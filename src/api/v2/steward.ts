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
import { ISSUE_LABEL, ISSUES } from "../../core/v2/review.js";
import { agentsPage, auditPage, canariesPage, contentPage, controlsPage, evidencePage, healthPage, overviewPage, peoplePage, refusedPage, reviewPage, type AgentRow, type HealthSwitch, type PersonRow, type ReporterRow } from "../../web/steward.js";

/**
 * The deployment's health, for /steward/health: what the operator console's Health page showed, moved here when v2
 * retired the console. Supplied by the Worker (it reads configuration and operational state no pure module may).
 */
export interface StewardHealth {
  sth(): Promise<Record<string, unknown>>;
  logSize(): Promise<number>;
  ops(key: "cron:last" | "audit:last"): Promise<{ value: unknown; at: string } | null>;
  /** Replays the whole hash chain and Merkle tree (read-only) and records the outcome as audit:last. */
  runAudit(at: string): Promise<{ intact: boolean; problem: string | null; size: number }>;
  switches(): Promise<HealthSwitch[]>;
  /** Attempted writes by route: accepted, refused and why (operational counters, never who). */
  writes(): Promise<Record<string, { accepted: number; refused: number; reasons: Record<string, number> }>>;
}

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
  /** The deployment's health (log, scheduled run, configuration switches), when configured. */
  health?: StewardHealth | null;
}

const MAX_FORM = 8 * 1024;
/** The bulk seed form carries up to 25 briefs of 1500 characters with their quotes and tests, URL-encoded: it has its own ceiling. */
const MAX_SEED_FORM = 96 * 1024;
const SESSION_COOKIE = "ecd_s";

export function isStewardPath(path: string): boolean {
  return /^\/steward(\/|$)/.test(path);
}

/**
 * Reads the seeds a steward pasted into the bulk form, as a phone or a
 * document viewer may have handed them over: a byte-order mark, a Markdown
 * code fence, prose before or after the array, a viewer's line numbers,
 * no-break and zero-width spaces from a rendered page, typographic quotes in
 * place of straight ones. Each repair is tried only after the text fails to
 * parse without it, and the first reading that parses wins, so a clean paste
 * is read exactly as written (curly quotes inside a quoted sentence are the
 * authors' words and stay). When nothing parses, the problem names the JSON
 * engine's reason for the paste as it stood and how many characters arrived,
 * so a paste cut short shows up as one.
 */
