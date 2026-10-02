/**
 * Accounts for people (Ecdysis v2; design: claude/ecdysis-v2-people-and-
 * stewardship.md §2–§3, §8).
 *
 * Principles, in code:
 *  - The log stays pseudonymous. An account owns one OPERATOR ID (`op_…`),
 *    and that id is all the log ever sees. Email, sessions, pairing codes
 *    and preferences live here, off the log, and can be deleted.
 *  - No passwords. Sign-in is an email magic link: single-use, 15 minutes,
 *    stored as a hash, bound to the browser that asked for it. Sessions are
 *    30-day HttpOnly cookies, stored as hashes; each sign-in mints a new one
 *    (earlier sessions on other devices stay until they expire or "sign out
 *    everywhere" ends them).
 *  - Sensitive actions (revoking a key, deleting the account, steward acts)
 *    need a sign-in within the last STEP_UP_MS.
 *  - Email is kept two ways, neither readable from the database alone: an
 *    HMAC for lookup and an AES-GCM seal for sending, both keyed from the
 *    ACCOUNTS_KEY secret (HKDF, distinct infos). Without that key there are
 *    no accounts (fail closed), and the pages say so.
 *  - Nothing here is an input to any number. Tiers reach the record only
 *    as `operator.tier` entries the service appends when an agent is paired.
 */

import { b64urlDecode, b64urlEncode, bufferSource, toHex, type Json } from "../../core/canonical.js";
import { EMAIL_RE, type SendEmail } from "../herald.js";
import { sha256Hex, sameString } from "../access.js";

export const LINK_TTL_MS = 15 * 60 * 1000;
export const SESSION_TTL_MS = 30 * 24 * 3600 * 1000;
export const STEP_UP_MS = 10 * 60 * 1000;
export const PAIRING_TTL_MS = 24 * 3600 * 1000;
export const LINKS_PER_HOUR = 5;
/** Sign-in links the whole deployment sends in an hour: a ceiling on what an attacker can make Ecdysis mail out. */
export const LINKS_GLOBAL_PER_HOUR = 300;
export const SIGNUPS_PER_HOUR = 3;
/**
 * Pairing-code guesses per connection and hour. The code's 75 bits are the
 * real defence; this only slows a flood. It is generous because MCP calls
 * from an AI app arrive from that app's few addresses, shared by all its
 * users, and a legitimate pairing must never be refused for a stranger's
 * typo.
 */
export const PAIRING_ATTEMPTS_PER_HOUR = 200;
const HOUR_MS = 3600 * 1000;

export type Role = "member" | "steward";

export interface AccountRow {
  id: string;
  emailHash: string;
  emailSealed: string;
  operatorId: string;
  role: Role;
  createdAt: string;
}
export interface SessionRow { hash: string; accountId: string; createdAt: string; expiresAt: string; signedInAt: string }
export interface MagicLinkRow { hash: string; emailHash: string; emailSealed: string; browserHash: string; createdAt: string; expiresAt: string; usedAt: string | null }
export interface PairingRow { hash: string; accountId: string; createdAt: string; expiresAt: string; usedAt: string | null }

export type Digest = "daily" | "weekly" | "off";
export const ALERTS = ["check.owed", "dispute.opened", "claim.contested", "claim.established", "finding.against", "appeal.deadline"] as const;
export type Alert = (typeof ALERTS)[number];
export interface Preferences {
  interests: { fields: string[]; topics: string[]; claims: string[]; agents: string[] };
  notifications: { digest: Digest; alerts: Alert[] };
  /** A public profile at /u/<name>, opt-in (§4.7). Null: none. */
  profile: string | null;
}
export const DEFAULT_PREFERENCES: Preferences = { interests: { fields: [], topics: [], claims: [], agents: [] }, notifications: { digest: "off", alerts: [] }, profile: null };

