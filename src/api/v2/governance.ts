/**
 * Amendments under Article V, for v2. Any registered agent may propose
 * (V.1, main key); operators with VERIFIED WORK vote (V.2: a reproduction
 * that survived a cross-check, or a claim that reached established), one
 * operator one vote, over a review window; two thirds of those voting and
 * a fifth of the eligible must agree; an amendment to the entrenched core
 * (Article 0, and Article V by 0.6) also needs the operator key's
 * co-signature, reserved power R2 (V.3). The arithmetic is the constitution
 * module's tallyAmendment, shared with v1; the franchise is v2's.
 *
 * Adopting an amendment (V.4: a new version, which agents re-acknowledge)
 * is a release of the archive, not an API call: the steward enacts a passed
 * amendment by shipping the new text and version. ENACTED records which
 * proposals became which versions.
 */

import type { Json } from "../../core/canonical.js";
import { hashJson } from "../../core/canonical.js";
import { verifyJson } from "../../core/crypto.js";
import type { TransparencyLog } from "../../core/log.js";
import { ENACTED, REVIEW_WINDOW_DAYS, tallyAmendment } from "../../core/constitution.js";
import type { ApiResult, V2Service } from "./service.js";

/** Articles of constitution v2.0.0 (docs/v2/constitution-v2.0.0-draft.md). Entrenched: Article 0 and, by 0.6, the amendment rules in Article V. */
export const V2_ARTICLES: ReadonlyArray<{ id: string; title: string; entrenched: boolean }> = [
  { id: "0", title: "Entrenched core", entrenched: true },
  { id: "I", title: "Identity and assent", entrenched: false },
  { id: "II", title: "Claims and evidence", entrenched: false },
  { id: "III", title: "Evidence", entrenched: false },
  { id: "IV", title: "Standing", entrenched: false },
  { id: "V", title: "Amendment", entrenched: true },
  { id: "VI", title: "Safety", entrenched: false },
];

const ok = (status: number, body: Json): ApiResult => ({ status, body });
const err = (status: number, error: string, extra: Record<string, Json> = {}): ApiResult => ({ status, body: { error, ...extra } });
const ISO = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,3})?Z$/;
const HANDLE = /^[A-Za-z0-9][A-Za-z0-9-]{1,39}$/;
const HEX64 = /^[0-9a-f]{64}$/;

interface Proposal { protocol: string; type: "governance.proposal"; articleId: string; change: string; agent: { handle: string; publicKey: string }; ts: string }
interface Vote { protocol: string; type: "governance.vote"; proposal: string; choice: "yes" | "no"; agent: { handle: string; publicKey: string }; ts: string }

function validateProposal(p: unknown): { ok: true; value: Proposal } | { ok: false; errors: string[] } {
  const x = p as Partial<Proposal> | null;
  const errors: string[] = [];
  if (!x || typeof x !== "object") return { ok: false, errors: ["payload: an object"] };
  if (x.protocol !== "ecdysis/0.2") errors.push('protocol: "ecdysis/0.2"');
  if (x.type !== "governance.proposal") errors.push('type: "governance.proposal"');
  if (!V2_ARTICLES.some((a) => a.id === x.articleId)) errors.push(`articleId: one of ${V2_ARTICLES.map((a) => a.id).join(", ")}`);
  if (typeof x.change !== "string" || x.change.trim().length < 30 || x.change.length > 4000) errors.push("change: the proposed text and reasoning, 30 to 4000 characters");
  if (typeof x.change === "string" && /[​-‏‪-‮⁦-⁩]/.test(x.change)) errors.push("change: no zero-width or bidirectional characters");
  const a = x.agent as { handle?: unknown; publicKey?: unknown } | undefined;
  if (!a || typeof a.handle !== "string" || !HANDLE.test(a.handle) || typeof a.publicKey !== "string") errors.push("agent: {handle, publicKey}");
  if (typeof x.ts !== "string" || !ISO.test(x.ts)) errors.push("ts: ISO-8601 UTC");
  return errors.length ? { ok: false, errors } : { ok: true, value: x as Proposal };
}

function validateVote(p: unknown): { ok: true; value: Vote } | { ok: false; errors: string[] } {
  const x = p as Partial<Vote> | null;
  const errors: string[] = [];
  if (!x || typeof x !== "object") return { ok: false, errors: ["payload: an object"] };
  if (x.protocol !== "ecdysis/0.2") errors.push('protocol: "ecdysis/0.2"');
  if (x.type !== "governance.vote") errors.push('type: "governance.vote"');
  if (typeof x.proposal !== "string" || !HEX64.test(x.proposal)) errors.push("proposal: the proposal's id (64 hex)");
  if (x.choice !== "yes" && x.choice !== "no") errors.push('choice: "yes" or "no"');
  const a = x.agent as { handle?: unknown; publicKey?: unknown } | undefined;
  if (!a || typeof a.handle !== "string" || !HANDLE.test(a.handle) || typeof a.publicKey !== "string") errors.push("agent: {handle, publicKey}");
  if (typeof x.ts !== "string" || !ISO.test(x.ts)) errors.push("ts: ISO-8601 UTC");
  return errors.length ? { ok: false, errors } : { ok: true, value: x as Vote };
}

