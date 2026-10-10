/**
 * /me: the handler behind "Your Ecdysis". Decides, never renders (that is
 * src/web/me.ts). Every state change is a POST carrying the session's
 * anti-forgery token; key issue, key revocation and deletion also need a
 * sign-in from the last ten minutes (step-up). Two cookies: `ecd_b` names
 * the browser (a magic link works only where it was requested) and `ecd_s`
 * is the session. Pages are never cached or indexed.
 */

import type { Json } from "../../core/canonical.js";
import { generateKeyPair } from "../../core/crypto.js";
import { isHeld } from "../../core/v2/flow.js";
import { CLAIM_REF, isClaimRef } from "../../core/v2/refs.js";
import { FIELDS } from "../../core/schema.js";
import { Accounts, ALERTS, clearCookie, cookie, setCookie, type Alert, type Digest, type Preferences, type Signed } from "./accounts.js";
import type { V2Service } from "./service.js";
import type { OAuth } from "./oauth.js";
import type { V2Governance } from "./governance.js";
import { CONSTITUTION_VERSION, constitutionHash } from "../../core/constitution.js";
import { NEXT_COOKIE, safeNext } from "./oauth-http.js";
import type { V2Feeds } from "./feed.js";
import type { IssueRegistry } from "./issues.js";
import { analyticsPage, keyIssuedPage, linkSentPage, mePage, noticePage, pairingPage, signInPage, type MeAgent, type MeAnalytics, type MeConstitution, type MeCorrectable, type MeData, type MeFinding, type MeVerification } from "../../web/me.js";

export const ME_HEADERS: Record<string, string> = {
  "content-type": "text/html; charset=utf-8",
  "x-content-type-options": "nosniff",
  // Not "no-referrer": under that policy browsers send `Origin: null` on the
  // page's OWN form posts (Fetch's "append a request Origin header"), which
  // sameOrigin() below would refuse; the sign-in button then does nothing
  // (seen in production on 3 Oct 2026, the first time anyone signed in).
  // "same-origin" still sends nothing to any other site: these pages load no
  // third-party resource at all (default-src 'none'), and a link out carries
  // no referrer. The v1 console learnt the same lesson (src/api/operator.ts).
  "referrer-policy": "same-origin",
  "strict-transport-security": "max-age=31536000; includeSubDomains",
  "cache-control": "no-store",
  "x-robots-tag": "noindex, nofollow",
  "content-security-policy": "default-src 'none'; style-src 'unsafe-inline'; img-src 'self'; font-src 'self'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'",
};
const BROWSER_COOKIE = "ecd_b";
const SESSION_COOKIE = "ecd_s";
const YEAR_S = 365 * 24 * 3600;
const MAX_FORM = 16 * 1024;
/** A managed agent's claims open to correction that the page lists, newest first; an older one is corrected by its id. */
export const CORRECTIONS_LISTED = 20;

/** A refusal from the service, as a sentence for the page: its error, and what its detail says. */
function refusal(body: Json): string {
  const b = (body && typeof body === "object" && !Array.isArray(body) ? body : {}) as Record<string, unknown>;
  const detail = Array.isArray(b["detail"]) ? (b["detail"] as unknown[]).filter((x): x is string => typeof x === "string") : [];
  return `${String(b["error"] ?? "refused")}${detail.length ? `: ${detail.join("; ")}` : ""}`;
}

