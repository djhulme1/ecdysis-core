/**
 * Verify, don't trust: rebuild the record from the public log and check
 * what the server publishes. Pure over a `getJson` you supply, so the same
 * code runs from a script against a live deployment and from a test against
 * the router.
 *
 * 1. The log: every entry chains to the one before; every payload hashes to
 *    what its entry commits to (except an item whose words a steward has
 *    taken out of view, which is counted and named); the Merkle root over
 *    the entries matches the signed tree head; and the head's signature
 *    verifies with the log's public key, when one is given.
 * 2. The numbers: every claim's credence, status, use and dispute,
 *    recomputed by the published rules from nothing but those entries, must
 *    equal what GET /v2/credence serves.
 */
import { canonicalBytes, hashJson, toHex, type Json } from "../../core/canonical.js";
import { leafHash, merkleRoot } from "../../core/merkle.js";
import { TransparencyLog, type LogEntry, type SignedTreeHead } from "../../core/log.js";
import { CREDENCE_V2_VERSION } from "../../core/v2/credence.js";
import { isHeld, V2_ENTRY_TYPES, type V2Entry, type V2EntryType } from "../../core/v2/flow.js";
import { resolveV2 } from "../../core/v2/resolve.js";

/** One public entry, as GET /v2/log/entries serves it. */
export interface PublicEntry { seq: number; ts: string; type: string; payloadHash: string; prevHash: string; entryHash: string; payload: Record<string, unknown> }
export interface RecomputeV2Report {
  entries: number;
  /** Entries whose words a steward has taken out of view: chained and in the tree, their payload hash not checkable from what is shown. */
  withheld: number;
  /** "signature verifies", "unsigned (no key given)", "served without a signature", or the failure. */
  head: string;
  compared: number;
  /** Everything that did not hold: the log's integrity first, then the numbers. Empty when everything recomputes. */
  mismatches: string[];
  agents: number;
  receipts: number;
  findings: number;
  voided: number;
}

/** A log read in full and checked: its head, its entries as served, and everything that did not hold. */
export interface VerifiedLog {
  sth: SignedTreeHead & { signature?: string };
  /** Every entry served, in order (possibly more than the head covers, when the log grew while it was read). */
  entries: PublicEntry[];
  withheld: number;
  head: string;
  mismatches: string[];
}

/**
 * Part 1 alone: read a log's head and every entry from `prefix` (/v2/log on this code; an earlier record's deployment may
 * serve its log elsewhere), and check the chain, the payload hashes, the Merkle root against the head, and the head's
 * signature when a key is given. Used by recomputeV2 and by the export of a record (scripts/export-record.ts).
 */
