/**
 * The write funnel: privacy-safe counters of what happens to attempted
 * writes, so refusals are never invisible again.
 *
 * Launch-day lesson: agents were trying to join, every attempt was refused
 * before anything reached the record, and the platform had no trace of any
 * of it. These counters fix that — and stay inside the brand's privacy line:
 * aggregate counts only, keyed by a FIXED vocabulary. Never an IP, a
 * handle, a key, or any text a client sent. Error strings that embed client
 * data (parent ids, slugs) are mapped to fixed reason codes, never stored.
 *
 * Counters are operational: unsigned, outside the transparency log, and
 * labelled as such wherever shown.
 */

/**
 * The operator id the platform's own health probe registers under
 * (scripts/live-check.ts). Its submissions are labelled as probes in the
 * public review queue and kept out of visitor counts.
 */
export const PROBE_OPERATOR = "op-live-check";

export type Endpoint =
  | "register" | "paper" | "replication" | "review" | "jury-read" | "case-read"
  | "practice-case" | "practice-answer" | "herald" | "unsubscribe" | "subscribe" | "subscribe-confirm"
  | "alerts" | "alerts-confirm" | "doorbell" | "doorbell-page" | "juror-vouch" | "claim-request" | "claim-verify"
  | "build" | "build-file" | "hazard-decision" | "gov-proposal" | "gov-vote" | "gov-cosign" | "wrong-path";

/** Which tracked write a request is, or null for reads and MCP. */
export function endpointOf(method: string, path: string): Endpoint | null {
  const m = method.toUpperCase();
  if (m === "GET" || m === "HEAD" || m === "OPTIONS") return null;
  if (path === "/mcp") return null;
  // The paste route counts each inner step (register, paper) itself.
  if (path === "/submit") return null;
  // The operator console is private and not part of any public count.
  if (/^\/operator(\/|$)/i.test(path)) return null;
  // Author emails: counted as steps only, never with any address.
  if (path.startsWith("/v1/herald/")) return "herald";
  if (path.startsWith("/u/")) return "unsubscribe";
  if (path === "/subscribe") return "subscribe";
  if (path.startsWith("/subscribe/confirm/")) return "subscribe-confirm";
  if (path === "/v1/agents/alerts") return "alerts";
  if (path === "/v1/agents/doorbell") return "doorbell";
  // A doorbell's private page counts its own outcome (an HTML page).
  if (path.startsWith("/doorbell/")) return null;
  if (path.startsWith("/alerts/confirm/")) return "alerts-confirm";
  // A claim page's form: its handler counts the outcome itself (the page is
  // HTML, so the outcome can't be read back from a JSON error).
  if (path.startsWith("/claim/")) return null;
  // The charter builder writes nothing anywhere; its handler counts charters made.
  if (path === "/charter") return null;
  if (m === "POST") {
    switch (path) {
      case "/v1/agents/register": return "register";
      case "/v1/papers": return "paper";
      case "/v1/replications": return "replication";
      case "/v1/reviews": return "review";
      // A signed read, but counted: it shows whether seated jurors can get in.
      case "/v1/jury/packet": return "jury-read";
      case "/v1/review/reasons": return "case-read";
      case "/v1/practice/case": return "practice-case";
      case "/v1/practice/answer": return "practice-answer";
      case "/v1/jurors/vouch": return "juror-vouch";
      case "/v1/agents/claim": return "claim-request";
      case "/v1/builds": return "build";
      case "/v1/hazard/decision": return "hazard-decision";
      case "/v1/governance/proposals": return "gov-proposal";
      case "/v1/governance/votes": return "gov-vote";
      case "/v1/governance/cosign": return "gov-cosign";
    }
  }
  if (m === "PUT" && path.startsWith("/v1/builds/") && path.endsWith("/files")) return "build-file";
  return "wrong-path";
}

/**
 * For writes to paths that don't exist, the first two path segments say
 * what the agent guessed ("v1/agents", "api/v1") — useful, bounded, and
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
  [/publicKey must be/, "bad-key-format"],
  [/handle must be/, "bad-handle"],
  [/publicKey and operatorId are required/, "missing-key-or-operator"],
  [/acknowledge the constitution/, "no-constitution-ack"],
  [/handle already registered/, "handle-taken"],
  [/key already registered/, "key-taken"],
  [/does not match the registered key/, "key-mismatch"],
  [/register first|unknown agent|unknown or revoked/, "not-registered"],
  [/revoked/, "revoked"],
  [/signature verification failed|does not verify/, "bad-signature"],
  [/malformed envelope/, "malformed-envelope"],
  [/no citation on faith/, "citation-basis"],
  [/invalid payload|invalid review|invalid vote|invalid build manifest|invalid amendment/, "invalid-schema"],
  [/is not in the corpus|has no claim/, "unknown-parent"],
  [/name the claims|builds have no claims|cite a build with rel/, "citation-basis"],
  [/characters (or formatting )?that must be removed/, "unsanitised-text"],
  [/refused by screening/, "screening-block"],
  [/already submitted|already sent|already voted|already proposed|already vouched|already verified|already co-signed/, "duplicate"],
  [/can vouch|vouch for itself|vouch for at most|sits on an open case/, "vouch-refused"],
  [/not on this item's jury/, "not-a-juror"],
  [/reviews are closed|R1 applies only|voting on this amendment closed/, "closed"],
  [/reasons are shared once/, "not-decided"],
  [/practice limit/, "practice-limit"],
  [/claim limit/, "claim-limit"],
  [/paused by the operator|switched off/, "paused"],
  [/already answered|has expired/, "practice-closed"],
  [/only the case's author and jurors/, "not-a-party"],
  [/stale request/, "stale-request"],
  [/too large/, "too-large"],
  [/body must be JSON/, "bad-json"],
  [/rate limit/, "rate-limited"],
  [/read-only/, "read-only"],
  [/size mismatch|hash mismatch|does not declare/, "bad-file"],
  [/only operators whose agents have jury-accepted work vote/, "not-enfranchised"],
  [/entrenched core need/, "not-entrenched"],
  [/^url: /, "bad-webhook"],
  [/didn't answer the challenge/, "webhook-unverified"],
  [/webhook checks an hour/, "rate-limited"],
  [/can't store routine tokens|webhook rings are signed/, "not-configured"],
  [/^kind: |^cadence: /, "invalid-schema"],
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

/**
 * Counters for a step its handler counts itself (a page, not JSON), with
 * the reason given directly from that handler's own fixed vocabulary: both
 * the all-time and the daily counter.
 */
