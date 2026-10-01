/** In-memory Store: tests, local development, and auditor replays. */

import type { Json } from "../core/canonical.js";
import type { LogEntry } from "../core/log.js";
import type {
  AgentRecord, AuditRecord, BuildRecord, ClaimRecord, DeliveryRecord, HeraldRecord, IssueRecord, JurorOperatorRecord, JurorVouchRecord, JuryAlertRecord, SettingRecord,
  LogRowView, PaperRecord, PracticeRecord, QuarantineRecord, ReplicationRecord, Store, SubscriberRecord,
} from "./store.js";

interface LogRow {
  entry: LogEntry;
  entryHash: string;
  leafHash: string;
  payload: Json;
}

export class MemoryStore implements Store {
  private log: LogRow[] = [];
  private agents = new Map<string, AgentRecord>();
  private byKey = new Map<string, string>();
  private papers = new Map<string, PaperRecord>(); // by cid
  private byHandle = new Map<string, string>(); // display handle -> cid
  private order: string[] = []; // cids in accept order
  private replications: ReplicationRecord[] = [];
  private quarantine = new Map<string, QuarantineRecord>();
  private envelopes = new Set<string>();
  private practice = new Map<string, PracticeRecord>();
  private herald = new Map<string, HeraldRecord>();
  private suppressed = new Map<string, string>();

  // --- LogBackend ---
  async logSize(): Promise<number> {
    return this.log.length;
  }
  async lastEntryHash(): Promise<string | null> {
    return this.log.length ? this.log[this.log.length - 1]!.entryHash : null;
  }
  async appendLogRow(row: LogRow): Promise<void> {
    if (row.entry.seq !== this.log.length) throw new Error("append out of order");
    this.log.push(row);
  }
  async getEntry(seq: number): Promise<{ entry: LogEntry; entryHash: string } | null> {
    const r = this.log[seq];
    return r ? { entry: r.entry, entryHash: r.entryHash } : null;
  }
  async leafHashes(size: number): Promise<string[]> {
    if (size > this.log.length) throw new Error("leafHashes: size beyond log");
    return this.log.slice(0, size).map((r) => r.leafHash);
  }
  /** Test/auditor access to payloads in seq order. */
  async allEvents(): Promise<Array<{ seq: number; type: LogEntry["type"]; payload: Json }>> {
    return this.log.map((r) => ({ seq: r.entry.seq, type: r.entry.type, payload: r.payload }));
  }
  async payloadAt(seq: number): Promise<Json> {
    const r = this.log[seq];
    if (!r) throw new Error(`payloadAt: no entry ${seq}`);
    return r.payload;
  }
  /** Test-only: corrupt a stored entry to prove audits catch it. */
  _tamper(seq: number, mutate: (row: LogRow) => void): void {
    mutate(this.log[seq]!);
  }

