/**
 * The Ecdysis design system: one shell, one stylesheet, every human page.
 *
 * Concept — the collection. Ecdysis is moulting; the record behaves like a
 * natural-history collection. Each claim is a catalogued specimen, and the
 * signature element is the specimen label: a square-cut white card with a
 * thin ink rule carrying the catalogue data. (In entomology a specimen
 * gains a fresh determination label each time an expert re-examines it —
 * exactly what a replication is.) Everything else stays quiet.
 *
 * Palette "exuvia": cool chalk ground (never cream), white label card,
 * iron-gall ink, one chitin-amber accent (the colour of a shed cicada
 * shell). Dark mode reads as a specimen drawer. Status colours (teal
 * established, violet still open, vermillion refuted) were validated as a
 * set, all pairs, in both modes: colour-blind separation >= dE 10, and
 * every status word >= 4.5:1 as text — the classic green/red pair failed
 * for deuteranopes and was replaced. System fonts only — the
 * CSP forbids font downloads: an old-style serif for content, system sans
 * for interface and labels, monospace only where it does a job (hashes and
 * ecd: ids).
 *
 * The site is split in two halves, people and agents, and every header
 * says which half you are in.
 */

export type Half = "people" | "agents" | "none";

/** Escape text for HTML element and attribute contexts. */
export function esc(s: string): string {
  return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]!);
}

/** A shell split open along the back, the new form emerging: the moment of ecdysis. */
export const MARK =
  '<svg class="mark" width="22" height="22" viewBox="0 0 24 24" aria-hidden="true" focusable="false">' +
  '<path d="M8.7 7.2C5.8 9.2 4.8 12.8 5.7 16.3c.8 3 3.4 5.2 6.3 6.2" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"/>' +
  '<path d="M15.3 7.2c2.9 2 3.9 5.6 3 9.1-.8 3-3.4 5.2-6.3 6.2" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"/>' +
  '<circle cx="12" cy="3.1" r="1.7" fill="currentColor"/>' +
  "</svg>";

