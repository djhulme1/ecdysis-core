/**
 * The derivation is total: whatever the log holds, deriving the record and
 * computing the numbers never throws and never yields a NaN. Every v2 page
 * and endpoint derives the record from the log on request, so a single entry
 * that made the derivation throw would take the whole of v2 down with it.
 * The service validates what it appends; this is the second line.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { deriveV2, V2_ENTRY_TYPES, type V2Entry, type V2EntryType } from "../src/core/v2/flow.js";
import { computeV2 } from "../src/core/v2/scoring.js";

/** A small deterministic generator (xorshift32). */
function rng(seed: number) {
  let s = seed >>> 0 || 1;
  const next = () => { s ^= s << 13; s >>>= 0; s ^= s >>> 17; s ^= s << 5; s >>>= 0; return s / 4294967296; };
  const int = (n: number) => Math.floor(next() * n);
  const pick = <T,>(xs: readonly T[]): T => xs[int(xs.length)]!;
  return { next, int, pick };
}

const HANDLES = ["Ant", "Bee", "Cat", "Dog", "", "x".repeat(50), "Ant"];
const OPS = ["op-a", "op-b", "op-c", "", "op_0123456789abcdef01234567"];
const TARGETS = ["ecd:1#C1", "ecd:1#C2", "ext:0123456789abcdef#C1", "nothere#C9", "", "ecd:1", "#"];
const IDS = ["r1", "r2", "r3", "f1", "a".repeat(64), "", "r1"];

function randomValue(r: ReturnType<typeof rng>, depth = 0): unknown {
  switch (r.int(depth > 2 ? 7 : 10)) {
    case 0: return null;
    case 1: return r.next() < 0.5;
    case 2: return r.pick([0, 1, -1, 0.5, 1e308, -1e308, NaN, Infinity, 2 ** 53]);
    case 3: return r.pick(["", "x", "ecd:1#C1", "2026-10-03T09:00:00Z", "not a date", "verified", "fabrication", "\u0000", "💥"]);
    case 4: return r.pick(HANDLES);
    case 5: return r.pick(TARGETS);
    case 6: return r.pick(IDS);
    case 7: return Array.from({ length: r.int(4) }, () => randomValue(r, depth + 1));
    default: { const o: Record<string, unknown> = {}; for (let i = r.int(4); i > 0; i--) o[r.pick(["id", "handle", "operatorId", "target", "claims", "label", "confidence", "verdict", "oddCommit", "key", "commit", "models", "builds_on", "for", "tier", "subject", "compromisedAt", "outcome", "crossMatch", "seedInsensitive", "decision", "crossCheck", "seed", "bundle", "forecast", "claim", "zzz"])] = randomValue(r, depth + 1); return o; }
  }
}

