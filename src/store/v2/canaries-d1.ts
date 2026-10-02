/**
 * The canary registry on D1 (migration 0017). Off the log; the outcome,
 * label and source live sealed in one column, so the table alone names no
 * live canary.
 */
import type { CanaryRow, CanaryStore } from "../../api/v2/canaries.js";

export class D1CanaryStore implements CanaryStore {
  constructor(private db: D1Database) {}
  private row(r: Record<string, unknown>): CanaryRow {
    return { claim: String(r["claim"]), sealed: String(r["sealed"]), revealAfter: r["reveal_after"] ? String(r["reveal_after"]) : null, registeredAt: String(r["registered_at"]), registeredBy: String(r["registered_by"]), revealedAt: r["revealed_at"] ? String(r["revealed_at"]) : null };
  }
  async list() {
    const rs = await this.db.prepare("SELECT * FROM steward_canaries ORDER BY registered_at ASC LIMIT 1000").all<Record<string, unknown>>();
    return (rs.results ?? []).map((r) => this.row(r));
  }
  async get(claim: string) {
    const r = await this.db.prepare("SELECT * FROM steward_canaries WHERE claim = ?1").bind(claim).first<Record<string, unknown>>();
    return r ? this.row(r) : null;
  }
  async put(row: CanaryRow) {
    await this.db.prepare("INSERT INTO steward_canaries (claim, sealed, reveal_after, registered_at, registered_by, revealed_at) VALUES (?1, ?2, ?3, ?4, ?5, ?6) ON CONFLICT(claim) DO UPDATE SET sealed = excluded.sealed, reveal_after = excluded.reveal_after, registered_at = excluded.registered_at, registered_by = excluded.registered_by, revealed_at = excluded.revealed_at")
      .bind(row.claim, row.sealed, row.revealAfter, row.registeredAt, row.registeredBy, row.revealedAt).run();
  }
  async delete(claim: string) {
    await this.db.prepare("DELETE FROM steward_canaries WHERE claim = ?1").bind(claim).run();
  }
}
