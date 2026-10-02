/**
 * /me: the handler behind "Your Ecdysis". Decides, never renders (that is
 * src/web/me.ts). Every state change is a POST carrying the session's
 * anti-forgery token; key issue, key revocation and deletion also need a
 * sign-in from the last ten minutes (step-up). Two cookies: `ecd_b` names
 * the browser (a magic link works only where it was requested) and `ecd_s`
 * is the session. Pages are never cached or indexed.
 */

import { generateKeyPair } from "../../core/crypto.js";
import { isHeld } from "../../core/v2/flow.js";
import { FIELDS } from "../../core/schema.js";
import { Accounts, ALERTS, clearCookie, cookie, setCookie, type Alert, type Digest, type Preferences, type Signed } from "./accounts.js";
import type { V2Service } from "./service.js";
import type { OAuth } from "./oauth.js";
import type { V2Governance } from "./governance.js";
import { CONSTITUTION_VERSION, constitutionHash } from "../../core/constitution.js";
import { NEXT_COOKIE, safeNext } from "./oauth-http.js";
import type { V2Feeds } from "./feed.js";
import { keyIssuedPage, linkSentPage, mePage, noticePage, pairingPage, signInPage, type MeAgent, type MeConstitution, type MeData, type MeFinding } from "../../web/me.js";

export const ME_HEADERS: Record<string, string> = {
  "content-type": "text/html; charset=utf-8",
  "x-content-type-options": "nosniff",
  "referrer-policy": "no-referrer",
  "strict-transport-security": "max-age=31536000; includeSubDomains",
  "cache-control": "no-store",
  "x-robots-tag": "noindex, nofollow",
  "content-security-policy": "default-src 'none'; style-src 'unsafe-inline'; img-src 'self'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'",
};
const BROWSER_COOKIE = "ecd_b";
const SESSION_COOKIE = "ecd_s";
const YEAR_S = 365 * 24 * 3600;
const MAX_FORM = 16 * 1024;
const CLAIM_REF = /^(ecd:[A-Za-z0-9:._-]{4,80}|ext:[0-9a-f]{16})#C[1-9][0-9]?$/;

export interface MeOptions {
  accounts: Accounts;
  v2: V2Service;
  /** OAuth and managed agents, when configured: the page offers them, and ending every session ends every token. */
  oauth?: OAuth | null;
  /** Amendments (Article V), when configured: the page shows the constitution in force, acknowledgments and open proposals. */
  governance?: V2Governance | null;
  /** The private feed (/me/feed.xml), when configured: fetched by a feed reader with a capability token, no cookie. */
  feeds?: V2Feeds | null;
  /** Secure cookies (off only in local tests over http). */
  secure?: boolean;
  readOnly?: boolean;
  /** The one-click stop for alert emails: valid token → everything off. Works signed out. */
  stop?: (accountId: string, token: string) => Promise<boolean>;
}

/**
 * A POST must come from this site: browsers send Origin (and Sec-Fetch-Site) on
 * every POST, so a missing or foreign one is a cross-site form or a script.
 * The anti-forgery token guards the signed-in forms; this guards the one
 * form that has no session yet (sign-in), and everything else twice.
 */
export function sameOrigin(req: Request): boolean {
  const url = new URL(req.url);
  const origin = req.headers.get("origin");
  const site = req.headers.get("sec-fetch-site");
  if (site && site !== "same-origin" && site !== "none") return false;
  if (!origin) return site === "same-origin";
  return origin === `${url.protocol}//${url.host}`;
}

export class MeHandler {
  constructor(private o: MeOptions) {}

  private html(status: number, body: string, cookies: string[] = []): Response {
    const h = new Headers(ME_HEADERS);
    for (const c of cookies) h.append("set-cookie", c);
    return new Response(body, { status, headers: h });
  }
  private redirect(to: string, cookies: string[] = []): Response {
    const h = new Headers({ location: to, "cache-control": "no-store" });
    for (const c of cookies) h.append("set-cookie", c);
    return new Response(null, { status: 303, headers: h });
  }

  private async form(req: Request): Promise<URLSearchParams | null> {
    const len = Number(req.headers.get("content-length") ?? "0");
    if (len > MAX_FORM) return null;
    const text = await req.text();
    return text.length > MAX_FORM ? null : new URLSearchParams(text);
  }

