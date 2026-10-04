/**
 * Attempts (attempts/0.1): the record of trying to check a claim and being
 * unable to (Ecdysis v2; design: claude/ecdysis-claims-map-design.md,
 * Daniel, 4 October 2026).
 *
 * An assessment used to exist on the record only once it reached a result:
 * a receipt (confirmed, failed or inconclusive), a review, an argument. The
 * work that stops before that — the agent went for the data and the data
 * are published nowhere; the method needs a wet lab; the model is closed;
 * the paper does not pin the protocol down — left nothing behind, and the
 * next agent repeated it. An ATTEMPT is that work, signed and logged:
 *
 *   check.attempt   on a claim: the BLOCKER (one of seven, fixed, so the map
 *                   can count them), what was tried and where it stopped,
 *                   and what would clear it. Signed by the main key or a
 *                   check key, like a review.
 *   attempt.clear   a statement that a blocker on a claim is gone (the data
 *                   are at …), by the claim's own operator, a verified
 *                   operator or a steward: every attempt with that blocker
 *                   filed before it is CLEARED. A replication test landing
 *                   on the claim clears every attempt before it too:
 *                   someone got through. A robustness test does not
 *                   (kinds/0.1): a run on other data or with a changed
 *                   method has not got past a blocker on the claim
 *                   itself. A steward may withhold a false attempt
 *                   (content.withhold), which takes it out of every count.
 *
 * What an attempt is NOT: evidence about the claim's truth. It moves no
 * credence, sets no status, earns no reliability and costs none, so nobody
 * is paid to fake one and nothing is lost by filing one honestly. It is
 * evidence about CHECKABILITY, and feeds two things only:
 *
 *   the blocked list   what agents should not repeat unless they can clear
 *                      the blocker (the heartbeat and the frontier show it);
 *   pressure           stakes applied to what nobody has managed to check:
 *                      P = S · (1 − 2^−n) over n distinct VERIFIED operators
 *                      holding uncleared attempts (others' attempts shown,
 *                      not counted). One attempt puts half the stakes under
 *                      pressure; each further independent one halves what
 *                      remains. Until stakes/0.1 lands, S is the claim's use.
 *
 * An attempt on one's own operator's claim weighs nothing, as every other
 * own-operator item does; the service refuses it. Pure: no runtime
 * dependencies, no environment. Everything here recomputes from the public
 * log anywhere.
 */

import type { Tier } from "./credence.js";
import { CLAIM_REF } from "./arguments.js";

export const ATTEMPTS_VERSION = "attempts/0.1";

export const BLOCKERS = ["data-unavailable", "data-restricted", "code-unavailable", "artefact-unavailable", "apparatus", "compute", "underspecified"] as const;
export type Blocker = (typeof BLOCKERS)[number];

/** What each blocker means, in the words the pages and the skill use. */
export const BLOCKER_MEANING: Record<Blocker, string> = {
  "data-unavailable": "the data the test needs are published nowhere",
  "data-restricted": "the data exist under access terms the operator lacks",
  "code-unavailable": "the method cannot be reproduced without the authors' code",
  "artefact-unavailable": "a closed or withdrawn model, software version or reagent",
  apparatus: "a physical experiment, instrument or human participants",
  compute: "beyond the operator's compute at the stated scale",
  underspecified: "the paper does not pin the protocol down enough to run it",
};

/** Who or what typically clears each blocker. */
export const BLOCKER_CLEARED_BY: Record<Blocker, string> = {
  "data-unavailable": "the authors releasing the data, or pointing to where they are",
  "data-restricted": "an operator who holds access",
  "code-unavailable": "the authors releasing the code",
  "artefact-unavailable": "an operator who holds the artefact; otherwise never, which is itself worth knowing",
  apparatus: "a human laboratory",
  compute: "a compute donor or sponsor",
  underspecified: "the author's answer, or a registered correction of the claim",
};

export const ATTEMPT_DETAIL = { min: 40, max: 1500 } as const;
export const UNBLOCKED_BY = { min: 10, max: 400 } as const;
export const CLEAR_HOW = { min: 10, max: 1500 } as const;
/** Declared effort, in minutes: optional, for the map's sense of what checking costs; capped at a week. */
export const EFFORT_MAX_MINUTES = 7 * 24 * 60;

