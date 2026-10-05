/**
 * inputs/0.1: data a bundle reads but does not carry. The commit pins each
 * input by hash and size with an access class; what is not open must be
 * held to re-run the bundle. A receipt on such data is weighed as an
 * unverified operator's until a verified, independent cross-check matches
 * it, is drawn as a cross-check only for checkers who hold its inputs, and
 * reports numbers only. The adversarial cases: a checker without the data
 * is never handed a receipt it cannot run; a verified operator's lone
 * receipt on private data settles nothing; a record cannot be copied into
 * an output.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { MemoryStore } from "../src/store/memory-store.js";
import { TransparencyLog } from "../src/core/log.js";
import { generateKeyPair, signJson, type KeyPairB64 } from "../src/core/crypto.js";
import { MemoryV2Store, V2Service } from "../src/api/v2/service.js";
import { canRun, inputProblems, pickCrossCheck, requiredHoldings, validateCheckCommit, type Bundle, type BundleInput, type Outputs } from "../src/core/v2/receipts.js";
import { sumEvidence, type EvidenceInput } from "../src/core/v2/credence.js";
import type { Json } from "../src/core/canonical.js";
import { CONSTITUTION_VERSION, constitutionHash } from "../src/core/constitution.js";
import { declared, REPRODUCTION } from "./kinds-kit.js";
const ACK = { version: CONSTITUTION_VERSION, hash: await constitutionHash() };

const SHA_A = "a".repeat(64);
const SHA_B = "b".repeat(64);
const OPEN: BundleInput = { name: "campaigns", url: "https://data.example.org/campaigns-2014.csv.gz", sha256: SHA_A, bytes: 123456, access: "open", licence: "CC-BY-4.0" };
const PRIVATE: BundleInput = { name: "survey", url: "https://archive.example.org/study/9999", sha256: SHA_B, bytes: 20_000_000_000, access: "restricted", licence: "end-user licence; register" };

async function world() {
  const store = new MemoryStore();
  const clock = { t: Date.UTC(2026, 9, 3, 9, 0, 0) };
  const now = () => new Date(clock.t);
  const log = new TransparencyLog(store, now);
  const logKey = await generateKeyPair();
  const rows = () => (store as unknown as { log: Array<{ entry: { seq: number; ts: string; type: string }; payload: Json }> }).log.map((r) => ({ seq: r.entry.seq, ts: r.entry.ts, type: r.entry.type, payload: r.payload }));
  const v2 = new MemoryV2Store(rows);
  const svc = new V2Service({ log, store: v2, logPrivateKey: logKey.privateKey, now });
  const keys = new Map<string, KeyPairB64>();
  const agent = async (handle: string, op: string, models?: string[], tier: "account" | "verified" | null = "verified") => {
    const kp = await generateKeyPair();
    keys.set(handle, kp);
    const r = await svc.registerAgent({ constitution: ACK, handle, publicKey: kp.publicKey, operatorId: op, ...(models ? { models } : {}) });
    assert.equal(r.status, 201, JSON.stringify(r.body));
    if (tier) await svc.setTier(op, tier);
    return kp;
  };
  const ts = () => now().toISOString().replace(/\.\d{3}Z$/, "Z");
  const sign = async (handle: string, payload: Record<string, Json>) => {
    const full: Json = declared({ ...payload, agent: { handle, publicKey: keys.get(handle)!.publicKey }, ts: ts() });
    return { payload: full, signature: await signJson(keys.get(handle)!.privateKey, full) } as Json;
  };
  const bundle = (n: number, inputs?: BundleInput[]): Bundle => ({ repo: "https://github.com/example/rep", commit: n.toString(16).padStart(40, "0"), image: "sha256:" + "a".repeat(64), run: "python run.py", outputs: [{ name: "effect", tolerance: 0.01 }, { name: "n" }], runtimeMinutes: 5, ...(inputs ? { inputs } : {}) });
  const commit = async (handle: string, target: string, b: Bundle, extra: Record<string, Json> = {}) =>
    svc.commitCheck(await sign(handle, { protocol: "ecdysis/0.2", type: "check.commit", target, kind: "replication", bundle: b as unknown as Json, ...extra }));
  const result = async (handle: string, id: string, outcome: string, outputs: Outputs, cross: { receipt: string; outputs: Outputs } | null) =>
    svc.fileResult(await sign(handle, { protocol: "ecdysis/0.2", type: "check.result", commit: id, outcome, outputs, crossCheck: cross as unknown as Json }));
  const external = async (handle: string, source: string, quote: string) => {
    const r = await svc.registerExternalClaim(await sign(handle, { protocol: "ecdysis/0.2", type: "claim.external", source, quote, test: "the stated result fails to appear with the stated setup" }));
    assert.equal(r.status, 201, JSON.stringify(r.body));
    return String((r.body as Record<string, Json>)["ref"]);
  };
  const b = (r: { body: Json }) => r.body as Record<string, Json>;
  const idOf = (r: { body: Json }) => String(b(r)["id"]);
  return { svc, agent, sign, bundle, commit, result, external, b, idOf, rows, keys, now, tick: (ms: number) => { clock.t += ms; } };
}

describe("inputs/0.1: the core", () => {
  it("validates declared inputs and holdings, and says what a bundle requires", () => {
    assert.deepEqual(inputProblems(undefined), []);
    assert.deepEqual(inputProblems([OPEN, PRIVATE]), []);
    const bad = inputProblems([
      { name: "9bad", url: "http://plain.example.org/x", sha256: "nothex", bytes: 0, access: "public" as never, licence: "x".repeat(121) },
      { ...OPEN },
      { ...OPEN },
    ]);
    assert.ok(bad.some((e) => e.startsWith("bundle.inputs[0].name")));
    assert.ok(bad.some((e) => e.startsWith("bundle.inputs[0].url: https")));
    assert.ok(bad.some((e) => e.startsWith("bundle.inputs[0].sha256")));
    assert.ok(bad.some((e) => e.startsWith("bundle.inputs[0].bytes")));
    assert.ok(bad.some((e) => e.startsWith("bundle.inputs[0].access")));
    assert.ok(bad.some((e) => e.startsWith("bundle.inputs[0].licence")));
    assert.ok(bad.some((e) => e === "bundle.inputs[2].name: duplicate"));
    assert.deepEqual(inputProblems(Array.from({ length: 9 }, (_, i) => ({ ...OPEN, name: `in${i}` }))), ["bundle.inputs: at most 8 declared inputs"]);
    assert.ok(inputProblems([{ ...OPEN, bytes: 2 ** 40 }, { ...PRIVATE, bytes: 1 }]).some((e) => e.includes("bytes in all")));
    assert.deepEqual(requiredHoldings([OPEN]), []);
    assert.deepEqual(requiredHoldings([OPEN, PRIVATE, { ...PRIVATE, name: "survey2" }]), [SHA_B]);
    assert.ok(canRun([], []) && canRun([SHA_B], [SHA_B, SHA_A]) && !canRun([SHA_B], [SHA_A]));
    // The commit validator carries both; holdings must be hashes.
    const base = { protocol: "ecdysis/0.2", type: "check.commit", target: "ext:0123456789abcdef", kind: "replication", design: REPRODUCTION, agent: { handle: "Ant", publicKey: "k".repeat(44) }, ts: "2026-10-03T09:00:00Z" };
    const bundle = { repo: "https://github.com/example/rep", commit: "0".repeat(40), run: "python run.py", outputs: [{ name: "effect" }], runtimeMinutes: 5, inputs: [OPEN, PRIVATE] };
    assert.equal(validateCheckCommit({ ...base, bundle, holds: [SHA_B] }).ok, true);
    const v = validateCheckCommit({ ...base, bundle: { ...bundle, inputs: [{ ...PRIVATE, access: "secret" }] }, holds: ["nothex"] });
    assert.equal(v.ok, false);
    if (!v.ok) assert.ok(v.errors.some((e) => e.startsWith("bundle.inputs[0].access")) && v.errors.some((e) => e.startsWith("holds:")));
  });

  it("draws a cross-check only among receipts the checker can run, uniformly under the seed", () => {
    const earlier = [
      { id: "r1", operatorId: "op-1", seq: 1, requires: [] as string[] },
      { id: "r2", operatorId: "op-2", seq: 2, requires: [SHA_B] },
      { id: "r3", operatorId: "op-3", seq: 3, requires: [SHA_A, SHA_B] },
    ];
    const seeds = Array.from({ length: 40 }, (_, i) => i.toString(16).padStart(64, "0"));
    // Without holdings only the open receipt is ever drawn.
    assert.ok(seeds.every((s) => pickCrossCheck(s, earlier, "op-x") === "r1"));
    // Holding B opens r2; holding both opens all three; the seed decides which, and every eligible one is drawn by some seed.
    const withB = new Set(seeds.map((s) => pickCrossCheck(s, earlier, "op-x", undefined, [SHA_B])));
    assert.deepEqual([...withB].sort(), ["r1", "r2"]);
    const withBoth = new Set(seeds.map((s) => pickCrossCheck(s, earlier, "op-x", undefined, new Set([SHA_A, SHA_B]))));
    assert.deepEqual([...withBoth].sort(), ["r1", "r2", "r3"]);
    // Nothing runnable: no cross-check rather than one the checker cannot do.
    assert.equal(pickCrossCheck(seeds[0]!, earlier.slice(1), "op-x"), null);
    // Independence still comes first: a checker never re-runs its own receipt, held or not.
    assert.equal(pickCrossCheck(seeds[3]!, [earlier[1]!], "op-2", undefined, [SHA_B]), null);
  });

  it("weighs a receipt the audit cannot reach as an unverified operator's, whatever its tier", () => {
    const item = (over: Partial<EvidenceInput>): EvidenceInput => ({ id: "r", claim: "ecd:cccccccccccccccc", kind: "replication", confirms: true, agent: "Ant", operatorId: "op-a", tier: "verified", families: ["claude"], seq: 1, ...over });
    const audited = sumEvidence([item({})], "op-author");
    const unaudited = sumEvidence([item({ auditable: false })], "op-author");
    assert.ok(audited.confirmingReplication && audited.s > 0 && audited.sumVerified > 0);
    assert.ok(!unaudited.confirmingReplication && unaudited.s === 0 && unaudited.sumVerified === 0, "it settles nothing");
    assert.ok(unaudited.sum > 0 && unaudited.sum < audited.sum, "it still moves credence a little, as an unverified operator's would");
    assert.equal(sumEvidence([item({ tier: "unverified" })], "op-author").sum, unaudited.sum, "exactly as much as that");
    const explicit = sumEvidence([item({ auditable: true })], "op-author");
    assert.deepEqual([explicit.sum, explicit.sumVerified, explicit.s, explicit.confirmingReplication], [audited.sum, audited.sumVerified, audited.s, audited.confirmingReplication], "true means weighed by tier as usual");
  });
});

describe("inputs/0.1: on the record", () => {
  it("logs inputs by hash and class, draws cross-checks by holdings, and lets a verified cross-check make the receipt count", async () => {
    const w = await world();
    await w.agent("Ant", "op-a", ["claude"]);
    await w.agent("Bee", "op-b", ["gpt"]);
    await w.agent("Cat", "op-c", ["gemini"]);
    await w.agent("Dog", "op-d", ["mistral"]);
    const ref = await w.external("Dog", "doi:10.1016/j.jbusvent.2013.06.005", "successful projects are funded by a small margin while failed ones fail by large amounts");
    // Ant's replication rests on a restricted survey: the commit records the input by hash and class, never its URL or licence.
    const c1 = await w.commit("Ant", ref, w.bundle(1, [OPEN, PRIVATE]), { holds: [SHA_B] });
    assert.equal(c1.status, 201, JSON.stringify(c1.body));
    assert.match(String(w.b(c1)["inputs"]), /counts at the unverified weight/);
    const id1 = w.idOf(c1);
    const entry = w.rows().find((x) => x.type === "check.commit" && (x.payload as Record<string, Json>)["id"] === id1)!.payload as Record<string, Json>;
    assert.deepEqual(entry["inputs"], [{ name: "campaigns", sha256: SHA_A, bytes: 123456, access: "open" }, { name: "survey", sha256: SHA_B, bytes: 20_000_000_000, access: "restricted" }]);
    assert.deepEqual(entry["holds"], [SHA_B]);
    assert.ok(!JSON.stringify(entry).includes("example.org"), "URLs stay in the stored bundle, off the log");
    // Numbers only: a string output could carry a record of the data.
    const leak = await w.result("Ant", id1, "confirmed", { effect: 0.42, n: "row 17: Jane Doe, 4 Acacia Avenue" }, null);
    assert.equal(leak.status, 422);
    assert.match(String(w.b(leak)["error"]), /numbers only/);
    assert.equal((await w.result("Ant", id1, "confirmed", { effect: 0.42, n: 48526 }, null)).status, 201);
    // A verified operator's receipt, but the claim stays unchecked: the audit has not reached it.
    let claim = (await w.svc.scores()).claims.get(ref)!;
    assert.equal(claim.status, "unchecked");
    assert.ok(claim.credence > 0.5, "it still moved credence a little");
    const view = w.b(await w.svc.receipt(id1));
    assert.deepEqual(view["requires"], [SHA_B]);
    assert.equal(view["auditable"], false);
    // Bee holds nothing: it is never handed Ant's receipt, and gets no cross-check at all (nothing else exists).
    const c2 = await w.commit("Bee", ref, w.bundle(2));
    assert.equal(w.b(c2)["crossCheck"], null, "a checker is never assigned a receipt it cannot run");
    assert.equal((await w.result("Bee", w.idOf(c2), "confirmed", { effect: 0.41, n: 48526 }, null)).status, 201);
    // Cat holds the survey: the draw assigns it Ant's receipt (Bee's open one is eligible too; the seed chose), and a match verifies it.
    let assigned: string | null = null;
    let idC = "";
    for (let n = 3; n < 40 && assigned !== id1; n++) {
      const cN = await w.commit("Cat", ref, w.bundle(n, [PRIVATE]), { holds: [SHA_B] });
      assigned = (w.b(cN)["crossCheck"] as Record<string, Json> | null)?.["receipt"] as string | null;
      idC = w.idOf(cN);
      if (assigned !== id1) assert.equal((await w.result("Cat", idC, "inconclusive", { effect: 0.4, n: 1 }, assigned ? { receipt: assigned, outputs: { effect: 0.41, n: 48526 } } : null)).status, 201);
    }
    assert.equal(assigned, id1, "with the holding, Ant's receipt is drawn");
    const stringCross = await w.result("Cat", idC, "confirmed", { effect: 0.43, n: 48526 }, { receipt: id1, outputs: { effect: 0.42, n: "48526" } });
    assert.equal(stringCross.status, 422, "numbers only for the cross-check of a restricted bundle too");
    const rC = await w.result("Cat", idC, "confirmed", { effect: 0.43, n: 48526 }, { receipt: id1, outputs: { effect: 0.425, n: 48526 } });
    assert.equal(rC.status, 201, JSON.stringify(rC.body));
    assert.equal(w.b(rC)["crossMatch"], true);
    const rec = await w.svc.record();
    assert.deepEqual(rec.checks.get(id1)!.verifiedBy, [idC]);
    assert.equal(w.b(await w.svc.receipt(id1))["auditable"], true, "the audit reached it");
    claim = (await w.svc.scores()).claims.get(ref)!;
    assert.equal(claim.status, "supported", "now Ant's and Bee's verified confirming replications count in full");
  });

  it("a bundle with open inputs only is an ordinary receipt: drawn for anyone, weighed by tier at once", async () => {
    const w = await world();
    await w.agent("Ant", "op-a", ["claude"]);
    await w.agent("Bee", "op-b", ["gpt"]);
    await w.agent("Dog", "op-d", ["mistral"]);
    const ref = await w.external("Dog", "arxiv:2001.08361", "test loss follows a power law in compute over seven orders of magnitude");
    const c1 = await w.commit("Ant", ref, w.bundle(1, [OPEN]));
    assert.equal(c1.status, 201);
    assert.equal(w.b(c1)["inputs"], undefined, "nothing to warn about");
    assert.equal((await w.result("Ant", w.idOf(c1), "confirmed", { effect: 0.9, n: "seven orders" }, null)).status, 201, "strings are fine when every input is open");
    assert.equal((await w.svc.scores()).claims.get(ref)!.status, "supported");
    const c2 = await w.commit("Bee", ref, w.bundle(2));
    assert.equal((w.b(c2)["crossCheck"] as Record<string, Json>)["receipt"], w.idOf(c1), "drawn without any holding");
  });
});
