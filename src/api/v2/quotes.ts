/**
 * The quote scout: does a registered claim's quote exist in its source?
 *
 * An external claim is a sentence from human literature with a source
 * (arxiv:… or doi:…). Nothing checked, until now, that the sentence is in
 * the paper: putting false words in a real author's mouth is the costliest
 * error the record can make. On a schedule the scout takes a few unchecked
 * claims, fetches what the source's own index publishes (the arXiv API's
 * abstract and title; Crossref's abstract, when the publisher deposited one,
 * and title), and compares:
 *
 *   verified         the quote is in the abstract (or the title), word for word after normalisation
 *   mismatch         it nearly is: the nearest stretch of the abstract shares most of its words but not all; an issue is opened
 *   not-in-abstract  it is not: the quote may be from the body of the paper, which the scout cannot read; nothing follows
 *   no-abstract      the source publishes no abstract to check against
 *   unresolvable     the source does not resolve (a wrong id or DOI); an issue is opened
 *   error            the fetch failed; tried again later
 *
 * The result is off the log (it is an observation about a source, not evidence
 * about the claim) and feeds no number; the claim page shows it. Comparison
 * is deterministic and runs on normalised words: case, quotes, dashes,
 * ligatures, diacritics and spacing are ignored, nothing else.
 */

import type { V2Service } from "./service.js";
import type { IssueRegistry } from "./issues.js";

export type QuoteStatus = "verified" | "mismatch" | "not-in-abstract" | "no-abstract" | "unresolvable" | "error";

export interface QuoteCheck {
  claim: string;
  status: QuoteStatus;
  /** What the quote was found in or compared against. */
  where: "arxiv-abstract" | "arxiv-title" | "crossref-abstract" | "crossref-title" | null;
  /** The best-matching stretch of the source text (for mismatches, so a steward sees the difference). */
  nearest: string | null;
  /** Share of the quote's words found in order in the nearest stretch (1 for verified). */
  similarity: number | null;
  checkedAt: string;
  attempts: number;
  /** For errors and unresolvable sources: what happened. */
  detail: string | null;
}

export interface QuoteCheckStore {
  get(claim: string): Promise<QuoteCheck | null>;
  put(row: QuoteCheck): Promise<void>;
  list(limit: number): Promise<QuoteCheck[]>;
}

export class MemoryQuoteCheckStore implements QuoteCheckStore {
  rows = new Map<string, QuoteCheck>();
  async get(claim: string) { return this.rows.get(claim) ?? null; }
  async put(row: QuoteCheck) { this.rows.set(row.claim, { ...row }); }
  async list(limit: number) { return [...this.rows.values()].slice(0, limit); }
}

/** Below this share of the quote's words, the nearest stretch is not the quote at all: the sentence is from elsewhere in the paper. */
export const MISMATCH_FLOOR = 0.6;
/** Retries for errors and unresolvable sources, then the scout leaves it. */
const MAX_ATTEMPTS = 4;
const RETRY_MS = 6 * 3600 * 1000;

export interface QuoteScoutOptions {
  store: QuoteCheckStore;
  v2: V2Service;
  issues?: IssueRegistry | null;
  fetchImpl?: typeof fetch;
  now?: () => Date;
  /** A pause between fetches (arXiv asks for one request every three seconds). Tests pass a no-op. */
  pause?: (ms: number) => Promise<void>;
  /** Named in the user agent, as Crossref asks. */
  contact?: string;
}

export class QuoteScout {
  private now: () => Date;
  private fetchImpl: typeof fetch;
  private pause: (ms: number) => Promise<void>;
  constructor(private o: QuoteScoutOptions) {
    this.now = o.now ?? (() => new Date());
    this.fetchImpl = o.fetchImpl ?? fetch;
    this.pause = o.pause ?? ((ms) => new Promise((r) => setTimeout(r, ms)));
  }

  /** Check up to `limit` external claims that have no result yet, or whose last attempt failed and is old enough to retry. */
  async run(limit = 6): Promise<{ checked: number; verified: number; mismatched: number; unresolvable: number; errors: number }> {
    const r = await this.o.v2.record();
    const out = { checked: 0, verified: 0, mismatched: 0, unresolvable: 0, errors: 0 };
    const cutoff = this.now().getTime() - RETRY_MS;
    for (const [id, x] of [...r.external.entries()].sort(([a], [b]) => (a < b ? -1 : 1))) {
      if (out.checked >= limit) break;
      if (r.held.has(id)) continue; // out of view: nothing to check until it is back
      const prev = await this.o.store.get(id);
      if (prev && !((prev.status === "error" || prev.status === "unresolvable") && prev.attempts < MAX_ATTEMPTS && Date.parse(prev.checkedAt) < cutoff)) continue;
      if (out.checked > 0) await this.pause(3000);
      const row = await this.check(id, x.source, x.quote, (prev?.attempts ?? 0) + 1);
      await this.o.store.put(row);
      out.checked++;
      if (row.status === "verified") out.verified++;
      if (row.status === "mismatch") { out.mismatched++; await this.o.issues?.open("quote-mismatch", id, 2, `The quote is not in the source's ${row.where?.replace("-", " ")} as registered; the nearest stretch shares ${Math.round((row.similarity ?? 0) * 100)}% of its words. Nearest: "${row.nearest ?? ""}"`, "scout"); }
      if (row.status === "unresolvable") { out.unresolvable++; if (row.attempts >= 2) await this.o.issues?.open("source-unresolvable", id, 2, `The source ${x.source} did not resolve on ${row.attempts} attempts: ${row.detail ?? ""}`, "scout"); }
      if (row.status === "error") out.errors++;
    }
    return out;
  }

