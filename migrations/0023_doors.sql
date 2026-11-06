-- Attribution at sign-up (src/api/v2/accounts.ts): the door an account came
-- through (a channel name from the ?via= link the person followed, carried in
-- the ecd_via cookie until they signed up) and the country their connection
-- came from when the account was made (ISO 3166-1 alpha-2, from Cloudflare's
-- cf-ipcountry header; never an address). Counted by the stewards' attribution
-- report, by month, door and country; off the log; deleted with the account.
ALTER TABLE accounts ADD COLUMN door TEXT;
ALTER TABLE accounts ADD COLUMN country TEXT;
CREATE INDEX IF NOT EXISTS accounts_created ON accounts (created_at);
