/**
 * The network drawing (graph/0.1): the claims and what rests on what, drawn so the shape of the record reads at a glance.
 * One drawing serves every page that shows the network: the claims page and the observatory (the joined claims), a claim's
 * line of work, and the network view (/network), where it is filtered, sized and grouped by the reader's choice.
 *
 * Grouped by connectivity. Claims joined by links, directly or through others, are drawn together in one group, the largest
 * group first; claims joined to nothing stand apart, in a grid of their own. Within a group, foundations are on the left and
 * what rests on them to their right, a column per step (the longest chain of links beneath a claim, then pulled right
 * towards what rests on it, so that no line is longer than it must be). A line that spans several columns passes through a
 * waypoint in each. The order down each column is chosen so that linked claims sit near one another and lines cross as
 * little as possible: barycentre sweeps, keeping the order with the fewest crossings. Each claim is then placed as close to
 * the claims it is linked to as the spacing allows (least squares under the order, by pooling adjacent violators).
 *
 * What each mark says. Shape: human literature (square) or published here (circle). Fill: status, as the chips have it
 * (established filled, supported grey, unchecked empty and dashed, contested orange, refuted empty, outlined and crossed).
 * Area: the measure chosen (stakes by default; or credence, pressure, reliance, use, or none), so a claim twice the stakes
 * has about twice the ink. A ⊘ beside a claim: tried, and not checkable as things stand. A line: declared by the author of
 * the claim resting (solid), identified in the literature by an agent reading the citing paper (dashed), or a refutation
 * (orange); its width, the measure chosen (none by default; or the credence of the claim it rests on, so a line onto weak
 * ground is thin, or the stakes of the claim resting on it).
 *
 * Pure and deterministic: the same claims draw the same picture for everyone, whatever order they are read in. Script-free:
 * every choice is a link or a GET form, and the server draws. Every word in the drawing is escaped.
 */

import { esc } from "../design.js";
import { figure, STATUS_GLYPH, STATUS_TONE, SVG_FILL, type GraphEdge, type GraphNode } from "./viz.js";

export type SizeBy = "stakes" | "credence" | "pressure" | "reliance" | "use" | "same";
export type LinesBy = "same" | "credence" | "stakes";
export type GroupBy = "connected" | "field";

export interface NetworkOptions {
  /** The drawing's width in the units its words are set in: on a desktop the figure is this wide, so words are at their size. */
  width?: number;
  size?: SizeBy;
  lines?: LinesBy;
  group?: GroupBy;
  /** Draw the claims joined to nothing, in a grid of their own (the network view); otherwise the table has them. */
  alone?: boolean;
  /** Claims drawn faded: in the drawing for its shape, but not what the filters ask for. */
  dim?: ReadonlySet<string>;
  /** The claim the drawing is centred on: ringed in orange and always named. */
  focus?: string | null;
  /** Where a group's caption leads, given the id of the group's weightiest claim; absent, the caption is plain text. */
  groupHref?: (claim: string) => string;
}

/** The width the network is laid out in: the wide figure's inner width, so the drawing is at its own size on a desktop. */
export const NET_WIDTH = 1064;
/** The most claims the network view draws at once; the rest are counted, and the filters narrow the view. */
export const NETWORK_MAX = 400;

/** What the size choices measure, in the words the legend and the form use. */
export const SIZE_WORDS: Record<SizeBy, string> = { stakes: "stakes", credence: "credence", pressure: "pressure", reliance: "reliance", use: "use", same: "all the same" };
export const LINES_WORDS: Record<LinesBy, string> = { same: "all the same", credence: "the credence of the claim it rests on", stakes: "the stakes of the claim resting on it" };

const R_MIN = 4;
const R_MAX = 16;
const R_SAME = 7;
/** A column's width: in a group of a few claims, in a larger one, and at least; a label is as wide as its column allows. */
const COL_SMALL = 150;
const COL = 210;
const COL_MIN = 96;
/** A small group, drawn with narrower columns so that several share a row. */
const SMALL = 4;
const LABEL_H = 16;
const PAD = 16;
const CAPTION_H = 30;
const GAP = 20;
const CELL = 2 * R_MAX + 10;
/** A group of this many claims or fewer names every claim; a larger one names its weightiest third (at least six). */
const NAME_ALL = 10;

const cmp = (a: string, b: string) => (a < b ? -1 : a > b ? 1 : 0);
const two = (x: number) => x.toFixed(2);
const one = (x: number) => x.toFixed(1);
const n = (x: number) => x.toLocaleString("en-GB");
const STATUS_RANK: Record<string, number> = { established: 0, supported: 1, unchecked: 2, contested: 3, refuted: 4 };

