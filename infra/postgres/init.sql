CREATE TABLE IF NOT EXISTS users (
    user_id         TEXT PRIMARY KEY,
    google_sub      TEXT NOT NULL UNIQUE,
    email           TEXT NOT NULL,
    display_name    TEXT NOT NULL DEFAULT '',
    avatar_url      TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_login_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS user_preferences (
    user_id              TEXT PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
    topics               TEXT[] NOT NULL DEFAULT ARRAY['Top','Canada','Local'],
    prefer_listen_ready  BOOLEAN NOT NULL DEFAULT FALSE,
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
