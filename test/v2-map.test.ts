/**
 * The claims map (map/0.1; claude/ecdysis-claims-map-design.md §5): how
 * completely the literature has been assessed, field by field, and where the
 * stakes still sit. The core builds the per-field funnel (registered →
 * attempted → blocked, by blocker → assessed → resolved; each a count and a
 * sum of stakes), the coverage against the citation graph's field totals,
 * and the three lists (the unchecked, under pressure, cleared), all
 * deterministic. The service places claims by their source's observed field
 * (an Ecdysis paper by its declared field), serves the map at GET /v2/map
 * and the get_map tool, and draws it script-free at /map; the observatory,
 * the graph, the agent and paper pages carry attempts and stakes too. The
 * challenge board that used to direct attention sends its visitors here.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { MemoryStore } from "../src/store/memory-store.js";
import { TransparencyLog } from "../src/core/log.js";
import { generateKeyPair, signJson, type KeyPairB64 } from "../src/core/crypto.js";
import { structuralScreener } from "../src/core/hazard.js";
import { MemoryV2Store, V2Service } from "../src/api/v2/service.js";
import { EcdysisService } from "../src/api/service.js";
import { route, MemoryRateLimiter } from "../src/api/router.js";
import { PagesHandler } from "../src/api/v2/pages.js";
import { handleMcp } from "../src/api/mcp.js";
import { v2Tools } from "../src/api/v2/tools.js";
import { buildMap, MAP_VERSION, UNPLACED_FIELD, type MapClaim } from "../src/core/v2/map.js";
import type { FieldObservation } from "../src/core/v2/stakes.js";
import { BLOCKER_SIDE, type ClaimBlockers } from "../src/core/v2/attempts.js";
import type { Bundle } from "../src/core/v2/receipts.js";
import type { Json } from "../src/core/canonical.js";
import { CONSTITUTION_VERSION, constitutionHash } from "../src/core/constitution.js";
import { declared } from "./kinds-kit.js";

const ACK = { version: CONSTITUTION_VERSION, hash: await constitutionHash() };
const body = (r: { body: Json }) => r.body as Record<string, Json>;
const DETAIL = "Went to the paper's data statement, the supplementary files and the authors' lab page: the panel the test needs is described but published nowhere, and the lab page says it is available on request only.";
const UNBLOCK = "The authors releasing the panel, or pointing to where it is deposited.";

/** A scored claim as the service hands it to the core, with every flag off unless given. */
function claim(ref: string, field: string, stakes: number, over: Partial<MapClaim> = {}): MapClaim {
  const external = ref.startsWith("ext:");
  return { ref, paper: ref.split("#")[0]!, external, field, source: external ? `doi:10.1/${ref.slice(4, 8)}` : null, stakes, reach: 0, use: stakes, credence: 0.5, status: "unchecked", attempted: false, blocked: null, assessed: false, resolved: false, attempts: 0, ...over };
}
/** A claim's blockers as the record summarises them (attempts/0.2): the authors' carry the pressure's n, the operator's are its capability. */
const blockedBy = (verifiedOperators: number, ...blockers: Array<"data-unavailable" | "compute">): ClaimBlockers => {
  const authors = blockers.filter((b) => BLOCKER_SIDE[b] === "author");
  return {
    claim: "", verifiedOperators: authors.length ? verifiedOperators : 0, dominant: authors[0] ?? null, capability: blockers.filter((b) => BLOCKER_SIDE[b] === "operator"),
    blockers: blockers.map((b) => ({ blocker: b, side: BLOCKER_SIDE[b], verifiedOperators, otherOperators: 0, unsupported: 0, attempts: [], unblockedBy: [] })),
  };
};

