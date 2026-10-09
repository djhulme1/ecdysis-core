/**
 * credence/0.6, the checking ladder (Lucy's three levels, 9 October 2026):
 *
 *   1. same data, same method (a verification): shows the reported results
 *      follow from the paper's data;
 *   2. new data, same method (a reproduction): tests the finding itself;
 *   3. the design: whether the method tests what the claim says (robustness
 *      tests and arguments on methodological grounds).
 *
 * On a claim about the world (a period scope, or general because the finding
 * is asserted beyond its data), a confirming verification counts half a
 * confirming reproduction, a failing one keeps its full weight, and the claim
 * can be established only once a reproduction has confirmed it. A claim
 * general by construction is unchanged: checking the object is the test.
 * Direction names the rung a check should take; each claim page shows how
 * far up it has got; the FAQ draws the order.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { MemoryStore } from "../src/store/memory-store.js";
import { TransparencyLog } from "../src/core/log.js";
import { generateKeyPair, signJson, type KeyPairB64 } from "../src/core/crypto.js";
import { MemoryV2Store, V2Service } from "../src/api/v2/service.js";
import { PagesHandler } from "../src/api/v2/pages.js";
import {
  aboutTheWorld, computeCredenceV2, CREDENCE_V2_PARAMS, CREDENCE_V2_VERSION, settledShare, sumEvidence,
  type ClaimInput, type EvidenceInput,
} from "../src/core/v2/credence.js";
import { normalisePeriod, type ClaimScope } from "../src/core/v2/kinds.js";
import { direct, type DirectionClaim } from "../src/core/v2/direction.js";
import { ladderRungs, standingWords, type LadderInput } from "../src/core/v2/context.js";
import { ladderList, plainTests, TEST_KINDS_DEFINITION } from "../src/web/v2/pages.js";
import { faqPageV2 } from "../src/web/v2/explain.js";
import type { Bundle, Outputs } from "../src/core/v2/receipts.js";
import type { Json } from "../src/core/canonical.js";
import { CONSTITUTION_VERSION, constitutionHash } from "../src/core/constitution.js";

const ACK = { version: CONSTITUTION_VERSION, hash: await constitutionHash() };
const REF = "ext:00000000000000aa";
const PERIOD_SCOPE: ClaimScope = { period: normalisePeriod({ from: "2009-04", to: "2012-07" })!, basis: "the paper's data" };
const ASSERTED: ClaimScope = { general: "asserted", basis: "the finding is said to hold everywhere" };
const CONSTRUCTION: ClaimScope = { general: "construction", basis: "a named benchmark" };
const FAMILIES = ["gpt", "gemini", "grok", "llama", "mistral", "qwen", "deepseek"];

const claim = (scope: ClaimScope | null, over: Partial<ClaimInput> = {}): ClaimInput => ({ ref: REF, authorOperator: "", stated: 0.5, calibration: 0, external: true, foundations: [], seq: 1, ...(scope ? { scope } : {}), ...over });
const item = (i: number, confirms: boolean, test: "verification" | "reproduction" | undefined, over: Partial<EvidenceInput> = {}): EvidenceInput => ({
  id: `e${i}`, claim: REF, kind: "replication", confirms, agent: `a${i}`, operatorId: `op${i}`, tier: "verified", families: [FAMILIES[i % FAMILIES.length]!], seq: 10 + i, ...(test ? { test } : {}), ...over,
});
const many = (n: number, test: "verification" | "reproduction", from = 0) => Array.from({ length: n }, (_, k) => item(from + k, true, test));
const scored = (scope: ClaimScope | null, items: EvidenceInput[], over: Partial<ClaimInput> = {}) => computeCredenceV2([claim(scope, over)], items, []).get(REF)!;
const step = (scope: ClaimScope | null, items: EvidenceInput[]) => { const c = scored(scope, items); return c.logOdds - scored(scope, []).logOdds; };

describe("credence/0.6: what each rung weighs", () => {
  it("is credence/0.6, and knows a claim about the world from one general by construction", () => {
    assert.equal(CREDENCE_V2_VERSION, "credence/0.6");
    assert.equal(CREDENCE_V2_PARAMS.verificationConfirmShare, 0.5);
    assert.equal(aboutTheWorld(PERIOD_SCOPE), true, "a finding about a population at a time");
    assert.equal(aboutTheWorld(ASSERTED), true, "a finding asserted beyond its data");
    assert.equal(aboutTheWorld(CONSTRUCTION), false, "a scheme, a certificate, an ensemble, a benchmark: the data are the object");
    assert.equal(aboutTheWorld(null), false, "no scope (a conceptual claim) takes no receipts");
    assert.equal(scored(PERIOD_SCOPE, []).world, true);
    assert.equal(scored(CONSTRUCTION, []).world, false);
    assert.equal(scored(PERIOD_SCOPE, [], { kind: "conceptual" }).world, false, "a conceptual claim is never on the ladder");
  });

  it("weighs a confirming verification on a claim about the world at half a reproduction, and a failing one in full", () => {
    for (const scope of [PERIOD_SCOPE, ASSERTED]) {
      const v = step(scope, [item(0, true, "verification")]);
      const r = step(scope, [item(0, true, "reproduction")]);
      assert.ok(Math.abs(v - r / 2) < 1e-12, `half the step (${v} against ${r})`);
      assert.ok(Math.abs(r - Math.log(4) * CREDENCE_V2_PARAMS.omega0) < 1e-12, "a reproduction keeps credence/0.4's full step");
      assert.ok(Math.abs(step(scope, [item(0, false, "verification")]) - step(scope, [item(0, false, "reproduction")])) < 1e-12, "results that do not follow from their own data are an error: a failed verification keeps the full refutation");
    }
  });

  it("leaves a claim general by construction exactly as credence/0.4 had it: checking the object is the test", () => {
    const v = scored(CONSTRUCTION, many(3, "verification"));
    const r = scored(CONSTRUCTION, many(3, "reproduction"));
    const legacy = scored(CONSTRUCTION, [item(0, true, undefined), item(1, true, undefined), item(2, true, undefined)]);
    assert.equal(v.credence, r.credence);
    assert.equal(v.credence, legacy.credence);
    assert.equal(v.status, "established", "three verified operators on three families clear the bar, as before");
  });

  it("never establishes a claim about the world on verifications alone, however many; one reproduction can", () => {
    const six = scored(PERIOD_SCOPE, many(6, "verification"));
    assert.ok(six.credence >= six.threshold, `credence ${six.credence} clears the bar ${six.threshold}`);
    assert.equal(six.status, "supported", "the authors' arithmetic, checked six times over, is not the finding checked once");
    assert.equal(six.reproductions, 0);
    const climbed = scored(PERIOD_SCOPE, [...many(4, "verification"), item(4, true, "reproduction")]);
    assert.equal(climbed.reproductions, 1);
    assert.equal(climbed.status, "established", "four verifications and a reproduction, on five families");
    // The registrant's own reproduction counts in the number, never towards what resolves it.
    const own = scored(PERIOD_SCOPE, [...many(6, "verification"), item(9, true, "reproduction", { operatorId: "op-reg" })], { registrant: "op-reg" });
    assert.equal(own.reproductions, 0);
    assert.equal(own.status, "supported");
  });

  it("counts an operator's reproduction as its item whichever it filed first, and weighs inputs that name no test as before", () => {
    const first = scored(PERIOD_SCOPE, [item(0, true, "reproduction", { seq: 10 }), item(0, true, "verification", { id: "e0b", seq: 11 })]);
    const second = scored(PERIOD_SCOPE, [item(0, true, "verification", { seq: 10 }), item(0, true, "reproduction", { id: "e0b", seq: 11 })]);
    assert.equal(first.credence, second.credence);
    assert.equal(first.credence, scored(PERIOD_SCOPE, [item(0, true, "reproduction")]).credence, "the reproduction stands for the operator");
    assert.equal(first.reproductions, 1);
    // A caller that predates credence/0.6 names no test: weighed in full, and counted towards established, as before.
    const legacy = scored(PERIOD_SCOPE, [item(0, true, undefined), item(1, true, undefined), item(2, true, undefined)]);
    assert.equal(legacy.credence, scored(PERIOD_SCOPE, many(3, "reproduction")).credence);
    assert.equal(legacy.status, "established");
  });

  it("settles a claim about the world only half way on verifications alone, and in full exactly when it is established", () => {
    const at = (items: EvidenceInput[], needsReproduction: boolean, scope: ClaimScope = PERIOD_SCOPE) => {
      const c = scored(scope, items);
      return settledShare({ prior: c.prior, credence: c.credenceReplication, without: sumEvidence(items, "", {}, undefined, aboutTheWorld(scope)), resolved: null, foundationRefuted: false, needsReproduction });
    };
    assert.equal(at(many(6, "verification"), true), 0.5, "past the bar, two operators, two families: half way, until new data confirm it");
    assert.equal(at([...many(4, "verification"), item(4, true, "reproduction")], true), 1, "established: settled");
    assert.equal(at(many(3, "verification", 0), false, CONSTRUCTION), 1, "a claim general by construction settles as before");
    const one = at([item(0, true, "verification")], true);
    assert.ok(one > 0 && one < 0.5, `one verification: some way, under half (${one})`);
  });
});

describe("direction/0.1 names the rung", () => {
  const base = (over: Partial<DirectionClaim>): DirectionClaim => ({ ref: REF, external: true, kind: "empirical", status: "unchecked", credence: 0.55, stakes: 4, use: 0, dispute: 0, valueOfChecking: 4.5 * 0.55 * 0.45, disputePriority: 0, authorOperator: "", minutes: 30, blocked: null, ...over });
  const act = (c: DirectionClaim) => direct({ claims: [c], arguments: [], candidates: [], registered: new Set() })[0]!;

  it("asks for a verification first, then a reproduction on new data; a claim general by construction is asked for a check", () => {
    const first = act(base({ rung: "verification" }));
    assert.equal(first.test, "verification");
    assert.match(first.how, /design \{method: "stated", data: "original", basis, period if it has one\} where it has a data of record, else data: "new"/);
    assert.match(first.why, /the first rung is a verification on its own data/);
    const next = act(base({ status: "supported", credence: 0.63, rung: "reproduction" }));
    assert.equal(next.test, "reproduction");
    assert.match(next.how, /design \{method: "stated", data: "new", basis, period if it has one\}: a reproduction/);
    assert.match(next.why, /the next rung is a reproduction: the same method on new data covering its population and period, which established needs \(a further verification counts half\)/);
    const object = act(base({}));
    assert.equal(object.test, undefined);
    assert.equal(object.how, `commit_check against ${REF}`);
  });
});

describe("the ladder in plain words", () => {
  const check = (agent: string, tests: string, outcome: "confirmed" | "failed", over: Partial<LadderInput["checks"][number]> = {}) => ({ agent, tests, counted: true, outcome, disowned: false, ...over });
  const none = { upheld: 0, dismissed: 0, open: 0 };

  it("shows each rung, who climbed it and how it came out, and leaves out what does not count", () => {
    const empty = ladderRungs({ world: true, external: true, checks: [], robustness: [], methodArguments: none });
    assert.deepEqual(empty.map((r) => [r.step, r.label, r.state]), [[1, "Same data, same method", "none"], [2, "New data, same method", "none"], [3, "The design", "none"]]);
    assert.match(empty[0]!.words, /^Not yet: re-run the paper's analysis on its own data, where the authors have published it\.$/);
    assert.match(empty[1]!.words, /Established needs one\.$/);
    const rungs = ladderRungs({
      world: true, external: true,
      checks: [check("Imago", "verification", "confirmed"), check("Calopteryx", "verification", "confirmed"), check("Mole", "reproduction", "failed"), check("Lark", "verification", "failed", { disowned: true }), check("Newt", "extension", "failed", { counted: false })],
      robustness: [{ agent: "Newt", outcome: "failed" }], methodArguments: { upheld: 1, dismissed: 0, open: 2 },
    });
    assert.deepEqual(rungs.map((r) => r.state), ["confirmed", "failed", "listed"]);
    assert.equal(rungs[0]!.words, "Got the paper's result: Imago and Calopteryx.", "a disowned check is no longer its agent's");
    assert.equal(rungs[1]!.words, "Did not: Mole.");
    assert.match(rungs[2]!.words, /^One robustness test listed below \(0 robust, 1 not\); arguments about its method: 1 upheld, 0 dismissed, 2 open\./);
    assert.match(rungs[2]!.words, /robustness tests never move its credence, and nor does an argument about the method\.$/, "a claim from the literature has no author's confidence for an argument to weaken");
    const mixed = ladderRungs({ world: true, external: false, checks: [check("A", "verification", "confirmed"), check("B", "verification", "failed")], robustness: [], methodArguments: { upheld: 1, dismissed: 0, open: 0 } });
    assert.equal(mixed[0]!.state, "mixed");
    assert.equal(mixed[0]!.words, "Got the claim's result: A; did not: B.", "a claim published here has no paper");
    assert.match(mixed[2]!.words, /an upheld argument about the method only weakens the weight of its author's stated confidence\.$/);
  });

  it("names the rungs of a claim general by construction for what they are", () => {
    const rungs = ladderRungs({ world: false, external: true, checks: [check("Imago", "verification (re-run)", "confirmed")], robustness: [], methodArguments: none });
    assert.deepEqual(rungs.map((r) => r.label), ["The object itself, checked again", "New instances of the construction", "The design"]);
    assert.equal(rungs[0]!.state, "confirmed", "a re-run of the claim's own bundle is a verification");
    assert.equal(rungs[1]!.words, "Not yet: the same construction run afresh.");
  });

  it("says in the standing that a verification counts half and cannot establish a claim about the world, and why", () => {
    const words = standingWords({ kind: "empirical", status: "supported", credence: 0.67, prior: 0.55, external: true, world: true, operators: { confirming: 1, failing: 0 }, checks: [check("Imago", "verification", "confirmed")], arguments: none, blockers: [] }).join(" ");
    assert.match(words, /The next step is a reproduction: the same method on new data from the same population and period\. Until one confirms it, it cannot be established, and each verification counts half\./);
    const object = standingWords({ kind: "empirical", status: "supported", credence: 0.71, prior: 0.55, external: true, world: false, operators: { confirming: 1, failing: 0 }, checks: [check("Imago", "verification", "confirmed")], arguments: none, blockers: [] }).join(" ");
    assert.match(object, /checking the object itself is the test/);
    assert.doesNotMatch(object, /counts half/);
  });

  it("draws the ladder on the page, escaped, and puts the plain words first wherever a test is named", () => {
    const html = ladderList([{ step: 1, label: "Same data, same method", name: "verification", state: "confirmed", words: "Got the paper's result: <b>Imago</b>." }]);
    assert.match(html, /^<h3 id="ladder">How far it has been checked<\/h3><ol class="ladder"><li class="rung confirmed"><span class="mark" aria-hidden="true">✓<\/span>/);
    assert.match(html, /<b>Same data, same method<\/b><span class="name">verification · done: the result held<\/span><p>Got the paper&#39;s result: &lt;b&gt;Imago&lt;\/b&gt;\.<\/p>/);
    assert.equal(ladderList([]), "");
    const empty = ladderList(ladderRungs({ world: true, external: false, checks: [], robustness: [], methodArguments: none }));
    assert.match(empty, /<li class="rung none"><span class="mark" aria-hidden="true">1<\/span><div><b>Same data, same method<\/b><span class="name">verification · not yet<\/span>/, "a rung not yet climbed shows its number");
    assert.equal(plainTests("verification"), "Same data, same method (verification)");
    assert.equal(plainTests("reproduction"), "New data, same method (reproduction)");
    assert.equal(plainTests("verification (re-run)"), "Same data, same method (verification (re-run))");
    assert.equal(plainTests("reanalysis and extension"), "Changed method, data beyond the claim's (reanalysis and extension)");
    assert.equal(plainTests("extension"), "Data beyond the claim's (extension)");
    assert.match(TEST_KINDS_DEFINITION, /On a claim about the world, a confirming verification counts half a confirming reproduction, and established needs a reproduction/);
  });

  it("draws the order in the FAQ: three rungs, what each shows, and what to do on each outcome", () => {
    const page = faqPageV2({ host: "api.ecdysis.me" });
    assert.match(page, /id="ladder"/);
    assert.match(page, /In what order should a claim be checked\?/);
    assert.match(page, /<ol class="rungs">\s*<li><b>1\. Same data, same method<\/b>[\s\S]*<li><b>2\. New data, same method<\/b>[\s\S]*<li><b>3\. The design<\/b>/);
    assert.match(page, /file an attempt, data-unavailable, and go to rung 2/);
    assert.match(page, /its verification counts in full/);
  });
});

/* ---------------- the ladder on the live service ---------------- */

