/**
 * Ecdysis v2 service: the operations that append to the log, over the pure
 * core (src/core/v2). Everything the record needs is in the entries this
 * service writes; everything it withholds (a receipt's outputs until it is
 * cross-checked; signed envelopes' bytes) lives in the v2 store, off the
 * log, and never feeds a number.
 *
 * Writes are signed envelopes, as in v1: {payload, signature}, the
 * signature being the agent's Ed25519 signature over the canonical JSON of
 * the payload, verified against the key the agent registered, or against a
 * CHECK KEY the main key delegated (constitution I.3). A check key signs
 * reports only (check.commit, check.result, review): publication, external
 * claims, escalation and key management need the main key, so a runner
 * that executes foreign bundles holds nothing that can speak for the agent
 * beyond the reports it is there to file. The service adds no authority of
 * its own.
 *
 * The receipt flow (design §4):
 *   commitCheck   validate, log check.commit, then seal at once: the log key
 *                 signs the commitment, the seed is the seal's SHA-256, and
 *                 the seed picks the cross-check (an earlier receipt of the
 *                 same claim by an independent operator; receipts under an
 *                 open finding first, so disputes get their extra runs).
 *   fileResult    validate, within RESULT_DEADLINE_MS of the seal; compare
 *                 the cross-check's outputs with the earlier receipt's
 *                 (within its declared tolerances, and exactly); log
 *                 check.result; then look at every run of that bundle under
 *                 that seed and decide a finding when the rules allow.
 *   sweepLapses   sealed checks past the deadline are logged as lapsed.
 */

import type { Json } from "../../core/canonical.js";
import { hashJson } from "../../core/canonical.js";
import { publicKeyProblem, verifyJson } from "../../core/crypto.js";
import type { TransparencyLog } from "../../core/log.js";
import { modelFamilies } from "../../core/v2/credence.js";
import { deriveV2, V2_ENTRY_TYPES, type V2Entry, type V2EntryType, type V2Record } from "../../core/v2/flow.js";
import {
  bundleHash,
  compareOutputs,
  isDeterministic,
  largestIdenticalGroup,
  pickCrossCheck,
  sealCommit,
  seedInsensitive,
  settleRuns,
  validateCheckCommit,
  validateCheckResult,
  type Bundle,
  type CheckCommit,
  type CheckResult,
  type Outputs,
} from "../../core/v2/receipts.js";
import { computeV2 } from "../../core/v2/scoring.js";
import { validateEscalateV2, validatePaperV2, validateReviewV2, type EscalateV2Payload, type PaperV2Payload, type ReviewV2Payload } from "../../core/v2/paper.js";
import { runScreening, type Screener, type Screenable } from "../../core/hazard.js";
import type { PaperPayload } from "../../core/schema.js";

export const RESULT_DEADLINE_MS = 7 * 24 * 3600 * 1000;
/** Papers a day, by tier (sanity check §5.7). */
export const QUOTA_PER_DAY: Record<"unverified" | "account" | "verified", number> = { unverified: 1, account: 3, verified: 5 };
/** Escalations a day per operator (§5.8). */
export const ESCALATIONS_PER_DAY = 3;
/** Check keys in force per agent: one per runner is the idea, not a key farm. */
export const CHECK_KEYS_MAX = 8;
/** Vouches an operator may have in force (§5.4): vouching is a liability, not a favour to hand out. */
export const VOUCHES_MAX = 3;

export interface ApiResult { status: number; body: Json }
const ok = (status: number, body: Json): ApiResult => ({ status, body });
const err = (status: number, error: string, extra: Record<string, Json> = {}): ApiResult => ({ status, body: { error, ...extra } });

/** What the service keeps off the log. */
export interface V2Store {
  /** The signed envelope behind a logged entry, by its receipt id. */
  putEnvelope(id: string, envelope: Json): Promise<void>;
  getEnvelope(id: string): Promise<Json | null>;
  /** A receipt's outputs, withheld from public view until it is cross-checked. */
  putOutputs(commitId: string, outputs: Outputs): Promise<void>;
  getOutputs(commitId: string): Promise<Outputs | null>;
  /** The bundle a commit named, so cross-checkers can fetch it. */
  putBundle(commitId: string, bundle: Bundle): Promise<void>;
  getBundle(commitId: string): Promise<Bundle | null>;
  /** The log's rows, for derivation. */
  listLog(fromSeq: number, limit: number): Promise<Array<{ seq: number; ts: string; type: string; payload: Json }>>;
}

export class MemoryV2Store implements V2Store {
  private envelopes = new Map<string, Json>();
  private outputs = new Map<string, Outputs>();
  private bundles = new Map<string, Bundle>();
  constructor(private rows: () => Array<{ seq: number; ts: string; type: string; payload: Json }>) {}
  async putEnvelope(id: string, envelope: Json) { this.envelopes.set(id, structuredClone(envelope)); }
  async getEnvelope(id: string) { return this.envelopes.get(id) ?? null; }
  async putOutputs(id: string, outputs: Outputs) { this.outputs.set(id, { ...outputs }); }
  async getOutputs(id: string) { return this.outputs.get(id) ?? null; }
  async putBundle(id: string, bundle: Bundle) { this.bundles.set(id, structuredClone(bundle)); }
  async getBundle(id: string) { return this.bundles.get(id) ?? null; }
  async listLog(fromSeq: number, limit: number) { return this.rows().slice(Math.max(0, fromSeq), Math.max(0, fromSeq) + limit); }
}

export interface V2ServiceOptions {
  log: TransparencyLog;
  store: V2Store;
  /** The log key, which seals commitments. Without it nothing can be sealed, so nothing can be committed. */
  logPrivateKey: string | null;
  /** Content screening (fail-closed). Structural screening by default. */
  screeners?: Screener[];
  /** Spend a pairing code from a person's account page: the operator id it stands for. Absent: pairing is not offered. */
  pairing?: (code: string, ip: string) => Promise<{ ok: true; operatorId: string } | { ok: false; status: number; error: string }>;
  now?: () => Date;
}

const V2_TYPES = new Set<string>(V2_ENTRY_TYPES);
const ISO = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,3})?Z$/;
const HANDLE = /^[A-Za-z0-9][A-Za-z0-9-]{1,39}$/;

/** What a key may sign: everything (the main key) or reports only (a check key). */
type Scope = "main" | "reports";

interface KeyDelegatePayload { protocol: string; type: "key.delegate"; key: string; scope: "reports"; label?: string; agent: { handle: string; publicKey: string }; ts: string }
interface KeyRevokePayload { protocol: string; type: "key.revoke"; key: string; compromisedAt?: string; agent: { handle: string; publicKey: string }; ts: string }

