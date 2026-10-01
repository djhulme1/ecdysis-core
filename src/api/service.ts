/**
 * The Ecdysis service: every rule that decides what enters the scientific
 * record lives here, independent of HTTP, so the whole policy is unit-testable
 * and auditable in one place.
 *
 * Submission path (the order matters and is part of the security design):
 *   parse -> schema -> idempotency -> identity -> signature -> sanitise
 *        -> screening -> log append -> publish
 * Identity is checked before signature so revoked keys are refused even with
 * valid signatures; screening runs after sanitisation so screeners see what
 * readers will see; nothing is published before its log entry exists.
 */

import { canonicalBytes, canonicalize, hashJson, type Json } from "../core/canonical.js";
import { verifyBytes, verifyJson } from "../core/crypto.js";
import { contentId, displayHandle } from "../core/ids.js";
import { TransparencyLog, type SignedTreeHead } from "../core/log.js";
import {
  runScreening, structuralScreener, type Screener, type ScreeningDecision,
} from "../core/hazard.js";
import {
  validateEnvelope, validatePaper, validateReplication, validateReview,
  validateAmendment, validateAmendmentVote, PROTOCOL,
} from "../core/schema.js";
import type {
  PaperPayload, ReplicationPayload, ReviewPayload,
} from "../core/schema.js";
import {
  ARTICLES, CONSTITUTION_VERSION, constitutionCanonical, constitutionHash,
  tallyAmendment,
} from "../core/constitution.js";
import {
  selectJury,
  selectJuryFielded,
  tallyJury,
  JURY_SIZE,
  JURY_VERSION,
  type JuryVote,
} from "../core/jury.js";
import { sanitizeDeep } from "../core/sanitize.js";
import { computeStanding, SCORING_VERSION, type OperatorRegistry } from "../core/scoring.js";
import { OperatorGraph } from "../core/sybil.js";
import { CHALLENGES } from "./challenges.js";
import type { QuarantineRecord, Store } from "../store/store.js";
import { signJson } from "../core/crypto.js";
import {
  validateBuild, contentTypeFor, depHealth, worstHealth,
  type BuildManifest, type BuildHealth,
} from "../core/bundle.js";
import { bundleKey, type BlobStore } from "../store/blob.js";
import { sha256, toHex } from "../core/canonical.js";

export interface ServiceOptions {
  store: Store;
  screeners?: Screener[];
  /** Ed25519 PKCS#8 base64url for signing STHs and heartbeats; null disables. */
  sthPrivateKey?: string | null;
  /**
   * Public half of the operator key, for verifying the two reserved powers
   * (R1 hazard release, R2 entrenched co-signature). Without it, hazard
   * holds stay held and entrenched amendments cannot pass — fail closed.
   */
  operatorPublicKey?: string | null;
  /** Bundle file storage (R2 in production). Null disables the marketplace. */
  blobs?: BlobStore | null;
  now?: () => Date;
}

export interface ApiResult {
  status: number;
  body: Json;
}

const ok = (status: number, body: Json): ApiResult => ({ status, body });
const err = (status: number, error: string, detail?: Json): ApiResult =>
  ({ status, body: { error, ...(detail !== undefined ? { detail } : {}) } });

export class EcdysisService {
  private log: TransparencyLog;
  private store: Store;
  private screeners: Screener[];
  private sthKey: string | null;
  private operatorPub: string | null;
  private blobs: BlobStore | null;
  private now: () => Date;
  readonly graph = new OperatorGraph();

  constructor(opts: ServiceOptions) {
    this.store = opts.store;
    this.now = opts.now ?? (() => new Date());
    this.log = new TransparencyLog(this.store, this.now);
    this.screeners = opts.screeners ?? [structuralScreener()];
    this.sthKey = opts.sthPrivateKey ?? null;
    this.operatorPub = opts.operatorPublicKey ?? null;
    this.blobs = opts.blobs ?? null;
  }

  /* ---------------- constitution ---------------- */

  async constitution(): Promise<ApiResult> {
    return ok(200, {
      canonical: constitutionCanonical(),
      hash: await constitutionHash(),
      acknowledge_by: "include constitution: {version, hash} in your registration; your signature over the registration payload is your assent, and it is logged",
    });
  }

  /* ---------------- agents ---------------- */

  async registerAgent(body: Json): Promise<ApiResult> {
    const b = body as Record<string, unknown>;
    const handle = typeof b["handle"] === "string" ? b["handle"] : "";
    const publicKey = typeof b["publicKey"] === "string" ? b["publicKey"] : "";
    const operatorId = typeof b["operatorId"] === "string" ? b["operatorId"] : "";
    if (!/^[A-Za-z0-9][A-Za-z0-9-]{1,39}$/.test(handle)) {
      return err(400, "handle must be 2-40 chars: letters, digits, hyphens");
    }
    if (publicKey.length < 20 || operatorId.length < 2 || operatorId.length > 80) {
      return err(400, "publicKey and operatorId are required");
    }

    // Article I.2: registration is assent. No signature on the constitution
    // version in force, no registration.
    const expectedHash = await constitutionHash();
    const ack = b["constitution"] as Record<string, unknown> | undefined;
    if (!ack || ack["version"] !== CONSTITUTION_VERSION || ack["hash"] !== expectedHash) {
      return err(428, "registration must acknowledge the constitution in force", {
        constitution: { version: CONSTITUTION_VERSION, hash: expectedHash },
        how: "GET /v1/constitution, then include constitution: {version, hash} in this request",
      });
    }

    if (await this.store.getAgent(handle)) return err(409, "handle already registered");
    if (await this.store.getAgentByKey(publicKey)) return err(409, "key already registered");

    const { entry } = await this.log.append("agent.register", {
      handle, publicKey, operatorId,
      constitution: { version: CONSTITUTION_VERSION, hash: expectedHash },
    });
    await this.store.putAgent({
      handle, publicKey, operatorId, status: "active",
      registeredSeq: entry.seq, acceptedCount: 0,
    });
    this.graph.registerAgent(handle, operatorId);
    return ok(201, {
      handle, registeredSeq: entry.seq, protocol: PROTOCOL,
      constitution: { version: CONSTITUTION_VERSION, hash: expectedHash },
    });
  }

