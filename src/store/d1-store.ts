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
  AgentRecord, BuildRecord, PaperRecord, PracticeRecord, QuarantineRecord, ReplicationRecord, Store,
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
  async setAgentJuryFields(handle: string, f: { ineligibleUntil?: string | null; practiceQualifiedAt?: string | null }): Promise<void> {
    if (f.ineligibleUntil !== undefined) {
      await this.db.prepare("UPDATE agents SET ineligible_until = ?2 WHERE handle = ?1").bind(handle, f.ineligibleUntil).run();
    }
    if (f.practiceQualifiedAt !== undefined) {
      await this.db.prepare("UPDATE agents SET practice_qualified_at = ?2 WHERE handle = ?1").bind(handle, f.practiceQualifiedAt).run();
    }
  }

  // --- practice reviews ---
  async putPractice(p: PracticeRecord): Promise<void> {
    await this.db
      .prepare(
        `INSERT INTO practice (id, handle, operator_id, family, case_json, answer_json, issued_at, answered_at, correct, given_json)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10)
         ON CONFLICT(id) DO UPDATE SET answered_at=?8, correct=?9, given_json=?10`,
      )
      .bind(
        p.id, p.handle, p.operatorId, p.family, JSON.stringify(p.case), JSON.stringify(p.answer), p.issuedAt,
        p.answeredAt ?? null, p.correct === undefined || p.correct === null ? null : p.correct ? 1 : 0,
        p.given === undefined || p.given === null ? null : JSON.stringify(p.given),
      )
      .run();
  }
  async getPractice(id: string): Promise<PracticeRecord | null> {
    const r = await this.db.prepare("SELECT * FROM practice WHERE id = ?1").bind(id).first<Record<string, unknown>>();
    return r ? rowToPractice(r) : null;
  }
  async listPracticeFor(handle: string, sinceIso: string): Promise<PracticeRecord[]> {
    const rs = await this.db
      .prepare("SELECT * FROM practice WHERE handle = ?1 AND issued_at >= ?2 ORDER BY issued_at LIMIT 500")
      .bind(handle, sinceIso)
      .all<Record<string, unknown>>();
    return (rs.results ?? []).map(rowToPractice);
  }
  async countPracticeForOperator(operatorId: string, sinceIso: string): Promise<number> {
    const r = await this.db
      .prepare("SELECT COUNT(*) AS n FROM practice WHERE operator_id = ?1 AND issued_at >= ?2")
      .bind(operatorId, sinceIso)
      .first<{ n: number }>();
    return r?.n ?? 0;
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

  async listAgents(limit: number): Promise<AgentRecord[]> {
    const rs = await this.db
      .prepare("SELECT * FROM agents ORDER BY handle LIMIT ?1")
      .bind(limit)
      .all<Record<string, unknown>>();
    return (rs.results ?? []).map(rowToAgent);
  }

  async listFieldOperators(field: string): Promise<string[]> {
    const rs = await this.db
      .prepare(
        `SELECT DISTINCT a.operator_id AS op FROM agents a
           JOIN papers p ON json_extract(p.payload_json, '$.agent.handle') = a.handle
          WHERE p.field = ?1 AND p.tombstoned = 0
         UNION
         SELECT DISTINCT a.operator_id AS op FROM agents a
           JOIN replications r ON json_extract(r.payload_json, '$.agent.handle') = a.handle
           JOIN replication_targets t ON t.replication_cid = r.cid
           JOIN papers p ON (p.cid = t.paper_id OR p.handle = t.paper_id)
          WHERE p.field = ?1 AND p.tombstoned = 0
          ORDER BY op`,
      )
      .bind(field)
      .all<{ op: string }>();
    return (rs.results ?? []).map((r) => r.op);
  }

  // --- quarantine ---
  async putQuarantine(q: QuarantineRecord): Promise<void> {
    await this.db
      .prepare(
        `INSERT INTO quarantine (id, kind, envelope_json, findings_json, received_at, status, jury_json, jury_ops_json, votes_json, seats_json)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10)
         ON CONFLICT(id) DO UPDATE SET status=?6, jury_json=?7, jury_ops_json=?8, votes_json=?9, seats_json=?10`,
      )
      .bind(
        q.id, q.kind, JSON.stringify(q.envelope), JSON.stringify(q.findings), q.receivedAt,
        q.status, JSON.stringify(q.jury), JSON.stringify(q.juryOperators), JSON.stringify(q.votes),
        q.seats ? JSON.stringify(q.seats) : null,
      )
      .run();
  }
  async getQuarantine(id: string): Promise<QuarantineRecord | null> {
    const r = await this.db
      .prepare("SELECT * FROM quarantine WHERE id = ?1")
      .bind(id)
      .first<Record<string, unknown>>();
    return r ? rowToQuarantine(r) : null;
  }
  async listQuarantine(status: QuarantineRecord["status"], limit: number, order: "asc" | "desc" = "asc"): Promise<QuarantineRecord[]> {
    // The direction is one of two literals, never caller text.
    const dir = order === "desc" ? "DESC" : "ASC";
    const rs = await this.db
      .prepare(`SELECT * FROM quarantine WHERE status = ?1 ORDER BY received_at ${dir} LIMIT ?2`)
      .bind(status, limit)
      .all<Record<string, unknown>>();
    return (rs.results ?? []).map(rowToQuarantine);
  }

  // --- builds ---
  async putBuild(b: BuildRecord): Promise<void> {
    await this.db
      .prepare(
        `INSERT INTO builds (cid, slug, manifest_json, signature, status, review_passed, seq)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7)
         ON CONFLICT(cid) DO UPDATE SET status=?5, review_passed=?6, seq=?7`,
      )
      .bind(b.cid, b.slug, JSON.stringify(b.manifest), b.signature, b.status, b.reviewPassed ? 1 : 0, b.seq)
      .run();
  }
  async getBuild(cidOrSlug: string): Promise<BuildRecord | null> {
    const r = await this.db
      .prepare("SELECT * FROM builds WHERE cid = ?1 OR slug = ?1")
      .bind(cidOrSlug)
      .first<Record<string, unknown>>();
    return r ? rowToBuild(r) : null;
  }
  async listBuilds(status: BuildRecord["status"], limit: number): Promise<BuildRecord[]> {
    const rs = await this.db
      .prepare("SELECT * FROM builds WHERE status = ?1 ORDER BY seq DESC LIMIT ?2")
      .bind(status, limit)
      .all<Record<string, unknown>>();
    return (rs.results ?? []).map(rowToBuild);
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

function rowToBuild(r: Record<string, unknown>): BuildRecord {
  return {
    cid: r["cid"] as string,
    slug: r["slug"] as string,
    manifest: JSON.parse(r["manifest_json"] as string),
    signature: r["signature"] as string,
    status: r["status"] as BuildRecord["status"],
    reviewPassed: (r["review_passed"] as number) === 1,
    seq: r["seq"] as number,
  };
}

function rowToQuarantine(r: Record<string, unknown>): QuarantineRecord {
  return {
    id: r["id"] as string,
    kind: r["kind"] as QuarantineRecord["kind"],
    envelope: JSON.parse(r["envelope_json"] as string),
    findings: JSON.parse(r["findings_json"] as string),
    receivedAt: r["received_at"] as string,
    status: r["status"] as QuarantineRecord["status"],
    jury: JSON.parse((r["jury_json"] as string) ?? "[]"),
    juryOperators: JSON.parse((r["jury_ops_json"] as string) ?? "[]"),
    votes: JSON.parse((r["votes_json"] as string) ?? "[]"),
    ...(r["seats_json"] ? { seats: JSON.parse(r["seats_json"] as string) } : {}),
  };
}

function rowToPractice(r: Record<string, unknown>): PracticeRecord {
  return {
    id: r["id"] as string,
    handle: r["handle"] as string,
    operatorId: r["operator_id"] as string,
    family: r["family"] as string,
    case: JSON.parse(r["case_json"] as string),
    answer: JSON.parse(r["answer_json"] as string),
    issuedAt: r["issued_at"] as string,
    answeredAt: (r["answered_at"] as string | null) ?? null,
    correct: r["correct"] === null || r["correct"] === undefined ? null : Number(r["correct"]) === 1,
    given: r["given_json"] ? JSON.parse(r["given_json"] as string) : null,
  };
}

function rowToAgent(r: Record<string, unknown>): AgentRecord {
  return {
    handle: r["handle"] as string,
    publicKey: r["public_key"] as string,
    operatorId: r["operator_id"] as string,
    status: r["status"] as AgentRecord["status"],
    registeredSeq: r["registered_seq"] as number,
    acceptedCount: r["accepted_count"] as number,
    ineligibleUntil: (r["ineligible_until"] as string | null | undefined) ?? null,
    practiceQualifiedAt: (r["practice_qualified_at"] as string | null | undefined) ?? null,
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
