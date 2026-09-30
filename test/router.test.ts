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
    assert.match(html, /ECDYSIS/);
    assert.ok(html.includes(await constitutionHash()), "landing page shows the constitution hash");
    assert.ok(html.includes("test-public-key-value-long-enough"), "landing page shows the log public key");
    const csp = page.headers.get("content-security-policy") ?? "";
    assert.match(csp, /frame-ancestors 'none'/);
    assert.match(csp, /connect-src 'self'/);

    const index = await route(req("/"), svc, limiter());
    assert.match(index.headers.get("content-type") ?? "", /application\/json/);
    const body = (await index.json()) as { service: string; start: string };
    assert.equal(body.service, "ecdysis-core");
    assert.equal(body.start, "GET /skill.md");
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
      assert.match(html, /ecdysis\.me — the record/);
      assert.match(html, /ecdysis\.app — the impact/);
      assert.match(html, /What this is not/);
      assert.ok(!html.includes("<script"), "about page ships no script");
    }
    const landing = await route(req("/", { accept: "text/html" }), svc, limiter());
    assert.match(await landing.text(), /\/about/);
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
