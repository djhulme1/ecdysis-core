/**
 * sources/0.1: how the record names a human work (Ecdysis v2; Daniel, 5 October 2026: "We need to come up with a
 * fool-proof mechanism to code papers/claims that fall outside that remit so we can map all papers (including conference
 * papers)", and "make the scheme explicit in the protocol and well documented throughout").
 *
 * A claim registered from human literature (claim.external) quotes a sentence of a human work and names the work by its
 * SOURCE: a scheme and an identifier, "scheme:identifier". Until sources/0.1 the record took two schemes, arxiv: and doi:,
 * so it could not name a conference paper with neither (NeurIPS, ICML, JMLR, ICLR, older AAAI and IJCAI papers), a PubMed
 * record without a DOI, a book, or a report only a library indexes. sources/0.1 names every work, in twelve schemes, in
 * this order of precedence:
 *
 *   arxiv       an arXiv e-print                          arxiv:2201.02177, arxiv:cs/0305009
 *   doi         anything with a DOI                       doi:10.1038/s41586-021-03819-2
 *   pmid        a PubMed record                           pmid:27357684
 *   pmcid       a PubMed Central full text                pmcid:PMC4948312
 *   openreview  an OpenReview forum (ICLR, TMLR, ...)     openreview:rJl-b3RcF7
 *   acl         an ACL Anthology paper                    acl:2020.acl-main.463, acl:P19-1001
 *   pmlr        a PMLR paper (ICML, AISTATS, COLT, ...)   pmlr:v119/frankle20a
 *   jmlr        a JMLR paper                              jmlr:v15/srivastava14a
 *   neurips     a NeurIPS (NIPS) proceedings paper        neurips:2019/1113d7a76ffceca1bb350bfe145467c6
 *   openalex    any work OpenAlex indexes                 openalex:W2741809807
 *   isbn        a book                                    isbn:9780262035613
 *   cite        a work no index names                     cite:cheeseman-1991-0a1b2c3d4e5f
 *
 * THE RULES.
 *
 *   1. ONE SPELLING. Each scheme has one canonical spelling of each identifier (SCHEMES below): ASCII, the scheme in lower
 *      case, no version suffix, no URL around it. A registration in any other spelling is refused, and the refusal gives
 *      the canonical one, so the same work is never named two ways by accident and the same sentence of the same work is
 *      registered once (a claim's id is the hash of its source and its quote). nameSource turns a URL or a common
 *      spelling ("arXiv:2201.02177v2", "https://doi.org/10.1038/...", "PMID: 27357684", an OpenReview, ACL Anthology,
 *      PMLR, JMLR or NeurIPS address) into the canonical form, for agents to send; GET /v2/sources?name=... does the same.
 *   2. PRECEDENCE. A work is named by the first scheme in the order above under which its quoted words can be read: its
 *      arXiv id when the sentence is in the arXiv version, else its DOI, and so on down to openalex, isbn and cite. Two
 *      agents quoting the same version then name it alike.
 *   3. THE QUOTED TEXT. The quote is a sentence of the text the source names, as that scheme's own index publishes it:
 *      arXiv's abstract for arxiv:; the publisher's, deposited with Crossref, for doi: (else Europe PMC's or OpenAlex's
 *      record of the same DOI); PubMed's, through Europe PMC, for pmid: and pmcid:; OpenReview's for openreview:; the
 *      proceedings page's for acl:, pmlr:, jmlr: and neurips:; OpenAlex's for openalex:. The quote scout checks it there.
 *      A book (isbn:) and a work no index names (cite:) have no open text to check: their quotes are their registrants'
 *      word, signed, and their claim pages say so.
 *   4. THE WORK, IN WORDS. A registration may give the work as a citation, work {title, authors (family names, first
 *      author first), year, venue?}, and a cite: source must, since its key is derived from those words and the service
 *      recomputes it: cite:<the first author's family name, folded to ASCII letters and digits>-<year>-<the first 12 hex
 *      characters of the SHA-256 of the title, folded>. A title is folded by Unicode compatibility decomposition, accents
 *      off, lower case, æ œ ß as ae oe ss, and every run of characters other than letters and digits made one space,
 *      trimmed. When the work is named in words, the quote scout also compares its title with the title the source's index
 *      gives, so a wrong identifier (a DOI one digit out names another paper) is caught: "wrong-work".
 *
 * A source is a pointer: nothing here moves a number. What a source can carry is bounded the same way everywhere: ASCII
 * only (a homoglyph or an invisible character cannot make two spellings of one work, or one spelling of two), at most
 * SOURCE_MAX characters, and identifiers whose shapes cannot hold a path, a query or markup where they are put into a URL.
 *
 * Pure: no runtime dependencies, nothing read from the environment, so every source recomputes anywhere.
 */
