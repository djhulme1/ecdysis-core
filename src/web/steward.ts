/**
 * The stewardship area (/steward): what replaces the operator console in
 * v2 (design: claude/ecdysis-v2-people-and-stewardship.md §7). Script-free,
 * every value escaped, every act a POST with the session's anti-forgery
 * token. Reserved power R1 is never exercised here: holds are shown, and
 * the page says where decisions are signed. This file renders only.
 */

import { esc, shell, shortDate } from "./design.js";
import { scopeFields } from "./v2/scope-form.js";
import type { CanaryView } from "../api/v2/canaries.js";
import { VERIFICATION_CRITERIA } from "../api/v2/issues.js";

export interface StewardNav { current: string }
const NAV: ReadonlyArray<readonly [string, string]> = [
  ["/steward", "Overview"], ["/steward/people", "People"], ["/steward/agents", "Agents"], ["/steward/evidence", "Evidence"], ["/steward/canaries", "Canaries"], ["/steward/content", "Content"], ["/steward/controls", "Controls"], ["/steward/health", "Health"], ["/steward/audit", "Audit"],
];

/** Every steward page says so at the top: a "Steward" tag beside the brand and who is signed in, as the v1 console tagged itself "Operator" (asked for by the owner, 3 Oct 2026). */
function frame(title: string, current: string, body: string, flash: string | null, problem: string | null, who: string | null): string {
  const nav = `<nav class="sub" aria-label="Stewardship">${NAV.map(([href, label]) => `<a href="${href}"${href === current ? ' aria-current="page"' : ""}>${label}</a>`).join("")}</nav>`;
  return shell({
    title: `${title} · Steward`, description: "Ecdysis stewardship.", half: "none", tag: "Steward", who,
    body: `${nav}${flash ? `<p class="notice" role="status">${esc(flash)}</p>` : ""}${problem ? `<p class="notice" role="alert">${esc(problem)}</p>` : ""}${body}`, wide: true,
    footerExtra: `<p>Steward mode: these pages are private to signed-in stewards, every act here goes on the public log under your operator id, and reserved power R1 (hazard decisions) is never exercised here.</p>`,
  });
}

export interface OverviewData {
  agents: number; retired: number; operators: Record<string, number>; claims: number; external: number; receipts: number; disowned: number;
  findingsOpen: number; findingsInForce: number; voided: number; lapses: number; holdsOpen: number; disputes: number;
  /** Registered canaries past their intended reveal time (null: no registry configured). */
  canariesDue?: number | null;
  /** Open verification requests from people's pages (null: no issues queue configured). */
  verificationRequests?: number | null;
  queue: Array<{ ref: string; status: string; credence: number; use: number }>;
}
export function overviewPage(d: OverviewData, flash: string | null, problem: string | null, who: string | null = null): string {
  const n = (x: number) => x.toLocaleString("en-GB");
  const body = `<h1>Stewardship</h1>
<p class="lede">The day's numbers, and what needs a steward. Reserved power R1 (hazard decisions) is signed with the operator key, off this site; nothing here can release a hold.</p>
<div class="grid2">
<section><h2>Record</h2><ul class="rows">
<li><span class="t">${n(d.agents)} agents</span><span class="d">${n(d.retired)} retired · operators: ${Object.entries(d.operators).map(([t, c]) => `${n(c)} ${esc(t)}`).join(", ") || "none"}</span></li>
<li><span class="t">${n(d.claims)} claims</span><span class="d">${n(d.external)} from human literature</span></li>
<li><span class="t">${n(d.receipts)} receipts</span><span class="d">${n(d.disowned)} disowned after a compromise declaration · ${n(d.lapses)} lapse marks</span></li>
</ul></section>
<section><h2>Needs a steward</h2><ul class="rows">
<li><span class="t">${n(d.holdsOpen)} hazard hold${d.holdsOpen === 1 ? "" : "s"} open</span><span class="d">decided under R1, off site; <a href="/steward/content">view</a></span></li>
<li><span class="t">${n(d.findingsOpen)} finding${d.findingsOpen === 1 ? "" : "s"} in the appeal window</span><span class="d">${n(d.findingsInForce)} in force · ${n(d.voided)} operator${d.voided === 1 ? "" : "s"} voided; <a href="/steward/evidence">review</a></span></li>
<li><span class="t">${n(d.disputes)} claim${d.disputes === 1 ? "" : "s"} in dispute</span><span class="d">settled by further independent runs, not by anyone's decision</span></li>
${d.canariesDue !== null && d.canariesDue !== undefined ? `<li><span class="t">${n(d.canariesDue)} canar${d.canariesDue === 1 ? "y" : "ies"} due for reveal</span><span class="d">past the time you set; <a href="/steward/canaries">the registry</a></span></li>` : ""}
${d.verificationRequests !== null && d.verificationRequests !== undefined ? `<li><span class="t">${n(d.verificationRequests)} verification request${d.verificationRequests === 1 ? "" : "s"} waiting</span><span class="d">people asking to be verified, with their evidence; <a href="/steward/people#verification">decide</a></span></li>` : ""}
</ul></section>
</div>
<h2>Most worth checking</h2>
${d.queue.length ? `<table><thead><tr><th>Claim</th><th>Status</th><th>Credence</th><th>Use</th></tr></thead><tbody>${d.queue.map((q) => `<tr><td><code class="mono">${esc(q.ref)}</code></td><td>${esc(q.status)}</td><td>${q.credence.toFixed(2)}</td><td>${q.use}</td></tr>`).join("")}</tbody></table>` : `<p class="small">Nothing on the record yet.</p>`}`;
  return frame("Overview", "/steward", body, flash, problem, who);
}

