/**
 * What a finding covers, and what a receipt tests (scope/0.1 and kinds/0.1,
 * 4 October 2026; design: claude/ecdysis-scope-design.md, Parts I and II).
 *
 * SCOPE. Every new empirical claim declares what it covers: a PERIOD (the
 * span of the data the finding describes), or GENERAL, either because its
 * object is defined by construction (a theorem, a simulation's ensemble, a
 * named benchmark or model: every sample of it is the same population) or
 * because the finding is ASSERTED beyond its data (for a claim from human
 * literature, only when the registered sentence itself says so). A claim
 * from human literature also declares its FIDELITY: whether its test states
 * the method the paper reports ("reported") or adapts it ("adapted": another
 * data source, other sample rules, another statistic or thresholds). A claim
 * may carry a DATA OF RECORD: its own data by hash, which is what lets the
 * archive check that a receipt used "the claim's own data".
 *
 * KINDS (Clemens, "The meaning of failed replications", J. Econ. Surveys
 * 31(1), 2017, Table 1). A receipt declares, before its seed, two facts and
 * why: did it use the claim's stated method, and are its data the claim's
 * own, new data covering the claim's whole population and period, or data
 * beyond them? The archive derives the kind:
 *
 *                                   method as stated   method altered
 *   the claim's own data            VERIFICATION       reanalysis
 *   new data, the whole population  REPRODUCTION       reanalysis
 *   and period
 *   beyond them, or a subset        extension          reanalysis-extension
 *
 * Verification and reproduction are REPLICATION TESTS: they sample the same
 * sampling distribution as the original, so a discrepancy says something is
 * wrong with the claim (or with the test). Everything else is a ROBUSTNESS
 * TEST: it asks whether the finding holds under a change, and a discrepancy
 * says only that the change matters. Only replication tests are evidence on
 * the claim; a robustness test is listed beside it as "robust / not robust
 * to …" and never moves its credence or status. The burden of proof is the
 * follow-up's: a receipt that does not declare what it tests, or whose
 * declaration the archive cannot confirm, counts as a robustness test.
 *
 * What the archive confirms, here and in the service before a commit is
 * accepted: a replication test on a claim with a period declares exactly
 * that period, to the month (a narrower one is a subset, which Clemens
 * counts as an extension); its result reports the span its data actually
 * cover, which must lie within the declaration and reach the period's first
 * and last months; "the claim's own data" means every file of the claim's
 * data of record among the bundle's inputs, by hash; "new data" needs a
 * declared scope; a re-run applies the stated method. What it cannot confirm
 * — whether the code applies the stated method, and population beyond time
 * — is stated in the receipt's basis before the seed, in public, against
 * public code.
 *
 * Pure: no runtime dependencies, no environment. Every classification
 * recomputes from the public log anywhere.
 */

import { sanitizeText } from "../sanitize.js";

export const KINDS_VERSION = "kinds/0.1";
export const SCOPE_VERSION = "scope/0.1";

/* ---------------- periods ---------------- */

/** A span of dates, inclusive, normalised to YYYY-MM-DD at both ends. */
export interface Period { from: string; to: string }

const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
const YM = /^(\d{4})-(\d{2})$/;
const YMD = /^(\d{4})-(\d{2})-(\d{2})$/;

const daysIn = (y: number, m: number) => new Date(Date.UTC(y, m, 0)).getUTCDate();
const pad = (n: number, w = 2) => String(n).padStart(w, "0");

/** One bound: "YYYY-MM-DD", or "YYYY-MM" expanded to the month's first day (a start) or last day (an end). Null if not a real date. */
export function parseBound(v: unknown, end: boolean): string | null {
  if (typeof v !== "string") return null;
  let m = YMD.exec(v);
  if (m) {
    const y = Number(m[1]), mo = Number(m[2]), d = Number(m[3]);
    if (y < 1000 || mo < 1 || mo > 12 || d < 1 || d > daysIn(y, mo)) return null;
    return v;
  }
  m = YM.exec(v);
  if (m) {
    const y = Number(m[1]), mo = Number(m[2]);
    if (y < 1000 || mo < 1 || mo > 12) return null;
    return `${m[1]}-${m[2]}-${end ? pad(daysIn(y, mo)) : "01"}`;
  }
  return null;
}

