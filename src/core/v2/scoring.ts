/**
 * Track record (Ecdysis v2; design §6): the scientific process identifies
 * bad actors over time.
 *
 * Every evidential report i on claim c moved c's credence from p to p′ when
 * it was filed. When c resolves (T = 1 established, T = 0 refuted, each
 * judged WITHOUT report i, so no report ever resolves itself), report i is
 * credited by the Brier score used as a market scoring rule (Hanson 2003):
 *
 *   C_i = S(p′, T) − S(p, T),   S(x, T) = −(x − T)².
 *
 * Theorem 2. If credence is calibrated, (a) reporting a success without
 * doing the work has expected credit −(p′ − p)² < 0; (b) an honest report
 * that moves credence to the Bayesian posterior has expected credit
 * E[(p′ − p)²] > 0. (a): with T ~ Bern(p), E[(p − T)² − (p′ − T)²] =
 * −(p′ − p)². (b): for p′ = E[T | outcome], E[(p − T)²] = E[(p′ − p)²] +
 * E[(p′ − T)²], martingale increments being orthogonal. ∎ Lying and sloppy
 * work are penalised alike; intent never has to be established.
 *
 * An agent's reliability is ω = σ(ΣC/κ): ½ with no record, towards 1 with
 * a good one, towards 0 with a bad one. A lapse (a committed check never
 * reported) costs a little. Proven fabrication sets ω to 0.
 *
 * Speed limit: a report's credit has mean ∓δ² but standard deviation
 * 2δ√(p(1 − p)), so telling a liar from an honest agent takes about
 * 2z²p(1 − p)/δ² resolved reports. This is the slow, universal net;
 * receipts are the fast, provable one.
 */

import {
  clampLogOdds,
  computeCredenceV2,
  familyCount,
  logit,
  sigma,
  statusOf,
  sumEvidence,
  thresholdOf,
  type ClaimInput,
  type ClaimV2,
  type EvidenceInput,
  type UseInput,
} from "./credence.js";

export const TRACK_VERSION = "track/0.1";

export const TRACK_PARAMS = {
  /**
   * Scale of the reliability logistic: ΣC = κ moves ω from ½ to 0.73. One
   * report's credit is typically 0.01 to 0.25, so weight moves over tens of
   * resolved reports, as the speed limit says it must, and one honest dissent
   * that turns out wrong costs little.
   */
  kappa: 1,
  /** What a lapse costs: about one wrong report, so committing and then hiding a failure never pays. */
  lapse: 0.1,
} as const;

export interface ScoredReport {
  id: string;
  agent: string;
  claim: string;
  seq: number;
  /** The claim's credence just before and just after this report. */
  before: number;
  after: number;
  /** The claim's resolution without this report: 1 established, 0 refuted, null not yet. */
  resolved: 0 | 1 | null;
  credit: number;
}

export interface TrackRecord {
  reports: ScoredReport[];
  /** Per agent: Σ credit, less lapses. */
  credit: Map<string, number>;
  /** Per agent: ω. */
  reliability: Map<string, number>;
}

export interface TrackOptions {
  vouchLinked?: (a: string, b: string) => boolean;
  ringLinked?: (a: string, b: string) => boolean;
  /** Agents under a fabrication finding in force: their evidence weighs nothing and their ω is 0. */
  fabricators?: Set<string>;
  /**
   * Operators under a finding in force (Daniel, 2 Oct: voiding reaches the
   * operator's other evidence). Every item from these operators weighs
   * nothing; the appeal period and reversibility live in the log, not here.
   */
  voidedOperators?: Set<string>;
  /** Committed checks never reported, per agent. */
  lapses?: Map<string, number>;
  /**
   * Canaries revealed (design §7): claims whose truth is known from outside
   * the record. Every report on an anchored claim is scored against that
   * truth, whatever the evidence on the record says; while a canary is live
   * nothing marks it, so it is scored like any other claim until then.
   */
  anchors?: Map<string, boolean>;
}

/** The improvement a move from p to p′ made, once the truth T is known. */
export function marketCredit(before: number, after: number, t: 0 | 1): number {
  return (before - t) ** 2 - (after - t) ** 2;
}

export function reliabilityOf(credit: number): number {
  return sigma(credit / TRACK_PARAMS.kappa);
}

