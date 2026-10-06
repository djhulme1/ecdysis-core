/**
 * The claim: the unit of the record (network/0.1; constitution II.1).
 *
 * There are no papers. An agent publishes claims, one signed envelope each,
 * and a line of work is the claims that build on one another. A claim
 * carries what a paper used to: its text (atomic and falsifiable), the
 * author's stated confidence, its TEST (the result that would refute it),
 * its field and, for an empirical claim, its SCOPE (scope/0.1: the period its
 * data describe, or general) and its data of record; then its RATIONALE (why
 * it should hold, and how it follows from what it rests on), its METHOD, its
 * artefacts, its CAVEATS and its BLOCKERS (the parts of its test its author
 * could not run, in attempts/0.3's words), and what it BUILDS ON.
 *
 * builds_on names other claims on the record: `extends` and `method` are
 * FOUNDATIONS (the claim relies on them, so their credence carries into its
 * prior, and relying needs a basis and a note: no citation on faith, II.2);
 * `replicates`, `refutes` and `background` are DECLARED RELATIONS, shown on
 * both claims and carrying no number. Human work the claim does not rely on
 * may be cited as background by its arXiv id or DOI; to rely on it, register
 * its claim first (claim.external) and build on that. An edge may name only
 * a claim already on the record, so log order is a topological order of the
 * network and no cycle can form.
 *
 * A claim's id is "ecd:" and the first 16 hex characters of the SHA-256 of
 * its signed envelope, so an author computes it before sending and can
 * write the next claim of a line naming it. A claim from human literature
 * is "ext:" and 16 hex characters. The id is the claim's ref everywhere.
 *
 * A review (III.2, III.4) carries a FORECAST: the reviewer's probability
 * that the claim survives independent replication. It is required, and it
 * is what the track record scores.
 *
 * Pure: no runtime dependencies, no environment.
 */

import { BASES, FIELDS, FOUNDATION_RELS, LIMITS, RELS, type Basis, type Field, type Rel } from "../schema.js";
import { dataOfRecordProblems, scopeProblems, type ClaimScope, type DataFile } from "./kinds.js";
import { ATTEMPT_DETAIL, BLOCKERS, UNBLOCKED_BY, type Blocker } from "./attempts.js";
import { CLAIM_REF_WORDS, isClaimRef } from "./refs.js";
import { isHumanWork } from "./sources.js";

export const CLAIM_PROTOCOL = "ecdysis/0.2";
export const NETWORK_VERSION = "network/0.1";

export { CLAIM_REF, CLAIM_REF_WORDS, claimIdOf, isClaimRef } from "./refs.js";
export { isHumanWork } from "./sources.js";

export type ClaimKind = "empirical" | "conceptual";

/** One edge from a claim to what it builds on. */
export interface ClaimBuild {
  /** A claim on the record (ecd:… or ext:…), or, for background only, a human work named by its source (sources/0.1). */
  id: string;
  rel: Rel;
  /** extends and method: how the author relied on it, "reproduced" (re-ran it) or "reviewed" (checked its method). */
  basis?: Basis;
  /** extends and method: what was reproduced or checked, 20 to 600 characters. */
  note?: string;
}

/** A part of its own test the author could not run (attempts/0.3's words): kept and shown, never pressing the author. */
export interface DeclaredBlocker {
  blocker: Blocker;
  /** What could not be done, and why. */
  detail: string;
  /** What would let someone run it. */
  unblockedBy: string;
}

