# Real-time ingestion — development docs

Canadian news middleman: poll RSS, write short briefs, track storylines, speak summaries, and serve **CrackNews** (Expo) via a .NET API.

This folder is the product and engineering source of truth. **No application code lives here** — only plans, contracts, and UX guidance.

## Start here

| If you want… | Read |
| --- | --- |
| Run the app today | **[DEV.md](./DEV.md)** |
| What is already built | **[SHIPPED.md](./SHIPPED.md)** |
| Future login prefs / outlet subscribe / recommendations | **[upgrade-plan.md](./upgrade-plan.md)** |
| Ultra delivery roadmap | [roadmap.md](./roadmap.md) |

## Components (independent folders)

| Piece | Path | Role |
| --- | --- | --- |
| Ingestion pipeline | `realtime_ingestion/` | Poll → summarize (Ollama) → speak (Kokoro) → publish |
| Backend API | `backend/` | .NET 10 Web API (Kestrel / Lambda-ready) |
| Mobile app | `mobile/` | CrackNews — Expo + Zustand + expo-audio |
| Local stack | `docker-compose.yml` | MongoDB, PostgreSQL, Redis (+ MinIO profile) |

`backend/` and `mobile/` are **independent** — integrate only over `/v1` ([api.md](./api.md)).

## Doc map

| Doc | Read when you need… |
| --- | --- |
| [DEV.md](./DEV.md) | Runbook, env vars, module map |
| [SHIPPED.md](./SHIPPED.md) | Accurate shipped vs deferred inventory |
| [upgrade-plan.md](./upgrade-plan.md) | Preferences, outlet subscribe, For You ranker |
| [architecture.md](./architecture.md) | End-to-end system map |
| [features.md](./features.md) | Product features and acceptance criteria |
| [pipeline.md](./pipeline.md) | Ollama → GPU-gated Kokoro → publish rules |
| [data-model.md](./data-model.md) | MongoDB / PostgreSQL / S3 shapes |
| [backend.md](./backend.md) | .NET API, Lambda, Docker |
| [api.md](./api.md) | HTTP contracts |
| [mobile.md](./mobile.md) | CrackNews UX (as built + deferred) |
| [local-development.md](./local-development.md) | Machine setup, Ollama, Compose |
| [roadmap.md](./roadmap.md) | Phases P0–P7, critical path |
| [IMPLEMENTATION.md](./IMPLEMENTATION.md) | Slice status / smoke notes |

## North-star user loop (current)

1. Open CrackNews → immersive **two-column** Home wall.
2. Tap a card → **in-tab** full-screen story; Original in WebView.
3. Center **Play** speaks the current page’s briefs; leaving the page stops audio.
4. **Storylines** → outlet timeline (timestamp · line · nodes · cards).
5. Optional Google / `dev:` login; tune **topics** in Settings (Home is always voice-ready).
6. Display ads may appear as labeled cards on Home / Storylines; they are not in Play.
7. Multi-outlet compare swipe is **deferred** — same story may still show as multiple wall cards.

## Design principles

- Briefs are the product; full articles stay at the source (in-app Original WebView).
- Play is intentional and page-scoped — never auto-starts on card open.
- Summary before speech; speech waits for a free GPU.
- Mobile: SQLite/cache + remote API; Postgres for users; Mongo for content.
- Temporary HTML reader in `realtime_ingestion` is for pipeline ops only.
