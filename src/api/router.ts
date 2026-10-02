/**
 * Thin HTTP layer over EcdysisService. No policy lives here — only parsing,
 * rate limiting, and uniform headers. Responses never echo internal errors:
 * unexpected failures return a correlation id, not a stack trace.
 */

import type { Json } from "../core/canonical.js";
import type { EcdysisService, ShareKind } from "./service.js";
import { ARTICLES, constitutionHash, CONSTITUTION_VERSION, REVIEW_WINDOW_DAYS } from "../core/constitution.js";
import { badgeSvg, bibtexFor, constitutionMd, feedAtom, FIELD_LABELS, llmsTxt, robotsTxt, sitemapXml, skillMd, termsMd } from "./site.js";
import { PAPER_ID } from "../web/design.js";
import { looksLikePrivateKey, MAX_PASTE_CHARS, parseBundle, submitFormPage, submitResultPage, type StepResult } from "../web/submit.js";
import { aboutPage, agentsPage, forkPage, kitPage, papersPage, peoplePage, privacyPage } from "../web/pages.js";
import { observatoryPage } from "../web/observatory.js";
import { reviewPage, type Decision, type QueueBody } from "../web/review.js";
import { appsPage } from "../web/apps.js";
import { preprintGonePage, preprintPage, preprintsPage, type PreprintListItem, type PreprintView } from "../web/preprints.js";
import { paperPage as renderPaper } from "../web/paper.js";
import type { Herald } from "./herald.js";
import { digestNotice, subscribePage, type Newsletter } from "./newsletter.js";
import { handleConsole, isConsolePath, type ConsoleDeps } from "./operator.js";
import type { JuryAlerts } from "./alerts.js";
import type { Doorbells } from "./doorbells.js";
import { FIELDS } from "../core/schema.js";
import { challengesBody } from "./challenges.js";
import { dayFunnelKeys, endpointOf, funnelKeys, HUMAN_PAGES, pageKeyOf, referrerBucket, stepKeys } from "./funnel.js";
import { handleMcp } from "./mcp.js";
import { v2Tools } from "./v2/tools.js";
import type { V2Service } from "./v2/service.js";
import type { MeHandler } from "./v2/me.js";
import { isStewardPath, type StewardHandler } from "./v2/steward.js";
import type { PagesHandler } from "./v2/pages.js";
import { agentMissingPage, agentPage } from "../web/agent.js";
import { claimMissingPage, claimPage, claimStatusCode } from "../web/claim.js";
import type { ShareData } from "../web/share.js";
import { graphPage } from "../web/graph.js";
import { frontierPage } from "../web/frontier.js";
import { commonsPage } from "../web/commons.js";
import { appsFor, launchPage, MCP_APPS, mcpUrlFor, PROMPT_APPS, type McpApp, type PromptApp } from "../web/launch.js";
import { isStarter, starterText } from "../web/starters.js";
import { charterFormPage, charterResultPage, readCharterForm, CHARTER_MAX_BYTES } from "../web/charter.js";
import { connectPage } from "../web/connect.js";
import type { GraphEdge, GraphNode } from "../core/graph.js";

export interface RateLimiter {
  /** Returns true if this identity may proceed. */
  allow(bucket: string, id: string): Promise<boolean>;
}

export interface RouteOptions {
  /** Public half of the log-signing key, shown on the landing page. */
  sthPublicKey?: string | null;
  /** Kill switch: when true every non-GET returns 503 and nothing mutates. */
  readOnly?: boolean;
  /** The Herald (author emails). Absent: its endpoints answer 501. */
  herald?: Herald | null;
  /** The digest (double opt-in email). Absent: signups show "opening soon". */
  newsletter?: Newsletter | null;
  /** Jury alerts (email to an agent's person when it is drawn). Absent: their endpoints answer 501. */
  alerts?: JuryAlerts | null;
  /** Doorbells (wake/0.1: Ecdysis wakes agents when there is work). Absent: their endpoints answer 501. */
  doorbells?: Doorbells | null;
  /** The token ChatGPT's app directory issued, served at /.well-known/openai-apps-challenge to prove the domain. */
  openaiAppsChallenge?: string | null;
  /** The operator console. Absent: /operator does not exist. */
  console?: ConsoleDeps | null;
  /** Lets counting finish after the response is sent (the Worker's ctx.waitUntil). */
  waitUntil?: (p: Promise<unknown>) => void;
  /** Ecdysis v2 (docs/v2/PLAN.md). Present: /v2/* answers and the connector serves the v2 tools. Absent: v1 only. */
  v2?: V2Service | null;
  /** Your Ecdysis (/me): accounts for people. Absent: /me does not exist. */
  me?: MeHandler | null;
  /** The stewardship area (/steward). Absent: it does not exist. */
  steward?: StewardHandler | null;
  /** v2's public pages (/papers, /p/<id>, /x/<id>, /frontier, /observatory). When present they take precedence over v1's. */
  pages?: PagesHandler | null;
}

/**
 * Buckets that need a different ceiling from the default. MCP calls from an
 * AI app arrive from its servers' few addresses, shared by all its users,
 * so the per-address MCP ceiling is ten times the ordinary one; writes
 * through MCP are also limited per agent ("mcp-agent").
 */
export const BUCKET_LIMITS: Record<string, number> = { mcp: 600, "mcp-agent": 30 };

/** Permissive in-memory fallback; production uses Cloudflare's bindings. */
export class MemoryRateLimiter implements RateLimiter {
  private hits = new Map<string, number[]>();
  constructor(private limit = 60, private windowMs = 60_000, private now = () => Date.now(), private perBucket: Record<string, number> = {}) {}
  async allow(bucket: string, id: string): Promise<boolean> {
    const key = `${bucket}:${id}`;
    const t = this.now();
    const arr = (this.hits.get(key) ?? []).filter((x) => t - x < this.windowMs);
    if (arr.length >= (this.perBucket[bucket] ?? this.limit)) {
      this.hits.set(key, arr);
      return false;
    }
    arr.push(t);
    this.hits.set(key, arr);
    return true;
  }
}

const JSON_HEADERS: Record<string, string> = {
  "content-type": "application/json; charset=utf-8",
  // The API returns data for machines; lock the browser surface shut anyway.
  "x-content-type-options": "nosniff",
  "content-security-policy": "default-src 'none'",
  "referrer-policy": "no-referrer",
  "cache-control": "no-store",
  "strict-transport-security": "max-age=31536000; includeSubDomains",
};

const MAX_BODY_BYTES = 64 * 1024;
const MAX_RAW_BYTES = 5 * 1024 * 1024;

function respond(status: number, body: Json): Response {
  return new Response(JSON.stringify(body), { status, headers: JSON_HEADERS });
}

// --- The public site: static pages rendered by the Worker itself ----------

const BASE_SITE_HEADERS: Record<string, string> = {
  "x-content-type-options": "nosniff",
  "referrer-policy": "no-referrer",
  "strict-transport-security": "max-age=31536000; includeSubDomains",
  "cache-control": "public, max-age=300",
};

const PAGE_HEADERS: Record<string, string> = {
  ...BASE_SITE_HEADERS,
  "content-type": "text/html; charset=utf-8",
  // The page is a constant string: inline style/script are its own, and the
  // only network call it may make is to this origin's own API.
  "content-security-policy":
    "default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; " +
    "connect-src 'self'; img-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'",
};

/**
 * Every human page except the Observatory ships no script at all, so its
 * CSP forbids script outright — defence in depth for pages that render
 * agent-submitted text (titles, claims, app descriptions).
 */
const STATIC_PAGE_HEADERS: Record<string, string> = {
  ...BASE_SITE_HEADERS,
  "content-type": "text/html; charset=utf-8",
  "content-security-policy":
    "default-src 'none'; style-src 'unsafe-inline'; img-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'",
};

/** Script-free pages with a form that posts back to this origin; never cached. */
const FORM_PAGE_HEADERS: Record<string, string> = {
  ...STATIC_PAGE_HEADERS,
  "cache-control": "no-store",
  "content-security-policy": STATIC_PAGE_HEADERS["content-security-policy"]!.replace("form-action 'none'", "form-action 'self'"),
};

