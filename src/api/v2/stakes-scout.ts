/**
 * The stakes scout (stakes/0.1): reads each registered source's reach from
 * the public citation graph and logs it, so every claim's stakes recompute
 * from the log (design: claude/ecdysis-claims-map-design.md §3 and §5a).
 *
 * On the cron it takes a few registered sources that were never observed, or
 * whose observation is older than REFRESH_MS, and asks the graph:
 *
 *   OpenAlex first   https://api.openalex.org/works/doi:<doi>  (an arXiv id is
 *                    asked for as its DataCite DOI, 10.48550/arXiv.<id>): the
 *                    citation count, the publication year, the field of its
 *                    primary topic (OpenAlex's 26 fields), and for a work with
 *                    a venue the venue's two-year mean citedness from
 *                    /sources/<id>, which stands in for a young paper's
 *                    citations (stakes.ts).
 *   Semantic Scholar https://api.semanticscholar.org/graph/v1/paper/arXiv:<id>
 *   when OpenAlex    (or DOI:<doi>): the citation count, the year and a field
 *   knows nothing    of study. No venue figure.
 *
 * What it writes is a source.observed entry, the platform's observation, as
 * check.seal is the platform's seal: {source, provider, work, citedBy,
 * venueCitedness?, year?, field?}, or {…, unresolved: true, citedBy: 0} when
 * no index knows the work, so the source is not asked about again until the
 * next refresh. A provider that errors (5xx, a network failure) is left for
 * the next run; nothing is logged for it. Agents never write these entries:
 * the service has no endpoint for them, so no agent can inflate a stake.
 *
 * Both indexes are open (OpenAlex CC0; Semantic Scholar's open API) and both
 * ask for a named user agent and a gentle pace: one source a second here, a
 * few sources a run.
 */

import type { TransparencyLog } from "../../core/log.js";
import type { V2Service } from "./service.js";
import type { ObservationProvider } from "../../core/v2/stakes.js";

/** How often a source is asked about again. Citation counts move slowly; a month keeps the record current enough and the indexes unbothered. */
export const REFRESH_MS = 30 * 24 * 3600 * 1000;
const PAUSE_MS = 1000;

export interface Observed {
  provider: ObservationProvider;
  work: string | null;
  citedBy: number;
  venueCitedness: number | null;
  year: number | null;
  field: string | null;
}

export interface StakesScoutOptions {
  v2: V2Service;
  log: TransparencyLog;
  fetchImpl?: typeof fetch;
  now?: () => Date;
  /** A pause between sources. Tests pass a no-op. */
  pause?: (ms: number) => Promise<void>;
  /** Named in the user agent, as both indexes ask. */
  contact?: string;
}

export class StakesScout {
  private now: () => Date;
  private fetchImpl: typeof fetch;
  private pause: (ms: number) => Promise<void>;
  constructor(private o: StakesScoutOptions) {
    this.now = o.now ?? (() => new Date());
    this.fetchImpl = o.fetchImpl ?? fetch;
    this.pause = o.pause ?? ((ms) => new Promise((r) => setTimeout(r, ms)));
  }

  /** Observe up to `limit` sources due for it: never observed first, then the stalest. */
  async run(limit = 5): Promise<{ observed: number; unresolved: number; errors: number }> {
    const r = await this.o.v2.record();
    const out = { observed: 0, unresolved: 0, errors: 0 };
    const cutoff = this.now().getTime() - REFRESH_MS;
    const sources = new Map<string, string>(); // lower-cased → as registered
    for (const [id, x] of r.external) if (!r.held.has(id) && x.source) sources.set(x.source.toLowerCase(), x.source);
    const due = [...sources.entries()]
      .map(([key, source]) => ({ key, source, last: r.observations.get(key)?.observedAt ?? null }))
      .filter((s) => s.last === null || Date.parse(s.last) < cutoff)
      .sort((a, b) => (a.last === null ? -1 : b.last === null ? 1 : Date.parse(a.last) - Date.parse(b.last)) || (a.key < b.key ? -1 : 1))
      .slice(0, limit);
    let first = true;
    for (const s of due) {
      if (!first) await this.pause(PAUSE_MS);
      first = false;
      const got = await this.observe(s.source);
      if (got.status === "error") { out.errors++; continue; }
      if (got.status === "unresolved") {
        out.unresolved++;
        await this.o.log.append("source.observed", { source: s.key, provider: "openalex", work: null, citedBy: 0, unresolved: true, detail: got.detail.slice(0, 200) });
        continue;
      }
      const o = got.observed;
      await this.o.log.append("source.observed", {
        source: s.key, provider: o.provider, work: o.work, citedBy: o.citedBy,
        ...(o.venueCitedness !== null ? { venueCitedness: round3(o.venueCitedness) } : {}), ...(o.year !== null ? { year: o.year } : {}), ...(o.field ? { field: o.field } : {}),
      });
      out.observed++;
    }
    return out;
  }

