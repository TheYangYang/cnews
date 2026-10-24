"""Retention pruning (local + MongoDB/S3), storyline merge, upload retry.

Run: python -m unittest discover -s realtime_ingestion/tests -t .
Mongo tests use a throwaway database on MONGODB_URI and skip when Mongo is down.
"""

from __future__ import annotations

import tempfile
import unittest
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from pymongo import MongoClient

from realtime_ingestion import config, maintenance
from realtime_ingestion.database import Database, iso, utcnow
from realtime_ingestion.publish.mongo_store import MongoStore
from realtime_ingestion.publish.publisher import Publisher


class FakePublisher:
    def __init__(self, fail: bool) -> None:
        self.fail = fail
        self.sent: list[str] = []

    enabled = True

    async def audio_file(self, article, path, *, content_type, duration_ms):
        if self.fail:
            raise ConnectionError("S3 unreachable")
        self.sent.append(path.name)


class FakeS3:
    def __init__(self) -> None:
        self.deleted: list[str] = []

    def delete_keys(self, keys: list[str]) -> None:
        self.deleted.extend(keys)


class LocalStoreTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self._audio_dir = config.AUDIO_DIR
        config.AUDIO_DIR = root / "audio"
        config.AUDIO_DIR.mkdir()
        self.db = Database(root / "news.db")
        self.db.init()
        self.db.seed_feeds(config.FEEDS[:1])
        self.feed_id = self.db.due_feeds()[0]["id"]

    def tearDown(self) -> None:
        self.db.close()
        config.AUDIO_DIR = self._audio_dir
        self.tmp.cleanup()

    def article(self, n: int, *, age_days: float) -> int:
        pk, _ = self.db.insert_article(
            feed_id=self.feed_id,
            article_id=f"a{n}",
            url=f"https://example.ca/{n}",
            title=f"Unrelated headline number {n} {n * 104729}",
            title_hash=f"h{n}",
            image_url=None,
            category="Canada",
            place="Canada",
            outlet="CBC",
            raw_text="full article text " * 50,
            published_at=None,
        )
        self.db.save_summary(pk, summary="A brief.", summary_words=2, summary_engine="t")
        when = iso(utcnow() - timedelta(days=age_days))
        self.db.conn.execute(
            "UPDATE articles SET first_seen_at = ?, summarized_at = ? WHERE id = ?", (when, when, pk)
        )
        self.db.conn.commit()
        return pk

    def test_text_is_dropped_once_briefed(self) -> None:
        row = self.db.get_article(self.article(1, age_days=0))
        self.assertEqual(row["summary"], "A brief.")
        self.assertIsNone(row["raw_text"])
        self.assertIsNone(row["clean_text"])

    def test_prune_keeps_dedupe_window_and_open_storylines(self) -> None:
        old = self.article(1, age_days=10)
        on_open_thread = self.article(2, age_days=10)
        recent = self.article(3, age_days=2)
        self.db.create_thread(title="Strike vote", open_question="outcome", article_id=on_open_thread, note="n")
        (config.AUDIO_DIR / f"{old}.opus").write_bytes(b"x")

        result = maintenance.prune(self.db)

        self.assertEqual(result["deleted_ids"], [old])
        self.assertFalse((config.AUDIO_DIR / f"{old}.opus").exists())
        self.assertIsNotNone(self.db.get_article(on_open_thread))
        # Inside the 7-day window the row stays, so the feed's copy is not briefed again.
        self.assertIsNotNone(self.db.get_article(recent))
        self.assertTrue(self.db.feed_carries(self.feed_id, "https://example.ca/3", "h3"))

    def test_quiet_storylines_close(self) -> None:
        pk = self.article(4, age_days=0)
        thread = self.db.create_thread(title="Fire", open_question="containment", article_id=pk, note="n")
        old = iso(utcnow() - timedelta(days=8))
        self.db.conn.execute("UPDATE threads SET updated_at = ? WHERE id = ?", (old, thread))
        self.db.conn.commit()
        closed = self.db.close_stale_threads(quiet_days=7)
        self.assertEqual([tid for tid, _ in closed], [thread])
        self.assertEqual(self.db.open_threads(), [])

    async def test_failed_upload_is_retried_then_local_file_removed(self) -> None:
        pk = self.article(5, age_days=0)
        audio = config.AUDIO_DIR / f"{pk}.opus"
        audio.write_bytes(b"opus")
        self.db.save_audio(pk, audio_path=audio.name, audio_status="upload_failed")

        await maintenance.retry_failed_uploads(self.db, FakePublisher(fail=True))
        self.assertEqual(self.db.get_article(pk)["audio_status"], "upload_failed")
        self.assertTrue(audio.exists())

        publisher = FakePublisher(fail=False)
        await maintenance.retry_failed_uploads(self.db, publisher)
        self.assertEqual(publisher.sent, [audio.name])
        self.assertEqual(self.db.get_article(pk)["audio_status"], "ready")
        self.assertFalse(audio.exists())


def _mongo_available() -> bool:
    try:
        MongoClient(config.MONGODB_URI, serverSelectionTimeoutMS=800).admin.command("ping")
        return True
    except Exception:
        return False