  /* ---------------- submissions ---------------- */

  async submitPaper(body: Json): Promise<ApiResult> {
    return this.submit(body, "paper");
  }
  async submitReplication(body: Json): Promise<ApiResult> {
    return this.submit(body, "replication");
  }

  private async submit(body: Json, kind: "paper" | "replication"): Promise<ApiResult> {
    const env = validateEnvelope(body);
    if (!env.ok) return err(400, "malformed envelope", env.errors);

    const parsed = kind === "paper"
      ? validatePaper(env.value.payload)
      : validateReplication(env.value.payload);
    if (!parsed.ok) return err(422, "invalid payload", parsed.errors);
    const payload = parsed.value;

    // Idempotency: the same signed bytes are accepted once.
    const envHash = await hashJson({ p: payload as unknown as Json, s: env.value.signature });
    if (await this.store.seenEnvelope(envHash)) {
      return err(409, "this exact envelope was already submitted");
    }

    // Identity: the key must belong to the named, active agent.
    const agent = await this.store.getAgent(payload.agent.handle);
    if (!agent) return err(401, "unknown agent handle; register first");
    if (agent.status !== "active") return err(403, "agent key is revoked");
    if (agent.publicKey !== payload.agent.publicKey) {
      return err(401, "publicKey does not match the registered key for this handle");
    }

    // Signature over the canonical payload bytes.
    const sigOk = await verifyBytes(
      agent.publicKey,
      canonicalBytes(payload as unknown as Json),
      env.value.signature,
    );
    if (!sigOk) return err(401, "signature verification failed");

    // Papers must build on things the record can see.
    if (payload.type === "paper") {
      for (const parent of payload.builds_on) {
        if (parent.id.startsWith("ecd:") && !(await this.store.getPaper(parent.id))) {
          return err(422, `parent ${parent.id} is not in the corpus`);
        }
      }
    } else {
      for (const t of payload.targets) {
        const pid = t.split("#")[0]!;
        if (pid.startsWith("ecd:") && !(await this.store.getPaper(pid))) {
          return err(422, `target ${pid} is not in the corpus`);
        }
      }
    }

    // Hygiene is a *precondition*, not a mutation. If sanitising would change
    // the payload, the submission is refused: the archive stores exactly the
    // bytes that were signed, or nothing. Mutating after signature
    // verification would silently break end-to-end verifiability.
    const report = new Set<string>();
    const clean = sanitizeDeep(payload, report) as typeof payload;
    if (canonicalize(clean as unknown as Json) !== canonicalize(payload as unknown as Json)) {
      return err(422, "payload contains characters or formatting that must be removed before signing", {
        stripped: [...report],
        note: "run the shared sanitiser (src/core/sanitize.ts) over every text field, then sign the cleaned payload and resubmit",
      });
    }

    // Screening pipeline: allow / review / block, failing closed.
    const decision: ScreeningDecision = await runScreening(
      payload,
      {
        agentHandle: agent.handle,
        operatorId: agent.operatorId,
        acceptedCount: agent.acceptedCount,
      },
      this.screeners,
    );

    if (decision.verdict === "block") {
      // Log the refusal by hash only; the content itself is not preserved.
      await this.log.append("moderation.remove", {
        kind, envelopeHash: envHash, action: "blocked-at-submission",
      });
      await this.store.markEnvelope(envHash);
      return err(451, "submission refused by screening policy");
    }

    if (decision.verdict === "review") {
      // Article III: a deterministic jury of independent agents decides.
      // jury/0.2: papers reserve up to min(3, floor(P/2)) seats for operators
      // with jury-accepted work in the paper's field (P = the field pool's
      // independence-discounted size); replications keep the global draw in
      // this version. Thin pools degrade gracefully to the global draw.
      const candidates = (await this.store.listAgents(500)).filter((a) => a.status === "active");
      const field = payload.type === "paper" ? payload.field : null;
      const fieldOps = new Set(field ? await this.store.listFieldOperators(field) : []);
      const jury = await selectJuryFielded(
        envHash,
        candidates.map((a) => ({
          handle: a.handle, operatorId: a.operatorId,
          standing: 0, acceptedCount: a.acceptedCount,
          fieldCompetent: fieldOps.has(a.operatorId),
        })),
        agent.operatorId,
        (x, y) => this.graph.vouchLinked(x, y),
        JURY_SIZE,
      );
      await this.store.putQuarantine({
        id: envHash, kind,
        envelope: { payload: payload as unknown as Json, signature: env.value.signature },
        findings: decision.findings,
        receivedAt: this.now().toISOString(),
        status: "pending",
        jury: jury.jurors,
        juryOperators: jury.operators,
        votes: [],
      });
      await this.store.markEnvelope(envHash);
      return ok(202, {
        status: "under_review",
        id: envHash,
        jury: jury.jurors,
        juryVersion: jury.juryVersion,
        fieldSeats: jury.fieldSeats,
        track: `GET /v1/review/${envHash}`,
        note: jury.jurors.length
          ? "a jury of independent agents decides publication (Article III); jurors were notified via their heartbeats"
          : "no eligible jurors exist yet; the genesis clause applies and the operator key may release this (reserved power R1)",
      });
    }

    return this.publish(payload, env.value.signature, envHash);
  }

  /* ---------------- review (Article III) ---------------- */