/** {from, to} with real dates, from ≤ to; null otherwise. */
export function normalisePeriod(x: unknown): Period | null {
  const p = x as { from?: unknown; to?: unknown } | null;
  if (!p || typeof p !== "object" || Array.isArray(p)) return null;
  const from = parseBound(p.from, false);
  const to = parseBound(p.to, true);
  if (!from || !to || from > to) return null;
  return { from, to };
}

/** What is wrong with a declared period, in the archive's words; empty when nothing is. `notAfter` (YYYY-MM-DD): a finding does not describe the future. */
export function periodProblems(x: unknown, where: string, notAfter?: string): string[] {
  const p = normalisePeriod(x);
  if (!p) return [`${where}: {from, to}, each "YYYY-MM" or "YYYY-MM-DD", from no later than to`];
  const errors: string[] = [];
  if (notAfter && p.to > notAfter) errors.push(`${where}.to: not after today (${notAfter}); a finding does not describe the future`);
  if (Number(p.to.slice(0, 4)) - Number(p.from.slice(0, 4)) > 200) errors.push(`${where}: at most 200 years`);
  return errors;
}

export const monthOf = (d: string) => d.slice(0, 7);
/** The same months at both ends: what a replication test's declared period must be, against a claim's. */
export const sameMonths = (a: Period, b: Period) => monthOf(a.from) === monthOf(b.from) && monthOf(a.to) === monthOf(b.to);
export const within = (inner: Period, outer: Period) => inner.from >= outer.from && inner.to <= outer.to;
export const overlaps = (a: Period, b: Period) => a.from <= b.to && b.from <= a.to;
/** An emitted span that starts in the claim's first month and ends in its last: the data reach the whole period. */
export const reachesEnds = (emitted: Period, claim: Period) => monthOf(emitted.from) === monthOf(claim.from) && monthOf(emitted.to) === monthOf(claim.to);

/** A period in words: "10 September 2026", "September 2026", "April 2009 to July 2012". */
export function periodWords(p: Period): string {
  const day = (d: string) => `${Number(d.slice(8, 10))} ${MONTHS[Number(d.slice(5, 7)) - 1]} ${d.slice(0, 4)}`;
  const month = (d: string) => `${MONTHS[Number(d.slice(5, 7)) - 1]} ${d.slice(0, 4)}`;
  if (p.from === p.to) return day(p.from);
  const wholeMonths = p.from.endsWith("-01") && Number(p.to.slice(8, 10)) === daysIn(Number(p.to.slice(0, 4)), Number(p.to.slice(5, 7)));
  if (monthOf(p.from) === monthOf(p.to)) return wholeMonths ? month(p.from) : `${day(p.from)} to ${day(p.to)}`;
  return wholeMonths ? `${month(p.from)} to ${month(p.to)}` : `${day(p.from)} to ${day(p.to)}`;
}

/* ---------------- the period a result reports ---------------- */

/**
 * The two output names a bundle uses to report the span its data actually
 * cover (YYYYMMDD integers, computed from the data). Required when a commit
 * declared a period; reserved, so they never count against MAX_OUTPUTS, and
 * a cross-check compares them exactly.
 */
export const PERIOD_OUTPUTS = ["period_from", "period_to"] as const;

const yyyymmdd = (v: unknown): string | null => {
  if (typeof v !== "number" || !Number.isInteger(v) || v < 10000101 || v > 99991231) return null;
  const s = String(v);
  return parseBound(`${s.slice(0, 4)}-${s.slice(4, 6)}-${s.slice(6, 8)}`, false);
};

/** The span a result's outputs report, or null when they report none (or not two real dates in order). */
export function emittedPeriod(outputs: Record<string, unknown> | null | undefined): Period | null {
  if (!outputs) return null;
  const from = yyyymmdd(outputs["period_from"]);
  const to = yyyymmdd(outputs["period_to"]);
  return from && to && from <= to ? { from, to } : null;
}

/* ---------------- claim scope, fidelity, data of record ---------------- */

