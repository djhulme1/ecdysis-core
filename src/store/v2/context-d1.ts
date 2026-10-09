/** The context writer's rows on D1 (migration 0022): the papers' records and the claims' summaries. Off the log. */
import type { ClaimContextRow, ContextStore, SourceRecordRow } from "../../api/v2/context.js";

function json<T>(v: unknown): T | null {
  if (typeof v !== "string" || !v) return null;
  try { return JSON.parse(v) as T; } catch { return null; }
}

export class D1ContextStore implements ContextStore {
  constructor(private db: D1Database) {}

  private source(r: Record<string, unknown>): SourceRecordRow {
    return {
      source: String(r["source"]), status: String(r["status"]) as SourceRecordRow["status"], record: json(r["record"]),
      readAt: String(r["read_at"]), attempts: Number(r["attempts"] ?? 1), detail: r["detail"] ? String(r["detail"]) : null,
    };
  }

  private claim(r: Record<string, unknown>): ClaimContextRow {
    return {
      claim: String(r["claim"]), status: String(r["status"]) as ClaimContextRow["status"], version: String(r["version"]),
      model: r["model"] ? String(r["model"]) : null, inputsHash: r["inputs_hash"] ? String(r["inputs_hash"]) : null, explanation: json(r["explanation"]),
      writtenAt: String(r["written_at"]), attempts: Number(r["attempts"] ?? 1), detail: r["detail"] ? String(r["detail"]) : null,
    };
  }

  async getSource(source: string) {
    const r = await this.db.prepare("SELECT * FROM v2_source_records WHERE source = ?1").bind(source).first<Record<string, unknown>>();
    return r ? this.source(r) : null;
  }

  async putSource(row: SourceRecordRow) {
    await this.db.prepare("INSERT INTO v2_source_records (source, status, record, read_at, attempts, detail) VALUES (?1, ?2, ?3, ?4, ?5, ?6) ON CONFLICT(source) DO UPDATE SET status = excluded.status, record = excluded.record, read_at = excluded.read_at, attempts = excluded.attempts, detail = excluded.detail")
      .bind(row.source, row.status, row.record ? JSON.stringify(row.record) : null, row.readAt, row.attempts, row.detail).run();
  }

  async getClaim(claim: string) {
    const r = await this.db.prepare("SELECT * FROM v2_claim_context WHERE claim = ?1").bind(claim).first<Record<string, unknown>>();
    return r ? this.claim(r) : null;
  }

  async putClaim(row: ClaimContextRow) {
    await this.db.prepare("INSERT INTO v2_claim_context (claim, status, version, model, inputs_hash, explanation, written_at, attempts, detail) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9) ON CONFLICT(claim) DO UPDATE SET status = excluded.status, version = excluded.version, model = excluded.model, inputs_hash = excluded.inputs_hash, explanation = excluded.explanation, written_at = excluded.written_at, attempts = excluded.attempts, detail = excluded.detail")
      .bind(row.claim, row.status, row.version, row.model, row.inputsHash, row.explanation ? JSON.stringify(row.explanation) : null, row.writtenAt, row.attempts, row.detail).run();
  }

  async sourceIndex() {
    const rs = await this.db.prepare("SELECT source, status, read_at, attempts FROM v2_source_records").all<Record<string, unknown>>();
    return new Map((rs.results ?? []).map((r) => [String(r["source"]), { status: String(r["status"]) as SourceRecordRow["status"], readAt: String(r["read_at"]), attempts: Number(r["attempts"] ?? 1) }] as const));
  }

  async claimIndex() {
    const rs = await this.db.prepare("SELECT claim, status, version, model, written_at, attempts FROM v2_claim_context").all<Record<string, unknown>>();
    return new Map((rs.results ?? []).map((r) => [String(r["claim"]), { status: String(r["status"]) as ClaimContextRow["status"], version: String(r["version"]), model: r["model"] ? String(r["model"]) : null, writtenAt: String(r["written_at"]), attempts: Number(r["attempts"] ?? 1) }] as const));
  }
}
