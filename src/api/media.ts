/**
 * The site's media (src/web/media.ts), served from the Worker's static assets with byte ranges.
 *
 * Cloudflare's asset server answers every request with the whole file and status 200, whatever Range asks for.
 * Safari will not play a video from a server that does that, and no browser can seek far into one before it has
 * downloaded that far. So the Worker runs first for every request (wrangler.toml, [assets] run_worker_first),
 * and for a listed address it reads the file from the ASSETS binding and answers 206 with the bytes asked for
 * (RFC 9110 §14). Nothing else uploaded with the assets is reachable: an address under /media/ that is not
 * listed is a 404. These answers come before anything touches the record, the rate limits or the counters.
 */

import { MEDIA } from "../web/media.js";

/** The [assets] binding, as much of it as is used here: a fetch that returns the uploaded file at a path. */
export interface AssetFetcher {
  fetch(request: Request): Promise<Response>;
}

const MEDIA_HEADERS: Readonly<Record<string, string>> = {
  "x-content-type-options": "nosniff",
  "referrer-policy": "no-referrer",
  "strict-transport-security": "max-age=31536000; includeSubDomains",
  "content-security-policy": "default-src 'none'",
  // Each address names its file's hash, so what it serves never changes: a year, and no revalidation.
  "cache-control": "public, max-age=31536000, immutable",
  "accept-ranges": "bytes",
};

const TEXT_HEADERS: Readonly<Record<string, string>> = {
  "content-type": "text/plain; charset=utf-8",
  "x-content-type-options": "nosniff",
  "content-security-policy": "default-src 'none'",
  "cache-control": "no-store",
};

function text(status: number, body: string, method: string, extra: Record<string, string> = {}): Response {
  return new Response(method === "HEAD" ? null : body, { status, headers: { ...TEXT_HEADERS, ...extra } });
}

/** An inclusive byte range within a file. */
export interface ByteRange {
  start: number;
  end: number;
}

/**
 * The one range a Range header asks for, within a file of `size` bytes (RFC 9110 §14.1.2): `bytes=a-b`, `bytes=a-`
 * or the suffix `bytes=-n`. Null means send the whole file: no header, a unit other than bytes, a malformed value,
 * or several ranges (a server may ignore Range, and browsers ask for one at a time). "unsatisfiable" means the
 * range starts at or past the end, or asks for an empty suffix: the answer is 416.
 */
export function parseRange(header: string | null, size: number): ByteRange | null | "unsatisfiable" {
  if (header === null) return null;
  const m = /^\s*bytes\s*=\s*(\d*)\s*-\s*(\d*)\s*$/i.exec(header);
  if (!m || (m[1] === "" && m[2] === "")) return null;
  const num = (s: string) => (s.length > 15 ? Number.POSITIVE_INFINITY : Number(s));
  if (m[1] === "") {
    const n = num(m[2]!);
    if (n === 0 || size === 0) return "unsatisfiable";
    return { start: Math.max(0, size - n), end: size - 1 };
  }
  const start = num(m[1]!);
  const end = m[2] === "" ? Number.POSITIVE_INFINITY : num(m[2]!);
  if (end < start) return null;
  if (start >= size) return "unsatisfiable";
  return { start, end: Math.min(end, size - 1) };
}