  // --- agents ---
  async getAgent(handle: string): Promise<AgentRecord | null> {
    return this.agents.get(handle) ?? null;
  }
  async getAgentByKey(publicKey: string): Promise<AgentRecord | null> {
    const h = this.byKey.get(publicKey);
    return h ? this.agents.get(h) ?? null : null;
  }
  async putAgent(agent: AgentRecord): Promise<void> {
    this.agents.set(agent.handle, agent);
    this.byKey.set(agent.publicKey, agent.handle);
  }
  async bumpAccepted(handle: string): Promise<void> {
    const a = this.agents.get(handle);
    if (a) a.acceptedCount += 1;
  }
  private jurorOps = new Map<string, JurorOperatorRecord>();
  private jurorVouches: JurorVouchRecord[] = [];
  async putJurorOperator(r: JurorOperatorRecord): Promise<void> {
    this.jurorOps.set(r.operatorId, { ...r });
  }
  async getJurorOperator(operatorId: string): Promise<JurorOperatorRecord | null> {
    const r = this.jurorOps.get(operatorId);
    return r ? { ...r } : null;
  }
  async listJurorOperators(limit: number): Promise<JurorOperatorRecord[]> {
    return [...this.jurorOps.values()].sort((a, b) => a.seq - b.seq).slice(0, limit).map((r) => ({ ...r }));
  }
  async deleteJurorOperator(operatorId: string): Promise<void> {
    this.jurorOps.delete(operatorId);
  }
  private settings = new Map<string, SettingRecord>();
  async listSettings(): Promise<SettingRecord[]> {
    return [...this.settings.values()].map((x) => ({ ...x }));
  }
  async putSetting(x: SettingRecord): Promise<void> {
    this.settings.set(x.key, { ...x });
  }
  private claims = new Map<string, ClaimRecord>();
  async putClaim(c: ClaimRecord): Promise<void> {
    this.claims.set(c.id, { ...c });
  }
  async getClaim(id: string): Promise<ClaimRecord | null> {
    const c = this.claims.get(id);
    return c ? { ...c } : null;
  }
  async getClaimByCode(code: string): Promise<ClaimRecord | null> {
    const c = [...this.claims.values()].find((x) => x.code === code);
    return c ? { ...c } : null;
  }
  async listClaims(q: { handle?: string; status?: ClaimRecord["status"]; limit: number }): Promise<ClaimRecord[]> {
    return [...this.claims.values()]
      .filter((c) => (q.handle === undefined || c.handle === q.handle) && (q.status === undefined || c.status === q.status))
      .sort((a, b) => b.createdAt.localeCompare(a.createdAt) || b.id.localeCompare(a.id))
      .slice(0, q.limit)
      .map((c) => ({ ...c }));
  }
  async putJurorVouch(v: JurorVouchRecord): Promise<void> {
    if (!this.jurorVouches.some((x) => x.fromOperator === v.fromOperator && x.forOperator === v.forOperator)) this.jurorVouches.push({ ...v });
  }
  async listJurorVouches(q: { forOperator?: string; fromOperator?: string }): Promise<JurorVouchRecord[]> {
    return this.jurorVouches
      .filter((v) => (q.forOperator === undefined || v.forOperator === q.forOperator) && (q.fromOperator === undefined || v.fromOperator === q.fromOperator))
      .map((v) => ({ ...v }));
  }

  async setAgentJuryFields(handle: string, f: { ineligibleUntil?: string | null; practiceQualifiedAt?: string | null; independentQualifiedAt?: string | null }): Promise<void> {
    const a = this.agents.get(handle);
    if (!a) return;
    if (f.ineligibleUntil !== undefined) a.ineligibleUntil = f.ineligibleUntil;
    if (f.practiceQualifiedAt !== undefined) a.practiceQualifiedAt = f.practiceQualifiedAt;
    if (f.independentQualifiedAt !== undefined) a.independentQualifiedAt = f.independentQualifiedAt;
  }
  async putPractice(p: PracticeRecord): Promise<void> {
    this.practice.set(p.id, structuredClone(p));
  }
  async getPractice(id: string): Promise<PracticeRecord | null> {
    const p = this.practice.get(id);
    return p ? structuredClone(p) : null;
  }
  async listPracticeFor(handle: string, sinceIso: string): Promise<PracticeRecord[]> {
    return [...this.practice.values()]
      .filter((p) => p.handle === handle && p.issuedAt >= sinceIso)
      .sort((a, b) => a.issuedAt.localeCompare(b.issuedAt))
      .map((p) => structuredClone(p));
  }
  async countPracticeForOperator(operatorId: string, sinceIso: string): Promise<number> {
    return [...this.practice.values()].filter((p) => p.operatorId === operatorId && p.issuedAt >= sinceIso).length;
  }
  async putHerald(h: HeraldRecord): Promise<void> {
    this.herald.set(h.id, structuredClone(h));
  }
  async getHerald(id: string): Promise<HeraldRecord | null> {
    const h = this.herald.get(id);
    return h ? structuredClone(h) : null;
  }
  async listHerald(limit: number): Promise<HeraldRecord[]> {
    return [...this.herald.values()].sort((a, b) => b.createdAt.localeCompare(a.createdAt)).slice(0, limit).map((h) => structuredClone(h));
  }
  async countHeraldSent(sinceIso: string, domain?: string): Promise<number> {
    return [...this.herald.values()].filter((h) =>
      h.status === "sent" && (h.sentAt ?? "") >= sinceIso && (!domain || h.recipient.toLowerCase().endsWith("@" + domain))).length;
  }
  async isSuppressed(email: string): Promise<boolean> {
    return this.suppressed.has(email.toLowerCase());
  }
  async suppress(email: string, at: string): Promise<void> {
    if (!this.suppressed.has(email.toLowerCase())) this.suppressed.set(email.toLowerCase(), at);
  }
  async listSuppressed(limit: number): Promise<Array<{ email: string; at: string }>> {
    return [...this.suppressed.entries()].map(([email, at]) => ({ email, at }))
      .sort((a, b) => b.at.localeCompare(a.at)).slice(0, limit);
  }

