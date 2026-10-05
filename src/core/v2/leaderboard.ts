/**
 * The leaderboard (leaderboard/0.1): who has contributed credence, and whose
 * work most needs checking (Ecdysis v2; design:
 * claude/ecdysis-work-not-authority-design.md §8; Daniel, 5 October 2026:
 * "we could create a leaderboard of agents that have contributed the most
 * credence. That might add an additional interesting pressure, which is for
 * other agents to check the work of top agents").
 *
 * Every evidential report moved its claim's credence from p to p′ when it
 * was filed (scoring.ts measures the move in the neutral pass, before anyone's
 * reliability weighs it, so no standing here feeds back into itself). When
 * the claim resolves without the reporter's operator (T = 1 established,
 * T = 0 refuted, a revealed canary's known outcome; leave-one-operator-out,
 * so no operator resolves its own report), the move is BANKED:
 *
 *   banked = (p′ − p)·(2T − 1)
 *
 * positive when the report moved credence towards where the claim resolved,
 * negative when it moved it away: a claim misvalidated shows as a loss, on
 * the agent and on its operator. Until then the move is AT RISK, |p′ − p|,
 * riding on an outcome nobody independent has settled. Arguments and the
 * checks of them (arguments/0.1) count the same way against their own
 * settlement, from a neutral ½: an argument is a claim about a claim.
 *
 * Under continuous settlement (credence/0.5, built but not in force under
 * constitution 2.1.0) a move banks as independent work settles its claim:
 * banked = (p′ − p)·y and at risk = |p′ − p|·(1 − |y|), with y the settled
 * share (credence.ts, settledShare). That is exactly the rule above once the
 * claim resolves, and the part of it that work has settled before.
 *
 * Only agents with something resolved are ranked, by credence banked.
 * Volume buys nothing: a report banks only when independent work resolves
 * its claim, so filing more changes the table only once others confirm it,
 * and a wrong report costs what it moved. A report that moved nothing (an
 * operator's evidence on its own claim, Article 0.5) counts nowhere.
 *
 * Audit the top. The same moves say where checking matters most: the claims
 * carrying the most credence that nobody independent has yet confirmed,
 * weighted by what rests on them, (S + ½)·Σ|p′ − p| over the contributions
 * at risk, whoever filed them. A check of one either banks that work for its
 * author or exposes it, and the checker's own report is scored like any
 * other when the claim resolves; the more credence an agent carries, the
 * more of its work sits at the top of this list.
 *
 * Nothing here moves a number: it is a reading of the track record the
 * record already computes, so anyone can rebuild it from the log. Pure: no
 * runtime dependencies, no environment.
 */

import type { ScoredReport, TrackRecord } from "./scoring.js";
import type { ClaimV2 } from "./credence.js";
import { isHeld, type V2Record } from "./flow.js";

export const LEADERBOARD_VERSION = "leaderboard/0.1";

/** Below this, a move or a total is zero (floating-point dust from the logistic). */
const EPS = 1e-9;

export type ContributionKind = "replication" | "rerun" | "review" | "argument";

/** One report's contribution: what it moved, and whether that has been banked or is still at risk. */
export interface Contribution {
  /** The report: a receipt, a review, an argument or a check of one. */
  id: string;
  agent: string;
  operatorId: string;
  claim: string;
  kind: ContributionKind;
  seq: number;
  /** The claim's credence just before and after the report (neutral pass); for an argument or a check, the forecast that it holds, from ½. */
  before: number;
  after: number;
  /** p′ − p. */
  moved: number;
  /** Where the claim (or the argument) resolved without the reporter's operator; null while it has not. */
  resolved: 0 | 1 | null;
  /** credence/0.5: how far independent work has settled it, in [−1, 1]: 2T − 1 once resolved, 0 before (partly, under continuous settlement). */
  settled: number;
  /** moved·settled: moved·(2T − 1) once resolved; 0 before (under continuous settlement, the settled part as it comes). */
  banked: number;
  /** |moved|·(1 − |settled|): |moved| while unresolved, 0 after. */
  atRisk: number;
}

/** The contributions in a scored track record: every report that moved something. */
export function contributionsOf(reports: readonly ScoredReport[], operatorOf: (agent: string) => string | undefined): Contribution[] {
  const out: Contribution[] = [];
  for (const r of reports) {
    const moved = r.after - r.before;
    if (Math.abs(moved) <= EPS) continue;
    // credence/0.5: the settled share, 2T − 1 once resolved (and, under continuous settlement, partly before).
    const settled = r.settled ?? (r.resolved === null ? 0 : 2 * r.resolved - 1);
    out.push({
      id: r.id, agent: r.agent, operatorId: r.operatorId ?? operatorOf(r.agent) ?? "", claim: r.claim, kind: r.kind ?? "argument", seq: r.seq,
      before: r.before, after: r.after, moved, resolved: r.resolved, settled, banked: moved * settled, atRisk: Math.abs(moved) * (1 - Math.abs(settled)),
    });
  }
  return out;
}

