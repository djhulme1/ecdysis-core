/**
 * The record derived from the log (src/core/v2/flow.ts): every input to
 * credence and the track record comes from entries alone, as constitution
 * 0.4 requires; the network of claims (network/0.1) is the claims and their
 * edges, use counted per operator; and the receipt life cycle, findings,
 * appeals and reversals behave as the design says.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { deriveV2, type V2Entry, type V2EntryType } from "../src/core/v2/flow.js";
import { computeV2 } from "../src/core/v2/scoring.js";
import { APPEAL_MS } from "../src/core/v2/receipts.js";
import { GENERAL, REPORTED, REPRODUCTION } from "./kinds-kit.js";

function log() {
  const entries: V2Entry[] = [];
  let t = Date.UTC(2026, 9, 2, 12, 0, 0);
  // What the service writes since scope/0.1 and kinds/0.1: an empirical claim from human literature with its scope and
  // fidelity, a commit with its design (test/kinds-kit.ts). An entry that states its own keeps them.
  const add = (type: V2EntryType, payload: Record<string, unknown>, dtMs = 60_000) => {
    t += dtMs;
    const p = type === "claim.external" && payload["kind"] !== "conceptual" && !("scope" in payload) ? { ...payload, scope: GENERAL, fidelity: REPORTED }
      : type === "check.commit" && !("design" in payload) ? { ...payload, design: REPRODUCTION } : payload;
    entries.push({ seq: entries.length, ts: new Date(t).toISOString(), type, payload: p });
    return entries.length - 1;
  };
  return { entries, add, now: () => new Date(t) };
}

/** Claim ids as the service writes them: "ecd:" or "ext:" and 16 hex characters. */
const ECD = (n: number) => `ecd:${n.toString(16).padStart(16, "0")}`;
const EXT = (n: number) => `ext:${n.toString(16).padStart(16, "0")}`;

