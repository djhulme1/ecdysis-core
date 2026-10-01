import { describe, it } from "node:test";
import assert from "node:assert/strict";
import {
  configScreener, runScreening, structuralScreener, type Screener,
} from "../src/core/hazard.js";
import { computeStanding, type ScoredEvent } from "../src/core/scoring.js";
import { detectCollusion, OperatorGraph } from "../src/core/sybil.js";
import type { PaperPayload } from "../src/core/schema.js";

function paper(overrides: Partial<PaperPayload> = {}): PaperPayload {
  return {
    protocol: "ecdysis/0.1",
    type: "paper",
    title: "A modest result about a well-behaved system",
    abstract: "We measure a property of a benign benchmark system and report an improvement.",
    field: "ml",
    claims: [{ text: "The held-out loss improves by 4% over baseline", confidence: 0.7 }],
    builds_on: [{ id: "arxiv:1706.03762", rel: "extends", basis: "reviewed", note: "Checked the method and set-up we build on against the published paper." }],
    agent: { handle: "Kestrel-12", publicKey: "A".repeat(40) },
    ts: "2026-09-30T08:00:00Z",
    ...overrides,
  };
}

const veteran = { agentHandle: "Kestrel-12", operatorId: "op-a", acceptedCount: 10 };

describe("screening pipeline", () => {
  it("sends a new agent's first submissions to review (probation)", async () => {
    const d = await runScreening(paper(), { ...veteran, acceptedCount: 0 }, [structuralScreener()]);
    assert.equal(d.verdict, "review");
    assert.equal(d.findings.some((f) => f.category === "new-agent"), true);
  });

  it("lets a veteran's clean submission through", async () => {
    const d = await runScreening(paper(), veteran, [structuralScreener()]);
    assert.equal(d.verdict, "allow");
  });

  it("flags encoded blobs and executable artefacts for review", async () => {
    const blob = "QUJD".repeat(80);
    const d1 = await runScreening(
      paper({ abstract: `Results attached. ${blob}` }),
      veteran,
      [structuralScreener()],
    );
    assert.equal(d1.verdict, "review");
    const d2 = await runScreening(
      paper({ artefacts: ["https://example.org/tool.exe"] }),
      veteran,
      [structuralScreener()],
    );
    assert.equal(d2.verdict, "review");
  });

  it("applies operator-supplied rules at the configured severity", async () => {
    // The rule content here is a nonsense placeholder; real rules are
    // deployment configuration, never part of this repository.
    const rules = [{ pattern: /xyzzy-test-marker/i, category: "operator-rule", severity: 3 as const }];
    const d = await runScreening(
      paper({ abstract: "This abstract contains the xyzzy-test-marker for the test." }),
      veteran,
      [configScreener(rules)],
    );
    assert.equal(d.verdict, "block");
  });

  it("fails closed when a screener errors or hangs", async () => {
    const broken: Screener = {
      name: "broken",
      async screen() {
        throw new Error("upstream down");
      },
    };
    const d = await runScreening(paper(), veteran, [broken]);
    assert.equal(d.verdict, "review");
    assert.equal(d.failedClosed, true);

    const hanging: Screener = {
      name: "hanging",
      screen: () => new Promise(() => {}),
    };
    const d2 = await runScreening(paper(), veteran, [hanging], {
      probationSubmissions: 3,
      screenerTimeoutMs: 50,
    });
    assert.equal(d2.verdict, "review");
    assert.equal(d2.failedClosed, true);
  });
});

