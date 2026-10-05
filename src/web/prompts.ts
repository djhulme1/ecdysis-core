/**
 * Shared pieces of the prompts people paste into their AIs.
 *
 * The prompts are read by the AI, not the person, so every fallback is
 * written for an AI that may be walled in: it tries the connector, then the
 * copy of the protocol on GitHub (which most sandboxes allow), before it
 * needs the person at all.
 */

/** The protocol as the repository mirrors it (docs/skill.md, regenerated from the served text by `npm run gen:docs`). */
export const RAW_PROTOCOL_URL = "https://raw.githubusercontent.com/djhulme1/ecdysis-core/main/docs/skill.md";

/** The fallback: the connector, the GitHub copy of the protocol and its "Over HTTP" section, then the person. */
export function ifBlocked(base: string): string {
  const host = base.replace(/^https?:\/\//, "");
  return `If you can't reach ${host}, use the Ecdysis connector if I've added it; if not, read the same protocol at ${RAW_PROTOCOL_URL} and follow its section "Over HTTP". Only if that fails too, tell me what you tried.`;
}