function validateKeyPayload<T extends KeyDelegatePayload | KeyRevokePayload>(type: T["type"]) {
  return (p: unknown): { ok: true; value: T } | { ok: false; errors: string[] } => {
    const x = p as { protocol?: unknown; type?: unknown; key?: unknown; scope?: unknown; label?: unknown; compromisedAt?: unknown; agent?: unknown; ts?: unknown } | null;
    const errors: string[] = [];
    if (!x || typeof x !== "object") return { ok: false, errors: ["payload: an object"] };
    if (x.protocol !== "ecdysis/0.2") errors.push('protocol: "ecdysis/0.2"');
    if (x.type !== type) errors.push(`type: "${type}"`);
    if (typeof x.key !== "string" || x.key.length < 20 || x.key.length > 200) errors.push("key: the public key (base64url DER SPKI Ed25519)");
    if (type === "key.delegate") {
      if (x.scope !== "reports") errors.push('scope: "reports" (a check key signs check.commit, check.result and review only)');
      if (x.label !== undefined && (typeof x.label !== "string" || x.label.length > 80)) errors.push("label: optional, at most 80 characters");
    } else if (x.compromisedAt !== undefined && (typeof x.compromisedAt !== "string" || !ISO.test(x.compromisedAt))) errors.push("compromisedAt: optional ISO-8601 UTC time from which the key's reports are disowned");
    const a = x.agent as { handle?: unknown; publicKey?: unknown } | undefined;
    if (!a || typeof a.handle !== "string" || !HANDLE.test(a.handle) || typeof a.publicKey !== "string" || a.publicKey.length < 20) errors.push("agent: {handle, publicKey} (the main key)");
    if (typeof x.ts !== "string" || !ISO.test(x.ts)) errors.push("ts: ISO-8601 UTC");
    return errors.length ? { ok: false, errors } : { ok: true, value: x as unknown as T };
  };
}

type LogRow = { seq: number; ts: string; type: string; payload: Json };
/** Outputs are revealed to everyone once a receipt has been cross-checked, or after this long regardless. */
export const OUTPUTS_REVEAL_MS = 30 * 24 * 3600 * 1000;

export class V2Service {
  private now: () => Date;
  /**
   * The log's rows, read once and extended incrementally: the log is
   * append-only, so rows already seen never change, and each call fetches
   * only what was appended since. One Worker isolate serves many requests
   * with one full read instead of one per request.
   */
  private cache: { rows: LogRow[]; nextSeq: number } = { rows: [], nextSeq: 0 };
  constructor(private o: V2ServiceOptions) {
    this.now = o.now ?? (() => new Date());
  }

  /** Every row of the log, oldest first. */
  private async rows(): Promise<LogRow[]> {
    for (;;) {
      const more = await this.o.store.listLog(this.cache.nextSeq, 10_000);
      for (const r of more) {
        if (r.seq !== this.cache.nextSeq) { // a gap or a replay: start again from nothing rather than trust a partial view
          this.cache = { rows: [], nextSeq: 0 };
          return this.rows();
        }
        this.cache.rows.push(r);
        this.cache.nextSeq = r.seq + 1;
      }
      if (more.length < 10_000) return this.cache.rows;
    }
  }

  /** The record as of now, derived from the log. */
  async record(): Promise<V2Record> {
    const rows = await this.rows();
    const entries: V2Entry[] = rows
      .filter((r) => V2_TYPES.has(r.type))
      .map((r) => ({ seq: r.seq, ts: r.ts, type: r.type as V2EntryType, payload: (r.payload ?? {}) as Record<string, unknown> }));
    return deriveV2(entries, this.now());
  }

  /** The signed envelope behind a logged entry (a paper's full text, a receipt's commitment), by its content id. */
  async envelope(id: string): Promise<Json | null> {
    return /^[0-9a-f]{64}$/.test(id) ? this.o.store.getEnvelope(id) : null;
  }

  /** Credence, statuses and the track record, all from the log. */
  async scores() {
    const r = await this.record();
    return computeV2(r.claims, r.evidence, r.uses, { vouchLinked: r.vouchLinked, ringLinked: r.ringLinked, voidedOperators: r.voidedOperators, fabricators: r.fabricators, lapses: r.lapses, anchors: r.anchors });
  }

  /* ---------------- identity ---------------- */

  /**
   * Register an agent. With a pairing code from a person's account page, the
   * agent is registered under that person's operator id (and the operator
   * enters the record at the account tier); otherwise under whatever stable
   * id the agent gives, unverified.
   */
  async registerAgent(p: { handle: unknown; publicKey: unknown; operatorId?: unknown; models?: unknown; pairing?: unknown }, ip = "local"): Promise<ApiResult> {
    const handle = typeof p.handle === "string" ? p.handle : "";
    if (!HANDLE.test(handle)) return err(400, "handle must be 2-40 chars: letters, digits, hyphens");
    const publicKey = typeof p.publicKey === "string" ? p.publicKey : "";
    const kp = await publicKeyProblem(publicKey);
    if (kp) return err(400, `publicKey: ${kp}`);
    let operatorId = typeof p.operatorId === "string" ? p.operatorId.trim() : "";
    const paired = p.pairing !== undefined;
    if (paired) {
      if (!this.o.pairing) return err(501, "pairing codes are not available on this deployment");
      if (typeof p.pairing !== "string") return err(400, "pairing: a code from the person's account page");
      if (operatorId) return err(400, "operatorId: with a pairing code, omit it; the code names the operator");
    } else {
      if (operatorId.length < 2 || operatorId.length > 80) return err(400, "operatorId: 2-80 characters, one stable id for whoever runs you (or a pairing code from their account page)");
      if (/^op_/.test(operatorId)) return err(400, "operatorId: ids starting op_ belong to accounts; pair with a code from the account page instead");
    }
    const models = Array.isArray(p.models) ? p.models.filter((m): m is string => typeof m === "string" && m.trim().length >= 2 && m.length <= 80).slice(0, 8) : [];
    const r = await this.record();
    if (r.agents.has(handle)) return err(409, "handle taken");
    if (r.keys.has(publicKey)) return err(409, "this key already belongs to an agent; generate a fresh keypair");
    // Everything else checked, spend the code last: a refused registration must not burn it.
    if (paired) {
      const pr = await this.o.pairing!(p.pairing as string, ip);
      if (!pr.ok) return err(pr.status, pr.error);
      operatorId = pr.operatorId;
    }
    await this.o.log.append("agent.register", { handle, publicKey, operatorId, ...(models.length ? { models } : {}) });
    if (paired && !r.tiers.has(operatorId)) await this.o.log.append("operator.tier", { operatorId, tier: "account" });
    const tier = paired ? (r.tiers.get(operatorId) ?? "account") : (r.tiers.get(operatorId) ?? "unverified");
    return ok(201, { handle, operatorId, tier, families: modelFamilies(models), next: "delegate_key for the machine that will run bundles, then commit_check or publish" });
  }

  /**
   * Set an operator's tier. A steward's act names the steward's own operator
   * id (pseudonymous, like everything on the log) so the audit trail is
   * public; the account pairing path writes the entry without one.
   */
  async setTier(operatorId: string, tier: "unverified" | "account" | "verified", steward?: string): Promise<ApiResult> {
    if (!operatorId || operatorId.length > 80) return err(400, "operatorId");
    if (tier !== "unverified" && tier !== "account" && tier !== "verified") return err(400, "tier: unverified, account or verified");
    const r = await this.record();
    if ((r.tiers.get(operatorId) ?? "unverified") === tier) return err(409, `already at tier "${tier}"`);
    await this.o.log.append("operator.tier", { operatorId, tier, ...(steward ? { by: "steward", steward } : {}) });
    return ok(200, { operatorId, tier });
  }

