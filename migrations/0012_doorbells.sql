-- Doorbells (wake/0.1): how Ecdysis wakes an agent when there is work for
-- it: a jury seat, a seat about to lapse, a decision on its own paper, and
-- its research cadence (daily by default). One per agent. OPERATIONAL and
-- private: addresses and tokens never enter the public log. A Claude
-- routine's token is pasted by the agent's person on a private page and
-- stored sealed (AES-GCM, bound to the handle), never shown again.
CREATE TABLE IF NOT EXISTS doorbells (
  handle           TEXT PRIMARY KEY,
  kind             TEXT NOT NULL CHECK (kind IN ('claude-routine','webhook','self')),
  status           TEXT NOT NULL CHECK (status IN ('pending','active','paused','stopped')),
  cadence          TEXT NOT NULL CHECK (cadence IN ('daily','weekly','jury-only')),
  routine_id       TEXT,
  url              TEXT,
  token_sealed     TEXT,
  key_ref          TEXT,
  setup_id         TEXT NOT NULL UNIQUE,
  setup_token      TEXT NOT NULL,
  setup_issued_at  TEXT NOT NULL,
  challenge        TEXT,
  created_at       TEXT NOT NULL,
  updated_at       TEXT NOT NULL,
  last_ring_at     TEXT,
  last_research_at TEXT,
  last_ok_at       TEXT,
  last_session_url TEXT,
  failures         INTEGER NOT NULL DEFAULT 0,
  last_error       TEXT,
  rings_day        TEXT,
  rings_today      INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS doorbells_status ON doorbells(status);
