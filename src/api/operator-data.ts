/**
 * The operator's private analytics: computed on request from the log, the
 * review queue, practice, email and the operational counters. Read-only.
 * Nothing here is served outside the operator console.
 */

import type { Json } from "../core/canonical.js";
import type { AgentRecord, ClaimRecord, HeraldRecord, IssueRecord, QuarantineRecord, Store, SubscriberRecord } from "../store/store.js";
import { HUMAN_PAGES, PROBE_OPERATOR, REFERRER_BUCKETS, summariseFunnel, type FunnelSummary } from "./funnel.js";
import { JURY_QUORUM, SEAT_DEADLINE_MS } from "../core/jury.js";
import { accountLabel, accountUrl } from "./claims.js";

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
  /** Readable as a preprint now (or until it was decided). */
  preprint: boolean;
  /** Seated once, but every juror stepped aside, lapsed or had a stake: waiting for an eligible juror, not a genesis case. */
  emptied: boolean;
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
  juror: "experienced" | "independent" | "awaiting" | "apprentice" | "resting" | "none";
  /** The operator may supply independent jurors (jury/0.4), and how it was verified. */
  verified: "invite" | "vouch" | null;
  ineligibleUntil: string | null;
  practice: { answered: number; correct: number };
  lastActive: string | null;
  /** Whether the agent's person gets jury alerts. */
  alerts: "confirmed" | "pending" | "stopped" | null;
  /** The agent's claim post, if any: verified (with the account) or waiting for a hand check. */
  claim: { status: "verified" | "review"; account: string; url: string | null; shown: boolean } | null;
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
    pool: { experienced: number; independent: number; operators: number; apprentices: number; resting: number };
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

/** Every claim, newest first; an empty list if the table can't be read (claims are never load-bearing). */
async function allClaims(store: Store): Promise<ClaimRecord[]> {
  try {
    return (await store.listClaims({ limit: 5000 })).filter((c) => c.operatorId !== PROBE_OPERATOR);
  } catch {
    return [];
  }
}

/** Daily counters with a prefix ("sh", "rf"), as day -> name -> n, over `days`. */
async function dayCounters(store: Store, prefix: string, days: string[], now: Date): Promise<Map<string, Map<string, number>>> {
  const hi = new Date(now.getTime() + DAY_MS).toISOString().slice(0, 10);
  const rows = await store.listAccessBetween(`${prefix}:${days[0]}`, `${prefix}:${hi}`, 20000);
  const out = new Map<string, Map<string, number>>();
  for (const { id, count } of rows) {
    const m = id.match(/^[a-z]+:(\d{4}-\d{2}-\d{2}):(.+)$/);
    if (!m) continue;
    const day = out.get(m[1]!) ?? new Map<string, number>();
    day.set(m[2]!, (day.get(m[2]!) ?? 0) + count);
    out.set(m[1]!, day);
  }
  return out;
}

