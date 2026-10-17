# Shipped status — CrackNews

Living record of what is **actually built and working** as of **2026-10-17**.  
Specs that still describe aspirational UX are called out under **Deferred**.

Brand: **CrackNews** (Expo app name; package `ca.cracknews.app`).

---

## Stack (as implemented)

| Layer | Choice |
| --- | --- |
| Ingest | Python `realtime_ingestion/` — RSS, Ollama briefs, GPU-gated Kokoro → Opus/m4a, publish |
| Content store | MongoDB (`stories`, `threads`, `compares`, `display_ads`) |
| Users | PostgreSQL (`users`, `user_preferences`) |
| Audio files | Local `wwwroot/media` (dev) / S3-compatible (prod path) |
| API | .NET 10 `backend/CNews.Api` — Kestrel LAN + Lambda-ready hosting |
| Mobile | Expo SDK 57, Expo Router, Zustand, TanStack Query, expo-sqlite, expo-audio, Reanimated |
| Theme | System light/dark; Atlantic blue + graphite (custom, not HeroUI) |

---

## Delivered by area

### Ingest & publish

- Continuous RSS poll with topic catalog and dedupe.
- Briefs via Ollama `llama3.1:8b` with extractive fallback.
- GPU rest gate before Kokoro TTS; Opus via ffmpeg when available (WAV/m4a fallbacks).
- Publish to Mongo (`stories`, `threads`/`storylines`, `compares`) with audio keys/status.
- Demo seed: `scripts/seed_demo_mongo.py`, `scripts/seed_demo_ads.py`, Kokoro / demo brief generators.
- Ops HTML reader on `:8765` for pipeline debugging only.

### Backend API (`/v1`)

| Endpoint | Status |
| --- | --- |
| `GET /v1/health` | Done |
| `GET /v1/ads/display` | Done — first-party display ads; `slot=home_wall` or `storylines_list` (not in the news feed) |
| `GET /v1/home/feed` | Done — topics, cursor, `newerThan`; mobile always uses `mode=listen` |
| `GET /v1/stories/{id}` | Done |
| `GET /v1/stories/{id}/audio-url` | Done — signed / local media URL |
| `GET /v1/coverage/{clusterId}` | Done (API); **not wired in mobile UI** |
| `GET /v1/storylines` | Done — **cursor pagination** on `updatedAt` + `threadId` |
| `GET /v1/storylines/{id}` | Done — updates with outlet, brief, `sourceUrl`, cover, audio |
| `GET /v1/meta/topics` | Done |
| `POST /v1/auth/google` | Done — real verify + `dev:email` bypass |
| `GET /v1/me`, `PUT /v1/me/topics` | Done |

Guest browse of feed/storylines without JWT is allowed.

### Mobile — Home

- Staggered two-column masonry wall (aligned tops, full-bleed photo cards).
- Display ads mix in as **masonry cards** (labeled Ad); tap opens the advertiser in-app. **Not** in Play. No banners, interstitials, or audio ads.
- Tap a **story** card → **in-tab** full-screen vertical reader above the tab bar (not a root modal).
- Reader: image, title, summary, **in-app WebView** for Original.
- Opening Original **pauses** Play; closing Original **resumes**.
- Opening a card does **not** auto-start audio — only the center Play button does.
- Center Play: **stories only**, left→right then top→bottom; highlight while speaking; auto-advance. Ads are skipped.
- Pull-to-refresh while listening: **current brief keeps playing**; remaining queue is rebound to the new wall order.
- Scroll down → `loadMore` via feed cursor.
- Pull-to-refresh → fresh first page, **shuffled** order (“fresh mix”), pagination reset. Ads re-roll (sometimes none).
- Feed is **not** geo-located. Topics (including `Local`) are desks, not the user’s city.
- System dark mode; typographic **C** icon + black splash.
- Tabs: **Home · Storylines · Play · Settings · Login**.

### Mobile — Storylines

- List with Ongoing / Closed / All filters.
- Display ads may appear as full-width storyline-style cards (labeled Ad); tap opens the advertiser. Not in Play or the timeline.
- Cursor page size 10; scroll down loads more; pull-to-refresh reshuffles.
- In-tab storyline reader: hero + **outlet timeline**.
- Timeline: real **clock timestamps**, icon nodes, continuous spine **from first node center to last** (no dangling stem past the last item), cards kept (thumb / title / summary / Original).
- Play on Storylines uses that surface’s queue (list briefs or current thread updates).
- Opening Original pauses; back to timeline resumes.
- Leaving the Storylines surface **stops** playback (page-scoped Play).

