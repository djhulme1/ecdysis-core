-- Autonomous governance: juries on quarantine, and a wider status machine
-- ('hazard_hold' for juror escalations awaiting reserved power R1). SQLite
-- cannot alter a CHECK constraint, so quarantine is rebuilt in place.

CREATE TABLE quarantine_v2 (
  id            TEXT PRIMARY KEY,
  kind          TEXT NOT NULL CHECK (kind IN ('paper','replication','build')),
  envelope_json TEXT NOT NULL,
  findings_json TEXT NOT NULL,
  received_at   TEXT NOT NULL,
  status        TEXT NOT NULL DEFAULT 'pending'
                CHECK (status IN ('pending','released','rejected','hazard_hold')),
  jury_json     TEXT NOT NULL DEFAULT '[]',
  jury_ops_json TEXT NOT NULL DEFAULT '[]',
  votes_json    TEXT NOT NULL DEFAULT '[]'
);

INSERT INTO quarantine_v2 (id, kind, envelope_json, findings_json, received_at, status)
  SELECT id, kind, envelope_json, findings_json, received_at, status FROM quarantine;

DROP TABLE quarantine;
ALTER TABLE quarantine_v2 RENAME TO quarantine;
CREATE INDEX quarantine_by_status ON quarantine(status, received_at);
