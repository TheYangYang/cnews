"""Render spoken briefs with Kokoro when GPU is free; publish Opus to S3."""

from __future__ import annotations

import asyncio
from pathlib import Path

from realtime_ingestion import config
from realtime_ingestion.broker import RedisBroker
from realtime_ingestion.database import Database
from realtime_ingestion.normalize import prepare_speech_text
from realtime_ingestion.publish.publisher import Publisher
from realtime_ingestion.tts.gpu_gate import GATE
from realtime_ingestion.tts.opus import encode_opus_from_wav, write_wav_from_samples

_pipeline = None
_pipeline_error: Exception | None = None
_reported_missing = False


def _load_pipeline():
    global _pipeline, _pipeline_error
    if _pipeline_error is not None:
        raise _pipeline_error
    if _pipeline is None:
        try:
            from kokoro import KPipeline
        except Exception as exc:
            _pipeline_error = exc
            raise
        _pipeline = KPipeline(lang_code="a")
    return _pipeline


def render_kokoro(text: str, wav_dest: Path) -> int:
    pipeline = _load_pipeline()
    chunks = []
    for _graphemes, _phonemes, audio in pipeline(text, voice=config.KOKORO_VOICE, speed=1.0):
        chunks.append(audio)
    if not chunks:
        raise RuntimeError("Kokoro returned no audio")
    return write_wav_from_samples(wav_dest, chunks)


async def _handle(db: Database, publisher: Publisher, fields: dict[str, str], stop: asyncio.Event) -> str:
    """
    Returns:
      ack — message handled
      retry — GPU busy; do not ack yet
    """
    global _reported_missing
    article_pk = int(fields["article_pk"])
    article = db.get_article(article_pk)
    if article is None or not article.get("summary"):
        return "ack"
    if article.get("audio_path"):
        return "ack"

    if not config.TTS_ENABLED:
        db.save_audio(article_pk, audio_path=None, audio_status="unavailable")
        publisher.mark_audio_unavailable(article)
        return "ack"

    acquired = await GATE.wait_for_tts(stop)
    if not acquired:
        if stop.is_set():
            return "ack"
        db.add_event("tts", f"gpu_wait article={article_pk}")
        try:
            publisher.publish_story_text(article, audio_status="pending")
        except Exception:
            pass
        return "retry"

    wav_dest = config.AUDIO_DIR / f"{article_pk}.wav"
    opus_dest = config.AUDIO_DIR / f"{article_pk}.opus"
    try:
        speech = prepare_speech_text(article["summary"])
        db.add_event("tts", f"tts_start article={article_pk}")
        duration_ms = await asyncio.to_thread(render_kokoro, speech, wav_dest)
        content_type = "audio/wav"
        upload_path = wav_dest
        if encode_opus_from_wav(wav_dest, opus_dest):
            content_type = "audio/opus"
            upload_path = opus_dest
            db.save_audio(article_pk, audio_path=opus_dest.name, audio_status="ready")
        else:
            db.save_audio(article_pk, audio_path=wav_dest.name, audio_status="ready")
            db.add_event("tts", "ffmpeg/opus unavailable; publishing WAV")
        db.set_runtime("tts_status", "Kokoro-82M")
        publisher.publish_audio_file(
            article,
            upload_path,
            content_type=content_type,
            duration_ms=duration_ms,
        )
        db.add_event("tts", f"tts_done {upload_path.name} for {article['title']}")
        return "ack"
    except Exception as exc:
        missing = isinstance(exc, (ImportError, ModuleNotFoundError)) or _pipeline_error is not None
        status = "Kokoro-82M is not installed" if missing else f"Kokoro failed: {exc}"
        db.save_audio(article_pk, audio_path=None, audio_status=status)
        db.set_runtime("tts_status", status)
        if missing:
            publisher.mark_audio_unavailable(article)
        else:
            try:
                publisher.publish_story_text(article, audio_status="failed")
            except Exception:
                pass
        if not _reported_missing:
            db.add_event("tts", status)
            _reported_missing = True
        return "ack"
    finally:
        GATE.release_tts()


async def run_tts_worker(
    db: Database,
    broker: RedisBroker,
    stop: asyncio.Event,
    publisher: Publisher,
) -> None:
    db.add_event("tts", "TTS worker listening for briefs")
    while not stop.is_set():
        messages = await broker.read(
            config.STREAM_SUMMARIES,
            config.GROUP_TTS,
            "tts-1",
            count=1,
            block_ms=2000,
        )
        for message_id, fields in messages:
            try:
                result = await _handle(db, publisher, fields, stop)
            except Exception as exc:
                db.add_event("tts", f"worker error: {exc}")
                result = "ack"
            if result == "ack":
                await broker.ack(config.STREAM_SUMMARIES, config.GROUP_TTS, message_id)
            else:
                await asyncio.sleep(2)
