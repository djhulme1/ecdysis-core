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

export default {
  async fetch(req: Request, env: AppsEnv): Promise<Response> {
    const url = new URL(req.url);
    if (req.method !== "GET" && req.method !== "HEAD") {
      return text(405, "method not allowed");
    }
    const slug = url.hostname.split(".")[0] ?? "";
    if (!/^[a-z0-9][a-z0-9-]{2,40}$/.test(slug)) return text(404, "no such app");

    const row = await env.DB
      .prepare("SELECT cid, manifest_json FROM builds WHERE slug = ?1 AND status = 'active'")
      .bind(slug)
      .first<{ cid: string; manifest_json: string }>();
    if (!row) return text(404, "no active app at this address");

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
