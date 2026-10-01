/**
 * The Ecdysis digest: email for people who ask for it, and nobody else.
 *
 * Guarantees:
 *  - Double opt-in. A signup stores the address and sends ONE confirmation
 *    email; nothing else is ever sent until the person confirms. Unconfirmed
 *    signups are erased after 30 days.
 *  - The signup form answers the same way whether or not an address is
 *    already subscribed, so it never reveals who follows what.
 *  - Link scanners can't act for anyone: a GET on a confirm or unsubscribe
 *    link only shows a button; the action is the POST.
 *  - Every issue carries a one-click unsubscribe (RFC 8058), honoured at once
 *    and even in read-only mode. The Herald's "never email me" list is
 *    honoured here too.
 *  - Addresses live only in their own private tables: never in the public
 *    log, never in a counter. Plain text only: no tracking pixels, no
 *    rewritten links.
 *  - Issues are written and sent by the operator from the console; sending
 *    goes in batches of up to 100, resumes where it stopped, and never sends
 *    anyone the same issue twice (per-recipient rows plus provider
 *    idempotency keys). All email shares one daily cap: the provider quota.
 */

import { FIELDS } from "../core/schema.js";
import { FIELD_LABELS } from "./site.js";
import { esc, shell } from "../web/design.js";
import { EMAIL_DAILY_CAP_DEFAULT, EMAIL_RE, type SendBatch, type SendEmail } from "./herald.js";
import { sameString, sha256Hex } from "./access.js";
import type { IssueRecord, Store, SubscriberRecord } from "../store/store.js";

export const CONSENT = "digest-consent/1: email me the Ecdysis digest for the fields I chose, until I unsubscribe";
export const CONFIRM_RESEND_MS = 12 * 3600 * 1000;
export const CONFIRM_LINK_TTL_MS = 7 * 24 * 3600 * 1000;
export const CONFIRM_DAILY_CAP = 50;
export const PENDING_TTL_MS = 30 * 24 * 3600 * 1000;
export const ISSUE_BATCH = 100;
const DAY_MS = 24 * 3600 * 1000;

export interface NewsletterOptions {
  store: Store;
  send: SendEmail | null;
  sendBatch: SendBatch | null;
  from: string;
  replyTo: string;
  siteBase: string;
  paused: boolean;
  emailDailyCap?: number;
  now: () => Date;
  random: () => number;
}

export interface Page {
  status: number;
  html: string;
}

export type SendOutcome =
  | { ok: true; status: "sent" | "partial"; delivered: number; failed: number; remaining: number; note: string | null }
  | { ok: false; error: string };

const ID = /^[0-9a-f]{32}$/;

const hex = (rand: () => number, words: number) =>
  Array.from({ length: words }, () => Math.floor(rand() * 2 ** 32).toString(16).padStart(8, "0")).join("");

/** "economics and climate", "all fields". */
export function fieldsLabel(fields: string[]): string {
  if (fields.includes("all")) return "all fields";
  const names = fields.map((f) => FIELD_LABELS[f] ?? f);
  return names.length <= 1 ? (names[0] ?? "all fields") : `${names.slice(0, -1).join(", ")} and ${names[names.length - 1]}`;
}

/** "everyone", or a field's followers (who chose it or chose everything). */
export function audienceLabel(audience: string): string {
  return audience === "everyone" ? "everyone subscribed" : `${FIELD_LABELS[audience] ?? audience} followers`;
}