/** A node's value for the measure chosen; a node's stakes when nothing is chosen, for ranking which claims to name. */
export function measureOf(node: GraphNode, by: SizeBy): number {
  const v = by === "credence" ? node.credence : by === "pressure" ? node.pressure ?? 0 : by === "reliance" ? node.reliance ?? 0 : by === "use" ? node.use : node.stakes ?? node.use;
  return Number.isFinite(v) && v > 0 ? v : 0;
}

/** One line per pair of claims: the relations joining them, whether it is declared by its author or only identified. */
interface DrawEdge { from: string; to: string; rels: string[]; identified: boolean }

interface Placed { node: GraphNode; x: number; y: number; r: number; label: string | null }
interface Frame { x: number; y: number; w: number; h: number; caption: string; href: string | null; section: boolean }
export interface NetworkLayout {
  width: number; height: number;
  nodes: Placed[];
  edges: Array<{ edge: DrawEdge; pts: Array<[number, number]> }>;
  frames: Frame[];
  /** Groups of joined claims drawn, and claims drawn standing alone. */
  groups: number; alone: number;
}

/** The edges between drawn claims, one per pair, in a fixed order. A self-edge, or an edge to a claim not drawn, is left out. */
function mergeEdges(edges: readonly GraphEdge[], drawn: ReadonlyMap<string, GraphNode>): DrawEdge[] {
  const byPair = new Map<string, DrawEdge>();
  for (const e of edges) {
    if (e.from === e.to || !drawn.has(e.from) || !drawn.has(e.to)) continue;
    const key = `${e.from}\u0000${e.to}`;
    const d = byPair.get(key) ?? { from: e.from, to: e.to, rels: [], identified: true };
    const rel = e.rel ?? "extends";
    if (!d.rels.includes(rel)) d.rels.push(rel);
    d.identified = d.identified && e.identified === true;
    byPair.set(key, d);
  }
  return [...byPair.values()].map((d) => ({ ...d, rels: [...d.rels].sort(cmp) })).sort((a, b) => cmp(a.from, b.from) || cmp(a.to, b.to));
}

/** Pool adjacent violators: the non-decreasing sequence nearest (least squares) to the values given. */
function pava(values: readonly number[]): number[] {
  const blocks: Array<{ sum: number; count: number }> = [];
  for (const v of values) {
    blocks.push({ sum: v, count: 1 });
    for (;;) {
      const b = blocks[blocks.length - 1]!;
      const a = blocks[blocks.length - 2];
      if (!a || a.sum / a.count <= b.sum / b.count) break;
      a.sum += b.sum; a.count += b.count; blocks.pop();
    }
  }
  return blocks.flatMap((b) => Array.from({ length: b.count }, () => b.sum / b.count));
}

/**
 * The column of every claim in a group: 0 for a claim resting on nothing in it, else one more than the deepest claim it rests
 * on (in order, without recursion, so a chain of any length is fine); then, from the right, each claim moves right to just
 * left of the nearest claim resting on it. A claim on a cycle (possible among identified links only by a race) takes the depth
 * its other foundations give it.
 */
function columnsOf(ids: readonly string[], edges: readonly DrawEdge[]): Map<string, number> {
  const down = new Map<string, string[]>(ids.map((id) => [id, []]));
  const up = new Map<string, string[]>(ids.map((id) => [id, []]));
  for (const e of edges) { down.get(e.from)!.push(e.to); up.get(e.to)!.push(e.from); }
  const waiting = new Map(ids.map((id) => [id, down.get(id)!.length] as const));
  const col = new Map<string, number>();
  const ready = ids.filter((id) => waiting.get(id) === 0);
  for (let i = 0; i < ready.length; i++) {
    const v = ready[i]!;
    const fs = down.get(v)!;
    col.set(v, fs.length ? 1 + Math.max(...fs.map((f) => col.get(f) ?? 0)) : 0);
    for (const d of up.get(v)!) { const left = waiting.get(d)! - 1; waiting.set(d, left); if (left === 0) ready.push(d); }
  }
  for (const id of ids) if (!col.has(id)) { const known = down.get(id)!.map((f) => col.get(f)).filter((c): c is number => c !== undefined); col.set(id, known.length ? 1 + Math.max(...known) : 0); }
  for (const v of [...ids].sort((a, b) => col.get(b)! - col.get(a)! || cmp(a, b))) {
    const deps = up.get(v)!;
    if (!deps.length) continue;
    const room = Math.min(...deps.map((d) => col.get(d)!)) - 1;
    if (room > col.get(v)!) col.set(v, room);
  }
  const least = Math.min(...ids.map((id) => col.get(id)!));
  for (const id of ids) col.set(id, col.get(id)! - least);
  return col;
}

