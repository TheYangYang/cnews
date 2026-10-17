# Implementation execution plan

Living build plan. Specs remain in the other docs; this file tracks **how we ship**.  
Canonical inventory: [SHIPPED.md](./SHIPPED.md) · Runbook: [DEV.md](./DEV.md).

## Non-negotiables

- Production quality: env config, typed APIs, clear layers.
- Independent folders: `realtime_ingestion/`, `backend/`, `mobile/`.
- Critical path: briefs → Opus + GPU gate → Mongo/S3 publish → `/v1` → CrackNews mobile.
- Loop: plan slice → implement → smoke → next slice.

## Slice status

| Slice | Deliverable | Status |
| --- | --- | --- |
| A | Compose, env examples, folder READMEs | **Done** |
| B | Ingest GPU gate, Opus, Mongo/S3 publish | **Done** (host needs Ollama/Kokoro/ffmpeg for live audio) |
| C | .NET 10 `/v1` + Google/Postgres + storylines cursor | **Done** |
| D | Expo CrackNews: wall / reader / Play / Storylines / Settings | **Done** |
| E | Seed + LAN runbook | **Done** |
| F | Page-scoped Play, Original pause/resume, timeline spine, shuffle refresh, lock-screen audio config | **Done** |
| G | Coverage horizontal pager | **Deferred** |
| H | Outlet subscribe + For You recommendations | **Planned** — [upgrade-plan.md](./upgrade-plan.md) |

## Verified locally (checkpoint)

- `docker compose up -d mongo postgres redis`
- `python3 scripts/seed_demo_mongo.py` and `python3 scripts/seed_demo_ads.py`
- `dotnet test` / API on `:5080`: health, feed (`mode=listen`), ads/display, storylines (+ cursor), coverage, audio-url
- Mobile: Expo SDK 57, Metro LAN; Play + Storylines timeline against seeded Mongo

## Layering

**Ingest:** workers → `publish/` side-effect boundary.  
**Backend:** Api / Application / Domain / Infrastructure.  
**Mobile:** Expo Router · `features/` · `shared/` · `data/` (api, db, stores).

## Recent product hardening (2026-10-17)

- Display ads: story-like cards on Home + Storylines list; tap opens advertiser; not in Play.
- Voice-first: Home always `mode=listen`; Settings is topics only (no listening radios / About).
- Pull-to-refresh while Play: keep current brief, rebind remaining queue.

## Earlier hardening (2026-10-10)

- Brand **CrackNews**; system dark mode; typographic C icon / black splash.
- In-tab readers above the tab bar; Original in WebView.
- Play: no auto-start on open; stop on leave page; surface-aware resume; Storylines queue.
- Storyline timeline: clock stamps, connected icon spine, cards, Original pause/resume.
- Home + Storylines: scroll-down `loadMore`; pull-up shuffle refresh.
- `expo-audio` background playback + lock-screen metadata (native rebuild required).
- Multi-outlet compare UI left deferred; API retained.

## Still operator-owned

1. Docker Desktop before Compose.  
2. `ollama pull llama3.1:8b` for live briefs.  
3. Kokoro + `ffmpeg` for Opus.  
4. MinIO optional (`--profile audio`).  
5. Real Google OAuth for non-dev.  
6. Expo Go / dev client on same Wi‑Fi as API; set `EXPO_PUBLIC_API_BASE_URL` + `PUBLIC_BASE_URL`.  
7. Rebuild native binary for lock-screen audio.

## How to run

See **[DEV.md](./DEV.md)** — copy-paste runbook.
