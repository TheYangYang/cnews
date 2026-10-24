"""Render spoken briefs with Kokoro when the GPU is free; publish Opus to S3.

Kokoro loads once at startup on CPU. On a GPU host it moves to the card only for a
speech turn (see tts/gpu_gate.py). With GPU_SWAP_MODELS the turn first unloads the
Ollama model, so an 8B LLM and Kokoro never fight over a 6 GB card, and Kokoro
returns to CPU when the turn ends. Opus encoding and upload run after the GPU is
released, overlapping the next render.
"""

from __future__ import annotations

import asyncio
import time
from pathlib import Path

import httpx

from realtime_ingestion import config, llm
from realtime_ingestion.broker import RedisBroker, enqueued_at
from realtime_ingestion.database import Database
from realtime_ingestion.normalize import prepare_speech_text
from realtime_ingestion.publish.publisher import AsyncPublisher
from realtime_ingestion.tts.gpu_gate import GATE
from realtime_ingestion.tts.opus import encode_opus_from_wav, write_wav_from_samples

# Uploads in flight while the next brief renders.
_MAX_FINALIZING = 4


class Speaker:
    """Kokoro pipeline that can move between CPU and GPU."""

    def __init__(self) -> None:
        self._pipeline = None
        self.error: Exception | None = None
        self.target = "cpu"
        self.device = "cpu"

    def load(self) -> None:
        try:
            import torch
            from kokoro import KPipeline
        except Exception as exc:
            self.error = exc
            return
        wanted = config.TTS_DEVICE
        if wanted == "auto":
            wanted = "cuda" if torch.cuda.is_available() else "cpu"
        if wanted == "cuda" and not torch.cuda.is_available():
            wanted = "cpu"
        self.target = wanted
        try:
            self._pipeline = KPipeline(lang_code="a", device="cpu")
        except Exception as exc:
            self.error = exc

    @property
    def ready(self) -> bool:
        return self._pipeline is not None

    def move(self, device: str) -> None:
        if self._pipeline is None or device == self.device:
            return
        self._pipeline.model.to(device)
        self.device = device
        if device == "cpu":
            import torch

            if torch.cuda.is_available():
                torch.cuda.empty_cache()

    def render(self, text: str, wav_dest: Path) -> int:
        if self._pipeline is None:
            raise RuntimeError("Kokoro is not loaded")
        chunks = [
            audio
            for _graphemes, _phonemes, audio in self._pipeline(
                text, voice=config.KOKORO_VOICE, speed=1.0
            )
        ]
        if not chunks:
            raise RuntimeError("Kokoro returned no audio")
        return write_wav_from_samples(wav_dest, chunks)


def _encode(wav_dest: Path, opus_dest: Path) -> tuple[Path, str]:
    if encode_opus_from_wav(wav_dest, opus_dest, bitrate=config.OPUS_BITRATE):
        # The WAV is ~12x the Opus size and nothing reads it once Opus exists.
        wav_dest.unlink(missing_ok=True)
        return opus_dest, "audio/opus"
    return wav_dest, "audio/wav"