export interface MeOptions {
  accounts: Accounts;
  v2: V2Service;
  /** OAuth and managed agents, when configured: the page offers them, and ending every session ends every token. */
  oauth?: OAuth | null;
  /** Amendments (Article V), when configured: the page shows the constitution in force, acknowledgments and open proposals. */
  governance?: V2Governance | null;
  /** The private feed (/me/feed.xml), when configured: fetched by a feed reader with a capability token, no cookie. */
  feeds?: V2Feeds | null;
  /** The stewards' issues queue, when configured: a person asks for verification from here, and reads the decision here. */
  issues?: IssueRegistry | null;
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
 *
 * `Origin: null` is ambiguous: a browser sends it both for a cross-site form
 * in a sandboxed frame (refuse) and for a same-origin form post from a page
 * served with `Referrer-Policy: no-referrer` (fine). Sec-Fetch-Site, which
 * no page can set or suppress, tells them apart; without it, null is refused,
 * so the check fails closed. Our own pages no longer send no-referrer (see
 * ME_HEADERS), so in practice Origin is the real one.
 */
export function sameOrigin(req: Request): boolean {
  const url = new URL(req.url);
  const origin = req.headers.get("origin");
  const site = req.headers.get("sec-fetch-site");
  if (site && site !== "same-origin" && site !== "none") return false;
  if (!origin || origin === "null") return site === "same-origin";
  return origin === `${url.protocol}//${url.host}`;
}

/** The analytics as CSV: one row per agent, then one per claim. Values are quoted; a leading =, +, - or @ is neutralised so a cell can never be a formula. */
export function analyticsCsv(a: MeAnalytics): string {
  const cell = (v: unknown): string => {
    let t = v === null || v === undefined ? "" : Array.isArray(v) ? v.join(" ") : typeof v === "number" ? (Number.isInteger(v) ? String(v) : v.toFixed(4)) : String(v);
    if (/^[=+\-@\t\r]/.test(t)) t = `'${t}`;
    return `"${t.replace(/"/g, '""')}"`;
  };
  const row = (vs: unknown[]) => vs.map(cell).join(",");
  const lines = [
    row(["kind", "agent", "handle_or_ref", "text", "status_or_models", "credence_or_reliability", "use", "dispute", "receipts", "verification_rate", "lapses", "credence_7d_ago", "credence_30d_ago", "families"]),
    ...a.agents.map((g) => row(["agent", g.handle, g.handle, "", g.families, g.reliability, g.use, "", g.receipts, g.verificationRate, g.lapses, "", "", g.families])),
    ...a.claims.map((c) => row(["claim", c.agent, c.ref, c.text, c.status, c.credence, c.use, c.dispute, "", "", "", c.weekAgo, c.monthAgo, c.families])),
  ];
  return `${lines.join("\r\n")}\r\n`;
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
      // Analytics (§4.6): per agent and per claim, with the credence trajectory, as a page or as CSV. Derived on request,
      // never on the dashboard: the trajectory derives the record at earlier moments.
      if (path === "/me/analytics" || path === "/me/analytics.csv") {
        const a = await this.analytics(signed);
        if (path.endsWith(".csv")) return new Response(method === "HEAD" ? null : analyticsCsv(a), { status: 200, headers: { ...ME_HEADERS, "content-type": "text/csv; charset=utf-8", "content-disposition": `attachment; filename="ecdysis-${signed.account.operatorId}.csv"` } });
        return this.html(200, method === "HEAD" ? "" : analyticsPage(a));
      }
      if (path !== "/me") return this.redirect("/me");
      return this.html(200, await dashboard(url.searchParams.get("ok"), null));
    }

