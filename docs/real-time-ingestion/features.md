# Features

Product features for the real-time ingestion system and the mobile experience it powers. Each feature lists the user-visible outcome and what “done” means.

## F1 — Continuous Canadian feed ingest

**Outcome.** New RSS stories from the catalog appear in the pipeline within one poll interval of the feed.

**Details.**

- National desks poll about every 2–5 minutes; city/regional about every 10 minutes.
- Deduplicate by URL per feed; link the same URL across feeds without re-summarizing.
- Cap new articles per poll so the local model does not fall behind.
- Topics: `Top`, `Canada`, `Local`, `World`, `Politics`, `Business`, `Health`, `Arts`, `Technology`, `Sports`.
- Places: province or city labels on each Local story (not GPS). Catalog covers major CMAs plus provincial desks so smaller cities still get nearby news.
- English-only RSS: Kokoro has no French voice (no Radio-Canada / La Presse / TVA / Journal). Montreal still has CBC, Global, and CityNews in English.

**Done when.** A new CBC/Global headline shows a stored article row (working store) after the next eligible poll, without duplicate briefs for the same URL.

## F2 — Short human briefs (Ollama 8B)

**Outcome.** Each story gets about 50 plain words a person can read or hear in under 30 seconds.

**Details.**

- Default model: Ollama `llama3.1:8b` (pull required on the GPU host).
- Fallback: extractive cut from article text if Ollama fails or reply is too short.
- Persist engine used (`ollama` vs `extractive`) for quality review.

**Done when.** Home cards show a brief for every published story; empty briefs never reach the mobile API.

## F3 — GPU-gated spoken briefs (Kokoro → Opus)

**Outcome.** When speech is enabled, the user can play a natural voice reading of the brief.

**Details.**

- Summary always completes before TTS starts.
- Kokoro runs only when the GPU is at rest (see [pipeline.md](./pipeline.md)).
- Output format for mobile: **Opus** (small, stream-friendly).
- Upload Opus to S3; MongoDB stores `audioKey` and `audioStatus`.

**Done when.** A published story with `audioStatus = ready` plays in Expo Go over a signed URL without downloading the whole catalog.

## F4 — Publish gate (MongoDB + S3)

**Outcome.** The app never sees a half-published listen experience when audio was promised.

**Rules (summary).**

1. Generate brief first.
2. If GPU rests, generate Opus.
3. Push summary to MongoDB.
4. Upload Opus to S3.
5. Mark the document fully ready when required media is present.

Text-first publish is allowed when audio is disabled or still pending; the API must expose clear audio state. Full rules: [pipeline.md](./pipeline.md).

**Done when.** API list/detail endpoints only return documents that passed the publish gate for the requested mode (`text` or `listen`).

## F5 — Home: immersive wall + full-screen reader

**Outcome.** Browse a light RedNote-style wall; tap into an immersive full-screen story.

**Status.** **Shipped** (CrackNews Expo).

**Details.**

- Wall: staggered two-column masonry — **not** a rigid grid. **No** top app-name bar.
- Image card: full-bleed image + title; tap → **in-tab** full-screen reader (above tab bar).
- Display ads may mix in as labeled masonry cards (0–1 per page); tap opens the advertiser. Ads are not in Play.
- Reader: image, title, summary, in-app **Original** WebView (Play pauses / resumes).
- Scroll down loads more (cursor); pull at top → **fresh shuffled** first page (ads re-roll).
- Always voice-ready feed (`mode=listen`). Topic-filtered; not geo-located. SQLite/cache + remote sync.

**Done when.** Cold open paints the wall immersively; tap/back round-trips to full-screen cleanly.

## F5b — Center Play queue

**Outcome.** Center navbar Play speaks stories for the **focused page** (Home wall or Storylines).

**Status.** **Shipped** (page-scoped; stops on tab leave; lock-screen ready with native rebuild).

**Details.**

- Home: **stories only**, left→right then top→bottom among visible masonry cards; skip ads and non-ready audio.
- Pull-to-refresh while playing keeps the current brief and rebinds the remaining queue to the new wall order.
- Storylines: list briefs or current thread updates (ads in the list are skipped).
- Soft highlight / Listening on the speaking card or timeline row.
- No auto-play on card open.

**Done when.** From a populated Home wall, Play audibly walks visible ready cards; switching tabs stops audio.

## F6b — Search

**Outcome.** The user can type a city, outlet, or headline word and get matching briefs (and storylines). Play speaks those hits.

**Status.** **Shipped.**

**Details.**

- `GET /v1/search?q=&mode=listen` plus on-device cache. Not a recommender. No ads.
- Tabs: Home · Storylines · Play · Search · Settings (Login hidden).

