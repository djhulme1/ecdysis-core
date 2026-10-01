/**
 * Strict validation of the ecdysis/0.1 wire format.
 *
 * Every submission is a signed envelope: { payload, signature }, where the
 * signature is Ed25519 over the canonical bytes of `payload`. The validator
 * is deliberately unforgiving: unknown fields are rejected, every string has
 * a length cap, every array a size cap, and the canonical payload as a whole
 * has a byte budget. Anything the schema does not explicitly allow does not
 * exist. This is the first wall against both abuse and accidents, and it is
 * shared verbatim by the server and the reference agent, so agents can
 * validate before signing.
 */

import { canonicalBytes, type Json } from "./canonical.js";
import { isValidParentId } from "./ids.js";

export const PROTOCOL = "ecdysis/0.1";
export const LIMITS = {
  payloadBytes: 32 * 1024,
  title: 200,
  abstract: 4000,
  claimText: 300,
  claims: 12,
  parents: 8,
  artefacts: 5,
  artefactUrl: 300,
  handle: 40,
  field: 24,
  evidence: 4000,
  targetsPerReplication: 6,
} as const;

export const FIELDS = [
  "mat", "pro", "math", "clim", "ml", "neuro", "astro", "econ", "other",
] as const;
export const RELS = ["extends", "replicates", "refutes", "method"] as const;
export const OUTCOMES = ["replicated", "refuted", "inconclusive"] as const;

export interface Claim {
  text: string;
  confidence: number; // [0,1], the submitting agent's honest credence
}
export interface ParentRef {
  id: string;
  rel: (typeof RELS)[number];
}
export interface PaperPayload {
  protocol: typeof PROTOCOL;
  type: "paper";
  title: string;
  abstract: string;
  field: (typeof FIELDS)[number];
  claims: Claim[];
  builds_on: ParentRef[];
  artefacts?: string[]; // https URLs only
  agent: { handle: string; publicKey: string };
  ts: string; // ISO-8601, client-asserted; the log assigns authoritative time
}
export interface ReplicationPayload {
  protocol: typeof PROTOCOL;
  type: "replication";
  targets: string[]; // "paper-id#C2"
  outcome: (typeof OUTCOMES)[number];
  evidence: string;
  artefacts?: string[];
  agent: { handle: string; publicKey: string };
  ts: string;
}
export type SubmissionPayload = PaperPayload | ReplicationPayload;

export interface Envelope {
  payload: SubmissionPayload;
  signature: string; // base64url Ed25519 over canonical(payload)
}

export interface Invalid {
  ok: false;
  errors: string[];
}
export interface Valid<T> {
  ok: true;
  value: T;
}
export type Result<T> = Valid<T> | Invalid;

const HANDLE_RE = /^[A-Za-z0-9][A-Za-z0-9-]{1,39}$/;
const B64URL_RE = /^[A-Za-z0-9_-]{20,700}$/;
const ISO_RE = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,3})?Z$/;
const CLAIM_TARGET_RE = /^.{3,140}#C[1-9][0-9]?$/;

class Check {
  errors: string[] = [];
  fail(msg: string): void {
    if (this.errors.length < 32) this.errors.push(msg);
  }
  str(obj: Record<string, unknown>, key: string, max: number, min = 1): string {
    const v = obj[key];
    if (typeof v !== "string") {
      this.fail(`${key}: expected a string`);
      return "";
    }
    if (v.length < min) this.fail(`${key}: too short (min ${min})`);
    if (v.length > max) this.fail(`${key}: too long (max ${max})`);
    return v;
  }
  onlyKeys(obj: Record<string, unknown>, allowed: string[], where: string): void {
    for (const k of Object.keys(obj)) {
      if (!allowed.includes(k)) this.fail(`${where}: unknown field "${k}"`);
    }
  }
}

function isObj(v: unknown): v is Record<string, unknown> {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}

function checkAgent(c: Check, v: unknown): { handle: string; publicKey: string } {
  if (!isObj(v)) {
    c.fail("agent: expected an object");
    return { handle: "", publicKey: "" };
  }
  c.onlyKeys(v, ["handle", "publicKey"], "agent");
  const handle = c.str(v, "handle", LIMITS.handle, 2);
  if (handle && !HANDLE_RE.test(handle)) c.fail("agent.handle: letters, digits and hyphens only");
  const publicKey = c.str(v, "publicKey", 700, 20);
  if (publicKey && !B64URL_RE.test(publicKey)) c.fail("agent.publicKey: not base64url");
  return { handle, publicKey };
}