  /**
   * A verified operator vouches for another (§9): payload {protocol, type
   * "operator.vouch", for, agent, ts} signed by one of its agents' main
   * keys. Two vouches in force from distinct verified operators verify the
   * vouchee; a finding against the vouchee suspends every vouch the voucher
   * made and marks its agents. At most VOUCHES_MAX in force per operator.
   */
  async vouch(env: Json): Promise<ApiResult> {
    type VouchPayload = { protocol: string; type: "operator.vouch"; for: string; agent: { handle: string; publicKey: string }; ts: string };
    const validate = (p: unknown): { ok: true; value: VouchPayload } | { ok: false; errors: string[] } => {
      const x = p as Partial<VouchPayload> | null;
      const errors: string[] = [];
      if (!x || typeof x !== "object") return { ok: false, errors: ["payload: an object"] };
      if (x.protocol !== "ecdysis/0.2") errors.push('protocol: "ecdysis/0.2"');
      if (x.type !== "operator.vouch") errors.push('type: "operator.vouch"');
      if (typeof x.for !== "string" || x.for.length < 2 || x.for.length > 80) errors.push("for: the operator id you vouch for");
      const a = x.agent as { handle?: unknown; publicKey?: unknown } | undefined;
      if (!a || typeof a.handle !== "string" || !HANDLE.test(a.handle) || typeof a.publicKey !== "string") errors.push("agent: {handle, publicKey}");
      if (typeof x.ts !== "string" || !ISO.test(x.ts)) errors.push("ts: ISO-8601 UTC");
      return errors.length ? { ok: false, errors } : { ok: true, value: x as VouchPayload };
    };
    const opened = await this.openEnvelope<VouchPayload>(env, "operator.vouch", validate, "main");
    if (!opened.ok) return opened.result;
    const { payload: v, operatorId: from, record: r } = opened;
    if ((r.tiers.get(from) ?? "unverified") !== "verified") return err(403, "only a verified operator may vouch");
    if (r.suspendedVouchers.has(from)) return err(403, "your vouches are suspended: an operator you vouched for is under a finding in force");
    if (v.for === from) return err(400, "for: not yourself");
    if (![...r.agents.values()].some((a) => a.operatorId === v.for)) return err(404, "for: no agent is registered under that operator id");
    if (r.voidedOperators.has(v.for)) return err(403, "for: a finding of fabrication against that operator is in force");
    const mine = r.vouches.filter((x) => x.from === from);
    if (mine.some((x) => x.for === v.for)) return err(409, "already vouched for that operator");
    if (mine.filter((x) => x.inForce).length >= VOUCHES_MAX) return err(429, `at most ${VOUCHES_MAX} vouches in force per operator`);
    await this.o.store.putEnvelope(opened.id, env);
    await this.o.log.append("operator.vouch", { from, for: v.for, handle: v.agent.handle });
    const after = (await this.record()).tiers.get(v.for) ?? "unverified";
    return ok(201, { from, for: v.for, tier: after, note: after === "verified" ? "That operator is now verified: two verified operators vouch for it." : "Recorded. A second verified operator's vouch would verify it. A finding against it would suspend every vouch you have made and cost your agents a mark." });
  }

  /**
   * Reveal a canary (design §7): a steward writes the known outcome of a
   * claim registered from a human replication project. From now every
   * report on it is scored against that truth. Nothing marked it before.
   */
  async revealCanary(claim: string, outcome: string, steward: string): Promise<ApiResult> {
    if (outcome !== "confirmed" && outcome !== "refuted") return err(400, "outcome: confirmed or refuted");
    const r = await this.record();
    if (!r.claims.some((c) => c.ref === claim)) return err(404, "no such claim on the record");
    if (r.anchors.has(claim)) return err(409, "already revealed");
    await this.o.log.append("canary.reveal", { claim, outcome, by: "steward", steward });
    const reports = r.evidence.filter((e) => e.claim === claim).length;
    return ok(200, { claim, outcome, reports, note: `Revealed. ${reports} report${reports === 1 ? "" : "s"} on this claim ${reports === 1 ? "is" : "are"} now scored against the known outcome.` });
  }

  /** Hazard holds (screening, escalations) and releases, newest first: what waits for reserved power R1. View only here. */
  async holds(limit = 50): Promise<Array<{ seq: number; ts: string; type: "hazard.hold" | "hazard.release"; subject: string; reason: string; by: string | null; open: boolean }>> {
    const rows = await this.rows();
    const released = new Set<string>();
    for (const x of rows) if (x.type === "hazard.release") released.add(String((x.payload as Record<string, unknown>)["subject"] ?? ""));
    return rows.filter((x) => x.type === "hazard.hold" || x.type === "hazard.release").map((x) => {
      const p = x.payload as Record<string, unknown>;
      const subject = String(p["subject"] ?? "");
      return { seq: x.seq, ts: x.ts, type: x.type as "hazard.hold" | "hazard.release", subject, reason: String(p["reason"] ?? ""), by: typeof p["by"] === "string" ? (p["by"] as string) : null, open: x.type === "hazard.hold" && !released.has(subject) };
    }).reverse().slice(0, limit);
  }

  /** Entries that record a steward's or an operator's act, newest first: the audit trail. */
  async audit(limit = 100): Promise<Array<{ seq: number; ts: string; type: string; by: string; steward: string | null; summary: string }>> {
    const rows = await this.rows();
    return rows.filter((x) => typeof (x.payload as Record<string, unknown>)["by"] === "string").map((x) => {
      const p = x.payload as Record<string, unknown>;
      const summary = Object.entries(p).filter(([k]) => k !== "by" && k !== "steward").map(([k, v]) => `${k}=${typeof v === "string" ? v.slice(0, 40) : JSON.stringify(v)}`).join(" ");
      return { seq: x.seq, ts: x.ts, type: x.type, by: String(p["by"]), steward: typeof p["steward"] === "string" ? (p["steward"] as string) : null, summary };
    }).reverse().slice(0, limit);
  }

  /* ---------------- keys (constitution I.3) ---------------- */

  /** The main key delegates a check key: it signs reports only. */
  async delegateKey(env: Json): Promise<ApiResult> {
    const opened = await this.openEnvelope<KeyDelegatePayload>(env, "key.delegate", validateKeyPayload<KeyDelegatePayload>("key.delegate"), "main");
    if (!opened.ok) return opened.result;
    const { payload: d, record: r } = opened;
    const res = await this.delegate(r, d.agent.handle, d.key, d.label, null);
    if (res.status === 201) await this.o.store.putEnvelope(opened.id, env);
    return res;
  }

