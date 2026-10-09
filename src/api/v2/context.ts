/**
 * The context writer (context/0.1): on the cron, it gives each claim from human literature the context a reader needs.
 * The design and the rules are in core/v2/context.ts; this is the part that reads and writes.
 *
 *   The paper    For each registered source, OpenAlex's record of the work: title, authors, venue, year, type, keywords
 *                and its topic with the subfield, field and domain above it. One request a source, read again after
 *                RECORD_REFRESH_MS. Read whether or not a summary can be written, so every claim page names its paper.
 *   The summary  For each claim whose quote the quote scout found in its source (or could not check, the source having no
 *                open abstract), a language model writes what the claim means, what the paper found and its technical
 *                terms, from the quote, the paper's record and the abstract its own index publishes (readSource, the same
 *                reader the quote scout uses). Nothing an agent wrote but the quote goes in. The answer is checked against
 *                the limits (explanationProblems) and by screening before anything is kept.
 *
 * Highest stakes first, so the claims most worth reading about are explained first, and a few a run: the back catalogue is
 * worked through within a day of the key being installed, and new claims within the hour. A claim is written again only
 * when the version of the instructions or the model changes; a refused summary is not retried until one of them does.
 *
 * Off the log, as the quote scout's results are: the paper's record and the summary are context, never evidence, and feed
 * no number. Safeguards, so nothing depends on anyone remembering: without ANTHROPIC_API_KEY nothing is written (the
 * papers are still read); CONTEXT_PAUSED stops it; CONTEXT_DAILY_CAP bounds the model calls in a UTC day, whatever any
 * run asks for; and the key is sent to the model's provider alone, in a header, and kept out of every row and message.
 */

import type { V2Service } from "./service.js";
import { readSource, type QuoteCheckStore, type QuoteStatus } from "./quotes.js";
import { isHeld } from "../../core/v2/flow.js";
import { parseSource } from "../../core/v2/sources.js";
import { hashJson, type Json } from "../../core/canonical.js";
import { runScreening, type Screener } from "../../core/hazard.js";
import {
  CONTEXT_VERSION, EXPLAINER_SYSTEM, EXPLANATION_TOOL, PAPER_LIMITS, explainerMessage, explanationProblems, topicWords,
  type ExplainerMaterial, type Explanation, type PaperRecord,
} from "../../core/v2/context.js";

/** The model the writer uses unless CONTEXT_MODEL names another (Anthropic's id). */
export const DEFAULT_CONTEXT_MODEL = "claude-sonnet-5-5";
/** Model calls in one UTC day unless CONTEXT_DAILY_CAP says otherwise: enough for the back catalogue and a busy day. */
export const DEFAULT_CONTEXT_DAILY_CAP = 1000;
/** A paper's record is read again after this long (titles and topics barely move; citations come from the stakes scout's log). */
export const RECORD_REFRESH_MS = 180 * 24 * 3600 * 1000;
const RETRY_MS = 6 * 3600 * 1000;
const MAX_ATTEMPTS = 4;
/** The longest abstract given to the model; longer ones are cut at a sentence end (only the model sees it). */
const ABSTRACT_MAX = 6000;
/** Only these quote checks let a summary be written: found in the source, or not checkable against an abstract at all. */
const EXPLAINABLE: ReadonlySet<QuoteStatus> = new Set<QuoteStatus>(["verified", "not-in-abstract", "no-abstract"]);

export interface SourceRecordRow {
  source: string;
  status: "read" | "unresolved" | "error";
  record: PaperRecord | null;
  readAt: string;
  attempts: number;
  detail: string | null;
}

export interface ClaimContextRow {
  claim: string;
  status: "written" | "refused" | "error";
  version: string;
  model: string | null;
  inputsHash: string | null;
  explanation: Explanation | null;
  writtenAt: string;
  attempts: number;
  detail: string | null;
}

