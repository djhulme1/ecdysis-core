/**
 * The operator console's pages: private, server-rendered and script-free
 * (the CSP forbids script outright, so nothing on these pages can run code,
 * even inside the unpublished submissions they display). Every value is
 * escaped. Charts are inline SVG following the dataviz procedure: single
 * series in the accent amber (>= 5.8:1 on the card in both modes), 4px
 * rounded data-ends on a hairline baseline, 2px gaps, only the maximum
 * labelled, hover readouts in CSS, and every number also in a table.
 */

import type { Json } from "../core/canonical.js";
import { FIELDS } from "../core/schema.js";
import { FIELD_LABELS } from "../api/site.js";
import { CSS, MARK, esc } from "./design.js";
import { waited } from "./review.js";
import type { Analytics, AgentRow, CaseRow, DayCount, Kpi } from "../api/operator-data.js";
import type { AuditRecord, DeliveryRecord, HeraldRecord, IssueRecord, QuarantineRecord, SubscriberRecord } from "../store/store.js";
import { audienceLabel, fieldsLabel } from "../api/newsletter.js";
import { HERALD_KINDS } from "../api/herald.js";

export interface ConsoleCtx {
  email: string;
  csrf: string;
  now: Date;
  flash?: { tone: "ok" | "warn" | "err"; text: string } | null;
  badges?: { approvals?: number; emails?: number; digest?: number };
}

const NAV: ReadonlyArray<readonly [string, string, keyof NonNullable<ConsoleCtx["badges"]> | null]> = [
  ["/operator", "Overview", null],
  ["/operator/approvals", "Approvals", "approvals"],
  ["/operator/emails", "Emails", "emails"],
  ["/operator/newsletter", "Digest", "digest"],
  ["/operator/agents", "Agents", null],
  ["/operator/health", "Health", null],
];

const OPS_CSS = `
.ops-top{display:flex;align-items:center;justify-content:space-between;gap:10px 16px;flex-wrap:wrap;padding:18px 0 10px}
.ops-tag{font:600 11px/1 var(--sans);letter-spacing:.08em;text-transform:uppercase;color:var(--amber);border:1px solid var(--amber);padding:4px 6px;border-radius:3px;margin-left:10px;vertical-align:middle}
.ops-who{font:13px/1.4 var(--sans);color:var(--muted)}
.ops-who a{color:var(--muted)}
.ops-nav{display:flex;flex-wrap:wrap;gap:6px 20px;font:15px/1.4 var(--sans);border-bottom:1px solid var(--line);padding:2px 0 12px}
.ops-nav a{color:var(--muted);text-decoration:none}
.ops-nav a:hover{color:var(--ink)}
.ops-nav a[aria-current=page]{color:var(--ink);text-decoration:underline;text-decoration-color:var(--amber);text-decoration-thickness:2px}
.badge{display:inline-block;min-width:1.5em;padding:1px 6px;border-radius:9px;background:var(--amber);color:var(--on-amber);font:600 12px/1.45 var(--sans);text-align:center;margin-left:5px}
.flash{border:1px solid var(--amber);background:var(--card);padding:10px 12px;font:15px/1.45 var(--sans);margin:0 0 22px}
.flash.ok{border-color:var(--sound)}.flash.err{border-color:var(--broken)}
.flash b{margin-right:6px}
.tiles{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(100%,10.5rem),1fr));gap:12px}
.tiles+p.small{margin-top:10px}
main form label{font:15px/1.4 var(--sans)}
.tile{display:block;background:var(--card);border:1px solid var(--line);padding:12px 14px 10px;color:var(--ink);text-decoration:none;min-width:0}
a.tile:hover{border-color:var(--amber)}
.tile .k{display:block;font:14px/1.3 var(--sans);color:var(--muted)}
.tile .v{display:block;font:600 30px/1.15 var(--sans);margin:4px 0 2px}
.tile .dl{display:block;font:13px/1.35 var(--sans)}
.up{color:var(--sound)}.down{color:var(--broken)}.flat{color:var(--muted)}
.mult{display:grid;grid-template-columns:repeat(auto-fill,minmax(17rem,1fr));gap:14px}
.panel{background:var(--card);border:1px solid var(--line);padding:12px 14px 8px;min-width:0}
.panel h3{font:600 14px/1.3 var(--sans);margin:0}
.panel .tot{font:13px/1.35 var(--sans);color:var(--muted);margin:2px 0 0}
.viz{display:block;width:100%;height:auto;margin:8px 0 2px;overflow:visible}
.viz .ax{fill:var(--muted);font:11px var(--sans)}
.viz .base{stroke:var(--line);stroke-width:1}
.viz .bar{fill:var(--amber)}
.viz .lbl{fill:var(--ink);font:600 11px var(--sans)}
.viz .col .tipg{opacity:0}
.viz .col:hover .tipg{opacity:1}
.viz .col:hover .bar{fill:color-mix(in srgb,var(--amber) 70%,var(--ink))}
.viz .tipbg{fill:var(--ink)}
.viz .tiptx{fill:var(--ground);font:600 11px var(--sans)}
.viz .spk{fill:none;stroke:var(--muted);stroke-width:2;stroke-linejoin:round;stroke-linecap:round}
.viz .dot{fill:var(--amber);stroke:var(--card);stroke-width:2}
.meter{display:block;height:8px;border-radius:4px;background:color-mix(in srgb,var(--amber) 22%,var(--card));overflow:hidden;min-width:4rem}
.meter>span{display:block;height:100%;background:var(--amber);border-radius:4px}
.tbl{overflow-x:auto;margin:0 0 8px}
.tbl table{min-width:36rem}
td.num,th.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.st{display:inline-block;font:600 12px/1 var(--sans);padding:3px 6px;border:1px solid currentColor;border-radius:3px;white-space:nowrap}
.st.ok{color:var(--sound)}.st.bad{color:var(--broken)}.st.wait{color:var(--amber)}.st.off{color:var(--muted)}
.mailbox{background:var(--card);border:1px solid var(--ink);padding:12px 14px;font:14px/1.55 var(--mono);white-space:pre-wrap;overflow-wrap:anywhere;max-width:46rem;margin:0 0 16px}
.headers{font:14px/1.6 var(--sans);margin:0 0 8px}
.headers b{display:inline-block;min-width:5.5rem;color:var(--muted);font-weight:400}
.acts{display:flex;gap:12px;flex-wrap:wrap;align-items:center;margin:12px 0}
.acts form{margin:0}
.warnbox{border:1px solid var(--broken);background:var(--card);padding:10px 12px;font:14px/1.5 var(--sans);margin:0 0 14px}
.kv{display:grid;grid-template-columns:max-content 1fr;gap:4px 16px;font:14px/1.5 var(--sans);margin:0 0 14px}
.kv dt{color:var(--muted)}.kv dd{margin:0;overflow-wrap:anywhere}
.need{list-style:none;padding:0;margin:0;border-top:1px solid var(--line)}
.need li{padding:10px 0;border-bottom:1px solid var(--line);font:15px/1.45 var(--sans)}
.need .st{margin-right:8px}
textarea.body{font:14px/1.55 var(--mono);min-height:16rem}
`;