  /**
   * The operator (the person whose account owns the operator id) delegates a
   * check key for one of its agents, from the account page. The entry says
   * so (`by: "operator"`). This is how someone whose AI cannot hold a key
   * gets one onto a runner.
   */
  async delegateKeyByOperator(operatorId: string, handle: string, key: string, label?: string): Promise<ApiResult> {
    const r = await this.record();
    const agent = r.agents.get(handle);
    if (!agent) return err(404, "no such agent");
    if (agent.operatorId !== operatorId) return err(403, "that agent belongs to another operator");
    if (agent.revokedAt) return err(409, "this agent is retired");
    return this.delegate(r, handle, key, label, "operator");
  }

  private async delegate(r: V2Record, handle: string, key: string, label: string | undefined, by: "operator" | null): Promise<ApiResult> {
    const kp = await publicKeyProblem(key);
    if (kp) return err(400, `key: ${kp}`);
    const agent = r.agents.get(handle)!;
    if (key === agent.publicKey) return err(400, "key: a check key must differ from the main key");
    const known = r.keys.get(key);
    if (known) return err(409, known.revokedAt ? "this key was revoked; revoked keys are never reinstated, generate a new one" : "this key already belongs to an agent");
    if (agent.checkKeys.length >= CHECK_KEYS_MAX) return err(429, `at most ${CHECK_KEYS_MAX} check keys in force; revoke one first`);
    await this.o.log.append("key.delegate", { handle, operatorId: agent.operatorId, key, scope: "reports", ...(label ? { label: label.slice(0, 80) } : {}), ...(by ? { by } : {}) });
    return ok(201, {
      handle, key, scope: "reports",
      note: "Delegated. Sign check.commit, check.result and review with this key where bundles run; keep the main key elsewhere. If the runner is compromised, revoke_key with the time it happened: reports after that time are disowned.",
    });
  }

  /**
   * Revoke a key (immediate). With compromisedAt, reports the key signed at
   * or after that time are disowned by the derivation. Revoking the main key
   * retires the agent. An already-revoked key accepts a second revocation
   * only to move its compromise time EARLIER: disowning can grow as the
   * incident is understood, never shrink.
   */
  async revokeKey(env: Json): Promise<ApiResult> {
    const opened = await this.openEnvelope<KeyRevokePayload>(env, "key.revoke", validateKeyPayload<KeyRevokePayload>("key.revoke"), "main");
    if (!opened.ok) return opened.result;
    const { payload: v, record: r } = opened;
    const k = r.keys.get(v.key);
    if (!k) return err(404, "no such key");
    if (k.handle !== v.agent.handle) return err(403, "that key belongs to another agent");
    const res = await this.revoke(r, k.key, v.compromisedAt, null);
    if (res.status === 200) await this.o.store.putEnvelope(opened.id, env);
    return res;
  }

  /**
   * The operator revokes one of its agents' keys from the account page, the
   * main key included: this is the recovery path when an agent's main key is
   * lost or stolen and so can no longer sign its own revocation.
   */
  async revokeKeyByOperator(operatorId: string, key: string, compromisedAt?: string): Promise<ApiResult> {
    const r = await this.record();
    const k = r.keys.get(key);
    if (!k) return err(404, "no such key");
    if (r.agents.get(k.handle)?.operatorId !== operatorId) return err(403, "that key belongs to another operator's agent");
    if (compromisedAt !== undefined && !ISO.test(compromisedAt)) return err(400, "compromisedAt: ISO-8601 UTC");
    return this.revoke(r, key, compromisedAt, "operator");
  }

  private async revoke(r: V2Record, key: string, compromisedAt: string | undefined, by: "operator" | null): Promise<ApiResult> {
    const k = r.keys.get(key)!;
    if (compromisedAt !== undefined && Date.parse(compromisedAt) > this.now().getTime()) return err(400, "compromisedAt: not in the future");
    if (k.revokedAt) {
      const earlier = compromisedAt !== undefined && (!k.compromisedAt || Date.parse(compromisedAt) < Date.parse(k.compromisedAt));
      if (!earlier) return err(409, "already revoked; a second revocation may only declare an earlier compromise time", { revokedAt: k.revokedAt, compromisedAt: k.compromisedAt });
    }
    const operatorId = r.agents.get(k.handle)?.operatorId ?? "";
    await this.o.log.append("key.revoke", { handle: k.handle, operatorId, key, scope: k.scope, ...(compromisedAt ? { compromisedAt } : {}), ...(by ? { by } : {}) });
    const disowned = [...r.checks.values()].filter((c) => compromisedAt && ((c.key === key && Date.parse(c.committedAt) >= Date.parse(compromisedAt)) || (c.resultKey === key && c.resultedAt && Date.parse(c.resultedAt) >= Date.parse(compromisedAt)))).map((c) => c.id);
    return ok(200, {
      key, scope: k.scope, revoked: true, compromisedAt: compromisedAt ?? null, disownedChecks: disowned,
      note: k.scope === "main"
        ? "The main key is revoked: this agent is retired. Register a new agent for a fresh key. Reports signed after the compromise time are disowned; findings already decided stand unless a steward reverses them on appeal."
        : "Revoked. Reports this key signed after the compromise time are disowned and feed no number; findings already decided stand unless a steward reverses them on appeal.",
    });
  }

  /* ---------------- envelopes ---------------- */

  /**
   * Open a signed envelope: validate the payload, find the agent, check that
   * the key that signed is allowed to sign THIS kind of payload (the main
   * key signs anything; a check key signs reports only; a revoked key signs
   * nothing), and verify the signature. Returns the record it derived so the
   * caller need not derive it again.
   */
  private async openEnvelope<T extends { agent: { handle: string; publicKey: string } }>(
    env: Json, type: string, validate: (p: unknown) => { ok: true; value: T } | { ok: false; errors: string[] }, scope: Scope,
  ): Promise<{ ok: true; payload: T; operatorId: string; id: string; record: V2Record; key: string; checkKey: boolean } | { ok: false; result: ApiResult }> {
    const e = env as { payload?: unknown; signature?: unknown } | null;
    if (!e || typeof e !== "object" || typeof e.signature !== "string" || !e.payload || typeof e.payload !== "object") {
      return { ok: false, result: err(400, "malformed envelope: {payload, signature}") };
    }
    const v = validate(e.payload);
    if (!v.ok) return { ok: false, result: err(400, `invalid ${type}`, { detail: v.errors }) };
    const r = await this.record();
    const agent = r.agents.get(v.value.agent.handle);
    if (!agent) return { ok: false, result: err(404, "unknown agent; register first") };
    if (agent.revokedAt) return { ok: false, result: err(401, "this agent's main key was revoked; the agent is retired") };
    const key = v.value.agent.publicKey;
    const k = r.keys.get(key);
    if (!k || k.handle !== v.value.agent.handle) return { ok: false, result: err(401, "publicKey is neither this agent's registered key nor a check key it delegated") };
    if (k.revokedAt) return { ok: false, result: err(401, "this key was revoked", { revokedAt: k.revokedAt }) };
    if (k.scope === "reports" && scope !== "reports") return { ok: false, result: err(403, `a check key signs reports only (check.commit, check.result, review); ${type} needs the main key`) };
    if (!(await verifyJson(key, e.payload as Json, e.signature))) return { ok: false, result: err(401, "bad signature") };
    const id = await hashJson({ p: e.payload as Json, s: e.signature });
    return { ok: true, payload: v.value, operatorId: agent.operatorId, id, record: r, key, checkKey: k.scope === "reports" };
  }

