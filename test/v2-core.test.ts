/**
 * Ecdysis v2's core (claude/ecdysis-v2-design.md; sanity check
 * claude/ecdysis-v2-sanity-check.md): credence/0.2, the track record and
 * receipts. Each result the design states is checked here against its own
 * definition, numerically, so the documents and the code can't drift apart.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import {
  CREDENCE_V2_PARAMS as P,
  calibrationOf,
  computeCredenceV2,
  disputeOf,
  diversityFactor,
  logit,
  modelFamilies,
  modelFamily,
  priorOf,
  sigma,
  type ClaimInput,
  type EvidenceInput,
} from "../src/core/v2/credence.js";
import { computeV2, marketCredit, reliabilityOf } from "../src/core/v2/scoring.js";
import {
  compareOutputs,
  FINDING_MIN_RUNS,
  isDeterministic,
  pickCrossCheck,
  sealCommit,
  seedFromSeal,
  seedInsensitive,
  settleRuns,
  validateCheckCommit,
  validateCheckResult,
  verifySeal,
  type Bundle,
} from "../src/core/v2/receipts.js";
import { generateKeyPair } from "../src/core/crypto.js";
import { sha256, toHex } from "../src/core/canonical.js";

const near = (a: number, b: number, eps = 1e-9) => assert.ok(Math.abs(a - b) <= eps, `${a} ≉ ${b}`);

const claim = (ref: string, seq: number, o: Partial<ClaimInput> = {}): ClaimInput => ({
  ref, paper: ref.split("#")[0]!, authorOperator: "op-author", stated: 0.8, foundations: [], seq, ...o,
});
let n = 0;
/** A verified operator on a distinct model family per operator, unless said otherwise. */
const ev = (claimRef: string, kind: EvidenceInput["kind"], confirms: boolean, op: string, o: Partial<EvidenceInput> = {}): EvidenceInput => ({
  id: `e${++n}`, claim: claimRef, kind, confirms, agent: `${op}-agent`, operatorId: op, tier: "verified", families: [`fam-${op}`], seq: 100 + n, ...o,
});
/** Everyone fully reliable, so a check's weight is just independence × tier × diversity. */
const full = { reliability: () => 1 };

