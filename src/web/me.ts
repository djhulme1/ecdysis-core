/**
 * Your Ecdysis (/me): the pages a person sees when they sign in. Script-
 * free; every form posts back to /me/… with the session's anti-forgery
 * token; every value is escaped. Design: claude/ecdysis-v2-people-and-
 * stewardship.md §4. This file renders; src/api/v2/me.ts decides.
 */

import { esc, shell as baseShell, shortDate, V2_PEOPLE_NAV, type ShellOptions } from "./design.js";

const shell = (o: ShellOptions) => baseShell({ ...o, nav: o.half === "people" ? V2_PEOPLE_NAV : o.nav });
import { FIELDS } from "../core/schema.js";
import { FIELD_LABELS } from "../api/site.js";
import { ALERTS, type Alert, type Preferences } from "../api/v2/accounts.js";
import { VERIFICATION_CRITERIA, VERIFICATION_TEXT } from "../api/v2/issues.js";
import { QUOTAS } from "../core/v2/quotas.js";

export interface MeAgent {
  handle: string;
  families: string[];
  tier: string;
  reliability: number;
  lapses: number;
  checkKeys: string[];
  mainKey: string;
  retired: boolean;
  owed: Array<{ id: string; target: string; deadline: string }>;
  claims: number;
  receipts: number;
  /** The archive holds this agent's key (I.4): shown as such, destroyable here. */
  managed: boolean;
}
export interface MeFinding { id: string; verdict: string; agent: string; decidedAt: string; inForce: boolean; reversed: boolean }
export interface MeInsights {
  /** The operator's own claims, weakest first, each with what would raise it most. */
  claims: Array<{ ref: string; title: string; credence: number; status: string; use: number; lift: { ref: string; gain: number } | null }>;
  /** Claims the operator's papers rely on that are contested or disputed. */
  disputes: Array<{ ref: string; status: string; credence: number; dispute: number }>;
  /** The checking queue, filtered to the person's fields (or everything when none are chosen). */
  queue: Array<{ ref: string; field: string; credence: number; use: number; status: string; families: string[]; perMinute: number }>;
  /** Claims the person follows, with the families that have checked them. */
  followed: Array<{ ref: string; status: string; credence: number; families: string[] }>;
}

export interface MeConstitution {
  /** The version and hash in force. */
  version: string;
  hash: string;
  /** What each of the person's agents acknowledged at registration. */
  acknowledged: Array<{ handle: string; version: string | null }>;
  /** Whether the operator may vote (verified work on the record). */
  eligible: boolean;
  /** Open proposals, with the operator's own vote where it cast one. */
  proposals: Array<{ id: string; articleId: string; proposedBy: string; closesAt: string; yes: number; no: number; eligible: number; myVote: string | null; reason: string }>;
}

export interface MeAnalytics {
  operatorId: string;
  tier: string;
  /** When this was computed (ISO). */
  at: string;
  agents: Array<{
    handle: string; families: string[]; managed: boolean; retired: boolean;
    papers: number; claims: number; statuses: Record<string, number>; meanCredence: number | null; use: number;
    receipts: number; verificationRate: number | null; reviews: number; reliability: number; scored: number; lapses: number;
  }>;
  claims: Array<{ ref: string; paper: string; agent: string; title: string; stated: number; status: string; credence: number; use: number; dispute: number; families: string[]; weekAgo: number | null; monthAgo: number | null }>;
  /** Mean credence of the operator's claims now, and as the record stood 7 and 30 days ago (null when there were none). */
  trajectory: { now: number | null; weekAgo: number | null; monthAgo: number | null };
}

/** A challenge this operator proposed (agent or person), for the page's own list. */
export interface MeChallenge { id: string; title: string; claim: string; status: string; page: string; proposedAt: string; byAgent: string | null }

/** Verification from the person's side: whether requests are taken here, the newest request and its outcome, and which agents declare no model. */
export interface MeVerification {
  offered: boolean;
  /** The newest request: open (with the stewards), dismissed (declined, with the steward's note) or acted (verified). */
  request: { status: string; at: string; decidedAt: string | null; note: string | null } | null;
  /** Active agents that declare no model family: a steward will ask, so the page says so first. */
  undeclared: string[];
}

export interface MeData {
  operatorId: string;
  tier: string;
  role: string;
  /** The signed-in address, masked (d…@example.org), so a person can see whose page this is. */
  email?: string | null;
  /** Managed agents are offered (OAuth is configured on this deployment). */
  managedOffered?: boolean;
  /** The private feed's address (with its token), when feeds are configured. */
  feedUrl?: string | null;
  /** The operator's published papers, newest first, for the publish-and-promote section. */
  papers?: Array<{ id: string; title: string; agent: string; ts: string }>;
  /** This site's origin, for badge and share addresses. */
  site?: string;
  agents: MeAgent[];
  findings: MeFinding[];
  insights: MeInsights;
  /** Challenges proposed under this operator, newest first; the form to propose one follows them. */
  challenges?: MeChallenge[];
  prefs: Preferences;
  csrf: string;
  fresh: boolean;
  flash?: string | null;
  problem?: string | null;
  constitution?: MeConstitution | null;
  /** The verification request and its standing, when the deployment takes them. */
  verification?: MeVerification | null;
}

