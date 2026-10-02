/**
 * /steward: the stewardship area's handler (design §7). Two locks, both
 * required when configured: Cloudflare Access in front (the header it sets
 * after admitting a request, verified again here), and a signed-in account
 * with the steward role. Acts (tier changes, reversals) also need a sign-in
 * from the last ten minutes, carry the session's anti-forgery token, and go
 * on the log with the steward's operator id. Reserved power R1 is not here.
 */

import { verifyAccess, accessConfigured, type AccessConfig } from "../access.js";
import { APPEAL_MS } from "../../core/v2/receipts.js";
import { ME_HEADERS, sameOrigin } from "./me.js";
import { cookie, type Accounts, type Signed } from "./accounts.js";
import type { V2Service } from "./service.js";
import type { CanaryRegistry } from "./canaries.js";
import { auditPage, canariesPage, contentPage, controlsPage, evidencePage, overviewPage, peoplePage, refusedPage, type PersonRow } from "../../web/steward.js";

export interface StewardOptions {
  accounts: Accounts;
  v2: V2Service;
  /** Cloudflare Access configuration; when configured, the Access header is required too. Null: no Access layer (tests). */
  access: AccessConfig | null;
  fetchImpl?: typeof fetch;
  now?: () => Date;
  readOnly?: boolean;
  /** The canary registry (off the log), when configured. */
  canaries?: CanaryRegistry | null;
}

const MAX_FORM = 8 * 1024;
const SESSION_COOKIE = "ecd_s";

export function isStewardPath(path: string): boolean {
  return /^\/steward(\/|$)/.test(path);
}

export class StewardHandler {
  private now: () => Date;
  constructor(private o: StewardOptions) { this.now = o.now ?? (() => new Date()); }

  private html(status: number, body: string): Response {
    return new Response(body, { status, headers: ME_HEADERS });
  }
  private redirect(to: string): Response {
    return new Response(null, { status: 303, headers: { location: to, "cache-control": "no-store" } });
  }

