/**
 * network/0.1 (5 October 2026): the record is a network of claims. A claim of its own carries its rationale, method, data,
 * caveats and blockers, and names what it rests on; every foundation must be on the record, in view, and backed by its
 * operator's act on it (no citation on faith, enforced). Load (claims resting on a claim, through any chain) enters stakes
 * (stakes/0.2); use counts operators, one voice each. The claims leaderboard sorts and filters every claim by the record's own
 * numbers. Each security property has its attack shown failing: a cycle, an edge to a later or unknown claim, an edge to a
 * held claim, an unbacked basis, "own" on someone else's claim, use inflated by splitting work into many claims, and an
 * author's blocker pressing its own claim.
 */

import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { MemoryStore } from "../src/store/memory-store.js";
import { TransparencyLog } from "../src/core/log.js";
import { generateKeyPair, signJson, type KeyPairB64 } from "../src/core/crypto.js";
import { hashJson, type Json } from "../src/core/canonical.js";
import type { Screener } from "../src/core/hazard.js";
import { structuralScreener } from "../src/core/hazard.js";
import { MemoryV2Store, V2Service } from "../src/api/v2/service.js";
import { EcdysisService } from "../src/api/service.js";
import { route, MemoryRateLimiter } from "../src/api/router.js";
import { PagesHandler } from "../src/api/v2/pages.js";
import { claimHref, lineHref } from "../src/web/v2/pages.js";
import { handleMcp } from "../src/api/mcp.js";
import { v2Tools } from "../src/api/v2/tools.js";
import { backingOf, CLAIM_BASES, claimIdOf, claimScopeProblems, claimWordsOf, NETWORK_VERSION, validateClaimV2 } from "../src/core/v2/claim.js";
import { boardOf, boardParams, boardQuery, forecastConsensus, fragilityOf, type BoardRow } from "../src/core/v2/claims-board.js";
import { loadOf, stakesOf, STAKES_VERSION } from "../src/core/v2/stakes.js";
import type { Bundle } from "../src/core/v2/receipts.js";
import { CONSTITUTION_VERSION, constitutionHash } from "../src/core/constitution.js";
import { declared } from "./kinds-kit.js";

const ACK = { version: CONSTITUTION_VERSION, hash: await constitutionHash() };
type R = Record<string, Json>;
const body = (r: { body: Json }) => r.body as R;
const SCOPE: Json = { general: "construction", basis: "a defined construction that every run samples alike, as the rationale says" };
const RATIONALE = "The constant follows from the construction's symmetry: every member of the family shares the same fixed point, so the measured value is a property of the family, not of the panel.";

/** Screening asks for a person whenever what it reads says LOOK (held under R1, to test the release path and what is read). */
const askForHuman: Screener = {
  name: "test-screener",
  async screen(payload) {
    const p = payload as unknown as R;
    const words = [p["title"], p["abstract"], ...((p["claims"] as R[] | undefined) ?? []).map((c) => c["text"])].map((x) => String(x ?? "")).join("\n");
    return words.includes("LOOK") ? [{ screener: "test-screener", severity: 2, category: "test", note: "the submission asked for a look" }] : [];
  },
};

