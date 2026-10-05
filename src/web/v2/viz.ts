/**
 * The site's figures: how Ecdysis works, the observatory's charts and the
 * knowledge graph. Script-free, like every page. Bar charts and histograms
 * are HTML (a list of rows, a row of columns) so their words stay words at
 * every width and read to a screen reader as the data they are; the graph
 * and the receipt diagram are inline SVG with a title, a description and
 * the same numbers as a table beneath. Every colour is a design token, so a
 * figure reads in both themes; every value is escaped.
 *
 * Marks follow the brand: ink and its greys carry magnitude and identity,
 * the one orange marks what asks for attention (contested, a threshold
 * crossed), refuted is an empty mark with a heavy outline, crossed. Nothing
 * is carried by colour alone: every series is labelled, and the status
 * glyphs are the chips' own. No gradients, as the kit asks.
 *
 * Mock data. While the record is thin, the observatory and the graph show
 * ILLUSTRATIVE figures, so a visitor can see what the record will measure
 * before it has measured it. They are deterministic and fictional (no real
 * paper, agent or source is named), and labelled as such on every figure
 * and at the top of the page; the real counts are always shown beside
 * them. The threshold is MOCK_UNTIL_CLAIMS claims on the record.
 */

import { esc, statusTone } from "../design.js";
import { computeCredenceV2, CREDENCE_V2_VERSION, type ClaimInput, type ClaimStatusV2, type EvidenceInput, type EvidenceKind, type UseInput } from "../../core/v2/credence.js";

/** Below this many claims on the record, the figures are the mock set, labelled. */
export const MOCK_UNTIL_CLAIMS = 20;
/** The most claims the knowledge graph draws; the rest are in the table. */
export const GRAPH_MAX_NODES = 60;

export type Tone = "sound" | "part" | "open" | "risk" | "broken" | "ink" | "mid" | "pale" | "accent";
export const STATUS_GLYPH: Record<string, string> = { established: "●", supported: "◐", unchecked: "○", contested: "◆", refuted: "✕" };
const STATUS_TONE: Record<string, Tone> = { established: "sound", supported: "part", unchecked: "open", contested: "risk", refuted: "broken" };
export const STATUS_ORDER_V2 = ["established", "supported", "unchecked", "contested", "refuted"] as const;

const n = (x: number) => x.toLocaleString("en-GB");
/** Fills for the drawing: refuted is an empty shape with a heavy outline and a ✕ at its centre, as the chips are crossed; unchecked an empty shape with a dashed outline. */
const SVG_FILL: Record<Tone, string> = {
  sound: "var(--ink)", part: "var(--rule)", open: "var(--card)", risk: "var(--accent)", broken: "var(--card)",
  ink: "var(--ink)", mid: "var(--rule)", pale: "var(--line)", accent: "var(--accent)",
};

/** The chip that marks a mock figure. The same words everywhere, so a reader learns them once. */
export const MOCK_CHIP = `<span class="mock" title="Fictional numbers, shown until the record has ${MOCK_UNTIL_CLAIMS} claims">Illustrative · mock data</span>`;

function figure(o: { id: string; title: string; caption: string; body: string; illustrative?: boolean; wide?: boolean; extraClass?: string }): string {
  return `<figure class="fig${o.illustrative ? " illustrative" : ""}${o.wide ? " wide" : ""}${o.extraClass ? ` ${o.extraClass}` : ""}" id="${esc(o.id)}">
<figcaption><span class="fig-title">${esc(o.title)}</span>${o.illustrative ? MOCK_CHIP : ""}<span class="fig-caption">${esc(o.caption)}</span></figcaption>
${o.body}
</figure>`;
}

export interface BarRow { label: string; value: number; tone?: Tone; glyph?: string; href?: string }

/**
 * Horizontal bars as a list: label, bar, value in each row, one scale for
 * all (the longest row, unless `max` is given). The list is the data, so no
 * second table is needed.
 */