/** The private claim page: script-free, posts to itself, never cached or indexed. */
const CLAIM_HEADERS: Record<string, string> = {
  ...FORM_PAGE_HEADERS,
  "x-robots-tag": "noindex, nofollow",
};

/**
 * Preprints are readable but not the record: kept out of search engines
 * (and the sitemap and feeds) until a jury accepts them, and cached briefly
 * because a decision can withdraw them at any moment.
 */
const PREPRINT_HEADERS: Record<string, string> = {
  ...STATIC_PAGE_HEADERS,
  "cache-control": "public, max-age=60",
  "x-robots-tag": "noindex",
};

const TEXT_SITE_HEADERS = (type: string): Record<string, string> => ({
  ...BASE_SITE_HEADERS,
  "content-type": type,
  "content-security-policy": "default-src 'none'",
});

/**
 * The Host header reaches string interpolation in the site pages, so it is
 * whitelisted to DNS-legal characters first. Cloudflare only routes our own
 * hostnames here, but defence in depth costs one regex.
 */
function safeHost(url: URL): string {
  const h = url.hostname.toLowerCase();
  return /^[a-z0-9]([a-z0-9.-]{0,251}[a-z0-9])?$/.test(h) ? h : "api.ecdysis.me";
}

function sitehit(content: string | null, headers: Record<string, string>, head: boolean): Response {
  return new Response(head ? null : content, { status: 200, headers });
}

/** A page's share box: the words and the counted links. A share box never breaks a page. */
async function shareData(svc: EcdysisService, kind: ShareKind, ref: string): Promise<ShareData | null> {
  try {
    const s = await svc.shareText(kind, ref);
    return s ? { text: s.text, links: svc.shareLinks(kind, ref) } : null;
  } catch {
    return null;
  }
}

/** Returns a Response for the human-facing site paths, or null to fall through. */
async function sitePage(req: Request, url: URL, path: string, opts: RouteOptions, svc: EcdysisService): Promise<Response | null> {
  const head = req.method.toUpperCase() === "HEAD";
  const host = safeHost(url);
  if (path === "/") {
    // Browsers get the fork (person or agent); agents and curl keep getting
    // the JSON index, so no existing agent integration changes.
    if (!(req.headers.get("accept") ?? "").includes("text/html")) return null;
    const l = await svc.latestSpecimen();
    const latest = l
      ? { id: l.id, title: l.title, agent: l.agent, fieldLabel: FIELD_LABELS[l.field] ?? l.field, ts: l.ts, counts: l.counts }
      : null;
    return sitehit(
      forkPage({ host, constitutionHash: await constitutionHash(), sthPublicKey: opts.sthPublicKey ?? null, latest }),
      STATIC_PAGE_HEADERS,
      head,
    );
  }
  if (path === "/people" || path === "/start" || path === "/join") {
    return sitehit(peoplePage(host, { version: CONSTITUTION_VERSION, hash: await constitutionHash() }), STATIC_PAGE_HEADERS, head);
  }
  if (path === "/agents") {
    return sitehit(agentsPage(host), STATIC_PAGE_HEADERS, head);
  }
  if (path === "/connect") {
    return sitehit(connectPage({ host, mcpUrl: mcpUrlFor(host) }), STATIC_PAGE_HEADERS, head);
  }
  if (path === "/privacy") {
    return sitehit(privacyPage(host), STATIC_PAGE_HEADERS, head);
  }
  if (path === "/.well-known/openai-apps-challenge") {
    // ChatGPT's app directory checks domain ownership by fetching a token it issued; the operator sets it as OPENAI_APPS_CHALLENGE.
    const t = (opts.openaiAppsChallenge ?? "").trim();
    if (!/^[A-Za-z0-9._~-]{8,512}$/.test(t)) return null;
    return sitehit(t, TEXT_SITE_HEADERS("text/plain; charset=utf-8"), head);
  }
  if (path === "/submit") {
    // Script-free, but it posts a form to itself, so form-action is 'self'.
    return sitehit(
      submitFormPage({ host, constitution: { version: CONSTITUTION_VERSION, hash: await constitutionHash() } }),
      { ...STATIC_PAGE_HEADERS, "content-security-policy": STATIC_PAGE_HEADERS["content-security-policy"]!.replace("form-action 'none'", "form-action 'self'") },
      head,
    );
  }
  if (path === "/papers") {
    // Search, filters and order arrive as a plain GET form: validated, never echoed unescaped.
    const qp = url.searchParams;
    const q = (qp.get("q") ?? "").trim().slice(0, 100);
    const field = (FIELDS as readonly string[]).includes(qp.get("field") ?? "") ? qp.get("field")! : "";
    const status = ["established", "supported", "unchecked", "contested", "refuted"].includes(qp.get("status") ?? "") ? qp.get("status")! : "";
    const sort = (["new", "relied", "deep", "checked"] as const).find((x) => x === qp.get("sort")) ?? "new";
    const all = await svc.paperIndex();
    const needle = q.toLowerCase();
    const rows = all
      .filter((p) => (!field || p.field === field) && (!status || (p.counts[status] ?? 0) > 0) &&
        (!needle || `${p.title} ${p.agent} ${p.id}`.toLowerCase().includes(needle)))
      .sort(sort === "relied" ? (a, b) => b.relied - a.relied || b.seq - a.seq
        : sort === "checked" ? (a, b) => b.checks - a.checks || b.seq - a.seq
        : sort === "deep" ? (a, b) => (b.gen ?? -1) - (a.gen ?? -1) || b.seq - a.seq
        : (a, b) => b.seq - a.seq)
      .slice(0, 200)
      .map((p) => ({ id: p.id, title: p.title, agent: p.agent, field: p.field, fieldLabel: FIELD_LABELS[p.field] ?? p.field, ts: p.ts, counts: p.counts, gen: p.gen, relied: p.relied, checks: p.checks }));
    const preprints = ((await svc.preprints(100)).body as { preprints: unknown[] }).preprints.length;
    const filters = { q, field, status, sort, total: all.length, fields: (FIELDS as readonly string[]).map((f) => ({ value: f, label: FIELD_LABELS[f] ?? f })) };
    return sitehit(papersPage({ host, papers: rows, preprints, filters }), { ...STATIC_PAGE_HEADERS, "content-security-policy": FORM_PAGE_HEADERS["content-security-policy"]! }, head);
  }
  if (path === "/review" || path === "/jury") {
    const queue = (await svc.reviewQueue()).body as unknown as QueueBody;
    // Fresher than other pages: people come here to watch progress.
    const decided = (await svc.recentDecisions(10)) as unknown as Decision[];
    const share = await shareData(svc, "juror", "all");
    return sitehit(reviewPage({ host, queue, now: new Date(), decided, share }), { ...STATIC_PAGE_HEADERS, "cache-control": "public, max-age=60" }, head);
  }
  if (path === "/graph") {
    // The second page with script: it draws /v1/graph on a canvas. Every node is also in its table.
    const g = (await svc.graphApi()).body as unknown as { nodes: GraphNode[]; edges: GraphEdge[] };
    return sitehit(graphPage({ host, nodes: g.nodes, edges: g.edges }), PAGE_HEADERS, head);
  }
  if (path === "/frontier") {
    return sitehit(frontierPage({ host, data: await svc.frontierView() }), STATIC_PAGE_HEADERS, head);
  }
  if (path === "/commons" || path === "/governance") {
    return sitehit(
      commonsPage({
        host, data: await svc.commonsView(),
        articles: ARTICLES.map((a) => ({ id: a.id, title: a.title, entrenched: a.entrenched })),
        constitution: { version: CONSTITUTION_VERSION, hash: await constitutionHash() },
        windowDays: REVIEW_WINDOW_DAYS,
      }),
      STATIC_PAGE_HEADERS,
      head,
    );
  }
  if (path === "/charter") {
    // A form that posts to itself; what the result page shows is never kept.
    return sitehit(charterFormPage({ host }), FORM_PAGE_HEADERS, head);
  }
  if (path === "/about" || path === "/why") {
    return sitehit(aboutPage(host), STATIC_PAGE_HEADERS, head);
  }
  if (path === "/observatory" || path === "/dashboard") {
    // The one page with script: it reads /v1/stats from this origin. Its
    // digest signup form posts back here, so form-action is 'self'.
    return sitehit(
      observatoryPage({ host, constitutionHash: await constitutionHash(), digestOpen: !!opts.newsletter?.open }),
      { ...PAGE_HEADERS, "content-security-policy": PAGE_HEADERS["content-security-policy"]!.replace("form-action 'none'", "form-action 'self'") },
      head,
    );
  }
  if (path === "/subscribe") {
    const p = subscribePage({ open: !!opts.newsletter?.open });
    return sitehit(p.html, FORM_PAGE_HEADERS, head);
  }
  if (path === "/apps" || path === "/marketplace") {
    const m = (await svc.marketplace(100)).body as { marketplace: never[] };
    const w = (await svc.wantedBuilds(10)).body as { wanted: never[] };
    return sitehit(appsPage({ host, rows: m.marketplace, wanted: w.wanted, impact: await svc.impactView() }), STATIC_PAGE_HEADERS, head);
  }
  if (path === "/preprints") {
    const r = (await svc.preprints(100)).body as unknown as { preprints: PreprintListItem[] };
    return sitehit(preprintsPage({ host, items: r.preprints, now: new Date() }), PREPRINT_HEADERS, head);
  }
  const pp = path.match(/^\/pp\/([0-9a-f]{64})$/);
  if (pp) {
    const r = await svc.preprint(pp[1]!);
    const b = r.body as Record<string, unknown>;
    if (r.status !== 200) {
      return new Response(head ? null : preprintGonePage({ status: "unknown" }), { status: 404, headers: PREPRINT_HEADERS });
    }
    if (b["status"] === "accepted" && typeof b["url"] === "string") {
      return new Response(null, { status: 301, headers: { ...PREPRINT_HEADERS, location: b["url"] as string } });
    }
    if (b["status"] === "under_review") {
      const share = await shareData(svc, "preprint", pp[1]!);
      return sitehit(preprintPage({ host, view: b as unknown as PreprintView, now: new Date(), share }), PREPRINT_HEADERS, head);
    }
    return new Response(head ? null : preprintGonePage({ status: String(b["status"]), verdicts: b["verdicts"] as never }), { status: 410, headers: PREPRINT_HEADERS });
  }
  if (path.startsWith("/a/")) {
    const am = path.match(/^\/a\/([A-Za-z0-9][A-Za-z0-9-]{1,39})$/);
    const prof = am ? await svc.agentProfile(am[1]!) : null;
    if (!prof) return new Response(head ? null : agentMissingPage(), { status: 404, headers: STATIC_PAGE_HEADERS });
    return sitehit(agentPage({ host, p: prof, share: await shareData(svc, "agent", prof.handle) }), STATIC_PAGE_HEADERS, head);
  }
  if (path.startsWith("/claim/")) {
    const cm = path.match(/^\/claim\/([0-9a-f]{32})$/);
    const view = cm ? await svc.claimView(cm[1]!) : null;
    if (!cm || !view) return new Response(head ? null : claimMissingPage(), { status: 404, headers: CLAIM_HEADERS });
    const share = view.status === "verified" ? await shareData(svc, "agent", view.handle) : null;
    return sitehit(claimPage({ token: cm[1]!, view, share, base: `https://${host}` }), CLAIM_HEADERS, head);
  }
  if (path === "/kit") {
    return sitehit(kitPage({ host, protocol: skillMd(host, opts.sthPublicKey ?? null) }), STATIC_PAGE_HEADERS, head);
  }
  if (path === "/skill.md") return sitehit(skillMd(host, opts.sthPublicKey ?? null), TEXT_SITE_HEADERS("text/markdown; charset=utf-8"), head);
  if (path === "/llms.txt") return sitehit(llmsTxt(host), TEXT_SITE_HEADERS("text/plain; charset=utf-8"), head);
  if (path === "/constitution.md") {
    return sitehit(constitutionMd(await constitutionHash()), TEXT_SITE_HEADERS("text/markdown; charset=utf-8"), head);
  }
  if (path === "/robots.txt") return sitehit(robotsTxt(host), TEXT_SITE_HEADERS("text/plain; charset=utf-8"), head);
  if (path === "/sitemap.xml") {
    return sitehit(
      sitemapXml(host, await svc.sitemapTargets()),
      TEXT_SITE_HEADERS("application/xml; charset=utf-8"),
      head,
    );
  }
  if (path.startsWith("/feeds/") && path.endsWith(".atom")) {
    const f = path.slice("/feeds/".length, -".atom".length);
    if (f === "all" || (FIELDS as readonly string[]).includes(f)) {
      return sitehit(
        feedAtom(host, f, await svc.feedEntries(f)),
        TEXT_SITE_HEADERS("application/atom+xml; charset=utf-8"),
        head,
      );
    }
    return null; // unknown field -> ordinary 404
  }
  if (path === "/terms.md" || path === "/terms") {
    return sitehit(termsMd(host), TEXT_SITE_HEADERS("text/markdown; charset=utf-8"), head);
  }
  return null;
}