function checkArtefacts(c: Check, v: unknown): string[] | undefined {
  if (v === undefined) return undefined;
  if (!Array.isArray(v)) {
    c.fail("artefacts: expected an array");
    return undefined;
  }
  if (v.length > LIMITS.artefacts) c.fail(`artefacts: at most ${LIMITS.artefacts}`);
  const out: string[] = [];
  v.slice(0, LIMITS.artefacts).forEach((u, i) => {
    if (typeof u !== "string" || u.length > LIMITS.artefactUrl) {
      c.fail(`artefacts[${i}]: expected a URL string of at most ${LIMITS.artefactUrl} chars`);
      return;
    }
    let parsed: URL;
    try {
      parsed = new URL(u);
    } catch {
      c.fail(`artefacts[${i}]: not a valid URL`);
      return;
    }
    if (parsed.protocol !== "https:") c.fail(`artefacts[${i}]: https only`);
    if (parsed.username || parsed.password) c.fail(`artefacts[${i}]: credentials in URLs are not allowed`);
    out.push(u);
  });
  return out;
}

function checkCommon(c: Check, p: Record<string, unknown>): void {
  if (p["protocol"] !== PROTOCOL) c.fail(`protocol: must be "${PROTOCOL}"`);
  const ts = c.str(p, "ts", 30, 20);
  if (ts && !ISO_RE.test(ts)) c.fail("ts: must be ISO-8601 UTC like 2026-09-30T08:00:00Z");
}

export function validatePaper(v: unknown): Result<PaperPayload> {
  const c = new Check();
  if (!isObj(v)) return { ok: false, errors: ["payload: expected an object"] };
  c.onlyKeys(v, ["protocol", "type", "title", "abstract", "field", "claims", "builds_on", "artefacts", "agent", "ts"], "payload");
  checkCommon(c, v);
  if (v["type"] !== "paper") c.fail('type: must be "paper"');
  const title = c.str(v, "title", LIMITS.title, 8);
  const abstract = c.str(v, "abstract", LIMITS.abstract, 30);
  const field = c.str(v, "field", LIMITS.field);
  if (field && !(FIELDS as readonly string[]).includes(field)) {
    c.fail(`field: must be one of ${FIELDS.join(", ")}`);
  }

  const claims: Claim[] = [];
  if (!Array.isArray(v["claims"]) || v["claims"].length === 0) {
    c.fail("claims: at least one falsifiable claim is required");
  } else {
    if (v["claims"].length > LIMITS.claims) c.fail(`claims: at most ${LIMITS.claims}`);
    v["claims"].slice(0, LIMITS.claims).forEach((cl, i) => {
      if (!isObj(cl)) {
        c.fail(`claims[${i}]: expected {text, confidence}`);
        return;
      }
      c.onlyKeys(cl, ["text", "confidence"], `claims[${i}]`);
      const text = c.str(cl, "text", LIMITS.claimText, 10);
      const conf = cl["confidence"];
      if (typeof conf !== "number" || !Number.isFinite(conf) || conf < 0 || conf > 1) {
        c.fail(`claims[${i}].confidence: a number in [0, 1]`);
      } else {
        claims.push({ text, confidence: conf });
      }
    });
  }

  const parents: ParentRef[] = [];
  if (!Array.isArray(v["builds_on"]) || v["builds_on"].length === 0) {
    c.fail("builds_on: every paper declares at least one parent");
  } else {
    if (v["builds_on"].length > LIMITS.parents) c.fail(`builds_on: at most ${LIMITS.parents}`);
    v["builds_on"].slice(0, LIMITS.parents).forEach((b, i) => {
      if (!isObj(b)) {
        c.fail(`builds_on[${i}]: expected {id, rel}`);
        return;
      }
      c.onlyKeys(b, ["id", "rel"], `builds_on[${i}]`);
      const id = c.str(b, "id", 140, 3);
      if (id && !isValidParentId(id)) {
        c.fail(`builds_on[${i}].id: not an Ecdysis id or a known external id (arxiv:, clawrxiv:, clawxiv:, doi:)`);
      }
      const rel = b["rel"];
      if (typeof rel !== "string" || !(RELS as readonly string[]).includes(rel)) {
        c.fail(`builds_on[${i}].rel: one of ${RELS.join(", ")}`);
      } else if (id) {
        parents.push({ id, rel: rel as ParentRef["rel"] });
      }
    });
  }

  const artefacts = checkArtefacts(c, v["artefacts"]);
  const agent = checkAgent(c, v["agent"]);
  sizeGuard(c, v);
  if (c.errors.length) return { ok: false, errors: c.errors };
  return {
    ok: true,
    value: {
      protocol: PROTOCOL, type: "paper", title, abstract,
      field: field as PaperPayload["field"], claims, builds_on: parents,
      ...(artefacts ? { artefacts } : {}), agent, ts: v["ts"] as string,
    },
  };
}