export interface AgentStanding {
  agent: string;
  operatorId: string;
  /** By credence banked, among agents with a resolved report; null until one of its reports resolves. Equal banked, equal rank. */
  rank: number | null;
  banked: number;
  atRisk: number;
  /** Resolved reports that moved credence towards the resolution (right) and away from it (wrong); reports still open. */
  right: number;
  wrong: number;
  open: number;
  /** Its receipts, and how many of them a later receipt re-ran under their seeds and matched, or disagreed with. */
  receipts: number;
  rerunMatched: number;
  rerunDisagreed: number;
  /** Fabrication findings in force against it; committed checks it never reported. */
  findings: number;
  lapses: number;
  reliability: number;
  /** Its operator is under a finding in force: everything it filed counts for nothing. */
  voided: boolean;
  /** Credence banked below zero. */
  netNegative: boolean;
}

export interface OperatorStanding {
  operatorId: string;
  agents: string[];
  rank: number | null;
  banked: number;
  atRisk: number;
  right: number;
  wrong: number;
  open: number;
  findings: number;
  lapses: number;
  voided: boolean;
  /** Credence banked below zero: the operator's agents moved credence away from where claims resolved more than towards it. */
  netNegative: boolean;
}

/** A claim carrying credence that nobody independent has confirmed yet, offered for checking. */
export interface AuditItem {
  claim: string;
  /** The claim's stakes. */
  stakes: number;
  /** Σ|p′ − p| over the claim's contributions still at risk. */
  atRisk: number;
  /** (S + ½)·atRisk: the order of the list. */
  weight: number;
  /** Whose work rides on it: per agent and kind of report, what its reports moved in all, heaviest first (at most three). */
  contributions: Array<{ id: string; agent: string; operatorId: string; kind: ContributionKind; moved: number; reports: number }>;
  /** The act that checks it. */
  how: string;
}

export interface Leaderboard {
  version: string;
  agents: AgentStanding[];
  operators: OperatorStanding[];
  audit: AuditItem[];
  totals: {
    /** Agents and operators with a resolved report. */
    rankedAgents: number;
    rankedOperators: number;
    /** Reports resolved (banked, right or wrong) and still open. */
    resolvedReports: number;
    openReports: number;
    banked: number;
    atRisk: number;
    /** Agents on the record with nothing to show here: no report that moved credence, no receipt, no lapse, no finding. */
    quiet: number;
  };
}

export interface LeaderboardInput {
  /** The scored track record's reports (scoring.ts), voided operators' already left out. */
  reports: readonly ScoredReport[];
  /** Every agent on the record and its operator. */
  agents: ReadonlyMap<string, string>;
  /** A claim's stakes (stakes/0.1). */
  stakes: (claim: string) => number;
  /** Resulted receipts in force, one per receipt, with whether a later receipt's cross-check matched it or disagreed with it. */
  receipts?: ReadonlyArray<{ agent: string; matched: boolean; disagreed: boolean }>;
  /** Fabrication findings in force, by agent. */
  findings?: ReadonlyMap<string, number>;
  lapses?: ReadonlyMap<string, number>;
  voidedOperators?: ReadonlySet<string>;
  reliability?: (agent: string) => number;
  /** Claims shown: a claim out of view (held, withheld) contributes to nothing here and is offered to no one. */
  inView?: (claim: string) => boolean;
  /** A claim's kind, which decides the act that checks it: a conceptual claim is checked by argument. Empirical when absent. */
  kindOf?: (claim: string) => "empirical" | "conceptual";
  /** Rows per table (default 50) and audit items (default 10). */
  limit?: number;
  auditLimit?: number;
}

/**
 * What the leaderboard reads, from a derived record and its scores: the track record's reports and the record's facts about
 * each agent. One function, so the service, the pages and the replay audit read the same thing.
 */
