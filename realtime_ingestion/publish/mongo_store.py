"""MongoDB publish store for stories, coverage, and storylines."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pymongo import ASCENDING, DESCENDING, MongoClient, ReturnDocument
from pymongo.collection import Collection
from pymongo.database import Database as MongoDatabase


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _as_time(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    try:
        moment = datetime.fromisoformat(str(value))
        return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)
    except ValueError:
        return datetime.min.replace(tzinfo=timezone.utc)


class MongoStore:
    def __init__(self, uri: str, database: str) -> None:
        self._client = MongoClient(uri, serverSelectionTimeoutMS=5_000)
        self._db: MongoDatabase = self._client[database]
        self.stories: Collection = self._db["stories"]
        self.compares: Collection = self._db["compares"]
        self.threads: Collection = self._db["threads"]
        self.deadletters: Collection = self._db["publish_deadletters"]
        self.ingest_status: Collection = self._db["ingest_status"]
        self._ensure_indexes()

    def _ensure_indexes(self) -> None:
        self.stories.create_index("storyId", unique=True)
        self.stories.create_index([("topic", ASCENDING), ("publishedAt", DESCENDING)])
        self.stories.create_index(
            [("listenReady", ASCENDING), ("topic", ASCENDING), ("publishedAt", DESCENDING)]
        )
        self.stories.create_index("clusterId")
        self.stories.create_index("threadId")
        self.compares.create_index("clusterId", unique=True)
        self.compares.create_index([("updatedAt", DESCENDING)])
        self.threads.create_index("threadId", unique=True)
        self.threads.create_index([("status", ASCENDING), ("updatedAt", DESCENDING)])
        # Retention queries.
        self.stories.create_index("publishedAt")
        self.threads.create_index("updates.storyId")
        self.threads.create_index([("status", ASCENDING), ("closedAt", ASCENDING)])

    def ping(self) -> None:
        self._client.admin.command("ping")

    def close(self) -> None:
        self._client.close()

    def upsert_story(self, doc: dict[str, Any]) -> dict[str, Any]:
        """Write text fields. Audio fields are only defaulted on insert, so a text
        re-publish never wipes an attached audioKey or flips listenReady off."""
        doc = {**doc, "updatedAt": _utc_now()}
        audio_defaults = {
            "audioStatus": "pending",
            "audioKey": None,
            "audioContentType": None,
            "audioDurationMs": None,
            "listenReady": False,
        }
        for key in audio_defaults:
            doc.pop(key, None)
        return self.stories.find_one_and_update(
            {"storyId": doc["storyId"]},
            {"$set": doc, "$setOnInsert": {"createdAt": _utc_now(), **audio_defaults}},
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )

    def set_story_thread(self, story_ids: list[str], thread_id: str) -> None:
        if story_ids:
            self.stories.update_many(
                {"storyId": {"$in": story_ids}},
                {"$set": {"threadId": thread_id, "updatedAt": _utc_now()}},
            )

    def attach_audio(
        self,
        story_id: str,
        *,
        audio_key: str,
        audio_content_type: str,
        audio_duration_ms: int | None,
    ) -> dict[str, Any] | None:
        return self.stories.find_one_and_update(
            {"storyId": story_id},
            {
                "$set": {
                    "audioKey": audio_key,
                    "audioContentType": audio_content_type,
                    "audioDurationMs": audio_duration_ms,
                    "audioStatus": "ready",
                    "listenReady": True,
                    "updatedAt": _utc_now(),
                }
            },
            return_document=ReturnDocument.AFTER,
        )

    def mark_audio_status(self, story_id: str, status: str) -> None:
        """Record a non-ready outcome. Never downgrades a story that already has audio."""
        listen = status == "ready"
        self.stories.update_one(
            {"storyId": story_id, "audioStatus": {"$ne": "ready"}},
            {
                "$set": {
                    "audioStatus": status,
                    "listenReady": listen,
                    "updatedAt": _utc_now(),
                }
            },
        )

    def upsert_compare(self, doc: dict[str, Any]) -> None:
        doc = {**doc, "updatedAt": _utc_now()}
        self.compares.update_one(
            {"clusterId": doc["clusterId"]},
            {"$set": doc},
            upsert=True,
        )

    def upsert_thread(self, doc: dict[str, Any]) -> None:
        """Merge the timeline by storyId instead of replacing it: the ingest box prunes
        its local copy, so Mongo keeps entries the box no longer has."""
        doc = {**doc, "updatedAt": _utc_now()}
        existing = self.threads.find_one({"threadId": doc["threadId"]}, {"updates": 1}) or {}
        merged = {u["storyId"]: u for u in existing.get("updates") or [] if u.get("storyId")}
        for update in doc.get("updates") or []:
            kept = merged.get(update["storyId"], {})
            # Never downgrade audio already attached to an entry.
            if kept.get("audioStatus") == "ready" and update.get("audioStatus") != "ready":
                update = {**update, "audioStatus": "ready", "audioKey": kept.get("audioKey")}
            merged[update["storyId"]] = update
        doc["updates"] = sorted(merged.values(), key=lambda u: _as_time(u.get("at")), reverse=True)
        self.threads.update_one({"threadId": doc["threadId"]}, {"$set": doc}, upsert=True)

    def mark_thread_audio(self, story_id: str, audio_key: str) -> None:
        """A story's audio landed: make it playable inside any storyline that lists it."""
        self.threads.update_many(
            {"updates.storyId": story_id},
            {"$set": {"updates.$[u].audioStatus": "ready", "updates.$[u].audioKey": audio_key}},
            array_filters=[{"u.storyId": story_id}],
        )

    def close_thread(self, thread_id: str, closed_at: datetime) -> None:
        self.threads.update_one(
            {"threadId": thread_id},
            {"$set": {"status": "closed", "closedAt": closed_at, "updatedAt": _utc_now()}},
        )

    # ----- retention ----------------------------------------------------------------

    def expired_threads(self, closed_before: datetime) -> list[dict[str, Any]]:
        """Closed storylines past their window. Older pipeline docs stored closedAt as text."""
        return list(
            self.threads.find(
                {
                    "status": "closed",
                    "$or": [
                        {"closedAt": {"$lt": closed_before}},
                        {"closedAt": {"$lt": closed_before.isoformat()}},
                    ],
                },
                {"threadId": 1, "updates.storyId": 1},
            )
        )

    def expired_story_keys(self, published_before: datetime) -> list[tuple[str, str | None]]:
        return [
            (doc["storyId"], doc.get("audioKey"))
            for doc in self.stories.find(
                {"publishedAt": {"$lt": published_before}}, {"storyId": 1, "audioKey": 1}
            )
        ]

    def story_keys(self, story_ids: list[str]) -> list[tuple[str, str | None]]:
        return [
            (doc["storyId"], doc.get("audioKey"))
            for doc in self.stories.find({"storyId": {"$in": story_ids}}, {"storyId": 1, "audioKey": 1})
        ]

    def stories_held_by_threads(self, story_ids: list[str], *, except_threads: list[str]) -> set[str]:
        """Which of these stories still appear in a live storyline (open, or closed recently)."""
        return set(
            self.threads.distinct(
                "updates.storyId",
                {"updates.storyId": {"$in": story_ids}, "threadId": {"$nin": except_threads}},
            )
        ) & set(story_ids)

    def delete_stories(self, story_ids: list[str]) -> int:
        return self.stories.delete_many({"storyId": {"$in": story_ids}}).deleted_count

    def delete_threads(self, thread_ids: list[str]) -> int:
        return self.threads.delete_many({"threadId": {"$in": thread_ids}}).deleted_count

    def delete_stale_side_docs(self, before: datetime) -> None:
        self.compares.delete_many({"updatedAt": {"$lt": before}})
        self.deadletters.delete_many({"at": {"$lt": before}})

    def write_heartbeat(self, fields: dict[str, Any]) -> None:
        self.ingest_status.update_one(
            {"_id": "ingest"}, {"$set": {**fields, "lastSeenAt": _utc_now()}}, upsert=True
        )

    def deadletter(self, kind: str, ref: str, error: str, payload: dict[str, Any] | None = None) -> None:
        self.deadletters.insert_one(
            {
                "kind": kind,
                "ref": ref,
                "error": error,
                "payload": payload or {},
                "at": _utc_now(),
            }
        )
