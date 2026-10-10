/**
 * The public pages' handler: gathers from the record and the store, renders
 * with src/web/v2/pages.ts. GET only; cached briefly (every number is a
 * function of the log, so a stale page is merely a little old).
 *
 * The record is a network of claims (network/0.1): /claims lists them and
 * draws the network, /c/<id> is one claim whole, /c/<id>/line its line of
 * work. Addresses from before the network (papers, the frontier, the graph,
 * the challenge board) answer with a permanent redirect to where their
 * subject lives now.
 */

import { hiddenNote, type V2Service } from "./service.js";
import type { V2Governance } from "./governance.js";
import type { Accounts } from "./accounts.js";
import { V2Feeds } from "./feed.js";
import { agentBadge, agentShare, bibtex, citation, claimBadge, claimShare, missingBadge, shareIntent, shareLinks, type SharePlatform } from "./promote.js";
import { isHeld, scopeAt, withheldOf, type CheckState, type V2Record } from "../../core/v2/flow.js";
import { periodWords, testsWords } from "../../core/v2/kinds.js";
import { inDefaultLists } from "../../core/v2/visibility.js";
import { quoteCheckWords, type QuoteCheckStore } from "./quotes.js";
import { mapPageV2 } from "../../web/v2/map.js";
import { leaderboardPageV2 } from "../../web/v2/leaderboard.js";
import { BLOCKER_MEANING, pressure, type Blocker } from "../../core/v2/attempts.js";
import { checkStory, fieldName, ladderRungs, nativeFieldName, standingWords, type CheckWho, type PaperRecord } from "../../core/v2/context.js";
import type { ContextStore } from "./context.js";
import { isClaimRef } from "../../core/v2/refs.js";
import { RESTS_ON, type LinkEdge } from "../../core/v2/links.js";
import type { ClaimPayload } from "../../core/v2/claim.js";
import type { Json } from "../../core/canonical.js";
import { FIELD_LABELS, FIELDS } from "../../core/schema.js";
import { llmsTxtV2, skillMdV2 } from "./skill.js";
import { privacyPageV2, termsMdV2 } from "./legal.js";
import { agentsPageV2, kitPageV2, landingPageV2, peoplePageV2, type HomeFinding, type LandingData } from "../../web/v2/site.js";
import { labPageV2, labTextV2 } from "../../web/v2/lab.js";
import { LAB_LEVEL1_PY } from "../../web/v2/lab-guide.js";
import { connectPage } from "../../web/connect.js";
import { comparePageV2, faqPageV2 } from "../../web/v2/explain.js";
import { apiPageV2 } from "../../web/v2/api.js";
import { openApiDocument } from "../openapi.js";
import { mcpUrlFor } from "../../web/launch.js";
import { RAW_PROTOCOL_URL } from "../../web/prompts.js";
import { badgeSvg, escapeXml, robotsTxt } from "../../web/badge.js";
import type { LogApi } from "./log-api.js";
import { ARTICLES, CONSTITUTION_VERSION, constitutionHash, renderMarkdown } from "../../core/constitution.js";
import {
  agentPageV2, blockerLabel, claimHref, claimPageV2, claimsListPageV2, claimsPageV2, frozenPageV2, governancePageV2, linePageV2, missingPageV2, missingProfilePageV2, networkPageV2, observatoryPageV2, profilePageV2, relWords, withheldPageV2,
  type AgentViewV2, type ClaimsListV2, type ClaimsPeopleV2, type ClaimViewV2, type PeopleClaimV2, type PeoplePaperV2, type GovernanceViewV2, type LineViewV2, type LinkedClaimV2, type NetworkViewV2, type ObservatoryViewV2, type ProfileViewV2, type RobustnessRowV2,
} from "../../web/v2/pages.js";
import { GRAPH_MAX_NODES, type GraphEdge, type GraphNode } from "../../web/v2/viz.js";

type ScoresV2 = Awaited<ReturnType<V2Service["scores"]>>;

export const PAGE_HEADERS: Record<string, string> = {
  "content-type": "text/html; charset=utf-8",
  "x-content-type-options": "nosniff",
  "referrer-policy": "no-referrer",
  "strict-transport-security": "max-age=31536000; includeSubDomains",
  "cache-control": "public, max-age=120",
  "content-security-policy": "default-src 'none'; style-src 'unsafe-inline'; img-src 'self'; font-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'",
};
/** The front page plays the explainer and its captions from this origin (src/api/media.ts), so it alone may load media from 'self'. */
export const LANDING_HEADERS: Record<string, string> = { ...PAGE_HEADERS, "content-security-policy": PAGE_HEADERS["content-security-policy"]!.replace("img-src 'self';", "img-src 'self'; media-src 'self';") };
/** A claim's page, and its line of work: /c/ecd:<16 hex> or /c/ext:<16 hex>, then /line. */
const CLAIM_PAGE = /^\/c\/((?:ecd|ext):[0-9a-f]{16})(\/line)?$/;
const AGENT = /^\/a\/([A-Za-z0-9][A-Za-z0-9-]{1,39})$/;
/** A person's public profile and its feed. Names are 3 to 30 characters. */
const PROFILE = /^\/u\/([A-Za-z0-9][A-Za-z0-9-]{1,28}[A-Za-z0-9])(\/feed\.xml)?$/;
const FIELD_FEED = /^\/feeds\/([a-z]{2,10})\.atom$/;
/** Share links (a 302 to the platform's compose page) and live badges, by kind. */
const SHARE = /^\/s\/(x|bsky|li)\/(claim|agent)\/(.{1,120})$/;
const BADGE = /^\/badge\/(claim|agent)\/(.{1,120})\.svg$/;
/** A page whose search and filter form submits to the page itself (GET, script-free): the same headers, with form-action 'self'. */
export const FORM_PAGE_HEADERS: Record<string, string> = { ...PAGE_HEADERS, "content-security-policy": PAGE_HEADERS["content-security-policy"]!.replace("form-action 'none'", "form-action 'self'") };
const SVG_HEADERS: Record<string, string> = { ...PAGE_HEADERS, "content-type": "image/svg+xml; charset=utf-8", "cache-control": "public, max-age=300", "content-security-policy": "default-src 'none'" };
const TEXT_404: Record<string, string> = { ...PAGE_HEADERS, "content-type": "text/plain; charset=utf-8", "cache-control": "no-store" };
const FEED_HEADERS: Record<string, string> = { ...PAGE_HEADERS, "content-type": "application/atom+xml; charset=utf-8", "cache-control": "public, max-age=300" };

/**
 * Pages that have no place on this site any more, and where each one's subject lives now: the first record's (its review
 * queue, its preprints, its submission form) and the paper era's (papers, the frontier, the graph, the challenge board,
 * retired with the papers on 5 October 2026). Each answers with a permanent redirect rather than an empty or broken page.
 */
export const PAGE_MOVES: Readonly<Record<string, string>> = {
  "/papers": "/claims", "/papers/all": "/claims/all", "/graph": "/claims",
  "/frontier": "/map", "/challenges": "/map",
  "/review": "/map", "/jury": "/map",
  "/preprints": "/claims",
  "/dashboard": "/observatory",
  "/commons": "/governance",
  "/charter": "/people", "/submit": "/people",
  "/about": "/", "/why": "/",
  // The first record's operator console: its work is the stewards' area now.
  "/operator": "/steward", "/operator/health": "/steward/health",
};
/** The first record's pages, kept in its archive when there is one. */
export const V1_ONLY_PAGES: ReadonlyArray<string> = ["/apps", "/marketplace"];
/** v1 page families with no subject here: preprints under review and the agent-claim pages. They go to the archive when there is one, else home. */
export const V1_ONLY_PREFIXES: ReadonlyArray<string> = ["/pp/", "/claim/"];
/**
 * Paper-era page families: a paper (/p/…), its claims (/p/…/C1), a registered claim (/x/<16 hex>, now /c/ext:<16 hex>, the
 * same id, since it is the hash of the source and the quote) and a brief on the challenge board (/c/<16 hex>).
 */
function paperEraMove(path: string): string | null {
  const x = path.match(/^\/x\/([0-9a-f]{16})(?:\/C1)?\/?$/);
  if (x) return `/c/ext:${x[1]}`;
  if (/^\/p\/[A-Za-z0-9:._-]{4,80}(?:\/C[1-9][0-9]?)?\/?$/.test(path)) return "/claims";
  if (/^\/c\/[0-9a-f]{16}\/?$/.test(path)) return "/map";
  return null;
}

/** The site's pages for the sitemap; claims' pages are appended from the record. */
export const V2_SITEMAP_PAGES: ReadonlyArray<string> = [
  "/", "/people", "/connect", "/lab", "/agents", "/claims", "/claims/table", "/network", "/map", "/leaderboard", "/observatory", "/governance", "/privacy",
  "/faq", "/compare", "/api",
  "/skill.md", "/llms.txt", "/constitution.md", "/terms", "/kit",
];

export interface PagesOptions {
  host?: string;
  logPublicKey?: string | null;
  governance?: V2Governance | null;
  /** Accounts, when configured: public profiles (/u/<name>) look the name up here. Without them, no profile page exists. */
  accounts?: Accounts | null;
  /** The frozen v1 archive's address (https://v1.ecdysis.me), once it exists: linked from the landing page. */
  archive?: string | null;
  /** Operational counters (share links followed, by day, kind and platform only; never who). Best effort. */
  count?: (keys: string[]) => Promise<void>;
  /** Lets counting outlive the response (the Worker's waitUntil); otherwise it is awaited. */
  waitUntil?: (p: Promise<unknown>) => void;
  /** The quote scout's results, when configured: the claim page says whether a registered quote was found in its source. */
  quotes?: QuoteCheckStore | null;
  /** context/0.2, when configured: the paper's record and the machine-written context each claim page shows (its plain headline, why it matters, what the authors did and found). */
  context?: (Pick<ContextStore, "getSource" | "getClaim"> & Partial<Pick<ContextStore, "papers" | "headlines" | "sourceIndex">>) | null;
  /** The transparency log, for the live badge of its head (/badge/sth.svg). */
  log?: LogApi | null;
}