    // Every POST below needs the anti-forgery token.
    const f = await this.form(req);
    if (!f || !(await this.o.accounts.csrfOk(signed, f.get("csrf")))) return this.html(403, await dashboard(null, "That form had expired. Please try again."));
    if (this.o.readOnly && path !== "/me/signout" && path !== "/me/signout-all") return this.html(503, noticePage("Not right now", "Ecdysis isn't taking changes at the moment. Please try again later."));
    // Keys, deletion, pairing (which lets whoever holds the code register agents under this operator), a managed agent's one
    // correction of a claim (signed as the agent, and never undone) and a verification request (a statement of who stands
    // behind the operator) need a recent sign-in.
    const needsStepUp = path === "/me/keys/issue" || path === "/me/keys/revoke" || path === "/me/delete" || path === "/me/pairing" || path === "/me/agents/managed" || path === "/me/agents/managed/destroy" || path === "/me/agents/managed/amend" || path === "/me/verify";
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
      case "/me/agents/managed/amend": {
        // A managed agent's one correction of a claim: the connector never signs it (oauth.ts, PAGE_SIGNS), so it is asked
        // for here, and decided by the service exactly as any correction is.
        if (!this.o.oauth) return this.html(404, noticePage("Not offered", "Managed agents are not offered on this deployment."));
        const claim = (f.get("claim") ?? "").trim();
        const named = isClaimRef(claim) ? claim : "the claim";
        // A textarea's line breaks arrive as CRLF, as forms encode them; LF is what the person typed. Nothing else is
        // touched: the service judges every other character, as it would in an envelope the agent signed itself.
        const test = (f.get("test") ?? "").replace(/\r\n/g, "\n");
        const kind = f.get("kind") ?? "";
        if (!test.trim() && !kind) return this.html(400, await dashboard(null, `Nothing was corrected in ${named}: write the corrected test, or choose the corrected kind.`));
        const r = await this.o.oauth.amendManaged(signed, claim, { ...(kind ? { kind } : {}), ...(test.trim() ? { test } : {}) });
        if (r.status !== 201) return this.html(r.status, await dashboard(null, `Couldn't correct ${named}: ${refusal(r.body)}`));
        return this.redirect(`/me?ok=${encodeURIComponent(`Corrected ${claim}, once: the correction is on the public log, signed as its managed agent, and the claim's page shows both versions.`)}`);
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
        const fields = f.getAll("fields").filter((x): x is (typeof FIELDS)[number] => (FIELDS as readonly string[]).includes(x));
        const lines = (name: string, re: RegExp | null, max: number) => [...new Set((f.get(name) ?? "").split(/\r?\n/).map((s) => s.trim()).filter((s) => s && s.length <= 120 && (!re || re.test(s))))].slice(0, max);
        // Each form writes only the section it owns, over the preferences as they stand at the moment of writing.
        const r = await this.o.accounts.updatePreferences(signed, (p): Preferences => ({ ...p, interests: { ...p.interests, fields: [...new Set(fields)], topics: lines("topics", null, 30), claims: lines("claims", CLAIM_REF, 100) } }));
        if (!r.ok) return this.html(r.status, await dashboard(null, r.error));
        return this.redirect("/me?ok=Interests+saved.");
      }
      case "/me/notifications": {
        const digest = f.get("digest");
        const alerts = f.getAll("alerts").filter((x): x is Alert => (ALERTS as readonly string[]).includes(x));
        const r = await this.o.accounts.updatePreferences(signed, (p): Preferences => ({ ...p, notifications: { digest: (digest === "daily" || digest === "weekly" ? digest : "off") as Digest, alerts: [...new Set(alerts)] } }));
        if (!r.ok) return this.html(r.status, await dashboard(null, r.error));
        return this.redirect("/me?ok=Notifications+saved.");
      }
      case "/me/profile": {
        // Opt in to a public page at /u/<name>, or opt out. The name is the only thing the page adds to what the record shows.
        const clear = f.get("action") === "clear";
        const r = await this.o.accounts.setProfile(signed, clear ? null : (f.get("name") ?? ""));
        if (!r.ok) return this.html(r.status, await dashboard(null, `Couldn't set the profile name: ${r.error}.`));
        return this.redirect(`/me?ok=${encodeURIComponent(r.name ? `Your public profile is at /u/${r.name}.` : "Your public profile is off.")}`);
      }
      case "/me/verify": {
        if (!this.o.issues) return this.html(404, noticePage("Not offered", "Verification requests are not taken on this deployment; write to the stewards instead."));
        const r = await this.o.issues.requestVerification(signed.account.operatorId, f.get("evidence") ?? "");
        if (!r.ok) return this.html(r.status, await dashboard(null, `Couldn't send the request: ${r.error}.`));
        return this.redirect(`/me?ok=${encodeURIComponent("Your request is with the stewards. They see it here only; their decision goes on the public log as a tier entry, and this page will say what they decided.")}#verification`);
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

  /**
   * Analytics for the operator's agents and claims (§4.6). The credence
   * trajectory compares today's scores with the record as it stood 7 and 30
   * days ago; those two derivations are memoised like any other.
   */
  private async analytics(signed: Signed): Promise<MeAnalytics> {
    const op = signed.account.operatorId;
    // The service's clock, not the wall's: "a week ago" is a week before the moment the record is read at.
    const now = this.o.v2.clock();
    const r = await this.o.v2.record();
    const s = await this.o.v2.scores();
    const DAY = 24 * 3600 * 1000;
    const at = async (daysAgo: number) => { const rec = await this.o.v2.recordAsOf(new Date(now.getTime() - daysAgo * DAY)); return this.o.v2.scoresFor(rec); };
    const [week, month] = [await at(7), await at(30)];
    const mine = r.claims.filter((c) => c.authorOperator === op && !isHeld(r, c.ref));
    const claims = mine.map((c) => {
      const sc = s.claims.get(c.ref);
      const n = r.native.get(c.ref);
      return { ref: c.ref, agent: n?.handle ?? "", text: n?.text ?? "", stated: c.stated, status: sc?.status ?? "unchecked", credence: sc?.credence ?? 0.5, use: sc?.use ?? 0, dispute: sc?.dispute ?? 0, families: sc?.families ?? [], weekAgo: week.claims.get(c.ref)?.credence ?? null, monthAgo: month.claims.get(c.ref)?.credence ?? null };
    });
    const mean = (xs: number[]) => (xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : null);
    const agents = [...r.agents.entries()].filter(([, a]) => a.operatorId === op).map(([handle, a]) => {
      const own = claims.filter((c) => c.agent === handle);
      const receipts = [...r.checks.values()].filter((c) => c.handle === handle && c.stage === "resulted" && !c.disowned);
      const crossed = receipts.filter((c) => c.crossMatch !== null);
      const statuses: Record<string, number> = {};
      for (const c of own) statuses[c.status] = (statuses[c.status] ?? 0) + 1;
      return {
        handle, families: a.families, managed: a.managed, retired: a.revokedAt !== null,
        claims: own.length, statuses, meanCredence: mean(own.map((c) => c.credence)), use: own.reduce((x, c) => x + c.use, 0),
        receipts: receipts.length, verificationRate: crossed.length ? crossed.filter((c) => c.crossMatch).length / crossed.length : null,
        reviews: r.evidence.filter((e) => e.kind === "review" && e.agent === handle).length,
        reliability: s.track.reliability.get(handle) ?? 0.5, scored: s.track.reports.filter((x) => x.agent === handle && x.resolved !== null).length,
        lapses: r.lapses.get(handle) ?? 0,
      };
    });
    return {
      operatorId: op, tier: r.tiers.get(op) ?? "account", at: now.toISOString(), agents, claims,
      trajectory: { now: mean(claims.map((c) => c.credence)), weekAgo: mean(claims.map((c) => c.weekAgo).filter((x): x is number => x !== null)), monthAgo: mean(claims.map((c) => c.monthAgo).filter((x): x is number => x !== null)) },
    };
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
      claims: [...r.native.values()].filter((c) => c.handle === handle).length,
      registered: [...r.external.values()].filter((e) => e.handle === handle).length,
      links: [...r.links.values()].filter((l) => l.handle === handle && !l.withdrawn && !l.disowned).length,
      receipts: [...r.checks.values()].filter((c) => c.handle === handle && c.stage === "resulted" && !c.disowned).length,
      managed: a.managed,
    }));
    const findings: MeFinding[] = r.findings.filter((f) => f.oddOperator === op).map((f) => ({ id: f.id, verdict: f.verdict, agent: f.oddAgent ?? "", decidedAt: f.decidedAt, inForce: f.inForce, reversed: f.reversed }));
    const prefs = await this.o.accounts.preferences(signed);
    const rank = (x: string) => ({ refuted: 0, contested: 1, unchecked: 2, supported: 3, established: 4 } as Record<string, number>)[x] ?? 2;
    const mine = r.claims.filter((c) => c.authorOperator === op).map((c) => s.claims.get(c.ref)).filter((c): c is NonNullable<typeof c> => !!c)
      .sort((a, b) => rank(a.status) - rank(b.status) || a.credence - b.credence).slice(0, 20)
      .map((c) => ({ ref: c.ref, text: r.native.get(c.ref)?.text ?? "", credence: c.credence, status: c.status, use: c.use, lift: c.lift[0] ? { ref: c.lift[0].ref, gain: c.lift[0].gain } : null }));
    const reliedOn = new Set(r.uses.filter((u) => u.operatorId === op).map((u) => u.claim));
    const disputes = [...reliedOn].map((ref) => s.claims.get(ref)).filter((c): c is NonNullable<typeof c> => !!c && (c.status === "contested" || c.dispute > 0))
      .map((c) => ({ ref: c.ref, status: c.status, credence: c.credence, dispute: c.dispute }));
    const fields = new Set(prefs.interests.fields);
    const fieldOf = (ref: string) => r.native.get(ref)?.field ?? "other";
    const own = new Set(r.claims.filter((c) => c.authorOperator === op).map((c) => c.ref));
    const queue = [...s.claims.values()].filter((c) => c.status !== "established" && c.status !== "refuted" && !own.has(c.ref) && !isHeld(r, c.ref) && (!fields.size || fields.has(fieldOf(c.ref))))
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
    // Verification: the tier as the record has it, and the newest request (open, declined with the steward's note, or acted).
    let verification: MeVerification | null = null;
    if (this.o.issues) {
      const req = await this.o.issues.verificationOf(op);
      verification = {
        offered: true,
        request: req ? { status: req.status, at: req.openedAt, decidedAt: req.decidedAt, note: req.note ? req.note.replace(/^(verify|decline):\s*/, "") : null } : null,
        undeclared: agents.filter((a) => !a.retired && a.families.length === 0).map((a) => a.handle),
      };
    }
    // Corrections (claim.amend) the person may make for their managed agents, here and only here: the agents the archive can
    // still sign for, and each one's claims the service would still let its operator correct (in view, never corrected,
    // nothing landed on them), newest first, CORRECTIONS_LISTED at most for each; an older one is corrected by its id.
    let corrections: MeData["corrections"] = null;
    if (this.o.oauth) {
      const handles = (await this.o.oauth.managedAgentsOf(signed.account.id)).filter((m) => !m.destroyedAt).map((m) => m.handle);
      if (handles.length) {
        const kinds = new Map(r.claims.map((c) => [c.ref, c.kind ?? "empirical"]));
        const claims: MeCorrectable[] = [];
        const more: string[] = [];
        for (const handle of handles) {
          const own = [
            ...[...r.native.values()].filter((c) => c.handle === handle).map((c) => ({ id: c.id, text: c.text, test: c.test, source: null, seq: c.seq })),
            ...[...r.external.entries()].filter(([, e]) => e.handle === handle).map(([id, e]) => ({ id, text: e.quote, test: e.test, source: e.source, seq: e.seq })),
          ].sort((a, b) => b.seq - a.seq);
          let listed = 0;
          for (const c of own) {
            if (!this.o.v2.amendable(r, c.id, op)) continue;
            if (listed === CORRECTIONS_LISTED) { more.push(handle); break; }
            claims.push({ id: c.id, handle, text: c.text, test: c.test, source: c.source, kind: kinds.get(c.id) ?? "empirical" });
            listed++;
          }
        }
        corrections = { agents: handles, claims, more };
      }
    }
    const data: MeData = {
      constitution, verification, corrections,
      operatorId: op, tier: r.tiers.get(op) ?? "account", role: signed.account.role, agents, findings,
      email: email ? Accounts.maskEmail(email) : null,
      managedOffered: !!this.o.oauth,
      insights: { claims: mine, disputes, queue, followed },
      claims: [...r.native.values()].filter((c) => c.operatorId === op && !isHeld(r, c.id)).sort((a, b) => b.seq - a.seq).slice(0, 50).map((c) => ({ id: c.id, text: c.text, agent: c.handle, ts: c.ts })),
      registered: [...r.external.entries()].filter(([id, e]) => e.operatorId === op && !isHeld(r, id)).sort(([, a], [, b]) => b.seq - a.seq).slice(0, 50)
        .map(([id, e]) => ({ id, text: e.quote, source: e.source, agent: e.handle, ts: e.ts, status: s.claims.get(id)?.status ?? "unchecked", credence: s.claims.get(id)?.credence ?? 0.5 })),
      site: origin,
      // The private feed's address carries its own key; shown here, to be pasted into a reader, and reset from here.
      feedUrl: this.o.feeds ? `${origin}/me/feed.xml?a=${encodeURIComponent(signed.account.id)}&t=${await this.o.accounts.feedToken(signed.account.id, prefs.feed.epoch)}` : null,
      prefs, csrf: await this.o.accounts.csrf(signed), fresh: this.o.accounts.fresh(signed), flash, problem,
    };
    return mePage(data);
  }
}
