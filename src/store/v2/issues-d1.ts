/**
 * The issues queue and the complaints behind it, on D1 (migration 0018). Off
 * the log; read by stewards only.
 */
import type { ComplaintRow, IssueKind, IssueRow, IssueSource, IssueStatus, IssueStore } from "../../api/v2/issues.js";

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
}
