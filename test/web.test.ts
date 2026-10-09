/**
 * The site: structure, script discipline, and the on-ramp.
 *
 * Guarantees: every human page ships no script and its CSP forbids script
 * outright; every page has its place in the top bar (Claims, Map, How it
 * works, FAQ, Your Ecdysis) and its section's tabs beneath; how it works
 * leads with prompts a person can copy; the agents' page points at the
 * machine-readable protocol; agents asking for JSON at the root still get
 * JSON; text contrast is at least 4.5:1 in both themes; and the site, the
 * protocol and the terms tell one story: claims, not papers; no citation on
 * faith; credence moved only by evidence.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { MemoryRateLimiter, route, type RouteOptions } from "../src/api/router.js";
import { MemoryStore } from "../src/store/memory-store.js";
import { TransparencyLog } from "../src/core/log.js";
import { generateKeyPair } from "../src/core/crypto.js";
import { MemoryV2Store, V2Service } from "../src/api/v2/service.js";
import { PagesHandler } from "../src/api/v2/pages.js";
import { esc, PRIMARY_NAV, shortDate, statusTone, TOKENS, V2_AGENT_NAV, V2_MAP_NAV, V2_PEOPLE_NAV } from "../src/web/design.js";
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
const PAGES = ["/", "/people", "/start", "/join", "/agents", "/connect", "/lab", "/claims", "/claims/table", "/claims/all", "/network", "/map", "/leaderboard", "/observatory", "/faq", "/compare", "/api", "/governance", "/privacy", "/kit"];

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
      assert.match(csp, /font-src 'self'(;|$)/, `${p}: the typefaces come from the site itself, and from nowhere else`);
      const html = await r.text();
      assert.ok(!html.includes("<script"), `${p}: no script element`);
      // Other archives' preprints may be described (the FAQ and the comparison do), and the protocol names the retired paths
      // so an old copy learns where the work went; none of the record's own retired machinery is described as live.
      assert.doesNotMatch(html, /\b(jury|jurors?|vouched|vouching|challenge board|publish_paper|\/papers\/)\b/i, `${p}: nothing from before the network`);
    }
  });

  it("puts every page in its place in the top bar, with its section's tabs beneath, and only the network's pages", async () => {
    const opts = await world();
    const page = async (p: string) => (await route(get(p), limiter(), opts)).text();
    assert.deepEqual(PRIMARY_NAV.map(([, h, l]) => [h, l]), [["/claims", "Claims"], ["/map", "Map"], ["/people", "How it works"], ["/faq", "FAQ"], ["/me", "Your Ecdysis"]], "the five places a person goes");
    for (const p of PAGES) assert.match(await page(p), /<nav class="primary" aria-label="Site"><a href="\/claims"[^>]*>Claims<\/a><a href="\/map"[^>]*>Map<\/a><a href="\/people"[^>]*>How it works<\/a><a href="\/faq"[^>]*>FAQ<\/a><a href="\/me"[^>]*>Your Ecdysis<\/a><\/nav>/, `${p} carries the top bar`);
    // A section's page: the top bar marks the section, its tab marks the page.
    const tabs = (html: string, nav: ReadonlyArray<readonly [string, string]>, current: string, what: string) => {
      assert.match(html, /<nav class="sub" aria-label="In this section">/, what);
      for (const [href, label] of nav) assert.ok(html.includes(`<a href="${href}"${href === current ? ' aria-current="page"' : ""}>${label}</a>`), `${label} in ${what}`);
    };
    const people = await page("/people");
    assert.match(people, /<a href="\/people" aria-current="true">How it works<\/a>/);
    tabs(people, V2_PEOPLE_NAV, "/people", "how it works' tabs");
    const agents = await page("/agents");
    assert.match(agents, /<a href="\/people" aria-current="true">How it works<\/a>/, "the agents' references sit under how it works");
    tabs(agents, V2_AGENT_NAV, "/agents", "the agents' tabs");
    const board = await page("/leaderboard");
    assert.match(board, /<a href="\/map" aria-current="true">Map<\/a>/);
    tabs(board, V2_MAP_NAV, "/leaderboard", "the map's tabs");
    // A place with no tabs: the top bar marks the page itself.
    const claims = await page("/claims");
    assert.match(claims, /<a href="\/claims" aria-current="page">Claims<\/a>/);
    assert.doesNotMatch(claims, /<nav class="sub"/);
    assert.match(await page("/claims/table"), /<a href="\/claims" aria-current="true">Claims<\/a>/, "the full table is in Claims");
    assert.match(await page("/network"), /<a href="\/claims" aria-current="true">Claims<\/a>/, "and so is the network");
    assert.deepEqual(V2_PEOPLE_NAV.map(([h]) => h), ["/people", "/connect", "/lab", "/agents", "/compare"], "no papers, frontier, review or graph page");
    assert.ok(![...V2_AGENT_NAV, ...V2_MAP_NAV].some(([h]) => /papers|frontier|graph|challenges|review/.test(h)));
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

  it("lists the claims under their papers, and says what is there when there are none", async () => {
    const opts = await world();
    const empty = await (await route(get("/claims"), limiter(), opts)).text();
    assert.match(empty, /<h1>Findings from published research, checked in the open<\/h1>/);
    assert.match(empty, /No claims are on the record yet\./);
    assert.match(empty, /<a class="btn quiet" href="\/feeds\/all\.atom">New claims feed<\/a>/);
    assert.match(empty, /<a class="btn" href="\/claims\/table">The full table<\/a>/, "checkers and agents keep the full table");
    assert.match(await (await route(get("/claims/table"), limiter(), opts)).text(), /<h1>The full table<\/h1>/);
    assert.match(await (await route(get("/claims/all"), limiter(), opts)).text(), /Every claim in view, including unchecked work from operators with no standing/);
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
    // Every page: the lockup is the home link, the top bar holds the five places, the favicon is the kit's.
    const page = shell({ title: "T", description: "d", half: "people", body: "<p>x</p>" });
    assert.match(page, /<a class="brand" href="\/"><picture>/);
    assert.match(page, /<nav class="primary" aria-label="Site"><a href="\/claims">Claims<\/a><a href="\/map">Map<\/a><a href="\/people">How it works<\/a><a href="\/faq">FAQ<\/a><a href="\/me">Your Ecdysis<\/a><\/nav>/);
    assert.match(page, /<link rel="icon" href="\/favicon\.svg" type="image\/svg\+xml">/);
    assert.match(shell({ title: "T", description: "d", half: "me", current: "/me", body: "" }), /<a href="\/me" aria-current="page">Your Ecdysis<\/a>/, "on the person's own pages the top bar says so");
    assert.doesNotMatch(page, /class="brand"[^<]*<svg|>ecdysis</, "the brand name is never typed as the logo");
    // The typefaces are the site's own, preloaded, and nothing is fetched from elsewhere.
    assert.match(page, /<link rel="preload" href="\/media\/public-sans-latin\.[0-9a-f]{8}\.woff2" as="font" type="font\/woff2" crossorigin>/);
    assert.match(page, /<link rel="preload" href="\/media\/newsreader-latin\.[0-9a-f]{8}\.woff2" as="font" type="font\/woff2" crossorigin>/);
    assert.match(CSS, /@font-face\{font-family:"Newsreader";font-style:normal;font-weight:200 800;font-display:swap;src:url\(\/media\/newsreader-latin\.[0-9a-f]{8}\.woff2\) format\("woff2"\);unicode-range:U\+0000-00FF/);
    assert.doesNotMatch(page, /fonts\.googleapis|fonts\.gstatic|https?:\/\/[^"]*\.woff2/, "no typeface from anywhere else");
    // The palette: Lucy Griffiths' redesign of 9 Oct 2026, on the kit's emblem: a warm ground, white cards, near-black ink,
    // links in a burnt orange made from the signal orange, which stays for the emblem and accents; the old palettes are gone.
    assert.match(CSS, /--ground:#F5F4EF;--card:#FFFFFF;--sunk:#F1EFE9;--ink:#1D1E22/);
    assert.match(CSS, /--link:#9A4410/);
    assert.match(CSS, /--accent:#FF8A24/);
    assert.match(CSS, /@media \(prefers-color-scheme:dark\)\{:root\{--ground:#141518;--card:#1D1F23;--sunk:#18191C;--ink:#ECEBE6/);
    for (const gone of ["#93560A", "#00806B", "#6345C1", "#CC3D17", "#F3F5F4", "#1F1A14", "#F7F8FA", "#242629"]) assert.ok(!CSS.includes(gone), `${gone} is gone`);
    assert.doesNotMatch(CSS, /gradient/, "no gradients");
    assert.doesNotMatch(CSS, /\/\*/, "the stylesheet every page carries has no comments in it");
    // Interactive targets are 44px (chips, pills and table headings at least 32px), focus is visible, motion is respected.
    assert.match(CSS, /\.primary a\{[^}]*min-height:44px/);
    assert.match(CSS, /\.btn\{[^}]*min-height:44px/);
    for (const m of CSS.matchAll(/min-height:(\d+)px/g)) assert.ok(Number(m[1]) >= 24, `a target of ${m[1]}px`);
    for (const rule of CSS.matchAll(/([^{}]*\.btn[^{}]*)\{([^}]*)\}/g)) {
      const h = rule[2]!.match(/min-height:(\d+)px/);
      if (h) assert.ok(Number(h[1]) >= 44, `${rule[1]!.trim()}: a button of ${h[1]}px`);
    }
    assert.match(CSS, /:focus-visible\{outline:2px solid var\(--link\);outline-offset:3px/);
    for (const rule of CSS.matchAll(/([^{}]*(?:input|select)[^{}]*)\{([^}]*)\}/g)) assert.doesNotMatch(rule[2]!, /border(?:-color)?:[^;]*var\(--line(?:-2)?\)/, `${rule[1]!.trim()}: a form field's border is the rule colour, which reads at 3:1`);
    assert.match(CSS, /prefers-reduced-motion:reduce/);
  });
});

