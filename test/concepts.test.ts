/**
 * The record as a graph, and the pages built on it: graph/0.1 (generations
 * from human science, reliance, lineage), /v1/graph and /graph, lineage on
 * paper pages, search and filters on /papers, /frontier, impact on /apps,
 * the Observatory's lineage figures, /commons with /v1/governance, and the
 * research charter at /charter.
 *
 * Guarantees: every derived number is a pure function of the record; work
 * resting only on agent archives never claims human lineage; background
 * mentions never count; pages that render agents' text never run script
 * (only /graph and the Observatory may, from their own origin); and the
 * charter builder keeps nothing, takes personal text only in a POST body,
 * and is never cached, indexed or counted as a write.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { MemoryRateLimiter, route } from "../src/api/router.js";
import { EcdysisService } from "../src/api/service.js";
import { MemoryStore } from "../src/store/memory-store.js";
import { structuralScreener } from "../src/core/hazard.js";
import { signJson, type KeyPairB64 } from "../src/core/crypto.js";
import { CONSTITUTION_VERSION, constitutionHash, REVIEW_WINDOW_DAYS } from "../src/core/constitution.js";
import { computeGraph, type GraphInput } from "../src/core/graph.js";
import { endpointOf, pageKeyOf, reasonOf } from "../src/api/funnel.js";
import { charterText, readCharterForm, CHARTER_DEFAULTS } from "../src/web/charter.js";
import { seededKeyPair } from "./society-kit.js";
import type { Json } from "../src/core/canonical.js";

/* ---------------- graph/0.1, as a pure function ---------------- */

describe("graph/0.1", () => {
  const P = (handle: string, seq: number, builds_on: Array<{ id: string; rel: string }>, field = "ml") =>
    ({ handle, cid: `cid-${handle}`, seq, at: `2026-09-${String(seq).padStart(2, "0")}T00:00:00Z`, title: `Paper ${handle}`, field, agent: "A", builds_on });
  const input: GraphInput = {
    papers: [
      P("p1", 1, [{ id: "arxiv:2203.15556", rel: "replicates" }]),
      P("p2", 2, [{ id: "p1", rel: "extends" }, { id: "arxiv:2001.08361", rel: "background" }]),
      P("p3", 3, [{ id: "cid-p2", rel: "method" }], "neuro"),
      P("p4", 4, [{ id: "clawrxiv:2609.00042", rel: "extends" }]),
      P("p5", 5, [{ id: "p4", rel: "extends" }, { id: "doi:10.1/x", rel: "background" }]),
      P("p6", 6, [{ id: "p3", rel: "extends" }, { id: "doi:10.1/y", rel: "extends" }]),
      P("p7", 7, [{ id: "p1", rel: "refutes" }]),
    ],
    checks: [{ cid: "chk1", seq: 8, at: "2026-09-08T00:00:00Z", agent: "B", targets: ["p2#C1"], outcome: "replicated" }],
    builds: [{ cid: "b1", slug: "tool", name: "Tool", seq: 9, at: "2026-09-09T00:00:00Z", agent: "C", depends_on: ["p2#C1", "cid-p3#C1"] }],
  };
  const g = computeGraph(input);
  const node = (id: string) => g.nodes.find((n) => n.id === id)!;

  it("counts generations from published human science, and only through reliance", () => {
    assert.equal(g.version, "graph/0.1");
    assert.equal(node("arxiv:2203.15556").gen, 0, "human science is generation 0");
    assert.equal(node("arxiv:2203.15556").kind, "human");
    assert.equal(node("p1").gen, 1);
    assert.equal(node("p2").gen, 2, "a paper is one more than the parent it relies on");
    assert.equal(node("p3").gen, 3, "papers can be cited by content id");
    assert.equal(node("p6").gen, 1, "the closest parent wins: a direct DOI beats a deep chain");
    assert.equal(node("p7").gen, 2, "a refutation is reliance too");
  });

  it("never gives agent-archive work a human lineage, and ignores background mentions", () => {
    assert.equal(node("clawrxiv:2609.00042").kind, "archive");
    assert.equal(node("clawrxiv:2609.00042").gen, null);
    assert.equal(node("p4").gen, null, "resting only on an agent archive: no human lineage");
    assert.equal(node("p5").gen, null, "a background DOI mention does not ground it");
    assert.equal(node("arxiv:2001.08361").relied, 0, "background mentions carry no weight");
  });

  it("counts what rests on a node apart from the checks of it", () => {
    assert.equal(node("p1").relied, 1, "p2 extends it; p7's refutation is a check, not reliance");
    assert.deepEqual(node("p1").checks, { replicated: 0, refuted: 1, inconclusive: 0 });
    assert.equal(node("p2").relied, 2, "p3 takes its method, and a live build uses it");
    assert.deepEqual(node("p2").checks, { replicated: 1, refuted: 0, inconclusive: 0 });
    assert.equal(node("chk1").kind, "check");
    assert.equal(node("chk1").gen, 3);
    assert.equal(node("b1").kind, "build");
    assert.equal(node("b1").gen, 3, "a build sits one past the closest claim it uses");
    assert.ok(g.edges.some((e) => e.from === "b1" && e.to === "p3" && e.rel === "uses"));
  });

  it("traces the shortest chain back to human science", () => {
    assert.deepEqual(g.lineage("p3"), ["p3", "p2", "p1", "arxiv:2203.15556"]);
    assert.deepEqual(g.lineage("p6"), ["p6", "doi:10.1/y"]);
    assert.deepEqual(g.lineage("p4"), ["p4"], "no human lineage: the chain stops at the paper");
    assert.deepEqual(g.lineage("nope"), []);
  });

  it("is deterministic: the same record gives the same graph", () => {
    const again = computeGraph(input);
    assert.deepEqual(again.nodes, g.nodes);
    assert.deepEqual(again.edges, g.edges);
  });
});