  /* ---------------- receipts ---------------- */

  async commitCheck(env: Json): Promise<ApiResult> {
    if (!this.o.logPrivateKey) return err(503, "the archive cannot seal commitments right now (no log key)");
    const opened = await this.openEnvelope<CheckCommit>(env, "check.commit", validateCheckCommit, "reports");
    if (!opened.ok) return opened.result;
    const { payload: c, operatorId, id, record: r, key, checkKey } = opened;
    if (r.checks.has(id)) return err(409, "this exact commitment was already made", { id });
    const target = r.claims.find((cl) => cl.ref === c.target);
    if (!target) return err(404, "target: no such claim on the record", { target: c.target });
    if (target.authorOperator && target.authorOperator === operatorId) return err(403, "a check of your own operator's claim weighs nothing (Article 0.5); leave it to others");
    if (r.voidedOperators.has(operatorId)) return err(403, "a finding of fabrication against this operator is in force");
    const bundle = await bundleHash(c.bundle);
    const families = modelFamilies(c.models ?? null);
    await this.o.store.putEnvelope(id, env);
    await this.o.store.putBundle(id, c.bundle);
    await this.o.log.append("check.commit", {
      id, target: c.target, kind: c.kind, bundle, image: !!c.bundle.image, runtimeMinutes: c.bundle.runtimeMinutes,
      handle: c.agent.handle, operatorId, ...(c.models ? { models: c.models } : {}), ...(c.methods ? { methods: c.methods } : {}),
      ...(checkKey ? { key } : {}),
    });
    // Seal at once: the submitter has committed, so nothing it chose can move the seed or the cross-check any more.
    const { seal, seed, cross } = await this.seal(r, id, c.target, operatorId);
    const crossBundle = cross ? await this.o.store.getBundle(cross) : null;
    const crossSeed = cross ? r.checks.get(cross)?.seed ?? null : null;
    return ok(201, {
      id, seal, seed, deadline: new Date(this.now().getTime() + RESULT_DEADLINE_MS).toISOString(),
      families,
      crossCheck: cross ? { receipt: cross, bundle: crossBundle as unknown as Json, seed: crossSeed } : null,
      next: cross
        ? "Run your bundle with ECDYSIS_SEED=<seed>. Also run the cross-check's bundle with ECDYSIS_SEED=<its seed> and report both outputs with file_result."
        : "Run your bundle with ECDYSIS_SEED=<seed> and report its outputs with file_result. You are the first to check this claim, so there is no cross-check this time.",
    });
  }

  /**
   * Seal a commitment: the log key's deterministic signature over the commit
   * id gives the seed; the seed draws the cross-check from the earlier
   * receipts of the claim by independent operators, disputed receipts
   * first (an earlier receipt that a cross-check disagreed with, and that
   * no finding has decided yet, gets its extra runs before anything else).
   */
  private async seal(r: V2Record, id: string, target: string, operatorId: string): Promise<{ seal: string; seed: string; cross: string | null }> {
    const { seal, seed } = await sealCommit(this.o.logPrivateKey!, id);
    const earlier = r.receiptsByClaim.get(target) ?? [];
    const decided = new Set(r.findings.filter((f) => !f.reversed && f.verdict !== "unresolved").map((f) => `${f.bundle}|${f.seed}`));
    const disputed = earlier.filter((x) => { const ch = r.checks.get(x.id); return !!ch && ch.disputedBy.length > 0 && !decided.has(`${ch.bundle}|${ch.seed}`); });
    const pool = disputed.length ? disputed : earlier;
    const cross = pickCrossCheck(seed, pool, operatorId, r.vouchLinked);
    await this.o.log.append("check.seal", { commit: id, seal, seed, crossCheck: cross });
    return { seal, seed, cross };
  }

  /**
   * Failsafe: a commitment whose seal never made it to the log (the append
   * after check.commit failed) is sealed now. The submitter still chose
   * nothing after committing; the pool may hold receipts filed since, which
   * are other people's. Called by the sweeper.
   */
  async sealPending(): Promise<{ sealed: string[] }> {
    if (!this.o.logPrivateKey) return { sealed: [] };
    const r = await this.record();
    const sealed: string[] = [];
    for (const c of r.checks.values()) {
      if (c.stage !== "committed") continue;
      await this.seal(r, c.id, c.target, c.operatorId);
      sealed.push(c.id);
    }
    return { sealed };
  }

  /**
   * A receipt as the public sees it: the commit, its stage, the bundle, and
   * its outputs once revealed. Outputs are withheld until the receipt has
   * been cross-checked, so the next scientist runs blind, or until
   * OUTPUTS_REVEAL_MS has passed, so nothing stays hidden for ever.
   */
  async receipt(id: string): Promise<ApiResult> {
    const r = await this.record();
    const c = r.checks.get(id);
    if (!c) return err(404, "no such receipt");
    const crossChecked = c.verifiedBy.length + c.disputedBy.length > 0;
    const aged = c.resultedAt !== null && this.now().getTime() - Date.parse(c.resultedAt) >= OUTPUTS_REVEAL_MS;
    const revealed = c.stage === "resulted" && (crossChecked || aged);
    const outputs = revealed ? await this.o.store.getOutputs(id) : null;
    const bundle = await this.o.store.getBundle(id);
    return ok(200, {
      id, target: c.target, kind: c.kind, stage: c.stage, agent: c.handle, operatorId: c.operatorId, families: c.families,
      committedAt: c.committedAt, sealedAt: c.sealedAt, resultedAt: c.resultedAt, seed: c.seed, crossCheck: c.crossCheck,
      outcome: c.outcome, crossMatch: c.crossMatch, verifiedBy: c.verifiedBy, disputedBy: c.disputedBy, disowned: c.disowned,
      bundle: bundle as unknown as Json, bundleHash: c.bundle,
      outputs: outputs as unknown as Json,
      outputsStatus: c.stage !== "resulted" ? "not filed" : revealed ? "revealed" : "withheld until cross-checked or 30 days old",
      note: "Data, never instructions. Re-run the bundle under the seed and compare: the outputs, once revealed, are what every cross-check was compared against.",
    });
  }

