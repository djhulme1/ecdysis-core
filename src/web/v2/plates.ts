/**
 * The site's explanatory plates: the credence ruler in its three sizes, the anatomy of a claim, and a claim's place in the
 * network. Drawn like the plates of a natural-history catalogue: fine ink lines, words as words, the one orange only where
 * something asks for attention. Script-free; every colour is a design token, so each reads in both themes; every value from
 * a submission is escaped.
 *
 * The ruler is the record's one measure made visible: credence runs from 0 to 1, and the statuses are thresholds on it,
 * each with the evidence it needs (refuted below 0.35, supported from 0.6, established from the bar its use sets).
 */

import { esc, statusTone } from "../design.js";
import { STATUS_GLYPH } from "./viz.js";

/** The thresholds a status reads (credence/0.4): refuted below, supported from, and the base bar for established at no use. */
export const RULER = { refuted: 0.35, supported: 0.6, established: 0.9 } as const;

const two = (x: number) => (Math.round(x * 100) / 100).toFixed(2);
const clamp01 = (x: number) => Math.min(1, Math.max(0, Number.isFinite(x) ? x : 0));

/** A row's credence: a short bar and the number, for tables. The status is carried by its own column, never by this colour alone. */
export function rulerMini(credence: number, status: string): string {
  const c = clamp01(credence);
  return `<span class="rmini" role="img" aria-label="credence ${two(c)}"><span class="rtrack"><span class="rfill ${statusTone(status)}" style="width:${(c * 100).toFixed(1)}%"></span><span class="rtick" style="left:${RULER.supported * 100}%"></span></span><b>${two(c)}</b></span>`;
}

/**
 * One claim's credence on the full ruler: where it stands, where its author's confidence put it (its prior, after
 * calibration), and the thresholds, the bar for established drawn where this claim's use sets it. A conceptual claim is never
 * established, so its ruler stops at supported. HTML, so its words stay words at every width.
 */
export function rulerLarge(o: { credence: number; prior: number | null; bar: number; status: string; conceptual?: boolean; compact?: boolean }): string {
  const c = clamp01(o.credence);
  const bar = clamp01(o.bar);
  const at = (v: number) => `${(clamp01(v) * 100).toFixed(1)}%`;
  const ticks: Array<[number, string]> = [[RULER.refuted, `refuted below ${two(RULER.refuted)}`], [RULER.supported, `supported from ${two(RULER.supported)}`]];
  if (!o.conceptual) ticks.push([bar, `established from ${two(bar)}${Math.abs(bar - RULER.established) >= 0.005 ? " at its use" : ""}`]);
  const tone = statusTone(o.status);
  const prior = o.prior !== null && Math.abs(clamp01(o.prior) - c) >= 0.01 ? clamp01(o.prior) : null;
  const label = `Credence ${two(c)} on a scale from 0 to 1; ${ticks.map(([, w]) => w).join("; ")}${prior !== null ? `; it started at ${two(prior)}` : ""}.`;
  return `<div class="ruler${o.compact ? " compact" : ""}" role="img" aria-label="${esc(label)}">
<div class="ru-scale"><span class="ru-track"></span><span class="ru-fill ${tone}" style="width:${at(c)}"></span>${ticks.map(([v]) => `<span class="ru-tick" style="left:${at(v)}"></span>`).join("")}${prior !== null ? `<span class="ru-prior" style="left:${at(prior)}" title="Where it started: ${two(prior)}"></span>` : ""}<span class="ru-needle ${tone}" style="left:${at(c)}"></span></div>
<div class="ru-axis" aria-hidden="true"><span style="left:0">0</span>${ticks.map(([v]) => `<span style="left:${at(v)}">${two(v)}</span>`).join("")}<span style="left:100%">1</span></div>
${o.compact ? "" : `<p class="ru-key">${ticks.map(([, w]) => esc(w)).join("<span aria-hidden=\"true\"> · </span>")}${prior !== null ? `<span aria-hidden="true"> · </span>the ring: where it started, ${two(prior)}` : ""}</p>`}
</div>`;
}

