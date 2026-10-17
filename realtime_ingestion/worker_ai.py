"""Normalize article text and summarize it with Ollama (Llama 3.1 8B)."""

from __future__ import annotations

import asyncio

import httpx

from realtime_ingestion import config
from realtime_ingestion.broker import RedisBroker
from realtime_ingestion.database import Database
from realtime_ingestion.framing import needs_refresh, source_key, write_notes
from realtime_ingestion.normalize import prepare_speech_text, tidy_summary, word_count
from realtime_ingestion.publish.publisher import Publisher
from realtime_ingestion.threads import decide
from realtime_ingestion.tts.gpu_gate import GATE


def _extractive_brief(text: str, words: int = config.SUMMARY_WORDS) -> str:
    pieces = text.split()
    if not pieces:
        return ""
    brief = " ".join(pieces[:words]).rstrip(",;: ")
    if brief and brief[-1] not in ".!?":
        brief += "."
    return brief


async def _summarize(client: httpx.AsyncClient, title: str, text: str) -> str:
    clipped = text[: config.PROMPT_CHAR_LIMIT]
    response = await client.post(
        f"{config.OLLAMA_URL}/api/chat",
        json={
            "model": config.OLLAMA_MODEL,
            "stream": False,
            "keep_alive": "10m",
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You write a plain news brief of about 50 words for a reader. "
                        "Use plain sentences only. Do not use markdown, bullets, or a label. "
                        "Do not add facts that are not in the article. "
                        "Do not greet the reader, and do not pretend you are reporting from the scene."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Headline: {title}\n\nArticle:\n{clipped}",
                },
            ],
            "options": {"temperature": 0.2, "num_predict": 160},
        },
    )
    response.raise_for_status()
    content = response.json()["message"]["content"]
    return tidy_summary(content)


async def _handle(
    db: Database,
    broker: RedisBroker,
    client: httpx.AsyncClient,
    fields: dict[str, str],
    publisher: Publisher,
) -> None:
    article_pk = int(fields["article_pk"])
    article = db.get_article(article_pk)
    if article is None:
        return
    if article.get("summary"):
        await broker.publish(config.STREAM_SUMMARIES, {"article_pk": str(article_pk)})
        try:
            publisher.publish_story_text(article, audio_status="pending" if not article.get("audio_path") else "ready")
        except Exception as exc:
            db.add_event("publish", f"re-publish failed: {exc}")
        return

    raw_text = fields.get("raw_text") or article.get("raw_text") or ""
    title = fields.get("title") or article["title"]
    clean = prepare_speech_text(raw_text)
    engine = config.OLLAMA_MODEL
    GATE.begin_ollama()
    try:
        summary = await _summarize(client, title, clean)
        if word_count(summary) < 12:
            raise ValueError("summary was too short")
    except Exception as exc:
        summary = _extractive_brief(clean)
        engine = "extractive fallback"
        db.add_event("ai", f"Ollama failed for '{title}': {exc}")
    finally:
        GATE.end_ollama()

    db.save_summary(
        article_pk,
        clean_text=clean,
        summary=summary,
        summary_words=word_count(summary),
        summary_engine=engine,
    )
    article = db.get_article(article_pk) or article
    db.add_event("ai", f"brief_ready {word_count(summary)} words via {engine}: {title}")
    if not config.PUBLISH_REQUIRE_AUDIO:
        try:
            publisher.publish_story_text(article, audio_status="pending")
        except Exception as exc:
            db.add_event("publish", f"text publish failed: {exc}")
    await broker.publish(config.STREAM_SUMMARIES, {"article_pk": str(article_pk)})
    cluster_id = article.get("cluster_id")
    if cluster_id:
        await _refresh_framing(db, client, cluster_id, publisher)
    await _consider_thread(db, client, article, publisher)


