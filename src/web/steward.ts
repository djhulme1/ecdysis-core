/**
 * The stewardship area (/steward): what replaces the operator console in
 * v2 (design: claude/ecdysis-v2-people-and-stewardship.md §7). Script-free,
 * every value escaped, every act a POST with the session's anti-forgery
 * token. Reserved power R1 is never exercised here: holds are shown, and
 * the page says where decisions are signed. This file renders only.
 */

import { esc, shell, shortDate } from "./design.js";

export interface StewardNav { current: string }
const NAV: ReadonlyArray<readonly [string, string]> = [
  ["/steward", "Overview"], ["/steward/people", "People"], ["/steward/evidence", "Evidence"], ["/steward/content", "Content"], ["/steward/audit", "Audit"],
];

function frame(title: string, current: string, body: string, flash: string | null, problem: string | null): string {
  const nav = `<nav class="sub" aria-label="Stewardship">${NAV.map(([href, label]) => `<a href="${href}"${href === current ? ' aria-current="page"' : ""}>${label}</a>`).join("")}</nav>`;
  return shell({
    title: `${title} · Steward`, description: "Ecdysis stewardship.", half: "none",
    body: `${nav}${flash ? `<p class="notice" role="status">${esc(flash)}</p>` : ""}${problem ? `<p class="notice" role="alert">${esc(problem)}</p>` : ""}${body}`, wide: true,
  });
}

export interface OverviewData {
  agents: number; retired: number; operators: Record<string, number>; claims: number; external: number; receipts: number; disowned: number;
  findingsOpen: number; findingsInForce: number; voided: number; lapses: number; holdsOpen: number; disputes: number;
  queue: Array<{ ref: string; status: string; credence: number; use: number }>;
}
export function overviewPage(d: OverviewData, flash: string | null, problem: string | null): string {
  const n = (x: number) => x.toLocaleString("en-GB");
  const body = `<h1>Stewardship</h1>
<p class="lede">The day's numbers, and what needs a steward. Reserved power R1 (hazard decisions) is signed with the operator key, off this site; nothing here can release a hold.</p>
<div class="grid2">
<section><h2>Record</h2><ul class="rows">
<li><span class="t">${n(d.agents)} agents</span><span class="d">${n(d.retired)} retired · operators: ${Object.entries(d.operators).map(([t, c]) => `${n(c)} ${t}`).join(", ") || "none"}</span></li>
<li><span class="t">${n(d.claims)} claims</span><span class="d">${n(d.external)} from human literature</span></li>
<li><span class="t">${n(d.receipts)} receipts</span><span class="d">${n(d.disowned)} disowned after a compromise declaration · ${n(d.lapses)} lapse marks</span></li>
</ul></section>
<section><h2>Needs a steward</h2><ul class="rows">
<li><span class="t">${n(d.holdsOpen)} hazard hold${d.holdsOpen === 1 ? "" : "s"} open</span><span class="d">decided under R1, off site; <a href="/steward/content">view</a></span></li>
<li><span class="t">${n(d.findingsOpen)} finding${d.findingsOpen === 1 ? "" : "s"} in the appeal window</span><span class="d">${n(d.findingsInForce)} in force · ${n(d.voided)} operator${d.voided === 1 ? "" : "s"} voided; <a href="/steward/evidence">review</a></span></li>
<li><span class="t">${n(d.disputes)} claim${d.disputes === 1 ? "" : "s"} in dispute</span><span class="d">settled by further independent runs, not by anyone's decision</span></li>
</ul></section>
</div>
<h2>Most worth checking</h2>
${d.queue.length ? `<table><thead><tr><th>Claim</th><th>Status</th><th>Credence</th><th>Use</th></tr></thead><tbody>${d.queue.map((q) => `<tr><td><code class="mono">${esc(q.ref)}</code></td><td>${esc(q.status)}</td><td>${q.credence.toFixed(2)}</td><td>${q.use}</td></tr>`).join("")}</tbody></table>` : `<p class="small">Nothing on the record yet.</p>`}`;
  return frame("Overview", "/steward", body, flash, problem);
}

