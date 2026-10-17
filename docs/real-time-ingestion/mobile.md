# Mobile app — CrackNews

Client for published briefs. Root: `mobile/` (Expo SDK 57).  
**Shipped behavior:** [SHIPPED.md](./SHIPPED.md) · **Dev runbook:** [DEV.md](./DEV.md) · **Future prefs/recs:** [upgrade-plan.md](./upgrade-plan.md)

## Product feeling

A **lightweight, immersive discovery feed** you can skim like RedNote (小红书), with one-tap listening from the center Play control — not a dense newspaper, not a social network.

- Home: **staggered two-column** photo wall. No top app-name bar.
- Display ads mix in as labeled cards on Home and Storylines (0–1 per page); tap opens the advertiser. **Not** in Play.
- Tap a **story** card → **in-tab full-screen** reader (above the tab bar).
- **Original** opens an in-app WebView; Play **pauses**, resumes when you leave Original.
- Play is **page-scoped** (Home vs Storylines); leaving a page **stops** audio.
- **Storylines** tab: timelines with timestamp + line + icon nodes + cards.
- Multi-outlet **compare swipe is deferred** — clustered stories still appear as separate Home cards (optional · Sources cue).

## Tech stack (as built)

| Layer | Choice |
| --- | --- |
| Framework | React Native via **Expo 57** (Expo Router) |
| UI | Custom theme (Atlantic blue + graphite, system light/dark); Reanimated |
| Client state | **Zustand** (`playerStore`, `playSurfaceStore`, `feedUiStore`, `authStore`, …) |
| Server cache | TanStack Query + **SQLite** / AsyncStorage feed cache |
| Audio | **expo-audio** — Opus/m4a briefs; background + lock-screen metadata |
| Accounts | Google Sign-In stub → JWT (`dev:` in Development) |

## Information architecture

```text
┌──────┬────────────┬──────────┬────────┬──────────┐
│ Home │ Storylines │  ▶ Play  │ Search │ Settings │
└──────┴────────────┴──────────┴────────┴──────────┘
```

| Slot | Job |
| --- | --- |
| Home | Masonry wall + vertical full-screen reader |
| Storylines | Ongoing / Closed / All + outlet timeline reader |
| Play | Speaks the **current page’s** queue (not a destination tab) |
| Search | Lookup briefs + storylines; Play speaks matching stories |
| Settings | Topic toggles only (Home is always voice-ready) |

Deep links (later): `cnews://story/{id}`, `cnews://storyline/{threadId}`.

---

## Play control

### Surfaces

| Focused screen | Queue |
| --- | --- |
| Home wall | Visible **story** cards, left→right then top→bottom (ads skipped) |
| Search | Matching stories in list order (ads skipped) |
| Storylines list | Up to ~8 open threads’ outlet briefs |
| Storyline detail | That thread’s updates in order |

### Rules (shipped)

1. Opening a card **never** starts audio — only Play.
2. Pause/resume only if `playerStore.context` matches the current surface; otherwise start that page’s queue.
3. Blur of Home / Storylines / Settings / Login / story reader → **`stop()`**.
4. Original WebView → **pause**; close → **resume** if it was playing.
5. Pull-to-refresh on Home while playing: **keep the current brief**; rebind the remaining queue to the new wall order.
6. Background / lock screen: continues when the phone sleeps **if** a native build has `enableBackgroundPlayback` (see [DEV.md](./DEV.md)).
7. Long-press Play → hard stop.

### Visual feedback

- ▶ / ❚❚ on the center control; quiet `1/N` progress.
- Soft highlight / “Listening” on the speaking wall card or timeline row.

---

## 1. Home

### Wall

- Staggered masonry; full-bleed image + title overlay.
- Display ads (labeled Ad) may occupy one masonry slot; tap opens the advertiser in-app.
- Home always requests `GET /v1/home/feed?mode=listen`. Feed is **not** geo-located.
- Scroll **down** → cursor `loadMore`.
- Pull **up** → fresh first page, **shuffled** (“Updated · fresh mix”), reset cursor; ads re-roll (sometimes none).
- Optional · Sources when `clusterId` is set (no compare pager).

### Full-screen reader

- Vertical pager through the **feed** (same stories as the wall).
- Layout: image · outlet · title · summary · Original (WebView).
- Tab bar remains visible (in-tab route).

### Multi-outlet (deferred)

API `GET /v1/coverage/{clusterId}` exists. Horizontal outlet swipe is **not** in the app. Keep separate cards on the wall.

---

## 2. Storylines

### List

- Filters: Ongoing | Closed | All.
- Page size 10; scroll down loads more; pull-to-refresh reshuffles.
- Display ads may appear as full-width storyline-style cards (labeled Ad).
- Card: cover, title, status, update count, latest outlet whisper.

### Detail — outlet timeline

```text
  ●  10:57 AM
  │  Missouri / Global
  │  ┌─────────────────┐
  │  │ thumb · title   │
  │  │ summary         │
  │  │ Original · host │
  │  └─────────────────┘
  │
  ●  12:57 PM
     CBC
     ┌─────────────────┐
     │ …               │
     └─────────────────┘
```

- Real **clock** stamps (`2:15 PM` or `Mar 9, 2:15 PM`).
- Continuous spine from **first node center → last node center** (no dangling line past the last update).
- Cards stay; Original pause/resume same as Home.

---

## 3. Search

- Debounced `GET /v1/search?q=&mode=listen` plus on-device cache.
- Matches title, summary, outlet, topic, place (and storyline titles).
- No ads. Guest. Not a recommender.
- Play on this tab speaks the story hits; storyline rows open the timeline.

---

## 4. Settings + Login

- Topics from `/v1/meta/topics` (on-device). Login tab is hidden.
- No listening-mode radios and no About — Home is always voice-ready.
- Future outlet subscribe + For You ranking: [upgrade-plan.md](./upgrade-plan.md) (not in progress).

---

## Visual direction

| Do | Don’t |
| --- | --- |
| Immersive wall, no brand header | Newspaper chrome on Home |
| Staggered masonry | Rigid equal grid |
| In-tab reader above tabs | Modal that hides the tab bar |
| Page-scoped Play | Cross-tab audio from the wrong queue |
| Timeline stamps + connected nodes | Broken stems that miss the next icon |

Motion: wall/list enter fades; speaking highlight; timeline row enter.

---

## Acceptance walkthrough (current)

1. Home wall paints staggered cards; pull refreshes a fresh mix; scroll loads more. Ads (if any) look like cards and open the advertiser.  
2. Tap a story → in-tab reader; Original WebView; Play pauses/resumes around Original.  
3. Center Play on Home speaks visible **stories** left→right; ads skipped; leaving Home stops audio.  
4. Storylines paginate (ads may appear in the list); timeline shows stamps + connected icons + cards.  
5. Play on a storyline speaks that thread; Original pause/resume works.  
6. Search finds a seeded story (e.g. Calgary / CBC); Play speaks those hits.  
7. Settings topics filter the wall.  
8. (Dev client) Lock screen shows CrackNews brief metadata while playing.  
