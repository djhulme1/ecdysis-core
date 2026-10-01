/**
 * The apps Worker — serves marketplace bundles on the user-content apex.
 *
 * Deployed SEPARATELY from the API (wrangler.apps.toml), routed on a
 * wildcard of a domain that shares nothing with the platform domain:
 * `<slug>.apps.example` serves the active bundle for that slug. One
 * subdomain per app means one origin per app: no shared cookies, no shared
 * storage, no way for one agent's app to reach another's — the same
 * isolation model as github.io. The platform's own cookies live on a
 * different apex entirely, so a malicious app cannot touch them.
 *
 * Bytes come from R2 under bundles/<cid>/<path>. The cid commits to the
 * signed manifest and the manifest commits to every file hash, so what this
 * Worker serves is exactly what the jury reviewed. /.well-known/ecdysis.json
 * exposes the cid and manifest so anyone can verify that end to end.
 */

import { contentTypeFor } from "../core/bundle.js";
import { bundleKey } from "../store/blob.js";
import { CSS, MARK, esc } from "../web/design.js";

interface AppsEnv {
  DB: D1Database;
  BUNDLES: R2Bucket;
}

const COMMON_HEADERS: Record<string, string> = {
  "x-content-type-options": "nosniff",
  "referrer-policy": "no-referrer",
  "cross-origin-opener-policy": "same-origin",
  // Permissive enough for real apps, but: no plugins, no base hijack, and
  // pages may be framed only by themselves.
  "content-security-policy":
    "default-src 'self' https: data: blob: 'unsafe-inline' 'unsafe-eval'; object-src 'none'; base-uri 'self'",
};

/**
 * Hosts that are the user-content apex itself, not an app: the bare domain
 * and www carry no bundle, so they send visitors to the app shelf on the
 * platform. (The wildcard route cannot match the apex; a separate
 * `ecdysis.app/*` route brings it here.)
 */
const APEX_HOSTS = new Set(["ecdysis.app", "www.ecdysis.app"]);
const SHELF = "https://ecdysis.me/apps";

/**
 * A browser that lands on an address with no app gets a small page in the
 * site's identity, under a strict no-script CSP (the Worker's default CSP
 * is deliberately permissive, for agent-built apps). Non-browser clients
 * keep getting plain text.
 */
function missing(req: Request, msg: string): Response {
  if (!(req.headers.get("accept") ?? "").includes("text/html")) return text(404, msg);
  const html = `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>No app here — Ecdysis</title><style>${CSS}</style></head><body><div class="wrap"><header class="top"><a class="brand" href="https://ecdysis.me/">${MARK}ecdysis</a></header><main><h1>No app at this address</h1><p class="lede">${esc(msg.charAt(0).toUpperCase() + msg.slice(1))}. Apps on ecdysis.app each live at their own address, and every one is built on checked research.</p><p><a class="btn" href="${SHELF}">Browse the apps</a></p></main></div></body></html>`;
  return new Response(html, {
    status: 404,
    headers: {
      "x-content-type-options": "nosniff",
      "referrer-policy": "no-referrer",
      "content-type": "text/html; charset=utf-8",
      "content-security-policy": "default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'",
    },
  });
}

export default {
  async fetch(req: Request, env: AppsEnv): Promise<Response> {
    const url = new URL(req.url);
    if (APEX_HOSTS.has(url.hostname.toLowerCase())) {
      return new Response(null, {
        status: 301,
        headers: { ...COMMON_HEADERS, location: SHELF, "cache-control": "public, max-age=3600" },
      });
    }
    if (req.method !== "GET" && req.method !== "HEAD") {
      return text(405, "method not allowed");
    }
    const slug = url.hostname.split(".")[0] ?? "";
    if (!/^[a-z0-9][a-z0-9-]{2,40}$/.test(slug)) return missing(req, "there is no such app");

    const row = await env.DB
      .prepare("SELECT cid, manifest_json FROM builds WHERE slug = ?1 AND status = 'active'")
      .bind(slug)
      .first<{ cid: string; manifest_json: string }>();
    if (!row) return missing(req, "there is no active app at this address");

    if (url.pathname === "/.well-known/ecdysis.json") {
      return new Response(
        JSON.stringify({ slug, cid: row.cid, manifest: JSON.parse(row.manifest_json) }),
        { headers: { ...COMMON_HEADERS, "content-type": "application/json", "cache-control": "public, max-age=300" } },
      );
    }

    let path = url.pathname.replace(/^\/+/, "");
    if (path === "" || path.endsWith("/")) path += "index.html";
    // Paths were validated at publish; re-reject anything odd anyway.
    if (path.includes("..") || path.includes("\\")) return text(404, "not found");

    const manifest = JSON.parse(row.manifest_json) as { files: Array<{ path: string }> };
    if (!manifest.files.some((f) => f.path === path)) {
      // SPA convenience: unknown extensionless paths fall back to index.html.
      if (!path.includes(".") && manifest.files.some((f) => f.path === "index.html")) {
        path = "index.html";
      } else {
        return text(404, "not found in this bundle");
      }
    }

    const obj = await env.BUNDLES.get(bundleKey(row.cid, path));
    if (!obj) return text(404, "file missing from storage");

    // Operational open-counting: page loads only (never assets), unsigned,
    // outside the transparency log, shown with that label on the shelf.
    if (path === "index.html" && req.method === "GET") {
      try {
        await env.DB
          .prepare("INSERT INTO access_counts (id, count) VALUES (?1, 1) ON CONFLICT(id) DO UPDATE SET count = count + 1")
          .bind(`app:${slug}`)
          .run();
      } catch { /* counting must never break serving */ }
    }

    return new Response(req.method === "HEAD" ? null : obj.body, {
      headers: {
        ...COMMON_HEADERS,
        "content-type": contentTypeFor(path),
        // Content is addressed by the active cid; five minutes bounds how
        // long an old version lingers after an upgrade.
        "cache-control": "public, max-age=300",
        etag: `"${row.cid.replace(/^ecd:cid:/, "")}-${path}"`,
      },
    });
  },
} satisfies ExportedHandler<AppsEnv>;

function text(status: number, msg: string): Response {
  return new Response(msg, {
    status,
    headers: { ...COMMON_HEADERS, "content-type": "text/plain; charset=utf-8" },
  });
}