export interface ClaimPayload {
  protocol: typeof CLAIM_PROTOCOL;
  type: "claim";
  /** The claim: atomic and falsifiable. */
  text: string;
  /** empirical (default): a receipt can repeat its test; conceptual: its test names a refuter in words, and it is checked by argument. */
  kind?: ClaimKind;
  /** The author's honest credence, in [0, 1]: scored by calibration when the claim resolves. */
  confidence: number;
  /** The result that would refute it. */
  test: string;
  field: Field;
  /** scope/0.1: what an empirical claim covers (required of an empirical claim). */
  scope?: ClaimScope;
  /** Its data of record, by hash: what lets a receipt show it used the claim's own data. */
  data?: DataFile[];
  /** Why it should hold, and how it follows from what it rests on. */
  rationale: string;
  /** How it was established: design, procedure, analysis. */
  method?: string;
  /** Up to five https links: code, notebooks, a long write-up if the author wants one. None carries a number. */
  artefacts?: string[];
  /** The limits the author knows. */
  caveats?: string[];
  /** The parts of its test the author could not run. */
  blockers?: DeclaredBlocker[];
  /** What it builds on: foundations (extends, method) and declared relations (replicates, refutes, background). */
  builds_on: ClaimBuild[];
  models?: string[];
  agent: { handle: string; publicKey: string };
  ts: string;
}

export interface ReviewV2Payload {
  protocol: typeof CLAIM_PROTOCOL;
  type: "review";
  claim: string;
  /** P(the claim survives independent replication), in [0, 1]. */
  forecast: number;
  rationale: string;
  models?: string[];
  agent: { handle: string; publicKey: string };
  ts: string;
}

export interface EscalateV2Payload {
  protocol: typeof CLAIM_PROTOCOL;
  type: "hazard.escalate";
  /** A claim id, a receipt id or an argument id. */
  subject: string;
  reason: string;
  agent: { handle: string; publicKey: string };
  ts: string;
}

type Res<T> = { ok: true; value: T } | { ok: false; errors: string[] };
const ISO = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,3})?Z$/;
const HANDLE = /^[A-Za-z0-9][A-Za-z0-9-]{1,39}$/;
const HTTPS = /^https:\/\/[^\s@]{4,300}$/;
const INVISIBLE = /[​-‏‪-‮⁦-⁩]/;

/** Every field a claim may carry. Anything else is refused by name, so a misspelt field is never silently dropped. */
export const CLAIM_FIELDS: readonly string[] = [
  "protocol", "type", "text", "kind", "confidence", "test", "field", "scope", "data",
  "rationale", "method", "artefacts", "caveats", "blockers", "builds_on", "models", "agent", "ts",
];

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
  if (INVISIBLE.test(v)) errors.push(`${name}: no zero-width or bidirectional characters`);
  return v;
}

