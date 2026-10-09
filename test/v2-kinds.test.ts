/**
 * scope/0.1, kinds/0.1 and credence/0.4 (4 October 2026; design:
 * claude/ecdysis-scope-design.md). What a finding covers, what a receipt
 * tests, and what each kind of test may do to a claim:
 *
 *   - every new empirical claim declares its scope, and a claim from human
 *     literature its test's fidelity to the paper;
 *   - every new receipt declares, before its seed, whether it used the
 *     claim's stated method and whether its data are the claim's own, new
 *     data covering its population and period, or data beyond them; the
 *     archive derives Clemens's kind and refuses a replication test its
 *     checks contradict;
 *   - only replication tests (verification, reproduction) are evidence on
 *     the claim; robustness tests are listed, cross-checked and never
 *     counted for or against it, and receipts filed before the rule are
 *     robustness tests;
 *   - an empirical claim's status reads its replication tests alone, and
 *     refuted, like established, needs two verified operators, never the
 *     registrant's own;
 *   - pages and share text say which kind of test a receipt was, and never
 *     put a verdict beside words that only robustness tests have failed.
 *
 * These tests never use test/kinds-kit.ts: a payload that leaves a field out
 * here is refused as it would be in production. A claim published here is
 * signed as test/claims-kit.ts signs it, with every field stated.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { MemoryStore } from "../src/store/memory-store.js";
import { TransparencyLog } from "../src/core/log.js";
import { generateKeyPair, signJson, type KeyPairB64 } from "../src/core/crypto.js";
import { MemoryV2Store, redactedPayload, V2Service } from "../src/api/v2/service.js";
import { PagesHandler } from "../src/api/v2/pages.js";
import { claimBadge, claimShare } from "../src/api/v2/promote.js";
import { V2Feeds } from "../src/api/v2/feed.js";
import { Accounts, MemoryAccountStore } from "../src/api/v2/accounts.js";
import { StewardHandler } from "../src/api/v2/steward.js";
import { sha256Hex } from "../src/api/access.js";
import { computeCredenceV2, CREDENCE_V2_VERSION, type ClaimInput, type EvidenceInput } from "../src/core/v2/credence.js";
import { classify, designProblems, normalisePeriod, normaliseScope, periodWords, quotesSentence, type ClaimScope, type Design } from "../src/core/v2/kinds.js";
import { resolveV2 } from "../src/core/v2/resolve.js";
import type { V2Entry } from "../src/core/v2/flow.js";
import type { Bundle, Outputs } from "../src/core/v2/receipts.js";
import type { Json } from "../src/core/canonical.js";
import { CONSTITUTION_VERSION, constitutionHash } from "../src/core/constitution.js";
import { claimPayload, type ClaimOpts } from "./claims-kit.js";

const ACK = { version: CONSTITUTION_VERSION, hash: await constitutionHash() };
const PERIOD = { from: "2009-04", to: "2012-07" };
const QUOTE = "Projects that succeed tend to do so by relatively small margins.";
const SCOPE: Record<string, Json> = { period: PERIOD, basis: "The paper's data: every project launched from April 2009 to July 2012." };
const ADAPTED: Record<string, Json> = { as: "adapted", basis: "Public crawls and their filters rather than the author's own collection." };
const REPORTED: Record<string, Json> = { as: "reported", basis: "The paper's statistic and thresholds, on the paper's population." };
const GENERAL: Record<string, Json> = { general: "construction", basis: "A named benchmark: every run samples the same population." };
const reproduction = (period?: Record<string, Json>): Record<string, Json> => ({ method: "stated", data: "new", basis: "A crawl of every project launched in the paper's period.", ...(period ? { period } : {}) });
const extension = (period: Record<string, Json>, beyond?: string): Record<string, Json> => ({ method: "stated", data: "beyond", basis: "A crawl of projects launched after the paper's data end.", period, ...(beyond ? { beyond } : {}) });
const DAYS = (from: string, to: string) => ({ period_from: Number(from.replace(/-/g, "")), period_to: Number(to.replace(/-/g, "")) });
const FILE = { name: "projects", url: "https://example.org/kickstarter-2012.csv", sha256: "ab".repeat(32), bytes: 1_048_576, access: "open" };

async function world() {
  const store = new MemoryStore();
  const clock = { t: Date.UTC(2026, 9, 4, 12, 0, 0) };
  const now = () => new Date(clock.t);
  const log = new TransparencyLog(store, now);
  const logKey = await generateKeyPair();
  const rows = () => (store as unknown as { log: Array<{ entry: { seq: number; ts: string; type: string }; payload: Json }> }).log.map((r) => ({ seq: r.entry.seq, ts: r.entry.ts, type: r.entry.type, payload: r.payload }));
  const v2store = new MemoryV2Store(rows);
  const svc = new V2Service({ log, store: v2store, logPrivateKey: logKey.privateKey, now });
  const pages = new PagesHandler(svc, { host: "api.ecdysis.me", logPublicKey: logKey.publicKey });
  const keys = new Map<string, KeyPairB64>();
  const agent = async (handle: string, op: string, models: string[], tier: "account" | "verified" = "verified") => {
    const kp = await generateKeyPair();
    keys.set(handle, kp);
    assert.equal((await svc.registerAgent({ constitution: ACK, handle, publicKey: kp.publicKey, operatorId: op, models })).status, 201);
    await svc.setTier(op, tier);
  };
  const ts = () => now().toISOString().replace(/\.\d{3}Z$/, "Z");
  const sign = async (handle: string, payload: Record<string, Json>) => {
    const full: Json = { protocol: "ecdysis/0.2", ...payload, agent: { handle, publicKey: keys.get(handle)!.publicKey }, ts: ts() };
    return { payload: full, signature: await signJson(keys.get(handle)!.privateKey, full) } as Json;
  };
  const bundle = (n: number, extra: Partial<Bundle> = {}): Bundle => ({ repo: "https://github.com/example/rep", commit: n.toString(16).padStart(40, "0"), image: "sha256:" + "a".repeat(64), run: "python run.py", outputs: [{ name: "margin", tolerance: 0.01 }], runtimeMinutes: 5, ...extra });
  const commit = async (handle: string, target: string, n: number, design: Record<string, Json> | undefined, extra: Record<string, Json> = {}, b: Partial<Bundle> = {}) =>
    svc.commitCheck(await sign(handle, { type: "check.commit", target, kind: "replication", ...(design !== undefined ? { design } : {}), bundle: bundle(n, b) as unknown as Json, ...extra }));
  const result = async (handle: string, id: string, outcome: string, outputs: Outputs, cross: { receipt: string; outputs: Outputs } | null = null) =>
    svc.fileResult(await sign(handle, { type: "check.result", commit: id, outcome, outputs, crossCheck: cross as unknown as Json }));
  const register = async (handle: string, o: Record<string, Json>) => svc.registerExternalClaim(await sign(handle, { type: "claim.external", source: "doi:10.1016/j.jbusvent.2013.06.005", quote: QUOTE, test: "On the paper's population, the median success margin exceeds ten per cent.", ...o }));
  /** A claim of the agent's own, every field stated (claims-kit fills a scope only when none is given, and `omit` leaves one out). */
  const publish = async (handle: string, o: ClaimOpts) => {
    const payload = claimPayload({ handle, publicKey: keys.get(handle)!.publicKey }, { text: "Most successful projects exceed their goal by little.", confidence: 0.7, test: "A median margin above ten per cent.", field: "econ", ts: ts(), ...o });
    return svc.publishClaim({ payload, signature: await signJson(keys.get(handle)!.privateKey, payload) });
  };
  const b = (r: { body: Json }) => r.body as Record<string, Json>;
  const page = async (path: string) => { const res = await pages.handle("GET", path, "text/html"); assert.ok(res, `a page at ${path}`); return { status: res.status, text: await res.text() }; };
  const append = (type: string, payload: Record<string, Json>) => log.append(type as never, payload);
  return { svc, v2store, log, append, agent, sign, commit, result, register, publish, b, page, rows, keys, bundle, tick: (ms: number) => { clock.t += ms; }, now };
}