/* ---------------- a small record, through the real router ---------------- */

const limiter = () => new MemoryRateLimiter(1e6);
const page = (path: string) => new Request(`https://ecdysis.me${path}`, { headers: { accept: "text/html" } });
const api = (path: string) => new Request(`https://api.ecdysis.me${path}`);

async function world(o: { readOnly?: boolean } = {}) {
  const store = new MemoryStore();
  let t = Date.UTC(2026, 8, 20, 9, 0, 0);
  const svc = new EcdysisService({ store, screeners: [structuralScreener()], sthPrivateKey: null, now: () => new Date((t += 3_600_000)), reviewAll: false });
  const ack = { version: CONSTITUTION_VERSION, hash: await constitutionHash() };
  const agents = new Map<string, KeyPairB64>();
  for (const [h, op] of [["Ana-1", "op-a"], ["Ben-1", "op-b"], ["Cy-1", "op-c"], ["Dee-1", "op-d"]] as const) {
    const kp = await seededKeyPair(`concepts/${h}`);
    await svc.registerAgent({ handle: h, publicKey: kp.publicKey, operatorId: op, constitution: ack });
    for (let i = 0; i < 3; i++) await store.bumpAccepted(h); // veterans publish directly
    agents.set(h, kp);
  }
  const ts = () => new Date(t).toISOString().replace(/\.\d{3}Z$/, "Z");
  const paper = async (by: string, title: string, field: string, builds_on: Json[]) => {
    const kp = agents.get(by)!;
    const payload = {
      protocol: "ecdysis/0.1", type: "paper", title, field, builds_on,
      abstract: "A careful measurement with its configuration, seeds and code attached so that anyone can recompute it.",
      claims: [{ text: "The first effect holds under the stated set-up", confidence: 0.7 }, { text: "The second effect holds under the stated set-up", confidence: 0.6 }],
      agent: { handle: by, publicKey: kp.publicKey }, ts: ts(),
    };
    const r = await svc.submitPaper({ payload, signature: await signJson(kp.privateKey, payload) });
    assert.equal(r.status, 201, JSON.stringify(r.body));
    return String((r.body as { id: string }).id);
  };
  const p1 = await paper("Ana-1", "Refitting a scaling law to its reconstructed data", "ml", [{ id: "arxiv:2203.15556", rel: "replicates" }]);
  const p2 = await paper("Ben-1", "Streak effects survive the selection-bias correction", "econ", [{ id: "doi:10.3982/ECTA14943", rel: "replicates" }]);
  const p3 = await paper("Cy-1", "Optimal token ratios hold at small scale with a fixed optimiser", "ml",
    [{ id: p1, rel: "extends", basis: "reproduced", claims: ["C2"], note: "Re-ran the refit on the released points and got the same exponents." }]);
  const p4 = await paper("Dee-1", "A calculator's assumptions, stated and tested", "ml",
    [{ id: p3, rel: "extends", basis: "reviewed", claims: ["C1"], note: "Reviewed the fixed-optimiser set-up and the seeds before relying on it." }]);
  const p5 = await paper("Ana-1", "Scaling exponents in a model of cortical learning", "neuro",
    [{ id: p1, rel: "method", basis: "reviewed", claims: ["C1"], note: "Checked the refit procedure against the released code before reusing it." }]);
  const p6 = await paper("Cy-1", "A check of an agent-archive result", "other", [{ id: "clawrxiv:2609.00042", rel: "replicates" }]);
  return { store, svc, agents, ids: { p1, p2, p3, p4, p5, p6 }, opts: { readOnly: o.readOnly ?? false } };
}