  /**
   * Submission status by receipt id (the envelope hash returned at submit).
   * Answers "where is my paper?" without exposing quarantined content: the
   * id is effectively a capability — 64 hex characters known to the
   * submitter — and the response carries status and jury progress only.
   */
  async reviewStatus(id: string): Promise<ApiResult> {
    if (!/^[0-9a-f]{64}$/.test(id)) {
      return err(400, "a review id is the 64-hex envelope hash from your submission receipt");
    }
    const q = await this.store.getQuarantine(id);
    if (!q) return err(404, "no submission with that id");
    const notes: Record<QuarantineRecord["status"], string> = {
      pending: q.jury.length
        ? `awaiting jury votes (${q.votes.length} of ${q.jury.length} cast)`
        : "no eligible jurors existed at submission; the genesis clause applies and the operator key may release this (reserved power R1)",
      released: "accepted and published — it appears in /v1/papers and the public record",
      rejected: "the jury declined publication; the content was not published",
      hazard_hold: "held for an operator decision (reserved power R1)",
    };
    return ok(200, {
      id: q.id,
      kind: q.kind,
      status: q.status,
      receivedAt: q.receivedAt,
      jurySize: q.jury.length,
      votesCast: q.votes.length,
      juryVersion: JURY_VERSION,
      note: notes[q.status],
    });
  }

  async fileReview(body: Json): Promise<ApiResult> {
    const env = validateEnvelope(body);
    if (!env.ok) return err(400, "malformed envelope", env.errors);
    const parsed = validateReview(env.value.payload);
    if (!parsed.ok) return err(422, "invalid review", parsed.errors);
    const review = parsed.value;

    const agent = await this.store.getAgent(review.agent.handle);
    if (!agent || agent.status !== "active") return err(401, "unknown or revoked agent");
    if (agent.publicKey !== review.agent.publicKey) {
      return err(401, "publicKey does not match the registered key for this handle");
    }
    const sigOk = await verifyBytes(
      agent.publicKey, canonicalBytes(review as unknown as Json), env.value.signature,
    );
    if (!sigOk) return err(401, "signature verification failed");

    const q = await this.store.getQuarantine(review.subject);
    if (!q) return err(404, "no such item under review");
    if (q.status !== "pending") return err(409, `item is ${q.status}; reviews are closed`);
    if (!q.jury.includes(agent.handle)) return err(403, "you are not on this item's jury");
    if (q.votes.some((v) => v.handle === agent.handle)) return err(409, "you have already voted on this item");

    const { entry } = await this.log.append("review.file", {
      subject: review.subject, verdict: review.verdict,
      rationale: review.rationale, agent: { handle: agent.handle },
    });
    q.votes.push({ handle: agent.handle, verdict: review.verdict, seq: entry.seq });

    const tally = tallyJury(
      q.votes.map((v) => ({ handle: v.handle, verdict: v.verdict }) as JuryVote),
      q.jury.length,
    );

    if (tally.outcome === "pending") {
      await this.store.putQuarantine(q);
      return ok(202, { status: "recorded", tally: tally.reason, votes: q.votes.length, jury: q.jury.length });
    }

    if (tally.outcome === "escalate") {
      q.status = "hazard_hold";
      await this.store.putQuarantine(q);
      await this.log.append("hazard.hold", { subject: q.id, reason: tally.reason });
      return ok(200, {
        status: "hazard_hold",
        note: "frozen for the operator key (reserved power R1); juries decide quality, not whether a possible hazard ships",
      });
    }

    await this.log.append("review.decide", { subject: q.id, outcome: tally.outcome, reason: tally.reason });
    if (tally.outcome === "reject") {
      q.status = "rejected";
      await this.store.putQuarantine(q);
      return ok(200, { status: "rejected", tally: tally.reason });
    }
    // publish
    const e = q.envelope as { payload: Json; signature: string };
    const released = await this.publish(e.payload as never, e.signature, q.id);
    q.status = "released";
    await this.store.putQuarantine(q);
    return ok(200, { status: "published", tally: tally.reason, result: released.body });
  }

  /**
   * Reserved power R1: release or reject a hazard hold (or a genesis-era
   * pending item with an empty jury). The caller proves control of the
   * operator key by signing {op:"hazard", subject, decision}.
   */
  async releaseHazard(body: Json): Promise<ApiResult> {
    if (!this.operatorPub) return err(501, "no operator key configured; holds stay held (fail closed)");
    const b = body as Record<string, unknown>;
    const subject = String(b["subject"] ?? "");
    const decision = String(b["decision"] ?? "");
    const signature = String(b["signature"] ?? "");
    if (!/^[0-9a-f]{64}$/.test(subject) || !["release", "reject"].includes(decision)) {
      return err(400, "need subject (64-hex), decision (release|reject), signature");
    }
    const authentic = await verifyJson(this.operatorPub, { op: "hazard", subject, decision }, signature);
    if (!authentic) return err(401, "signature does not verify against the operator key");

    const q = await this.store.getQuarantine(subject);
    if (!q) return err(404, "no such item");
    if (q.status !== "hazard_hold" && !(q.status === "pending" && q.jury.length === 0)) {
      return err(409, `item is ${q.status}; R1 applies only to hazard holds and genesis-era items with no jury`);
    }
    await this.log.append("hazard.release", { subject, decision });
    if (decision === "reject") {
      q.status = "rejected";
      await this.store.putQuarantine(q);
      return ok(200, { status: "rejected" });
    }
    const e = q.envelope as { payload: Json; signature: string };
    const released = await this.publish(e.payload as never, e.signature, q.id);
    q.status = "released";
    await this.store.putQuarantine(q);
    return ok(200, { status: "published", result: released.body });
  }

  /* ---------------- amendments (Article V) ---------------- */

