/**
 * Verify, don't trust (v2): rebuild the record from the public log and check
 * every credence the server publishes.
 *
 *   npm run recompute:v2                          # the live archive
 *   npm run recompute:v2 -- https://api.example  # any deployment
 *
 * Fetches every log entry (GET /v1/log/entries, paged), derives the v2
 * record (src/core/v2/flow.ts) and computes credence/0.3 and track/0.2
 * (src/core/v2/scoring.ts) from nothing but those entries, then compares
 * GET /v2/credence claim by claim: credence, status, use and dispute must
 * agree. Exits non-zero on any mismatch. The log's own integrity (chain,
 * Merkle root, signed tree head) is what scripts/recompute.ts checks; run
 * both.
 */
import { recomputeV2 } from "../src/api/v2/recompute.js";

const base = (process.argv[2] ?? "https://api.ecdysis.me").replace(/\/+$/, "");
const report = await recomputeV2(async <T>(path: string): Promise<T> => {
  const r = await fetch(`${base}${path}`, { headers: { "x-ecdysis-probe": "1", accept: "application/json" } });
  if (!r.ok) throw new Error(`${path}: HTTP ${r.status}`);
  return (await r.json()) as T;
});
for (const m of report.mismatches) console.error(`MISMATCH ${m}`);
console.log(`read ${report.entries} v2 entries; ${report.compared} claims compared, ${report.mismatches.length} mismatch${report.mismatches.length === 1 ? "" : "es"}; ${report.agents} agents, ${report.receipts} receipts, ${report.findings} findings, ${report.voided} voided operators`);
process.exit(report.mismatches.length ? 1 : 0);
