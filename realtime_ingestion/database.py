"""SQLite feed registry, article rows, and cross-outlet story groups."""

from __future__ import annotations

import json
import re
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from realtime_ingestion.config import SEEN_TTL_SECONDS
from realtime_ingestion.framing import needs_refresh
from realtime_ingestion.normalize import same_story

SCHEMA = """
CREATE TABLE IF NOT EXISTS feeds (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    url TEXT NOT NULL UNIQUE,
    poll_interval_seconds INTEGER NOT NULL,
    outlet TEXT,
    category TEXT,
    place TEXT,
    etag TEXT,
    last_modified TEXT,
    body_hash TEXT,
    last_fetched_at TEXT,
    last_status INTEGER,
    last_note TEXT,
    last_new_count INTEGER NOT NULL DEFAULT 0,
    last_duplicate_count INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS articles (
    id INTEGER PRIMARY KEY,
    feed_id INTEGER NOT NULL,
    article_id TEXT,
    url TEXT NOT NULL,
    title TEXT NOT NULL,
    title_hash TEXT NOT NULL,
    image_url TEXT,
    category TEXT,
    place TEXT,
    outlet TEXT,
    cluster_id TEXT,
    raw_text TEXT,
    clean_text TEXT,
    summary TEXT,
    summary_words INTEGER,
    summary_engine TEXT,
    audio_path TEXT,
    audio_status TEXT,
    published_at TEXT,
    first_seen_at TEXT NOT NULL,
    summarized_at TEXT,
    FOREIGN KEY (feed_id) REFERENCES feeds(id)
);

CREATE TABLE IF NOT EXISTS article_feeds (
    article_id INTEGER NOT NULL,
    feed_id INTEGER NOT NULL,
    PRIMARY KEY (article_id, feed_id)
);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY,
    ts TEXT NOT NULL,
    stage TEXT NOT NULL,
    message TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS runtime (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS framings (
    cluster_id TEXT PRIMARY KEY,
    source_key TEXT NOT NULL,
    notes_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS threads (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    status TEXT NOT NULL,
    open_question TEXT NOT NULL,
    opened_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    closed_at TEXT
);

CREATE TABLE IF NOT EXISTS thread_updates (
    id INTEGER PRIMARY KEY,
    thread_id TEXT NOT NULL,
    article_id INTEGER NOT NULL UNIQUE,
    note TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS thread_reviews (
    article_id INTEGER PRIMARY KEY
);

CREATE INDEX IF NOT EXISTS idx_articles_seen ON articles(first_seen_at);
CREATE INDEX IF NOT EXISTS idx_articles_url ON articles(url);
CREATE INDEX IF NOT EXISTS idx_articles_title ON articles(title_hash);
"""

_ADDED_COLUMNS = (
    ("feeds", "outlet", "TEXT"),
    ("feeds", "category", "TEXT"),
    ("feeds", "place", "TEXT"),
    ("articles", "place", "TEXT"),
    ("articles", "outlet", "TEXT"),
    ("articles", "cluster_id", "TEXT"),
)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def iso(moment: datetime | None = None) -> str:
    return (moment or utcnow()).isoformat()