describe("credence/0.2", () => {
  it("an unchecked claim sits at its prior, which its foundations cap", () => {
    const r = computeCredenceV2([claim("a#C1", 1, { stated: 0.9 }), claim("b#C1", 2, { foundations: ["a#C1"] })], [], []);
    const a = r.get("a#C1")!;
    const b = r.get("b#C1")!;
    near(a.credence, priorOf(0.9, P.rho0, []));
    near(b.prior, priorOf(0.8, P.rho0, [a.credence]));
    assert.equal(a.status, "unchecked");
    assert.equal(b.status, "unchecked");
  });

  it("Proposition 1: ∂ℓ(c)/∂ℓ(f) = κ_c(1 − p_f), so the weakest foundation lifts a claim most", () => {
    const fs = [0.9, 0.5];
    const q = priorOf(0.8, 0.5, fs);
    const kappa = (q - P.epsilon) / (q * (1 - q));
    for (const [i, f] of fs.entries()) {
      const h = 1e-6;
      const bumped = fs.map((v, j) => (j === i ? sigma(logit(v) + h) : v));
      const numeric = (logit(priorOf(0.8, 0.5, bumped)) - logit(q)) / h;
      near(numeric, kappa * (1 - f), 1e-4);
    }
    const lifted = (i: number) => priorOf(0.8, 0.5, fs.map((v, j) => (j === i ? sigma(logit(v) + Math.log(4)) : v)));
    assert.ok(lifted(1) - q > 2 * (lifted(0) - q), "replicating the weak foundation gains more than twice as much");
    // The platform's own "what would raise this claim most" ranks the weak foundation first.
    const r = computeCredenceV2(
      [claim("strong#C1", 1, { stated: 0.95 }), claim("weak#C1", 2, { stated: 0.5 }), claim("top#C1", 3, { foundations: ["strong#C1", "weak#C1"] })],
      [], [],
    );
    assert.equal(r.get("top#C1")!.lift[0]!.ref, "weak#C1");
    assert.ok(r.get("top#C1")!.lift[0]!.gain > r.get("top#C1")!.lift[1]!.gain);
  });

  it("a split is contested, not netted away: 5 confirmations and 5 failures give D = 10, where credence/0.1 said refuted", () => {
    near(5 * Math.log(4) - 5 * Math.log(6), -2.0273, 1e-4);
    const items = [
      ...[1, 2, 3, 4, 5].map((i) => ev("x#C1", "replication", true, `op-y${i}`)),
      ...[1, 2, 3, 4, 5].map((i) => ev("x#C1", "replication", false, `op-n${i}`)),
    ];
    const x = computeCredenceV2([claim("x#C1", 1, { stated: 0.5, calibration: 0 })], items, [], full).get("x#C1")!;
    near(x.s, 5);
    near(x.f, 5);
    near(x.dispute, 10);
    assert.equal(x.status, "contested");
    near(x.disputePriority, 0.5 * 10);
  });

  it("dispute measures disagreement, not evidence: 0 when agreed, ~4f for a lone dissenter, contested from a seventh", () => {
    assert.equal(disputeOf(0, 0), 0);
    assert.equal(disputeOf(7, 0), 0);
    near(disputeOf(9, 1), 3.6);
    near(disputeOf(99, 1), 3.96);
    near((1 - Math.sqrt(0.5)) / 2, 0.1464, 1e-4);
    const mk = (yes: number, no: number) => computeCredenceV2(
      [claim("d#C1", 1)],
      [...Array.from({ length: yes }, (_, i) => ev("d#C1", "replication", true, `op-a${i}`)), ...Array.from({ length: no }, (_, i) => ev("d#C1", "replication", false, `op-b${i}`))],
      [], full,
    ).get("d#C1")!.status;
    assert.equal(mk(5, 1), "contested", "one dissent in six (16.7%) is over the line: 4r(1 − r) = 0.556");
    assert.notEqual(mk(6, 1), "contested", "one in seven (14.3%) is just under it: 4r(1 − r) = 0.490");
  });

  it("re-runs prove honesty, not truth: a confirming re-run weighs a review, a failing one half a refutation, and neither sets a status", () => {
    const one = computeCredenceV2([claim("r#C1", 1)], [ev("r#C1", "rerun", true, "op-r1")], [], full).get("r#C1")!;
    near(one.logOdds - logit(one.prior), Math.log(4) * 0.25);
    assert.equal(one.reproduced, true);
    assert.equal(one.status, "unchecked", "reproduced, but no replication yet");
    const bad = computeCredenceV2([claim("r#C1", 1)], [ev("r#C1", "rerun", false, "op-r1")], [], full).get("r#C1")!;
    near(bad.logOdds - logit(bad.prior), -Math.log(6) * 0.5);
    assert.equal(bad.status, "unchecked", "a misreport moves credence; only a failed replication can refute");
    const many = [1, 2, 3, 4, 5, 6].map((i) => ev("r#C1", "rerun", true, `op-r${i}`));
    const onlyReruns = computeCredenceV2([claim("r#C1", 1)], many, [], full).get("r#C1")!;
    assert.equal(onlyReruns.status, "unchecked", "six re-runs never establish, nor even support");
    const withRep = computeCredenceV2([claim("r#C1", 1)], [...many, ev("r#C1", "replication", true, "op-rep")], [], full).get("r#C1")!;
    assert.equal(withRep.status, "supported", "one replication, one model family: supported, not established");
    const twoFams = computeCredenceV2([claim("r#C1", 1)], [...many, ev("r#C1", "replication", true, "op-rep"), ev("r#C1", "replication", true, "op-rep2")], [], full).get("r#C1")!;
    assert.equal(twoFams.status, "established", "two replications from two model families");
  });

  it("a monoculture is not a crowd: same-family confirmations count ½, ¼, …, and established needs two families", () => {
    const same = [1, 2, 3].map((i) => ev("m#C1", "replication", true, `op-c${i}`, { families: ["claude"] }));
    const r = computeCredenceV2([claim("m#C1", 1)], same, [], full).get("m#C1")!;
    near(r.logOdds - logit(r.prior), Math.log(4) * (1 + 0.5 + 0.25));
    near(r.s, 1.75);
    assert.equal(r.status, "supported", "credence is high, but one family never establishes");
    const mixed = computeCredenceV2([claim("m#C1", 1)], [...same, ev("m#C1", "replication", true, "op-g", { families: ["gemini"] })], [], full).get("m#C1")!;
    assert.deepEqual(mixed.families, ["claude", "gemini"]);
    assert.equal(mixed.status, "established");
    const unknown = computeCredenceV2([claim("m#C1", 1)], [1, 2].map((i) => ev("m#C1", "replication", true, `op-u${i}`, { families: [] })), [], full).get("m#C1")!;
    near(unknown.s, 2); // undeclared items are not discounted against each other
    assert.equal(unknown.status, "supported", "but undeclared is no family: established needs two declared ones");
  });

  it("declaring models is optional, and an agent may declare several: the discount follows the overlap", () => {
    // After a Claude-only confirmation: another Claude-only confirmation weighs ½; a three-model one that includes Claude weighs 5/6; a Gemini-only one weighs 1.
    const claude = [{ families: ["claude"], confirms: true }];
    near(diversityFactor(["claude"], true, claude), 0.5);
    near(diversityFactor(["claude", "gpt", "gemini"], true, claude), 5 / 6);
    near(diversityFactor(["gemini"], true, claude), 1);
    near(diversityFactor(["claude"], true, [{ families: ["claude", "gpt"], confirms: true }]), 0.5, 1e-9); // fully covered by an earlier mixed check
    near(diversityFactor([], true, [...claude, { families: ["gpt"], confirms: true }]), 1); // undeclared: no discount, and no diversity credit either
    const items = [
      ev("d2#C1", "replication", true, "op-a", { families: ["claude"] }),
      ev("d2#C1", "replication", true, "op-b", { families: ["claude", "gpt", "gemini"] }),
    ];
    const r = computeCredenceV2([claim("d2#C1", 1)], items, [], full).get("d2#C1")!;
    near(r.s, 1 + 5 / 6);
    assert.deepEqual(r.families, ["claude", "gemini", "gpt"]);
    assert.equal(r.status, "established", "the union of declared families spans two or more");
    const undeclaredOnly = computeCredenceV2([claim("d2#C1", 1)], [ev("d2#C1", "replication", true, "op-a", { families: [] }), ev("d2#C1", "replication", true, "op-b", { families: [] })], [], full).get("d2#C1")!;
    assert.equal(undeclaredOnly.status, "supported", "the incentive to declare: undeclared checks cannot show diversity");
  });

  it("modelFamily and modelFamilies normalise declared models", () => {
    assert.equal(modelFamily("claude-opus-5-5"), "claude");
    assert.equal(modelFamily("Anthropic/Claude Sonnet 5.5"), "claude");
    assert.equal(modelFamily("gpt-5.2"), "gpt");
    assert.equal(modelFamily("o3-pro"), "gpt");
    assert.equal(modelFamily("Gemini 3 Pro"), "gemini");
    assert.equal(modelFamily("mixtral-8x22b"), "mistral");
    assert.equal(modelFamily("grok-4"), "grok");
    assert.equal(modelFamily(""), null);
    assert.equal(modelFamily(null), null);
    assert.deepEqual(modelFamilies(["gpt-5.2", "o3-pro", "Claude Opus 5.5"]), ["claude", "gpt"]);
    assert.deepEqual(modelFamilies("grok-4"), ["grok"]);
    assert.deepEqual(modelFamilies(null), []);
  });

  it("resolution needs verified evidence: cheap identities move credence a little and never a status", () => {
    const two = [1, 2].map((i) => ev("v#C1", "replication", true, `op-s${i}`, { tier: "unverified" }));
    const r2 = computeCredenceV2([claim("v#C1", 1)], two, [], full).get("v#C1")!;
    near(r2.logOdds - logit(r2.prior), Math.log(4) * 0.25 * 2); // each unverified check weighs a quarter
    // A crowd of cheap identities, declared or not, moves a claim by at most 3:1 all together.
    const crowd = Array.from({ length: 20 }, (_, i) => ev("v#C1", "replication", true, `op-s${i}`, { tier: "unverified", families: [] }));
    const r = computeCredenceV2([claim("v#C1", 1)], crowd, [], full).get("v#C1")!;
    near(r.logOdds - logit(r.prior), Math.log(3)); // capped
    assert.equal(r.s, 0, "no resolution mass");
    assert.equal(r.status, "unchecked");
    assert.equal(r.dispute, 0);
    const accounts = Array.from({ length: 20 }, (_, i) => ev("v#C1", "replication", true, `op-a${i}`, { tier: "account", families: [] }));
    near(computeCredenceV2([claim("v#C1", 1)], accounts, [], full).get("v#C1")!.logOdds - logit(r.prior), Math.log(3)); // accounts are cheap too: the same cap
    const against = Array.from({ length: 20 }, (_, i) => ev("v#C1", "replication", false, `op-n${i}`, { tier: "unverified", families: [] }));
    near(computeCredenceV2([claim("v#C1", 1)], against, [], full).get("v#C1")!.logOdds - logit(r.prior), -Math.log(3)); // and in the other direction
    const acct = computeCredenceV2([claim("v#C1", 1)], [ev("v#C1", "replication", true, "op-acc", { tier: "account" })], [], full).get("v#C1")!;
    near(acct.logOdds - logit(acct.prior), Math.log(4) * 0.5);
    assert.equal(acct.status, "unchecked");
    // The cap is one cap: checks and reviews from non-verified operators share it, so splitting a crowd between the two
    // kinds of report buys nothing. (Verified operators' reviews have their own ln 3 cap.)
    const mixed = [...crowd, ...Array.from({ length: 12 }, (_, i) => ev("v#C1", "review", true, `op-r${i}`, { tier: "unverified", families: [] }))];
    near(computeCredenceV2([claim("v#C1", 1)], mixed, [], full).get("v#C1")!.logOdds - logit(r.prior), Math.log(3));
    const both = [...crowd, ...[1, 2, 3].map((i) => ev("v#C1", "review", true, `op-w${i}`))]; // verified reviews beside the crowd
    near(computeCredenceV2([claim("v#C1", 1)], both, [], full).get("v#C1")!.logOdds - logit(r.prior), Math.log(3) + 3 * Math.log(4) / 4);
  });

  it("refuted needs a failed verified replication and low credence; a refuted foundation makes dependants contested", () => {
    const r = computeCredenceV2(
      [claim("f#C1", 1), claim("g#C1", 2, { foundations: ["f#C1"] })],
      [ev("f#C1", "replication", false, "op-1"), ev("f#C1", "replication", false, "op-2")], [], full,
    );
    assert.equal(r.get("f#C1")!.status, "refuted");
    assert.equal(r.get("g#C1")!.status, "contested");
  });

  it("one operator, one voice: its own evidence is worth nothing, and several items count once", () => {
    const own = computeCredenceV2([claim("o#C1", 1)], [ev("o#C1", "replication", true, "op-author")], [], full).get("o#C1")!;
    assert.equal(own.s, 0);
    assert.equal(own.status, "unchecked");
    const many = computeCredenceV2([claim("o#C1", 1)], [1, 2, 3].map(() => ev("o#C1", "replication", true, "op-same")), [], full).get("o#C1")!;
    near(many.s, 1);
  });

  it("reviews move a little, both ways, and never more than ln 3 together", () => {
    const pro = computeCredenceV2([claim("w#C1", 1)], [1, 2, 3, 4, 5, 6, 7, 8].map((i) => ev("w#C1", "review", true, `op-v${i}`)), [], full).get("w#C1")!;
    near(pro.logOdds - logit(pro.prior), Math.log(3));
    assert.equal(pro.status, "unchecked", "reviews never lift a claim out of unchecked");
    const con = computeCredenceV2([claim("w#C1", 1)], [ev("w#C1", "review", false, "op-v1")], [], full).get("w#C1")!;
    near(con.logOdds - logit(con.prior), -Math.log(4) / 4);
  });

  it("use is never an input to credence, but raises the bar", () => {
    const base = computeCredenceV2([claim("u#C1", 1)], [], []).get("u#C1")!;
    const used = computeCredenceV2([claim("u#C1", 1)], [], [1, 2, 3, 4, 5, 6].map((i) => ({ claim: "u#C1", paper: `p${i}`, operatorId: `op-p${i}`, tier: "verified" as const }))).get("u#C1")!;
    near(used.credence, base.credence);
    near(used.use, 6);
    assert.ok(used.threshold > base.threshold);
    const self = computeCredenceV2([claim("u#C1", 1)], [], [{ claim: "u#C1", paper: "mine", operatorId: "op-author", tier: "verified" }]).get("u#C1")!;
    assert.equal(self.use, 0, "the author's own papers add no use");
    // Use is weighed by the citing operator's tier: a crowd of free identities citing a claim cannot raise its threshold,
    // hijack the queues or make it look load-bearing. A use without a tier is read as unverified (the safe default).
    const cheap = computeCredenceV2([claim("u#C1", 1)], [], [1, 2, 3, 4].map((i) => ({ claim: "u#C1", paper: `q${i}`, operatorId: `op-q${i}`, tier: "unverified" as const }))).get("u#C1")!;
    near(cheap.use, 1);
    assert.equal(computeCredenceV2([claim("u#C1", 1)], [], [1, 2, 3, 4].map((i) => ({ claim: "u#C1", paper: `q${i}`, operatorId: `op-q${i}` }))).get("u#C1")!.use, 1, "no tier: unverified");
    const acc = computeCredenceV2([claim("u#C1", 1)], [], [{ claim: "u#C1", paper: "a", operatorId: "op-acc", tier: "account" as const }, { claim: "u#C1", paper: "b", operatorId: "op-ver", tier: "verified" as const }]).get("u#C1")!;
    near(acc.use, 1.5);
  });
});

