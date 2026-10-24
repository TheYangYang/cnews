"""Run the poller, summary worker, speech worker, publisher, and local results page."""

from __future__ import annotations

import asyncio
import signal
import sys
import threading
from typing import Awaitable, Callable

from realtime_ingestion import config
from realtime_ingestion.broker import open_broker
from realtime_ingestion.database import Database
from realtime_ingestion.maintenance import run_maintenance
from realtime_ingestion.poller import run_poller
from realtime_ingestion.publish import AsyncPublisher
from realtime_ingestion.ui import serve_ui
from realtime_ingestion.worker_ai import run_ai_worker
from realtime_ingestion.worker_tts import run_tts_worker

_RESTART_DELAY_SECONDS = 5
_SHUTDOWN_GRACE_SECONDS = 20


async def _supervise(
    name: str,
    db: Database,
    stop: asyncio.Event,
    run: Callable[[], Awaitable[None]],
) -> None:
    """Keep one worker alive: log a crash, wait a moment, start it again."""
    while not stop.is_set():
        try:
            await run()
            return
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            db.add_event(name, f"crashed, restarting in {_RESTART_DELAY_SECONDS}s: {exc!r}")
            try:
                await asyncio.wait_for(stop.wait(), timeout=_RESTART_DELAY_SECONDS)
            except TimeoutError:
                pass


async def _run() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    config.AUDIO_DIR.mkdir(parents=True, exist_ok=True)

    db = Database(config.DB_PATH)
    db.init()
    db.seed_feeds(config.FEEDS)
    db.backfill()
    publisher = AsyncPublisher(config.DB_PATH)
    await publisher.start()
    broker = await open_broker(config.REDIS_URL)
    db.set_runtime("broker", broker.label)
    db.set_runtime("model", config.OLLAMA_MODEL)
    db.set_runtime("tts_status", "loading Kokoro-82M" if config.TTS_ENABLED else "disabled")
    db.set_runtime("publish", "on" if publisher.enabled else "off")
    await broker.ensure_group(config.STREAM_ARTICLES, config.GROUP_AI)
    await broker.ensure_group(config.STREAM_SUMMARIES, config.GROUP_TTS)

    server = serve_ui(config.DB_PATH, config.AUDIO_DIR, config.UI_HOST, config.UI_PORT)
    thread = threading.Thread(target=server.serve_forever, name="ui", daemon=True)
    thread.start()
    url = f"http://{config.UI_HOST}:{config.UI_PORT}"
    print(f"Results: {url}", flush=True)
    db.add_event("ui", f"results page at {url}")

    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop.set)
        except (NotImplementedError, RuntimeError):
            pass  # Windows: Ctrl+C still raises KeyboardInterrupt

    tasks = [
        asyncio.create_task(
            _supervise("ai", db, stop, lambda: run_ai_worker(db, broker, stop, publisher)), name="ai"
        ),
        asyncio.create_task(
            _supervise("tts", db, stop, lambda: run_tts_worker(db, broker, stop, publisher)), name="tts"
        ),
        asyncio.create_task(
            _supervise("poller", db, stop, lambda: run_poller(db, broker, stop)), name="poller"
        ),
        asyncio.create_task(
            _supervise("maintenance", db, stop, lambda: run_maintenance(db, publisher, stop)),
            name="maintenance",
        ),
    ]
    try:
        await stop.wait()
    finally:
        stop.set()
        # Let workers finish the job in hand (an Ollama call can take a while), then cancel.
        _done, pending = await asyncio.wait(tasks, timeout=_SHUTDOWN_GRACE_SECONDS)
        for task in pending:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        server.shutdown()
        await broker.close()
        await publisher.close()
        db.close()


def main() -> None:
    try:
        asyncio.run(_run())
    except KeyboardInterrupt:
        pass
    print("stopped", flush=True)


if __name__ == "__main__":
    main()