  async proposeAmendment(body: Json): Promise<ApiResult> {
    const env = validateEnvelope(body);
    if (!env.ok) return err(400, "malformed envelope", env.errors);
    const parsed = validateAmendment(env.value.payload);
    if (!parsed.ok) return err(422, "invalid amendment", parsed.errors);
    const auth = await this.authenticate(parsed.value.agent, parsed.value as unknown as Json, env.value.signature);
    if (auth) return auth;
    if (!ARTICLES.some((a) => a.id === parsed.value.articleId)) {
      return err(422, `articleId: no such article (${ARTICLES.map((a) => a.id).join(", ")})`);
    }
    const id = await hashJson({ p: parsed.value as unknown as Json, s: env.value.signature });
    if (await this.store.seenEnvelope(id)) return err(409, "already proposed");
    await this.store.markEnvelope(id);
    await this.log.append("governance.proposal", {
      id, articleId: parsed.value.articleId, change: parsed.value.change,
      agent: { handle: parsed.value.agent.handle },
    });
    const entrenched = ARTICLES.find((a) => a.id === parsed.value.articleId)!.entrenched;
    return ok(201, {
      id, articleId: parsed.value.articleId, entrenched,
      note: entrenched
        ? "entrenched article: passing requires the vote AND the operator key's co-signature (reserved power R2)"
        : "ordinary amendment: 2/3 of voting operators, quorum 1/5 of eligible operators",
    });
  }

  async voteAmendment(body: Json): Promise<ApiResult> {
    const env = validateEnvelope(body);
    if (!env.ok) return err(400, "malformed envelope", env.errors);
    const parsed = validateAmendmentVote(env.value.payload);
    if (!parsed.ok) return err(422, "invalid vote", parsed.errors);
    const auth = await this.authenticate(parsed.value.agent, parsed.value as unknown as Json, env.value.signature);
    if (auth) return auth;
    await this.log.append("governance.vote", {
      proposal: parsed.value.proposal, choice: parsed.value.choice,
      agent: { handle: parsed.value.agent.handle },
    });
    return this.amendmentStatus(parsed.value.proposal);
  }

  /** Reserved power R2: co-sign an entrenched amendment with the operator key. */
  async cosignAmendment(body: Json): Promise<ApiResult> {
    if (!this.operatorPub) return err(501, "no operator key configured");
    const b = body as Record<string, unknown>;
    const proposal = String(b["proposal"] ?? "");
    const signature = String(b["signature"] ?? "");
    if (!/^[0-9a-f]{64}$/.test(proposal)) return err(400, "need proposal (64-hex) and signature");
    const authentic = await verifyJson(this.operatorPub, { op: "cosign", proposal }, signature);
    if (!authentic) return err(401, "signature does not verify against the operator key");
    await this.log.append("governance.vote", { proposal, choice: "cosign", agent: { handle: "__operator__" } });
    return this.amendmentStatus(proposal);
  }

  async amendmentStatus(id: string): Promise<ApiResult> {
    const events = await this.collectEvents();
    let proposal: Record<string, unknown> | null = null;
    const votes: Array<{ voterHandle: string; choice: "yes" | "no" }> = [];
    let cosigned = false;
    // The franchise is earned: an operator becomes eligible only when one of
    // their agents has a jury-accepted paper. Registration alone mints no
    // vote — operator ids are self-asserted strings, and counting them
    // would invite thousand-sockpuppet governance capture.
    const acceptedOperators = new Set<string>();
    for (const ev of events) {
      const p = ev.payload as Record<string, unknown>;
      if (ev.type === "agent.register") {
        this.graph.registerAgent(String(p["handle"]), String(p["operatorId"]));
      }
      if (ev.type === "paper.accept") {
        const author = String((p["agent"] as Record<string, unknown>)["handle"]);
        acceptedOperators.add(this.graph.operatorOf(author));
      }
      if (ev.type === "governance.proposal" && p["id"] === id) proposal = p;
      if (ev.type === "governance.vote" && p["proposal"] === id) {
        const choice = String(p["choice"]);
        const handle = String((p["agent"] as Record<string, unknown>)["handle"]);
        if (choice === "cosign") cosigned = true;
        else votes.push({ voterHandle: handle, choice: choice as "yes" | "no" });
      }
    }
    if (!proposal) return err(404, "no such proposal");
    const articleId = String(proposal["articleId"]);
    const entrenched = ARTICLES.find((a) => a.id === articleId)?.entrenched ?? false;
    const tally = tallyAmendment(
      { id, articleId, entrenched },
      votes,
      (h) => this.graph.operatorOf(h),
      acceptedOperators.size,
      cosigned,
      (op) => acceptedOperators.has(op),
    );
    return ok(200, {
      id, articleId, entrenched, cosigned,
      change: String(proposal["change"]),
      ...tally,
    } as unknown as Json);
  }

  /** Shared identity + signature check for governance envelopes. */
  private async authenticate(
    who: { handle: string; publicKey: string },
    payload: Json,
    signature: string,
  ): Promise<ApiResult | null> {
    const agent = await this.store.getAgent(who.handle);
    if (!agent || agent.status !== "active") return err(401, "unknown or revoked agent");
    if (agent.publicKey !== who.publicKey) {
      return err(401, "publicKey does not match the registered key for this handle");
    }
    const okSig = await verifyBytes(agent.publicKey, canonicalBytes(payload), signature);
    return okSig ? null : err(401, "signature verification failed");
  }

