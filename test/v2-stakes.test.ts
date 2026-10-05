/**
 * stakes/0.1 (claude/ecdysis-claims-map-design.md §3, §5a): how much rests
 * on a claim on and off the record. The core (reach, the venue stand-in for
 * a young paper, S = U + log2(1 + R)), the record (source.observed entries
 * read into reach; the latest per source stands; a malformed one changes
 * nothing), the scout (OpenAlex with the venue's citedness, Semantic Scholar
 * when OpenAlex knows nothing, an unresolved source logged once, an erroring
 * index left for the next run, nothing asked twice within a month), and the
 * surfaces (the frontier ranks by stakes; credence does not move; the claim
 * page states the inputs; the API serves stakes and reach). The adversarial
 * point is structural: no endpoint writes source.observed, so no agent can
 * raise a stake.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { MemoryStore } from "../src/store/memory-store.js";
import { TransparencyLog } from "../src/core/log.js";
import { generateKeyPair, signJson, type KeyPairB64 } from "../src/core/crypto.js";
import { structuralScreener } from "../src/core/hazard.js";
import { MemoryV2Store, V2Service } from "../src/api/v2/service.js";
import { route, MemoryRateLimiter } from "../src/api/router.js";
import { PagesHandler } from "../src/api/v2/pages.js";
import { StakesScout } from "../src/api/v2/stakes-scout.js";
import { parseObservation, reachOf, stakesOf, type SourceObservation } from "../src/core/v2/stakes.js";
import { deriveV2 } from "../src/core/v2/flow.js";
import type { Json } from "../src/core/canonical.js";
import { CONSTITUTION_VERSION, constitutionHash } from "../src/core/constitution.js";
import { declared } from "./kinds-kit.js";

const ACK = { version: CONSTITUTION_VERSION, hash: await constitutionHash() };
const body = (r: { body: Json }) => r.body as Record<string, Json>;
const NOW = new Date(Date.UTC(2026, 9, 4, 22, 0, 0));

describe("stakes/0.1: the core", () => {
  const obs = (over: Partial<SourceObservation>): SourceObservation => ({ source: "doi:10.1/x", provider: "openalex", work: "W1", citedBy: 0, venueCitedness: null, year: null, field: null, fieldId: null, unresolved: false, observedAt: "2026-10-04T22:00:00Z", seq: 1, ...over });
  it("reach is the citation count, or for a paper under two years old its venue's expected citations when larger", () => {
    assert.equal(reachOf(null, NOW), 0);
    assert.equal(reachOf(obs({ citedBy: 2480 }), NOW), 2480);
    assert.equal(reachOf(obs({ citedBy: 3, year: 2026, venueCitedness: 12.5 }), NOW), 25, "young: 12.5 a year over two years stands in for 3");
    assert.equal(reachOf(obs({ citedBy: 40, year: 2026, venueCitedness: 12.5 }), NOW), 40, "young but already past the venue's expectation");
    assert.equal(reachOf(obs({ citedBy: 3, year: 2023, venueCitedness: 12.5 }), NOW), 3, "three years old: its own citations only");
    assert.equal(reachOf(obs({ citedBy: 3, year: 2026, venueCitedness: null }), NOW), 3, "no venue figure (an arXiv paper): its own citations");
    assert.equal(reachOf(obs({ citedBy: 0, unresolved: true }), NOW), 0);
  });
  it("S = U + log2(1 + R): a thousand citations count like ten dependants; no reach leaves stakes equal to use", () => {
    assert.equal(stakesOf(0, 0), 0);
    assert.equal(stakesOf(3, 0), 3);
    assert.ok(Math.abs(stakesOf(0, 1023) - 10) < 1e-9);
    assert.ok(Math.abs(stakesOf(2, 7) - 5) < 1e-9);
    assert.equal(stakesOf(-1, -5), 0, "never negative");
  });
  it("parses a source.observed payload and rejects what is not one", () => {
    const p = parseObservation({ source: "DOI:10.1038/Nature", provider: "openalex", work: "W123", citedBy: 2480.7, venueCitedness: 41.2, year: 2019, field: "Computer Science" }, 9, "2026-10-04T22:00:00Z")!;
    assert.equal(p.source, "doi:10.1038/nature", "lower-cased");
    assert.equal(p.citedBy, 2480);
    assert.equal(p.venueCitedness, 41.2);
    assert.equal(p.year, 2019);
    assert.equal(p.field, "Computer Science");
    assert.equal(p.unresolved, false);
    const u = parseObservation({ source: "arxiv:2501.00001", provider: "openalex", work: null, citedBy: 0, unresolved: true }, 10, "2026-10-04T22:00:00Z")!;
    assert.equal(u.unresolved, true);
    assert.equal(u.citedBy, 0);
    for (const bad of [{ source: "isbn:1", provider: "openalex", citedBy: 1 }, { source: "doi:10.1/x", provider: "scopus", citedBy: 1 }, { source: "doi:10.1/x", provider: "openalex", citedBy: -1 }, { source: "doi:10.1/x", provider: "openalex" }]) {
      assert.equal(parseObservation(bad, 1, "2026-10-04T22:00:00Z"), null, JSON.stringify(bad));
    }
  });
  it("the record reads the latest observation per source into the claims' reach; a malformed entry changes nothing", () => {
    const key = "MCowBQYDK2VwAyEA" + "A".repeat(43);
    const entries = [
      { seq: 0, ts: "2026-10-04T09:00:00Z", type: "constitution.adopt" as const, payload: { version: "2.0.0", hash: "b".repeat(64), ts: "2026-10-04T09:00:00Z", signature: "x" } },
      { seq: 1, ts: "2026-10-04T09:00:00Z", type: "agent.register" as const, payload: { handle: "Ant", operatorId: "op-a", publicKey: key } },
      { seq: 2, ts: "2026-10-04T09:00:00Z", type: "claim.external" as const, payload: { id: "ext:" + "1".repeat(16), handle: "Ant", operatorId: "op-a", source: "arxiv:2203.15556", quote: "a quote of ten words", test: "a test of ten words" } },
      { seq: 3, ts: "2026-10-04T09:00:00Z", type: "source.observed" as const, payload: { source: "arxiv:2203.15556", provider: "openalex", work: "W1", citedBy: 100, year: 2022 } },
      { seq: 4, ts: "2026-10-04T10:00:00Z", type: "source.observed" as const, payload: { source: "ARXIV:2203.15556", provider: "semanticscholar", work: "abc", citedBy: 255, year: 2022 } },
      { seq: 5, ts: "2026-10-04T11:00:00Z", type: "source.observed" as const, payload: { source: "arxiv:2203.15556", provider: "nowhere", citedBy: 9999 } },
    ];
    const r = deriveV2(entries, NOW);
    const obs = r.observations.get("arxiv:2203.15556")!;
    assert.equal(obs.citedBy, 255, "the latest well-formed observation stands");
    assert.equal(obs.provider, "semanticscholar");
    assert.equal(r.claims[0]!.reach, 255);
  });
});

async function world() {
  const clock = { t: NOW.getTime() };
  const now = () => new Date(clock.t);
  const logStore = new MemoryStore();
  const log = new TransparencyLog(logStore, now);
  const logKey = await generateKeyPair();
  const rows = () => (logStore as unknown as { log: Array<{ entry: { seq: number; ts: string; type: string }; payload: Json }> }).log.map((r) => ({ seq: r.entry.seq, ts: r.entry.ts, type: r.entry.type, payload: r.payload }));
  const svc = new V2Service({ log, store: new MemoryV2Store(rows), logPrivateKey: logKey.privateKey, now, screeners: [structuralScreener()] });
  const pages = new PagesHandler(svc, { host: "api.ecdysis.me" });
  const limiter = new MemoryRateLimiter(10_000);
  const keys = new Map<string, KeyPairB64>();
  const agent = async (handle: string, op: string, models?: string[]) => {
    const kp = await generateKeyPair();
    keys.set(handle, kp);
    assert.equal((await svc.registerAgent({ constitution: ACK, handle, publicKey: kp.publicKey, operatorId: op, ...(models ? { models } : {}) })).status, 201);
    await svc.setTier(op, "verified");
    return kp;
  };
  const sign = async (handle: string, payload: Record<string, Json>) => {
    const kp = keys.get(handle)!;
    const full: Json = declared({ ...payload, agent: { handle, publicKey: kp.publicKey }, ts: now().toISOString().replace(/\.\d{3}Z$/, "Z") });
    return { payload: full, signature: await signJson(kp.privateKey, full) } as Json;
  };
  const register = async (handle: string, source: string, quote: string) => {
    const r = await svc.registerExternalClaim(await sign(handle, { protocol: "ecdysis/0.2", type: "claim.external", source, quote, test: "A re-analysis of the paper's own data giving a value outside its interval." }));
    assert.equal(r.status, 201, JSON.stringify(r.body));
    return String(body(r)["ref"]);
  };
  const get = async (path: string) => { const r = await route(new Request(`https://api.ecdysis.me${path}`), limiter, { v2: svc, pages }); return { status: r.status, body: (await r.json()) as Record<string, Json> }; };
  const page = async (path: string) => { const r = await route(new Request(`https://api.ecdysis.me${path}`, { headers: { accept: "text/html" } }), limiter, { v2: svc, pages }); return { status: r.status, html: await r.text() }; };
  return { svc, log, agent, sign, register, get, page, now, tick: (ms: number) => { clock.t += ms; } };
}

/** A fake of the two indexes: OpenAlex knows the Chinchilla paper and a journal paper with a venue (both in its field 17, whose totals it serves); Semantic Scholar knows a third; nobody knows the fourth; the fifth errors. */
function fakeGraph() {
  const calls: string[] = [];
  const json = (status: number, b: unknown) => new Response(JSON.stringify(b), { status, headers: { "content-type": "application/json" } });
  const fetchImpl: typeof fetch = async (input) => {
    const url = String(input);
    calls.push(url);
    if (url.includes("api.openalex.org/works/doi:10.48550%2FarXiv.2203.15556")) return json(200, { id: "https://openalex.org/W4225", cited_by_count: 2480, publication_year: 2022, primary_topic: { display_name: "Natural Language Processing", field: { display_name: "Computer Science", id: "https://openalex.org/fields/17" } }, primary_location: { source: null } });
    if (url.includes("api.openalex.org/works/doi:10.1038%2Fs41586-026-10549-w")) return json(200, { id: "https://openalex.org/W9001", cited_by_count: 3, publication_year: 2026, primary_topic: { field: { display_name: "Computer Science", id: "https://openalex.org/fields/17" } }, primary_location: { source: { id: "https://openalex.org/S137773608", display_name: "Nature" } } });
    if (url.includes("api.openalex.org/sources/S137773608")) return json(200, { id: "https://openalex.org/S137773608", summary_stats: { "2yr_mean_citedness": 41.25, h_index: 1500 } });
    if (url.includes("api.openalex.org/fields/17")) return json(200, { id: "https://openalex.org/fields/17", display_name: "Computer Science", works_count: 30_000_000, cited_by_count: 250_000_000 });
    if (url.includes("api.openalex.org/works/doi:10.48550%2FarXiv.2609.99999")) return json(404, { error: "not found" });
    if (url.includes("api.semanticscholar.org/graph/v1/paper/arXiv%3A2609.99999")) return json(200, { paperId: "s2abc", citationCount: 7, year: 2026, s2FieldsOfStudy: [{ category: "Computer Science", source: "s2-fos-model" }] });
    if (url.includes("doi:10.9999%2Fnobody")) return json(404, {});
    if (url.includes("DOI%3A10.9999%2Fnobody")) return json(404, {});
    if (url.includes("doi:10.5555%2Fdown")) return json(503, {});
    return json(404, {});
  };
  return { fetchImpl, calls };
}

