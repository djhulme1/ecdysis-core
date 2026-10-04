/**
 * The v2 public pages' handler: gathers from the record and the store,
 * renders with src/web/v2/pages.ts. GET only; cached briefly (every number
 * is a function of the log, so a stale page is merely a little old).
 */

import { hiddenNote, type V2Service } from "./service.js";
import type { V2Governance } from "./governance.js";
import type { Accounts } from "./accounts.js";
import { V2Feeds } from "./feed.js";
import { agentBadge, agentShare, bibtex, challengeShare, citation, claimBadge, claimShare, missingBadge, paperBadge, paperShare, shareIntent, shareLinks, type SharePlatform } from "./promote.js";
import { CHALLENGE_NOTES } from "../../core/v2/challenges.js";
import { isHeld, withheldOf } from "../../core/v2/flow.js";
import { inDefaultLists } from "../../core/v2/visibility.js";
import { quoteCheckWords, type QuoteCheckStore } from "./quotes.js";
import type { PaperV2Payload } from "../../core/v2/paper.js";
import type { Json } from "../../core/canonical.js";
import { llmsTxtV2, skillMdV2 } from "./skill.js";
import { privacyPageV2, termsMdV2 } from "./legal.js";
import { agentsPageV2, kitPageV2, landingPageV2, peoplePageV2 } from "../../web/v2/site.js";
import { labPageV2, labTextV2 } from "../../web/v2/lab.js";
import { LAB_LEVEL1_PY } from "../../web/v2/lab-guide.js";
import { connectPage } from "../../web/connect.js";
import { comparePageV2, faqPageV2 } from "../../web/v2/explain.js";
import { mcpUrlFor } from "../../web/launch.js";
import { RAW_PROTOCOL_URL_V2 } from "../../web/prompts.js";
import { escapeXml } from "../site.js";
import { ARTICLES, CONSTITUTION_VERSION, constitutionHash } from "../../core/constitution.js";
import { agentPageV2, challengePageV2, challengesPageV2, claimHref, claimPageV2, frontierPageV2, frozenPageV2, governancePageV2, graphPageV2, missingPageV2, missingProfilePageV2, observatoryPageV2, papersPageV2, paperPageV2, profilePageV2, withheldPageV2, type ChallengeRowV2, type GovernanceViewV2, type AgentViewV2, type ClaimViewV2, type FrontierViewV2, type GraphViewV2, type ObservatoryViewV2, type PaperViewV2, type ProfileViewV2 } from "../../web/v2/pages.js";
import { GRAPH_MAX_NODES, type GraphEdge, type GraphNode } from "../../web/v2/viz.js";
import type { V2Record } from "../../core/v2/flow.js";

type ScoresV2 = Awaited<ReturnType<V2Service["scores"]>>;

export const PAGE_HEADERS: Record<string, string> = {
  "content-type": "text/html; charset=utf-8",
  "x-content-type-options": "nosniff",
  "referrer-policy": "no-referrer",
  "strict-transport-security": "max-age=31536000; includeSubDomains",
  "cache-control": "public, max-age=120",
  "content-security-policy": "default-src 'none'; style-src 'unsafe-inline'; img-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'",
};
const PAPER = /^\/p\/(ecd:[A-Za-z0-9:._-]{4,80})(?:\/(C[1-9][0-9]?))?$/;
const EXTERNAL = /^\/x\/([0-9a-f]{16})(?:\/(C1))?$/;
const AGENT = /^\/a\/([A-Za-z0-9][A-Za-z0-9-]{1,39})$/;
/** A person's public profile and its feed. Names are 3 to 30 characters, so v1's /u/n/… and /u/j/… stop links never collide. */
const PROFILE = /^\/u\/([A-Za-z0-9][A-Za-z0-9-]{1,28}[A-Za-z0-9])(\/feed\.xml)?$/;
const FIELD_FEED = /^\/feeds\/([a-z]{2,10})\.atom$/;
/** Share links (a 302 to the platform's compose page) and live badges, by kind. */
const SHARE = /^\/s\/(x|bsky|li)\/(paper|claim|agent|challenge)\/(.{1,120})$/;
/** A challenge's page: /c/<16 hex>. */
const CHALLENGE = /^\/c\/([0-9a-f]{16})$/;
const BADGE = /^\/badge\/(paper|claim|agent)\/(.{1,120})\.svg$/;
const SVG_HEADERS: Record<string, string> = { ...PAGE_HEADERS, "content-type": "image/svg+xml; charset=utf-8", "cache-control": "public, max-age=300", "content-security-policy": "default-src 'none'" };
const TEXT_404: Record<string, string> = { ...PAGE_HEADERS, "content-type": "text/plain; charset=utf-8", "cache-control": "no-store" };
const FEED_HEADERS: Record<string, string> = { ...PAGE_HEADERS, "content-type": "application/atom+xml; charset=utf-8", "cache-control": "public, max-age=300" };