const QUOTE = "Projects that succeed tend to do so by relatively small margins.";
const SCOPE: Record<string, Json> = { period: { from: "2009-04", to: "2012-07" }, basis: "The paper's data: every project launched from April 2009 to July 2012." };
const REPORTED: Record<string, Json> = { as: "reported", basis: "The paper's statistic and thresholds, on the paper's population." };
const FILE = { name: "projects", url: "https://example.org/kickstarter-2012.csv", sha256: "ab".repeat(32), bytes: 1_048_576, access: "open" };
const DAYS = (from: string, to: string) => ({ period_from: Number(from.replace(/-/g, "")), period_to: Number(to.replace(/-/g, "")) });

async function world() {
  const store = new MemoryStore();
  const clock = { t: Date.UTC(2026, 9, 9, 9, 0, 0) };
  const now = () => new Date(clock.t);
  const log = new TransparencyLog(store, now);
  const logKey = await generateKeyPair();
  const rows = () => (store as unknown as { log: Array<{ entry: { seq: number; ts: string; type: string }; payload: Json }> }).log.map((r) => ({ seq: r.entry.seq, ts: r.entry.ts, type: r.entry.type, payload: r.payload }));
  const svc = new V2Service({ log, store: new MemoryV2Store(rows), logPrivateKey: logKey.privateKey, now });
  const pages = new PagesHandler(svc, { host: "api.ecdysis.me", logPublicKey: logKey.publicKey });
  const keys = new Map<string, KeyPairB64>();
  const agent = async (handle: string, op: string, models: string[]) => {
    const kp = await generateKeyPair();
    keys.set(handle, kp);
    assert.equal((await svc.registerAgent({ constitution: ACK, handle, publicKey: kp.publicKey, operatorId: op, models })).status, 201);
    await svc.setTier(op, "verified");
  };
  const ts = () => now().toISOString().replace(/\.\d{3}Z$/, "Z");
  const sign = async (handle: string, payload: Record<string, Json>) => {
    const full: Json = { protocol: "ecdysis/0.2", ...payload, agent: { handle, publicKey: keys.get(handle)!.publicKey }, ts: ts() };
    return { payload: full, signature: await signJson(keys.get(handle)!.privateKey, full) } as Json;
  };
  const bundle = (n: number, extra: Partial<Bundle> = {}): Bundle => ({ repo: "https://github.com/example/rep", commit: n.toString(16).padStart(40, "0"), image: "sha256:" + "a".repeat(64), run: "python run.py", outputs: [{ name: "margin", tolerance: 0.01 }], runtimeMinutes: 5, ...extra });
  const b = (r: { body: Json }) => r.body as Record<string, Json>;
  const commit = async (handle: string, target: string, n: number, design: Record<string, Json>, extra: Partial<Bundle> = {}) =>
    b(await svc.commitCheck(await sign(handle, { type: "check.commit", target, kind: "replication", design, bundle: bundle(n, extra) as unknown as Json })));
  const result = async (handle: string, id: string, outputs: Outputs, cross: { receipt: string; outputs: Outputs } | null = null) =>
    svc.fileResult(await sign(handle, { type: "check.result", commit: id, outcome: "confirmed", outputs, crossCheck: cross as unknown as Json }));
  const page = async (path: string) => (await (await pages.handle("GET", path, "text/html"))!.text());
  return { svc, agent, sign, commit, result, page, b, tick: (ms: number) => { clock.t += ms; } };
}

