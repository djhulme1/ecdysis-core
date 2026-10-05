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
 *
 * Arguments (arguments/0.1) are scored the same way, against their own
 * settlement rather than the claim's: an argument is a forecast about
 * itself (the arguer's `confidence` that it holds, from a neutral ½), and a
 * check is a forecast at checkConfidence (holds) or 1 − checkConfidence
 * (does not), judged against the settlement WITHOUT that checker's operator,
 * so nobody settles their own report. Agents who attack conceptual claims
 * well build a record; agents who file rhetoric build a bad one.
 */

import { ARGUMENT_PARAMS, settleArgument, type ArgumentState, type ClaimArgumentsInput } from "./arguments.js";
import {
  clampLogOdds,
  computeCredenceV2,
  conceptualStatusOf,
  familyCount,
  logit,
  resolutionOf,
  sigma,
  statusOf,
  sumArguments,
  sumEvidence,
  thresholdOf,
  type ClaimInput,
  type ClaimV2,
  type EvidenceInput,
  type EvidenceKind,
  type UseInput,
} from "./credence.js";

export const TRACK_VERSION = "track/0.2";

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
  /** The reporting operator (verification by record counts per operator). Absent on argument reports. */
  operatorId?: string;
  /** replication, rerun or review. Absent on argument reports. */
  kind?: EvidenceKind;
  /** Filed before any verified replication by another operator on the claim: a call made while the record was still open. */
  early?: boolean;
  /** Distinct verified operators whose replications the leave-one-operator-out resolution rests on. */
  resolvers?: number;
  /** A receipt that a verified, independent cross-check matched. */
  crossChecked?: boolean;
}

/**
 * Verification by record (4 October 2026, Daniel: "verified by some function
 * of credence"). An operator that no steward has verified earns the verified
 * tier from what the record shows it did:
 * reports filed EARLY (before any verified replication by another operator
 * on the claim), on claims that then RESOLVED on the replications of at
 * least two verified operators other than itself (the leave-one-operator-out
 * resolution the track record already scores against), enough of them, on
 * enough distinct sources, including receipts that an independent verified
 * cross-check matched (so compute and honesty are in the mix, not only
 * forecasting), and RIGHT often enough (a report is right when its credit
 * is positive: it moved credence towards where the record resolved). No
 * finding in force. Earned verification counts in turn: the newly verified
 * resolve claims that let others earn, so the verified set is the least
 * fixed point of this rule over the steward-verified base (resolve.ts).
 */
export const EARNING_PARAMS = {
  /** Qualifying reports needed. */
  reports: 5,
  /** Of which cross-checked receipts. */
  receipts: 2,
  /** Distinct sources the qualifying reports' claims come from: a human paper for claims registered from it, else the claim itself. */
  sources: 3,
  /** Share of qualifying reports that must be right. */
  right: 0.75,
  /** Verified operators, other than the reporter, whose replications the resolution must rest on. */
  resolvers: 2,
} as const;

export interface EarnedVerification {
  operatorId: string;
  reports: number;
  right: number;
  receipts: number;
  sources: number;
  /** The round of the fixed-point iteration in which the operator earned it (1: against the steward-verified base). */
  round: number;
}

/**
 * The operators that earn verification from these scored reports, given who
 * is verified already. Pure; one pass over the reports.
 */
export function earnedVerification(reports: ScoredReport[], verified: (operatorId: string) => boolean, voidedOperators: Set<string> = new Set(), round = 1, params = EARNING_PARAMS, sourceOf: (claim: string) => string = (c) => c): Map<string, EarnedVerification> {
  const byOperator = new Map<string, ScoredReport[]>();
  for (const r of reports) {
    if (!r.operatorId || verified(r.operatorId) || voidedOperators.has(r.operatorId)) continue;
    if (!r.early || r.resolved === null || (r.resolvers ?? 0) < params.resolvers) continue;
    byOperator.set(r.operatorId, [...(byOperator.get(r.operatorId) ?? []), r]);
  }
  const earned = new Map<string, EarnedVerification>();
  for (const [operatorId, rs] of byOperator) {
    const right = rs.filter((r) => r.credit > 0).length;
    const receipts = rs.filter((r) => r.kind === "replication" && r.crossChecked === true).length;
    const sources = new Set(rs.map((r) => sourceOf(r.claim))).size;
    if (rs.length >= params.reports && receipts >= params.receipts && sources >= params.sources && right >= params.right * rs.length) {
      earned.set(operatorId, { operatorId, reports: rs.length, right, receipts, sources, round });
    }
  }
  return earned;
}

export interface TrackRecord {
  reports: ScoredReport[];
  /** Per agent: Σ credit, less lapses. */
  credit: Map<string, number>;
  /** Per agent: ω. */
  reliability: Map<string, number>;
}

export interface TrackOptions {
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
  /** arguments/0.1: each claim's settled arguments' effects (credence/0.3 applies them). */
  arguments?: Map<string, ClaimArgumentsInput>;
  /** arguments/0.1: every argument with its checks, to score arguers and checkers against each settlement. */
  argumentStates?: ArgumentState[];
}

/**
 * Credit for arguments and their checks (arguments/0.1). An arguer's
 * confidence is scored from ½ against the settlement; each checker's
 * `holds` is scored at checkConfidence against the settlement reached
 * without that checker's operator (leave-one-operator-out), so a check
 * never resolves itself. Disowned reports, open arguments and voided
 * operators score nothing.
 */
