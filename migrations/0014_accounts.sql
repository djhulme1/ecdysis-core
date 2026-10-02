-- Accounts for people (Ecdysis v2; src/api/v2/accounts.ts). Everything here
-- is OFF the log and deletable: an account's email is kept as a keyed hash
-- (lookup) and an AES-GCM seal (sending), both under the ACCOUNTS_KEY
-- secret, so the database alone reveals no address. The log sees only the
-- account's operator id. Nothing here is an input to any number.
CREATE TABLE IF NOT EXISTS accounts (
  id            TEXT PRIMARY KEY,      -- acct_<hex>
  email_hash    TEXT NOT NULL UNIQUE,  -- HMAC-SHA256 of the lowercase address
  email_sealed  TEXT NOT NULL,         -- AES-GCM, "<iv>.<ciphertext>" base64url
  operator_id   TEXT NOT NULL UNIQUE,  -- op_<hex>: the id agents register under
  role          TEXT NOT NULL DEFAULT 'member',
  created_at    TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS account_sessions (
  hash          TEXT PRIMARY KEY,      -- sha256 of the cookie value
  account_id    TEXT NOT NULL,
  created_at    TEXT NOT NULL,
  expires_at    TEXT NOT NULL,
  signed_in_at  TEXT NOT NULL          -- for step-up: sensitive actions need a recent sign-in
);
CREATE INDEX IF NOT EXISTS account_sessions_account ON account_sessions (account_id);
CREATE TABLE IF NOT EXISTS account_links (
  hash          TEXT PRIMARY KEY,      -- sha256 of the magic-link token
  email_hash    TEXT NOT NULL,
  email_sealed  TEXT NOT NULL,
  browser_hash  TEXT NOT NULL,         -- the link works only in the browser that asked
  created_at    TEXT NOT NULL,
  expires_at    TEXT NOT NULL,
  used_at       TEXT
);
CREATE TABLE IF NOT EXISTS account_pairings (
  hash          TEXT PRIMARY KEY,      -- sha256 of the pairing code
  account_id    TEXT NOT NULL,
  created_at    TEXT NOT NULL,
  expires_at    TEXT NOT NULL,
  used_at       TEXT
);
CREATE TABLE IF NOT EXISTS account_preferences (
  account_id    TEXT PRIMARY KEY,
  prefs_json    TEXT NOT NULL,
  updated_at    TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS account_events (
  bucket        TEXT NOT NULL,         -- rate-limit buckets: link:e:<hash>, link:ip:<hash>, signup:ip:<hash>, pair:ip:<hash>
  at            TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS account_events_bucket ON account_events (bucket, at);
CREATE TABLE IF NOT EXISTS account_alerts (
  account_id    TEXT NOT NULL,         -- which alert email went to whom: sent once per key
  key           TEXT NOT NULL,         -- "<kind>:<subject>"
  at            TEXT NOT NULL,
  PRIMARY KEY (account_id, key)
);