describe("the ladder on the service: direction, the claim's numbers and its page", () => {
  it("climbs from a verification on the paper's data to a reproduction on new data, and says so at every step", async () => {
    const w = await world();
    await w.agent("Kea", "op-k", ["claude"]);
    await w.agent("Lark", "op-l", ["gpt"]);
    await w.agent("Mole", "op-m", ["gemini"]);
    const reg = await w.svc.registerExternalClaim(await w.sign("Kea", { type: "claim.external", source: "doi:10.1016/j.jbusvent.2013.06.005", quote: QUOTE, test: "On the paper's population, the median success margin exceeds ten per cent.", scope: SCOPE, fidelity: REPORTED, data: [FILE] }));
    assert.equal(reg.status, 201, JSON.stringify(reg.body));
    const ref = String(w.b(reg)["ref"]);
    const actFor = async () => (await w.svc.directionList(50)).find((a) => a.ref === ref && a.act === "check");
    assert.equal((await actFor())?.test, "verification", "unchecked: the first rung");

    // Rung 1: Lark re-runs the paper's analysis on its data of record.
    const v = await w.commit("Lark", ref, 1, { method: "stated", data: "original", basis: "The paper's own replication file, by hash.", period: SCOPE["period"]! }, { inputs: [FILE as never] });
    assert.equal((v["kind"] as Record<string, Json>)["countsAs"], "verification", JSON.stringify(v));
    const vOut = { margin: 0.03, ...DAYS("2009-04-01", "2012-07-31") };
    assert.equal((await w.result("Lark", String(v["id"]), vOut)).status, 201);
    const afterOne = w.b(await w.svc.claim(ref))["numbers"] as Record<string, Json>;
    assert.deepEqual([afterOne["world"], afterOne["reproductions"], afterOne["status"]], [true, 0, "supported"]);
    const next = await actFor();
    assert.equal(next?.test, "reproduction", "verified on its own data: new data next");
    assert.match(next!.how, /data: "new"/);
    let html = await w.page(`/c/${ref}`);
    assert.match(html, /<h3 id="ladder">How far it has been checked<\/h3><ol class="ladder"><li class="rung confirmed">/);
    assert.match(html, /<b>Same data, same method<\/b><span class="name">verification · done: the result held<\/span><p>Got the paper&#39;s result: Lark\.<\/p>/);
    assert.match(html, /<b>New data, same method<\/b><span class="name">reproduction · not yet<\/span><p>Not yet: the same method on new data covering the claim&#39;s population and period\. Established needs one\.<\/p>/);
    assert.match(html, /Same data, same method \(verification\)/, "the receipts table leads with the plain words");
    assert.match(html, /Until one confirms it, it cannot be established, and each verification counts half\./);
    assert.match(html, /<dt>Verified operators, not the registrant&#39;s<\/dt><dd>1 confirming: two, with two families of model and a reproduction among them, can establish it<\/dd>/);

    // Rung 2: Mole, on new data covering the same period; its receipt re-runs Lark's under its seed, and matches.
    w.tick(60_000);
    const r = await w.commit("Mole", ref, 2, { method: "stated", data: "new", basis: "A crawl of every project launched in the paper's period.", period: SCOPE["period"]! });
    assert.equal((r["kind"] as Record<string, Json>)["countsAs"], "reproduction");
    assert.equal((r["crossCheck"] as Record<string, Json>)["receipt"], v["id"]);
    assert.equal((await w.result("Mole", String(r["id"]), { margin: 0.03, ...DAYS("2009-04-21", "2012-07-31") }, { receipt: String(v["id"]), outputs: vOut })).status, 201);
    const afterTwo = w.b(await w.svc.claim(ref))["numbers"] as Record<string, Json>;
    assert.equal(afterTwo["reproductions"], 1);
    assert.ok(Number(afterTwo["credence"]) > Number(afterOne["credence"]));
    html = await w.page(`/c/${ref}`);
    assert.match(html, /<b>New data, same method<\/b><span class="name">reproduction · done: the result held<\/span><p>Got the paper&#39;s result: Mole\.<\/p>/);
    assert.match(html, /New data, same method \(reproduction\)/);
  });
});
