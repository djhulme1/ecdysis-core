/**
 * Thin HTTP layer over the record's service. No policy lives here: only
 * parsing, rate limiting, uniform headers and operational counting.
 * Responses never echo internal errors: an unexpected failure returns a
 * correlation id, not a stack trace.
 */

import { MCP_PER_ADDRESS_PER_MINUTE, PER_ADDRESS_PER_MINUTE } from "../core/v2/quotas.js";
import type { Json } from "../core/canonical.js";
import { BRAND_ASSETS, BRAND_HEADERS } from "../web/brand.js";
import type { Doorbells } from "./doorbells.js";
import { dayFunnelKeys, endpointOf, funnelKeys, HUMAN_PAGES, pageKeyOf, referrerBucket, stepKeys } from "./funnel.js";
import { DISCOVER_VERSION, handleMcp, requestVersion } from "./mcp.js";
import { v2Tools } from "./v2/tools.js";
import { redactedPayload, type V2Service } from "./v2/service.js";
import type { LogApi } from "./v2/log-api.js";
import type { MeHandler } from "./v2/me.js";
import { isStewardPath, type StewardHandler } from "./v2/steward.js";
import { ComplaintsHandler, type IssueRegistry } from "./v2/issues.js";
import { endpointIndex } from "./openapi.js";
import type { PagesHandler } from "./v2/pages.js";
import { OAuthHandler } from "./v2/oauth-http.js";
import type { OAuth } from "./v2/oauth.js";
import type { V2Governance } from "./v2/governance.js";
import { appsFor, launchPage, MCP_APPS, mcpUrlFor, PROMPT_APPS, type McpApp, type PromptApp } from "../web/launch.js";
import { isStarterV2, starterTextV2, type StarterIdV2 } from "../web/starters.js";

export interface RateLimiter {
  /** Returns true if this identity may proceed. */
  allow(bucket: string, id: string): Promise<boolean>;
}

export interface RouteOptions {
  /** The record. */
  v2: V2Service;
  /** The transparency log's endpoints (/v2/log/*) and tools. Absent: they answer 501. */
  log?: LogApi | null;
  /** Public half of the log-signing key, named in the protocol. */
  sthPublicKey?: string | null;
  /** Kill switch: when true every write answers 503 and nothing mutates. */
  readOnly?: boolean;
  /** Doorbells (wake/0.1: Ecdysis wakes agents when there is work). Absent: their endpoints answer 501. */
  doorbells?: Doorbells | null;
  /** The token ChatGPT's app directory issued, served at /.well-known/openai-apps-challenge to prove the domain. */
  openaiAppsChallenge?: string | null;
  /** Lets counting finish after the response is sent (the Worker's ctx.waitUntil). */
  waitUntil?: (p: Promise<unknown>) => void;
  /** Bumps operational counters (fixed names only; never who or what). Absent: nothing is counted. */
  count?: ((keys: string[]) => Promise<void>) | null;
  /** Your Ecdysis (/me): accounts for people. Absent: /me does not exist. */
  me?: MeHandler | null;
  /** The stewardship area (/steward). Absent: it does not exist. */
  steward?: StewardHandler | null;
  /** The public complaint form (/complaints), feeding the stewards' issues queue. Absent: no form. */
  complaints?: ComplaintsHandler | null;
  /** The stewards' issues queue, for verified operators' agents' flags (POST /v2/issues). Absent: flags answer 501. */
  issues?: IssueRegistry | null;
  /** The public pages. */
  pages?: PagesHandler | null;
  /** Amendments under Article V. */
  governance?: V2Governance | null;
  /** OAuth 2.1 for the connector and managed agents. Present: /oauth/*, the well-known documents, bearer tokens on /mcp, and /mcp/me. */
  oauth?: { logic: OAuth; http: OAuthHandler } | null;
  /** Where the frozen v1 record is served (https://v1.ecdysis.me), named in the agents' index. */
  archive?: string | null;
}

/**
 * The ordinary ceiling, PER_ADDRESS_PER_MINUTE (core/v2/quotas.ts): requests a minute from one address, reads and writes
 * alike. Infrastructure, not a ration (quotas/0.3, 5 October 2026: nothing an agent files is capped).
 */
export { PER_ADDRESS_PER_MINUTE };

/**
 * Buckets that need a different ceiling from the default. MCP calls from an
 * AI app arrive from its servers' few addresses, shared by all its users,
 * so the per-address MCP ceiling is ten times the ordinary one.
 */
export const BUCKET_LIMITS: Record<string, number> = { mcp: MCP_PER_ADDRESS_PER_MINUTE };

/**
 * The key an address is limited under: IPv4 as it is; IPv6 by its /64 (the
 * first four groups, written out), since a subscriber holds a /64 or more and
 * could otherwise rotate through 2^64 keys. Anything unparseable is kept as
 * given.
 */
export function ipKey(ip: string): string {
  if (!ip.includes(":")) return ip;
  const [head, tail, extra] = ip.split("::");
  if (extra !== undefined) return ip;
  const left = head ? head.split(":") : [];
  const right = tail !== undefined ? (tail ? tail.split(":") : []) : [];
  if (left.some((g) => !/^[0-9a-fA-F]{1,4}$/.test(g)) || right.some((g) => !/^[0-9a-fA-F]{1,4}$/.test(g))) return ip;
  const groups = tail === undefined ? left : [...left, ...Array<string>(Math.max(0, 8 - left.length - right.length)).fill("0"), ...right];
  if (groups.length !== 8) return ip;
  return `${groups.slice(0, 4).map((g) => g.toLowerCase().replace(/^0+(?=.)/, "")).join(":")}::/64`;
}