  /** One claim: fetch the source's index entry and compare. Never throws. */
  async check(claim: string, source: string, quote: string, attempts = 1): Promise<QuoteCheck> {
    const at = this.now().toISOString();
    const base = { claim, checkedAt: at, attempts };
    try {
      const got = await this.fetchSource(source);
      if (!got.ok) return { ...base, status: got.status, where: null, nearest: null, similarity: null, detail: got.detail };
      const texts: Array<[QuoteCheck["where"], string]> = [];
      if (got.abstract) texts.push([got.kind === "arxiv" ? "arxiv-abstract" : "crossref-abstract", got.abstract]);
      if (got.title) texts.push([got.kind === "arxiv" ? "arxiv-title" : "crossref-title", got.title]);
      if (!texts.length) return { ...base, status: "no-abstract", where: null, nearest: null, similarity: null, detail: null };
      let best: { where: QuoteCheck["where"]; m: ReturnType<typeof matchQuote> } | null = null;
      for (const [where, text] of texts) {
        const m = matchQuote(quote, text);
        if (m.exact) return { ...base, status: "verified", where, nearest: null, similarity: 1, detail: null };
        if (!best || m.similarity > best.m.similarity) best = { where, m };
      }
      const abstractOnly = texts.find(([w]) => w?.endsWith("abstract"));
      if (!abstractOnly) return { ...base, status: "no-abstract", where: null, nearest: null, similarity: null, detail: null };
      if (best && best.m.similarity >= MISMATCH_FLOOR) return { ...base, status: "mismatch", where: best.where, nearest: best.m.nearest, similarity: best.m.similarity, detail: null };
      return { ...base, status: "not-in-abstract", where: null, nearest: null, similarity: best?.m.similarity ?? 0, detail: null };
    } catch (e) {
      return { ...base, status: "error", where: null, nearest: null, similarity: null, detail: String((e as Error)?.message ?? e).slice(0, 200) };
    }
  }

  private async fetchSource(source: string): Promise<{ ok: true; kind: "arxiv" | "crossref"; abstract: string | null; title: string | null } | { ok: false; status: "unresolvable" | "error"; detail: string }> {
    const ua = `ecdysis-quote-scout/0.1 (https://ecdysis.me; mailto:${this.o.contact ?? "replies@ecdysis.me"})`;
    const m = source.match(/^(arxiv|doi):(.+)$/i);
    if (!m) return { ok: false, status: "unresolvable", detail: "not an arxiv: or doi: source" };
    const kind = m[1]!.toLowerCase(), id = m[2]!.trim();
    if (kind === "arxiv") {
      const bare = id.replace(/^arxiv:/i, "").replace(/v\d+$/, "");
      const res = await this.fetchImpl(`https://export.arxiv.org/api/query?id_list=${encodeURIComponent(bare)}&max_results=1`, { headers: { "user-agent": ua, accept: "application/atom+xml" } });
      if (!res.ok) return res.status >= 500 ? { ok: false, status: "error", detail: `arXiv ${res.status}` } : { ok: false, status: "unresolvable", detail: `arXiv ${res.status}` };
      const xml = await res.text();
      const entry = xml.match(/<entry>([\s\S]*?)<\/entry>/)?.[1];
      if (!entry) return { ok: false, status: "unresolvable", detail: "arXiv returned no entry for that id" };
      const title = tag(entry, "title");
      const summary = tag(entry, "summary");
      // A malformed id comes back as an entry titled "Error" whose summary says so; an unknown id as a feed with no entry.
      if (!summary || /^Error$/i.test(title ?? "")) return { ok: false, status: "unresolvable", detail: summary ? `arXiv: ${summary.slice(0, 120)}` : "arXiv knows no such paper" };
      return { ok: true, kind: "arxiv", abstract: summary, title };
    }
    const res = await this.fetchImpl(`https://api.crossref.org/works/${encodeURIComponent(id)}`, { headers: { "user-agent": ua, accept: "application/json" } });
    if (res.status === 404) return { ok: false, status: "unresolvable", detail: "Crossref knows no such DOI" };
    if (!res.ok) return { ok: false, status: "error", detail: `Crossref ${res.status}` };
    const body = (await res.json().catch(() => null)) as { message?: { abstract?: string; title?: string[] } } | null;
    if (!body?.message) return { ok: false, status: "error", detail: "Crossref answered without a work" };
    return { ok: true, kind: "crossref", abstract: body.message.abstract ? stripTags(body.message.abstract) : null, title: body.message.title?.[0] ? stripTags(body.message.title[0]) : null };
  }
}

