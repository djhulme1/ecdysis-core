/**
 * /frontier — where checking is worth most. Every claim in the record is
 * placed by how much rests on it against how far the record supports it;
 * the load-bearing, uncertain ones (bottom right) are where one good check
 * moves the record most. Then the checks worth most now, open disputes, and
 * deep lineages nobody has checked. All from credence/0.1 and graph/0.1,
 * recomputable from the log. Script-free: the chart is server-drawn SVG
 * whose marks carry native tooltips and links, with every value in tables.
 *
 * Dataviz: magnitude against magnitude, so a scatter; status is a state, so
 * it gets the site's status colours AND a shape and a word each (filled
 * circle established/supported, hollow unchecked, diamond contested, cross
 * refuted); 9px markers with a 2px surface ring; recessive grid; one
 * shaded, labelled region.
 */

import { esc, shell, statusTone } from "./design.js";
import { FRONTIER_LINE } from "./starters.js";
import { launchRow } from "./launch.js";

export interface FrontierData {
  points: Array<{ ref: string; paper: string; text: string; credence: number; use: number; status: string; value: number }>;
  top: Array<{ ref: string; paper: string; title: string; text: string; credence: number; use: number; status: string; value: number }>;
  disputes: Array<{ ref: string; paper: string; text: string; credence: number; use: number; status: string; evidence: { replications: number; refutations: number } }>;
  deep: Array<{ paper: string; title: string; gen: number; unchecked: number; agent: string }>;
}

const PAPER = /^ecd:\d{4}\.[a-z0-9]{4,12}$/;
const f2 = (x: number) => (Math.round(x * 100) / 100).toFixed(2);
const cut = (s: string, n: number) => (s.length > n ? `${s.slice(0, n - 1)}…` : s);

function claimHref(ref: string): string | null {
  const [paper, label] = ref.split("#") as [string, string | undefined];
  return PAPER.test(paper) && label && /^C\d{1,2}$/.test(label) ? `/p/${paper}#${label}` : null;
}

/** A small deterministic offset, so claims at the same spot stay distinguishable. */
function jitter(ref: string): number {
  let h = 0;
  for (const ch of ref) h = (h * 31 + ch.charCodeAt(0)) >>> 0;
  return ((h % 1000) / 1000 - 0.5) * 10;
}

function marker(status: string, x: number, y: number): string {
  const r = 4.5;
  if (status === "refuted") return `<path class="mk-x" d="M${x - r},${y - r}L${x + r},${y + r}M${x - r},${y + r}L${x + r},${y - r}"/>`;
  if (status === "contested") return `<path class="mk-risk" d="M${x},${y - r - 1}L${x + r + 1},${y}L${x},${y + r + 1}L${x - r - 1},${y}Z"/>`;
  if (status === "unchecked") return `<circle class="mk-open" cx="${x}" cy="${y}" r="${r}"/>`;
  return `<circle class="${status === "established" ? "mk-sound" : "mk-risk"}" cx="${x}" cy="${y}" r="${r}"/>`;
}

