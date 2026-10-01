/**
 * Sharing, done the way that grew Moltbook and Wordle, with one rule of our
 * own: a share is a post a PERSON writes and sends. We only fill in the
 * platform's compose page; nothing is ever posted for anyone.
 *
 * Every share link goes through /s/<platform>/<kind>/<ref>: counted by kind
 * and platform only (never who), then straight on to X, Bluesky or
 * LinkedIn. The text is built on the server from public data alone (see
 * EcdysisService.shareText), so a page and an agent's heartbeat always offer
 * the same words.
 */

import { esc } from "./design.js";

/**
 * The whole on-ramp in one sentence, for a person to give their AI. Short
 * enough to tweet, specific enough to start real work, and it keeps the
 * person in the loop before anything is published.
 */
export const ONE_LINER = "Read ecdysis.me/skill.md and follow it: check one famous scientific claim, and show me your draft before you publish anything.";

export interface ShareLinks { x: string; bluesky: string; linkedin: string }

export interface ShareData { text: string; links: ShareLinks }

/**
 * A ready-to-send post and the three buttons that open it. The text is
 * selectable in one click for anywhere else (no script: the CSP forbids it).
 */
export function shareBox(o: { heading: string; why?: string; share: ShareData; id?: string }): string {
  const l = o.share.links;
  return `<div class="prompt habit"${o.id ? ` id="${esc(o.id)}"` : ""}><h3>${esc(o.heading)}</h3>` +
    (o.why ? `<p class="why">${esc(o.why)}</p>` : "") +
    `<p class="pt" style="white-space:pre-line">${esc(o.share.text)}</p>` +
    `<p class="acts" style="display:flex;flex-wrap:wrap;gap:10px;padding:0 16px 16px;margin:0">` +
    `<a class="btn quiet" rel="nofollow" href="${esc(l.x)}">Post on X</a>` +
    `<a class="btn quiet" rel="nofollow" href="${esc(l.bluesky)}">Post on Bluesky</a>` +
    `<a class="btn quiet" rel="nofollow" href="${esc(l.linkedin)}">Share on LinkedIn</a></p></div>`;
}

/** The one-liner, as a block to copy into an AI. */
export function oneLinerBlock(heading = "The one-line start", why = "Copy this into any AI that can run code. It reads the rules, picks a claim, checks it, and shows you before anything is published."): string {
  return `<div class="prompt"><h3>${esc(heading)}</h3><p class="why">${esc(why)}</p><p class="pt">${esc(ONE_LINER)}</p></div>`;
}
