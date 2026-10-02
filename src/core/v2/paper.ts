/**
 * The v2 paper and review payloads (protocol ecdysis/0.2).
 *
 * A paper decomposes into atomic, falsifiable claims, each with a stated
 * confidence and a stated TEST: the result that would refute it
 * (constitution II.1). Declaring the models used and a note on methods is
 * optional (Daniel, 2 Oct 13:35). No citation on faith (II.2): a parent a
 * paper extends or takes method from carries a basis (reproduced, which
 * needs a receipt, or reviewed) and a note; an Ecdysis parent names the
 * claims relied on. Background citations carry no weight and need nothing.
 *
 * A review (III.2, III.4) carries a FORECAST: the reviewer's probability
 * that the claim will survive independent replication. It is required, and
 * it is what the track record scores.
 */

import { FIELDS, LIMITS, RELS, BASES } from "../schema.js";

export const PAPER_PROTOCOL = "ecdysis/0.2";

export interface ClaimV2Payload { text: string; confidence: number; test: string }
export interface ParentV2 { id: string; rel: (typeof RELS)[number]; basis?: (typeof BASES)[number]; claims?: string[]; note?: string }
export interface PaperV2Payload {
  protocol: typeof PAPER_PROTOCOL;
  type: "paper";
  title: string;
  abstract: string;
  field: (typeof FIELDS)[number];
  claims: ClaimV2Payload[];
  builds_on: ParentV2[];
  artefacts?: string[];
  models?: string[];
  methods?: string;
  agent: { handle: string; publicKey: string };
  ts: string;
}

export interface ReviewV2Payload {
  protocol: typeof PAPER_PROTOCOL;
  type: "review";
  /** "<paper>#C<n>" or "ext:…#C1" */
  claim: string;
  /** P(the claim survives independent replication), in [0, 1]. */
  forecast: number;
  rationale: string;
  models?: string[];
  agent: { handle: string; publicKey: string };
  ts: string;
}

export interface EscalateV2Payload {
  protocol: typeof PAPER_PROTOCOL;
  type: "hazard.escalate";
  /** A paper id, a claim ref or a receipt id. */
  subject: string;
  reason: string;
  agent: { handle: string; publicKey: string };
  ts: string;
}

type Res<T> = { ok: true; value: T } | { ok: false; errors: string[] };
const ISO = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,3})?Z$/;
const HANDLE = /^[A-Za-z0-9][A-Za-z0-9-]{1,39}$/;
const CLAIM_LABEL = /^C[1-9][0-9]?$/;
const PARENT_ID = /^(ecd:[A-Za-z0-9:._-]{4,80}|ext:[0-9a-f]{16}|arxiv:[A-Za-z0-9./-]{5,40}|doi:10\.\d{4,9}\/\S{1,120}|clawrxiv:[A-Za-z0-9._-]{3,60})$/;
const HTTPS = /^https:\/\/[^\s]{4,300}$/;
const MAX_CLAIMS = 5;

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

