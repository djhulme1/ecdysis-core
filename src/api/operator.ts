/**
 * The operator console: ecdysis.me/operator, for the operator alone.
 *
 * Every request must carry a valid Cloudflare Access token for an allowed
 * address (access.ts); anything else gets a refusal page and touches no
 * data. Every POST must also come from this origin (Origin and
 * Sec-Fetch-Site) and carry the anti-forgery token bound to the sign-in.
 * Every action is written to the console's own audit trail. Responses are
 * never cached and never indexed, and the pages ship no script at all.
 *
 * What the console can do: approve, send and cancel author emails; write and
 * send digest issues; unsubscribe or erase a subscriber; run the jury
 * deadline check and a full log audit. What it deliberately cannot do:
 * publication decisions under R1, which need the operator key on the
 * operator's own machine.
 */

import type { EcdysisService, ApiResult } from "./service.js";
import type { Store } from "../store/store.js";
import type { Herald } from "./herald.js";
import { audienceLabel, type Newsletter } from "./newsletter.js";
import { csrfFor, sameString, verifyAccess, type AccessConfig } from "./access.js";
import { collectAnalytics, lastDays } from "./operator-data.js";
import { PROBE_OPERATOR } from "./funnel.js";
import { FIELDS } from "../core/schema.js";
import { FIELD_LABELS } from "./site.js";
import * as P from "../web/operator.js";

export interface ConsoleDeps {
  svc: EcdysisService;
  store: Store;
  herald: Herald | null;
  newsletter: Newsletter | null;
  access: AccessConfig;
  readOnly: boolean;
  switches: P.Switch[];
  heraldFrom: string;
  digestFrom: string;
  replyTo: string;
  fetchImpl?: typeof fetch;
  now?: () => Date;
}

const HEADERS: Record<string, string> = {
  "content-type": "text/html; charset=utf-8",
  "cache-control": "no-store, private",
  "x-robots-tag": "noindex, nofollow, noarchive",
  // Not "no-referrer": under that policy browsers send `Origin: null` on the
  // console's own form posts, which the same-origin check below would refuse.
  // "same-origin" still sends nothing to any other site.
  "referrer-policy": "same-origin",
  "x-content-type-options": "nosniff",
  "strict-transport-security": "max-age=31536000; includeSubDomains",
  "cross-origin-opener-policy": "same-origin",
  "cross-origin-resource-policy": "same-origin",
  "permissions-policy": "camera=(), microphone=(), geolocation=(), payment=()",
  // No script at all; forms may only post back to this origin.
  "content-security-policy":
    "default-src 'none'; style-src 'unsafe-inline'; img-src 'self'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'",
};

const MAX_FORM_BYTES = 64 * 1024;

/** Paths the console owns. Case-insensitive, so no spelling of the path slips past the lock. */
export function isConsolePath(path: string): boolean {
  return /^\/operator(\/|$)/i.test(path);
}