/** A mostly well-formed entry of the given type, with random fields torn out or corrupted. */
function entry(r: ReturnType<typeof rng>, seq: number, type: V2EntryType): V2Entry {
  const ts = new Date(Date.UTC(2026, 9, 1) + seq * 60_000 + (r.next() < 0.1 ? -1e12 : 0)).toISOString();
  const handle = r.pick(HANDLES), operatorId = r.pick(OPS), target = r.pick(TARGETS), id = r.pick(IDS);
  let p: Record<string, unknown>;
  switch (type) {
    case "operator.tier": p = { operatorId, tier: r.pick(["verified", "account", "unverified", "king", 3]) }; break;
    case "operator.vouch": p = { from: r.pick(OPS), for: operatorId }; break;
    case "agent.register": p = { handle, operatorId, publicKey: `pk-${handle}-${r.int(3)}`, models: r.pick([["claude"], ["gpt", "gemini"], [], "gpt", null]), managed: r.pick([true, false, "yes"]) }; break;
    case "paper.publish": p = { id: r.pick(["ecd:1", "ecd:2", ""]), handle, operatorId, claims: r.pick([[{ label: "C1", confidence: 0.8 }, { label: "C2", confidence: 1.5 }], [], "C1", null]), builds_on: r.pick([[{ id: "ecd:1", rel: "extends", basis: "reviewed", claims: ["C1"] }], [{ id: "ecd:1", rel: "background" }], [], null]) }; break;
    case "claim.external": p = { id: r.pick(["ext:0123456789abcdef", ""]), handle, operatorId, source: "arxiv:1706.03762", quote: "q", test: "t" }; break;
    case "check.commit": p = { id, target, kind: r.pick(["replication", "rerun", "other"]), bundle: r.pick(["b1", "b2", ""]), image: r.pick([true, false]), runtimeMinutes: r.pick([5, 0, -1, "x"]), handle, operatorId, models: r.pick([["gpt"], undefined]) }; break;
    case "check.seal": p = { commit: id, seal: "s", seed: r.pick(["ab".repeat(32), "cd".repeat(32), ""]), crossCheck: r.pick([null, "r1", "r2", "nothere"]) }; break;
    case "check.result": p = { commit: id, outcome: r.pick(["confirmed", "failed", "inconclusive", "maybe"]), crossMatch: r.pick([true, false, null]), seedInsensitive: r.pick([true, undefined]), key: r.pick([undefined, "pk-Ant-0", "ck"]) }; break;
    case "check.lapse": p = { commit: id }; break;
    case "finding.decide": p = { id: r.pick(["f1", "f2"]), bundle: r.pick(["b1", "b2"]), seed: r.pick(["ab".repeat(32), "cd".repeat(32)]), verdict: r.pick(["fabrication", "irreproducible", "unresolved", "guilty"]), oddCommit: r.pick([id, null]), runs: [id] }; break;
    case "finding.reverse": p = { id: r.pick(["f1", "f2", "f9"]) }; break;
    case "review.file": p = { id, claim: target, handle, operatorId, forecast: r.pick([0.8, 0.2, 2, -1, "x"]), key: r.pick([undefined, "ck"]) }; break;
    case "key.delegate": p = { handle, operatorId, key: r.pick(["ck", "ck2", "pk-Ant-0", ""]), scope: "reports" }; break;
    case "key.revoke": p = { handle, operatorId, key: r.pick(["ck", "pk-Ant-0", "pk-Bee-1", ""]), scope: r.pick(["reports", "main"]), compromisedAt: r.pick([undefined, "2026-10-01T00:30:00Z", "garbage", "2099-01-01T00:00:00Z"]) }; break;
    case "canary.reveal": p = { claim: target, outcome: r.pick(["confirmed", "refuted", "x"]) }; break;
    case "hazard.hold": p = { subject: r.pick([target, id, "ecd:1", ""]), reason: "r" }; break;
    case "hazard.release": p = { subject: r.pick([target, id, "ecd:1"]), decision: r.pick(["release", "reject", undefined]) }; break;
    case "challenge.propose": p = { id: r.pick(["ch:0123456789abcdef", "ch:x", ""]), claim: target, title: "t", brief: "b", scale: r.pick(["cpu-minutes", "reasoning", "x"]), wants: r.pick(["receipt", "argument", "x", undefined]), handle, operatorId, proposer: r.pick(["agent", "person", "steward", "x"]) }; break;
    case "challenge.withdraw": p = { id: r.pick(["ch:0123456789abcdef", "ch:x"]), reason: "r", by: r.pick(["proposer", "steward", "x"]) }; break;
    // arguments/0.1: arguments, checks and answers, well-formed and not.
    case "argument.file": p = { id: r.pick(["a".repeat(64), "b".repeat(64), "short", ""]), claim: target, stance: r.pick(["refutes", "qualifies", "supports", "x"]), grounds: r.pick(["counterexample", "contradiction", "unsupported-premise", "logical-gap", "statistical-insufficiency", "methodological-flaw", "x"]), text: "t", cites: r.pick([[target], ["ecd:1#C1", 3], "ecd:1#C1", null, undefined]), instance: r.pick([null, { text: "i" }, { bundle: { repo: "https://x", commit: "c", run: "r" } }, "i", 5, []]), confidence: r.pick([0.8, 0.2, 0, 1, 2, -1, "x", NaN]), handle, operatorId, models: r.pick([["gpt"], undefined]) }; break;
    case "argument.check": p = { id: r.pick(["c".repeat(64), ""]), argument: r.pick(["a".repeat(64), "b".repeat(64), "nothere"]), holds: r.pick([true, false, "yes", 1, null]), note: "n", handle, operatorId, models: r.pick([["claude"], ["gpt", "claude"], undefined]), key: r.pick([undefined, "ck"]) }; break;
    case "argument.answer": p = { argument: r.pick(["a".repeat(64), "b".repeat(64), "nothere"]), text: "x", handle, operatorId }; break;
    default: p = {};
  }
  // Tear fields out or corrupt them, sometimes wholesale.
  if (r.next() < 0.15) for (const k of Object.keys(p)) if (r.next() < 0.3) delete p[k];
  if (r.next() < 0.15) for (const k of Object.keys(p)) if (r.next() < 0.3) p[k] = randomValue(r);
  if (r.next() < 0.03) p = randomValue(r) as Record<string, unknown>;
  return { seq, ts, type, payload: p };
}