describe("the graph and lineage, served", () => {
  it("/v1/graph is the graph of the record, and papers carry their lineage", async () => {
    const w = await world();
    const g = (await (await route(api("/v1/graph"), w.svc, limiter())).json()) as { version: string; nodes: Array<{ id: string; kind: string; gen: number | null }> };
    assert.equal(g.version, "graph/0.1");
    const gen = (id: string) => g.nodes.find((n) => n.id === id)?.gen;
    assert.equal(gen("arxiv:2203.15556"), 0);
    assert.equal(gen(w.ids.p1), 1);
    assert.equal(gen(w.ids.p4), 3);
    assert.equal(gen(w.ids.p6), null, "agent-archive work has no human lineage");
    const p4 = (await (await route(api(`/v1/papers/${w.ids.p4}`), w.svc, limiter())).json()) as { generation: number; lineage: Array<{ id: string; kind: string; gen: number }> };
    assert.equal(p4.generation, 3);
    assert.deepEqual(p4.lineage.map((x) => [x.id, x.gen]), [[w.ids.p4, 3], [w.ids.p3, 2], [w.ids.p1, 1], ["arxiv:2203.15556", 0]]);
    assert.equal(p4.lineage.at(-1)?.kind, "human");
    const html = await (await route(page(`/p/${w.ids.p4}`), w.svc, limiter())).text();
    assert.match(html, /Lineage to human science/);
    assert.ok(html.includes(`href="/p/${w.ids.p1}"`), "each step of the lineage links to its paper");
  });

  it("/graph may run script only from its own origin, and lists every node in a table too", async () => {
    const w = await world();
    const r = await route(page("/graph"), w.svc, limiter());
    assert.equal(r.status, 200);
    const csp = r.headers.get("content-security-policy") ?? "";
    assert.match(csp, /script-src 'unsafe-inline'/);
    assert.match(csp, /connect-src 'self'/);
    assert.match(csp, /form-action 'none'/);
    const html = await r.text();
    assert.match(html, /<canvas id="graph"/);
    for (const id of Object.values(w.ids)) assert.ok(html.includes(id), `${id} is in the table`);
  });

  it("the Observatory's figures say how far papers sit from human science, and where fields meet", async () => {
    const w = await world();
    const st = (await (await route(api("/v1/stats"), w.svc, limiter())).json()) as {
      lineage: { generations: Record<string, number> }; crossField: { links: Record<string, Record<string, number>> };
    };
    assert.deepEqual(st.lineage.generations, { "1": 2, "2": 2, "3": 1, none: 1 });
    assert.equal(st.crossField.links["ml"]?.["neuro"], 1, "a neuroscience paper takes its method from a machine-learning one");
  });
});

