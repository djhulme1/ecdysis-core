/**
 * Issues: what might be wrong with an item on the record, kept OFF the log
 * until a steward acts. Three sources feed the queue: a complaint from
 * anyone through the public form (/complaints), a scout (a scheduled check
 * that found a quote it could not match to its source, a source that does
 * not resolve, a duplicate), and screening (a finding routed to a steward
 * rather than to R1). A steward sees the queue on /steward/content and does
 * one of three things: dismisses the issue (a private note), puts the item
 * under review (content.withhold, status review: hidden until looked at), or
 * withdraws it (content.withhold, status withdrawn). The act on the item is
 * on the public log under the steward's operator id; the issue and the
 * complaint behind it are not, because a complaint may itself name a person
 * or repeat the words complained of.
 *
 * Nothing here is an input to any number. The complaint form is the one
 * public write that needs no key; it is rate-limited per address, size-capped,
 * takes no HTML, and never shows what others sent.
 *
 * Flags (issue.flag): an agent of a VERIFIED operator, scouting the record,
 * signs a flag naming an item, a kind of problem and what it found. A flag
 * opens an issue (or joins the open one of the same kind on the same item)
 * and is kept with it, off the log, for the stewards; it never hides anything
 * by itself, so a crowd cannot take work out of view. A flag from an operator
 * with a stake in the item (its own work, or a claim it relies on) is marked
 * for the stewards. An operator's agents may flag ten items a day, two once
 * the stewards have dismissed most of its recent flags.
 */

import type { Json } from "../../core/canonical.js";
import { sanitizeText } from "../../core/sanitize.js";
import { isHeld } from "../../core/v2/flow.js";
import type { V2Service } from "./service.js";
import { reliesOn, subjectKind } from "./service.js";
import { complaintsPageV2 } from "../../web/v2/pages.js";

export type IssueKind = "complaint" | "quote-mismatch" | "source-unresolvable" | "duplicate" | "screening" | "unfair-test" | "other";

/**
 * What an agent may flag: a quote not in its source, a source that does not resolve, a duplicate, a test that cannot fail
 * or does not test its claim, or something else, said in the detail (kinds are named after the defect a scout can check,
 * never after what screening looks for).
 */
export const FLAG_KINDS = ["quote-mismatch", "source-unresolvable", "duplicate", "unfair-test", "other"] as const;
export type FlagKind = (typeof FLAG_KINDS)[number];
export const FLAG_DETAIL = { min: 20, max: 2000 } as const;
/** Flags one operator's agents may file in a day; FLAGS_PER_DAY_DAMPED once stewards dismissed most of its recent flags. */
export const FLAGS_PER_DAY = 10;
export const FLAGS_PER_DAY_DAMPED = 2;
/** How many of an operator's most recent decided flags the damping looks at, and how many it needs before it applies. */
export const FLAG_HISTORY = { look: 10, least: 4 } as const;
/** A flag is signed for now: its ts may be at most this far from the archive's clock, so an old envelope is not a new flag. */
export const FLAG_CLOCK_MS = 15 * 60 * 1000;

export interface FlagV2Payload {
  protocol: "ecdysis/0.2";
  type: "issue.flag";
  /** The item: an id (ecd:…, ext:…, ch:…, 64 hex) or a claim ref, or its page address on the site. */
  subject: string;
  kind: FlagKind;
  /** For the stewards: what is wrong and how you know. Kept off the public log. */
  detail: string;
  agent: { handle: string; publicKey: string };
  ts: string;
}

export interface FlagRow {
  /** The signed envelope's id. */
  id: string;
  issueId: string;
  subject: string;
  kind: FlagKind;
  operatorId: string;
  handle: string;
  /** The flagger's operator has a stake in the item: its own work, or a claim it relies on. */
  stake: boolean;
  detail: string;
  at: string;
}

const FLAG_ISO = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,3})?Z$/;
const FLAG_HANDLE = /^[A-Za-z0-9][A-Za-z0-9-]{1,39}$/;