function tag(xml: string, name: string): string | null {
  const m = xml.match(new RegExp(`<${name}[^>]*>([\\s\\S]*?)</${name}>`));
  return m ? decodeEntities(m[1]!).replace(/\s+/g, " ").trim() : null;
}

function stripTags(s: string): string {
  return decodeEntities(s.replace(/<[^>]+>/g, " ")).replace(/\s+/g, " ").trim();
}

function decodeEntities(s: string): string {
  return s.replace(/&(#x?[0-9a-f]+|amp|lt|gt|quot|apos);/gi, (all, code: string) => {
    if (code[0] === "#") { const n = code[1]?.toLowerCase() === "x" ? parseInt(code.slice(2), 16) : parseInt(code.slice(1), 10); return Number.isFinite(n) ? String.fromCodePoint(n) : all; }
    return { amp: "&", lt: "<", gt: ">", quot: '"', apos: "'" }[code.toLowerCase()] ?? all;
  });
}

/** Words, normalised: lower case, no diacritics, quotes and dashes and ligatures unified, nothing but letters and digits kept. */
export function wordsOf(s: string): string[] {
  const t = s.normalize("NFKD").replace(/[̀-ͯ]/g, "").toLowerCase()
    .replace(/[‘’‚‛′]/g, "'").replace(/[“”„‟″]/g, '"').replace(/[‐-―−]/g, "-")
    .replace(/æ/g, "ae").replace(/œ/g, "oe").replace(/ß/g, "ss");
  return t.split(/[^a-z0-9']+/).map((w) => w.replace(/^'+|'+$/g, "")).filter((w) => w.length > 0);
}

/**
 * Is the quote in the text? Exact: its normalised words appear consecutively. Otherwise the nearest stretch of the text of
 * the quote's length, by the share of the quote's words found there in order (a longest common subsequence), as a number
 * in [0, 1], with that stretch returned so a steward can see what differs.
 */
export function matchQuote(quote: string, text: string): { exact: boolean; similarity: number; nearest: string } {
  const q = wordsOf(quote), t = wordsOf(text);
  if (q.length === 0 || t.length === 0) return { exact: false, similarity: 0, nearest: "" };
  const joinedT = ` ${t.join(" ")} `, joinedQ = ` ${q.join(" ")} `;
  if (joinedT.includes(joinedQ)) return { exact: true, similarity: 1, nearest: q.join(" ") };
  let best = 0, at = 0;
  const n = q.length;
  // Windows a little longer than the quote, so a quote with a word dropped from the source still lines up.
  const width = Math.min(t.length, n + Math.ceil(n / 5) + 2);
  for (let i = 0; i + Math.min(width, t.length) <= t.length; i++) {
    const window = t.slice(i, i + width);
    const l = lcs(q, window);
    if (l > best) { best = l; at = i; }
    if (best === n) break;
  }
  return { exact: false, similarity: best / n, nearest: t.slice(at, at + width).join(" ") };
}

function lcs(a: string[], b: string[]): number {
  const prev = new Array<number>(b.length + 1).fill(0);
  const cur = new Array<number>(b.length + 1).fill(0);
  for (let i = 1; i <= a.length; i++) {
    for (let j = 1; j <= b.length; j++) cur[j] = a[i - 1] === b[j - 1] ? prev[j - 1]! + 1 : Math.max(prev[j]!, cur[j - 1]!);
    for (let j = 0; j <= b.length; j++) { prev[j] = cur[j]!; cur[j] = 0; }
  }
  return prev[b.length]!;
}

/** The sentence a claim page shows under a registered quote. */
export function quoteCheckWords(c: QuoteCheck | null): string {
  if (!c) return "The quote has not yet been checked against its source.";
  const when = c.checkedAt.slice(0, 10);
  switch (c.status) {
    case "verified": return `Quote verified against the ${c.where === "arxiv-abstract" ? "arXiv abstract" : c.where === "arxiv-title" ? "arXiv title" : c.where === "crossref-abstract" ? "publisher's abstract" : "publisher's title"} on ${when}.`;
    case "mismatch": return `The quote differs from the source's ${c.where?.endsWith("title") ? "title" : "abstract"} (${Math.round((c.similarity ?? 0) * 100)}% of its words found in order, checked ${when}); the stewards have been told.`;
    case "not-in-abstract": return `The quote is not in the source's abstract (checked ${when}); it may be from the body of the paper, which is not checked here.`;
    case "no-abstract": return `The source publishes no abstract to check the quote against (checked ${when}).`;
    case "unresolvable": return `The source could not be resolved (checked ${when}); the stewards have been told.`;
    default: return `The source could not be reached (checked ${when}); it will be tried again.`;
  }
}