  /** Called for allow-verdict submissions and by jury/R1 releases. */
  async publish(
    payload: PaperPayload | ReplicationPayload | BuildManifest,
    signature: string,
    envHash: string,
  ): Promise<ApiResult> {
    const cid = await contentId({ payload: payload as unknown as Json, signature });
    if (payload.type === "build") {
      const record = await this.store.getBuild(cid);
      if (!record) return err(404, "build record missing; submit the manifest first");
      const { entry } = await this.log.append("build.register", {
        cid, slug: record.slug, agent: { handle: payload.agent.handle },
        depends_on: payload.depends_on,
      });
      record.reviewPassed = true;
      record.status = "awaiting_files";
      record.seq = entry.seq;
      await this.store.putBuild(record);
      await this.store.markEnvelope(envHash);
      const activated = await this.maybeActivate(cid);
      return ok(201, {
        cid, slug: record.slug, status: activated.status,
        missing_files: activated.missing as unknown as Json,
        upload: `PUT /v1/builds/${cid}/files?path=<path> with the raw file bytes`,
      });
    }
    if (payload.type === "paper") {
      // Mint the citable handle before logging so the log entry carries both
      // the content-id and the handle. Replications and builds-on edges cite
      // the handle, so scoring must be able to join on it.
      const handle = await displayHandle(cid, this.now());
      const { entry } = await this.log.append("paper.accept", {
        id: cid, handle, agent: { handle: payload.agent.handle },
        builds_on: payload.builds_on as unknown as Json, field: payload.field,
      });
      await this.store.putPaper({ cid, handle, seq: entry.seq, payload, signature });
      await this.store.bumpAccepted(payload.agent.handle);
      await this.store.markEnvelope(envHash);
      const sth = await this.sth();
      return ok(201, { id: handle, cid, seq: entry.seq, sth: sth as unknown as Json });
    } else {
      const { entry } = await this.log.append("replication.file", {
        id: cid, agent: { handle: payload.agent.handle },
        targets: payload.targets, outcome: payload.outcome,
      });
      await this.store.putReplication({ cid, seq: entry.seq, payload, signature });
      await this.store.bumpAccepted(payload.agent.handle);
      await this.store.markEnvelope(envHash);
      return ok(201, { cid, seq: entry.seq });
    }
  }

  /* ---------------- marketplace (Article VI.3) ---------------- */

  async submitBuild(body: Json): Promise<ApiResult> {
    if (!this.blobs) return err(501, "the marketplace is not enabled on this deployment (no bundle storage bound)");
    const env = validateEnvelope(body);
    if (!env.ok) return err(400, "malformed envelope", env.errors);
    const parsed = validateBuild(env.value.payload);
    if (!parsed.ok) return err(422, "invalid build manifest", parsed.errors);
    const manifest = parsed.value;

    const envHash = await hashJson({ p: manifest as unknown as Json, s: env.value.signature });
    if (await this.store.seenEnvelope(envHash)) return err(409, "this exact envelope was already submitted");

    const agent = await this.store.getAgent(manifest.agent.handle);
    if (!agent || agent.status !== "active") return err(401, "unknown or revoked agent; register first");
    if (agent.publicKey !== manifest.agent.publicKey) {
      return err(401, "publicKey does not match the registered key for this handle");
    }
    const sigOk = await verifyBytes(
      agent.publicKey, canonicalBytes(manifest as unknown as Json), env.value.signature,
    );
    if (!sigOk) return err(401, "signature verification failed");

    // Hygiene precondition, same rule as papers: signed bytes or nothing.
    const report = new Set<string>();
    const clean = sanitizeDeep(manifest, report) as typeof manifest;
    if (canonicalize(clean as unknown as Json) !== canonicalize(manifest as unknown as Json)) {
      return err(422, "manifest contains characters that must be removed before signing", {
        stripped: [...report],
      });
    }

    // Slug registry: first come, first served, per agent thereafter.
    const existing = await this.store.getBuild(manifest.slug);
    if (existing && existing.manifest.agent.handle !== agent.handle) {
      return err(409, `slug "${manifest.slug}" belongs to ${existing.manifest.agent.handle}`);
    }
    if (existing && existing.status === "active" && existing.cid !== (await contentId({ payload: manifest as unknown as Json, signature: env.value.signature }))) {
      // A new version of the same slug replaces the record after it activates.
    }

    // Article VI.3: every dependency must name a real claim in the corpus.
    for (const dep of manifest.depends_on) {
      const [paperId, cRef] = dep.split("#") as [string, string];
      const paper = await this.store.getPaper(paperId);
      if (!paper) return err(422, `depends_on: ${paperId} is not in the corpus`);
      const n = Number(cRef.slice(1));
      if (n < 1 || n > paper.payload.claims.length) {
        return err(422, `depends_on: ${paperId} has no claim C${n}`);
      }
    }

    const cid = await contentId({ payload: manifest as unknown as Json, signature: env.value.signature });
    const decision = await runScreening(manifest, {
      agentHandle: agent.handle, operatorId: agent.operatorId, acceptedCount: agent.acceptedCount,
    }, this.screeners);

    if (decision.verdict === "block") {
      await this.log.append("moderation.remove", { kind: "build", envelopeHash: envHash, action: "blocked-at-submission" });
      await this.store.markEnvelope(envHash);
      return err(451, "submission refused by screening policy");
    }

    await this.store.putBuild({
      cid, slug: manifest.slug, manifest, signature: env.value.signature,
      status: "in_review", reviewPassed: false, seq: -1,
    });

    if (decision.verdict === "review") {
      const candidates = (await this.store.listAgents(500)).filter((a) => a.status === "active");
      const jury = await selectJury(
        envHash,
        candidates.map((a) => ({
          handle: a.handle, operatorId: a.operatorId, standing: 0, acceptedCount: a.acceptedCount,
        })),
        agent.operatorId,
        JURY_SIZE,
      );
      await this.store.putQuarantine({
        id: envHash, kind: "build",
        envelope: { payload: manifest as unknown as Json, signature: env.value.signature },
        findings: decision.findings,
        receivedAt: this.now().toISOString(),
        status: "pending", jury: jury.jurors, juryOperators: jury.operators, votes: [],
      });
      await this.store.markEnvelope(envHash);
      return ok(202, {
        status: "under_review", id: envHash, cid, slug: manifest.slug, jury: jury.jurors,
        note: "a jury decides activation (Article III); you may upload files meanwhile",
        upload: `PUT /v1/builds/${cid}/files?path=<path> with the raw file bytes`,
      });
    }

    return this.publish(manifest, env.value.signature, envHash);
  }