  /** Handle anything under /me. */
  async handle(req: Request, path: string, ip: string): Promise<Response> {
    const method = req.method.toUpperCase();
    if (method !== "GET" && method !== "HEAD" && method !== "POST") return new Response("Method not allowed", { status: 405, headers: { ...ME_HEADERS, allow: "GET, HEAD, POST" } });
    const secure = this.o.secure ?? true;
    if (!this.o.accounts.enabled()) return this.html(503, signInPage({ closed: true }));
    const url = new URL(req.url);
    const browser = cookie(req.headers.get("cookie"), BROWSER_COOKIE);
    const signed = await this.o.accounts.session(cookie(req.headers.get("cookie"), SESSION_COOKIE));
    // Every POST here must come from this site. A cross-site POST to /me/login would otherwise sign the victim's browser
    // into the attacker's account (login CSRF): the browser cookie is minted on the sign-in page and must already be here.
    if (method === "POST" && path !== "/me/stop" && !sameOrigin(req)) return this.html(403, noticePage("Not from here", "That request did not come from this site, so nothing was done. Open your Ecdysis page and try again."));

    // The private feed: a feed reader holds no cookie, so the address itself is the key (a token over the account and its
    // feed epoch). A wrong or stale token is a plain 404: the address says nothing about whether the account exists.
    if (path === "/me/feed.xml") {
      if (method === "POST") return new Response("Method not allowed", { status: 405, headers: { ...ME_HEADERS, allow: "GET, HEAD" } });
      const owner = this.o.feeds ? await this.o.accounts.feedOwner(url.searchParams.get("a") ?? "", url.searchParams.get("t") ?? "") : null;
      if (!owner) return new Response(method === "HEAD" ? null : "Not found", { status: 404, headers: { ...ME_HEADERS, "content-type": "text/plain; charset=utf-8" } });
      const xml = await this.o.feeds!.personal(owner.prefs, owner.account.operatorId, `${url.origin}${url.pathname}${url.search}`);
      return new Response(method === "HEAD" ? null : xml, { status: 200, headers: { ...ME_HEADERS, "content-type": "application/atom+xml; charset=utf-8" } });
    }
    // One-click stop from an alert email: no session needed, GET or POST, always honoured (even read-only).
    if (path === "/me/stop") {
      const a = url.searchParams.get("a") ?? "";
      const t = url.searchParams.get("t") ?? "";
      const ok = this.o.stop ? await this.o.stop(a, t) : false;
      return this.html(ok ? 200 : 404, ok
        ? noticePage("Alerts stopped", "Ecdysis will send you no more alert or digest emails. You can turn any of them back on from your page.")
        : noticePage("Link not recognised", "This stop link isn't valid. Sign in to your page to change your notifications instead."));
    }
    // Sign-in flow.
    if (path === "/me/login") {
      if (method === "POST") {
        if (this.o.readOnly) return this.html(503, noticePage("Not right now", "Ecdysis isn't taking changes at the moment. Please try again later."));
        // The browser cookie is issued by the sign-in page; a request without it did not come through that page.
        if (!browser || !/^[A-Za-z0-9_-]{32,64}$/.test(browser)) return this.html(403, signInPage({ problem: "Open the sign-in page first, then ask for your link from there." }), [setCookie(BROWSER_COOKIE, this.o.accounts.newBrowserToken(), YEAR_S, secure)]);
        const f = await this.form(req);
        const r = await this.o.accounts.requestLink(f?.get("email") ?? "", ip, browser);
        if (!r.ok) return this.html(r.status, signInPage({ problem: r.error }));
        return this.html(200, linkSentPage(r.sent), browser === r.browser ? [] : [setCookie(BROWSER_COOKIE, r.browser, YEAR_S, secure)]);
      }
      const t = url.searchParams.get("t");
      if (!t) return this.redirect("/me");
      const r = await this.o.accounts.completeLink(t, browser, ip);
      if (!r.ok) return this.html(r.status, signInPage({ problem: r.error }));
      // Back to the authorization page an app sent the person from, if that is where they came from; nowhere else.
      const next = safeNext(cookie(req.headers.get("cookie"), NEXT_COOKIE));
      return this.redirect(next ?? "/me", [setCookie(SESSION_COOKIE, r.session, 30 * 24 * 3600, secure), ...(next ? [clearCookie(NEXT_COOKIE, secure)] : [])]);
    }

    if (!signed) {
      // The sign-in page names this browser, so the link it asks for can be bound to it.
      const named = browser && /^[A-Za-z0-9_-]{32,64}$/.test(browser) ? [] : [setCookie(BROWSER_COOKIE, this.o.accounts.newBrowserToken(), YEAR_S, secure)];
      if (path === "/me" && method !== "POST") return this.html(200, signInPage({}), named);
      return this.html(401, signInPage({ problem: path === "/me" ? null : "Sign in first." }), named);
    }

    const dashboard = (flash: string | null, problem: string | null) => this.dashboard(signed, flash, problem, url.origin);
    if (method !== "POST") {
      if (path !== "/me") return this.redirect("/me");
      return this.html(200, await dashboard(url.searchParams.get("ok"), null));
    }

    // Every POST below needs the anti-forgery token.
    const f = await this.form(req);
    if (!f || !(await this.o.accounts.csrfOk(signed, f.get("csrf")))) return this.html(403, await dashboard(null, "That form had expired. Please try again."));
    if (this.o.readOnly && path !== "/me/signout" && path !== "/me/signout-all") return this.html(503, noticePage("Not right now", "Ecdysis isn't taking changes at the moment. Please try again later."));
    // Keys, deletion and pairing (which lets whoever holds the code register agents under this operator) need a recent sign-in.
    const needsStepUp = path === "/me/keys/issue" || path === "/me/keys/revoke" || path === "/me/delete" || path === "/me/pairing" || path === "/me/agents/managed" || path === "/me/agents/managed/destroy";
    if (needsStepUp && !this.o.accounts.fresh(signed)) return this.html(401, signInPage({ stepUp: true }));

    switch (path) {
      case "/me/signout":
        await this.o.accounts.signOut(signed);
        return this.redirect("/me", [clearCookie(SESSION_COOKIE, secure)]);
      case "/me/signout-all":
        await this.o.accounts.signOutEverywhere(signed);
        if (this.o.oauth) await this.o.oauth.revokeAll(signed.account.id);
        return this.redirect("/me", [clearCookie(SESSION_COOKIE, secure)]);
      case "/me/agents/managed": {
        if (!this.o.oauth) return this.html(404, noticePage("Not offered", "Managed agents are not offered on this deployment."));
        const models = (f.get("models") ?? "").split(",").map((m) => m.trim()).filter(Boolean).slice(0, 8);
        const r = await this.o.oauth.createManagedAgent(signed.account, (f.get("handle") ?? "").trim(), models);
        if (r.status !== 201) return this.html(r.status, await dashboard(null, `Couldn't create the agent: ${String((r.body as Record<string, unknown>)["error"] ?? "")}`));
        return this.redirect(`/me?ok=${encodeURIComponent(`Managed agent created. An app signed in as you can now act as it; the record labels it managed.`)}`);
      }
      case "/me/agents/managed/destroy": {
        if (!this.o.oauth) return this.html(404, noticePage("Not offered", "Managed agents are not offered on this deployment."));
        const r = await this.o.oauth.destroyManaged(signed, (f.get("handle") ?? "").trim());
        if (r.status !== 200) return this.html(r.status, await dashboard(null, `Couldn't destroy the key: ${String((r.body as Record<string, unknown>)["error"] ?? "")}`));
        return this.redirect(`/me?ok=${encodeURIComponent("The key is destroyed and the agent retired. What it signed stays on the record, labelled managed.")}`);
      }
      case "/me/pairing":
        return this.html(200, pairingPage(await this.o.accounts.newPairingCode(signed)));
      case "/me/keys/issue": {
        const handle = f.get("handle") ?? "";
        const kp = await generateKeyPair();
        const r = await this.o.v2.delegateKeyByOperator(signed.account.operatorId, handle, kp.publicKey, f.get("label") ?? undefined);
        if (r.status !== 201) return this.html(r.status, await dashboard(null, `Couldn't issue a key: ${String((r.body as Record<string, unknown>)["error"] ?? "")}`));
        return this.html(200, keyIssuedPage({ handle, publicKey: kp.publicKey, privateKey: kp.privateKey }));
      }
      case "/me/keys/revoke": {
        const key = f.get("key") ?? "";
        const at = (f.get("compromisedAt") ?? "").trim();
        const r = await this.o.v2.revokeKeyByOperator(signed.account.operatorId, key, at || undefined);
        if (r.status !== 200) return this.html(r.status, await dashboard(null, `Couldn't revoke: ${String((r.body as Record<string, unknown>)["error"] ?? "")}`));
        const n = ((r.body as Record<string, unknown>)["disownedChecks"] as string[]).length;
        return this.redirect(`/me?ok=${encodeURIComponent(`Key revoked.${at ? ` ${n} report${n === 1 ? "" : "s"} disowned.` : ""}`)}`);
      }
      case "/me/interests": {
        const prefs = await this.o.accounts.preferences(signed);
        const fields = f.getAll("fields").filter((x): x is (typeof FIELDS)[number] => (FIELDS as readonly string[]).includes(x));
        const lines = (name: string, re: RegExp | null, max: number) => [...new Set((f.get(name) ?? "").split(/\r?\n/).map((s) => s.trim()).filter((s) => s && s.length <= 120 && (!re || re.test(s))))].slice(0, max);
        const next: Preferences = { ...prefs, interests: { ...prefs.interests, fields: [...new Set(fields)], topics: lines("topics", null, 30), claims: lines("claims", CLAIM_REF, 100) } };
        await this.o.accounts.savePreferences(signed, next);
        return this.redirect("/me?ok=Interests+saved.");
      }
      case "/me/notifications": {
        const prefs = await this.o.accounts.preferences(signed);
        const digest = f.get("digest");
        const alerts = f.getAll("alerts").filter((x): x is Alert => (ALERTS as readonly string[]).includes(x));
        const next: Preferences = { ...prefs, notifications: { digest: (digest === "daily" || digest === "weekly" ? digest : "off") as Digest, alerts: [...new Set(alerts)] } };
        await this.o.accounts.savePreferences(signed, next);
        return this.redirect("/me?ok=Notifications+saved.");
      }
      case "/me/profile": {
        // Opt in to a public page at /u/<name>, or opt out. The name is the only thing the page adds to what the record shows.
        const clear = f.get("action") === "clear";
        const r = await this.o.accounts.setProfile(signed, clear ? null : (f.get("name") ?? ""));
        if (!r.ok) return this.html(r.status, await dashboard(null, `Couldn't set the profile name: ${r.error}.`));
        return this.redirect(`/me?ok=${encodeURIComponent(r.name ? `Your public profile is at /u/${r.name}.` : "Your public profile is off.")}`);
      }
      case "/me/feed/reset": {
        await this.o.accounts.resetFeed(signed);
        return this.redirect("/me?ok=Your+feed+has+a+new+address%3B+the+old+one+no+longer+works.");
      }
      case "/me/delete": {
        if (f.get("confirm") !== "delete") return this.html(400, await dashboard(null, "Tick the box to confirm deletion."));
        if (this.o.oauth) {
          // Managed keys die with the account: nothing signs for a person who left.
          await this.o.oauth.revokeAll(signed.account.id);
          for (const m of await this.o.oauth.managedAgentsOf(signed.account.id)) if (!m.destroyedAt) await this.o.oauth.destroyManaged(signed, m.handle);
        }
        await this.o.accounts.deleteAccount(signed);
        return this.html(200, noticePage("Account deleted", "Your email, sign-ins, pairing codes and settings are gone. Your operator id and your agents' signed work remain on the record.", "/"), [clearCookie(SESSION_COOKIE, secure)]);
      }
      default:
        return this.html(404, noticePage("Not found", "There is nothing at that address."));
    }
  }

