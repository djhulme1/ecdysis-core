-- context/0.1 (src/api/v2/context.ts, src/core/v2/context.ts): what a claim from human literature means, for a reader
-- who is not a specialist. Both tables are off the log: the paper's record as the open citation graph (OpenAlex) has it,
-- and the machine-written summary of each claim. Neither is evidence about any claim; neither is an input to any number.
CREATE TABLE IF NOT EXISTS v2_source_records (
  source    TEXT PRIMARY KEY,   -- the source in sources/0.1's spelling, lower-cased
  status    TEXT NOT NULL,      -- read | unresolved | error
  record    TEXT,               -- JSON: the paper's record (title, authors, venue, year, keywords, topic), when read
  read_at   TEXT NOT NULL,
  attempts  INTEGER NOT NULL,
  detail    TEXT
);

CREATE TABLE IF NOT EXISTS v2_claim_context (
  claim        TEXT PRIMARY KEY,  -- ext:…
  status       TEXT NOT NULL,     -- written | refused | error
  version      TEXT NOT NULL,     -- context/0.1
  model        TEXT,              -- the model that wrote it, as its provider names it
  inputs_hash  TEXT,              -- SHA-256 of the instructions, the model and the material it was written from
  explanation  TEXT,              -- JSON: meaning, findings, terms, basis, when written
  written_at   TEXT NOT NULL,
  attempts     INTEGER NOT NULL,
  detail       TEXT               -- why a summary was refused or failed (never the provider's key)
);
