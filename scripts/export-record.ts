/**
 * Export a record's log, verified, into the repository: the public copy of a
 * record that is no longer served.
 *
 *   npm run export:record -- --base https://api.ecdysis.me --log /v1/log \
 *     --key MCowBQYDK2VwAyEACQKUaC27eF_XhkCw06IrJJ7eLSW7GtT_IzwaNiNCRPc --out mirror/v2
 *
 * Reads the deployment's signed tree head and every entry under --log, and
 * checks them as recompute does (every entry chains, every payload hashes to
 * its commitment, the Merkle root over the entries the head covers matches
 * the head, and the head's signature verifies with --key). Only then does it
 * write, into --out:
 *
 *   entries.jsonl      the entries the head covers, one per line, as served
 *                      (seq, ts, type, payloadHash, prevHash, entryHash,
 *                      payload), so anyone can recompute the root again;
 *   final-sth.json     the head they were verified against;
 *   sth-history.jsonl  that head appended, after the heads the nightly live
 *                      check mirrored while the record was live (its last
 *                      line is the same head as final-sth.json).
 *
 * Nothing is written when anything fails to verify. Read-only against the
 * deployment, and marked as a probe so it is never counted. Run it again to
 * bring an export up to date: it rewrites entries.jsonl and final-sth.json,
 * and appends the new head only if it differs from the last line.
 *
 * Written for the fresh start of 5 October 2026 (docs/FRESH-START.md), when
 * the record of 3 to 5 October was left behind in its own database and the
 * network of claims began at a new genesis.
 */
import { mkdirSync, readFileSync, writeFileSync, existsSync, appendFileSync } from "node:fs";
import { join } from "node:path";
import { verifyLog } from "../src/api/v2/recompute.js";

function arg(name: string): string | null {
  const i = process.argv.indexOf(`--${name}`);
  return i >= 0 && i + 1 < process.argv.length ? process.argv[i + 1]! : null;
}

function usage(): never {
  console.error("usage: npm run export:record -- --base <url> --log <path prefix> --key <the record's log key, base64url SPKI> --out <directory>");
  process.exit(2);
  throw new Error("unreachable");
}

const base = (arg("base") ?? "https://api.ecdysis.me").replace(/\/+$/, "");
const prefix = (arg("log") ?? "/v2/log").replace(/\/+$/, "");
const key = arg("key") ?? usage();
const out = arg("out") ?? usage();

const report = await verifyLog(async <T>(path: string): Promise<T> => {
  const r = await fetch(`${base}${path}`, { headers: { "x-ecdysis-probe": "1", accept: "application/json" } });
  if (!r.ok) throw new Error(`${path}: HTTP ${r.status}`);
  return (await r.json()) as T;
}, { prefix, publicKey: key });

if (report.head !== "signature verifies") report.mismatches.push(`head: ${report.head}`);
if (report.withheld > 0) report.mismatches.push(`${report.withheld} entries have words out of view: their payloads cannot be checked, so this export would not be whole`);
for (const m of report.mismatches) console.error(`MISMATCH ${m}`);
if (report.mismatches.length) {
  console.error("Nothing was written.");
  process.exit(1);
}

const covered = report.entries.slice(0, report.sth.treeSize);
const sth = { treeSize: report.sth.treeSize, rootHash: report.sth.rootHash, timestamp: report.sth.timestamp, signature: report.sth.signature };
mkdirSync(out, { recursive: true });
writeFileSync(join(out, "entries.jsonl"), covered.map((e) => JSON.stringify({ seq: e.seq, ts: e.ts, type: e.type, payloadHash: e.payloadHash, prevHash: e.prevHash, entryHash: e.entryHash, payload: e.payload })).join("\n") + "\n");
writeFileSync(join(out, "final-sth.json"), JSON.stringify(sth, null, 2) + "\n");
const history = join(out, "sth-history.jsonl");
const last = existsSync(history) ? readFileSync(history, "utf8").trim().split("\n").filter(Boolean).pop() ?? null : null;
const lastHead = last ? (JSON.parse(last) as { treeSize?: number; rootHash?: string }) : null;
if (!lastHead || lastHead.treeSize !== sth.treeSize || lastHead.rootHash !== sth.rootHash) {
  appendFileSync(history, JSON.stringify({ at: new Date().toISOString(), ...sth, signatureVerified: true }) + "\n");
}
const types = new Map<string, number>();
for (const e of covered) types.set(e.type, (types.get(e.type) ?? 0) + 1);
console.log(`exported ${covered.length} entries from ${base}${prefix} to ${out}: the chain holds, every payload hashes to its commitment, the root matches the head, and the head's signature verifies`);
console.log(`head: size ${sth.treeSize}, root ${sth.rootHash}, signed ${sth.timestamp}`);
console.log([...types.entries()].sort((a, b) => b[1] - a[1]).map(([t, n]) => `${t} ${n}`).join(", "));
