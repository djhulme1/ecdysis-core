/**
 * HTTP-layer tests: the public site, the retired addresses, the kill switch,
 * HEAD handling, header discipline and the fallback rate limiter. Policy is
 * tested at the service layer; this file covers what the router itself adds.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { MemoryRateLimiter, RETIRED_V2, route } from "../src/api/router.js";
import { MCP_PER_ADDRESS_PER_MINUTE, PER_ADDRESS_PER_MINUTE } from "../src/core/v2/quotas.js";
import { MemoryStore } from "../src/store/memory-store.js";
import { TransparencyLog } from "../src/core/log.js";
import { generateKeyPair } from "../src/core/crypto.js";
import { MemoryV2Store, V2Service } from "../src/api/v2/service.js";
import { PagesHandler, PAGE_MOVES } from "../src/api/v2/pages.js";
import { LogApi } from "../src/api/v2/log-api.js";
import { constitutionHash } from "../src/core/constitution.js";
import type { Json } from "../src/core/canonical.js";

async function world(o: { signingKey?: boolean; finalSth?: { treeSize: number; rootHash: string; timestamp: string; signature: string } | null } = {}) {
  const now = () => new Date(Date.UTC(2026, 9, 5, 12, 0, 0));
  const store = new MemoryStore();
  const log = new TransparencyLog(store, now);
  const logKey = await generateKeyPair();
  const v2store = new MemoryV2Store(() => (store as unknown as { log: Array<{ entry: { seq: number; ts: string; type: string }; payload: Json }> }).log.map((r) => ({ seq: r.entry.seq, ts: r.entry.ts, type: r.entry.type, payload: r.payload })));
  const svc = new V2Service({ log, store: v2store, logPrivateKey: logKey.privateKey, now });
  const logApi = new LogApi({ log, reader: store, signingKey: o.signingKey === false ? null : logKey.privateKey, finalSth: o.finalSth ?? null, now });
  const pages = new PagesHandler(svc, { host: "api.ecdysis.me", logPublicKey: logKey.publicKey, archive: "https://v1.ecdysis.me", log: logApi });
  const opts = { v2: svc, log: logApi, pages, sthPublicKey: logKey.publicKey, archive: "https://v1.ecdysis.me" };
  return { svc, log, logApi, logKey, pages, opts, store };
}

function req(path: string, init: RequestInit & { accept?: string } = {}): Request {
  const headers = new Headers(init.headers);
  if (init.accept) headers.set("accept", init.accept);
  return new Request(`https://api.ecdysis.me${path}`, { ...init, headers });
}

const limiter = () => new MemoryRateLimiter(1000);

describe("public site", () => {
  it("serves the landing page to browsers and the JSON index to agents", async () => {
    const w = await world();
    const page = await route(req("/", { accept: "text/html,application/xhtml+xml" }), limiter(), w.opts);
    assert.equal(page.status, 200);
    assert.match(page.headers.get("content-type") ?? "", /text\/html/);
    const html = await page.text();
    assert.match(html, /href="\/people"/, "the person door");
    assert.match(html, /href="\/agents"/, "the agent door");
    assert.ok(html.includes(await constitutionHash()), "landing page shows the constitution hash");
    assert.ok(html.includes(w.logKey.publicKey), "landing page shows the log public key");
    const csp = page.headers.get("content-security-policy") ?? "";
    assert.match(csp, /frame-ancestors 'none'/);
    assert.ok(!csp.includes("script-src"), "the fork ships no script at all");
    assert.ok(!html.includes("<script"), "and contains none");

    const index = await route(req("/"), limiter(), w.opts);
    assert.match(index.headers.get("content-type") ?? "", /application\/json/);
    const body = (await index.json()) as { service: string; protocol: string; start: string; if_blocked: string; site: string[]; archive?: { v1: string } };
    assert.equal(body.service, "ecdysis");
    assert.equal(body.protocol, "ecdysis/0.2");
    assert.equal(body.start, "GET /skill.md");
    assert.ok(body.site.includes("GET /claims") && body.site.includes("GET /map"), "the site's pages are the network's");
    assert.ok(!body.site.some((s) => /papers|frontier|challenges/.test(s)), "and none from the paper era");
    assert.equal(body.archive?.v1, "https://v1.ecdysis.me");
    // The index is often the ONE path a walled-in agent can reach: it must say how to get through the allowlist and where
    // the readable mirror lives.
    assert.match(body.if_blocked, /allowlist api\.ecdysis\.me/);
    assert.match(body.if_blocked, /github\.com\/djhulme1\/ecdysis-core/);
  });

  it("serves the onboarding files with safe headers", async () => {
    const w = await world();
    const hash = await constitutionHash();
    const skill = await route(req("/skill.md"), limiter(), w.opts);
    assert.equal(skill.status, 200);
    assert.match(skill.headers.get("content-type") ?? "", /text\/markdown/);
    const skillBody = await skill.text();
    assert.match(skillBody, /\/v2\/agents\/register/);
    assert.match(skillBody, /network\/0\.1/);
    assert.ok(skillBody.includes(w.logKey.publicKey), "the protocol names the log key");
    const cons = await route(req("/constitution.md"), limiter(), w.opts);
    assert.equal(cons.status, 200);
    assert.ok((await cons.text()).includes(hash), "constitution page carries its own hash");
    for (const p of ["/llms.txt", "/robots.txt"]) {
      const r = await route(req(p), limiter(), w.opts);
      assert.equal(r.status, 200, p);
      assert.equal(r.headers.get("x-content-type-options"), "nosniff", p);
      assert.match(r.headers.get("content-security-policy") ?? "", /^default-src 'none'/, p);
    }
  });
});

describe("retired addresses", () => {
  it("the paper era's API paths answer 410 with where the work went, before anything else is read", async () => {
    const w = await world();
    for (const [path, reason] of Object.entries(RETIRED_V2)) {
      for (const method of ["GET", "POST"]) {
        const r = await route(req(path, { method, ...(method === "POST" ? { body: "{}", headers: { "content-type": "application/json" } } : {}) }), limiter(), w.opts);
        assert.equal(r.status, 410, `${method} ${path}`);
        const body = (await r.json()) as { error: string; see?: string };
        assert.match(body.error, /retired on 5 October 2026/);
        assert.ok(body.error.includes(reason), `${path} says where the work went`);
      }
    }
    assert.ok(Object.keys(RETIRED_V2).includes("/v2/papers") && Object.keys(RETIRED_V2).includes("/v2/frontier") && Object.keys(RETIRED_V2).includes("/v2/vouch"));
  });

  it("the first record's API, and the log's old address, answer 410 and point at the live log", async () => {
    const w = await world();
    const sth = await route(req("/v1/log/sth"), limiter(), w.opts);
    assert.equal(sth.status, 410);
    const body = (await sth.json()) as { error: string; see: string; earlier: string; archive: string };
    assert.equal(body.see, "/v2/log/sth");
    assert.match(body.error, /new genesis on 5 October 2026/);
    assert.match(body.earlier, /mirror\/v2/);
    assert.equal(body.archive, "https://v1.ecdysis.me");
    const reg = await route(req("/v1/agents/register", { method: "POST", body: "{}", headers: { "content-type": "application/json" } }), limiter(), w.opts);
    assert.equal(reg.status, 410);
    assert.match(((await reg.json()) as { error: string }).error, /archived/);
  });

  it("the paper era's pages move, permanently, to where their subject lives now", async () => {
    const w = await world();
    for (const [from, to] of Object.entries(PAGE_MOVES)) {
      const r = await route(req(from, { accept: "text/html" }), limiter(), w.opts);
      assert.equal(r.status, 301, from);
      assert.equal(r.headers.get("location"), to, from);
    }
    const hex = "0123456789abcdef";
    for (const [from, to] of [[`/x/${hex}/C1`, `/c/ext:${hex}`], [`/x/${hex}`, `/c/ext:${hex}`], ["/p/ecd:2610.abc", "/claims"], ["/p/ecd:2610.abc/C2", "/claims"], [`/c/${hex}`, "/map"]]) {
      const r = await route(req(from!, { accept: "text/html" }), limiter(), w.opts);
      assert.equal(r.status, 301, from);
      assert.equal(r.headers.get("location"), to, from);
    }
    // The first record's own pages go to its archive.
    const apps = await route(req("/apps", { accept: "text/html" }), limiter(), w.opts);
    assert.equal(apps.status, 301);
    assert.equal(apps.headers.get("location"), "https://v1.ecdysis.me/apps");
  });
});

describe("sitemap and feeds", () => {
  it("serves /sitemap.xml with the public pages and a robots.txt pointer", async () => {
    const w = await world();
    const r = await route(req("/sitemap.xml"), limiter(), w.opts);
    assert.equal(r.status, 200);
    assert.match(r.headers.get("content-type") ?? "", /application\/xml/);
    const xml = await r.text();
    assert.match(xml, /<urlset/);
    assert.match(xml, /https:\/\/ecdysis\.me\/claims<\/loc>/);
    assert.match(xml, /https:\/\/ecdysis\.me\/map<\/loc>/);
    assert.match(xml, /skill\.md<\/loc>/);
    assert.doesNotMatch(xml, /\/papers|\/frontier|\/challenges/);
    const robots = await route(req("/robots.txt"), limiter(), w.opts);
    assert.match(await robots.text(), /Sitemap: https:\/\/ecdysis\.me\/sitemap\.xml/);
  });

  it("serves valid Atom per field and for 'all', and 404s unknown fields; the observatory advertises them", async () => {
    const w = await world();
    for (const p of ["/feeds/all.atom", "/feeds/ml.atom", "/feeds/neuro.atom"]) {
      const r = await route(req(p), limiter(), w.opts);
      assert.equal(r.status, 200, p);
      assert.match(r.headers.get("content-type") ?? "", /application\/atom\+xml/);
      const xml = await r.text();
      assert.match(xml, /<feed xmlns="http:\/\/www\.w3\.org\/2005\/Atom">/);
      assert.match(xml, /<link href="https:\/\/(api\.)?ecdysis\.me\/feeds\/\w+\.atom" rel="self" type="application\/atom\+xml"\/>/);
    }
    assert.equal((await route(req("/feeds/astrology.atom"), limiter(), w.opts)).status, 404);
    const r = await route(req("/observatory", { accept: "text/html" }), limiter(), w.opts);
    const html = await r.text();
    assert.match(html, /feeds\/all\.atom/);
    assert.match(html, /rel="alternate" type="application\/atom\+xml"/);
  });
});

describe("kill switch", () => {
  it("refuses writes with 503 in read-only mode while reads stay up", async () => {
    const w = await world();
    const post = await route(req("/v2/agents/register", { method: "POST", body: "{}", accept: "application/json", headers: { "content-type": "application/json" } }), limiter(), { ...w.opts, readOnly: true });
    assert.equal(post.status, 503);
    const body = (await post.json()) as { error: string };
    assert.match(body.error, /read-only/);
    const claim = await route(req("/v2/claims", { method: "POST", body: "{}", headers: { "content-type": "application/json" } }), limiter(), { ...w.opts, readOnly: true });
    assert.equal(claim.status, 503);
    assert.equal((await route(req("/v2/log/sth"), limiter(), { ...w.opts, readOnly: true })).status, 200);
    assert.equal((await route(req("/v2/claims"), limiter(), { ...w.opts, readOnly: true })).status, 200);
    assert.equal((await route(req("/skill.md"), limiter(), { ...w.opts, readOnly: true })).status, 200);
  });

  it("does not gate writes when the switch is off", async () => {
    const w = await world();
    const post = await route(req("/v2/agents/register", { method: "POST", body: "{}", headers: { "content-type": "application/json" } }), limiter(), { ...w.opts, readOnly: false });
    // 4xx from validation, never 503: the request reached the service.
    assert.ok(post.status >= 400 && post.status < 500, String(post.status));
  });
});

describe("HEAD", () => {
  it("answers HEAD like GET, without a body", async () => {
    const w = await world();
    const head = await route(req("/v2/log/sth", { method: "HEAD" }), limiter(), w.opts);
    assert.equal(head.status, 200);
    assert.equal(await head.text(), "");
    const page = await route(req("/skill.md", { method: "HEAD" }), limiter(), w.opts);
    assert.equal(page.status, 200);
    assert.equal(await page.text(), "");
    const claims = await route(req("/claims", { method: "HEAD", accept: "text/html" }), limiter(), w.opts);
    assert.equal(claims.status, 200);
    assert.equal(await claims.text(), "");
  });
});

describe("the log over HTTP", () => {
  it("serves a signed head, entries with payloads, proofs and an audit; without a key the head is unsigned and says so by its shape", async () => {
    const w = await world();
    await w.log.append("claim.publish", { id: "ecd:0000000000000001", cid: "1".repeat(64), handle: "Ant", operatorId: "op-a", text: "a claim", test: "its test", field: "math", confidence: 0.7, builds_on: [] });
    const sth = (await (await route(req("/v2/log/sth"), limiter(), w.opts)).json()) as { treeSize: number; rootHash: string; signature?: string };
    assert.equal(sth.treeSize, 1);
    assert.ok(await TransparencyLog.verifySth(w.logKey.publicKey, sth as never), "the head verifies with the log key");
    const entries = (await (await route(req("/v2/log/entries?from=0&limit=10"), limiter(), w.opts)).json()) as { version: string; entries: Array<{ seq: number; type: string; payload: Record<string, unknown> }>; withheld: string };
    assert.equal(entries.version, "log-entries/0.2");
    assert.equal(entries.entries[0]!.type, "claim.publish");
    assert.equal(entries.entries[0]!.payload["text"], "a claim");
    assert.match(entries.withheld, /Nothing on the log is withheld/);
    const incl = await route(req("/v2/log/inclusion?seq=0"), limiter(), w.opts);
    assert.equal(incl.status, 200);
    const audit = (await (await route(req("/v2/log/audit"), limiter(), w.opts)).json()) as { intact: boolean };
    assert.equal(audit.intact, true);
    assert.equal((await route(req("/v2/log/sth", { method: "POST", body: "{}" }), limiter(), w.opts)).status, 405, "the log takes no writes over HTTP");
    assert.equal((await route(req("/v2/log/sth", { method: "POST" }), limiter(), w.opts)).status, 400, "a bodiless POST is refused before any route is read");
    const unsigned = await world({ signingKey: false });
    const head = (await (await route(req("/v2/log/sth"), limiter(), unsigned.opts)).json()) as Record<string, unknown>;
    assert.equal("signature" in head, false, "no key: an unsigned head, a known state");
    assert.equal((await route(req("/v2/log/sth"), limiter(), { v2: w.svc })).status, 501, "no log API configured: the endpoints say so");
  });
});

describe("the fallback rate limiter", () => {
  it("is one per isolate, so limits hold across requests, and its memory is bounded", async () => {
    const { limiterFrom } = await import("../src/index.js");
    const a = limiterFrom({});
    const b = limiterFrom({});
    assert.equal(a, b, "every request gets the same limiter; a fresh one per request would refuse nothing");
    // Through the binding, when bound, the limiter is Cloudflare's.
    const seen: string[] = [];
    const bound = limiterFrom({ RL_KEY: { limit: async ({ key }) => { seen.push(key); return { success: key !== "read:9.9.9.9" }; } } });
    assert.equal(await bound.allow("read", "1.1.1.1"), true);
    assert.equal(await bound.allow("read", "9.9.9.9"), false);
    assert.deepEqual(seen, ["read:1.1.1.1", "read:9.9.9.9"]);
    // Each bucket goes to the binding that carries its ceiling: one binding has one limit for every key, so the connector's
    // ceiling must never be judged by RL_KEY's. Writes share RL_KEY with reads (the same default ceiling). There is no
    // per-agent binding any more (quotas/0.3).
    const calls: Record<string, string[]> = { key: [], mcp: [] };
    const two = limiterFrom({
      RL_KEY: { limit: async ({ key }) => { calls.key!.push(key); return { success: true }; } },
      RL_MCP: { limit: async ({ key }) => { calls.mcp!.push(key); return { success: false }; } },
    });
    assert.equal(await two.allow("read", "1.1.1.1"), true);
    assert.equal(await two.allow("write", "1.1.1.1"), true);
    assert.equal(await two.allow("mcp", "1.1.1.1"), false);
    assert.deepEqual(calls, { key: ["read:1.1.1.1", "write:1.1.1.1"], mcp: ["mcp:1.1.1.1"] });
    // A bucket whose binding is not bound keeps a ceiling: it falls back to the in-memory limiter with that bucket's own
    // limit, so an old configuration with RL_KEY alone never applies the ordinary ceiling to the connector.
    const keyOnly = limiterFrom({ RL_KEY: { limit: async () => ({ success: false }) } });
    assert.equal(await keyOnly.allow("read", "3.3.3.3"), false, "RL_KEY judges reads");
    assert.equal(await keyOnly.allow("mcp", "3.3.3.3"), true, "the connector is not judged by RL_KEY");
    for (let i = 0; i < MCP_PER_ADDRESS_PER_MINUTE - 1; i++) await keyOnly.allow("mcp", "3.3.3.3");
    assert.equal(await keyOnly.allow("mcp", "3.3.3.3"), false, `but the in-memory ceiling of ${MCP_PER_ADDRESS_PER_MINUTE} still holds`);
    // A binding that fails never opens the gates: the request is judged by the in-memory limiter instead.
    const broken = limiterFrom({ RL_KEY: { limit: async () => { throw new Error("binding unavailable"); } } });
    for (let i = 0; i < PER_ADDRESS_PER_MINUTE; i++) assert.equal(await broken.allow("read", "4.4.4.4"), true);
    assert.equal(await broken.allow("read", "4.4.4.4"), false, "one past the ceiling is refused by the fallback");
    // The sliding window: 60 reads a minute per address; the 61st is refused, and a minute later the window has moved on.
    let t = Date.UTC(2026, 9, 3);
    const l = new MemoryRateLimiter(60, 60_000, () => t, { mcp: 600 });
    for (let i = 0; i < 60; i++) assert.equal(await l.allow("read", "1.1.1.1"), true, `read ${i + 1}`);
    assert.equal(await l.allow("read", "1.1.1.1"), false, "the 61st in a minute is refused");
    assert.equal(await l.allow("read", "2.2.2.2"), true, "another address is unaffected");
    assert.equal(await l.allow("mcp", "1.1.1.1"), true, "another bucket has its own ceiling");
    t += 60_001;
    assert.equal(await l.allow("read", "1.1.1.1"), true, "a minute on, the window has moved");
    // Memory: past MAX_KEYS addresses, those outside the window are forgotten; the table never grows without bound.
    const many = new MemoryRateLimiter(60, 60_000, () => t);
    for (let i = 0; i < MemoryRateLimiter.MAX_KEYS; i++) await many.allow("read", `10.0.${i >> 8}.${i & 255}`);
    assert.equal(many.size, MemoryRateLimiter.MAX_KEYS);
    t += 60_001;
    await many.allow("read", "fresh");
    assert.equal(many.size, 1, "everything outside the window was swept when the table was full");
    for (let i = 0; i < MemoryRateLimiter.MAX_KEYS + 500; i++) await many.allow("read", `10.1.${i >> 8}.${i & 255}`);
    assert.ok(many.size <= MemoryRateLimiter.MAX_KEYS, "still inside the window, the quietest go first");
    // A busy address is never evicted to make room for a flood: it was hit last, so the quiet ones go.
    const busy = new MemoryRateLimiter(60, 60_000, () => t);
    for (let i = 0; i < MemoryRateLimiter.MAX_KEYS - 1; i++) { await busy.allow("read", `10.2.${i >> 8}.${i & 255}`); }
    t += 10;
    for (let i = 0; i < 59; i++) await busy.allow("read", "busy");
    t += 10;
    for (let i = 0; i < 3000; i++) await busy.allow("read", `10.3.${i >> 8}.${i & 255}`);
    assert.equal(await busy.allow("read", "busy"), true, "the sixtieth hit is allowed");
    assert.equal(await busy.allow("read", "busy"), false, "and the sixty-first refused: the flood did not reset the busy address's count");
    // IPv6 is keyed by its /64.
    const { ipKey } = await import("../src/api/router.js");
    assert.equal(ipKey("1.2.3.4"), "1.2.3.4");
    assert.equal(ipKey("2001:db8:85a3::8a2e:370:7334"), "2001:db8:85a3:0::/64");
    assert.equal(ipKey("2001:0db8:85a3:0000:0000:8a2e:0370:7334"), "2001:db8:85a3:0::/64");
    assert.equal(ipKey("2001:db8:85a3:0:ffff:8a2e:370:7334"), ipKey("2001:db8:85a3::1"), "two addresses in one /64 share a key");
    assert.notEqual(ipKey("2001:db8:85a3:1::1"), ipKey("2001:db8:85a3::1"));
    assert.equal(ipKey("::1"), "0:0:0:0::/64");
    assert.equal(ipKey("not:an::ip::at all"), "not:an::ip::at all", "unparseable: kept as given");
    assert.equal(ipKey("local"), "local");
  });
});

describe("a frozen record's final tree head", () => {
  it("is served verbatim under READ_ONLY, so an archive needs no log key and the head verifies for ever", async () => {
    const { finalSthFrom } = await import("../src/index.js");
    // The live Worker signs the final head with its key; the archive is given that head and no key.
    const live = await world();
    await live.log.append("claim.publish", { id: "ecd:0000000000000001", cid: "1".repeat(64), handle: "Ant", operatorId: "op-a", text: "a claim", test: "its test", field: "math", confidence: 0.7, builds_on: [] });
    const final = (await live.logApi.sth()) as { treeSize: number; rootHash: string; timestamp: string; signature: string };
    assert.ok(await TransparencyLog.verifySth(live.logKey.publicKey, final));
    const json = JSON.stringify(final);
    // Parsed only when frozen; anything unreadable is ignored rather than trusted.
    assert.equal(finalSthFrom({ READ_ONLY: "0", FINAL_STH: json }), null, "not frozen: a fresh head is signed as usual");
    assert.equal(finalSthFrom({ READ_ONLY: "1", FINAL_STH: "not json" }), null);
    assert.equal(finalSthFrom({ READ_ONLY: "1", FINAL_STH: JSON.stringify({ ...final, rootHash: "short" }) }), null);
    assert.deepEqual(finalSthFrom({ READ_ONLY: "1", FINAL_STH: json }), final);
    // The archive: no private key, the final head configured; it serves exactly that head, timestamp and signature included.
    const archive = new LogApi({ log: live.log, reader: live.store, signingKey: null, finalSth: finalSthFrom({ READ_ONLY: "1", FINAL_STH: json }) });
    assert.deepEqual(await archive.sth(), final);
    const res = await route(new Request("https://v1.ecdysis.me/v2/log/sth"), new MemoryRateLimiter(), { v2: live.svc, log: archive, readOnly: true });
    assert.equal(res.status, 200);
    assert.deepEqual(await res.json(), final);
  });
});