  async handle(req: Request, path: string): Promise<Response> {
    const method = req.method.toUpperCase();
    if (method !== "GET" && method !== "HEAD" && method !== "POST") return new Response("Method not allowed", { status: 405, headers: { ...ME_HEADERS, allow: "GET, HEAD, POST" } });
    // Lock one: Cloudflare Access. Configured in production; a configuration that is present but incomplete fails closed,
    // as the operator console's does. (Tests pass access: null to run without it.)
    if (this.o.access) {
      if (!accessConfigured(this.o.access)) return this.html(503, refusedPage("This area sits behind Cloudflare Access, which is not fully configured on this deployment; nothing is served until it is."));
      const v = await verifyAccess(req, this.o.access, this.o.fetchImpl ?? fetch, this.now().getTime());
      if (!v.ok) return this.html(403, refusedPage("This area sits behind Cloudflare Access; the request did not carry a valid Access token."));
    }
    // Lock two: a signed-in steward, by the list as it stands now (not as it stood when they signed in).
    const signed = await this.o.accounts.session(cookie(req.headers.get("cookie"), SESSION_COOKIE));
    if (!signed) return this.html(401, refusedPage("Sign in to your Ecdysis first; stewardship needs a signed-in steward."));
    if (signed.account.role !== "steward" || !(await this.o.accounts.isSteward(signed.account))) return this.html(403, refusedPage("Your account does not hold the steward role."));
    if (method === "POST" && !sameOrigin(req)) return this.html(403, refusedPage("That request did not come from this site, so nothing was done."));

    const url = new URL(req.url);
    const flash = url.searchParams.get("ok");
    if (method !== "POST") return this.page(path, signed, url, flash, null);

    const len = Number(req.headers.get("content-length") ?? "0");
    const text = len > MAX_FORM ? "" : await req.text();
    if (len > MAX_FORM || text.length > MAX_FORM) return this.html(413, refusedPage("That form was too large."));
    const f = new URLSearchParams(text);
    if (!(await this.o.accounts.csrfOk(signed, f.get("csrf")))) return this.page("/steward", signed, url, null, "That form had expired. Please try again.");
    if (this.o.readOnly) return this.page("/steward", signed, url, null, "Ecdysis isn't taking changes at the moment.");
    if (!this.o.accounts.fresh(signed)) return this.html(401, refusedPage("This act needs a sign-in from the last ten minutes. Sign in again from your Ecdysis page, then return."));
    const steward = signed.account.operatorId;
    switch (path) {
      case "/steward/people/tier": {
        const tier = f.get("tier") ?? "";
        const r = await this.o.v2.setTier(f.get("operatorId") ?? "", tier as "unverified" | "account" | "verified", steward);
        if (r.status !== 200) return this.page("/steward/people", signed, url, null, `Couldn't set the tier: ${String((r.body as Record<string, unknown>)["error"] ?? "")}`);
        return this.redirect(`/steward/people?ok=${encodeURIComponent(`Tier set to ${tier}.`)}`);
      }
      case "/steward/evidence/reveal": {
        const r = await this.o.v2.revealCanary((f.get("claim") ?? "").trim(), f.get("outcome") ?? "", steward);
        if (r.status !== 200) return this.page("/steward/evidence", signed, url, null, `Couldn't reveal: ${String((r.body as Record<string, unknown>)["error"] ?? "")}`);
        return this.redirect(`/steward/evidence?ok=${encodeURIComponent(String((r.body as Record<string, unknown>)["note"] ?? "Revealed."))}`);
      }
      case "/steward/evidence/reverse": {
        const r = await this.o.v2.reverseFinding(f.get("id") ?? "", steward);
        if (r.status !== 200) return this.page("/steward/evidence", signed, url, null, `Couldn't reverse: ${String((r.body as Record<string, unknown>)["error"] ?? "")}`);
        return this.redirect("/steward/evidence?ok=Finding+reversed.+Everything+it+voided+is+restored.");
      }
      case "/steward/controls/set": {
        const key = f.get("setting") ?? "";
        const value = f.get("value") ?? "";
        const r = await this.o.v2.setSetting(key, value, steward);
        if (r.status !== 200) return this.page("/steward/controls", signed, url, null, `Couldn't change the switch: ${String((r.body as Record<string, unknown>)["error"] ?? "")}`);
        return this.redirect(`/steward/controls?ok=${encodeURIComponent((r.body as Record<string, unknown>)["changed"] ? `${key} is now ${value}; the change is on the log.` : `${key} was already ${value}.`)}`);
      }
      case "/steward/canaries/register": {
        if (!this.o.canaries) return this.html(404, refusedPage("The canary registry is not configured on this deployment."));
        const r = await this.o.canaries.register({ claim: f.get("claim") ?? "", outcome: f.get("outcome") ?? "", label: f.get("label") ?? "", source: f.get("source") ?? "", revealAfter: f.get("revealAfter") }, steward);
        if (!r.ok) return this.page("/steward/canaries", signed, url, null, `Couldn't register: ${r.error}.`);
        return this.redirect("/steward/canaries?ok=Registered.+Nothing+marks+it+on+the+record%3B+reveal+it+from+here+when+the+time+comes.");
      }
      case "/steward/canaries/reveal": {
        if (!this.o.canaries) return this.html(404, refusedPage("The canary registry is not configured on this deployment."));
        const r = await this.o.canaries.reveal(f.get("claim") ?? "", steward);
        if (!r.ok) return this.page("/steward/canaries", signed, url, null, `Couldn't reveal: ${r.error}.`);
        return this.redirect(`/steward/canaries?ok=${encodeURIComponent(r.note)}`);
      }
      case "/steward/canaries/remove": {
        if (!this.o.canaries) return this.html(404, refusedPage("The canary registry is not configured on this deployment."));
        if (!(await this.o.canaries.remove(f.get("claim") ?? ""))) return this.page("/steward/canaries", signed, url, null, "Couldn't remove: not in the registry.");
        return this.redirect("/steward/canaries?ok=Removed+from+the+registry.+The+log+is+untouched.");
      }
      default:
        return this.html(404, refusedPage("There is nothing at that address."));
    }
  }

