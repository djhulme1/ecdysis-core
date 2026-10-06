/**
 * sources/0.1 (core/v2/sources.ts): how the record names a human work. Every
 * scheme's one spelling is taken and every other refused with the right one
 * in the refusal; a URL or a loose spelling is named, never guessed; a source
 * cannot carry a path, a query, markup, a homoglyph or an invisible character
 * into a URL or a page; a cite: key is derived from its citation and checked;
 * the quote scout reads each scheme's own index, and catches an identifier
 * that names another work; the stakes scout looks each work up where it can,
 * and nothing about a source moves a number. Every attack is shown failing.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { MemoryStore } from "../src/store/memory-store.js";
import { TransparencyLog } from "../src/core/log.js";
import { generateKeyPair, signJson } from "../src/core/crypto.js";
import { hashJson, type Json } from "../src/core/canonical.js";
import { MemoryV2Store, V2Service } from "../src/api/v2/service.js";
import { IssueRegistry, MemoryIssueStore } from "../src/api/v2/issues.js";
import { MemoryQuoteCheckStore, QuoteScout, invertedAbstract, metaContent } from "../src/api/v2/quotes.js";
import { PagesHandler } from "../src/api/v2/pages.js";
import { StakesScout } from "../src/api/v2/stakes-scout.js";
import { parseObservation } from "../src/core/v2/stakes.js";
import { validateClaim } from "../src/core/v2/claim.js";
import {
  citeKeyOf, foldFamily, foldTitle, isHumanWork, nameSource, parseSource, resolverOf, SCHEMES, SOURCE_MAX, SOURCE_SCHEMES, sourcesTable, titleAgreement,
} from "../src/core/v2/sources.js";
import { CONSTITUTION_VERSION, constitutionHash } from "../src/core/constitution.js";

const ACK = { version: CONSTITUTION_VERSION, hash: await constitutionHash() };
const body = (r: { body: Json }) => r.body as Record<string, Json>;

describe("sources/0.1: one spelling for every scheme", () => {
  it("takes each scheme's example as it stands, in precedence order, each with a resolver but cite:", () => {
    assert.deepEqual([...SOURCE_SCHEMES], ["arxiv", "doi", "pmid", "pmcid", "openreview", "acl", "pmlr", "jmlr", "neurips", "openalex", "isbn", "cite"]);
    for (const s of SOURCE_SCHEMES) {
      const r = parseSource(SCHEMES[s].example);
      assert.equal(r.ok, true, `${s}: ${JSON.stringify(r)}`);
      assert.equal((r as { scheme: string }).scheme, s);
      assert.equal(resolverOf(SCHEMES[s].example) === null, s === "cite", s);
    }
    const t = sourcesTable();
    assert.equal(t.length, 12);
    assert.equal(t[0]!.resolver, "https://arxiv.org/abs/2201.02177");
    assert.equal(t.find((x) => x.scheme === "isbn")!.text, null, "a book has no open text");
  });

  it("names a work from its address or any common spelling, and never guesses", () => {
    const cases: Array<[string, string]> = [
      ["arXiv:2201.02177v2", "arxiv:2201.02177"],
      ["https://arxiv.org/pdf/2201.02177v3.pdf", "arxiv:2201.02177"],
      ["https://arxiv.org/abs/cs/0305009v1", "arxiv:cs/0305009"],
      ["arxiv.org/abs/math.GT/0309136", "arxiv:math/0309136"],
      ["2201.02177", "arxiv:2201.02177"],
      ["doi:10.1038/S41586-021-03819-2", "doi:10.1038/s41586-021-03819-2"],
      ["https://doi.org/10.1038/s41586-021-03819-2.", "doi:10.1038/s41586-021-03819-2"],
      ["10.48550/arXiv.2201.02177", "arxiv:2201.02177"],
      ["PMID: 27357684", "pmid:27357684"],
      ["https://pubmed.ncbi.nlm.nih.gov/27357684/", "pmid:27357684"],
      ["https://www.ncbi.nlm.nih.gov/pmc/articles/4948312", "pmcid:PMC4948312"],
      ["pmc4948312", "pmcid:PMC4948312"],
      ["https://openreview.net/forum?id=rJl-b3RcF7", "openreview:rJl-b3RcF7"],
      ["https://aclanthology.org/2020.acl-main.463/", "acl:2020.acl-main.463"],
      ["acl:p19-1001", "acl:P19-1001"],
      ["https://proceedings.mlr.press/v119/frankle20a/frankle20a.pdf", "pmlr:v119/frankle20a"],
      ["https://www.jmlr.org/papers/volume15/srivastava14a/srivastava14a.pdf", "jmlr:v15/srivastava14a"],
      ["https://papers.nips.cc/paper/2019/file/1113D7A76FFCECA1BB350BFE145467C6-Paper.pdf", "neurips:2019/1113d7a76ffceca1bb350bfe145467c6"],
      ["https://openalex.org/W2741809807", "openalex:W2741809807"],
      ["w2741809807", "openalex:W2741809807"],
      ["ISBN 978-0-262-03561-3", "isbn:9780262035613"],
      ["0-262-03561-8", "isbn:9780262035613"],
    ];
    for (const [raw, want] of cases) {
      const r = nameSource(raw);
      assert.equal(r.ok && r.source, want, `${raw}: ${JSON.stringify(r)}`);
      assert.equal(parseSource(want).ok, true, `${want} is canonical`);
    }
    for (const raw of ["https://example.com/paper.pdf", "a paper I read", "Smith 2019", "isbn:9780262035614", "0-262-03561-9"]) {
      assert.equal(nameSource(raw).ok, false, raw);
    }
  });

  it("refuses every other spelling with the right one in the refusal", () => {
    const refused = (raw: string, want: RegExp) => {
      const r = parseSource(raw);
      assert.equal(r.ok, false, raw);
      assert.match((r as { error: string }).error, want, raw);
    };
    refused("arxiv:2201.02177v2", /write it as arxiv:2201\.02177/);
    refused("ArXiv:2201.02177", /write it as arxiv:2201\.02177/);
    refused("doi:10.1038/S41586-021-03819-2", /write it as doi:10\.1038\/s41586-021-03819-2/);
    refused("doi:10.1038/s41586-021-03819-2.", /write it as doi:10\.1038\/s41586-021-03819-2 /);
    refused("https://doi.org/10.1038/x", /write it as doi:10\.1038\/x/);
    refused("pmcid:4948312", /write it as pmcid:PMC4948312/);
    refused("openalex:w2741809807", /write it as openalex:W2741809807/);
    refused("isbn:978-0-262-03561-3", /write it as isbn:9780262035613/);
    refused("isbn:9780262035614", /not an isbn: identifier/);
    refused("arxiv:badid", /not an arxiv: identifier/);
    refused("ssrn:12345", /not a scheme sources\/0\.1 knows/);
    refused("", /names a human work/);
  });

  it("lets no homoglyph, invisible character, path, query or markup through", () => {
    for (const raw of ["аrxiv:2201.02177", "arxiv:2201.02177​", "arxiv:2201. 0217", "doi:10.1038/s41586 x", "doi:10.1038/café"]) {
      const r = parseSource(raw);
      assert.equal(r.ok, false, JSON.stringify(raw));
      assert.match((r as { error: string }).error, /ASCII/);
    }
    for (const raw of ["arxiv:2201.02177 ", "doi:10.1038/a b", "pmlr:v119/../../etc/passwd", "jmlr:v15/../x", "openreview:abc&id=evil", "openreview:abc?x", "acl:2020.acl-main.463/../x",
      "neurips:2019/../../x", "pmid:0123", "openalex:W0", "cite:Cheeseman-1991-0a1b2c3d4e5f", `doi:10.1000/${"x".repeat(SOURCE_MAX)}`, 'doi:10.1000/"onload="x', "doi:10.1000/a{b}"]) {
      assert.equal(parseSource(raw).ok, false, raw);
    }
    // What a DOI may hold (old SICI DOIs keep their angle brackets and hash) is escaped wherever it goes.
    const sici = "doi:10.1002/(sici)1097-4636(199601)30:1<1::aid-jbm1>3.0.co;2-#";
    assert.equal(parseSource(sici).ok, true);
    assert.equal(resolverOf(sici), "https://doi.org/10.1002/(sici)1097-4636(199601)30:1%3C1::aid-jbm1%3E3.0.co;2-%23");
    assert.equal(isHumanWork(sici), true);
    assert.equal(isHumanWork("doi:10.1000/x."), false);
  });
});

describe("sources/0.1: the work in words", () => {
  it("derives a cite: key from the citation, folding case, accents and punctuation, and nothing else", async () => {
    const w = { title: "Where the really hard problems are", authors: ["Cheeseman", "Kanefsky", "Taylor"], year: 1991 };
    const k = await citeKeyOf(w);
    assert.match(k, /^cite:cheeseman-1991-[0-9a-f]{12}$/);
    assert.equal(parseSource(k).ok, true);
    assert.equal(await citeKeyOf({ ...w, title: "WHERE THE REALLY HARD PROBLEMS ARE." }), k);
    assert.equal(await citeKeyOf({ ...w, authors: ["Chéeseman"] }), k);
    assert.notEqual(await citeKeyOf({ ...w, year: 1992 }), k);
    assert.notEqual(await citeKeyOf({ ...w, title: "Where the really easy problems are" }), k);
    assert.equal(foldTitle("Æsthetic “Phase” Transitions — in 3-SAT!"), "aesthetic phase transitions in 3 sat");
    assert.equal(foldFamily("van der Waals-Ćirić"), "vanderwaalsciric");
    assert.equal(foldFamily("李"), "anon");
    assert.equal(foldTitle("随机可满足性"), "随机可满足性", "a title in another script keeps its letters");
  });

  it("judges whether two titles name one work, a subtitle costing nothing", () => {
    assert.equal(titleAgreement("The lottery ticket hypothesis", "The Lottery Ticket Hypothesis: Finding Sparse, Trainable Neural Networks"), 1);
    assert.ok(titleAgreement("Deep residual learning for image recognition", "Attention is all you need")! < 0.6);
    assert.equal(titleAgreement("Attention", "Attention is all you need"), null, "too short to judge");
  });

  it("takes a human work as background only in its one spelling", () => {
    const claim = (id: string) => validateClaim({ protocol: "ecdysis/0.2", type: "claim", text: "A claim that names a human work as background only.", confidence: 0.5,
      test: "Refuted if the stated quantity falls outside the stated range.", field: "math", rationale: "x".repeat(60), scope: { general: "construction", basis: "the ensemble as defined in the text" },
      builds_on: [{ id, rel: "background" }], agent: { handle: "Ant", publicKey: "MCowBQYDK2VwAyEA" + "x".repeat(43) }, ts: "2026-10-06T00:00:00Z" } as unknown as Json);
    for (const id of ["arxiv:2201.02177", "pmlr:v119/frankle20a", "openalex:W2741809807", "isbn:9780262035613"]) assert.equal(claim(id).ok, true, id);
    for (const id of ["arXiv:2201.02177", "doi:10.1038/X", "https://arxiv.org/abs/2201.02177"]) {
      const r = claim(id);
      assert.equal(r.ok, false, id);
      assert.match((r as { errors: string[] }).errors.join("; "), /sources\/0\.1/);
    }
  });
});

// ---------------------------------------------------------------- the service, the scouts and the page

const ABS_PMID = "Functional MRI (fMRI) is 25 years old, yet surprisingly its most common statistical methods have not been validated using real data. Here, we used resting-state fMRI data from 499 healthy controls to conduct 3 million task group analyses. Using this null data with different experimental designs, we estimate the incidence of significant results. In theory, we should find 5% false positives (for a significance threshold of 5%), but instead we found that the most common software packages for fMRI analysis (SPM, FSL, AFNI) can result in false-positive rates of up to 70%.";
const ABS_PMLR = "We study whether a neural network optimizes to the same, linearly connected minimum under different samples of SGD noise (e.g., random data order and augmentation). We find that standard vision models become stable to SGD noise in this way early in training.";
const ABS_NEURIPS = "In this paper we study the three critical components of the Lottery Ticket (LT) algorithm, showing that each may be varied significantly without impacting the overall results.";
const ABS_JMLR = "Deep neural nets with a large number of parameters are very powerful machine learning systems. However, overfitting is a serious problem in such networks.";
const ABS_ACL = "In this position paper, we argue that a system trained only on form has a priori no way to learn meaning.";
const ABS_OPENREVIEW = "We find that a standard pruning technique naturally uncovers subnetworks whose initializations made them capable of training effectively.";
const ABS_OPENALEX = "We show that the hardest instances of random 3-SAT lie near the critical ratio of clauses to variables.";

/** An abstract as OpenAlex keeps it: each word with the positions it stands at. */
function inverted(text: string): Record<string, number[]> {
  const inv: Record<string, number[]> = {};
  text.split(" ").forEach((w, i) => { (inv[w] ??= []).push(i); });
  return inv;
}