export interface ContextStore {
  getSource(source: string): Promise<SourceRecordRow | null>;
  putSource(row: SourceRecordRow): Promise<void>;
  getClaim(claim: string): Promise<ClaimContextRow | null>;
  putClaim(row: ClaimContextRow): Promise<void>;
  /** Every source's state in one read, so a run never asks once per source. */
  sourceIndex(): Promise<Map<string, Pick<SourceRecordRow, "status" | "readAt" | "attempts">>>;
  /** Every claim's state in one read. */
  claimIndex(): Promise<Map<string, Pick<ClaimContextRow, "status" | "version" | "model" | "writtenAt" | "attempts">>>;
}

export class MemoryContextStore implements ContextStore {
  sources = new Map<string, SourceRecordRow>();
  claims = new Map<string, ClaimContextRow>();
  async getSource(source: string) { const r = this.sources.get(source); return r ? structuredClone(r) : null; }
  async putSource(row: SourceRecordRow) { this.sources.set(row.source, structuredClone(row)); }
  async getClaim(claim: string) { const r = this.claims.get(claim); return r ? structuredClone(r) : null; }
  async putClaim(row: ClaimContextRow) { this.claims.set(row.claim, structuredClone(row)); }
  async sourceIndex() { return new Map([...this.sources.values()].map((r) => [r.source, { status: r.status, readAt: r.readAt, attempts: r.attempts }] as const)); }
  async claimIndex() { return new Map([...this.claims.values()].map((r) => [r.claim, { status: r.status, version: r.version, model: r.model, writtenAt: r.writtenAt, attempts: r.attempts }] as const)); }
}

/** How many model calls a UTC day has had: kept in ops state on the deployment. */
export interface DailyLedger {
  get(): Promise<{ day: string; count: number } | null>;
  put(v: { day: string; count: number }): Promise<void>;
}

export class MemoryLedger implements DailyLedger {
  v: { day: string; count: number } | null = null;
  async get() { return this.v ? { ...this.v } : null; }
  async put(v: { day: string; count: number }) { this.v = { ...v }; }
}

export interface ContextWriterOptions {
  store: ContextStore;
  v2: V2Service;
  /** The quote scout's results: a summary is written only for a quote it found in its source, or could not check. */
  quotes: QuoteCheckStore;
  fetchImpl?: typeof fetch;
  now?: () => Date;
  /** A pause between requests to the indexes. Tests pass a no-op. */
  pause?: (ms: number) => Promise<void>;
  contact?: string;
  openAlexKey?: string | null;
  /** The model provider's key (ANTHROPIC_API_KEY, a secret the deploy installs). Absent: nothing is written. */
  anthropicKey?: string | null;
  model?: string | null;
  /** CONTEXT_PAUSED: nothing is written while it is on (papers are still read). */
  paused?: boolean;
  /** CONTEXT_DAILY_CAP: model calls allowed in a UTC day. */
  dailyCap?: number | null;
  ledger?: DailyLedger;
  /** The record's own screening (Workers AI's classifier and the deployment's rules): a summary that does not pass is not kept. */
  screeners?: Screener[];
}

export interface ContextRunResult {
  papersRead: number;
  papersUnresolved: number;
  written: number;
  refused: number;
  errors: number;
  /** The daily cap stopped the run. */
  capped: boolean;
  /** Why nothing was written, when nothing could be: "no key", "paused", or the provider refusing the key. */
  off: string | null;
}

export class ContextWriter {
  private now: () => Date;
  private fetchImpl: typeof fetch;
  private pause: (ms: number) => Promise<void>;
  readonly model: string;
  constructor(private o: ContextWriterOptions) {
    this.now = o.now ?? (() => new Date());
    // Wrapped, never stored bare: workerd refuses `fetch` called as a method of another object (see the scouts).
    const f = o.fetchImpl;
    this.fetchImpl = f ? (input, init) => f(input, init) : (input, init) => fetch(input, init);
    this.pause = o.pause ?? ((ms) => new Promise((r) => setTimeout(r, ms)));
    this.model = (o.model ?? "").trim() || DEFAULT_CONTEXT_MODEL;
  }