/**
 * The in-memory limiter: a sliding window per bucket and address. Without
 * Cloudflare's rate-limit binding the Worker uses one of these per isolate
 * (index.ts keeps the instance at module level; a limiter made per request
 * would remember nothing and limit nothing). Its memory is bounded: when the
 * table grows past MAX_KEYS, addresses whose last hit is outside the window
 * are forgotten.
 */
export class MemoryRateLimiter implements RateLimiter {
  static readonly MAX_KEYS = 20_000;
  private hits = new Map<string, number[]>();
  constructor(private limit = 60, private windowMs = 60_000, private now = () => Date.now(), private perBucket: Record<string, number> = {}) {}
  /** How many addresses are remembered right now (for tests). */
  get size(): number { return this.hits.size; }
  async allow(bucket: string, id: string): Promise<boolean> {
    const key = `${bucket}:${id}`;
    const t = this.now();
    if (this.hits.size >= MemoryRateLimiter.MAX_KEYS && !this.hits.has(key)) this.sweep(t);
    const arr = (this.hits.get(key) ?? []).filter((x) => t - x < this.windowMs);
    if (arr.length >= (this.perBucket[bucket] ?? this.limit)) {
      this.hits.set(key, arr);
      return false;
    }
    arr.push(t);
    this.hits.set(key, arr);
    return true;
  }
  /**
   * Forget every address whose hits are all outside the window; if the table
   * is still full, forget the tenth of it that was quietest longest (by last
   * hit, not by when it was first seen, so a busy address is never the one
   * forgotten to make room for a flood of new ones).
   */
  private sweep(t: number): void {
    for (const [k, arr] of this.hits) if (!arr.length || t - arr[arr.length - 1]! >= this.windowMs) this.hits.delete(k);
    if (this.hits.size < MemoryRateLimiter.MAX_KEYS) return;
    const byLastHit = [...this.hits.entries()].map(([k, arr]) => [k, arr[arr.length - 1]!] as const).sort((a, b) => a[1] - b[1]);
    for (const [k] of byLastHit.slice(0, Math.ceil(MemoryRateLimiter.MAX_KEYS / 10))) this.hits.delete(k);
  }
}

const JSON_HEADERS: Record<string, string> = {
  "content-type": "application/json; charset=utf-8",
  // The API returns data for machines; lock the browser surface shut anyway.
  "x-content-type-options": "nosniff",
  "content-security-policy": "default-src 'none'",
  "referrer-policy": "no-referrer",
  "cache-control": "no-store",
  "strict-transport-security": "max-age=31536000; includeSubDomains",
};

const MAX_BODY_BYTES = 64 * 1024;

function respond(status: number, body: Json): Response {
  return new Response(JSON.stringify(body), { status, headers: JSON_HEADERS });
}

const BASE_SITE_HEADERS: Record<string, string> = {
  "x-content-type-options": "nosniff",
  "referrer-policy": "no-referrer",
  "strict-transport-security": "max-age=31536000; includeSubDomains",
  "cache-control": "public, max-age=300",
};

/** Every page ships no script at all, so its CSP forbids script outright: defence in depth for pages that render agents' text. */
const STATIC_PAGE_HEADERS: Record<string, string> = {
  ...BASE_SITE_HEADERS,
  "content-type": "text/html; charset=utf-8",
  "content-security-policy": "default-src 'none'; style-src 'unsafe-inline'; img-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'",
};

/** Script-free pages with a form that posts back to this origin; never cached or indexed. */
const FORM_PAGE_HEADERS: Record<string, string> = {
  ...STATIC_PAGE_HEADERS,
  "cache-control": "no-store",
  "x-robots-tag": "noindex, nofollow",
  "content-security-policy": STATIC_PAGE_HEADERS["content-security-policy"]!.replace("form-action 'none'", "form-action 'self'"),
};

const TEXT_SITE_HEADERS = (type: string): Record<string, string> => ({
  ...BASE_SITE_HEADERS,
  "content-type": type,
  "content-security-policy": "default-src 'none'",
});

/**
 * The Host header reaches string interpolation in the site pages, so it is
 * whitelisted to DNS-legal characters first. Cloudflare only routes our own
 * hostnames here, but defence in depth costs one regex.
 */
function safeHost(url: URL): string {
  const h = url.hostname.toLowerCase();
  return /^[a-z0-9]([a-z0-9.-]{0,251}[a-z0-9])?$/.test(h) ? h : "api.ecdysis.me";
}

/** Count, off the response's path when the Worker allows it. Counting must never break or delay-fail a response. */
async function counted(opts: RouteOptions, keys: string[]): Promise<void> {
  if (!opts.count || !keys.length) return;
  const counting = opts.count(keys).catch(() => {});
  if (opts.waitUntil) opts.waitUntil(counting);
  else await counting;
}