/** Does an If-None-Match value name this entity tag? Weak comparison (§13.1.2), as the field requires. */
function noneMatch(header: string, etag: string): boolean {
  const tag = etag.replace(/^W\//, "");
  return header.split(",").some((t) => { const v = t.trim(); return v === "*" || v.replace(/^W\//, "") === tag; });
}

/**
 * The bytes [start, end] of a stream, read in order: whole chunks before the range are dropped, the chunks that
 * straddle its edges are cut, and the source is cancelled once the end is reached. A source that ends early errors
 * the stream, so a client never takes a short body for the range it asked for.
 */
export function sliceStream(source: ReadableStream<Uint8Array>, start: number, end: number): ReadableStream<Uint8Array> {
  const reader = source.getReader();
  const stop = end + 1;
  let pos = 0;
  return new ReadableStream<Uint8Array>({
    async pull(controller) {
      for (;;) {
        if (pos >= stop) {
          controller.close();
          await reader.cancel().catch(() => {});
          return;
        }
        const { value, done } = await reader.read();
        if (done) {
          controller.error(new Error(`media ended at byte ${pos}, before ${stop}`));
          return;
        }
        const from = Math.max(0, start - pos);
        const to = Math.min(value.byteLength, stop - pos);
        pos += value.byteLength;
        if (to > from) {
          controller.enqueue(value.subarray(from, to));
          return;
        }
      }
    },
    cancel(reason) {
      return reader.cancel(reason);
    },
  });
}

type FixedLengthStreamCtor = new (length: number) => { readable: ReadableStream<Uint8Array>; writable: WritableStream<Uint8Array> };

/**
 * On Workers a streamed body goes out chunked unless it passes through a FixedLengthStream, which declares its
 * length: a video wants Content-Length on every answer. Elsewhere (the tests, Node) the stream is returned as is.
 */
function withLength(body: ReadableStream<Uint8Array>, length: number): ReadableStream<Uint8Array> {
  const Fixed = (globalThis as { FixedLengthStream?: FixedLengthStreamCtor }).FixedLengthStream;
  if (!Fixed) return body;
  const fixed = new Fixed(length);
  body.pipeTo(fixed.writable).catch(() => { /* the client went away, or the source failed: the response says so */ });
  return fixed.readable;
}

/**
 * Answer a request for one of the site's media files, or null when the path is not under /media/ (everything else
 * is the record's business). GET and HEAD only; Range on GET; If-None-Match and If-Range against the file's hash.
 */
export async function serveMedia(req: Request, assets: AssetFetcher | null | undefined): Promise<Response | null> {
  const url = new URL(req.url);
  if (!url.pathname.startsWith("/media/")) return null;
  const method = req.method.toUpperCase();
  const file = MEDIA[url.pathname];
  if (!file) return text(404, "Not found", method);
  if (method !== "GET" && method !== "HEAD") return text(405, "Method not allowed", method, { allow: "GET, HEAD" });
  if (!assets) return text(503, "Media are not served by this deployment.", method);

  const etag = `"${file.sha256}"`;
  const headers: Record<string, string> = { ...MEDIA_HEADERS, "content-type": file.type, etag };
  const inm = req.headers.get("if-none-match");
  if (inm !== null && noneMatch(inm, etag)) return new Response(null, { status: 304, headers });

  // Range is defined for GET alone; If-Range with any other validator than this file's asks for the whole file.
  let range = method === "GET" ? parseRange(req.headers.get("range"), file.bytes) : null;
  const ifRange = req.headers.get("if-range");
  if (range !== null && ifRange !== null && ifRange.trim() !== etag) range = null;
  if (range === "unsatisfiable") {
    return new Response(method === "HEAD" ? null : "Range not satisfiable", {
      status: 416,
      headers: { ...headers, "content-type": "text/plain; charset=utf-8", "cache-control": "no-store", "content-range": `bytes */${file.bytes}` },
    });
  }
  const start = range ? range.start : 0;
  const end = range ? range.end : file.bytes - 1;
  const length = end - start + 1;
  headers["content-length"] = String(length);
  if (range) headers["content-range"] = `bytes ${start}-${end}/${file.bytes}`;
  const status = range ? 206 : 200;
  if (method === "HEAD") return new Response(null, { status, headers });

  let upstream: Response;
  try {
    // Only the address goes to the asset server: no Range, no validators, so it answers with the whole file.
    upstream = await assets.fetch(new Request(new URL(file.path, url.origin).toString()));
  } catch (e) {
    console.error("media: asset fetch failed", e);
    return text(503, "This file is unavailable for the moment.", method);
  }
  if (!upstream.ok || !upstream.body) {
    await upstream.body?.cancel().catch(() => {});
    console.error(`media: the asset server answered ${upstream.status} for ${file.path}`);
    return text(upstream.status === 404 ? 404 : 503, upstream.status === 404 ? "Not found" : "This file is unavailable for the moment.", method);
  }
  const whole = start === 0 && end === file.bytes - 1;
  const body = whole ? upstream.body : sliceStream(upstream.body, start, end);
  return new Response(withLength(body, length), { status, headers });
}