export function scoreArguments(args: ReadonlyArray<ArgumentState>, voidedOperators?: Set<string>, fabricators?: Set<string>): ScoredReport[] {
  const out: ScoredReport[] = [];
  const A = ARGUMENT_PARAMS;
  for (const a of args) {
    if (a.status === "open") continue;
    const t: 0 | 1 = a.status === "upheld" ? 1 : 0;
    if (!a.disowned && !voidedOperators?.has(a.operatorId) && !fabricators?.has(a.handle)) {
      out.push({ id: a.id, agent: a.handle, claim: a.claim, seq: a.seq, before: 0.5, after: a.confidence, resolved: t, credit: marketCredit(0.5, a.confidence, t) });
    }
    for (const c of a.checks) {
      if (c.disowned || voidedOperators?.has(c.operatorId) || fabricators?.has(c.handle)) continue;
      const without = settleArgument(a.checks.filter((x) => x.operatorId !== c.operatorId));
      if (without.status === "open" || without.status !== a.status) { out.push({ id: c.id, agent: c.handle, claim: a.claim, seq: c.seq, before: 0.5, after: c.holds ? A.checkConfidence : 1 - A.checkConfidence, resolved: null, credit: 0 }); continue; }
      const after = c.holds ? A.checkConfidence : 1 - A.checkConfidence;
      out.push({ id: c.id, agent: c.handle, claim: a.claim, seq: c.seq, before: 0.5, after, resolved: t, credit: marketCredit(0.5, after, t) });
    }
  }
  return out;
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
  const opts = { ringLinked: o.ringLinked, voided };
  const byClaim = new Map<string, EvidenceInput[]>();
  for (const e of evidence) byClaim.set(e.claim, [...(byClaim.get(e.claim) ?? []), e]);
  const reports: ScoredReport[] = [];
  for (const c of claims) {
    const r = neutral.get(c.ref);
    if (!r) continue;
    const items = (byClaim.get(c.ref) ?? []).filter((e) => !voided(e)).sort((a, b) => a.seq - b.seq);
    // Settled arguments are a standing term on the claim's log-odds (credence/0.3): every report is scored on top of it.
    const args = o.arguments?.get(c.ref);
    const argSum = sumArguments(args);
    const base = logit(r.prior) + argSum.verified + argSum.other;
    const foundationRefuted = r.foundations.some((x) => x.status === "refuted");
    for (const [k, item] of items.entries()) {
      const prefix = items.slice(0, k);
      const before = sigma(clampLogOdds(base + sumEvidence(prefix, c.authorOperator, opts).sum));
      const after = sigma(clampLogOdds(base + sumEvidence([...prefix, item], c.authorOperator, opts).sum));
      // Leave-one-OPERATOR-out: the resolution a report is scored against leaves out everything its operator filed on the
      // claim, so an operator cannot resolve its own report by filing a second one that stands in for the first.
      const without = sumEvidence(items.filter((e) => e.operatorId !== item.operatorId), c.authorOperator, opts, c.registrant);
      // Resolved against the bar at zero use (τ0), never τ(U): use raises the bar a claim must clear to READ established,
      // but a citation must not change what anyone's report is scored against (use never moves credence; §2).
      // A conceptual claim resolves by argument (an upheld counterexample), never by replication; its reviews are scored against that.
      // credence/0.4: an empirical claim resolves on its verified replication tests alone, as its status reads them.
      const verifiedBase = logit(r.prior) + argSum.verified;
      const status = r.kind === "conceptual"
        ? conceptualStatusOf(sigma(clampLogOdds(verifiedBase + without.sumVerified)), args, r.cap !== null)
        : statusOf({
          credence: sigma(clampLogOdds(logit(r.prior) + without.replicationSum)), sReplication: without.sReplication, fReplication: without.fReplication, threshold: thresholdOf(0),
          confirmingReplication: without.confirmingReplication, failingReplication: without.failingReplication,
          confirmingFamilies: familyCount(without.confirmingFamilies), confirmingOperators: without.confirmingOperators, failingOperators: without.failingOperators,
          foundationRefuted,
        });
      const resolved = resolutionOf(status, o.anchors?.get(c.ref));
      // Early: nobody verified, other than this operator, had replicated the claim yet when this report was filed.
      const early = !prefix.some((e) => e.tier === "verified" && e.kind !== "review" && e.operatorId !== item.operatorId && e.auditable !== false);
      reports.push({
        id: item.id, agent: item.agent, claim: c.ref, seq: item.seq, before, after, resolved,
        credit: resolved === null ? 0 : marketCredit(before, after, resolved),
        operatorId: item.operatorId, kind: item.kind, early, resolvers: without.replicatingOperators, ...(item.crossChecked ? { crossChecked: true } : {}),
      });
    }
  }
  for (const rep of scoreArguments(o.argumentStates ?? [], o.voidedOperators, o.fabricators)) reports.push(rep);
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
  const neutral = computeCredenceV2(claims, evidence, uses, { ringLinked: o.ringLinked, voided, anchors: o.anchors, arguments: o.arguments });
  const track = scoreTrackRecord(claims, evidence, neutral, o);
  const weighed = computeCredenceV2(claims, evidence, uses, {
    ringLinked: o.ringLinked, voided, anchors: o.anchors, arguments: o.arguments,
    reliability: (a) => track.reliability.get(a) ?? 0.5,
  });
  return { claims: weighed, track };
}