/**
 * Score every report against its claim's leave-one-out resolution, using
 * the neutral pass (every reporter at ω0) so the moves don't depend on the
 * reliabilities they are about to determine.
 */
export function scoreTrackRecord(
  claims: ClaimInput[],
  evidence: EvidenceInput[],
  neutral: Map<string, ClaimV2>,
  o: TrackOptions = {},
): TrackRecord {
  const voided = (e: EvidenceInput) => !!o.fabricators?.has(e.agent) || !!o.voidedOperators?.has(e.operatorId);
  const opts = { vouchLinked: o.vouchLinked, ringLinked: o.ringLinked, voided };
  const byClaim = new Map<string, EvidenceInput[]>();
  for (const e of evidence) byClaim.set(e.claim, [...(byClaim.get(e.claim) ?? []), e]);
  const reports: ScoredReport[] = [];
  for (const c of claims) {
    const r = neutral.get(c.ref);
    if (!r) continue;
    const items = (byClaim.get(c.ref) ?? []).filter((e) => !voided(e)).sort((a, b) => a.seq - b.seq);
    const base = logit(r.prior);
    const foundationRefuted = r.foundations.some((x) => x.status === "refuted");
    for (const [k, item] of items.entries()) {
      const prefix = items.slice(0, k);
      const before = sigma(clampLogOdds(base + sumEvidence(prefix, c.authorOperator, opts).sum));
      const after = sigma(clampLogOdds(base + sumEvidence([...prefix, item], c.authorOperator, opts).sum));
      // Leave-one-OPERATOR-out: the resolution a report is scored against leaves out everything its operator filed on the
      // claim, so an operator cannot resolve its own report by filing a second one that stands in for the first.
      const without = sumEvidence(items.filter((e) => e.operatorId !== item.operatorId), c.authorOperator, opts);
      // Resolved against the bar at zero use (τ0), never τ(U): use raises the bar a claim must clear to READ established,
      // but a citation must not change what anyone's report is scored against (use never moves credence; §2).
      const status = statusOf({
        credence: sigma(clampLogOdds(base + without.sumVerified)), s: without.s, f: without.f, threshold: thresholdOf(0),
        confirmingReplication: without.confirmingReplication, failingReplication: without.failingReplication,
        confirmingFamilies: familyCount(without.confirmingFamilies), confirmingOperators: without.confirmingOperators,
        foundationRefuted,
      });
      const anchor = o.anchors?.get(c.ref);
      const resolved: 0 | 1 | null = anchor !== undefined ? (anchor ? 1 : 0) : status === "established" ? 1 : status === "refuted" ? 0 : null;
      reports.push({
        id: item.id, agent: item.agent, claim: c.ref, seq: item.seq, before, after, resolved,
        credit: resolved === null ? 0 : marketCredit(before, after, resolved),
      });
    }
  }
  const credit = new Map<string, number>();
  for (const rep of reports) credit.set(rep.agent, (credit.get(rep.agent) ?? 0) + rep.credit);
  for (const [agent, n] of o.lapses ?? []) credit.set(agent, (credit.get(agent) ?? 0) - n * TRACK_PARAMS.lapse);
  const reliability = new Map<string, number>();
  for (const [agent, cr] of credit) reliability.set(agent, o.fabricators?.has(agent) ? 0 : reliabilityOf(cr));
  for (const agent of o.fabricators ?? []) reliability.set(agent, 0);
  return { reports, credit, reliability };
}

/**
 * The whole v2 computation: a neutral pass, the track record it yields,
 * then credence with every reporter weighed by its record. Deterministic.
 */
export function computeV2(
  claims: ClaimInput[],
  evidence: EvidenceInput[],
  uses: UseInput[],
  o: TrackOptions = {},
): { claims: Map<string, ClaimV2>; track: TrackRecord } {
  const voided = (e: EvidenceInput) => !!o.fabricators?.has(e.agent) || !!o.voidedOperators?.has(e.operatorId);
  const neutral = computeCredenceV2(claims, evidence, uses, { vouchLinked: o.vouchLinked, ringLinked: o.ringLinked, voided });
  const track = scoreTrackRecord(claims, evidence, neutral, o);
  const weighed = computeCredenceV2(claims, evidence, uses, {
    vouchLinked: o.vouchLinked, ringLinked: o.ringLinked, voided,
    reliability: (a) => track.reliability.get(a) ?? 0.5,
  });
  return { claims: weighed, track };
}
