"""Housekeeping for a long-running ingest box.

Every minute: heartbeat to MongoDB (GET /v1/health/ingest alerts when it goes stale).
Every 10 minutes: retry audio that failed to reach S3.
Hourly: close quiet storylines, prune the local working store, and prune the
published store (MongoDB + S3) to what the app should still show.
"""

from __future__ import annotations

import asyncio
import time

from realtime_ingestion import config
from realtime_ingestion.database import Database
from realtime_ingestion.publish.publisher import AsyncPublisher


async def retry_failed_uploads(db: Database, publisher: AsyncPublisher) -> int:
    """Re-send audio that rendered locally but never reached S3 (network blip, bad keys)."""
    if not publisher.enabled:
        return 0
    done = 0
    for article in db.audio_uploads_to_retry():
        path = config.AUDIO_DIR / article["audio_path"]
        if not path.is_file():
            db.save_audio(int(article["id"]), audio_path=None, audio_status="failed")
            continue
        content_type = "audio/opus" if path.suffix == ".opus" else "audio/wav"
        try:
            await publisher.audio_file(article, path, content_type=content_type, duration_ms=None)
        except Exception as exc:
            db.add_event("publish", f"upload retry failed for {article['id']}: {exc}")
            break  # S3 still unreachable; try the rest next round
        db.save_audio(int(article["id"]), audio_path=article["audio_path"], audio_status="ready")
        path.unlink(missing_ok=True)  # S3 has it now
        done += 1
    if done:
        db.add_event("publish", f"retried {done} audio uploads")
    return done


async def close_stale_storylines(db: Database, publisher: AsyncPublisher) -> int:
    closed = db.close_stale_threads(quiet_days=config.STORYLINE_STALE_DAYS)
    for thread_id, closed_at in closed:
        try:
            await publisher.close_thread(thread_id, closed_at)
        except Exception as exc:
            db.add_event("maintenance", f"could not publish storyline close {thread_id}: {exc}")
    if closed:
        db.add_event("maintenance", f"closed {len(closed)} storylines quiet for {config.STORYLINE_STALE_DAYS}d")
    return len(closed)


def prune(db: Database) -> dict:
    result = db.prune(keep_days=config.RETENTION_DAYS)
    for article_id in result["deleted_ids"]:
        for suffix in (".opus", ".wav"):
            (config.AUDIO_DIR / f"{article_id}{suffix}").unlink(missing_ok=True)
    if result["articles"] or result["text_trimmed"]:
        db.add_event(
            "maintenance",
            f"local store: pruned {result['articles']} articles older than {config.RETENTION_DAYS}d, "
            f"{result['threads']} closed storylines, trimmed text on {result['text_trimmed']}",
        )
    return result


async def run_maintenance(db: Database, publisher: AsyncPublisher, stop: asyncio.Event) -> None:
    last_prune = last_retry = float("-inf")
    while not stop.is_set():
        try:
            await publisher.heartbeat()
        except Exception as exc:
            db.add_event("maintenance", f"heartbeat failed: {exc}")
        if time.monotonic() - last_retry >= config.UPLOAD_RETRY_INTERVAL_SECONDS:
            last_retry = time.monotonic()
            await retry_failed_uploads(db, publisher)
        if time.monotonic() - last_prune >= config.MAINTENANCE_INTERVAL_SECONDS:
            last_prune = time.monotonic()
            await close_stale_storylines(db, publisher)
            prune(db)
            if config.PRUNE_PUBLISHED and publisher.enabled:
                try:
                    await publisher.prune_published(
                        story_days=config.STORY_RETENTION_DAYS,
                        closed_thread_days=config.CLOSED_STORYLINE_RETENTION_DAYS,
                    )
                except Exception as exc:
                    db.add_event("maintenance", f"published-store prune failed, will retry: {exc}")
        try:
            await asyncio.wait_for(stop.wait(), timeout=config.HEARTBEAT_INTERVAL_SECONDS)
        except TimeoutError:
            pass
