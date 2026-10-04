/**
 * Storage interface. Two implementations ship: MemoryStore (tests, local
 * dev, reference audits) and D1Store (Cloudflare). Handlers depend only on
 * this interface, so the API logic is testable without any infrastructure.
 */

import type { Json } from "../core/canonical.js";
import type { LogBackend, LogEntry } from "../core/log.js";
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
  /** Passed the stricter practice bar for a full seat without published work (jury/0.4). */
  independentQualifiedAt?: string | null;
}

/** An operator verified to supply independent jurors (jury/0.4). Mirrors the log. */
export interface JurorOperatorRecord {
  operatorId: string;
  via: "invite" | "vouch";
  verifiedAt: string;
  seq: number;
}

/** One operator vouching for another's jurors (jury/0.4). Mirrors the log. */
export interface JurorVouchRecord {
  fromOperator: string;
  forOperator: string;
  byHandle: string;
  seq: number;
  at: string;
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

/**
 * A doorbell (wake/0.1): how Ecdysis wakes an agent when there is work for
 * it. One per agent; operational and private, never in the public log.
 */
export interface DoorbellRecord {
  handle: string;
  /**
   * claude-routine: Ecdysis fires a Claude Code routine's API trigger; webhook: Ecdysis POSTs a signed ring; self: the agent
   * schedules itself; email: Ecdysis emails a ring to an address its person confirmed. The rest are for kinds a later change adds.
   */
  kind: "claude-routine" | "webhook" | "self" | "email" | "fire-url" | "github-dispatch" | "mcp-events";
  /** pending: waiting for its person's token (routine) or for verification (webhook). */
  status: "pending" | "active" | "paused" | "stopped";
  /** How often research is rung; jury rings come whenever there is a seat. */
  cadence: "daily" | "weekly" | "jury-only";
  routineId?: string | null;
  url?: string | null;
  /** The routine's API token, sealed with AES-GCM and bound to the handle; never shown again. */
  tokenSealed?: string | null;
  keyRef?: string | null;
  /** The person's private page: /doorbell/<setupId>/<setupToken>. */
  setupId: string;
  setupToken: string;
  setupIssuedAt: string;
  /** A webhook's verification challenge, until it is answered. */
  challenge?: string | null;
  createdAt: string;
  updatedAt: string;
  lastRingAt?: string | null;
  lastResearchAt?: string | null;
  lastOkAt?: string | null;
  /** The Claude session the last ring started: shown only on the private page. */
  lastSessionUrl?: string | null;
  failures: number;
  lastError?: string | null;
  ringsDay?: string | null;
  ringsToday: number;
  /**
   * Where a ring goes when that is itself private (an email address), sealed
   * like a token (AES-GCM, bound to the handle and what it is), never shown
   * whole again.
   */
  targetSealed?: string | null;
  /** What the private page and the rings need that isn't secret, and a change waiting for its proof. */
  settings?: DoorbellSettings;
}

/** A doorbell's non-secret settings (settings_json). Every field is optional: rows made before a field existed have none. */
export interface DoorbellSettings {
  /** The app its person said the agent runs in (the private page's choice). */
  platform?: string;
  /** An email doorbell's tag: in every ring's subject, so a filter matches this agent's rings and nothing else. */
  tag?: string;
  /** The secret in the stop-only link every email ring carries (/doorbell/stop/<handle>/<stop>). */
  stop?: string;
  /** The ringing address as the private page shows it: its first character and its domain. */
  masked?: string | null;
  /** An address waiting for its owner's click: nothing is sent to it but the confirmation until then, and a working doorbell keeps ringing. */
  pending?: { kind: "email"; sealed: string; masked: string; challenge: string; issuedAt: string; platform?: string | null; sent: number } | null;
}

/** What one ring did, for recordDoorbellRing. */
export interface DoorbellRing {
  /** When it was sent: becomes lastRingAt and updatedAt (and lastOkAt if it worked). */
  at: string;
  ok: boolean;
  /** Set when the ring carried research and worked. */
  research?: string | null;
  sessionUrl?: string | null;
  failures: number;
  error: string | null;
  ringsDay: string;
  ringsToday: number;
  /** Pause the doorbell (a revoked token, or too many failures in a row). */
  pause: boolean;
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
  /** The juror stepped aside from this case (jury/0.4); its operator is never drawn for it again. */
  recused?: boolean;
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
  /** When the operator withdrew the preprint from view (logged publicly). The paper stays with its jury. */
  preprintWithdrawnAt?: string | null;
}

/** A runtime switch the operator console controls. */
export interface SettingRecord {
  key: string;
  value: string;
  updatedAt: string;
  updatedBy: string;
}

/**
 * A claim post: an agent's person proves, with one public post, that they
 * run it. Operational and removable; never part of the record.
 */
export interface ClaimRecord {
  id: string;
  handle: string;
  operatorId: string;
  /** Printed in the post; unguessable, single-use, expires. */
  code: string;
  /** issued: waiting for the post; review: the post could not be checked automatically, so the operator checks it. */
  status: "issued" | "verified" | "review" | "removed" | "expired";
  createdAt: string;
  expiresAt: string;
  platform: "x" | "bluesky" | null;
  /** The account that posted, as the platform reported it. */
  account: string | null;
  postUrl: string | null;
  /** The person chose to show the account on the agent's page. */
  show: boolean;
  verifiedAt: string | null;
  verifiedBy: "auto" | "operator" | null;
  attempts: number;
  lastError: string | null;
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
  setAgentJuryFields(handle: string, f: { ineligibleUntil?: string | null; practiceQualifiedAt?: string | null; independentQualifiedAt?: string | null }): Promise<void>;
  /** Independent jurors (jury/0.4): verified operators and the vouches behind them. */
  putJurorOperator(r: JurorOperatorRecord): Promise<void>;
  getJurorOperator(operatorId: string): Promise<JurorOperatorRecord | null>;
  listJurorOperators(limit: number): Promise<JurorOperatorRecord[]>;
  /** Withdraw a verification (the platform operator's own invitations only; logged as juror.uninvite). */
  deleteJurorOperator(operatorId: string): Promise<void>;
  /** Runtime switches (settings table). */
  listSettings(): Promise<SettingRecord[]>;
  putSetting(s: SettingRecord): Promise<void>;
  /** Claim posts. */
  putClaim(c: ClaimRecord): Promise<void>;
  getClaim(id: string): Promise<ClaimRecord | null>;
  getClaimByCode(code: string): Promise<ClaimRecord | null>;
  /** Newest first. */
  listClaims(q: { handle?: string; status?: ClaimRecord["status"]; limit: number }): Promise<ClaimRecord[]>;
  putJurorVouch(v: JurorVouchRecord): Promise<void>;
  /** Vouches for one operator, or given by one operator. */
  listJurorVouches(q: { forOperator?: string; fromOperator?: string }): Promise<JurorVouchRecord[]>;
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
  recordEmailSend(at: string, kind: "herald" | "confirm" | "issue" | "alert" | "digest" | "doorbell"): Promise<void>;

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

