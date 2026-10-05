/**
 * MCP Events on the connector (experimental): ChatGPT, signed in, subscribes
 * to ecdysis.wake for one of its person's agents, and the subscription
 * becomes that agent's doorbell.
 *
 * Guarantees tested here: only a signed-in principal can subscribe, and only
 * for an agent of its own operator; the callback is held to the webhook
 * rules and must answer a verification signed with the client's own secret,
 * with the same challenge, before anything is kept; a refresh changes only
 * the secret and the lapse time, and a rotating secret is signed with too
 * for a day; every delivery is signed (v1 under the secret, v1a under the
 * log key) with the subscription id in its headers; a 410 ends it at once;
 * a lapsed subscription, or an agent no longer on the account, is never
 * rung; a subscription the person ended can't be revived by the app's
 * automatic refresh until the person allows it; and the transport speaks
 * MCP 2026-07-28 (server/discover, resultType, the header check, 404 for
 * an unknown method) beside the older versions.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { Doorbells } from "../src/api/doorbells.js";
import { MemoryStore } from "../src/store/memory-store.js";
import { handleMcp, type McpContext } from "../src/api/mcp.js";
import { MemoryRateLimiter, route } from "../src/api/router.js";
import { generateKeyPair, signJson, verifyJson } from "../src/core/crypto.js";
import { TransparencyLog } from "../src/core/log.js";
import { MemoryV2Store, V2Service } from "../src/api/v2/service.js";
import { v2Tools } from "../src/api/v2/tools.js";
import type { Json } from "../src/core/canonical.js";
import { newSecret, verifyDelivery } from "../src/core/webhooks.js";

const T0 = Date.UTC(2026, 9, 5, 9, 0, 0);
const HOUR = 3600 * 1000;
const DAY = 24 * HOUR;
const CALLBACK = "https://chatgpt.example.com/mcp/events/cb_123";
const DANIEL = { accountId: "acct_0123456789abcdef01234567", operatorId: "op-daniel", clientId: "client-chatgpt", scope: "agent" };
const MALLORY = { accountId: "acct_fedcba9876543210fedcba98", operatorId: "op-mallory", clientId: "client-chatgpt", scope: "agent" };

interface Call { url: string; headers: Record<string, string>; body: string }

async function world() {
  let now = T0;
  const store = new MemoryStore();
  const log = await generateKeyPair();
  const calls: Call[] = [];
  // A callback that answers the verification as ChatGPT does: {"challenge": "<the same>"}.
  let handler: (url: string, body: string) => Response = (_u, body) => {
    const j = JSON.parse(body) as { type?: string; challenge?: string };
    return j.type === "verification" ? Response.json({ challenge: j.challenge }) : new Response(null, { status: 202 });
  };
  const fetchImpl = (async (input: RequestInfo | URL, init?: RequestInit) => {
    const headers: Record<string, string> = {};
    new Headers(init?.headers).forEach((v, k) => { headers[k] = v; });
    const body = String(init?.body ?? "");
    calls.push({ url: String(input), headers, body });
    return handler(String(input), body);
  }) as typeof fetch;
  const owners = new Map<string, string>([["gemini-djhulme", "op-daniel"], ["Mal-1", "op-mallory"]]);
  let n = 11;
  const bells = new Doorbells({
    store, siteBase: "https://ecdysis.me", apiBase: "https://api.ecdysis.me", sthPrivateKey: log.privateKey, sealSecret: null, readOnly: false,
    fetchImpl, now: () => new Date(now), random: () => ((n++ * 2654435761) % 4294967296) / 4294967296,
    resolveAgent: async (h) => (owners.has(h) ? { publicKey: "k", operatorId: owners.get(h)! } : null),
  });
  // The record, whose tools the connector serves beside the events.
  const v2 = new V2Service({
    log: new TransparencyLog(store, () => new Date(now)), logPrivateKey: log.privateKey, now: () => new Date(now),
    store: new MemoryV2Store(() => (store as unknown as { log: Array<{ entry: { seq: number; ts: string; type: string }; payload: Json }> }).log.map((r) => ({ seq: r.entry.seq, ts: r.entry.ts, type: r.entry.type, payload: r.payload }))),
  });
  const tools = v2Tools(v2);
  const rpc = async (method: string, params: Record<string, unknown>, principal: McpContext["principal"] = DANIEL) => {
    const r = await handleMcp({ jsonrpc: "2.0", id: 1, method, params } as Json, { host: "api.ecdysis.me", doorbells: bells, principal, tools });
    return r.body as { result?: Record<string, Json>; error?: { code: number; message: string; data?: { reason?: string } } };
  };
  const subscribe = (secret: string, extra: Record<string, unknown> = {}, principal: McpContext["principal"] = DANIEL) =>
    rpc("events/subscribe", { name: "ecdysis.wake", arguments: { agent: "gemini-djhulme" }, delivery: { mode: "webhook", url: CALLBACK, secret }, cursor: null, ...extra }, principal);
  return { store, log, calls, bells, v2, owners, rpc, subscribe, on(h: typeof handler) { handler = h; }, tick(ms: number) { now += ms; }, get now() { return now; } };
}

describe("MCP Events: discovery", () => {
  it("speaks MCP 2026-07-28 beside the older versions, and lists one event", async () => {
    const w = await world();
    const d = await w.rpc("server/discover", { _meta: { "io.modelcontextprotocol/protocolVersion": "2026-07-28" } });
    assert.equal(d.result!["resultType"], "complete");
    assert.deepEqual((d.result!["supportedVersions"] as string[])[0], "2026-07-28");
    assert.ok((d.result!["supportedVersions"] as string[]).includes("2025-06-18"), "older clients still served");
    assert.deepEqual((d.result!["capabilities"] as Record<string, Json>)["events"], {});
    const list = await w.rpc("events/list", { _meta: { "io.modelcontextprotocol/protocolVersion": "2026-07-28" } });
    assert.equal(list.result!["resultType"], "complete");
    const events = list.result!["events"] as Array<Record<string, Json>>;
    assert.equal(events.length, 1);
    assert.equal(events[0]!["name"], "ecdysis.wake");
    assert.deepEqual(events[0]!["delivery"], ["webhook"]);
    assert.deepEqual((events[0]!["inputSchema"] as Record<string, Json>)["required"], ["agent"]);
    // tools/list as 2026-07-28 carries resultType; as 2025-06-18 it is unchanged.
    assert.equal((await w.rpc("tools/list", { _meta: { "io.modelcontextprotocol/protocolVersion": "2026-07-28" } })).result!["resultType"], "complete");
    assert.equal((await w.rpc("tools/list", {})).result!["resultType"], undefined);
  });

  it("refuses a request whose header and _meta disagree, and answers an unknown method with 404 under 2026-07-28", async () => {
    const w = await world();
    const lim = new MemoryRateLimiter(1000);
    const post = (headers: Record<string, string>, body: unknown) => route(new Request("https://api.ecdysis.me/mcp", { method: "POST", headers: { "content-type": "application/json", accept: "application/json, text/event-stream", ...headers }, body: JSON.stringify(body) }), lim, { v2: w.v2, doorbells: w.bells });
    const mismatch = await post({ "mcp-protocol-version": "2026-07-28" }, { jsonrpc: "2.0", id: 7, method: "tools/list", params: { _meta: { "io.modelcontextprotocol/protocolVersion": "2025-06-18" } } });
    assert.equal(mismatch.status, 400);
    assert.equal(((await mismatch.json()) as { error: { code: number } }).error.code, -32020);
    const unknown = await post({ "mcp-protocol-version": "2026-07-28" }, { jsonrpc: "2.0", id: 8, method: "nothing/here", params: { _meta: { "io.modelcontextprotocol/protocolVersion": "2026-07-28" } } });
    assert.equal(unknown.status, 404);
    const old = await post({}, { jsonrpc: "2.0", id: 9, method: "nothing/here" });
    assert.equal(old.status, 200, "older clients keep the JSON-RPC error in a 200");
  });
});

describe("MCP Events: subscribing", () => {
  it("needs a signed-in principal and an agent of its own operator, a public callback and a proper secret", async () => {
    const w = await world();
    const s = newSecret();
    assert.equal((await w.subscribe(s, {}, null)).error!.code, -32012);
    assert.match((await w.rpc("events/subscribe", { name: "ecdysis.wake", arguments: { agent: "gemini-djhulme" }, delivery: { mode: "webhook", url: CALLBACK, secret: s } }, MALLORY)).error!.message, /no agent gemini-djhulme on your account/);
    for (const url of ["http://chatgpt.example.com/cb", "https://127.0.0.1/cb", "https://api.ecdysis.me/x", "https://localhost/cb", "https://chatgpt.example.com:8443/cb"]) {
      const r = await w.rpc("events/subscribe", { name: "ecdysis.wake", arguments: { agent: "gemini-djhulme" }, delivery: { mode: "webhook", url, secret: s } });
      assert.equal(r.error!.code, -32015, url);
      assert.equal(r.error!.data!.reason, "invalid_url");
    }
    assert.equal((await w.subscribe("whsec_" + btoa("too short"))).error!.code, -32602);
    assert.equal((await w.rpc("events/subscribe", { name: "something.else", arguments: { agent: "gemini-djhulme" }, delivery: { mode: "webhook", url: CALLBACK, secret: s } })).error!.code, -32602);
    assert.equal((await w.rpc("events/subscribe", { name: "ecdysis.wake", arguments: { agent: "gemini-djhulme", extra: 1 }, delivery: { mode: "webhook", url: CALLBACK, secret: s } })).error!.code, -32602);
    assert.equal(w.calls.length, 0, "nothing was sent anywhere");
  });

  it("keeps nothing until the callback answers a verification signed with the client's secret, with the same challenge", async () => {
    const w = await world();
    const s = newSecret();
    w.on(() => Response.json({ challenge: "not the one" }));
    const wrong = await w.subscribe(s);
    assert.equal(wrong.error!.code, -32015);
    assert.equal(wrong.error!.data!.reason, "challenge_failed");
    assert.equal(await w.store.getDoorbell("gemini-djhulme"), null);
    w.on(() => new Response(null, { status: 302, headers: { location: "https://elsewhere.example/" } }));
    assert.equal((await w.subscribe(s)).error!.data!.reason, "redirect");
    w.on((_u, body) => Response.json({ challenge: (JSON.parse(body) as { challenge: string }).challenge }));
    w.calls.length = 0;
    const ok = await w.subscribe(s);
    assert.ok(ok.result, JSON.stringify(ok.error));
    const id = String(ok.result!["id"]);
    assert.match(id, /^sub_[0-9a-f]{32}$/);
    assert.equal(ok.result!["cursor"], null);
    assert.equal(ok.result!["truncated"], false);
    assert.equal(Date.parse(String(ok.result!["refreshBefore"])), w.now + 7 * DAY, "a week unless asked otherwise");
    // The verification itself.
    const v = w.calls[0]!;
    assert.equal(v.url, CALLBACK);
    const vb = JSON.parse(v.body) as Record<string, Json>;
    assert.deepEqual(Object.keys(vb).sort(), ["challenge", "type"]);
    assert.equal(vb["type"], "verification");
    assert.match(v.headers["webhook-id"]!, /^msg_verification_/);
    assert.equal(v.headers["x-mcp-subscription-id"], id);
    assert.ok(await verifyDelivery({ headers: v.headers, body: v.body, nowS: Math.floor(w.now / 1000), secret: s }), "signed with the client's own secret");
    const d = (await w.store.getDoorbell("gemini-djhulme"))!;
    assert.equal(d.kind, "mcp-events");
    assert.equal(d.status, "active");
    assert.equal(d.settings!.subscription, id);
    assert.ok(!JSON.stringify(d).includes(s.slice(6, 30)), "the secret is sealed");
    // ttlMs is honoured within an hour and thirty days.
    const short = await w.subscribe(s, { ttlMs: 60_000 });
    assert.equal(Date.parse(String(short.result!["refreshBefore"])), w.now + HOUR);
  });

  it("refreshes without a new verification, and signs with a rotated-out secret for a day", async () => {
    const w = await world();
    const s1 = newSecret();
    const first = await w.subscribe(s1);
    w.tick(5 * DAY);
    w.calls.length = 0;
    const s2 = newSecret();
    const again = await w.subscribe(s2);
    assert.equal(again.result!["id"], first.result!["id"], "the same subscription");
    assert.equal(w.calls.length, 0, "no new verification for a refresh");
    assert.equal(Date.parse(String(again.result!["refreshBefore"])), w.now + 7 * DAY);
    w.tick(HOUR);
    await w.bells.notify();
    const ev = w.calls.at(-1)!;
    const sigs = ev.headers["webhook-signature"]!.split(" ");
    assert.equal(sigs.filter((x) => x.startsWith("v1,")).length, 2, "both secrets sign during the rotation");
    assert.ok(await verifyDelivery({ headers: ev.headers, body: ev.body, nowS: Math.floor(w.now / 1000), secret: s1 }));
    assert.ok(await verifyDelivery({ headers: ev.headers, body: ev.body, nowS: Math.floor(w.now / 1000), secret: s2 }));
  });
});

describe("MCP Events: delivery", () => {
  it("delivers each ring as one signed event with the subscription id, Ecdysis's own data inside", async () => {
    const w = await world();
    const s = newSecret();
    const id = String((await w.subscribe(s)).result!["id"]);
    w.calls.length = 0;
    w.tick(DAY + HOUR);
    const swept = await w.bells.notify();
    assert.equal(swept.rung, 1);
    const ev = w.calls[0]!;
    assert.equal(ev.url, CALLBACK);
    const body = JSON.parse(ev.body) as { eventId: string; name: string; timestamp: string; data: Record<string, Json>; cursor: null };
    assert.equal(body.name, "ecdysis.wake");
    assert.match(body.eventId, /^evt_[0-9a-f]{32}$/);
    assert.equal(ev.headers["webhook-id"], body.eventId);
    assert.equal(ev.headers["x-mcp-subscription-id"], id);
    assert.equal(body.cursor, null);
    assert.ok(!("type" in body), "no top-level type: that marks a control message");
    assert.equal(body.data["agent"], "gemini-djhulme");
    assert.equal(body.data["heartbeat"], "https://api.ecdysis.me/v2/heartbeat?agent=gemini-djhulme");
    assert.ok(await verifyJson(w.log.publicKey, body.data["payload"]!, String(body.data["signature"])), "the ring inside verifies with the log key");
    assert.ok(await verifyDelivery({ headers: ev.headers, body: ev.body, nowS: Math.floor(w.now / 1000), secret: s }), "v1 under the client's secret");
    assert.ok(await verifyDelivery({ headers: ev.headers, body: ev.body, nowS: Math.floor(w.now / 1000), publicKeySpkiB64url: w.log.publicKey }), "v1a under the log key");
  });

  it("ends at once on 410, never rings a lapsed subscription, and never rings for an agent no longer on the account", async () => {
    const w = await world();
    await w.subscribe(newSecret());
    w.on(() => new Response(null, { status: 410 }));
    w.tick(DAY + HOUR);
    await w.bells.notify();
    assert.equal((await w.store.getDoorbell("gemini-djhulme"))!.status, "paused", "410: gone, not retried");

    const w2 = await world();
    await w2.subscribe(newSecret(), { ttlMs: 2 * HOUR });
    w2.tick(DAY + HOUR);
    w2.calls.length = 0;
    await w2.bells.notify();
    assert.equal(w2.calls.length, 0);
    assert.match(String((await w2.store.getDoorbell("gemini-djhulme"))!.lastError), /lapsed/);

    const w3 = await world();
    await w3.subscribe(newSecret());
    w3.owners.set("gemini-djhulme", "op-someone-else");
    w3.tick(DAY + HOUR);
    w3.calls.length = 0;
    await w3.bells.notify();
    assert.equal(w3.calls.length, 0);
    assert.match(String((await w3.store.getDoorbell("gemini-djhulme"))!.lastError), /no longer on the account/);
  });

  it("unsubscribes only what this principal made to this callback, and does so idempotently", async () => {
    const w = await world();
    await w.subscribe(newSecret());
    const by = (p: McpContext["principal"], url = CALLBACK) => w.rpc("events/unsubscribe", { name: "ecdysis.wake", arguments: { agent: "gemini-djhulme" }, delivery: { mode: "webhook", url } }, p);
    assert.deepEqual((await by(MALLORY)).result, {});
    assert.deepEqual((await by(DANIEL, "https://chatgpt.example.com/other")).result, {});
    assert.equal((await w.store.getDoorbell("gemini-djhulme"))!.status, "active", "neither touched it");
    assert.deepEqual((await by(DANIEL)).result, {});
    assert.equal((await w.store.getDoorbell("gemini-djhulme"))!.status, "stopped");
    assert.deepEqual((await by(DANIEL)).result, {}, "again: still fine");
  });

  it("respects the person: a subscription they ended can't come back by the app's refresh until they allow it", async () => {
    const w = await world();
    const s = newSecret();
    await w.subscribe(s);
    // The agent sets a new doorbell with its main key (its person gets a link), and the person chooses a schedule on it.
    const kp = await generateKeyPair();
    const bells = new Doorbells({
      store: w.store, siteBase: "https://ecdysis.me", apiBase: "https://api.ecdysis.me", sthPrivateKey: w.log.privateKey, sealSecret: null, readOnly: false,
      now: () => new Date(w.now), random: Math.random,
      resolveAgent: async (h) => (h === "gemini-djhulme" ? { publicKey: kp.publicKey, operatorId: "op-daniel" } : null),
      fetchImpl: (async () => new Response("{}")) as typeof fetch,
    });
    const payload = { protocol: "ecdysis/0.2", agent: { handle: "gemini-djhulme", publicKey: kp.publicKey }, ts: new Date(w.now).toISOString().replace(/\.\d{3}Z$/, "Z"), type: "doorbell.set", kind: "claude-routine" } as Json;
    const set = await bells.request({ payload, signature: await signJson(kp.privateKey, payload) } as Json);
    const [, lid, ltok] = String((set.body as Record<string, Json>)["for_your_person"]).match(/doorbell\/([0-9a-f]{32})\/([0-9a-f]{64})/)!;
    await bells.page(lid!, ltok!, "POST", new URLSearchParams({ action: "self", platform: "chatgpt" }));
    assert.equal((await w.store.getDoorbell("gemini-djhulme"))!.kind, "self");
    // ChatGPT's automatic refresh: refused, so the person's choice stands.
    const refresh = await w.subscribe(s);
    assert.equal(refresh.error!.code, -32015);
    assert.equal(refresh.error!.data!.reason, "ended");
    assert.equal((await w.store.getDoorbell("gemini-djhulme"))!.kind, "self");
    // The page offers to allow it again; once allowed, the app can subscribe.
    const page = await bells.page(lid!, ltok!, "GET", null, new URLSearchParams({ for: "chatgpt" }));
    assert.match(page.html, /Allow ChatGPT to subscribe again/);
    await bells.page(lid!, ltok!, "POST", new URLSearchParams({ action: "allow-events", platform: "chatgpt" }));
    const back = await w.subscribe(s);
    assert.ok(back.result, JSON.stringify(back.error));
    assert.equal((await w.store.getDoorbell("gemini-djhulme"))!.kind, "mcp-events");
  });
});

describe("MCP Events: ended subscriptions stay ended", () => {
  it("lets the newest subscriber keep the doorbell: a replaced subscription's refresh is refused, so two never swap at each refresh", async () => {
    const w = await world();
    const a = newSecret();
    await w.subscribe(a);
    const OTHER = "https://chatgpt.example.com/mcp/events/cb_456";
    const b = await w.rpc("events/subscribe", { name: "ecdysis.wake", arguments: { agent: "gemini-djhulme" }, delivery: { mode: "webhook", url: OTHER, secret: newSecret() } });
    assert.ok(b.result, JSON.stringify(b.error));
    assert.equal((await w.store.getDoorbell("gemini-djhulme"))!.url, OTHER);
    const refreshA = await w.subscribe(a);
    assert.equal(refreshA.error!.data!.reason, "ended", "the replaced subscription's refresh is refused");
    assert.equal((await w.store.getDoorbell("gemini-djhulme"))!.url, OTHER, "the newest keeps it");
  });

  it("keeps a subscription the person ended ended, even after another one comes and goes", async () => {
    const w = await world();
    const a = newSecret();
    await w.subscribe(a);
    const d = (await w.store.getDoorbell("gemini-djhulme"))!;
    // The person stops it on the page.
    await w.bells.page(d.setupId, d.setupToken, "POST", new URLSearchParams({ action: "stop" }));
    const OTHER = "https://chatgpt.example.com/mcp/events/cb_789";
    const b = await w.rpc("events/subscribe", { name: "ecdysis.wake", arguments: { agent: "gemini-djhulme" }, delivery: { mode: "webhook", url: OTHER, secret: newSecret() } });
    assert.ok(b.result, JSON.stringify(b.error));
    assert.equal((await w.subscribe(a)).error!.data!.reason, "ended", "a new subscription doesn't revive an ended one");
  });

  it("lets an app that unsubscribed itself subscribe again, without the person", async () => {
    const w = await world();
    const s = newSecret();
    await w.subscribe(s);
    assert.deepEqual((await w.rpc("events/unsubscribe", { name: "ecdysis.wake", arguments: { agent: "gemini-djhulme" }, delivery: { mode: "webhook", url: CALLBACK } })).result, {});
    assert.equal((await w.store.getDoorbell("gemini-djhulme"))!.status, "stopped");
    const again = await w.subscribe(s);
    assert.ok(again.result, JSON.stringify(again.error));
    assert.equal((await w.store.getDoorbell("gemini-djhulme"))!.status, "active");
  });

  it("keeps nothing if the doorbell was stopped while the callback was being checked", async () => {
    const w = await world();
    const s = newSecret();
    await w.subscribe(s);
    const d = (await w.store.getDoorbell("gemini-djhulme"))!;
    // A new callback is being verified when the person presses stop.
    w.on((_u, body) => {
      void w.bells.page(d.setupId, d.setupToken, "POST", new URLSearchParams({ action: "stop" }));
      return Response.json({ challenge: (JSON.parse(body) as { challenge: string }).challenge });
    });
    const r = await w.rpc("events/subscribe", { name: "ecdysis.wake", arguments: { agent: "gemini-djhulme" }, delivery: { mode: "webhook", url: "https://chatgpt.example.com/mcp/events/cb_new", secret: newSecret() } });
    await new Promise((res) => setTimeout(res, 0));
    const after = (await w.store.getDoorbell("gemini-djhulme"))!;
    assert.equal(after.status, "stopped", JSON.stringify(r));
  });
});
