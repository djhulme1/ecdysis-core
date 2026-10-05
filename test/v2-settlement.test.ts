/**
 * credence/0.5, continuous settlement, adversarially. It is built but not in force under constitution 2.1.0 (SETTLEMENT is
 * "resolution"), so these tests run it explicitly. They show: a report settles as independent work arrives and exactly as
 * today at the bar; nobody settles their own report, by a second agent or as a literature claim's registrant; one colluding
 * operator can settle at most half; unverified identities settle nothing; a dispute unsettles; a canary's truth decides;
 * and the leaderboard and calibration read the settled share.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import type { V2Entry } from "../src/core/v2/flow.js";
import { resolveV2 } from "../src/core/v2/resolve.js";
import { EARNING_PARAMS, marketCredit, settledCredit, type ScoredReport } from "../src/core/v2/scoring.js";
import { calibrationOf, CREDENCE_V2_PARAMS as P, SETTLEMENT, logit } from "../src/core/v2/credence.js";
import { contributionsOf } from "../src/core/v2/leaderboard.js";
import { scriptedLog } from "../scripts/v2-replay-audit.js";

const CLAIM = "ext:5a75a75a75a75a75";
const GENERAL = { general: "construction", basis: "a named benchmark and setup: every run samples the same population" };
const REPORTED = { as: "reported", basis: "the test states the method and the thresholds the paper reports" };
const REPRODUCTION = { method: "stated", data: "new", basis: "the claim's stated method, run afresh on new samples under the seed" };

/** One literature claim registered by Exuvia (op-d), then the receipts given, in order. */
function world(receipts: Array<{ handle: string; outcome: "confirmed" | "failed"; models?: string[] }>, o: { tiers?: Record<string, string>; canary?: boolean } = {}): V2Entry[] {
  const out: V2Entry[] = [];
  let seq = 0;
  const t0 = Date.UTC(2026, 9, 6);
  const push = (type: string, payload: Record<string, unknown>) => { out.push({ seq, ts: new Date(t0 + seq * 60_000).toISOString(), type: type as V2Entry["type"], payload: payload as V2Entry["payload"] }); seq++; };
  const agents: Record<string, [string, string[]]> = {
    Exuvia: ["op-d", ["qwen"]], Imago: ["op-d", ["claude"]], Pupa: ["op-d", ["mistral"]], Teneral: ["op-l", ["gemini"]],
    Xeno: ["op-3", ["gpt"]], Wren: ["op-4", ["mistral"]], Vole: ["op-5", ["grok"]], Yew: ["op-6", ["llama"]], Cheap: ["op-c", ["phi"]],
  };
  for (const op of ["op-d", "op-l", "op-3", "op-4", "op-5", "op-6", "op-c"]) push("operator.tier", { operatorId: op, tier: o.tiers?.[op] ?? "verified", by: "steward", steward: "op-steward" });
  for (const [handle, [op, models]] of Object.entries(agents)) push("agent.register", { handle, operatorId: op, publicKey: `pk-${handle}`, models, constitution: { version: "2.1.0" } });
  push("claim.external", { id: CLAIM, handle: "Exuvia", operatorId: "op-d", source: "arxiv:0000.00000", quote: "the threshold lies near 4.2", test: "a finite-size scaling fit puts it outside 4.1 to 4.3", scope: GENERAL, fidelity: REPORTED });
  let rc = 0;
  for (const r of receipts) {
    const [op, fam] = agents[r.handle]!;
    const id = `r${(++rc).toString(16).padStart(63, "0")}`;
    push("check.commit", { id, target: CLAIM, kind: "replication", design: REPRODUCTION, bundle: `b-${r.handle}-${rc}`, image: true, runtimeMinutes: 5, handle: r.handle, operatorId: op, models: r.models ?? fam, key: `pk-${r.handle}` });
    push("check.seal", { commit: id, seal: "s", seed: rc.toString(16).padStart(64, "0"), crossCheck: null });
    push("check.result", { commit: id, outcome: r.outcome, crossMatch: null, key: `pk-${r.handle}` });
  }
  if (o.canary) push("canary.reveal", { claim: CLAIM, outcome: "refuted", by: "steward", steward: "op-steward" });
  return out;
}

const AS_OF = new Date(Date.UTC(2026, 10, 6));
const report = (log: V2Entry[], agent: string, mode: "resolution" | "continuous") => {
  const r = resolveV2(log, AS_OF, EARNING_PARAMS, mode).scores.track.reports.find((x) => x.agent === agent && x.claim === CLAIM);
  assert.ok(r, `${agent}'s report`);
  return r;
};
const yes = (handle: string, models?: string[]) => ({ handle, outcome: "confirmed" as const, ...(models ? { models } : {}) });
const no = (handle: string) => ({ handle, outcome: "failed" as const });

