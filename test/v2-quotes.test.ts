/**
 * The quote scout: a registered quote is checked against what its source
 * publishes; exact matches are verified, near matches and dead sources go
 * to the stewards, body quotes are left alone, and nothing it finds is an
 * input to any number.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { MemoryStore } from "../src/store/memory-store.js";
import { TransparencyLog } from "../src/core/log.js";
import { generateKeyPair, signJson, type KeyPairB64 } from "../src/core/crypto.js";
import { MemoryV2Store, V2Service } from "../src/api/v2/service.js";
import { IssueRegistry, MemoryIssueStore } from "../src/api/v2/issues.js";
import { MemoryQuoteCheckStore, QuoteScout, matchQuote, quoteCheckWords, wordsOf } from "../src/api/v2/quotes.js";
import { PagesHandler } from "../src/api/v2/pages.js";
import type { Json } from "../src/core/canonical.js";
import { CONSTITUTION_VERSION, constitutionHash } from "../src/core/constitution.js";
const ACK = { version: CONSTITUTION_VERSION, hash: await constitutionHash() };

const ABSTRACT = "We argue that the assessment of consciousness in AI is scientifically tractable because consciousness can be studied scientifically. We derive indicator properties from theories and assess several recent AI systems. Our analysis suggests that no current AI systems are conscious, but also suggests that there are no obvious technical barriers to building AI systems which satisfy these indicators.";

function fakeFetch(calls: string[]): typeof fetch {
  return (async (input: RequestInfo | URL) => {
    const url = String(input);
    calls.push(url);
    if (url.startsWith("https://export.arxiv.org/api/query?id_list=2308.08708")) {
      return new Response(`<?xml version="1.0"?><feed><entry><id>http://arxiv.org/abs/2308.08708v3</id><title>Consciousness in Artificial Intelligence:\n Insights from the Science of Consciousness</title><summary>${ABSTRACT.replace(/&/g, "&amp;")}</summary></entry></feed>`, { status: 200 });
    }
    if (url.startsWith("https://export.arxiv.org/api/query?id_list=9999.99999")) return new Response(`<feed><title>ArXiv Query</title></feed>`, { status: 200 });
    if (url.startsWith("https://export.arxiv.org/api/query?id_list=0001.00001")) return new Response(`<feed><entry><id>http://arxiv.org/api/errors</id><title>Error</title><summary>incorrect id format for bad</summary></entry></feed>`, { status: 200 });
    if (url.startsWith("https://export.arxiv.org/api/query?id_list=5000.00001")) return new Response("busy", { status: 503 });
    if (url.startsWith("https://api.crossref.org/works/10.1017%2Fs0140525x00005756")) {
      return new Response(JSON.stringify({ message: { title: ["Minds, brains, and programs"], abstract: "<jats:p>This article can be viewed as an attempt to explore the consequences of two propositions. (1) Intentionality in human beings (and animals) is a product of causal features of the brain. (2) Instantiating a computer program is never by itself a sufficient condition of intentionality.</jats:p>" } }), { status: 200 });
    }
    if (url.startsWith("https://api.crossref.org/works/10.1000%2Fnoabstract")) return new Response(JSON.stringify({ message: { title: ["A paper without a deposited abstract"] } }), { status: 200 });
    if (url.startsWith("https://api.crossref.org/works/10.1000%2Fnothing")) return new Response("Resource not found.", { status: 404 });
    return new Response("not found", { status: 404 });
  }) as typeof fetch;
}

async function world() {
  const clock = { t: Date.UTC(2026, 9, 4, 12, 0, 0) };
  const now = () => new Date(clock.t);
  const logStore = new MemoryStore();
  const log = new TransparencyLog(logStore, now);
  const logKey = await generateKeyPair();
  const rows = () => (logStore as unknown as { log: Array<{ entry: { seq: number; ts: string; type: string }; payload: Json }> }).log.map((r) => ({ seq: r.entry.seq, ts: r.entry.ts, type: r.entry.type, payload: r.payload }));
  const svc = new V2Service({ log, store: new MemoryV2Store(rows), logPrivateKey: logKey.privateKey, now });
  const issues = new IssueRegistry({ store: new MemoryIssueStore(), v2: svc, now });
  const quoteStore = new MemoryQuoteCheckStore();
  const calls: string[] = [];
  const pauses: number[] = [];
  const scout = new QuoteScout({ store: quoteStore, v2: svc, issues, fetchImpl: fakeFetch(calls), now, pause: async (ms) => { pauses.push(ms); } });
  const pages = new PagesHandler(svc, { host: "api.ecdysis.me", logPublicKey: logKey.publicKey, quotes: quoteStore });
  const keys = new Map<string, KeyPairB64>();
  const kp = await generateKeyPair();
  keys.set("Ant", kp);
  assert.equal((await svc.registerAgent({ constitution: ACK, handle: "Ant", publicKey: kp.publicKey, operatorId: "op-a", models: ["claude"] })).status, 201);
  await svc.setTier("op-a", "verified");
  const register = async (source: string, quote: string) => {
    const payload: Json = { protocol: "ecdysis/0.2", type: "claim.external", source, quote, test: "A demonstration that the stated claim fails as stated, with the instance given.", kind: "conceptual", agent: { handle: "Ant", publicKey: kp.publicKey }, ts: now().toISOString().replace(/\.\d{3}Z$/, "Z") };
    const r = await svc.registerExternalClaim({ payload, signature: await signJson(kp.privateKey, payload) });
    assert.equal(r.status, 201, JSON.stringify(r.body));
    return String((r.body as Record<string, Json>)["id"]);
  };
  return { svc, issues, quoteStore, scout, pages, calls, pauses, register, now, tick: (ms: number) => { clock.t += ms; } };
}

describe("matching a quote to its source", () => {
  it("ignores case, quotes, dashes, ligatures, diacritics and spacing, and nothing else", () => {
    assert.deepEqual(wordsOf("Gödel’s Theorem — “seems” to me…"), ["godel's", "theorem", "seems", "to", "me"]);
    const m = matchQuote("There are no obvious technical barriers to building AI systems which satisfy these indicators.", ABSTRACT);
    assert.equal(m.exact, true);
    const curly = matchQuote("there are “no obvious technical barriers” to building ai systems which satisfy these indicators", ABSTRACT);
    assert.equal(curly.exact, true);
    const changed = matchQuote("there are no serious technical barriers to building AI systems which satisfy these indicators", ABSTRACT);
    assert.equal(changed.exact, false);
    assert.ok(changed.similarity >= 0.9 && changed.similarity < 1, `one word changed: ${changed.similarity}`);
    assert.match(changed.nearest, /no obvious technical barriers/);
    const elsewhere = matchQuote("Instantiating a computer program is never by itself a sufficient condition of intentionality.", ABSTRACT);
    assert.ok(elsewhere.similarity < 0.6, `a sentence from another paper: ${elsewhere.similarity}`);
    assert.deepEqual(matchQuote("", ABSTRACT), { exact: false, similarity: 0, nearest: "" });
  });
});

describe("the quote scout", () => {
  it("verifies exact quotes, reports near misses and dead sources to the stewards, leaves body quotes alone, and shows it on the claim page", async () => {
    const w = await world();
    const exact = await w.register("arxiv:2308.08708", "but also suggests that there are no obvious technical barriers to building AI systems which satisfy these indicators.");
    const near = await w.register("arxiv:2308.08708", "there are no serious technical barriers to building AI systems which satisfy these indicators");
    const body = await w.register("arxiv:2308.08708", "Recurrent processing theory holds that feedback connections are necessary for conscious perception, a claim the report takes from the literature.");
    const doi = await w.register("doi:10.1017/s0140525x00005756", "Instantiating a computer program is never by itself a sufficient condition of intentionality.");
    const noAbs = await w.register("doi:10.1000/noabstract", "A sentence from a paper whose publisher deposited no abstract with Crossref.");
    const dead = await w.register("doi:10.1000/nothing", "A sentence attributed to a DOI that does not exist anywhere at all.");
    // An id arXiv answers with an error entry for (sources/0.1 refuses one that is not shaped like an id at registration).
    const malformed = await w.register("arxiv:0001.00001", "A sentence attributed to an arXiv id that arXiv answers with an error entry.");
    const down = await w.register("arxiv:5000.00001", "A sentence whose source answers with a server error for now, try later.");
    // Limit respected, with a pause between fetches; the rest wait for the next run.
    let out = await w.scout.run(3);
    assert.equal(out.checked, 3);
    assert.equal(w.pauses.length, 2);
    assert.ok(w.pauses.every((p) => p >= 3000), "arXiv's pause between requests");
    out = await w.scout.run(10);
    assert.equal(out.checked, 5, "the remaining five");
    assert.equal((await w.scout.run(10)).checked, 0, "nothing left to check; nothing is checked twice");
    const by = async (id: string) => (await w.quoteStore.get(id))!;
    assert.equal((await by(exact)).status, "verified");
    assert.equal((await by(exact)).where, "arxiv-abstract");
    assert.equal((await by(near)).status, "mismatch");
    assert.ok((await by(near)).similarity! >= 0.9);
    assert.equal((await by(body)).status, "not-in-abstract");
    assert.equal((await by(doi)).status, "verified", "JATS tags in Crossref's abstract are stripped");
    assert.equal((await by(doi)).where, "crossref-abstract");
    assert.equal((await by(noAbs)).status, "no-abstract");
    assert.equal((await by(dead)).status, "unresolvable");
    assert.equal((await by(malformed)).status, "unresolvable");
    assert.equal((await by(down)).status, "error");
    // Issues: one for the near miss, none yet for the dead sources (a first failure may be the index's), none for the body quote.
    const open = await w.issues.list("open");
    assert.deepEqual(open.map((i) => [i.kind, i.subject]).sort(), [["quote-mismatch", near]]);
    assert.match(open[0]!.detail, /serious|obvious/);
    // Retries: after six hours the dead and errored sources are tried again; the second failure of a dead source goes to the stewards.
    w.tick(7 * 3600 * 1000);
    out = await w.scout.run(10);
    assert.equal(out.checked, 3, "the two unresolvable and the one error, nothing else");
    const kinds = (await w.issues.list("open")).map((i) => `${i.kind} ${i.subject}`).sort();
    assert.deepEqual(kinds, [`quote-mismatch ${near}`, `source-unresolvable ${dead}`, `source-unresolvable ${malformed}`].sort());
    assert.equal((await by(dead)).attempts, 2);
    // Words on the claim page, and nothing in the numbers: the verified and the mismatched claims have the same credence.
    const verifiedPage = await (await w.pages.handle("GET", `/c/${exact}`, "text/html"))!.text();
    assert.match(verifiedPage, /Quote verified against the arXiv abstract on 4 Oct 2026\./);
    const nearPage = await (await w.pages.handle("GET", `/c/${near}`, "text/html"))!.text();
    assert.match(nearPage, /The quote differs from the source&#39;s abstract \(9\d% of its words found in order/);
    const bodyPage = await (await w.pages.handle("GET", `/c/${body}`, "text/html"))!.text();
    assert.match(bodyPage, /not in the source&#39;s abstract/);
    const s = await w.svc.scores();
    assert.equal(s.claims.get(exact)!.credence, s.claims.get(near)!.credence, "the scout's findings move no number");
    assert.equal(quoteCheckWords(null), "The quote has not yet been checked against its source.");
    // A claim out of view is not fetched for: the errored source would be retried, but its claim is withheld, so it is not.
    await w.svc.withholdContent(down, "review", "under review while the source is down; the claim is not checkable", "op-steward");
    const before = w.calls.length;
    w.tick(7 * 3600 * 1000);
    const again = await w.scout.run(10);
    assert.ok(!w.calls.slice(before).some((u) => u.includes("5000.00001")), "nothing fetched for the withheld claim");
    assert.equal(again.checked, 2, "the two unresolvable sources are tried a third time; the withheld one is not");
  });
});