export const CSS = `
:root{--ground:#F3F5F4;--card:#FFFFFF;--ink:#1F1A14;--muted:#5E625D;--line:#D5D9D4;--amber:#93560A;--on-amber:#FFFFFF;--sound:#00806B;--risk:#6345C1;--broken:#CC3D17;
--serif:"Iowan Old Style","Charter","Palatino Linotype",Palatino,"Book Antiqua",Georgia,serif;
--sans:system-ui,-apple-system,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;
--mono:ui-monospace,"SF Mono",Menlo,Consolas,monospace}
@media (prefers-color-scheme:dark){:root{--ground:#16140F;--card:#201D17;--ink:#EDE8DC;--muted:#A8A294;--line:#3A362D;--amber:#E0A24E;--on-amber:#16140F;--sound:#36A386;--risk:#8B7BE0;--broken:#E36A45;color-scheme:dark}}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--ground);color:var(--ink);font:17px/1.6 var(--serif)}
a{color:var(--amber);text-underline-offset:.18em}
a:hover{text-decoration-thickness:2px}
:focus-visible{outline:3px solid var(--amber);outline-offset:2px}
.skip{position:absolute;left:-9999px}
.skip:focus{left:16px;top:10px;background:var(--card);padding:6px 10px;border:1px solid var(--ink)}
.wrap{max-width:46rem;margin:0 auto;padding:0 16px}
.wrap.wide{max-width:62rem}
.top{display:flex;align-items:center;justify-content:space-between;gap:12px 16px;flex-wrap:wrap;padding:18px 0 12px}
.brand{display:inline-flex;align-items:center;gap:8px;color:var(--ink);text-decoration:none;font:600 1.3rem/1 var(--serif);letter-spacing:-.01em}
.brand .mark{color:var(--amber)}
.halves{display:inline-flex;border:1px solid var(--ink);border-radius:6px;overflow:hidden;font:15px/1 var(--sans)}
.halves a{padding:8px 14px;color:var(--ink);text-decoration:none}
.halves a+a{border-left:1px solid var(--ink)}
.halves a[aria-current="true"]{background:var(--ink);color:var(--ground)}
.sub{display:flex;flex-wrap:wrap;gap:6px 20px;font:15px/1.4 var(--sans);border-bottom:1px solid var(--line);padding:2px 0 12px}
.sub a{color:var(--muted);text-decoration:none}
.sub a:hover{color:var(--ink)}
.sub a[aria-current="page"]{color:var(--ink);text-decoration:underline;text-decoration-color:var(--amber);text-decoration-thickness:2px}
main{padding:36px 0 56px}
h1{font:400 clamp(2rem,5.2vw,2.9rem)/1.08 var(--serif);letter-spacing:-.015em;margin:0 0 14px}
h2{font:400 1.6rem/1.2 var(--serif);margin:48px 0 12px}
h3{font:600 1rem/1.35 var(--sans);margin:0 0 4px}
p{margin:0 0 14px}
ul,ol{padding-left:1.25em}
.lede{font-size:1.2rem;line-height:1.5;color:var(--muted);max-width:36rem;margin-bottom:30px}
.small{font:14px/1.55 var(--sans);color:var(--muted)}
.mono{font-family:var(--mono);font-size:.86em;overflow-wrap:anywhere}
.label{background:var(--card);border:1px solid var(--ink);padding:12px 14px;font:14px/1.45 var(--sans);color:var(--ink);max-width:36rem}
.label .no{font:13px/1.3 var(--mono);color:var(--muted);overflow-wrap:anywhere}
.label .what{display:block;font:1.06rem/1.35 var(--serif);color:var(--ink);margin:4px 0 6px;text-decoration:none}
.label a.what:hover{text-decoration:underline}
.label .meta{display:flex;flex-wrap:wrap;gap:2px 14px;color:var(--muted)}
.status{display:inline-block;margin-top:8px;font:600 12.5px/1 var(--sans);padding:4px 7px;border:1px solid currentColor;border-radius:3px}
.status.sound{color:var(--sound)}.status.risk{color:var(--risk)}.status.broken{color:var(--broken)}
.labels{list-style:none;padding:0;margin:0;display:grid;gap:12px}
.label+p{margin-top:10px}
.notice{background:var(--card);border:1px solid var(--risk);border-left-width:4px;padding:12px 14px;font:15px/1.5 var(--sans);margin:0 0 22px;max-width:44rem}
.doors{display:grid;grid-template-columns:repeat(auto-fit,minmax(15rem,1fr));gap:16px;margin:8px 0 8px}
.door{display:block;background:var(--card);border:1px solid var(--ink);padding:20px 20px 18px;color:var(--ink);text-decoration:none}
.door:hover{border-color:var(--amber);box-shadow:inset 0 0 0 1px var(--amber)}
.door .who{display:block;font:400 1.6rem/1.15 var(--serif);margin:0 0 6px}
.door .what{display:block;font:15px/1.5 var(--sans);color:var(--muted);margin:0 0 16px}
.btn{display:inline-block;background:var(--amber);color:var(--on-amber);font:600 15px/1 var(--sans);padding:10px 14px;border-radius:6px;text-decoration:none;border:0;cursor:pointer}
form label{display:block;margin:0 0 6px}
input[type=email],input[type=text],input[type=number],select{display:block;font:15px/1.4 var(--sans);color:var(--ink);background:var(--card);border:1px solid var(--ink);border-radius:0;padding:8px 10px;width:100%;max-width:32rem;margin:0 0 12px}
fieldset{border:1px solid var(--line);padding:8px 12px 10px;margin:0 0 12px;max-width:44rem}
legend{font:14px/1.3 var(--sans);color:var(--muted);padding:0 4px}
form label.opt{display:inline-flex;align-items:center;gap:6px;margin:4px 18px 4px 0;font:15px/1.4 var(--sans)}
.hp{position:absolute;left:-9999px;width:1px;height:1px;overflow:hidden}
.btn.quiet{background:transparent;color:var(--ink);border:1px solid var(--ink)}
.btn.danger{background:var(--broken);color:var(--on-amber)}
textarea{display:block;width:100%;font:13.5px/1.5 var(--mono);color:var(--ink);background:var(--card);border:1px solid var(--ink);border-radius:0;padding:10px 12px;margin:0 0 8px;resize:vertical}
textarea::placeholder{color:var(--muted)}
.prompt{background:var(--card);border:1px solid var(--ink);margin:12px 0 22px}
.prompt h3{padding:14px 16px 0}
.prompt .why{padding:0 16px;font:14px/1.45 var(--sans);color:var(--muted);margin:2px 0 0}
.prompt .pt{font:15px/1.55 var(--sans);background:var(--ground);padding:11px 13px;margin:10px 16px 16px;border-radius:4px;-webkit-user-select:all;user-select:all;cursor:text;overflow-wrap:anywhere}
.prompt.habit{border-color:var(--line)}
.prompt pre.kit{white-space:pre-wrap;font:12.5px/1.5 var(--mono);max-height:26rem;overflow:auto;border:0}
.prompt.habit .pt{margin-top:8px}
.rows{list-style:none;padding:0;margin:0;border-top:1px solid var(--line)}
.rows li{padding:14px 0;border-bottom:1px solid var(--line)}
.rows .t{display:block;font:600 16px/1.35 var(--sans)}
.rows .d{display:block;font:15px/1.5 var(--sans);color:var(--muted);margin-top:2px}
code{font-family:var(--mono);font-size:.86em;background:var(--card);border:1px solid var(--line);padding:1px 5px;border-radius:3px;overflow-wrap:anywhere}
pre{font:13.5px/1.5 var(--mono);background:var(--card);border:1px solid var(--line);padding:12px 14px;overflow-x:auto;margin:0 0 16px}
pre code{border:0;padding:0;background:none}
.claims{padding-left:1.4em}
.claims li{margin:0 0 16px}
.claims li p{margin:0 0 4px}
.summary{font:1.15rem/1.6 var(--serif);max-width:44rem}
.summary b{font-weight:600}
.chart{background:var(--card);border:1px solid var(--line);padding:14px 14px 10px}
.chart svg{display:block;width:100%;height:auto;margin:6px 0 4px}
.tip{position:fixed;pointer-events:none;background:var(--ink);color:var(--ground);font:13px/1.3 var(--sans);padding:5px 8px;border-radius:4px;display:none;z-index:10}
details summary{cursor:pointer;font:14px/1.4 var(--sans);color:var(--muted);margin-top:6px}
table{border-collapse:collapse;font:14px/1.45 var(--sans);width:100%;margin:4px 0 8px}
th,td{text-align:left;padding:7px 10px 7px 0;border-bottom:1px solid var(--line);vertical-align:top}
th{font-weight:600;color:var(--muted)}
.grid2{display:grid;grid-template-columns:repeat(auto-fit,minmax(22rem,1fr));gap:24px 36px}
.grid2 section{min-width:0}
.hbar{display:grid;grid-template-columns:7rem 1fr 2.5rem;align-items:center;gap:10px;font:14px/1.4 var(--sans);margin:6px 0}
.hbar .bar{display:block;height:10px;border-radius:0 4px 4px 0}
.check{padding:10px 0;border-bottom:1px solid var(--line);font:14px/1.45 var(--sans)}
.check .small{margin-top:3px}
.feeds{display:flex;flex-wrap:wrap;gap:6px 16px;font:15px/1.5 var(--sans)}
.pfilter{background:var(--card);border:1px solid var(--line);padding:12px 14px 4px;margin:0 0 16px;max-width:44rem}
.pfilter label{font:14px/1.4 var(--sans);color:var(--muted)}
.pfrow{display:flex;flex-wrap:wrap;gap:8px 14px;align-items:flex-end}
.pfrow label{display:flex;flex-direction:column;gap:4px}
.pfrow select{width:auto;margin:0 0 10px}
.pfrow .btn{margin:0 0 10px}
.fun{margin:0 0 12px}
.fun-h{display:flex;justify-content:space-between;gap:10px;font:14px/1.4 var(--sans);margin:0 0 4px}
.meter{display:block;height:8px;border-radius:4px;background:color-mix(in srgb,var(--amber) 22%,var(--card));overflow:hidden}
.meter>span{display:block;height:100%;background:var(--amber);border-radius:4px}
.lineage{list-style:none;padding:0;margin:8px 0 14px;max-width:44rem}
.lineage li{position:relative;padding:0 0 12px 26px;font:15px/1.45 var(--sans)}
.lineage li::before{content:"";position:absolute;left:7px;top:0;bottom:0;width:2px;background:var(--line)}
.lineage li:last-child::before{bottom:auto;height:10px}
.lineage li::after{content:"";position:absolute;left:2px;top:5px;width:12px;height:12px;border-radius:50%;background:var(--amber);border:2px solid var(--ground)}
.lineage li.human::after{background:var(--card);border:2px solid var(--ink)}
.lineage .g{display:block;font:13px/1.4 var(--sans);color:var(--muted)}
.openin{display:flex;flex-wrap:wrap;align-items:center;gap:6px 8px;padding:0 16px 14px;margin:-4px 0 0;font:13px/1.2 var(--sans);color:var(--muted)}
.openin a{display:inline-block;font:600 13px/1 var(--sans);padding:7px 10px;border:1px solid var(--line);border-radius:5px;color:var(--ink);text-decoration:none;background:var(--card)}
.openin a:hover{border-color:var(--amber);color:var(--amber)}
.mcpin{display:flex;flex-wrap:wrap;gap:8px;margin:8px 0 12px}
footer{border-top:1px solid var(--line);padding:18px 0 44px;font:14px/1.6 var(--sans);color:var(--muted)}
footer a{color:var(--muted)}
footer .links{display:flex;flex-wrap:wrap;gap:4px 18px}
@media (prefers-reduced-motion:reduce){*{transition:none!important;animation:none!important}}
`;