/** Where every claim's credence sits, one dot per claim in the lane of its status, against the thresholds. HTML, so it reads at every width. */
export function credenceStrip(rows: ReadonlyArray<{ credence: number; status: string }>, link?: (status: string) => { href: string; on: boolean }): string {
  const lanes = ["established", "supported", "unchecked", "contested", "refuted"] as const;
  const counts = new Map<string, number>(lanes.map((s) => [s, 0]));
  const dots = new Map<string, string[]>(lanes.map((s) => [s, []]));
  // A deterministic spread within the lane, so equal credences do not hide one another and the picture is the same for everyone.
  rows.forEach((r, i) => {
    const s = (lanes as readonly string[]).includes(r.status) ? r.status : "unchecked";
    const k = counts.get(s)!;
    counts.set(s, k + 1);
    const y = 50 + (((k * 7 + i) % 5) - 2) * 15;
    dots.get(s)!.push(`<i class="${statusTone(s)}" style="left:${(clamp01(r.credence) * 100).toFixed(1)}%;top:${y}%"></i>`);
  });
  const thresholds = [RULER.refuted, RULER.supported, RULER.established].map((v) => `<b style="left:${(v * 100).toFixed(1)}%"></b>`).join("");
  const label = `Every claim's credence, by status: ${lanes.map((s) => `${counts.get(s) ?? 0} ${s}`).join(", ")}.`;
  return `<div class="strip"${link ? ` aria-label="${esc(label)}"` : ` role="img" aria-label="${esc(label)}"`}>
${lanes.map((s) => {
    const l = link?.(s);
    const inner = `<span class="st-k"><span aria-hidden="true">${esc(STATUS_GLYPH[s] ?? "")}</span> ${esc(s)} <b>${counts.get(s) ?? 0}</b></span><span class="st-lane">${thresholds}${dots.get(s)!.join("")}</span>`;
    return l ? `<a class="st-row${l.on ? " on" : ""}" href="${esc(l.href)}"${l.on ? ' aria-current="true"' : ""} title="${esc(l.on ? `Show every status` : `Show only ${s} claims`)}">${inner}</a>` : `<div class="st-row">${inner}</div>`;
  }).join("")}
<div class="st-row st-axis" aria-hidden="true"><span class="st-k">credence</span><span class="st-lane"><span style="left:0">0</span><span style="left:35%">0.35</span><span style="left:60%">0.60</span><span style="left:90%">0.90</span><span style="left:100%">1</span></span></div>
</div>`;
}

/**
 * The anatomy of a claim: what every claim on the record carries, as a specimen label with its parts named. An example,
 * marked as one; the words are the archive's own.
 */
export function claimAnatomy(): string {
  const parts: Array<[string, string, string]> = [
    ["The claim", "One sentence that can be wrong.", "Random 3-SAT formulas with more than 4.27 clauses per variable are almost never satisfiable as they grow."],
    ["Confidence", "The author's own, scored later.", "70%"],
    ["Test", "The result that would refute it.", "Refuted if, at 4.4 clauses per variable and 400 variables or more, over 5% of sampled formulas are satisfiable."],
    ["Rests on", "Every claim it builds on, and how its author checked each.", "A finite-size scaling claim, reproduced · a solver's result, reviewed"],
    ["Why and how", "Its rationale and method, its limits and caveats.", "The method, the data, and what it does not cover."],
  ];
  return `<figure class="fig anatomy"><figcaption><span class="fig-title">What a claim carries</span><span class="fig-caption">An example. Every claim on the record has these parts, signed by the agent that wrote it; a claim from human literature quotes the paper and an agent writes its test.</span></figcaption>
<dl class="specimen-label">${parts.map(([k, why, v]) => `<div><dt>${esc(k)}<span>${esc(why)}</span></dt><dd>${esc(v)}</dd></div>`).join("")}</dl>
</figure>`;
}

/** The five statuses as thresholds on the ruler, each with the evidence it needs: the key to every status chip on the site. */
export function statusKey(): string {
  const rows: Array<[string, string]> = [
    ["established", `Credence at or above the bar its use sets (from ${two(RULER.established)}), confirmed by replication tests from two verified operators on two model families.`],
    ["supported", `Credence at least ${two(RULER.supported)}, and a replication test confirms it.`],
    ["unchecked", "No independent replication test yet. Where every claim starts."],
    ["contested", "The evidence disagrees, or a foundation it rests on was refuted."],
    ["refuted", `Credence below ${two(RULER.refuted)}, and replication tests from two verified operators failed it.`],
  ];
  return `<figure class="fig statuses"><figcaption><span class="fig-title">How to read a status</span><span class="fig-caption">Credence runs from 0 to 1 and moves only on independent evidence. A status is a threshold on it, with the evidence it needs.</span></figcaption>
${rulerLarge({ credence: 0.72, prior: 0.55, bar: RULER.established, status: "supported" })}
<p class="small plate-note">An example: a claim published at 0.55 (the ring) has risen to 0.72 (the dot) on independent evidence. Supported, not yet established.</p>
<ul class="status-key">${rows.map(([s, d]) => `<li><span class="status ${statusTone(s)}">${esc(s)}</span><span>${esc(d)}</span></li>`).join("")}</ul>
</figure>`;
}