  /** Why the writer writes nothing, or null when it can write. */
  offReason(): string | null {
    if (!this.o.anthropicKey?.trim()) return "no key";
    if (this.o.paused) return "paused";
    return null;
  }

  private ua(): string {
    return `ecdysis-context/0.1 (https://ecdysis.me; mailto:${this.o.contact ?? "replies@ecdysis.me"})`;
  }

  /** Never let the key into anything kept or shown, whatever an error message says. */
  private redact(s: string): string {
    const k = this.o.anthropicKey?.trim();
    return (k && k.length >= 8 ? s.split(k).join("[key]") : s).slice(0, 300);
  }

  /** One run: up to `papers` papers' records read, then up to `writes` summaries written, highest stakes first. */
  async run(limits: { papers?: number; writes?: number } = {}): Promise<ContextRunResult> {
    const out: ContextRunResult = { papersRead: 0, papersUnresolved: 0, written: 0, refused: 0, errors: 0, capped: false, off: null };
    const r = await this.o.v2.record();
    const s = await this.o.v2.scores();
    const now = this.now();
    const t = now.getTime();
    const claims = [...r.external.entries()]
      .filter(([id]) => !isHeld(r, id))
      .map(([id, x]) => ({ id, x, stakes: s.claims.get(id)?.stakes ?? 0 }))
      .sort((a, b) => b.stakes - a.stakes || (a.id < b.id ? -1 : 1));
    // The papers first: each source due once, in the order of its highest-stakes claim.
    const sources = await this.o.store.sourceIndex();
    let first = true;
    for (const c of claims) {
      if (out.papersRead + out.papersUnresolved >= (limits.papers ?? 12)) break;
      const key = c.x.source.toLowerCase();
      const row = sources.get(key);
      const due = !row || (row.status === "error" ? row.attempts < MAX_ATTEMPTS && Date.parse(row.readAt) < t - RETRY_MS : Date.parse(row.readAt) < t - RECORD_REFRESH_MS);
      if (!due) continue;
      if (!first) await this.pause(1000);
      first = false;
      const got = await this.readPaper(c.x.source).catch((e) => ({ status: "error" as const, record: null, detail: String((e as Error)?.message ?? e) }));
      const next: SourceRecordRow = { source: key, status: got.status, record: got.record, readAt: now.toISOString(), attempts: got.status === "error" ? (row?.status === "error" ? row.attempts + 1 : 1) : 1, detail: got.detail ? got.detail.slice(0, 300) : null };
      await this.o.store.putSource(next);
      sources.set(key, { status: next.status, readAt: next.readAt, attempts: next.attempts });
      if (got.status === "read") out.papersRead++;
      else if (got.status === "unresolved") out.papersUnresolved++;
      else out.errors++;
    }
    out.off = this.offReason();
    if (out.off) return out;
    // Then the summaries.
    const done = await this.o.store.claimIndex();
    const checks = new Map((await this.o.quotes.list(100_000)).map((q) => [q.claim, q.status] as const));
    const cap = Math.max(0, Math.floor(this.o.dailyCap ?? DEFAULT_CONTEXT_DAILY_CAP));
    const ledger = this.o.ledger ?? new MemoryLedger();
    const day = now.toISOString().slice(0, 10);
    const today = await ledger.get();
    let used = today && today.day === day ? today.count : 0;
    let writes = 0;
    for (const c of claims) {
      if (writes >= (limits.writes ?? 12)) break;
      const row = done.get(c.id);
      const due = !row
        || row.version !== CONTEXT_VERSION
        || (row.status === "written" && row.model !== this.model)
        || (row.status === "error" && row.attempts < MAX_ATTEMPTS && Date.parse(row.writtenAt) < t - RETRY_MS);
      if (!due) continue;
      const q = checks.get(c.id);
      if (!q || !EXPLAINABLE.has(q)) continue;
      if (used >= cap) { out.capped = true; break; }
      if (!first) await this.pause(1000);
      first = false;
      writes++;
      used++;
      await ledger.put({ day, count: used });
      const paper = (await this.o.store.getSource(c.x.source.toLowerCase()))?.record ?? null;
      const result = await this.writeOne(c.id, c.x.source, c.x.quote, c.x.kind, paper, row ?? null);
      if (result === "stop") { out.off = "the model provider refused the key"; out.errors++; break; }
      out[result]++;
    }
    return out;
  }