export type GeneralReason = "construction" | "asserted";
export type ClaimScope = { period: Period; basis: string } | { general: GeneralReason; basis: string };
export interface Fidelity { as: "reported" | "adapted"; basis: string }
/** A file of a claim's data of record, in inputs/0.1's form (receipts.ts, BundleInput). */
export interface DataFile { name: string; url: string; sha256: string; bytes: number; access: "open" | "registered" | "restricted"; licence?: string }

export const BASIS = { min: 20, max: 400 } as const;
export const MAX_DATA_FILES = 8;
const HEX64 = /^[0-9a-f]{64}$/;
const FILE_NAME = /^[A-Za-z][A-Za-z0-9_.-]{0,39}$/;
/**
 * A short text the pages will show: its length, and nothing in it invisible (the sanitiser's classes: control, bidirectional,
 * zero-width and tag characters), since the page shows exactly what the log holds, with its agent's name.
 */
const textProblem = (v: unknown, where: string, min: number, max: number, what: string): string | null =>
  typeof v !== "string" || v.trim().length < min || v.length > max ? `${where}: ${what}, ${min} to ${max} characters`
    : sanitizeText(v).stripped.length > 0 ? `${where}: no control, bidirectional, zero-width or tag characters` : null;

/** What is wrong with a declared scope; empty when nothing is. `external`: a claim from human literature, whose basis quotes the paper. */
export function scopeProblems(x: unknown, where: string, o: { notAfter?: string; external: boolean }): string[] {
  const s = x as { period?: unknown; general?: unknown; basis?: unknown } | null;
  const shapes = `${where}: {period: {from, to}, basis} for a finding about a span of time, or {general: "construction" | "asserted", basis}`;
  if (!s || typeof s !== "object" || Array.isArray(s)) return [shapes];
  const errors: string[] = [];
  if (s.period !== undefined && s.general !== undefined) errors.push(`${where}: a period or general, not both`);
  else if (s.period !== undefined) errors.push(...periodProblems(s.period, `${where}.period`, o.notAfter));
  else if (s.general !== "construction" && s.general !== "asserted") errors.push(shapes);
  const what = o.external
    ? (s.general === undefined ? "the paper's words that state the span of its data" : s.general === "construction" ? "what defines the object the claim is about" : "the registered sentence's words that assert the finding beyond the paper's data")
    : (s.general === undefined ? "the data the finding describes" : s.general === "construction" ? "what defines the object the claim is about" : "why the finding holds beyond its data");
  const t = textProblem(s.basis, `${where}.basis`, BASIS.min, BASIS.max, what);
  if (t) errors.push(t);
  return errors;
}

export function normaliseScope(x: unknown): ClaimScope | null {
  const s = x as { period?: unknown; general?: unknown; basis?: unknown } | null;
  if (!s || typeof s !== "object" || typeof s.basis !== "string") return null;
  if (s.period !== undefined) { const p = normalisePeriod(s.period); return p && s.general === undefined ? { period: p, basis: s.basis } : null; }
  return s.general === "construction" || s.general === "asserted" ? { general: s.general, basis: s.basis } : null;
}

export function fidelityProblems(x: unknown, where: string): string[] {
  const f = x as { as?: unknown; basis?: unknown } | null;
  if (!f || typeof f !== "object" || Array.isArray(f) || (f.as !== "reported" && f.as !== "adapted")) return [`${where}: {as: "reported" | "adapted", basis}: does the test state the method the paper reports, or adapt it (another data source, other sample rules, another statistic or other thresholds)?`];
  const t = textProblem(f.basis, `${where}.basis`, BASIS.min, BASIS.max, f.as === "reported" ? "how the test follows the paper's reported method" : "what the test changes from the paper's reported method");
  return t ? [t] : [];
}

export function normaliseFidelity(x: unknown): Fidelity | null {
  const f = x as { as?: unknown; basis?: unknown } | null;
  return f && typeof f === "object" && (f.as === "reported" || f.as === "adapted") && typeof f.basis === "string" ? { as: f.as, basis: f.basis } : null;
}

