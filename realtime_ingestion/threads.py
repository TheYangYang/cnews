"""Follow an unfinished situation until a later story closes it."""

from __future__ import annotations

import re
from typing import Any

import httpx

from realtime_ingestion import config

Decision = dict[str, Any]
_PLACEHOLDERS = {"short title", "what is still unknown", "what is newly known", "unknown", "still unknown"}
_ID = re.compile(r"^[0-9a-f]{6,32}$", re.IGNORECASE)


def parse_decision(text: str, open_threads: list[dict[str, str]]) -> Decision | None:
    """Read one reply line: IGNORE, OPEN, or UPDATE."""
    cleaned = re.sub(r"(?is)<think>.*?</think>", " ", text or "")
    line = ""
    for raw in cleaned.splitlines():
        candidate = raw.strip().lstrip("-*0123456789.) ").strip()
        if candidate:
            line = candidate
            break
    if not line:
        return None
    parts = [part.strip() for part in line.split("|")]
    action = parts[0].upper()
    if action == "IGNORE":
        return {"action": "ignore"}
    if action == "OPEN" and len(parts) >= 3 and parts[1] and parts[2]:
        title = _clip(parts[1], 12)
        note = _clip(parts[2], 40)
        if _ID.match(title) or _placeholder(title) or _placeholder(note):
            return {"action": "ignore"}
        return {"action": "open", "title": title, "note": note}
    if action == "UPDATE" and len(parts) >= 4:
        thread = _match_thread(parts[1], open_threads)
        if thread is None or not parts[2]:
            return None
        return {
            "action": "update",
            "thread_id": thread["id"],
            "note": _clip(parts[2], 40),
            "resolved": parts[3].upper().startswith("CLOSED"),
        }
    return None


def _placeholder(text: str) -> bool:
    lowered = re.sub(r"\s+", " ", text.lower()).strip(" .:")
    lowered = re.sub(r"^(still unknown|unknown)\s*:\s*", "", lowered)
    return lowered in _PLACEHOLDERS


def _clip(text: str, max_words: int) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip().strip("\"'")
    words = cleaned.split()
    if len(words) > max_words:
        cleaned = " ".join(words[:max_words]).rstrip(",;: ")
    return cleaned


def _match_thread(token: str, open_threads: list[dict[str, str]]) -> dict[str, str] | None:
    key = token.strip().lower()
    if len(key) < 6:
        return None
    for thread in open_threads:
        if thread["id"] == key or thread["id"].startswith(key):
            return thread
    return None


def _prompt(title: str, summary: str, open_threads: list[dict[str, str]]) -> str:
    if open_threads:
        listed = "\n".join(
            f"{thread['id'][:8]} | {thread['title']} | still unknown: {thread['open_question']}"
            for thread in open_threads
        )
    else:
        listed = "(none)"
    return (
        "You watch news for situations a reader would check again later.\n"
        "Open a thread only when the outcome is still unknown.\n"
        "If this brief is the same situation as an open thread, update that thread.\n"
        "Do not open a second thread for a situation that is already listed.\n"
        "Close it when the outcome is now known.\n"
        "Ignore a finished event, a final score, a comment, or a feature.\n\n"
        f"Open threads:\n{listed}\n\n"
        f"Headline: {title}\n"
        f"Brief: {summary}\n\n"
        "Reply with exactly one line and no other text.\n"
        "A thread id belongs only on an UPDATE line. Never use an id as a title.\n"
        "IGNORE\n"
        "OPEN | short title in words | the specific fact that is still unknown\n"
        "UPDATE | thread id | what is newly known | OPEN\n"
        "UPDATE | thread id | what is newly known | CLOSED"
    )


async def decide(
    client: httpx.AsyncClient,
    *,
    title: str,
    summary: str,
    open_threads: list[dict[str, str]],
) -> Decision | None:
    response = await client.post(
        f"{config.OLLAMA_URL}/api/chat",
        json={
            "model": config.OLLAMA_MODEL,
            "stream": False,
            "keep_alive": "10m",
            "messages": [
                {
                    "role": "system",
                    "content": "You decide whether a news brief starts, continues, or ends an unfinished situation. Use plain text.",
                },
                {"role": "user", "content": _prompt(title, summary, open_threads)},
            ],
            "options": {"temperature": 0.1, "num_predict": 80},
        },
    )
    response.raise_for_status()
    content = response.json()["message"]["content"]
    return parse_decision(content, open_threads)
