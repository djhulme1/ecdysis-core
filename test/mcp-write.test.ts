/**
 * Writing through the MCP connector: the same signed envelopes, the same
 * service methods and the same checks as the HTTP API, so a connected AI
 * app (or a Claude routine, whose connectors need no network allowlist)
 * can take part without the paste page.
 *
 * Guarantees: every tool carries a title and a read-only or destructive
 * annotation; writes need the agent's own signature (the transport adds no
 * authority); refusals come back as tool errors with the HTTP status; the
 * kill switch refuses every write but a doorbell stop; writes are limited
 * per agent, not per address (an AI app's calls share its servers'
 * addresses); and each write is counted under the API's funnel names,
 * never a probe's.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { MemoryRateLimiter, route } from "../src/api/router.js";
import { EcdysisService } from "../src/api/service.js";
import { Doorbells } from "../src/api/doorbells.js";
import { MemoryStore } from "../src/store/memory-store.js";
import { structuralScreener } from "../src/core/hazard.js";
import { generateKeyPair, signJson, type KeyPairB64 } from "../src/core/crypto.js";
import { CONSTITUTION_VERSION, constitutionHash } from "../src/core/constitution.js";
import type { Json } from "../src/core/canonical.js";

async function world(o: { readOnly?: boolean; limit?: number } = {}) {
  const store = new MemoryStore();
  const log = await generateKeyPair();
  const svc = new EcdysisService({ store, screeners: [structuralScreener()], sthPrivateKey: log.privateKey });
  let n = 3;
  const bells = new Doorbells({
    store, siteBase: "https://ecdysis.me", apiBase: "https://api.ecdysis.me", sthPrivateKey: log.privateKey, sealSecret: null,
    readOnly: !!o.readOnly, now: () => new Date(), random: () => ((n++ * 2654435761) % 4294967296) / 4294967296,
    fetchImpl: (async () => new Response("", { status: 500 })) as typeof fetch,
  });
  // Per-agent writes limited as asked; everything else effectively unlimited, so the test isolates the per-agent bucket.
  const limiter = new MemoryRateLimiter(1000, 60_000, () => Date.now(), { "mcp-agent": o.limit ?? 1000 });
  let id = 0;
  const call = async (name: string, args: Record<string, unknown>, headers: Record<string, string> = {}) => {
    const r = await route(new Request("https://api.ecdysis.me/mcp", {
      method: "POST", headers: { "content-type": "application/json", ...headers },
      body: JSON.stringify({ jsonrpc: "2.0", id: ++id, method: "tools/call", params: { name, arguments: args } }),
    }), svc, limiter, { doorbells: bells, readOnly: !!o.readOnly });
    assert.equal(r.status, 200);
    const b = (await r.json()) as { result: { content: Array<{ text: string }>; isError?: boolean } };
    return { isError: !!b.result.isError, body: JSON.parse(b.result.content[0]!.text) as Record<string, unknown> };
  };
  const ack = { version: CONSTITUTION_VERSION, hash: await constitutionHash() };
  const sign = async (kp: KeyPairB64, handle: string, extra: Record<string, Json>) => {
    const payload = { protocol: "ecdysis/0.1", agent: { handle, publicKey: kp.publicKey }, ts: new Date().toISOString(), ...extra } as Json;
    return { payload, signature: await signJson(kp.privateKey, payload) } as Json;
  };
  return { store, svc, call, ack, sign };
}

const paper = (handle: string, publicKey: string, ts = new Date().toISOString()): Json => ({
  protocol: "ecdysis/0.1", type: "paper",
  title: "A benign measurement of held-out loss on a public benchmark",
  abstract: "We measure a property of a benign benchmark and report the primary metric with seeds and configs attached for replication.",
  field: "ml",
  claims: [{ text: "Held-out loss improves by 3% over the parent baseline", confidence: 0.7 }],
  builds_on: [{ id: "arxiv:1706.03762", rel: "extends", basis: "reviewed", note: "Checked the method and set-up we build on against the published paper." }],
  agent: { handle, publicKey }, ts,
});

describe("MCP tools for the directory", () => {
  it("gives every tool a title and a read-only or destructive annotation, and writes are never marked read-only", async () => {
    const svc = new EcdysisService({ store: new MemoryStore(), screeners: [structuralScreener()], sthPrivateKey: null });
    const r = await route(new Request("https://api.ecdysis.me/mcp", {
      method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ jsonrpc: "2.0", id: 1, method: "tools/list" }),
    }), svc, new MemoryRateLimiter(1000));
    const tools = ((await r.json()) as { result: { tools: Array<{ name: string; title?: string; annotations?: Record<string, unknown> }> } }).result.tools;
    const writes = ["register_agent", "submit_paper", "submit_replication", "file_review", "set_doorbell", "stop_doorbell", "jury_alerts", "get_practice_case", "answer_practice_case"];
    for (const t of tools) {
      assert.ok(t.title && t.title.length > 3, `${t.name} has a title`);
      assert.equal(t.annotations?.["title"], t.title);
      assert.equal(typeof t.annotations?.["readOnlyHint"], "boolean", `${t.name} says whether it only reads`);
      if (!t.annotations?.["readOnlyHint"]) assert.equal(typeof t.annotations?.["destructiveHint"], "boolean", `${t.name} says whether it destroys`);
      assert.equal(t.annotations?.["readOnlyHint"], !writes.includes(t.name), `${t.name}'s read-only hint is honest`);
    }
    for (const w of writes) assert.ok(tools.some((t) => t.name === w), `missing ${w}`);
    assert.equal(tools.find((t) => t.name === "stop_doorbell")!.annotations!["destructiveHint"], true);
    assert.equal(tools.find((t) => t.name === "submit_paper")!.annotations!["destructiveHint"], false);
  });
});

describe("writing through MCP", () => {
  it("registers, submits a signed paper, and refuses a forged or repeated one, as the API does", async () => {
    const w = await world();
    const kp = await generateKeyPair();
    const reg = await w.call("register_agent", { handle: "Wren-1", publicKey: kp.publicKey, operatorId: "op-wren", constitution: w.ack });
    assert.equal(reg.isError, false);
    assert.equal(reg.body["http_status"], 201);
    assert.match(String(reg.body["doorbell"]), /doorbell/);

    const payload = paper("Wren-1", kp.publicKey);
    const env = { payload, signature: await signJson(kp.privateKey, payload) };
    const sub = await w.call("submit_paper", { envelope: env });
    assert.equal(sub.isError, false, JSON.stringify(sub.body));
    assert.equal(sub.body["http_status"], 202);
    assert.match(String(sub.body["track"]), /\/v1\/review\//);

    const again = await w.call("submit_paper", { envelope: env });
    assert.equal(again.isError, true);
    assert.equal(again.body["http_status"], 409);

    // The transport adds no authority: someone else's key is still refused.
    const stranger = await generateKeyPair();
    const forgedPayload = paper("Wren-1", kp.publicKey, new Date(Date.now() + 1000).toISOString());
    const forged = await w.call("submit_paper", { envelope: { payload: forgedPayload, signature: await signJson(stranger.privateKey, forgedPayload) } });
    assert.equal(forged.isError, true);
    assert.equal(forged.body["http_status"], 401);
  });

  it("sets and stops a doorbell, which hands back the person's private link", async () => {
    const w = await world();
    const kp = await generateKeyPair();
    await w.call("register_agent", { handle: "Wren-2", publicKey: kp.publicKey, operatorId: "op-wren2", constitution: w.ack });
    const set = await w.call("set_doorbell", { envelope: await w.sign(kp, "Wren-2", { type: "doorbell.set", kind: "claude-routine" }) });
    assert.equal(set.isError, false, JSON.stringify(set.body));
    assert.equal(set.body["http_status"], 202);
    assert.match(String(set.body["for_your_person"]), /^https:\/\/ecdysis\.me\/doorbell\/[0-9a-f]{32}\/[0-9a-f]{64}$/);
    // Each tool does one thing.
    const wrong = await w.call("set_doorbell", { envelope: await w.sign(kp, "Wren-2", { type: "doorbell.stop" }) });
    assert.equal(wrong.isError, true);
    const stop = await w.call("stop_doorbell", { envelope: await w.sign(kp, "Wren-2", { type: "doorbell.stop" }) });
    assert.equal(stop.body["http_status"], 200);
    assert.equal((await w.store.getDoorbell("Wren-2"))!.status, "stopped");
  });

  it("refuses every write in read-only mode except stopping a doorbell", async () => {
    const live = await world();
    const kp = await generateKeyPair();
    await live.call("register_agent", { handle: "Wren-3", publicKey: kp.publicKey, operatorId: "op-wren3", constitution: live.ack });
    await live.call("set_doorbell", { envelope: await live.sign(kp, "Wren-3", { type: "doorbell.set", kind: "self" }) });

    // The same store, now behind the kill switch.
    const ro = await world({ readOnly: true });
    const roCall = async (name: string, args: Record<string, unknown>) => {
      const svc = live.svc;
      const bells = new Doorbells({
        store: live.store, siteBase: "https://ecdysis.me", apiBase: "https://api.ecdysis.me", sthPrivateKey: null, sealSecret: null,
        readOnly: true, now: () => new Date(), random: Math.random,
      });
      const r = await route(new Request("https://api.ecdysis.me/mcp", {
        method: "POST", headers: { "content-type": "application/json" },
        body: JSON.stringify({ jsonrpc: "2.0", id: 1, method: "tools/call", params: { name, arguments: args } }),
      }), svc, new MemoryRateLimiter(1000), { doorbells: bells, readOnly: true });
      const b = (await r.json()) as { result: { content: Array<{ text: string }>; isError?: boolean } };
      return { isError: !!b.result.isError, body: JSON.parse(b.result.content[0]!.text) as Record<string, unknown> };
    };
    void ro;
    const k2 = await generateKeyPair();
    const reg = await roCall("register_agent", { handle: "Wren-4", publicKey: k2.publicKey, operatorId: "op-wren4", constitution: live.ack });
    assert.equal(reg.body["http_status"], 503);
    assert.equal(await live.store.getAgent("Wren-4"), null);
    const pPayload = paper("Wren-3", kp.publicKey);
    const sub = await roCall("submit_paper", { envelope: { payload: pPayload, signature: await signJson(kp.privateKey, pPayload) } });
    assert.equal(sub.body["http_status"], 503);
    const practice = await roCall("get_practice_case", { envelope: await live.sign(kp, "Wren-3", { type: "practice.request" }) });
    assert.equal(practice.body["http_status"], 503, "practice writes state, so it waits too");
    const set = await roCall("set_doorbell", { envelope: await live.sign(kp, "Wren-3", { type: "doorbell.set", kind: "self" }) });
    assert.equal(set.body["http_status"], 503);
    const stop = await roCall("stop_doorbell", { envelope: await live.sign(kp, "Wren-3", { type: "doorbell.stop" }) });
    assert.equal(stop.body["http_status"], 200, "a stop always works");
    assert.equal((await live.store.getDoorbell("Wren-3"))!.status, "stopped");
    // Reading still works.
    const about = await roCall("get_constitution", {});
    assert.equal(about.isError, false);
  });

  it("limits writes per agent, not per address, and counts them under the API's names", async () => {
    const w = await world({ limit: 2 });
    const a = await generateKeyPair();
    const b = await generateKeyPair();
    // Two agents behind the same address (an AI app's servers) each get their own allowance.
    assert.equal((await w.call("register_agent", { handle: "Wren-5", publicKey: a.publicKey, operatorId: "op-5", constitution: w.ack })).body["http_status"], 201);
    assert.equal((await w.call("register_agent", { handle: "Wren-6", publicKey: b.publicKey, operatorId: "op-6", constitution: w.ack })).body["http_status"], 201);
    const set = async () => (await w.call("set_doorbell", { envelope: await w.sign(a, "Wren-5", { type: "doorbell.set", kind: "self" }) })).body["http_status"];
    assert.equal(await set(), 200);
    assert.equal(await set(), 429, "Wren-5's third write in a minute");
    assert.equal((await w.call("set_doorbell", { envelope: await w.sign(b, "Wren-6", { type: "doorbell.set", kind: "self" }) })).body["http_status"], 200, "Wren-6 is unaffected");

    const ids = (await w.store.listAccessPrefix("f")).map((c) => c.id);
    assert.ok(ids.includes("funnel:register:201"));
    assert.ok(ids.includes("funnel:doorbell:200"));
    const day = new Date().toISOString().slice(0, 10);
    assert.ok(ids.includes(`fd:${day}:doorbell:ok`));
    assert.ok((await w.store.listAccessPrefix("mcpw:")).some((c) => c.id === `mcpw:${day}:ok`));

    // A probe's writes are never counted.
    const before = (await w.store.listAccessPrefix("funnel:register")).reduce((s, c) => s + c.count, 0);
    const c = await generateKeyPair();
    await w.call("register_agent", { handle: "Wren-7", publicKey: c.publicKey, operatorId: "op-live-check", constitution: w.ack }, { "x-ecdysis-probe": "1" });
    const after = (await w.store.listAccessPrefix("funnel:register")).reduce((s, x) => s + x.count, 0);
    assert.equal(after, before);
  });
});
