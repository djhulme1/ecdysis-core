/**
 * The transparency log, read over HTTP and the connector: the signed tree
 * head, inclusion and consistency proofs, the entries themselves with their
 * payloads, and a full audit. Anyone can check every number on the site
 * against these offline with the log's public key (Article 0.4); nothing
 * here needs trust in this server.
 */

import type { Json } from "../../core/canonical.js";
import type { LogEntry, SignedTreeHead, TransparencyLog } from "../../core/log.js";
import type { ApiResult } from "./service.js";

/** What the log's storage serves besides the tree: one entry, or a run of entries with their payloads. */
export interface LogReader {
  getEntry(seq: number): Promise<{ entry: LogEntry; entryHash: string } | null>;
  listLogFull(fromSeq: number, limit: number): Promise<Array<{ entry: LogEntry; entryHash: string; payload: Json }>>;
}

export interface LogApiOptions {
  log: TransparencyLog;
  reader: LogReader;
  /** The log key (base64url PKCS#8): heads are signed with it; without it they are served unsigned and say so by having no signature. */
  signingKey: string | null;
  /** A frozen record's final head, served verbatim instead of a fresh one (the deployment is read-only and needs no key). */
  finalSth?: SignedTreeHead | null;
  now?: () => Date;
}

export const LOG_ENTRIES_VERSION = "log-entries/0.2";

const ok = (status: number, body: Json): ApiResult => ({ status, body });
const err = (status: number, error: string): ApiResult => ({ status, body: { error } });

export class LogApi {
  private now: () => Date;
  constructor(private o: LogApiOptions) {
    this.now = o.now ?? (() => new Date());
  }

  /** The current head: signed with the log key, or the frozen final head, or unsigned when no key is installed. */
  async sth(): Promise<SignedTreeHead | { treeSize: number; rootHash: string; timestamp: string }> {
    if (this.o.finalSth) return this.o.finalSth;
    if (this.o.signingKey) return this.o.log.signedTreeHead(this.o.signingKey);
    const treeSize = await this.o.log.size();
    return { treeSize, rootHash: await this.o.log.root(treeSize), timestamp: this.now().toISOString() };
  }

  async sthResult(): Promise<ApiResult> {
    return ok(200, (await this.sth()) as unknown as Json);
  }

  async size(): Promise<number> {
    return this.o.log.size();
  }

  async inclusion(seq: number, treeSize?: number): Promise<ApiResult> {
    try {
      const { proof, treeSize: n } = await this.o.log.proveInclusion(seq, treeSize);
      const row = await this.o.reader.getEntry(seq);
      if (!row) return err(400, "seq out of range for that tree size");
      return ok(200, { seq, treeSize: n, proof, entry: row.entry as unknown as Json, rootHash: await this.o.log.root(n) });
    } catch {
      return err(400, "seq out of range for that tree size");
    }
  }

  async consistency(first: number, second: number): Promise<ApiResult> {
    const n = await this.o.log.size();
    if (!(Number.isInteger(first) && Number.isInteger(second)) || first < 0 || second > n || first > second) {
      return err(400, "need 0 <= first <= second <= current tree size");
    }
    return ok(200, {
      first, second,
      firstRoot: await this.o.log.root(first),
      secondRoot: await this.o.log.root(second),
      proof: await this.o.log.proveConsistency(first, second),
    });
  }

  /** The whole chain re-walked, every hash recomputed, the root confirmed: 200 when intact, 500 with the first problem. */
  async audit(): Promise<ApiResult> {
    const problem = await this.o.log.audit();
    return ok(problem ? 500 : 200, { intact: problem === null, problem });
  }

  /**
   * The log itself, payloads included, so anyone can recompute every number and verify every hash (Article 0.4). `redact`
   * lets the caller blank the words of an item a steward has taken out of view; the payload hash still commits to them.
   */
  async entries(from: number, limit: number, redact: (type: string, payload: Json) => Json = (_t, p) => p): Promise<ApiResult> {
    const size = await this.o.log.size();
    const start = Number.isInteger(from) && from >= 0 ? from : 0;
    const n = Math.min(Math.max(Number.isInteger(limit) ? limit : 100, 1), 200);
    const rows = start < size ? await this.o.reader.listLogFull(start, n) : [];
    const entries = rows.map((r) => ({
      seq: r.entry.seq, ts: r.entry.ts, type: r.entry.type,
      payloadHash: r.entry.payloadHash, prevHash: r.entry.prevHash, entryHash: r.entryHash,
      payload: redact(r.entry.type, r.payload),
    }));
    const next = start + entries.length < size && entries.length > 0 ? start + entries.length : null;
    return ok(200, {
      version: LOG_ENTRIES_VERSION,
      treeSize: size, from: start, count: entries.length, next,
      verify: "For each entry: payloadHash = sha256 of the canonical JSON of payload (unless its words are withheld); entryHash = sha256 of the canonical JSON of {seq, ts, type, payloadHash, prevHash}; prevHash = the previous entry's entryHash (64 zeros for seq 0); the Merkle root over leaf hashes sha256(0x00 || canonical entry) matches the signed tree head (GET /v2/log/sth). npm run recompute:v2 does all of it, then recomputes every claim's numbers.",
      entries: entries as unknown as Json,
    });
  }
}