**Done when.** Searching a seeded place or outlet returns cards; Play reads the result list.

## F6 — Topic preferences in Settings

**Outcome.** The user controls which desks fill Home and lists.

**Details.**

- Multi-select topic toggles matching the ingest catalog. **No** listening-mode radios.
- Home is always `mode=listen`; Play still skips cards without audio.
- Defaults: `Top`, `Canada`, `Local` on; others off (tunable).
- Mirrored in on-device SQLite; synced to **PostgreSQL** when signed in with Google.
- Changing topics triggers a Home feed sync.

**Done when.** Turning off `Sports` means no sports cards appear on Home until turned back on.

## F7 — Coverage merged into Home full-screen

**Outcome.** Multi-outlet framing is experienced inside the Home reader — not a separate tab.

**Status.** **Deferred** (product choice). API `GET /v1/coverage/{clusterId}` + seed clusters exist; Home shows **separate cards** per outlet with optional · Sources. No horizontal compare pager.

**Details (when revisited).**

- No Coverage tab. Quiet sources cue on wall cards.
- Open a clustered story → full-screen **horizontal pager**: framing + brief + play per outlet.
- Driven by `cluster_id` + framing; API already exposes coverage.

**Done when.** Opening a multi-outlet card lets the user swipe between publishers in full-screen.

## F8 — Storylines (same situation over time)

**Outcome.** The user can follow an unfolding story as a polished timeline.

**Status.** **Shipped.**

**Details.**

- Tab: **Storylines** — Ongoing / Closed / All; cursor pagination + shuffle refresh.
- Display ads may appear as full-width storyline-style cards (labeled Ad); not in Play or the timeline.
- Detail: hero + outlet timeline (clock stamp, connected icon spine, summary cards, Original).
- Play scoped to list or open thread; Original pause/resume.
- Pipeline decisions remain `IGNORE` / `OPEN` / `UPDATE`.

**Done when.** At least one multi-update storyline is browsable with clear Ongoing/Closed state.

## F9 — Backend for mobile (.NET on Lambda)

**Outcome.** A stable HTTP API the Expo app can call from a phone on the same Wi‑Fi (dev) or over the internet (prod).

**Details.**

- ASP.NET Core (.NET 10) packaged as a Lambda container image.
- Local simulation via Docker + Lambda RIE (and Kestrel for Expo).
- Reads MongoDB (content); reads/writes PostgreSQL (users); signs S3 audio URLs.
- Google token verification for login.
- No ingest or GPU work inside Lambda.

**Done when.** Expo Go on a physical phone can load Home against the local Dockerized API (or a deployed stage URL).

## F10 — Human-friendly mobile UX

**Outcome.** Immersive RedNote-like wall, full-screen reader, center Play, Search, Storylines timeline; tabs: Home · Storylines · Play · Search · Settings.

**Status.** **Shipped** (coverage swipe excluded — see F7).

**Non-goals for v1.**

- Multi-outlet compare pager (deferred).
- Social feed, comments, likes, or push spam.
- Rigid grids or app-name top bar on Home.

Guidance: [mobile.md](./mobile.md) · [SHIPPED.md](./SHIPPED.md).

**Done when.** A new user understands wall → reader → Original, Play, and Storylines without long onboarding.

## F11 — Local simulation with Docker

**Outcome.** A developer can run MongoDB, PostgreSQL, S3-compatible storage, Redis, and the Lambda API without a full AWS account on day one.

**Details.**

- Compose services for MongoDB, PostgreSQL, MinIO (S3 API), Redis, backend.
- Ollama + Kokoro stay on the host (GPU / model size).
- Documented in [local-development.md](./local-development.md).

**Done when.** `docker compose up` plus host Ollama yields a published story visible through the API.

## F12 — Google login + PostgreSQL users

**Outcome.** Users can sign in with Google; identity and topic preferences persist in PostgreSQL and sync to the device.

**Details.**

- Guest browse allowed; login unlocks cross-device prefs.
- Backend verifies Google ID token; upserts `users` / `user_preferences`.
- Mobile device SQLite mirrors prefs for offline Settings.

**Done when.** Sign-in with Google on Expo Go creates a Postgres row and restores topics on a second device/session.

## Out of scope (for now)

- Push notifications and breaking-news alerts.
- Personalized ranking / outlet subscribe — **planned**, see [upgrade-plan.md](./upgrade-plan.md).
- GPS / city Play (stories may have a `place` label; the feed is not filtered by device location).
- Audio mid-roll ads / AdMob (display cards only).
- Multi-language briefs.
- Apple / email password login (Google first).
- Moderating or rewriting outlet framing beyond existing comparison notes.
- Horizontal coverage compare UI (F7 deferred).
