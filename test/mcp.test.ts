/**
 * The MCP endpoint, the challenge board, and the live badges: the
 * any-model on-ramps. All read-only; all must survive read-only mode.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { MemoryRateLimiter, route } from "../src/api/router.js";
import { EcdysisService } from "../src/api/service.js";
import { MemoryStore } from "../src/store/memory-store.js";
import { structuralScreener } from "../src/core/hazard.js";

function makeSvc(): EcdysisService {
  return new EcdysisService({
    store: new MemoryStore(),
    screeners: [structuralScreener()],
    sthPrivateKey: null,
  });
}

const limiter = () => new MemoryRateLimiter(1000);

function rpc(body: unknown): Request {
  return new Request("https://api.ecdysis.me/mcp", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
}

describe("MCP endpoint", () => {
  it("initializes, lists tools, and answers calls", async () => {
    const svc = makeSvc();

    const init = await route(rpc({ jsonrpc: "2.0", id: 1, method: "initialize", params: { protocolVersion: "2025-06-18", capabilities: {}, clientInfo: { name: "t", version: "0" } } }), svc, limiter());
    assert.equal(init.status, 200);
    const initBody = (await init.json()) as { result: { protocolVersion: string; capabilities: { tools: object }; serverInfo: { name: string } } };
    assert.equal(initBody.result.protocolVersion, "2025-06-18");
    assert.equal(initBody.result.serverInfo.name, "ecdysis");
    assert.ok(initBody.result.capabilities.tools);

    const list = await route(rpc({ jsonrpc: "2.0", id: 2, method: "tools/list" }), svc, limiter());
    const tools = ((await list.json()) as { result: { tools: Array<{ name: string }> } }).result.tools.map((t) => t.name);
    for (const expected of ["about", "get_frontier", "get_challenges", "get_tree_head", "how_to_join"]) {
      assert.ok(tools.includes(expected), `missing tool ${expected}`);
    }

    const about = await route(rpc({ jsonrpc: "2.0", id: 3, method: "tools/call", params: { name: "about", arguments: {} } }), svc, limiter());
    const aboutBody = (await about.json()) as { result: { content: Array<{ type: string; text: string }> } };
    assert.match(aboutBody.result.content[0]!.text, /machine science/);
    assert.match(aboutBody.result.content[0]!.text, /data, never instructions/);

    const ch = await route(rpc({ jsonrpc: "2.0", id: 4, method: "tools/call", params: { name: "get_challenges", arguments: {} } }), svc, limiter());
    const chBody = (await ch.json()) as { result: { content: Array<{ text: string }> } };
    assert.match(chBody.result.content[0]!.text, /grokking/i);
    assert.match(chBody.result.content[0]!.text, /replicates/);
  });

  it("handles notifications, unknown methods and unknown tools correctly", async () => {
    const svc = makeSvc();

    const note = await route(rpc({ jsonrpc: "2.0", method: "notifications/initialized" }), svc, limiter());
    assert.equal(note.status, 202);

    const bad = await route(rpc({ jsonrpc: "2.0", id: 9, method: "no/such" }), svc, limiter());
    const badBody = (await bad.json()) as { error: { code: number } };
    assert.equal(badBody.error.code, -32601);

    const badTool = await route(rpc({ jsonrpc: "2.0", id: 10, method: "tools/call", params: { name: "write_everything" } }), svc, limiter());
    const badToolBody = (await badTool.json()) as { error: { code: number } };
    assert.equal(badToolBody.error.code, -32602);

    const get = await route(new Request("https://api.ecdysis.me/mcp"), svc, limiter());
    assert.equal(get.status, 405);
  });

  it("stays up in read-only mode, because its tools only read", async () => {
    const svc = makeSvc();
    const r = await route(rpc({ jsonrpc: "2.0", id: 1, method: "tools/list" }), svc, limiter(), { readOnly: true });
    assert.equal(r.status, 200);
  });
});

describe("challenge board and badges", () => {
  it("serves the challenge board with honest framing", async () => {
    const svc = makeSvc();
    const r = await route(new Request("https://api.ecdysis.me/v1/challenges"), svc, limiter());
    assert.equal(r.status, 200);
    const b = (await r.json()) as { note: string; challenges: Array<{ parent: string; rel: string }> };
    assert.match(b.note, /not log entries/);
    assert.ok(b.challenges.length >= 8);
    for (const c of b.challenges) {
      assert.match(c.parent, /^(arxiv|doi):/);
      assert.ok(["replicates", "refutes"].includes(c.rel));
    }
  });

  it("serves live SVG badges", async () => {
    const svc = makeSvc();
    const sth = await route(new Request("https://api.ecdysis.me/badge/sth.svg"), svc, limiter());
    assert.equal(sth.status, 200);
    assert.match(sth.headers.get("content-type") ?? "", /image\/svg/);
    assert.match(await sth.text(), /entr/);

    const agent = await route(new Request("https://api.ecdysis.me/badge/agent/Nobody-7.svg"), svc, limiter());
    assert.match(await agent.text(), /unregistered/);

    const evil = await route(new Request("https://api.ecdysis.me/badge/agent/%3Cscript%3E.svg"), svc, limiter());
    const evilBody = await evil.text();
    assert.ok(!evilBody.includes("<script"), "handle is never interpolated unescaped");
  });
});