// A literature claim's prior is ε + (1 − ε)·½ = 0.55; each verified confirmation in the scoring pass adds ln 2.
const L0 = logit(0.55);
const FRAC1 = Math.log(2) / (logit(P.tau0) - L0);

describe("credence/0.5: not in force under constitution 2.1.0", () => {
  it("scores the record by resolution unless asked otherwise, so nothing on the live record moves", () => {
    assert.equal(SETTLEMENT, "resolution");
    const log = scriptedLog();
    const asOf = new Date(Date.UTC(2026, 10, 5));
    const d = resolveV2(log, asOf);
    const r = resolveV2(log, asOf, EARNING_PARAMS, "resolution");
    assert.deepEqual([...d.scores.claims.values()].map((c) => [c.ref, c.credence, c.status, c.calibration]), [...r.scores.claims.values()].map((c) => [c.ref, c.credence, c.status, c.calibration]));
    assert.deepEqual([...d.scores.track.credit], [...r.scores.track.credit]);
    for (const x of d.scores.track.reports) assert.equal(x.settled, x.resolved === null ? 0 : 2 * x.resolved - 1, "under resolution, settled is only ever −1, 0 or 1");
  });
});

describe("credence/0.5: a report settles as independent work arrives", () => {
  it("credits Imago's replication as other operators confirm it, and exactly as today at the bar", () => {
    const steps = [[yes("Imago")], [yes("Imago"), yes("Teneral")], [yes("Imago"), yes("Teneral"), yes("Xeno")], [yes("Imago"), yes("Teneral"), yes("Xeno"), yes("Wren")]];
    const shares = steps.map((s) => report(world(s), "Imago", "continuous").settled!);
    const today = steps.map((s) => report(world(s), "Imago", "resolution").settled!);
    assert.deepEqual(today, [0, 0, 0, 1], "today: nothing until three other operators have confirmed");
    assert.equal(shares[0], 0, "nobody else has replicated: nothing is settled");
    assert.ok(Math.abs(shares[1]! - FRAC1 / 4) < 1e-12, `one other operator on one family: a quarter of the way it has come (${shares[1]})`);
    assert.ok(Math.abs(shares[2]! - 2 * FRAC1) < 1e-12, `two operators, two families: the whole of the way (${shares[2]})`);
    assert.equal(shares[3], 1, "at the bar: settled, as today's rule resolves it");
    const at = steps[3]!;
    assert.equal(report(world(at), "Imago", "continuous").credit, report(world(at), "Imago", "resolution").credit, "the same credit at the bar, to the last bit");
    for (let i = 1; i < shares.length; i++) assert.ok(shares[i]! >= shares[i - 1]!, "agreeing work never lowers it");
  });

  it("scores a dissent that later work contradicts as wrong, in proportion, and a dispute unsettles everyone", () => {
    const log = world([yes("Imago"), yes("Teneral"), yes("Xeno"), yes("Wren"), yes("Vole"), no("Yew")]);
    assert.equal(report(log, "Imago", "continuous").settled, 0, "one failure among five replications: contested, so nobody's report is settled");
    assert.equal(report(log, "Imago", "resolution").resolved, null);
    const yew = report(log, "Yew", "continuous");
    assert.equal(yew.settled, 1, "the failing report is judged against the five confirmations it disagrees with");
    assert.ok(yew.credit < 0);
    assert.equal(yew.credit, report(log, "Yew", "resolution").credit);
    const early = report(world([no("Yew"), yes("Teneral"), yes("Xeno")]), "Yew", "continuous");
    assert.ok(early.settled! > 0 && early.settled! < 1 && early.credit < 0, `partly settled against the dissent: ${early.settled}, credit ${early.credit}`);
  });
});

describe("credence/0.5: nobody settles their own report", () => {
  it("refuses a second agent of the same operator: Pupa's confirmation settles nothing of Imago's", () => {
    const r = report(world([yes("Imago"), yes("Pupa")]), "Imago", "continuous");
    assert.equal(r.settled, 0);
    assert.equal(r.credit, 0);
  });

  it("never counts a literature claim's registrant towards the operators: Imago (Exuvia's operator) settles nothing of Teneral's", () => {
    const r = report(world([yes("Teneral"), yes("Imago")]), "Teneral", "continuous");
    assert.equal(r.settled, 0, "the registrant's operator wrote the test: its replication counts in the sum, never as an operator");
    const withXeno = report(world([yes("Teneral"), yes("Imago"), yes("Xeno")]), "Teneral", "continuous");
    assert.ok(withXeno.settled! > 0 && withXeno.settled! <= 0.25, `one independent operator besides: at most a quarter (${withXeno.settled})`);
  });

  it("caps what one colluding operator can settle at a half, whatever families its receipt declares", () => {
    const one = report(world([yes("Imago"), yes("Teneral")]), "Imago", "continuous");
    const declaresMany = report(world([yes("Imago"), yes("Teneral", ["gemini", "gpt", "grok", "mistral"])]), "Imago", "continuous");
    assert.ok(one.settled! <= 0.25, `one operator, one family: at most a quarter (${one.settled})`);
    assert.ok(declaresMany.settled! <= 0.5, `one operator declaring four families: at most a half (${declaresMany.settled})`);
    assert.ok(declaresMany.settled! > one.settled!, "declared families count, but never past the operator cap");
  });

  it("lets no unverified or account-tier identity settle anything, however many", () => {
    const log = world([yes("Imago"), yes("Cheap"), yes("Teneral")], { tiers: { "op-c": "account", "op-l": "unverified" } });
    assert.equal(report(log, "Imago", "continuous").settled, 0, "only verified operators' replications settle");
  });
});

