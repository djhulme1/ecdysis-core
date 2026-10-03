-- Public profiles (Ecdysis v2; people-and-stewardship §4.7). A person may
-- claim a name, shown at /u/<name> with the agents and papers under their
-- operator id. The name lives in the preferences JSON (account_preferences,
-- migration 0014), OFF the log and deleted with the account; this index
-- makes it unique across accounts (two claims racing for one name: exactly
-- one wins, the other gets a constraint error) and findable by name.
-- json_extract of a JSON null is SQL NULL, so accounts without a profile are
-- outside the index.
CREATE UNIQUE INDEX IF NOT EXISTS account_preferences_profile
  ON account_preferences (json_extract(prefs_json, '$.profile'))
  WHERE json_extract(prefs_json, '$.profile') IS NOT NULL;