  private async page(path: string, signed: Signed, url: URL, flash: string | null, problem: string | null): Promise<Response> {
    const r = await this.o.v2.record();
    const csrf = await this.o.accounts.csrf(signed);
    const fresh = this.o.accounts.fresh(signed);
    switch (path) {
      case "/steward": {
        const s = await this.o.v2.scores();
        const operators = new Map<string, string>();
        for (const a of r.agents.values()) operators.set(a.operatorId, r.tiers.get(a.operatorId) ?? "unverified");
        const byTier: Record<string, number> = {};
        for (const t of operators.values()) byTier[t] = (byTier[t] ?? 0) + 1;
        const checks = [...r.checks.values()];
        const all = [...s.claims.values()];
        return this.html(200, overviewPage({
          agents: r.agents.size, retired: [...r.agents.values()].filter((a) => a.revokedAt).length, operators: byTier,
          claims: r.claims.length, external: r.external.size,
          receipts: checks.filter((c) => c.stage === "resulted" && !c.disowned).length, disowned: checks.filter((c) => c.disowned).length,
          findingsOpen: r.findings.filter((f) => !f.reversed && f.verdict === "fabrication" && !f.inForce).length,
          findingsInForce: r.findings.filter((f) => f.inForce).length, voided: r.voidedOperators.size,
          lapses: [...r.lapses.values()].reduce((a, b) => a + b, 0),
          holdsOpen: (await this.o.v2.holds(500)).filter((h) => h.open).length,
          canariesDue: this.o.canaries ? await this.o.canaries.due() : null,
          disputes: all.filter((c) => c.dispute > 0).length,
          queue: all.filter((c) => c.status !== "established" && c.status !== "refuted").sort((a, b) => b.valueOfChecking - a.valueOfChecking).slice(0, 10).map((c) => ({ ref: c.ref, status: c.status, credence: c.credence, use: c.use })),
        }, flash, problem));
      }
      case "/steward/people": {
        const q = (url.searchParams.get("q") ?? "").trim().slice(0, 80);
        const s = await this.o.v2.scores();
        const ops = new Map<string, PersonRow>();
        for (const [handle, a] of r.agents) {
          const row = ops.get(a.operatorId) ?? { operatorId: a.operatorId, tier: r.tiers.get(a.operatorId) ?? "unverified", account: false, agents: [], voided: r.voidedOperators.has(a.operatorId) };
          row.agents.push({ handle, reliability: s.track.reliability.get(handle) ?? 0.5, retired: a.revokedAt !== null });
          ops.set(a.operatorId, row);
        }
        for (const [op, tier] of r.tiers) if (!ops.has(op)) ops.set(op, { operatorId: op, tier, account: false, agents: [], voided: r.voidedOperators.has(op) });
        let rows = [...ops.values()];
        if (q) rows = rows.filter((x) => x.operatorId.includes(q) || x.agents.some((a) => a.handle.toLowerCase().includes(q.toLowerCase())));
        rows = rows.slice(0, 100);
        for (const row of rows) row.account = !!(await this.o.accounts.accountForOperator(row.operatorId));
        return this.html(200, peoplePage({ rows, q, csrf, fresh }, flash, problem));
      }
      case "/steward/evidence": {
        const s = await this.o.v2.scores();
        const findings = [...r.findings].reverse().map((f) => ({ id: f.id, verdict: f.verdict, oddAgent: f.oddAgent, oddOperator: f.oddOperator, decidedAt: f.decidedAt, appealUntil: new Date(Date.parse(f.decidedAt) + APPEAL_MS).toISOString(), inForce: f.inForce, reversed: f.reversed, bundle: f.bundle, seed: f.seed }));
        const disputes = [...s.claims.values()].filter((c) => c.dispute > 0).sort((a, b) => b.disputePriority - a.disputePriority).map((c) => {
          const rs = r.receiptsByClaim.get(c.ref) ?? [];
          return { ref: c.ref, credence: c.credence, dispute: c.dispute, status: c.status, receipts: rs.length, disputedReceipts: rs.filter((x) => (r.checks.get(x.id)?.disputedBy.length ?? 0) > 0).length };
        });
        const anchors = [...r.anchors].map(([claim, confirmed]) => ({ claim, confirmed }));
        return this.html(200, evidencePage({ findings, disputes, anchors, csrf, fresh }, flash, problem));
      }
      case "/steward/canaries": {
        if (!this.o.canaries) return this.html(404, refusedPage("The canary registry is not configured on this deployment."));
        return this.html(200, canariesPage({ rows: await this.o.canaries.list(), csrf, fresh, now: this.now().toISOString() }, flash, problem));
      }
      case "/steward/controls":
        return this.html(200, controlsPage({ switches: await this.o.v2.settingsView(), csrf, fresh, readOnly: !!this.o.readOnly }, flash, problem));
      case "/steward/content":
        return this.html(200, contentPage({ holds: await this.o.v2.holds(100) }, flash, problem));
      case "/steward/audit":
        return this.html(200, auditPage({ rows: await this.o.v2.audit(200) }, flash, problem));
      default:
        return this.html(404, refusedPage("There is nothing at that address."));
    }
  }
}