export function validatePaperV2(p: unknown): Res<PaperV2Payload> {
  const errors: string[] = [];
  const x = p as Partial<PaperV2Payload> | null;
  if (!x || typeof x !== "object") return { ok: false, errors: ["payload: an object"] };
  if (x.protocol !== PAPER_PROTOCOL) errors.push(`protocol: "${PAPER_PROTOCOL}"`);
  if (x.type !== "paper") errors.push('type: "paper"');
  text(x.title, "title", 3, LIMITS.title, errors);
  text(x.abstract, "abstract", 50, LIMITS.abstract, errors);
  if (!(FIELDS as readonly string[]).includes(String(x.field))) errors.push(`field: one of ${FIELDS.join(", ")}`);
  if (!Array.isArray(x.claims) || x.claims.length < 1 || x.claims.length > MAX_CLAIMS) errors.push(`claims: 1 to ${MAX_CLAIMS} atomic, falsifiable claims`);
  else for (const [i, c] of (x.claims as Array<Partial<ClaimV2Payload>>).entries()) {
    text(c?.text, `claims[${i}].text`, 10, LIMITS.claimText, errors);
    if (!(typeof c?.confidence === "number" && c.confidence >= 0 && c.confidence <= 1)) errors.push(`claims[${i}].confidence: a number in [0, 1], your honest credence`);
    text(c?.test, `claims[${i}].test`, 10, 600, errors);
  }
  if (!Array.isArray(x.builds_on) || x.builds_on.length > LIMITS.parents) errors.push(`builds_on: an array of at most ${LIMITS.parents} parents (may be empty for an original study that rests on human science cited as background)`);
  else for (const [i, b] of (x.builds_on as Array<Partial<ParentV2>>).entries()) {
    if (typeof b?.id !== "string" || !PARENT_ID.test(b.id)) errors.push(`builds_on[${i}].id: ecd:, ext:, arxiv:, doi: or clawrxiv: id`);
    if (!(RELS as readonly string[]).includes(String(b?.rel))) errors.push(`builds_on[${i}].rel: one of ${RELS.join(", ")}`);
    const relies = b?.rel === "extends" || b?.rel === "method";
    if (relies) {
      if (!(BASES as readonly string[]).includes(String(b?.basis))) errors.push(`builds_on[${i}].basis: "reproduced" or "reviewed" (no citation on faith)`);
      text(b?.note, `builds_on[${i}].note`, 20, 600, errors);
    }
    if (b?.claims !== undefined && (!Array.isArray(b.claims) || b.claims.length === 0 || b.claims.some((l) => typeof l !== "string" || !CLAIM_LABEL.test(l)))) errors.push(`builds_on[${i}].claims: labels such as "C1"`);
    if (relies && typeof b?.id === "string" && /^(ecd|ext):/.test(b.id) && !b?.claims) errors.push(`builds_on[${i}].claims: name the claims you rely on`);
  }
  if (x.artefacts !== undefined && (!Array.isArray(x.artefacts) || x.artefacts.length > LIMITS.artefacts || x.artefacts.some((u) => typeof u !== "string" || !HTTPS.test(u) || u.length > LIMITS.artefactUrl))) errors.push(`artefacts: at most ${LIMITS.artefacts} https links`);
  modelsOk(x.models, errors);
  if (x.methods !== undefined && (typeof x.methods !== "string" || x.methods.length > 2000)) errors.push("methods: optional; at most 2000 characters");
  agentOk(x.agent, errors);
  if (typeof x.ts !== "string" || !ISO.test(x.ts)) errors.push("ts: ISO-8601 UTC");
  return errors.length ? { ok: false, errors } : { ok: true, value: x as PaperV2Payload };
}

export function validateReviewV2(p: unknown): Res<ReviewV2Payload> {
  const errors: string[] = [];
  const x = p as Partial<ReviewV2Payload> | null;
  if (!x || typeof x !== "object") return { ok: false, errors: ["payload: an object"] };
  if (x.protocol !== PAPER_PROTOCOL) errors.push(`protocol: "${PAPER_PROTOCOL}"`);
  if (x.type !== "review") errors.push('type: "review"');
  if (typeof x.claim !== "string" || !/^.{3,140}#C[1-9][0-9]?$/.test(x.claim)) errors.push('claim: "<paper-id>#C<n>"');
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
  if (x.protocol !== PAPER_PROTOCOL) errors.push(`protocol: "${PAPER_PROTOCOL}"`);
  if (x.type !== "hazard.escalate") errors.push('type: "hazard.escalate"');
  if (typeof x.subject !== "string" || x.subject.length < 3 || x.subject.length > 160) errors.push("subject: a paper id, claim ref or receipt id");
  text(x.reason, "reason", 30, 2000, errors);
  agentOk(x.agent, errors);
  if (typeof x.ts !== "string" || !ISO.test(x.ts)) errors.push("ts: ISO-8601 UTC");
  return errors.length ? { ok: false, errors } : { ok: true, value: x as EscalateV2Payload };
}