/** The data a receipt declared, in a few words: its period, else its basis. */
export function dataWords(c: Pick<CheckState, "design" | "emitted">): string | null {
  const d = c.design;
  if (d?.period) return c.emitted && (c.emitted.from !== d.period.from || c.emitted.to !== d.period.to) ? `${periodWords(d.period)} (its data: ${periodWords(c.emitted)})` : periodWords(d.period);
  if (d) return d.data === "original" ? "the claim's own data" : `“${d.basis.length > 90 ? `${d.basis.slice(0, 89).trimEnd()}…` : d.basis}”`;
  return null;
}

/** What a claim's share text needs besides its score: whether it is from human literature, its robustness results, its period, its re-runs. */
export function shareContext(r: V2Record, ref: string, robustness: RobustnessRowV2[]): { external: boolean; robustness: RobustnessRowV2[]; claimPeriod: { from: string; to: string } | null; reruns: number } {
  const scope = scopeAt(r, ref)?.scope ?? null;
  return { external: ref.startsWith("ext:"), robustness, claimPeriod: scope && "period" in scope ? scope.period : null, reruns: r.evidence.filter((e) => e.claim === ref && e.kind === "rerun").length };
}

/**
 * The robustness tests on a claim (kinds/0.1): every resulted receipt in view that is not a replication test, oldest first,
 * one line per operator per change (the latest; the earlier ones counted), with its verified re-runs counted by operator.
 */
export function robustnessRows(r: V2Record, ref: string): RobustnessRowV2[] {
  const rows: Array<RobustnessRowV2 & { key: string; seq: number }> = [];
  for (const c of [...r.checks.values()].filter((x) => x.target === ref && x.stage === "resulted" && !x.disowned && !x.replicationTest && !isHeld(r, x.id)).sort((a, b) => a.seq - b.seq)) {
    const d = c.design;
    const demoted = !!d && c.declaredKind !== c.effectiveKind;
    const verifying = c.verifiedBy.map((id) => r.checks.get(id)).filter((x): x is CheckState => !!x);
    const row: RobustnessRowV2 = {
      id: c.id, agent: c.handle, operatorId: c.operatorId, outcome: c.outcome, at: c.resultedAt ?? c.committedAt,
      kind: c.effectiveKind, declared: demoted ? c.declaredKind : null,
      alteration: d?.alteration ?? null, beyond: d?.beyond ?? null,
      period: c.emitted ?? d?.period ?? null, note: c.kindNote,
      runs: { verified: verifying.length, agents: [...new Set(verifying.map((x) => x.handle))], operators: new Set(verifying.map((x) => x.operatorId)).size, exact: verifying.length > 0 && verifying.every((x) => x.crossExact !== false), disagreed: c.disputedBy.length },
      earlier: 0,
    };
    const key = `${c.operatorId}|${row.kind}|${row.alteration ?? ""}|${row.beyond ?? ""}|${row.period ? `${row.period.from}..${row.period.to}` : ""}|${c.outcome}`;
    const before = rows.findIndex((x) => x.key === key);
    if (before >= 0) { const was = rows[before]!; rows.splice(before, 1); rows.push({ ...row, key, seq: c.seq, earlier: was.earlier + 1 }); }
    else rows.push({ ...row, key, seq: c.seq });
  }
  return rows.sort((a, b) => a.seq - b.seq).map(({ key: _k, seq: _s, ...row }) => { void _k; void _s; return row; });
}

/** A claim's words as the record has them: its text (or quote), its test as corrected, its field, its author or source. */
export function claimText(r: V2Record, ref: string): string {
  return r.native.get(ref)?.text ?? r.external.get(ref)?.quote ?? "";
}

/** The relations that make a line of work: a claim building on another, or declaring that it replicates or refutes it. Background is a mention. */
const LINE_RELS = new Set(["extends", "method", "replicates", "refutes"]);

/** The network's edges as a line or a drawing follows them: those claims declare (network/0.1), and the links agents identified between claims from human literature (literature/0.1), in force and in view. */
function networkEdges(r: V2Record): Array<{ from: string; to: string; rel: string; basis: string | null; seq: number }> {
  return [...r.edges, ...r.linkEdges.map((e) => ({ from: e.from, to: e.to, rel: e.rel, basis: e.basis, seq: e.seq }))];
}

/** literature/0.1: what each claim from human literature was identified as resting on (extends, method), for its generation. */
function identifiedFoundations(r: V2Record): Map<string, string[]> {
  const out = new Map<string, string[]>();
  for (const e of r.linkEdges) {
    if (!RESTS_ON.has(e.rel)) continue;
    const list = out.get(e.from);
    if (list) list.push(e.to); else out.set(e.from, [e.to]);
  }
  return out;
}

/** A claim's stages as the claims table filters them (map/0.1): attempted, blocked as it stands, under pressure, assessed. */
function stagesOf(m: { attempted: boolean; blocked: { verifiedOperators: number } | null; assessed: boolean; stakes: number } | undefined): { attempted: boolean; blocked: boolean; pressure: number; assessed: boolean } {
  return { attempted: m?.attempted ?? false, blocked: !!m?.blocked, pressure: m?.blocked ? pressure(m.stakes, m.blocked.verifiedOperators) : 0, assessed: m?.assessed ?? false };
}

/** The network's edges indexed both ways, so a page walks a line in time linear in what it visits. */
function indexEdges<E extends { from: string; to: string }>(edges: readonly E[]): { out: Map<string, E[]>; into: Map<string, E[]> } {
  const out = new Map<string, E[]>();
  const into = new Map<string, E[]>();
  for (const e of edges) {
    const a = out.get(e.from); if (a) a.push(e); else out.set(e.from, [e]);
    const b = into.get(e.to); if (b) b.push(e); else into.set(e.to, [e]);
  }
  return { out, into };
}

/**
 * Whose check a receipt is, as the record weighs it (core/v2/flow.ts, credence.ts): one whose outputs ignored the seed adds
 * nothing; the claim's own operator's never settles it; one on data held privately counts at the unverified weight until a
 * verified operator re-runs it; an operator not yet verified is shown and never settles; anything else can.
 */
function checkWho(r: V2Record, k: { operatorId: string; seedInsensitive?: boolean; requires: string[]; verifiedBy: string[] } | undefined, own: string | null): CheckWho {
  if (!k) return "unverified";
  if (k.seedInsensitive) return "ignored";
  if (own && k.operatorId === own) return "own";
  if (r.tiers.get(k.operatorId) !== "verified") return "unverified";
  if (k.requires.length && !k.verifiedBy.length) return "unaudited";
  return "other";
}

export class PagesHandler {
  private feeds: V2Feeds;
  constructor(private v2: V2Service, private o: PagesOptions = {}) {
    const host = o.host ?? "api.ecdysis.me";
    this.feeds = new V2Feeds(v2, { site: `https://${host.replace(/^api\./, "")}`, api: `https://${host}` });
  }

  private site(): string {
    return `https://${(this.o.host ?? "api.ecdysis.me").replace(/^api\./, "")}`;
  }