export function readSeedPaste(raw: string): { seeds: unknown[] } | { problem: string } {
  const text = raw.replace(/^\uFEFF/, "").trim();
  if (!text) return { problem: "Couldn't read the seeds: the box was empty. Paste a JSON array of {source, quote, test, kind, title, brief, scale, wants}." };
  const attempts: string[] = [];
  const add = (t: string) => { if (t && !attempts.includes(t)) attempts.push(t); };
  const widen = (repair: (t: string) => string) => { for (const t of [...attempts]) add(repair(t)); };
  // As pasted, minus a leading ```json line and a trailing ``` line.
  const unfenced = text.replace(/^```[A-Za-z]*[ \t]*\r?\n?/, "").replace(/\r?\n?[ \t]*```$/, "").trim();
  add(unfenced);
  // The outermost array alone: anything before the first [ or after the last ] is a document's prose, not a seed.
  const open = unfenced.indexOf("["), close = unfenced.lastIndexOf("]");
  if (open >= 0 && close > open) add(unfenced.slice(open, close + 1));
  // A code viewer's line numbers, when every line carries one (a JSON line never begins with a digit).
  widen((t) => t.split(/\r?\n/).every((l) => !l.trim() || /^\s*\d+(\s|$)/.test(l)) ? t.replace(/^\s*\d+(\s|$)/gm, "") : t);
  // A rendered page's spacing: no-break spaces for indentation, zero-width and soft-hyphen characters in the text.
  widen((t) => t.replace(/[\u00A0\u2000-\u200A\u202F\u205F\u3000]/g, " ").replace(/[\u200B-\u200D\u2060\uFEFF\u00AD]/g, ""));
  // Typographic double quotes where JSON wants straight ones (a keyboard's smart punctuation, a word processor): first only
  // where a string delimiter can stand (after [ { , : or before : , } ]), which leaves a quotation inside a sentence alone;
  // then everywhere, for a paste with no quotations inside.
  const curly = /[\u201C\u201D\u201E\u201F\u301D\u301E]/g;
  widen((t) => t.replace(/([[{,:]\s*)[\u201C\u201D\u201E\u201F\u301D\u301E]/g, '$1"').replace(/[\u201C\u201D\u201E\u201F\u301D\u301E](\s*[:,}\]])/g, '"$1'));
  widen((t) => t.replace(curly, '"'));
  let why: string | null = null;
  for (const t of attempts) {
    try {
      const v: unknown = JSON.parse(t);
      return { seeds: Array.isArray(v) ? v : [v] };
    } catch (e) {
      why ??= (e instanceof Error ? e.message : String(e)).replace(/\s+/g, " ").slice(0, 200);
    }
  }
  const cut = /end of JSON input|Unterminated string/i.test(why ?? "") ? ` The text ends before the array closes, so the paste may have been cut short: ${text.length.toLocaleString("en-GB")} characters arrived.` : "";
  return { problem: `Couldn't read the seeds as JSON (${why ?? "not JSON"}).${cut} Paste the whole array of {source, quote, test, kind, title, brief, scale, wants}; a code fence or text around it is ignored.` };
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
    const maxForm = path === "/steward/content/challenge-seed-many" ? MAX_SEED_FORM : MAX_FORM;
    const text = len > maxForm ? "" : await req.text();
    if (len > maxForm || text.length > maxForm) return this.html(413, refusedPage("That form was too large."));
    const f = new URLSearchParams(text);
    if (!(await this.o.accounts.csrfOk(signed, f.get("csrf")))) return this.page("/steward", signed, url, null, "That form had expired. Please try again.");
    // A full audit only reads the log, so it needs no fresh sign-in and stays available in read-only mode.
    if (path === "/steward/health/audit") {
      if (!this.o.health) return this.html(404, refusedPage("Health is not configured on this deployment."));
      const a = await this.o.health.runAudit(this.now().toISOString());
      return a.intact ? this.redirect(`/steward/health?ok=${encodeURIComponent(`Full audit passed: the log is intact over ${a.size.toLocaleString("en-GB")} entries.`)}`) : this.page("/steward/health", signed, url, null, `The audit found a problem: ${a.problem ?? "unspecified"}.`);
    }
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
      case "/steward/content/challenge-seed": {
        // A founding challenge, seeded by this steward under their operator id: screened like any brief, outside the daily quota.
        const r = await this.o.v2.proposeChallengeBySteward(steward, { claim: f.get("claim") ?? "", source: f.get("source") ?? "", quote: f.get("quote") ?? "", test: f.get("test") ?? "", kind: f.get("kind") ?? "", title: f.get("title") ?? "", brief: f.get("brief") ?? "", scale: f.get("scale") ?? "", wants: f.get("wants") ?? "" });
        if (r.status !== 201) {
          const b = r.body as Record<string, unknown>;
          const why = (Array.isArray(b["detail"]) ? b["detail"] : Array.isArray(b["findings"]) ? b["findings"] : []) as string[];
          return this.page("/steward/content", signed, url, null, `Couldn't seed the challenge: ${String(b["error"] ?? "")}${why.length ? ` (${why.join("; ")})` : ""}.`);
        }
        return this.redirect(`/steward/content?ok=${encodeURIComponent("Founding challenge seeded. It is on the board under your operator id, named as a steward's seed.")}`);
      }
      case "/steward/content/challenge-seed-many": {
        // Several founding challenges in one act: a JSON array pasted into the form, each seeded as above; the reply says which went on.
        const read = readSeedPaste(f.get("seeds") ?? "");
        if ("problem" in read) return this.page("/steward/content", signed, url, null, read.problem);
        const seeds = read.seeds;
        if (seeds.length === 0 || seeds.length > 25) return this.page("/steward/content", signed, url, null, `Couldn't read the seeds: a JSON array of 1 to 25 objects (${seeds.length} arrived).`);
        const outcomes: string[] = [];
        let seeded = 0;
        for (const [i, raw] of seeds.entries()) {
          const x = (raw && typeof raw === "object" ? raw : {}) as Record<string, unknown>;
          const r = await this.o.v2.proposeChallengeBySteward(steward, { claim: typeof x["claim"] === "string" ? x["claim"] : "", source: x["source"] ?? "", quote: x["quote"] ?? "", test: x["test"] ?? "", kind: x["kind"] ?? "", title: x["title"] ?? "", brief: x["brief"] ?? "", scale: x["scale"] ?? "", wants: x["wants"] ?? "" });
          const b = r.body as Record<string, unknown>;
          if (r.status === 201) { seeded++; outcomes.push(`${i + 1}: seeded ${String(b["id"])}`); }
          else { const why = (Array.isArray(b["detail"]) ? b["detail"] : Array.isArray(b["findings"]) ? b["findings"] : []) as string[]; outcomes.push(`${i + 1}: ${r.status} ${String(b["error"] ?? "")}${why.length ? ` (${why.join("; ")})` : ""}`); }
        }
        const summary = `${seeded} of ${seeds.length} seeded. ${outcomes.join(" · ")}`;
        return seeded === seeds.length ? this.redirect(`/steward/content?ok=${encodeURIComponent(summary.slice(0, 1500))}`) : this.page("/steward/content", signed, url, seeded ? summary.slice(0, 1500) : null, seeded ? null : summary.slice(0, 1500));
      }
      case "/steward/content/challenge-withdraw": {
        const r = await this.o.v2.withdrawChallengeBySteward(f.get("id") ?? "", f.get("reason") ?? "", steward);
        if (r.status !== 200) return this.page("/steward/content", signed, url, null, `Couldn't withdraw: ${String((r.body as Record<string, unknown>)["error"] ?? "")}`);
        return this.redirect("/steward/content?ok=Challenge+withdrawn%3B+the+reason+is+on+the+log+under+your+operator+id.");
      }
      // review/0.1: put an item under review, keep it, withdraw it from view, or correct its claim's test.
      case "/steward/review/report": {
        const r = await this.o.v2.reportBySteward((f.get("subject") ?? "").trim(), f.get("issue") ?? "", f.get("note") ?? "", steward);
        if (r.status !== 202) return this.page("/steward/review", signed, url, null, `Couldn't put it under review: ${String((r.body as Record<string, unknown>)["error"] ?? "")}`);
        const b = r.body as Record<string, unknown>;
        return this.redirect(`/steward/review?ok=${encodeURIComponent(b["hidden"] ? "Under review, and held out of view until a steward decides." : "Under review: it carries a banner until a steward decides.")}`);
      }
      case "/steward/review/withdraw": {
        const r = await this.o.v2.withdrawContent((f.get("subject") ?? "").trim(), f.get("issue") ?? "", f.get("note") ?? "", steward);
        if (r.status !== 200) return this.page("/steward/review", signed, url, null, `Couldn't withdraw it: ${String((r.body as Record<string, unknown>)["error"] ?? "")}`);
        return this.redirect(`/steward/review?ok=${encodeURIComponent("Withdrawn from view, with your note on its page and on the log. Restore it below if this was a mistake.")}`);
      }
      case "/steward/review/restore": {
        const r = await this.o.v2.restoreContent((f.get("subject") ?? "").trim(), f.get("note") ?? "", steward);
        if (r.status !== 200) return this.page("/steward/review", signed, url, null, `Couldn't restore it: ${String((r.body as Record<string, unknown>)["error"] ?? "")}`);
        return this.redirect(`/steward/review?ok=${encodeURIComponent(String((r.body as Record<string, unknown>)["note"] ?? "Done."))}`);
      }
      case "/steward/review/correct": {
        const r = await this.o.v2.correctClaimBySteward((f.get("claim") ?? "").trim(), f.get("test") ?? "", f.get("kind") ?? "", f.get("reason") ?? "", steward);
        if (r.status !== 200) {
          const b = r.body as Record<string, unknown>;
          const why = (Array.isArray(b["detail"]) ? b["detail"] : Array.isArray(b["findings"]) ? b["findings"] : []) as string[];
          return this.page("/steward/review", signed, url, null, `Couldn't correct it: ${String(b["error"] ?? "")}${why.length ? ` (${why.join("; ")})` : ""}`);
        }
        return this.redirect(`/steward/review?ok=${encodeURIComponent("Corrected. The old test stays on the log and on the claim's page; reports that the test was unfair are closed as answered.")}`);
      }
      case "/steward/canaries/register": {
        if (!this.o.canaries) return this.html(404, refusedPage("The canary registry is not configured on this deployment."));
        const r = await this.o.canaries.register({ claim: f.get("claim") ?? "", outcome: f.get("outcome") ?? "", label: f.get("label") ?? "", source: f.get("source") ?? "", revealAfter: f.get("revealAfter") }, steward);
        if (!r.ok) return this.page("/steward/canaries", signed, url, null, `Couldn't register: ${r.error}.`);
        return this.redirect("/steward/canaries?ok=Registered.+Nothing+marks+it+on+the+record%3B+reveal+it+from+here+when+the+time+comes.");
      }
      case "/steward/canaries/reveal": {
        if (!this.o.canaries) return this.html(404, refusedPage("The canary registry is not configured on this deployment."));
        const r = await this.o.canaries.reveal(f.get("key") ?? "", steward);
        if (!r.ok) return this.page("/steward/canaries", signed, url, null, `Couldn't reveal: ${r.error}.`);
        return this.redirect(`/steward/canaries?ok=${encodeURIComponent(r.note)}`);
      }
      case "/steward/canaries/remove": {
        if (!this.o.canaries) return this.html(404, refusedPage("The canary registry is not configured on this deployment."));
        if (!(await this.o.canaries.remove(f.get("key") ?? ""))) return this.page("/steward/canaries", signed, url, null, "Couldn't remove: not in the registry.");
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
    // Shown at the top of every page: who is signed in, in steward mode.
    const who = await this.o.accounts.emailOf(signed.account);
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
          review: { open: [...r.review.values()].filter((x) => x.pending).length, hidden: [...r.review.values()].filter((x) => x.hidden).length, withdrawn: [...r.review.values()].filter((x) => x.withdrawn).length },
          canariesDue: this.o.canaries ? await this.o.canaries.due() : null,
          disputes: all.filter((c) => c.dispute > 0).length,
          queue: all.filter((c) => c.status !== "established" && c.status !== "refuted").sort((a, b) => b.valueOfChecking - a.valueOfChecking).slice(0, 10).map((c) => ({ ref: c.ref, status: c.status, credence: c.credence, use: c.use })),
        }, flash, problem, who));
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
        return this.html(200, peoplePage({ rows, q, csrf, fresh }, flash, problem, who));
      }
      case "/steward/agents": {
        const q = (url.searchParams.get("q") ?? "").trim().slice(0, 80).toLowerCase();
        const only = url.searchParams.get("only") ?? "";
        const s = await this.o.v2.scores();
        const checks = [...r.checks.values()];
        let rows: AgentRow[] = [...r.agents.entries()].map(([handle, a]) => ({
          handle, operatorId: a.operatorId, tier: r.tiers.get(a.operatorId) ?? "unverified", families: a.families, managed: a.managed,
          retired: a.revokedAt !== null, voided: r.voidedOperators.has(a.operatorId), lapses: r.lapses.get(handle) ?? 0,
          reliability: s.track.reliability.get(handle) ?? 0.5, checkKeys: a.checkKeys.length,
          papers: [...r.papers.values()].filter((p) => p.handle === handle).length,
          receipts: checks.filter((c) => c.handle === handle && c.stage === "resulted" && !c.disowned).length,
          owed: checks.filter((c) => c.handle === handle && c.stage === "sealed" && !c.disowned).length,
          constitution: a.constitution,
        })).sort((x, y) => x.handle.localeCompare(y.handle));
        if (q) rows = rows.filter((x) => x.handle.toLowerCase().includes(q) || x.operatorId.toLowerCase().includes(q) || x.families.some((f) => f.toLowerCase().includes(q)));
        if (only === "managed") rows = rows.filter((x) => x.managed);
        else if (only === "voided") rows = rows.filter((x) => x.voided);
        else if (only === "retired") rows = rows.filter((x) => x.retired);
        else if (only === "lapsed") rows = rows.filter((x) => x.lapses > 0);
        else if (only === "owing") rows = rows.filter((x) => x.owed > 0);
        const families: Record<string, number> = {};
        for (const a of r.agents.values()) for (const f of a.families.length ? a.families : ["undeclared"]) families[f] = (families[f] ?? 0) + 1;
        return this.html(200, agentsPage({ rows: rows.slice(0, 200), total: r.agents.size, q, only, families }, flash, problem, who));
      }
      case "/steward/evidence": {
        const s = await this.o.v2.scores();
        const findings = [...r.findings].reverse().map((f) => ({ id: f.id, verdict: f.verdict, oddAgent: f.oddAgent, oddOperator: f.oddOperator, decidedAt: f.decidedAt, appealUntil: new Date(Date.parse(f.decidedAt) + APPEAL_MS).toISOString(), inForce: f.inForce, reversed: f.reversed, bundle: f.bundle, seed: f.seed }));
        const disputes = [...s.claims.values()].filter((c) => c.dispute > 0).sort((a, b) => b.disputePriority - a.disputePriority).map((c) => {
          const rs = r.receiptsByClaim.get(c.ref) ?? [];
          return { ref: c.ref, credence: c.credence, dispute: c.dispute, status: c.status, receipts: rs.length, disputedReceipts: rs.filter((x) => (r.checks.get(x.id)?.disputedBy.length ?? 0) > 0).length };
        });
        const anchors = [...r.anchors].map(([claim, confirmed]) => ({ claim, confirmed }));
        return this.html(200, evidencePage({ findings, disputes, anchors, csrf, fresh }, flash, problem, who));
      }
      case "/steward/canaries": {
        if (!this.o.canaries) return this.html(404, refusedPage("The canary registry is not configured on this deployment."));
        return this.html(200, canariesPage({ rows: await this.o.canaries.list(), csrf, fresh, now: this.now().toISOString() }, flash, problem, who));
      }
      case "/steward/controls":
        return this.html(200, controlsPage({ switches: await this.o.v2.settingsView(), csrf, fresh, readOnly: !!this.o.readOnly }, flash, problem, who));
      case "/steward/content": {
        const board = (await this.o.v2.challenges(200, true)).body as { challenges: Array<{ id: string; title: string; claim: string; status: string; proposedAt: string; page: string; proposer: { kind: string; handle?: string; operatorId: string }; withdrawn: { at: string; by: string; reason: string } | null }> };
        const challenges = board.challenges.map((c) => ({ id: c.id, title: c.title, claim: c.claim, status: c.status, proposedAt: c.proposedAt, page: c.page, withdrawn: c.withdrawn, proposer: c.proposer.kind === "agent" ? `agent ${c.proposer.handle ?? ""} (${c.proposer.operatorId})` : c.proposer.kind === "steward" ? `steward ${c.proposer.operatorId} (founding)` : `person ${c.proposer.operatorId}` }));
        return this.html(200, contentPage({ holds: await this.o.v2.holds(100), challenges, csrf, fresh }, flash, problem, who));
      }
      case "/steward/review": {
        const items = await this.o.v2.reviewQueue(300);
        const reporters = new Map<string, ReporterRow>();
        for (const st of r.review.values()) for (const x of st.reports) {
          if (x.by !== "agent" || x.conflicted) continue;
          const row = reporters.get(x.operatorId) ?? { operatorId: x.operatorId, tier: r.tiers.get(x.operatorId) ?? "unverified", open: 0, upheld: 0, dismissed: 0 };
          if (x.open) row.open++; else if (x.closedAs === "restored") row.dismissed++; else row.upheld++;
          reporters.set(x.operatorId, row);
        }
        return this.html(200, reviewPage({
          open: items.filter((x) => x.state === "under review" || x.state === "held out of view" || x.state === "reported to the stewards"),
          r1: items.filter((x) => x.state === "held under R1"),
          withdrawn: items.filter((x) => x.state === "withdrawn"),
          closed: items.filter((x) => x.state === "closed").slice(0, 30),
          reporters: [...reporters.values()].sort((a, b) => b.open + b.upheld + b.dismissed - (a.open + a.upheld + a.dismissed)),
          issues: ISSUES.map((i) => [i, ISSUE_LABEL[i]] as const), csrf, fresh, now: this.now().toISOString(),
        }, flash, problem, who));
      }
      case "/steward/health": {
        const h = this.o.health;
        if (!h) return this.html(404, refusedPage("Health is not configured on this deployment."));
        const sth = await h.sth();
        const audit = await h.ops("audit:last");
        const cron = await h.ops("cron:last");
        const av = (audit?.value ?? {}) as Record<string, unknown>;
        const cv = (cron?.value ?? {}) as Record<string, unknown>;
        // The run's own counts, by the names the v2 record uses; a v1-only count is left out.
        const COUNTS: ReadonlyArray<readonly [string, string]> = [
          ["v2Lapsed", "checks lapsed"], ["v2Sealed", "seals completed"], ["v2AlertsSent", "alerts sent"], ["v2DigestsSent", "digests sent"],
          ["doorbellsRung", "doorbells rung"], ["doorbellsFailed", "doorbells failed"], ["doorbellsPaused", "doorbells paused"], ["doorbellsWaiting", "doorbells waiting"], ["purged", "stale signups erased"],
        ];
        const writes = Object.entries(await h.writes()).map(([route, w]) => ({ route, accepted: w.accepted, refused: w.refused, reasons: Object.entries(w.reasons).sort((a, b) => b[1] - a[1]).slice(0, 3) as Array<readonly [string, number]> })).sort((a, b) => b.accepted + b.refused - (a.accepted + a.refused));
        return this.html(200, healthPage({
          logSize: await h.logSize(), rootHash: String(sth["rootHash"] ?? ""), treeAt: String(sth["timestamp"] ?? ""), signed: !!sth["signature"],
          audit: audit ? { at: audit.at, intact: av["intact"] === true, size: typeof av["size"] === "number" ? (av["size"] as number) : null, problem: typeof av["problem"] === "string" ? (av["problem"] as string) : null } : null,
          cron: cron ? { at: cron.at, ok: cv["ok"] !== false, error: typeof cv["error"] === "string" ? (cv["error"] as string) : null, counts: COUNTS.filter(([k]) => typeof cv[k] === "number").map(([k, label]) => [label, cv[k] as number] as const) } : null,
          switches: await h.switches(), writes, now: this.now().toISOString(), csrf,
        }, flash, problem, who));
      }
      case "/steward/audit":
        return this.html(200, auditPage({ rows: await this.o.v2.audit(200) }, flash, problem, who));
      default:
        return this.html(404, refusedPage("There is nothing at that address."));
    }
  }
}
