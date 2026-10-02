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
  computeCredenceV2,
  disputeOf,
  logit,
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
  id: `e${++n}`, claim: claimRef, kind, confirms, agent: `${op}-agent`, operatorId: op, tier: "verified", family: `fam-${op}`, seq: 100 + n, ...o,
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
    const same = [1, 2, 3].map((i) => ev("m#C1", "replication", true, `op-c${i}`, { family: "claude" }));
    const r = computeCredenceV2([claim("m#C1", 1)], same, [], full).get("m#C1")!;
    near(r.logOdds - logit(r.prior), Math.log(4) * (1 + 0.5 + 0.25));
    near(r.s, 1.75);
    assert.equal(r.status, "supported", "credence is high, but one family never establishes");
    const mixed = computeCredenceV2([claim("m#C1", 1)], [...same, ev("m#C1", "replication", true, "op-g", { family: "gemini" })], [], full).get("m#C1")!;
    assert.deepEqual(mixed.families, ["claude", "gemini"]);
    assert.equal(mixed.status, "established");
    const unknown = computeCredenceV2([claim("m#C1", 1)], [1, 2].map((i) => ev("m#C1", "replication", true, `op-u${i}`, { family: null })), [], full).get("m#C1")!;
    near(unknown.s, 2); // unknown families are not discounted against each other
    assert.equal(unknown.status, "supported", "but unknown counts as one family at most");
  });

  it("modelFamily normalises declared models", () => {
    assert.equal(modelFamily("claude-opus-5-5"), "claude");
    assert.equal(modelFamily("Anthropic/Claude Sonnet 5.5"), "claude");
    assert.equal(modelFamily("gpt-5.2"), "gpt");
    assert.equal(modelFamily("o3-pro"), "gpt");
    assert.equal(modelFamily("Gemini 3 Pro"), "gemini");
    assert.equal(modelFamily("mixtral-8x22b"), "mistral");
    assert.equal(modelFamily("grok-4"), "grok");
    assert.equal(modelFamily(""), null);
    assert.equal(modelFamily(null), null);
  });

  it("resolution needs verified evidence: cheap identities move credence a little and never a status", () => {
    const cheap = [1, 2, 3, 4].map((i) => ev("v#C1", "replication", true, `op-s${i}`, { tier: "unverified" }));
    const r = computeCredenceV2([claim("v#C1", 1)], cheap, [], full).get("v#C1")!;
    near(r.logOdds - logit(r.prior), Math.log(4) * 0.25 * 4);
    assert.equal(r.s, 0, "no resolution mass");
    assert.equal(r.status, "unchecked");
    assert.equal(r.dispute, 0);
    const acct = computeCredenceV2([claim("v#C1", 1)], [ev("v#C1", "replication", true, "op-acc", { tier: "account" })], [], full).get("v#C1")!;
    near(acct.logOdds - logit(acct.prior), Math.log(4) * 0.5);
    assert.equal(acct.status, "unchecked");
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
    const used = computeCredenceV2([claim("u#C1", 1)], [], [1, 2, 3, 4, 5, 6].map((i) => ({ claim: "u#C1", paper: `p${i}`, operatorId: `op-p${i}` }))).get("u#C1")!;
    near(used.credence, base.credence);
    near(used.use, 6);
    assert.ok(used.threshold > base.threshold);
    const self = computeCredenceV2([claim("u#C1", 1)], [], [{ claim: "u#C1", paper: "mine", operatorId: "op-author" }]).get("u#C1")!;
    assert.equal(self.use, 0, "the author's own papers add no use");
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
  });

  it("determinism is observed, never declared: a pinned image and two exact matches", () => {
    const bundle: Bundle = { repo: "https://github.com/x/y", commit: "a".repeat(40), run: "python run.py", outputs: [{ name: "a" }], runtimeMinutes: 5 };
    assert.equal(isDeterministic(bundle, 5), false, "no pinned image: never deterministic");
    assert.equal(isDeterministic({ ...bundle, image: "sha256:" + "b".repeat(64) }, 1), false);
    assert.equal(isDeterministic({ ...bundle, image: "sha256:" + "b".repeat(64) }, 2), true);
  });

  it("validates commits and results; a commit names its model and expected runtime", () => {
    const commit = {
      protocol: "ecdysis/0.2", type: "check.commit", target: "ecd:2610.3qjqtw#C1", kind: "replication", model: "claude-opus-5-5",
      bundle: { repo: "https://github.com/example/ks94", commit: "a".repeat(40), run: "python run.py", outputs: [{ name: "alpha_c", tolerance: 0.01 }], runtimeMinutes: 30 },
      agent: { handle: "Moth-1", publicKey: "MCowBQYDK2VwAyEA" }, ts: "2026-10-02T12:00:00Z",
    };
    assert.equal(validateCheckCommit(commit).ok, true);
    assert.equal(validateCheckCommit({ ...commit, model: undefined }).ok, false, "the model is required");
    assert.equal(validateCheckCommit({ ...commit, bundle: { ...commit.bundle, runtimeMinutes: 0 } }).ok, false);
    assert.equal(validateCheckCommit({ ...commit, bundle: { ...commit.bundle, deterministic: true } }).ok, true, "an unknown extra field is ignored, not trusted");
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