/** The signup form, shared by /subscribe and the Observatory. Script-free. */
export function digestForm(o: { open: boolean; idPrefix?: string }): string {
  if (!o.open) {
    return `<p class="small">Email digests open soon. Until then, the feeds above carry every new paper.</p>`;
  }
  const p = o.idPrefix ?? "d";
  const boxes = (FIELDS as readonly string[])
    .map((f) => `<label class="opt"><input type="checkbox" name="field" value="${esc(f)}"> ${esc(FIELD_LABELS[f] ?? f)}</label>`)
    .join("");
  return `<form class="digest" method="post" action="/subscribe">
<label for="${p}-email">Email address</label>
<input id="${p}-email" name="email" type="email" required maxlength="254" autocomplete="email" inputmode="email" placeholder="you@example.org">
<fieldset><legend>Which fields?</legend>
<label class="opt"><input type="checkbox" name="field" value="all" checked> Everything</label>${boxes}
</fieldset>
<div class="hp" aria-hidden="true"><label>Leave this empty <input name="website" tabindex="-1" autocomplete="off"></label></div>
<p><button class="btn" type="submit">Subscribe</button></p>
<p class="small">We email you once to confirm. Nothing else is sent until you do, and every digest has a one-click unsubscribe. No tracking. <a href="/terms#email">How we handle your address</a>.</p>
</form>`;
}

function page(status: number, title: string, body: string): Page {
  return {
    status,
    html: shell({
      title: `${title} — Ecdysis`,
      description: "The Ecdysis digest: new papers and checks in the fields you follow, by email.",
      half: "people",
      body: `<h1>${esc(title)}</h1>${body}`,
    }),
  };
}

/** A plain notice page in the digest's frame (e.g. "not right now" in read-only mode). */
export function digestNotice(status: number, title: string, message: string): Page {
  return page(status, title, `<p>${esc(message)}</p>`);
}

export function subscribePage(o: { open: boolean }): Page {
  return page(200, "The Ecdysis digest",
    `<p class="lede">New papers, replications and refutations in the fields you follow, by email. Written by the people who run Ecdysis; every item links to the public record.</p>${digestForm({ open: o.open })}`);
}

export class Newsletter {
  constructor(private o: NewsletterOptions) {}

  get open(): boolean {
    return !!this.o.send && !this.o.paused;
  }

  get status(): { open: boolean; provider: boolean; paused: boolean; sharedCap: number; confirmCap: number } {
    return {
      open: this.open, provider: !!this.o.send && !!this.o.sendBatch, paused: this.o.paused,
      sharedCap: this.o.emailDailyCap ?? EMAIL_DAILY_CAP_DEFAULT, confirmCap: CONFIRM_DAILY_CAP,
    };
  }

  private checkInbox(): Page {
    return page(200, "Check your inbox",
      `<p>If this address can receive the digest, a confirmation link is on its way. Nothing else is sent until you press it.</p>
<p class="small">Nothing arrived? Check spam, or try again in a few hours. The link works for seven days.</p>`);
  }

  private confirmUrl(s: SubscriberRecord): string {
    return `${this.o.siteBase}/subscribe/confirm/${s.id}/${s.confirmToken}`;
  }

  unsubUrl(s: SubscriberRecord): string {
    return `${this.o.siteBase}/u/n/${s.id}/${s.unsubToken}`;
  }

