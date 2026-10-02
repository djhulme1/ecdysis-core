/**
 * The v2 service end to end, over the pure core and the transparency log:
 * registration; an external claim as a target; commit → seal → result with
 * cross-check assignment (disputes first); a disagreement that becomes a
 * finding only when the rules allow; lapses; the scores recomputed from
 * the log alone.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { MemoryStore } from "../src/store/memory-store.js";
import { TransparencyLog } from "../src/core/log.js";
import { generateKeyPair, signJson, type KeyPairB64 } from "../src/core/crypto.js";
import { MemoryV2Store, RESULT_DEADLINE_MS, V2Service } from "../src/api/v2/service.js";
import { seedFromSeal, verifySeal, type Bundle, type Outputs } from "../src/core/v2/receipts.js";
import type { Json } from "../src/core/canonical.js";

async function world() {
  const store = new MemoryStore();
  const clock = { t: Date.UTC(2026, 9, 3, 9, 0, 0) };
  const now = () => new Date(clock.t);
  const log = new TransparencyLog(store, now);
  const logKey = await generateKeyPair();
  const v2 = new MemoryV2Store(() => (store as unknown as { log: Array<{ entry: { seq: number; ts: string; type: string }; payload: Json }> }).log.map((r) => ({ seq: r.entry.seq, ts: r.entry.ts, type: r.entry.type, payload: r.payload })));
  const svc = new V2Service({ log, store: v2, logPrivateKey: logKey.privateKey, now });
  const keys = new Map<string, KeyPairB64>();
  const agent = async (handle: string, op: string, models?: string[], tier: "account" | "verified" | null = "verified") => {
    const kp = await generateKeyPair();
    keys.set(handle, kp);
    const r = await svc.registerAgent({ handle, publicKey: kp.publicKey, operatorId: op, ...(models ? { models } : {}) });
    assert.equal(r.status, 201, JSON.stringify(r.body));
    if (tier) await svc.setTier(op, tier);
    return kp;
  };
  const sign = async (handle: string, payload: Json) => ({ payload, signature: await signJson(keys.get(handle)!.privateKey, payload) }) as Json;
  const tick = (ms: number) => { clock.t += ms; };
  const bundle = (n: number, image = true): Bundle => ({ repo: "https://github.com/example/rep", commit: n.toString(16).padStart(40, "0"), ...(image ? { image: "sha256:" + "a".repeat(64) } : {}), run: "python run.py", outputs: [{ name: "alpha", tolerance: 0.01 }, { name: "solver" }], runtimeMinutes: 5 });
  const commit = async (handle: string, target: string, b: Bundle, extra: Record<string, Json> = {}) =>
    svc.commitCheck(await sign(handle, { protocol: "ecdysis/0.2", type: "check.commit", target, kind: "replication", bundle: b as unknown as Json, agent: { handle, publicKey: keys.get(handle)!.publicKey }, ts: now().toISOString().replace(/\.\d{3}Z$/, "Z"), ...extra }));
  const result = async (handle: string, id: string, outcome: string, outputs: Outputs, cross: { receipt: string; outputs: Outputs } | null) =>
    svc.fileResult(await sign(handle, { protocol: "ecdysis/0.2", type: "check.result", commit: id, outcome, outputs, crossCheck: cross as unknown as Json, agent: { handle, publicKey: keys.get(handle)!.publicKey }, ts: now().toISOString().replace(/\.\d{3}Z$/, "Z") }));
  return { svc, agent, sign, tick, now, bundle, commit, result, logKey, keys };
}

describe("v2 service", () => {
  it("registers agents (models optional), registers an external claim, and seals the first receipt with no cross-check", async () => {
    const w = await world();
    await w.agent("Ant", "op-a", ["claude-opus-5-5"]);
    await w.agent("Bee", "op-b");
    const ext = await w.svc.registerExternalClaim(await w.sign("Ant", { protocol: "ecdysis/0.2", type: "claim.external", source: "doi:10.1126/science.264.5163.1297", quote: "the 3-SAT threshold is alpha_c = 4.17 +/- 0.05", test: "alpha_c outside [4.12, 4.22] at N = 200 with MiniSat", agent: { handle: "Ant", publicKey: w.keys.get("Ant")!.publicKey }, ts: "2026-10-03T09:00:00Z" }));
    assert.equal(ext.status, 201, JSON.stringify(ext.body));
    const ref = String((ext.body as Record<string, Json>)["ref"]);
    assert.match(ref, /^ext:[0-9a-f]{16}#C1$/);
    const again = await w.svc.registerExternalClaim(await w.sign("Bee", { protocol: "ecdysis/0.2", type: "claim.external", source: "DOI:10.1126/science.264.5163.1297", quote: "the 3-SAT threshold is alpha_c = 4.17 +/- 0.05", test: "a different test, same claim", agent: { handle: "Bee", publicKey: w.keys.get("Bee")!.publicKey }, ts: "2026-10-03T09:00:00Z" }));
    assert.equal(again.status, 200, "the same source and quote is the same claim");

    const c1 = await w.commit("Bee", ref, w.bundle(1));
    assert.equal(c1.status, 201, JSON.stringify(c1.body));
    const b1 = c1.body as Record<string, Json>;
    assert.equal(b1["crossCheck"], null, "the first receipt of a claim has nothing to cross-check");
    assert.ok(await verifySeal(w.logKey.publicKey, String(b1["id"]), String(b1["seal"])), "anyone can check the seal against the log key");
    assert.equal(b1["seed"], await seedFromSeal(String(b1["seal"])));
    const bad = await w.commit("Bee", "ecd:nothere#C1", w.bundle(2));
    assert.equal(bad.status, 404);
    const forged = await w.svc.commitCheck({ payload: { protocol: "ecdysis/0.2", type: "check.commit", target: ref, kind: "replication", bundle: w.bundle(3) as unknown as Json, agent: { handle: "Bee", publicKey: w.keys.get("Bee")!.publicKey }, ts: "2026-10-03T09:00:00Z" }, signature: "AAAA".repeat(20) });
    assert.equal(forged.status, 401);
  });

  it("assigns cross-checks among independent operators, verifies on a match, and the scores follow from the log", async () => {
    const w = await world();
    await w.agent("Ant", "op-a", ["claude"]);
    await w.agent("Bee", "op-b", ["gpt"]);
    await w.agent("Cat", "op-c", ["gemini"]);
    const ext = await w.svc.registerExternalClaim(await w.sign("Ant", { protocol: "ecdysis/0.2", type: "claim.external", source: "arxiv:2203.15556", quote: "the compute-optimal token count scales linearly with parameters", test: "exponent outside [0.9, 1.1]", agent: { handle: "Ant", publicKey: w.keys.get("Ant")!.publicKey }, ts: "2026-10-03T09:00:00Z" }));
    const ref = String((ext.body as Record<string, Json>)["ref"]);
    const c1 = await w.commit("Bee", ref, w.bundle(1));
    const id1 = String((c1.body as Record<string, Json>)["id"]);
    const r1 = await w.result("Bee", id1, "confirmed", { alpha: 1.02, solver: "x" }, null);
    assert.equal(r1.status, 201, JSON.stringify(r1.body));
    // Bee cannot cross-check itself: its second receipt on the same claim gets no cross-check; Cat's does.
    const c1b = await w.commit("Bee", ref, w.bundle(9));
    assert.equal((c1b.body as Record<string, Json>)["crossCheck"], null);
    const c2 = await w.commit("Cat", ref, w.bundle(2));
    const b2 = c2.body as Record<string, Json>;
    const cross = b2["crossCheck"] as Record<string, Json>;
    assert.equal(cross["receipt"], id1, "Cat is assigned Bee's receipt");
    assert.equal((cross["bundle"] as Record<string, Json>)["run"], "python run.py", "with the bundle to run");
    const r2 = await w.result("Cat", String(b2["id"]), "confirmed", { alpha: 1.0, solver: "y" }, { receipt: id1, outputs: { alpha: 1.025, solver: "x" } });
    assert.equal(r2.status, 201, JSON.stringify(r2.body));
    assert.equal((r2.body as Record<string, Json>)["crossMatch"], true, "within the declared tolerance of 0.01");
    const rec = await w.svc.record();
    assert.deepEqual(rec.checks.get(id1)!.verifiedBy, [String(b2["id"])]);
    const scores = await w.svc.scores();
    const claim = scores.claims.get(ref)!;
    assert.equal(claim.status, "supported", "two verified confirming replications from newcomers (reliability ½) do not yet clear the bar of 0.9");
    assert.deepEqual(claim.families, ["gemini", "gpt"], "but the diversity for 'established' is there once the evidence is");
    assert.ok(claim.credence > 0.8 && claim.credence < 0.9);
    // A result for someone else's commitment, or a second result, is refused.
    const again = await w.result("Cat", String(b2["id"]), "confirmed", { alpha: 1, solver: "y" }, { receipt: id1, outputs: { alpha: 1, solver: "x" } });
    assert.equal(again.status, 409);
    const theirs = await w.result("Ant", String(b2["id"]), "confirmed", { alpha: 1, solver: "y" }, null);
    assert.equal(theirs.status, 403);
  });

  it("a disagreement opens a finding; it is decided only with four independent runs, as fabrication only when determinism was observed", async () => {
    const w = await world();
    await w.agent("Ant", "op-a", ["claude"]);
    await w.agent("Liar", "op-l", ["gpt"]);
    await w.agent("Cat", "op-c", ["gemini"]);
    await w.agent("Dog", "op-d", ["grok"]);
    await w.agent("Emu", "op-e", ["mistral"]);
    const ext = await w.svc.registerExternalClaim(await w.sign("Ant", { protocol: "ecdysis/0.2", type: "claim.external", source: "arxiv:1706.03762", quote: "attention alone reaches 28.4 BLEU on WMT14 En-De", test: "BLEU below 27 with the stated setup", agent: { handle: "Ant", publicKey: w.keys.get("Ant")!.publicKey }, ts: "2026-10-03T09:00:00Z" }));
    const ref = String((ext.body as Record<string, Json>)["ref"]);
    const liar = await w.commit("Liar", ref, w.bundle(1));
    const idL = String((liar.body as Record<string, Json>)["id"]);
    await w.result("Liar", idL, "confirmed", { alpha: 28.4, solver: "x" }, null);
    // Cat re-runs Liar's bundle under Liar's seed and gets something else.
    const cat = await w.commit("Cat", ref, w.bundle(2));
    const idC = String((cat.body as Record<string, Json>)["id"]);
    assert.equal(((cat.body as Record<string, Json>)["crossCheck"] as Record<string, Json>)["receipt"], idL);
    const rc = await w.result("Cat", idC, "failed", { alpha: 26.1, solver: "y" }, { receipt: idL, outputs: { alpha: 26.0, solver: "x" } });
    assert.equal((rc.body as Record<string, Json>)["crossMatch"], false);
    let finding = (rc.body as Record<string, Json>)["finding"] as Record<string, Json>;
    assert.equal(finding["status"], "open");
    assert.equal(finding["need"], 2, "two runs so far (Liar's own and Cat's); four are needed");
    // Dog is drawn to the disputed receipt first, and agrees with Cat.
    const dog = await w.commit("Dog", ref, w.bundle(3));
    const idD = String((dog.body as Record<string, Json>)["id"]);
    assert.equal(((dog.body as Record<string, Json>)["crossCheck"] as Record<string, Json>)["receipt"], idL, "disputes first");
    const rd = await w.result("Dog", idD, "failed", { alpha: 26.2, solver: "y" }, { receipt: idL, outputs: { alpha: 26.0, solver: "x" } });
    finding = (rd.body as Record<string, Json>)["finding"] as Record<string, Json>;
    assert.equal(finding["status"], "open", "three runs, two against one: still not a verdict");
    assert.equal(finding["need"], 1);
    let scores = await w.svc.scores();
    assert.equal(scores.claims.get(ref)!.status, "contested", "meanwhile the disagreement is visible");
    // Emu's run agrees with Cat and Dog exactly: four runs, all but one agree. Determinism was observed (Cat and Dog matched exactly, pinned image), so this is fabrication.
    const emu = await w.commit("Emu", ref, w.bundle(4));
    const idE = String((emu.body as Record<string, Json>)["id"]);
    const re = await w.result("Emu", idE, "failed", { alpha: 26.3, solver: "y" }, { receipt: idL, outputs: { alpha: 26.0, solver: "x" } });
    finding = (re.body as Record<string, Json>)["finding"] as Record<string, Json>;
    assert.equal(finding["status"], "decided");
    assert.equal(finding["verdict"], "fabrication");
    assert.equal(finding["oddCommit"], idL);
    assert.equal(finding["deterministic"], true);
    // Not in force until the appeal period has passed.
    let rec = await w.svc.record();
    assert.equal(rec.voidedOperators.size, 0);
    assert.equal((await w.commit("Liar", ref, w.bundle(8))).status, 201, "Liar may still commit, and appeal, within the window");
    w.tick(15 * 24 * 3600 * 1000);
    rec = await w.svc.record();
    assert.deepEqual([...rec.voidedOperators], ["op-l"]);
    assert.equal((await w.commit("Liar", ref, w.bundle(7))).status, 403, "in force: the operator cannot commit");
    scores = await w.svc.scores();
    assert.equal(scores.claims.get(ref)!.status, "refuted", "three independent failures, the fabrication void");
    // A steward reverses: everything comes back.
    const rev = await w.svc.reverseFinding(String(finding["id"]));
    assert.equal(rev.status, 200);
    rec = await w.svc.record();
    assert.equal(rec.voidedOperators.size, 0);
  });

  it("without a pinned image the same disagreement is irreproducible, not fabrication", async () => {
    const w = await world();
    await w.agent("Ant", "op-a");
    await w.agent("Liar", "op-l");
    await w.agent("Cat", "op-c");
    await w.agent("Dog", "op-d");
    await w.agent("Emu", "op-e");
    const ext = await w.svc.registerExternalClaim(await w.sign("Ant", { protocol: "ecdysis/0.2", type: "claim.external", source: "arxiv:1706.03762", quote: "attention alone reaches 28.4 BLEU on WMT14 En-De", test: "BLEU below 27 with the stated setup", agent: { handle: "Ant", publicKey: w.keys.get("Ant")!.publicKey }, ts: "2026-10-03T09:00:00Z" }));
    const ref = String((ext.body as Record<string, Json>)["ref"]);
    const liar = await w.commit("Liar", ref, w.bundle(1, false));
    const idL = String((liar.body as Record<string, Json>)["id"]);
    await w.result("Liar", idL, "confirmed", { alpha: 28.4, solver: "x" }, null);
    let last: Record<string, Json> = {};
    for (const [h, n] of [["Cat", 2], ["Dog", 3], ["Emu", 4]] as const) {
      const c = await w.commit(h, ref, w.bundle(n, false));
      const r = await w.result(h, String((c.body as Record<string, Json>)["id"]), "failed", { alpha: 26, solver: "y" }, { receipt: idL, outputs: { alpha: 26.0, solver: "x" } });
      last = r.body as Record<string, Json>;
    }
    const finding = last["finding"] as Record<string, Json>;
    assert.equal(finding["verdict"], "irreproducible");
    assert.equal(finding["deterministic"], false);
    const rec = await w.svc.record();
    assert.equal(rec.voidedOperators.size, 0, "nobody is voided");
    assert.equal(rec.lapses.get("Liar"), 1, "a mark on the record");
  });

  it("a sealed check not reported within the deadline lapses, and cannot be filed afterwards", async () => {
    const w = await world();
    await w.agent("Ant", "op-a");
    await w.agent("Bee", "op-b");
    const ext = await w.svc.registerExternalClaim(await w.sign("Ant", { protocol: "ecdysis/0.2", type: "claim.external", source: "arxiv:1706.03762", quote: "attention alone reaches 28.4 BLEU on WMT14 En-De", test: "BLEU below 27 with the stated setup", agent: { handle: "Ant", publicKey: w.keys.get("Ant")!.publicKey }, ts: "2026-10-03T09:00:00Z" }));
    const ref = String((ext.body as Record<string, Json>)["ref"]);
    const c = await w.commit("Bee", ref, w.bundle(1));
    const id = String((c.body as Record<string, Json>)["id"]);
    assert.deepEqual((await w.svc.sweepLapses()).lapsed, []);
    w.tick(RESULT_DEADLINE_MS + 1000);
    const late = await w.result("Bee", id, "confirmed", { alpha: 1, solver: "x" }, null);
    assert.equal(late.status, 409);
    assert.deepEqual((await w.svc.sweepLapses()).lapsed, [id]);
    const rec = await w.svc.record();
    assert.equal(rec.checks.get(id)!.stage, "lapsed");
    assert.equal(rec.lapses.get("Bee"), 1);
    assert.equal(rec.evidence.length, 0);
  });
});