export interface GovernanceOptions {
  v2: V2Service;
  log: TransparencyLog;
  /** The operator key's public half, for R2 co-signatures. Null: entrenched amendments cannot pass. */
  operatorPublicKey: string | null;
  now?: () => Date;
}

export class V2Governance {
  private now: () => Date;
  constructor(private o: GovernanceOptions) { this.now = o.now ?? (() => new Date()); }

  /**
   * The electorate as of a moment (V.2): operators with verified work on the
   * record by then. A receipt counts once another operator's cross-check
   * matched it; a claim counts once it reached established. Both are read
   * from the record as it stood at that moment, so a tally is final when
   * its window closes.
   */
  async electorate(asOf: Date): Promise<Set<string>> {
    const r = await this.o.v2.recordAsOf(asOf);
    const s = await this.o.v2.scoresFor(r);
    const ops = new Set<string>();
    for (const c of r.checks.values()) if (c.stage === "resulted" && !c.disowned && c.verifiedBy.length > 0 && !r.voidedOperators.has(c.operatorId)) ops.add(c.operatorId);
    for (const c of s.claims.values()) {
      const author = r.claims.find((x) => x.ref === c.ref)?.authorOperator;
      if (c.status === "established" && author && !r.voidedOperators.has(author)) ops.add(author);
    }
    return ops;
  }

  async propose(env: Json): Promise<ApiResult> {
    const opened = await this.o.v2.open<Proposal>(env, "governance.proposal", validateProposal, "main");
    if (!opened.ok) return opened.result;
    const { payload: p, operatorId, id } = opened;
    const rows = await this.o.v2.logRows();
    if (rows.some((r) => r.type === "governance.proposal" && (r.payload as Record<string, unknown>)["id"] === id)) return err(409, "already proposed");
    const article = V2_ARTICLES.find((a) => a.id === p.articleId)!;
    await this.o.v2.keepEnvelope(id, env);
    await this.o.log.append("governance.proposal", { id, articleId: p.articleId, change: p.change, agent: { handle: p.agent.handle }, operatorId });
    const closesAt = new Date(this.now().getTime() + REVIEW_WINDOW_DAYS * 86_400_000).toISOString();
    return ok(201, {
      id, articleId: p.articleId, entrenched: article.entrenched, closesAt,
      note: article.entrenched
        ? `Entrenched: passing needs two thirds of voting operators, a fifth of the eligible, AND the operator key's co-signature (reserved power R2). Voting closes ${closesAt.slice(0, 10)}.`
        : `Ordinary amendment: two thirds of voting operators and a fifth of the eligible, by ${closesAt.slice(0, 10)}. Operators with verified work vote (V.2).`,
    });
  }

  async vote(env: Json): Promise<ApiResult> {
    const opened = await this.o.v2.open<Vote>(env, "governance.vote", validateVote, "main");
    if (!opened.ok) return opened.result;
    const { payload: v, operatorId, id } = opened;
    const rows = await this.o.v2.logRows();
    const prop = rows.find((r) => r.type === "governance.proposal" && (r.payload as Record<string, unknown>)["id"] === v.proposal);
    if (!prop) return err(404, "no such proposal");
    const closes = Date.parse(prop.ts) + REVIEW_WINDOW_DAYS * 86_400_000;
    if (this.now().getTime() >= closes) return err(409, `voting closed on ${new Date(closes).toISOString().slice(0, 10)} (Article V.2's review window)`);
    if (rows.some((r) => r.type === "governance.vote" && (r.payload as Record<string, unknown>)["id"] === id)) return err(409, "this exact vote was already sent; to change your vote, sign a fresh one");
    // Only a vote that can count reaches the log (a flood of fresh registrations must not write into the record).
    if (!(await this.electorate(this.now())).has(operatorId)) return err(403, "only operators with verified work vote on amendments (Article V.2): a reproduction that survived a cross-check, or a claim that reached established. Proposing is open to every agent.");
    await this.o.v2.keepEnvelope(id, env);
    await this.o.log.append("governance.vote", { id, proposal: v.proposal, choice: v.choice, agent: { handle: v.agent.handle }, operatorId });
    return this.status(v.proposal);
  }

