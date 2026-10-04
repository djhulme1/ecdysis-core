/**
 * Verify, don't trust (v2): rebuild the record from the public log and
 * compare every served credence with the recomputation. Pure over a
 * `getJson` you supply, so the same code runs from a script against a live
 * deployment and from a test against the router.
 */
import { CREDENCE_V2_VERSION } from "../../core/v2/credence.js";
import { deriveV2, isFrozen, V2_ENTRY_TYPES, wordsWithheld, type V2Entry, type V2EntryType } from "../../core/v2/flow.js";
import { TEXT_FIELDS } from "../../core/v2/review.js";
import { computeV2 } from "../../core/v2/scoring.js";

export interface PublicEntry { seq: number; ts: string; type: string; payload: Record<string, unknown>; withheld?: string[] }
export interface RecomputeV2Report { entries: number; compared: number; mismatches: string[]; agents: number; receipts: number; findings: number; voided: number }

export async function recomputeV2(getJson: <T>(path: string) => Promise<T>, now: Date = new Date()): Promise<RecomputeV2Report> {
  // A steward may restore an item between two page reads, so words withheld on one page and an item back in view on a
  // later one can disagree honestly: read the log again, once, before calling it a fault.
  try {
    return await recomputeOnce(getJson, now);
  } catch (e) {
    if (!(e instanceof WithheldWithoutReason)) throw e;
    return recomputeOnce(getJson, now);
  }
}

class WithheldWithoutReason extends Error {}

async function recomputeOnce(getJson: <T>(path: string) => Promise<T>, now: Date): Promise<RecomputeV2Report> {
  const entries: V2Entry[] = [];
  const withheld: V2Entry[] = [];
  const types = new Set<string>(V2_ENTRY_TYPES);
  let from = 0;
  for (;;) {
    const page = await getJson<{ entries: PublicEntry[]; next: number | null }>(`/v1/log/entries?from=${from}&limit=200`);
    for (const e of page.entries) {
      if (!types.has(e.type)) continue;
      // Only the words of a withdrawn (or hidden) item may be withheld (review/0.1); every field a number rests on is public.
      const allowed = TEXT_FIELDS[e.type] ?? [];
      const bad = (e.withheld ?? []).filter((f) => !allowed.includes(f));
      if (bad.length) throw new Error(`entry ${e.seq} (${e.type}) has withheld fields ${bad.join(", ")}: only an item's words may be withheld from a v2 entry, never what a number rests on`);
      entries.push({ seq: e.seq, ts: e.ts, type: e.type as V2EntryType, payload: e.payload });
      if (e.withheld?.length) withheld.push(entries.at(-1)!);
    }
    if (page.next === null || page.entries.length === 0) break;
    from = page.next;
  }
  const r = deriveV2(entries, now);
  // And words may be withheld only from an entry whose item the record itself shows withdrawn or held out of view.
  for (const e of withheld) if (!wordsWithheld(r, e.type, e.payload)) throw new WithheldWithoutReason(`entry ${e.seq} (${e.type}) has withheld words, but the record shows nothing of it withdrawn or held out of view`);
  const s = computeV2(r.claims, r.evidence, r.uses, { vouchLinked: r.vouchLinked, ringLinked: r.ringLinked, voidedOperators: r.voidedOperators, fabricators: r.fabricators, lapses: r.lapses, anchors: r.anchors, arguments: r.argumentEffects, argumentStates: r.argumentsInForce });
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
  // Frozen claims (held under R1, withdrawn from view, or hidden while reviewed) are served nowhere, by design.
  for (const ref of mine.keys()) if (!isFrozen(r, ref) && !served.claims.some((c) => c.ref === ref)) mismatches.push(`${ref}: derivable from the log but not served`);
  return { entries: entries.length, compared: served.claims.length, mismatches, agents: r.agents.size, receipts: [...r.checks.values()].filter((c) => c.stage === "resulted").length, findings: r.findings.length, voided: r.voidedOperators.size };
}
