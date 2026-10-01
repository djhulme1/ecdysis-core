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
  | "practice-case" | "practice-answer" | "build" | "build-file"
  | "hazard-decision" | "gov-proposal" | "gov-vote" | "gov-cosign" | "wrong-path";

/** Which tracked write a request is, or null for reads and MCP. */
export function endpointOf(method: string, path: string): Endpoint | null {
  const m = method.toUpperCase();
  if (m === "GET" || m === "HEAD" || m === "OPTIONS") return null;
  if (path === "/mcp") return null;
  // The paste route counts each inner step (register, paper) itself.
  if (path === "/submit") return null;
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
  [/invalid payload|invalid review|invalid vote|invalid build manifest|invalid amendment/, "invalid-schema"],
  [/is not in the corpus|has no claim/, "unknown-parent"],
  [/characters (or formatting )?that must be removed/, "unsanitised-text"],
  [/refused by screening/, "screening-block"],
  [/already submitted|already voted|already proposed/, "duplicate"],
  [/not on this item's jury/, "not-a-juror"],
  [/reviews are closed|R1 applies only/, "closed"],
  [/reasons are shared once/, "not-decided"],
  [/practice limit/, "practice-limit"],
  [/already answered|has expired/, "practice-closed"],
  [/only the case's author and jurors/, "not-a-party"],
  [/stale request/, "stale-request"],
  [/too large/, "too-large"],
  [/body must be JSON/, "bad-json"],
  [/rate limit/, "rate-limited"],
  [/read-only/, "read-only"],
  [/size mismatch|hash mismatch|does not declare/, "bad-file"],
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
  const keys = [`funnel:${where}:${status}`];
  if (status >= 400) keys.push(`funnel:${where}:${status}:${error ? reasonOf(error) : "other"}`);
  return keys;
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
