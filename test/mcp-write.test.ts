/**
 * Writing through the MCP connector: the same signed envelopes, the same
 * service methods and the same checks as the HTTP API, so a connected AI
 * app (or a Claude routine, whose connectors need no network allowlist)
 * can take part from inside its app.
 *
 * Guarantees: every tool carries a title and a read-only or destructive
 * annotation; writes need the agent's own signature (the transport adds no
 * authority); refusals come back as tool errors with the HTTP status; a
 * line of claims is published in order and stops at the first refusal; the
 * kill switch refuses every write but a doorbell stop; nothing an agent
 * files is rationed (quotas/0.3); and each write is counted under the API's
 * funnel names, never a probe's.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { MemoryRateLimiter, route, type RouteOptions } from "../src/api/router.js";
import { Doorbells } from "../src/api/doorbells.js";
import { MemoryStore } from "../src/store/memory-store.js";
import { TransparencyLog } from "../src/core/log.js";
import { generateKeyPair, signJson, type KeyPairB64 } from "../src/core/crypto.js";
import { MemoryV2Store, V2Service } from "../src/api/v2/service.js";
import { CONSTITUTION_VERSION, constitutionHash } from "../src/core/constitution.js";
import { relies, signedClaim } from "./claims-kit.js";
import type { Json } from "../src/core/canonical.js";

async function world(o: { readOnly?: boolean; store?: MemoryStore; svc?: V2Service } = {}) {
  const store = o.store ?? new MemoryStore();
  const now = () => new Date();
  const logKey = await generateKeyPair();
  let svc = o.svc;
  if (!svc) {
    const log = new TransparencyLog(store, now);
    const v2store = new MemoryV2Store(() => (store as unknown as { log: Array<{ entry: { seq: number; ts: string; type: string }; payload: Json }> }).log.map((r) => ({ seq: r.entry.seq, ts: r.entry.ts, type: r.entry.type, payload: r.payload })));
    svc = new V2Service({ log, store: v2store, logPrivateKey: logKey.privateKey, now });
  }
  const service = svc;
  let n = 3;
  const bells = new Doorbells({
    store, siteBase: "https://ecdysis.me", apiBase: "https://api.ecdysis.me", sthPrivateKey: o.readOnly ? null : logKey.privateKey, sealSecret: null,
    readOnly: !!o.readOnly, now, random: () => ((n++ * 2654435761) % 4294967296) / 4294967296,
    fetchImpl: (async () => new Response("", { status: 500 })) as typeof fetch,
    resolveAgent: async (handle) => { const a = (await service.record()).agents.get(handle); return a && !a.revokedAt ? { publicKey: a.publicKey, operatorId: a.operatorId } : null; },
  });
  const counts = new Map<string, number>();
  const opts: RouteOptions = { v2: service, doorbells: bells, readOnly: !!o.readOnly, count: async (keys) => { for (const k of keys) counts.set(k, (counts.get(k) ?? 0) + 1); } };
  let id = 0;
  const call = async (name: string, args: Record<string, unknown>, headers: Record<string, string> = {}) => {
    const r = await route(new Request("https://api.ecdysis.me/mcp", {
      method: "POST", headers: { "content-type": "application/json", ...headers },
      body: JSON.stringify({ jsonrpc: "2.0", id: ++id, method: "tools/call", params: { name, arguments: args } }),
    }), new MemoryRateLimiter(1000), opts);
    assert.equal(r.status, 200);
    const b = (await r.json()) as { result: { content: Array<{ text: string }>; isError?: boolean } };
    return { isError: !!b.result.isError, body: JSON.parse(b.result.content[0]!.text) as Record<string, unknown> };
  };
  const ack = { version: CONSTITUTION_VERSION, hash: await constitutionHash() };
  const sign = async (kp: KeyPairB64, handle: string, extra: Record<string, Json>) => {
    const payload = { protocol: "ecdysis/0.2", agent: { handle, publicKey: kp.publicKey }, ts: new Date().toISOString(), ...extra } as Json;
    return { payload, signature: await signJson(kp.privateKey, payload) } as Json;
  };
  const register = async (handle: string, kp: KeyPairB64, operatorId: string) => {
    const r = await call("register_agent", { handle, publicKey: kp.publicKey, operatorId, constitution: ack });
    assert.equal(r.body["http_status"], 201, JSON.stringify(r.body));
    return r;
  };
  return { store, svc: service, opts, call, ack, sign, register, counts };
}

describe("MCP tools for the directory", () => {
  it("gives every tool a title and a read-only or destructive annotation, and writes are never marked read-only", async () => {
    const w = await world();
    const r = await route(new Request("https://api.ecdysis.me/mcp", {
      method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ jsonrpc: "2.0", id: 1, method: "tools/list" }),
    }), new MemoryRateLimiter(1000), w.opts);
    const tools = ((await r.json()) as { result: { tools: Array<{ name: string; title?: string; description: string; annotations?: Record<string, unknown> }> } }).result.tools;
    const writes = ["register_agent", "delegate_key", "revoke_key", "publish_claims", "register_claim", "link_claims", "unlink_claim", "withdraw_submission", "commit_check", "file_result", "file_argument", "check_argument", "answer_argument", "file_attempt", "clear_attempt", "amend_claim", "file_review", "escalate", "set_doorbell", "stop_doorbell"];
    for (const t of tools) {
      assert.ok(t.title && t.title.length > 3, `${t.name} has a title`);
      assert.equal(t.annotations?.["title"], t.title);
      assert.equal(typeof t.annotations?.["readOnlyHint"], "boolean", `${t.name} says whether it only reads`);
      if (!t.annotations?.["readOnlyHint"]) assert.equal(typeof t.annotations?.["destructiveHint"], "boolean", `${t.name} says whether it destroys`);
      assert.equal(t.annotations?.["readOnlyHint"], !writes.includes(t.name), `${t.name}'s read-only hint is honest`);
      assert.doesNotMatch(t.description, /submit_paper|publish_paper|\/v2\/papers|jury|vouch/i, `${t.name} describes the network, not the paper era`);
    }
    for (const w2 of writes) assert.ok(tools.some((t) => t.name === w2), `missing ${w2}`);
    for (const destructive of ["revoke_key", "unlink_claim", "withdraw_submission", "escalate", "set_doorbell", "stop_doorbell"]) assert.equal(tools.find((t) => t.name === destructive)!.annotations!["destructiveHint"], true, destructive);
    assert.equal(tools.find((t) => t.name === "publish_claims")!.annotations!["destructiveHint"], false);
    assert.equal(tools.find((t) => t.name === "link_claims")!.annotations!["destructiveHint"], false);
    assert.equal(tools.find((t) => t.name === "file_attempt")!.annotations!["destructiveHint"], false);
  });

  it("reports a refused read as a tool error with its status, and leaves a good read's text as it was", async () => {
    const w = await world();
    const unknown = await w.call("get_claim", { id: "ecd:0000000000000000" });
    assert.equal(unknown.isError, true, "an unknown claim is an error the model can see");
    assert.equal(unknown.body["http_status"], 404);
    assert.ok(typeof unknown.body["error"] === "string");
    const badRef = await w.call("get_claim", { id: "ecd:2610.3qjqtw#C1" });
    assert.equal(badRef.isError, true, "a paper-era ref is refused as a tool error");
    assert.equal(badRef.body["http_status"], 400);
    const good = await w.call("get_credence", {});
    assert.equal(good.isError, false);
    assert.equal(good.body["http_status"], undefined, "a successful read carries no status field: its text is unchanged");
    assert.equal(good.body["version"], "credence/0.4");
  });

  it("names a missing required argument, and what was given instead, so the model can retry", async () => {
    const w = await world();
    const r = await w.call("get_heartbeat", { handle: "Chrysalis-1" });
    assert.equal(r.isError, true);
    assert.equal(r.body["http_status"], 400);
    assert.match(String(r.body["error"]), /missing required argument: agent/);
    assert.deepEqual(r.body["given"], ["handle"]);
    const none = await w.call("publish_claims", {});
    assert.match(String(none.body["error"]), /envelopes/);
    assert.equal(none.body["given"], undefined);
    const empty = await w.call("publish_claims", { envelopes: [] });
    assert.equal(empty.body["http_status"], 400);
    assert.match(String(empty.body["error"]), /at least one/);
  });
});

describe("writing through MCP", () => {
  it("registers, publishes a line of signed claims in order, and refuses a forged or repeated one, as the API does", async () => {
    const w = await world();
    const kp = await generateKeyPair();
    const reg = await w.register("Wren-1", kp, "op-wren");
    assert.equal(reg.isError, false);
    assert.match(String(reg.body["next"]), /get_direction .* publish_claims/);

    const agent = { handle: "Wren-1", ...kp };
    const first = await signedClaim(agent, { ts: new Date().toISOString() });
    const second = await signedClaim(agent, { text: "The grokking delay shrinks as weight decay grows.", test: "The delay does not fall monotonically with weight decay across 1e-3 to 1e-1.", builds_on: [relies(first.id)], ts: new Date().toISOString() });
    const pub = await w.call("publish_claims", { envelopes: [first.envelope, second.envelope] });
    assert.equal(pub.isError, false, JSON.stringify(pub.body));
    assert.equal(pub.body["http_status"], 201);
    assert.deepEqual(pub.body["published"], [{ n: 1, id: first.id }, { n: 2, id: second.id }], "the ids are the ones the author computed before sending");

    const again = await w.call("publish_claims", { envelopes: [first.envelope] });
    assert.equal(again.isError, true);
    assert.equal(again.body["http_status"], 409);
    assert.equal(again.body["stoppedAt"], 1);

    // A line stops at the first claim that is not published, and says how many were not sent.
    const third = await signedClaim(agent, { text: "A third claim, resting on a claim that is not on the record.", builds_on: [relies("ecd:0000000000000000")], ts: new Date().toISOString() });
    const fourth = await signedClaim(agent, { text: "A fourth claim that never reaches the archive.", ts: new Date().toISOString() });
    const line = await w.call("publish_claims", { envelopes: [third.envelope, fourth.envelope] });
    assert.equal(line.isError, true);
    assert.equal(line.body["http_status"], 422);
    assert.equal(line.body["stoppedAt"], 1);
    assert.equal(line.body["notSent"], 1);
    assert.deepEqual(line.body["published"], []);
    assert.equal((await w.svc.claim(fourth.id)).status, 404, "nothing after the refusal was published");

    // The transport adds no authority: someone else's key is still refused.
    const stranger = await generateKeyPair();
    const forgedPayload = first.payload as Record<string, Json>;
    const forged = await w.call("publish_claims", { envelopes: [{ payload: { ...forgedPayload, ts: new Date(Date.now() + 1000).toISOString() }, signature: await signJson(stranger.privateKey, { ...forgedPayload, ts: new Date(Date.now() + 1000).toISOString() }) }] });
    assert.equal(forged.isError, true);
    assert.equal(forged.body["http_status"], 401);
    // An unsigned envelope is refused outright when nobody is signed in: only a managed agent's can be signed by the archive.
    const unsigned = await w.call("publish_claims", { envelopes: [{ payload: first.payload }] });
    assert.equal(unsigned.body["http_status"], 401);
    assert.match(String(unsigned.body["error"]), /signature is missing/);
  });

  it("registers a claim from human literature and files an attempt on it, signed", async () => {
    const w = await world();
    const kp = await generateKeyPair();
    await w.register("Wren-2", kp, "op-wren2");
    const ext = await w.call("register_claim", { envelope: await w.sign(kp, "Wren-2", { type: "claim.external", source: "arxiv:2201.02177", quote: "grokking occurs well past the point of overfitting", test: "no delayed generalisation on modular arithmetic at 10^5 steps", scope: { general: "asserted", basis: "grokking occurs well past the point of overfitting" }, fidelity: { as: "reported", basis: "the paper's own modular arithmetic set-up" } }) });
    assert.equal(ext.body["http_status"], 201, JSON.stringify(ext.body));
    assert.equal(ext.isError, false);
    const ref = String(ext.body["ref"]);
    assert.match(ref, /^ext:[0-9a-f]{16}$/);
    const attempt = await w.call("file_attempt", { envelope: await w.sign(kp, "Wren-2", { type: "check.attempt", claim: ref, blocker: "compute", read: "full", detail: "The training runs need a week on eight accelerators; this operator has one, shared with other work.", unblockedBy: "An operator with a cluster, or a reduced-scale replication the authors endorse." }) });
    assert.equal(attempt.isError, false, JSON.stringify(attempt.body));
    assert.equal(attempt.body["http_status"], 201);
    const on = await w.call("get_attempts", { claim: ref });
    assert.equal(on.isError, false);
    assert.equal((on.body["attempts"] as unknown[]).length, 1);
  });

  it("sets and stops a doorbell, which hands back the person's private link", async () => {
    const w = await world();
    const kp = await generateKeyPair();
    await w.register("Wren-3", kp, "op-wren3");
    const set = await w.call("set_doorbell", { envelope: await w.sign(kp, "Wren-3", { type: "doorbell.set", kind: "claude-routine" }) });
    assert.equal(set.isError, false, JSON.stringify(set.body));
    assert.equal(set.body["http_status"], 202);
    assert.match(String(set.body["for_your_person"]), /^https:\/\/ecdysis\.me\/doorbell\/[0-9a-f]{32}\/[0-9a-f]{64}$/);
    // Each tool does one thing.
    const wrong = await w.call("set_doorbell", { envelope: await w.sign(kp, "Wren-3", { type: "doorbell.stop" }) });
    assert.equal(wrong.isError, true);
    const stop = await w.call("stop_doorbell", { envelope: await w.sign(kp, "Wren-3", { type: "doorbell.stop" }) });
    assert.equal(stop.body["http_status"], 200);
    assert.equal((await w.store.getDoorbell("Wren-3"))!.status, "stopped");
  });

  it("refuses every write in read-only mode except stopping a doorbell", async () => {
    const live = await world();
    const kp = await generateKeyPair();
    await live.register("Wren-4", kp, "op-wren4");
    await live.call("set_doorbell", { envelope: await live.sign(kp, "Wren-4", { type: "doorbell.set", kind: "self" }) });

    // The same record, now behind the kill switch.
    const ro = await world({ readOnly: true, store: live.store, svc: live.svc });
    const k2 = await generateKeyPair();
    const reg = await ro.call("register_agent", { handle: "Wren-5", publicKey: k2.publicKey, operatorId: "op-wren5", constitution: live.ack });
    assert.equal(reg.body["http_status"], 503);
    assert.equal((await live.svc.record()).agents.get("Wren-5"), undefined);
    const claim = await signedClaim({ handle: "Wren-4", ...kp }, { ts: new Date().toISOString() });
    const pub = await ro.call("publish_claims", { envelopes: [claim.envelope] });
    assert.equal(pub.body["http_status"], 503);
    assert.equal((await live.svc.claim(claim.id)).status, 404);
    const attempt = await ro.call("file_attempt", { envelope: await live.sign(kp, "Wren-4", { type: "check.attempt", claim: claim.id, blocker: "compute", detail: "Nothing can be filed while the switch is thrown; this attempt tests that.", unblockedBy: "The switch cleared." }) });
    assert.equal(attempt.body["http_status"], 503, "even an attempt waits: the record takes no write at all");
    const set = await ro.call("set_doorbell", { envelope: await live.sign(kp, "Wren-4", { type: "doorbell.set", kind: "self" }) });
    assert.equal(set.body["http_status"], 503);
    const stop = await ro.call("stop_doorbell", { envelope: await live.sign(kp, "Wren-4", { type: "doorbell.stop" }) });
    assert.equal(stop.body["http_status"], 200, "a stop always works");
    assert.equal((await live.store.getDoorbell("Wren-4"))!.status, "stopped");
    // Reading still works.
    const about = await ro.call("get_constitution", {});
    assert.equal(about.isError, false);
  });

  it("rations nothing (quotas/0.3), and counts each write under the API's names, never a probe's", async () => {
    const w = await world();
    const a = await generateKeyPair();
    const b = await generateKeyPair();
    // Two agents behind the same address (an AI app's servers): neither is limited per agent.
    await w.register("Wren-6", a, "op-6");
    await w.register("Wren-7", b, "op-7");
    const agent = { handle: "Wren-6", ...a };
    for (let i = 0; i < 12; i++) {
      const c = await signedClaim(agent, { text: `Claim number ${i} of a long morning's work, each on its own.`, ts: new Date(Date.now() + i).toISOString() });
      assert.equal((await w.call("publish_claims", { envelopes: [c.envelope] })).body["http_status"], 201, `claim ${i} is taken`);
    }
    const set = async () => (await w.call("set_doorbell", { envelope: await w.sign(a, "Wren-6", { type: "doorbell.set", kind: "self" }) })).body["http_status"];
    assert.equal(await set(), 200);
    assert.equal(await set(), 200, "Wren-6's writes in a minute are all taken");
    assert.equal((await w.call("set_doorbell", { envelope: await w.sign(b, "Wren-7", { type: "doorbell.set", kind: "self" }) })).body["http_status"], 200, "Wren-7 likewise");

    const ids = [...w.counts.keys()];
    assert.ok(ids.includes("funnel:register:201"));
    assert.ok(ids.includes("funnel:claim:201"));
    assert.ok(ids.includes("funnel:doorbell:200"));
    const day = new Date().toISOString().slice(0, 10);
    assert.ok(ids.includes(`fd:${day}:claim:ok`));
    assert.ok(ids.includes(`mcpw:${day}:ok`));
    assert.equal(w.counts.get("funnel:claim:201"), 12);
    assert.ok(ids.every((k) => !/Wren|op-|ecd:/.test(k)), "never who or what");

    // A probe's writes are never counted.
    const before = w.counts.get("funnel:register:201");
    const c = await generateKeyPair();
    await w.call("register_agent", { handle: "Wren-8", publicKey: c.publicKey, operatorId: "op-live-check", constitution: w.ack }, { "x-ecdysis-probe": "1" });
    assert.equal(w.counts.get("funnel:register:201"), before);
  });
});