describe("map/0.1: the core", () => {
  const cs: MapClaim[] = [
    claim("ext:aaaaaaaaaaaaaaaa#C1", "Computer Science", 11, { reach: 2047, use: 0 }),                                   // unchecked, the highest stakes
    claim("ext:bbbbbbbbbbbbbbbb#C1", "Computer Science", 6, { attempted: true, blocked: blockedBy(1, "data-unavailable"), attempts: 1 }),
    claim("ext:cccccccccccccccc#C1", "Computer Science", 4, { attempted: true, assessed: true, status: "supported" }),  // tried, then checked: assessed, not blocked
    claim("ext:dddddddddddddddd#C1", "Mathematics", 3, { assessed: true, resolved: true, status: "established" }),
    claim("ecd:eeeeeeeeeeeeeeee#C1", "Mathematics", 1),
    claim("ext:ffffffffffffffff#C1", "Mathematics", 2, { attempted: true, blocked: blockedBy(2, "compute", "data-unavailable"), attempts: 2 }),
  ];
  const fields = new Map<string, FieldObservation>([["Computer Science", { field: "Computer Science", fieldId: "17", works: 30_000_000, citedBy: 250_000_000, observedAt: "2026-10-04T09:00:00Z", seq: 1 }]]);
  const citations = new Map<string, number>([["doi:10.1/aaaa", 2047], ["doi:10.1/bbbb", 100_000_000], ["doi:10.1/cccc", 5]]);

  it("funnels each field by count and by stakes, with blockers broken out, and measures coverage against the field's citations", () => {
    const m = buildMap(cs, [], fields, citations);
    assert.equal(m.version, MAP_VERSION);
    assert.deepEqual(m.fields.map((f) => f.field), ["Computer Science", "Mathematics"], "fields by registered stakes, descending");
    const cs1 = m.fields[0]!;
    assert.deepEqual(cs1.registered, { claims: 3, stakes: 21 });
    assert.deepEqual(cs1.attempted, { claims: 2, stakes: 10 });
    assert.deepEqual(cs1.blocked, { claims: 1, stakes: 6, byBlocker: { "data-unavailable": { claims: 1, stakes: 6 } } });
    assert.deepEqual(cs1.assessed, { claims: 1, stakes: 4 });
    assert.deepEqual(cs1.resolved, { claims: 0, stakes: 0 });
    assert.equal(cs1.sources, 3);
    assert.equal(cs1.sourcesCitedBy, 100_002_052);
    assert.equal(cs1.coverage, 0.4, "the registered sources' citations as a share of the field's");
    assert.equal(cs1.assessedShare, 0.1905, "4 of 21 stakes assessed, to four places");
    assert.deepEqual(cs1.denominator, fields.get("Computer Science"));
    const math = m.fields[1]!;
    assert.deepEqual(math.registered, { claims: 3, stakes: 6 });
    assert.deepEqual(math.blocked.byBlocker, { compute: { claims: 1, stakes: 2 }, "data-unavailable": { claims: 1, stakes: 2 } }, "a claim with two blockers counts once per blocker");
    assert.deepEqual(math.resolved, { claims: 1, stakes: 3 });
    assert.equal(math.coverage, null, "no totals observed for the field: coverage unknown, not zero");
    assert.equal(math.sources, 2, "an Ecdysis paper's claim is no source in the literature");
    assert.deepEqual(m.totals.registered, { claims: 6, stakes: 27 });
    assert.deepEqual(m.totals.blocked, { claims: 2, stakes: 8, byBlocker: { "data-unavailable": { claims: 2, stakes: 8 }, compute: { claims: 1, stakes: 2 } } });
    assert.equal(m.totals.assessedShare, 0.2593);
    assert.ok(!("coverage" in m.totals) && !("field" in m.totals), "totals have no field and no single denominator");
  });

  it("lists the unchecked by stakes, the blocked by pressure, and the clearings newest first; limits apply to each; coverage never exceeds one", () => {
    const cleared = [
      { ref: "ext:cccccccccccccccc#C1", blocker: "data-unavailable" as const, by: "a receipt", how: null, at: "2026-10-03T10:00:00Z", seq: 40 },
      { ref: "ext:zzzzzzzzzzzzzzzz#C1", blocker: "compute" as const, by: "Ant", how: "A smaller instance of the same family is now stated in the protocol.", at: "2026-10-04T10:00:00Z", seq: 50 },
    ];
    const m = buildMap(cs, cleared, fields, citations);
    assert.deepEqual(m.unchecked.map((c) => c.ref), ["ext:aaaaaaaaaaaaaaaa#C1", "ecd:eeeeeeeeeeeeeeee#C1"], "nothing filed, by stakes; attempted, assessed, blocked and resolved claims are not unchecked");
    assert.deepEqual(m.unchecked[0], { ref: "ext:aaaaaaaaaaaaaaaa#C1", field: "Computer Science", stakes: 11, reach: 2047, use: 0, credence: 0.5, status: "unchecked", external: true });
    assert.deepEqual(m.underPressure.map((c) => [c.ref, c.pressure, c.verifiedOperators]), [["ext:bbbbbbbbbbbbbbbb#C1", 3, 1], ["ext:ffffffffffffffff#C1", 1.5, 2]], "pressure = stakes × (1 − 2^−n): 6 × ½, 2 × ¾");
    assert.deepEqual(m.underPressure[1]!.blockers, ["compute", "data-unavailable"], "every blocker in force is listed");
    assert.equal(m.underPressure[1]!.dominant, "data-unavailable", "the pressure is attributed to the authors' blocker, never to the operator's");
    assert.deepEqual(m.needsCapability.map((c) => [c.ref, c.capability, c.verifiedOperators]), [["ext:ffffffffffffffff#C1", ["compute"], 2]], "the operator's blockers, by stakes: where a sponsor or an operator with the hardware can help");
    const opsOnly = buildMap([claim("ext:1111111111111111#C1", "Physics", 9, { attempted: true, blocked: blockedBy(1, "compute"), attempts: 1 })], [], fields, citations);
    assert.deepEqual(opsOnly.underPressure, [], "a claim blocked only on the operator's side presses nobody");
    assert.deepEqual(opsOnly.needsCapability.map((c) => c.ref), ["ext:1111111111111111#C1"]);
    assert.deepEqual(opsOnly.totals.blocked, { claims: 1, stakes: 9, byBlocker: { compute: { claims: 1, stakes: 9 } } }, "it is still blocked in the funnel");
    assert.deepEqual(m.cleared.map((c) => [c.ref, c.by, c.field, c.stakes]), [["ext:zzzzzzzzzzzzzzzz#C1", "Ant", UNPLACED_FIELD, 0], ["ext:cccccccccccccccc#C1", "a receipt", "Computer Science", 4]], "newest first; a clearing on a claim no longer scored is placed nowhere, with no stakes");
    const one = buildMap(cs, cleared, fields, citations, 1);
    assert.equal(one.unchecked.length, 1); assert.equal(one.underPressure.length, 1); assert.equal(one.needsCapability.length, 1); assert.equal(one.cleared.length, 1);
    const over = buildMap(cs, [], fields, new Map([["doi:10.1/aaaa", 10 ** 12]]));
    assert.equal(over.fields[0]!.coverage, 1, "more citations than the field's total (a stale denominator) reads as full coverage, never more");
  });

  it("is deterministic whatever the input order, and empty input gives an empty map", () => {
    const a = buildMap(cs, [], fields, citations);
    const b = buildMap([...cs].reverse(), [], fields, citations);
    assert.deepEqual(a, b);
    const e = buildMap([], [], new Map(), new Map());
    assert.deepEqual(e.fields, []);
    assert.deepEqual(e.totals.registered, { claims: 0, stakes: 0 });
    assert.equal(e.totals.assessedShare, null);
    assert.deepEqual([e.unchecked, e.underPressure, e.needsCapability, e.cleared], [[], [], [], []]);
  });
});

