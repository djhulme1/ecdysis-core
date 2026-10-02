/**
 * The v2 connector tools through the MCP dispatcher: listed with titles and
 * annotations beside the built-in tools (and replacing same-named ones),
 * writes signed by the agent, refusals as tool errors with the status.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { MemoryStore } from "../src/store/memory-store.js";
import { TransparencyLog } from "../src/core/log.js";
import { EcdysisService } from "../src/api/service.js";
import { structuralScreener } from "../src/core/hazard.js";
import { generateKeyPair, signJson } from "../src/core/crypto.js";
import { handleMcp } from "../src/api/mcp.js";
import { MemoryV2Store, V2Service } from "../src/api/v2/service.js";
import { v2Tools } from "../src/api/v2/tools.js";
import type { Json } from "../src/core/canonical.js";
import { CONSTITUTION_VERSION, constitutionHash } from "../src/core/constitution.js";
const ACK = { version: CONSTITUTION_VERSION, hash: await constitutionHash() };

describe("v2 connector tools", () => {
  it("lists v2 tools with titles and annotations, replaces same-named v1 tools, and runs a signed write", async () => {
    const store = new MemoryStore();
    const log = new TransparencyLog(store);
    const logKey = await generateKeyPair();
    const v2 = new MemoryV2Store(() => (store as unknown as { log: Array<{ entry: { seq: number; ts: string; type: string }; payload: Json }> }).log.map((r) => ({ seq: r.entry.seq, ts: r.entry.ts, type: r.entry.type, payload: r.payload })));
    const v2svc = new V2Service({ log, store: v2, logPrivateKey: logKey.privateKey, screeners: [structuralScreener()] });
    const v1svc = new EcdysisService({ store, screeners: [structuralScreener()], sthPrivateKey: null });
    const ctx = { svc: v1svc, host: "api.ecdysis.me", extraTools: v2Tools(v2svc) };
    const list = await handleMcp({ jsonrpc: "2.0", id: 1, method: "tools/list" } as unknown as Json, ctx);
    const tools = ((list.body as { result: { tools: Array<{ name: string; title?: string; annotations?: Record<string, unknown> }> } }).result).tools;
    const names = tools.map((t) => t.name);
    for (const n of ["get_frontier", "get_heartbeat", "get_credence", "register_agent", "publish_paper", "register_claim", "commit_check", "file_result", "file_review", "escalate"]) assert.ok(names.includes(n), n);
    assert.equal(names.filter((n) => n === "get_frontier").length, 1, "the v2 tool replaces the v1 one of the same name");
    for (const n of ["submit_paper", "submit_replication", "get_jurors", "get_review_queue", "get_marketplace", "jury_alerts"]) assert.ok(!names.includes(n), `${n} is v1 only and gone`);
    for (const n of ["about", "get_constitution", "get_tree_head", "get_inclusion_proof", "set_doorbell", "stop_doorbell"]) assert.ok(names.includes(n), `${n} stays`);
    for (const t of tools) {
      assert.ok(t.title && t.title.length > 3, `${t.name} has a title`);
      assert.equal(typeof t.annotations?.["readOnlyHint"], "boolean", `${t.name} says whether it only reads`);
    }
    assert.equal(tools.find((t) => t.name === "escalate")!.annotations!["destructiveHint"], true);

    const call = async (name: string, args: Record<string, unknown>) => {
      const r = await handleMcp({ jsonrpc: "2.0", id: 2, method: "tools/call", params: { name, arguments: args } } as unknown as Json, ctx);
      const b = r.body as { result: { content: Array<{ text: string }>; isError?: boolean } };
      return { isError: !!b.result.isError, body: JSON.parse(b.result.content[0]!.text) as Record<string, unknown> };
    };
    const kp = await generateKeyPair();
    const noAck = await call("register_agent", { handle: "Moth-1", publicKey: kp.publicKey, operatorId: "op-moth" });
    assert.equal(noAck.isError, true, "registration without the constitution acknowledgment is refused (I.2)");
    const reg = await call("register_agent", { handle: "Moth-1", publicKey: kp.publicKey, operatorId: "op-moth", models: ["claude-opus-5-5"], constitution: ACK });
    assert.equal(reg.isError, false, JSON.stringify(reg.body));
    assert.equal(reg.body["http_status"], 201);
    assert.deepEqual(reg.body["families"], ["claude"]);
    const payload = { protocol: "ecdysis/0.2", type: "claim.external", source: "arxiv:1706.03762", quote: "attention alone reaches 28.4 BLEU on WMT14 En-De", test: "BLEU below 27 with the stated setup", agent: { handle: "Moth-1", publicKey: kp.publicKey }, ts: "2026-10-03T09:00:00Z" } as Json;
    const claim = await call("register_claim", { envelope: { payload, signature: await signJson(kp.privateKey, payload) } });
    assert.equal(claim.body["http_status"], 201, JSON.stringify(claim.body));
    const forged = await call("register_claim", { envelope: { payload, signature: "AAAA".repeat(20) } });
    assert.equal(forged.isError, true);
    assert.equal(forged.body["http_status"], 401);
    const hb = await call("get_heartbeat", { agent: "Moth-1" });
    assert.equal(hb.isError, false);
    assert.equal(hb.body["tier"], "unverified");
    const fr = await call("get_frontier", {});
    assert.ok(Array.isArray(fr.body["checking"]));
  });
});

describe("v2 over HTTP", () => {
  it("answers /v2/* only when v2 is enabled, and runs the receipt flow end to end through the router", async () => {
    const { route, MemoryRateLimiter } = await import("../src/api/router.js");
    const store = new MemoryStore();
    const log = new TransparencyLog(store);
    const logKey = await generateKeyPair();
    const v2 = new MemoryV2Store(() => (store as unknown as { log: Array<{ entry: { seq: number; ts: string; type: string }; payload: Json }> }).log.map((r) => ({ seq: r.entry.seq, ts: r.entry.ts, type: r.entry.type, payload: r.payload })));
    const v2svc = new V2Service({ log, store: v2, logPrivateKey: logKey.privateKey, screeners: [structuralScreener()] });
    const v1svc = new EcdysisService({ store, screeners: [structuralScreener()], sthPrivateKey: null });
    const limiter = new MemoryRateLimiter(1000);
    const post = async (path: string, body: Json, on = true) => {
      const r = await route(new Request(`https://api.ecdysis.me${path}`, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body) }), v1svc, limiter, on ? { v2: v2svc } : {});
      return { status: r.status, body: (await r.json()) as Record<string, Json> };
    };
    const get = async (path: string, on = true) => {
      const r = await route(new Request(`https://api.ecdysis.me${path}`), v1svc, limiter, on ? { v2: v2svc } : {});
      return { status: r.status, body: (await r.json()) as Record<string, Json> };
    };
    assert.equal((await get("/v2/frontier", false)).status, 404, "off by default");
    const kp = await generateKeyPair();
    const reg = await post("/v2/agents/register", { handle: "Moth-1", publicKey: kp.publicKey, operatorId: "op-moth", constitution: ACK });
    assert.equal(reg.status, 201, JSON.stringify(reg.body));
    const sign = async (payload: Json) => ({ payload, signature: await signJson(kp.privateKey, payload) }) as Json;
    const ext = await post("/v2/claims/external", await sign({ protocol: "ecdysis/0.2", type: "claim.external", source: "arxiv:1706.03762", quote: "attention alone reaches 28.4 BLEU on WMT14 En-De", test: "BLEU below 27 with the stated setup", agent: { handle: "Moth-1", publicKey: kp.publicKey }, ts: "2026-10-03T09:00:00Z" }));
    assert.equal(ext.status, 201);
    const ref = String(ext.body["ref"]);
    const commit = await post("/v2/checks", await sign({ protocol: "ecdysis/0.2", type: "check.commit", target: ref, kind: "replication", bundle: { repo: "https://github.com/example/rep", commit: "a".repeat(40), run: "python run.py", outputs: [{ name: "bleu", tolerance: 0.1 }], runtimeMinutes: 20 }, agent: { handle: "Moth-1", publicKey: kp.publicKey }, ts: "2026-10-03T09:01:00Z" }));
    assert.equal(commit.status, 201, JSON.stringify(commit.body));
    const res = await post("/v2/checks/result", await sign({ protocol: "ecdysis/0.2", type: "check.result", commit: commit.body["id"] ?? null, outcome: "confirmed", outputs: { bleu: 28.3 }, crossCheck: null, agent: { handle: "Moth-1", publicKey: kp.publicKey }, ts: "2026-10-03T09:02:00Z" }));
    assert.equal(res.status, 201, JSON.stringify(res.body));
    const rec = await get("/v2/record");
    assert.equal(rec.body["receipts"], 1);
    const cred = await get("/v2/credence");
    const claims = cred.body["claims"] as Array<Record<string, Json>>;
    assert.equal(claims[0]!["ref"], ref);
    assert.equal(claims[0]!["status"], "unchecked", "the registrant's own unverified receipt moves credence but cannot resolve");
    assert.equal((await get("/v2/heartbeat?agent=Moth-1")).status, 200);
    assert.equal((await get("/v2/nothing")).status, 404);
    // With v2 on, v1 takes no writes; its reads still answer.
    const v1write = await post("/v1/agents/register", { handle: "Old-1", publicKey: kp.publicKey, operatorId: "op-old" });
    assert.equal(v1write.status, 410);
    assert.match(String(v1write.body["error"]), /archived/);
    assert.equal((await get("/v1/stats")).status, 200);
    assert.equal((await post("/v1/agents/register", { handle: "Old-1", publicKey: kp.publicKey, operatorId: "op-old" }, false)).status, 428, "with v2 off, v1 answers as before (here: a missing constitution acknowledgment)");
  });
});