export function barChart(o: { id: string; title: string; caption: string; rows: BarRow[]; max?: number; unit?: string; illustrative?: boolean; format?: (v: number) => string }): string {
  const fmt = o.format ?? n;
  const max = Math.max(o.max ?? 0, ...o.rows.map((r) => r.value), 1);
  const rows = o.rows.map((r) => {
    const w = Math.round((1000 * r.value) / max) / 10;
    const label = `${r.glyph ? `<span class="g" aria-hidden="true">${esc(r.glyph)}</span> ` : ""}${esc(r.label)}`;
    return `<li><span class="k">${r.href ? `<a href="${esc(r.href)}">${label}</a>` : label}</span><span class="b"><span class="f ${r.tone ?? "ink"}" style="width:${w}%"></span></span><span class="v">${esc(fmt(r.value))}${o.unit ? esc(o.unit) : ""}</span></li>`;
  }).join("");
  const body = o.rows.length ? `<ul class="bars">${rows}</ul>` : `<p class="small">Nothing to show yet.</p>`;
  return figure({ id: o.id, title: o.title, caption: o.caption, body, illustrative: o.illustrative });
}

/** Claims by status, as bars in the status order with the status glyphs. */
export function statusChart(o: { id: string; statuses: Record<string, number>; illustrative?: boolean; caption?: string }): string {
  const rows: BarRow[] = STATUS_ORDER_V2.map((s) => ({ label: s, value: o.statuses[s] ?? 0, tone: STATUS_TONE[s]!, glyph: STATUS_GLYPH[s]! }));
  return barChart({ id: o.id, title: "Claims by status", caption: o.caption ?? "Statuses come from independent replications only. Established needs confirmation on two declared model families from verified operators.", rows, illustrative: o.illustrative });
}

/**
 * Columns over equal buckets (a histogram), each labelled beneath with the
 * start of its range, the value above the column. Heights are a share of
 * the tallest column, set as a custom property so the label rides on top.
 */
export function histogram(o: { id: string; title: string; caption: string; buckets: number[]; labels: string[]; illustrative?: boolean; tone?: Tone; unit?: string }): string {
  const max = Math.max(...o.buckets, 1);
  const cols = o.buckets.map((v, i) => {
    const h = Math.round((84 * v) / max);
    return `<li style="--h:${h}%"><span class="v">${v ? n(v) : ""}</span><span class="c ${o.tone ?? "ink"}"></span><span class="x">${esc(o.labels[i] ?? "")}</span></li>`;
  }).join("");
  const body = `<ol class="hist" style="--n:${o.buckets.length}" aria-label="${esc(o.title)}">${cols}</ol>
<details><summary>The numbers as a table</summary><table><thead><tr><th>${esc(o.unit ?? "Range")}</th><th>Count</th></tr></thead><tbody>${o.buckets.map((v, i) => `<tr><td>${esc(o.labels[i] ?? "")}</td><td>${n(v)}</td></tr>`).join("")}</tbody></table></details>`;
  return figure({ id: o.id, title: o.title, caption: o.caption, body, illustrative: o.illustrative });
}

/** A number that matters, with the line it must not cross. `warn` marks a number on the wrong side of its line. */
export function statTile(o: { label: string; value: string; note: string; warn?: boolean }): string {
  return `<div class="stat${o.warn ? " warn" : ""}"><span class="stat-v">${esc(o.value)}</span><span class="stat-l">${esc(o.label)}</span><span class="stat-n">${esc(o.note)}</span></div>`;
}

export interface GraphNode {
  id: string; label: string; external: boolean; status: string; use: number; credence: number; gen: number; href?: string; paper: string;
  /** stakes/0.1: use + log2(1 + the source's citations); sets the node's size. Absent: use. */
  stakes?: number;
  /** attempts/0.1: what blocks the claim as it stands (tried, not checkable); drawn as a ⊘ beside the node. */
  blocked?: string[];
}
export interface GraphEdge { from: string; to: string }

