/**
 * The STAGING record's keys, made inside the Staging workflow's runner and
 * nowhere else: the log key, the operator key (used once, for genesis) and
 * the accounts key. Each is written to its own file under the directory
 * given, mode 0600, and never printed; the workflow installs the private
 * halves as Worker secrets straight from those files, masks them, and
 * deletes the directory before the run ends. Only the public halves leave
 * the run, as repository variables.
 *
 *   node --import tsx scripts/staging-keys.ts <dir>
 *
 * Writes: log.private, log.public, operator.private, operator.public,
 * accounts.key (32 random bytes as 64 hex characters).
 */
import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { generateKeyPair } from "../src/core/crypto.js";

const dir = process.argv[2];
if (!dir) throw new Error("usage: staging-keys.ts <dir>");
mkdirSync(dir, { recursive: true, mode: 0o700 });
const put = (name: string, value: string) => writeFileSync(join(dir, name), value, { mode: 0o600 });
const log = await generateKeyPair();
const operator = await generateKeyPair();
put("log.private", log.privateKey);
put("log.public", log.publicKey);
put("operator.private", operator.privateKey);
put("operator.public", operator.publicKey);
put("accounts.key", [...crypto.getRandomValues(new Uint8Array(32))].map((b) => b.toString(16).padStart(2, "0")).join(""));
process.stdout.write(`staging-keys: five files in ${dir}; public halves ${log.publicKey.slice(0, 20)}… (log) and ${operator.publicKey.slice(0, 20)}… (operator)\n`);
