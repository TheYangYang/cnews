# Upgrade plan — personalization & recommendations

**Status:** Planned — **not implementing now**.  
Builds on today’s CrackNews loop (guest browse, topic toggles, Google/dev login, Postgres `user_preferences`).

Goal: signed-in users get **outlet subscriptions**, richer **preferences**, and a **recommendation layer** that ranks Home / Storylines without turning the app into a social network.

Related: [features.md](./features.md) · [data-model.md](./data-model.md) · [api.md](./api.md) · [SHIPPED.md](./SHIPPED.md)

---

## Why later

| Today | Gap |
| --- | --- |
| Topic filters (`Top`, `Canada`, …) | Too coarse — users care about **CBC vs National Post**, local desks, etc. |
| Chronological / shuffled feed | No learning from plays, dwell, or follows |
| Guest + optional Google | Prefs exist but are thin (`topics` + listening mode) |
| Cluster/coverage API unused in UI | Personalization can still ship without compare swipe |

---

## Phased delivery (future)

### U0 — Account foundation (prerequisite)

Harden login before personalization:

- Production Google OAuth client IDs (retire `dev:` outside Development).
- Stable `userId` in JWT; refresh tokens if sessions get long-lived.
- Postgres migrations for preference tables (below).
- Settings: clear “Signed in · syncing preferences” state.

**Exit.** Same Google account restores topics on a second device reliably.

---

### U1 — Preference profile

Expand what we store per user (Postgres), mirror on device for offline Settings.

**Preference fields (proposed)**

| Field | Type | Notes |
| --- | --- | --- |
| `topics` | string[] | Existing |
| `listeningPreference` | enum | Existing (`any` / `voice_ready_only`) |
| `preferredOutlets` | string[] | e.g. `CBC`, `Global News` — **subscribe** |
| `mutedOutlets` | string[] | Soft-hide from Home |
| `preferredPlaces` | string[] | Province / city labels from ingest |
| `briefDensity` | enum | shorter / default (future brief variants) |
| `timezone` | string | Stamp display + digest windows |

**API (proposed)**

```http
GET  /v1/me/preferences
PUT  /v1/me/preferences
```

Body merges with existing `PUT /v1/me/topics` (or deprecate topics-only endpoint).

**Mobile**

- Settings sections: Topics · **Outlets** · Places · Listening.
- Outlet list sourced from `/v1/meta/outlets` (new) derived from distinct `stories.outlet`.

**Exit.** User can follow 3 outlets + mute 1; Home respects soft filters after sync.

---

### U2 — Outlet subscribe / follow

Product model:

- **Subscribe** = boost + optionally require at least one subscribed outlet in Play queues when available.
- **Mute** = exclude from Home wall (still reachable via Storylines / search later).
- Not a social graph — no public follows.

**Data**

```text
user_outlet_subscriptions (
  user_id, outlet, weight, created_at
)
user_outlet_mutes (
  user_id, outlet, created_at
)
```

**Feed behavior (v1 rules, no ML)**

1. Fetch candidate page as today (topic + cursor).
2. Filter out `mutedOutlets`.
3. Stable re-rank: subscribed outlets first (recency within group), then others.
4. Play visible-queue unchanged except it sees the re-ranked wall.

**Exit.** Subscribed CBC cards appear above muted/non-followed peers on the first screen.

---

### U3 — Implicit signals (privacy-light)

Collect **on-device first**, batch upload when signed in (opt-in analytics toggle).

| Event | Use |
| --- | --- |
| `play_start` / `play_complete` | Affinity for outlet + topic |
| `card_open` / `original_open` | Interest vs skip |
| `storyline_follow` (explicit later) | Thread affinity |
| Negative: quick dismiss / mute | Downrank |

Store aggregates in Postgres (`user_affinity_outlet`, `user_affinity_topic`) — **no raw article body**.

**Exit.** Affinity table updates after a Play session; no ranking change yet (U4).

---

### U4 — Recommendation ranking

Replace pure chrono/shuffle for signed-in Home (guests keep today’s behavior).

**v1 scorer (interpretable, no GPU)**

```text
score = w1 * recency
      + w2 * topic_match
      + w3 * outlet_subscribe
      + w4 * outlet_affinity
      + w5 * place_match
      - w6 * already_seen_penalty
```

Serve via:

```http
GET /v1/home/feed?mode=for_you
```

or header `X-Feed-Rank: for_you` when JWT present. Keep `mode=chrono` for debugging.

**Storylines**

- Optional `for_you` list: boost threads whose outlets intersect subscriptions / affinity.
- Timeline detail stays chronological (truth of the event).

**Guardrails**

- Always include a **diversity floor** (max N consecutive same outlet).
- Cold start: fall back to topics + subscribe list only.
- Document weights in config (not hard-coded magic only).

**Exit.** Blind A/B or dogfood: signed-in For You feels more relevant than guest shuffle without trapping users in one desk.

---

### U5 — Optional later enhancements

| Idea | Notes |
| --- | --- |
| Daily digest audio | Playlist of top For You briefs |
| “More like this” | Same cluster / topic expand |
| Explicit Follow on Storyline | Pin thread to Storylines top |
| On-device ranking | If privacy mode: score locally from mirrored affinities |
| Compare swipe (F7) | Can return independently of recommender |
| Push breaking alerts | Only with explicit opt-in |

---

## Suggested schema additions (draft)

```sql
-- preferences blob or columns
ALTER TABLE user_preferences
  ADD COLUMN preferred_outlets text[] DEFAULT '{}',
  ADD COLUMN muted_outlets text[] DEFAULT '{}',
  ADD COLUMN preferred_places text[] DEFAULT '{}';

CREATE TABLE user_outlet_subscriptions (
  user_id uuid NOT NULL REFERENCES users(id),
  outlet text NOT NULL,
  weight real NOT NULL DEFAULT 1,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (user_id, outlet)
);

CREATE TABLE user_affinity_outlet (
  user_id uuid NOT NULL,
  outlet text NOT NULL,
  score real NOT NULL DEFAULT 0,
  updated_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (user_id, outlet)
);
```

Mongo stays the content system of record; **do not** write user prefs into Mongo.

---

## Mobile UX sketch (future)

```text
Settings
├── Account
├── Topics          (existing)
├── Outlets         NEW — search + subscribe / mute chips
├── Places          NEW
├── Listening       (existing)
└── Privacy         NEW — “Improve recommendations” toggle

Home
├── Guest / chrono   — today’s shuffle + pagination
└── Signed-in       — For You rank (subtle label, not a second tab)
```

No separate “Discover” tab in v1 of this plan — keep Home immersive.

---

## Implementation order (when we start)

1. U0 production auth  
2. U1 preferences API + Settings Outlets UI  
3. U2 mute/subscribe filter + boost in `GetFeedAsync`  
4. U3 play/open events → affinity  
5. U4 `for_you` scorer + config weights  
6. U5 only if metrics support it  

Estimate (solo, rough): U0–U2 ≈ 1–2 weeks; U3–U4 ≈ 2–3 weeks including dogfood.

---

## Non-goals (still)

- Social likes/comments/follower counts.
- Selling attention to advertisers.
- Training on full article text in the cloud without a clear privacy story.
- Replacing outlet journalism with model-generated “news.”

---

## Acceptance (when U4 ships)

1. New Google user with empty affinity gets a sensible topic+subscribe feed.  
2. Subscribing to CBC increases CBC share on screen 1 within one refresh.  
3. Muting an outlet removes it from Home (Storylines may still show).  
4. Guest feed behavior unchanged.  
5. Play still page-scoped; recommendations never auto-start audio.  
