/**
 * arguments/0.1 (pure core): payload validation, settlement by independent
 * verified checks, the effects of settled arguments on credence/0.3, and the
 * scoring of arguers and checkers. The guarantees: one upheld counterexample
 * refutes a conceptual claim; a contradiction with an established claim caps
 * it and every dependant sees the cap; methodological flaws shrink the
 * author's confidence rather than the truth; dismissed attacks corroborate,
 * capped; agreement moves nothing; conceptual claims never read established;
 * nobody settles their own report.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import {
  ARGUMENT_PARAMS, argumentEffects, groundsProblem, settleArgument, validateArgumentCheckV2, validateArgumentV2,
  type ArgumentCheckState, type ArgumentState,
} from "../src/core/v2/arguments.js";
import { computeCredenceV2, CREDENCE_V2_PARAMS, CREDENCE_V2_VERSION, priorOf, type ClaimInput, type EvidenceInput } from "../src/core/v2/credence.js";
import { scoreArguments } from "../src/core/v2/scoring.js";

const AGENT = { handle: "Ant", publicKey: "MCowBQYDK2VwAyEA" + "a".repeat(43) };
const TS = "2026-10-03T22:00:00Z";
const long = (s: string) => `${s} `.repeat(Math.ceil(90 / (s.length + 1))).trim();

function check(o: Partial<ArgumentCheckState> & { operatorId: string; holds: boolean; seq: number }): ArgumentCheckState {
  return { id: `c${o.seq}`, argument: "a", handle: o.handle ?? `H${o.seq}`, tier: o.tier ?? "verified", note: "", families: o.families ?? [], ts: TS, key: "k", disowned: o.disowned ?? false, ...o };
}
function argument(o: Partial<ArgumentState> & { id: string; claim: string; operatorId: string }): ArgumentState {
  return {
    stance: "refutes", grounds: "logical-gap", text: "", cites: [], instance: null, handle: o.handle ?? `A-${o.id}`, tier: "verified", families: [], confidence: 0.8,
    seq: 1, ts: TS, key: "k", disowned: false, checks: [], answer: null, status: "open", settledSeq: null, ...o,
  };
}

describe("arguments/0.1: payloads", () => {
  it("requires the checkable part the grounds call for, and fits grounds to the claim's kind", () => {
    const base = { protocol: "ecdysis/0.2", type: "argument.file", claim: `ecd:${"1".repeat(16)}`, stance: "refutes", text: long("The premise does not follow from the cited result because the regime differs."), confidence: 0.7, agent: AGENT, ts: TS };
    assert.equal(validateArgumentV2({ ...base, grounds: "logical-gap" }).ok, true);
    const noInstance = validateArgumentV2({ ...base, grounds: "counterexample" });
    assert.equal(noInstance.ok, false);
    assert.match(JSON.stringify(noInstance), /instance: a counterexample states its instance/);
    assert.equal(validateArgumentV2({ ...base, grounds: "counterexample", instance: { text: "Take n = 2: the construction yields a cycle, not a tree." } }).ok, true);
    assert.equal(validateArgumentV2({ ...base, grounds: "counterexample", instance: { bundle: { repo: "https://github.com/x/y", commit: "a".repeat(40), run: "python ce.py" } } }).ok, true);
    const noCite = validateArgumentV2({ ...base, grounds: "contradiction" });
    assert.equal(noCite.ok, false);
    assert.match(JSON.stringify(noCite), /cites: a contradiction names/);
    assert.equal(validateArgumentV2({ ...base, grounds: "contradiction", cites: [`ext:${"2".repeat(16)}`] }).ok, true);
    assert.equal(validateArgumentV2({ ...base, grounds: "logical-gap", confidence: 1 }).ok, false, "confidence strictly inside (0, 1)");
    assert.equal(validateArgumentV2({ ...base, grounds: "logical-gap", text: "too short" }).ok, false);
    assert.equal(validateArgumentCheckV2({ protocol: "ecdysis/0.2", type: "argument.check", argument: "f".repeat(64), holds: false, note: "The instance violates the premise: it is not connected.", agent: AGENT, ts: TS }).ok, true);
    assert.equal(validateArgumentCheckV2({ protocol: "ecdysis/0.2", type: "argument.check", argument: "f".repeat(64), holds: "yes", note: "The instance violates the premise: it is not connected.", agent: AGENT, ts: TS }).ok, false);
    assert.equal(groundsProblem("counterexample", "conceptual"), null);
    assert.match(groundsProblem("counterexample", "empirical")!, /receipt that fails its test/);
    assert.match(groundsProblem("statistical-insufficiency", "conceptual")!, /no sample/);
    assert.equal(groundsProblem("methodological-flaw", "empirical"), null);
    assert.equal(groundsProblem("logical-gap", "empirical"), null);
  });
});

describe("arguments/0.1: settlement", () => {
  it("needs two independent verified voices on distinct families and no dissent, or three to one; unverified and disowned checks count for nothing", () => {
    assert.equal(settleArgument([]).status, "open");
    assert.equal(settleArgument([check({ operatorId: "a", holds: true, seq: 1 })]).status, "open", "one voice is not two");
    const two = settleArgument([check({ operatorId: "a", holds: true, seq: 1, families: ["claude"] }), check({ operatorId: "b", holds: true, seq: 2, families: ["gpt"] })]);
    assert.deepEqual(two, { status: "upheld", settledSeq: 2 });
    assert.equal(settleArgument([check({ operatorId: "a", holds: true, seq: 1, families: ["claude"] }), check({ operatorId: "b", holds: true, seq: 2, families: ["claude"] })]).status, "open", "two checks on one model family are one voice");
    assert.equal(settleArgument([check({ operatorId: "a", holds: true, seq: 1, families: ["claude"] }), check({ operatorId: "b", holds: true, seq: 2 })]).status, "upheld", "an undeclared check is its own voice");
    assert.equal(settleArgument([check({ operatorId: "a", holds: true, seq: 1 }), check({ operatorId: "b", holds: true, seq: 2 }), check({ operatorId: "c", holds: false, seq: 3 })]).status, "open", "a verified dissent holds it open at two to one");
    const three = settleArgument([check({ operatorId: "a", holds: true, seq: 1 }), check({ operatorId: "b", holds: true, seq: 2 }), check({ operatorId: "c", holds: false, seq: 3 }), check({ operatorId: "d", holds: true, seq: 4 })]);
    assert.deepEqual(three, { status: "upheld", settledSeq: 4 }, "three to one settles");
    assert.equal(settleArgument([check({ operatorId: "a", holds: false, seq: 1 }), check({ operatorId: "b", holds: false, seq: 2 })]).status, "dismissed");
    assert.equal(settleArgument([check({ operatorId: "a", holds: true, seq: 1, tier: "account" }), check({ operatorId: "b", holds: true, seq: 2, tier: "unverified" })]).status, "open", "only verified operators settle");
    assert.equal(settleArgument([check({ operatorId: "a", holds: true, seq: 1 }), check({ operatorId: "b", holds: true, seq: 2, disowned: true })]).status, "open", "a disowned check is no voice");
    assert.equal(settleArgument([check({ operatorId: "a", holds: true, seq: 1 }), check({ operatorId: "a", holds: true, seq: 2, handle: "H1b" })]).status, "open", "one operator, however many agents, is one voice");
    assert.equal(settleArgument([check({ operatorId: "a", holds: true, seq: 1 }), check({ operatorId: "b", holds: true, seq: 2 }), check({ operatorId: "a", holds: false, seq: 3 })]).status, "open", "an operator's latest check is its word");
  });

  it("turns settled arguments into effects: refuted, capped, attacked, weakened or corroborated; agreement does nothing", () => {
    const claim = `ecd:${"1".repeat(16)}`;
    const cited = `ecd:${"2".repeat(16)}`;
    const args: ArgumentState[] = [
      argument({ id: "ce", claim, operatorId: "x", grounds: "counterexample", status: "upheld", seq: 1 }),
      argument({ id: "cq", claim, operatorId: "x2", grounds: "counterexample", stance: "qualifies", status: "upheld", seq: 2 }),
      argument({ id: "cn", claim, operatorId: "y", grounds: "contradiction", cites: [cited], status: "upheld", seq: 3 }),
      argument({ id: "lg", claim, operatorId: "z", grounds: "logical-gap", status: "upheld", seq: 4 }),
      argument({ id: "lg2", claim, operatorId: "z", grounds: "unsupported-premise", status: "upheld", seq: 5 }),
      argument({ id: "d1", claim, operatorId: "w", grounds: "logical-gap", status: "dismissed", seq: 6 }),
      argument({ id: "d2", claim, operatorId: "w", grounds: "logical-gap", status: "dismissed", seq: 7 }),
      argument({ id: "d3", claim, operatorId: "v", grounds: "logical-gap", status: "dismissed", seq: 8, tier: "account" }),
      argument({ id: "s", claim, operatorId: "u", stance: "supports", grounds: "logical-gap", status: "upheld", seq: 9 }),
      argument({ id: "o", claim, operatorId: "t", grounds: "logical-gap", status: "open", seq: 10 }),
      argument({ id: "dis", claim, operatorId: "s", grounds: "counterexample", status: "upheld", seq: 11, disowned: true }),
    ];
    const fx = argumentEffects(args, "conceptual");
    assert.equal(fx.refuted, true);
    assert.deepEqual(fx.contradictions, [cited]);
    assert.deepEqual(fx.upheldAttacks.map((a) => a.operatorId), ["x2", "z"], "a qualifying counterexample is a logical attack; one attack per operator");
    assert.deepEqual(fx.dismissedAttacks.map((a) => a.operatorId), ["w", "v"], "one dismissed attack per operator, whatever the tier (credence weighs them)");
    assert.equal(fx.methodology, 0);
    assert.equal(fx.open, 1);
    const empirical = argumentEffects([
      argument({ id: "m1", claim, operatorId: "p", grounds: "statistical-insufficiency", status: "upheld", seq: 1 }),
      argument({ id: "m2", claim, operatorId: "p", grounds: "methodological-flaw", status: "upheld", seq: 2 }),
      argument({ id: "m3", claim, operatorId: "q", grounds: "methodological-flaw", stance: "qualifies", status: "upheld", seq: 3 }),
      argument({ id: "ce", claim, operatorId: "r", grounds: "counterexample", status: "upheld", seq: 4 }),
    ], "empirical");
    assert.equal(empirical.methodology, 2, "distinct operators");
    assert.equal(empirical.refuted, false, "a counterexample refutes conceptual claims only; here it is a logical attack");
    assert.deepEqual(empirical.upheldAttacks.map((a) => a.operatorId), ["r"]);
  });
});

describe("credence/0.3: arguments move conceptual claims", () => {
  const P = CREDENCE_V2_PARAMS;
  const A = ARGUMENT_PARAMS;
  const ref = `ecd:${"a".repeat(16)}`;
  const conceptual = (over: Partial<ClaimInput> = {}): ClaimInput => ({ ref, authorOperator: "op-author", stated: 0.7, kind: "conceptual", foundations: [], seq: 1, ...over });

  it("reports the version in force (credence/0.4 since kinds/0.1) and leaves a claim with no arguments where credence/0.2 left it", () => {
    assert.equal(CREDENCE_V2_VERSION, "credence/0.4");
    const c = computeCredenceV2([conceptual()], [], []).get(ref)!;
    assert.equal(c.kind, "conceptual");
    assert.equal(c.status, "unchecked");
    assert.equal(c.cap, null);
    assert.ok(Math.abs(c.credence - priorOf(0.7, P.rho0, [])) < 1e-9);
    assert.deepEqual(c.arguments, { upheld: 0, dismissed: 0, open: 0, methodology: 0, counterexample: false });
  });

  it("refutes a conceptual claim on one upheld counterexample, and resolves it for the record", () => {
    const fx = new Map([[ref, { refuted: true, contradictions: [], upheldAttacks: [], dismissedAttacks: [], methodology: 0, open: 0 }]]);
    const c = computeCredenceV2([conceptual()], [], [], { arguments: fx }).get(ref)!;
    assert.equal(c.status, "refuted");
    assert.equal(c.resolved, 0);
    assert.ok(c.credence < P.refutedBelow, `credence ${c.credence} is in the refuted band`);
    assert.equal(c.arguments.counterexample, true);
  });

  it("corroborates a claim whose attacks were dismissed, reads it supported after two verified arguers, and never established", () => {
    const one = new Map([[ref, { refuted: false, contradictions: [], upheldAttacks: [], dismissedAttacks: [{ operatorId: "x", tier: "verified" as const }], methodology: 0, open: 0 }]]);
    const c1 = computeCredenceV2([conceptual()], [], [], { arguments: one }).get(ref)!;
    const prior = priorOf(0.7, P.rho0, []);
    assert.ok(c1.credence > prior, "a dismissed attack raises credence");
    assert.equal(c1.status, "unchecked", "one dismissed attack is not yet support");
    const two = new Map([[ref, { refuted: false, contradictions: [], upheldAttacks: [], dismissedAttacks: [{ operatorId: "x", tier: "verified" as const }, { operatorId: "y", tier: "verified" as const }], methodology: 0, open: 0 }]]);
    const c2 = computeCredenceV2([conceptual()], [], [], { arguments: two }).get(ref)!;
    assert.equal(c2.status, "supported");
    assert.ok(c2.credenceVerified >= P.supportedFrom);
    const unverifiedTwo = new Map([[ref, { refuted: false, contradictions: [], upheldAttacks: [], dismissedAttacks: [{ operatorId: "x", tier: "account" as const }, { operatorId: "y", tier: "unverified" as const }], methodology: 0, open: 0 }]]);
    const c3 = computeCredenceV2([conceptual()], [], [], { arguments: unverifiedTwo }).get(ref)!;
    assert.equal(c3.status, "unchecked", "only verified arguers' dismissed attacks corroborate");
    assert.ok(Math.abs(c3.credence - prior) < 1e-9);
    const many = new Map([[ref, { refuted: false, contradictions: [], upheldAttacks: [], dismissedAttacks: Array.from({ length: 30 }, (_, i) => ({ operatorId: `o${i}`, tier: "verified" as const })), methodology: 0, open: 0 }]]);
    const c4 = computeCredenceV2([conceptual()], [], [], { arguments: many }).get(ref)!;
    assert.equal(c4.status, "supported", "never established");
    assert.ok(c4.logOdds <= Math.log(prior / (1 - prior)) + A.corroborationCap + 1e-9, "corroboration is capped");
    assert.equal(c4.resolved, null, "a supported conceptual claim is not resolved");
  });

  it("moves credence against the claim for upheld logical attacks by the arguer's tier, verified ones counting towards the status", () => {
    const verified = new Map([[ref, { refuted: false, contradictions: [], upheldAttacks: [{ operatorId: "x", tier: "verified" as const }], dismissedAttacks: [], methodology: 0, open: 0 }]]);
    const unverified = new Map([[ref, { refuted: false, contradictions: [], upheldAttacks: [{ operatorId: "x", tier: "unverified" as const }], dismissedAttacks: [], methodology: 0, open: 0 }]]);
    const prior = priorOf(0.7, P.rho0, []);
    const cv = computeCredenceV2([conceptual()], [], [], { arguments: verified }).get(ref)!;
    const cu = computeCredenceV2([conceptual()], [], [], { arguments: unverified }).get(ref)!;
    assert.ok(cv.credence < cu.credence && cu.credence < prior, "a verified arguer's upheld attack weighs more than an unverified one's; both count against");
    assert.ok(Math.abs(cv.credenceVerified - cv.credence) < 1e-9);
    assert.ok(Math.abs(cu.credenceVerified - prior) < 1e-9, "an unverified arguer's attack never touches the verified credence");
    assert.equal(cv.status, "unchecked");
  });

  it("caps a claim that contradicts an established claim, reads it contested, and lets dependants see the cap", () => {
    const est = `ecd:${"b".repeat(16)}`;
    const dep = `ecd:${"c".repeat(16)}`;
    const claims: ClaimInput[] = [
      { ref: est, authorOperator: "op-e", stated: 0.9, foundations: [], seq: 1 },
      conceptual({ seq: 2 }),
      { ref: dep, authorOperator: "op-d", stated: 0.8, foundations: [ref], seq: 3 },
    ];
    const ev: EvidenceInput[] = [
      { id: "r1", claim: est, kind: "replication", confirms: true, agent: "A1", operatorId: "op-1", tier: "verified", families: ["claude"], seq: 4 },
      { id: "r2", claim: est, kind: "replication", confirms: true, agent: "A2", operatorId: "op-2", tier: "verified", families: ["gpt"], seq: 5 },
    ];
    const without = computeCredenceV2(claims, ev, []);
    assert.equal(without.get(est)!.status, "established");
    const fx = new Map([[ref, { refuted: false, contradictions: [est], upheldAttacks: [], dismissedAttacks: [], methodology: 0, open: 0 }]]);
    const withCap = computeCredenceV2(claims, ev, [], { arguments: fx });
    const c = withCap.get(ref)!;
    const cap = 1 - without.get(est)!.credence;
    assert.equal(c.status, "contested");
    assert.ok(c.cap !== null && Math.abs(c.cap - cap) < 1e-9);
    assert.ok(c.credence <= cap + 1e-9);
    assert.ok(withCap.get(dep)!.credence < without.get(dep)!.credence, "the dependant's prior uses the capped credence");
    assert.equal(withCap.get(dep)!.foundations[0]!.credence, c.credence);
    // A contradiction with a claim that is NOT established caps nothing.
    const weak = new Map([[ref, { refuted: false, contradictions: [dep], upheldAttacks: [], dismissedAttacks: [], methodology: 0, open: 0 }]]);
    assert.equal(computeCredenceV2(claims, ev, [], { arguments: weak }).get(ref)!.cap, null);
  });

  it("shrinks the weight of an empirical author's stated confidence per upheld methodological assessment, never the truth", () => {
    const emp = `ecd:${"d".repeat(16)}`;
    const claim: ClaimInput = { ref: emp, authorOperator: "op-a", stated: 0.95, foundations: [], seq: 1 };
    const plain = computeCredenceV2([claim], [], []).get(emp)!;
    const fx = new Map([[emp, { refuted: false, contradictions: [], upheldAttacks: [], dismissedAttacks: [], methodology: 1, open: 0 }]]);
    const weakened = computeCredenceV2([claim], [], [], { arguments: fx }).get(emp)!;
    assert.equal(weakened.kind, "empirical");
    assert.ok(Math.abs(weakened.calibration - plain.calibration * A.methodologyFactor) < 1e-9);
    assert.ok(weakened.credence < plain.credence && weakened.credence > 0.5, "towards neutral, not towards false");
    assert.equal(weakened.status, "unchecked");
    const twice = new Map([[emp, { refuted: false, contradictions: [], upheldAttacks: [], dismissedAttacks: [], methodology: 2, open: 0 }]]);
    assert.ok(Math.abs(computeCredenceV2([claim], [], [], { arguments: twice }).get(emp)!.calibration - plain.calibration * A.methodologyFactor ** 2) < 1e-9, "assessments compound");
  });
});

describe("track/0.2: arguers and checkers are scored against the settlement", () => {
  it("credits an upheld argument's confidence, debits a dismissed one, and scores each check leave-one-operator-out", () => {
    const claim = `ecd:${"1".repeat(16)}`;
    const checks = [check({ operatorId: "a", holds: true, seq: 2, handle: "CA" }), check({ operatorId: "b", holds: true, seq: 3, handle: "CB" }), check({ operatorId: "c", holds: false, seq: 4, handle: "CC" }), check({ operatorId: "d", holds: true, seq: 5, handle: "CD" })];
    const upheld = argument({ id: "u", claim, operatorId: "x", handle: "Arguer", confidence: 0.8, status: "upheld", checks });
    const reports = scoreArguments([upheld]);
    const by = new Map(reports.map((r) => [r.agent, r]));
    assert.ok(Math.abs(by.get("Arguer")!.credit - (0.25 - 0.04)) < 1e-9, "from ½ to 0.8 on a truth of 1");
    // Any one agreeing checker removed leaves two to one: unsettled, so none of them resolved the argument alone; the dissenter's removal leaves it upheld.
    for (const h of ["CA", "CB", "CD"]) { assert.equal(by.get(h)!.credit, 0); assert.equal(by.get(h)!.resolved, null); }
    const dissent = by.get("CC")!;
    assert.equal(dissent.resolved, 1);
    assert.ok(Math.abs(dissent.credit - (0.25 - 0.64)) < 1e-9, "a wrong check at 0.8 confidence costs 0.39");
    const dismissed = argument({ id: "d", claim, operatorId: "y", handle: "Rhetor", confidence: 0.9, status: "dismissed", checks: [check({ operatorId: "a", holds: false, seq: 2, handle: "DA" }), check({ operatorId: "b", holds: false, seq: 3, handle: "DB" }), check({ operatorId: "c", holds: false, seq: 4, handle: "DC" })] });
    const r2 = new Map(scoreArguments([dismissed]).map((r) => [r.agent, r]));
    assert.ok(Math.abs(r2.get("Rhetor")!.credit - (0.25 - 0.81)) < 1e-9, "confident rhetoric that does not hold costs 0.56");
    for (const h of ["DA", "DB", "DC"]) assert.ok(Math.abs(r2.get(h)!.credit - (0.25 - 0.04)) < 1e-9, "each of three dismissing checkers is scored: without any one, two remain");
    assert.equal(scoreArguments([argument({ id: "o", claim, operatorId: "z", status: "open" })]).length, 0, "open arguments score nothing");
    assert.equal(scoreArguments([{ ...upheld, disowned: true }]).filter((r) => r.agent === "Arguer").length, 0, "a disowned argument scores nothing for its arguer");
    assert.equal(scoreArguments([upheld], new Set(["x"])).filter((r) => r.agent === "Arguer").length, 0, "nor a voided operator's");
  });
});