type Tone = "ok" | "warn" | "err";
const FLASH: Record<string, [Tone, string]> = {
  drafted: ["ok", "Draft saved. Read the exact text below, then send or cancel it."],
  sent: ["ok", "Sent."],
  cancelled: ["ok", "Cancelled. Nothing was sent."],
  "send-failed": ["err", "The provider refused the email; its reason is shown below."],
  paused: ["warn", "Email is paused (HERALD_PAUSED, or read-only mode). Nothing was sent."],
  "no-provider": ["warn", "No email provider key is installed yet (HERALD_API_KEY). Nothing was sent."],
  "daily-cap": ["warn", "The Herald's daily cap is reached. Nothing was sent; try tomorrow."],
  "domain-cap": ["warn", "Today's cap for that recipient's domain is reached. Nothing was sent; try tomorrow."],
  "shared-cap": ["warn", "The shared daily email cap is reached. Nothing was sent; try tomorrow."],
  suppressed: ["warn", "That address has asked never to be emailed, so the draft was closed unsent."],
  "not-draft": ["warn", "That isn't a draft any more."],
  "confirm-needed": ["warn", "Tick the box to confirm first."],
  "read-only": ["warn", "Read-only mode is on, so console actions are disabled."],
  deadlines: ["ok", "Deadline check done. The counts are in Health, under console activity."],
  invited: ["ok", "Invited. That operator's agents now hold full juror seats once each passes the practice bar. The invitation is in the public log."],
  "invite-known": ["warn", "That operator is already verified."],
  "invite-unknown": ["err", "No registered agent has that operator id. Check the spelling, or wait until one of its agents registers."],
  "invite-bad": ["err", "That isn't a usable operator id."],
  "audit-ok": ["ok", "Full audit passed: the log is intact."],
  "audit-bad": ["err", "The audit found a problem: see below."],
  "issue-saved": ["ok", "Issue saved as a draft. Read it below, then send it."],
  "issue-sent": ["ok", "Sent to everyone in the audience."],
  "issue-partial-cap": ["warn", "Part-sent: the shared daily cap is reached. Press Continue tomorrow to send the rest."],
  "issue-partial-batch": ["warn", "Sent one batch of 100. Press Continue for the next."],
  "issue-failed": ["err", "The provider refused the batch. Nothing more was sent; the reason is below. Press Continue to retry."],
  "empty-audience": ["warn", "Nobody has confirmed a subscription for that audience yet. Nothing was sent."],
  "already-sending": ["warn", "That issue is already being sent."],
  unsubscribed: ["ok", "Unsubscribed. They won't receive the digest again."],
  erased: ["ok", "Erased: the address and its delivery records are gone."],
  "not-found": ["err", "Not found."],
  error: ["err", "That didn't work."],
};

function page(status: number, html: string): Response {
  return new Response(html, { status, headers: HEADERS });
}

function redirect(to: string, code?: string): Response {
  // Targets are built here from fixed paths and validated ids, never from request text.
  return new Response(null, { status: 303, headers: { ...HEADERS, location: code ? `${to}?m=${code}` : to } });
}

function heraldCode(r: ApiResult): string {
  if (r.status === 200) return "sent";
  const e = String((r.body as Record<string, unknown> | null)?.["error"] ?? "");
  if (/paused/.test(e)) return "paused";
  if (/no email provider/.test(e)) return "no-provider";
  if (/shared cap/.test(e)) return "shared-cap";
  if (/emails to .* reached/.test(e)) return "domain-cap";
  if (/daily cap/.test(e)) return "daily-cap";
  if (/unsubscribed/.test(e)) return "suppressed";
  if (r.status === 502) return "send-failed";
  if (r.status === 404) return "not-found";
  if (r.status === 409) return "not-draft";
  return "error";
}

function issueCode(error: string): string {
  if (/paused/.test(error)) return "paused";
  if (/No email provider/.test(error)) return "no-provider";
  if (/Nobody has confirmed/.test(error)) return "empty-audience";
  if (/already being sent/.test(error)) return "already-sending";
  if (/already (sent|cancelled)|is (sent|cancelled|sending)/.test(error)) return "not-draft";
  if (/No such issue/.test(error)) return "not-found";
  if (/provider/.test(error)) return "issue-failed";
  return "error";
}

const HEX32 = "([0-9a-f]{32})";
const HEX64 = "([0-9a-f]{64})";

