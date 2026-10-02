/**
 * The v2 record derived from the log (src/core/v2/flow.ts): every input to
 * credence and the track record comes from entries alone, as constitution
 * 0.4 requires, and the receipt life cycle, findings, appeals and
 * reversals behave as the design says.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { deriveV2, type V2Entry, type V2EntryType } from "../src/core/v2/flow.js";
import { computeV2 } from "../src/core/v2/scoring.js";
import { APPEAL_MS } from "../src/core/v2/receipts.js";

function log() {
  const entries: V2Entry[] = [];
  let t = Date.UTC(2026, 9, 2, 12, 0, 0);
  const add = (type: V2EntryType, payload: Record<string, unknown>, dtMs = 60_000) => {
    t += dtMs;
    entries.push({ seq: entries.length, ts: new Date(t).toISOString(), type, payload });
    return entries.length - 1;
  };
  return { entries, add, now: () => new Date(t) };
}

/** A verified operator with one agent on a given model. */
function operator(L: ReturnType<typeof log>, op: string, handle: string, model: string, tier = "verified") {
  L.add("operator.tier", { operatorId: op, tier });
  L.add("agent.register", { handle, operatorId: op, publicKey: `pk-${handle}`, models: [model] });
}

/** A full receipt: commit, seal (with a cross-check), result. */
function receipt(L: ReturnType<typeof log>, o: { id: string; target: string; kind?: "rerun" | "replication"; bundle: string; handle: string; op: string; outcome?: string; cross?: string | null; crossMatch?: boolean | null; models?: string[] }) {
  L.add("check.commit", { id: o.id, target: o.target, kind: o.kind ?? "replication", bundle: o.bundle, image: true, runtimeMinutes: 10, handle: o.handle, operatorId: o.op, ...(o.models ? { models: o.models } : {}) });
  L.add("check.seal", { commit: o.id, seal: `seal-${o.id}`, seed: "ab".repeat(32), crossCheck: o.cross ?? null });
  L.add("check.result", { commit: o.id, outcome: o.outcome ?? "confirmed", crossMatch: o.crossMatch ?? (o.cross ? true : null) });
}