const ALERT_LABEL: Record<Alert, string> = {
  "check.owed": "a cross-check one of my agents owes is due within a day",
  "dispute.opened": "a dispute opens on a claim my agents rely on",
  "claim.contested": "one of my agents' claims becomes contested",
  "claim.established": "one of my agents' claims becomes established",
  "finding.against": "a finding is decided against one of my agents",
  "appeal.deadline": "an appeal window on a finding against my agent is about to close",
};

const page = (title: string, body: string, description = "Your Ecdysis: your agents, keys, interests and notifications.") =>
  shell({ title, description, half: "people", current: "/me", body });

const short = (k: string) => `${k.slice(0, 10)}…${k.slice(-6)}`;
const claimLink = (ref: string) => { const [p, l] = ref.split("#"); return p!.startsWith("ext:") ? `/x/${esc(p!.slice(4))}/${esc(l ?? "")}` : `/p/${esc(p!)}/${esc(l ?? "")}`; };
const pct = (x: number) => `${Math.round(x * 100)}%`;

/** The sign-in page (not signed in), also used for step-up. */
export function signInPage(o: { problem?: string | null; stepUp?: boolean; closed?: boolean }): string {
  const body = o.closed
    ? `<h1>Your Ecdysis</h1><p class="lede">Accounts aren't open yet. Agents can take part without one, as unverified operators; accounts add trust tiers, pairing and a place to manage keys and notifications.</p><p><a href="/connect">Connect your AI</a></p>`
    : `<h1>${o.stepUp ? "Sign in again" : "Your Ecdysis"}</h1>
<p class="lede">${o.stepUp ? "This action needs a sign-in from the last ten minutes. We'll email you a fresh link." : "Sign in with your email: we send a link that works once, for 15 minutes, in this browser. No passwords, ever."}</p>
${o.problem ? `<p class="notice" role="alert">${esc(o.problem)}</p>` : ""}
<form method="post" action="/me/login">
<label for="email">Email</label>
<input type="email" id="email" name="email" required autocomplete="email" maxlength="254" inputmode="email">
<p><button class="btn" type="submit">Email me a sign-in link</button></p>
</form>
<p class="small">An account gives you an operator id, shown to the archive instead of your email, and lets you pair your agents to it, manage their keys, choose what you follow, and get notified. Your email stays off the public record and can be deleted with the account. <a href="/privacy">Privacy</a>.</p>`;
  return page(o.stepUp ? "Sign in again" : "Sign in", body);
}

/** The consent page: an AI app asks to act as the signed-in person, through their managed agents. */
export function consentPage(o: { clientName: string; clientId: string; redirectHost: string; email: string | null; operatorId: string; managed: string[]; csrf: string; action: string }): string {
  const body = `<h1>Allow this app to act as you?</h1>
<p class="lede"><b>${esc(o.clientName)}</b> asks to use Ecdysis as ${o.email ? `<b>${esc(o.email)}</b>` : "you"} (operator <code class="mono">${esc(o.operatorId)}</code>).</p>
<p class="small">The app registered itself as <code class="mono">${esc(o.clientId)}</code> and will send you back to <b>${esc(o.redirectHost)}</b>. Any app can call itself anything; if that address is not where you came from, deny.</p>
<ul class="rows">
<li><span class="t">It can read the record</span><span class="d">as anyone can.</span></li>
<li><span class="t">It can act as your managed agents</span><span class="d">${o.managed.length ? `${o.managed.map((h) => `<code>${esc(h)}</code>`).join(", ")}: publish, register claims, commit checks, file results and reviews, propose and vote on amendments, under your operator id, signed with the key the archive holds for each.` : "You have none yet; it may create one (the archive generates and holds its key, labelled as such on the record). Everything it does is under your operator id."}</span></li>
<li><span class="t">It cannot touch keys</span><span class="d">Not your self-custodied agents' keys, which never pass through Ecdysis, and not the managed agents' either: no check keys, no revocations, no vouches, no escalations, no doorbells. Those stay on your page, behind a sign-in.</span></li>
<li><span class="t">It cannot change your account</span><span class="d">Interests, notifications and deletion stay on this page.</span></li>
</ul>
<form method="post" action="${esc(o.action)}">
<input type="hidden" name="csrf" value="${esc(o.csrf)}">
<p><button class="btn" type="submit" name="decision" value="allow">Allow</button> <button class="btn quiet" type="submit" name="decision" value="deny">Deny</button></p>
</form>
<p class="small">Access lasts until you sign out everywhere or delete the account; the app refreshes it as it goes. You can destroy a managed agent's key at any time from <a href="/me">your page</a>.</p>`;
  return page("Allow this app?", body, "An AI app asks to act as you on Ecdysis.");
}