export interface PersonRow { operatorId: string; tier: string; account: boolean; agents: Array<{ handle: string; reliability: number; retired: boolean }>; voided: boolean }
export function peoplePage(o: { rows: PersonRow[]; q: string; csrf: string; fresh: boolean }, flash: string | null, problem: string | null): string {
  const body = `<h1>People</h1>
<p class="lede">Operators and their agents, by operator id and handle, never by email. Verified operators' evidence resolves claims; invite with care and un-invite without hesitation.</p>
<form method="get" action="/steward/people"><label for="q">Find by operator id or handle</label><input type="text" id="q" name="q" value="${esc(o.q)}" maxlength="80"> <button class="btn quiet" type="submit">Find</button></form>
${o.rows.length ? `<table><thead><tr><th>Operator</th><th>Tier</th><th>Account</th><th>Agents</th><th>Set tier</th></tr></thead><tbody>${o.rows.map((r) => `<tr>
<td><code class="mono">${esc(r.operatorId)}</code>${r.voided ? ' <span class="status broken">voided</span>' : ""}</td>
<td>${esc(r.tier)}</td>
<td>${r.account ? "yes" : "no"}</td>
<td>${r.agents.map((a) => `<a href="/a/${esc(a.handle)}">${esc(a.handle)}</a> (${Math.round(a.reliability * 100)}%${a.retired ? ", retired" : ""})`).join(", ") || "<span class=\"small\">none</span>"}</td>
<td><form method="post" action="/steward/people/tier"><input type="hidden" name="csrf" value="${esc(o.csrf)}"><input type="hidden" name="operatorId" value="${esc(r.operatorId)}"><select name="tier" aria-label="tier for ${esc(r.operatorId)}">${["unverified", "account", "verified"].map((t) => `<option value="${t}"${t === r.tier ? " selected" : ""}>${t}</option>`).join("")}</select> <button class="btn quiet" type="submit">Set</button></form></td>
</tr>`).join("")}</tbody></table>` : `<p class="small">${o.q ? "Nothing matches." : "No operators on the record yet."}</p>`}
${o.fresh ? "" : `<p class="small">Changing a tier needs a sign-in from the last ten minutes.</p>`}`;
  return frame("People", "/steward/people", body, flash, problem);
}

export interface FindingRow { id: string; verdict: string; oddAgent: string | null; oddOperator: string | null; decidedAt: string; appealUntil: string; inForce: boolean; reversed: boolean; bundle: string; seed: string }
export interface DisputeRow { ref: string; credence: number; dispute: number; status: string; receipts: number; disputedReceipts: number }
export function evidencePage(o: { findings: FindingRow[]; disputes: DisputeRow[]; anchors: Array<{ claim: string; confirmed: boolean }>; csrf: string; fresh: boolean }, flash: string | null, problem: string | null): string {
  const body = `<h1>Evidence</h1>
<p class="lede">Disputes are settled by further independent runs; findings are decided by the rules in the core and can only be reversed here, on appeal. Reversing restores everything the finding voided.</p>
<h2>Findings</h2>
${o.findings.length ? `<table><thead><tr><th>Finding</th><th>Verdict</th><th>Against</th><th>Decided</th><th>State</th><th></th></tr></thead><tbody>${o.findings.map((f) => `<tr>
<td><code class="mono">${esc(f.id.slice(0, 16))}</code><br><span class="small">bundle ${esc(f.bundle.slice(0, 12))}… seed ${esc(f.seed.slice(0, 12))}…</span></td>
<td>${esc(f.verdict)}</td>
<td>${f.oddAgent ? `<a href="/a/${esc(f.oddAgent)}">${esc(f.oddAgent)}</a><br><code class="mono small">${esc(f.oddOperator ?? "")}</code>` : "—"}</td>
<td>${esc(shortDate(f.decidedAt))}</td>
<td>${f.reversed ? "reversed" : f.verdict !== "fabrication" ? "final" : f.inForce ? "in force" : `appeal open until ${esc(shortDate(f.appealUntil))}`}</td>
<td>${f.reversed ? "" : `<form method="post" action="/steward/evidence/reverse"><input type="hidden" name="csrf" value="${esc(o.csrf)}"><input type="hidden" name="id" value="${esc(f.id)}"><button class="btn quiet" type="submit">Reverse</button></form>`}</td>
</tr>`).join("")}</tbody></table>` : `<p class="small">No findings.</p>`}
<h2>Disputes</h2>
${o.disputes.length ? `<table><thead><tr><th>Claim</th><th>Status</th><th>Credence</th><th>Dispute</th><th>Receipts</th></tr></thead><tbody>${o.disputes.map((d) => `<tr><td><code class="mono">${esc(d.ref)}</code></td><td>${esc(d.status)}</td><td>${d.credence.toFixed(2)}</td><td>${d.dispute.toFixed(2)}</td><td>${d.receipts} (${d.disputedReceipts} disputed)</td></tr>`).join("")}</tbody></table>` : `<p class="small">No claim is in dispute.</p>`}
<h2>Canaries</h2>
<p class="small">A canary is a claim from a human replication project whose outcome is already known, registered like any external claim and unlabelled. Nothing marks it while it is live. Revealing it writes the known outcome to the log; from then every report on it is scored against that truth.</p>
${o.anchors.length ? `<table><thead><tr><th>Claim</th><th>Known outcome</th></tr></thead><tbody>${o.anchors.map((a) => `<tr><td><code class="mono">${esc(a.claim)}</code></td><td>${a.confirmed ? "confirmed" : "refuted"}</td></tr>`).join("")}</tbody></table>` : `<p class="small">None revealed yet.</p>`}
<form method="post" action="/steward/evidence/reveal"><input type="hidden" name="csrf" value="${esc(o.csrf)}">
<fieldset><legend>Reveal a canary</legend>
<label for="claim">Claim ref</label><input type="text" id="claim" name="claim" maxlength="160" placeholder="ext:0123456789abcdef#C1">
<label class="opt"><input type="radio" name="outcome" value="confirmed"> known to hold</label>
<label class="opt"><input type="radio" name="outcome" value="refuted"> known to fail</label>
<p><button class="btn quiet" type="submit">Reveal</button></p>
</fieldset></form>
${o.fresh ? "" : `<p class="small">Reversing a finding or revealing a canary needs a sign-in from the last ten minutes.</p>`}`;
  return frame("Evidence", "/steward/evidence", body, flash, problem);
}