/** A data of record: 1 to 8 files, each {name, url, sha256, bytes, access, licence?}, as inputs/0.1 declares a bundle's inputs. */
export function dataOfRecordProblems(x: unknown, where: string): string[] {
  if (!Array.isArray(x) || x.length < 1 || x.length > MAX_DATA_FILES) return [`${where}: 1 to ${MAX_DATA_FILES} files, each {name, url, sha256, bytes, access, licence?}`];
  const errors: string[] = [];
  const names = new Set<string>();
  for (const [k, f] of (x as Array<Partial<DataFile> | null>).entries()) {
    const at = `${where}[${k}]`;
    if (!f || typeof f !== "object") { errors.push(`${at}: {name, url, sha256, bytes, access, licence?}`); continue; }
    if (typeof f.name !== "string" || !FILE_NAME.test(f.name)) errors.push(`${at}.name: a letter then letters, digits, _ . - (max 40)`);
    else if (names.has(f.name)) errors.push(`${at}.name: duplicate`);
    else names.add(f.name);
    if (typeof f.url !== "string" || !/^https:\/\/[^\s]{4,300}$/.test(f.url) || sanitizeText(f.url).stripped.length > 0) errors.push(`${at}.url: https, at most 300 characters, nothing invisible`);
    if (typeof f.sha256 !== "string" || !HEX64.test(f.sha256)) errors.push(`${at}.sha256: 64 hex`);
    if (!(typeof f.bytes === "number" && Number.isSafeInteger(f.bytes) && f.bytes > 0)) errors.push(`${at}.bytes: the exact size, a positive integer`);
    if (f.access !== "open" && f.access !== "registered" && f.access !== "restricted") errors.push(`${at}.access: open, registered or restricted`);
    if (f.licence !== undefined && (typeof f.licence !== "string" || f.licence.length > 120 || sanitizeText(f.licence).stripped.length > 0)) errors.push(`${at}.licence: optional; at most 120 characters, nothing invisible`);
  }
  return errors;
}

/** A data of record as the log carries it: each file's known fields, nothing else. */
export function normaliseData(x: unknown): DataFile[] {
  if (!Array.isArray(x)) return [];
  return (x as Array<Partial<DataFile> | null>).filter((f): f is Partial<DataFile> => !!f && typeof f === "object" && typeof f.sha256 === "string" && HEX64.test(f.sha256)).map((f) => ({
    name: String(f.name ?? ""), url: String(f.url ?? ""), sha256: f.sha256 as string, bytes: typeof f.bytes === "number" ? f.bytes : 0,
    access: f.access === "registered" || f.access === "restricted" ? f.access : "open", ...(typeof f.licence === "string" ? { licence: f.licence } : {}),
  }));
}

/**
 * Whether a basis quotes the registered sentence: its words appear in the
 * quote, ignoring case, spacing, the style of quotation marks and a closing
 * full stop. A claim from human literature may be declared general
 * ("asserted") only on the strength of its own sentence's words, so the
 * archive checks that the words it is given are that sentence's.
 */