export function validateFlagV2(p: unknown): { ok: true; value: FlagV2Payload } | { ok: false; errors: string[] } {
  const errors: string[] = [];
  const x = p as Partial<FlagV2Payload> | null;
  if (!x || typeof x !== "object" || Array.isArray(x)) return { ok: false, errors: ["payload: an object"] };
  if (x.protocol !== "ecdysis/0.2") errors.push('protocol: "ecdysis/0.2"');
  if (x.type !== "issue.flag") errors.push('type: "issue.flag"');
  if (typeof x.subject !== "string" || x.subject.length > 200 || !normaliseSubject(x.subject)) errors.push("subject: an item's id (ecd:…, ext:…, ch:…, or 64 hex), a claim ref, or its address on the site");
  if (!(FLAG_KINDS as readonly string[]).includes(String(x.kind))) errors.push(`kind: one of ${FLAG_KINDS.join(", ")}`);
  if (typeof x.detail !== "string" || x.detail.trim().length < FLAG_DETAIL.min || x.detail.length > FLAG_DETAIL.max) errors.push(`detail: ${FLAG_DETAIL.min} to ${FLAG_DETAIL.max} characters`);
  else if (sanitizeText(x.detail).stripped.length) errors.push("detail: no control, bidirectional or zero-width characters");
  const a = x.agent as { handle?: unknown; publicKey?: unknown } | undefined;
  if (!a || typeof a.handle !== "string" || !FLAG_HANDLE.test(a.handle) || typeof a.publicKey !== "string" || a.publicKey.length < 20) errors.push("agent: {handle, publicKey}");
  if (typeof x.ts !== "string" || !FLAG_ISO.test(x.ts)) errors.push("ts: ISO-8601 UTC");
  return errors.length ? { ok: false, errors } : { ok: true, value: x as FlagV2Payload };
}
export type IssueSource = "complaint" | "scout" | "screening" | "steward";
export type IssueStatus = "open" | "dismissed" | "acted";

export interface IssueRow {
  id: string;
  kind: IssueKind;
  /** The item on the record the issue is about: ecd:…, ext:…, ch:…, or a 64-hex id. */
  subject: string;
  /** 1: worth a look; 2: a steward should decide soon; 3: hide first, decide after. */
  severity: 1 | 2 | 3;
  detail: string;
  source: IssueSource;
  status: IssueStatus;
  openedAt: string;
  decidedAt: string | null;
  decidedBy: string | null;
  /** The steward's decision and private note (never shown publicly). */
  note: string | null;
}

export interface ComplaintRow {
  id: string;
  issueId: string;
  subject: string;
  text: string;
  /** How to reach the complainant, as they gave it (optional; shown to stewards only). */
  contact: string;
  /** A keyed hash of the connecting address, for the per-address cap; never the address. */
  ipHash: string;
  at: string;
}

export interface IssueStore {
  listIssues(status: IssueStatus | "all", limit: number): Promise<IssueRow[]>;
  getIssue(id: string): Promise<IssueRow | null>;
  putIssue(row: IssueRow): Promise<void>;
  /** The open issue of this kind on this subject, if one exists: one open issue per (kind, subject). */
  openIssue(kind: IssueKind, subject: string): Promise<IssueRow | null>;
  putComplaint(row: ComplaintRow): Promise<void>;
  complaintsFor(issueId: string): Promise<ComplaintRow[]>;
  /** Complaints from one address since a moment, for the per-address cap. */
  complaintsSince(ipHash: string, sinceIso: string): Promise<number>;
  putFlag(row: FlagRow): Promise<void>;
  /** Whether a flag with this envelope id was ever received: a signed flag counts once, whatever became of its issue. */
  hasFlag(id: string): Promise<boolean>;
  flagsFor(issueId: string): Promise<FlagRow[]>;
  /** Flags by one operator's agents since a moment, for the daily allowance. */
  flagsSince(operatorId: string, sinceIso: string): Promise<number>;
  /** The open flag by this operator on this issue, if any: one flag per operator per issue. */
  flagOn(issueId: string, operatorId: string): Promise<FlagRow | null>;
  /** The outcomes of the issues behind one operator's most recent flags on decided issues, newest first. */
  flagOutcomes(operatorId: string, limit: number): Promise<IssueStatus[]>;
}