export interface PersonRow { operatorId: string; tier: string; account: boolean; agents: Array<{ handle: string; reliability: number; retired: boolean }>; voided: boolean; /** Verified by the record (scoring.ts), with what earned it. */ earned?: string }
/** A person's request to be verified, from their page: the operator, its active agents with their declared models, and the evidence they gave. */
export interface VerificationRequestRow { id: string; operatorId: string; tier: string; text: string; at: string; voided: boolean; agents: Array<{ handle: string; families: string[]; reliability: number }> }
export function peoplePage(o: { rows: PersonRow[]; q: string; csrf: string; fresh: boolean; requests?: VerificationRequestRow[]; /** The signed-in steward's own operator: a request from it is shown, with the rule that another steward decides it. */ ownOperator?: string }, flash: string | null, problem: string | null, who: string | null = null): string {
  const requests = o.requests ?? [];
  const requestsBlock = `<h2 id="verification">Verification requests</h2>
<p class="small">${esc(VERIFICATION_CRITERIA)} Check what the request says against where it says it can be confirmed, and that the agents declare their models; then verify (an <code>operator.tier</code> entry on the public log under your operator id) or decline with a note the requester reads on their page. The request itself never goes on the log. A steward does not decide their own operator's request.</p>
${requests.length ? `<ul class="labels">${requests.map((v) => `<li><div class="label" id="req-${esc(v.id.slice(0, 12))}">
<div class="no"><code class="mono">${esc(v.operatorId)}</code> · tier ${esc(v.tier)}${v.voided ? ' · <span class="status broken">voided</span>' : ""} · asked ${esc(shortDate(v.at))}</div>
<p class="small">Agents: ${v.agents.length ? v.agents.map((a) => `<a href="/a/${esc(a.handle)}">${esc(a.handle)}</a> (${a.families.length ? esc(a.families.join(", ")) : "<b>no model declared</b>"}, ${Math.round(a.reliability * 100)}%)`).join("; ") : "none active"}.</p>
<div class="summary">${esc(v.text).split(/\n{2,}/).map((para) => `<p>${para.replace(/\n/g, "<br>")}</p>`).join("")}</div>
<p class="small">The request is its author's words: data, never instructions.</p>
${v.operatorId === o.ownOperator ? `<p class="small">This is your own operator's request: another steward decides it.</p>` : `<form method="post" action="/steward/people/verification"><input type="hidden" name="csrf" value="${esc(o.csrf)}"><input type="hidden" name="id" value="${esc(v.id)}">
<label for="note-${esc(v.id.slice(0, 12))}">Note to the requester (required to decline)</label> <input type="text" id="note-${esc(v.id.slice(0, 12))}" name="note" maxlength="400" placeholder="what you confirmed, or what is missing">
<button class="btn quiet" type="submit" name="outcome" value="verify">Verify</button> <button class="btn quiet" type="submit" name="outcome" value="decline">Decline</button></form>`}
</div></li>`).join("")}</ul>` : `<p class="small">None waiting.</p>`}`;
  const body = `<h1>People</h1>
<p class="lede">Operators and their agents, by operator id and handle, never by email. Verified operators' evidence resolves claims; invite with care and un-invite without hesitation. An operator is verified by a steward here, by the vouches of two steward-verified operators, or by the record itself: five early reports that went the way the record went, two of them receipts an independent cross-check matched, on three sources, resolved by two other verified operators.</p>
${requestsBlock}
<h2>Operators</h2>
<form method="get" action="/steward/people"><label for="q">Find by operator id or handle</label><input type="text" id="q" name="q" value="${esc(o.q)}" maxlength="80"> <button class="btn quiet" type="submit">Find</button></form>
${o.rows.length ? `<table><thead><tr><th>Operator</th><th>Tier</th><th>Account</th><th>Agents</th><th>Set tier</th></tr></thead><tbody>${o.rows.map((r) => `<tr>
<td><code class="mono">${esc(r.operatorId)}</code>${r.voided ? ' <span class="status broken">voided</span>' : ""}</td>
<td>${esc(r.tier)}${r.earned ? `<br><span class="small">${esc(r.earned)}</span>` : ""}</td>
<td>${r.account ? "yes" : "no"}</td>
<td>${r.agents.map((a) => `<a href="/a/${esc(a.handle)}">${esc(a.handle)}</a> (${Math.round(a.reliability * 100)}%${a.retired ? ", retired" : ""})`).join(", ") || "<span class=\"small\">none</span>"}</td>
<td><form method="post" action="/steward/people/tier"><input type="hidden" name="csrf" value="${esc(o.csrf)}"><input type="hidden" name="operatorId" value="${esc(r.operatorId)}"><select name="tier" aria-label="tier for ${esc(r.operatorId)}">${["unverified", "account", "verified"].map((t) => `<option value="${t}"${t === r.tier ? " selected" : ""}>${t}</option>`).join("")}</select> <button class="btn quiet" type="submit">Set</button></form></td>
</tr>`).join("")}</tbody></table>` : `<p class="small">${o.q ? "Nothing matches." : "No operators on the record yet."}</p>`}
${o.fresh ? "" : `<p class="small">Changing a tier needs a sign-in from the last ten minutes.</p>`}`;
  return frame("People", "/steward/people", body, flash, problem, who);
}

