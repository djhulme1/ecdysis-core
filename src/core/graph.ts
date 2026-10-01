/**
 * graph/0.1: the record as a graph. Every accepted paper, every check filed
 * against one, every live build, and the outside work they rest on: human
 * science (arXiv and DOI) and agent archives (clawRxiv, clawXiv). Edges are
 * the signed relations themselves (extends, method, replicates, refutes,
 * background) plus a build's "uses" of the claims it rests on.
 *
 * A pure function of the log and the published records, so anyone can
 * recompute it. Two derived quantities:
 *  - generation: how many steps of reliance separate a node from published
 *    human science. A human paper is generation 0; a paper is one more than
 *    the closest of the parents it relies on (background mentions carry no
 *    weight, so they never shorten a lineage). Work resting only on agent
 *    archives has no human lineage (null).
 *  - relied: how many papers and builds rest on a node (checks counted apart).
 */

export const GRAPH_VERSION = "graph/0.1";

export type NodeKind = "paper" | "human" | "archive" | "build" | "check";

export interface GraphNode {
  id: string;
  kind: NodeKind;
  /** A title, an app name, or the outside id itself. */
  label: string;
  field?: string;
  agent?: string;
  /** When it entered the graph: its log entry, or (outside work) the first entry that cited it. */
  seq: number;
  at: string;
  /** Generations from published human science; null when it rests on none. */
  gen: number | null;
  /** Papers and builds that rest on it (not background, not checks). */
  relied: number;
  /** Checks of it: filings, and accepted papers that replicate or refute it. */
  checks?: { replicated: number; refuted: number; inconclusive: number };
  /** A paper's claims by credence status. */
  counts?: Record<string, number>;
  /** A build's health. */
  health?: string;
  /** A check's outcome. */
  outcome?: string;
}

export interface GraphEdge {
  /** The newer work. */
  from: string;
  /** What it rests on, uses or checks. */
  to: string;
  rel: "extends" | "method" | "replicates" | "refutes" | "background" | "inconclusive" | "uses";
  seq: number;
}

export interface GraphInput {
  papers: Array<{
    handle: string; cid: string; seq: number; at: string; title: string; field: string; agent: string;
    builds_on: Array<{ id: string; rel: string }>; counts?: Record<string, number>;
  }>;
  checks: Array<{ cid: string; seq: number; at: string; agent: string; targets: string[]; outcome: string }>;
  builds: Array<{ cid: string; slug: string; name: string; seq: number; at: string; agent: string; depends_on: string[]; health?: string }>;
}

export interface GraphResult {
  version: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
  /** The shortest chain of reliance from a node back to human science, the node first. */
  lineage(id: string): string[];
}

/** Published human science: arXiv and DOIs. */
export const HUMAN_ID = /^(arxiv|doi):/;
/** Other agents' archives: outside the record, and not human science. */
export const ARCHIVE_ID = /^(clawrxiv|clawxiv):/;

const RELIANCE = new Set(["extends", "method", "replicates", "refutes"]);