  /** One claim's summary: read the abstract, ask the model, check what it says, screen it, keep it. */
  private async writeOne(claim: string, source: string, quote: string, kind: "empirical" | "conceptual", paper: PaperRecord | null, prev: Pick<ClaimContextRow, "status" | "attempts" | "version"> | null): Promise<"written" | "refused" | "errors" | "stop"> {
    const at = this.now().toISOString();
    const attempts = prev && prev.status === "error" && prev.version === CONTEXT_VERSION ? prev.attempts + 1 : 1;
    const keep = async (row: Omit<ClaimContextRow, "claim" | "version" | "model" | "writtenAt" | "attempts">) => {
      await this.o.store.putClaim({ claim, version: CONTEXT_VERSION, model: this.model, writtenAt: at, attempts, ...row, detail: row.detail ? this.redact(row.detail) : null });
    };
    let text: Awaited<ReturnType<typeof readSource>>;
    try {
      text = await readSource(source, { fetchImpl: this.fetchImpl, userAgent: this.ua(), openAlexKey: this.o.openAlexKey ?? null });
    } catch (e) {
      await keep({ status: "error", inputsHash: null, explanation: null, detail: `the source's index could not be read: ${String((e as Error)?.message ?? e)}` });
      return "errors";
    }
    if (!text.ok && text.status === "error") {
      await keep({ status: "error", inputsHash: null, explanation: null, detail: `the source's index could not be read: ${text.detail}` });
      return "errors";
    }
    const abstract = text.ok && text.abstract ? cutAbstract(text.abstract) : null;
    const material: ExplainerMaterial = {
      quote, kind,
      paper: {
        title: paper?.title ?? (text.ok ? text.title : null) ?? null,
        authors: (paper?.authors ?? []).slice(0, 6),
        year: paper?.year ?? null, venue: paper?.venue ?? null, keywords: paper?.keywords ?? [], topic: topicWords(paper?.topic ?? null),
      },
      abstract,
    };
    const inputsHash = await hashJson({ version: CONTEXT_VERSION, model: this.model, system: EXPLAINER_SYSTEM, tool: EXPLANATION_TOOL as unknown as Json, material: material as unknown as Json });
    const answer = await this.ask(material);
    if (!answer.ok) {
      await keep({ status: "error", inputsHash, explanation: null, detail: answer.detail });
      return answer.stop ? "stop" : "errors";
    }
    const checked = explanationProblems(answer.input);
    if (!checked.ok) {
      await keep({ status: "refused", inputsHash, explanation: null, detail: `outside the limits: ${checked.problems.join("; ")}` });
      return "refused";
    }
    const v = checked.value;
    // A summary with no abstract to draw on has no findings to report: any it gives came from somewhere other than the paper.
    if (!abstract && v.findings.length) {
      await keep({ status: "refused", inputsHash, explanation: null, detail: "findings given without an abstract to take them from" });
      return "refused";
    }
    const decision = await runScreening({ texts: [v.meaning, ...v.findings, ...v.terms.flatMap((x) => [x.term, x.means])] }, { agentHandle: "Ecdysis", operatorId: "archive", acceptedCount: 1_000_000 }, this.o.screeners ?? [], { probationSubmissions: 0, screenerTimeoutMs: 8000 });
    if (decision.verdict !== "allow") {
      const outage = decision.failedClosed && decision.findings.every((f) => f.category === "screener-unavailable");
      await keep({ status: outage ? "error" : "refused", inputsHash, explanation: null, detail: outage ? "screening could not answer" : `screening: ${decision.findings.map((f) => f.category).join(", ")}` });
      return outage ? "errors" : "refused";
    }
    const explanation: Explanation = { ...v, basis: abstract ? "abstract" : "title", abstractFrom: abstract && text.ok ? text.kind : null, model: this.model, writtenAt: at, version: CONTEXT_VERSION };
    await keep({ status: "written", inputsHash, explanation, detail: null });
    return "written";
  }

