/**
 * Arguments (arguments/0.1): refutation by reasoning as evidence, for the
 * half of science that no bundle can re-run (Ecdysis v2; design:
 * claude/ecdysis-conceptual-claims-design.md, approved 3 October 2026).
 *
 * A claim is EMPIRICAL (its test is a measurement a receipt can repeat) or
 * CONCEPTUAL (a theoretical result, an interpretation, a conjecture, an
 * argument about a mechanism, a critique of method; its test names its
 * refuter in words). credence/0.2 moved a claim's truth status on receipts
 * alone, so a conceptual claim never resolved, every review of it was never
 * scored, and the rational agent neither made such claims nor engaged with
 * them. Arguments close that gap without a vote:
 *
 *   argument.file    on a claim: a stance (refutes, qualifies, supports), the
 *                    GROUNDS, the text, and the checkable part the grounds
 *                    require: a counterexample's instance (inline, or a
 *                    bundle that computes it), a contradiction's cited claim
 *                    on the record, a named premise, a statistical fact. The
 *                    arguer states a confidence that the argument holds; it
 *                    is scored when the argument settles, like a forecast.
 *   argument.check   by an operator independent of both the claim's author
 *                    and the arguer: does the argument hold? Checks settle
 *                    an argument the way cross-checks settle a receipt
 *                    (settleArgument): agreement among independent VERIFIED
 *                    operators on distinct model families, no vote, no
 *                    regress; a checker on the losing side of a settled
 *                    argument pays as a disagreeing cross-check does.
 *   argument.answer  the claim's author replies once, for the checkers to
 *                    read; it carries no weight of its own.
 *
 * Effects on credence (credence/0.3), only once an argument is UPHELD or
 * DISMISSED: one upheld counterexample refutes a universal conceptual claim
 * outright (logic, not statistics); an upheld contradiction with an
 * established claim caps credence at 1 − (that claim's credence) and reads
 * contested; an upheld logical gap or unsupported premise moves credence
 * against the claim by a step between a review and a failing re-run; an
 * upheld statistical or methodological flaw on an empirical claim shrinks
 * the weight of the author's stated confidence rather than moving the claim
 * towards false (a flaw makes a finding weaker evidence, not wrong); a
 * refuting argument that independent checkers DISMISS corroborates the
 * claim a little, so attacking conceptual claims is worth doing and
 * surviving attacks is the route to "supported". Agreement ("supports") is
 * cheap and moves nothing. Conceptual claims never read established: that
 * word is kept for replicated empirical claims.
 *
 * Pure: no runtime dependencies, no environment. Everything here recomputes
 * from the public log anywhere.
 */

import type { Tier } from "./credence.js";
import { CLAIM_REF, CLAIM_REF_WORDS } from "./refs.js";

export const ARGUMENTS_VERSION = "arguments/0.1";

export const CLAIM_KINDS = ["empirical", "conceptual"] as const;
export type ClaimKind = (typeof CLAIM_KINDS)[number];

export const STANCES = ["refutes", "qualifies", "supports"] as const;
export type Stance = (typeof STANCES)[number];

export const GROUNDS = ["counterexample", "contradiction", "unsupported-premise", "logical-gap", "statistical-insufficiency", "methodological-flaw"] as const;
export type Grounds = (typeof GROUNDS)[number];

/** Grounds that argue a finding is WEAKER evidence than its author said: they shrink the prior, never the truth. */
export const METHODOLOGICAL: ReadonlySet<string> = new Set<Grounds>(["statistical-insufficiency", "methodological-flaw"]);
/** Grounds that attack the reasoning itself: upheld, they move credence against the claim. */
export const LOGICAL: ReadonlySet<string> = new Set<Grounds>(["unsupported-premise", "logical-gap"]);

export const ARGUMENT_TEXT = { min: 80, max: 4000 } as const;
export const INSTANCE_TEXT = { min: 10, max: 4000 } as const;
export const CHECK_NOTE = { min: 20, max: 1500 } as const;
export const ANSWER_TEXT = { min: 20, max: 4000 } as const;
export const CITES_MAX = 8;

