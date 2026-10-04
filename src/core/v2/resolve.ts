/**
 * The whole record, resolved: derivation (flow.ts), the numbers (scoring.ts)
 * and verification by record, together.
 *
 * Who is verified decides what resolves; what resolved decides who has
 * earned verification (scoring.ts, earnedVerification). The two are made
 * well-founded by iteration from the steward-verified base: derive and
 * score with the base, add every operator that now meets the rule, derive
 * and score again with them verified, and stop when a round adds nobody.
 * The set only grows within a resolution, so the iteration ends in at most
 * as many rounds as there are operators (in practice two or three), and
 * its result is the least set closed under the rule above the base: the
 * same for everyone who replays the log, because every step is a
 * deterministic function of the entries (constitution 0.4). A finding in
 * force removes an operator from consideration whatever the record showed
 * before it.
 */

import { deriveV2, type V2Entry, type V2Record } from "./flow.js";
import { computeV2, earnedVerification, EARNING_PARAMS, type EarnedVerification, type TrackRecord } from "./scoring.js";
import type { ClaimV2 } from "./credence.js";

export interface ResolvedV2 {
  record: V2Record;
  scores: { claims: Map<string, ClaimV2>; track: TrackRecord };
  /** Operators verified by the record, with what earned it. */
  verifiedByRecord: Map<string, EarnedVerification>;
  /** Rounds of the fixed-point iteration (1 when nobody earned anything). */
  rounds: number;
}

/** A safety stop no honest log reaches: the set grows by at least one operator a round, and operators are finite. */
const MAX_ROUNDS = 64;

export function resolveV2(entries: V2Entry[], now: Date, params = EARNING_PARAMS): ResolvedV2 {
  const earned = new Map<string, EarnedVerification>();
  for (let round = 1; round <= MAX_ROUNDS; round++) {
    const record = deriveV2(entries, now, { verifiedByRecord: new Set(earned.keys()) });
    const scores = scoreRecord(record);
    const verified = (op: string) => record.tiers.get(op) === "verified";
    const newly = earnedVerification(scores.track.reports, verified, record.voidedOperators, round, params);
    // An operator earned earlier but voided since drops out: the derivation above already refused it the tier.
    for (const op of [...earned.keys()]) if (record.voidedOperators.has(op)) earned.delete(op);
    if (newly.size === 0) {
      record.verifiedByRecord = new Map(earned);
      return { record, scores, verifiedByRecord: new Map(earned), rounds: round };
    }
    for (const [op, e] of newly) earned.set(op, e);
  }
  throw new Error("verification by record did not converge");
}

/** The numbers for a derived record, as the service and the audit compute them. */
export function scoreRecord(r: V2Record): { claims: Map<string, ClaimV2>; track: TrackRecord } {
  return computeV2(r.claims, r.evidence, r.uses, {
    vouchLinked: r.vouchLinked, ringLinked: r.ringLinked, voidedOperators: r.voidedOperators, fabricators: r.fabricators,
    lapses: r.lapses, anchors: r.anchors, arguments: r.argumentEffects, argumentStates: [...r.arguments.values()],
  });
}
