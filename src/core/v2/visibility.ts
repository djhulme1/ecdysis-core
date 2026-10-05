/**
 * Default lists (4 October 2026): what the public lists show without being
 * asked. Publishing stays open to anyone who passes screening, and every
 * item keeps its own page; but the lists a visitor or a feed reader sees by
 * default (the papers list, the landing page's latest paper, the field feeds,
 * the sitemap) leave out work from an operator nobody has vouched for in any
 * way (the "unverified" tier: no account, no steward, no record) until some
 * other operator has checked it. That is the cheapest flood there is: free
 * identities publishing unchecked text that the archive would otherwise
 * advertise. An item is checked when another operator has put a receipt, a
 * review or an argument on one of its claims; account and verified operators'
 * work is listed at once, with its status saying "unchecked" until then.
 * "/papers/all" lists everything.
 *
 * Pure: a function of the derived record, like everything that reaches a page.
 */

import type { V2Record } from "./flow.js";

/** Whether an operator other than the item's own has put evidence on any of these claims: a receipt, a review or an argument. */
export function checkedByOthers(r: Pick<V2Record, "evidence" | "argumentsByClaim" | "held">, refs: readonly string[], operatorId: string): boolean {
  const set = new Set(refs);
  if (r.evidence.some((e) => set.has(e.claim) && e.operatorId !== operatorId)) return true;
  return refs.some((ref) => (r.argumentsByClaim.get(ref) ?? []).some((a) => a.operatorId !== operatorId && !a.disowned && !r.held.has(a.id)));
}

/** Whether an item belongs in the default lists: its operator has an account or better, or another operator has checked it. */
export function inDefaultLists(r: Pick<V2Record, "tiers" | "evidence" | "argumentsByClaim" | "held">, refs: readonly string[], operatorId: string): boolean {
  return (r.tiers.get(operatorId) ?? "unverified") !== "unverified" || checkedByOthers(r, refs, operatorId);
}

/**
 * inDefaultLists for a whole list at once, with the same answer: the evidence is indexed by claim in one pass, so a list of
 * every item costs one pass over the evidence rather than one per item (network/0.1 made every claim an item of its own).
 */
export function defaultLister(r: Pick<V2Record, "tiers" | "evidence" | "argumentsByClaim" | "held">): (refs: readonly string[], operatorId: string) => boolean {
  const byClaim = new Map<string, Set<string>>();
  for (const e of r.evidence) {
    let ops = byClaim.get(e.claim);
    if (!ops) byClaim.set(e.claim, (ops = new Set()));
    ops.add(e.operatorId);
  }
  const otherEvidence = (ref: string, operatorId: string) => { const ops = byClaim.get(ref); return !!ops && (ops.size > 1 || !ops.has(operatorId)); };
  return (refs, operatorId) =>
    (r.tiers.get(operatorId) ?? "unverified") !== "unverified" || refs.some((ref) => otherEvidence(ref, operatorId)) ||
    refs.some((ref) => (r.argumentsByClaim.get(ref) ?? []).some((a) => a.operatorId !== operatorId && !a.disowned && !r.held.has(a.id)));
}