/** Everything off the log. Deleting an account deletes its rows here and nothing on the log. */
export interface AccountStore {
  getAccount(id: string): Promise<AccountRow | null>;
  getAccountByEmailHash(emailHash: string): Promise<AccountRow | null>;
  getAccountByOperator(operatorId: string): Promise<AccountRow | null>;
  putAccount(row: AccountRow): Promise<void>;
  /** Create an account; false (and nothing written) when one with that email hash already exists. */
  createAccount(row: AccountRow): Promise<boolean>;
  /** Remove the account and everything that could identify its address: sessions, pairings, preferences, sent alerts, its links and its rate-limit events. */
  deleteAccount(id: string, emailHash: string): Promise<void>;
  putMagicLink(row: MagicLinkRow): Promise<void>;
  getMagicLink(hash: string): Promise<MagicLinkRow | null>;
  /** Spend the link: true if this call spent it, false if it was already spent (the store decides atomically). */
  useMagicLink(hash: string, usedAt: string): Promise<boolean>;
  putSession(row: SessionRow): Promise<void>;
  getSession(hash: string): Promise<SessionRow | null>;
  deleteSession(hash: string): Promise<void>;
  deleteSessionsFor(accountId: string): Promise<void>;
  putPairing(row: PairingRow): Promise<void>;
  getPairing(hash: string): Promise<PairingRow | null>;
  /** Spend the code: true if this call spent it, false if it was already spent. */
  usePairing(hash: string, usedAt: string): Promise<boolean>;
  getPreferences(accountId: string): Promise<Preferences | null>;
  putPreferences(accountId: string, prefs: Preferences): Promise<void>;
  /** Rate limiting: how many events a bucket saw since `sinceIso`, and record one. Events are forgotten after a day. */
  countEvents(bucket: string, sinceIso: string): Promise<number>;
  recordEvent(bucket: string, atIso: string): Promise<void>;
  /** Alert emails: accounts with any alert ticked, and the durable record of what was sent to whom. */
  listAlertAccounts(): Promise<Array<{ account: AccountRow; alerts: Alert[] }>>;
  /** Accounts that chose a digest, with their preferences. */
  listDigestAccounts(): Promise<Array<{ account: AccountRow; prefs: Preferences }>>;
  wasSent(accountId: string, key: string): Promise<boolean>;
  markSent(accountId: string, key: string, atIso: string): Promise<void>;
}

export class MemoryAccountStore implements AccountStore {
  accounts = new Map<string, AccountRow>();
  links = new Map<string, MagicLinkRow>();
  sessions = new Map<string, SessionRow>();
  pairings = new Map<string, PairingRow>();
  prefs = new Map<string, Preferences>();
  events: Array<{ bucket: string; at: string }> = [];
  async getAccount(id: string) { return this.accounts.get(id) ?? null; }
  async getAccountByEmailHash(h: string) { return [...this.accounts.values()].find((a) => a.emailHash === h) ?? null; }
  async getAccountByOperator(op: string) { return [...this.accounts.values()].find((a) => a.operatorId === op) ?? null; }
  async putAccount(row: AccountRow) { this.accounts.set(row.id, { ...row }); }
  async createAccount(row: AccountRow) {
    for (const a of this.accounts.values()) if (a.emailHash === row.emailHash) return false;
    this.accounts.set(row.id, { ...row });
    return true;
  }
  async deleteAccount(id: string, emailHash: string) {
    this.accounts.delete(id);
    this.prefs.delete(id);
    for (const k of this.sent) if (k.startsWith(`${id}|`)) this.sent.delete(k);
    for (const [h, s] of this.sessions) if (s.accountId === id) this.sessions.delete(h);
    for (const [h, p] of this.pairings) if (p.accountId === id) this.pairings.delete(h);
    for (const [h, l] of this.links) if (l.emailHash === emailHash) this.links.delete(h);
    this.events = this.events.filter((e) => e.bucket !== `link:e:${emailHash}`);
  }
  async putMagicLink(row: MagicLinkRow) { this.links.set(row.hash, { ...row }); }
  async getMagicLink(hash: string) { return this.links.get(hash) ?? null; }
  async useMagicLink(hash: string, usedAt: string) { const l = this.links.get(hash); if (!l || l.usedAt) return false; l.usedAt = usedAt; return true; }
  async putSession(row: SessionRow) { this.sessions.set(row.hash, { ...row }); }
  async getSession(hash: string) { return this.sessions.get(hash) ?? null; }
  async deleteSession(hash: string) { this.sessions.delete(hash); }
  async deleteSessionsFor(accountId: string) { for (const [h, s] of this.sessions) if (s.accountId === accountId) this.sessions.delete(h); }
  async putPairing(row: PairingRow) { this.pairings.set(row.hash, { ...row }); }
  async getPairing(hash: string) { return this.pairings.get(hash) ?? null; }
  async usePairing(hash: string, usedAt: string) { const p = this.pairings.get(hash); if (!p || p.usedAt) return false; p.usedAt = usedAt; return true; }
  async getPreferences(accountId: string) { return this.prefs.get(accountId) ?? null; }
  async putPreferences(accountId: string, prefs: Preferences) { this.prefs.set(accountId, structuredClone(prefs)); }
  async countEvents(bucket: string, sinceIso: string) { return this.events.filter((e) => e.bucket === bucket && e.at >= sinceIso).length; }
  async recordEvent(bucket: string, atIso: string) { this.events.push({ bucket, at: atIso }); }
  sent = new Set<string>();
  async listAlertAccounts() {
    const out: Array<{ account: AccountRow; alerts: Alert[] }> = [];
    for (const [id, p] of this.prefs) { const a = this.accounts.get(id); if (a && p.notifications.alerts.length) out.push({ account: a, alerts: p.notifications.alerts }); }
    return out;
  }
  async listDigestAccounts() {
    const out: Array<{ account: AccountRow; prefs: Preferences }> = [];
    for (const [id, p] of this.prefs) { const a = this.accounts.get(id); if (a && p.notifications.digest !== "off") out.push({ account: a, prefs: structuredClone(p) }); }
    return out;
  }
  async wasSent(accountId: string, key: string) { return this.sent.has(`${accountId}|${key}`); }
  async markSent(accountId: string, key: string) { this.sent.add(`${accountId}|${key}`); }
}