import { sha256, toHex } from "../canonical.js";

export const SOURCES_VERSION = "sources/0.1";

export const SOURCE_SCHEMES = ["arxiv", "doi", "pmid", "pmcid", "openreview", "acl", "pmlr", "jmlr", "neurips", "openalex", "isbn", "cite"] as const;
export type SourceScheme = (typeof SOURCE_SCHEMES)[number];

/** The longest source the record takes. */
export const SOURCE_MAX = 200;

/**
 * Whether a string is a source lower-cased: the record joins a source's observations to its claims by the source in lower
 * case (stakes/0.2), so a key is a source whatever the case of its letters, its identifier in its scheme's shape.
 */
export function isSourceKey(v: string): boolean {
  const m = v.match(/^([a-z]+):(.+)$/);
  if (!m || !(SOURCE_SCHEMES as readonly string[]).includes(m[1]!)) return false;
  const info = SCHEMES[m[1] as SourceScheme];
  return new RegExp(info.id.source, "i").test(m[2]!) && (info.scheme !== "isbn" || isbnCheck(m[2]!));
}

export interface SchemeInfo {
  scheme: SourceScheme;
  /** What it names, in words. */
  names: string;
  /** The canonical identifier: the part after "scheme:". */
  id: RegExp;
  /** The canonical form in words. */
  form: string;
  example: string;
  /** What the quote scout reads to check a quote, in words; null when there is no open text. */
  text: string | null;
  /** Where anyone can look the work up; null when nothing can. */
  resolve: (id: string) => string | null;
}

