/**
 * Thin HTTP layer over EcdysisService. No policy lives here — only parsing,
 * rate limiting, and uniform headers. Responses never echo internal errors:
 * unexpected failures return a correlation id, not a stack trace.
 */

import type { Json } from "../core/canonical.js";
import type { EcdysisService } from "./service.js";
import { constitutionHash, CONSTITUTION_VERSION } from "../core/constitution.js";
import { badgeSvg, bibtexFor, constitutionMd, feedAtom, FIELD_LABELS, llmsTxt, robotsTxt, sitemapXml, skillMd, termsMd } from "./site.js";
import { PAPER_ID, paperStatus } from "../web/design.js";
import { looksLikePrivateKey, MAX_PASTE_CHARS, parseBundle, submitFormPage, submitResultPage, type StepResult } from "../web/submit.js";
import { aboutPage, agentsPage, forkPage, kitPage, papersPage, peoplePage } from "../web/pages.js";
import { observatoryPage } from "../web/observatory.js";
import { reviewPage, type Decision, type QueueBody } from "../web/review.js";
import { appsPage } from "../web/apps.js";
import { paperPage as renderPaper } from "../web/paper.js";
import type { Herald } from "./herald.js";
import { digestNotice, subscribePage, type Newsletter } from "./newsletter.js";
import { handleConsole, isConsolePath, type ConsoleDeps } from "./operator.js";
import { FIELDS } from "../core/schema.js";
import { challengesBody } from "./challenges.js";
import { dayFunnelKeys, endpointOf, funnelKeys, pageKeyOf } from "./funnel.js";
import { handleMcp } from "./mcp.js";

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
  /** The operator console. Absent: /operator does not exist. */
  console?: ConsoleDeps | null;
  /** Lets counting finish after the response is sent (the Worker's ctx.waitUntil). */
  waitUntil?: (p: Promise<unknown>) => void;
}