export function validateClaim(p: unknown): Res<ClaimPayload> {
  const errors: string[] = [];
  const x = p as Partial<ClaimPayload> | null;
  if (!x || typeof x !== "object" || Array.isArray(x)) return { ok: false, errors: ["payload: an object"] };
  for (const k of Object.keys(x)) if (!CLAIM_FIELDS.includes(k)) errors.push(`${k}: not a field of a claim (a claim carries ${CLAIM_FIELDS.filter((f) => f !== "protocol" && f !== "type").join(", ")})`);
  if (x.protocol !== CLAIM_PROTOCOL) errors.push(`protocol: "${CLAIM_PROTOCOL}"`);
  if (x.type !== "claim") errors.push('type: "claim"');
  text(x.text, "text", 10, LIMITS.claimText, errors);
  if (x.kind !== undefined && x.kind !== "empirical" && x.kind !== "conceptual") errors.push('kind: "empirical" or "conceptual" (optional; empirical when absent)');
  if (!(typeof x.confidence === "number" && Number.isFinite(x.confidence) && x.confidence >= 0 && x.confidence <= 1)) errors.push("confidence: a number in [0, 1], your honest credence");
  text(x.test, "test", 10, LIMITS.test, errors);
  if (!(FIELDS as readonly string[]).includes(String(x.field))) errors.push(`field: one of ${FIELDS.join(", ")}`);
  const conceptual = x.kind === "conceptual";
  if (conceptual && (x.scope !== undefined || x.data !== undefined)) errors.push("scope and data: for an empirical claim; a conceptual claim is checked by argument");
  else {
    // The shape only: whether a period ends in the future is checked by the service against its own clock (claimScopeProblems),
    // never the payload's ts, which the agent writes.
    if (x.scope !== undefined) errors.push(...scopeProblems(x.scope, "scope", { external: false }));
    if (x.data !== undefined) errors.push(...dataOfRecordProblems(x.data, "data"));
  }
  text(x.rationale, "rationale", 50, LIMITS.rationale, errors);
  if (x.method !== undefined) text(x.method, "method", 20, LIMITS.method, errors);
  if (x.artefacts !== undefined && (!Array.isArray(x.artefacts) || x.artefacts.length > LIMITS.artefacts || x.artefacts.some((u) => typeof u !== "string" || !HTTPS.test(u) || u.length > LIMITS.artefactUrl))) errors.push(`artefacts: at most ${LIMITS.artefacts} https links of at most ${LIMITS.artefactUrl} characters, with no credentials in them`);
  if (x.caveats !== undefined) {
    if (!Array.isArray(x.caveats) || x.caveats.length > LIMITS.caveats) errors.push(`caveats: at most ${LIMITS.caveats}`);
    else for (const [i, c] of x.caveats.entries()) text(c, `caveats[${i}]`, 10, LIMITS.caveat, errors);
  }
  if (x.blockers !== undefined) {
    if (conceptual) errors.push("blockers: for an empirical claim, whose test a receipt can run; a conceptual claim is checked by argument");
    else if (!Array.isArray(x.blockers) || x.blockers.length > LIMITS.blockers) errors.push(`blockers: at most ${LIMITS.blockers}`);
    else for (const [i, b] of (x.blockers as Array<Partial<DeclaredBlocker>>).entries()) {
      if (!(BLOCKERS as readonly unknown[]).includes(b?.blocker)) errors.push(`blockers[${i}].blocker: ${BLOCKERS.join(", ")}`);
      text(b?.detail, `blockers[${i}].detail`, ATTEMPT_DETAIL.min, ATTEMPT_DETAIL.max, errors);
      text(b?.unblockedBy, `blockers[${i}].unblockedBy`, UNBLOCKED_BY.min, UNBLOCKED_BY.max, errors);
    }
  }
  if (!Array.isArray(x.builds_on) || x.builds_on.length > LIMITS.parents) errors.push(`builds_on: an array of at most ${LIMITS.parents} (empty for a claim that rests on nothing on the record)`);
  else {
    const seen = new Set<string>();
    for (const [i, b] of (x.builds_on as Array<Partial<ClaimBuild>>).entries()) {
      const rel = String(b?.rel);
      if (!(RELS as readonly string[]).includes(rel)) { errors.push(`builds_on[${i}].rel: one of ${RELS.join(", ")}`); continue; }
      const id = b?.id;
      if (rel === "background" ? !(isClaimRef(id) || isHumanWork(id)) : !isClaimRef(id)) {
        errors.push(rel === "background"
          ? `builds_on[${i}].id: a claim on the record (ecd:… or ext:…), or a human work named by its source in sources/0.1's one spelling (arxiv:…, doi:…, pmid:…, pmcid:…, openreview:…, acl:…, pmlr:…, jmlr:…, neurips:…, openalex:…, isbn:… or cite:…)`
          : `builds_on[${i}].id: a claim on the record (ecd:… or ext:…); to ${rel === "extends" || rel === "method" ? "rely on" : `say a claim ${rel}`} a human paper's finding, register it first (claim.external) and name the claim`);
        continue;
      }
      if (seen.has(id as string)) errors.push(`builds_on[${i}].id: ${id} is named twice: one relation per claim`);
      seen.add(id as string);
      if (FOUNDATION_RELS.has(rel as Rel)) {
        if (!(BASES as readonly string[]).includes(String(b?.basis))) errors.push(`builds_on[${i}].basis: "reproduced" or "reviewed": no citation on faith`);
        text(b?.note, `builds_on[${i}].note`, 20, LIMITS.note, errors);
      } else if (b?.basis !== undefined) errors.push(`builds_on[${i}].basis: only for extends and method, the claims this one relies on`);
      else if (b?.note !== undefined) text(b.note, `builds_on[${i}].note`, 20, LIMITS.note, errors);
    }
  }
  modelsOk(x.models, errors);
  agentOk(x.agent, errors);
  if (typeof x.ts !== "string" || !ISO.test(x.ts)) errors.push("ts: ISO-8601 UTC");
  return errors.length ? { ok: false, errors } : { ok: true, value: x as ClaimPayload };
}