describe("credence/0.2: the maths review's defects, closed", () => {
  it("cheap identities cannot poison the diversity discount: only verified items set the families that discount later ones", () => {
    // Two verified replications on two families establish the claim.
    const base = computeCredenceV2([claim("d#C1", 1)], [ev("d#C1", "replication", true, "op-v1", { families: ["claude"] }), ev("d#C1", "replication", true, "op-v2", { families: ["gpt"] })], [], full).get("d#C1")!;
    assert.equal(base.status, "established");
    // Eight unverified sybils each declaring every common family, filed FIRST, used to multiply each later verified replication by 2^-8.
    const sybils = Array.from({ length: 8 }, (_, i) => ev("d#C1", "review", true, `op-s${i}`, { tier: "unverified", families: ["claude", "gpt", "gemini", "grok", "mistral", "llama", "deepseek", "qwen"], seq: 10 + i }));
    const poisoned = computeCredenceV2([claim("d#C1", 1)], [...sybils, ev("d#C1", "replication", true, "op-v1", { families: ["claude"], seq: 50 }), ev("d#C1", "replication", true, "op-v2", { families: ["gpt"], seq: 51 })], [], full).get("d#C1")!;
    assert.equal(poisoned.status, "established", "the verified replications keep their weight");
    near(poisoned.s, 2);
    assert.ok(poisoned.credence >= base.credence, "the sybils' capped agreement adds a little and takes nothing away");
    // Failing sybils cannot pull it down either beyond their cap, and the status stands.
    const against = computeCredenceV2([claim("d#C1", 1)], [...sybils.map((e) => ({ ...e, confirms: false })), ev("d#C1", "replication", true, "op-v1", { families: ["claude"], seq: 50 }), ev("d#C1", "replication", true, "op-v2", { families: ["gpt"], seq: 51 })], [], full).get("d#C1")!;
    assert.equal(against.status, "established");
    near(against.logOdds, base.logOdds - 8 * (Math.log(4) / 4) * P.tier.unverified, 1e-9);
    // A verified item on the same family still discounts a later one (the design's shared blind spots).
    const same = computeCredenceV2([claim("d#C1", 1)], [ev("d#C1", "replication", true, "op-v1", { families: ["claude"] }), ev("d#C1", "replication", true, "op-v2", { families: ["claude"] })], [], full).get("d#C1")!;
    near(same.s, 1.5);
  });

  it("the statuses are tested against verified evidence alone, and established needs two distinct verified operators", () => {
    // One verified operator declaring two models supplies two families but is one voice: not established.
    const one = computeCredenceV2([claim("o#C1", 1, { stated: 1 })], [ev("o#C1", "replication", true, "op-v1", { families: ["claude", "gpt"] })], [], full).get("o#C1")!;
    assert.equal(one.status, "supported");
    assert.ok(one.credence >= one.threshold, "credence alone would have cleared the bar");
    // Unverified reviews (capped at ln 3 all together) can lift the displayed credence over the bar, never the status.
    const author = claim("m#C1", 1, { stated: 0.6 });
    const partner = ev("m#C1", "replication", true, "op-v1", { families: ["claude"] });
    const partner2 = ev("m#C1", "replication", true, "op-v2", { families: ["gpt"], seq: 300 });
    const crowd = Array.from({ length: 10 }, (_, i) => ev("m#C1", "review", true, `op-c${i}`, { tier: "unverified", families: [] }));
    const shaky = { reliability: (a: string) => (a === "op-v2-agent" ? 0.2 : 1) }; // the second operator's record is poor, so verified evidence alone falls just short of τ0
    const verifiedOnly = computeCredenceV2([author], [partner, partner2], [], shaky).get("m#C1")!;
    assert.ok(verifiedOnly.credenceVerified < verifiedOnly.threshold, `verified alone: ${verifiedOnly.credenceVerified}`);
    assert.equal(verifiedOnly.status, "supported");
    const withCrowd = computeCredenceV2([author], [partner, partner2, ...crowd], [], shaky).get("m#C1")!;
    assert.ok(withCrowd.credence > withCrowd.credenceVerified, "the crowd shows in the displayed credence");
    assert.ok(withCrowd.credence >= withCrowd.threshold, "and would have carried the claim over the bar on its own");
    near(withCrowd.credenceVerified, verifiedOnly.credenceVerified);
    assert.equal(withCrowd.status, "supported", "but only verified evidence resolves");
    // Two verified operators linked by a vouch are not two independent voices on a third party's claim: the later weighs half.
    const linked = { ...full, vouchLinked: (a: string, b: string) => (a === "op-v1" && b === "op-v2") || (a === "op-v2" && b === "op-v1") };
    const pair = computeCredenceV2([claim("l#C1", 1, { stated: 1 })], [ev("l#C1", "replication", true, "op-v1", { families: ["claude"] }), ev("l#C1", "replication", true, "op-v2", { families: ["gpt"] })], [], linked).get("l#C1")!;
    near(pair.s, 1.5);
    const free = computeCredenceV2([claim("l#C1", 1, { stated: 1 })], [ev("l#C1", "replication", true, "op-v1", { families: ["claude"] }), ev("l#C1", "replication", true, "op-v2", { families: ["gpt"] })], [], full).get("l#C1")!;
    near(free.s, 2);
    assert.equal(free.status, "established");
  });

  it("the arithmetic never saturates: a prior of 1 or thirty confirmations leave room for the next failure to move the number", () => {
    const sure = computeCredenceV2([claim("s#C1", 1, { stated: 1, calibration: 1 })], [ev("s#C1", "replication", false, "op-v1"), ev("s#C1", "replication", false, "op-v2")], [], full).get("s#C1")!;
    assert.ok(Number.isFinite(sure.logOdds) && sure.credence < 1, `credence ${sure.credence}`);
    assert.ok(sure.credence < sigma(logit(sure.prior)), "two failures lowered it");
    const many = Array.from({ length: 30 }, (_, i) => ev("p#C1", "replication", true, `op-m${i}`, { families: [`f${i}`] }));
    const high = computeCredenceV2([claim("p#C1", 1)], many, [], full).get("p#C1")!;
    assert.ok(high.credence < 1 && high.logOdds < P.maxLogOdds && high.logOdds > P.softLogOdds);
    near(computeCredenceV2([claim("p#C1", 1)], many.slice(0, 2), [], full).get("p#C1")!.logOdds, logit(priorOf(0.8, P.rho0, [])) + 2 * Math.log(4), 1e-9); // untouched in the ordinary range
    assert.ok(high.valueOfChecking > 0, "still worth a look, however little");
    const thenFail = computeCredenceV2([claim("p#C1", 1)], [...many, ev("p#C1", "replication", false, "op-x", { seq: 999 })], [], full).get("p#C1")!;
    assert.ok(thenFail.credence < high.credence, "a failure after thirty confirmations still moves the number");
  });
});

