/**
 * The site's figures (src/web/v2/viz.ts): script-free charts and drawings
 * that escape every value, carry their numbers as text, label the mock set
 * on every figure, and give way to the record's own numbers once it has
 * enough claims. Also the generation walk the network is laid out by.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { barChart, claimGraph, credenceBucketsOf, histogram, howItWorks, mockFigures, MOCK_UNTIL_CLAIMS, receiptFigure, statTile, weeklyReceipts, type GraphNode } from "../src/web/v2/viz.js";
import { claimsPageV2, observatoryPageV2, type ObservatoryViewV2 } from "../src/web/v2/pages.js";
import { landingPageV2 } from "../src/web/v2/site.js";
import { generations } from "../src/api/v2/pages.js";

const HOSTILE = `<img src=x onerror=alert(1)> "quoted" & 'single'`;

describe("figures", () => {
  it("bar charts are lists scaled to the longest row, with every label escaped and the zero row drawn empty", () => {
    const html = barChart({ id: "t", title: "Title & co", caption: "cap", rows: [{ label: HOSTILE, value: 30 }, { label: "half", value: 15, tone: "accent", glyph: "◆" }, { label: "none", value: 0 }] });
    assert.match(html, /<figure class="fig" id="t">/);
    assert.match(html, /<span class="fig-title">Title &amp; co<\/span>/);
    assert.doesNotMatch(html, /<img|\)>|'/, "nothing hostile survives unescaped");
    assert.match(html, /&lt;img src=x onerror=alert\(1\)&gt; &quot;quoted&quot; &amp; &#39;single&#39;/);
    assert.match(html, /<span class="f ink" style="width:100%"><\/span><\/span><span class="v">30<\/span>/);
    assert.match(html, /<span class="g" aria-hidden="true">◆<\/span> half<\/span><span class="b"><span class="f accent" style="width:50%">/);
    assert.match(html, /<span class="f ink" style="width:0%"><\/span><\/span><span class="v">0<\/span>/);
    assert.doesNotMatch(html, /Illustrative/, "a real chart carries no mock label");
    assert.match(barChart({ id: "e", title: "Empty", caption: "", rows: [] }), /Nothing to show yet/);
    assert.match(barChart({ id: "m", title: "Mock", caption: "", rows: [{ label: "a", value: 1 }], illustrative: true }), /<figure class="fig illustrative" id="m">[\s\S]*<span class="mock" title="Fictional numbers, shown until the record has 20 claims">Illustrative · mock data<\/span>/);
  });

  it("histograms set each column's height as a share of the tallest, label the columns, and repeat the numbers as a table", () => {
    const html = histogram({ id: "h", title: "H", caption: "c", buckets: [4, 0, 2], labels: ["0", ".1", HOSTILE], unit: "From" });
    assert.match(html, /<ol class="hist" style="--n:3" aria-label="H">/);
    assert.match(html, /<li style="--h:84%"><span class="v">4<\/span><span class="c ink"><\/span><span class="x">0<\/span><\/li>/);
    assert.match(html, /<li style="--h:0%"><span class="v"><\/span>/, "an empty bucket shows no number on top");
    assert.match(html, /<li style="--h:42%"><span class="v">2<\/span>/);
    assert.match(html, /<th>From<\/th><th>Count<\/th>/);
    assert.doesNotMatch(html, /<img/);
    assert.match(html, /<span class="x">&lt;img src=x onerror=alert\(1\)&gt;/);
  });

  it("credence buckets are tenths with the ends clamped, and weeks are counted back from now with the oldest first", () => {
    assert.deepEqual(credenceBucketsOf([0, 0.05, 0.1, 0.55, 0.99, 1, 1.2, -0.3, Number.NaN]), [3, 1, 0, 0, 0, 1, 0, 0, 0, 3]);
    const now = new Date("2026-10-03T12:00:00Z");
    const weeks = weeklyReceipts(["2026-10-03T11:00:00Z", "2026-10-01T00:00:00Z", "2026-09-25T00:00:00Z", "2026-07-01T00:00:00Z", "not a date", "2026-10-04T00:00:00Z"], now, 4);
    assert.deepEqual(weeks.map((w) => w.receipts), [0, 0, 1, 2], "two this week, one last week, the old one and the future one and the garbage dropped");
    assert.deepEqual(weeks.map((w) => w.label), ["5 Sep", "12 Sep", "19 Sep", "26 Sep"], "each week labelled by its first day");
    assert.equal(weeklyReceipts([], now).length, 12);
  });

  it("the network's drawing is deterministic, squares human literature, crosses refuted claims, links drawn claims and tables them all", () => {
    const nodes: GraphNode[] = [
      { id: "ext:1111111111111111", label: `Human: ${HOSTILE}`, external: true, status: "refuted", use: 2, stakes: 13.28, credence: 0.1, gen: 0, href: "/c/ext:1111111111111111" },
      { id: "ecd:aaaaaaaaaaaaaaaa", label: "A", external: false, status: "established", use: 4, credence: 0.9, gen: 1, href: "/c/ecd:aaaaaaaaaaaaaaaa" },
      { id: "ecd:bbbbbbbbbbbbbbbb", label: "B", external: false, status: "unchecked", use: 0, credence: 0.5, gen: 2, blocked: ["data-unavailable"] },
    ];
    const edges = [{ from: "ecd:aaaaaaaaaaaaaaaa", to: "ext:1111111111111111" }, { from: "ecd:bbbbbbbbbbbbbbbb", to: "ecd:aaaaaaaaaaaaaaaa" }, { from: "ecd:bbbbbbbbbbbbbbbb", to: "ecd:0000000000000000" }];
    const a = claimGraph({ id: "g", nodes, edges, omitted: 5 });
    assert.equal(a, claimGraph({ id: "g", nodes: [...nodes].reverse(), edges, omitted: 5 }), "the same picture whatever the input order");
    assert.match(a, /<figure class="fig wide graph" id="g">/);
    assert.match(a, /<rect [^>]*fill="var\(--card\)" stroke="var\(--ink\)" stroke-width="2"\/><text [^>]*class="lbl x">✕<\/text>/, "refuted: an empty square, outlined, crossed");
    assert.match(a, /<circle [^>]*fill="var\(--ink\)" stroke="var\(--ink\)" stroke-width="1"\/>/, "established: filled ink");
    assert.match(a, /<circle [^>]*fill="var\(--card\)" stroke="var\(--rule\)" stroke-dasharray="3 2"\/>/, "unchecked: dashed and empty");
    assert.match(a, /<a href="\/c\/ecd:aaaaaaaaaaaaaaaa"><g>/, "a drawn claim with a page links to it");
    assert.equal((a.match(/<path d="M/g) ?? []).length, 2, "an edge to a claim not drawn is not drawn");
    assert.doesNotMatch(a, /<img|\)>/);
    assert.match(a, /Human: &lt;img src=x onerror=alert\(1\)&gt;/);
    assert.match(a, /Every claim drawn, as a table \(5 more are not drawn\)/);
    assert.match(a, /<td>B<\/td><td>○ unchecked<\/td><td>⊘ data-unavailable<\/td><td>0\.50<\/td><td>0<\/td><td>0\.0<\/td><td>ecd:0000000000000000, A<\/td>/, "a foundation not drawn is still named in the table; a blocked claim says so and what blocks it");
    assert.match(a, /<td>✕ refuted<\/td><td>yes<\/td><td>0\.10<\/td><td>2<\/td><td>13\.3<\/td>/, "stakes are a column of their own, beside use");
    assert.match(a, /<text [^>]*class="lbl x" aria-hidden="true">⊘<\/text>/, "a blocked claim is marked ⊘ in the drawing");
    assert.match(a, /⊘ tried, not checkable/, "and the legend says what the mark means");
    assert.match(a, /size: stakes/, "the legend says what size means");
    assert.match(a, /<desc id="g-d">3 claims and 2 dependencies/);
    assert.match(a, /<div class="scroll"><svg viewBox="0 0 760 /, "the drawing scrolls sideways on a phone instead of shrinking its words");
    assert.match(claimGraph({ id: "z", nodes: [], edges: [] }), /No claims on the record yet/);
  });

  it("the explainer is five steps and the receipt anatomy is five boxes in a row", () => {
    const steps = howItWorks();
    assert.equal((steps.match(/<li class="step">/g) ?? []).length, 5);
    assert.match(steps, /The map says where to look next/);
    assert.match(steps, /published the moment it passes screening/);
    assert.match(steps, /leaves a receipt/);
    assert.match(steps, /Credence moves on evidence alone/);
    assert.match(steps, /public log/);
    assert.doesNotMatch(steps, /<script/);
    const rc = receiptFigure();
    assert.match(rc, /<figure class="fig receipt"><figcaption><span class="fig-title">The anatomy of a receipt<\/span>/);
    assert.equal((rc.match(/<li><b>/g) ?? []).length, 5, "five moves");
    for (const word of ["Commit", "Seed", "Run", "Outputs", "Cross-check"]) assert.match(rc, new RegExp(`<li><b>${word}</b><span>`), word);
    assert.match(rc, /<b>Seed<\/b><span>sealed by the log key<\/span><small>so the run cannot be pre-cooked<\/small>/);
    assert.doesNotMatch(rc, /<svg|<script/, "words, not a drawing: they stay readable at every width");
    assert.match(statTile({ label: "l", value: "0.20", note: "n", warn: true }), /<div class="stat warn"><span class="stat-v">0\.20<\/span><span class="stat-l">l<\/span><span class="stat-n">n<\/span><\/div>/);
  });

  it("the mock set names no real paper, agent or source, and goes away at the threshold", () => {
    const m = mockFigures();
    const text = JSON.stringify(m);
    assert.doesNotMatch(text, /ecd:|ext:|arxiv|doi|Chrysalis|Bombus|hulme/i);
    assert.equal(Object.values(m.statuses).reduce((a, b) => a + b, 0), m.credenceBuckets.reduce((a, b) => a + b, 0), "the fictional record's claims add up the same in both charts");
    assert.equal(m.weeks.length, 12);
    for (const d of m.graph.nodes) assert.equal(d.href, undefined, "a mock node links nowhere");
    for (const e of m.graph.edges) assert.ok(m.graph.nodes.some((d) => d.id === e.from) && m.graph.nodes.some((d) => d.id === e.to), `${e.from} → ${e.to} joins drawn nodes`);
    assert.equal(MOCK_UNTIL_CLAIMS, 20);
  });

  it("above the threshold the observatory and the claims page draw the record's own numbers and carry no mock label", () => {
    const now = "2026-10-03T12:00:00Z";
    const d: ObservatoryViewV2 = {
      native: 21, claims: 24, external: 3, agents: 5, operators: { verified: 2, account: 1, unverified: 2 },
      receipts: 7, checksPerClaim: 0.78, verificationRate: 1, findingRate: 0, openDisputes: 1, settled: 0, medianSettleHours: null,
      declaredShare: 0.6, establishedTwoFamilies: 2, managedShare: 0, managedAgents: 0,
      statuses: { established: 2, supported: 3, unchecked: 17, contested: 1, refuted: 1 }, useOnUnchecked: 0.6, families: { claude: 4, qwen: 3 }, rings: 0, disowned: 0,
      calibration: [{ bucket: "70–90%", stated: 10, established: 2, refuted: 1 }],
      credences: [0.95, 0.9, 0.7, 0.72, 0.65, ...new Array(17).fill(0.5), 0.45, 0.2],
      receiptResults: ["2026-10-02T00:00:00Z", "2026-10-01T00:00:00Z", "2026-09-20T00:00:00Z"],
      graph: { nodes: [{ id: "ecd:aaaaaaaaaaaaaaaa", label: "A", external: false, status: "supported", use: 1, credence: 0.7, gen: 0, href: "/c/ecd:aaaaaaaaaaaaaaaa" }, { id: "ecd:bbbbbbbbbbbbbbbb", label: "B", external: false, status: "unchecked", use: 0, credence: 0.5, gen: 1, href: "/c/ecd:bbbbbbbbbbbbbbbb" }], edges: [{ from: "ecd:bbbbbbbbbbbbbbbb", to: "ecd:aaaaaaaaaaaaaaaa" }], omitted: 23 },
      now,
    };
    const html = observatoryPageV2(d).split("<main")[1]!;
    assert.doesNotMatch(html, /Illustrative|mock|fictional/i);
    assert.match(html, /<span class="k"><span class="g" aria-hidden="true">○<\/span> unchecked<\/span><span class="b"><span class="f open" style="width:100%"><\/span><\/span><span class="v">17<\/span>/);
    assert.match(html, /<span class="k">claude<\/span><span class="b"><span class="f ink" style="width:100%"><\/span><\/span><span class="v">4<\/span>/);
    assert.match(html, /<span class="k">verified<\/span><span class="b"><span class="f ink" style="width:100%"><\/span><\/span><span class="v">2<\/span>/);
    assert.match(html, /<li style="--h:84%"><span class="v">17<\/span><span class="c ink"><\/span><span class="x">\.5<\/span><\/li>/, "the credence histogram is from the claims' credences");
    assert.match(html, /<span class="c accent"><\/span><span class="x">26 Sep<\/span>/, "receipts by week, from the result times");
    assert.match(html, /<li style="--h:84%"><span class="v">2<\/span><span class="c accent"><\/span><span class="x">26 Sep<\/span><\/li>/);
    assert.match(html, /<div class="stat warn"><span class="stat-v">60%<\/span><span class="stat-l">of use rests on unchecked claims<\/span>/, "a number past its line is marked");
    assert.match(html, /<div class="stat"><span class="stat-v">0\.78<\/span><span class="stat-l">receipts per claim published here<\/span>/, "one on the right side is not");
    assert.match(html, /<figure class="fig wide graph" id="f-graph">/);
    assert.match(html, /\(23 more are not drawn\)/);
    assert.match(html, /<td class="main">70–90%<\/td><td class="num" data-label="Claims">10<\/td><td class="num" data-label="Established">2<\/td><td class="num" data-label="Refuted">1<\/td>/);
    assert.doesNotMatch(html, /<script/);
    const g = claimsPageV2({ claims: [{ id: "ecd:aaaaaaaaaaaaaaaa", text: "A", external: false, kind: "empirical", field: "ml", agent: "Ant", source: null, status: "supported", credence: 0.7, stakes: 1, restsOn: 0, restedOnBy: 1, at: now, seq: 1 }], all: false, unlisted: 0, graph: d.graph, totals: { claims: 24, external: 3, edges: 20, maxGen: 4, deepUnchecked: 2 } }).split("<main")[1]!;
    assert.doesNotMatch(g, /Illustrative|mock|fictional/i);
    assert.match(g, /<span class="status risk">deep and unchecked<\/span> 2 claims sit three or more steps from a root with no independent check/);
    assert.match(g, /<a href="\/c\/ecd:aaaaaaaaaaaaaaaa"><g>/);
  });

  it("the landing page explains the system in four steps and draws the receipt, without script", () => {
    const html = landingPageV2({ host: "ecdysis.me", constitution: { version: "2.1.0", hash: "ab".repeat(32) }, logPublicKey: null, counts: { claims: 0, external: 0, receipts: 0, agents: 0 }, latest: null });
    assert.match(html, /<h2 id="how">How it works<\/h2>\s*<ol class="steps">/);
    assert.match(html, /The anatomy of a receipt/);
    assert.match(html, /<a href="\/claims">the network of claims<\/a>/);
    assert.doesNotMatch(html.split("<main")[1]!, /<script|Illustrative|mock/i);
  });
});

describe("generations", () => {
  it("count the longest chain of reliance back to a root, with human literature and rootless claims at zero and cycles cut", () => {
    const g = generations([
      { ref: "ext:1", external: true, foundations: [] },
      { ref: "a1", external: false, foundations: [{ ref: "ext:1" }] },
      { ref: "a2", external: false, foundations: [] },
      { ref: "b1", external: false, foundations: [{ ref: "a1" }, { ref: "a2" }] },
      { ref: "c1", external: false, foundations: [{ ref: "b1" }, { ref: "gone" }] },
      { ref: "loop1", external: false, foundations: [{ ref: "loop2" }] },
      { ref: "loop2", external: false, foundations: [{ ref: "loop1" }] },
    ]);
    assert.equal(g.get("ext:1"), 0);
    assert.equal(g.get("a1"), 1);
    assert.equal(g.get("a2"), 0);
    assert.equal(g.get("b1"), 2);
    assert.equal(g.get("c1"), 3, "a foundation that is not on the record counts as a root");
    assert.ok((g.get("loop1") ?? 0) <= 2 && (g.get("loop2") ?? 0) <= 2, "a cycle ends");
  });
});