/**
 * The knowledge graph: claims as nodes, "rests on" as edges, laid out by
 * generation from left (human literature and roots) to right (what builds
 * on them). Deterministic, so the picture is the same for everyone; the
 * reader's eye does the rest. Node size follows use; shape says external
 * (square) or native (circle); the fill follows the status chips (refuted
 * is an empty shape crossed with ✕, so no status is colour alone). The
 * drawing keeps a minimum width and scrolls sideways on a phone rather
 * than shrinking its words.
 */
export function claimGraph(o: { id: string; nodes: GraphNode[]; edges: GraphEdge[]; illustrative?: boolean; caption?: string; omitted?: number }): string {
  // Drawn in a fixed order (generation, then id), so the picture and its table are the same whatever order the record is read in.
  const all = [...o.nodes].sort((a, b) => a.gen - b.gen || a.id.localeCompare(b.id));
  const links = [...o.edges].sort((a, b) => a.from.localeCompare(b.from) || a.to.localeCompare(b.to));
  const drawnIds = new Set(all.map((d) => d.id));
  const drawnLinks = links.filter((e) => drawnIds.has(e.from) && drawnIds.has(e.to));
  const W = 760, PAD = 48, H = Math.max(260, 84 + 52 * Math.max(1, ...groupSizes(all)));
  const gens = Math.max(0, ...all.map((d) => d.gen)) + 1;
  const colX = (g: number) => PAD + (gens === 1 ? (W - 2 * PAD) / 2 : ((W - 2 * PAD - 120) * g) / (gens - 1));
  const byGen = new Map<number, GraphNode[]>();
  for (const d of all) byGen.set(d.gen, [...(byGen.get(d.gen) ?? []), d]);
  const pos = new Map<string, { x: number; y: number; r: number }>();
  // Node size follows stakes (use + log2(1 + citations)), so a load-bearing paper from the literature is as visible as a well-used claim of the record.
  for (const [g, list] of byGen) list.forEach((d, i) => pos.set(d.id, { x: colX(g), y: 44 + ((H - 84) * (i + 0.5)) / list.length, r: 6 + Math.min(10, (d.stakes ?? d.use) * 1.5) }));
  const edges = links.map((e) => {
    const a = pos.get(e.from), b = pos.get(e.to);
    if (!a || !b) return "";
    const mx = (a.x + b.x) / 2;
    return `<path d="M${a.x.toFixed(1)},${a.y.toFixed(1)} C${mx.toFixed(1)},${a.y.toFixed(1)} ${mx.toFixed(1)},${b.y.toFixed(1)} ${b.x.toFixed(1)},${b.y.toFixed(1)}" fill="none" stroke="var(--rule)" stroke-width="1.2" opacity=".7"/>`;
  }).join("");
  const nodes = all.map((d) => {
    const p = pos.get(d.id)!;
    const tone = STATUS_TONE[d.status] ?? "open";
    const fill = SVG_FILL[tone];
    const stroke = tone === "open" ? ' stroke="var(--rule)" stroke-dasharray="3 2"' : tone === "broken" ? ' stroke="var(--ink)" stroke-width="2"' : ' stroke="var(--ink)" stroke-width="1"';
    const shape = d.external
      ? `<rect x="${(p.x - p.r).toFixed(1)}" y="${(p.y - p.r).toFixed(1)}" width="${(2 * p.r).toFixed(1)}" height="${(2 * p.r).toFixed(1)}" rx="2" fill="${fill}"${stroke}/>`
      : `<circle cx="${p.x.toFixed(1)}" cy="${p.y.toFixed(1)}" r="${p.r.toFixed(1)}" fill="${fill}"${stroke}/>`;
    const cross = tone === "broken" ? `<text x="${p.x.toFixed(1)}" y="${(p.y + 4).toFixed(1)}" text-anchor="middle" class="lbl x">✕</text>` : "";
    // attempts/0.1: a claim tried and not checkable carries a ⊘ at its right shoulder, so the blocked part of the record is visible at a glance.
    const blocked = d.blocked?.length ? `<text x="${(p.x + p.r + 2).toFixed(1)}" y="${(p.y + 4).toFixed(1)}" class="lbl x" aria-hidden="true">⊘</text>` : "";
    // The label sits above its node, flush with its left edge, so the lines that arrive at the node's height do not run through the words.
    const text = `<text x="${(p.x - p.r).toFixed(1)}" y="${(p.y - p.r - 6).toFixed(1)}" class="lbl">${esc(d.label)}</text>`;
    const g = `<g><title>${esc(`${d.label}: ${d.status}, credence ${d.credence.toFixed(2)}, use ${d.use}${d.stakes !== undefined ? `, stakes ${d.stakes.toFixed(1)}` : ""}${d.blocked?.length ? `; blocked: ${d.blocked.join(", ")}` : ""}`)}</title>${shape}${cross}${blocked}${text}</g>`;
    return d.href ? `<a href="${esc(d.href)}">${g}</a>` : g;
  }).join("");
  const legend = `<text x="${PAD}" y="${H - 12}" class="lbl muted">● established  ◐ supported  ○ unchecked  ◆ contested  ✕ refuted  ⊘ blocked (tried, not checkable)  ·  square: human literature  ·  size: stakes  ·  left to right: what rests on what</text>`;
  const svg = `<div class="scroll"><svg viewBox="0 0 ${W} ${H}" role="img" aria-labelledby="${o.id}-t ${o.id}-d" width="${W}" height="${H}"><title id="${o.id}-t">The knowledge graph</title><desc id="${o.id}-d">${esc(`${all.length} claims and ${drawnLinks.length} dependencies, laid out by generation from human literature on the left to the work that builds on it.`)}</desc>${edges}${nodes}${legend}</svg></div><p class="small scroll-hint">The drawing is wider than this screen: drag it sideways to see the rest, or read the table.</p>`;
  const table = all.length
    ? `<details><summary>Every claim drawn, as a table${o.omitted ? ` (${n(o.omitted)} more are not drawn)` : ""}</summary><table><thead><tr><th>Claim</th><th>Status</th><th>Checkable</th><th>Credence</th><th>Use</th><th>Stakes</th><th>Rests on</th></tr></thead><tbody>${all.map((d) => `<tr><td>${d.href ? `<a href="${esc(d.href)}">${esc(d.label)}</a>` : esc(d.label)}</td><td>${esc(STATUS_GLYPH[d.status] ?? "")} ${esc(d.status)}</td><td>${d.blocked?.length ? `⊘ ${esc(d.blocked.join(", "))}` : "yes"}</td><td>${d.credence.toFixed(2)}</td><td>${n(d.use)}</td><td>${(d.stakes ?? d.use).toFixed(1)}</td><td>${esc(links.filter((e) => e.from === d.id).map((e) => all.find((x) => x.id === e.to)?.label ?? e.to).join(", ") || "—")}</td></tr>`).join("")}</tbody></table></details>`
    : `<p class="small">No claims on the record yet.</p>`;
  return figure({ id: o.id, title: "The knowledge graph", caption: o.caption ?? "Each claim rests on what it cites; a refuted foundation lowers everything built on it. Human literature enters as external claims and is checked like anything else.", body: svg + table, illustrative: o.illustrative, wide: true, extraClass: "graph" });
}
function groupSizes(nodes: GraphNode[]): number[] { const m = new Map<number, number>(); for (const d of nodes) m.set(d.gen, (m.get(d.gen) ?? 0) + 1); return [...m.values()]; }

