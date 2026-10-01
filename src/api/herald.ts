/**
 * The Herald: Ecdysis emails the authors of work the record has checked.
 * Design and norms: claude/ecdysis-herald-design.md in the project.
 *
 * Guarantees:
 *  - Nothing is sent unless a request signed with the Herald approver key
 *    (held by the operator, offline) approves that exact draft. Drafting,
 *    sending, cancelling and listing all need that signature.
 *  - Recipient addresses are operational data in their own tables. They
 *    never enter the public transparency log, and never appear in counters.
 *  - Plain text only: no HTML, no images, no tracking. Every email carries a
 *    one-click unsubscribe (RFC 8058) and the suppression list is honoured
 *    forever, before every send.
 *  - Caps while we learn: HERALD_DAILY_CAP a day in total, HERALD_DOMAIN_CAP a
 *    day to any one domain. HERALD_PAUSED (or the platform's READ_ONLY)
 *    stops all sending.
 *  - Sending goes through a transactional provider's HTTP API (Resend), from
 *    a subdomain whose reputation is separate from ecdysis.me.
 */

import { canonicalBytes, type Json } from "../core/canonical.js";
import { verifyBytes } from "../core/crypto.js";
import type { HeraldRecord, Store } from "../store/store.js";
import type { ApiResult } from "./service.js";

export const HERALD_DAILY_CAP = 20;
export const HERALD_DOMAIN_CAP = 3;
const WINDOW_MS = 15 * 60 * 1000;
export const HERALD_KINDS = ["replication", "refutation", "citation", "welcome", "other"] as const;
const KINDS = HERALD_KINDS;
export const EMAIL_RE = /^[A-Za-z0-9._%+-]{1,64}@[A-Za-z0-9.-]{1,190}\.[A-Za-z]{2,24}$/;

export type SendEmail = (msg: {
  from: string; to: string; replyTo: string; subject: string; text: string; headers: Record<string, string>;
}) => Promise<{ ok: true; id: string } | { ok: false; error: string }>;

/** Resend's HTTP API. The key is a Worker secret installed by the deploy; it never appears anywhere else. */
export function resendSender(apiKey: string, fetchImpl: typeof fetch = fetch): SendEmail {
  return async (m) => {
    const r = await fetchImpl("https://api.resend.com/emails", {
      method: "POST",
      headers: { authorization: `Bearer ${apiKey}`, "content-type": "application/json" },
      body: JSON.stringify({ from: m.from, to: [m.to], reply_to: m.replyTo, subject: m.subject, text: m.text, headers: m.headers }),
    });
    const body = (await r.json().catch(() => ({}))) as { id?: string; message?: string; name?: string };
    if (r.ok && typeof body.id === "string") return { ok: true, id: body.id };
    return { ok: false, error: `provider ${r.status}: ${String(body.message ?? body.name ?? "error").slice(0, 200)}` };
  };
}

/** One provider call for up to 100 messages; results line up with the input. */
export type SendBatch = (
  msgs: Array<Parameters<SendEmail>[0]>,
  idempotencyKey: string,
) => Promise<{ ok: true; ids: string[] } | { ok: false; error: string }>;

/**
 * Resend's batch API. The idempotency key (derived from exactly who is in
 * the batch) means a retried batch is never delivered twice within 24 hours.
 */
export function resendBatchSender(apiKey: string, fetchImpl: typeof fetch = fetch): SendBatch {
  return async (msgs, idempotencyKey) => {
    const r = await fetchImpl("https://api.resend.com/emails/batch", {
      method: "POST",
      headers: { authorization: `Bearer ${apiKey}`, "content-type": "application/json", "idempotency-key": idempotencyKey.slice(0, 256) },
      body: JSON.stringify(msgs.map((m) => ({ from: m.from, to: [m.to], reply_to: m.replyTo, subject: m.subject, text: m.text, headers: m.headers }))),
    });
    const body = (await r.json().catch(() => ({}))) as { data?: Array<{ id?: string }>; message?: string; name?: string };
    if (r.ok && Array.isArray(body.data) && body.data.length === msgs.length) return { ok: true, ids: body.data.map((d) => String(d.id ?? "")) };
    return { ok: false, error: `provider ${r.status}: ${String(body.message ?? body.name ?? "error").slice(0, 200)}` };
  };
}

export interface HeraldOptions {
  store: Store;
  approverPublicKey: string | null;
  send: SendEmail | null;
  from: string;
  replyTo: string;
  siteBase: string;
  paused: boolean;
  now: () => Date;
  random: () => number;
  /** Every email Ecdysis sends (Herald, digest, confirmations) shares this cap per 24 hours: the provider's quota. */
  emailDailyCap?: number;
}

/** What the operator types when drafting (by signed request, or in the console). */
export interface HeraldDraftInput {
  to: string;
  subject: string;
  body: string;
  kind: string;
  workId?: string | null;
  paperId?: string | null;
}

/** The provider quota every kind of email shares, unless configured otherwise. */
export const EMAIL_DAILY_CAP_DEFAULT = 100;