describe("the derivation is total", () => {
  it("never throws and never yields a NaN, over thousands of random and corrupted logs", () => {
    const types = V2_ENTRY_TYPES;
    let entries = 0;
    for (let trial = 0; trial < 4000; trial++) {
      const r = rng(1234 + trial);
      const log: V2Entry[] = [];
      const n = r.int(60);
      for (let i = 0; i < n; i++) log.push(entry(r, i, r.pick(types)));
      entries += n;
      const now = new Date(Date.UTC(2026, 9, 1) + r.int(100) * 24 * 3600 * 1000);
      let rec;
      try {
        rec = deriveV2(log, now);
      } catch (e) {
        assert.fail(`deriveV2 threw on trial ${trial}: ${String(e)}\n${JSON.stringify(log).slice(0, 2000)}`);
      }
      let out;
      try {
        out = computeV2(rec.claims, rec.evidence, rec.uses, { vouchLinked: rec.vouchLinked, ringLinked: rec.ringLinked, voidedOperators: rec.voidedOperators, fabricators: rec.fabricators, lapses: rec.lapses, anchors: rec.anchors, arguments: rec.argumentEffects, argumentStates: [...rec.arguments.values()] });
      } catch (e) {
        assert.fail(`computeV2 threw on trial ${trial}: ${String(e)}\n${JSON.stringify(log).slice(0, 2000)}`);
      }
      for (const c of out.claims.values()) {
        for (const [k, v] of Object.entries({ credence: c.credence, use: c.use, dispute: c.dispute, threshold: c.threshold, prior: c.prior, logOdds: c.logOdds })) {
          assert.ok(Number.isFinite(v), `trial ${trial}: ${c.ref}.${k} = ${v}`);
        }
        assert.ok(c.credence >= 0 && c.credence <= 1, `trial ${trial}: credence in [0, 1]`);
      }
      for (const [agent, rel] of out.track.reliability) assert.ok(Number.isFinite(rel) && rel >= 0 && rel <= 1, `trial ${trial}: reliability of ${agent} = ${rel}`);
      for (const a of rec.arguments.values()) assert.ok(a.status === "open" || a.status === "upheld" || a.status === "dismissed", `trial ${trial}: argument ${a.id} status ${a.status}`);
      for (const c of out.claims.values()) if (c.cap !== null) assert.ok(c.cap > 0 && c.cap < 1 && c.credence <= c.cap + 1e-9, `trial ${trial}: cap ${c.cap} on ${c.ref}`);
    }
    assert.ok(entries > 40_000, `a real exercise (${entries} entries)`);
  });
});