/**
 * The maths review's six design questions, decided by Daniel on 3 Oct 2026
 * (all six as recommended): 1 two DECLARED families for established; 2 the
 * ring rule stays "ever"; 3 calibration derived from the record; 4 external
 * foundations at face value until verified evidence counts against them;
 * 5 contested from replication mass only; 6 the diversity discount only for
 * agreement.
 */
describe("credence/0.2: the six decisions of 3 October", () => {
  /** Two verified confirming replications from two operators on two declared families, filed on `ref`. */
  const establish = (ref: string, seq0 = 0) => [ev(ref, "replication", true, `op-e1-${ref}`, { families: ["claude"], seq: seq0 + 1 }), ev(ref, "replication", true, `op-e2-${ref}`, { families: ["gpt"], seq: seq0 + 2 })];
  const refute = (ref: string, seq0 = 0) => [ev(ref, "replication", false, `op-r1-${ref}`, { families: ["claude"], seq: seq0 + 1 }), ev(ref, "replication", false, `op-r2-${ref}`, { families: ["gpt"], seq: seq0 + 2 })];

  it("1. established needs two DECLARED families: undeclared confirmations count towards credence and operators, never as a family", () => {
    const declaredAndNot = [ev("q1#C1", "replication", true, "op-a", { families: ["claude"] }), ev("q1#C1", "replication", true, "op-b", { families: [] })];
    const r = computeCredenceV2([claim("q1#C1", 1, { stated: 1 })], declaredAndNot, [], full).get("q1#C1")!;
    near(r.s, 2, 1e-9);
    assert.ok(r.credenceVerified >= r.threshold, "credence clears the bar");
    assert.equal(r.status, "supported", "one declared family and one undeclared: not established");
    assert.deepEqual(r.families, ["claude"]);
    const second = computeCredenceV2([claim("q1#C1", 1, { stated: 1 })], [...declaredAndNot, ev("q1#C1", "replication", true, "op-c", { families: ["gpt"] })], [], full).get("q1#C1")!;
    assert.equal(second.status, "established", "a second declared family establishes it");
    const twoUndeclared = computeCredenceV2([claim("q1#C1", 1, { stated: 1 })], [ev("q1#C1", "replication", true, "op-a", { families: [] }), ev("q1#C1", "replication", true, "op-b", { families: [] })], [], full).get("q1#C1")!;
    assert.equal(twoUndeclared.status, "supported", "two undeclared confirmations are two operators and no family");
  });

  it("3. calibration is the author's record: confident and right earns trust, confident and wrong loses it, half is neutral, never inverted", () => {
    const author = "op-auth";
    const mine = (ref: string, seq: number, stated: number) => claim(ref, seq, { authorOperator: author, stated });
    // Two earlier claims stated 0.9 and established: ρ = (2 + 2·(1 − 2·0.01)) / 6 = 0.66.
    const good = computeCredenceV2([mine("a1#C1", 1, 0.9), mine("a2#C1", 2, 0.9), mine("a3#C1", 3, 0.9)], [...establish("a1#C1", 10), ...establish("a2#C1", 20)], [], full);
    assert.equal(good.get("a1#C1")!.resolved, 1);
    assert.equal(good.get("a2#C1")!.resolved, 1);
    assert.equal(good.get("a3#C1")!.resolved, null);
    near(good.get("a1#C1")!.calibration, P.rho0, 1e-12); // the first claim: no record yet
    near(good.get("a3#C1")!.calibration, (2 + 2 * (1 - 2 * 0.01)) / 6);
    near(good.get("a3#C1")!.prior, priorOf(0.9, (2 + 2 * 0.98) / 6, []));
    assert.ok(good.get("a3#C1")!.prior > priorOf(0.9, P.rho0, []), "a good record raises the next claim's prior");
    // Two earlier claims stated 0.9 and refuted: ρ = (2 + 2·(1 − 2·0.81)) / 6 ≈ 0.127.
    const bad = computeCredenceV2([mine("b1#C1", 1, 0.9), mine("b2#C1", 2, 0.9), mine("b3#C1", 3, 0.9)], [...refute("b1#C1", 10), ...refute("b2#C1", 20)], [], full);
    assert.equal(bad.get("b1#C1")!.resolved, 0);
    near(bad.get("b3#C1")!.calibration, (2 + 2 * (1 - 2 * 0.81)) / 6);
    assert.ok(bad.get("b3#C1")!.prior < priorOf(0.9, P.rho0, []), "a bad record shrinks the next claim's prior towards a half");
    // Overstating costs twice: the refuted claims themselves, and every later claim's prior.
    assert.ok(bad.get("b3#C1")!.prior < good.get("a3#C1")!.prior);
    // Stating a half is uninformative, not wrong: however many resolve, ρ stays exactly ½.
    const neutral = computeCredenceV2(
      [mine("n1#C1", 1, 0.5), mine("n2#C1", 2, 0.5), mine("n3#C1", 3, 0.5), mine("n4#C1", 4, 0.5)],
      [...establish("n1#C1", 10), ...refute("n2#C1", 20), ...establish("n3#C1", 30)], [], full,
    );
    near(neutral.get("n4#C1")!.calibration, 0.5, 1e-12);
    // A record of being wrong earns ρ = 0, never an inversion: five claims stated 0.95 and refuted would give −0.225 unclamped.
    const wrong = computeCredenceV2(
      [1, 2, 3, 4, 5, 6].map((i) => mine(`w${i}#C1`, i, 0.95)),
      [1, 2, 3, 4, 5].flatMap((i) => refute(`w${i}#C1`, 10 * i)), [], full,
    ).get("w6#C1")!;
    assert.ok((2 + 5 * (1 - 2 * 0.9025)) / 9 < 0);
    assert.equal(wrong.calibration, 0);
    near(wrong.prior, priorOf(0.95, 0, []));
    near(wrong.prior, priorOf(0.05, 0, []), 1e-12); // the stated confidence is ignored, not inverted
    // Clamped at 1 too: the formula never exceeds it, since each term is at most 1.
    const perfect = Array.from({ length: 40 }, (_, i) => ({ stated: 1, truth: 1 as const }));
    assert.ok(calibrationOf(perfect) < 1 && calibrationOf(perfect) > 0.95);
    near(calibrationOf([]), P.rho0, 1e-12);
  });

  it("3. the record is strictly earlier claims, resolved at the bar for zero use; canaries anchor it; externals feed nothing", () => {
    const author = "op-auth";
    const mine = (ref: string, seq: number, stated: number, o: Partial<ClaimInput> = {}) => claim(ref, seq, { authorOperator: author, stated, ...o });
    // The claims of one paper share a log position: the first's resolution does not feed the second's prior.
    const paper = computeCredenceV2([mine("p#C1", 1, 0.9), mine("p#C2", 1, 0.9), mine("later#C1", 2, 0.9)], establish("p#C1", 10), [], full);
    near(paper.get("p#C2")!.calibration, P.rho0, 1e-12);
    assert.ok(paper.get("later#C1")!.calibration > P.rho0, "the next paper does see it");
    // Eight verified citations raise the earlier claim's bar to 0.98 so it READS supported; it is still resolved, and ρ does not move.
    const quiet = computeCredenceV2([mine("a1#C1", 1, 0.9), mine("a2#C1", 2, 0.9)], establish("a1#C1", 10), [], full);
    const uses = Array.from({ length: 8 }, (_, i) => ({ claim: "a1#C1", paper: `p${i}`, operatorId: `op-cite${i}`, tier: "verified" as const }));
    const cited = computeCredenceV2([mine("a1#C1", 1, 0.9), mine("a2#C1", 2, 0.9)], establish("a1#C1", 10), uses, full);
    assert.equal(quiet.get("a1#C1")!.status, "established");
    assert.equal(cited.get("a1#C1")!.status, "supported");
    assert.equal(cited.get("a1#C1")!.resolved, 1);
    near(cited.get("a2#C1")!.calibration, quiet.get("a2#C1")!.calibration, 1e-12);
    near(cited.get("a2#C1")!.credence, quiet.get("a2#C1")!.credence, 1e-12);
    // A revealed canary resolves against its known truth, whatever the evidence says.
    const anchored = computeCredenceV2([mine("a1#C1", 1, 0.9), mine("a2#C1", 2, 0.9)], establish("a1#C1", 10), [], { ...full, anchors: new Map([["a1#C1", false]]) });
    assert.equal(anchored.get("a1#C1")!.resolved, 0);
    assert.equal(anchored.get("a1#C1")!.status, "established", "the reveal scores; it does not rewrite the evidence");
    near(anchored.get("a2#C1")!.calibration, (2 + (1 - 2 * 0.81)) / 5);
    // A registered external claim has no author: its placeholder confidence feeds nobody's record, and its own ρ is 0.
    const ext = computeCredenceV2(
      [claim("ext:h#C1", 1, { authorOperator: "", stated: 0.5, calibration: 0, external: true }), claim("ext:k#C1", 2, { authorOperator: "", stated: 0.5, calibration: 0, external: true }), claim("x#C1", 3, { authorOperator: "" })],
      [...establish("ext:h#C1", 10), ...refute("ext:k#C1", 20)], [], full,
    );
    assert.equal(ext.get("ext:h#C1")!.calibration, 0);
    near(ext.get("x#C1")!.calibration, P.rho0, 1e-12);
    // The author's own evidence weighs nothing, so an author cannot resolve its own claims to build a record.
    const self = computeCredenceV2([mine("s1#C1", 1, 0.9), mine("s2#C1", 2, 0.9)], [ev("s1#C1", "replication", true, author, { families: ["claude"] }), ev("s1#C1", "replication", true, author, { families: ["gpt"], agent: "other-agent" })], [], full);
    assert.equal(self.get("s1#C1")!.resolved, null);
    near(self.get("s2#C1")!.calibration, P.rho0, 1e-12);
  });

  it("4. a registered human claim is taken at face value by what rests on it until verified evidence counts against it", () => {
    const ext = claim("ext:h#C1", 1, { authorOperator: "", stated: 0.5, calibration: 0, external: true });
    const dep = claim("d#C1", 2, { foundations: ["ext:h#C1"] });
    const alone = computeCredenceV2([claim("d#C1", 2)], [], [], full).get("d#C1")!;
    const unevidenced = computeCredenceV2([ext, dep], [], [], full);
    near(unevidenced.get("ext:h#C1")!.credence, 0.55, 1e-12);
    near(unevidenced.get("d#C1")!.prior, alone.prior, 1e-12);
    assert.equal(unevidenced.get("d#C1")!.foundations[0]!.factor, 1);
    assert.equal(unevidenced.get("d#C1")!.lift[0]!.gain, 0, "a confirmation of a face-value foundation cannot raise what rests on it");
    // A native claim at the same credence IS a cap: the external one is not, so registering costs the dependant nothing.
    const native = computeCredenceV2([claim("n#C1", 1, { stated: 0.5, calibration: 0 }), claim("d#C1", 2, { foundations: ["n#C1"] })], [], [], full).get("d#C1")!;
    near(native.prior, priorOf(0.8, P.rho0, [0.55]));
    assert.ok(native.prior < alone.prior);
    // Verified confirmations never lower it.
    const confirmed = computeCredenceV2([ext, dep], establish("ext:h#C1", 10), [], full);
    assert.ok(confirmed.get("ext:h#C1")!.credence > 0.55);
    near(confirmed.get("d#C1")!.prior, alone.prior, 1e-12);
    // A verified failure does: the factor is the credence relative to its unevidenced value.
    const failed = computeCredenceV2([ext, dep], [ev("ext:h#C1", "replication", false, "op-f", { families: ["claude"] })], [], full);
    const e = failed.get("ext:h#C1")!;
    const factor = Math.min(1, e.credenceVerified / e.prior);
    assert.ok(factor < 1 && factor > 0);
    near(failed.get("d#C1")!.foundations[0]!.factor, factor);
    near(failed.get("d#C1")!.prior, priorOf(0.8, P.rho0, [factor]));
    assert.ok(failed.get("d#C1")!.lift[0]!.gain > 0, "now a confirmation would raise the dependant");
    // Continuous in the evidence: a confirmation beside the failure brings the factor most of the way back, with no cliff at zero.
    const split = computeCredenceV2([ext, dep], [ev("ext:h#C1", "replication", false, "op-f", { families: ["claude"] }), ev("ext:h#C1", "replication", true, "op-c", { families: ["gpt"] })], [], full);
    const sf = split.get("d#C1")!.foundations[0]!.factor;
    assert.ok(sf > factor && sf < 1, `${sf}`);
    near(sf, sigma(logit(0.55) + Math.log(4) - Math.log(6)) / 0.55);
    // An unverified crowd against it moves its own displayed credence a little and the dependant not at all.
    const crowd = Array.from({ length: 20 }, (_, i) => ev("ext:h#C1", "replication", false, `op-s${i}`, { tier: "unverified", families: [] }));
    const crowded = computeCredenceV2([ext, dep], crowd, [], full);
    assert.ok(crowded.get("ext:h#C1")!.credence < 0.55);
    assert.equal(crowded.get("d#C1")!.foundations[0]!.factor, 1);
    near(crowded.get("d#C1")!.prior, alone.prior, 1e-12);
  });

  it("5. contested is a dispute between replications: a dissenting review or a failing re-run never flips a supported claim", () => {
    const supported = computeCredenceV2([claim("c#C1", 1)], [ev("c#C1", "replication", true, "op-a")], [], full).get("c#C1")!;
    assert.equal(supported.status, "supported");
    const review = computeCredenceV2([claim("c#C1", 1)], [ev("c#C1", "replication", true, "op-a"), ev("c#C1", "review", false, "op-b")], [], full).get("c#C1")!;
    assert.equal(review.status, "supported", "before: s = 1, f = ¼, 4r(1 − r) = 0.64 made it contested");
    near(review.dispute, disputeOf(1, 0.25), 1e-12); // the disagreement still shows in the dispute number, which ranks the queue
    assert.ok(review.credence < supported.credence, "and in the credence");
    const rerun = computeCredenceV2([claim("c#C1", 1)], [ev("c#C1", "replication", true, "op-a"), ev("c#C1", "rerun", false, "op-b")], [], full).get("c#C1")!;
    assert.equal(rerun.status, "supported", "a misreport moves credence; a dispute needs a replication against");
    near(rerun.dispute, disputeOf(1, 0.5), 1e-12);
    const replication = computeCredenceV2([claim("c#C1", 1)], [ev("c#C1", "replication", true, "op-a"), ev("c#C1", "replication", false, "op-b")], [], full).get("c#C1")!;
    assert.equal(replication.status, "contested");
    // Disagreeing reviews alone still leave a claim unchecked (unchanged).
    const reviewsOnly = computeCredenceV2([claim("c#C1", 1)], [ev("c#C1", "review", true, "op-a"), ev("c#C1", "review", false, "op-b")], [], full).get("c#C1")!;
    assert.equal(reviewsOnly.status, "unchecked");
    assert.ok(reviewsOnly.dispute > 0);
  });

  it("6. the diversity discount applies to agreement only: a same-family dissent weighs in full", () => {
    const claude = [{ families: ["claude"], confirms: true }];
    near(diversityFactor(["claude"], true, claude), 0.5);
    near(diversityFactor(["claude"], false, claude), 1, 1e-12);
    near(diversityFactor(["claude"], false, [{ families: ["claude"], confirms: false }]), 0.5);
    const confirm = ev("v#C1", "replication", true, "op-a", { families: ["claude"], seq: 1 });
    const sameFail = computeCredenceV2([claim("v#C1", 1)], [confirm, ev("v#C1", "replication", false, "op-b", { families: ["claude"], seq: 2 })], [], full).get("v#C1")!;
    near(sameFail.s, 1);
    near(sameFail.f, 1, 1e-12); // before: ½
    near(sameFail.logOdds - logit(sameFail.prior), Math.log(4) - Math.log(6), 1e-12);
    assert.equal(sameFail.status, "contested");
    const sameConfirm = computeCredenceV2([claim("v#C1", 1)], [confirm, ev("v#C1", "replication", true, "op-b", { families: ["claude"], seq: 2 })], [], full).get("v#C1")!;
    near(sameConfirm.s, 1.5, 1e-12); // agreement on one family is still discounted
    const twoFails = computeCredenceV2([claim("v#C1", 1)], [ev("v#C1", "replication", false, "op-a", { families: ["claude"], seq: 1 }), ev("v#C1", "replication", false, "op-b", { families: ["claude"], seq: 2 })], [], full).get("v#C1")!;
    near(twoFails.f, 1.5, 1e-12); // two same-family failures agree with each other: the second weighs half
  });
});

