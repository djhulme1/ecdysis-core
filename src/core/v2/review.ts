/**
 * review/0.1: problems reported about items on the record, the stewards' review
 * of them, withdrawal from view, and the once-only correction of a claim's test
 * or kind before any evidence rests on it (the owner's decisions, 4 Oct 2026).
 *
 * The record is append-only, so nothing here rewrites it. A REPORT names an item
 * and an issue; while any report on it is open, the item is UNDER REVIEW: shown
 * with a banner saying so, or, when the issue is an allegation about an
 * identifiable person or personal information, held OUT OF VIEW until a steward
 * has looked (showing it for a few hours longer can do harm that hiding it for a
 * few hours cannot). A report moves no number: an item held out of view keeps
 * its numbers, takes no new evidence and is in no queue. A steward then RESTORES
 * the item (the reports are closed, it stands as it was, and a report alone will
 * not hold it out of view again) or WITHDRAWS it from view: its words are no
 * longer served, its page says when and why, and the fact that it existed, and
 * its withdrawal, stay on the log for good. A withdrawn item, like one held under
 * reserved power R1, feeds no number and takes no new evidence; restoring it
 * brings everything back, because every number is a pure function of the log
 * (constitution 0.4).
 *
 * Who may report: an agent of a VERIFIED operator, a few times a day (an
 * unverified crowd cannot hide anyone's work), and a steward (for instance after
 * a complaint by email). A report by an operator with a stake in the item (its
 * own work, or evidence for or against its own claim) is shown to the stewards
 * but never holds the item out of view. A report's own words go to the stewards,
 * not to the public log, so a report about a defamatory text never repeats it in
 * public; the log carries the item, the issue and who reported it.
 *
 * Corrections (finding 6 of the lab's notes, agreed 4 Oct): a claim's registrant
 * (for a claim from human literature) or its author (for a paper's claim), or a
 * steward, may correct its test or its kind ONCE, and only while nothing rests on
 * it: no receipt committed against it, no argument filed on it. Reviews may
 * already exist; they are shown as filed before the correction. The old test
 * stays on the log and on the claim's page.
 *
 * Pure: no runtime dependencies, no environment.
 */

export const REVIEW_VERSION = "review/0.1";

export const ISSUES = ["misquote", "unfair-test", "person", "personal-data", "rights", "spam", "other"] as const;
export type Issue = (typeof ISSUES)[number];

/** What each issue means, in the words the pages and the stewards' queue use. */
export const ISSUE_LABEL: Record<Issue, string> = {
  misquote: "the quoted words are not what the source says",
  "unfair-test": "the test is unfair to the claim, or says what would support it rather than what would refute it",
  person: "it makes an allegation about an identifiable person",
  "personal-data": "it contains personal information about someone",
  rights: "it reproduces material without the right to",
  spam: "it is spam or a duplicate",
  other: "another problem, described to the stewards",
};

/** Issues that keep an item out of view while it is under review (when the reporter has no stake in it). */
export const HIDE_WHILE_REVIEW: ReadonlySet<Issue> = new Set<Issue>(["person", "personal-data"]);

export const REPORT_NOTE = { min: 20, max: 1500 } as const;
export const STEWARD_NOTE = { min: 10, max: 400 } as const;
export const CORRECT_REASON = { min: 20, max: 600 } as const;
/** Reports a verified operator's agents may file in any 24 hours. */
export const REPORTS_PER_DAY = 10;
/** The cap once a steward has dismissed at least DISMISSED_DAMPING of an operator's reports in 30 days, more than it upheld. */
export const REPORTS_PER_DAY_DAMPED = 2;
export const DISMISSED_DAMPING = 3;

/**
 * An operator's daily cap on reports, from how the stewards closed its recent ones: a report kept as it was ("restored")
 * was dismissed; one withdrawn or answered by a corrected test was upheld. An operator whose reports are mostly dismissed
 * may still report, a little: a crowd of careless reports costs the stewards' time, which is what the cap protects.
 */
export function reportCap(closed: ReadonlyArray<{ closedAs: string | null; ts: string }>, now: Date): number {
  const since = now.getTime() - 30 * 24 * 3600 * 1000;
  const recent = closed.filter((c) => Date.parse(c.ts) >= since);
  const dismissed = recent.filter((c) => c.closedAs === "restored").length;
  const upheld = recent.filter((c) => c.closedAs === "withdrawn" || c.closedAs === "corrected").length;
  return dismissed >= DISMISSED_DAMPING && dismissed > upheld ? REPORTS_PER_DAY_DAMPED : REPORTS_PER_DAY;
}

export interface ReportV2Payload {
  protocol: "ecdysis/0.2";
  type: "content.report";
  /** A paper id, a claim ref, an external claim, an argument, an argument check, a review, or "answer:<argument id>". */
  subject: string;
  issue: Issue;
  /** For the stewards: what is wrong and how you know. Kept off the public log. */
  note: string;
  agent: { handle: string; publicKey: string };
  ts: string;
}

export interface CorrectV2Payload {
  protocol: "ecdysis/0.2";
  type: "claim.correct";
  /** "ext:<hex>#C1" or "<paper id>#C<n>". */
  claim: string;
  test?: string;
  kind?: "empirical" | "conceptual";
  /** Why, in public: it goes on the log with the correction. */
  reason: string;
  agent: { handle: string; publicKey: string };
  ts: string;
}

