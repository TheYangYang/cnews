"""Async RSS poller with HTTP caching headers and a Redis publisher."""

from __future__ import annotations

import asyncio
import hashlib
from email.utils import parsedate_to_datetime

import feedparser
import httpx

from news_pipeline import config
from news_pipeline.broker import RedisBroker
from news_pipeline.database import Database
from news_pipeline.normalize import (
    canonical_url,
    digest,
    extract_image,
    extract_story,
    html_to_text,
    title_hash,
)

FEED_HEADERS = {
    "User-Agent": config.USER_AGENT,
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
}
HTML_HEADERS = {
    "User-Agent": config.USER_AGENT,
    "Accept": "text/html,application/xhtml+xml",
}


def _published(entry: feedparser.FeedParserDict) -> str | None:
    raw = entry.get("published") or entry.get("updated")
    if not raw:
        return None
    try:
        moment = parsedate_to_datetime(raw)
    except (TypeError, ValueError, IndexError):
        return str(raw)
    if moment.tzinfo is None:
        return moment.isoformat()
    return moment.isoformat()


def _rss_text(entry: feedparser.FeedParserDict) -> str:
    parts = [entry.get("summary") or "", entry.get("description") or ""]
    for block in entry.get("content") or []:
        if isinstance(block, dict):
            parts.append(block.get("value") or "")
    texts = [html_to_text(part) for part in parts]
    return max(texts, key=len, default="")


def _image(entry: feedparser.FeedParserDict, description: str) -> str | None:
    image = extract_image(description)
    if image:
        return image
    for key in ("media_content", "media_thumbnail"):
        for item in entry.get(key) or []:
            url = item.get("url") if isinstance(item, dict) else None
            if url and str(url).startswith("https://"):
                return str(url)
    return None


async def _load_article_text(client: httpx.AsyncClient, url: str) -> str:
    try:
        response = await client.get(url, headers=HTML_HEADERS)
        response.raise_for_status()
    except httpx.HTTPError:
        return ""
    return extract_story(response.text)


async def _republish_pending(db: Database, broker: RedisBroker) -> None:
    pending = db.pending_articles()
    if not pending:
        return
    for article in pending:
        await broker.publish(
            config.STREAM_ARTICLES,
            {
                "article_pk": str(article["id"]),
                "feed_id": str(article["feed_id"]),
                "article_id": article["article_id"] or "",
                "url": article["url"],
                "title": article["title"],
                "raw_text": article["raw_text"] or "",
            },
        )
    db.add_event("poller", f"requeued {len(pending)} stories still waiting on a summary")