interface Vertex { key: string; col: number; real: GraphNode | null; top: number; bottom: number; left: string[]; right: string[] }

/**
 * The crossings between neighbouring columns: each column pair's line segments, sorted by where they leave, cross once for
 * every pair whose arrivals are in the opposite order; counted as inversions with a Fenwick tree, in O(m log m).
 */
function crossings(rows: readonly string[][], vs: ReadonlyMap<string, Vertex>): number {
  let total = 0;
  for (let c = 0; c + 1 < rows.length; c++) {
    const at = new Map(rows[c + 1]!.map((k, i) => [k, i] as const));
    const pairs: Array<[number, number]> = [];
    rows[c]!.forEach((k, i) => { for (const r of vs.get(k)!.right) { const j = at.get(r); if (j !== undefined) pairs.push([i, j]); } });
    pairs.sort((a, b) => a[0] - b[0] || a[1] - b[1]);
    const size = rows[c + 1]!.length;
    const tree = new Array<number>(size + 1).fill(0);
    let seen = 0;
    for (const [, j] of pairs) {
      // Earlier segments arriving strictly below this one cross it: all seen so far, less those arriving at or above it.
      let atOrAbove = 0;
      for (let x = j + 1; x > 0; x -= x & -x) atOrAbove += tree[x]!;
      total += seen - atOrAbove;
      for (let x = j + 1; x <= size; x += x & -x) tree[x]! += 1;
      seen++;
    }
  }
  return total;
}

/** One group laid out on its own: its claims' places, its lines' waypoints and its size, with (0, 0) its top left corner. */
function layoutGroup(ids: readonly string[], edges: readonly DrawEdge[], node: ReadonlyMap<string, GraphNode>, radius: ReadonlyMap<string, number>, named: ReadonlySet<string>, rank: (id: string) => number, width: number) {
  const col = columnsOf(ids, edges);
  const cols = Math.max(...ids.map((id) => col.get(id)!)) + 1;
  const gap = Math.max(COL_MIN, Math.min(ids.length <= SMALL ? COL_SMALL : COL, (width - 2 * PAD) / cols));
  const vs = new Map<string, Vertex>();
  for (const id of ids) {
    const r = radius.get(id)!;
    vs.set(id, { key: id, col: col.get(id)!, real: node.get(id)!, top: r + (named.has(id) ? LABEL_H + 2 : 4), bottom: r + 4, left: [], right: [] });
  }
  const chains = edges.map((e, i) => {
    const a = col.get(e.from)!, b = col.get(e.to)!;
    const chain = [e.from];
    for (let c = a - 1; c > b; c--) { const key = `\u0001${i}:${c}`; vs.set(key, { key, col: c, real: null, top: 3, bottom: 3, left: [], right: [] }); chain.push(key); }
    chain.push(e.to);
    // Each step of a chain joins neighbouring columns; a line that runs backwards (only on a cycle) is drawn but steers nothing.
    if (a > b) for (let k = 0; k + 1 < chain.length; k++) { vs.get(chain[k]!)!.left.push(chain[k + 1]!); vs.get(chain[k + 1]!)!.right.push(chain[k]!); }
    return { edge: e, chain };
  });
  // The order down each column: the weightiest first, then sweeps towards the barycentre of the neighbours, keeping the best.
  let rows: string[][] = Array.from({ length: cols }, () => []);
  for (const v of [...vs.values()].sort((a, b) => (a.real && b.real ? rank(b.key) - rank(a.key) || cmp(a.key, b.key) : a.real ? -1 : b.real ? 1 : cmp(a.key, b.key)))) rows[v.col]!.push(v.key);
  const sweep = (dir: 1 | -1) => {
    const order = dir === 1 ? [...rows.keys()].slice(1) : [...rows.keys()].reverse().slice(1);
    for (const c of order) {
      const pos = new Map(rows[c - dir]!.map((k, i) => [k, i] as const));
      const row = rows[c]!;
      const span = Math.max(1, rows[c - dir]!.length - 1) / Math.max(1, row.length - 1);
      const key = row.map((k, i) => {
        const ns = (dir === 1 ? vs.get(k)!.left : vs.get(k)!.right).map((x) => pos.get(x)).filter((p): p is number => p !== undefined);
        return { k, i, at: ns.length ? ns.reduce((s, p) => s + p, 0) / ns.length : i * span };
      });
      rows[c] = key.sort((a, b) => a.at - b.at || a.i - b.i).map((x) => x.k);
    }
  };
  let best = rows.map((r) => [...r]);
  let fewest = crossings(rows, vs);
  for (let pass = 0; pass < 8 && fewest > 0; pass++) {
    sweep(1); sweep(-1);
    const now = crossings(rows, vs);
    if (now < fewest) { fewest = now; best = rows.map((r) => [...r]); }
  }
  rows = best;
  // Heights: each claim as near the mean of its neighbours as its column's order and spacing allow.
  const y = new Map<string, number>();
  const sepOf = (a: Vertex, b: Vertex) => a.bottom + b.top + (a.real && b.real ? 8 : 4);
  for (const row of rows) { let at = 0; row.forEach((k, i) => { if (i) at += sepOf(vs.get(row[i - 1]!)!, vs.get(k)!); y.set(k, at); }); }
  for (let pass = 0; pass < 10; pass++) {
    const order = pass % 2 ? [...rows.keys()].reverse() : [...rows.keys()];
    for (const c of order) {
      const row = rows[c]!;
      const offset: number[] = [];
      row.forEach((k, i) => offset.push(i ? offset[i - 1]! + sepOf(vs.get(row[i - 1]!)!, vs.get(k)!) : 0));
      const target = row.map((k, i) => {
        const v = vs.get(k)!;
        const ns = [...v.left, ...v.right].map((x) => y.get(x)!).filter((t) => t !== undefined);
        return (ns.length ? ns.reduce((s, t) => s + t, 0) / ns.length : y.get(k)!) - offset[i]!;
      });
      pava(target).forEach((z, i) => y.set(row[i]!, z + offset[i]!));
    }
  }
  const top = Math.min(...[...vs.values()].map((v) => y.get(v.key)! - v.top));
  const xOf = (c: number) => PAD + gap / 2 + c * gap;
  const at = (k: string): [number, number] => [xOf(vs.get(k)!.col), y.get(k)! - top + CAPTION_H];
  const height = Math.max(...[...vs.values()].map((v) => y.get(v.key)! - top + v.bottom)) + CAPTION_H + PAD;
  return {
    w: 2 * PAD + cols * gap, h: height, cols, gap,
    nodes: ids.map((id) => ({ id, xy: at(id) })),
    edges: chains.map(({ edge, chain }) => ({ edge, pts: chain.map(at) })),
  };
}