export async function handleConsole(req: Request, deps: ConsoleDeps): Promise<Response> {
  const url = new URL(req.url);
  const path = url.pathname.replace(/\/+$/, "") || "/";
  const method = req.method.toUpperCase();
  const now = (deps.now ?? (() => new Date()))();

  const v = await verifyAccess(req, deps.access, deps.fetchImpl ?? fetch, now.getTime());
  if (!v.ok) {
    // On any other hostname the console simply doesn't exist.
    if (v.reason === "wrong-host") return new Response("Not found", { status: 404, headers: { ...HEADERS, "content-type": "text/plain; charset=utf-8" } });
    return page(403, P.refusedPage(v.reason));
  }
  const csrf = await csrfFor(v.token);
  const actor = v.email;

  if (method === "POST") {
    // Same-origin posts only. Browsers set Sec-Fetch-Site themselves and page
    // script cannot forge it, so "same-origin" is the strong signal; with it,
    // an Origin of "null" (what browsers send under a strict referrer policy)
    // is fine. Without Sec-Fetch-Site (older browsers) the Origin must be this
    // console's own. The form token bound to the sign-in is required always.
    const origin = req.headers.get("origin");
    const site = req.headers.get("sec-fetch-site");
    const own = `https://${deps.access.host}`;
    const sameOrigin = site === "same-origin"
      ? origin === null || origin === "null" || origin === own
      : site === null && origin === own;
    if (!sameOrigin) return page(403, P.refusedPage("cross-site"));
    if (Number(req.headers.get("content-length") ?? "0") > MAX_FORM_BYTES) return page(413, P.refusedPage("too-large"));
    const text = await req.text();
    if (text.length > MAX_FORM_BYTES) return page(413, P.refusedPage("too-large"));
    const form = new URLSearchParams(text);
    if (!sameString(form.get("csrf") ?? "", csrf)) return page(403, P.refusedPage("bad-form"));
    return post(path, form, deps, { actor, csrf, now });
  }
  if (method !== "GET" && method !== "HEAD") return page(405, P.refusedPage("method"));
  const res = await get(path, url, deps, { actor, csrf, now });
  return method === "HEAD" ? new Response(null, { status: res.status, headers: res.headers }) : res;
}

interface Who { actor: string; csrf: string; now: Date }

async function ctxFor(deps: ConsoleDeps, who: Who, url: URL | null): Promise<P.ConsoleCtx> {
  const code = url?.searchParams.get("m") ?? "";
  const f = FLASH[code];
  const holds = await deps.store.listQuarantine("hazard_hold", 200);
  const pending = await deps.store.listQuarantine("pending", 200);
  const herald = await deps.store.listHerald(200);
  const issues = await deps.store.listIssues(50);
  let genesis = 0;
  for (const q of pending) {
    if (q.jury.length || q.seats?.length) continue; // only never-seated (genesis) cases wait for the operator
    const handle = String((((q.envelope as Record<string, unknown> | null)?.["payload"] as Record<string, unknown> | undefined)?.["agent"] as Record<string, unknown> | undefined)?.["handle"] ?? "");
    const a = handle ? await deps.store.getAgent(handle) : null;
    if (a?.operatorId !== PROBE_OPERATOR) genesis += 1;
  }
  return {
    email: who.actor, csrf: who.csrf, now: who.now,
    flash: f ? { tone: f[0], text: f[1] } : null,
    badges: {
      approvals: holds.length + genesis,
      emails: herald.filter((h) => h.status === "draft").length,
      digest: issues.filter((i) => i.status === "sending").length,
    },
  };
}

async function audiences(deps: ConsoleDeps): Promise<Array<{ value: string; label: string; count: number }>> {
  const subs = (await deps.store.listSubscribers(20000)).filter((s) => s.status === "confirmed");
  const never = new Set((await deps.store.listSuppressed(20000)).map((s) => s.email));
  const live = subs.filter((s) => !never.has(s.email));
  return [
    { value: "everyone", label: "Everyone subscribed", count: live.length },
    ...(FIELDS as readonly string[]).map((f) => ({
      value: f, label: `${FIELD_LABELS[f] ?? f} followers`,
      count: live.filter((s) => s.fields.includes("all") || s.fields.includes(f)).length,
    })),
  ];
}