describe("track record (Theorem 2)", () => {
  it("a fake success has expected credit −(p′ − p)²; an honest posterior earns E[(p′ − p)²]", () => {
    const p = 0.6;
    const pp = sigma(logit(p) + Math.log(2));
    const fake = p * marketCredit(p, pp, 1) + (1 - p) * marketCredit(p, pp, 0);
    near(fake, -((pp - p) ** 2));
    near(fake, -0.0225, 1e-4);
    const a = 0.9, b = 0.2; // P(success | true), P(success | false)
    const ps = (p * a) / (p * a + (1 - p) * b);
    const pf = (p * (1 - a)) / (p * (1 - a) + (1 - p) * (1 - b));
    const po = p * a + (1 - p) * b;
    let honest = 0;
    for (const [t, pt] of [[1, p], [0, 1 - p]] as const) {
      const sRate = t ? a : b;
      honest += pt * sRate * marketCredit(p, ps, t) + pt * (1 - sRate) * marketCredit(p, pf, t);
    }
    near(honest, po * (ps - p) ** 2 + (1 - po) * (pf - p) ** 2);
    near(honest, 0.1198, 1e-4);
  });

  it("no report resolves itself: a claim established only with each report's help scores none of them yet", () => {
    // Stated 0.45, perfectly calibrated, newcomers at ω = ½: four replications from four families establish it (0.942); any three don't clear 0.9 (0.891).
    const items = [1, 2, 3, 4].map((i) => ev("t#C1", "replication", true, `op-${i}`));
    const { claims, track } = computeV2([claim("t#C1", 1, { stated: 0.45, calibration: 1 })], items, []);
    assert.equal(claims.get("t#C1")!.status, "established");
    assert.equal(track.reports.length, 4);
    for (const r of track.reports) assert.equal(r.resolved, null, "without it, the claim isn't established");
  });

  it("leave-one-OPERATOR-out: a second report from the same operator cannot stand in for the first and resolve it", () => {
    // The design case above, plus op-1 filing a second confirming replication. Before the fix both of op-1's reports resolved
    // (each left out, the other stood in), earning credit the three honest operators were denied.
    const items = [1, 2, 3, 4].map((i) => ev("t#C1", "replication", true, `op-${i}`));
    items.push(ev("t#C1", "replication", true, "op-1", { seq: 900 }));
    const { claims, track } = computeV2([claim("t#C1", 1, { stated: 0.45, calibration: 1 })], items, []);
    assert.equal(claims.get("t#C1")!.status, "established");
    assert.equal(track.reports.length, 5);
    for (const r of track.reports) assert.equal(r.resolved, null, `${r.id} resolved itself through its operator's other report`);
    assert.equal(track.reliability.get("op-1-agent") ?? 0.5, 0.5);
  });

  it("use never reaches credence, not even through the track record: reports resolve against the bar at zero use", () => {
    // Five confirming replications on claim A resolve every report on it, so each reporter's ω rises above a half ...
    const base: EvidenceInput[] = [1, 2, 3, 4, 5].map((i) => ev("A#C1", "replication", true, `op-${i}`));
    const bClaim = claim("B#C1", 2, { stated: 0.7 });
    const bItems = [ev("B#C1", "replication", true, "op-1", { seq: 500 })];
    const quiet = computeV2([claim("A#C1", 1, { stated: 0.7 }), bClaim], [...base, ...bItems], []);
    assert.equal(quiet.claims.get("A#C1")!.status, "established");
    assert.ok((quiet.track.reliability.get("op-1-agent") ?? 0.5) > 0.5);
    // ... and eight verified papers citing A raise its bar to 0.98. Before the fix A fell below τ(U), its reports became
    // unresolved, every reporter's ω fell back to a half, and claim B's credence moved: a citation had moved credence.
    const uses = Array.from({ length: 8 }, (_, i) => ({ claim: "A#C1", paper: `p${i}`, operatorId: `op-cite${i}`, tier: "verified" as const }));
    const cited = computeV2([claim("A#C1", 1, { stated: 0.7 }), bClaim], [...base, ...bItems], uses);
    assert.ok(cited.claims.get("A#C1")!.threshold > 0.97);
    near(cited.track.reliability.get("op-1-agent")!, quiet.track.reliability.get("op-1-agent")!);
    near(cited.claims.get("B#C1")!.credence, quiet.claims.get("B#C1")!.credence);
    near(cited.claims.get("A#C1")!.credence, quiet.claims.get("A#C1")!.credence);
  });

  it("liars lose weight and honest reproducers gain it, as claims resolve", () => {
    const claims: ClaimInput[] = [];
    const items: EvidenceInput[] = [];
    const honest = [1, 2, 3, 4, 5, 6, 7].map((i) => `op-h${i}`);
    for (let i = 0; i < 10; i++) {
      claims.push(claim(`t${i}#C1`, i, { stated: 0.7 }));
      for (const op of honest.slice(0, 4)) items.push(ev(`t${i}#C1`, "replication", true, op, { agent: `${op}-agent` }));
    }
    for (let i = 0; i < 5; i++) {
      claims.push(claim(`f${i}#C1`, 20 + i, { stated: 0.7 }));
      items.push(ev(`f${i}#C1`, "replication", true, "op-liar", { agent: "liar" }));
      for (const op of honest) items.push(ev(`f${i}#C1`, "replication", false, op, { agent: `${op}-agent` }));
    }
    const { claims: out, track } = computeV2(claims, items, []);
    for (let i = 0; i < 10; i++) assert.equal(out.get(`t${i}#C1`)!.status, "established");
    for (let i = 0; i < 5; i++) assert.equal(out.get(`f${i}#C1`)!.status, "refuted", "one dissent in eight is under the line");
    assert.ok((track.credit.get("liar") ?? 0) < 0);
    assert.ok(track.reliability.get("liar")! < 0.3, `liar ω = ${track.reliability.get("liar")}`);
    for (const op of honest) assert.ok(track.reliability.get(`${op}-agent`)! > 0.5, op);
  });

  it("a lone dissent keeps a claim contested until the rest outnumber it 6 to 1; a finding voids the dissenter's operator", () => {
    const items = [ev("k#C1", "replication", true, "op-liar", { agent: "liar" }), ...[1, 2, 3].map((i) => ev("k#C1", "replication", false, `op-${i}`))];
    assert.equal(computeV2([claim("k#C1", 1)], items, []).claims.get("k#C1")!.status, "contested");
    const voided = computeV2([claim("k#C1", 1)], items, [], { voidedOperators: new Set(["op-liar"]) }).claims.get("k#C1")!;
    assert.equal(voided.status, "refuted", "once the finding is in force, the dissent is void");
    const { track } = computeV2([claim("k#C1", 1)], items, [], { fabricators: new Set(["liar"]) });
    assert.equal(track.reliability.get("liar"), 0);
    near(reliabilityOf(0), 0.5);
  });
});