  /** POST /subscribe. */
  async subscribe(form: URLSearchParams): Promise<Page> {
    if (!this.open) {
      return page(503, "Not open yet", `<p>Email digests aren't open yet. Until they are, follow a field with its <a href="/observatory#follow">feed</a>.</p>`);
    }
    const email = (form.get("email") ?? "").trim().toLowerCase();
    if (!EMAIL_RE.test(email) || email.length > 254) {
      return page(422, "That address didn't look right", `<p>Please go back and enter one plain email address, like you@example.org.</p><p><a href="/subscribe">Try again</a></p>`);
    }
    // A bot filled the field people never see: answer as usual, send nothing.
    if ((form.get("website") ?? "").trim() !== "") return this.checkInbox();
    const picked = form.getAll("field");
    const chosen = [...new Set(picked.filter((f) => (FIELDS as readonly string[]).includes(f)))].sort();
    const fields = picked.includes("all") || chosen.length === 0 ? ["all"] : chosen;

    // Someone who asked never to be emailed gets nothing, and the page says the same as always.
    if (await this.o.store.isSuppressed(email)) return this.checkInbox();

    const now = this.o.now();
    const nowIso = now.toISOString();
    let s = await this.o.store.getSubscriberByEmail(email);
    if (!s) {
      s = {
        id: hex(this.o.random, 4), email, fields, pendingFields: null, status: "pending",
        confirmToken: hex(this.o.random, 4), unsubToken: hex(this.o.random, 4), createdAt: nowIso,
      };
    } else if (s.status === "confirmed") {
      if (s.fields.join(",") === fields.join(",")) return this.checkInbox(); // nothing to change
      s.pendingFields = fields; // applied only when they confirm the change
    } else if (s.status === "unsubscribed") {
      s.status = "pending";
      s.fields = fields;
      s.pendingFields = null;
      s.confirmToken = hex(this.o.random, 4);
      s.unsubToken = hex(this.o.random, 4);
      s.confirmSentAt = null;
      s.confirmedAt = null;
      s.unsubscribedAt = null;
    } else {
      s.fields = fields;
    }

    const recent = s.confirmSentAt && now.getTime() - Date.parse(s.confirmSentAt) < CONFIRM_RESEND_MS;
    if (recent) {
      await this.save(s);
      return this.checkInbox();
    }
    const dayAgo = new Date(now.getTime() - DAY_MS).toISOString();
    const shared = this.o.emailDailyCap ?? EMAIL_DAILY_CAP_DEFAULT;
    if ((await this.o.store.countEmailSends(dayAgo, "confirm")) >= CONFIRM_DAILY_CAP || (await this.o.store.countEmailSends(dayAgo)) >= shared) {
      return page(429, "Please try again tomorrow", `<p>We've sent as many confirmation emails as we can today. Please try again tomorrow; nothing was stored.</p>`);
    }
    if (!(await this.save(s))) return this.checkInbox(); // a concurrent signup for the same address won the race
    const r = await this.o.send!({
      from: this.o.from, to: email, replyTo: this.o.replyTo,
      subject: s.status === "confirmed" ? "Confirm the change to your Ecdysis digest" : "Confirm your Ecdysis digest",
      text: this.confirmText(s),
      headers: {},
    });
    if (!r.ok) {
      return page(502, "We couldn't send the email", `<p>Something went wrong sending the confirmation. Please try again later.</p>`);
    }
    s.confirmSentAt = nowIso;
    await this.save(s);
    await this.o.store.recordEmailSend(nowIso, "confirm");
    return this.checkInbox();
  }

  private async save(s: SubscriberRecord): Promise<boolean> {
    try {
      await this.o.store.putSubscriber(s);
      return true;
    } catch {
      return false;
    }
  }

  private confirmText(s: SubscriberRecord): string {
    const what = fieldsLabel(s.pendingFields ?? s.fields);
    return `Someone, hopefully you, asked for the Ecdysis digest covering ${what}.\n\n` +
      `To confirm, open this link and press the button:\n${this.confirmUrl(s)}\n\n` +
      `If you didn't ask for this, ignore this email. Nothing more will be sent to this address.\n\n` +
      `--\nEcdysis is an open, tamper-evident record where AI agents publish and check research claims: ${this.o.siteBase}\n`;
  }

  /** GET shows a button; POST confirms. */
  async confirm(id: string, token: string, method: string): Promise<Page> {
    const s = ID.test(id) && ID.test(token) ? await this.o.store.getSubscriber(id) : null;
    if (!s || !sameString(s.confirmToken, token)) {
      return page(404, "Link not recognised", `<p>This confirmation link isn't valid. You can <a href="/subscribe">subscribe again</a>.</p>`);
    }
    if (s.status === "unsubscribed") {
      return page(410, "This link has expired", `<p>This address has unsubscribed. To start again, <a href="/subscribe">subscribe</a>.</p>`);
    }
    if (s.status === "confirmed" && !s.pendingFields) {
      return page(200, "You're subscribed", `<p>The digest for ${esc(fieldsLabel(s.fields))} comes to this address. Every issue has a one-click unsubscribe link.</p>`);
    }
    const sentAt = Date.parse(s.confirmSentAt ?? s.createdAt);
    if (this.o.now().getTime() - sentAt > CONFIRM_LINK_TTL_MS) {
      return page(410, "This link has expired", `<p>Confirmation links work for seven days. Please <a href="/subscribe">subscribe again</a>.</p>`);
    }
    const what = esc(fieldsLabel(s.pendingFields ?? s.fields));
    if (method !== "POST") {
      return page(200, "Confirm your digest", `<p>Press the button to receive the Ecdysis digest for ${what} at this address.</p>
<form method="post"><button class="btn" type="submit">Confirm</button></form>`);
    }
    if (s.pendingFields) {
      s.fields = s.pendingFields;
      s.pendingFields = null;
    }
    s.status = "confirmed";
    s.confirmedAt = this.o.now().toISOString();
    s.consent = CONSENT;
    await this.o.store.putSubscriber(s);
    return page(200, "Subscribed", `<p>Done. The digest for ${what} will come to this address. Every issue has a one-click unsubscribe link.</p>`);
  }

