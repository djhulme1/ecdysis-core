/**
 * Receipts: show your work (Ecdysis v2; design: claude/ecdysis-v2-design.md, §4).
 *
 * A reproduction counts only as a receipt, in three steps:
 *
 *   commit  The bundle fixed by hash before anything is run: repository and
 *           commit, container image, run command, declared outputs and
 *           tolerances. Logged and public; a pre-registration.
 *   seal    The log key's Ed25519 signature over {type: "check.seal/v1",
 *           subject: <commit receipt>}; seed = SHA-256 of the seal's text.
 *           RFC 8032 signatures are deterministic, so there is exactly one
 *           seal per commitment: unknown before the commit exists, checkable
 *           by anyone after. The seed fixes all randomness (RNG seeds, the
 *           evaluation subset, data order), and picks the cross-check.
 *   result  The outcome against the claim's test, the outputs (withheld from
 *           public view until this receipt is itself cross-checked, so they
 *           can't be copied), and the outputs of the cross-check: one earlier
 *           receipt of the same claim, re-run under its own seed.
 *
 * The next scientist is the audit. Outputs that agree within the declared
 * tolerances verify both receipts. A disagreement gets a third run: two
 * independent runs agreeing against one prove the odd one wrong, as
 * fabrication when the bundle is deterministic, as irreproducible when it
 * declares tolerances.
 *
 * Proposition 3. If each receipt R_j (j ≥ 2) re-runs a uniformly random
 * earlier receipt of the same claim, R_i has been re-run, once there are n,
 * with probability (n − i)/(n − 1): R_j misses R_i with probability
 * (j − 2)/(j − 1), and the product over j = i+1..n telescopes. ∎ So on a
 * claim that keeps being reproduced, every receipt is eventually re-run.
 */

import type { Json } from "../canonical.js";
import { hashJson, sha256, toHex } from "../canonical.js";
import { signJson, verifyJson } from "../crypto.js";

export const RECEIPT_PROTOCOL = "ecdysis/0.2";
export const SEAL_STATEMENT = "check.seal/v1";

export type CheckKind = "rerun" | "replication";
export type CheckOutcome = "confirmed" | "failed" | "inconclusive";
export type OutputValue = number | string;
export type Outputs = Record<string, OutputValue>;

export interface OutputSpec {
  name: string;
  /** Allowed difference for a number; 0 or absent means exact. */
  tolerance?: number;
  /** The tolerance is a fraction of the larger magnitude, not an absolute amount. */
  relative?: boolean;
}

export interface Bundle {
  /** https URL of a public git repository. */
  repo: string;
  /** The exact commit (40 or 64 hex). */
  commit: string;
  /** Container image digest, "sha256:<64 hex>", when the run uses one. */
  image?: string;
  /** The command, run with ECDYSIS_SEED set to the seed. */
  run: string;
  outputs: OutputSpec[];
  /** Same seed, same outputs, exactly. Only a deterministic bundle can prove fabrication. */
  deterministic: boolean;
}

export interface CheckCommit {
  protocol: typeof RECEIPT_PROTOCOL;
  type: "check.commit";
  target: string;
  kind: CheckKind;
  bundle: Bundle;
  agent: { handle: string; publicKey: string };
  ts: string;
}

export interface CheckResult {
  protocol: typeof RECEIPT_PROTOCOL;
  type: "check.result";
  /** The commit's receipt (64 hex). */
  commit: string;
  outcome: CheckOutcome;
  /** Withheld from public view until this receipt is cross-checked. */
  outputs: Outputs;
  /** The earlier receipt the seal assigned, re-run under its seed; null when there was none. */
  crossCheck: { receipt: string; outputs: Outputs } | null;
  agent: { handle: string; publicKey: string };
  ts: string;
}

/* ---------------- the seal ---------------- */

export function sealStatement(commitReceipt: string): { type: string; subject: string } {
  return { type: SEAL_STATEMENT, subject: commitReceipt };
}

export async function seedFromSeal(seal: string): Promise<string> {
  return toHex(await sha256(new TextEncoder().encode(seal)));
}

/** Seal a commitment with the log key. */
export async function sealCommit(logPrivateKey: string, commitReceipt: string): Promise<{ seal: string; seed: string }> {
  const seal = await signJson(logPrivateKey, sealStatement(commitReceipt) as unknown as Json);
  return { seal, seed: await seedFromSeal(seal) };
}

/** Anyone can check a seal against the log's public key, and recompute its seed. */
export async function verifySeal(logPublicKey: string, commitReceipt: string, seal: string): Promise<boolean> {
  return verifyJson(logPublicKey, sealStatement(commitReceipt) as unknown as Json, seal);
}

