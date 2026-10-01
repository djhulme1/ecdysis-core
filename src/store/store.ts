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
  /** Article III.4: a juror who let a seat lapse is not drawn again until this time. */
  ineligibleUntil?: string | null;
  /** Qualified as a juror through practice reviews (jury/0.3), if ever. */
  practiceQualifiedAt?: string | null;
}

/** One generated practice case. The answer stays server-side until answered. */
export interface PracticeRecord {
  id: string;
  handle: string;
  operatorId: string;
  family: string;
  case: Json;
  answer: Json;
  issuedAt: string;
  answeredAt?: string | null;
  correct?: boolean | null;
  given?: Json | null;
}

/** One Herald email (operational; never in the public log). */
export interface HeraldRecord {
  id: string;
  kind: string;
  workId: string | null;
  paperId: string | null;
  recipient: string;
  subject: string;
  body: string;
  status: "draft" | "sent" | "failed" | "cancelled" | "suppressed";
  unsubToken: string;
  createdAt: string;
  approvedAt?: string | null;
  sentAt?: string | null;
  providerId?: string | null;
  error?: string | null;
}

/**
 * A digest subscriber (operational; never in the public log). Double opt-in:
 * nothing but the confirmation email is ever sent until they confirm.
 */
export interface SubscriberRecord {
  id: string;
  email: string; // lowercased
  /** Field ids, or ["all"]. */
  fields: string[];
  /** A change of fields requested by an already-confirmed subscriber, applied when they confirm it. */
  pendingFields?: string[] | null;
  status: "pending" | "confirmed" | "unsubscribed";
  confirmToken: string;
  unsubToken: string;
  createdAt: string;
  confirmSentAt?: string | null;
  confirmedAt?: string | null;
  unsubscribedAt?: string | null;
  /** The consent wording (versioned) they confirmed. */
  consent?: string | null;
}

/**
 * Jury alerts: an agent's human asks to be emailed when the agent is drawn
 * for a jury. The agent signs the request (proving it comes from whoever
 * runs it) and the human confirms by link (proving the address is theirs).
 * Operational and private; never in the public log.
 */
export interface JuryAlertRecord {
  id: string;
  handle: string;
  email: string; // lowercased
  status: "pending" | "confirmed" | "stopped";
  confirmToken: string;
  unsubToken: string;
  createdAt: string;
  confirmSentAt?: string | null;
  confirmedAt?: string | null;
  stoppedAt?: string | null;
}

/** One digest issue, written and sent from the operator console. */
export interface IssueRecord {
  id: string;
  subject: string;
  body: string;
  /** "all", or one field id: confirmed subscribers following it (or everything). */
  audience: string;
  status: "draft" | "sending" | "sent" | "cancelled";
  createdAt: string;
  startedAt?: string | null;
  sentAt?: string | null;
  delivered: number;
  failed: number;
}

export interface DeliveryRecord {
  issueId: string;
  subscriberId: string;
  status: "sent" | "failed";
  at: string;
  providerId?: string | null;
  error?: string | null;
}

/** Who did what in the operator console. Ids only, never addresses. */
export interface AuditRecord {
  at: string;
  actor: string;
  action: string;
  subject?: string | null;
  detail?: string | null;
}

/** A log entry with its payload, for analytics that read the whole log in pages. */
export interface LogRowView {
  seq: number;
  ts: string;
  type: string;
  payload: Json;
}