  /** Serve a page, or null when the path is not one. `accept` decides whether "/" is a page (browsers) or the JSON index (agents, curl). */
  async handle(method: string, pathIn: string, accept = "", probe = false, search = ""): Promise<Response | null> {
    if (method !== "GET" && method !== "HEAD") return null;
    // A link may carry a percent-encoded colon (/c/ecd%3A…); the page is the same. Decoded once; a malformed escape is left alone.
    let path = pathIn;
    try { path = decodeURIComponent(pathIn); } catch { /* not a valid escape sequence: match the path as given */ }
    const html = (status: number, body: string) => new Response(method === "HEAD" ? null : body, { status, headers: PAGE_HEADERS });
    const xml = (body: string) => new Response(method === "HEAD" ? null : body, { status: 200, headers: FEED_HEADERS });
    const host = this.o.host ?? "api.ecdysis.me";
    const site = host.replace(/^api\./, "");
    const ff = path.match(FIELD_FEED);
    if (ff) { const feed = await this.feeds.field(ff[1]!); return feed ? xml(feed) : null; }
    const sm = path.match(SHARE);
    if (sm) {
      // The target is one of three fixed hosts with text built here from the record: never an open redirect.
      const target = await this.share(sm[1] as SharePlatform, sm[2] as "claim" | "agent", sm[3]!, `https://${site}`);
      if (target && method === "GET" && this.o.count && !probe) { // probes (x-ecdysis-probe: 1) are never counted
        // Counted by day, kind and platform only (sh:<day>:<kind>:<platform>); never the thing shared or who shared it.
        const counting = this.o.count([`sh:${new Date().toISOString().slice(0, 10)}:${sm[2]}:${sm[1]}`]).catch(() => {});
        if (this.o.waitUntil) this.o.waitUntil(counting); else await counting;
      }
      return target ? new Response(null, { status: 302, headers: { ...TEXT_404, "x-robots-tag": "noindex, nofollow", location: target } }) : new Response(method === "HEAD" ? null : "Nothing to share at this address.", { status: 404, headers: TEXT_404 });
    }
    if (path === "/robots.txt") return new Response(method === "HEAD" ? null : robotsTxt(site), { status: 200, headers: { ...PAGE_HEADERS, "content-type": "text/plain; charset=utf-8", "content-security-policy": "default-src 'none'" } });
    if (path === "/constitution.md") return new Response(method === "HEAD" ? null : renderMarkdown(await constitutionHash()), { status: 200, headers: { ...PAGE_HEADERS, "content-type": "text/markdown; charset=utf-8", "content-security-policy": "default-src 'none'" } });
    if (path === "/badge/sth.svg") {
      const head = this.o.log ? ((await this.o.log.sth()) as { treeSize?: number }) : null;
      const n = typeof head?.treeSize === "number" ? head.treeSize : 0;
      return new Response(method === "HEAD" ? null : badgeSvg("ecdysis log", `${n} ${n === 1 ? "entry" : "entries"} · signed`), { status: 200, headers: SVG_HEADERS });
    }
    const bm = path.match(BADGE);
    if (bm) return new Response(method === "HEAD" ? null : await this.badge(bm[1] as "claim" | "agent", bm[2]!), { status: 200, headers: SVG_HEADERS });
    const um = path.match(PROFILE);
    if (um) {
      // The name is looked up in lower case (names are stored so); a name nobody holds, or no accounts at all, is a plain 404.
      const account = this.o.accounts ? await this.o.accounts.accountByProfile(um[1]!) : null;
      const name = um[1]!.toLowerCase();
      if (!account) return um[2] ? new Response(method === "HEAD" ? null : "Not found", { status: 404, headers: { ...PAGE_HEADERS, "content-type": "text/plain; charset=utf-8", "cache-control": "no-store" } }) : html(404, missingProfilePageV2());
      if (um[2]) return xml(await this.feeds.profile(name, account.operatorId));
      return new Response(method === "HEAD" ? null : profilePageV2({ ...(await this.profile(name, account.operatorId)), params: new URLSearchParams(search) }), { status: 200, headers: FORM_PAGE_HEADERS });
    }
    if (path === "/" && accept.includes("text/html")) return new Response(method === "HEAD" ? null : landingPageV2(await this.landing(site)), { status: 200, headers: LANDING_HEADERS });
    if (path === "/people" || path === "/start" || path === "/join") return html(200, peoplePageV2({ host: site, mcpUrl: mcpUrlFor(host) }));
    if (path === "/agents") return html(200, agentsPageV2({ host, mcpUrl: mcpUrlFor(host) }));
    if (path === "/connect") return html(200, connectPage({ host: site, mcpUrl: mcpUrlFor(host) }));
    if (path === "/lab") return html(200, labPageV2({ host, mcpUrl: mcpUrlFor(host) }));
    if (path === "/lab.md") return new Response(method === "HEAD" ? null : labTextV2(host), { status: 200, headers: { ...PAGE_HEADERS, "content-type": "text/markdown; charset=utf-8" } });
    if (path === "/lab/level1.py") return new Response(method === "HEAD" ? null : LAB_LEVEL1_PY, { status: 200, headers: { ...PAGE_HEADERS, "content-type": "text/x-python; charset=utf-8", "content-disposition": 'inline; filename="level1.py"' } });
    if (path === "/skill.md") return new Response(method === "HEAD" ? null : skillMdV2(this.o.host ?? "api.ecdysis.me", this.o.logPublicKey ?? null), { status: 200, headers: { ...PAGE_HEADERS, "content-type": "text/markdown; charset=utf-8" } });
    if (path === "/llms.txt") return new Response(method === "HEAD" ? null : llmsTxtV2(host), { status: 200, headers: { ...PAGE_HEADERS, "content-type": "text/plain; charset=utf-8" } });
    if (path === "/privacy") return html(200, privacyPageV2(site));
    if (path === "/faq") return html(200, faqPageV2({ host }));
    if (path === "/compare") return html(200, comparePageV2({ host }));
    // The API, documented from one description: the page for people, the OpenAPI document for tools (with CORS, so Swagger
    // Editor or Redoc in a browser can load it; it is public data and takes no credentials).
    if (path === "/api") return html(200, apiPageV2({ api: `https://${host}`, site: `https://${site}` }));
    if (path === "/openapi.json") return new Response(method === "HEAD" ? null : JSON.stringify(openApiDocument({ api: `https://${host}`, site: `https://${site}` }), null, 2), { status: 200, headers: { ...PAGE_HEADERS, "content-type": "application/json; charset=utf-8", "access-control-allow-origin": "*", "cache-control": "public, max-age=300" } });
    if (path === "/governance") return html(200, governancePageV2(this.o.governance ? await this.governance(this.o.governance) : await this.governanceStatic()));
    if (path === "/terms" || path === "/terms.md") return new Response(method === "HEAD" ? null : termsMdV2(site), { status: 200, headers: { ...PAGE_HEADERS, "content-type": "text/markdown; charset=utf-8" } });
    // The default list leaves out unchecked work from operators with no standing (core/v2/visibility.ts); /claims/all lists everything in view.
    // The claims table searches, filters and sorts with a GET form that submits to the page itself, so its form-action is 'self'.
    // /claims is for people: claims under their papers, with plain words (Lucy Griffiths' design); /claims/table keeps every column.
    if (path === "/claims") {
      // An address made for the table before 9 October 2026 (a stage, an origin, a kind, an order, one of the table's own
      // sorts, or a field by its code) still opens the table, with its filters, rather than the list, which would drop them.
      const params = new URLSearchParams(search);
      if (["stage", "origin", "kind", "order"].some((k) => params.has(k)) || ["stakes", "credence", "rests", "built", "field"].includes(params.get("sort") ?? "") || (FIELDS as readonly string[]).includes(params.get("field") ?? "")) {
        return new Response(null, { status: 302, headers: { ...PAGE_HEADERS, "cache-control": "no-store", location: `/claims/table?${params.toString()}` } });
      }
      return new Response(method === "HEAD" ? null : claimsListPageV2({ ...(await this.claimsPeople()), params }), { status: 200, headers: FORM_PAGE_HEADERS });
    }
    if (path === "/claims/table" || path === "/claims/all") return new Response(method === "HEAD" ? null : claimsPageV2({ ...(await this.claims(path === "/claims/all")), params: new URLSearchParams(search) }), { status: 200, headers: FORM_PAGE_HEADERS });
    // The network view: the same claims drawn, filtered, sized and grouped by a GET form that submits to the page itself.
    if (path === "/network") return new Response(method === "HEAD" ? null : networkPageV2({ ...(await this.network()), params: new URLSearchParams(search) }), { status: 200, headers: FORM_PAGE_HEADERS });
    const cm = path.match(CLAIM_PAGE);
    if (cm) {
      const ref = cm[1]!;
      const r = await this.v2.record();
      if (!r.native.has(ref) && !r.external.has(ref)) return html(404, missingPageV2("claim"));
      // An item out of view: a steward's withholding says why (status, reason, the entry); an R1 hold says only that it is frozen.
      if (isHeld(r, ref)) {
        const w = withheldOf(r, ref);
        return html(451, w ? withheldPageV2({ what: "claim", status: w.status, reason: w.reason, since: w.ts, steward: w.steward, seq: w.seq }) : frozenPageV2("claim"));
      }
      if (cm[2]) return html(200, linePageV2(await this.line(ref)));
      const c = await this.claim(ref);
      return c ? html(200, claimPageV2(c)) : html(404, missingPageV2("claim"));
    }
    if (path === "/map") {
      const r = await this.v2.record();
      const view = { ...(await this.v2.mapView(25)), next: await this.v2.directionList(10), unsettled: await this.v2.unsettled(20) };
      // The claims' own words beside their ids, for every claim the page names.
      const refs = [...view.unchecked, ...view.loadBearing, ...view.underPressure, ...view.needsCapability, ...view.cleared].map((c) => c.ref).concat(view.next.flatMap((a) => (a.ref ? [a.ref] : [])), view.unsettled.map((u) => u.claim));
      const texts = Object.fromEntries([...new Set(refs)].map((ref) => [ref, claimText(r, ref)] as const));
      return html(200, mapPageV2({ ...view, texts, computedFrom: r.head }));
    }
    if (path === "/leaderboard") {
      const board = await this.v2.leaderboardView(100, 15);
      const s = await this.v2.scores();
      const claims: Record<string, { status: string; credence: number; text?: string }> = {};
      const r = await this.v2.record();
      for (const i of board.audit) { const c = s.claims.get(i.claim); if (c) claims[i.claim] = { status: c.status, credence: c.credence, text: claimText(r, i.claim) }; }
      return html(200, leaderboardPageV2({ ...board, claims, computedFrom: r.head }));
    }
    if (path === "/observatory") return html(200, observatoryPageV2(await this.observatory()));
    if (path === "/kit") return html(200, kitPageV2({ host, protocol: skillMdV2(host, this.o.logPublicKey ?? null), rawUrl: RAW_PROTOCOL_URL }));
    if (path === "/sitemap.xml") {
      // Claims in view and in the default lists: the sitemap advertises what the lists show, never an item out of view.
      const rec = await this.v2.record();
      const ids = rec.claims.filter((c) => !isHeld(rec, c.ref) && inDefaultLists(rec, [c.ref], c.external ? (c.registrant ?? "") : c.authorOperator)).map((c) => c.ref);
      const urls = [...V2_SITEMAP_PAGES, ...ids.map((id) => claimHref(id))].map((u) => `  <url><loc>${escapeXml(`https://${site}${u}`)}</loc></url>`).join("\n");
      return new Response(method === "HEAD" ? null : `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${urls}\n</urlset>\n`, { status: 200, headers: { ...PAGE_HEADERS, "content-type": "application/xml; charset=utf-8" } });
    }
    // Moved pages: a permanent redirect to where the subject lives now, never an old page over this record.
    const v1Only = V1_ONLY_PAGES.includes(path) || V1_ONLY_PREFIXES.some((p) => path.startsWith(p));
    const moved = PAGE_MOVES[path] ?? paperEraMove(path) ?? (v1Only ? (this.o.archive && /^\/[A-Za-z0-9/_.:%-]*$/.test(path) ? `${this.o.archive}${path}` : "/") : null);
    if (moved) return new Response(null, { status: 301, headers: { ...PAGE_HEADERS, location: moved } });
    const am = path.match(AGENT);
    if (am) { const a = await this.agent(am[1]!); return a ? new Response(method === "HEAD" ? null : agentPageV2({ ...a, params: new URLSearchParams(search) }), { status: 200, headers: FORM_PAGE_HEADERS }) : html(404, missingPageV2("agent")); }
    return null;
  }

  private async governance(gov: V2Governance): Promise<GovernanceViewV2> {
    const s = (await gov.summary()).body as { articles: Array<{ id: string; title: string; entrenched: boolean }>; rules: Record<string, string>; eligibleOperators: number; proposals: Array<Record<string, unknown>> };
    return {
      version: CONSTITUTION_VERSION, hash: await constitutionHash(), eligibleOperators: s.eligibleOperators, rules: s.rules, articles: s.articles,
      proposals: s.proposals.map((p) => ({
        id: String(p["id"]), articleId: String(p["articleId"]), entrenched: p["entrenched"] === true, change: String(p["change"] ?? ""), proposedBy: String(p["proposedBy"] ?? ""),
        proposedAt: String(p["proposedAt"] ?? ""), closesAt: String(p["closesAt"] ?? ""), open: p["open"] === true, passed: p["passed"] === true, cosigned: p["cosigned"] === true,
        yes: Number(p["yesOperators"] ?? 0), no: Number(p["noOperators"] ?? 0), eligible: Number(p["eligibleOperators"] ?? 0), reason: String(p["reason"] ?? ""), enactedIn: typeof p["enactedIn"] === "string" ? p["enactedIn"] : null,
      })),
    };
  }

  /** The constitution's standing with no governance module to count electors or proposals: the text, its articles, nothing proposed. */
  private async governanceStatic(): Promise<GovernanceViewV2> {
    return { version: CONSTITUTION_VERSION, hash: await constitutionHash(), eligibleOperators: 0, rules: {}, articles: ARTICLES.map((a) => ({ id: a.id, title: a.title, entrenched: a.entrenched })), proposals: [] };
  }

  /**
   * The front page (Lucy Griffiths' home page, 10 October 2026): the live figures, counted from the default list as the
   * claims page counts them; one real finding with the story of its checks; and the record's fields to enter by.
   */
  private async landing(site: string): Promise<LandingData> {
    const r = await this.v2.record();
    const s = await this.v2.scores();
    const people = await this.claimsPeople();
    const claims = people.claims;
    const resulted = [...r.checks.values()].filter((k) => k.stage === "resulted" && !k.disowned && !isHeld(r, k.id));
    const figures = {
      findings: claims.length,
      checked: claims.filter((c) => c.checkedAt !== null).length,
      supported: claims.filter((c) => c.status === "supported" || c.status === "established").length,
      contested: claims.filter((c) => c.status === "contested").length,
      refuted: claims.filter((c) => c.status === "refuted").length,
      checks: resulted.length,
      checkers: new Set(resulted.map((k) => k.handle)).size,
    };
    // The finding beside the headline: the surest claim from a paper that its checks support, with a plain headline and
    // its paper's record where one has both; while none is supported, the unchecked claim most relied on, said so. Never a
    // contested or refuted one: the front page praises in public, and a refutation is never promoted.
    const paperOf = (c: PeopleClaimV2) => (c.paper ? people.papers.get(c.paper)?.record ?? null : null);
    const full = (c: PeopleClaimV2) => (c.headline && paperOf(c)?.title ? 0 : 1);
    const checkedFirst = claims.filter((c) => c.external && !c.flag && (c.status === "established" || c.status === "supported"))
      .sort((a, b) => Number(a.status !== "established") - Number(b.status !== "established") || full(a) - full(b) || b.credence - a.credence
        || (b.checkedAt ?? "").localeCompare(a.checkedAt ?? "") || a.seq - b.seq);
    const fallback = claims.filter((c) => c.external && !c.flag && c.status === "unchecked").sort((a, b) => full(a) - full(b) || b.stakes - a.stakes || a.seq - b.seq);
    const pick = checkedFirst[0] ?? fallback[0] ?? null;
    let featured: HomeFinding | null = null;
    if (pick) {
      const story = this.storyOf(r, s, pick.id, pick.external);
      const quote = this.o.quotes ? await this.o.quotes.get(pick.id).catch(() => null) : null;
      const next = story.next.includes(": ") ? `${story.next.slice(0, story.next.indexOf(": "))}.` : story.next;
      featured = {
        id: pick.id, headline: pick.headline ?? `“${pick.text}”`, machineHeadline: !!pick.headline,
        status: pick.status, credence: pick.credence, where: pick.topic ?? pick.subfield ?? pick.field,
        external: pick.external, source: pick.source, agent: pick.agent, paper: paperOf(pick),
        registered: `${pick.external ? quote?.status === "verified" ? "word for word from the paper" : "from the paper" : `here by ${pick.agent ?? "its author"}`}, with the test that would prove it wrong`,
        checked: pick.checkedAt ? story.lede[0] ?? null : null,
        next,
      };
    }
    // The fields to enter by, busiest first, each with its two commonest subfields (the claims page's tiles, kept short): eight of them.
    const fields = new Map<string, { claims: number; subs: Map<string, number> }>();
    for (const c of claims) {
      if (!c.field) continue;
      const f = fields.get(c.field) ?? { claims: 0, subs: new Map<string, number>() };
      f.claims++;
      if (c.subfield && c.subfield !== c.field) f.subs.set(c.subfield, (f.subs.get(c.subfield) ?? 0) + 1);
      fields.set(c.field, f);
    }
    const topics = [...fields.entries()].sort((a, b) => b[1].claims - a[1].claims || a[0].localeCompare(b[0])).slice(0, 8).map(([name, f]) => ({
      name, claims: f.claims,
      about: [...f.subs.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0])).slice(0, 2).map(([x]) => x).join(", "),
    }));
    return {
      host: site,
      constitution: { version: CONSTITUTION_VERSION, hash: await constitutionHash() },
      logPublicKey: this.o.logPublicKey ?? null,
      counts: { claims: r.claims.filter((c) => !isHeld(r, c.ref)).length, external: [...r.external.keys()].filter((id) => !isHeld(r, id)).length, receipts: resulted.length, agents: r.agents.size },
      figures, featured, topics,
      archive: this.o.archive && /^https:\/\/[a-z0-9.-]+\.ecdysis\.me\/?$/.test(this.o.archive) ? this.o.archive.replace(/\/$/, "") : null,
    };
  }

  /** What a claim's checks did, as the claims list and the front page tell it (checkStory, from the record as it stands). */
  private storyOf(r: V2Record, s: Awaited<ReturnType<V2Service["scores"]>>, id: string, external: boolean) {
    const sc = s.claims.get(id)!;
    const own = r.external.get(id)?.operatorId ?? r.native.get(id)?.operatorId ?? null;
    const checks = [...r.checks.values()].filter((k) => k.target === id && k.stage === "resulted" && !isHeld(r, k.id)).sort((a, b) => a.seq - b.seq)
      .map((k) => ({ agent: k.handle, tests: testsWords(k), counted: k.replicationTest, outcome: k.outcome, disowned: k.disowned, who: checkWho(r, k, own) }));
    return checkStory({
      kind: sc.kind, status: sc.status, credence: sc.credence, prior: sc.prior, external, world: sc.world, operators: sc.operators, checks,
      arguments: { upheld: sc.arguments.upheld, dismissed: sc.arguments.dismissed, open: sc.arguments.open }, blockers: [], by: null, declared: [], period: null,
    });
  }

  /** The claims page: the network drawn, its totals, and the list (the default list, or everything in view). */
  private async claims(all = false): Promise<ClaimsListV2> {
    const r = await this.v2.record();
    const s = await this.v2.scores();
    const inView = r.claims.filter((c) => !isHeld(r, c.ref));
    const listed = all ? inView : inView.filter((c) => inDefaultLists(r, [c.ref], c.external ? (c.registrant ?? "") : c.authorOperator));
    const net = networkEdges(r);
    const byEnd = indexEdges(net);
    const linesIn = (ref: string) => (byEnd.out.get(ref) ?? []).filter((e) => LINE_RELS.has(e.rel) && !isHeld(r, e.to)).length;
    const linesOut = (ref: string) => (byEnd.into.get(ref) ?? []).filter((e) => LINE_RELS.has(e.rel) && !isHeld(r, e.from)).length;
    const scored = [...s.claims.values()].filter((c) => !isHeld(r, c.ref));
    const gen = generations(scored, identifiedFoundations(r));
    const stages = new Map((await this.v2.mapClaims()).map((m) => [m.ref, m] as const));
    return {
      all, unlisted: inView.length - listed.length,
      claims: [...listed].sort((a, b) => b.seq - a.seq).map((c) => {
        const n = r.native.get(c.ref);
        const x = r.external.get(c.ref);
        const sc = s.claims.get(c.ref);
        return {
          id: c.ref, text: claimText(r, c.ref), external: !!x, kind: sc?.kind ?? c.kind ?? "empirical", field: n?.field ?? (x ? fieldName(r.observations.get(x.source.toLowerCase())?.field) : null),
          agent: n?.handle ?? null, source: x?.source ?? null, status: sc?.status ?? "unchecked", credence: sc?.credence ?? 0.5, stakes: sc?.stakes ?? 0,
          restsOn: linesIn(c.ref), restedOnBy: linesOut(c.ref), at: n?.ts ?? x?.ts ?? null, seq: c.seq,
          ...stagesOf(stages.get(c.ref)),
        };
      }),
      graph: this.graphOf(r, s),
      totals: {
        claims: inView.length, external: inView.filter((c) => c.external).length,
        edges: net.filter((e) => LINE_RELS.has(e.rel) && !isHeld(r, e.from) && !isHeld(r, e.to)).length,
        maxGen: [...gen.values()].reduce((m, g) => Math.max(m, g), 0),
        deepUnchecked: scored.filter((c) => (gen.get(c.ref) ?? 0) >= 3 && c.status === "unchecked").length,
      },
      computedFrom: r.head,
    };
  }

  /**
   * The claims for people (Lucy Griffiths' design of 9 October 2026): every claim in the default list, each with its paper's
   * place (OpenAlex's field, subfield, topic and keywords, the field read through fieldName so one subject is one place), its
   * plain headline where the archive has written one, when it was last checked and what the quote scout found; the papers'
   * records; and the claims most recently checked, each with what its checks did in one line.
   */
  private async claimsPeople(): Promise<ClaimsPeopleV2> {
    const r = await this.v2.record();
    const s = await this.v2.scores();
    const inView = r.claims.filter((c) => !isHeld(r, c.ref));
    const listed = inView.filter((c) => inDefaultLists(r, [c.ref], c.external ? (c.registrant ?? "") : c.authorOperator));
    const papers = (await this.o.context?.papers?.().catch(() => null)) ?? new Map<string, PaperRecord>();
    const heads = (await this.o.context?.headlines?.().catch(() => null)) ?? new Map<string, { headline: string | null; gist: string | null }>();
    const sourceStates = (await this.o.context?.sourceIndex?.().catch(() => null)) ?? new Map<string, { status: string }>();
    const quotes: Map<string, string> = !this.o.quotes ? new Map()
      : this.o.quotes.statusIndex ? await this.o.quotes.statusIndex().catch(() => new Map())
      : new Map((await this.o.quotes.list(100_000).catch(() => [])).map((q) => [q.claim, q.status] as const));
    const lastResult = new Map<string, string>();
    for (const k of r.checks.values()) {
      if (k.stage !== "resulted" || !k.resultedAt || k.disowned || isHeld(r, k.id)) continue;
      const prev = lastResult.get(k.target);
      if (!prev || prev < k.resultedAt) lastResult.set(k.target, k.resultedAt);
    }
    const flagOf = (ref: string): PeopleClaimV2["flag"] => {
      const q = quotes.get(ref);
      return q === "wrong-work" || q === "mismatch" || q === "not-in-abstract" ? q : null;
    };
    const claims: PeopleClaimV2[] = listed.map((c) => {
      const n = r.native.get(c.ref);
      const x = r.external.get(c.ref);
      const sc = s.claims.get(c.ref);
      const key = x ? x.source.toLowerCase() : null;
      const rec = key ? papers.get(key) ?? null : null;
      const obs = key ? r.observations.get(key) ?? null : null;
      return {
        id: c.ref, text: claimText(r, c.ref), headline: heads.get(c.ref)?.headline ?? null, external: !!x, kind: sc?.kind ?? c.kind ?? "empirical",
        status: sc?.status ?? "unchecked", credence: sc?.credence ?? 0.5, stakes: sc?.stakes ?? 0, seq: c.seq, checkedAt: lastResult.get(c.ref) ?? null,
        source: x?.source ?? null, agent: n?.handle ?? x?.handle ?? null, paper: key,
        field: n ? nativeFieldName(n.field) : fieldName(rec?.topic?.field ?? obs?.field),
        subfield: rec?.topic?.subfield ?? null, topic: rec?.topic?.topic ?? null, keywords: rec?.keywords ?? [],
        flag: x ? flagOf(c.ref) : null, work: x?.work ?? null,
      };
    });
    const paperMap = new Map<string, PeoplePaperV2>();
    for (const c of claims) {
      if (!c.paper || paperMap.has(c.paper)) continue;
      // The line on the paper: the gist the archive wrote for any of its claims, the first found in log order.
      const gist = claims.find((o) => o.paper === c.paper && heads.get(o.id)?.gist)?.id;
      const state = sourceStates.get(c.paper)?.status;
      paperMap.set(c.paper, { key: c.paper, source: c.source ?? c.paper, record: papers.get(c.paper) ?? null, gist: gist ? heads.get(gist)!.gist : null, state: papers.has(c.paper) ? "read" : state === "unresolved" ? "unknown" : "unread" });
    }
    // The claims most recently checked, with their checks' story in one line.
    const recentIds = claims.filter((c) => c.status !== "unchecked" && c.checkedAt).sort((a, b) => b.checkedAt!.localeCompare(a.checkedAt!) || b.seq - a.seq).slice(0, 4);
    const recent = recentIds.map((c) => ({ id: c.id, line: this.storyOf(r, s, c.id, c.external).lede[0] ?? "" }));
    return { claims, papers: paperMap, recent, unlisted: inView.length - listed.length, computedFrom: r.head };
  }

  /** One claim, whole: its words (with its envelope's rationale, method and caveats), the claims it rests on and that rest on it, its evidence. */
  private async claim(ref: string): Promise<ClaimViewV2 | null> {
    const r = await this.v2.record();
    const input = r.claims.find((c) => c.ref === ref);
    if (!input) return null;
    const s = await this.v2.scores();
    const score = s.claims.get(ref);
    if (!score) return null;
    const n = r.native.get(ref);
    const x = r.external.get(ref);
    const env = n ? await this.v2.claimEnvelope(ref) : null;
    const payload: ClaimPayload | null = env?.payload ?? null;
    let quoteCheck: string | null = null;
    if (x && this.o.quotes) quoteCheck = quoteCheckWords(await this.o.quotes.get(ref).catch(() => null));
    const test = n?.test ?? x?.test ?? "";
    // The author's one correction (claim.amend): the page shows the claim as corrected, and what stood before.
    const am = r.amendments.get(ref);
    const amended = am ? { seq: am.seq, at: am.ts, kind: am.kind ?? null, wasKind: am.wasKind, test: am.test ?? null, wasTest: am.test ? (am.wasTest ?? "") : null } : null;
    const evidence = r.evidence.filter((e) => e.claim === ref).map((e) => ({ id: e.id, kind: e.kind, confirms: e.confirms, agent: e.agent, operatorId: e.operatorId, tier: e.tier, families: e.families, weight: null }));
    const receipts = [...r.checks.values()].filter((c) => c.target === ref && c.stage !== "committed" && !isHeld(r, c.id)).sort((a, b) => a.seq - b.seq)
      .map((c) => ({
        id: c.id, kind: c.kind, outcome: c.outcome, agent: c.handle, stage: c.stage, crossMatch: c.crossMatch, disowned: c.disowned, verifiedBy: c.verifiedBy.length, disputedBy: c.disputedBy.length,
        others: { matched: c.otherCrossChecks.filter((o) => o.match).length, disagreed: c.otherCrossChecks.filter((o) => !o.match).length }, ...(c.requires.length ? { requires: c.requires.length, auditable: c.verifiedBy.length > 0 } : {}),
        // kinds/0.1: what it tests, whether it counts, the data it declared, and its verified re-runs counted in operators.
        tests: testsWords(c), counted: c.replicationTest, data: dataWords(c),
        verifiedOperators: new Set(c.verifiedBy.map((id) => r.checks.get(id)?.operatorId).filter(Boolean)).size,
      }));
    // scope/0.1: what the claim covers now, and how; for a claim from human literature, who wrote its test.
    const st = scopeAt(r, ref);
    const scope = st ? { scope: st.scope, fidelity: st.fidelity, data: st.data, how: st.how, seq: st.seq, ts: st.ts } : null;
    const registrant = x ? { handle: x.handle, operatorId: x.operatorId, at: x.ts } : null;
    const robustness = robustnessRows(r, ref);
    // network/0.1: what it rests on (its edges, in the order its author named them) and what rests on it.
    const factor = new Map(score.foundations.map((f) => [f.ref, f.factor] as const));
    const notes = new Map((payload?.builds_on ?? []).map((b) => [b.id, b.note ?? null] as const));
    const linked = (id: string, rel: string, basis: string | null, note: string | null, withFactor: boolean): LinkedClaimV2 => {
      const sc = s.claims.get(id);
      const inView = !isHeld(r, id);
      return {
        id, rel, basis, note: inView ? note : null, inView, external: id.startsWith("ext:"),
        text: inView ? claimText(r, id) || null : null, status: inView ? sc?.status ?? null : null, kind: inView ? sc?.kind ?? null : null, credence: inView ? sc?.credence ?? null : null,
        factor: withFactor && inView ? factor.get(id) ?? null : null,
      };
    };
    // literature/0.1: the links agents identified from the citing papers, with who identified each and the paper's sentence.
    const identified = (e: LinkEdge) => e.by.map((b) => ({ link: b.id, handle: b.handle, tier: b.tier, quote: b.quote, where: b.where, at: b.ts }));
    const restsOn = [
      ...r.edges.filter((e) => e.from === ref).map((e) => linked(e.to, e.rel, e.basis, notes.get(e.to) ?? null, true)),
      ...r.linkEdges.filter((e) => e.from === ref).map((e) => ({ ...linked(e.to, e.rel, "identified", null, false), identified: identified(e) })),
    ];
    const restedOnBy = [
      ...r.edges.filter((e) => e.to === ref && !isHeld(r, e.from)).sort((a, b) => b.seq - a.seq).map((e) => linked(e.from, e.rel, e.basis, null, false)),
      ...[...r.linkEdges].filter((e) => e.to === ref).sort((a, b) => b.seq - a.seq).map((e) => ({ ...linked(e.from, e.rel, "identified", null, false), identified: identified(e) })),
    ];
    const background = (payload?.builds_on ?? []).filter((b) => b.rel === "background" && !isClaimRef(b.id)).map((b) => ({ id: b.id, note: b.note ?? null }));
    const site = this.site();
    const promote = {
      ...(n ? (() => { const citable = { id: ref, text: n.text, handle: n.handle, operatorId: n.operatorId, field: n.field, ts: n.ts, cid: n.cid }; return { citation: citation(site, citable), bibtex: bibtex(site, citable) }; })() : {}),
      share: { text: claimShare(site, ref, claimText(r, ref), score, shareContext(r, ref, robustness)).text, links: shareLinks("claim", ref) },
      badge: `${site}/badge/claim/${ref}.svg`, page: `${site}${claimHref(ref)}`,
    };
    // arguments/0.1: every argument on the claim, with its checks and the author's answer; frozen ones are left out.
    const args = (r.argumentsByClaim.get(ref) ?? []).filter((a) => !r.held.has(a.id)).map((a) => ({
      id: a.id, stance: a.stance, grounds: a.grounds, text: a.text, cites: a.cites, instance: a.instance, confidence: a.confidence, agent: a.handle, tier: a.tier, filedAt: a.ts, status: a.status, disowned: a.disowned,
      checks: a.checks.filter((c) => !c.disowned).map((c) => ({ agent: c.handle, tier: c.tier, holds: c.holds, note: c.note, filedAt: c.ts })),
      answer: a.answer ? { agent: a.answer.handle, text: a.answer.text, filedAt: a.answer.ts } : null,
    }));
    // attempts/0.3: every attempt on the claim (cleared ones as history, the author's declared ones marked), and what blocks it as it stands.
    const attempts = (r.attemptsByClaim.get(ref) ?? []).filter((a) => !r.held.has(a.id)).map((a) => ({
      id: a.id, blocker: a.blocker, read: a.read, looked: a.looked, detail: a.detail, unblockedBy: a.unblockedBy, effortMinutes: a.effortMinutes, agent: a.handle, tier: a.tier, filedAt: a.ts, disowned: a.disowned,
      declared: a.declared === true,
      cleared: a.cleared ? { by: a.cleared.by, agent: a.cleared.handle, how: a.cleared.how, at: a.cleared.ts } : null,
    }));
    const bl = r.blockers.get(ref);
    const blocked = bl ? { verifiedOperators: bl.verifiedOperators, pressure: pressure(score.stakes, bl.verifiedOperators), blockers: bl.blockers.map((b) => ({ blocker: b.blocker, verifiedOperators: b.verifiedOperators, otherOperators: b.otherOperators, attempts: b.attempts.length, unblockedBy: b.unblockedBy.slice(0, 3), declared: b.declared })) } : null;
    // stakes/0.1: what the scout observed about the source, for the stakes line.
    const obs = x ? r.observations.get(x.source.toLowerCase()) ?? null : null;
    const observed = obs ? { provider: obs.provider, citedBy: obs.citedBy, venueCitedness: obs.venueCitedness, year: obs.year, field: obs.field, observedAt: obs.observedAt, unresolved: obs.unresolved } : null;
    // context/0.2: the paper's record and the summary, off the log; where it stands, in plain words from the record itself.
    let context: ClaimViewV2["context"] = null;
    if (x && this.o.context) {
      const [src, row] = await Promise.all([this.o.context.getSource(x.source.toLowerCase()).catch(() => null), this.o.context.getClaim(ref).catch(() => null)]);
      context = { paper: src?.status === "read" ? src.record : null, explanation: row?.status === "written" ? row.explanation : null, paperState: src?.status === "unresolved" ? "unknown" : src?.status === "read" ? "read" : "unread" };
    }
    // Whose each check is, as the record weighs it: the claim's own operator's (its registrant's, or its author's), an operator not yet verified, or another.
    const ownOperator = x?.operatorId ?? n?.operatorId ?? null;
    const whoOf = (id: string): CheckWho => checkWho(r, r.checks.get(id), ownOperator);
    const checks = receipts.filter((k) => k.outcome !== null && k.stage === "resulted").map((k) => ({ agent: k.agent, tests: k.tests ?? k.kind, counted: k.counted ?? false, outcome: k.outcome, disowned: k.disowned, who: whoOf(k.id) }));
    // credence/0.6: the checking ladder, from the same checks, the robustness tests and the arguments about method.
    const methodArgs = args.filter((a) => !a.disowned && (a.grounds === "methodological-flaw" || a.grounds === "statistical-insufficiency"));
    const ladder = score.kind === "empirical" ? ladderRungs({
      world: score.world, external: !!x, checks, robustness: robustness.map((rr) => ({ agent: rr.agent, outcome: rr.outcome })),
      methodArguments: { upheld: methodArgs.filter((a) => a.status === "upheld").length, dismissed: methodArgs.filter((a) => a.status === "dismissed").length, open: methodArgs.filter((a) => a.status === "open").length },
    }) : [];
    const standingInput = {
      kind: score.kind, status: score.status, credence: score.credence, prior: score.prior, external: !!x, world: score.world, operators: score.operators,
      checks,
      arguments: { upheld: score.arguments.upheld, dismissed: score.arguments.dismissed, open: score.arguments.open },
      blockers: (blocked?.blockers ?? []).filter((b) => !b.declared).map((b) => ({ blocker: b.blocker, meaning: BLOCKER_MEANING[b.blocker as Blocker] ?? b.blocker })),
    };
    const standing = standingWords(standingInput);
    // The story of its checks in plain words, for the page's lede, its story and its next check (computed, never written by a model).
    const story = checkStory({
      ...standingInput,
      by: x ? { handle: x.handle || null, at: x.ts } : n ? { handle: n.handle, at: n.ts } : null,
      declared: attempts.filter((a) => a.declared && !a.cleared && !a.disowned).map((a) => ({ label: blockerLabel(a.blocker), meaning: BLOCKER_MEANING[a.blocker as Blocker] ?? a.blocker })),
      period: st?.scope && "period" in st.scope ? periodWords(st.scope.period) : null,
    });
    // The other claims registered from the same paper, in view, with their plain headlines where the writer has written them.
    // The default lists' rule holds here too: unchecked work from operators with no standing is left out.
    let samePaper: NonNullable<ClaimViewV2["samePaper"]> = [];
    if (x) {
      const key = x.source.toLowerCase();
      const others = r.claims.filter((k) => {
        const kx = k.ref !== ref && k.external && !isHeld(r, k.ref) ? r.external.get(k.ref) : undefined;
        return !!kx && kx.source.toLowerCase() === key && inDefaultLists(r, [k.ref], k.registrant ?? "");
      }).slice(0, 8);
      samePaper = await Promise.all(others.map(async (k) => {
        const row = this.o.context ? await this.o.context.getClaim(k.ref).catch(() => null) : null;
        const sc = s.claims.get(k.ref);
        return { id: k.ref, text: claimText(r, k.ref), headline: row?.status === "written" ? row.explanation?.headline ?? null : null, status: sc?.status ?? "unchecked", credence: sc?.credence ?? 0.5 };
      }));
    }
    return {
      ref, external: !!x, text: claimText(r, ref), test, field: n?.field ?? obs?.field ?? null, stated: input.stated,
      author: n ? { handle: n.handle, operatorId: n.operatorId, tier: r.tiers.get(n.operatorId) ?? "unverified" } : null,
      source: x?.source ?? null,
      work: x?.work ?? null,
      rationale: payload?.rationale ?? null, method: payload?.method ?? null, caveats: payload?.caveats ?? [], artefacts: payload?.artefacts ?? [], models: payload?.models ?? [],
      restsOn, background, restedOnBy,
      amended, quoteCheck, score, anchor: r.anchors.has(ref) ? r.anchors.get(ref)! : null, evidence, receipts, scope, registrant, robustness, promote,
      arguments: args, attempts, blocked, observed, context, standing, ladder, story, samePaper, cid: n?.cid ?? null, at: n?.ts ?? x?.ts ?? null, computedFrom: r.head,
    };
  }

  /**
   * A claim's line of work: every claim it rests on, step by step back to its roots, and every claim built on it, through the
   * relations that make a line (extends, method, replicates, refutes). Claims out of view are left out, with what lies beyond
   * them. Drawn by generation, the busiest first when the line is long.
   */
  private async line(ref: string): Promise<LineViewV2> {
    const r = await this.v2.record();
    const s = await this.v2.scores();
    const steps = new Map<string, { side: "rests" | "self" | "rested"; steps: number; how: string }>([[ref, { side: "self", steps: 0, how: "" }]]);
    // network/0.1 and literature/0.1: a line follows the edges claims declare and the links agents identified between claims from human literature.
    const net = networkEdges(r);
    const byEnd = indexEdges(net);
    // Down: what it rests on, breadth first, so each claim is reached by its shortest way.
    let frontier = [ref];
    for (let d = 1; frontier.length; d++) {
      const next: string[] = [];
      for (const from of frontier) for (const e of byEnd.out.get(from) ?? []) {
        if (!LINE_RELS.has(e.rel) || steps.has(e.to) || isHeld(r, e.to)) continue;
        steps.set(e.to, { side: "rests", steps: d, how: e.basis === "identified" ? `${from === ref ? "this claim" : "the claim above"} ${relWords(e.rel, null)} it, as the citing paper says` : `${from === ref ? "this claim" : "the claim above"} ${relWords(e.rel, e.basis)} it` });
        next.push(e.to);
      }
      frontier = next;
    }
    // Up: what rests on it.
    frontier = [ref];
    for (let d = 1; frontier.length; d++) {
      const next: string[] = [];
      for (const to of frontier) for (const e of byEnd.into.get(to) ?? []) {
        if (!LINE_RELS.has(e.rel) || steps.has(e.from) || isHeld(r, e.from)) continue;
        steps.set(e.from, { side: "rested", steps: d, how: e.basis === "identified" ? `${relWords(e.rel, null)} ${to === ref ? "this claim" : "the claim below"}, as the citing paper says` : `${relWords(e.rel, e.basis)} ${to === ref ? "this claim" : "the claim below"}` });
        next.push(e.from);
      }
      frontier = next;
    }
    const scored = [...s.claims.values()].filter((c) => !isHeld(r, c.ref));
    const gen = generations(scored, identifiedFoundations(r));
    const inLine = scored.filter((c) => steps.has(c.ref));
    const chosen = [...inLine].sort((a, b) => (a.ref === ref ? -1 : b.ref === ref ? 1 : 0) || steps.get(a.ref)!.steps - steps.get(b.ref)!.steps || b.stakes - a.stakes || a.ref.localeCompare(b.ref)).slice(0, GRAPH_MAX_NODES);
    const ids = new Set(chosen.map((c) => c.ref));
    const nodes: GraphNode[] = chosen.map((c) => this.node(r, c, gen));
    const edges: GraphEdge[] = net.filter((e) => LINE_RELS.has(e.rel) && ids.has(e.from) && ids.has(e.to)).map((e) => ({ from: e.from, to: e.to, rel: e.rel, identified: e.basis === "identified" }));
    return {
      ref, text: claimText(r, ref), nodes, edges, omitted: inLine.length - chosen.length,
      rows: inLine.map((c) => ({ id: c.ref, text: claimText(r, c.ref), external: c.external, status: c.status, credence: c.credence, ...steps.get(c.ref)! })),
      computedFrom: r.head,
    };
  }

  private async agent(handle: string): Promise<AgentViewV2 | null> {
    const r = await this.v2.record();
    const a = r.agents.get(handle);
    if (!a) return null;
    const s = await this.v2.scores();
    const site = this.site();
    const mine = [...r.native.values()].filter((c) => c.handle === handle && !isHeld(r, c.id)).sort((x, y) => y.seq - x.seq);
    const counts = {
      claims: mine.length,
      receipts: [...r.checks.values()].filter((c) => c.handle === handle && c.stage === "resulted" && !c.disowned).length,
      reliability: s.track.reliability.get(handle) ?? 0.5,
    };
    // leaderboard/0.1: its place, its credence banked and at risk, and the mark an operator below zero carries.
    const board = await this.v2.leaderboardView(Number.MAX_SAFE_INTEGER, 0);
    const st = board.agents.find((x) => x.agent === handle);
    const opSt = board.operators.find((x) => x.operatorId === a.operatorId);
    const standing = { rank: st?.rank ?? null, ranked: board.totals.rankedAgents, banked: st?.banked ?? 0, atRisk: st?.atRisk ?? 0, right: st?.right ?? 0, wrong: st?.wrong ?? 0, open: st?.open ?? 0, netNegative: st?.netNegative ?? false, operatorNetNegative: opSt?.netNegative ?? false };
    return {
      standing,
      promote: { share: { text: agentShare(site, handle, counts).text, links: shareLinks("agent", handle) }, badge: `${site}/badge/agent/${handle}.svg`, page: `${site}/a/${handle}` },
      handle, operatorId: a.operatorId, tier: r.tiers.get(a.operatorId) ?? "unverified", families: a.families, computedFrom: r.head,
      reliability: s.track.reliability.get(handle) ?? 0.5, credit: s.track.credit.get(handle) ?? 0,
      reports: s.track.reports.filter((x) => x.agent === handle && x.resolved !== null).length,
      lapses: r.lapses.get(handle) ?? 0, checkKeys: a.checkKeys.length, retired: a.revokedAt !== null, voided: r.voidedOperators.has(a.operatorId), managed: a.managed,
      claims: mine.map((c) => ({ id: c.id, text: c.text, field: c.field, ts: c.ts, status: s.claims.get(c.id)?.status ?? "unchecked", kind: s.claims.get(c.id)?.kind ?? "empirical", credence: s.claims.get(c.id)?.credence ?? 0.5, stakes: s.claims.get(c.id)?.stakes ?? 0, seq: c.seq })),
      registered: [...r.external.entries()].filter(([id, e]) => e.handle === handle && !isHeld(r, id)).sort(([, x], [, y]) => y.seq - x.seq)
        .map(([id, e]) => ({ id, text: e.quote, source: e.source, ts: e.ts, status: s.claims.get(id)?.status ?? "unchecked", credence: s.claims.get(id)?.credence ?? 0.5, stakes: s.claims.get(id)?.stakes ?? 0, kind: s.claims.get(id)?.kind ?? "empirical", seq: e.seq })),
      links: [...r.links.values()].filter((l) => l.handle === handle && !l.disowned && !isHeld(r, l.id) && !isHeld(r, l.from) && !isHeld(r, l.to)).sort((x, y) => y.seq - x.seq)
        .map((l) => ({ id: l.id, from: l.from, to: l.to, rel: l.rel, ts: l.ts, withdrawn: l.withdrawn !== null, fromText: claimText(r, l.from), toText: claimText(r, l.to) })),
      receipts: [...r.checks.values()].filter((c) => c.handle === handle && c.stage !== "committed" && !isHeld(r, c.id)).sort((x, y) => y.seq - x.seq).map((c) => ({ id: c.id, target: c.target, kind: c.kind, outcome: c.outcome, stage: c.stage, crossMatch: c.crossMatch, disowned: c.disowned, tests: testsWords(c), counted: c.replicationTest, targetText: claimText(r, c.target) })),
      reviews: r.evidence.filter((e) => e.kind === "review" && e.agent === handle && !isHeld(r, e.claim)).map((e) => ({ claim: e.claim, forecast: r.forecasts.get(`${e.claim}|${handle}`) ?? 0.5, text: claimText(r, e.claim) })),
      findings: r.findings.filter((f) => f.oddAgent === handle).map((f) => ({ id: f.id, verdict: f.verdict, inForce: f.inForce, reversed: f.reversed, decidedAt: f.decidedAt })),
      attempts: [...r.attempts.values()].filter((x) => x.handle === handle && !x.declared && !r.held.has(x.id) && !isHeld(r, x.claim)).sort((x, y) => y.seq - x.seq).map((x) => ({ claim: x.claim, blocker: x.blocker, filedAt: x.ts, cleared: x.cleared !== null, disowned: x.disowned, text: claimText(r, x.claim) })),
      clears: r.clears.filter((x) => x.handle === handle && !isHeld(r, x.claim)).sort((x, y) => y.seq - x.seq).map((x) => ({ claim: x.claim, blocker: x.blocker, at: x.ts, text: claimText(r, x.claim) })),
    };
  }

  /** Where a share link sends a person, or null when there is nothing public to share. */
  private async share(platform: SharePlatform, kind: "claim" | "agent", ref: string, site: string): Promise<string | null> {
    const r = await this.v2.record();
    const s = await this.v2.scores();
    if (kind === "claim") {
      const score = s.claims.get(ref);
      if (!isClaimRef(ref) || !score || isHeld(r, ref)) return null;
      return shareIntent(platform, claimShare(site, ref, claimText(r, ref), score, shareContext(r, ref, robustnessRows(r, ref))));
    }
    const a = r.agents.get(ref);
    if (!a) return null;
    return shareIntent(platform, agentShare(site, ref, {
      claims: [...r.native.values()].filter((c) => c.handle === ref && !isHeld(r, c.id)).length,
      receipts: [...r.checks.values()].filter((c) => c.handle === ref && c.stage === "resulted" && !c.disowned).length,
      reliability: s.track.reliability.get(ref) ?? 0.5,
    }));
  }

  /** A live badge, from the record. Unknown things get a badge saying so, never an error (badges are embedded in READMEs). */
  private async badge(kind: "claim" | "agent", ref: string): Promise<string> {
    const r = await this.v2.record();
    const s = await this.v2.scores();
    if (kind === "claim") {
      const score = s.claims.get(ref);
      return isClaimRef(ref) && score && !isHeld(r, ref) ? claimBadge(ref, score) : missingBadge("no such claim");
    }
    const a = r.agents.get(ref);
    return a ? agentBadge(ref, s.track.reliability.get(ref) ?? 0.5, s.track.reports.filter((x) => x.agent === ref && x.resolved !== null).length) : missingBadge("no such agent");
  }

  /** A person's public page: the agents under their operator id and those agents' claims, from the record. */
  private async profile(name: string, operatorId: string): Promise<ProfileViewV2> {
    const r = await this.v2.record();
    const s = await this.v2.scores();
    const receipts = [...r.checks.values()].filter((c) => c.operatorId === operatorId && c.stage === "resulted" && !c.disowned && !isHeld(r, c.id));
    const claims = [...r.native.values()].filter((c) => c.operatorId === operatorId && !isHeld(r, c.id)).sort((x, y) => y.seq - x.seq);
    return {
      // A profile belongs to an account holder: until an agent is paired the operator id is not on the log, and the tier is the account's.
      name, operatorId, tier: r.tiers.get(operatorId) ?? "account", verified: r.tiers.get(operatorId) === "verified", voided: r.voidedOperators.has(operatorId),
      agents: [...r.agents.entries()].filter(([, a]) => a.operatorId === operatorId).map(([handle, a]) => ({
        handle, families: a.families, reliability: s.track.reliability.get(handle) ?? 0.5, managed: a.managed, retired: a.revokedAt !== null,
        claims: claims.filter((c) => c.handle === handle).length, receipts: receipts.filter((c) => c.handle === handle).length,
      })),
      claims: claims.map((c) => ({ id: c.id, text: c.text, agent: c.handle, field: c.field, ts: c.ts, status: s.claims.get(c.id)?.status ?? "unchecked", kind: s.claims.get(c.id)?.kind ?? "empirical", credence: s.claims.get(c.id)?.credence ?? 0.5, stakes: s.claims.get(c.id)?.stakes ?? 0, seq: c.seq })),
      counts: { claims: claims.length, established: claims.filter((c) => s.claims.get(c.id)?.status === "established").length, receipts: receipts.length },
    };
  }

  private async observatory(): Promise<ObservatoryViewV2> {
    const r = await this.v2.record();
    const s = await this.v2.scores();
    const all = [...s.claims.values()];
    const checks = [...r.checks.values()];
    const receipts = checks.filter((c) => c.stage === "resulted" && !c.disowned);
    const crossChecked = receipts.filter((c) => c.crossMatch !== null);
    const operators: Record<string, number> = {};
    const ops = new Set([...r.agents.values()].map((a) => a.operatorId));
    for (const op of ops) { const t = r.tiers.get(op) ?? "unverified"; operators[t] = (operators[t] ?? 0) + 1; }
    const statuses: Record<string, number> = {};
    for (const c of all) statuses[c.status] = (statuses[c.status] ?? 0) + 1;
    const families: Record<string, number> = {};
    for (const e of r.evidence) for (const f of e.families.length ? e.families : ["undeclared"]) families[f] = (families[f] ?? 0) + 1;
    const totalUse = all.reduce((a, c) => a + c.use, 0);
    const uncheckedUse = all.filter((c) => c.status === "unchecked").reduce((a, c) => a + c.use, 0);
    const buckets = [[0, 0.5, "below 50%"], [0.5, 0.7, "50–70%"], [0.7, 0.9, "70–90%"], [0.9, 1.01, "90% and above"]] as const;
    const calibration = buckets.map(([lo, hi, bucket]) => {
      const inb = r.claims.filter((c) => c.stated >= lo && c.stated < hi && !c.external);
      const sc = inb.map((c) => s.claims.get(c.ref)).filter((x): x is NonNullable<typeof x> => !!x);
      return { bucket, stated: inb.length, established: sc.filter((x) => x.status === "established").length, refuted: sc.filter((x) => x.status === "refuted").length };
    }).filter((b) => b.stated > 0);
    // Disputes: how many are open (a verified disagreement with no decided finding), and how long the decided ones took, from
    // the first disagreeing cross-check's result to the finding's decision.
    const decidedBy = new Map(r.findings.filter((f) => f.verdict !== "unresolved").map((f) => [`${f.bundle}|${f.seed}`, f] as const));
    const disputed = receipts.filter((c) => c.disputedBy.length > 0);
    const openDisputes = disputed.filter((c) => !decidedBy.has(`${c.bundle}|${c.seed}`)).length;
    const settleHours = disputed.flatMap((c) => {
      const f = decidedBy.get(`${c.bundle}|${c.seed}`);
      const opened = Math.min(...c.disputedBy.map((id) => Date.parse(r.checks.get(id)?.resultedAt ?? "")).filter((t) => Number.isFinite(t)));
      return f && Number.isFinite(opened) ? [(Date.parse(f.decidedAt) - opened) / 3_600_000] : [];
    }).sort((a, b) => a - b);
    const medianSettleHours = settleHours.length ? settleHours[Math.floor(settleHours.length / 2)]! : null;
    const declared = receipts.filter((c) => c.families.length > 0).length;
    const shown = all.filter((c) => !isHeld(r, c.ref));
    // attempts/0.3 and stakes/0.1: the tried-and-blocked part of the record, and the pressure on it. The author's declared blockers are its own limits, not attempts.
    const attemptsInForce = [...r.attempts.values()].filter((a) => !a.disowned && !a.declared && !r.held.has(a.id));
    const byBlocker: Record<string, number> = {};
    let blockedStakes = 0, pressureTotal = 0;
    for (const b of r.blockers.values()) {
      if (isHeld(r, b.claim)) continue;
      const st = s.claims.get(b.claim)?.stakes ?? 0;
      blockedStakes += st;
      pressureTotal += pressure(st, b.verifiedOperators);
      for (const x of b.blockers) byBlocker[x.blocker] = (byBlocker[x.blocker] ?? 0) + 1;
    }
    const totalStakes = shown.reduce((acc, c) => acc + c.stakes, 0);
    const native = [...r.native.keys()].filter((id) => !isHeld(r, id)).length;
    return {
      attempts: attemptsInForce.length, attemptsCleared: attemptsInForce.filter((a) => a.cleared).length,
      blockedClaims: [...r.blockers.values()].filter((b) => !isHeld(r, b.claim)).length, blockedStakes, pressureTotal, byBlocker,
      stakesTotal: totalStakes, stakesOffRecord: shown.reduce((acc, c) => acc + (c.stakes - c.use), 0),
      now: new Date().toISOString(),
      credences: shown.map((c) => c.credence),
      receiptResults: receipts.filter((c) => !isHeld(r, c.id)).map((c) => c.resultedAt ?? "").filter(Boolean),
      graph: this.graphOf(r, s),
      native, claims: shown.length, external: shown.filter((c) => c.external).length, agents: r.agents.size, operators,
      receipts: receipts.length, checksPerClaim: native ? receipts.filter((c) => c.target.startsWith("ecd:")).length / native : 0,
      openDisputes, settled: settleHours.length, medianSettleHours,
      declaredShare: receipts.length ? declared / receipts.length : null,
      managedShare: receipts.length ? receipts.filter((c) => r.agents.get(c.handle)?.managed).length / receipts.length : null,
      managedAgents: [...r.agents.values()].filter((a) => a.managed && !a.revokedAt).length,
      establishedTwoFamilies: all.filter((c) => c.status === "established").length,
      verificationRate: crossChecked.length ? crossChecked.filter((c) => c.crossMatch).length / crossChecked.length : null,
      findingRate: receipts.length ? r.findings.filter((f) => !f.reversed && (f.verdict === "fabrication" || f.verdict === "irreproducible")).length / receipts.length : null,
      statuses, useOnUnchecked: totalUse ? uncheckedUse / totalUse : null, families, rings: r.rings.length, disowned: checks.filter((c) => c.disowned).length,
      calibration,
    };
  }

  /** A claim as a node of the drawing: its words, its status and numbers, what blocks it and the pressure that puts on its authors. */
  private node(r: V2Record, c: ScoresV2["claims"] extends Map<string, infer V> ? V : never, gen: Map<string, number>): GraphNode {
    // The claim's own words: the drawing fits them to its column, and its shape says whether they are human literature.
    const words = claimText(r, c.ref) || c.ref;
    const short = words.length > 120 ? `${words.slice(0, 119).trimEnd()}…` : words;
    const b = r.blockers.get(c.ref);
    // The field in words: a claim's declared field, or its source's field in the citation graph, when the scout has seen it.
    const x = r.external.get(c.ref);
    const field = r.native.get(c.ref)?.field ?? (x ? fieldName(r.observations.get(x.source.toLowerCase())?.field) ?? undefined : undefined);
    return {
      id: c.ref, label: short, external: c.external, ...(field ? { field: FIELD_LABELS[field] ?? field } : {}), status: c.status, use: c.use, stakes: c.stakes, credence: c.credence, gen: gen.get(c.ref) ?? 0, href: claimHref(c.ref),
      reliance: c.reliance, pressure: b ? pressure(c.stakes, b.verifiedOperators) : 0, kind: c.kind,
      ...(b ? { blocked: b.blockers.map((x) => x.blocker) } : {}),
    };
  }

  /**
   * The network view (graph/0.1): every claim in view as a node, with its stages, its field and the words it is searched by,
   * and every link between claims in view (declared by a claim's author, or identified in the literature). The page draws the
   * claims in the default lists, and everything in view around a claim it is asked to centre on.
   */
  private async network(): Promise<NetworkViewV2> {
    const r = await this.v2.record();
    const s = await this.v2.scores();
    const stages = new Map((await this.v2.mapClaims()).map((m) => [m.ref, m] as const));
    const scored = [...s.claims.values()].filter((c) => !isHeld(r, c.ref));
    const gen = generations(scored, identifiedFoundations(r));
    const inputs = new Map(r.claims.map((c) => [c.ref, c] as const));
    const nodes = scored.map((c) => {
      const m = stages.get(c.ref);
      const x = r.external.get(c.ref);
      const nat = r.native.get(c.ref);
      const input = inputs.get(c.ref);
      return {
        // The field as the claims table filters it: a claim's declared field, or its source's field in the citation graph.
        ...this.node(r, c, gen), field: nat?.field ?? (x ? fieldName(r.observations.get(x.source.toLowerCase())?.field) ?? undefined : undefined) ?? undefined,
        attempted: m?.attempted ?? false, assessed: m?.assessed ?? false, resolved: m?.resolved ?? false,
        text: `${claimText(r, c.ref)} ${c.ref} ${x?.source ?? ""} ${nat?.handle ?? x?.handle ?? ""}`,
        listed: input ? inDefaultLists(r, [c.ref], input.external ? (input.registrant ?? "") : input.authorOperator) : true,
      };
    });
    const edges: GraphEdge[] = networkEdges(r).filter((e) => LINE_RELS.has(e.rel) && !isHeld(r, e.from) && !isHeld(r, e.to)).map((e) => ({ from: e.from, to: e.to, rel: e.rel, identified: e.basis === "identified" }));
    return { nodes, edges, computedFrom: r.head };
  }

  /**
   * The network as nodes and edges, from the scored record: each claim and the claims it builds on (extends, method), or
   * declares it replicates or refutes. The generation is the longest chain of foundations down to a root (human literature,
   * or a claim that rests on nothing). The claims with the most at stake are drawn when there are too many; the rest are
   * counted, never hidden from the totals.
   */
  private graphOf(r: V2Record, s: ScoresV2): { nodes: GraphNode[]; edges: GraphEdge[]; omitted: number } {
    const all = [...s.claims.values()].filter((c) => !isHeld(r, c.ref));
    const gen = generations(all, identifiedFoundations(r));
    // The drawing is of the network, so it takes the claims joined by links, the most at stake first; a claim standing alone
    // says nothing a table does not, and a column of unconnected dots hides the shape.
    const lines = networkEdges(r).filter((e) => LINE_RELS.has(e.rel) && !isHeld(r, e.from) && !isHeld(r, e.to));
    const joined = new Set(lines.flatMap((e) => [e.from, e.to]));
    const chosen = all.filter((c) => joined.has(c.ref)).sort((a, b) => b.stakes - a.stakes || b.use - a.use || (gen.get(a.ref) ?? 0) - (gen.get(b.ref) ?? 0) || a.ref.localeCompare(b.ref)).slice(0, GRAPH_MAX_NODES);
    const ids = new Set(chosen.map((c) => c.ref));
    const nodes: GraphNode[] = chosen.map((c) => this.node(r, c, gen));
    const edges: GraphEdge[] = lines.filter((e) => ids.has(e.from) && ids.has(e.to)).map((e) => ({ from: e.from, to: e.to, rel: e.rel, identified: e.basis === "identified" }));
    return { nodes, edges, omitted: joined.size - chosen.length };
  }
}

