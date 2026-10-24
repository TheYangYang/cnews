"""Normalize article text and summarize it with Ollama (Llama 3.1 8B).

Priority on a single GPU: a brief for every new article comes first, then speech
(the TTS worker takes a GPU turn when briefs go quiet), then enrichment
(storyline decisions and multi-outlet framing). Enrichment is never dropped: it
waits for an idle GPU, and runs at least every ENRICH_MAX_LAG_SECONDS under load.
"""

from __future__ import annotations

import asyncio
import time

import httpx

from realtime_ingestion import config, llm
from realtime_ingestion.broker import RedisBroker
from realtime_ingestion.database import Database
from realtime_ingestion.framing import needs_refresh, source_key, write_notes
from realtime_ingestion.normalize import prepare_speech_text, tidy_summary, word_count
from realtime_ingestion.publish.publisher import AsyncPublisher
from realtime_ingestion.threads import decide
from realtime_ingestion.tts.gpu_gate import GATE

_SYSTEM = (
    "You write a plain news brief of about 50 words for a reader. "
    "Use plain sentences only. Do not use markdown, bullets, or a label. "
    "Do not add facts that are not in the article. "
    "Do not greet the reader, and do not pretend you are reporting from the scene."
)


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
    content = await llm.chat(
        client,
        system=_SYSTEM,
        user=f"Headline: {title}\n\nArticle:\n{clipped}",
        temperature=0.2,
        num_predict=160,
    )
    return tidy_summary(content)


