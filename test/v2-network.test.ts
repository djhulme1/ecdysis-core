/**
 * graph/0.1: the network drawing and the network view. The drawing groups claims by connectivity, puts foundations to the
 * left of what rests on them, orders each column so lines cross as little as possible, passes long lines through a waypoint
 * per column, and sizes claims and lines by the measure chosen. The view filters, sizes and centres the drawing from the
 * address bar, so every choice is checked against what it offers and every word it echoes is escaped.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { claimGraph, layoutNetwork, networkSvg, NET_WIDTH } from "../src/web/v2/network.js";
import type { GraphEdge, GraphNode } from "../src/web/v2/viz.js";
import { MemoryStore } from "../src/store/memory-store.js";
import { TransparencyLog } from "../src/core/log.js";
import { generateKeyPair, signJson, type KeyPairB64 } from "../src/core/crypto.js";
import { MemoryV2Store, V2Service } from "../src/api/v2/service.js";
import { PagesHandler } from "../src/api/v2/pages.js";
import type { Json } from "../src/core/canonical.js";
import { CONSTITUTION_VERSION, constitutionHash } from "../src/core/constitution.js";
import { declared } from "./kinds-kit.js";
import { relies, signedClaim } from "./claims-kit.js";

const node = (id: string, o: Partial<GraphNode> = {}): GraphNode => ({ id, label: `Claim ${id}`, external: false, status: "unchecked", use: 0, credence: 0.5, gen: 0, href: `/c/${id}`, stakes: 1, ...o });
const edge = (from: string, to: string, o: Partial<GraphEdge> = {}): GraphEdge => ({ from, to, rel: "extends", ...o });
const at = (L: ReturnType<typeof layoutNetwork>, id: string) => L.nodes.find((p) => p.node.id === id)!;

/** Crossings among the drawn lines between each pair of neighbouring columns, from the drawn positions. */
function crossingsOf(L: ReturnType<typeof layoutNetwork>): number {
  const segs = L.edges.flatMap((e) => e.pts.slice(1).map((b, i) => [e.pts[i]!, b] as const));
  let n = 0;
  for (let a = 0; a < segs.length; a++) for (let b = a + 1; b < segs.length; b++) {
    const [p1, p2] = segs[a]!; const [q1, q2] = segs[b]!;
    if (p1[0] !== q1[0] || p2[0] !== q2[0]) continue;
    if ((p1[1] - q1[1]) * (p2[1] - q2[1]) < 0) n++;
  }
  return n;
}

