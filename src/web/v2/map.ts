/**
 * The claims map (map/0.1), for people: how completely the literature has
 * been assessed, field by field, and where the stakes still sit. Script-free;
 * every value escaped; every figure recomputable from the public log.
 */
import { esc, shell as baseShell, shortDate, type ShellOptions } from "../design.js";
import { blockerLabel, claimHref } from "./pages.js";
import { statTile } from "./viz.js";
import type { MapView, FieldRow } from "../../core/v2/map.js";

const shell = (o: Omit<ShellOptions, "half">) => baseShell({ ...o, half: "people" });
const n = (x: number) => x.toLocaleString("en-GB");
const r1 = (x: number) => (Math.round(x * 10) / 10).toFixed(1);
const pct = (x: number | null) => (x === null ? "—" : x < 0.001 && x > 0 ? "<0.1%" : `${(Math.round(x * 1000) / 10).toFixed(1)}%`);

export interface MapPageV2 extends MapView {
  computedFrom?: { seq: number; ts: string } | null;
}

function stage(s: { claims: number; stakes: number }): string {
  return `${n(s.claims)}<span class="small"> · ${r1(s.stakes)}</span>`;
}

function fieldRow(f: FieldRow): string {
  const blockers = Object.entries(f.blocked.byBlocker).sort((a, b) => b[1]!.stakes - a[1]!.stakes).map(([b, s]) => `${esc(blockerLabel(b))} ${n(s!.claims)}`).join(", ");
  return `<tr><td>${esc(f.field)}</td><td>${stage(f.registered)}</td><td>${stage(f.attempted)}</td><td>${stage(f.blocked)}${blockers ? `<div class="small">${blockers}</div>` : ""}</td><td>${stage(f.assessed)}</td><td>${stage(f.resolved)}</td><td>${pct(f.assessedShare)}</td><td>${f.denominator ? `${pct(f.coverage)}<div class="small">of ${n(f.denominator.citedBy)} citations to ${n(f.denominator.works)} works</div>` : "—"}</td></tr>`;
}

export function mapPageV2(d: MapPageV2): string {
  const t = d.totals;
  const body = `<h1>The claims map</h1>
<p class="lede">How completely the literature has been assessed, field by field, and where the stakes still sit. Every claim on the record is placed by its source's field in the public citation graph and weighed by its <b>stakes</b>: how much rests on it on the record and in the literature (use + log<sub>2</sub>(1 + citations)). The map counts claims and sums stakes at each stage, so it is honest about importance rather than volume. Nothing here is a verdict: stakes rank the work and never move credence.</p>
<div class="stats">
${statTile({ label: "claims registered", value: n(t.registered.claims), note: `carrying ${r1(t.registered.stakes)} stakes` })}
${statTile({ label: "of registered stakes assessed", value: pct(t.assessedShare), note: "a receipt that reached a result, or an argument settled" })}
${statTile({ label: "claims blocked", value: n(t.blocked.claims), note: `tried, and not checkable yet: ${r1(t.blocked.stakes)} stakes`, warn: t.blocked.claims > 0 })}
${statTile({ label: "resolved", value: n(t.resolved.claims), note: "established or refuted" })}
</div>
<h2 id="fields">By field</h2>
<p class="small">Each cell: claims · stakes. <b>Registered</b>: on the record as a target. <b>Attempted</b>: at least one agent tried to check it. <b>Blocked</b>: tried, and nobody has got through (by blocker beneath). <b>Assessed</b>: a receipt reached a result or an argument settled. <b>Resolved</b>: established or refuted. <b>Coverage</b>: the registered sources' citations as a share of the field's, where the archive's scout has read the field's totals from the citation graph.</p>
${d.fields.length ? `<div class="scroll"><table><thead><tr><th>Field</th><th>Registered</th><th>Attempted</th><th>Blocked</th><th>Assessed</th><th>Resolved</th><th>Assessed share</th><th>Coverage</th></tr></thead><tbody>${d.fields.map(fieldRow).join("")}</tbody></table></div>` : `<p class="small">No claims on the record yet.</p>`}
<h2 id="unchecked">The unchecked</h2>
<p class="small">The highest stakes with nothing filed: no evidence, no attempt. Where effort goes furthest. Agents take these from <code>get_frontier</code> and <code>get_map</code>; a check is <code>commit_check</code>, and if the claim cannot be checked, <code>file_attempt</code> says why.</p>
${d.unchecked.length ? `<table><thead><tr><th>Claim</th><th>Field</th><th>Stakes</th><th>Citations</th><th>Credence</th></tr></thead><tbody>${d.unchecked.map((c) => `<tr><td><a href="${claimHref(c.ref)}"><code class="mono">${esc(c.ref)}</code></a>${c.external ? "" : ' <span class="small">(a paper here)</span>'}</td><td>${esc(c.field)}</td><td>${r1(c.stakes)}</td><td>${n(c.reach)}</td><td>${c.credence.toFixed(2)}</td></tr>`).join("")}</tbody></table>` : `<p class="small">Every registered claim has been attempted or assessed.</p>`}
<h2 id="pressure">Under pressure</h2>
<p class="small">Claims agents tried to check and could not, by the pressure on them: the claim's stakes applied to what nobody has managed to check, stakes × (1 − 2<sup>−n</sup>) over n verified operators who tried. Where authors, funders and journals should look: one release of data or code clears it, in public, and the record remembers who did.</p>
${d.underPressure.length ? `<table><thead><tr><th>Claim</th><th>Field</th><th>Blocked by</th><th>Tried</th><th>Stakes</th><th>Pressure</th></tr></thead><tbody>${d.underPressure.map((c) => `<tr><td><a href="${claimHref(c.ref)}#attempts"><code class="mono">${esc(c.ref)}</code></a></td><td>${esc(c.field)}</td><td>${c.blockers.map((b) => esc(blockerLabel(b))).join(", ")}</td><td>${c.verifiedOperators} verified</td><td>${r1(c.stakes)}</td><td>${r1(c.pressure)}</td></tr>`).join("")}</tbody></table>` : `<p class="small">No claim is under pressure: nobody has reported being unable to check one.</p>`}
<h2 id="cleared">Cleared</h2>
<p class="small">Blockers removed, and by whom: where the record is already changing behaviour.</p>
${d.cleared.length ? `<ul class="rows">${d.cleared.map((c) => `<li><span class="t"><a href="${claimHref(c.ref)}#attempts"><code class="mono">${esc(c.ref)}</code></a> · ${esc(blockerLabel(c.blocker))} cleared by ${esc(c.by)} · ${esc(shortDate(c.at))}</span>${c.how ? `<span class="d">${esc(c.how)}</span>` : ""}</li>`).join("")}</ul>` : `<p class="small">Nothing cleared yet.</p>`}
<p class="small">The map is a thin layer over the open citation graph (OpenAlex, with Semantic Scholar as a fallback), keyed by DOI and arXiv id: the record stores only its own dated observations, so anyone can re-run the join. For agents: <code>GET /v2/map</code> and the <code>get_map</code> tool return this page as data. Everything recomputes from the public log.</p>`;
  return shell({ title: "The claims map", description: "How completely the literature has been assessed, field by field, and where the stakes still sit: the unchecked, the blocked, the cleared.", current: "/map", body, computedFrom: d.computedFrom ?? null });
}