export interface AccountsOptions {
  store: AccountStore;
  /** ACCOUNTS_KEY: 32 bytes as 64 hex characters. Null or unreadable: accounts are closed. */
  key: string | null;
  send: SendEmail | null;
  from: string;
  replyTo: string;
  siteBase: string;
  /** SHA-256 hex of lowercase emails that hold the steward role (the same list the console used). */
  stewardEmailHashes: string[];
  now?: () => Date;
  /** Random bytes; the Worker's crypto by default. */
  randomBytes?: (n: number) => Uint8Array;
}

export interface Signed { account: AccountRow; session: SessionRow; sessionHash: string }

const HEX64 = /^[0-9a-f]{64}$/i;
const te = new TextEncoder();
const td = new TextDecoder();
/** Pairing codes: 15 characters from an alphabet without look-alikes, as three groups (75 bits). */
const CODE_ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789";
export const PAIRING_CODE = /^[a-z2-9]{5}-[a-z2-9]{5}-[a-z2-9]{5}$/;

export class Accounts {
  private now: () => Date;
  private rnd: (n: number) => Uint8Array;
  private keys: Promise<{ hmac: CryptoKey; aes: CryptoKey; tokens: CryptoKey; keys: CryptoKey } | null> | null = null;

  constructor(private o: AccountsOptions) {
    this.now = o.now ?? (() => new Date());
    this.rnd = o.randomBytes ?? ((n) => crypto.getRandomValues(new Uint8Array(n)));
  }

  /** Accounts exist only with a readable key. */
  enabled(): boolean {
    return !!this.o.key && HEX64.test(this.o.key.trim());
  }

  private async material(): Promise<{ hmac: CryptoKey; aes: CryptoKey; tokens: CryptoKey; keys: CryptoKey } | null> {
    if (!this.enabled()) return null;
    if (!this.keys) {
      this.keys = (async () => {
        const raw = new Uint8Array(this.o.key!.trim().match(/../g)!.map((h) => parseInt(h, 16)));
        const base = await crypto.subtle.importKey("raw", bufferSource(raw), "HKDF", false, ["deriveKey"]);
        const derive = (info: string, algo: HmacKeyGenParams | AesKeyGenParams, usages: KeyUsage[]) =>
          crypto.subtle.deriveKey({ name: "HKDF", hash: "SHA-256", salt: bufferSource(te.encode("ecdysis-accounts/1")), info: bufferSource(te.encode(info)) }, base, algo, false, usages);
        return {
          hmac: await derive("email-hash/1", { name: "HMAC", hash: "SHA-256" }, ["sign"]),
          aes: await derive("email-seal/1", { name: "AES-GCM", length: 256 }, ["encrypt", "decrypt"]),
          tokens: await derive("tokens/1", { name: "HMAC", hash: "SHA-256" }, ["sign"]),
          keys: await derive("managed-key/1", { name: "AES-GCM", length: 256 }, ["encrypt", "decrypt"]),
        };
      })();
    }
    return this.keys;
  }

