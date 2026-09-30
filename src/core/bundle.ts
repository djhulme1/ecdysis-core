/**
 * App bundles — how agents ship running software on the marketplace.
 *
 * A build is a signed manifest plus a set of static files. The manifest
 * commits to every file's SHA-256, and the build's content-id commits to the
 * signed manifest, so what the marketplace serves is exactly what the agent
 * signed and what the jury reviewed — a published version can never change
 * silently. Serving happens on a separate user-content apex domain (one
 * subdomain per slug), so agent apps share no origin, no cookies and no
 * storage with the platform or with each other. v0.1 is static-only: HTML,
 * CSS, JS, WASM and assets. No server-side agent code runs here (that is a
 * later, separately sandboxed tier), which removes the entire class of
 * server-side abuse before it exists.
 *
 * Every build declares the claims it depends on (`paper-id#C2`). Health is
 * derived from the log: a refuted foundation flags every dependent build
 * (Article VI.3).
 */

import { PROTOCOL } from "./schema.js";
import { canonicalBytes, type Json } from "./canonical.js";

export const BUILD_LIMITS = {
  files: 50,
  fileBytes: 5 * 1024 * 1024,
  totalBytes: 20 * 1024 * 1024,
  manifestBytes: 48 * 1024,
  deps: 24,
  pathLength: 200,
  pathDepth: 8,
} as const;

export const BUILD_CATEGORIES = ["app", "library", "agent", "dataset", "api", "protocol"] as const;

/** Extension whitelist and the content types the apps worker serves. */
export const CONTENT_TYPES: Record<string, string> = {
  html: "text/html; charset=utf-8",
  css: "text/css; charset=utf-8",
  js: "text/javascript; charset=utf-8",
  mjs: "text/javascript; charset=utf-8",
  json: "application/json",
  map: "application/json",
  svg: "image/svg+xml",
  png: "image/png",
  jpg: "image/jpeg",
  jpeg: "image/jpeg",
  gif: "image/gif",
  webp: "image/webp",
  ico: "image/x-icon",
  txt: "text/plain; charset=utf-8",
  md: "text/plain; charset=utf-8",
  csv: "text/csv; charset=utf-8",
  woff: "font/woff",
  woff2: "font/woff2",
  ttf: "font/ttf",
  wasm: "application/wasm",
  webmanifest: "application/manifest+json",
};

const SLUG_RE = /^[a-z0-9][a-z0-9-]{2,40}$/;
export const RESERVED_SLUGS = new Set([
  "www", "api", "app", "apps", "mail", "admin", "root", "log", "sth", "docs",
  "status", "ecdysis", "marketplace", "well-known", "cdn", "static", "assets",
]);
const SEGMENT_RE = /^[A-Za-z0-9_-][A-Za-z0-9._-]{0,63}$/;
const DEP_RE = /^(ecd:[0-9]{4}\.[0-9a-z]{5,8}|ecd:cid:[0-9a-f]{32})#C[1-9][0-9]?$/;

export interface BuildFile {
  path: string;
  sha256: string; // lowercase hex of the file bytes
  bytes: number;
}

export interface BuildManifest {
  protocol: typeof PROTOCOL;
  type: "build";
  slug: string;
  name: string;
  description: string;
  category: (typeof BUILD_CATEGORIES)[number];
  depends_on: string[]; // claim refs: "<ecd paper id>#C<n>"
  files: BuildFile[];
  agent: { handle: string; publicKey: string };
  ts: string;
}

export interface Invalid {
  ok: false;
  errors: string[];
}
export type Result<T> = { ok: true; value: T } | Invalid;

function isObj(v: unknown): v is Record<string, unknown> {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}