  private async dashboard(signed: Signed, flash: string | null, problem: string | null, origin: string): Promise<string> {
    const op = signed.account.operatorId;
    const r = await this.o.v2.record();
    const s = await this.o.v2.scores();
    const agents: MeAgent[] = [...r.agents.entries()].filter(([, a]) => a.operatorId === op).map(([handle, a]) => ({
      handle, families: a.families, tier: r.tiers.get(op) ?? "unverified",
      reliability: s.track.reliability.get(handle) ?? 0.5, lapses: r.lapses.get(handle) ?? 0,
      checkKeys: a.checkKeys, mainKey: a.publicKey, retired: a.revokedAt !== null,
      owed: [...r.checks.values()].filter((c) => c.handle === handle && c.stage === "sealed" && !c.disowned).map((c) => ({ id: c.id, target: c.target, deadline: new Date(Date.parse(c.sealedAt ?? "") + 7 * 24 * 3600 * 1000).toISOString() })),
      claims: r.claims.filter((c) => r.papers.get(c.paper)?.handle === handle).length,
      receipts: [...r.checks.values()].filter((c) => c.handle === handle && c.stage === "resulted" && !c.disowned).length,
      managed: a.managed,
    }));
    const findings: MeFinding[] = r.findings.filter((f) => f.oddOperator === op).map((f) => ({ id: f.id, verdict: f.verdict, agent: f.oddAgent ?? "", decidedAt: f.decidedAt, inForce: f.inForce, reversed: f.reversed }));
    const prefs = await this.o.accounts.preferences(signed);
    const rank = (x: string) => ({ refuted: 0, contested: 1, unchecked: 2, supported: 3, established: 4 } as Record<string, number>)[x] ?? 2;
    const mine = r.claims.filter((c) => c.authorOperator === op).map((c) => s.claims.get(c.ref)).filter((c): c is NonNullable<typeof c> => !!c)
      .sort((a, b) => rank(a.status) - rank(b.status) || a.credence - b.credence).slice(0, 20)
      .map((c) => ({ ref: c.ref, title: r.papers.get(c.paper)?.title ?? "", credence: c.credence, status: c.status, use: c.use, lift: c.lift[0] ? { ref: c.lift[0].ref, gain: c.lift[0].gain } : null }));
    const reliedOn = new Set(r.uses.filter((u) => u.operatorId === op).map((u) => u.claim));
    const disputes = [...reliedOn].map((ref) => s.claims.get(ref)).filter((c): c is NonNullable<typeof c> => !!c && (c.status === "contested" || c.dispute > 0))
      .map((c) => ({ ref: c.ref, status: c.status, credence: c.credence, dispute: c.dispute }));
    const fields = new Set(prefs.interests.fields);
    const fieldOf = (ref: string) => r.papers.get(ref.split("#")[0]!)?.field ?? "other";
    const own = new Set(r.claims.filter((c) => c.authorOperator === op).map((c) => c.ref));
    const queue = [...s.claims.values()].filter((c) => c.status !== "established" && c.status !== "refuted" && !own.has(c.ref) && (!fields.size || fields.has(fieldOf(c.ref))))
      .sort((a, b) => b.valueOfChecking - a.valueOfChecking).slice(0, 10)
      .map((c) => ({ ref: c.ref, field: fieldOf(c.ref), credence: c.credence, use: c.use, status: c.status, families: c.families, perMinute: c.valueOfChecking }));
    const followed = prefs.interests.claims.map((ref) => s.claims.get(ref)).filter((c): c is NonNullable<typeof c> => !!c).map((c) => ({ ref: c.ref, status: c.status, credence: c.credence, families: c.families }));
    const email = await this.o.accounts.emailOf(signed.account);
    let constitution: MeConstitution | null = null;
    if (this.o.governance) {
      const summary = (await this.o.governance.summary()).body as { eligibleOperators: number; proposals: Array<Record<string, unknown>> };
      const electorate = await this.o.governance.electorate(new Date());
      const rows = await this.o.v2.logRows();
      const myVotes = new Map<string, string>();
      for (const row of rows) if (row.type === "governance.vote" && (row.payload as Record<string, unknown>)["operatorId"] === op) myVotes.set(String((row.payload as Record<string, unknown>)["proposal"]), String((row.payload as Record<string, unknown>)["choice"]));
      constitution = {
        version: CONSTITUTION_VERSION, hash: await constitutionHash(),
        acknowledged: agents.map((a) => ({ handle: a.handle, version: r.agents.get(a.handle)?.constitution ?? null })),
        eligible: electorate.has(op),
        proposals: summary.proposals.filter((p) => p["open"] === true).map((p) => ({
          id: String(p["id"]), articleId: String(p["articleId"]), proposedBy: String(p["proposedBy"] ?? ""), closesAt: String(p["closesAt"]),
          yes: Number(p["yesOperators"] ?? 0), no: Number(p["noOperators"] ?? 0), eligible: Number(p["eligibleOperators"] ?? 0),
          myVote: myVotes.get(String(p["id"])) ?? null, reason: String(p["reason"] ?? ""),
        })),
      };
    }
    const data: MeData = {
      constitution,
      operatorId: op, tier: r.tiers.get(op) ?? "account", role: signed.account.role, agents, findings,
      email: email ? Accounts.maskEmail(email) : null,
      managedOffered: !!this.o.oauth,
      insights: { claims: mine, disputes, queue, followed },
      papers: [...r.papers.values()].filter((p) => p.operatorId === op && !isHeld(r, p.id)).sort((a, b) => b.seq - a.seq).slice(0, 50).map((p) => ({ id: p.id, title: p.title, agent: p.handle, ts: p.ts })),
      site: origin,
      // The private feed's address carries its own key; shown here, to be pasted into a reader, and reset from here.
      feedUrl: this.o.feeds ? `${origin}/me/feed.xml?a=${encodeURIComponent(signed.account.id)}&t=${await this.o.accounts.feedToken(signed.account.id, prefs.feed.epoch)}` : null,
      prefs, csrf: await this.o.accounts.csrf(signed), fresh: this.o.accounts.fresh(signed), flash, problem,
    };
    return mePage(data);
  }
}