  // --- digest (operational, private) ---
  private subscribers = new Map<string, SubscriberRecord>();
  private issues = new Map<string, IssueRecord>();
  private deliveries = new Map<string, DeliveryRecord>(); // `${issue}|${subscriber}`
  private sends: Array<{ at: string; kind: string }> = [];
  async putSubscriber(s: SubscriberRecord): Promise<void> {
    const clash = [...this.subscribers.values()].find((x) => x.email === s.email && x.id !== s.id);
    if (clash) throw new Error("UNIQUE constraint failed: subscribers.email");
    this.subscribers.set(s.id, structuredClone(s));
  }
  async getSubscriber(id: string): Promise<SubscriberRecord | null> {
    const s = this.subscribers.get(id);
    return s ? structuredClone(s) : null;
  }
  async getSubscriberByEmail(email: string): Promise<SubscriberRecord | null> {
    const s = [...this.subscribers.values()].find((x) => x.email === email.toLowerCase());
    return s ? structuredClone(s) : null;
  }
  async listSubscribers(limit: number): Promise<SubscriberRecord[]> {
    return [...this.subscribers.values()].sort((a, b) => b.createdAt.localeCompare(a.createdAt))
      .slice(0, limit).map((s) => structuredClone(s));
  }
  async deleteSubscriber(id: string): Promise<void> {
    this.subscribers.delete(id);
    for (const k of [...this.deliveries.keys()]) if (k.endsWith(`|${id}`)) this.deliveries.delete(k);
  }
  async listStalePending(beforeIso: string, limit: number): Promise<SubscriberRecord[]> {
    return [...this.subscribers.values()]
      .filter((s) => s.status === "pending" && (s.confirmSentAt ?? s.createdAt) < beforeIso)
      .slice(0, limit).map((s) => structuredClone(s));
  }
  async putIssue(i: IssueRecord): Promise<void> {
    this.issues.set(i.id, structuredClone(i));
  }
  async getIssue(id: string): Promise<IssueRecord | null> {
    const i = this.issues.get(id);
    return i ? structuredClone(i) : null;
  }
  async listIssues(limit: number): Promise<IssueRecord[]> {
    return [...this.issues.values()].sort((a, b) => b.createdAt.localeCompare(a.createdAt))
      .slice(0, limit).map((i) => structuredClone(i));
  }
  async claimIssue(id: string, at: string): Promise<boolean> {
    const i = this.issues.get(id);
    if (!i || i.status !== "draft") return false;
    i.status = "sending";
    i.startedAt = at;
    return true;
  }
  async putDelivery(d: DeliveryRecord): Promise<void> {
    this.deliveries.set(`${d.issueId}|${d.subscriberId}`, structuredClone(d));
  }
  async listDeliveries(issueId: string): Promise<DeliveryRecord[]> {
    return [...this.deliveries.values()].filter((d) => d.issueId === issueId).map((d) => structuredClone(d));
  }
  async recordEmailSend(at: string, kind: "herald" | "confirm" | "issue" | "alert"): Promise<void> {
    this.sends.push({ at, kind });
  }

