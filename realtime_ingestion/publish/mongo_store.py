"""MongoDB publish store for stories, coverage, and storylines."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pymongo import ASCENDING, DESCENDING, MongoClient, ReturnDocument
from pymongo.collection import Collection
from pymongo.database import Database as MongoDatabase


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class MongoStore:
    def __init__(self, uri: str, database: str) -> None:
        self._client = MongoClient(uri, serverSelectionTimeoutMS=5_000)
        self._db: MongoDatabase = self._client[database]
        self.stories: Collection = self._db["stories"]
        self.compares: Collection = self._db["compares"]
        self.threads: Collection = self._db["threads"]
        self.deadletters: Collection = self._db["publish_deadletters"]
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

    def ping(self) -> None:
        self._client.admin.command("ping")

    def close(self) -> None:
        self._client.close()

    def upsert_story(self, doc: dict[str, Any]) -> dict[str, Any]:
        doc = {**doc, "updatedAt": _utc_now()}
        return self.stories.find_one_and_update(
            {"storyId": doc["storyId"]},
            {"$set": doc, "$setOnInsert": {"createdAt": _utc_now()}},
            upsert=True,
            return_document=ReturnDocument.AFTER,
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
        listen = status == "ready"
        self.stories.update_one(
            {"storyId": story_id},
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
        doc = {**doc, "updatedAt": _utc_now()}
        self.threads.update_one(
            {"threadId": doc["threadId"]},
            {"$set": doc},
            upsert=True,
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