/** A label that fits its column: the claim's words, cut at a word where possible. */
function fit(label: string, gap: number): string {
  const max = Math.max(8, Math.floor((gap - 12) / 5.9));
  if (label.length <= max) return label;
  const cut = label.slice(0, max - 1);
  const space = cut.lastIndexOf(" ");
  return `${(space > max * 0.45 ? cut.slice(0, space) : cut).trimEnd().replace(/[,;:.]$/, "")}…`;
}

/** Lay the claims out: groups of joined claims, the largest first; then the claims standing alone; sectioned by field if asked. */
export function layoutNetwork(nodesIn: readonly GraphNode[], edgesIn: readonly GraphEdge[], o: NetworkOptions = {}): NetworkLayout {
  const W = o.width ?? NET_WIDTH;
  const size = o.size ?? "stakes";
  const nodes = [...nodesIn].sort((a, b) => cmp(a.id, b.id));
  const byId = new Map(nodes.map((x) => [x.id, x] as const));
  const edges = mergeEdges(edgesIn, byId);
  const top = size === "credence" ? 1 : Math.max(0, ...nodes.map((x) => measureOf(x, size)));
  const radius = new Map(nodes.map((x) => [x.id, size === "same" ? R_SAME : R_MIN + (R_MAX - R_MIN) * Math.sqrt(top > 0 ? measureOf(x, size) / top : 0)] as const));
  const weight = (id: string) => measureOf(byId.get(id)!, size === "same" ? "stakes" : size);
  // Groups: claims joined by links, directly or through others (union by the smaller id, so the result is order-free).
  const parent = new Map(nodes.map((x) => [x.id, x.id] as const));
  const find = (x: string): string => { let r = x; while (parent.get(r) !== r) r = parent.get(r)!; return r; };
  for (const e of edges) { const a = find(e.from), b = find(e.to); if (a !== b) { if (cmp(a, b) < 0) parent.set(b, a); else parent.set(a, b); } }
  const members = new Map<string, string[]>();
  for (const x of nodes) { const r = find(x.id); const list = members.get(r); if (list) list.push(x.id); else members.set(r, [x.id]); }
  const heaviest = (ids: readonly string[]) => [...ids].sort((a, b) => weight(b) - weight(a) || cmp(a, b))[0]!;
  const groups = [...members.values()].filter((ids) => ids.length > 1)
    .sort((a, b) => b.length - a.length || b.reduce((s, id) => s + weight(id), 0) - a.reduce((s, id) => s + weight(id), 0) || cmp(a[0]!, b[0]!));
  const alone = o.alone ? [...members.values()].filter((ids) => ids.length === 1).map((ids) => ids[0]!) : [];
  // Which claims are named: every claim of a small group, the weightiest third of a larger one, and the focus.
  const named = new Set<string>(o.focus && byId.has(o.focus) ? [o.focus] : []);
  for (const ids of groups) for (const id of ids.length <= NAME_ALL ? ids : [...ids].sort((a, b) => weight(b) - weight(a) || cmp(a, b)).slice(0, Math.max(6, Math.ceil(ids.length / 3)))) named.add(id);
  const fieldOf = (id: string) => byId.get(id)!.field ?? "Not yet placed";
  // Blocks to place in rows: a section heading, a group, or the grid of claims standing alone.
  type Block = { kind: "section"; title: string } | { kind: "group"; ids: string[] } | { kind: "alone"; ids: string[] };
  const blocks: Block[] = [];
  const aloneSorted = (ids: readonly string[]) => [...ids].sort((a, b) => (STATUS_RANK[byId.get(a)!.status] ?? 9) - (STATUS_RANK[byId.get(b)!.status] ?? 9) || weight(b) - weight(a) || cmp(a, b));
  if (o.group === "field") {
    const majority = (ids: readonly string[]) => {
      const count = new Map<string, number>();
      for (const id of ids) count.set(fieldOf(id), (count.get(fieldOf(id)) ?? 0) + 1);
      return [...count.entries()].sort((a, b) => b[1] - a[1] || cmp(a[0], b[0]))[0]![0];
    };
    const sections = new Map<string, { groups: string[][]; alone: string[]; claims: number }>();
    const section = (f: string) => { const s = sections.get(f) ?? { groups: [], alone: [], claims: 0 }; sections.set(f, s); return s; };
    for (const ids of groups) { const s = section(majority(ids)); s.groups.push(ids); s.claims += ids.length; }
    for (const id of alone) { const s = section(fieldOf(id)); s.alone.push(id); s.claims += 1; }
    for (const [title, s] of [...sections.entries()].sort((a, b) => b[1].claims - a[1].claims || cmp(a[0], b[0]))) {
      blocks.push({ kind: "section", title: `${title}: ${n(s.claims)} claim${s.claims === 1 ? "" : "s"}` });
      for (const ids of s.groups) blocks.push({ kind: "group", ids });
      if (s.alone.length) blocks.push({ kind: "alone", ids: aloneSorted(s.alone) });
    }
  } else {
    for (const ids of groups) blocks.push({ kind: "group", ids });
    if (alone.length) blocks.push({ kind: "alone", ids: aloneSorted(alone) });
  }
  const placed: Placed[] = [];
  const lines: NetworkLayout["edges"] = [];
  const frames: Frame[] = [];
  const edgesOf = new Map<string, DrawEdge[]>();
  for (const e of edges) { const r = find(e.from); const list = edgesOf.get(r); if (list) list.push(e); else edgesOf.set(r, [e]); }
  // Each block becomes a box to place; a section heading starts a shelf of its own.
  type Box = { w: number; h: number; draw: (gx: number, gy: number) => void };
  const shelves: Array<{ title: string | null; boxes: Box[] }> = [];
  for (const b of blocks) {
    if (b.kind === "section") { shelves.push({ title: b.title, boxes: [] }); continue; }
    if (!shelves.length) shelves.push({ title: null, boxes: [] });
    const into = shelves[shelves.length - 1]!.boxes;
    if (b.kind === "group") {
      const g = layoutGroup(b.ids, edgesOf.get(find(b.ids[0]!)) ?? [], byId, radius, named, weight, W);
      const depth = g.cols - 1;
      // The group's field, where its claims have one: the commonest, and "and more" when they differ.
      const fields = new Map<string, number>();
      for (const id of b.ids) { const f = byId.get(id)!.field; if (f) fields.set(f, (fields.get(f) ?? 0) + 1); }
      const field = [...fields.entries()].sort((p, q) => q[1] - p[1] || cmp(p[0], q[0]))[0]?.[0] ?? null;
      const lead = heaviest(b.ids);
      into.push({ w: g.w, h: g.h, draw: (gx, gy) => {
        frames.push({ x: gx, y: gy, w: g.w, h: g.h, caption: `${n(b.ids.length)} claims, ${depth} step${depth === 1 ? "" : "s"} deep${o.group === "field" || !field ? "" : `, ${field}${fields.size > 1 ? " and more" : ""}`}`, href: o.groupHref ? o.groupHref(lead) : null, section: false });
        for (const p of g.nodes) placed.push({ node: byId.get(p.id)!, x: gx + p.xy[0], y: gy + p.xy[1], r: radius.get(p.id)!, label: named.has(p.id) ? fit(byId.get(p.id)!.label, g.gap) : null });
        for (const l of g.edges) lines.push({ edge: l.edge, pts: l.pts.map(([px, py]) => [gx + px, gy + py] as [number, number]) });
      } });
      continue;
    }
    const cols = Math.max(1, Math.min(b.ids.length, Math.floor((W - 2 * PAD) / CELL)));
    const w = Math.max(300, 2 * PAD + cols * CELL);
    const h = CAPTION_H + Math.ceil(b.ids.length / cols) * CELL + PAD / 2;
    into.push({ w, h, draw: (gx, gy) => {
      frames.push({ x: gx, y: gy, w, h, caption: `Standing alone here: ${n(b.ids.length)} claim${b.ids.length === 1 ? "" : "s"}`, href: null, section: false });
      b.ids.forEach((id, i) => placed.push({ node: byId.get(id)!, x: gx + PAD + (i % cols) * CELL + CELL / 2, y: gy + CAPTION_H + Math.floor(i / cols) * CELL + CELL / 2, r: radius.get(id)!, label: null }));
    } });
  }
  // First fit, row by row: a row takes the first box left, then every later box that still fits beside it, so the largest
  // groups lead and the small ones fill the gaps.
  let y = 0, widest = W;
  for (const shelf of shelves) {
    if (shelf.title !== null) { frames.push({ x: 0, y, w: W, h: 26, caption: shelf.title, href: null, section: true }); y += 34; }
    const left = [...shelf.boxes];
    while (left.length) {
      const row = [left.shift()!];
      let used = row[0]!.w;
      for (let i = 0; i < left.length;) {
        if (used + GAP + left[i]!.w <= W) { used += GAP + left[i]!.w; row.push(left.splice(i, 1)[0]!); } else i++;
      }
      let x = 0;
      for (const box of row) { box.draw(x, y); x += box.w + GAP; }
      widest = Math.max(widest, used);
      y += Math.max(...row.map((box) => box.h)) + GAP;
    }
  }
  // A pixel below the lowest frame, so its bottom edge is drawn whole.
  const height = frames.length ? Math.max(...frames.map((f) => f.y + f.h)) + 1 : 0;
  return { width: Math.max(W, widest), height, nodes: placed, edges: lines, frames, groups: groups.length, alone: alone.length };
}