  /** The model, through Anthropic's Messages API, made to answer with the explain_claim tool. */
  private async ask(material: ExplainerMaterial): Promise<{ ok: true; input: unknown } | { ok: false; detail: string; stop?: boolean }> {
    const key = this.o.anthropicKey!.trim();
    let res: Response;
    try {
      res = await this.fetchImpl("https://api.anthropic.com/v1/messages", {
        method: "POST",
        headers: { "x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json" },
        body: JSON.stringify({
          model: this.model, max_tokens: 1500, system: EXPLAINER_SYSTEM,
          tools: [EXPLANATION_TOOL], tool_choice: { type: "tool", name: EXPLANATION_TOOL.name },
          messages: [{ role: "user", content: explainerMessage(material) }],
        }),
      });
    } catch (e) {
      return { ok: false, detail: `the model provider could not be reached: ${String((e as Error)?.message ?? e)}` };
    }
    if (res.status === 401 || res.status === 403) return { ok: false, detail: `the model provider refused the key (${res.status})`, stop: true };
    if (!res.ok) {
      const body = (await res.json().catch(() => null)) as { error?: { type?: unknown } } | null;
      const type = typeof body?.error?.type === "string" ? ` (${body.error.type.slice(0, 60)})` : "";
      return { ok: false, detail: `the model provider answered ${res.status}${type}` };
    }
    const body = (await res.json().catch(() => null)) as { content?: Array<{ type?: string; name?: string; input?: unknown }>; stop_reason?: string } | null;
    const block = body?.content?.find((b) => b?.type === "tool_use" && b?.name === EXPLANATION_TOOL.name);
    if (!block) return { ok: false, detail: `no explanation in the answer${body?.stop_reason ? ` (it stopped: ${String(body.stop_reason).slice(0, 40)})` : ""}` };
    return { ok: true, input: block.input };
  }

  /** OpenAlex's record of a source's work, by whatever id OpenAlex looks works up by. Never throws for an answer it can read. */
  async readPaper(source: string): Promise<{ status: "read" | "unresolved" | "error"; record: PaperRecord | null; detail: string | null }> {
    const p = parseSource(source);
    if (!p.ok) return { status: "unresolved", record: null, detail: "not a source in sources/0.1's spelling" };
    const key = p.scheme === "arxiv" ? `doi:10.48550/arXiv.${p.id}` : p.scheme === "doi" ? `doi:${p.id}` : p.scheme === "pmid" || p.scheme === "pmcid" ? `${p.scheme}:${p.id}` : p.scheme === "openalex" ? p.id : null;
    if (!key) return { status: "unresolved", record: null, detail: `OpenAlex looks works up by no ${p.scheme}: id` };
    const c = key.indexOf(":");
    const path = c > 0 ? `${key.slice(0, c)}:${encodeURIComponent(key.slice(c + 1))}` : encodeURIComponent(key);
    const mailto = encodeURIComponent(this.o.contact ?? "replies@ecdysis.me");
    const k = this.o.openAlexKey?.trim();
    const res = await this.fetchImpl(`https://api.openalex.org/works/${path}?select=id,display_name,title,publication_year,type,authorships,primary_location,keywords,primary_topic,cited_by_count&mailto=${mailto}`,
      { headers: { "user-agent": this.ua(), accept: "application/json", ...(k ? { authorization: `Bearer ${k}` } : {}) } });
    if (res.status === 404) return { status: "unresolved", record: null, detail: "OpenAlex knows no such work" };
    if (!res.ok) return { status: "error", record: null, detail: `OpenAlex ${res.status}` };
    const w = (await res.json().catch(() => null)) as OpenAlexWork | null;
    if (!w || typeof w !== "object") return { status: "error", record: null, detail: "OpenAlex answered without a work" };
    return { status: "read", record: paperRecordOf(w, this.now().toISOString()), detail: null };
  }
}