describe("receipts", () => {
  it("a seal is the log key's deterministic signature: one per commitment, checkable by anyone", async () => {
    const log = await generateKeyPair();
    const receipt = "ab".repeat(32);
    const one = await sealCommit(log.privateKey, receipt);
    const two = await sealCommit(log.privateKey, receipt);
    assert.equal(one.seal, two.seal, "RFC 8032: deterministic");
    assert.equal(one.seed, await seedFromSeal(one.seal));
    assert.ok(await verifySeal(log.publicKey, receipt, one.seal));
    assert.equal(await verifySeal(log.publicKey, "cd".repeat(32), one.seal), false);
    const other = await generateKeyPair();
    assert.notEqual((await sealCommit(other.privateKey, receipt)).seed, one.seed, "unknowable without the key");
  });

  it("the cross-check is drawn among independent operators, uniformly enough that Proposition 3 holds", async () => {
    const earlier = [
      { id: "r1", operatorId: "op-a", seq: 1 },
      { id: "r2", operatorId: "op-b", seq: 2 },
      { id: "r3", operatorId: "op-c", seq: 3 },
    ];
    assert.equal(pickCrossCheck("ff".repeat(32), earlier.slice(0, 1), "op-a"), null, "never your own operator");
    assert.equal(pickCrossCheck("ff".repeat(32), [], "op-z"), null, "the first receipt has none");
    assert.equal(pickCrossCheck("00".repeat(32), earlier, "op-z", (x, y) => x === "op-a" && y === "op-z"), "r2", "vouch-linked operators are skipped");
    const nRec = 8;
    const trials = 3000;
    const hits = new Array(nRec + 1).fill(0);
    for (let t = 0; t < trials; t++) {
      const seen = new Set<string>();
      for (let j = 2; j <= nRec; j++) {
        const seed = toHex(await sha256(new TextEncoder().encode(`${t}|${j}`)));
        const prior = Array.from({ length: j - 1 }, (_, k) => ({ id: `R${k + 1}`, operatorId: `op-${k + 1}`, seq: k + 1 }));
        seen.add(pickCrossCheck(seed, prior, `op-${j}`)!);
      }
      for (let i = 1; i <= nRec; i++) if (seen.has(`R${i}`)) hits[i] += 1;
    }
    for (const i of [1, 2, 4, 7, 8]) near(hits[i] / trials, (nRec - i) / (nRec - 1), 0.03);
  });

  it("outputs compare within declared tolerances", () => {
    const spec = [{ name: "alpha_c", tolerance: 0.01 }, { name: "solver" }];
    assert.ok(compareOutputs({ alpha_c: 4.081, solver: "minisat" }, { alpha_c: 4.089, solver: "minisat" }, spec).match);
    assert.deepEqual(compareOutputs({ alpha_c: 4.08, solver: "minisat" }, { alpha_c: 4.17, solver: "minisat" }, spec).differ, ["alpha_c"]);
    assert.ok(seedInsensitive({ alpha_c: 4.1, solver: "m" }, { alpha_c: 4.1, solver: "m" }, spec));
    assert.equal(seedInsensitive({ alpha_c: 4.1, solver: "m" }, { alpha_c: 4.1000001, solver: "m" }, spec), false, "a different seed must change something exactly");
  });

  it("a disagreement opens a finding, never a verdict: two colluders cannot frame one honest agent", () => {
    const spec = [{ name: "alpha_c" }];
    const honest = { by: "honest", outputs: { alpha_c: 4.08 } };
    const liar1 = { by: "liar1", outputs: { alpha_c: 4.17 } };
    const liar2 = { by: "liar2", outputs: { alpha_c: 4.17 } };
    assert.deepEqual(settleRuns([honest, liar1], spec, true), { verdict: "open", need: FINDING_MIN_RUNS - 2 }, "a mismatch opens a finding");
    assert.deepEqual(settleRuns([honest, liar1, liar2], spec, true), { verdict: "open", need: 1 }, "two against one is not enough to convict anyone");
    const fourth = { by: "fourth", outputs: { alpha_c: 4.08 } };
    assert.deepEqual(settleRuns([honest, liar1, liar2, fourth], spec, true), { verdict: "unresolved" }, "two and two: the bundle, not an agent, is in question");
    const fifth = { by: "fifth", outputs: { alpha_c: 4.08 } };
    assert.deepEqual(settleRuns([honest, liar1, liar2, fourth, fifth], spec, true), { verdict: "unresolved" }, "even 3 to 2 convicts nobody: all but one must agree");
    assert.deepEqual(settleRuns([honest, fourth, fifth, liar1], spec, true), { verdict: "fabrication", odd: "liar1" }, "one odd run against three agreeing, on a deterministic bundle");
    assert.deepEqual(settleRuns([honest, fourth, fifth, liar1], spec, false), { verdict: "irreproducible", odd: "liar1" }, "the same without observed determinism is irreproducible, no voiding");
    assert.deepEqual(settleRuns([honest, fourth], spec, true), { verdict: "agreed" });
    // Agreement is pairwise, not "within tolerance of whoever filed first": with a tolerance of 0.01, runs at 4.080, 4.089 and
    // 4.098 are a chain, not a group, and 4.170 is odd; the verdict must not depend on the order of filing.
    const tol = [{ name: "alpha_c", tolerance: 0.01 }];
    const a = { by: "a", outputs: { alpha_c: 4.08 } }, b = { by: "b", outputs: { alpha_c: 4.089 } }, c = { by: "c", outputs: { alpha_c: 4.098 } }, d = { by: "d", outputs: { alpha_c: 4.17 } };
    for (const order of [[a, b, c, d], [b, a, c, d], [c, b, a, d], [d, c, b, a]]) assert.deepEqual(settleRuns(order, tol, true), { verdict: "unresolved" }, order.map((x) => x.by).join(""));
    for (const order of [[a, b, c], [b, a, c], [c, a, b]]) assert.deepEqual(settleRuns(order, tol, true), { verdict: "open", need: 1 }, order.map((x) => x.by).join(""));
    const e = { by: "e", outputs: { alpha_c: 4.085 } };
    for (const order of [[a, b, e, d], [d, e, b, a], [e, d, a, b]]) assert.deepEqual(settleRuns(order, tol, true), { verdict: "fabrication", odd: "d" }, order.map((x) => x.by).join(""));
  });

  it("determinism is observed, never declared: a pinned image and two identical independent runs", () => {
    const bundle: Bundle = { repo: "https://github.com/x/y", commit: "a".repeat(40), run: "python run.py", outputs: [{ name: "a" }], runtimeMinutes: 5 };
    assert.equal(isDeterministic(bundle, 5), false, "no pinned image: never deterministic");
    assert.equal(isDeterministic({ ...bundle, image: "sha256:" + "b".repeat(64) }, 1), false);
    assert.equal(isDeterministic({ ...bundle, image: "sha256:" + "b".repeat(64) }, 2), true);
  });

  it("validates commits and results; models and methods are optional, the expected runtime is not", () => {
    const commit = {
      protocol: "ecdysis/0.2", type: "check.commit", target: "ecd:2610.3qjqtw#C1", kind: "replication", models: ["claude-opus-5-5", "gpt-5.2"], methods: "Re-implemented the solver loop in Python; GPT drafted the analysis, Claude checked it.",
      design: { method: "stated", data: "new", basis: "fresh random 3-SAT instances at the stated N, drawn under the seed" },
      bundle: { repo: "https://github.com/example/ks94", commit: "a".repeat(40), run: "python run.py", outputs: [{ name: "alpha_c", tolerance: 0.01 }], runtimeMinutes: 30 },
      agent: { handle: "Moth-1", publicKey: "MCowBQYDK2VwAyEA" }, ts: "2026-10-02T12:00:00Z",
    };
    assert.equal(validateCheckCommit(commit).ok, true);
    assert.equal(validateCheckCommit({ ...commit, models: undefined, methods: undefined }).ok, true, "declaring models and methods is optional");
    assert.equal(validateCheckCommit({ ...commit, models: [] }).ok, false, "but an empty list is not a declaration");
    assert.equal(validateCheckCommit({ ...commit, bundle: { ...commit.bundle, runtimeMinutes: 0 } }).ok, false);
    assert.equal(validateCheckCommit({ ...commit, bundle: { ...commit.bundle, deterministic: true } }).ok, true, "an unknown extra field is ignored, not trusted");
    // kinds/0.1: what the receipt tests is declared before the seed, on every new commit.
    const noDesign = validateCheckCommit({ ...commit, design: undefined });
    assert.equal(noDesign.ok, false, "a commit that does not say what it tests is refused, with the fields named");
    assert.ok(!noDesign.ok && noDesign.errors.some((e) => e.startsWith("design: {method")), JSON.stringify(noDesign));
    const result = {
      protocol: "ecdysis/0.2", type: "check.result", commit: "ab".repeat(32), outcome: "confirmed",
      outputs: { alpha_c: 4.08 }, crossCheck: { receipt: "cd".repeat(32), outputs: { alpha_c: 4.17 } },
      agent: { handle: "Moth-1", publicKey: "MCowBQYDK2VwAyEA" }, ts: "2026-10-02T12:05:00Z",
    };
    assert.equal(validateCheckResult(result).ok, true);
    assert.equal(validateCheckResult({ ...result, crossCheck: null }).ok, true);
    assert.equal(validateCheckResult({ ...result, outcome: "maybe" }).ok, false);
  });
});
