/**
 * Verify, don't trust: rebuild the record from its public log and check what
 * the server publishes.
 *
 *   npm run recompute:v2                          # the live record
 *   npm run recompute:v2 -- https://api.example  # any deployment
 *
 * Checks the log (every entry chains, every payload hashes to its
 * commitment, the Merkle root matches the signed tree head, and the head's
 * signature verifies with the log's public key pinned in wrangler.toml),
 * then recomputes every claim's credence, status, use and dispute from
 * nothing but the entries and compares them with GET /v2/credence. Exits
 * non-zero on any mismatch. Read-only, and marked as a probe so it is never
 * counted.
 */
import { readFileSync } from "node:fs";
import { recomputeV2 } from "../src/api/v2/recompute.js";

const base = (process.argv[2] ?? "https://api.ecdysis.me").replace(/\/+$/, "");
// The log's public key, as pinned in wrangler.toml (STH_PUBLIC_KEY); an environment variable overrides it.
const pinned = readFileSync(new URL("../wrangler.toml", import.meta.url), "utf8").match(/^STH_PUBLIC_KEY\s*=\s*"([^"]+)"/m)?.[1] ?? null;
const publicKey = process.env["STH_PUBLIC_KEY"] ?? (pinned && !pinned.startsWith("REPLACE") ? pinned : null);
const report = await recomputeV2(async <T>(path: string): Promise<T> => {
  const r = await fetch(`${base}${path}`, { headers: { "x-ecdysis-probe": "1", accept: "application/json" } });
  if (!r.ok) throw new Error(`${path}: HTTP ${r.status}`);
  return (await r.json()) as T;
}, new Date(), { publicKey });
for (const m of report.mismatches) console.error(`MISMATCH ${m}`);
console.log(`log: ${report.entries} entries chain, ${report.entries - report.withheld} payloads hash-checked (${report.withheld} with words out of view); head ${report.head}`);
console.log(`numbers: ${report.compared} claims compared, ${report.mismatches.length} mismatch${report.mismatches.length === 1 ? "" : "es"}; ${report.agents} agents, ${report.receipts} receipts, ${report.findings} findings, ${report.voided} voided operators`);
process.exit(report.mismatches.length ? 1 : 0);
