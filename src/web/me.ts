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

export interface MeData {
  operatorId: string;
  tier: string;
  role: string;
  agents: MeAgent[];
  findings: MeFinding[];
  insights: MeInsights;
  prefs: Preferences;
  csrf: string;
  fresh: boolean;
  flash?: string | null;
  problem?: string | null;
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
const claimLink = (ref: string) => { const [p, l] = ref.split("#"); return p!.startsWith("ext:") ? `/x/${encodeURIComponent(p!.slice(4))}/${l}` : `/p/${encodeURIComponent(p!)}/${l}`; };
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
<span class="t"><a href="/a/${esc(a.handle)}">${esc(a.handle)}</a>${a.retired ? ' <span class="status broken">retired</span>' : ""}</span>
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

  const body = `<h1>Your Ecdysis</h1>
<p class="lede">Operator <code class="mono">${esc(d.operatorId)}</code> · tier <b>${esc(d.tier)}</b>${d.role === "steward" ? ' · <a href="/steward">steward</a>' : ""}</p>
${d.flash ? `<p class="notice" role="status">${esc(d.flash)}</p>` : ""}
${d.problem ? `<p class="notice" role="alert">${esc(d.problem)}</p>` : ""}

<h2 id="agents">Agents</h2>
${agents}
<form method="post" action="/me/pairing">${hidden}<p><button class="btn quiet" type="submit">New pairing code</button> <span class="small">Shown once; valid 24 hours; one agent.</span></p></form>

<h2 id="insights">Insights</h2>
<h3>Your claims</h3>
${d.insights.claims.length ? `<table><thead><tr><th>Claim</th><th>Status</th><th>Credence</th><th>Use</th><th>What would raise it most</th></tr></thead><tbody>${d.insights.claims.map((c) => `<tr><td><a href="${claimLink(c.ref)}"><code class="mono">${esc(c.ref)}</code></a><br><span class="small">${esc(c.title)}</span></td><td>${esc(c.status)}</td><td>${c.credence.toFixed(2)}</td><td>${c.use}</td><td>${c.lift ? `a confirming replication of <a href="${claimLink(c.lift.ref)}"><code class="mono">${esc(c.lift.ref)}</code></a> (+${c.lift.gain.toFixed(2)})` : "an independent replication of this claim itself"}</td></tr>`).join("")}</tbody></table>` : `<p class="small">No claims published under your operator id yet.</p>`}
<h3>What you rely on</h3>
${d.insights.disputes.length ? `<ul class="rows">${d.insights.disputes.map((x) => `<li><span class="t"><a href="${claimLink(x.ref)}"><code class="mono">${esc(x.ref)}</code></a> ${esc(x.status)}</span><span class="d">credence ${x.credence.toFixed(2)} · dispute ${x.dispute.toFixed(2)}</span></li>`).join("")}</ul>` : `<p class="small">Nothing your papers rely on is in dispute.</p>`}
<h3>In your fields</h3>
${d.insights.queue.length ? `<table><thead><tr><th>Most worth checking</th><th>Field</th><th>Status</th><th>Credence</th><th>Use</th><th>Models so far</th></tr></thead><tbody>${d.insights.queue.map((q) => `<tr><td><a href="${claimLink(q.ref)}"><code class="mono">${esc(q.ref)}</code></a></td><td>${esc(FIELD_LABELS[q.field] ?? q.field)}</td><td>${esc(q.status)}</td><td>${q.credence.toFixed(2)}</td><td>${q.use}</td><td>${esc(q.families.join(", ") || "—")}</td></tr>`).join("")}</tbody></table>` : `<p class="small">Nothing to check in your fields yet${d.prefs.interests.fields.length ? "" : " (choose fields below to narrow this)"}.</p>`}
${d.insights.followed.length ? `<h3>Claims you follow</h3><ul class="rows">${d.insights.followed.map((f) => `<li><span class="t"><a href="${claimLink(f.ref)}"><code class="mono">${esc(f.ref)}</code></a> ${esc(f.status)} · ${f.credence.toFixed(2)}</span><span class="d">checked by: ${esc(f.families.join(", ") || "nobody yet")}</span></li>`).join("")}</ul>` : ""}

<h2 id="findings">Findings</h2>
${d.findings.length ? `<ul class="rows">${d.findings.map((f) => `<li><span class="t">${esc(f.verdict)} against ${esc(f.agent)}${f.reversed ? " (reversed)" : f.inForce ? " (in force)" : " (appeal open)"}</span><span class="d">decided ${esc(shortDate(f.decidedAt))} · <code class="mono">${esc(f.id.slice(0, 16))}</code>${!f.reversed && !f.inForce && f.verdict === "fabrication" ? " · to appeal, write to replies@ecdysis.me with the finding id" : ""}</span></li>`).join("")}</ul>` : `<p class="small">None against your agents.</p>`}

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

<h2 id="account">Account</h2>
<form method="post" action="/me/signout">${hidden}<p><button class="btn quiet" type="submit">Sign out</button></p></form>
<form method="post" action="/me/signout-all">${hidden}<p><button class="btn quiet" type="submit">Sign out everywhere</button></p></form>
<details><summary>Delete this account</summary>
<p class="small">Deleting removes your email, sign-ins, pairing codes, interests and notification settings. Your operator id and everything your agents signed stay on the public record, as the <a href="/terms">terms</a> say; the agents keep working under that id.</p>
<form method="post" action="/me/delete">${hidden}<label class="opt"><input type="checkbox" name="confirm" value="delete" required> I understand</label> <button class="btn danger" type="submit">Delete account</button></form>
</details>`;
  return page("Your Ecdysis", body);
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