/** A line through its waypoints, leaving and arriving level, so it reads as flowing from column to column. */
function pathOf(pts: ReadonlyArray<[number, number]>): string {
  const [x0, y0] = pts[0]!;
  let d = `M${one(x0)},${one(y0)}`;
  for (let i = 1; i < pts.length; i++) {
    const [ax, ay] = pts[i - 1]!; const [bx, by] = pts[i]!;
    const mx = (ax + bx) / 2;
    d += ` C${one(mx)},${one(ay)} ${one(mx)},${one(by)} ${one(bx)},${one(by)}`;
  }
  return d;
}

const RELS: Record<string, string> = { extends: "extends", method: "takes its method from", replicates: "replicates", refutes: "refutes" };

/** The drawing as SVG: frames and captions, then the lines (faded ones first), then the claims, each linked to its page. */
export function networkSvg(L: NetworkLayout, o: NetworkOptions & { id: string; label?: string }): string {
  const dim = o.dim ?? new Set<string>();
  const lines = o.lines ?? "same";
  const byId = new Map(L.nodes.map((p) => [p.node.id, p.node] as const));
  const topStakes = Math.max(0, ...L.nodes.map((p) => measureOf(p.node, "stakes")));
  const widthOf = (e: DrawEdge) => {
    if (lines === "credence") return 0.6 + 3.4 * Math.min(1, Math.max(0, byId.get(e.to)!.credence));
    if (lines === "stakes") return 0.6 + 3.4 * Math.sqrt(topStakes > 0 ? measureOf(byId.get(e.from)!, "stakes") / topStakes : 0);
    return 1.3;
  };
  const frames = L.frames.map((f) => {
    const caption = `<text class="cap${f.section ? " sec" : ""}" x="${one(f.x + (f.section ? 0 : PAD))}" y="${one(f.y + (f.section ? 18 : 20))}">${esc(f.caption)}</text>`;
    return `${f.section ? `<line class="sec" x1="${one(f.x)}" y1="${one(f.y + 26)}" x2="${one(f.x + f.w)}" y2="${one(f.y + 26)}"/>` : `<rect class="grp" x="${one(f.x)}" y="${one(f.y)}" width="${one(f.w)}" height="${one(f.h)}" rx="6"/>`}${f.href ? `<a href="${esc(f.href)}">${caption}</a>` : caption}`;
  }).join("");
  const faded = (e: DrawEdge) => dim.has(e.from) || dim.has(e.to);
  const edges = [...L.edges].sort((a, b) => Number(faded(b.edge)) - Number(faded(a.edge))).map(({ edge: e, pts }) => {
    const cls = ["e", e.identified ? "id" : "", e.rels.includes("refutes") ? "ref" : "", faded(e) ? "dim" : ""].filter(Boolean).join(" ");
    const said = `${byId.get(e.from)!.label} ${e.rels.map((r) => RELS[r] ?? r).join(" and ")} ${byId.get(e.to)!.label}${e.identified ? " (identified in the literature)" : ""}`;
    return `<path d="${pathOf(pts)}" class="${cls}" fill="none" stroke-width="${two(widthOf(e))}"><title>${esc(said)}</title></path>`;
  }).join("");
  const nodes = L.nodes.map((p) => {
    const d = p.node;
    const tone = STATUS_TONE[d.status] ?? "open";
    const fill = SVG_FILL[tone];
    const stroke = tone === "open" ? ' stroke="var(--st-unc)" stroke-dasharray="3 2"' : tone === "broken" ? ' stroke="var(--st-ref)" stroke-width="2"' : ' stroke="var(--card)" stroke-width="1"';
    const shape = d.external
      ? `<rect x="${one(p.x - p.r)}" y="${one(p.y - p.r)}" width="${one(2 * p.r)}" height="${one(2 * p.r)}" rx="2" fill="${fill}"${stroke}/>`
      : `<circle cx="${one(p.x)}" cy="${one(p.y)}" r="${one(p.r)}" fill="${fill}"${stroke}/>`;
    const ring = o.focus === d.id ? `<circle cx="${one(p.x)}" cy="${one(p.y)}" r="${one(p.r + 5)}" class="ring" fill="none"/>` : "";
    const cross = tone === "broken" ? `<text x="${one(p.x)}" y="${one(p.y + 4)}" text-anchor="middle" class="lbl x">✕</text>` : "";
    // attempts/0.1: a claim tried and not checkable carries a ⊘ at its right shoulder.
    const blocked = d.blocked?.length ? `<text x="${one(p.x + p.r + 2)}" y="${one(p.y + 4)}" class="lbl x" aria-hidden="true">⊘</text>` : "";
    const label = p.label ? `<text x="${one(p.x)}" y="${one(p.y - p.r - 6)}" text-anchor="middle" class="lbl">${esc(p.label)}</text>` : "";
    const title = `${d.label}: ${d.status}, credence ${two(d.credence)}, stakes ${one(d.stakes ?? d.use)}${d.pressure ? `, pressure ${one(d.pressure)}` : ""}${d.reliance ? `, reliance ${one(d.reliance)}` : ""}${d.blocked?.length ? `; blocked: ${d.blocked.join(", ")}` : ""}`;
    const cls = o.focus === d.id ? ' class="focus"' : dim.has(d.id) ? ' class="dim"' : "";
    const g = `<g${cls}><title>${esc(title)}</title>${ring}${shape}${cross}${blocked}${label}</g>`;
    return d.href ? `<a href="${esc(d.href)}">${g}</a>` : g;
  });
  // Faded claims first, so what the filters ask for is drawn over them.
  const order = L.nodes.map((p, i) => ({ i, faded: dim.has(p.node.id) })).sort((a, b) => Number(b.faded) - Number(a.faded) || a.i - b.i).map((x) => nodes[x.i]!).join("");
  const desc = `${L.nodes.length} claims and ${L.edges.length} dependencies, in ${L.groups} group${L.groups === 1 ? "" : "s"} of joined claims${L.alone ? ` and ${L.alone} standing alone` : ""}; within a group, foundations on the left and what rests on them to the right.`;
  return `<svg class="net" viewBox="0 0 ${L.width} ${one(L.height)}" width="${L.width}" height="${one(L.height)}" style="max-width:${L.width}px;min-width:${Math.min(L.width, 880)}px" role="img" aria-labelledby="${esc(o.id)}-t ${esc(o.id)}-d"><title id="${esc(o.id)}-t">${esc(o.label ?? "The network of claims")}</title><desc id="${esc(o.id)}-d">${esc(desc)}</desc><g class="frames">${frames}</g><g class="edges">${edges}</g><g class="nodes">${order}</g></svg>`;
}

