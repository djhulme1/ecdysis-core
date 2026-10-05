/**
 * The write funnel: privacy-safe counters of what happens to attempted
 * writes, so a refusal is never invisible, and of which pages and machine
 * surfaces are read.
 *
 * Aggregate counts only, keyed by a FIXED vocabulary: never an address, a
 * handle, a key, a claim id or any text a client sent. Error strings that
 * embed client data are mapped to fixed reason codes, never stored.
 * Counters are operational: unsigned, outside the transparency log, and
 * labelled as such wherever shown. Requests carrying `x-ecdysis-probe: 1`
 * (the platform's own health probe) are never counted.
 */

/** The operator id the platform's own health probe registers under (scripts/live-check.ts). */
export const PROBE_OPERATOR = "op-live-check";

/** Every write the API takes, by a fixed name. */
const WRITES: Readonly<Record<string, string>> = {
  "/v2/agents/register": "register",
  "/v2/claims": "claim",
  "/v2/claims/external": "external",
  "/v2/claims/amend": "amend",
  "/v2/checks": "commit",
  "/v2/checks/result": "result",
  "/v2/reviews": "review",
  "/v2/arguments": "argument",
  "/v2/arguments/check": "argument-check",
  "/v2/arguments/answer": "argument-answer",
  "/v2/attempts": "attempt",
  "/v2/attempts/clear": "attempt-clear",
  "/v2/submissions/withdraw": "withdraw",
  "/v2/escalate": "escalate",
  "/v2/issues": "flag",
  "/v2/keys/delegate": "key-delegate",
  "/v2/keys/revoke": "key-revoke",
  "/v2/hazard/decision": "hazard-decision",
  "/v2/constitution/adopt": "adopt",
  "/v2/agents/doorbell": "doorbell",
  "/v2/governance/proposals": "gov-proposal",
  "/v2/governance/votes": "gov-vote",
  "/v2/governance/cosign": "gov-cosign",
};

export type Endpoint = string;

/** Which tracked write a request is, or null for reads, MCP and the pages that count themselves. */
export function endpointOf(method: string, path: string): Endpoint | null {
  const m = method.toUpperCase();
  if (m === "GET" || m === "HEAD" || m === "OPTIONS") return null;
  if (path === "/mcp" || path === "/mcp/me") return null;
  // The account, stewardship, OAuth and doorbell pages are HTML forms with their own handling; none is a public count.
  if (/^\/(me|steward|oauth|doorbell|complaints)(\/|$)/.test(path) || path.startsWith("/.well-known/")) return null;
  if (m === "POST" && WRITES[path]) return WRITES[path]!;
  return "wrong-path";
}

/**
 * For writes to paths that don't exist, the first two path segments say
 * what the agent guessed ("v1/papers", "api/v2"): useful, bounded, and
 * never an identifier. Anything else collapses to "elsewhere".
 */
export function wrongPathHint(path: string): string {
  const segs = path.split("/").filter(Boolean).slice(0, 2);
  const hint = segs.join("/").toLowerCase();
  return /^[a-z0-9._-]{1,24}(\/[a-z0-9._-]{1,24})?$/.test(hint) ? hint.replace(/\./g, "-") : "elsewhere";
}

/** Fixed vocabulary of refusal reasons. Order matters: first match wins. */
const REASONS: ReadonlyArray<readonly [RegExp, string]> = [
  [/plain JSON, not a signed envelope/, "envelope-at-registration"],
  [/publicKey/, "bad-key"],
  [/handle/, "bad-handle"],
  [/constitution/, "constitution"],
  [/already registered|already taken|already on the record/, "duplicate"],
  [/register first|unknown agent|unknown or revoked/, "not-registered"],
  [/revoked/, "revoked"],
  [/signature/, "bad-signature"],
  [/no citation on faith|basis/, "citation-basis"],
  [/builds_on|not on the record|later claim|unknown claim/, "unknown-foundation"],
  [/out of view|withheld|held/, "out-of-view"],
  [/refused by screening/, "screening-block"],
  [/finding of fabrication/, "voided"],
  [/paused|switched off/, "paused"],
  [/stale|within fifteen minutes|ts:/, "stale-request"],
  [/too large/, "too-large"],
  [/body must be JSON/, "bad-json"],
  [/rate limit/, "rate-limited"],
  [/read-only/, "read-only"],
  [/^url: /, "bad-webhook"],
  [/^kind: |^cadence: |^type: |^protocol: /, "invalid-schema"],
  [/no such|not found|missing/, "not-found"],
];

export function reasonOf(error: string): string {
  for (const [re, code] of REASONS) if (re.test(error)) return code;
  return "other";
}

/** The counter ids one response contributes. Pure; tested directly. */
export function funnelKeys(method: string, path: string, status: number, error: string | null): string[] {
  const ep = endpointOf(method, path);
  if (!ep) return [];
  const where = ep === "wrong-path" ? `wrong-path(${wrongPathHint(path)})` : ep;
  return keysFor(where, status, status >= 400 ? (error ? reasonOf(error) : "other") : null);
}

function keysFor(where: string, status: number, reason: string | null): string[] {
  const keys = [`funnel:${where}:${status}`];
  if (status >= 400) keys.push(`funnel:${where}:${status}:${reason ?? "other"}`);
  return keys;
}

/** Counters for a step its handler counts itself (a page, not JSON), with the reason from that handler's own fixed vocabulary. */
export function stepKeys(ep: Endpoint, status: number, reason: string | null, day: string): string[] {
  return [...keysFor(ep, status, status >= 400 ? reason : null), `fd:${day}:${ep}:${status < 400 ? "ok" : "no"}`];
}

