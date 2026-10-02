/**
 * The canary registry on D1 (migration 0017). Off the log. Rows are keyed by
 * a keyed hash of the claim ref, and the ref, outcome, label and source live
 * sealed in one column bound to that key, so the table alone names no live
 * canary.
 */
import type { CanaryRow, CanaryStore } from "../../api/v2/canaries.js";

export class D1CanaryStore implements CanaryStore {
  constructor(private db: D1Database) {}
  private row(r: Record<string, unknown>): CanaryRow {
    return { key: String(r["key"]), sealed: String(r["sealed"]), revealAfter: r["reveal_after"] ? String(r["reveal_after"]) : null, registeredAt: String(r["registered_at"]), registeredBy: String(r["registered_by"]), revealedAt: r["revealed_at"] ? String(r["revealed_at"]) : null };
  }
  async list() {
    const rs = await this.db.prepare("SELECT * FROM steward_canaries ORDER BY registered_at ASC LIMIT 1000").all<Record<string, unknown>>();
    return (rs.results ?? []).map((r) => this.row(r));
  }
  async get(key: string) {
    const r = await this.db.prepare("SELECT * FROM steward_canaries WHERE key = ?1").bind(key).first<Record<string, unknown>>();
    return r ? this.row(r) : null;
  }
  async put(row: CanaryRow) {
    await this.db.prepare("INSERT INTO steward_canaries (key, sealed, reveal_after, registered_at, registered_by, revealed_at) VALUES (?1, ?2, ?3, ?4, ?5, ?6) ON CONFLICT(key) DO UPDATE SET sealed = excluded.sealed, reveal_after = excluded.reveal_after, registered_at = excluded.registered_at, registered_by = excluded.registered_by, revealed_at = excluded.revealed_at")
      .bind(row.key, row.sealed, row.revealAfter, row.registeredAt, row.registeredBy, row.revealedAt).run();
  }
  async delete(key: string) {
    await this.db.prepare("DELETE FROM steward_canaries WHERE key = ?1").bind(key).run();
  }
}