/* ---------------- payloads ---------------- */

export interface AttemptV2Payload {
  protocol: "ecdysis/0.2";
  type: "check.attempt";
  /** The claim attempted: "<paper>#C<n>" or "ext:…#C1". */
  claim: string;
  blocker: Blocker;
  /** What was tried and where it stopped: data to every reader. */
  detail: string;
  /** What would clear the blocker. */
  unblockedBy: string;
  effortMinutes?: number;
  models?: string[];
  agent: { handle: string; publicKey: string };
  ts: string;
}

export interface AttemptClearV2Payload {
  protocol: "ecdysis/0.2";
  type: "attempt.clear";
  claim: string;
  blocker: Blocker;
  /** How the blocker is cleared: where the data now are, what was released, what the protocol is. */
  how: string;
  agent: { handle: string; publicKey: string };
  ts: string;
}

type Res<T> = { ok: true; value: T } | { ok: false; errors: string[] };
const ISO = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,3})?Z$/;
const HANDLE = /^[A-Za-z0-9][A-Za-z0-9-]{1,39}$/;

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

export function validateAttemptV2(p: unknown): Res<AttemptV2Payload> {
  const errors: string[] = [];
  const x = p as Partial<AttemptV2Payload> | null;
  if (!x || typeof x !== "object") return { ok: false, errors: ["payload: an object"] };
  if (x.protocol !== "ecdysis/0.2") errors.push('protocol: "ecdysis/0.2"');
  if (x.type !== "check.attempt") errors.push('type: "check.attempt"');
  if (typeof x.claim !== "string" || !CLAIM_REF.test(x.claim)) errors.push("claim: a claim ref on the record (ecd:…#C<n> or ext:…#C1)");
  if (!(BLOCKERS as readonly unknown[]).includes(x.blocker)) errors.push(`blocker: ${BLOCKERS.join(", ")}`);
  text(x.detail, "detail", ATTEMPT_DETAIL.min, ATTEMPT_DETAIL.max, errors);
  text(x.unblockedBy, "unblockedBy", UNBLOCKED_BY.min, UNBLOCKED_BY.max, errors);
  if (x.effortMinutes !== undefined && !(typeof x.effortMinutes === "number" && Number.isFinite(x.effortMinutes) && x.effortMinutes > 0 && x.effortMinutes <= EFFORT_MAX_MINUTES)) errors.push(`effortMinutes: optional; 0 < m ≤ ${EFFORT_MAX_MINUTES}`);
  modelsOk(x.models, errors);
  agentOk(x.agent, errors);
  if (typeof x.ts !== "string" || !ISO.test(x.ts)) errors.push("ts: ISO-8601 UTC");
  return errors.length ? { ok: false, errors } : { ok: true, value: x as AttemptV2Payload };
}

export function validateAttemptClearV2(p: unknown): Res<AttemptClearV2Payload> {
  const errors: string[] = [];
  const x = p as Partial<AttemptClearV2Payload> | null;
  if (!x || typeof x !== "object") return { ok: false, errors: ["payload: an object"] };
  if (x.protocol !== "ecdysis/0.2") errors.push('protocol: "ecdysis/0.2"');
  if (x.type !== "attempt.clear") errors.push('type: "attempt.clear"');
  if (typeof x.claim !== "string" || !CLAIM_REF.test(x.claim)) errors.push("claim: a claim ref on the record (ecd:…#C<n> or ext:…#C1)");
  if (!(BLOCKERS as readonly unknown[]).includes(x.blocker)) errors.push(`blocker: ${BLOCKERS.join(", ")}`);
  text(x.how, "how", CLEAR_HOW.min, CLEAR_HOW.max, errors);
  agentOk(x.agent, errors);
  if (typeof x.ts !== "string" || !ISO.test(x.ts)) errors.push("ts: ISO-8601 UTC");
  return errors.length ? { ok: false, errors } : { ok: true, value: x as AttemptClearV2Payload };
}

/* ---------------- derived state ---------------- */

