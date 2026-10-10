/**
 * The front page's video, its poster and captions, and the site's two typefaces: what is uploaded, how it is served, and
 * where it shows.
 *
 * Guarantees: every file listed in src/web/media.ts is the file in public/ (size, hash, the hash in its name),
 * under Cloudflare's 25 MiB limit, and nothing unlisted sits in public/media; the video starts playing before it has
 * downloaded (its index comes first); the captions are well-formed, readable (two lines of 42 at most, no overlap)
 * and word for word the transcript on the page; /media/ answers byte ranges exactly as RFC 9110 has them, because
 * the asset server alone does not and Safari will not play a video without them; it reaches nothing it does not
 * list; the Worker answers it before anything touches the record; and the front page embeds the video with no
 * script, nothing downloaded before play, and a CSP that lets media load from this origin on that page alone.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";
import { EXPLAINER, FONTS, MEDIA, megabytes, PRELOAD_FONTS, runningTime } from "../src/web/media.js";
import { parseRange, serveMedia, sliceStream, type AssetFetcher } from "../src/api/media.js";
import { MemoryRateLimiter, route, type RouteOptions } from "../src/api/router.js";
import { MemoryStore } from "../src/store/memory-store.js";
import { TransparencyLog } from "../src/core/log.js";
import { generateKeyPair } from "../src/core/crypto.js";
import { MemoryV2Store, V2Service } from "../src/api/v2/service.js";
import { PagesHandler } from "../src/api/v2/pages.js";
import { esc } from "../src/web/design.js";
import type { Json } from "../src/core/canonical.js";

const ROOT = join(import.meta.dirname, "..");
const PUBLIC = join(ROOT, "public");
const bytesOf = (path: string) => readFileSync(join(PUBLIC, path));
const VIDEO = bytesOf(EXPLAINER.video.path);
const SIZE = VIDEO.byteLength;

/** The asset server as the binding presents it: the whole file, status 200, in chunks of `chunk` bytes, whatever is asked. */
function fakeAssets(o: { chunk?: number; truncate?: number; status?: number; throws?: boolean } = {}) {
  const asked: Request[] = [];
  const assets: AssetFetcher = {
    async fetch(req: Request) {
      asked.push(req);
      if (o.throws) throw new Error("asset server unreachable");
      if (o.status) return new Response("no", { status: o.status });
      const path = new URL(req.url).pathname;
      const all = bytesOf(path);
      const data = o.truncate !== undefined ? all.subarray(0, o.truncate) : all;
      const chunk = o.chunk ?? 65536;
      let at = 0;
      return new Response(new ReadableStream<Uint8Array>({
        pull(c) {
          if (at >= data.byteLength) return c.close();
          c.enqueue(new Uint8Array(data.subarray(at, at + chunk)));
          at += chunk;
        },
      }), { status: 200 });
    },
  };
  return { assets, asked };
}

const media = (path: string, init: RequestInit = {}) => new Request(`https://ecdysis.me${path}`, init);
const body = async (r: Response) => Buffer.from(await r.arrayBuffer());

