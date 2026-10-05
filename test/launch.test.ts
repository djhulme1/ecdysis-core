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
import { MemoryRateLimiter, route } from "../src/api/router.js";
import { MemoryStore } from "../src/store/memory-store.js";
import { structuralScreener } from "../src/core/hazard.js";
import { CONSTITUTION_VERSION, constitutionHash } from "../src/core/constitution.js";
import { appsFor, PROMPT_APPS, type PromptApp } from "../src/web/launch.js";
import { starterText, STARTERS } from "../src/web/starters.js";
import { esc } from "../src/web/design.js";

const world = () => {
  const store = new MemoryStore();
  return { store, svc: new EcdysisService({ store, screeners: [structuralScreener()], sthPrivateKey: null }) };
};
const get = (path: string, headers: Record<string, string> = {}) =>
  new Request(`https://ecdysis.me${path}`, { headers: { accept: "text/html", ...headers } });
const lim = () => new MemoryRateLimiter(1e6);
const base = "https://ecdysis.me";
const unescape = (s: string) => s.replace(/&#39;/g, "'").replace(/&quot;/g, '"').replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&amp;/g, "&");

describe("Open in: prompts into AI apps", () => {
  it("every prompt fits every app it is offered in", async () => {
    const constitution = { version: CONSTITUTION_VERSION, hash: await constitutionHash() };
    for (const id of STARTERS) {
      const text = starterText(id, base, constitution);
      assert.ok(text.length > 40, id);
      for (const app of appsFor(id)) assert.ok(text.length <= PROMPT_APPS[app].max, `${id} is too long for ${app}`);
    }
  });

  it("opens the web apps with exactly the prompt the page shows, typed in", async () => {
    const { svc } = world();
    const people = await (await route(get("/people"), svc, lim())).text();
    const constitution = { version: CONSTITUTION_VERSION, hash: await constitutionHash() };
    for (const id of ["famous", "field", "new", "volunteer", "juror", "alerts", "paste", "handoff", "build-tool", "one-line"] as const) {
      const text = starterText(id, base, constitution);
      assert.ok(people.includes(esc(text)), `/people shows the ${id} prompt`);
      assert.ok(people.includes(`href="/o/claude/${id}"`), `/people offers ${id} in Claude`);
      for (const app of ["claude", "chatgpt", "grok"] as PromptApp[]) {
        const r = await route(get(`/o/${app}/${id}`), svc, lim());
        assert.equal(r.status, 302, `${app}/${id}`);
        const to = new URL(r.headers.get("location")!);
        assert.equal(to.origin, { claude: "https://claude.ai", chatgpt: "https://chatgpt.com", grok: "https://grok.com" }[app as string]);
        assert.equal(to.searchParams.get("q"), text, "the prompt arrives intact, and nothing else");
        assert.equal(r.headers.get("cache-control"), "no-store");
      }
    }
    const review = await (await route(get("/review"), svc, lim())).text();
    assert.ok(review.includes(`href="/o/claude/juror"`) && review.includes(`href="/o/claude/volunteer"`));
    const frontier = await (await route(get("/frontier"), svc, lim())).text();
    assert.ok(frontier.includes(`href="/o/claude-code/frontier"`));
  });

  it("opens Claude Code through a script-free page that says what to do if nothing happens", async () => {
    const { svc } = world();
    const r = await route(get("/o/claude-code/famous"), svc, lim());
    assert.equal(r.status, 200);
    assert.ok(!(r.headers.get("content-security-policy") ?? "").includes("script-src"));
    assert.match(r.headers.get("x-robots-tag") ?? "", /noindex/);
    const html = await r.text();
    assert.ok(!html.includes("<script"));
    const refresh = unescape(html.match(/http-equiv="refresh" content="0;url=([^"]+)"/)![1]!);
    assert.ok(!/[!'()*]/.test(refresh), "strictly encoded: no app's link parser trips on an apostrophe");
    assert.ok(refresh.startsWith("claude-cli://open?q="));
    const q = new URL(refresh.replace("claude-cli://open", "https://x.invalid/open")).searchParams.get("q");
    assert.equal(q, starterText("famous", base, { version: CONSTITUTION_VERSION, hash: await constitutionHash() }));
    assert.match(html, /If nothing happens/);
    assert.match(html, /run once/);
    // Prompts written for a walled-in chat AI are not offered in Claude Code.
    assert.equal((await route(get("/o/claude-code/paste"), svc, lim())).status, 404);
  });

  it("is never an open redirect: unknown apps, prompts and shapes are 404s", async () => {
    const { svc } = world();
    for (const p of ["/o/evil/famous", "/o/claude/nope", "/o/claude/famous/extra", "/o/claude/..%2F..%2Fevil", "/o/https:/x.com", "/o/claude", "/o/claude/FAMOUS"]) {
      const r = await route(get(p), svc, lim());
      assert.ok(r.status === 404 || !r.headers.get("location"), `${p}: ${r.status}`);
    }
  });
});

describe("Add to: the MCP server into AI tools", () => {
  it("builds each tool's official install link with exactly the server's address", async () => {
    const { svc } = world();
    const page = async (tool: string) => (await (await route(get(`/o/${tool}/mcp`), svc, lim())).text());
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
    const connect = await (await route(get("/connect"), svc, lim())).text();
    for (const tool of ["cursor", "vscode", "lmstudio"]) assert.ok(connect.includes(`href="/o/${tool}/mcp"`));
    assert.match(connect, /claude mcp add --transport http ecdysis https:\/\/api\.ecdysis\.me\/mcp/);
    assert.match(connect, /Add custom connector/);
    const people = await (await route(get("/people"), svc, lim())).text();
    assert.ok(people.includes(`href="/connect#claude"`), "step 1 on the people page points to each app's steps");
    const agents = await (await route(get("/agents"), svc, lim())).text();
    assert.ok(agents.includes(`href="/o/cursor/mcp"`));
  });
});

describe("counting launches", () => {
  it("counts each press by app and prompt only, and never a HEAD or a probe", async () => {
    const { svc, store } = world();
    await route(get("/o/claude/famous"), svc, lim());
    await route(get("/o/claude/famous"), svc, lim());
    await route(get("/o/cursor/mcp"), svc, lim());
    await route(new Request("https://ecdysis.me/o/chatgpt/famous", { method: "HEAD" }), svc, lim());
    await route(get("/o/chatgpt/famous", { "x-ecdysis-probe": "1" }), svc, lim());
    const day = new Date().toISOString().slice(0, 10);
    const rows = await store.listAccessPrefix("op:");
    const n = (k: string) => rows.find((r) => r.id === `op:${day}:${k}`)?.count ?? 0;
    assert.equal(n("claude:famous"), 2);
    assert.equal(n("cursor:mcp"), 1);
    assert.equal(n("chatgpt:famous"), 0);
    assert.ok(rows.every((r) => /^op:\d{4}-\d{2}-\d{2}:[a-z-]+:[a-z-]+$/.test(r.id)), "a fixed vocabulary, nothing else");
  });
});
