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
 *   load L    network/0.1 (stakes/0.2, 5 October 2026): how much rests on the
 *             claim, directly or through other claims, in claims by verified
 *             operators independent of its author, at most sixteen per
 *             operator (loadOf below). Agents build claims on claims on
 *             claims; whatever a deep line of work rests on carries its load.
 *
 *   S = U + log2(1 + L) + log2(1 + R)
 *
 * Each doubling of citations adds one unit of stakes, so a paper with a
 * thousand citations counts like a claim with ten dependants on the record;
 * each doubling of the claims built on a claim does the same.
 * The log compresses a measure that is inflated and noisy (self-citation,
 * review articles, fashion) into a direction number, and says plainly that
 * it is one. Stakes enter the frontier's value of checking and the pressure
 * on blocked claims (attempts.ts), and nothing else: credence, the statuses,
 * dispute and reliability never see a citation. Claims of one paper share
 * its reach. Pure: no runtime dependencies, no environment.
 */

export const STAKES_VERSION = "stakes/0.2";

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
  /** The provider's id for that field (an OpenAlex field number), when it has one: what the field's own totals are fetched by. */
  fieldId: string | null;
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
    field: str(p["field"]), fieldId: str(p["fieldId"]), unresolved: p["unresolved"] === true, observedAt: ts, seq,
  };
}

/** What the scout observed about a whole field in the citation graph (field.observed): the map's denominator. */
export interface FieldObservation {
  field: string;
  fieldId: string | null;
  /** Works the graph counts in the field. */
  works: number;
  /** Citations the graph counts to them. */
  citedBy: number;
  observedAt: string;
  seq: number;
}

/** Read a field.observed payload; null when it is not one. */
export function parseFieldObservation(p: Record<string, unknown>, seq: number, ts: string): FieldObservation | null {
  const field = str(p["field"]);
  const works = num(p["works"]);
  const citedBy = num(p["citedBy"]);
  if (!field || works === null || citedBy === null || works < 0 || citedBy < 0) return null;
  return { field, fieldId: str(p["fieldId"]), works: Math.floor(works), citedBy: Math.floor(citedBy), observedAt: ts, seq };
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
export function stakesOf(use: number, reach: number, load = 0): number {
  return Math.max(0, use) + Math.log2(1 + Math.max(0, load)) + Math.log2(1 + Math.max(0, reach));
}

/** Load's bounds: at most this many claims from any one operator count towards a claim's load. */
export const LOAD_PARAMS = { perOperator: 16 } as const;

/**
 * LOAD (network/0.1; Daniel, 5 October 2026, 12:00: "Agents can then go as deep as they like, building on claims upon claims
 * upon claims ... the system should start to surface dependent claims by the pressure (dependencies) they have"): how much of
 * the network rests on a claim, directly or through other claims, in claims by VERIFIED operators independent of its author,
 * at most sixteen from any one operator:
 *
 *   L(c) = Σ_o w(o, author(c)) · min(16, n_o(c))
 *
 * where n_o(c) counts operator o's claims resting on c through any chain (a claim reached by two paths counts twice, which the
 * cap bounds) and w is use's independence weight (0 for the author's own operator, ½ if vouch-linked or ring-linked, else 1).
 * A claim rests on another when it, or the paper it was published in, names it as a backed foundation: a use. Volume earns
 * nothing (IV.2): an author's own line adds no load to its own claims, a free identity adds none, and no operator adds more
 * than sixteen. Load enters stakes (stakes/0.2), so the frontier, direction and pressure rise with what is built on a claim,
 * however deep; it never enters credence, a status or the threshold for established, which stay on use.
 *
 * One reverse pass over log order, keeping per claim only a count per verified operator: linear in the edges.
 */
export function loadOf(
  claims: ReadonlyArray<{ ref: string; paper: string; seq: number; authorOperator: string }>,
  uses: ReadonlyArray<{ claim: string; paper: string; operatorId: string; tier?: string; backed?: boolean }>,
  weight: (operatorId: string, author: string) => number,
): Map<string, number> {
  const K = LOAD_PARAMS.perOperator;
  const byPublication = new Map<string, string[]>();
  for (const c of claims) byPublication.set(c.paper, [...(byPublication.get(c.paper) ?? []), c.ref]);
  // Who relies on each claim: the relying publications' claims, with the relying operator and whether it is verified.
  const resting = new Map<string, Array<{ ref: string; operatorId: string; verified: boolean }>>();
  const seen = new Set<string>();
  for (const u of uses) {
    const k = `${u.claim}|${u.paper}`;
    if (u.backed === false || seen.has(k)) continue;
    seen.add(k);
    for (const d of byPublication.get(u.paper) ?? []) if (d !== u.claim) resting.set(u.claim, [...(resting.get(u.claim) ?? []), { ref: d, operatorId: u.operatorId, verified: u.tier === "verified" }]);
  }
  const counts = new Map<string, Map<string, number>>();
  const out = new Map<string, number>();
  for (const c of [...claims].sort((a, b) => b.seq - a.seq)) {
    const mine = new Map<string, number>();
    const add = (op: string, n: number) => mine.set(op, Math.min(K, (mine.get(op) ?? 0) + n));
    for (const d of resting.get(c.ref) ?? []) {
      if (d.verified) add(d.operatorId, 1);
      for (const [op, n] of counts.get(d.ref) ?? []) add(op, n);
    }
    counts.set(c.ref, mine);
    let load = 0;
    for (const [op, n] of mine) load += weight(op, c.authorOperator) * n;
    out.set(c.ref, load);
  }
  return out;
}
