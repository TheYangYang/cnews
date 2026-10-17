# Data model

Contracts for published content (MongoDB), users (PostgreSQL), media (S3), and the on-device SQLite cache. Field names use camelCase in API JSON.

## Identifiers

| Id | Meaning |
| --- | --- |
| `storyId` | Stable id for one outlet report (maps from today’s article row id / UUID) |
| `clusterId` | Shared event across outlets (coverage API exists; Home swipe UI deferred) |
| `threadId` | Unfolding situation → **Storyline** in the app |
| `userId` | App user (PostgreSQL) |
| `audioKey` | S3 object key for Opus |

## Store split

| Store | Owns |
| --- | --- |
| MongoDB | Stories, coverage clusters, storylines, display ads |
| PostgreSQL | Users, Google subject, topic preferences |
| S3 | Opus audio bytes |
| Device SQLite | Cached feed cards, local prefs mirror, read/play cursors |

## MongoDB collections

### `stories`

One document per outlet report that passed text publish.

```json
{
  "storyId": "01J…",
  "clusterId": "01J…",
  "threadId": null,
  "title": "Headline",
  "summary": "About fifty plain words…",
  "summaryWords": 48,
  "summaryEngine": "ollama",
  "imageUrl": "https://…",
  "imageAspect": 0.8,
  "outlet": "CBC",
  "topic": "Canada",
  "place": "Manitoba",
  "sourceUrl": "https://…",
  "publishedAt": "2026-10-10T15:00:00Z",
  "ingestedAt": "2026-10-10T15:01:10Z",
  "audioStatus": "ready",
  "audioKey": "audio/opus/2026/10/10/01J….opus",
  "audioContentType": "audio/opus",
  "audioDurationMs": 18240,
  "listenReady": true,
  "textReady": true
}
```

`imageUrl` may be null when RSS/HTML had no usable image — mobile then uses the text-only card.

| `audioStatus` | Meaning |
| --- | --- |
| `pending` | Brief published; Opus not yet |
| `ready` | Opus in S3; safe for listen Home |
| `unavailable` | TTS disabled or permanently skipped |
| `failed` | TTS/upload failed; may retry |

**Indexes (suggested).**

- `{ topic: 1, publishedAt: -1 }`
- `{ listenReady: 1, topic: 1, publishedAt: -1 }`
- `{ clusterId: 1 }`
- `{ threadId: 1, publishedAt: 1 }`
- unique `{ storyId: 1 }`

### `compares` (Coverage)

One document per multi-outlet cluster used by the Home **full-screen coverage pager**.

```json
{
  "clusterId": "01J…",
  "title": "Shared event label or best headline",
  "topics": ["Canada", "Politics"],
  "updatedAt": "2026-10-10T15:05:00Z",
  "outlets": [
    {
      "storyId": "01J…",
      "outlet": "CBC",
      "framing": "Led with the provincial angle.",
      "summary": "…",
      "audioStatus": "ready",
      "audioKey": "audio/opus/…/….opus"
    },
    {
      "storyId": "01J…",
      "outlet": "Global",
      "framing": "Led with the federal response.",
      "summary": "…",
      "audioStatus": "pending",
      "audioKey": null
    }
  ]
}
```

Only clusters with **≥ 2** outlets and framing text for each are returned for the coverage pager.

### `threads` (Storylines)

```json
{
  "threadId": "01J…",
  "title": "Short situation title",
  "status": "open",
  "topic": "Canada",
  "place": "Winnipeg",
  "openedAt": "2026-10-09T12:00:00Z",
  "closedAt": null,
  "updatedAt": "2026-10-10T15:10:00Z",
  "updates": [
    {
      "storyId": "01J…",
      "at": "2026-10-09T12:05:00Z",
      "outlet": "CBC",
      "summary": "…",
      "audioStatus": "ready",
      "audioKey": "audio/opus/…/….opus"
    }
  ]
}
```

| `status` (API) | UI label |
| --- | --- |
| `open` | **Ongoing** |
| `closed` | **Closed** |

### `display_ads`

First-party in-feed cards. Not mixed into `stories`. Served by `GET /v1/ads/display`. Seed: `scripts/seed_demo_ads.py`.

```json
{
  "adId": "display_demo_1",
  "advertiser": "VIA Rail",
  "title": "Weekend trains from $49 — see Canada by rail",
  "clickUrl": "https://www.viarail.ca/",
  "imageKey": "local/ads/display/ad_demo_1.jpg",
  "imageAspect": 0.74,
  "active": true,
  "slot": "home_wall",
  "slots": ["home_wall"]
}
```

| Field | Notes |
| --- | --- |
| `slot` / `slots` | `home_wall` and/or `storylines_list` |
| `imageKey` | Local media or S3 key; API returns a signed/local `imageUrl` |
| `active` | Inactive ads are omitted |

Play queues ignore these. No audio ads in this collection.

### `publish_deadletters` (ops)

Failed Mongo/S3 attempts for operators; not exposed to mobile.

## PostgreSQL (users)

### `users`

| Column | Type | Notes |
| --- | --- | --- |
| `user_id` | text PK | App id (ULID/UUID) |
| `google_sub` | text unique | Google subject |
| `email` | text | |
| `display_name` | text | |
| `avatar_url` | text null | |
| `created_at` | timestamptz | |
| `updated_at` | timestamptz | |
| `last_login_at` | timestamptz | |

### `user_preferences`

| Column | Type | Notes |
| --- | --- | --- |
| `user_id` | text PK/FK | |
| `topics` | text[] or jsonb | e.g. `{Canada,Local}` |
| `prefer_listen_ready` | boolean | Unused by the app (Home is always `mode=listen`) |
| `updated_at` | timestamptz | |

## Device SQLite (mobile cache)

Suggested tables (names illustrative):

- `cached_stories` — StoryCard fields needed for masonry + detail offline read
- `cached_coverage` / `cached_storylines` — list rows + optional detail JSON
- `local_prefs` — topics mirror, guest or signed-in
- `sync_state` — cursors, `newestPublishedAt`, last sync times
- `play_history` — optional soft exclude of recently heard ids

Audio bytes are **not** stored in SQLite for v1.

## S3 object layout

```text
s3://{bucket}/audio/opus/{yyyy}/{mm}/{dd}/{storyId}.opus
```

- Content-Type: `audio/opus`
- Cache-Control: long-lived (content addressed by story id; replace only on re-synth)
- Encryption: SSE-S3 or SSE-KMS
- Public access: **blocked**; Lambda mints signed GET URLs

Optional later: `audio/opus/clusters/{clusterId}.opus` for a single “compare voiceover”.

## API-facing DTOs (conceptual)

Mobile never receives raw Mongo documents with internal counters. The backend maps to slim DTOs described in [api.md](./api.md).

## Soft deletes / retention

- Stories older than a configurable window (e.g. 14–30 days) may drop from the Home feed window but remain addressable by id for Storylines history.
- S3 lifecycle rule can expire Opus after the same window + grace days.
- Working SQLite can retain longer for debugging.