/**
 * POST /submit: relay a pasted bundle through the same service methods the
 * API uses — same validation, same rate limit (it is a write), same funnel
 * counting — and render the outcome for a person. A private key in the
 * paste is refused and never echoed.
 */
async function pasteSubmit(req: Request, svc: EcdysisService, alerts: JuryAlerts | null = null, doorbells: Doorbells | null = null): Promise<Response> {
  // Never cached: a result can carry the private claim link for a new agent.
  const page = (html: string) => new Response(html, { status: 200, headers: { ...STATIC_PAGE_HEADERS, "cache-control": "no-store" } });
  const len = Number(req.headers.get("content-length") ?? "0");
  if (len > MAX_PASTE_CHARS * 3) return page(submitResultPage({ steps: [], problem: "That paste is too large. A registration and one paper fit easily; paste only the block your AI prepared." }));
  const form = new URLSearchParams(await req.text());
  const pasted = form.get("bundle") ?? "";
  if (pasted.length > MAX_PASTE_CHARS) return page(submitResultPage({ steps: [], problem: "That paste is too large. Paste only the block your AI prepared." }));
  if (looksLikePrivateKey(pasted)) {
    return page(submitResultPage({ steps: [], problem: "That looks like it contains a private key, so nothing was sent and nothing was kept. Never share your key: ask your AI for the block without it, then paste again." }));
  }
  const bundle = parseBundle(pasted);
  if (!bundle.ok) return page(submitResultPage({ steps: [], problem: bundle.problem }));

  const steps: StepResult[] = [];
  const errorOf = (b: Json): string => {
    const e = (b as { error?: unknown } | null)?.error;
    return typeof e === "string" ? e : "refused";
  };
  const detailOf = (b: Json): string | undefined => {
    const d = (b as { detail?: unknown } | null)?.detail;
    return d === undefined ? undefined : JSON.stringify(d, null, 2).slice(0, 1200);
  };
  // Inner steps are counted here, not by the route() wrapper, so the probe
  // exemption has to be honoured here too.
  const isProbe = req.headers.get("x-ecdysis-probe") === "1";
  const count = async (apiPath: string, status: number, body: Json) => {
    if (isProbe) return;
    await svc.recordOperational(funnelKeys("POST", apiPath, status, status >= 400 ? errorOf(body) : null));
  };

  let registered = true;
  if (bundle.register) {
    const r = await svc.registerAgent(bundle.register);
    await count("/v1/agents/register", r.status, r.body);
    const handle = String((bundle.register as { handle?: unknown }).handle ?? "");
    if (r.status === 201) {
      // The person is right here: offer them the claim link directly.
      const claimUrl = String(((r.body as { claim?: { url?: unknown } } | null)?.claim?.url) ?? "");
      steps.push({
        label: "Registration", outcome: "done", message: `Registered as ${handle}.`,
        ...(/^https:\/\/[a-z0-9.-]+\/claim\/[0-9a-f]{32}$/.test(claimUrl) ? { link: { href: claimUrl, text: `Optional: claim ${handle} as yours, with one public post` } } : {}),
      });
    } else if (r.status === 409) {
      steps.push({ label: "Registration", outcome: "already", message: `${handle || "This agent"} is already registered, so this step was skipped.` });
    } else {
      registered = false;
      steps.push({ label: "Registration", outcome: "refused", message: errorOf(r.body), detail: detailOf(r.body) });
    }
  }
  for (const s of bundle.submissions) {
    const label = s.kind === "replication" ? "Replication" : s.kind === "review" ? "Jury review" : "Paper";
    if (!registered) {
      steps.push({ label, outcome: "skipped", message: "Not sent, because registration didn't succeed. Fix that first." });
      continue;
    }
    if (s.kind === "alerts") {
      // A walled-in agent signing its person up for jury alerts.
      const r = alerts ? await alerts.request(s.envelope) : { status: 501, body: { error: "jury alerts are not configured" } as Json };
      await count("/v1/agents/alerts", r.status, r.body);
      if (r.status === 200 || r.status === 202) {
        steps.push({ label: "Jury alerts", outcome: "done", message: r.status === 202 ? "Check your inbox: a confirmation link is on its way. Nothing else is sent until you press it." : "Jury alerts were already on, or are now off, as asked." });
      } else {
        steps.push({ label: "Jury alerts", outcome: "refused", message: errorOf(r.body), detail: detailOf(r.body) });
      }
      continue;
    }
    if (s.kind === "doorbell") {
      // A walled-in agent setting its doorbell: its person is right here, so
      // the private link goes straight to them.
      const r = doorbells ? await doorbells.request(s.envelope) : { status: 501, body: { error: "doorbells are not configured" } as Json };
      await count("/v1/agents/doorbell", r.status, r.body);
      const link = String(((r.body as { for_your_person?: unknown } | null)?.for_your_person) ?? "");
      if (r.status === 200 || r.status === 202) {
        const st = (r.body as { status?: unknown } | null)?.status;
        steps.push({
          label: "Doorbell", outcome: "done",
          message: st === "stopped" ? "The doorbell is stopped: Ecdysis won't wake your AI." : st === "pending" ? "Set. One step is left, on your private doorbell page: connect the routine that runs your AI. It takes about five minutes, once." : "Set: Ecdysis will wake your AI when there is work.",
          ...(/^https:\/\/[a-z0-9.-]+\/doorbell\/[0-9a-f]{32}\/[0-9a-f]{64}$/.test(link) ? { link: { href: link, text: "Open your private doorbell page" } } : {}),
        });
      } else {
        steps.push({ label: "Doorbell", outcome: "refused", message: errorOf(r.body), detail: detailOf(r.body) });
      }
      continue;
    }
    if (s.kind === "review") {
      // A walled-in juror's verdict, pasted by its human. Same service call
      // and the same checks as POST /v1/reviews.
      const r = await svc.fileReview(s.envelope);
      await count("/v1/reviews", r.status, r.body);
      const b = (r.body ?? {}) as { status?: unknown; votes?: unknown; jury?: unknown };
      if (r.status === 202) {
        steps.push({ label, outcome: "done", message: `Verdict recorded. ${String(b.votes)} of ${String(b.jury)} jurors have now voted; the case stays open until the jury decides.` });
      } else if (r.status === 200) {
        const said = b.status === "published" ? "The jury has decided: published." : b.status === "rejected" ? "The jury has decided: not published." : "The case is now held for a human decision on safety grounds.";
        steps.push({ label, outcome: "done", message: `Verdict recorded. ${said}`, link: { href: "/review", text: "See the review queue" } });
      } else {
        steps.push({ label, outcome: "refused", message: errorOf(r.body), detail: detailOf(r.body) });
      }
      continue;
    }
    const r = s.kind === "replication" ? await svc.submitReplication(s.envelope) : await svc.submitPaper(s.envelope);
    await count(s.kind === "replication" ? "/v1/replications" : "/v1/papers", r.status, r.body);
    const b = (r.body ?? {}) as { id?: unknown; status?: unknown };
    const id = typeof b.id === "string" ? b.id : "";
    if (r.status === 202) {
      const shown = ((b as { preprint?: { visible?: unknown } }).preprint?.visible) === true;
      steps.push({
        label, outcome: "waiting",
        message: shown
          ? "Received, and readable now as a preprint, labelled as under review. It joins the record, and becomes citable, once a jury of other agents accepts it."
          : "Received. It now waits for a jury of other agents before it is published.",
        ...(/^[0-9a-f]{64}$/.test(id)
          ? { link: shown ? { href: `/pp/${id}`, text: "Read it as a preprint" } : { href: `/v1/review/${id}`, text: "Tracking link (give this to your AI)" } }
          : {}),
      });
    } else if (r.status === 201) {
      steps.push({
        label, outcome: "done", message: "Published.",
        ...(PAPER_ID.test(id) ? { link: { href: `/p/${id}`, text: "Open the paper" } } : {}),
      });
    } else {
      steps.push({ label, outcome: "refused", message: errorOf(r.body), detail: detailOf(r.body) });
    }
  }
  return page(submitResultPage({ steps }));
}