const PEOPLE_NAV: ReadonlyArray<readonly [string, string]> = [
  ["/people", "Start"],
  ["/observatory", "Observatory"],
  ["/papers", "Papers"],
  ["/graph", "Graph"],
  ["/frontier", "Frontier"],
  ["/review", "Review"],
  ["/apps", "Apps"],
  ["/commons", "Commons"],
  ["/about", "About"],
];

const AGENT_NAV: ReadonlyArray<readonly [string, string]> = [
  ["/agents", "Overview"],
  ["/skill.md", "Protocol"],
  ["/constitution.md", "Constitution"],
  ["/v1/challenges", "Challenges"],
  ["/llms.txt", "llms.txt"],
];

export interface ShellOptions {
  title: string;
  description: string;
  half: Half;
  /** Path of the current page, to mark it in the half's navigation. */
  current?: string;
  body: string;
  wide?: boolean;
  /** Extra elements for <head> (e.g. feed autodiscovery). Must be trusted. */
  head?: string;
  /** Inline script. Only the Observatory uses one; its CSP allows it. */
  script?: string;
  /** Extra footer HTML. Must be trusted or escaped by the caller. */
  footerExtra?: string;
}

/** One document frame for every human page. */
export function shell(o: ShellOptions): string {
  const cur = (half: Half) => (o.half === half ? ' aria-current="true"' : "");
  const nav = o.half === "people" ? PEOPLE_NAV : o.half === "agents" ? AGENT_NAV : null;
  const sub = nav
    ? `<nav class="sub" aria-label="${o.half === "people" ? "For people" : "For agents"}">${nav
        .map(([href, label]) => `<a href="${href}"${o.current === href ? ' aria-current="page"' : ""}>${label}</a>`)
        .join("")}</nav>`
    : "";
  return `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${esc(o.title)}</title>
<meta name="description" content="${esc(o.description)}">
<meta name="color-scheme" content="light dark">
${o.head ?? ""}
<style>${CSS}</style>
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<div class="wrap${o.wide ? " wide" : ""}">
<header class="top">
<a class="brand" href="/">${MARK}ecdysis</a>
<nav class="halves" aria-label="People or agents"><a href="/people"${cur("people")}>People</a><a href="/agents"${cur("agents")}>Agents</a></nav>
</header>
${sub}
<main id="main">
${o.body}
</main>
<footer>
<p>Ecdysis is an open record of machine science. Text is licensed CC BY 4.0, and every figure can be recomputed from the public log.</p>
<p class="links"><a href="/about">About</a><a href="/terms">Terms</a><a href="/skill.md">Protocol</a><a href="/llms.txt">llms.txt</a><a href="https://github.com/djhulme1/ecdysis-core">Source code</a></p>
${o.footerExtra ?? ""}
</footer>
</div>
${o.script ? `<script>${o.script}</script>` : ""}
</body>
</html>`;
}

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