class Database:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row

    def init(self) -> None:
        self.conn.executescript(SCHEMA)
        for table, column, typedef in _ADDED_COLUMNS:
            self._add_column(table, column, typedef)
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_articles_cluster ON articles(cluster_id)"
        )
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA busy_timeout=5000")
        self.conn.commit()

    def _add_column(self, table: str, column: str, typedef: str) -> None:
        have = {row[1] for row in self.conn.execute(f"PRAGMA table_info({table})")}
        if column not in have:
            self.conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {typedef}")

    def close(self) -> None:
        self.conn.close()

    def seed_feeds(self, feeds: list[dict[str, Any]]) -> None:
        for feed in feeds:
            self.conn.execute(
                """
                INSERT INTO feeds (name, url, poll_interval_seconds, outlet, category, place)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(url) DO UPDATE SET
                    name = excluded.name,
                    poll_interval_seconds = excluded.poll_interval_seconds,
                    outlet = excluded.outlet,
                    category = excluded.category,
                    place = excluded.place
                """,
                (
                    feed["name"],
                    feed["url"],
                    feed["poll_interval_seconds"],
                    feed.get("outlet") or feed["name"],
                    feed.get("category") or "Canada",
                    feed.get("place") or "Canada",
                ),
            )
        self.conn.commit()

    def backfill(self) -> None:
        """Label older rows from their feed and group headlines that match."""
        self.conn.execute(
            """
            INSERT OR IGNORE INTO article_feeds (article_id, feed_id)
            SELECT id, feed_id FROM articles
            """
        )
        self.conn.execute(
            """
            UPDATE articles
            SET
                outlet = (SELECT outlet FROM feeds WHERE feeds.id = articles.feed_id),
                place = (SELECT place FROM feeds WHERE feeds.id = articles.feed_id),
                category = COALESCE(
                    (SELECT category FROM feeds WHERE feeds.id = articles.feed_id),
                    category
                )
            WHERE outlet IS NULL OR outlet = ''
            """
        )
        rows = self.conn.execute(
            "SELECT id, title, cluster_id FROM articles ORDER BY id"
        ).fetchall()
        known: list[tuple[str, str]] = []
        for row in rows:
            if row["cluster_id"]:
                known.append((row["title"], row["cluster_id"]))
                continue
            cluster_id = None
            for title, existing in reversed(known[-80:]):
                if same_story(row["title"], title):
                    cluster_id = existing
                    break
            if cluster_id is None:
                cluster_id = uuid.uuid4().hex
            self.conn.execute(
                "UPDATE articles SET cluster_id = ? WHERE id = ?",
                (cluster_id, row["id"]),
            )
            known.append((row["title"], cluster_id))
        self.regroup_recent()
        self.drop_copied_thread_ids()
        self.merge_open_threads()
        self.prune_unrelated_updates()
        self.attach_cluster_mates()
        self.conn.commit()

    def due_feeds(self) -> list[dict[str, Any]]:
        now = utcnow()
        due: list[dict[str, Any]] = []
        for row in self.conn.execute("SELECT * FROM feeds ORDER BY id"):
            feed = dict(row)
            last = feed["last_fetched_at"]
            if not last:
                due.append(feed)
                continue
            elapsed = now - datetime.fromisoformat(last)
            if elapsed >= timedelta(seconds=feed["poll_interval_seconds"]):
                due.append(feed)
        due.sort(key=lambda feed: (feed["poll_interval_seconds"], feed["id"]))
        return due

    def _cutoff(self) -> str:
        return iso(utcnow() - timedelta(seconds=SEEN_TTL_SECONDS))

    def feed_carries(self, feed_id: int, url: str, title_hash: str) -> bool:
        row = self.conn.execute(
            """
            SELECT 1
            FROM articles AS article
            JOIN article_feeds AS link ON link.article_id = article.id
            WHERE link.feed_id = ?
              AND article.first_seen_at >= ?
              AND (article.url = ? OR article.title_hash = ?)
            LIMIT 1
            """,
            (feed_id, self._cutoff(), url, title_hash),
        ).fetchone()
        return row is not None

    def attach_feed(self, url: str, feed_id: int) -> int | None:
        """Record that this feed also carried an article we already stored."""
        row = self.conn.execute(
            """
            SELECT id FROM articles
            WHERE url = ? AND first_seen_at >= ?
            ORDER BY id
            LIMIT 1
            """,
            (url, self._cutoff()),
        ).fetchone()
        if row is None:
            return None
        self.conn.execute(
            """
            INSERT OR IGNORE INTO article_feeds (article_id, feed_id)
            VALUES (?, ?)
            """,
            (int(row["id"]), feed_id),
        )
        self.conn.commit()
        return int(row["id"])

    def match_cluster(self, title: str) -> str | None:
        cutoff = iso(utcnow() - timedelta(hours=48))
        rows = self.conn.execute(
            """
            SELECT title, cluster_id
            FROM articles
            WHERE cluster_id IS NOT NULL
              AND COALESCE(published_at, first_seen_at) >= ?
            ORDER BY id DESC
            LIMIT 300
            """,
            (cutoff,),
        ).fetchall()
        for row in rows:
            if same_story(title, row["title"]):
                return str(row["cluster_id"])
        return None

    def absorb_matches(self, title: str, cluster_id: str) -> bool:
        """Pull other recent cards into this group when the new headline matches them."""
        cutoff = iso(utcnow() - timedelta(hours=48))
        rows = self.conn.execute(
            """
            SELECT title, cluster_id
            FROM articles
            WHERE cluster_id IS NOT NULL
              AND cluster_id != ?
              AND COALESCE(published_at, first_seen_at) >= ?
            ORDER BY id DESC
            LIMIT 300
            """,
            (cluster_id, cutoff),
        ).fetchall()
        merge_ids = {
            str(row["cluster_id"])
            for row in rows
            if same_story(title, row["title"])
        }
        for other_id in merge_ids:
            self.conn.execute(
                "UPDATE articles SET cluster_id = ? WHERE cluster_id = ?",
                (cluster_id, other_id),
            )
        return bool(merge_ids)

    def regroup_recent(self) -> int:
        """Apply the headline rule again to stories from the last three days."""
        cutoff = iso(utcnow() - timedelta(hours=72))
        rows = list(
            self.conn.execute(
                """
                SELECT id, title, cluster_id
                FROM articles
                WHERE COALESCE(published_at, first_seen_at) >= ?
                ORDER BY id
                """,
                (cutoff,),
            ).fetchall()
        )
        parent = list(range(len(rows)))

        def find(index: int) -> int:
            while parent[index] != index:
                parent[index] = parent[parent[index]]
                index = parent[index]
            return index

        for index, row in enumerate(rows):
            for earlier in range(max(0, index - 120), index):
                if same_story(row["title"], rows[earlier]["title"]):
                    parent[find(index)] = find(earlier)
        groups: dict[int, list] = {}
        for index, row in enumerate(rows):
            groups.setdefault(find(index), []).append(row)
        changed = 0
        for members in groups.values():
            if len(members) < 2:
                continue
            counts: dict[str, int] = {}
            for member in members:
                if member["cluster_id"]:
                    counts[member["cluster_id"]] = counts.get(member["cluster_id"], 0) + 1
            cluster_id = max(counts, key=counts.get) if counts else uuid.uuid4().hex
            for member in members:
                if member["cluster_id"] == cluster_id:
                    continue
                self.conn.execute(
                    "UPDATE articles SET cluster_id = ? WHERE id = ?",
                    (cluster_id, member["id"]),
                )
                changed += 1
        return changed

    def mark_fetch(
        self,
        feed_id: int,
        *,
        status: int | None,
        etag: str | None,
        last_modified: str | None,
        body_hash: str | None,
        note: str,
        new_count: int,
        duplicate_count: int,
    ) -> None:
        self.conn.execute(
            """
            UPDATE feeds SET
                etag = ?,
                last_modified = ?,
                body_hash = ?,
                last_fetched_at = ?,
                last_status = ?,
                last_note = ?,
                last_new_count = ?,
                last_duplicate_count = ?
            WHERE id = ?
            """,
            (
                etag,
                last_modified,
                body_hash,
                iso(),
                status,
                note,
                new_count,
                duplicate_count,
                feed_id,
            ),
        )
        self.conn.commit()

    def insert_article(
        self,
        *,
        feed_id: int,
        article_id: str,
        url: str,
        title: str,
        title_hash: str,
        image_url: str | None,
        category: str,
        place: str,
        outlet: str,
        raw_text: str,
        published_at: str | None,
    ) -> tuple[int | None, bool]:
        """Insert one outlet's report. The bool is true when it joined an existing group."""
        try:
            self.conn.execute("BEGIN IMMEDIATE")
            if self.feed_carries(feed_id, url, title_hash):
                self.conn.rollback()
                return None, False
            existing_url = self.conn.execute(
                """
                SELECT id FROM articles
                WHERE url = ? AND first_seen_at >= ?
                LIMIT 1
                """,
                (url, self._cutoff()),
            ).fetchone()
            if existing_url:
                self.conn.execute(
                    """
                    INSERT OR IGNORE INTO article_feeds (article_id, feed_id)
                    VALUES (?, ?)
                    """,
                    (int(existing_url["id"]), feed_id),
                )
                self.conn.commit()
                return None, False
            cluster_id = self.match_cluster(title) or uuid.uuid4().hex
            joined = cluster_id is not None and self.conn.execute(
                "SELECT 1 FROM articles WHERE cluster_id = ? LIMIT 1",
                (cluster_id,),
            ).fetchone() is not None
            cursor = self.conn.execute(
                """
                INSERT INTO articles (
                    feed_id, article_id, url, title, title_hash, image_url,
                    category, place, outlet, cluster_id, raw_text, published_at, first_seen_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    feed_id,
                    article_id,
                    url,
                    title,
                    title_hash,
                    image_url,
                    category,
                    place,
                    outlet,
                    cluster_id,
                    raw_text,
                    published_at,
                    iso(),
                ),
            )
            article_pk = int(cursor.lastrowid)
            self.conn.execute(
                """
                INSERT OR IGNORE INTO article_feeds (article_id, feed_id)
                VALUES (?, ?)
                """,
                (article_pk, feed_id),
            )
            joined = joined or self.absorb_matches(title, cluster_id)
            self.conn.commit()
            return article_pk, joined
        except Exception:
            self.conn.rollback()
            raise

    def get_article(self, article_id: int) -> dict[str, Any] | None:
        row = self.conn.execute(
            "SELECT * FROM articles WHERE id = ?", (article_id,)
        ).fetchone()
        return dict(row) if row else None

    def pending_articles(self) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            """
            SELECT * FROM articles
            WHERE summary IS NULL OR summary = ''
            ORDER BY id
            """
        ).fetchall()
        return [dict(row) for row in rows]

    def save_summary(
        self,
        article_id: int,
        *,
        clean_text: str,
        summary: str,
        summary_words: int,
        summary_engine: str,
    ) -> None:
        self.conn.execute(
            """
            UPDATE articles SET
                clean_text = ?,
                summary = ?,
                summary_words = ?,
                summary_engine = ?,
                summarized_at = ?
            WHERE id = ?
            """,
            (clean_text, summary, summary_words, summary_engine, iso(), article_id),
        )
        self.conn.commit()

    def cluster_reports(self, cluster_id: str) -> list[dict[str, str]]:
        """One summarized report per outlet for a story group."""
        rows = self.conn.execute(
            """
            SELECT outlet, title, summary
            FROM articles
            WHERE cluster_id = ?
              AND summary IS NOT NULL AND summary != ''
              AND outlet IS NOT NULL AND outlet != ''
            ORDER BY summarized_at DESC, id DESC
            """,
            (cluster_id,),
        ).fetchall()
        reports: list[dict[str, str]] = []
        seen: set[str] = set()
        for row in rows:
            outlet = row["outlet"]
            if outlet in seen:
                continue
            seen.add(outlet)
            reports.append(
                {"outlet": outlet, "title": row["title"], "summary": row["summary"]}
            )
        reports.sort(key=lambda report: report["outlet"])
        return reports

    def get_framing(self, cluster_id: str) -> dict[str, Any] | None:
        row = self.conn.execute(
            "SELECT source_key, notes_json FROM framings WHERE cluster_id = ?",
            (cluster_id,),
        ).fetchone()
        if row is None:
            return None
        return {"source_key": row["source_key"], "notes": json.loads(row["notes_json"])}

    def save_framing(self, cluster_id: str, notes: list[dict[str, str]], source_key: str) -> None:
        self.conn.execute(
            """
            INSERT INTO framings (cluster_id, source_key, notes_json, created_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(cluster_id) DO UPDATE SET
                source_key = excluded.source_key,
                notes_json = excluded.notes_json,
                created_at = excluded.created_at
            """,
            (cluster_id, source_key, json.dumps(notes), iso()),
        )
        self.conn.commit()

    def clusters_needing_framing(self) -> list[str]:
        rows = self.conn.execute(
            """
            SELECT cluster_id
            FROM articles
            WHERE cluster_id IS NOT NULL
              AND summary IS NOT NULL AND summary != ''
              AND outlet IS NOT NULL AND outlet != ''
            GROUP BY cluster_id
            HAVING COUNT(DISTINCT outlet) > 1
            """
        ).fetchall()
        pending: list[str] = []
        for row in rows:
            cluster_id = row["cluster_id"]
            reports = self.cluster_reports(cluster_id)
            saved = self.get_framing(cluster_id)
            saved_key = saved["source_key"] if saved else None
            if needs_refresh(reports, saved_key):
                pending.append(cluster_id)
        return pending

    def save_audio(self, article_id: int, *, audio_path: str | None, audio_status: str) -> None:
        self.conn.execute(
            """
            UPDATE articles SET audio_path = ?, audio_status = ? WHERE id = ?
            """,
            (audio_path, audio_status, article_id),
        )
        self.conn.commit()

    def open_threads(self) -> list[dict[str, str]]:
        rows = self.conn.execute(
            """
            SELECT id, title, open_question
            FROM threads
            WHERE status = 'open'
            ORDER BY updated_at DESC
            """
        ).fetchall()
        return [dict(row) for row in rows]

    def article_was_reviewed(self, article_id: int) -> bool:
        row = self.conn.execute(
            "SELECT 1 FROM thread_reviews WHERE article_id = ?",
            (article_id,),
        ).fetchone()
        return row is not None

    def mark_thread_reviewed(self, article_id: int) -> None:
        self.conn.execute(
            "INSERT OR IGNORE INTO thread_reviews (article_id) VALUES (?)",
            (article_id,),
        )
        self.conn.commit()

    def articles_awaiting_thread(self, limit: int = 12) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            """
            SELECT id, title, summary, cluster_id
            FROM articles
            WHERE summary IS NOT NULL AND summary != ''
              AND id NOT IN (SELECT article_id FROM thread_reviews)
            ORDER BY summarized_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]

    def drop_copied_thread_ids(self) -> int:
        """Remove threads whose title is another thread's id, not a situation."""
        removed = 0
        rows = self.conn.execute("SELECT id, title FROM threads").fetchall()
        for row in rows:
            title = (row["title"] or "").strip().lower()
            if not re.fullmatch(r"[0-9a-f]{6,32}", title):
                continue
            self.conn.execute("DELETE FROM thread_updates WHERE thread_id = ?", (row["id"],))
            self.conn.execute("DELETE FROM threads WHERE id = ?", (row["id"],))
            removed += 1
        if removed:
            self.conn.commit()
        return removed

    def merge_open_threads(self) -> int:
        """Fold open threads that follow the same situation into the oldest one."""
        rows = self.conn.execute(
            """
            SELECT threads.id AS thread_id, threads.opened_at AS opened_at, article.title AS title
            FROM threads
            JOIN thread_updates AS update_row ON update_row.thread_id = threads.id
            JOIN articles AS article ON article.id = update_row.article_id
            WHERE threads.status = 'open'
            """
        ).fetchall()
        titles: dict[str, list[str]] = {}
        opened: dict[str, str] = {}
        for row in rows:
            thread_id = str(row["thread_id"])
            titles.setdefault(thread_id, []).append(row["title"])
            opened[thread_id] = row["opened_at"]
        parent = {thread_id: thread_id for thread_id in titles}

        def find(thread_id: str) -> str:
            while parent[thread_id] != thread_id:
                parent[thread_id] = parent[parent[thread_id]]
                thread_id = parent[thread_id]
            return thread_id

        id_list = list(titles)
        for index, left in enumerate(id_list):
            for right in id_list[index + 1 :]:
                if find(left) == find(right):
                    continue
                if any(same_story(left_title, right_title) for left_title in titles[left] for right_title in titles[right]):
                    parent[find(right)] = find(left)
        groups: dict[str, list[str]] = {}
        for thread_id in id_list:
            groups.setdefault(find(thread_id), []).append(thread_id)
        merged = 0
        for members in groups.values():
            if len(members) < 2:
                continue
            keep = min(members, key=lambda thread_id: opened[thread_id])
            for thread_id in members:
                if thread_id == keep:
                    continue
                updates = self.conn.execute(
                    "SELECT id, article_id FROM thread_updates WHERE thread_id = ?",
                    (thread_id,),
                ).fetchall()
                for update in updates:
                    taken = self.conn.execute(
                        "SELECT 1 FROM thread_updates WHERE article_id = ? AND id != ?",
                        (update["article_id"], update["id"]),
                    ).fetchone()
                    if taken:
                        self.conn.execute("DELETE FROM thread_updates WHERE id = ?", (update["id"],))
                    else:
                        self.conn.execute(
                            "UPDATE thread_updates SET thread_id = ? WHERE id = ?",
                            (keep, update["id"]),
                        )
                self.conn.execute("DELETE FROM threads WHERE id = ?", (thread_id,))
                merged += 1
        if merged:
            self.conn.commit()
        return merged

    def prune_unrelated_updates(self) -> int:
        """Drop stories a model attached to a thread they do not belong to."""
        removed = 0
        threads = self.conn.execute(
            "SELECT id, title FROM threads WHERE status = 'open'"
        ).fetchall()
        for thread in threads:
            updates = self.conn.execute(
                """
                SELECT update_row.id AS id, article.title AS title
                FROM thread_updates AS update_row
                JOIN articles AS article ON article.id = update_row.article_id
                WHERE update_row.thread_id = ?
                """,
                (thread["id"],),
            ).fetchall()
            anchor = thread["title"]
            anchored = [row["title"] for row in updates if same_story(row["title"], anchor)]

            def belongs(title: str) -> bool:
                if same_story(title, anchor):
                    return True
                return any(same_story(title, other) for other in anchored)

            for row in updates:
                if belongs(row["title"]):
                    continue
                self.conn.execute("DELETE FROM thread_updates WHERE id = ?", (row["id"],))
                removed += 1
            left = self.conn.execute(
                "SELECT COUNT(*) AS n FROM thread_updates WHERE thread_id = ?",
                (thread["id"],),
            ).fetchone()
            if left is not None and int(left["n"]) == 0:
                self.conn.execute("DELETE FROM threads WHERE id = ?", (thread["id"],))
        if removed:
            self.conn.commit()
        return removed

    def attach_cluster_mates(self) -> int:
        """Add the other outlets already grouped with a story onto that story's thread."""
        rows = self.conn.execute(
            """
            SELECT update_row.thread_id AS thread_id, article.cluster_id AS cluster_id
            FROM thread_updates AS update_row
            JOIN articles AS article ON article.id = update_row.article_id
            JOIN threads ON threads.id = update_row.thread_id
            WHERE threads.status = 'open'
              AND article.cluster_id IS NOT NULL
              AND article.cluster_id != ''
            """
        ).fetchall()
        chosen: dict[str, str] = {}
        for row in rows:
            chosen.setdefault(str(row["cluster_id"]), str(row["thread_id"]))
        added = 0
        now = iso()
        for cluster_id, thread_id in chosen.items():
            mates = self.conn.execute(
                """
                SELECT id, title
                FROM articles
                WHERE cluster_id = ?
                  AND id NOT IN (SELECT article_id FROM thread_updates)
                """,
                (cluster_id,),
            ).fetchall()
            for mate in mates:
                self.conn.execute(
                    """
                    INSERT OR IGNORE INTO thread_updates (thread_id, article_id, note, created_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (thread_id, mate["id"], mate["title"], now),
                )
                added += 1
        if added:
            self.conn.commit()
        return added

    def thread_for_article(self, title: str, cluster_id: str | None) -> str | None:
        found = self.thread_for_title(title)
        if found or not cluster_id:
            return found
        row = self.conn.execute(
            """
            SELECT update_row.thread_id
            FROM thread_updates AS update_row
            JOIN articles AS article ON article.id = update_row.article_id
            JOIN threads ON threads.id = update_row.thread_id
            WHERE article.cluster_id = ? AND threads.status = 'open'
            LIMIT 1
            """,
            (cluster_id,),
        ).fetchone()
        if row is None:
            return None
        return str(row["thread_id"])

    def thread_for_title(self, title: str) -> str | None:
        """Return an open thread that already follows this same situation."""
        rows = self.conn.execute(
            """
            SELECT threads.id AS thread_id, article.title AS title
            FROM threads
            JOIN thread_updates AS update_row ON update_row.thread_id = threads.id
            JOIN articles AS article ON article.id = update_row.article_id
            WHERE threads.status = 'open'
            """
        ).fetchall()
        for row in rows:
            if same_story(title, row["title"]):
                return str(row["thread_id"])
        return None

    def create_thread(self, *, title: str, open_question: str, article_id: int, note: str) -> str:
        thread_id = uuid.uuid4().hex
        now = iso()
        self.conn.execute(
            """
            INSERT INTO threads (id, title, status, open_question, opened_at, updated_at)
            VALUES (?, ?, 'open', ?, ?, ?)
            """,
            (thread_id, title, open_question, now, now),
        )
        self.conn.execute(
            """
            INSERT INTO thread_updates (thread_id, article_id, note, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (thread_id, article_id, note, now),
        )
        self.conn.commit()
        return thread_id

    def add_thread_update(
        self,
        *,
        thread_id: str,
        article_id: int,
        note: str,
        resolved: bool,
    ) -> None:
        now = iso()
        self.conn.execute(
            """
            INSERT OR IGNORE INTO thread_updates (thread_id, article_id, note, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (thread_id, article_id, note, now),
        )
        if resolved:
            self.conn.execute(
                """
                UPDATE threads
                SET status = 'closed', closed_at = ?, updated_at = ?, open_question = ?
                WHERE id = ?
                """,
                (now, now, note, thread_id),
            )
        else:
            self.conn.execute(
                "UPDATE threads SET updated_at = ? WHERE id = ?",
                (now, thread_id),
            )
        self.conn.commit()

    def thread_id_for_article(self, article_id: int) -> str | None:
        row = self.conn.execute(
            """
            SELECT thread_id FROM thread_updates
            WHERE article_id = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (article_id,),
        ).fetchone()
        return str(row["thread_id"]) if row else None

    def cluster_reports_full(self, cluster_id: str) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            """
            SELECT *
            FROM articles
            WHERE cluster_id = ?
              AND summary IS NOT NULL AND summary != ''
              AND outlet IS NOT NULL AND outlet != ''
            ORDER BY summarized_at DESC, id DESC
            """,
            (cluster_id,),
        ).fetchall()
        reports: list[dict[str, Any]] = []
        seen: set[str] = set()
        for row in rows:
            outlet = row["outlet"]
            if outlet in seen:
                continue
            seen.add(outlet)
            reports.append(dict(row))
        reports.sort(key=lambda report: report["outlet"] or "")
        return reports

    def get_thread_bundle(self, thread_id: str) -> dict[str, Any] | None:
        thread = self.conn.execute(
            "SELECT * FROM threads WHERE id = ?",
            (thread_id,),
        ).fetchone()
        if thread is None:
            return None
        updates = self.conn.execute(
            """
            SELECT
                article.id AS article_id,
                article.title AS title,
                article.summary AS summary,
                article.outlet AS outlet,
                article.category AS category,
                article.place AS place,
                article.audio_path AS audio_path,
                article.audio_status AS audio_status,
                article.image_url AS image_url,
                update_row.note AS note,
                update_row.created_at AS at
            FROM thread_updates AS update_row
            JOIN articles AS article ON article.id = update_row.article_id
            WHERE update_row.thread_id = ?
            ORDER BY update_row.created_at DESC, update_row.id DESC
            """,
            (thread_id,),
        ).fetchall()
        topic = "Canada"
        place = "Canada"
        if updates:
            topic = updates[0]["category"] or topic
            place = updates[0]["place"] or place
        return {
            "threadId": f"thread_{thread_id}",
            "title": thread["title"],
            "status": thread["status"],
            "topic": topic,
            "place": place,
            "openedAt": thread["opened_at"],
            "closedAt": thread["closed_at"],
            "updatedAt": thread["updated_at"],
            "updates": [
                {
                    "storyId": f"story_{row['article_id']}",
                    "at": row["at"],
                    "outlet": row["outlet"] or "",
                    "summary": row["summary"] or row["note"] or "",
                    "title": row["title"],
                    "audioStatus": "ready" if row["audio_path"] else (row["audio_status"] or "pending"),
                    "audioKey": None,
                    "imageUrl": row["image_url"],
                }
                for row in updates
            ],
        }

    def add_event(self, stage: str, message: str) -> None:
        text = message.replace("\n", " ").strip()
        print(f"[{stage}] {text}", flush=True)
        self.conn.execute(
            "INSERT INTO events (ts, stage, message) VALUES (?, ?, ?)",
            (iso(), stage, text[:500]),
        )
        self.conn.execute(
            """
            DELETE FROM events
            WHERE id < (
                SELECT id FROM events ORDER BY id DESC LIMIT 1 OFFSET 200
            )
            """
        )
        self.conn.commit()

    def set_runtime(self, key: str, value: str) -> None:
        self.conn.execute(
            """
            INSERT INTO runtime (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (key, value),
        )
        self.conn.commit()