async def poll_feed(
    feed: dict,
    client: httpx.AsyncClient,
    db: Database,
    broker: RedisBroker,
) -> None:
    headers = dict(FEED_HEADERS)
    if feed.get("etag"):
        headers["If-None-Match"] = feed["etag"]
    if feed.get("last_modified"):
        headers["If-Modified-Since"] = feed["last_modified"]

    response = await client.get(feed["url"], headers=headers)
    etag = response.headers.get("etag") or feed.get("etag")
    last_modified = response.headers.get("last-modified") or feed.get("last_modified")

    if response.status_code == 304:
        db.mark_fetch(
            feed["id"],
            status=304,
            etag=etag,
            last_modified=last_modified,
            body_hash=feed.get("body_hash"),
            note="304 Not Modified",
            new_count=0,
            duplicate_count=0,
        )
        return

    response.raise_for_status()
    body_hash = hashlib.sha256(response.content).hexdigest()
    if feed.get("body_hash") and feed["body_hash"] == body_hash:
        db.mark_fetch(
            feed["id"],
            status=response.status_code,
            etag=etag,
            last_modified=last_modified,
            body_hash=body_hash,
            note="feed body unchanged",
            new_count=0,
            duplicate_count=0,
        )
        return

    parsed = feedparser.parse(response.content)
    entries = list(parsed.entries)
    unseen = []
    duplicates = 0
    linked = 0
    for entry in entries:
        link = (entry.get("link") or "").strip()
        title = html_to_text(entry.get("title") or "")
        if not link or not title:
            continue
        url = canonical_url(link)
        hashed = title_hash(title)
        if db.feed_carries(feed["id"], url, hashed):
            duplicates += 1
            continue
        if db.attach_feed(url, feed["id"]):
            linked += 1
            continue
        unseen.append((entry, url, title))

    selected = unseen[: config.MAX_NEW_ARTICLES_PER_POLL]
    waiting = len(unseen) - len(selected)
    semaphore = asyncio.Semaphore(config.ARTICLE_FETCH_CONCURRENCY)

    async def enrich(item: tuple) -> dict | None:
        entry, url, title = item
        link = entry.get("link") or url
        description = entry.get("summary") or entry.get("description") or ""
        rss_text = _rss_text(entry)
        story = ""
        if len(rss_text) < 500:
            async with semaphore:
                story = await _load_article_text(client, link)
        raw_text = story if len(story) >= len(rss_text) else rss_text
        if not raw_text:
            raw_text = title
        article_key = str(entry.get("id") or url)
        # Seen-keys are per feed so a second outlet can still publish its own report.
        claimed = await broker.mark_seen(
            digest(f"{feed['id']}|{url}"),
            digest(f"{feed['id']}|{title}"),
            config.SEEN_TTL_SECONDS,
        )
        if not claimed:
            return None
        return {
            "article_id": article_key,
            "url": url,
            "title": title,
            "raw_text": raw_text,
            "image_url": _image(entry, description),
            "published_at": _published(entry),
            "title_hash": title_hash(title),
        }

    enriched = await asyncio.gather(*(enrich(item) for item in selected))
    payloads = [item for item in enriched if item]
    duplicates += sum(1 for item in enriched if item is None)
    published = 0
    for payload in payloads:
        article_pk, joined = db.insert_article(
            feed_id=feed["id"],
            article_id=payload["article_id"],
            url=payload["url"],
            title=payload["title"],
            title_hash=payload["title_hash"],
            image_url=payload["image_url"],
            category=feed.get("category") or "Canada",
            place=feed.get("place") or "Canada",
            outlet=feed.get("outlet") or feed["name"],
            raw_text=payload["raw_text"],
            published_at=payload["published_at"],
        )
        if article_pk is None:
            duplicates += 1
            continue
        await broker.publish(
            config.STREAM_ARTICLES,
            {
                "article_pk": str(article_pk),
                "feed_id": str(feed["id"]),
                "article_id": payload["article_id"],
                "url": payload["url"],
                "title": payload["title"],
                "raw_text": payload["raw_text"],
            },
        )
        published += 1
        if joined:
            db.add_event("compare", f"{feed.get('outlet') or feed['name']} grouped: {payload['title']}")
        else:
            db.add_event("dedup", f"new story: {payload['title']}")

    note = f"{published} new, {linked} already stored, {duplicates} already seen"
    if waiting:
        note += f", {waiting} left for the next poll"
    if not etag and not response.headers.get("last-modified"):
        note += "; server sent no ETag or Last-Modified"
    saved_hash = body_hash if waiting == 0 else None
    db.mark_fetch(
        feed["id"],
        status=response.status_code,
        etag=etag,
        last_modified=last_modified,
        body_hash=saved_hash,
        note=note,
        new_count=published,
        duplicate_count=duplicates + linked,
    )
    if published or linked:
        db.add_event("poller", f"{feed['name']}: {note}")


async def run_poller(db: Database, broker: RedisBroker, stop: asyncio.Event) -> None:
    await _republish_pending(db, broker)
    timeout = httpx.Timeout(25.0, connect=10.0)
    async with httpx.AsyncClient(
        timeout=timeout,
        follow_redirects=True,
        headers=FEED_HEADERS,
    ) as client:
        while not stop.is_set():
            for feed in db.due_feeds():
                try:
                    await poll_feed(feed, client, db, broker)
                except Exception as exc:
                    db.mark_fetch(
                        feed["id"],
                        status=None,
                        etag=feed.get("etag"),
                        last_modified=feed.get("last_modified"),
                        body_hash=None,
                        note=f"fetch failed: {exc}",
                        new_count=0,
                        duplicate_count=0,
                    )
                    db.add_event("poller", f"fetch failed: {exc}")
            try:
                await asyncio.wait_for(stop.wait(), timeout=2)
            except TimeoutError:
                continue