describe("the v2 record from the log", () => {
  it("publishes claims on screening, with foundations and use from reliance citations, and external claims as targets", () => {
    const L = log();
    operator(L, "op-a", "Ant", "claude");
    operator(L, "op-b", "Bee", "gpt");
    L.add("claim.external", { id: "ext:ks94", handle: "Ant", operatorId: "op-a", source: "doi:10.1126/science.264.5163.1297", quote: "alpha_c = 4.17 +/- 0.05", test: "alpha_c outside [4.12, 4.22] at N = 200" });
    L.add("paper.publish", { id: "ecd:1", handle: "Ant", operatorId: "op-a", claims: [{ label: "C1", confidence: 0.8, test: "x" }], builds_on: [{ id: "ext:ks94", rel: "extends", basis: "reproduced", claims: ["C1"] }] });
    L.add("paper.publish", { id: "ecd:2", handle: "Bee", operatorId: "op-b", claims: [{ label: "C1", confidence: 0.7, test: "y" }], builds_on: [{ id: "ecd:1", rel: "method", basis: "reviewed", claims: ["C1"] }, { id: "ecd:1", rel: "background" }] });
    const r = deriveV2(L.entries, L.now());
    assert.deepEqual(r.claims.map((c) => c.ref), ["ext:ks94#C1", "ecd:1#C1", "ecd:2#C1"]);
    assert.deepEqual(r.claims[1]!.foundations, ["ext:ks94#C1"]);
    assert.deepEqual(r.claims[2]!.foundations, ["ecd:1#C1"], "background citations are not foundations");
    assert.deepEqual(r.uses, [{ claim: "ext:ks94#C1", paper: "ecd:1", operatorId: "op-a" }, { claim: "ecd:1#C1", paper: "ecd:2", operatorId: "op-b" }]);
    assert.equal(r.external.get("ext:ks94")!.test, "alpha_c outside [4.12, 4.22] at N = 200");
    const out = computeV2(r.claims, r.evidence, r.uses, { vouchLinked: r.vouchLinked });
    assert.equal(out.claims.get("ecd:1#C1")!.use, 1);
    assert.equal(out.claims.get("ext:ks94#C1")!.status, "unchecked");
  });

  it("a receipt becomes evidence only once its result is filed; its tier and families come from the log", () => {
    const L = log();
    operator(L, "op-a", "Ant", "claude");
    operator(L, "op-b", "Bee", "gpt");
    L.add("operator.tier", { operatorId: "op-c", tier: "account" });
    L.add("agent.register", { handle: "Cat", operatorId: "op-c", publicKey: "pk-c" });
    L.add("paper.publish", { id: "ecd:1", handle: "Ant", operatorId: "op-a", claims: [{ label: "C1", confidence: 0.8 }], builds_on: [] });
    L.add("check.commit", { id: "r1", target: "ecd:1#C1", kind: "replication", bundle: "b1", image: true, runtimeMinutes: 5, handle: "Bee", operatorId: "op-b" });
    let r = deriveV2(L.entries, L.now());
    assert.equal(r.evidence.length, 0, "a commitment is not evidence");
    assert.equal(r.checks.get("r1")!.stage, "committed");
    L.add("check.seal", { commit: "r1", seal: "s", seed: "cd".repeat(32), crossCheck: null });
    L.add("check.result", { commit: "r1", outcome: "confirmed", crossMatch: null });
    receipt(L, { id: "r2", target: "ecd:1#C1", bundle: "b2", handle: "Cat", op: "op-c", cross: "r1", crossMatch: true, models: ["gemini-3", "gpt-5.2"] });
    r = deriveV2(L.entries, L.now());
    assert.equal(r.evidence.length, 2);
    assert.deepEqual(r.evidence.map((e) => [e.agent, e.tier, e.families]), [["Bee", "verified", ["gpt"]], ["Cat", "account", ["gemini", "gpt"]]]);
    assert.deepEqual(r.checks.get("r1")!.verifiedBy, ["r2"], "r2's matching cross-check verifies r1");
    assert.deepEqual(r.receiptsByClaim.get("ecd:1#C1")!.map((x) => x.id), ["r1", "r2"]);
    const out = computeV2(r.claims, r.evidence, r.uses, { vouchLinked: r.vouchLinked });
    const c = out.claims.get("ecd:1#C1")!;
    assert.equal(c.status, "supported", "one verified replication (Bee); Cat's account-tier check moves credence but cannot resolve");
    assert.deepEqual(c.families, ["gpt"]);
  });

  it("a finding of fabrication takes effect after the appeal period, voids the operator, and a reversal restores everything", () => {
    const L = log();
    operator(L, "op-a", "Ant", "claude");
    operator(L, "op-liar", "Liar", "gpt");
    operator(L, "op-c", "Cat", "gemini");
    operator(L, "op-d", "Dog", "grok");
    L.add("paper.publish", { id: "ecd:1", handle: "Ant", operatorId: "op-a", claims: [{ label: "C1", confidence: 0.6 }], builds_on: [] });
    receipt(L, { id: "r1", target: "ecd:1#C1", bundle: "b1", handle: "Liar", op: "op-liar", outcome: "confirmed" });
    receipt(L, { id: "r2", target: "ecd:1#C1", bundle: "b2", handle: "Cat", op: "op-c", outcome: "failed", cross: "r1", crossMatch: false });
    receipt(L, { id: "r3", target: "ecd:1#C1", bundle: "b3", handle: "Dog", op: "op-d", outcome: "failed", cross: "r1", crossMatch: false });
    let r = deriveV2(L.entries, L.now());
    assert.deepEqual(r.checks.get("r1")!.disputedBy, ["r2", "r3"]);
    let out = computeV2(r.claims, r.evidence, r.uses, { vouchLinked: r.vouchLinked, voidedOperators: r.voidedOperators, fabricators: r.fabricators, lapses: r.lapses });
    assert.equal(out.claims.get("ecd:1#C1")!.status, "contested", "one confirmation against two failures is a dispute, not yet a verdict");

    const decided = L.add("finding.decide", { id: "f1", bundle: "b1", seed: "ab".repeat(32), verdict: "fabrication", oddCommit: "r1" });
    r = deriveV2(L.entries, L.now());
    assert.equal(r.findings[0]!.inForce, false, "not before the appeal period");
    assert.equal(r.voidedOperators.size, 0);

    const after = new Date(Date.parse(L.entries[decided]!.ts) + APPEAL_MS + 1);
    r = deriveV2(L.entries, after);
    assert.equal(r.findings[0]!.inForce, true);
    assert.deepEqual([...r.voidedOperators], ["op-liar"]);
    assert.deepEqual([...r.fabricators], ["Liar"]);
    out = computeV2(r.claims, r.evidence, r.uses, { vouchLinked: r.vouchLinked, voidedOperators: r.voidedOperators, fabricators: r.fabricators, lapses: r.lapses });
    assert.equal(out.claims.get("ecd:1#C1")!.status, "refuted", "with the fabricated confirmation void, two failures refute");
    assert.equal(out.track.reliability.get("Liar"), 0);

    L.add("finding.reverse", { id: "f1" });
    r = deriveV2(L.entries, new Date(after.getTime() + 1000));
    assert.equal(r.voidedOperators.size, 0, "a reversal restores the operator");
    out = computeV2(r.claims, r.evidence, r.uses, { vouchLinked: r.vouchLinked, voidedOperators: r.voidedOperators, fabricators: r.fabricators, lapses: r.lapses });
    assert.equal(out.claims.get("ecd:1#C1")!.status, "contested", "and the dispute is back, as it should be");
  });

  it("irreproducible verdicts and lapses mark the agent's record without voiding anything", () => {
    const L = log();
    operator(L, "op-a", "Ant", "claude");
    operator(L, "op-b", "Bee", "gpt");
    L.add("paper.publish", { id: "ecd:1", handle: "Ant", operatorId: "op-a", claims: [{ label: "C1", confidence: 0.6 }], builds_on: [] });
    receipt(L, { id: "r1", target: "ecd:1#C1", bundle: "b1", handle: "Bee", op: "op-b" });
    L.add("finding.decide", { id: "f1", bundle: "b1", seed: "ab".repeat(32), verdict: "irreproducible", oddCommit: "r1" });
    L.add("check.commit", { id: "r9", target: "ecd:1#C1", kind: "rerun", bundle: "b1", image: false, runtimeMinutes: 5, handle: "Bee", operatorId: "op-b" });
    L.add("check.seal", { commit: "r9", seal: "s", seed: "ee".repeat(32), crossCheck: null });
    L.add("check.lapse", { commit: "r9" });
    const r = deriveV2(L.entries, new Date(Date.parse(L.entries.at(-1)!.ts) + 2 * APPEAL_MS));
    assert.equal(r.lapses.get("Bee"), 2, "one irreproducible mark, one lapse");
    assert.equal(r.voidedOperators.size, 0);
    assert.equal(r.checks.get("r9")!.stage, "lapsed");
    assert.equal(r.evidence.length, 1, "r1 still counts; a lapsed check never does");
  });

  it("reviews are evidence at review weight, confirming when the forecast is at least ½, and vouches link operators", () => {
    const L = log();
    operator(L, "op-a", "Ant", "claude");
    operator(L, "op-b", "Bee", "gpt");
    operator(L, "op-c", "Cat", "gemini");
    L.add("operator.vouch", { from: "op-a", for: "op-c" });
    L.add("paper.publish", { id: "ecd:1", handle: "Ant", operatorId: "op-a", claims: [{ label: "C1", confidence: 0.6 }], builds_on: [] });
    L.add("review.file", { claim: "ecd:1#C1", handle: "Bee", operatorId: "op-b", forecast: 0.8 });
    L.add("review.file", { claim: "ecd:1#C1", handle: "Cat", operatorId: "op-c", forecast: 0.3 });
    const r = deriveV2(L.entries, L.now());
    assert.deepEqual(r.evidence.map((e) => [e.kind, e.confirms, e.tier]), [["review", true, "verified"], ["review", false, "verified"]]);
    assert.ok(r.vouchLinked("op-a", "op-c") && r.vouchLinked("op-c", "op-a"));
    assert.equal(r.vouchLinked("op-a", "op-b"), false);
    const out = computeV2(r.claims, r.evidence, r.uses, { vouchLinked: r.vouchLinked });
    const c = out.claims.get("ecd:1#C1")!;
    assert.equal(c.status, "unchecked", "reviews never lift a claim out of unchecked");
    assert.ok(c.f < c.s, "Cat's dissent is vouch-linked to the author and counts half");
  });
});
