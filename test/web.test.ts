/**
 * The two-halves site: structure, script discipline, and the on-ramp.
 *
 * Guarantees: every human page ships no script and its CSP forbids script
 * outright; every page in a half says which half it is in; the people half
 * leads with prompts a person can copy; the agent half points at the
 * machine-readable protocol; agents asking for JSON at the root still get
 * JSON; and the site, the protocol and the terms tell one story: claims,
 * not papers; no citation on faith; credence moved only by evidence.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { MemoryRateLimiter, route, type RouteOptions } from "../src/api/router.js";
import { MemoryStore } from "../src/store/memory-store.js";
import { TransparencyLog } from "../src/core/log.js";
import { generateKeyPair } from "../src/core/crypto.js";
import { MemoryV2Store, V2Service } from "../src/api/v2/service.js";
import { PagesHandler } from "../src/api/v2/pages.js";
import { esc, shortDate, statusTone, V2_AGENT_NAV, V2_PEOPLE_NAV } from "../src/web/design.js";
import { constitutionHash } from "../src/core/constitution.js";
import type { Json } from "../src/core/canonical.js";

async function world() {
  const now = () => new Date(Date.UTC(2026, 9, 5, 12, 0, 0));
  const store = new MemoryStore();
  const log = new TransparencyLog(store, now);
  const logKey = await generateKeyPair();
  const v2store = new MemoryV2Store(() => (store as unknown as { log: Array<{ entry: { seq: number; ts: string; type: string }; payload: Json }> }).log.map((r) => ({ seq: r.entry.seq, ts: r.entry.ts, type: r.entry.type, payload: r.payload })));
  const svc = new V2Service({ log, store: v2store, logPrivateKey: logKey.privateKey, now });
  const pages = new PagesHandler(svc, { host: "ecdysis.me", logPublicKey: logKey.publicKey, archive: "https://v1.ecdysis.me" });
  const opts: RouteOptions = { v2: svc, pages, sthPublicKey: logKey.publicKey, archive: "https://v1.ecdysis.me" };
  return opts;
}
const get = (path: string, accept = "text/html") =>
  new Request(`https://ecdysis.me${path}`, { headers: { accept } });
const limiter = () => new MemoryRateLimiter(1000);

/** Every human page the network serves, static or computed from an empty record. */
const PAGES = ["/", "/people", "/start", "/join", "/agents", "/connect", "/lab", "/claims", "/claims/all", "/map", "/leaderboard", "/observatory", "/faq", "/compare", "/api", "/governance", "/privacy", "/kit"];

describe("two halves", () => {
  it("serves every human page with no script and a CSP that forbids it", async () => {
    const opts = await world();
    for (const p of PAGES) {
      const r = await route(get(p), limiter(), opts);
      assert.equal(r.status, 200, p);
      const csp = r.headers.get("content-security-policy") ?? "";
      assert.ok(!csp.includes("script-src"), `${p}: CSP must not allow script`);
      assert.match(csp, /default-src 'none'/, p);
      assert.match(csp, /frame-ancestors 'none'/, p);
      const html = await r.text();
      assert.ok(!html.includes("<script"), `${p}: no script element`);
      // Other archives' preprints may be described (the FAQ and the comparison do), and the protocol names the retired paths
      // so an old copy learns where the work went; none of the record's own retired machinery is described as live.
      assert.doesNotMatch(html, /\b(jury|jurors?|vouched|vouching|challenge board|publish_paper|\/papers\/)\b/i, `${p}: nothing from before the network`);
    }
  });

  it("marks which half a page belongs to, and each half's navigation is the network's", async () => {
    const opts = await world();
    const people = await (await route(get("/people"), limiter(), opts)).text();
    assert.match(people, /<a href="\/people" aria-current="true">People<\/a>/);
    assert.match(people, /aria-label="For people"/);
    for (const [href, label] of V2_PEOPLE_NAV) assert.ok(people.includes(`<a href="${href}"${href === "/people" ? ' aria-current="page"' : ""}>${label}</a>`), `${label} in the people nav`);
    const agents = await (await route(get("/agents"), limiter(), opts)).text();
    assert.match(agents, /<a href="\/agents" aria-current="true">Agents<\/a>/);
    assert.match(agents, /aria-label="For agents"/);
    for (const [href, label] of V2_AGENT_NAV) assert.ok(agents.includes(`<a href="${href}"${href === "/agents" ? ' aria-current="page"' : ""}>${label}</a>`), `${label} in the agent nav`);
    assert.deepEqual(V2_PEOPLE_NAV.map(([h]) => h), ["/people", "/connect", "/lab", "/claims", "/map", "/leaderboard", "/observatory", "/faq"], "no papers, frontier, review or graph page");
    assert.ok(!V2_AGENT_NAV.some(([h]) => /papers|frontier|graph|challenges|review/.test(h)));
  });

  it("still gives agents JSON at the root", async () => {
    const r = await route(get("/", "application/json"), limiter(), await world());
    assert.match(r.headers.get("content-type") ?? "", /application\/json/);
    const body = (await r.json()) as { start: string; protocol: string };
    assert.equal(body.start, "GET /skill.md");
    assert.equal(body.protocol, "ecdysis/0.2");
  });
});

