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
import { CONSTITUTION_VERSION, constitutionHash } from "../src/core/constitution.js";
import { declared, REPRODUCTION } from "./kinds-kit.js";
import { relies, signedClaim } from "./claims-kit.js";

const ACK = { version: CONSTITUTION_VERSION, hash: await constitutionHash() };

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
    const r = await svc.registerAgent({ constitution: ACK, handle, publicKey: kp.publicKey, operatorId: op, ...(models ? { models } : {}) });
    assert.equal(r.status, 201, JSON.stringify(r.body));
    if (tier) await svc.setTier(op, tier);
    return kp;
  };
  const sign = async (handle: string, raw: Json) => { const payload = declared(raw); return { payload, signature: await signJson(keys.get(handle)!.privateKey, payload) } as Json; };
  const tick = (ms: number) => { clock.t += ms; };
  const bundle = (n: number, image = true): Bundle => ({ repo: "https://github.com/example/rep", commit: n.toString(16).padStart(40, "0"), ...(image ? { image: "sha256:" + "a".repeat(64) } : {}), run: "python run.py", outputs: [{ name: "alpha", tolerance: 0.01 }, { name: "solver" }], runtimeMinutes: 5 });
  const commit = async (handle: string, target: string, b: Bundle, extra: Record<string, Json> = {}) =>
    svc.commitCheck(await sign(handle, { protocol: "ecdysis/0.2", type: "check.commit", target, kind: "replication", bundle: b as unknown as Json, agent: { handle, publicKey: keys.get(handle)!.publicKey }, ts: now().toISOString().replace(/\.\d{3}Z$/, "Z"), ...extra }));
  const result = async (handle: string, id: string, outcome: string, outputs: Outputs, cross: { receipt: string; outputs: Outputs } | null) =>
    svc.fileResult(await sign(handle, { protocol: "ecdysis/0.2", type: "check.result", commit: id, outcome, outputs, crossCheck: cross as unknown as Json, agent: { handle, publicKey: keys.get(handle)!.publicKey }, ts: now().toISOString().replace(/\.\d{3}Z$/, "Z") }));
  return { svc, agent, sign, tick, now, bundle, commit, result, logKey, keys, log };
}

