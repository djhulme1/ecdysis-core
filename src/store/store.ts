/**
 * What the Worker keeps besides the log's own rows: the doorbells (operational, never on the log), the claims that stop a
 * ring or an email being sent twice, the email ledger every kind of email shares, operational state (the cron's last run,
 * the last audit, the scouts' candidates) and the operational counters (fixed names only, never who or what).
 */

import type { Json } from "../core/canonical.js";
import type { LogBackend, LogEntry } from "../core/log.js";

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
  stop?: string | null;
  /** The ringing address as the private page shows it: its first character and its domain. */
  masked?: string | null;
  /** A trigger URL's service and host, as the private page names them ("Zapier", "hooks.zapier.com"). */
  service?: string | null;
  host?: string | null;
  /** The Standard Webhooks shared secret (whsec_…), sealed like a token: v1 signatures on every webhook and trigger-URL delivery. */
  signing?: string | null;
  /** A GitHub dispatch doorbell's repository (owner/name), workflow file and branch; its token is sealed in target_sealed. */
  repo?: string | null;
  workflow?: string | null;
  ref?: string | null;
  /** An MCP event subscription (mcp-events): its id, the event, who subscribed, and when it lapses unless refreshed. */
  subscription?: string | null;
  event?: string | null;
  operator?: string | null;
  account?: string | null;
  expires?: string | null;
  /** A replaced signing secret, still signed with until prevUntil, so a client rotating its secret loses nothing. */
  signingPrev?: string | null;
  prevUntil?: string | null;
  /** Subscriptions that were ended (by the person, a stop, a new doorbell or another subscription): a refresh of one is refused until the person allows them again. The newest ten. */
  endedSubs?: string[];
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

/** A log entry with its payload, for analytics that read the whole log in pages. */
export interface LogRowView {
  seq: number;
  ts: string;
  type: string;
  payload: Json;
}

/** The kinds of email the ledger counts against the shared daily cap. */
export type EmailKind = "confirm" | "alert" | "digest" | "doorbell" | "doorbell-confirm";

export interface Store extends LogBackend {
  /** The log, read in pages: payloads for whoever recomputes the record. */
  listLog(fromSeq: number, limit: number): Promise<LogRowView[]>;
  /** The same with each entry and its hash, for the public log endpoint. */
  listLogFull(fromSeq: number, limit: number): Promise<Array<{ entry: LogEntry; entryHash: string; payload: Json }>>;

  /* doorbells (wake/0.1) */
  putDoorbell(d: DoorbellRecord): Promise<void>;
  /**
   * Write a doorbell only if nobody changed it since it was read (its updatedAt is still `expectUpdatedAt`, or, for null,
   * no row exists). A person's stop always wins over a ring that was in flight.
   */
  putDoorbellIf(d: DoorbellRecord, expectUpdatedAt: string | null): Promise<boolean>;
  getDoorbell(handle: string): Promise<DoorbellRecord | null>;
  getDoorbellBySetup(setupId: string): Promise<DoorbellRecord | null>;
  listDoorbells(limit: number): Promise<DoorbellRecord[]>;
  /** Record one ring's outcome, only if the doorbell is still active and unchanged since the sweep read it. */
  recordDoorbellRing(handle: string, expectUpdatedAt: string, r: DoorbellRing): Promise<boolean>;
  /** Forget ring claims older than this (every reason they concern has long closed). */
  purgeRingClaims(beforeIso: string): Promise<number>;
  /** Claim the right to send (handle, subject, kind) once: true the first time, false ever after. */
  claimAlertSend(handle: string, subject: string, kind: string, at: string): Promise<boolean>;
  releaseAlertSend(handle: string, subject: string, kind: string): Promise<void>;

  /* the email ledger: every email Ecdysis sends counts toward one daily cap */
  recordEmailSend(at: string, kind: EmailKind): Promise<void>;
  countEmailSends(sinceIso: string, kind?: string): Promise<number>;

  /* operational state and counters */
  putOpsState(key: string, value: Json, at: string): Promise<void>;
  getOpsState(key: string): Promise<{ value: Json; at: string } | null>;
  bumpAccess(id: string): Promise<void>;
  getAccess(id: string): Promise<number>;
  listAccessPrefix(prefix: string): Promise<Array<{ id: string; count: number }>>;
}