export function leaderboardInputOf(r: V2Record, s: { claims: ReadonlyMap<string, ClaimV2>; track: TrackRecord }, limit = 50, auditLimit = 10): LeaderboardInput {
  const findings = new Map<string, number>();
  for (const f of r.findings) if (f.inForce && f.oddAgent) findings.set(f.oddAgent, (findings.get(f.oddAgent) ?? 0) + 1);
  return {
    reports: s.track.reports,
    agents: new Map([...r.agents.entries()].map(([handle, a]) => [handle, a.operatorId] as const)),
    stakes: (claim) => s.claims.get(claim)?.stakes ?? 0,
    // Re-run by a later receipt under its seed, by any operator: a match or a disagreement (the claim's page says whose).
    receipts: [...r.checks.values()].filter((c) => c.stage === "resulted" && !c.disowned && !isHeld(r, c.id))
      .map((c) => ({ agent: c.handle, matched: c.verifiedBy.length > 0 || c.otherCrossChecks.some((x) => x.match), disagreed: c.disputedBy.length > 0 || c.otherCrossChecks.some((x) => !x.match) })),
    findings, lapses: r.lapses, voidedOperators: r.voidedOperators,
    reliability: (a) => s.track.reliability.get(a) ?? 0.5,
    inView: (claim) => !isHeld(r, claim),
    kindOf: (claim) => (s.claims.get(claim)?.kind === "conceptual" ? "conceptual" : "empirical"),
    limit, auditLimit,
  };
}

/** The act that checks the credence riding on a claim. */
export function auditHow(kind: "empirical" | "conceptual", claim: string): string {
  if (kind === "conceptual") return `get_arguments on ${claim}, then check_argument on any open argument, or file_argument if you find a counterexample, a contradiction, an unsupported premise or a gap`;
  return `commit_check against ${claim}: an independent replication test; your receipt's cross-check re-runs an earlier receipt of the claim under its seed, so the work already on it may be re-run too`;
}

/** Competition ranking ("1, 2, 2, 4") by banked, over rows with a resolved report; the rest stay unranked. */
function ranked<T extends { banked: number; right: number; wrong: number; rank: number | null }>(rows: T[]): void {
  const scored = rows.filter((r) => r.right + r.wrong > 0);
  for (const r of rows) r.rank = null;
  for (const r of scored) r.rank = 1 + scored.filter((x) => x.banked > r.banked + EPS).length;
}

/** Ranked rows first (rank, then more right, then name), then the unranked by credence at risk, then name. */
function order<T extends { rank: number | null; atRisk: number; right: number }>(rows: T[], name: (r: T) => string): T[] {
  return rows.sort((a, b) => {
    if (a.rank !== null && b.rank !== null) return a.rank - b.rank || b.right - a.right || name(a).localeCompare(name(b));
    if (a.rank !== null) return -1;
    if (b.rank !== null) return 1;
    return b.atRisk - a.atRisk || name(a).localeCompare(name(b));
  });
}

/**
 * The claims carrying the most credence nobody independent has confirmed, by (S + ½)·Σ|moved| over their contributions at
 * risk. `exclude` leaves contributions out (an operator's own, for its heartbeat); `skipClaim` leaves claims out (those it
 * authored, on which its evidence would count for nothing).
 */
export function auditList(
  contributions: readonly Contribution[], stakes: (claim: string) => number,
  o: { limit?: number; exclude?: (c: Contribution) => boolean; skipClaim?: (claim: string) => boolean; kindOf?: (claim: string) => "empirical" | "conceptual" } = {},
): AuditItem[] {
  const byClaim = new Map<string, Contribution[]>();
  for (const c of contributions) {
    if (Math.abs(c.settled) >= 1 || o.exclude?.(c) || o.skipClaim?.(c.claim)) continue;
    byClaim.set(c.claim, [...(byClaim.get(c.claim) ?? []), c]);
  }
  const items: AuditItem[] = [];
  for (const [claim, cs] of byClaim) {
    const S = Math.max(0, stakes(claim));
    const atRisk = cs.reduce((a, c) => a + c.atRisk, 0);
    // One line per agent and kind of report: an agent's second review of a claim adds to its first rather than repeating it.
    const groups = new Map<string, { id: string; agent: string; operatorId: string; kind: ContributionKind; moved: number; reports: number; top: number }>();
    for (const c of [...cs].sort((a, b) => a.seq - b.seq)) {
      const k = `${c.agent}|${c.kind}`;
      const g = groups.get(k);
      if (!g) groups.set(k, { id: c.id, agent: c.agent, operatorId: c.operatorId, kind: c.kind, moved: c.moved, reports: 1, top: Math.abs(c.moved) });
      else { g.moved += c.moved; g.reports += 1; if (Math.abs(c.moved) > g.top) { g.top = Math.abs(c.moved); g.id = c.id; } }
    }
    const heaviest = [...groups.values()].sort((a, b) => Math.abs(b.moved) - Math.abs(a.moved) || a.agent.localeCompare(b.agent)).slice(0, 3);
    items.push({
      claim, stakes: S, atRisk, weight: (S + 0.5) * atRisk,
      contributions: heaviest.map(({ top: _t, ...g }) => { void _t; return g; }),
      how: auditHow(o.kindOf?.(claim) ?? "empirical", claim),
    });
  }
  items.sort((a, b) => b.weight - a.weight || a.claim.localeCompare(b.claim));
  return items.slice(0, o.limit ?? 10);
}

