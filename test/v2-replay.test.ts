/**
 * The replay audit (scripts/v2-replay-audit.ts): deterministic, and the
 * committed baseline is what the core computes now. A change that moves a
 * number on the scripted record must update audit/v2-baseline.json
 * deliberately (npm run audit:v2 -- --update) and say why in its commit.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { differencesV2, ref, scoreScripted, scriptedLog, type V2Outputs } from "../scripts/v2-replay-audit.js";

describe("the v2 replay audit", () => {
  it("scores the scripted record identically every time, and the record covers the rules", () => {
    const a = scoreScripted();
    const b = scoreScripted();
    assert.deepEqual(a, b);
    const log = scriptedLog();
    const types = new Set(log.map((e) => e.type));
    for (const t of ["operator.tier", "agent.register", "claim.publish", "claim.external", "claim.amend", "check.commit", "check.seal", "check.result", "check.lapse", "check.attempt", "finding.decide", "finding.reverse", "review.file", "argument.file", "argument.check", "argument.answer", "key.delegate", "key.revoke", "canary.reveal", "hazard.hold", "hazard.release", "content.withhold", "content.restore"]) assert.ok(types.has(t as never), `${t} is exercised`);
    assert.ok(!types.has("paper.publish" as never) && !types.has("operator.vouch" as never) && !types.has("claim.scope" as never) && !types.has("check.describe" as never), "nothing from before the network");
    assert.ok(Object.keys(a.claims).length >= 40);
    assert.equal(a.labels![ref("p1C1")], "p1C1 (Ant)", "an id reads back to its label");
    assert.equal(a.facts["voided"], "op-u3", "the fabrication finding voids its operator");
    assert.equal(a.findings["f2"]?.endsWith("reversed"), true);
    assert.equal(a.facts["rings"], "op-v1~op-v2", "Ant and Bee confirmed each other's claims: a ring");
    assert.equal(a.tiers["op-a1"], "verified", "Fox's operator, verified by a steward (vouching is gone)");
    assert.equal(a.facts["disowned"], "1", "the compromised check key's receipt is disowned");
    assert.equal(a.facts["held"], `${ref("p6C1")},ext:eeeeeeeeeeeeeeee`, "an R1 hold and a steward's withholding are both out of view");
    assert.equal(a.facts["withheld"], "ext:eeeeeeeeeeeeeeee:review", "the withheld claim stays under review; the withdrawn-then-restored claim does not appear");
    // network/0.1: edges are per claim, use per operator, and a ring halves a use.
    assert.equal(a.facts["edges"], "extends:10;method:1");
    assert.match(a.claims[ref("p1C1")]!, / use 2\.750000 /, "Bee (ring-linked, ½), Cat (two claims, once), Emu (1), Jay (unverified, ¼)");
    assert.match(a.claims[ref("p2C1")]!, / use 1\.000000 /);
    // attempts/0.3: an author's own blockers, declared with the claim or filed after, press nobody; another operator's do.
    assert.equal(a.facts["attempts"], `${ref("p1C1")}:data-unavailable:declared:own;${ref("p1C1")}:compute:declared:own;${ref("p2C1")}:data-unavailable;${ref("p1C1")}:code-unavailable:own`);
    assert.equal(a.facts["pressure"], `${ref("p2C1")}:0.500000`, "stakes 1 × (1 − 2^−1) from Cat's attempt; nothing from Ant's own on p1C1, whose stakes are higher");
    // Verification by record: Yak earns the tier against the steward-verified base, Zed against a base that includes Yak; a
    // forecaster with no cross-checked receipt (Sly) and a late herder (Hog) stay where they were.
    assert.equal(a.tiers["op-a3"], "verified", "Yak: verified by the record");
    assert.equal(a.tiers["op-a4"], "verified", "Zed: verified by the record once Yak's receipts weigh one");
    assert.equal(a.tiers["op-s1"], "account", "Sly: five early right reviews and no receipt earn nothing");
    assert.equal(a.tiers["op-h1"], "account", "Hog: five right reviews after the record resolved earn nothing");
    assert.match(a.facts["verifiedByRecord"]!, /^op-a3:\d+\/\d+\/\d+\/\d+@1;op-a4:\d+\/\d+\/\d+\/\d+@2$/);
    assert.equal(a.facts["rounds"], "3", "two rounds earned, a third added nobody");
    assert.equal(a.facts["amendments"], `${ref("p16C3")}:empirical→conceptual:test;ext:2222222222222222:empirical→empirical`, "one correction each stands; a second, and one after evidence, do not");
    assert.match(a.claims[ref("p16C3")]!, /conceptual/);
    assert.equal(a.facts["scopes"], "ext:2222222222222222:registration(2009-04-01..2012-07-31)>amend(2009-04-01..2012-07-31)", "a scope corrected once, before evidence, is history");
    // scope/0.1 and kinds/0.1: a replication test whose data reach part of the period is an extension and moves nothing; a test
    // on later data is an extension; refuted needs two operators besides the registrant's; a contradiction caps only a claim
    // whose scope overlaps.
    assert.equal(a.facts["kinds"], "extension:2;reproduction:71");
    assert.equal(a.facts["demoted"], "ext:1111111111111111:reproduction→extension", "data reaching only part of the period make an extension");
    assert.match(a.claims["ext:1111111111111111"]!, / supported /, "one reproduction in the paper's period; the failures on other data move nothing");
    assert.match(a.claims["ext:2222222222222222"]!, / contested /, "two failures, one of them the registrant's own: contested, not refuted");
    assert.match(a.claims["ext:3333333333333333"]!, / refuted /, "two operators' failing replication tests, neither the registrant's: refuted");
    assert.match(a.claims[ref("p24C1")]!, / established /);
    assert.doesNotMatch(a.claims[ref("p23C1")]!, /cap/, "a later period cannot contradict an earlier one");
    assert.match(a.claims[ref("p25C1")]!, /unchecked .* cap /, "an overlapping one is capped, and its status still reads its replication tests alone");
    assert.match(a.claims[ref("p4C1")]!, / contested /, "one verified operator's failure does not refute");
    assert.equal(a.reliability["Gnu"], "0.500000", "so Gnu's lone confirmation of it is not scored as wrong");
  });

  it("matches the committed baseline (run npm run audit:v2 -- --update to move it deliberately)", () => {
    const was = JSON.parse(readFileSync(new URL("../audit/v2-baseline.json", import.meta.url), "utf8")) as V2Outputs;
    const diffs = differencesV2(was, scoreScripted());
    assert.deepEqual(diffs, [], `the core's numbers moved:\n${diffs.join("\n")}\nIf that is the intent, update audit/v2-baseline.json with the change and say why.`);
  });

  it("names every figure that moves", () => {
    const was: V2Outputs = { claims: { "ecd:0000000000000001": "0.5 · 0.5 · unchecked · use 0 · dispute 0" }, reliability: { Ant: "0.500000" }, tiers: {}, findings: {}, facts: {} };
    const now: V2Outputs = { claims: { "ecd:0000000000000001": "0.6 · 0.6 · supported · use 0 · dispute 0", "ecd:0000000000000002": "x" }, reliability: { Ant: "0.510000" }, tiers: {}, findings: {}, facts: {} };
    assert.deepEqual(differencesV2(was, now), [
      "claims ecd:0000000000000001: 0.5 · 0.5 · unchecked · use 0 · dispute 0 → 0.6 · 0.6 · supported · use 0 · dispute 0",
      "claims ecd:0000000000000002: (absent) → x",
      "reliability Ant: 0.500000 → 0.510000",
    ]);
    assert.deepEqual(differencesV2(now, now), []);
  });
});
