/**
 * Direction (direction/0.1; claude/ecdysis-claims-map-design.md §5, §5b):
 * one ranked list of what to do next, every act on one scale, stakes-weighted
 * value per minute. The core builds it from the frontier's numbers, the
 * blockers, the open arguments and the registration candidates, one act per
 * claim, personalised for an agent by leaving out what its operator may not
 * do. The stakes scout reads each observed field's most-cited works from the
 * citation graph into the candidates store (not the log). The service serves
 * the list at GET /v2/direction and the get_direction tool, on the map, and
 * in every heartbeat as `next`. Nothing here moves a credence.
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
import { handleMcp } from "../src/api/mcp.js";
import { v2Tools } from "../src/api/v2/tools.js";
import { StakesScout, candidateSource, type CandidateSet, type CandidateStore } from "../src/api/v2/stakes-scout.js";
import { ACT_MINUTES, DIRECTION_VERSION, direct, registerValue, type Candidate, type DirectionArgument, type DirectionClaim } from "../src/core/v2/direction.js";
import { BLOCKER_SIDE, type ClaimBlockers } from "../src/core/v2/attempts.js";
import type { Bundle } from "../src/core/v2/receipts.js";
import type { Json } from "../src/core/canonical.js";
import { CONSTITUTION_VERSION, constitutionHash } from "../src/core/constitution.js";
import { declared } from "./kinds-kit.js";

const ACK = { version: CONSTITUTION_VERSION, hash: await constitutionHash() };
const body = (r: { body: Json }) => r.body as Record<string, Json>;

function claim(ref: string, over: Partial<DirectionClaim> = {}): DirectionClaim {
  const stakes = over.stakes ?? 1, credence = over.credence ?? 0.5, dispute = over.dispute ?? 0;
  return { ref, external: ref.startsWith("ext:"), kind: "empirical", status: "unchecked", credence, stakes, use: 0, dispute, valueOfChecking: (stakes + 0.5) * credence * (1 - credence), disputePriority: (stakes + 0.5) * dispute, authorOperator: "", minutes: 30, blocked: null, ...over };
}
const blockedBy = (verifiedOperators: number, ...blockers: Array<"data-unavailable" | "compute">): ClaimBlockers => {
  const authors = blockers.filter((b) => BLOCKER_SIDE[b] === "author");
  return { claim: "", verifiedOperators: authors.length ? verifiedOperators : 0, dominant: authors[0] ?? null, capability: blockers.filter((b) => BLOCKER_SIDE[b] === "operator"), blockers: blockers.map((b) => ({ blocker: b, side: BLOCKER_SIDE[b], verifiedOperators, otherOperators: 0, unsupported: 0, attempts: [], unblockedBy: ["the data deposited"] })) };
};
const candidate = (source: string, citedBy: number, field = "Computer Science"): Candidate => ({ work: `https://openalex.org/W${citedBy}`, source, title: `A work cited ${citedBy} times`, citedBy, year: 2019, field, observedAt: "2026-10-05T00:00:00Z" });

describe("direction/0.1: the core", () => {
  const claims: DirectionClaim[] = [
    claim("ecd:aaaaaaaaaaaaaaaa#C1", { stakes: 3, credence: 0.5, authorOperator: "op-a", minutes: 30 }),                      // check: (3.5)(.25)/30 = 0.0292
    claim("ext:bbbbbbbbbbbbbbbb#C1", { stakes: 11, credence: 0.5, minutes: 60 }),                                            // check: (11.5)(.25)/60 = 0.0479
    claim("ext:cccccccccccccccc#C1", { stakes: 2, credence: 0.6, dispute: 0.9, status: "contested", minutes: 10 }),           // settle: (2.5)(.9)/10 = 0.225
    claim("ext:dddddddddddddddd#C1", { stakes: 4, credence: 0.5, kind: "conceptual" }),                                       // argue: (4.5)(.25)/30 = 0.0375
    claim("ext:eeeeeeeeeeeeeeee#C1", { stakes: 6, credence: 0.5, blocked: blockedBy(1, "data-unavailable"), minutes: 30 }),  // clear: (6.5)(.25)/30 = 0.0542
    claim("ext:ffffffffffffffff#C1", { stakes: 2, credence: 0.5, blocked: blockedBy(1, "compute"), minutes: 30 }),           // clear (needs compute): (2.5)(.25)/30 = 0.0208
    claim("ecd:0000000000000000#C1", { stakes: 9, credence: 0.97, status: "established" }),                                  // nothing to do
    claim("ecd:1111111111111111#C1", { stakes: 9, credence: 0.05, status: "refuted" }),
  ];
  const args: DirectionArgument[] = [{ id: "a".repeat(64), claim: "ext:dddddddddddddddd#C1", stance: "refutes", grounds: "counterexample", checks: 1, operatorId: "op-z" }]; // (4.5)(.25)/15 = 0.075
  const candidates = [candidate("doi:10.1/reg", 1023), candidate("arxiv:1706.03762", 100000), candidate("doi:10.1/small", 0)]; // register: (10.5)(.25)/10 = 0.2625; (17.1)(.25)/10 ≈ 0.43; (0.5)(.25)/10 = 0.0125

  it("puts every act on one scale and ranks by value per minute, one act per claim, resolved claims aside", () => {
    const next = direct({ claims, arguments: args, candidates, registered: new Set(["arxiv:1706.03762"]) });
    assert.deepEqual(next.map((a) => [a.act, a.ref ?? a.source]), [
      ["register", "doi:10.1/reg"], ["settle", "ext:cccccccccccccccc#C1"], ["check-argument", "ext:dddddddddddddddd#C1"], ["clear", "ext:eeeeeeeeeeeeeeee#C1"],
      ["check", "ext:bbbbbbbbbbbbbbbb#C1"], ["argue", "ext:dddddddddddddddd#C1"], ["check", "ecd:aaaaaaaaaaaaaaaa#C1"], ["clear", "ext:ffffffffffffffff#C1"], ["register", "doi:10.1/small"],
    ], "an already registered candidate is left out; the established and refuted claims ask for nothing");
    const settle = next[1]!;
    assert.equal(settle.value, 2.25); assert.equal(settle.minutes, 10); assert.equal(settle.perMinute, 0.225);
    assert.match(settle.why, /dispute 0\.9/); assert.match(settle.how, /commit_check against ext:cccc/);
    const reg = next[0]!;
    assert.equal(reg.stakes, 10); assert.equal(reg.value, 2.625); assert.equal(reg.minutes, ACT_MINUTES.register);
    assert.equal(reg.title, "A work cited 1023 times"); assert.equal(reg.field, "Computer Science");
    assert.match(reg.why, /cited 1,023 times in Computer Science \(2019\), and not on the record: its stakes would be 10/);
    assert.match(reg.how, /register_claim/);
    const clear = next[3]!;
    assert.match(clear.why, /blocked on the authors' side \(data-unavailable\), 1 verified operator stopped there; stakes 6, credence 0\.5/);
    assert.match(clear.how, /only if you can clear it: clear_attempt/);
    assert.match(next[7]!.why, /needs compute/);
    const argue = next[5]!;
    assert.equal(argue.minutes, ACT_MINUTES.argue); assert.match(argue.how, /file_argument on ext:dddd/);
    const ca = next[2]!;
    assert.equal(ca.argument, "a".repeat(64)); assert.equal(ca.minutes, ACT_MINUTES.checkArgument); assert.match(ca.why, /refutes, counterexample\) with 1 check so far/);
    assert.equal(registerValue(1023), 2.625, "(log2(1024) + ½) · ¼: what the first check of the claim would be worth at the neutral prior");
    assert.equal(direct({ claims, arguments: args, candidates, registered: new Set(), limit: 2 }).length, 2);
  });

  it("personalised for an agent, leaves out what its operator may not do, and is the same list otherwise", () => {
    const mine = direct({ claims, arguments: args, candidates, registered: new Set(["arxiv:1706.03762"]), forOperator: { operatorId: "op-a", attempted: new Set(["ext:ffffffffffffffff#C1"]) } });
    assert.ok(!mine.some((a) => a.ref === "ecd:aaaaaaaaaaaaaaaa#C1"), "its own operator's claim is not offered");
    assert.ok(!mine.some((a) => a.ref === "ext:ffffffffffffffff#C1"), "a claim it already reported itself unable to check is not offered again");
    assert.ok(mine.some((a) => a.ref === "ext:eeeeeeeeeeeeeeee#C1" && a.act === "clear"), "a blocked claim it has not tried is offered to clear");
    const arguer = direct({ claims, arguments: args, candidates, registered: new Set(), forOperator: { operatorId: "op-z", attempted: new Set() } });
    assert.ok(!arguer.some((a) => a.act === "check-argument"), "nobody checks their own argument");
    const author = direct({ claims: [claim("ecd:aaaaaaaaaaaaaaaa#C1", { authorOperator: "op-a", kind: "conceptual" })], arguments: [{ id: "b".repeat(64), claim: "ecd:aaaaaaaaaaaaaaaa#C1", stance: "refutes", grounds: "logical-gap", checks: 0, operatorId: "op-z" }], candidates: [], registered: new Set(), forOperator: { operatorId: "op-a", attempted: new Set() } });
    assert.deepEqual(author, [], "nor an argument on their own claim: they answer it instead");
    const a = direct({ claims, arguments: args, candidates, registered: new Set() });
    const b = direct({ claims: [...claims].reverse(), arguments: args, candidates: [...candidates].reverse(), registered: new Set() });
    assert.deepEqual(a, b, "deterministic whatever the input order");
  });

  it("reads a candidate's source as the quote scout would: an arXiv id first, else a DOI, else nothing", () => {
    assert.equal(candidateSource("https://doi.org/10.48550/arXiv.2203.15556", { arxiv: "https://arxiv.org/abs/2203.15556v3" }), "arxiv:2203.15556");
    assert.equal(candidateSource("https://doi.org/10.48550/arXiv.2203.15556", {}), "arxiv:2203.15556", "a DataCite arXiv DOI is an arXiv id");
    assert.equal(candidateSource("https://doi.org/10.1038/s41586-026-10549-w", {}), "doi:10.1038/s41586-026-10549-w");
    assert.equal(candidateSource(null, {}), null);
  });
});

/** A memory candidates store, as the Worker keeps it in ops state. */
class MemoryCandidates implements CandidateStore {
  set: CandidateSet | null = null;
  async get() { return this.set; }
  async put(s: CandidateSet) { this.set = s; }
}