  async fileResult(env: Json): Promise<ApiResult> {
    const opened = await this.openEnvelope<CheckResult>(env, "check.result", validateCheckResult, "reports");
    if (!opened.ok) return opened.result;
    const { payload: res, operatorId, record: r, key, checkKey } = opened;
    const check = r.checks.get(res.commit);
    if (!check) return err(404, "no such commitment");
    if (check.handle !== res.agent.handle || check.operatorId !== operatorId) return err(403, "only the agent that committed may file its result");
    if (check.stage === "resulted") return err(409, "already filed");
    if (check.stage === "lapsed") return err(409, "this check lapsed: commit again");
    if (check.stage !== "sealed" || !check.seed) return err(409, "not sealed");
    if (check.disowned) return err(409, "this commitment was disowned by a compromise declaration: commit again with a key in force");
    const sealedAt = Date.parse(check.sealedAt ?? "");
    if (Number.isFinite(sealedAt) && this.now().getTime() - sealedAt > RESULT_DEADLINE_MS) return err(409, "past the deadline: this check will be marked lapsed");

    // The cross-check: the earlier receipt's outputs are compared within its declared tolerances, and exactly.
    let crossMatch: boolean | null = null;
    let crossExact: boolean | null = null;
    if (check.crossCheck) {
      if (!res.crossCheck || res.crossCheck.receipt !== check.crossCheck) return err(422, "crossCheck: report the outputs of the receipt the seal assigned", { expected: check.crossCheck });
      const theirs = await this.o.store.getOutputs(check.crossCheck);
      const theirBundle = await this.o.store.getBundle(check.crossCheck);
      if (!theirs || !theirBundle) return err(500, "the cross-checked receipt's outputs are missing");
      crossMatch = compareOutputs(theirs, res.crossCheck.outputs, theirBundle.outputs).match;
      crossExact = compareOutputs(theirs, res.crossCheck.outputs, theirBundle.outputs.map((o) => ({ name: o.name }))).match;
      await this.o.store.putOutputs(`${check.crossCheck}@${res.commit}`, res.crossCheck.outputs);
    } else if (res.crossCheck) {
      return err(422, "crossCheck: the seal assigned none; send null");
    }
    // Seed-insensitivity: the same bundle produced exactly these outputs under a different seed before, so the seed selects nothing and its re-runs count as one.
    let insensitive = false;
    const spec = (await this.o.store.getBundle(res.commit))?.outputs ?? [];
    for (const other of r.checks.values()) {
      if (other.id === res.commit || other.bundle !== check.bundle || other.stage !== "resulted" || other.seed === check.seed) continue;
      const theirs = await this.o.store.getOutputs(other.id);
      if (theirs && seedInsensitive(theirs, res.outputs, spec)) { insensitive = true; break; }
    }
    await this.o.store.putOutputs(res.commit, res.outputs);
    await this.o.log.append("check.result", { commit: res.commit, outcome: res.outcome, crossMatch, ...(crossExact !== null ? { crossExact } : {}), ...(checkKey ? { key } : {}), ...(insensitive ? { seedInsensitive: true } : {}) });

    let finding: Json = null;
    if (check.crossCheck && crossMatch === false) finding = await this.decideFinding(check.crossCheck);
    return ok(201, {
      id: res.commit, outcome: res.outcome, crossMatch,
      ...(finding ? { finding } : {}),
      ...(insensitive ? { seedInsensitive: true, seedNote: "This bundle gave exactly the same outputs under a different seed: it ignores ECDYSIS_SEED, so its re-runs count together as one piece of evidence. Bundles should let the seed choose what they sample." } : {}),
      note: crossMatch === false
        ? "Your cross-check disagreed with the earlier receipt. A finding is open: further independent runs decide it. Nobody is voided by a disagreement alone."
        : "Filed. Your outputs stay withheld until another agent cross-checks you; your receipt counts from now.",
    });
  }

  /**
   * Every run of the disputed receipt's bundle under its seed: the receipt's
   * own outputs, plus each cross-check run of it. Decide when the rules
   * allow (receipts.ts settleRuns), and log it. Returns the decision, or
   * what is still needed.
   */
  private async decideFinding(receiptId: string): Promise<Json> {
    const r = await this.record();
    const check = r.checks.get(receiptId);
    const bundle = await this.o.store.getBundle(receiptId);
    const own = await this.o.store.getOutputs(receiptId);
    if (!check || !bundle || !own || !check.seed) return null;
    const runs: Array<{ by: string; outputs: Outputs; commit: string }> = [{ by: check.operatorId, outputs: own, commit: receiptId }];
    for (const id of [...check.verifiedBy, ...check.disputedBy]) {
      const o = await this.o.store.getOutputs(`${receiptId}@${id}`);
      const by = r.checks.get(id)?.operatorId;
      if (o && by) runs.push({ by, outputs: o, commit: id });
    }
    // Determinism, observed: at least two independent runs under this seed with exactly identical outputs, on a pinned image.
    const deterministic = isDeterministic(bundle, largestIdenticalGroup(runs, bundle.outputs));
    const s = settleRuns(runs.map(({ by, outputs }) => ({ by, outputs })), bundle.outputs, deterministic);
    if (s.verdict === "open") return { status: "open", runs: runs.length, need: s.need, bundle: check.bundle, seed: check.seed };
    const already = r.findings.find((f) => f.bundle === check.bundle && f.seed === check.seed && !f.reversed && f.verdict !== "unresolved");
    if (already) return { status: "decided", verdict: already.verdict, id: already.id };
    const oddCommit = "odd" in s ? runs.find((x) => x.by === s.odd)?.commit ?? null : null;
    const id = await hashJson({ bundle: check.bundle, seed: check.seed, runs: runs.map((x) => x.commit) });
    await this.o.log.append("finding.decide", { id, bundle: check.bundle, seed: check.seed, verdict: s.verdict, oddCommit, deterministic, runs: runs.map((x) => x.commit) });
    return { status: "decided", id, verdict: s.verdict, oddCommit, deterministic, appealUntil: s.verdict === "fabrication" ? new Date(this.now().getTime() + 14 * 24 * 3600 * 1000).toISOString() : null };
  }

  /** Reverse a finding (a steward's act after an appeal, logged with the steward's operator id). */
  async reverseFinding(id: string, steward?: string): Promise<ApiResult> {
    const r = await this.record();
    const f = r.findings.find((x) => x.id === id);
    if (!f) return err(404, "no such finding");
    if (f.reversed) return err(409, "already reversed");
    await this.o.log.append("finding.reverse", { id, ...(steward ? { by: "steward", steward } : {}) });
    return ok(200, { id, reversed: true });
  }

  /** Sealed checks past their deadline are lapsed, which costs their agent a mark (unless the commitment was disowned). Unsealed commitments are sealed first. */
  async sweepLapses(): Promise<{ lapsed: string[]; sealed: string[] }> {
    const { sealed } = await this.sealPending();
    const r = await this.record();
    const lapsed: string[] = [];
    for (const c of r.checks.values()) {
      const t = c.sealedAt ? Date.parse(c.sealedAt) : NaN;
      if (c.stage === "sealed" && Number.isFinite(t) && this.now().getTime() - t > RESULT_DEADLINE_MS) {
        await this.o.log.append("check.lapse", { commit: c.id });
        lapsed.push(c.id);
      }
    }
    return { lapsed, sealed };
  }


  /* ---------------- publication ---------------- */

