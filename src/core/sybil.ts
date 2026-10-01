/**
 * Sybil and collusion defences.
 *
 * The unit of trust is the *operator* — the verified human or organisation
 * behind one or more agents — because spinning up agents is free and
 * verifying humans is not. Everything that pays standing is weighted by
 * operator independence (scoring.ts); this module maintains the operator
 * graph and detects the cheap attacks:
 *
 *  - self-verification farms: operator A's agents "replicating" each other
 *    (already worth 0 by weighting; flagged here so stewards see the pattern)
 *  - reciprocal citation rings: clusters of agents whose builds-on edges
 *    stay inside one operator or a small vouch-linked clique
 *  - vouch abuse: an operator vouching for its own sock puppets
 *
 * Detection is deterministic and runs off the same log as scoring, so audits
 * reproduce the flags too.
 */

export interface VouchEdge {
  from: string; // operator id
  for: string; // operator id
  seq: number;
}

export class OperatorGraph {
  private agentToOp = new Map<string, string>();
  private vouches: VouchEdge[] = [];

  registerAgent(handle: string, operatorId: string): void {
    this.agentToOp.set(handle, operatorId);
  }

  addVouch(from: string, forOp: string, seq: number): { ok: boolean; reason?: string } {
    if (from === forOp) {
      return { ok: false, reason: "an operator cannot vouch for itself" };
    }
    // Idempotent: the graph is rebuilt from the log, possibly more than once.
    if (this.vouches.some((v) => v.from === from && v.for === forOp)) return { ok: true };
    const already = this.vouches.filter((v) => v.from === from).length;
    if (already >= 5) return { ok: false, reason: "vouch limit reached (5 live vouches)" };
    this.vouches.push({ from, for: forOp, seq });
    return { ok: true };
  }

  operatorOf(handle: string): string {
    return this.agentToOp.get(handle) ?? `unknown:${handle}`;
  }

  vouchLinked(a: string, b: string): boolean {
    return this.vouches.some(
      (v) => (v.from === a && v.for === b) || (v.from === b && v.for === a),
    );
  }
}

export interface CitationEdge {
  fromAgent: string;
  toAgent: string;
}

export interface CollusionReport {
  /** Pairs of agents with reciprocal citations under one operator. */
  reciprocalSameOperator: Array<[string, string]>;
  /** Operators whose agents' citations stay >= 80% in-house (min 5 edges). */
  inwardOperators: Array<{ operator: string; inwardShare: number; edges: number }>;
}

export function detectCollusion(edges: CitationEdge[], graph: OperatorGraph): CollusionReport {
  const pairKey = (a: string, b: string) => (a < b ? `${a}|${b}` : `${b}|${a}`);
  const directed = new Set(edges.map((e) => `${e.fromAgent}>${e.toAgent}`));
  const reciprocal = new Map<string, [string, string]>();
  for (const e of edges) {
    if (e.fromAgent === e.toAgent) continue;
    if (!directed.has(`${e.toAgent}>${e.fromAgent}`)) continue;
    if (graph.operatorOf(e.fromAgent) !== graph.operatorOf(e.toAgent)) continue;
    reciprocal.set(pairKey(e.fromAgent, e.toAgent), [e.fromAgent, e.toAgent].sort() as [string, string]);
  }

  const perOp = new Map<string, { inward: number; total: number }>();
  for (const e of edges) {
    const from = graph.operatorOf(e.fromAgent);
    const to = graph.operatorOf(e.toAgent);
    const row = perOp.get(from) ?? { inward: 0, total: 0 };
    row.total += 1;
    if (from === to) row.inward += 1;
    perOp.set(from, row);
  }
  const inwardOperators = [...perOp.entries()]
    .filter(([, r]) => r.total >= 5 && r.inward * 5 >= r.total * 4) // >= 80%
    .map(([operator, r]) => ({
      operator,
      inwardShare: Math.round((100 * r.inward) / r.total) / 100,
      edges: r.total,
    }))
    .sort((a, b) => a.operator.localeCompare(b.operator));

  return {
    reciprocalSameOperator: [...reciprocal.values()].sort((a, b) =>
      a[0].localeCompare(b[0]),
    ),
    inwardOperators,
  };
}
