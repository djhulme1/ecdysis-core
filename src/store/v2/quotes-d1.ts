/** The quote scout's results on D1 (migration 0019). Off the log. */
import type { QuoteCheck, QuoteCheckStore, QuoteStatus } from "../../api/v2/quotes.js";

export class D1QuoteCheckStore implements QuoteCheckStore {
  constructor(private db: D1Database) {}
  private row(r: Record<string, unknown>): QuoteCheck {
    return {
      claim: String(r["claim"]), status: String(r["status"]) as QuoteStatus, where: (r["where_found"] ? String(r["where_found"]) : null) as QuoteCheck["where"],
      nearest: r["nearest"] ? String(r["nearest"]) : null, similarity: r["similarity"] === null || r["similarity"] === undefined ? null : Number(r["similarity"]),
      checkedAt: String(r["checked_at"]), attempts: Number(r["attempts"] ?? 1), detail: r["detail"] ? String(r["detail"]) : null,
    };
  }
  async get(claim: string) {
    const r = await this.db.prepare("SELECT * FROM v2_quote_checks WHERE claim = ?1").bind(claim).first<Record<string, unknown>>();
    return r ? this.row(r) : null;
  }
  async put(row: QuoteCheck) {
    await this.db.prepare("INSERT INTO v2_quote_checks (claim, status, where_found, nearest, similarity, checked_at, attempts, detail) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8) ON CONFLICT(claim) DO UPDATE SET status = excluded.status, where_found = excluded.where_found, nearest = excluded.nearest, similarity = excluded.similarity, checked_at = excluded.checked_at, attempts = excluded.attempts, detail = excluded.detail")
      .bind(row.claim, row.status, row.where, row.nearest, row.similarity, row.checkedAt, row.attempts, row.detail).run();
  }
  async statusIndex() {
    const rs = await this.db.prepare("SELECT claim, status FROM v2_quote_checks").all<Record<string, unknown>>();
    return new Map((rs.results ?? []).map((r) => [String(r["claim"]), String(r["status"]) as QuoteStatus] as const));
  }
  async list(limit: number) {
    const rs = await this.db.prepare("SELECT * FROM v2_quote_checks ORDER BY checked_at DESC LIMIT ?1").bind(Math.min(Math.max(1, limit), 1000)).all<Record<string, unknown>>();
    return (rs.results ?? []).map((r) => this.row(r));
  }
}