  // --- jury alerts ---
  private alerts = new Map<string, JuryAlertRecord>();
  private alertSends = new Set<string>();
  async putJuryAlert(a: JuryAlertRecord): Promise<void> {
    const clash = [...this.alerts.values()].find((x) => x.handle === a.handle && x.id !== a.id);
    if (clash) throw new Error("UNIQUE constraint failed: jury_alerts.handle");
    this.alerts.set(a.id, structuredClone(a));
  }
  async getJuryAlert(id: string): Promise<JuryAlertRecord | null> {
    const a = this.alerts.get(id);
    return a ? structuredClone(a) : null;
  }
  async getJuryAlertByHandle(handle: string): Promise<JuryAlertRecord | null> {
    const a = [...this.alerts.values()].find((x) => x.handle === handle);
    return a ? structuredClone(a) : null;
  }
  async listJuryAlerts(limit: number): Promise<JuryAlertRecord[]> {
    return [...this.alerts.values()].sort((a, b) => b.createdAt.localeCompare(a.createdAt)).slice(0, limit).map((a) => structuredClone(a));
  }
  async deleteJuryAlert(id: string): Promise<void> {
    this.alerts.delete(id);
  }
  async claimAlertSend(handle: string, subject: string, kind: string, _at: string): Promise<boolean> {
    const k = `${handle}|${subject}|${kind}`;
    if (this.alertSends.has(k)) return false;
    this.alertSends.add(k);
    return true;
  }
  async releaseAlertSend(handle: string, subject: string, kind: string): Promise<void> {
    this.alertSends.delete(`${handle}|${subject}|${kind}`);
  }
  async countEmailSends(sinceIso: string, kind?: string): Promise<number> {
    return this.sends.filter((s) => s.at >= sinceIso && (!kind || s.kind === kind)).length;
  }

  // --- operator console ---
  private opsState = new Map<string, { value: Json; at: string }>();
  private audit: AuditRecord[] = [];
  async putOpsState(key: string, value: Json, at: string): Promise<void> {
    this.opsState.set(key, { value: structuredClone(value), at });
  }
  async getOpsState(key: string): Promise<{ value: Json; at: string } | null> {
    const v = this.opsState.get(key);
    return v ? structuredClone(v) : null;
  }
  async appendAudit(a: AuditRecord): Promise<void> {
    this.audit.push({ ...a });
  }
  async listAudit(limit: number): Promise<AuditRecord[]> {
    return [...this.audit].reverse().slice(0, limit);
  }
  async listLog(fromSeq: number, limit: number): Promise<LogRowView[]> {
    return this.log.slice(Math.max(0, fromSeq), Math.max(0, fromSeq) + limit)
      .map((r) => ({ seq: r.entry.seq, ts: r.entry.ts, type: r.entry.type, payload: r.payload }));
  }
  async listPracticeSince(sinceIso: string, limit: number): Promise<PracticeRecord[]> {
    return [...this.practice.values()].filter((p) => p.issuedAt >= sinceIso)
      .sort((a, b) => a.issuedAt.localeCompare(b.issuedAt)).slice(0, limit).map((p) => structuredClone(p));
  }

  // --- papers ---
  async putPaper(p: PaperRecord): Promise<void> {
    this.papers.set(p.cid, p);
    this.byHandle.set(p.handle, p.cid);
    this.order.push(p.cid);
  }
  async getPaper(idOrCid: string): Promise<PaperRecord | null> {
    const cid = this.papers.has(idOrCid) ? idOrCid : this.byHandle.get(idOrCid);
    return cid ? this.papers.get(cid) ?? null : null;
  }
  async listPapers(limit: number, field?: string): Promise<PaperRecord[]> {
    const out: PaperRecord[] = [];
    for (let i = this.order.length - 1; i >= 0 && out.length < limit; i--) {
      const p = this.papers.get(this.order[i]!)!;
      if (!field || p.payload.field === field) out.push(p);
    }
    return out;
  }
  async putReplication(r: ReplicationRecord): Promise<void> {
    this.replications.push(r);
  }
  async listReplicationsFor(paperId: string): Promise<ReplicationRecord[]> {
    return this.replications.filter((r) =>
      r.payload.targets.some((t) => t.split("#")[0] === paperId),
    );
  }

  async listAgents(limit: number): Promise<AgentRecord[]> {
    return [...this.agents.values()].slice(0, limit);
  }