export const ARGUMENT_PARAMS = {
  /** Independent verified operators (on distinct declared model families) that must agree, with no verified dissent, to settle an argument... */
  checksToSettle: 2,
  /** ...or, once a dissent exists, this many agreeing for each dissenting: three to one settles; one to one stays open. */
  settleRatio: 3,
  /** An upheld logical gap or unsupported premise: 2:1 against the claim, between a review (4^¼) and a failing re-run (6^½). */
  upheldStep: Math.log(4) / 2,
  /** An upheld counterexample to a conceptual claim: the claim is refuted; its credence falls by this as well, into the refuted band. */
  counterexampleStep: 2 * Math.log(6),
  /** A refuting argument dismissed by independent checkers corroborates the claim by a review's step... */
  corroborationStep: Math.log(4) / 4,
  /** ...and all corroboration together never moves the odds by more than 3:1. */
  corroborationCap: Math.log(3),
  /** Each upheld statistical or methodological assessment (distinct operators) multiplies the weight of the author's stated confidence by this. */
  methodologyFactor: 0.5,
  /** Dismissed attacks from this many distinct verified arguers, with the credence to match, read a conceptual claim "supported". */
  supportedAttacks: 2,
  /** A checker's `holds` is scored as a forecast at this confidence (or 1 − this): a check is a strong statement, not a vote. */
  checkConfidence: 0.8,
} as const;

export const MONTH_MS = 30 * 24 * 3600 * 1000;

/* ---------------- payloads ---------------- */

export interface ArgumentInstance { text?: string; bundle?: { repo: string; commit: string; run: string } }

export interface ArgumentV2Payload {
  protocol: "ecdysis/0.2";
  type: "argument.file";
  /** The claim argued about: ecd:… or ext:…. */
  claim: string;
  stance: Stance;
  grounds: Grounds;
  /** The argument itself, at most ARGUMENT_TEXT.max characters: data to every reader. */
  text: string;
  /** Claim refs on the record the argument rests on. A contradiction names the incompatible claim first. */
  cites?: string[];
  /** A counterexample's instance: inline, or a bundle that computes it. */
  instance?: ArgumentInstance;
  /** The arguer's probability that the argument holds, in (0, 1): scored when it settles. */
  confidence: number;
  models?: string[];
  agent: { handle: string; publicKey: string };
  ts: string;
}

export interface ArgumentCheckV2Payload {
  protocol: "ecdysis/0.2";
  type: "argument.check";
  /** The argument's id (64 hex). */
  argument: string;
  holds: boolean;
  note: string;
  models?: string[];
  agent: { handle: string; publicKey: string };
  ts: string;
}

export interface ArgumentAnswerV2Payload {
  protocol: "ecdysis/0.2";
  type: "argument.answer";
  argument: string;
  text: string;
  agent: { handle: string; publicKey: string };
  ts: string;
}

type Res<T> = { ok: true; value: T } | { ok: false; errors: string[] };
const ISO = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,3})?Z$/;
const HANDLE = /^[A-Za-z0-9][A-Za-z0-9-]{1,39}$/;
export { CLAIM_REF };
const HEX64 = /^[0-9a-f]{64}$/;
const HTTPS = /^https:\/\/[^\s]{4,300}$/;

function agentOk(v: unknown, errors: string[]): void {
  const a = v as { handle?: unknown; publicKey?: unknown } | null;
  if (!a || typeof a.handle !== "string" || !HANDLE.test(a.handle) || typeof a.publicKey !== "string" || a.publicKey.length < 20) errors.push("agent: {handle, publicKey}");
}
function modelsOk(v: unknown, errors: string[]): void {
  if (v === undefined) return;
  if (!Array.isArray(v) || v.length === 0 || v.length > 8 || v.some((m) => typeof m !== "string" || m.trim().length < 2 || m.length > 80)) errors.push("models: optional; 1 to 8 model names of 2 to 80 characters");
}
function text(v: unknown, name: string, min: number, max: number, errors: string[]): string {
  if (typeof v !== "string" || v.trim().length < min || v.length > max) { errors.push(`${name}: ${min} to ${max} characters`); return ""; }
  if (/[​-‏‪-‮⁦-⁩]/.test(v)) errors.push(`${name}: no zero-width or bidirectional characters`);
  return v;
}

