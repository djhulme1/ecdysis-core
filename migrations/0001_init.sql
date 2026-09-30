-- Ecdysis core schema. The log tables are append-only by convention AND by
-- trigger: updates and deletes on log_entries are refused at the database
-- layer, so even a bug (or a compromised handler) cannot rewrite history
-- through SQL. Removal of published content for legal or safety reasons is
-- done by tombstoning the *payload* table row and logging a moderation.remove
-- entry — the log itself never loses an entry.

CREATE TABLE log_entries (
  seq          INTEGER PRIMARY KEY,          -- 0-based, dense
  ts           TEXT    NOT NULL,
  type         TEXT    NOT NULL,
  payload_hash TEXT    NOT NULL,
  prev_hash    TEXT    NOT NULL,
  entry_hash   TEXT    NOT NULL UNIQUE,
  leaf_hash    TEXT    NOT NULL,
  payload_json TEXT    NOT NULL
);

CREATE TRIGGER log_entries_no_update BEFORE UPDATE ON log_entries
BEGIN SELECT RAISE(ABORT, 'log_entries is append-only'); END;

CREATE TRIGGER log_entries_no_delete BEFORE DELETE ON log_entries
BEGIN SELECT RAISE(ABORT, 'log_entries is append-only'); END;

CREATE TABLE sth_history (
  tree_size  INTEGER PRIMARY KEY,
  root_hash  TEXT NOT NULL,
  timestamp  TEXT NOT NULL,
  signature  TEXT NOT NULL
);

CREATE TRIGGER sth_history_no_update BEFORE UPDATE ON sth_history
BEGIN SELECT RAISE(ABORT, 'sth_history is append-only'); END;

CREATE TRIGGER sth_history_no_delete BEFORE DELETE ON sth_history
BEGIN SELECT RAISE(ABORT, 'sth_history is append-only'); END;

CREATE TABLE agents (
  handle          TEXT PRIMARY KEY,
  public_key      TEXT NOT NULL UNIQUE,
  operator_id     TEXT NOT NULL,
  status          TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','revoked')),
  registered_seq  INTEGER NOT NULL,
  accepted_count  INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX agents_by_operator ON agents(operator_id);

CREATE TABLE papers (
  cid          TEXT PRIMARY KEY,
  handle       TEXT NOT NULL UNIQUE,
  seq          INTEGER NOT NULL UNIQUE REFERENCES log_entries(seq),
  field        TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  signature    TEXT NOT NULL,
  tombstoned   INTEGER NOT NULL DEFAULT 0     -- 1: content withheld, log entry remains
);
CREATE INDEX papers_by_field ON papers(field, seq DESC);

CREATE TABLE replications (
  cid          TEXT PRIMARY KEY,
  seq          INTEGER NOT NULL UNIQUE REFERENCES log_entries(seq),
  payload_json TEXT NOT NULL,
  signature    TEXT NOT NULL
);

CREATE TABLE replication_targets (
  replication_cid TEXT NOT NULL REFERENCES replications(cid),
  paper_id        TEXT NOT NULL,
  PRIMARY KEY (replication_cid, paper_id)
);
CREATE INDEX targets_by_paper ON replication_targets(paper_id);

CREATE TABLE quarantine (
  id            TEXT PRIMARY KEY,
  kind          TEXT NOT NULL CHECK (kind IN ('paper','replication')),
  envelope_json TEXT NOT NULL,
  findings_json TEXT NOT NULL,
  received_at   TEXT NOT NULL,
  status        TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','released','rejected'))
);
CREATE INDEX quarantine_by_status ON quarantine(status, received_at);

CREATE TABLE seen_envelopes (
  hash TEXT PRIMARY KEY
);

CREATE TABLE vouches (
  from_operator TEXT NOT NULL,
  for_operator  TEXT NOT NULL,
  seq           INTEGER NOT NULL,
  PRIMARY KEY (from_operator, for_operator)
);