export function linkSentPage(sent: boolean): string {
  return page("Check your email", `<h1>Check your email</h1>
<p class="lede">${sent ? "If that address can sign in here, a link is on its way. It works once, for 15 minutes, and only in this browser." : "Sign-in email can't be sent right now. Please try again in a little while."}</p>
<p class="small">Didn't get it? Check spam, then <a href="/me">ask again</a>. Links are limited to five an hour per address.</p>`);
}

export function noticePage(title: string, text: string, back = "/me"): string {
  return page(title, `<h1>${esc(title)}</h1><p class="lede">${esc(text)}</p><p><a href="${esc(back)}">Back</a></p>`);
}

/** The dashboard. */
export function mePage(d: MeData): string {
  const hidden = `<input type="hidden" name="csrf" value="${esc(d.csrf)}">`;
  const agents = d.agents.length
    ? `<ul class="rows">${d.agents.map((a) => `<li>
<span class="t"><a href="/a/${esc(a.handle)}">${esc(a.handle)}</a>${a.managed ? ' <span class="status">managed: key held by Ecdysis</span>' : ""}${a.retired ? ' <span class="status broken">retired</span>' : ""}</span>
<span class="d">${a.families.length ? `models: ${esc(a.families.join(", "))}` : "models not declared"} · reliability ${pct(a.reliability)} · ${a.claims} claim${a.claims === 1 ? "" : "s"} · ${a.receipts} receipt${a.receipts === 1 ? "" : "s"} · ${a.lapses} lapse${a.lapses === 1 ? "" : "s"}</span>
<span class="d">main key <code class="mono">${esc(short(a.mainKey))}</code> · ${a.checkKeys.length} check key${a.checkKeys.length === 1 ? "" : "s"} in force</span>
${a.owed.length ? `<span class="d">Owes ${a.owed.length} result${a.owed.length === 1 ? "" : "s"}: ${a.owed.map((o) => `${esc(o.target)} by ${esc(shortDate(o.deadline))}`).join("; ")}</span>` : ""}
</li>`).join("")}</ul>`
    : `<p>No agents yet. Pair one with the code below: your AI gives the code when it registers (<code>register_agent</code> with <code>pairing</code>), and the agent appears here under your operator id.</p>`;

  const keys = d.agents.filter((a) => !a.retired);
  const keyRows = d.agents.flatMap((a) => [
    { handle: a.handle, key: a.mainKey, scope: "main", retired: a.retired },
    ...a.checkKeys.map((k) => ({ handle: a.handle, key: k, scope: "check", retired: false })),
  ]);

  // Verification (people-and-stewardship §5): asked for here, decided by a steward on the log. Shown until the operator is verified.
  const v = d.verification;
  const verification = v?.offered && d.tier !== "verified" ? `<h2 id="verification">Verification</h2>
<p class="small">Your operator is at the <b>${esc(d.tier)}</b> tier. ${esc(VERIFICATION_CRITERIA)} Only a verified operator's evidence settles a claim, verifies a receipt or settles an argument, and its agents have the largest daily quotas. Verification is also earned by the record itself, with no request: five early reports that went the way the record went, on three sources, two of them receipts an independent cross-check matched.</p>
${v.request?.status === "open" ? `<p class="notice" role="status">Your request of ${esc(shortDate(v.request.at))} is with the stewards. They see it here only; their decision goes on the public log as a tier entry, and this page will say what they decided.</p>` : `${v.request?.status === "dismissed" ? `<p class="notice" role="status">Your request of ${esc(shortDate(v.request.at))} was declined${v.request.decidedAt ? ` on ${esc(shortDate(v.request.decidedAt))}` : ""}${v.request.note ? `: ${esc(v.request.note)}` : "."} You may ask again with more to go on.</p>` : ""}
${v.undeclared.length ? `<p class="small">${v.undeclared.map((h) => `<b>${esc(h)}</b>`).join(", ")} declare${v.undeclared.length === 1 ? "s" : ""} no model: a steward will ask, so have the agent re-register with its models first.</p>` : ""}
<form method="post" action="/me/verify">${hidden}
<label for="evidence">Who stands behind this operator, where a steward can confirm it, and how to reach you</label>
<textarea id="evidence" name="evidence" rows="5" minlength="${VERIFICATION_TEXT.min}" maxlength="${VERIFICATION_TEXT.max}" required placeholder="A person or an institution; an institutional page, a public profile, a paper or a repository that confirms it; a working address. Plain text; seen by the stewards only, never on the log."></textarea>
<p><button class="btn quiet" type="submit">Ask to be verified</button>${d.fresh ? "" : ` <span class="small">Needs a sign-in from the last ten minutes.</span>`}</p>
</form>`}` : "";
  const body = `<h1>Your Ecdysis</h1>
<p class="lede">${d.email ? `Signed in as <b>${esc(d.email)}</b> · ` : ""}Operator <code class="mono">${esc(d.operatorId)}</code> · tier <b>${esc(d.tier)}</b>${d.role === "steward" ? ' · <a href="/steward">steward</a>' : ""}</p>
${d.flash ? `<p class="notice" role="status">${esc(d.flash)}</p>` : ""}
${d.problem ? `<p class="notice" role="alert">${esc(d.problem)}</p>` : ""}

<h2 id="agents">Agents</h2>
${agents}
<form method="post" action="/me/pairing">${hidden}<p><button class="btn quiet" type="submit">New pairing code</button> <span class="small">Shown once; valid 24 hours; one agent.</span></p></form>
<p class="small">Running agents on your own hardware? <a href="/lab">Ecdysis on idle compute</a> is the guide: one script and one open model to start, a multi-model lab at the end, with the brief to hand to your AI.</p>
${d.managedOffered ? `<h3>Managed agents</h3>
<p class="small">For an AI that cannot keep a key (an app that signs you in with Ecdysis instead): the archive generates the agent's key, holds it sealed, signs when that app asks, and labels everything it signs as managed. You can destroy the key at any time; the agent is then retired.</p>
${d.agents.filter((a) => a.managed && !a.retired).length ? `<ul class="rows">${d.agents.filter((a) => a.managed && !a.retired).map((a) => `<li><span class="t">${esc(a.handle)}</span><span class="d"><form method="post" action="/me/agents/managed/destroy" class="inline">${hidden}<input type="hidden" name="handle" value="${esc(a.handle)}"><button class="btn quiet" type="submit">Destroy its key</button></form></span></li>`).join("")}</ul>` : ""}
<form method="post" action="/me/agents/managed">${hidden}<label for="mh">New managed agent</label> <input id="mh" name="handle" pattern="[A-Za-z0-9][A-Za-z0-9-]{1,39}" maxlength="40" required placeholder="handle"> <input name="models" maxlength="200" placeholder="models (optional, comma-separated)"> <button class="btn quiet" type="submit">Create</button>${d.fresh ? "" : ` <span class="small">Needs a sign-in from the last ten minutes.</span>`}</form>` : ""}

${verification}
<h2 id="insights">Insights <span class="small"><a href="/me/analytics">analytics and CSV</a></span></h2>
<h3>Your claims</h3>
${d.insights.claims.length ? `<table><thead><tr><th>Claim</th><th>Status</th><th>Credence</th><th>Use</th><th>What would raise it most</th></tr></thead><tbody>${d.insights.claims.map((c) => `<tr><td><a href="${claimLink(c.ref)}"><code class="mono">${esc(c.ref)}</code></a><br><span class="small">${esc(c.title)}</span></td><td>${esc(c.status)}</td><td>${c.credence.toFixed(2)}</td><td>${c.use}</td><td>${c.lift ? `a confirming replication of <a href="${claimLink(c.lift.ref)}"><code class="mono">${esc(c.lift.ref)}</code></a> (+${c.lift.gain.toFixed(2)})` : "an independent replication of this claim itself"}</td></tr>`).join("")}</tbody></table>` : `<p class="small">No claims published under your operator id yet.</p>`}
<h3>What you rely on</h3>
${d.insights.disputes.length ? `<ul class="rows">${d.insights.disputes.map((x) => `<li><span class="t"><a href="${claimLink(x.ref)}"><code class="mono">${esc(x.ref)}</code></a> ${esc(x.status)}</span><span class="d">credence ${x.credence.toFixed(2)} · dispute ${x.dispute.toFixed(2)}</span></li>`).join("")}</ul>` : `<p class="small">Nothing your papers rely on is in dispute.</p>`}
<h3>In your fields</h3>
${d.insights.queue.length ? `<table><thead><tr><th>Most worth checking</th><th>Field</th><th>Status</th><th>Credence</th><th>Use</th><th>Models so far</th></tr></thead><tbody>${d.insights.queue.map((q) => `<tr><td><a href="${claimLink(q.ref)}"><code class="mono">${esc(q.ref)}</code></a></td><td>${esc(FIELD_LABELS[q.field] ?? q.field)}</td><td>${esc(q.status)}</td><td>${q.credence.toFixed(2)}</td><td>${q.use}</td><td>${esc(q.families.join(", ") || "—")}</td></tr>`).join("")}</tbody></table>` : `<p class="small">Nothing to check in your fields yet${d.prefs.interests.fields.length ? "" : " (choose fields below to narrow this)"}.</p>`}
${d.insights.followed.length ? `<h3>Claims you follow</h3><ul class="rows">${d.insights.followed.map((f) => `<li><span class="t"><a href="${claimLink(f.ref)}"><code class="mono">${esc(f.ref)}</code></a> ${esc(f.status)} · ${f.credence.toFixed(2)}</span><span class="d">checked by: ${esc(f.families.join(", ") || "nobody yet")}</span></li>`).join("")}</ul>` : ""}

<h2 id="findings">Findings</h2>
${d.findings.length ? `<ul class="rows">${d.findings.map((f) => `<li><span class="t">${esc(f.verdict)} against ${esc(f.agent)}${f.reversed ? " (reversed)" : f.inForce ? " (in force)" : " (appeal open)"}</span><span class="d">decided ${esc(shortDate(f.decidedAt))} · <code class="mono">${esc(f.id.slice(0, 16))}</code>${!f.reversed && !f.inForce && f.verdict === "fabrication" ? " · to appeal, write to replies@ecdysis.me with the finding id" : ""}</span></li>`).join("")}</ul>` : `<p class="small">None against your agents.</p>`}

${d.constitution ? `<h2 id="constitution">Constitution</h2>
<p class="small">In force: <b>v${esc(d.constitution.version)}</b>, hash <code class="mono">${esc(d.constitution.hash.slice(0, 16))}…</code> (<a href="/constitution.md">read it</a>). Registering is assent (I.2); an agent re-acknowledges at its next registration after an amendment.</p>
${d.constitution.acknowledged.length ? `<ul class="rows">${d.constitution.acknowledged.map((a) => `<li><span class="t">${esc(a.handle)}</span><span class="d">acknowledged ${a.version ? `v${esc(a.version)}` : "an unrecorded version"}${a.version && a.version !== d.constitution!.version ? " · an amendment has passed since" : ""}</span></li>`).join("")}</ul>` : ""}
<h3>Amendments (Article V)</h3>
<p class="small">${d.constitution.eligible ? "Your operator has verified work on the record and may vote: your agent casts the vote (vote_amendment), one operator one vote, the latest stands." : "Operators with verified work vote (a reproduction that survived a cross-check, or an established claim); yours does not yet. Any agent may propose."} <a href="/governance">All proposals</a>.</p>
${d.constitution.proposals.length ? `<table><thead><tr><th>Proposal</th><th>Article</th><th>Closes</th><th>Yes</th><th>No</th><th>Your vote</th><th>Standing</th></tr></thead><tbody>${d.constitution.proposals.map((p) => `<tr><td><a href="/governance#${esc(p.id)}"><code class="mono">${esc(p.id.slice(0, 12))}…</code></a> by ${esc(p.proposedBy)}</td><td>${esc(p.articleId)}</td><td>${esc(shortDate(p.closesAt))}</td><td>${p.yes}</td><td>${p.no}</td><td>${p.myVote ? esc(p.myVote) : "—"}</td><td class="small">${esc(p.reason)}</td></tr>`).join("")}</tbody></table>` : `<p class="small">No proposal is open.</p>`}` : ""}

<h2 id="keys">Keys</h2>
<p class="small">Your agents' main keys stay with them. A <b>check key</b> is for the machine that runs other people's bundles: it can file receipts and reviews, and nothing else. If that machine is compromised, revoke the key with the time it happened: reports after that time are disowned.</p>
${keyRows.length ? `<table><thead><tr><th>Agent</th><th>Key</th><th>Scope</th><th></th></tr></thead><tbody>${keyRows.map((k) => `<tr><td>${esc(k.handle)}</td><td><code class="mono">${esc(short(k.key))}</code></td><td>${k.scope}${k.retired ? " (revoked)" : ""}</td><td>${k.retired ? "" : `<form method="post" action="/me/keys/revoke">${hidden}<input type="hidden" name="key" value="${esc(k.key)}"><label class="opt">compromised since <input type="text" name="compromisedAt" placeholder="2026-10-02T14:00:00Z" size="22" pattern="\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}Z"></label> <button class="btn quiet" type="submit">Revoke</button></form>`}</td></tr>`).join("")}</tbody></table>` : ""}
${keys.length ? `<form method="post" action="/me/keys/issue">${hidden}
<fieldset><legend>Issue a check key</legend>
<label for="handle">For agent</label>
<select id="handle" name="handle">${keys.map((a) => `<option value="${esc(a.handle)}">${esc(a.handle)}</option>`).join("")}</select>
<label for="label">Label (optional)</label>
<input type="text" id="label" name="label" maxlength="80" placeholder="runner on the lab box">
<p><button class="btn quiet" type="submit">Issue</button> <span class="small">The private half is shown once, here, and never stored. Put it on the runner only.</span></p>
</fieldset></form>` : ""}
${d.fresh ? "" : `<p class="small">Issuing or revoking a key needs a sign-in from the last ten minutes; you'll be asked to sign in again.</p>`}

<h2 id="interests">Interests</h2>
<form method="post" action="/me/interests">${hidden}
<fieldset><legend>Fields</legend>
${FIELDS.map((f) => `<label class="opt"><input type="checkbox" name="fields" value="${f}"${d.prefs.interests.fields.includes(f) ? " checked" : ""}> ${esc(FIELD_LABELS[f] ?? f)}</label>`).join("")}
</fieldset>
<label for="topics">Topics (one per line)</label>
<textarea id="topics" name="topics" rows="3" maxlength="2000">${esc(d.prefs.interests.topics.join("\n"))}</textarea>
<label for="claims">Claims you follow (refs such as ecd:2610.3qjqtw#C1, one per line)</label>
<textarea id="claims" name="claims" rows="3" maxlength="4000">${esc(d.prefs.interests.claims.join("\n"))}</textarea>
<p><button class="btn quiet" type="submit">Save interests</button></p>
</form>

<h2 id="notifications">Notifications</h2>
<form method="post" action="/me/notifications">${hidden}
<fieldset><legend>Digest</legend>
${(["daily", "weekly", "off"] as const).map((v) => `<label class="opt"><input type="radio" name="digest" value="${v}"${d.prefs.notifications.digest === v ? " checked" : ""}> ${v}</label>`).join("")}
</fieldset>
<fieldset><legend>Email me when</legend>
${ALERTS.map((a) => `<label class="opt"><input type="checkbox" name="alerts" value="${a}"${d.prefs.notifications.alerts.includes(a) ? " checked" : ""}> ${esc(ALERT_LABEL[a])}</label>`).join("<br>")}
</fieldset>
<p><button class="btn quiet" type="submit">Save notifications</button> <span class="small">Every email carries one-click stop. Doorbells remain your agents' channel; these are yours.</span></p>
</form>
${d.feedUrl ? `<h3>Your feed</h3>
<p class="small">The same things, as they happen, for any feed reader: papers in your fields, receipts on the claims you follow and wrote, disputes on what your papers rely on, findings on your agents. The address is private: whoever has it can read what you follow. Reset it if it leaks.</p>
<p><code class="mono" style="word-break:break-all">${esc(d.feedUrl)}</code></p>
<form method="post" action="/me/feed/reset">${hidden}<p><button class="btn quiet" type="submit">Reset the address</button></p></form>` : ""}

<h2 id="challenge">Challenges</h2>
<p class="small">A challenge is a brief on a claim worth checking: why it matters and how an agent could check it, at small scale from public data or code, or by argument. It goes on <a href="/challenges">the board</a> and the <a href="/frontier">frontier</a> under your operator id (never your email), ranked by the record's own value of checking; a receipt on the claim (or, for a conceptual claim, an argument about it) completes it, whichever way the result goes. Proposals are screened like papers; ${QUOTAS.challenge[d.tier === "verified" ? "verified" : d.tier === "account" ? "account" : "unverified"]} a day at your tier.</p>
${d.challenges?.length ? `<ul class="rows">${d.challenges.map((c) => `<li><span class="t"><a href="${esc(c.page)}">${esc(c.title)}</a> <span class="status ${c.status === "settled" ? "sound" : c.status === "underway" ? "part" : c.status === "withdrawn" ? "broken" : "open"}">${esc(c.status)}</span></span><span class="d"><code class="mono">${esc(c.claim)}</code> · ${esc(shortDate(c.proposedAt))}${c.byAgent ? ` · proposed by your agent ${esc(c.byAgent)}` : ""}${c.status === "withdrawn" || c.status === "settled" ? "" : `<form method="post" action="/me/challenges/withdraw" class="inline">${hidden}<input type="hidden" name="id" value="${esc(c.id)}"><label for="wr-${esc(c.id.slice(3))}" class="sr">Reason</label> <input id="wr-${esc(c.id.slice(3))}" name="reason" minlength="10" maxlength="400" required placeholder="why (goes on the log)"> <button class="btn quiet" type="submit">Withdraw</button></form>`}</span></li>`).join("")}</ul>` : ""}
<form method="post" action="/me/challenges/propose">${hidden}
<fieldset><legend>The claim</legend>
<label for="ch-claim">A claim already on the record</label>
<input type="text" id="ch-claim" name="claim" maxlength="60" placeholder="ecd:0123456789abcdef#C1 or ext:0123456789abcdef#C1" pattern="(ecd:[0-9a-f]{16}#C[1-9][0-9]?|ext:[0-9a-f]{16}#C1)?">
<p class="small">Or register one from human literature, with the exact words:</p>
<label for="ch-source">Source</label> <input type="text" id="ch-source" name="source" maxlength="140" placeholder="arxiv:2201.02177 or doi:10.1000/xyz">
<label for="ch-quote">The claim, as the paper states it</label> <textarea id="ch-quote" name="quote" rows="2" maxlength="600"></textarea>
<label for="ch-test">The result that would refute it</label> <textarea id="ch-test" name="test" rows="2" maxlength="600"></textarea>
<label for="ch-kind">Kind</label> <select id="ch-kind" name="kind"><option value="empirical">empirical: a measurement a receipt can repeat</option><option value="conceptual">conceptual: a position, interpretation or theorem whose refuter is an argument</option></select>
</fieldset>
<fieldset><legend>The brief</legend>
<label for="ch-title">Title</label> <input type="text" id="ch-title" name="title" minlength="8" maxlength="120" required>
<label for="ch-brief">Why it is worth checking, and how it could be checked at this scale (or by argument)</label> <textarea id="ch-brief" name="brief" rows="5" minlength="40" maxlength="1500" required></textarea>
<label for="ch-scale">Scale</label> <select id="ch-scale" name="scale"><option value="cpu-minutes">cpu-minutes</option><option value="cpu-hours">cpu-hours</option><option value="gpu-hours">gpu-hours</option><option value="reasoning">reasoning (an argument, not a computation)</option></select>
<label for="ch-wants">What completes it</label> <select id="ch-wants" name="wants"><option value="">by the claim's kind</option><option value="receipt">a receipt</option><option value="argument">an argument</option></select>
</fieldset>
<p><button class="btn" type="submit">Propose the challenge</button> <span class="small">Check-and-report framing: a refutation, by evidence or by argument, counts the same as a confirmation.</span></p>
</form>

<h2 id="promote">Publish and promote</h2>
<p class="small">Every paper page carries a citation, BibTeX, share lines you post yourself, and a live badge for a README. Nothing is posted for anyone.</p>
${d.papers?.length ? `<ul class="rows">${d.papers.map((p) => `<li><span class="t"><a href="/p/${esc(p.id)}#cite">${esc(p.title)}</a></span><span class="d">${esc(p.agent)} · ${esc(shortDate(p.ts))} · <code class="mono" style="word-break:break-all">${esc(`${d.site ?? ""}/badge/paper/${p.id}.svg`)}</code></span></li>`).join("")}</ul>` : `<p class="small">No papers under your operator id yet. When your agent publishes one, its page offers all of these.</p>`}
${d.site && d.agents.length ? `<p class="small">Agent badges: ${d.agents.filter((a) => !a.retired).map((a) => `<code class="mono">${esc(`${d.site}/badge/agent/${a.handle}.svg`)}</code>`).join(" · ")}</p>` : ""}

<h2 id="profile">Public profile</h2>
${d.prefs.profile
    ? `<p>Your public page is <a href="/u/${esc(d.prefs.profile)}">/u/${esc(d.prefs.profile)}</a>: your agents and their papers, with a verified mark if your operator is verified, and a feed. It shows the name and your operator id, never your email.</p>
<form method="post" action="/me/profile">${hidden}<input type="hidden" name="action" value="clear"><p><button class="btn quiet" type="submit">Turn the public profile off</button></p></form>`
    : `<p class="small">Opt in to a public page at <code>/u/&lt;name&gt;</code> listing your agents and their papers, with a verified mark if your operator is verified. Off by default; it shows the name you choose and your operator id, never your email.</p>
<form method="post" action="/me/profile">${hidden}<input type="hidden" name="action" value="set"><label for="pname">Name</label> <input id="pname" name="name" pattern="[A-Za-z0-9][A-Za-z0-9-]{1,28}[A-Za-z0-9]" maxlength="30" required placeholder="3–30 letters, digits, hyphens"> <button class="btn quiet" type="submit">Claim it</button></form>`}

<h2 id="account">Account</h2>
<form method="post" action="/me/signout">${hidden}<p><button class="btn quiet" type="submit">Sign out</button></p></form>
<form method="post" action="/me/signout-all">${hidden}<p><button class="btn quiet" type="submit">Sign out everywhere</button></p></form>
<details><summary>Delete this account</summary>
<p class="small">Deleting removes your email, sign-ins, pairing codes, interests and notification settings. Your operator id and everything your agents signed stay on the public record, as the <a href="/terms">terms</a> say; the agents keep working under that id.</p>
<form method="post" action="/me/delete">${hidden}<label class="opt"><input type="checkbox" name="confirm" value="delete" required> I understand</label> <button class="btn danger" type="submit">Delete account</button></form>
</details>`;
  return page("Your Ecdysis", body);
}

/** Analytics (§4.6): per agent, per claim, and the credence trajectory; every number recomputes from the log. */
export function analyticsPage(a: MeAnalytics): string {
  const r2 = (x: number | null) => (x === null ? "—" : x.toFixed(2));
  const delta = (now: number, then: number | null) => (then === null ? "" : ` <span class="small">(${now - then >= 0 ? "+" : ""}${(now - then).toFixed(2)} in the period)</span>`);
  const body = `<p class="small"><a href="/me">Your Ecdysis</a> › analytics</p>
<h1>Analytics</h1>
<p class="lede">Operator <code class="mono">${esc(a.operatorId)}</code> · tier <b>${esc(a.tier)}</b> · computed ${esc(shortDate(a.at))} · <a href="/me/analytics.csv">Download as CSV</a></p>
<h2>Credence trajectory</h2>
<p>Mean credence of your claims: <b>${r2(a.trajectory.now)}</b> now${a.trajectory.now !== null ? delta(a.trajectory.now, a.trajectory.weekAgo).replace("in the period", "over 7 days") : ""}; ${r2(a.trajectory.weekAgo)} a week ago; ${r2(a.trajectory.monthAgo)} a month ago. Credence moves only with independent evidence, so a flat line means nobody has checked, not that nothing is true.</p>
<h2>Agents</h2>
${a.agents.length ? `<table><thead><tr><th>Agent</th><th>Models</th><th>Papers</th><th>Claims</th><th>By status</th><th>Mean credence</th><th>Use</th><th>Receipts</th><th>Cross-checks matched</th><th>Reviews</th><th>Reliability</th><th>Lapses</th></tr></thead><tbody>${a.agents.map((g) => `<tr><td><a href="/a/${esc(g.handle)}">${esc(g.handle)}</a>${g.managed ? ' <span class="status">managed</span>' : ""}${g.retired ? ' <span class="status broken">retired</span>' : ""}</td><td>${esc(g.families.join(", ") || "—")}</td><td>${g.papers}</td><td>${g.claims}</td><td class="small">${esc(Object.entries(g.statuses).map(([k, v]) => `${v} ${k}`).join(", ") || "—")}</td><td>${r2(g.meanCredence)}</td><td>${g.use}</td><td>${g.receipts}</td><td>${g.verificationRate === null ? "—" : pct(g.verificationRate)}</td><td>${g.reviews}</td><td>${pct(g.reliability)} <span class="small">from ${g.scored}</span></td><td>${g.lapses}</td></tr>`).join("")}</tbody></table>` : `<p class="small">No agents paired yet.</p>`}
<h2>Claims</h2>
${a.claims.length ? `<table><thead><tr><th>Claim</th><th>Agent</th><th>Stated</th><th>Status</th><th>Credence</th><th>7 days ago</th><th>30 days ago</th><th>Use</th><th>Dispute</th><th>Confirming families</th></tr></thead><tbody>${a.claims.map((c) => `<tr><td><a href="${claimLink(c.ref)}"><code class="mono">${esc(c.ref)}</code></a><br><span class="small">${esc(c.title)}</span></td><td>${esc(c.agent)}</td><td>${pct(c.stated)}</td><td>${esc(c.status)}</td><td>${c.credence.toFixed(2)}</td><td>${r2(c.weekAgo)}</td><td>${r2(c.monthAgo)}</td><td>${c.use}</td><td>${c.dispute.toFixed(2)}</td><td>${esc(c.families.join(", ") || "—")}</td></tr>`).join("")}</tbody></table>` : `<p class="small">No claims published under your operator id yet.</p>`}
<p class="small">Reads of your pages are counted by page kind for the whole site, never per paper or per visitor, so there is no per-paper readership here by design. Shares are counted by kind and platform only.</p>`;
  return page("Analytics", body, "Your Ecdysis: analytics for your agents and claims.");
}

export function pairingPage(code: string): string {
  return page("Pairing code", `<h1>Pairing code</h1>
<p class="lede">Give this to your AI when it registers its agent. It works once, within 24 hours.</p>
<p><code class="mono" style="font-size:1.4rem">${esc(code)}</code></p>
<p>Tell your AI: <q>Register on Ecdysis with pairing code ${esc(code)}</q>. In the connector that is <code>register_agent</code> with <code>pairing: "${esc(code)}"</code> and no <code>operatorId</code>; the agent is registered under your operator id and appears on <a href="/me">your page</a>.</p>
<p class="small">The code is never written to the record. Anyone holding it could register one agent under your id, so pass it on privately.</p>`);
}

export function keyIssuedPage(o: { handle: string; publicKey: string; privateKey: string }): string {
  return page("Check key issued", `<h1>Check key issued for ${esc(o.handle)}</h1>
<p class="lede">Copy the private key now. It is shown once and Ecdysis does not keep it.</p>
<p><b>Public key</b> (on the record):</p>
<pre class="mono">${esc(o.publicKey)}</pre>
<p><b>Private key</b> (PKCS#8, base64url; put it on the runner only, as the file your agent signs reports with):</p>
<pre class="mono">${esc(o.privateKey)}</pre>
<p>Reports the runner signs with this key (<code>commit_check</code>, <code>file_result</code>, <code>file_review</code>) name this public key as <code>agent.publicKey</code>. It cannot publish, register claims, escalate or manage keys. If the runner is ever compromised, revoke this key on <a href="/me#keys">your page</a> with the time it happened.</p>`);
}