describe("the people half", () => {
  it("leads with three copyable prompts that point at the protocol and keep the human in the loop", async () => {
    const html = await (await route(get("/people"), limiter(), await world())).text();
    assert.match(html, /Put your AI to work on science/);
    const prompts = html.match(/<p class="pt">([^<]*)<\/p>/g) ?? [];
    assert.equal(prompts.length, 3, "three prompts");
    for (const p of prompts) {
      assert.match(p, /skill\.md and follow it/, "each prompt defers to the protocol");
      assert.match(p, /before you (publish|file) anything/, "each keeps the human in the loop");
      assert.match(p, /research agent/, "each starts an agent that keeps going, not a one-off");
      assert.match(p, /set up your doorbell \(skill\.md, &quot;Doorbells&quot;\)/, "each ends by setting up the doorbell");
      // A walled-in AI gets through on its own before it involves the person.
      assert.match(p, /raw\.githubusercontent\.com\/djhulme1\/ecdysis-core\/main\/docs\/skill\.md/, "each prompt names the GitHub copy");
      assert.doesNotMatch(p, /\[your [a-z' ]+\]/, "no placeholders to edit");
    }
    assert.match(html, /ask me only if you can&#39;t tell which|ask me only if you can't tell which/, "the AI infers the field");
    assert.match(html, /It comes back by itself/);
    assert.match(html, /user-select:all/, "one click selects a whole prompt");
    assert.match(html, /Claims, not papers/);
    assert.match(html, /Even an attempt is logged/);
  });

  it("hands the protocol to a stuck AI from /kit, with the live log key in it", async () => {
    const opts = await world();
    const html = await (await route(get("/kit"), limiter(), opts)).text();
    assert.match(html, /Hand the protocol to your AI/);
    assert.match(html, /copied it from https:\/\/ecdysis\.me\/kit because you can&#39;t reach the site/);
    assert.match(html, /raw\.githubusercontent\.com\/djhulme1\/ecdysis-core\/main\/docs\/skill\.md/, "the GitHub copy comes first");
    assert.match(html, /Never include your private key/);
    assert.match(html, /MCowBQYDK2VwAyEA/, "the log key is in the protocol it carries");
    assert.doesNotMatch(html, /plain JSON \(no payload or signature wrapper\)|tracking link/, "no paste relay: every write is an envelope the AI signs itself");
  });

  it("asks agents to choose an operator id, not to make their person do it, and never to name them", async () => {
    const skill = await (await route(get("/skill.md"), limiter(), await world())).text();
    assert.match(skill, /operator id of your own|operatorId/);
    assert.match(skill, /never a name or an email address|no names of private people/);
    assert.match(skill, /Never include a\s+private key anywhere/);
  });

  it("lists claims newest first, and says what to do when there are none", async () => {
    const opts = await world();
    const empty = await (await route(get("/claims"), limiter(), opts)).text();
    assert.match(empty, /No claims yet/);
    assert.match(empty, /<a href="\/feeds\/all\.atom">/);
    assert.match(empty, /The record is a network of claims/);
    const all = await (await route(get("/claims/all"), limiter(), opts)).text();
    assert.match(all, /Every claim in view/);
  });
});

describe("the agent half", () => {
  it("points at the machine-readable protocol, the connector and the network's tools", async () => {
    const html = await (await route(get("/agents"), limiter(), await world())).text();
    assert.match(html, /GET https:\/\/ecdysis\.me\/skill\.md/);
    assert.match(html, /"mcpServers"/);
    assert.match(html, /publish_claims/);
    assert.match(html, /get_heartbeat/);
    assert.match(html, /file_attempt/);
    assert.match(html, /commit_check/);
    assert.match(html, /docs\/QUICKSTART\.md/, "the worked example");
    assert.doesNotMatch(html, /publish_paper|\/v2\/papers|\/v1\//);
  });
});

describe("design primitives", () => {
  it("escapes, dates and status marks safely", () => {
    assert.equal(esc(`<a href="x">'&`), "&lt;a href=&quot;x&quot;&gt;&#39;&amp;");
    assert.equal(shortDate("2026-09-30T20:45:00Z"), "30 Sep 2026");
    assert.equal(shortDate("not a date"), "");
    // Five marks, none carried by colour alone (brand kit, 3 Oct 2026): filled, outlined, dashed, the one orange, crossed.
    assert.equal(statusTone("established"), "sound");
    assert.equal(statusTone("supported"), "part");
    assert.equal(statusTone("unchecked"), "open");
    assert.equal(statusTone("contested"), "risk", "contested is the one status that takes the accent: it asks for attention");
    assert.equal(statusTone("refuted"), "broken");
    assert.equal(statusTone(null), "open", "anything unknown reads as unchecked");
  });
});

describe("one story across the site and the protocol", () => {
  it("tells people, agents and machines the same rules: claims not papers, no citation on faith, credence moved only by evidence", async () => {
    const opts = await world();
    const text = async (p: string, accept = "text/html") => (await route(get(p, accept), limiter(), opts)).text();
    const landing = await text("/");
    assert.match(landing, /There are no papers, only claims building on claims/);
    assert.match(landing, /Published as claims, each tested on its own/);
    assert.ok(landing.includes(await constitutionHash()));
    const faq = await text("/faq");
    assert.match(faq, /Where are the papers\?/);
    assert.match(faq, /What is a claim\?/);
    const agents = await text("/agents");
    assert.match(agents, /no citation on faith/);
    const people = await text("/people");
    assert.match(people, /Claims, not papers/);
    assert.match(people, /a citation never moves a credence/);
    const skill = await text("/skill.md", "text/markdown");
    for (const h of ["## Publishing claims (network/0.1)", "## Claims from human literature", "## Receipts: the only way to check", "## Credence, use, dispute, stakes: four numbers, never blended", "## The network (network/0.1)", "## Verify, don't trust"]) assert.ok(skill.includes(h), h);
    assert.match(skill, /there are no papers/);
    assert.match(skill, /No citation on faith/);
    assert.match(skill, /basis "reproduced"/);
    assert.doesNotMatch(skill, /"preprint"|publish_paper|vouching|jury/);
    assert.match(skill, /Paths retired with the papers \(\/v2\/papers, \/v2\/frontier,\s+\/v2\/challenges, \/v2\/vouch\) answer 410/, "an old copy learns where the work went");
    const llms = await text("/llms.txt", "text/plain");
    assert.match(llms, /network of claims, not of papers/);
    assert.match(llms, /nothing is cited on faith/);
    assert.match(llms, /\/v2\/direction/);
    const terms = await text("/terms", "text/markdown");
    assert.match(terms, /## Claims, not assertions/);
    assert.doesNotMatch(terms, /preprint|paper|vouch/i);
    const missing = await route(get(`/c/ecd:${"0".repeat(16)}`), limiter(), opts);
    assert.equal(missing.status, 404);
    assert.match(await missing.text(), /No claim by that id is on the record/);
  });
});

describe("the brand (kit of 3 Oct 2026)", () => {
  it("serves the kit's SVGs unchanged, puts the lockup and the person's page in every header, and never types the brand name as the logo", async () => {
    const { BRAND_ASSETS, LOGO_HORIZONTAL_LIGHT, LOGO_HORIZONTAL_DARK, LOGO_SYMBOL, FAVICON_SVG, brandLockup, BRAND } = await import("../src/web/brand.js");
    const { shell, CSS } = await import("../src/web/design.js");
    // The assets are the kit's: the emblem's three fixed tints, the wordmark path shared by the light and dark lockups, nothing else changed.
    for (const tint of [BRAND.signalOrange, BRAND.wingMid, BRAND.wingPale]) for (const svg of [LOGO_HORIZONTAL_LIGHT, LOGO_HORIZONTAL_DARK, LOGO_SYMBOL, FAVICON_SVG]) assert.ok(svg.includes(`fill="${tint}"`), `${tint} in every asset`);
    assert.equal(LOGO_HORIZONTAL_LIGHT.replace('<g fill="#242629"', '<g fill="#F7F8FA"'), LOGO_HORIZONTAL_DARK, "the dark lockup is the light one with soft-white lettering");
    assert.ok(LOGO_HORIZONTAL_LIGHT.includes('viewBox="0 0 740 190"') && LOGO_SYMBOL.includes('viewBox="0 0 540 258"') && FAVICON_SVG.includes('viewBox="0 0 64 64"'));
    assert.deepEqual(Object.keys(BRAND_ASSETS).sort(), ["/brand/ecdysis-horizontal-dark.svg", "/brand/ecdysis-horizontal-light.svg", "/brand/ecdysis-symbol.svg", "/favicon.svg"]);
    for (const a of Object.values(BRAND_ASSETS)) { assert.equal(a.type, "image/svg+xml; charset=utf-8"); assert.doesNotMatch(a.body, /<script|on[a-z]+=/i, "no script in an image"); }
    // The lockup: light and dark by the reader's colour scheme, the kit's alt for a home link, proportions kept (width and height in the 740:190 ratio).
    const lock = brandLockup();
    assert.match(lock, /<source media="\(prefers-color-scheme: dark\)" srcset="\/brand\/ecdysis-horizontal-dark\.svg">/);
    assert.match(lock, /<img class="lockup" src="\/brand\/ecdysis-horizontal-light\.svg" alt="Ecdysis home" width="740" height="190"/);
    assert.match(lock, /<img class="symbol" src="\/brand\/ecdysis-symbol\.svg" alt="" [^>]*aria-hidden="true"/, "the small-screen symbol is decorative beside the lockup");
    // Every page: the lockup is the home link, the top bar holds People, Agents and Your Ecdysis, the favicon is the kit's.
    const page = shell({ title: "T", description: "d", half: "people", body: "<p>x</p>" });
    assert.match(page, /<a class="brand" href="\/"><picture>/);
    assert.match(page, /<nav class="halves" aria-label="Site"><span class="seg"><a href="\/people" aria-current="true">People<\/a><a href="\/agents">Agents<\/a><\/span><a class="me" href="\/me">Your Ecdysis<\/a><\/nav>/);
    assert.match(page, /<link rel="icon" href="\/favicon\.svg" type="image\/svg\+xml">/);
    assert.match(shell({ title: "T", description: "d", half: "me", body: "" }), /<a class="me" href="\/me" aria-current="true">Your Ecdysis<\/a>/, "on the person's own pages the top bar says so");
    assert.doesNotMatch(page, /class="brand"[^<]*<svg|>ecdysis</, "the brand name is never typed as the logo");
    // The palette is the kit's and only the kit's: soft white, ink, signal orange; ink on orange buttons; the old amber, teal, violet and vermillion are gone.
    assert.match(CSS, /--ground:#F7F8FA;--card:#FFFFFF;--ink:#242629/);
    assert.match(CSS, /--accent:#FF8A24;--on-accent:#242629/);
    assert.match(CSS, /@media \(prefers-color-scheme:dark\)\{:root\{--ground:#242629;--card:#2C2F33;--ink:#F7F8FA/);
    for (const gone of ["#93560A", "#00806B", "#6345C1", "#CC3D17", "#F3F5F4", "#1F1A14"]) assert.ok(!CSS.includes(gone), `${gone} is gone`);
    assert.doesNotMatch(CSS, /gradient/, "no gradients");
    // Interactive targets are 44px, focus is visible, motion is respected.
    assert.match(CSS, /\.halves \.seg a\{[^}]*min-height:44px/);
    assert.match(CSS, /\.btn\{[^}]*min-height:44px/);
    assert.match(CSS, /:focus-visible\{outline:2px solid var\(--ink\);outline-offset:4px\}/);
    assert.match(CSS, /prefers-reduced-motion:reduce/);
  });
});
