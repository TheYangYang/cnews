"""Run the poller, summary worker, speech worker, and local results page."""

from __future__ import annotations

import asyncio
import sys
import threading

from news_pipeline import config
from news_pipeline.broker import open_broker
from news_pipeline.database import Database
from news_pipeline.poller import run_poller
from news_pipeline.ui import serve_ui
from news_pipeline.worker_ai import run_ai_worker
from news_pipeline.worker_tts import run_tts_worker


async def _run() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    db = Database(config.DB_PATH)
    db.init()
    db.seed_feeds(config.FEEDS)
    db.backfill()
    broker = await open_broker(config.REDIS_URL)
    db.set_runtime("broker", broker.label)
    db.set_runtime("model", config.OLLAMA_MODEL)
    db.set_runtime("tts_status", "Kokoro-82M")
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
        asyncio.create_task(run_ai_worker(db, broker, stop), name="ai"),
        asyncio.create_task(run_tts_worker(db, broker, stop), name="tts"),
        asyncio.create_task(run_poller(db, broker, stop), name="poller"),
    ]
    try:
        await asyncio.gather(*tasks)
    finally:
        stop.set()
        server.shutdown()
        await broker.close()
        db.close()


def main() -> None:
    try:
        asyncio.run(_run())
    except KeyboardInterrupt:
        print("stopped", flush=True)


if __name__ == "__main__":
    main()
