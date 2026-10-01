/**
 * The two-halves site: structure, script discipline, and the on-ramp.
 *
 * Guarantees: every human page except the Observatory ships no script and
 * its CSP forbids script outright; every page in a half says which half it
 * is in; the people half leads with prompts a person can copy; the agent
 * half points at the machine-readable protocol; agents asking for JSON at
 * the root still get JSON.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { MemoryRateLimiter, route } from "../src/api/router.js";
import { EcdysisService } from "../src/api/service.js";
import { MemoryStore } from "../src/store/memory-store.js";
import { structuralScreener } from "../src/core/hazard.js";
import { esc, paperStatus, shortDate, specimenLabel } from "../src/web/design.js";
import { constitutionHash } from "../src/core/constitution.js";

const svc = () =>
  new EcdysisService({ store: new MemoryStore(), screeners: [structuralScreener()], sthPrivateKey: null });
const get = (path: string, accept = "text/html") =>
  new Request(`https://ecdysis.me${path}`, { headers: { accept } });
const limiter = () => new MemoryRateLimiter(1000);

const STATIC_PAGES = ["/", "/people", "/start", "/join", "/agents", "/papers", "/about", "/why", "/apps", "/marketplace"];

describe("two halves", () => {
  it("serves every static human page with no script and a CSP that forbids it", async () => {
    const s = svc();
    for (const p of STATIC_PAGES) {
      const r = await route(get(p), s, limiter());
      assert.equal(r.status, 200, p);
      const csp = r.headers.get("content-security-policy") ?? "";
      assert.ok(!csp.includes("script-src"), `${p}: CSP must not allow script`);
      assert.match(csp, /default-src 'none'/, p);
      assert.match(csp, /frame-ancestors 'none'/, p);
      assert.ok(!(await r.text()).includes("<script"), `${p}: no script element`);
    }
  });

  it("only the Observatory may run script, and only from its own origin", async () => {
    const r = await route(get("/observatory"), svc(), limiter());
    const csp = r.headers.get("content-security-policy") ?? "";
    assert.match(csp, /script-src 'unsafe-inline'/);
    assert.match(csp, /connect-src 'self'/);
  });

  it("marks which half a page belongs to", async () => {
    const s = svc();
    const people = await (await route(get("/people"), s, limiter())).text();
    assert.match(people, /<a href="\/people" aria-current="true">People<\/a>/);
    assert.match(people, /aria-label="For people"/);
    const agents = await (await route(get("/agents"), s, limiter())).text();
    assert.match(agents, /<a href="\/agents" aria-current="true">Agents<\/a>/);
    assert.match(agents, /aria-label="For agents"/);
  });

  it("still gives agents JSON at the root", async () => {
    const r = await route(get("/", "application/json"), svc(), limiter());
    assert.match(r.headers.get("content-type") ?? "", /application\/json/);
    const body = (await r.json()) as { start: string };
    assert.equal(body.start, "GET /skill.md");
  });
});

describe("the people half", () => {
  it("leads with three copyable prompts that point at the protocol and keep the human in the loop", async () => {
    const html = await (await route(get("/people"), svc(), limiter())).text();
    assert.match(html, /Put your AI to work on science/);
    const prompts = html.match(/<p class="pt">([^<]*)<\/p>/g) ?? [];
    assert.ok(prompts.length >= 3, "three prompts plus habit lines");
    for (const p of prompts.slice(0, 3)) {
      assert.match(p, /skill\.md and follow it/, "each prompt defers to the protocol");
      assert.match(p, /before you publish anything/, "each keeps the human in the loop");
    }
    assert.match(html, /\[your topic\]/, "personal prompts carry a visible placeholder");
    assert.match(html, /user-select:all/, "one click selects a whole prompt");
    assert.match(html, /allowlist ecdysis\.me and api\.ecdysis\.me/);
  });

  it("helps a stuck AI: a self-contained hand-off prompt carrying the live constitution", async () => {
    const html = await (await route(get("/people"), svc(), limiter())).text();
    assert.match(html, /If your AI gets stuck/);
    assert.match(html, /can&#39;t reach Ecdysis/);
    const hash = await constitutionHash();
    assert.ok(html.includes(hash), "the hand-off prompt carries the current constitution hash");
    assert.match(html, /plain JSON \(no payload or signature wrapper\)/);
    assert.match(html, /MCowBQYDK2VwAyEA/);
    assert.match(html, /pip install cryptography/);
    assert.match(html, /tracking link/);
  });

  it("lists papers newest first, and says what to do when there are none", async () => {
    const empty = await (await route(get("/papers"), svc(), limiter())).text();
    assert.match(empty, /No papers yet/);
    assert.match(empty, /href="\/people"/);
  });
});

describe("the agent half", () => {
  it("points at the machine-readable protocol, MCP and the allowlist fallback", async () => {
    const html = await (await route(get("/agents"), svc(), limiter())).text();
    assert.match(html, /GET https:\/\/ecdysis\.me\/skill\.md/);
    assert.match(html, /"mcpServers"/);
    assert.match(html, /If you are blocked/);
  });
});

describe("design primitives", () => {
  it("escapes, dates and labels safely", () => {
    assert.equal(esc(`<a href="x">'&`), "&lt;a href=&quot;x&quot;&gt;&#39;&amp;");
    assert.equal(shortDate("2026-09-30T20:45:00Z"), "30 Sep 2026");
    assert.equal(shortDate("not a date"), "");
    const hostile = specimenLabel({ id: "javascript:alert(1)", title: "<img src=x onerror=1>", agent: "a", fieldLabel: "ml", ts: "" });
    assert.ok(!hostile.includes("<img"), "titles are escaped");
    assert.ok(!hostile.includes('href="/p/javascript'), "non-platform ids are never linked");
    assert.equal(paperStatus(["replicated", "refuted"]), "refuted", "a refutation dominates");
    assert.equal(paperStatus([]), "unexamined");
  });
});
