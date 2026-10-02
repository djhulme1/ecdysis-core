-- The steward's canary registry (Ecdysis v2; src/api/v2/canaries.ts). OFF
-- the log. A canary is an external claim whose outcome was known before it
-- was planted; the registry remembers which live claims are canaries and when
-- the steward means to reveal each. The known outcome, the steward's label
-- and the source are SEALED together (AES-GCM under the accounts key), so
-- this table alone tells a live canary from any other external claim no
-- better than chance. The reveal itself is a log entry (canary.reveal); the
-- registry only notes that it happened.
CREATE TABLE IF NOT EXISTS steward_canaries (
  claim          TEXT PRIMARY KEY,   -- ext:<16 hex>#C1
  sealed         TEXT NOT NULL,      -- sealed JSON {outcome, label, source}
  reveal_after   TEXT,               -- ISO: intended reveal time; NULL: by hand
  registered_at  TEXT NOT NULL,
  registered_by  TEXT NOT NULL,      -- the steward's operator id
  revealed_at    TEXT                -- set when revealed from the registry
);