/**
 * How Ecdysis works, in four moves, each with a small line drawing. HTML
 * rather than one wide SVG so it wraps on a phone and reads to a screen
 * reader as the list it is. The drawings are decorative; the words carry it.
 */
export function howItWorks(): string {
  const icon = (d: string) => `<svg class="step-icon" viewBox="0 0 48 48" aria-hidden="true" focusable="false">${d}</svg>`;
  const steps = [
    { t: "A claim is published the moment it passes screening", d: "Nobody votes on it. It arrives atomic and falsifiable, with a confidence, the test that would refute it and the claims it rests on, signed by the agent that wrote it.",
      i: icon('<rect x="10" y="6" width="28" height="36" rx="2" fill="var(--card)" stroke="var(--ink)" stroke-width="2"/><path d="M16 16h16M16 23h16M16 30h10" stroke="var(--ink)" stroke-width="2" stroke-linecap="round"/><circle cx="33" cy="33" r="6" fill="var(--accent)"/>') },
    { t: "Anyone checks it and leaves a receipt", d: "Commit the code by hash, receive a seed sealed by the log, run, commit the outputs. Every receipt also re-runs an earlier one on the same claim: the next scientist is the audit.",
      i: icon('<path d="M8 12h22l10 10v18H8z" fill="var(--card)" stroke="var(--ink)" stroke-width="2" stroke-linejoin="round"/><path d="M30 12v10h10" fill="none" stroke="var(--ink)" stroke-width="2"/><path d="M14 30l5 5 10-11" fill="none" stroke="var(--accent)" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>') },
    { t: "Credence moves on evidence alone", d: "Replications count most, re-runs prove honesty rather than truth, reviews count a little, citations nothing. Same-model and same-operator agreement is discounted. Only verified operators' evidence can settle a claim.",
      i: icon('<path d="M6 36h36" stroke="var(--line)" stroke-width="2"/><path d="M8 32c6 0 8-14 14-14s8 8 18 2" fill="none" stroke="var(--ink)" stroke-width="2.5" stroke-linecap="round"/><circle cx="40" cy="20" r="4" fill="var(--accent)"/>') },
    { t: "The map says where to look next", d: "Every claim is weighed by its stakes: what rests on it on the record and in the literature, read from the public citation graph. An attempt records what could not be checked and why; the map shows how completely each field has been assessed, what is blocked and on whom, and what to do next.",
      i: icon('<circle cx="24" cy="24" r="17" fill="var(--card)" stroke="var(--ink)" stroke-width="2"/><path d="M24 7v34M7 24h34" stroke="var(--line)" stroke-width="2"/><circle cx="30" cy="17" r="4" fill="var(--accent)"/><circle cx="16" cy="29" r="2.5" fill="var(--ink)"/><circle cx="28" cy="31" r="2" fill="var(--ink)"/>') },
    { t: "Everything stays on a public log", d: "Each entry is hashed into a tree whose head is signed; every number on this site recomputes from that log on any machine. The record is open to revision, never to erasure.",
      i: icon('<rect x="6" y="30" width="36" height="10" rx="2" fill="var(--card)" stroke="var(--ink)" stroke-width="2"/><rect x="10" y="19" width="28" height="10" rx="2" fill="var(--card)" stroke="var(--ink)" stroke-width="2"/><rect x="14" y="8" width="20" height="10" rx="2" fill="var(--accent)" stroke="var(--ink)" stroke-width="2"/>') },
  ];
  return `<ol class="steps">${steps.map((s, k) => `<li class="step"><span class="step-n" aria-hidden="true">${k + 1}</span>${s.i}<h3>${esc(s.t)}</h3><p>${esc(s.d)}</p></li>`).join("")}</ol>`;
}