describe("the network drawing", () => {
  it("draws foundations left of what rests on them, groups joined claims, and is the same whatever order it is given", () => {
    const nodes = [node("a"), node("b"), node("c"), node("d"), node("e"), node("f")];
    const edges = [edge("b", "a"), edge("c", "b"), edge("e", "d")];
    const L = layoutNetwork(nodes, edges, { alone: true });
    for (const e of L.edges) assert.ok(e.pts[0]![0] > e.pts[e.pts.length - 1]![0], `${e.edge.from} rests on ${e.edge.to}: drawn to its right`);
    assert.equal(L.groups, 2, "a–b–c and d–e are two groups");
    assert.equal(L.alone, 1, "f stands alone");
    assert.deepEqual(L.frames.map((f) => f.caption), ["3 claims, 2 steps deep", "2 claims, 1 step deep", "Standing alone here: 1 claim"]);
    // Every claim sits inside its group's frame.
    for (const [ids, frame] of [[["a", "b", "c"], L.frames[0]!], [["d", "e"], L.frames[1]!], [["f"], L.frames[2]!]] as const) {
      for (const id of ids) { const p = at(L, id); assert.ok(p.x > frame.x && p.x < frame.x + frame.w && p.y > frame.y && p.y < frame.y + frame.h, id); }
    }
    const again = layoutNetwork([...nodes].reverse(), [...edges].reverse(), { alone: true });
    assert.equal(networkSvg(again, { id: "g", alone: true }), networkSvg(L, { id: "g", alone: true }));
    assert.equal(layoutNetwork(nodes, edges).alone, 0, "without `alone`, a claim joined to nothing is left to the table");
  });

  it("orders each column so lines do not cross when they need not, and passes a long line through a waypoint", () => {
    // Two foundations, each with its own dependent; weighted so that the first order would cross them.
    const nodes = [node("a", { stakes: 9 }), node("b", { stakes: 1 }), node("c", { stakes: 1 }), node("d", { stakes: 9 }), node("z")];
    const crossing = layoutNetwork(nodes, [edge("c", "a"), edge("d", "b"), edge("z", "c"), edge("z", "d")]);
    assert.equal(crossingsOf(crossing), 0, "the sweeps untangle them");
    // x rests on y and on w directly; y rests on w: the line from x to w spans two columns.
    const L = layoutNetwork([node("w"), node("y"), node("x")], [edge("y", "w"), edge("x", "y"), edge("x", "w")]);
    const long = L.edges.find((e) => e.edge.from === "x" && e.edge.to === "w")!;
    assert.equal(long.pts.length, 3, "a waypoint in the middle column");
    assert.equal(long.pts[1]![0], at(L, "y").x);
    // A claim resting on nothing sits just left of what rests on it, not at the far left.
    const pulled = layoutNetwork([node("w"), node("y"), node("x"), node("r")], [edge("y", "w"), edge("x", "y"), edge("x", "r")]);
    assert.equal(at(pulled, "r").x, at(pulled, "y").x, "r is pulled right, beside y");
  });

  it("sizes claims by area for the measure chosen, and lines by the credence or stakes chosen", () => {
    const nodes = [node("a", { credence: 0.95, stakes: 1, pressure: 0 }), node("b", { credence: 0.2, stakes: 8, pressure: 6 }), node("c", { credence: 0.5, stakes: 4 })];
    const edges = [edge("b", "a"), edge("c", "b")];
    const r = (o: Parameters<typeof layoutNetwork>[2], id: string) => at(layoutNetwork(nodes, edges, o), id).r;
    assert.ok(r({ size: "credence" }, "a") > r({ size: "credence" }, "c") && r({ size: "credence" }, "c") > r({ size: "credence" }, "b"));
    assert.ok(r({}, "b") > r({}, "c") && r({}, "c") > r({}, "a"), "stakes by default");
    assert.ok(r({ size: "pressure" }, "b") > r({ size: "pressure" }, "a"));
    assert.equal(r({ size: "pressure" }, "a"), r({ size: "pressure" }, "c"), "no pressure, the least size");
    assert.equal(r({ size: "same" }, "a"), r({ size: "same" }, "b"));
    const widths = (lines: "same" | "credence" | "stakes") => {
      const L = layoutNetwork(nodes, edges, { lines });
      const svg = networkSvg(L, { id: "w", lines });
      return Object.fromEntries([...svg.matchAll(/<path d="[^"]+" class="[^"]*" fill="none" stroke-width="([\d.]+)"><title>Claim (\w) /g)].map((m) => [m[2]!, Number(m[1])]));
    };
    assert.deepEqual(widths("same"), { b: 1.3, c: 1.3 });
    assert.ok(widths("credence")["b"]! > widths("credence")["c"]!, "b rests on a (0.95), c on b (0.2): the line onto weak ground is thinner");
    assert.ok(widths("stakes")["b"]! > widths("stakes")["c"]!, "b carries stakes 8, c stakes 4");
  });

  it("styles a line by what it is, fades what was not asked for, rings the claim it is centred on, and escapes every word", () => {
    const hostile = `<script>alert(1)</script> & "quotes"`;
    const nodes = [node("a", { label: hostile, external: true }), node("b"), node("c"), node("d", { blocked: ["code-unavailable"] })];
    const edges = [edge("b", "a", { identified: true }), edge("c", "b", { rel: "refutes" }), edge("d", "c")];
    const svg = claimGraph({ id: "h", nodes, edges, dim: new Set(["d"]), focus: "b" });
    assert.doesNotMatch(svg, /<script/);
    assert.match(svg, /&lt;script&gt;alert\(1\)&lt;\/script&gt; &amp; &quot;quotes&quot;/);
    assert.match(svg, /<path d="[^"]+" class="e id" fill="none"/, "identified: dashed");
    assert.match(svg, /<path d="[^"]+" class="e ref" fill="none"/, "a refutation: orange");
    assert.match(svg, /<path d="[^"]+" class="e dim" fill="none"/, "a line to a faded claim is faded");
    assert.match(svg, /<a href="\/c\/d"><g class="dim">/);
    assert.match(svg, /<a href="\/c\/b"><g class="focus"><title>[^<]*<\/title><circle [^>]*class="ring"/);
    assert.match(svg, /aria-hidden="true">⊘<\/text>/, "a blocked claim is marked");
    assert.match(svg, /declared by its author/);
    assert.match(svg, /identified in the literature/);
    assert.match(svg, /the claim it is drawn around/);
    // A long label is cut, at a word, to fit its column.
    const long = layoutNetwork([node("p", { label: "word ".repeat(40).trim() }), node("q")], [edge("q", "p")]);
    assert.ok(at(long, "p").label!.endsWith("…") && at(long, "p").label!.length < 40);
  });

  it("sections by field when asked, with each section's groups and the claims standing alone in it", () => {
    const nodes = [node("a", { field: "Mathematics" }), node("b", { field: "Mathematics" }), node("c", { field: "Physics" }), node("d", { field: "Mathematics" })];
    const L = layoutNetwork(nodes, [edge("b", "a")], { group: "field", alone: true });
    assert.deepEqual(L.frames.map((f) => f.caption), ["Mathematics: 3 claims", "2 claims, 1 step deep", "Standing alone here: 1 claim", "Physics: 1 claim", "Standing alone here: 1 claim"]);
    assert.equal(L.width, NET_WIDTH);
  });
});