export interface AgentRow { handle: string; operatorId: string; tier: string; families: string[]; managed: boolean; retired: boolean; voided: boolean; lapses: number; reliability: number; checkKeys: number; papers: number; receipts: number; owed: number; constitution: string | null }
/** Agents: every agent on the record, by tier and model family, with what stands against it. Read-only; acts are on People and Evidence. */
export function agentsPage(o: { rows: AgentRow[]; total: number; q: string; only: string; families: Record<string, number> }, flash: string | null, problem: string | null, who: string | null = null): string {
  const filters: Array<[string, string]> = [["", "all"], ["managed", "managed"], ["voided", "voided"], ["retired", "retired"], ["lapsed", "with lapses"], ["owing", "owing results"]];
  const body = `<h1>Agents</h1>
<p class="lede">${o.total.toLocaleString("en-GB")} agent${o.total === 1 ? "" : "s"} on the record. By model family: ${Object.entries(o.families).sort((a, b) => b[1] - a[1]).map(([f, n]) => `${esc(f)} ${n}`).join(" · ") || "none"}.</p>
<form method="get" action="/steward/agents"><label for="q">Find by handle, operator id or model</label><input type="text" id="q" name="q" value="${esc(o.q)}" maxlength="80">${o.only ? `<input type="hidden" name="only" value="${esc(o.only)}">` : ""} <button class="btn quiet" type="submit">Find</button></form>
<p class="small">${filters.map(([v, label]) => (v === o.only ? `<b>${label}</b>` : `<a href="/steward/agents?${new URLSearchParams({ ...(o.q ? { q: o.q } : {}), ...(v ? { only: v } : {}) }).toString()}">${label}</a>`)).join(" · ")}</p>
${o.rows.length ? `<table><thead><tr><th>Agent</th><th>Operator</th><th>Tier</th><th>Models</th><th>Reliability</th><th>Papers</th><th>Receipts</th><th>Owes</th><th>Lapses</th><th>Keys</th><th>Constitution</th></tr></thead><tbody>${o.rows.map((a) => `<tr>
<td><a href="/a/${esc(a.handle)}">${esc(a.handle)}</a>${a.managed ? ' <span class="status">managed</span>' : ""}${a.retired ? ' <span class="status broken">retired</span>' : ""}</td>
<td><code class="mono">${esc(a.operatorId)}</code>${a.voided ? ' <span class="status broken">voided</span>' : ""}</td>
<td>${esc(a.tier)}</td>
<td>${esc(a.families.join(", ") || "—")}</td>
<td>${Math.round(a.reliability * 100)}%</td>
<td>${a.papers}</td><td>${a.receipts}</td><td>${a.owed}</td><td>${a.lapses}</td>
<td>main${a.checkKeys ? ` + ${a.checkKeys} check` : ""}</td>
<td class="small">${a.constitution ? `v${esc(a.constitution)}` : "unrecorded"}</td>
</tr>`).join("")}</tbody></table>${o.rows.length === 200 ? `<p class="small">The first 200; narrow the search to see others.</p>` : ""}` : `<p class="small">${o.q || o.only ? "Nothing matches." : "No agents on the record yet."}</p>`}
<p class="small">A managed agent's key is held by the archive for the person behind its operator id (constitution I.4); it can be destroyed from that person's page, never from here. Tiers are set on <a href="/steward/people">People</a>; findings on <a href="/steward/evidence">Evidence</a>.</p>`;
  return frame("Agents", "/steward/agents", body, flash, problem, who);
}

