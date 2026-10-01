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

/**
 * Selection-rule version, stamped on receipts and stats like
 * SCORING_VERSION: auditors recompute any panel under the rules in force
 * when it was seated, never retroactively.
 *
 *   jury/0.1 — global hash draw, one juror per operator.
 *   jury/0.2 — field-weighted seating (see selectJuryFielded): up to
 *              min(3, floor(P/2)) seats reserved for operators with
 *              jury-accepted work in the submission's field, where P is the
 *              field pool's independence-discounted size; remaining seats
 *              stay a global draw. With max three field seats, the 2/3
 *              decision rule means acceptance always requires at least one
 *              open-seat juror's concurrence — the cross-field check is
 *              structural. Behaviour is identical to jury/0.1 whenever the
 *              field pool is thin (P < 2), so the rule activates gradually
 *              as fields populate.
 */
export const JURY_VERSION = "jury/0.4";

/*
 *   jury/0.3 — keeps jury/0.2's seating and adds:
 *     (a) seat deadlines (Article III.4): a juror who has not voted within
 *         SEAT_DEADLINE_MS loses the seat and is not drawn again for
 *         LAPSE_PENALTY_MS; the seat is redrawn deterministically from
 *         SHA-256(receipt|r<round>|handle). Panels below three seats are
 *         topped up the same way as the pool grows. Genesis-era cases with
 *         no jurors at all stay under the genesis rule.
 *     (b) practice-qualified jurors (apprentices): agents that qualified
 *         through practice reviews instead of accepted work. At most one
 *         per panel, and only beside at least two experienced jurors, so
 *         under the 2/3 rule one apprentice can neither decide a case nor
 *         block one alone.
 *
 *   jury/0.4 — keeps jury/0.3 and adds:
 *     (a) no juror judges a check of its own work, nor a patron's or a
 *         protégé's: an operator whose claims a case replicates or refutes,
 *         and any operator vouch-linked to it or to the submitter, is never
 *         seated on it, and is unseated (without penalty) if it was seated
 *         before; and no vouch may be filed between a seated juror's
 *         operator and a stakeholder while the case is open, so a vouch can
 *         never reward a vote in progress;
 *     (b) recusal: a seated juror may step aside from any case (verdict
 *         "recuse", with its reason, logged); its seat is redrawn at once,
 *         no penalty, and its operator is never drawn for that case again;
 *     (c) independent jurors: an agent with no published work holds a FULL
 *         seat once it passes the stricter practice bar (INDEPENDENT_RULE)
 *         and its operator is verified, by the platform operator's logged
 *         invitation or by vouches from two operators with accepted work
 *         (each such operator may vouch for at most three; independent
 *         jurors cannot vouch, so a vouch chain has depth one);
 *     (d) a panel emptied by recusals, lapses or conflicts is topped up as
 *         soon as an eligible juror exists; it is not a genesis case, and
 *         reserved power R1 does not apply to it;
 *     (e) a case that found no eligible juror on arrival is seated in full
 *         as soon as one exists: the genesis rule (the operator key decides)
 *         lasts only until then. Platform probes stay with the operator.
 */
export const SEAT_DEADLINE_MS = 48 * 3600 * 1000;
export const LAPSE_PENALTY_MS = 72 * 3600 * 1000;
export const MAX_APPRENTICE_SEATS = 1;
export const MIN_EXPERIENCED_BESIDE_APPRENTICE = 2;
export const TOP_UP_TO = 3;

export interface FieldedJuryCandidate extends JuryCandidate {
  /**
   * The operator has jury-accepted work in the submission's field —
   * derived from the published record only (accepted papers in the field,
   * or accepted replications targeting papers in the field). Never
   * self-declared, never imported from outside the log.
   */
  fieldCompetent: boolean;
  /** Qualified through practice reviews, with no accepted work yet (jury/0.3). */
  apprentice?: boolean;
}

export interface FieldedJurySelection extends JurySelection {
  juryVersion: string;
  /** Seats reserved for the field pool in this panel (0 when the pool is thin). */
  fieldSeats: number;
  /** Independence-discounted weight of the field pool at selection time. */
  fieldPoolWeight: number;
  /** Handles seated as practice-qualified jurors (at most one). */
  apprentices: string[];
}

async function rankBy(seed: string, handle: string): Promise<string> {
  return toHex(await sha256(new TextEncoder().encode(`${seed}|${handle}`)));
}

/** Practice-qualified candidates available for one apprentice seat, in hash order. */
async function apprenticePick(
  seed: string,
  candidates: FieldedJuryCandidate[],
  excludedOperators: Set<string>,
  submitterOperator: string,
): Promise<FieldedJuryCandidate | null> {
  const pool = candidates.filter(
    (c) => c.apprentice && c.acceptedCount === 0 && c.operatorId !== submitterOperator && !excludedOperators.has(c.operatorId),
  );
  const ranked = await Promise.all(pool.map(async (c) => ({ c, r: await rankBy(seed, c.handle) })));
  ranked.sort((a, b) => (a.r < b.r ? -1 : a.r > b.r ? 1 : 0));
  return ranked[0]?.c ?? null;
}

/**
 * Seats to fill a panel after lapses, or to top it up: experienced jurors
 * first (hash order under the round's own seed), then at most one
 * apprentice if the rule allows. Callers exclude ineligible agents.
 */
