/**
 * robots.txt, read as a crawler reads it (RFC 9309, robots-kit.ts). On the website, crawlers keep every page in the
 * sitemap and every claim, and stay off the private pages and the lists' filtered, sorted and paged views (the views
 * whose crawling knocked the site over on 21 to 22 October 2026). On the API host, which repeats the website's pages,
 * crawlers read only the guides. An agent fetching a page for a person keeps everything that is not private, on both.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { MemoryRateLimiter, route } from "../src/api/router.js";
import { MemoryStore } from "../src/store/memory-store.js";
import { TransparencyLog } from "../src/core/log.js";
import { generateKeyPair, signJson } from "../src/core/crypto.js";
import { MemoryV2Store, V2Service } from "../src/api/v2/service.js";
import { PagesHandler } from "../src/api/v2/pages.js";
import { LogApi } from "../src/api/v2/log-api.js";
import { CONSTITUTION_VERSION, constitutionHash } from "../src/core/constitution.js";
import { CRAWLER_HEAVY_VIEWS, FOR_A_PERSON, robotsTxt } from "../src/web/badge.js";
import type { Json } from "../src/core/canonical.js";
import { declared } from "./kinds-kit.js";
import { signedClaim } from "./claims-kit.js";
import { mayRead, sitemaps } from "./robots-kit.js";

const SITE = robotsTxt("ecdysis.me");
const API = robotsTxt("ecdysis.me", true);
/** Crawlers with no group of their own, which take the "*" group: the ones seen walking the lists in October 2026. */
const CRAWLERS = ["Amazonbot", "PerplexityBot", "meta-externalagent", "SemrushBot", "QlyzeBot", "GoogleOther", "ClaudeBot", "Reflectionbot", "Googlebot", "Applebot"];

const PUBLIC = ["/", "/claims", "/claims/table", "/network", "/map", "/leaderboard", "/observatory", "/people", "/c/ecd:0123456789abcdef",
  "/c/ext:0eb4de6dba1cca03", "/c/ext:0eb4de6dba1cca03/line", "/a/Exuvia", "/sitemap.xml", "/skill.md", "/llms.txt", "/feeds/all.atom",
  "/media/ecdysis-explainer.85ae80d3.jpg", "/media/public-sans-latin.5ed4d31c.woff2"];
const HEAVY = ["/claims?field=Physics%20and%20Astronomy", "/claims?status=supported&page=2", "/claims?page=2", "/claims?show=checked&sort=checked",
  "/claims/table?sort=checked", "/network?depth=all&focus=ext%3Afa4c2362f93b0f94"];
const PRIVATE = ["/me", "/me/profile", "/me/signout", "/steward", "/steward/health", "/s/x/claim/ecd:0123456789abcdef", "/o/claude/mcp", "/doorbell/confirm/a/b"];
const API_PATHS = ["/v2/claims", "/v2/record", "/v2/claims/ext:0eb4de6dba1cca03", "/v2/log/sth", "/mcp"];
const GUIDES = ["/skill.md", "/llms.txt", "/lab.md", "/openapi.json", "/.well-known/oauth-protected-resource"];

describe("robots.txt on the website", () => {
  it("lets crawlers read every public page and claim, and the front page's media, but not the heavy views or the private pages", () => {
    for (const bot of CRAWLERS) {
      for (const p of PUBLIC) assert.ok(mayRead(SITE, bot, p), `${bot} may read ${p}`);
      for (const p of HEAVY) assert.ok(!mayRead(SITE, bot, p), `${bot} stays off ${p}`);
      for (const p of PRIVATE) assert.ok(!mayRead(SITE, bot, p), `${bot} stays off ${p}`);
    }
  });

  it("lets an agent fetching for a person read the heavy views too, in any letter case, but not the private pages", () => {
    for (const agent of [...FOR_A_PERSON, "claude-user", "CHATGPT-USER"]) {
      for (const p of [...PUBLIC, ...HEAVY]) assert.ok(mayRead(SITE, agent, p), `${agent} may read ${p}`);
      for (const p of PRIVATE) assert.ok(!mayRead(SITE, agent, p), `${agent} stays off ${p}`);
    }
  });

  it("names each heavy view by its query, so the plain list and network pages stay open", () => {
    for (const v of CRAWLER_HEAVY_VIEWS) {
      assert.ok(v.endsWith("?"), v);
      assert.ok(mayRead(SITE, "Googlebot", v.slice(0, -1)), v.slice(0, -1));
    }
    assert.deepEqual(sitemaps(SITE), ["https://ecdysis.me/sitemap.xml"]);
  });
});

describe("robots.txt on the API host", () => {
  it("keeps crawlers to the guides and points them at the website's sitemap", () => {
    for (const bot of CRAWLERS) {
      for (const p of GUIDES) assert.ok(mayRead(API, bot, p), `${bot} may read ${p}`);
      for (const p of [...PUBLIC.filter((x) => !GUIDES.includes(x)), ...HEAVY, ...PRIVATE, ...API_PATHS]) assert.ok(!mayRead(API, bot, p), `${bot} stays off api ${p}`);
    }
    assert.deepEqual(sitemaps(API), ["https://ecdysis.me/sitemap.xml"]);
  });

  it("lets an agent fetching for a person read the API and every public page, but not the private pages", () => {
    for (const agent of FOR_A_PERSON) {
      for (const p of [...PUBLIC, ...HEAVY, ...API_PATHS, ...GUIDES]) assert.ok(mayRead(API, agent, p), `${agent} may read api ${p}`);
      for (const p of PRIVATE) assert.ok(!mayRead(API, agent, p), `${agent} stays off api ${p}`);
    }
  });
});