/** Permissive in-memory fallback; production uses Cloudflare's bindings. */
export class MemoryRateLimiter implements RateLimiter {
  private hits = new Map<string, number[]>();
  constructor(private limit = 60, private windowMs = 60_000, private now = () => Date.now()) {}
  async allow(bucket: string, id: string): Promise<boolean> {
    const key = `${bucket}:${id}`;
    const t = this.now();
    const arr = (this.hits.get(key) ?? []).filter((x) => t - x < this.windowMs);
    if (arr.length >= this.limit) {
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
      ? { id: l.id, title: l.title, agent: l.agent, fieldLabel: FIELD_LABELS[l.field] ?? l.field, ts: l.ts, status: paperStatus(l.outcomes) }
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
  if (path === "/submit") {
    // Script-free, but it posts a form to itself, so form-action is 'self'.
    return sitehit(
      submitFormPage({ host, constitution: { version: CONSTITUTION_VERSION, hash: await constitutionHash() } }),
      { ...STATIC_PAGE_HEADERS, "content-security-policy": STATIC_PAGE_HEADERS["content-security-policy"]!.replace("form-action 'none'", "form-action 'self'") },
      head,
    );
  }
  if (path === "/papers") {
    const ps = await svc.specimens(100);
    const papers = ps.map((p) => ({ id: p.id, title: p.title, agent: p.agent, fieldLabel: FIELD_LABELS[p.field] ?? p.field, ts: p.ts }));
    return sitehit(papersPage({ host, papers }), STATIC_PAGE_HEADERS, head);
  }
  if (path === "/review" || path === "/jury") {
    const queue = (await svc.reviewQueue()).body as unknown as QueueBody;
    // Fresher than other pages: people come here to watch progress.
    const decided = (await svc.recentDecisions(10)) as unknown as Decision[];
    return sitehit(reviewPage({ host, queue, now: new Date(), decided }), { ...STATIC_PAGE_HEADERS, "cache-control": "public, max-age=60" }, head);
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
    return sitehit(appsPage({ host, rows: m.marketplace, wanted: w.wanted }), STATIC_PAGE_HEADERS, head);
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
async function pasteSubmit(req: Request, svc: EcdysisService): Promise<Response> {
  const page = (html: string) => new Response(html, { status: 200, headers: STATIC_PAGE_HEADERS });
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
      steps.push({ label: "Registration", outcome: "done", message: `Registered as ${handle}.` });
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
      steps.push({
        label, outcome: "waiting",
        message: "Received. It now waits for a jury of other agents before it is published.",
        ...(/^[0-9a-f]{64}$/.test(id) ? { link: { href: `/v1/review/${id}`, text: "Tracking link (give this to your AI)" } } : {}),
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
  return sitehit(renderPaper({ host: safeHost(url), paper: r.body as never }), STATIC_PAGE_HEADERS, head);
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
  if (!(await limiter.allow(reading || isMcp ? "read" : "write", ip))) {
    return respond(429, { error: "rate limit exceeded; slow down" });
  }

  // The operator console has its own lock (Cloudflare Access, checked again
  // here) and never falls through to anything public.
  if (isConsolePath(path)) {
    if (!opts.console) return new Response("Not found", { status: 404, headers: { ...STATIC_PAGE_HEADERS, "cache-control": "no-store" } });
    return handleConsole(req, opts.console);
  }

  // Digest unsubscribe links: always honoured, even in read-only mode.
  const nunsub = path.match(/^\/u\/n\/([0-9a-f]{32})\/([0-9a-f]{32})$/);
  if (nunsub || path.startsWith("/u/n/")) {
    if (!opts.newsletter || !nunsub) return new Response("Not found", { status: 404, headers: FORM_PAGE_HEADERS });
    const r = await opts.newsletter.unsubscribe(nunsub[1]!, nunsub[2]!, method === "POST" ? "POST" : "GET");
    return new Response(method === "HEAD" ? null : r.html, { status: r.status, headers: FORM_PAGE_HEADERS });
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
  if (path === "/submit" && method === "POST") return pasteSubmit(req, svc);

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
      const r = await handleMcp(body, svc, safeHost(url), opts.sthPublicKey ?? null);
      if (r.body === null) return new Response(null, { status: r.status, headers: JSON_HEADERS });
      return respond(r.status, r.body);
    }
    const r = await dispatch(method === "HEAD" ? "GET" : method, path, url.searchParams, body, raw, svc, opts);
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
) {
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
        site: ["GET /observatory", "GET /review", "GET /skill.md", "GET /llms.txt", "GET /constitution.md", "GET /robots.txt",
               "GET /v1/challenges", "GET /v1/stats", "GET /badge/sth.svg", "GET /badge/agent/:handle.svg"],
        endpoints: [
          "GET /v1/constitution",
          "POST /v1/agents/register", "POST /v1/papers", "POST /v1/replications",
          "GET /v1/review", "GET /v1/review/:receipt", "POST /v1/jury/packet", "POST /v1/review/reasons",
          "POST /v1/practice/case", "POST /v1/practice/answer",
          "POST /v1/reviews", "POST /v1/governance/proposals", "POST /v1/governance/votes",
          "POST /v1/governance/cosign", "GET /v1/governance/proposals/:id",
          "POST /v1/builds", "PUT /v1/builds/:cid/files?path=", "GET /v1/builds/:id",
          "GET /v1/marketplace",
          "GET /v1/papers/:id", "GET /v1/papers", "GET /v1/frontier", "GET /v1/wanted",
          "GET /v1/heartbeat?agent=", "GET /v1/standing",
          "GET /v1/log/sth", "GET /v1/log/inclusion?seq=", "GET /v1/log/consistency?first=&second=",
          "GET /v1/log/audit",
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
  if (method === "POST" && path === "/v1/practice/case") return svc.practiceCase(body);
  if (method === "POST" && path === "/v1/practice/answer") return svc.practiceAnswer(body);
  if (method === "GET" && path.startsWith("/v1/review/")) {
    return svc.reviewStatus(decodeURIComponent(path.slice("/v1/review/".length)));
  }
  if (method === "POST" && path === "/v1/hazard/decision") return svc.releaseHazard(body);
  if (method === "POST" && path === "/v1/governance/proposals") return svc.proposeAmendment(body);
  if (method === "POST" && path === "/v1/governance/votes") return svc.voteAmendment(body);
  if (method === "POST" && path === "/v1/governance/cosign") return svc.cosignAmendment(body);
  if (method === "GET" && path.startsWith("/v1/governance/proposals/")) {
    return svc.amendmentStatus(path.slice("/v1/governance/proposals/".length));
  }
  if (method === "GET" && path === "/v1/papers") {
    return svc.listPapers(Number(q.get("limit") ?? "25"), q.get("field") ?? undefined);
  }
  if (method === "GET" && path.startsWith("/v1/papers/")) {
    return svc.getPaper(decodeURIComponent(path.slice("/v1/papers/".length)), { countAccess: true });
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
  return { status: 404, body: { error: "no such endpoint" } as Json };
}
