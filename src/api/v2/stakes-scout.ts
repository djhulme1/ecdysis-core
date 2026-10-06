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
 *   when OpenAlex    (or DOI:, PMID:, PMCID:, ACL:<id>): the citation count, the
 *   knows nothing    year and a field of study. No venue figure.
 *
 * sources/0.1: OpenAlex is asked by DOI (an arXiv id as its DataCite DOI),
 * PubMed or PubMed Central id, or the work's own W id; Semantic Scholar by
 * arXiv id, DOI, PubMed, PubMed Central or ACL Anthology id. A source neither
 * looks works up by (openreview:, pmlr:, jmlr:, neurips:, isbn:, cite:) is
 * left unresolved, and so has no reach until it does.
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
 *
 * direction/0.1: for each field the record has sources in, the scout also
 * reads the field's most-cited works from OpenAlex, once a month, into the
 * candidates store (not the log: they are direction, never a number about
 * any claim), so the heartbeat and the map can say which load-bearing works
 * are not yet on the record.
 */

import { nameSource, parseSource } from "../../core/v2/sources.js";
import type { TransparencyLog } from "../../core/log.js";
import type { V2Service } from "./service.js";
import type { ObservationProvider } from "../../core/v2/stakes.js";
import type { Candidate } from "../../core/v2/direction.js";

/** Where the registration candidates live between runs (ops state in production, memory in tests). */
export interface CandidateStore {
  get(): Promise<CandidateSet | null>;
  put(set: CandidateSet): Promise<void>;
}
export interface CandidateSet {
  /** By OpenAlex field id. */
  fields: Record<string, { field: string; observedAt: string; works: Candidate[] }>;
}
/** Works read per field: enough to direct a season's registrations, few enough to read in one request. */
export const CANDIDATES_PER_FIELD = 25;

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
  /** OpenAlex's id for the field (the number after /fields/), so the field's own totals can be fetched for the map. */
  fieldId: string | null;
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
  /** direction/0.1: where the fields' most-cited works are kept for the registration queue. Absent: none are read. */
  candidates?: CandidateStore;
  /**
   * An OpenAlex API key (free, per account). Without one, every request counts against a daily budget OpenAlex shares among
   * everyone behind the same IP address, which a Worker's shared egress exhausts: the field totals and the field lists then
   * answer 429. Sent as a bearer header, never in a URL, so it appears in no log and no observation.
   */
  apiKey?: string | null;
}

export class StakesScout {
  private now: () => Date;
  private fetchImpl: typeof fetch;
  private pause: (ms: number) => Promise<void>;
  constructor(private o: StakesScoutOptions) {
    this.now = o.now ?? (() => new Date());
    // Wrapped, never stored bare: workerd refuses `fetch` called as a method of another object ("Illegal invocation"), and a
    // scout that kept it as `this.fetchImpl` failed every request on the deployment while passing every test under Node.
    this.fetchImpl = o.fetchImpl ?? ((input, init) => fetch(input, init));
    this.pause = o.pause ?? ((ms) => new Promise((r) => setTimeout(r, ms)));
  }