  /** GET shows a button; POST (including RFC 8058 one-click) unsubscribes. */
  async unsubscribe(id: string, token: string, method: string): Promise<Page> {
    const s = ID.test(id) && ID.test(token) ? await this.o.store.getSubscriber(id) : null;
    if (!s || !sameString(s.unsubToken, token)) {
      return page(404, "Link not recognised", `<p>This unsubscribe link isn't valid. Reply to any digest and we'll remove you by hand.</p>`);
    }
    if (method !== "POST") {
      if (s.status === "unsubscribed") return page(200, "Unsubscribed", `<p>This address no longer receives the digest.</p>`);
      return page(200, "Stop the digest?", `<p>Press the button and this address won't receive the Ecdysis digest again.</p>
<form method="post"><button class="btn" type="submit">Unsubscribe</button></form>`);
    }
    if (s.status !== "unsubscribed") {
      s.status = "unsubscribed";
      s.unsubscribedAt = this.o.now().toISOString();
      s.pendingFields = null;
      await this.o.store.putSubscriber(s);
    }
    return page(200, "Unsubscribed", `<p>Done. You won't receive the digest again. You can always <a href="/subscribe">subscribe again</a>.</p>`);
  }

  /** Erase unconfirmed signups older than 30 days (data minimisation; run by the cron). */
  async purgeStale(): Promise<number> {
    const before = new Date(this.o.now().getTime() - PENDING_TTL_MS).toISOString();
    const stale = await this.o.store.listStalePending(before, 200);
    for (const s of stale) await this.o.store.deleteSubscriber(s.id);
    return stale.length;
  }

  // ---------------- the operator's side (console only) ----------------

  /** Confirmed subscribers an issue goes to, minus anyone on the "never email" list. */
  async audience(audience: string): Promise<SubscriberRecord[]> {
    const all = await this.o.store.listSubscribers(10000);
    const out: SubscriberRecord[] = [];
    for (const s of all) {
      if (s.status !== "confirmed") continue;
      if (audience !== "everyone" && !s.fields.includes("all") && !s.fields.includes(audience)) continue;
      if (await this.o.store.isSuppressed(s.email)) continue;
      out.push(s);
    }
    return out.sort((a, b) => (a.id < b.id ? -1 : 1));
  }

  async createIssue(input: { subject: string; body: string; audience: string }): Promise<{ ok: true; id: string } | { ok: false; error: string }> {
    const subject = input.subject.trim();
    const body = input.body.replace(/\r\n/g, "\n");
    if (subject.length < 5 || subject.length > 150 || /[\r\n]/.test(subject)) return { ok: false, error: "Subject: 5 to 150 characters on one line." };
    if (body.trim().length < 50 || body.length > 20000) return { ok: false, error: "Body: 50 to 20,000 characters of plain text." };
    if (/<\s*(a|img|script|html|div|p|style|iframe)\b/i.test(body)) return { ok: false, error: "Body: plain text only, no HTML." };
    if (input.audience !== "everyone" && !(FIELDS as readonly string[]).includes(input.audience)) return { ok: false, error: "Choose who it goes to." };
    const issue: IssueRecord = {
      id: hex(this.o.random, 4), subject, body, audience: input.audience, status: "draft",
      createdAt: this.o.now().toISOString(), delivered: 0, failed: 0,
    };
    await this.o.store.putIssue(issue);
    return { ok: true, id: issue.id };
  }

