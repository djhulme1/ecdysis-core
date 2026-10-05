/**
 * D1 (SQLite) Store for Cloudflare. Mirrors MemoryStore behaviour exactly;
 * the tests define that behaviour against MemoryStore, and the migrations
 * define this schema.
 *
 * Concurrency note: appends must be serialised. A conflicting append
 * violates the PRIMARY KEY on log_entries.seq, and the caller retries.
 * Never relax that constraint: it is what makes "append-only" mean
 * something.
 */

import type { Json } from "../core/canonical.js";
import type { LogEntry } from "../core/log.js";
import type { DoorbellRecord, DoorbellRing, DoorbellSettings, EmailKind, LogRowView, Store } from "./store.js";

export class D1Store implements Store {
  constructor(private db: D1Database) {}

  async logSize(): Promise<number> {
    const r = await this.db.prepare("SELECT COUNT(*) AS n FROM log_entries").first<{ n: number }>();
    return r?.n ?? 0;
  }

  async lastEntryHash(): Promise<string | null> {
    const r = await this.db
      .prepare("SELECT entry_hash FROM log_entries ORDER BY seq DESC LIMIT 1")
      .first<{ entry_hash: string }>();
    return r?.entry_hash ?? null;
  }

  async appendLogRow(row: {
    entry: LogEntry; entryHash: string; leafHash: string; payload: Json;
  }): Promise<void> {
    await this.db
      .prepare(
        `INSERT INTO log_entries (seq, ts, type, payload_hash, prev_hash, entry_hash, leaf_hash, payload_json)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8)`,
      )
      .bind(
        row.entry.seq, row.entry.ts, row.entry.type, row.entry.payloadHash,
        row.entry.prevHash, row.entryHash, row.leafHash, JSON.stringify(row.payload),
      )
      .run();
  }

  async getEntry(seq: number): Promise<{ entry: LogEntry; entryHash: string } | null> {
    const r = await this.db
      .prepare("SELECT * FROM log_entries WHERE seq = ?1")
      .bind(seq)
      .first<Record<string, unknown>>();
    if (!r) return null;
    return {
      entry: {
        seq: r["seq"] as number, ts: r["ts"] as string,
        type: r["type"] as LogEntry["type"],
        payloadHash: r["payload_hash"] as string, prevHash: r["prev_hash"] as string,
      },
      entryHash: r["entry_hash"] as string,
    };
  }

  async leafHashes(size: number): Promise<string[]> {
    const rs = await this.db
      .prepare("SELECT leaf_hash FROM log_entries WHERE seq < ?1 ORDER BY seq")
      .bind(size)
      .all<{ leaf_hash: string }>();
    const rows = rs.results ?? [];
    if (rows.length !== size) throw new Error("leafHashes: size beyond log");
    return rows.map((r) => r.leaf_hash);
  }

  async recordEmailSend(at: string, kind: EmailKind): Promise<void> {
    await this.db.prepare("INSERT INTO email_sends (at, kind) VALUES (?1, ?2)").bind(at, kind).run();
  }

  async claimAlertSend(handle: string, subject: string, kind: string, at: string): Promise<boolean> {
    const r = await this.db
      .prepare("INSERT OR IGNORE INTO jury_alert_sends (handle, subject, kind, at) VALUES (?1, ?2, ?3, ?4)")
      .bind(handle, subject, kind, at).run();
    return (r.meta?.changes ?? 0) > 0;
  }

  async releaseAlertSend(handle: string, subject: string, kind: string): Promise<void> {
    await this.db.prepare("DELETE FROM jury_alert_sends WHERE handle = ?1 AND subject = ?2 AND kind = ?3").bind(handle, subject, kind).run();
  }

  async countEmailSends(sinceIso: string, kind?: string): Promise<number> {
    const r = kind
      ? await this.db.prepare("SELECT COUNT(*) AS n FROM email_sends WHERE at >= ?1 AND kind = ?2").bind(sinceIso, kind).first<{ n: number }>()
      : await this.db.prepare("SELECT COUNT(*) AS n FROM email_sends WHERE at >= ?1").bind(sinceIso).first<{ n: number }>();
    return r?.n ?? 0;
  }

