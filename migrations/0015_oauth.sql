-- OAuth 2.1 for the connector, and managed agents (Ecdysis v2;
-- src/api/v2/oauth.ts; constitution I.4). Everything here is OFF the log.
-- Codes and tokens are stored as hashes; a managed agent's private key is
-- stored sealed (AES-GCM under a key derived from ACCOUNTS_KEY, bound to the
-- handle) and erased when the person destroys it. Nothing here is an input
-- to any number; the log records a managed agent's registration as
-- `managed: true`, which is what the record shows.
CREATE TABLE IF NOT EXISTS oauth_clients (
  id                 TEXT PRIMARY KEY,   -- cl_<hex>
  name               TEXT NOT NULL,
  redirect_uris_json TEXT NOT NULL,      -- JSON array of exact URIs
  created_at         TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS oauth_registrations (
  ip_hash    TEXT NOT NULL,              -- for the per-connection limit on client registration
  at         TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS oauth_registrations_ip ON oauth_registrations (ip_hash, at);
CREATE TABLE IF NOT EXISTS oauth_codes (
  hash           TEXT PRIMARY KEY,       -- sha256 of the code
  client_id      TEXT NOT NULL,
  account_id     TEXT NOT NULL,
  redirect_uri   TEXT NOT NULL,
  code_challenge TEXT NOT NULL,          -- PKCE S256
  scope          TEXT NOT NULL,
  resource       TEXT NOT NULL,
  created_at     TEXT NOT NULL,
  expires_at     TEXT NOT NULL,
  used_at        TEXT
);
CREATE TABLE IF NOT EXISTS oauth_tokens (
  hash        TEXT PRIMARY KEY,          -- sha256 of the token
  kind        TEXT NOT NULL,             -- access | refresh
  account_id  TEXT NOT NULL,
  client_id   TEXT NOT NULL,
  scope       TEXT NOT NULL,
  resource    TEXT NOT NULL,
  created_at  TEXT NOT NULL,
  expires_at  TEXT NOT NULL,
  revoked_at  TEXT
);
CREATE INDEX IF NOT EXISTS oauth_tokens_account ON oauth_tokens (account_id);
CREATE TABLE IF NOT EXISTS managed_keys (
  handle         TEXT PRIMARY KEY,
  account_id     TEXT NOT NULL,
  public_key     TEXT NOT NULL,
  private_sealed TEXT NOT NULL,          -- "" once destroyed
  created_at     TEXT NOT NULL,
  destroyed_at   TEXT
);
CREATE INDEX IF NOT EXISTS managed_keys_account ON managed_keys (account_id);