describe("robots.txt as served", () => {
  async function world() {
    const now = () => new Date(Date.UTC(2026, 9, 5, 12, 0, 0));
    const store = new MemoryStore();
    const log = new TransparencyLog(store, now);
    const logKey = await generateKeyPair();
    const v2store = new MemoryV2Store(() => (store as unknown as { log: Array<{ entry: { seq: number; ts: string; type: string }; payload: Json }> }).log.map((r) => ({ seq: r.entry.seq, ts: r.entry.ts, type: r.entry.type, payload: r.payload })));
    const svc = new V2Service({ log, store: v2store, logPrivateKey: logKey.privateKey, now });
    const logApi = new LogApi({ log, reader: store, signingKey: logKey.privateKey, finalSth: null, now });
    const pages = new PagesHandler(svc, { host: "api.ecdysis.me", logPublicKey: logKey.publicKey, archive: "https://v1.ecdysis.me", log: logApi });
    // One claim of the network's own and one from the literature, so the sitemap lists claim pages of both kinds.
    const ant = await generateKeyPair();
    const ACK = { version: CONSTITUTION_VERSION, hash: await constitutionHash() };
    assert.equal((await svc.registerAgent({ constitution: ACK, handle: "Ant", publicKey: ant.publicKey, operatorId: "op-a" })).status, 201);
    await svc.setTier("op-a", "verified"); // the lists, and so the sitemap, show a verified operator's claims
    const ts = now().toISOString().replace(/\.\d{3}Z$/, "Z");
    const claim = await signedClaim({ handle: "Ant", ...ant }, { text: "A claim of the network's own that the sitemap lists as a page.", field: "math", ts });
    assert.equal((await svc.publishClaim(claim.envelope)).status, 201);
    const ext: Json = declared({ protocol: "ecdysis/0.2", type: "claim.external", source: "arxiv:1706.03762", quote: "Attention alone reaches 28.4 BLEU on the task.", test: "BLEU below 27 with the stated setup", agent: { handle: "Ant", publicKey: ant.publicKey }, ts });
    assert.equal((await svc.registerExternalClaim({ payload: ext, signature: await signJson(ant.privateKey, ext) } as Json)).status, 201);
    return { opts: { v2: svc, log: logApi, pages, sthPublicKey: logKey.publicKey, archive: "https://v1.ecdysis.me" } };
  }
  const get = async (w: Awaited<ReturnType<typeof world>>, url: string, init: RequestInit = {}) => route(new Request(url, init), new MemoryRateLimiter(1000), w.opts);

  it("answers for the host it is asked on, as plain text that cannot run", async () => {
    const w = await world();
    for (const [url, want] of [["https://ecdysis.me/robots.txt", SITE], ["https://api.ecdysis.me/robots.txt", API]] as const) {
      const r = await get(w, url);
      assert.equal(r.status, 200, url);
      assert.match(r.headers.get("content-type") ?? "", /^text\/plain/, url);
      assert.equal(r.headers.get("x-content-type-options"), "nosniff", url);
      assert.match(r.headers.get("content-security-policy") ?? "", /^default-src 'none'/, url);
      assert.equal(await r.text(), want, url);
      assert.equal(await (await get(w, url, { method: "HEAD" })).text(), "", `HEAD ${url}`);
    }
  });

  it("never keeps a crawler from a page the sitemap lists, the claims' pages among them", async () => {
    const w = await world();
    const xml = await (await get(w, "https://ecdysis.me/sitemap.xml")).text();
    const paths = [...xml.matchAll(/<loc>([^<]+)<\/loc>/g)].map((m) => { const u = new URL(m[1]!); return u.pathname + u.search; });
    assert.ok(paths.some((p) => p.startsWith("/c/ecd:")) && paths.some((p) => p.startsWith("/c/ext:")), "the sitemap lists claims of both kinds");
    for (const p of paths) for (const bot of CRAWLERS) assert.ok(mayRead(SITE, bot, p), `${bot} may read ${p}, which the sitemap lists`);
  });

  it("covers the filtered and paged views the claims list links to, and none of its links to claims", async () => {
    const w = await world();
    const html = await (await get(w, "https://ecdysis.me/claims", { headers: { accept: "text/html" } })).text();
    const hrefs = [...html.matchAll(/href="(\/[^"]*)"/g)].map((m) => m[1]!.replace(/&amp;/g, "&"));
    const views = hrefs.filter((h) => h.startsWith("/claims?") || h.startsWith("/claims/table?") || h.startsWith("/network?"));
    assert.ok(views.length >= 5, `the list links to its views (${views.length})`);
    for (const h of views) {
      assert.ok(!mayRead(SITE, "PerplexityBot", h), `crawlers stay off ${h}`);
      assert.ok(mayRead(SITE, "Claude-User", h), `an agent for a person may read ${h}`);
    }
    const claims = hrefs.filter((h) => h.startsWith("/c/"));
    assert.ok(claims.length > 0, "the list links to its claims");
    for (const h of claims) assert.ok(mayRead(SITE, "PerplexityBot", h), `crawlers may read ${h}`);
  });
});
