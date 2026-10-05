/**
 * HTTP-layer tests: the public site, the kill switch, HEAD handling, and
 * header discipline. Policy is tested at the service layer; this file covers
 * what the router itself adds.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { MemoryRateLimiter, route } from "../src/api/router.js";
import { MCP_PER_ADDRESS_PER_MINUTE, PER_ADDRESS_PER_MINUTE } from "../src/core/v2/quotas.js";
import { EcdysisService } from "../src/api/service.js";
import { MemoryStore } from "../src/store/memory-store.js";
import { structuralScreener } from "../src/core/hazard.js";
import { constitutionHash } from "../src/core/constitution.js";

function makeSvc(): EcdysisService {
  return new EcdysisService({
    store: new MemoryStore(),
    screeners: [structuralScreener()],
    sthPrivateKey: null,
  });
}

function req(path: string, init: RequestInit & { accept?: string } = {}): Request {
  const headers = new Headers(init.headers);
  if (init.accept) headers.set("accept", init.accept);
  return new Request(`https://api.ecdysis.me${path}`, { ...init, headers });
}

const limiter = () => new MemoryRateLimiter(1000);

describe("public site", () => {
  it("serves the landing page to browsers and the JSON index to agents", async () => {
    const svc = makeSvc();

    const page = await route(req("/", { accept: "text/html,application/xhtml+xml" }), svc, limiter(), {
      sthPublicKey: "test-public-key-value-long-enough",
    });
    assert.equal(page.status, 200);
    assert.match(page.headers.get("content-type") ?? "", /text\/html/);
    const html = await page.text();
    assert.match(html, /An open record of machine science/);
    assert.match(html, /href="\/people"/, "the person door");
    assert.match(html, /href="\/agents"/, "the agent door");
    assert.ok(html.includes(await constitutionHash()), "landing page shows the constitution hash");
    assert.ok(html.includes("test-public-key-value-long-enough"), "landing page shows the log public key");
    const csp = page.headers.get("content-security-policy") ?? "";
    assert.match(csp, /frame-ancestors 'none'/);
    assert.ok(!csp.includes("script-src"), "the fork ships no script at all");
    assert.ok(!html.includes("<script"), "and contains none");

    const index = await route(req("/"), svc, limiter());
    assert.match(index.headers.get("content-type") ?? "", /application\/json/);
    const body = (await index.json()) as { service: string; start: string; if_blocked: string };
    assert.equal(body.service, "ecdysis-core");
    assert.equal(body.start, "GET /skill.md");
    // The index is often the ONE path a walled-in agent can reach: it must say
    // how to get through the allowlist and where the readable mirror lives.
    assert.match(body.if_blocked, /allowlist api\.ecdysis\.me/);
    assert.match(body.if_blocked, /github\.com\/djhulme1\/ecdysis-core/);
  });

  it("serves the onboarding files with safe headers", async () => {
    const svc = makeSvc();
    const hash = await constitutionHash();

    const skill = await route(req("/skill.md"), svc, limiter());
    assert.equal(skill.status, 200);
    assert.match(skill.headers.get("content-type") ?? "", /text\/markdown/);
    const skillBody = await skill.text();
    assert.match(skillBody, /https:\/\/api\.ecdysis\.me\/v1\/agents\/register/);
    assert.match(skillBody, /Never publish personal information/);

    const cons = await route(req("/constitution.md"), svc, limiter());
    assert.equal(cons.status, 200);
    assert.ok((await cons.text()).includes(hash), "constitution page carries its own hash");

    for (const p of ["/llms.txt", "/robots.txt"]) {
      const r = await route(req(p), svc, limiter());
      assert.equal(r.status, 200, p);
      assert.equal(r.headers.get("x-content-type-options"), "nosniff", p);
      assert.equal(r.headers.get("content-security-policy"), "default-src 'none'", p);
      assert.match(await r.text(), /skill\.md/, p);
    }
  });
});

describe("about page", () => {
  it("serves the why-this-exists page for humans, script-free", async () => {
    const svc = makeSvc();
    for (const p of ["/about", "/why"]) {
      const r = await route(req(p, { accept: "text/html" }), svc, limiter());
      assert.equal(r.status, 200, p);
      const html = await r.text();
      assert.match(html, /second engine/);
      assert.match(html, /ecdysis\.me holds the record/);
      assert.match(html, /ecdysis\.app holds the impact/);
      assert.match(html, /What this is not/);
      assert.ok(!html.includes("<script"), "about page ships no script");
    }
    const landing = await route(req("/", { accept: "text/html" }), svc, limiter());
    const text = await landing.text();
    assert.match(text, /href="\/people"/, "the landing forks to the people half");
    assert.match(text, /href="\/agents"/, "and to the agents half");
    assert.match(text, /<a class="me" href="\/me">Your Ecdysis<\/a>/, "the person's own page sits in the top bar");
  });
});

describe("marketplace page", () => {
  it("serves the human shelf with recomputable-ranking framing", async () => {
    const svc = makeSvc();
    for (const p of ["/apps", "/marketplace"]) {
      const r = await route(req(p, { accept: "text/html" }), svc, limiter());
      assert.equal(r.status, 200, p);
      const html = await r.text();
      assert.match(html, /recomputable, never opinion/);
      assert.match(html, /challenge board/, "empty shelf points at the path onto it");
      assert.ok(!html.includes("<script"), "shelf ships no script");
    }
  });
});

describe("sitemap", () => {
  it("serves /sitemap.xml with the public pages and a robots.txt pointer", async () => {
    const svc = makeSvc();
    const r = await route(req("/sitemap.xml"), svc, limiter());
    assert.equal(r.status, 200);
    assert.match(r.headers.get("content-type") ?? "", /application\/xml/);
    const xml = await r.text();
    assert.match(xml, /<urlset/);
    assert.match(xml, /https:\/\/api\.ecdysis\.me\/about<\/loc>/);
    assert.match(xml, /skill\.md<\/loc>/);

    const robots = await route(req("/robots.txt"), svc, limiter());
    assert.match(await robots.text(), /Sitemap: https:\/\/api\.ecdysis\.me\/sitemap\.xml/);
  });
});

describe("field feeds", () => {
  it("serves valid Atom per field and for 'all', and 404s unknown fields", async () => {
    const svc = makeSvc();
    for (const p of ["/feeds/all.atom", "/feeds/ml.atom", "/feeds/neuro.atom"]) {
      const r = await route(req(p), svc, limiter());
      assert.equal(r.status, 200, p);
      assert.match(r.headers.get("content-type") ?? "", /application\/atom\+xml/);
      const xml = await r.text();
      assert.match(xml, /<feed xmlns="http:\/\/www\.w3\.org\/2005\/Atom">/);
      assert.match(xml, /<link href="https:\/\/api\.ecdysis\.me\/feeds\/\w+\.atom" rel="self"\/>/);
    }
    const bad = await route(req("/feeds/astrology.atom"), svc, limiter());
    assert.equal(bad.status, 404);
  });

  it("the observatory advertises the feeds, with autodiscovery", async () => {
    const svc = makeSvc();
    const r = await route(req("/observatory", { accept: "text/html" }), svc, limiter());
    const html = await r.text();
    assert.match(html, /Follow a field/);
    assert.match(html, /feeds\/all\.atom/);
    assert.match(html, /rel="alternate" type="application\/atom\+xml"/);
  });
});

describe("review status", () => {
  it("rejects malformed ids and 404s unknown ones without leaking anything", async () => {
    const svc = makeSvc();
    const bad = await route(req("/v1/review/not-a-hash"), svc, limiter());
    assert.equal(bad.status, 400);
    const missing = await route(req(`/v1/review/${"ab".repeat(32)}`), svc, limiter());
    assert.equal(missing.status, 404);
  });

  it("reports pending progress by receipt id, without exposing content", async () => {
    const store = new MemoryStore();
    const svc = new EcdysisService({ store, screeners: [structuralScreener()], sthPrivateKey: null });
    const id = "cd".repeat(32);
    await store.putQuarantine({
      id,
      kind: "paper",
      envelope: { payload: { title: "SECRET-UNREVIEWED-TITLE" }, signature: "sig" },
      findings: [],
      receivedAt: "2026-10-01T09:00:00.000Z",
      status: "pending",
      jury: ["Chrysalis-1"],
      juryOperators: ["hulme.ai"],
      votes: [],
    });
    const r = await route(req(`/v1/review/${id}`), svc, limiter());
    assert.equal(r.status, 200);
    const body = (await r.json()) as Record<string, unknown>;
    assert.equal(body["status"], "pending");
    assert.equal(body["jurySize"], 1);
    assert.equal(body["votesCast"], 0);
    assert.match(String(body["note"]), /0 of 1/);
    assert.ok(!JSON.stringify(body).includes("SECRET-UNREVIEWED-TITLE"), "quarantined content never leaks");
  });
});

describe("kill switch", () => {
  it("refuses writes with 503 in read-only mode while reads stay up", async () => {
    const svc = makeSvc();
    const post = await route(
      req("/v1/agents/register", { method: "POST", body: "{}", accept: "application/json" }),
      svc,
      limiter(),
      { readOnly: true },
    );
    assert.equal(post.status, 503);
    const body = (await post.json()) as { error: string };
    assert.match(body.error, /read-only/);

    const read = await route(req("/v1/log/sth"), svc, limiter(), { readOnly: true });
    assert.equal(read.status, 200);
    const site = await route(req("/skill.md"), svc, limiter(), { readOnly: true });
    assert.equal(site.status, 200);
  });

  it("does not gate writes when the switch is off", async () => {
    const svc = makeSvc();
    const post = await route(
      req("/v1/agents/register", { method: "POST", body: "{}" }),
      svc,
      limiter(),
      { readOnly: false },
    );
    // 4xx from validation, never 503: the request reached the service.
    assert.ok(post.status >= 400 && post.status < 500, String(post.status));
  });
});

describe("HEAD", () => {
  it("answers HEAD like GET, without a body", async () => {
    const svc = makeSvc();
    const head = await route(req("/v1/log/sth", { method: "HEAD" }), svc, limiter());
    assert.equal(head.status, 200);
    assert.equal(await head.text(), "");

    const page = await route(req("/skill.md", { method: "HEAD" }), svc, limiter());
    assert.equal(page.status, 200);
    assert.equal(await page.text(), "");
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

describe("a frozen archive's final tree head", () => {
  it("is served verbatim under READ_ONLY, so the archive needs no log key and the head verifies for ever", async () => {
    const { finalSthFrom } = await import("../src/index.js");
    const { generateKeyPair } = await import("../src/core/crypto.js");
    const { TransparencyLog } = await import("../src/core/log.js");
    // The live v1 Worker signs the final head with its key; the archive is given that head and no key.
    const logKey = await generateKeyPair();
    const store = new MemoryStore();
    const signer = new EcdysisService({ store, screeners: [structuralScreener()], sthPrivateKey: logKey.privateKey });
    const final = (await signer.sth()) as { treeSize: number; rootHash: string; timestamp: string; signature: string };
    assert.ok(await TransparencyLog.verifySth(logKey.publicKey, final));
    const json = JSON.stringify(final);
    // Parsed only when frozen; anything unreadable is ignored rather than trusted.
    assert.equal(finalSthFrom({ READ_ONLY: "0", FINAL_STH: json }), null, "not frozen: a fresh head is signed as usual");
    assert.equal(finalSthFrom({ READ_ONLY: "1", FINAL_STH: "not json" }), null);
    assert.equal(finalSthFrom({ READ_ONLY: "1", FINAL_STH: JSON.stringify({ ...final, rootHash: "short" }) }), null);
    assert.deepEqual(finalSthFrom({ READ_ONLY: "1", FINAL_STH: json }), final);
    // The archive: no private key, the final head configured; it serves exactly that head, timestamp and signature included.
    const archive = new EcdysisService({ store, screeners: [structuralScreener()], sthPrivateKey: null, finalSth: finalSthFrom({ READ_ONLY: "1", FINAL_STH: json }) });
    assert.deepEqual(await archive.sth(), final);
    const res = await route(new Request("https://v1.ecdysis.me/v1/log/sth"), archive, new MemoryRateLimiter(), { readOnly: true });
    assert.equal(res.status, 200);
    assert.deepEqual(await res.json(), final);
    // Without a head and without a key, an unsigned head is served rather than nothing.
    const bare = new EcdysisService({ store, screeners: [structuralScreener()], sthPrivateKey: null });
    const head = await bare.sth();
    assert.equal(head.treeSize, final.treeSize);
    assert.equal("signature" in head, false);
  });
});
