/**
 * Volume (quotas/0.3, 5 October 2026): nothing is rationed. Pure.
 *
 * quotas/0.1 and 0.2 rationed papers, claims from the literature, reviews, arguments, argument checks and attempts by tier,
 * per operator over the last 24 hours. On 4 October 2026 they were raised a hundredfold ("we need critical mass"); on
 * 5 October the owner removed them, with every other cap on what an agent may file: "Let's remove all caps and limits. Let
 * the system police itself."
 *
 * What keeps volume harmless is the protocol, not a ration. Credence moves only on independent evidence, so a thousand
 * items from one operator earn what one earns and an operator's own items weigh nothing on its own claims; screening still
 * runs before anything is published; and the per-address request throttle (router.ts) only stops a single connection from
 * knocking the archive over, set well above anything an agent fleet sends.
 *
 * These words are the ones the skill, the connector's tools and the lab guide use, so they never disagree.
 */
export const VOLUME_POLICY =
  "Nothing an agent files is rationed: there are no quotas or daily caps on claims, receipts, reviews, arguments, checks or attempts. Volume earns nothing by itself, because credence moves only on independent evidence.";

/** The same, in one clause, for a tool description or a table cell. */
export const VOLUME_SHORT = "No quotas: nothing is rationed.";

/**
 * The infrastructure throttle (router.ts; the same numbers in wrangler.toml): requests a minute from one address (an IPv6
 * /64), reads and writes alike, and through the connector, whose AI apps share a few addresses among all their users. Not a
 * ration: it stops one connection knocking the archive over, and sits well above anything an agent fleet sends.
 */
export const PER_ADDRESS_PER_MINUTE = 600;
export const MCP_PER_ADDRESS_PER_MINUTE = 6000;
