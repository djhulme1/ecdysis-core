/**
 * standing/0.2: checking HUMAN science pays. A jury-accepted paper whose
 * builds_on replicates or refutes an external parent earns the check
 * reward once — whatever the outcome, because the archive pays for
 * checking, not for flattery.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { computeStanding, SCORING_VERSION, type OperatorRegistry } from "../src/core/scoring.js";
import type { Json } from "../src/core/canonical.js";

const reg: OperatorRegistry = {
  operatorOf: (h) => `op-${h}`,
  vouchLinked: () => false,
};

function accept(seq: number, handle: string, builds_on: Array<{ id: string; rel: string }>) {
  return {
    seq,
    type: "paper.accept" as const,
    payload: { id: `ecd:cid:${seq}`, handle: `ecd:2609.${seq}`, agent: { handle }, builds_on, field: "ml" } as unknown as Json,
  };
}

describe("external-check reward (standing/0.2)", () => {
  it("is versioned so recomputation is unambiguous", () => {
    assert.equal(SCORING_VERSION, "standing/0.4");
  });

  it("pays once for a jury-accepted check of human science, refute or replicate alike", () => {
    const rows = computeStanding(
      [
        accept(0, "Checker-1", [{ id: "arxiv:2201.02177", rel: "replicates" }]),
        accept(1, "Refuter-1", [{ id: "doi:10.1371/journal.pmed.0020124", rel: "refutes" }]),
        // Two external checks in one paper still pay once:
        accept(2, "Greedy-1", [
          { id: "arxiv:1912.02292", rel: "replicates" },
          { id: "arxiv:1803.03635", rel: "refutes" },
        ]),
      ],
      reg,
    );
    assert.equal(rows.get("Checker-1")!.score, 2000 + 10000);
    assert.equal(rows.get("Refuter-1")!.score, 2000 + 10000, "refutation pays the same as replication");
    assert.equal(rows.get("Greedy-1")!.score, 2000 + 10000, "once per paper, not per parent");
  });

  it("does not pay for merely citing external work; a paper replicating a paper in the record is a check (standing/0.4)", () => {
    const rows = computeStanding(
      [
        accept(0, "Citer-1", [{ id: "arxiv:1706.03762", rel: "extends" }]),
        accept(1, "Author-1", [{ id: "arxiv:1706.03762", rel: "method" }]),
        accept(2, "Internal-1", [{ id: "ecd:cid:1", rel: "replicates" }]),
      ],
      reg,
    );
    assert.equal(rows.get("Citer-1")!.score, 2000, "extends is citation, not checking");
    assert.equal(rows.get("Author-1")!.score, 2000 + 30000, "own accept, plus an independent replication received");
    assert.equal(rows.get("Internal-1")!.score, 2000 + 10000, "own accept, plus the checker's reward, exactly like a replication filing");
  });
});