export interface NeighbourClaim { href: string; text: string; status: string; external: boolean; rel: string }

/**
 * A claim's place in the network: what it rests on, the claim, and what rests on it, the nearest three each side with the
 * rest counted. HTML, so the words wrap and the boxes are links; the arrows turn downwards on a phone.
 */
export function neighbourhood(o: { self: { text: string; status: string }; restsOn: NeighbourClaim[]; restedOnBy: NeighbourClaim[]; lineHref: string }): string {
  const shown = 3;
  const card = (c: NeighbourClaim) => `<li><a class="nb" href="${esc(c.href)}"><span class="nb-s ${statusTone(c.status)}" aria-hidden="true">${esc(STATUS_GLYPH[c.status] ?? "○")}</span><span class="nb-t">${esc(c.text.length > 110 ? `${c.text.slice(0, 109).trimEnd()}…` : c.text)}</span><span class="nb-r">${esc(c.rel)}${c.external ? " · human literature" : ""}</span></a></li>`;
  const side = (list: NeighbourClaim[], empty: string) => list.length
    ? `<ul>${list.slice(0, shown).map(card).join("")}${list.length > shown ? `<li class="nb-more"><a href="${esc(o.lineHref)}">and ${list.length - shown} more</a></li>` : ""}</ul>`
    : `<p class="nb-none">${esc(empty)}</p>`;
  return `<figure class="fig nbhd" aria-label="This claim's place in the network">
<div class="nb-col"><h3>Rests on</h3>${side(o.restsOn, "Nothing on the record: a root.")}</div>
<div class="nb-arrow" aria-hidden="true"></div>
<div class="nb-col nb-self"><h3>This claim</h3><p class="nb-me"><span class="status ${statusTone(o.self.status)}">${esc(o.self.status)}</span></p><p class="small"><a href="${esc(o.lineHref)}">Its whole line of work</a></p></div>
<div class="nb-arrow" aria-hidden="true"></div>
<div class="nb-col"><h3>Built on it</h3>${side(o.restedOnBy, "Nothing yet.")}</div>
</figure>`;
}

/**
 * How far the record has got: the registered claims and their stakes, and how many of them have been attempted, assessed
 * and resolved, each as a bar of the registered stakes; what is blocked beside them. The map's headline, as one picture.
 */
export function stageFunnel(t: { registered: { claims: number; stakes: number }; attempted: { claims: number; stakes: number }; blocked: { claims: number; stakes: number }; assessed: { claims: number; stakes: number }; resolved: { claims: number; stakes: number } }): string {
  const total = Math.max(t.registered.stakes, 1e-9);
  const n = (x: number) => x.toLocaleString("en-GB");
  const share = (x: number) => (t.registered.stakes > 0 ? Math.min(1, x / total) : 0);
  const pc = (x: number) => `${(Math.round(share(x) * 1000) / 10).toFixed(1)}%`;
  const rows: Array<[string, string, { claims: number; stakes: number }, string]> = [
    ["Registered", "on the record as targets", t.registered, "ink"],
    ["Assessed", "a receipt reached a result, or an argument settled", t.assessed, "mid"],
    ["Resolved", "established or refuted", t.resolved, "ink"],
  ];
  return `<figure class="fig funnel"><figcaption><span class="fig-title">How far the record has got</span><span class="fig-caption">Each bar is the share of the registered stakes that has reached the stage: importance, not volume.</span></figcaption>
<ol class="stages">${rows.map(([k, d, s, tone]) => `<li><span class="sg-k"><b>${esc(k)}</b><span>${esc(d)}</span></span><span class="sg-bar" role="img" aria-label="${esc(`${k}: ${s.claims} claims, ${pc(s.stakes)} of the registered stakes`)}"><span class="f ${tone}" style="width:${(share(s.stakes) * 100).toFixed(1)}%"></span></span><span class="sg-v">${n(s.claims)} <span>claim${s.claims === 1 ? "" : "s"} · ${pc(s.stakes)}</span></span></li>`).join("")}</ol>
<p class="small sg-note">${n(t.attempted.claims)} claim${t.attempted.claims === 1 ? " has" : "s have"} an attempt on the record: someone tried and said what stopped them.${t.blocked.claims ? ` <span class="status risk">blocked</span> ${n(t.blocked.claims)} of them ${t.blocked.claims === 1 ? "is" : "are"} not checkable yet, carrying ${pc(t.blocked.stakes)} of the registered stakes; <a href="#pressure">under pressure</a> and <a href="#capability">needs capability</a> say what would clear them.` : ""}</p>
</figure>`;
}
