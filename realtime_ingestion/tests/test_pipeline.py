"""Brief → speech flow with fake Ollama and Kokoro, in-process Redis, temp SQLite.

Run: python -m unittest discover -s realtime_ingestion/tests
"""

from __future__ import annotations

import asyncio
import json
import tempfile
import time
import unittest
from pathlib import Path

import fakeredis.aioredis
import httpx
import numpy as np

from realtime_ingestion import config
from realtime_ingestion.broker import RedisBroker
from realtime_ingestion.database import Database
from realtime_ingestion.publish.publisher import AsyncPublisher
from realtime_ingestion.tts import gpu_gate
from realtime_ingestion.tts.opus import write_wav_from_samples
from realtime_ingestion.worker_ai import AiWorker
from realtime_ingestion.worker_tts import TtsWorker

ARTICLE = " ".join(["The council voted on the transit plan after a long debate."] * 12)


class FakeOllama:
    """Records the order of chat calls and unloads; replies like llama would."""

    def __init__(self, log: list[str]) -> None:
        self.log = log
        self.num_ctx: set[int] = set()

    def __call__(self, request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content or b"{}")
        if request.url.path == "/api/generate" and body.get("keep_alive") == 0:
            self.log.append("unload")
            return httpx.Response(200, json={"done": True})
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": config.OLLAMA_MODEL}]})
        self.num_ctx.add(body["options"]["num_ctx"])
        prompt = body["messages"][-1]["content"]
        if prompt.startswith("Headline:"):
            title = prompt.split("\n", 1)[0].removeprefix("Headline: ")
            self.log.append(f"brief:{title}")
            text = "City council approved the transit plan after debate, and riders will see new routes next spring with more frequent buses across the downtown core."
        elif "Open threads" in prompt:
            self.log.append("thread")
            text = "IGNORE"
        else:
            self.log.append("framing")
            text = ""
        return httpx.Response(200, json={"message": {"content": text}})


class FakeSpeaker:
    def __init__(self, log: list[str]) -> None:
        self.log = log
        self.error = None
        self.target = "cuda"
        self.device = "cpu"
        self.moves: list[str] = []

    ready = True

    def load(self) -> None:
        pass

    def move(self, device: str) -> None:
        self.moves.append(device)
        self.device = device

    def render(self, text: str, wav_dest: Path) -> int:
        assert self.device == "cuda", "Kokoro must be on the GPU during a turn"
        self.log.append(f"tts:{wav_dest.stem}")
        time.sleep(0.01)
        return write_wav_from_samples(wav_dest, [np.zeros(2400, dtype=np.float32)])


class PipelineTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self._saved = (config.AUDIO_DIR, config.PUBLISH_ENABLED, config.GPU_SWAP_MODELS, config.TTS_ENABLED)
        config.AUDIO_DIR = root / "audio"
        config.AUDIO_DIR.mkdir()
        config.PUBLISH_ENABLED = False
        config.GPU_SWAP_MODELS = True
        config.TTS_ENABLED = True
        # Fresh gate with short timings so the test runs in about a second.
        gate = gpu_gate.GpuGate(idle_grace=0.2, max_lag=60, turn_min=2, turn_max=4, poll=0.01)
        self._saved_gate = gpu_gate.GATE
        for module in ("realtime_ingestion.worker_ai", "realtime_ingestion.worker_tts"):
            __import__(module, fromlist=["GATE"]).GATE = gate
        gpu_gate.GATE = gate
        self.gate = gate

        db_path = root / "news.db"
        self.db = Database(db_path)
        self.db.init()
        self.db.seed_feeds(config.FEEDS[:1])
        self.publisher = AsyncPublisher(db_path)
        await self.publisher.start()
        self.broker = RedisBroker(fakeredis.aioredis.FakeRedis(decode_responses=True), "test", durable=True)
        await self.broker.ensure_group(config.STREAM_ARTICLES, config.GROUP_AI)
        await self.broker.ensure_group(config.STREAM_SUMMARIES, config.GROUP_TTS)
        self.log: list[str] = []
        self.ollama = FakeOllama(self.log)
        self.client = httpx.AsyncClient(transport=httpx.MockTransport(self.ollama), base_url=config.OLLAMA_URL)

    async def asyncTearDown(self) -> None:
        await self.client.aclose()
        await self.broker.close()
        await self.publisher.close()
        self.db.close()
        config.AUDIO_DIR, config.PUBLISH_ENABLED, config.GPU_SWAP_MODELS, config.TTS_ENABLED = self._saved
        for module in ("realtime_ingestion.worker_ai", "realtime_ingestion.worker_tts"):
            __import__(module, fromlist=["GATE"]).GATE = self._saved_gate
        gpu_gate.GATE = self._saved_gate
        self.tmp.cleanup()

    async def _add_article(self, n: int) -> int:
        feed_id = self.db.due_feeds()[0]["id"]
        pk, _joined = self.db.insert_article(
            feed_id=feed_id,
            article_id=f"a{n}",
            url=f"https://example.ca/{n}",
            title=f"Story number {n} about item {n * 7919}",
            title_hash=f"h{n}",
            image_url=None,
            category="Local",
            place="Calgary",
            outlet="CBC",
            raw_text=ARTICLE,
            published_at=None,
        )
        await self.broker.publish(config.STREAM_ARTICLES, {"article_pk": str(pk), "raw_text": ARTICLE})
        return pk

    async def test_briefs_first_then_batched_speech_with_model_swap(self) -> None:
        pks = [await self._add_article(n) for n in range(5)]
        speaker = FakeSpeaker(self.log)
        stop = asyncio.Event()
        ai = AiWorker(self.db, self.broker, self.client, self.publisher)
        tts = TtsWorker(self.db, self.broker, self.publisher, self.client, speaker)
        tasks = [asyncio.create_task(ai.run(stop)), asyncio.create_task(tts.run(stop))]

        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            done = [self.db.get_article(pk).get("audio_path") for pk in pks]
            if all(done):
                break
            await asyncio.sleep(0.05)
        stop.set()
        await asyncio.wait_for(asyncio.gather(*tasks), timeout=10)

        for pk in pks:
            row = self.db.get_article(pk)
            self.assertTrue(row["summary"], f"article {pk} has no brief")
            self.assertEqual(row["audio_status"], "ready")
            self.assertTrue((config.AUDIO_DIR / row["audio_path"]).is_file())
        # Every article was briefed before any speech: the burst kept the GPU on the LLM.
        first_tts = next(i for i, e in enumerate(self.log) if e.startswith("tts:"))
        self.assertEqual(sum(e.startswith("brief:") for e in self.log[:first_tts]), 5)
        # The speech turn swapped models: Ollama unloaded, Kokoro moved to GPU then back.
        self.assertEqual(self.log[first_tts - 1], "unload")
        self.assertEqual(speaker.moves[0], "cuda")
        self.assertEqual(speaker.moves[-1], "cpu")
        # Storyline review ran only after speech (enrichment is lowest priority).
        threads = [i for i, e in enumerate(self.log) if e == "thread"]
        last_tts = max(i for i, e in enumerate(self.log) if e.startswith("tts:"))
        self.assertTrue(threads and min(threads) > last_tts, self.log)
        self.assertEqual(self.ollama.num_ctx, {config.OLLAMA_NUM_CTX})

    async def test_gpu_render_failure_falls_back_to_cpu(self) -> None:
        pks = [await self._add_article(n) for n in range(2)]

        class NoKernelSpeaker(FakeSpeaker):
            def render(self, text: str, wav_dest: Path) -> int:
                if self.device == "cuda":
                    raise RuntimeError("CUDA error: no kernel image is available for execution on the device")
                self.log.append(f"tts:{wav_dest.stem}")
                return write_wav_from_samples(wav_dest, [np.zeros(2400, dtype=np.float32)])

        speaker = NoKernelSpeaker(self.log)
        stop = asyncio.Event()
        ai = AiWorker(self.db, self.broker, self.client, self.publisher)
        tts = TtsWorker(self.db, self.broker, self.publisher, self.client, speaker)
        tasks = [asyncio.create_task(ai.run(stop)), asyncio.create_task(tts.run(stop))]
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline and not all(
            self.db.get_article(pk).get("audio_path") for pk in pks
        ):
            await asyncio.sleep(0.05)
        stop.set()
        await asyncio.wait_for(asyncio.gather(*tasks), timeout=10)
        for pk in pks:
            self.assertEqual(self.db.get_article(pk)["audio_status"], "ready")
        self.assertEqual(speaker.device, "cpu")
        self.assertFalse(self.gate.scheduling)
        self.assertFalse(self.gate.in_turn)

    async def test_unacked_speech_job_is_recovered_after_restart(self) -> None:
        pk = await self._add_article(1)
        self.db.save_summary(pk, summary="A short brief for speech.", summary_words=5, summary_engine="test")
        await self.broker.publish(config.STREAM_SUMMARIES, {"article_pk": str(pk)})
        # A previous run received the job and died before acking it.
        taken = await self.broker.read(config.STREAM_SUMMARIES, config.GROUP_TTS, "tts-1")
        self.assertEqual(len(taken), 1)

        speaker = FakeSpeaker(self.log)
        stop = asyncio.Event()
        tts = TtsWorker(self.db, self.broker, self.publisher, self.client, speaker)
        task = asyncio.create_task(tts.run(stop))
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline and not self.db.get_article(pk).get("audio_path"):
            await asyncio.sleep(0.05)
        stop.set()
        await asyncio.wait_for(task, timeout=10)
        self.assertEqual(self.db.get_article(pk)["audio_status"], "ready")
        pending = await self.broker.redis.xpending(config.STREAM_SUMMARIES, config.GROUP_TTS)
        self.assertEqual(pending["pending"], 0)


if __name__ == "__main__":
    unittest.main()