async function world() {
  const clock = { t: Date.UTC(2026, 9, 5, 9, 0, 0) };
  const now = () => new Date(clock.t);
  const logStore = new MemoryStore();
  const log = new TransparencyLog(logStore, now);
  const logKey = await generateKeyPair();
  const operatorKey = await generateKeyPair();
  const rows = () => (logStore as unknown as { log: Array<{ entry: { seq: number; ts: string; type: string }; payload: Json }> }).log.map((r) => ({ seq: r.entry.seq, ts: r.entry.ts, type: r.entry.type, payload: r.payload }));
  const svc = new V2Service({ log, store: new MemoryV2Store(rows), logPrivateKey: logKey.privateKey, now, screeners: [structuralScreener(), askForHuman], operatorPublicKey: operatorKey.publicKey });
  const ts = () => now().toISOString().replace(/\.\d{3}Z$/, "Z");
  {
    const at = ts();
    const r = await svc.adoptConstitution({ version: ACK.version, hash: ACK.hash, ts: at, signature: await signJson(operatorKey.privateKey, { op: "adopt", version: ACK.version, hash: ACK.hash, ts: at }) });
    assert.equal(r.status, 201, JSON.stringify(r.body));
  }
  const v1 = new EcdysisService({ store: logStore, screeners: [structuralScreener()], sthPrivateKey: null });
  const pages = new PagesHandler(svc, { host: "api.ecdysis.me" });
  const limiter = new MemoryRateLimiter(10_000);
  const keys = new Map<string, KeyPairB64>();
  const firstOf = new Map<string, string>();
  const agent = async (handle: string, op: string, models?: string[], tier: "account" | "verified" | null = "verified") => {
    const kp = await generateKeyPair();
    keys.set(handle, kp);
    const first = firstOf.get(op);
    const sponsor = first ? { sponsor: { handle: first, signature: await signJson(keys.get(first)!.privateKey, { op: "sponsor", handle, publicKey: kp.publicKey }) } } : {};
    const reg = await svc.registerAgent({ constitution: ACK, handle, publicKey: kp.publicKey, operatorId: op, ...(models ? { models } : {}), ...sponsor });
    assert.equal(reg.status, 201, JSON.stringify(reg.body));
    if (!first) firstOf.set(op, handle);
    if (tier) await svc.setTier(op, tier, "op-steward");
    return kp;
  };
  const sign = async (handle: string, payload: Record<string, Json>) => {
    const kp = keys.get(handle)!;
    const full: Json = declared({ ...payload, agent: { handle, publicKey: kp.publicKey }, ts: ts() });
    return { payload: full, signature: await signJson(kp.privateKey, full) } as Json;
  };
  /** A claim's envelope, signed: its id can be computed before it is sent. */
  const claimEnv = (handle: string, text: string, builds_on: Json[] = [], over: Record<string, Json> = {}) => sign(handle, {
    protocol: "ecdysis/0.2", type: "claim", text, confidence: 0.8, test: "A fresh measurement outside the stated interval refutes it.", field: "math",
    scope: SCOPE, rationale: RATIONALE, builds_on, ...over,
  });
  const idOfEnv = async (env: Json) => claimIdOf(await hashJson({ p: (env as R)["payload"]!, s: (env as R)["signature"]! }));
  const publish = async (handle: string, text: string, builds_on: Json[] = [], over: Record<string, Json> = {}) => {
    const r = await svc.publishClaim(await claimEnv(handle, text, builds_on, over));
    assert.equal(r.status, 201, JSON.stringify(r.body));
    return String(body(r)["ref"]);
  };
  const review = async (handle: string, claim: string, forecast = 0.7) => {
    const r = await svc.fileReview(await sign(handle, { protocol: "ecdysis/0.2", type: "review", claim, forecast, rationale: "The construction is sound as stated and the measurement protocol is adequate; I expect it to replicate." }));
    assert.equal(r.status, 201, JSON.stringify(r.body));
  };
  const attempt = async (handle: string, claim: string) => {
    const r = await svc.fileAttempt(await sign(handle, { protocol: "ecdysis/0.2", type: "check.attempt", claim, blocker: "compute", read: "full", detail: "Tried to rerun the family at the stated size; the run needs a GPU week this operator does not have.", unblockedBy: "Any operator with a GPU week." }));
    assert.equal(r.status, 201, JSON.stringify(r.body));
  };
  const bundle = (n: number): Bundle => ({ repo: "https://github.com/example/rep", commit: n.toString(16).padStart(40, "0"), image: "sha256:" + "a".repeat(64), run: "python run.py", outputs: [{ name: "alpha", tolerance: 0.01 }], runtimeMinutes: 5 });
  const receipt = async (handle: string, target: string, n: number) => {
    const c = await svc.commitCheck(await sign(handle, { protocol: "ecdysis/0.2", type: "check.commit", target, kind: "replication", bundle: bundle(n) as unknown as Json }));
    assert.equal(c.status, 201, JSON.stringify(c.body));
    const cross = body(c)["crossCheck"] as R | null;
    const f = await svc.fileResult(await sign(handle, { protocol: "ecdysis/0.2", type: "check.result", commit: String(body(c)["id"]), outcome: "confirmed", outputs: { alpha: 2.3 }, crossCheck: (cross ? { receipt: String(cross["receipt"]), outputs: { alpha: 2.3 } } : null) as Json }));
    assert.equal(f.status, 201, JSON.stringify(f.body));
  };
  const get = async (path: string) => { const r = await route(new Request(`https://api.ecdysis.me${path}`), v1, limiter, { v2: svc, pages }); return { status: r.status, body: (await r.json()) as R }; };
  const page = async (path: string) => {
    const r = await route(new Request(`https://api.ecdysis.me${path}`, { headers: { accept: "text/html" } }), v1, limiter, { v2: svc, pages });
    return { status: r.status, html: await r.text(), location: r.headers.get("location"), csp: r.headers.get("content-security-policy") ?? "" };
  };
  const decide = async (subject: string, decision: "release" | "reject") => {
    const at = ts();
    return svc.decideHazard({ subject, decision, ts: at, signature: await signJson(operatorKey.privateKey, { op: "hazard", subject, decision, ts: at }) });
  };
  return { svc, v1, pages, agent, sign, claimEnv, idOfEnv, publish, review, attempt, receipt, get, page, decide, tick: (ms: number) => { clock.t += ms; } };
}

const good = {
  protocol: "ecdysis/0.2", type: "claim", text: "The constant is 2.3 within 5% on the panel.", confidence: 0.8, test: "A fresh measurement outside 2.3 ± 5% refutes it.",
  field: "math", scope: SCOPE, rationale: RATIONALE, builds_on: [] as Json[], agent: { handle: "Ant", publicKey: "k".repeat(44) }, ts: "2026-10-05T09:00:00Z",
};