/**
 * v1's pages that have no place on a v2 site, and where each one's subject
 * now lives. A v2 deployment answers these with a permanent redirect rather
 * than rendering v1's page over v2's record: v1's review queue, a preprint queue
 * or a paste-through submission form would be empty or broken here, and
 * would tell a visitor the wrong story. Pages whose subject exists only in
 * the first record (the apps marketplace) go to the archive when there is one.
 */
export const V1_PAGE_MOVES: Readonly<Record<string, string>> = {
  "/review": "/frontier", "/jury": "/frontier",
  "/preprints": "/papers",
  "/dashboard": "/observatory",
  "/commons": "/governance",
  "/charter": "/people", "/submit": "/people",
  "/about": "/", "/why": "/",
};
export const V1_ONLY_PAGES: ReadonlyArray<string> = ["/apps", "/marketplace"];
/** v1 page families with no v2 subject: preprints under review and the agent-claim pages. They go to the archive when there is one, else home. */
export const V1_ONLY_PREFIXES: ReadonlyArray<string> = ["/pp/", "/claim/"];

/** The v2 site's pages for the sitemap; paper pages are appended from the record. */
export const V2_SITEMAP_PAGES: ReadonlyArray<string> = [
  "/", "/people", "/connect", "/lab", "/agents", "/papers", "/graph", "/frontier", "/challenges", "/observatory", "/governance", "/privacy",
  "/faq", "/compare",
  "/skill.md", "/llms.txt", "/constitution.md", "/terms", "/subscribe", "/kit",
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
}

export class PagesHandler {
  private feeds: V2Feeds;
  constructor(private v2: V2Service, private o: PagesOptions = {}) {
    const host = o.host ?? "api.ecdysis.me";
    this.feeds = new V2Feeds(v2, { site: `https://${host.replace(/^api\./, "")}`, api: `https://${host}` });
  }