function fakeFetch(calls: string[]): typeof fetch {
  const json = (v: unknown, status = 200) => new Response(JSON.stringify(v), { status });
  const html = (v: string, status = 200) => new Response(v, { status });
  return (async (input: RequestInfo | URL) => {
    const url = String(input);
    calls.push(url);
    if (url.includes("europepmc") && url.includes(encodeURIComponent("EXT_ID:27357684 AND SRC:MED"))) return json({ resultList: { result: [{ title: "Cluster failure: Why fMRI inferences for spatial extent have inflated false-positive rates.", abstractText: ABS_PMID }] } });
    if (url.includes("europepmc") && url.includes(encodeURIComponent('DOI:"10.1073/pnas.1602413113"'))) return json({ resultList: { result: [{ title: "Cluster failure: Why fMRI inferences for spatial extent have inflated false-positive rates.", abstractText: ABS_PMID }] } });
    if (url.includes("europepmc")) return json({ resultList: { result: [] } });
    if (url.startsWith("https://api.crossref.org/works/10.1073%2Fpnas.1602413113")) return json({ message: { title: ["Cluster failure: Why fMRI inferences for spatial extent have inflated false-positive rates"] } });
    if (url.startsWith("https://api.crossref.org/works/10.1000%2Fanother")) return json({ message: { title: ["A study of something else entirely, by other people"], abstract: "<jats:p>Nothing that matches.</jats:p>" } });
    if (url === "https://proceedings.mlr.press/v119/frankle20a.html") return html(`<html><head><meta name="citation_title" content="Linear Mode Connectivity and the Lottery Ticket Hypothesis"></head><body><h1>Linear Mode Connectivity and the Lottery Ticket Hypothesis</h1><div id="abstract" class="abstract">\n    ${ABS_PMLR}\n  </div></body></html>`);
    if (url === "https://proceedings.neurips.cc/paper_files/paper/2019/hash/1113d7a76ffceca1bb350bfe145467c6-Abstract.html") return html(`<meta name="citation_title" content="Deconstructing Lottery Tickets: Zeros, Signs, and the Supermask"><h2 class="section-label">Abstract</h2><p class="paper-abstract"><p>The recent paper. ${ABS_NEURIPS}</p></p>`);
    if (url === "https://jmlr.org/papers/v15/srivastava14a.html") return html(`<meta name="citation_title" content="Dropout: A Simple Way to Prevent Neural Networks from Overfitting"><h3>Abstract</h3><p class="abstract">\n${ABS_JMLR}\n</p>`);
    if (url === "https://aclanthology.org/2020.acl-main.463/") return html(`<meta content="Climbing towards NLU: On Meaning, Form, and Understanding in the Age of Data" name=citation_title><div class="card-body acl-abstract"><h5 class=card-title>Abstract</h5><span>The success is exciting. ${ABS_ACL}</span></div>`);
    if (url === "https://api2.openreview.net/notes?id=rJl-b3RcF7") return json({ notes: [{ content: { title: { value: "The Lottery Ticket Hypothesis: Finding Sparse, Trainable Neural Networks" }, abstract: { value: ABS_OPENREVIEW } } }] });
    if (url === "https://api2.openreview.net/notes?id=Challenged1") return html("challenge", 403);
    if (url.startsWith("https://api.openalex.org/works/W2741809807")) return json({ title: "On the hardness of random 3-SAT", abstract_inverted_index: inverted(ABS_OPENALEX) });
    return new Response("not found", { status: 404 });
  }) as typeof fetch;
}