export function quotesSentence(basis: string, quote: string): boolean {
  const norm = (t: string) => t.toLowerCase().replace(/[‘’‚‛′]/g, "'").replace(/[“”„‟″]/g, '"').replace(/\s+/g, " ").trim();
  const b = norm(basis).replace(/^["'\s]+|["'.…\s]+$/g, "");
  return b.length >= BASIS.min && norm(quote).includes(b);
}

/** A scope from a web form's fields: scope ("period", "construction" or "asserted"), from, to and basis. Undefined when the form names none. */
export function scopeFromForm(f: { scope?: unknown; from?: unknown; to?: unknown; basis?: unknown }): unknown {
  const kind = typeof f.scope === "string" ? f.scope.trim() : "";
  if (!kind) return undefined;
  const basis = typeof f.basis === "string" ? f.basis.trim() : f.basis;
  return kind === "period" ? { period: { from: typeof f.from === "string" ? f.from.trim() : f.from, to: typeof f.to === "string" ? f.to.trim() : f.to }, basis } : { general: kind, basis };
}

/** A fidelity from a web form's fields: as ("reported" or "adapted") and basis. Undefined when the form names none. */
export function fidelityFromForm(f: { as?: unknown; basis?: unknown }): unknown {
  const as = typeof f.as === "string" ? f.as.trim() : "";
  return as ? { as, basis: typeof f.basis === "string" ? f.basis.trim() : f.basis } : undefined;
}

/** The words a data of record puts on the log (its URLs and licences), for screening with the rest of a declaration. */
export function dataWordsOf(files: ReadonlyArray<{ url?: unknown; licence?: unknown }> | null | undefined): string[] {
  return (files ?? []).flatMap((f) => [f?.url, f?.licence]).filter((t): t is string => typeof t === "string" && t.trim() !== "");
}

/** The SHA-256s of a data of record, sorted and distinct. */
export function dataHashes(files: ReadonlyArray<{ sha256?: unknown }> | null | undefined): string[] {
  return [...new Set((files ?? []).map((f) => f?.sha256).filter((h): h is string => typeof h === "string" && HEX64.test(h)))].sort();
}

/**
 * Whether two claims' scopes can be about the same thing: a general claim
 * overlaps everything; two periods overlap when their spans meet. A claim
 * with no declared scope is treated as general here, so the rule never
 * hides a contradiction it cannot rule out.
 */
export function scopesOverlap(a: ClaimScope | null | undefined, b: ClaimScope | null | undefined): boolean {
  if (!a || !b || !("period" in a) || !("period" in b)) return true;
  return overlaps(a.period, b.period);
}

/* ---------------- what a receipt declares ---------------- */

export type DesignMethod = "stated" | "altered";
export type DesignData = "original" | "new" | "beyond";
export interface Design {
  method: DesignMethod;
  data: DesignData;
  /** Why these data are the claim's own, or cover its population and period, or how they differ. */
  basis: string;
  /** What the method changes (required when altered): words that finish "not robust to reanalysis: …". */
  alteration?: string;
  /** What the data extend to (required when beyond, unless a period says it): words that finish "extension to …". */
  beyond?: string;
  /** The span the analysis covers. Required when the claim has a period. */
  period?: Period;
}

export const ALTERATION = { min: 3, max: 120 } as const;
export const BEYOND = { min: 3, max: 80 } as const;

/**
 * Words that pass a verdict. An alteration or an extension is a label the
 * page composes into a sentence ("Not robust to reanalysis: …"), so it
 * describes a change, never a judgement of the original or its authors: a
 * robustness test says the change matters, not that anyone erred. So these
 * words are refused in those labels (and in a description of an older
 * receipt), and an "alteration" reading "correcting the authors' coding
 * errors" cannot put a verdict on a page that has made none. A basis is shown
 * as its agent's words, in quotation marks with its name, and is screened
 * like any submission. "Error" is a verdict only in some
 * uses: "standard errors", "measurement error" and "error bars" describe
 * statistics, and pass; "coding errors" and "errors in the original" do not.
 */
export const VERDICT_WORDS = /\b(erroneous(?:ly)?|mistakes?|mistaken(?:ly)?|wrong(?:ly)?|fraud(?:ulent)?|fabricat\w*|refut\w*|debunk\w*|flawed|misconduct|incorrect(?:ly)?|bogus|botched)\b|\b(?:coding|data|programming|transcription|clerical|calculation|spreadsheet)\s+errors?\b|\berrors?\s+(?:in|by|of|made by)\s+(?:the\s+)?(?:original|authors?|paper|study|code)\b/i;

/** Latin look-alikes from other scripts, so a verdict cannot pass in Cyrillic or Greek letters. */
const CONFUSABLES: Record<string, string> = {
  "а": "a", "в": "b", "е": "e", "к": "k", "м": "m", "н": "h", "о": "o", "р": "p", "с": "c", "т": "t", "у": "y", "х": "x", "і": "i", "ј": "j", "ѕ": "s", "ԁ": "d", "ԛ": "q", "ԝ": "w", "ӏ": "l", "ɡ": "g",
  "А": "A", "В": "B", "Е": "E", "К": "K", "М": "M", "Н": "H", "О": "O", "Р": "P", "С": "C", "Т": "T", "У": "Y", "Х": "X", "І": "I", "Ј": "J", "Ѕ": "S",
  "α": "a", "ε": "e", "ι": "i", "κ": "k", "ν": "v", "ο": "o", "ρ": "p", "τ": "t", "υ": "u", "χ": "x", "Α": "A", "Β": "B", "Ε": "E", "Ι": "I", "Κ": "K", "Μ": "M", "Ν": "N", "Ο": "O", "Ρ": "P", "Τ": "T", "Χ": "X",
};
/** Whether words pass a verdict, read through compatibility forms, accents and look-alike letters. */
export function passesVerdict(t: string): boolean {
  const folded = t.normalize("NFKC").normalize("NFD").replace(/\p{M}/gu, "").replace(/[^\x00-\x7F]/g, (ch) => CONFUSABLES[ch] ?? ch);
  return VERDICT_WORDS.test(folded);
}

/** What is wrong with a declaration, in the archive's words; empty when nothing is. `code`: the commit's kind. */
export function designProblems(x: unknown, code?: "rerun" | "replication"): string[] {
  const d = x as Partial<Record<keyof Design, unknown>> | null;
  const shape = 'design: {method: "stated" | "altered", data: "original" | "new" | "beyond", basis, alteration?, beyond?, period?}: say, before you run, whether you use the claim\'s stated method and whether your data are the claim\'s own, new data covering its whole population and period, or data beyond them';
  if (!d || typeof d !== "object" || Array.isArray(d)) return [shape];
  const errors: string[] = [];
  if (d.method !== "stated" && d.method !== "altered") errors.push('design.method: "stated" (the claim\'s test, as it states its method) or "altered"');
  if (d.data !== "original" && d.data !== "new" && d.data !== "beyond") errors.push('design.data: "original" (the claim\'s own data, its data of record), "new" (new data covering its whole population and period) or "beyond" (another population or period, or a part of it)');
  const b = textProblem(d.basis, "design.basis", BASIS.min, BASIS.max, "why these data are the claim's own, or cover its population and period, or how they differ");
  if (b) errors.push(b);
  if (d.method === "altered" || d.alteration !== undefined) {
    const t = textProblem(d.alteration, "design.alteration", ALTERATION.min, ALTERATION.max, "what your method changes, in words that finish \"not robust to reanalysis: …\"");
    if (t) errors.push(t);
    else if (passesVerdict(String(d.alteration))) errors.push("design.alteration: describe the change, not a verdict on the original (no words such as coding errors, mistake, wrong, fraud, refuted, debunked or flawed)");
    if (d.method !== "altered") errors.push('design.alteration: only with method "altered"');
  }
  if (d.beyond !== undefined) {
    const t = textProblem(d.beyond, "design.beyond", BEYOND.min, BEYOND.max, "what your data extend to, in words that finish \"extension to …\"");
    if (t) errors.push(t);
    else if (passesVerdict(String(d.beyond))) errors.push("design.beyond: describe the data, not a verdict on the original");
    if (d.data !== "beyond") errors.push('design.beyond: only with data "beyond"');
  }
  if (d.period !== undefined) errors.push(...periodProblems(d.period, "design.period"));
  if (d.data === "beyond" && d.beyond === undefined && d.period === undefined) errors.push('design: with data "beyond", say what the data extend to (beyond) or declare their period');
  // A re-run runs the original's own bundle, which applies the claim's stated method by definition; a changed method is the
  // agent's own implementation. Its data may be the claim's own (a verification), new data its seed draws from the same
  // population (a simulation's ensemble, a fresh fetch of the same period: a reproduction), or data beyond (an extension).
  if (code === "rerun" && d.method !== undefined && d.method !== "stated") errors.push('design.method: a re-run ("rerun") runs the original\'s own bundle, which applies the stated method; a changed method is your own implementation (kind "replication")');
  return errors;
}

export function normaliseDesign(x: unknown): Design | null {
  const d = x as Partial<Record<keyof Design, unknown>> | null;
  if (!d || typeof d !== "object" || Array.isArray(d)) return null;
  if ((d.method !== "stated" && d.method !== "altered") || (d.data !== "original" && d.data !== "new" && d.data !== "beyond") || typeof d.basis !== "string") return null;
  const period = d.period === undefined ? undefined : normalisePeriod(d.period);
  if (period === null) return null;
  return {
    method: d.method, data: d.data, basis: d.basis,
    ...(typeof d.alteration === "string" ? { alteration: d.alteration } : {}),
    ...(typeof d.beyond === "string" ? { beyond: d.beyond } : {}),
    ...(period ? { period } : {}),
  };
}

/* ---------------- kinds ---------------- */

export type ReceiptKind = "verification" | "reproduction" | "reanalysis" | "extension" | "reanalysis-extension";
/** What a receipt counts as: a kind, or "unconfirmed" (it declared a replication test the archive could not confirm), or "undeclared" (filed before receipts said what they test). */
export type EffectiveKind = ReceiptKind | "unconfirmed" | "undeclared";
export const REPLICATION_TESTS: ReadonlySet<EffectiveKind> = new Set<EffectiveKind>(["verification", "reproduction"]);
export const isReplicationTest = (k: EffectiveKind | null | undefined) => !!k && REPLICATION_TESTS.has(k);

/** Clemens's Table 1, from the two facts a receipt declares. */
export function declaredKind(d: Pick<Design, "method" | "data">): ReceiptKind {
  if (d.method === "altered") return d.data === "beyond" ? "reanalysis-extension" : "reanalysis";
  return d.data === "original" ? "verification" : d.data === "new" ? "reproduction" : "extension";
}

export interface ClassifyInput {
  design: Design | null;
  /** The commit's kind, which is about code: "rerun" re-runs the original's own bundle; "replication" is the agent's own implementation. */
  code: "rerun" | "replication";
  /** The claim's scope in force when the receipt was committed; null when none was declared (a claim from human literature registered before scopes existed). */
  scope: ClaimScope | null;
  /** The SHA-256s of the claim's data of record in force at the commit; empty when it has none. */
  record: readonly string[];
  /** The SHA-256s of the bundle's inputs. */
  inputs: readonly string[];
  /** The span the result reports its data cover; null when it reported none; undefined before the result. */
  emitted?: Period | null;
}

export interface Classification {
  declared: ReceiptKind | "undeclared";
  effective: EffectiveKind;
  /** A replication test, after every check: the only receipts that are evidence on the claim. */
  replicationTest: boolean;
  /** Why the archive counts the receipt as something other than it declared, in its words; null when it does not. */
  note: string | null;
}

/**
 * What a receipt counts as. A declared robustness test is taken at its word
 * (saying less than one could is never a gain). A declared replication test
 * counts as one only if nothing the archive can check contradicts it; the
 * service refuses such a commit outright, so a demotion here only meets a
 * hostile or historical entry, or the result's own report of the span its
 * data cover (which may show a part of the period: a subset, an extension).
 */
export function classify(x: ClassifyInput): Classification {
  if (!x.design) return { declared: "undeclared", effective: "undeclared", replicationTest: false, note: null };
  const d = x.design;
  const declared = declaredKind(d);
  const as = (effective: EffectiveKind, note: string | null = null): Classification => ({ declared, effective, replicationTest: isReplicationTest(effective), note });
  if (!REPLICATION_TESTS.has(declared)) return as(declared);
  if (d.data === "original") {
    if (x.record.length === 0) return as("unconfirmed", "the claim has no data of record, so its own data cannot be confirmed");
    if (!x.record.every((h) => x.inputs.includes(h))) return as("unconfirmed", "its inputs do not include the claim's data of record");
  }
  if (d.data === "new" && x.scope === null) return as("unconfirmed", "the claim declared no scope, so new data cannot be shown to sample its population");
  if (x.scope && "period" in x.scope) {
    const claimPeriod = x.scope.period;
    if (!d.period) return as("unconfirmed", "it declared no period on a claim that has one");
    if (!sameMonths(d.period, claimPeriod)) return as("extension", `its period, ${periodWords(d.period)}, is not the claim's, ${periodWords(claimPeriod)}`);
    if (x.emitted === undefined) return as(declared);
    if (x.emitted === null) return as("unconfirmed", "its result reported no period");
    if (!within(x.emitted, d.period)) return as("unconfirmed", "its result reported data outside its declared period");
    if (!reachesEnds(x.emitted, claimPeriod)) return as("extension", `its data cover ${periodWords(x.emitted)}, a part of the claim's period`);
  }
  return as(declared);
}

/* ---------------- describing an older receipt ---------------- */

/**
 * A receipt committed before kinds/0.1 said nothing about what it tests, so
 * it counts as a robustness test. Its own agent may describe it once,
 * afterwards, in words: a reanalysis, an extension, or both. A description
 * changes the words on its page and never a number, and it can never make a
 * receipt a replication test: that would be a declaration made after the
 * outcome was known.
 */
export type Described = "reanalysis" | "extension" | "reanalysis-extension";
export interface Description { as: Described; alteration?: string; beyond?: string; period?: Period }

export function descriptionProblems(x: unknown): string[] {
  const d = x as Partial<Record<keyof Description, unknown>> | null;
  if (!d || typeof d !== "object" || Array.isArray(d)) return ['description: {as: "reanalysis" | "extension" | "reanalysis-extension", alteration?, beyond?, period?}'];
  const errors: string[] = [];
  if (d.as !== "reanalysis" && d.as !== "extension" && d.as !== "reanalysis-extension") errors.push('as: "reanalysis", "extension" or "reanalysis-extension": an older receipt is described as a robustness test, never a replication test');
  const needsAlteration = d.as === "reanalysis" || d.as === "reanalysis-extension";
  const needsBeyond = d.as === "extension" || d.as === "reanalysis-extension";
  if (needsAlteration || d.alteration !== undefined) {
    const t = textProblem(d.alteration, "alteration", ALTERATION.min, ALTERATION.max, "what the method changed");
    if (t) errors.push(t); else if (passesVerdict(String(d.alteration))) errors.push("alteration: describe the change, not a verdict on the original");
  }
  if (d.beyond !== undefined) {
    const t = textProblem(d.beyond, "beyond", BEYOND.min, BEYOND.max, "what the data extended to");
    if (t) errors.push(t); else if (passesVerdict(String(d.beyond))) errors.push("beyond: describe the data, not a verdict on the original");
  }
  if (needsBeyond && d.beyond === undefined && d.period === undefined) errors.push("say what the data extended to (beyond) or give their period");
  if (d.period !== undefined) errors.push(...periodProblems(d.period, "period"));
  return errors;
}

export function normaliseDescription(x: unknown): Description | null {
  const d = x as Partial<Record<keyof Description, unknown>> | null;
  if (!d || typeof d !== "object" || (d.as !== "reanalysis" && d.as !== "extension" && d.as !== "reanalysis-extension")) return null;
  const period = d.period === undefined ? undefined : normalisePeriod(d.period);
  if (period === null) return null;
  return { as: d.as, ...(typeof d.alteration === "string" ? { alteration: d.alteration } : {}), ...(typeof d.beyond === "string" ? { beyond: d.beyond } : {}), ...(period ? { period } : {}) };
}

/* ---------------- words ---------------- */

/** What a robustness result's line says it extends to: the agent's words, else its period's. */
export function extensionTo(x: { beyond?: string; period?: Period }): string | null {
  return x.beyond ? x.beyond : x.period ? periodWords(x.period) : null;
}

/** What a receipt tests, in the archive's words: a re-run's verification says so. */
export function testsWords(c: { effectiveKind: EffectiveKind; kind: "rerun" | "replication" }): string {
  return c.effectiveKind === "verification" && c.kind === "rerun" ? "verification (re-run)" : KIND_WORDS[c.effectiveKind];
}

/** A kind as the pages name it. */
export const KIND_WORDS: Record<EffectiveKind, string> = {
  verification: "verification",
  reproduction: "reproduction",
  reanalysis: "reanalysis",
  extension: "extension",
  "reanalysis-extension": "reanalysis and extension",
  unconfirmed: "robustness test (replication test not confirmed)",
  undeclared: "robustness test (filed before kinds/0.1)",
};