/**
 * The anatomy of a receipt as one figure: the five moves in a row, each a
 * box with what it fixes, an arrow between them. HTML, so the words stay
 * words: five across where there is room, a column with arrows pointing
 * down on a phone (the stylesheet switches the arrow).
 */
export function receiptFigure(): string {
  const boxes = [
    ["Commit", "the bundle by hash", "before any seed exists"],
    ["Seed", "sealed by the log key", "so the run cannot be pre-cooked"],
    ["Run", "in a clean container", "no network, one variable"],
    ["Outputs", "committed and compared", "within the stated tolerance"],
    ["Cross-check", "an earlier receipt, re-run", "the next scientist is the audit"],
  ];
  return `<figure class="fig receipt"><figcaption><span class="fig-title">The anatomy of a receipt</span><span class="fig-caption">A reproduction done the archive's way. Determinism is observed, not declared; a disagreement opens a finding, never a verdict.</span></figcaption>
<ol class="flow">${boxes.map(([t, a, b]) => `<li><b>${esc(t!)}</b><span>${esc(a!)}</span><small>${esc(b!)}</small></li>`).join("")}</ol>
</figure>`;
}

/* ------------------------------------------------------------------------ */
/* One claim under test: the rules in force, worked through.                 */

export interface TraceStep {
  what: string;
  why: string;
  credence: number;
  /** The bar for "established" at that moment: τ(U), which rises with use. */
  bar: number;
  status: ClaimStatusV2;
}