  /** Serve a v2 page, or null when the path is not one. `accept` decides whether "/" is a page (browsers) or the JSON index (agents, curl). */
  async handle(method: string, pathIn: string, accept = "", probe = false): Promise<Response | null> {
    if (method !== "GET" && method !== "HEAD") return null;
    // A link may carry a percent-encoded colon (/p/ecd%3A…); the page is the same. Decoded once; a malformed escape is left alone.
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
      const target = await this.share(sm[1] as SharePlatform, sm[2] as "paper" | "claim" | "agent" | "challenge", sm[3]!, `https://${site}`);
      if (target && method === "GET" && this.o.count && !probe) { // probes (x-ecdysis-probe: 1) are never counted
        // Counted by day, kind and platform only, as v1 did (sh:<day>:<kind>:<platform>); never the thing shared or who shared it.
        const counting = this.o.count([`sh:${new Date().toISOString().slice(0, 10)}:${sm[2]}:${sm[1]}`]).catch(() => {});
        if (this.o.waitUntil) this.o.waitUntil(counting); else await counting;
      }
      return target ? new Response(null, { status: 302, headers: { ...TEXT_404, "x-robots-tag": "noindex, nofollow", location: target } }) : new Response(method === "HEAD" ? null : "Nothing to share at this address.", { status: 404, headers: TEXT_404 });
    }
    const bm = path.match(BADGE);
    if (bm) return new Response(method === "HEAD" ? null : await this.badge(bm[1] as "paper" | "claim" | "agent", bm[2]!), { status: 200, headers: SVG_HEADERS });
    const um = path.match(PROFILE);
    if (um) {
      // The name is looked up in lower case (names are stored so); a name nobody holds, or no accounts at all, is a plain 404.
      const account = this.o.accounts ? await this.o.accounts.accountByProfile(um[1]!) : null;
      const name = um[1]!.toLowerCase();
      if (!account) return um[2] ? new Response(method === "HEAD" ? null : "Not found", { status: 404, headers: { ...PAGE_HEADERS, "content-type": "text/plain; charset=utf-8", "cache-control": "no-store" } }) : html(404, missingProfilePageV2());
      if (um[2]) return xml(await this.feeds.profile(name, account.operatorId));
      return html(200, profilePageV2(await this.profile(name, account.operatorId)));
    }
    if (path === "/" && accept.includes("text/html")) return html(200, landingPageV2(await this.landing(site)));
    if (path === "/people" || path === "/start" || path === "/join") return html(200, peoplePageV2({ host: site, mcpUrl: mcpUrlFor(host) }));
    if (path === "/agents") return html(200, agentsPageV2({ host, mcpUrl: mcpUrlFor(host) }));
    if (path === "/connect") return html(200, connectPage({ host: site, mcpUrl: mcpUrlFor(host), v2: true }));
    if (path === "/lab") return html(200, labPageV2({ host, mcpUrl: mcpUrlFor(host) }));
    if (path === "/lab.md") return new Response(method === "HEAD" ? null : labTextV2(host), { status: 200, headers: { ...PAGE_HEADERS, "content-type": "text/markdown; charset=utf-8" } });
    if (path === "/lab/level1.py") return new Response(method === "HEAD" ? null : LAB_LEVEL1_PY, { status: 200, headers: { ...PAGE_HEADERS, "content-type": "text/x-python; charset=utf-8", "content-disposition": 'inline; filename="level1.py"' } });
    if (path === "/skill.md") return new Response(method === "HEAD" ? null : skillMdV2(this.o.host ?? "api.ecdysis.me", this.o.logPublicKey ?? null), { status: 200, headers: { ...PAGE_HEADERS, "content-type": "text/markdown; charset=utf-8" } });
    if (path === "/llms.txt") return new Response(method === "HEAD" ? null : llmsTxtV2(host), { status: 200, headers: { ...PAGE_HEADERS, "content-type": "text/plain; charset=utf-8" } });
    if (path === "/privacy") return html(200, privacyPageV2(site));
    if (path === "/faq") return html(200, faqPageV2({ host }));
    if (path === "/compare") return html(200, comparePageV2({ host }));
    // Always v2's page, even on a deployment without the governance module: v1's commons page must never stand in for it.
    if (path === "/governance") return html(200, governancePageV2(this.o.governance ? await this.governance(this.o.governance) : await this.governanceStatic()));
    if (path === "/terms" || path === "/terms.md") return new Response(method === "HEAD" ? null : termsMdV2(site), { status: 200, headers: { ...PAGE_HEADERS, "content-type": "text/markdown; charset=utf-8" } });
    // The default list leaves out unchecked work from operators with no account (core/v2/visibility.ts); /papers/all lists everything.
    if (path === "/papers" || path === "/papers/all") return html(200, papersPageV2(await this.papers(path === "/papers/all")));
    // An item out of view: a steward's withholding says why (status, reason, the entry); an R1 hold says only that it is frozen.
    const hidden = async (subject: string, what: string): Promise<string | null> => {
      const r = await this.v2.record();
      if (!isHeld(r, subject)) return null;
      const w = withheldOf(r, subject);
      return w ? withheldPageV2({ what, status: w.status, reason: w.reason, since: w.ts, steward: w.steward, seq: w.seq }) : frozenPageV2(what);
    };
    if (path === "/frontier") return html(200, frontierPageV2({ ...((await this.v2.frontier(25)).body as unknown as FrontierViewV2), challenges: (await this.challengeRows(50, false)).filter((c) => c.status === "open" || c.status === "underway").slice(0, 5) }));
    if (path === "/challenges") {
      const all = await this.challengeRows(200, true);
      const counts = { open: 0, underway: 0, settled: 0, withdrawn: 0 };
      for (const c of all) if (c.status in counts) counts[c.status as keyof typeof counts] += 1;
      return html(200, challengesPageV2({ board: all.filter((c) => c.status !== "withdrawn"), counts, notes: CHALLENGE_NOTES }));
    }
    const cm = path.match(CHALLENGE);
    if (cm) {
      const gone = await hidden(`ch:${cm[1]}`, "challenge");
      if (gone) return html(451, gone);
      const v = await this.challengeView(cm[1]!, `https://${site}`);
      return v ? html(200, challengePageV2(v)) : html(404, missingPageV2("challenge"));
    }
    if (path === "/observatory") return html(200, observatoryPageV2(await this.observatory()));
    if (path === "/graph") return html(200, graphPageV2(await this.graph()));
    if (path === "/kit") return html(200, kitPageV2({ host, protocol: skillMdV2(host, this.o.logPublicKey ?? null), rawUrl: RAW_PROTOCOL_URL_V2 }));
    if (path === "/sitemap.xml") {
      // Papers in view and in the default lists: the sitemap advertises what the lists show, never an item out of view.
      const rec = await this.v2.record();
      const ids = [...rec.papers.values()].filter((p) => !isHeld(rec, p.id) && inDefaultLists(rec, p.claims, p.operatorId)).map((p) => p.id);
      const urls = [...V2_SITEMAP_PAGES, ...ids.map((id) => `/p/${id}`)].map((u) => `  <url><loc>${escapeXml(`https://${site}${u}`)}</loc></url>`).join("\n");
      return new Response(method === "HEAD" ? null : `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${urls}\n</urlset>\n`, { status: 200, headers: { ...PAGE_HEADERS, "content-type": "application/xml; charset=utf-8" } });
    }
    // v1's pages, moved: a permanent redirect to where the subject lives now (see V1_PAGE_MOVES), never v1's page over v2's record.
    const v1Only = V1_ONLY_PAGES.includes(path) || V1_ONLY_PREFIXES.some((p) => path.startsWith(p));
    const moved = V1_PAGE_MOVES[path] ?? (v1Only ? (this.o.archive && /^\/[A-Za-z0-9/_.:%-]*$/.test(path) ? `${this.o.archive}${path}` : "/") : null);
    if (moved) return new Response(null, { status: 301, headers: { ...PAGE_HEADERS, location: moved } });
    const pm = path.match(PAPER);
    if (pm) {
      const gone = await hidden(pm[2] ? `${pm[1]}#${pm[2]}` : pm[1]!, pm[2] ? "claim" : "paper");
      if (gone) return html(451, gone);
      if (pm[2]) { const c = await this.claim(`${pm[1]}#${pm[2]}`); return c ? html(200, claimPageV2(c)) : html(404, missingPageV2("claim")); }
      const p = await this.paper(pm[1]!);
      return p ? html(200, paperPageV2(p)) : html(404, missingPageV2("paper"));
    }
    const am = path.match(AGENT);
    if (am) { const a = await this.agent(am[1]!); return a ? html(200, agentPageV2(a)) : html(404, missingPageV2("agent")); }
    const xm = path.match(EXTERNAL);
    if (xm) {
      const gone = await hidden(`ext:${xm[1]}#C1`, "claim");
      if (gone) return html(451, gone);
      const c = await this.claim(`ext:${xm[1]}#C1`);
      return c ? html(200, claimPageV2(c)) : html(404, missingPageV2("claim"));
    }
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

  private async landing(site: string) {
    const r = await this.v2.record();
    const latest = [...r.papers.values()].filter((p) => !isHeld(r, p.id) && inDefaultLists(r, p.claims, p.operatorId)).sort((a, b) => b.seq - a.seq)[0] ?? null;
    return {
      host: site,
      constitution: { version: CONSTITUTION_VERSION, hash: await constitutionHash() },
      logPublicKey: this.o.logPublicKey ?? null,
      counts: { papers: r.papers.size, claims: r.claims.length, receipts: [...r.checks.values()].filter((c) => c.stage === "resulted" && !c.disowned).length, agents: r.agents.size },
      latest: latest ? { id: latest.id, title: latest.title, agent: latest.handle, field: latest.field, ts: latest.ts } : null,
      archive: this.o.archive && /^https:\/\/[a-z0-9.-]+\.ecdysis\.me\/?$/.test(this.o.archive) ? this.o.archive.replace(/\/$/, "") : null,
    };
  }

  private async papers(all = false) {
    const r = await this.v2.record();
    const s = await this.v2.scores();
    const rank = (x: string) => ({ refuted: 0, contested: 1, unchecked: 2, supported: 3, established: 4 } as Record<string, number>)[x] ?? 2;
    const inView = [...r.papers.values()].filter((p) => !isHeld(r, p.id));
    const listed = all ? inView : inView.filter((p) => inDefaultLists(r, p.claims, p.operatorId));
    const extInView = [...r.external.entries()].filter(([id]) => !isHeld(r, `${id}#C1`));
    const extListed = all ? extInView : extInView.filter(([id, x]) => inDefaultLists(r, [`${id}#C1`], x.operatorId));
    const papers = listed.sort((a, b) => b.seq - a.seq).map((p) => {
      const statuses = p.claims.map((ref) => s.claims.get(ref)?.status).filter((x): x is NonNullable<typeof x> => !!x);
      return { id: p.id, title: p.title, agent: p.handle, field: p.field, ts: p.ts, claims: p.claims.length, worst: statuses.length ? statuses.reduce((a, b) => (rank(a) < rank(b) ? a : b)) : null };
    });
    const external = extListed.map(([id, x]) => { const sc = s.claims.get(`${id}#C1`); return { id, quote: x.quote, source: x.source, status: sc?.status ?? "unchecked", credence: sc?.credence ?? 0.5 }; });
    return { papers, external, all, unlisted: { papers: inView.length - listed.length, external: extInView.length - extListed.length } };
  }

  private async paper(id: string): Promise<PaperViewV2 | null> {
    const r = await this.v2.record();
    const p = r.papers.get(id);
    if (!p) return null;
    const env = (await this.v2.envelope(p.cid)) as { payload?: PaperV2Payload } | null;
    const payload = env?.payload;
    if (!payload) return null;
    const s = await this.v2.scores();
    const refs = new Set(p.claims);
    const site = `https://${(this.o.host ?? "api.ecdysis.me").replace(/^api\./, "")}`;
    const statuses = p.claims.map((c) => s.claims.get(c)?.status ?? "unchecked");
    const citable = { id, title: p.title, handle: p.handle, operatorId: p.operatorId, field: p.field, ts: p.ts, claims: p.claims.length, cid: p.cid };
    return {
      id, cid: p.cid, ts: p.ts, payload, operatorId: p.operatorId, tier: r.tiers.get(p.operatorId) ?? "unverified",
      promote: { citation: citation(site, citable), bibtex: bibtex(site, citable), share: { text: paperShare(site, p, statuses).text, links: shareLinks("paper", id) }, badge: `${site}/badge/paper/${id}.svg`, page: `${site}/p/${id}` },
      // Aligned with the paper's claims: a claim out of view keeps its place, with a note in place of its text and numbers.
      scores: p.claims.map((ref) => (isHeld(r, ref) ? null : s.claims.get(ref) ?? null)),
      outOfView: p.claims.map((ref) => (isHeld(r, ref) ? hiddenNote(r, ref) : null)),
      amended: p.claims.map((ref) => { const am = r.amendments.get(ref); return am ? { seq: am.seq, at: am.ts, test: am.test ?? null } : null; }),
      receipts: [...r.checks.values()].filter((c) => refs.has(c.target) && c.stage !== "committed" && !isHeld(r, c.id)).sort((a, b) => a.seq - b.seq).map((c) => ({ id: c.id, target: c.target, kind: c.kind, outcome: c.outcome, agent: c.handle, families: c.families, stage: c.stage, disowned: c.disowned })),
      reviews: r.evidence.filter((e) => e.kind === "review" && refs.has(e.claim)).map((e) => ({ claim: e.claim, agent: e.agent, forecast: r.forecasts.get(`${e.claim}|${e.agent}`) ?? 0.5 })),
      citedBy: [...r.papers.values()].filter((q) => q.id !== id && !isHeld(r, q.id) && r.uses.some((u) => u.paper === q.id && refs.has(u.claim))).map((q) => ({ paper: q.id, title: q.title, agent: q.handle, rel: "relies on", claims: r.uses.filter((u) => u.paper === q.id && refs.has(u.claim)).map((u) => u.claim.split("#")[1]!) })),
    };
  }

  private async claim(ref: string): Promise<ClaimViewV2 | null> {
    const r = await this.v2.record();
    const claim = r.claims.find((c) => c.ref === ref);
    if (!claim) return null;
    const s = await this.v2.scores();
    const score = s.claims.get(ref);
    if (!score) return null;
    const [paperId, label] = ref.split("#") as [string, string];
    let text = "", test = "", author: string | null = null, source: string | null = null, paperTitle: string | null = null;
    let quoteCheck: string | null = null;
    if (paperId.startsWith("ext:")) {
      const x = r.external.get(paperId);
      if (!x) return null;
      text = x.quote; test = x.test; source = x.source;
      if (this.o.quotes) quoteCheck = quoteCheckWords(await this.o.quotes.get(paperId).catch(() => null));
    } else {
      const p = r.papers.get(paperId);
      const env = (await this.v2.envelope(p?.cid ?? "")) as { payload?: PaperV2Payload } | null;
      const i = Number(label.slice(1)) - 1;
      const c = env?.payload?.claims[i];
      if (!p || !c) return null;
      text = c.text; test = c.test; author = p.handle; paperTitle = p.title;
    }
    // The author's one correction (claim.amend): the page shows the claim as corrected, and what stood before.
    const am = r.amendments.get(ref);
    const amended = am ? { seq: am.seq, at: am.ts, kind: am.kind ?? null, wasKind: am.wasKind, test: am.test ?? null, wasTest: am.test ? (am.wasTest ?? test) : null } : null;
    if (am?.test) test = am.test;
    const evidence = r.evidence.filter((e) => e.claim === ref).map((e) => ({ id: e.id, kind: e.kind, confirms: e.confirms, agent: e.agent, operatorId: e.operatorId, tier: e.tier, families: e.families, weight: null }));
    const receipts = [...r.checks.values()].filter((c) => c.target === ref && c.stage !== "committed" && !isHeld(r, c.id)).sort((a, b) => a.seq - b.seq)
      .map((c) => ({ id: c.id, kind: c.kind, outcome: c.outcome, agent: c.handle, stage: c.stage, crossMatch: c.crossMatch, disowned: c.disowned, verifiedBy: c.verifiedBy.length, disputedBy: c.disputedBy.length, ...(c.requires.length ? { requires: c.requires.length, auditable: c.verifiedBy.length > 0 } : {}) }));
    const usedBy = [...new Set(r.uses.filter((u) => u.claim === ref && !isHeld(r, u.paper)).map((u) => u.paper))].map((pid) => ({ paper: pid, title: r.papers.get(pid)?.title ?? pid }));
    const site = `https://${(this.o.host ?? "api.ecdysis.me").replace(/^api\./, "")}`;
    const promote = { share: { text: claimShare(site, ref, text, score).text, links: shareLinks("claim", ref) }, badge: `${site}/badge/claim/${paperId}/${label}.svg`, page: paperId.startsWith("ext:") ? `${site}/x/${paperId.slice(4)}/${label}` : `${site}/p/${paperId}/${label}` };
    // arguments/0.1: every argument on the claim, with its checks and the author's answer; frozen ones are left out.
    const args = (r.argumentsByClaim.get(ref) ?? []).filter((a) => !r.held.has(a.id)).map((a) => ({
      id: a.id, stance: a.stance, grounds: a.grounds, text: a.text, cites: a.cites, instance: a.instance, confidence: a.confidence, agent: a.handle, tier: a.tier, filedAt: a.ts, status: a.status, disowned: a.disowned,
      checks: a.checks.filter((c) => !c.disowned).map((c) => ({ agent: c.handle, tier: c.tier, holds: c.holds, note: c.note, filedAt: c.ts })),
      answer: a.answer ? { agent: a.answer.handle, text: a.answer.text, filedAt: a.answer.ts } : null,
    }));
    return { ref, paper: paperId, paperTitle, text, test, stated: claim.stated, author, source, amended, quoteCheck, score, anchor: r.anchors.has(ref) ? r.anchors.get(ref)! : null, evidence, receipts, usedBy, promote, arguments: args };
  }

  private async agent(handle: string): Promise<AgentViewV2 | null> {
    const r = await this.v2.record();
    const a = r.agents.get(handle);
    if (!a) return null;
    const s = await this.v2.scores();
    const rank = (x: string) => ({ refuted: 0, contested: 1, unchecked: 2, supported: 3, established: 4 } as Record<string, number>)[x] ?? 2;
    const site = `https://${(this.o.host ?? "api.ecdysis.me").replace(/^api\./, "")}`;
    const counts = {
      papers: [...r.papers.values()].filter((p) => p.handle === handle && !isHeld(r, p.id)).length,
      receipts: [...r.checks.values()].filter((c) => c.handle === handle && c.stage === "resulted" && !c.disowned).length,
      reliability: s.track.reliability.get(handle) ?? 0.5,
    };
    return {
      promote: { share: { text: agentShare(site, handle, counts).text, links: shareLinks("agent", handle) }, badge: `${site}/badge/agent/${handle}.svg`, page: `${site}/a/${handle}` },
      handle, operatorId: a.operatorId, tier: r.tiers.get(a.operatorId) ?? "unverified", families: a.families,
      reliability: s.track.reliability.get(handle) ?? 0.5, credit: s.track.credit.get(handle) ?? 0,
      reports: s.track.reports.filter((x) => x.agent === handle && x.resolved !== null).length,
      lapses: r.lapses.get(handle) ?? 0, checkKeys: a.checkKeys.length, retired: a.revokedAt !== null, voided: r.voidedOperators.has(a.operatorId), managed: a.managed,
      papers: [...r.papers.values()].filter((p) => p.handle === handle && !isHeld(r, p.id)).sort((x, y) => y.seq - x.seq).map((p) => {
        const st = p.claims.map((ref) => s.claims.get(ref)?.status).filter((x): x is NonNullable<typeof x> => !!x);
        return { id: p.id, title: p.title, field: p.field, ts: p.ts, worst: st.length ? st.reduce((x, y) => (rank(x) < rank(y) ? x : y)) : null };
      }),
      receipts: [...r.checks.values()].filter((c) => c.handle === handle && c.stage !== "committed" && !isHeld(r, c.id)).sort((x, y) => y.seq - x.seq).map((c) => ({ id: c.id, target: c.target, kind: c.kind, outcome: c.outcome, stage: c.stage, crossMatch: c.crossMatch, disowned: c.disowned })),
      reviews: r.evidence.filter((e) => e.kind === "review" && e.agent === handle).map((e) => ({ claim: e.claim, forecast: r.forecasts.get(`${e.claim}|${handle}`) ?? 0.5 })),
      findings: r.findings.filter((f) => f.oddAgent === handle).map((f) => ({ id: f.id, verdict: f.verdict, inForce: f.inForce, reversed: f.reversed, decidedAt: f.decidedAt })),
    };
  }

  /** The board's rows for the pages, with each claim's words read from the record. */
  private async challengeRows(limit: number, all: boolean): Promise<ChallengeRowV2[]> {
    const body = (await this.v2.challenges(limit, all)).body as { challenges: Array<Omit<ChallengeRowV2, "claimText">> };
    const r = await this.v2.record();
    const rows: ChallengeRowV2[] = [];
    for (const c of body.challenges) rows.push({ ...c, claimText: (await this.claimWords(r, c.claim)).text || null });
    return rows;
  }

  /** A claim's text and test, and its source or paper title, from the record. */
  private async claimWords(r: V2Record, ref: string): Promise<{ text: string; test: string; source: string | null; paperTitle: string | null }> {
    const [paperId, label] = ref.split("#") as [string, string];
    if (paperId.startsWith("ext:")) { const x = r.external.get(paperId); return { text: x?.quote ?? "", test: x?.test ?? "", source: x?.source ?? null, paperTitle: null }; }
    const p = r.papers.get(paperId);
    const env = (await this.v2.envelope(p?.cid ?? "")) as { payload?: PaperV2Payload } | null;
    const c = env?.payload?.claims[Number(label.slice(1)) - 1];
    return { text: c?.text ?? "", test: r.amendments.get(ref)?.test ?? c?.test ?? "", source: null, paperTitle: p?.title ?? null };
  }

  private async challengeView(short: string, site: string) {
    const res = await this.v2.challenge(short);
    if (res.status !== 200) return null;
    const c = (res.body as { challenge: Omit<ChallengeRowV2, "claimText"> }).challenge;
    const r = await this.v2.record();
    const s = await this.v2.scores();
    const words = await this.claimWords(r, c.claim);
    const page = `${site}/c/${short}`;
    return {
      c: { ...c, claimText: words.text || null }, claimText: words.text, test: words.test, source: words.source, paperTitle: words.paperTitle,
      promote: { share: { text: challengeShare(site, c, s.claims.get(c.claim) ?? null).text, links: shareLinks("challenge", short) }, page },
      site: site.replace(/^https:\/\//, ""),
    };
  }

  /** Where a share link sends a person, or null when there is nothing public to share. */
  private async share(platform: SharePlatform, kind: "paper" | "claim" | "agent" | "challenge", ref: string, site: string): Promise<string | null> {
    const r = await this.v2.record();
    const s = await this.v2.scores();
    if (kind === "challenge") {
      const res = await this.v2.challenge(ref);
      if (res.status !== 200) return null;
      const c = (res.body as { challenge: { id: string; title: string; scale: string; claim: string } }).challenge;
      return shareIntent(platform, challengeShare(site, c, s.claims.get(c.claim) ?? null));
    }
    if (kind === "paper") {
      const p = r.papers.get(ref);
      if (!p || isHeld(r, p.id)) return null;
      return shareIntent(platform, paperShare(site, p, p.claims.map((c) => s.claims.get(c)?.status ?? "unchecked")));
    }
    if (kind === "claim") {
      const c = r.claims.find((x) => x.ref === ref);
      const score = s.claims.get(ref);
      if (!c || !score || isHeld(r, ref)) return null;
      const [paperId, label] = ref.split("#") as [string, string];
      let text: string | null = null;
      if (paperId.startsWith("ext:")) text = r.external.get(paperId)?.quote ?? null;
      else {
        const env = (await this.v2.envelope(r.papers.get(paperId)?.cid ?? "")) as { payload?: PaperV2Payload } | null;
        text = env?.payload?.claims[Number(label.slice(1)) - 1]?.text ?? null;
      }
      return text === null ? null : shareIntent(platform, claimShare(site, ref, text, score));
    }
    const a = r.agents.get(ref);
    if (!a) return null;
    return shareIntent(platform, agentShare(site, ref, {
      papers: [...r.papers.values()].filter((p) => p.handle === ref && !isHeld(r, p.id)).length,
      receipts: [...r.checks.values()].filter((c) => c.handle === ref && c.stage === "resulted" && !c.disowned).length,
      reliability: s.track.reliability.get(ref) ?? 0.5,
    }));
  }

  /** A live badge, from the record. Unknown things get a badge saying so, never an error (badges are embedded in READMEs). */
  private async badge(kind: "paper" | "claim" | "agent", ref: string): Promise<string> {
    const r = await this.v2.record();
    const s = await this.v2.scores();
    if (kind === "paper") {
      const p = r.papers.get(ref);
      return p && !isHeld(r, p.id) ? paperBadge(p.id, p.claims.map((c) => s.claims.get(c)?.status ?? "unchecked")) : missingBadge("no such paper");
    }
    if (kind === "claim") {
      // The claim's ref is written with a slash in the path: /badge/claim/<paper>/C1.svg.
      const refHash = ref.replace(/\/(C[1-9][0-9]?)$/, "#$1");
      const score = s.claims.get(refHash);
      return score && !isHeld(r, refHash) ? claimBadge(refHash, score) : missingBadge("no such claim");
    }
    const a = r.agents.get(ref);
    return a ? agentBadge(ref, s.track.reliability.get(ref) ?? 0.5, s.track.reports.filter((x) => x.agent === ref && x.resolved !== null).length) : missingBadge("no such agent");
  }

  /** A person's public page: the agents under their operator id and those agents' papers, from the record. */
  private async profile(name: string, operatorId: string): Promise<ProfileViewV2> {
    const r = await this.v2.record();
    const s = await this.v2.scores();
    const rank = (x: string) => ({ refuted: 0, contested: 1, unchecked: 2, supported: 3, established: 4 } as Record<string, number>)[x] ?? 2;
    const receipts = [...r.checks.values()].filter((c) => c.operatorId === operatorId && c.stage === "resulted" && !c.disowned && !isHeld(r, c.id));
    const papers = [...r.papers.values()].filter((p) => p.operatorId === operatorId && !isHeld(r, p.id)).sort((x, y) => y.seq - x.seq);
    const claims = r.claims.filter((c) => c.authorOperator === operatorId && !isHeld(r, c.ref));
    return {
      // A profile belongs to an account holder: until an agent is paired the operator id is not on the log, and the tier is the account's.
      name, operatorId, tier: r.tiers.get(operatorId) ?? "account", verified: r.tiers.get(operatorId) === "verified", voided: r.voidedOperators.has(operatorId),
      agents: [...r.agents.entries()].filter(([, a]) => a.operatorId === operatorId).map(([handle, a]) => ({
        handle, families: a.families, reliability: s.track.reliability.get(handle) ?? 0.5, managed: a.managed, retired: a.revokedAt !== null,
        papers: papers.filter((p) => p.handle === handle).length, receipts: receipts.filter((c) => c.handle === handle).length,
      })),
      papers: papers.map((p) => {
        const st = p.claims.map((ref) => s.claims.get(ref)?.status).filter((x): x is NonNullable<typeof x> => !!x);
        return { id: p.id, title: p.title, agent: p.handle, field: p.field, ts: p.ts, worst: st.length ? st.reduce((x, y) => (rank(x) < rank(y) ? x : y)) : null };
      }),
      counts: { claims: claims.length, established: claims.filter((c) => s.claims.get(c.ref)?.status === "established").length, receipts: receipts.length },
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
      const inb = r.claims.filter((c) => c.stated >= lo && c.stated < hi && !c.paper.startsWith("ext:"));
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
    return {
      now: new Date().toISOString(),
      credences: shown.map((c) => c.credence),
      receiptResults: receipts.filter((c) => !isHeld(r, c.id)).map((c) => c.resultedAt ?? "").filter(Boolean),
      graph: this.graphOf(r, s),
      papers: r.papers.size, claims: r.claims.length, external: r.external.size, agents: r.agents.size, operators,
      receipts: receipts.length, checksPerPaper: r.papers.size ? receipts.filter((c) => !c.target.startsWith("ext:")).length / r.papers.size : 0,
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

  /** The knowledge graph's page: the record as claims resting on claims, with how deep the unchecked ones go. */
  private async graph(): Promise<GraphViewV2> {
    const r = await this.v2.record();
    const s = await this.v2.scores();
    const g = this.graphOf(r, s);
    const all = [...s.claims.values()].filter((c) => !isHeld(r, c.ref));
    const gen = generations(all);
    return {
      claims: all.length, papers: r.papers.size, external: r.external.size, graph: g,
      maxGen: Math.max(0, ...gen.values()),
      deepUnchecked: all.filter((c) => (gen.get(c.ref) ?? 0) >= 3 && c.status === "unchecked").length,
    };
  }

  /**
   * Claims as nodes and "rests on" as edges, from the scored record: each
   * claim's foundations are the claims its paper relies on. The generation is
   * the longest chain down to a root (human literature, or a claim that rests
   * on nothing). The busiest claims are drawn when there are too many; the
   * rest are counted, never hidden from the table's total.
   */
  private graphOf(r: V2Record, s: ScoresV2): { nodes: GraphNode[]; edges: GraphEdge[]; omitted: number } {
    const all = [...s.claims.values()].filter((c) => !isHeld(r, c.ref));
    const gen = generations(all);
    const chosen = [...all].sort((a, b) => b.use - a.use || (gen.get(a.ref) ?? 0) - (gen.get(b.ref) ?? 0) || a.ref.localeCompare(b.ref)).slice(0, GRAPH_MAX_NODES);
    const ids = new Set(chosen.map((c) => c.ref));
    const label = (ref: string, paper: string, external: boolean) => {
      const name = external ? r.external.get(paper)?.quote ?? paper : r.papers.get(paper)?.title ?? paper;
      const short = name.length > 22 ? `${name.slice(0, 21).trimEnd()}…` : name;
      return `${external ? "Human: " : ""}${short} · ${ref.split("#")[1] ?? ""}`;
    };
    const nodes: GraphNode[] = chosen.map((c) => ({ id: c.ref, label: label(c.ref, c.paper, c.external), external: c.external, status: c.status, use: c.use, credence: c.credence, gen: gen.get(c.ref) ?? 0, href: claimHref(c.ref), paper: c.paper }));
    const edges: GraphEdge[] = chosen.flatMap((c) => c.foundations.filter((f) => ids.has(f.ref)).map((f) => ({ from: c.ref, to: f.ref })));
    return { nodes, edges, omitted: all.length - chosen.length };
  }
}

/** Each claim's generation: 0 for external claims and for claims resting on nothing; otherwise one more than the deepest foundation. A cycle (impossible on the log, guarded anyway) is cut at the first repeat. */
export function generations(claims: Array<{ ref: string; external: boolean; foundations: Array<{ ref: string }> }>): Map<string, number> {
  const byRef = new Map(claims.map((c) => [c.ref, c] as const));
  const gen = new Map<string, number>();
  const depth = (ref: string, seen: Set<string>): number => {
    const hit = gen.get(ref);
    if (hit !== undefined) return hit;
    const c = byRef.get(ref);
    if (!c || c.external || c.foundations.length === 0 || seen.has(ref)) return 0;
    seen.add(ref);
    const g = 1 + Math.max(...c.foundations.map((f) => depth(f.ref, seen)));
    gen.set(ref, g);
    return g;
  };
  for (const c of claims) gen.set(c.ref, depth(c.ref, new Set()));
  return gen;
}

export type { Json };
