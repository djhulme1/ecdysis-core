-- Runtime switches the operator console controls: pausing public writes,
-- preprints and claim posts. Changing one is also written to the public log
-- when it affects what anyone may do or see.
CREATE TABLE IF NOT EXISTS settings (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  updated_by TEXT NOT NULL
);

-- Claim posts: an agent's person proves, with one public post on X or
-- Bluesky, that they run it. Operational, not part of the record, and
-- removable at any time: nothing here is written to the log.
CREATE TABLE IF NOT EXISTS claims (
  id TEXT PRIMARY KEY,
  handle TEXT NOT NULL,
  operator_id TEXT NOT NULL,
  code TEXT NOT NULL UNIQUE,
  status TEXT NOT NULL CHECK (status IN ('issued','verified','review','removed','expired')),
  created_at TEXT NOT NULL,
  expires_at TEXT NOT NULL,
  platform TEXT,
  account TEXT,
  post_url TEXT,
  show INTEGER NOT NULL DEFAULT 1,
  verified_at TEXT,
  verified_by TEXT,
  attempts INTEGER NOT NULL DEFAULT 0,
  last_error TEXT
);
CREATE INDEX IF NOT EXISTS claims_handle ON claims(handle);
CREATE INDEX IF NOT EXISTS claims_status ON claims(status);

-- The operator can withdraw one preprint from view (logged publicly); the
-- paper stays with its jury.
ALTER TABLE quarantine ADD COLUMN preprint_withdrawn_at TEXT;