/** What the marks mean: shapes and fills, the line styles, and what size and width measure here. */
function legend(L: NetworkLayout, o: NetworkOptions): string {
  const size = o.size ?? "stakes";
  const lines = o.lines ?? "same";
  const top = Math.max(0, ...L.nodes.map((p) => measureOf(p.node, size)));
  const sample = (cls: string) => `<svg class="k" viewBox="0 0 28 10" width="28" height="10" aria-hidden="true"><line x1="1" y1="5" x2="27" y2="5" class="${cls}"/></svg>`;
  const shape = (inner: string) => `<svg class="k" viewBox="0 0 14 14" width="14" height="14" aria-hidden="true">${inner}</svg>`;
  return `<div class="net-key"><p class="graph-key"><span>● established</span><span>◐ supported</span><span>○ unchecked</span><span>◆ contested</span><span>✕ refuted</span><span>⊘ tried, not checkable</span></p>
<p class="graph-key"><span>${shape('<rect x="2" y="2" width="10" height="10" rx="1" class="shp" fill="none"/>')} human literature</span><span>${shape('<circle cx="7" cy="7" r="5" class="shp" fill="none"/>')} published here</span><span>${sample("e")} declared by its author</span><span>${sample("e id")} identified in the literature</span><span>${sample("e ref")} refutes</span><span>left to right: what rests on what</span></p>
<p class="graph-key"><span>size: ${esc(SIZE_WORDS[size])}${size === "same" ? "" : `, by area${top > 0 ? `; the largest here ${size === "credence" ? two(top) : one(top)}` : ""}`}</span>${lines === "same" ? "" : `<span>line width: ${esc(LINES_WORDS[lines])}</span>`}${o.focus ? `<span><svg class="k" viewBox="0 0 14 14" width="14" height="14" aria-hidden="true"><circle cx="7" cy="7" r="5" class="ring" fill="none"/></svg> the claim it is drawn around</span>` : ""}</p></div>`;
}

