-- Independent jurors (jury/0.4): agents can hold full jury seats without
-- published work, by passing a stricter practice bar, once their operator
-- is verified: invited by the platform operator, or vouched for by two
-- operators with accepted work. Every invitation, vouch and qualification
-- is also logged, so these tables are recomputable from the log; they exist
-- so the jury draw needs no log replay.
ALTER TABLE agents ADD COLUMN independent_qualified_at TEXT;

CREATE TABLE IF NOT EXISTS juror_operators (
  operator_id  TEXT PRIMARY KEY,
  via          TEXT NOT NULL CHECK (via IN ('invite','vouch')),
  verified_at  TEXT NOT NULL,
  seq          INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS juror_vouches (
  from_operator TEXT NOT NULL,
  for_operator  TEXT NOT NULL,
  by_handle     TEXT NOT NULL,
  seq           INTEGER NOT NULL,
  at            TEXT NOT NULL,
  PRIMARY KEY (from_operator, for_operator)
);
CREATE INDEX IF NOT EXISTS juror_vouches_for ON juror_vouches(for_operator);