  /* ---------------- primitives ---------------- */

  static normaliseEmail(email: string): string | null {
    const e = email.trim().toLowerCase();
    return EMAIL_RE.test(e) ? e : null;
  }

  /** Keyed hash of an email for lookup: unguessable without the key. */
  async emailHash(email: string): Promise<string> {
    const m = await this.material();
    if (!m) throw new Error("accounts closed");
    return toHex(new Uint8Array(await crypto.subtle.sign("HMAC", m.hmac, bufferSource(te.encode(email)))));
  }

  /** A keyed token over `purpose|subject` (one-click stop links, say), under its own derived key: never a hash of an address. */
  async token_(purpose: string, subject: string): Promise<string> {
    const m = await this.material();
    if (!m) throw new Error("accounts closed");
    return toHex(new Uint8Array(await crypto.subtle.sign("HMAC", m.tokens, bufferSource(te.encode(`${purpose}|${subject}`)))));
  }

  /** Whether an account's address is on the configured steward list, read now (a steward removed from the list stops being one at once). */
  async isSteward(account: AccountRow): Promise<boolean> {
    if (!this.o.stewardEmailHashes.length) return false;
    const email = await this.unseal(account.emailSealed);
    return !!email && this.o.stewardEmailHashes.includes(await sha256Hex(email));
  }

  /** The address, masked for display: enough to recognise, not enough to copy. */
  static maskEmail(email: string): string {
    const at = email.indexOf("@");
    if (at <= 0) return "…";
    return `${email[0]}…@${email.slice(at + 1)}`;
  }

  async seal(text: string): Promise<string> {
    const m = await this.material();
    if (!m) throw new Error("accounts closed");
    const iv = this.rnd(12);
    const ct = new Uint8Array(await crypto.subtle.encrypt({ name: "AES-GCM", iv: bufferSource(iv) }, m.aes, bufferSource(te.encode(text))));
    return `${b64urlEncode(iv)}.${b64urlEncode(ct)}`;
  }

  async unseal(sealed: string): Promise<string | null> {
    const m = await this.material();
    const [iv, ct] = sealed.split(".");
    if (!m || !iv || !ct) return null;
    try {
      return td.decode(await crypto.subtle.decrypt({ name: "AES-GCM", iv: bufferSource(b64urlDecode(iv)) }, m.aes, bufferSource(b64urlDecode(ct))));
    } catch {
      return null;
    }
  }

  /**
   * Seal a managed agent's private key (I.4), under its own derived key and
   * bound to the handle: a sealed key moved to another agent's row does not
   * open. The archive holds such keys only for agents whose people asked.
   */
  async sealManagedKey(handle: string, privateKey: string): Promise<string> {
    const m = await this.material();
    if (!m) throw new Error("accounts closed");
    const iv = this.rnd(12);
    const ct = new Uint8Array(await crypto.subtle.encrypt({ name: "AES-GCM", iv: bufferSource(iv), additionalData: bufferSource(te.encode(`managed|${handle}`)) }, m.keys, bufferSource(te.encode(privateKey))));
    return `${b64urlEncode(iv)}.${b64urlEncode(ct)}`;
  }
  async unsealManagedKey(handle: string, sealed: string): Promise<string | null> {
    const m = await this.material();
    const [iv, ct] = sealed.split(".");
    if (!m || !iv || !ct) return null;
    try {
      return td.decode(await crypto.subtle.decrypt({ name: "AES-GCM", iv: bufferSource(b64urlDecode(iv)), additionalData: bufferSource(te.encode(`managed|${handle}`)) }, m.keys, bufferSource(b64urlDecode(ct))));
    } catch {
      return null;
    }
  }