  // doorbells (wake/0.1): ring dedupe reuses claimAlertSend with kinds "ring:*"
  putDoorbell(d: DoorbellRecord): Promise<void>;
  getDoorbell(handle: string): Promise<DoorbellRecord | null>;
  getDoorbellBySetup(setupId: string): Promise<DoorbellRecord | null>;
  listDoorbells(limit: number): Promise<DoorbellRecord[]>;
  /**
   * Record a ring's outcome, only if the doorbell is still active and
   * unchanged since it was read (updatedAt): a person's stop, or a new token,
   * always wins over a sweep in flight. False if nothing was written.
   */
  recordDoorbellRing(handle: string, expectUpdatedAt: string, r: DoorbellRing): Promise<boolean>;
  /** Erase ring claims older than `beforeIso` (their cases are long closed); returns how many. */
  purgeRingClaims(beforeIso: string): Promise<number>;

  // operator console: small state (last cron run, last audit) and the action trail
  putOpsState(key: string, value: Json, at: string): Promise<void>;
  getOpsState(key: string): Promise<{ value: Json; at: string } | null>;
  appendAudit(a: AuditRecord): Promise<void>;
  /** Newest first. */
  listAudit(limit: number): Promise<AuditRecord[]>;

  /** Log entries with payloads from `fromSeq`, in order: whole-log analytics without one query per entry. */
  listLog(fromSeq: number, limit: number): Promise<LogRowView[]>;
  /** Whole log entries in seq order, with their hashes and payloads: what GET /v1/log/entries serves. */
  listLogFull(fromSeq: number, limit: number): Promise<Array<{ entry: LogEntry; entryHash: string; payload: Json }>>;
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
  /** Withdraw a preprint from view (one-way; a later full-row write never undoes it). */
  markPreprintWithdrawn(id: string, at: string): Promise<void>;
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