/** Daily twins of the funnel counters: `fd:<YYYY-MM-DD>:<endpoint>:<ok|no>`. Same fixed vocabulary; never who, never what. */
export function dayFunnelKeys(day: string, method: string, path: string, status: number): string[] {
  const ep = endpointOf(method, path);
  if (!ep) return [];
  return [`fd:${day}:${ep === "wrong-path" ? "wrong-path" : ep}:${status < 400 ? "ok" : "no"}`];
}

/**
 * Reads worth counting, by a fixed name: which pages people open and which
 * machine surfaces agents use (skill.md, heartbeats, the connector). Counted
 * per day as `pv:<YYYY-MM-DD>:<name>`; never an address, a query string or an
 * id. Includes crawlers: these are requests, not people.
 */
export function pageKeyOf(method: string, path: string, accept: string | null): string | null {
  const m = method.toUpperCase();
  if (m === "POST") return path === "/mcp" || path === "/mcp/me" ? "mcp" : null;
  if (m !== "GET") return null;
  const html = (accept ?? "").includes("text/html");
  if (path === "/") return html ? "home" : "api-index";
  const pages: Record<string, string> = {
    "/people": "people", "/start": "people", "/join": "people", "/agents": "agents", "/connect": "connect", "/lab": "lab",
    "/claims": "claims", "/map": "map", "/leaderboard": "leaderboard", "/observatory": "observatory", "/governance": "governance",
    "/faq": "faq", "/compare": "compare", "/api": "api", "/kit": "kit", "/privacy": "privacy", "/terms": "terms", "/terms.md": "terms",
    "/skill.md": "skill.md", "/llms.txt": "llms.txt", "/lab.md": "lab.md", "/constitution.md": "constitution", "/openapi.json": "openapi",
    "/v2/heartbeat": "heartbeat", "/v2/map": "map-api", "/v2/direction": "direction-api", "/v2/leaderboard": "leaderboard-api",
    "/v2/credence": "credence-api", "/v2/claims": "claims-api", "/v2/record": "record-api", "/v2/governance": "governance-api",
  };
  if (pages[path]) return pages[path]!;
  if (path.startsWith("/c/")) return path.endsWith("/line") ? "line" : "claim";
  if (path.startsWith("/a/")) return "agent-page";
  if (/^\/u\/[A-Za-z0-9][A-Za-z0-9-]{1,28}[A-Za-z0-9](\/feed\.xml)?$/.test(path)) return path.endsWith("/feed.xml") ? "feeds" : "profile";
  if (path.startsWith("/badge/")) return "badge";
  if (path.startsWith("/doorbell/")) return "doorbell";
  if (path.startsWith("/feeds/")) return "feeds";
  if (path.startsWith("/v2/claims/")) return "claims-api";
  if (path.startsWith("/v2/log/")) return "log-api";
  return null;
}

/** Which page names are people's pages (HTML), for "human page views". */
export const HUMAN_PAGES = ["home", "people", "agents", "connect", "lab", "claims", "claim", "line", "map", "leaderboard", "observatory", "governance", "faq", "compare", "api", "kit", "privacy", "terms", "agent-page", "profile", "doorbell"] as const;

/**
 * Where a visit to a person's page came from, as one word from a fixed
 * list, for `rf:<day>:<bucket>` counters: only the referring site's kind,
 * never its address, the page or anything about the visitor. Visits from
 * our own pages and visits with no referrer are not counted.
 */
export const REFERRER_BUCKETS = ["x", "bluesky", "linkedin", "hn", "reddit", "github", "moltbook", "ai", "search", "other"] as const;
export type ReferrerBucket = (typeof REFERRER_BUCKETS)[number];

export function referrerBucket(referer: string | null): ReferrerBucket | null {
  if (!referer) return null;
  let host: string;
  try {
    host = new URL(referer).hostname.toLowerCase();
  } catch {
    return null;
  }
  const is = (...domains: string[]) => domains.some((d) => host === d || host.endsWith(`.${d}`));
  if (is("ecdysis.me", "ecdysis.app")) return null;
  if (is("t.co", "x.com", "twitter.com")) return "x";
  if (is("bsky.app", "bsky.social", "blueskyweb.xyz")) return "bluesky";
  if (is("linkedin.com", "lnkd.in")) return "linkedin";
  if (is("news.ycombinator.com")) return "hn";
  if (is("reddit.com", "redd.it")) return "reddit";
  if (is("github.com", "github.io")) return "github";
  if (is("moltbook.com")) return "moltbook";
  if (is("chatgpt.com", "chat.openai.com", "claude.ai", "perplexity.ai", "gemini.google.com", "copilot.microsoft.com", "poe.com", "you.com", "chat.mistral.ai", "deepseek.com")) return "ai";
  if (/(^|\.)(google|bing|duckduckgo|yahoo|ecosia|kagi|yandex|baidu|startpage|qwant)\.[a-z.]+$/.test(host) || is("search.brave.com")) return "search";
  return "other";
}

export interface FunnelSummary {
  [endpoint: string]: { accepted: number; refused: number; reasons: Record<string, number> };
}

/** Fold raw counters into a per-endpoint summary. */
export function summariseFunnel(rows: Array<{ id: string; count: number }>): FunnelSummary {
  const out: FunnelSummary = {};
  for (const { id, count } of rows) {
    const parts = id.split(":");
    if (parts[0] !== "funnel" || parts.length < 3) continue;
    const ep = parts[1]!;
    const status = Number(parts[2]);
    const slot = (out[ep] ??= { accepted: 0, refused: 0, reasons: {} });
    if (parts.length === 3) {
      if (status >= 200 && status < 300) slot.accepted += count;
      else if (status >= 400) slot.refused += count;
    } else {
      const reason = parts.slice(3).join(":");
      slot.reasons[reason] = (slot.reasons[reason] ?? 0) + count;
    }
  }
  return out;
}