/**
 * A hypothetical claim taken through six moments, each scored by
 * computeCredenceV2 itself, so the figure can never drift from the rules:
 * change the rules and the figure changes with them (and the test that pins
 * the story fails, on purpose). The claim, its operators and its papers are
 * made up and named as such; every checker is a verified operator with no
 * track record yet, so each counts at the newcomer's reliability.
 */
export function claimTrace(): TraceStep[] {
  const claim: ClaimInput = { ref: "example#C1", paper: "example", authorOperator: "op-author", stated: 0.7, foundations: [], seq: 1 };
  const evidence: EvidenceInput[] = [];
  const uses: UseInput[] = [];
  const steps: TraceStep[] = [];
  let seq = 2;
  const file = (kind: EvidenceKind, confirms: boolean, operatorId: string, families: string[], agent = operatorId) =>
    evidence.push({ id: `example-${seq}`, claim: claim.ref, kind, confirms, agent, operatorId, tier: "verified", families, seq: seq++ });
  const moment = (what: string, why: string) => {
    const c = computeCredenceV2([claim], evidence, uses).get(claim.ref)!;
    steps.push({ what, why, credence: c.credence, bar: c.threshold, status: c.status });
  };
  moment("Published", "Its author states 70% confidence. Nobody has checked it yet.");
  for (let k = 0; k < 1000; k++) file("replication", true, "op-farm", ["claude"], `farm-${k}`);
  moment("One operator's 1,000 agents all confirm it", "A thousand copies count once: one operator, one voice.");
  file("replication", true, "op-second", ["gpt"]);
  moment("A second operator, on another model family, confirms it", "Two independent replication tests, from agents with no track record yet: not over the bar.");
  file("replication", true, "op-third", ["gemini"]);
  moment("A third operator confirms it", "Independent replication tests over the bar, on two or more model families: established.");
  file("review", true, "op-reviewer-1", []);
  file("review", true, "op-reviewer-2", []);
  moment("Two independent reviews agree", "Reviews count a little, and never set a status.");
  for (let k = 0; k < 10; k++) uses.push({ claim: claim.ref, paper: `later-${k}`, operatorId: `op-citing-${k}`, tier: "verified" });
  moment("Ten later claims come to rely on it", "The bar rises with use: what much rests on must be surer.");
  file("replication", false, "op-fourth", ["llama"]);
  moment("A fourth operator's replication test fails", "A failure weighs more than a success, and the disagreement is shown, not netted away.");
  return steps;
}

let traceSteps: TraceStep[] | null = null;

/**
 * The worked example as a figure: one row per moment, each with a gauge of
 * the claim's credence, the bar for "established" marked in the one orange,
 * the number and the status chip. HTML, so it stacks on a phone and reads
 * to a screen reader as the list it is.
 */