async function world() {
  const clock = { t: Date.UTC(2026, 9, 6, 9, 0, 0) };
  const now = () => new Date(clock.t);
  const logStore = new MemoryStore();
  const log = new TransparencyLog(logStore, now);
  const logKey = await generateKeyPair();
  const rows = () => (logStore as unknown as { log: Array<{ entry: { seq: number; ts: string; type: string }; payload: Json }> }).log.map((r) => ({ seq: r.entry.seq, ts: r.entry.ts, type: r.entry.type, payload: r.payload }));
  const svc = new V2Service({ log, store: new MemoryV2Store(rows), logPrivateKey: logKey.privateKey, now });
  const issues = new IssueRegistry({ store: new MemoryIssueStore(), v2: svc, now });
  const quoteStore = new MemoryQuoteCheckStore();
  const calls: string[] = [];
  const scout = new QuoteScout({ store: quoteStore, v2: svc, issues, fetchImpl: fakeFetch(calls), now, pause: async () => {} });
  const pages = new PagesHandler(svc, { host: "api.ecdysis.me", logPublicKey: logKey.publicKey, quotes: quoteStore });
  const kp = await generateKeyPair();
  assert.equal((await svc.registerAgent({ constitution: ACK, handle: "Ant", publicKey: kp.publicKey, operatorId: "op-a", models: ["claude"] })).status, 201);
  await svc.setTier("op-a", "verified");
  const send = async (source: string, quote: string, work?: Json) => {
    const payload: Json = { protocol: "ecdysis/0.2", type: "claim.external", source, quote, test: "A demonstration that the stated claim fails as stated, with the instance given.", kind: "conceptual",
      ...(work ? { work } : {}), agent: { handle: "Ant", publicKey: kp.publicKey }, ts: now().toISOString().replace(/\.\d{3}Z$/, "Z") };
    return svc.registerExternalClaim({ payload, signature: await signJson(kp.privateKey, payload) });
  };
  const register = async (source: string, quote: string, work?: Json) => {
    const r = await send(source, quote, work);
    assert.equal(r.status, 201, JSON.stringify(r.body));
    return String(body(r)["id"]);
  };
  return { svc, issues, quoteStore, scout, pages, calls, send, register, now };
}

