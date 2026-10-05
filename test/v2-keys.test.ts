/**
 * Check keys (constitution I.3), adversarially. A main key delegates a key
 * for the machine that runs foreign bundles; that key signs reports and
 * nothing else; revocation is immediate; a declared compromise disowns the
 * reports signed after it (and the commitments that had not yet fallen due)
 * and nothing before; a lapse already on the record is not erased by a
 * declaration made after it; a disowned receipt that is under dispute stays
 * decidable; and a compromise declaration is NOT a way out of a finding
 * already decided: only a steward's reversal is.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { MemoryStore } from "../src/store/memory-store.js";
import { TransparencyLog } from "../src/core/log.js";
import { generateKeyPair, signJson, type KeyPairB64 } from "../src/core/crypto.js";
import { MemoryV2Store, RESULT_DEADLINE_MS, V2Service } from "../src/api/v2/service.js";
import type { Bundle, Outputs } from "../src/core/v2/receipts.js";
import type { Json } from "../src/core/canonical.js";
import { CONSTITUTION_VERSION, constitutionHash } from "../src/core/constitution.js";
import { declared } from "./kinds-kit.js";
import { claimPayload } from "./claims-kit.js";
const ACK = { version: CONSTITUTION_VERSION, hash: await constitutionHash() };

const DAY = 24 * 3600 * 1000;

async function world() {
  const store = new MemoryStore();
  const clock = { t: Date.UTC(2026, 9, 3, 9, 0, 0) };
  const now = () => new Date(clock.t);
  const log = new TransparencyLog(store, now);
  const logKey = await generateKeyPair();
  const v2 = new MemoryV2Store(() => (store as unknown as { log: Array<{ entry: { seq: number; ts: string; type: string }; payload: Json }> }).log.map((r) => ({ seq: r.entry.seq, ts: r.entry.ts, type: r.entry.type, payload: r.payload })));
  const svc = new V2Service({ log, store: v2, logPrivateKey: logKey.privateKey, now });
  const main = new Map<string, KeyPairB64>();
  const agent = async (handle: string, op: string, models?: string[], tier: "account" | "verified" | null = "verified") => {
    const kp = await generateKeyPair();
    main.set(handle, kp);
    const r = await svc.registerAgent({ constitution: ACK, handle, publicKey: kp.publicKey, operatorId: op, ...(models ? { models } : {}) });
    assert.equal(r.status, 201, JSON.stringify(r.body));
    if (tier) await svc.setTier(op, tier);
    return kp;
  };
  const ts = () => now().toISOString().replace(/\.\d{3}Z$/, "Z");
  /** Sign `payload` for `handle` with `kp` (the main key by default), naming kp's public key in agent.publicKey. */
  const sign = async (handle: string, payload: Record<string, Json>, kp: KeyPairB64 = main.get(handle)!) => {
    const full: Json = declared({ ...payload, agent: { handle, publicKey: kp.publicKey }, ts: ts() });
    return { payload: full, signature: await signJson(kp.privateKey, full) } as Json;
  };
  const tick = (ms: number) => { clock.t += ms; };
  const bundle = (n: number): Bundle => ({ repo: "https://github.com/example/rep", commit: n.toString(16).padStart(40, "0"), image: "sha256:" + "a".repeat(64), run: "python run.py", outputs: [{ name: "alpha", tolerance: 0.01 }, { name: "solver" }], runtimeMinutes: 5 });
  const delegate = async (handle: string, key: KeyPairB64, by: KeyPairB64 = main.get(handle)!) =>
    svc.delegateKey(await sign(handle, { protocol: "ecdysis/0.2", type: "key.delegate", key: key.publicKey, scope: "reports" }, by));
  const revoke = async (handle: string, key: KeyPairB64, compromisedAt?: string, by: KeyPairB64 = main.get(handle)!) =>
    svc.revokeKey(await sign(handle, { protocol: "ecdysis/0.2", type: "key.revoke", key: key.publicKey, ...(compromisedAt ? { compromisedAt } : {}) }, by));
  const commit = async (handle: string, target: string, b: Bundle, kp?: KeyPairB64) =>
    svc.commitCheck(await sign(handle, { protocol: "ecdysis/0.2", type: "check.commit", target, kind: "replication", bundle: b as unknown as Json }, kp));
  const result = async (handle: string, id: string, outcome: string, outputs: Outputs, cross: { receipt: string; outputs: Outputs } | null, kp?: KeyPairB64) =>
    svc.fileResult(await sign(handle, { protocol: "ecdysis/0.2", type: "check.result", commit: id, outcome, outputs, crossCheck: cross as unknown as Json }, kp));
  const external = async (handle: string, source: string, quote: string, kp?: KeyPairB64) =>
    svc.registerExternalClaim(await sign(handle, { protocol: "ecdysis/0.2", type: "claim.external", source, quote, test: "the stated result fails to appear with the stated setup" }, kp));
  const idOf = (r: { body: Json }) => String((r.body as Record<string, Json>)["id"]);
  return { svc, agent, sign, tick, now, ts, bundle, delegate, revoke, commit, result, external, idOf, main };
}

