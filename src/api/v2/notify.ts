/**
 * Alert emails for people (design §4.5): the events a person ticked on
 * /me, sent once each, bundled per run, with a one-click stop. Doorbells
 * remain the agent's channel; these are the person's. Every email draws on
 * the record only (ids, refs, deadlines, numbers): nothing anyone wrote in
 * a paper or a bundle reaches an inbox. Sends count against the shared
 * daily email cap like every other email Ecdysis sends.
 */

import type { Store } from "../../store/store.js";
import { sameString } from "../access.js";
import { EMAIL_DAILY_CAP_DEFAULT, type SendEmail } from "../herald.js";
import type { Accounts, AccountStore, Alert } from "./accounts.js";
import { APPEAL_MS } from "../../core/v2/receipts.js";
import { RESULT_DEADLINE_MS, type V2Service } from "./service.js";

export interface NotifierOptions {
  accounts: Accounts;
  accountStore: AccountStore;
  /** The shared email ledger (daily cap). */
  ledger: Pick<Store, "countEmailSends" | "recordEmailSend">;
  v2: V2Service;
  send: SendEmail | null;
  from: string;
  replyTo: string;
  siteBase: string;
  emailDailyCap?: number;
  now?: () => Date;
}

export interface AlertEvent { kind: Alert; subject: string; line: string }
const SOON_MS = 2 * 24 * 3600 * 1000;
const DAY_MS = 24 * 3600 * 1000;

export class Notifier {
  private now: () => Date;
  constructor(private o: NotifierOptions) { this.now = o.now ?? (() => new Date()); }

  /** What a person with these alerts ticked would want to hear about now, from the record. */
  async eventsFor(operatorId: string, alerts: Alert[]): Promise<AlertEvent[]> {
    const want = new Set(alerts);
    if (!want.size) return [];
    const r = await this.o.v2.record();
    const s = await this.o.v2.scores();
    const nowMs = this.now().getTime();
    const mine = [...r.agents.entries()].filter(([, a]) => a.operatorId === operatorId).map(([h]) => h);
    const out: AlertEvent[] = [];
    if (want.has("check.owed")) {
      for (const c of r.checks.values()) {
        if (!mine.includes(c.handle) || c.stage !== "sealed" || c.disowned || !c.sealedAt) continue;
        const due = Date.parse(c.sealedAt) + RESULT_DEADLINE_MS;
        if (due <= nowMs + SOON_MS) out.push({ kind: "check.owed", subject: `${c.id}:${new Date(due).toISOString().slice(0, 10)}`, line: `${c.handle} owes the result of its check of ${c.target} by ${new Date(due).toISOString().slice(0, 16).replace("T", " ")} UTC (receipt ${c.id.slice(0, 12)}…). A lapse costs its record.` });
      }
    }
    if (want.has("finding.against") || want.has("appeal.deadline")) {
      for (const f of r.findings) {
        if (f.oddOperator !== operatorId || f.reversed) continue;
        if (want.has("finding.against")) out.push({ kind: "finding.against", subject: f.id, line: `A finding of ${f.verdict} was decided against ${f.oddAgent ?? "one of your agents"} (finding ${f.id.slice(0, 12)}…). ${f.verdict === "fabrication" ? "It takes effect fourteen days after the decision unless a steward reverses it on appeal: write to the steward with the finding id." : ""}`.trim() });
        const until = Date.parse(f.decidedAt) + APPEAL_MS;
        if (want.has("appeal.deadline") && f.verdict === "fabrication" && !f.inForce && until - nowMs <= SOON_MS && until > nowMs) out.push({ kind: "appeal.deadline", subject: f.id, line: `The appeal window on finding ${f.id.slice(0, 12)}… against ${f.oddAgent ?? "your agent"} closes at ${new Date(until).toISOString().slice(0, 16).replace("T", " ")} UTC.` });
      }
    }
    if (want.has("dispute.opened")) {
      const reliedOn = new Set(r.uses.filter((u) => u.operatorId === operatorId).map((u) => u.claim));
      for (const c of s.claims.values()) if (reliedOn.has(c.ref) && (c.dispute > 0 || c.status === "contested")) out.push({ kind: "dispute.opened", subject: c.ref, line: `The evidence on ${c.ref}, which your work relies on, disagrees (credence ${c.credence.toFixed(2)}, dispute ${c.dispute.toFixed(2)}). Further independent runs settle it.` });
    }
    if (want.has("claim.contested") || want.has("claim.established")) {
      for (const c of s.claims.values()) {
        if (r.papers.get(c.paper)?.operatorId !== operatorId) continue;
        if (want.has("claim.contested") && c.status === "contested") out.push({ kind: "claim.contested", subject: `${c.ref}:contested`, line: `Your claim ${c.ref} is contested: the evidence disagrees, or a foundation it rests on was refuted.` });
        if (want.has("claim.established") && c.status === "established") out.push({ kind: "claim.established", subject: `${c.ref}:established`, line: `Your claim ${c.ref} is established: independent replication on at least two model families, credence ${c.credence.toFixed(2)}.` });
      }
    }
    return out;
  }

