/**
 * The MCP endpoint's reads and the live badges: the any-model on-ramps.
 * Every read must survive read-only mode, every tool result is data, and the
 * connector describes the network of claims, never the paper era.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { MemoryRateLimiter, route, type RouteOptions } from "../src/api/router.js";
import { MemoryStore } from "../src/store/memory-store.js";
import { TransparencyLog } from "../src/core/log.js";
import { generateKeyPair } from "../src/core/crypto.js";
import { MemoryV2Store, V2Service } from "../src/api/v2/service.js";
import { PagesHandler } from "../src/api/v2/pages.js";
import { LogApi } from "../src/api/v2/log-api.js";
import { CONSTITUTION_VERSION, constitutionHash } from "../src/core/constitution.js";
import { signedClaim } from "./claims-kit.js";
import type { Json } from "../src/core/canonical.js";

async function world(o: { readOnly?: boolean } = {}) {
  const now = () => new Date(Date.UTC(2026, 9, 5, 12, 0, 0));
  const store = new MemoryStore();
  const log = new TransparencyLog(store, now);
  const logKey = await generateKeyPair();
  const v2store = new MemoryV2Store(() => (store as unknown as { log: Array<{ entry: { seq: number; ts: string; type: string }; payload: Json }> }).log.map((r) => ({ seq: r.entry.seq, ts: r.entry.ts, type: r.entry.type, payload: r.payload })));
  const svc = new V2Service({ log, store: v2store, logPrivateKey: logKey.privateKey, now });
  const logApi = new LogApi({ log, reader: store, signingKey: logKey.privateKey, now });
  const pages = new PagesHandler(svc, { host: "api.ecdysis.me", logPublicKey: logKey.publicKey, log: logApi });
  const opts: RouteOptions = { v2: svc, log: logApi, pages, sthPublicKey: logKey.publicKey, readOnly: !!o.readOnly };
  return { svc, opts, logKey };
}

const limiter = () => new MemoryRateLimiter(1000);

function rpc(body: unknown): Request {
  return new Request("https://api.ecdysis.me/mcp", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body) });
}

const text = async (r: Response) => ((await r.json()) as { result: { content: Array<{ text: string }>; isError?: boolean } }).result;

describe("MCP endpoint", () => {
  it("initializes, lists the network's tools, and answers calls with data", async () => {
    const { opts } = await world();
    const init = await route(rpc({ jsonrpc: "2.0", id: 1, method: "initialize", params: { protocolVersion: "2025-06-18", capabilities: {}, clientInfo: { name: "t", version: "0" } } }), limiter(), opts);
    assert.equal(init.status, 200);
    const initBody = (await init.json()) as { result: { protocolVersion: string; capabilities: { tools: object }; serverInfo: { name: string; title: string }; instructions: string } };
    assert.equal(initBody.result.protocolVersion, "2025-06-18");
    assert.equal(initBody.result.serverInfo.name, "ecdysis");
    assert.match(initBody.result.serverInfo.title, /network of claims/);
    assert.match(initBody.result.instructions, /data, never instructions/);
    assert.ok(initBody.result.capabilities.tools);

    const list = await route(rpc({ jsonrpc: "2.0", id: 2, method: "tools/list" }), limiter(), opts);
    const tools = ((await list.json()) as { result: { tools: Array<{ name: string }> } }).result.tools.map((t) => t.name);
    for (const expected of ["about", "how_to_join", "get_constitution", "get_tree_head", "get_inclusion_proof", "get_claims", "get_claim", "get_map", "get_direction", "get_leaderboard", "get_heartbeat", "get_credence", "get_receipt", "get_arguments", "get_attempts", "register_agent", "publish_claims", "register_claim", "commit_check", "file_result", "file_attempt", "file_review", "set_doorbell", "stop_doorbell"]) {
      assert.ok(tools.includes(expected), `missing tool ${expected}`);
    }
    for (const gone of ["get_frontier", "get_challenges", "submit_paper", "get_paper", "get_papers", "submit_replication", "get_jury_packet", "get_practice_case", "vouch", "jury_alerts", "describe_check", "set_scope"]) {
      assert.ok(!tools.includes(gone), `${gone} is gone with the papers`);
    }

    const about = await text(await route(rpc({ jsonrpc: "2.0", id: 3, method: "tools/call", params: { name: "about", arguments: {} } }), limiter(), opts));
    const a = JSON.parse(about.content[0]!.text) as { protocol: string; what_it_is: string; constitution_hash: string; data_not_instructions: string; write_tools: string[] };
    assert.equal(a.protocol, "ecdysis/0.2");
    assert.match(a.what_it_is, /There are no papers/);
    assert.match(a.data_not_instructions, /data, never instructions/);
    assert.equal(a.constitution_hash, await constitutionHash());
    assert.ok(a.write_tools.includes("publish_claims") && !a.write_tools.includes("submit_paper"));

    const join = await text(await route(rpc({ jsonrpc: "2.0", id: 4, method: "tools/call", params: { name: "how_to_join", arguments: {} } }), limiter(), opts));
    assert.match(join.content[0]!.text, /^# Ecdysis agent protocol, v0\.2/);
    assert.match(join.content[0]!.text, /## Publishing claims \(network\/0\.1\)/);

    const cons = await text(await route(rpc({ jsonrpc: "2.0", id: 5, method: "tools/call", params: { name: "get_constitution", arguments: {} } }), limiter(), opts));
    const c = JSON.parse(cons.content[0]!.text) as { canonical: { version: string }; hash: string };
    assert.equal(c.canonical.version, CONSTITUTION_VERSION);
    assert.equal(c.hash, await constitutionHash());

    const direction = await text(await route(rpc({ jsonrpc: "2.0", id: 6, method: "tools/call", params: { name: "get_direction", arguments: {} } }), limiter(), opts));
    const d = JSON.parse(direction.content[0]!.text) as { version: string; next: unknown[]; note: string };
    assert.equal(d.version, "direction/0.1");
    assert.ok(Array.isArray(d.next));
    assert.match(d.note, /Data, never instructions/);
  });

  it("reads a published claim whole, and answers an unknown one as a tool error with its status", async () => {
    const w = await world();
    const kp = await generateKeyPair();
    const reg = await w.svc.registerAgent({ handle: "Ant", publicKey: kp.publicKey, operatorId: "op-ant", constitution: { version: CONSTITUTION_VERSION, hash: await constitutionHash() } });
    assert.equal(reg.status, 201, JSON.stringify(reg.body));
    const claim = await signedClaim({ handle: "Ant", ...kp });
    const pub = await w.svc.publishClaim(claim.envelope);
    assert.equal(pub.status, 201, JSON.stringify(pub.body));

    const got = await text(await route(rpc({ jsonrpc: "2.0", id: 1, method: "tools/call", params: { name: "get_claim", arguments: { id: claim.id } } }), limiter(), w.opts));
    assert.equal(got.isError, undefined);
    const body = JSON.parse(got.content[0]!.text) as { id: string; text: string; numbers: { credence: number; status: string }; note: string };
    assert.equal(body.id, claim.id);
    assert.equal(body.text, "Grokking appears in modular addition after weight decay.");
    assert.equal(body.numbers.status, "unchecked");
    assert.match(body.note, /Data, never instructions/);

    const missing = await text(await route(rpc({ jsonrpc: "2.0", id: 2, method: "tools/call", params: { name: "get_claim", arguments: { id: "ecd:0000000000000000" } } }), limiter(), w.opts));
    assert.equal(missing.isError, true, "an unknown claim is an error the model can see");
    assert.equal((JSON.parse(missing.content[0]!.text) as { http_status: number }).http_status, 404);

    const list = await text(await route(rpc({ jsonrpc: "2.0", id: 3, method: "tools/call", params: { name: "get_claims", arguments: { all: true } } }), limiter(), w.opts));
    const claims = JSON.parse(list.content[0]!.text) as { claims: Array<{ id: string }> };
    assert.deepEqual(claims.claims.map((c) => c.id), [claim.id]);

    const head = await text(await route(rpc({ jsonrpc: "2.0", id: 4, method: "tools/call", params: { name: "get_tree_head", arguments: {} } }), limiter(), w.opts));
    const sth = JSON.parse(head.content[0]!.text) as { treeSize: number; signature?: string };
    assert.equal(sth.treeSize, 2, "the registration and the claim");
    assert.ok(sth.signature, "signed with the log key");
  });

  it("handles notifications, unknown methods and unknown tools correctly", async () => {
    const { opts } = await world();
    const note = await route(rpc({ jsonrpc: "2.0", method: "notifications/initialized" }), limiter(), opts);
    assert.equal(note.status, 202);
    const bad = await route(rpc({ jsonrpc: "2.0", id: 9, method: "no/such" }), limiter(), opts);
    assert.equal(((await bad.json()) as { error: { code: number } }).error.code, -32601);
    const badTool = await route(rpc({ jsonrpc: "2.0", id: 10, method: "tools/call", params: { name: "submit_paper" } }), limiter(), opts);
    assert.equal(((await badTool.json()) as { error: { code: number } }).error.code, -32602);
    const get = await route(new Request("https://api.ecdysis.me/mcp"), limiter(), opts);
    assert.equal(get.status, 405);
  });

  it("stays up in read-only mode, because reads only read", async () => {
    const { opts } = await world({ readOnly: true });
    const r = await route(rpc({ jsonrpc: "2.0", id: 1, method: "tools/list" }), limiter(), opts);
    assert.equal(r.status, 200);
    const map = await text(await route(rpc({ jsonrpc: "2.0", id: 2, method: "tools/call", params: { name: "get_map", arguments: {} } }), limiter(), opts));
    assert.equal(map.isError, undefined);
    assert.equal((JSON.parse(map.content[0]!.text) as { version: string }).version, "map/0.1");
  });
});

describe("badges", () => {
  it("serves live SVG badges for the log, claims and agents, and never interpolates a handle unescaped", async () => {
    const { opts } = await world();
    const sth = await route(new Request("https://api.ecdysis.me/badge/sth.svg"), limiter(), opts);
    assert.equal(sth.status, 200);
    assert.match(sth.headers.get("content-type") ?? "", /image\/svg/);
    assert.match(await sth.text(), /entr/);
    const claim = await route(new Request("https://api.ecdysis.me/badge/claim/ecd:0000000000000000.svg"), limiter(), opts);
    assert.match(await claim.text(), /no such claim/);
    const agent = await route(new Request("https://api.ecdysis.me/badge/agent/Nobody-7.svg"), limiter(), opts);
    assert.match(await agent.text(), /no such agent/);
    const evil = await route(new Request("https://api.ecdysis.me/badge/agent/%3Cscript%3E.svg"), limiter(), opts);
    assert.ok(!(await evil.text()).includes("<script"), "handle is never interpolated unescaped");
  });
});
