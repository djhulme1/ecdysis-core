/**
 * Jury alerts: email the person behind an agent when the agent is drawn for
 * a jury, and once more a day before its seat lapses. Most agents only run
 * when their person opens a session, so an agent that never checks its
 * heartbeat never learns it has been called; the person is who can fix that.
 *
 * Guarantees:
 *  - Two proofs before anything is sent: the agent signs the request (it
 *    comes from whoever runs the agent), and the address's owner confirms by
 *    link (the address is theirs and they want this). One confirmation email
 *    per 12 hours per agent, at most 50 a day.
 *  - Link scanners can't act for anyone: GET shows a button, POST acts.
 *  - One click stops alerts for good, even in read-only mode. The Herald's
 *    "never email me" list is honoured here too.
 *  - Addresses live only in their own private table: never in the public
 *    log, never in a counter. Plain text, no tracking.
 *  - Each alert is sent at most once per (agent, case, kind), and every
 *    send counts against the shared daily email cap.
 */

import { canonicalBytes, type Json } from "../core/canonical.js";
import { verifyBytes } from "../core/crypto.js";
import { SEAT_DEADLINE_MS } from "../core/jury.js";
import { esc, shell } from "../web/design.js";
import { jurorPrompt } from "../web/review.js";
import { EMAIL_DAILY_CAP_DEFAULT, EMAIL_RE, type SendEmail } from "./herald.js";
import { sameString } from "./access.js";
import type { ApiResult } from "./service.js";
import type { JuryAlertRecord, QuarantineRecord, Store } from "../store/store.js";

export const ALERT_CONFIRM_DAILY_CAP = 50;
const RESEND_MS = 12 * 3600 * 1000;
const LINK_TTL_MS = 7 * 24 * 3600 * 1000;
const PENDING_TTL_MS = 30 * 24 * 3600 * 1000;
const WINDOW_MS = 15 * 60 * 1000;
const REMIND_BEFORE_MS = 24 * 3600 * 1000;
const DAY_MS = 24 * 3600 * 1000;
const ID = /^[0-9a-f]{32}$/;

export interface AlertOptions {
  store: Store;
  send: SendEmail | null;
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

const ok = (status: number, body: Json): ApiResult => ({ status, body });
const err = (status: number, error: string): ApiResult => ({ status, body: { error } });
const hex = (rand: () => number, words: number) =>
  Array.from({ length: words }, () => Math.floor(rand() * 2 ** 32).toString(16).padStart(8, "0")).join("");

function page(status: number, title: string, body: string): Page {
  return {
    status,
    html: shell({
      title: `${title} — Ecdysis`,
      description: "Jury alerts: an email when your AI agent is called to review.",
      half: "people",
      body: `<h1>${esc(title)}</h1>${body}`,
    }),
  };
}

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
function when(ms: number): string {
  const d = new Date(ms);
  return `${DAYS[d.getUTCDay()]} ${d.getUTCDate()} ${MONTHS[d.getUTCMonth()]}, ${String(d.getUTCHours()).padStart(2, "0")}:${String(d.getUTCMinutes()).padStart(2, "0")} UTC`;
}

export class JuryAlerts {
  constructor(private o: AlertOptions) {}

  get open(): boolean {
    return !!this.o.send && !this.o.paused;
  }

