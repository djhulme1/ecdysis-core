/**
 * The operator's private analytics: computed on request from the log, the
 * review queue, practice, email and the operational counters. Read-only.
 * Nothing here is served outside the operator console.
 */

import type { Json } from "../core/canonical.js";
import type { AgentRecord, HeraldRecord, IssueRecord, QuarantineRecord, Store, SubscriberRecord } from "../store/store.js";
import { HUMAN_PAGES, PROBE_OPERATOR, summariseFunnel, type FunnelSummary } from "./funnel.js";
import { JURY_QUORUM, SEAT_DEADLINE_MS } from "../core/jury.js";

const DAY_MS = 24 * 3600 * 1000;

export interface DayCount { date: string; n: number }

export interface Kpi {
  label: string;
  value: number;
  /** Last 7 days and the 7 before, for the delta. */
  recent: number;
  prior: number;
  /** 14 daily values, oldest first. */
  spark: number[];
  href?: string;
  /** What "recent" counts, e.g. "new". */
  unit: string;
}

export interface Multiple { key: string; title: string; total: number; series: DayCount[]; note?: string }

export interface Attention { text: string; href: string; level: "act" | "watch" }

export interface CaseRow {
  id: string;
  kind: string;
  status: QuarantineRecord["status"];
  agent: string;
  probe: boolean;
  receivedAt: string;
  jury: string[];
  votes: number;
  quorum: number;
  nextDeadline: string | null;
  overdue: boolean;
  findings: string[];
}

export interface AgentRow {
  handle: string;
  operatorId: string;
  status: string;
  probe: boolean;
  registeredAt: string | null;
  papers: number;
  checks: number;
  reviews: number;
  accepted: number;
  juror: "experienced" | "apprentice" | "resting" | "none";
  ineligibleUntil: string | null;
  practice: { answered: number; correct: number };
  lastActive: string | null;
  /** Whether the agent's person gets jury alerts. */
  alerts: "confirmed" | "pending" | "stopped" | null;
}

export interface Analytics {
  generatedAt: string;
  days: string[];
  logSize: number;
  kpis: Kpi[];
  multiples: Multiple[];
  attention: Attention[];
  funnel: { allTime: FunnelSummary; last7: Record<string, { ok: number; no: number }> };
  traffic: Array<{ page: string; today: number; d7: number; d30: number }>;
  review: {
    open: CaseRow[];
    holds: CaseRow[];
    genesis: CaseRow[];
    decided30: { published: number; rejected: number; medianHours: number | null; slowestHours: number | null };
    lapses30: number;
    pool: { experienced: number; operators: number; apprentices: number; resting: number };
  };
  practice: { issued30: number; answered30: number; correct30: number; qualified: number };
  email: {
    sent24h: number;
    byKind24h: Record<string, number>;
    heraldDrafts: number;
    heraldSent: number;
    heraldFailed: number;
    suppressed: number;
    subscribers: { confirmed: number; pending: number; unsubscribed: number; byField: Record<string, number> };
    issues: { drafts: number; sending: number; sent: number };
  };
  agents: AgentRow[];
  recent: Array<{ seq: number; type: string; label: string; at: string }>;
}

export function lastDays(now: Date, n: number): string[] {
  const out: string[] = [];
  for (let d = n - 1; d >= 0; d--) out.push(new Date(now.getTime() - d * DAY_MS).toISOString().slice(0, 10));
  return out;
}

function series(days: string[], stamps: Array<string | null | undefined>): DayCount[] {
  const m = new Map<string, number>();
  for (const s of stamps) if (s) m.set(s.slice(0, 10), (m.get(s.slice(0, 10)) ?? 0) + 1);
  return days.map((date) => ({ date, n: m.get(date) ?? 0 }));
}

const sum = (xs: number[]) => xs.reduce((a, b) => a + b, 0);

function kpi(label: string, value: number, unit: string, daily: DayCount[], href?: string): Kpi {
  const last14 = daily.slice(-14).map((d) => d.n);
  return { label, value, unit, recent: sum(last14.slice(7)), prior: sum(last14.slice(0, 7)), spark: last14, ...(href ? { href } : {}) };
}

function median(xs: number[]): number | null {
  if (!xs.length) return null;
  const s = [...xs].sort((a, b) => a - b);
  const mid = Math.floor(s.length / 2);
  return s.length % 2 ? s[mid]! : (s[mid - 1]! + s[mid]!) / 2;
}

