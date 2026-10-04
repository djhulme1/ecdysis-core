/**
 * Verify, don't trust (v2): rebuild the record from the public log and
 * compare every served credence with the recomputation. Pure over a
 * `getJson` you supply, so the same code runs from a script against a live
 * deployment and from a test against the router.
 */
import { CREDENCE_V2_VERSION } from "../../core/v2/credence.js";
import { isHeld, V2_ENTRY_TYPES, type V2Entry, type V2EntryType } from "../../core/v2/flow.js";
import { resolveV2 } from "../../core/v2/resolve.js";

export interface PublicEntry { seq: number; ts: string; type: string; payload: Record<string, unknown>; withheld?: string[] }
export interface RecomputeV2Report { entries: number; compared: number; mismatches: string[]; agents: number; receipts: number; findings: number; voided: number }

export async function recomputeV2(getJson: <T>(path: string) => Promise<T>, now: Date = new Date()): Promise<RecomputeV2Report> {
  const entries: V2Entry[] = [];
  const types = new Set<string>(V2_ENTRY_TYPES);
  let from = 0;
  for (;;) {
    const page = await getJson<{ entries: PublicEntry[]; next: number | null }>(`/v1/log/entries?from=${from}&limit=200`);
    for (const e of page.entries) {
      if (!types.has(e.type)) continue;
      if (e.withheld?.length) throw new Error(`entry ${e.seq} (${e.type}) has withheld fields ${e.withheld.join(", ")}: a v2 entry must be fully public`);
      entries.push({ seq: e.seq, ts: e.ts, type: e.type as V2EntryType, payload: e.payload });
    }
    if (page.next === null || page.entries.length === 0) break;
    from = page.next;
  }
  const { record: r, scores: s } = resolveV2(entries, now);
  const served = await getJson<{ version: string; claims: Array<{ ref: string; credence: number; status: string; use: number; dispute: number }> }>("/v2/credence");
  if (served.version !== CREDENCE_V2_VERSION) throw new Error(`server speaks ${served.version}, this code ${CREDENCE_V2_VERSION}`);
  const near = (a: number, b: number) => Math.abs(a - b) <= 1e-6;
  const mismatches: string[] = [];
  const mine = new Map([...s.claims.values()].map((c) => [c.ref, c] as const));
  for (const c of served.claims) {
    const m = mine.get(c.ref);
    if (!m) { mismatches.push(`${c.ref}: served but not derivable from the log`); continue; }
    if (!near(m.credence, c.credence) || m.status !== c.status || m.use !== c.use || !near(m.dispute, c.dispute)) {
      mismatches.push(`${c.ref}: served credence ${c.credence} status ${c.status} use ${c.use} dispute ${c.dispute}; recomputed ${m.credence.toFixed(6)} ${m.status} ${m.use} ${m.dispute.toFixed(6)}`);
    }
  }
  // A claim out of view (held under R1, or withheld by a steward, both on the log) is served nowhere, by design.
  for (const ref of mine.keys()) if (!served.claims.some((c) => c.ref === ref) && !isHeld(r, ref)) mismatches.push(`${ref}: derivable from the log but not served`);
  return { entries: entries.length, compared: served.claims.length, mismatches, agents: r.agents.size, receipts: [...r.checks.values()].filter((c) => c.stage === "resulted").length, findings: r.findings.length, voided: r.voidedOperators.size };
}