interface OpenAlexWork {
  id?: string;
  display_name?: string | null;
  title?: string | null;
  publication_year?: number | null;
  type?: string | null;
  cited_by_count?: number | null;
  authorships?: Array<{ author?: { display_name?: string | null } | null }> | null;
  primary_location?: { source?: { display_name?: string | null } | null } | null;
  keywords?: Array<{ display_name?: string | null; score?: number | null }> | null;
  primary_topic?: { display_name?: string | null; subfield?: { display_name?: string | null } | null; field?: { display_name?: string | null } | null; domain?: { display_name?: string | null } | null } | null;
}

/** One line of an index's text: tags gone, spaces collapsed, cut to a length, null when empty. */
function line(v: unknown, max: number = PAPER_LIMITS.text): string | null {
  if (typeof v !== "string") return null;
  const t = v.replace(/<(script|style)\b[^>]*>[\s\S]*?<\/\1\s*>/gi, " ").replace(/<[^>]*>/g, " ").replace(/\s+/g, " ").trim();
  return t ? (t.length > max ? `${t.slice(0, max - 1).trimEnd()}…` : t) : null;
}

/** OpenAlex's answer as the record keeps it: only what the page shows, each value checked and cut to size. */
export function paperRecordOf(w: OpenAlexWork, readAt: string): PaperRecord {
  const authors = (Array.isArray(w.authorships) ? w.authorships : []).map((a) => line(a?.author?.display_name, 120)).filter((x): x is string => !!x);
  const keywords = (Array.isArray(w.keywords) ? w.keywords : [])
    .filter((k) => typeof k?.display_name === "string")
    .sort((a, b) => (b.score ?? 0) - (a.score ?? 0))
    .map((k) => line(k.display_name, 80))
    .filter((x): x is string => !!x)
    .slice(0, PAPER_LIMITS.keywords);
  const t = w.primary_topic;
  const topic = t && line(t.display_name) ? { topic: line(t.display_name)!, subfield: line(t.subfield?.display_name), field: line(t.field?.display_name), domain: line(t.domain?.display_name) } : null;
  const venue = line(w.primary_location?.source?.display_name, 200);
  return {
    provider: "openalex",
    work: typeof w.id === "string" ? w.id.replace(/^https?:\/\/openalex\.org\//i, "") : null,
    title: line(w.title ?? w.display_name),
    authors: authors.slice(0, PAPER_LIMITS.authors), authorCount: authors.length,
    venue,
    year: typeof w.publication_year === "number" && Number.isFinite(w.publication_year) ? w.publication_year : null,
    type: line(w.type, 40),
    citedBy: typeof w.cited_by_count === "number" && Number.isFinite(w.cited_by_count) ? Math.max(0, Math.floor(w.cited_by_count)) : null,
    keywords, topic, readAt,
  };
}

/** An abstract cut at a sentence end before ABSTRACT_MAX characters (only the model sees it). */
function cutAbstract(a: string): string {
  const t = a.replace(/\s+/g, " ").trim();
  if (t.length <= ABSTRACT_MAX) return t;
  const cut = t.slice(0, ABSTRACT_MAX);
  const end = cut.lastIndexOf(". ");
  return end > ABSTRACT_MAX / 2 ? cut.slice(0, end + 1) : cut;
}
