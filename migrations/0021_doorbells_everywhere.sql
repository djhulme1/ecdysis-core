-- Doorbells for every platform (wake/0.1). Most AI apps can't be started
-- from outside but can start themselves when an email arrives, so a
-- doorbell may now be an email to an address its person confirmed; later
-- changes add trigger URLs, GitHub dispatches and MCP event subscriptions,
-- and the constraint below already names them so the table is rebuilt once.
--
-- Two new columns:
--  - target_sealed: where a ring goes when that is itself private (an
--    email address), sealed like a routine's token (AES-GCM, bound to the
--    handle and to what it is), never shown whole again;
--  - settings_json: what the private page needs that isn't secret (the app
--    its person runs it in, the email tag, the stop link's secret) and an
--    address waiting for its owner's click.
--
-- SQLite can't alter a CHECK constraint, so the table is rebuilt in place,
-- as 0002 did for quarantine: every row and column is copied, nothing is
-- dropped but the old table's shell. Operational and private as before:
-- none of this enters the public log.

CREATE TABLE doorbells_v2 (
  handle           TEXT PRIMARY KEY,
  kind             TEXT NOT NULL CHECK (kind IN ('claude-routine','webhook','self','email','fire-url','github-dispatch','mcp-events')),
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
  rings_today      INTEGER NOT NULL DEFAULT 0,
  target_sealed    TEXT,
  settings_json    TEXT NOT NULL DEFAULT '{}'
);

INSERT INTO doorbells_v2 (handle, kind, status, cadence, routine_id, url, token_sealed, key_ref, setup_id, setup_token, setup_issued_at,
  challenge, created_at, updated_at, last_ring_at, last_research_at, last_ok_at, last_session_url, failures, last_error, rings_day, rings_today)
  SELECT handle, kind, status, cadence, routine_id, url, token_sealed, key_ref, setup_id, setup_token, setup_issued_at,
    challenge, created_at, updated_at, last_ring_at, last_research_at, last_ok_at, last_session_url, failures, last_error, rings_day, rings_today
  FROM doorbells;

DROP TABLE doorbells;
ALTER TABLE doorbells_v2 RENAME TO doorbells;
CREATE INDEX IF NOT EXISTS doorbells_status ON doorbells(status);