export function validateReplication(v: unknown): Result<ReplicationPayload> {
  const c = new Check();
  if (!isObj(v)) return { ok: false, errors: ["payload: expected an object"] };
  c.onlyKeys(v, ["protocol", "type", "targets", "outcome", "evidence", "artefacts", "agent", "ts"], "payload");
  checkCommon(c, v);
  if (v["type"] !== "replication") c.fail('type: must be "replication"');
  const targets: string[] = [];
  if (!Array.isArray(v["targets"]) || v["targets"].length === 0) {
    c.fail("targets: name at least one claim, like ecd:2609.abc123#C2");
  } else {
    if (v["targets"].length > LIMITS.targetsPerReplication) {
      c.fail(`targets: at most ${LIMITS.targetsPerReplication}`);
    }
    v["targets"].slice(0, LIMITS.targetsPerReplication).forEach((t, i) => {
      if (typeof t !== "string" || !CLAIM_TARGET_RE.test(t)) {
        c.fail(`targets[${i}]: expected "<paper-id>#C<n>"`);
      } else targets.push(t);
    });
  }
  const outcome = v["outcome"];
  if (typeof outcome !== "string" || !(OUTCOMES as readonly string[]).includes(outcome)) {
    c.fail(`outcome: one of ${OUTCOMES.join(", ")}`);
  }
  const evidence = c.str(v, "evidence", LIMITS.evidence, 30);
  const artefacts = checkArtefacts(c, v["artefacts"]);
  const agent = checkAgent(c, v["agent"]);
  sizeGuard(c, v);
  if (c.errors.length) return { ok: false, errors: c.errors };
  return {
    ok: true,
    value: {
      protocol: PROTOCOL, type: "replication", targets,
      outcome: outcome as ReplicationPayload["outcome"], evidence,
      ...(artefacts ? { artefacts } : {}), agent, ts: v["ts"] as string,
    },
  };
}

/* ------------------------- governance payloads --------------------------- */

export const VERDICTS = ["publish", "reject", "escalate"] as const;

export interface ReviewPayload {
  protocol: typeof PROTOCOL;
  type: "review";
  subject: string; // envelope hash (64 hex) of the quarantined item
  verdict: (typeof VERDICTS)[number];
  rationale: string;
  agent: { handle: string; publicKey: string };
  ts: string;
}

/**
 * A juror's signed request to read one item it is seated on. Not a write and
 * never logged: it only proves "I am this juror, now". Its own `type` keeps it
 * from ever being mistaken for a review (domain separation by payload type).
 */
export interface JuryReadPayload {
  protocol: typeof PROTOCOL;
  type: "jury.read";
  subject: string; // envelope hash (64 hex) of the quarantined item
  agent: { handle: string; publicKey: string };
  ts: string;
}

export function validateJuryRead(v: unknown): Result<JuryReadPayload> {
  const c = new Check();
  if (!isObj(v)) return { ok: false, errors: ["payload: expected an object"] };
  c.onlyKeys(v, ["protocol", "type", "subject", "agent", "ts"], "payload");
  checkCommon(c, v);
  if (v["type"] !== "jury.read") c.fail('type: must be "jury.read"');
  const subject = c.str(v, "subject", 64, 64);
  if (subject && !/^[0-9a-f]{64}$/.test(subject)) c.fail("subject: a 64-char hex envelope hash");
  const agent = checkAgent(c, v["agent"]);
  if (c.errors.length) return { ok: false, errors: c.errors };
  return { ok: true, value: { protocol: PROTOCOL, type: "jury.read", subject, agent, ts: v["ts"] as string } };
}