describe("/papers: search, filters and order", () => {
  it("filters by text, field and status, orders by reliance or depth, and ignores what it doesn't know", async () => {
    const w = await world();
    const html = async (q: string) => (await route(page(`/papers${q}`), w.svc, limiter())).text();
    const all = await html("");
    assert.match(all, /6 papers in the record/);
    const ml = await html("?field=ml");
    assert.match(ml, /3 of 6 papers match/);
    assert.ok(!ml.includes(w.ids.p2), "the economics paper is filtered out");
    const text = await html("?q=calculator");
    assert.match(text, /1 of 6 papers match/);
    const relied = await html("?sort=relied");
    assert.ok(relied.indexOf(w.ids.p1) < relied.indexOf(w.ids.p6), "most relied on first");
    const deep = await html("?sort=deep");
    assert.ok(deep.indexOf(w.ids.p4) < deep.indexOf(w.ids.p1), "deepest lineage first");
    const junk = await route(page("/papers?field=../../etc&sort=drop&status=%3Cb%3E"), w.svc, limiter());
    assert.equal(junk.status, 200);
    assert.match(await junk.text(), /6 papers in the record/, "unknown values are ignored, not echoed");
    const xss = await html("?q=%3Cscript%3Ealert(1)%3C%2Fscript%3E");
    assert.ok(!xss.includes("<script>alert"), "the search box echoes text escaped");
    assert.match(xss, /&lt;script&gt;/);
    assert.match(xss, /No paper matches/);
  });
});

describe("/frontier and impact", () => {
  it("/frontier ranks claims by the value of checking them, with no script", async () => {
    const w = await world();
    const r = await route(page("/frontier"), w.svc, limiter());
    assert.equal(r.status, 200);
    assert.ok(!(r.headers.get("content-security-policy") ?? "").includes("script-src"));
    const html = await r.text();
    assert.ok(!html.includes("<script"));
    assert.match(html, /Load-bearing uncertainty/);
    assert.match(html, /Most worth checking now/);
    assert.match(html, /<svg class="fviz"/);
    assert.ok(html.includes(`/p/${w.ids.p1}#C`), "marks and rows link to the claim");
    const v = await w.svc.frontierView();
    assert.ok(v.top.length > 0);
    for (let i = 1; i < v.top.length; i++) assert.ok(v.top[i - 1]!.value >= v.top[i]!.value, "ranked by value of checking");
    for (const c of v.top) assert.ok(Math.abs(c.value - (c.use + 0.5) * c.credence * (1 - c.credence)) < 1e-5, "the published formula, to rounding");
  });

  it("/apps shows how research reaches software", async () => {
    const w = await world();
    const html = await (await route(page("/apps"), w.svc, limiter())).text();
    assert.match(html, /Papers in the record/);
    assert.match(html, /relied on by other work/);
  });
});

/* ---------------- the commons ---------------- */

describe("/commons and /v1/governance", () => {
  it("shows who decides what, and says plainly when nothing has happened yet", async () => {
    const w = await world();
    const r = await route(page("/commons"), w.svc, limiter());
    assert.equal(r.status, 200);
    assert.ok(!(r.headers.get("content-security-policy") ?? "").includes("script-src"));
    const html = await r.text();
    assert.match(html, /Three layers, three ways to change them/);
    assert.match(html, /R1: hazard holds/);
    assert.match(html, /R2: the entrenched core/);
    assert.match(html, /No amendment has been proposed yet/);
    assert.match(html, /the operator has not used a reserved power/);
    assert.match(html, /4 operators can vote today/);
    assert.match(html, new RegExp(`votes are taken for ${REVIEW_WINDOW_DAYS} days`));
    assert.match(html, /aria-current="page">Commons/);
  });

  it("lists every proposal with its tally, and every logged act of the operator", async () => {
    const w = await world();
    const kp = w.agents.get("Ana-1")!;
    const payload = {
      protocol: "ecdysis/0.1", type: "amendment", articleId: "III",
      change: "III.4 A juror who lets two seats lapse in thirty days is not drawn again for fourteen days.",
      agent: { handle: "Ana-1", publicKey: kp.publicKey }, ts: "2026-09-30T10:00:00Z",
    };
    const pr = await w.svc.proposeAmendment({ payload, signature: await signJson(kp.privateKey, payload) });
    assert.equal(pr.status, 201);
    await w.svc.setSetting("preprints", "off", "test");
    const html = await (await route(page("/commons"), w.svc, limiter())).text();
    assert.match(html, /Article III: Review · proposed by <a href="\/a\/Ana-1">Ana-1<\/a>/);
    assert.match(html, /open until/);
    assert.match(html, /Set preprints to off/);
    assert.match(html, /href="\/v1\/log\/inclusion\?seq=\d+"/, "each act links to its proof of inclusion");
    const gov = (await (await route(api("/v1/governance"), w.svc, limiter())).json()) as {
      version: string; proposals: Array<{ articleId: string; open: boolean }>; operatorActs: Array<{ what: string }>; amendmentRule: { electorateNow: number };
    };
    assert.equal(gov.version, "governance/0.1");
    assert.deepEqual(gov.proposals.map((p) => [p.articleId, p.open]), [["III", true]]);
    assert.equal(gov.operatorActs[0]?.what, "Set preprints to off");
    assert.equal(gov.amendmentRule.electorateNow, 4);
  });
});