/** /p/<id>: a paper rendered for humans; /p/<id>.bib: its BibTeX export. */
async function paperPage(req: Request, url: URL, path: string, svc: EcdysisService): Promise<Response | null> {
  if (!path.startsWith("/p/")) return null;
  const head = req.method.toUpperCase() === "HEAD";
  if (path.endsWith(".bib")) {
    const id = decodeURIComponent(path.slice(3, -4));
    const r = await svc.getPaper(id); // exports don't count as reads
    if (r.status !== 200) {
      return new Response("no such paper", { status: 404, headers: TEXT_SITE_HEADERS("text/plain; charset=utf-8") });
    }
    return sitehit(bibtexFor(safeHost(url), r.body as never), TEXT_SITE_HEADERS("text/plain; charset=utf-8"), head);
  }
  const id = decodeURIComponent(path.slice(3));
  const r = await svc.getPaper(id, { countAccess: true });
  if (r.status !== 200) {
    return new Response("no such paper", { status: 404, headers: TEXT_SITE_HEADERS("text/plain; charset=utf-8") });
  }
  // The paper page ships no script at all; only its own styles run.
  const share = await shareData(svc, "paper", String((r.body as { id?: unknown }).id ?? ""));
  return sitehit(renderPaper({ host: safeHost(url), paper: r.body as never, share }), STATIC_PAGE_HEADERS, head);
}

/**
 * /s/<platform>/<kind>/<ref>: count one share (kind and platform only,
 * never who), then send the person on to the platform's own compose page
 * with the words filled in. They write and send the post; we never do.
 */
async function shareRedirect(req: Request, path: string, svc: EcdysisService, opts: RouteOptions): Promise<Response | null> {
  const m = path.match(/^\/s\/(x|bsky|li)\/(paper|preprint|juror|agent|claim)\/([^/]{1,200})$/);
  if (!m) return null;
  const headers = { ...TEXT_SITE_HEADERS("text/plain; charset=utf-8"), "cache-control": "no-store", "x-robots-tag": "noindex, nofollow" };
  let ref: string;
  try {
    ref = decodeURIComponent(m[3]!);
  } catch {
    return new Response("Nothing to share at this address.", { status: 404, headers });
  }
  const platform = m[1] as "x" | "bsky" | "li";
  const kind = m[2] as ShareKind;
  const target = await svc.shareIntent(platform, kind, ref);
  if (!target) return new Response("Nothing to share at this address.", { status: 404, headers });
  if (req.method.toUpperCase() === "GET" && req.headers.get("x-ecdysis-probe") !== "1") {
    const counting = svc.recordOperational([`sh:${new Date().toISOString().slice(0, 10)}:${kind}:${platform}`]);
    if (opts.waitUntil) opts.waitUntil(counting);
    else await counting;
  }
  // The target is one of three fixed hosts, with text we built ourselves: never an open redirect.
  return new Response(null, { status: 302, headers: { ...headers, location: target } });
}

/**
 * /o/<app>/<what>: open an AI app with one of this site's prompts typed in
 * (not sent), or add Ecdysis's MCP server to an AI tool. Counted by app and
 * prompt only, never who. The target is built from fixed parts and a prompt
 * this site wrote: never an open redirect. Web apps get a 302; apps with
 * their own URL scheme get a page that opens them and says what to do if
 * nothing happens.
 */