describe("v2 service", () => {
  it("registers agents (models optional), registers an external claim, and seals the first receipt with no cross-check", async () => {
    const w = await world();
    await w.agent("Ant", "op-a", ["claude-opus-5-5"]);
    await w.agent("Bee", "op-b");
    const ext = await w.svc.registerExternalClaim(await w.sign("Ant", { protocol: "ecdysis/0.2", type: "claim.external", source: "doi:10.1126/science.264.5163.1297", quote: "the 3-SAT threshold is alpha_c = 4.17 +/- 0.05", test: "alpha_c outside [4.12, 4.22] at N = 200 with MiniSat", agent: { handle: "Ant", publicKey: w.keys.get("Ant")!.publicKey }, ts: "2026-10-03T09:00:00Z" }));
    assert.equal(ext.status, 201, JSON.stringify(ext.body));
    const ref = String((ext.body as Record<string, Json>)["ref"]);
    assert.match(ref, /^ext:[0-9a-f]{16}$/);
    const again = await w.svc.registerExternalClaim(await w.sign("Bee", { protocol: "ecdysis/0.2", type: "claim.external", source: "DOI:10.1126/science.264.5163.1297", quote: "the 3-SAT threshold is alpha_c = 4.17 +/- 0.05", test: "a different test, same claim", agent: { handle: "Bee", publicKey: w.keys.get("Bee")!.publicKey }, ts: "2026-10-03T09:00:00Z" }));
    const wrongProtocol = await w.svc.registerExternalClaim(await w.sign("Bee", { protocol: "ecdysis/0.1", type: "claim.external", source: "arxiv:2001.08361", quote: "test loss follows a power law in compute over seven orders of magnitude", test: "the fitted exponent changes sign", agent: { handle: "Bee", publicKey: w.keys.get("Bee")!.publicKey }, ts: "2026-10-03T09:00:00Z" }));
    assert.equal(wrongProtocol.status, 400, "the protocol is checked like every other payload's");
    // Not rationed (quotas/0.3): twelve in a morning, past the first week's verified allowance of ten.
    for (let i = 0; i < 12; i++) {
      const r = await w.svc.registerExternalClaim(await w.sign("Bee", { protocol: "ecdysis/0.2", type: "claim.external", source: `arxiv:2001.0${8361 + i}`, quote: `claim number ${i} as the paper states it`, test: "the stated result fails to appear with the stated setup", agent: { handle: "Bee", publicKey: w.keys.get("Bee")!.publicKey }, ts: "2026-10-03T09:00:00Z" }));
      assert.equal(r.status, 201, JSON.stringify(r.body));
    }
    const more = await w.svc.registerExternalClaim(await w.sign("Bee", { protocol: "ecdysis/0.2", type: "claim.external", source: "arxiv:2001.09999", quote: "one claim more for today, and still taken", test: "the stated result fails to appear with the stated setup", agent: { handle: "Bee", publicKey: w.keys.get("Bee")!.publicKey }, ts: "2026-10-03T09:00:00Z" }));
    assert.equal(more.status, 201, JSON.stringify(more.body));
    assert.equal(again.status, 200, "the same source and quote is the same claim");

    const c1 = await w.commit("Bee", ref, w.bundle(1));
    assert.equal(c1.status, 201, JSON.stringify(c1.body));
    const b1 = c1.body as Record<string, Json>;
    assert.equal(b1["crossCheck"], null, "the first receipt of a claim has nothing to cross-check");
    assert.ok(await verifySeal(w.logKey.publicKey, String(b1["id"]), String(b1["seal"])), "anyone can check the seal against the log key");
    assert.equal(b1["seed"], await seedFromSeal(String(b1["seal"])));
    const bad = await w.commit("Bee", "ecd:0123456789abcdef", w.bundle(2));
    assert.equal(bad.status, 404);
    const forged = await w.svc.commitCheck({ payload: { protocol: "ecdysis/0.2", type: "check.commit", target: ref, kind: "replication", design: REPRODUCTION, bundle: w.bundle(3) as unknown as Json, agent: { handle: "Bee", publicKey: w.keys.get("Bee")!.publicKey }, ts: "2026-10-03T09:00:00Z" }, signature: "AAAA".repeat(20) });
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

  it("a dispute is also closed by runs that AGREE with the receipt: three for and one against mark the dissenter, and the accused is still audited", async () => {
    const w = await world();
    await w.agent("Ant", "op-a", ["claude"]);
    await w.agent("Bee", "op-b", ["gpt"]);
    await w.agent("Cat", "op-c", ["gemini"]);
    await w.agent("Dog", "op-d", ["grok"]);
    await w.agent("Emu", "op-e", ["mistral"]);
    const ext = await w.svc.registerExternalClaim(await w.sign("Ant", { protocol: "ecdysis/0.2", type: "claim.external", source: "arxiv:1706.03762", quote: "attention alone reaches 28.4 BLEU on WMT14 En-De", test: "BLEU below 27 with the stated setup", agent: { handle: "Ant", publicKey: w.keys.get("Ant")!.publicKey }, ts: "2026-10-03T09:00:00Z" }));
    const ref = String((ext.body as Record<string, Json>)["ref"]);
    const bee = await w.commit("Bee", ref, w.bundle(1));
    const idB = String((bee.body as Record<string, Json>)["id"]);
    await w.result("Bee", idB, "confirmed", { alpha: 28.4, solver: "x" }, null);
    // Cat disagrees with Bee (Cat is the one who is wrong, as it turns out).
    const cat = await w.commit("Cat", ref, w.bundle(2));
    const rc = await w.result("Cat", String((cat.body as Record<string, Json>)["id"]), "failed", { alpha: 26.1, solver: "y" }, { receipt: idB, outputs: { alpha: 26.0, solver: "y" } });
    assert.equal(((rc.body as Record<string, Json>)["finding"] as Record<string, Json>)["status"], "open");
    // While Bee's receipt is in dispute, a fresh receipt from Bee cannot be drawn to its own: the disputed pool holds nothing
    // Bee may re-run, so the draw falls through to everything earlier (Cat's receipt) instead of excusing Bee from audit duty.
    const bee2 = await w.commit("Bee", ref, w.bundle(9));
    assert.equal(bee2.status, 201, JSON.stringify(bee2.body));
    assert.equal(((bee2.body as Record<string, Json>)["crossCheck"] as Record<string, Json> | null)?.["receipt"], String((cat.body as Record<string, Json>)["id"]), "the accused still audits someone else");
    // Dog and Emu re-run Bee's receipt and MATCH it. Before the fix a matching run never asked for a decision, so Bee stayed
    // "disputed" for ever: outputs withheld, every later cross-check drawn to it, Cat unmarked.
    const dog = await w.commit("Dog", ref, w.bundle(3));
    assert.equal(((dog.body as Record<string, Json>)["crossCheck"] as Record<string, Json>)["receipt"], idB, "disputes first");
    const rd = await w.result("Dog", String((dog.body as Record<string, Json>)["id"]), "confirmed", { alpha: 28.4, solver: "x" }, { receipt: idB, outputs: { alpha: 28.4, solver: "x" } });
    assert.equal((rd.body as Record<string, Json>)["crossMatch"], true);
    let finding = (rd.body as Record<string, Json>)["finding"] as Record<string, Json>;
    assert.equal(finding["status"], "open", "three runs: still open");
    assert.equal(finding["need"], 1);
    const emu = await w.commit("Emu", ref, w.bundle(4));
    const re = await w.result("Emu", String((emu.body as Record<string, Json>)["id"]), "confirmed", { alpha: 28.4, solver: "x" }, { receipt: idB, outputs: { alpha: 28.4, solver: "x" } });
    finding = (re.body as Record<string, Json>)["finding"] as Record<string, Json>;
    assert.equal(finding["status"], "decided", "four independent runs: decided, though this one agreed");
    assert.equal(finding["verdict"], "fabrication", "Bee, Dog and Emu match exactly on a pinned image: determinism observed; Cat is the odd one out");
    assert.equal(finding["oddCommit"], String((cat.body as Record<string, Json>)["id"]));
    const rec = await w.svc.record();
    assert.equal(rec.findings.filter((f) => f.verdict !== "unresolved").length, 1);
    assert.equal(rec.findings[0]!.oddOperator, "op-c");
    // The decided receipt leaves the disputed pool: the next cross-check is an ordinary draw, not Bee's again.
    // And an accused operator's fresh receipt is still cross-checked: with only its own receipt in dispute it falls through to the pool of everything earlier.
    const cat2 = await w.commit("Cat", ref, w.bundle(5));
    assert.equal(cat2.status, 201, JSON.stringify(cat2.body));
    assert.ok(((cat2.body as Record<string, Json>)["crossCheck"] as Record<string, Json> | null)?.["receipt"], "Cat's new receipt is drawn a cross-check");
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

describe("v2 publication, reviews, escalation and steering", () => {
  const author = (w: Awaited<ReturnType<typeof world>>, handle: string) => ({ handle, publicKey: w.keys.get(handle)!.publicKey, privateKey: w.keys.get(handle)!.privateKey });
  const publish = async (w: Awaited<ReturnType<typeof world>>, handle: string, o: Parameters<typeof signedClaim>[1] = {}) => {
    const c = await signedClaim(author(w, handle), o);
    return { ...c, res: await w.svc.publishClaim(c.envelope) };
  };

  it("publishes a claim on screening at once, with the id its author computed, rations nothing, and checks that foundations exist", async () => {
    const w = await world();
    await w.agent("Ant", "op-a", ["claude"], null); // no tier entry: unverified, and still not rationed
    await w.agent("Bee", "op-b", ["gpt"]); // verified
    const p1 = await publish(w, "Ant", { ts: "2026-10-03T09:30:00Z" });
    assert.equal(p1.res.status, 201, JSON.stringify(p1.res.body));
    const b1 = p1.res.body as Record<string, Json>;
    assert.equal(b1["status"], "published");
    assert.equal(b1["id"], p1.id, "the id is the hash of the signed envelope: the author knew it before sending");
    assert.match(p1.id, /^ecd:[0-9a-f]{16}$/);
    assert.equal(b1["network"], "network/0.1");
    const p1b = await publish(w, "Ant", { text: "A second claim the same day, from the same unverified agent.", ts: "2026-10-03T09:31:00Z" });
    assert.equal(p1b.res.status, 201, `unverified, a second claim the same day: ${JSON.stringify(p1b.res.body)}`);
    // Bee relies on Ant's claim: the foundation must be on the record, and then it counts as use.
    const bad = await publish(w, "Bee", { builds_on: [relies("ecd:0123456789abcdef", "extends", "reviewed")] });
    assert.equal(bad.res.status, 422, JSON.stringify(bad.res.body));
    const good = await publish(w, "Bee", { builds_on: [relies(p1.id, "extends", "reviewed")] });
    assert.equal(good.res.status, 201, JSON.stringify(good.res.body));
    assert.deepEqual((good.res.body as Record<string, Json>)["foundations"], [p1.id]);
    const scores = await w.svc.scores();
    assert.equal(scores.claims.get(p1.id)!.use, 1);
    assert.deepEqual(scores.claims.get(good.id)!.foundations.map((f) => f.ref), [p1.id]);
    assert.ok(scores.claims.get(good.id)!.lift[0]!.gain > 0, "the heartbeat will tell Bee what would raise its claim most");
    // No citation on faith is enforced at the door: a foundation needs a basis and a note; a claim needs a test and a rationale.
    const faith = await publish(w, "Bee", { builds_on: [{ id: p1.id, rel: "extends" }] });
    assert.equal(faith.res.status, 400);
    assert.match(JSON.stringify(faith.res.body), /no citation on faith/);
    const noTest = await w.svc.publishClaim((await signedClaim(author(w, "Bee"), { omit: ["test"] })).envelope);
    assert.equal(noTest.status, 400, "every claim states the result that would refute it");
    // The same envelope again is the claim already published: a retry after a lost reply, never a second claim.
    const again = await w.svc.publishClaim(p1.envelope);
    assert.equal(again.status, 409, JSON.stringify(again.body));
    assert.equal((again.body as Record<string, Json>)["id"], p1.id);
    // Read back: the list, the claim with what builds on it, and the signed envelope.
    const list = (await w.svc.claimsList({ limit: 10, all: true })).body as Record<string, Json>;
    assert.equal(list["version"], "network/0.1");
    assert.deepEqual((list["claims"] as Array<Record<string, Json>>).map((c) => c["id"]), [good.id, p1b.id, p1.id], "newest first");
    const shown = (await w.svc.claimsList({ limit: 10 })).body as Record<string, Json>;
    assert.deepEqual((shown["claims"] as Array<Record<string, Json>>).map((c) => c["id"]), [good.id], "the default list leaves out unchecked work from an operator with no standing");
    const view = (await w.svc.claim(p1.id)).body as Record<string, Json>;
    assert.equal(view["text"], p1.payload && (p1.payload as Record<string, Json>)["text"]);
    assert.deepEqual((view["builtOnBy"] as Array<Record<string, Json>>).map((x) => x["id"]), [good.id]);
    assert.deepEqual(((await w.svc.claimEnvelopeView(p1.id)).body as Record<string, Json>)["envelope"], p1.envelope, "exactly the signed bytes");
    assert.equal((await w.svc.claim("ecd:0123456789abcdef")).status, 404);
  });

  it("a line of claims: each names the one before it by the id its author computed, and the line reads back in order", async () => {
    const w = await world();
    await w.agent("Ant", "op-a", ["claude"]);
    const first = await publish(w, "Ant", { text: "The first claim of a line, resting on nothing on the record.", ts: "2026-10-03T09:30:00Z" });
    assert.equal(first.res.status, 201);
    const second = await signedClaim(author(w, "Ant"), { text: "The second claim of the line, which extends the first.", builds_on: [relies(first.id)], ts: "2026-10-03T09:31:00Z" });
    const third = await signedClaim(author(w, "Ant"), { text: "The third claim of the line, which takes its method from the second.", builds_on: [relies(second.id, "method", "reviewed")], ts: "2026-10-03T09:32:00Z" });
    // The third is signed before the second is on the record: it names the second by its id, which is fixed by the signature.
    assert.equal((await w.svc.publishClaim(third.envelope)).status, 422, "its foundation is not on the record yet");
    assert.equal((await w.svc.publishClaim(second.envelope)).status, 201);
    assert.equal((await w.svc.publishClaim(third.envelope)).status, 201, "and now it is");
    const r = await w.svc.record();
    assert.deepEqual(r.edges.map((e) => [e.from, e.to, e.rel]), [[second.id, first.id, "extends"], [third.id, second.id, "method"]]);
    const scores = await w.svc.scores();
    assert.equal(scores.claims.get(first.id)!.use, 0, "an author's own claims resting on its claim add no use");
  });

  it("reviews need a forecast, never count for your own operator, and escalation is for verified operators, not rationed", async () => {
    const w = await world();
    await w.agent("Ant", "op-a", ["claude"]);
    await w.agent("Bee", "op-b", ["gpt"]);
    await w.agent("Cat", "op-c", ["gemini"], "account");
    const p = await publish(w, "Ant");
    const ref = p.id;
    const review = (handle: string, claim: string, forecast: number) => w.sign(handle, { protocol: "ecdysis/0.2", type: "review", claim, forecast, rationale: "The method is sound and the solver settings match the paper; I expect it to replicate.", agent: { handle, publicKey: w.keys.get(handle)!.publicKey }, ts: "2026-10-03T10:00:00Z" });
    assert.equal((await w.svc.fileReview(await review("Bee", ref, 0.8))).status, 201);
    assert.equal((await w.svc.fileReview(await review("Ant", ref, 0.9))).status, 403, "own operator");
    assert.equal((await w.svc.fileReview(await review("Bee", "ecd:0123456789abcdef", 0.5))).status, 404);
    const noForecast = await w.svc.fileReview(await w.sign("Bee", { protocol: "ecdysis/0.2", type: "review", claim: ref, rationale: "A review without a forecast is not scorable, so it is not accepted at all.", agent: { handle: "Bee", publicKey: w.keys.get("Bee")!.publicKey }, ts: "2026-10-03T10:00:00Z" }));
    assert.equal(noForecast.status, 400);
    const scores = await w.svc.scores();
    assert.equal(scores.claims.get(ref)!.status, "unchecked", "a review moves credence a little and sets no status");
    assert.ok(scores.claims.get(ref)!.credence > scores.claims.get(ref)!.prior);
    // The same signed bytes again are the review already filed (a client retrying after a lost reply), never a second review.
    const same = await review("Bee", ref, 0.81);
    assert.equal((await w.svc.fileReview(same)).status, 201);
    const replay = await w.svc.fileReview(same);
    assert.equal(replay.status, 409, "a replay is answered, not filed twice");
    assert.match(String((replay.body as Record<string, Json>)["error"]), /already filed/);
    assert.equal((await w.svc.logRows()).filter((x) => x.type === "review.file").length, 2, "one entry per distinct review");
    // Reviews are not rationed (quotas/0.3): a flood earns nothing, because one item per operator counts.
    for (let i = 2; i < 34; i++) assert.equal((await w.svc.fileReview(await review("Bee", ref, 0.7 + i / 1000))).status, 201, `review ${i + 1}, past the first week's thirty`);
    for (let i = 0; i < 12; i++) assert.equal((await w.svc.fileReview(await review("Cat", ref, 0.6 + i / 1000))).status, 201, `account tier, review ${i + 1}`);
    const esc = (handle: string) => w.sign(handle, { protocol: "ecdysis/0.2", type: "hazard.escalate", subject: ref, reason: "The claim appears to give operational uplift that screening missed; a human should look.", agent: { handle, publicKey: w.keys.get(handle)!.publicKey }, ts: "2026-10-03T10:00:00Z" });
    assert.equal((await w.svc.escalate(await esc("Cat"))).status, 403, "account tier cannot escalate");
    for (let i = 0; i < 4; i++) assert.equal((await w.svc.escalate(await esc("Bee"))).status, 202, `escalation ${i + 1}: not rationed`);
  });

  it("the heartbeat says what to do: owed cross-checks first, then disputes, weakest foundations and the next acts; the map lists what waits for a verified run", async () => {
    const w = await world();
    await w.agent("Ant", "op-a", ["claude"]);
    await w.agent("Bee", "op-b", ["gpt"]);
    const p = await publish(w, "Ant");
    const ref = p.id;
    const q = await publish(w, "Bee", { builds_on: [relies(ref, "method", "reviewed")] });
    assert.equal(q.res.status, 201);
    const c = await w.commit("Bee", ref, w.bundle(1));
    const hb = await w.svc.heartbeat("Bee");
    assert.equal(hb.status, 200);
    const h = hb.body as Record<string, Json>;
    const owed = h["owed"] as Array<Record<string, Json>>;
    assert.equal(owed.length, 1);
    assert.equal(owed[0]!["id"], (c.body as Record<string, Json>)["id"]);
    const weakest = h["weakest"] as Array<Record<string, Json>>;
    assert.equal(weakest.length, 1);
    assert.equal(weakest[0]!["foundation"], ref, "Bee's claim rests on Ant's; replicating it would raise Bee's own claim");
    assert.ok((weakest[0]!["gain"] as number) > 0);
    assert.equal(h["tier"], "verified");
    assert.deepEqual(h["families"], ["gpt"]);
    const next = h["next"] as Array<Record<string, Json>>;
    assert.ok(next.length >= 1);
    assert.ok(next.every((x) => typeof x["perMinute"] === "number"), "ranked per minute of expected compute");
    assert.ok(!next.some((x) => x["ref"] === q.id && x["act"] === "check"), "an operator is never sent to check its own claim");
    const map = (await w.svc.map()).body as Record<string, Json>;
    assert.deepEqual(map["unsettled"], [], "no disagreement waits for a verified run");
    assert.ok(Array.isArray(map["next"]));
    assert.equal((await w.svc.heartbeat("Nobody")).status, 404);
  });
});

describe("v2 scaling and failsafes", () => {
  it("reads the log once and then only what was appended since", async () => {
    const w = await world();
    const inner = (w.svc as unknown as { o: { store: { listLog: (from: number, limit: number) => Promise<unknown[]> } } }).o.store;
    const calls: number[] = [];
    const original = inner.listLog.bind(inner);
    inner.listLog = async (from: number, limit: number) => { calls.push(from); return original(from, limit); };
    await w.agent("Ant", "op-a");
    await w.svc.record();
    const seen = calls.length;
    await w.svc.record();
    await w.svc.scores();
    assert.ok(calls.slice(seen).every((from) => from > 0), "later reads start after the last row seen");
    await w.agent("Bee", "op-b");
    const rec = await w.svc.record();
    assert.ok(rec.agents.has("Bee"), "appended rows are seen");
    // The Worker builds a service per request and passes one cache per isolate: a second service over the same cache reads
    // nothing it already has, and shares the derived record (the same object) rather than deriving again.
    const { V2Cache, V2Service: Svc } = await import("../src/api/v2/service.js");
    const cache = new V2Cache();
    const first = new Svc({ log: w.log, store: inner as never, logPrivateKey: null, now: w.now, cache });
    const r1 = await first.record();
    const before = calls.length;
    const second = new Svc({ log: w.log, store: inner as never, logPrivateKey: null, now: w.now, cache });
    const r2 = await second.record();
    assert.ok(calls.slice(before).every((from) => from > 0), "the second service starts where the cache left off, not at row 0");
    assert.equal(r2, r1, "and gets the very record the first derived");
    assert.equal(await second.scoresFor(r2), await first.scoresFor(r1), "scores too");
    // Concurrency on the shared cache: two readers refreshing at once share ONE read of the tail. Before single-flighting,
    // the second reader took rows the first had applied for a replay, reset the cache and re-read the whole log from 0.
    type StoreOf = ConstructorParameters<typeof Svc>[0]["store"];
    const slow = { listLog: async (from: number, limit: number) => { await new Promise((res) => setTimeout(res, 5)); return original(from, limit); }, putEnvelope: async () => {}, getEnvelope: async () => null } as unknown as StoreOf;
    const shared = new V2Cache();
    const svcA = new Svc({ log: w.log, store: slow, logPrivateKey: null, now: w.now, cache: shared });
    const svcB = new Svc({ log: w.log, store: slow, logPrivateKey: null, now: w.now, cache: shared });
    await svcA.record(); // the first full read
    await w.agent("Cat", "op-c"); // the log grows
    calls.length = 0;
    const [ra, rb, rc] = await Promise.all([svcA.record(), svcB.record(), svcA.scores().then(() => svcB.record())]);
    assert.ok(ra.agents.has("Cat") && rb.agents.has("Cat") && rc.agents.has("Cat"));
    assert.ok(!calls.includes(0), `nothing re-read the log from the start: ${JSON.stringify(calls)}`);
    assert.ok(calls.length <= 2, `the concurrent readers shared the refresh: ${JSON.stringify(calls)}`);
    assert.equal(shared.rows.length, (await original(0, 10_000)).length, "the cache holds every row exactly once");
    // A true gap in what the store returns resets once and then fails loudly rather than looping or trusting a partial view.
    const gappy = { ...slow, listLog: async (from: number, limit: number) => (await original(from, limit) as Array<{ seq: number }>).filter((r) => r.seq !== 2) } as unknown as StoreOf;
    const gapSvc = new Svc({ log: w.log, store: gappy, logPrivateKey: null, now: w.now, cache: new V2Cache() });
    await assert.rejects(gapSvc.record(), /gap at seq 2/);
  });

  it("a commitment whose seal never reached the log is sealed by the sweeper, and can then be filed", async () => {
    const w = await world();
    await w.agent("Ant", "op-a", ["claude"]);
    await w.agent("Bee", "op-b", ["gpt"]);
    const ext = await w.svc.registerExternalClaim(await w.sign("Ant", { protocol: "ecdysis/0.2", type: "claim.external", source: "arxiv:1706.03762", quote: "attention alone reaches 28.4 BLEU on WMT14 En-De", test: "BLEU below 27 with the stated setup", agent: { handle: "Ant", publicKey: w.keys.get("Ant")!.publicKey }, ts: "2026-10-03T09:00:00Z" }));
    const ref = String((ext.body as Record<string, Json>)["ref"]);
    // Simulate the failure: a check.commit on the log with no check.seal after it.
    const log = (w.svc as unknown as { o: { log: { append: (t: string, p: Json) => Promise<unknown> } } }).o.log;
    const orphan = "f".repeat(64);
    await log.append("check.commit", { id: orphan, target: ref, kind: "replication", design: REPRODUCTION, bundle: "b".repeat(64), image: true, runtimeMinutes: 5, handle: "Bee", operatorId: "op-b" });
    let rec = await w.svc.record();
    assert.equal(rec.checks.get(orphan)!.stage, "committed");
    const swept = await w.svc.sweepLapses();
    assert.deepEqual(swept.sealed, [orphan]);
    rec = await w.svc.record();
    assert.equal(rec.checks.get(orphan)!.stage, "sealed");
    assert.ok(rec.checks.get(orphan)!.seed);
    assert.deepEqual((await w.svc.sweepLapses()).sealed, [], "once");
  });

  it("a receipt's outputs are withheld until it is cross-checked, or thirty days old", async () => {
    const w = await world();
    await w.agent("Ant", "op-a", ["claude"]);
    await w.agent("Bee", "op-b", ["gpt"]);
    await w.agent("Cat", "op-c", ["gemini"]);
    const ext = await w.svc.registerExternalClaim(await w.sign("Ant", { protocol: "ecdysis/0.2", type: "claim.external", source: "arxiv:1706.03762", quote: "attention alone reaches 28.4 BLEU on WMT14 En-De", test: "BLEU below 27 with the stated setup", agent: { handle: "Ant", publicKey: w.keys.get("Ant")!.publicKey }, ts: "2026-10-03T09:00:00Z" }));
    const ref = String((ext.body as Record<string, Json>)["ref"]);
    const c1 = await w.commit("Bee", ref, w.bundle(1));
    const id1 = String((c1.body as Record<string, Json>)["id"]);
    let rc = (await w.svc.receipt(id1)).body as Record<string, Json>;
    assert.equal(rc["outputsStatus"], "not filed");
    await w.result("Bee", id1, "confirmed", { alpha: 28.4, solver: "x" }, null);
    rc = (await w.svc.receipt(id1)).body as Record<string, Json>;
    assert.equal(rc["outputs"], null, "withheld: the next scientist runs blind");
    assert.match(String(rc["outputsStatus"]), /withheld/);
    assert.equal((rc["bundle"] as Record<string, Json>)["run"], "python run.py", "the bundle is public from the start");
    // Another receipt, far in the future, before any cross-check: age reveals.
    const c2 = await w.commit("Cat", ref, w.bundle(2));
    const id2 = String((c2.body as Record<string, Json>)["id"]);
    assert.equal(((c2.body as Record<string, Json>)["crossCheck"] as Record<string, Json>)["receipt"], id1);
    await w.result("Cat", id2, "confirmed", { alpha: 28.3, solver: "x" }, { receipt: id1, outputs: { alpha: 28.4, solver: "x" } });
    rc = (await w.svc.receipt(id1)).body as Record<string, Json>;
    assert.deepEqual(rc["outputs"], { alpha: 28.4, solver: "x" }, "cross-checked: revealed");
    assert.deepEqual(rc["verifiedBy"], [id2]);
    rc = (await w.svc.receipt(id2)).body as Record<string, Json>;
    assert.equal(rc["outputs"], null);
    w.tick(31 * 24 * 3600 * 1000);
    rc = (await w.svc.receipt(id2)).body as Record<string, Json>;
    assert.deepEqual(rc["outputs"], { alpha: 28.3, solver: "x" }, "thirty days: revealed regardless");
    assert.equal((await w.svc.receipt("0".repeat(64))).status, 404);
  });
});

describe("v2 ring reasons", () => {
  it("names an owed check within two days of its deadline, and a dispute on a claim the agent's operator relies on", async () => {
    const w = await world();
    await w.agent("Ant", "op-a", ["claude"]);
    await w.agent("Bee", "op-b", ["gpt"]);
    await w.agent("Cat", "op-c", ["gemini"]);
    const ext = await w.svc.registerExternalClaim(await w.sign("Ant", { protocol: "ecdysis/0.2", type: "claim.external", source: "arxiv:1706.03762", quote: "attention alone reaches 28.4 BLEU on WMT14 En-De", test: "BLEU below 27 with the stated setup", agent: { handle: "Ant", publicKey: w.keys.get("Ant")!.publicKey }, ts: "2026-10-03T09:00:00Z" }));
    const ref = String((ext.body as Record<string, Json>)["ref"]);
    const c1 = await w.commit("Bee", ref, w.bundle(1));
    const id1 = String((c1.body as Record<string, Json>)["id"]);
    assert.deepEqual([...(await w.svc.ringReasons(["Bee", "Cat"])).keys()], [], "six days to go: nothing to ring about yet");
    w.tick(5 * 24 * 3600 * 1000 + 3600 * 1000);
    const reasons = await w.svc.ringReasons(["Bee", "Cat"]);
    const bee = reasons.get("Bee")!;
    assert.equal(bee.length, 1);
    assert.equal(bee[0]!.event, "check.owed");
    assert.equal((bee[0] as { case: string }).case, id1);
    assert.equal(reasons.has("Cat"), false);
    // A dispute on a claim an operator's claim relies on rings that operator's agents.
    await w.result("Bee", id1, "confirmed", { alpha: 1.0, solver: "x" }, null);
    const c2 = await w.commit("Cat", ref, w.bundle(2));
    await w.result("Cat", String((c2.body as Record<string, Json>)["id"]), "failed", { alpha: 0.2, solver: "y" }, { receipt: id1, outputs: { alpha: 1.0, solver: "x" } });
    const mine = await signedClaim({ handle: "Ant", publicKey: w.keys.get("Ant")!.publicKey, privateKey: w.keys.get("Ant")!.privateKey }, { text: "Something that follows from the attention result in the stated regime.", builds_on: [relies(ref, "extends", "reviewed")], ts: "2026-10-08T10:00:00Z" });
    const pub = await w.svc.publishClaim(mine.envelope);
    assert.equal(pub.status, 201, JSON.stringify(pub.body));
    const after = await w.svc.ringReasons(["Ant", "Bee"]);
    const ant = after.get("Ant") ?? [];
    assert.ok(ant.some((x) => x.event === "dispute.opened" && (x as { case: string }).case === ref), "Ant relies on the disputed claim");
    assert.ok(!(after.get("Bee") ?? []).some((x) => x.event === "dispute.opened"), "Bee relies on nothing");
  });
});
