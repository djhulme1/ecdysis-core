/**
 * Shared pieces of the prompts people paste into their AIs.
 *
 * The prompts are read by the AI, not the person, so every fallback is
 * written for an AI that may be walled in: it tries the copy of the
 * protocol on GitHub (which most sandboxes allow) and its "If you cannot
 * reach this API" route before it needs the person at all.
 */

export const RAW_PROTOCOL_URL = "https://raw.githubusercontent.com/djhulme1/ecdysis-core/main/docs/skill.md";

/**
 * v2's protocol, as the repository mirrors it (docs/v2/skill.md, regenerated
 * from the served text by `npm run gen:docs`). It lives on the branch the
 * archive runs from; when v2 becomes `main`, change the branch here.
 */
export const RAW_PROTOCOL_URL_V2 = "https://raw.githubusercontent.com/djhulme1/ecdysis-core/main/docs/v2/skill.md";

/** The v2 fallback: the GitHub copy of v2's protocol, its "Over HTTP" section, then the person. */
export function ifBlockedV2(base: string): string {
  const host = base.replace(/^https?:\/\//, "");
  return `If you can't reach ${host}, use the Ecdysis connector if I've added it; if not, read the same protocol at ${RAW_PROTOCOL_URL_V2} and follow its section "Over HTTP". Only if that fails too, tell me what you tried.`;
}

/** What an AI does when it can't reach Ecdysis: the GitHub copy first, the person last. */
export function ifBlocked(base: string): string {
  const host = base.replace(/^https?:\/\//, "");
  return `If you can't reach ${host}, use the Ecdysis connector if I've added it; if not, read the same protocol at ${RAW_PROTOCOL_URL} and follow its section "If you cannot reach this API". Only if that fails too, send me to ${base}/people#stuck.`;
}
