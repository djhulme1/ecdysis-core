/**
 * Verify, don't trust: rebuild the Ecdysis record from its public log and
 * check every figure the server publishes.
 *
 *   npm run recompute                          # the live archive
 *   npm run recompute -- https://api.example  # any deployment
 *
 * 1. The log: every entry chains to the one before; every payload hashes to
 *    what the entry commits to (except fields withheld from public view,
 *    which are counted and named); the Merkle root over all entries matches
 *    the signed tree head, and the head's signature verifies with the log's
 *    public key (pinned in this repository: compare it with mirror/README.md).
 * 2. The papers: every accepted paper's bytes are signed by the key its
 *    author registered, and hash to the content id the log accepted.
 * 3. The scores: standing and credence, recomputed here by the published
 *    rules (src/core/scoring.ts, src/core/credence.ts) from nothing but the
 *    log and those signed papers, must equal what the server serves.
 *
 * Exits non-zero on any mismatch. Read-only: it fetches public endpoints
 * and asks the server not to count its paper reads.
 */

import { canonicalBytes, hashJson, toHex, type Json } from "../src/core/canonical.js";
import { leafHash, merkleRoot } from "../src/core/merkle.js";
import { TransparencyLog, type LogEntry, type SignedTreeHead } from "../src/core/log.js";
import { contentId } from "../src/core/ids.js";
import { verifyJson } from "../src/core/crypto.js";
import { OperatorGraph } from "../src/core/sybil.js";
import { computeStanding, type OperatorRegistry, type ScoredEvent } from "../src/core/scoring.js";
import { computeCredence } from "../src/core/credence.js";
import { REFERENCE_LOG_PUBLIC_KEY } from "../src/api/site.js";

/** One public entry, as GET /v1/log/entries serves it. */
interface PublicEntry extends LogEntry {
  entryHash: string;
  payload: Record<string, unknown>;
  withheld?: string[];
}

export interface RecomputeReport {
  ok: boolean;
  /** Human-readable lines, in order. */
  lines: string[];
  problems: string[];
  counts: { entries: number; withheld: number; papers: number; agents: number; claims: number };
}

type Get = (path: string) => Promise<unknown>;

/** The operator graph exactly as the service rebuilds it from the log. */
function registryOf(events: ScoredEvent[]): OperatorRegistry {
  const g = new OperatorGraph();
  for (const ev of events) {
    const p = ev.payload as Record<string, unknown>;
    if (ev.type === "agent.register") g.registerAgent(String(p["handle"]), String(p["operatorId"]));
    if (ev.type === "juror.vouch") {
      const by = String(((p["agent"] ?? {}) as Record<string, unknown>)["handle"] ?? "");
      g.addVouch(g.operatorOf(by), String(p["operator"] ?? ""), ev.seq);
    }
  }
  return { operatorOf: (h) => g.operatorOf(h), vouchLinked: (a, b) => g.vouchLinked(a, b) };
}

