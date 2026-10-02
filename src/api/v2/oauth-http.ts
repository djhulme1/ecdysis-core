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
import { formOf, MAX_BODY } from "./oauth.js";
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

/** Only the authorization page may be returned to after sign-in: that path on this site with any query (RFC 3986's query characters), nothing else. */
export function safeNext(v: string | null): string | null {
  return v && /^\/oauth\/authorize\?[A-Za-z0-9%._~!$&'()*+,;=:@/?-]{1,2000}$/.test(v) ? v : null;
}

export class OAuthHandler {
  constructor(private o: OAuthHttpOptions) {}

  private json(status: number, body: Json, extra: Record<string, string> = {}): Response {
    return new Response(JSON.stringify(body), { status, headers: { ...JSON_HEADERS, ...extra } });
  }
  private html(status: number, body: string, cookies: string[] = [], formActionAlso?: string): Response {
    const h = new Headers(ME_HEADERS);
    // The consent form's answer is a redirect to the client. Chrome and Safari hold the whole redirect chain to form-action,
    // so the client's origin is allowed on that one page; everything else keeps 'self'.
    if (formActionAlso) h.set("content-security-policy", ME_HEADERS["content-security-policy"]!.replace("form-action 'self'", `form-action 'self' ${formActionAlso}`));
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
    // RFC 8414: the authorization server's document lives on the issuer's host and names it; served anywhere else it would
    // contradict itself, so it is not served there. RFC 9728: the resource's document lives on the resource's host, at the
    // root and at the resource's own path (and /mcp/me, which is the same resource).
    if (path === "/.well-known/oauth-authorization-server") {
      if (url.origin !== this.o.oauth.issuer) return this.json(404, { error: "not_found", error_description: `the authorization server is ${this.o.oauth.issuer}` });
      return this.json(200, this.o.oauth.metadata(), { "cache-control": "public, max-age=3600", "access-control-allow-origin": "*" });
    }
    if (path === "/.well-known/oauth-protected-resource" || path === "/.well-known/oauth-protected-resource/mcp" || path === "/.well-known/oauth-protected-resource/mcp/me") {
      if (url.origin !== new URL(this.o.oauth.resource).origin) return this.json(404, { error: "not_found", error_description: `the protected resource is ${this.o.oauth.resource}` });
      return this.json(200, this.o.oauth.resourceMetadata(), { "cache-control": "public, max-age=3600", "access-control-allow-origin": "*" });
    }
    if (path.startsWith("/.well-known/oauth-protected-resource/")) return this.json(404, { error: "not_found" });
    if (method === "OPTIONS" && (path === "/oauth/register" || path === "/oauth/token" || path === "/oauth/revoke")) {
      return new Response(null, { status: 204, headers: { "access-control-allow-origin": "*", "access-control-allow-methods": "POST, OPTIONS", "access-control-allow-headers": "content-type, authorization", "access-control-max-age": "86400" } });
    }
    if (path === "/oauth/register") {
      if (method !== "POST") return this.json(405, { error: "invalid_request", error_description: "POST a client registration" });
      if (this.o.readOnly) return this.json(503, { error: "temporarily_unavailable", error_description: "Ecdysis is read-only right now" });
      if (Number(req.headers.get("content-length") ?? "0") > MAX_BODY) return this.json(413, { error: "invalid_client_metadata", error_description: "registration too large" });
      let body: Json = null;
      try { const text = await req.text(); if (text.length > MAX_BODY) throw new Error("large"); body = JSON.parse(text) as Json; } catch { return this.json(400, { error: "invalid_client_metadata", error_description: "JSON body, under 16 KB" }); }
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
    // An unknown client or an unregistered redirect URI: nothing to send anyone back to; shown, never followed.
    if (!check.ok && !check.redirect) return this.html(check.status, noticePage("This sign-in request isn't valid", check.error, "/me"));
    const clientName = check.ok ? check.client.name : "An app";
    // The person is authenticated BEFORE anything is sent back to a client (OAuth 2.1 §7.12.2): an unauthenticated visitor
    // never bounces off this page to a registered URI, so the authorization server is no redirector. The sign-in is a fresh
    // one (step-up), as creating a managed agent from the page would need: a stale cookie alone grants nothing.
    const signed = await this.o.accounts.session(cookie(req.headers.get("cookie"), SESSION_COOKIE));
    if (!signed || !this.o.accounts.fresh(signed)) {
      // Sign in first, then come back here. The return path is this page's own path and query, kept in a short-lived cookie.
      const browser = cookie(req.headers.get("cookie"), BROWSER_COOKIE);
      const cookies = [setCookie(NEXT_COOKIE, `${url.pathname}${url.search}`, 15 * 60, secure)];
      if (!browser || !/^[A-Za-z0-9_-]{32,64}$/.test(browser)) cookies.push(setCookie(BROWSER_COOKIE, this.o.accounts.newBrowserToken(), YEAR_S, secure));
      return this.html(signed ? 401 : 200, signInPage({ stepUp: !!signed, problem: `${clientName} asks to act as you on Ecdysis. Sign in first; you will be asked whether to allow it.` }), cookies);
    }
    if (!check.ok) return this.redirect(check.redirect!); // a known client's bad request goes back to it, now that the person is here
    const action = `${url.pathname}${url.search}`;
    const clientOrigin = new URL(check.redirectUri).origin;
    if (method === "GET") {
      const email = await this.o.accounts.emailOf(signed.account);
      const managed = (await this.o.oauth.managedAgentsOf(signed.account.id)).filter((m) => !m.destroyedAt).map((m) => m.handle);
      return this.html(200, consentPage({ clientName: check.client.name, clientId: check.client.id, redirectHost: new URL(check.redirectUri).host, email: email ? Accounts.maskEmail(email) : null, operatorId: signed.account.operatorId, managed, csrf: await this.o.accounts.csrf(signed), action }), [clearCookie(NEXT_COOKIE, secure)], clientOrigin);
    }
    // POST: the decision. Same origin and the anti-forgery token, like every other form on the site.
    if (!sameOrigin(req)) return this.html(403, noticePage("Not from here", "That request did not come from this site, so nothing was done."));
    const form = await formOf(req);
    if (!(await this.o.accounts.csrfOk(signed, form.get("csrf")))) return this.html(403, noticePage("That form had expired", "Please go back to the app and try again."));
    if (form.get("decision") !== "allow") {
      // Declined: the person is told, and offered the way back; nobody is sent to a registered URI without a click.
      const d = await this.o.oauth.deny(url.searchParams);
      return this.html(200, noticePage("Nothing was granted", `You declined. ${check.client.name} was not given access to your account.`, d ? d.redirect : "/me"), [], clientOrigin);
    }
    if (this.o.readOnly) return this.html(503, noticePage("Not right now", "Ecdysis isn't taking changes at the moment. Please try again later."));
    const g = await this.o.oauth.grant(signed, url.searchParams);
    if (!g.ok) return g.redirect ? this.redirect(g.redirect) : this.html(g.status, noticePage("This sign-in request isn't valid", g.error, "/me"));
    return this.redirect(g.redirect);
  }
}