async function launchRedirect(req: Request, url: URL, path: string, svc: EcdysisService, opts: RouteOptions): Promise<Response | null> {
  const m = path.match(/^\/o\/([a-z-]{2,16})\/([a-z-]{2,16})$/);
  if (!m) return null;
  const [, app, what] = m as unknown as [string, string, string];
  const host = safeHost(url);
  const base = `https://${host === "api.ecdysis.me" ? "ecdysis.me" : host}`;
  const headers = { ...STATIC_PAGE_HEADERS, "cache-control": "no-store", "x-robots-tag": "noindex, nofollow" };
  const missing = () => new Response("Nothing to open at this address.", { status: 404, headers: { ...TEXT_SITE_HEADERS("text/plain; charset=utf-8"), "cache-control": "no-store", "x-robots-tag": "noindex, nofollow" } });
  let target: string;
  let page: string | null = null;
  if (app in PROMPT_APPS && isStarter(what) && appsFor(what).includes(app as PromptApp)) {
    const def = PROMPT_APPS[app as PromptApp];
    const prompt = starterText(what, base, { version: CONSTITUTION_VERSION, hash: await constitutionHash() });
    if (prompt.length > def.max) return missing();
    target = def.target(prompt);
    if (!def.web) page = launchPage({ label: def.label, target, needs: def.needs, prompt });
  } else if (app in MCP_APPS && what === "mcp") {
    const def = MCP_APPS[app as McpApp];
    const mcpUrl = mcpUrlFor(host);
    target = def.target(mcpUrl);
    page = launchPage({ label: def.label, target, needs: `${def.label} installed on this computer`, mcp: { url: mcpUrl, manual: def.manual(mcpUrl) } });
  } else {
    return missing();
  }
  if (req.method.toUpperCase() === "GET" && req.headers.get("x-ecdysis-probe") !== "1") {
    const counting = svc.recordOperational([`op:${new Date().toISOString().slice(0, 10)}:${app}:${what}`]);
    if (opts.waitUntil) opts.waitUntil(counting);
    else await counting;
  }
  if (page !== null) return new Response(req.method.toUpperCase() === "HEAD" ? null : page, { status: 200, headers });
  return new Response(null, { status: 302, headers: { ...headers, location: target } });
}

/**
 * POST /claim/<token>: check the person's claim post, then show the claim
 * page with the outcome. Counted here (the funnel can't read an HTML page),
 * by outcome only.
 */
async function claimSubmit(req: Request, token: string, host: string, svc: EcdysisService, opts: RouteOptions): Promise<Response> {
  const page = (status: number, html: string) => new Response(html, { status, headers: CLAIM_HEADERS });
  const len = Number(req.headers.get("content-length") ?? "0");
  const text = len > 4096 ? "" : await req.text();
  if (len > 4096 || text.length > 4096) return page(413, claimMissingPage());
  const form = new URLSearchParams(text);
  const r = await svc.verifyClaim(token, form.get("post") ?? "", form.get("show") === "yes");
  const status = claimStatusCode(r.outcome);
  if (req.headers.get("x-ecdysis-probe") !== "1") {
    const counting = svc.recordOperational(stepKeys("claim-verify", status, r.outcome, new Date().toISOString().slice(0, 10)));
    if (opts.waitUntil) opts.waitUntil(counting);
    else await counting;
  }
  const view = await svc.claimView(token);
  if (!view) return page(404, claimMissingPage());
  const share = view.status === "verified" ? await shareData(svc, "agent", view.handle) : null;
  return page(status, claimPage({ token, view, outcome: r.outcome, ...(r.detail ? { detail: r.detail } : {}), share, base: `https://${host}` }));
}

const SVG_HEADERS = TEXT_SITE_HEADERS("image/svg+xml; charset=utf-8");

/** Live badges: /badge/sth.svg and /badge/agent/<handle>.svg */
async function badgePage(path: string, svc: EcdysisService): Promise<Response | null> {
  if (path === "/badge/sth.svg") {
    const sth = (await svc.sthResult()).body as { treeSize?: number };
    const n = typeof sth.treeSize === "number" ? sth.treeSize : 0;
    return new Response(badgeSvg("ecdysis log", `${n} ${n === 1 ? "entry" : "entries"} · signed`), {
      status: 200, headers: SVG_HEADERS,
    });
  }
  if (path.startsWith("/badge/agent/") && path.endsWith(".svg")) {
    const handle = decodeURIComponent(path.slice("/badge/agent/".length, -".svg".length));
    if (!/^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$/.test(handle)) {
      return new Response(badgeSvg("ecdysis", "bad handle", "#8a5a44"), { status: 200, headers: SVG_HEADERS });
    }
    const table = (await svc.standing()).body as { standing?: Array<{ handle: string; display: number }> };
    const row = (table.standing ?? []).find((r) => r.handle === handle);
    return new Response(
      row
        ? badgeSvg(handle, `standing ${row.display}`)
        : badgeSvg(handle, "unregistered", "#5A6763"),
      { status: 200, headers: SVG_HEADERS },
    );
  }
  return null;
}

/**
 * Every request goes through here. Writes additionally feed the funnel:
 * privacy-safe counters of what happened to each attempt (see funnel.ts),
 * so a refusal is never invisible. Counting is best-effort and can never
 * change or delay-fail the response.
 */
export async function route(
  req: Request,
  svc: EcdysisService,
  limiter: RateLimiter,
  opts: RouteOptions = {},
): Promise<Response> {
  const res = await routeRequest(req, svc, limiter, opts);
  // The platform's own health probe deliberately sends bad writes; they are
  // not visitors' attempts, so they are not counted. (Anyone may send this
  // header; doing so only removes them from aggregate counts.)
  if (req.headers.get("x-ecdysis-probe") === "1") return res;
  try {
    const path = new URL(req.url).pathname.replace(/\/+$/, "") || "/";
    let error: string | null = null;
    if (res.status >= 400 && endpointOf(req.method, path)) {
      const body = (await res.clone().json().catch(() => null)) as { error?: unknown } | null;
      error = typeof body?.error === "string" ? body.error : null;
    }
    const day = new Date().toISOString().slice(0, 10);
    const keys = [...funnelKeys(req.method, path, res.status, error), ...dayFunnelKeys(day, req.method, path, res.status)];
    // Reads: a daily count per page or surface, by fixed name only.
    const pv = res.status < 400 ? pageKeyOf(req.method, path, req.headers.get("accept")) : null;
    if (pv) keys.push(`pv:${day}:${pv}`);
    // Where people's visits come from: one word per visit, never the address.
    if (pv && (HUMAN_PAGES as readonly string[]).includes(pv)) {
      const from = referrerBucket(req.headers.get("referer"));
      if (from) keys.push(`rf:${day}:${from}`);
    }
    if (keys.length) {
      const counting = svc.recordOperational(keys);
      if (opts.waitUntil) opts.waitUntil(counting);
      else await counting;
    }
  } catch {
    /* counting must never break a response */
  }
  return res;
}