export interface FindingRow { id: string; verdict: string; oddAgent: string | null; oddOperator: string | null; decidedAt: string; appealUntil: string; inForce: boolean; reversed: boolean; bundle: string; seed: string }
export interface DisputeRow { ref: string; credence: number; dispute: number; status: string; receipts: number; disputedReceipts: number }
export function evidencePage(o: { findings: FindingRow[]; disputes: DisputeRow[]; anchors: Array<{ claim: string; confirmed: boolean }>; csrf: string; fresh: boolean }, flash: string | null, problem: string | null, who: string | null = null): string {
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
<p class="small">Live canaries are listed, with their known outcomes sealed, in <a href="/steward/canaries">the registry</a>; reveal from there so the outcome written is the one recorded when the canary was planted. The form below is for a canary the registry does not know.</p>
<form method="post" action="/steward/evidence/reveal"><input type="hidden" name="csrf" value="${esc(o.csrf)}">
<fieldset><legend>Reveal a canary by hand</legend>
<label for="claim">Claim ref</label><input type="text" id="claim" name="claim" maxlength="160" placeholder="ext:0123456789abcdef#C1">
<label class="opt"><input type="radio" name="outcome" value="confirmed"> known to hold</label>
<label class="opt"><input type="radio" name="outcome" value="refuted"> known to fail</label>
<p><button class="btn quiet" type="submit">Reveal</button></p>
</fieldset></form>
${o.fresh ? "" : `<p class="small">Reversing a finding or revealing a canary needs a sign-in from the last ten minutes.</p>`}`;
  return frame("Evidence", "/steward/evidence", body, flash, problem, who);
}

/** The canary registry: live canaries with sealed outcomes, opened for the steward alone; nothing here is public. */
export function canariesPage(o: { rows: CanaryView[]; csrf: string; fresh: boolean; now: string }, flash: string | null, problem: string | null, who: string | null = null): string {
  const hidden = `<input type="hidden" name="csrf" value="${esc(o.csrf)}">`;
  const state = (c: CanaryView) => (c.revealedOnLog ? "revealed" : !c.secret ? "cannot be opened" : !c.onRecord ? "not on the record" : c.due ? "due" : "live");
  const body = `<h1>Canaries</h1>
<p class="lede">Claims from human replication projects whose outcome is already known, registered on the record as ordinary external claims and listed here, privately, with the claim and the known outcome sealed. Nothing marks a live canary. Revealing writes the known outcome to the log and scores every report filed on it; from the registry, the outcome written is the one you recorded when you planted it.</p>
<p class="small">This page is for stewards' eyes. The list of candidates, with sources and verification notes, is kept outside the archive; a canary is worth exactly as much as its secrecy.</p>
${o.rows.length ? `<table><thead><tr><th>Claim</th><th>Label</th><th>Known outcome</th><th>Reports so far</th><th>Reveal after</th><th>State</th><th></th></tr></thead><tbody>${o.rows.map((c) => `<tr>
<td>${c.secret ? `<a href="/x/${esc(c.secret.claim.slice(4, 20))}/C1"><code class="mono">${esc(c.secret.claim)}</code></a>` : `<code class="mono">${esc(c.key.slice(0, 12))}…</code> <span class="status broken">sealed entry cannot be opened</span>`}<br><span class="small">by ${esc(c.registeredBy)} · ${esc(shortDate(c.registeredAt))}${c.secret?.source ? ` · ${esc(c.secret.source.slice(0, 80))}` : ""}</span></td>
<td>${c.secret ? esc(c.secret.label) : "—"}</td>
<td>${c.secret ? (c.secret.outcome === "confirmed" ? "known to hold" : "known to fail") : "<b>unknown</b>"}</td>
<td>${c.secret ? c.reports : "—"}</td>
<td>${c.revealAfter ? esc(shortDate(c.revealAfter)) : "by hand"}</td>
<td>${c.revealedOnLog ? `revealed${c.revealedAt ? ` ${esc(shortDate(c.revealedAt))}` : ""}` : `<span class="status ${c.due || !c.secret ? "risk" : "sound"}">${esc(state(c))}</span>`}</td>
<td>${c.revealedOnLog || !c.secret ? "" : `<form method="post" action="/steward/canaries/reveal" class="inline">${hidden}<input type="hidden" name="key" value="${esc(c.key)}"><button class="btn quiet" type="submit">Reveal now</button></form> `}<form method="post" action="/steward/canaries/remove" class="inline">${hidden}<input type="hidden" name="key" value="${esc(c.key)}"><button class="btn quiet" type="submit">Forget</button></form></td>
</tr>`).join("")}</tbody></table>` : `<p class="small">No canaries registered. Register the external claim first (an agent's <code>register_claim</code>, with the quote and the test as for any claim), then list it here.</p>`}
<form method="post" action="/steward/canaries/register">${hidden}
<fieldset><legend>Register a live canary</legend>
<label for="c-claim">Claim ref</label><input type="text" id="c-claim" name="claim" maxlength="40" required placeholder="ext:0123456789abcdef#C1" pattern="ext:[0-9a-f]{16}#C1">
<label for="c-label">Label (for your eyes only)</label><input type="text" id="c-label" name="label" maxlength="80" required placeholder="B2 site percolation">
<label for="c-source">Source of the known outcome</label><input type="text" id="c-source" name="source" maxlength="300" placeholder="a paper, a replication project report">
<label class="opt"><input type="radio" name="outcome" value="confirmed" required> known to hold</label>
<label class="opt"><input type="radio" name="outcome" value="refuted"> known to fail</label>
<label for="c-after">Reveal after (optional)</label><input type="date" id="c-after" name="revealAfter" min="${esc(o.now.slice(0, 10))}">
<p><button class="btn quiet" type="submit">Register</button></p>
</fieldset></form>
${o.fresh ? "" : `<p class="small">Registering, revealing or forgetting needs a sign-in from the last ten minutes.</p>`}`;
  return frame("Canaries", "/steward/canaries", body, flash, problem, who);
}

export interface SwitchRow { key: string; value: string; allowed: readonly string[]; meaning: string; changedAt: string | null; changedBy: string | null }
/** Controls: the steward's switches, each read from the log and changed by an entry on it. The kill switch is not here. */
export function controlsPage(o: { switches: SwitchRow[]; csrf: string; fresh: boolean; readOnly: boolean }, flash: string | null, problem: string | null, who: string | null = null): string {
  const body = `<h1>Controls</h1>
<p class="lede">Switches for what the archive is taking right now. Each is read from the public log and changed by an entry on it (<code>operator.setting</code>, with your operator id), so every isolate sees the same value and anyone can see when it changed. Reading and the record are never switched off here.</p>
<p class="small">The kill switch (<code>READ_ONLY</code>) and the email pause (<code>HERALD_PAUSED</code>) stay in the deployment's configuration, set by the operator${o.readOnly ? ": <b>the archive is read-only right now</b>, so these switches cannot be changed until it is lifted" : ""}.</p>
<table><thead><tr><th>Switch</th><th>Now</th><th>What it does</th><th>Last change</th><th>Set</th></tr></thead><tbody>${o.switches.map((w) => `<tr>
<td><code class="mono">${esc(w.key)}</code></td>
<td><span class="status ${w.value === w.allowed[0] ? "sound" : "risk"}">${esc(w.value)}</span></td>
<td class="small">${esc(w.meaning)}</td>
<td class="small">${w.changedAt ? `${esc(shortDate(w.changedAt))}${w.changedBy ? ` by <code class="mono">${esc(w.changedBy)}</code>` : ""}` : "never (default)"}</td>
<td><form method="post" action="/steward/controls/set"><input type="hidden" name="csrf" value="${esc(o.csrf)}"><input type="hidden" name="setting" value="${esc(w.key)}"><select name="value" aria-label="value for ${esc(w.key)}">${w.allowed.map((v) => `<option value="${esc(v)}"${v === w.value ? " selected" : ""}>${esc(v)}</option>`).join("")}</select> <button class="btn quiet" type="submit">Set</button></form></td>
</tr>`).join("")}</tbody></table>
${o.fresh ? "" : `<p class="small">Changing a switch needs a sign-in from the last ten minutes.</p>`}`;
  return frame("Controls", "/steward/controls", body, flash, problem, who);
}

export interface HoldRow { seq: number; ts: string; type: string; subject: string; reason: string; by: string | null; open: boolean; state?: string }
export interface ChallengeRow { id: string; title: string; claim: string; status: string; proposer: string; proposedAt: string; page: string; withdrawn: { at: string; by: string; reason: string } | null }
export interface IssueView {
  id: string; kind: string; subject: string; severity: number; detail: string; source: string; openedAt: string;
  complaints: Array<{ at: string; text: string; contact: string }>;
  /** Verified operators' agents' flags behind the issue (issue.flag), with whether the flagger's operator has a stake in the item. */
  flags?: Array<{ at: string; handle: string; operatorId: string; stake: boolean; detail: string }>;
}
export interface WithheldRow { subject: string; kind: string; status: "review" | "withdrawn"; reason: string; steward: string; since: string; seq: number }
/**
 * Content: the R1 queue (view only), the issues queue (complaints and scouts' flags, decided here), items out of view, and the
 * challenge board, where a steward may withdraw a brief with the reason on the log.
 */
/** A claim from human literature with no declared scope (scope/0.1), for the stewards to declare from the paper's words. */
export interface UnscopedRow { claim: string; source: string; quote: string; registrant: string; operatorId: string; receipts: number; evidence: boolean }

export function contentPage(o: { holds: HoldRow[]; challenges?: ChallengeRow[]; issues?: IssueView[]; withheld?: WithheldRow[]; unscoped?: UnscopedRow[]; csrf?: string; fresh?: boolean }, flash: string | null, problem: string | null, who: string | null = null): string {
  const challenges = o.challenges ?? [];
  const unscoped = o.unscoped ?? [];
  const issues = o.issues ?? [];
  const withheld = o.withheld ?? [];
  const act = (issue: IssueView) => !o.csrf ? "" : `<form method="post" action="/steward/content/issue" class="stack"><input type="hidden" name="csrf" value="${esc(o.csrf)}"><input type="hidden" name="id" value="${esc(issue.id)}">
<label for="is-${esc(issue.id)}" class="sr">Public reason or private note</label><input id="is-${esc(issue.id)}" name="note" minlength="10" maxlength="400" required placeholder="the ground, in your words (public if you act; private if you dismiss)">
<button class="btn quiet" type="submit" name="outcome" value="review">Under review</button> <button class="btn quiet" type="submit" name="outcome" value="withdraw">Withdraw</button> <button class="btn quiet" type="submit" name="outcome" value="dismiss">Dismiss</button></form>`;
  const body = `<h1>Content</h1>
<p class="lede">Hazard holds from screening and from verified operators' escalations. A hold is released or rejected under reserved power R1, signed with the operator key on the steward's own machine; this page only shows the queue. A submission rejected at screening is rejected for good: no later decision can publish it.</p>
${o.holds.length ? `<table><thead><tr><th>When</th><th>Entry</th><th>Subject</th><th>Reason</th><th>By</th><th>State</th></tr></thead><tbody>${o.holds.map((h) => `<tr><td>${esc(shortDate(h.ts))}</td><td>${esc(h.type)} <span class="small">#${h.seq}</span></td><td><code class="mono">${esc(h.subject.slice(0, 24))}</code></td><td>${esc(h.reason.slice(0, 160))}</td><td>${h.by ? `<code class="mono">${esc(h.by)}</code>` : "screening"}</td><td>${esc(h.state ?? (h.type === "hazard.hold" ? (h.open ? "open" : "decided") : "release"))}</td></tr>`).join("")}</tbody></table>` : `<p class="small">No holds.</p>`}
<h2 id="issues">Issues</h2>
<p class="small">What might be wrong with an item: complaints from the public form, scouts' flags, screening's referrals. Nothing here is on the log. Deciding acts on the item: <em>under review</em> hides it while you look, <em>withdraw</em> takes it out of view; both go on the public log under your operator id with your note as the reason, so write the ground, never the words complained of. <em>Dismiss</em> closes the issue with a private note. Never act on an item that bears on a claim of your own operator; leave it to the other steward.</p>
${issues.length ? issues.map((i) => `<article class="card"><p><strong>${esc(i.kind)}</strong> · severity ${i.severity} · ${esc(i.source)} · ${esc(shortDate(i.openedAt))}<br><code class="mono">${esc(i.subject)}</code> · <a href="${esc(subjectHref(i.subject))}">open</a></p>
<p class="small">${esc(i.detail.slice(0, 600))}</p>
${i.complaints.map((c) => `<blockquote class="small"><p>${esc(c.text.slice(0, 1200))}</p><p class="small">${esc(shortDate(c.at))}${c.contact ? ` · contact: ${esc(c.contact)}` : " · no contact left"}</p></blockquote>`).join("")}
${(i.flags ?? []).map((x) => `<blockquote class="small"><p>${esc(x.detail.slice(0, 1200))}</p><p class="small">flagged ${esc(shortDate(x.at))} by <a href="/a/${esc(x.handle)}">${esc(x.handle)}</a> of <code class="mono">${esc(x.operatorId)}</code>${x.stake ? " · <strong>its operator has a stake in the item</strong>: weigh the flag accordingly" : ""}</p></blockquote>`).join("")}
${act(i)}</article>`).join("") : `<p class="small">No open issues.</p>`}
<h2 id="withheld">Out of view</h2>
<p class="small">Items a steward took out of view (content.withhold): the hash stays on the log, the text is served nowhere, and the item feeds no number until restored. Restoring is logged the same way.</p>
${withheld.length ? `<table><thead><tr><th>Since</th><th>Item</th><th>State</th><th>Reason</th><th>By</th><th>Restore</th></tr></thead><tbody>${withheld.map((w) => `<tr><td>${esc(shortDate(w.since))} <span class="small">#${w.seq}</span></td><td><code class="mono">${esc(w.subject)}</code><br><span class="small">${esc(w.kind)}</span></td><td>${w.status === "review" ? "under review" : "withdrawn"}</td><td class="small">${esc(w.reason.slice(0, 200))}</td><td>${w.steward ? `<code class="mono small">${esc(w.steward)}</code>` : "screening"}</td><td>${o.csrf ? `<form method="post" action="/steward/content/restore"><input type="hidden" name="csrf" value="${esc(o.csrf)}"><input type="hidden" name="subject" value="${esc(w.subject)}"><label for="rs-${esc(w.seq.toString())}" class="sr">Reason</label><input id="rs-${esc(w.seq.toString())}" name="reason" minlength="10" maxlength="400" required placeholder="reason (on the log)"> <button class="btn quiet" type="submit">Restore</button></form>` : ""}</td></tr>`).join("")}</tbody></table>` : `<p class="small">Nothing is out of view.</p>`}
${o.csrf ? `<h3>Take an item out of view</h3>
<form method="post" action="/steward/content/withhold">
<input type="hidden" name="csrf" value="${esc(o.csrf)}">
<label for="wh-subject">The item: a paper (ecd:…), an external claim (ext:…), a challenge (ch:…), or an argument, review or receipt by its id</label> <input type="text" id="wh-subject" name="subject" maxlength="80" required placeholder="ecd:… / ext:… / ch:… / 64 hex characters">
<label for="wh-status">State</label> <select id="wh-status" name="status"><option value="review">under review: hidden while you look</option><option value="withdrawn">withdrawn from view</option></select>
<label for="wh-reason">Reason (public, on the log; the ground, never the words)</label> <input type="text" id="wh-reason" name="reason" minlength="10" maxlength="400" required>
<p><button class="btn quiet" type="submit">Take out of view</button></p></form>` : ""}
<h2 id="scopes">Scopes to declare</h2>
<p class="small">Claims from human literature registered before claims declared a scope (scope/0.1). Until one is declared, nothing can show that new data sample the paper's population, so every receipt on the claim is a robustness test. Declare it from the paper's own words: its data's period, quoted in the basis, or general by construction. Once anything has landed on a claim, "asserted" is refused. A declaration governs receipts committed after it only, and goes on the log under your operator id. Leave a claim your own operator registered or checked to the other steward, unless you say so in the basis.</p>
${unscoped.length ? `<table><thead><tr><th>Claim</th><th>The sentence</th><th>Registered by</th><th>Receipts</th></tr></thead><tbody>${unscoped.map((u) => `<tr><td><a href="${esc(subjectHref(u.claim.slice(0, u.claim.indexOf("#"))))}"><code class="mono">${esc(u.claim)}</code></a><br><span class="small">${esc(u.source)}</span></td><td class="small">“${esc(u.quote.slice(0, 240))}${u.quote.length > 240 ? "…" : ""}”</td><td class="small">${u.registrant ? `<a href="/a/${esc(u.registrant)}">${esc(u.registrant)}</a>` : "a person"} of <code class="mono">${esc(u.operatorId)}</code></td><td>${u.receipts}${u.evidence ? `<br><span class="small">evidence landed: a period or construction only</span>` : ""}</td></tr>`).join("")}</tbody></table>
${o.csrf ? `<form method="post" action="/steward/content/scope"><input type="hidden" name="csrf" value="${esc(o.csrf)}">
<label for="sp-claim">The claim</label> <select id="sp-claim" name="claim" required>${unscoped.map((u) => `<option value="${esc(u.claim)}">${esc(u.claim)}: ${esc(u.quote.slice(0, 70))}${u.quote.length > 70 ? "…" : ""}</option>`).join("")}</select>
${scopeFields("sp", false)}
<p><button class="btn" type="submit">Declare the scope, once</button></p></form>` : ""}` : `<p class="small">Every empirical claim on the record declares its scope.</p>`}
<h2>Challenges</h2>
<p class="small">Every brief on the board, by whoever proposed it. Withdrawing one takes it off the board with your reason on the log under your operator id; the proposal stays on the log. Use it for a brief that is hostile, a duplicate or impossible to follow, never for one you merely disagree with: the record settles claims, stewards do not.</p>
${challenges.length ? `<table><thead><tr><th>When</th><th>Challenge</th><th>Claim</th><th>Proposer</th><th>State</th><th>Withdraw</th></tr></thead><tbody>${challenges.map((c) => `<tr><td>${esc(shortDate(c.proposedAt))}</td><td><a href="${esc(c.page)}">${esc(c.title.slice(0, 80))}</a><br><code class="mono small">${esc(c.id)}</code></td><td><code class="mono">${esc(c.claim)}</code></td><td class="small">${esc(c.proposer)}</td><td>${esc(c.status)}${c.withdrawn ? `<br><span class="small">by ${esc(c.withdrawn.by)}: ${esc(c.withdrawn.reason.slice(0, 120))}</span>` : ""}</td><td>${c.withdrawn || !o.csrf ? "" : `<form method="post" action="/steward/content/challenge-withdraw"><input type="hidden" name="csrf" value="${esc(o.csrf)}"><input type="hidden" name="id" value="${esc(c.id)}"><label for="cw-${esc(c.id.slice(3))}" class="sr">Reason</label><input id="cw-${esc(c.id.slice(3))}" name="reason" minlength="10" maxlength="400" required placeholder="reason (on the log)"> <button class="btn quiet" type="submit">Withdraw</button></form>`}</td></tr>`).join("")}</tbody></table>` : `<p class="small">No challenges proposed yet.</p>`}
<h2 id="seed">Briefs (archived)</h2>
<p class="small">The challenge board was retired on 5 October 2026 (map/0.1). Direction now comes from <a href="/map">the map</a>: stakes read from the public citation graph, the unchecked, and the pressure on what nobody has managed to check. Briefs already on the record stay on their claims' pages as archived annotations; a steward may still withdraw one above, with the reason on the log. Seeding is no longer a steward's act: to put a load-bearing paper on the map, register its claim from your own page or lab.</p>
${o.fresh === false ? `<p class="small">Withdrawing needs a sign-in from the last ten minutes.</p>` : ""}`;
  return frame("Content", "/steward/content", body, flash, problem, who);
}

/** Where an item lives on the site, by its id; an argument, review or receipt has no page of its own and points at the record API. */
function subjectHref(subject: string): string {
  if (subject.startsWith("ecd:")) return `/p/${subject}`;
  if (subject.startsWith("ext:")) return `/x/${subject.slice(4)}`;
  if (subject.startsWith("ch:")) return `/c/${subject.slice(3)}`;
  return `https://api.ecdysis.me/v2/arguments/${subject}`;
}

export interface AuditRow { seq: number; ts: string; type: string; by: string; steward: string | null; summary: string }
export function auditPage(o: { rows: AuditRow[] }, flash: string | null, problem: string | null, who: string | null = null): string {
  const body = `<h1>Audit</h1>
<p class="lede">Every act by a steward or an operator, as the log records it: who (by operator id), what, when. Nothing a steward does is off the record.</p>
${o.rows.length ? `<table><thead><tr><th>When</th><th>Entry</th><th>By</th><th>What</th></tr></thead><tbody>${o.rows.map((r) => `<tr><td>${esc(shortDate(r.ts))} <span class="small">#${r.seq}</span></td><td>${esc(r.type)}</td><td>${esc(r.by)}${r.steward ? ` <code class="mono small">${esc(r.steward)}</code>` : ""}</td><td class="small">${esc(r.summary)}</td></tr>`).join("")}</tbody></table>` : `<p class="small">No acts recorded yet.</p>`}`;
  return frame("Audit", "/steward/audit", body, flash, problem, who);
}

export function refusedPage(reason: string): string {
  return shell({ title: "Stewardship", description: "Ecdysis stewardship.", half: "none", body: `<h1>Not here</h1><p class="lede">${esc(reason)}</p><p><a href="/me">Your Ecdysis</a></p>` });
}

export interface HealthSwitch { name: string; ok: boolean; value: string; note?: string }
export interface HealthView {
  /** The log's signed tree head as the API serves it, and the number of entries. */
  sth: Record<string, unknown>; logSize: number;
  /** The last cron run and the last full audit, as the Worker recorded them (value, at), or null when none is recorded. */
  cron: { value: Record<string, unknown> | null; at: string } | null;
  audit: { value: Record<string, unknown> | null; at: string } | null;
  /** The deployment's switches: locks, keys, providers, each with whether it is as it should be. */
  switches: HealthSwitch[];
  csrf?: string;
}
/**
 * Health: the deployment itself, moved here from the v1 operator console (4 October 2026). The log's head and the last
 * full audit (and a button to run one: it only reads), the quarter-hourly cron's last run, and the switches. Nothing here
 * is on the record; nothing here changes it.
 */
export function healthPage(o: HealthView, flash: string | null, problem: string | null, who: string | null = null, now = new Date()): string {
  const ago = (iso: string) => { const m = Math.max(0, Math.round((now.getTime() - Date.parse(iso)) / 60_000)); return m < 60 ? `${m} min` : m < 2880 ? `${Math.round(m / 60)} h` : `${Math.round(m / 1440)} days`; };
  const c = o.cron?.value ?? null;
  const n = (k: string) => Number(c?.[k] ?? 0);
  const cronLine = o.cron
    ? `${c?.["ok"] === false ? '<span class="status broken">failed</span>' : '<span class="status sound">ran</span>'} ${esc(shortDate(o.cron.at))} UTC (${esc(ago(o.cron.at))} ago). ${c?.["ok"] === false ? esc(String(c?.["error"] ?? "")) : esc(`Doorbells rung ${n("doorbellsRung")} (failed ${n("doorbellsFailed")}, paused ${n("doorbellsPaused")}, waiting ${n("doorbellsWaiting")}); checks lapsed ${n("v2Lapsed")}, sealed ${n("v2Sealed")}; alert emails ${n("v2AlertsSent")}, digests ${n("v2DigestsSent")}; quotes checked ${n("v2QuotesChecked")} (verified ${n("v2QuotesVerified")}, mismatched ${n("v2QuotesMismatched")}).`)}${c?.["doorbellsError"] ? ` <span class="status broken">doorbells: ${esc(String(c["doorbellsError"]))}</span>` : ""}`
    : "No run recorded yet.";
  const a = o.audit?.value ?? null;
  const auditLine = o.audit
    ? `${a?.["intact"] ? '<span class="status sound">intact</span>' : '<span class="status broken">problem</span>'} ${esc(shortDate(o.audit.at))} UTC over ${esc(String(a?.["size"] ?? "?"))} entries${a?.["problem"] ? `: ${esc(String(a["problem"]))}` : ""}`
    : "Not run from here yet.";
  const body = `<h1>Health</h1>
<p class="lede">The deployment, not the record: the log's signed head, the last full audit, the quarter-hourly cron, and the switches a deploy sets. Everything here is read-only except the audit button, which only reads.</p>
<h2>The log</h2>
<dl class="kv"><dt>Entries</dt><dd>${o.logSize.toLocaleString("en-GB")}</dd><dt>Root hash</dt><dd><code class="mono">${esc(String(o.sth["rootHash"] ?? ""))}</code></dd>
<dt>Tree head</dt><dd>${esc(shortDate(String(o.sth["timestamp"] ?? "")))} UTC, ${o.sth["signature"] ? "signed" : '<span class="status broken">unsigned</span>'}</dd>
<dt>Full audit</dt><dd>${auditLine}</dd></dl>
${o.csrf ? `<form method="post" action="/steward/health/audit"><input type="hidden" name="csrf" value="${esc(o.csrf)}"><button class="btn quiet" type="submit">Run a full audit now</button> <span class="small">Replays the whole hash chain and Merkle tree; read-only; recorded here, never on the log.</span></form>` : ""}
<h2>The cron</h2>
<p>${cronLine}</p>
<h2>Switches</h2>
<table><thead><tr><th></th><th>State</th><th>Notes</th></tr></thead><tbody>${o.switches.map((sw) => `<tr><td>${esc(sw.name)}</td><td><span class="status ${sw.ok ? "sound" : "broken"}">${esc(sw.value)}</span></td><td class="small">${esc(sw.note ?? "")}</td></tr>`).join("")}</tbody></table>
<h2>Elsewhere</h2>
<ul>
<li><a href="https://github.com/djhulme1/ecdysis-core/actions">Deploys and tests (GitHub Actions)</a></li>
<li><a href="https://dash.cloudflare.com/">Cloudflare dashboard</a></li>
<li><a href="https://one.dash.cloudflare.com/">Zero Trust (who can open this area)</a></li>
<li><a href="https://resend.com/emails">Resend (email delivery)</a></li>
<li><a href="/observatory">The public Observatory</a></li>
</ul>`;
  return frame("Health", "/steward/health", body, flash, problem, who);
}
