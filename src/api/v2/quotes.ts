/**
 * The quote scout: does a registered claim's quote exist in its source?
 *
 * An external claim is a sentence from human literature with a source, the
 * work named in sources/0.1's one spelling (core/v2/sources.ts). Nothing
 * checked, until 4 October, that the sentence is in the paper: putting false
 * words in a real author's mouth is the costliest error the record can make.
 * On a schedule the scout takes a few unchecked claims, fetches what the
 * source's own index publishes, and compares. What it reads, by scheme
 * (sources/0.1, rule 3):
 *
 *   arxiv:          the arXiv API's abstract and title
 *   doi:            Crossref's abstract (when the publisher deposited one) and title; failing an abstract, Europe PMC's
 *                   record of the DOI, then OpenAlex's
 *   pmid:, pmcid:   Europe PMC's abstract and title (PubMed's)
 *   openreview:     OpenReview's abstract and title
 *   acl:, pmlr:, jmlr:, neurips:   the proceedings page's abstract and title
 *   openalex:       OpenAlex's abstract and title
 *   isbn:, cite:    nothing: a book and a work no index names have no open text; their quotes are their registrants' word
 *
 * and what it finds:
 *
 *   verified         the quote is in the abstract (or the title), word for word after normalisation
 *   mismatch         it nearly is: the nearest stretch of the abstract shares most of its words but not all; an issue is opened
 *   not-in-abstract  it is not: the quote may be from the body of the paper, which the scout cannot read; nothing follows
 *   no-abstract      the source publishes no abstract to check against (or, isbn: and cite:, has no open text)
 *   wrong-work       the registration named the work in words, and the source's own title is another work's: the
 *                    identifier is wrong (a DOI one digit out); an issue is opened
 *   unresolvable     the source does not resolve (a wrong id or DOI); an issue is opened
 *   error            the fetch failed; tried again later
 *
 * The result is off the log (it is an observation about a source, not evidence
 * about the claim) and feeds no number; the claim page shows it. Comparison
 * is deterministic and runs on normalised words: case, quotes, dashes,
 * ligatures, diacritics and spacing are ignored, nothing else.
 */

import { shortDate } from "../../web/design.js";
import type { V2Service } from "./service.js";
import type { IssueRegistry } from "./issues.js";
import { parseSource, titleAgreement, WRONG_WORK_BELOW, type WorkCitation } from "../../core/v2/sources.js";

export type QuoteStatus = "verified" | "mismatch" | "not-in-abstract" | "no-abstract" | "wrong-work" | "unresolvable" | "error";

/** Whose index the scout read: the first half of `where`. */
export type QuoteIndex = "arxiv" | "crossref" | "europepmc" | "openalex" | "openreview" | "proceedings";
export type QuoteWhere = `${QuoteIndex}-abstract` | `${QuoteIndex}-title`;

export interface QuoteCheck {
  claim: string;
  status: QuoteStatus;
  /** What the quote was found in or compared against. */
  where: QuoteWhere | null;
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
  /** Every claim's status in one small read, however many there are (the lists mark quotes not found in their source). */
  statusIndex?(): Promise<Map<string, QuoteStatus>>;
}

export class MemoryQuoteCheckStore implements QuoteCheckStore {
  rows = new Map<string, QuoteCheck>();
  async get(claim: string) { return this.rows.get(claim) ?? null; }
  async put(row: QuoteCheck) { this.rows.set(row.claim, { ...row }); }
  async list(limit: number) { return [...this.rows.values()].slice(0, limit); }
  async statusIndex() { return new Map([...this.rows.values()].map((r) => [r.claim, r.status] as const)); }
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
  /** The account's OpenAlex key, when one is installed (OPENALEX_API_KEY): sent to OpenAlex only, in a header. */
  openAlexKey?: string | null;
}