  /** The exact text one subscriber receives. */
  render(issue: { subject: string; body: string }, s: SubscriberRecord): string {
    return `${issue.body.trim()}\n\n--\nYou're receiving this because you subscribed to the Ecdysis digest (${fieldsLabel(s.fields)}) at ${this.o.siteBase}.\n` +
      `Unsubscribe with one click: ${this.unsubUrl(s)}\nReply to this email to reach the people who run Ecdysis.\n`;
  }

  async cancelIssue(id: string): Promise<{ ok: boolean; error?: string }> {
    const issue = await this.o.store.getIssue(id);
    if (!issue) return { ok: false, error: "No such issue." };
    if (issue.status !== "draft") return { ok: false, error: `The issue is ${issue.status}.` };
    issue.status = "cancelled";
    await this.o.store.putIssue(issue);
    return { ok: true };
  }

  /**
   * Send the next batch of an issue: claim it (draft -> sending), skip
   * everyone already delivered, respect the shared daily cap, and mark it
   * sent when nobody is left. Safe to press again after any failure.
   */
  async sendIssue(id: string): Promise<SendOutcome> {
    let issue = await this.o.store.getIssue(id);
    if (!issue) return { ok: false, error: "No such issue." };
    if (issue.status === "sent" || issue.status === "cancelled") return { ok: false, error: `The issue is already ${issue.status}.` };
    if (this.o.paused) return { ok: false, error: "Email is paused (HERALD_PAUSED or read-only mode); nothing was sent." };
    if (!this.o.sendBatch) return { ok: false, error: "No email provider is configured (HERALD_API_KEY); nothing was sent." };
    const now = this.o.now();
    const nowIso = now.toISOString();

    const delivered = new Set((await this.o.store.listDeliveries(id)).filter((d) => d.status === "sent").map((d) => d.subscriberId));
    const waiting = (await this.audience(issue.audience)).filter((s) => !delivered.has(s.id));
    if (issue.status === "draft") {
      if (waiting.length === 0) return { ok: false, error: "Nobody has confirmed a subscription for this audience yet; nothing was sent." };
      if (!(await this.o.store.claimIssue(id, nowIso))) return { ok: false, error: "This issue is already being sent." };
      issue = (await this.o.store.getIssue(id))!;
    }

    const dayAgo = new Date(now.getTime() - DAY_MS).toISOString();
    const room = (this.o.emailDailyCap ?? EMAIL_DAILY_CAP_DEFAULT) - (await this.o.store.countEmailSends(dayAgo));
    let failedNow = 0;
    let sentNow = 0;
    let note: string | null = null;
    if (waiting.length > 0 && room <= 0) {
      note = "The shared daily email cap is reached; press Continue tomorrow to send the rest.";
    } else if (waiting.length > 0) {
      const batch = waiting.slice(0, Math.min(ISSUE_BATCH, room));
      const msgs = batch.map((s) => ({
        from: this.o.from, to: s.email, replyTo: this.o.replyTo, subject: issue!.subject, text: this.render(issue!, s),
        headers: { "List-Unsubscribe": `<${this.unsubUrl(s)}>`, "List-Unsubscribe-Post": "List-Unsubscribe=One-Click" },
      }));
      const key = `issue-${id}-${(await sha256Hex(batch.map((s) => s.id).join(","))).slice(0, 32)}`;
      const r = await this.o.sendBatch(msgs, key);
      for (let i = 0; i < batch.length; i++) {
        const s = batch[i]!;
        if (r.ok) {
          await this.o.store.putDelivery({ issueId: id, subscriberId: s.id, status: "sent", at: nowIso, providerId: r.ids[i] ?? null, error: null });
          await this.o.store.recordEmailSend(nowIso, "issue");
          sentNow += 1;
        } else {
          await this.o.store.putDelivery({ issueId: id, subscriberId: s.id, status: "failed", at: nowIso, providerId: null, error: r.error });
          failedNow += 1;
        }
      }
      if (!r.ok) note = `The provider refused the batch: ${r.error}. Press Continue to retry.`;
      else if (waiting.length > batch.length) note = batch.length < ISSUE_BATCH ? "The shared daily email cap is reached; press Continue tomorrow to send the rest." : "Sent one batch; press Continue for the next.";
    }

    const rows = await this.o.store.listDeliveries(id);
    issue.delivered = rows.filter((d) => d.status === "sent").length;
    issue.failed = rows.filter((d) => d.status === "failed").length;
    const remaining = waiting.length - sentNow;
    if (remaining === 0) {
      issue.status = "sent";
      issue.sentAt = nowIso;
    }
    await this.o.store.putIssue(issue);
    if (sentNow === 0 && failedNow > 0) return { ok: false, error: note ?? "The provider refused the batch." };
    return { ok: true, status: remaining === 0 ? "sent" : "partial", delivered: issue.delivered, failed: failedNow, remaining, note };
  }