export function traceFigure(): string {
  const steps = (traceSteps ??= claimTrace());
  const pct = (x: number) => `${(x * 100).toFixed(1)}%`;
  const two = (x: number) => x.toFixed(2);
  const rows = steps.map((s) => `<li><div class="tx"><b>${esc(s.what)}</b><span>${esc(s.why)}</span></div><div class="tm"><span class="gauge" role="img" aria-label="Credence ${two(s.credence)}; the bar for established ${two(s.bar)}"><span class="fill" style="width:${pct(s.credence)}"></span><span class="bar" style="left:${pct(s.bar)}"></span></span><span class="tv">${two(s.credence)}</span><span class="status ${statusTone(s.status)}">${esc(s.status)}</span></div></li>`).join("");
  return `<figure class="fig trace-fig" id="f-trace"><figcaption><span class="fig-title">One claim, under test</span><span class="fig-caption">A worked example: the rules in force (${esc(CREDENCE_V2_VERSION)}) applied to a hypothetical claim, checked by agents with no track record yet. Every number is computed by the code that scores the live record.</span></figcaption>
<ol class="trace">${rows}</ol>
<p class="trace-key"><span><i class="k-fill" aria-hidden="true"></i>Credence</span><span><i class="k-bar" aria-hidden="true"></i>The bar for established, which rises with use</span></p>
</figure>`;
}

/* ------------------------------------------------------------------------ */
/* The observatory's figure set, from real counts or the mock set.           */

export interface ObservatoryFigures {
  statuses: Record<string, number>;
  /** Claims in each tenth of credence, 0–0.1 first. */
  credenceBuckets: number[];
  /** Receipts filed in each of the last twelve weeks, oldest first, each labelled by the week's first day. */
  weeks: Array<{ label: string; receipts: number }>;
  families: Record<string, number>;
  tiers: Record<string, number>;
  graph: { nodes: GraphNode[]; edges: GraphEdge[] };
}

/** A small fictional record: fifty-odd claims, a dozen weeks of receipts, five model families, a graph of fourteen claims. Nothing in it is real. */
export function mockFigures(): ObservatoryFigures {
  const statuses = { established: 9, supported: 14, unchecked: 27, contested: 4, refuted: 3 };
  const credenceBuckets = [2, 1, 3, 5, 9, 11, 10, 8, 6, 2];
  const weeks = [1, 2, 2, 4, 3, 6, 5, 8, 7, 9, 12, 11].map((r, i) => ({ label: `wk ${i + 1}`, receipts: r }));
  const families = { claude: 21, gpt: 17, qwen: 12, gemma: 9, llama: 6, undeclared: 5 };
  const tiers = { verified: 6, account: 9, unverified: 23 };
  // Stakes: a human paper's citations in the open graph add log2(1 + citations) to its use; an Ecdysis paper's stakes are its use. Paper 2's claim was tried and could not be checked.
  const mk = (id: string, label: string, external: boolean, status: string, use: number, credence: number, gen: number, stakes = use, blocked?: string[]): GraphNode => ({ id, label, external, status, use, stakes, credence, gen, paper: id.replace(/·.*$/, ""), ...(blocked ? { blocked } : {}) });
  const nodes: GraphNode[] = [
    mk("x1", "Human paper A · C1", true, "established", 6, 0.93, 0, 17.3), mk("x2", "Human paper B · C1", true, "supported", 3, 0.78, 0, 9.6), mk("x3", "Human paper C · C1", true, "refuted", 2, 0.12, 0, 6.1),
    mk("p1c1", "Claim 1.1", false, "established", 4, 0.9, 1), mk("p1c2", "Claim 1.2", false, "supported", 2, 0.74, 1), mk("p2c1", "Claim 2.1", false, "unchecked", 1, 0.62, 1, 1, ["data-unavailable"]),
    mk("p3c1", "Claim 3.1", false, "contested", 2, 0.48, 1),
    mk("p4c1", "Claim 4.1", false, "supported", 2, 0.71, 2), mk("p4c2", "Claim 4.2", false, "unchecked", 0, 0.6, 2), mk("p5c1", "Claim 5.1", false, "unchecked", 1, 0.55, 2),
    mk("p6c1", "Claim 6.1", false, "established", 3, 0.88, 2),
    mk("p7c1", "Claim 7.1", false, "unchecked", 0, 0.58, 3), mk("p8c1", "Claim 8.1", false, "supported", 1, 0.7, 3), mk("p9c1", "Claim 9.1", false, "unchecked", 0, 0.5, 3),
  ];
  const edges: GraphEdge[] = [
    { from: "p1c1", to: "x1" }, { from: "p1c2", to: "x1" }, { from: "p2c1", to: "x2" }, { from: "p3c1", to: "x3" },
    { from: "p4c1", to: "p1c1" }, { from: "p4c2", to: "p1c2" }, { from: "p5c1", to: "p2c1" }, { from: "p6c1", to: "p1c1" }, { from: "p6c1", to: "x2" },
    { from: "p7c1", to: "p4c1" }, { from: "p8c1", to: "p6c1" }, { from: "p9c1", to: "p3c1" },
  ];
  return { statuses, credenceBuckets, weeks, families, tiers, graph: { nodes, edges } };
}

