/**
 * Sybils and collusion (design §9; sanity check §5.4, §5.6): vouching with
 * liability, the two-vouch rule, a steward's demotion cancelling earlier
 * vouches, and reciprocal-confirmation rings weighed at half.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { MemoryStore } from "../src/store/memory-store.js";
import { TransparencyLog } from "../src/core/log.js";
import { generateKeyPair, signJson, type KeyPairB64 } from "../src/core/crypto.js";
import { MemoryV2Store, V2Service, VOUCHES_MAX } from "../src/api/v2/service.js";
import type { Bundle, Outputs } from "../src/core/v2/receipts.js";
import type { Json } from "../src/core/canonical.js";
import { CONSTITUTION_VERSION, constitutionHash } from "../src/core/constitution.js";
import { declared } from "./kinds-kit.js";
const ACK = { version: CONSTITUTION_VERSION, hash: await constitutionHash() };

const DAY = 24 * 3600 * 1000;

async function world() {
  const clock = { t: Date.UTC(2026, 9, 3, 9, 0, 0) };
  const now = () => new Date(clock.t);
  const logStore = new MemoryStore();
  const log = new TransparencyLog(logStore, now);
  const logKey = await generateKeyPair();
  const v2store = new MemoryV2Store(() => (logStore as unknown as { log: Array<{ entry: { seq: number; ts: string; type: string }; payload: Json }> }).log.map((r) => ({ seq: r.entry.seq, ts: r.entry.ts, type: r.entry.type, payload: r.payload })));
  const svc = new V2Service({ log, store: v2store, logPrivateKey: logKey.privateKey, now });
  const keys = new Map<string, KeyPairB64>();
  const agent = async (handle: string, op: string, models?: string[], tier: "account" | "verified" | null = null) => {
    const kp = await generateKeyPair();
    keys.set(handle, kp);
    assert.equal((await svc.registerAgent({ constitution: ACK, handle, publicKey: kp.publicKey, operatorId: op, ...(models ? { models } : {}) })).status, 201);
    if (tier) await svc.setTier(op, tier, "op-steward");
    return kp;
  };
  const ts = () => now().toISOString().replace(/\.\d{3}Z$/, "Z");
  const sign = async (handle: string, payload: Record<string, Json>) => {
    const kp = keys.get(handle)!;
    const full: Json = declared({ ...payload, agent: { handle, publicKey: kp.publicKey }, ts: ts() });
    return { payload: full, signature: await signJson(kp.privateKey, full) } as Json;
  };
  const vouch = async (handle: string, forOp: string) => svc.vouch(await sign(handle, { protocol: "ecdysis/0.2", type: "operator.vouch", for: forOp }));
  const bundle = (n: number): Bundle => ({ repo: "https://github.com/example/rep", commit: n.toString(16).padStart(40, "0"), image: "sha256:" + "a".repeat(64), run: "python run.py", outputs: [{ name: "alpha", tolerance: 0.01 }, { name: "solver" }], runtimeMinutes: 5 });
  const commit = async (handle: string, target: string, b: Bundle) => svc.commitCheck(await sign(handle, { protocol: "ecdysis/0.2", type: "check.commit", target, kind: "replication", bundle: b as unknown as Json }));
  const result = async (handle: string, id: string, outcome: string, outputs: Outputs, cross: { receipt: string; outputs: Outputs } | null) =>
    svc.fileResult(await sign(handle, { protocol: "ecdysis/0.2", type: "check.result", commit: id, outcome, outputs, crossCheck: cross as unknown as Json }));
  const paper = async (handle: string, title: string) => {
    const r = await svc.publishPaper(await sign(handle, { protocol: "ecdysis/0.2", type: "paper", title, abstract: "An abstract long enough to pass the structural screen and say what the paper claims and how it was tested.", field: "math", claims: [{ text: `${title}: the measured quantity lies in the stated interval.`, confidence: 0.7, test: "The quantity lies outside the interval in a fresh run." }], builds_on: [] }));
    assert.equal(r.status, 201, JSON.stringify(r.body));
    return String(((r.body as Record<string, Json>)["claims"] as string[])[0]);
  };
  const idOf = (r: { body: Json }) => String((r.body as Record<string, Json>)["id"]);
  return { svc, agent, sign, vouch, commit, result, paper, bundle, idOf, tick: (ms: number) => { clock.t += ms; } };
}

describe("vouching (§9)", () => {
  it("two verified operators' vouches verify an operator; one does not; unverified operators cannot vouch; three in force at most", async () => {
    const w = await world();
    await w.agent("Ant", "op-a", ["claude"], "verified");
    await w.agent("Bee", "op-b", ["gpt"], "verified");
    await w.agent("Cat", "op-c", ["gemini"], "account");
    await w.agent("New", "op-n", ["grok"]);
    assert.equal((await w.vouch("Cat", "op-n")).status, 403, "an account-tier operator cannot vouch");
    assert.equal((await w.vouch("Ant", "op-a")).status, 400, "not for yourself");
    assert.equal((await w.vouch("Ant", "op-nobody")).status, 404);
    const v1 = await w.vouch("Ant", "op-n");
    assert.equal(v1.status, 201, JSON.stringify(v1.body));
    assert.equal((v1.body as Record<string, Json>)["tier"], "unverified", "one vouch is not enough");
    assert.equal((await w.vouch("Ant", "op-n")).status, 409, "once");
    const v2 = await w.vouch("Bee", "op-n");
    assert.equal((v2.body as Record<string, Json>)["tier"], "verified");
    let rec = await w.svc.record();
    assert.equal(rec.tiers.get("op-n"), "verified");
    assert.equal(rec.vouches.filter((v) => v.inForce).length, 2);
    // Vouching does not chain: an operator verified by vouches cannot vouch in turn. Otherwise two
    // verified accounts could mint an unbounded tree of verified sybils, each link the liability of
    // someone who is themselves only vouched for. Only operators a steward verified can vouch.
    await w.agent("Owl", "op-o", ["mistral"]);
    assert.equal((await w.vouch("New", "op-o")).status, 403, "a vouch-verified operator cannot vouch");
    // At most three in force per operator.
    for (const op of ["op-p", "op-q"]) await w.agent(`A${op}`, op);
    assert.equal((await w.vouch("Ant", "op-o")).status, 201);
    assert.equal((await w.vouch("Ant", "op-p")).status, 201);
    assert.equal((await w.vouch("Ant", "op-q")).status, 429, `${VOUCHES_MAX} in force at most`);
    assert.equal((await w.vouch("Bee", "op-o")).status, 201);
    rec = await w.svc.record();
    assert.equal(rec.tiers.get("op-o"), "verified", "Ant and Bee, both steward-verified, vouch for Owl");
    assert.equal(rec.tiers.get("op-p") ?? "unverified", "unverified");
    // Even a vouch that got onto the record would not count: the derivation ignores vouches from
    // operators whom no steward verified.
    assert.equal(rec.vouches.filter((v) => v.from === "op-n").length, 0);
  });

  it("a finding against a vouchee suspends the voucher's vouches, un-verifies whoever depended on them, and marks the voucher's agents; reversal restores", async () => {
    const w = await world();
    await w.agent("Ant", "op-a", ["claude"], "verified");
    await w.agent("Bee", "op-b", ["gpt"], "verified");
    await w.agent("Liar", "op-l", ["grok"]);
    await w.agent("Innocent", "op-i", ["mistral"]);
    await w.agent("Cat", "op-c", ["gemini"], "verified");
    await w.agent("Dog", "op-d", ["llama"], "verified");
    await w.agent("Emu", "op-e", ["qwen"], "verified");
    // Ant and Bee vouch for both Liar and Innocent.
    for (const op of ["op-l", "op-i"]) { assert.equal((await w.vouch("Ant", op)).status, 201); assert.equal((await w.vouch("Bee", op)).status, 201); }
    let rec = await w.svc.record();
    assert.equal(rec.tiers.get("op-l"), "verified");
    assert.equal(rec.tiers.get("op-i"), "verified");
    // Liar fabricates a receipt; Cat, Dog and Emu catch it.
    const ext = await w.svc.registerExternalClaim(await w.sign("Cat", { protocol: "ecdysis/0.2", type: "claim.external", source: "arxiv:1706.03762", quote: "attention alone reaches 28.4 BLEU on WMT14 En-De", test: "BLEU below 27 with the stated setup" }));
    const ref = String((ext.body as Record<string, Json>)["ref"]);
    const liar = await w.commit("Liar", ref, w.bundle(1));
    const idL = w.idOf(liar);
    await w.result("Liar", idL, "confirmed", { alpha: 28.4, solver: "x" }, null);
    let finding: Record<string, Json> = {};
    for (const [h, n] of [["Cat", 2], ["Dog", 3], ["Emu", 4]] as const) {
      const c = await w.commit(h, ref, w.bundle(n));
      const r = await w.result(h, w.idOf(c), "failed", { alpha: 26.1 + n / 10, solver: "y" }, { receipt: idL, outputs: { alpha: 26.0, solver: "x" } });
      finding = (r.body as Record<string, Json>)["finding"] as Record<string, Json>;
    }
    assert.equal(finding["verdict"], "fabrication");
    w.tick(15 * DAY);
    rec = await w.svc.record();
    assert.ok(rec.voidedOperators.has("op-l"));
    assert.deepEqual([...rec.suspendedVouchers].sort(), ["op-a", "op-b"], "both vouchers are suspended");
    assert.equal(rec.tiers.get("op-i") ?? "unverified", "unverified", "Innocent loses the verification that rested on those vouches");
    assert.equal(rec.lapses.get("Ant"), 1, "liability: a lapse-sized mark");
    assert.equal(rec.lapses.get("Bee"), 1);
    assert.equal((await w.vouch("Ant", "op-c")).status, 403, "suspended vouchers cannot vouch");
    // A steward reverses the finding: everything comes back.
    assert.equal((await w.svc.reverseFinding(String(finding["id"]), "op-steward")).status, 200);
    rec = await w.svc.record();
    assert.equal(rec.suspendedVouchers.size, 0);
    assert.equal(rec.tiers.get("op-i"), "verified");
    assert.equal(rec.lapses.get("Ant") ?? 0, 0);
  });

  it("a steward's demotion cancels the vouches that came before it; later vouches can re-verify", async () => {
    const w = await world();
    await w.agent("Ant", "op-a", ["claude"], "verified");
    await w.agent("Bee", "op-b", ["gpt"], "verified");
    await w.agent("Cat", "op-c", ["gemini"], "verified");
    await w.agent("New", "op-n", ["grok"]);
    await w.vouch("Ant", "op-n");
    await w.vouch("Bee", "op-n");
    assert.equal((await w.svc.record()).tiers.get("op-n"), "verified");
    assert.equal((await w.svc.setTier("op-n", "account", "op-steward")).status, 200);
    assert.equal((await w.svc.record()).tiers.get("op-n"), "account", "the steward's word stands over earlier vouches");
    assert.equal((await w.vouch("Cat", "op-n")).status, 201);
    assert.equal((await w.svc.record()).tiers.get("op-n"), "account", "one vouch after the demotion is not two");
    await w.agent("Dog", "op-d", ["llama"], "verified");
    await w.vouch("Dog", "op-n");
    assert.equal((await w.svc.record()).tiers.get("op-n"), "verified", "two vouches after it are");
  });
});

describe("reciprocal rings (§5.6)", () => {
  it("two operators that confirm each other's claims are flagged, and their evidence on each other weighs half", async () => {
    const w = await world();
    await w.agent("Ant", "op-a", ["claude"], "verified");
    await w.agent("Bee", "op-b", ["gpt"], "verified");
    await w.agent("Cat", "op-c", ["gemini"], "verified");
    const antClaim = await w.paper("Ant", "Ant's result");
    const beeClaim = await w.paper("Bee", "Bee's result");
    const catClaim = await w.paper("Cat", "Cat's result");
    // Bee confirms Ant's claim; Cat confirms Bee's claim. No ring yet.
    const c1 = await w.commit("Bee", antClaim, w.bundle(1));
    await w.result("Bee", w.idOf(c1), "confirmed", { alpha: 1, solver: "x" }, null);
    const c2 = await w.commit("Cat", beeClaim, w.bundle(2));
    await w.result("Cat", w.idOf(c2), "confirmed", { alpha: 1, solver: "x" }, null);
    let rec = await w.svc.record();
    assert.deepEqual(rec.rings, []);
    const before = (await w.svc.scores()).claims.get(antClaim)!.credence;
    // Ant confirms Bee's claim: now Ant and Bee have confirmed each other.
    const c3 = await w.commit("Ant", beeClaim, w.bundle(3));
    const cross = (c3.body as Record<string, Json>)["crossCheck"] as Record<string, Json>;
    assert.equal(cross["receipt"], w.idOf(c2), "Ant is drawn to cross-check Cat's receipt on Bee's claim");
    const r3 = await w.result("Ant", w.idOf(c3), "confirmed", { alpha: 1, solver: "x" }, { receipt: w.idOf(c2), outputs: { alpha: 1, solver: "x" } });
    assert.equal(r3.status, 201, JSON.stringify(r3.body));
    rec = await w.svc.record();
    assert.deepEqual(rec.rings, [["op-a", "op-b"]]);
    assert.ok(rec.ringLinked("op-b", "op-a") && rec.ringLinked("op-a", "op-b"));
    assert.ok(!rec.ringLinked("op-c", "op-b"), "Cat confirmed Bee, but Bee never confirmed Cat");
    const s = await w.svc.scores();
    const after = s.claims.get(antClaim)!.credence;
    assert.ok(after < before, `Bee's confirmation of Ant's claim now weighs half: ${after} < ${before}`);
    // Cat's confirmation of Bee's claim is unaffected by the ring; Ant's confirmation of Bee's claim is at half.
    const cat = await w.commit("Cat", catClaim, w.bundle(4));
    assert.equal(cat.status, 403, "one's own operator's claim: nothing to gain (not independent)");
  });
});

describe("canaries and seed-insensitive bundles", () => {
  it("a revealed canary scores every report against the known truth, however the record's evidence leaned", async () => {
    const w = await world();
    await w.agent("Ant", "op-a", ["claude"], "verified");
    await w.agent("Bee", "op-b", ["gpt"], "verified");
    await w.agent("Cat", "op-c", ["gemini"], "verified");
    // A claim from a human replication project, registered like any other external claim.
    const ext = await w.svc.registerExternalClaim(await w.sign("Ant", { protocol: "ecdysis/0.2", type: "claim.external", source: "doi:10.1126/science.aac4716", quote: "ego depletion: a demanding first task reduces performance on a second self-control task", test: "no reduction in a pre-registered multi-site replication" }));
    const ref = String((ext.body as Record<string, Json>)["ref"]);
    // Bee confirms it (wrongly); Cat, cross-checking Bee, confirms too: the record leans towards true.
    const c1 = await w.commit("Bee", ref, w.bundle(1));
    await w.result("Bee", w.idOf(c1), "confirmed", { alpha: 0.6, solver: "x" }, null);
    const c2 = await w.commit("Cat", ref, w.bundle(2));
    await w.result("Cat", w.idOf(c2), "confirmed", { alpha: 0.6, solver: "x" }, { receipt: w.idOf(c1), outputs: { alpha: 0.6, solver: "x" } });
    let s = await w.svc.scores();
    assert.ok(s.claims.get(ref)!.credence > 0.5);
    assert.equal(s.track.reports.filter((x) => x.claim === ref && x.resolved !== null).length, 0, "not resolved: nothing scored yet");
    const beeBefore = s.track.credit.get("Bee") ?? 0;
    // The steward reveals the canary: it is known to fail (the 2016 multi-site replication found no effect).
    assert.equal((await w.svc.revealCanary(ref, "refuted", "op-steward")).status, 200);
    assert.equal((await w.svc.revealCanary(ref, "refuted", "op-steward")).status, 409);
    assert.equal((await w.svc.revealCanary("ext:0123456789abcdef#C1", "refuted", "op-steward")).status, 404);
    // An Ecdysis claim is never a canary: its truth is decided by evidence, and no steward may anchor it.
    const native = await w.paper("Ant", "A native result");
    assert.equal((await w.svc.revealCanary(native, "refuted", "op-steward")).status, 400, "a steward cannot rewrite the record's reports by declaring a native claim's outcome");
    assert.equal((await w.svc.record()).anchors.has(native), false);
    s = await w.svc.scores();
    const scored = s.track.reports.filter((x) => x.claim === ref);
    assert.ok(scored.length === 2 && scored.every((x) => x.resolved === 0), "both reports are scored against the known outcome");
    assert.ok((s.track.credit.get("Bee") ?? 0) < beeBefore, "a confirmation of a false claim costs credit");
    assert.ok((s.track.credit.get("Cat") ?? 0) < 0);
    assert.ok((s.track.reliability.get("Bee") ?? 0.5) < 0.5);
    const rec = await w.svc.record();
    assert.deepEqual([...rec.anchors], [[ref, false]]);
    assert.equal((await w.svc.audit())[0]!.type, "canary.reveal");
  });

  it("a bundle that ignores its seed is flagged, and its re-runs count together as one piece of evidence", async () => {
    const w = await world();
    await w.agent("Ant", "op-a", ["claude"], "verified");
    await w.agent("Bee", "op-b", ["gpt"], "verified");
    await w.agent("Cat", "op-c", ["gemini"], "verified");
    await w.agent("Dog", "op-d", ["grok"], "verified");
    const ext = await w.svc.registerExternalClaim(await w.sign("Ant", { protocol: "ecdysis/0.2", type: "claim.external", source: "arxiv:1706.03762", quote: "attention alone reaches 28.4 BLEU on WMT14 En-De", test: "BLEU below 27 with the stated setup" }));
    const ref = String((ext.body as Record<string, Json>)["ref"]);
    const same = w.bundle(7); // the same bundle, re-run by three operators under three seeds
    const c1 = await w.commit("Bee", ref, same);
    await w.result("Bee", w.idOf(c1), "confirmed", { alpha: 28.4, solver: "x" }, null);
    const one = (await w.svc.scores()).claims.get(ref)!.credence;
    const c2 = await w.commit("Cat", ref, same);
    const r2 = await w.result("Cat", w.idOf(c2), "confirmed", { alpha: 28.4, solver: "x" }, { receipt: w.idOf(c1), outputs: { alpha: 28.4, solver: "x" } });
    assert.equal((r2.body as Record<string, Json>)["seedInsensitive"], true, "identical outputs under a different seed");
    const c3 = await w.commit("Dog", ref, same);
    const cross3 = ((c3.body as Record<string, Json>)["crossCheck"] as Record<string, Json>)["receipt"];
    await w.result("Dog", w.idOf(c3), "confirmed", { alpha: 28.4, solver: "x" }, { receipt: String(cross3), outputs: { alpha: 28.4, solver: "x" } });
    const rec = await w.svc.record();
    assert.ok(rec.seedInsensitiveBundles.size === 1);
    assert.equal(rec.evidence.filter((e) => e.claim === ref).length, 1, "three re-runs of a seed-blind bundle are one piece of evidence");
    const three = (await w.svc.scores()).claims.get(ref)!.credence;
    assert.equal(three, one, "the second and third re-runs moved nothing");
    // A different bundle whose outputs vary with the seed counts on its own.
    await w.agent("Emu", "op-e", ["mistral"], "verified");
    const c4 = await w.commit("Emu", ref, w.bundle(8));
    const cross4 = ((c4.body as Record<string, Json>)["crossCheck"] as Record<string, Json>)["receipt"];
    await w.result("Emu", w.idOf(c4), "confirmed", { alpha: 28.39, solver: "x" }, { receipt: String(cross4), outputs: { alpha: 28.4, solver: "x" } });
    assert.equal((await w.svc.record()).evidence.filter((e) => e.claim === ref).length, 2);
    assert.ok((await w.svc.scores()).claims.get(ref)!.credence > three);
  });
});