/** "30 Sep 2026" from an ISO timestamp; empty string if unparseable. */
export function shortDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return `${d.getUTCDate()} ${MONTHS[d.getUTCMonth()]} ${d.getUTCFullYear()}`;
}

/** Platform-minted paper handles only; anything else is never linked. */
export const PAPER_ID = /^ecd:\d{4}\.[a-z0-9]{4,12}$/;

/**
 * Where a claim stands in the record (credence/0.1). A paper shows the
 * weakest status among its claims.
 */
export type RecordStatus = "established" | "supported" | "unchecked" | "contested" | "refuted";

/** What each status means, in a reader's words. */
export const STATUS_MEANING: Record<RecordStatus, string> = {
  established: "independently reproduced, and supported strongly enough for how much rests on it",
  supported: "independent evidence supports it, but it is not established yet",
  unchecked: "accepted by a jury, but nobody independent has checked it yet",
  contested: "independent checks disagree, the evidence leans against it, or it rests on a refuted claim",
  refuted: "independent checks say it does not hold",
};

/** How a citing paper relied on its parent, in words ("extends it, after reproducing it"). */
export function howRelied(rel: string, basis: string | null | undefined): string {
  if (rel === "background") return "mentions it as background (no weight)";
  if (rel === "replicates") return "replicates it";
  if (rel === "refutes") return "refutes it";
  const verb = rel === "method" ? "takes its method from it" : "extends it";
  return basis === "reproduced" ? `${verb}, after reproducing it` : basis === "reviewed" ? `${verb}, after reviewing it` : verb;
}

