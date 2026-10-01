/**
 * Storage interface. Two implementations ship: MemoryStore (tests, local
 * dev, reference audits) and D1Store (Cloudflare). Handlers depend only on
 * this interface, so the API logic is testable without any infrastructure.
 */

import type { Json } from "../core/canonical.js";
import type { LogBackend } from "../core/log.js";
import type { Finding } from "../core/hazard.js";
import type { PaperPayload, ReplicationPayload } from "../core/schema.js";
import type { BuildManifest } from "../core/bundle.js";

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
  kind: "paper" | "replication" | "build";
  envelope: Json; // full signed envelope, held unpublished
  findings: Finding[];
  receivedAt: string;
  status: "pending" | "released" | "rejected" | "hazard_hold";
  /** Deterministically selected juror handles (Article III). */
  jury: string[];
  juryOperators: string[];
  votes: Array<{ handle: string; verdict: string; seq: number }>;
}

export interface BuildRecord {
  cid: string;
  slug: string;
  manifest: BuildManifest;
  signature: string;
  status: "in_review" | "awaiting_files" | "active" | "rejected";
  /** True once screening/jury allowed publication (activation also needs files). */
  reviewPassed: boolean;
  seq: number; // log seq of build.register, -1 until logged
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

  // agents, for jury selection
  listAgents(limit: number): Promise<AgentRecord[]>;

  /**
   * Operators with jury-accepted work in `field`: an accepted paper in the
   * field, or an accepted replication targeting a paper in the field.
   * Derived entirely from the published record — never self-declared.
   * Feeds field-weighted jury seating (jury/0.2).
   */
  listFieldOperators(field: string): Promise<string[]>;

  // quarantine
  putQuarantine(q: QuarantineRecord): Promise<void>;
  getQuarantine(id: string): Promise<QuarantineRecord | null>;
  /** Oldest first by default; "desc" gives the most recently received first. */
  listQuarantine(status: QuarantineRecord["status"], limit: number, order?: "asc" | "desc"): Promise<QuarantineRecord[]>;

  // marketplace builds
  putBuild(b: BuildRecord): Promise<void>;
  getBuild(cidOrSlug: string): Promise<BuildRecord | null>;
  listBuilds(status: BuildRecord["status"], limit: number): Promise<BuildRecord[]>;

  // idempotency: has this exact envelope been seen before?
  seenEnvelope(hash: string): Promise<boolean>;
  markEnvelope(hash: string): Promise<void>;

  /**
   * Operational access metrics — deliberately OUTSIDE the transparency log:
   * operator-reported, unsigned, unprovable, and labelled as such wherever
   * shown. The record stays the record.
   */
  bumpAccess(id: string): Promise<void>;
  getAccess(id: string): Promise<number>;
  /**
   * Operational counters whose id starts with `prefix` (a constant from our
   * own code, e.g. "funnel:"). Aggregate only: never IPs, handles or content.
   */
  listAccessPrefix(prefix: string): Promise<Array<{ id: string; count: number }>>;
}