/* -------------------------------------------------------------------------------------------------------------------- */
/* The network view, end to end                                                                                            */

const ACK = { version: CONSTITUTION_VERSION, hash: await constitutionHash() };
const QUOTE = "Building directly on the threshold measured by the earlier study, we confirm the transition at the same ratio.";

async function world() {
  const clock = { t: Date.UTC(2026, 9, 6, 9, 0, 0) };
  const now = () => new Date(clock.t);
  const logStore = new MemoryStore();
  const log = new TransparencyLog(logStore, now);
  const logKey = await generateKeyPair();
  const v2store = new MemoryV2Store(() => (logStore as unknown as { log: Array<{ entry: { seq: number; ts: string; type: string }; payload: Json }> }).log.map((r) => ({ seq: r.entry.seq, ts: r.entry.ts, type: r.entry.type, payload: r.payload })));
  const svc = new V2Service({ log, store: v2store, logPrivateKey: logKey.privateKey, now });
  const pages = new PagesHandler(svc);
  const keys = new Map<string, KeyPairB64>();
  const agent = async (handle: string, op: string) => {
    const kp = await generateKeyPair();
    keys.set(handle, kp);
    assert.equal((await svc.registerAgent({ constitution: ACK, handle, publicKey: kp.publicKey, operatorId: op })).status, 201);
    await svc.setTier(op, "verified");
    return kp;
  };
  const ts = () => { clock.t += 60_000; return now().toISOString().replace(/\.\d{3}Z$/, "Z"); };
  const sign = async (handle: string, payload: Record<string, Json>) => {
    const kp = keys.get(handle)!;
    const full: Json = declared({ ...payload, agent: { handle, publicKey: kp.publicKey }, ts: ts() });
    return { payload: full, signature: await signJson(kp.privateKey, full) } as Json;
  };
  const register = async (handle: string, source: string, quote: string) => {
    const r = await svc.registerExternalClaim(await sign(handle, { protocol: "ecdysis/0.2", type: "claim.external", source, quote, test: "A re-run of the paper's own experiment giving a value outside its interval." }));
    assert.equal(r.status, 201, JSON.stringify(r.body));
    return String((r.body as Record<string, Json>)["ref"]);
  };
  const link = async (handle: string, from: string, to: string) => {
    const r = await svc.linkClaims(await sign(handle, { protocol: "ecdysis/0.2", type: "claim.link", from, to, rel: "extends", basis: "identified", evidence: { quote: QUOTE, where: "Section 2" } }));
    assert.ok(r.status === 201, JSON.stringify(r.body));
  };
  const get = async (path: string, search = "") => {
    const r = (await pages.handle("GET", path, "text/html", false, search))!;
    return { status: r.status, html: await r.text(), csp: r.headers.get("content-security-policy") ?? "" };
  };
  return { svc, agent, sign, register, link, get, ts };
}

/** The claims a page's drawing names, faded or not: its nodes' links, in drawing order. */
const drawnIds = (html: string) => [...html.matchAll(/<a href="\/c\/([^"]+)"><g( class="(?:dim|focus)")?>/g)].map((m) => `${m[1]}${m[2] ? ` ${m[2].slice(8, -1)}` : ""}`);

