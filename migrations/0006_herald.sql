-- The Herald: emails from Ecdysis to the authors of work the record has
-- checked. OPERATIONAL and private: recipient addresses never enter the
-- public transparency log. Every send needs the Herald approver's
-- signature; the suppression list is honoured forever.
CREATE TABLE IF NOT EXISTS herald (
  id           TEXT PRIMARY KEY,
  kind         TEXT NOT NULL,
  work_id      TEXT,
  paper_id     TEXT,
  recipient    TEXT NOT NULL,
  subject      TEXT NOT NULL,
  body         TEXT NOT NULL,
  status       TEXT NOT NULL,
  unsub_token  TEXT NOT NULL,
  created_at   TEXT NOT NULL,
  approved_at  TEXT,
  sent_at      TEXT,
  provider_id  TEXT,
  error        TEXT
);
CREATE INDEX IF NOT EXISTS herald_by_status ON herald(status, created_at);
CREATE INDEX IF NOT EXISTS herald_by_sent ON herald(sent_at);

CREATE TABLE IF NOT EXISTS herald_suppression (
  email TEXT PRIMARY KEY,
  at    TEXT NOT NULL
);