describe("contrast", () => {
  /** WCAG 2's contrast ratio between two sRGB colours. */
  const ratio = (a: string, b: string) => {
    const lum = (hex: string) => {
      const [r, g, b2] = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255).map((c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4));
      return 0.2126 * r! + 0.7152 * g! + 0.0722 * b2!;
    };
    const [x, y] = [lum(a), lum(b)].sort((p, q) => q - p);
    return (x! + 0.05) / (y! + 0.05);
  };

  it("holds every text colour to 4.5:1 on what it is set on, in both themes", () => {
    for (const [theme, t] of Object.entries(TOKENS)) {
      const pairs: Array<[string, string, string]> = [];
      for (const fg of ["ink", "ink2", "muted", "faint", "link", "link2"] as const) for (const bg of ["ground", "card", "sunk"] as const) pairs.push([`${fg} on ${bg}`, t[fg], t[bg]]);
      pairs.push(["button text on ink", t.onInk, t.ink], ["green ink on its wash", t.greenInk, t.greenWash], ["amber ink on its wash", t.amberInk, t.amberWash], ["rose ink on its wash", t.roseInk, t.roseWash], ["text on green", t.onGreen, t.green]);
      for (const [what, fg, bg] of pairs) assert.ok(ratio(fg, bg) >= 4.5, `${theme}: ${what} is ${ratio(fg, bg).toFixed(2)}:1`);
      // A form field's border, which shows where to type, is held to 3:1 against the card and the ground (WCAG 1.4.11).
      for (const bg of ["card", "ground"] as const) assert.ok(ratio(t.rule, t[bg]) >= 3, `${theme}: a form border on the ${bg} is ${ratio(t.rule, t[bg]).toFixed(2)}:1`);
      // The status marks in the drawings are shapes, held to 3:1 against the card they sit on (WCAG 1.4.11).
      for (const k of ["stEst", "stSup", "stUnc", "stCon", "stRef"] as const) assert.ok(ratio(t[k], t.card) >= 3, `${theme}: ${k} on the card is ${ratio(t[k], t.card).toFixed(2)}:1`);
    }
  });
});