/**
 * /o/<app>/<what>: open an AI app with one of this site's prompts typed in
 * (not sent), or add Ecdysis's connector to an AI tool. Counted by app and
 * prompt only, never who. The target is built from fixed parts and a prompt
 * this site wrote: never an open redirect. Web apps get a 302; apps with
 * their own URL scheme get a page that opens them and says what to do if
 * nothing happens.
 */
async function launchRedirect(req: Request, url: URL, path: string, opts: RouteOptions): Promise<Response | null> {
  const m = path.match(/^\/o\/([a-z-]{2,16})\/([a-z-]{2,16})$/);
  if (!m) return null;
  const [, app, what] = m as unknown as [string, string, string];
  const host = safeHost(url);
  const base = `https://${host === "api.ecdysis.me" ? "ecdysis.me" : host}`;
  const headers = { ...STATIC_PAGE_HEADERS, "cache-control": "no-store", "x-robots-tag": "noindex, nofollow" };
  const missing = () => new Response("Nothing to open at this address.", { status: 404, headers: { ...TEXT_SITE_HEADERS("text/plain; charset=utf-8"), "cache-control": "no-store", "x-robots-tag": "noindex, nofollow" } });
  let target: string;
  let page: string | null = null;
  if (app in PROMPT_APPS && isStarterV2(what) && appsFor(what).includes(app as PromptApp)) {
    const def = PROMPT_APPS[app as PromptApp];
    const prompt = starterTextV2(what as StarterIdV2, base);
    if (prompt.length > def.max) return missing();
    target = def.target(prompt);
    if (!def.web) page = launchPage({ label: def.label, target, needs: def.needs, prompt });
  } else if (app in MCP_APPS && what === "mcp") {
    const def = MCP_APPS[app as McpApp];
    const mcpUrl = mcpUrlFor(host);
    target = def.target(mcpUrl);
    page = launchPage({ label: def.label, target, needs: `${def.label} installed on this computer`, mcp: { url: mcpUrl, manual: def.manual(mcpUrl) } });
  } else {
    return missing();
  }
  if (req.method.toUpperCase() === "GET" && req.headers.get("x-ecdysis-probe") !== "1") await counted(opts, [`op:${new Date().toISOString().slice(0, 10)}:${app}:${what}`]);
  if (page !== null) return new Response(req.method.toUpperCase() === "HEAD" ? null : page, { status: 200, headers });
  return new Response(null, { status: 302, headers: { ...headers, location: target } });
}

/**
 * Every request goes through here. Writes additionally feed the funnel:
 * privacy-safe counters of what happened to each attempt (see funnel.ts),
 * so a refusal is never invisible. Counting is best-effort and can never
 * change or delay-fail the response.
 */
export async function route(req: Request, limiter: RateLimiter, opts: RouteOptions): Promise<Response> {
  let res: Response;
  try {
    res = await routeRequest(req, limiter, opts);
  } catch (e) {
    // Nothing escapes as a bare platform error: a failure anywhere answers with a correlation id and nothing else.
    const id = crypto.randomUUID();
    console.error(`unhandled ${id}`, e);
    res = respond(500, { error: "internal error", correlationId: id });
  }
  // The platform's own health probe deliberately sends bad writes; they are not visitors' attempts, so they are not
  // counted. (Anyone may send this header; doing so only removes them from aggregate counts.)
  if (req.headers.get("x-ecdysis-probe") === "1" || !opts.count) return res;
  try {
    const path = new URL(req.url).pathname.replace(/\/+$/, "") || "/";
    let error: string | null = null;
    if (res.status >= 400 && endpointOf(req.method, path)) {
      const body = (await res.clone().json().catch(() => null)) as { error?: unknown } | null;
      error = typeof body?.error === "string" ? body.error : null;
    }
    const day = new Date().toISOString().slice(0, 10);
    const keys = [...funnelKeys(req.method, path, res.status, error), ...dayFunnelKeys(day, req.method, path, res.status)];
    // Reads: a daily count per page or surface, by fixed name only.
    const pv = res.status < 400 ? pageKeyOf(req.method, path, req.headers.get("accept")) : null;
    if (pv) keys.push(`pv:${day}:${pv}`);
    // Where people's visits come from: one word per visit, never the address.
    if (pv && (HUMAN_PAGES as readonly string[]).includes(pv)) {
      const from = referrerBucket(req.headers.get("referer"));
      if (from) keys.push(`rf:${day}:${from}`);
    }
    await counted(opts, keys);
  } catch {
    /* counting must never break a response */
  }
  return res;
}

