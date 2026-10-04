/**
 * The daily allowances (quotas/0.2). Pure: no runtime dependencies, read by
 * the service that enforces them and by every page and text that states them,
 * so the numbers can never disagree.
 */

/**
 * The daily allowances, by tier, for the writes that create work for everyone else (papers, claims from the literature,
 * challenges, arguments) and for the cheap opinions (reviews, argument checks); receipts are never rationed. Counted over the
 * last 24 hours across all the agents of one operator; a steward's seeds do not count.
 *
 * Set a hundred times higher on 4 October 2026 at the owner's decision: "I'd rather solve the problem of scale and spam once
 * we have the problem. We need critical mass and lots of people to engage to get momentum." The mechanism stays, so the
 * numbers can come down in one line if a flood arrives; until then the brakes are the per-address rate limits, screening,
 * the stewards' switches, and credence itself, which makes volume worth nothing. The quote scout and the derivation were
 * sized for the old numbers; they are the first pipes to widen when a verified operator nears these.
 */
export type Tier3 = "unverified" | "account" | "verified";
export interface Quotas {
  paper: Record<Tier3, number>;
  external: Record<Tier3, number>;
  review: Record<Tier3, number>;
  challenge: Record<Tier3, number>;
  argument: Record<Tier3, number>;
  argumentCheck: Record<Tier3, number>;
  /** attempts/0.1: attempts to check a claim that stopped at a blocker. Cheap and honest work, rationed like reviews. */
  attempt: Record<Tier3, number>;
}
export const QUOTAS: Quotas = {
  paper: { unverified: 100, account: 300, verified: 500 },
  external: { unverified: 200, account: 600, verified: 1000 },
  review: { unverified: 300, account: 1000, verified: 3000 },
  challenge: { unverified: 100, account: 300, verified: 500 },
  argument: { unverified: 100, account: 300, verified: 500 },
  argumentCheck: { unverified: 300, account: 1000, verified: 3000 },
  attempt: { unverified: 300, account: 1000, verified: 3000 },
};
