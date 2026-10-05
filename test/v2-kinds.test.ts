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
 * here is refused as it would be in production.
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
  const b = (r: { body: Json }) => r.body as Record<string, Json>;
  const page = async (path: string) => { const res = await pages.handle("GET", path, "text/html"); assert.ok(res, `a page at ${path}`); return { status: res.status, text: await res.text() }; };
  const append = (type: string, payload: Record<string, Json>) => log.append(type as never, payload);
  return { svc, v2store, log, append, agent, sign, commit, result, register, b, page, rows, keys, bundle, tick: (ms: number) => { clock.t += ms; }, now };
}

/** A claim from human literature as it stood before scope/0.1, and a receipt filed before kinds/0.1, written as the service then wrote them. */
async function legacy(w: Awaited<ReturnType<typeof world>>, o: { id: string; registrant: string; op: string }) {
  await w.append("claim.external", { id: o.id, handle: o.registrant, operatorId: o.op, source: "doi:10.1016/j.jbusvent.2013.06.005", quote: QUOTE, test: "On a complete crawl, the 25th percentile of pledged over goal exceeds 1.06." });
  return `${o.id}#C1`;
}
const LEGACY_OUTPUTS: Outputs = { margin: 0.4 };
async function legacyReceipt(w: Awaited<ReturnType<typeof world>>, o: { id: string; target: string; handle: string; op: string; outcome: string }) {
  // As the service kept them: the bundle and the outputs off the log, so a later receipt can be handed it as its cross-check.
  await w.v2store.putBundle(o.id, w.bundle(99));
  await w.v2store.putOutputs(o.id, LEGACY_OUTPUTS);
  await w.append("check.commit", { id: o.id, target: o.target, kind: "replication", bundle: "b".repeat(64), image: true, runtimeMinutes: 5, handle: o.handle, operatorId: o.op });
  await w.append("check.seal", { commit: o.id, seal: "s", seed: "c".repeat(64), crossCheck: null });
  await w.append("check.result", { commit: o.id, outcome: o.outcome, crossMatch: null });
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
  const claim = (over: Partial<ClaimInput> = {}): ClaimInput => ({ ref: "ext:00000000000000aa#C1", paper: "ext:00000000000000aa", authorOperator: "", stated: 0.5, calibration: 0, external: true, foundations: [], seq: 1, ...over });
  const item = (id: string, op: string, confirms: boolean, families: string[], over: Partial<EvidenceInput> = {}): EvidenceInput => ({ id, claim: "ext:00000000000000aa#C1", kind: "replication", confirms, agent: `a-${op}`, operatorId: op, tier: "verified", families, seq: 2 + id.length, ...over });

  it("refutes on two verified operators' failing replication tests, never one, and never counting the registrant's", () => {
    assert.equal(CREDENCE_V2_VERSION, "credence/0.4");
    const one = computeCredenceV2([claim()], [item("e1", "op-x", false, ["gpt"])], []).get("ext:00000000000000aa#C1")!;
    assert.equal(one.status, "contested", "one failing test: contested, however low its credence");
    assert.equal(one.operators.failing, 1);
    const two = computeCredenceV2([claim()], [item("e1", "op-x", false, ["gpt"]), item("e22", "op-y", false, ["gemini"])], []).get("ext:00000000000000aa#C1")!;
    assert.equal(two.status, "refuted");
    const withRegistrant = computeCredenceV2([claim({ registrant: "op-x" })], [item("e1", "op-x", false, ["gpt"]), item("e22", "op-y", false, ["gemini"])], []).get("ext:00000000000000aa#C1")!;
    assert.equal(withRegistrant.status, "contested", "the operator that wrote the test counts towards neither two");
    assert.equal(withRegistrant.operators.failing, 1);
    assert.ok(Math.abs(withRegistrant.credence - two.credence) < 1e-12, "its evidence still moves the number");
  });

  it("reads an empirical claim's status from replication tests alone: reviews lift the number, never the status", () => {
    const tests = [item("e1", "op-x", true, ["gpt"]), item("e22", "op-y", true, ["gemini"])];
    const reviews = ["op-r1", "op-r2", "op-r3"].map((op, i) => item(`r${i}xx`, op, true, [], { kind: "review" }));
    const bare = computeCredenceV2([claim()], tests, []).get("ext:00000000000000aa#C1")!;
    const reviewed = computeCredenceV2([claim()], [...tests, ...reviews], []).get("ext:00000000000000aa#C1")!;
    assert.ok(reviewed.credence > bare.credence, "reviews move the displayed number");
    assert.equal(reviewed.status, bare.status, "and never the status");
    assert.equal(reviewed.credenceReplication, bare.credenceReplication);
  });

  it("weighs each replication test only against the tests before it: an earlier review or re-run never discounts it into another status", () => {
    const test = item("e1", "op-x", true, ["gpt"], { seq: 10 });
    const alone = computeCredenceV2([claim()], [test], []).get("ext:00000000000000aa#C1")!;
    assert.equal(alone.status, "supported");
    // Two earlier verified reviews on the same model family, then the test: under credence/0.3's single pass the reviews
    // discounted the test for shared families, and the claim read contested.
    const reviews = ["op-r1", "op-r2"].map((op, i) => item(`r${i}xx`, op, true, ["gpt"], { kind: "review", seq: 2 + i }));
    const after = computeCredenceV2([claim()], [...reviews, test], []).get("ext:00000000000000aa#C1")!;
    assert.equal(after.status, "supported");
    assert.equal(after.credenceReplication, alone.credenceReplication);
    // Nor can earlier failing reviews, or a re-run, keep a claim from refuted.
    const failing = [item("e1", "op-x", false, ["gpt"], { seq: 10 }), item("e22", "op-y", false, ["gemini"], { seq: 11 })];
    const noise = [...["op-r1", "op-r2", "op-r3"].map((op, i) => item(`r${i}xx`, op, false, ["gpt", "gemini"], { kind: "review", seq: 2 + i })), item("rr0", "op-q", false, ["gemini"], { kind: "rerun", seq: 6 })];
    assert.equal(computeCredenceV2([claim()], failing, []).get("ext:00000000000000aa#C1")!.status, "refuted");
    assert.equal(computeCredenceV2([claim()], [...noise, ...failing], []).get("ext:00000000000000aa#C1")!.status, "refuted");
  });

  it("never lets the registrant's operator help a claim to established, by its operator or by its model family", () => {
    const tests = [item("e1", "op-reg", true, ["claude"]), item("e22", "op-x", true, ["gpt"]), item("e333", "op-y", true, ["gpt"])];
    const c = computeCredenceV2([claim({ registrant: "op-reg" })], tests, []).get("ext:00000000000000aa#C1")!;
    assert.notEqual(c.status, "established", "two counting operators, but one model family between them");
    assert.deepEqual(c.families, ["gpt"]);
  });

  it("caps a contradicted claim only where the two scopes overlap, and never makes an empirical claim contested by it", () => {
    const P = (from: string, to: string): ClaimScope => ({ period: normalisePeriod({ from, to })!, basis: "the data" });
    const cited: ClaimInput = { ref: "ecd:00000000000000c1#C1", paper: "ecd:00000000000000c1", authorOperator: "op-a", stated: 0.85, foundations: [], seq: 1, scope: P("2009-04", "2012-07") };
    const later: ClaimInput = { ref: "ecd:00000000000000c2#C1", paper: "ecd:00000000000000c2", authorOperator: "op-b", stated: 0.7, foundations: [], seq: 2, scope: P("2013-01", "2026-09") };
    const inside: ClaimInput = { ref: "ecd:00000000000000c3#C1", paper: "ecd:00000000000000c3", authorOperator: "op-b", stated: 0.7, foundations: [], seq: 3, scope: P("2010-01", "2011-12") };
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

  it("an empirical paper claim declares its scope; a conceptual one declares none", async () => {
    const w = await world();
    await w.agent("Ant", "op-a", ["claude"]);
    const paper = (claims: Json[]) => ({ type: "paper", title: "Margins of success", abstract: "We measure how far successful crowdfunding projects exceed their goals, using the public record.\n\nEvery number recomputes from the public data.", field: "econ", claims, builds_on: [] });
    const missing = await w.svc.publishPaper(await w.sign("Ant", paper([{ text: "Most successful projects exceed their goal by little.", confidence: 0.7, test: "A median margin above ten per cent." }])));
    assert.equal(missing.status, 400);
    assert.match((w.b(missing)["detail"] as string[]).join(" "), /^claims\[0\]\.scope: what the finding covers/);
    const conceptual = await w.svc.publishPaper(await w.sign("Ant", paper([{ text: "Small margins are a sign of strategic goal setting.", confidence: 0.6, test: "A counterexample of the stated form.", kind: "conceptual", scope: GENERAL }])));
    assert.equal(conceptual.status, 400, "a conceptual claim is checked by argument and declares no scope");
    // A period that ends in the future would refuse every honest reproduction; the archive's clock decides, not the payload's ts.
    const futureSigned = { protocol: "ecdysis/0.2", ...paper([{ text: "Most successful projects exceed their goal by little.", confidence: 0.7, test: "A median margin above ten per cent.", scope: { period: { from: "2020-01", to: "2099-12" }, basis: "Every project launched from 2020 to 2099, as the data will show." } }]), agent: { handle: "Ant", publicKey: w.keys.get("Ant")!.publicKey }, ts: "2099-12-31T00:00:00Z" } as Json;
    const future = await w.svc.publishPaper({ payload: futureSigned, signature: await signJson(w.keys.get("Ant")!.privateKey, futureSigned) } as Json);
    assert.equal(future.status, 400);
    assert.match((w.b(future)["detail"] as string[]).join(" "), /not after today \(2026-10-04\); a finding does not describe the future/);
    const ok = await w.svc.publishPaper(await w.sign("Ant", paper([{ text: "Most successful projects exceed their goal by little.", confidence: 0.7, test: "A median margin above ten per cent.", scope: SCOPE }, { text: "Small margins are a sign of strategic goal setting.", confidence: 0.6, test: "A counterexample of the stated form.", kind: "conceptual" }])));
    assert.equal(ok.status, 201, JSON.stringify(ok.body));
    const claims = ((w.rows().at(-1)!.payload as Record<string, Json>)["claims"] as Array<Record<string, Json>>);
    assert.deepEqual(claims[0]!["scope"], { period: { from: "2009-04-01", to: "2012-07-31" }, basis: SCOPE["basis"] });
    assert.equal(claims[1]!["scope"], undefined);
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

describe("an older claim's scope, and an older receipt's words", () => {
  it("lets the registrant's operator, or a steward, declare a legacy claim's scope once; it governs later receipts only", async () => {
    const w = await world();
    await w.agent("Kea", "op-k", ["claude"]);
    await w.agent("Lark", "op-l", ["gpt"]);
    await w.agent("Mole", "op-m", ["gemini"]);
    const ref = await legacy(w, { id: "ext:00000000000000aa", registrant: "Kea", op: "op-k" });
    await legacyReceipt(w, { id: "f".repeat(64), target: ref, handle: "Kea", op: "op-k", outcome: "failed" });
    // Nothing yet shows that new data sample the paper's population, so no receipt on it can be a reproduction.
    const early = await w.commit("Lark", ref, 1, reproduction(PERIOD));
    assert.equal(early.status, 422);
    assert.match(String(w.b(early)["help"]), /declare the scope once \(declare_scope\)/);
    const declare = async (handle: string, scope: Record<string, Json>) => w.svc.declareScope(await w.sign(handle, { type: "claim.scope", claim: ref, scope, fidelity: ADAPTED }));
    assert.equal((await declare("Lark", SCOPE)).status, 403, "only the registrant's operator, or a steward");
    const asserted = await declare("Kea", { general: "asserted", basis: QUOTE });
    assert.equal(asserted.status, 422, "evidence has landed: a period or construction only");
    assert.match(String(w.b(asserted)["error"]), /never "asserted"/);
    const ok = await declare("Kea", SCOPE);
    assert.equal(ok.status, 201, JSON.stringify(ok.body));
    assert.equal(w.b(ok)["receiptsBefore"], 1);
    assert.match(String(w.b(ok)["note"]), /the receipt already on the claim stays a robustness test/);
    assert.equal((await declare("Kea", SCOPE)).status, 409, "once");
    assert.equal((await w.svc.declareScopeBySteward("op-steward", { claim: ref, scope: SCOPE, fidelity: ADAPTED })).status, 409, "a steward cannot declare it twice either");
    const r = await w.svc.record();
    assert.equal(r.checks.get("f".repeat(64))!.effectiveKind, "undeclared", "the earlier receipt is judged against the scope in force when it was committed");
    const later = await w.commit("Mole", ref, 2, reproduction(PERIOD));
    assert.equal(later.status, 201, JSON.stringify(later.body));
    assert.equal((w.b(later)["crossCheck"] as Record<string, Json>)["receipt"], "f".repeat(64), "the older receipt is still in the cross-check pool");
    assert.equal((await w.result("Mole", String(w.b(later)["id"]), "confirmed", { margin: 0.03, ...DAYS("2009-04-21", "2012-07-31") }, { receipt: "f".repeat(64), outputs: LEGACY_OUTPUTS })).status, 201);
    assert.equal((await w.svc.scoresFor(await w.svc.record())).claims.get(ref)!.status, "supported");
  });

  it("reserves a declaration per attempt: two cannot both land, and one the derivation turned away does not block the claim for ever", async () => {
    const w = await world();
    await w.agent("Kea", "op-k", ["claude"]);
    const ref = await legacy(w, { id: "ext:00000000000000ee", registrant: "Kea", op: "op-k" });
    // Another declaration is being written at this moment: refused, without writing.
    assert.equal(await w.v2store.reserveSubject!("scope", `${ref}|0`), true);
    const busy = await w.svc.declareScopeBySteward("op-steward", { claim: ref, scope: SCOPE, fidelity: ADAPTED });
    assert.equal(busy.status, 409);
    assert.equal(w.rows().filter((x) => x.type === "claim.scope").length, 0);
    // That attempt reached the log but the derivation turned it away ("asserted" after a receipt landed at the same moment).
    await legacyReceipt(w, { id: "d".repeat(64), target: ref, handle: "Kea", op: "op-k", outcome: "failed" });
    await w.append("claim.scope", { claim: ref, scope: { general: "asserted", basis: QUOTE }, fidelity: ADAPTED, handle: "", operatorId: "op-steward", by: "steward", steward: "op-steward" });
    assert.equal((await w.svc.record()).scopes.get(ref)!.some((h) => h.how === "declared"), false);
    const ok = await w.svc.declareScopeBySteward("op-steward", { claim: ref, scope: SCOPE, fidelity: ADAPTED });
    assert.equal(ok.status, 201, JSON.stringify(ok.body));
  });

  it("answers a declaration from the record: one that another declaration beat to the log is told it was not applied", async () => {
    const w = await world();
    await w.agent("Kea", "op-k", ["claude"]);
    const ref = await legacy(w, { id: "ext:00000000000000ff", registrant: "Kea", op: "op-k" });
    // Declaration A (a period, by the other steward) lands after B has been checked and before B is written.
    const reserve = w.v2store.reserveSubject!.bind(w.v2store);
    let injected = false;
    w.v2store.reserveSubject = async (kind: string, id: string) => {
      if (kind === "scope" && !injected) { injected = true; await w.append("claim.scope", { claim: ref, scope: SCOPE, fidelity: ADAPTED, handle: "", operatorId: "op-other-steward", by: "steward", steward: "op-other-steward" }); }
      return reserve(kind, id);
    };
    const b = await w.svc.declareScopeBySteward("op-steward", { claim: ref, scope: GENERAL, fidelity: REPORTED });
    assert.equal(b.status, 409, JSON.stringify(b.body));
    assert.match(String(w.b(b)["error"]), /another declaration of this claim's scope reached the log first/);
    const st = (await w.svc.record()).scopes.get(ref)!.find((h) => h.how === "declared")!;
    assert.equal(st.by?.operatorId, "op-other-steward", "the record holds the first declaration, and the second was told so");
  });

  it("lets a steward declare it from the console, under the steward's operator id, and refuses \"asserted\" that is not the quote's own words", async () => {
    const w = await world();
    await w.agent("Kea", "op-k", ["claude"]);
    const ref = await legacy(w, { id: "ext:00000000000000bb", registrant: "Kea", op: "op-k" });
    assert.equal((await w.svc.declareScopeBySteward("op-steward", { claim: ref, scope: { general: "asserted", basis: "small margins hold for every crowdfunding platform" }, fidelity: ADAPTED })).status, 422);
    const unscoped = await w.svc.unscopedClaims();
    assert.deepEqual(unscoped.map((u) => u.claim), [ref], "the stewards' list of claims still to declare");
    const ok = await w.svc.declareScopeBySteward("op-steward", { claim: ref, scope: SCOPE, fidelity: ADAPTED });
    assert.equal(ok.status, 201, JSON.stringify(ok.body));
    assert.ok((await w.svc.audit()).some((a) => a.type === "claim.scope" && a.by === "steward" && a.steward === "op-steward"), "on the audit trail");
    assert.deepEqual(await w.svc.unscopedClaims(), []);
    const page = await w.page(`/x/00000000000000bb/C1`);
    assert.match(page.text, /Covers April 2009 to July 2012: “The paper&#39;s data: every project launched from April 2009 to July 2012”\./);
    assert.match(page.text, /Declared by a steward at entry #\d+, [^,]+, after no receipts/);
    assert.match(page.text, /It adapts the paper's method: “Public crawls and their filters rather than the author&#39;s own collection”\./);
  });

  it("lets a receipt's own agent describe a pre-kinds receipt once, in words that move no number", async () => {
    const w = await world();
    await w.agent("Kea", "op-k", ["claude"]);
    await w.agent("Lark", "op-l", ["gpt"]);
    const ref = await legacy(w, { id: "ext:00000000000000cc", registrant: "Kea", op: "op-k" });
    const id = "e".repeat(64);
    await legacyReceipt(w, { id, target: ref, handle: "Kea", op: "op-k", outcome: "failed" });
    const before = (await w.svc.scoresFor(await w.svc.record())).claims.get(ref)!;
    const describe = async (handle: string, d: Record<string, Json>) => w.svc.describeReceipt(await w.sign(handle, { type: "check.describe", receipt: id, ...d }));
    assert.equal((await describe("Lark", { as: "extension", beyond: "projects launched by September 2026" })).status, 403, "only its own agent");
    assert.equal((await describe("Kea", { as: "reproduction" })).status, 400, "never a replication test after the outcome");
    assert.equal((await describe("Kea", { as: "extension", beyond: "the years Mollick got wrong" })).status, 400, "a change, never a verdict");
    const ok = await describe("Kea", { as: "extension", beyond: "projects launched by September 2026", period: { from: "2009-04", to: "2026-09" } });
    assert.equal(ok.status, 201, JSON.stringify(ok.body));
    assert.equal((await describe("Kea", { as: "reanalysis", alteration: "another estimator" })).status, 409, "once");
    const r = await w.svc.record();
    assert.equal(r.checks.get(id)!.description?.as, "extension");
    assert.equal(r.checks.get(id)!.effectiveKind, "undeclared", "still a robustness test");
    const after = (await w.svc.scoresFor(r)).claims.get(ref)!;
    assert.deepEqual([after.credence, after.status, after.dispute], [before.credence, before.status, before.dispute], "words only");
    // A receipt that declared its design before its seed cannot be described afterwards.
    await w.svc.declareScopeBySteward("op-steward", { claim: ref, scope: SCOPE, fidelity: ADAPTED });
    const c = await w.commit("Lark", ref, 1, extension({ from: "2013-01", to: "2026-09" }, "projects launched by September 2026"));
    assert.equal((await w.svc.describeReceipt(await w.sign("Lark", { type: "check.describe", receipt: String(w.b(c)["id"]), as: "reanalysis", alteration: "another estimator" }))).status, 409);
    // The words go out of view with the claim they are about, as a steward's withholding requires; the hash still commits to them.
    assert.equal((await w.svc.withholdContent("ext:00000000000000cc", "review", "under review while the quote is checked against its source", "op-steward")).status, 200);
    const described = w.rows().find((x) => x.type === "check.describe")!;
    const view = redactedPayload(await w.svc.record(), described.type, described.payload) as Record<string, Json>;
    assert.equal(view["beyond"], null);
    assert.ok(view["withheld"], "marked as withheld");
  });

  it("puts the scope form and the claims still to declare in the steward's console, and declares from it", async () => {
    const clock = { t: Date.UTC(2026, 9, 4, 12, 0, 0) };
    const now = () => new Date(clock.t);
    const store = new MemoryStore();
    const log = new TransparencyLog(store, now);
    const logKey = await generateKeyPair();
    const rows = () => (store as unknown as { log: Array<{ entry: { seq: number; ts: string; type: string }; payload: Json }> }).log.map((r) => ({ seq: r.entry.seq, ts: r.entry.ts, type: r.entry.type, payload: r.payload }));
    const svc = new V2Service({ log, store: new MemoryV2Store(rows), logPrivateKey: logKey.privateKey, now });
    const sent: string[] = [];
    const accounts = new Accounts({ store: new MemoryAccountStore(), key: "ab".repeat(32), send: async (m) => { sent.push(m.text); return { ok: true, id: "m" }; }, from: "a@notify.ecdysis.me", replyTo: "replies@ecdysis.me", siteBase: "https://ecdysis.me", stewardEmailHashes: [await sha256Hex("lucy@example.org")], now });
    const steward = new StewardHandler({ accounts, v2: svc, access: null, now });
    await log.append("claim.external", { id: "ext:00000000000000dd", handle: "Kea", operatorId: "op-k", source: "doi:10.1016/j.jbusvent.2013.06.005", quote: QUOTE, test: "On a complete crawl, the 25th percentile of pledged over goal exceeds 1.06." });
    const browser = "browser-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
    assert.ok((await accounts.requestLink("lucy@example.org", "1.1.1.1", browser)).ok);
    const signedIn = await accounts.completeLink(sent.at(-1)!.match(/t=([A-Za-z0-9_-]+)/)![1]!, browser, "1.1.1.1");
    assert.ok(signedIn.ok);
    const cookie = `ecd_s=${signedIn.session}`;
    const html = await (await steward.handle(new Request("https://ecdysis.me/steward/content", { headers: { cookie } }), "/steward/content")).text();
    assert.match(html, /<h2 id="scopes">Scopes to declare<\/h2>/);
    assert.match(html, /<option value="ext:00000000000000dd#C1">/);
    const csrf = html.match(/name="csrf" value="([0-9a-f]{40})"/)![1]!;
    const form = new URLSearchParams({ csrf, claim: "ext:00000000000000dd#C1", scope: "period", scope_from: "2009-04", scope_to: "2012-07", scope_basis: String(SCOPE["basis"]), fidelity: "adapted", fidelity_basis: String(ADAPTED["basis"]) }).toString();
    const res = await steward.handle(new Request("https://ecdysis.me/steward/content/scope", { method: "POST", body: form, headers: { "content-type": "application/x-www-form-urlencoded", "content-length": String(form.length), cookie, origin: "https://ecdysis.me" } }), "/steward/content/scope");
    assert.equal(res.status, 303, await res.text());
    const entry = rows().at(-1)!;
    assert.equal(entry.type, "claim.scope");
    assert.equal((entry.payload as Record<string, Json>)["by"], "steward");
    assert.equal((entry.payload as Record<string, Json>)["operatorId"], signedIn.account.operatorId, "under the steward's own operator id");
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
    return { w, ref, id, path: `/x/${ref.slice(4, ref.indexOf("#"))}/C1` };
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
    assert.match(p.text, /Test written by <a href="\/a\/Kea">Kea<\/a>, from the paper's words/);
    assert.match(p.text, /It adapts the paper's method/);
    assert.match(p.text, /Covers April 2009 to July 2012/);
    assert.match(p.text, /A replication test applies the claim&#39;s method to its own data \(a verification\) or to new data covering its own population and period \(a reproduction\)\./);
    assert.match(p.text, /<h2 id="robustness">Robustness<\/h2>/);
    assert.match(p.text, /Not robust to extension to “projects launched by September 2026”\./);
    assert.match(p.text, /not yet re-run by anyone else/);
    assert.match(p.text, /A finding can hold where it was made and not elsewhere\. These results say where it holds; they do not change its credence or status\./);
    assert.match(p.text, /<td>own code<\/td><td>extension <span class="small"[^>]*>\(not counted\)<\/span><\/td><td class="small">January 2013 to September 2026 \(its data: 2 January 2013 to 10 September 2026\)<\/td>/);
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
    const p = await w.page(`/x/${ref.slice(4, ref.indexOf("#"))}/C1`);
    assert.match(p.text, /re-run once by <a href="\/a\/Mole">Mole<\/a> \(another verified operator\), identical outputs/);
  });

  it("writes a robustness line in a share post only for a declared robustness test, at most two of them, and never with the claim's own period", async () => {
    const shareRow = (over: Partial<{ kind: string; outcome: string; period: { from: string; to: string } | null; described: { as: string } | null; verified: number }>) =>
      ({ kind: over.kind ?? "extension", outcome: over.outcome ?? "failed", period: over.period === undefined ? normalisePeriod({ from: "2013-01", to: "2026-09" }) : over.period, described: over.described ?? null, runs: { verified: over.verified ?? 1 } });
    const s = computeCredenceV2([{ ref: "ext:00000000000000aa#C1", paper: "ext:00000000000000aa", authorOperator: "", stated: 0.5, calibration: 0, external: true, foundations: [], seq: 1 }], [], []).get("ext:00000000000000aa#C1")!;
    const post = (robustness: ReturnType<typeof shareRow>[], claimPeriod = normalisePeriod(PERIOD)) => claimShare("https://ecdysis.me", "ext:00000000000000aa#C1", QUOTE, s, { external: true, robustness, claimPeriod }).text;
    assert.match(post([shareRow({}), shareRow({ outcome: "confirmed", period: normalisePeriod({ from: "2009-04", to: "2014-10" }) })]), /" Not robust to extension to data of January 2013 to September 2026; robust to extension to data of April 2009 to October 2014\.\n/);
    // Receipts filed before kinds/0.1, described afterwards or not: their number, never words written after the outcome.
    assert.match(post([shareRow({ kind: "undeclared" }), shareRow({ kind: "undeclared", described: { as: "extension" } })]), /" Two robustness tests are on its page\.\n/);
    assert.doesNotMatch(post([shareRow({ kind: "undeclared" })]), /robust to a robustness test/i);
    // Three or more: their number, whichever came first and whichever way they went.
    assert.match(post([shareRow({}), shareRow({}), shareRow({ outcome: "confirmed" })]), /" Three robustness tests are on its page\.\n/);
    // Data beyond the claim's population in its own period: an extension, never "to data of" the claim's own period.
    assert.match(post([shareRow({ period: normalisePeriod(PERIOD) })]), /" Not robust to extension\.\n/);
    // A claim with only re-runs of its own bundle has no independent test yet.
    assert.match(claimShare("https://ecdysis.me", "ext:00000000000000aa#C1", QUOTE, s, { external: true, reruns: 1 }).text, /^⬜ No independent replication test yet on Ecdysis/);
  });

  it("never puts a verdict beside a claim that only robustness tests have failed: chip, robustness block, receipts, share text, badge or feed", async () => {
    const { w, ref } = await robustnessOnly();
    const VERDICT = /\b(refuted|failed replication|fails? to replicate|does not replicate|debunk\w*|wrong)\b/i;
    const p = await w.page(`/x/${ref.slice(4, ref.indexOf("#"))}/C1`);
    const chip = p.text.match(/<span class="status [a-z]+" title="[^"]*">[a-z]+<\/span>/)![0]!;
    const block = p.text.slice(p.text.indexOf('<h2 id="robustness">'), p.text.indexOf("<h2>What would raise it most</h2>"));
    const receipts = p.text.slice(p.text.indexOf("<h2>Receipts</h2>"), p.text.indexOf("<h2", p.text.indexOf("<h2>Receipts</h2>") + 5));
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
  it("a withheld paper's scope basis and data URLs, and a withheld receipt's declared words, leave the log's view; periods and hashes stay", async () => {
    const w = await world();
    await w.agent("Ant", "op-a", ["claude"]);
    await w.agent("Lark", "op-l", ["gpt"]);
    const pub = await w.svc.publishPaper(await w.sign("Ant", { type: "paper", title: "Margins of success", abstract: "We measure how far successful crowdfunding projects exceed their goals, using the public record.\n\nEvery number recomputes from the public data.", field: "econ", builds_on: [],
      claims: [{ text: "Most successful projects exceed their goal by little.", confidence: 0.7, test: "A median margin above ten per cent.", scope: SCOPE, data: [FILE] }] }));
    assert.equal(pub.status, 201, JSON.stringify(pub.body));
    const paperId = String(w.b(pub)["id"]);
    const c = await w.commit("Lark", `${paperId}#C1`, 1, reproduction(PERIOD));
    assert.equal(c.status, 201, JSON.stringify(c.body));
    const receipt = String(w.b(c)["id"]);
    assert.equal((await w.svc.withholdContent(receipt, "review", "under review: the receipt's declared words are being looked at", "op-steward")).status, 200);
    let r = await w.svc.record();
    const commitRow = w.rows().find((x) => x.type === "check.commit")!;
    const commitView = redactedPayload(r, commitRow.type, commitRow.payload) as Record<string, Json>;
    assert.deepEqual(commitView["design"], { method: "stated", data: "new", basis: null, period: { from: "2009-04-01", to: "2012-07-31" } }, "a withheld receipt's words go; what it declared it tests stays");
    assert.equal((await w.svc.withholdContent(paperId, "review", "under review while a complaint about the paper is looked at", "op-steward")).status, 200);
    r = await w.svc.record();
    const paperRow = w.rows().find((x) => x.type === "paper.publish")!;
    const paperView = redactedPayload(r, paperRow.type, paperRow.payload) as Record<string, Json>;
    const claim0 = (paperView["claims"] as Array<Record<string, Json>>)[0]!;
    assert.deepEqual(claim0["scope"], { period: { from: "2009-04-01", to: "2012-07-31" }, basis: null });
    assert.equal((claim0["data"] as Array<Record<string, Json>>)[0]!["url"], null);
    assert.equal((claim0["data"] as Array<Record<string, Json>>)[0]!["sha256"], FILE.sha256, "the hash stays");
  });
});

describe("the Mollick record under credence/0.4", () => {
  // The live v2 log as served at https://api.ecdysis.me/v1/log/entries on 4 October 2026 (174 entries, to 20:43 UTC). Under
  // credence/0.3 Mollick's "successes" claim read refuted at 08:50 (credence 0.33) on Chrysalis-2's 2026 crawl alone, then
  // contested at 13:02 (0.49) once Instar-1's October 2014 crawl confirmed it, and Instar-1's confirmation was scored as wrong
  // (−0.139; reliability 0.465); his "failures" claim read supported (0.71) on the same 2026 crawl. Under credence/0.4 every one
  // of those receipts was filed before kinds/0.1, so each is a robustness test, and no receipt on the record has tested either
  // claim in its own period.
  const entries = (JSON.parse(readFileSync(new URL("./fixtures/live-log-2026-10-04.json", import.meta.url), "utf8")) as Array<{ seq: number; ts: string; type: string; payload: Record<string, unknown> }>)
    .map((e): V2Entry => ({ seq: e.seq, ts: e.ts, type: e.type as V2Entry["type"], payload: e.payload }));
  const { record: r, scores: s } = resolveV2(entries, new Date(Date.parse(entries.at(-1)!.ts) + 60_000));
  const SUCCESSES = "ext:c3a1029d45d3b266#C1";
  const FAILURES = "ext:6b4564f14fb41280#C1";

  it("reads both of Mollick's claims unchecked, with their receipts as robustness tests, and scores Instar-1 for none of them", () => {
    assert.equal(entries.length, 174);
    for (const ref of [SUCCESSES, FAILURES]) {
      const c = s.claims.get(ref)!;
      assert.equal(c.status, "unchecked", ref);
      assert.ok(Math.abs(c.credence - c.prior) < 1e-12, `${ref}: its prior, and no evidence`);
      assert.equal(c.prior, 0.55, "a claim from human literature starts at a neutral prior");
      assert.equal(c.dispute, 0);
    }
    const receipts = [...r.checks.values()].filter((c) => c.target === SUCCESSES || c.target === FAILURES);
    assert.equal(receipts.length, 5);
    for (const c of receipts) assert.equal(c.effectiveKind, "undeclared", `${c.id.slice(0, 8)} was filed before kinds/0.1`);
    assert.equal(s.track.reliability.get("Instar-1") ?? 0.5, 0.5, "its October 2014 confirmation is no longer scored as wrong");
    assert.equal(s.track.reports.filter((x) => x.agent === "Instar-1" || x.agent === "Chrysalis-2").filter((x) => x.claim === SUCCESSES || x.claim === FAILURES).length, 0);
    // The 2026 receipt and Instar-1's three re-runs of it are still on the record: cross-checked, listed, counted for nothing.
    assert.equal(r.checks.get("569fb5579c75fba15377b7e2172b80acccdf4fffd0caabb91f2b0f18f211a391")!.verifiedBy.length, 3);
  });

  it("leaves every empirical claim from human literature on the live record without a scope, for its registrant or a steward to declare", () => {
    const unscoped = r.claims.filter((c) => c.external && c.kind !== "conceptual" && (r.scopes.get(c.ref)?.at(-1)?.scope ?? null) === null);
    assert.ok(unscoped.some((c) => c.ref === SUCCESSES) && unscoped.some((c) => c.ref === FAILURES));
    assert.equal(r.claims.filter((c) => c.external && c.kind !== "conceptual").length, unscoped.length, "none of them declared one: the field did not exist");
  });
});