@unittest.skipUnless(_mongo_available(), "MongoDB not reachable")
class PublishedStoreTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.db_name = f"cnews_test_{uuid.uuid4().hex[:10]}"
        self.mongo = MongoStore(config.MONGODB_URI, self.db_name)
        self.local = Database(Path(self.tmp.name) / "news.db")
        self.local.init()
        self.s3 = FakeS3()
        publisher = Publisher.__new__(Publisher)
        publisher._db, publisher._mongo, publisher._s3, publisher._enabled = self.local, self.mongo, self.s3, True
        self.publisher = publisher
        self.now = datetime.now(timezone.utc)

    def tearDown(self) -> None:
        self.mongo._client.drop_database(self.db_name)
        self.mongo.close()
        self.local.close()
        self.tmp.cleanup()

    def story(self, sid: str, *, age_days: float) -> None:
        self.mongo.stories.insert_one(
            {"storyId": sid, "publishedAt": self.now - timedelta(days=age_days), "audioKey": f"audio/{sid}.opus"}
        )

    def thread(self, tid: str, story_ids: list[str], *, closed_days_ago: float | None) -> None:
        self.mongo.threads.insert_one(
            {
                "threadId": tid,
                "status": "open" if closed_days_ago is None else "closed",
                "closedAt": None if closed_days_ago is None else self.now - timedelta(days=closed_days_ago),
                "updates": [{"storyId": sid} for sid in story_ids],
            }
        )

    def ids(self, collection) -> set[str]:
        key = "storyId" if collection is self.mongo.stories else "threadId"
        return {doc[key] for doc in collection.find({}, {key: 1})}

    def test_retention_rules(self) -> None:
        self.story("fresh", age_days=3)
        self.story("old", age_days=20)
        self.story("old_in_open_thread", age_days=40)
        self.story("old_in_recently_closed", age_days=25)
        self.story("in_expired_thread", age_days=40)
        self.thread("thread_open", ["old_in_open_thread"], closed_days_ago=None)
        self.thread("thread_recent", ["old_in_recently_closed"], closed_days_ago=10)
        self.thread("thread_expired", ["in_expired_thread"], closed_days_ago=31)

        result = self.publisher.prune_published(story_days=14, closed_thread_days=30)

        self.assertEqual(
            self.ids(self.mongo.stories), {"fresh", "old_in_open_thread", "old_in_recently_closed"}
        )
        self.assertEqual(self.ids(self.mongo.threads), {"thread_open", "thread_recent"})
        self.assertEqual(sorted(self.s3.deleted), ["audio/in_expired_thread.opus", "audio/old.opus"])
        self.assertEqual(result, {"stories": 2, "threads": 1})

    def test_s3_failure_keeps_mongo_docs(self) -> None:
        self.story("old", age_days=20)

        def broken(keys):
            raise RuntimeError("S3 down")

        self.s3.delete_keys = broken
        with self.assertRaises(RuntimeError):
            self.publisher.prune_published(story_days=14, closed_thread_days=30)
        self.assertEqual(self.ids(self.mongo.stories), {"old"})

    def test_heartbeat_reports_last_brief_and_backlog(self) -> None:
        self.local.seed_feeds(config.FEEDS[:1])
        feed_id = self.local.due_feeds()[0]["id"]
        pk, _ = self.local.insert_article(
            feed_id=feed_id, article_id="a", url="https://example.ca/hb", title="Heartbeat story",
            title_hash="hb", image_url=None, category="Canada", place="Canada", outlet="CBC",
            raw_text="text", published_at=None,
        )
        self.local.save_summary(pk, summary="A brief.", summary_words=2, summary_engine="t")

        self.publisher.heartbeat()

        doc = self.mongo.ingest_status.find_one({"_id": "ingest"})
        self.assertIsInstance(doc["lastSeenAt"], datetime)
        self.assertIsInstance(doc["lastBriefAt"], datetime)
        self.assertEqual(doc["backlog"], 0)

    def test_published_storyline_has_dates_and_original_link(self) -> None:
        self.local.seed_feeds(config.FEEDS[:1])
        feed_id = self.local.due_feeds()[0]["id"]
        pk, _ = self.local.insert_article(
            feed_id=feed_id, article_id="a", url="https://example.ca/strike", title="Strike vote set",
            title_hash="h", image_url=None, category="Canada", place="Canada", outlet="CBC",
            raw_text="text", published_at=None,
        )
        self.local.save_summary(pk, summary="Workers vote Friday.", summary_words=3, summary_engine="t")
        tid = self.local.create_thread(title="Strike", open_question="outcome", article_id=pk, note="n")

        self.publisher.publish_thread(tid)

        doc = self.mongo.threads.find_one({"threadId": f"thread_{tid}"})
        self.assertIsInstance(doc["openedAt"], datetime)
        self.assertIsInstance(doc["updates"][0]["at"], datetime)
        self.assertEqual(doc["updates"][0]["sourceUrl"], "https://example.ca/strike")

    def test_storyline_publish_merges_instead_of_replacing(self) -> None:
        at = lambda h: self.now - timedelta(hours=h)  # noqa: E731
        self.mongo.upsert_thread(
            {"threadId": "t1", "updates": [{"storyId": "s1", "at": at(5), "audioStatus": "ready", "audioKey": "k1"}]}
        )
        # Ingest box later knows only the new update (s1 was pruned locally) ...
        self.mongo.upsert_thread({"threadId": "t1", "updates": [{"storyId": "s2", "at": at(1), "audioStatus": "pending"}]})
        # ... or re-sends s1 without audio: the attached audio must survive.
        self.mongo.upsert_thread({"threadId": "t1", "updates": [{"storyId": "s1", "at": at(5), "audioStatus": "pending"}]})
        self.mongo.mark_thread_audio("s2", "k2")

        updates = self.mongo.threads.find_one({"threadId": "t1"})["updates"]
        self.assertEqual([u["storyId"] for u in updates], ["s2", "s1"])
        self.assertEqual([(u["audioStatus"], u["audioKey"]) for u in updates], [("ready", "k2"), ("ready", "k1")])


if __name__ == "__main__":
    unittest.main()