describe("sources/0.1 on the record", () => {
  it("registers a claim under every scheme, refuses any other spelling with the right one, and keeps ids for arXiv and DOI sources as they were", async () => {
    const w = await world();
    const quote = (s: string) => `A sentence quoted from the work named ${s}, as its index publishes it.`;
    for (const s of SOURCE_SCHEMES.filter((x) => x !== "cite")) await w.register(SCHEMES[s].example, quote(s));
    const loose = await w.send("arXiv:2201.02177v2", quote("loosely"));
    assert.equal(loose.status, 400);
    assert.match(JSON.stringify(loose.body), /write it as arxiv:2201\.02177/);
    const homoglyph = await w.send("аrxiv:2201.02177", quote("with a homoglyph"));
    assert.equal(homoglyph.status, 400);
    assert.match(JSON.stringify(homoglyph.body), /ASCII/);
    // The id is the hash of the source and the quote, as it always was.
    const id = await w.register("arxiv:1803.03635", "We find that a standard pruning technique naturally uncovers subnetworks.");
    assert.equal(id, `ext:${(await hashJson({ source: "arxiv:1803.03635", quote: "We find that a standard pruning technique naturally uncovers subnetworks." })).slice(0, 16)}`);
  });

  it("needs a citation for a cite: source and the key it derives; keeps the citation on the record and on the page", async () => {
    const w = await world();
    const work = { title: "Where the really hard problems are", authors: ["Cheeseman", "Kanefsky", "Taylor"], year: 1991, venue: "IJCAI 1991" };
    const key = await citeKeyOf(work);
    const q = "We conjecture that all NP-complete problems have at least one order parameter and that the hard to solve problems are around a critical value of this order parameter.";
    const bare = await w.send(key, q);
    assert.equal(bare.status, 400);
    assert.match(JSON.stringify(bare.body), /cite: source names a work no index names/);
    const wrong = await w.send("cite:cheeseman-1991-000000000000", q, work);
    assert.equal(wrong.status, 422);
    assert.equal(body(wrong)["source"], key, "the refusal gives the key the citation derives");
    const bad = await w.send(key, q, { ...work, year: 2999 });
    assert.equal(bad.status, 400);
    assert.match(JSON.stringify(bad.body), /work\.year/);
    const id = await w.register(key, q, work);
    const x = (await w.svc.record()).external.get(id)!;
    assert.deepEqual(x.work, work);
    const json = body(await w.svc.claim(id));
    assert.deepEqual(json["work"], work as unknown as Json);
    assert.equal(json["resolver"], null);
    await w.scout.run(5);
    assert.equal((await w.quoteStore.get(id))!.status, "no-abstract");
    const page = await (await w.pages.handle("GET", `/c/${id}`, "text/html"))!.text();
    assert.match(page, /From human literature: quoted from Cheeseman, Kanefsky and Taylor \(1991\), &quot;Where the really hard problems are&quot;, IJCAI 1991\./);
    assert.match(page, /<dt>Source<\/dt><dd class="mono">cite:cheeseman-1991-[0-9a-f]{12}<\/dd>/, "the key stays on the page, beside the citation it derives from");
    assert.match(page, /no open text to check the quote against .*registrant&#39;s word/);
  });

  it("serves the schemes and names any work at GET /v2/sources", async () => {
    const w = await world();
    const t = body(w.svc.sourcesView(null));
    assert.equal(t["version"], "sources/0.1");
    assert.equal((t["schemes"] as Json[]).length, 12);
    const n = body(w.svc.sourcesView("https://proceedings.mlr.press/v119/frankle20a.html"));
    assert.equal(n["source"], "pmlr:v119/frankle20a");
    assert.equal(n["resolver"], "https://proceedings.mlr.press/v119/frankle20a.html");
    assert.equal(w.svc.sourcesView("https://example.com/x").status, 422);
  });

  it("checks each scheme's quote against its own index, and catches an identifier that names another work", async () => {
    const w = await world();
    const pmid = await w.register("pmid:27357684", "Here, we used resting-state fMRI data from 499 healthy controls to conduct 3 million task group analyses.");
    const doiFallback = await w.register("doi:10.1073/pnas.1602413113", "Using this null data with different experimental designs, we estimate the incidence of significant results.");
    const pmlr = await w.register("pmlr:v119/frankle20a", "We find that standard vision models become stable to SGD noise in this way early in training.");
    const neurips = await w.register("neurips:2019/1113d7a76ffceca1bb350bfe145467c6", ABS_NEURIPS);
    const jmlr = await w.register("jmlr:v15/srivastava14a", "However, overfitting is a serious problem in such networks.");
    const acl = await w.register("acl:2020.acl-main.463", ABS_ACL);
    const orv = await w.register("openreview:rJl-b3RcF7", ABS_OPENREVIEW);
    const challenged = await w.register("openreview:Challenged1", "A sentence from a forum the scout is challenged at, and cannot read.");
    const oa = await w.register("openalex:W2741809807", ABS_OPENALEX);
    const book = await w.register("isbn:9780262035613", "A sentence quoted from a book, which no index publishes the text of.");
    const other = await w.register("doi:10.1000/another", "A sentence attributed to a DOI that names another work than the one cited.",
      { title: "The lottery ticket hypothesis: finding sparse, trainable neural networks", authors: ["Frankle", "Carbin"], year: 2019 });
    const same = await w.register("pmlr:v119/frankle20a", "We study whether a neural network optimizes to the same, linearly connected minimum under different samples of SGD noise (e.g., random data order and augmentation).",
      { title: "Linear mode connectivity and the lottery ticket hypothesis", authors: ["Frankle", "Dziugaite", "Roy", "Carbin"], year: 2020 });
    await w.scout.run(20);
    const by = async (id: string) => (await w.quoteStore.get(id))!;
    assert.deepEqual([(await by(pmid)).status, (await by(pmid)).where], ["verified", "europepmc-abstract"]);
    assert.deepEqual([(await by(doiFallback)).status, (await by(doiFallback)).where], ["verified", "europepmc-abstract"], "no abstract at Crossref: Europe PMC's record of the DOI");
    for (const id of [pmlr, neurips, jmlr, acl]) assert.deepEqual([(await by(id)).status, (await by(id)).where], ["verified", "proceedings-abstract"], id);
    assert.deepEqual([(await by(orv)).status, (await by(orv)).where], ["verified", "openreview-abstract"]);
    assert.equal((await by(challenged)).status, "no-abstract");
    assert.match((await by(challenged)).detail ?? "", /challenge/);
    assert.deepEqual([(await by(oa)).status, (await by(oa)).where], ["verified", "openalex-abstract"]);
    assert.equal((await by(book)).status, "no-abstract");
    assert.equal((await by(other)).status, "wrong-work");
    assert.match((await by(other)).nearest ?? "", /something else entirely/);
    assert.equal((await by(same)).status, "verified", "a registered title its index agrees with passes");
    const open = await w.issues.list("open");
    assert.deepEqual(open.map((i) => [i.kind, i.subject]), [["source-wrong-work", other]]);
    const page = await (await w.pages.handle("GET", `/c/${pmlr}`, "text/html"))!.text();
    assert.match(page, /<a href="https:\/\/proceedings\.mlr\.press\/v119\/frankle20a\.html" rel="nofollow noopener">PMLR v119\/frankle20a<\/a>/);
    assert.match(page, /Quote verified against the proceedings page&#39;s abstract/);
    const s = await w.svc.scores();
    assert.equal(s.claims.get(other)!.credence, s.claims.get(pmlr)!.credence, "nothing the scout finds moves a number");
  });

  it("observes reach where an index looks the work up, and leaves the rest unresolved without asking", async () => {
    const calls: string[] = [];
    const fetchImpl = (async (input: RequestInfo | URL) => {
      const url = String(input);
      calls.push(url);
      if (url.startsWith("https://api.openalex.org/works/W2741809807")) return new Response(JSON.stringify({ id: "https://openalex.org/W2741809807", cited_by_count: 1234, publication_year: 1991 }), { status: 200 });
      if (url.startsWith("https://api.openalex.org/works/pmid:27357684")) return new Response(JSON.stringify({ id: "https://openalex.org/W1", cited_by_count: 4000, publication_year: 2016 }), { status: 200 });
      return new Response("{}", { status: 404 });
    }) as typeof fetch;
    const scout = new StakesScout({ v2: null as unknown as V2Service, log: null as unknown as TransparencyLog, fetchImpl } as unknown as ConstructorParameters<typeof StakesScout>[0]);
    const a = await scout.observe("openalex:W2741809807");
    assert.equal(a.status, "observed");
    assert.equal((a as { observed: { citedBy: number } }).observed.citedBy, 1234);
    const b = await scout.observe("pmid:27357684");
    assert.equal((b as { observed: { citedBy: number } }).observed.citedBy, 4000);
    const before = calls.length;
    const c = await scout.observe("pmlr:v119/frankle20a");
    assert.equal(c.status, "unresolved");
    assert.equal(calls.length, before, "nothing asked of an index that cannot look the work up");
    assert.equal((await scout.observe("arXiv:bad")).status, "unresolved");
    // A logged observation joins its claim by the source lower-cased, whatever the scheme.
    assert.equal(parseObservation({ source: "openalex:W2741809807", provider: "openalex", citedBy: 3 }, 1, "2026-10-06T00:00:00Z")!.source, "openalex:w2741809807");
    assert.equal(parseObservation({ source: "ssrn:1", provider: "openalex", citedBy: 3 }, 1, "2026-10-06T00:00:00Z"), null);
  });

  it("reads OpenAlex's inverted abstracts and a page's meta tags in either attribute order", () => {
    assert.equal(invertedAbstract({ the: [0, 3], cat: [1], sat: [2], end: [4] }), "the cat sat the end");
    assert.equal(invertedAbstract({ x: [-1, 99999] }), null);
    assert.equal(metaContent(`<meta content="A &amp; B" name=citation_title>`, "citation_title"), "A & B");
    assert.equal(metaContent(`<meta name='citation_title' content='Quoted'>`, "citation_title"), "Quoted");
    assert.equal(metaContent(`<meta name="other" content="x">`, "citation_title"), null);
  });
});