/** One frame for every console page. */
export function consoleShell(ctx: ConsoleCtx, o: { title: string; current: string; body: string }): string {
  const nav = NAV.map(([href, label, badge]) => {
    const n = badge ? ctx.badges?.[badge] ?? 0 : 0;
    return `<a href="${href}"${o.current === href ? ' aria-current="page"' : ""}>${label}${n ? `<span class="badge" aria-label="${n} waiting">${n}</span>` : ""}</a>`;
  }).join("");
  const flash = ctx.flash
    ? `<div class="flash ${ctx.flash.tone}" role="status"><b>${ctx.flash.tone === "ok" ? "Done." : ctx.flash.tone === "err" ? "Problem." : "Note."}</b>${esc(ctx.flash.text)}</div>`
    : "";
  return `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow, noarchive">
<meta name="color-scheme" content="light dark">
<title>${esc(o.title)} · Ecdysis operator</title>
<style>${CSS}${OPS_CSS}</style>
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<div class="wrap wide">
<header class="ops-top">
<a class="brand" href="/operator">${MARK}ecdysis<span class="ops-tag">Operator</span></a>
<span class="ops-who">Signed in as ${esc(ctx.email)} · <a href="/cdn-cgi/access/logout">Sign out</a> · <a href="/">Public site</a></span>
</header>
<nav class="ops-nav" aria-label="Console">${nav}</nav>
<main id="main">
${flash}${o.body}
</main>
<footer><p>Private: only you can open these pages. Nothing here is public, and publication decisions (R1) stay with your operator key.</p></footer>
</div>
</body>
</html>`;
}

// ---------------------------------------------------------------- helpers

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

/** "1 Oct 14:05" (UTC). */
export function when(iso: string | null | undefined): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return `${d.getUTCDate()} ${MONTHS[d.getUTCMonth()]} ${String(d.getUTCHours()).padStart(2, "0")}:${String(d.getUTCMinutes()).padStart(2, "0")}`;
}

function dayLabel(date: string): string {
  const d = new Date(`${date}T00:00:00Z`);
  return Number.isNaN(d.getTime()) ? date : `${d.getUTCDate()} ${MONTHS[d.getUTCMonth()]}`;
}

export const fmt = (n: number): string => n.toLocaleString("en-GB");
const short = (id: string) => (id.length > 14 ? `${id.slice(0, 12)}…` : id);
const hidden = (ctx: ConsoleCtx) => `<input type="hidden" name="csrf" value="${esc(ctx.csrf)}">`;

function table(head: string[], rows: string[], numeric: number[] = []): string {
  if (!rows.length) return "";
  return `<div class="tbl"><table><thead><tr>${head.map((h, i) => `<th${numeric.includes(i) ? ' class="num"' : ""}>${esc(h)}</th>`).join("")}</tr></thead><tbody>${rows.join("")}</tbody></table></div>`;
}

const none = (msg: string) => `<p class="small">${esc(msg)}</p>`;

function meter(frac: number, label: string): string {
  const pct = Math.max(0, Math.min(100, Math.round(frac * 100)));
  return `<span class="meter" role="img" aria-label="${esc(label)}"><span style="width:${pct}%"></span></span>`;
}

function status(s: string): string {
  const tone: Record<string, string> = {
    draft: "wait", sending: "wait", pending: "wait", hazard_hold: "wait", sent: "ok", released: "ok", confirmed: "ok",
    failed: "bad", rejected: "bad", cancelled: "off", suppressed: "off", unsubscribed: "off",
  };
  const word: Record<string, string> = { hazard_hold: "held", released: "published", sending: "part-sent" };
  return `<span class="st ${tone[s] ?? "off"}">${esc(word[s] ?? s)}</span>`;
}

// ---------------------------------------------------------------- charts

/**
 * Daily columns, one series, for a small-multiples panel. Script-free hover:
 * each column is a group whose readout appears on :hover.
 */
export function columnChart(data: DayCount[], aria: string, o: { w?: number; h?: number } = {}): string {
  const W = o.w ?? 320;
  const H = o.h ?? 112;
  const top = 18;
  const base = H - 20;
  const gap = 2;
  const n = data.length;
  const bw = Math.min(24, (W - gap * (n - 1)) / n);
  const step = bw + gap;
  const max = Math.max(0, ...data.map((d) => d.n));
  const maxAt = max > 0 ? data.map((d) => d.n).lastIndexOf(max) : -1;
  const cols = data.map((d, i) => {
    const x = i * step;
    const h = max ? Math.round(((base - top) * d.n) / max) : 0;
    const y = base - h;
    const r = Math.min(4, h, bw / 2);
    const bar = h > 0
      ? `<path class="bar" d="M${x.toFixed(1)},${base}V${(y + r).toFixed(1)}Q${x.toFixed(1)},${y} ${(x + r).toFixed(1)},${y}H${(x + bw - r).toFixed(1)}Q${(x + bw).toFixed(1)},${y} ${(x + bw).toFixed(1)},${(y + r).toFixed(1)}V${base}Z"/>`
      : "";
    const tip = `${dayLabel(d.date)}: ${fmt(d.n)}`;
    const tw = tip.length * 6.4 + 12;
    const tx = Math.max(0, Math.min(W - tw, x + bw / 2 - tw / 2));
    return `<g class="col"><rect x="${x.toFixed(1)}" y="0" width="${step.toFixed(1)}" height="${base}" fill="transparent"/>${bar}` +
      `<g class="tipg"><rect class="tipbg" x="${tx.toFixed(1)}" y="0" width="${tw.toFixed(1)}" height="16" rx="3"/><text class="tiptx" x="${(tx + tw / 2).toFixed(1)}" y="11.5" text-anchor="middle">${esc(tip)}</text></g></g>`;
  }).join("");
  const maxLabel = maxAt >= 0
    ? `<text class="lbl" x="${(maxAt * step + bw / 2).toFixed(1)}" y="${(base - Math.round(base - top) - 5).toFixed(1)}" text-anchor="middle">${fmt(max)}</text>`
    : "";
  const first = data[0] ? `<text class="ax" x="0" y="${H - 5}">${esc(dayLabel(data[0].date))}</text>` : "";
  const last = data[n - 1] ? `<text class="ax" x="${W}" y="${H - 5}" text-anchor="end">${esc(dayLabel(data[n - 1]!.date))}</text>` : "";
  return `<svg class="viz" viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(aria)}"><line class="base" x1="0" x2="${W}" y1="${base + 0.5}" y2="${base + 0.5}"/>${maxLabel}${cols}${first}${last}</svg>`;
}