class AiWorker:
    def __init__(
        self,
        db: Database,
        broker: RedisBroker,
        client: httpx.AsyncClient,
        publisher: AsyncPublisher,
    ) -> None:
        self.db = db
        self.broker = broker
        self.client = client
        self.publisher = publisher
        # Clusters whose coverage changed since the last framing pass (debounced).
        self.dirty_clusters: dict[str, None] = {}
        self.last_enrich = time.monotonic()

    # ----- briefs (top priority) --------------------------------------------------

    async def handle_article(self, fields: dict[str, str]) -> None:
        db = self.db
        article_pk = int(fields["article_pk"])
        article = db.get_article(article_pk)
        if article is None:
            return
        if article.get("summary"):
            # Redelivered after a crash: make sure speech and the text doc exist.
            await self.broker.publish(config.STREAM_SUMMARIES, {"article_pk": str(article_pk)})
            try:
                await self.publisher.story_text(article)
            except Exception as exc:
                db.add_event("publish", f"re-publish failed: {exc}")
            return

        raw_text = fields.get("raw_text") or article.get("raw_text") or ""
        title = fields.get("title") or article["title"]
        clean = prepare_speech_text(raw_text)
        engine = config.OLLAMA_MODEL
        try:
            async with GATE.llm():
                summary = await _summarize(self.client, title, clean)
            if word_count(summary) < 12:
                raise ValueError("summary was too short")
        except Exception as exc:
            summary = _extractive_brief(clean)
            engine = "extractive fallback"
            db.add_event("ai", f"Ollama failed for '{title}': {exc}")

        db.save_summary(
            article_pk,
            summary=summary,
            summary_words=word_count(summary),
            summary_engine=engine,
        )
        article = db.get_article(article_pk) or article
        db.add_event("ai", f"brief_ready {word_count(summary)} words via {engine}: {title}")
        # Speech is queued before anything else so Kokoro follows the brief directly.
        await self.broker.publish(config.STREAM_SUMMARIES, {"article_pk": str(article_pk)})
        if not config.PUBLISH_REQUIRE_AUDIO:
            try:
                await self.publisher.story_text(article, audio_status="pending")
            except Exception as exc:
                db.add_event("publish", f"text publish failed: {exc}")
        cluster_id = article.get("cluster_id")
        if cluster_id:
            self.dirty_clusters[cluster_id] = None

    # ----- enrichment (when the GPU is free) --------------------------------------

    async def enrich_once(self) -> bool:
        """Run one framing refresh or one storyline review. Returns True if work ran."""
        self.last_enrich = time.monotonic()
        while self.dirty_clusters:
            cluster_id = next(iter(self.dirty_clusters))
            del self.dirty_clusters[cluster_id]
            if await self._refresh_framing(cluster_id):
                return True
        waiting = self.db.articles_awaiting_thread(
            1, window_hours=config.THREAD_REVIEW_WINDOW_HOURS
        )
        if waiting:
            await self._consider_thread(waiting[0])
            return True
        return False

    async def _refresh_framing(self, cluster_id: str) -> bool:
        db = self.db
        reports = db.cluster_reports(cluster_id)
        saved = db.get_framing(cluster_id)
        saved_key = saved["source_key"] if saved else None
        if not needs_refresh(reports, saved_key):
            await self.publisher.coverage(cluster_id)
            return False
        try:
            async with GATE.llm():
                notes = await write_notes(self.client, reports)
        except Exception as exc:
            db.add_event("framing", f"Ollama failed: {exc}")
            return True
        if not notes:
            db.add_event("framing", "the model reply did not include one line per outlet")
            return True
        db.save_framing(cluster_id, notes, source_key(reports))
        preview = " ".join(f"{note['outlet']}: {note['note']}" for note in notes)
        db.add_event("framing", preview)
        await self.publisher.coverage(cluster_id)
        return True

    async def _consider_thread(self, article: dict) -> None:
        db = self.db
        article_id = int(article["id"])
        summary = article.get("summary") or ""
        if not summary or db.article_was_reviewed(article_id):
            return
        open_threads = db.open_threads(config.THREAD_PROMPT_MAX_OPEN)
        try:
            async with GATE.llm():
                decision = await decide(
                    self.client,
                    title=article["title"],
                    summary=summary,
                    open_threads=open_threads,
                )
        except Exception as exc:
            db.add_event("thread", f"Ollama failed: {exc}")
            return
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
            await self.publisher.thread(thread_id)

    # ----- loop -------------------------------------------------------------------

    async def _process(self, message_id: str, fields: dict[str, str]) -> None:
        try:
            async with GATE.busy():
                await self.handle_article(fields)
        except Exception as exc:
            self.db.add_event("ai", f"worker error: {exc}")
        await self.broker.ack(config.STREAM_ARTICLES, config.GROUP_AI, message_id)

    async def run(self, stop: asyncio.Event) -> None:
        db = self.db
        try:
            names = await llm.installed_models(self.client)
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
            self.dirty_clusters[cluster_id] = None

        # Jobs that were in hand when the last run stopped.
        for message_id, fields in await self.broker.read_pending(
            config.STREAM_ARTICLES, config.GROUP_AI, "ai-1"
        ):
            await self._process(message_id, fields)

        while not stop.is_set():
            messages = await self.broker.read(
                config.STREAM_ARTICLES,
                config.GROUP_AI,
                "ai-1",
                count=1,
                block_ms=1000,
            )
            if messages:
                for message_id, fields in messages:
                    await self._process(message_id, fields)
                # Starvation guard: keep storylines moving during a long burst.
                if time.monotonic() - self.last_enrich >= config.ENRICH_MAX_LAG_SECONDS:
                    await self._enrich_guarded()
                continue
            # No new articles. Let speech take the GPU first; enrich when it is done.
            if GATE.speech_waiting or GATE.in_turn:
                continue
            await self._enrich_guarded()

    async def _enrich_guarded(self) -> None:
        try:
            await self.enrich_once()
        except Exception as exc:
            self.db.add_event("ai", f"enrichment error: {exc}")


async def run_ai_worker(
    db: Database,
    broker: RedisBroker,
    stop: asyncio.Event,
    publisher: AsyncPublisher,
) -> None:
    timeout = httpx.Timeout(config.OLLAMA_TIMEOUT_SECONDS, connect=5.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        await AiWorker(db, broker, client, publisher).run(stop)