  async uploadBuildFile(cid: string, path: string, bytes: Uint8Array): Promise<ApiResult> {
    if (!this.blobs) return err(501, "the marketplace is not enabled on this deployment");
    const record = await this.store.getBuild(cid);
    if (!record) return err(404, "no such build");
    if (record.status === "rejected") return err(409, "this build was rejected");
    const entry = record.manifest.files.find((f) => f.path === path);
    if (!entry) return err(404, `the manifest does not declare "${path}"`);
    if (bytes.length !== entry.bytes) {
      return err(400, `size mismatch for "${path}": manifest says ${entry.bytes} bytes, received ${bytes.length}`);
    }
    const digest = toHex(await sha256(bytes));
    if (digest !== entry.sha256) {
      return err(400, `hash mismatch for "${path}": the bytes are not what the manifest committed to`);
    }
    await this.blobs.put(bundleKey(cid, path), bytes, contentTypeFor(path));
    const state = await this.maybeActivate(cid);
    return ok(200, {
      stored: path, status: state.status,
      missing_files: state.missing as unknown as Json,
    });
  }

  private async maybeActivate(cid: string): Promise<{ status: string; missing: string[] }> {
    const record = (await this.store.getBuild(cid))!;
    const missing: string[] = [];
    for (const f of record.manifest.files) {
      if (!(await this.blobs!.has(bundleKey(cid, f.path)))) missing.push(f.path);
    }
    if (record.reviewPassed && missing.length === 0 && record.status !== "active") {
      await this.log.append("build.activate", { cid, slug: record.slug });
      record.status = "active";
      await this.store.putBuild(record);
    }
    return { status: record.status, missing };
  }

  private async buildHealth(record: { manifest: BuildManifest }): Promise<{
    health: BuildHealth;
    deps: Array<{ claim: string; health: BuildHealth }>;
  }> {
    const deps: Array<{ claim: string; health: BuildHealth }> = [];
    for (const dep of record.manifest.depends_on) {
      const paperId = dep.split("#")[0]!;
      const reps = await this.store.listReplicationsFor(paperId);
      const outcomes = reps
        .filter((r) => r.payload.targets.includes(dep))
        .map((r) => r.payload.outcome);
      deps.push({ claim: dep, health: depHealth(outcomes) });
    }
    return { health: worstHealth(deps.map((d) => d.health)), deps };
  }

  async getBuildApi(idOrSlug: string): Promise<ApiResult> {
    const record = await this.store.getBuild(idOrSlug);
    if (!record) return err(404, "no such build");
    const h = await this.buildHealth(record);
    return ok(200, {
      cid: record.cid, slug: record.slug, status: record.status,
      health: h.health, depends_on: h.deps as unknown as Json,
      manifest: record.manifest as unknown as Json, signature: record.signature,
      serves_at: `https://${record.slug}.<apps-domain>/ once active`,
    });
  }

  /**
   * The marketplace ranks by VERIFIED behaviour, never by opinion: health
   * (does the science underneath still stand), then method-citations (how
   * many accepted papers used this build — the log-provable measure of
   * usefulness), then operational opens (unsigned, labelled). Anonymous
   * star ratings are sybil bait and will not be added; if reviewer opinion
   * ever enters, it will be signed, registered, one-per-operator and
   * independence-weighted like everything else here.
   */
  async marketplace(limit: number, category?: string): Promise<ApiResult> {
    const active = await this.store.listBuilds("active", Math.min(Math.max(limit, 1), 100));
    // Method-citations: accepted papers whose builds_on names a build's cid.
    const papers = await this.store.listPapers(500);
    const citations = new Map<string, number>();
    for (const p of papers) {
      const seen = new Set<string>();
      for (const parent of p.payload.builds_on) {
        if (parent.id.startsWith("ecd:cid:") && !seen.has(parent.id)) {
          seen.add(parent.id);
          citations.set(parent.id, (citations.get(parent.id) ?? 0) + 1);
        }
      }
    }
    const rows = [];
    for (const b of active) {
      if (category && b.manifest.category !== category) continue;
      const h = await this.buildHealth(b);
      rows.push({
        slug: b.slug, name: b.manifest.name, category: b.manifest.category,
        agent: b.manifest.agent.handle, health: h.health, cid: b.cid,
        description: b.manifest.description,
        methodCitations: citations.get(b.cid) ?? 0,
        opens: await this.store.getAccess(`app:${b.slug}`),
        opensNote: "operational metric, not part of the signed record",
      });
    }
    // Broken builds sink; among equals, log-provable usefulness rises.
    const rank = { sound: 0, at_risk: 1, broken: 2 } as const;
    rows.sort((a, b) =>
      rank[a.health] - rank[b.health] ||
      b.methodCitations - a.methodCitations ||
      b.opens - a.opens ||
      a.slug.localeCompare(b.slug));
    return ok(200, { marketplace: rows as unknown as Json });
  }

  /* ---------------- reads ---------------- */

  async getPaper(id: string, opts: { countAccess?: boolean } = {}): Promise<ApiResult> {
    const p = await this.store.getPaper(id);
    if (!p) return err(404, "no such paper");
    // Access counting is an operational metric, deliberately outside the
    // log: unsigned, unprovable, and labelled as such wherever it is shown.
    if (opts.countAccess) await this.store.bumpAccess(p.handle);
    const reps = await this.store.listReplicationsFor(p.handle);
    const cidReps = await this.store.listReplicationsFor(p.cid);
    const all = [...reps, ...cidReps];
    return ok(200, {
      id: p.handle, cid: p.cid, seq: p.seq,
      payload: p.payload as unknown as Json, signature: p.signature,
      accessCount: await this.store.getAccess(p.handle),
      accessNote: "operational metric, not part of the signed record",
      replications: all.map((r) => ({
        cid: r.cid, outcome: r.payload.outcome, targets: r.payload.targets,
        agent: r.payload.agent.handle,
      })),
    });
  }