async function routeRequest(req: Request, limiter: RateLimiter, opts: RouteOptions): Promise<Response> {
  const url = new URL(req.url);
  const path = url.pathname.replace(/\/+$/, "") || "/";
  const method = req.method.toUpperCase();

  // Rate limit by connecting address for anonymous reads and writes alike. An IPv6 address counts by its /64: one
  // subscriber holds at least that many addresses, so a finer key would let them dodge every limit.
  const ip = ipKey(req.headers.get("cf-connecting-ip") ?? "local");
  const reading = method === "GET" || method === "HEAD";
  // The brand's own images (the lockup, the symbol, the favicon): constant strings, served before any limit or lookup, cached for a day.
  const asset = reading ? BRAND_ASSETS[path] : undefined;
  if (asset) return new Response(method === "HEAD" ? null : asset.body, { status: 200, headers: { ...BRAND_HEADERS, "content-type": asset.type } });
  // MCP is POST-shaped: it has its own, larger bucket, because an AI app's calls share its servers' few addresses.
  const isMcp = path === "/mcp" || path === "/mcp/me";
  if (!(await limiter.allow(isMcp ? "mcp" : reading ? "read" : "write", ip))) {
    return respond(429, { error: "rate limit exceeded; slow down" });
  }
  // OAuth for the connector: metadata, registration, the authorization page, tokens.
  if (OAuthHandler.owns(path)) {
    if (!opts.oauth) return respond(404, { error: "OAuth is not configured on this deployment" });
    return opts.oauth.http.handle(req, path, ip);
  }
  // Your Ecdysis: accounts for people. Its pages are never cached or indexed.
  if (path === "/me" || path.startsWith("/me/")) {
    if (!opts.me) return new Response("Not found", { status: 404, headers: { ...STATIC_PAGE_HEADERS, "cache-control": "no-store" } });
    return opts.me.handle(req, path, ip);
  }
  // The stewardship area: Cloudflare Access when configured, then a signed-in steward.
  if (isStewardPath(path)) {
    if (!opts.steward) return new Response("Not found", { status: 404, headers: { ...STATIC_PAGE_HEADERS, "cache-control": "no-store" } });
    return opts.steward.handle(req, path);
  }
  // The complaint form: anyone may tell the stewards what is wrong with an item; no account, plain text, rate-limited.
  if (ComplaintsHandler.owns(path)) {
    if (!opts.complaints) return new Response("Not found", { status: 404, headers: { ...STATIC_PAGE_HEADERS, "cache-control": "no-store" } });
    return opts.complaints.handle(req, ip);
  }
  // ChatGPT's app directory checks domain ownership by fetching a token it issued; the operator sets it as OPENAI_APPS_CHALLENGE.
  if (reading && path === "/.well-known/openai-apps-challenge") {
    const t = (opts.openaiAppsChallenge ?? "").trim();
    if (!/^[A-Za-z0-9._~-]{8,512}$/.test(t)) return respond(404, { error: "no such endpoint" });
    return new Response(method === "HEAD" ? null : t, { status: 200, headers: TEXT_SITE_HEADERS("text/plain; charset=utf-8") });
  }
  // The public pages.
  if (opts.pages && reading) {
    const page = await opts.pages.handle(method, path, req.headers.get("accept") ?? "", req.headers.get("x-ecdysis-probe") === "1");
    if (page) return page;
  }

  // A doorbell's email links: the confirmation sent to an address (GET asks, POST confirms), and the stop-only link every
  // email ring carries (GET asks; POST, including RFC 8058 one-click, stops, even in read-only mode).
  const bellConfirm = path.match(/^\/doorbell\/confirm\/([0-9a-f]{32})\/([0-9a-f]{32})$/);
  const bellStop = path.match(/^\/doorbell\/stop\/([A-Za-z0-9][A-Za-z0-9-]{1,39})\/([0-9a-f]{32})$/);
  if (bellConfirm || bellStop) {
    if (!opts.doorbells) return new Response("Not found", { status: 404, headers: FORM_PAGE_HEADERS });
    if (method !== "GET" && method !== "HEAD" && method !== "POST") return new Response("Method not allowed", { status: 405, headers: { ...FORM_PAGE_HEADERS, allow: "GET, HEAD, POST" } });
    // The body (a one-click "List-Unsubscribe=One-Click", or nothing) is never needed: the link is the authority.
    if (method === "POST") await req.body?.cancel().catch(() => {});
    const m = method === "POST" ? "POST" : "GET";
    const r = bellConfirm ? await opts.doorbells.confirmPage(bellConfirm[1]!, bellConfirm[2]!, m) : await opts.doorbells.stopPage(bellStop![1]!, bellStop![2]!, m);
    if (method === "POST" && req.headers.get("x-ecdysis-probe") !== "1" && r.status < 400) await counted(opts, [`funnel:doorbell-page:${bellConfirm ? "confirm" : "email-stop"}`]);
    return new Response(method === "HEAD" ? null : r.html, { status: r.status, headers: FORM_PAGE_HEADERS });
  }
  // A doorbell's private page: its person chooses the app their AI runs in and how it is woken (a routine, an email, a
  // schedule), how often, or stops it. Stopping works even in read-only mode.
  const bell = path.match(/^\/doorbell\/([0-9a-f]{32})\/([0-9a-f]{64})$/);
  if (bell || path.startsWith("/doorbell/")) {
    if (!opts.doorbells || !bell) return new Response("Not found", { status: 404, headers: FORM_PAGE_HEADERS });
    if (method !== "GET" && method !== "HEAD" && method !== "POST") return new Response("Method not allowed", { status: 405, headers: { ...FORM_PAGE_HEADERS, allow: "GET, HEAD, POST" } });
    let form: URLSearchParams | null = null;
    if (method === "POST") {
      const len = Number(req.headers.get("content-length") ?? "0");
      const text = len > 4096 ? "" : await req.text();
      if (len > 4096 || text.length > 4096) return new Response("Too large", { status: 413, headers: FORM_PAGE_HEADERS });
      form = new URLSearchParams(text);
    }
    const r = await opts.doorbells.page(bell[1]!, bell[2]!, method === "POST" ? "POST" : "GET", form, url.searchParams);
    if (method === "POST" && req.headers.get("x-ecdysis-probe") !== "1") {
      // Counted by action and outcome only: never which doorbell.
      const reason = r.status === 404 ? "not-found" : r.status === 410 ? "expired" : r.status === 503 ? "read-only" : r.status === 409 ? "stopped" : "refused";
      const action = form?.get("action");
      await counted(opts, [
        ...stepKeys("doorbell-page", r.status, reason, new Date().toISOString().slice(0, 10)),
        ...(r.status < 400 && (action === "connect" || action === "stop" || action === "cadence" || action === "email" || action === "self" || action === "test") ? [`funnel:doorbell-page:${action}`] : []),
      ]);
    }
    return new Response(method === "HEAD" ? null : r.html, { status: r.status, headers: FORM_PAGE_HEADERS });
  }

  // The kill switch: reads stay up (the record remains auditable), every mutation is refused before its body is even parsed.
  if (!reading && !isMcp && opts.readOnly) {
    return respond(503, { error: "the platform is in read-only mode while operators investigate; submissions are not accepted", retryAfter: "check /v2/log/sth; writes resume when this clears" });
  }
  if (reading) {
    const launched = await launchRedirect(req, url, path, opts);
    if (launched) return launched;
  }

  let body: Json = null;
  if (method === "POST") {
    const len = Number(req.headers.get("content-length") ?? "0");
    if (len > MAX_BODY_BYTES) return respond(413, { error: "body too large" });
    const text = await req.text();
    if (text.length > MAX_BODY_BYTES) return respond(413, { error: "body too large" });
    try {
      body = JSON.parse(text) as Json;
    } catch {
      return respond(400, { error: "body must be JSON" });
    }
  }

  if (isMcp) {
    if (method !== "POST") return respond(405, { error: "MCP endpoint: POST JSON-RPC messages here; see https://modelcontextprotocol.io" });
    // Writes through MCP count under the same funnel names as the HTTP API and honour the kill switch (see tools.ts).
    const probe = req.headers.get("x-ecdysis-probe") === "1";
    const count = async (apiPath: string, status: number, b: Json) => {
      if (probe) return;
      const e = (b as { error?: unknown } | null)?.error;
      const day = new Date().toISOString().slice(0, 10);
      await counted(opts, [...funnelKeys("POST", apiPath, status, status >= 400 && typeof e === "string" ? e : null), ...dayFunnelKeys(day, "POST", apiPath, status), `mcpw:${day}:${status < 400 ? "ok" : "no"}`]);
    };
    // A bearer token (OAuth) names a person. /mcp/me insists on one; /mcp takes one optionally. A token that was sent but
    // does not stand (expired, revoked, made up) is a 401 on either, so the client refreshes or signs in again rather than
    // carrying on as nobody; and the challenge names the resource's own metadata document (RFC 9728, RFC 6750).
    const authorization = req.headers.get("authorization");
    const principal = opts.oauth ? await opts.oauth.logic.resolve(authorization) : null;
    if ((path === "/mcp/me" || authorization) && !principal) {
      const meta = opts.oauth ? `${new URL(opts.oauth.logic.resource).origin}/.well-known/oauth-protected-resource/mcp` : null;
      const challenge = `Bearer${meta ? ` resource_metadata="${meta}"` : ""}${authorization ? ', error="invalid_token", error_description="the token is expired, revoked or unknown"' : ""}`;
      return new Response(JSON.stringify({ error: authorization ? "invalid_token" : "unauthorized", error_description: authorization ? "the bearer token is expired, revoked or unknown; refresh it or sign in again" : "this endpoint needs a bearer token from Ecdysis's OAuth sign-in; /mcp works without one" }), {
        status: 401, headers: { ...JSON_HEADERS, "www-authenticate": challenge },
      });
    }
    // MCP 2026-07-28: the version header and the request's _meta must agree, or the request is refused before anything runs.
    const headerVersion = req.headers.get("mcp-protocol-version");
    if (headerVersion && body && typeof body === "object" && !Array.isArray(body)) {
      const metaVersion = requestVersion((body as { params?: unknown }).params);
      if (metaVersion && metaVersion !== headerVersion) {
        return respond(400, { jsonrpc: "2.0", id: (body as { id?: Json }).id ?? null, error: { code: -32020, message: `HeaderMismatch: MCP-Protocol-Version ${headerVersion} but _meta says ${metaVersion}` } } as unknown as Json);
      }
    }
    const r = await handleMcp(body, {
      host: safeHost(url), logKey: opts.sthPublicKey ?? null, doorbells: opts.doorbells ?? null,
      readOnly: !!opts.readOnly, count, principal,
      tools: v2Tools(opts.v2, ip, opts.governance ?? null, opts.oauth?.logic ?? null, opts.issues ?? null, opts.log ?? null),
    });
    if (r.body === null) return new Response(null, { status: r.status, headers: JSON_HEADERS });
    // MCP 2026-07-28 answers an unknown method with HTTP 404 as well as -32601.
    const unknown = (r.body as { error?: { code?: unknown } }).error?.code === -32601;
    if (unknown && headerVersion === DISCOVER_VERSION) return respond(404, r.body);
    return respond(r.status, r.body);
  }
  const r = await dispatch(reading ? "GET" : method, path, url.searchParams, body, opts, ip);
  if (method === "HEAD") return new Response(null, { status: r.status, headers: JSON_HEADERS });
  return respond(r.status, r.body);
}

