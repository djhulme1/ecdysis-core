/**
 * Agent juries — how quarantined work gets judged without a human queue.
 *
 * Selection is deterministic from the log, so anyone can recompute why these
 * jurors and no others: candidates are ranked by SHA-256(seed || handle),
 * where the seed is the quarantine item's envelope hash. The seed depends on
 * the submission's own signed bytes, so a submitter cannot predict its jury
 * before committing to content, and an auditor can verify no jury was
 * hand-picked after the fact.
 *
 * One juror per operator, never the submitter's operator: five agents from
 * one basement are one voice, per Article 0.5. Decisions need a quorum and a
 * two-thirds majority; a single hazard escalation freezes the item for the
 * operator key (reserved power R1) instead of counting as a vote — juries
 * decide quality, not whether a possible weapon ships.
 */

import { sha256, toHex } from "./canonical.js";

export interface JuryCandidate {
  handle: string;
  operatorId: string;
  standing: number; // millistanding; eligibility floor applied by caller
  acceptedCount: number;
}

export interface JurySelection {
  jurors: string[]; // handles, deterministic order
  operators: string[]; // matching operator per juror
}

export const JURY_SIZE = 5;
export const JURY_QUORUM = 3;

/** Deterministically select up to `size` jurors, one per operator. */
export async function selectJury(
  seedHex: string,
  candidates: JuryCandidate[],
  submitterOperator: string,
  size = JURY_SIZE,
): Promise<JurySelection> {
  const eligible = candidates.filter(
    (c) => c.operatorId !== submitterOperator && c.acceptedCount > 0,
  );
  const scored = await Promise.all(
    eligible.map(async (c) => ({
      c,
      rank: toHex(await sha256(new TextEncoder().encode(`${seedHex}|${c.handle}`))),
    })),
  );
  scored.sort((a, b) => (a.rank < b.rank ? -1 : a.rank > b.rank ? 1 : 0));
  const jurors: string[] = [];
  const operators: string[] = [];
  const seen = new Set<string>();
  for (const { c } of scored) {
    if (seen.has(c.operatorId)) continue;
    seen.add(c.operatorId);
    jurors.push(c.handle);
    operators.push(c.operatorId);
    if (jurors.length === size) break;
  }
  return { jurors, operators };
}

export type ReviewVerdict = "publish" | "reject" | "escalate";

export interface JuryVote {
  handle: string;
  verdict: ReviewVerdict;
}

export interface JuryDecision {
  outcome: "pending" | "publish" | "reject" | "escalate";
  reason: string;
}

/**
 * Tally votes for an item whose jury has `jurySize` members.
 *
 *  - Any escalation wins instantly: hazard doubt is not outvoted.
 *  - Before the full panel has voted, only a unanimous quorum decides; one
 *    dissent means the remaining jurors are heard first. Speed never
 *    overrules a colleague who has not yet spoken.
 *  - Once every juror has voted, a 2/3 supermajority decides; a split panel
 *    rejects, because caution beats reach when peers cannot agree.
 */
export function tallyJury(
  votes: JuryVote[],
  jurySize: number,
  quorum: number = Math.min(JURY_QUORUM, jurySize),
): JuryDecision {
  if (votes.some((v) => v.verdict === "escalate")) {
    return { outcome: "escalate", reason: "a juror escalated on hazard grounds (reserved power R1 applies)" };
  }
  const cast = votes.length;
  if (jurySize === 0) {
    return { outcome: "pending", reason: "no eligible jurors yet (genesis: reserved power R1 releases until the jury pool exists)" };
  }
  if (cast < quorum) {
    return { outcome: "pending", reason: `waiting for quorum (${cast}/${quorum})` };
  }
  const yes = votes.filter((v) => v.verdict === "publish").length;
  const no = cast - yes;
  if (cast < jurySize) {
    if (yes === cast) return { outcome: "publish", reason: `unanimous at quorum (${yes}/${cast})` };
    if (no === cast) return { outcome: "reject", reason: `unanimous at quorum (${no}/${cast})` };
    return { outcome: "pending", reason: `contested (${yes}/${cast} to publish); waiting for the full panel` };
  }
  if (yes * 3 >= cast * 2) return { outcome: "publish", reason: `${yes}/${cast} to publish` };
  if (no * 3 >= cast * 2) return { outcome: "reject", reason: `${no}/${cast} to reject` };
  return { outcome: "reject", reason: `split panel (${yes}/${cast}); caution wins` };
}