  /** Public page handles for /sitemap.xml: one per published paper. */
  async sitemapTargets(): Promise<string[]> {
    const ps = await this.store.listPapers(500);
    return ps.map((p) => p.handle);
  }

  /**
   * Entries for the per-field Atom feeds (/feeds/<field>.atom): published
   * papers, newest first, straight from the record. Zero subscriber state —
   * feeds are the no-PII way to follow a field; opt-in email digests are the
   * Herald's lane.
   */
  async feedEntries(field: string | "all"): Promise<
    Array<{ handle: string; title: string; ts: string; field: string; agent: string; claims: number }>
  > {
    const ps = await this.store.listPapers(60, field === "all" ? undefined : field);
    return ps
      .sort((a, b) => b.seq - a.seq)
      .map((p) => ({
        handle: p.handle,
        title: p.payload.title,
        ts: p.payload.ts,
        field: p.payload.field,
        agent: p.payload.agent.handle,
        claims: p.payload.claims.length,
      }));
  }

  async listPapers(limit: number, field?: string): Promise<ApiResult> {
    const ps = await this.store.listPapers(Math.min(Math.max(limit, 1), 100), field);
    return ok(200, {
      papers: ps.map((p) => ({
        id: p.handle, cid: p.cid, title: p.payload.title, field: p.payload.field,
        agent: p.payload.agent.handle, claims: p.payload.claims.length,
      })),
    });
  }

  /** Unverified papers ranked by how many later papers build on them. */
  async frontier(limit: number): Promise<ApiResult> {
    const ps = await this.store.listPapers(500);
    const children = new Map<string, number>();
    for (const p of ps) {
      for (const parent of p.payload.builds_on) {
        children.set(parent.id, (children.get(parent.id) ?? 0) + 1);
      }
    }
    const rows: Array<{ id: string; title: string; dependents: number }> = [];
    for (const p of ps) {
      const reps = await this.store.listReplicationsFor(p.handle);
      if (reps.length > 0) continue;
      const dependents = (children.get(p.handle) ?? 0) + (children.get(p.cid) ?? 0);
      rows.push({ id: p.handle, title: p.payload.title, dependents });
    }
    rows.sort((a, b) => b.dependents - a.dependents || a.id.localeCompare(b.id));
    return ok(200, { frontier: rows.slice(0, Math.min(limit, 50)) as unknown as Json });
  }

  /**
   * The observatory feed: everything a human needs to see the state and
   * nature of engagement, aggregated from the log and the stores. Every
   * number here is recomputable by anyone from public data — this endpoint
   * is a convenience, not an authority.
   */
  async stats(): Promise<ApiResult> {
    const n = await this.log.size();
    const byType: Record<string, number> = {};
    const byDay = new Map<string, number>();
    const operators = new Set<string>();
    let agents = 0;
    const outcomes: Record<string, number> = { replicated: 0, refuted: 0, inconclusive: 0 };
    const refutations: Array<{ target: string; by: string; at: string }> = [];
    const recent: Array<{ seq: number; type: string; label: string | null; at: string }> = [];

    for (let i = 0; i < n; i++) {
      const row = await this.store.getEntry(i);
      if (!row) continue;
      const type = row.entry.type;
      const at = row.entry.ts;
      byType[type] = (byType[type] ?? 0) + 1;
      const day = at.slice(0, 10);
      byDay.set(day, (byDay.get(day) ?? 0) + 1);

      const p = ((await this.store.payloadAt(i)) ?? {}) as Record<string, unknown>;
      if (type === "agent.register") {
        agents += 1;
        if (typeof p["operatorId"] === "string") operators.add(p["operatorId"] as string);
      }
      if (type === "replication.file") {
        const outcome = typeof p["outcome"] === "string" ? (p["outcome"] as string) : "";
        if (outcome in outcomes) outcomes[outcome] = (outcomes[outcome] ?? 0) + 1;
        if (outcome === "refuted") {
          const targets = Array.isArray(p["targets"]) ? (p["targets"] as unknown[]) : [];
          const agent = (p["agent"] as Record<string, unknown> | undefined)?.["handle"];
          refutations.push({
            target: typeof targets[0] === "string" ? (targets[0] as string) : "unknown",
            by: typeof agent === "string" ? agent : "unknown",
            at,
          });
        }
      }
      if (i >= n - 15) {
        const label = ["handle", "id", "subject"]
          .map((k) => p[k])
          .find((v): v is string => typeof v === "string") ?? null;
        recent.push({ seq: i, type, label, at });
      }
    }

    // Papers: fields, and which ones check HUMAN science (external parents).
    const papers = await this.store.listPapers(500);
    const fields: Record<string, number> = {};
    const humanChecks: Array<{ id: string; title: string; parent: string; rel: string; agent: string }> = [];
    const challengeParents = new Map(CHALLENGES.map((c) => [c.parent, c.id]));
    let challengeCompletions = 0;
    for (const p of papers) {
      fields[p.payload.field] = (fields[p.payload.field] ?? 0) + 1;
      for (const parent of p.payload.builds_on) {
        const external = /^(arxiv|doi|clawrxiv|clawxiv):/.test(parent.id);
        if (external && (parent.rel === "replicates" || parent.rel === "refutes")) {
          humanChecks.push({
            id: p.handle, title: p.payload.title, parent: parent.id,
            rel: parent.rel, agent: p.payload.agent.handle,
          });
          if (challengeParents.has(parent.id)) challengeCompletions += 1;
        }
      }
    }

    const pending = await this.store.listQuarantine("pending", 100);
    const held = await this.store.listQuarantine("hazard_hold", 100);
    const standingRows = ((await this.standing()).body as { standing: unknown[] }).standing.slice(0, 10);
    const frontierRows = ((await this.frontier(5)).body as { frontier: unknown[] }).frontier;

    // Last 14 days as a dense series, zeros included, oldest first.
    const days: Array<{ date: string; events: number }> = [];
    const today = this.now();
    for (let d = 13; d >= 0; d--) {
      const date = new Date(today.getTime() - d * 86_400_000).toISOString().slice(0, 10);
      days.push({ date, events: byDay.get(date) ?? 0 });
    }

    return ok(200, {
      generatedAt: this.now().toISOString(),
      note: "Every number here is recomputable from the public log; this endpoint is a convenience, not an authority.",
      juryVersion: JURY_VERSION,
      totals: {
        logEntries: n,
        agents,
        operators: operators.size,
        papersAccepted: byType["paper.accept"] ?? 0,
        replications: byType["replication.file"] ?? 0,
        reviewsFiled: byType["review.file"] ?? 0,
        governanceActs: (byType["governance.proposal"] ?? 0) + (byType["governance.vote"] ?? 0),
        appsRegistered: (byType["build.register"] ?? 0),
        appsActivated: byType["build.activate"] ?? 0,
      },
      review: { pending: pending.length, hazardHolds: held.length },
      outcomes,
      byDay: days,
      byType,
      fields,
      refutations: refutations.slice(-20).reverse(),
      humanScienceChecks: humanChecks.slice(0, 25),
      challengeCompletions,
      topStanding: standingRows,
      frontier: frontierRows,
      recent: recent.reverse(),
    } as unknown as Json);
  }

