/**
 * The issues queue and the complaints and flags behind it, on D1 (migrations
 * 0018 and 0020). Off the log; read by stewards only.
 */
import type { ComplaintRow, FlagKind, FlagRow, IssueKind, IssueRow, IssueSource, IssueStatus, IssueStore } from "../../api/v2/issues.js";

export class D1IssueStore implements IssueStore {
  constructor(private db: D1Database) {}
  private issue(r: Record<string, unknown>): IssueRow {
    return {
      id: String(r["id"]), kind: String(r["kind"]) as IssueKind, subject: String(r["subject"]), severity: Number(r["severity"]) as 1 | 2 | 3, detail: String(r["detail"] ?? ""),
      source: String(r["source"]) as IssueSource, status: String(r["status"]) as IssueStatus, openedAt: String(r["opened_at"]),
      decidedAt: r["decided_at"] ? String(r["decided_at"]) : null, decidedBy: r["decided_by"] ? String(r["decided_by"]) : null, note: r["note"] ? String(r["note"]) : null,
    };
  }
  private complaint(r: Record<string, unknown>): ComplaintRow {
    return { id: String(r["id"]), issueId: String(r["issue_id"]), subject: String(r["subject"]), text: String(r["text"] ?? ""), contact: String(r["contact"] ?? ""), ipHash: String(r["ip_hash"]), at: String(r["at"]) };
  }
  async listIssues(status: IssueStatus | "all", limit: number) {
    const n = Math.min(Math.max(1, limit), 500);
    const rs = status === "all"
      ? await this.db.prepare("SELECT * FROM v2_issues ORDER BY opened_at DESC LIMIT ?1").bind(n).all<Record<string, unknown>>()
      : await this.db.prepare("SELECT * FROM v2_issues WHERE status = ?1 ORDER BY opened_at DESC LIMIT ?2").bind(status, n).all<Record<string, unknown>>();
    return (rs.results ?? []).map((r) => this.issue(r));
  }
  async getIssue(id: string) {
    const r = await this.db.prepare("SELECT * FROM v2_issues WHERE id = ?1").bind(id).first<Record<string, unknown>>();
    return r ? this.issue(r) : null;
  }
  async putIssue(row: IssueRow) {
    await this.db.prepare("INSERT INTO v2_issues (id, kind, subject, severity, detail, source, status, opened_at, decided_at, decided_by, note) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11) ON CONFLICT(id) DO UPDATE SET severity = excluded.severity, detail = excluded.detail, status = excluded.status, decided_at = excluded.decided_at, decided_by = excluded.decided_by, note = excluded.note")
      .bind(row.id, row.kind, row.subject, row.severity, row.detail, row.source, row.status, row.openedAt, row.decidedAt, row.decidedBy, row.note).run();
  }
  async openIssue(kind: IssueKind, subject: string) {
    const r = await this.db.prepare("SELECT * FROM v2_issues WHERE kind = ?1 AND subject = ?2 AND status = 'open' ORDER BY opened_at ASC LIMIT 1").bind(kind, subject).first<Record<string, unknown>>();
    return r ? this.issue(r) : null;
  }
  async latestIssue(kind: IssueKind, subject: string) {
    const r = await this.db.prepare("SELECT * FROM v2_issues WHERE kind = ?1 AND subject = ?2 ORDER BY opened_at DESC LIMIT 1").bind(kind, subject).first<Record<string, unknown>>();
    return r ? this.issue(r) : null;
  }
  async putComplaint(row: ComplaintRow) {
    await this.db.prepare("INSERT OR IGNORE INTO v2_complaints (id, issue_id, subject, text, contact, ip_hash, at) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7)").bind(row.id, row.issueId, row.subject, row.text, row.contact, row.ipHash, row.at).run();
  }
  async complaintsFor(issueId: string) {
    const rs = await this.db.prepare("SELECT * FROM v2_complaints WHERE issue_id = ?1 ORDER BY at ASC LIMIT 100").bind(issueId).all<Record<string, unknown>>();
    return (rs.results ?? []).map((r) => this.complaint(r));
  }
  async complaintsSince(ipHash: string, sinceIso: string) {
    const r = await this.db.prepare("SELECT COUNT(*) AS n FROM v2_complaints WHERE ip_hash = ?1 AND at >= ?2").bind(ipHash, sinceIso).first<{ n: number }>();
    return Number(r?.n ?? 0);
  }
  private flag(r: Record<string, unknown>): FlagRow {
    return { id: String(r["id"]), issueId: String(r["issue_id"]), subject: String(r["subject"]), kind: String(r["kind"]) as FlagKind, operatorId: String(r["operator_id"]), handle: String(r["handle"]), stake: Number(r["stake"]) === 1, detail: String(r["detail"] ?? ""), at: String(r["at"]) };
  }
  async putFlag(row: FlagRow) {
    await this.db.prepare("INSERT OR IGNORE INTO v2_flags (id, issue_id, subject, kind, operator_id, handle, stake, detail, at) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9)")
      .bind(row.id, row.issueId, row.subject, row.kind, row.operatorId, row.handle, row.stake ? 1 : 0, row.detail, row.at).run();
  }
  async hasFlag(id: string) {
    return !!(await this.db.prepare("SELECT 1 AS x FROM v2_flags WHERE id = ?1").bind(id).first<{ x: number }>());
  }
  async flagsFor(issueId: string) {
    const rs = await this.db.prepare("SELECT * FROM v2_flags WHERE issue_id = ?1 ORDER BY at ASC LIMIT 100").bind(issueId).all<Record<string, unknown>>();
    return (rs.results ?? []).map((r) => this.flag(r));
  }
  async flagsSince(operatorId: string, sinceIso: string) {
    const r = await this.db.prepare("SELECT COUNT(*) AS n FROM v2_flags WHERE operator_id = ?1 AND at >= ?2").bind(operatorId, sinceIso).first<{ n: number }>();
    return Number(r?.n ?? 0);
  }
  async flagOn(issueId: string, operatorId: string) {
    const r = await this.db.prepare("SELECT * FROM v2_flags WHERE issue_id = ?1 AND operator_id = ?2 LIMIT 1").bind(issueId, operatorId).first<Record<string, unknown>>();
    return r ? this.flag(r) : null;
  }
  async flagOutcomes(operatorId: string, limit: number) {
    const rs = await this.db.prepare("SELECT i.status AS status FROM v2_flags f JOIN v2_issues i ON i.id = f.issue_id WHERE f.operator_id = ?1 AND i.status != 'open' ORDER BY f.at DESC LIMIT ?2")
      .bind(operatorId, Math.min(Math.max(1, limit), 100)).all<{ status: string }>();
    return (rs.results ?? []).map((r) => String(r.status) as IssueStatus);
  }
}
