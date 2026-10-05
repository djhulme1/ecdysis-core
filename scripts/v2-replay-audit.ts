/**
 * The v2 replay audit: a scripted record, scored by the published rules,
 * compared with a committed baseline.
 *
 *   npm run audit:v2                 # compare with audit/v2-baseline.json; exit 1 on any difference
 *   npm run audit:v2 -- --update     # write the new baseline, to commit with the change
 *
 * Every number the archive shows recomputes from the log, so a change to
 * the core that moves a credence, a status, a reliability or a finding is a
 * change to what the archive says about people's work. This script derives
 * and scores a fixed, deliberately varied synthetic log (agents of every
 * tier, claims resting on claims (network/0.1), claims from human
 * literature, receipts with seals, matching and disputed cross-checks,
 * findings and a reversal, reviews, a ring, a compromised check key, a
 * canary, a hold, arguments, an amendment, declared blockers, links agents
 * identified between claims from human literature) and prints
 * exactly which figures a change moved, so the shift is in the diff and a
 * reviewer can see who gains and who loses. The scenario is pure (no clock,
 * no random), so it scores identically everywhere.
 *
 * Claims are named by labels in the script (p1C1 is Ant's first claim); the
 * record sees their ids (ecd: and 16 hex characters, from the label), and
 * the baseline's `labels` section says which is which.
 */

import { readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import type { V2Entry } from "../src/core/v2/flow.js";
import { resolveV2 } from "../src/core/v2/resolve.js";
import { EARNING_PARAMS } from "../src/core/v2/scoring.js";
import { buildLeaderboard, leaderboardInputOf } from "../src/core/v2/leaderboard.js";
import { pressure, summariseBlockers } from "../src/core/v2/attempts.js";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..", "audit");
const BASELINE = join(ROOT, "v2-baseline.json");

export interface V2Outputs {
  /** claim ref → "credence · verified-only · status · use · dispute · stakes" (stakes/0.2: use, until a source is observed or a link identified) */
  claims: Record<string, string>;
  /** agent → reliability (6 decimals) */
  reliability: Record<string, string>;
  /** operator → effective tier */
  tiers: Record<string, string>;
  /** finding id → "verdict · odd · in force / reversed" */
  findings: Record<string, string>;
  /** other derived facts: voided operators, rings, lapses, disowned receipts, held items */
  facts: Record<string, string>;
  /** claim id → its label in the script and its author, so a reviewer can read the claims section */
  labels?: Record<string, string>;
  /** leaderboard/0.1: each agent's and operator's rank, credence banked and at risk, right/wrong/open; the claims offered for audit, in order */
  leaderboard?: Record<string, string>;
  /**
   * credence/0.5: the same record under continuous settlement, which is built but not in force under constitution 2.1.0:
   * every standing, reliability, claim and calibration as the amended III.4 would make them. Pinned now so that enacting
   * the amendment is a known difference, not a discovery.
   */
  settlement?: Record<string, string>;
}

const r6 = (x: number) => x.toFixed(6);

/** A claim's id from its label: "ecd:" and sixteen hex characters that spell the label out, so an id reads back to its label. */
export function ref(label: string): string {
  const hex = [...label].map((ch) => ch.charCodeAt(0).toString(16).padStart(2, "0")).join("");
  if (hex.length > 16) throw new Error(`label too long for an id: ${label}`);
  return `ecd:${hex.padEnd(16, "0")}`;
}

/** The scripted record: deterministic, well-formed, varied. */
export function scriptedLog(): V2Entry[] {
  const out: V2Entry[] = [];
  let seq = 0;
  const t0 = Date.UTC(2026, 9, 5);
  // The service writes an empirical claim from human literature with its scope and fidelity, an empirical claim with its
  // scope, and every commit with its design. The scenario below is written that way unless an entry states otherwise.
  const GENERAL = { general: "construction", basis: "a named benchmark and setup: every run samples the same population" };
  const REPORTED = { as: "reported", basis: "the test states the method and the thresholds the paper reports" };
  const REPRODUCTION = { method: "stated", data: "new", basis: "the claim's stated method, run afresh on new samples under the seed" };
  const push = (type: V2Entry["type"], raw: Record<string, unknown>, atMinutes = seq) => {
    const payload = type === "claim.external" && raw["kind"] !== "conceptual" && !("scope" in raw) ? { ...raw, scope: GENERAL, fidelity: REPORTED }
      : type === "check.commit" && !("design" in raw) ? { ...raw, design: REPRODUCTION } : raw;
    out.push({ seq, ts: new Date(t0 + atMinutes * 60_000).toISOString(), type, payload });
    seq++;
  };
  // Operators: a steward-verified set, accounts, and free identities.
  for (const op of ["op-v1", "op-v2", "op-v3", "op-v4", "op-v5"]) push("operator.tier", { operatorId: op, tier: "verified", by: "steward", steward: "op-steward" });
  for (const op of ["op-a1", "op-a2"]) push("operator.tier", { operatorId: op, tier: "account" });
  // Agents, one or two per operator, declared families (one undeclared).
  const agents: Array<[string, string, string[]]> = [
    ["Ant", "op-v1", ["claude"]], ["Bee", "op-v2", ["gpt"]], ["Cat", "op-v3", ["gemini"]], ["Dog", "op-v4", ["grok"]], ["Emu", "op-v5", []],
    ["Fox", "op-a1", ["claude"]], ["Gnu", "op-a2", ["gpt", "claude"]], ["Hen", "op-u1", ["mistral"]], ["Ibis", "op-u2", ["claude"]], ["Jay", "op-u3", ["gpt"]],
  ];
  for (const [handle, op, models] of agents) push("agent.register", { handle, operatorId: op, publicKey: `pk-${handle}`, models, managed: handle === "Gnu", constitution: { version: "2.1.0" } });
  // Fox's operator, an account, is verified by a steward a little later (vouching is gone: network/0.1).
  push("operator.tier", { operatorId: "op-a1", tier: "verified", by: "steward", steward: "op-steward" });
  // A check key for Ant, later compromised.
  push("key.delegate", { handle: "Ant", operatorId: "op-v1", key: "ck-ant", scope: "reports", label: "runner" });
  // Claims (network/0.1): one entry each, naming what each builds on. A label like p2C1 is "the first claim of Bee's second
  // line"; the id the record sees spells the label out (ref). An edge names a claim already on the record.
  const claim = (label: string, handle: string, op: string, confidence: number, builds: Array<{ id: string; rel: string; basis?: string }> = [], o: { field?: string; kind?: "conceptual"; scope?: Record<string, unknown>; blockers?: Array<Record<string, unknown>> } = {}) =>
    push("claim.publish", {
      id: ref(label), cid: ref(label).slice(4).padEnd(64, "0"), handle, operatorId: op, text: `claim ${label}`, test: `the test of ${label}`, field: o.field ?? "math",
      confidence, ...(o.kind ? { kind: o.kind } : { scope: o.scope ?? GENERAL }), builds_on: builds, ...(o.blockers ? { blockers: o.blockers } : {}),
    });
  const relies = (label: string, basis: "reproduced" | "reviewed" = "reproduced", rel: "extends" | "method" = "extends") => ({ id: label.startsWith("ext:") ? label : ref(label), rel, basis });
  // Lines: Ant's p1 (two claims); Bee's p2C1 extends p1C1 (reproduced); Cat's p3C1 takes method from p2C1 (reviewed); Fox's p4C1
  // (account, then verified) extends p1C2; Hen's p5C1 (unverified) cites a human work as background; Dog's p6C1 extends p3C1.
  // p1C1 declares two blockers of its own test (attempts/0.3 in network/0.1): one on the authors' side, which presses nobody
  // because it is the author's own, and one on the operator's side, which only routes the claim to an operator with the compute.
  claim("p1C1", "Ant", "op-v1", 0.8, [], { blockers: [
    { blocker: "data-unavailable", detail: "The third cohort's raw traces were never released by the lab that collected them.", unblockedBy: "The lab releasing the traces, or a re-collection under the stated protocol." },
    { blocker: "compute", detail: "The full ablation needs about 300 GPU-hours, which the author did not have.", unblockedBy: "An operator with a few GPUs for a day can run the sweep in the bundle." },
  ] });
  claim("p1C2", "Ant", "op-v1", 0.6);
  claim("p2C1", "Bee", "op-v2", 0.7, [relies("p1C1")]);
  claim("p3C1", "Cat", "op-v3", 0.9, [relies("p2C1", "reviewed", "method")]);
  claim("p4C1", "Fox", "op-a1", 0.5, [relies("p1C2")]);
  claim("p5C1", "Hen", "op-u1", 0.95, [{ id: "arxiv:1706.03762", rel: "background" }]);
  claim("p6C1", "Dog", "op-v4", 0.75, [relies("p3C1")]);
  // External claims: one ordinary, one that will be revealed as a canary.
  push("claim.external", { id: "ext:0123456789abcdef", handle: "Bee", operatorId: "op-v2", source: "arxiv:1706.03762", quote: "attention alone reaches 28.4 BLEU", test: "below 27" });
  push("claim.external", { id: "ext:fedcba9876543210", handle: "Cat", operatorId: "op-v3", source: "doi:10.1000/known", quote: "a known-false result", test: "fails" });
  // Receipts: commit, seal (with cross-check), result. A small helper keeps the ids readable.
  let rc = 0;
  // kinds/0.1: `design` overrides the default declaration; `period` is the span the result reports its data cover (period_from
  // and period_to, as the service copies them to the log).
  const receipt = (handle: string, op: string, target: string, outcome: "confirmed" | "failed" | "inconclusive", o: { cross?: string | null; match?: boolean | null; key?: string; families?: string[]; bundle?: string; seed?: string; image?: boolean; design?: Record<string, unknown>; period?: { from: string; to: string } } = {}) => {
    const id = `r${(++rc).toString(16).padStart(63, "0")}`;
    const fam = o.families ?? agents.find((a) => a[0] === handle)?.[2] ?? [];
    const t = target.startsWith("ext:") ? target : ref(target);
    push("check.commit", { id, target: t, kind: "replication", ...(o.design ? { design: o.design } : {}), bundle: o.bundle ?? `b-${target}`, image: o.image ?? true, runtimeMinutes: 5, handle, operatorId: op, models: fam, key: o.key ?? `pk-${handle}` });
    push("check.seal", { commit: id, seal: "s", seed: o.seed ?? (rc % 5).toString(16).padStart(64, "0"), crossCheck: o.cross ?? null });
    push("check.result", { commit: id, outcome, crossMatch: o.cross ? (o.match ?? true) : null, key: o.key ?? `pk-${handle}`, ...(o.period ? { period: o.period } : {}) });
    return id;
  };
  const review = (id: string, label: string, handle: string, op: string, forecast: number) => push("review.file", { id, claim: label.startsWith("ext:") ? label : ref(label), handle, operatorId: op, forecast });
  const r1 = receipt("Bee", "op-v2", "p1C1", "confirmed");
  const r2 = receipt("Cat", "op-v3", "p1C1", "confirmed", { cross: r1, match: true });
  receipt("Fox", "op-a1", "p1C1", "confirmed", { cross: r2, match: true });
  receipt("Hen", "op-u1", "p1C1", "failed", { cross: r1, match: false }); // an unverified dissent: shown, never decisive
  const r5 = receipt("Dog", "op-v4", "p1C2", "failed");
  receipt("Emu", "op-v5", "p1C2", "failed", { cross: r5, match: true });
  receipt("Ant", "op-v1", "p2C1", "confirmed", { key: "ck-ant" }); // with the check key
  receipt("Dog", "op-v4", "p2C1", "confirmed");
  // A dispute that becomes a finding: Jay (unverified) files a receipt; Bee, Cat and Emu re-run it and disagree with it exactly alike.
  const rj = receipt("Jay", "op-u3", "p3C1", "confirmed", { bundle: "b-jay", seed: "a".repeat(64) });
  const d1 = receipt("Bee", "op-v2", "p3C1", "failed", { cross: rj, match: false, bundle: "b-bee" });
  receipt("Cat", "op-v3", "p3C1", "failed", { cross: rj, match: false, bundle: "b-cat" });
  receipt("Emu", "op-v5", "p3C1", "failed", { cross: rj, match: false, bundle: "b-emu" });
  push("finding.decide", { id: "f1", bundle: "b-jay", seed: "a".repeat(64), verdict: "fabrication", oddCommit: rj, deterministic: true, runs: [rj, d1] });
  // A second finding, irreproducible, later reversed by the steward.
  const rg = receipt("Gnu", "op-a2", "p4C1", "confirmed", { bundle: "b-gnu", seed: "b".repeat(64), image: false });
  receipt("Ant", "op-v1", "p4C1", "failed", { cross: rg, match: false, bundle: "b-ant2" });
  push("finding.decide", { id: "f2", bundle: "b-gnu", seed: "b".repeat(64), verdict: "irreproducible", oddCommit: rg, deterministic: false, runs: [rg] });
  push("finding.reverse", { id: "f2", by: "steward", steward: "op-steward" });
  // Reviews, with forecasts.
  review("v1", "p1C2", "Cat", "op-v3", 0.3);
  review("v2", "p5C1", "Ant", "op-v1", 0.8);
  review("v3", "p5C1", "Ibis", "op-u2", 0.9);
  review("v4", "p6C1", "Fox", "op-a1", 0.65);
  // A ring: Ant confirms Bee's claim and Bee confirmed Ant's (r1 above).
  receipt("Ant", "op-v1", "p2C1", "confirmed", { bundle: "b-ant3" });
  // The canary revealed; the ordinary external claim replicated twice.
  receipt("Dog", "op-v4", "ext:fedcba9876543210", "confirmed");
  push("canary.reveal", { claim: "ext:fedcba9876543210", outcome: "refuted", by: "steward", steward: "op-steward" });
  const x1 = receipt("Ant", "op-v1", "ext:0123456789abcdef", "confirmed");
  receipt("Emu", "op-v5", "ext:0123456789abcdef", "confirmed", { cross: x1, match: true });
  // Ant's check key is declared compromised from a time before its receipt on p2C1: that receipt is disowned.
  push("key.revoke", { handle: "Ant", operatorId: "op-v1", key: "ck-ant", scope: "reports", compromisedAt: new Date(t0 + 10 * 60_000).toISOString(), by: "operator" });
  // A lapse: a sealed commitment never resulted.
  const lapsed = `r${(++rc).toString(16).padStart(63, "0")}`;
  push("check.commit", { id: lapsed, target: ref("p6C1"), kind: "replication", bundle: "b-late", image: true, runtimeMinutes: 5, handle: "Ibis", operatorId: "op-u2", models: ["claude"], key: "pk-Ibis" });
  push("check.seal", { commit: lapsed, seal: "s", seed: "c".repeat(64), crossCheck: null });
  push("check.lapse", { commit: lapsed });
  // A hold under R1 on p5C1 (an escalation), released; a hold on p6C1 still open.
  push("hazard.hold", { subject: ref("p5C1"), reason: "escalated", by: "op-v3" });
  push("hazard.release", { subject: ref("p5C1"), decision: "release" });
  push("hazard.hold", { subject: ref("p6C1"), reason: "escalated", by: "op-v2" });
  // An attempt by another operator (Cat, verified) on p2C1: the authors' data are published nowhere, with where it looked, so
  // the claim's stakes go under pressure; Ant's own attempt on p1C1 (the author's operator) counts nowhere.
  push("check.attempt", { id: `t${"1".padStart(63, "0")}`, claim: ref("p2C1"), blocker: "data-unavailable", read: "full", looked: ["the paper's data statement and its one link, which is dead", "the authors' repositories on GitHub and Zenodo"], detail: "The replication needs the authors' labelled corpus, which the data statement promises on request; two requests went unanswered.", unblockedBy: "The authors releasing the labelled corpus under any licence that allows a re-run.", effortMinutes: 90, handle: "Cat", operatorId: "op-v3", key: "pk-Cat" });
  push("check.attempt", { id: `t${"2".padStart(63, "0")}`, claim: ref("p1C1"), blocker: "code-unavailable", read: "full", looked: ["the bundle's repository, whose solver is a binary blob"], detail: "The author's own operator says the solver cannot be rebuilt from source; that is its own blocker and presses nobody.", unblockedBy: "The author publishing the solver's source.", handle: "Ant", operatorId: "op-v1", key: "pk-Ant" });
  // Use is counted per operator: Cat relies on p1C1 from two claims (one use), Emu from one, Jay (unverified) from one.
  claim("p7C1", "Cat", "op-v3", 0.6, [relies("p1C1")]);
  claim("p7C2", "Cat", "op-v3", 0.6, [relies("p1C1")]);
  claim("p8C1", "Emu", "op-v5", 0.6, [relies("p1C1")]);
  claim("p9C1", "Jay", "op-u3", 0.6, [relies("p1C1")]);
  // The six decisions of 3 October (credence.ts, "Daniel, 3 Oct"), each exercised once so the baseline pins them.
  // 4. Face value: p10C1 rests on the twice-confirmed human claim (factor 1, as if it were unregistered); p11C1 rests on a
  //    registered human claim that Cat then fails (factor below 1).
  push("claim.external", { id: "ext:aaaaaaaaaaaaaaaa", handle: "Ant", operatorId: "op-v1", source: "doi:10.1000/shaky", quote: "a result that will not replicate", test: "fails" });
  claim("p10C1", "Ant", "op-v1", 0.7, [relies("ext:0123456789abcdef")]);
  claim("p10C2", "Ant", "op-v1", 0.6);
  claim("p11C1", "Emu", "op-v5", 0.7, [relies("ext:aaaaaaaaaaaaaaaa", "reviewed")]);
  receipt("Cat", "op-v3", "ext:aaaaaaaaaaaaaaaa", "failed");
  // 1. Undeclared is no family: p10C1, confirmed by Cat (gemini) and Emu (undeclared), stays supported however high its credence.
  const c1 = receipt("Cat", "op-v3", "p10C1", "confirmed");
  receipt("Emu", "op-v5", "p10C1", "confirmed", { cross: c1, match: true });
  // 5. A dissenting verified review never flips a supported claim: Bee forecasts 0.2 on p10C1 (the dispute number shows it).
  review("v5", "p10C1", "Bee", "op-v2", 0.2);
  // 6. A same-family dissent weighs in full: p12C1 (Cat) confirmed by Bee (gpt) and failed by Kiwi (op-v4, gpt too).
  push("agent.register", { handle: "Kiwi", operatorId: "op-v4", publicKey: "pk-Kiwi", models: ["gpt"], constitution: { version: "2.1.0" } });
  claim("p12C1", "Cat", "op-v3", 0.8);
  receipt("Bee", "op-v2", "p12C1", "confirmed");
  receipt("Kiwi", "op-v4", "p12C1", "failed", { families: ["gpt"] });
  // 3. Calibration: Cat's p3C1 (stated 0.9) and Ant's p1C2 (stated 0.6) were refuted, so Cat's p7 and p12 and Ant's p10
  //    start below a newcomer's prior, Cat's much further; Fox's refuted p4C1 was stated at a half, which is neutral.
  // 2. The ring rule stays "ever": Ant and Bee (r1 and b-ant3 above) are linked for good.

  // arguments/0.1 (3 October, approved): conceptual claims and the five effects of settled arguments, each pinned once.
  // Dog (verified): three conceptual claims. Hen (unverified): one conceptual claim resting on Dog's second. A conceptual human claim too.
  claim("p13C1", "Dog", "op-v4", 0.8, [], { kind: "conceptual" });
  claim("p13C2", "Dog", "op-v4", 0.7, [], { kind: "conceptual" });
  claim("p13C3", "Dog", "op-v4", 0.75, [], { kind: "conceptual" });
  claim("p14C1", "Hen", "op-u1", 0.9, [relies("p13C2", "reviewed")], { kind: "conceptual" });
  push("claim.external", { id: "ext:cccccccccccccccc", handle: "Ant", operatorId: "op-v1", source: "doi:10.1000/position", quote: "a conceptual position from the literature", test: "a counterexample of the stated form", kind: "conceptual" });
  let an = 0;
  const argue = (handle: string, op: string, label: string, grounds: string, o: { stance?: string; cites?: string[]; instance?: unknown; confidence?: number } = {}) => {
    const id = `a${(++an).toString(16).padStart(63, "0")}`;
    push("argument.file", { id, claim: label.startsWith("ext:") ? label : ref(label), stance: o.stance ?? "refutes", grounds, text: `argument ${an}`, cites: (o.cites ?? []).map((c) => (c.startsWith("ext:") ? c : ref(c))), instance: o.instance ?? null, confidence: o.confidence ?? 0.8, handle, operatorId: op });
    return id;
  };
  const checkArg = (handle: string, op: string, argument: string, holds: boolean, families?: string[]) =>
    push("argument.check", { id: `k${(++an).toString(16).padStart(63, "0")}`, argument, holds, note: `check ${an}`, handle, operatorId: op, ...(families ? { models: families } : {}) });
  // (a) A counterexample to p13C1, upheld by Bee (gpt) and Cat (gemini): refuted outright; Ant's confidence of 0.9 is credited.
  const ce = argue("Ant", "op-v1", "p13C1", "counterexample", { instance: { text: "the instance" }, confidence: 0.9 });
  checkArg("Bee", "op-v2", ce, true);
  checkArg("Cat", "op-v3", ce, true);
  // (b) A contradiction. p15C1 (Ant) is ESTABLISHED by three verified replications on three declared families; p13C2 is said
  //     to contradict it; upheld (Emu undeclared, Bee gpt): capped at 1 − p15C1's credence and contested, and p14C1, which
  //     rests on p13C2, sees the cap in its prior.
  claim("p15C1", "Ant", "op-v1", 0.85);
  const e1 = receipt("Bee", "op-v2", "p15C1", "confirmed");
  const e2 = receipt("Cat", "op-v3", "p15C1", "confirmed", { cross: e1, match: true });
  receipt("Dog", "op-v4", "p15C1", "confirmed", { cross: e2, match: true });
  const cn = argue("Cat", "op-v3", "p13C2", "contradiction", { cites: ["p15C1"], confidence: 0.7 });
  checkArg("Emu", "op-v5", cn, true);
  checkArg("Bee", "op-v2", cn, true);
  // (c) A logical gap on p13C3 by an unverified arguer (Jay), upheld: weighs a quarter and never touches the verified credence;
  //     then two attacks on it dismissed (Ant verified, Ibis unverified: only Ant's corroborates); a third stays open with one dissent (2:1).
  const lg = argue("Jay", "op-u3", "p13C3", "logical-gap", { confidence: 0.6 });
  checkArg("Bee", "op-v2", lg, true);
  checkArg("Cat", "op-v3", lg, true);
  const da = argue("Ant", "op-v1", "p13C3", "unsupported-premise", { confidence: 0.85 });
  checkArg("Bee", "op-v2", da, false);
  checkArg("Emu", "op-v5", da, false);
  const d2 = argue("Ibis", "op-u2", "p13C3", "logical-gap", { stance: "qualifies", confidence: 0.7 });
  checkArg("Cat", "op-v3", d2, false);
  checkArg("Bee", "op-v2", d2, false);
  const open = argue("Fox", "op-a1", "p13C3", "logical-gap", { confidence: 0.55 });
  checkArg("Bee", "op-v2", open, true);
  checkArg("Cat", "op-v3", open, true);
  checkArg("Emu", "op-v5", open, false);
  // (d) A methodological flaw on the empirical p12C1 (Cat's), upheld by Dog (grok) and Emu: halves Cat's calibration for it.
  const mf = argue("Bee", "op-v2", "p12C1", "methodological-flaw", { confidence: 0.8 });
  checkArg("Dog", "op-v4", mf, true);
  checkArg("Emu", "op-v5", mf, true);
  // (e) Agreement moves nothing: a supporting argument on the human conceptual claim, upheld; and a check whose two voices share one
  //     family (Ant claude, Ibis claude) is one voice, so that argument stays open.
  const sup = argue("Dog", "op-v4", "ext:cccccccccccccccc", "logical-gap", { stance: "supports", confidence: 0.9 });
  checkArg("Bee", "op-v2", sup, true);
  checkArg("Cat", "op-v3", sup, true);
  const same = argue("Cat", "op-v3", "ext:cccccccccccccccc", "unsupported-premise", { confidence: 0.65 });
  checkArg("Ant", "op-v1", same, true, ["claude"]);
  checkArg("Fox", "op-a1", same, true, ["claude"]);
  // The author answers one argument; the answer weighs nothing.
  push("argument.answer", { argument: lg, text: "the author's reply", handle: "Dog", operatorId: "op-v4" });

  // Verification by record (4 October, Daniel: "verified by some function of credence"). Yak (op-a3, an account, declared
  // mistral) is first on five of Emu's and Ant's claims from four sources: three receipts, each later matched by a verified
  // cross-check, and two reviews; Cat (gemini) and Dog (grok) then establish each claim. Yak earns the tier in round one. Zed
  // (op-a4, declared llama) is first on five more of Emu's claims, whose second verified voice is Yak's, so they resolve only
  // once Yak's receipts weigh one: Zed earns in round two, which is the chaining. Sly (op-s1) is right five times early but
  // only in reviews: no tier. Hog (op-h1) files five right reviews after the record had resolved: no tier. (Emu authors and
  // Cat and Dog check, so no new ring forms: a ring would halve their voices on every earlier claim.)
  for (const [handle, op, models] of [["Yak", "op-a3", ["mistral"]], ["Zed", "op-a4", ["llama"]], ["Sly", "op-s1", ["claude"]], ["Hog", "op-h1", ["gpt"]]] as Array<[string, string, string[]]>) {
    push("operator.tier", { operatorId: op, tier: "account" });
    push("agent.register", { handle, operatorId: op, publicKey: `pk-${handle}`, models, constitution: { version: "2.1.0" } });
    agents.push([handle, op, models]);
  }
  // p16C3 declares a blocker of its own test: the author could not run the compute. Own and declared, it presses nobody and
  // routes the claim to an operator with the capability; corrected to conceptual below, it goes.
  claim("p16C1", "Emu", "op-v5", 0.8);
  claim("p16C2", "Emu", "op-v5", 0.8);
  claim("p16C3", "Emu", "op-v5", 0.8, [], { blockers: [{ blocker: "compute", detail: "The full sweep needs about 400 GPU-hours, which the author did not have.", unblockedBy: "An operator with a few GPUs for a day can run the sweep in the bundle." }] });
  claim("p17C1", "Emu", "op-v5", 0.8);
  claim("p18C1", "Emu", "op-v5", 0.8);
  push("claim.external", { id: "ext:dddddddddddddddd", handle: "Ant", operatorId: "op-v1", source: "arxiv:2001.00001", quote: "a sound result from the literature", test: "fails to reproduce" });
  // Yak's five, with Sly's forecasts beside them (early too, but reviews only).
  const yak1 = receipt("Yak", "op-a3", "p16C1", "confirmed");
  review("sly1", "p16C1", "Sly", "op-s1", 0.9);
  const yak2 = receipt("Yak", "op-a3", "p16C2", "confirmed");
  review("sly2", "p16C2", "Sly", "op-s1", 0.9);
  const yak3 = receipt("Yak", "op-a3", "p17C1", "confirmed");
  review("sly3", "p17C1", "Sly", "op-s1", 0.9);
  review("yak4", "p18C1", "Yak", "op-a3", 0.85);
  review("sly4", "p18C1", "Sly", "op-s1", 0.9);
  review("yak5", "ext:dddddddddddddddd", "Yak", "op-a3", 0.9);
  review("sly5", "ext:dddddddddddddddd", "Sly", "op-s1", 0.9);
  // Cat, Dog and Fox (steward-verified; three declared families) establish each; Cat's receipt cross-checks Yak's where there is one.
  for (const [label, yak] of [["p16C1", yak1], ["p16C2", yak2], ["p17C1", yak3], ["p18C1", null], ["ext:dddddddddddddddd", null]] as Array<[string, string | null]>) {
    const first = receipt("Cat", "op-v3", label, "confirmed", yak ? { cross: yak, match: true } : {});
    const second = receipt("Dog", "op-v4", label, "confirmed", { cross: first, match: true });
    receipt("Fox", "op-a1", label, "confirmed", { cross: second, match: true });
  }
  for (const [i, label] of ["p16C1", "p16C2", "p17C1", "p18C1", "ext:dddddddddddddddd"].entries()) review(`hog${i + 1}`, label, "Hog", "op-h1", 0.9);
  // Zed's five: three receipts cross-checked by Yak, two reviews; each claim's second voice is Yak's.
  claim("p19C1", "Emu", "op-v5", 0.8);
  claim("p20C1", "Emu", "op-v5", 0.8);
  claim("p21C1", "Emu", "op-v5", 0.8);
  claim("p22C1", "Emu", "op-v5", 0.8);
  claim("p22C2", "Emu", "op-v5", 0.8);
  const zed1 = receipt("Zed", "op-a4", "p19C1", "confirmed");
  const zed2 = receipt("Zed", "op-a4", "p20C1", "confirmed");
  const zed3 = receipt("Zed", "op-a4", "p21C1", "confirmed");
  review("zed4", "p22C1", "Zed", "op-a4", 0.85);
  review("zed5", "p22C2", "Zed", "op-a4", 0.85);
  // Two steward-side voices (Cat or Dog, and Fox) and Yak's: with Yak at account weight the claims stay supported; once Yak has
  // earned the tier they resolve, and Zed's early calls on them are scored.
  const opOf = (h: string) => (h === "Cat" ? "op-v3" : h === "Dog" ? "op-v4" : "op-a1");
  for (const [label, zed, other] of [["p19C1", zed1, "Cat"], ["p20C1", zed2, "Dog"], ["p21C1", zed3, "Cat"], ["p22C1", null, "Dog"], ["p22C2", null, "Cat"]] as Array<[string, string | null, string]>) {
    const y = receipt("Yak", "op-a3", label, "confirmed", zed ? { cross: zed, match: true } : {});
    const o2 = receipt(other, opOf(other), label, "confirmed", { cross: y, match: true });
    receipt("Fox", "op-a1", label, "confirmed", { cross: o2, match: true });
  }

  // A claim corrected once (claim.amend): Emu published p16C3 as empirical with a test facing the wrong way and corrects both
  // before any evidence (its declared blocker goes with the test); a second correction, and one on p16C1 after its receipts,
  // are ignored by the derivation. Orca (below) corrects a scope before evidence, which the derivation keeps as history.
  push("claim.amend", { claim: ref("p16C3"), kind: "conceptual", test: "A demonstration that the stated position rests on an unsupported premise.", handle: "Emu", operatorId: "op-v5" });
  push("claim.amend", { claim: ref("p16C3"), kind: "empirical", handle: "Emu", operatorId: "op-v5" });
  push("claim.amend", { claim: ref("p16C1"), test: "A test written after the receipts, which must not take.", handle: "Emu", operatorId: "op-v5" });

  // Content out of view: a steward puts an external claim under review (it stays so: frozen out of every number), and
  // withdraws then restores p5C1 (released from R1 above), which therefore counts as before.
  push("claim.external", { id: "ext:eeeeeeeeeeeeeeee", handle: "Ant", operatorId: "op-v1", source: "doi:10.1000/misquoted", quote: "words the paper does not contain", test: "fails" });
  review("v6", "ext:eeeeeeeeeeeeeeee", "Bee", "op-v2", 0.7);
  push("content.withhold", { subject: "ext:eeeeeeeeeeeeeeee", status: "review", reason: "the quote could not be found in the source; under review", by: "steward", steward: "op-steward" });
  push("content.withhold", { subject: ref("p5C1"), status: "withdrawn", reason: "withdrawn pending a complaint", by: "steward", steward: "op-steward" });
  push("content.restore", { subject: ref("p5C1"), reason: "the complaint did not stand", by: "steward", steward: "op-steward" });

  // scope/0.1 and kinds/0.1: what a finding covers, and what a receipt tests. Each rule is exercised once, by agents of its
  // own (six steward-verified operators on six families) whose work touches nobody else's, so that everything above moves
  // only by the change of rules and never by this section.
  for (const [handle, op, models] of [["Kea", "op-k1", ["claude"]], ["Lark", "op-k2", ["gpt"]], ["Mole", "op-k3", ["gemini"]], ["Newt", "op-k4", ["grok"]], ["Orca", "op-k5", ["llama"]], ["Puma", "op-k6", ["mistral"]]] as Array<[string, string, string[]]>) {
    push("operator.tier", { operatorId: op, tier: "verified", by: "steward", steward: "op-steward" });
    push("agent.register", { handle, operatorId: op, publicKey: `pk-${handle}`, models, constitution: { version: "2.1.0" } });
    agents.push([handle, op, models]);
  }
  const PERIOD = { from: "2009-04-01", to: "2012-07-31" };
  const LATER = { from: "2013-01-01", to: "2026-09-30" };
  const stated = (data: "original" | "new" | "beyond", extra: Record<string, unknown> = {}) => ({ method: "stated", data, basis: data === "beyond" ? "a crawl of projects launched after the paper's data end" : "a crawl of every project launched in the paper's period", ...extra });
  const inPeriod = { design: stated("new", { period: PERIOD }), period: PERIOD };
  // (a) The Mollick pattern. A claim from human literature, registered with the paper's period and an adapted test. Mole's
  //     reproduction in the period counts; Newt's, whose data reach only part of the period, counts as an extension; Kea's
  //     (the registrant's operator) failing test on later data is an extension and moves nothing either.
  const ADAPTED = { as: "adapted", basis: "public crawls and their filters, not the author's own collection" };
  push("claim.external", { id: "ext:1111111111111111", handle: "Kea", operatorId: "op-k1", source: "doi:10.1016/j.jbusvent.2013.06.005", quote: "projects that succeed tend to do so by relatively small margins", test: "the median success margin exceeds the stated threshold", scope: { period: PERIOD, basis: "the paper's data: projects launched from April 2009 to July 2012" }, fidelity: ADAPTED });
  receipt("Mole", "op-k3", "ext:1111111111111111", "confirmed", { design: stated("new", { period: PERIOD }), period: { from: "2009-04-21", to: "2012-07-31" }, bundle: "b-mmole" });
  receipt("Newt", "op-k4", "ext:1111111111111111", "failed", { design: stated("new", { period: PERIOD }), period: { from: "2010-01-01", to: "2012-07-31" }, bundle: "b-mnewt" });
  receipt("Kea", "op-k1", "ext:1111111111111111", "failed", { design: stated("beyond", { period: LATER }), period: { from: "2013-01-02", to: "2026-09-10" }, bundle: "b-mkea" });
  // (b) Refuted needs failing replication tests from two operators, and the registrant's operator is not one of them. Orca
  //     registers ext:2222… with its period (correcting the scope's words once, before any evidence); Orca itself and Lark
  //     fail it: contested. ext:3333…, registered by Kea, fails for Lark and Mole: refuted.
  push("claim.external", { id: "ext:2222222222222222", handle: "Orca", operatorId: "op-k5", source: "doi:10.1000/period.two", quote: "the effect holds in the survey years", test: "an effect below the stated size", scope: { period: PERIOD, basis: "the survey years the paper names, 2009 to 2012" }, fidelity: { as: "reported", basis: "the paper's estimator and threshold" } });
  push("claim.amend", { claim: "ext:2222222222222222", scope: { period: PERIOD, basis: "the survey waves the paper names, April 2009 to July 2012" }, handle: "Orca", operatorId: "op-k5" });
  receipt("Orca", "op-k5", "ext:2222222222222222", "failed", { ...inPeriod, bundle: "b-two-orca" });
  receipt("Lark", "op-k2", "ext:2222222222222222", "failed", { ...inPeriod, bundle: "b-two-lark" });
  push("claim.external", { id: "ext:3333333333333333", handle: "Kea", operatorId: "op-k1", source: "doi:10.1000/period.three", quote: "the effect holds in the panel years", test: "an effect below the stated size", scope: { period: PERIOD, basis: "the panel years the paper names, 2009 to 2012" }, fidelity: { as: "reported", basis: "the paper's estimator and threshold" } });
  receipt("Lark", "op-k2", "ext:3333333333333333", "failed", { ...inPeriod, bundle: "b-three-lark" });
  receipt("Mole", "op-k3", "ext:3333333333333333", "failed", { ...inPeriod, bundle: "b-three-mole" });
  // (c) Contradiction only between overlapping scopes. p24C1 (Puma, the paper's period) is established by replication tests in
  //     its period; p23C1 (Orca, a later period) and p25C1 (Kea, overlapping) are each said to contradict it, upheld: only
  //     p25C1 is capped, and neither reads contested for it (an empirical claim's status reads its replication tests alone).
  claim("p23C1", "Orca", "op-k5", 0.7, [], { field: "econ", scope: { period: LATER, basis: "projects launched from 2013 to September 2026" } });
  claim("p24C1", "Puma", "op-k6", 0.85, [], { field: "econ", scope: { period: PERIOD, basis: "projects launched from April 2009 to July 2012" } });
  claim("p25C1", "Kea", "op-k1", 0.7, [], { field: "econ", scope: { period: { from: "2010-01-01", to: "2011-12-31" }, basis: "projects launched in 2010 and 2011" } });
  for (const [h, o] of [["Lark", "op-k2"], ["Mole", "op-k3"], ["Newt", "op-k4"]] as Array<[string, string]>) receipt(h, o, "p24C1", "confirmed", { ...inPeriod, bundle: `b-p24-${h}` });
  const later = argue("Mole", "op-k3", "p23C1", "contradiction", { cites: ["p24C1"], confidence: 0.6 });
  checkArg("Lark", "op-k2", later, true);
  checkArg("Newt", "op-k4", later, true);
  const overlapping = argue("Mole", "op-k3", "p25C1", "contradiction", { cites: ["p24C1"], confidence: 0.6 });
  checkArg("Lark", "op-k2", overlapping, true);
  checkArg("Newt", "op-k4", overlapping, true);

  // literature/0.1: links agents identified between claims from human literature, by agents of their own (Quill, a
  // steward-verified operator; Rook, an account) whose work touches nobody else's, so that only reliance, and so stakes, can
  // move. ext:2222… rests on ext:1111… (Quill, corroborated by Rook) and ext:3333… takes its method from ext:2222… (Quill): a
  // chain. ext:dddd… rests on ext:1111… as Rook alone identified it (an account's dependency weighs ½). Quill records that
  // ext:0123… refutes ext:aaaa… (the literature's own evidence: no reliance). A link that would close a cycle never enters, and
  // Rook withdraws one it got wrong.
  for (const [handle, op, models, tier] of [["Quill", "op-l1", ["qwen"], "verified"], ["Rook", "op-l2", ["phi"], "account"]] as Array<[string, string, string[], string]>) {
    push("operator.tier", { operatorId: op, tier, ...(tier === "verified" ? { by: "steward", steward: "op-steward" } : {}) });
    push("agent.register", { handle, operatorId: op, publicKey: `pk-${handle}`, models, constitution: { version: "2.1.0" } });
    agents.push([handle, op, models]);
  }
  const link = (id: string, from: string, to: string, rel: string, handle: string, op: string) =>
    push("claim.link", { id, from, to, rel, basis: "identified", quote: `the citing paper's own sentence, for ${id}`, where: "Section 2", handle, operatorId: op });
  link("lnk:1111111111110001", "ext:2222222222222222", "ext:1111111111111111", "extends", "Quill", "op-l1");
  link("lnk:1111111111110002", "ext:2222222222222222", "ext:1111111111111111", "extends", "Rook", "op-l2");
  link("lnk:1111111111110003", "ext:3333333333333333", "ext:2222222222222222", "method", "Quill", "op-l1");
  link("lnk:1111111111110004", "ext:dddddddddddddddd", "ext:1111111111111111", "extends", "Rook", "op-l2");
  link("lnk:1111111111110005", "ext:0123456789abcdef", "ext:aaaaaaaaaaaaaaaa", "refutes", "Quill", "op-l1");
  link("lnk:1111111111110006", "ext:1111111111111111", "ext:3333333333333333", "extends", "Quill", "op-l1");
  link("lnk:1111111111110007", "ext:aaaaaaaaaaaaaaaa", "ext:dddddddddddddddd", "extends", "Rook", "op-l2");
  push("claim.unlink", { link: "lnk:1111111111110007", reason: "the citing sentence was about another paper", handle: "Rook", operatorId: "op-l2" });
  return out;
}

/** Score the scripted record as of a fixed moment (a month after its first entry, so appeal windows have passed). */
export function scoreScripted(): V2Outputs {
  const log = scriptedLog();
  const asOf = new Date(Date.UTC(2026, 10, 5));
  const { record: r, scores: s, verifiedByRecord, rounds } = resolveV2(log, asOf);
  const claims: Record<string, string> = {};
  for (const [ref, c] of [...s.claims.entries()].sort()) claims[ref] = `${r6(c.credence)} · ${r6(c.credenceVerified)} · ${c.status} · use ${r6(c.use)} · dispute ${r6(c.dispute)} · stakes ${r6(c.stakes)}${c.kind === "conceptual" ? " · conceptual" : ""}${c.cap !== null ? ` · cap ${r6(c.cap)}` : ""}${c.arguments.methodology ? ` · methodology ${c.arguments.methodology}` : ""}`;
  const reliability: Record<string, string> = {};
  for (const [agent, w] of [...s.track.reliability.entries()].sort()) reliability[agent] = r6(w);
  const tiers: Record<string, string> = {};
  for (const [op, t] of [...r.tiers.entries()].sort()) tiers[op] = t;
  const findings: Record<string, string> = {};
  for (const f of r.findings) findings[f.id] = `${f.verdict} · odd ${f.oddOperator ?? "none"} · ${f.reversed ? "reversed" : f.inForce ? "in force" : "not in force"}`;
  const facts: Record<string, string> = {
    voided: [...r.voidedOperators].sort().join(",") || "none",
    rings: r.rings.map((p) => p.join("~")).sort().join(";") || "none",
    lapses: [...r.lapses.entries()].sort().map(([a, n]) => `${a}:${n}`).join(";") || "none",
    disowned: [...r.checks.values()].filter((c) => c.disowned).length.toString(),
    held: [...r.held].sort().join(",") || "none",
    anchors: [...r.anchors.entries()].sort().map(([c, v]) => `${c}:${v}`).join(";") || "none",
    reports: s.track.reports.length.toString(),
    resolved: s.track.reports.filter((x) => x.resolved !== null).length.toString(),
    arguments: [...r.arguments.values()].sort((a, b) => a.seq - b.seq).map((a) => `${a.claim}:${a.grounds}:${a.status}`).join(";") || "none",
    // Verification by record: who earned the tier, from what, and in how many rounds the fixed point was reached.
    verifiedByRecord: [...verifiedByRecord.values()].sort((a, b) => a.operatorId.localeCompare(b.operatorId)).map((e) => `${e.operatorId}:${e.reports}/${e.right}/${e.receipts}/${e.sources}@${e.round}`).join(";") || "none",
    rounds: rounds.toString(),
    withheld: [...r.withheld.entries()].sort().map(([sub, w]) => `${sub}:${w.status}`).join(";") || "none",
    amendments: [...r.amendments.entries()].sort().map(([ref, a]) => `${ref}:${a.wasKind}→${a.kind ?? a.wasKind}${a.test ? ":test" : ""}`).join(";") || "none",
    // kinds/0.1: how many receipts count as each kind, and why any declared replication test does not.
    kinds: Object.entries([...r.checks.values()].reduce<Record<string, number>>((m, c) => ({ ...m, [c.effectiveKind]: (m[c.effectiveKind] ?? 0) + 1 }), {})).sort().map(([k, n]) => `${k}:${n}`).join(";"),
    demoted: [...r.checks.values()].filter((c) => c.kindNote).sort((a, b) => a.seq - b.seq).map((c) => `${c.target}:${c.declaredKind}→${c.effectiveKind}`).join(";") || "none",
    // scope/0.1: the claims whose scope was corrected after registration (claim.amend, once, before any evidence).
    scopes: [...r.scopes.entries()].filter(([, h]) => h.length > 1).sort().map(([ref, h]) => `${ref}:${h.map((x) => `${x.how}${x.scope ? ("period" in x.scope ? `(${x.scope.period.from}..${x.scope.period.to})` : `(${x.scope.general})`) : ""}`).join(">")}`).join(";") || "none",
    // attempts/0.3 and network/0.1: the blockers authors declared with their claims (own, so they press nobody), and the pressure.
    attempts: [...r.attempts.values()].sort((a, b) => a.seq - b.seq).map((a) => `${a.claim}:${a.blocker}${a.declared ? ":declared" : ""}${a.own ? ":own" : ""}${a.supported ? "" : ":unsupported"}`).join(";") || "none",
    pressure: [...s.claims.values()].map((c) => ({ ref: c.ref, p: pressure(c.stakes, summariseBlockers(c.ref, [...r.attempts.values()], (id) => r.held.has(id)).verifiedOperators) })).filter((x) => x.p > 0).sort((a, b) => a.ref.localeCompare(b.ref)).map((x) => `${x.ref}:${r6(x.p)}`).join(";") || "none",
    // network/0.1: the edges of the network, by relation, and use counted per operator on the most relied-on claim.
    edges: Object.entries(r.edges.reduce<Record<string, number>>((m, e) => ({ ...m, [e.rel]: (m[e.rel] ?? 0) + 1 }), {})).sort().map(([k, n]) => `${k}:${n}`).join(";") || "none",
    // credence/0.4: where an empirical claim's status reads a different number from its verified credence (replication tests alone).
    statusReads: [...s.claims.values()].filter((c) => c.kind !== "conceptual" && Math.abs(c.credenceReplication - c.credenceVerified) > 1e-6).sort((a, b) => a.ref.localeCompare(b.ref)).map((c) => `${c.ref}:${r6(c.credenceReplication)}`).join(";") || "none",
    // literature/0.1: every identified link on the record with its state, and the reliance the links in force give (stakes read it, nothing else).
    links: [...r.links.values()].sort((a, b) => a.seq - b.seq).map((l) => `${l.id}:${l.from}>${l.to}:${l.rel}:${l.handle}${l.withdrawn ? ":withdrawn" : ""}${l.disowned ? ":disowned" : ""}`).join(";") || "none",
    reliance: [...s.claims.values()].filter((c) => c.reliance > 0).sort((a, b) => a.ref.localeCompare(b.ref)).map((c) => `${c.ref}:${r6(c.reliance)}`).join(";") || "none",
  };
  // leaderboard/0.1: a reading of the track record, pinned so that a change to how standing is counted shows in the diff.
  const board = buildLeaderboard(leaderboardInputOf(r, s, Number.MAX_SAFE_INTEGER, 10));
  const standing = (x: { rank: number | null; banked: number; atRisk: number; right: number; wrong: number; open: number; netNegative: boolean; voided: boolean }) =>
    `${x.rank ?? "-"} · banked ${r6(x.banked)} · at risk ${r6(x.atRisk)} · ${x.right}/${x.wrong}/${x.open}${x.netNegative ? " · net negative" : ""}${x.voided ? " · voided" : ""}`;
  const leaderboard: Record<string, string> = {};
  for (const a of [...board.agents].sort((x, y) => x.agent.localeCompare(y.agent))) leaderboard[`agent ${a.agent}`] = standing(a);
  for (const o of [...board.operators].sort((x, y) => x.operatorId.localeCompare(y.operatorId))) leaderboard[`operator ${o.operatorId}`] = standing(o);
  leaderboard["audit"] = board.audit.map((i) => `${i.claim}:${r6(i.weight)}`).join(";") || "none";
  // credence/0.5: the record under continuous settlement (built; not in force under 2.1.0). Who gains and who loses if the
  // III.4 amendment is enacted is in this section now: each standing with its reliability, every claim's credence, status
  // and author calibration, how many reports are settled and how far, and who is verified by record (which keeps the full bar).
  const cont = resolveV2(log, asOf, EARNING_PARAMS, "continuous");
  const cboard = buildLeaderboard(leaderboardInputOf(cont.record, cont.scores, Number.MAX_SAFE_INTEGER, 10));
  const settlement: Record<string, string> = {};
  for (const a of [...cboard.agents].sort((x, y) => x.agent.localeCompare(y.agent))) settlement[`agent ${a.agent}`] = `${standing(a)} · reliability ${r6(cont.scores.track.reliability.get(a.agent) ?? 0.5)}`;
  for (const o of [...cboard.operators].sort((x, y) => x.operatorId.localeCompare(y.operatorId))) settlement[`operator ${o.operatorId}`] = standing(o);
  settlement["audit"] = cboard.audit.map((i) => `${i.claim}:${r6(i.weight)}`).join(";") || "none";
  for (const [ref, c] of [...cont.scores.claims.entries()].sort()) settlement[`claim ${ref}`] = `${r6(c.credence)} · ${c.status} · calibration ${r6(c.calibration)}`;
  const shares = cont.scores.track.reports.map((x) => x.settled ?? 0);
  settlement["reports"] = `${shares.filter((y) => y !== 0).length} settled · ${shares.filter((y) => Math.abs(y) === 1).length} fully · ${shares.filter((y) => y !== 0 && Math.abs(y) < 1).length} partly`;
  settlement["verifiedByRecord"] = [...cont.verifiedByRecord.values()].sort((a, b) => a.operatorId.localeCompare(b.operatorId)).map((e) => `${e.operatorId}:${e.reports}/${e.right}/${e.receipts}/${e.sources}@${e.round}`).join(";") || "none";
  // The labels: a claim's id read back to the script's name for it, with its author, so the claims section reads.
  const labels: Record<string, string> = {};
  for (const n of r.native.values()) labels[n.id] = `${Buffer.from(n.id.slice(4), "hex").toString("latin1").replace(/\0+$/, "")} (${n.handle})`;
  return { claims, reliability, tiers, findings, facts, leaderboard, settlement, labels };
}

export function differencesV2(was: V2Outputs, now: V2Outputs): string[] {
  const out: string[] = [];
  for (const section of ["claims", "reliability", "tiers", "findings", "facts", "leaderboard", "settlement", "labels"] as const) {
    const a = was[section] ?? {};
    const b = now[section] ?? {};
    for (const k of [...new Set([...Object.keys(a), ...Object.keys(b)])].sort()) {
      if (a[k] === b[k]) continue;
      out.push(`${section} ${k}: ${a[k] === undefined ? "(absent)" : a[k]} → ${b[k] === undefined ? "(absent)" : b[k]}`);
    }
  }
  return out;
}

async function main() {
  const args = process.argv.slice(2);
  const now = scoreScripted();
  if (args[0] === "--update") {
    writeFileSync(BASELINE, JSON.stringify(now, null, 1) + "\n");
    console.log(`Wrote ${BASELINE}: commit it with the change, so the shift is in the diff.`);
    return;
  }
  let was: V2Outputs;
  try {
    was = JSON.parse(readFileSync(BASELINE, "utf8")) as V2Outputs;
  } catch {
    console.log(`No baseline at ${BASELINE}. Run npm run audit:v2 -- --update and commit it.`);
    process.exitCode = 1;
    return;
  }
  const diffs = differencesV2(was, now);
  if (!diffs.length) {
    console.log(`v2 replay audit: no change. ${Object.keys(now.claims).length} claims, ${Object.keys(now.reliability).length} agents' reliability, ${Object.keys(now.findings).length} findings and every derived fact are exactly as in the baseline.`);
    return;
  }
  console.log(`v2 replay audit: this change moves ${diffs.length} figure(s) on the scripted record:\n`);
  for (const d of diffs) console.log(`  ${d}`);
  console.log("\nIf that is the intent, run npm run audit:v2 -- --update and commit audit/v2-baseline.json with the change.");
  console.log("Reviewers: check who gains and who loses above, and whether the change's author runs any of them.");
  process.exitCode = 1;
}

if (import.meta.url === `file://${process.argv[1]}`) {
  main().catch((e) => {
    console.error(e instanceof Error ? e.message : e);
    process.exitCode = 1;
  });
}