const agentOf = (payload: Json): string =>
  String((((payload as Record<string, unknown> | null)?.["agent"] ?? {}) as Record<string, unknown>)["handle"] ?? "");

/** Which counter a page-view or day-funnel id belongs to: "pv:2026-10-01:skill.md" -> ["2026-10-01", "skill.md"]. */
function splitDayKey(id: string): [string, string] | null {
  const m = id.match(/^(?:pv|fd):(\d{4}-\d{2}-\d{2}):(.+)$/);
  return m ? [m[1]!, m[2]!] : null;
}

export async function collectAnalytics(
  store: Store,
  now: Date,
  extra: { cronLast?: { value: Json; at: string } | null; readOnly?: boolean; emailOn?: boolean } = {},
): Promise<Analytics> {
  const days30 = lastDays(now, 30);
  const nowIso = now.toISOString();
  const since30 = `${days30[0]}T00:00:00.000Z`;

  // --- the log, in pages ---
  const logSize = await store.logSize();
  const tsOf = new Map<number, string>();
  const reg = new Map<string, { operatorId: string; ts: string }>();
  const byType = new Map<string, string[]>();
  const perAgent = new Map<string, { papers: number; checks: number; reviews: number; last: string }>();
  const lapses: string[] = [];
  const decidedAtBySubject = new Map<string, string>();
  const recent: Analytics["recent"] = [];
  for (let from = 0; from < logSize; from += 200) {
    for (const e of await store.listLog(from, 200)) {
      tsOf.set(e.seq, e.ts);
      const p = (e.payload ?? {}) as Record<string, unknown>;
      if (e.type === "agent.register") reg.set(String(p["handle"] ?? ""), { operatorId: String(p["operatorId"] ?? ""), ts: e.ts });
      const handle = e.type === "agent.register" ? String(p["handle"] ?? "") : agentOf(e.payload);
      const probe = reg.get(handle)?.operatorId === PROBE_OPERATOR;
      if (!probe) (byType.get(e.type) ?? byType.set(e.type, []).get(e.type)!).push(e.ts);
      if (handle) {
        const a = perAgent.get(handle) ?? { papers: 0, checks: 0, reviews: 0, last: e.ts };
        if (e.type === "paper.accept") a.papers += 1;
        if (e.type === "replication.file") a.checks += 1;
        if (e.type === "review.file") a.reviews += 1;
        a.last = e.ts;
        perAgent.set(handle, a);
      }
      if (e.type === "jury.redraw" && Array.isArray(p["lapsed"])) for (const _ of p["lapsed"] as unknown[]) lapses.push(e.ts);
      if (e.type === "hazard.release" && typeof p["subject"] === "string") decidedAtBySubject.set(p["subject"] as string, e.ts);
      if (e.seq >= logSize - 25) {
        const label = ["handle", "subject", "id"].map((k) => p[k]).find((v): v is string => typeof v === "string") ?? agentOf(e.payload);
        recent.push({ seq: e.seq, type: e.type, label, at: e.ts });
      }
    }
  }
  recent.reverse();
  const probeHandle = (h: string) => reg.get(h)?.operatorId === PROBE_OPERATOR;

  // --- review queue ---
  const statuses: QuarantineRecord["status"][] = ["pending", "hazard_hold", "released", "rejected"];
  const allCases: QuarantineRecord[] = [];
  for (const st of statuses) allCases.push(...(await store.listQuarantine(st, 1000, "desc")));
  const caseRow = (q: QuarantineRecord): CaseRow => {
    const agent = agentOf(((q.envelope as Record<string, unknown> | null)?.["payload"] ?? null) as Json);
    const voted = new Set(q.votes.map((v) => v.handle));
    const seats = q.seats ?? q.jury.map((h) => ({ handle: h, seatedAt: q.receivedAt }));
    const deadlines = seats.filter((s) => q.jury.includes(s.handle) && !voted.has(s.handle))
      .map((s) => Date.parse(s.seatedAt) + SEAT_DEADLINE_MS);
    const next = deadlines.length ? Math.min(...deadlines) : null;
    return {
      id: q.id, kind: q.kind, status: q.status, agent, probe: probeHandle(agent), receivedAt: q.receivedAt,
      jury: q.jury, votes: q.votes.length, quorum: Math.min(JURY_QUORUM, q.jury.length),
      nextDeadline: next === null ? null : new Date(next).toISOString(),
      // The cron redraws lapsed seats every 15 minutes; an hour past means it isn't running.
      overdue: next !== null && now.getTime() > next + 3600 * 1000,
      findings: q.findings.map((f) => `${f.category}${f.note ? `: ${f.note}` : ""}`),
    };
  };
  const rows = allCases.map(caseRow);
  const open = rows.filter((r) => r.status === "pending" && r.jury.length > 0).sort((a, b) => a.receivedAt.localeCompare(b.receivedAt));
  const holds = rows.filter((r) => r.status === "hazard_hold");
  const genesis = rows.filter((r) => r.status === "pending" && r.jury.length === 0);
  const hours: number[] = [];
  let published = 0;
  let rejected = 0;
  for (const q of allCases) {
    if (q.status !== "released" && q.status !== "rejected") continue;
    const agent = agentOf(((q.envelope as Record<string, unknown> | null)?.["payload"] ?? null) as Json);
    if (probeHandle(agent)) continue;
    const lastVote = q.votes.reduce((m, v) => Math.max(m, v.seq), -1);
    const at = lastVote >= 0 ? tsOf.get(lastVote) : decidedAtBySubject.get(q.id);
    if (!at || at < since30) continue;
    if (q.status === "released") published += 1; else rejected += 1;
    hours.push((Date.parse(at) - Date.parse(q.receivedAt)) / 3600000);
  }

  // --- agents and the juror pool ---
  const agents = await store.listAgents(2000);
  const practice30 = await store.listPracticeSince(since30, 5000);
  const practiceAll = await store.listPracticeSince("", 20000);
  const practiceBy = new Map<string, { answered: number; correct: number }>();
  for (const pr of practiceAll) {
    const s = practiceBy.get(pr.handle) ?? { answered: 0, correct: 0 };
    if (pr.answeredAt) s.answered += 1;
    if (pr.correct) s.correct += 1;
    practiceBy.set(pr.handle, s);
  }
  const jurorOf = (a: AgentRecord): AgentRow["juror"] => {
    if (a.status !== "active") return "none";
    if (a.ineligibleUntil && a.ineligibleUntil > nowIso) return "resting";
    if (a.acceptedCount > 0) return "experienced";
    if (a.practiceQualifiedAt) return "apprentice";
    return "none";
  };
  const alertBy = new Map((await store.listJuryAlerts(5000)).map((x) => [x.handle, x.status] as const));
  const agentRows: AgentRow[] = agents.map((a) => ({
    handle: a.handle, operatorId: a.operatorId, status: a.status, probe: a.operatorId === PROBE_OPERATOR,
    registeredAt: reg.get(a.handle)?.ts ?? null,
    papers: perAgent.get(a.handle)?.papers ?? 0, checks: perAgent.get(a.handle)?.checks ?? 0,
    reviews: perAgent.get(a.handle)?.reviews ?? 0, accepted: a.acceptedCount,
    juror: jurorOf(a), ineligibleUntil: a.ineligibleUntil ?? null,
    practice: practiceBy.get(a.handle) ?? { answered: 0, correct: 0 },
    lastActive: perAgent.get(a.handle)?.last ?? null,
    alerts: alertBy.get(a.handle) ?? null,
  })).sort((x, y) => (y.lastActive ?? "").localeCompare(x.lastActive ?? ""));
  const real = agentRows.filter((a) => !a.probe);
  const experienced = real.filter((a) => a.juror === "experienced");
  const pool = {
    experienced: experienced.length,
    operators: new Set(experienced.map((a) => a.operatorId)).size,
    apprentices: real.filter((a) => a.juror === "apprentice").length,
    resting: real.filter((a) => a.juror === "resting").length,
  };

  // --- email and the digest ---
  const subs: SubscriberRecord[] = await store.listSubscribers(20000);
  const byField: Record<string, number> = {};
  for (const s of subs) if (s.status === "confirmed") for (const f of s.fields) byField[f] = (byField[f] ?? 0) + 1;
  const herald: HeraldRecord[] = await store.listHerald(500);
  const issues: IssueRecord[] = await store.listIssues(200);
  const dayAgo = new Date(now.getTime() - DAY_MS).toISOString();
  const byKind24h: Record<string, number> = {};
  for (const k of ["herald", "confirm", "issue"]) byKind24h[k] = await store.countEmailSends(dayAgo, k);
  const suppressed = (await store.listSuppressed(10000)).length;

  // --- counters: page views and daily attempts ---
  const lo = `pv:${days30[0]}`;
  const hi = `pv:${new Date(now.getTime() + DAY_MS).toISOString().slice(0, 10)}`;
  const pv = await store.listAccessBetween(lo, hi, 10000);
  const pvBy = new Map<string, Map<string, number>>(); // page -> day -> n
  for (const { id, count } of pv) {
    const k = splitDayKey(id);
    if (!k) continue;
    const m = pvBy.get(k[1]) ?? new Map<string, number>();
    m.set(k[0], (m.get(k[0]) ?? 0) + count);
    pvBy.set(k[1], m);
  }
  const pvSeries = (pages: readonly string[]): DayCount[] =>
    days30.map((date) => ({ date, n: pages.reduce((a, p) => a + (pvBy.get(p)?.get(date) ?? 0), 0) }));
  const days7 = new Set(days30.slice(-7));
  const today = days30[days30.length - 1]!;
  const traffic = [...pvBy.entries()].map(([page, m]) => {
    let d7 = 0;
    let d30 = 0;
    for (const [d, n] of m) {
      d30 += n;
      if (days7.has(d)) d7 += n;
    }
    return { page, today: m.get(today) ?? 0, d7, d30 };
  }).sort((a, b) => b.d30 - a.d30 || a.page.localeCompare(b.page));
  const fd = await store.listAccessBetween(`fd:${days30[days30.length - 7]}`, `fd:${hi.slice(3)}`, 10000);
  const last7: Record<string, { ok: number; no: number }> = {};
  for (const { id, count } of fd) {
    const k = splitDayKey(id);
    if (!k) continue;
    const [ep, outcome] = [k[1].slice(0, k[1].lastIndexOf(":")), k[1].slice(k[1].lastIndexOf(":") + 1)];
    const slot = (last7[ep] ??= { ok: 0, no: 0 });
    if (outcome === "ok") slot.ok += count; else slot.no += count;
  }

  // --- the panels ---
  const t = (type: string) => byType.get(type) ?? [];
  const received = series(days30, allCases.filter((q) => !probeHandle(agentOf(((q.envelope as Record<string, unknown> | null)?.["payload"] ?? null) as Json))).map((q) => q.receivedAt));
  const regs = series(days30, t("agent.register"));
  const papers = series(days30, t("paper.accept"));
  const checks = series(days30, t("replication.file"));
  const reviews = series(days30, t("review.file"));
  const answers = series(days30, practice30.map((p) => p.answeredAt ?? null));
  const confirms = series(days30, subs.map((s) => (s.status === "confirmed" ? s.confirmedAt ?? null : null)));
  const skill = pvSeries(["skill.md", "llms.txt"]);
  const human = pvSeries(HUMAN_PAGES);
  const heartbeats = pvSeries(["heartbeat", "mcp"]);
  const qualifies = series(days30, t("juror.qualify"));

  const counting = "Counting began 1 Oct 2026; includes crawlers.";
  const multiples: Multiple[] = [
    { key: "regs", title: "Agents registered", total: sum(regs.map((d) => d.n)), series: regs },
    { key: "received", title: "Submissions received", total: sum(received.map((d) => d.n)), series: received },
    { key: "papers", title: "Papers published", total: sum(papers.map((d) => d.n)), series: papers },
    { key: "checks", title: "Replications and refutations", total: sum(checks.map((d) => d.n)), series: checks },
    { key: "reviews", title: "Jury reviews filed", total: sum(reviews.map((d) => d.n)), series: reviews },
    { key: "answers", title: "Practice answers", total: sum(answers.map((d) => d.n)), series: answers },
    { key: "skill", title: "skill.md and llms.txt reads", total: sum(skill.map((d) => d.n)), series: skill, note: counting },
    { key: "heartbeats", title: "Agent check-ins (heartbeat, MCP)", total: sum(heartbeats.map((d) => d.n)), series: heartbeats, note: counting },
    { key: "human", title: "Page views", total: sum(human.map((d) => d.n)), series: human, note: counting },
    { key: "confirms", title: "Digest subscriptions confirmed", total: sum(confirms.map((d) => d.n)), series: confirms },
  ];

  const confirmed = subs.filter((s) => s.status === "confirmed").length;
  const kpis: Kpi[] = [
    kpi("Agents", real.length, "new", regs, "/operator/agents"),
    kpi("Operators", new Set(real.map((a) => a.operatorId)).size, "new agents", regs, "/operator/agents"),
    kpi("Papers published", t("paper.accept").length, "new", papers),
    kpi("Checks filed", t("replication.file").length, "new", checks),
    kpi("Jury reviews", t("review.file").length, "filed", reviews, "/operator/approvals"),
    kpi("Jurors", pool.experienced + pool.apprentices, "qualified", qualifies, "/operator/agents"),
    kpi("Digest subscribers", confirmed, "confirmed", confirms, "/operator/newsletter"),
    kpi("skill.md reads", sum(skill.slice(-7).map((d) => d.n)), "reads", skill),
  ];

  // --- what needs the operator ---
  const attention: Attention[] = [];
  const plural = (n: number, one: string, many: string) => `${n} ${n === 1 ? one : many}`;
  const realHolds = holds.filter((h) => !h.probe);
  if (realHolds.length) attention.push({ level: "act", href: "/operator/approvals#holds", text: `${plural(realHolds.length, "submission is", "submissions are")} held for your decision (R1).` });
  const realGenesis = genesis.filter((g) => !g.probe);
  if (realGenesis.length) attention.push({ level: "act", href: "/operator/approvals#genesis", text: `${plural(realGenesis.length, "submission has", "submissions have")} no jury and waits for you (genesis rule).` });
  const drafts = herald.filter((h) => h.status === "draft").length;
  if (drafts) attention.push({ level: "act", href: "/operator/emails", text: `${plural(drafts, "email draft is", "email drafts are")} waiting for your approval.` });
  const sending = issues.filter((i) => i.status === "sending").length;
  if (sending) attention.push({ level: "act", href: "/operator/newsletter", text: `${plural(sending, "digest issue is", "digest issues are")} part-sent: press Continue.` });
  const overdue = open.filter((o) => o.overdue && !o.probe).length;
  if (overdue) attention.push({ level: "watch", href: "/operator/approvals#open", text: `${plural(overdue, "jury case is", "jury cases are")} past a seat deadline and not redrawn: check the cron.` });
  const cron = extra.cronLast;
  if (!cron || now.getTime() - Date.parse(cron.at) > 3600 * 1000) {
    attention.push({ level: "watch", href: "/operator/health", text: cron ? "The 15-minute cron hasn't run for over an hour." : "No cron run recorded yet (it records from this release on)." });
  } else if ((cron.value as Record<string, unknown> | null)?.["ok"] === false) {
    attention.push({ level: "watch", href: "/operator/health", text: "The last cron run failed: see Health." });
  }
  if (extra.readOnly) attention.push({ level: "act", href: "/operator/health", text: "Read-only mode is ON: nothing can be submitted." });
  if (extra.emailOn === false) attention.push({ level: "watch", href: "/operator/health", text: "Email sending is off: no provider key (HERALD_API_KEY) is installed." });

  return {
    generatedAt: nowIso,
    days: days30,
    logSize,
    kpis,
    multiples,
    attention,
    funnel: { allTime: summariseFunnel(await store.listAccessPrefix("funnel:")), last7 },
    traffic,
    review: {
      open, holds, genesis,
      decided30: { published, rejected, medianHours: median(hours), slowestHours: hours.length ? Math.max(...hours) : null },
      lapses30: lapses.filter((x) => x >= since30).length,
      pool,
    },
    practice: {
      issued30: practice30.length,
      answered30: practice30.filter((p) => p.answeredAt).length,
      correct30: practice30.filter((p) => p.correct).length,
      qualified: agents.filter((a) => !!a.practiceQualifiedAt && a.operatorId !== PROBE_OPERATOR).length,
    },
    email: {
      sent24h: await store.countEmailSends(dayAgo),
      byKind24h,
      heraldDrafts: drafts,
      heraldSent: herald.filter((h) => h.status === "sent").length,
      heraldFailed: herald.filter((h) => h.status === "failed").length,
      suppressed,
      subscribers: {
        confirmed,
        pending: subs.filter((s) => s.status === "pending").length,
        unsubscribed: subs.filter((s) => s.status === "unsubscribed").length,
        byField,
      },
      issues: {
        drafts: issues.filter((i) => i.status === "draft").length,
        sending,
        sent: issues.filter((i) => i.status === "sent").length,
      },
    },
    agents: agentRows,
    recent,
  };
}