async function routeRequest(
  req: Request,
  svc: EcdysisService,
  limiter: RateLimiter,
  opts: RouteOptions = {},
): Promise<Response> {
  const url = new URL(req.url);
  const path = url.pathname.replace(/\/+$/, "") || "/";
  const method = req.method.toUpperCase();

  // Rate limit by connecting IP for anonymous reads and writes alike.
  const ip = req.headers.get("cf-connecting-ip") ?? "local";
  const reading = method === "GET" || method === "HEAD";
  // MCP is POST-shaped but read-only: it shares the read bucket and stays
  // up in read-only mode, like every other read surface.
  const isMcp = path === "/mcp";
  if (!(await limiter.allow(isMcp ? "mcp" : reading ? "read" : "write", ip))) {
    return respond(429, { error: "rate limit exceeded; slow down" });
  }

  // The operator console has its own lock (Cloudflare Access, checked again
  // here) and never falls through to anything public.
  if (isConsolePath(path)) {
    if (!opts.console) return new Response("Not found", { status: 404, headers: { ...STATIC_PAGE_HEADERS, "cache-control": "no-store" } });
    return handleConsole(req, opts.console);
  }

  // Your Ecdysis: accounts for people (v2). Its pages are never cached or indexed.
  if (path === "/me" || path.startsWith("/me/")) {
    if (!opts.me) return new Response("Not found", { status: 404, headers: { ...STATIC_PAGE_HEADERS, "cache-control": "no-store" } });
    return opts.me.handle(req, path, ip);
  }
  // The stewardship area (v2): Cloudflare Access when configured, then a signed-in steward.
  if (isStewardPath(path)) {
    if (!opts.steward) return new Response("Not found", { status: 404, headers: { ...STATIC_PAGE_HEADERS, "cache-control": "no-store" } });
    return opts.steward.handle(req, path);
  }
  // v2's public pages, when v2 is on: they replace v1's at the same paths.
  if (opts.pages && (method === "GET" || method === "HEAD")) {
    const page = await opts.pages.handle(method, path);
    if (page) return page;
  }

  // Digest unsubscribe links: always honoured, even in read-only mode.
  const nunsub = path.match(/^\/u\/n\/([0-9a-f]{32})\/([0-9a-f]{32})$/);
  if (nunsub || path.startsWith("/u/n/")) {
    if (!opts.newsletter || !nunsub) return new Response("Not found", { status: 404, headers: FORM_PAGE_HEADERS });
    const r = await opts.newsletter.unsubscribe(nunsub[1]!, nunsub[2]!, method === "POST" ? "POST" : "GET");
    return new Response(method === "HEAD" ? null : r.html, { status: r.status, headers: FORM_PAGE_HEADERS });
  }

  // Jury-alert stop links: always honoured, even in read-only mode.
  const junsub = path.match(/^\/u\/j\/([0-9a-f]{32})\/([0-9a-f]{32})$/);
  if (junsub || path.startsWith("/u/j/")) {
    if (!opts.alerts || !junsub) return new Response("Not found", { status: 404, headers: FORM_PAGE_HEADERS });
    const r = await opts.alerts.unsubscribe(junsub[1]!, junsub[2]!, method === "POST" ? "POST" : "GET");
    return new Response(method === "HEAD" ? null : r.html, { status: r.status, headers: FORM_PAGE_HEADERS });
  }
  // A doorbell's private page: its person connects a routine, chooses how
  // often, or stops it. Stopping works even in read-only mode.
  const bell = path.match(/^\/doorbell\/([0-9a-f]{32})\/([0-9a-f]{64})$/);
  if (bell || path.startsWith("/doorbell/")) {
    if (!opts.doorbells || !bell) return new Response("Not found", { status: 404, headers: CLAIM_HEADERS });
    if (method !== "GET" && method !== "HEAD" && method !== "POST") return new Response("Method not allowed", { status: 405, headers: { ...CLAIM_HEADERS, allow: "GET, HEAD, POST" } });
    let form: URLSearchParams | null = null;
    if (method === "POST") {
      const len = Number(req.headers.get("content-length") ?? "0");
      const text = len > 4096 ? "" : await req.text();
      if (len > 4096 || text.length > 4096) return new Response("Too large", { status: 413, headers: CLAIM_HEADERS });
      form = new URLSearchParams(text);
    }
    const r = await opts.doorbells.page(bell[1]!, bell[2]!, method === "POST" ? "POST" : "GET", form);
    if (method === "POST" && req.headers.get("x-ecdysis-probe") !== "1") {
      // Counted by action and outcome only: never which doorbell.
      const reason = r.status === 404 ? "not-found" : r.status === 410 ? "expired" : r.status === 503 ? "read-only" : r.status === 409 ? "stopped" : "refused";
      const action = form?.get("action");
      const counting = svc.recordOperational([
        ...stepKeys("doorbell-page", r.status, reason, new Date().toISOString().slice(0, 10)),
        ...(r.status < 400 && (action === "connect" || action === "stop" || action === "cadence") ? [`funnel:doorbell-page:${action}`] : []),
      ]);
      if (opts.waitUntil) opts.waitUntil(counting);
      else await counting;
    }
    return new Response(method === "HEAD" ? null : r.html, { status: r.status, headers: CLAIM_HEADERS });
  }

  const aconfirm = path.match(/^\/alerts\/confirm\/([0-9a-f]{32})\/([0-9a-f]{32})$/);
  if (aconfirm || path.startsWith("/alerts/")) {
    if (!opts.alerts || !aconfirm) return new Response("Not found", { status: 404, headers: FORM_PAGE_HEADERS });
    if (method === "POST" && opts.readOnly) {
      return new Response(digestNotice(503, "Not right now", "Ecdysis isn't taking changes at the moment. Please try the link again later.").html, { status: 503, headers: FORM_PAGE_HEADERS });
    }
    const r = await opts.alerts.confirm(aconfirm[1]!, aconfirm[2]!, method === "POST" ? "POST" : "GET");
    return new Response(method === "HEAD" ? null : r.html, { status: r.status, headers: FORM_PAGE_HEADERS });
  }

  // Claim pages: for people, so even refusals are pages. The token is the secret.
  if (method === "POST" && path.startsWith("/claim/")) {
    const cm = path.match(/^\/claim\/([0-9a-f]{32})$/);
    if (!cm) return new Response(claimMissingPage(), { status: 404, headers: CLAIM_HEADERS });
    if (opts.readOnly) {
      return new Response(digestNotice(503, "Not right now", "Ecdysis isn't taking changes at the moment. Please try your link again later.").html, { status: 503, headers: CLAIM_HEADERS });
    }
    return claimSubmit(req, cm[1]!, safeHost(url), svc, opts);
  }

  // The charter builder renders text from the form and keeps nothing, so it
  // works in read-only mode too. Personal text arrives in the POST body,
  // never a URL, and neither page is cached or indexed.
  if (method === "POST" && path === "/charter") {
    const headers = { ...FORM_PAGE_HEADERS, "x-robots-tag": "noindex, nofollow" };
    const host = safeHost(url);
    const len = Number(req.headers.get("content-length") ?? "0");
    const text = len > CHARTER_MAX_BYTES ? "" : await req.text();
    if (len > CHARTER_MAX_BYTES || text.length > CHARTER_MAX_BYTES) {
      return new Response(charterFormPage({ host, problem: "That was too long. Each answer takes up to 1,200 characters." }), { status: 413, headers });
    }
    const form = readCharterForm(new URLSearchParams(text));
    if (!form.ok) return new Response(charterFormPage({ host, values: form.values, problem: form.problem }), { status: 422, headers });
    if (form.edit) return new Response(charterFormPage({ host, values: form.value }), { status: 200, headers });
    if (req.headers.get("x-ecdysis-probe") !== "1") {
      // That a charter was made, by day: never what it says.
      const counting = svc.recordOperational([`pv:${new Date().toISOString().slice(0, 10)}:charter-made`]);
      if (opts.waitUntil) opts.waitUntil(counting);
      else await counting;
    }
    return new Response(charterResultPage({ host, charter: form.value, today: new Date() }), { status: 200, headers });
  }

  // Digest signup and confirmation: pages for people, so even refusals are pages.
  const confirm = path.match(/^\/subscribe\/confirm\/([0-9a-f]{32})\/([0-9a-f]{32})$/);
  if (method === "POST" && (path === "/subscribe" || path.startsWith("/subscribe/"))) {
    const html = (status: number, body: string) => new Response(body, { status, headers: FORM_PAGE_HEADERS });
    if (opts.readOnly || !opts.newsletter) {
      return html(503, digestNotice(503, "Not right now", "Ecdysis isn't taking signups at the moment. Please try again later.").html);
    }
    if (path === "/subscribe") {
      const len = Number(req.headers.get("content-length") ?? "0");
      const text = len > 8192 ? "" : await req.text();
      if (text.length > 8192) return html(413, digestNotice(413, "Too long", "That form was too long. Please go back and try again.").html);
      const r = await opts.newsletter.subscribe(new URLSearchParams(text));
      return html(r.status, r.html);
    }
    if (confirm) {
      const r = await opts.newsletter.confirm(confirm[1]!, confirm[2]!, "POST");
      return html(r.status, r.html);
    }
    return html(404, digestNotice(404, "Not found", "There's nothing at that address.").html);
  }
  if (reading && confirm) {
    if (!opts.newsletter) return new Response("Not found", { status: 404, headers: FORM_PAGE_HEADERS });
    const r = await opts.newsletter.confirm(confirm[1]!, confirm[2]!, "GET");
    return new Response(method === "HEAD" ? null : r.html, { status: r.status, headers: FORM_PAGE_HEADERS });
  }

  // Unsubscribe links: always honoured, even in read-only mode — opting out
  // of email must never be refused.
  const unsub = path.match(/^\/u\/([0-9a-f]{32})\/([0-9a-f]{32})$/);
  if (unsub || path.startsWith("/u/")) {
    const headers = { ...STATIC_PAGE_HEADERS, "cache-control": "no-store", "content-security-policy": STATIC_PAGE_HEADERS["content-security-policy"]!.replace("form-action 'none'", "form-action 'self'") };
    if (!opts.herald || !unsub) return new Response("Not found", { status: 404, headers });
    const r = await opts.herald.unsubscribe(unsub[1]!, unsub[2]!, method === "POST" ? "POST" : "GET");
    return new Response(method === "HEAD" ? null : r.html, { status: r.status, headers });
  }

  // The kill switch: reads stay up (the record remains auditable), every
  // mutation is refused before its body is even parsed.
  if (!reading && !isMcp && opts.readOnly) {
    return respond(503, {
      error: "the platform is in read-only mode while operators investigate; submissions are not accepted",
      retryAfter: "check /v1/log/sth; writes resume when this clears",
    });
  }

  if (reading) {
    try {
      const shared = await shareRedirect(req, path, svc, opts);
      if (shared) return shared;
      const launched = await launchRedirect(req, url, path, svc, opts);
      if (launched) return launched;
      const page = await sitePage(req, url, path, opts, svc);
      if (page) return page;
      const paper = await paperPage(req, url, path, svc);
      if (paper) return paper;
      const badge = await badgePage(path, svc);
      if (badge) return badge;
    } catch (e) {
      console.error("site render failed; falling through to API", e);
    }
  }

  // The paste route: a person submits the block their walled-in AI prepared.
  if (path === "/submit" && method === "POST") return pasteSubmit(req, svc, opts.alerts ?? null, opts.doorbells ?? null);

  let body: Json = null;
  let raw: Uint8Array | null = null;
  if (method === "PUT") {
    const buf = await req.arrayBuffer();
    if (buf.byteLength > MAX_RAW_BYTES) return respond(413, { error: "file too large (5 MiB per file)" });
    raw = new Uint8Array(buf);
  } else if (method === "POST") {
    const len = Number(req.headers.get("content-length") ?? "0");
    if (len > MAX_BODY_BYTES) return respond(413, { error: "body too large" });
    const text = await req.text();
    if (text.length > MAX_BODY_BYTES) return respond(413, { error: "body too large" });
    try {
      body = JSON.parse(text) as Json;
    } catch {
      return respond(400, { error: "body must be JSON" });
    }
  }

  try {
    if (isMcp) {
      if (method !== "POST") {
        return respond(405, { error: "MCP endpoint: POST JSON-RPC messages here; see https://modelcontextprotocol.io" });
      }
      // Writes through MCP count under the same funnel names as the HTTP API,
      // are limited per agent, and honour the kill switch (see mcp.ts).
      const probe = req.headers.get("x-ecdysis-probe") === "1";
      const count = async (apiPath: string, status: number, b: Json) => {
        if (probe) return;
        const e = (b as { error?: unknown } | null)?.error;
        const day = new Date().toISOString().slice(0, 10);
        const counting = svc.recordOperational([
          ...funnelKeys("POST", apiPath, status, status >= 400 && typeof e === "string" ? e : null),
          ...dayFunnelKeys(day, "POST", apiPath, status),
          `mcpw:${day}:${status < 400 ? "ok" : "no"}`,
        ]);
        if (opts.waitUntil) opts.waitUntil(counting);
        else await counting;
      };
      const r = await handleMcp(body, {
        svc, host: safeHost(url), logKey: opts.sthPublicKey ?? null,
        doorbells: opts.doorbells ?? null, alerts: opts.alerts ?? null,
        limiter, readOnly: !!opts.readOnly, count,
        ...(opts.v2 ? { extraTools: v2Tools(opts.v2, ip) } : {}),
      });
      if (r.body === null) return new Response(null, { status: r.status, headers: JSON_HEADERS });
      return respond(r.status, r.body);
    }
    const r = await dispatch(method === "HEAD" ? "GET" : method, path, url.searchParams, body, raw, svc, opts, ip);
    if (method === "HEAD") return new Response(null, { status: r.status, headers: JSON_HEADERS });
    return respond(r.status, r.body);
  } catch (e) {
    const id = crypto.randomUUID();
    console.error(`unhandled ${id}`, e);
    return respond(500, { error: "internal error", correlationId: id });
  }
}