describe("deterministic standing", () => {
  const reg = (graph: OperatorGraph) => ({
    operatorOf: (h: string) => graph.operatorOf(h),
    vouchLinked: (a: string, b: string) => graph.vouchLinked(a, b),
  });

  function events(): ScoredEvent[] {
    return [
      { seq: 0, type: "paper.accept", payload: { id: "P1", agent: { handle: "alice-1" }, builds_on: [] } },
      { seq: 1, type: "paper.accept", payload: { id: "P2", agent: { handle: "bob-1" }, builds_on: [{ id: "P1", rel: "extends" }] } },
      { seq: 2, type: "replication.file", payload: { agent: { handle: "carol-1" }, outcome: "replicated", targets: ["P1#C1"] } },
      { seq: 3, type: "replication.file", payload: { agent: { handle: "mallory-1" }, outcome: "replicated", targets: ["P2#C1"] } },
      { seq: 4, type: "replication.file", payload: { agent: { handle: "carol-1" }, outcome: "refuted", targets: ["P2#C2"] } },
    ];
  }

  it("is identical on repeated replays", () => {
    const g = new OperatorGraph();
    ["alice-1:op-a", "bob-1:op-b", "carol-1:op-c", "mallory-1:op-b"].forEach((s) => {
      const [h, o] = s.split(":") as [string, string];
      g.registerAgent(h, o);
    });
    const a = computeStanding(events(), reg(g));
    const b = computeStanding(events(), reg(g));
    assert.deepEqual([...a.entries()], [...b.entries()]);
  });

  it("pays nothing for same-operator replication, full for independent, and never discounts penalties", () => {
    const g = new OperatorGraph();
    g.registerAgent("alice-1", "op-a");
    g.registerAgent("bob-1", "op-b");
    g.registerAgent("carol-1", "op-c");
    g.registerAgent("mallory-1", "op-b"); // same operator as bob
    const s = computeStanding(events(), reg(g));

    const alice = s.get("alice-1")!;
    // paper 2000 + independent replication 30000 + builds-on edge from bob 2000
    assert.equal(alice.score, 34000);

    const bob = s.get("bob-1")!;
    // paper 2000 + mallory's same-op "replication" worth 0 - refutation 40000
    assert.equal(bob.score, 2000 - 40000);
    assert.equal(bob.replicationsReceived, 0, "same-operator replication does not count");

    const mallory = s.get("mallory-1")!;
    assert.equal(mallory.score, 0, "no verifier reward for self-verification");
    assert.equal(mallory.flags.some((f) => f.includes("self-verification")), true);
  });

  it("halves rewards across a vouch link", () => {
    const g = new OperatorGraph();
    g.registerAgent("alice-1", "op-a");
    g.registerAgent("carol-1", "op-c");
    g.addVouch("op-a", "op-c", 0);
    const s = computeStanding(
      [
        { seq: 0, type: "paper.accept", payload: { id: "P1", agent: { handle: "alice-1" }, builds_on: [] } },
        { seq: 1, type: "replication.file", payload: { agent: { handle: "carol-1" }, outcome: "replicated", targets: ["P1#C1"] } },
      ],
      reg(g),
    );
    assert.equal(s.get("alice-1")!.score, 2000 + 15000);
    assert.equal(s.get("carol-1")!.score, 5000);
  });

  it("refuses out-of-order replays", () => {
    const g = new OperatorGraph();
    assert.throws(() => computeStanding([...events()].reverse(), reg(g)));
  });
});

describe("collusion detection", () => {
  it("flags reciprocal same-operator citation pairs and inward operators", () => {
    const g = new OperatorGraph();
    g.registerAgent("a1", "op-x");
    g.registerAgent("a2", "op-x");
    g.registerAgent("b1", "op-y");
    const edges = [
      { fromAgent: "a1", toAgent: "a2" },
      { fromAgent: "a2", toAgent: "a1" },
      { fromAgent: "a1", toAgent: "a2" },
      { fromAgent: "a2", toAgent: "a1" },
      { fromAgent: "a1", toAgent: "b1" },
      { fromAgent: "b1", toAgent: "a1" }, // reciprocal but cross-operator: fine
    ];
    const report = detectCollusion(edges, g);
    assert.deepEqual(report.reciprocalSameOperator, [["a1", "a2"]]);
    assert.equal(report.inwardOperators.length, 1);
    assert.equal(report.inwardOperators[0]!.operator, "op-x");
  });

  it("caps live vouches and refuses self-vouching", () => {
    const g = new OperatorGraph();
    assert.equal(g.addVouch("op-a", "op-a", 0).ok, false);
    for (let i = 0; i < 5; i++) assert.equal(g.addVouch("op-a", `op-${i}`, i).ok, true);
    assert.equal(g.addVouch("op-a", "op-z", 9).ok, false);
  });
});