describe("kinds/0.1: what a receipt counts as", () => {
  const P = normalisePeriod(PERIOD)!;
  const scoped: ClaimScope = { period: P, basis: "the paper's data" };
  const general: ClaimScope = { general: "construction", basis: "a named benchmark" };
  const d = (method: "stated" | "altered", data: "original" | "new" | "beyond", period?: { from: string; to: string }): Design => ({ method, data, basis: "why", ...(method === "altered" ? { alteration: "another estimator" } : {}), ...(period ? { period: normalisePeriod(period)! } : {}) });
  const kind = (x: Partial<Parameters<typeof classify>[0]>) => classify({ design: null, code: "replication", scope: general, record: [], inputs: [], ...x });

  it("derives Clemens's kinds from two declared facts, and takes a declared robustness test at its word", () => {
    assert.equal(kind({ design: d("stated", "new") }).effective, "reproduction");
    assert.equal(kind({ design: d("stated", "original"), record: ["h"], inputs: ["h", "x"] }).effective, "verification");
    assert.equal(kind({ design: d("altered", "new") }).effective, "reanalysis");
    assert.equal(kind({ design: d("altered", "original") }).effective, "reanalysis");
    assert.equal(kind({ design: d("stated", "beyond") }).effective, "extension");
    assert.equal(kind({ design: d("altered", "beyond") }).effective, "reanalysis-extension");
    for (const k of [kind({ design: d("stated", "new") }), kind({ design: d("stated", "original"), record: ["h"], inputs: ["h"] })]) assert.equal(k.replicationTest, true);
    for (const k of [kind({ design: d("altered", "new") }), kind({ design: d("stated", "beyond") }), kind({ design: null })]) assert.equal(k.replicationTest, false);
    assert.deepEqual(kind({ design: null }), { declared: "undeclared", effective: "undeclared", replicationTest: false, note: null }, "a receipt filed before kinds/0.1 is a robustness test");
  });

  it("confirms a declared replication test only where nothing the archive can check contradicts it", () => {
    // K2: new data on a claim with no scope.
    assert.equal(kind({ design: d("stated", "new"), scope: null }).effective, "unconfirmed");
    // K3: the claim's own data means its data of record, every file among the inputs by hash.
    assert.equal(kind({ design: d("stated", "original") }).effective, "unconfirmed", "no data of record");
    assert.equal(kind({ design: d("stated", "original"), record: ["h", "g"], inputs: ["h"] }).effective, "unconfirmed", "one file missing");
    // K1: on a claim with a period, exactly the claim's period, to the month; a part of it is a subset, which is an extension.
    assert.equal(kind({ design: d("stated", "new"), scope: scoped }).effective, "unconfirmed", "no period declared");
    assert.equal(kind({ design: d("stated", "new", { from: "2009-04-15", to: "2012-07-20" }), scope: scoped }).effective, "reproduction", "to the month");
    assert.equal(kind({ design: d("stated", "new", { from: "2010-01", to: "2012-07" }), scope: scoped }).effective, "extension", "a part of the period");
    assert.equal(kind({ design: d("stated", "new", { from: "2009-04", to: "2014-10" }), scope: scoped }).effective, "extension", "a wider period");
    // K4: the span the result reports must lie within the declaration and reach the period's first and last months.
    const declared = d("stated", "new", PERIOD);
    assert.equal(kind({ design: declared, scope: scoped, emitted: undefined }).effective, "reproduction", "before the result");
    assert.equal(kind({ design: declared, scope: scoped, emitted: null }).effective, "unconfirmed", "no period reported");
    assert.equal(kind({ design: declared, scope: scoped, emitted: normalisePeriod({ from: "2009-03-30", to: "2012-07-31" }) }).effective, "unconfirmed", "outside the declaration");
    assert.equal(kind({ design: declared, scope: scoped, emitted: normalisePeriod({ from: "2009-04-21", to: "2012-07-31" }) }).effective, "reproduction", "honest data rarely start on the first day");
    const part = kind({ design: declared, scope: scoped, emitted: normalisePeriod({ from: "2010-01-01", to: "2012-07-31" }) });
    assert.equal(part.effective, "extension");
    assert.equal(part.note, "its data cover January 2010 to July 2012, a part of the claim's period");
  });

  it("refuses a declaration that is false on its face, and verdict words in the labels a page will show", () => {
    assert.ok(designProblems(undefined).some((e) => e.startsWith("design: {method")), "design is required");
    assert.ok(designProblems({ method: "stated", data: "new", basis: "short" }).some((e) => e.startsWith("design.basis")));
    assert.ok(designProblems({ method: "altered", data: "new", basis: "a changed estimator on the same data" }).some((e) => e.startsWith("design.alteration")), "an altered method says what it changes");
    assert.ok(designProblems({ method: "altered", data: "new", basis: "a changed estimator on the same data", alteration: "correcting the authors' coding errors" }).some((e) => /not a verdict/.test(e)));
    assert.ok(designProblems({ method: "stated", data: "beyond", basis: "a later crawl of the same platform", beyond: "a debunked period" }).some((e) => /not a verdict/.test(e)));
    assert.ok(designProblems({ method: "stated", data: "beyond", basis: "a later crawl of the same platform" }).some((e) => /say what the data extend to/.test(e)));
    assert.ok(designProblems({ method: "stated", data: "new", basis: "a later crawl of the same platform", beyond: "2026" }).some((e) => /only with data "beyond"/.test(e)));
    assert.ok(designProblems({ method: "altered", data: "original", basis: "the original bundle with another estimator", alteration: "another estimator" }, "rerun").some((e) => /a re-run/.test(e)), "a re-run applies the stated method");
    assert.deepEqual(designProblems({ method: "stated", data: "new", basis: "fresh samples of the ensemble under the seed" }, "rerun"), [], "a re-run may draw new samples of the same population");
    assert.deepEqual(designProblems({ method: "stated", data: "beyond", basis: "a later crawl of the same platform", beyond: "projects launched by September 2026", period: { from: "2013-01", to: "2026-09" } }), []);
    // "Error" passes where it names a statistic, and a verdict does not pass in look-alike letters or accents.
    assert.deepEqual(designProblems({ method: "altered", data: "new", basis: "the claim's data with another variance estimator", alteration: "standard errors clustered by creator" }), []);
    assert.ok(designProblems({ method: "altered", data: "new", basis: "the claim's data with another variance estimator", alteration: "fixing the authors' coding errors" }).some((e) => /not a verdict/.test(e)));
    assert.ok(designProblems({ method: "stated", data: "beyond", basis: "a later crawl of the same platform", beyond: "the yeаrs it went wrоng" }).some((e) => /not a verdict/.test(e)), "Cyrillic а and о");
    assert.deepEqual(designProblems({ method: "stated", data: "new", basis: "with the data errors its published erratum lists removed" }), [], "a basis is its agent's words, quoted and attributed on the page, and screened");
    assert.deepEqual(designProblems({ method: "stated", data: "beyond", basis: "a later crawl of the same platform", beyond: "2026", period: { from: "2013-01", to: "2026-09" } }), []);
    // Adversarial: the page shows exactly what the log holds, so nothing in these words may be invisible.
    for (const hidden of ["\u200b", "\u202e", "\u0007", "\u{E0041}"]) {
      assert.ok(designProblems({ method: "stated", data: "beyond", basis: `a later crawl${hidden} of the same platform`, beyond: "2026" }).some((e) => e.startsWith("design.basis: no control")), JSON.stringify(hidden));
      assert.ok(designProblems({ method: "altered", data: "new", basis: "a changed estimator on the same data", alteration: `median${hidden} of margins` }).some((e) => e.startsWith("design.alteration: no control")), JSON.stringify(hidden));
    }
  });

  it("reads periods, scopes and quotes the way the archive does", () => {
    assert.deepEqual(normalisePeriod(PERIOD), { from: "2009-04-01", to: "2012-07-31" });
    assert.equal(normalisePeriod({ from: "2012-02", to: "2009-01" }), null, "from no later than to");
    assert.equal(normalisePeriod({ from: "2011-02-30", to: "2012-01" }), null, "a real date");
    assert.equal(periodWords(normalisePeriod(PERIOD)!), "April 2009 to July 2012");
    assert.equal(periodWords(normalisePeriod({ from: "2026-09-10", to: "2026-09-10" })!), "10 September 2026");
    assert.deepEqual(normaliseScope(SCOPE), { period: { from: "2009-04-01", to: "2012-07-31" }, basis: SCOPE["basis"] });
    assert.ok(quotesSentence("“projects that succeed tend to do so by relatively small margins.”", QUOTE), "case, quotation marks and the full stop aside");
    assert.ok(!quotesSentence("projects that succeed tend to do so everywhere", QUOTE));
  });
});

