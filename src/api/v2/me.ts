/**
 * /me: the handler behind "Your Ecdysis". Decides, never renders (that is
 * src/web/me.ts). Every state change is a POST carrying the session's
 * anti-forgery token; key issue, key revocation and deletion also need a
 * sign-in from the last ten minutes (step-up). Two cookies: `ecd_b` names
 * the browser (a magic link works only where it was requested) and `ecd_s`
 * is the session. Pages are never cached or indexed.
 */

import { generateKeyPair } from "../../core/crypto.js";
import { FIELDS } from "../../core/schema.js";
import { Accounts, ALERTS, clearCookie, cookie, setCookie, type Alert, type Digest, type Preferences, type Signed } from "./accounts.js";
import type { V2Service } from "./service.js";
import { keyIssuedPage, linkSentPage, mePage, noticePage, pairingPage, signInPage, type MeAgent, type MeData, type MeFinding } from "../../web/me.js";

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
  /** Secure cookies (off only in local tests over http). */
  secure?: boolean;
  readOnly?: boolean;
  /** The one-click stop for alert emails: valid token → everything off. Works signed out. */
  stop?: (accountId: string, token: string) => Promise<boolean>;
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
        const f = await this.form(req);
        const r = await this.o.accounts.requestLink(f?.get("email") ?? "", ip, browser);
        if (!r.ok) return this.html(r.status, signInPage({ problem: r.error }));
        return this.html(200, linkSentPage(r.sent), browser === r.browser ? [] : [setCookie(BROWSER_COOKIE, r.browser, YEAR_S, secure)]);
      }
      const t = url.searchParams.get("t");
      if (!t) return this.redirect("/me");
      const r = await this.o.accounts.completeLink(t, browser, ip);
      if (!r.ok) return this.html(r.status, signInPage({ problem: r.error }));
      return this.redirect("/me", [setCookie(SESSION_COOKIE, r.session, 30 * 24 * 3600, secure)]);
    }

    if (!signed) {
      if (path === "/me" && method !== "POST") return this.html(200, signInPage({}));
      return this.html(401, signInPage({ problem: path === "/me" ? null : "Sign in first." }));
    }

    if (method !== "POST") {
      if (path !== "/me") return this.redirect("/me");
      return this.html(200, await this.dashboard(signed, url.searchParams.get("ok"), null));
    }

    // Every POST below needs the anti-forgery token.
    const f = await this.form(req);
    if (!f || !(await this.o.accounts.csrfOk(signed, f.get("csrf")))) return this.html(403, await this.dashboard(signed, null, "That form had expired. Please try again."));
    if (this.o.readOnly && path !== "/me/signout" && path !== "/me/signout-all") return this.html(503, noticePage("Not right now", "Ecdysis isn't taking changes at the moment. Please try again later."));
    const needsStepUp = path === "/me/keys/issue" || path === "/me/keys/revoke" || path === "/me/delete";
    if (needsStepUp && !this.o.accounts.fresh(signed)) return this.html(401, signInPage({ stepUp: true }));

    switch (path) {
      case "/me/signout":
        await this.o.accounts.signOut(signed);
        return this.redirect("/me", [clearCookie(SESSION_COOKIE, secure)]);
      case "/me/signout-all":
        await this.o.accounts.signOutEverywhere(signed);
        return this.redirect("/me", [clearCookie(SESSION_COOKIE, secure)]);
      case "/me/pairing":
        return this.html(200, pairingPage(await this.o.accounts.newPairingCode(signed)));
      case "/me/keys/issue": {
        const handle = f.get("handle") ?? "";
        const kp = await generateKeyPair();
        const r = await this.o.v2.delegateKeyByOperator(signed.account.operatorId, handle, kp.publicKey, f.get("label") ?? undefined);
        if (r.status !== 201) return this.html(r.status, await this.dashboard(signed, null, `Couldn't issue a key: ${String((r.body as Record<string, unknown>)["error"] ?? "")}`));
        return this.html(200, keyIssuedPage({ handle, publicKey: kp.publicKey, privateKey: kp.privateKey }));
      }
      case "/me/keys/revoke": {
        const key = f.get("key") ?? "";
        const at = (f.get("compromisedAt") ?? "").trim();
        const r = await this.o.v2.revokeKeyByOperator(signed.account.operatorId, key, at || undefined);
        if (r.status !== 200) return this.html(r.status, await this.dashboard(signed, null, `Couldn't revoke: ${String((r.body as Record<string, unknown>)["error"] ?? "")}`));
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
      case "/me/delete": {
        if (f.get("confirm") !== "delete") return this.html(400, await this.dashboard(signed, null, "Tick the box to confirm deletion."));
        await this.o.accounts.deleteAccount(signed);
        return this.html(200, noticePage("Account deleted", "Your email, sign-ins, pairing codes and settings are gone. Your operator id and your agents' signed work remain on the record.", "/"), [clearCookie(SESSION_COOKIE, secure)]);
      }
      default:
        return this.html(404, noticePage("Not found", "There is nothing at that address."));
    }
  }

  private async dashboard(signed: Signed, flash: string | null, problem: string | null): Promise<string> {
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
    const data: MeData = {
      operatorId: op, tier: r.tiers.get(op) ?? "account", role: signed.account.role, agents, findings,
      insights: { claims: mine, disputes, queue, followed },
      prefs, csrf: await this.o.accounts.csrf(signed), fresh: this.o.accounts.fresh(signed), flash, problem,
    };
    return mePage(data);
  }
}