async function get(path: string, url: URL, deps: ConsoleDeps, who: Who): Promise<Response> {
  const ctx = await ctxFor(deps, who, url);
  const { store } = deps;
  const extra = async () => ({
    cronLast: await store.getOpsState("cron:last"),
    readOnly: deps.readOnly,
    emailOn: deps.herald?.status.provider ?? false,
  });

  if (path === "/operator") {
    return page(200, P.overviewPage(ctx, await collectAnalytics(store, who.now, await extra())));
  }
  if (path === "/operator/approvals") {
    const a = await collectAnalytics(store, who.now, await extra());
    const heraldDrafts = (await store.listHerald(200)).filter((h) => h.status === "draft");
    return page(200, P.approvalsPage(ctx, a, { heraldDrafts, issues: await store.listIssues(50) }));
  }
  let m = path.match(new RegExp(`^/operator/case/${HEX64}$`));
  if (m) {
    const q = await store.getQuarantine(m[1]!);
    if (!q) return page(404, P.consoleShell({ ...ctx, flash: { tone: "err", text: "No such submission." } }, { title: "Not found", current: "/operator/approvals", body: "" }));
    const handle = String(((((q.envelope as Record<string, unknown> | null)?.["payload"] ?? {}) as Record<string, unknown>)["agent"] as Record<string, unknown> | undefined)?.["handle"] ?? "");
    const agent = handle ? await store.getAgent(handle) : null;
    return page(200, P.casePage(ctx, q, { probe: agent?.operatorId === PROBE_OPERATOR }));
  }
  if (path === "/operator/emails") {
    if (!deps.herald) return page(200, P.consoleShell(ctx, { title: "Emails", current: "/operator/emails", body: "<h1>Emails</h1><p>The Herald isn't configured on this deployment.</p>" }));
    return page(200, P.emailsPage(ctx, {
      rows: await store.listHerald(200), status: deps.herald.status,
      sent24h: await store.countEmailSends(new Date(who.now.getTime() - 86400000).toISOString()),
      suppressed: await store.listSuppressed(500),
    }));
  }
  m = path.match(new RegExp(`^/operator/emails/${HEX32}$`));
  if (m && deps.herald) {
    const h = await store.getHerald(m[1]!);
    if (!h) return redirect("/operator/emails", "not-found");
    return page(200, P.heraldDraftPage(ctx, h, { text: deps.herald.render(h), from: deps.heraldFrom, replyTo: deps.replyTo, status: deps.herald.status }));
  }
  if (path === "/operator/newsletter") {
    if (!deps.newsletter) return page(200, P.consoleShell(ctx, { title: "Digest", current: "/operator/newsletter", body: "<h1>Digest</h1><p>The digest isn't configured on this deployment.</p>" }));
    const subscribers = await store.listSubscribers(20000);
    const days = lastDays(who.now, 30);
    const counts = new Map<string, number>();
    for (const s of subscribers) if (s.status === "confirmed" && s.confirmedAt) counts.set(s.confirmedAt.slice(0, 10), (counts.get(s.confirmedAt.slice(0, 10)) ?? 0) + 1);
    const prefill = url.searchParams.get("prefill");
    let form: { audience: string; subject: string; body: string } | undefined;
    if (prefill && (prefill === "everyone" || (FIELDS as readonly string[]).includes(prefill))) {
      const span = [7, 14, 30].includes(Number(url.searchParams.get("days"))) ? Number(url.searchParams.get("days")) : 7;
      form = { audience: prefill, ...(await deps.newsletter.draftFromRecord(prefill, span)) };
    }
    return page(200, P.digestPage(ctx, {
      subscribers, issues: await store.listIssues(100), status: deps.newsletter.status,
      sent24h: await store.countEmailSends(new Date(who.now.getTime() - 86400000).toISOString()),
      confirms: days.map((date) => ({ date, n: counts.get(date) ?? 0 })),
      audiences: await audiences(deps), ...(form ? { form } : {}),
    }));
  }
  m = path.match(new RegExp(`^/operator/newsletter/issues/${HEX32}$`));
  if (m && deps.newsletter) {
    const issue = await store.getIssue(m[1]!);
    if (!issue) return redirect("/operator/newsletter", "not-found");
    const people = await deps.newsletter.audience(issue.audience);
    const sample = people[0] ?? {
      id: "0".repeat(32), email: "subscriber@example.org", fields: issue.audience === "everyone" ? ["all"] : [issue.audience],
      status: "confirmed" as const, confirmToken: "0".repeat(32), unsubToken: "0".repeat(32), createdAt: who.now.toISOString(),
    };
    const deliveries = await store.listDeliveries(issue.id);
    const failures = deliveries.filter((d) => d.status === "failed").sort((a, b) => b.at.localeCompare(a.at));
    return page(200, P.issuePage(ctx, issue, {
      preview: deps.newsletter.render(issue, sample), audienceCount: people.length, deliveries,
      status: deps.newsletter.status, from: deps.digestFrom, replyTo: deps.replyTo, lastError: failures[0]?.error ?? null,
    }));
  }
  if (path === "/operator/newsletter/subscribers") {
    return page(200, P.subscribersPage(ctx, await store.listSubscribers(5000)));
  }
  if (path === "/operator/agents") {
    return page(200, P.agentsPage(ctx, (await collectAnalytics(store, who.now, await extra())).agents));
  }
  if (path === "/operator/health") {
    return page(200, P.healthPage(ctx, {
      sth: (await deps.svc.sth()) as unknown as Record<string, unknown>, logSize: await store.logSize(),
      cron: await store.getOpsState("cron:last"), audit: await store.getOpsState("audit:last"),
      switches: deps.switches, trail: await store.listAudit(50),
    }));
  }
  return page(404, P.consoleShell({ ...ctx, flash: { tone: "err", text: "There's no console page at that address." } }, { title: "Not found", current: "", body: "<h1>Not found</h1>" }));
}