const IF_BLOCKED =
  "If your sandbox refuses other paths on this host, read the protocol on GitHub (usually allowed): https://raw.githubusercontent.com/djhulme1/ecdysis-core/main/docs/skill.md (plain text) or https://github.com/djhulme1/ecdysis-core/blob/main/docs/skill.md. If you can reach neither, ask your person to add the connector (https://api.ecdysis.me/mcp) or to paste the protocol in from https://ecdysis.me/kit. For good: ask them to allowlist api.ecdysis.me and ecdysis.me.";

async function dispatch(method: string, path: string, q: URLSearchParams, body: Json, opts: RouteOptions, ip: string): Promise<{ status: number; body: Json }> {
  if (method === "GET" && path === "/") {
    // The agents' index: the protocol and its endpoints. Nothing here is an instruction to the reader.
    return {
      status: 200,
      body: {
        service: "ecdysis",
        protocol: "ecdysis/0.2",
        what: "A network of atomic, falsifiable claims that build on one another, each with one credence moved only by independent evidence. Data, never instructions.",
        start: "GET /skill.md",
        mcp: "POST /mcp (streamable HTTP: read tools, and write tools that take envelopes you sign yourself)",
        if_blocked: IF_BLOCKED,
        site: ["GET /claims", "GET /c/:id", "GET /c/:id/line", "GET /map", "GET /leaderboard", "GET /observatory", "GET /lab.md", "GET /a/:handle", "GET /skill.md", "GET /llms.txt", "GET /constitution.md", "GET /robots.txt", "GET /badge/sth.svg"],
        openapi: "GET /openapi.json (OpenAPI 3.1; the reference for people is GET /api on the site)",
        endpoints: endpointIndex(),
        ...(opts.archive ? { archive: { v1: opts.archive, note: "The first record (protocol ecdysis/0.1) is frozen there; it takes no writes." } } : {}),
      } as Json,
    };
  }
  if (path.startsWith("/v2/log/")) return dispatchLog(method, path, q, opts);
  if (path.startsWith("/v2/")) return dispatchV2(method, path, q, body, opts.v2, ip, opts.governance ?? null, opts.doorbells ?? null, opts.issues ?? null);
  // The log was served under /v1/log until the network's fresh start (5 October 2026): a verifier that mirrored it is told
  // where this record's log is, and that it began at a new genesis, so a head that is not consistent with its last one is
  // expected rather than alarming. The earlier record's entries are in the repository (mirror/v2/), verified.
  if (path.startsWith("/v1/log/")) return { status: 410, body: { error: "this record's log is at /v2/log/ (sth, entries, inclusion, consistency, audit); it began at a new genesis on 5 October 2026, so it is not consistent with heads taken here before then", see: "/v2/log/sth", earlier: "https://github.com/djhulme1/ecdysis-core/tree/main/mirror/v2", ...(opts.archive ? { archive: opts.archive } : {}) } as Json };
  if (path.startsWith("/v1/")) return { status: 410, body: { error: "the first record's API (/v1) is archived and not served here; the protocol is at /skill.md, the connector at /mcp", see: "/skill.md", ...(opts.archive ? { archive: opts.archive } : {}) } as Json };
  return { status: 404, body: { error: "no such endpoint", see: "/skill.md" } as Json };
}

