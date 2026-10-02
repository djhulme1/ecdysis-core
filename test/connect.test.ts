/**
 * /connect: Ecdysis's connector in every major AI app, and the pages a
 * directory listing needs (privacy, domain proof).
 *
 * Guarantees: every major app has its own section with the connector's
 * address; apps with a working prompt link get a one-click start, and
 * apps without one are told plainly to copy; the page is script-free; the
 * people page's first step points at it; the privacy page exists and says
 * what is kept; and the ChatGPT domain token is served only when set, and
 * only if it looks like a token.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { MemoryRateLimiter, route } from "../src/api/router.js";
import { EcdysisService } from "../src/api/service.js";
import { MemoryStore } from "../src/store/memory-store.js";
import { structuralScreener } from "../src/core/hazard.js";

const svc = () => new EcdysisService({ store: new MemoryStore(), screeners: [structuralScreener()], sthPrivateKey: null });
const get = (path: string, host = "ecdysis.me") => new Request(`https://${host}${path}`, { headers: { accept: "text/html" } });
const lim = () => new MemoryRateLimiter(1e6);

describe("connecting every major AI app", () => {
  it("has a section for each app with the connector's address, and starts each the way it can", async () => {
    const r = await route(get("/connect"), svc(), lim());
    assert.equal(r.status, 200);
    assert.ok(!(r.headers.get("content-security-policy") ?? "").includes("script-src"));
    const html = await r.text();
    assert.ok(!html.includes("<script"));
    for (const id of ["claude", "chatgpt", "gemini", "grok", "copilot", "perplexity", "mistral", "tools", "cli", "api"]) {
      assert.ok(html.includes(`id="${id}"`), `a section for ${id}`);
    }
    assert.ok(html.split("https://api.ecdysis.me/mcp").length > 10, "the same address everywhere");
    for (const app of ["claude", "chatgpt", "grok"]) assert.ok(html.includes(`href="/o/${app}/famous"`), `one-click start in ${app}`);
    assert.match(html, /Gemini has no link that opens with a prompt/);
    assert.match(html, /Copilot has no working link that opens with a prompt/);
    assert.match(html, /Developer mode/);
    assert.match(html, /grok\.com\/connectors/);
    assert.match(html, /gemini mcp add --transport http ecdysis/);
    assert.match(html, /&quot;type&quot;: &quot;mcp&quot;, &quot;server_label&quot;: &quot;ecdysis&quot;/);
    assert.match(html, /its own key, which never leaves it/);
  });

  it("puts connecting first on the people page, and in the footer of every page", async () => {
    const people = await (await route(get("/people"), svc(), lim())).text();
    assert.ok(people.indexOf('id="step1"') < people.indexOf('id="step2"') && people.indexOf('id="step2"') < people.indexOf('id="step3"'), "three steps, in order");
    for (const id of ["claude", "chatgpt", "gemini", "grok", "copilot"]) assert.ok(people.includes(`href="/connect#${id}"`));
    assert.ok(people.includes('href="/connect"'), "and in the footer");
    const papers = await (await route(get("/papers"), svc(), lim())).text();
    assert.ok(papers.includes('href="/connect"') && papers.includes('href="/privacy"'));
  });
});

describe("what a directory listing needs", () => {
  it("serves a privacy page that says what is kept, why, for how long, and who else handles it", async () => {
    const r = await route(get("/privacy"), svc(), lim());
    assert.equal(r.status, 200);
    const html = await r.text();
    for (const must of [/Email addresses/, /Doorbells/, /erased after 30 days/, /Cloudflare/, /Resend/, /Anthropic/, /No cookies/, /replies@ecdysis\.me/, /The connector/]) {
      assert.match(html, must);
    }
  });

  it("serves the ChatGPT domain token only when set, and only if it looks like one", async () => {
    const path = "/.well-known/openai-apps-challenge";
    assert.equal((await route(get(path, "api.ecdysis.me"), svc(), lim())).status, 404);
    const ok = await route(get(path, "api.ecdysis.me"), svc(), lim(), { openaiAppsChallenge: "abc123-XYZ_token.value" });
    assert.equal(ok.status, 200);
    assert.equal(await ok.text(), "abc123-XYZ_token.value");
    assert.match(ok.headers.get("content-type") ?? "", /text\/plain/);
    const bad = await route(get(path, "api.ecdysis.me"), svc(), lim(), { openaiAppsChallenge: "<script>alert(1)</script>" });
    assert.equal(bad.status, 404);
  });
});