  /** One source: OpenAlex, then Semantic Scholar. Never throws. */
  async observe(source: string): Promise<{ status: "observed"; observed: Observed } | { status: "unresolved"; detail: string } | { status: "error"; detail: string }> {
    const m = source.match(/^(arxiv|doi):(.+)$/i);
    if (!m) return { status: "unresolved", detail: "not an arxiv: or doi: source" };
    const kind = m[1]!.toLowerCase(), id = m[2]!.trim();
    const arxivId = kind === "arxiv" ? id.replace(/^arxiv:/i, "").replace(/v\d+$/, "") : null;
    const doi = kind === "doi" ? id : `10.48550/arXiv.${arxivId}`;
    try {
      const oa = await this.openAlex(doi, kind === "doi");
      if (oa.status === "observed" || oa.status === "error") return oa;
      const s2 = await this.semanticScholar(arxivId ? `arXiv:${arxivId}` : `DOI:${doi}`);
      if (s2.status === "observed" || s2.status === "error") return s2;
      return { status: "unresolved", detail: `${oa.detail}; ${s2.detail}` };
    } catch (e) {
      return { status: "error", detail: String((e as Error)?.message ?? e).slice(0, 200) };
    }
  }

  private ua(): string {
    return `ecdysis-stakes-scout/0.1 (https://ecdysis.me; mailto:${this.o.contact ?? "replies@ecdysis.me"})`;
  }

  private async openAlex(doi: string, withVenue: boolean): Promise<{ status: "observed"; observed: Observed } | { status: "unresolved"; detail: string } | { status: "error"; detail: string }> {
    const mailto = encodeURIComponent(this.o.contact ?? "replies@ecdysis.me");
    const res = await this.fetchImpl(`https://api.openalex.org/works/doi:${encodeURIComponent(doi)}?mailto=${mailto}`, { headers: { "user-agent": this.ua(), accept: "application/json" } });
    if (res.status === 404) return { status: "unresolved", detail: "OpenAlex knows no such work" };
    if (!res.ok) return { status: "error", detail: `OpenAlex ${res.status}` };
    const w = (await res.json().catch(() => null)) as OpenAlexWork | null;
    if (!w || typeof w !== "object") return { status: "error", detail: "OpenAlex answered without a work" };
    const citedBy = typeof w.cited_by_count === "number" && Number.isFinite(w.cited_by_count) ? Math.max(0, Math.floor(w.cited_by_count)) : 0;
    const year = typeof w.publication_year === "number" && Number.isFinite(w.publication_year) ? w.publication_year : null;
    const field = w.primary_topic?.field?.display_name?.trim() || null;
    let venueCitedness: number | null = null;
    const venue = w.primary_location?.source?.id;
    if (withVenue && typeof venue === "string" && /openalex\.org\/S\d+$/i.test(venue)) {
      const sid = venue.slice(venue.lastIndexOf("/") + 1);
      const sres = await this.fetchImpl(`https://api.openalex.org/sources/${encodeURIComponent(sid)}?mailto=${mailto}`, { headers: { "user-agent": this.ua(), accept: "application/json" } });
      if (sres.ok) {
        const src = (await sres.json().catch(() => null)) as { summary_stats?: Record<string, unknown> } | null;
        const v = src?.summary_stats?.["2yr_mean_citedness"];
        if (typeof v === "number" && Number.isFinite(v) && v >= 0) venueCitedness = v;
      }
    }
    const work = typeof w.id === "string" ? w.id.replace(/^https?:\/\/openalex\.org\//i, "") : null;
    return { status: "observed", observed: { provider: "openalex", work, citedBy, venueCitedness, year, field } };
  }

  private async semanticScholar(paperId: string): Promise<{ status: "observed"; observed: Observed } | { status: "unresolved"; detail: string } | { status: "error"; detail: string }> {
    const res = await this.fetchImpl(`https://api.semanticscholar.org/graph/v1/paper/${encodeURIComponent(paperId)}?fields=citationCount,year,s2FieldsOfStudy,paperId`, { headers: { "user-agent": this.ua(), accept: "application/json" } });
    if (res.status === 404) return { status: "unresolved", detail: "Semantic Scholar knows no such paper" };
    if (!res.ok) return { status: "error", detail: `Semantic Scholar ${res.status}` };
    const p = (await res.json().catch(() => null)) as S2Paper | null;
    if (!p || typeof p !== "object") return { status: "error", detail: "Semantic Scholar answered without a paper" };
    const citedBy = typeof p.citationCount === "number" && Number.isFinite(p.citationCount) ? Math.max(0, Math.floor(p.citationCount)) : 0;
    const year = typeof p.year === "number" && Number.isFinite(p.year) ? p.year : null;
    const field = Array.isArray(p.s2FieldsOfStudy) ? (p.s2FieldsOfStudy.find((f) => typeof f?.category === "string")?.category ?? null) : null;
    return { status: "observed", observed: { provider: "semanticscholar", work: typeof p.paperId === "string" ? p.paperId : null, citedBy, venueCitedness: null, year, field } };
  }
}

interface OpenAlexWork {
  id?: string;
  cited_by_count?: number;
  publication_year?: number;
  primary_topic?: { display_name?: string; field?: { display_name?: string } } | null;
  primary_location?: { source?: { id?: string; display_name?: string } | null } | null;
}
interface S2Paper {
  paperId?: string;
  citationCount?: number;
  year?: number;
  s2FieldsOfStudy?: Array<{ category?: string; source?: string }>;
}

const round3 = (x: number) => Math.round(x * 1000) / 1000;
