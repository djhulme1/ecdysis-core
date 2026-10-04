-- The quote scout's results (src/api/v2/quotes.ts): whether a registered
-- claim's quote exists in its source's published abstract or title. Off the
-- log; an observation about a source, never an input to any number.
CREATE TABLE IF NOT EXISTS v2_quote_checks (
  claim       TEXT PRIMARY KEY,      -- ext:…
  status      TEXT NOT NULL,         -- verified | mismatch | not-in-abstract | no-abstract | unresolvable | error
  where_found TEXT,                  -- arxiv-abstract | arxiv-title | crossref-abstract | crossref-title
  nearest     TEXT,                  -- the best-matching stretch of the source, for mismatches
  similarity  REAL,                  -- share of the quote's words found in order
  checked_at  TEXT NOT NULL,
  attempts    INTEGER NOT NULL,
  detail      TEXT
);
