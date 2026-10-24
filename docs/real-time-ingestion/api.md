# Mobile API contract

Versioned HTTP API served by the .NET backend. Base path: `/v1`.

All timestamps are ISO-8601 UTC. All successful responses are JSON. Errors use a small envelope.

## Error envelope

```json
{
  "error": {
    "code": "not_found",
    "message": "Story not found"
  }
}
```

| HTTP | `code` examples |
| --- | --- |
| 400 | `bad_request`, `invalid_topic` |
| 401 | `unauthorized` |
| 404 | `not_found` |
| 429 | `rate_limited` |
| 500 | `server_error` |

## Shared types

### `StoryCard`

```json
{
  "storyId": "01J…",
  "title": "Headline",
  "summary": "Brief…",
  "summaryPreview": "Brief truncated for text-only cards…",
  "imageUrl": "https://… or null",
  "imageAspect": 0.75,
  "outlet": "CBC",
  "topic": "Canada",
  "place": "Manitoba",
  "publishedAt": "2026-10-10T15:00:00Z",
  "sourceUrl": "https://…",
  "audioStatus": "ready",
  "audioUrl": "https://signed…",
  "audioDurationMs": 18240,
  "clusterId": "01J…",
  "threadId": null
}
```

- `imageUrl` null → client renders the text-only masonry card (title + `summaryPreview` + ellipsis).
- `imageAspect` optional hint so columns can stagger without waiting on image load.
- `audioUrl` only when `audioStatus === "ready"`. Refresh via detail or `/audio-url` on 403.

### Topics query

```text
?topics=Canada,Local,Politics
```

Omit or empty → use stored user prefs if `Authorization` present, else server default (`Top,Canada,Local`). Unknown tokens → `400 invalid_topic`.

---

## Display ads (Home wall)

Separate from news and from audio ads. Not mixed into `/v1/home/feed`.

### `GET /v1/ads/display`

```text
?slot=home_wall|storylines_list&limit=6
```

**200**

```json
{
  "items": [
    {
      "adId": "display_demo_1",
      "advertiser": "VIA Rail",
      "title": "Weekend trains from $49 — see Canada by rail",
      "clickUrl": "https://www.viarail.ca/",
      "imageUrl": "http://10.0.0.100:5080/media/ads/display/ad_demo_1.jpg",
      "imageAspect": 0.74
    }
  ]
}
```

The client may insert 0–1 of these as story-like cards: Home masonry (`home_wall`) or Storylines list (`storylines_list`). Play queues ignore them. No timeline or audio ads.

## Search

Lookup over published briefs. Not a recommender. Guest-accessible. Ads are not mixed in.

### `GET /v1/search`

```text
?q=calgary&mode=listen&limit=20
```

| Query | Default | Notes |
| --- | --- | --- |
| `q` | — | Case-insensitive match on title, summary, outlet, topic, place (and storyline title/updates). Shorter than 2 characters → empty lists. |
| `mode` | `listen` | `listen` = voice-ready stories only |
| `limit` | `20` | max 40 stories; storylines capped at 8 |

**200**

```json
{
  "stories": [ /* StoryCard */ ],
  "storylines": [ /* storyline summaries */ ],
  "serverTime": "2026-10-17T21:00:00Z"
}
```

## Auth (Google → PostgreSQL)

### `POST /v1/auth/google`

Body:

```json
{
  "idToken": "google-id-token"
}
```

**200**

```json
{
  "accessToken": "jwt…",
  "expiresAt": "2026-10-11T15:00:00Z",
  "user": {
    "userId": "01J…",
    "email": "user@gmail.com",
    "displayName": "Alex",
    "avatarUrl": "https://…",
    "topics": ["Top", "Canada", "Local"]
  }
}
```

Backend verifies the Google token, upserts PostgreSQL `users`, returns an app JWT.

### `GET /v1/me`

Requires `Authorization: Bearer …`.

**200** — same `user` object as above.

### `PUT /v1/me/topics`

```json
{ "topics": ["Canada", "Politics"] }
```