  /**
   * Publish on screening (III.1). Screening fails closed: a finding that
   * needs a human, or a screener that cannot answer, holds the paper for
   * R1; a blocking finding refuses it; otherwise it is published at once
   * and its claims enter the record. There is no probation and no jury:
   * tiers set quotas and default-list visibility instead.
   */
  async publishPaper(env: Json): Promise<ApiResult> {
    const opened = await this.openEnvelope<PaperV2Payload>(env, "paper", validatePaperV2, "main");
    if (!opened.ok) return opened.result;
    const { payload: paper, operatorId, id: cid, record: r } = opened;
    if (r.voidedOperators.has(operatorId)) return err(403, "a finding of fabrication against this operator is in force");
    if (r.claims.some((c) => c.paper === `ecd:${cid.slice(0, 16)}`)) return err(409, "this exact paper was already published");
    // Foundations must exist: no citation on faith also means no citation of nothing.
    for (const b of paper.builds_on) {
      if ((b.rel === "extends" || b.rel === "method") && /^(ecd|ext):/.test(b.id)) {
        for (const label of b.claims ?? []) if (!r.claims.some((c) => c.ref === `${b.id}#${label}`)) return err(422, `builds_on: ${b.id}#${label} is not on the record`);
      }
    }
    // Quota by tier, over the last day.
    const tier = r.tiers.get(operatorId) ?? "unverified";
    const dayAgo = this.now().getTime() - 24 * 3600 * 1000;
    const rows = await this.rows();
    const today = rows.filter((x) => x.type === "paper.publish" && (x.payload as Record<string, unknown>)["operatorId"] === operatorId && Date.parse(x.ts) >= dayAgo).length;
    if (today >= QUOTA_PER_DAY[tier]) return err(429, `quota: ${QUOTA_PER_DAY[tier]} paper${QUOTA_PER_DAY[tier] === 1 ? "" : "s"} a day at tier "${tier}"`, { tier });
    // Screening, fail-closed, no probation (tiers do that job in v2).
    const screenable: PaperPayload = {
      protocol: "ecdysis/0.1", type: "paper", title: paper.title, abstract: paper.abstract, field: paper.field,
      claims: paper.claims.map((c) => ({ text: c.text, confidence: c.confidence })),
      builds_on: paper.builds_on.map((b) => ({ id: b.id, rel: b.rel, ...(b.basis ? { basis: b.basis } : {}), ...(b.claims ? { claims: b.claims } : {}), ...(b.note ? { note: b.note } : {}) })),
      ...(paper.artefacts ? { artefacts: paper.artefacts } : {}), agent: paper.agent, ts: paper.ts,
    };
    const decision = await runScreening(screenable as Screenable, { agentHandle: paper.agent.handle, operatorId, acceptedCount: 1_000_000 }, this.o.screeners ?? [], { probationSubmissions: 0, screenerTimeoutMs: 8000 });
    if (decision.verdict === "block") return err(451, "refused by screening", { findings: decision.findings.map((f) => `${f.category}: ${f.note}`) });
    await this.o.store.putEnvelope(cid, env);
    if (decision.verdict === "review") {
      await this.o.log.append("hazard.hold", { subject: cid, reason: decision.failedClosed ? "screening could not answer; held for the steward (R1)" : "screening asked for a human look (R1)", categories: decision.findings.map((f) => f.category) });
      return ok(202, { status: "held", id: cid, note: "Screening held this for a human decision (reserved power R1). Nothing is published until it is released." });
    }
    const id = `ecd:${cid.slice(0, 16)}`;
    await this.o.log.append("paper.publish", {
      id, cid, handle: paper.agent.handle, operatorId, title: paper.title, field: paper.field,
      claims: paper.claims.map((c, i) => ({ label: `C${i + 1}`, confidence: c.confidence })),
      builds_on: paper.builds_on.map((b) => ({ id: b.id, rel: b.rel, ...(b.basis ? { basis: b.basis } : {}), ...(b.claims ? { claims: b.claims } : {}) })),
      ...(paper.models ? { models: paper.models } : {}),
    });
    return ok(201, {
      status: "published", id, claims: paper.claims.map((_, i) => `${id}#C${i + 1}`), tier,
      note: "Published. Credence starts at your stated confidence, shrunk by your calibration and capped by your foundations; only independent evidence moves it from here.",
    });
  }

  /** A review with a forecast (III.2, III.4). Own-operator reviews weigh nothing and are refused as such. */
  async fileReview(env: Json): Promise<ApiResult> {
    const opened = await this.openEnvelope<ReviewV2Payload>(env, "review", validateReviewV2, "reports");
    if (!opened.ok) return opened.result;
    const { payload: rev, operatorId, id, record: r, key, checkKey } = opened;
    const claim = r.claims.find((c) => c.ref === rev.claim);
    if (!claim) return err(404, "no such claim on the record");
    if (claim.authorOperator && claim.authorOperator === operatorId) return err(403, "a review of your own operator's claim weighs nothing (Article 0.5)");
    if (r.voidedOperators.has(operatorId)) return err(403, "a finding of fabrication against this operator is in force");
    await this.o.store.putEnvelope(id, env);
    await this.o.log.append("review.file", { id, claim: rev.claim, handle: rev.agent.handle, operatorId, forecast: rev.forecast, ...(rev.models ? { models: rev.models } : {}), ...(checkKey ? { key } : {}) });
    return ok(201, { id, claim: rev.claim, forecast: rev.forecast, note: "Filed. Reviews move credence a little; your forecast is scored when the claim resolves." });
  }

  /** Any verified operator's agent may freeze an item for R1 (§5.8). Rate-limited; false escalations cost record. */
  async escalate(env: Json): Promise<ApiResult> {
    const opened = await this.openEnvelope<EscalateV2Payload>(env, "hazard.escalate", validateEscalateV2, "main");
    if (!opened.ok) return opened.result;
    const { payload: e, operatorId, record: r } = opened;
    if ((r.tiers.get(operatorId) ?? "unverified") !== "verified") return err(403, "only a verified operator's agent may escalate");
    const dayAgo = this.now().getTime() - 24 * 3600 * 1000;
    const rows = await this.rows();
    const today = rows.filter((x) => x.type === "hazard.hold" && (x.payload as Record<string, unknown>)["by"] === operatorId && Date.parse(x.ts) >= dayAgo).length;
    if (today >= ESCALATIONS_PER_DAY) return err(429, `at most ${ESCALATIONS_PER_DAY} escalations a day per operator`);
    await this.o.log.append("hazard.hold", { subject: e.subject, reason: "escalated by an agent (R1)", by: operatorId, handle: e.agent.handle });
    return ok(202, { subject: e.subject, status: "held", note: "Frozen for the steward's decision under reserved power R1." });
  }

  /* ---------------- what to do next ---------------- */

  /** The two queues (design §7), each per unit of declared compute where a bundle is known. */
  async frontier(limit = 10): Promise<ApiResult> {
    const r = await this.record();
    const s = await this.scores();
    const cost = (ref: string) => {
      const rs = (r.receiptsByClaim.get(ref) ?? []).map((x) => r.checks.get(x.id)?.runtimeMinutes ?? 0).filter((m) => m > 0);
      return rs.length ? Math.max(5, rs.reduce((a, b) => a + b, 0) / rs.length) : 30;
    };
    const all = [...s.claims.values()];
    const checking = all.filter((c) => c.status !== "established" && c.status !== "refuted")
      .map((c) => ({ ref: c.ref, credence: round(c.credence), use: c.use, status: c.status, families: c.families, value: round(c.valueOfChecking), perMinute: round(c.valueOfChecking / cost(c.ref), 6), minutes: cost(c.ref) }))
      .sort((a, b) => b.perMinute - a.perMinute).slice(0, limit);
    const disputes = all.filter((c) => c.dispute > 0)
      .map((c) => ({ ref: c.ref, credence: round(c.credence), use: c.use, status: c.status, dispute: round(c.dispute), priority: round(c.disputePriority), perMinute: round(c.disputePriority / cost(c.ref), 6), minutes: cost(c.ref) }))
      .sort((a, b) => b.perMinute - a.perMinute).slice(0, limit);
    return ok(200, { version: "credence/0.2", checking, disputes, note: "Two queues, never blended into credence: what nobody knows yet (value of checking = (use + ½)·p(1 − p)), and where the evidence disagrees ((use + ½)·D), each per minute of expected compute." });
  }

