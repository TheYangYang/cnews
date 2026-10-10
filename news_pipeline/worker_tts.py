"""Render spoken briefs to WAV with Kokoro-82M when that engine is installed."""

from __future__ import annotations

import asyncio
import wave
from pathlib import Path

from news_pipeline import config
from news_pipeline.broker import RedisBroker
from news_pipeline.database import Database

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


def _write_wav(path: Path, samples) -> None:
    import numpy as np

    audio = np.concatenate(list(samples)) if not isinstance(samples, np.ndarray) else samples
    pcm = (audio * 32767).clip(-32768, 32767).astype(np.int16)
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "w") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(config.KOKORO_SAMPLE_RATE)
        handle.writeframes(pcm.tobytes())


def render_kokoro(text: str, dest: Path) -> None:
    pipeline = _load_pipeline()
    chunks = []
    for _graphemes, _phonemes, audio in pipeline(text, voice=config.KOKORO_VOICE, speed=1.0):
        chunks.append(audio)
    if not chunks:
        raise RuntimeError("Kokoro returned no audio")
    _write_wav(dest, chunks)


async def _handle(db: Database, fields: dict[str, str]) -> None:
    article_pk = int(fields["article_pk"])
    article = db.get_article(article_pk)
    if article is None or not article.get("summary"):
        return
    if article.get("audio_path"):
        return

    dest = config.AUDIO_DIR / f"{article_pk}.wav"
    try:
        await asyncio.to_thread(render_kokoro, article["summary"], dest)
    except Exception as exc:
        global _reported_missing
        missing = isinstance(exc, (ImportError, ModuleNotFoundError)) or _pipeline_error is not None
        status = "Kokoro-82M is not installed" if missing else f"Kokoro failed: {exc}"
        db.save_audio(article_pk, audio_path=None, audio_status=status)
        db.set_runtime("tts_status", status)
        if not _reported_missing:
            db.add_event("tts", status)
            _reported_missing = True
        return

    db.save_audio(article_pk, audio_path=dest.name, audio_status="ready")
    db.set_runtime("tts_status", "Kokoro-82M")
    db.add_event("tts", f"rendered {dest.name} for {article['title']}")


async def run_tts_worker(db: Database, broker: RedisBroker, stop: asyncio.Event) -> None:
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
                await _handle(db, fields)
            except Exception as exc:
                db.add_event("tts", f"worker error: {exc}")
            await broker.ack(config.STREAM_SUMMARIES, config.GROUP_TTS, message_id)