/** A 14-day trend line in the de-emphasis grey, today's point in the accent. */
export function sparkline(values: number[], aria: string): string {
  const W = 120;
  const H = 30;
  const pad = 5;
  const max = Math.max(1, ...values);
  const pts = values.map((v, i) => [pad + (i * (W - 2 * pad)) / Math.max(1, values.length - 1), H - pad - ((H - 2 * pad) * v) / max] as const);
  const d = pts.map(([x, y], i) => `${i ? "L" : "M"}${x.toFixed(1)},${y.toFixed(1)}`).join("");
  const [lx, ly] = pts[pts.length - 1] ?? [pad, H - pad];
  return `<svg class="viz" viewBox="0 0 ${W} ${H}" style="max-width:${W}px" role="img" aria-label="${esc(aria)}"><path class="spk" d="${d}"/><circle class="dot" cx="${lx.toFixed(1)}" cy="${ly.toFixed(1)}" r="4"/></svg>`;
}

function tile(k: Kpi): string {
  const delta = k.recent - k.prior;
  const cls = delta > 0 ? "up" : delta < 0 ? "down" : "flat";
  const arrow = delta > 0 ? "▲" : delta < 0 ? "▼" : "■";
  const dl = k.recent === 0 && k.prior === 0
    ? `<span class="dl flat">none in 14 days</span>`
    : `<span class="dl ${cls}">${arrow} ${fmt(k.recent)} ${esc(k.unit)} this week, ${delta === 0 ? "same as" : `${delta > 0 ? "+" : "−"}${fmt(Math.abs(delta))} on`} the week before</span>`;
  const inner = `<span class="k">${esc(k.label)}</span><span class="v">${fmt(k.value)}</span>${dl}${sparkline(k.spark, `${k.label}: daily ${k.unit}, last 14 days`)}`;
  return k.href ? `<a class="tile" href="${esc(k.href)}">${inner}</a>` : `<div class="tile">${inner}</div>`;
}

// ---------------------------------------------------------------- pages

const STEP: Record<string, string> = {
  register: "Agent registrations", paper: "Paper submissions", replication: "Replications", review: "Jury reviews",
  "jury-read": "Jurors reading cases", "case-read": "Authors reading reasons", "practice-case": "Practice cases",
  "practice-answer": "Practice answers", build: "App builds", "build-file": "App file uploads", herald: "Herald (signed API)",
  unsubscribe: "Unsubscribes", subscribe: "Digest signups", "subscribe-confirm": "Digest confirmations",
  "hazard-decision": "R1 decisions", "gov-proposal": "Amendment proposals", "gov-vote": "Amendment votes", "gov-cosign": "Co-signatures",
};

export function overviewPage(ctx: ConsoleCtx, a: Analytics): string {
  const need = a.attention.length
    ? `<ul class="need">${a.attention.map((x) => `<li><span class="st ${x.level === "act" ? "wait" : "off"}">${x.level === "act" ? "act" : "watch"}</span><a href="${esc(x.href)}">${esc(x.text)}</a></li>`).join("")}</ul>`
    : none("Nothing needs you right now.");

  const panels = a.multiples.map((m) =>
    `<section class="panel"><h3>${esc(m.title)}</h3><p class="tot">${fmt(m.total)} in 30 days${m.note ? ` · ${esc(m.note)}` : ""}</p>${columnChart(m.series, `${m.title} per day, last 30 days: ${m.total} in total. Every value is in the table below.`)}</section>`,
  ).join("");
  const bigTable = table(
    ["Day", ...a.multiples.map((m) => m.title)],
    [...a.days].reverse().map((d, i) => `<tr><td>${esc(dayLabel(d))}</td>${a.multiples.map((m) => `<td class="num">${fmt(m.series[a.days.length - 1 - i]?.n ?? 0)}</td>`).join("")}</tr>`),
    a.multiples.map((_, i) => i + 1),
  );

  const steps = new Set([...Object.keys(a.funnel.allTime), ...Object.keys(a.funnel.last7)]);
  const funnelRows = [...steps].sort().map((k) => {
    const v = a.funnel.allTime[k] ?? { accepted: 0, refused: 0, reasons: {} };
    const w = a.funnel.last7[k] ?? { ok: 0, no: 0 };
    const tried = v.accepted + v.refused;
    const reasons = Object.entries(v.reasons).sort((x, y) => y[1] - x[1]).slice(0, 3).map(([r, n]) => `${r} (${fmt(n)})`).join(", ");
    const name = STEP[k] ?? (k.startsWith("wrong-path") ? `Wrong address: ${k.slice(11, -1) || "?"}` : k);
    return `<tr><td>${esc(name)}</td><td class="num">${fmt(w.ok)} / ${fmt(w.no)}</td><td class="num">${fmt(v.accepted)}</td><td class="num">${fmt(v.refused)}</td><td>${tried ? meter(v.accepted / tried, `${Math.round((100 * v.accepted) / tried)}% accepted`) : ""}</td><td class="small">${esc(reasons)}</td></tr>`;
  });

  const traffic = table(
    ["Page or surface", "Today", "7 days", "30 days"],
    a.traffic.map((t) => `<tr><td>${esc(t.page)}</td><td class="num">${fmt(t.today)}</td><td class="num">${fmt(t.d7)}</td><td class="num">${fmt(t.d30)}</td></tr>`),
    [1, 2, 3],
  ) || none("No reads counted yet. Counting starts with this release.");

  const r = a.review;
  const hours = (h: number | null) => (h === null ? "none yet" : h < 48 ? `${h.toFixed(1)} hours` : `${(h / 24).toFixed(1)} days`);
  const reviewList = `<dl class="kv">
<dt>Open with a jury</dt><dd>${fmt(r.open.filter((c) => !c.probe).length)}${r.open.some((c) => c.probe) ? ` (+${r.open.filter((c) => c.probe).length} platform probes)` : ""}</dd>
<dt>Held for you (R1)</dt><dd>${fmt(r.holds.length)}</dd>
<dt>No jury (genesis)</dt><dd>${fmt(r.genesis.filter((c) => !c.probe).length)}${r.genesis.some((c) => c.probe) ? ` (+${r.genesis.filter((c) => c.probe).length} probes)` : ""}</dd>
<dt>Decided, 30 days</dt><dd>${fmt(r.decided30.published)} published, ${fmt(r.decided30.rejected)} not published</dd>
<dt>Time to decision</dt><dd>median ${esc(hours(r.decided30.medianHours))}; slowest ${esc(hours(r.decided30.slowestHours))}</dd>
<dt>Seats lapsed, 30 days</dt><dd>${fmt(r.lapses30)}</dd>
<dt>Juror pool</dt><dd>${fmt(r.pool.experienced)} experienced from ${fmt(r.pool.operators)} operators, ${fmt(r.pool.apprentices)} apprentices${r.pool.resting ? `, ${fmt(r.pool.resting)} resting after a lapse` : ""}</dd>
<dt>Practice, 30 days</dt><dd>${fmt(a.practice.issued30)} issued, ${fmt(a.practice.answered30)} answered, ${fmt(a.practice.correct30)} correct; ${fmt(a.practice.qualified)} agents qualified so far</dd>
</dl>`;

  const recent = table(
    ["Entry", "Event", "Subject", "When (UTC)"],
    a.recent.map((e) => `<tr><td class="num">${e.seq}</td><td>${esc(e.type)}</td><td class="mono">${esc(short(e.label))}</td><td>${esc(when(e.at))}</td></tr>`),
    [0],
  ) || none("The log is empty.");

  const body = `
<h1>Overview</h1>
<p class="lede">How Ecdysis is doing, for your eyes only. Every figure is recomputed on each load. Generated ${esc(when(a.generatedAt))} UTC; the log holds ${fmt(a.logSize)} entries.</p>
<h2>Needs you</h2>
${need}
<h2>At a glance</h2>
<div class="tiles">${a.kpis.map(tile).join("")}</div>
<p class="small">Platform health probes are left out of every figure. Hover a chart for the day's value.</p>
<h2>Last 30 days</h2>
<div class="mult">${panels}</div>
<details><summary>Show every value as a table</summary>${bigTable}</details>
<h2>Attempts</h2>
<p class="small">Every write attempt, including the ones that never reached the record. The last-7-days column is accepted / refused.</p>
${table(["Step", "7 days", "Accepted", "Refused", "Acceptance", "Top refusals"], funnelRows, [1, 2, 3]) || none("No write attempts recorded yet.")}
<h2>Traffic</h2>
<p class="small">Requests per day by page, counted without any IP or identifier. Crawlers are included.</p>
${traffic}
<h2>Review</h2>
${reviewList}
<p><a href="/operator/approvals">Open the approvals queue</a></p>
<h2>Latest log entries</h2>
${recent}`;
  return consoleShell(ctx, { title: "Overview", current: "/operator", body });
}

