-- Marketplace builds: signed, content-addressed static bundles served on the
-- user-content apex. File bytes live in R2 under bundles/<cid>/<path>; this
-- table is the metadata and the slug registry.

CREATE TABLE builds (
  cid           TEXT PRIMARY KEY,
  slug          TEXT NOT NULL UNIQUE,
  manifest_json TEXT NOT NULL,
  signature     TEXT NOT NULL,
  status        TEXT NOT NULL DEFAULT 'in_review'
                CHECK (status IN ('in_review','awaiting_files','active','rejected')),
  review_passed INTEGER NOT NULL DEFAULT 0,
  seq           INTEGER NOT NULL DEFAULT -1
);
CREATE INDEX builds_by_status ON builds(status, seq DESC);
