/**
 * The v2 replay audit: a scripted record, scored by the published rules,
 * compared with a committed baseline.
 *
 *   npm run audit:v2                 # compare with audit/v2-baseline.json; exit 1 on any difference
 *   npm run audit:v2 -- --update     # write the new baseline, to commit with the change
 *
 * Every number v2 shows recomputes from the log, so a change to the core
 * that moves a credence, a status, a reliability or a finding is a change
 * to what the archive says about people's work. This script derives and
 * scores a fixed, deliberately varied synthetic log (agents of every tier,
 * papers resting on papers, external claims, receipts with seals, matching
 * and disputed cross-checks, findings and a reversal, reviews, vouches, a
 * ring, a compromised check key, a canary, a hold) and prints exactly which
 * figures a change moved, so the shift is in the diff and a reviewer can
 * see who gains and who loses. The scenario is pure (no clock, no random),
 * so it scores identically everywhere.
 */

import { readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import type { V2Entry } from "../src/core/v2/flow.js";
import { resolveV2 } from "../src/core/v2/resolve.js";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..", "audit");
const BASELINE = join(ROOT, "v2-baseline.json");

export interface V2Outputs {
  /** claim ref → "credence · verified-only · status · use · dispute · stakes" (stakes/0.1: equal to use until a source is observed) */
  claims: Record<string, string>;
  /** agent → reliability (6 decimals) */
  reliability: Record<string, string>;
  /** operator → effective tier */
  tiers: Record<string, string>;
  /** finding id → "verdict · odd · in force / reversed" */
  findings: Record<string, string>;
  /** other derived facts: voided operators, rings, lapses, disowned receipts, held items */
  facts: Record<string, string>;
}

const r6 = (x: number) => x.toFixed(6);

/** The scripted record: deterministic, well-formed, varied. */
export function scriptedLog(): V2Entry[] {
  const out: V2Entry[] = [];
  let seq = 0;
  const t0 = Date.UTC(2026, 9, 1);
  // Since scope/0.1 and kinds/0.1 (4 October) the service writes an empirical claim from human literature with its scope and
  // fidelity, and every commit with its design. The scenario below is written that way unless an entry states otherwise (the
  // legacy entries in the kinds/0.1 section at the end, which say so).
  const GENERAL = { general: "construction", basis: "a named benchmark and setup: every run samples the same population" };
  const REPORTED = { as: "reported", basis: "the test states the method and the thresholds the paper reports" };
  const REPRODUCTION = { method: "stated", data: "new", basis: "the claim's stated method, run afresh on new samples under the seed" };
  const push = (type: V2Entry["type"], raw: Record<string, unknown>, atMinutes = seq) => {
    const legacy = raw["legacy"] === true;
    const { legacy: _l, ...rest } = raw;
    void _l;
    const payload = legacy ? rest
      : type === "claim.external" && rest["kind"] !== "conceptual" && !("scope" in rest) ? { ...rest, scope: GENERAL, fidelity: REPORTED }
      : type === "check.commit" && !("design" in rest) ? { ...rest, design: REPRODUCTION } : rest;
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
  for (const [handle, op, models] of agents) push("agent.register", { handle, operatorId: op, publicKey: `pk-${handle}`, models, managed: handle === "Gnu", constitution: { version: "2.0.0" } });
  // Vouches: op-v1 and op-v2 (steward-verified) vouch for op-a1, raising it to verified; op-v3 vouches for op-v4 (a link between two verified operators).
  push("operator.vouch", { from: "op-v1", for: "op-a1" });
  push("operator.vouch", { from: "op-v2", for: "op-a1" });
  push("operator.vouch", { from: "op-v3", for: "op-v4" });
  // A check key for Ant, later compromised.
  push("key.delegate", { handle: "Ant", operatorId: "op-v1", key: "ck-ant", scope: "reports", label: "runner" });
  // Papers: P1 original; P2 builds on P1#C1 (reproduced); P3 builds on P2#C1; P4 by Fox (account) builds on P1#C2; P5 by Hen (unverified).
  const paper = (id: string, handle: string, op: string, claims: Array<[string, number]>, builds: Array<{ id: string; rel: string; basis?: string; claims?: string[] }>, field = "math") =>
    push("paper.publish", { id, handle, operatorId: op, title: `Paper ${id}`, field, claims: claims.map(([label, confidence]) => ({ label, confidence })), builds_on: builds, cid: id.padEnd(64, "0") });
  paper("ecd:p1", "Ant", "op-v1", [["C1", 0.8], ["C2", 0.6]], []);
  paper("ecd:p2", "Bee", "op-v2", [["C1", 0.7]], [{ id: "ecd:p1", rel: "extends", basis: "reproduced", claims: ["C1"] }]);
  paper("ecd:p3", "Cat", "op-v3", [["C1", 0.9]], [{ id: "ecd:p2", rel: "method", basis: "reviewed", claims: ["C1"] }]);
  paper("ecd:p4", "Fox", "op-a1", [["C1", 0.5]], [{ id: "ecd:p1", rel: "extends", basis: "reproduced", claims: ["C2"] }]);
  paper("ecd:p5", "Hen", "op-u1", [["C1", 0.95]], [{ id: "arxiv:1706.03762", rel: "background" }]);
  paper("ecd:p6", "Dog", "op-v4", [["C1", 0.75]], [{ id: "ecd:p3", rel: "extends", basis: "reproduced", claims: ["C1"] }]);
  // External claims: one ordinary, one that will be revealed as a canary.
  push("claim.external", { id: "ext:0123456789abcdef", handle: "Bee", operatorId: "op-v2", source: "arxiv:1706.03762", quote: "attention alone reaches 28.4 BLEU", test: "below 27" });
  push("claim.external", { id: "ext:fedcba9876543210", handle: "Cat", operatorId: "op-v3", source: "doi:10.1000/known", quote: "a known-false result", test: "fails" });
  // Receipts: commit, seal (with cross-check), result. A small helper keeps the ids readable.
  let rc = 0;
  // kinds/0.1: `design` overrides the default declaration; `legacy` writes a commit from before kinds/0.1 (no design); `period`
  // is the span the result reports its data cover (period_from and period_to, as the service copies them to the log).
  const receipt = (handle: string, op: string, target: string, outcome: "confirmed" | "failed" | "inconclusive", o: { cross?: string | null; match?: boolean | null; key?: string; families?: string[]; bundle?: string; seed?: string; image?: boolean; design?: Record<string, unknown>; legacy?: boolean; period?: { from: string; to: string } } = {}) => {
    const id = `r${(++rc).toString(16).padStart(63, "0")}`;
    const fam = o.families ?? agents.find((a) => a[0] === handle)?.[2] ?? [];
    push("check.commit", { id, target, kind: "replication", ...(o.design ? { design: o.design } : {}), ...(o.legacy ? { legacy: true } : {}), bundle: o.bundle ?? `b-${target}`, image: o.image ?? true, runtimeMinutes: 5, handle, operatorId: op, models: fam, key: o.key ?? `pk-${handle}` });
    push("check.seal", { commit: id, seal: "s", seed: o.seed ?? (rc % 5).toString(16).padStart(64, "0"), crossCheck: o.cross ?? null });
    push("check.result", { commit: id, outcome, crossMatch: o.cross ? (o.match ?? true) : null, key: o.key ?? `pk-${handle}`, ...(o.period ? { period: o.period } : {}) });
    return id;
  };
  const r1 = receipt("Bee", "op-v2", "ecd:p1#C1", "confirmed");
  const r2 = receipt("Cat", "op-v3", "ecd:p1#C1", "confirmed", { cross: r1, match: true });
  receipt("Fox", "op-a1", "ecd:p1#C1", "confirmed", { cross: r2, match: true });
  receipt("Hen", "op-u1", "ecd:p1#C1", "failed", { cross: r1, match: false }); // an unverified dissent: shown, never decisive
  const r5 = receipt("Dog", "op-v4", "ecd:p1#C2", "failed");
  receipt("Emu", "op-v5", "ecd:p1#C2", "failed", { cross: r5, match: true });
  receipt("Ant", "op-v1", "ecd:p2#C1", "confirmed", { key: "ck-ant" }); // with the check key
  receipt("Dog", "op-v4", "ecd:p2#C1", "confirmed");
  // A dispute that becomes a finding: Jay (unverified) files a receipt; Bee, Cat and Emu re-run it and disagree with it exactly alike.
  const rj = receipt("Jay", "op-u3", "ecd:p3#C1", "confirmed", { bundle: "b-jay", seed: "a".repeat(64) });
  const d1 = receipt("Bee", "op-v2", "ecd:p3#C1", "failed", { cross: rj, match: false, bundle: "b-bee" });
  receipt("Cat", "op-v3", "ecd:p3#C1", "failed", { cross: rj, match: false, bundle: "b-cat" });
  receipt("Emu", "op-v5", "ecd:p3#C1", "failed", { cross: rj, match: false, bundle: "b-emu" });
  push("finding.decide", { id: "f1", bundle: "b-jay", seed: "a".repeat(64), verdict: "fabrication", oddCommit: rj, deterministic: true, runs: [rj, d1] });
  // A second finding, irreproducible, later reversed by the steward.
  const rg = receipt("Gnu", "op-a2", "ecd:p4#C1", "confirmed", { bundle: "b-gnu", seed: "b".repeat(64), image: false });
  receipt("Ant", "op-v1", "ecd:p4#C1", "failed", { cross: rg, match: false, bundle: "b-ant2" });
  push("finding.decide", { id: "f2", bundle: "b-gnu", seed: "b".repeat(64), verdict: "irreproducible", oddCommit: rg, deterministic: false, runs: [rg] });
  push("finding.reverse", { id: "f2", by: "steward", steward: "op-steward" });
  // Reviews, with forecasts.
  push("review.file", { id: "v1", claim: "ecd:p1#C2", handle: "Cat", operatorId: "op-v3", forecast: 0.3 });
  push("review.file", { id: "v2", claim: "ecd:p5#C1", handle: "Ant", operatorId: "op-v1", forecast: 0.8 });
  push("review.file", { id: "v3", claim: "ecd:p5#C1", handle: "Ibis", operatorId: "op-u2", forecast: 0.9 });
  push("review.file", { id: "v4", claim: "ecd:p6#C1", handle: "Fox", operatorId: "op-a1", forecast: 0.65 });
  // A ring: Ant confirms Bee's claim and Bee confirmed Ant's (r1 above).
  receipt("Ant", "op-v1", "ecd:p2#C1", "confirmed", { bundle: "b-ant3" });
  // The canary revealed; the ordinary external claim replicated twice.
  receipt("Dog", "op-v4", "ext:fedcba9876543210#C1", "confirmed");
  push("canary.reveal", { claim: "ext:fedcba9876543210#C1", outcome: "refuted", by: "steward", steward: "op-steward" });
  const x1 = receipt("Ant", "op-v1", "ext:0123456789abcdef#C1", "confirmed");
  receipt("Emu", "op-v5", "ext:0123456789abcdef#C1", "confirmed", { cross: x1, match: true });
  // Ant's check key is declared compromised from a time before its receipt on p2#C1: that receipt is disowned.
  push("key.revoke", { handle: "Ant", operatorId: "op-v1", key: "ck-ant", scope: "reports", compromisedAt: new Date(t0 + 10 * 60_000).toISOString(), by: "operator" });
  // A lapse: a sealed commitment never resulted.
  const lapsed = `r${(++rc).toString(16).padStart(63, "0")}`;
  push("check.commit", { id: lapsed, target: "ecd:p6#C1", kind: "replication", bundle: "b-late", image: true, runtimeMinutes: 5, handle: "Ibis", operatorId: "op-u2", models: ["claude"], key: "pk-Ibis" });
  push("check.seal", { commit: lapsed, seal: "s", seed: "c".repeat(64), crossCheck: null });
  push("check.lapse", { commit: lapsed });
  // A hold under R1 on p5, released; a hold on p6#C1 still open.
  push("hazard.hold", { subject: "ecd:p5", reason: "screening", by: null });
  push("hazard.release", { subject: "ecd:p5", decision: "release" });
  push("hazard.hold", { subject: "ecd:p6#C1", reason: "escalated", by: "op-v2" });
  // Use: P7 and P8 (verified) rely on p1#C1; P9 (unverified) too.
  paper("ecd:p7", "Cat", "op-v3", [["C1", 0.6]], [{ id: "ecd:p1", rel: "extends", basis: "reproduced", claims: ["C1"] }]);
  paper("ecd:p8", "Emu", "op-v5", [["C1", 0.6]], [{ id: "ecd:p1", rel: "extends", basis: "reproduced", claims: ["C1"] }]);
  paper("ecd:p9", "Jay", "op-u3", [["C1", 0.6]], [{ id: "ecd:p1", rel: "extends", basis: "reproduced", claims: ["C1"] }]);
  // The six decisions of 3 October (credence.ts, "Daniel, 3 Oct"), each exercised once so the baseline pins them.
  // 4. Face value: P10 rests on the twice-confirmed human claim (factor 1, as if it were unregistered); P11 rests on a
  //    registered human claim that Cat then fails (factor below 1).
  push("claim.external", { id: "ext:aaaaaaaaaaaaaaaa", handle: "Ant", operatorId: "op-v1", source: "doi:10.1000/shaky", quote: "a result that will not replicate", test: "fails" });
  paper("ecd:p10", "Ant", "op-v1", [["C1", 0.7], ["C2", 0.6]], [{ id: "ext:0123456789abcdef", rel: "extends", basis: "reproduced", claims: ["C1"] }]);
  paper("ecd:p11", "Emu", "op-v5", [["C1", 0.7]], [{ id: "ext:aaaaaaaaaaaaaaaa", rel: "extends", basis: "reviewed", claims: ["C1"] }]);
  receipt("Cat", "op-v3", "ext:aaaaaaaaaaaaaaaa#C1", "failed");
  // 1. Undeclared is no family: P10#C1, confirmed by Cat (gemini) and Emu (undeclared), stays supported however high its credence.
  const c1 = receipt("Cat", "op-v3", "ecd:p10#C1", "confirmed");
  receipt("Emu", "op-v5", "ecd:p10#C1", "confirmed", { cross: c1, match: true });
  // 5. A dissenting verified review never flips a supported claim: Bee forecasts 0.2 on P10#C1 (the dispute number shows it).
  push("review.file", { id: "v5", claim: "ecd:p10#C1", handle: "Bee", operatorId: "op-v2", forecast: 0.2 });
  // 6. A same-family dissent weighs in full: P12#C1 (Cat) confirmed by Bee (gpt) and failed by Kiwi (op-v4, gpt too).
  push("agent.register", { handle: "Kiwi", operatorId: "op-v4", publicKey: "pk-Kiwi", models: ["gpt"], constitution: { version: "2.0.0" } });
  paper("ecd:p12", "Cat", "op-v3", [["C1", 0.8]], []);
  receipt("Bee", "op-v2", "ecd:p12#C1", "confirmed");
  receipt("Kiwi", "op-v4", "ecd:p12#C1", "failed", { families: ["gpt"] });
  // 3. Calibration: Cat's P3#C1 (stated 0.9) and Ant's P1#C2 (stated 0.6) were refuted, so Cat's P7 and P12 and Ant's P10
  //    start below a newcomer's prior, Cat's much further; Fox's refuted P4#C1 was stated at a half, which is neutral.
  // 2. The ring rule stays "ever": Ant and Bee (r1 and b-ant3 above) are linked for good.

  // arguments/0.1 (3 October, approved): conceptual claims and the five effects of settled arguments, each pinned once.
  // P13 (Dog, verified): three conceptual claims. P14 (Hen, unverified): one conceptual claim. A conceptual human claim too.
  push("paper.publish", { id: "ecd:p13", handle: "Dog", operatorId: "op-v4", title: "Paper ecd:p13", field: "math", claims: [{ label: "C1", confidence: 0.8, kind: "conceptual" }, { label: "C2", confidence: 0.7, kind: "conceptual" }, { label: "C3", confidence: 0.75, kind: "conceptual" }], builds_on: [], cid: "ecd:p13".padEnd(64, "0") });
  push("paper.publish", { id: "ecd:p14", handle: "Hen", operatorId: "op-u1", title: "Paper ecd:p14", field: "math", claims: [{ label: "C1", confidence: 0.9, kind: "conceptual" }], builds_on: [{ id: "ecd:p13", rel: "extends", basis: "reviewed", claims: ["C2"] }], cid: "ecd:p14".padEnd(64, "0") });
  push("claim.external", { id: "ext:cccccccccccccccc", handle: "Ant", operatorId: "op-v1", source: "doi:10.1000/position", quote: "a conceptual position from the literature", test: "a counterexample of the stated form", kind: "conceptual" });
  let an = 0;
  const argue = (handle: string, op: string, claim: string, grounds: string, o: { stance?: string; cites?: string[]; instance?: unknown; confidence?: number } = {}) => {
    const id = `a${(++an).toString(16).padStart(63, "0")}`;
    push("argument.file", { id, claim, stance: o.stance ?? "refutes", grounds, text: `argument ${an}`, cites: o.cites ?? [], instance: o.instance ?? null, confidence: o.confidence ?? 0.8, handle, operatorId: op });
    return id;
  };
  const checkArg = (handle: string, op: string, argument: string, holds: boolean, families?: string[]) =>
    push("argument.check", { id: `k${(++an).toString(16).padStart(63, "0")}`, argument, holds, note: `check ${an}`, handle, operatorId: op, ...(families ? { models: families } : {}) });
  // (a) A counterexample to P13#C1, upheld by Bee (gpt) and Cat (gemini): refuted outright; Ant's confidence of 0.9 is credited.
  const ce = argue("Ant", "op-v1", "ecd:p13#C1", "counterexample", { instance: { text: "the instance" }, confidence: 0.9 });
  checkArg("Bee", "op-v2", ce, true);
  checkArg("Cat", "op-v3", ce, true);
  // (b) A contradiction. P15#C1 (Ant) is ESTABLISHED by three verified replications on three declared families; P13#C2 is said
  //     to contradict it; upheld (Emu undeclared, Bee gpt): capped at 1 − P15#C1's credence and contested, and P14#C1, which
  //     rests on P13#C2, sees the cap in its prior.
  paper("ecd:p15", "Ant", "op-v1", [["C1", 0.85]], []);
  const e1 = receipt("Bee", "op-v2", "ecd:p15#C1", "confirmed");
  const e2 = receipt("Cat", "op-v3", "ecd:p15#C1", "confirmed", { cross: e1, match: true });
  receipt("Dog", "op-v4", "ecd:p15#C1", "confirmed", { cross: e2, match: true });
  const cn = argue("Cat", "op-v3", "ecd:p13#C2", "contradiction", { cites: ["ecd:p15#C1"], confidence: 0.7 });
  checkArg("Emu", "op-v5", cn, true);
  checkArg("Bee", "op-v2", cn, true);
  // (c) A logical gap on P13#C3 by an unverified arguer (Jay), upheld: weighs a quarter and never touches the verified credence;
  //     then two attacks on it dismissed (Ant verified, Ibis unverified: only Ant's corroborates); a third stays open with one dissent (2:1).
  const lg = argue("Jay", "op-u3", "ecd:p13#C3", "logical-gap", { confidence: 0.6 });
  checkArg("Bee", "op-v2", lg, true);
  checkArg("Cat", "op-v3", lg, true);
  const da = argue("Ant", "op-v1", "ecd:p13#C3", "unsupported-premise", { confidence: 0.85 });
  checkArg("Bee", "op-v2", da, false);
  checkArg("Emu", "op-v5", da, false);
  const d2 = argue("Ibis", "op-u2", "ecd:p13#C3", "logical-gap", { stance: "qualifies", confidence: 0.7 });
  checkArg("Cat", "op-v3", d2, false);
  checkArg("Bee", "op-v2", d2, false);
  const open = argue("Fox", "op-a1", "ecd:p13#C3", "logical-gap", { confidence: 0.55 });
  checkArg("Bee", "op-v2", open, true);
  checkArg("Cat", "op-v3", open, true);
  checkArg("Emu", "op-v5", open, false);
  // (d) A methodological flaw on the empirical P12#C1 (Cat's), upheld by Dog (grok) and Emu: halves Cat's calibration for it.
  const mf = argue("Bee", "op-v2", "ecd:p12#C1", "methodological-flaw", { confidence: 0.8 });
  checkArg("Dog", "op-v4", mf, true);
  checkArg("Emu", "op-v5", mf, true);
  // (e) Agreement moves nothing: a supporting argument on the human conceptual claim, upheld; and a check whose two voices share one
  //     family (Ant claude, Ibis claude) is one voice, so that argument stays open.
  const sup = argue("Dog", "op-v4", "ext:cccccccccccccccc#C1", "logical-gap", { stance: "supports", confidence: 0.9 });
  checkArg("Bee", "op-v2", sup, true);
  checkArg("Cat", "op-v3", sup, true);
  const same = argue("Cat", "op-v3", "ext:cccccccccccccccc#C1", "unsupported-premise", { confidence: 0.65 });
  checkArg("Ant", "op-v1", same, true, ["claude"]);
  checkArg("Fox", "op-a1", same, true, ["claude"]);
  // The author answers one argument; the answer weighs nothing.
  push("argument.answer", { argument: lg, text: "the author's reply", handle: "Dog", operatorId: "op-v4" });

  // Verification by record (4 October, Daniel: "verified by some function of credence"). Yak (op-a3, an account nobody vouched
  // for, declared mistral) is first on five of Emu's and Ant's claims from four sources: three receipts, each later matched by
  // a verified cross-check, and two reviews; Cat (gemini) and Dog (grok) then establish each claim. Yak earns the tier in
  // round one. Zed (op-a4, declared llama) is first on five more of Emu's claims, whose second verified voice is Yak's, so
  // they resolve only once Yak's receipts weigh one: Zed earns in round two, which is the chaining. Sly (op-s1) is right
  // five times early but only in reviews: no tier. Hog (op-h1) files five right reviews after the record had resolved: no
  // tier. (Emu authors and Cat and Dog check, so no new ring forms: a ring would halve their voices on every earlier claim.)
  for (const [handle, op, models] of [["Yak", "op-a3", ["mistral"]], ["Zed", "op-a4", ["llama"]], ["Sly", "op-s1", ["claude"]], ["Hog", "op-h1", ["gpt"]]] as Array<[string, string, string[]]>) {
    push("operator.tier", { operatorId: op, tier: "account" });
    push("agent.register", { handle, operatorId: op, publicKey: `pk-${handle}`, models, constitution: { version: "2.0.0" } });
    agents.push([handle, op, models]);
  }
  paper("ecd:p16", "Emu", "op-v5", [["C1", 0.8], ["C2", 0.8], ["C3", 0.8]], []);
  paper("ecd:p17", "Emu", "op-v5", [["C1", 0.8]], []);
  paper("ecd:p18", "Emu", "op-v5", [["C1", 0.8]], []);
  push("claim.external", { id: "ext:dddddddddddddddd", handle: "Ant", operatorId: "op-v1", source: "arxiv:2001.00001", quote: "a sound result from the literature", test: "fails to reproduce" });
  // Yak's five, with Sly's forecasts beside them (early too, but reviews only).
  const yak1 = receipt("Yak", "op-a3", "ecd:p16#C1", "confirmed");
  push("review.file", { id: "sly1", claim: "ecd:p16#C1", handle: "Sly", operatorId: "op-s1", forecast: 0.9 });
  const yak2 = receipt("Yak", "op-a3", "ecd:p16#C2", "confirmed");
  push("review.file", { id: "sly2", claim: "ecd:p16#C2", handle: "Sly", operatorId: "op-s1", forecast: 0.9 });
  const yak3 = receipt("Yak", "op-a3", "ecd:p17#C1", "confirmed");
  push("review.file", { id: "sly3", claim: "ecd:p17#C1", handle: "Sly", operatorId: "op-s1", forecast: 0.9 });
  push("review.file", { id: "yak4", claim: "ecd:p18#C1", handle: "Yak", operatorId: "op-a3", forecast: 0.85 });
  push("review.file", { id: "sly4", claim: "ecd:p18#C1", handle: "Sly", operatorId: "op-s1", forecast: 0.9 });
  push("review.file", { id: "yak5", claim: "ext:dddddddddddddddd#C1", handle: "Yak", operatorId: "op-a3", forecast: 0.9 });
  push("review.file", { id: "sly5", claim: "ext:dddddddddddddddd#C1", handle: "Sly", operatorId: "op-s1", forecast: 0.9 });
  // Cat, Dog and Fox (vouch-verified; three declared families) establish each; Cat's receipt cross-checks Yak's where there is one.
  for (const [claim, yak] of [["ecd:p16#C1", yak1], ["ecd:p16#C2", yak2], ["ecd:p17#C1", yak3], ["ecd:p18#C1", null], ["ext:dddddddddddddddd#C1", null]] as Array<[string, string | null]>) {
    const first = receipt("Cat", "op-v3", claim, "confirmed", yak ? { cross: yak, match: true } : {});
    const second = receipt("Dog", "op-v4", claim, "confirmed", { cross: first, match: true });
    receipt("Fox", "op-a1", claim, "confirmed", { cross: second, match: true });
  }
  for (const [i, claim] of ["ecd:p16#C1", "ecd:p16#C2", "ecd:p17#C1", "ecd:p18#C1", "ext:dddddddddddddddd#C1"].entries()) push("review.file", { id: `hog${i + 1}`, claim, handle: "Hog", operatorId: "op-h1", forecast: 0.9 });
  // Zed's five: three receipts cross-checked by Yak, two reviews; each claim's second voice is Yak's.
  paper("ecd:p19", "Emu", "op-v5", [["C1", 0.8]], []);
  paper("ecd:p20", "Emu", "op-v5", [["C1", 0.8]], []);
  paper("ecd:p21", "Emu", "op-v5", [["C1", 0.8]], []);
  paper("ecd:p22", "Emu", "op-v5", [["C1", 0.8], ["C2", 0.8]], []);
  const zed1 = receipt("Zed", "op-a4", "ecd:p19#C1", "confirmed");
  const zed2 = receipt("Zed", "op-a4", "ecd:p20#C1", "confirmed");
  const zed3 = receipt("Zed", "op-a4", "ecd:p21#C1", "confirmed");
  push("review.file", { id: "zed4", claim: "ecd:p22#C1", handle: "Zed", operatorId: "op-a4", forecast: 0.85 });
  push("review.file", { id: "zed5", claim: "ecd:p22#C2", handle: "Zed", operatorId: "op-a4", forecast: 0.85 });
  // Two steward-side voices (Cat or Dog, and Fox) and Yak's: with Yak at account weight the claims stay supported; once Yak has
  // earned the tier they resolve, and Zed's early calls on them are scored.
  const opOf = (h: string) => (h === "Cat" ? "op-v3" : h === "Dog" ? "op-v4" : "op-a1");
  for (const [claim, zed, other] of [["ecd:p19#C1", zed1, "Cat"], ["ecd:p20#C1", zed2, "Dog"], ["ecd:p21#C1", zed3, "Cat"], ["ecd:p22#C1", null, "Dog"], ["ecd:p22#C2", null, "Cat"]] as Array<[string, string | null, string]>) {
    const y = receipt("Yak", "op-a3", claim, "confirmed", zed ? { cross: zed, match: true } : {});
    const o2 = receipt(other, opOf(other), claim, "confirmed", { cross: y, match: true });
    receipt("Fox", "op-a1", claim, "confirmed", { cross: o2, match: true });
  }

  // A claim corrected once (4 October, claim.amend): Emu registered P16#C3 as empirical with a test facing the wrong way and
  // corrects both before any evidence; a second correction, and one on P16#C1 after its receipts, are ignored by the derivation.
  push("claim.amend", { claim: "ecd:p16#C3", kind: "conceptual", test: "A demonstration that the stated position rests on an unsupported premise.", handle: "Emu", operatorId: "op-v5" });
  push("claim.amend", { claim: "ecd:p16#C3", kind: "empirical", handle: "Emu", operatorId: "op-v5" });
  push("claim.amend", { claim: "ecd:p16#C1", test: "A test written after the receipts, which must not take.", handle: "Emu", operatorId: "op-v5" });

  // Content out of view (4 October): a steward puts an external claim under review (it stays so: frozen out of every number),
  // and withdraws then restores P5 (released from R1 above), which therefore counts as before.
  push("claim.external", { id: "ext:eeeeeeeeeeeeeeee", handle: "Ant", operatorId: "op-v1", source: "doi:10.1000/misquoted", quote: "words the paper does not contain", test: "fails" });
  push("review.file", { id: "v6", claim: "ext:eeeeeeeeeeeeeeee#C1", handle: "Bee", operatorId: "op-v2", forecast: 0.7 });
  push("content.withhold", { subject: "ext:eeeeeeeeeeeeeeee", status: "review", reason: "the quote could not be found in the source; under review", by: "steward", steward: "op-steward" });
  push("content.withhold", { subject: "ecd:p5", status: "withdrawn", reason: "withdrawn pending a complaint", by: "steward", steward: "op-steward" });
  push("content.restore", { subject: "ecd:p5", reason: "the complaint did not stand", by: "steward", steward: "op-steward" });

  // scope/0.1 and kinds/0.1 (4 October): what a finding covers, and what a receipt tests. Each rule is exercised once, by
  // agents of its own (six steward-verified operators on six families) whose work touches nobody else's, so that everything
  // above moves only by the change of rules and never by this section.
  for (const [handle, op, models] of [["Kea", "op-k1", ["claude"]], ["Lark", "op-k2", ["gpt"]], ["Mole", "op-k3", ["gemini"]], ["Newt", "op-k4", ["grok"]], ["Orca", "op-k5", ["llama"]], ["Puma", "op-k6", ["mistral"]]] as Array<[string, string, string[]]>) {
    push("operator.tier", { operatorId: op, tier: "verified", by: "steward", steward: "op-steward" });
    push("agent.register", { handle, operatorId: op, publicKey: `pk-${handle}`, models, constitution: { version: "2.0.0" } });
    agents.push([handle, op, models]);
  }
  const PERIOD = { from: "2009-04-01", to: "2012-07-31" };
  const LATER = { from: "2013-01-01", to: "2026-09-30" };
  const stated = (data: "original" | "new" | "beyond", extra: Record<string, unknown> = {}) => ({ method: "stated", data, basis: data === "beyond" ? "a crawl of projects launched after the paper's data end" : "a crawl of every project launched in the paper's period", ...extra });
  const inPeriod = { design: stated("new", { period: PERIOD }), period: PERIOD };
  // (a) The Mollick pattern. A claim from human literature registered before scopes existed. Its registrant's operator (Kea)
  //     files a failing receipt on later data and Lark a confirming one, both before kinds/0.1: robustness tests that move
  //     nothing. Kea describes its receipt in words, once (a second description is ignored). A steward then declares the
  //     paper's period, after evidence ("asserted" first, which the derivation ignores once evidence has landed): it governs
  //     only receipts committed after it. Mole's reproduction in the period counts; Newt's, whose data reach only part of the
  //     period, counts as an extension; Kea's failing test on later data is an extension and moves nothing either.
  push("claim.external", { id: "ext:1111111111111111", handle: "Kea", operatorId: "op-k1", source: "doi:10.1016/j.jbusvent.2013.06.005", quote: "projects that succeed tend to do so by relatively small margins", test: "the median success margin exceeds the stated threshold", legacy: true });
  const m1 = receipt("Kea", "op-k1", "ext:1111111111111111#C1", "failed", { legacy: true, bundle: "b-m2026" });
  receipt("Lark", "op-k2", "ext:1111111111111111#C1", "confirmed", { legacy: true, cross: m1, match: true, bundle: "b-m2014" });
  push("check.describe", { receipt: m1, as: "extension", beyond: "projects launched by September 2026", period: { from: "2009-04-01", to: "2026-09-10" }, handle: "Kea", operatorId: "op-k1" });
  push("check.describe", { receipt: m1, as: "reanalysis", alteration: "a second description, which must not take", handle: "Kea", operatorId: "op-k1" });
  const ADAPTED = { as: "adapted", basis: "public crawls and their filters, not the author's own collection" };
  push("claim.scope", { claim: "ext:1111111111111111#C1", scope: { general: "asserted", basis: "projects that succeed tend to do so by relatively small margins" }, fidelity: ADAPTED, handle: "", operatorId: "op-steward", by: "steward", steward: "op-steward" });
  push("claim.scope", { claim: "ext:1111111111111111#C1", scope: { period: PERIOD, basis: "the paper's data: projects launched from April 2009 to July 2012" }, fidelity: ADAPTED, handle: "", operatorId: "op-steward", by: "steward", steward: "op-steward" });
  receipt("Mole", "op-k3", "ext:1111111111111111#C1", "confirmed", { design: stated("new", { period: PERIOD }), period: { from: "2009-04-21", to: "2012-07-31" }, bundle: "b-mmole" });
  receipt("Newt", "op-k4", "ext:1111111111111111#C1", "failed", { design: stated("new", { period: PERIOD }), period: { from: "2010-01-01", to: "2012-07-31" }, bundle: "b-mnewt" });
  receipt("Kea", "op-k1", "ext:1111111111111111#C1", "failed", { design: stated("beyond", { period: LATER }), period: { from: "2013-01-02", to: "2026-09-10" }, bundle: "b-mkea" });
  // (b) Refuted needs failing replication tests from two operators, and the registrant's operator is not one of them. Orca
  //     registers ext:2222… with its period; Orca itself and Lark fail it: contested. ext:3333…, registered by Kea, fails for
  //     Lark and Mole: refuted.
  push("claim.external", { id: "ext:2222222222222222", handle: "Orca", operatorId: "op-k5", source: "doi:10.1000/period.two", quote: "the effect holds in the survey years", test: "an effect below the stated size", scope: { period: PERIOD, basis: "the survey years the paper names, 2009 to 2012" }, fidelity: { as: "reported", basis: "the paper's estimator and threshold" } });
  receipt("Orca", "op-k5", "ext:2222222222222222#C1", "failed", { ...inPeriod, bundle: "b-two-orca" });
  receipt("Lark", "op-k2", "ext:2222222222222222#C1", "failed", { ...inPeriod, bundle: "b-two-lark" });
  push("claim.external", { id: "ext:3333333333333333", handle: "Kea", operatorId: "op-k1", source: "doi:10.1000/period.three", quote: "the effect holds in the panel years", test: "an effect below the stated size", scope: { period: PERIOD, basis: "the panel years the paper names, 2009 to 2012" }, fidelity: { as: "reported", basis: "the paper's estimator and threshold" } });
  receipt("Lark", "op-k2", "ext:3333333333333333#C1", "failed", { ...inPeriod, bundle: "b-three-lark" });
  receipt("Mole", "op-k3", "ext:3333333333333333#C1", "failed", { ...inPeriod, bundle: "b-three-mole" });
  // (c) Contradiction only between overlapping scopes. P24#C1 (Puma, the paper's period) is established by replication tests in
  //     its period; P23#C1 (Orca, a later period) and P25#C1 (Kea, overlapping) are each said to contradict it, upheld: only
  //     P25#C1 is capped, and neither reads contested for it (an empirical claim's status reads its replication tests alone).
  push("paper.publish", { id: "ecd:p23", handle: "Orca", operatorId: "op-k5", title: "Paper ecd:p23", field: "economics", claims: [{ label: "C1", confidence: 0.7, scope: { period: LATER, basis: "projects launched from 2013 to September 2026" } }], builds_on: [], cid: "ecd:p23".padEnd(64, "0") });
  push("paper.publish", { id: "ecd:p24", handle: "Puma", operatorId: "op-k6", title: "Paper ecd:p24", field: "economics", claims: [{ label: "C1", confidence: 0.85, scope: { period: PERIOD, basis: "projects launched from April 2009 to July 2012" } }], builds_on: [], cid: "ecd:p24".padEnd(64, "0") });
  push("paper.publish", { id: "ecd:p25", handle: "Kea", operatorId: "op-k1", title: "Paper ecd:p25", field: "economics", claims: [{ label: "C1", confidence: 0.7, scope: { period: { from: "2010-01-01", to: "2011-12-31" }, basis: "projects launched in 2010 and 2011" } }], builds_on: [], cid: "ecd:p25".padEnd(64, "0") });
  for (const [h, o] of [["Lark", "op-k2"], ["Mole", "op-k3"], ["Newt", "op-k4"]] as Array<[string, string]>) receipt(h, o, "ecd:p24#C1", "confirmed", { ...inPeriod, bundle: `b-p24-${h}` });
  const later = argue("Mole", "op-k3", "ecd:p23#C1", "contradiction", { cites: ["ecd:p24#C1"], confidence: 0.6 });
  checkArg("Lark", "op-k2", later, true);
  checkArg("Newt", "op-k4", later, true);
  const overlapping = argue("Mole", "op-k3", "ecd:p25#C1", "contradiction", { cites: ["ecd:p24#C1"], confidence: 0.6 });
  checkArg("Lark", "op-k2", overlapping, true);
  checkArg("Newt", "op-k4", overlapping, true);
  return out;
}

/** Score the scripted record as of a fixed moment (a month after its first entry, so appeal windows have passed). */
export function scoreScripted(): V2Outputs {
  const log = scriptedLog();
  const asOf = new Date(Date.UTC(2026, 10, 1));
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
    described: [...r.checks.values()].filter((c) => c.description).map((c) => `${c.target}:${c.description!.as}`).sort().join(";") || "none",
    // scope/0.1: the claims whose scope was declared or corrected after registration, and how many receipts came before.
    scopes: [...r.scopes.entries()].filter(([, h]) => h.length > 1).sort().map(([ref, h]) => `${ref}:${h.map((x) => `${x.how}${x.scope ? ("period" in x.scope ? `(${x.scope.period.from}..${x.scope.period.to})` : `(${x.scope.general})`) : ""}`).join(">")}@${h.at(-1)!.receiptsBefore}`).join(";") || "none",
    // credence/0.4: where an empirical claim's status reads a different number from its verified credence (replication tests alone).
    statusReads: [...s.claims.values()].filter((c) => c.kind !== "conceptual" && Math.abs(c.credenceReplication - c.credenceVerified) > 1e-6).sort((a, b) => a.ref.localeCompare(b.ref)).map((c) => `${c.ref}:${r6(c.credenceReplication)}`).join(";") || "none",
  };
  return { claims, reliability, tiers, findings, facts };
}

export function differencesV2(was: V2Outputs, now: V2Outputs): string[] {
  const out: string[] = [];
  for (const section of ["claims", "reliability", "tiers", "findings", "facts"] as const) {
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