/** One claim.publish entry, as the service writes it once screening passes. */
function claim(L: ReturnType<typeof log>, id: string, handle: string, op: string, o: { confidence?: number; builds_on?: Array<Record<string, unknown>>; models?: string[]; kind?: "conceptual" } = {}) {
  return L.add("claim.publish", {
    id, cid: id.slice(4).padEnd(64, "0"), handle, operatorId: op, text: `claim ${id}`, test: `the test of ${id}`, field: "ml",
    confidence: o.confidence ?? 0.6, ...(o.kind ? { kind: o.kind } : { scope: GENERAL }), builds_on: o.builds_on ?? [], ...(o.models ? { models: o.models } : {}),
  });
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

describe("the record from the log", () => {
  it("publishes claims one entry each, with foundations and use from what each relies on, and external claims as targets", () => {
    const L = log();
    operator(L, "op-a", "Ant", "claude");
    operator(L, "op-b", "Bee", "gpt");
    const ks94 = EXT(0x94);
    L.add("claim.external", { id: ks94, handle: "Ant", operatorId: "op-a", source: "doi:10.1126/science.264.5163.1297", quote: "alpha_c = 4.17 +/- 0.05", test: "alpha_c outside [4.12, 4.22] at N = 200" });
    claim(L, ECD(1), "Ant", "op-a", { confidence: 0.8, builds_on: [{ id: ks94, rel: "extends", basis: "reproduced" }] });
    claim(L, ECD(2), "Bee", "op-b", { confidence: 0.7, builds_on: [{ id: ECD(1), rel: "method", basis: "reviewed" }] });
    claim(L, ECD(3), "Bee", "op-b", { builds_on: [{ id: ECD(1), rel: "background" }, { id: ECD(2), rel: "replicates" }] });
    const r = deriveV2(L.entries, L.now());
    assert.deepEqual(r.claims.map((c) => c.ref), [ks94, ECD(1), ECD(2), ECD(3)]);
    assert.deepEqual(r.claims[1]!.foundations, [ks94]);
    assert.deepEqual(r.claims[2]!.foundations, [ECD(1)]);
    assert.deepEqual(r.claims[3]!.foundations, [], "background and declared relations are not foundations");
    assert.deepEqual(r.uses, [{ claim: ks94, by: ECD(1), operatorId: "op-a", tier: "verified" }, { claim: ECD(1), by: ECD(2), operatorId: "op-b", tier: "verified" }], "a use carries the relying operator's tier, so cheap identities cannot inflate use");
    assert.deepEqual(r.edges.map((e) => [e.from, e.to, e.rel]), [[ECD(1), ks94, "extends"], [ECD(2), ECD(1), "method"], [ECD(3), ECD(1), "background"], [ECD(3), ECD(2), "replicates"]]);
    assert.equal(r.external.get(ks94)!.test, "alpha_c outside [4.12, 4.22] at N = 200");
    const out = computeV2(r.claims, r.evidence, r.uses, { ringLinked: r.ringLinked });
    assert.equal(out.claims.get(ECD(1))!.use, 1);
    assert.equal(out.claims.get(ks94)!.status, "unchecked");
  });

  it("an edge names only a claim already on the record, so the network is acyclic; a foundation without a basis is no foundation", () => {
    const L = log();
    operator(L, "op-a", "Ant", "claude");
    operator(L, "op-b", "Bee", "gpt");
    // A hostile entry names a claim that comes later, itself, and a foundation with no basis: those edges are dropped.
    claim(L, ECD(1), "Ant", "op-a", { builds_on: [{ id: ECD(2), rel: "extends", basis: "reproduced" }, { id: ECD(1), rel: "extends", basis: "reproduced" }] });
    claim(L, ECD(2), "Bee", "op-b", { builds_on: [{ id: ECD(1), rel: "extends" }, { id: ECD(1), rel: "replicates" }] });
    claim(L, ECD(1), "Bee", "op-b", { builds_on: [] });
    const r = deriveV2(L.entries, L.now());
    assert.deepEqual(r.claims.map((c) => c.ref), [ECD(1), ECD(2)], "the first entry for an id stands");
    assert.deepEqual(r.claims[0]!.foundations, [], "no edge to a later claim or to itself: log order is a topological order");
    assert.deepEqual(r.claims[1]!.foundations, [], "no citation on faith");
    assert.deepEqual(r.edges.map((e) => [e.from, e.to, e.rel]), [[ECD(2), ECD(1), "replicates"]], "the foundation without a basis is dropped whole, so the declared relation after it stands");
    assert.equal(r.native.get(ECD(1))!.handle, "Ant");
  });

  it("use is counted per operator: splitting work into many claims does not multiply it", () => {
    const L = log();
    operator(L, "op-a", "Ant", "claude");
    operator(L, "op-b", "Bee", "gpt");
    operator(L, "op-c", "Cat", "gemini");
    claim(L, ECD(1), "Ant", "op-a");
    // Bee relies on ECD(1) from five claims; Cat from one.
    for (let i = 0; i < 5; i++) claim(L, ECD(10 + i), "Bee", "op-b", { builds_on: [{ id: ECD(1), rel: "extends", basis: "reproduced" }] });
    claim(L, ECD(20), "Cat", "op-c", { builds_on: [{ id: ECD(1), rel: "extends", basis: "reviewed" }] });
    // The author's own claims resting on it add nothing.
    claim(L, ECD(30), "Ant", "op-a", { builds_on: [{ id: ECD(1), rel: "extends", basis: "reproduced" }] });
    const r = deriveV2(L.entries, L.now());
    assert.equal(r.uses.filter((u) => u.claim === ECD(1)).length, 7, "every use is on the record");
    const out = computeV2(r.claims, r.evidence, r.uses, { ringLinked: r.ringLinked });
    assert.equal(out.claims.get(ECD(1))!.use, 2, "two independent operators rely on it: Bee's five claims count once, Ant's own none");
  });

  it("a receipt becomes evidence only once its result is filed; its tier and families come from the log", () => {
    const L = log();
    operator(L, "op-a", "Ant", "claude");
    operator(L, "op-b", "Bee", "gpt");
    L.add("operator.tier", { operatorId: "op-c", tier: "account" });
    L.add("agent.register", { handle: "Cat", operatorId: "op-c", publicKey: "pk-c" });
    claim(L, ECD(1), "Ant", "op-a", { confidence: 0.8 });
    L.add("check.commit", { id: "r1", target: ECD(1), kind: "replication", bundle: "b1", image: true, runtimeMinutes: 5, handle: "Bee", operatorId: "op-b" });
    let r = deriveV2(L.entries, L.now());
    assert.equal(r.evidence.length, 0, "a commitment is not evidence");
    assert.equal(r.checks.get("r1")!.stage, "committed");
    L.add("check.seal", { commit: "r1", seal: "s", seed: "cd".repeat(32), crossCheck: null });
    L.add("check.result", { commit: "r1", outcome: "confirmed", crossMatch: null });
    receipt(L, { id: "r2", target: ECD(1), bundle: "b2", handle: "Cat", op: "op-c", cross: "r1", crossMatch: true, models: ["gemini-3", "gpt-5.2"] });
    r = deriveV2(L.entries, L.now());
    assert.equal(r.evidence.length, 2);
    assert.deepEqual(r.evidence.map((e) => [e.agent, e.tier, e.families]), [["Bee", "verified", ["gpt"]], ["Cat", "account", ["gemini", "gpt"]]]);
    assert.deepEqual(r.checks.get("r1")!.verifiedBy, [], "an account-tier operator's matching cross-check does not verify r1: only verified operators verify or dispute");
    assert.deepEqual(r.checks.get("r1")!.otherCrossChecks, [{ id: "r2", match: true }], "but it is kept and shown");
    assert.deepEqual(r.receiptsByClaim.get(ECD(1))!.map((x) => x.id), ["r1", "r2"]);
    const out = computeV2(r.claims, r.evidence, r.uses, { ringLinked: r.ringLinked });
    const c = out.claims.get(ECD(1))!;
    assert.equal(c.status, "supported", "one verified replication (Bee); Cat's account-tier check moves credence but cannot resolve");
    assert.deepEqual(c.families, ["gpt"]);
  });

  it("a finding of fabrication takes effect after the appeal period, voids the operator, and a reversal restores everything", () => {
    const L = log();
    operator(L, "op-a", "Ant", "claude");
    operator(L, "op-liar", "Liar", "gpt");
    operator(L, "op-c", "Cat", "gemini");
    operator(L, "op-d", "Dog", "grok");
    claim(L, ECD(1), "Ant", "op-a");
    receipt(L, { id: "r1", target: ECD(1), bundle: "b1", handle: "Liar", op: "op-liar", outcome: "confirmed" });
    receipt(L, { id: "r2", target: ECD(1), bundle: "b2", handle: "Cat", op: "op-c", outcome: "failed", cross: "r1", crossMatch: false });
    receipt(L, { id: "r3", target: ECD(1), bundle: "b3", handle: "Dog", op: "op-d", outcome: "failed", cross: "r1", crossMatch: false });
    let r = deriveV2(L.entries, L.now());
    assert.deepEqual(r.checks.get("r1")!.disputedBy, ["r2", "r3"]);
    let out = computeV2(r.claims, r.evidence, r.uses, { ringLinked: r.ringLinked, voidedOperators: r.voidedOperators, fabricators: r.fabricators, lapses: r.lapses });
    assert.equal(out.claims.get(ECD(1))!.status, "contested", "one confirmation against two failures is a dispute, not yet a verdict");

    const decided = L.add("finding.decide", { id: "f1", bundle: "b1", seed: "ab".repeat(32), verdict: "fabrication", oddCommit: "r1" });
    r = deriveV2(L.entries, L.now());
    assert.equal(r.findings[0]!.inForce, false, "not before the appeal period");
    assert.equal(r.voidedOperators.size, 0);

    const after = new Date(Date.parse(L.entries[decided]!.ts) + APPEAL_MS + 1);
    r = deriveV2(L.entries, after);
    assert.equal(r.findings[0]!.inForce, true);
    assert.deepEqual([...r.voidedOperators], ["op-liar"]);
    assert.deepEqual([...r.fabricators], ["Liar"]);
    out = computeV2(r.claims, r.evidence, r.uses, { ringLinked: r.ringLinked, voidedOperators: r.voidedOperators, fabricators: r.fabricators, lapses: r.lapses });
    assert.equal(out.claims.get(ECD(1))!.status, "refuted", "with the fabricated confirmation void, two failures refute");
    assert.equal(out.track.reliability.get("Liar"), 0);

    L.add("finding.reverse", { id: "f1" });
    r = deriveV2(L.entries, new Date(after.getTime() + 1000));
    assert.equal(r.voidedOperators.size, 0, "a reversal restores the operator");
    out = computeV2(r.claims, r.evidence, r.uses, { ringLinked: r.ringLinked, voidedOperators: r.voidedOperators, fabricators: r.fabricators, lapses: r.lapses });
    assert.equal(out.claims.get(ECD(1))!.status, "contested", "and the dispute is back, as it should be");
  });

  it("irreproducible verdicts and lapses mark the agent's record without voiding anything", () => {
    const L = log();
    operator(L, "op-a", "Ant", "claude");
    operator(L, "op-b", "Bee", "gpt");
    claim(L, ECD(1), "Ant", "op-a");
    receipt(L, { id: "r1", target: ECD(1), bundle: "b1", handle: "Bee", op: "op-b" });
    L.add("finding.decide", { id: "f1", bundle: "b1", seed: "ab".repeat(32), verdict: "irreproducible", oddCommit: "r1" });
    L.add("check.commit", { id: "r9", target: ECD(1), kind: "rerun", bundle: "b1", image: false, runtimeMinutes: 5, handle: "Bee", operatorId: "op-b" });
    L.add("check.seal", { commit: "r9", seal: "s", seed: "ee".repeat(32), crossCheck: null });
    L.add("check.lapse", { commit: "r9" });
    const r = deriveV2(L.entries, new Date(Date.parse(L.entries.at(-1)!.ts) + 2 * APPEAL_MS));
    assert.equal(r.lapses.get("Bee"), 2, "one irreproducible mark, one lapse");
    assert.equal(r.voidedOperators.size, 0);
    assert.equal(r.checks.get("r9")!.stage, "lapsed");
    assert.equal(r.evidence.length, 1, "r1 still counts; a lapsed check never does");
  });

  it("reviews are evidence at review weight, confirming when the forecast is at least ½; operators that confirm each other's claims are linked", () => {
    const L = log();
    operator(L, "op-a", "Ant", "claude");
    operator(L, "op-b", "Bee", "gpt");
    operator(L, "op-c", "Cat", "gemini");
    claim(L, ECD(1), "Ant", "op-a");
    claim(L, ECD(2), "Cat", "op-c");
    claim(L, ECD(3), "Bee", "op-b");
    // Ant and Cat review each other's claims favourably: a ring. Bee only reviews.
    L.add("review.file", { claim: ECD(2), handle: "Ant", operatorId: "op-a", forecast: 0.9 });
    L.add("review.file", { claim: ECD(1), handle: "Cat", operatorId: "op-c", forecast: 0.8 });
    L.add("review.file", { claim: ECD(3), handle: "Ant", operatorId: "op-a", forecast: 0.3 });
    L.add("review.file", { claim: ECD(1), handle: "Bee", operatorId: "op-b", forecast: 0.2 });
    const r = deriveV2(L.entries, L.now());
    assert.deepEqual(r.evidence.map((e) => [e.claim, e.kind, e.confirms, e.tier]), [[ECD(2), "review", true, "verified"], [ECD(1), "review", true, "verified"], [ECD(3), "review", false, "verified"], [ECD(1), "review", false, "verified"]]);
    assert.ok(r.ringLinked("op-a", "op-c") && r.ringLinked("op-c", "op-a"), "each confirmed the other's claim");
    assert.equal(r.ringLinked("op-a", "op-b"), false, "a dissent links nobody");
    const out = computeV2(r.claims, r.evidence, r.uses, { ringLinked: r.ringLinked });
    const c = out.claims.get(ECD(1))!;
    assert.equal(c.status, "unchecked", "reviews never lift a claim out of unchecked");
    assert.ok(c.s < c.f, "Cat's favourable review is ring-linked to the author and counts half; Bee's dissent counts in full");
  });
});