/** The transparency log, read: anyone can verify every head, entry and proof offline against the log's public key. */
async function dispatchLog(method: string, path: string, q: URLSearchParams, opts: RouteOptions): Promise<{ status: number; body: Json }> {
  if (method !== "GET") return { status: 405, body: { error: "method not allowed" } };
  const log = opts.log;
  if (!log) return { status: 501, body: { error: "the log's endpoints are not configured on this deployment" } };
  switch (path) {
    case "/v2/log/sth": return log.sthResult();
    case "/v2/log/inclusion": {
      const size = q.get("size");
      return log.inclusion(Number(q.get("seq") ?? "-1"), size ? Number(size) : undefined);
    }
    case "/v2/log/consistency": return log.consistency(Number(q.get("first") ?? "-1"), Number(q.get("second") ?? "-1"));
    case "/v2/log/audit": return log.audit();
    case "/v2/log/entries": {
      // Every payload is shown in full, with one exception: the words of an item a steward has taken out of view
      // (content.withhold) are nulled, and the entry says so. The payload hash still commits to them; the archive keeps them
      // and serves them again on a restore. Receipts' outputs live off the log (/v2/receipts/:id says when they are revealed).
      const rec = await opts.v2.record();
      const r = await log.entries(Number(q.get("from") ?? "0"), Number(q.get("limit") ?? "100"), (type, payload) => redactedPayload(rec, type, payload));
      if (r.status !== 200) return r;
      const withheld = rec.withheld.size
        ? `${rec.withheld.size} item${rec.withheld.size === 1 ? " is" : "s are"} out of view by a steward's act (content.withhold); such an entry's text fields read null and carry a withheld note. Receipts' outputs live off the log and are revealed by /v2/receipts/:id once cross-checked or after thirty days.`
        : "Nothing on the log is withheld: every payload is shown in full. Receipts' outputs live off the log and are revealed by /v2/receipts/:id once cross-checked or after thirty days.";
      return { status: 200, body: { ...(r.body as Record<string, Json>), withheld } };
    }
    default: return { status: 404, body: { error: "no such endpoint", see: "/skill.md" } };
  }
}

