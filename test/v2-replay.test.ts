/**
 * The v2 replay audit (scripts/v2-replay-audit.ts): deterministic, and the
 * committed baseline is what the core computes now. A change that moves a
 * number on the scripted record must update audit/v2-baseline.json
 * deliberately (npm run audit:v2 -- --update) and say why in its commit.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { differencesV2, scoreScripted, scriptedLog, type V2Outputs } from "../scripts/v2-replay-audit.js";

describe("the v2 replay audit", () => {
  it("scores the scripted record identically every time, and the record covers the rules", () => {
    const a = scoreScripted();
    const b = scoreScripted();
    assert.deepEqual(a, b);
    const log = scriptedLog();
    const types = new Set(log.map((e) => e.type));
    for (const t of ["operator.tier", "operator.vouch", "agent.register", "paper.publish", "claim.external", "check.commit", "check.seal", "check.result", "check.lapse", "finding.decide", "finding.reverse", "review.file", "key.delegate", "key.revoke", "canary.reveal", "hazard.hold", "hazard.release"]) assert.ok(types.has(t as never), `${t} is exercised`);
    assert.ok(Object.keys(a.claims).length >= 12);
    assert.equal(a.facts["voided"], "op-u3", "the fabrication finding voids its operator");
    assert.equal(a.findings["f2"]?.endsWith("reversed"), true);
    assert.equal(a.tiers["op-a1"], "verified", "two steward-verified vouches verify an account");
    assert.equal(a.facts["disowned"], "1", "the compromised check key's receipt is disowned");
    assert.equal(a.facts["held"], "ecd:p6#C1,ext:eeeeeeeeeeeeeeee", "an R1 hold and a steward's withholding are both out of view");
    assert.equal(a.facts["withheld"], "ext:eeeeeeeeeeeeeeee:review", "the withheld claim stays under review; the withdrawn-then-restored paper does not appear");
    // Verification by record: Yak earns the tier against the steward-verified base, Zed against a base that includes Yak; a
    // forecaster with no cross-checked receipt (Sly) and a late herder (Hog) stay where they were.
    assert.equal(a.tiers["op-a3"], "verified", "Yak: verified by the record");
    assert.equal(a.tiers["op-a4"], "verified", "Zed: verified by the record once Yak's receipts weigh one");
    assert.equal(a.tiers["op-s1"], "account", "Sly: five early right reviews and no receipt earn nothing");
    assert.equal(a.tiers["op-h1"], "account", "Hog: five right reviews after the record resolved earn nothing");
    assert.match(a.facts["verifiedByRecord"]!, /^op-a3:\d+\/\d+\/\d+\/\d+@1;op-a4:\d+\/\d+\/\d+\/\d+@2$/);
    assert.equal(a.facts["rounds"], "3", "two rounds earned, a third added nobody");
    assert.equal(a.facts["amendments"], "ecd:p16#C3:empirical→conceptual:test", "one correction stands; the second, and one after evidence, do not");
    assert.match(a.claims["ecd:p16#C3"]!, /conceptual/);
  });

  it("matches the committed baseline (run npm run audit:v2 -- --update to move it deliberately)", () => {
    const was = JSON.parse(readFileSync(new URL("../audit/v2-baseline.json", import.meta.url), "utf8")) as V2Outputs;
    const diffs = differencesV2(was, scoreScripted());
    assert.deepEqual(diffs, [], `the core's numbers moved:\n${diffs.join("\n")}\nIf that is the intent, update audit/v2-baseline.json with the change and say why.`);
  });

  it("names every figure that moves", () => {
    const was: V2Outputs = { claims: { "a#C1": "0.5 · 0.5 · unchecked · use 0 · dispute 0" }, reliability: { Ant: "0.500000" }, tiers: {}, findings: {}, facts: {} };
    const now: V2Outputs = { claims: { "a#C1": "0.6 · 0.6 · supported · use 0 · dispute 0", "b#C1": "x" }, reliability: { Ant: "0.510000" }, tiers: {}, findings: {}, facts: {} };
    assert.deepEqual(differencesV2(was, now), [
      "claims a#C1: 0.5 · 0.5 · unchecked · use 0 · dispute 0 → 0.6 · 0.6 · supported · use 0 · dispute 0",
      "claims b#C1: (absent) → x",
      "reliability Ant: 0.500000 → 0.510000",
    ]);
    assert.deepEqual(differencesV2(now, now), []);
  });
});