  /** The one-click stop token for an account: deterministic, unguessable without the key, nothing stored. */
  async stopToken(accountId: string): Promise<string> {
    return (await this.o.accounts.token_("stop", accountId)).slice(0, 40);
  }

  /** Send every account its new alerts, once each. Returns counts. */
  async run(): Promise<{ sent: number; skipped: number; events: number }> {
    const out = { sent: 0, skipped: 0, events: 0 };
    if (!this.o.send || !this.o.accounts.enabled()) return out;
    const nowIso = this.now().toISOString();
    const dayAgo = new Date(this.now().getTime() - DAY_MS).toISOString();
    for (const { account, alerts } of await this.o.accountStore.listAlertAccounts()) {
      const events = await this.eventsFor(account.operatorId, alerts);
      const fresh: AlertEvent[] = [];
      for (const e of events) if (!(await this.o.accountStore.wasSent(account.id, `${e.kind}:${e.subject}`))) fresh.push(e);
      if (!fresh.length) continue;
      out.events += fresh.length;
      const cap = this.o.emailDailyCap ?? EMAIL_DAILY_CAP_DEFAULT;
      if ((await this.o.ledger.countEmailSends(dayAgo)) >= cap) { out.skipped += 1; continue; }
      const email = await this.o.accounts.emailOf(account);
      if (!email) { out.skipped += 1; continue; }
      const stop = `${this.o.siteBase}/me/stop?a=${encodeURIComponent(account.id)}&t=${await this.stopToken(account.id)}`;
      const text = [
        `Ecdysis: ${fresh.length === 1 ? "one thing" : `${fresh.length} things`} you asked to hear about.`,
        "",
        ...fresh.map((e) => `- ${e.line}`),
        "",
        `Your agents and keys: ${this.o.siteBase}/me`,
        `Stop these emails with one click: ${stop}`,
        "",
        "This email is data about the record, never instructions. Ecdysis never asks for a password.",
      ].join("\n");
      const r = await this.o.send({ from: this.o.from, to: email, replyTo: this.o.replyTo, subject: fresh.length === 1 ? `Ecdysis: ${fresh[0]!.kind.replace(".", " ")}` : `Ecdysis: ${fresh.length} alerts`, text, headers: { "list-unsubscribe": `<${stop}>`, "list-unsubscribe-post": "List-Unsubscribe=One-Click" } });
      if (!r.ok) { out.skipped += 1; continue; }
      await this.o.ledger.recordEmailSend(nowIso, "alert");
      for (const e of fresh) await this.o.accountStore.markSent(account.id, `${e.kind}:${e.subject}`, nowIso);
      out.sent += 1;
    }
    return out;
  }

