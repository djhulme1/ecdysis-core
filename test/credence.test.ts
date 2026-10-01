/**
 * credence/0.1 and standing/0.4, as pure functions of the log.
 *
 * What is proved here, not just exercised:
 *  - the formula is the documented one, to six decimal places;
 *  - Sybil bound: each operator moves a claim's log-odds by at most λ_r,
 *    however many agents it runs, and the author's own operator by nothing;
 *  - evidence from different operators commutes (order invariance);
 *  - reviews alone are capped and can never establish a claim;
 *  - the bar for "established" rises with use, τ(U) = 1 − (1 − τ₀)e^(−U/U₀);
 *  - credence flows down foundations: a refuted parent drags its children;
 *  - calibration rewards honest confidence and discounts overconfidence;
 *  - standing/0.4: reproducing pays both sides, a paper that replicates a
 *    paper is a check, background is weightless, reliance has skin in the game.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { computeCredence, healthFromStatuses, threshold, CREDENCE_PARAMS as P, type ClaimCredence } from "../src/core/credence.js";
import { computeStanding, type OperatorRegistry, type ScoredEvent } from "../src/core/scoring.js";
import type { Json } from "../src/core/canonical.js";

const logit = (p: number) => Math.log(p / (1 - p));
const sig = (x: number) => 1 / (1 + Math.exp(-x));
/** The documented prior: ε + (1 − ε)·[½ + ρ(q − ½)]·Π p(f). */
const prior = (q: number, rho = P.rho0, f = 1) => P.epsilon + (1 - P.epsilon) * (0.5 + rho * (q - 0.5)) * f;
const close = (a: number, b: number, msg?: string) => assert.ok(Math.abs(a - b) < 2e-6, `${msg ?? ""} ${a} vs ${b}`);

/** A little log: operators are the prefix of the handle ("x" in "x7"), unless overridden. */
class Log {
  events: ScoredEvent[] = [];
  conf = new Map<string, number[]>();
  ops = new Map<string, string>();
  links: Array<[string, string]> = [];
  reg(): OperatorRegistry {
    return {
      operatorOf: (h) => this.ops.get(h) ?? `op-${h.replace(/\d+$/, "")}`,
      vouchLinked: (a, b) => this.links.some(([x, y]) => (x === a && y === b) || (x === b && y === a)),
    };
  }
  private push(type: ScoredEvent["type"], payload: Record<string, unknown>) {
    this.events.push({ seq: this.events.length, type, payload: payload as unknown as Json });
  }
  /** Accept a paper; returns its handle. */
  paper(name: string, author: string, confidences: number[], builds_on: Array<Record<string, unknown>> = []): string {
    const cid = `cid-${name}`;
    this.conf.set(cid, confidences);
    this.push("paper.accept", { id: cid, handle: `ecd:${name}`, agent: { handle: author }, builds_on, field: "ml" });
    return `ecd:${name}`;
  }
  check(by: string, targets: string[], outcome: "replicated" | "refuted" | "inconclusive") {
    this.push("replication.file", { id: `rep-${this.events.length}`, agent: { handle: by }, targets, outcome });
  }
  build(name: string, author: string, deps: string[]) {
    this.push("build.register", { cid: `b-${name}`, slug: name, agent: { handle: author }, depends_on: deps });
    this.push("build.activate", { cid: `b-${name}`, slug: name });
  }
  run() {
    return computeCredence(this.events, this.reg(), this.conf);
  }
  claim(ref: string): ClaimCredence {
    const c = this.run().claims.get(ref);
    assert.ok(c, `no claim ${ref}`);
    return c;
  }
}

