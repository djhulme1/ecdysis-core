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
import { scoreRecord } from "../src/core/v2/resolve.js";
import { direct } from "../src/core/v2/direction.js";
import { buildLeaderboard, leaderboardInputOf } from "../src/core/v2/leaderboard.js";

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
const CLAIMS = ["ecd:0000000000000001", "ecd:0000000000000002", "ecd:0000000000000003", "ext:0123456789abcdef", "ecd:nothere", "", "ecd:1", "#", "arxiv:1706.03762"];
const TARGETS = CLAIMS;
const IDS = ["r1", "r2", "r3", "f1", "a".repeat(64), "", "r1"];

function randomValue(r: ReturnType<typeof rng>, depth = 0): unknown {
  switch (r.int(depth > 2 ? 7 : 10)) {
    case 0: return null;
    case 1: return r.next() < 0.5;
    case 2: return r.pick([0, 1, -1, 0.5, 1e308, -1e308, NaN, Infinity, 2 ** 53]);
    case 3: return r.pick(["", "x", "ecd:0000000000000001", "2026-10-03T09:00:00Z", "not a date", "verified", "fabrication", "\u0000", "💥"]);
    case 4: return r.pick(HANDLES);
    case 5: return r.pick(TARGETS);
    case 6: return r.pick(IDS);
    case 7: return Array.from({ length: r.int(4) }, () => randomValue(r, depth + 1));
    default: { const o: Record<string, unknown> = {}; for (let i = r.int(4); i > 0; i--) o[r.pick(["id", "cid", "handle", "operatorId", "target", "text", "test", "kind", "field", "scope", "data", "blockers", "confidence", "verdict", "oddCommit", "key", "commit", "models", "builds_on", "tier", "subject", "compromisedAt", "outcome", "crossMatch", "seedInsensitive", "decision", "crossCheck", "seed", "bundle", "forecast", "claim", "blocker", "read", "looked", "source", "citedBy", "zzz"])] = randomValue(r, depth + 1); return o; }
  }
}