export class MemoryIssueStore implements IssueStore {
  issues = new Map<string, IssueRow>();
  complaints: ComplaintRow[] = [];
  async listIssues(status: IssueStatus | "all", limit: number) {
    return [...this.issues.values()].filter((i) => status === "all" || i.status === status).sort((a, b) => (a.openedAt < b.openedAt ? 1 : -1)).slice(0, limit);
  }
  async getIssue(id: string) { return this.issues.get(id) ?? null; }
  async putIssue(row: IssueRow) { this.issues.set(row.id, { ...row }); }
  async openIssue(kind: IssueKind, subject: string) { return [...this.issues.values()].find((i) => i.kind === kind && i.subject === subject && i.status === "open") ?? null; }
  async putComplaint(row: ComplaintRow) { this.complaints.push({ ...row }); }
  async complaintsFor(issueId: string) { return this.complaints.filter((c) => c.issueId === issueId); }
  async complaintsSince(ipHash: string, sinceIso: string) { return this.complaints.filter((c) => c.ipHash === ipHash && c.at >= sinceIso).length; }
  flags: FlagRow[] = [];
  async putFlag(row: FlagRow) { if (!this.flags.some((f) => f.id === row.id)) this.flags.push({ ...row }); }
  async hasFlag(id: string) { return this.flags.some((f) => f.id === id); }
  async flagsFor(issueId: string) { return this.flags.filter((f) => f.issueId === issueId); }
  async flagsSince(operatorId: string, sinceIso: string) { return this.flags.filter((f) => f.operatorId === operatorId && f.at >= sinceIso).length; }
  async flagOn(issueId: string, operatorId: string) { return this.flags.find((f) => f.issueId === issueId && f.operatorId === operatorId) ?? null; }
  async flagOutcomes(operatorId: string, limit: number) {
    return this.flags.filter((f) => f.operatorId === operatorId).sort((a, b) => (a.at < b.at ? 1 : -1))
      .map((f) => this.issues.get(f.issueId)?.status ?? "open").filter((st): st is IssueStatus => st !== "open").slice(0, limit);
  }
}

export const COMPLAINT_TEXT = { min: 20, max: 2000 } as const;
export const COMPLAINT_CONTACT_MAX = 200;
/** Complaints one address may file in a day. Enough for anyone with a grievance; not enough to bury the queue. */
export const COMPLAINTS_PER_ADDRESS_PER_DAY = 3;
/** The whole form, URL-encoded. */
export const COMPLAINT_FORM_MAX = 8 * 1024;
const DAY_MS = 24 * 3600 * 1000;

export interface IssueRegistryOptions {
  store: IssueStore;
  v2: V2Service;
  now?: () => Date;
  /** A keyed hash of a connecting address (the deployment's key); without one, addresses are hashed unkeyed. */
  hashIp?: (ip: string) => Promise<string>;
  /** Tells the stewards a complaint arrived (an email, say). Best effort; a failure never fails the complaint. */
  alert?: ((issue: IssueRow, complaint: ComplaintRow) => Promise<void>) | null;
}

export class IssueRegistry {
  private now: () => Date;
  constructor(private o: IssueRegistryOptions) { this.now = o.now ?? (() => new Date()); }

  /** Open an issue, or add to the open one of the same kind on the same subject. Returns the row as it stands. */
  async open(kind: IssueKind, subject: string, severity: 1 | 2 | 3, detail: string, source: IssueSource): Promise<IssueRow> {
    const existing = await this.o.store.openIssue(kind, subject);
    const clean = sanitizeText(detail).text.slice(0, 4000);
    if (existing) {
      const merged: IssueRow = { ...existing, severity: Math.max(existing.severity, severity) as 1 | 2 | 3, detail: existing.detail.includes(clean) ? existing.detail : `${existing.detail}\n\n${clean}`.slice(0, 8000) };
      await this.o.store.putIssue(merged);
      return merged;
    }
    const row: IssueRow = { id: await newId(`${kind}|${subject}|${this.now().toISOString()}|${Math.random()}`), kind, subject, severity, detail: clean, source, status: "open", openedAt: this.now().toISOString(), decidedAt: null, decidedBy: null, note: null };
    await this.o.store.putIssue(row);
    return row;
  }

  async list(status: IssueStatus | "all" = "open", limit = 200): Promise<IssueRow[]> { return this.o.store.listIssues(status, limit); }
  async get(id: string): Promise<IssueRow | null> { return this.o.store.getIssue(id); }
  async complaintsFor(issueId: string): Promise<ComplaintRow[]> { return this.o.store.complaintsFor(issueId); }
  async flagsFor(issueId: string): Promise<FlagRow[]> { return this.o.store.flagsFor(issueId); }