describe("the network view", () => {
  it("draws the claims with their links, filters by the table's choices, fades or hides the rest, and centres on a claim", async () => {
    const w = await world();
    const ant = await w.agent("Ant", "op-a");
    await w.agent("Exuvia", "op-x");
    const first = await signedClaim({ handle: "Ant", ...ant }, { text: "First claim: the gap closes under weight decay at the stated scale.", test: "The gap stays open for 10^5 steps.", field: "ml", ts: w.ts() });
    assert.equal((await w.svc.publishClaim(first.envelope)).status, 201);
    const second = await signedClaim({ handle: "Ant", ...ant }, { text: "Second claim: the same gap closes on a second task as well.", test: "The gap stays open on the second task.", field: "ml", builds_on: [relies(first.id, "extends", "reviewed")], ts: w.ts() });
    assert.equal((await w.svc.publishClaim(second.envelope)).status, 201);
    const older = await w.register("Exuvia", "doi:10.1000/mitchell.1992", "the hardest instances of random 3-SAT occur at a ratio of clauses to variables of about 4.3");
    const newer = await w.register("Exuvia", "doi:10.1000/crawford.1996", "the crossover point for random 3-SAT lies at a ratio of 4.24 for large instances");
    const lone = await w.register("Exuvia", "doi:10.1000/unrelated.2001", "an unrelated finding that nothing on the record rests on at all");
    await w.link("Exuvia", newer, older);

    const all = await w.get("/network");
    assert.equal(all.status, 200);
    assert.match(all.csp, /default-src 'none'/);
    assert.match(all.csp, /form-action 'self'/, "the form submits to the site itself, and nowhere else");
    assert.doesNotMatch(all.html, /<script/);
    assert.deepEqual(drawnIds(all.html).sort(), [first.id, second.id, newer, older, lone].sort());
    assert.match(all.html, /<p class="count" role="status">5 claims; 2 links between those drawn\.<\/p>/);
    assert.match(all.html, /<path d="[^"]+" class="e id" fill="none"/, "the identified link, dashed");
    assert.match(all.html, /<path d="[^"]+" class="e" fill="none"/, "the declared one, solid");
    assert.match(all.html, /Standing alone here: 1 claim/);
    assert.match(all.html, /<nav class="views" aria-label="See the claims as"><a href="\/claims">Table<\/a><a href="\/network" aria-current="page">Network<\/a><\/nav>/);

    // Filters fade what they leave out, or hide it; the links between what is left stay.
    const faded = await w.get("/network", "?origin=literature");
    assert.deepEqual(drawnIds(faded.html).filter((x) => x.endsWith(" dim")).sort(), [`${first.id} dim`, `${second.id} dim`].sort());
    assert.match(faded.html, /5 claims, 3 as asked; the rest are drawn faded, for the shape/);
    const hidden = await w.get("/network", "?origin=literature&rest=hide");
    assert.deepEqual(drawnIds(hidden.html).sort(), [newer, older, lone].sort());
    const identified = await w.get("/network", "?links=identified&rest=hide");
    assert.equal((identified.html.match(/<path d="M/g) ?? []).length, 1, "only the identified link");
    const declaredOnly = await w.get("/network", "?links=declared");
    assert.doesNotMatch(declaredOnly.html, /<path d="[^"]+" class="e id"/);

    // Centred on a claim: what lies within the links asked for, the claim ringed, a pill to stop.
    const around = await w.get("/network", `?depth=1&focus=${encodeURIComponent(newer)}`);
    assert.deepEqual(drawnIds(around.html).sort(), [`${newer} focus`, older].sort());
    assert.match(around.html, /<input type="hidden" name="focus" value="ext:[0-9a-f]{16}">/);
    assert.match(around.html, /<a class="pill" href="\/network" aria-label="Stop centring on this claim">Around: the crossover point/);
    assert.match(around.html, /<select name="depth"><option value="">2 links<\/option><option value="1" selected>1 link<\/option>/);
    // A group's caption draws that group alone.
    assert.match(all.html, /<a href="\/network\?depth=all&amp;focus=(?:ecd|ext)%3A[0-9a-f]{16}"><text class="cap"/);

    // Sizes and widths are the reader's choice; the legend says which.
    const sized = await w.get("/network", "?size=credence&lines=credence");
    assert.match(sized.html, /size: credence, by area/);
    assert.match(sized.html, /line width: the credence of the claim it rests on/);
    const grouped = await w.get("/network", "?group=field");
    assert.match(grouped.html, /<text class="cap sec"[^>]*>machine learning: 2 claims<\/text>/);
  });

  it("ignores what it does not offer and escapes what it echoes, so a hostile address changes nothing but what is drawn", async () => {
    const w = await world();
    const ant = await w.agent("Ant", "op-a");
    const c = await signedClaim({ handle: "Ant", ...ant }, { text: "A claim with a test of its own, published here for the view.", test: "It fails on a fresh seed.", field: "ml", ts: w.ts() });
    assert.equal((await w.svc.publishClaim(c.envelope)).status, 201);
    const hostile = await w.get("/network", `?q=${encodeURIComponent('"><script>alert(1)</script>')}&size=__proto__&lines=%3Cb%3E&group=x&rest=all&depth=-1&focus=${encodeURIComponent("<img src=x onerror=alert(1)>")}&status=${encodeURIComponent('" onmouseover="x')}`);
    assert.equal(hostile.status, 200);
    assert.doesNotMatch(hostile.html, /<script|<img src=x|onmouseover="x/, "nothing from the address becomes markup (the page's own images are its logo)");
    assert.match(hostile.html, /value="&quot;&gt;&lt;script&gt;alert\(1\)&lt;\/script&gt;"/);
    assert.doesNotMatch(hostile.html, /name="focus"|Around:/, "a claim not on the record is no centre");
    assert.doesNotMatch(hostile.html, /Status: /, "a status the view does not offer is no filter");
    assert.match(hostile.html, /<select name="size"><option value="">Stakes<\/option>(?:<option value="\w+">[^<]+<\/option>)+<\/select>/, "an unknown size is the default, and nothing else is chosen");
    assert.match(hostile.html, /No claims match\. Clear a filter or search for something else\./);
    assert.match(hostile.csp, /form-action 'self'/);
  });

  it("carries the search and shared filters between the table and the network, and the table filters by stage", async () => {
    const w = await world();
    const ant = await w.agent("Ant", "op-a");
    await w.agent("Bee", "op-b");
    const c = await signedClaim({ handle: "Ant", ...ant }, { text: "A claim to check: the threshold sits at the stated ratio exactly.", test: "The threshold lies elsewhere.", field: "ml", ts: w.ts() });
    assert.equal((await w.svc.publishClaim(c.envelope)).status, 201);
    const d = await signedClaim({ handle: "Ant", ...ant }, { text: "A claim nobody has tried: the effect holds beyond the panel.", test: "The effect vanishes beyond the panel.", field: "ml", ts: w.ts() });
    assert.equal((await w.svc.publishClaim(d.envelope)).status, 201);
    const tried = await w.svc.fileAttempt(await w.sign("Bee", { protocol: "ecdysis/0.2", type: "check.attempt", claim: c.id, blocker: "compute", read: "full", detail: "The stated run needs eight GPUs for a week; the claim's own bundle declares 10,080 minutes and nothing smaller is stated.", unblockedBy: "A smaller instance stated in the protocol, or a grant of compute." }));
    assert.equal(tried.status, 201, JSON.stringify(tried.body));

    const table = await w.get("/claims", "?stage=attempted&q=threshold");
    assert.match(table.html, /<a href="\/network\?q=threshold&amp;stage=attempted">Network<\/a>/);
    assert.match(table.html, new RegExp(`href="/c/${c.id}"`));
    assert.doesNotMatch(table.html, new RegExp(`<a class="t" href="/c/${d.id}"`));
    const untried = await w.get("/claims", "?stage=untried");
    assert.match(untried.html, new RegExp(`<a class="t" href="/c/${d.id}"`));
    assert.doesNotMatch(untried.html, new RegExp(`<a class="t" href="/c/${c.id}"`));
    const net = await w.get("/network", "?stage=attempted&size=credence&q=threshold");
    assert.match(net.html, /<a href="\/claims\?q=threshold&amp;stage=attempted">Table<\/a>/, "the drawing's own choices stay with the drawing");
    const claim = await w.get(`/c/${c.id}`);
    assert.match(claim.html, new RegExp(`<a href="/network\\?focus=${c.id.replace(":", "%3A")}">In the network</a>`));
  });
});