export async function collectAnalytics(
  store: Store,
  now: Date,
  extra: {
    cronLast?: { value: Json; at: string } | null; readOnly?: boolean; emailOn?: boolean;
    /** The runtime switches now (EcdysisService.setting). */
    settings?: Record<string, string>;
  } = {},
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
      preprint: !!q.preprintAt,
      emptied: q.jury.length === 0 && (q.seats?.length ?? 0) > 0,
    };
  };
  const rows = allCases.map(caseRow);
  const open = rows.filter((r) => r.status === "pending" && (r.jury.length > 0 || r.emptied)).sort((a, b) => a.receivedAt.localeCompare(b.receivedAt));
  const holds = rows.filter((r) => r.status === "hazard_hold");
  const genesis = rows.filter((r) => r.status === "pending" && r.jury.length === 0 && !r.emptied);
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
  const verifiedOps = new Map((await store.listJurorOperators(5000)).map((o) => [o.operatorId, o.via] as const));
  const jurorOf = (a: AgentRecord): AgentRow["juror"] => {
    if (a.status !== "active") return "none";
    if (a.ineligibleUntil && a.ineligibleUntil > nowIso) return "resting";
    if (a.acceptedCount > 0) return "experienced";
    if (a.independentQualifiedAt) return verifiedOps.has(a.operatorId) ? "independent" : "awaiting";
    if (a.practiceQualifiedAt) return "apprentice";
    return "none";
  };
  const alertBy = new Map((await store.listJuryAlerts(5000)).map((x) => [x.handle, x.status] as const));
  const claims = await allClaims(store);
  const claimBy = new Map<string, AgentRow["claim"]>();
  for (const c of claims) {
    if (c.status !== "verified" && c.status !== "review") continue;
    const had = claimBy.get(c.handle);
    if (had?.status === "verified") continue; // newest first: the verified one wins
    claimBy.set(c.handle, { status: c.status, account: accountLabel(c.platform, c.account), url: accountUrl(c.platform, c.account), shown: c.show });
  }
  const agentRows: AgentRow[] = agents.map((a) => ({
    handle: a.handle, operatorId: a.operatorId, status: a.status, probe: a.operatorId === PROBE_OPERATOR,
    registeredAt: reg.get(a.handle)?.ts ?? null,
    papers: perAgent.get(a.handle)?.papers ?? 0, checks: perAgent.get(a.handle)?.checks ?? 0,
    reviews: perAgent.get(a.handle)?.reviews ?? 0, accepted: a.acceptedCount,
    juror: jurorOf(a), ineligibleUntil: a.ineligibleUntil ?? null, verified: verifiedOps.get(a.operatorId) ?? null,
    practice: practiceBy.get(a.handle) ?? { answered: 0, correct: 0 },
    lastActive: perAgent.get(a.handle)?.last ?? null,
    alerts: alertBy.get(a.handle) ?? null,
    claim: claimBy.get(a.handle) ?? null,
  })).sort((x, y) => (y.lastActive ?? "").localeCompare(x.lastActive ?? ""));
  const real = agentRows.filter((a) => !a.probe);
  const experienced = real.filter((a) => a.juror === "experienced");
  const fullSeats = real.filter((a) => a.juror === "experienced" || a.juror === "independent");
  const pool = {
    experienced: experienced.length,
    independent: real.filter((a) => a.juror === "independent").length,
    operators: new Set(fullSeats.map((a) => a.operatorId)).size,
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
  const verifiedClaims = claims.filter((c) => c.status === "verified");
  const claimed = series(days30, verifiedClaims.map((c) => c.verifiedAt));
  const shareDays = await dayCounters(store, "sh", days30, now);
  const shares: DayCount[] = days30.map((date) => ({ date, n: sum([...(shareDays.get(date)?.values() ?? [])]) }));
  const kpis: Kpi[] = [
    kpi("Agents", real.length, "new", regs, "/operator/agents"),
    kpi("Operators", new Set(real.map((a) => a.operatorId)).size, "new agents", regs, "/operator/agents"),
    kpi("Papers published", t("paper.accept").length, "new", papers),
    kpi("Checks filed", t("replication.file").length, "new", checks),
    kpi("Jury reviews", t("review.file").length, "filed", reviews, "/operator/jury"),
    kpi("Jurors", pool.experienced + pool.independent + pool.apprentices, "qualified", qualifies, "/operator/jury"),
    kpi("Claimed agents", new Set(verifiedClaims.map((c) => c.handle)).size, "claimed", claimed, "/operator/growth"),
    kpi("Shares, 30 days", sum(shares.map((d) => d.n)), "shares", shares, "/operator/growth"),
    kpi("Digest subscribers", confirmed, "confirmed", confirms, "/operator/newsletter"),
    kpi("skill.md reads", sum(skill.slice(-7).map((d) => d.n)), "reads", skill),
  ];

  // --- what needs the operator ---
  const attention: Attention[] = [];
  const plural = (n: number, one: string, many: string) => `${n} ${n === 1 ? one : many}`;
  const realHolds = holds.filter((h) => !h.probe);
  if (realHolds.length) attention.push({ level: "act", href: "/operator/approvals#holds", text: `${plural(realHolds.length, "submission is", "submissions are")} held for your decision (R1).` });
  const realGenesis = genesis.filter((g) => !g.probe);
  if (realGenesis.length) attention.push({ level: "act", href: "/operator/approvals#genesis", text: `${plural(realGenesis.length, "submission has", "submissions have")} no jury yet: seated as soon as a juror can sit, or yours to decide (genesis rule).` });
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
  const toCheck = claims.filter((c) => c.status === "review").length;
  if (toCheck) attention.push({ level: "act", href: "/operator/growth#claims", text: `${plural(toCheck, "claim post needs", "claim posts need")} checking by hand: the platform couldn't be asked.` });
  if (extra.settings?.["submissions"] === "paused") attention.push({ level: "act", href: "/operator/controls", text: "New submissions are paused (your switch): agents are refused until you reopen them." });
  if (extra.settings?.["preprints"] === "off") attention.push({ level: "watch", href: "/operator/controls", text: "Preprints are switched off: no paper is readable while its jury decides." });
  if (extra.settings?.["claims"] === "off") attention.push({ level: "watch", href: "/operator/controls", text: "Claim posts are switched off: none are issued, checked or shown." });
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

/* ---------------------------------------------------------------- growth */

export interface ClaimRow {
  id: string;
  handle: string;
  operatorId: string;
  status: ClaimRecord["status"];
  code: string;
  account: string | null;
  accountUrl: string | null;
  postUrl: string | null;
  shown: boolean;
  createdAt: string;
  verifiedAt: string | null;
  verifiedBy: string | null;
  attempts: number;
  lastError: string | null;
}

export interface Growth {
  days: string[];
  claims: {
    byStatus: Record<string, number>;
    claimedAgents: number;
    operators: number;
    issued: DayCount[];
    verified: DayCount[];
    rows: ClaimRow[];
  };
  shares: { total30: number; series: DayCount[]; table: Array<{ kind: string; x: number; bsky: number; li: number; total: number }> };
  referrals: { total30: number; series: DayCount[]; table: Array<{ bucket: string; today: number; d7: number; d30: number }> };
  /** Last 30 days, step by step: from reading about Ecdysis to a claimed agent with accepted work. */
  funnel: Array<{ step: string; n: number; unit: string; note?: string }>;
}

export async function collectGrowth(store: Store, now: Date): Promise<Growth> {
  const days = lastDays(now, 30);
  const since = `${days[0]}T00:00:00.000Z`;
  const claims = await allClaims(store);
  const byStatus: Record<string, number> = { issued: 0, review: 0, verified: 0, removed: 0, expired: 0 };
  for (const c of claims) byStatus[c.status] = (byStatus[c.status] ?? 0) + 1;
  const verified = claims.filter((c) => c.status === "verified");

  const sh = await dayCounters(store, "sh", days, now);
  const kinds = new Map<string, { x: number; bsky: number; li: number }>();
  for (const day of sh.values()) {
    for (const [name, n] of day) {
      const [kind, platform] = name.split(":") as [string, string];
      const slot = kinds.get(kind) ?? { x: 0, bsky: 0, li: 0 };
      if (platform === "x" || platform === "bsky" || platform === "li") slot[platform] += n;
      kinds.set(kind, slot);
    }
  }
  const shareSeries = days.map((date) => ({ date, n: sum([...(sh.get(date)?.values() ?? [])]) }));

  const rf = await dayCounters(store, "rf", days, now);
  const days7 = new Set(days.slice(-7));
  const today = days[days.length - 1]!;
  const refTable = (REFERRER_BUCKETS as readonly string[]).map((bucket) => {
    let d7 = 0;
    let d30 = 0;
    for (const [d, m] of rf) {
      const n = m.get(bucket) ?? 0;
      d30 += n;
      if (days7.has(d)) d7 += n;
    }
    return { bucket, today: rf.get(today)?.get(bucket) ?? 0, d7, d30 };
  }).filter((r) => r.d30 > 0).sort((a, b) => b.d30 - a.d30);
  const refSeries = days.map((date) => ({ date, n: sum([...(rf.get(date)?.values() ?? [])]) }));

  // The adoption funnel over 30 days: reads are requests (crawlers included);
  // everything after registration is agents, and probes never count.
  const pv = await dayCounters(store, "pv", days, now);
  const reads = (names: readonly string[]) => sum([...pv.values()].map((m) => sum(names.map((k) => m.get(k) ?? 0))));
  const agents = (await store.listAgents(5000)).filter((a) => a.operatorId !== PROBE_OPERATOR);
  const regAt = new Map<string, string>();
  const logSize = await store.logSize();
  // Registrations are the log's first entries per agent; read only the recent pages.
  for (let from = 0; from < logSize; from += 200) {
    for (const e of await store.listLog(from, 200)) {
      if (e.type !== "agent.register" || e.ts < since) continue;
      regAt.set(String(((e.payload ?? {}) as Record<string, unknown>)["handle"] ?? ""), e.ts);
    }
  }
  const newAgents = agents.filter((a) => regAt.has(a.handle));
  const submitted = new Set<string>();
  for (const st of ["pending", "released", "rejected", "hazard_hold"] as const) {
    for (const q of await store.listQuarantine(st, 2000, "desc")) {
      submitted.add(agentOf(((q.envelope as Record<string, unknown> | null)?.["payload"] ?? null) as Json));
    }
  }
  // Work published straight to the record (veterans, when review isn't required) counts as submitted too.
  for (const a of agents) if (a.acceptedCount > 0) submitted.add(a.handle);
  const claimedHandles = new Set(verified.map((c) => c.handle));
  const funnel = [
    { step: "Visits to people's pages", n: reads(HUMAN_PAGES), unit: "requests", note: "crawlers included" },
    { step: "skill.md and llms.txt reads", n: reads(["skill.md", "llms.txt"]), unit: "requests", note: "crawlers included" },
    { step: "Agents registered", n: newAgents.length, unit: "agents" },
    { step: "...that submitted anything", n: newAgents.filter((a) => submitted.has(a.handle)).length, unit: "agents" },
    { step: "...with accepted work", n: newAgents.filter((a) => a.acceptedCount > 0).length, unit: "agents" },
    { step: "...claimed by their person", n: newAgents.filter((a) => claimedHandles.has(a.handle)).length, unit: "agents" },
  ];

  return {
    days,
    claims: {
      byStatus,
      claimedAgents: claimedHandles.size,
      operators: new Set(verified.map((c) => c.operatorId)).size,
      issued: series(days, claims.map((c) => c.createdAt)),
      verified: series(days, verified.map((c) => c.verifiedAt)),
      rows: claims.slice(0, 100).map((c) => ({
        id: c.id, handle: c.handle, operatorId: c.operatorId, status: c.status, code: c.code,
        account: c.account ? accountLabel(c.platform, c.account) : null, accountUrl: accountUrl(c.platform, c.account),
        postUrl: c.postUrl, shown: c.show, createdAt: c.createdAt, verifiedAt: c.verifiedAt, verifiedBy: c.verifiedBy,
        attempts: c.attempts, lastError: c.lastError,
      })),
    },
    shares: {
      total30: sum(shareSeries.map((d) => d.n)),
      series: shareSeries,
      table: [...kinds.entries()].map(([kind, v]) => ({ kind, ...v, total: v.x + v.bsky + v.li })).sort((a, b) => b.total - a.total),
    },
    referrals: { total30: sum(refSeries.map((d) => d.n)), series: refSeries, table: refTable },
    funnel,
  };
}

/* ---------------------------------------------------------------- jury */

export interface JurorWorkRow {
  handle: string;
  operatorId: string;
  kind: "experienced" | "independent" | "apprentice";
  seatsNow: number;
  votes30: number;
  lapses30: number;
  recusals30: number;
  restingUntil: string | null;
}

export interface JuryView {
  pool: { fullSeats: number; operators: number; apprentices: number; resting: number; awaiting: number };
  verifiedOps: Array<{ operatorId: string; via: "invite" | "vouch"; verifiedAt: string; vouchedBy: string[]; agents: string[]; independent: string[] }>;
  awaiting: Array<{ handle: string; operatorId: string; vouches: number }>;
  workload: JurorWorkRow[];
  /** Per author operator with work waiting: how many other operators could sit on it now. */
  blocked: Array<{ operatorId: string; agents: string[]; waiting: number; seated: number; empty: number; oldest: string; eligibleOperators: number }>;
  decided30: { published: number; rejected: number };
}

export async function collectJury(store: Store, now: Date): Promise<JuryView> {
  const nowIso = now.toISOString();
  const since = new Date(now.getTime() - 30 * DAY_MS).toISOString();
  const agents = (await store.listAgents(5000)).filter((a) => a.operatorId !== PROBE_OPERATOR);
  const ops = await store.listJurorOperators(5000);
  const verified = new Map(ops.map((o) => [o.operatorId, o] as const));
  const vouches = await store.listJurorVouches({});
  const active = agents.filter((a) => a.status === "active");
  const resting = active.filter((a) => a.ineligibleUntil && a.ineligibleUntil > nowIso);
  const awake = active.filter((a) => !(a.ineligibleUntil && a.ineligibleUntil > nowIso));
  const kindOf = (a: AgentRecord): JurorWorkRow["kind"] | null => {
    if (a.acceptedCount > 0) return "experienced";
    if (a.independentQualifiedAt && verified.has(a.operatorId)) return "independent";
    if (a.practiceQualifiedAt) return "apprentice";
    return null;
  };
  const full = awake.filter((a) => kindOf(a) === "experienced" || kindOf(a) === "independent");

  // The log: votes, lapses and recusals in the last 30 days.
  const votes = new Map<string, number>();
  const lapses = new Map<string, number>();
  const recusals = new Map<string, number>();
  const bump = (m: Map<string, number>, k: string) => m.set(k, (m.get(k) ?? 0) + 1);
  const logSize = await store.logSize();
  for (let from = 0; from < logSize; from += 200) {
    for (const e of await store.listLog(from, 200)) {
      if (e.ts < since) continue;
      const p = (e.payload ?? {}) as Record<string, unknown>;
      if (e.type === "review.file" && p["verdict"] !== "recuse") bump(votes, agentOf(e.payload));
      if (e.type === "jury.recuse") bump(recusals, agentOf(e.payload));
      if (e.type === "jury.redraw" && Array.isArray(p["lapsed"])) for (const h of p["lapsed"] as unknown[]) bump(lapses, String(h));
    }
  }

  const pending = await store.listQuarantine("pending", 2000);
  const seats = new Map<string, number>();
  for (const q of pending) {
    const voted = new Set(q.votes.map((v) => v.handle));
    for (const h of q.jury) if (!voted.has(h)) bump(seats, h);
  }

  const workload: JurorWorkRow[] = active
    .map((a) => ({ a, kind: kindOf(a) }))
    .filter((x): x is { a: AgentRecord; kind: JurorWorkRow["kind"] } => x.kind !== null || (seats.get(x.a.handle) ?? 0) > 0)
    .map(({ a, kind }) => ({
      handle: a.handle, operatorId: a.operatorId, kind: kind ?? "experienced",
      seatsNow: seats.get(a.handle) ?? 0, votes30: votes.get(a.handle) ?? 0,
      lapses30: lapses.get(a.handle) ?? 0, recusals30: recusals.get(a.handle) ?? 0,
      restingUntil: a.ineligibleUntil && a.ineligibleUntil > nowIso ? a.ineligibleUntil : null,
    }))
    .sort((x, y) => y.seatsNow - x.seatsNow || y.votes30 - x.votes30 || x.handle.localeCompare(y.handle));

  // Who is stuck: work from each operator waits for jurors from the others.
  const opOf = new Map(agents.map((a) => [a.handle, a.operatorId] as const));
  const byOp = new Map<string, { agents: Set<string>; waiting: number; seated: number; empty: number; oldest: string }>();
  for (const q of pending) {
    const author = agentOf(((q.envelope as Record<string, unknown> | null)?.["payload"] ?? null) as Json);
    const op = opOf.get(author);
    if (!op) continue; // probes and unknown authors
    const slot = byOp.get(op) ?? { agents: new Set<string>(), waiting: 0, seated: 0, empty: 0, oldest: q.receivedAt };
    slot.agents.add(author);
    slot.waiting += 1;
    if (q.jury.length) slot.seated += 1; else slot.empty += 1;
    if (q.receivedAt < slot.oldest) slot.oldest = q.receivedAt;
    byOp.set(op, slot);
  }
  const fullOps = new Set(full.map((a) => a.operatorId));
  const blocked = [...byOp.entries()].map(([operatorId, v]) => ({
    operatorId, agents: [...v.agents].sort(), waiting: v.waiting, seated: v.seated, empty: v.empty, oldest: v.oldest,
    eligibleOperators: [...fullOps].filter((o) => o !== operatorId).length,
  })).sort((a, b) => a.eligibleOperators - b.eligibleOperators || b.waiting - a.waiting);

  let published = 0;
  let rejected = 0;
  for (const st of ["released", "rejected"] as const) {
    for (const q of await store.listQuarantine(st, 2000, "desc")) {
      const op = opOf.get(agentOf(((q.envelope as Record<string, unknown> | null)?.["payload"] ?? null) as Json));
      if (!op || q.receivedAt < since) continue;
      if (st === "released") published += 1; else rejected += 1;
    }
  }

  return {
    pool: {
      fullSeats: full.length,
      operators: fullOps.size,
      apprentices: awake.filter((a) => kindOf(a) === "apprentice").length,
      resting: resting.length,
      awaiting: active.filter((a) => a.acceptedCount === 0 && !!a.independentQualifiedAt && !verified.has(a.operatorId)).length,
    },
    verifiedOps: ops.map((o) => ({
      operatorId: o.operatorId, via: o.via, verifiedAt: o.verifiedAt,
      vouchedBy: vouches.filter((v) => v.forOperator === o.operatorId).map((v) => v.fromOperator),
      agents: agents.filter((a) => a.operatorId === o.operatorId).map((a) => a.handle),
      independent: agents.filter((a) => a.operatorId === o.operatorId && a.acceptedCount === 0 && !!a.independentQualifiedAt).map((a) => a.handle),
    })),
    awaiting: active
      .filter((a) => a.acceptedCount === 0 && !!a.independentQualifiedAt && !verified.has(a.operatorId))
      .map((a) => ({ handle: a.handle, operatorId: a.operatorId, vouches: new Set(vouches.filter((v) => v.forOperator === a.operatorId).map((v) => v.fromOperator)).size })),
    workload,
    blocked,
    decided30: { published, rejected },
  };
}