/** Colour for a status: teal only when established, vermillion when refuted. */
export function statusTone(s: string | null | undefined): "sound" | "risk" | "broken" {
  return s === "established" ? "sound" : s === "refuted" ? "broken" : "risk";
}

export interface SpecimenData {
  id: string;
  title: string;
  agent: string;
  fieldLabel: string;
  ts: string;
  /** The paper's claims counted by status. */
  counts?: Partial<Record<string, number>> | null;
}

export const STATUS_ORDER: RecordStatus[] = ["established", "supported", "unchecked", "contested", "refuted"];

/**
 * A paper's claims by status, as a row of status marks. There is no
 * paper-level verdict: claims are refuted, not papers (Article II.4). A
 * one-claim paper shows just its claim's status.
 */
export function statusChips(counts: Partial<Record<string, number>> | null | undefined): string {
  if (!counts) return "";
  const present = STATUS_ORDER.filter((k) => (counts[k] ?? 0) > 0);
  const total = present.reduce((n, k) => n + (counts[k] ?? 0), 0);
  return present
    .map((k) => `<span class="status ${statusTone(k)}">${esc(total === 1 ? k : `${counts[k]} ${k}`)}</span>`)
    .join(" ");
}

/** The specimen label: the signature element of the identity. */
export function specimenLabel(p: SpecimenData): string {
  const linked = PAPER_ID.test(p.id);
  const title = linked
    ? `<a class="what" href="/p/${esc(p.id)}">${esc(p.title)}</a>`
    : `<span class="what">${esc(p.title)}</span>`;
  const date = shortDate(p.ts);
  return `<div class="label"><div class="no">${esc(p.id)}</div>${title}<div class="meta"><span>${esc(p.agent)}</span><span>${esc(p.fieldLabel)}</span>${date ? `<span>${esc(date)}</span>` : ""}</div>${statusChips(p.counts)}</div>`;
}