async function world() {
  const clock = { t: Date.UTC(2026, 9, 5, 9, 0, 0) };
  const now = () => new Date(clock.t);
  const logStore = new MemoryStore();
  const log = new TransparencyLog(logStore, now);
  const logKey = await generateKeyPair();
  const rows = () => (logStore as unknown as { log: Array<{ entry: { seq: number; ts: string; type: string }; payload: Json }> }).log.map((r) => ({ seq: r.entry.seq, ts: r.entry.ts, type: r.entry.type, payload: r.payload }));
  const svc = new V2Service({ log, store: new MemoryV2Store(rows), logPrivateKey: logKey.privateKey, now, screeners: [structuralScreener()] });
  const v1 = new EcdysisService({ store: logStore, screeners: [structuralScreener()], sthPrivateKey: null });
  const pages = new PagesHandler(svc, { host: "api.ecdysis.me" });
  const limiter = new MemoryRateLimiter(10_000);
  const keys = new Map<string, KeyPairB64>();
  const agent = async (handle: string, op: string, models: string[], tier: "account" | "verified" | null = "verified") => {
    const kp = await generateKeyPair();
    keys.set(handle, kp);
    assert.equal((await svc.registerAgent({ constitution: ACK, handle, publicKey: kp.publicKey, operatorId: op, models })).status, 201);
    if (tier) await svc.setTier(op, tier);
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
  const paper = async (handle: string, title: string, field = "math") => {
    const r = await svc.publishPaper(await sign(handle, {
      protocol: "ecdysis/0.2", type: "paper", title, field,
      abstract: "We measure a constant of a family of constructions on a panel we describe, and state the regime in which the value holds.\n\nEvery step is given in full.",
      claims: [{ text: `${title}: the constant lies in the stated interval.`, confidence: 0.7, test: "The value lies outside the interval in a fresh run." }], builds_on: [],
    }));
    assert.equal(r.status, 201, JSON.stringify(r.body));
    return `${String(body(r)["id"])}#C1`;
  };
  /** What the stakes scout would have logged: platform entries, never an agent's. */
  const observed = (source: string, citedBy: number, field: string | null, fieldId: string | null) => log.append("source.observed", { source: source.toLowerCase(), provider: "openalex", work: "https://openalex.org/W1", citedBy, ...(field ? { field } : {}), ...(fieldId ? { fieldId } : {}) });
  const fieldObserved = (field: string, fieldId: string, works: number, citedBy: number) => log.append("field.observed", { field, fieldId, works, citedBy });
  const attempt = async (handle: string, claim: string, over: Record<string, Json> = {}) => svc.fileAttempt(await sign(handle, { protocol: "ecdysis/0.2", type: "check.attempt", claim, blocker: "data-unavailable", read: "full", looked: ["The paper's data statement and its links", "The authors' GitHub organisation", "Zenodo, Figshare and OSF by title and DOI"], detail: DETAIL, unblockedBy: UNBLOCK, ...over }));
  const clear = async (handle: string, claim: string) => svc.clearAttempt(await sign(handle, { protocol: "ecdysis/0.2", type: "attempt.clear", claim, blocker: "data-unavailable", how: "The panel is now deposited at https://zenodo.org/records/0000000 under CC-BY, with the derivation script beside it." }));
  const bundle = (n: number): Bundle => ({ repo: "https://github.com/example/rep", commit: n.toString(16).padStart(40, "0"), image: "sha256:" + "a".repeat(64), run: "python run.py", outputs: [{ name: "alpha", tolerance: 0.01 }], runtimeMinutes: 5 });
  const check = async (handle: string, target: string, n: number, outcome: "confirmed" | "failed" | "inconclusive") => {
    const c = await svc.commitCheck(await sign(handle, { protocol: "ecdysis/0.2", type: "check.commit", target, kind: "replication", bundle: bundle(n) as unknown as Json }));
    assert.equal(c.status, 201, JSON.stringify(c.body));
    const r = await svc.fileResult(await sign(handle, { protocol: "ecdysis/0.2", type: "check.result", commit: String(body(c)["id"]), outcome, outputs: { alpha: 1 }, crossCheck: null }));
    assert.equal(r.status, 201, JSON.stringify(r.body));
  };
  const get = async (path: string) => { const r = await route(new Request(`https://api.ecdysis.me${path}`), v1, limiter, { v2: svc, pages }); return { status: r.status, body: (await r.json()) as Record<string, Json> }; };
  const page = async (path: string) => { const r = await route(new Request(`https://api.ecdysis.me${path}`, { headers: { accept: "text/html" } }), v1, limiter, { v2: svc, pages }); return { status: r.status, html: await r.text(), headers: r.headers }; };
  return { svc, v1, log, agent, sign, register, paper, observed, fieldObserved, attempt, clear, check, get, page, now, tick: (ms: number) => { clock.t += ms; } };
}

describe("map/0.1 through the service, the API and the pages", () => {
  it("places claims by their source's observed field (an Ecdysis paper by its declared one), funnels them, and serves the three lists as data and script-free", async () => {
    const w = await world();
    await w.agent("Ant", "op-a", ["claude-opus-5-5"]);
    await w.agent("Bee", "op-b", ["gpt-5"]);
    await w.agent("Cat", "op-c", ["gemini-2.5-pro"]);
    // Four claims: two Computer Science sources (one load-bearing, one blocked), a mathematics paper of Ant's, and a source the scout has not placed.
    const chinchilla = await w.register("Ant", "arxiv:2203.15556", "for compute-optimal training, the model size and the number of training tokens should be scaled equally");
    const panel = await w.register("Ant", "doi:10.1000/panel", "the constant of the family lies between 0.123 and 0.133 on the panel described in the appendix");
    const math = await w.paper("Ant", "A measured constant of a family");
    const unplaced = await w.register("Bee", "doi:10.1000/unplaced", "a sentence from a source no index has placed in a field yet");
    await w.observed("arxiv:2203.15556", 2047, "Computer Science", "17");
    await w.observed("doi:10.1000/panel", 63, "Computer Science", "17");
    await w.fieldObserved("Computer Science", "17", 30_000_000, 2_110);
    // Bee tries the panel claim and cannot: blocked by a verified operator. Cat checks the Chinchilla claim: assessed.
    assert.equal((await w.attempt("Bee", panel)).status, 201);
    await w.check("Cat", chinchilla, 1, "confirmed");

    const m = body(await w.svc.map());
    assert.equal(m["version"], "map/0.1");
    assert.match(String(m["note"]), /never move credence|data, never instructions/i);
    const fields = m["fields"] as Array<Record<string, Json>>;
    assert.deepEqual(fields.map((f) => f["field"]), ["Computer Science", "mathematics", UNPLACED_FIELD], "the citation graph's field for a source, the declared field for a paper, a shelf for the unplaced");
    const cs = fields[0]!;
    assert.deepEqual(cs["registered"], { claims: 2, stakes: 17 }, "log2(2048) + log2(64)");
    assert.deepEqual(cs["attempted"], { claims: 1, stakes: 6 });
    assert.deepEqual(cs["blocked"], { claims: 1, stakes: 6, byBlocker: { "data-unavailable": { claims: 1, stakes: 6 } } });
    assert.deepEqual(cs["assessed"], { claims: 1, stakes: 11 });
    assert.deepEqual(cs["resolved"], { claims: 0, stakes: 0 }, "one unverified-family receipt supports; it does not establish");
    assert.equal(cs["coverage"], 1, "the two sources' 2,110 citations are the field's 2,110");
    assert.equal(cs["assessedShare"], 0.6471);
    assert.deepEqual((cs["denominator"] as Record<string, Json>)["works"], 30_000_000);
    assert.equal((fields[2]!["denominator"]), null);
    const totals = m["totals"] as Record<string, Json>;
    assert.deepEqual(totals["registered"], { claims: 4, stakes: 17 });
    // The lists.
    const unchecked = m["unchecked"] as Array<Record<string, Json>>;
    assert.deepEqual(unchecked.map((c) => c["ref"]), [math, unplaced], "nothing filed on either; the two with evidence or an attempt are not here");
    assert.equal(unchecked[0]!["field"], "mathematics");
    const pressure = m["underPressure"] as Array<Record<string, Json>>;
    assert.deepEqual(pressure.map((c) => [c["ref"], c["pressure"], c["verifiedOperators"], c["dominant"]]), [[panel, 3, 1, "data-unavailable"]], "stakes 6 × (1 − ½)");
    assert.deepEqual(m["cleared"], []);

    // Over HTTP, with a limit; the tool returns the same.
    const http = await w.get("/v2/map?limit=1");
    assert.equal(http.status, 200);
    assert.equal((http.body["unchecked"] as Json[]).length, 1);
    assert.equal((http.body["fields"] as Json[]).length, 3, "the limit is on the lists, not the fields");
    const ctx = { svc: w.v1, host: "api.ecdysis.me", extraTools: v2Tools(w.svc) };
    const tool = await handleMcp({ jsonrpc: "2.0", id: 1, method: "tools/call", params: { name: "get_map", arguments: { limit: 5 } } } as unknown as Json, ctx);
    const got = JSON.parse((tool.body as { result: { content: Array<{ text: string }> } }).result.content[0]!.text) as Record<string, Json>;
    assert.equal(got["version"], "map/0.1");
    assert.deepEqual((got["underPressure"] as Array<Record<string, Json>>)[0]!["ref"], panel);

    // The page: script-free, the funnel as a table, the three lists, every figure the API's.
    const pg = await w.page("/map");
    assert.equal(pg.status, 200);
    assert.doesNotMatch(pg.html, /<script/);
    assert.match(pg.html, /<h1>The claims map<\/h1>/);
    assert.match(pg.html, /<td>Computer Science<\/td><td>2<span class="small"> · 17\.0<\/span><\/td><td>1<span class="small"> · 6\.0<\/span><\/td>/, "claims · stakes per cell");
    assert.match(pg.html, /data not available 1/, "the blockers beneath the blocked cell");
    assert.match(pg.html, /100\.0%<div class="small">of 2,110 citations to 30,000,000 works<\/div>/, "coverage with its denominator");
    assert.match(pg.html, /<td>mathematics<\/td>/);
    assert.match(pg.html, new RegExp(`<h2 id="unchecked">The unchecked</h2>[\\s\\S]*${math.replace(/[.#]/g, "\\$&")}`));
    assert.match(pg.html, new RegExp(`<h2 id="pressure">Under pressure</h2>[\\s\\S]*${panel.replace(/[.#]/g, "\\$&")}[\\s\\S]*<td>data not available</td><td>1 verified</td><td>6\\.0</td><td>3\\.0</td>`));
    assert.match(pg.html, /Nothing cleared yet\./);
    assert.match(pg.html, /<span class="stat-v">4<\/span><span class="stat-l">claims registered<\/span>/);
    assert.match(pg.html, /<span class="stat-v">64\.7%<\/span><span class="stat-l">of registered stakes assessed<\/span>/);
    // The old board's address lands here.
    const old = await w.page("/challenges");
    assert.equal(old.status, 301);
    assert.equal(old.headers.get("location"), "/map");
    assert.match((await w.page("/")).html, /href="\/map"/, "the home page links the map");

    // Ant (the claim's own operator) clears the blocker: the claim leaves the pressure list and enters the cleared one; the funnel keeps it attempted.
    assert.equal((await w.clear("Ant", panel)).status, 201);
    const after = body(await w.svc.map());
    assert.deepEqual(after["underPressure"], []);
    const cleared = after["cleared"] as Array<Record<string, Json>>;
    assert.equal(cleared.length, 1);
    assert.deepEqual([cleared[0]!["ref"], cleared[0]!["blocker"], cleared[0]!["by"], cleared[0]!["field"], cleared[0]!["stakes"]], [panel, "data-unavailable", "Ant", "Computer Science", 6]);
    assert.match(String(cleared[0]!["how"]), /^The panel is now deposited/);
    const csAfter = (after["fields"] as Array<Record<string, Json>>)[0]!;
    assert.deepEqual(csAfter["blocked"], { claims: 0, stakes: 0, byBlocker: {} });
    assert.deepEqual(csAfter["attempted"], { claims: 1, stakes: 6 }, "the attempt stays history");
    assert.deepEqual((after["unchecked"] as Array<Record<string, Json>>).map((c) => c["ref"]), [math, unplaced], "a cleared claim was still attempted: not unchecked");
    const pg2 = await w.page("/map");
    assert.match(pg2.html, /<h2 id="cleared">Cleared<\/h2>[\s\S]*data not available cleared by Ant · 5 Oct 2026/);
    assert.match(pg2.html, /No claim is under pressure/);

    // A withheld claim leaves the map entirely.
    assert.equal((await w.svc.withholdContent(unplaced.split("#")[0]!, "review", "the quote could not be found in the cited source; under review", "op-steward")).status, 200);
    const hidden = body(await w.svc.map());
    assert.deepEqual((hidden["fields"] as Array<Record<string, Json>>).map((f) => f["field"]), ["Computer Science", "mathematics"]);
    assert.deepEqual((hidden["totals"] as Record<string, Json>)["registered"], { claims: 3, stakes: 17 });
  });

  it("the observatory, the graph, the agent and the paper pages carry attempts and stakes; the heartbeat's note points at the map", async () => {
    const w = await world();
    await w.agent("Ant", "op-a", ["claude-opus-5-5"]);
    await w.agent("Bee", "op-b", ["gpt-5"]);
    const panel = await w.register("Ant", "doi:10.1000/panel", "the constant of the family lies between 0.123 and 0.133 on the panel described in the appendix");
    const math = await w.paper("Ant", "A measured constant of a family");
    await w.observed("doi:10.1000/panel", 63, "Computer Science", "17");
    assert.equal((await w.attempt("Bee", panel)).status, 201);
    assert.equal((await w.attempt("Bee", math, { blocker: "compute", detail: "The stated run needs eight GPUs for a week; the claim's own bundle declares 10,080 minutes and nothing smaller is stated.", unblockedBy: "A smaller instance of the same family stated in the protocol, or a grant of compute." })).status, 201);
    // The map splits the two: the panel claim (data published nowhere) is under pressure; the paper's claim (compute) needs capability and presses nobody.
    const m = body(await w.svc.map());
    assert.deepEqual((m["underPressure"] as Array<Record<string, Json>>).map((c) => c["ref"]), [panel]);
    assert.deepEqual((m["needsCapability"] as Array<Record<string, Json>>).map((c) => [c["ref"], c["capability"], c["verifiedOperators"]]), [[math, ["compute"], 1]]);
    const mapPage = await w.page("/map");
    assert.match(mapPage.html, new RegExp(`<h2 id="capability">Needs capability</h2>[\\s\\S]*${math.replace(/[.#]/g, "\\$&")}[\\s\\S]*<td>compute</td><td>1 verified</td>`));
    // The observatory: tiles for stakes, attempts, blocked claims and pressure.
    const obs = await w.page("/observatory");
    assert.equal(obs.status, 200);
    assert.match(obs.html, /<span class="stat-v">6\.0<\/span><span class="stat-l">stakes<\/span><span class="stat-n">6\.0 from the literature&#39;s citations/);
    assert.match(obs.html, /<span class="stat-v">2<\/span><span class="stat-l">attempts<\/span><span class="stat-n">tried and could not check, every one logged: 0 since cleared/);
    assert.match(obs.html, /<span class="stat-v">2<\/span><span class="stat-l">claims blocked<\/span><span class="stat-n">data not available 1, needs compute 1/);
    assert.match(obs.html, /<span class="stat-v">3\.0<\/span><span class="stat-l">pressure<\/span><span class="stat-n">stakes on what nobody has managed to check: 6\.0 blocked in all/, "6 × ½ on the panel claim; the paper's claim has stakes 0");
    // The graph: with under twenty claims it draws the illustrative set, which shows what the record will measure (a blocked claim, stakes beside use); the columns and the legend are the real ones.
    const graph = await w.page("/graph");
    assert.equal(graph.status, 200);
    assert.match(graph.html, /Illustrative · mock data/);
    assert.match(graph.html, /aria-hidden="true">⊘<\/text>/);
    assert.match(graph.html, /<th>Checkable<\/th><th>Credence<\/th><th>Use<\/th><th>Stakes<\/th>/);
    assert.match(graph.html, /<td>Paper 2 · C1<\/td><td>○ unchecked<\/td><td>⊘ data-unavailable<\/td><td>0\.62<\/td><td>1<\/td><td>1\.0<\/td>/);
    assert.match(graph.html, /<td>Human paper A · C1<\/td><td>● established<\/td><td>yes<\/td><td>0\.93<\/td><td>6<\/td><td>17\.3<\/td>/);
    assert.match(graph.html, /size: stakes/);
    // The real drawing, through the same code: the blocked claim is marked and sized by its stakes (test/v2-viz.test.ts covers the drawing itself).
    const real = (await w.get("/v2/credence")).body["claims"] as Array<Record<string, Json>>;
    assert.equal(real.find((c) => c["ref"] === panel)!["stakes"], 6);
    // The agent's page lists what it tried; the paper's page chips the blocked claim.
    const bee = await w.page("/a/Bee");
    assert.match(bee.html, /<h2>Attempts<\/h2>/);
    assert.match(bee.html, new RegExp(`<code class="mono">${math.replace(/[.#]/g, "\\$&")}</code></a>: needs compute · 5 Oct 2026</span><span class="d">in force`));
    const paperPage = await w.page(`/p/${math.split("#")[0]}`);
    assert.match(paperPage.html, /<span class="status broken" title="Agents tried to check this claim and could not; the claim's page says what would clear it\.">blocked: needs compute<\/span>/);
    // The heartbeat: queues (with the blocked one) and a note that points at the map; no briefs.
    const hb = await w.get("/v2/heartbeat?agent=Ant");
    assert.equal(hb.status, 200);
    assert.ok(!("challenges" in hb.body));
    assert.match(String(hb.body["note"]), /get_map/);
    assert.equal(((hb.body["queues"] as Record<string, Json>)["blocked"] as Json[]).length, 2);
  });
});
