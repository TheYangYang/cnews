# Architecture

## Purpose

Build a Canadian news middleman: poll RSS feeds, keep one copy of each story, write a short brief with a local LLM, group reports that belong together, speak the brief when a GPU is free, then publish text and audio for a mobile app.

Today the pipeline still uses a local SQLite database and a temporary results page at `http://127.0.0.1:8765`. The target architecture below is what we are building toward. See [roadmap.md](./roadmap.md) for the migration path.

## Target system map

```mermaid
flowchart TB
  subgraph sources [Sources]
    RSS[RSS feeds]
  end

  subgraph ingest [realtime_ingestion]
    Poller[Poller]
    AI[AI worker - Ollama 8B]
    GPUGate[GPU rest gate]
    TTS[Kokoro TTS - Opus]
    Publish[Publisher]
  end

  subgraph bus [Work bus]
    Articles[news:articles]
    Summaries[news:summaries]
  end

  subgraph local [Local / GPU host]
    Ollama[Ollama llama3.1:8b]
    Kokoro[Kokoro-82M]
    Redis[(Redis Streams)]
    WorkDB[(Working store SQLite or Redis)]
  end

  subgraph cloud [Cloud publish]
    Mongo[(MongoDB content)]
    PG[(PostgreSQL users)]
    S3[(S3 Opus objects)]
  end

  subgraph api [backend]
    Lambda[.NET 10 Web API on Lambda]
    CDN[CloudFront or signed URLs]
  end

  subgraph clients [Clients]
    Mobile[React Native Expo]
    LocalDB[(Device SQLite)]
    DevUI[Temporary local reader]
  end

  RSS --> Poller
  Poller --> WorkDB
  Poller --> Articles
  Articles --> AI
  AI --> Ollama
  AI --> WorkDB
  AI --> Summaries
  Summaries --> GPUGate
  GPUGate -->|GPU free| TTS
  TTS --> Kokoro
  AI --> Publish
  TTS --> Publish
  Publish -->|summary JSON| Mongo
  Publish -->|audio/opus| S3
  Mongo --> Lambda
  PG --> Lambda
  S3 --> CDN
  Lambda --> Mobile
  Mobile --> LocalDB
  CDN --> Mobile
  WorkDB --> DevUI
  Redis --- Articles
  Redis --- Summaries
```

## Responsibilities

### `realtime_ingestion` (Python)

- Own feed registry, polling, dedupe, clustering, briefs, framing, threads.
- Call Ollama for text work (briefs, framing sentences, thread decisions).
- Call Kokoro only after the brief exists **and** the GPU is idle.
- Publish ready stories: summary document → MongoDB; Opus file → S3.
- Keep a working store for in-flight work and the temporary reader.
- Never expose MongoDB or S3 credentials to the mobile app.

### `backend` (.NET 10 Web API → AWS Lambda)

- Read API over published MongoDB documents (stories, coverage, storylines).
- Auth + profile API against **PostgreSQL** (Google Sign-In).
- Issue short-lived audio URLs (signed S3 or CloudFront).
- Filter feeds by topic preferences (query and/or stored user prefs).
- Deploy as a container image to Lambda; locally emulate with Docker + Lambda RIE.

### Mobile (React Native + Expo Go)

- Immersive Home wall (masonry) → full-screen reader; Coverage = horizontal outlet swipe (no Coverage tab).
- Tabs: Home · Play · Storylines · Settings.
- Stack: latest React Native / Expo, **HeroUI Native**, **Zustand**, on-device **SQLite** + remote API.
- Talk only to the backend API. Never talk to Ollama, Redis, or the GPU host.

## End-to-end story lifecycle