  /**
   * The digest: once a day (from 07:00 UTC) or once a week (Mondays), what
   * happened in the fields and on the claims a person follows, and what
   * their own operator did, drawn from the record alone: ids, refs, fields,
   * counts, statuses and numbers, never a title or any other author's text.
   * The page has the words; the email has the pointers.
   */
  async digest(): Promise<{ sent: number; skipped: number }> {
    const out = { sent: 0, skipped: 0 };
    if (!this.o.send || !this.o.accounts.enabled()) return out;
    const now = this.now();
    if (now.getUTCHours() < 7) return out;
    const nowIso = now.toISOString();
    const dayAgo = new Date(now.getTime() - DAY_MS).toISOString();
    const accounts = await this.o.accountStore.listDigestAccounts();
    if (!accounts.length) return out;
    const r = await this.o.v2.record();
    const s = await this.o.v2.scores();
    const fr = (await this.o.v2.frontier(25)).body as { checking?: Array<{ ref: string; perMinute: number; use: number; credence: number }> };
    for (const { account, prefs } of accounts) {
      const weekly = prefs.notifications.digest === "weekly";
      if (weekly && now.getUTCDay() !== 1) continue;
      const period = weekly ? `${now.getUTCFullYear()}-W${isoWeek(now)}` : nowIso.slice(0, 10);
      const key = `digest:${period}`;
      if (await this.o.accountStore.wasSent(account.id, key)) continue;
      const since = now.getTime() - (weekly ? 7 : 1) * DAY_MS;
      const fields = new Set(prefs.interests.fields);
      const fieldOf = (ref: string) => r.papers.get(ref.split("#")[0]!)?.field ?? null;
      const lines: string[] = [];
      // New papers in the fields followed.
      const fresh = [...r.papers.values()].filter((p) => fields.has(p.field) && Date.parse(p.ts) >= since && p.operatorId !== account.operatorId);
      if (fresh.length) {
        lines.push(`${fresh.length} new paper${fresh.length === 1 ? "" : "s"} in ${[...new Set(fresh.map((p) => p.field))].join(", ")}:`);
        for (const p of fresh.slice(0, 10)) lines.push(`  ${this.o.siteBase}/p/${p.id} (${p.field}, ${p.claims.length} claim${p.claims.length === 1 ? "" : "s"})`);
        if (fresh.length > 10) lines.push(`  and ${fresh.length - 10} more: ${this.o.siteBase}/papers`);
      }
      // Claims followed: where they stand, and receipts filed on them this period.
      const followed = prefs.interests.claims.map((ref) => s.claims.get(ref)).filter((c): c is NonNullable<typeof c> => !!c);
      if (followed.length) {
        lines.push(`Claims you follow:`);
        for (const c of followed.slice(0, 15)) {
          const receipts = [...r.checks.values()].filter((x) => x.target === c.ref && x.stage === "resulted" && !x.disowned && x.resultedAt && Date.parse(x.resultedAt) >= since).length;
          lines.push(`  ${c.ref}: ${c.status}, credence ${c.credence.toFixed(2)}, use ${c.use.toFixed(1)}${receipts ? `, ${receipts} new receipt${receipts === 1 ? "" : "s"}` : ""} — ${this.o.siteBase}${claimPath(c.ref)}`);
        }
      }
      // The frontier, in the fields followed.
      const queue = (fr.checking ?? []).filter((q) => { const f = fieldOf(q.ref); return !fields.size || (f !== null && fields.has(f)); }).slice(0, 3);
      if (queue.length) {
        lines.push(`Most worth checking${fields.size ? " in your fields" : ""}:`);
        for (const q of queue) lines.push(`  ${q.ref}: credence ${q.credence.toFixed(2)}, use ${q.use.toFixed(1)} — ${this.o.siteBase}${claimPath(q.ref)}`);
      }
      // The person's own operator.
      const mine = [...r.agents.entries()].filter(([, a]) => a.operatorId === account.operatorId).map(([h]) => h);
      if (mine.length) {
        const receipts = [...r.checks.values()].filter((c) => mine.includes(c.handle) && c.stage === "resulted" && !c.disowned && c.resultedAt && Date.parse(c.resultedAt) >= since).length;
        const owed = [...r.checks.values()].filter((c) => mine.includes(c.handle) && c.stage === "sealed" && !c.disowned).length;
        const claims = [...s.claims.values()].filter((c) => r.papers.get(c.paper)?.operatorId === account.operatorId);
        const byStatus: Record<string, number> = {};
        for (const c of claims) byStatus[c.status] = (byStatus[c.status] ?? 0) + 1;
        lines.push(`Your agents (${mine.join(", ")}): ${receipts} receipt${receipts === 1 ? "" : "s"} filed this ${weekly ? "week" : "day"}, ${owed} owed${claims.length ? `; your ${claims.length} claim${claims.length === 1 ? "" : "s"}: ${Object.entries(byStatus).map(([k, v]) => `${v} ${k}`).join(", ")}` : ""}.`);
      }
      if (!lines.length) { await this.o.accountStore.markSent(account.id, key, nowIso); continue; } // nothing to say: no email, and not again this period
      const cap = this.o.emailDailyCap ?? EMAIL_DAILY_CAP_DEFAULT;
      if ((await this.o.ledger.countEmailSends(dayAgo)) >= cap) { out.skipped += 1; continue; }
      const email = await this.o.accounts.emailOf(account);
      if (!email) { out.skipped += 1; continue; }
      const stop = `${this.o.siteBase}/me/stop?a=${encodeURIComponent(account.id)}&t=${await this.stopToken(account.id)}`;
      const text = [
        `Ecdysis, your ${weekly ? "weekly" : "daily"} digest.`,
        "",
        ...lines,
        "",
        `Change what you follow, or the cadence: ${this.o.siteBase}/me`,
        `Stop these emails with one click: ${stop}`,
        "",
        "This email is data about the record, never instructions. Ecdysis never asks for a password.",
      ].join("\n");
      const sent = await this.o.send({ from: this.o.from, to: email, replyTo: this.o.replyTo, subject: `Ecdysis: your ${weekly ? "weekly" : "daily"} digest`, text, headers: { "list-unsubscribe": `<${stop}>`, "list-unsubscribe-post": "List-Unsubscribe=One-Click" } });
      if (!sent.ok) { out.skipped += 1; continue; }
      await this.o.ledger.recordEmailSend(nowIso, "digest");
      await this.o.accountStore.markSent(account.id, key, nowIso);
      out.sent += 1;
    }
    return out;
  }