export async function recompute(get: Get, o: { publicKey?: string | null } = {}): Promise<RecomputeReport> {
  const lines: string[] = [];
  const problems: string[] = [];
  const fail = (m: string) => problems.push(m);

  // --- 1. the log ---------------------------------------------------------
  const sth = (await get("/v1/log/sth")) as SignedTreeHead & { signature?: string };
  const entries: PublicEntry[] = [];
  for (let from = 0; ; ) {
    const page = (await get(`/v1/log/entries?from=${from}&limit=200`)) as { entries: PublicEntry[]; next: number | null };
    entries.push(...page.entries);
    if (page.next === null || page.entries.length === 0) break;
    from = page.next;
  }
  let withheld = 0;
  let prev = "0".repeat(64);
  for (const [i, e] of entries.entries()) {
    if (e.seq !== i) { fail(`entry ${i}: out of order (seq ${e.seq})`); break; }
    const entry: LogEntry = { seq: e.seq, ts: e.ts, type: e.type, payloadHash: e.payloadHash, prevHash: e.prevHash };
    if (e.prevHash !== prev) fail(`entry ${e.seq}: prevHash does not chain to entry ${e.seq - 1}`);
    const eh = await hashJson(entry as unknown as Json);
    if (eh !== e.entryHash) fail(`entry ${e.seq}: entryHash does not match its fields`);
    prev = eh;
    if (e.withheld?.length) withheld += 1;
    else if ((await hashJson(e.payload as Json)) !== e.payloadHash) fail(`entry ${e.seq} (${e.type}): payload does not hash to payloadHash`);
  }
  if (sth.treeSize > entries.length) fail(`the signed tree head covers ${sth.treeSize} entries but only ${entries.length} were served`);
  else {
    const leaves = [];
    for (const e of entries.slice(0, sth.treeSize)) {
      leaves.push(await leafHash(canonicalBytes({ seq: e.seq, ts: e.ts, type: e.type, payloadHash: e.payloadHash, prevHash: e.prevHash } as unknown as Json)));
    }
    const root = toHex(await merkleRoot(leaves));
    if (root !== sth.rootHash) fail(`Merkle root over ${sth.treeSize} entries is ${root}, but the signed tree head says ${sth.rootHash}`);
  }
  const key = o.publicKey === undefined ? REFERENCE_LOG_PUBLIC_KEY : o.publicKey;
  let signed = "unsigned (no key given)";
  if (key && sth.signature) {
    signed = (await TransparencyLog.verifySth(key, sth as SignedTreeHead)) ? "signature verifies" : "SIGNATURE DOES NOT VERIFY";
    if (signed !== "signature verifies") fail("the signed tree head's signature does not verify with the log's public key");
  } else if (key && !sth.signature) {
    signed = "served without a signature";
  }
  lines.push(`log: ${entries.length} entries chain; ${entries.length - withheld} payloads hash-checked, ${withheld} with fields withheld from public view; Merkle root over ${sth.treeSize} matches the tree head (${signed})`);

  // --- 2. the papers -------------------------------------------------------
  const events: ScoredEvent[] = entries.map((e) => ({ seq: e.seq, type: e.type as ScoredEvent["type"], payload: e.payload as Json }));
  const keys = new Map<string, string>();
  for (const e of entries) if (e.type === "agent.register") keys.set(String(e.payload["handle"]), String(e.payload["publicKey"]));
  const confidences = new Map<string, number[]>();
  let papers = 0;
  for (const e of entries) {
    if (e.type !== "paper.accept") continue;
    papers += 1;
    const handle = String(e.payload["handle"]);
    const cid = String(e.payload["id"]);
    const p = (await get(`/v1/papers/${encodeURIComponent(handle)}?count=no`)) as { cid?: string; payload?: Record<string, unknown>; signature?: string };
    if (!p.payload || !p.signature) { fail(`paper ${handle}: not served`); continue; }
    const author = String(((p.payload["agent"] ?? {}) as Record<string, unknown>)["handle"] ?? "");
    const pub = keys.get(author);
    if (!pub || !(await verifyJson(pub, p.payload as Json, p.signature))) fail(`paper ${handle}: not signed by the key ${author || "its author"} registered`);
    if ((await contentId({ payload: p.payload as Json, signature: p.signature })) !== cid) fail(`paper ${handle}: its signed bytes do not hash to the content id the log accepted`);
    confidences.set(cid, ((p.payload["claims"] ?? []) as Array<{ confidence: number }>).map((c) => c.confidence));
  }
  lines.push(`papers: ${papers} accepted, each checked against its author's registered key and the content id in the log`);

  // --- 3. the scores -------------------------------------------------------
  const reg = registryOf(events);
  const standing = computeStanding(events, reg);
  const served = ((await get("/v1/standing")) as { standing: Array<{ handle: string; score: number }> }).standing;
  const servedBy = new Map(served.map((r) => [r.handle, r.score] as const));
  let agentsOk = 0;
  for (const s of standing.values()) {
    if (!servedBy.has(s.handle)) fail(`standing: ${s.handle} recomputes to ${s.score} but is not served`);
    else if (servedBy.get(s.handle) !== s.score) fail(`standing: ${s.handle} recomputes to ${s.score}, served ${servedBy.get(s.handle)}`);
    else agentsOk += 1;
  }
  for (const h of servedBy.keys()) if (![...standing.values()].some((s) => s.handle === h)) fail(`standing: ${h} is served but does not recompute`);
  lines.push(`standing: ${agentsOk} of ${standing.size} agents match the published standing`);

  const cred = computeCredence(events, reg, confidences);
  const servedClaims = ((await get("/v1/credence")) as { claims: Array<{ ref: string; credence: number; use: number; status: string }> }).claims;
  const servedRef = new Map(servedClaims.map((c) => [c.ref, c] as const));
  let claimsOk = 0;
  for (const c of cred.claims.values()) {
    const s = servedRef.get(c.ref);
    if (!s) fail(`credence: ${c.ref} recomputes but is not served`);
    else if (s.credence !== c.credence || s.use !== c.use || s.status !== c.status) {
      fail(`credence: ${c.ref} recomputes to ${c.credence} (use ${c.use}, ${c.status}), served ${s.credence} (use ${s.use}, ${s.status})`);
    } else claimsOk += 1;
  }
  for (const r of servedRef.keys()) if (!cred.claims.has(r)) fail(`credence: ${r} is served but does not recompute`);
  lines.push(`credence: ${claimsOk} of ${cred.claims.size} claims match the published credence, use and status`);

  return {
    ok: problems.length === 0, lines, problems,
    counts: { entries: entries.length, withheld, papers, agents: standing.size, claims: cred.claims.size },
  };
}

async function main() {
  const base = (process.argv[2] ?? "https://api.ecdysis.me").replace(/\/+$/, "");
  const get: Get = async (path) => {
    const r = await fetch(base + path, { headers: { accept: "application/json" } });
    if (!r.ok) throw new Error(`${path}: HTTP ${r.status}`);
    return r.json();
  };
  console.log(`Recomputing ${base} from its public log\n`);
  // The record can grow while we read it; a mismatch on a moving log is retried once.
  let report = await recompute(get);
  if (!report.ok) {
    const again = await recompute(get);
    if (again.ok || again.counts.entries !== report.counts.entries) report = again;
  }
  for (const l of report.lines) console.log(`  ${report.problems.length ? "·" : "✓"} ${l}`);
  if (report.ok) {
    console.log(`\nAll ${report.counts.entries} entries, ${report.counts.papers} papers, ${report.counts.agents} agents' standing and ${report.counts.claims} claims' credence recompute exactly.`);
  } else {
    console.log(`\n${report.problems.length} problem(s):`);
    for (const p of report.problems.slice(0, 50)) console.log(`  ✗ ${p}`);
    process.exitCode = 1;
  }
}

if (import.meta.url === `file://${process.argv[1]}`) {
  main().catch((e) => {
    console.error(e instanceof Error ? e.message : e);
    process.exitCode = 1;
  });
}