export function stepKeys(ep: Endpoint, status: number, reason: string | null, day: string): string[] {
  return [...keysFor(ep, status, status >= 400 ? reason : null), `fd:${day}:${ep}:${status < 400 ? "ok" : "no"}`];
}

/**
 * Daily twins of the funnel counters, for the operator's private view of
 * attempts over time: `fd:<YYYY-MM-DD>:<endpoint>:<ok|no>`. Same fixed
 * vocabulary; never who, never what.
 */
export function dayFunnelKeys(day: string, method: string, path: string, status: number): string[] {
  const ep = endpointOf(method, path);
  if (!ep) return [];
  const where = ep === "wrong-path" ? "wrong-path" : ep;
  return [`fd:${day}:${where}:${status < 400 ? "ok" : "no"}`];
}

/**
 * Reads worth counting, by a fixed name: which pages people open and which
 * machine surfaces agents use (skill.md, heartbeats, MCP). Counted per day as
 * `pv:<YYYY-MM-DD>:<name>`; never an IP, a query string or a paper id.
 * Includes crawlers: these are requests, not people.
 */
export function pageKeyOf(method: string, path: string, accept: string | null): string | null {
  const m = method.toUpperCase();
  // POST /charter counts itself (only a charter made, not an edit or a refusal).
  if (m === "POST") return path === "/mcp" ? "mcp" : null;
  if (m !== "GET") return null;
  const html = (accept ?? "").includes("text/html");
  if (path === "/") return html ? "home" : "api-index";
  const pages: Record<string, string> = {
    "/people": "people", "/start": "people", "/join": "people", "/agents": "agents",
    "/observatory": "observatory", "/dashboard": "observatory", "/papers": "papers",
    "/review": "review", "/jury": "review", "/apps": "apps", "/marketplace": "apps", "/about": "about", "/why": "about",
    "/submit": "submit", "/subscribe": "subscribe", "/skill.md": "skill.md", "/llms.txt": "llms.txt",
    "/constitution.md": "constitution", "/terms": "terms", "/terms.md": "terms",
    "/v1/heartbeat": "heartbeat", "/v1/stats": "stats-api", "/v1/review": "review-api", "/v1/challenges": "challenges",
    "/v1/constitution": "constitution-api", "/v1/frontier": "frontier-api", "/v1/standing": "standing-api",
    "/v1/wanted": "wanted-api", "/kit": "kit", "/v1/credence": "credence-api", "/v1/jurors": "jurors-api",
    "/graph": "graph", "/v1/graph": "graph-api", "/frontier": "frontier",
    "/commons": "commons", "/governance": "commons", "/v1/governance": "governance-api", "/charter": "charter",
    "/connect": "connect", "/privacy": "privacy", "/faq": "faq", "/compare": "compare",
  };
  if (pages[path]) return pages[path]!;
  if (path.startsWith("/p/")) return "paper";
  if (path === "/preprints") return "preprints";
  if (path.startsWith("/pp/")) return "preprint";
  if (path.startsWith("/a/")) return "agent-page";
  if (path.startsWith("/claim/")) return "claim";
  if (path.startsWith("/x/")) return "claim"; // an external claim's page (v2)
  if (/^\/u\/[A-Za-z0-9][A-Za-z0-9-]{1,28}[A-Za-z0-9](\/feed\.xml)?$/.test(path)) return path.endsWith("/feed.xml") ? "feeds" : "profile"; // a person's public profile (v2); never /u/n/… or /u/j/… stop links
  if (path.startsWith("/badge/")) return "badge";
  if (path.startsWith("/doorbell/")) return "doorbell";
  if (path.startsWith("/v1/preprints")) return "preprints-api";
  if (path.startsWith("/feeds/")) return "feeds";
  if (path.startsWith("/v1/papers")) return "papers-api";
  if (path.startsWith("/v1/log/")) return "log-api";
  return null;
}

/** Which page names are people's pages (HTML), for "human page views". */
export const HUMAN_PAGES = ["home", "people", "agents", "observatory", "papers", "paper", "preprints", "preprint", "review", "apps", "about", "submit", "subscribe", "kit", "terms", "agent-page", "claim", "graph", "frontier", "commons", "charter", "doorbell", "connect", "privacy", "profile", "faq", "compare"] as const;

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

/** Fold raw counters into a per-endpoint summary for /v1/stats. */
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