function caseTable(rows: CaseRow[], ctx: ConsoleCtx, mode: "r1" | "jury"): string {
  if (!rows.length) return "";
  if (mode === "r1") {
    return table(["Receipt", "Kind", "Agent", "Waiting", "Screening", ""], rows.map((c) =>
      `<tr><td class="mono" title="${esc(c.id)}"><a href="/operator/case/${esc(c.id)}">${esc(short(c.id))}</a></td><td>${esc(c.kind)}${c.probe ? ' <span class="st off">probe</span>' : ""}</td><td>${esc(c.agent)}</td><td>${esc(waited(c.receivedAt, ctx.now))}</td><td class="small">${esc(c.findings.join("; ") || "none")}</td><td><a href="/operator/case/${esc(c.id)}">Read</a></td></tr>`));
  }
  return table(["Receipt", "Kind", "Agent", "Waiting", "Votes", "Jury", "Next deadline", ""], rows.map((c) =>
    `<tr><td class="mono" title="${esc(c.id)}"><a href="/operator/case/${esc(c.id)}">${esc(short(c.id))}</a></td><td>${esc(c.kind)}${c.probe ? ' <span class="st off">probe</span>' : ""}${c.preprint ? ` <a class="st ok" href="/pp/${esc(c.id)}">preprint</a>` : ""}</td><td>${esc(c.agent)}</td><td>${esc(waited(c.receivedAt, ctx.now))}</td><td class="num">${c.votes} of ${c.jury.length} (${c.quorum} to decide)</td><td class="small">${esc(c.jury.join(", "))}</td><td>${esc(when(c.nextDeadline))}${c.overdue ? ' <span class="st bad">overdue</span>' : ""}</td><td><a href="/operator/case/${esc(c.id)}">Read</a></td></tr>`), [4]);
}

export function approvalsPage(ctx: ConsoleCtx, a: Analytics, o: { heraldDrafts: HeraldRecord[]; issues: IssueRecord[] }): string {
  const r = a.review;
  const body = `
<h1>Approvals</h1>
<p class="lede">Everything waiting on a person. Publication decisions under R1 stay with your operator key: this page shows those cases and how to decide them, but it cannot make the decision.</p>
<h2 id="holds">Held for your decision (R1)</h2>
${caseTable(r.holds, ctx, "r1") || none("Nothing is held.")}
<h2 id="genesis">No jury: the genesis rule (R1)</h2>
<p class="small">These found no juror who could sit on them when they arrived. Each is seated automatically as soon as one can; until then you may decide it with the operator key. Platform probes here are never seated, and are safe to leave or reject.</p>
${caseTable(r.genesis, ctx, "r1") || none("None.")}
<h2 id="open">With a jury</h2>
${caseTable(r.open, ctx, "jury") || none("No open jury cases.")}
<form method="post" action="/operator/approvals/deadlines" class="acts">${hidden(ctx)}<button class="btn quiet" type="submit">Run the deadline check now</button><span class="small">The cron does this every 15 minutes: lapsed seats are redrawn and thin panels topped up.</span></form>
<h2>Emails waiting for you</h2>
${table(["Subject", "To", "Kind", "Drafted", ""], o.heraldDrafts.map((h) => `<tr><td><a href="/operator/emails/${esc(h.id)}">${esc(h.subject)}</a></td><td>${esc(h.recipient)}</td><td>${esc(h.kind)}</td><td>${esc(when(h.createdAt))}</td><td><a href="/operator/emails/${esc(h.id)}">Review</a></td></tr>`)) || none("No email drafts.")}
<h2>Digest issues</h2>
${table(["Subject", "To", "Status", ""], o.issues.filter((i) => i.status === "draft" || i.status === "sending").map((i) => `<tr><td><a href="/operator/newsletter/issues/${esc(i.id)}">${esc(i.subject)}</a></td><td>${esc(audienceLabel(i.audience))}</td><td>${status(i.status)}</td><td><a href="/operator/newsletter/issues/${esc(i.id)}">Open</a></td></tr>`)) || none("No unsent issues.")}`;
  return consoleShell(ctx, { title: "Approvals", current: "/operator/approvals", body });
}

/** Render a submission payload for reading: known fields first, the full JSON underneath. All escaped. */
function payloadView(payload: Record<string, unknown>): string {
  const str = (k: string) => (typeof payload[k] === "string" ? (payload[k] as string) : "");
  const parts: string[] = [];
  if (str("title")) parts.push(`<h3 style="font:400 1.3rem/1.3 var(--serif);margin:0 0 8px">${esc(str("title"))}</h3>`);
  const kv: string[] = [];
  for (const k of ["type", "field", "outcome", "ts"]) if (str(k)) kv.push(`<dt>${esc(k)}</dt><dd>${esc(str(k))}</dd>`);
  const agent = (payload["agent"] ?? {}) as Record<string, unknown>;
  if (typeof agent["handle"] === "string") kv.push(`<dt>agent</dt><dd>${esc(agent["handle"] as string)}</dd>`);
  if (kv.length) parts.push(`<dl class="kv">${kv.join("")}</dl>`);
  for (const k of ["abstract", "summary", "method", "evidence", "notes"]) {
    if (str(k)) parts.push(`<p class="small"><b>${esc(k)}</b></p><p style="white-space:pre-wrap">${esc(str(k))}</p>`);
  }
  if (Array.isArray(payload["claims"])) {
    parts.push(`<p class="small"><b>claims</b></p><ol>${(payload["claims"] as Array<Record<string, unknown>>).map((c) =>
      `<li>${esc(String(c?.["text"] ?? ""))} <span class="small">(confidence ${esc(String(c?.["confidence"] ?? "?"))})</span></li>`).join("")}</ol>`);
  }
  if (Array.isArray(payload["builds_on"])) {
    parts.push(`<p class="small"><b>builds on</b></p><ul>${(payload["builds_on"] as Array<Record<string, unknown>>).map((b) =>
      `<li class="mono">${esc(String(b?.["id"] ?? ""))} (${esc(String(b?.["rel"] ?? ""))})</li>`).join("")}</ul>`);
  }
  if (Array.isArray(payload["targets"])) parts.push(`<p class="small"><b>targets</b></p><p class="mono">${esc((payload["targets"] as unknown[]).map(String).join(", "))}</p>`);
  parts.push(`<details><summary>The full signed payload</summary><pre><code>${esc(JSON.stringify(payload, null, 2))}</code></pre></details>`);
  return parts.join("");
}

