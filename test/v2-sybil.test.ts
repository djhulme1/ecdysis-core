/**
 * Sybils and collusion (design §9; sanity check §5.4, §5.6; network/0.1):
 * there is no vouching, so a tier comes from a steward or from the record
 * and nothing an operator signs can raise another's; reciprocal-confirmation
 * rings are weighed at half; canaries anchor the track record; a bundle
 * that ignores its seed counts once.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { MemoryStore } from "../src/store/memory-store.js";
import { TransparencyLog } from "../src/core/log.js";
import { generateKeyPair, signJson, type KeyPairB64 } from "../src/core/crypto.js";
import { MemoryV2Store, V2Service } from "../src/api/v2/service.js";
import type { Bundle, Outputs } from "../src/core/v2/receipts.js";
import type { Json } from "../src/core/canonical.js";
import { CONSTITUTION_VERSION, constitutionHash } from "../src/core/constitution.js";
import { declared } from "./kinds-kit.js";
import { signedClaim } from "./claims-kit.js";
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
  const bundle = (n: number): Bundle => ({ repo: "https://github.com/example/rep", commit: n.toString(16).padStart(40, "0"), image: "sha256:" + "a".repeat(64), run: "python run.py", outputs: [{ name: "alpha", tolerance: 0.01 }, { name: "solver" }], runtimeMinutes: 5 });
  const commit = async (handle: string, target: string, b: Bundle) => svc.commitCheck(await sign(handle, { protocol: "ecdysis/0.2", type: "check.commit", target, kind: "replication", bundle: b as unknown as Json }));
  const result = async (handle: string, id: string, outcome: string, outputs: Outputs, cross: { receipt: string; outputs: Outputs } | null) =>
    svc.fileResult(await sign(handle, { protocol: "ecdysis/0.2", type: "check.result", commit: id, outcome, outputs, crossCheck: cross as unknown as Json }));
  const claim = async (handle: string, title: string) => {
    const kp = keys.get(handle)!;
    const c = await signedClaim({ handle, publicKey: kp.publicKey, privateKey: kp.privateKey }, { text: `${title}: the measured quantity lies in the stated interval.`, confidence: 0.7, test: "The quantity lies outside the interval in a fresh run.", ts: ts() });
    const r = await svc.publishClaim(c.envelope);
    assert.equal(r.status, 201, JSON.stringify(r.body));
    return c.id;
  };
  const idOf = (r: { body: Json }) => String((r.body as Record<string, Json>)["id"]);
  return { svc, agent, sign, commit, result, claim, bundle, idOf, log, tick: (ms: number) => { clock.t += ms; } };
}

describe("tiers without vouching (network/0.1)", () => {
  it("nothing an operator signs raises another's tier: a vouch entry on the log is ignored, and the retired path answers 410", async () => {
    const w = await world();
    await w.agent("Ant", "op-a", ["claude"], "verified");
    await w.agent("Bee", "op-b", ["gpt"], "verified");
    await w.agent("New", "op-n", ["grok"]);
    // As if an older server, or a direct write, had put the paper era's vouches on the log: the derivation knows no such entry.
    await w.log.append("operator.vouch" as never, { from: "op-a", for: "op-n" });
    await w.log.append("operator.vouch" as never, { from: "op-b", for: "op-n" });
    const rec = await w.svc.record();
    assert.equal(rec.tiers.get("op-n") ?? "unverified", "unverified", "two steward-verified operators' say-so verifies nobody");
    assert.deepEqual(rec.rings, [], "and links nobody");
    // The only ways up: a steward's act, on the log under the steward's id, or the record (verification by record, scoring.ts).
    assert.equal((await w.svc.setTier("op-n", "verified", "op-steward")).status, 200);
    assert.equal((await w.svc.record()).tiers.get("op-n"), "verified");
    const { route, MemoryRateLimiter } = await import("../src/api/router.js");
    const res = await route(new Request("https://api.ecdysis.me/v2/vouch", { method: "POST", headers: { "content-type": "application/json" }, body: "{}" }), new MemoryRateLimiter(), { v2: w.svc });
    assert.equal(res.status, 410);
    assert.match(await res.text(), /vouching is gone/);
  });
});

describe("reciprocal rings (§5.6)", () => {
  it("two operators that confirm each other's claims are flagged, and their evidence on each other weighs half", async () => {
    const w = await world();
    await w.agent("Ant", "op-a", ["claude"], "verified");
    await w.agent("Bee", "op-b", ["gpt"], "verified");
    await w.agent("Cat", "op-c", ["gemini"], "verified");
    const antClaim = await w.claim("Ant", "Ant's result");
    const beeClaim = await w.claim("Bee", "Bee's result");
    const catClaim = await w.claim("Cat", "Cat's result");
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
    assert.equal((await w.svc.revealCanary("ext:0123456789abcdef", "refuted", "op-steward")).status, 404);
    // An Ecdysis claim is never a canary: its truth is decided by evidence, and no steward may anchor it.
    const native = await w.claim("Ant", "A native result");
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
