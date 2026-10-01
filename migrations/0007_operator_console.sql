-- The operator console and the digest (double opt-in email). OPERATIONAL
-- and private: nothing here enters the public transparency log, and no
-- address ever appears in a counter.

-- Digest subscribers. Nothing but the confirmation email is sent until the
-- person confirms; an unsubscribe is honoured at once and for good.
CREATE TABLE IF NOT EXISTS subscribers (
  id              TEXT PRIMARY KEY,
  email           TEXT NOT NULL UNIQUE,
  fields_json     TEXT NOT NULL,
  pending_json    TEXT,
  status          TEXT NOT NULL,
  confirm_token   TEXT NOT NULL,
  unsub_token     TEXT NOT NULL,
  created_at      TEXT NOT NULL,
  confirm_sent_at TEXT,
  confirmed_at    TEXT,
  unsubscribed_at TEXT,
  consent         TEXT
);
CREATE INDEX IF NOT EXISTS subscribers_by_status ON subscribers(status, created_at);

-- Digest issues, written and sent from the console.
CREATE TABLE IF NOT EXISTS newsletter_issues (
  id         TEXT PRIMARY KEY,
  subject    TEXT NOT NULL,
  body       TEXT NOT NULL,
  audience   TEXT NOT NULL,
  status     TEXT NOT NULL,
  created_at TEXT NOT NULL,
  started_at TEXT,
  sent_at    TEXT,
  delivered  INTEGER NOT NULL DEFAULT 0,
  failed     INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS issues_by_created ON newsletter_issues(created_at);

-- One row per (issue, subscriber): sending resumes where it stopped and
-- never sends anyone the same issue twice.
CREATE TABLE IF NOT EXISTS newsletter_deliveries (
  issue_id      TEXT NOT NULL,
  subscriber_id TEXT NOT NULL,
  status        TEXT NOT NULL,
  at            TEXT NOT NULL,
  provider_id   TEXT,
  error         TEXT,
  PRIMARY KEY (issue_id, subscriber_id)
);

-- Every email handed to the provider, by kind only: the shared daily cap.
CREATE TABLE IF NOT EXISTS email_sends (
  at   TEXT NOT NULL,
  kind TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS email_sends_by_at ON email_sends(at);

-- Small operational state: the last cron run, the last full audit.
CREATE TABLE IF NOT EXISTS ops_state (
  key   TEXT PRIMARY KEY,
  value TEXT NOT NULL,
  at    TEXT NOT NULL
);

-- What was done from the operator console, by whom. Ids only.
CREATE TABLE IF NOT EXISTS ops_audit (
  id      INTEGER PRIMARY KEY AUTOINCREMENT,
  at      TEXT NOT NULL,
  actor   TEXT NOT NULL,
  action  TEXT NOT NULL,
  subject TEXT,
  detail  TEXT
);
CREATE INDEX IF NOT EXISTS ops_audit_by_at ON ops_audit(at);