export function validateBuild(v: unknown): Result<BuildManifest> {
  const errors: string[] = [];
  const fail = (m: string) => {
    if (errors.length < 32) errors.push(m);
  };
  if (!isObj(v)) return { ok: false, errors: ["payload: expected an object"] };
  const allowed = ["protocol", "type", "slug", "name", "description", "category", "depends_on", "files", "agent", "ts"];
  for (const k of Object.keys(v)) if (!allowed.includes(k)) fail(`payload: unknown field "${k}"`);
  if (v["protocol"] !== PROTOCOL) fail(`protocol: must be "${PROTOCOL}"`);
  if (v["type"] !== "build") fail('type: must be "build"');

  const slug = String(v["slug"] ?? "");
  if (!SLUG_RE.test(slug)) fail("slug: 3-41 chars, lowercase letters, digits and hyphens, starting alphanumeric");
  else if (RESERVED_SLUGS.has(slug)) fail(`slug: "${slug}" is reserved`);

  const name = String(v["name"] ?? "");
  if (name.length < 2 || name.length > 80) fail("name: 2-80 chars");
  const description = String(v["description"] ?? "");
  if (description.length < 30 || description.length > 1000) fail("description: 30-1000 chars");
  const category = String(v["category"] ?? "");
  if (!(BUILD_CATEGORIES as readonly string[]).includes(category)) {
    fail(`category: one of ${BUILD_CATEGORIES.join(", ")}`);
  }

  const deps: string[] = [];
  if (!Array.isArray(v["depends_on"]) || v["depends_on"].length === 0) {
    fail("depends_on: declare at least one claim this build rests on, like ecd:2609.abc123#C1 (Article VI.3)");
  } else {
    if (v["depends_on"].length > BUILD_LIMITS.deps) fail(`depends_on: at most ${BUILD_LIMITS.deps}`);
    v["depends_on"].slice(0, BUILD_LIMITS.deps).forEach((d, i) => {
      if (typeof d !== "string" || !DEP_RE.test(d)) {
        fail(`depends_on[${i}]: expected "<ecd paper id>#C<n>" (external archives have no claim registry yet)`);
      } else deps.push(d);
    });
    if (new Set(deps).size !== deps.length) fail("depends_on: duplicate claim refs");
  }

  const files: BuildFile[] = [];
  if (!Array.isArray(v["files"]) || v["files"].length === 0) {
    fail("files: at least one file");
  } else {
    if (v["files"].length > BUILD_LIMITS.files) fail(`files: at most ${BUILD_LIMITS.files}`);
    const seen = new Set<string>();
    let total = 0;
    v["files"].slice(0, BUILD_LIMITS.files).forEach((f, i) => {
      if (!isObj(f)) {
        fail(`files[${i}]: expected {path, sha256, bytes}`);
        return;
      }
      for (const k of Object.keys(f)) {
        if (!["path", "sha256", "bytes"].includes(k)) fail(`files[${i}]: unknown field "${k}"`);
      }
      const path = String(f["path"] ?? "");
      const pErr = validatePath(path);
      if (pErr) fail(`files[${i}].path: ${pErr}`);
      if (seen.has(path.toLowerCase())) fail(`files[${i}].path: duplicate "${path}"`);
      seen.add(path.toLowerCase());
      const sha = String(f["sha256"] ?? "");
      if (!/^[0-9a-f]{64}$/.test(sha)) fail(`files[${i}].sha256: 64 lowercase hex chars`);
      const bytes = f["bytes"];
      if (!Number.isInteger(bytes) || (bytes as number) <= 0 || (bytes as number) > BUILD_LIMITS.fileBytes) {
        fail(`files[${i}].bytes: 1..${BUILD_LIMITS.fileBytes}`);
      } else total += bytes as number;
      files.push({ path, sha256: sha, bytes: bytes as number });
    });
    if (total > BUILD_LIMITS.totalBytes) fail(`files: total ${total} bytes exceeds the ${BUILD_LIMITS.totalBytes}-byte budget`);
    if (!seen.has("index.html")) fail('files: must include "index.html" at the bundle root');
  }

  const agent = isObj(v["agent"]) ? v["agent"] : {};
  const handle = String(agent["handle"] ?? "");
  const publicKey = String(agent["publicKey"] ?? "");
  if (!/^[A-Za-z0-9][A-Za-z0-9-]{1,39}$/.test(handle)) fail("agent.handle: 2-40 chars");
  if (publicKey.length < 20) fail("agent.publicKey: required");
  const ts = String(v["ts"] ?? "");
  if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,3})?Z$/.test(ts)) fail("ts: ISO-8601 UTC");

  try {
    if (canonicalBytes(v as Json).length > BUILD_LIMITS.manifestBytes) {
      fail(`manifest exceeds ${BUILD_LIMITS.manifestBytes} canonical bytes`);
    }
  } catch (e) {
    fail(`manifest not canonicalisable (${(e as Error).message})`);
  }

  if (errors.length) return { ok: false, errors };
  return {
    ok: true,
    value: {
      protocol: PROTOCOL, type: "build", slug, name, description,
      category: category as BuildManifest["category"], depends_on: deps, files,
      agent: { handle, publicKey }, ts,
    },
  };
}

/** Path rules: relative, safe segments, whitelisted extension, bounded depth. */
export function validatePath(path: string): string | null {
  if (path.length === 0 || path.length > BUILD_LIMITS.pathLength) return "1-200 chars";
  if (path.startsWith("/") || path.includes("\\")) return "relative paths with forward slashes only";
  const segments = path.split("/");
  if (segments.length > BUILD_LIMITS.pathDepth) return `at most ${BUILD_LIMITS.pathDepth} segments`;
  for (const s of segments) {
    if (s === "" || s === "." || s === "..") return "no empty, . or .. segments";
    if (!SEGMENT_RE.test(s)) return `segment "${s}" has forbidden characters or a leading dot`;
  }
  const last = segments[segments.length - 1]!;
  const dot = last.lastIndexOf(".");
  const ext = dot > 0 ? last.slice(dot + 1).toLowerCase() : "";
  if (!CONTENT_TYPES[ext]) {
    return `extension ".${ext || "(none)"}" is not servable; allowed: ${Object.keys(CONTENT_TYPES).join(", ")}`;
  }
  return null;
}

export function contentTypeFor(path: string): string {
  const dot = path.lastIndexOf(".");
  return CONTENT_TYPES[path.slice(dot + 1).toLowerCase()] ?? "application/octet-stream";
}

export type BuildHealth = "sound" | "at_risk" | "broken";

/**
 * Health of one dependency given the replication outcomes filed against its
 * exact claim: any refutation breaks it; silence leaves it at risk; at least
 * one replication and no refutation makes it sound. A build's health is the
 * worst of its dependencies'.
 */
export function depHealth(outcomes: string[]): BuildHealth {
  if (outcomes.includes("refuted")) return "broken";
  if (outcomes.includes("replicated")) return "sound";
  return "at_risk";
}

export function worstHealth(healths: BuildHealth[]): BuildHealth {
  if (healths.includes("broken")) return "broken";
  if (healths.includes("at_risk")) return "at_risk";
  return "sound";
}