export async function verifyLog(getJson: <T>(path: string) => Promise<T>, o: { prefix?: string; publicKey?: string | null } = {}): Promise<VerifiedLog> {
  const prefix = o.prefix ?? "/v2/log";
  const mismatches: string[] = [];
  const sth = await getJson<SignedTreeHead & { signature?: string }>(`${prefix}/sth`);
  const served: PublicEntry[] = [];
  for (let from = 0; ;) {
    const page = await getJson<{ entries: PublicEntry[]; next: number | null }>(`${prefix}/entries?from=${from}&limit=200`);
    served.push(...page.entries);
    if (page.next === null || page.entries.length === 0) break;
    from = page.next;
  }
  let withheld = 0;
  let prev = "0".repeat(64);
  for (const [i, e] of served.entries()) {
    if (e.seq !== i) { mismatches.push(`log: entry ${i} is out of order (seq ${e.seq})`); break; }
    const entry: LogEntry = { seq: e.seq, ts: e.ts, type: e.type as LogEntry["type"], payloadHash: e.payloadHash, prevHash: e.prevHash };
    if (e.prevHash !== prev) mismatches.push(`log: entry ${e.seq}'s prevHash does not chain to entry ${e.seq - 1}`);
    const eh = await hashJson(entry as unknown as Json);
    if (eh !== e.entryHash) mismatches.push(`log: entry ${e.seq}'s entryHash does not match its fields`);
    prev = eh;
    // A steward's withholding blanks an item's words and says so in the payload: that payload cannot hash to the commitment.
    if (e.payload && typeof e.payload === "object" && "withheld" in e.payload) withheld += 1;
    else if ((await hashJson(e.payload as Json)) !== e.payloadHash) mismatches.push(`log: entry ${e.seq} (${e.type})'s payload does not hash to its payloadHash`);
  }
  if (sth.treeSize > served.length) mismatches.push(`log: the signed tree head covers ${sth.treeSize} entries but only ${served.length} were served`);
  else {
    const leaves: Uint8Array[] = [];
    for (const e of served.slice(0, sth.treeSize)) leaves.push(await leafHash(canonicalBytes({ seq: e.seq, ts: e.ts, type: e.type, payloadHash: e.payloadHash, prevHash: e.prevHash } as unknown as Json)));
    const root = toHex(await merkleRoot(leaves));
    if (root !== sth.rootHash) mismatches.push(`log: the Merkle root over ${sth.treeSize} entries is ${root}, but the signed tree head says ${sth.rootHash}`);
  }
  let head = "unsigned (no key given)";
  if (o.publicKey && sth.signature) {
    head = (await TransparencyLog.verifySth(o.publicKey, sth as SignedTreeHead)) ? "signature verifies" : "SIGNATURE DOES NOT VERIFY";
    if (head !== "signature verifies") mismatches.push("log: the signed tree head's signature does not verify with the log's public key");
  } else if (o.publicKey) head = "served without a signature";
  return { sth, entries: served, withheld, head, mismatches };
}

export async function recomputeV2(getJson: <T>(path: string) => Promise<T>, now: Date = new Date(), o: { publicKey?: string | null } = {}): Promise<RecomputeV2Report> {
  // --- 1. the log ---------------------------------------------------------
  const { entries: served, withheld, head, mismatches } = await verifyLog(getJson, { publicKey: o.publicKey ?? null });

  // --- 2. the numbers -----------------------------------------------------
  const types = new Set<string>(V2_ENTRY_TYPES);
  const entries: V2Entry[] = served.filter((e) => types.has(e.type)).map((e) => ({ seq: e.seq, ts: e.ts, type: e.type as V2EntryType, payload: e.payload }));
  const { record: r, scores: s } = resolveV2(entries, now);
  const credence = await getJson<{ version: string; claims: Array<{ ref: string; credence: number; status: string; use: number; dispute: number }> }>("/v2/credence");
  if (credence.version !== CREDENCE_V2_VERSION) throw new Error(`server speaks ${credence.version}, this code ${CREDENCE_V2_VERSION}`);
  const near = (a: number, b: number) => Math.abs(a - b) <= 1e-6;
  const mine = new Map([...s.claims.values()].map((c) => [c.ref, c] as const));
  for (const c of credence.claims) {
    const m = mine.get(c.ref);
    if (!m) { mismatches.push(`${c.ref}: served but not derivable from the log`); continue; }
    if (!near(m.credence, c.credence) || m.status !== c.status || m.use !== c.use || !near(m.dispute, c.dispute)) {
      mismatches.push(`${c.ref}: served credence ${c.credence} status ${c.status} use ${c.use} dispute ${c.dispute}; recomputed ${m.credence.toFixed(6)} ${m.status} ${m.use} ${m.dispute.toFixed(6)}`);
    }
  }
  // A claim out of view (held under R1, or withheld by a steward, both on the log) is served nowhere, by design.
  for (const ref of mine.keys()) if (!credence.claims.some((c) => c.ref === ref) && !isHeld(r, ref)) mismatches.push(`${ref}: derivable from the log but not served`);
  return {
    entries: served.length, withheld, head, compared: credence.claims.length, mismatches,
    agents: r.agents.size, receipts: [...r.checks.values()].filter((c) => c.stage === "resulted").length, findings: r.findings.length, voided: r.voidedOperators.size,
  };
}