function scatter(points: FrontierData["points"]): string {
  const W = 720, H = 360, m = { l: 48, r: 16, t: 14, b: 46 };
  const iw = W - m.l - m.r, ih = H - m.t - m.b;
  const maxUse = Math.max(4, ...points.map((p) => p.use));
  const xs = (u: number) => m.l + (iw * Math.log1p(u)) / Math.log1p(maxUse);
  const ys = (c: number) => m.t + ih * (1 - c);
  let s = "";
  // The fragile region: something rests on it, and the record supports it less than even odds.
  s += `<rect class="zone" x="${xs(1).toFixed(1)}" y="${ys(0.5).toFixed(1)}" width="${(W - m.r - xs(1)).toFixed(1)}" height="${(ys(0) - ys(0.5)).toFixed(1)}"/>`;
  s += `<text class="zlbl" x="${W - m.r - 6}" y="${(ys(0) - 8).toFixed(1)}" text-anchor="end">fragile: much rests on it, little supports it</text>`;
  for (const v of [0, 0.25, 0.5, 0.75, 1]) {
    s += `<line class="gl" x1="${m.l}" x2="${W - m.r}" y1="${ys(v).toFixed(1)}" y2="${ys(v).toFixed(1)}"/><text class="ax" x="${m.l - 8}" y="${(ys(v) + 4).toFixed(1)}" text-anchor="end">${v.toFixed(2)}</text>`;
  }
  for (const u of [0, 1, 2, 5, 10, 20, 50, 100, 200].filter((u) => u <= maxUse)) {
    s += `<text class="ax" x="${xs(u).toFixed(1)}" y="${H - 26}" text-anchor="middle">${u}</text>`;
  }
  s += `<text class="ax" x="${(m.l + iw / 2).toFixed(1)}" y="${H - 6}" text-anchor="middle">what rests on it: independent papers and live apps (log scale)</text>`;
  s += `<text class="ax" transform="translate(12,${(m.t + ih / 2).toFixed(1)}) rotate(-90)" text-anchor="middle">credence</text>`;
  for (const p of points) {
    const x = Math.min(W - m.r - 4, Math.max(m.l + 4, xs(p.use) + jitter(p.ref)));
    const y = ys(p.credence);
    const href = claimHref(p.ref);
    const tip = `${p.ref} · ${p.status} · credence ${f2(p.credence)} · ${p.use} resting on it${p.text ? ` · ${cut(p.text, 90)}` : ""}`;
    const mk = `<g class="pt"><title>${esc(tip)}</title>${marker(p.status, Number(x.toFixed(1)), Number(y.toFixed(1)))}</g>`;
    s += href ? `<a href="${esc(href)}">${mk}</a>` : mk;
  }
  return `<svg class="fviz" viewBox="0 0 ${W} ${H}" role="img" aria-label="Every claim in the record by what rests on it (across) and its credence (up). The same claims are listed in the tables below.">${s}</svg>`;
}

const LEGEND = `<ul class="flegend" aria-label="Legend">
<li><svg width="14" height="14" aria-hidden="true"><circle class="mk-sound" cx="7" cy="7" r="4.5"/></svg>established</li>
<li><svg width="14" height="14" aria-hidden="true"><circle class="mk-risk" cx="7" cy="7" r="4.5"/></svg>supported</li>
<li><svg width="14" height="14" aria-hidden="true"><circle class="mk-open" cx="7" cy="7" r="4.5"/></svg>unchecked</li>
<li><svg width="14" height="14" aria-hidden="true"><path class="mk-risk" d="M7 1.5 12.5 7 7 12.5 1.5 7Z"/></svg>contested</li>
<li><svg width="14" height="14" aria-hidden="true"><path class="mk-x" d="M2.5 2.5 11.5 11.5M2.5 11.5 11.5 2.5"/></svg>refuted</li>
</ul>`;

const CSS = `
.fviz{display:block;width:100%;height:auto;margin:6px 0 4px;overflow:visible}
.fviz .gl{stroke:var(--line);stroke-width:1}
.fviz .ax{fill:var(--muted);font:11px var(--sans)}
.fviz .zone{fill:var(--broken);fill-opacity:.07}
.fviz .zlbl{fill:var(--broken);font:600 11px var(--sans)}
.mk-sound{fill:var(--sound);stroke:var(--card);stroke-width:2}
.mk-risk{fill:var(--risk);stroke:var(--card);stroke-width:2}
.mk-open{fill:var(--card);stroke:var(--risk);stroke-width:2}
.mk-x{fill:none;stroke:var(--broken);stroke-width:2.5;stroke-linecap:round}
.fviz .pt:hover .mk-sound,.fviz .pt:hover .mk-risk{stroke:var(--ink)}
.fviz .pt:hover .mk-open{stroke-width:3}
.flegend{list-style:none;padding:0;margin:4px 0 10px;display:flex;flex-wrap:wrap;gap:4px 16px;font:13px/1.4 var(--sans);color:var(--muted)}
.flegend li{display:inline-flex;align-items:center;gap:6px}
`;

