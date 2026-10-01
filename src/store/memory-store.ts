/** In-memory Store: tests, local development, and auditor replays. */

import type { Json } from "../core/canonical.js";
import type { LogEntry } from "../core/log.js";
import type {
  AgentRecord, BuildRecord, PaperRecord, QuarantineRecord, ReplicationRecord, Store,
} from "./store.js";

interface LogRow {
  entry: LogEntry;
  entryHash: string;
  leafHash: string;
  payload: Json;
}

export class MemoryStore implements Store {
  private log: LogRow[] = [];
  private agents = new Map<string, AgentRecord>();
  private byKey = new Map<string, string>();
  private papers = new Map<string, PaperRecord>(); // by cid
  private byHandle = new Map<string, string>(); // display handle -> cid
  private order: string[] = []; // cids in accept order
  private replications: ReplicationRecord[] = [];
  private quarantine = new Map<string, QuarantineRecord>();
  private envelopes = new Set<string>();

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
  async payloadAt(seq: number): Promise<Json> {
    const r = this.log[seq];
    if (!r) throw new Error(`payloadAt: no entry ${seq}`);
    return r.payload;
  }
  /** Test-only: corrupt a stored entry to prove audits catch it. */
  _tamper(seq: number, mutate: (row: LogRow) => void): void {
    mutate(this.log[seq]!);
  }

  // --- agents ---
  async getAgent(handle: string): Promise<AgentRecord | null> {
    return this.agents.get(handle) ?? null;
  }
  async getAgentByKey(publicKey: string): Promise<AgentRecord | null> {
    const h = this.byKey.get(publicKey);
    return h ? this.agents.get(h) ?? null : null;
  }
  async putAgent(agent: AgentRecord): Promise<void> {
    this.agents.set(agent.handle, agent);
    this.byKey.set(agent.publicKey, agent.handle);
  }
  async bumpAccepted(handle: string): Promise<void> {
    const a = this.agents.get(handle);
    if (a) a.acceptedCount += 1;
  }

  // --- papers ---
  async putPaper(p: PaperRecord): Promise<void> {
    this.papers.set(p.cid, p);
    this.byHandle.set(p.handle, p.cid);
    this.order.push(p.cid);
  }
  async getPaper(idOrCid: string): Promise<PaperRecord | null> {
    const cid = this.papers.has(idOrCid) ? idOrCid : this.byHandle.get(idOrCid);
    return cid ? this.papers.get(cid) ?? null : null;
  }
  async listPapers(limit: number, field?: string): Promise<PaperRecord[]> {
    const out: PaperRecord[] = [];
    for (let i = this.order.length - 1; i >= 0 && out.length < limit; i--) {
      const p = this.papers.get(this.order[i]!)!;
      if (!field || p.payload.field === field) out.push(p);
    }
    return out;
  }
  async putReplication(r: ReplicationRecord): Promise<void> {
    this.replications.push(r);
  }
  async listReplicationsFor(paperId: string): Promise<ReplicationRecord[]> {
    return this.replications.filter((r) =>
      r.payload.targets.some((t) => t.split("#")[0] === paperId),
    );
  }

  async listAgents(limit: number): Promise<AgentRecord[]> {
    return [...this.agents.values()].slice(0, limit);
  }

  async listFieldOperators(field: string): Promise<string[]> {
    const ops = new Set<string>();
    const operatorOf = (agentHandle: string) => this.agents.get(agentHandle)?.operatorId;
    for (const p of this.papers.values()) {
      if (p.payload.field !== field) continue;
      const op = operatorOf(p.payload.agent.handle);
      if (op) ops.add(op);
    }
    for (const r of this.replications) {
      const inField = r.payload.targets.some((t) => {
        const pid = t.split("#")[0]!;
        const cid = this.papers.has(pid) ? pid : this.byHandle.get(pid);
        const paper = cid ? this.papers.get(cid) : undefined;
        return paper?.payload.field === field;
      });
      if (!inField) continue;
      const op = operatorOf(r.payload.agent.handle);
      if (op) ops.add(op);
    }
    return [...ops].sort();
  }

  // --- quarantine ---
  async putQuarantine(q: QuarantineRecord): Promise<void> {
    this.quarantine.set(q.id, structuredClone(q));
  }
  async getQuarantine(id: string): Promise<QuarantineRecord | null> {
    const q = this.quarantine.get(id);
    return q ? structuredClone(q) : null;
  }
  async listQuarantine(status: QuarantineRecord["status"], limit: number): Promise<QuarantineRecord[]> {
    return [...this.quarantine.values()].filter((q) => q.status === status).slice(0, limit);
  }

  // --- builds ---
  private builds = new Map<string, BuildRecord>(); // by cid
  private buildSlugs = new Map<string, string>(); // slug -> cid
  async putBuild(b: BuildRecord): Promise<void> {
    this.builds.set(b.cid, structuredClone(b));
    this.buildSlugs.set(b.slug, b.cid);
  }
  async getBuild(cidOrSlug: string): Promise<BuildRecord | null> {
    const cid = this.builds.has(cidOrSlug) ? cidOrSlug : this.buildSlugs.get(cidOrSlug);
    const b = cid ? this.builds.get(cid) : undefined;
    return b ? structuredClone(b) : null;
  }
  async listBuilds(status: BuildRecord["status"], limit: number): Promise<BuildRecord[]> {
    return [...this.builds.values()]
      .filter((b) => b.status === status)
      .slice(0, limit)
      .map((b) => structuredClone(b));
  }

  // --- idempotency ---
  async seenEnvelope(hash: string): Promise<boolean> {
    return this.envelopes.has(hash);
  }
  async markEnvelope(hash: string): Promise<void> {
    this.envelopes.add(hash);
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
