/**
 * HTTP-layer tests: the public site, the kill switch, HEAD handling, and
 * header discipline. Policy is tested at the service layer; this file covers
 * what the router itself adds.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { MemoryRateLimiter, route } from "../src/api/router.js";
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
    assert.match(await landing.text(), /\/about/);
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
    assert.ok(many.size <= MemoryRateLimiter.MAX_KEYS, "still inside the window, the oldest go first");
  });
});
