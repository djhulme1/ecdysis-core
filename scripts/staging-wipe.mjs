// Wipe the STAGING record: drop every table in the staging database so the
// migrations can lay it out again from nothing. Run by the Staging workflow
// (.github/workflows/staging.yml) before a reset's genesis; never by hand
// against anything else.
//
// Three locks against ever touching production:
//   1. it always runs wrangler with --env staging, and reads the database it
//      is about to wipe from that environment's own [[d1_databases]] block;
//   2. that block must name the database "ecdysis-staging" and the
//      environment must say ENVIRONMENT = "staging", or it stops;
//   3. the top-level (production) database id must not be the one it resolved.
//
// Needs CLOUDFLARE_API_TOKEN and CLOUDFLARE_ACCOUNT_ID in the environment,
// as every wrangler command does; it prints what it drops and nothing else.

import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";

const toml = readFileSync(new URL("../wrangler.toml", import.meta.url), "utf8");
const stagingAt = toml.indexOf("[env.staging]");
if (stagingAt < 0) fail("wrangler.toml has no [env.staging]");
const top = toml.slice(0, toml.search(/^\[env\./m));
const staging = toml.slice(stagingAt);
if (!/^ENVIRONMENT\s*=\s*"staging"/m.test(staging)) fail("[env.staging] does not say ENVIRONMENT = \"staging\"");
const stagingDb = staging.match(/^\[\[env\.staging\.d1_databases\]\]\s*\nbinding\s*=\s*"DB"\s*\ndatabase_name\s*=\s*"([^"]+)"\s*\ndatabase_id\s*=\s*"([^"]+)"/m);
if (!stagingDb) fail("[env.staging] has no DB binding in the expected shape");
const [, name, id] = stagingDb;
if (name !== "ecdysis-staging") fail(`the staging database is named "${name}", not "ecdysis-staging": refusing`);
if (id.startsWith("REPLACE")) fail("the staging database id is still a placeholder: patch it first (STAGING_D1_ID)");
const productionId = top.match(/^database_id\s*=\s*"([^"]+)"/m)?.[1];
if (!productionId || productionId === id) fail("the staging database id is production's: refusing");

function fail(msg) {
  process.stderr.write(`staging-wipe: ${msg}\n`);
  process.exit(1);
}

function d1(command) {
  const out = execFileSync("npx", ["wrangler", "d1", "execute", "DB", "--env", "staging", "--remote", "--json", "--command", command], { encoding: "utf8", stdio: ["ignore", "pipe", "inherit"] });
  // wrangler prints its banner to stdout before the JSON on some versions: take the JSON from its first bracket.
  const json = out.slice(out.indexOf("["));
  return JSON.parse(json);
}

// Everything the migrations made, and wrangler's own migrations table, so they run again from the first. Cloudflare's own
// tables (_cf_*) and SQLite's (sqlite_*) are not ours to drop. Triggers and indexes go with their tables.
const rows = d1("SELECT name, type FROM sqlite_master WHERE type IN ('table', 'view') AND name NOT LIKE 'sqlite\\_%' ESCAPE '\\' AND name NOT LIKE '\\_cf\\_%' ESCAPE '\\' ORDER BY type DESC, name")[0]?.results ?? [];
if (!rows.length) {
  process.stdout.write("staging-wipe: nothing to drop (an empty database)\n");
  process.exit(0);
}
const statements = rows.map((r) => `DROP ${r.type === "view" ? "VIEW" : "TABLE"} IF EXISTS "${String(r.name).replace(/"/g, '""')}";`);
process.stdout.write(`staging-wipe: dropping ${rows.length} ${rows.length === 1 ? "object" : "objects"} from ${name} (${id}): ${rows.map((r) => r.name).join(", ")}\n`);
// One statement a call: a batch stops at its first failure, and a table another depends on may need a second pass.
let left = statements;
for (let pass = 0; pass < 3 && left.length; pass++) {
  const failed = [];
  for (const s of left) {
    try { d1(s); } catch { failed.push(s); }
  }
  left = failed;
}
if (left.length) fail(`could not drop: ${left.join(" ")}`);
const after = d1("SELECT count(*) AS n FROM sqlite_master WHERE type IN ('table', 'view') AND name NOT LIKE 'sqlite\\_%' ESCAPE '\\' AND name NOT LIKE '\\_cf\\_%' ESCAPE '\\'")[0]?.results?.[0]?.n;
if (Number(after) !== 0) fail(`${after} objects remain`);
process.stdout.write("staging-wipe: the staging database is empty; apply the migrations next\n");
