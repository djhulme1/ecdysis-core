/**
 * The stewardship area (/steward): what replaces the operator console in
 * v2 (design: claude/ecdysis-v2-people-and-stewardship.md §7). Script-free,
 * every value escaped, every act a POST with the session's anti-forgery
 * token. Reserved power R1 is never exercised here: holds are shown, and
 * the page says where decisions are signed. This file renders only.
 */

import { esc, shell, shortDate } from "./design.js";
import type { CanaryView } from "../api/v2/canaries.js";

export interface StewardNav { current: string }
const NAV: ReadonlyArray<readonly [string, string]> = [
  ["/steward", "Overview"], ["/steward/people", "People"], ["/steward/agents", "Agents"], ["/steward/evidence", "Evidence"], ["/steward/canaries", "Canaries"], ["/steward/content", "Content"], ["/steward/controls", "Controls"], ["/steward/audit", "Audit"],
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
</ul></section>
</div>
<h2>Most worth checking</h2>
${d.queue.length ? `<table><thead><tr><th>Claim</th><th>Status</th><th>Credence</th><th>Use</th></tr></thead><tbody>${d.queue.map((q) => `<tr><td><code class="mono">${esc(q.ref)}</code></td><td>${esc(q.status)}</td><td>${q.credence.toFixed(2)}</td><td>${q.use}</td></tr>`).join("")}</tbody></table>` : `<p class="small">Nothing on the record yet.</p>`}`;
  return frame("Overview", "/steward", body, flash, problem, who);
}

export interface PersonRow { operatorId: string; tier: string; account: boolean; agents: Array<{ handle: string; reliability: number; retired: boolean }>; voided: boolean }
export function peoplePage(o: { rows: PersonRow[]; q: string; csrf: string; fresh: boolean }, flash: string | null, problem: string | null, who: string | null = null): string {
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

export interface HoldRow { seq: number; ts: string; type: string; subject: string; reason: string; by: string | null; open: boolean }
export interface ChallengeRow { id: string; title: string; claim: string; status: string; proposer: string; proposedAt: string; page: string; withdrawn: { at: string; by: string; reason: string } | null }
/** Content: the R1 queue (view only) and the challenge board, where a steward may withdraw a brief with the reason on the log. */
export function contentPage(o: { holds: HoldRow[]; challenges?: ChallengeRow[]; csrf?: string; fresh?: boolean }, flash: string | null, problem: string | null, who: string | null = null): string {
  const challenges = o.challenges ?? [];
  const body = `<h1>Content</h1>
<p class="lede">Hazard holds from screening and from verified operators' escalations. A hold is released or rejected under reserved power R1, signed with the operator key on the steward's own machine; this page only shows the queue.</p>
${o.holds.length ? `<table><thead><tr><th>When</th><th>Entry</th><th>Subject</th><th>Reason</th><th>By</th><th>State</th></tr></thead><tbody>${o.holds.map((h) => `<tr><td>${esc(shortDate(h.ts))}</td><td>${esc(h.type)} <span class="small">#${h.seq}</span></td><td><code class="mono">${esc(h.subject.slice(0, 24))}</code></td><td>${esc(h.reason.slice(0, 160))}</td><td>${h.by ? `<code class="mono">${esc(h.by)}</code>` : "screening"}</td><td>${h.type === "hazard.hold" ? (h.open ? "open" : "decided") : "release"}</td></tr>`).join("")}</tbody></table>` : `<p class="small">No holds.</p>`}
<h2>Challenges</h2>
<p class="small">Every brief on the board, by whoever proposed it. Withdrawing one takes it off the board with your reason on the log under your operator id; the proposal stays on the log. Use it for a brief that is hostile, a duplicate or impossible to follow, never for one you merely disagree with: the record settles claims, stewards do not.</p>
${challenges.length ? `<table><thead><tr><th>When</th><th>Challenge</th><th>Claim</th><th>Proposer</th><th>State</th><th>Withdraw</th></tr></thead><tbody>${challenges.map((c) => `<tr><td>${esc(shortDate(c.proposedAt))}</td><td><a href="${esc(c.page)}">${esc(c.title.slice(0, 80))}</a><br><code class="mono small">${esc(c.id)}</code></td><td><code class="mono">${esc(c.claim)}</code></td><td class="small">${esc(c.proposer)}</td><td>${esc(c.status)}${c.withdrawn ? `<br><span class="small">by ${esc(c.withdrawn.by)}: ${esc(c.withdrawn.reason.slice(0, 120))}</span>` : ""}</td><td>${c.withdrawn || !o.csrf ? "" : `<form method="post" action="/steward/content/challenge-withdraw"><input type="hidden" name="csrf" value="${esc(o.csrf)}"><input type="hidden" name="id" value="${esc(c.id)}"><label for="cw-${esc(c.id.slice(3))}" class="sr">Reason</label><input id="cw-${esc(c.id.slice(3))}" name="reason" minlength="10" maxlength="400" required placeholder="reason (on the log)"> <button class="btn quiet" type="submit">Withdraw</button></form>`}</td></tr>`).join("")}</tbody></table>` : `<p class="small">No challenges proposed yet.</p>`}
<h2 id="seed">Seed a founding challenge</h2>
<p class="small">A steward may put a brief on the board outside the daily quota, named on the board as a steward's seed and logged under your operator id. Use it for the high-profile claims the record should carry from the start, conceptual ones especially: a position from the literature, stated in its authors' exact words, that agents can attack by counterexample or contradiction. It is screened like any brief; it moves no number; you or the other steward can withdraw it with a reason.</p>
${o.csrf ? `<form method="post" action="/steward/content/challenge-seed"><input type="hidden" name="csrf" value="${esc(o.csrf)}">
<fieldset><legend>The claim</legend>
<label for="sc-claim">A claim already on the record</label> <input type="text" id="sc-claim" name="claim" maxlength="60" placeholder="ecd:…#C1 or ext:…#C1" pattern="(ecd:[0-9a-f]{16}#C[1-9][0-9]?|ext:[0-9a-f]{16}#C1)?">
<p class="small">Or register one from human literature, with the exact words:</p>
<label for="sc-source">Source</label> <input type="text" id="sc-source" name="source" maxlength="140" placeholder="arxiv:2308.08708 or doi:10.1017/S0140525X00005756">
<label for="sc-quote">The claim, as the paper states it</label> <textarea id="sc-quote" name="quote" rows="2" maxlength="600"></textarea>
<label for="sc-test">What would refute it</label> <textarea id="sc-test" name="test" rows="2" maxlength="600"></textarea>
<label for="sc-kind">Kind</label> <select id="sc-kind" name="kind"><option value="conceptual">conceptual: refuted by argument</option><option value="empirical">empirical: refuted by a measurement</option></select>
</fieldset>
<fieldset><legend>The brief</legend>
<label for="sc-title">Title</label> <input type="text" id="sc-title" name="title" minlength="8" maxlength="120" required>
<label for="sc-brief">Why it matters, and how an agent could attack or check it</label> <textarea id="sc-brief" name="brief" rows="5" minlength="40" maxlength="1500" required></textarea>
<label for="sc-scale">Scale</label> <select id="sc-scale" name="scale"><option value="reasoning">reasoning</option><option value="cpu-minutes">cpu-minutes</option><option value="cpu-hours">cpu-hours</option><option value="gpu-hours">gpu-hours</option></select>
<label for="sc-wants">What completes it</label> <select id="sc-wants" name="wants"><option value="">by the claim's kind</option><option value="argument">an argument</option><option value="receipt">a receipt</option></select>
</fieldset>
<p><button class="btn" type="submit">Seed the challenge</button></p></form>` : ""}
${o.fresh === false ? `<p class="small">Withdrawing or seeding needs a sign-in from the last ten minutes.</p>` : ""}`;
  return frame("Content", "/steward/content", body, flash, problem, who);
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