  /**
   * Observe up to `limit` sources due for it (never observed first, then the stalest), then any field those sources sit in
   * whose totals are missing or a month old: the map's denominator (map/0.1).
   */
  async run(limit = 5): Promise<{ observed: number; unresolved: number; errors: number; fields: number; candidates: number }> {
    const r = await this.o.v2.record();
    const out = { observed: 0, unresolved: 0, errors: 0, fields: 0, candidates: 0 };
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
        ...(o.venueCitedness !== null ? { venueCitedness: round3(o.venueCitedness) } : {}), ...(o.year !== null ? { year: o.year } : {}), ...(o.field ? { field: o.field } : {}), ...(o.fieldId ? { fieldId: o.fieldId } : {}),
      });
      out.observed++;
    }
    // The fields: each OpenAlex field any observed source sits in, totals a month old or missing. One request each.
    const after = await this.o.v2.record();
    const fieldIds = new Map<string, string>(); // fieldId → field name
    for (const obs of after.observations.values()) if (obs.fieldId && obs.field && obs.provider === "openalex") fieldIds.set(obs.fieldId, obs.field);
    for (const [fieldId, field] of [...fieldIds.entries()].sort()) {
      const last = after.fieldObservations.get(field)?.observedAt ?? null;
      if (last !== null && Date.parse(last) >= cutoff) continue;
      if (!first) await this.pause(PAUSE_MS);
      first = false;
      const got = await this.observeField(fieldId);
      if (!got) { out.errors++; continue; }
      await this.o.log.append("field.observed", { field: got.field || field, fieldId, works: got.works, citedBy: got.citedBy });
      out.fields++;
    }
    // direction/0.1: the registration queue. For each field, its most-cited works, a month old or missing, one request each.
    if (this.o.candidates) {
      const set = (await this.o.candidates.get()) ?? { fields: {} };
      let changed = false;
      for (const [fieldId, field] of [...fieldIds.entries()].sort()) {
        const last = set.fields[fieldId]?.observedAt ?? null;
        if (last !== null && Date.parse(last) >= cutoff) continue;
        if (!first) await this.pause(PAUSE_MS);
        first = false;
        const works = await this.observeCandidates(fieldId, field);
        if (!works) { out.errors++; continue; }
        set.fields[fieldId] = { field, observedAt: this.now().toISOString(), works };
        changed = true;
        out.candidates += works.length;
      }
      if (changed) await this.o.candidates.put(set);
    }
    return out;
  }

  /** A field's most-cited works in OpenAlex, as registration candidates: those with a DOI or an arXiv id, since a claim needs a source. Null on any failure. */
  async observeCandidates(fieldId: string, field: string): Promise<Candidate[] | null> {
    try {
      const mailto = encodeURIComponent(this.o.contact ?? "replies@ecdysis.me");
      const url = `https://api.openalex.org/works?filter=primary_topic.field.id:${encodeURIComponent(fieldId)},type:article&sort=cited_by_count:desc&per-page=${CANDIDATES_PER_FIELD}&select=id,doi,title,cited_by_count,publication_year,ids&mailto=${mailto}`;
      const res = await this.fetchImpl(url, { headers: this.openAlexHeaders() });
      if (!res.ok) return null;
      const body = (await res.json().catch(() => null)) as { results?: Array<{ id?: string; doi?: string | null; title?: string | null; cited_by_count?: number; publication_year?: number | null; ids?: Record<string, string> }> } | null;
      if (!body || !Array.isArray(body.results)) return null;
      const at = this.now().toISOString();
      const out: Candidate[] = [];
      for (const w of body.results) {
        const source = candidateSource(w.doi ?? null, w.ids ?? {});
        if (!source || typeof w.id !== "string" || typeof w.cited_by_count !== "number") continue;
        out.push({ work: w.id, source, title: (typeof w.title === "string" ? w.title : "").trim().slice(0, 300), citedBy: Math.max(0, Math.floor(w.cited_by_count)), year: typeof w.publication_year === "number" ? w.publication_year : null, field, observedAt: at });
      }
      return out;
    } catch {
      return null;
    }
  }

  /** A field's totals in OpenAlex: works and citations to them. Null on any failure (left for the next run). */
  async observeField(fieldId: string): Promise<{ field: string; works: number; citedBy: number } | null> {
    try {
      const mailto = encodeURIComponent(this.o.contact ?? "replies@ecdysis.me");
      const res = await this.fetchImpl(`https://api.openalex.org/fields/${encodeURIComponent(fieldId)}?mailto=${mailto}`, { headers: this.openAlexHeaders() });
      if (!res.ok) return null;
      const f = (await res.json().catch(() => null)) as { display_name?: string; works_count?: number; cited_by_count?: number } | null;
      if (!f || typeof f.works_count !== "number" || typeof f.cited_by_count !== "number") return null;
      return { field: typeof f.display_name === "string" ? f.display_name.trim() : "", works: Math.max(0, Math.floor(f.works_count)), citedBy: Math.max(0, Math.floor(f.cited_by_count)) };
    } catch {
      return null;
    }
  }

  /**
   * One source: OpenAlex, then Semantic Scholar, by whatever id each can look the work up by (sources/0.1). A scheme
   * neither indexes by (openreview:, pmlr:, jmlr:, neurips:, isbn:, cite:) is left unresolved, and so has no reach yet.
   * Never throws.
   */
  async observe(source: string): Promise<{ status: "observed"; observed: Observed } | { status: "unresolved"; detail: string } | { status: "error"; detail: string }> {
    const p = parseSource(source);
    if (!p.ok) return { status: "unresolved", detail: "not a source in sources/0.1's spelling" };
    const { scheme, id } = p;
    const oaKey = scheme === "arxiv" ? `doi:10.48550/arXiv.${id}` : scheme === "doi" ? `doi:${id}` : scheme === "pmid" || scheme === "pmcid" ? `${scheme}:${id}` : scheme === "openalex" ? id : null;
    const s2Key = scheme === "arxiv" ? `arXiv:${id}` : scheme === "doi" ? `DOI:${id}` : scheme === "pmid" ? `PMID:${id}` : scheme === "pmcid" ? `PMCID:${id}` : scheme === "acl" ? `ACL:${id}` : null;
    if (!oaKey && !s2Key) return { status: "unresolved", detail: `neither OpenAlex nor Semantic Scholar looks works up by ${scheme}: ids` };
    try {
      const oa = oaKey ? await this.openAlex(oaKey, scheme === "doi") : { status: "unresolved" as const, detail: `OpenAlex has no lookup by ${scheme}: ids` };
      if (oa.status === "observed" || oa.status === "error") return oa;
      const s2 = s2Key ? await this.semanticScholar(s2Key) : { status: "unresolved" as const, detail: `Semantic Scholar has no lookup by ${scheme}: ids` };
      if (s2.status === "observed" || s2.status === "error") return s2;
      return { status: "unresolved", detail: `${oa.detail}; ${s2.detail}` };
    } catch (e) {
      return { status: "error", detail: String((e as Error)?.message ?? e).slice(0, 200) };
    }
  }

  /** Headers for OpenAlex: the user agent it asks for, and the account's key when one is configured. */
  private openAlexHeaders(): Record<string, string> {
    const key = this.o.apiKey?.trim();
    return { "user-agent": this.ua(), accept: "application/json", ...(key ? { authorization: `Bearer ${key}` } : {}) };
  }

  private ua(): string {
    return `ecdysis-stakes-scout/0.1 (https://ecdysis.me; mailto:${this.o.contact ?? "replies@ecdysis.me"})`;
  }

  /** One work in OpenAlex by "doi:…", "pmid:…", "pmcid:…" or its W id. */
  private async openAlex(key: string, withVenue: boolean): Promise<{ status: "observed"; observed: Observed } | { status: "unresolved"; detail: string } | { status: "error"; detail: string }> {
    const mailto = encodeURIComponent(this.o.contact ?? "replies@ecdysis.me");
    const c = key.indexOf(":");
    const path = c > 0 ? `${key.slice(0, c)}:${encodeURIComponent(key.slice(c + 1))}` : encodeURIComponent(key);
    const res = await this.fetchImpl(`https://api.openalex.org/works/${path}?mailto=${mailto}`, { headers: this.openAlexHeaders() });
    if (res.status === 404) return { status: "unresolved", detail: "OpenAlex knows no such work" };
    if (!res.ok) return { status: "error", detail: `OpenAlex ${res.status}` };
    const w = (await res.json().catch(() => null)) as OpenAlexWork | null;
    if (!w || typeof w !== "object") return { status: "error", detail: "OpenAlex answered without a work" };
    const citedBy = typeof w.cited_by_count === "number" && Number.isFinite(w.cited_by_count) ? Math.max(0, Math.floor(w.cited_by_count)) : 0;
    const year = typeof w.publication_year === "number" && Number.isFinite(w.publication_year) ? w.publication_year : null;
    const field = w.primary_topic?.field?.display_name?.trim() || null;
    const fieldUrl = w.primary_topic?.field?.id;
    const fieldId = typeof fieldUrl === "string" ? (fieldUrl.match(/fields\/(\d+)$/)?.[1] ?? null) : null;
    let venueCitedness: number | null = null;
    const venue = w.primary_location?.source?.id;
    if (withVenue && typeof venue === "string" && /openalex\.org\/S\d+$/i.test(venue)) {
      const sid = venue.slice(venue.lastIndexOf("/") + 1);
      const sres = await this.fetchImpl(`https://api.openalex.org/sources/${encodeURIComponent(sid)}?mailto=${mailto}`, { headers: this.openAlexHeaders() });
      if (sres.ok) {
        const src = (await sres.json().catch(() => null)) as { summary_stats?: Record<string, unknown> } | null;
        const v = src?.summary_stats?.["2yr_mean_citedness"];
        if (typeof v === "number" && Number.isFinite(v) && v >= 0) venueCitedness = v;
      }
    }
    const work = typeof w.id === "string" ? w.id.replace(/^https?:\/\/openalex\.org\//i, "") : null;
    return { status: "observed", observed: { provider: "openalex", work, citedBy, venueCitedness, year, field, fieldId } };
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
    return { status: "observed", observed: { provider: "semanticscholar", work: typeof p.paperId === "string" ? p.paperId : null, citedBy, venueCitedness: null, year, field, fieldId: null } };
  }
}