Persists to PostgreSQL; mobile also mirrors into SQLite.

### `POST /v1/auth/logout`

Invalidate refresh/session server-side if used; client drops JWT.

---

## Home (masonry feed)

### `GET /v1/home/feed`

Primary endpoint for the RedNote-style wall.

| Query | Default | Notes |
| --- | --- | --- |
| `topics` | prefs / default | Comma-separated |
| `limit` | `20` | max 40 |
| `cursor` | — | Opaque; omit for newest page |
| `newerThan` | — | ISO time; used when user pulls at top for **new** items |
| `mode` | `any` | `listen` = voice-ready stories only. CrackNews always sends `listen`. |

**200**

```json
{
  "items": [ /* StoryCard */ ],
  "nextCursor": "…",
  "serverTime": "2026-10-10T15:00:00Z"
}
```

Client upserts `items` into SQLite. The Expo app always requests `mode=listen`. Pull-to-refresh fetches a fresh first page and shuffles locally (not a `newerThan` merge).

### `GET /v1/home/random` (optional helper)

Kept for tooling / demos; Home UI does **not** depend on a single hero card.

---

## Stories

### `GET /v1/stories/{storyId}`

**200**

```json
{
  "story": { /* StoryCard */ },
  "compareClusterId": "01J…",
  "threadId": "01J…"
}
```

`compareClusterId` / `threadId` are available for Storylines links. Coverage swipe UI is **deferred** — Home still shows separate cards per outlet.

### `GET /v1/stories/{storyId}/audio-url`

**200** `{ "audioUrl": "https://…", "expiresAt": "…" }`

---

## Coverage (for Home full-screen pager — not a tab)

There is **no** mobile Coverage tab. The client loads cluster detail when opening a story that has `clusterId` / `compareClusterId`.

### `GET /v1/coverage/{clusterId}`

**200** — event title + `outlets[]` with `framing`, `summary`, `audioStatus`, `audioUrl`, `outlet`, `storyId`, `imageUrl`.

API is ready for a horizontal full-screen pager; that UI is **not** in the app. Seeded clusters still appear as separate Home cards.

### `GET /v1/coverage` (optional)

List endpoint is **optional / admin / future**. The v1 app does not need a coverage index screen.

Aliases: `/v1/compares/{id}` may remain as synonyms during migration.

---

## Storylines (formerly threads)

### `GET /v1/storylines`

| Query | Default |
| --- | --- |
| `status` | `open` (`open` \| `closed` \| `all`) — map to Ongoing / Closed in UI |
| `topics` | optional |
| `limit` | `20` |
| `cursor` | opaque |

**200** — `{ threadId, title, status, updatedAt, updateCount, topic, place }`.

### `GET /v1/storylines/{threadId}`

**200** — full storyline with ordered `updates[]` (newest first in API or sorted by client).

Aliases: `/v1/threads` deprecated synonyms OK during migration.

---

## Meta

### `GET /v1/meta/topics`

**200** `{ "topics": [ { "id": "Canada", "label": "Canada" } ] }`

### `GET /v1/health`

**200** `{ "status": "ok" }`

### `GET /v1/health/ingest`

For an uptime monitor. Reads the heartbeat the ingest box writes to Mongo `ingest_status` every minute.

**200** `{ "status": "ok", "problem": null, "lastSeenAt": "…", "lastBriefAt": "…", "backlog": 0, "host": "…", "ttsStatus": "…" }`

**503** same shape, `status: "down"`, `problem` one of: `ingest has never checked in`, `ingest box stopped checking in` (no heartbeat for `INGEST_STALE_MINUTES`, default 15), `ingest is up but no new briefs` (none for `INGEST_BRIEF_STALE_MINUTES`, default 180).

---

## Headers

| Header | Use |
| --- | --- |
| `Authorization: Bearer …` | Logged-in user |
| `X-Device-Id` | Optional guest analytics / cache hints |

## Pagination

Opaque cursors. Home and Storylines pull-to-refresh reset to a shuffled first page (client-side). `newerThan` remains available for a future “new items only” merge.