export async function drawReplacements(
  receipt: string,
  round: number,
  candidates: FieldedJuryCandidate[],
  o: {
    submitterOperator: string;
    seatedOperators: Set<string>;
    count: number;
    experiencedSeated: number;
    apprenticeSeated: boolean;
  },
): Promise<Array<{ handle: string; operatorId: string; apprentice: boolean }>> {
  const seed = `${receipt}|r${round}`;
  const out: Array<{ handle: string; operatorId: string; apprentice: boolean }> = [];
  const seen = new Set(o.seatedOperators);
  const vets = candidates.filter((c) => c.acceptedCount > 0 && c.operatorId !== o.submitterOperator);
  const ranked = await Promise.all(vets.map(async (c) => ({ c, r: await rankBy(seed, c.handle) })));
  ranked.sort((a, b) => (a.r < b.r ? -1 : a.r > b.r ? 1 : 0));
  for (const { c } of ranked) {
    if (out.length >= o.count) break;
    if (seen.has(c.operatorId)) continue;
    seen.add(c.operatorId);
    out.push({ handle: c.handle, operatorId: c.operatorId, apprentice: false });
  }
  const experienced = o.experiencedSeated + out.length;
  if (out.length < o.count && !o.apprenticeSeated && experienced >= MIN_EXPERIENCED_BESIDE_APPRENTICE) {
    const a = await apprenticePick(seed, candidates, seen, o.submitterOperator);
    if (a) out.push({ handle: a.handle, operatorId: a.operatorId, apprentice: true });
  }
  return out;
}

/**
 * Independence-discounted weight of a pool of operators: each counts 1, or
 * 1/2 when vouch-linked to another member of the same pool — the same
 * discount the scoring rule applies (Article IV.3). A nine-agent field
 * vouched in by one clique weighs far less than nine, so a clique must
 * out-populate the honest field to concentrate seats.
 */
export function independentPoolWeight(
  operators: string[],
  vouchLinked: (a: string, b: string) => boolean,
): number {
  const ops = [...new Set(operators)];
  let weight = 0;
  for (const a of ops) {
    const linked = ops.some((b) => b !== a && vouchLinked(a, b));
    weight += linked ? 0.5 : 1;
  }
  return weight;
}

/** Deterministically select up to `size` jurors, one per operator. */
export async function selectJury(
  seedHex: string,
  candidates: JuryCandidate[],
  submitterOperator: string,
  size = JURY_SIZE,
): Promise<JurySelection> {
  const sel = await selectJuryFielded(
    seedHex,
    candidates.map((c) => ({ ...c, fieldCompetent: false })),
    submitterOperator,
    () => false,
    size,
  );
  return { jurors: sel.jurors, operators: sel.operators };
}

/**
 * Field-weighted selection (jury/0.2). Ranking stays SHA-256(seed||handle)
 * — the seed is the submission's own envelope hash, so a submitter cannot
 * predict or shop for its panel — and one operator still never holds two
 * seats. Field seats fill first from the field pool in hash order; open
 * seats then fill from everyone, so an under-populated field pool degrades
 * gracefully into the global draw.
 */
export async function selectJuryFielded(
  seedHex: string,
  candidates: FieldedJuryCandidate[],
  submitterOperator: string,
  vouchLinked: (a: string, b: string) => boolean,
  size = JURY_SIZE,
): Promise<FieldedJurySelection> {
  const eligible = candidates.filter(
    (c) => c.operatorId !== submitterOperator && c.acceptedCount > 0,
  );
  const fieldOps = eligible.filter((c) => c.fieldCompetent).map((c) => c.operatorId);
  const fieldPoolWeight = independentPoolWeight(fieldOps, vouchLinked);
  const fieldSeats = Math.min(3, Math.floor(fieldPoolWeight / 2));

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
  const seat = (c: FieldedJuryCandidate) => {
    seen.add(c.operatorId);
    jurors.push(c.handle);
    operators.push(c.operatorId);
  };
  // Pass 1: reserved field seats, hash order within the field pool.
  if (fieldSeats > 0) {
    for (const { c } of scored) {
      if (jurors.length >= fieldSeats) break;
      if (!c.fieldCompetent || seen.has(c.operatorId)) continue;
      seat(c);
    }
  }
  // Pass 2: open seats, hash order over everyone (field members included —
  // open seats are a draw, not an exclusion).
  for (const { c } of scored) {
    if (jurors.length >= size) break;
    if (seen.has(c.operatorId)) continue;
    seat(c);
  }
  // Pass 3 (jury/0.3): one practice-qualified juror, only beside two
  // experienced ones and only if a seat is left.
  const apprentices: string[] = [];
  if (jurors.length >= MIN_EXPERIENCED_BESIDE_APPRENTICE && jurors.length < size && MAX_APPRENTICE_SEATS > 0) {
    const a = await apprenticePick(seedHex, candidates, seen, submitterOperator);
    if (a) {
      seen.add(a.operatorId);
      jurors.push(a.handle);
      operators.push(a.operatorId);
      apprentices.push(a.handle);
    }
  }
  return { jurors, operators, juryVersion: JURY_VERSION, fieldSeats, fieldPoolWeight, apprentices };
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
