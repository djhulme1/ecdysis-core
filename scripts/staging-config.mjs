// Fill in the STAGING database id in wrangler.toml by looking the database
// up by its name, so no workflow depends on a repository variable somebody
// has to copy by hand. Run by the Deploy, CI (preview) and Staging workflows
// before any wrangler command that uses --env staging.
//
//   node scripts/staging-config.mjs            exit 0 and patch; exit 3 when ecdysis-staging does not exist (not provisioned)
//   node scripts/staging-config.mjs --create   create ecdysis-staging first when it is missing
//
// It refuses an id equal to production's (the top-level database_id), and it
// touches only the placeholder under [env.staging]. Needs CLOUDFLARE_API_TOKEN
// and CLOUDFLARE_ACCOUNT_ID, as every wrangler command does.

import { execFileSync } from "node:child_process";
import { readFileSync, writeFileSync } from "node:fs";

const NAME = "ecdysis-staging";
const PLACEHOLDER = "REPLACE_WITH_STAGING_D1_ID";
const file = new URL("../wrangler.toml", import.meta.url);
const toml = readFileSync(file, "utf8");
const wrangler = (args) => execFileSync("npx", ["wrangler", ...args], { encoding: "utf8", stdio: ["ignore", "pipe", "pipe"] });
const find = () => {
  const out = wrangler(["d1", "list", "--json"]);
  return JSON.parse(out.slice(out.indexOf("["))).find((d) => d.name === NAME)?.uuid ?? null;
};

let id = find();
if (!id && process.argv.includes("--create")) {
  wrangler(["d1", "create", NAME]);
  id = find();
}
if (!id) {
  process.stdout.write(`staging-config: no database named ${NAME}: staging is not provisioned (run the Staging workflow once)\n`);
  process.exit(3);
}
const production = toml.slice(0, toml.search(/^\[env\./m)).match(/^database_id\s*=\s*"([^"]+)"/m)?.[1];
if (!production || production === id) {
  process.stderr.write("staging-config: the staging database id is production's: refusing\n");
  process.exit(1);
}
if (!toml.includes(PLACEHOLDER)) {
  process.stderr.write("staging-config: wrangler.toml has no staging placeholder to fill\n");
  process.exit(1);
}
writeFileSync(file, toml.replace(PLACEHOLDER, id));
process.stdout.write(`staging-config: ${NAME} is ${id}\n`);