describe("credence/0.5: what settles, decides", () => {
  it("takes a revealed canary's known truth over any evidence", () => {
    const r = report(world([yes("Imago"), yes("Teneral"), yes("Xeno")], { canary: true }), "Imago", "continuous");
    assert.equal(r.settled, -1);
    assert.equal(r.credit, marketCredit(r.before, r.after, 0));
  });

  it("is exactly today's resolution wherever today's rule resolves, and short of ±1 everywhere else (the scripted record)", () => {
    const log = scriptedLog();
    const asOf = new Date(Date.UTC(2026, 10, 5));
    const c = resolveV2(log, asOf, EARNING_PARAMS, "continuous");
    let partly = 0;
    for (const x of c.scores.track.reports) {
      assert.ok(x.settled! >= -1 && x.settled! <= 1);
      if (x.resolved !== null) assert.equal(x.settled, 2 * x.resolved - 1, `${x.agent} on ${x.claim}`);
      else { assert.ok(Math.abs(x.settled!) < 1, `${x.agent} on ${x.claim}: unresolved, so not fully settled`); if (x.settled !== 0) partly++; }
    }
    assert.ok(partly >= 20, `the reports work has partly settled are credited (${partly})`);
    const r = resolveV2(log, asOf, EARNING_PARAMS, "resolution");
    assert.deepEqual([...c.verifiedByRecord.keys()].sort(), [...r.verifiedByRecord.keys()].sort(), "verification by record keeps the full bar");
    assert.deepEqual([...c.scores.claims.values()].map((x) => x.status), [...r.scores.claims.values()].map((x) => x.status), "no status changes");
  });
});

describe("credence/0.5: the leaderboard and calibration read the settled share", () => {
  it("banks the settled part of a move and keeps the rest at risk; an older report without a share reads its resolution", () => {
    const rep = (settled: number | undefined, resolved: 0 | 1 | null): ScoredReport => ({ id: "x", agent: "Ant", claim: "c", seq: 1, before: 0.5, after: 0.7, resolved, credit: 0, ...(settled === undefined ? {} : { settled }) });
    const [half] = contributionsOf([rep(0.5, null)], () => "op");
    assert.ok(Math.abs(half!.banked - 0.1) < 1e-12 && Math.abs(half!.atRisk - 0.1) < 1e-12);
    const [old] = contributionsOf([rep(undefined, 1)], () => "op");
    assert.equal(old!.settled, 1);
    assert.ok(Math.abs(old!.banked - 0.2) < 1e-12 && old!.atRisk === 0);
    const [open] = contributionsOf([rep(undefined, null)], () => "op");
    assert.ok(open!.settled === 0 && open!.banked === 0 && Math.abs(open!.atRisk - 0.2) < 1e-12);
  });

  it("credits a report the settled share of its market score, and nothing before", () => {
    assert.equal(settledCredit(0.55, 0.71, 1), marketCredit(0.55, 0.71, 1));
    assert.equal(settledCredit(0.55, 0.71, -1), marketCredit(0.55, 0.71, 0));
    assert.equal(settledCredit(0.55, 0.71, 0), 0);
    assert.ok(Math.abs(settledCredit(0.55, 0.71, 0.5) - 0.5 * marketCredit(0.55, 0.71, 1)) < 1e-15);
  });

  it("weighs a calibration record by the settled share, and an unweighted record as before", () => {
    const old = [{ stated: 0.9, truth: 1 as const }, { stated: 0.8, truth: 0 as const }];
    const expected = (P.rhoK * P.rho0 + (1 - 2 * 0.01) + (1 - 2 * 0.64)) / (P.rhoK + 2);
    assert.ok(Math.abs(calibrationOf(old) - expected) < 1e-15);
    assert.ok(Math.abs(calibrationOf([{ stated: 0.9, truth: 1, weight: 0.5 }]) - (P.rhoK * P.rho0 + 0.5 * (1 - 2 * 0.01)) / (P.rhoK + 0.5)) < 1e-15);
    assert.equal(calibrationOf([{ stated: 0.9, truth: 1, weight: 0 }]), P.rho0, "a claim nobody has settled says nothing about its author");
  });
});
