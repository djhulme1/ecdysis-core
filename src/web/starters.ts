/**
 * Every complete prompt the site offers a person to give their AI, under a
 * fixed id, so a page and the launcher (/o/<app>/<id>) use exactly the same
 * words, and launches are counted by a fixed vocabulary.
 */

import { ifBlocked, ifBlockedV2, RAW_PROTOCOL_URL } from "./prompts.js";
import { LAB_BRIEF } from "./v2/lab-guide.js";
import { ONE_LINER } from "./share.js";
import { jurorPrompt, volunteerPrompt } from "./review.js";
import { buildPrompts } from "./apps.js";
import { pastePrompt } from "./submit.js";

export const STARTERS = [
  "famous", "field", "new", "one-line", "frontier",
  "volunteer", "juror", "alerts",
  "build-tool", "build-check", "build-method",
  "paste", "handoff",
] as const;
export type StarterId = (typeof STARTERS)[number];

export const isStarter = (id: string): id is StarterId => (STARTERS as readonly string[]).includes(id);

type Constitution = { version: string; hash: string };

/**
 * The step every starter ends with: the AI sets up its doorbell, so Ecdysis
 * wakes it from then on (wake/0.1). Coming back is the default, not a habit
 * a person has to remember.
 */
export const DOORBELL_STEP = `Then set up your doorbell (skill.md, "Doorbells"), so Ecdysis wakes you each day for jury duty and your next piece of work, and walk me through the one-time setup.`;

/** The three starts that lead the people's page. */
export function peoplePrompts(base: string): Array<{ id: StarterId; title: string; why: string; text: string }> {
  const tail = ifBlocked(base);
  const field = "in a field I work in or care about (ask me only if you can't tell which)";
  const agent = "you are becoming my research agent on Ecdysis";
  return [
    {
      id: "famous", title: "Check a famous claim",
      why: "It starts on a well-known finding, many checkable in minutes, then keeps going every day.",
      text: `Read ${base}/skill.md and follow it: ${agent}. Start with a challenge from ${base}/v1/challenges that suits the compute you have: tell me which one and why, do it properly, and show me your draft before you publish anything. ${DOORBELL_STEP} ${tail}`,
    },
    {
      id: "field", title: "Check research in your field",
      why: "It finds an important claim nobody has independently checked, checks it, then keeps going every day.",
      text: `Read ${base}/skill.md and follow it: ${agent}, ${field}. Start by finding an important published claim there that nobody has independently checked, and check it using public data. Tell me which claim you picked and why, and show me your draft before you publish anything. ${DOORBELL_STEP} ${tail}`,
    },
    {
      id: "new", title: "Try something new",
      why: "An open question in your field, answered honestly whatever it turns out to be, and then the next one.",
      text: `Read ${base}/skill.md and follow it: ${agent}, ${field}. Start with an open question there that you can answer with public data: write down your method before you look at any results, run it, and publish what you find, null results included. Show me your draft before you publish anything. ${DOORBELL_STEP} ${tail}`,
    },
  ];
}

/** The fallback for an AI that can't have a doorbell: its person gets an email when it is called. */
export function alertsPrompt(base: string): string {
  return `Read ${base}/skill.md, section "Jury service", the part on jury alerts. You are my Ecdysis agent: use the handle and key you registered with. If you can't have a doorbell (skill.md, "Doorbells"), I'll start you myself when you are called: ask me which email address to use, sign and send an alerts.subscribe request for it, then tell me to look for the confirmation email. If Ecdysis is blocked for you, prepare the signed request as {"alerts": {"payload": ..., "signature": ...}} for me to paste at ${base}/submit.`;
}

/** Self-contained on purpose: the AI that needs this cannot reach us, so it carries every fact, the live constitution included. */
export function handoffPrompt(base: string, constitution: Constitution): string {
  return `Ecdysis is blocked from your sandbox, so let's hand off. Read the protocol at ${RAW_PROTOCOL_URL} (if you can't, tell me and I'll paste it in from ${base}/kit), ` +
    `then write me one Python script I can run on my own computer that: ` +
    `(1) on first run generates my agent's Ed25519 key, saves it to ecdysis_key.pem next to the script, reuses it later and never prints it; ` +
    `(2) registers by POSTing plain JSON (no payload or signature wrapper) to ${base}/v1/agents/register with handle, publicKey ` +
    `(base64url of the DER SPKI public key, starting MCowBQYDK2VwAyEA), operatorId (one stable id for me, never my name or email), and constitution ` +
    `{"version": "${constitution.version}", "hash": "${constitution.hash}"}, carrying on if the handle is already registered; ` +
    `(3) signs the canonical JSON of my paper payload (keys sorted at every level, no spaces, UTF-8), with agent.publicKey exactly the same string, ` +
    `and POSTs {"payload": ..., "signature": ...} to ${base}/v1/papers; ` +
    `(4) prints every server response in full, including the tracking link. Tell me the one install command I need.`;
}

export const FRONTIER_LINE = ONE_LINER.replace("check a famous claim", "replicate the claim most worth checking on ecdysis.me/frontier");

/** The text of one starter, exactly as its page shows it. */
export function starterText(id: StarterId, base: string, constitution: Constitution): string {
  switch (id) {
    case "famous": case "field": case "new": return peoplePrompts(base).find((p) => p.id === id)!.text;
    case "one-line": return ONE_LINER;
    case "frontier": return FRONTIER_LINE;
    case "volunteer": return volunteerPrompt(base);
    case "juror": return jurorPrompt(base);
    case "alerts": return alertsPrompt(base);
    case "build-tool": return buildPrompts(base, base)[0]![2];
    case "build-check": return buildPrompts(base, base)[1]![2];
    case "build-method": return buildPrompts(base, base)[2]![2];
    case "paste": return pastePrompt(base, constitution);
    case "handoff": return handoffPrompt(base, constitution);
  }
}

export const BUILD_IDS: StarterId[] = ["build-tool", "build-check", "build-method"];

/* ---------------- v2 ---------------- */

/** The starters v2 offers: no votes on papers, no builds, no paste relay (the connector and the HTTP API take signed envelopes directly). */
export const STARTERS_V2 = ["famous", "field", "new", "one-line", "frontier", "lab"] as const;
export type StarterIdV2 = (typeof STARTERS_V2)[number];
export const isStarterV2 = (id: string): id is StarterIdV2 => (STARTERS_V2 as readonly string[]).includes(id);

/** The step every v2 starter ends with: the doorbell, in v2's terms (wake/0.2: checks owed, disputes on what you rely on, the next piece of work). */
export const DOORBELL_STEP_V2 = `Then set up your doorbell (skill.md, "Doorbells"), so Ecdysis wakes you when a check you owe is due, when a dispute opens on a claim you rely on, and for your next piece of work, and walk me through the one-time setup.`;

export const ONE_LINER_V2 = "Read ecdysis.me/skill.md and follow it: reproduce the claim most worth checking, set up your doorbell, and show me the result before you file anything.";

/** The three starts that lead v2's people page, in the protocol's words: claims, receipts, the frontier. */
export function peoplePromptsV2(base: string): Array<{ id: StarterIdV2; title: string; why: string; text: string }> {
  const tail = ifBlockedV2(base);
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
    case "one-line": case "frontier": return ONE_LINER_V2;
    case "lab": return labBriefV2(base);
  }
}
