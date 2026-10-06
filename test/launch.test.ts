/**
 * One click from a prompt to an AI app (/o/<app>/<prompt>), and from the MCP
 * server into an AI tool (/o/<tool>/mcp).
 *
 * Guarantees: each button opens exactly the prompt its page shows, typed in
 * and never sent by us; every prompt fits the app's link limit; the target
 * is built from fixed parts, so the route is never an open redirect; app
 * schemes land on a script-free page that says what to do if nothing
 * happens; MCP install links carry exactly the server's address; and each
 * click is counted by app and prompt only.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { MemoryRateLimiter, route, type RouteOptions } from "../src/api/router.js";
import { MemoryStore } from "../src/store/memory-store.js";
import { TransparencyLog } from "../src/core/log.js";
import { generateKeyPair } from "../src/core/crypto.js";
import { MemoryV2Store, V2Service } from "../src/api/v2/service.js";
import { PagesHandler } from "../src/api/v2/pages.js";
import { appsFor, PROMPT_APPS, type PromptApp } from "../src/web/launch.js";
import { starterTextV2, STARTERS_V2 } from "../src/web/starters.js";
import { esc } from "../src/web/design.js";
import type { Json } from "../src/core/canonical.js";

async function world() {
  const now = () => new Date(Date.UTC(2026, 9, 5, 12, 0, 0));
  const store = new MemoryStore();
  const log = new TransparencyLog(store, now);
  const logKey = await generateKeyPair();
  const v2store = new MemoryV2Store(() => (store as unknown as { log: Array<{ entry: { seq: number; ts: string; type: string }; payload: Json }> }).log.map((r) => ({ seq: r.entry.seq, ts: r.entry.ts, type: r.entry.type, payload: r.payload })));
  const svc = new V2Service({ log, store: v2store, logPrivateKey: logKey.privateKey, now });
  const pages = new PagesHandler(svc, { host: "ecdysis.me", logPublicKey: logKey.publicKey });
  const counts = new Map<string, number>();
  const opts: RouteOptions = { v2: svc, pages, sthPublicKey: logKey.publicKey, count: async (keys) => { for (const k of keys) counts.set(k, (counts.get(k) ?? 0) + 1); } };
  return { opts, counts };
}
const get = (path: string, headers: Record<string, string> = {}) =>
  new Request(`https://ecdysis.me${path}`, { headers: { accept: "text/html", ...headers } });
const lim = () => new MemoryRateLimiter(1e6);
const base = "https://ecdysis.me";
const unescape = (s: string) => s.replace(/&#39;/g, "'").replace(/&quot;/g, '"').replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&amp;/g, "&");

describe("Open in: prompts into AI apps", () => {
  it("every prompt fits every app it is offered in, and speaks of claims, never papers", () => {
    for (const id of STARTERS_V2) {
      const text = starterTextV2(id, base);
      assert.ok(text.length > 40, id);
      for (const app of appsFor(id)) assert.ok(text.length <= PROMPT_APPS[app].max, `${id} is too long for ${app}`);
      assert.doesNotMatch(text, /\bpapers?\b/i, `${id}: no papers`);
      assert.doesNotMatch(text, /\b(jury|juror|challenge|vouch)/i, `${id}: nothing from before the network`);
    }
  });

  it("opens the web apps with exactly the prompt the page shows, typed in", async () => {
    const { opts } = await world();
    const people = await (await route(get("/people"), lim(), opts)).text();
    for (const id of ["famous", "field", "new"] as const) {
      const text = starterTextV2(id, base);
      assert.ok(people.includes(esc(text)), `/people shows the ${id} prompt`);
      assert.ok(people.includes(`href="/o/claude/${id}"`), `/people offers ${id} in Claude`);
      for (const app of ["claude", "chatgpt", "grok"] as PromptApp[]) {
        const r = await route(get(`/o/${app}/${id}`), lim(), opts);
        assert.equal(r.status, 302, `${app}/${id}`);
        const to = new URL(r.headers.get("location")!);
        assert.equal(to.origin, { claude: "https://claude.ai", chatgpt: "https://chatgpt.com", grok: "https://grok.com" }[app as string]);
        assert.equal(to.searchParams.get("q"), text, "the prompt arrives intact, and nothing else");
        assert.equal(r.headers.get("cache-control"), "no-store");
      }
    }
    const lab = await (await route(get("/lab"), lim(), opts)).text();
    assert.ok(lab.includes(`href="/o/claude-code/lab"`), "the lab brief opens in Claude Code");
    assert.ok(lab.includes(esc(starterTextV2("lab", base)).slice(0, 200)), "and the page shows the brief it opens");
  });

  it("opens Claude Code through a script-free page that says what to do if nothing happens", async () => {
    const { opts } = await world();
    const r = await route(get("/o/claude-code/famous"), lim(), opts);
    assert.equal(r.status, 200);
    assert.ok(!(r.headers.get("content-security-policy") ?? "").includes("script-src"));
    assert.match(r.headers.get("x-robots-tag") ?? "", /noindex/);
    const html = await r.text();
    assert.ok(!html.includes("<script"));
    const refresh = unescape(html.match(/http-equiv="refresh" content="0;url=([^"]+)"/)![1]!);
    assert.ok(!/[!'()*]/.test(refresh), "strictly encoded: no app's link parser trips on an apostrophe");
    assert.ok(refresh.startsWith("claude-cli://open?q="));
    const q = new URL(refresh.replace("claude-cli://open", "https://x.invalid/open")).searchParams.get("q");
    assert.equal(q, starterTextV2("famous", base));
    assert.match(html, /If nothing happens/);
    assert.match(html, /run once/);
  });

  it("is never an open redirect: unknown apps, prompts and shapes are 404s", async () => {
    const { opts } = await world();
    for (const p of ["/o/evil/famous", "/o/claude/nope", "/o/claude/famous/extra", "/o/claude/..%2F..%2Fevil", "/o/https:/x.com", "/o/claude", "/o/claude/FAMOUS", "/o/claude/paste", "/o/claude/juror", "/o/claude/volunteer"]) {
      const r = await route(get(p), lim(), opts);
      assert.ok(r.status === 404 || !r.headers.get("location"), `${p}: ${r.status}`);
    }
  });
});

describe("Add to: the MCP server into AI tools", () => {
  it("builds each tool's official install link with exactly the server's address", async () => {
    const { opts } = await world();
    const page = async (tool: string) => (await (await route(get(`/o/${tool}/mcp`), lim(), opts)).text());
    const target = (html: string) => unescape(html.match(/http-equiv="refresh" content="0;url=([^"]+)"/)![1]!);
    const cursor = target(await page("cursor"));
    assert.ok(cursor.startsWith("cursor://anysphere.cursor-deeplink/mcp/install?name=ecdysis&config="));
    assert.deepEqual(JSON.parse(atob(decodeURIComponent(cursor.split("config=")[1]!))), { url: "https://api.ecdysis.me/mcp" });
    const vscode = target(await page("vscode"));
    assert.ok(vscode.startsWith("vscode:mcp/install?"));
    assert.deepEqual(JSON.parse(decodeURIComponent(vscode.split("?")[1]!)), { name: "ecdysis", type: "http", url: "https://api.ecdysis.me/mcp" });
    const lm = target(await page("lmstudio"));
    assert.ok(lm.startsWith("lmstudio://add_mcp?name=ecdysis&config="));
    assert.deepEqual(JSON.parse(atob(decodeURIComponent(lm.split("config=")[1]!))), { url: "https://api.ecdysis.me/mcp" });
    assert.match(await page("cursor"), /mcp\.json/, "and how to add it by hand");
    const connect = await (await route(get("/connect"), lim(), opts)).text();
    for (const tool of ["cursor", "vscode", "lmstudio"]) assert.ok(connect.includes(`href="/o/${tool}/mcp"`));
    assert.match(connect, /claude mcp add --transport http --scope user ecdysis https:\/\/api\.ecdysis\.me\/mcp/, "in every project, not only the one it was added in");
    assert.match(connect, /Add custom connector/);
    const people = await (await route(get("/people"), lim(), opts)).text();
    assert.ok(people.includes(`href="/connect"`), "step 1 on the people page points to the connection guides");
    const agents = await (await route(get("/agents"), lim(), opts)).text();
    assert.ok(agents.includes("https://api.ecdysis.me/mcp"), "the agents' door names the connector");
  });
});

describe("counting launches", () => {
  it("counts each press by app and prompt only, and never a HEAD or a probe", async () => {
    const { opts, counts } = await world();
    await route(get("/o/claude/famous"), lim(), opts);
    await route(get("/o/claude/famous"), lim(), opts);
    await route(get("/o/cursor/mcp"), lim(), opts);
    await route(new Request("https://ecdysis.me/o/chatgpt/famous", { method: "HEAD" }), lim(), opts);
    await route(get("/o/chatgpt/famous", { "x-ecdysis-probe": "1" }), lim(), opts);
    await route(get("/o/claude/nope"), lim(), opts);
    const day = new Date().toISOString().slice(0, 10);
    const n = (k: string) => counts.get(`op:${day}:${k}`) ?? 0;
    assert.equal(n("claude:famous"), 2);
    assert.equal(n("cursor:mcp"), 1);
    assert.equal(n("chatgpt:famous"), 0);
    assert.equal(n("claude:nope"), 0, "a miss is not a launch");
    assert.ok([...counts.keys()].every((k) => /^op:\d{4}-\d{2}-\d{2}:[a-z-]+:[a-z-]+$/.test(k)), "a fixed vocabulary, nothing else");
  });
});