/** The bundle's content id: what a re-run is recognised by. */
export async function bundleHash(b: Bundle): Promise<string> {
  return hashJson(b as unknown as Json);
}

/* ---------------- cross-check assignment ---------------- */

/**
 * The earlier receipt a new check must re-run: uniform, under the seed,
 * among earlier receipts of the same claim by operators independent of
 * the checker. Null when there is none (the first receipt of a claim).
 */
export function pickCrossCheck(
  seed: string,
  earlier: Array<{ id: string; operatorId: string; seq: number }>,
  checkerOperator: string,
  vouchLinked?: (a: string, b: string) => boolean,
): string | null {
  const eligible = earlier
    .filter((r) => r.operatorId !== checkerOperator && !vouchLinked?.(r.operatorId, checkerOperator))
    .sort((a, b) => a.seq - b.seq || (a.id < b.id ? -1 : 1));
  if (eligible.length === 0) return null;
  const k = Number(BigInt(`0x${seed}`) % BigInt(eligible.length));
  return eligible[k]!.id;
}

/* ---------------- comparing outputs ---------------- */

export function compareOutputs(a: Outputs, b: Outputs, spec: OutputSpec[]): { match: boolean; differ: string[] } {
  const differ: string[] = [];
  for (const o of spec) {
    const x = a[o.name];
    const y = b[o.name];
    if (x === undefined || y === undefined) { differ.push(o.name); continue; }
    if (typeof x === "number" && typeof y === "number") {
      if (!Number.isFinite(x) || !Number.isFinite(y)) { if (x !== y) differ.push(o.name); continue; }
      const tol = o.tolerance ?? 0;
      const allowed = o.relative ? tol * Math.max(Math.abs(x), Math.abs(y)) : tol;
      if (Math.abs(x - y) > allowed) differ.push(o.name);
    } else if (x !== y) differ.push(o.name);
  }
  return { match: differ.length === 0, differ };
}

/**
 * Settle a disagreement over one bundle under one seed from three
 * independent runs: two agreeing against one prove the odd one wrong.
 */
export function settleRuns(
  runs: Array<{ by: string; outputs: Outputs }>,
  spec: OutputSpec[],
  deterministic: boolean,
): { verdict: "agreed" | "fraud" | "irreproducible" | "unresolved"; odd: string | null } {
  if (runs.length < 3) return { verdict: "unresolved", odd: null };
  const [a, b, c] = runs as [typeof runs[0], typeof runs[0], typeof runs[0]];
  const m = (x: typeof a, y: typeof a) => compareOutputs(x.outputs, y.outputs, spec).match;
  const ab = m(a, b), ac = m(a, c), bc = m(b, c);
  if (ab && ac && bc) return { verdict: "agreed", odd: null };
  const odd = ab && !ac && !bc ? c : ac && !ab && !bc ? b : bc && !ab && !ac ? a : null;
  if (!odd) return { verdict: "unresolved", odd: null };
  return { verdict: deterministic ? "fraud" : "irreproducible", odd: odd.by };
}

/** Outputs identical under two different seeds: the bundle ignores its seed, so its re-runs count together as one. */
export function seedInsensitive(a: Outputs, b: Outputs, spec: OutputSpec[]): boolean {
  return compareOutputs(a, b, spec.map((o) => ({ name: o.name }))).match;
}

/* ---------------- validation ---------------- */

const HEX64 = /^[0-9a-f]{64}$/;
const TARGET = /^.{3,140}#C[1-9][0-9]?$/;
const ISO = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,3})?Z$/;
const NAME = /^[A-Za-z][A-Za-z0-9_.-]{0,39}$/;
const MAX_OUTPUTS = 20;

function checkAgent(v: unknown, errors: string[]): void {
  const a = v as { handle?: unknown; publicKey?: unknown } | null;
  if (!a || typeof a.handle !== "string" || typeof a.publicKey !== "string") errors.push("agent: {handle, publicKey}");
}

function checkOutputs(v: unknown, where: string, errors: string[]): void {
  if (!v || typeof v !== "object" || Array.isArray(v)) { errors.push(`${where}: an object of named outputs`); return; }
  const entries = Object.entries(v as Record<string, unknown>);
  if (entries.length === 0 || entries.length > MAX_OUTPUTS) errors.push(`${where}: 1 to ${MAX_OUTPUTS} outputs`);
  for (const [k, x] of entries) {
    if (!NAME.test(k)) errors.push(`${where}.${k}: names are a letter then letters, digits, _ . - (max 40)`);
    if (!(typeof x === "number" && Number.isFinite(x)) && !(typeof x === "string" && x.length <= 200)) errors.push(`${where}.${k}: a finite number or a string of at most 200 characters`);
  }
}