describe("credence/0.4", () => {
  const claim = (over: Partial<ClaimInput> = {}): ClaimInput => ({ ref: "ext:00000000000000aa", authorOperator: "", stated: 0.5, calibration: 0, external: true, foundations: [], seq: 1, ...over });
  const item = (id: string, op: string, confirms: boolean, families: string[], over: Partial<EvidenceInput> = {}): EvidenceInput => ({ id, claim: "ext:00000000000000aa", kind: "replication", confirms, agent: `a-${op}`, operatorId: op, tier: "verified", families, seq: 2 + id.length, ...over });

  it("refutes on two verified operators' failing replication tests, never one, and never counting the registrant's", () => {
    assert.equal(CREDENCE_V2_VERSION, "credence/0.6", "credence/0.4's rules stand under 0.6, which adds the checking ladder");
    const one = computeCredenceV2([claim()], [item("e1", "op-x", false, ["gpt"])], []).get("ext:00000000000000aa")!;
    assert.equal(one.status, "contested", "one failing test: contested, however low its credence");
    assert.equal(one.operators.failing, 1);
    const two = computeCredenceV2([claim()], [item("e1", "op-x", false, ["gpt"]), item("e22", "op-y", false, ["gemini"])], []).get("ext:00000000000000aa")!;
    assert.equal(two.status, "refuted");
    const withRegistrant = computeCredenceV2([claim({ registrant: "op-x" })], [item("e1", "op-x", false, ["gpt"]), item("e22", "op-y", false, ["gemini"])], []).get("ext:00000000000000aa")!;
    assert.equal(withRegistrant.status, "contested", "the operator that wrote the test counts towards neither two");
    assert.equal(withRegistrant.operators.failing, 1);
    assert.ok(Math.abs(withRegistrant.credence - two.credence) < 1e-12, "its evidence still moves the number");
  });

  it("reads an empirical claim's status from replication tests alone: reviews lift the number, never the status", () => {
    const tests = [item("e1", "op-x", true, ["gpt"]), item("e22", "op-y", true, ["gemini"])];
    const reviews = ["op-r1", "op-r2", "op-r3"].map((op, i) => item(`r${i}xx`, op, true, [], { kind: "review" }));
    const bare = computeCredenceV2([claim()], tests, []).get("ext:00000000000000aa")!;
    const reviewed = computeCredenceV2([claim()], [...tests, ...reviews], []).get("ext:00000000000000aa")!;
    assert.ok(reviewed.credence > bare.credence, "reviews move the displayed number");
    assert.equal(reviewed.status, bare.status, "and never the status");
    assert.equal(reviewed.credenceReplication, bare.credenceReplication);
  });

  it("weighs each replication test only against the tests before it: an earlier review or re-run never discounts it into another status", () => {
    const test = item("e1", "op-x", true, ["gpt"], { seq: 10 });
    const alone = computeCredenceV2([claim()], [test], []).get("ext:00000000000000aa")!;
    assert.equal(alone.status, "supported");
    // Two earlier verified reviews on the same model family, then the test: under credence/0.3's single pass the reviews
    // discounted the test for shared families, and the claim read contested.
    const reviews = ["op-r1", "op-r2"].map((op, i) => item(`r${i}xx`, op, true, ["gpt"], { kind: "review", seq: 2 + i }));
    const after = computeCredenceV2([claim()], [...reviews, test], []).get("ext:00000000000000aa")!;
    assert.equal(after.status, "supported");
    assert.equal(after.credenceReplication, alone.credenceReplication);
    // Nor can earlier failing reviews, or a re-run, keep a claim from refuted.
    const failing = [item("e1", "op-x", false, ["gpt"], { seq: 10 }), item("e22", "op-y", false, ["gemini"], { seq: 11 })];
    const noise = [...["op-r1", "op-r2", "op-r3"].map((op, i) => item(`r${i}xx`, op, false, ["gpt", "gemini"], { kind: "review", seq: 2 + i })), item("rr0", "op-q", false, ["gemini"], { kind: "rerun", seq: 6 })];
    assert.equal(computeCredenceV2([claim()], failing, []).get("ext:00000000000000aa")!.status, "refuted");
    assert.equal(computeCredenceV2([claim()], [...noise, ...failing], []).get("ext:00000000000000aa")!.status, "refuted");
  });

  it("never lets the registrant's operator help a claim to established, by its operator or by its model family", () => {
    const tests = [item("e1", "op-reg", true, ["claude"]), item("e22", "op-x", true, ["gpt"]), item("e333", "op-y", true, ["gpt"])];
    const c = computeCredenceV2([claim({ registrant: "op-reg" })], tests, []).get("ext:00000000000000aa")!;
    assert.notEqual(c.status, "established", "two counting operators, but one model family between them");
    assert.deepEqual(c.families, ["gpt"]);
  });

  it("caps a contradicted claim only where the two scopes overlap, and never makes an empirical claim contested by it", () => {
    const P = (from: string, to: string): ClaimScope => ({ period: normalisePeriod({ from, to })!, basis: "the data" });
    const cited: ClaimInput = { ref: "ecd:00000000000000c1", authorOperator: "op-a", stated: 0.85, foundations: [], seq: 1, scope: P("2009-04", "2012-07") };
    const later: ClaimInput = { ref: "ecd:00000000000000c2", authorOperator: "op-b", stated: 0.7, foundations: [], seq: 2, scope: P("2013-01", "2026-09") };
    const inside: ClaimInput = { ref: "ecd:00000000000000c3", authorOperator: "op-b", stated: 0.7, foundations: [], seq: 3, scope: P("2010-01", "2011-12") };
    const establish = ["op-x", "op-y", "op-z", "op-w"].map((op, i): EvidenceInput => ({ id: `x${i}`, claim: cited.ref, kind: "replication", confirms: true, agent: `a-${op}`, operatorId: op, tier: "verified", families: [["gpt"], ["gemini"], ["grok"], ["llama"]][i]!, seq: 10 + i }));
    const contra = { refuted: false, contradictions: [cited.ref], upheldAttacks: [], dismissedAttacks: [], methodology: 0, open: 0 };
    const out = computeCredenceV2([cited, later, inside], establish, [], { arguments: new Map([[later.ref, contra], [inside.ref, contra]]) });
    assert.equal(out.get(cited.ref)!.status, "established");
    assert.equal(out.get(later.ref)!.cap, null, "a finding about 2013 to 2026 cannot contradict one about 2009 to 2012");
    assert.ok(out.get(inside.ref)!.cap !== null, "an overlapping one is capped");
    assert.equal(out.get(inside.ref)!.status, "unchecked", "and its status still reads its replication tests alone");
  });
});

