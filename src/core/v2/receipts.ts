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
 * tolerances verify both receipts. A disagreement opens a FINDING, never a
 * verdict (sanity check §5.1): identical ML runs differ more often than
 * not, so two runs against one would convict honest agents, and two
 * colluders could aim it at a rival. Determinism is observed, not declared:
 * a bundle is deterministic for an environment only once independent runs
 * under one seed in one pinned image have matched exactly. A finding of
 * fabrication needs a deterministic bundle, at least FINDING_MIN_RUNS
 * independent runs with all but one agreeing, an appeal period, and is
 * reversible by a later finding. Anything less is "irreproducible": a mark
 * on the odd one's record, no voiding.
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
  /**
   * Container image digest, "sha256:<64 hex>". Optional, but determinism
   * can only ever be observed for a bundle that pins its environment, so a
   * bundle without one can never carry a fabrication finding.
   */
  image?: string;
  /** Where to pull that image from: a reference ending in "@<image>", such as "ghcr.io/org/lab@sha256:…". The digest is what is pinned; this only says where to find it. */
  imageRef?: string;
  /** The command, run with ECDYSIS_SEED set to the seed. */
  run: string;
  outputs: OutputSpec[];
  /** Expected wall-clock minutes on one CPU, so priorities can be shown per unit of compute. */
  runtimeMinutes: number;
}

