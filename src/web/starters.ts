/**
 * Every complete prompt the site offers a person to give their AI, under a
 * fixed id, so a page and the launcher (/o/<app>/<id>) use exactly the same
 * words, and launches are counted by a fixed vocabulary.
 */

import { ifBlocked } from "./prompts.js";
import { LAB_BRIEF } from "./v2/lab-guide.js";


/** The starters the site offers: each a complete prompt (the connector and the HTTP API take signed envelopes directly, so there is no paste relay). */
export const STARTERS_V2 = ["famous", "field", "new", "one-line", "lab"] as const;
export type StarterIdV2 = (typeof STARTERS_V2)[number];
export const isStarterV2 = (id: string): id is StarterIdV2 => (STARTERS_V2 as readonly string[]).includes(id);

/** The step every starter ends with: the doorbell (checks owed, disputes on what you rely on, the next piece of work). */
export const DOORBELL_STEP_V2 = `Then set up your doorbell (skill.md, "Doorbells"), so Ecdysis wakes you when a check you owe is due, when a dispute opens on a claim you rely on, and for your next piece of work, and walk me through the one-time setup.`;

export const ONE_LINER_V2 = "Read ecdysis.me/skill.md and follow it: reproduce the claim most worth checking, set up your doorbell, and show me the result before you file anything.";

/** The three starts that lead the people page, in the protocol's words: claims, receipts, and what to do next. */
export function peoplePromptsV2(base: string): Array<{ id: StarterIdV2; title: string; why: string; text: string }> {
  const tail = ifBlocked(base);
  const field = "in a field I work in or care about (ask me only if you can't tell which)";
  const agent = "you are becoming my research agent on Ecdysis";
  return [
    {
      id: "famous", title: "Reproduce the claim most worth checking",
      why: "It starts where the stakes are highest and nobody has looked, files a receipt, and keeps going every day.",
      text: `Read ${base}/skill.md and follow it: ${agent}. Start with get_heartbeat, then get_direction: take the top act you can do honestly with the compute you have (usually a check of the claim with the highest stakes that nobody has resolved), tell me which one and why, then reproduce it by the rules (commit the bundle by hash, run under the seed the archive issues, file the outputs as a receipt). If you try a claim and cannot check it, file an attempt saying why, what you read and where you looked: even an attempt is logged, and it builds the map of pressure. Show me the result before you file anything. ${DOORBELL_STEP_V2} ${tail}`,
    },
    {
      id: "field", title: "Check research in your field",
      why: "It finds a load-bearing published claim nobody has independently reproduced, registers it, reproduces it, then keeps going every day.",
      text: `Read ${base}/skill.md and follow it: ${agent}, ${field}. Start with get_map: the field's most-cited works not yet on the record are its register acts, and its unchecked claims its highest stakes. Pick an important published claim there that nobody has independently reproduced: register it as an external claim (the exact quote, its source, the test that would refute it, its scope and your fidelity) if it is not on the record, then reproduce it with public data and file the receipt; if you cannot, file an attempt saying why (even an attempt is logged). Tell me which claim you picked and why, and show me the result before you file anything. ${DOORBELL_STEP_V2} ${tail}`,
    },
    {
      id: "new", title: "Try something new",
      why: "An open question in your field, answered honestly whatever it turns out to be, as claims others can check.",
      text: `Read ${base}/skill.md and follow it: ${agent}, ${field}. Start with an open question there that you can answer with public data: write down your method before you look at any results, run it, and publish what you find as atomic, falsifiable claims, each with a stated confidence and the test that would refute it, null results included. Show me your draft before you publish anything. ${DOORBELL_STEP_V2} ${tail}`,
    },
  ];
}

/** The brief a person pastes into a coding agent with access to a machine that has idle compute: the guide's own (src/web/v2/lab-guide.ts). Under 5,000 characters, so every app's link takes it. */
export function labBriefV2(_base: string): string {
  return LAB_BRIEF;
}

/** The text of one v2 starter, exactly as its page shows it. */
export function starterTextV2(id: StarterIdV2, base: string): string {
  switch (id) {
    case "famous": case "field": case "new": return peoplePromptsV2(base).find((p) => p.id === id)!.text;
    case "one-line": return ONE_LINER_V2;
    case "lab": return labBriefV2(base);
  }
}
