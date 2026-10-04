/**
 * Stakes (stakes/0.1): how much rests on a claim, on and off the record
 * (Ecdysis v2; design: claude/ecdysis-claims-map-design.md §3, Daniel,
 * 4 October 2026: "we shouldn't give any credence to citations, but it
 * might help direct agents towards claims in high-impact papers").
 *
 * Two sources, one unit:
 *
 *   use U     what rests on the claim ON the record: the papers that build
 *             on it, weighted by the citing operator's tier and independence
 *             (credence.ts). Unchanged here.
 *   reach R   what the literature has built on the claim's source paper OFF
 *             the record, read from the public citation graph by the
 *             platform's stakes scout and never supplied by an agent: the
 *             source's citation count C as OpenAlex (or a fallback index)
 *             reports it, logged as a dated source.observed entry so the
 *             number recomputes from the log. A paper younger than
 *             YOUNG_YEARS has not accrued citations, so for it the venue's
 *             expected citations stand in: R = max(C, venue's two-year mean
 *             citedness × 2). Author h-index is not used: it measures the
 *             person, not the claim.
 *
 *   S = U + log2(1 + R)
 *
 * Each doubling of citations adds one unit of stakes, so a paper with a
 * thousand citations counts like a claim with ten dependants on the record.
 * The log compresses a measure that is inflated and noisy (self-citation,
 * review articles, fashion) into a direction number, and says plainly that
 * it is one. Stakes enter the frontier's value of checking and the pressure
 * on blocked claims (attempts.ts), and nothing else: credence, the statuses,
 * dispute and reliability never see a citation. Claims of one paper share
 * its reach. Pure: no runtime dependencies, no environment.
 */

export const STAKES_VERSION = "stakes/0.1";

export const STAKES_PARAMS = {
  /** A source younger than this (by publication year) takes its venue's expected citations when they exceed its own. */
  youngYears: 2,
  /** The venue's two-year mean citedness counts for this many years of expected citations. */
  venueYears: 2,
} as const;

export const OBSERVATION_PROVIDERS = ["openalex", "semanticscholar", "crossref"] as const;
export type ObservationProvider = (typeof OBSERVATION_PROVIDERS)[number];

/** What the stakes scout observed about a registered source, as logged (source.observed). */
export interface SourceObservation {
  /** The source as registered, lower-cased: "arxiv:…" or "doi:…". */
  source: string;
  provider: ObservationProvider;
  /** The provider's id for the work (an OpenAlex W…, a Semantic Scholar paper id, or the DOI). */
  work: string | null;
  /** Citations the provider counts for the work. */
  citedBy: number;
  /** The venue's two-year mean citedness (an impact-factor-like figure), when the provider gives one. */
  venueCitedness: number | null;
  /** The work's publication year, when known. */
  year: number | null;
  /** The field the provider places the work in (OpenAlex's 26 fields, a Semantic Scholar field of study, or an arXiv category). */
  field: string | null;
  /** No open index knew the work when the scout looked: reach 0 until the next refresh. */
  unresolved: boolean;
  /** When the observation was made (the log's time of the entry). */
  observedAt: string;
  seq: number;
}

const num = (v: unknown): number | null => (typeof v === "number" && Number.isFinite(v) ? v : null);
const str = (v: unknown): string | null => (typeof v === "string" && v.trim() ? v.trim() : null);

/** Read a source.observed payload; null when it is not one (a hostile or malformed entry changes nothing). */
export function parseObservation(p: Record<string, unknown>, seq: number, ts: string): SourceObservation | null {
  const source = str(p["source"])?.toLowerCase() ?? null;
  const provider = str(p["provider"]);
  const citedBy = num(p["citedBy"]);
  if (!source || !/^(arxiv:|doi:)/.test(source) || !provider || !(OBSERVATION_PROVIDERS as readonly string[]).includes(provider) || citedBy === null || citedBy < 0) return null;
  const year = num(p["year"]);
  const venue = num(p["venueCitedness"]);
  return {
    source, provider: provider as ObservationProvider, work: str(p["work"]), citedBy: Math.floor(citedBy),
    venueCitedness: venue === null ? null : Math.max(0, venue),
    year: year !== null && year >= 1800 && year <= 2200 ? Math.floor(year) : null,
    field: str(p["field"]), unresolved: p["unresolved"] === true, observedAt: ts, seq,
  };
}

/**
 * Reach: the source's citations, or for a young source its venue's expected citations when larger. `now` fixes what "young"
 * means, so the same log gives the same numbers on the same day anywhere.
 */
export function reachOf(obs: SourceObservation | null | undefined, now: Date): number {
  if (!obs) return 0;
  const cited = Math.max(0, obs.citedBy);
  if (obs.year === null || obs.venueCitedness === null) return cited;
  const age = now.getUTCFullYear() - obs.year;
  const young = age < STAKES_PARAMS.youngYears;
  return young ? Math.max(cited, obs.venueCitedness * STAKES_PARAMS.venueYears) : cited;
}

/** S = U + log2(1 + R). */
export function stakesOf(use: number, reach: number): number {
  return Math.max(0, use) + Math.log2(1 + Math.max(0, reach));
}
