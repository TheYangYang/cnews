"""Map working-store rows into MongoDB + S3 publish documents."""

from __future__ import annotations

import asyncio
import functools
import logging
import socket
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from realtime_ingestion import config
from realtime_ingestion.database import Database
from realtime_ingestion.publish.mongo_store import MongoStore
from realtime_ingestion.publish.s3_store import S3Store

log = logging.getLogger(__name__)


def story_id_for(article_pk: int) -> str:
    return f"story_{article_pk}"


def cluster_id_for(raw: str | None) -> str | None:
    if not raw:
        return None
    return f"cluster_{raw}" if not str(raw).startswith("cluster_") else str(raw)


def thread_id_for(raw: str | None) -> str | None:
    if not raw:
        return None
    return f"thread_{raw}" if not str(raw).startswith("thread_") else str(raw)


def _parse_time(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    try:
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return datetime.now(timezone.utc)


class Publisher:
    def __init__(self, db: Database) -> None:
        self._db = db
        self._mongo: MongoStore | None = None
        self._s3: S3Store | None = None
        self._enabled = config.PUBLISH_ENABLED
        if not self._enabled:
            return
        try:
            self._mongo = MongoStore(config.MONGODB_URI, config.MONGODB_DATABASE)
            self._mongo.ping()
            self._s3 = S3Store(
                bucket=config.S3_BUCKET,
                region=config.S3_REGION,
                endpoint=config.S3_ENDPOINT or None,
                access_key=config.S3_ACCESS_KEY or None,
                secret_key=config.S3_SECRET_KEY or None,
                force_path_style=config.S3_FORCE_PATH_STYLE,
                prefix=config.S3_PREFIX,
            )
            self._s3.ensure_bucket()
            db.add_event("publish", "MongoDB + S3 publish ready")
        except Exception as exc:
            self._enabled = False
            self._mongo = None
            self._s3 = None
            db.add_event("publish", f"publish disabled: {exc}")

    @property
    def enabled(self) -> bool:
        return self._enabled and self._mongo is not None

    def close(self) -> None:
        if self._mongo:
            self._mongo.close()

    def publish_story_text(self, article: dict[str, Any], *, audio_status: str = "pending") -> None:
        """Upsert the text doc. ``audio_status`` only lands if the story has no audio yet."""
        if not self.enabled or not self._mongo:
            return
        article_pk = int(article["id"])
        sid = story_id_for(article_pk)
        published = _parse_time(article.get("published_at") or article.get("summarized_at") or article.get("first_seen_at"))
        summary = (article.get("summary") or "").strip()
        if not summary:
            return
        thread_raw = self._db.thread_id_for_article(article_pk)
        doc = {
            "storyId": sid,
            "clusterId": cluster_id_for(article.get("cluster_id")),
            "threadId": thread_id_for(thread_raw),
            "title": article["title"],
            "summary": summary,
            "summaryWords": int(article.get("summary_words") or 0),
            "summaryEngine": article.get("summary_engine") or "",
            "imageUrl": article.get("image_url"),
            "outlet": article.get("outlet") or "",
            "topic": article.get("category") or "Top",
            "place": article.get("place") or "Canada",
            "sourceUrl": article.get("url") or "",
            "publishedAt": published,
            "ingestedAt": _parse_time(article.get("first_seen_at")),
            "textReady": True,
        }
        try:
            self._mongo.upsert_story(doc)
            if audio_status in {"unavailable", "failed"}:
                self._mongo.mark_audio_status(sid, audio_status)
            self._db.add_event("publish", f"story upsert {sid}")
        except Exception as exc:
            self._mongo.deadletter("story", sid, str(exc), doc)
            self._db.add_event("publish", f"story upsert failed {sid}: {exc}")
            raise

    def publish_audio_file(
        self,
        article: dict[str, Any],
        path: Path,
        *,
        content_type: str,
        duration_ms: int | None = None,
    ) -> str | None:
        if not self.enabled or not self._mongo or not self._s3:
            return None
        article_pk = int(article["id"])
        sid = story_id_for(article_pk)
        when = _parse_time(article.get("summarized_at") or article.get("first_seen_at"))
        ext = "opus" if content_type.endswith("opus") else path.suffix.lstrip(".") or "wav"
        key = self._s3.audio_key_for(sid, when, ext=ext)
        try:
            # Ensure text doc exists first
            self.publish_story_text(article, audio_status="pending")
            full_key = self._s3.put_file(key, path, content_type)
            self._mongo.attach_audio(
                sid,
                audio_key=full_key,
                audio_content_type=content_type,
                audio_duration_ms=duration_ms,
            )
            self._mongo.mark_thread_audio(sid, full_key)
            self._db.add_event("publish", f"audio put {full_key}")
            return full_key
        except Exception as exc:
            self._mongo.deadletter("audio", sid, str(exc), {"path": str(path)})
            self._mongo.mark_audio_status(sid, "failed")
            self._db.add_event("publish", f"audio put failed {sid}: {exc}")
            raise

    def mark_audio_unavailable(self, article: dict[str, Any]) -> None:
        if not self.enabled or not self._mongo:
            return
        try:
            self.publish_story_text(article, audio_status="unavailable")
        except Exception as exc:
            self._db.add_event("publish", f"mark unavailable failed: {exc}")

    def publish_coverage(self, cluster_id: str) -> None:
        if not self.enabled or not self._mongo:
            return
        framing = self._db.get_framing(cluster_id)
        reports = self._db.cluster_reports_full(cluster_id)
        if len(reports) < 2 or not framing:
            return
        notes = {n["outlet"]: n.get("note") or n.get("framing") or "" for n in framing["notes"]}
        outlets = []
        topics: set[str] = set()
        title = reports[0]["title"]
        for report in reports:
            topics.add(report.get("category") or "Top")
            pk = int(report["id"])
            outlets.append(
                {
                    "storyId": story_id_for(pk),
                    "outlet": report["outlet"],
                    "framing": notes.get(report["outlet"], ""),
                    "summary": report.get("summary") or "",
                    "audioStatus": "ready" if report.get("audio_path") else (report.get("audio_status") or "pending"),
                    "audioKey": None,
                    "imageUrl": report.get("image_url"),
                }
            )
        doc = {
            "clusterId": cluster_id_for(cluster_id),
            "title": title,
            "topics": sorted(topics),
            "outlets": outlets,
        }
        try:
            self._mongo.upsert_compare(doc)
            self._db.add_event("publish", f"coverage upsert {doc['clusterId']}")
        except Exception as exc:
            self._mongo.deadletter("coverage", str(cluster_id), str(exc), doc)
            self._db.add_event("publish", f"coverage failed: {exc}")

    def publish_thread(self, thread_id: str) -> None:
        if not self.enabled or not self._mongo:
            return
        thread = self._db.get_thread_bundle(thread_id)
        if not thread:
            return
        # The API only reads BSON dates (text dates showed every entry as "now").
        thread["openedAt"] = _parse_time(thread["openedAt"])
        thread["closedAt"] = _parse_time(thread["closedAt"]) if thread["closedAt"] else None
        thread.pop("updatedAt", None)
        for update in thread["updates"]:
            update["at"] = _parse_time(update["at"])
        try:
            self._mongo.upsert_thread(thread)
            self._mongo.set_story_thread(
                [update["storyId"] for update in thread["updates"]], thread["threadId"]
            )
            self._db.add_event("publish", f"storyline upsert {thread['threadId']}")
        except Exception as exc:
            self._mongo.deadletter("thread", thread_id, str(exc), thread)
            self._db.add_event("publish", f"storyline failed: {exc}")


    def prune_published(self, *, story_days: int, closed_thread_days: int) -> dict[str, int]:
        """Delete what the app no longer shows, from S3 first and then MongoDB.

        - A story is removed ``story_days`` after it was published, unless a live
          storyline (open, or closed less than ``closed_thread_days`` ago) lists it.
        - A closed storyline is removed ``closed_thread_days`` after closing, with its
          stories (unless another live storyline still lists them).
        S3 goes first: if it fails, the Mongo docs stay and the next round retries.
        """
        if not self.enabled or not self._mongo or not self._s3:
            return {"stories": 0, "threads": 0}
        now = datetime.now(timezone.utc)
        story_cutoff = now - timedelta(days=story_days)
        thread_cutoff = now - timedelta(days=closed_thread_days)

        expired_threads = self._mongo.expired_threads(thread_cutoff)
        expired_ids = [t["threadId"] for t in expired_threads]
        thread_story_ids = [
            u["storyId"] for t in expired_threads for u in t.get("updates") or [] if u.get("storyId")
        ]
        candidates = dict(self._mongo.expired_story_keys(story_cutoff))
        candidates.update(dict(self._mongo.story_keys(thread_story_ids)) if thread_story_ids else {})

        removed = 0
        ids = list(candidates)
        for start in range(0, len(ids), 500):
            chunk = ids[start : start + 500]
            held = self._mongo.stories_held_by_threads(chunk, except_threads=expired_ids)
            doomed = [sid for sid in chunk if sid not in held]
            keys = [candidates[sid] for sid in doomed if candidates[sid]]
            if keys:
                self._s3.delete_keys(keys)
            removed += self._mongo.delete_stories(doomed)
        threads = self._mongo.delete_threads(expired_ids) if expired_ids else 0
        self._mongo.delete_stale_side_docs(story_cutoff)
        if removed or threads:
            self._db.add_event(
                "maintenance", f"published store: removed {removed} stories, {threads} closed storylines"
            )
        return {"stories": removed, "threads": threads}

    def heartbeat(self) -> None:
        """Tell the API this box is alive (read by GET /v1/health/ingest)."""
        if not self.enabled or not self._mongo:
            return
        stats = self._db.heartbeat_stats()
        self._mongo.write_heartbeat(
            {
                "lastBriefAt": _parse_time(stats["last_brief_at"]) if stats["last_brief_at"] else None,
                "backlog": stats["backlog"],
                "ttsStatus": stats["tts_status"],
                "host": socket.gethostname(),
            }
        )

    def close_thread(self, thread_id: str, closed_at: str) -> None:
        if self.enabled and self._mongo:
            self._mongo.close_thread(thread_id_for(thread_id), _parse_time(closed_at))


class AsyncPublisher:
    """Run every Mongo/S3 call on one background thread so the event loop never blocks.

    The thread owns its own SQLite connection (sqlite3 objects are thread-bound), and
    a single worker keeps publishes for one story in the order they were requested.
    """

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="publish")
        self._inner: Publisher | None = None

    async def start(self) -> None:
        self._inner = await self._run(lambda: Publisher(Database(self._db_path)))

    @property
    def enabled(self) -> bool:
        return self._inner is not None and self._inner.enabled

    async def _run(self, fn, *args, **kwargs):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self._executor, functools.partial(fn, *args, **kwargs))

    async def story_text(self, article: dict[str, Any], *, audio_status: str = "pending") -> None:
        await self._run(self._inner.publish_story_text, article, audio_status=audio_status)

    async def audio_file(
        self, article: dict[str, Any], path: Path, *, content_type: str, duration_ms: int | None
    ) -> str | None:
        return await self._run(
            self._inner.publish_audio_file,
            article,
            path,
            content_type=content_type,
            duration_ms=duration_ms,
        )

    async def audio_unavailable(self, article: dict[str, Any]) -> None:
        await self._run(self._inner.mark_audio_unavailable, article)

    async def coverage(self, cluster_id: str) -> None:
        await self._run(self._inner.publish_coverage, cluster_id)

    async def thread(self, thread_id: str) -> None:
        await self._run(self._inner.publish_thread, thread_id)

    async def prune_published(self, *, story_days: int, closed_thread_days: int) -> dict[str, int]:
        return await self._run(
            self._inner.prune_published, story_days=story_days, closed_thread_days=closed_thread_days
        )

    async def close_thread(self, thread_id: str, closed_at: str) -> None:
        await self._run(self._inner.close_thread, thread_id, closed_at)

    async def heartbeat(self) -> None:
        await self._run(self._inner.heartbeat)

    async def close(self) -> None:
        if self._inner is not None:
            inner = self._inner
            await self._run(lambda: (inner.close(), inner._db.close()))
        self._executor.shutdown(wait=True)
