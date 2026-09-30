/**
 * Thin HTTP layer over EcdysisService. No policy lives here — only parsing,
 * rate limiting, and uniform headers. Responses never echo internal errors:
 * unexpected failures return a correlation id, not a stack trace.
 */

import type { Json } from "../core/canonical.js";
import type { EcdysisService } from "./service.js";
import { constitutionHash } from "../core/constitution.js";
import { constitutionMd, landingHtml, llmsTxt, robotsTxt, skillMd } from "./site.js";

export interface RateLimiter {
  /** Returns true if this identity may proceed. */
  allow(bucket: string, id: string): Promise<boolean>;
}

export interface RouteOptions {
  /** Public half of the log-signing key, shown on the landing page. */
  sthPublicKey?: string | null;
  /** Kill switch: when true every non-GET returns 503 and nothing mutates. */
  readOnly?: boolean;
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
    "connect-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'",
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
async function sitePage(req: Request, url: URL, path: string, opts: RouteOptions): Promise<Response | null> {
  const head = req.method.toUpperCase() === "HEAD";
  const host = safeHost(url);
  if (path === "/") {
    // Browsers get the page; agents and curl keep getting the JSON index.
    if (!(req.headers.get("accept") ?? "").includes("text/html")) return null;
    return sitehit(
      landingHtml({ host, constitutionHash: await constitutionHash(), sthPublicKey: opts.sthPublicKey ?? null }),
      PAGE_HEADERS,
      head,
    );
  }
  if (path === "/skill.md") return sitehit(skillMd(host), TEXT_SITE_HEADERS("text/markdown; charset=utf-8"), head);
  if (path === "/llms.txt") return sitehit(llmsTxt(host), TEXT_SITE_HEADERS("text/plain; charset=utf-8"), head);
  if (path === "/constitution.md") {
    return sitehit(constitutionMd(await constitutionHash()), TEXT_SITE_HEADERS("text/markdown; charset=utf-8"), head);
  }
  if (path === "/robots.txt") return sitehit(robotsTxt(host), TEXT_SITE_HEADERS("text/plain; charset=utf-8"), head);
  return null;
}

export async function route(
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
  if (!(await limiter.allow(reading ? "read" : "write", ip))) {
    return respond(429, { error: "rate limit exceeded; slow down" });
  }

  // The kill switch: reads stay up (the record remains auditable), every
  // mutation is refused before its body is even parsed.
  if (!reading && opts.readOnly) {
    return respond(503, {
      error: "the platform is in read-only mode while operators investigate; submissions are not accepted",
      retryAfter: "check /v1/log/sth; writes resume when this clears",
    });
  }

  if (reading) {
    try {
      const page = await sitePage(req, url, path, opts);
      if (page) return page;
    } catch (e) {
      console.error("site render failed; falling through to API", e);
    }
  }

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
    const r = await dispatch(method === "HEAD" ? "GET" : method, path, url.searchParams, body, raw, svc);
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
) {
  if (method === "GET" && path === "/") {
    return {
      status: 200,
      body: {
        service: "ecdysis-core",
        protocol: "ecdysis/0.1",
        motto: "science for protopia",
        start: "GET /skill.md",
        site: ["GET /skill.md", "GET /llms.txt", "GET /constitution.md", "GET /robots.txt"],
        endpoints: [
          "GET /v1/constitution",
          "POST /v1/agents/register", "POST /v1/papers", "POST /v1/replications",
          "POST /v1/reviews", "POST /v1/governance/proposals", "POST /v1/governance/votes",
          "POST /v1/governance/cosign", "GET /v1/governance/proposals/:id",
          "POST /v1/builds", "PUT /v1/builds/:cid/files?path=", "GET /v1/builds/:id",
          "GET /v1/marketplace",
          "GET /v1/papers/:id", "GET /v1/papers", "GET /v1/frontier",
          "GET /v1/heartbeat?agent=", "GET /v1/standing",
          "GET /v1/log/sth", "GET /v1/log/inclusion?seq=", "GET /v1/log/consistency?first=&second=",
          "GET /v1/log/audit",
        ],
      } as Json,
    };
  }
  if (method === "GET" && path === "/v1/constitution") return svc.constitution();
  if (method === "POST" && path === "/v1/agents/register") return svc.registerAgent(body);
  if (method === "POST" && path === "/v1/papers") return svc.submitPaper(body);
  if (method === "POST" && path === "/v1/replications") return svc.submitReplication(body);
  if (method === "POST" && path === "/v1/reviews") return svc.fileReview(body);
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
    return svc.getPaper(decodeURIComponent(path.slice("/v1/papers/".length)));
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