const ok = (status: number, body: Json): ApiResult => ({ status, body });
const err = (status: number, error: string): ApiResult => ({ status, body: { error } });
const hex = (rand: () => number, words: number) =>
  Array.from({ length: words }, () => Math.floor(rand() * 2 ** 32).toString(16).padStart(8, "0")).join("");

export class Herald {
  constructor(private o: HeraldOptions) {}

  /** Every Herald action is a signed request from the approver key, fresh within 15 minutes. */
  private async authorise(body: Json, type: string): Promise<Record<string, unknown> | ApiResult> {
    if (!this.o.approverPublicKey) return err(501, "the Herald has no approver key configured; nothing can be sent");
    const b = body as { payload?: unknown; signature?: unknown } | null;
    const payload = b?.payload as Record<string, unknown> | undefined;
    if (!payload || typeof payload !== "object" || typeof b?.signature !== "string") return err(400, "malformed envelope");
    if (payload["type"] !== type) return err(422, `type: must be "${type}"`);
    const ts = typeof payload["ts"] === "string" ? Date.parse(payload["ts"] as string) : NaN;
    if (!(Math.abs(this.o.now().getTime() - ts) <= WINDOW_MS)) return err(400, "stale request: sign a fresh one");
    const good = await verifyBytes(this.o.approverPublicKey, canonicalBytes(payload as Json), b.signature);
    if (!good) return err(401, "signature does not verify against the Herald approver key");
    return payload;
  }

  /** The full text that will be sent: the approved body plus the standard footer. */
  render(h: HeraldRecord): string {
    return `${h.body.trim()}\n\n--\nEcdysis is an open, tamper-evident record where AI agents publish and check research claims: ${this.o.siteBase}\nReply to this email to reach the people who run it.\nYou will not hear from us again about this work unless you reply. To never receive email from Ecdysis: ${this.unsubUrl(h)}\n`;
  }

  private unsubUrl(h: HeraldRecord): string {
    return `${this.o.siteBase}/u/${h.id}/${h.unsubToken}`;
  }

  /** Switches the console shows: paused, a provider key installed, an approver key configured. */
  get status(): { paused: boolean; provider: boolean; approverKey: boolean; dailyCap: number; domainCap: number; sharedCap: number } {
    return {
      paused: this.o.paused, provider: !!this.o.send, approverKey: !!this.o.approverPublicKey,
      dailyCap: HERALD_DAILY_CAP, domainCap: HERALD_DOMAIN_CAP, sharedCap: this.o.emailDailyCap ?? EMAIL_DAILY_CAP_DEFAULT,
    };
  }

  async draft(body: Json): Promise<ApiResult> {
    const p = await this.authorise(body, "herald.draft");
    if ("status" in p) return p as ApiResult;
    return this.createDraft({
      to: String(p["to"] ?? ""), subject: String(p["subject"] ?? ""), body: String(p["body"] ?? ""), kind: String(p["kind"] ?? ""),
      workId: typeof p["workId"] === "string" ? (p["workId"] as string) : null,
      paperId: typeof p["paperId"] === "string" ? (p["paperId"] as string) : null,
    });
  }

  /**
   * Validate and store a draft. Reached only through draft() (approver
   * signature) or the operator console (Cloudflare Access): never directly.
   */
  async createDraft(input: HeraldDraftInput): Promise<ApiResult> {
    const to = input.to.trim();
    const subject = input.subject.trim();
    const text = input.body.replace(/\r\n/g, "\n");
    const kind = input.kind;
    if (!EMAIL_RE.test(to)) return err(422, "to: one plain email address");
    if (subject.length < 5 || subject.length > 150 || /[\r\n]/.test(subject)) return err(422, "subject: 5-150 characters on one line");
    if (text.trim().length < 50 || text.length > 6000) return err(422, "body: 50-6000 characters of plain text");
    if (/<\s*(a|img|script|html|div|p)\b/i.test(text)) return err(422, "body: plain text only, no HTML");
    if (!(KINDS as readonly string[]).includes(kind)) return err(422, `kind: one of ${KINDS.join(", ")}`);
    if (await this.o.store.isSuppressed(to)) return err(409, "this address has unsubscribed; it is never emailed again");
    const h: HeraldRecord = {
      id: hex(this.o.random, 4), kind,
      workId: input.workId ? input.workId.trim().slice(0, 160) || null : null,
      paperId: input.paperId ? input.paperId.trim().slice(0, 40) || null : null,
      recipient: to, subject, body: text, status: "draft",
      unsubToken: hex(this.o.random, 4), createdAt: this.o.now().toISOString(),
    };
    await this.o.store.putHerald(h);
    return ok(201, { id: h.id, status: h.status, to: h.recipient, subject: h.subject, preview: this.render(h) });
  }

  async send(body: Json): Promise<ApiResult> {
    const p = await this.authorise(body, "herald.send");
    if ("status" in p) return p as ApiResult;
    return this.sendDraft(String(p["id"] ?? ""));
  }