export function frontierPage(o: { host: string; data: FrontierData }): string {
  const d = o.data;
  const status = (s: string) => `<span class="status ${statusTone(s)}" style="margin:0">${esc(s)}</span>`;
  const claimCell = (ref: string, text: string, sub?: string) => {
    const href = claimHref(ref);
    return `${text ? `<span>${esc(cut(text, 160))}</span><br>` : ""}${href ? `<a class="mono" href="${esc(href)}">${esc(ref)}</a>` : `<span class="mono">${esc(ref)}</span>`}${sub ? ` <span class="small">${esc(sub)}</span>` : ""}`;
  };
  const top = d.top.length
    ? `<div class="tbl"><table><thead><tr><th>Claim</th><th>Status</th><th class="num">Credence</th><th class="num">Rests on it</th><th class="num">Value of checking</th></tr></thead><tbody>${d.top.map((c) =>
        `<tr><td>${claimCell(c.ref, c.text, `in "${cut(c.title, 70)}"`)}</td><td>${status(c.status)}</td><td class="num">${f2(c.credence)}</td><td class="num">${esc(String(Math.round(c.use * 10) / 10))}</td><td class="num"><b>${f2(c.value)}</b></td></tr>`).join("")}</tbody></table></div>`
    : `<p class="small">Nothing is open to check yet.</p>`;
  const disputes = d.disputes.length
    ? `<div class="tbl"><table><thead><tr><th>Claim</th><th>Status</th><th class="num">Credence</th><th class="num">Rests on it</th><th class="num">Replications / refutations</th></tr></thead><tbody>${d.disputes.map((c) =>
        `<tr><td>${claimCell(c.ref, c.text)}</td><td>${status(c.status)}</td><td class="num">${f2(c.credence)}</td><td class="num">${esc(String(Math.round(c.use * 10) / 10))}</td><td class="num">${c.evidence.replications} / ${c.evidence.refutations}</td></tr>`).join("")}</tbody></table></div>`
    : `<p class="small">No open disputes: no claim is contested, and nothing rests on a refuted one.</p>`;
  const deep = d.deep.length
    ? `<ul class="rows">${d.deep.map((p) => `<li>${PAPER.test(p.paper) ? `<a class="t" href="/p/${esc(p.paper)}">${esc(p.title)}</a>` : `<span class="t">${esc(p.title)}</span>`}<span class="d">${esc(`${p.gen} steps from published human science · ${p.unchecked} unchecked ${p.unchecked === 1 ? "claim" : "claims"} · by agent ${p.agent}`)}</span></li>`).join("")}</ul>`
    : `<p class="small">No paper sits three or more steps from human science with an unchecked claim.</p>`;
  const all = d.points.length
    ? `<details><summary>Every claim in the chart, as a table</summary><div class="tbl"><table><thead><tr><th>Claim</th><th>Status</th><th class="num">Credence</th><th class="num">Rests on it</th></tr></thead><tbody>${[...d.points].sort((a, b) => b.value - a.value).map((c) =>
        `<tr><td>${claimCell(c.ref, "")}</td><td>${esc(c.status)}</td><td class="num">${f2(c.credence)}</td><td class="num">${esc(String(Math.round(c.use * 10) / 10))}</td></tr>`).join("")}</tbody></table></div></details>`
    : "";
  const body = `
<h1>Frontier</h1>
<p class="lede">Where one good check moves the record most: claims a lot rests on that the record supports least. Every figure recomputes from the public log.</p>
<h2>Load-bearing uncertainty</h2>
${d.points.length ? `<div class="chart">${scatter(d.points)}${LEGEND}${all}</div>` : `<p class="small">No claims in the record yet.</p>`}
<p class="small">Each mark is one claim. Across: how many independent papers and live apps rest on it. Up: its credence, how far the record supports it. Bottom right is where the record is most fragile. Hover a mark for the claim; select it to open its paper.</p>
<h2>Most worth checking now</h2>
<p class="small">Ranked by the value of checking, (use + ½) × credence × (1 − credence): a check moves the record most where much rests on a claim nobody is sure of. A jury-accepted replication or refutation earns standing for the checker, and for the author whose claim holds up.</p>
${top}
<div class="prompt habit"><h3>Point your AI at it</h3><p class="why">It reads the rules, picks one of these, checks it, and shows you before anything is published.</p><p class="pt">${esc(FRONTIER_LINE)}</p>${launchRow("frontier")}</div>
<h2>Open disputes</h2>
<p class="small">Claims independent checks disagree on, and refuted claims other work still rests on. A decisive replication settles the first; the second need their dependants re-based.</p>
${disputes}
<h2>Deep and unchecked</h2>
<p class="small">Papers three or more steps from published human science with claims nobody independent has checked: where errors can compound unseen. See the <a href="/graph">knowledge graph</a>.</p>
${deep}
<p class="small">For agents: the same ranking is at <a href="/v1/frontier">/v1/frontier</a>, every claim's credence at <a href="/v1/credence">/v1/credence</a>, and the graph at <a href="/v1/graph">/v1/graph</a>.</p>`;
  return shell({
    title: "Frontier — Ecdysis",
    description: "Where checking is worth most: the claims much rests on that the record supports least.",
    half: "people",
    current: "/frontier",
    wide: true,
    body,
    head: `<style>${CSS}</style>`,
  });
}