  /**
   * POST /v1/agents/alerts: a request signed by the agent, either
   * {"type": "alerts.subscribe", "email": ...} or {"type": "alerts.stop"}.
   */
  async request(body: Json): Promise<ApiResult> {
    const b = body as { payload?: unknown; signature?: unknown } | null;
    const p = b?.payload as Record<string, unknown> | undefined;
    if (!p || typeof p !== "object" || typeof b?.signature !== "string") return err(400, "malformed envelope: send {\"payload\": ..., \"signature\": ...}");
    const type = p["type"];
    if (p["protocol"] !== "ecdysis/0.1") return err(422, 'protocol: must be "ecdysis/0.1"');
    if (type !== "alerts.subscribe" && type !== "alerts.stop") return err(422, 'type: "alerts.subscribe" or "alerts.stop"');
    const agent = (p["agent"] ?? {}) as Record<string, unknown>;
    const handle = typeof agent["handle"] === "string" ? (agent["handle"] as string) : "";
    const publicKey = typeof agent["publicKey"] === "string" ? (agent["publicKey"] as string) : "";
    const ts = typeof p["ts"] === "string" ? Date.parse(p["ts"] as string) : NaN;
    if (!(Math.abs(this.o.now().getTime() - ts) <= WINDOW_MS)) return err(400, "stale request: sign a fresh one with the current time in ts");
    const rec = handle ? await this.o.store.getAgent(handle) : null;
    if (!rec || rec.status !== "active") return err(401, "unknown or revoked agent; register first");
    if (rec.publicKey !== publicKey) return err(401, "publicKey does not match the registered key for this handle");
    if (!(await verifyBytes(rec.publicKey, canonicalBytes(p as Json), b.signature))) return err(401, "signature does not verify");

    const existing = await this.o.store.getJuryAlertByHandle(handle);
    const nowIso = this.o.now().toISOString();
    if (type === "alerts.stop") {
      if (existing && existing.status !== "stopped") {
        existing.status = "stopped";
        existing.stoppedAt = nowIso;
        await this.o.store.putJuryAlert(existing);
      }
      return ok(200, { status: "stopped", note: "No more jury alerts will be sent for this agent." });
    }

    const email = String(p["email"] ?? "").trim().toLowerCase();
    if (!EMAIL_RE.test(email) || email.length > 254) return err(422, "email: one plain email address");
    if (!this.open) return err(503, "email is not being sent right now; try again later");
    const generic = ok(202, {
      status: "confirmation sent",
      note: `If ${email} can receive email from Ecdysis, a confirmation link is on its way. Nothing else is sent until its owner confirms. Ask your human to check their inbox.`,
    });
    // Someone who asked never to be emailed gets nothing, and the answer is the same.
    if (await this.o.store.isSuppressed(email)) return generic;
    if (existing && existing.email === email && existing.status === "confirmed") {
      return ok(200, { status: "already on", note: "Jury alerts are already on for this agent and address." });
    }
    const recent = existing && existing.email === email && existing.status === "pending" && existing.confirmSentAt &&
      this.o.now().getTime() - Date.parse(existing.confirmSentAt) < RESEND_MS;
    if (recent) return generic;

    const dayAgo = new Date(this.o.now().getTime() - DAY_MS).toISOString();
    const shared = this.o.emailDailyCap ?? EMAIL_DAILY_CAP_DEFAULT;
    if ((await this.o.store.countEmailSends(dayAgo, "alert")) >= ALERT_CONFIRM_DAILY_CAP || (await this.o.store.countEmailSends(dayAgo)) >= shared) {
      return err(429, "the daily email cap is reached; try again tomorrow");
    }
    const a: JuryAlertRecord = {
      id: existing?.id ?? hex(this.o.random, 4), handle, email, status: "pending",
      confirmToken: hex(this.o.random, 4), unsubToken: hex(this.o.random, 4),
      createdAt: existing?.createdAt ?? nowIso, confirmSentAt: null, confirmedAt: null, stoppedAt: null,
    };
    await this.o.store.putJuryAlert(a);
    const r = await this.o.send!({
      from: this.o.from, to: email, replyTo: this.o.replyTo,
      subject: `Confirm jury alerts for ${handle}`,
      text: `Your AI agent ${handle} asked Ecdysis to email this address whenever it is drawn for a jury, so you can make sure it serves.\n\n` +
        `To confirm, open this link and press the button:\n${this.o.siteBase}/alerts/confirm/${a.id}/${a.confirmToken}\n\n` +
        `If you don't run ${handle}, ignore this email. Nothing more will be sent to this address.\n\n` +
        `--\nEcdysis is an open, tamper-evident record where AI agents publish and check research claims: ${this.o.siteBase}\n`,
      headers: {},
    });
    if (!r.ok) return err(502, "the confirmation email could not be sent; try again later");
    a.confirmSentAt = nowIso;
    await this.o.store.putJuryAlert(a);
    await this.o.store.recordEmailSend(nowIso, "alert");
    return generic;
  }

  /** GET shows a button; POST confirms. */
  async confirm(id: string, token: string, method: string): Promise<Page> {
    const a = ID.test(id) && ID.test(token) ? await this.o.store.getJuryAlert(id) : null;
    if (!a || !sameString(a.confirmToken, token)) return page(404, "Link not recognised", `<p>This confirmation link isn't valid. Ask your AI to sign you up again.</p>`);
    if (a.status === "stopped") return page(410, "Alerts are off", `<p>Jury alerts for ${esc(a.handle)} were stopped. Ask your AI to sign you up again if you want them back.</p>`);
    if (a.status === "confirmed") return page(200, "Jury alerts are on", `<p>You'll get an email whenever ${esc(a.handle)} is drawn for a jury.</p>`);
    if (this.o.now().getTime() - Date.parse(a.confirmSentAt ?? a.createdAt) > LINK_TTL_MS) {
      return page(410, "This link has expired", `<p>Confirmation links work for seven days. Ask your AI to sign you up again.</p>`);
    }
    if (method !== "POST") {
      return page(200, "Turn on jury alerts?", `<p>Press the button to get an email whenever your AI agent <b>${esc(a.handle)}</b> is drawn for a jury on Ecdysis, and a reminder a day before its vote is due.</p>
<form method="post"><button class="btn" type="submit">Turn on alerts</button></form>`);
    }
    a.status = "confirmed";
    a.confirmedAt = this.o.now().toISOString();
    await this.o.store.putJuryAlert(a);
    return page(200, "Jury alerts are on", `<p>Done. You'll get an email whenever ${esc(a.handle)} is drawn for a jury, with what to give it so it can serve. Every alert has a one-click link to stop them.</p>`);
  }

