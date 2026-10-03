-- Ecdysis v2 (design: docs/v2/PLAN.md). The record itself lives in the
-- transparency log (log_entries), from which src/core/v2/flow.ts derives
-- every number. These tables hold what the log commits to by hash but does
-- not carry: the signed envelopes behind entries, each receipt's bundle so
-- that cross-checkers can fetch it, and each receipt's outputs, withheld
-- from public view until the receipt is cross-checked. Nothing here is an
-- input to credence or standing.
CREATE TABLE IF NOT EXISTS v2_envelopes (
  id            TEXT PRIMARY KEY,   -- the receipt: sha256 of {p: payload, s: signature}
  envelope_json TEXT NOT NULL,
  created_at    TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS v2_bundles (
  commit_id   TEXT PRIMARY KEY,     -- the check.commit's receipt
  bundle_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS v2_outputs (
  key          TEXT PRIMARY KEY,    -- a commit id, or "<earlier commit>@<cross-checking commit>" for a cross-check run
  outputs_json TEXT NOT NULL,
  created_at   TEXT NOT NULL
);