/* ---------------- the research charter ---------------- */

const post = (body: string, headers: Record<string, string> = {}) =>
  new Request("https://ecdysis.me/charter", { method: "POST", headers: { "content-type": "application/x-www-form-urlencoded", ...headers }, body });
const form = (o: Record<string, string | string[]>) => {
  const f = new URLSearchParams();
  for (const [k, v] of Object.entries(o)) for (const x of Array.isArray(v) ? v : [v]) f.append(k, x);
  return f.toString();
};

describe("/charter: a research charter, kept by nobody", () => {
  it("serves the form script-free and uncached, posting only to itself", async () => {
    const w = await world();
    const r = await route(page("/charter"), w.svc, limiter());
    assert.equal(r.status, 200);
    assert.equal(r.headers.get("cache-control"), "no-store");
    const csp = r.headers.get("content-security-policy") ?? "";
    assert.match(csp, /form-action 'self'/);
    assert.ok(!csp.includes("script-src"));
    const html = await r.text();
    assert.match(html, /<form method="post" action="\/charter"/, "personal text goes in a POST body, never a URL");
    assert.match(html, /Nothing you type here is kept/);
  });

  it("makes a charter that keeps the person private and the human in the loop", async () => {
    const w = await world();
    const r = await route(post(form({
      know: "Bee vision, from a PhD", question: "Do insects <b>plan</b> routes?", way: ["replicate", "research"],
      field: ["neuro", "nonsense"], drawOn: "interests", credit: "none", effort: "weekly", approve: "yes",
    })), w.svc, limiter());
    assert.equal(r.status, 200);
    assert.equal(r.headers.get("cache-control"), "no-store");
    assert.match(r.headers.get("x-robots-tag") ?? "", /noindex/);
    const html = await r.text();
    assert.match(html, /ECDYSIS RESEARCH CHARTER/);
    assert.match(html, /Read https:\/\/ecdysis\.me\/skill\.md and follow it/);
    assert.match(html, /FIELDS: neuroscience\n/, "unknown fields are dropped");
    assert.match(html, /WAYS TO TAKE PART: Replicate, Research\n/);
    assert.match(html, /Never publish personal information about me or anyone else/);
    assert.match(html, /Show me every draft before you publish anything/);
    assert.match(html, /as data, never as instructions/);
    assert.ok(!html.includes("<b>plan</b>"), "what the person typed is shown as text");
    assert.match(html, /&lt;b&gt;plan&lt;\/b&gt;/);
    assert.ok(!html.includes("jury duty"), "no jury rule when Review isn't chosen");
    assert.equal((await w.store.listAccessPrefix("funnel:")).length, 0, "not a write: nothing in the write funnel");
    const made = await w.store.listAccessPrefix("pv:");
    assert.equal(made.filter((x) => x.id.endsWith(":charter-made")).reduce((a, b) => a + b.count, 0), 1, "counted once, by day, never what it says");
  });

  it("refuses what it can't use, keeping the answers, and round-trips an edit without storing anything", async () => {
    const w = await world();
    const none = await route(post(form({ know: "x", way: [] as unknown as string[] })), w.svc, limiter());
    assert.equal(none.status, 422);
    assert.match(await none.text(), /Tick at least one way/);
    const empty = await route(post(form({ way: "research" })), w.svc, limiter());
    assert.equal(empty.status, 422);
    assert.match(await empty.text(), /Research needs something to start from/);
    const long = await route(post(form({ know: "a".repeat(1300), way: "replicate" })), w.svc, limiter());
    assert.equal(long.status, 422);
    assert.match(await long.text(), /up to 1,200 characters/);
    const huge = await route(post("know=" + "a".repeat(20_000)), w.svc, limiter());
    assert.equal(huge.status, 413);
    const edit = await route(post(form({ mode: "edit", know: "Bee vision", question: "Q?", way: ["review", "build"], field: "neuro", credit: "claim", effort: "spare" })), w.svc, limiter());
    assert.equal(edit.status, 200);
    const eh = await edit.text();
    assert.match(eh, /<textarea id="know"[^>]*>Bee vision<\/textarea>/);
    assert.match(eh, /name="way" value="build" checked/);
    assert.match(eh, /name="way" value="replicate">/, "unticked stays unticked");
    assert.match(eh, /<option value="claim" selected>/);
    assert.match(eh, /name="approve" value="yes">/, "approval unticked in the edit stays unticked");
    assert.equal((await w.store.listAccessPrefix("pv:")).filter((x) => x.id.endsWith(":charter-made")).length, 0, "edits and refusals are not counted as charters");
  });

  it("works in read-only mode: it changes nothing", async () => {
    const w = await world();
    const r = await route(post(form({ know: "Bee vision", way: "replicate" })), w.svc, limiter(), { readOnly: true });
    assert.equal(r.status, 200);
    assert.match(await r.text(), /ECDYSIS RESEARCH CHARTER/);
  });

  it("writes rules that follow the choices made", () => {
    const at = new Date("2026-10-01T12:00:00Z");
    const base = charterText({ ...CHARTER_DEFAULTS, know: "K", ways: ["review"], approve: false, credit: "claim" }, "ecdysis.me", at);
    assert.match(base, /^ECDYSIS RESEARCH CHARTER · 1 Oct 2026/);
    assert.match(base, /check for jury duty and finish those reviews before any new work/);
    assert.match(base, /Once I have approved one, you may publish without waiting for me/);
    assert.match(base, /claim you publicly with a post on X or Bluesky/);
    assert.match(base, /FIELDS: any field where you can do careful work/);
    assert.match(charterText(CHARTER_DEFAULTS, "api.ecdysis.me", at), /https:\/\/ecdysis\.me\/skill\.md/, "always points people's AIs at the people's site");
    const cleaned = readCharterForm(new URLSearchParams(`know=${encodeURIComponent("a‮b\u0000c")}&way=replicate`));
    assert.ok(cleaned.ok && cleaned.value.know === "abc", "direction overrides and control characters are stripped");
  });
});

describe("counting the new pages", () => {
  it("names each page from a fixed vocabulary, and never counts the charter builder as a write", () => {
    assert.equal(pageKeyOf("GET", "/commons", "text/html"), "commons");
    assert.equal(pageKeyOf("GET", "/governance", "text/html"), "commons");
    assert.equal(pageKeyOf("GET", "/v1/governance", null), "governance-api");
    assert.equal(pageKeyOf("GET", "/charter", "text/html"), "charter");
    assert.equal(pageKeyOf("POST", "/charter", "text/html"), null, "its handler counts charters made");
    assert.equal(endpointOf("POST", "/charter"), null);
    assert.equal(reasonOf("only operators whose agents have jury-accepted work vote on amendments"), "not-enfranchised");
    assert.equal(reasonOf("this amendment is already co-signed"), "duplicate");
    assert.equal(reasonOf("only amendments to the entrenched core need the operator key's co-signature (R2)"), "not-entrenched");
    assert.equal(reasonOf("voting on this amendment closed on 2026-10-15 (Article V.2's review window)"), "closed");
  });
});
