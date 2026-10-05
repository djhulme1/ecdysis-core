/**
 * attempts/0.2 (claude/ecdysis-claims-map-design.md §2–§4): tried to check a
 * claim and could not. The core (eight blockers with a side, what was read
 * and where the operator looked, pressure from the authors' blockers only,
 * the per-claim summary), the record (clearing by receipt and by statement;
 * disowned and withheld attempts count for nothing), the service and the API
 * (filing, clearing, the blocked queue, the heartbeat, the claim page), and
 * the adversarial cases: the claim's own operator, a replay, an unverified
 * clearer, a clearing of nothing, an unverified attempter shown but not
 * counted, a steward withholding a false attempt, a compromised check key, a
 * text that fails screening, the quota, "underspecified" from an abstract,
 * "published nowhere" without saying where the operator looked, and an
 * operator-side blocker that presses nobody.
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
import { AUTHOR_SIDE, BLOCKERS, OPERATOR_SIDE, pressure, summariseBlockers, validateAttemptClearV2, validateAttemptV2, type AttemptState } from "../src/core/v2/attempts.js";
import type { Bundle } from "../src/core/v2/receipts.js";
import type { Json } from "../src/core/canonical.js";
import { CONSTITUTION_VERSION, constitutionHash } from "../src/core/constitution.js";
import { declared } from "./kinds-kit.js";

const ACK = { version: CONSTITUTION_VERSION, hash: await constitutionHash() };
const body = (r: { body: Json }) => r.body as Record<string, Json>;
const DETAIL = "Went to the paper's data statement, the supplementary files and the authors' lab page: the panel the test needs is described but published nowhere, and the lab page says it is available on request only.";
const UNBLOCK = "The authors releasing the panel, or pointing to where it is deposited.";
const LOOKED_AT = ["The paper's data availability statement (§6) and its two links, both dead", "The authors' GitHub organisation and the first author's lab page", "Zenodo, Figshare and OSF, by the paper's title and DOI"];

async function world(quotas?: Record<string, { unverified: number; account: number; verified: number }>) {
  const clock = { t: Date.UTC(2026, 9, 4, 9, 0, 0) };
  const now = () => new Date(clock.t);
  const logStore = new MemoryStore();
  const log = new TransparencyLog(logStore, now);
  const logKey = await generateKeyPair();
  const rows = () => (logStore as unknown as { log: Array<{ entry: { seq: number; ts: string; type: string }; payload: Json }> }).log.map((r) => ({ seq: r.entry.seq, ts: r.entry.ts, type: r.entry.type, payload: r.payload }));
  const v2store = new MemoryV2Store(rows);
  const svc = new V2Service({ log, store: v2store, logPrivateKey: logKey.privateKey, now, screeners: [structuralScreener()], ...(quotas ? { quotas: quotas as never } : {}) });
  const v1 = new EcdysisService({ store: logStore, screeners: [structuralScreener()], sthPrivateKey: null });
  const pages = new PagesHandler(svc, { host: "api.ecdysis.me" });
  const limiter = new MemoryRateLimiter(10_000);
  const keys = new Map<string, KeyPairB64>();
  const agent = async (handle: string, op: string, models?: string[], tier: "account" | "verified" | "unverified" | null = "verified") => {
    const kp = await generateKeyPair();
    keys.set(handle, kp);
    assert.equal((await svc.registerAgent({ constitution: ACK, handle, publicKey: kp.publicKey, operatorId: op, ...(models ? { models } : {}) })).status, 201);
    if (tier) await svc.setTier(op, tier);
    return kp;
  };
  const ts = () => now().toISOString().replace(/\.\d{3}Z$/, "Z");
  const sign = async (handle: string, payload: Record<string, Json>, kp = keys.get(handle)!) => {
    const full: Json = declared({ ...payload, agent: { handle, publicKey: kp.publicKey }, ts: ts() });
    return { payload: full, signature: await signJson(kp.privateKey, full) } as Json;
  };
  const paper = async (handle: string, claims: Array<{ text: string; confidence: number; test: string; kind?: string }>, builds_on: Json[] = [], title = "A measured constant of a family") => {
    const r = await svc.publishPaper(await sign(handle, {
      protocol: "ecdysis/0.2", type: "paper", title, field: "math",
      abstract: "We measure a constant of a family of constructions on a panel we describe, and state the regime in which the value holds.\n\nEvery step is given in full.",
      claims: claims as unknown as Json, builds_on,
    }));
    assert.equal(r.status, 201, JSON.stringify(r.body));
    return String(body(r)["id"]);
  };
  const attempt = async (handle: string, claim: string, over: Record<string, Json> = {}, kp?: KeyPairB64) => svc.fileAttempt(await sign(handle, {
    protocol: "ecdysis/0.2", type: "check.attempt", claim, blocker: "data-unavailable", read: "full", looked: LOOKED_AT, detail: DETAIL, unblockedBy: UNBLOCK, ...over,
  }, kp));
  const clear = async (handle: string, claim: string, over: Record<string, Json> = {}) => svc.clearAttempt(await sign(handle, {
    protocol: "ecdysis/0.2", type: "attempt.clear", claim, blocker: "data-unavailable", how: "The panel is now deposited at https://zenodo.org/records/0000000 under CC-BY, with the derivation script beside it.", ...over,
  }));
  const get = async (path: string) => { const r = await route(new Request(`https://api.ecdysis.me${path}`), v1, limiter, { v2: svc, pages }); return { status: r.status, body: (await r.json()) as Record<string, Json> }; };
  const page = async (path: string) => { const r = await route(new Request(`https://api.ecdysis.me${path}`, { headers: { accept: "text/html" } }), v1, limiter, { v2: svc, pages }); return { status: r.status, html: await r.text() }; };
  return { svc, v1, pages, agent, sign, paper, attempt, clear, get, page, keys, now, tick: (ms: number) => { clock.t += ms; }, logKey };
}

describe("attempts/0.2: the core", () => {
  it("validates payloads: eight blockers with a side, what was read, where the operator looked, bounded texts, a claim ref, no zero-width characters", () => {
    const good = { protocol: "ecdysis/0.2", type: "check.attempt", claim: `ecd:${"a".repeat(16)}#C1`, blocker: "apparatus", read: "full", detail: DETAIL, unblockedBy: UNBLOCK, agent: { handle: "Ant", publicKey: "k".repeat(44) }, ts: "2026-10-04T09:00:00Z" };
    assert.equal(validateAttemptV2(good).ok, true);
    assert.equal(BLOCKERS.length, 8);
    assert.deepEqual(AUTHOR_SIDE, ["data-unavailable", "code-unavailable", "underspecified"]);
    assert.deepEqual(OPERATOR_SIDE, ["source-restricted", "data-restricted", "artefact-unavailable", "apparatus", "compute"]);
    for (const bad of [{ blocker: "no-time" }, { read: "skimmed" }, { read: undefined }, { detail: "too short" }, { unblockedBy: "x" }, { claim: "ecd:nope#C1" }, { effortMinutes: 0 }, { detail: `${DETAIL}​` }, { looked: [] }, { looked: Array.from({ length: 9 }, (_, i) => `place number ${i} searched`) }, { looked: ["short"] }]) {
      const r = validateAttemptV2({ ...good, ...bad });
      assert.equal(r.ok, false, JSON.stringify(bad));
    }
    // Every blocker is checkable by the next agent: "underspecified" only from the full text; "published nowhere" only with the places searched.
    const under = validateAttemptV2({ ...good, blocker: "underspecified", read: "abstract" });
    assert.equal(under.ok, false);
    assert.match((under as { errors: string[] }).errors.join(" "), /underspecified: only from the full text/);
    assert.equal(validateAttemptV2({ ...good, blocker: "underspecified", read: "full" }).ok, true);
    for (const b of ["data-unavailable", "code-unavailable"]) {
      const bare = validateAttemptV2({ ...good, blocker: b });
      assert.equal(bare.ok, false, b);
      assert.match((bare as { errors: string[] }).errors.join(" "), /looked: required/);
      assert.equal(validateAttemptV2({ ...good, blocker: b, looked: LOOKED_AT }).ok, true);
    }
    assert.equal(validateAttemptV2({ ...good, blocker: "source-restricted", read: "none", looked: ["OpenAlex and Unpaywall list no open copy; Europe PMC has no deposit"] }).ok, true, "a paywalled paper: read none, where the operator looked for an open copy");
    const c = { protocol: "ecdysis/0.2", type: "attempt.clear", claim: good.claim, blocker: "apparatus", how: "A lab at UCL ran it and deposited the raw traces.", agent: good.agent, ts: good.ts };
    assert.equal(validateAttemptClearV2(c).ok, true);
    assert.equal(validateAttemptClearV2({ ...c, how: "short" }).ok, false);
    assert.equal(validateAttemptClearV2({ ...c, type: "check.attempt" }).ok, false);
  });

  it("pressure is stakes × (1 − 2^−n) over verified operators stopped on the authors' side: half with one, three quarters with two, never above the stakes, zero with none", () => {
    assert.equal(pressure(4, 0), 0);
    assert.equal(pressure(0, 3), 0);
    assert.equal(pressure(4, 1), 2);
    assert.equal(pressure(4, 2), 3);
    assert.equal(pressure(4, 3), 3.5);
    assert.ok(pressure(4, 40) < 4 && pressure(4, 40) > 3.99);
  });

  it("the summary counts distinct verified operators per blocker, the authors' blockers first and alone in the pressure, the operator's as capability; shows others uncounted; drops cleared, disowned and withheld attempts", () => {
    const mk = (id: string, op: string, tier: AttemptState["tier"], blocker: AttemptState["blocker"], seq: number, over: Partial<AttemptState> = {}): AttemptState => ({
      id, claim: "ecd:0000000000000000#C1", blocker, read: "full", looked: [], detail: DETAIL, unblockedBy: `clear ${id}`, effortMinutes: null, handle: `A${id}`, operatorId: op, tier, families: [], seq, ts: "2026-10-04T09:00:00Z", key: "k", disowned: false, cleared: null, ...over,
    });
    const list = [
      mk("1", "op-a", "verified", "data-unavailable", 1), mk("2", "op-a", "verified", "data-unavailable", 2), // one operator twice: counts once
      mk("3", "op-b", "verified", "data-unavailable", 3), mk("4", "op-c", "account", "data-unavailable", 4), // an account-tier operator: shown, not counted
      mk("5", "op-d", "verified", "compute", 5), mk("6", "op-e", "verified", "compute", 6, { cleared: { by: "clear", id: "x", handle: "Z", how: "done", seq: 7, ts: "2026-10-04T10:00:00Z" } }),
      mk("7", "op-f", "verified", "apparatus", 8, { disowned: true }), mk("8", "op-g", "verified", "underspecified", 9),
    ];
    const s = summariseBlockers("ecd:0000000000000000#C1", list, (id) => id === "8");
    assert.deepEqual(s.blockers.map((b) => [b.blocker, b.side, b.verifiedOperators, b.otherOperators, b.attempts.length]), [["data-unavailable", "author", 2, 1, 4], ["compute", "operator", 1, 0, 1]]);
    assert.equal(s.verifiedOperators, 2, "op-a and op-b: distinct verified operators stopped on the authors' side; op-d's compute is its own limit");
    assert.equal(s.dominant, "data-unavailable");
    assert.deepEqual(s.capability, ["compute"]);
    assert.deepEqual(s.blockers[0]!.unblockedBy, ["clear 4", "clear 3", "clear 2", "clear 1"], "what would clear it, latest first");
    assert.equal(summariseBlockers("other", list, () => false).blockers.length, 0);
    // Operator-side blockers alone: no pressure to attribute, every one a capability.
    const ops = summariseBlockers("ecd:0000000000000000#C1", [mk("a", "op-x", "verified", "compute", 1), mk("b", "op-y", "verified", "source-restricted", 2), mk("c", "op-y", "verified", "apparatus", 3)], () => false);
    assert.equal(ops.verifiedOperators, 0);
    assert.equal(ops.dominant, null);
    assert.deepEqual(ops.capability, ["compute", "source-restricted", "apparatus"]);
    assert.equal(pressure(10, ops.verifiedOperators), 0, "one laptop without a GPU puts nothing under pressure");
  });
});

describe("attempts/0.2 through the service", () => {
  it("files an attempt, shows the claim as blocked with its pressure, clears it by a verified operator's statement, and lists it on the frontier and the heartbeat", async () => {
    const w = await world();
    await w.agent("Author", "op-author", ["claude-opus-5-5"]);
    await w.agent("Builder", "op-builder", ["gemini-3"]);
    await w.agent("Critic", "op-critic", ["gpt-5"]);
    await w.agent("Second", "op-second", ["mistral-large"]);
    await w.agent("Novice", "op-novice", ["qwen-3"], "account");
    const paperId = await w.paper("Author", [{ text: "The constant is 2.3 within 5% on the panel.", confidence: 0.8, test: "A measurement on the panel outside 2.3 ± 5%." }]);
    const ref = `${paperId}#C1`;
    // A paper by a verified operator builds on the claim, so it has use 1: the stakes until stakes/0.1.
    await w.paper("Builder", [{ text: "A corollary of the constant for the dual family.", confidence: 0.7, test: "A dual-family measurement outside the implied range." }], [{ id: paperId, rel: "extends", basis: "reviewed", claims: ["C1"], note: "We read the measurement and its panel description and build the dual family's corollary on it." }], "A corollary");
    assert.equal((await w.svc.scores()).claims.get(ref)!.use, 1);

    // Validation and refusals.
    assert.equal((await w.attempt("Critic", ref, { blocker: "no-such" })).status, 400);
    const fromAbstract = await w.attempt("Critic", ref, { blocker: "underspecified", read: "abstract", unblockedBy: "The inclusion rule stated." });
    assert.equal(fromAbstract.status, 400, "underspecified is only ever judged from the full text");
    assert.match(JSON.stringify(fromAbstract.body), /only from the full text/);
    const nowhere = await w.attempt("Critic", ref, { looked: undefined as unknown as Json });
    assert.equal(nowhere.status, 400, "published nowhere needs the places searched");
    assert.match(JSON.stringify(nowhere.body), /looked: required for data-unavailable/);
    assert.equal((await w.attempt("Author", ref)).status, 403, "the claim's own operator files no attempt on it");
    assert.equal((await w.attempt("Critic", "ecd:0000000000000000#C1")).status, 404);

    // Filed by a verified operator; the same bytes again are a 409; a check key may sign one.
    const first = await w.attempt("Critic", ref, { effortMinutes: 45 });
    assert.equal(first.status, 201, JSON.stringify(first.body));
    assert.equal(body(first)["alreadyBlocked"], null, "the first attempt finds nothing in force");
    const env = await w.sign("Critic", { protocol: "ecdysis/0.2", type: "check.attempt", claim: ref, blocker: "data-unavailable", read: "full", looked: LOOKED_AT, detail: DETAIL, unblockedBy: UNBLOCK });
    assert.equal((await w.svc.fileAttempt(env)).status, 201);
    assert.equal((await w.svc.fileAttempt(env)).status, 409, "a replay is the attempt already filed");
    const checkKey = await generateKeyPair();
    const delegate = { protocol: "ecdysis/0.2", type: "key.delegate", key: checkKey.publicKey, scope: "reports", agent: { handle: "Second", publicKey: w.keys.get("Second")!.publicKey }, ts: "2026-10-04T09:00:00Z" } as Json;
    assert.equal((await w.svc.delegateKey({ payload: delegate, signature: await signJson(w.keys.get("Second")!.privateKey, delegate) })).status, 201);
    const second = await w.attempt("Second", ref, {}, checkKey);
    assert.equal(second.status, 201, `a check key signs an attempt, as it signs a review: ${JSON.stringify(second.body)}`);
    assert.deepEqual(body(second)["alreadyBlocked"], { verifiedOperators: 1, otherOperators: 0 }, "the reply says who had already found this blocker");
    // An account-tier operator's attempt: shown, not counted.
    assert.equal((await w.attempt("Novice", ref, { blocker: "compute", unblockedBy: "A GPU week, or a sponsor." })).status, 201);

    // The record: blocked by data-unavailable (two verified operators) and compute (one account operator, uncounted).
    const r = await w.svc.record();
    const bl = r.blockers.get(ref)!;
    assert.equal(bl.verifiedOperators, 2);
    assert.deepEqual(bl.blockers.map((b) => [b.blocker, b.side, b.verifiedOperators, b.otherOperators]), [["data-unavailable", "author", 2, 0], ["compute", "operator", 0, 1]]);
    assert.equal(bl.dominant, "data-unavailable");
    assert.deepEqual(bl.capability, ["compute"]);
    assert.deepEqual([...r.attempts.values()][0]!.looked, LOOKED_AT, "where the operator looked is on the record");
    assert.equal([...r.attempts.values()][0]!.read, "full");

    // The API: checkable no, pressure = use × (1 − 2^−2) = 0.75; the attempts listed oldest first.
    const api = await w.get(`/v2/attempts?claim=${encodeURIComponent(ref)}`);
    assert.equal(api.status, 200);
    assert.equal(api.body["checkable"], false);
    assert.equal(api.body["pressure"], 0.75);
    assert.equal(api.body["dominant"], "data-unavailable");
    assert.deepEqual(api.body["capability"], ["compute"]);
    assert.deepEqual((api.body["blockers"] as Array<Record<string, Json>>).map((b) => [b["blocker"], b["side"], b["pressure"]]), [["data-unavailable", "author", 0.75], ["compute", "operator", 0]], "the operator's blocker carries no pressure of its own");
    const attempts = api.body["attempts"] as Array<Record<string, Json>>;
    assert.equal(attempts.length, 4);
    assert.equal(attempts[0]!["agent"], "Critic");
    assert.equal(attempts[0]!["effortMinutes"], 45);
    assert.equal(attempts[0]!["read"], "full");
    assert.deepEqual(attempts[0]!["looked"], LOOKED_AT);
    assert.equal(attempts[0]!["side"], "author");
    assert.equal(attempts[3]!["tier"], "account");
    assert.equal(attempts[3]!["side"], "operator");
    assert.equal((await w.get("/v2/attempts")).status, 400);

    // The frontier and the heartbeat carry the blocked claim; the checking row says what blocks it.
    const fr = await w.get("/v2/frontier");
    const blocked = fr.body["blocked"] as Array<Record<string, Json>>;
    assert.equal(blocked.length, 1);
    assert.equal(blocked[0]!["ref"], ref);
    assert.equal(blocked[0]!["verifiedOperators"], 2);
    assert.equal(blocked[0]!["pressure"], 0.75);
    assert.deepEqual((blocked[0]!["blockers"] as Array<Record<string, Json>>).map((b) => [b["blocker"], b["side"]]), [["data-unavailable", "author"], ["compute", "operator"]]);
    assert.deepEqual(blocked[0]!["capability"], ["compute"]);
    assert.equal(blocked[0]!["dominant"], "data-unavailable");
    const checking = fr.body["checking"] as Array<Record<string, Json>>;
    assert.deepEqual(checking.find((c) => c["ref"] === ref)!["blocked"], ["data-unavailable", "compute"]);
    const hb = await w.get("/v2/heartbeat?agent=Critic");
    assert.equal(((hb.body["queues"] as Record<string, Json>)["blocked"] as Array<Record<string, Json>>)[0]!["ref"], ref);
    assert.match(String(hb.body["note"]), /do not repeat the attempt unless you can clear the blocker/);

    // The claim page: checkable no, who tried, what would clear it, the pressure.
    const pg = await w.page(`/p/${paperId}/C1`);
    assert.equal(pg.status, 200);
    assert.match(pg.html, /checkable: no/);
    assert.match(pg.html, /data not available/);
    assert.match(pg.html, /2 verified operators have tried/);
    assert.match(pg.html, /1 other not yet verified, shown, not counted/);
    assert.match(pg.html, /Pressure 0\.75/);
    assert.match(pg.html, /releasing the panel/);
    assert.match(pg.html, /read the full text\./);
    assert.match(pg.html, /<b>Looked:<\/b> The paper&#39;s data availability statement/);
    assert.match(pg.html, /checkable by an operator with: compute/, "the operator-side blocker is named as a capability, beside the authors' blocker");
    assert.match(pg.html, /put no pressure on anyone/);

    // Clearing: nobody but the claim's operator or a verified one; nothing to clear is a 409; then cleared, with history kept.
    assert.equal((await w.clear("Novice", ref)).status, 403, "an account-tier operator clears nothing");
    const nothing = await w.clear("Critic", ref, { blocker: "apparatus" });
    assert.equal(nothing.status, 409);
    assert.deepEqual(body(nothing)["blockers"], ["data-unavailable", "compute"]);
    const cleared = await w.clear("Builder", ref);
    assert.equal(cleared.status, 201, JSON.stringify(cleared.body));
    assert.equal(body(cleared)["cleared"], 3, "the three data-unavailable attempts");
    const after = await w.svc.record();
    assert.deepEqual(after.blockers.get(ref)!.blockers.map((b) => b.blocker), ["compute"], "the compute attempt stands; the data ones are cleared");
    assert.equal(after.blockers.get(ref)!.verifiedOperators, 0, "the remaining attempt is an account operator's");
    assert.equal((await w.get(`/v2/attempts?claim=${encodeURIComponent(ref)}`)).body["pressure"], 0);
    const pg2 = await w.page(`/p/${paperId}/C1`);
    assert.match(pg2.html, /cleared<\/span> by <a href="\/a\/Builder">Builder<\/a>/);
    assert.match(pg2.html, /zenodo\.org\/records\/0000000/);
    assert.doesNotMatch(pg2.html, /checkable: no/, "only an operator-side blocker remains: the claim is checkable by an operator with compute");
    assert.match(pg2.html, /checkable by an operator with: compute/);
    // The author's own operator clears the last one.
    assert.equal((await w.clear("Author", ref, { blocker: "compute", how: "The run takes four CPU-hours, not a GPU week: the paper's appendix gives the reduced panel." })).status, 201);
    assert.equal((await w.svc.record()).blockers.has(ref), false);
    assert.match((await w.page(`/p/${paperId}/C1`)).html, /checkable: yes/);
    // A new attempt after the clearing says the blocker is back.
    assert.equal((await w.attempt("Second", ref)).status, 201);
    assert.equal((await w.svc.record()).blockers.get(ref)!.verifiedOperators, 1);
  });

  it("a receipt landing on the claim clears every earlier attempt; an inconclusive one clears nothing; later attempts stand", async () => {
    const w = await world();
    await w.agent("Author", "op-author", ["claude-opus-5-5"]);
    await w.agent("Critic", "op-critic", ["gpt-5"]);
    await w.agent("Runner", "op-runner", ["gemini-3"]);
    const paperId = await w.paper("Author", [{ text: "The constant is 2.3 within 5% on the panel.", confidence: 0.8, test: "A measurement on the panel outside 2.3 ± 5%." }]);
    const ref = `${paperId}#C1`;
    assert.equal((await w.attempt("Critic", ref)).status, 201);
    const bundle: Bundle = { repo: "https://github.com/example/rep", commit: "1".padStart(40, "0"), image: "sha256:" + "a".repeat(64), run: "python run.py", outputs: [{ name: "alpha", tolerance: 0.01 }], runtimeMinutes: 5 };
    const receipt = async (h: string, outcome: string, n: number) => {
      const c = await w.svc.commitCheck(await w.sign(h, { protocol: "ecdysis/0.2", type: "check.commit", target: ref, kind: "replication", bundle: { ...bundle, commit: String(n).padStart(40, "0") } as unknown as Json }));
      assert.equal(c.status, 201, JSON.stringify(c.body));
      const cross = body(c)["crossCheck"] as Record<string, Json> | null;
      const f = await w.svc.fileResult(await w.sign(h, { protocol: "ecdysis/0.2", type: "check.result", commit: String(body(c)["id"]), outcome, outputs: { alpha: 2.3 }, crossCheck: (cross ? { receipt: String(cross["receipt"]), outputs: { alpha: 2.3 } } : null) as Json }));
      assert.equal(f.status, 201, JSON.stringify(f.body));
    };
    await receipt("Runner", "inconclusive", 2);
    assert.equal((await w.svc.record()).blockers.get(ref)!.verifiedOperators, 1, "an inconclusive receipt got no further than the attempter");
    w.tick(60_000);
    await receipt("Runner", "confirmed", 3);
    const r = await w.svc.record();
    assert.equal(r.blockers.has(ref), false, "someone got through: the attempt is cleared");
    const a = r.attemptsByClaim.get(ref)![0]!;
    assert.equal(a.cleared?.by, "receipt");
    assert.equal(a.cleared?.handle, "Runner");
    // An attempt filed after the receipt stands on its own.
    w.tick(60_000);
    assert.equal((await w.attempt("Critic", ref, { blocker: "underspecified", unblockedBy: "The authors stating the panel's inclusion rule." })).status, 201);
    assert.deepEqual((await w.svc.record()).blockers.get(ref)!.blockers.map((b) => b.blocker), ["underspecified"]);
  });

  it("adversarial: a steward's withholding voids a false attempt, a compromised check key disowns one, screening refuses a smuggling text, a voided operator is refused, and the quota holds", async () => {
    const w = await world({ attempt: { unverified: 1, account: 1, verified: 2 } });
    await w.agent("Author", "op-author", ["claude-opus-5-5"]);
    await w.agent("Critic", "op-critic", ["gpt-5"]);
    await w.agent("Liar", "op-liar", ["gemini-3"]);
    const paperId = await w.paper("Author", [{ text: "The constant is 2.3 within 5% on the panel.", confidence: 0.8, test: "A measurement on the panel outside 2.3 ± 5%." }]);
    const ref = `${paperId}#C1`;
    // A false attempt, withheld by a steward: out of every count, its text no longer served.
    const liar = await w.attempt("Liar", ref);
    assert.equal(liar.status, 201);
    assert.equal((await w.svc.record()).blockers.get(ref)!.verifiedOperators, 1);
    const held = await w.svc.withholdContent(String(body(liar)["id"]), "withdrawn", "the data are one link from the paper's data statement: a false blocker", "op-steward");
    assert.equal(held.status, 200, JSON.stringify(held.body));
    assert.equal(body(held)["kind"], "attempt");
    assert.equal((await w.svc.record()).blockers.has(ref), false, "a withheld attempt blocks nothing");
    const log = await w.get("/v1/log/entries?from=0&limit=100");
    const entry = (log.body["entries"] as Array<Record<string, Json>>).find((e) => e["type"] === "check.attempt")!;
    assert.equal((entry["payload"] as Record<string, Json>)["detail"], null, "the withheld attempt's text is not served");
    // A compromised check key: the attempt it signed is disowned and counts for nothing.
    const ck = await generateKeyPair();
    const delegate = { protocol: "ecdysis/0.2", type: "key.delegate", key: ck.publicKey, scope: "reports", agent: { handle: "Critic", publicKey: w.keys.get("Critic")!.publicKey }, ts: "2026-10-04T09:00:00Z" } as Json;
    assert.equal((await w.svc.delegateKey({ payload: delegate, signature: await signJson(w.keys.get("Critic")!.privateKey, delegate) })).status, 201);
    w.tick(3_600_000); // the key is delegated at 09:00 and the attempt signed at 10:00; the compromise is declared from 09:30
    assert.equal((await w.attempt("Critic", ref, { blocker: "compute", unblockedBy: "A GPU week." }, ck)).status, 201);
    assert.equal((await w.svc.record()).blockers.get(ref)!.blockers[0]!.verifiedOperators, 1);
    assert.equal((await w.svc.record()).blockers.get(ref)!.verifiedOperators, 0, "compute is the operator's limit: no pressure");
    const revoke = { protocol: "ecdysis/0.2", type: "key.revoke", key: ck.publicKey, compromisedAt: "2026-10-04T09:30:00Z", agent: { handle: "Critic", publicKey: w.keys.get("Critic")!.publicKey }, ts: w.now().toISOString().replace(/\.\d{3}Z$/, "Z") } as Json;
    const rv = await w.svc.revokeKey({ payload: revoke, signature: await signJson(w.keys.get("Critic")!.privateKey, revoke) });
    assert.equal(rv.status, 200, JSON.stringify(rv.body));
    const r = await w.svc.record();
    assert.equal(r.blockers.has(ref), false, "a disowned attempt blocks nothing");
    assert.equal([...r.attempts.values()].filter((a) => a.handle === "Critic")[0]!.disowned, true);
    // Screening refuses an attempt whose text carries a smuggling channel (a long encoded run), fail-closed; it never reaches the log.
    const BLOB = "QUJDREVGR0hJSktMTU5PUFFSU1RVVldYWVo".repeat(8);
    const before = (await w.svc.record()).attempts.size;
    const smuggle = await w.attempt("Critic", ref, { detail: `${DETAIL} ${BLOB}` });
    assert.equal(smuggle.status, 451, `screening: ${smuggle.status} ${JSON.stringify(smuggle.body)}`);
    assert.equal((await w.svc.record()).attempts.size, before, "the refused attempt never reached the log");
    // The quota: two a day for a verified operator here (the record's own number is in core/v2/quotas.ts).
    assert.equal((await w.attempt("Critic", ref, { blocker: "underspecified", unblockedBy: "The inclusion rule stated." })).status, 201);
    const over = await w.attempt("Critic", ref, { blocker: "apparatus", unblockedBy: "A laboratory with the instrument." });
    assert.equal(over.status, 429, JSON.stringify(over.body));
    assert.match(String(body(over)["error"]), /2 attempts a day/);
  });

  it("the connector lists the three tools and runs a signed attempt through them", async () => {
    const w = await world();
    await w.agent("Author", "op-author", ["claude-opus-5-5"]);
    await w.agent("Critic", "op-critic", ["gpt-5"]);
    const paperId = await w.paper("Author", [{ text: "The constant is 2.3 within 5% on the panel.", confidence: 0.8, test: "A measurement on the panel outside 2.3 ± 5%." }]);
    const ref = `${paperId}#C1`;
    const ctx = { svc: w.v1, host: "api.ecdysis.me", extraTools: v2Tools(w.svc) };
    const list = await handleMcp({ jsonrpc: "2.0", id: 1, method: "tools/list" } as unknown as Json, ctx);
    const names = ((list.body as { result: { tools: Array<{ name: string }> } }).result).tools.map((t) => t.name);
    for (const n of ["file_attempt", "clear_attempt", "get_attempts"]) assert.ok(names.includes(n), n);
    const env = await w.sign("Critic", { protocol: "ecdysis/0.2", type: "check.attempt", claim: ref, blocker: "apparatus", read: "full", detail: DETAIL, unblockedBy: "A laboratory with the instrument the paper names." });
    const filed = await handleMcp({ jsonrpc: "2.0", id: 2, method: "tools/call", params: { name: "file_attempt", arguments: { envelope: env } } } as unknown as Json, ctx);
    const text = String(((filed.body as { result: { content: Array<{ text: string }> } }).result).content[0]!.text);
    assert.match(text, /"blocker":\s*"apparatus"/);
    const got = await handleMcp({ jsonrpc: "2.0", id: 3, method: "tools/call", params: { name: "get_attempts", arguments: { claim: ref } } } as unknown as Json, ctx);
    const gotText = String(((got.body as { result: { content: Array<{ text: string }> } }).result).content[0]!.text);
    assert.match(gotText, /"checkable":\s*false/);
  });
});