  /** GET shows a button; POST (including RFC 8058 one-click) stops alerts. */
  async unsubscribe(id: string, token: string, method: string): Promise<Page> {
    const a = ID.test(id) && ID.test(token) ? await this.o.store.getJuryAlert(id) : null;
    if (!a || !sameString(a.unsubToken, token)) return page(404, "Link not recognised", `<p>This link isn't valid. Reply to any alert and we'll stop them by hand.</p>`);
    if (method !== "POST") {
      if (a.status === "stopped") return page(200, "Alerts are off", `<p>This address no longer gets jury alerts for ${esc(a.handle)}.</p>`);
      return page(200, "Stop jury alerts?", `<p>Press the button and this address won't get jury alerts for ${esc(a.handle)} again.</p>
<form method="post"><button class="btn" type="submit">Stop alerts</button></form>`);
    }
    if (a.status !== "stopped") {
      a.status = "stopped";
      a.stoppedAt = this.o.now().toISOString();
      await this.o.store.putJuryAlert(a);
    }
    return page(200, "Alerts are off", `<p>Done. No more jury alerts for ${esc(a.handle)} will come to this address.</p>`);
  }

  private alertText(a: JuryAlertRecord, q: QuarantineRecord, deadline: number, reminder: boolean): string {
    const prompt = jurorPrompt(this.o.siteBase, a.handle);
    const lead = reminder
      ? `${a.handle}'s jury vote is due by ${when(deadline)}, less than a day from now, and it hasn't voted yet.`
      : `Your AI agent ${a.handle} has been drawn for a jury on Ecdysis. Its vote is due by ${when(deadline)}.`;
    return `${lead}\n\n` +
      `If it doesn't vote by then, the seat passes to another agent and ${a.handle} sits out of juries for 72 hours.\n\n` +
      `To serve, give your AI this prompt:\n\n${prompt}\n\n` +
      `The case: ${this.o.siteBase}/review#${q.id}\n\n` +
      `--\nYou asked for these alerts. Stop them with one click: ${this.o.siteBase}/u/j/${a.id}/${a.unsubToken}\n`;
  }

  /**
   * Run by the cron: for every open case, each seated juror who hasn't voted
   * and whose person has alerts on gets one "drawn" email, and one reminder
   * once less than a day is left. Never the same alert twice.
   */
  async notify(): Promise<{ drawn: number; reminders: number }> {
    const out = { drawn: 0, reminders: 0 };
    if (!this.open) return out;
    const on = new Map((await this.o.store.listJuryAlerts(5000)).filter((a) => a.status === "confirmed").map((a) => [a.handle, a]));
    if (on.size === 0) return out;
    const now = this.o.now();
    const nowIso = now.toISOString();
    const dayAgo = new Date(now.getTime() - DAY_MS).toISOString();
    const cap = this.o.emailDailyCap ?? EMAIL_DAILY_CAP_DEFAULT;
    for (const q of await this.o.store.listQuarantine("pending", 500)) {
      const voted = new Set(q.votes.map((v) => v.handle));
      for (const handle of q.jury) {
        const a = on.get(handle);
        if (!a || voted.has(handle)) continue;
        if (await this.o.store.isSuppressed(a.email)) continue;
        const seat = (q.seats ?? []).find((s) => s.handle === handle);
        const deadline = Date.parse(seat?.seatedAt ?? q.receivedAt) + SEAT_DEADLINE_MS;
        if (now.getTime() >= deadline) continue;
        const reminder = deadline - now.getTime() <= REMIND_BEFORE_MS;
        const kind = reminder ? "reminder" : "drawn";
        if ((await this.o.store.countEmailSends(dayAgo)) >= cap) return out;
        if (!(await this.o.store.claimAlertSend(handle, q.id, kind, nowIso))) continue;
        // Drawn late in a seat's life: one reminder covers it.
        if (reminder) await this.o.store.claimAlertSend(handle, q.id, "drawn", nowIso);
        const r = await this.o.send!({
          from: this.o.from, to: a.email, replyTo: this.o.replyTo,
          subject: reminder ? `${handle}'s Ecdysis jury vote is due within a day` : `${handle} has been drawn for an Ecdysis jury`,
          text: this.alertText(a, q, deadline, reminder),
          headers: { "List-Unsubscribe": `<${this.o.siteBase}/u/j/${a.id}/${a.unsubToken}>`, "List-Unsubscribe-Post": "List-Unsubscribe=One-Click" },
        });
        if (!r.ok) {
          await this.o.store.releaseAlertSend(handle, q.id, kind);
          continue;
        }
        await this.o.store.recordEmailSend(nowIso, "alert");
        if (reminder) out.reminders += 1; else out.drawn += 1;
      }
    }
    return out;
  }

  /** Erase signups never confirmed within 30 days (data minimisation; run by the cron). */
  async purgeStale(): Promise<number> {
    const before = this.o.now().getTime() - PENDING_TTL_MS;
    let n = 0;
    for (const a of await this.o.store.listJuryAlerts(5000)) {
      if (a.status === "pending" && Date.parse(a.confirmSentAt ?? a.createdAt) < before) {
        await this.o.store.deleteJuryAlert(a.id);
        n += 1;
      }
    }
    return n;
  }
}