  async putDoorbell(d: DoorbellRecord): Promise<void> {
    await this.db
      .prepare(
        `INSERT INTO doorbells (handle, kind, status, cadence, routine_id, url, token_sealed, key_ref, setup_id, setup_token, setup_issued_at,
           challenge, created_at, updated_at, last_ring_at, last_research_at, last_ok_at, last_session_url, failures, last_error, rings_day, rings_today,
           target_sealed, settings_json)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?13, ?14, ?15, ?16, ?17, ?18, ?19, ?20, ?21, ?22, ?23, ?24)
         ON CONFLICT(handle) DO UPDATE SET kind=?2, status=?3, cadence=?4, routine_id=?5, url=?6, token_sealed=?7, key_ref=?8, setup_id=?9,
           setup_token=?10, setup_issued_at=?11, challenge=?12, updated_at=?14, last_ring_at=?15, last_research_at=?16, last_ok_at=?17,
           last_session_url=?18, failures=?19, last_error=?20, rings_day=?21, rings_today=?22, target_sealed=?23, settings_json=?24`,
      )
      .bind(d.handle, d.kind, d.status, d.cadence, d.routineId ?? null, d.url ?? null, d.tokenSealed ?? null, d.keyRef ?? null,
        d.setupId, d.setupToken, d.setupIssuedAt, d.challenge ?? null, d.createdAt, d.updatedAt, d.lastRingAt ?? null,
        d.lastResearchAt ?? null, d.lastOkAt ?? null, d.lastSessionUrl ?? null, d.failures, d.lastError ?? null, d.ringsDay ?? null, d.ringsToday,
        d.targetSealed ?? null, JSON.stringify(d.settings ?? {}))
      .run();
  }

  async putDoorbellIf(d: DoorbellRecord, expectUpdatedAt: string | null): Promise<boolean> {
    const values = [d.handle, d.kind, d.status, d.cadence, d.routineId ?? null, d.url ?? null, d.tokenSealed ?? null, d.keyRef ?? null,
      d.setupId, d.setupToken, d.setupIssuedAt, d.challenge ?? null, d.createdAt, d.updatedAt, d.lastRingAt ?? null,
      d.lastResearchAt ?? null, d.lastOkAt ?? null, d.lastSessionUrl ?? null, d.failures, d.lastError ?? null, d.ringsDay ?? null, d.ringsToday,
      d.targetSealed ?? null, JSON.stringify(d.settings ?? {})];
    const res = expectUpdatedAt === null
      ? await this.db.prepare(
        `INSERT INTO doorbells (handle, kind, status, cadence, routine_id, url, token_sealed, key_ref, setup_id, setup_token, setup_issued_at,
           challenge, created_at, updated_at, last_ring_at, last_research_at, last_ok_at, last_session_url, failures, last_error, rings_day, rings_today,
           target_sealed, settings_json)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?13, ?14, ?15, ?16, ?17, ?18, ?19, ?20, ?21, ?22, ?23, ?24)
         ON CONFLICT(handle) DO NOTHING`,
      ).bind(...values).run()
      : await this.db.prepare(
        `UPDATE doorbells SET kind=?2, status=?3, cadence=?4, routine_id=?5, url=?6, token_sealed=?7, key_ref=?8, setup_id=?9,
           setup_token=?10, setup_issued_at=?11, challenge=?12, updated_at=?14, last_ring_at=?15, last_research_at=?16, last_ok_at=?17,
           last_session_url=?18, failures=?19, last_error=?20, rings_day=?21, rings_today=?22, target_sealed=?23, settings_json=?24
         WHERE handle=?1 AND updated_at=?25`,
      ).bind(...values, expectUpdatedAt).run();
    return (res.meta?.changes ?? 0) > 0;
  }

  async getDoorbell(handle: string): Promise<DoorbellRecord | null> {
    const r = await this.db.prepare("SELECT * FROM doorbells WHERE handle = ?1").bind(handle).first<Record<string, unknown>>();
    return r ? rowToDoorbell(r) : null;
  }

  async getDoorbellBySetup(setupId: string): Promise<DoorbellRecord | null> {
    const r = await this.db.prepare("SELECT * FROM doorbells WHERE setup_id = ?1").bind(setupId).first<Record<string, unknown>>();
    return r ? rowToDoorbell(r) : null;
  }

  async listDoorbells(limit: number): Promise<DoorbellRecord[]> {
    const rs = await this.db.prepare("SELECT * FROM doorbells ORDER BY handle LIMIT ?1").bind(limit).all<Record<string, unknown>>();
    return (rs.results ?? []).map(rowToDoorbell);
  }

  async recordDoorbellRing(handle: string, expectUpdatedAt: string, r: DoorbellRing): Promise<boolean> {
    const res = await this.db
      .prepare(
        `UPDATE doorbells SET updated_at=?3, last_ring_at=?3, last_ok_at=CASE WHEN ?4 = 1 THEN ?3 ELSE last_ok_at END,
           last_research_at=COALESCE(?5, last_research_at), last_session_url=COALESCE(?6, last_session_url),
           failures=?7, last_error=?8, rings_day=?9, rings_today=?10, status=CASE WHEN ?11 = 1 THEN 'paused' ELSE status END
         WHERE handle=?1 AND updated_at=?2 AND status='active'`,
      )
      .bind(handle, expectUpdatedAt, r.at, r.ok ? 1 : 0, r.research ?? null, r.sessionUrl ?? null, r.failures, r.error,
        r.ringsDay, r.ringsToday, r.pause ? 1 : 0)
      .run();
    return (res.meta?.changes ?? 0) > 0;
  }

  async purgeRingClaims(beforeIso: string): Promise<number> {
    const res = await this.db.prepare("DELETE FROM jury_alert_sends WHERE kind LIKE 'ring:%' AND at < ?1").bind(beforeIso).run();
    return res.meta?.changes ?? 0;
  }

