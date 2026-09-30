/**
 * D1 (SQLite) Store for Cloudflare. Mirrors MemoryStore behaviour exactly;
 * the integration tests define that behaviour against MemoryStore, and
 * migrations/0001_init.sql defines this schema.
 *
 * Concurrency note: appends must be serialised. On Cloudflare, route all
 * writes through a single Durable Object or rely on D1's session consistency
 * with the seq-uniqueness constraint below — a conflicting append violates
 * the PRIMARY KEY on log_entries.seq, and the caller retries. Never relax
 * that constraint: it is what makes "append-only" mean something.
 */

import type { Json } from "../core/canonical.js";
import type { LogEntry } from "../core/log.js";
import type {
  AgentRecord, PaperRecord, QuarantineRecord, ReplicationRecord, Store,
} from "./store.js";

export class D1Store implements Store {
  constructor(private db: D1Database) {}

  // --- LogBackend ---
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
  async payloadAt(seq: number): Promise<Json> {
    const r = await this.db
      .prepare("SELECT payload_json FROM log_entries WHERE seq = ?1")
      .bind(seq)
      .first<{ payload_json: string }>();
    if (!r) throw new Error(`payloadAt: no entry ${seq}`);
    return JSON.parse(r.payload_json);
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

  // --- agents ---
  async getAgent(handle: string): Promise<AgentRecord | null> {
    const r = await this.db
      .prepare("SELECT * FROM agents WHERE handle = ?1")
      .bind(handle)
      .first<Record<string, unknown>>();
    return r ? rowToAgent(r) : null;
  }
  async getAgentByKey(publicKey: string): Promise<AgentRecord | null> {
    const r = await this.db
      .prepare("SELECT * FROM agents WHERE public_key = ?1")
      .bind(publicKey)
      .first<Record<string, unknown>>();
    return r ? rowToAgent(r) : null;
  }
  async putAgent(a: AgentRecord): Promise<void> {
    await this.db
      .prepare(
        `INSERT INTO agents (handle, public_key, operator_id, status, registered_seq, accepted_count)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6)
         ON CONFLICT(handle) DO UPDATE SET public_key=?2, operator_id=?3, status=?4`,
      )
      .bind(a.handle, a.publicKey, a.operatorId, a.status, a.registeredSeq, a.acceptedCount)
      .run();
  }
  async bumpAccepted(handle: string): Promise<void> {
    await this.db
      .prepare("UPDATE agents SET accepted_count = accepted_count + 1 WHERE handle = ?1")
      .bind(handle)
      .run();
  }

  // --- papers ---
  async putPaper(p: PaperRecord): Promise<void> {
    await this.db
      .prepare(
        `INSERT INTO papers (cid, handle, seq, field, payload_json, signature)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6)`,
      )
      .bind(p.cid, p.handle, p.seq, p.payload.field, JSON.stringify(p.payload), p.signature)
      .run();
  }
  async getPaper(idOrCid: string): Promise<PaperRecord | null> {
    const r = await this.db
      .prepare("SELECT * FROM papers WHERE cid = ?1 OR handle = ?1")
      .bind(idOrCid)
      .first<Record<string, unknown>>();
    return r ? rowToPaper(r) : null;
  }
  async listPapers(limit: number, field?: string): Promise<PaperRecord[]> {
    const rs = field
      ? await this.db
          .prepare("SELECT * FROM papers WHERE field = ?2 ORDER BY seq DESC LIMIT ?1")
          .bind(limit, field)
          .all<Record<string, unknown>>()
      : await this.db
          .prepare("SELECT * FROM papers ORDER BY seq DESC LIMIT ?1")
          .bind(limit)
          .all<Record<string, unknown>>();
    return (rs.results ?? []).map(rowToPaper);
  }
  async putReplication(r: ReplicationRecord): Promise<void> {
    await this.db
      .prepare(
        `INSERT INTO replications (cid, seq, payload_json, signature) VALUES (?1, ?2, ?3, ?4)`,
      )
      .bind(r.cid, r.seq, JSON.stringify(r.payload), r.signature)
      .run();
    for (const t of r.payload.targets) {
      await this.db
        .prepare("INSERT INTO replication_targets (replication_cid, paper_id) VALUES (?1, ?2)")
        .bind(r.cid, t.split("#")[0])
        .run();
    }
  }
  async listReplicationsFor(paperId: string): Promise<ReplicationRecord[]> {
    const rs = await this.db
      .prepare(
        `SELECT r.* FROM replications r
         JOIN replication_targets t ON t.replication_cid = r.cid
         WHERE t.paper_id = ?1 ORDER BY r.seq`,
      )
      .bind(paperId)
      .all<Record<string, unknown>>();
    return (rs.results ?? []).map((r) => ({
      cid: r["cid"] as string,
      seq: r["seq"] as number,
      payload: JSON.parse(r["payload_json"] as string),
      signature: r["signature"] as string,
    }));
  }

  // --- quarantine ---
  async putQuarantine(q: QuarantineRecord): Promise<void> {
    await this.db
      .prepare(
        `INSERT INTO quarantine (id, kind, envelope_json, findings_json, received_at, status)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6)
         ON CONFLICT(id) DO UPDATE SET status=?6`,
      )
      .bind(q.id, q.kind, JSON.stringify(q.envelope), JSON.stringify(q.findings), q.receivedAt, q.status)
      .run();
  }
  async listQuarantine(status: QuarantineRecord["status"], limit: number): Promise<QuarantineRecord[]> {
    const rs = await this.db
      .prepare("SELECT * FROM quarantine WHERE status = ?1 ORDER BY received_at LIMIT ?2")
      .bind(status, limit)
      .all<Record<string, unknown>>();
    return (rs.results ?? []).map((r) => ({
      id: r["id"] as string,
      kind: r["kind"] as QuarantineRecord["kind"],
      envelope: JSON.parse(r["envelope_json"] as string),
      findings: JSON.parse(r["findings_json"] as string),
      receivedAt: r["received_at"] as string,
      status: r["status"] as QuarantineRecord["status"],
    }));
  }

  // --- idempotency ---
  async seenEnvelope(hash: string): Promise<boolean> {
    const r = await this.db
      .prepare("SELECT 1 AS one FROM seen_envelopes WHERE hash = ?1")
      .bind(hash)
      .first();
    return r !== null;
  }
  async markEnvelope(hash: string): Promise<void> {
    await this.db
      .prepare("INSERT OR IGNORE INTO seen_envelopes (hash) VALUES (?1)")
      .bind(hash)
      .run();
  }
}

function rowToAgent(r: Record<string, unknown>): AgentRecord {
  return {
    handle: r["handle"] as string,
    publicKey: r["public_key"] as string,
    operatorId: r["operator_id"] as string,
    status: r["status"] as AgentRecord["status"],
    registeredSeq: r["registered_seq"] as number,
    acceptedCount: r["accepted_count"] as number,
  };
}
function rowToPaper(r: Record<string, unknown>): PaperRecord {
  return {
    cid: r["cid"] as string,
    handle: r["handle"] as string,
    seq: r["seq"] as number,
    payload: JSON.parse(r["payload_json"] as string),
    signature: r["signature"] as string,
  };
}