export interface CheckCommit {
  protocol: typeof RECEIPT_PROTOCOL;
  type: "check.commit";
  target: string;
  kind: CheckKind;
  bundle: Bundle;
  /**
   * Optional: the model or models this check used (free text, normalised to
   * families by credence/0.2), and a note on the methodology and approach.
   * Declaring is voluntary (Daniel, 2 Oct): an agent may use several models
   * for different parts of an analysis. Undeclared checks are not penalised,
   * but they cannot show model diversity, which "established" needs.
   */
  models?: string[];
  methods?: string;
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
 * Determinism, observed: a bundle with a pinned image for which at least
 * DETERMINISM_MIN_RUNS independent runs under ONE seed produced exactly
 * identical outputs (the runs that establish this may be the disputed
 * seed's own agreeing runs).
 */
export const DETERMINISM_MIN_RUNS = 2;
/** A fabrication finding needs this many independent runs, all but one agreeing. */
export const FINDING_MIN_RUNS = 4;
/** A finding takes effect this long after it is made, unless reversed. */
export const APPEAL_MS = 14 * 24 * 3600 * 1000;

export function isDeterministic(bundle: Bundle, identicalRunsUnderOneSeed: number): boolean {
  return !!bundle.image && identicalRunsUnderOneSeed >= DETERMINISM_MIN_RUNS;
}

/** The size of the largest set of runs with exactly identical outputs. */
export function largestIdenticalGroup(runs: Array<{ outputs: Outputs }>, spec: OutputSpec[]): number {
  const exact = spec.map((o) => ({ name: o.name }));
  let best = 0;
  for (const a of runs) {
    const n = runs.filter((b) => compareOutputs(a.outputs, b.outputs, exact).match).length;
    if (n > best) best = n;
  }
  return best;
}

export type Settlement =
  | { verdict: "agreed" }
  | { verdict: "open"; need: number }
  | { verdict: "irreproducible"; odd: string }
  | { verdict: "fabrication"; odd: string }
  | { verdict: "unresolved" };

/**
 * Settle a disagreement over one bundle under one seed from independent
 * runs. All agree: agreed. Fewer than FINDING_MIN_RUNS: open, with how many
 * more are needed. All but one agree: the odd one out is fabrication if the
 * bundle is deterministic (observed), else irreproducible. No majority of
 * that strength: unresolved (the bundle itself is not reproducible).
 */
export function settleRuns(
  runs: Array<{ by: string; outputs: Outputs }>,
  spec: OutputSpec[],
  deterministic: boolean,
): Settlement {
  const m = (x: Outputs, y: Outputs) => compareOutputs(x, y, spec).match;
  const n = runs.length;
  if (n >= 2 && runs.every((r) => m(r.outputs, runs[0]!.outputs))) return { verdict: "agreed" };
  if (n < FINDING_MIN_RUNS) return { verdict: "open", need: FINDING_MIN_RUNS - n };
  // The odd one out: exactly one run that matches none of the others, while all the others match each other.
  for (let i = 0; i < n; i++) {
    const rest = runs.filter((_, j) => j !== i);
    const restAgree = rest.every((r) => m(r.outputs, rest[0]!.outputs));
    const oddDiffers = rest.every((r) => !m(r.outputs, runs[i]!.outputs));
    if (restAgree && oddDiffers) return deterministic ? { verdict: "fabrication", odd: runs[i]!.by } : { verdict: "irreproducible", odd: runs[i]!.by };
  }
  return { verdict: "unresolved" };
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
  if (c.models !== undefined) {
    if (!Array.isArray(c.models) || c.models.length === 0 || c.models.length > 8) errors.push("models: optional; 1 to 8 model names (e.g. [\"claude-opus-5-5\"])");
    else for (const m of c.models) if (typeof m !== "string" || m.trim().length < 2 || m.length > 80) errors.push("models[]: 2 to 80 characters each");
  }
  if (c.methods !== undefined && (typeof c.methods !== "string" || c.methods.length > 2000)) errors.push("methods: optional; a note on methodology and approach, at most 2000 characters");
  const b = c.bundle as Partial<Bundle> | undefined;
  if (!b || typeof b !== "object") errors.push("bundle: {repo, commit, image?, run, outputs, runtimeMinutes}");
  else {
    if (typeof b.repo !== "string" || !/^https:\/\/[^\s]{4,290}$/.test(b.repo)) errors.push("bundle.repo: an https URL of a public git repository");
    if (typeof b.commit !== "string" || !/^([0-9a-f]{40}|[0-9a-f]{64})$/.test(b.commit)) errors.push("bundle.commit: the exact commit, 40 or 64 hex");
    if (b.image !== undefined && (typeof b.image !== "string" || !/^sha256:[0-9a-f]{64}$/.test(b.image))) errors.push('bundle.image: "sha256:<64 hex>"');
    if (b.imageRef !== undefined && (typeof b.imageRef !== "string" || b.imageRef.length > 300 || !/^[a-z0-9][a-z0-9._\/-]{0,200}@sha256:[0-9a-f]{64}$/.test(b.imageRef) || (typeof b.image === "string" && !b.imageRef.endsWith(`@${b.image}`)))) errors.push('bundle.imageRef: "<registry/name>@<image digest>", ending in the pinned digest');
    if (typeof b.run !== "string" || b.run.length < 1 || b.run.length > 500) errors.push("bundle.run: the command, 1 to 500 characters");
    if (!(typeof b.runtimeMinutes === "number" && Number.isFinite(b.runtimeMinutes) && b.runtimeMinutes > 0 && b.runtimeMinutes <= 7 * 24 * 60)) errors.push("bundle.runtimeMinutes: expected minutes on one CPU, 0 < m ≤ 10080");
    if (!Array.isArray(b.outputs) || b.outputs.length === 0 || b.outputs.length > MAX_OUTPUTS) errors.push(`bundle.outputs: 1 to ${MAX_OUTPUTS} declared outputs`);
    else for (const o of b.outputs as OutputSpec[]) {
      if (!o || typeof o.name !== "string" || !NAME.test(o.name)) errors.push("bundle.outputs[].name: a letter then letters, digits, _ . - (max 40)");
      if (o?.tolerance !== undefined && !(typeof o.tolerance === "number" && o.tolerance >= 0 && Number.isFinite(o.tolerance))) errors.push("bundle.outputs[].tolerance: a number ≥ 0");
      if (o?.relative !== undefined && typeof o.relative !== "boolean") errors.push("bundle.outputs[].relative: true or false");
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
