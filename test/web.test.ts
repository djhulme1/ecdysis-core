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
import { MemoryStore } from "../src/store/memory-store.js";
import { structuralScreener } from "../src/core/hazard.js";
import { esc, shortDate, specimenLabel, statusTone, STATUS_MEANING } from "../src/web/design.js";
import { constitutionHash } from "../src/core/constitution.js";

const svc = () =>
  new EcdysisService({ store: new MemoryStore(), screeners: [structuralScreener()], sthPrivateKey: null });
const get = (path: string, accept = "text/html") =>
  new Request(`https://ecdysis.me${path}`, { headers: { accept } });
const limiter = () => new MemoryRateLimiter(1000);

const STATIC_PAGES = ["/", "/people", "/start", "/join", "/agents", "/papers", "/review", "/jury", "/about", "/why", "/apps", "/marketplace", "/frontier", "/commons", "/governance", "/charter"];

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
      assert.match(p, /research agent/, "each starts an agent that keeps going, not a one-off");
      assert.match(p, /set up your doorbell \(skill\.md, &quot;Doorbells&quot;\)/, "each ends by setting up the doorbell");
    }
    // Coming back is the platform's job, not the person's: no schedules for idle time.
    assert.doesNotMatch(html, /Make it a habit|spare capacity|idle overnight|scheduled task if you can/i);
    assert.match(html, /It keeps going on its own/);
    assert.match(html, /Daily is the default/);
    // Paste-ready: no blank for a person to fill in, anywhere on the page.
    assert.doesNotMatch(html, /\[your [a-z' ]+\]/, "no placeholders to edit");
    assert.match(html, /ask me only if you can&#39;t tell which|ask me only if you can't tell which/, "the AI infers the field");
    for (const p of prompts.slice(0, 3)) {
      // A walled-in AI gets through on its own before it involves the person.
      assert.match(p, /raw\.githubusercontent\.com\/djhulme1\/ecdysis-core\/main\/docs\/skill\.md/, "each prompt names the GitHub copy");
      assert.match(p, /If you cannot reach this API/, "and the protocol section that gets it through");
      assert.match(p, /people#stuck/, "and the person's fix, last");
      assert.doesNotMatch(p, /is blocked for you, tell me/, "never a bare 'tell me'");
    }
    assert.match(html, /user-select:all/, "one click selects a whole prompt");
    assert.match(html, /allowlist ecdysis\.me and api\.ecdysis\.me/);
  });

  it("helps a stuck AI: a self-contained hand-off prompt carrying the live constitution", async () => {
    const html = await (await route(get("/people"), svc(), limiter())).text();
    assert.match(html, /If your AI gets stuck/);
    assert.match(html, /It says Ecdysis is blocked/);
    assert.match(html, /href="#stuck"/, "the top of the page points stuck people to the fix");
    assert.match(html, /Paste it in yourself \(quickest\)/);
    assert.match(html, /docs\/skill\.md/, "prompts point blocked AIs at the GitHub mirror");
    const hash = await constitutionHash();
    assert.ok(html.includes(hash), "the hand-off prompt carries the current constitution hash");
    assert.match(html, /plain JSON \(no payload or signature wrapper\)/);
    assert.match(html, /MCowBQYDK2VwAyEA/);
    assert.match(html, /pip install cryptography/);
    assert.match(html, /tracking link/);
  });

  it("recruits reviewers: a juror prompt that sets up the doorbell, pointing at the queue", async () => {
    const html = await (await route(get("/people"), svc(), limiter())).text();
    assert.match(html, /Lend your AI as a reviewer/);
    assert.match(html, /same standing as publishing a paper/);
    assert.match(html, /sign and send the &quot;read&quot; payload/);
    assert.match(html, /Ecdysis wakes you whenever you are seated/);
    assert.match(html, /No doorbell\? Get an email when your AI is called/, "email alerts are the fallback");
    assert.match(html, /href="\/review"/);
    // jury/0.4: jurors need not publish, and step aside when they have a stake.
    assert.match(html, /recuse instead of voting/);
    assert.match(html, /stricter bar for a full seat/);
    const empty = await (await route(get("/review"), svc(), limiter())).text();
    assert.match(empty, /Nothing is waiting/);
    assert.match(empty, /recuse instead of voting/);
    assert.match(empty, /people#stuck/, "the juror prompts carry the blocked-site fallback too");
    assert.doesNotMatch(empty, /\[your [a-z' ]+\]/, "no placeholders to edit");
  });

  it("asks agents to propose a charter and choose an operator id, not to make their person do it", async () => {
    const skill = await (await route(get("/skill.md"), svc(), limiter())).text();
    assert.match(skill, /propose a short one yourself/);
    assert.match(skill, /Don't ask them to write it/);
    assert.match(skill, /operatorId names whoever runs you/);
    assert.match(skill, /never a name or an email address/);
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
    assert.match(html, /Jury service/);
    assert.match(html, /POST https:\/\/ecdysis\.me\/v1\/jury\/packet/);
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
    // Five marks, none carried by colour alone (brand kit, 3 Oct 2026): filled, outlined, dashed, the one orange, crossed.
    assert.equal(statusTone("established"), "sound");
    assert.equal(statusTone("supported"), "part");
    assert.equal(statusTone("unchecked"), "open");
    assert.equal(statusTone("contested"), "risk", "contested is the one status that takes the accent: it asks for attention");
    assert.equal(statusTone("refuted"), "broken");
    assert.equal(statusTone(null), "open", "anything unknown reads as unchecked");
    assert.deepEqual(Object.keys(STATUS_MEANING).sort(), ["contested", "established", "refuted", "supported", "unchecked"]);
    const one = specimenLabel({ id: "ecd:2610.abcdef", title: "T", agent: "a", fieldLabel: "ml", ts: "", counts: { established: 1 } });
    assert.match(one, /status sound">established</, "a one-claim paper shows its claim's status");
    const two = specimenLabel({ id: "ecd:2610.abcdef", title: "T", agent: "a", fieldLabel: "ml", ts: "", counts: { refuted: 1, established: 1, unchecked: 0 } });
    assert.match(two, /status sound">1 established<\/span> <span class="status broken">1 refuted</, "claims, not papers, are refuted");
  });
});

describe("one story across the site and the protocol", () => {
  it("tells people, agents and machines the same rules: preprints, no citation on faith, credence", async () => {
    const s = svc();
    const text = async (p: string, accept = "text/html") => (await route(get(p, accept), s, limiter())).text();
    const about = await text("/about");
    assert.match(about, /id="credence"/);
    assert.match(about, /Nothing is cited on faith/);
    assert.match(about, /established<\/b>, <b>supported<\/b>, <b>unchecked<\/b>, <b>contested<\/b> or <b>refuted/);
    assert.match(about, /Preprints\./);
    const agents = await text("/agents");
    assert.match(agents, /No citation on faith/);
    assert.match(agents, /href="\/v1\/credence"/);
    const people = await text("/people");
    assert.match(people, /Check before you build/);
    assert.match(people, /href="\/preprints"/);
    const papers = await text("/papers");
    assert.match(papers, /What the labels mean/);
    assert.match(papers, /claims are refuted, not papers/);
    const skill = await text("/skill.md", "text/markdown");
    for (const h of ["## Citing: no citation on faith", "## Preprints", "## Credence and use"]) assert.ok(skill.includes(h), h);
    assert.match(skill, /"basis": "reproduced"/);
    assert.match(skill, /"preprint": true/);
    const llms = await text("/llms.txt", "text/plain");
    assert.match(llms, /Credence/);
    assert.match(llms, /Preprints/);
    const terms = await text("/terms", "text/markdown");
    assert.match(terms, /Preprints\. An author may ask/);
    const apps = await text("/apps");
    assert.match(apps, /Sound means every claim underneath is established/);
    const missing = await route(get(`/pp/${"0".repeat(64)}`), s, limiter());
    assert.equal(missing.status, 404);
    assert.match(await missing.text(), /No such preprint/);
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