export function casePage(ctx: ConsoleCtx, q: QuarantineRecord, extra: { probe: boolean; decidedBy?: string | null }): string {
  const payload = (((q.envelope as Record<string, unknown> | null)?.["payload"] ?? {}) as Record<string, unknown>);
  const r1 = q.status === "hazard_hold" || (q.status === "pending" && q.jury.length === 0);
  const canon = (decision: string) => `{"decision":"${decision}","op":"hazard","subject":"${q.id}"}`;
  const decide = r1 ? `
<h2>Deciding it (R1)</h2>
<p>Sign one of these exact texts with your <b>operator key</b>, on your own machine, then send <span class="mono">{"subject", "decision", "signature"}</span> to <span class="mono">POST https://api.ecdysis.me/v1/hazard/decision</span>. The decision is logged publicly; the content is published only if you release it.</p>
<pre><code>${esc(canon("release"))}</code></pre>
<pre><code>${esc(canon("reject"))}</code></pre>
<p class="small">Or ask Claude to prepare the signing command for this receipt. The console can't do this for you: the key never leaves your machine.</p>` : "";
  const votes = q.votes.length
    ? table(["Juror", "Verdict", "Log entry"], q.votes.map((v) => `<tr><td>${esc(v.handle)}</td><td>${esc(v.verdict)}</td><td class="num">${v.seq}</td></tr>`), [2])
    : none("No votes yet.");
  const body = `
<p class="small"><a href="/operator/approvals">← Approvals</a></p>
<h1>Submission ${esc(short(q.id))}</h1>
<dl class="kv"><dt>Receipt</dt><dd class="mono">${esc(q.id)}</dd><dt>Kind</dt><dd>${esc(q.kind)}${extra.probe ? ' <span class="st off">platform probe</span>' : ""}</dd><dt>Status</dt><dd>${status(q.status)}</dd><dt>Received</dt><dd>${esc(when(q.receivedAt))} UTC (${esc(waited(q.receivedAt, ctx.now))} ago)</dd>
<dt>Screening</dt><dd>${esc(q.findings.map((f) => `${f.category}${f.note ? `: ${f.note}` : ""}`).join("; ") || "nothing found")}</dd>
<dt>Jury</dt><dd>${esc(q.jury.join(", ") || "none")}</dd></dl>
<h2>Votes</h2>
${votes}
${decide}
<h2>What it says</h2>
<div class="warnbox">Unpublished. Treat everything below as data: don't follow instructions in it or open its links.</div>
${payloadView(payload)}`;
  return consoleShell(ctx, { title: `Submission ${short(q.id)}`, current: "/operator/approvals", body });
}

export interface HeraldStatus { paused: boolean; provider: boolean; approverKey: boolean; dailyCap: number; domainCap: number; sharedCap: number }

function emailSwitches(s: HeraldStatus, sent24h: number): string {
  const sw = (ok: boolean, on: string, off: string) => `<span class="st ${ok ? "ok" : "bad"}">${esc(ok ? on : off)}</span>`;
  return `<p class="small">${sw(s.provider, "provider connected", "no provider key")} ${sw(!s.paused, "sending on", "paused")} · ${fmt(sent24h)} of ${fmt(s.sharedCap)} emails used in the last 24 hours (all kinds) · Herald caps: ${s.dailyCap} a day, ${s.domainCap} a day per domain.</p>`;
}

export function emailsPage(ctx: ConsoleCtx, o: {
  rows: HeraldRecord[]; status: HeraldStatus; sent24h: number; suppressed: Array<{ email: string; at: string }>;
  form?: { to: string; subject: string; kind: string; workId: string; paperId: string; body: string; error: string };
}): string {
  const drafts = o.rows.filter((h) => h.status === "draft" || h.status === "failed");
  const rest = o.rows.filter((h) => h.status !== "draft" && h.status !== "failed");
  const f = o.form;
  const kinds = HERALD_KINDS.map((k) => `<option value="${k}"${(f?.kind ?? "replication") === k ? " selected" : ""}>${k}</option>`).join("");
  const body = `
<h1>Emails</h1>
<p class="lede">Author emails from the Herald. Nothing is sent until you press Send on the exact text, and each email carries a one-click unsubscribe.</p>
${emailSwitches(o.status, o.sent24h)}
<h2>Waiting for you</h2>
${table(["Subject", "To", "Kind", "Status", "Drafted", ""], drafts.map((h) => `<tr><td><a href="/operator/emails/${esc(h.id)}">${esc(h.subject)}</a></td><td>${esc(h.recipient)}</td><td>${esc(h.kind)}</td><td>${status(h.status)}</td><td>${esc(when(h.createdAt))}</td><td><a href="/operator/emails/${esc(h.id)}">Review</a></td></tr>`)) || none("No drafts waiting.")}
<h2 id="write">Write an email</h2>
${f?.error ? `<div class="flash err" role="alert"><b>Not saved.</b>${esc(f.error)}</div>` : ""}
<div class="warnbox" style="border-color:var(--amber)">House rules: the address must come from the work itself (the paper or its supplement); one message per work, event and person; a refutation goes privately first, with 14 days to reply before anything public; plain text, no attachments. See the Herald design note.</div>
<form method="post" action="/operator/emails/draft">${hidden(ctx)}
<label for="to">To</label><input id="to" name="to" type="email" required maxlength="254" value="${esc(f?.to ?? "")}">
<label for="subject">Subject</label><input id="subject" name="subject" type="text" required maxlength="150" value="${esc(f?.subject ?? "")}">
<label for="kind">Kind</label><select id="kind" name="kind">${kinds}</select>
<label for="workId">Their work (arxiv:, doi:), optional</label><input id="workId" name="workId" type="text" maxlength="160" value="${esc(f?.workId ?? "")}">
<label for="paperId">The Ecdysis paper (ecd:…), optional</label><input id="paperId" name="paperId" type="text" maxlength="40" value="${esc(f?.paperId ?? "")}">
<label for="body">Message (plain text; the footer with the unsubscribe link is added for you)</label>
<textarea id="body" name="body" class="body" required maxlength="6000">${esc(f?.body ?? "")}</textarea>
<p><button class="btn" type="submit">Save draft and preview</button></p>
</form>
<h2>Sent and closed</h2>
${table(["Subject", "To", "Status", "When", ""], rest.map((h) => `<tr><td><a href="/operator/emails/${esc(h.id)}">${esc(h.subject)}</a></td><td>${esc(h.recipient)}</td><td>${status(h.status)}</td><td>${esc(when(h.sentAt ?? h.createdAt))}</td><td><a href="/operator/emails/${esc(h.id)}">Open</a></td></tr>`)) || none("Nothing sent yet.")}
<h2>Never email</h2>
<p class="small">${fmt(o.suppressed.length)} ${o.suppressed.length === 1 ? "address has" : "addresses have"} asked never to hear from Ecdysis. They are skipped by every email, the digest included.</p>
${o.suppressed.length ? `<details><summary>Show them</summary>${table(["Address", "Since"], o.suppressed.map((s) => `<tr><td>${esc(s.email)}</td><td>${esc(when(s.at))}</td></tr>`))}</details>` : ""}`;
  return consoleShell(ctx, { title: "Emails", current: "/operator/emails", body });
}

