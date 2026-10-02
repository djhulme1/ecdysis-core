-- The steward's canary registry (Ecdysis v2; src/api/v2/canaries.ts). OFF
-- the log. A canary is an external claim whose outcome was known before it
-- was planted; the registry remembers which live claims are canaries and when
-- the steward means to reveal each. Each row is keyed by a KEYED HASH of the
-- claim ref (under the accounts token key), and the ref, the known outcome,
-- the steward's label and the source are SEALED together under a key of
-- their own, bound to the row key: a copy of this table is a list of
-- random-looking rows with dates, and a blob moved to another row does not
-- open. The reveal itself is a log entry (canary.reveal); the registry only
-- notes that it happened.
CREATE TABLE IF NOT EXISTS steward_canaries (
  key            TEXT PRIMARY KEY,   -- keyed hash of the claim ref (40 hex)
  sealed         TEXT NOT NULL,      -- sealed JSON {claim, outcome, label, source}, bound to key
  reveal_after   TEXT,               -- ISO: intended reveal time; NULL: by hand
  registered_at  TEXT NOT NULL,
  registered_by  TEXT NOT NULL,      -- the steward's operator id
  revealed_at    TEXT                -- set when revealed from the registry
);
