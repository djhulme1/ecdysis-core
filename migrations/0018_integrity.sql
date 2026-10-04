-- Integrity (4 October 2026): what keeps the record honest without anyone
-- voting. Three tables, none an input to any number.
--
-- v2_subjects: an id reserved at the moment of writing. The derived record is
-- what a request checks against, and two requests that overlap both see a
-- record without the id; the primary key here is the one check that cannot
-- be overtaken, so a duplicate submitted twice at once enters the log once.
CREATE TABLE IF NOT EXISTS v2_subjects (
  kind        TEXT NOT NULL,         -- external | paper
  id          TEXT NOT NULL,
  created_at  TEXT NOT NULL,
  PRIMARY KEY (kind, id)
);
-- v2_issues: what might be wrong with an item, off the log until a steward
-- acts (src/api/v2/issues.ts). A steward's act on the item is logged
-- publicly (content.withhold / content.restore); the issue is not.
CREATE TABLE IF NOT EXISTS v2_issues (
  id          TEXT PRIMARY KEY,
  kind        TEXT NOT NULL,         -- complaint | quote-mismatch | source-unresolvable | duplicate | named-person | other
  subject     TEXT NOT NULL,         -- ecd:… | ext:… | ch:… | a 64-hex id
  severity    INTEGER NOT NULL,      -- 1 worth a look, 2 decide soon, 3 hide first
  detail      TEXT NOT NULL,
  source      TEXT NOT NULL,         -- complaint | scout | screening | steward
  status      TEXT NOT NULL,         -- open | dismissed | acted
  opened_at   TEXT NOT NULL,
  decided_at  TEXT,
  decided_by  TEXT,                  -- the steward's operator id
  note        TEXT                   -- the decision and the steward's private note
);
CREATE INDEX IF NOT EXISTS v2_issues_status ON v2_issues (status, opened_at);
CREATE INDEX IF NOT EXISTS v2_issues_subject ON v2_issues (kind, subject, status);
-- v2_complaints: what the public form took, kept for the stewards only. The
-- connecting address is kept as a keyed hash for the per-address cap.
CREATE TABLE IF NOT EXISTS v2_complaints (
  id          TEXT PRIMARY KEY,
  issue_id    TEXT NOT NULL,
  subject     TEXT NOT NULL,
  text        TEXT NOT NULL,
  contact     TEXT NOT NULL,
  ip_hash     TEXT NOT NULL,
  at          TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS v2_complaints_issue ON v2_complaints (issue_id);
CREATE INDEX IF NOT EXISTS v2_complaints_ip ON v2_complaints (ip_hash, at);
