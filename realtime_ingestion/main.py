"""Run the poller, summary worker, speech worker, publisher, and local results page."""

from __future__ import annotations

import asyncio
import sys
import threading

from realtime_ingestion import config
from realtime_ingestion.broker import open_broker
from realtime_ingestion.database import Database
from realtime_ingestion.poller import run_poller
from realtime_ingestion.publish import Publisher
from realtime_ingestion.ui import serve_ui
from realtime_ingestion.worker_ai import run_ai_worker
from realtime_ingestion.worker_tts import run_tts_worker


async def _run() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    config.AUDIO_DIR.mkdir(parents=True, exist_ok=True)

    db = Database(config.DB_PATH)
    db.init()
    db.seed_feeds(config.FEEDS)
    db.backfill()
    publisher = Publisher(db)
    broker = await open_broker(config.REDIS_URL)
    db.set_runtime("broker", broker.label)
    db.set_runtime("model", config.OLLAMA_MODEL)
    db.set_runtime("tts_status", "Kokoro-82M" if config.TTS_ENABLED else "disabled")
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
    tasks = [
        asyncio.create_task(run_ai_worker(db, broker, stop, publisher), name="ai"),
        asyncio.create_task(run_tts_worker(db, broker, stop, publisher), name="tts"),
        asyncio.create_task(run_poller(db, broker, stop), name="poller"),
    ]
    try:
        await asyncio.gather(*tasks)
    finally:
        stop.set()
        server.shutdown()
        await broker.close()
        publisher.close()
        db.close()


def main() -> None:
    try:
        asyncio.run(_run())
    except KeyboardInterrupt:
        print("stopped", flush=True)


if __name__ == "__main__":
    main()
