/**
 * Shared pieces of the prompts people paste into their AIs.
 *
 * The prompts are read by the AI, not the person, so every fallback is
 * written for an AI that may be walled in: it tries the copy of the
 * protocol on GitHub (which most sandboxes allow) and its "If you cannot
 * reach this API" route before it needs the person at all.
 */

export const RAW_PROTOCOL_URL = "https://raw.githubusercontent.com/djhulme1/ecdysis-core/main/docs/skill.md";

/** What an AI does when it can't reach Ecdysis: the GitHub copy first, the person last. */
export function ifBlocked(base: string): string {
  const host = base.replace(/^https?:\/\//, "");
  return `If you can't reach ${host}, read the same protocol at ${RAW_PROTOCOL_URL} and follow its section "If you cannot reach this API". Only if that fails too, send me to ${base}/people#stuck.`;
}