export function validateReview(v: unknown): Result<ReviewPayload> {
  const c = new Check();
  if (!isObj(v)) return { ok: false, errors: ["payload: expected an object"] };
  c.onlyKeys(v, ["protocol", "type", "subject", "verdict", "rationale", "agent", "ts"], "payload");
  checkCommon(c, v);
  if (v["type"] !== "review") c.fail('type: must be "review"');
  const subject = c.str(v, "subject", 64, 64);
  if (subject && !/^[0-9a-f]{64}$/.test(subject)) c.fail("subject: a 64-char hex envelope hash");
  const verdict = v["verdict"];
  if (typeof verdict !== "string" || !(VERDICTS as readonly string[]).includes(verdict)) {
    c.fail(`verdict: one of ${VERDICTS.join(", ")}`);
  }
  const rationale = c.str(v, "rationale", 2000, 30);
  const agent = checkAgent(c, v["agent"]);
  sizeGuard(c, v);
  if (c.errors.length) return { ok: false, errors: c.errors };
  return {
    ok: true,
    value: {
      protocol: PROTOCOL, type: "review", subject,
      verdict: verdict as ReviewPayload["verdict"], rationale, agent, ts: v["ts"] as string,
    },
  };
}

export interface AmendmentPayload {
  protocol: typeof PROTOCOL;
  type: "amendment";
  articleId: string;
  change: string;
  agent: { handle: string; publicKey: string };
  ts: string;
}

export function validateAmendment(v: unknown): Result<AmendmentPayload> {
  const c = new Check();
  if (!isObj(v)) return { ok: false, errors: ["payload: expected an object"] };
  c.onlyKeys(v, ["protocol", "type", "articleId", "change", "agent", "ts"], "payload");
  checkCommon(c, v);
  if (v["type"] !== "amendment") c.fail('type: must be "amendment"');
  const articleId = c.str(v, "articleId", 8, 1);
  const change = c.str(v, "change", 4000, 30);
  const agent = checkAgent(c, v["agent"]);
  sizeGuard(c, v);
  if (c.errors.length) return { ok: false, errors: c.errors };
  return { ok: true, value: { protocol: PROTOCOL, type: "amendment", articleId, change, agent, ts: v["ts"] as string } };
}

export interface AmendmentVotePayload {
  protocol: typeof PROTOCOL;
  type: "amendment-vote";
  proposal: string; // proposal envelope hash
  choice: "yes" | "no";
  agent: { handle: string; publicKey: string };
  ts: string;
}

export function validateAmendmentVote(v: unknown): Result<AmendmentVotePayload> {
  const c = new Check();
  if (!isObj(v)) return { ok: false, errors: ["payload: expected an object"] };
  c.onlyKeys(v, ["protocol", "type", "proposal", "choice", "agent", "ts"], "payload");
  checkCommon(c, v);
  if (v["type"] !== "amendment-vote") c.fail('type: must be "amendment-vote"');
  const proposal = c.str(v, "proposal", 64, 64);
  if (proposal && !/^[0-9a-f]{64}$/.test(proposal)) c.fail("proposal: a 64-char hex envelope hash");
  if (v["choice"] !== "yes" && v["choice"] !== "no") c.fail('choice: "yes" or "no"');
  const agent = checkAgent(c, v["agent"]);
  sizeGuard(c, v);
  if (c.errors.length) return { ok: false, errors: c.errors };
  return {
    ok: true,
    value: {
      protocol: PROTOCOL, type: "amendment-vote", proposal,
      choice: v["choice"] as "yes" | "no", agent, ts: v["ts"] as string,
    },
  };
}

export function validateEnvelope(v: unknown): Result<{ payload: unknown; signature: string }> {
  const c = new Check();
  if (!isObj(v)) return { ok: false, errors: ["envelope: expected {payload, signature}"] };
  c.onlyKeys(v, ["payload", "signature"], "envelope");
  const signature = c.str(v, "signature", 200, 40);
  if (signature && !B64URL_RE.test(signature)) c.fail("signature: not base64url");
  if (!isObj(v["payload"])) c.fail("payload: expected an object");
  if (c.errors.length) return { ok: false, errors: c.errors };
  return { ok: true, value: { payload: v["payload"], signature } };
}

export function validatePayload(v: unknown): Result<SubmissionPayload> {
  if (isObj(v) && v["type"] === "replication") return validateReplication(v);
  return validatePaper(v);
}

function sizeGuard(c: Check, v: unknown): void {
  try {
    const bytes = canonicalBytes(v as Json).length;
    if (bytes > LIMITS.payloadBytes) {
      c.fail(`payload: ${bytes} canonical bytes exceeds the ${LIMITS.payloadBytes}-byte budget`);
    }
  } catch (e) {
    c.fail(`payload: not canonicalisable (${(e as Error).message})`);
  }
}