/** A mostly well-formed entry of the given type, with random fields torn out or corrupted. */
function entry(r: ReturnType<typeof rng>, seq: number, type: V2EntryType): V2Entry {
  const ts = new Date(Date.UTC(2026, 9, 1) + seq * 60_000 + (r.next() < 0.1 ? -1e12 : 0)).toISOString();
  const handle = r.pick(HANDLES), operatorId = r.pick(OPS), target = r.pick(TARGETS), id = r.pick(IDS);
  let p: Record<string, unknown>;
  switch (type) {
    case "constitution.adopt": p = { version: r.pick(["2.1.0", "2.0.0", "x", 3]), hash: r.pick(["a".repeat(64), "", "short"]), by: r.pick(["operator", "x"]) }; break;
    case "operator.tier": p = { operatorId, tier: r.pick(["verified", "account", "unverified", "king", 3]) }; break;
    case "agent.register": p = { handle, operatorId, publicKey: `pk-${handle}-${r.int(3)}`, models: r.pick([["claude"], ["gpt", "gemini"], [], "gpt", null]), managed: r.pick([true, false, "yes"]) }; break;
    case "claim.publish": p = {
      id: r.pick(CLAIMS), cid: r.pick(["a".repeat(64), "b".repeat(64), ""]), handle, operatorId, text: r.pick(["a claim", "", 5]), test: r.pick(["its test", ""]),
      kind: r.pick(["empirical", "conceptual", undefined, "x"]), confidence: r.pick([0.8, 1.5, -1, "x", undefined]), field: r.pick(["ml", "econ", "", "x"]),
      scope: r.pick([{ general: "construction", basis: "b" }, { period: { from: "2020-01-01", to: "2021-01-01" }, basis: "b" }, { general: "asserted", basis: "b" }, "x", null, undefined, { period: { from: "x", to: 3 } }]),
      data: r.pick([undefined, [], [{ name: "d", url: "https://x", sha256: "a".repeat(64), bytes: 3, access: "open" }], "x", [5]]),
      builds_on: r.pick([[{ id: "ecd:0000000000000001", rel: "extends", basis: "reviewed" }], [{ id: "ecd:0000000000000002", rel: "method", basis: "reproduced" }], [{ id: "ecd:0000000000000001", rel: "replicates" }], [{ id: "ext:0123456789abcdef", rel: "refutes" }], [{ id: "arxiv:1706.03762", rel: "background" }], [{ id: r.pick(CLAIMS), rel: r.pick(["extends", "x", 3]) }], [], null, "x"]),
      blockers: r.pick([undefined, [], [{ blocker: "data-unavailable", detail: "d", unblockedBy: "u" }], [{ blocker: "x" }], "x"]),
      models: r.pick([["gpt"], undefined, "x"]),
    }; break;
    case "claim.external": p = { id: r.pick(["ext:0123456789abcdef", ""]), handle, operatorId, source: r.pick(["arxiv:1706.03762", "doi:10.1/x", ""]), quote: "q", test: "t", kind: r.pick(["empirical", "conceptual", undefined]), scope: r.pick([{ general: "construction", basis: "b" }, { period: { from: "2009-04-01", to: "2012-07-31" }, basis: "b" }, undefined, "x"]), fidelity: r.pick([{ as: "reported", basis: "b" }, { as: "adapted", basis: "b" }, undefined, 3]) }; break;
    case "claim.amend": p = { claim: target, handle, operatorId, kind: r.pick([undefined, "conceptual", "empirical", "x"]), test: r.pick([undefined, "a corrected test of some length", "", 3]), scope: r.pick([undefined, { general: "construction", basis: "b" }, "x"]), fidelity: r.pick([undefined, { as: "adapted", basis: "b" }]), data: r.pick([undefined, [], "x"]) }; break;
    case "check.commit": p = { id, target, kind: r.pick(["replication", "rerun", "other"]), design: r.pick([undefined, { method: "stated", data: "original", basis: "b" }, { method: "altered", data: "new", basis: "b", alteration: "a" }, { method: "x" }, "x"]), period: r.pick([undefined, { from: "2020-01-01", to: "2021-01-01" }, "x"]), bundle: r.pick(["b1", "b2", ""]), image: r.pick([true, false]), runtimeMinutes: r.pick([5, 0, -1, "x"]), handle, operatorId, models: r.pick([["gpt"], undefined]), key: r.pick([undefined, "ck", "pk-Ant-0"]) }; break;
    case "check.seal": p = { commit: id, seal: "s", seed: r.pick(["ab".repeat(32), "cd".repeat(32), ""]), crossCheck: r.pick([null, "r1", "r2", "nothere"]) }; break;
    case "check.result": p = { commit: id, outcome: r.pick(["confirmed", "failed", "inconclusive", "maybe"]), outputs: r.pick([undefined, { alpha: 1 }, { period_from: 20200101, period_to: 20201231 }, { period_from: "x" }, "x"]), crossMatch: r.pick([true, false, null]), seedInsensitive: r.pick([true, undefined]), key: r.pick([undefined, "pk-Ant-0", "ck"]) }; break;
    case "check.lapse": p = { commit: id }; break;
    case "check.attempt": p = { id: r.pick(["a".repeat(64), "b".repeat(64), "", "short"]), claim: target, handle, operatorId, blocker: r.pick(["data-unavailable", "code-unavailable", "underspecified", "source-restricted", "data-restricted", "artefact-unavailable", "apparatus", "compute", "x", 3]), read: r.pick(["full", "abstract", "none", undefined, "x"]), looked: r.pick([undefined, [], ["the data statement"], "x", [3]]), detail: "d", unblockedBy: "u", effortMinutes: r.pick([undefined, 30, -1, "x"]), models: r.pick([["gpt"], undefined]), key: r.pick([undefined, "ck"]) }; break;
    case "attempt.clear": p = { id: r.pick(["c".repeat(64), "", "short"]), claim: target, handle, operatorId, blocker: r.pick(["data-unavailable", "compute", "x"]), how: "h" }; break;
    case "finding.decide": p = { id: r.pick(["f1", "f2"]), bundle: r.pick(["b1", "b2"]), seed: r.pick(["ab".repeat(32), "cd".repeat(32)]), verdict: r.pick(["fabrication", "irreproducible", "unresolved", "guilty"]), oddCommit: r.pick([id, null]), runs: [id] }; break;
    case "finding.reverse": p = { id: r.pick(["f1", "f2", "f9"]) }; break;
    case "review.file": p = { id, claim: target, handle, operatorId, forecast: r.pick([0.8, 0.2, 2, -1, "x"]), key: r.pick([undefined, "ck"]) }; break;
    case "key.delegate": p = { handle, operatorId, key: r.pick(["ck", "ck2", "pk-Ant-0", ""]), scope: "reports" }; break;
    case "key.revoke": p = { handle, operatorId, key: r.pick(["ck", "pk-Ant-0", "pk-Bee-1", ""]), scope: r.pick(["reports", "main"]), compromisedAt: r.pick([undefined, "2026-10-01T00:30:00Z", "garbage", "2099-01-01T00:00:00Z"]) }; break;
    case "canary.reveal": p = { claim: target, outcome: r.pick(["confirmed", "refuted", "x"]) }; break;
    case "hazard.hold": p = { subject: r.pick([target, id, "a".repeat(64), ""]), reason: "r" }; break;
    case "hazard.release": p = { subject: r.pick([target, id, "a".repeat(64)]), decision: r.pick(["release", "reject", undefined]) }; break;
    case "submission.withdraw": p = { subject: r.pick([target, id, "a".repeat(64), ""]), by: operatorId, handle, reason: r.pick(["r", "", 5]) }; break;
    case "content.withhold": p = { subject: r.pick([target, id, "a".repeat(64), ""]), status: r.pick(["review", "withdrawn", "x", undefined]), reason: "r", by: r.pick(["screening", "steward", undefined]), steward: r.pick(["", "op_steward", 3]) }; break;
    case "content.restore": p = { subject: r.pick([target, id, "a".repeat(64), ""]), steward: "op_steward" }; break;
    case "source.observed": p = { source: r.pick(["arxiv:1706.03762", "doi:10.1/x", "ARXIV:1706.03762", "", "x"]), provider: r.pick(["openalex", "x", undefined]), work: "W1", citedBy: r.pick([100, 0, -1, "x", NaN, 1e308]), venueCitedness: r.pick([undefined, 10, -5, "x"]), year: r.pick([undefined, 2017, 1700, 2300, "x"]), field: r.pick(["ml", "", undefined]), fieldId: "F1", unresolved: r.pick([true, false, "x"]) }; break;
    case "field.observed": p = { field: r.pick(["ml", "econ", "", undefined]), fieldId: "F1", works: r.pick([1000, 0, -1, "x", NaN]), citedBy: r.pick([1e6, 0, -1, "x", Infinity]) }; break;
    // arguments/0.1: arguments, checks and answers, well-formed and not.
    case "argument.file": p = { id: r.pick(["a".repeat(64), "b".repeat(64), "short", ""]), claim: target, stance: r.pick(["refutes", "qualifies", "supports", "x"]), grounds: r.pick(["counterexample", "contradiction", "unsupported-premise", "logical-gap", "statistical-insufficiency", "methodological-flaw", "x"]), text: "t", cites: r.pick([[target], ["ecd:0000000000000001", 3], "ecd:0000000000000001", null, undefined]), instance: r.pick([null, { text: "i" }, { bundle: { repo: "https://x", commit: "c", run: "r" } }, "i", 5, []]), confidence: r.pick([0.8, 0.2, 0, 1, 2, -1, "x", NaN]), handle, operatorId, models: r.pick([["gpt"], undefined]) }; break;
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
        out = scoreRecord(rec);
      } catch (e) {
        assert.fail(`scoreRecord threw on trial ${trial}: ${String(e)}\n${JSON.stringify(log).slice(0, 2000)}`);
      }
      // The derived views are total too: the direction list and the leaderboard over whatever the record holds.
      try {
        const claims = [...out.claims.values()].map((c) => ({ ref: c.ref, external: c.external, kind: c.kind, status: c.status, credence: c.credence, stakes: c.stakes, use: c.use, dispute: c.dispute, valueOfChecking: c.valueOfChecking, disputePriority: c.disputePriority, authorOperator: rec.claims.find((x) => x.ref === c.ref)?.authorOperator ?? "", minutes: 10, blocked: rec.blockers.get(c.ref) ?? null }));
        direct({ claims, arguments: [], candidates: [], registered: new Set(), forOperator: null, limit: 10 });
        buildLeaderboard(leaderboardInputOf(rec, out, 10, 5));
      } catch (e) {
        assert.fail(`a derived view threw on trial ${trial}: ${String(e)}\n${JSON.stringify(log).slice(0, 2000)}`);
      }
      for (const c of out.claims.values()) {
        for (const [k, v] of Object.entries({ credence: c.credence, use: c.use, dispute: c.dispute, stakes: c.stakes, threshold: c.threshold, prior: c.prior, logOdds: c.logOdds, valueOfChecking: c.valueOfChecking })) {
          assert.ok(Number.isFinite(v), `trial ${trial}: ${c.ref}.${k} = ${v}`);
        }
        assert.ok(c.credence >= 0 && c.credence <= 1, `trial ${trial}: credence in [0, 1]`);
      }
      for (const [agent, rel] of out.track.reliability) assert.ok(Number.isFinite(rel) && rel >= 0 && rel <= 1, `trial ${trial}: reliability of ${agent} = ${rel}`);
      for (const a of rec.arguments.values()) assert.ok(a.status === "open" || a.status === "upheld" || a.status === "dismissed", `trial ${trial}: argument ${a.id} status ${a.status}`);
      for (const c of out.claims.values()) if (c.cap !== null) assert.ok(c.cap > 0 && c.cap < 1 && c.credence <= c.cap + 1e-9, `trial ${trial}: cap ${c.cap} on ${c.ref}`);
      for (const [ref, b] of rec.blockers) assert.ok(Array.isArray(b.blockers) && b.claim === ref, `trial ${trial}: blockers on ${ref}`);
    }
    assert.ok(entries > 40_000, `a real exercise (${entries} entries)`);
  });
});