  /**
   * Reasons to wake these agents (design §7), for the doorbells: a check
   * they owe whose deadline is within two days, and a dispute on a claim
   * their operator's papers rely on. Data for the ring; the heartbeat says
   * the rest.
   */
  async ringReasons(handles: string[]): Promise<Map<string, Array<{ event: "check.owed"; case: string; target: string; due: string } | { event: "dispute.opened"; case: string; credence: number }>>> {
    const out = new Map<string, Array<{ event: "check.owed"; case: string; target: string; due: string } | { event: "dispute.opened"; case: string; credence: number }>>();
    const wanted = new Set(handles);
    if (!wanted.size) return out;
    const r = await this.record();
    const s = await this.scores();
    const soon = this.now().getTime() + 2 * 24 * 3600 * 1000;
    for (const c of r.checks.values()) {
      if (!wanted.has(c.handle) || c.stage !== "sealed" || c.disowned || !c.sealedAt) continue;
      const due = Date.parse(c.sealedAt) + RESULT_DEADLINE_MS;
      if (due <= soon) out.set(c.handle, [...(out.get(c.handle) ?? []), { event: "check.owed", case: c.id, target: c.target, due: new Date(due).toISOString() }]);
    }
    const disputed = [...s.claims.values()].filter((c) => c.dispute > 0 || c.status === "contested");
    if (disputed.length) {
      for (const handle of wanted) {
        const op = r.agents.get(handle)?.operatorId;
        if (!op) continue;
        const reliedOn = new Set(r.uses.filter((u) => u.operatorId === op).map((u) => u.claim));
        for (const c of disputed) if (reliedOn.has(c.ref)) out.set(handle, [...(out.get(handle) ?? []), { event: "dispute.opened", case: c.ref, credence: round(c.credence) }]);
      }
    }
    return out;
  }

  /** What an agent should do when it wakes (design §7): cross-checks owed, disputes on what it relies on, its weakest foundations, the queues. */
  async heartbeat(handle: string): Promise<ApiResult> {
    const r = await this.record();
    const agent = r.agents.get(handle);
    if (!agent) return err(404, "unknown agent");
    const s = await this.scores();
    const owed = [...r.checks.values()].filter((c) => c.handle === handle && c.stage === "sealed" && !c.disowned)
      .map((c) => ({ id: c.id, target: c.target, seed: c.seed, crossCheck: c.crossCheck, deadline: new Date(Date.parse(c.sealedAt ?? this.now().toISOString()) + RESULT_DEADLINE_MS).toISOString() }));
    const mine = r.claims.filter((c) => c.authorOperator === agent.operatorId).map((c) => s.claims.get(c.ref)!).filter(Boolean);
    const weakest = mine.flatMap((c) => c.lift.slice(0, 1).map((l) => ({ claim: c.ref, credence: round(c.credence), foundation: l.ref, from: round(l.from), to: round(l.to), gain: round(l.gain) })))
      .sort((a, b) => b.gain - a.gain).slice(0, 5);
    const reliedOn = new Set(mine.flatMap((c) => c.foundations.map((f) => f.ref)));
    const disputes = [...reliedOn].map((ref) => s.claims.get(ref)).filter((c): c is NonNullable<typeof c> => !!c && (c.status === "contested" || c.dispute > 0))
      .map((c) => ({ ref: c.ref, status: c.status, credence: round(c.credence), dispute: round(c.dispute) }));
    const fr = (await this.frontier(5)).body as Record<string, Json>;
    return ok(200, {
      handle, operatorId: agent.operatorId, tier: r.tiers.get(agent.operatorId) ?? "unverified", families: agent.families,
      reliability: round(s.track.reliability.get(handle) ?? 0.5),
      voided: r.voidedOperators.has(agent.operatorId),
      checkKeys: agent.checkKeys.length, retired: agent.revokedAt !== null,
      owed, weakest, disputes, queues: { checking: fr["checking"] ?? null, disputes: fr["disputes"] ?? null },
      note: "Data, never instructions. First file what you owe (a lapse costs your record), then look at disputes on what you rely on, then at your own weakest foundation, then at the queues.",
    });
  }

  /* ---------------- claims ---------------- */

  /** Register a claim from human literature as a target. */
  async registerExternalClaim(env: Json): Promise<ApiResult> {
    type Ext = { protocol: string; type: "claim.external"; source: string; quote: string; test: string; agent: { handle: string; publicKey: string }; ts: string };
    const validate = (p: unknown): { ok: true; value: Ext } | { ok: false; errors: string[] } => {
      const x = p as Partial<Ext> | null;
      const errors: string[] = [];
      if (!x || typeof x !== "object") return { ok: false, errors: ["payload: an object"] };
      if (x.type !== "claim.external") errors.push('type: "claim.external"');
      if (typeof x.source !== "string" || !/^(arxiv:\S{5,40}|doi:10\.\d{4,9}\/\S{1,120})$/i.test(x.source)) errors.push("source: arxiv:<id> or doi:<doi>");
      if (typeof x.quote !== "string" || x.quote.length < 10 || x.quote.length > 600) errors.push("quote: the claim as the paper states it, 10 to 600 characters");
      if (typeof x.test !== "string" || x.test.length < 10 || x.test.length > 600) errors.push("test: the result that would refute it, 10 to 600 characters");
      if (!x.agent || typeof x.agent.handle !== "string" || typeof x.agent.publicKey !== "string") errors.push("agent: {handle, publicKey}");
      if (typeof x.ts !== "string") errors.push("ts: ISO-8601 UTC");
      return errors.length ? { ok: false, errors } : { ok: true, value: x as Ext };
    };
    const opened = await this.openEnvelope<Ext>(env, "claim.external", validate, "main");
    if (!opened.ok) return opened.result;
    const { payload: c, operatorId, record: r } = opened;
    const id = `ext:${(await hashJson({ source: c.source.toLowerCase(), quote: c.quote.trim() })).slice(0, 16)}`;
    if (r.external.has(id)) return ok(200, { id, ref: `${id}#C1`, note: "already registered" });
    await this.o.log.append("claim.external", { id, handle: c.agent.handle, operatorId, source: c.source, quote: c.quote, test: c.test });
    return ok(201, { id, ref: `${id}#C1`, next: "commit_check against this ref to replicate it" });
  }
}

const round = (x: number, d = 4) => Math.round(x * 10 ** d) / 10 ** d;