/** A DOI in a URL: what RFC 3986 lets through a path as it is, and nothing else. */
const urlPart = (s: string) => s.replace(/[^A-Za-z0-9._~:/()\-;@!$&'*+,=]/g, (c) => encodeURIComponent(c));

export const SCHEMES: Readonly<Record<SourceScheme, SchemeInfo>> = {
  arxiv: {
    scheme: "arxiv", names: "an arXiv e-print",
    id: /^(\d{4}\.\d{4,5}|[a-z]+(-[a-z]+)?\/\d{7})$/,
    form: "arxiv:<id>: the new-style id (YYMM.NNNNN) or the old-style one (archive/YYMMNNN, the subject class left out), lower case, no version",
    example: "arxiv:2201.02177", text: "the abstract arXiv publishes",
    resolve: (id) => `https://arxiv.org/abs/${id}`,
  },
  doi: {
    scheme: "doi", names: "anything with a DOI: journals, proceedings, preprint servers (bioRxiv, medRxiv, SSRN, Zenodo), reports",
    id: /^10\.\d{4,9}\/[!#-@[\]_a-z~]{1,150}(?<![.,;:])$/,
    form: "doi:<doi>: the DOI alone, lower case (DOIs are case-insensitive), no https://doi.org/ before it and no punctuation after it",
    example: "doi:10.1038/s41586-021-03819-2", text: "the abstract its publisher deposited with Crossref; failing that, Europe PMC's or OpenAlex's record of the same DOI",
    resolve: (id) => `https://doi.org/${urlPart(id)}`,
  },
  pmid: {
    scheme: "pmid", names: "a PubMed record",
    id: /^[1-9]\d{0,9}$/,
    form: "pmid:<digits>: the PubMed id, no leading zeros",
    example: "pmid:27357684", text: "PubMed's abstract, through Europe PMC",
    resolve: (id) => `https://pubmed.ncbi.nlm.nih.gov/${id}/`,
  },
  pmcid: {
    scheme: "pmcid", names: "a PubMed Central full text",
    id: /^PMC[1-9]\d{0,9}$/,
    form: "pmcid:PMC<digits>: PMC in capitals, no leading zeros",
    example: "pmcid:PMC4948312", text: "the abstract Europe PMC publishes for it",
    resolve: (id) => `https://pmc.ncbi.nlm.nih.gov/articles/${id}/`,
  },
  openreview: {
    scheme: "openreview", names: "an OpenReview forum: ICLR, TMLR and the venues OpenReview hosts",
    id: /^[A-Za-z0-9_-]{5,24}$/,
    form: "openreview:<forum id>: the id after ?id= in the forum's address, its case kept (OpenReview ids are case-sensitive)",
    example: "openreview:rJl-b3RcF7", text: "the abstract OpenReview publishes",
    resolve: (id) => `https://openreview.net/forum?id=${id}`,
  },
  acl: {
    scheme: "acl", names: "an ACL Anthology paper: ACL, EMNLP, NAACL, EACL, COLING, LREC, TACL, CL and their workshops",
    id: /^(\d{4}\.[a-z0-9]+(-[a-z0-9]+)*\.\d{1,4}|[A-Z]\d{2}-\d{4})$/,
    form: "acl:<anthology id>: the new style (2020.acl-main.463) in lower case, or the old style (P19-1001) with its capital letter",
    example: "acl:2020.acl-main.463", text: "the abstract the ACL Anthology publishes",
    resolve: (id) => `https://aclanthology.org/${id}/`,
  },
  pmlr: {
    scheme: "pmlr", names: "a paper in the Proceedings of Machine Learning Research: ICML, AISTATS, COLT, CoRL, UAI and others",
    id: /^v[1-9]\d{0,3}\/[a-z0-9][a-z0-9_-]{1,79}$/,
    form: "pmlr:v<volume>/<key>: as in proceedings.mlr.press/v119/frankle20a.html, lower case",
    example: "pmlr:v119/frankle20a", text: "the abstract on its proceedings page",
    resolve: (id) => `https://proceedings.mlr.press/${id}.html`,
  },
  jmlr: {
    scheme: "jmlr", names: "a paper in the Journal of Machine Learning Research",
    id: /^v[1-9]\d{0,2}\/[a-z0-9][a-z0-9_-]{1,79}$/,
    form: "jmlr:v<volume>/<key>: as in jmlr.org/papers/v15/srivastava14a.html, lower case",
    example: "jmlr:v15/srivastava14a", text: "the abstract on its page",
    resolve: (id) => `https://jmlr.org/papers/${id}.html`,
  },
  neurips: {
    scheme: "neurips", names: "a paper in the NeurIPS (NIPS) proceedings",
    id: /^(19[89]\d|2\d{3})\/[0-9a-f]{32}$/,
    form: "neurips:<year>/<hash>: the year and the 32 hex characters of its proceedings address (…/<year>/hash/<hash>-Abstract…), lower case",
    example: "neurips:2019/1113d7a76ffceca1bb350bfe145467c6", text: "the abstract on its proceedings page",
    resolve: (id) => {
      const [year, hash] = id.split("/");
      return `https://proceedings.neurips.cc/paper_files/paper/${year}/hash/${hash}-Abstract${Number(year) >= 2022 ? "-Conference" : ""}.html`;
    },
  },
  openalex: {
    scheme: "openalex", names: "any work OpenAlex indexes, about 250 million, from every field: what the schemes above do not name",
    id: /^W[1-9]\d{3,11}$/,
    form: "openalex:W<digits>: the work's OpenAlex id, W in capitals",
    example: "openalex:W2741809807", text: "the abstract OpenAlex publishes",
    resolve: (id) => `https://openalex.org/${id}`,
  },
  isbn: {
    scheme: "isbn", names: "a book",
    id: /^97[89]\d{10}$/,
    form: "isbn:<13 digits>: the ISBN-13, no hyphens (an ISBN-10 is written as its ISBN-13), its check digit right",
    example: "isbn:9780262035613", text: null,
    resolve: (id) => `https://openlibrary.org/isbn/${id}`,
  },
  cite: {
    scheme: "cite", names: "a work no index names: a report, a thesis, a talk, an old proceedings paper nobody has indexed",
    id: /^[a-z0-9]{1,40}-\d{4}-[0-9a-f]{12}$/,
    form: "cite:<family>-<year>-<12 hex>: derived from the work's citation (work {title, authors, year}), which the registration must carry",
    example: "cite:cheeseman-1991-0a1b2c3d4e5f", text: null,
    resolve: () => null,
  },
};

export type SourceResult = { ok: true; scheme: SourceScheme; id: string; source: string } | { ok: false; error: string };

const NOT_ASCII = /[^\x21-\x7e]/;

/**
 * A source as the record takes it: canonical, or refused with the reason, and with the canonical spelling when one can
 * be made from what was sent.
 */
export function parseSource(raw: unknown): SourceResult {
  if (typeof raw !== "string" || !raw) return { ok: false, error: "a source names a human work: scheme:identifier (sources/0.1)" };
  if (raw.length > SOURCE_MAX) return { ok: false, error: `at most ${SOURCE_MAX} characters` };
  const bad = raw.match(NOT_ASCII);
  if (bad) return { ok: false, error: `printable ASCII only, with no spaces (sources/0.1): it holds U+${bad[0].codePointAt(0)!.toString(16).toUpperCase().padStart(4, "0")}` };
  const m = raw.match(/^([a-z]+):(.+)$/);
  const info = m && (SOURCE_SCHEMES as readonly string[]).includes(m[1]!) ? SCHEMES[m[1] as SourceScheme] : null;
  if (info && info.id.test(m![2]!) && (info.scheme !== "isbn" || isbnCheck(m![2]!))) return { ok: true, scheme: info.scheme, id: m![2]!, source: raw };
  const named = nameSource(raw);
  if (named.ok) return { ok: false, error: `write it as ${named.source} (sources/0.1's one spelling of it)` };
  if (info) return { ok: false, error: `not ${article(info.scheme)} ${info.scheme}: identifier as sources/0.1 writes one: ${info.form}, for example ${info.example}` };
  return { ok: false, error: `not a scheme sources/0.1 knows: ${SOURCE_SCHEMES.map((s) => `${s}:`).join(", ")}` };
}

/** Whether the string is a source in its canonical form. */
export function isHumanWork(v: unknown): v is string {
  return parseSource(v).ok;
}

/** The scheme of a canonical source, or null. */
export function schemeOf(source: string): SourceScheme | null {
  const r = parseSource(source);
  return r.ok ? r.scheme : null;
}

/** Where anyone can look the work up, for a canonical source; null when nothing can (cite:) or it is not one. */
export function resolverOf(source: string): string | null {
  const r = parseSource(source);
  return r.ok ? SCHEMES[r.scheme].resolve(r.id) : null;
}

/** The scheme's name as a reader knows it. */
export const SCHEME_WORDS: Readonly<Record<SourceScheme, string>> = {
  arxiv: "arXiv", doi: "DOI", pmid: "PubMed", pmcid: "PubMed Central", openreview: "OpenReview", acl: "ACL Anthology",
  pmlr: "PMLR", jmlr: "JMLR", neurips: "NeurIPS proceedings", openalex: "OpenAlex", isbn: "ISBN", cite: "citation key",
};

/**
 * The canonical source for what an agent has in hand: a source in any spelling, a URL of the work's page, or a bare
 * identifier whose shape is unmistakable (a new-style arXiv id, a DOI, a PMC id, an OpenAlex W id, an ISBN). Never a
 * guess: what matches no rule is refused, with the schemes listed.
 */
export function nameSource(raw: unknown): SourceResult {
  if (typeof raw !== "string") return { ok: false, error: "a source names a human work: scheme:identifier (sources/0.1)" };
  const s = raw.trim();
  if (!s || s.length > 2 * SOURCE_MAX) return { ok: false, error: `at most ${SOURCE_MAX} characters` };
  const bad = s.match(/[^\x20-\x7e]/);
  if (bad) return { ok: false, error: `printable ASCII only (sources/0.1): it holds U+${bad[0].codePointAt(0)!.toString(16).toUpperCase().padStart(4, "0")}` };
  const done = (scheme: SourceScheme, id: string): SourceResult => {
    const info = SCHEMES[scheme];
    if (!info.id.test(id) || (scheme === "isbn" && !isbnCheck(id))) return { ok: false, error: `not ${article(scheme)} ${scheme}: identifier as sources/0.1 writes one: ${info.form}, for example ${info.example}` };
    const source = `${scheme}:${id}`;
    return source.length > SOURCE_MAX ? { ok: false, error: `at most ${SOURCE_MAX} characters` } : { ok: true, scheme, id, source };
  };
  const arxivId = (x: string): string => {
    let id = x.replace(/\.pdf$/i, "").replace(/v\d+$/i, "");
    const old = id.match(/^([A-Za-z]+(?:-[A-Za-z]+)?)(?:\.[A-Za-z]{2})?\/(\d{7})$/);
    if (old) id = `${old[1]!.toLowerCase()}/${old[2]}`;
    return id.toLowerCase();
  };
  const fromDoi = (d: string): SourceResult => {
    const doi = d.trim().replace(/[.,;:]+$/, "").toLowerCase();
    const ax = doi.match(/^10\.48550\/arxiv\.(.+)$/);
    return ax ? done("arxiv", arxivId(ax[1]!)) : done("doi", doi);
  };
  // A URL of the work's page.
  const u = s.match(/^(?:https?:\/\/)?([^/?#\s]+)(\/[^?#\s]*)?(\?[^#\s]*)?/i);
  const host = u ? u[1]!.toLowerCase().replace(/^www\./, "") : "";
  const path = u?.[2] ?? "";
  const query = u?.[3] ?? "";
  if (/^https?:\/\//i.test(s) || /^(arxiv\.org|doi\.org|dx\.doi\.org|pubmed\.ncbi\.nlm\.nih\.gov|(www\.)?ncbi\.nlm\.nih\.gov|pmc\.ncbi\.nlm\.nih\.gov|europepmc\.org|openreview\.net|aclanthology\.org|(www\.)?aclweb\.org|proceedings\.mlr\.press|(www\.)?jmlr\.org|proceedings\.neurips\.cc|papers\.nips\.cc|papers\.neurips\.cc|openalex\.org|api\.openalex\.org)\//i.test(s)) {
    let m: RegExpMatchArray | null;
    if (host === "arxiv.org" || host === "export.arxiv.org") {
      if ((m = path.match(/^\/(?:abs|pdf|html|format)\/(.+?)\/?$/))) return done("arxiv", arxivId(safeDecode(m[1]!)));
    }
    if (host === "doi.org" || host === "dx.doi.org") {
      if ((m = path.match(/^\/(10\..+)$/))) return fromDoi(safeDecode(m[1]!));
    }
    if (host === "pubmed.ncbi.nlm.nih.gov" && (m = path.match(/^\/(\d+)\/?$/))) return done("pmid", String(Number(m[1])));
    if (host === "ncbi.nlm.nih.gov" && (m = path.match(/^\/pubmed\/(\d+)\/?$/))) return done("pmid", String(Number(m[1])));
    if ((host === "ncbi.nlm.nih.gov" || host === "pmc.ncbi.nlm.nih.gov") && (m = path.match(/^\/(?:pmc\/)?articles\/(?:pmc)?(\d+)\/?$/i))) return done("pmcid", `PMC${Number(m[1])}`);
    if (host === "europepmc.org") {
      if ((m = path.match(/^\/(?:article|abstract)\/MED\/(\d+)\/?$/i))) return done("pmid", String(Number(m[1])));
      if ((m = path.match(/^\/(?:article\/PMC|articles)\/(pmc\d+)\/?$/i))) return done("pmcid", `PMC${Number(m[1]!.slice(3))}`);
    }
    if (host === "openreview.net" && /^\/(forum|pdf)\/?$/.test(path) && (m = query.match(/[?&]id=([A-Za-z0-9_-]+)(&|$)/))) return done("openreview", m[1]!);
    if (host === "aclanthology.org" && (m = path.match(/^\/([0-9A-Za-z.-]+?)(?:\.pdf|\.bib|\.xml)?\/?$/))) return done("acl", aclId(m[1]!));
    if (host === "aclweb.org" && (m = path.match(/^\/anthology\/([0-9A-Za-z.-]+?)(?:\.pdf|\.bib)?\/?$/))) return done("acl", aclId(m[1]!));
    if (host === "proceedings.mlr.press" && (m = path.match(/^\/(v\d+)\/([a-z0-9_-]+?)(?:\.html|\/[a-z0-9_-]+\.pdf)?\/?$/i))) return done("pmlr", `${m[1]!.toLowerCase()}/${m[2]!.toLowerCase()}`);
    if (host === "jmlr.org") {
      if ((m = path.match(/^\/papers\/(v\d+)\/([a-z0-9_-]+?)(?:\.html)?\/?$/i))) return done("jmlr", `${m[1]!.toLowerCase()}/${m[2]!.toLowerCase()}`);
      if ((m = path.match(/^\/papers\/volume(\d+)\/([a-z0-9_-]+)\/[a-z0-9_-]+\.pdf$/i))) return done("jmlr", `v${Number(m[1])}/${m[2]!.toLowerCase()}`);
    }
    if (["proceedings.neurips.cc", "papers.nips.cc", "papers.neurips.cc"].includes(host) && (m = path.match(/^\/(?:paper_files\/)?paper\/(\d{4})\/(?:hash|file)\/([0-9a-fA-F]{32})-/))) return done("neurips", `${m[1]}/${m[2]!.toLowerCase()}`);
    if ((host === "openalex.org" || host === "api.openalex.org") && (m = path.match(/^\/(?:works\/)?(w\d+)\/?$/i))) return done("openalex", `W${m[1]!.slice(1)}`);
    return { ok: false, error: `sources/0.1 names no work by a ${host || "web"} address: name it by its scheme (${SOURCE_SCHEMES.map((x) => `${x}:`).join(", ")})` };
  }
  // A scheme and an identifier in any spelling.
  const p = s.match(/^([A-Za-z]+)\s*:\s*(.+)$/);
  if (p) {
    const scheme = p[1]!.toLowerCase(), id = p[2]!.trim();
    switch (scheme) {
      case "arxiv": return done("arxiv", arxivId(id.replace(/^arxiv:/i, "")));
      case "doi": return fromDoi(id.replace(/^(https?:\/\/)?(dx\.)?doi\.org\//i, ""));
      case "pmid": return done("pmid", /^\d+$/.test(id) ? String(Number(id)) : id);
      case "pmcid": case "pmc": return /^(pmc)?\d+$/i.test(id) ? done("pmcid", `PMC${Number(id.replace(/^pmc/i, ""))}`) : done("pmcid", id);
      case "openreview": return done("openreview", id);
      case "acl": return done("acl", aclId(id));
      case "pmlr": return done("pmlr", id.toLowerCase().replace(/\.html$/, ""));
      case "jmlr": return done("jmlr", id.toLowerCase().replace(/\.html$/, ""));
      case "neurips": case "nips": return done("neurips", id.toLowerCase());
      case "openalex": return /^w\d+$/i.test(id) ? done("openalex", `W${id.slice(1)}`) : done("openalex", id);
      case "isbn": return isbnOf(id);
      case "cite": return done("cite", id.toLowerCase());
      default: break;
    }
  }
  // A bare identifier whose shape is unmistakable.
  if (/^\d{4}\.\d{4,5}(v\d+)?$/.test(s)) return done("arxiv", arxivId(s));
  if (/^10\.\d{4,9}\//.test(s)) return fromDoi(s);
  if (/^pmc\d+$/i.test(s)) return done("pmcid", `PMC${Number(s.slice(3))}`);
  if (/^w\d{4,12}$/i.test(s)) return done("openalex", `W${s.slice(1)}`);
  if (/^isbn(-1[03])?\b/i.test(s)) return isbnOf(s);
  if (/^(97[89][\d -]{10,16}|\d[\d -]{8,12}[\dXx])$/.test(s) && s.replace(/[ -]/g, "").length >= 10) return isbnOf(s);
  return { ok: false, error: `not a source sources/0.1 can name: write scheme:identifier (${SOURCE_SCHEMES.map((x) => `${x}:`).join(", ")}), or give the work's address` };
}

const article = (word: string) => (/^[aeiou]/.test(word) ? "an" : "a");

function safeDecode(x: string): string {
  try { return decodeURIComponent(x); } catch { return x; }
}

function aclId(id: string): string {
  return /^[A-Za-z]\d{2}-\d{4}$/.test(id) ? id[0]!.toUpperCase() + id.slice(1) : id.toLowerCase();
}

/** An ISBN-13's check digit is right. */
export function isbnCheck(d13: string): boolean {
  if (!/^\d{13}$/.test(d13)) return false;
  const sum = [...d13].reduce((a, c, i) => a + Number(c) * (i % 2 === 0 ? 1 : 3), 0);
  return sum % 10 === 0;
}

/** An ISBN-10 or ISBN-13 in any spelling, as its ISBN-13; refused if its check digit is wrong. */
function isbnOf(raw: string): SourceResult {
  const d = raw.replace(/^isbn(-1[03])?:?\s*/i, "").replace(/[\s-]/g, "").toUpperCase();
  if (/^\d{9}[\dX]$/.test(d)) {
    const ten = [...d].reduce((a, c, i) => a + (c === "X" ? 10 : Number(c)) * (10 - i), 0);
    if (ten % 11 !== 0) return { ok: false, error: "an ISBN-10 whose check digit is wrong" };
    const twelve = `978${d.slice(0, 9)}`;
    const sum = [...twelve].reduce((a, c, i) => a + Number(c) * (i % 2 === 0 ? 1 : 3), 0);
    return { ok: true, scheme: "isbn", id: twelve + String((10 - (sum % 10)) % 10), source: `isbn:${twelve}${(10 - (sum % 10)) % 10}` };
  }
  if (/^\d{13}$/.test(d)) return isbnCheck(d) && SCHEMES.isbn.id.test(d) ? { ok: true, scheme: "isbn", id: d, source: `isbn:${d}` } : { ok: false, error: "an ISBN-13 whose check digit is wrong, or that does not begin 978 or 979" };
  return { ok: false, error: `not an isbn: identifier as sources/0.1 writes one: ${SCHEMES.isbn.form}` };
}

/* ---------------- the work, in words (rule 4) ---------------- */

export interface WorkCitation {
  title: string;
  /** Family names, first author first. */
  authors: string[];
  year: number;
  venue?: string;
}

export const WORK_LIMITS = { title: { min: 5, max: 300 }, authors: { min: 1, max: 20 }, author: { min: 1, max: 60 }, venue: { max: 200 }, firstYear: 1450 } as const;

/** What is wrong with a work's citation (nothing: []). Its year may be at most next year. */
export function workProblems(w: unknown, thisYear: number): string[] {
  const x = w as Partial<WorkCitation> | null;
  if (!x || typeof x !== "object" || Array.isArray(x)) return ["work: {title, authors, year, venue?}: the work, as a citation"];
  const out: string[] = [];
  for (const k of Object.keys(x)) if (!["title", "authors", "year", "venue"].includes(k)) out.push(`work.${k}: not a field of a citation (title, authors, year, venue)`);
  if (typeof x.title !== "string" || x.title.trim().length < WORK_LIMITS.title.min || x.title.length > WORK_LIMITS.title.max) out.push(`work.title: the work's title, ${WORK_LIMITS.title.min} to ${WORK_LIMITS.title.max} characters`);
  if (!Array.isArray(x.authors) || x.authors.length < WORK_LIMITS.authors.min || x.authors.length > WORK_LIMITS.authors.max || x.authors.some((a) => typeof a !== "string" || a.trim().length < WORK_LIMITS.author.min || a.length > WORK_LIMITS.author.max)) {
    out.push(`work.authors: ${WORK_LIMITS.authors.min} to ${WORK_LIMITS.authors.max} family names, first author first, each at most ${WORK_LIMITS.author.max} characters`);
  }
  if (typeof x.year !== "number" || !Number.isInteger(x.year) || x.year < WORK_LIMITS.firstYear || x.year > thisYear + 1) out.push(`work.year: the year it appeared, ${WORK_LIMITS.firstYear} to ${thisYear + 1}`);
  if (x.venue !== undefined && (typeof x.venue !== "string" || !x.venue.trim() || x.venue.length > WORK_LIMITS.venue.max)) out.push(`work.venue: optional; where it appeared, at most ${WORK_LIMITS.venue.max} characters`);
  return out;
}

/** A title folded for comparing and hashing (rule 4). */
export function foldTitle(title: string): string {
  return title.normalize("NFKD").replace(/\p{Mn}/gu, "").toLowerCase().replace(/æ/g, "ae").replace(/œ/g, "oe").replace(/ß/g, "ss")
    .replace(/[^\p{L}\p{N}]+/gu, " ").trim();
}

/** A family name folded to what a cite: key carries: ASCII letters and digits, at most 40; "anon" when nothing is left. */
export function foldFamily(name: string): string {
  const f = name.normalize("NFKD").replace(/\p{Mn}/gu, "").toLowerCase().replace(/æ/g, "ae").replace(/œ/g, "oe").replace(/ß/g, "ss")
    .replace(/[^a-z0-9]+/g, "").slice(0, 40);
  return f || "anon";
}

/** The cite: source a work's citation derives (rule 4): the first author's family name, the year, and the title's hash. */
export async function citeKeyOf(w: Pick<WorkCitation, "title" | "authors" | "year">): Promise<string> {
  const hex = toHex(await sha256(new TextEncoder().encode(foldTitle(w.title))));
  return `cite:${foldFamily(w.authors[0] ?? "")}-${String(w.year).padStart(4, "0")}-${hex.slice(0, 12)}`;
}

/**
 * How far two titles agree, from 0 to 1: the share of the shorter title's words found, in order, in the longer (a
 * subtitle on one side costs nothing). Titles of fewer than three words are too short to judge: null.
 */
export function titleAgreement(a: string, b: string): number | null {
  const x = foldTitle(a).split(" ").filter(Boolean), y = foldTitle(b).split(" ").filter(Boolean);
  const [short, long] = x.length <= y.length ? [x, y] : [y, x];
  if (short.length < 3) return null;
  const prev = new Array<number>(long.length + 1).fill(0), cur = new Array<number>(long.length + 1).fill(0);
  for (let i = 1; i <= short.length; i++) {
    for (let j = 1; j <= long.length; j++) cur[j] = short[i - 1] === long[j - 1] ? prev[j - 1]! + 1 : Math.max(prev[j]!, cur[j - 1]!);
    for (let j = 0; j <= long.length; j++) { prev[j] = cur[j]!; cur[j] = 0; }
  }
  return prev[long.length]! / short.length;
}

/** Below this agreement between the registered title and the source's own, the identifier names another work. */
export const WRONG_WORK_BELOW = 0.6;

/** The scheme table, as GET /v2/sources serves it: data, in precedence order. */
export function sourcesTable(): Array<{ scheme: SourceScheme; names: string; form: string; example: string; text: string | null; resolver: string | null }> {
  return SOURCE_SCHEMES.map((s) => {
    const i = SCHEMES[s];
    const ex = i.example.slice(s.length + 1);
    return { scheme: s, names: i.names, form: i.form, example: i.example, text: i.text, resolver: i.resolve(ex) };
  });
}