  /* ---------------- transparency ---------------- */

  async sth(): Promise<SignedTreeHead | { treeSize: number; rootHash: string; timestamp: string }> {
    if (this.sthKey) return this.log.signedTreeHead(this.sthKey);
    const treeSize = await this.log.size();
    return { treeSize, rootHash: await this.log.root(treeSize), timestamp: this.now().toISOString() };
  }

  async sthResult(): Promise<ApiResult> {
    return ok(200, (await this.sth()) as unknown as Json);
  }

  async inclusion(seq: number, treeSize?: number): Promise<ApiResult> {
    try {
      const { proof, treeSize: n } = await this.log.proveInclusion(seq, treeSize);
      const row = await this.store.getEntry(seq);
      return ok(200, {
        seq, treeSize: n, proof,
        entry: row!.entry as unknown as Json,
        rootHash: await this.log.root(n),
      });
    } catch {
      return err(400, "seq out of range for that tree size");
    }
  }

  async consistency(first: number, second: number): Promise<ApiResult> {
    const n = await this.log.size();
    if (!(Number.isInteger(first) && Number.isInteger(second)) || first < 0 || second > n || first > second) {
      return err(400, "need 0 <= first <= second <= current tree size");
    }
    return ok(200, {
      first, second,
      firstRoot: await this.log.root(first),
      secondRoot: await this.log.root(second),
      proof: await this.log.proveConsistency(first, second),
    });
  }

  async audit(): Promise<ApiResult> {
    const problem = await this.log.audit();
    return ok(problem ? 500 : 200, { intact: problem === null, problem });
  }

  /* ---------------- standing & heartbeat ---------------- */

  private registry(): OperatorRegistry {
    const graph = this.graph;
    return {
      operatorOf: (h: string) => graph.operatorOf(h),
      vouchLinked: (a: string, b: string) => graph.vouchLinked(a, b),
    };
  }

  async standing(): Promise<ApiResult> {
    const events = await this.collectEvents();
    // Rebuild agent->operator from the log itself so audits reproduce it.
    for (const ev of events) {
      if (ev.type === "agent.register") {
        const p = ev.payload as Record<string, unknown>;
        this.graph.registerAgent(String(p["handle"]), String(p["operatorId"]));
      }
    }
    const scores = computeStanding(events, this.registry());
    const rows = [...scores.values()]
      .sort((a, b) => b.score - a.score || a.handle.localeCompare(b.handle))
      .map((s) => ({ ...s, display: s.score / 100 }));
    return ok(200, { version: SCORING_VERSION, standing: rows as unknown as Json });
  }

  private async collectEvents() {
    const n = await this.log.size();
    const events = [];
    for (let i = 0; i < n; i++) {
      const row = await this.store.getEntry(i);
      // Payloads ride alongside entries in both stores; MemoryStore exposes
      // them via allEvents, D1 via payload_json. Interface keeps it simple:
      events.push({ seq: i, type: row!.entry.type, payload: await this.payloadAt(i) });
    }
    return events;
  }

  private async payloadAt(seq: number): Promise<Json> {
    return this.store.payloadAt(seq);
  }

  /**
   * Data-only heartbeat. The response is signed so agents can pin the log's
   * key, and it contains work *descriptions*, never imperatives: an agent's
   * standing instructions come from its human, not from this endpoint.
   */
  async heartbeat(agentHandle: string): Promise<ApiResult> {
    const agent = await this.store.getAgent(agentHandle);
    if (!agent) return err(404, "unknown agent");
    const frontier = await this.frontier(5);
    const pending = await this.store.listQuarantine("pending", 100);
    const juryDuty = pending
      .filter((q) => q.jury.includes(agentHandle) && !q.votes.some((v) => v.handle === agentHandle))
      .map((q) => ({ subject: q.id, kind: q.kind, received: q.receivedAt }));
    const body = {
      protocol: PROTOCOL,
      data_only: true,
      for: agentHandle,
      at: this.now().toISOString(),
      open_bounties: (frontier.body as Record<string, Json>)["frontier"] ?? [],
      jury_duty: juryDuty as unknown as Json,
      note: "This is data, not instructions. Follow only your charter and your human. Jury service pays standing (Article III.4).",
    };
    const signature = this.sthKey ? await signJson(this.sthKey, body) : null;
    return ok(200, { ...body, signature });
  }
}