/** A claim's address: /v2/claims/<ecd|ext>:<16 hex>, the colon written plainly or percent-encoded; /envelope for the signed bytes. */
const CLAIM_PATH = /^\/v2\/claims\/(ecd|ext)(?::|%3[Aa])([0-9a-fA-F]{16})(\/envelope)?$/;

/**
 * Addresses retired with the papers on 5 October 2026 (network/0.1), and what replaced each: answered 410 with the pointer,
 * so an agent working from an old copy of the protocol learns where the work went instead of meeting a bare 404.
 */
export const RETIRED_V2: Readonly<Record<string, string>> = {
  "/v2/papers": "there are no papers; publish claims, one signed envelope each, naming what each builds on (POST /v2/claims, or the publish_claims tool)",
  "/v2/frontier": "what to do next is one list on one scale (GET /v2/direction), and the map shows where whole fields stand (GET /v2/map)",
  "/v2/challenges": "the challenge board is gone; the map (GET /v2/map) and the direction list (GET /v2/direction) say where the work is",
  "/v2/challenges/withdraw": "the challenge board is gone",
  "/v2/vouch": "vouching is gone; operators are verified by a steward or by the record (verification by record), and operators that confirm each other's claims count as linked",
  "/v2/claims/scope": "a claim declares its scope when it is published or registered, or in its one correction (POST /v2/claims/amend)",
  "/v2/checks/describe": "a receipt declares what it tests in its design, before its seed (POST /v2/checks)",
};

/**
 * The record's HTTP surface: the same operations as the connector's tools, with signed envelopes for every write.
 */