export class QuoteScout {
  private now: () => Date;
  private fetchImpl: typeof fetch;
  private pause: (ms: number) => Promise<void>;
  constructor(private o: QuoteScoutOptions) {
    this.now = o.now ?? (() => new Date());
    // Wrapped, never stored bare: workerd refuses `fetch` called as a method of another object ("Illegal invocation"), and a
    // scout that kept it as `this.fetchImpl` failed every request on the deployment while passing every test under Node.
    this.fetchImpl = o.fetchImpl ?? ((input, init) => fetch(input, init));
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
      // A failure of the scout's own making is no attempt on the source: until 5 October (#64) every request failed on the
      // Worker with "Illegal invocation", spending claims' four attempts in a day. Those rows start again, at once.
      const ours = prev?.status === "error" && /Illegal invocation/.test(prev.detail ?? "");
      if (prev && !ours && !((prev.status === "error" || prev.status === "unresolvable") && prev.attempts < MAX_ATTEMPTS && Date.parse(prev.checkedAt) < cutoff)) continue;
      if (out.checked > 0) await this.pause(3000);
      const row = await this.check(id, x.source, x.quote, ours ? 1 : (prev?.attempts ?? 0) + 1, x.work ?? null);
      await this.o.store.put(row);
      out.checked++;
      if (row.status === "verified") out.verified++;
      if (row.status === "mismatch") { out.mismatched++; await this.o.issues?.open("quote-mismatch", id, 2, `The quote is not in the source's ${row.where?.replace("-", " ")} as registered; the nearest stretch shares ${Math.round((row.similarity ?? 0) * 100)}% of its words. Nearest: "${row.nearest ?? ""}"`, "scout"); }
      if (row.status === "unresolvable") { out.unresolvable++; if (row.attempts >= 2) await this.o.issues?.open("source-unresolvable", id, 2, `The source ${x.source} did not resolve on ${row.attempts} attempts: ${row.detail ?? ""}`, "scout"); }
      if (row.status === "wrong-work") { out.mismatched++; await this.o.issues?.open("source-wrong-work", id, 2, `The source ${x.source} names another work: its index gives the title "${row.nearest ?? ""}", against the registered "${x.work?.title ?? ""}" (${Math.round((row.similarity ?? 0) * 100)}% of the words agree)`, "scout"); }
      if (row.status === "error") out.errors++;
    }
    return out;
  }

  /** One claim: fetch the source's index entry and compare. Never throws. */
  async check(claim: string, source: string, quote: string, attempts = 1, work: WorkCitation | null = null): Promise<QuoteCheck> {
    const at = this.now().toISOString();
    const base = { claim, checkedAt: at, attempts };
    try {
      // Called through this.fetchImpl, exactly as before readSource was shared (the fetch-binding test pins that behaviour).
      const got = await readSource(source, { fetchImpl: (input, init) => this.fetchImpl(input, init), contact: this.o.contact, openAlexKey: this.o.openAlexKey });
      if (!got.ok) return { ...base, status: got.status, where: null, nearest: null, similarity: null, detail: got.detail };
      // sources/0.1 rule 4: a work named in words whose title the index contradicts is another work.
      if (work?.title && got.title) {
        const agree = titleAgreement(work.title, got.title);
        if (agree !== null && agree < WRONG_WORK_BELOW) return { ...base, status: "wrong-work", where: `${got.kind}-title`, nearest: got.title.slice(0, 300), similarity: Math.round(agree * 1000) / 1000, detail: `registered as "${work.title.slice(0, 200)}"` };
      }
      const texts: Array<[QuoteWhere, string]> = [];
      if (got.abstract) texts.push([`${got.kind}-abstract`, got.abstract]);
      if (got.title) texts.push([`${got.kind}-title`, got.title]);
      if (!texts.length) return { ...base, status: "no-abstract", where: null, nearest: null, similarity: null, detail: got.detail ?? null };
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
}

/** What readSource needs: a fetch, and how to name itself to the indexes. */
export interface ReadSourceOptions {
  fetchImpl: typeof fetch;
  /** Named in the user agent, as Crossref asks. */
  contact?: string;
  /** Sent as the whole user agent instead of the quote scout's (the context writer names itself). */
  userAgent?: string;
  /** The account's OpenAlex key, when one is installed: sent to OpenAlex only, in a header. */
  openAlexKey?: string | null;
}

/** What a source's own index publishes: its abstract and title (sources/0.1, rule 3), read as the quote scout reads them. */
export type SourceText = { ok: true; kind: QuoteIndex; abstract: string | null; title: string | null; detail?: string } | { ok: false; status: "unresolvable" | "error"; detail: string };

/**
 * Read what a source's own index publishes: its abstract and title, by scheme, as the header of this file lists them. Used by
 * the quote scout and by the context writer (context.ts), so both read the same text from the same place. Throws only on a
 * network failure, which callers catch.
 */
/** How long a source's index may take to answer: a request that hangs never holds the cron (which awaits its whole run). */
export const SOURCE_TIMEOUT_MS = 20_000;

export async function readSource(source: string, o: ReadSourceOptions): Promise<SourceText> {
  const ua = o.userAgent ?? `ecdysis-quote-scout/0.2 (https://ecdysis.me; mailto:${o.contact ?? "replies@ecdysis.me"})`;
  const fetchImpl = o.fetchImpl;
  const parsed = parseSource(source);
  if (!parsed.ok) return { ok: false, status: "unresolvable", detail: `not a source in sources/0.1's spelling: ${parsed.error}`.slice(0, 200) };
  const { scheme, id } = parsed;
  const get = (url: string, accept: string, extra: Record<string, string> = {}) => fetchImpl(url, { headers: { "user-agent": ua, accept, ...extra }, signal: AbortSignal.timeout(SOURCE_TIMEOUT_MS) });
  const page = async (url: string, abstractRe: RegExp, titleRe: RegExp | null): Promise<{ ok: true; kind: QuoteIndex; abstract: string | null; title: string | null } | { ok: false; status: "unresolvable" | "error"; detail: string }> => {
    const res = await get(url, "text/html");
    if (res.status === 404) return { ok: false, status: "unresolvable", detail: `the proceedings page is not there (${url.slice(0, 120)})` };
    if (!res.ok) return { ok: false, status: res.status >= 500 ? "error" : "unresolvable", detail: `the proceedings page answered ${res.status}` };
    const html = await res.text();
    const a = html.match(abstractRe)?.[1];
    const t = metaContent(html, "citation_title") ?? (titleRe ? html.match(titleRe)?.[1] ?? null : null);
    return { ok: true, kind: "proceedings", abstract: a ? stripTags(a) || null : null, title: t ? stripTags(t) || null : null };
  };
  switch (scheme) {
    case "arxiv": {
      const res = await get(`https://export.arxiv.org/api/query?id_list=${encodeURIComponent(id)}&max_results=1`, "application/atom+xml");
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
    case "doi": {
      const res = await get(`https://api.crossref.org/works/${encodeURIComponent(id)}`, "application/json");
      if (res.status === 404) return { ok: false, status: "unresolvable", detail: "Crossref knows no such DOI" };
      if (!res.ok) return { ok: false, status: "error", detail: `Crossref ${res.status}` };
      const body = (await res.json().catch(() => null)) as { message?: { abstract?: string; title?: string[] } } | null;
      if (!body?.message) return { ok: false, status: "error", detail: "Crossref answered without a work" };
      const title = body.message.title?.[0] ? stripTags(body.message.title[0]) : null;
      if (body.message.abstract) return { ok: true, kind: "crossref", abstract: stripTags(body.message.abstract), title };
      // No abstract deposited with Crossref: Europe PMC's record of the same DOI, then OpenAlex's (sources/0.1 rule 3).
      const epmc = await europePmc(fetchImpl, `DOI:"${id}"`, ua);
      if (epmc?.abstract) return { ok: true, kind: "europepmc", abstract: epmc.abstract, title: epmc.title ?? title };
      const oa = await openAlexAbstract(fetchImpl, o.openAlexKey ?? null, `doi:${id}`, ua);
      if (oa?.abstract) return { ok: true, kind: "openalex", abstract: oa.abstract, title: oa.title ?? title };
      return { ok: true, kind: "crossref", abstract: null, title };
    }
    case "pmid":
    case "pmcid": {
      const epmc = await europePmc(fetchImpl, scheme === "pmid" ? `EXT_ID:${id} AND SRC:MED` : `PMCID:${id}`, ua);
      if (epmc === null) return { ok: false, status: "error", detail: "Europe PMC did not answer" };
      if (!epmc.found) return { ok: false, status: "unresolvable", detail: `Europe PMC knows no such ${scheme === "pmid" ? "PubMed" : "PubMed Central"} record` };
      return { ok: true, kind: "europepmc", abstract: epmc.abstract, title: epmc.title };
    }
    case "openreview": {
      for (const api of ["https://api2.openreview.net", "https://api.openreview.net"]) {
        const res = await get(`${api}/notes?id=${encodeURIComponent(id)}`, "application/json");
        if (res.status === 403) return { ok: true, kind: "openreview", abstract: null, title: null, detail: "OpenReview asked for a challenge the scout cannot answer" };
        if (!res.ok) continue;
        const body = (await res.json().catch(() => null)) as { notes?: Array<{ content?: Record<string, unknown> }> } | null;
        const c = body?.notes?.[0]?.content;
        if (!c) continue;
        const val = (v: unknown): string | null => typeof v === "string" ? v : v && typeof v === "object" && typeof (v as { value?: unknown }).value === "string" ? (v as { value: string }).value : null;
        return { ok: true, kind: "openreview", abstract: val(c["abstract"]) ? stripTags(val(c["abstract"])!) : null, title: val(c["title"]) ? stripTags(val(c["title"])!) : null };
      }
      return { ok: false, status: "unresolvable", detail: "OpenReview knows no such forum" };
    }
    case "acl": return page(`https://aclanthology.org/${id}/`, /class="card-body acl-abstract"[^>]*>[\s\S]*?<span>([\s\S]*?)<\/span>/, /<h2[^>]*id="title"[^>]*>([\s\S]*?)<\/h2>/);
    case "pmlr": return page(`https://proceedings.mlr.press/${id}.html`, /<div id="abstract"[^>]*>([\s\S]*?)<\/div>/, /<h1>([\s\S]*?)<\/h1>/);
    case "jmlr": return page(`https://jmlr.org/papers/${id}.html`, /<p class="abstract">([\s\S]*?)<\/p>/, /<h2>([\s\S]*?)<\/h2>/);
    case "neurips": {
      const [year, hash] = id.split("/");
      const base = `https://proceedings.neurips.cc/paper_files/paper/${year}/hash/${hash}-Abstract`;
      const tries = Number(year) >= 2022 ? [`${base}-Conference.html`, `${base}-Datasets_and_Benchmarks.html`, `${base}.html`] : [`${base}.html`];
      let last: Awaited<ReturnType<typeof page>> = { ok: false, status: "unresolvable", detail: "the proceedings page is not there" };
      for (const url of tries) {
        last = await page(url, /class="paper-abstract">\s*(?:<p>)?([\s\S]*?)<\/p>/, null);
        if (last.ok || last.status === "error") return last;
      }
      return last;
    }
    case "openalex": {
      const oa = await openAlexAbstract(fetchImpl, o.openAlexKey ?? null, id, ua);
      if (oa === null) return { ok: false, status: "error", detail: "OpenAlex did not answer" };
      if (!oa.found) return { ok: false, status: "unresolvable", detail: "OpenAlex knows no such work" };
      return { ok: true, kind: "openalex", abstract: oa.abstract, title: oa.title };
    }
    case "isbn": return { ok: true, kind: "proceedings", abstract: null, title: null, detail: "a book (isbn:) has no open text the scout can read: the quote is its registrant's word (sources/0.1)" };
    case "cite": return { ok: true, kind: "proceedings", abstract: null, title: null, detail: "a work no index names (cite:) has no open text the scout can read: the quote is its registrant's word (sources/0.1)" };
  }
}

/** Europe PMC's first hit for a query: null if it did not answer. */
async function europePmc(fetchImpl: typeof fetch, query: string, ua: string): Promise<{ found: boolean; abstract: string | null; title: string | null } | null> {
  const res = await fetchImpl(`https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=${encodeURIComponent(query)}&resultType=core&format=json&pageSize=1`, { headers: { "user-agent": ua, accept: "application/json" }, signal: AbortSignal.timeout(SOURCE_TIMEOUT_MS) });
  if (!res.ok) return null;
  const body = (await res.json().catch(() => null)) as { resultList?: { result?: Array<{ abstractText?: string; title?: string }> } } | null;
  const hit = body?.resultList?.result?.[0];
  if (!hit) return { found: false, abstract: null, title: null };
  return { found: true, abstract: hit.abstractText ? stripTags(hit.abstractText) || null : null, title: hit.title ? stripTags(hit.title) || null : null };
}

/** OpenAlex's record of a work ("W…", or "doi:…"): its abstract (rebuilt from the inverted index) and title; null if it did not answer. */
async function openAlexAbstract(fetchImpl: typeof fetch, openAlexKey: string | null, key: string, ua: string): Promise<{ found: boolean; abstract: string | null; title: string | null } | null> {
  const k = openAlexKey?.trim();
  const res = await fetchImpl(`https://api.openalex.org/works/${key.startsWith("doi:") ? `doi:${encodeURIComponent(key.slice(4))}` : encodeURIComponent(key)}?select=title,display_name,abstract_inverted_index`,
    { headers: { "user-agent": ua, accept: "application/json", ...(k ? { authorization: `Bearer ${k}` } : {}) }, signal: AbortSignal.timeout(SOURCE_TIMEOUT_MS) });
  if (res.status === 404) return { found: false, abstract: null, title: null };
  if (!res.ok) return null;
  const w = (await res.json().catch(() => null)) as { title?: string; display_name?: string; abstract_inverted_index?: Record<string, number[]> | null } | null;
  if (!w) return null;
  return { found: true, abstract: invertedAbstract(w.abstract_inverted_index ?? null), title: (w.title ?? w.display_name ?? "").trim() || null };
}

/** An abstract from OpenAlex's inverted index: each word at each of its positions, in order. */
export function invertedAbstract(inv: Record<string, number[]> | null): string | null {
  if (!inv || typeof inv !== "object") return null;
  const at: string[] = [];
  for (const [word, positions] of Object.entries(inv)) {
    if (!Array.isArray(positions)) continue;
    for (const p of positions) if (Number.isInteger(p) && p >= 0 && p < 20000) at[p] = word;
  }
  const text = at.filter((w) => typeof w === "string").join(" ").trim();
  return text || null;
}

/** A <meta name="…" content="…"> value, whichever order and quoting its attributes have. */
export function metaContent(html: string, name: string): string | null {
  const re = new RegExp(`<meta\\b[^>]*\\bname=["']?${name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}["']?[^>]*>`, "i");
  const tagText = html.match(re)?.[0];
  if (!tagText) return null;
  const c = tagText.match(/\bcontent=(?:"([^"]*)"|'([^']*)'|([^\s>]+))/i);
  const v = c ? (c[1] ?? c[2] ?? c[3] ?? "") : "";
  return v ? decodeEntities(v).replace(/\s+/g, " ").trim() : null;
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

/** Each place the scout reads, in a reader's words. */
const WHERE_WORDS: Record<QuoteWhere, string> = {
  "arxiv-abstract": "arXiv abstract", "arxiv-title": "arXiv title", "crossref-abstract": "publisher's abstract", "crossref-title": "publisher's title",
  "europepmc-abstract": "PubMed abstract (Europe PMC)", "europepmc-title": "PubMed title (Europe PMC)", "openalex-abstract": "OpenAlex abstract",
  "openalex-title": "OpenAlex title", "openreview-abstract": "OpenReview abstract", "openreview-title": "OpenReview title",
  "proceedings-abstract": "proceedings page's abstract", "proceedings-title": "proceedings page's title",
};

/** The sentence a claim page shows under a registered quote. */
export function quoteCheckWords(c: QuoteCheck | null): string {
  if (!c) return "The quote has not yet been checked against its source.";
  const when = shortDate(c.checkedAt);
  switch (c.status) {
    case "verified": return `Quote verified against the ${WHERE_WORDS[c.where ?? "crossref-abstract"] ?? "source's abstract"} on ${when}.`;
    case "mismatch": return `The quote differs from the source's ${c.where?.endsWith("title") ? "title" : "abstract"} (${Math.round((c.similarity ?? 0) * 100)}% of its words found in order, checked ${when}); the stewards have been told.`;
    case "not-in-abstract": return `The quote is not in the source's abstract (checked ${when}); it may be from the body of the paper, which is not checked here.`;
    case "no-abstract": return /registrant's word/.test(c.detail ?? "") ? `The source has no open text to check the quote against (a book, or a work no index names): the quote is its registrant's word, signed (sources/0.1; checked ${when}).` : `The source publishes no abstract to check the quote against (checked ${when}).`;
    case "wrong-work": return `The source names another work: its index gives the title ${JSON.stringify(c.nearest ?? "")}, not the one registered (checked ${when}); the stewards have been told.`;
    case "unresolvable": return `The source could not be resolved (checked ${when}); the stewards have been told.`;
    default: return `The source could not be reached (checked ${when}); it will be tried again.`;
  }
}