  async putOpsState(key: string, value: Json, at: string): Promise<void> {
    await this.db
      .prepare("INSERT INTO ops_state (key, value, at) VALUES (?1, ?2, ?3) ON CONFLICT(key) DO UPDATE SET value=?2, at=?3")
      .bind(key, JSON.stringify(value), at).run();
  }

  async getOpsState(key: string): Promise<{ value: Json; at: string } | null> {
    const r = await this.db.prepare("SELECT value, at FROM ops_state WHERE key = ?1").bind(key).first<{ value: string; at: string }>();
    return r ? { value: JSON.parse(r.value) as Json, at: r.at } : null;
  }

  async listLogFull(fromSeq: number, limit: number): Promise<Array<{ entry: LogEntry; entryHash: string; payload: Json }>> {
    const rs = await this.db
      .prepare("SELECT seq, ts, type, payload_hash, prev_hash, entry_hash, payload_json FROM log_entries WHERE seq >= ?1 ORDER BY seq LIMIT ?2")
      .bind(Math.max(0, fromSeq), limit)
      .all<{ seq: number; ts: string; type: string; payload_hash: string; prev_hash: string; entry_hash: string; payload_json: string }>();
    return (rs.results ?? []).map((r) => ({
      entry: { seq: r.seq, ts: r.ts, type: r.type as LogEntry["type"], payloadHash: r.payload_hash, prevHash: r.prev_hash },
      entryHash: r.entry_hash,
      payload: JSON.parse(r.payload_json) as Json,
    }));
  }

  async listLog(fromSeq: number, limit: number): Promise<LogRowView[]> {
    const rs = await this.db
      .prepare("SELECT seq, ts, type, payload_json FROM log_entries WHERE seq >= ?1 ORDER BY seq LIMIT ?2")
      .bind(Math.max(0, fromSeq), limit).all<{ seq: number; ts: string; type: string; payload_json: string }>();
    return (rs.results ?? []).map((r) => ({ seq: r.seq, ts: r.ts, type: r.type, payload: JSON.parse(r.payload_json) as Json }));
  }

  async bumpAccess(id: string): Promise<void> {
    await this.db
      .prepare(
        "INSERT INTO access_counts (id, count) VALUES (?1, 1) " +
        "ON CONFLICT(id) DO UPDATE SET count = count + 1",
      )
      .bind(id)
      .run();
  }

  async getAccess(id: string): Promise<number> {
    const row = await this.db
      .prepare("SELECT count FROM access_counts WHERE id = ?1")
      .bind(id)
      .first<{ count: number }>();
    return row?.count ?? 0;
  }

  async listAccessPrefix(prefix: string): Promise<Array<{ id: string; count: number }>> {
    // Range scan instead of LIKE: no wildcard semantics to escape, and the
    // primary-key index serves it. "￿" sorts after any id character.
    const rs = await this.db
      .prepare("SELECT id, count FROM access_counts WHERE id >= ?1 AND id < ?2 ORDER BY id LIMIT 500")
      .bind(prefix, prefix + "￿")
      .all<{ id: string; count: number }>();
    return rs.results ?? [];
  }
}

function rowToDoorbell(r: Record<string, unknown>): DoorbellRecord {
  const opt = (k: string) => (r[k] as string | null) ?? null;
  return {
    handle: r["handle"] as string,
    kind: r["kind"] as DoorbellRecord["kind"],
    status: r["status"] as DoorbellRecord["status"],
    cadence: r["cadence"] as DoorbellRecord["cadence"],
    routineId: opt("routine_id"),
    url: opt("url"),
    tokenSealed: opt("token_sealed"),
    keyRef: opt("key_ref"),
    setupId: r["setup_id"] as string,
    setupToken: r["setup_token"] as string,
    setupIssuedAt: r["setup_issued_at"] as string,
    challenge: opt("challenge"),
    createdAt: r["created_at"] as string,
    updatedAt: r["updated_at"] as string,
    lastRingAt: opt("last_ring_at"),
    lastResearchAt: opt("last_research_at"),
    lastOkAt: opt("last_ok_at"),
    lastSessionUrl: opt("last_session_url"),
    failures: Number(r["failures"] ?? 0),
    lastError: opt("last_error"),
    ringsDay: opt("rings_day"),
    ringsToday: Number(r["rings_today"] ?? 0),
    targetSealed: opt("target_sealed"),
    settings: settingsOf(r["settings_json"]),
  };
}

/** A doorbell's settings, from its column: anything unreadable reads as none (the page then asks again), never as a failure. */
function settingsOf(raw: unknown): DoorbellSettings {
  if (typeof raw !== "string" || !raw) return {};
  try {
    const v = JSON.parse(raw) as unknown;
    return v && typeof v === "object" && !Array.isArray(v) ? (v as DoorbellSettings) : {};
  } catch {
    return {};
  }
}
