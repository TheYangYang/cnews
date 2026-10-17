"""One sentence per outlet on what that outlet chose to emphasize."""

from __future__ import annotations

import hashlib
import re

import httpx

from realtime_ingestion import config

Report = dict[str, str]
Note = dict[str, str]


def source_key(reports: list[Report]) -> str:
    """Changes when an outlet's brief changes, so the note can be rewritten."""
    lines = [f"{report['outlet']}\n{report['summary']}" for report in reports]
    payload = "\n".join(lines)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def needs_refresh(reports: list[Report], saved_key: str | None) -> bool:
    if len(reports) < 2:
        return False
    return saved_key != source_key(reports)


def _sentence(text: str, *, max_words: int = 40) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip().strip("\"'")
    words = cleaned.split()
    if len(words) > max_words:
        cleaned = " ".join(words[:max_words]).rstrip(",;: ") + "."
    return cleaned


def parse_notes(text: str, outlets: list[str]) -> list[Note] | None:
    """Read 'CBC: ...' lines. Returns one note per outlet, or None if a line is missing."""
    cleaned = re.sub(r"(?is)<think>.*?</think>", " ", text or "")
    found: dict[str, str] = {}
    for raw_line in cleaned.splitlines():
        line = raw_line.strip().lstrip("-*0123456789.) ").strip()
        line = line.replace("**", "")
        if ":" in line:
            label, rest = line.split(":", 1)
        elif " - " in line:
            label, rest = line.split(" - ", 1)
        else:
            continue
        label = label.strip().strip("*")
        outlet = next((name for name in outlets if name.lower() == label.lower()), None)
        if outlet is None or outlet in found:
            continue
        sentence = _sentence(rest)
        if sentence:
            found[outlet] = sentence
    if set(found) != set(outlets):
        return None
    return [{"outlet": outlet, "note": found[outlet]} for outlet in outlets]


def _prompt(reports: list[Report]) -> str:
    blocks = []
    for report in reports:
        blocks.append(
            f"Outlet: {report['outlet']}\n"
            f"Headline: {report['title']}\n"
            f"Brief: {report['summary']}"
        )
    names = "\n".join(f"{report['outlet']}:" for report in reports)
    return (
        "Compare how these outlets framed the same event. "
        "For each outlet, write one plain sentence about what that outlet chose to lead with. "
        "When the briefs differ, mention a detail that outlet included. "
        "Use only the briefs. Do not add facts, and do not rank the outlets.\n\n"
        + "\n\n".join(blocks)
        + "\n\nReply with one line per outlet, and no other text:\n"
        + names
    )


async def write_notes(client: httpx.AsyncClient, reports: list[Report]) -> list[Note] | None:
    outlets = [report["outlet"] for report in reports]
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
                        "You describe differences in news framing. "
                        "Use plain sentences. Do not use markdown."
                    ),
                },
                {"role": "user", "content": _prompt(reports)},
            ],
            "options": {"temperature": 0.2, "num_predict": 220},
        },
    )
    response.raise_for_status()
    content = response.json()["message"]["content"]
    return parse_notes(content, outlets)
