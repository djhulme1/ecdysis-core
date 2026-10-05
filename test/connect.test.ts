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
import { MemoryRateLimiter, route, type RouteOptions } from "../src/api/router.js";
import { MemoryStore } from "../src/store/memory-store.js";
import { TransparencyLog } from "../src/core/log.js";
import { generateKeyPair } from "../src/core/crypto.js";
import { MemoryV2Store, V2Service } from "../src/api/v2/service.js";
import { PagesHandler } from "../src/api/v2/pages.js";
import type { Json } from "../src/core/canonical.js";

async function world(extra: Partial<RouteOptions> = {}): Promise<RouteOptions> {
  const now = () => new Date(Date.UTC(2026, 9, 5, 12, 0, 0));
  const store = new MemoryStore();
  const log = new TransparencyLog(store, now);
  const logKey = await generateKeyPair();
  const v2store = new MemoryV2Store(() => (store as unknown as { log: Array<{ entry: { seq: number; ts: string; type: string }; payload: Json }> }).log.map((r) => ({ seq: r.entry.seq, ts: r.entry.ts, type: r.entry.type, payload: r.payload })));
  const svc = new V2Service({ log, store: v2store, logPrivateKey: logKey.privateKey, now });
  const pages = new PagesHandler(svc, { host: "ecdysis.me", logPublicKey: logKey.publicKey });
  return { v2: svc, pages, sthPublicKey: logKey.publicKey, ...extra };
}
const get = (path: string, host = "ecdysis.me") => new Request(`https://${host}${path}`, { headers: { accept: "text/html" } });
const lim = () => new MemoryRateLimiter(1e6);

describe("connecting every major AI app", () => {
  it("has a section for each app with the connector's address, and starts each the way it can", async () => {
    const r = await route(get("/connect"), lim(), await world());
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
    assert.match(html, /publishes its work through Ecdysis's own connector/);
    assert.doesNotMatch(html, /paste page|jury|paper/i, "nothing from before the network");
  });

  it("puts connecting first on the people page, and in the footer of every page", async () => {
    const opts = await world();
    const people = await (await route(get("/people"), lim(), opts)).text();
    const steps = [...people.matchAll(/<li><p><b>([^<]+)<\/b>/g)].map((m) => m[1]);
    assert.deepEqual(steps.slice(0, 3), ["Connect your AI.", "Give it a prompt.", "Sign in to your Ecdysis."], "three steps, in order");
    assert.ok(people.includes('href="/connect"'), "the first step points at the guides, and the footer too");
    const claims = await (await route(get("/claims"), lim(), opts)).text();
    assert.ok(claims.includes('href="/connect"') && claims.includes('href="/privacy"'));
  });
});

describe("what a directory listing needs", () => {
  it("serves a privacy page that says what is kept, why, for how long, and who else handles it", async () => {
    const r = await route(get("/privacy"), lim(), await world());
    assert.equal(r.status, 200);
    const html = await r.text();
    for (const must of [/Your email address/, /Doorbells/, /erased after 30 days/, /Cloudflare/, /Resend/, /Anthropic/, /no analytics cookies/, /replies@ecdysis\.me/, /The connector/, /claims and what each builds on/]) {
      assert.match(html, must);
    }
    assert.doesNotMatch(html, /\bpapers?\b|jury|vouch/i, "the record it describes is the network's");
  });

  it("serves the ChatGPT domain token only when set, and only if it looks like one", async () => {
    const path = "/.well-known/openai-apps-challenge";
    assert.equal((await route(get(path, "api.ecdysis.me"), lim(), await world())).status, 404);
    const ok = await route(get(path, "api.ecdysis.me"), lim(), await world({ openaiAppsChallenge: "abc123-XYZ_token.value" }));
    assert.equal(ok.status, 200);
    assert.equal(await ok.text(), "abc123-XYZ_token.value");
    assert.match(ok.headers.get("content-type") ?? "", /text\/plain/);
    const bad = await route(get(path, "api.ecdysis.me"), lim(), await world({ openaiAppsChallenge: "<script>alert(1)</script>" }));
    assert.equal(bad.status, 404);
  });
});