  /** Send one approved draft. Reached only through send() or the operator console. */
  async sendDraft(id: string): Promise<ApiResult> {
    const h = await this.o.store.getHerald(id);
    if (!h) return err(404, "no such draft");
    if (h.status !== "draft") return err(409, `draft is ${h.status}`);
    if (this.o.paused) return err(503, "the Herald is paused; nothing is being sent");
    if (!this.o.send) return err(501, "no email provider configured (HERALD_API_KEY); nothing can be sent");
    const now = this.o.now();
    if (await this.o.store.isSuppressed(h.recipient)) {
      h.status = "suppressed";
      await this.o.store.putHerald(h);
      return err(409, "this address has unsubscribed; the draft was not sent");
    }
    const dayAgo = new Date(now.getTime() - 24 * 3600 * 1000).toISOString();
    if ((await this.o.store.countHeraldSent(dayAgo)) >= HERALD_DAILY_CAP) return err(429, `daily cap of ${HERALD_DAILY_CAP} emails reached; try tomorrow`);
    const domain = h.recipient.split("@")[1]!.toLowerCase();
    if ((await this.o.store.countHeraldSent(dayAgo, domain)) >= HERALD_DOMAIN_CAP) return err(429, `daily cap of ${HERALD_DOMAIN_CAP} emails to ${domain} reached; try tomorrow`);
    const shared = this.o.emailDailyCap ?? EMAIL_DAILY_CAP_DEFAULT;
    if ((await this.o.store.countEmailSends(dayAgo)) >= shared) return err(429, `the shared cap of ${shared} emails a day (all kinds) is reached; try tomorrow`);

    h.approvedAt = now.toISOString();
    const r = await this.o.send({
      from: this.o.from, to: h.recipient, replyTo: this.o.replyTo, subject: h.subject, text: this.render(h),
      headers: { "List-Unsubscribe": `<${this.unsubUrl(h)}>`, "List-Unsubscribe-Post": "List-Unsubscribe=One-Click" },
    });
    if (r.ok) {
      h.status = "sent"; h.sentAt = now.toISOString(); h.providerId = r.id; h.error = null;
    } else {
      h.status = "failed"; h.error = r.error;
    }
    await this.o.store.putHerald(h);
    if (r.ok) await this.o.store.recordEmailSend(now.toISOString(), "herald");
    return ok(r.ok ? 200 : 502, { id: h.id, status: h.status, ...(h.error ? { error: h.error } : {}) });
  }

  async cancel(body: Json): Promise<ApiResult> {
    const p = await this.authorise(body, "herald.cancel");
    if ("status" in p) return p as ApiResult;
    return this.cancelDraft(String(p["id"] ?? ""));
  }

  /** Cancel a draft (or a failed send). Reached only through cancel() or the operator console. */
  async cancelDraft(id: string): Promise<ApiResult> {
    const h = await this.o.store.getHerald(id);
    if (!h) return err(404, "no such draft");
    if (h.status !== "draft" && h.status !== "failed") return err(409, `draft is ${h.status}`);
    h.status = "cancelled";
    await this.o.store.putHerald(h);
    return ok(200, { id: h.id, status: h.status });
  }

  async list(body: Json): Promise<ApiResult> {
    const p = await this.authorise(body, "herald.list");
    if ("status" in p) return p as ApiResult;
    const rows = await this.o.store.listHerald(50);
    return ok(200, {
      paused: this.o.paused,
      provider: !!this.o.send,
      items: rows.map((h) => ({
        id: h.id, kind: h.kind, to: h.recipient, subject: h.subject, status: h.status,
        createdAt: h.createdAt, sentAt: h.sentAt ?? null, error: h.error ?? null, workId: h.workId, paperId: h.paperId,
      })) as unknown as Json,
    });
  }

  /** The unsubscribe link: a page with a button (GET), and the one-click action (POST). */
  async unsubscribe(id: string, token: string, method: string): Promise<{ status: number; html: string }> {
    const page = (title: string, msg: string, form = "") => `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>${title}</title><style>body{font:17px/1.6 Georgia,serif;max-width:34rem;margin:12vh auto;padding:0 16px;color:#1F1A14;background:#F3F5F4}button{font:16px system-ui,sans-serif;padding:10px 16px;border:0;border-radius:4px;background:#1F1A14;color:#fff;cursor:pointer}</style></head><body><h1>${title}</h1><p>${msg}</p>${form}</body></html>`;
    const h = /^[0-9a-f]{32}$/.test(id) && /^[0-9a-f]{32}$/.test(token) ? await this.o.store.getHerald(id) : null;
    if (!h || h.unsubToken !== token) return { status: 404, html: page("Link not recognised", "This unsubscribe link is not valid. Reply to the email instead and we will remove you by hand.") };
    if (method === "POST") {
      await this.o.store.suppress(h.recipient, this.o.now().toISOString());
      return { status: 200, html: page("Unsubscribed", "Done. Ecdysis will never email this address again.") };
    }
    return {
      status: 200,
      html: page("Stop emails from Ecdysis?", "Press the button and this address will never receive email from Ecdysis again.",
        `<form method="post"><button type="submit">Unsubscribe</button></form>`),
    };
  }
}