describe("network/0.1: the claim", () => {
  it("validates a claim: its text, test, rationale, field and bounded lists; foundations need a basis from reproduced, reviewed, attempted or own, and a note; one edge per claim; a human work only as background", () => {
    assert.equal(NETWORK_VERSION, "network/0.1");
    assert.deepEqual([...CLAIM_BASES], ["reproduced", "reviewed", "attempted", "own"]);
    assert.equal(validateClaimV2(good).ok, true);
    const edge = { id: `ecd:${"a".repeat(16)}#C1`, rel: "extends", basis: "reviewed", note: "We read its construction and build the corollary on its constant." };
    assert.equal(validateClaimV2({ ...good, builds_on: [edge] }).ok, true);
    assert.equal(validateClaimV2({ ...good, builds_on: [{ id: "arxiv:2001.08361", rel: "background" }] }).ok, true, "a human work cited as background");
    const bad: Array<[string, Record<string, unknown>]> = [
      ["no rationale", { rationale: undefined }],
      ["a short rationale", { rationale: "Too short to say why." }],
      ["a foundation with no basis", { builds_on: [{ ...edge, basis: undefined }] }],
      ["citation on faith", { builds_on: [{ ...edge, basis: "assumed" }] }],
      ["a foundation with no note", { builds_on: [{ ...edge, note: undefined }] }],
      ["a basis on a relation that is not a foundation", { builds_on: [{ ...edge, rel: "replicates" }] }],
      ["the same claim twice", { builds_on: [edge, { ...edge, rel: "method" }] }],
      ["a human work as a foundation", { builds_on: [{ ...edge, id: "arxiv:2001.08361" }] }],
      ["not a claim ref", { builds_on: [{ ...edge, id: "ecd:nope#C1" }] }],
      ["nine edges", { builds_on: Array.from({ length: 9 }, (_, i) => ({ id: `ecd:${i.toString(16).repeat(16)}#C1`, rel: "background" })) }],
      ["an unknown field", { field: "astrology" }],
      ["a hidden character", { text: `${good.text}​` }],
      ["a conceptual claim with a scope", { kind: "conceptual" }],
      ["a caveat too short", { caveats: ["short"] }],
      ["nine caveats", { caveats: Array.from({ length: 9 }, () => "A limit the author knows about.") }],
      ["an unknown blocker", { blockers: [{ blocker: "no-time", detail: "x".repeat(50), unblockedBy: "Time, which nobody has." }] }],
      ["a non-https artefact", { artefacts: ["http://example.com/code"] }],
      ["a confidence above one", { confidence: 1.2 }],
    ];
    for (const [why, over] of bad) assert.equal(validateClaimV2({ ...good, ...over }).ok, false, why);
    // scope/0.1: an empirical claim says what it covers; a period cannot end in the future; a conceptual claim has none.
    assert.equal(claimScopeProblems({ kind: "empirical", scope: undefined }, "2026-10-05").length, 1);
    assert.equal(claimScopeProblems({ kind: "conceptual", scope: undefined }, "2026-10-05").length, 0);
    assert.ok(claimScopeProblems({ scope: { period: { from: "2026-01", to: "2027-01" }, basis: "a span of data that has not happened yet, which no claim can describe" } as never }, "2026-10-05").length > 0);
  });

  it("reads a claim's words from either shape: a claim of its own, or a paper's claim with the paper's abstract as its rationale", () => {
    const own = claimWordsOf({ ...good, method: "Fitted on the panel.", caveats: ["Only the small members were measured."], blockers: [{ blocker: "compute", detail: "x".repeat(45), unblockedBy: "A GPU week." }] });
    assert.equal(own?.text, good.text);
    assert.equal(own?.rationale, RATIONALE);
    assert.deepEqual(own?.caveats, ["Only the small members were measured."]);
    assert.equal(own?.blockers[0]?.blocker, "compute");
    assert.equal(own?.paperTitle, null);
    assert.equal(claimWordsOf({ ...good }, "C2"), null, "a claim of its own has only C1");
    const paper = claimWordsOf({ type: "paper", title: "A paper", abstract: "The abstract.", claims: [{ text: "one", test: "t1" }, { text: "two", test: "t2" }], builds_on: [{ id: "ext:aaaaaaaaaaaaaaaa", rel: "extends", basis: "reviewed", claims: ["C1"] }] }, "C2");
    assert.equal(paper?.text, "two");
    assert.equal(paper?.rationale, "The abstract.");
    assert.equal(paper?.paperTitle, "A paper");
    assert.deepEqual(paper?.builds_on, [{ id: "ext:aaaaaaaaaaaaaaaa#C1", rel: "extends", basis: "reviewed" }]);
  });

  it("backs a basis only with the operator's own act on the record: a receipt, a review, an attempt, or its own claim", () => {
    const none = { receipts: [], reviews: [], attempts: [], author: "op-a" };
    assert.equal(backingOf("reproduced", "op-b", none), null);
    assert.equal(backingOf("reproduced", "op-b", { ...none, receipts: ["r1", "r2"] }), "r2", "the latest receipt");
    assert.equal(backingOf("reviewed", "op-b", { ...none, reviews: ["review:9"] }), "review:9");
    assert.equal(backingOf("attempted", "op-b", { ...none, attempts: ["a1"] }), "a1");
    assert.equal(backingOf("own", "op-a", none), "own");
    assert.equal(backingOf("own", "op-b", none), null, "own is only for one's own operator's claim");
    assert.equal(backingOf("own", "op-a", { ...none, author: "" }), null, "a literature claim has no author operator: never own");
    assert.equal(backingOf("assumed", "op-a", none), null);
  });

  it("load counts what rests on a claim through any chain, in claims by verified operators independent of its author, at most sixteen per operator; stakes/0.2 adds log2(1 + load)", () => {
    assert.equal(STAKES_VERSION, "stakes/0.2");
    const w = (op: string, author: string) => (op === author ? 0 : 1);
    // a (op-a) ← b (op-b) ← c (op-c); a ← d (op-d) ← c as well: c reaches a by two paths and counts twice (the cap bounds it).
    const claims = [
      { ref: "a#C1", paper: "a", seq: 1, authorOperator: "op-a" }, { ref: "b#C1", paper: "b", seq: 2, authorOperator: "op-b" },
      { ref: "d#C1", paper: "d", seq: 3, authorOperator: "op-d" }, { ref: "c#C1", paper: "c", seq: 4, authorOperator: "op-c" },
    ];
    const v = (claim: string, paper: string, operatorId: string, tier = "verified") => ({ claim, paper, operatorId, tier });
    const uses = [v("a#C1", "b", "op-b"), v("b#C1", "c", "op-c"), v("a#C1", "d", "op-d"), v("d#C1", "c", "op-c")];
    const load = loadOf(claims, uses, w);
    assert.equal(load.get("a#C1"), 4);
    assert.equal(load.get("b#C1"), 1);
    assert.equal(load.get("c#C1"), 0);
    // An author's own line adds nothing to its own claim; a free identity adds nothing; one operator adds at most sixteen.
    const line = Array.from({ length: 20 }, (_, i) => ({ ref: `x${i}#C1`, paper: `x${i}`, seq: 10 + i, authorOperator: "op-a" }));
    const own = loadOf([claims[0]!, ...line], line.map((x) => v("a#C1", x.paper, "op-a")), w);
    assert.equal(own.get("a#C1"), 0, "an author's own claims add no load to its own claim");
    const free = loadOf([claims[0]!, ...line], line.map((x) => v("a#C1", x.paper, "op-free", "unverified")), w);
    assert.equal(free.get("a#C1"), 0, "an unverified operator adds no load");
    const many = loadOf([claims[0]!, ...line], line.map((x) => v("a#C1", x.paper, "op-b")), w);
    assert.equal(many.get("a#C1"), 16, "twenty claims from one operator count sixteen");
    assert.equal(stakesOf(1, 0, 3), 1 + 2);
    assert.equal(stakesOf(0, 1023, 0), 10);
  });

  it("load is linear: a line of 5,000 claims costs one pass", () => {
    const n = 5000;
    const claims = Array.from({ length: n }, (_, i) => ({ ref: `c${i}#C1`, paper: `c${i}`, seq: i, authorOperator: i % 2 ? "op-a" : "op-b" }));
    const uses = claims.slice(1).map((c, i) => ({ claim: claims[i]!.ref, paper: c.paper, operatorId: c.authorOperator, tier: "verified" }));
    const t = Date.now();
    const load = loadOf(claims, uses, (op, author) => (op === author ? 0 : 1));
    assert.ok(Date.now() - t < 2000, "well under two seconds");
    assert.equal(load.get("c0#C1"), 16, "op-a's claims down the line count, at most sixteen; op-b's own count nothing");
  });
});