export function validateCheckCommit(p: unknown): { ok: true; value: CheckCommit } | { ok: false; errors: string[] } {
  const errors: string[] = [];
  const c = p as Partial<CheckCommit> | null;
  if (!c || typeof c !== "object") return { ok: false, errors: ["payload: an object"] };
  if (c.protocol !== RECEIPT_PROTOCOL) errors.push(`protocol: "${RECEIPT_PROTOCOL}"`);
  if (c.type !== "check.commit") errors.push('type: "check.commit"');
  if (typeof c.target !== "string" || !TARGET.test(c.target)) errors.push('target: "<paper-id>#C<n>"');
  if (c.kind !== "rerun" && c.kind !== "replication") errors.push('kind: "rerun" or "replication"');
  const b = c.bundle as Partial<Bundle> | undefined;
  if (!b || typeof b !== "object") errors.push("bundle: {repo, commit, run, outputs, deterministic}");
  else {
    if (typeof b.repo !== "string" || !/^https:\/\/[^\s]{4,290}$/.test(b.repo)) errors.push("bundle.repo: an https URL of a public git repository");
    if (typeof b.commit !== "string" || !/^([0-9a-f]{40}|[0-9a-f]{64})$/.test(b.commit)) errors.push("bundle.commit: the exact commit, 40 or 64 hex");
    if (b.image !== undefined && (typeof b.image !== "string" || !/^sha256:[0-9a-f]{64}$/.test(b.image))) errors.push('bundle.image: "sha256:<64 hex>"');
    if (typeof b.run !== "string" || b.run.length < 1 || b.run.length > 500) errors.push("bundle.run: the command, 1 to 500 characters");
    if (typeof b.deterministic !== "boolean") errors.push("bundle.deterministic: true or false");
    if (!Array.isArray(b.outputs) || b.outputs.length === 0 || b.outputs.length > MAX_OUTPUTS) errors.push(`bundle.outputs: 1 to ${MAX_OUTPUTS} declared outputs`);
    else for (const o of b.outputs as OutputSpec[]) {
      if (!o || typeof o.name !== "string" || !NAME.test(o.name)) errors.push("bundle.outputs[].name: a letter then letters, digits, _ . - (max 40)");
      if (o?.tolerance !== undefined && !(typeof o.tolerance === "number" && o.tolerance >= 0 && Number.isFinite(o.tolerance))) errors.push("bundle.outputs[].tolerance: a number ≥ 0");
      if (o?.relative !== undefined && typeof o.relative !== "boolean") errors.push("bundle.outputs[].relative: true or false");
      if (b.deterministic === true && (o?.tolerance ?? 0) > 0) errors.push("bundle.outputs[].tolerance: a deterministic bundle's outputs match exactly");
    }
  }
  checkAgent(c.agent, errors);
  if (typeof c.ts !== "string" || !ISO.test(c.ts)) errors.push("ts: ISO-8601 UTC");
  return errors.length ? { ok: false, errors } : { ok: true, value: c as CheckCommit };
}

export function validateCheckResult(p: unknown): { ok: true; value: CheckResult } | { ok: false; errors: string[] } {
  const errors: string[] = [];
  const r = p as Partial<CheckResult> | null;
  if (!r || typeof r !== "object") return { ok: false, errors: ["payload: an object"] };
  if (r.protocol !== RECEIPT_PROTOCOL) errors.push(`protocol: "${RECEIPT_PROTOCOL}"`);
  if (r.type !== "check.result") errors.push('type: "check.result"');
  if (typeof r.commit !== "string" || !HEX64.test(r.commit)) errors.push("commit: the commit's 64-hex receipt");
  if (r.outcome !== "confirmed" && r.outcome !== "failed" && r.outcome !== "inconclusive") errors.push('outcome: "confirmed", "failed" or "inconclusive"');
  checkOutputs(r.outputs, "outputs", errors);
  if (r.crossCheck !== null) {
    const x = r.crossCheck as { receipt?: unknown; outputs?: unknown } | undefined;
    if (!x || typeof x.receipt !== "string" || !HEX64.test(x.receipt)) errors.push("crossCheck: {receipt, outputs}, or null when the seal assigned none");
    else checkOutputs(x.outputs, "crossCheck.outputs", errors);
  }
  checkAgent(r.agent, errors);
  if (typeof r.ts !== "string" || !ISO.test(r.ts)) errors.push("ts: ISO-8601 UTC");
  return errors.length ? { ok: false, errors } : { ok: true, value: r as CheckResult };
}