```mermaid
sequenceDiagram
  participant Poller
  participant Redis
  participant AI as AI worker
  participant Ollama
  participant TTS as TTS worker
  participant Kokoro
  participant Mongo
  participant S3
  participant API as Lambda API
  participant App as Mobile

  Poller->>Redis: XADD news:articles
  AI->>Redis: read article
  AI->>Ollama: summarize ~50 words
  Ollama-->>AI: brief
  AI->>Redis: XADD news:summaries
  Note over AI: framing + threads may run after brief
  TTS->>Redis: read summary
  TTS->>TTS: wait until GPU rest
  TTS->>Kokoro: synthesize Opus
  Kokoro-->>TTS: audio.opus
  AI->>Mongo: upsert summary doc when text ready
  TTS->>S3: put Object audio/opus
  TTS->>Mongo: attach audioKey + audioReady
  App->>API: GET /v1/home/feed
  API->>Mongo: page by topics
  API-->>App: story cards + imageUrl
  App->>App: upsert device SQLite
  App->>API: GET audio URL on Play
  App->>S3: stream Opus via signed URL
```

Exact publish ordering rules are in [pipeline.md](./pipeline.md).

## Layering

| Layer | Technology | Notes |
| --- | --- | --- |
| Ingest + AI + TTS | Python, asyncio, Redis Streams | Runs on a GPU-capable host (local machine or GPU instance) |
| LLM | Ollama + `llama3.1:8b` | Required for quality briefs; extractive fallback only for resilience |
| Speech | Kokoro-82M → Opus | Optional for text-only publish; preferred for mobile listen mode |
| Working store | SQLite today | May remain for pipeline ops; not the mobile source of truth |
| Publish store | MongoDB | Stories, coverage (compares), storylines the API serves |
| User store | PostgreSQL | Google identity, topic preferences |
| Media store | AWS S3 | Opus blobs; app never gets a permanent public bucket listing |
| API | ASP.NET Core (.NET 10) on Lambda (container) | Stateless; scales with traffic |
| Client | React Native / Expo / HeroUI Native / Zustand | Immersive wall + full-screen + Play |
| Client cache | SQLite on device | Feed cards + prefs mirror; audio stays remote |

## Why this split

- **GPU work stays off Lambda.** Ollama and Kokoro need sustained compute and often a GPU. Lambda is a poor place for that.
- **Mobile stays thin.** The app asks for cards and audio URLs. It does not know about feeds or models.
- **Publish is intentional.** A story reaches users only after the publish gate passes, so Home never shows half-built briefs without their promised audio state.

## Current vs target (short)

| Concern | Current | Target |
| --- | --- | --- |
| Brief storage | Pipeline SQLite `articles.summary` | MongoDB `stories` (+ device SQLite cache) |
| Audio | Optional local WAV | Opus in S3; MongoDB holds `audioKey` |
| TTS timing | Stream consumer when Kokoro installed | After brief + GPU rest gate |
| Client | Local HTML reader | Expo wall → full-screen (+ coverage swipe) + Storylines |
| Users | — | Google Sign-In → PostgreSQL |
| API | `/api/snapshot` on local process | Versioned REST under `/v1` |

The temporary reader remains useful for watching the pipeline. It is not a substitute for the mobile UX described in [mobile.md](./mobile.md).

## Trust and security boundaries

- RSS fetch and HTML enrich run only inside the ingestion host.
- MongoDB, PostgreSQL, and S3 credentials live in ingestion + Lambda configuration (Secrets Manager / env), never in the app binary.
- Mobile uses Google ID tokens verified by the API; app stores only its own session JWT.
- Guest browse is allowed; mutating preferences on the server requires login.
- Signed audio URLs expire (suggested 15–60 minutes).

## Failure modes we design for

| Failure | Behavior |
| --- | --- |
| Ollama down | Extractive brief; mark `summaryEngine`; still eligible for later TTS if text exists |
| GPU busy | Brief may publish as text-first; audio attaches when Kokoro finishes |
| Kokoro missing | Text-only story; `audioStatus = unavailable` |
| Redis down | In-process fakeredis for local; production Redis required |
| MongoDB / S3 write fails | Retry with backoff; story stays unpublished to the API until both required writes succeed |
| Lambda cold start | Acceptable for v1; keep payloads small and Mongo queries indexed |

## Related docs

- Product behavior: [features.md](./features.md)
- Publish rules: [pipeline.md](./pipeline.md)
- Schemas: [data-model.md](./data-model.md)
- API surface: [api.md](./api.md)
- Lambda + Docker: [backend.md](./backend.md)
- App UX: [mobile.md](./mobile.md)