  private token(bytes = 32): string { return b64urlEncode(this.rnd(bytes)); }
  /** A fresh browser token, for the sign-in page to set before any link is asked for. */
  newBrowserToken(): string { return this.token(); }
  private id(prefix: string): string { return `${prefix}_${toHex(this.rnd(12))}`; }
  private async hash(secret: string): Promise<string> { return sha256Hex(`ecdysis-accounts|${secret}`); }
  private async ipHash(ip: string): Promise<string> { return (await sha256Hex(`ecdysis-accounts-ip|${ip}`)).slice(0, 32); }

  /** Record the attempt, THEN count: concurrent attempts over-count rather than slip under the limit. */
  private async limited(bucket: string, perHour: number): Promise<boolean> {
    const since = new Date(this.now().getTime() - HOUR_MS).toISOString();
    await this.o.store.recordEvent(bucket, this.now().toISOString());
    return (await this.o.store.countEvents(bucket, since)) > perHour;
  }

  /* ---------------- sign-in ---------------- */

  /**
   * Ask for a magic link. The answer is the same whether or not the address
   * has an account (no enumeration). `browser` is the value of the browser
   * cookie if the browser already has one; a new one is issued otherwise
   * and must be set on the response.
   */
  async requestLink(emailIn: string, ip: string, browser: string | null): Promise<{ ok: true; browser: string; sent: boolean } | { ok: false; status: number; error: string }> {
    if (!this.enabled()) return { ok: false, status: 503, error: "Accounts aren't open yet." };
    const email = Accounts.normaliseEmail(emailIn);
    if (!email) return { ok: false, status: 400, error: "That doesn't look like an email address." };
    const eh = await this.emailHash(email);
    // The connection's limit first (an attacker's connection runs dry whatever addresses it names), then the deployment's
    // ceiling on sign-in mail, then the address's, so that one connection cannot lock an address out by itself.
    if (await this.limited(`link:ip:${await this.ipHash(ip)}`, LINKS_PER_HOUR)) return { ok: false, status: 429, error: "Too many sign-in links from this connection in the last hour. Try later." };
    if (await this.limited("link:all", LINKS_GLOBAL_PER_HOUR)) return { ok: false, status: 429, error: "Ecdysis is sending a lot of sign-in links right now. Try again in a little while." };
    if (await this.limited(`link:e:${eh}`, LINKS_PER_HOUR)) return { ok: false, status: 429, error: "Too many sign-in links for that address in the last hour. Check your inbox, or try later." };
    const b = browser && /^[A-Za-z0-9_-]{32,64}$/.test(browser) ? browser : this.token();
    const t = this.token();
    const nowIso = this.now().toISOString();
    await this.o.store.putMagicLink({
      hash: await this.hash(t), emailHash: eh, emailSealed: await this.seal(email), browserHash: await this.hash(b),
      createdAt: nowIso, expiresAt: new Date(this.now().getTime() + LINK_TTL_MS).toISOString(), usedAt: null,
    });
    let sent = false;
    if (this.o.send) {
      const url = `${this.o.siteBase}/me/login?t=${t}`;
      const r = await this.o.send({
        from: this.o.from, to: email, replyTo: this.o.replyTo,
        subject: "Your Ecdysis sign-in link",
        text: `Sign in to Ecdysis from the browser you asked in:\n\n${url}\n\nThe link works once, for 15 minutes, and only in that browser. If you didn't ask for it, ignore this email: nothing happens without the link.\n\nEcdysis never asks for a password.`,
        headers: { "x-entity-ref-id": await this.hash(`link|${t}`) },
      });
      sent = r.ok;
    }
    return { ok: true, browser: b, sent };
  }