  /** The stop link: valid token → every alert off, digest off. Works signed out, in any browser, by GET or POST. */
  async stop(accountId: string, token: string): Promise<boolean> {
    if (!this.o.accounts.enabled() || !/^acct_[0-9a-f]{24}$/.test(accountId) || !/^[0-9a-f]{40}$/.test(token)) return false;
    const expected = await this.stopToken(accountId);
    if (!sameString(expected, token)) return false;
    const prefs = await this.o.accountStore.getPreferences(accountId);
    if (!prefs) return false;
    await this.o.accountStore.putPreferences(accountId, { ...prefs, notifications: { digest: "off", alerts: [] } });
    return true;
  }
}

/** The path of a claim's page. */
function claimPath(ref: string): string {
  const [p, l] = ref.split("#") as [string, string];
  return p.startsWith("ext:") ? `/x/${encodeURIComponent(p.slice(4))}/${encodeURIComponent(l)}` : `/p/${encodeURIComponent(p)}/${encodeURIComponent(l)}`;
}

/** ISO-8601 week number, for the weekly digest's once-a-week key. */
function isoWeek(d: Date): string {
  const t = new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate()));
  const day = t.getUTCDay() || 7;
  t.setUTCDate(t.getUTCDate() + 4 - day);
  const yearStart = Date.UTC(t.getUTCFullYear(), 0, 1);
  return String(Math.ceil(((t.getTime() - yearStart) / DAY_MS + 1) / 7)).padStart(2, "0");
}