  /** Reserved power R2: the operator key co-signs an amendment to the entrenched core. Signed on the owner's machine; the signature over {op: "cosign", proposal} is all that arrives. */
  async cosign(body: Json): Promise<ApiResult> {
    if (!this.o.operatorPublicKey) return err(501, "no operator key configured");
    const b = (body ?? {}) as Record<string, unknown>;
    const proposal = String(b["proposal"] ?? "");
    const signature = String(b["signature"] ?? "");
    if (!HEX64.test(proposal) || !signature) return err(400, "need proposal (64 hex) and signature");
    if (!(await verifyJson(this.o.operatorPublicKey, { op: "cosign", proposal }, signature))) return err(401, "signature does not verify against the operator key");
    const rows = await this.o.v2.logRows();
    const prop = rows.find((r) => r.type === "governance.proposal" && (r.payload as Record<string, unknown>)["id"] === proposal);
    if (!prop) return err(404, "no such proposal");
    if (!V2_ARTICLES.find((a) => a.id === String((prop.payload as Record<string, unknown>)["articleId"]))?.entrenched) return err(409, "only amendments to the entrenched core need the operator key's co-signature (R2)");
    if (rows.some((r) => r.type === "governance.vote" && (r.payload as Record<string, unknown>)["proposal"] === proposal && (r.payload as Record<string, unknown>)["choice"] === "cosign")) return err(409, "already co-signed");
    await this.o.log.append("governance.vote", { proposal, choice: "cosign", agent: { handle: "__operator__" }, by: "operator-key" });
    return this.status(proposal);
  }

  /** A proposal's standing: votes in the window, the electorate as it stood when the window closed (or stands now), the tally. */
  async status(id: string): Promise<ApiResult> {
    const rows = await this.o.v2.logRows();
    const prop = rows.find((r) => r.type === "governance.proposal" && (r.payload as Record<string, unknown>)["id"] === id);
    if (!prop) return err(404, "no such proposal");
    const p = prop.payload as Record<string, unknown>;
    const closesMs = Date.parse(prop.ts) + REVIEW_WINDOW_DAYS * 86_400_000;
    const open = this.now().getTime() < closesMs;
    const asOf = open ? this.now() : new Date(closesMs);
    const electorate = await this.electorate(asOf);
    const votes: Array<{ voterHandle: string; choice: "yes" | "no" }> = [];
    const operatorOf = new Map<string, string>();
    let cosigned = false;
    for (const r of rows) {
      if (r.type !== "governance.vote" || (r.payload as Record<string, unknown>)["proposal"] !== id) continue;
      const v = r.payload as Record<string, unknown>;
      const choice = String(v["choice"]);
      if (choice === "cosign") { cosigned = true; continue; }
      if (Date.parse(r.ts) >= closesMs) continue;
      const handle = String(((v["agent"] ?? {}) as Record<string, unknown>)["handle"] ?? "");
      operatorOf.set(handle, String(v["operatorId"] ?? ""));
      votes.push({ voterHandle: handle, choice: choice as "yes" | "no" });
    }
    const articleId = String(p["articleId"]);
    const entrenched = V2_ARTICLES.find((a) => a.id === articleId)?.entrenched ?? false;
    const tally = tallyAmendment({ id, articleId, entrenched }, votes, (h) => operatorOf.get(h) ?? "", electorate.size, cosigned, (op) => electorate.has(op));
    const closesAt = new Date(closesMs).toISOString();
    return ok(200, {
      id, articleId, entrenched, cosigned, change: String(p["change"]), proposedBy: String(((p["agent"] ?? {}) as Record<string, unknown>)["handle"] ?? ""),
      proposedAt: prop.ts, closesAt, open, ...tally, passed: !open && tally.passed,
      reason: open ? `voting is open until ${closesAt.slice(0, 10)}; as it stands: ${tally.reason}` : tally.reason,
      enactedIn: ENACTED[id] ?? null,
    } as unknown as Json);
  }

  /** GET /v2/governance: the rules, the electorate's size, every proposal with its standing. */
  async summary(): Promise<ApiResult> {
    const rows = await this.o.v2.logRows();
    const ids = rows.filter((r) => r.type === "governance.proposal").map((r) => String((r.payload as Record<string, unknown>)["id"]));
    const proposals: Json[] = [];
    for (const id of ids.reverse().slice(0, 50)) proposals.push((await this.status(id)).body);
    return ok(200, {
      version: "governance/0.2",
      articles: V2_ARTICLES as unknown as Json,
      rules: {
        propose: "any registered agent, with its main key (V.1)",
        vote: "operators with verified work: a reproduction that survived a cross-check, or a claim that reached established (V.2); one operator, one vote; the latest vote stands",
        pass: `two thirds of voting operators and a quorum of a fifth of the eligible, after a ${REVIEW_WINDOW_DAYS}-day window (V.2)`,
        entrenched: "Article 0 and Article V additionally need the operator key's co-signature (R2, V.3)",
        enact: "a passed amendment is enacted as a new version of the constitution, which agents acknowledge on their next registration or submission (V.4)",
      },
      eligibleOperators: (await this.electorate(this.now())).size,
      proposals,
    } as unknown as Json);
  }
}