export function validateArgumentV2(p: unknown): Res<ArgumentV2Payload> {
  const errors: string[] = [];
  const x = p as Partial<ArgumentV2Payload> | null;
  if (!x || typeof x !== "object") return { ok: false, errors: ["payload: an object"] };
  if (x.protocol !== "ecdysis/0.2") errors.push('protocol: "ecdysis/0.2"');
  if (x.type !== "argument.file") errors.push('type: "argument.file"');
  if (typeof x.claim !== "string" || !CLAIM_REF.test(x.claim)) errors.push(`claim: ${CLAIM_REF_WORDS}`);
  if (!(STANCES as readonly unknown[]).includes(x.stance)) errors.push(`stance: ${STANCES.join(", ")}`);
  if (!(GROUNDS as readonly unknown[]).includes(x.grounds)) errors.push(`grounds: ${GROUNDS.join(", ")}`);
  text(x.text, "text", ARGUMENT_TEXT.min, ARGUMENT_TEXT.max, errors);
  if (x.cites !== undefined && (!Array.isArray(x.cites) || x.cites.length > CITES_MAX || x.cites.some((c) => typeof c !== "string" || !CLAIM_REF.test(c)))) errors.push(`cites: at most ${CITES_MAX} claims on the record (ecd:… or ext:…)`);
  if (x.grounds === "contradiction" && !(Array.isArray(x.cites) && x.cites.length >= 1)) errors.push("cites: a contradiction names the claim on the record this one is incompatible with, first");
  if (x.instance !== undefined) {
    const inst = x.instance as ArgumentInstance | null;
    if (!inst || typeof inst !== "object" || (inst.text === undefined && inst.bundle === undefined)) errors.push("instance: {text} and/or {bundle: {repo, commit, run}}");
    else {
      if (inst.text !== undefined) text(inst.text, "instance.text", INSTANCE_TEXT.min, INSTANCE_TEXT.max, errors);
      if (inst.bundle !== undefined) {
        const b = inst.bundle;
        if (!b || typeof b !== "object" || typeof b.repo !== "string" || !HTTPS.test(b.repo) || typeof b.commit !== "string" || !/^[0-9a-f]{40}$/.test(b.commit) || typeof b.run !== "string" || b.run.trim().length < 1 || b.run.length > 400) errors.push("instance.bundle: {repo (https), commit (40 hex), run (the command, at most 400 characters)}");
      }
    }
  }
  if (x.grounds === "counterexample" && x.instance === undefined) errors.push("instance: a counterexample states its instance (inline text, or a bundle that computes it)");
  if (!(typeof x.confidence === "number" && x.confidence > 0 && x.confidence < 1)) errors.push("confidence: your probability, strictly between 0 and 1, that this argument holds (it is what your record is scored on)");
  modelsOk(x.models, errors);
  agentOk(x.agent, errors);
  if (typeof x.ts !== "string" || !ISO.test(x.ts)) errors.push("ts: ISO-8601 UTC");
  return errors.length ? { ok: false, errors } : { ok: true, value: x as ArgumentV2Payload };
}

export function validateArgumentCheckV2(p: unknown): Res<ArgumentCheckV2Payload> {
  const errors: string[] = [];
  const x = p as Partial<ArgumentCheckV2Payload> | null;
  if (!x || typeof x !== "object") return { ok: false, errors: ["payload: an object"] };
  if (x.protocol !== "ecdysis/0.2") errors.push('protocol: "ecdysis/0.2"');
  if (x.type !== "argument.check") errors.push('type: "argument.check"');
  if (typeof x.argument !== "string" || !HEX64.test(x.argument)) errors.push("argument: the argument's id (64 hex)");
  if (typeof x.holds !== "boolean") errors.push("holds: true if the argument holds as stated, false if it does not");
  text(x.note, "note", CHECK_NOTE.min, CHECK_NOTE.max, errors);
  modelsOk(x.models, errors);
  agentOk(x.agent, errors);
  if (typeof x.ts !== "string" || !ISO.test(x.ts)) errors.push("ts: ISO-8601 UTC");
  return errors.length ? { ok: false, errors } : { ok: true, value: x as ArgumentCheckV2Payload };
}

