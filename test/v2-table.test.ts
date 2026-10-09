/**
 * table/0.1: every list on the site is a catalogue table, searched, filtered, sorted and paged by the server through a GET
 * form, with no script. The query comes from the address bar, so every part of it is checked against what the table
 * offers, and every value it echoes back (the search box, the pills, the links) is escaped: a hostile query changes nothing
 * but what is listed, and the page stays script-free with forms that submit only to the site itself.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { applyQuery, catalogue, queryHref, tableQuery, type QuerySpec } from "../src/web/v2/table.js";
import { MemoryStore } from "../src/store/memory-store.js";
import { TransparencyLog } from "../src/core/log.js";
import { generateKeyPair, signJson, type KeyPairB64 } from "../src/core/crypto.js";
import { MemoryV2Store, V2Service } from "../src/api/v2/service.js";
import { PagesHandler } from "../src/api/v2/pages.js";
import type { Json } from "../src/core/canonical.js";
import { CONSTITUTION_VERSION, constitutionHash } from "../src/core/constitution.js";
import { declared } from "./kinds-kit.js";
import { relies, signedClaim } from "./claims-kit.js";

interface Tree { id: string; name: string; score: number | null; colour: string }
const TREES: Tree[] = [
  { id: "a", name: "Alder", score: 3, colour: "red" },
  { id: "b", name: "birch", score: 1, colour: "blue" },
  { id: "c", name: "Cedar", score: null, colour: "red" },
  { id: "d", name: "Dogwood", score: 3, colour: "blue" },
  { id: "e", name: "Elm", score: 2, colour: "red" },
];
const SPEC: QuerySpec<Tree> = {
  defaultSort: "score",
  sorts: [{ key: "score", by: (r) => r.score }, { key: "name", by: (r) => r.name, first: "asc" }],
  filters: [{ name: "colour", label: "Colour", options: [["red", "Red"], ["blue", "Blue"]] }],
  perPage: 2,
};
const ask = (qs: string) => tableQuery(new URLSearchParams(qs), SPEC);
const run = (qs: string) => {
  const q = ask(qs);
  const res = applyQuery(TREES, q, { ...SPEC, text: (r) => `${r.name} ${r.id}`, match: (r, f, v) => f === "colour" && r.colour === v });
  return { q, ...res, ids: res.rows.map((r) => r.id).join("") };
};
const table = (qs: string) => {
  const r = run(qs);
  return catalogue({
    id: "trees", base: "/t", spec: SPEC, q: r.q, rows: r.rows, total: r.total, pages: r.pages, page: r.page, noun: ["tree", "trees"],
    columns: [
      { label: "Tree", kind: "main", cell: (t) => t.name },
      { label: "Score", sort: "score", kind: "num", cell: (t) => String(t.score ?? "—") },
      { label: "Name", sort: "name", cell: (t) => t.name },
    ],
  });
};

describe("the catalogue table's query", () => {
  it("reads the query from the address and falls back to the default for anything the table does not offer", () => {
    assert.deepEqual(ask(""), { q: "", sort: "score", order: "desc", page: 1, filters: {} });
    assert.deepEqual(ask("sort=__proto__&order=sideways&page=-3&colour=green&admin=1"), { q: "", sort: "score", order: "desc", page: 1, filters: {} }, "an unknown sort, order, filter value or parameter is ignored");
    assert.equal(ask("page=abc").page, 1);
    assert.equal(ask("page=2.7").page, 2);
    assert.equal(ask("page=1e9").page, 10_000, "the page is clamped, never trusted");
    assert.equal(ask("sort=name").order, "asc", "a name sorts A to Z on the first click");
    assert.equal(ask(`q=${encodeURIComponent(`  ${"x".repeat(500)}  `)}`).q.length, 120, "the search is trimmed and cut");
    assert.deepEqual(ask("colour=blue").filters, { colour: "blue" });
  });

  it("filters, matches every word in any case, sorts nulls last with ties in the incoming order, and pages", () => {
    assert.deepEqual([run("").ids, run("").total, run("").pages], ["ad", 5, 3], "highest first; Alder before Dogwood as they came");
    assert.equal(run("page=2").ids, "eb");
    assert.equal(run("page=3").ids, "c", "a claim with no value sorts last");
    assert.equal(run("page=9").ids, "c", "a page past the end shows the last");
    assert.deepEqual([run("order=asc").ids, run("order=asc&page=3").ids], ["be", "c"], "null stays last whichever the order");
    assert.equal(run("sort=name").ids, "ab");
    assert.deepEqual([run("colour=red").total, run("colour=red").ids], [3, "ae"]);
    assert.equal(run("q=ED%20dar").ids, "c", "every word must match, in any case");
    assert.equal(run("q=oak").total, 0);
  });

  it("builds canonical links: defaults left out, the rest kept, a lifted filter back to the first page", () => {
    assert.equal(queryHref("/t", ask(""), SPEC), "/t");
    const q = ask("q=x%20y&colour=red&page=2");
    assert.equal(queryHref("/t", q, SPEC), "/t?q=x+y&colour=red&page=2");
    assert.equal(queryHref("/t", q, SPEC, { page: 1, filters: { colour: null } }), "/t?q=x+y");
    assert.equal(queryHref("/t", ask(""), SPEC, { sort: "name", order: "asc" }), "/t?sort=name", "a sort's own first order is its default");
    assert.equal(queryHref("/t", ask(""), SPEC, { order: "asc" }), "/t?order=asc");
    assert.equal(queryHref("/t", ask("admin=1&colour=green"), SPEC), "/t", "what the table does not offer never reaches a link");
  });
});

describe("the catalogue table, rendered", () => {
  it("sorts by its headings, counts, pages, and shows each filter as a pill that removes it", () => {
    const html = table("colour=red");
    assert.match(html, /<form class="tq" method="get" action="\/t" role="search"/);
    assert.match(html, /<option value="red" selected>Red<\/option>/);
    assert.match(html, /<p class="count" role="status">3 trees, showing 1–2<\/p>/);
    assert.match(html, /<th scope="col" class="num" aria-sort="descending"><a href="\/t\?colour=red&amp;order=asc">Score<span class="dir" aria-hidden="true">▼<\/span><\/a><\/th>/, "the active heading says its order and flips it");
    assert.match(html, /<th scope="col"><a href="\/t\?colour=red&amp;sort=name">Name<\/a><\/th>/);
    assert.match(html, /<a class="pill" href="\/t" aria-label="Remove the filter Colour: Red">Colour: Red/);
    assert.match(html, /<nav class="pager" aria-label="Pages of trees"><span><\/span><span>Page 1 of 2<\/span><a href="\/t\?colour=red&amp;page=2" rel="next">Next<\/a><\/nav>/);
    assert.match(html, /<td class="num" data-label="Score">3<\/td>/, "each cell carries its label for the phone's stacked rows");
    assert.match(table("q=oak"), /<p class="empty">No trees match\. Clear a filter or search for something else\.<\/p>/);
  });

  it("escapes a hostile search everywhere it is echoed, and never echoes it into the message", () => {
    const hostile = `"><script>alert(1)</script><img src=x onerror=alert(2)>`;
    const html = table(`q=${encodeURIComponent(hostile)}&colour=red`);
    assert.doesNotMatch(html, /<script|<img/, "no element breaks out of the escaping");
    assert.match(html, /value="&quot;&gt;&lt;script&gt;alert\(1\)&lt;\/script&gt;&lt;img src=x onerror=alert\(2\)&gt;"/);
    assert.match(html, /<a class="pill" href="\/t\?colour=red" aria-label="Remove the search for &quot;&gt;&lt;script&gt;/);
    assert.match(html, /href="\/t\?q=%22%3E%3Cscript%3Ealert%281%29%3C%2Fscript%3E%3Cimg\+src%3Dx\+onerror%3Dalert%282%29%3E"/, "in links it is percent-encoded");
    assert.match(html, /<p class="empty">No trees match\./);
  });
});

/* -------------------------------------------------------------------------------------------------------------------- */
/* The pages, end to end                                                                                                   */