describe("the media files", () => {
  it("are the files listed, by size, hash and the hash in their names, each under Cloudflare's 25 MiB limit", () => {
    for (const f of Object.values(MEDIA)) {
      const data = bytesOf(f.path);
      assert.equal(data.byteLength, f.bytes, `${f.path}: size`);
      const hash = createHash("sha256").update(data).digest("hex");
      assert.equal(hash, f.sha256, `${f.path}: hash`);
      assert.ok(f.path.includes(`.${hash.slice(0, 8)}.`), `${f.path}: the name carries the hash, so a new file gets a new address`);
      assert.ok(f.bytes <= 25 * 1024 * 1024, `${f.path}: over the 25 MiB asset limit`);
    }
    const listed = new Set(Object.keys(MEDIA));
    for (const name of readdirSync(join(PUBLIC, "media"))) assert.ok(listed.has(`/media/${name}`), `public/media/${name} is uploaded but not listed`);
    assert.deepEqual(readdirSync(PUBLIC), ["media"], "public/ holds the media and nothing else: everything in it is uploaded");
  });

  it("carries the two typefaces as WOFF2, each face once per range, served whole and cached for a year", async () => {
    assert.equal(FONTS.length, 8, "two families, upright and italic, Latin and Latin Extended");
    for (const f of FONTS) {
      assert.equal(new TextDecoder("latin1").decode(bytesOf(f.path).subarray(0, 4)), "wOF2", `${f.path} is WOFF2`);
      assert.equal(f.type, "font/woff2");
      const r = (await serveMedia(media(f.path), fakeAssets().assets))!;
      assert.equal(r.status, 200, f.path);
      assert.equal(r.headers.get("content-type"), "font/woff2");
      assert.match(r.headers.get("cache-control") ?? "", /max-age=31536000, immutable/);
      assert.deepEqual(await body(r), bytesOf(f.path));
    }
    assert.equal(new Set(FONTS.map((f) => `${f.family}|${f.style}|${f.range}`)).size, FONTS.length, "no face twice");
    assert.deepEqual(PRELOAD_FONTS.map((f) => [f.family, f.style, f.path.includes("-ext") ? "ext" : "latin"]), [["Public Sans", "normal", "latin"], ["Newsreader", "normal", "latin"]], "every page preloads the upright Latin faces, and nothing else");
  });

  it("is a video that starts before it has downloaded: H.264 in MP4, its index (moov) ahead of the data (mdat)", () => {
    const view = new DataView(VIDEO.buffer, VIDEO.byteOffset, VIDEO.byteLength);
    const ascii = (a: number, b: number) => String.fromCharCode(...VIDEO.subarray(a, b));
    const atoms: string[] = [];
    for (let at = 0; at + 8 <= SIZE;) {
      let len = view.getUint32(at);
      const type = ascii(at + 4, at + 8);
      if (len === 1) len = Number(view.getBigUint64(at + 8));
      atoms.push(type);
      if (len < 8) break;
      at += len;
    }
    assert.equal(atoms[0], "ftyp");
    assert.ok(atoms.indexOf("moov") > -1 && atoms.indexOf("moov") < atoms.indexOf("mdat"), `moov must precede mdat: ${atoms.join(" ")}`);
    assert.ok(new TextDecoder("latin1").decode(VIDEO.subarray(0, 300_000)).includes("avc1"), "H.264, which every browser plays");
    assert.ok(statSync(join(PUBLIC, EXPLAINER.poster.path)).size < 150_000, "the poster stays light: it loads with the page");
  });

  it("has captions that are well-formed, readable, inside the running time, and word for word the transcript", () => {
    const vtt = readFileSync(join(PUBLIC, EXPLAINER.captions.path), "utf8");
    assert.match(vtt, /^WEBVTT\n/);
    const secs = (t: string) => { const [h, m, s] = t.split(":"); return Number(h) * 3600 + Number(m) * 60 + Number(s); };
    const cues = vtt.trim().split(/\n\n+/).slice(1).map((block) => {
      const lines = block.split("\n");
      const m = /^(\d\d:\d\d:\d\d\.\d{3}) --> (\d\d:\d\d:\d\d\.\d{3})$/.exec(lines[1] ?? "");
      assert.ok(m, `a cue's timing: ${block}`);
      return { start: secs(m[1]!), end: secs(m[2]!), text: lines.slice(2) };
    });
    assert.ok(cues.length > 20);
    let last = 0;
    for (const c of cues) {
      assert.ok(c.start >= last && c.end > c.start, `cues in order, none overlapping: ${c.text.join(" ")}`);
      assert.ok(c.text.length >= 1 && c.text.length <= 2 && c.text.every((l) => l.length <= 42), `two lines of 42 at most: ${c.text.join(" / ")}`);
      last = c.end;
    }
    assert.ok(last <= EXPLAINER.seconds, "the last caption ends before the video does");
    const words = (s: string) => s.toLowerCase().replace(/[^a-z0-9' ]+/g, " ").split(/\s+/).filter(Boolean);
    assert.deepEqual(words(cues.map((c) => c.text.join(" ")).join(" ")), words(EXPLAINER.transcript.join(" ")));
    assert.ok(EXPLAINER.transcript.join(" ").includes("It's why I created Ecdysis."), "the name is spelt as the platform spells it");
  });

  it("are described the way people read sizes and times", () => {
    assert.equal(runningTime(EXPLAINER.seconds), "1 min 53 s");
    assert.equal(runningTime(60), "1 min");
    assert.equal(runningTime(9.4), "9 s");
    assert.equal(megabytes(EXPLAINER.video.bytes), "16 MB");
  });
});

describe("byte ranges (RFC 9110 §14)", () => {
  it("parses one range in each form, ignores what it may ignore, and names what cannot be satisfied", () => {
    assert.equal(parseRange(null, 100), null);
    assert.deepEqual(parseRange("bytes=0-1", 100), { start: 0, end: 1 }, "Safari's first question");
    assert.deepEqual(parseRange("bytes=0-", 100), { start: 0, end: 99 });
    assert.deepEqual(parseRange("bytes=40-", 100), { start: 40, end: 99 });
    assert.deepEqual(parseRange("bytes=-30", 100), { start: 70, end: 99 }, "a suffix");
    assert.deepEqual(parseRange("bytes=-300", 100), { start: 0, end: 99 }, "a suffix longer than the file is the file");
    assert.deepEqual(parseRange("bytes=90-1000", 100), { start: 90, end: 99 }, "an end past the file is clamped");
    assert.deepEqual(parseRange("BYTES = 5 - 9", 100), { start: 5, end: 9 }, "the unit is case-blind, whitespace allowed");
    assert.deepEqual(parseRange("bytes=5-99999999999999999999", 100), { start: 5, end: 99 }, "a huge end is clamped, not mangled");
    assert.equal(parseRange("bytes=100-", 100), "unsatisfiable");
    assert.equal(parseRange("bytes=99999999999999999999-", 100), "unsatisfiable");
    assert.equal(parseRange("bytes=-0", 100), "unsatisfiable");
    for (const ignored of ["bytes=0-1,5-9", "bytes=9-5", "bytes=-", "bytes=a-b", "items=0-1", "bytes 0-1", ""]) assert.equal(parseRange(ignored, 100), null, ignored);
  });

  it("slices a stream at any offsets, across chunk edges, and errors when the source ends early", async () => {
    const data = new Uint8Array(1000).map((_, i) => i % 251);
    const stream = (chunk: number, upto = data.length) => new ReadableStream<Uint8Array>({
      start(c) { for (let at = 0; at < upto; at += chunk) c.enqueue(data.slice(at, Math.min(at + chunk, upto))); c.close(); },
    });
    let seed = 7;
    const rnd = (n: number) => { seed = (seed * 1103515245 + 12345) % 2147483648; return seed % n; };
    for (let k = 0; k < 200; k++) {
      const a = rnd(1000), b = a + rnd(1000 - a), chunk = 1 + rnd(300);
      const got = Buffer.from(await new Response(sliceStream(stream(chunk), a, b)).arrayBuffer());
      assert.deepEqual(got, Buffer.from(data.slice(a, b + 1)), `[${a}, ${b}] in chunks of ${chunk}`);
    }
    await assert.rejects(new Response(sliceStream(stream(64, 500), 400, 900)).arrayBuffer(), /ended at byte 500/);
  });
});

describe("/media/", () => {
  it("answers the whole file with its length, type, hash and a year's caching", async () => {
    const { assets, asked } = fakeAssets();
    const r = (await serveMedia(media(EXPLAINER.video.path), assets))!;
    assert.equal(r.status, 200);
    assert.equal(r.headers.get("content-type"), "video/mp4");
    assert.equal(r.headers.get("content-length"), String(SIZE));
    assert.equal(r.headers.get("accept-ranges"), "bytes");
    assert.equal(r.headers.get("etag"), `"${EXPLAINER.video.sha256}"`);
    assert.equal(r.headers.get("cache-control"), "public, max-age=31536000, immutable");
    assert.equal(r.headers.get("x-content-type-options"), "nosniff");
    assert.equal(r.headers.get("content-security-policy"), "default-src 'none'");
    assert.ok((await body(r)).equals(VIDEO));
    assert.equal(asked.length, 1);
    assert.equal(asked[0]!.headers.get("range"), null, "the asset server is asked for the whole file, never a range it would ignore");
  });

  it("answers ranges with 206 and exactly the bytes asked for: Safari's probe, a seek, a suffix", async () => {
    const { assets } = fakeAssets({ chunk: 7919 });
    const cases: Array<[string, number, number]> = [["bytes=0-1", 0, 1], ["bytes=0-", 0, SIZE - 1], [`bytes=${SIZE - 1000}-`, SIZE - 1000, SIZE - 1], ["bytes=-4096", SIZE - 4096, SIZE - 1], ["bytes=123456-654321", 123456, 654321], [`bytes=8000000-${SIZE + 5}`, 8000000, SIZE - 1]];
    for (const [range, a, b] of cases) {
      const r = (await serveMedia(media(EXPLAINER.video.path, { headers: { range } }), assets))!;
      assert.equal(r.status, 206, range);
      assert.equal(r.headers.get("content-range"), `bytes ${a}-${b}/${SIZE}`, range);
      assert.equal(r.headers.get("content-length"), String(b - a + 1), range);
      assert.ok((await body(r)).equals(VIDEO.subarray(a, b + 1)), `${range}: the bytes`);
    }
  });

  it("refuses a range past the end with 416, and sends the whole file for what it may ignore", async () => {
    const { assets } = fakeAssets();
    const past = (await serveMedia(media(EXPLAINER.video.path, { headers: { range: `bytes=${SIZE}-` } }), assets))!;
    assert.equal(past.status, 416);
    assert.equal(past.headers.get("content-range"), `bytes */${SIZE}`);
    assert.equal(past.headers.get("cache-control"), "no-store");
    for (const range of ["bytes=0-1,10-20", "bytes=junk"]) {
      const r = (await serveMedia(media(EXPLAINER.video.path, { headers: { range } }), assets))!;
      assert.equal(r.status, 200, range);
      assert.equal(r.headers.get("content-length"), String(SIZE), range);
      await r.body?.cancel();
    }
  });

  it("honours If-Range and If-None-Match against the file's hash", async () => {
    const { assets, asked } = fakeAssets();
    const etag = `"${EXPLAINER.video.sha256}"`;
    const stale = (await serveMedia(media(EXPLAINER.video.path, { headers: { range: "bytes=0-1", "if-range": '"an-older-cut"' } }), assets))!;
    assert.equal(stale.status, 200, "a range of another version is not a range of this one: the whole file");
    await stale.body?.cancel();
    const fresh = (await serveMedia(media(EXPLAINER.video.path, { headers: { range: "bytes=0-1", "if-range": etag } }), assets))!;
    assert.equal(fresh.status, 206);
    await fresh.body?.cancel();
    const n = asked.length;
    for (const inm of [etag, `W/${etag}`, `"x", ${etag}`, "*"]) {
      const r = (await serveMedia(media(EXPLAINER.video.path, { headers: { "if-none-match": inm } }), assets))!;
      assert.equal(r.status, 304, inm);
      assert.equal(r.body, null);
      assert.equal(r.headers.get("etag"), etag);
    }
    assert.equal(asked.length, n, "a 304 reads nothing");
  });

  it("answers HEAD with the headers alone, Range ignored, and refuses other methods", async () => {
    const { assets, asked } = fakeAssets();
    const head = (await serveMedia(media(EXPLAINER.video.path, { method: "HEAD", headers: { range: "bytes=0-1" } }), assets))!;
    assert.equal(head.status, 200, "range handling is defined for GET alone");
    assert.equal(head.headers.get("content-length"), String(SIZE));
    assert.equal(head.body, null);
    const post = (await serveMedia(media(EXPLAINER.video.path, { method: "POST", body: "x" }), assets))!;
    assert.equal(post.status, 405);
    assert.equal(post.headers.get("allow"), "GET, HEAD");
    assert.equal(asked.length, 0);
  });

  it("serves the poster and captions with their own types", async () => {
    const { assets } = fakeAssets();
    for (const f of [EXPLAINER.poster, EXPLAINER.captions]) {
      const r = (await serveMedia(media(f.path), assets))!;
      assert.equal(r.status, 200);
      assert.equal(r.headers.get("content-type"), f.type);
      assert.ok((await body(r)).equals(bytesOf(f.path)), f.path);
    }
  });

  it("reaches only what it lists, leaves every other path to the record, and fails closed", async () => {
    const { assets, asked } = fakeAssets();
    assert.equal(await serveMedia(media("/"), assets), null);
    assert.equal(await serveMedia(media("/mediae"), assets), null);
    assert.equal(await serveMedia(media("/c/ecd:0123456789abcdef"), assets), null);
    for (const p of ["/media/", "/media/ecdysis-explainer.mp4", "/media/../wrangler.toml", "/media/%2e%2e/wrangler.toml", `${EXPLAINER.video.path}/x`, "/media/ECDYSIS-EXPLAINER.0D4AAE2A.MP4"]) {
      const r = (await serveMedia(media(p), assets))!;
      assert.ok(r === null || r.status === 404, `${p}: ${r?.status}`);
    }
    assert.equal(asked.length, 0, "nothing unlisted is ever fetched from the assets");
    assert.equal((await serveMedia(media(EXPLAINER.video.path), undefined))!.status, 503, "no binding: says so");
    assert.equal((await serveMedia(media(EXPLAINER.video.path), fakeAssets({ throws: true }).assets))!.status, 503);
    assert.equal((await serveMedia(media(EXPLAINER.video.path), fakeAssets({ status: 404 }).assets))!.status, 404);
    const short = (await serveMedia(media(EXPLAINER.video.path, { headers: { range: "bytes=1000-2000000" } }), fakeAssets({ truncate: 1_000_000 }).assets))!;
    await assert.rejects(short.arrayBuffer(), "an upload shorter than listed never passes for the range asked");
  });

  it("is answered by the Worker before anything touches the record", async () => {
    const { default: worker } = await import("../src/index.js");
    const { assets } = fakeAssets();
    // No D1, no keys: were the record touched first, this would throw.
    const env = { ASSETS: assets } as unknown as Parameters<typeof worker.fetch>[1];
    const ctx = { waitUntil() {}, passThroughOnException() {} } as unknown as Parameters<typeof worker.fetch>[2];
    const r = await worker.fetch(media(EXPLAINER.video.path, { headers: { range: "bytes=0-1" } }) as Parameters<typeof worker.fetch>[0], env, ctx);
    assert.equal(r.status, 206);
    assert.ok((await body(r)).equals(VIDEO.subarray(0, 2)));
  });

  it("is configured so the Worker runs first: the asset server alone would ignore Range", () => {
    const toml = readFileSync(join(ROOT, "wrangler.toml"), "utf8");
    const block = /^\[assets\]\n([\s\S]*?)(?=^\[|$(?![\s\S]))/m.exec(toml)?.[1] ?? "";
    assert.match(block, /^directory = "\.\/public"$/m);
    assert.match(block, /^binding = "ASSETS"$/m);
    assert.match(block, /^run_worker_first = true$/m);
  });
});

describe("the front page's video", () => {
  async function world(): Promise<RouteOptions> {
    const now = () => new Date(Date.UTC(2026, 9, 8, 12, 0, 0));
    const store = new MemoryStore();
    const log = new TransparencyLog(store, now);
    const logKey = await generateKeyPair();
    const v2store = new MemoryV2Store(() => (store as unknown as { log: Array<{ entry: { seq: number; ts: string; type: string }; payload: Json }> }).log.map((r) => ({ seq: r.entry.seq, ts: r.entry.ts, type: r.entry.type, payload: r.payload })));
    const svc = new V2Service({ log, store: v2store, logPrivateKey: logKey.privateKey, now });
    const pages = new PagesHandler(svc, { host: "ecdysis.me", logPublicKey: logKey.publicKey });
    return { v2: svc, pages, sthPublicKey: logKey.publicKey };
  }
  const page = (path: string) => new Request(`https://ecdysis.me${path}`, { headers: { accept: "text/html" } });

  it("sits just below the opening, framed by what it answers: the browser's own player, the poster, captions, nothing loaded before play, no script", async () => {
    const opts = await world();
    const r = await route(page("/"), new MemoryRateLimiter(1000), opts);
    assert.equal(r.status, 200);
    const html = await r.text();
    const film = html.slice(html.indexOf('<section class="film-row"'), html.indexOf('<section class="figures"'));
    assert.ok(film.length > 0, "the film has its own section, before the record's figures");
    assert.ok(html.indexOf("<h1>Science has outgrown its shell.</h1>") < html.indexOf("<video"), "below the opening");
    assert.match(film, /<h2 id="film-h">Why Ecdysis exists<\/h2>/);
    assert.match(film, /Daniel Hulme, who founded Ecdysis, explains in under two minutes why science needs a record that checks itself\./);
    const video = /<video [^>]*>/.exec(film)?.[0] ?? "";
    for (const attr of ["controls", "playsinline", 'preload="none"', `poster="${EXPLAINER.poster.path}"`, 'width="1280"', 'height="720"', 'aria-labelledby="film-h"']) assert.ok(video.includes(attr), `${attr} in ${video}`);
    assert.doesNotMatch(video, /autoplay|muted|loop/, "it plays when someone asks it to, with its sound");
    assert.ok(film.includes(`<source src="${EXPLAINER.video.path}" type="video/mp4">`));
    assert.ok(film.includes(`<track kind="captions" src="${EXPLAINER.captions.path}" srclang="en" label="English">`));
    assert.match(film, /<details class="transcript"><summary>Read the transcript<\/summary>/);
    for (const p of EXPLAINER.transcript) assert.ok(film.includes(`<p>${esc(p)}</p>`), "the transcript, escaped, in full");
    assert.ok(film.includes("1&nbsp;min&nbsp;53&nbsp;s"), "the running time never breaks across lines");
    assert.ok(!html.includes("<script"), "still no script");
  });

  it("lets the front page alone load media from this origin", async () => {
    const opts = await world();
    const csp = (p: string) => route(page(p), new MemoryRateLimiter(1000), opts).then((r) => r.headers.get("content-security-policy") ?? "");
    const front = await csp("/");
    assert.match(front, /(^|; )media-src 'self'(;|$)/);
    assert.match(front, /default-src 'none'/);
    assert.match(front, /frame-ancestors 'none'/);
    assert.ok(!front.includes("script-src"));
    for (const p of ["/people", "/agents", "/claims", "/faq"]) assert.ok(!(await csp(p)).includes("media-src"), `${p}: no media, no media-src`);
  });
});