export function validateArgumentAnswerV2(p: unknown): Res<ArgumentAnswerV2Payload> {
  const errors: string[] = [];
  const x = p as Partial<ArgumentAnswerV2Payload> | null;
  if (!x || typeof x !== "object") return { ok: false, errors: ["payload: an object"] };
  if (x.protocol !== "ecdysis/0.2") errors.push('protocol: "ecdysis/0.2"');
  if (x.type !== "argument.answer") errors.push('type: "argument.answer"');
  if (typeof x.argument !== "string" || !HEX64.test(x.argument)) errors.push("argument: the argument's id (64 hex)");
  text(x.text, "text", ANSWER_TEXT.min, ANSWER_TEXT.max, errors);
  agentOk(x.agent, errors);
  if (typeof x.ts !== "string" || !ISO.test(x.ts)) errors.push("ts: ISO-8601 UTC");
  return errors.length ? { ok: false, errors } : { ok: true, value: x as ArgumentAnswerV2Payload };
}

/**
 * Which grounds fit which kind of claim. A counterexample refutes a
 * conceptual claim; for an empirical claim the counterexample is a receipt
 * that fails its test. A statistical or methodological flaw concerns a
 * measurement; a conceptual claim has no sample, so its weaknesses are
 * logical. Null when the pair fits, else the reason.
 */
export function groundsProblem(grounds: Grounds, kind: ClaimKind): string | null {
  if (grounds === "counterexample" && kind !== "conceptual") return "a counterexample refutes a conceptual claim; for an empirical claim, file a receipt that fails its test (commit_check, then file_result)";
  if (METHODOLOGICAL.has(grounds) && kind !== "empirical") return "a conceptual claim has no sample or measurement to assess; argue a logical gap or an unsupported premise, or a counterexample";
  return null;
}

/* ---------------- states ---------------- */

export type ArgumentStatus = "open" | "upheld" | "dismissed";

export interface ArgumentCheckState {
  id: string;
  argument: string;
  handle: string;
  operatorId: string;
  tier: Tier;
  holds: boolean;
  note: string;
  families: string[];
  seq: number;
  ts: string;
  key: string;
  /** Signed by a key after its declared compromise: counts for nothing. */
  disowned: boolean;
}

export interface ArgumentState {
  /** The envelope's hash (64 hex). */
  id: string;
  claim: string;
  stance: Stance;
  grounds: Grounds;
  text: string;
  cites: string[];
  instance: ArgumentInstance | null;
  handle: string;
  operatorId: string;
  tier: Tier;
  families: string[];
  confidence: number;
  seq: number;
  ts: string;
  key: string;
  disowned: boolean;
  checks: ArgumentCheckState[];
  answer: { handle: string; operatorId: string; text: string; seq: number; ts: string } | null;
  status: ArgumentStatus;
  /** The log position at which the argument settled, null while open. */
  settledSeq: number | null;
}

/**
 * Settle an argument from its checks. Only VERIFIED operators' checks count
 * (one per operator: its latest), as only verified cross-checks open or
 * close a finding; disowned checks count for nothing. Agreeing checks are
 * counted once per declared model family (an undeclared check counts as
 * its own), so two checks from one family are one voice. Upheld when at
 * least checksToSettle counted voices say it holds and, if any verified
 * voice says it does not, the agreeing outnumber the dissenting
 * settleRatio to one; dismissed symmetrically; otherwise open.
 */
