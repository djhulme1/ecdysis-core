/**
 * The replay audit (scripts/replay-audit.ts): it must be deterministic, or
 * it would cry wolf on every pull request, and it must name who gains and
 * who loses when a change moves a score. (CI compares the committed
 * baseline itself: npm run audit:replay.)
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { differences, scoreLive, scoreSynthetic, type LiveCorpus } from "../scripts/replay-audit.js";

describe("the replay audit", () => {
  it("scores the scripted society identically every time", async () => {
    const a = await scoreSynthetic();
    const b = await scoreSynthetic();
    assert.deepEqual(a, b);
    assert.ok(Object.keys(a.standing).length >= 10);
    assert.equal(a.generation["P5"], 4, "the deep chain is four steps from human science");
    assert.equal(a.cases!["held-after-R1"], "rejected", "the hold went to the operator key");
    assert.equal(a.cases!["P3-rejected"], "rejected");
    assert.match(String(a.credence["P1#C2"]), /refuted/);
  });

  it("scores the frozen live record by the published rules", () => {
    const corpus = JSON.parse(readFileSync(new URL("../audit/corpus-live.json", import.meta.url), "utf8")) as LiveCorpus;
    const out = scoreLive(corpus);
    assert.ok(Object.keys(out.standing).length >= 1);
    assert.ok(Object.values(out.generation).every((g) => g === null || typeof g === "number"));
  });

  it("names every figure that moves, with the change in standing", () => {
    const was = { standing: { "Ana-1": -59000, "Zed-2": 20000 }, credence: { "P1#C1": "0.9 · use 2 · established" }, generation: { P1: 1 } };
    const now = { standing: { "Ana-1": -19000, "Zed-2": 10000 }, credence: { "P1#C1": "0.9 · use 2 · established" }, generation: { P1: 1, P9: 2 } };
    assert.deepEqual(differences(was, now), [
      "standing Ana-1: -59000 → -19000 (+400.00 standing)",
      "standing Zed-2: 20000 → 10000 (-100.00 standing)",
      "generation P9: (absent) → 2",
    ]);
    assert.deepEqual(differences(now, now), []);
  });
});