async function post(path: string, form: URLSearchParams, deps: ConsoleDeps, who: Who): Promise<Response> {
  const { store } = deps;
  const audit = (action: string, subject: string | null, detail: string | null = null) =>
    store.appendAudit({ at: who.now.toISOString(), actor: who.actor, action, subject, detail });
  const confirmed = form.get("confirm") === "yes";

  // A full audit only reads, so it stays available in read-only mode.
  if (path === "/operator/health/audit") {
    const r = await deps.svc.audit();
    const body = r.body as { intact?: boolean; problem?: string | null };
    const size = await store.logSize();
    await store.putOpsState("audit:last", { intact: !!body.intact, problem: body.problem ?? null, size }, who.now.toISOString());
    await audit("log.audit", null, body.intact ? `intact over ${size} entries` : "problem found");
    return redirect("/operator/health", body.intact ? "audit-ok" : "audit-bad");
  }
  if (deps.readOnly) return redirect(path.startsWith("/operator/newsletter") ? "/operator/newsletter" : path.startsWith("/operator/emails") ? "/operator/emails" : "/operator", "read-only");

  // jury/0.4: invite an operator to supply independent jurors. Logged publicly.
  if (path === "/operator/jurors/invite") {
    if (!confirmed) return redirect("/operator/agents", "confirm-needed");
    const op = (form.get("operatorId") ?? "").trim();
    const r = await deps.svc.inviteJurorOperator(op);
    await audit("juror.invite", op.slice(0, 80), String(r.status));
    if (r.status === 201) return redirect("/operator/agents", "invited");
    return redirect("/operator/agents", r.status === 409 ? "invite-known" : r.status === 404 ? "invite-unknown" : "invite-bad");
  }

  if (path === "/operator/approvals/deadlines") {
    const r = await deps.svc.enforceDeadlines();
    await audit("jury.deadlines", null, `cases ${r.cases}, lapsed ${r.lapsed}, seated ${r.seated}, decided ${r.decided}`);
    return redirect("/operator/approvals", "deadlines");
  }

  if (path === "/operator/emails/draft" && deps.herald) {
    const input = {
      to: form.get("to") ?? "", subject: form.get("subject") ?? "", kind: form.get("kind") ?? "",
      workId: form.get("workId") ?? "", paperId: form.get("paperId") ?? "", body: form.get("body") ?? "",
    };
    const r = await deps.herald.createDraft(input);
    if (r.status === 201) {
      const id = String((r.body as Record<string, unknown>)["id"]);
      await audit("email.draft", id, input.kind);
      return redirect(`/operator/emails/${id}`, "drafted");
    }
    const ctx = await ctxFor(deps, who, null);
    return page(422, P.emailsPage(ctx, {
      rows: await store.listHerald(200), status: deps.herald.status,
      sent24h: await store.countEmailSends(new Date(who.now.getTime() - 86400000).toISOString()),
      suppressed: await store.listSuppressed(500),
      form: { ...input, error: String((r.body as Record<string, unknown>)["error"] ?? "not saved") },
    }));
  }
  let m = path.match(new RegExp(`^/operator/emails/${HEX32}/(send|cancel)$`));
  if (m && deps.herald) {
    const [, id, act] = m as unknown as [string, string, string];
    if (act === "send") {
      if (!confirmed) return redirect(`/operator/emails/${id}`, "confirm-needed");
      const r = await deps.herald.sendDraft(id);
      const code = heraldCode(r);
      await audit("email.send", id, code);
      return redirect(`/operator/emails/${id}`, code);
    }
    const r = await deps.herald.cancelDraft(id);
    await audit("email.cancel", id, String(r.status));
    return redirect(`/operator/emails/${id}`, r.status === 200 ? "cancelled" : r.status === 404 ? "not-found" : "not-draft");
  }

  if (path === "/operator/newsletter/issues" && deps.newsletter) {
    const input = { audience: form.get("audience") ?? "", subject: form.get("subject") ?? "", body: form.get("body") ?? "" };
    const r = await deps.newsletter.createIssue(input);
    if (r.ok) {
      await audit("digest.draft", r.id, audienceLabel(input.audience));
      return redirect(`/operator/newsletter/issues/${r.id}`, "issue-saved");
    }
    const ctx = await ctxFor(deps, who, null);
    const subscribers = await store.listSubscribers(20000);
    return page(422, P.digestPage(ctx, {
      subscribers, issues: await store.listIssues(100), status: deps.newsletter.status,
      sent24h: await store.countEmailSends(new Date(who.now.getTime() - 86400000).toISOString()),
      confirms: lastDays(who.now, 30).map((date) => ({ date, n: subscribers.filter((s) => s.status === "confirmed" && s.confirmedAt?.slice(0, 10) === date).length })),
      audiences: await audiences(deps), form: { ...input, error: r.error },
    }));
  }
  m = path.match(new RegExp(`^/operator/newsletter/issues/${HEX32}/(send|cancel)$`));
  if (m && deps.newsletter) {
    const [, id, act] = m as unknown as [string, string, string];
    if (act === "send") {
      if (!confirmed) return redirect(`/operator/newsletter/issues/${id}`, "confirm-needed");
      const r = await deps.newsletter.sendIssue(id);
      const code = r.ok
        ? r.status === "sent" ? "issue-sent" : /cap/.test(r.note ?? "") ? "issue-partial-cap" : /refused/.test(r.note ?? "") ? "issue-failed" : "issue-partial-batch"
        : issueCode(r.error);
      await audit("digest.send", id, r.ok ? `${r.status}: delivered ${r.delivered}, remaining ${r.remaining}` : code);
      return redirect(`/operator/newsletter/issues/${id}`, code);
    }
    const r = await deps.newsletter.cancelIssue(id);
    await audit("digest.cancel", id, r.ok ? "cancelled" : "refused");
    return redirect(`/operator/newsletter/issues/${id}`, r.ok ? "cancelled" : "not-draft");
  }
  m = path.match(new RegExp(`^/operator/newsletter/subscribers/${HEX32}/(unsubscribe|erase)$`));
  if (m) {
    const [, id, act] = m as unknown as [string, string, string];
    const s = await store.getSubscriber(id);
    if (!s) return redirect("/operator/newsletter/subscribers", "not-found");
    if (act === "erase") {
      if (!confirmed) return redirect("/operator/newsletter/subscribers", "confirm-needed");
      await store.deleteSubscriber(id);
      await audit("digest.erase", id, null);
      return redirect("/operator/newsletter/subscribers", "erased");
    }
    if (s.status !== "unsubscribed") {
      s.status = "unsubscribed";
      s.unsubscribedAt = who.now.toISOString();
      s.pendingFields = null;
      await store.putSubscriber(s);
    }
    await audit("digest.unsubscribe", id, null);
    return redirect("/operator/newsletter/subscribers", "unsubscribed");
  }
  return redirect("/operator", "not-found");
}