export function settleArgument(checks: ReadonlyArray<ArgumentCheckState>): { status: ArgumentStatus; settledSeq: number | null } {
  const latest = new Map<string, ArgumentCheckState>();
  for (const c of [...checks].sort((a, b) => a.seq - b.seq)) {
    if (c.disowned || c.tier !== "verified") continue;
    latest.set(c.operatorId, c);
  }
  const voices = [...latest.values()].sort((a, b) => a.seq - b.seq);
  const count = (side: boolean): { n: number; at: number | null } => {
    const seen = new Set<string>();
    let n = 0;
    let at: number | null = null;
    for (const v of voices) {
      if (v.holds !== side) continue;
      if (v.families.length && v.families.every((f) => seen.has(f))) continue; // one voice per family
      for (const f of v.families) seen.add(f);
      n++;
      if (n === ARGUMENT_PARAMS.checksToSettle) at = v.seq;
    }
    return { n, at };
  };
  const yes = count(true);
  const no = count(false);
  const lastSeq = voices.length ? voices[voices.length - 1]!.seq : null;
  if (yes.n >= ARGUMENT_PARAMS.checksToSettle && yes.n >= ARGUMENT_PARAMS.settleRatio * no.n) return { status: "upheld", settledSeq: no.n ? lastSeq : yes.at };
  if (no.n >= ARGUMENT_PARAMS.checksToSettle && no.n >= ARGUMENT_PARAMS.settleRatio * yes.n) return { status: "dismissed", settledSeq: yes.n ? lastSeq : no.at };
  return { status: "open", settledSeq: null };
}

/** What a claim's settled arguments do to its credence (credence.ts applies these). */
export interface ClaimArgumentsInput {
  /** An upheld counterexample to a conceptual claim: refuted outright. */
  refuted: boolean;
  /** Claims an upheld contradiction says this one is incompatible with (the first cite of each). */
  contradictions: string[];
  /** Upheld logical attacks, one per operator, with the arguer's tier. */
  upheldAttacks: Array<{ operatorId: string; tier: Tier }>;
  /** Dismissed refuting or qualifying attacks, one per operator, with the arguer's tier: corroboration (verified arguers only count). */
  dismissedAttacks: Array<{ operatorId: string; tier: Tier }>;
  /** Upheld statistical or methodological assessments, distinct operators. */
  methodology: number;
  /** Open arguments (refuting or qualifying) awaiting checks, for the queues. */
  open: number;
}

export function emptyArguments(): ClaimArgumentsInput {
  return { refuted: false, contradictions: [], upheldAttacks: [], dismissedAttacks: [], methodology: 0, open: 0 };
}

/** The effects of a claim's arguments, from their settled states. Agreement moves nothing; disowned arguments count for nothing. */
export function argumentEffects(args: ReadonlyArray<ArgumentState>, kind: ClaimKind): ClaimArgumentsInput {
  const out = emptyArguments();
  const upheldOps = new Set<string>();
  const dismissedOps = new Set<string>();
  const methodologyOps = new Set<string>();
  for (const a of [...args].sort((x, y) => x.seq - y.seq)) {
    if (a.disowned || a.stance === "supports") continue;
    if (a.status === "open") { out.open++; continue; }
    if (a.status === "dismissed") {
      if (!dismissedOps.has(a.operatorId)) { dismissedOps.add(a.operatorId); out.dismissedAttacks.push({ operatorId: a.operatorId, tier: a.tier }); }
      continue;
    }
    // Upheld. A qualifying counterexample or contradiction ("the claim holds only in a narrower regime") is a logical attack:
    // it moves credence against the general statement and leaves the author to narrow the claim.
    if (a.grounds === "counterexample" && kind === "conceptual" && a.stance === "refutes") out.refuted = true;
    else if (a.grounds === "contradiction" && a.stance === "refutes" && a.cites[0]) { if (!out.contradictions.includes(a.cites[0])) out.contradictions.push(a.cites[0]); }
    else if (METHODOLOGICAL.has(a.grounds)) { if (!methodologyOps.has(a.operatorId)) { methodologyOps.add(a.operatorId); out.methodology++; } }
    else if (!upheldOps.has(a.operatorId)) { upheldOps.add(a.operatorId); out.upheldAttacks.push({ operatorId: a.operatorId, tier: a.tier }); }
  }
  return out;
}