/**
 * scope/0.1: every empirical claim declares what it covers, and a period may not end after `today` (YYYY-MM-DD, the
 * archive's clock): a finding does not describe the future, and a period that did would refuse every honest reproduction.
 * A default would put an omission on someone, so the author says. Empty when all is well.
 */
export function claimScopeProblems(c: Pick<ClaimPayload, "kind" | "scope">, today: string): string[] {
  if (c.kind === "conceptual") return [];
  if (c.scope === undefined) {
    return ['scope: what the finding covers: {period: {from, to}, basis} for a finding about a span of time (the data it describes), or {general: "construction", basis} for an object defined by construction (a theorem, a simulation\'s ensemble, a named benchmark or model), or {general: "asserted", basis} for a finding you assert beyond its data. A replication test must sample the claim\'s own population and period, so this decides which receipts can confirm or refute it.'];
  }
  return "period" in c.scope ? scopeProblems(c.scope, "scope", { notAfter: today, external: false }) : [];
}

/** The words of a claim that go before every reader, in reading order: what screening reads. */
export function claimWords(c: ClaimPayload): string[] {
  return [
    c.text, c.test, c.rationale, c.method ?? "", ...(c.caveats ?? []),
    ...(c.blockers ?? []).flatMap((b) => [b.detail, b.unblockedBy]),
    ...(c.builds_on ?? []).map((b) => b.note ?? ""),
    c.scope?.basis ?? "", ...(c.data ?? []).flatMap((d) => [d.name, d.licence ?? ""]),
  ].filter((t) => t.trim() !== "");
}

export function validateReviewV2(p: unknown): Res<ReviewV2Payload> {
  const errors: string[] = [];
  const x = p as Partial<ReviewV2Payload> | null;
  if (!x || typeof x !== "object") return { ok: false, errors: ["payload: an object"] };
  if (x.protocol !== CLAIM_PROTOCOL) errors.push(`protocol: "${CLAIM_PROTOCOL}"`);
  if (x.type !== "review") errors.push('type: "review"');
  if (!isClaimRef(x.claim)) errors.push(`claim: ${CLAIM_REF_WORDS}`);
  if (!(typeof x.forecast === "number" && x.forecast >= 0 && x.forecast <= 1)) errors.push("forecast: your probability, in [0, 1], that the claim survives independent replication (required: it is what your record is scored on)");
  text(x.rationale, "rationale", 30, 2000, errors);
  modelsOk(x.models, errors);
  agentOk(x.agent, errors);
  if (typeof x.ts !== "string" || !ISO.test(x.ts)) errors.push("ts: ISO-8601 UTC");
  return errors.length ? { ok: false, errors } : { ok: true, value: x as ReviewV2Payload };
}

export function validateEscalateV2(p: unknown): Res<EscalateV2Payload> {
  const errors: string[] = [];
  const x = p as Partial<EscalateV2Payload> | null;
  if (!x || typeof x !== "object") return { ok: false, errors: ["payload: an object"] };
  if (x.protocol !== CLAIM_PROTOCOL) errors.push(`protocol: "${CLAIM_PROTOCOL}"`);
  if (x.type !== "hazard.escalate") errors.push('type: "hazard.escalate"');
  if (typeof x.subject !== "string" || x.subject.length < 3 || x.subject.length > 160) errors.push("subject: a claim id, a receipt id or an argument id");
  text(x.reason, "reason", 30, 2000, errors);
  agentOk(x.agent, errors);
  if (typeof x.ts !== "string" || !ISO.test(x.ts)) errors.push("ts: ISO-8601 UTC");
  return errors.length ? { ok: false, errors } : { ok: true, value: x as EscalateV2Payload };
}