  /**
   * Follow a magic link. Creates the account on first sign-in (and its
   * operator id), rotates the session, and refreshes the steward role from
   * configuration. Returns the session cookie value to set.
   */
  async completeLink(t: string, browser: string | null, ip: string): Promise<{ ok: true; session: string; account: AccountRow; created: boolean } | { ok: false; status: number; error: string }> {
    if (!this.enabled()) return { ok: false, status: 503, error: "Accounts aren't open yet." };
    if (!/^[A-Za-z0-9_-]{32,64}$/.test(t)) return { ok: false, status: 400, error: "That link isn't valid." };
    const link = await this.o.store.getMagicLink(await this.hash(t));
    const nowMs = this.now().getTime();
    if (!link || link.usedAt || Date.parse(link.expiresAt) < nowMs) return { ok: false, status: 410, error: "That link has expired or was already used. Ask for a new one." };
    if (!browser || !sameString(await this.hash(browser), link.browserHash)) return { ok: false, status: 403, error: "Open the link in the browser you asked for it in." };
    // Spend before use, atomically: two requests racing with one link get one session between them.
    if (!(await this.o.store.useMagicLink(link.hash, this.now().toISOString()))) return { ok: false, status: 410, error: "That link has expired or was already used. Ask for a new one." };
    let account = await this.o.store.getAccountByEmailHash(link.emailHash);
    let created = false;
    const email = await this.unseal(link.emailSealed);
    const steward = email ? this.o.stewardEmailHashes.includes(await sha256Hex(email)) : false;
    if (!account) {
      if (await this.limited(`signup:ip:${await this.ipHash(ip)}`, SIGNUPS_PER_HOUR)) return { ok: false, status: 429, error: "Too many new accounts from this connection in the last hour. Try later." };
      const fresh: AccountRow = { id: this.id("acct"), emailHash: link.emailHash, emailSealed: link.emailSealed, operatorId: this.id("op"), role: steward ? "steward" : "member", createdAt: this.now().toISOString() };
      // Two first sign-ins racing for one address: the store keeps whichever landed first; the other joins it.
      created = await this.o.store.createAccount(fresh);
      account = created ? fresh : await this.o.store.getAccountByEmailHash(link.emailHash);
      if (!account) return { ok: false, status: 500, error: "The account could not be created. Try again." };
    }
    if ((account.role === "steward") !== steward) {
      account = { ...account, role: steward ? "steward" : "member" };
      await this.o.store.putAccount(account);
    }
    const s = this.token();
    const nowIso = this.now().toISOString();
    await this.o.store.putSession({ hash: await this.hash(s), accountId: account.id, createdAt: nowIso, expiresAt: new Date(nowMs + SESSION_TTL_MS).toISOString(), signedInAt: nowIso });
    return { ok: true, session: s, account, created };
  }

  /** The signed-in account behind a session cookie, or null. Expired sessions are removed. */
  async session(cookie: string | null): Promise<Signed | null> {
    if (!cookie || !/^[A-Za-z0-9_-]{32,64}$/.test(cookie) || !this.enabled()) return null;
    const h = await this.hash(cookie);
    const s = await this.o.store.getSession(h);
    if (!s) return null;
    if (Date.parse(s.expiresAt) < this.now().getTime()) { await this.o.store.deleteSession(h); return null; }
    const account = await this.o.store.getAccount(s.accountId);
    if (!account) { await this.o.store.deleteSession(h); return null; }
    return { account, session: s, sessionHash: h };
  }

  /** An account by id (for a bearer token's principal), or null. */
  async accountById(id: string): Promise<AccountRow | null> { return this.enabled() ? this.o.store.getAccount(id) : null; }

  /** Step-up: a sign-in within the last ten minutes. */
  fresh(s: Signed): boolean {
    return this.now().getTime() - Date.parse(s.session.signedInAt) <= STEP_UP_MS;
  }

  async signOut(s: Signed): Promise<void> { await this.o.store.deleteSession(s.sessionHash); }
  async signOutEverywhere(s: Signed): Promise<void> { await this.o.store.deleteSessionsFor(s.account.id); }

  /** The anti-forgery token for this session's forms: derivable only by the browser that holds the cookie. */
  async csrf(s: Signed): Promise<string> { return (await sha256Hex(`ecdysis-me-csrf|${s.sessionHash}`)).slice(0, 40); }
  async csrfOk(s: Signed, given: string | null): Promise<boolean> { return !!given && sameString(await this.csrf(s), given); }

  /* ---------------- pairing ---------------- */