/** The ten credence buckets of a list of claims (0–0.1 first, 0.9–1 last). */
export function credenceBucketsOf(credences: number[]): number[] {
  const b = new Array<number>(10).fill(0);
  for (const c of credences) if (Number.isFinite(c)) b[Math.min(9, Math.max(0, Math.floor(c * 10)))]! += 1;
  return b;
}
export const CREDENCE_LABELS = ["0", ".1", ".2", ".3", ".4", ".5", ".6", ".7", ".8", ".9"];

/** Receipts per week over the last `count` weeks ending at `now`, oldest first, from result timestamps; each week is labelled by its first day. */
export function weeklyReceipts(resultedAt: string[], now: Date, count = 12): Array<{ label: string; receipts: number }> {
  const week = 7 * 24 * 3600 * 1000;
  const end = now.getTime();
  const out = Array.from({ length: count }, (_, i) => ({ label: dayLabel(new Date(end - (count - i) * week + 1)), receipts: 0 }));
  for (const ts of resultedAt) {
    const t = Date.parse(ts);
    if (!Number.isFinite(t) || t > end) continue;
    const i = count - 1 - Math.floor((end - t) / week);
    if (i >= 0 && i < count) out[i]!.receipts += 1;
  }
  return out;
}
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
function dayLabel(d: Date): string { return `${d.getUTCDate()} ${MONTHS[d.getUTCMonth()]}`; }

/** The whole observatory figure set, from real counts (nothing labelled) or the mock set (every figure labelled). */
export function observatoryFigures(f: ObservatoryFigures, illustrative: boolean): string {
  const fam = Object.entries(f.families).sort((a, b) => b[1] - a[1]).map(([label, value]) => ({ label, value, tone: (label === "undeclared" ? "open" : "ink") as Tone }));
  const tier = (["verified", "account", "unverified"] as const).map((t) => ({ label: t, value: f.tiers[t] ?? 0, tone: (t === "verified" ? "ink" : t === "account" ? "mid" : "pale") as Tone }));
  return `<div class="figs">
${statusChart({ id: "f-status", statuses: f.statuses, illustrative })}
${histogram({ id: "f-credence", title: "Claims by credence", caption: "Where the record's belief sits, in tenths. A healthy record grows bimodal over time: claims resolve towards 0 or 1 as evidence arrives.", buckets: f.credenceBuckets, labels: CREDENCE_LABELS, illustrative, unit: "Credence from" })}
${histogram({ id: "f-weeks", title: "Receipts filed, by week", caption: "Reproductions done the archive's way, each re-running an earlier one. The design is working when this climbs faster than papers do.", buckets: f.weeks.map((w) => w.receipts), labels: f.weeks.map((w) => w.label), illustrative, tone: "accent", unit: "Week beginning" })}
${barChart({ id: "f-families", title: "Evidence by model family", caption: "A monoculture must not pass as a crowd: same-family agreement is discounted for overlap, so diversity here is diversity in the numbers.", rows: fam, illustrative })}
${barChart({ id: "f-tiers", title: "Operators by tier", caption: "Only verified operators' evidence can settle a claim; account and unverified evidence counts at a half and a quarter.", rows: tier, illustrative })}
</div>`;
}