describe("stakes/0.1: the scout and the surfaces", () => {
  it("observes each registered source once (OpenAlex, with the venue for a journal paper; Semantic Scholar when OpenAlex knows nothing), logs what it found, and leaves an erroring index for the next run", async () => {
    const w = await world();
    await w.agent("Ant", "op-a", ["claude-opus-5-5"]);
    const chinchilla = await w.register("Ant", "arxiv:2203.15556", "for compute-optimal training, the model size and the number of training tokens should be scaled equally");
    const nature = await w.register("Ant", "doi:10.1038/s41586-026-10549-w", "dominant headline metrics such as accuracy systematically reward guessing over acknowledging uncertainty");
    const young = await w.register("Ant", "arxiv:2609.99999", "a sentence from a very recent preprint that only one index has seen so far");
    const nobody = await w.register("Ant", "doi:10.9999/nobody", "a sentence from a source no open index knows about at all");
    const down = await w.register("Ant", "doi:10.5555/down", "a sentence from a source whose index is down this quarter hour");
    const before = (await w.svc.scores()).claims;
    for (const ref of [chinchilla, nature, young, nobody, down]) assert.equal(before.get(ref)!.stakes, 0, "no observation yet: stakes are use, which is 0");
    const graph = fakeGraph();
    const scout = new StakesScout({ v2: w.svc, log: w.log, fetchImpl: graph.fetchImpl, now: w.now, pause: async () => {} });
    const run = await scout.run(10);
    assert.deepEqual(run, { observed: 3, unresolved: 1, errors: 1, fields: 1, candidates: 0 }, "no candidates store here: none read");
    const r = await w.svc.record();
    assert.equal(r.observations.size, 4, "three observed, one unresolved, the erroring one not logged");
    assert.equal(r.observations.get("arxiv:2203.15556")!.fieldId, "17");
    assert.deepEqual([...r.fieldObservations.keys()], ["Computer Science"], "the one field the observed sources sit in, read once");
    assert.equal(r.fieldObservations.get("Computer Science")!.citedBy, 250_000_000);
    assert.equal(r.fieldObservations.get("Computer Science")!.works, 30_000_000);
    assert.equal(r.observations.get("arxiv:2203.15556")!.citedBy, 2480);
    assert.equal(r.observations.get("arxiv:2203.15556")!.field, "Computer Science");
    assert.equal(r.observations.get("doi:10.1038/s41586-026-10549-w")!.venueCitedness, 41.25);
    assert.equal(r.observations.get("arxiv:2609.99999")!.provider, "semanticscholar");
    assert.equal(r.observations.get("arxiv:2609.99999")!.citedBy, 7);
    assert.equal(r.observations.get("doi:10.9999/nobody")!.unresolved, true);
    assert.equal(r.observations.has("doi:10.5555/down"), false);
    // The second run asks only about the erroring source: the others were observed within the month.
    const n = graph.calls.length;
    const again = await scout.run(10);
    assert.deepEqual(again, { observed: 0, unresolved: 0, errors: 1, fields: 0, candidates: 0 });
    assert.equal(graph.calls.length - n, 1, "one request, for the one source still due; the field's totals are a month good");
    // A month on, every source is due again.
    w.tick(31 * 24 * 3600 * 1000);
    const later = await scout.run(10);
    assert.equal(later.observed + later.unresolved + later.errors, 5);
    assert.equal(later.fields, 1, "and the field's totals are read again");

    // The stakes: Chinchilla log2(2481) ≈ 11.28; the Nature paper is young, so its venue's 82.5 expected citations stand in for 3: log2(83.5) ≈ 6.38; the preprint log2(8) = 3; the unknown 0.
    const s = (await w.svc.scores()).claims;
    assert.ok(Math.abs(s.get(chinchilla)!.stakes - Math.log2(2481)) < 1e-9);
    assert.equal(s.get(chinchilla)!.reach, 2480);
    assert.ok(Math.abs(s.get(nature)!.stakes - Math.log2(1 + 82.5)) < 1e-9);
    assert.equal(s.get(young)!.stakes, 3);
    assert.equal(s.get(nobody)!.stakes, 0);
    // Credence did not move: a citation is not evidence.
    for (const ref of [chinchilla, nature, young, nobody, down]) {
      assert.equal(s.get(ref)!.credence, before.get(ref)!.credence, `${ref}: credence unchanged by observation`);
      assert.equal(s.get(ref)!.status, "unchecked");
      assert.equal(s.get(ref)!.threshold, before.get(ref)!.threshold, "the bar for established stays on use");
    }
    // The frontier ranks by stakes: Chinchilla first, the unknown last among equals.
    const fr = await w.get("/v2/frontier");
    const checking = fr.body["checking"] as Array<Record<string, Json>>;
    assert.equal(checking[0]!["ref"], chinchilla);
    assert.equal(checking[0]!["stakes"], 11.2767, "the API rounds to four places");
    assert.ok((checking[0]!["value"] as number) > (checking[1]!["value"] as number));
    assert.equal(checking[1]!["ref"], nature);
    // The API serves stakes and reach; the claim page states the inputs.
    const list = (await w.get("/v2/credence")).body["claims"] as Array<Record<string, Json>>;
    assert.equal(list.find((c) => c["ref"] === chinchilla)!["reach"], 2480);
    const pg = await w.page(`/x/${chinchilla.slice(4).replace("#C1", "")}/C1`);
    assert.equal(pg.status, 200);
    assert.match(pg.html, /Stakes 11\.28<\/b> = use \+ log<sub>2<\/sub>\(1 \+ reach\): 0 dependants on the record; reach 2,480: cited 2,480 times \(OpenAlex/);
    assert.match(pg.html, /field: Computer Science/);
    const pgN = await w.page(`/x/${nature.slice(4).replace("#C1", "")}/C1`);
    assert.match(pgN.html, /a young paper, so its venue's expected citations \(41\.25 a year over two years\) stand in for its own 3/);
    const pgU = await w.page(`/x/${nobody.slice(4).replace("#C1", "")}/C1`);
    assert.match(pgU.html, /reach 0: no open index knew this source/);
    const pgD = await w.page(`/x/${down.slice(4).replace("#C1", "")}/C1`);
    assert.match(pgD.html, /reach not yet observed/);
    // Nothing on the record moved for anyone's credence; the audit's strings would show it if it had.
  });

  it("no agent can write an observation: the API has no endpoint for source.observed and the log type is the platform's", async () => {
    const w = await world();
    await w.agent("Ant", "op-a", ["claude-opus-5-5"]);
    const ref = await w.register("Ant", "arxiv:2203.15556", "for compute-optimal training, the model size and the number of training tokens should be scaled equally");
    for (const path of ["/v2/sources/observed", "/v2/observations", "/v2/stakes"]) {
      const r = await route(new Request(`https://api.ecdysis.me${path}`, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(await w.sign("Ant", { protocol: "ecdysis/0.2", type: "source.observed", source: "arxiv:2203.15556", provider: "openalex", citedBy: 1e9 })) }), new EcdysisService({ store: new MemoryStore(), screeners: [structuralScreener()], sthPrivateKey: null }), new MemoryRateLimiter(1000), { v2: w.svc, pages: new PagesHandler(w.svc, { host: "api.ecdysis.me" }) });
      assert.equal(r.status, 404, path);
    }
    assert.equal((await w.svc.scores()).claims.get(ref)!.stakes, 0);
  });
});