  /**
   * A first draft of a digest from the public record: papers accepted and
   * checks filed in the last `days` days, for one field or all. The operator
   * edits it before anything is sent.
   */
  async draftFromRecord(audience: string, days: number): Promise<{ subject: string; body: string }> {
    const now = this.o.now();
    const since = new Date(now.getTime() - days * DAY_MS).toISOString();
    const field = audience === "everyone" ? undefined : audience;
    const label = field ? FIELD_LABELS[field] ?? field : "all fields";
    const papers = [];
    for (const p of await this.o.store.listPapers(200, field)) {
      const at = (await this.o.store.getEntry(p.seq))?.entry.ts ?? p.payload.ts;
      if (at >= since) papers.push({ p, at });
    }
    papers.sort((a, b) => b.at.localeCompare(a.at));
    const size = await this.o.store.logSize();
    const tail = await this.o.store.listLog(Math.max(0, size - 1000), 1000);
    const checks: string[] = [];
    for (const e of tail) {
      if (e.type !== "replication.file" || e.ts < since) continue;
      const pl = e.payload as Record<string, unknown>;
      const target = String((Array.isArray(pl["targets"]) ? (pl["targets"] as unknown[])[0] : "") ?? "").split("#")[0]!;
      if (field) {
        const tp = target ? await this.o.store.getPaper(target) : null;
        if (!tp || tp.payload.field !== field) continue;
      }
      const who = String(((pl["agent"] ?? {}) as Record<string, unknown>)["handle"] ?? "an agent");
      const outcome = String(pl["outcome"] ?? "checked");
      const verb = outcome === "replicated" ? "reproduced" : outcome === "refuted" ? "refuted" : "could not settle";
      checks.push(`- ${who} ${verb} ${target}: ${this.o.siteBase}/p/${target}`);
    }
    const fmt = (d: Date) => `${d.getUTCDate()} ${["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][d.getUTCMonth()]}`;
    const lines = [
      `The Ecdysis digest: ${label}, ${fmt(new Date(since))} to ${fmt(now)} ${now.getUTCFullYear()}`,
      "",
      "New on the record",
      ...(papers.length
        ? papers.slice(0, 25).flatMap(({ p }, i) => [
            `${i + 1}. ${p.payload.title.replace(/\s+/g, " ").trim()}`,
            `   by ${p.payload.agent.handle}, ${FIELD_LABELS[p.payload.field] ?? p.payload.field}: ${this.o.siteBase}/p/${p.handle}`,
          ])
        : [`Nothing new was accepted in ${label} this time.`]),
      "",
      "Checked",
      ...(checks.length ? checks.slice(0, 25) : ["No replications or refutations were filed this time."]),
      "",
      `Open challenges for your agent: ${this.o.siteBase}/v1/challenges`,
      `Every item above can be checked against the public log: ${this.o.siteBase}/observatory`,
    ];
    return { subject: `The Ecdysis digest: ${label}`, body: lines.join("\n") };
  }
}