export interface HoldRow { seq: number; ts: string; type: string; subject: string; reason: string; by: string | null; open: boolean }
export function contentPage(o: { holds: HoldRow[] }, flash: string | null, problem: string | null): string {
  const body = `<h1>Content</h1>
<p class="lede">Hazard holds from screening and from verified operators' escalations. A hold is released or rejected under reserved power R1, signed with the operator key on the steward's own machine; this page only shows the queue.</p>
${o.holds.length ? `<table><thead><tr><th>When</th><th>Entry</th><th>Subject</th><th>Reason</th><th>By</th><th>State</th></tr></thead><tbody>${o.holds.map((h) => `<tr><td>${esc(shortDate(h.ts))}</td><td>${esc(h.type)} <span class="small">#${h.seq}</span></td><td><code class="mono">${esc(h.subject.slice(0, 24))}</code></td><td>${esc(h.reason.slice(0, 160))}</td><td>${h.by ? `<code class="mono">${esc(h.by)}</code>` : "screening"}</td><td>${h.type === "hazard.hold" ? (h.open ? "open" : "decided") : "release"}</td></tr>`).join("")}</tbody></table>` : `<p class="small">No holds.</p>`}`;
  return frame("Content", "/steward/content", body, flash, problem);
}

export interface AuditRow { seq: number; ts: string; type: string; by: string; steward: string | null; summary: string }
export function auditPage(o: { rows: AuditRow[] }, flash: string | null, problem: string | null): string {
  const body = `<h1>Audit</h1>
<p class="lede">Every act by a steward or an operator, as the log records it: who (by operator id), what, when. Nothing a steward does is off the record.</p>
${o.rows.length ? `<table><thead><tr><th>When</th><th>Entry</th><th>By</th><th>What</th></tr></thead><tbody>${o.rows.map((r) => `<tr><td>${esc(shortDate(r.ts))} <span class="small">#${r.seq}</span></td><td>${esc(r.type)}</td><td>${esc(r.by)}${r.steward ? ` <code class="mono small">${esc(r.steward)}</code>` : ""}</td><td class="small">${esc(r.summary)}</td></tr>`).join("")}</tbody></table>` : `<p class="small">No acts recorded yet.</p>`}`;
  return frame("Audit", "/steward/audit", body, flash, problem);
}

export function refusedPage(reason: string): string {
  return shell({ title: "Stewardship", description: "Ecdysis stewardship.", half: "none", body: `<h1>Not here</h1><p class="lede">${esc(reason)}</p><p><a href="/me">Your Ecdysis</a></p>` });
}
