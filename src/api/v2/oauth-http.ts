/**
 * The HTTP face of OAuth 2.1 for the connector (oauth.ts has the logic):
 * the two metadata documents, client registration, the authorization page
 * (sign in, then consent), the token and revocation endpoints. Pages reuse
 * the account cookies and the anti-forgery token of /me; a person who is
 * not signed in sees the sign-in form and is brought back here afterwards
 * through a short-lived cookie that names this page and nothing else.
 */

import type { Json } from "../../core/canonical.js";
import { Accounts, cookie, setCookie, clearCookie } from "./accounts.js";
import { ME_HEADERS, sameOrigin } from "./me.js";
import type { OAuth } from "./oauth.js";
import { formOf } from "./oauth.js";
import { consentPage, noticePage, signInPage } from "../../web/me.js";

const SESSION_COOKIE = "ecd_s";
const BROWSER_COOKIE = "ecd_b";
export const NEXT_COOKIE = "ecd_next";
const YEAR_S = 365 * 24 * 3600;
const JSON_HEADERS: Record<string, string> = { "content-type": "application/json; charset=utf-8", "cache-control": "no-store", "x-content-type-options": "nosniff", pragma: "no-cache" };

export interface OAuthHttpOptions {
  oauth: OAuth;
  accounts: Accounts;
  secure?: boolean;
  readOnly?: boolean;
}

/** Only the authorization page may be returned to after sign-in: a path on this site, nothing else. */
export function safeNext(v: string | null): string | null {
  return v && /^\/oauth\/authorize\?[A-Za-z0-9%._~&=+-]{1,2000}$/.test(v) ? v : null;
}

export class OAuthHandler {
  constructor(private o: OAuthHttpOptions) {}

  private json(status: number, body: Json, extra: Record<string, string> = {}): Response {
    return new Response(JSON.stringify(body), { status, headers: { ...JSON_HEADERS, ...extra } });
  }
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

  /** Paths this handler owns. */
  static owns(path: string): boolean {
    return path === "/.well-known/oauth-authorization-server" || path === "/.well-known/oauth-protected-resource" || path.startsWith("/.well-known/oauth-protected-resource/") || path.startsWith("/oauth/");
  }

  async handle(req: Request, path: string, ip: string): Promise<Response> {
    const method = req.method.toUpperCase();
    const secure = this.o.secure ?? true;
    const url = new URL(req.url);
    if (path === "/.well-known/oauth-authorization-server") return this.json(200, this.o.oauth.metadata(), { "cache-control": "public, max-age=3600", "access-control-allow-origin": "*" });
    if (path === "/.well-known/oauth-protected-resource" || path.startsWith("/.well-known/oauth-protected-resource/")) return this.json(200, this.o.oauth.resourceMetadata(), { "cache-control": "public, max-age=3600", "access-control-allow-origin": "*" });
    if (method === "OPTIONS" && (path === "/oauth/register" || path === "/oauth/token" || path === "/oauth/revoke")) {
      return new Response(null, { status: 204, headers: { "access-control-allow-origin": "*", "access-control-allow-methods": "POST, OPTIONS", "access-control-allow-headers": "content-type, authorization", "access-control-max-age": "86400" } });
    }
    if (path === "/oauth/register") {
      if (method !== "POST") return this.json(405, { error: "invalid_request", error_description: "POST a client registration" });
      if (this.o.readOnly) return this.json(503, { error: "temporarily_unavailable", error_description: "Ecdysis is read-only right now" });
      let body: Json = null;
      try { body = (await req.json()) as Json; } catch { return this.json(400, { error: "invalid_client_metadata", error_description: "JSON body" }); }
      const r = await this.o.oauth.register(body, ip);
      return this.json(r.status, r.body, { "access-control-allow-origin": "*" });
    }
    if (path === "/oauth/token") {
      if (method !== "POST") return this.json(405, { error: "invalid_request", error_description: "POST the grant" });
      const r = await this.o.oauth.tokenRequest(await formOf(req));
      return this.json(r.status, r.body, { "access-control-allow-origin": "*" });
    }
    if (path === "/oauth/revoke") {
      if (method !== "POST") return this.json(405, { error: "invalid_request" });
      const r = await this.o.oauth.revoke(await formOf(req));
      return this.json(r.status, r.body, { "access-control-allow-origin": "*" });
    }
    if (path === "/oauth/authorize") return this.authorize(req, url, method, ip, secure);
    return this.json(404, { error: "not_found" });
  }

  /** The authorization page: refuse bad requests outright, sign the person in if need be, then ask. */
  private async authorize(req: Request, url: URL, method: string, ip: string, secure: boolean): Promise<Response> {
    void ip;
    if (method !== "GET" && method !== "POST") return this.html(405, noticePage("Method not allowed", "This page takes GET and POST."));
    if (!this.o.accounts.enabled()) return this.html(503, signInPage({ closed: true }));
    const check = await this.o.oauth.checkAuthorize(url.searchParams);
    if (!check.ok) {
      if (check.redirect) return this.redirect(check.redirect);
      return this.html(check.status, noticePage("This sign-in request isn't valid", check.error, "/me"));
    }
    const signed = await this.o.accounts.session(cookie(req.headers.get("cookie"), SESSION_COOKIE));
    if (!signed) {
      // Sign in first, then come back here. The return path is this page's own path and query, kept in a short-lived cookie.
      const browser = cookie(req.headers.get("cookie"), BROWSER_COOKIE);
      const cookies = [setCookie(NEXT_COOKIE, `${url.pathname}${url.search}`, 15 * 60, secure)];
      if (!browser || !/^[A-Za-z0-9_-]{32,64}$/.test(browser)) cookies.push(setCookie(BROWSER_COOKIE, this.o.accounts.newBrowserToken(), YEAR_S, secure));
      return this.html(200, signInPage({ problem: `${check.client.name} asks to act as you on Ecdysis. Sign in first; you will be asked whether to allow it.` }), cookies);
    }
    const action = `${url.pathname}${url.search}`;
    if (method === "GET") {
      const email = await this.o.accounts.emailOf(signed.account);
      const managed = (await this.o.oauth.managedAgentsOf(signed.account.id)).filter((m) => !m.destroyedAt).map((m) => m.handle);
      return this.html(200, consentPage({ clientName: check.client.name, email: email ? Accounts.maskEmail(email) : null, operatorId: signed.account.operatorId, managed, csrf: await this.o.accounts.csrf(signed), action }), [clearCookie(NEXT_COOKIE, secure)]);
    }
    // POST: the decision. Same origin and the anti-forgery token, like every other form on the site.
    if (!sameOrigin(req)) return this.html(403, noticePage("Not from here", "That request did not come from this site, so nothing was done."));
    const form = await formOf(req);
    if (!(await this.o.accounts.csrfOk(signed, form.get("csrf")))) return this.html(403, noticePage("That form had expired", "Please go back to the app and try again."));
    if (form.get("decision") !== "allow") {
      const d = await this.o.oauth.deny(url.searchParams);
      return d ? this.redirect(d.redirect) : this.html(400, noticePage("Declined", "Nothing was granted."));
    }
    if (this.o.readOnly) return this.html(503, noticePage("Not right now", "Ecdysis isn't taking changes at the moment. Please try again later."));
    const g = await this.o.oauth.grant(signed, url.searchParams);
    if (!g.ok) return g.redirect ? this.redirect(g.redirect) : this.html(g.status, noticePage("This sign-in request isn't valid", g.error, "/me"));
    return this.redirect(g.redirect);
  }
}