async def _refresh_framing(
    db: Database,
    client: httpx.AsyncClient,
    cluster_id: str,
    publisher: Publisher,
) -> None:
    reports = db.cluster_reports(cluster_id)
    saved = db.get_framing(cluster_id)
    saved_key = saved["source_key"] if saved else None
    if not needs_refresh(reports, saved_key):
        publisher.publish_coverage(cluster_id)
        return
    GATE.begin_ollama()
    try:
        notes = await write_notes(client, reports)
    except Exception as exc:
        db.add_event("framing", f"Ollama failed: {exc}")
        return
    finally:
        GATE.end_ollama()
    if not notes:
        db.add_event("framing", "the model reply did not include one line per outlet")
        return
    db.save_framing(cluster_id, notes, source_key(reports))
    preview = " ".join(f"{note['outlet']}: {note['note']}" for note in notes)
    db.add_event("framing", preview)
    publisher.publish_coverage(cluster_id)


async def _consider_thread(
    db: Database,
    client: httpx.AsyncClient,
    article: dict,
    publisher: Publisher,
) -> None:
    article_id = int(article["id"])
    summary = article.get("summary") or ""
    if not summary or db.article_was_reviewed(article_id):
        return
    open_threads = db.open_threads()
    GATE.begin_ollama()
    try:
        decision = await decide(
            client,
            title=article["title"],
            summary=summary,
            open_threads=open_threads,
        )
    except Exception as exc:
        db.add_event("thread", f"Ollama failed: {exc}")
        return
    finally:
        GATE.end_ollama()
    db.mark_thread_reviewed(article_id)
    thread_id: str | None = None
    if not decision or decision["action"] == "ignore":
        return
    if decision["action"] == "open":
        existing = db.thread_for_article(article["title"], article.get("cluster_id"))
        if existing:
            db.add_thread_update(
                thread_id=existing,
                article_id=article_id,
                note=decision["note"],
                resolved=False,
            )
            db.attach_cluster_mates()
            db.add_event("thread", f"updated: {decision['note']}")
            thread_id = existing
        else:
            thread_id = db.create_thread(
                title=decision["title"],
                open_question=decision["note"],
                article_id=article_id,
                note=decision["note"],
            )
            db.attach_cluster_mates()
            db.add_event("thread", f"opened: {decision['title']}")
    else:
        thread_id = decision["thread_id"]
        db.add_thread_update(
            thread_id=thread_id,
            article_id=article_id,
            note=decision["note"],
            resolved=bool(decision["resolved"]),
        )
        db.attach_cluster_mates()
        state = "closed" if decision["resolved"] else "updated"
        db.add_event("thread", f"{state}: {decision['note']}")
    if thread_id:
        publisher.publish_thread(thread_id)


async def _catch_up_threads(
    db: Database,
    client: httpx.AsyncClient,
    publisher: Publisher,
    limit: int = 12,
) -> None:
    for article in db.articles_awaiting_thread(limit):
        await _consider_thread(db, client, article, publisher)


async def run_ai_worker(
    db: Database,
    broker: RedisBroker,
    stop: asyncio.Event,
    publisher: Publisher,
) -> None:
    timeout = httpx.Timeout(180.0, connect=5.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            tags = await client.get(f"{config.OLLAMA_URL}/api/tags")
            tags.raise_for_status()
            names = [item["name"] for item in tags.json().get("models", [])]
            if config.OLLAMA_MODEL not in names:
                db.add_event(
                    "ai",
                    f"model {config.OLLAMA_MODEL} is not pulled; installed: {', '.join(names) or 'none'}",
                )
            else:
                db.add_event("ai", f"Ollama ready with {config.OLLAMA_MODEL}")
        except Exception as exc:
            db.add_event("ai", f"Ollama is not reachable: {exc}")

        for cluster_id in db.clusters_needing_framing():
            await _refresh_framing(db, client, cluster_id, publisher)
        await _catch_up_threads(db, client, publisher)

        while not stop.is_set():
            messages = await broker.read(
                config.STREAM_ARTICLES,
                config.GROUP_AI,
                "ai-1",
                count=1,
                block_ms=2000,
            )
            if not messages:
                waiting = db.articles_awaiting_thread(1)
                if waiting:
                    await _consider_thread(db, client, waiting[0], publisher)
                continue
            for message_id, fields in messages:
                try:
                    await _handle(db, broker, client, fields, publisher)
                except Exception as exc:
                    db.add_event("ai", f"worker error: {exc}")
                await broker.ack(config.STREAM_ARTICLES, config.GROUP_AI, message_id)