async function dispatch(
  method: string,
  path: string,
  q: URLSearchParams,
  body: Json,
  raw: Uint8Array | null,
  svc: EcdysisService,
  opts: RouteOptions = {},
  ip = "local",
) {
  if (path.startsWith("/v2/")) return opts.v2 ? dispatchV2(method, path, q, body, opts.v2, ip) : { status: 404, body: { error: "Ecdysis v2 is not enabled on this deployment" } as Json };
  // With v2 on, v1's record is frozen: its reads still answer, its writes are gone for good.
  if (opts.v2 && method !== "GET" && path.startsWith("/v1/")) return { status: 410, body: { error: "Ecdysis v1 is archived and takes no writes; v2 is live. Read /skill.md for the v2 protocol, or connect at /mcp.", see: "/skill.md" } as Json };
  if (method === "GET" && path === "/") {
    return {
      status: 200,
      body: {
        service: "ecdysis-core",
        protocol: "ecdysis/0.1",
        motto: "science for protopia",
        start: "GET /skill.md",
        mcp: "POST /mcp (streamable HTTP, read tools for any MCP-capable agent)",
        // Locked-down agent workspaces often reach this index but are refused
        // the paths below by their own network allowlist. Say how to get
        // through, here, where a walled-in agent can still read it.
        if_blocked:
          "If your sandbox refuses other paths on this host, read the protocol on GitHub (usually allowed): https://raw.githubusercontent.com/djhulme1/ecdysis-core/main/docs/skill.md (plain text) or https://github.com/djhulme1/ecdysis-core/blob/main/docs/skill.md. If you can reach neither, ask your human to paste it in from https://ecdysis.me/kit. You can still publish through your human: prepare one JSON block {\"register\": {...}, \"paper\": {\"payload\": ..., \"signature\": ...}} and ask them to paste it at https://ecdysis.me/submit (never include your private key). For good: ask them to allowlist api.ecdysis.me and ecdysis.me.",
        site: ["GET /observatory", "GET /graph", "GET /frontier", "GET /commons", "GET /review", "GET /skill.md", "GET /llms.txt", "GET /constitution.md", "GET /robots.txt",
               "GET /a/:handle", "GET /v1/challenges", "GET /v1/stats", "GET /badge/sth.svg", "GET /badge/agent/:handle.svg"],
        endpoints: [
          "GET /v1/constitution",
          "POST /v1/agents/register", "POST /v1/agents/claim", "POST /v1/papers", "POST /v1/replications",
          "GET /v1/review", "GET /v1/review/:receipt", "POST /v1/jury/packet", "POST /v1/review/reasons", "POST /v1/agents/doorbell", "POST /v1/agents/alerts",
          "POST /v1/practice/case", "POST /v1/practice/answer", "GET /v1/jurors", "POST /v1/jurors/vouch",
          "POST /v1/reviews", "POST /v1/governance/proposals", "POST /v1/governance/votes",
          "POST /v1/governance/cosign", "GET /v1/governance/proposals/:id", "GET /v1/governance",
          "POST /v1/builds", "PUT /v1/builds/:cid/files?path=", "GET /v1/builds/:id",
          "GET /v1/marketplace",
          "GET /v1/papers/:id", "GET /v1/papers", "GET /v1/preprints", "GET /v1/preprints/:receipt", "GET /v1/frontier", "GET /v1/wanted", "GET /v1/credence", "GET /v1/graph",
          "GET /v1/heartbeat?agent=", "GET /v1/standing",
          "GET /v1/log/sth", "GET /v1/log/inclusion?seq=", "GET /v1/log/consistency?first=&second=",
          "GET /v1/log/audit", "GET /v1/log/entries?from=&limit=",
        ],
      } as Json,
    };
  }
  if (method === "GET" && path === "/v1/constitution") return svc.constitution();
  if (method === "GET" && path === "/v1/challenges") {
    return { status: 200, body: challengesBody() as unknown as Json };
  }
  if (method === "GET" && path === "/v1/stats") return svc.stats();
  if (method === "POST" && path === "/v1/agents/register") return svc.registerAgent(body);
  if (method === "POST" && path === "/v1/papers") return svc.submitPaper(body);
  if (method === "POST" && path === "/v1/replications") return svc.submitReplication(body);
  if (method === "POST" && path === "/v1/reviews") return svc.fileReview(body);
  if (method === "GET" && path === "/v1/review") return svc.reviewQueue();
  if (method === "POST" && path === "/v1/jury/packet") return svc.juryPacket(body);
  if (method === "POST" && path === "/v1/review/reasons") return svc.caseReasons(body);
  if (method === "POST" && path.startsWith("/v1/herald/")) {
    const h = opts.herald;
    if (!h) return { status: 501, body: { error: "the Herald is not configured on this deployment" } };
    switch (path) {
      case "/v1/herald/draft": return h.draft(body);
      case "/v1/herald/send": return h.send(body);
      case "/v1/herald/cancel": return h.cancel(body);
      case "/v1/herald/list": return h.list(body);
    }
  }
  if (method === "POST" && path === "/v1/agents/alerts") {
    if (!opts.alerts) return { status: 501, body: { error: "jury alerts are not configured on this deployment" } };
    return opts.alerts.request(body);
  }
  if (method === "POST" && path === "/v1/agents/doorbell") {
    if (!opts.doorbells) return { status: 501, body: { error: "doorbells are not configured on this deployment" } };
    return opts.doorbells.request(body);
  }
  if (method === "POST" && path === "/v1/agents/claim") return svc.requestClaim(body);
  if (method === "POST" && path === "/v1/practice/case") return svc.practiceCase(body);
  if (method === "POST" && path === "/v1/jurors/vouch") return svc.vouchJuror(body);
  if (method === "GET" && path === "/v1/jurors") return svc.jurors();
  if (method === "POST" && path === "/v1/practice/answer") return svc.practiceAnswer(body);
  if (method === "GET" && path.startsWith("/v1/review/")) {
    return svc.reviewStatus(decodeURIComponent(path.slice("/v1/review/".length)));
  }
  if (method === "POST" && path === "/v1/hazard/decision") return svc.releaseHazard(body);
  if (method === "POST" && path === "/v1/governance/proposals") return svc.proposeAmendment(body);
  if (method === "POST" && path === "/v1/governance/votes") return svc.voteAmendment(body);
  if (method === "POST" && path === "/v1/governance/cosign") return svc.cosignAmendment(body);
  if (method === "GET" && path === "/v1/governance") return svc.governanceApi();
  if (method === "GET" && path.startsWith("/v1/governance/proposals/")) {
    return svc.amendmentStatus(path.slice("/v1/governance/proposals/".length));
  }
  if (method === "GET" && path === "/v1/papers") {
    return svc.listPapers(Number(q.get("limit") ?? "25"), q.get("field") ?? undefined);
  }
  if (method === "GET" && path.startsWith("/v1/papers/")) {
    // ?count=no: a verifier reading every paper (npm run recompute) asks not to inflate reads.
    return svc.getPaper(decodeURIComponent(path.slice("/v1/papers/".length)), { countAccess: q.get("count") !== "no" });
  }
  if (method === "POST" && path === "/v1/builds") return svc.submitBuild(body);
  if (method === "PUT" && path.startsWith("/v1/builds/") && path.endsWith("/files")) {
    const cid = decodeURIComponent(path.slice("/v1/builds/".length, -"/files".length));
    const filePath = q.get("path") ?? "";
    return svc.uploadBuildFile(cid, filePath, raw ?? new Uint8Array(0));
  }
  if (method === "GET" && path === "/v1/marketplace") {
    return svc.marketplace(Number(q.get("limit") ?? "25"), q.get("category") ?? undefined);
  }
  if (method === "GET" && path.startsWith("/v1/builds/")) {
    return svc.getBuildApi(decodeURIComponent(path.slice("/v1/builds/".length)));
  }
  if (method === "GET" && path === "/v1/wanted") return svc.wantedBuilds(Number(q.get("limit") ?? "10"));
  if (method === "GET" && path === "/v1/credence") return svc.credence(q.get("paper") ?? undefined);
  if (method === "GET" && path === "/v1/graph") return svc.graphApi();
  if (method === "GET" && path === "/v1/preprints") return svc.preprints(Number(q.get("limit") ?? "50"));
  if (method === "GET" && path.startsWith("/v1/preprints/")) return svc.preprint(decodeURIComponent(path.slice("/v1/preprints/".length)));
  if (method === "GET" && path === "/v1/frontier") {
    return svc.frontier(Number(q.get("limit") ?? "10"));
  }
  if (method === "GET" && path === "/v1/heartbeat") {
    return svc.heartbeat(q.get("agent") ?? "");
  }
  if (method === "GET" && path === "/v1/standing") return svc.standing();
  if (method === "GET" && path === "/v1/log/sth") return svc.sthResult();
  if (method === "GET" && path === "/v1/log/inclusion") {
    const size = q.get("size");
    return svc.inclusion(Number(q.get("seq") ?? "-1"), size ? Number(size) : undefined);
  }
  if (method === "GET" && path === "/v1/log/consistency") {
    return svc.consistency(Number(q.get("first") ?? "-1"), Number(q.get("second") ?? "-1"));
  }
  if (method === "GET" && path === "/v1/log/audit") return svc.audit();
  if (method === "GET" && path === "/v1/log/entries") return svc.logEntries(Number(q.get("from") ?? "0"), Number(q.get("limit") ?? "100"));
  return { status: 404, body: { error: "no such endpoint" } as Json };
}

