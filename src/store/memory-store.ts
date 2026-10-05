/** In-memory Store: tests, local development, and auditor replays. */

import type { Json } from "../core/canonical.js";
import type { LogEntry } from "../core/log.js";
import type { DoorbellRecord, DoorbellRing, EmailKind, LogRowView, Store } from "./store.js";

interface LogRow {
  entry: LogEntry;
  entryHash: string;
  leafHash: string;
  payload: Json;
}

export class MemoryStore implements Store {
  private log: LogRow[] = [];

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
  /** Test-only: corrupt a stored entry to prove audits catch it. */
  _tamper(seq: number, mutate: (row: LogRow) => void): void {
    mutate(this.log[seq]!);
  }
  async listLog(fromSeq: number, limit: number): Promise<LogRowView[]> {
    return this.log.slice(Math.max(0, fromSeq), Math.max(0, fromSeq) + limit)
      .map((r) => ({ seq: r.entry.seq, ts: r.entry.ts, type: r.entry.type, payload: r.payload }));
  }
  async listLogFull(fromSeq: number, limit: number): Promise<Array<{ entry: LogEntry; entryHash: string; payload: Json }>> {
    return this.log.slice(Math.max(0, fromSeq), Math.max(0, fromSeq) + limit)
      .map((r) => ({ entry: { ...r.entry }, entryHash: r.entryHash, payload: structuredClone(r.payload) }));
  }

  // --- doorbells ---
  private doorbells = new Map<string, DoorbellRecord>();
  private alertSends = new Map<string, { kind: string; at: string }>();
  async putDoorbell(d: DoorbellRecord): Promise<void> {
    const clash = [...this.doorbells.values()].find((x) => x.setupId === d.setupId && x.handle !== d.handle);
    if (clash) throw new Error("UNIQUE constraint failed: doorbells.setup_id");
    this.doorbells.set(d.handle, structuredClone(d));
  }
  async putDoorbellIf(d: DoorbellRecord, expectUpdatedAt: string | null): Promise<boolean> {
    const cur = this.doorbells.get(d.handle);
    if (expectUpdatedAt === null ? !!cur : !cur || cur.updatedAt !== expectUpdatedAt) return false;
    await this.putDoorbell(d);
    return true;
  }
  async getDoorbell(handle: string): Promise<DoorbellRecord | null> {
    const d = this.doorbells.get(handle);
    return d ? structuredClone(d) : null;
  }
  async getDoorbellBySetup(setupId: string): Promise<DoorbellRecord | null> {
    const d = [...this.doorbells.values()].find((x) => x.setupId === setupId);
    return d ? structuredClone(d) : null;
  }
  async listDoorbells(limit: number): Promise<DoorbellRecord[]> {
    return [...this.doorbells.values()].sort((a, b) => a.handle.localeCompare(b.handle)).slice(0, limit).map((d) => structuredClone(d));
  }
  async recordDoorbellRing(handle: string, expectUpdatedAt: string, r: DoorbellRing): Promise<boolean> {
    const d = this.doorbells.get(handle);
    if (!d || d.status !== "active" || d.updatedAt !== expectUpdatedAt) return false;
    d.updatedAt = r.at;
    d.lastRingAt = r.at;
    if (r.ok) d.lastOkAt = r.at;
    if (r.research) d.lastResearchAt = r.research;
    if (r.sessionUrl) d.lastSessionUrl = r.sessionUrl;
    d.failures = r.failures;
    d.lastError = r.error;
    d.ringsDay = r.ringsDay;
    d.ringsToday = r.ringsToday;
    if (r.pause) d.status = "paused";
    return true;
  }
  async purgeRingClaims(beforeIso: string): Promise<number> {
    let n = 0;
    for (const [k, v] of this.alertSends) {
      if (v.kind.startsWith("ring:") && v.at < beforeIso) {
        this.alertSends.delete(k);
        n += 1;
      }
    }
    return n;
  }
  async claimAlertSend(handle: string, subject: string, kind: string, at: string): Promise<boolean> {
    const k = `${handle}|${subject}|${kind}`;
    if (this.alertSends.has(k)) return false;
    this.alertSends.set(k, { kind, at });
    return true;
  }
  async releaseAlertSend(handle: string, subject: string, kind: string): Promise<void> {
    this.alertSends.delete(`${handle}|${subject}|${kind}`);
  }

  // --- the email ledger ---
  private sends: Array<{ at: string; kind: string }> = [];
  async recordEmailSend(at: string, kind: EmailKind): Promise<void> {
    this.sends.push({ at, kind });
  }
  async countEmailSends(sinceIso: string, kind?: string): Promise<number> {
    return this.sends.filter((s) => s.at >= sinceIso && (!kind || s.kind === kind)).length;
  }

  // --- operational state and counters ---
  private opsState = new Map<string, { value: Json; at: string }>();
  async putOpsState(key: string, value: Json, at: string): Promise<void> {
    this.opsState.set(key, { value: structuredClone(value), at });
  }
  async getOpsState(key: string): Promise<{ value: Json; at: string } | null> {
    const v = this.opsState.get(key);
    return v ? structuredClone(v) : null;
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
}