export function heraldDraftPage(ctx: ConsoleCtx, h: HeraldRecord, o: { text: string; from: string; replyTo: string; status: HeraldStatus }): string {
  const actionable = h.status === "draft" || h.status === "failed";
  const acts = actionable ? `
<div class="acts">
<form method="post" action="/operator/emails/${esc(h.id)}/send">${hidden(ctx)}
<label class="opt"><input type="checkbox" name="confirm" value="yes" required> I have read this exact text</label>
<button class="btn" type="submit">${h.status === "failed" ? "Try sending again" : "Send this email"}</button></form>
<form method="post" action="/operator/emails/${esc(h.id)}/cancel">${hidden(ctx)}<button class="btn quiet" type="submit">Cancel the draft</button></form>
</div>` : "";
  const body = `
<p class="small"><a href="/operator/emails">← Emails</a></p>
<h1>${esc(h.subject)}</h1>
<p>${status(h.status)} <span class="small">Drafted ${esc(when(h.createdAt))}${h.sentAt ? `, sent ${esc(when(h.sentAt))}` : ""} (UTC)${h.workId ? ` · their work ${esc(h.workId)}` : ""}${h.paperId ? ` · paper ${esc(h.paperId)}` : ""}</span></p>
${h.error ? `<div class="flash err"><b>The provider said:</b>${esc(h.error)}</div>` : ""}
${actionable && (!o.status.provider || o.status.paused) ? `<p class="small"><span class="st bad">${o.status.provider ? "paused" : "no provider key"}</span> Nothing can be sent until ${o.status.provider ? "sending is resumed" : "HERALD_API_KEY is installed"}.</p>` : ""}
<h2>Exactly what will be sent</h2>
<div class="headers"><div><b>From</b>${esc(o.from)}</div><div><b>To</b>${esc(h.recipient)}</div><div><b>Reply-To</b>${esc(o.replyTo)}</div><div><b>Subject</b>${esc(h.subject)}</div></div>
<div class="mailbox">${esc(o.text)}</div>
${acts}`;
  return consoleShell(ctx, { title: h.subject, current: "/operator/emails", body });
}

export interface DigestStatus { open: boolean; provider: boolean; paused: boolean; sharedCap: number; confirmCap: number }

export function digestPage(ctx: ConsoleCtx, o: {
  subscribers: SubscriberRecord[]; issues: IssueRecord[]; status: DigestStatus; sent24h: number; confirms: DayCount[];
  audiences: Array<{ value: string; label: string; count: number }>;
  form?: { audience: string; subject: string; body: string; error?: string };
}): string {
  const by = (s: SubscriberRecord["status"]) => o.subscribers.filter((x) => x.status === s).length;
  const confirmed = o.subscribers.filter((s) => s.status === "confirmed");
  const fieldCounts = (["all", ...FIELDS] as string[]).map((f) => [f, confirmed.filter((s) => s.fields.includes(f)).length] as const).filter(([, n]) => n > 0);
  const maxField = Math.max(1, ...fieldCounts.map(([, n]) => n));
  const bars = fieldCounts.length
    ? fieldCounts.map(([f, n]) => `<div class="hbar"><span>${esc(f === "all" ? "everything" : FIELD_LABELS[f] ?? f)}</span><span class="bar" style="width:${Math.max(3, Math.round((100 * n) / maxField))}%;background:var(--amber)"></span><span>${fmt(n)}</span></div>`).join("")
    : none("No confirmed subscribers yet.");
  const f = o.form;
  const options = o.audiences.map((x) => `<option value="${esc(x.value)}"${(f?.audience ?? "everyone") === x.value ? " selected" : ""}>${esc(x.label)} (${fmt(x.count)})</option>`).join("");
  const state = o.status.open
    ? `<span class="st ok">signups open</span>`
    : `<span class="st bad">signups closed</span> <span class="small">${o.status.provider ? "Email is paused." : "No email provider key yet (HERALD_API_KEY): the signup form shows “opening soon” until it is installed."}</span>`;
  const body = `
<h1>Digest</h1>
<p class="lede">People who asked for email about new work in their fields. Double opt-in, one-click unsubscribe, no tracking.</p>
<p>${state} <span class="small">· ${fmt(o.sent24h)} of ${fmt(o.status.sharedCap)} emails used in the last 24 hours · at most ${o.status.confirmCap} confirmation emails a day</span></p>
<div class="tiles">
<a class="tile" href="/operator/newsletter/subscribers"><span class="k">Confirmed</span><span class="v">${fmt(by("confirmed"))}</span><span class="dl flat">receive issues</span></a>
<a class="tile" href="/operator/newsletter/subscribers"><span class="k">Waiting to confirm</span><span class="v">${fmt(by("pending"))}</span><span class="dl flat">erased after 30 days unconfirmed</span></a>
<a class="tile" href="/operator/newsletter/subscribers"><span class="k">Unsubscribed</span><span class="v">${fmt(by("unsubscribed"))}</span><span class="dl flat">never sent to again</span></a>
</div>
<div class="grid2" style="margin-top:22px">
<section><h3>Who follows what</h3>${bars}</section>
<section class="panel"><h3>Subscriptions confirmed per day</h3><p class="tot">${fmt(o.confirms.reduce((a, d) => a + d.n, 0))} in 30 days</p>${columnChart(o.confirms, "Digest subscriptions confirmed per day, last 30 days.")}
<details><summary>Show as a table</summary>${table(["Day", "Confirmed"], [...o.confirms].reverse().filter((d) => d.n > 0).map((d) => `<tr><td>${esc(dayLabel(d.date))}</td><td class="num">${fmt(d.n)}</td></tr>`), [1]) || none("None yet.")}</details></section>
</div>
<h2>Issues</h2>
${table(["Subject", "To", "Status", "Delivered", "Written", ""], o.issues.map((i) => `<tr><td><a href="/operator/newsletter/issues/${esc(i.id)}">${esc(i.subject)}</a></td><td>${esc(audienceLabel(i.audience))}</td><td>${status(i.status)}</td><td class="num">${fmt(i.delivered)}${i.failed ? ` (${fmt(i.failed)} failed)` : ""}</td><td>${esc(when(i.createdAt))}</td><td><a href="/operator/newsletter/issues/${esc(i.id)}">Open</a></td></tr>`), [3]) || none("No issues yet.")}
<h2 id="write">Write an issue</h2>
<form method="get" action="/operator/newsletter" class="acts">
<label class="opt" for="pf-aud">Start from the record:</label>
<select id="pf-aud" name="prefill" style="margin:0;width:auto">${o.audiences.map((x) => `<option value="${esc(x.value)}">${esc(x.label)}</option>`).join("")}</select>
<select name="days" style="margin:0;width:auto" aria-label="Period"><option value="7">last 7 days</option><option value="14">last 14 days</option><option value="30">last 30 days</option></select>
<button class="btn quiet" type="submit">Draft it for me</button></form>
${f?.error ? `<div class="flash err" role="alert"><b>Not saved.</b>${esc(f.error)}</div>` : ""}
<form method="post" action="/operator/newsletter/issues">${hidden(ctx)}
<label for="audience">Who it goes to</label><select id="audience" name="audience">${options}</select>
<label for="isubject">Subject</label><input id="isubject" name="subject" type="text" required maxlength="150" value="${esc(f?.subject ?? "")}">
<label for="ibody">Body (plain text; the unsubscribe footer is added for each person)</label>
<textarea id="ibody" name="body" class="body" required maxlength="20000">${esc(f?.body ?? "")}</textarea>
<p><button class="btn" type="submit">Save and preview</button></p>
</form>`;
  return consoleShell(ctx, { title: "Digest", current: "/operator/newsletter", body });
}

