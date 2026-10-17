# CNews Mobile

React Native (**Expo SDK 57**) client for [CNews](../docs/real-time-ingestion/mobile.md). Immersive RedNote-style home wall, in-tab reader, center **Play** for visible **stories**, **Storylines**, first-party display ads, and **Settings** (Google sign-in stub + topic toggles). Coverage swipe is deferred.

Talks to the .NET API in `backend/` via `EXPO_PUBLIC_API_BASE_URL`. When the API is unreachable, seeded mock stories keep the UI usable offline.

## Requirements

- Node.js 20+ (tested on **Node 24**)
- [Expo Go](https://expo.dev/go) on a device, or iOS Simulator / Android emulator

## Quick start

```bash
cd mobile
npm install
npx expo start
```

Scan the QR code with Expo Go, or press `i` / `a` for simulators.

### API base URL

Default: `http://127.0.0.1:5080` (Simulator / same machine).

On a **physical phone**, use your machine’s LAN IP — not `localhost`:

```bash
EXPO_PUBLIC_API_BASE_URL=http://192.168.x.x:5080 npx expo start
```

Optional `.env` (Expo loads `EXPO_PUBLIC_*` at build time):

```bash
EXPO_PUBLIC_API_BASE_URL=http://127.0.0.1:5080
```

Start the backend first ([local development](../docs/real-time-ingestion/local-development.md)).

## UX map

| Tab | Role |
| --- | --- |
| **Home** | Staggered two-column masonry, no app-name header; tap story → in-tab reader; ads open the advertiser |
| **▶ Play** (center) | Speaks the current page (Home wall, Search hits, or Storylines) |
| **Search** | Lookup briefs + storylines; Play speaks matching stories |
| **Storylines** | Ongoing / Closed lists (ads may appear); detail timeline newest-first |
| **Settings** | Topic toggles only (Home is always voice-ready) |

Coverage is **not** a tab — clustered stories appear as separate Home cards. The coverage API exists; the swipe pager is deferred.

## Project layout

```text
mobile/
  app/                    # Expo Router (tabs + story modals)
  src/
    features/             # home, reader, storylines, settings, player
    shared/               # theme, components, hooks, utils
    data/
      api/                # /v1 HTTP client + mock fallback
      db/                 # expo-sqlite feed cache
      stores/             # Zustand (auth, player, feed UI, settings)
      seed/               # offline mock data
      types/
```

## Stack

- **Expo Router** — tabs + full-screen story modal
- **Zustand** — player queue, visible cards, auth/settings
- **TanStack Query** — feed / story / storylines fetching
- **expo-sqlite** — cached masonry cards
- **Custom theme** — Atlantic blue + graphite; system light/dark (not HeroUI)
- **expo-audio** — Opus/HTTP audio playback

## API endpoints used

See [api.md](../docs/real-time-ingestion/api.md):

- `GET /v1/home/feed?mode=listen`
- `GET /v1/search?q=&mode=listen`
- `GET /v1/ads/display?slot=home_wall|storylines_list`
- `GET /v1/stories/:id`, `GET /v1/stories/:id/audio-url`
- `GET /v1/storylines`, `GET /v1/storylines/:id`
- `GET /v1/meta/topics`
- `POST /v1/auth/google`, `PUT /v1/me/topics`

## Scripts

| Command | Description |
| --- | --- |
| `npm start` | Expo dev server |
| `npm run ios` | Open iOS |
| `npm run android` | Open Android |
| `npm run web` | Web (limited; mobile-first UI) |

## Notes

- **Google Sign-In** is a stub (`Continue with Google` → mock JWT) until OAuth client IDs are configured.
- Mock feed is written to SQLite on first launch so the wall paints without network.
- Audio requires `audioStatus: ready` and a valid signed URL from the API; mock cards may show “No voice on these cards yet” until backend audio exists.

## Related docs

- [Mobile UX](../docs/real-time-ingestion/mobile.md)
- [HTTP API](../docs/real-time-ingestion/api.md)
- [Features](../docs/real-time-ingestion/features.md)