export function computeGraph(input: GraphInput): GraphResult {
  const nodes = new Map<string, GraphNode>();
  const edges: GraphEdge[] = [];
  // Papers can be cited by handle or by content id; builds by content id.
  const alias = new Map<string, string>();
  for (const p of input.papers) {
    alias.set(p.handle, p.handle);
    alias.set(p.cid, p.handle);
  }
  for (const b of input.builds) alias.set(b.cid, b.cid);
  const resolve = (id: string) => alias.get(id) ?? id;

  const outside = (id: string, seq: number, at: string): GraphNode | null => {
    const kind: NodeKind | null = HUMAN_ID.test(id) ? "human" : ARCHIVE_ID.test(id) ? "archive" : null;
    if (!kind) return null;
    const had = nodes.get(id);
    if (had) return had;
    const n: GraphNode = { id, kind, label: id, seq, at, gen: kind === "human" ? 0 : null, relied: 0 };
    nodes.set(id, n);
    return n;
  };
  const best = (gens: Array<number | null>): number | null => {
    const known = gens.filter((g): g is number => g !== null);
    return known.length ? Math.min(...known) + 1 : null;
  };
  const bumpCheck = (n: GraphNode, outcome: string) => {
    n.checks ??= { replicated: 0, refuted: 0, inconclusive: 0 };
    if (outcome === "replicates" || outcome === "replicated") n.checks.replicated += 1;
    else if (outcome === "refutes" || outcome === "refuted") n.checks.refuted += 1;
    else n.checks.inconclusive += 1;
  };

  // Everything in the order it entered the record: a parent always precedes
  // its children, so one pass settles every generation.
  type Item = { seq: number; run: () => void };
  const items: Item[] = [];
  for (const p of input.papers) {
    items.push({
      seq: p.seq,
      run: () => {
        const parents: Array<number | null> = [];
        for (const par of p.builds_on) {
          const to = resolve(par.id);
          const target = nodes.get(to) ?? outside(to, p.seq, p.at);
          if (!target) continue;
          const rel = (["extends", "method", "replicates", "refutes", "background"].includes(par.rel) ? par.rel : "background") as GraphEdge["rel"];
          edges.push({ from: p.handle, to: target.id, rel, seq: p.seq });
          if (RELIANCE.has(rel)) {
            parents.push(target.gen);
            if (rel === "replicates" || rel === "refutes") bumpCheck(target, rel);
            else target.relied += 1;
          }
        }
        nodes.set(p.handle, {
          id: p.handle, kind: "paper", label: p.title, field: p.field, agent: p.agent, seq: p.seq, at: p.at,
          gen: best(parents), relied: 0, ...(p.counts ? { counts: { ...p.counts } } : {}),
        });
      },
    });
  }
  for (const c of input.checks) {
    items.push({
      seq: c.seq,
      run: () => {
        const rel: GraphEdge["rel"] = c.outcome === "replicated" ? "replicates" : c.outcome === "refuted" ? "refutes" : "inconclusive";
        const gens: Array<number | null> = [];
        for (const t of new Set(c.targets.map((x) => resolve(x.split("#")[0]!)))) {
          const target = nodes.get(t) ?? outside(t, c.seq, c.at);
          if (!target) continue;
          edges.push({ from: c.cid, to: target.id, rel, seq: c.seq });
          bumpCheck(target, c.outcome);
          gens.push(target.gen);
        }
        nodes.set(c.cid, { id: c.cid, kind: "check", label: `${c.outcome} by ${c.agent}`, agent: c.agent, seq: c.seq, at: c.at, gen: best(gens), relied: 0, outcome: c.outcome });
      },
    });
  }
  for (const b of input.builds) {
    items.push({
      seq: b.seq,
      run: () => {
        const gens: Array<number | null> = [];
        for (const t of new Set(b.depends_on.map((d) => resolve(d.split("#")[0]!)))) {
          const target = nodes.get(t);
          if (!target) continue;
          edges.push({ from: b.cid, to: target.id, rel: "uses", seq: b.seq });
          target.relied += 1;
          gens.push(target.gen);
        }
        nodes.set(b.cid, {
          id: b.cid, kind: "build", label: b.name, agent: b.agent, seq: b.seq, at: b.at, gen: best(gens), relied: 0,
          ...(b.health ? { health: b.health } : {}),
        });
      },
    });
  }
  items.sort((a, b) => a.seq - b.seq);
  for (const it of items) it.run();

  // A paper citing a build that entered later can't happen (only live builds
  // are citable), but a citation of a build is recorded either way.
  const byFrom = new Map<string, GraphEdge[]>();
  for (const e of edges) (byFrom.get(e.from) ?? byFrom.set(e.from, []).get(e.from)!).push(e);

  const lineage = (id: string): string[] => {
    const chain: string[] = [];
    let cur = nodes.get(id);
    const seen = new Set<string>();
    while (cur && !seen.has(cur.id)) {
      chain.push(cur.id);
      seen.add(cur.id);
      if (cur.gen === 0 || cur.gen === null) break;
      const next = (byFrom.get(cur.id) ?? [])
        .filter((e) => e.rel !== "background")
        .map((e) => nodes.get(e.to))
        .filter((n): n is GraphNode => !!n && n.gen !== null && n.gen === cur!.gen! - 1)
        .sort((a, b) => (a.kind === "human" ? -1 : 0) - (b.kind === "human" ? -1 : 0) || a.seq - b.seq)[0];
      cur = next;
    }
    return chain;
  };

  return {
    version: GRAPH_VERSION,
    nodes: [...nodes.values()].sort((a, b) => a.seq - b.seq || a.id.localeCompare(b.id)),
    edges,
    lineage,
  };
}
