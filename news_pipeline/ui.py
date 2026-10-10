"""Local page for reading briefs, filtering categories, and comparing outlets."""

from __future__ import annotations

import json
import sqlite3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

from news_pipeline.config import OLLAMA_MODEL, PLACE_ORDER, TOPIC_ORDER

PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>News across Canada</title>
<style>
  :root {
    color-scheme: dark;
    --bg: #12110f;
    --paper: #1c1a17;
    --ink: #f4f0e6;
    --muted: #b7ab9a;
    --line: #3a342c;
    --red: #e23b2f;
    --good: #d7e2c8;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    background: var(--bg);
    color: var(--ink);
    font-family: "Segoe UI", sans-serif;
  }
  header, main { width: min(1100px, calc(100% - 32px)); margin: 0 auto; }
  header { padding: 28px 0 8px; }
  .kicker {
    color: var(--red);
    letter-spacing: 0.14em;
    font-size: 12px;
    font-weight: 700;
  }
  h1 {
    font-family: Georgia, "Times New Roman", serif;
    font-weight: 500;
    font-size: 42px;
    margin: 6px 0 8px;
  }
  .sub { color: var(--ink); margin: 0; line-height: 1.45; }
  .tech { color: var(--muted); margin: 6px 0 18px; font-size: 13px; line-height: 1.4; }
  .filter-label {
    color: var(--muted);
    font-size: 12px;
    letter-spacing: 0.08em;
    margin: 0 0 8px;
  }
  .filters { display: flex; flex-wrap: wrap; gap: 8px; margin: 0 0 14px; padding: 0; }
  .filters button {
    background: transparent;
    color: var(--muted);
    border: 1px solid var(--line);
    border-radius: 999px;
    padding: 6px 10px;
    font: inherit;
    font-size: 13px;
    cursor: pointer;
  }
  .filters button.on { color: var(--ink); border-color: var(--red); }
  .steps { display: flex; flex-wrap: wrap; gap: 8px; margin: 0 0 18px; padding: 0; list-style: none; }
  .steps li {
    border: 1px solid var(--line);
    border-radius: 999px;
    padding: 6px 10px;
    color: var(--muted);
    font-size: 13px;
  }
  .steps li.on { color: var(--ink); border-color: var(--red); }
  .stats { display: flex; flex-wrap: wrap; gap: 18px; color: var(--muted); font-size: 14px; }
  .stats strong { color: var(--ink); font-weight: 600; }
  article.card {
    display: grid;
    grid-template-columns: 220px 1fr;
    gap: 18px;
    background: var(--paper);
    border-top: 3px solid var(--red);
    padding: 16px;
    margin: 16px 0;
  }
  article.card.no-photo { grid-template-columns: 1fr; }
  article.card img { width: 100%; height: 148px; object-fit: cover; background: #2a261f; }
  .badge {
    color: var(--red);
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    margin-bottom: 6px;
  }
  .meta { color: var(--muted); font-size: 13px; margin-bottom: 6px; }
  h2 { font-family: Georgia, "Times New Roman", serif; font-size: 26px; font-weight: 500; margin: 0 0 10px; }
  h2 a, h3 a { color: inherit; text-decoration: none; }
  h2 a:hover, h3 a:hover { text-decoration: underline; }
  .summary { font-size: 18px; line-height: 1.45; margin: 0 0 10px; }
  .excerpt { color: var(--muted); font-size: 14px; line-height: 1.5; margin: 0; }
  .status { color: var(--good); font-size: 13px; margin-top: 10px; }
  audio { width: min(420px, 100%); margin-top: 10px; }
  .framing {
    margin: 0 0 12px;
    padding: 10px 12px;
    background: #241f1a;
    border-left: 3px solid var(--red);
  }
  .framing-label {
    color: var(--muted);
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin-bottom: 6px;
  }
  .framing p { margin: 0 0 6px; font-size: 15px; line-height: 1.4; }
  .framing p:last-child { margin: 0; }
  .framing strong { color: var(--red); }
  .versions { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
  .version { border-top: 1px solid var(--line); padding-top: 10px; }
  .outlet {
    color: var(--red);
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin-bottom: 4px;
  }
  .version h3 {
    font-family: Georgia, "Times New Roman", serif;
    font-size: 20px;
    font-weight: 500;
    margin: 0 0 8px;
  }
  #log { margin: 8px 0 40px; }
  #log h3 { font-size: 14px; letter-spacing: 0.08em; color: var(--muted); font-weight: 600; }
  #log ul { list-style: none; padding: 0; margin: 0; }
  #log li { font-family: Consolas, monospace; font-size: 12px; color: var(--muted); padding: 4px 0; border-bottom: 1px solid var(--line); }
  .empty { color: var(--muted); padding: 24px 0 48px; }
  .thread { background: var(--paper); border-top: 3px solid var(--red); padding: 16px; margin: 16px 0; }
  .thread h2 { font-size: 28px; }
  .timeline { list-style: none; margin: 12px 0 0; padding: 0; }
  .timeline li { border-top: 1px solid var(--line); padding: 10px 0; }
  .timeline a { color: inherit; }
  @media (max-width: 720px) {
    article.card, .versions { grid-template-columns: 1fr; }
    h1 { font-size: 32px; }
    article.card img { height: 180px; }
  }
  @media (max-width: 420px) {
    header, main { width: min(1100px, calc(100% - 20px)); }
    h1 { font-size: 28px; }
    h2 { font-size: 22px; }
  }
</style>
</head>
<body>
<header>
  <div class="kicker">NEWSROOMS ACROSS CANADA</div>
  <h1>Across Canada</h1>
  <p class="sub" id="feed-note">Starting the poller…</p>
  <p class="tech" id="tech"></p>
  <div class="filters" id="views"></div>
  <div id="story-filters">
  <p class="filter-label">TOPIC</p>
  <div class="filters" id="topics"></div>
  <p class="filter-label">PLACE</p>
  <div class="filters" id="places"></div>
  </div>
  <ol class="steps" id="steps"></ol>
  <div class="stats" id="stats"></div>
</header>
<main>
  <div id="stories"></div>
  <p class="empty" id="empty">Waiting for the first stories from newsrooms across Canada.</p>
  <div id="thread-list" hidden></div>
  <p class="empty" id="threads-empty" hidden>No thread has a second report yet. A thread collects later stories about the same situation. A single story stays under Stories.</p>
  <section id="log">
    <h3>PIPELINE LOG</h3>
    <ul id="events"></ul>
  </section>
</main>
<script>
const STEPS = ["Registry", "Poller", "Dedup", "Normalize", "Llama", "Kokoro", "Compare"];
let view = "stories";
let topic = "All";
let place = "All";
let latest = null;

function when(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

function stageName(data) {
  if (!data.counts.feeds_polled) return "Poller";
  if (!data.counts.stories) return "Dedup";
  if (data.counts.summarized < data.counts.stories) return "Llama";
  if (data.tts_ready && data.counts.audio < data.counts.summarized) return "Kokoro";
  return "Compare";
}

function renderSteps(active) {
  const list = document.getElementById("steps");
  list.replaceChildren();
  for (const name of STEPS) {
    const item = document.createElement("li");
    item.textContent = name;
    if (name === active) item.className = "on";
    list.appendChild(item);
  }
}

function renderChips(id, values, selected, onPick) {
  const root = document.getElementById(id);
  root.replaceChildren();
  for (const value of values || ["All"]) {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = value;
    if (value === selected) button.className = "on";
    button.addEventListener("click", () => onPick(value));
    root.appendChild(button);
  }
}

function renderStats(data) {
  const bits = [
    ["Feeds", data.counts.feeds],
    ["Stories", data.counts.stories],
    ["Comparisons", data.counts.comparisons],
    ["Briefs", data.counts.summarized],
    ["Audio", data.counts.audio],
  ];
  const root = document.getElementById("stats");
  root.replaceChildren();
  for (const [label, value] of bits) {
    const span = document.createElement("span");
    const strong = document.createElement("strong");
    strong.textContent = String(value);
    span.append(label + " ", strong);
    root.appendChild(span);
  }
}

function hasLabel(values, selected) {
  return selected === "All" || (values || []).indexOf(selected) !== -1;
}

function visibleClusters(data) {
  return (data.clusters || []).filter((cluster) => {
    const topicOk = topic === "All" || cluster.sources.some((source) => hasLabel(source.categories, topic));
    const placeOk = place === "All" || cluster.sources.some((source) => hasLabel(source.places, place));
    return topicOk && placeOk;
  });
}

function signature(cluster) {
  const notes = (cluster.framing || []).map((note) => note.outlet + ":" + note.note).join(";");
  const sources = cluster.sources.map((source) => [
    source.id,
    source.summary || "",
    source.audio_url || "",
    (source.feeds || []).join(","),
  ].join("~")).join("|");
  return notes + "||" + sources;
}

function renderFraming(card, cluster) {
  const box = card.querySelector(".framing");
  box.replaceChildren();
  const notes = cluster.framing || [];
  if (cluster.sources.length < 2 || !notes.length) {
    box.hidden = true;
    return;
  }
  box.hidden = false;
  const label = document.createElement("div");
  label.className = "framing-label";
  label.textContent = "What each outlet emphasized";
  box.appendChild(label);
  const order = cluster.outlets || [];
  const sorted = notes.slice().sort((left, right) => order.indexOf(left.outlet) - order.indexOf(right.outlet));
  for (const note of sorted) {
    const line = document.createElement("p");
    const name = document.createElement("strong");
    name.textContent = note.outlet;
    line.append(name, " " + note.note);
    box.appendChild(line);
  }
}

function ensureCard(cluster) {
  let card = document.getElementById("story-" + cluster.id);
  if (card) return card;
  card = document.createElement("article");
  card.id = "story-" + cluster.id;
  card.className = "card";
  card.innerHTML = [
    "<img alt=''>",
    "<div>",
    "<div class='badge' hidden></div>",
    "<div class='meta'></div>",
    "<h2><a target='_blank' rel='noopener'></a></h2>",
    "<div class='framing' hidden></div>",
    "<div class='single'>",
    "<p class='summary'></p>",
    "<p class='excerpt' hidden></p>",
    "<div class='status'></div>",
    "<audio controls preload='none' hidden></audio>",
    "</div>",
    "<div class='versions' hidden></div>",
    "</div>",
  ].join("");
  return card;
}

function fillCard(card, cluster) {
  const compare = cluster.sources.length > 1;
  const lead = cluster.sources[0];
  card.classList.toggle("compare", compare);
  const photo = Boolean(cluster.image_url);
  card.classList.toggle("no-photo", !photo);
  const image = card.querySelector("img");
  image.hidden = !photo;
  if (photo && image.getAttribute("src") !== cluster.image_url) {
    image.src = cluster.image_url;
    image.alt = "";
  }
  const badge = card.querySelector(".badge");
  badge.hidden = !compare;
  badge.textContent = compare ? "Compare " + cluster.outlets.join(" · ") : "";
  const metaBits = compare
    ? [cluster.outlets.length + " outlets", when(cluster.published_at)]
    : [lead.feeds[0] || lead.outlet, when(lead.published_at)];
  if (!compare && lead.also_on && lead.also_on.length) metaBits.push("also " + lead.also_on.join(", "));
  card.querySelector(".meta").textContent = metaBits.filter(Boolean).join(" · ");
  const heading = card.querySelector("h2");
  heading.hidden = compare;
  const link = heading.querySelector("a");
  link.textContent = lead.title;
  link.href = lead.url;
  renderFraming(card, cluster);
  const single = card.querySelector(".single");
  const versions = card.querySelector(".versions");
  single.hidden = compare;
  versions.hidden = !compare;
  if (!compare) {
    const summary = single.querySelector(".summary");
    const briefText = plainBrief(lead.summary);
    summary.textContent = briefText || "Writing the brief…";
    single.querySelector(".excerpt").hidden = true;
    single.querySelector(".status").hidden = true;
    single.querySelector("audio").hidden = true;
    return;
  }
  versions.replaceChildren();
  for (const source of cluster.sources) {
    const block = document.createElement("section");
    block.className = "version";
    const who = document.createElement("div");
    who.className = "outlet";
    who.textContent = (source.feeds && source.feeds[0]) || source.outlet || "Outlet";
    const title = document.createElement("h3");
    const sourceLink = document.createElement("a");
    sourceLink.target = "_blank";
    sourceLink.rel = "noopener";
    sourceLink.href = source.url;
    sourceLink.textContent = source.title;
    title.appendChild(sourceLink);
    const summary = document.createElement("p");
    summary.className = "summary";
    const briefText = plainBrief(source.summary);
    summary.textContent = briefText;
    summary.hidden = !briefText;
    block.append(who, title, summary);
    versions.appendChild(block);
  }
}

function renderStories(clusters) {
  const root = document.getElementById("stories");
  const empty = document.getElementById("empty");
  const total = latest && latest.counts ? latest.counts.stories : 0;
  empty.hidden = clusters.length > 0;
  empty.textContent = total
    ? "No stories in this category yet."
    : "Waiting for the first stories from newsrooms across Canada.";
  const keep = new Set();
  for (const cluster of clusters) {
    const domId = "story-" + cluster.id;
    keep.add(domId);
    const card = ensureCard(cluster);
    const sig = signature(cluster);
    if (card.dataset.sig !== sig) {
      card.dataset.sig = sig;
      fillCard(card, cluster);
    }
    root.appendChild(card);
  }
  for (const child of [...root.children]) {
    if (!keep.has(child.id)) child.remove();
  }
}

function renderEvents(events) {
  const list = document.getElementById("events");
  list.replaceChildren();
  for (const event of events) {
    const item = document.createElement("li");
    item.textContent = when(event.ts) + "  " + event.stage + "  " + event.message;
    list.appendChild(item);
  }
}

function plainBrief(text) {
  return (text || "").replace(/^(?:Good (?:morning|afternoon|evening|night)[,.]?[ \t]*)?(?:I(?:'m| am) reporting(?: live)? from [^.]+[. \t]*)+/i, "").trim();
}

function emptyQuestion(text) {
  const value = (text || "").trim().toLowerCase().replace(/^still unknown:\\s*/, "");
  return !value || value === "what is still unknown" || value === "what is newly known" || value === "unknown";
}

function threadHeading(thread) {
  const title = (thread.title || "").trim();
  if (/^[0-9a-f]{6,}$/i.test(title)) {
    const update = (thread.updates || [])[0];
    return (update && update.title) || "Open situation";
  }
  return title;
}

function usefulNote(note, update) {
  if (emptyQuestion(note)) return "";
  if (note === update.title || note === update.summary) return "";
  return note;
}

function renderThreads(threads) {
  const root = document.getElementById("thread-list");
  const empty = document.getElementById("threads-empty");
  empty.hidden = view !== "threads" || threads.length > 0;
  root.replaceChildren();
  for (const thread of threads) {
    const card = document.createElement("article");
    card.className = "thread";
    const badge = document.createElement("div");
    badge.className = "badge";
    badge.textContent = thread.status === "open" ? "Open" : "Closed";
    const title = document.createElement("h2");
    title.textContent = threadHeading(thread);
    const question = document.createElement("p");
    question.className = "meta";
    question.textContent = "Still open: " + thread.open_question;
    question.hidden = emptyQuestion(thread.open_question);
    const timeline = document.createElement("ol");
    timeline.className = "timeline";
    for (const update of thread.updates || []) {
      const item = document.createElement("li");
      const whenText = document.createElement("div");
      whenText.className = "meta";
      const who = update.outlet ? update.outlet + " · " : "";
      whenText.textContent = who + when(update.created_at);
      const link = document.createElement("a");
      link.target = "_blank";
      link.rel = "noopener";
      link.href = update.url || "#";
      link.textContent = update.title || "Story";
      const brief = document.createElement("p");
      brief.className = "summary";
      const briefText = plainBrief(update.summary);
      brief.textContent = briefText;
      brief.hidden = !briefText;
      item.append(whenText, link, brief);
      const note = usefulNote(update.note, update);
      if (note) {
        const detail = document.createElement("div");
        detail.className = "meta";
        detail.textContent = note;
        item.append(detail);
      }
      timeline.appendChild(item);
    }
    card.append(badge, title, question, timeline);
    root.appendChild(card);
  }
}

function showView() {
  const storiesOn = view === "stories";
  document.getElementById("story-filters").hidden = !storiesOn;
  document.getElementById("stories").hidden = !storiesOn;
  document.getElementById("thread-list").hidden = storiesOn;
  const threads = (latest && latest.threads) || [];
  document.getElementById("threads-empty").hidden = storiesOn || threads.length > 0;
  if (!storiesOn) document.getElementById("empty").hidden = true;
}

function bindViews() {
  renderChips("views", ["Stories", "Threads"], view === "stories" ? "Stories" : "Threads", (value) => {
    view = value === "Threads" ? "threads" : "stories";
    bindViews();
    paint();
  });
}

function paint() {
  if (!latest) return;
  showView();
  if (view === "stories") renderStories(visibleClusters(latest));
  else renderThreads(latest.threads || []);
}

function bindFilters(data) {
  renderChips("topics", data.topics, topic, (value) => {
    topic = value;
    bindFilters(latest);
    paint();
  });
  renderChips("places", data.places, place, (value) => {
    place = value;
    bindFilters(latest);
    paint();
  });
}

async function refresh() {
  const response = await fetch("/api/snapshot", { cache: "no-store" });
  const data = await response.json();
  latest = data;
  if ((data.topics || []).indexOf(topic) === -1) topic = "All";
  if ((data.places || []).indexOf(place) === -1) place = "All";
  const ready = data.counts.summarized;
  const total = data.counts.stories;
  let note = data.counts.feeds + " feeds from newsrooms across Canada. Matching headlines stay in one card so you can compare outlets.";
  if (total && ready < total) note = ready + " of " + total + " briefs are ready. " + note;
  document.getElementById("feed-note").textContent = note;
  document.getElementById("tech").textContent = [data.broker, data.model, data.tts_status].filter(Boolean).join(" · ");
  bindViews();
  bindFilters(data);
  renderSteps(stageName(data));
  renderStats(data);
  paint();
  renderEvents(data.events || []);
}

refresh();
setInterval(refresh, 2000);
</script>
</body>
</html>
"""


def _excerpt(text: str, limit: int = 700) -> str:
    cleaned = " ".join((text or "").split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[:limit].rsplit(" ", 1)[0] + "…"


def _ordered(present: set[str], order: list[str]) -> list[str]:
    known = [item for item in order if item in present]
    extra = sorted(present - set(known))
    return ["All", *known, *extra]


def _source_label(feed_name: str, outlet: str) -> str:
    outlet = outlet or feed_name
    if feed_name.startswith(outlet + " "):
        detail = feed_name[len(outlet) + 1 :]
        return f"{outlet} · {detail}" if detail else outlet
    if feed_name == outlet:
        return outlet
    return f"{outlet} · {feed_name}"


def _thread_cards(conn: sqlite3.Connection) -> list[dict]:
    threads = [
        dict(row)
        for row in conn.execute(
            """
            SELECT id, title, status, open_question, opened_at, updated_at
            FROM threads
            ORDER BY CASE status WHEN 'open' THEN 0 ELSE 1 END, updated_at DESC
            """
        )
    ]
    if not threads:
        return []
    updates: dict[str, list[dict]] = {thread["id"]: [] for thread in threads}
    for row in conn.execute(
        """
        SELECT update_row.thread_id, update_row.note, update_row.created_at,
               article.title, article.url, article.summary, article.outlet
        FROM thread_updates AS update_row
        JOIN articles AS article ON article.id = update_row.article_id
        ORDER BY update_row.id
        """
    ):
        bucket = updates.get(row["thread_id"])
        if bucket is None:
            continue
        bucket.append(
            {
                "note": row["note"],
                "created_at": row["created_at"],
                "title": row["title"],
                "url": row["url"],
                "summary": row["summary"] or "",
                "outlet": row["outlet"] or "",
            }
        )
    for thread in threads:
        thread["updates"] = updates.get(thread["id"], [])
    return [thread for thread in threads if len(thread["updates"]) >= 2]


def snapshot(db_path: Path) -> dict:
    conn = sqlite3.connect(db_path, timeout=5)
    conn.row_factory = sqlite3.Row
    try:
        feed_rows = [dict(row) for row in conn.execute("SELECT * FROM feeds ORDER BY id")]
        topics = _ordered({row["category"] for row in feed_rows if row.get("category")}, list(TOPIC_ORDER))
        places = _ordered({row["place"] for row in feed_rows if row.get("place")}, list(PLACE_ORDER))
        rows = conn.execute(
            """
            SELECT
                article.id, article.title, article.url, article.image_url, article.summary,
                article.summary_words, article.summary_engine, article.clean_text, article.raw_text,
                article.audio_path, article.audio_status, article.published_at, article.first_seen_at,
                article.cluster_id, article.category, article.place, article.outlet,
                feed.name AS feed_name, feed.outlet AS feed_outlet,
                feed.category AS feed_category, feed.place AS feed_place
            FROM articles AS article
            JOIN article_feeds AS link ON link.article_id = article.id
            JOIN feeds AS feed ON feed.id = link.feed_id
            WHERE article.id IN (
                SELECT id FROM articles
                ORDER BY COALESCE(published_at, first_seen_at) DESC, id DESC
                LIMIT 160
            )
            ORDER BY COALESCE(article.published_at, article.first_seen_at) DESC, article.id DESC
            """
        ).fetchall()
        grouped: dict[int, dict] = {}
        order: list[int] = []
        for row in rows:
            item = grouped.get(row["id"])
            if item is None:
                audio_name = row["audio_path"]
                item = {
                    "id": row["id"],
                    "title": row["title"],
                    "url": row["url"],
                    "image_url": row["image_url"],
                    "summary": row["summary"],
                    "summary_words": row["summary_words"],
                    "summary_engine": row["summary_engine"],
                    "excerpt": _excerpt(row["clean_text"] or row["raw_text"] or ""),
                    "audio_url": f"/audio/{audio_name}" if audio_name else None,
                    "published_at": row["published_at"] or row["first_seen_at"],
                    "outlet": row["feed_outlet"] or row["outlet"] or "",
                    "cluster_id": row["cluster_id"] or f"solo-{row['id']}",
                    "categories": [],
                    "places": [],
                    "feeds": [],
                }
                grouped[row["id"]] = item
                order.append(row["id"])
            category = row["feed_category"] or row["category"]
            place = row["feed_place"] or row["place"]
            if category and category not in item["categories"]:
                item["categories"].append(category)
            if place and place not in item["places"]:
                item["places"].append(place)
            label = _source_label(row["feed_name"], row["feed_outlet"] or row["outlet"] or "")
            if label not in item["feeds"]:
                item["feeds"].append(label)

        clusters: dict[str, list[dict]] = {}
        cluster_order: list[str] = []
        for article_id in order:
            item = grouped[article_id]
            feeds = item["feeds"]
            source = {
                "id": item["id"],
                "title": item["title"],
                "url": item["url"],
                "summary": item["summary"],
                "summary_words": item["summary_words"],
                "summary_engine": item["summary_engine"],
                "excerpt": item["excerpt"],
                "audio_url": item["audio_url"],
                "published_at": item["published_at"],
                "outlet": item["outlet"],
                "categories": item["categories"],
                "places": item["places"],
                "feeds": feeds[:1],
                "also_on": feeds[1:],
            }
            cluster_id = item["cluster_id"]
            if cluster_id not in clusters:
                clusters[cluster_id] = []
                cluster_order.append(cluster_id)
            clusters[cluster_id].append(source)

        framings: dict[str, list] = {}
        for row in conn.execute("SELECT cluster_id, notes_json FROM framings"):
            try:
                framings[row["cluster_id"]] = json.loads(row["notes_json"])
            except json.JSONDecodeError:
                continue

        cards = []
        for cluster_id in cluster_order[:80]:
            sources = clusters[cluster_id]
            outlets: list[str] = []
            image_url = None
            for source in sources:
                if source["outlet"] and source["outlet"] not in outlets:
                    outlets.append(source["outlet"])
                if image_url is None and grouped[source["id"]]["image_url"]:
                    image_url = grouped[source["id"]]["image_url"]
            cards.append(
                {
                    "id": cluster_id,
                    "image_url": image_url,
                    "published_at": sources[0]["published_at"],
                    "outlets": outlets,
                    "sources": sources,
                    "framing": framings.get(cluster_id, []),
                }
            )

        events = [
            dict(row)
            for row in conn.execute(
                "SELECT ts, stage, message FROM events ORDER BY id DESC LIMIT 12"
            )
        ]
        runtime = {
            row["key"]: row["value"] for row in conn.execute("SELECT key, value FROM runtime")
        }
        story_total = conn.execute("SELECT COUNT(*) AS n FROM articles").fetchone()["n"]
        summarized = conn.execute(
            "SELECT COUNT(*) AS n FROM articles WHERE summary IS NOT NULL AND summary != ''"
        ).fetchone()["n"]
        audio = conn.execute(
            "SELECT COUNT(*) AS n FROM articles WHERE audio_path IS NOT NULL AND audio_path != ''"
        ).fetchone()["n"]
        comparisons = conn.execute(
            """
            SELECT COUNT(*) AS n FROM (
                SELECT cluster_id FROM articles
                WHERE cluster_id IS NOT NULL AND outlet IS NOT NULL AND outlet != ''
                GROUP BY cluster_id
                HAVING COUNT(DISTINCT outlet) > 1
            )
            """
        ).fetchone()["n"]
        feeds_polled = sum(1 for row in feed_rows if row.get("last_fetched_at"))
        return {
            "topics": topics,
            "places": places,
            "broker": runtime.get("broker", ""),
            "model": runtime.get("model", OLLAMA_MODEL),
            "tts_status": runtime.get("tts_status", "Kokoro-82M"),
            "tts_ready": runtime.get("tts_status") == "Kokoro-82M",
            "clusters": cards,
            "threads": _thread_cards(conn),
            "events": events,
            "counts": {
                "feeds": len(feed_rows),
                "feeds_polled": feeds_polled,
                "stories": story_total,
                "comparisons": comparisons,
                "summarized": summarized,
                "audio": audio,
            },
        }
    finally:
        conn.close()


def _handler(db_path: Path, audio_dir: Path):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *args) -> None:
            return

        def _send(self, status: int, body: bytes, content_type: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            path = unquote(urlparse(self.path).path)
            try:
                if path in ("/", "/index.html"):
                    self._send(200, PAGE.encode("utf-8"), "text/html; charset=utf-8")
                    return
                if path == "/api/snapshot":
                    payload = json.dumps(snapshot(db_path)).encode("utf-8")
                    self._send(200, payload, "application/json; charset=utf-8")
                    return
                if path == "/favicon.ico":
                    self.send_response(204)
                    self.end_headers()
                    return
                if path.startswith("/audio/"):
                    name = Path(path.removeprefix("/audio/")).name
                    file_path = audio_dir / name
                    if file_path.suffix.lower() != ".wav" or not file_path.is_file():
                        self._send(404, b"missing audio", "text/plain; charset=utf-8")
                        return
                    self._send(200, file_path.read_bytes(), "audio/wav")
                    return
                self._send(404, b"not found", "text/plain; charset=utf-8")
            except Exception as exc:
                message = str(exc).encode("utf-8", errors="replace")
                self._send(500, message, "text/plain; charset=utf-8")

    return Handler


def serve_ui(db_path: Path, audio_dir: Path, host: str, port: int) -> ThreadingHTTPServer:
    audio_dir.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer((host, port), _handler(db_path, audio_dir))
    return server