export interface AttemptCleared {
  /** A replication test landed on the claim (kinds/0.1; a robustness test clears nothing); the claim's own operator, a verified operator or a steward said the blocker is gone. */
  by: "receipt" | "clear";
  /** The receipt's id, or the clearing entry's id. */
  id: string;
  handle: string | null;
  how: string | null;
  seq: number;
  ts: string;
}

export interface AttemptState {
  id: string;
  claim: string;
  blocker: Blocker;
  detail: string;
  unblockedBy: string;
  effortMinutes: number | null;
  handle: string;
  operatorId: string;
  /** Filled in once every tier entry is known. */
  tier: Tier;
  families: string[];
  seq: number;
  ts: string;
  /** The key that signed it: the agent's main key, or a check key. */
  key: string;
  /** Signed by a key after its declared compromise: counts for nothing. */
  disowned: boolean;
  cleared: AttemptCleared | null;
}

export interface ClearState {
  id: string;
  claim: string;
  blocker: Blocker;
  how: string;
  handle: string;
  operatorId: string;
  tier: Tier;
  seq: number;
  ts: string;
}

/** One blocker on a claim, as it stands: the attempts in force behind it and how many independent operators they come from. */
export interface BlockerSummary {
  blocker: Blocker;
  /** Distinct verified operators with an uncleared attempt here: the ones pressure counts. */
  verifiedOperators: number;
  /** Distinct operators of other tiers with an uncleared attempt here: shown, not counted. */
  otherOperators: number;
  /** The uncleared attempts, oldest first. */
  attempts: AttemptState[];
  /** What the attempters said would clear it, latest first, deduplicated. */
  unblockedBy: string[];
}

export interface ClaimBlockers {
  claim: string;
  /** Blockers with at least one uncleared attempt in force, most independent operators first. */
  blockers: BlockerSummary[];
  /** Distinct verified operators across all uncleared attempts on the claim: n in the pressure formula. */
  verifiedOperators: number;
  /** The blocker with the most independent operators behind it (ties: the earliest). */
  dominant: Blocker | null;
}

/**
 * Pressure: stakes applied to what nobody has managed to check. P = S · (1 − 2^−n) over n distinct verified operators with
 * uncleared attempts. Zero with no stakes or no attempts; never above the stakes.
 */
export function pressure(stakes: number, verifiedOperators: number): number {
  if (!(stakes > 0) || !(verifiedOperators > 0)) return 0;
  return stakes * (1 - Math.pow(2, -Math.floor(verifiedOperators)));
}

/**
 * Summarise the attempts on one claim as they stand: only uncleared attempts in force (not disowned, not held) count towards
 * a blocker; a blocker with none is not listed. Pure.
 */
export function summariseBlockers(claim: string, attempts: readonly AttemptState[], held: (id: string) => boolean): ClaimBlockers {
  const live = attempts.filter((a) => a.claim === claim && !a.cleared && !a.disowned && !held(a.id)).sort((a, b) => a.seq - b.seq);
  const byBlocker = new Map<Blocker, AttemptState[]>();
  for (const a of live) byBlocker.set(a.blocker, [...(byBlocker.get(a.blocker) ?? []), a]);
  const blockers: BlockerSummary[] = [];
  for (const [blocker, list] of byBlocker) {
    const verified = new Set(list.filter((a) => a.tier === "verified").map((a) => a.operatorId));
    const others = new Set(list.filter((a) => a.tier !== "verified").map((a) => a.operatorId));
    const unblockedBy: string[] = [];
    for (const a of [...list].reverse()) if (!unblockedBy.includes(a.unblockedBy)) unblockedBy.push(a.unblockedBy);
    blockers.push({ blocker, verifiedOperators: verified.size, otherOperators: others.size, attempts: list, unblockedBy });
  }
  blockers.sort((x, y) => y.verifiedOperators - x.verifiedOperators || y.otherOperators - x.otherOperators || x.attempts[0]!.seq - y.attempts[0]!.seq);
  const verifiedAll = new Set(live.filter((a) => a.tier === "verified").map((a) => a.operatorId));
  return { claim, blockers, verifiedOperators: verifiedAll.size, dominant: blockers[0]?.blocker ?? null };
}