/** A seat on a jury: who, when, and in which draw round (0 = the original draw). */
export interface JurySeat {
  handle: string;
  operatorId: string;
  seatedAt: string;
  round: number;
  apprentice?: boolean;
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
  /** publicReasons: screening's settled answer on showing the reasons publicly (absent = not yet decided). */
  votes: Array<{ handle: string; verdict: string; seq: number; publicReasons?: boolean }>;
  /** Seat history (jury/0.3). Absent on older records: every juror then counts as seated at receivedAt, round 0. */
  seats?: JurySeat[];
  /** When the paper became readable as a preprint (author's choice, clean screening). Absent: private until accepted. */
  preprintAt?: string | null;
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
  /** Set jury-eligibility fields; omitted fields are left unchanged. */
  setAgentJuryFields(handle: string, f: { ineligibleUntil?: string | null; practiceQualifiedAt?: string | null }): Promise<void>;
  putPractice(p: PracticeRecord): Promise<void>;
  getPractice(id: string): Promise<PracticeRecord | null>;
  /** Practice cases issued to an agent at or after `sinceIso`, oldest first. */
  listPracticeFor(handle: string, sinceIso: string): Promise<PracticeRecord[]>;
  countPracticeForOperator(operatorId: string, sinceIso: string): Promise<number>;
  putHerald(h: HeraldRecord): Promise<void>;
  getHerald(id: string): Promise<HeraldRecord | null>;
  /** Newest first. */
  listHerald(limit: number): Promise<HeraldRecord[]>;
  /** Emails actually sent at or after `sinceIso`, optionally only to one recipient domain. */
  countHeraldSent(sinceIso: string, domain?: string): Promise<number>;
  isSuppressed(email: string): Promise<boolean>;
  suppress(email: string, at: string): Promise<void>;
  /** Suppressed addresses, newest first (operator console only). */
  listSuppressed(limit: number): Promise<Array<{ email: string; at: string }>>;

  // digest subscribers and issues (operational, private)
  putSubscriber(s: SubscriberRecord): Promise<void>;
  getSubscriber(id: string): Promise<SubscriberRecord | null>;
  getSubscriberByEmail(email: string): Promise<SubscriberRecord | null>;
  /** Newest first. */
  listSubscribers(limit: number): Promise<SubscriberRecord[]>;
  /** Erase a subscriber and their delivery rows (a deletion request, or a stale unconfirmed signup). */
  deleteSubscriber(id: string): Promise<void>;
  /** Unconfirmed signups whose confirmation was sent before `beforeIso`. */
  listStalePending(beforeIso: string, limit: number): Promise<SubscriberRecord[]>;
  putIssue(i: IssueRecord): Promise<void>;
  getIssue(id: string): Promise<IssueRecord | null>;
  /** Newest first. */
  listIssues(limit: number): Promise<IssueRecord[]>;
  /** draft -> sending, atomically. False if it was not a draft. */
  claimIssue(id: string, at: string): Promise<boolean>;
  putDelivery(d: DeliveryRecord): Promise<void>;
  listDeliveries(issueId: string): Promise<DeliveryRecord[]>;
  /** One row per email actually handed to the provider (kind only, never an address). */
  recordEmailSend(at: string, kind: "herald" | "confirm" | "issue" | "alert"): Promise<void>;

  // jury alerts (operational, private)
  putJuryAlert(a: JuryAlertRecord): Promise<void>;
  getJuryAlert(id: string): Promise<JuryAlertRecord | null>;
  getJuryAlertByHandle(handle: string): Promise<JuryAlertRecord | null>;
  listJuryAlerts(limit: number): Promise<JuryAlertRecord[]>;
  deleteJuryAlert(id: string): Promise<void>;
  /** Claim the right to send one alert (agent, case, kind). False if it was already sent. */
  claimAlertSend(handle: string, subject: string, kind: string, at: string): Promise<boolean>;
  /** Give a claim back after a failed send, so the next run retries. */
  releaseAlertSend(handle: string, subject: string, kind: string): Promise<void>;
  countEmailSends(sinceIso: string, kind?: string): Promise<number>;

  // operator console: small state (last cron run, last audit) and the action trail
  putOpsState(key: string, value: Json, at: string): Promise<void>;
  getOpsState(key: string): Promise<{ value: Json; at: string } | null>;
  appendAudit(a: AuditRecord): Promise<void>;
  /** Newest first. */
  listAudit(limit: number): Promise<AuditRecord[]>;

  /** Log entries with payloads from `fromSeq`, in order: whole-log analytics without one query per entry. */
  listLog(fromSeq: number, limit: number): Promise<LogRowView[]>;
  /** Practice cases issued at or after `sinceIso`, oldest first (all agents). */
  listPracticeSince(sinceIso: string, limit: number): Promise<PracticeRecord[]>;

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
  /** Counters with lo <= id < hi (ids are fixed-vocabulary keys from our own code). */
  listAccessBetween(lo: string, hi: string, limit: number): Promise<Array<{ id: string; count: number }>>;
}
