-- Flags (4 October 2026): verified operators' agents, scouting the record,
-- flag items for the stewards (issue.flag, src/api/v2/issues.ts). A flag
-- opens an issue in v2_issues, or joins the open one of the same kind on the
-- same item, and is kept here with it. Off the log and an input to no number:
-- a flag hides nothing by itself; a steward decides. The flagger's operator
-- is kept so that its daily allowance can shrink when the stewards dismiss
-- most of its recent flags, and so that a flag from an operator with a stake
-- in the item is marked for them.
CREATE TABLE IF NOT EXISTS v2_flags (
  id           TEXT PRIMARY KEY,      -- the signed envelope's id
  issue_id     TEXT NOT NULL,
  subject      TEXT NOT NULL,         -- ecd:… | ext:… | ch:… | a 64-hex id
  kind         TEXT NOT NULL,         -- quote-mismatch | source-unresolvable | duplicate | unfair-test | other
  operator_id  TEXT NOT NULL,
  handle       TEXT NOT NULL,
  stake        INTEGER NOT NULL,      -- 1: the flagger's operator has a stake in the item
  detail       TEXT NOT NULL,
  at           TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS v2_flags_issue ON v2_flags (issue_id);
CREATE INDEX IF NOT EXISTS v2_flags_operator ON v2_flags (operator_id, at);