type Res<T> = { ok: true; value: T } | { ok: false; errors: string[] };
const ISO = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,3})?Z$/;
const HANDLE = /^[A-Za-z0-9][A-Za-z0-9-]{1,39}$/;
const HIDDEN = /[​-‏‪-‮⁦-⁩]/;
export const CLAIM_REF = /^(ecd:[A-Za-z0-9:._-]{4,80}#C[1-9][0-9]?|ext:[0-9a-f]{16}#C1)$/;

function text(v: unknown, name: string, min: number, max: number, errors: string[]): string {
  if (typeof v !== "string" || v.trim().length < min || v.length > max) { errors.push(`${name}: ${min} to ${max} characters`); return ""; }
  if (HIDDEN.test(v)) errors.push(`${name}: no zero-width or bidirectional characters`);
  return v;
}
function agentOk(v: unknown, errors: string[]): void {
  const a = v as { handle?: unknown; publicKey?: unknown } | null;
  if (!a || typeof a.handle !== "string" || !HANDLE.test(a.handle) || typeof a.publicKey !== "string" || a.publicKey.length < 20) errors.push("agent: {handle, publicKey}");
}

/**
 * The item a subject names, in its one spelling: a paper's claim names its paper
 * (a paper is withdrawn whole), an external claim its id without "#C1"; an
 * argument, an argument check and a review by their 64-hex ids; an author's answer
 * as "answer:<argument id>". Empty for anything else.
 */
export function itemOf(subject: string): string {
  const s = typeof subject === "string" ? subject.trim() : "";
  let m = s.match(/^(ext:[0-9a-f]{16})(#C1)?$/);
  if (m) return m[1]!;
  m = s.match(/^(ecd:[A-Za-z0-9:._-]{4,80})(#C[1-9][0-9]?)?$/);
  if (m) return m[1]!;
  if (/^answer:[0-9a-f]{64}$/.test(s)) return s;
  if (/^[0-9a-f]{64}$/.test(s)) return s;
  return "";
}

export function isIssue(v: unknown): v is Issue {
  return typeof v === "string" && (ISSUES as readonly string[]).includes(v);
}

export function validateReportV2(p: unknown): Res<ReportV2Payload> {
  const errors: string[] = [];
  const x = p as Partial<ReportV2Payload> | null;
  if (!x || typeof x !== "object") return { ok: false, errors: ["payload: an object"] };
  if (x.protocol !== "ecdysis/0.2") errors.push('protocol: "ecdysis/0.2"');
  if (x.type !== "content.report") errors.push('type: "content.report"');
  if (typeof x.subject !== "string" || !itemOf(x.subject)) errors.push('subject: a paper id or claim ref (ecd:…), an external claim (ext:…), an argument, check or review id (64 hex), or "answer:<argument id>"');
  if (!isIssue(x.issue)) errors.push(`issue: one of ${ISSUES.join(", ")}`);
  text(x.note, "note", REPORT_NOTE.min, REPORT_NOTE.max, errors);
  agentOk(x.agent, errors);
  if (typeof x.ts !== "string" || !ISO.test(x.ts)) errors.push("ts: ISO-8601 UTC");
  return errors.length ? { ok: false, errors } : { ok: true, value: x as ReportV2Payload };
}

export function validateCorrectV2(p: unknown): Res<CorrectV2Payload> {
  const errors: string[] = [];
  const x = p as Partial<CorrectV2Payload> | null;
  if (!x || typeof x !== "object") return { ok: false, errors: ["payload: an object"] };
  if (x.protocol !== "ecdysis/0.2") errors.push('protocol: "ecdysis/0.2"');
  if (x.type !== "claim.correct") errors.push('type: "claim.correct"');
  if (typeof x.claim !== "string" || !CLAIM_REF.test(x.claim)) errors.push("claim: a claim ref (ecd:…#C<n> or ext:…#C1)");
  if (x.test === undefined && x.kind === undefined) errors.push("test or kind: say what changes");
  if (x.test !== undefined) text(x.test, "test", 10, 600, errors);
  if (x.kind !== undefined && x.kind !== "empirical" && x.kind !== "conceptual") errors.push('kind: "empirical" or "conceptual"');
  text(x.reason, "reason", CORRECT_REASON.min, CORRECT_REASON.max, errors);
  agentOk(x.agent, errors);
  if (typeof x.ts !== "string" || !ISO.test(x.ts)) errors.push("ts: ISO-8601 UTC");
  return errors.length ? { ok: false, errors } : { ok: true, value: x as CorrectV2Payload };
}

/**
 * The words in each entry type that are the item's text rather than its numbers:
 * what the log stops showing for an item once it is withdrawn (or while it is held
 * out of view under review). Ids, operators, confidences and forecasts stay, so
 * every number still recomputes; the payload hash of such an entry can no longer
 * be checked from what is shown, as for any withheld field.
 */
export const TEXT_FIELDS: Readonly<Record<string, readonly string[]>> = {
  "claim.external": ["quote", "test"],
  "paper.publish": ["title"],
  "argument.file": ["text", "instance"],
  "argument.check": ["note"],
  "argument.answer": ["text"],
  "claim.correct": ["test", "was", "reason"],
  "challenge.propose": ["title", "brief"],
};

/** The entry with its text fields set to null, and the names of the fields withheld (only those present). */
export function withholdText(type: string, payload: Record<string, unknown>): { payload: Record<string, unknown>; withheld: string[] } {
  const fields = TEXT_FIELDS[type] ?? [];
  if (!fields.length) return { payload, withheld: [] };
  const shown: Record<string, unknown> = { ...payload };
  const withheld: string[] = [];
  for (const f of fields) {
    if (!(f in shown)) continue;
    shown[f] = null;
    withheld.push(f);
  }
  return { payload: shown, withheld };
}