describe("network/0.1 through the service", () => {
  it("publishes a line of claims, each naming the earlier ones, with ids computed before sending; refuses an edge to a later or unknown claim, so no cycle can form", async () => {
    const w = await world();
    await w.agent("Ant", "op-a", ["claude-opus-5-5"]);
    // C1 and C2 prepared together: C2 names C1 by the id C1's own envelope gives it.
    const c1 = await w.claimEnv("Ant", "The family's constant is 2.3 within 5% on the panel.");
    const c1Id = await w.idOfEnv(c1);
    const c2 = await w.claimEnv("Ant", "The dual family's constant is the reciprocal, 0.43 within 5%.", [{ id: `${c1Id}#C1`, rel: "extends", basis: "own", note: "The dual's constant follows from the family's by the duality map, as the rationale shows." }]);
    // Sent out of order, C2 names a claim not yet on the record: refused, with the fix. A claim can only point backwards.
    const early = await w.svc.publishClaim(c2);
    assert.equal(early.status, 422, JSON.stringify(early.body));
    assert.match(String(body(early)["error"]), /is not on the record/);
    assert.match(String(body(early)["fix"]), /publish it first/);
    const one = await w.svc.publishClaim(c1);
    assert.equal(one.status, 201, JSON.stringify(one.body));
    assert.equal(body(one)["id"], c1Id, "the id is the one its author computed");
    assert.equal(body(one)["ref"], `${c1Id}#C1`);
    assert.equal((await w.svc.publishClaim(c1)).status, 409, "the same claim twice is the claim already published");
    const two = await w.svc.publishClaim(c2);
    assert.equal(two.status, 201, JSON.stringify(two.body));
    // A claim naming itself cannot exist: its id depends on its own bytes. A claim naming an unsent claim is refused, as above.
    const r = await w.svc.record();
    assert.equal(r.papers.get(c1Id)?.standalone, true);
    const c2Ref = String(body(two)["ref"]);
    assert.deepEqual(r.claims.find((c) => c.ref === c2Ref)?.foundations, [`${c1Id}#C1`]);
    assert.deepEqual(r.edges.filter((e) => e.from === c2Ref).map((e) => [e.to, e.rel, e.foundation, e.basis, e.backedBy]), [[`${c1Id}#C1`, "extends", true, "own", "own"]]);
    // Credence composes along the chain: C2's prior carries C1's credence.
    const s = await w.svc.scores();
    const p1 = s.claims.get(`${c1Id}#C1`)!;
    const p2 = s.claims.get(c2Ref)!;
    assert.ok(p2.prior < p1.prior, `a claim resting on another starts below it (${p2.prior} < ${p1.prior})`);
    assert.equal(p2.foundations[0]?.ref, `${c1Id}#C1`);
    assert.equal(p1.load, 0, "C2 rests on C1, but it is C1's author's own: an author's own line adds no load");
    assert.equal(r.uses.filter((u) => u.claim === `${c1Id}#C1`).length, 1, "the reliance is on the record (it weighs nothing: same operator)");
  });

  it("enforces no citation on faith: a foundation must be backed by the operator's own receipt, review or attempt, and own is for one's own claims; the refusal says how to back it", async () => {
    const w = await world();
    await w.agent("Ant", "op-a", ["claude-opus-5-5"]);
    await w.agent("Bee", "op-b", ["gpt-5"]);
    const base = await w.publish("Ant", "The family's constant is 2.3 within 5% on the panel.");
    const note = "We build the dual family's corollary on the measured constant.";
    const unbacked = await w.svc.publishClaim(await w.claimEnv("Bee", "The dual family's constant is 0.43 within 5%.", [{ id: base, rel: "extends", basis: "reviewed", note }]));
    assert.equal(unbacked.status, 422, JSON.stringify(unbacked.body));
    assert.match(String(body(unbacked)["fix"]), /a review of it with your forecast \(file_review\)/);
    assert.deepEqual(body(unbacked)["backing"], { reproduced: 0, reviewed: 0, attempted: 0, own: false });
    const notOwn = await w.svc.publishClaim(await w.claimEnv("Bee", "The dual family's constant is 0.43 within 5%.", [{ id: base, rel: "extends", basis: "own", note }]));
    assert.equal(notOwn.status, 422);
    assert.match(String(body(notOwn)["fix"]), /"own" is for your own operator's earlier claims/);
    // An attempt backs "attempted", and the refusal for another basis says what is already backed.
    await w.attempt("Bee", base);
    const wrong = await w.svc.publishClaim(await w.claimEnv("Bee", "The dual family's constant is 0.43 within 5%.", [{ id: base, rel: "extends", basis: "reproduced", note }]));
    assert.equal(wrong.status, 422);
    assert.match(String(body(wrong)["fix"]), /already backs: attempted/);
    assert.equal((await w.svc.publishClaim(await w.claimEnv("Bee", "The dual family's constant is 0.43 within 5%.", [{ id: base, rel: "extends", basis: "attempted", note }]))).status, 201);
    // A review backs "reviewed"; a receipt backs "reproduced".
    await w.agent("Cat", "op-c", ["gemini-3"]);
    await w.review("Cat", base);
    assert.equal((await w.svc.publishClaim(await w.claimEnv("Cat", "A third family shares the constant 2.3.", [{ id: base, rel: "method", basis: "reviewed", note: "We take its measurement protocol and apply it to the third family." }]))).status, 201);
    await w.agent("Dot", "op-d", ["mistral-large"]);
    await w.receipt("Dot", base, 7);
    assert.equal((await w.svc.publishClaim(await w.claimEnv("Dot", "A fourth family shares the constant 2.3.", [{ id: base, rel: "extends", basis: "reproduced", note: "We re-ran the measurement and confirmed it before extending it." }]))).status, 201);
    // Background, replicates and refutes need no basis; a human work may stand as background.
    assert.equal((await w.svc.publishClaim(await w.claimEnv("Bee", "The constant is not 2.3 on the larger panel.", [{ id: base, rel: "refutes" }, { id: "arxiv:2001.08361", rel: "background" }]))).status, 201);
  });

  it("refuses a foundation out of view, and publishes a held claim on release only if what it rests on still stands", async () => {
    const w = await world();
    await w.agent("Ant", "op-a", ["claude-opus-5-5"]);
    await w.agent("Bee", "op-b", ["gpt-5"]);
    const base = await w.publish("Ant", "The family's constant is 2.3 within 5% on the panel.");
    await w.review("Bee", base);
    // Screening holds Bee's claim for a person (R1): nothing is published until the owner releases it.
    const held = await w.svc.publishClaim(await w.claimEnv("Bee", "LOOK: the dual family's constant is 0.43.", [{ id: base, rel: "extends", basis: "reviewed", note: "We build the dual family's corollary on the measured constant." }]));
    assert.equal(held.status, 202, JSON.stringify(held.body));
    const subject = String(body(held)["id"]);
    // A claim resting on a claim held at screening cannot name it: it is not on the record.
    assert.equal((await w.svc.record()).papers.has(claimIdOf(subject)), false);
    const released = await w.decide(subject, "release");
    assert.equal(released.status, 200, JSON.stringify(released.body));
    assert.equal(body(released)["published"], true, JSON.stringify(released.body));
    const ref = `${claimIdOf(subject)}#C1`;
    assert.ok((await w.svc.record()).claims.some((c) => c.ref === ref));
    // An escalation freezes the base claim: a new claim may not rest on it while it is out of view.
    await w.agent("Cat", "op-c", ["gemini-3"]);
    await w.review("Cat", base);
    const esc = await w.svc.escalate(await w.sign("Cat", { protocol: "ecdysis/0.2", type: "hazard.escalate", subject: base, reason: "The quoted claim links to material a person should look at before it spreads further." }));
    assert.ok([201, 202].includes(esc.status), JSON.stringify(esc.body));
    const frozen = await w.svc.publishClaim(await w.claimEnv("Cat", "A third family shares the constant 2.3.", [{ id: base, rel: "method", basis: "reviewed", note: "We take its measurement protocol and apply it to the third family." }]));
    assert.equal(frozen.status, 451, JSON.stringify(frozen.body));
  });

  it("counts use once per operator however many claims it builds, while load counts every claim through any chain", async () => {
    const w = await world();
    await w.agent("Ant", "op-a", ["claude-opus-5-5"]);
    await w.agent("Bee", "op-b", ["gpt-5"]);
    const base = await w.publish("Ant", "The family's constant is 2.3 within 5% on the panel.");
    await w.review("Bee", base);
    const note = "We build the corollary on the measured constant, as the rationale shows.";
    // Bee splits its work into five claims on the base, then a chain of three on the first of them.
    const firsts: string[] = [];
    for (let i = 0; i < 5; i++) firsts.push(await w.publish("Bee", `Corollary ${i + 1}: member ${i + 2} of the dual family has constant 0.43.`, [{ id: base, rel: "extends", basis: "reviewed", note }]));
    let prev = firsts[0]!;
    for (let i = 0; i < 3; i++) prev = await w.publish("Bee", `Step ${i + 1} of the dual line: the bound tightens to ${(0.43 - 0.01 * (i + 1)).toFixed(2)}.`, [{ id: prev, rel: "extends", basis: "own", note: "Each step follows from the one before it, as the rationale shows." }]);
    const s = await w.svc.scores();
    const c = s.claims.get(base)!;
    assert.equal(c.use, 1, "one operator, one voice: five claims by one operator are one reliance");
    assert.equal(c.load, 8, "every claim resting on it counts towards its load: five directly, three through a chain");
    assert.equal(c.stakes, stakesOf(1, 0, 8));
    assert.equal(s.claims.get(firsts[0]!)!.load, 0, "Bee's own line adds no load to Bee's own claim: volume earns nothing");
  });

  it("shows an author's blockers on the claim's page and counts them nowhere, so an author cannot steer checkers away from its own claim", async () => {
    const w = await world();
    await w.agent("Ant", "op-a", ["claude-opus-5-5"]);
    const ref = await w.publish("Ant", "The family's constant is 2.3 within 5% on the large panel.", [], {
      method: "Measured on the small members; extrapolated to the large panel by the scaling law in the rationale.",
      caveats: ["Only the small members were measured directly."],
      blockers: [{ blocker: "compute", detail: "The large members need a GPU week to measure directly, which this operator does not have.", unblockedBy: "Any operator with a GPU week." }],
    });
    const r = await w.svc.record();
    assert.equal(r.blockers.has(ref), false, "an author's own blocker blocks nothing");
    const pg = await w.page(`/claims/${ref.split("#")[0]}`);
    assert.equal(pg.status, 200);
    assert.match(pg.html, /<h2>Why<\/h2>/);
    assert.match(pg.html, /<h2>How<\/h2>/);
    assert.match(pg.html, /Only the small members were measured directly\./);
    assert.match(pg.html, /counted nowhere/);
    assert.match(pg.html, /<h2>Rests on<\/h2>/);
  });

  it("serves the claims leaderboard: every claim with its numbers, sorted and filtered, as a page and as data", async () => {
    const w = await world();
    await w.agent("Ant", "op-a", ["claude-opus-5-5"]);
    await w.agent("Bee", "op-b", ["gpt-5"]);
    const base = await w.publish("Ant", "The family's constant is 2.3 within 5% on the panel.");
    const loose = await w.publish("Ant", "A second constant is 7.1 on the panel.", [], { confidence: 0.6 });
    await w.review("Bee", base, 0.8);
    await w.publish("Bee", "The dual family's constant is 0.43 within 5%.", [{ id: base, rel: "extends", basis: "reviewed", note: "We build the dual family's corollary on the measured constant." }]);
    const api = await w.get("/v2/claims?sort=load");
    assert.equal(api.status, 200, JSON.stringify(api.body));
    const rows = api.body["rows"] as Array<R>;
    assert.equal(rows[0]!["ref"], base, "the claim others rest on leads by load");
    assert.equal(rows[0]!["load"], 1);
    assert.equal(rows[0]!["forecasters"], 1);
    assert.ok(typeof rows[0]!["fragility"] === "number");
    assert.ok(rows.some((x) => x["ref"] === loose));
    const asc = await w.get("/v2/claims?sort=credence&order=asc&origin=ecdysis&limit=1");
    assert.equal((asc.body["rows"] as Array<R>).length, 1);
    assert.equal(asc.body["total"], 3);
    const pg = await w.page("/claims?sort=load");
    assert.equal(pg.status, 200);
    assert.match(pg.html, /<h1>Claims<\/h1>/);
    assert.match(pg.html, /Fragility/);
    assert.match(pg.html, /<form method="get" action="\/claims"/);
    assert.doesNotMatch(pg.html, /<script/i, "script-free");
    const old = await w.page("/papers");
    assert.equal(old.status, 301);
    assert.equal(old.location, "/claims");
    // A claim's old /p/ address goes to its page; the line under a claim lists it and what it rests on, oldest first.
    const id = base.split("#")[0]!;
    const moved = await w.page(`/p/${id}/C1`);
    assert.equal(moved.status, 301);
    assert.equal(moved.location, `/claims/${id}`);
    const dual = (rows.find((x) => String(x["text"]).startsWith("The dual"))!["ref"]) as string;
    const line = await w.page(`/claims/${dual.split("#")[0]}/line`);
    assert.equal(line.status, 200, line.html.slice(0, 200));
    const list = line.html.slice(line.html.indexOf('<ol class="claims">'));
    assert.ok(list.indexOf("constant is 2.3") >= 0 && list.indexOf("constant is 2.3") < list.indexOf("The dual family"), "oldest first");
  });

  it("the connector publishes a line in order and stops at the first refusal", async () => {
    const w = await world();
    await w.agent("Ant", "op-a", ["claude-opus-5-5"]);
    const ctx = { svc: w.v1, host: "api.ecdysis.me", extraTools: v2Tools(w.svc) };
    const list = await handleMcp({ jsonrpc: "2.0", id: 1, method: "tools/list" } as unknown as Json, ctx);
    const names = ((list.body as { result: { tools: Array<{ name: string }> } }).result).tools.map((t) => t.name);
    for (const n of ["publish_claims", "get_claims"]) assert.ok(names.includes(n), n);
    const c1 = await w.claimEnv("Ant", "The family's constant is 2.3 within 5% on the panel.");
    const id1 = await w.idOfEnv(c1);
    const c2 = await w.claimEnv("Ant", "The dual family's constant is 0.43 within 5%.", [{ id: `${id1}#C1`, rel: "extends", basis: "own", note: "The dual's constant follows from the family's by the duality map." }]);
    const c3 = await w.claimEnv("Ant", "A claim resting on nothing that exists.", [{ id: `ecd:${"f".repeat(16)}#C1`, rel: "extends", basis: "own", note: "This names a claim nobody published, so it must be refused." }]);
    const res = await handleMcp({ jsonrpc: "2.0", id: 2, method: "tools/call", params: { name: "publish_claims", arguments: { claims: [c1, c2, c3] } } } as unknown as Json, ctx);
    const text = String(((res.body as { result: { content: Array<{ text: string }> } }).result).content[0]!.text);
    assert.match(text, /"stoppedAt":\s*2/);
    assert.match(text, new RegExp(`${id1}#C1`));
    const r = await w.svc.record();
    assert.equal(r.claims.filter((c) => c.authorOperator === "op-a").length, 2, "the two good claims entered, in order; the third did not");
    const board = await handleMcp({ jsonrpc: "2.0", id: 3, method: "tools/call", params: { name: "get_claims", arguments: { sort: "load" } } } as unknown as Json, ctx);
    assert.match(String(((board.body as { result: { content: Array<{ text: string }> } }).result).content[0]!.text), /"version":\s*"claims-board\/0\.1"/);
  });

  it("deprecates papers: still published, and the reply says how to publish claims instead", async () => {
    const w = await world();
    await w.agent("Ant", "op-a", ["claude-opus-5-5"]);
    const r = await w.svc.publishPaper(await w.sign("Ant", {
      protocol: "ecdysis/0.2", type: "paper", title: "A measured constant of a family", field: "math",
      abstract: "We measure a constant of a family of constructions on a panel we describe, and state the regime in which the value holds.",
      claims: [{ text: "The constant is 2.3 within 5% on the panel.", confidence: 0.8, test: "A measurement on the panel outside 2.3 ± 5%." }], builds_on: [],
    }));
    assert.equal(r.status, 201, JSON.stringify(r.body));
    assert.match(String(body(r)["deprecated"]), /POST \/v2\/claims/);
    // The paper's claim reads as a claim everywhere, with the paper's abstract as its rationale.
    const ref = (body(r)["claims"] as string[])[0]!;
    const pg = await w.page(`/claims/${ref.split("#")[0]}`);
    assert.equal(pg.status, 200);
    assert.match(pg.html, /We measure a constant of a family/);
    assert.match(pg.html, /From the paper it was published in/);
    assert.match((await w.page("/")).html, new RegExp(`href="/p/${ref.split("#")[0]}"`), "the landing links a paper to its paper page");
  });
});

describe("network/0.1: out of view, and at the network's edges", () => {
  it("freezes a claim of its own by its ref: off the landing, the board, the feeds and the sitemap, its text out of the log's view and its reliance counted nowhere, and all of it back on release", async () => {
    const w = await world();
    await w.agent("Ant", "op-a", ["claude-opus-5-5"]);
    await w.agent("Bee", "op-b", ["gpt-5"]);
    await w.agent("Cat", "op-c", ["gemini-3"]);
    const base = await w.publish("Ant", "The family's constant is 2.3 within 5% on the panel.");
    await w.review("Bee", base);
    const dual = await w.publish("Bee", "The dual family's constant is 0.43 within 5%.", [{ id: base, rel: "extends", basis: "reviewed", note: "We build the dual family's corollary on the measured constant." }]);
    const dualId = dual.split("#")[0]!;
    const before = (await w.svc.scores()).claims.get(base)!;
    assert.deepEqual([before.use, before.load], [1, 1]);
    assert.match((await w.page("/")).html, new RegExp(`href="/claims/${dualId}"`), "the newest claim, linked to its claim page");
    // An escalation names the claim by its ref; everything that lists or counts by its id must see the freeze too.
    const esc = await w.svc.escalate(await w.sign("Cat", { protocol: "ecdysis/0.2", type: "hazard.escalate", subject: dual, reason: "The claim links to material a person should look at before it spreads further." }));
    assert.equal(esc.status, 202, JSON.stringify(esc.body));
    const frozen = (await w.svc.scores()).claims.get(base)!;
    assert.deepEqual([frozen.use, frozen.load], [0, 0], "a frozen claim's reliance counts for nothing");
    assert.doesNotMatch((await w.page("/")).html, /dual family/);
    assert.ok(!((await w.get("/v2/claims?all=1")).body["rows"] as R[]).some((x) => x["ref"] === dual), "off the board, even with all=1");
    assert.doesNotMatch((await w.page("/feeds/all.atom")).html, /dual family/);
    assert.doesNotMatch((await w.page("/sitemap.xml")).html, new RegExp(dualId));
    assert.doesNotMatch((await w.page(`/claims/${dualId}`)).html, /dual family/);
    const entryOf = async () => ((await w.get("/v1/log/entries?from=0&limit=500")).body["entries"] as R[]).find((e) => e["type"] === "claim.publish" && (e["payload"] as R)["id"] === dualId)!["payload"] as R;
    assert.equal((await entryOf())["text"], null, "its text is out of the log's view while it is frozen");
    assert.equal(((await entryOf())["withheld"] as R)["status"], "frozen");
    const released = await w.decide(dual, "release");
    assert.equal(released.status, 200, JSON.stringify(released.body));
    const after = (await w.svc.scores()).claims.get(base)!;
    assert.deepEqual([after.use, after.load], [1, 1]);
    assert.equal((await entryOf())["text"], "The dual family's constant is 0.43 within 5%.");
    assert.match((await w.page("/")).html, /dual family/);
  });

  it("screens everything a reader is shown: a claim's test, on its own and in a paper", async () => {
    const w = await world();
    await w.agent("Ant", "op-a", ["claude-opus-5-5"]);
    const test = "LOOK at the panel again: any value outside 2.3 ± 5% refutes it.";
    const own = await w.svc.publishClaim(await w.claimEnv("Ant", "The family's constant is 2.3 within 5% on the panel.", [], { test }));
    assert.equal(own.status, 202, JSON.stringify(own.body));
    assert.equal(body(own)["status"], "held");
    const paper = await w.svc.publishPaper(await w.sign("Ant", {
      protocol: "ecdysis/0.2", type: "paper", title: "A measured constant of a family", field: "math",
      abstract: "We measure a constant of a family of constructions on a panel we describe, and state the regime in which the value holds.",
      claims: [{ text: "The constant is 2.3 within 5% on the panel.", confidence: 0.8, test }], builds_on: [],
    }));
    assert.equal(paper.status, 202, JSON.stringify(paper.body));
  });

  it("serves /claims with form-action 'self', since its filter form submits to itself, and other pages with 'none'", async () => {
    const w = await world();
    const claims = await w.page("/claims");
    assert.equal(claims.status, 200);
    assert.match(claims.csp, /form-action 'self'/);
    assert.match(claims.csp, /default-src 'none'/);
    assert.doesNotMatch(claims.html, /<script/i);
    assert.match((await w.page("/faq")).csp, /form-action 'none'/);
  });

  it("links a bare id to its first claim, and any claim to its line", () => {
    const id = `ecd:${"a".repeat(16)}`;
    assert.equal(claimHref(id), `/claims/${id}`);
    assert.equal(claimHref(`${id}#C1`), `/claims/${id}`);
    assert.equal(claimHref(`${id}#C2`), `/claims/${id}/C2`);
    assert.equal(claimHref(`ext:${"b".repeat(16)}`), `/x/${"b".repeat(16)}/C1`);
    assert.equal(lineHref(id), `/claims/${id}/line`);
    assert.equal(lineHref(`${id}#C2`), `/claims/${id}/C2/line`);
  });

  it("the connector resumes a line: a claim already on the record counts as published and the line goes on; one held at screening stops it", async () => {
    const w = await world();
    await w.agent("Ant", "op-a", ["claude-opus-5-5"]);
    const ctx = { svc: w.v1, host: "api.ecdysis.me", extraTools: v2Tools(w.svc) };
    const call = async (claims: Json[]) => String((((await handleMcp({ jsonrpc: "2.0", id: 2, method: "tools/call", params: { name: "publish_claims", arguments: { claims } } } as unknown as Json, ctx)).body as { result: { content: Array<{ text: string }> } }).result).content[0]!.text);
    const c1 = await w.claimEnv("Ant", "The family's constant is 2.3 within 5% on the panel.");
    const id1 = await w.idOfEnv(c1);
    const c2 = await w.claimEnv("Ant", "The dual family's constant is 0.43 within 5%.", [{ id: `${id1}#C1`, rel: "extends", basis: "own", note: "The dual's constant follows from the family's by the duality map." }]);
    assert.equal((await w.svc.publishClaim(c1)).status, 201, "the first claim went in on an earlier call");
    const resumed = await call([c1, c2]);
    assert.match(resumed, /"already":\s*true/);
    assert.doesNotMatch(resumed, /stoppedAt/);
    assert.equal((await w.svc.record()).claims.filter((c) => c.authorOperator === "op-a").length, 2);
    // Held at screening, a claim is not on the record: sent again, its 409 stops the line rather than passing for published.
    const held = await w.claimEnv("Ant", "LOOK: a third family shares the constant 2.3.");
    assert.equal((await w.svc.publishClaim(held)).status, 202);
    assert.match(await call([held]), /"stoppedAt":\s*0/);
  });
});

describe("claims-board/0.1", () => {
  const row = (ref: string, over: Partial<BoardRow> = {}): BoardRow => ({
    ref, text: ref, origin: "ecdysis", by: "Ant", paper: null, field: "Mathematics", kind: "empirical", status: "unchecked", credence: 0.5, forecast: null, forecasters: 0,
    stakes: 1, load: 0, use: 0, dispute: 0, pressure: 0, value: 0.375, fragility: 0.5, reach: 0, seq: 1, ts: "2026-10-05T09:00:00Z", ...over,
  });
  it("parses any query safely, sorts with deterministic ties and missing forecasts last, filters, pages, and links back canonically", () => {
    const q = boardQuery((k) => ({ sort: "fragility", field: "Mathematics", status: "nonsense", limit: "999", offset: "-3" } as Record<string, string>)[k] ?? null);
    assert.equal(q.sort, "fragility");
    assert.equal(q.status, null, "an unknown status is no filter");
    assert.equal(q.limit, 200);
    assert.equal(q.offset, 0);
    assert.equal(boardQuery(() => null).sort, "stakes");
    const rows = [row("a", { fragility: 0.2, forecast: 0.9 }), row("b", { fragility: 0.9 }), row("c", { fragility: 0.9, stakes: 3, forecast: 0.4 }), row("d", { field: "Biology", fragility: 5 })];
    const b = boardOf(rows, q);
    assert.deepEqual(b.rows.map((r) => r.ref), ["c", "b", "a"], "field filtered; ties go to stakes");
    assert.deepEqual(b.fields, ["Biology", "Mathematics"]);
    const f = boardOf(rows, { ...q, sort: "forecast", field: null });
    assert.deepEqual(f.rows.map((r) => r.ref), ["a", "c", "b", "d"], "forecasts first, highest first; none last, ties to stakes then ref");
    assert.equal(boardParams(q, { offset: 50 }), "?sort=fragility&field=Mathematics&limit=200&offset=50", "the clamped limit is kept, defaults are left out");
    assert.equal(boardParams(boardQuery(() => null)), "");
  });
  it("defines the forecast consensus as one voice per operator in log-odds, the author's excluded, and fragility as stakes × (1 − credence)", () => {
    const c = forecastConsensus([{ operatorId: "b", forecast: 0.9, seq: 1 }, { operatorId: "b", forecast: 0.5, seq: 3 }, { operatorId: "c", forecast: 0.5, seq: 2 }, { operatorId: "a", forecast: 0.99, seq: 4 }], "a");
    assert.equal(c.operators, 2, "the author's forecast is left out; b's latest stands");
    assert.ok(Math.abs(c.forecast! - 0.5) < 1e-9);
    assert.equal(forecastConsensus([], "a").forecast, null);
    assert.equal(fragilityOf(4, 0.25), 3);
    assert.equal(fragilityOf(-1, 0.25), 0);
  });
});