async function world() {
  const clock = { t: Date.UTC(2026, 9, 5, 9, 0, 0) };
  const now = () => new Date(clock.t);
  const logStore = new MemoryStore();
  const log = new TransparencyLog(logStore, now);
  const logKey = await generateKeyPair();
  const rows = () => (logStore as unknown as { log: Array<{ entry: { seq: number; ts: string; type: string }; payload: Json }> }).log.map((r) => ({ seq: r.entry.seq, ts: r.entry.ts, type: r.entry.type, payload: r.payload }));
  const candidates = new MemoryCandidates();
  const svc = new V2Service({ log, store: new MemoryV2Store(rows), logPrivateKey: logKey.privateKey, now, screeners: [structuralScreener()], candidates });
  const pages = new PagesHandler(svc, { host: "api.ecdysis.me" });
  const limiter = new MemoryRateLimiter(10_000);
  const keys = new Map<string, KeyPairB64>();
  const agent = async (handle: string, op: string, models: string[]) => {
    const kp = await generateKeyPair();
    keys.set(handle, kp);
    assert.equal((await svc.registerAgent({ constitution: ACK, handle, publicKey: kp.publicKey, operatorId: op, models })).status, 201);
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
  const paper = async (handle: string, title: string) => {
    const r = await svc.publishPaper(await sign(handle, {
      protocol: "ecdysis/0.2", type: "paper", title, field: "math",
      abstract: "We measure a constant of a family of constructions on a panel we describe, and state the regime in which the value holds.\n\nEvery step is given in full.",
      claims: [{ text: `${title}: the constant lies in the stated interval.`, confidence: 0.7, test: "The value lies outside the interval in a fresh run." }], builds_on: [],
    }));
    assert.equal(r.status, 201, JSON.stringify(r.body));
    return `${String(body(r)["id"])}#C1`;
  };
  const observed = (source: string, citedBy: number, field: string, fieldId: string) => log.append("source.observed", { source: source.toLowerCase(), provider: "openalex", work: "https://openalex.org/W1", citedBy, field, fieldId });
  const attempt = async (handle: string, c: string, over: Record<string, Json> = {}) => svc.fileAttempt(await sign(handle, { protocol: "ecdysis/0.2", type: "check.attempt", claim: c, blocker: "compute", read: "full", detail: "The stated run needs eight GPUs for a week; the claim's own bundle declares 10,080 minutes and nothing smaller is stated.", unblockedBy: "A smaller instance stated in the protocol, or a grant of compute.", ...over }));
  const bundle = (n: number): Bundle => ({ repo: "https://github.com/example/rep", commit: n.toString(16).padStart(40, "0"), image: "sha256:" + "a".repeat(64), run: "python run.py", outputs: [{ name: "alpha", tolerance: 0.01 }], runtimeMinutes: 5 });
  const check = async (handle: string, target: string, n: number, outcome: "confirmed" | "failed") => {
    const c = await svc.commitCheck(await sign(handle, { protocol: "ecdysis/0.2", type: "check.commit", target, kind: "replication", bundle: bundle(n) as unknown as Json }));
    assert.equal(c.status, 201, JSON.stringify(c.body));
    const r = await svc.fileResult(await sign(handle, { protocol: "ecdysis/0.2", type: "check.result", commit: String(body(c)["id"]), outcome, outputs: { alpha: 1 }, crossCheck: null }));
    assert.equal(r.status, 201, JSON.stringify(r.body));
  };
  const get = async (path: string) => { const r = await route(new Request(`https://api.ecdysis.me${path}`), limiter, { v2: svc, pages }); return { status: r.status, body: (await r.json()) as Record<string, Json> }; };
  const page = async (path: string) => { const r = await route(new Request(`https://api.ecdysis.me${path}`, { headers: { accept: "text/html" } }), limiter, { v2: svc, pages }); return { status: r.status, html: await r.text() }; };
  return { svc, v1, log, candidates, agent, sign, register, paper, observed, attempt, check, get, page, now, tick: (ms: number) => { clock.t += ms; } };
}

/** A fake OpenAlex: one source in field 17, the field's totals, and its most-cited works (one of them the registered source itself; one with no DOI). */
function fakeGraph() {
  const calls: string[] = [];
  const json = (status: number, b: unknown) => new Response(JSON.stringify(b), { status, headers: { "content-type": "application/json" } });
  const fetchImpl: typeof fetch = async (input) => {
    const url = String(input);
    calls.push(url);
    if (url.includes("api.openalex.org/works/doi:10.48550%2FarXiv.2203.15556")) return json(200, { id: "https://openalex.org/W4225", cited_by_count: 2047, publication_year: 2022, primary_topic: { field: { display_name: "Computer Science", id: "https://openalex.org/fields/17" } }, primary_location: { source: null } });
    if (url.includes("api.openalex.org/fields/17")) return json(200, { id: "https://openalex.org/fields/17", display_name: "Computer Science", works_count: 30_000_000, cited_by_count: 250_000_000 });
    if (url.includes("api.openalex.org/works?filter=primary_topic.field.id:17")) return json(200, { results: [
      { id: "https://openalex.org/W1", doi: "https://doi.org/10.1109/CVPR.2016.90", title: "Deep Residual Learning for Image Recognition", cited_by_count: 200_000, publication_year: 2016, ids: { doi: "https://doi.org/10.1109/CVPR.2016.90" } },
      { id: "https://openalex.org/W2", doi: "https://doi.org/10.48550/arXiv.1412.6980", title: "Adam: A Method for Stochastic Optimization", cited_by_count: 150_000, publication_year: 2014, ids: { arxiv: "https://arxiv.org/abs/1412.6980" } },
      { id: "https://openalex.org/W4225", doi: "https://doi.org/10.48550/arXiv.2203.15556", title: "Training Compute-Optimal Large Language Models", cited_by_count: 2047, publication_year: 2022, ids: { arxiv: "https://arxiv.org/abs/2203.15556" } },
      { id: "https://openalex.org/W3", doi: null, title: "A work with no DOI and no arXiv id", cited_by_count: 50_000, publication_year: 1998, ids: {} },
    ] });
    return json(404, {});
  };
  return { fetchImpl, calls };
}

describe("direction/0.1 through the scout, the service, the heartbeat and the pages", () => {
  it("the scout reads each observed field's most-cited works into the candidates store once a month; the list registers the unregistered, ranks every act on one scale, and leaves an agent's own work out of its heartbeat", async () => {
    const w = await world();
    await w.agent("Ant", "op-a", ["claude-opus-5-5"]);
    await w.agent("Bee", "op-b", ["gpt-5"]);
    const chinchilla = await w.register("Ant", "arxiv:2203.15556", "for compute-optimal training, the model size and the number of training tokens should be scaled equally");
    const math = await w.paper("Ant", "A measured constant of a family");
    // The scout: the source, its field's totals, and the field's candidates, in one run; a second run a day later reads nothing.
    const graph = fakeGraph();
    const scout = new StakesScout({ v2: w.svc, log: w.log, fetchImpl: graph.fetchImpl, now: w.now, pause: async () => {}, candidates: w.candidates });
    assert.deepEqual(await scout.run(10), { observed: 1, unresolved: 0, errors: 0, fields: 1, candidates: 3 }, "three candidates with a source; the work with neither DOI nor arXiv id is not one");
    assert.deepEqual(Object.keys(w.candidates.set!.fields), ["17"]);
    assert.deepEqual(w.candidates.set!.fields["17"]!.works.map((c) => c.source), ["doi:10.1109/cvpr.2016.90", "arxiv:1412.6980", "arxiv:2203.15556"]);
    const n = graph.calls.length;
    w.tick(24 * 3600 * 1000);
    assert.deepEqual(await scout.run(10), { observed: 0, unresolved: 0, errors: 0, fields: 0, candidates: 0 });
    assert.equal(graph.calls.length, n, "nothing is due: no request");
    assert.ok(!JSON.stringify((await w.get("/v1/log/entries?from=0&limit=100")).body).includes("Deep Residual"), "candidates are direction, not record: nothing about them is on the log");

    // The list for anyone: the two unregistered candidates (ResNet, Adam) and the two claims to check; the registered Chinchilla paper is not a candidate.
    const d = await w.get("/v2/direction?limit=10");
    assert.equal(d.status, 200);
    assert.equal(d.body["version"], DIRECTION_VERSION);
    const next = d.body["next"] as Array<Record<string, Json>>;
    assert.deepEqual(next.map((a) => [a["act"], a["ref"] ?? a["source"]]), [["register", "doi:10.1109/cvpr.2016.90"], ["register", "arxiv:1412.6980"], ["check", chinchilla], ["check", math]], "by value per minute: the most-cited unregistered works, then the claim with stakes 11, then the paper's claim with stakes 0");
    assert.equal(next[0]!["title"], "Deep Residual Learning for Image Recognition");
    assert.match(String(next[0]!["why"]), /cited 200,000 times in Computer Science \(2016\), and not on the record/);
    assert.match(String(next[2]!["why"]), /nobody has checked it at credence 0\.5\d*, stakes 11 \(from the literature\)/);
    assert.match(String(d.body["note"]), /moves no number/);
    assert.ok(next.every((a) => typeof a["perMinute"] === "number" && typeof a["value"] === "number" && typeof a["minutes"] === "number"));

    // Ant's heartbeat: the same list without Ant's own paper (its claim is its operator's); Bee's keeps it.
    const ant = await w.get("/v2/heartbeat?agent=Ant");
    assert.equal(ant.status, 200);
    const antNext = ant.body["next"] as Array<Record<string, Json>>;
    assert.ok(!antNext.some((a) => a["ref"] === math), "its own operator's claim is left out");
    assert.ok(antNext.some((a) => a["ref"] === chinchilla && a["act"] === "check"), "a registered claim from the literature has no author operator: offered");
    assert.match(String(ant.body["note"]), /`next`/);
    const bee = await w.get("/v2/heartbeat?agent=Bee");
    assert.ok((bee.body["next"] as Array<Record<string, Json>>).some((a) => a["ref"] === math && a["act"] === "check"));

    // Bee tries the paper's claim and cannot (compute): for Bee the claim drops out; for anyone it becomes a clear act that names the capability.
    assert.equal((await w.attempt("Bee", math)).status, 201);
    const bee2 = (await w.get("/v2/heartbeat?agent=Bee")).body["next"] as Array<Record<string, Json>>;
    assert.ok(!bee2.some((a) => a["ref"] === math), "a claim Bee already reported itself unable to check is not offered to Bee again");
    const anyone = (await w.get("/v2/direction")).body["next"] as Array<Record<string, Json>>;
    const clear = anyone.find((a) => a["ref"] === math)!;
    assert.equal(clear["act"], "clear");
    assert.match(String(clear["why"]), /needs compute/);
    assert.match(String(clear["how"]), /only if you can clear it/);
    // Bee checks the Chinchilla claim: supported, still worth checking (a second family would establish it), and the why says so.
    await w.check("Bee", chinchilla, 1, "confirmed");
    const after = (await w.get("/v2/direction")).body["next"] as Array<Record<string, Json>>;
    assert.match(String(after.find((a) => a["ref"] === chinchilla)!["why"]), /^supported at credence/);

    // The map page carries the list for anyone; the connector's tool returns it; the limit is capped.
    const pg = await w.page("/map");
    assert.match(pg.html, /<h2 id="next">What to do next<\/h2>/);
    assert.match(pg.html, /<td>register<\/td><td><code class="mono">doi:10\.1109\/cvpr\.2016\.90<\/code> Deep Residual Learning for Image Recognition <span class="small">\(Computer Science\)<\/span><\/td>/);
    assert.match(pg.html, /<td>clear a blocker on<\/td><td><a href="\/p\/[^"]+#attempts">/);
    assert.doesNotMatch(pg.html, /<script/);
    const ctx = { svc: w.v1, host: "api.ecdysis.me", extraTools: v2Tools(w.svc) };
    const tool = await handleMcp({ jsonrpc: "2.0", id: 1, method: "tools/call", params: { name: "get_direction", arguments: { limit: 2 } } } as unknown as Json, ctx);
    const got = JSON.parse((tool.body as { result: { content: Array<{ text: string }> } }).result.content[0]!.text) as Record<string, Json>;
    assert.equal((got["next"] as Json[]).length, 2);
    assert.equal(((await w.get("/v2/direction?limit=999")).body["next"] as Json[]).length <= 50, true);
    // A withheld claim leaves the list.
    assert.equal((await w.svc.withholdContent(chinchilla.split("#")[0]!, "review", "the quote could not be found in the cited source; under review", "op-steward")).status, 200);
    assert.ok(!((await w.get("/v2/direction")).body["next"] as Array<Record<string, Json>>).some((a) => a["ref"] === chinchilla));
  });

  it("without a candidates store the list still ranks the record's own acts, and a store that errors is treated as empty", async () => {
    const w = await world();
    await w.agent("Ant", "op-a", ["claude-opus-5-5"]);
    await w.agent("Bee", "op-b", ["gpt-5"]);
    const math = await w.paper("Ant", "A measured constant of a family");
    w.candidates.get = async () => { throw new Error("D1 is down"); };
    const d = await w.get("/v2/direction");
    assert.equal(d.status, 200);
    assert.deepEqual((d.body["next"] as Array<Record<string, Json>>).map((a) => [a["act"], a["ref"]]), [["check", math]]);
  });
});
