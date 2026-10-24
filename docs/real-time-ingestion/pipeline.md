# Ingestion pipeline

How `realtime_ingestion` turns an RSS item into a mobile-ready brief and optional spoken Opus file.

## Prerequisites on the GPU / ingest host

1. Install [Ollama](https://ollama.com) and pull the 8B model:

   ```text
   ollama pull llama3.1:8b
   ```

2. Confirm the API:

   ```text
   curl http://127.0.0.1:11434/api/tags
   ```

3. Install Kokoro-82M (or the project’s chosen Kokoro runtime) with a voice suitable for short news briefs (current default voice name in code: `af_heart`).
4. Have Redis available (or accept in-process fakeredis for solo local runs).
5. Have publish targets reachable: MongoDB and S3 (or MinIO in Docker).

Without Ollama, briefs degrade to extractive text. Without Kokoro, stories stay text-only.

## Stages

```mermaid
stateDiagram-v2
  [*] --> Fetched: poller stores article
  Fetched --> Summarizing: news:articles
  Summarizing --> BriefReady: Ollama or extractive
  BriefReady --> Framing: cluster has 2+ briefs
  BriefReady --> ThreadReview: model IGNORE/OPEN/UPDATE
  BriefReady --> AwaitGpu: news:summaries
  AwaitGpu --> Synthesizing: GPU rest
  AwaitGpu --> TextPublish: audio disabled or deferred
  Synthesizing --> AudioReady: Opus written
  BriefReady --> TextPublish: always allowed for text
  TextPublish --> MongoUpsert
  AudioReady --> S3Upload
  S3Upload --> MongoAudioAttach
  MongoUpsert --> ReadyForApi
  MongoAudioAttach --> ReadyForApi
```

### 1. Poll and store

Unchanged intent from today’s poller:

- Conditional HTTP fetch (`ETag` / `Last-Modified` / body hash).
- Parse RSS; skip known URLs; enrich short bodies with one HTML fetch.
- Redis seen-keys per feed; SQLite (working store) insert + cluster assignment.
- `XADD` article id onto `news:articles`.

### 2. Summarize first (required)

The AI worker:

1. Reads one `news:articles` message.
2. Calls Ollama chat with a strict “~50 plain words” prompt.
3. Saves `summary`, `summaryWords`, `summaryEngine`.
4. Acknowledges the stream message.
5. Enqueues `news:summaries` for TTS **after** a non-empty brief exists.
6. May run framing and thread logic next (still text-side; no GPU speech yet).

**Rule:** Never start Kokoro for an article that has no brief.

### 3. GPU scheduling (before Kokoro)

Ollama and Kokoro share one GPU. On a small card (GTX 1060, 6 GB) an 8B model and Kokoro do not fit together, and contended inference causes timeouts and garbled audio. `tts/gpu_gate.py` makes them **take turns**.

**Priority:** brief for every new article → speech → enrichment (storyline decisions, multi-outlet framing).

| Rule | Behavior |
| --- | --- |
| Brief exists | Speech is only queued after `summary` is saved |
| LLM first | Ollama calls run whenever no speech turn is open |
| Speech turn starts | LLM quiet for `TTS_IDLE_GRACE_SECONDS` (4s), so a burst of articles is briefed first |
| Starvation guard | A brief that waited `TTS_MAX_LAG_SECONDS` (240s) forces a turn; new LLM calls queue behind it |
| Batching | A turn speaks at least `TTS_TURN_MIN` (4) briefs before yielding to new articles (`TTS_TURN_MAX` when forced), so one model swap covers several briefs |
| Model swap | With `GPU_SWAP_MODELS`, a turn unloads Ollama (`keep_alive: 0`), moves Kokoro to CUDA, and parks Kokoro on CPU when the turn ends |
| Enrichment | Runs when articles and speech are idle, and at least every `ENRICH_MAX_LAG_SECONDS` under load. Framing is debounced per cluster |
| Backpressure | The poller pauses intake while `ARTICLE_BACKLOG_MAX` (40) recent articles wait for a brief |
| Kokoro on CPU | `TTS_DEVICE=cpu` (or no CUDA): speech never waits on the LLM |
| CUDA failure | First failed GPU render (e.g. torch built without `sm_61`) switches Kokoro to CPU for the run |

Jobs are acked only after they finish. On restart each worker drains its unacked Redis entries first (`read_pending`); with the in-process broker, recent briefs without audio are requeued from SQLite.

### 4. Synthesize Opus

When the gate passes:

1. Prepare speech text (normalize numbers, strip URLs — existing `prepare_speech_text` intent).
2. Run Kokoro with the configured voice.
3. Encode **Opus** (recommend 24–32 kbps mono for brief length).
4. Write a temp file, then upload.

If Kokoro is not installed: set `audioStatus = unavailable`, ack the message, do not block text publish.

### 5. Publish to MongoDB and S3

**Recommended ordering**

1. Upsert the story summary document in MongoDB as soon as the brief is final (`audioStatus = pending | unavailable`).
2. Upload Opus to S3 under a deterministic key (see [data-model.md](./data-model.md)).
3. Patch the MongoDB document: `audioKey`, `audioStatus = ready`, `audioContentType = audio/opus`, `publishedAt` if not set.

**Strict listen mode (optional flag):** delay API visibility until step 3 succeeds. Default for Home “listen” sampling is to include `audioStatus = ready` only; text Home may include `pending`.

**Atomicity.** There is no distributed transaction. Use:

- Idempotent S3 puts (same key).
- Idempotent Mongo upserts on `storyId`.
- A `publishAttempts` counter and dead-letter log on repeated failure.

### 6. Framing and threads (text side)

These enrich MongoDB collections the Home **coverage pager** and the **Storylines** tab read. They do not require Opus.

- **Framing (Coverage):** when a cluster has ≥2 briefs, write one sentence per outlet into `framings` / embedded compare docs (consumed via horizontal full-screen pages on Home).
- **Storylines:** model returns `IGNORE` | `OPEN` | `UPDATE`; maintain thread documents and ordered updates.

Publish framing/thread docs independently of audio readiness.

## Working store vs publish store

| Store | Holds | Consumers |
| --- | --- | --- |
| SQLite (today) | In-flight articles, feeds, events, local reader | Pipeline + temp UI |
| Redis Streams | Work queues | Workers only |
| MongoDB | Published stories, compare, threads | Lambda API |
| S3 | Opus bytes | App via signed URL |

Retention (hourly, `realtime_ingestion/maintenance.py`):

- **Working store:** article text is dropped once briefed; local audio once S3 has it (failed uploads stay as `upload_failed` and are retried every 10 min). Rows stay 7 days for dedupe (RSS feeds re-list items for days), then go.
- **Published store:** a story is removed from MongoDB and S3 **14 days** after publishing unless a live storyline lists it. Storylines auto-close after **7 days** without an update and are removed, with their stories, **30 days** after closing. S3 is deleted first, then Mongo.
- **Storyline docs are merged, not replaced:** each publish upserts entries by `storyId`, so Mongo keeps entries the ingest box has already pruned. When a story's audio lands, its storyline entry is marked `ready` too.

Migration note: until Mongo publish is implemented, the local reader continues to read SQLite. After publish lands, the mobile app must not depend on SQLite.

## Configuration

Read from the environment, then the repo-root `.env` (`CNEWS_ENV_FILE` overrides the path). Full list with defaults: `realtime_ingestion/config.py` and `.env.example`.

| Variable | Purpose |
| --- | --- |
| `OLLAMA_URL` | Default `http://127.0.0.1:11434` |
| `OLLAMA_MODEL` | Default `llama3.1:8b` |
| `OLLAMA_NUM_CTX` | Default `3072`; sent on every call so Ollama never reloads between calls |
| `OLLAMA_KEEP_ALIVE` | Default `30m` |
| `KOKORO_VOICE` | e.g. `af_heart` |
| `TTS_ENABLED` | `true` / `false` |
| `TTS_DEVICE` | `auto` / `cuda` / `cpu` |
| `GPU_GATE_ENABLED` | Default `true` |
| `GPU_SWAP_MODELS` | Default `true` (single small GPU) |
| `MONGODB_URI` | Publish target |
| `S3_ENDPOINT` | AWS or MinIO URL |
| `S3_BUCKET` | Audio bucket |
| `S3_PREFIX` | e.g. `audio/opus/` |
| `REDIS_URL` | Stream broker |
| `PUBLISH_REQUIRE_AUDIO` | If `true`, hide from listen APIs until Opus ready |
| `CNEWS_DATA_DIR` | Working store + audio dir (default `./data`) |

## Observability

Emit structured events (also fine in the existing `events` table for local):

- `brief_ready`, `gpu_wait`, `tts_start`, `tts_done`, `mongo_upsert`, `s3_put`, `publish_ready`, `publish_failed`.

The temporary reader can keep showing these for developers. Mobile users never see them.

## Acceptance checklist

- [ ] `ollama pull llama3.1:8b` documented and verified on a clean machine.
- [x] Brief always precedes TTS enqueue.
- [x] Busy GPU delays TTS without dropping the brief (`realtime_ingestion/tests`).
- [ ] Opus lands in S3; MongoDB references the key.
- [ ] Text-only path works when TTS is off.
- [ ] Coverage pager data and Storylines update without waiting on audio.