class TtsWorker:
    def __init__(
        self,
        db: Database,
        broker: RedisBroker,
        publisher: AsyncPublisher,
        client: httpx.AsyncClient,
        speaker: Speaker,
    ) -> None:
        self.db = db
        self.broker = broker
        self.publisher = publisher
        self.client = client
        self.speaker = speaker
        self.inflight: set[int] = set()
        self.finalizing: set[asyncio.Task] = set()
        self._slots = asyncio.Semaphore(_MAX_FINALIZING)
        self._reported_failure = False

    # ----- GPU turn hooks -----------------------------------------------------------

    async def turn_start(self) -> None:
        if config.GPU_SWAP_MODELS:
            unloaded = await llm.unload(self.client)
            self.db.add_event("tts", "gpu turn: Ollama unloaded" if unloaded else "gpu turn: Ollama unload failed")
        await asyncio.to_thread(self.speaker.move, self.speaker.target)

    async def turn_end(self) -> None:
        if config.GPU_SWAP_MODELS:
            await asyncio.to_thread(self.speaker.move, "cpu")

    # ----- one brief ----------------------------------------------------------------

    async def _ack(self, message_id: str) -> None:
        await self.broker.ack(config.STREAM_SUMMARIES, config.GROUP_TTS, message_id)

    async def handle(self, message_id: str, fields: dict[str, str], stop: asyncio.Event) -> None:
        db = self.db
        article_pk = int(fields["article_pk"])
        article = db.get_article(article_pk)
        if (
            article is None
            or not article.get("summary")
            or article.get("audio_path")
            or article_pk in self.inflight
        ):
            await self._ack(message_id)
            return

        if not config.TTS_ENABLED or not self.speaker.ready:
            missing = config.TTS_ENABLED
            status = "unavailable"
            if missing:
                status = "Kokoro-82M is not installed"
                db.set_runtime("tts_status", status)
                if not self._reported_failure:
                    db.add_event("tts", f"{status}: {self.speaker.error}")
                    self._reported_failure = True
            db.save_audio(article_pk, audio_path=None, audio_status=status)
            await self._publish_safely(self.publisher.audio_unavailable(article))
            await self._ack(message_id)
            return

        lag = max(0.0, time.time() - enqueued_at(message_id))
        wav_dest = config.AUDIO_DIR / f"{article_pk}.wav"
        self.inflight.add(article_pk)
        try:
            async with GATE.tts(lag_seconds=lag, stop=stop) as granted:
                if not granted:
                    # Shutting down: leave unacked; read_pending picks it up next start.
                    self.inflight.discard(article_pk)
                    return
                speech = prepare_speech_text(article["summary"])
                db.add_event("tts", f"tts_start article={article_pk} on {self.speaker.device}")
                try:
                    duration_ms = await asyncio.to_thread(self.speaker.render, speech, wav_dest)
                except Exception as exc:
                    if self.speaker.device != "cuda":
                        raise
                    duration_ms = await self._fall_back_to_cpu(exc, speech, wav_dest)
        except Exception as exc:
            self.inflight.discard(article_pk)
            status = f"Kokoro failed: {exc}"
            db.save_audio(article_pk, audio_path=None, audio_status=status)
            db.set_runtime("tts_status", status)
            db.add_event("tts", status)
            await self._publish_safely(self.publisher.story_text(article, audio_status="failed"))
            await self._ack(message_id)
            return

        await self._slots.acquire()
        task = asyncio.create_task(self._finalize(message_id, article, wav_dest, duration_ms))
        self.finalizing.add(task)
        task.add_done_callback(self.finalizing.discard)

    async def _fall_back_to_cpu(self, exc: Exception, speech: str, wav_dest: Path) -> int:
        """GPU render failed (e.g. a torch build without sm_61 kernels for a GTX 1060).
        Keep speaking on CPU for the rest of this run instead of failing every brief."""
        self.db.add_event("tts", f"Kokoro on cuda failed ({exc}); switching to cpu for this run")
        self.speaker.target = "cpu"
        await asyncio.to_thread(self.speaker.move, "cpu")
        GATE.scheduling = False
        self.db.set_runtime("tts_status", "Kokoro-82M (cpu fallback)")
        return await asyncio.to_thread(self.speaker.render, speech, wav_dest)

    async def _finalize(self, message_id: str, article: dict, wav_dest: Path, duration_ms: int) -> None:
        db = self.db
        article_pk = int(article["id"])
        try:
            opus_dest = config.AUDIO_DIR / f"{article_pk}.opus"
            upload_path, content_type = await asyncio.to_thread(_encode, wav_dest, opus_dest)
            if content_type != "audio/opus":
                db.add_event("tts", "ffmpeg/opus unavailable; publishing WAV")
            db.save_audio(article_pk, audio_path=upload_path.name, audio_status="ready")
            db.set_runtime("tts_status", "Kokoro-82M")
            try:
                await self.publisher.audio_file(
                    article, upload_path, content_type=content_type, duration_ms=duration_ms
                )
                if self.publisher.enabled:
                    upload_path.unlink(missing_ok=True)  # S3 has it now
            except Exception as exc:
                # Kept on disk; maintenance retries the upload (see maintenance.py).
                db.save_audio(article_pk, audio_path=upload_path.name, audio_status="upload_failed")
                db.add_event("publish", f"audio publish failed, will retry: {exc}")
            db.add_event("tts", f"tts_done {upload_path.name} for {article['title']}")
            await self._ack(message_id)
        except Exception as exc:
            db.add_event("tts", f"finalize error: {exc}")
        finally:
            self.inflight.discard(article_pk)
            self._slots.release()

    async def _publish_safely(self, call) -> None:
        try:
            await call
        except Exception as exc:
            self.db.add_event("publish", f"audio status publish failed: {exc}")

    # ----- loop -------------------------------------------------------------------

    async def _process(self, message_id: str, fields: dict[str, str], stop: asyncio.Event) -> None:
        try:
            await self.handle(message_id, fields, stop)
        except Exception as exc:
            self.db.add_event("tts", f"worker error: {exc}")
            await self._ack(message_id)

    async def run(self, stop: asyncio.Event) -> None:
        db = self.db
        if config.TTS_ENABLED:
            await asyncio.to_thread(self.speaker.load)
        if self.speaker.ready:
            on_gpu = self.speaker.target == "cuda"
            # Speech on CPU never waits for the LLM; on GPU it takes turns.
            GATE.scheduling = config.GPU_GATE_ENABLED and on_gpu
            GATE.on_turn_start = self.turn_start
            GATE.on_turn_end = self.turn_end
            if not (on_gpu and config.GPU_SWAP_MODELS):
                await asyncio.to_thread(self.speaker.move, self.speaker.target)
            mode = "gpu turns + model swap" if on_gpu and config.GPU_SWAP_MODELS else "gpu turns" if on_gpu else "cpu"
            db.set_runtime("tts_status", f"Kokoro-82M ({mode})")
            db.add_event("tts", f"Kokoro ready on {self.speaker.target} ({mode})")
        elif config.TTS_ENABLED:
            GATE.scheduling = False
            db.add_event("tts", f"Kokoro unavailable: {self.speaker.error}")

        for message_id, fields in await self.broker.read_pending(
            config.STREAM_SUMMARIES, config.GROUP_TTS, "tts-1"
        ):
            await self._process(message_id, fields, stop)
        if not self.broker.durable:
            waiting = db.articles_awaiting_audio()
            for article_pk in waiting:
                await self.broker.publish(config.STREAM_SUMMARIES, {"article_pk": str(article_pk)})
            if waiting:
                db.add_event("tts", f"requeued {len(waiting)} recent briefs still waiting on speech")

        db.add_event("tts", "TTS worker listening for briefs")
        while not stop.is_set():
            # Inside a turn, poll quickly so an empty queue hands the GPU back promptly.
            messages = await self.broker.read(
                config.STREAM_SUMMARIES,
                config.GROUP_TTS,
                "tts-1",
                count=1,
                block_ms=200 if GATE.in_turn else 2000,
            )
            if not messages:
                await GATE.end_turn()
                continue
            for message_id, fields in messages:
                await self._process(message_id, fields, stop)

        if self.finalizing:
            await asyncio.gather(*self.finalizing, return_exceptions=True)


async def run_tts_worker(
    db: Database,
    broker: RedisBroker,
    stop: asyncio.Event,
    publisher: AsyncPublisher,
) -> None:
    async with httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=5.0)) as client:
        await TtsWorker(db, broker, publisher, client, Speaker()).run(stop)