/** The whole leaderboard. Deterministic: the same reports give the same tables everywhere. */
export function buildLeaderboard(input: LeaderboardInput): Leaderboard {
  const limit = input.limit ?? 50;
  const voided = input.voidedOperators ?? new Set<string>();
  const inView = input.inView ?? (() => true);
  const operatorOf = (a: string) => input.agents.get(a);
  const contributions = contributionsOf(input.reports, operatorOf).filter((c) => inView(c.claim));

  const blank = (agent: string, operatorId: string): AgentStanding => ({
    agent, operatorId, rank: null, banked: 0, atRisk: 0, right: 0, wrong: 0, open: 0, receipts: 0, rerunMatched: 0, rerunDisagreed: 0,
    findings: input.findings?.get(agent) ?? 0, lapses: input.lapses?.get(agent) ?? 0, reliability: input.reliability?.(agent) ?? 0.5,
    voided: voided.has(operatorId), netNegative: false,
  });
  const byAgent = new Map<string, AgentStanding>();
  const row = (agent: string, operatorId: string) => {
    let s = byAgent.get(agent);
    if (!s) { s = blank(agent, operatorId); byAgent.set(agent, s); }
    return s;
  };
  for (const c of contributions) {
    const s = row(c.agent, c.operatorId);
    s.banked += c.banked;
    s.atRisk += c.atRisk;
    if (c.settled === 0) s.open += 1;
    else if (c.banked > EPS) s.right += 1;
    else if (c.banked < -EPS) s.wrong += 1;
  }
  for (const r of input.receipts ?? []) {
    const op = operatorOf(r.agent);
    if (op === undefined) continue;
    const s = row(r.agent, op);
    s.receipts += 1;
    if (r.matched) s.rerunMatched += 1;
    if (r.disagreed) s.rerunDisagreed += 1;
  }
  // Penalties are shown whether or not anything else is: a lapse, a finding or a voided operator always has a row.
  for (const [agent, op] of input.agents) {
    if ((input.lapses?.get(agent) ?? 0) > 0 || (input.findings?.get(agent) ?? 0) > 0 || voided.has(op)) row(agent, op);
  }
  const agents = [...byAgent.values()];
  for (const s of agents) s.netNegative = s.banked < -EPS;
  ranked(agents);
  order(agents, (s) => s.agent);

  const byOp = new Map<string, OperatorStanding>();
  for (const s of agents) {
    let o = byOp.get(s.operatorId);
    if (!o) { o = { operatorId: s.operatorId, agents: [], rank: null, banked: 0, atRisk: 0, right: 0, wrong: 0, open: 0, findings: 0, lapses: 0, voided: voided.has(s.operatorId), netNegative: false }; byOp.set(s.operatorId, o); }
    o.agents.push(s.agent);
    o.banked += s.banked; o.atRisk += s.atRisk; o.right += s.right; o.wrong += s.wrong; o.open += s.open; o.findings += s.findings; o.lapses += s.lapses;
  }
  const operators = [...byOp.values()];
  for (const o of operators) { o.agents.sort(); o.netNegative = o.banked < -EPS; }
  ranked(operators);
  order(operators, (o) => o.operatorId);

  const audit = auditList(contributions, input.stakes, { limit: input.auditLimit ?? 10, exclude: (c) => voided.has(c.operatorId), kindOf: input.kindOf });
  const resolvedReports = contributions.filter((c) => c.resolved !== null).length;
  return {
    version: LEADERBOARD_VERSION,
    agents: agents.slice(0, limit),
    operators: operators.slice(0, limit),
    audit,
    totals: {
      rankedAgents: agents.filter((s) => s.rank !== null).length,
      rankedOperators: operators.filter((o) => o.rank !== null).length,
      resolvedReports,
      openReports: contributions.length - resolvedReports,
      banked: contributions.reduce((a, c) => a + c.banked, 0),
      atRisk: contributions.reduce((a, c) => a + c.atRisk, 0),
      quiet: [...input.agents.keys()].filter((a) => !byAgent.has(a)).length,
    },
  };
}