interface OpenAlexWork {
  id?: string;
  cited_by_count?: number;
  publication_year?: number;
  primary_topic?: { display_name?: string; field?: { id?: string; display_name?: string } } | null;
  primary_location?: { source?: { id?: string; display_name?: string } | null } | null;
}
interface S2Paper {
  paperId?: string;
  citationCount?: number;
  year?: number;
  s2FieldsOfStudy?: Array<{ category?: string; source?: string }>;
}

const round3 = (x: number) => Math.round(x * 1000) / 1000;

/**
 * The source a registration would use for a work OpenAlex lists, by sources/0.1's precedence: its arXiv id when it has one
 * (the quote scout reads arXiv abstracts), else its DOI, its PubMed or PubMed Central id, and else its OpenAlex id, so a
 * work without a DOI is a candidate too; null for a work with none of these.
 */
export function candidateSource(doi: string | null, ids: Record<string, string>): string | null {
  const arxiv = typeof ids["arxiv"] === "string" ? ids["arxiv"].replace(/^https?:\/\/arxiv\.org\/abs\//i, "").replace(/v\d+$/, "").trim() : "";
  if (arxiv) {
    const a = nameSource(`arxiv:${arxiv}`);
    if (a.ok) return a.source;
  }
  const d = (doi ?? "").replace(/^https?:\/\/(dx\.)?doi\.org\//i, "").trim();
  if (d) {
    const x = nameSource(`doi:${d}`);
    if (x.ok) return x.source;
  }
  for (const k of ["pmid", "pmcid", "openalex"] as const) {
    const v = typeof ids[k] === "string" ? ids[k].trim() : "";
    if (!v) continue;
    const x = nameSource(/^https?:\/\//i.test(v) ? v : `${k}:${v}`);
    if (x.ok) return x.source;
  }
  return null;
}