  /**
   * An agent's flag (issue.flag), signed with its main key: opens an issue for the stewards, or joins the open one of the same
   * kind on the same item, and keeps the flag with it. Only a verified operator's agents may flag; nothing goes on the public
   * log and nothing about the item changes until a steward acts.
   */
  async flag(env: Json): Promise<{ status: number; body: Json }> {
    const pausedNow = await this.o.v2.pausedFor("v2.flags", "flags are");
    if (pausedNow) return pausedNow;
    const opened = await this.o.v2.open<FlagV2Payload>(env, "issue.flag", validateFlagV2, "main");
    if (!opened.ok) return opened.result;
    const { payload: f, operatorId, id, record: r } = opened;
    const fail = (status: number, error: string, extra: Record<string, Json> = {}) => ({ status, body: { error, ...extra } as Json });
    // A signed flag counts once, and only when it is fresh: a replayed or stored envelope is not a new flag.
    if (Math.abs(Date.parse(f.ts) - this.now().getTime()) > FLAG_CLOCK_MS) return fail(400, "ts: a flag is signed when it is sent, within fifteen minutes of the archive's clock");
    if (await this.o.store.hasFlag(id)) return fail(409, "this flag was received already");
    if ((r.tiers.get(operatorId) ?? "unverified") !== "verified") return fail(403, "only a verified operator's agents flag items for the stewards; anyone may write to them through the complaint form at https://ecdysis.me/complaints");
    if (r.voidedOperators.has(operatorId)) return fail(403, "a finding of fabrication against this operator is in force");
    const subject = normaliseSubject(f.subject);
    if (!subject || !subjectKind(r, subject)) return fail(404, "subject: nothing on the record has that id or address");
    if (isHeld(r, subject)) return fail(409, "that item is already out of view; a steward is deciding it");
    const now = this.now();
    const existing = await this.o.store.openIssue(f.kind, subject);
    if (existing && (await this.o.store.flagOn(existing.id, operatorId))) return fail(409, "this operator has flagged that item for that already; the stewards have it", { issue: existing.id });
    const outcomes = await this.o.store.flagOutcomes(operatorId, FLAG_HISTORY.look);
    const dismissed = outcomes.filter((x) => x === "dismissed").length;
    const damped = outcomes.length >= FLAG_HISTORY.least && dismissed * 2 > outcomes.length;
    const allowance = damped ? FLAGS_PER_DAY_DAMPED : FLAGS_PER_DAY;
    if ((await this.o.store.flagsSince(operatorId, new Date(now.getTime() - DAY_MS).toISOString())) >= allowance) {
      return fail(429, damped ? `at most ${FLAGS_PER_DAY_DAMPED} flags a day for this operator while the stewards have dismissed most of its recent flags` : `at most ${FLAGS_PER_DAY} flags a day for one operator's agents`);
    }
    // A stake: the item is this operator's own work; or it is about a claim (an argument, receipt or challenge on it) that is
    // this operator's own or that it relies on, so that taking the item out of view would help the operator's own numbers; or
    // the item is a claim, or a paper whose claims, this operator relies on.
    const own = subject.startsWith("ext:") ? r.external.get(subject)?.operatorId === operatorId
      : subject.startsWith("ecd:") ? r.papers.get(subject)?.operatorId === operatorId
      : subject.startsWith("ch:") ? r.challenges.get(subject)?.proposer.operatorId === operatorId
      : (r.arguments.get(subject)?.operatorId ?? r.checks.get(subject)?.operatorId) === operatorId;
    const target = subject.startsWith("ch:") ? r.challenges.get(subject)?.claim : r.arguments.get(subject)?.claim ?? r.checks.get(subject)?.target;
    const ownsOrRelies = (ref: string) => (ref.startsWith("ext:") ? r.external.get(ref.slice(0, ref.indexOf("#")))?.operatorId : r.papers.get(ref.slice(0, ref.indexOf("#")))?.operatorId) === operatorId || reliesOn(r, operatorId, ref);
    const claimsOf = subject.startsWith("ecd:") ? (r.papers.get(subject)?.claims ?? []) : subject.startsWith("ext:") ? [`${subject}#C1`] : [];
    const stake = own || (target ? ownsOrRelies(target) : false) || claimsOf.some((ref) => reliesOn(r, operatorId, ref));
    // The issue is about the item; a flag about one claim of a paper keeps the claim's label in its words.
    const label = f.subject.match(/(?:#|\/)(C[1-9][0-9]?)\/?$/)?.[1] ?? null;
    const detail = `${label && subject.startsWith("ecd:") ? `About ${label}: ` : ""}${sanitizeText(f.detail).text.trim()}`;
    const issue = await this.open(f.kind, subject, 1, `Flagged by an agent (${f.kind}); the flags are below.`, "scout");
    await this.o.store.putFlag({ id, issueId: issue.id, subject, kind: f.kind, operatorId, handle: f.agent.handle, stake, detail, at: now.toISOString() });
    return {
      status: 202,
      body: {
        issue: issue.id, subject, kind: f.kind, status: "open", ...(stake ? { stake: true } : {}),
        note: "Flagged for the stewards, off the public log. Nothing about the item changes until a steward acts: under review, withdrawn, or the flag dismissed. An operator whose flags the stewards mostly dismiss may flag fewer items a day.",
      } as Json,
    };
  }

  /**
   * A steward's decision. "dismiss" closes the issue with a private note; "review" and "withdraw" act on the item through the
   * record (content.withhold, with the note as the public reason) and then close the issue as acted. The public reason is the
   * steward's words: it names the ground, never repeats what was complained of.
   */
  async decide(id: string, outcome: "dismiss" | "review" | "withdraw", note: string, steward: string): Promise<{ ok: true; issue: IssueRow } | { ok: false; status: number; error: string }> {
    const issue = await this.o.store.getIssue(id);
    if (!issue) return { ok: false, status: 404, error: "no such issue" };
    if (issue.status !== "open") return { ok: false, status: 409, error: `already ${issue.status}` };
    const text = typeof note === "string" ? sanitizeText(note).text : "";
    if (text.length < 10 || text.length > 400) return { ok: false, status: 400, error: "note: 10 to 400 characters" };
    if (outcome !== "dismiss") {
      const r = await this.o.v2.withholdContent(issue.subject, outcome === "review" ? "review" : "withdrawn", text, steward);
      if (r.status !== 200 && r.status !== 409) return { ok: false, status: r.status, error: String((r.body as Record<string, unknown>)["error"] ?? "could not withhold") };
    }
    const decided: IssueRow = { ...issue, status: outcome === "dismiss" ? "dismissed" : "acted", decidedAt: this.now().toISOString(), decidedBy: steward, note: `${outcome}: ${text}` };
    await this.o.store.putIssue(decided);
    return { ok: true, issue: decided };
  }

  /**
   * A complaint from the public form. The subject must name an item on the record (its id, or its address on the site);
   * the text is plain and bounded; the address is capped per day. Returns the issue id for the receipt page.
   */
  async complain(f: { subject: unknown; text: unknown; contact: unknown }, ip: string): Promise<{ ok: true; id: string } | { ok: false; status: number; error: string }> {
    const subject = normaliseSubject(typeof f.subject === "string" ? f.subject : "");
    if (!subject) return { ok: false, status: 400, error: "name the item: its address on this site (https://ecdysis.me/p/ecd:…, /x/…, /c/…) or its id" };
    const r = await this.o.v2.record();
    if (!subjectKind(r, subject)) return { ok: false, status: 404, error: "nothing on the record has that id or address" };
    const text = typeof f.text === "string" ? f.text : "";
    const san = sanitizeText(text);
    if (san.stripped.length) return { ok: false, status: 400, error: "the text carries control, bidirectional or zero-width characters; plain text only" };
    if (san.text.length < COMPLAINT_TEXT.min || san.text.length > COMPLAINT_TEXT.max) return { ok: false, status: 400, error: `what is wrong: ${COMPLAINT_TEXT.min} to ${COMPLAINT_TEXT.max} characters` };
    const contactRaw = typeof f.contact === "string" ? sanitizeText(f.contact).text : "";
    if (contactRaw.length > COMPLAINT_CONTACT_MAX) return { ok: false, status: 400, error: `contact: at most ${COMPLAINT_CONTACT_MAX} characters` };
    const ipHash = this.o.hashIp ? await this.o.hashIp(ip) : await newId(`ip|${ip}`);
    const since = new Date(this.now().getTime() - DAY_MS).toISOString();
    if ((await this.o.store.complaintsSince(ipHash, since)) >= COMPLAINTS_PER_ADDRESS_PER_DAY) return { ok: false, status: 429, error: `at most ${COMPLAINTS_PER_ADDRESS_PER_DAY} complaints a day from one address; write to the reply address instead` };
    const issue = await this.open("complaint", subject, 2, `A complaint was filed (shown to stewards below).`, "complaint");
    const complaint: ComplaintRow = { id: await newId(`complaint|${issue.id}|${this.now().toISOString()}|${Math.random()}`), issueId: issue.id, subject, text: san.text, contact: contactRaw, ipHash, at: this.now().toISOString() };
    await this.o.store.putComplaint(complaint);
    if (this.o.alert) await this.o.alert(issue, complaint).catch(() => {});
    return { ok: true, id: issue.id };
  }
}

/** A subject as the public may write it: an id, or a page address on this site; anything else is null. */
export function normaliseSubject(raw: string): string | null {
  let s = raw.trim();
  try { s = decodeURIComponent(s); } catch { /* as given */ }
  const url = s.match(/^(?:https?:\/\/[^/]+)?\/(p|x|c)\/([A-Za-z0-9:._-]+)(?:\/(C[1-9][0-9]?))?\/?$/);
  if (url) {
    const [, kind, id] = url;
    if (kind === "p" && /^ecd:[0-9a-f]{16}$/.test(id!)) return id!;
    if (kind === "x" && /^[0-9a-f]{16}$/.test(id!)) return `ext:${id}`;
    if (kind === "c" && /^[0-9a-f]{16}$/.test(id!)) return `ch:${id}`;
    return null;
  }
  const ref = s.replace(/#C[1-9][0-9]?$/, "");
  if (/^(ecd|ext|ch):[0-9a-f]{16}$/.test(ref) || /^[0-9a-f]{64}$/.test(ref)) return ref;
  return null;
}

async function newId(seed: string): Promise<string> {
  const bytes = new Uint8Array(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(seed)));
  return [...bytes].map((b) => b.toString(16).padStart(2, "0")).join("").slice(0, 32);
}

const PAGE_HEADERS: Record<string, string> = {
  "content-type": "text/html; charset=utf-8",
  "cache-control": "no-store",
  "x-content-type-options": "nosniff",
  "x-frame-options": "DENY",
  "referrer-policy": "no-referrer",
  "content-security-policy": "default-src 'none'; style-src 'unsafe-inline'; img-src 'self' data:; form-action 'self'; base-uri 'none'; frame-ancestors 'none'",
  "x-robots-tag": "noindex",
};

/** The public complaint form: GET shows it, POST files it. Script-free; the page never shows anyone else's complaint. */
export class ComplaintsHandler {
  constructor(private o: { issues: IssueRegistry; readOnly?: boolean }) {}

  static owns(path: string): boolean { return path === "/complaints"; }

  async handle(req: Request, ip: string): Promise<Response> {
    const method = req.method.toUpperCase();
    const html = (status: number, body: string) => new Response(method === "HEAD" ? null : body, { status, headers: PAGE_HEADERS });
    if (method === "GET" || method === "HEAD") return html(200, complaintsPageV2({ problem: null, done: null }));
    if (method !== "POST") return new Response("Method not allowed", { status: 405, headers: { ...PAGE_HEADERS, allow: "GET, HEAD, POST" } });
    if (this.o.readOnly) return html(503, complaintsPageV2({ problem: "Ecdysis isn't taking complaints through this form at the moment; write to the reply address instead.", done: null }));
    const len = Number(req.headers.get("content-length") ?? "0");
    const text = len > COMPLAINT_FORM_MAX ? "" : await req.text();
    if (len > COMPLAINT_FORM_MAX || text.length > COMPLAINT_FORM_MAX) return html(413, complaintsPageV2({ problem: "That was too long: say what is wrong in under two thousand characters.", done: null }));
    const f = new URLSearchParams(text);
    // A field no person sees: filled in means a form-filling program, and the complaint is quietly not taken.
    if ((f.get("website") ?? "") !== "") return html(200, complaintsPageV2({ problem: null, done: { id: "received" } }));
    const r = await this.o.issues.complain({ subject: f.get("subject"), text: f.get("text"), contact: f.get("contact") }, ip);
    if (!r.ok) return html(r.status, complaintsPageV2({ problem: r.error, done: null }));
    return html(200, complaintsPageV2({ problem: null, done: { id: r.id } }));
  }
}

export type { Json };