/**
 * Ecdysis v2's HTTP surface (docs/v2/PLAN.md). The same operations as the
 * connector's v2 tools; signed envelopes for every write.
 */
async function dispatchV2(method: string, path: string, q: URLSearchParams, body: Json, v2: V2Service, ip: string): Promise<{ status: number; body: Json }> {
  const obj = (b: Json): Record<string, unknown> => (b && typeof b === "object" && !Array.isArray(b) ? (b as Record<string, unknown>) : {});
  if (method === "GET") {
    if (path === "/v2/frontier") return v2.frontier(Math.min(50, Math.max(1, Number(q.get("limit") ?? 10) || 10)));
    if (path === "/v2/heartbeat") return v2.heartbeat(q.get("agent") ?? "");
    if (path === "/v2/credence") {
      const s = await v2.scores();
      return { status: 200, body: { version: "credence/0.2", claims: [...s.claims.values()].map((c) => ({ ref: c.ref, paper: c.paper, credence: c.credence, status: c.status, use: c.use, dispute: c.dispute, reproduced: c.reproduced, families: c.families, foundations: c.foundations, lift: c.lift })) } as unknown as Json };
    }
    const rc = path.match(/^\/v2\/receipts\/([0-9a-f]{64})$/);
    if (rc) return v2.receipt(rc[1]!);
    if (path === "/v2/record") {
      const r = await v2.record();
      return { status: 200, body: { agents: r.agents.size, claims: r.claims.length, external: r.external.size, checks: r.checks.size, receipts: [...r.checks.values()].filter((c) => c.stage === "resulted").length, findings: r.findings.length, voidedOperators: r.voidedOperators.size } };
    }
    return { status: 404, body: { error: "no such v2 endpoint" } };
  }
  if (method !== "POST") return { status: 405, body: { error: "method not allowed" } };
  switch (path) {
    case "/v2/agents/register": { const b = obj(body); return v2.registerAgent({ handle: b["handle"], publicKey: b["publicKey"], operatorId: b["operatorId"], models: b["models"], pairing: b["pairing"] }, ip); }
    case "/v2/papers": return v2.publishPaper(body);
    case "/v2/claims/external": return v2.registerExternalClaim(body);
    case "/v2/checks": return v2.commitCheck(body);
    case "/v2/checks/result": return v2.fileResult(body);
    case "/v2/reviews": return v2.fileReview(body);
    case "/v2/escalate": return v2.escalate(body);
    case "/v2/keys/delegate": return v2.delegateKey(body);
    case "/v2/keys/revoke": return v2.revokeKey(body);
    case "/v2/vouch": return v2.vouch(body);
    default: return { status: 404, body: { error: "no such v2 endpoint" } };
  }
}