  /** A new pairing code for this account's operator id: shown once, valid 24 hours, single-use. */
  async newPairingCode(s: Signed): Promise<string> {
    const bytes = this.rnd(15);
    const chars = [...bytes].map((b) => CODE_ALPHABET[b % CODE_ALPHABET.length]!).join("");
    const code = `${chars.slice(0, 5)}-${chars.slice(5, 10)}-${chars.slice(10, 15)}`;
    const nowIso = this.now().toISOString();
    await this.o.store.putPairing({ hash: await this.hash(`pair|${code}`), accountId: s.account.id, createdAt: nowIso, expiresAt: new Date(this.now().getTime() + PAIRING_TTL_MS).toISOString(), usedAt: null });
    return code;
  }

  /**
   * Spend a pairing code: the operator id it stands for, or null. Attempts
   * are rate-limited per connection so codes cannot be guessed.
   */
  async consumePairing(codeIn: string, ip: string): Promise<{ ok: true; operatorId: string; accountId: string } | { ok: false; status: number; error: string }> {
    if (!this.enabled()) return { ok: false, status: 503, error: "accounts aren't open yet" };
    const code = codeIn.trim().toLowerCase();
    if (!PAIRING_CODE.test(code)) return { ok: false, status: 400, error: "pairing: a code like abcde-fghjk-mnpqr from the person's account page" };
    if (await this.limited(`pair:ip:${await this.ipHash(ip)}`, PAIRING_ATTEMPTS_PER_HOUR)) return { ok: false, status: 429, error: "too many pairing attempts; try later" };
    const p = await this.o.store.getPairing(await this.hash(`pair|${code}`));
    if (!p || p.usedAt || Date.parse(p.expiresAt) < this.now().getTime()) return { ok: false, status: 404, error: "pairing: unknown, used or expired code; ask the person for a fresh one" };
    const account = await this.o.store.getAccount(p.accountId);
    if (!account) return { ok: false, status: 404, error: "pairing: that account no longer exists" };
    if (!(await this.o.store.usePairing(p.hash, this.now().toISOString()))) return { ok: false, status: 404, error: "pairing: unknown, used or expired code; ask the person for a fresh one" };
    return { ok: true, operatorId: account.operatorId, accountId: account.id };
  }

  /* ---------------- preferences and deletion ---------------- */

  async preferences(s: Signed): Promise<Preferences> {
    return (await this.o.store.getPreferences(s.account.id)) ?? structuredClone(DEFAULT_PREFERENCES);
  }
  async savePreferences(s: Signed, prefs: Preferences): Promise<void> {
    await this.o.store.putPreferences(s.account.id, prefs);
  }

  /** The person's email, for sending them things they asked for. Never shown in lists or logs. */
  async emailOf(account: AccountRow): Promise<string | null> {
    return this.unseal(account.emailSealed);
  }

  /** Delete the account: email, sessions, pairings, preferences. The operator id and everything signed under it stay on the log. */
  async deleteAccount(s: Signed): Promise<void> {
    await this.o.store.deleteAccount(s.account.id, s.account.emailHash);
  }

  /** For the steward's people page: find the account behind an operator id (never by email). */
  async accountForOperator(operatorId: string): Promise<AccountRow | null> {
    return this.o.store.getAccountByOperator(operatorId);
  }

  /** Grant or remove the steward role; the record of who did it is the steward log entry the caller writes. */
  async setRole(accountId: string, role: Role): Promise<boolean> {
    const a = await this.o.store.getAccount(accountId);
    if (!a) return false;
    await this.o.store.putAccount({ ...a, role });
    return true;
  }
}

/** Read one cookie from a Cookie header. */
export function cookie(header: string | null, name: string): string | null {
  if (!header) return null;
  for (const part of header.split(";")) {
    const i = part.indexOf("=");
    if (i < 0) continue;
    if (part.slice(0, i).trim() === name) {
      // A malformed percent-escape in a cookie is a bad cookie, not a server error.
      try { return decodeURIComponent(part.slice(i + 1).trim()); } catch { return null; }
    }
  }
  return null;
}

export function setCookie(name: string, value: string, maxAgeS: number, secure = true): string {
  return `${name}=${encodeURIComponent(value)}; Path=/; Max-Age=${maxAgeS}; HttpOnly; SameSite=Lax${secure ? "; Secure" : ""}`;
}
export function clearCookie(name: string, secure = true): string {
  return `${name}=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax${secure ? "; Secure" : ""}`;
}

export type { Json };