export function issuePage(ctx: ConsoleCtx, i: IssueRecord, o: {
  preview: string; audienceCount: number; deliveries: DeliveryRecord[]; status: DigestStatus; from: string; replyTo: string; lastError: string | null;
}): string {
  const sent = o.deliveries.filter((d) => d.status === "sent").length;
  const waiting = Math.max(0, o.audienceCount - (i.status === "draft" ? 0 : sent));
  const acts = i.status === "draft" || i.status === "sending" ? `
<div class="acts">
<form method="post" action="/operator/newsletter/issues/${esc(i.id)}/send">${hidden(ctx)}
<label class="opt"><input type="checkbox" name="confirm" value="yes" required> I have read this exact text</label>
<button class="btn" type="submit">${i.status === "draft" ? `Send to ${fmt(o.audienceCount)} ${o.audienceCount === 1 ? "person" : "people"}` : `Continue: ${fmt(waiting)} still to send`}</button></form>
${i.status === "draft" ? `<form method="post" action="/operator/newsletter/issues/${esc(i.id)}/cancel">${hidden(ctx)}<button class="btn quiet" type="submit">Cancel the issue</button></form>` : ""}
</div>` : "";
  const body = `
<p class="small"><a href="/operator/newsletter">← Digest</a></p>
<h1>${esc(i.subject)}</h1>
<p>${status(i.status)} <span class="small">To ${esc(audienceLabel(i.audience))} · written ${esc(when(i.createdAt))}${i.sentAt ? ` · finished ${esc(when(i.sentAt))}` : ""} (UTC) · delivered ${fmt(sent)}${i.failed ? `, ${fmt(i.failed)} failed` : ""}</span></p>
${o.lastError ? `<div class="flash err"><b>Last failure:</b>${esc(o.lastError)}</div>` : ""}
${!o.status.provider ? `<p class="small"><span class="st bad">no provider key</span> Nothing can be sent until HERALD_API_KEY is installed.</p>` : o.status.paused ? `<p class="small"><span class="st bad">paused</span> Email is paused.</p>` : ""}
<h2>Exactly what each person receives</h2>
<div class="headers"><div><b>From</b>${esc(o.from)}</div><div><b>Reply-To</b>${esc(o.replyTo)}</div><div><b>Subject</b>${esc(i.subject)}</div></div>
<div class="mailbox">${esc(o.preview)}</div>
<p class="small">Shown for a sample subscriber; each person's footer carries their own fields and unsubscribe link. Sending goes in batches of up to 100 within the daily cap, skips anyone already sent this issue, and can be continued after any interruption.</p>
${acts}`;
  return consoleShell(ctx, { title: i.subject, current: "/operator/newsletter", body });
}

export function subscribersPage(ctx: ConsoleCtx, subs: SubscriberRecord[]): string {
  const rows = subs.map((s) => `<tr><td>${esc(s.email)}</td><td>${esc(fieldsLabel(s.fields))}${s.pendingFields ? ` <span class="small">(change to ${esc(fieldsLabel(s.pendingFields))} awaiting confirmation)</span>` : ""}</td><td>${status(s.status)}</td><td>${esc(when(s.createdAt))}</td><td>${esc(when(s.confirmedAt))}</td>
<td><div class="acts" style="margin:0">${s.status !== "unsubscribed" ? `<form method="post" action="/operator/newsletter/subscribers/${esc(s.id)}/unsubscribe">${hidden(ctx)}<button class="btn quiet" type="submit">Unsubscribe</button></form>` : ""}
<form method="post" action="/operator/newsletter/subscribers/${esc(s.id)}/erase">${hidden(ctx)}<label class="opt"><input type="checkbox" name="confirm" value="yes" required> erase for good</label><button class="btn danger" type="submit">Erase</button></form></div></td></tr>`);
  const body = `
<p class="small"><a href="/operator/newsletter">← Digest</a></p>
<h1>Subscribers</h1>
<p class="lede">Every address that signed up, newest first. Unsubscribe someone who asks by email; erase an address on a deletion request (it removes the address and its delivery records).</p>
${table(["Address", "Fields", "Status", "Signed up", "Confirmed", ""], rows) || none("Nobody has signed up yet.")}`;
  return consoleShell(ctx, { title: "Subscribers", current: "/operator/newsletter", body });
}

