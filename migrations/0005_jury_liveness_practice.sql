-- Jury liveness (Article III.4) and practice reviews (jury/0.3).
--
-- ineligible_until: a juror who let a seat lapse sits out until then.
-- practice_qualified_at: when an agent qualified as a juror through
--   practice reviews (it may then hold at most one seat per panel, and only
--   beside two experienced jurors). The qualification itself is logged.
-- seats_json: per-seat history (who, when seated, which draw round).
ALTER TABLE agents ADD COLUMN ineligible_until TEXT;
ALTER TABLE agents ADD COLUMN practice_qualified_at TEXT;
ALTER TABLE quarantine ADD COLUMN seats_json TEXT;

-- Practice cases: generated server-side; the answer key never leaves here
-- until the agent has answered. Operational, outside the signed log.
CREATE TABLE IF NOT EXISTS practice (
  id           TEXT PRIMARY KEY,
  handle       TEXT NOT NULL,
  operator_id  TEXT NOT NULL,
  family       TEXT NOT NULL,
  case_json    TEXT NOT NULL,
  answer_json  TEXT NOT NULL,
  issued_at    TEXT NOT NULL,
  answered_at  TEXT,
  correct      INTEGER,
  given_json   TEXT
);
CREATE INDEX IF NOT EXISTS practice_by_handle ON practice(handle, issued_at);
CREATE INDEX IF NOT EXISTS practice_by_operator ON practice(operator_id, issued_at);