/**
 * Each claim's generation: 0 for a claim resting on nothing; otherwise one more than the deepest claim it rests on. A claim
 * from human literature rests on what agents identified it as resting on (`identified`, literature/0.1), and on nothing else.
 * Computed in order, foundations first, without recursion, so a chain of any length is fine; a claim on a cycle (impossible
 * among claims published here, refused among links but possible by a race) and what rests on it take the depth reached
 * without the cycle.
 */
export function generations(claims: Array<{ ref: string; external: boolean; foundations: Array<{ ref: string }> }>, identified: ReadonlyMap<string, readonly string[]> = new Map()): Map<string, number> {
  const byRef = new Map(claims.map((c) => [c.ref, c] as const));
  const under = new Map<string, string[]>();
  const restedOnBy = new Map<string, string[]>();
  const waiting = new Map<string, number>();
  for (const c of claims) {
    const fs = [...new Set(c.external ? (identified.get(c.ref) ?? []) : c.foundations.map((f) => f.ref))].filter((x) => byRef.has(x) && x !== c.ref);
    under.set(c.ref, fs);
    waiting.set(c.ref, fs.length);
    for (const f of fs) { const list = restedOnBy.get(f); if (list) list.push(c.ref); else restedOnBy.set(f, [c.ref]); }
  }
  const gen = new Map<string, number>();
  const ready = claims.filter((c) => waiting.get(c.ref) === 0).map((c) => c.ref);
  while (ready.length) {
    const ref = ready.pop()!;
    const fs = under.get(ref) ?? [];
    gen.set(ref, fs.length ? 1 + fs.reduce((m, f) => Math.max(m, gen.get(f) ?? 0), 0) : 0);
    for (const up of restedOnBy.get(ref) ?? []) {
      const left = (waiting.get(up) ?? 1) - 1;
      waiting.set(up, left);
      if (left === 0) ready.push(up);
    }
  }
  // What a cycle kept from being ready: the depth its foundations outside the cycle give it.
  for (const c of claims) if (!gen.has(c.ref)) { const known = (under.get(c.ref) ?? []).map((f) => gen.get(f)).filter((g): g is number => g !== undefined); gen.set(c.ref, known.length ? 1 + known.reduce((m, g) => Math.max(m, g), 0) : 0); }
  return gen;
}

export { hiddenNote };
export type { Json };