/**
 * The network as a figure: the drawing (it scrolls sideways on a phone rather than shrinking its words), what the marks mean,
 * and every claim drawn as a table, so nothing in the picture is only in the picture.
 */
export function claimGraph(o: NetworkOptions & { id: string; nodes: GraphNode[]; edges: GraphEdge[]; illustrative?: boolean; caption?: string; omitted?: number; title?: string }): string {
  if (!o.nodes.length) return `<p class="small">No claims on the record yet.</p>`;
  const L = layoutNetwork(o.nodes, o.edges, o);
  const byId = new Map(o.nodes.map((x) => [x.id, x] as const));
  const restsOn = (id: string) => [...new Set(o.edges.filter((e) => e.from === id && e.to !== id).map((e) => e.to))].sort(cmp).map((to) => byId.get(to)?.label ?? to);
  const svg = L.nodes.length
    ? `<div class="scroll">${networkSvg(L, o)}</div>${legend(L, o)}<p class="small scroll-hint">The drawing is wider than this screen: drag it sideways to see the rest, or read the table.</p>`
    : `<p class="small">No two claims here are joined yet: the table lists them.</p>`;
  const rows = L.nodes.length ? L.nodes.map((p) => p.node) : o.nodes;
  const table = `<details><summary>Every claim drawn, as a table${o.omitted ? ` (${n(o.omitted)} more are not drawn)` : ""}</summary><table><thead><tr><th>Claim</th><th>Status</th><th>Checkable</th><th>Credence</th><th>Use</th><th>Stakes</th><th>Rests on</th></tr></thead><tbody>${rows.map((d) => `<tr><td>${d.href ? `<a href="${esc(d.href)}">${esc(d.label)}</a>` : esc(d.label)}</td><td>${esc(STATUS_GLYPH[d.status] ?? "")} ${esc(d.status)}</td><td>${d.blocked?.length ? `⊘ ${esc(d.blocked.join(", "))}` : "yes"}</td><td>${two(d.credence)}</td><td>${n(d.use)}</td><td>${one(d.stakes ?? d.use)}</td><td>${esc(restsOn(d.id).join(", ") || "—")}</td></tr>`).join("")}</tbody></table></details>`;
  return figure({ id: o.id, title: o.title ?? "The network of claims", caption: o.caption ?? "Claims joined by links are drawn together as a group; within a group, each claim rests on the claims to its left. A refuted foundation lowers everything built on it. Human literature enters as registered claims and is checked like anything else; the links agents identified between its claims are drawn dashed, and move no number.", body: svg + table, illustrative: o.illustrative, wide: true, extraClass: "graph" });
}