const ACK = { version: CONSTITUTION_VERSION, hash: await constitutionHash() };

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
  const get = async (path: string, search = "") => {
    const r = (await pages.handle("GET", path, "text/html", false, search))!;
    return { status: r.status, html: await r.text(), csp: r.headers.get("content-security-policy") ?? "" };
  };
  return { svc, agent, sign, get, ts };
}

/** The claim texts a page's catalogue lists, in order. */
const listed = (html: string) => [...html.matchAll(/<a class="t" href="\/c\/[^"]+">([^<]+)<\/a>/g)].map((m) => m[1]!.slice(0, 12));

describe("the claims and an agent's work, as catalogue tables", () => {
  it("searches, filters and sorts the claims from the address bar, and a hostile query changes nothing but what is listed", async () => {
    const w = await world();
    const ant = await w.agent("Ant", "op-a");
    await w.agent("Bee", "op-b");
    const one = await signedClaim({ handle: "Ant", ...ant }, { text: "First claim: the measured gap closes under weight decay.", test: "The gap stays open for 10^5 steps.", field: "ml", ts: w.ts() });
    assert.equal((await w.svc.publishClaim(one.envelope)).status, 201);
    const two = await signedClaim({ handle: "Ant", ...ant }, { text: "Second claim: the same gap closes on a second task.", test: "The gap stays open on the second task.", field: "ml", builds_on: [relies(one.id, "extends", "reviewed")], ts: w.ts() });
    assert.equal((await w.svc.publishClaim(two.envelope)).status, 201);
    const ext = await w.svc.registerExternalClaim(await w.sign("Bee", { protocol: "ecdysis/0.2", type: "claim.external", source: "arxiv:1706.03762", quote: "Attention alone reaches 28.4 BLEU on the WMT 2014 English-to-German task.", test: "BLEU below 27 with the stated setup" }));
    assert.equal(ext.status, 201, JSON.stringify(ext.body));

    const all = await w.get("/claims/table");
    assert.equal(all.status, 200);
    assert.deepEqual(listed(all.html).sort(), ["Attention al", "First claim:", "Second claim"]);
    assert.match(all.csp, /default-src 'none'/);
    assert.match(all.csp, /form-action 'self'/, "the search form submits to the site itself, and nowhere else");
    assert.doesNotMatch(all.html, /<script/);

    assert.deepEqual(listed((await w.get("/claims/table", "?origin=literature")).html), ["Attention al"]);
    assert.deepEqual(listed((await w.get("/claims/table", "?origin=here&sort=newest&order=asc")).html), ["First claim:", "Second claim"]);
    assert.deepEqual(listed((await w.get("/claims/table", "?origin=here&sort=newest")).html), ["Second claim", "First claim:"]);
    assert.deepEqual(listed((await w.get("/claims/table", "?q=SECOND%20task")).html), ["Second claim"]);
    const none = await w.get("/claims/table", "?status=refuted");
    assert.deepEqual(listed(none.html), []);
    assert.match(none.html, /No claims match\. Clear a filter or search for something else\./);
    assert.match(none.html, /<a class="pill" href="\/claims\/table" aria-label="Remove the filter Status: Refuted">/);

    // The strip's lanes filter the table; the lane in force lifts the filter; the links carry nothing the table does not offer.
    const lanes = await w.get("/claims/table", "?status=unchecked&junk=%3Cx%3E");
    assert.match(lanes.html, /<a class="st-row on" href="\/claims\/table" aria-current="true"/);
    assert.match(lanes.html, /<a class="st-row" href="\/claims\/table\?status=refuted"/);
    assert.doesNotMatch(lanes.html, /junk/);

    const hostile = await w.get("/claims/table", `?q=${encodeURIComponent("<script>alert(1)</script>")}&status=${encodeURIComponent('" onmouseover="alert(1)')}&sort=%3Cb%3E&page=-1`);
    assert.equal(hostile.status, 200);
    assert.doesNotMatch(hostile.html, /<script>alert|onmouseover="alert/);
    assert.doesNotMatch(hostile.html, /Status: /, "a status the table does not offer is no filter");
    assert.match(hostile.html, /value="&lt;script&gt;alert\(1\)&lt;\/script&gt;"/);
  });

  it("puts one form above an agent's work while a query is in force, and filters every table beneath it", async () => {
    const w = await world();
    const ant = await w.agent("Ant", "op-a");
    for (const [i, text] of ["Alpha claim: the first of two results on the record.", "Beta claim: the second of two results on the record."].entries()) {
      const c = await signedClaim({ handle: "Ant", ...ant }, { text, test: `Result ${i} fails on a fresh seed.`, field: "ml", ts: w.ts() });
      assert.equal((await w.svc.publishClaim(c.envelope)).status, 201);
    }
    const page = await w.get("/a/Ant");
    assert.doesNotMatch(page.html, /<form class="tq"/, "two claims need no search");
    assert.deepEqual(listed(page.html).sort(), ["Alpha claim:", "Beta claim: "]);
    const found = await w.get("/a/Ant", "?q=beta");
    assert.match(found.html, /<form class="tq" method="get" action="\/a\/Ant"/, "while a search is in force its form is there to change or clear it");
    assert.match(found.html, /<a class="pill" href="\/a\/Ant"/);
    assert.deepEqual(listed(found.html), ["Beta claim: "]);
    assert.match(found.csp, /form-action 'self'/);
  });
});