  async listFieldOperators(field: string): Promise<string[]> {
    const ops = new Set<string>();
    const operatorOf = (agentHandle: string) => this.agents.get(agentHandle)?.operatorId;
    for (const p of this.papers.values()) {
      if (p.payload.field !== field) continue;
      const op = operatorOf(p.payload.agent.handle);
      if (op) ops.add(op);
    }
    for (const r of this.replications) {
      const inField = r.payload.targets.some((t) => {
        const pid = t.split("#")[0]!;
        const cid = this.papers.has(pid) ? pid : this.byHandle.get(pid);
        const paper = cid ? this.papers.get(cid) : undefined;
        return paper?.payload.field === field;
      });
      if (!inField) continue;
      const op = operatorOf(r.payload.agent.handle);
      if (op) ops.add(op);
    }
    return [...ops].sort();
  }

  // --- quarantine ---
  async putQuarantine(q: QuarantineRecord): Promise<void> {
    // A withdrawal is one-way: a full-row write from a stale read never undoes it (as in D1).
    const withdrawn = q.preprintWithdrawnAt ?? this.quarantine.get(q.id)?.preprintWithdrawnAt;
    this.quarantine.set(q.id, structuredClone({ ...q, ...(withdrawn ? { preprintWithdrawnAt: withdrawn } : {}) }));
  }
  async markPreprintWithdrawn(id: string, at: string): Promise<void> {
    const q = this.quarantine.get(id);
    if (q && !q.preprintWithdrawnAt) q.preprintWithdrawnAt = at;
  }
  async getQuarantine(id: string): Promise<QuarantineRecord | null> {
    const q = this.quarantine.get(id);
    return q ? structuredClone(q) : null;
  }
  async listQuarantine(status: QuarantineRecord["status"], limit: number, order: "asc" | "desc" = "asc"): Promise<QuarantineRecord[]> {
    const rows = [...this.quarantine.values()].filter((q) => q.status === status)
      .sort((a, b) => a.receivedAt.localeCompare(b.receivedAt));
    return (order === "desc" ? rows.reverse() : rows).slice(0, limit);
  }

  // --- builds ---
  private builds = new Map<string, BuildRecord>(); // by cid
  private buildSlugs = new Map<string, string>(); // slug -> cid
  async putBuild(b: BuildRecord): Promise<void> {
    this.builds.set(b.cid, structuredClone(b));
    this.buildSlugs.set(b.slug, b.cid);
  }
  async getBuild(cidOrSlug: string): Promise<BuildRecord | null> {
    const cid = this.builds.has(cidOrSlug) ? cidOrSlug : this.buildSlugs.get(cidOrSlug);
    const b = cid ? this.builds.get(cid) : undefined;
    return b ? structuredClone(b) : null;
  }
  async listBuilds(status: BuildRecord["status"], limit: number): Promise<BuildRecord[]> {
    return [...this.builds.values()]
      .filter((b) => b.status === status)
      .slice(0, limit)
      .map((b) => structuredClone(b));
  }

  // --- idempotency ---
  async seenEnvelope(hash: string): Promise<boolean> {
    return this.envelopes.has(hash);
  }
  async markEnvelope(hash: string): Promise<void> {
    this.envelopes.add(hash);
  }

  private access = new Map<string, number>();
  async bumpAccess(id: string): Promise<void> {
    this.access.set(id, (this.access.get(id) ?? 0) + 1);
  }
  async getAccess(id: string): Promise<number> {
    return this.access.get(id) ?? 0;
  }
  async listAccessPrefix(prefix: string): Promise<Array<{ id: string; count: number }>> {
    return [...this.access.entries()]
      .filter(([id]) => id.startsWith(prefix))
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([id, count]) => ({ id, count }));
  }
  async listAccessBetween(lo: string, hi: string, limit: number): Promise<Array<{ id: string; count: number }>> {
    return [...this.access.entries()]
      .filter(([id]) => id >= lo && id < hi)
      .sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0))
      .slice(0, limit)
      .map(([id, count]) => ({ id, count }));
  }
}
