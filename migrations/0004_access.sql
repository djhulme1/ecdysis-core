-- Access counts are an OPERATIONAL metric, deliberately outside the
-- transparency log: they are operator-reported, not signed, not provable,
-- and the UI labels them as such. The record stays the record.
CREATE TABLE IF NOT EXISTS access_counts (
  id TEXT PRIMARY KEY, -- paper display handle (ecd:YYMM.xxxxxx)
  count INTEGER NOT NULL DEFAULT 0
);