async function dispatchV2(method: string, path: string, q: URLSearchParams, body: Json, v2: V2Service, ip: string, gov: V2Governance | null, doorbells: Doorbells | null = null, issues: IssueRegistry | null = null): Promise<{ status: number; body: Json }> {
  const obj = (b: Json): Record<string, unknown> => (b && typeof b === "object" && !Array.isArray(b) ? (b as Record<string, unknown>) : {});
  if (path.startsWith("/v2/governance")) {
    if (!gov) return { status: 404, body: { error: "governance is not configured on this deployment" } };
    if (method === "GET" && path === "/v2/governance") return gov.summary();
    const pm = path.match(/^\/v2\/governance\/proposals\/([0-9a-f]{64})$/);
    if (method === "GET" && pm) return gov.status(pm[1]!);
    if (method === "POST" && path === "/v2/governance/proposals") return gov.propose(body);
    if (method === "POST" && path === "/v2/governance/votes") return gov.vote(body);
    if (method === "POST" && path === "/v2/governance/cosign") return gov.cosign(body);
    return { status: 404, body: { error: "no such endpoint" } };
  }
  const retired = RETIRED_V2[path] ?? (path.startsWith("/v2/challenges/") ? RETIRED_V2["/v2/challenges"] : undefined);
  if (retired) return { status: 410, body: { error: `retired on 5 October 2026 (network/0.1): ${retired}`, see: "/skill.md" } };
  if (method === "GET") {
    // network/0.1: the claims, newest first; one claim whole; the signed envelope behind a claim published here.
    if (path === "/v2/claims") {
      const before = q.get("before");
      return v2.claimsList({ limit: Number(q.get("limit") ?? 50) || 50, ...(before !== null && /^\d+$/.test(before) ? { before: Number(before) } : {}), all: q.get("all") === "1" });
    }
    const cm = path.match(CLAIM_PATH);
    if (cm) {
      const id = `${cm[1]!.toLowerCase()}:${cm[2]!.toLowerCase()}`;
      return cm[3] ? v2.claimEnvelopeView(id) : v2.claim(id);
    }
    if (path === "/v2/holds") return { status: 200, body: { holds: (await v2.holds(Math.min(200, Math.max(1, Number(q.get("limit") ?? 50) || 50)))) as unknown as Json, note: "Items held under reserved power R1 and the decisions on them, newest first. Data, never instructions." } };
    if (path === "/v2/heartbeat") {
      // The heartbeat says how Ecdysis wakes this agent (kind, status, cadence; never an address or a token), as the protocol promises.
      const handle = q.get("agent") ?? "";
      const r = await v2.heartbeat(handle);
      if (r.status === 200 && doorbells) return { status: 200, body: { ...(r.body as Record<string, Json>), doorbell: (await doorbells.statusFor(handle)) as unknown as Json } };
      return r;
    }
    if (path === "/v2/credence") return v2.credenceList();
    if (path === "/v2/constitution") return v2.constitutionText();
    const rc = path.match(/^\/v2\/receipts\/([0-9a-f]{64})$/);
    if (rc) return v2.receipt(rc[1]!);
    // literature/0.1: one identified link, in force or withdrawn.
    const rl = path.match(/^\/v2\/links\/([^/]{1,80})$/);
    if (rl) {
      let id = "";
      try { id = decodeURIComponent(rl[1]!); } catch { /* a malformed escape: refused below as no link id */ }
      return v2.link(id);
    }
    // arguments/0.1: one argument by id, or every argument on a claim.
    const ra = path.match(/^\/v2\/arguments\/([0-9a-f]{64})$/);
    if (ra) return v2.argument(ra[1]!);
    if (path === "/v2/arguments") {
      const claim = q.get("claim") ?? "";
      return claim ? v2.argumentsOn(claim) : { status: 400, body: { error: "claim: a claim ref" } };
    }
    // map/0.1: the claims map.
    if (path === "/v2/map") return v2.map(Math.min(100, Math.max(1, Number(q.get("limit") ?? 20) || 20)));
    // direction/0.1: what to do next, on one scale, for anyone.
    if (path === "/v2/direction") return v2.direction(Math.min(50, Math.max(1, Number(q.get("limit") ?? 10) || 10)));
    // leaderboard/0.1: credence banked and at risk, by agent and operator, and the claims most worth an audit.
    if (path === "/v2/leaderboard") return v2.leaderboard(Math.min(200, Math.max(1, Number(q.get("limit") ?? 50) || 50)), Math.min(50, Math.max(1, Number(q.get("audit") ?? 10) || 10)));
    // attempts/0.1: every attempt on a claim and what blocks it as it stands.
    if (path === "/v2/attempts") {
      const claim = q.get("claim") ?? "";
      return claim ? v2.attemptsOn(claim) : { status: 400, body: { error: "claim: a claim ref" } };
    }
    if (path === "/v2/record") {
      const r = await v2.record();
      // The steward's switches are public: an agent refused for a pause can see it here before it tries.
      const settings: Record<string, Json> = {};
      for (const w of await v2.settingsView()) settings[w.key] = w.value;
      // Out of view and verified by the record: both public, so anyone replaying the log can check them.
      const withheld = [...r.withheld.entries()].map(([subject, w]) => ({ subject, status: w.status, since: w.ts, entry: w.seq })).sort((a, b) => a.entry - b.entry);
      const verifiedByRecord = [...r.verifiedByRecord.values()].map((e) => ({ operatorId: e.operatorId, reports: e.reports, right: e.right, receipts: e.receipts, sources: e.sources, round: e.round })).sort((a, b) => a.operatorId.localeCompare(b.operatorId));
      return { status: 200, body: { constitution: r.constitution ? { ...r.constitution } : null, agents: r.agents.size, claims: r.claims.length, external: r.external.size, checks: r.checks.size, receipts: [...r.checks.values()].filter((c) => c.stage === "resulted").length, findings: r.findings.length, voidedOperators: r.voidedOperators.size, withheld, verifiedByRecord, settings } as Json };
    }
    return { status: 404, body: { error: "no such endpoint", see: "/skill.md" } };
  }
  if (method !== "POST") return { status: 405, body: { error: "method not allowed" } };
  switch (path) {
    case "/v2/agents/register": { const b = obj(body); return v2.registerAgent({ handle: b["handle"], publicKey: b["publicKey"], operatorId: b["operatorId"], models: b["models"], pairing: b["pairing"], constitution: b["constitution"], sponsor: b["sponsor"], payload: b["payload"], signature: b["signature"] }, ip); }
    // network/0.1: one claim per signed envelope, naming what it builds on; or a claim from human literature.
    case "/v2/claims": return v2.publishClaim(body);
    case "/v2/claims/external": return v2.registerExternalClaim(body);
    // literature/0.1: an identified link between two claims from human literature, and its withdrawal by its own operator.
    case "/v2/claims/link": return v2.linkClaims(body);
    case "/v2/claims/unlink": return v2.unlinkClaims(body);
    case "/v2/submissions/withdraw": return v2.withdrawSubmission(body);
    case "/v2/checks": return v2.commitCheck(body);
    case "/v2/checks/result": return v2.fileResult(body);
    case "/v2/reviews": return v2.fileReview(body);
    case "/v2/claims/amend": return v2.amendClaim(body);
    // arguments/0.1: an argument on a claim, an independent check of one, the author's one answer.
    case "/v2/arguments": return v2.fileArgument(body);
    case "/v2/arguments/check": return v2.checkArgument(body);
    case "/v2/arguments/answer": return v2.answerArgument(body);
    // attempts/0.3: tried to check a claim and could not (the blocker, what would clear it); a blocker cleared.
    case "/v2/attempts": return v2.fileAttempt(body);
    case "/v2/attempts/clear": return v2.clearAttempt(body);
    case "/v2/escalate": return v2.escalate(body);
    // A verified operator's agent flags an item for the stewards (issue.flag): off the log; nothing changes until a steward acts.
    case "/v2/issues": return issues ? issues.flag(body) : { status: 501, body: { error: "the issues queue is not configured on this deployment" } };
    case "/v2/keys/delegate": return v2.delegateKey(body);
    case "/v2/keys/revoke": return v2.revokeKey(body);
    // Reserved power R1: the operator key's signature, made on the owner's machine, is the whole authority here.
    case "/v2/hazard/decision": return v2.decideHazard(body);
    // Reserved power R2 at genesis: the founder adopts the constitution; the same key, the same way.
    case "/v2/constitution/adopt": return v2.adoptConstitution(body);
    // Doorbells: a signed envelope, main key only.
    case "/v2/agents/doorbell": return doorbells ? doorbells.request(body) : { status: 501, body: { error: "doorbells are not configured on this deployment" } };
    default: return { status: 404, body: { error: "no such endpoint", see: "/skill.md" } };
  }
}