### Mobile — Play (global rules)

- Play is **scoped to the focused page**: Home wall vs Storylines.
- Switching tabs / leaving a play surface **stops** audio (no cross-page resume of the wrong queue).
- Pause/resume only if the active `playerStore.context` matches the current surface.
- **Background / lock-screen playback** (Spotify-style): `shouldPlayInBackground`, lock-screen metadata, `expo-audio` `enableBackgroundPlayback` — requires a **native rebuild** (not Expo Go alone).
- Long-press Play → hard stop.

### Mobile — Settings / Login

- Topic toggles only (no listening-mode radios, no About).
- Home is always voice-ready (`GET /v1/home/feed?mode=listen`). Play still skips any card without audio.
- Google Sign-In stub → `dev:` JWT; topics sync via `/v1/me/topics`.

### Multi-outlet “compare”

- Backend + seed support `clusterId` + `GET /v1/coverage/{clusterId}`.
- Home shows separate cards per outlet; clustered cards may show **· Sources**.
- **No horizontal compare pager in the app** — deferred by product choice (keep as-is).

---

## Key mobile modules

| Path | Role |
| --- | --- |
| `mobile/src/features/home/HomeScreen.tsx` | Wall, refresh, load more, ad click-out |
| `mobile/src/features/home/MasonryWall.tsx` | Masonry + near-end + visible Play order (stories only) |
| `mobile/src/features/home/AdCard.tsx` | Home display ad card |
| `mobile/src/features/home/mixDisplayAds.ts` | Insert 0–1 display ad into Home / Storylines lists |
| `mobile/src/features/reader/StoryReaderScreen.tsx` | Vertical feed pager |
| `mobile/src/features/reader/ReaderPage.tsx` | Summary + Original WebView (pause/resume) |
| `mobile/src/features/storylines/StorylinesScreen.tsx` | List + pagination + display ads |
| `mobile/src/features/storylines/StorylineAdCard.tsx` | Full-width storyline-style ad card |
| `mobile/src/features/storylines/StorylineReaderScreen.tsx` | Outlet timeline + Original pause/resume |
| `mobile/src/features/player/PlayTabButton.tsx` | Surface-aware Play |
| `mobile/src/data/stores/playerStore.ts` | Queue, expo-audio, lock screen |
| `mobile/src/data/stores/playSurfaceStore.ts` | `home` \| `storylines` ownership |
| `mobile/src/shared/hooks/useFeed.ts` | Home cursor + shuffle refresh |
| `mobile/src/shared/hooks/useStorylines.ts` | Storylines cursor + shuffle refresh |

---

## Deferred (explicit)

| Item | Notes |
| --- | --- |
| F7 Coverage horizontal swipe | API ready; UI not built — **keep deferred** |
| Real Google OAuth clients | Dev uses `dev:email` |
| Lambda `dev` / ECR deploy | Local Kestrel first |
| Push notifications | Out of scope |
| Outlet subscriptions + ranking ML | See [upgrade-plan.md](./upgrade-plan.md) |
| GPS / city Play (e.g. Calgary) | Stories have a `place` label; feed is **not** filtered by device location |
| Audio mid-roll ads / AdMob | Display cards only for now |

---

## Decision log (product, recent)

| Date | Decision |
| --- | --- |
| 2026-10-10 | App brand = **CrackNews** |
| 2026-10-10 | Reader stays above tab bar (in-tab routes) |
| 2026-10-10 | Original opens in-app WebView; pause Play, resume on close |
| 2026-10-10 | No auto-play on card open — Play button only |
| 2026-10-10 | Play stops when leaving Home / Storylines / Settings / Login / reader |
| 2026-10-10 | Storyline timeline = timestamp + line + icon nodes + cards |
| 2026-10-10 | Pull-up refresh = reshuffle fresh page (Home + Storylines) |
| 2026-10-10 | Multi-outlet compare UI deferred; separate Home cards OK |
| 2026-10-10 | Background lock-screen audio enabled (needs native rebuild) |
| 2026-10-17 | Display ads: story-like cards on Home + Storylines list; not in Play |
| 2026-10-17 | Voice-first: Home always `mode=listen`; Settings topics only |
| 2026-10-17 | Pull-to-refresh while Play: keep current brief, rebind remaining queue |