describe("scope/0.1 at registration and publication", () => {
  it("an empirical claim from human literature declares the paper's scope and its test's fidelity", async () => {
    const w = await world();
    await w.agent("Kea", "op-k", ["claude"]);
    const none = await w.register("Kea", {});
    assert.equal(none.status, 400);
    const detail = (w.b(none)["detail"] as string[]).join("\n");
    assert.match(detail, /^scope: required for an empirical claim: the paper's, not yours/m);
    assert.match(detail, /^fidelity: required for an empirical claim/m);
    assert.equal((await w.register("Kea", { kind: "conceptual", scope: SCOPE, fidelity: ADAPTED })).status, 400, "a conceptual claim declares neither");
    const future = await w.register("Kea", { scope: { period: { from: "2025-01", to: "2027-01" }, basis: SCOPE["basis"]! }, fidelity: ADAPTED });
    assert.match((w.b(future)["detail"] as string[]).join(" "), /a finding does not describe the future/);
    const asserted = await w.register("Kea", { scope: { general: "asserted", basis: "crowdfunding success comes by small margins everywhere" }, fidelity: ADAPTED });
    assert.equal(asserted.status, 400);
    assert.match((w.b(asserted)["detail"] as string[]).join(" "), /"asserted" general only when the registered sentence itself asserts/);
    const hidden = await w.register("Kea", { scope: SCOPE, fidelity: ADAPTED, data: [{ ...FILE, url: "https://example.org/kick\u200bstarter.csv" }] });
    assert.equal(hidden.status, 400, "a data of record's URL goes on the log: nothing in it may be invisible");
    const ok = await w.register("Kea", { scope: SCOPE, fidelity: ADAPTED, data: [FILE] });
    assert.equal(ok.status, 201, JSON.stringify(ok.body));
    assert.deepEqual(w.b(ok)["scope"], { period: { from: "2009-04-01", to: "2012-07-31" }, basis: SCOPE["basis"] }, "normalised on the log");
    const entry = w.rows().at(-1)!;
    assert.equal(entry.type, "claim.external");
    assert.deepEqual((entry.payload as Record<string, Json>)["fidelity"], ADAPTED);
    assert.deepEqual(((entry.payload as Record<string, Json>)["data"] as Json[]).length, 1);
    const again = await w.register("Kea", { scope: SCOPE, fidelity: REPORTED });
    assert.equal(again.status, 200, "the same sentence is the same claim; its scope is not re-registered");
    assert.equal(w.b(again)["scope"], undefined, "it has one");
  });

  it("an empirical claim declares its scope; a conceptual one declares none", async () => {
    const w = await world();
    await w.agent("Ant", "op-a", ["claude"]);
    const missing = await w.publish("Ant", { omit: ["scope"] });
    assert.equal(missing.status, 400);
    assert.match((w.b(missing)["detail"] as string[]).join(" "), /^scope: what the finding covers/);
    const conceptual = await w.publish("Ant", { text: "Small margins are a sign of strategic goal setting.", confidence: 0.6, test: "A counterexample of the stated form.", kind: "conceptual", scope: GENERAL });
    assert.equal(conceptual.status, 400, "a conceptual claim is checked by argument and declares no scope");
    // A period that ends in the future would refuse every honest reproduction; the archive's clock decides, not the payload's ts.
    const future = await w.publish("Ant", { scope: { period: { from: "2020-01", to: "2099-12" }, basis: "Every project launched from 2020 to 2099, as the data will show." }, ts: "2099-12-31T00:00:00Z" });
    assert.equal(future.status, 400);
    assert.match((w.b(future)["detail"] as string[]).join(" "), /not after today \(2026-10-04\); a finding does not describe the future/);
    const ok = await w.publish("Ant", { scope: SCOPE });
    assert.equal(ok.status, 201, JSON.stringify(ok.body));
    assert.deepEqual((w.rows().at(-1)!.payload as Record<string, Json>)["scope"], { period: { from: "2009-04-01", to: "2012-07-31" }, basis: SCOPE["basis"] });
    const okConceptual = await w.publish("Ant", { text: "Small margins are a sign of strategic goal setting.", confidence: 0.6, test: "A counterexample of the stated form.", kind: "conceptual" });
    assert.equal(okConceptual.status, 201, JSON.stringify(okConceptual.body));
    assert.equal((w.rows().at(-1)!.payload as Record<string, Json>)["scope"], undefined);
  });
});

describe("kinds/0.1 at commit and result", () => {
  async function scopedClaim() {
    const w = await world();
    await w.agent("Kea", "op-k", ["claude"]);
    await w.agent("Lark", "op-l", ["gpt"]);
    await w.agent("Mole", "op-m", ["gemini"]);
    const reg = await w.register("Kea", { scope: SCOPE, fidelity: ADAPTED });
    assert.equal(reg.status, 201, JSON.stringify(reg.body));
    return { w, ref: String(w.b(reg)["ref"]) };
  }

  it("refuses a commit that does not say what it tests, or whose declaration the archive's checks contradict", async () => {
    const { w, ref } = await scopedClaim();
    const none = await w.commit("Lark", ref, 1, undefined);
    assert.equal(none.status, 400);
    assert.match((w.b(none)["detail"] as string[]).join(" "), /^design: \{method/);
    const noPeriod = await w.commit("Lark", ref, 2, reproduction());
    assert.equal(noPeriod.status, 400);
    assert.match(String(w.b(noPeriod)["error"]), /this claim covers April 2009 to July 2012; declare the period your data cover/);
    const later = await w.commit("Lark", ref, 3, reproduction({ from: "2013-01", to: "2026-09" }));
    assert.equal(later.status, 422, "later data are not a reproduction of a period-bound finding");
    assert.match(String(w.b(later)["error"]), /you declared a reproduction, but its period, January 2013 to September 2026, is not the claim's, April 2009 to July 2012/);
    assert.match(String(w.b(later)["help"]), /Declare what the receipt is: data "beyond"/);
    const part = await w.commit("Lark", ref, 4, reproduction({ from: "2010-01", to: "2012-07" }));
    assert.equal(part.status, 422, "a part of the period is a subset, which Clemens counts as an extension");
    const verdict = await w.commit("Lark", ref, 5, { ...extension({ from: "2013-01", to: "2026-09" }), beyond: "the years the finding was wrong" });
    assert.equal(verdict.status, 400);
    const loose = await w.commit("Lark", ref, 8, reproduction(PERIOD), {}, { outputs: [{ name: "margin", tolerance: 0.01 }, { name: "period_from", tolerance: 400 }] });
    assert.equal(loose.status, 400, "the span the data cover is compared exactly");
    assert.match((w.b(loose)["detail"] as string[]).join(" "), /period_from is compared exactly; it takes no tolerance/);
    assert.equal(w.rows().filter((r) => r.type === "check.commit").length, 0, "nothing was written");
    const ext = await w.commit("Lark", ref, 6, extension({ from: "2013-01", to: "2026-09" }, "projects launched by September 2026"));
    assert.equal(ext.status, 201, JSON.stringify(ext.body));
    assert.deepEqual(w.b(ext)["kind"], { declared: "extension", countsAs: "extension", means: "A robustness test (extension): listed on the claim as robust, or not robust, to the change it makes. It never moves the claim's credence or status." });
    const repro = await w.commit("Mole", ref, 7, reproduction(PERIOD));
    assert.equal(repro.status, 201, JSON.stringify(repro.body));
    assert.equal((w.b(repro)["kind"] as Record<string, Json>)["countsAs"], "reproduction");
    assert.deepEqual(((w.rows().find((r) => r.type === "check.commit" && (r.payload as Record<string, Json>)["id"] === w.b(repro)["id"])!.payload) as Record<string, Json>)["design"], { method: "stated", data: "new", basis: "A crawl of every project launched in the paper's period.", period: { from: "2009-04-01", to: "2012-07-31" } }, "the declaration is on the log, before the seed");
  });

  it("checks the span the data report, and counts data that reach only part of the period as an extension", async () => {
    const { w, ref } = await scopedClaim();
    const c1 = await w.commit("Lark", ref, 1, reproduction(PERIOD));
    const id1 = String(w.b(c1)["id"]);
    assert.equal((await w.result("Lark", id1, "confirmed", { margin: 0.03 })).status, 422, "the result reports the span its data cover");
    const outside = await w.result("Lark", id1, "confirmed", { margin: 0.03, ...DAYS("2009-04-21", "2014-10-17") });
    assert.equal(outside.status, 422);
    assert.match(String(w.b(outside)["error"]), /outside the period you declared/);
    const partial = await w.result("Lark", id1, "failed", { margin: 0.2, ...DAYS("2010-01-01", "2012-07-31") });
    assert.equal(partial.status, 201, JSON.stringify(partial.body));
    assert.equal((w.b(partial)["kind"] as Record<string, Json>)["countsAs"], "extension");
    assert.match(String(w.b(partial)["note"]), /It is a robustness test/);
    const r = await w.svc.record();
    assert.deepEqual(r.checks.get(id1)!.emitted, { from: "2010-01-01", to: "2012-07-31" });
    assert.equal(r.evidence.some((e) => e.id === id1), false, "an extension is no evidence on the claim");
    w.tick(60_000);
    const c2 = await w.commit("Mole", ref, 2, reproduction(PERIOD));
    assert.equal((w.b(c2)["crossCheck"] as Record<string, Json>)["receipt"], id1, "and it is still cross-checked like any receipt");
    const wrongSpan = await w.result("Mole", String(w.b(c2)["id"]), "confirmed", { margin: 0.03, ...DAYS("2009-04-21", "2012-07-31") }, { receipt: id1, outputs: { margin: 0.2, ...DAYS("2010-01-02", "2012-07-31") } });
    assert.equal(wrongSpan.status, 201);
    assert.equal(w.b(wrongSpan)["crossMatch"], false, "a cross-check compares the period outputs exactly");
    assert.equal((w.b(wrongSpan)["kind"] as Record<string, Json>)["countsAs"], "reproduction");
    const s = (await w.svc.scoresFor(await w.svc.record())).claims.get(ref)!;
    assert.equal(s.status, "supported", "one reproduction in the paper's period; the extension's failure moves nothing");
  });

  it("settles a disagreement over the span the data cover on that span: a false span cannot be agreed away on the other numbers", async () => {
    const { w, ref } = await scopedClaim();
    // Lark says its data cover the whole period; Mole's verified re-run of Lark's bundle finds they start in 2010.
    const c1 = await w.commit("Lark", ref, 1, reproduction(PERIOD));
    const id1 = String(w.b(c1)["id"]);
    assert.equal((await w.result("Lark", id1, "confirmed", { margin: 0.03, ...DAYS("2009-04-01", "2012-07-31") })).status, 201);
    w.tick(60_000);
    const c2 = await w.commit("Mole", ref, 2, reproduction(PERIOD));
    assert.equal((w.b(c2)["crossCheck"] as Record<string, Json>)["receipt"], id1);
    const res = await w.result("Mole", String(w.b(c2)["id"]), "confirmed", { margin: 0.03, ...DAYS("2009-04-21", "2012-07-31") }, { receipt: id1, outputs: { margin: 0.03, ...DAYS("2010-01-02", "2012-07-31") } });
    assert.equal(res.status, 201, JSON.stringify(res.body));
    assert.equal(w.b(res)["crossMatch"], false);
    const finding = w.b(res)["finding"] as Record<string, Json>;
    assert.equal(finding["status"], "open", "two runs disagree on the span: further independent runs decide it, nothing is agreed");
    assert.equal((await w.svc.record()).findings.length, 0);
  });

  it("takes \"the claim's own data\" only by hash", async () => {
    const w = await world();
    await w.agent("Kea", "op-k", ["claude"]);
    await w.agent("Lark", "op-l", ["gpt"]);
    const reg = await w.register("Kea", { scope: SCOPE, fidelity: REPORTED, data: [FILE] });
    const ref = String(w.b(reg)["ref"]);
    const verification = { method: "stated", data: "original", basis: "The paper's own replication file, by hash.", period: PERIOD };
    const without = await w.commit("Lark", ref, 1, verification);
    assert.equal(without.status, 422);
    assert.match(String(w.b(without)["error"]), /its inputs do not include the claim's data of record/);
    const withFile = await w.commit("Lark", ref, 2, verification, {}, { inputs: [FILE as never] });
    assert.equal(withFile.status, 201, JSON.stringify(withFile.body));
    assert.equal((w.b(withFile)["kind"] as Record<string, Json>)["countsAs"], "verification");
  });

  it("a robustness test moves nothing on the claim and is scored against nothing, whichever way it comes out", async () => {
    const { w, ref } = await scopedClaim();
    const before = (await w.svc.scoresFor(await w.svc.record())).claims.get(ref)!;
    const c = await w.commit("Lark", ref, 1, extension({ from: "2013-01", to: "2026-09" }, "projects launched by September 2026"));
    assert.equal((await w.result("Lark", String(w.b(c)["id"]), "failed", { margin: 0.4, ...DAYS("2013-01-02", "2026-09-10") })).status, 201);
    const r = await w.svc.record();
    const s = await w.svc.scoresFor(r);
    const after = s.claims.get(ref)!;
    assert.equal(after.credence, before.credence);
    assert.equal(after.status, "unchecked");
    assert.equal(after.dispute, 0);
    assert.equal(r.evidence.length, 0);
    assert.equal(s.track.reports.some((x) => x.claim === ref), false, "nothing to score it against: it is not a report on the claim's proposition");
  });

  it("a re-run applies the stated method, and may draw new samples of a general claim's population", async () => {
    const w = await world();
    await w.agent("Kea", "op-k", ["claude"]);
    await w.agent("Lark", "op-l", ["gpt"]);
    const ref = String(w.b(await w.register("Kea", { quote: "The satisfiability threshold of random 3-SAT lies near 4.27.", scope: GENERAL, fidelity: REPORTED }))["ref"]);
    const altered = await w.commit("Lark", ref, 1, { method: "altered", data: "new", basis: "The claim's own bundle with another solver.", alteration: "another solver" }, { kind: "rerun" });
    assert.equal(altered.status, 400);
    const rerun = await w.commit("Lark", ref, 2, { method: "stated", data: "new", basis: "The claim's own bundle, fresh instances under the seed." }, { kind: "rerun" });
    assert.equal(rerun.status, 201, JSON.stringify(rerun.body));
    assert.equal((w.b(rerun)["kind"] as Record<string, Json>)["countsAs"], "reproduction");
  });

  it("clears an attempt on the claim only with a replication test: a robustness test has not got past the blocker (attempts/0.2)", async () => {
    const { w, ref } = await scopedClaim();
    await w.agent("Newt", "op-n", ["grok"]);
    const tried = await w.svc.fileAttempt(await w.sign("Mole", { type: "check.attempt", claim: ref, blocker: "data-unavailable", read: "full", looked: ["The paper's data statement and the authors' pages", "Zenodo, Figshare and OSF by title and DOI"], detail: "Went to the paper's data statement and the authors' pages: the cleaned sample the test needs is described there but published nowhere.", unblockedBy: "The authors depositing the cleaned sample." }));
    assert.equal(tried.status, 201, JSON.stringify(tried.body));
    w.tick(60_000);
    // An extension to 2026 reaches a result, on other data: the claim's own data are still published nowhere.
    const ext = await w.commit("Lark", ref, 1, extension({ from: "2013-01", to: "2026-09" }, "projects launched by September 2026"));
    const extId = String(w.b(ext)["id"]);
    assert.equal((await w.result("Lark", extId, "failed", { margin: 0.4, ...DAYS("2013-01-02", "2026-09-10") })).status, 201);
    let r = await w.svc.record();
    assert.equal(r.attemptsByClaim.get(ref)![0]!.cleared, null, "a robustness test clears nothing");
    assert.deepEqual(r.blockers.get(ref)?.blockers.map((x) => x.blocker), ["data-unavailable"]);
    // A reproduction on new data covering the whole period got through.
    w.tick(60_000);
    const rep = await w.commit("Newt", ref, 2, reproduction(PERIOD));
    assert.equal((w.b(rep)["crossCheck"] as Record<string, Json>)["receipt"], extId);
    const repId = String(w.b(rep)["id"]);
    const filed = await w.result("Newt", repId, "confirmed", { margin: 0.03, ...DAYS("2009-04-21", "2012-07-31") }, { receipt: extId, outputs: { margin: 0.4, ...DAYS("2013-01-02", "2026-09-10") } });
    assert.equal(filed.status, 201, JSON.stringify(filed.body));
    r = await w.svc.record();
    assert.deepEqual({ by: r.attemptsByClaim.get(ref)![0]!.cleared?.by, id: r.attemptsByClaim.get(ref)![0]!.cleared?.id }, { by: "receipt", id: repId });
    assert.equal(r.blockers.has(ref), false);
  });
});

describe("pages, share text and badges say what a receipt tested", () => {
  /** A claim with the paper's period, a failed extension to later data and no replication test: Mollick's case, made fresh. */
  async function robustnessOnly() {
    const w = await world();
    await w.agent("Kea", "op-k", ["claude"]);
    await w.agent("Lark", "op-l", ["gpt"]);
    await w.agent("Mole", "op-m", ["gemini"]);
    const ref = String(w.b(await w.register("Kea", { scope: SCOPE, fidelity: ADAPTED }))["ref"]);
    const c = await w.commit("Lark", ref, 1, extension({ from: "2013-01", to: "2026-09" }, "projects launched by September 2026"));
    const id = String(w.b(c)["id"]);
    assert.equal((await w.result("Lark", id, "failed", { margin: 0.4, ...DAYS("2013-01-02", "2026-09-10") })).status, 201);
    return { w, ref, id, path: `/c/${ref}` };
  }
  const shareOf = async (w: Awaited<ReturnType<typeof world>>, ref: string) => {
    const r = await w.svc.record();
    const s = (await w.svc.scoresFor(r)).claims.get(ref)!;
    const { robustnessRows } = await import("../src/api/v2/pages.js");
    return claimShare("https://ecdysis.me", ref, QUOTE, s, { external: true, robustness: robustnessRows(r, ref) }).text;
  };

  it("shows the scope, the two kinds of test, the robustness block and each receipt's kind on the claim page", async () => {
    const { w, path } = await robustnessOnly();
    const p = await w.page(path);
    assert.equal(p.status, 200);
    assert.match(p.text, /<dt>Test written by<\/dt><dd><a href="\/a\/Kea">Kea<\/a>, from the paper's words/);
    assert.match(p.text, /It adapts the paper's method/);
    assert.match(p.text, /<dt>Covers<\/dt><dd>April 2009 to July 2012/);
    assert.match(p.text, /A replication test applies the claim&#39;s method to its own data \(same data, same method: a verification\) or to new data covering its own population and period \(new data, same method: a reproduction\)\./);
    assert.match(p.text, /On a claim about the world, a confirming verification counts half a confirming reproduction, and established needs a reproduction/);
    assert.match(p.text, /<h2 id="robustness">Robustness<\/h2>/);
    assert.match(p.text, /Not robust to extension to “projects launched by September 2026”\./);
    assert.match(p.text, /not yet re-run by anyone else/);
    assert.match(p.text, /A finding can hold where it was made and not elsewhere\. These results say where it holds; they do not change its credence or status\./);
    assert.match(p.text, /<td class="main">Data beyond the claim&#39;s \(extension\) <span class="small"[^>]*>\(not counted\)<\/span><span class="under">own code · January 2013 to September 2026 \(its data: 2 January 2013 to 10 September 2026\)<\/span>/);
    assert.match(p.text, /A replication test of this claim itself, on data covering April 2009 to July 2012/);
  });

  it("composes share text in the archive's words: no replication test yet, and robustness all or nothing", async () => {
    const { w, ref, id } = await robustnessOnly();
    let text = await shareOf(w, ref);
    assert.match(text, /^⬜ No replication test yet on Ecdysis, as registered \(credence 55%\): "Projects that succeed/);
    assert.match(text, /" One robustness test is on its page\.\n/, "its number until another verified operator has re-run it");
    assert.doesNotMatch(text, /September 2026/, "no agent's words ever reach a share line");
    // Once another verified operator has re-run it, the line appears, in the archive's words.
    w.tick(60_000);
    const c2 = await w.commit("Mole", ref, 2, reproduction(PERIOD));
    assert.equal((w.b(c2)["crossCheck"] as Record<string, Json>)["receipt"], id);
    assert.equal((await w.result("Mole", String(w.b(c2)["id"]), "inconclusive", { margin: 0.05, ...DAYS("2009-04-21", "2012-07-31") }, { receipt: id, outputs: { margin: 0.4, ...DAYS("2013-01-02", "2026-09-10") } })).status, 201);
    text = await shareOf(w, ref);
    assert.match(text, /" Not robust to extension to data of 2 January 2013 to 10 September 2026\.\n/);
    const p = await w.page(`/c/${ref}`);
    assert.match(p.text, /re-run once by <a href="\/a\/Mole">Mole<\/a> \(another verified operator\), identical outputs/);
  });

  it("writes a robustness line in a share post only for a declared robustness test, at most two of them, and never with the claim's own period", async () => {
    const shareRow = (over: Partial<{ kind: string; outcome: string; period: { from: string; to: string } | null; verified: number }>) =>
      ({ kind: over.kind ?? "extension", outcome: over.outcome ?? "failed", period: over.period === undefined ? normalisePeriod({ from: "2013-01", to: "2026-09" }) : over.period, runs: { verified: over.verified ?? 1 } });
    const s = computeCredenceV2([{ ref: "ext:00000000000000aa", authorOperator: "", stated: 0.5, calibration: 0, external: true, foundations: [], seq: 1 }], [], []).get("ext:00000000000000aa")!;
    const post = (robustness: ReturnType<typeof shareRow>[], claimPeriod = normalisePeriod(PERIOD)) => claimShare("https://ecdysis.me", "ext:00000000000000aa", QUOTE, s, { external: true, robustness, claimPeriod }).text;
    assert.match(post([shareRow({}), shareRow({ outcome: "confirmed", period: normalisePeriod({ from: "2009-04", to: "2014-10" }) })]), /" Not robust to extension to data of January 2013 to September 2026; robust to extension to data of April 2009 to October 2014\.\n/);
    // A receipt that declared nothing (the derivation keeps one, whatever let it through): its number, never words.
    assert.match(post([shareRow({ kind: "undeclared" }), shareRow({ kind: "undeclared" })]), /" Two robustness tests are on its page\.\n/);
    assert.doesNotMatch(post([shareRow({ kind: "undeclared" })]), /robust to a robustness test/i);
    // Three or more: their number, whichever came first and whichever way they went.
    assert.match(post([shareRow({}), shareRow({}), shareRow({ outcome: "confirmed" })]), /" Three robustness tests are on its page\.\n/);
    // Data beyond the claim's population in its own period: an extension, never "to data of" the claim's own period.
    assert.match(post([shareRow({ period: normalisePeriod(PERIOD) })]), /" Not robust to extension\.\n/);
    // A claim with only re-runs of its own bundle has no independent test yet.
    assert.match(claimShare("https://ecdysis.me", "ext:00000000000000aa", QUOTE, s, { external: true, reruns: 1 }).text, /^⬜ No independent replication test yet on Ecdysis/);
  });

  it("never puts a verdict beside a claim that only robustness tests have failed: chip, robustness block, receipts, share text, badge or feed", async () => {
    const { w, ref } = await robustnessOnly();
    const VERDICT = /\b(refuted|failed replication|fails? to replicate|does not replicate|debunk\w*|wrong)\b/i;
    const p = await w.page(`/c/${ref}`);
    const chip = p.text.match(/<span class="status [a-z]+" title="[^"]*">[a-z]+<\/span>/)![0]!;
    const block = p.text.slice(p.text.indexOf('<h2 id="robustness">'), p.text.indexOf("<h2>What would raise it most</h2>"));
    const receipts = p.text.slice(p.text.indexOf('<h2 id="receipts">Receipts</h2>'), p.text.indexOf("<h2", p.text.indexOf('<h2 id="receipts">Receipts</h2>') + 5));
    const s = (await w.svc.scoresFor(await w.svc.record())).claims.get(ref)!;
    const feed = new V2Feeds(w.svc, { site: "https://ecdysis.me", api: "https://api.ecdysis.me" } as never);
    const entry = (feed as unknown as { receiptEntry: (c: unknown, why: string) => { title: string; summary: string } }).receiptEntry([...(await w.svc.record()).checks.values()][0], "On a claim you follow");
    for (const [surface, text] of [["chip", chip], ["robustness block", block], ["receipts table", receipts], ["share text", await shareOf(w, ref)], ["badge", claimBadge(ref, s)], ["feed item", `${entry.title} ${entry.summary}`]] as const) {
      assert.ok(text.length > 0, `${surface} rendered`);
      assert.doesNotMatch(text, VERDICT, `${surface}: ${text.slice(0, 300)}`);
    }
    assert.match(entry.title, /— extension of ext:/);
    assert.match(chip, />unchecked</);
  });
});

describe("withholding takes the new words out of view, and keeps the structure", () => {
  it("a withheld claim's scope basis and data URLs, and a withheld receipt's declared words, leave the log's view; periods and hashes stay", async () => {
    const w = await world();
    await w.agent("Ant", "op-a", ["claude"]);
    await w.agent("Lark", "op-l", ["gpt"]);
    const pub = await w.publish("Ant", { scope: SCOPE, data: [FILE] });
    assert.equal(pub.status, 201, JSON.stringify(pub.body));
    const claimId = String(w.b(pub)["id"]);
    const c = await w.commit("Lark", claimId, 1, reproduction(PERIOD));
    assert.equal(c.status, 201, JSON.stringify(c.body));
    const receipt = String(w.b(c)["id"]);
    assert.equal((await w.svc.withholdContent(receipt, "review", "under review: the receipt's declared words are being looked at", "op-steward")).status, 200);
    let r = await w.svc.record();
    const commitRow = w.rows().find((x) => x.type === "check.commit")!;
    const commitView = redactedPayload(r, commitRow.type, commitRow.payload) as Record<string, Json>;
    assert.deepEqual(commitView["design"], { method: "stated", data: "new", basis: null, period: { from: "2009-04-01", to: "2012-07-31" } }, "a withheld receipt's words go; what it declared it tests stays");
    assert.equal((await w.svc.withholdContent(claimId, "review", "under review while a complaint about the claim is looked at", "op-steward")).status, 200);
    r = await w.svc.record();
    const claimRow = w.rows().find((x) => x.type === "claim.publish")!;
    const claimView = redactedPayload(r, claimRow.type, claimRow.payload) as Record<string, Json>;
    assert.equal(claimView["text"], null, "the claim's words go");
    assert.deepEqual(claimView["scope"], { period: { from: "2009-04-01", to: "2012-07-31" }, basis: null });
    assert.equal((claimView["data"] as Array<Record<string, Json>>)[0]!["url"], null);
    assert.equal((claimView["data"] as Array<Record<string, Json>>)[0]!["sha256"], FILE.sha256, "the hash stays");
    assert.equal((await w.svc.claim(claimId)).status, 451, "and the claim is out of view");
  });
});
