/**
 * Ecdysis v2's core (claude/ecdysis-v2-design.md): credence/0.2, the track
 * record and receipts. Each result the design states is checked here
 * against its own definition, numerically, so the document and the code
 * can't drift apart.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import {
  CREDENCE_V2_PARAMS as P,
  computeCredenceV2,
  disputeOf,
  logit,
  priorOf,
  sigma,
  type ClaimInput,
  type EvidenceInput,
} from "../src/core/v2/credence.js";
import { computeV2, marketCredit, reliabilityOf } from "../src/core/v2/scoring.js";
import {
  compareOutputs,
  pickCrossCheck,
  sealCommit,
  seedFromSeal,
  seedInsensitive,
  settleRuns,
  validateCheckCommit,
  validateCheckResult,
  verifySeal,
} from "../src/core/v2/receipts.js";
import { generateKeyPair } from "../src/core/crypto.js";
import { sha256, toHex } from "../src/core/canonical.js";

const near = (a: number, b: number, eps = 1e-9) => assert.ok(Math.abs(a - b) <= eps, `${a} ≉ ${b}`);

const claim = (ref: string, seq: number, o: Partial<ClaimInput> = {}): ClaimInput => ({
  ref, paper: ref.split("#")[0]!, authorOperator: "op-author", stated: 0.8, foundations: [], seq, ...o,
});
let n = 0;
const ev = (claimRef: string, kind: EvidenceInput["kind"], confirms: boolean, op: string, o: Partial<EvidenceInput> = {}): EvidenceInput => ({
  id: `e${++n}`, claim: claimRef, kind, confirms, agent: `${op}-agent`, operatorId: op, verified: true, seq: 100 + n, ...o,
});
/** Everyone fully reliable, so a check's weight is just independence × verification. */
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

  it("Proposition 1: ∂ℓ(c)/∂ℓ(f) = κ_c(1 − p_f), so the weakest foundation lifts a claim most (0.33 → 0.42 against 0.34)", () => {
    const fs = [0.9, 0.5];
    const q = priorOf(0.8, 0.5, fs);
    near(q, 0.327875, 1e-6);
    const kappa = (q - P.epsilon) / (q * (1 - q));
    for (const [i, f] of fs.entries()) {
      const h = 1e-6;
      const bumped = fs.map((v, j) => (j === i ? sigma(logit(v) + h) : v));
      const numeric = (logit(priorOf(0.8, 0.5, bumped)) - logit(q)) / h;
      near(numeric, kappa * (1 - f), 1e-4);
    }
    const lifted = (i: number) => priorOf(0.8, 0.5, fs.map((v, j) => (j === i ? sigma(logit(v) + Math.log(2)) : v)));
    assert.equal(lifted(1).toFixed(2), "0.42");
    assert.equal(lifted(0).toFixed(2), "0.34");
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

  it("dispute measures disagreement, not evidence: 0 when agreed, 4f for a lone dissenter, contested from a seventh", () => {
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

  it("established needs a confirming replication: re-runs prove honesty, not the effect", () => {
    const reruns = [1, 2, 3, 4, 5, 6].map((i) => ev("r#C1", "rerun", true, `op-r${i}`));
    const onlyReruns = computeCredenceV2([claim("r#C1", 1)], reruns, [], full).get("r#C1")!;
    assert.ok(onlyReruns.credence >= onlyReruns.threshold, "credence clears the bar");
    assert.equal(onlyReruns.status, "supported", "but re-runs alone never establish");
    const withRep = computeCredenceV2([claim("r#C1", 1)], [...reruns, ev("r#C1", "replication", true, "op-rep")], [], full).get("r#C1")!;
    assert.equal(withRep.status, "established");
  });

  it("refuted needs a failed replication and low credence; a refuted foundation makes its dependants contested", () => {
    const r = computeCredenceV2(
      [claim("f#C1", 1), claim("g#C1", 2, { foundations: ["f#C1"] })],
      [ev("f#C1", "replication", false, "op-1"), ev("f#C1", "replication", false, "op-2")], [], full,
    );
    assert.equal(r.get("f#C1")!.status, "refuted");
    assert.equal(r.get("g#C1")!.status, "contested");
  });

  it("one operator, one voice: its own evidence is worth nothing, several items count once, unverified counts half", () => {
    const own = computeCredenceV2([claim("o#C1", 1)], [ev("o#C1", "replication", true, "op-author")], [], full).get("o#C1")!;
    assert.equal(own.s, 0);
    assert.equal(own.status, "unchecked");
    const many = computeCredenceV2([claim("o#C1", 1)], [1, 2, 3].map(() => ev("o#C1", "replication", true, "op-same")), [], full).get("o#C1")!;
    near(many.s, 1);
    const unverified = computeCredenceV2([claim("o#C1", 1)], [ev("o#C1", "replication", true, "op-u", { verified: false })], [], full).get("o#C1")!;
    near(unverified.s, 0.5);
    near(unverified.logOdds - logit(unverified.prior), 0.5 * Math.log(4));
  });

  it("reviews move a little, both ways, and never more than ln 3 together", () => {
    const pro = computeCredenceV2([claim("v#C1", 1)], [1, 2, 3, 4, 5, 6, 7, 8].map((i) => ev("v#C1", "review", true, `op-v${i}`)), [], full).get("v#C1")!;
    near(pro.logOdds - logit(pro.prior), Math.log(3));
    const con = computeCredenceV2([claim("v#C1", 1)], [ev("v#C1", "review", false, "op-v1")], [], full).get("v#C1")!;
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
    // Stated ½, perfectly calibrated: four replications establish it (0.946), any three don't (0.898 < 0.9).
    const items = [1, 2, 3, 4].map((i) => ev("t#C1", "replication", true, `op-${i}`));
    const { claims, track } = computeV2([claim("t#C1", 1, { stated: 0.5, calibration: 1 })], items, []);
    assert.equal(claims.get("t#C1")!.status, "established");
    assert.equal(track.reports.length, 4);
    for (const r of track.reports) assert.equal(r.resolved, null, "without it, the claim isn't established");
  });

  it("liars lose weight and honest reproducers gain it, as claims resolve", () => {
    // Ten true claims, each confirmed by four honest operators; a liar "confirms" five false ones, which seven honest operators then refute.
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

  it("a lone dissent keeps a claim contested until the rest outnumber it 6 to 1: honest disagreement is surfaced, and liars are removed by cross-checks and their record", () => {
    const items = [ev("k#C1", "replication", true, "op-liar", { agent: "liar" }), ...[1, 2, 3].map((i) => ev("k#C1", "replication", false, `op-${i}`))];
    assert.equal(computeV2([claim("k#C1", 1)], items, []).claims.get("k#C1")!.status, "contested");
    const proven = computeV2([claim("k#C1", 1)], items, [], { fabricators: new Set(["liar"]) }).claims.get("k#C1")!;
    assert.equal(proven.status, "refuted", "once its fabrication is proven, the dissent is void");
  });

  it("proven fabrication weighs nothing and sets reliability to 0", () => {
    const items = [ev("z#C1", "replication", true, "op-f", { agent: "faker" })];
    const { claims, track } = computeV2([claim("z#C1", 1)], items, [], { fabricators: new Set(["faker"]) });
    assert.equal(claims.get("z#C1")!.status, "unchecked");
    assert.equal(track.reliability.get("faker"), 0);
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

  it("the cross-check is drawn among independent operators, and is uniform enough that Proposition 3 holds", async () => {
    const earlier = [
      { id: "r1", operatorId: "op-a", seq: 1 },
      { id: "r2", operatorId: "op-b", seq: 2 },
      { id: "r3", operatorId: "op-c", seq: 3 },
    ];
    assert.equal(pickCrossCheck("ff".repeat(32), earlier.slice(0, 1), "op-a"), null, "never your own operator");
    assert.equal(pickCrossCheck("ff".repeat(32), [], "op-z"), null, "the first receipt has none");
    assert.equal(pickCrossCheck("00".repeat(32), earlier, "op-z", (x, y) => x === "op-a" && y === "op-z"), "r2", "vouch-linked operators are skipped");
    // Proposition 3: receipt i of n is re-run with probability (n − i)/(n − 1).
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

  it("outputs compare within declared tolerances; two runs against one prove the odd one wrong", () => {
    const spec = [{ name: "alpha_c", tolerance: 0.01 }, { name: "solver" }];
    assert.ok(compareOutputs({ alpha_c: 4.081, solver: "minisat" }, { alpha_c: 4.089, solver: "minisat" }, spec).match);
    assert.deepEqual(compareOutputs({ alpha_c: 4.08, solver: "minisat" }, { alpha_c: 4.17, solver: "minisat" }, spec).differ, ["alpha_c"]);
    const runs = [
      { by: "claimant", outputs: { alpha_c: 4.17, solver: "minisat" } },
      { by: "checker", outputs: { alpha_c: 4.08, solver: "minisat" } },
      { by: "third", outputs: { alpha_c: 4.081, solver: "minisat" } },
    ];
    assert.deepEqual(settleRuns(runs, spec, false), { verdict: "irreproducible", odd: "claimant" });
    const exact = [{ name: "alpha_c" }, { name: "solver" }];
    assert.deepEqual(settleRuns([runs[0]!, runs[1]!, { by: "third", outputs: { alpha_c: 4.08, solver: "minisat" } }], exact, true), { verdict: "fraud", odd: "claimant" });
    assert.equal(settleRuns(runs.slice(0, 2), spec, true).verdict, "unresolved", "two runs never prove anything");
    assert.ok(seedInsensitive({ alpha_c: 4.1, solver: "m" }, { alpha_c: 4.1, solver: "m" }, spec));
    assert.equal(seedInsensitive({ alpha_c: 4.1, solver: "m" }, { alpha_c: 4.1000001, solver: "m" }, spec), false, "a different seed must change something exactly");
  });

  it("validates commits and results, and refuses tolerances on a deterministic bundle", () => {
    const commit = {
      protocol: "ecdysis/0.2", type: "check.commit", target: "ecd:2610.3qjqtw#C1", kind: "replication",
      bundle: { repo: "https://github.com/example/ks94", commit: "a".repeat(40), run: "python run.py", outputs: [{ name: "alpha_c" }], deterministic: true },
      agent: { handle: "Moth-1", publicKey: "MCowBQYDK2VwAyEA" }, ts: "2026-10-02T12:00:00Z",
    };
    assert.equal(validateCheckCommit(commit).ok, true);
    const bad = { ...commit, bundle: { ...commit.bundle, outputs: [{ name: "alpha_c", tolerance: 0.1 }] } };
    assert.equal(validateCheckCommit(bad).ok, false);
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
