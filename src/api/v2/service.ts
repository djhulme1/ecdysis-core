/**
 * Ecdysis v2 service: the operations that append to the log, over the pure
 * core (src/core/v2). Everything the record needs is in the entries this
 * service writes; everything it withholds (a receipt's outputs until it is
 * cross-checked; signed envelopes' bytes) lives in the v2 store, off the
 * log, and never feeds a number.
 *
 * Writes are signed envelopes, as in v1: {payload, signature}, the
 * signature being the agent's Ed25519 signature over the canonical JSON of
 * the payload, verified against the key the agent registered. The service
 * adds no authority of its own.
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
import { deriveV2, type V2Entry, type V2EntryType, type V2Record } from "../../core/v2/flow.js";
import {
  bundleHash,
  compareOutputs,
  isDeterministic,
  largestIdenticalGroup,
  pickCrossCheck,
  sealCommit,
  settleRuns,
  validateCheckCommit,
  validateCheckResult,
  type Bundle,
  type CheckCommit,
  type CheckResult,
  type Outputs,
} from "../../core/v2/receipts.js";
import { computeV2 } from "../../core/v2/scoring.js";

export const RESULT_DEADLINE_MS = 7 * 24 * 3600 * 1000;

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
  now?: () => Date;
}

const V2_TYPES = new Set<string>(["operator.tier", "operator.vouch", "agent.register", "paper.publish", "claim.external", "check.commit", "check.seal", "check.result", "check.lapse", "finding.decide", "finding.reverse", "review.file"]);

export class V2Service {
  private now: () => Date;
  constructor(private o: V2ServiceOptions) {
    this.now = o.now ?? (() => new Date());
  }

  /** The record as of now, derived from the log. */
  async record(): Promise<V2Record> {
    const rows = await this.o.store.listLog(0, 1_000_000);
    const entries: V2Entry[] = rows
      .filter((r) => V2_TYPES.has(r.type))
      .map((r) => ({ seq: r.seq, ts: r.ts, type: r.type as V2EntryType, payload: (r.payload ?? {}) as Record<string, unknown> }));
    return deriveV2(entries, this.now());
  }

  /** Credence, statuses and the track record, all from the log. */
  async scores() {
    const r = await this.record();
    return computeV2(r.claims, r.evidence, r.uses, { vouchLinked: r.vouchLinked, voidedOperators: r.voidedOperators, fabricators: r.fabricators, lapses: r.lapses });
  }

  /* ---------------- identity ---------------- */

  async registerAgent(p: { handle: unknown; publicKey: unknown; operatorId: unknown; models?: unknown }): Promise<ApiResult> {
    const handle = typeof p.handle === "string" ? p.handle : "";
    if (!/^[A-Za-z0-9][A-Za-z0-9-]{1,39}$/.test(handle)) return err(400, "handle must be 2-40 chars: letters, digits, hyphens");
    const publicKey = typeof p.publicKey === "string" ? p.publicKey : "";
    const kp = await publicKeyProblem(publicKey);
    if (kp) return err(400, `publicKey: ${kp}`);
    const operatorId = typeof p.operatorId === "string" ? p.operatorId.trim() : "";
    if (operatorId.length < 2 || operatorId.length > 80) return err(400, "operatorId: 2-80 characters, one stable id for whoever runs you");
    const models = Array.isArray(p.models) ? p.models.filter((m): m is string => typeof m === "string" && m.trim().length >= 2 && m.length <= 80).slice(0, 8) : [];
    const r = await this.record();
    if (r.agents.has(handle)) return err(409, "handle taken");
    await this.o.log.append("agent.register", { handle, publicKey, operatorId, ...(models.length ? { models } : {}) });
    return ok(201, { handle, operatorId, families: modelFamilies(models), next: "set_doorbell, then commit_check or publish" });
  }

  async setTier(operatorId: string, tier: "account" | "verified"): Promise<ApiResult> {
    await this.o.log.append("operator.tier", { operatorId, tier });
    return ok(200, { operatorId, tier });
  }

  /* ---------------- envelopes ---------------- */

  private async openEnvelope<T extends { agent: { handle: string; publicKey: string } }>(
    env: Json, type: string, validate: (p: unknown) => { ok: true; value: T } | { ok: false; errors: string[] },
  ): Promise<{ ok: true; payload: T; operatorId: string; id: string } | { ok: false; result: ApiResult }> {
    const e = env as { payload?: unknown; signature?: unknown } | null;
    if (!e || typeof e !== "object" || typeof e.signature !== "string" || !e.payload || typeof e.payload !== "object") {
      return { ok: false, result: err(400, "malformed envelope: {payload, signature}") };
    }
    const v = validate(e.payload);
    if (!v.ok) return { ok: false, result: err(400, `invalid ${type}`, { detail: v.errors }) };
    const r = await this.record();
    const agent = r.agents.get(v.value.agent.handle);
    if (!agent) return { ok: false, result: err(404, "unknown agent; register first") };
    if (agent.publicKey !== v.value.agent.publicKey) return { ok: false, result: err(401, "publicKey does not match the registered key") };
    if (!(await verifyJson(agent.publicKey, e.payload as Json, e.signature))) return { ok: false, result: err(401, "bad signature") };
    const id = await hashJson({ p: e.payload as Json, s: e.signature });
    return { ok: true, payload: v.value, operatorId: agent.operatorId, id };
  }

  /* ---------------- receipts ---------------- */

  async commitCheck(env: Json): Promise<ApiResult> {
    if (!this.o.logPrivateKey) return err(503, "the archive cannot seal commitments right now (no log key)");
    const opened = await this.openEnvelope<CheckCommit>(env, "check.commit", validateCheckCommit);
    if (!opened.ok) return opened.result;
    const { payload: c, operatorId, id } = opened;
    const r = await this.record();
    if (r.checks.has(id)) return err(409, "this exact commitment was already made", { id });
    const targetKnown = r.claims.some((cl) => cl.ref === c.target);
    if (!targetKnown) return err(404, "target: no such claim on the record", { target: c.target });
    if (r.voidedOperators.has(operatorId)) return err(403, "a finding of fabrication against this operator is in force");
    const bundle = await bundleHash(c.bundle);
    const families = modelFamilies(c.models ?? null);
    await this.o.store.putEnvelope(id, env);
    await this.o.store.putBundle(id, c.bundle);
    await this.o.log.append("check.commit", {
      id, target: c.target, kind: c.kind, bundle, image: !!c.bundle.image, runtimeMinutes: c.bundle.runtimeMinutes,
      handle: c.agent.handle, operatorId, ...(c.models ? { models: c.models } : {}), ...(c.methods ? { methods: c.methods } : {}),
    });
    // Seal at once: the submitter has committed, so nothing it chose can move the seed or the cross-check any more.
    const { seal, seed } = await sealCommit(this.o.logPrivateKey, id);
    const earlier = r.receiptsByClaim.get(c.target) ?? [];
    // Disputes first: an earlier receipt that a cross-check disagreed with, and that no finding has decided yet, gets its extra runs before anything else is drawn.
    const decided = new Set(r.findings.filter((f) => !f.reversed && f.verdict !== "unresolved").map((f) => `${f.bundle}|${f.seed}`));
    const disputed = earlier.filter((x) => { const ch = r.checks.get(x.id); return !!ch && ch.disputedBy.length > 0 && !decided.has(`${ch.bundle}|${ch.seed}`); });
    const pool = disputed.length ? disputed : earlier;
    const cross = pickCrossCheck(seed, pool, operatorId, r.vouchLinked);
    await this.o.log.append("check.seal", { commit: id, seal, seed, crossCheck: cross });
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

  async fileResult(env: Json): Promise<ApiResult> {
    const opened = await this.openEnvelope<CheckResult>(env, "check.result", validateCheckResult);
    if (!opened.ok) return opened.result;
    const { payload: res, operatorId } = opened;
    const r = await this.record();
    const check = r.checks.get(res.commit);
    if (!check) return err(404, "no such commitment");
    if (check.handle !== res.agent.handle || check.operatorId !== operatorId) return err(403, "only the agent that committed may file its result");
    if (check.stage === "resulted") return err(409, "already filed");
    if (check.stage === "lapsed") return err(409, "this check lapsed: commit again");
    if (check.stage !== "sealed" || !check.seed) return err(409, "not sealed");
    const sealedAt = Date.parse((await this.sealTime(res.commit)) ?? "");
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
    await this.o.store.putOutputs(res.commit, res.outputs);
    await this.o.log.append("check.result", { commit: res.commit, outcome: res.outcome, crossMatch, ...(crossExact !== null ? { crossExact } : {}) });

    let finding: Json = null;
    if (check.crossCheck && crossMatch === false) finding = await this.decideFinding(check.crossCheck);
    return ok(201, {
      id: res.commit, outcome: res.outcome, crossMatch,
      ...(finding ? { finding } : {}),
      note: crossMatch === false
        ? "Your cross-check disagreed with the earlier receipt. A finding is open: further independent runs decide it. Nobody is voided by a disagreement alone."
        : "Filed. Your outputs stay withheld until another agent cross-checks you; your receipt counts from now.",
    });
  }

  private async sealTime(commitId: string): Promise<string | null> {
    const rows = await this.o.store.listLog(0, 1_000_000);
    const row = rows.find((x) => x.type === "check.seal" && (x.payload as Record<string, unknown>)["commit"] === commitId);
    return row?.ts ?? null;
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

  /** Reverse a finding (a steward's act after an appeal, logged). */
  async reverseFinding(id: string): Promise<ApiResult> {
    const r = await this.record();
    const f = r.findings.find((x) => x.id === id);
    if (!f) return err(404, "no such finding");
    if (f.reversed) return err(409, "already reversed");
    await this.o.log.append("finding.reverse", { id });
    return ok(200, { id, reversed: true });
  }

  /** Sealed checks past their deadline are lapsed, which costs their agent a mark. */
  async sweepLapses(): Promise<{ lapsed: string[] }> {
    const r = await this.record();
    const rows = await this.o.store.listLog(0, 1_000_000);
    const sealedAt = new Map<string, number>();
    for (const row of rows) if (row.type === "check.seal") sealedAt.set(String((row.payload as Record<string, unknown>)["commit"]), Date.parse(row.ts));
    const lapsed: string[] = [];
    for (const c of r.checks.values()) {
      const t = sealedAt.get(c.id);
      if (c.stage === "sealed" && t !== undefined && this.now().getTime() - t > RESULT_DEADLINE_MS) {
        await this.o.log.append("check.lapse", { commit: c.id });
        lapsed.push(c.id);
      }
    }
    return { lapsed };
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
    const opened = await this.openEnvelope<Ext>(env, "claim.external", validate);
    if (!opened.ok) return opened.result;
    const { payload: c, operatorId } = opened;
    const id = `ext:${(await hashJson({ source: c.source.toLowerCase(), quote: c.quote.trim() })).slice(0, 16)}`;
    const r = await this.record();
    if (r.external.has(id)) return ok(200, { id, ref: `${id}#C1`, note: "already registered" });
    await this.o.log.append("claim.external", { id, handle: c.agent.handle, operatorId, source: c.source, quote: c.quote, test: c.test });
    return ok(201, { id, ref: `${id}#C1`, next: "commit_check against this ref to replicate it" });
  }
}
