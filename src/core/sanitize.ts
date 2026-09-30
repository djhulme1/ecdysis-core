/**
 * Text safety for agent-supplied content.
 *
 * Everything an agent submits is untrusted data. It is stored as plain text,
 * never as markup, and renderers must escape it — but the sanitiser removes a
 * class of characters that make text *lie to its readers* even as plain text:
 *
 *  - Bidirectional override and isolate controls (U+202A–U+202E, U+2066–2069):
 *    the "Trojan Source" trick (CVE-2021-42574), which renders text in a
 *    different order than it is processed. In a corpus that both humans and
 *    machines read, display order and processing order must agree.
 *  - Zero-width and invisible characters (U+200B–U+200D, U+2060, U+FEFF) and
 *    the Unicode tag block (U+E0000–U+E007F): invisible payload channels used
 *    to smuggle instructions to machine readers past human reviewers.
 *  - C0/C1 control characters other than \n and \t.
 *
 * The sanitiser also NFC-normalises, so visually identical strings hash
 * identically, and collapses pathological whitespace. It never tries to judge
 * meaning — that is the screening pipeline's job (see hazard.ts).
 */

export interface SanitizeResult {
  text: string;
  /** True if anything had to be removed or changed beyond NFC + trimming. */
  modified: boolean;
  /** Names of the character classes that were found and stripped. */
  stripped: string[];
}

const BIDI = /[‪-‮⁦-⁩؜‎‏]/g;
const INVISIBLE = /[​-‍⁠﻿­]/g;
const TAGS = /[\u{E0000}-\u{E007F}]/gu;
const CONTROLS = /[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F-\u009F]/g;

export function sanitizeText(input: string): SanitizeResult {
  const stripped: string[] = [];
  let text = input.normalize("NFC");

  if (BIDI.test(text)) {
    stripped.push("bidi-controls");
    text = text.replace(BIDI, "");
  }
  if (INVISIBLE.test(text)) {
    stripped.push("invisible");
    text = text.replace(INVISIBLE, "");
  }
  if (TAGS.test(text)) {
    stripped.push("unicode-tags");
    text = text.replace(TAGS, "");
  }
  if (CONTROLS.test(text)) {
    stripped.push("control-chars");
    text = text.replace(CONTROLS, "");
  }

  // Collapse >2 consecutive newlines and trailing space; trim ends.
  const collapsed = text
    .replace(/[ \t]+\n/g, "\n")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
  const modified = stripped.length > 0 || collapsed !== input;
  return { text: collapsed, modified, stripped };
}

/** Sanitise every string field of a flat-ish JSON value, in place-ish. */
export function sanitizeDeep<T>(value: T, report: Set<string>): T {
  if (typeof value === "string") {
    const r = sanitizeText(value);
    r.stripped.forEach((s) => report.add(s));
    return r.text as unknown as T;
  }
  if (Array.isArray(value)) {
    return value.map((v) => sanitizeDeep(v, report)) as unknown as T;
  }
  if (value && typeof value === "object") {
    const out: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(value)) out[k] = sanitizeDeep(v, report);
    return out as unknown as T;
  }
  return value;
}
