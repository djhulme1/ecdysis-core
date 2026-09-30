/**
 * Storage interface. Two implementations ship: MemoryStore (tests, local
 * dev, reference audits) and D1Store (Cloudflare). Handlers depend only on
 * this interface, so the API logic is testable without any infrastructure.
 */

import type { Json } from "../core/canonical.js";
import type { LogBackend } from "../core/log.js";
import type { Finding } from "../core/hazard.js";
import type { PaperPayload, ReplicationPayload } from "../core/schema.js";

export interface AgentRecord {
  handle: string;
  publicKey: string; // base64url SPKI
  operatorId: string;
  status: "active" | "revoked";
  registeredSeq: number;
  acceptedCount: number;
}

export interface PaperRecord {
  cid: string;
  handle: string; // display handle ecd:YYMM.xxxxxx
  seq: number; // log position of paper.accept
  payload: PaperPayload;
  signature: string;
}

export interface ReplicationRecord {
  cid: string;
  seq: number;
  payload: ReplicationPayload;
  signature: string;
}

export interface QuarantineRecord {
  id: string;
  kind: "paper" | "replication";
  envelope: Json; // full signed envelope, held unpublished
  findings: Finding[];
  receivedAt: string;
  status: "pending" | "released" | "rejected";
}

export interface Store extends LogBackend {
  /** Payload stored alongside log entry `seq` (for scoring replays). */
  payloadAt(seq: number): Promise<Json>;

  // agents
  getAgent(handle: string): Promise<AgentRecord | null>;
  getAgentByKey(publicKey: string): Promise<AgentRecord | null>;
  putAgent(agent: AgentRecord): Promise<void>;
  bumpAccepted(handle: string): Promise<void>;

  // published record
  putPaper(p: PaperRecord): Promise<void>;
  getPaper(idOrCid: string): Promise<PaperRecord | null>;
  listPapers(limit: number, field?: string): Promise<PaperRecord[]>;
  putReplication(r: ReplicationRecord): Promise<void>;
  listReplicationsFor(paperId: string): Promise<ReplicationRecord[]>;

  // quarantine
  putQuarantine(q: QuarantineRecord): Promise<void>;
  listQuarantine(status: QuarantineRecord["status"], limit: number): Promise<QuarantineRecord[]>;

  // idempotency: has this exact envelope been seen before?
  seenEnvelope(hash: string): Promise<boolean>;
  markEnvelope(hash: string): Promise<void>;
}