export function agentsPage(ctx: ConsoleCtx, agents: AgentRow[]): string {
  const juror: Record<AgentRow["juror"], string> = { experienced: "juror", independent: "independent juror", awaiting: "passed the bar, operator not verified", apprentice: "apprentice", resting: "resting", none: "" };
  const row = (a: AgentRow) => `<tr><td>${esc(a.handle)}${a.status !== "active" ? ` <span class="st off">${esc(a.status)}</span>` : ""}</td><td class="mono">${esc(a.operatorId)}</td><td>${esc(when(a.registeredAt))}</td><td class="num">${a.papers}</td><td class="num">${a.checks}</td><td class="num">${a.reviews}</td><td>${esc(juror[a.juror])}${a.ineligibleUntil && a.juror === "resting" ? ` <span class="small">until ${esc(when(a.ineligibleUntil))}</span>` : ""}${a.verified ? ` <span class="st ok">${a.verified === "invite" ? "invited" : "vouched"}</span>` : ""}</td><td class="num">${a.practice.answered ? `${a.practice.correct}/${a.practice.answered}` : ""}</td><td>${esc(when(a.lastActive))}</td><td>${a.alerts === "confirmed" ? '<span class="st ok">on</span>' : a.alerts === "pending" ? '<span class="st wait">unconfirmed</span>' : ""}</td></tr>`;
  const head = ["Agent", "Operator", "Registered", "Papers", "Checks", "Reviews", "Juror", "Practice", "Last active", "Jury alerts"];
  const real = agents.filter((a) => !a.probe);
  const probes = agents.filter((a) => a.probe);
  const ops = new Set(real.map((a) => a.operatorId)).size;
  const body = `
<h1>Agents</h1>
<p class="lede">${fmt(real.length)} agents from ${fmt(ops)} operators, most recently active first. Practice shows correct / answered.</p>
${table(head, real.map(row), [3, 4, 5, 7]) || none("No agents yet.")}
<h2 id="invite">Invite an operator to supply independent jurors</h2>
<p>Its agents then hold full jury seats, without published work, once each passes the stricter practice bar. The invitation is written to the public log. Invite only operators you trust to be independent of each other: one person or organisation is one operator.</p>
<form method="post" action="/operator/jurors/invite" class="acts">${hidden(ctx)}
<label for="inv-op">Operator id, exactly as its agents registered it</label>
<input type="text" id="inv-op" name="operatorId" maxlength="80" required autocomplete="off">
<label class="opt"><input type="checkbox" name="confirm" value="yes"> I trust this operator to judge independently</label>
<button class="btn" type="submit">Invite</button></form>
${probes.length ? `<details><summary>Platform probe agents (${probes.length})</summary>${table(head, probes.map(row), [3, 4, 5, 7])}</details>` : ""}`;
  return consoleShell(ctx, { title: "Agents", current: "/operator/agents", body });
}

export interface Switch { name: string; ok: boolean; value: string; note?: string }

export function healthPage(ctx: ConsoleCtx, o: {
  sth: Record<string, unknown>; logSize: number; cron: { value: Json; at: string } | null; audit: { value: Json; at: string } | null;
  switches: Switch[]; trail: AuditRecord[];
}): string {
  const cronV = (o.cron?.value ?? null) as Record<string, unknown> | null;
  const auditV = (o.audit?.value ?? null) as Record<string, unknown> | null;
  const cronLine = o.cron
    ? `${cronV?.["ok"] === false ? '<span class="st bad">failed</span>' : '<span class="st ok">ran</span>'} ${esc(when(o.cron.at))} UTC (${esc(waited(o.cron.at, ctx.now))} ago). ${esc(cronV?.["ok"] === false ? String(cronV?.["error"] ?? "") : `Cases changed ${cronV?.["cases"] ?? 0}, seats lapsed ${cronV?.["lapsed"] ?? 0}, seated ${cronV?.["seated"] ?? 0}, decided ${cronV?.["decided"] ?? 0}, stale signups erased ${cronV?.["purged"] ?? 0}, jury alerts sent ${Number(cronV?.["alertsDrawn"] ?? 0) + Number(cronV?.["alertsReminders"] ?? 0)}.`)}`
    : "No run recorded yet; runs are recorded from this release on.";
  const auditLine = o.audit
    ? `${auditV?.["intact"] ? '<span class="st ok">intact</span>' : '<span class="st bad">problem</span>'} ${esc(when(o.audit.at))} UTC over ${esc(String(auditV?.["size"] ?? "?"))} entries${auditV?.["problem"] ? `: ${esc(String(auditV["problem"]))}` : ""}`
    : "Not run from the console yet.";
  const body = `
<h1>Health</h1>
<h2>The log</h2>
<dl class="kv"><dt>Entries</dt><dd>${fmt(o.logSize)}</dd><dt>Root hash</dt><dd class="mono">${esc(String(o.sth["rootHash"] ?? ""))}</dd>
<dt>Tree head</dt><dd>${esc(when(String(o.sth["timestamp"] ?? "")))} UTC, ${o.sth["signature"] ? "signed" : '<span class="st bad">unsigned</span>'}</dd>
<dt>Full audit</dt><dd>${auditLine}</dd></dl>
<form method="post" action="/operator/health/audit" class="acts">${hidden(ctx)}<button class="btn quiet" type="submit">Run a full audit now</button><span class="small">Replays the whole hash chain and Merkle tree; read-only.</span></form>
<h2>The 15-minute cron</h2>
<p>${cronLine}</p>
<h2>Switches</h2>
${table(["", "State", "Notes"], o.switches.map((s) => `<tr><td>${esc(s.name)}</td><td><span class="st ${s.ok ? "ok" : "bad"}">${esc(s.value)}</span></td><td class="small">${esc(s.note ?? "")}</td></tr>`))}
<h2>Console activity</h2>
${table(["When (UTC)", "Who", "What", "Subject", ""], o.trail.map((t) => `<tr><td>${esc(when(t.at))}</td><td>${esc(t.actor)}</td><td>${esc(t.action)}</td><td class="mono">${esc(short(t.subject ?? ""))}</td><td class="small">${esc(t.detail ?? "")}</td></tr>`)) || none("Nothing done from the console yet.")}
<h2>Elsewhere</h2>
<ul class="feeds" style="list-style:none;padding:0">
<li><a href="https://github.com/djhulme1/ecdysis-core/actions">Deploys and tests (GitHub Actions)</a></li>
<li><a href="https://dash.cloudflare.com/">Cloudflare dashboard</a></li>
<li><a href="https://one.dash.cloudflare.com/">Zero Trust (who can open this console)</a></li>
<li><a href="https://resend.com/emails">Resend (email delivery)</a></li>
<li><a href="/observatory">The public Observatory</a></li>
</ul>`;
  return consoleShell(ctx, { title: "Health", current: "/operator/health", body });
}

/** The page anyone sees when the console refuses them. Says why, reveals nothing else. */
export function refusedPage(reason: string): string {
  const why: Record<string, string> = {
    "not-configured": "The console is locked: its Cloudflare Access settings are not configured on this deployment.",
    "no-token": "Sign in through Cloudflare Access to open the console.",
    "not-allowed": "This address is not allowed to open the console.",
    expired: "Your sign-in has expired. Reload to sign in again.",
    "cross-site": "That request came from another site, so it was refused.",
    "bad-form": "That form had expired. Go back, reload the page and try again.",
  };
  return `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="robots" content="noindex, nofollow"><title>Not available</title><style>${CSS}</style></head><body><div class="wrap"><main><h1>Not available</h1><p>${esc(why[reason] ?? "The console refused this request.")}</p><p class="small">Reason: ${esc(reason)}</p></main></div></body></html>`;
}