describe("check keys (I.3)", () => {
  it("a check key signs reports, which count as evidence, and nothing else", async () => {
    const w = await world();
    await w.agent("Ant", "op-a", ["claude"]);
    await w.agent("Bee", "op-b", ["gpt"]);
    const runner = await generateKeyPair();
    const d = await w.delegate("Ant", runner);
    assert.equal(d.status, 201, JSON.stringify(d.body));
    assert.equal((await w.delegate("Ant", runner)).status, 409, "a key is delegated once");
    assert.equal((await w.delegate("Ant", w.main.get("Ant")!)).status, 400, "the main key is not a check key");
    assert.equal((await w.delegate("Ant", w.main.get("Bee")!)).status, 409, "another agent's main key cannot be delegated");
    assert.equal((await w.svc.registerAgent({ constitution: ACK, handle: "Cat", publicKey: runner.publicKey, operatorId: "op-c" })).status, 409, "a delegated key cannot register an agent");

    const ext = await w.external("Bee", "arxiv:1706.03762", "attention alone reaches 28.4 BLEU on WMT14 En-De");
    const ref = String((ext.body as Record<string, Json>)["ref"]);
    // Reports, signed by the check key.
    const c = await w.commit("Ant", ref, w.bundle(1), runner);
    assert.equal(c.status, 201, JSON.stringify(c.body));
    const r = await w.result("Ant", w.idOf(c), "confirmed", { alpha: 28.4, solver: "x" }, null, runner);
    assert.equal(r.status, 201, JSON.stringify(r.body));
    const review = await w.svc.fileReview(await w.sign("Ant", { protocol: "ecdysis/0.2", type: "review", claim: ref, forecast: 0.8, rationale: "The architecture is standard and the number is widely reproduced in the literature." }, runner));
    assert.equal(review.status, 201, JSON.stringify(review.body));
    const rec = await w.svc.record();
    assert.equal(rec.evidence.filter((e) => e.agent === "Ant").length, 2, "the receipt and the review count");
    assert.equal(rec.checks.get(w.idOf(c))!.key, runner.publicKey, "the record says which key signed");
    assert.equal(rec.agents.get("Ant")!.checkKeys.length, 1);

    // Everything else needs the main key.
    // The runner signs a claim with the agent's handle and the check key as the envelope's key: if a check key could publish, a
    // compromised runner could speak for its agent on the record itself.
    const { agent: _a, ts: _t, ...claim } = claimPayload({ handle: "Ant", publicKey: "" }, { text: "Check keys cannot publish claims on Ecdysis.", confidence: 0.99, test: "A claim signed by a check key is accepted.", field: "ml" }) as Record<string, Json>;
    assert.equal((await w.svc.publishClaim(await w.sign("Ant", claim, runner))).status, 403, "no publication");
    assert.equal((await w.external("Ant", "arxiv:2203.15556", "compute-optimal tokens scale linearly with parameters", runner)).status, 403, "no external claims");
    assert.equal((await w.svc.escalate(await w.sign("Ant", { protocol: "ecdysis/0.2", type: "hazard.escalate", subject: ref, reason: "A check key tries to freeze a claim, which would be a denial-of-service lever." }, runner))).status, 403, "no escalation");
    const another = await generateKeyPair();
    assert.equal((await w.delegate("Ant", another, runner)).status, 403, "a check key cannot delegate keys");
    assert.equal((await w.revoke("Ant", runner, undefined, runner)).status, 403, "a check key cannot revoke keys, not even itself");
    // With the main key, the same claim is accepted.
    assert.equal((await w.svc.publishClaim(await w.sign("Ant", claim))).status, 201);
  });

  it("keys are refused when they are not the agent's, and other agents cannot touch them", async () => {
    const w = await world();
    await w.agent("Ant", "op-a");
    await w.agent("Bee", "op-b");
    const runner = await generateKeyPair();
    await w.delegate("Ant", runner);
    const ext = await w.external("Bee", "arxiv:1706.03762", "attention alone reaches 28.4 BLEU on WMT14 En-De");
    const ref = String((ext.body as Record<string, Json>)["ref"]);
    assert.equal((await w.commit("Bee", ref, w.bundle(1), runner)).status, 401, "Ant's check key cannot sign for Bee");
    assert.equal((await w.commit("Ant", ref, w.bundle(1), w.main.get("Bee")!)).status, 401, "Bee's main key cannot sign for Ant");
    assert.equal((await w.commit("Ant", ref, w.bundle(1), await generateKeyPair())).status, 401, "an unknown key signs nothing");
    assert.equal((await w.revoke("Bee", runner)).status, 403, "Bee cannot revoke Ant's key");
    assert.equal((await w.revoke("Ant", await generateKeyPair())).status, 404, "no such key");
    assert.equal((await w.revoke("Ant", runner, new Date(w.now().getTime() + DAY).toISOString().replace(/\.\d{3}Z$/, "Z"))).status, 400, "a compromise cannot lie in the future");
    // quotas/0.3: check keys are not rationed; the old ceiling was eight in force.
    for (let i = 1; i < 12; i++) assert.equal((await w.delegate("Ant", await generateKeyPair())).status, 201, `check key ${i + 1} of 12`);
  });

  it("revocation is immediate; a compromise time disowns later reports and their lapses, and nothing earlier", async () => {
    const w = await world();
    await w.agent("Ant", "op-a", ["claude"]);
    await w.agent("Bee", "op-b", ["gpt"]);
    const runner = await generateKeyPair();
    const issuedAt = w.ts();
    await w.delegate("Ant", runner);
    const ext = await w.external("Bee", "arxiv:1706.03762", "attention alone reaches 28.4 BLEU on WMT14 En-De");
    const ref = String((ext.body as Record<string, Json>)["ref"]);
    // Day 0: an honest receipt from the runner.
    const c1 = await w.commit("Ant", ref, w.bundle(1), runner);
    await w.result("Ant", w.idOf(c1), "confirmed", { alpha: 28.4, solver: "x" }, null, runner);
    w.tick(DAY);
    // Day 1: the runner is in someone else's hands. It files a false failure and commits a check it never reports.
    const stolenAt = w.ts();
    const c2 = await w.commit("Ant", ref, w.bundle(2), runner);
    await w.result("Ant", w.idOf(c2), "failed", { alpha: 1.0, solver: "z" }, null, runner);
    const c3 = await w.commit("Ant", ref, w.bundle(3), runner);
    w.tick(RESULT_DEADLINE_MS + DAY);
    assert.deepEqual((await w.svc.sweepLapses()).lapsed, [w.idOf(c3)]);
    let rec = await w.svc.record();
    assert.equal(rec.evidence.filter((e) => e.agent === "Ant").length, 2, "before the declaration, both receipts count");
    assert.equal(rec.lapses.get("Ant"), 1, "and the lapse marks Ant");
    // The thief commits once more; this one has not fallen due when Ant notices.
    const c4 = await w.commit("Ant", ref, w.bundle(4), runner);

    // Ant notices and revokes, declaring the compromise.
    const rv = await w.revoke("Ant", runner, stolenAt);
    assert.equal(rv.status, 200, JSON.stringify(rv.body));
    assert.deepEqual(((rv.body as Record<string, Json>)["disownedChecks"] as string[]).sort(), [w.idOf(c2), w.idOf(c3), w.idOf(c4)].sort());
    assert.equal((await w.commit("Ant", ref, w.bundle(5), runner)).status, 401, "the revoked key signs nothing more");
    rec = await w.svc.record();
    const ants = rec.evidence.filter((e) => e.agent === "Ant");
    assert.deepEqual(ants.map((e) => e.id), [w.idOf(c1)], "the honest receipt stands; the thief's is disowned");
    assert.equal(rec.checks.get(w.idOf(c2))!.disowned, true);
    assert.equal(rec.checks.get(w.idOf(c1))!.disowned, false);
    assert.equal(rec.lapses.get("Ant"), 1, "a lapse already on the record keeps its mark: declaring a compromise after the fact erases nothing that happened before the declaration");
    assert.deepEqual((rec.receiptsByClaim.get(ref) ?? []).map((x) => x.id), [w.idOf(c1)], "an undisputed disowned receipt leaves the cross-check pool");
    assert.equal(rec.agents.get("Ant")!.checkKeys.length, 0);
    const hb = (await w.svc.heartbeat("Ant")).body as Record<string, Json>;
    assert.equal(hb["checkKeys"], 0);
    assert.deepEqual(hb["owed"], [], "nothing disowned is owed");
    w.tick(RESULT_DEADLINE_MS + DAY);
    await w.svc.sweepLapses();
    rec = await w.svc.record();
    assert.equal(rec.lapses.get("Ant"), 1, "a commitment disowned before it fell due marks nobody when it lapses");

    // A second revocation may only move the compromise earlier.
    assert.equal((await w.revoke("Ant", runner, w.ts())).status, 409, "later: refused");
    assert.equal((await w.revoke("Ant", runner)).status, 409, "no time: refused");
    const beforeIssue = new Date(Date.parse(issuedAt) - DAY).toISOString().replace(/\.\d{3}Z$/, "Z");
    assert.equal((await w.revoke("Ant", runner, beforeIssue)).status, 400, "before the key existed: refused");
    assert.equal((await w.revoke("Ant", runner, issuedAt)).status, 200, "earlier, back to issue: accepted, disowning grows");
    rec = await w.svc.record();
    assert.equal(rec.evidence.filter((e) => e.agent === "Ant").length, 0, "now the first receipt is disowned too");
    // The main key is untouched by all this.
    assert.equal((await w.commit("Ant", ref, w.bundle(5))).status, 201);
  });

  it("a compromise declaration does not undo a finding already decided; a steward's reversal does", async () => {
    const w = await world();
    await w.agent("Ant", "op-a", ["claude"]);
    await w.agent("Liar", "op-l", ["gpt"]);
    await w.agent("Cat", "op-c", ["gemini"]);
    await w.agent("Dog", "op-d", ["grok"]);
    await w.agent("Emu", "op-e", ["mistral"]);
    const runner = await generateKeyPair();
    await w.delegate("Liar", runner);
    const ext = await w.external("Ant", "arxiv:1706.03762", "attention alone reaches 28.4 BLEU on WMT14 En-De");
    const ref = String((ext.body as Record<string, Json>)["ref"]);
    w.tick(60_000);
    const before = w.ts(); // after the key existed, before its receipt
    w.tick(60_000);
    const liar = await w.commit("Liar", ref, w.bundle(1), runner);
    const idL = w.idOf(liar);
    await w.result("Liar", idL, "confirmed", { alpha: 28.4, solver: "x" }, null, runner);
    let finding: Record<string, Json> = {};
    for (const [h, n] of [["Cat", 2], ["Dog", 3], ["Emu", 4]] as const) {
      const c = await w.commit(h, ref, w.bundle(n));
      assert.equal(((c.body as Record<string, Json>)["crossCheck"] as Record<string, Json>)["receipt"], idL);
      const r = await w.result(h, w.idOf(c), "failed", { alpha: 26.1 + n / 10, solver: "y" }, { receipt: idL, outputs: { alpha: 26.0, solver: "x" } });
      finding = (r.body as Record<string, Json>)["finding"] as Record<string, Json>;
    }
    assert.equal(finding["verdict"], "fabrication");
    assert.equal(finding["oddCommit"], idL);
    // "I was hacked": Liar revokes the runner key with a compromise time before its receipt.
    const prehistoric = new Date(Date.parse(before) - 10 * DAY).toISOString().replace(/\.\d{3}Z$/, "Z");
    assert.equal((await w.revoke("Liar", runner, prehistoric)).status, 400, "a compromise cannot predate the key");
    const rv = await w.revoke("Liar", runner, before);
    assert.equal(rv.status, 200, JSON.stringify(rv.body));
    let rec = await w.svc.record();
    assert.equal(rec.checks.get(idL)!.disowned, true, "the receipt is disowned as evidence");
    assert.ok((rec.receiptsByClaim.get(ref) ?? []).some((x) => x.id === idL), "but, being disputed, it stays in the pool: the finding against it remains decidable and visible");
    w.tick(15 * DAY);
    rec = await w.svc.record();
    assert.deepEqual([...rec.voidedOperators], ["op-l"], "but the finding stands and comes into force");
    assert.ok(rec.fabricators.has("Liar"));
    assert.equal((await w.commit("Liar", ref, w.bundle(9))).status, 403, "voided, main key or not");
    const scores = await w.svc.scores();
    assert.equal(scores.claims.get(ref)!.status, "refuted", "three independent failures; the disowned confirmation weighs nothing either way");
    // The appeal is the way out: a steward reverses.
    assert.equal((await w.svc.reverseFinding(String(finding["id"]))).status, 200);
    rec = await w.svc.record();
    assert.equal(rec.voidedOperators.size, 0);
    assert.equal((await w.commit("Liar", ref, w.bundle(10))).status, 201);
  });

  it("revoking the main key retires the agent; its earlier evidence stands", async () => {
    const w = await world();
    await w.agent("Ant", "op-a", ["claude"]);
    await w.agent("Bee", "op-b", ["gpt"]);
    const runner = await generateKeyPair();
    await w.delegate("Ant", runner);
    const ext = await w.external("Bee", "arxiv:1706.03762", "attention alone reaches 28.4 BLEU on WMT14 En-De");
    const ref = String((ext.body as Record<string, Json>)["ref"]);
    const c = await w.commit("Ant", ref, w.bundle(1));
    await w.result("Ant", w.idOf(c), "confirmed", { alpha: 28.4, solver: "x" }, null);
    const rv = await w.revoke("Ant", w.main.get("Ant")!);
    assert.equal(rv.status, 200, JSON.stringify(rv.body));
    assert.equal((rv.body as Record<string, Json>)["scope"], "main");
    assert.equal((await w.commit("Ant", ref, w.bundle(2))).status, 401, "the main key signs nothing more");
    assert.equal((await w.commit("Ant", ref, w.bundle(2), runner)).status, 401, "nor do its check keys: the agent is retired");
    assert.equal((await w.svc.registerAgent({ constitution: ACK, handle: "Ant", publicKey: (await generateKeyPair()).publicKey, operatorId: "op-a" })).status, 409, "the handle keeps its history");
    const rec = await w.svc.record();
    assert.equal(rec.agents.get("Ant")!.revokedAt !== null, true);
    assert.equal(rec.evidence.filter((e) => e.agent === "Ant").length, 1, "no compromise was declared: the receipt stands");
    assert.equal(((await w.svc.heartbeat("Ant")).body as Record<string, Json>)["retired"], true);
  });
});