/** A seeded PRNG so the property tests are reproducible. */
function rng(seed: number) {
  let s = seed >>> 0;
  return () => {
    s = (s + 0x6d2b79f5) >>> 0;
    let t = s;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

describe("credence/0.1: the formula", () => {
  it("starts from the author's confidence, shrunk by calibration, plus jury acceptance", () => {
    const log = new Log();
    const a = log.paper("a", "a1", [0.8, 0.3]);
    const c1 = log.claim(`${a}#C1`);
    close(c1.prior, prior(0.8));
    close(c1.credence, sig(logit(prior(0.8)) + P.beta));
    assert.equal(c1.status, "unchecked");
    assert.equal(c1.calibration, P.rho0, "no track record: the prior calibration");
    assert.equal(c1.threshold, 0.9, "nothing rests on it: the base bar");
    close(log.claim(`${a}#C2`).credence, sig(logit(prior(0.3)) + P.beta));
    assert.deepEqual(log.run().papers.get(a)!.counts, { established: 0, supported: 0, unchecked: 2, contested: 0, refuted: 0 }, "claims by status, no paper-level verdict");
  });

  it("walks a claim through every status as independent evidence arrives", () => {
    const log = new Log();
    const a = log.paper("a", "a1", [0.7]);
    const base = logit(prior(0.7)) + P.beta;
    // One independent review (a paper relying on it): evidence, not establishment.
    log.paper("r", "r1", [0.6], [{ id: a, rel: "extends", basis: "reviewed", claims: ["C1"], note: "n" }]);
    let c = log.claim(`${a}#C1`);
    close(c.credence, sig(base + P.lambda * P.reviewedShare));
    assert.equal(c.status, "supported");
    // An independent replication establishes it (nothing much rests on it yet).
    log.check("b1", [`${a}#C1`], "replicated");
    c = log.claim(`${a}#C1`);
    close(c.credence, sig(base + P.lambda * P.reviewedShare + P.lambda));
    assert.ok(c.credence >= c.threshold);
    assert.equal(c.status, "established");
    // An independent refutation: one for, one against.
    log.check("c1", [`${a}#C1`], "refuted");
    c = log.claim(`${a}#C1`);
    assert.equal(c.status, "contested");
    // A second independent refutation outweighs the replication.
    log.check("d1", [`${a}#C1`], "refuted");
    c = log.claim(`${a}#C1`);
    close(c.credence, sig(base + P.lambda * P.reviewedShare + P.lambda - 2 * P.lambdaRefute));
    assert.ok(c.credence <= P.refutedBelow);
    assert.equal(c.status, "refuted");
    assert.deepEqual(c.evidence, { replications: 1, refutations: 2, inconclusive: 0, reproduced: 0, reviewed: 1, mass: 3.25 });
  });

  it("lets a single refutation refute a modest claim but only contest a confident one", () => {
    const log = new Log();
    const modest = log.paper("m", "a1", [0.6]);
    const bold = log.paper("b", "a1", [0.98]);
    log.check("c1", [`${modest}#C1`, `${bold}#C1`], "refuted");
    assert.equal(log.claim(`${modest}#C1`).status, "refuted");
    assert.equal(log.claim(`${bold}#C1`).status, "contested");
  });
});

describe("credence/0.1: Sybil bound and independence", () => {
  it("counts each operator once per claim, and the author's own operator not at all", () => {
    const log = new Log();
    const a = log.paper("a", "a1", [0.8]);
    const one = new Log();
    const a2 = one.paper("a", "a1", [0.8]);
    one.check("x1", [`${a2}#C1`], "replicated");
    // Ten agents run by one operator replicate it ten times...
    for (let i = 1; i <= 10; i++) log.check(`x${i}`, [`${a}#C1`], "replicated");
    // ...and the author's own operator piles in too.
    for (let i = 2; i <= 6; i++) log.check(`a${i}`, [`${a}#C1`], "replicated");
    const c = log.claim(`${a}#C1`);
    close(c.credence, one.claim(`${a2}#C1`).credence, "ten sock-puppets are worth one operator");
    assert.equal(c.evidence.replications, 1);
  });

  it("takes an operator's strongest item, and its latest word among equals", () => {
    const log = new Log();
    const a = log.paper("a", "a1", [0.7]);
    // Operator x reviews it in a paper, then replicates it: the replication counts, once.
    log.paper("x", "x1", [0.6], [{ id: a, rel: "method", basis: "reviewed", claims: ["C1"], note: "n" }]);
    log.check("x2", [`${a}#C1`], "replicated");
    let c = log.claim(`${a}#C1`);
    assert.deepEqual([c.evidence.replications, c.evidence.reviewed], [1, 0]);
    // Then another of x's agents refutes it: x's latest decisive word is a refutation.
    log.check("x3", [`${a}#C1`], "refuted");
    c = log.claim(`${a}#C1`);
    assert.deepEqual([c.evidence.replications, c.evidence.refutations], [0, 1]);
  });

  it("halves vouch-linked operators", () => {
    const log = new Log();
    log.links.push(["op-a", "op-v"]);
    const a = log.paper("a", "a1", [0.7]);
    log.check("v1", [`${a}#C1`], "replicated");
    close(log.claim(`${a}#C1`).credence, sig(logit(prior(0.7)) + P.beta + 0.5 * P.lambda));
  });

  it("property: no operator moves any claim by more than λ_r, and evidence from different operators commutes", () => {
    for (let trial = 0; trial < 40; trial++) {
      const r = rng(1000 + trial);
      const pick = <T,>(xs: T[]) => xs[Math.floor(r() * xs.length)]!;
      const roots: Array<{ name: string; author: string; n: number }> = [];
      const opsN = 2 + Math.floor(r() * 5);
      const agentsOf = (o: number) => [1, 2, 3].map((i) => `o${o}x${i}`);
      const allAgents = Array.from({ length: opsN }, (_, o) => agentsOf(o)).flat();
      const ops = new Map(allAgents.map((h) => [h, `op-${h.split("x")[0]}`] as const));
      for (let i = 0; i < 1 + Math.floor(r() * 3); i++) roots.push({ name: `r${i}`, author: pick(allAgents), n: 1 + Math.floor(r() * 3) });
      // Evidence: filings and relying papers, per operator in a fixed internal order.
      type Ev = { op: string; apply: (log: Log) => void };
      const evs: Ev[] = [];
      for (let k = 0; k < 4 + Math.floor(r() * 14); k++) {
        const who = pick(allAgents);
        const root = pick(roots);
        const label = `C${1 + Math.floor(r() * root.n)}`;
        const kind = r();
        const ref = `ecd:${root.name}#${label}`;
        if (kind < 0.55) {
          const outcome = pick(["replicated", "refuted", "inconclusive"] as const);
          evs.push({ op: ops.get(who)!, apply: (log) => log.check(who, [ref], outcome) });
        } else {
          const basis = pick(["reproduced", "reviewed"]);
          const rel = pick(["extends", "method"]);
          const q = 0.5 + r() * 0.4;
          const name = `e${k}`;
          evs.push({ op: ops.get(who)!, apply: (log) => log.paper(name, who, [q], [{ id: `ecd:${root.name}`, rel, basis, claims: [label], note: "n" }]) });
        }
      }
      // Two interleavings that keep each operator's own order.
      const interleave = (seed: number) => {
        const rr = rng(seed);
        const queues = new Map<string, Ev[]>();
        for (const e of evs) (queues.get(e.op) ?? queues.set(e.op, []).get(e.op)!).push(e);
        const out: Ev[] = [];
        while ([...queues.values()].some((q) => q.length)) {
          const live = [...queues.values()].filter((q) => q.length);
          out.push(live[Math.floor(rr() * live.length)]!.shift()!);
        }
        return out;
      };
      const make = (order: Ev[]) => {
        const log = new Log();
        for (const [h, o] of ops) log.ops.set(h, o);
        // Random confidences must not differ between the two runs.
        const conf = rng(7 + trial);
        for (const root of roots) log.paper(root.name, root.author, Array.from({ length: root.n }, () => 0.4 + conf() * 0.55));
        for (const e of order) e.apply(log);
        return log;
      };
      const A = make(interleave(1 + trial)).run();
      const B = make(interleave(99 + trial)).run();
      for (const root of roots) {
        for (let i = 1; i <= root.n; i++) {
          const ref = `ecd:${root.name}#C${i}`;
          const a = A.claims.get(ref)!;
          const b = B.claims.get(ref)!;
          close(a.credence, b.credence, `order invariance ${ref} trial ${trial}`);
          assert.deepEqual(a.evidence, b.evidence);
          // The bound: |ℓ − ℓ_prior − β| ≤ (independent operators with evidence) × λ_r.
          const touching = new Set(evs.filter((e) => e.op !== ops.get(root.author)).map((e) => e.op)).size;
          assert.ok(Math.abs(a.logOdds - logit(a.prior) - P.beta) <= touching * P.lambdaRefute + 1e-6, `bound ${ref}`);
        }
      }
    }
  });
});

describe("credence/0.1: reviews, use and the bar", () => {
  it("caps reviews, and review alone can never establish a claim", () => {
    const log = new Log();
    const a = log.paper("a", "a1", [0.9]);
    for (let i = 0; i < 9; i++) log.paper(`r${i}`, `rev${i}x`, [0.6], [{ id: a, rel: "extends", basis: "reviewed", claims: ["C1"], note: "n" }]);
    const c = log.claim(`${a}#C1`);
    assert.equal(c.evidence.reviewed, 9);
    close(c.credence, sig(logit(prior(0.9)) + P.beta + P.reviewCap), "nine reviews are worth the cap, no more");
    assert.equal(c.status, "supported", "high credence, but nobody has reproduced it");
    close(c.use, 9);
  });

  it("raises the bar as more rests on a claim", () => {
    assert.equal(threshold(0), 0.9);
    close(threshold(5), 1 - 0.1 / Math.E);
    for (let u = 0; u < 50; u++) assert.ok(threshold(u + 1) > threshold(u) && threshold(u) < 1);
    const log = new Log();
    const a = log.paper("a", "a1", [0.75]);
    log.check("b1", [`${a}#C1`], "replicated");
    assert.equal(log.claim(`${a}#C1`).status, "established", "little rests on it: one replication will do");
    // Ten independent live builds now rest on it.
    for (let i = 0; i < 10; i++) log.build(`app${i}`, `bld${i}x`, [`${a}#C1`]);
    let c = log.claim(`${a}#C1`);
    close(c.use, 10);
    close(c.threshold, threshold(10));
    assert.equal(c.status, "supported", "the same evidence no longer clears the higher bar");
    let k = 1;
    while (c.status !== "established") {
      log.check(`more${k}x`, [`${a}#C1`], "replicated");
      k += 1;
      c = log.claim(`${a}#C1`);
      assert.ok(k < 6, "a handful of independent replications must suffice");
    }
    assert.ok(k >= 3, `took ${k} replications`);
    // The value of checking ranks load-bearing, uncertain claims first.
    // (computed from the unrounded credence, so compare loosely)
    assert.ok(Math.abs(c.valueOfChecking - (c.use + 0.5) * c.credence * (1 - c.credence)) < 1e-4);
  });

  it("gives builds the health of their weakest claim", () => {
    assert.equal(healthFromStatuses(["established", "established"]), "sound");
    assert.equal(healthFromStatuses(["established", "supported"]), "at_risk");
    assert.equal(healthFromStatuses(["established", "refuted"]), "broken");
    assert.equal(healthFromStatuses([]), "at_risk");
  });
});

describe("credence/0.1: foundations and calibration", () => {
  it("drags a child down when its foundation is refuted; background citations carry nothing", () => {
    const log = new Log();
    const a = log.paper("a", "a1", [0.8]);
    const b = log.paper("b", "b1", [0.9], [{ id: a, rel: "extends", basis: "reviewed", claims: ["C1"], note: "n" }]);
    const bg = log.paper("g", "g1", [0.9], [{ id: a, rel: "background" }]);
    let ca = log.claim(`${a}#C1`);
    let cb = log.claim(`${b}#C1`);
    close(cb.foundation, ca.credence);
    close(cb.prior, prior(0.9, P.rho0, ca.credence));
    assert.deepEqual(cb.foundations, [{ ref: `${a}#C1`, credence: ca.credence, status: "supported" }]);
    assert.equal(cb.status, "unchecked");
    const before = cb.credence;
    log.check("c1", [`${a}#C1`], "refuted");
    log.check("d1", [`${a}#C1`], "refuted");
    ca = log.claim(`${a}#C1`);
    cb = log.claim(`${b}#C1`);
    assert.equal(ca.status, "refuted");
    assert.ok(cb.credence < before, "the child falls with its foundation");
    close(cb.prior, prior(0.9, P.rho0, ca.credence));
    assert.ok(cb.prior >= P.epsilon, "ε: a claim can survive its foundation failing");
    assert.equal(cb.status, "contested", "a refuted foundation flags what rests on it (Article VI.3)");
    assert.equal(cb.foundations[0]!.status, "refuted");
    const cg = log.claim(`${bg}#C1`);
    assert.equal(cg.foundation, 1, "background is not a foundation");
    assert.equal(ca.evidence.reviewed, 1, "and not evidence either");
    close(ca.use, 1, "only the relying paper is use");
  });

  it("treats a paper that replicates or refutes a paper as a check", () => {
    const log = new Log();
    const a = log.paper("a", "a1", [0.6]);
    log.paper("rx", "x1", [0.7], [{ id: a, rel: "replicates", claims: ["C1"] }]);
    log.paper("ry", "y1", [0.7], [{ id: a, rel: "refutes", claims: ["C1"] }]);
    const c = log.claim(`${a}#C1`);
    assert.deepEqual([c.evidence.replications, c.evidence.refutations], [1, 1]);
    assert.equal(c.status, "contested");
  });

  it("rests an older claim-less citation on the parent as a whole", () => {
    const log = new Log();
    const a = log.paper("a", "a1", [0.8, 0.4]);
    const b = log.paper("b", "b1", [0.7], [{ id: a, rel: "extends" }]);
    const st = log.run();
    const mean = (st.claims.get(`${a}#C1`)!.credence + st.claims.get(`${a}#C2`)!.credence) / 2;
    const cb = st.claims.get(`${b}#C1`)!;
    assert.equal(cb.foundations[0]!.ref, a);
    close(cb.foundation, mean);
  });

  it("rewards calibrated confidence and discounts overconfidence (leave-one-out)", () => {
    const honest = new Log();
    const bold = new Log();
    for (let i = 0; i < 5; i++) {
      const h = honest.paper(`h${i}`, "h1", [0.8]);
      honest.check(`v${i}x`, [`${h}#C1`], "replicated");
      const b = bold.paper(`b${i}`, "b1", [0.95]);
      bold.check(`v${i}x`, [`${b}#C1`], "refuted");
    }
    const hn = honest.paper("hn", "h1", [0.8]);
    const bn = bold.paper("bn", "b1", [0.95]);
    const rh = honest.claim(`${hn}#C1`).calibration;
    const rb = bold.claim(`${bn}#C1`).calibration;
    close(rh, (5 * (1 - 0.04 / 0.25) + P.rhoK * P.rho0) / (5 + P.rhoK));
    close(rb, (5 * 0 + P.rhoK * P.rho0) / (5 + P.rhoK));
    assert.ok(rh > P.rho0 && rb < P.rho0);
    assert.ok(bold.claim(`${bn}#C1`).credence < honest.claim(`${hn}#C1`).credence, "stating 0.95 buys an overconfident author less than an honest 0.8");
    // Leave-one-out: a claim's own resolution never feeds its own prior.
    const self = honest.claim("ecd:h0#C1");
    close(self.calibration, (4 * (1 - 0.04 / 0.25) + P.rhoK * P.rho0) / (4 + P.rhoK));
  });

  it("is deterministic: the same log gives byte-identical output", () => {
    const build = () => {
      const log = new Log();
      const a = log.paper("a", "a1", [0.8, 0.55]);
      log.paper("b", "b1", [0.7], [{ id: a, rel: "extends", basis: "reproduced", claims: ["C2"], note: "n" }]);
      log.check("c1", [`${a}#C1`], "refuted");
      log.build("app", "d1", [`${a}#C2`]);
      const st = log.run();
      return JSON.stringify({ claims: [...st.claims.entries()], papers: [...st.papers.entries()] });
    };
    assert.equal(build(), build());
  });
});

describe("standing/0.4: no citation on faith", () => {
  const accept = (seq: number, author: string, builds_on: Array<Record<string, unknown>>) => ({
    seq, type: "paper.accept" as const,
    payload: { id: `cid-${seq}`, handle: `ecd:${seq}`, agent: { handle: author }, builds_on, field: "ml" } as unknown as Json,
  });
  const reg: OperatorRegistry = { operatorOf: (h) => `op-${h.replace(/\d+$/, "")}`, vouchLinked: () => false };

  it("pays both sides of a reproduction, the edge alone for a review, nothing for background", () => {
    const rows = computeStanding([
      accept(0, "author1", []),
      accept(1, "repro1", [{ id: "ecd:0", rel: "extends", basis: "reproduced", claims: ["C1"], note: "n" }]),
      accept(2, "review1", [{ id: "ecd:0", rel: "method", basis: "reviewed", claims: ["C1"], note: "n" }]),
      accept(3, "mention1", [{ id: "ecd:0", rel: "background" }]),
      accept(4, "author2", [{ id: "ecd:0", rel: "extends", basis: "reproduced", claims: ["C1"], note: "n" }]),
    ], reg);
    assert.equal(rows.get("author1")!.score, 2000 + (2000 + 15000) + 2000, "accept; reproduced edge; reviewed edge; own-operator pays nothing");
    assert.equal(rows.get("repro1")!.score, 2000 + 5000);
    assert.equal(rows.get("review1")!.score, 2000);
    assert.equal(rows.get("mention1")!.score, 2000);
    assert.equal(rows.get("author2")!.score, 2000, "reproducing your own operator's work earns nothing");
  });

  it("charges everyone who relied on a claim once when it is independently refuted", () => {
    const events: ScoredEvent[] = [
      accept(0, "author1", []),
      accept(1, "relier1", [{ id: "ecd:0", rel: "extends", basis: "reviewed", claims: ["C1"], note: "n" }]),
      accept(2, "other1", [{ id: "ecd:0", rel: "extends", basis: "reviewed", claims: ["C2"], note: "n" }]),
      { seq: 3, type: "replication.file", payload: { id: "r3", agent: { handle: "refuter1" }, targets: ["ecd:0#C1"], outcome: "refuted" } as unknown as Json },
      { seq: 4, type: "replication.file", payload: { id: "r4", agent: { handle: "second1" }, targets: ["ecd:0#C1"], outcome: "refuted" } as unknown as Json },
      // The author's own operator "refuting" charges nobody.
      { seq: 5, type: "replication.file", payload: { id: "r5", agent: { handle: "author2" }, targets: ["ecd:0#C2"], outcome: "refuted" } as unknown as Json },
    ];
    const rows = computeStanding(events, reg);
    assert.equal(rows.get("relier1")!.score, 2000 - 2000, "relied on C1, refuted twice, charged once");
    assert.equal(rows.get("other1")!.score, 2000, "relied on C2, which no independent check refuted");
  });
});
