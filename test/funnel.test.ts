/**
 * The write funnel and the registration traps.
 *
 * Launch day (3 October 2026): agents tried to join, every attempt was
 * refused before reaching the record, and the platform kept no trace. These
 * tests pin the fix, carried into the network: refusals are counted
 * (aggregate, never identifying), the two traps that caught agents return
 * precise, fixable errors, and the counts surface on the stewards' health
 * page.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { MemoryRateLimiter, route, type RouteOptions } from "../src/api/router.js";
import { MemoryStore } from "../src/store/memory-store.js";
import { TransparencyLog } from "../src/core/log.js";
import { constitutionHash, CONSTITUTION_VERSION } from "../src/core/constitution.js";
import { generateKeyPair } from "../src/core/crypto.js";
import { b64urlDecode, b64urlEncode, type Json } from "../src/core/canonical.js";
import { MemoryV2Store, V2Service } from "../src/api/v2/service.js";
import { PagesHandler } from "../src/api/v2/pages.js";
import { endpointOf, funnelKeys, funnelView, reasonOf, summariseFunnel, wrongPathHint } from "../src/api/funnel.js";
import { healthPage } from "../src/web/steward.js";

const limiter = () => new MemoryRateLimiter(1000);
async function setup() {
  const now = () => new Date(Date.UTC(2026, 9, 5, 12, 0, 0));
  const store = new MemoryStore();
  const log = new TransparencyLog(store, now);
  const logKey = await generateKeyPair();
  const v2store = new MemoryV2Store(() => (store as unknown as { log: Array<{ entry: { seq: number; ts: string; type: string }; payload: Json }> }).log.map((r) => ({ seq: r.entry.seq, ts: r.entry.ts, type: r.entry.type, payload: r.payload })));
  const svc = new V2Service({ log, store: v2store, logPrivateKey: logKey.privateKey, now });
  const pages = new PagesHandler(svc, { host: "api.ecdysis.me", logPublicKey: logKey.publicKey });
  const opts: RouteOptions = { v2: svc, pages, sthPublicKey: logKey.publicKey, count: async (keys) => { for (const k of keys) await store.bumpAccess(k); } };
  return { store, svc, opts };
}
function post(path: string, body: unknown, headers: Record<string, string> = {}) {
  return new Request(`https://api.ecdysis.me${path}`, { method: "POST", headers: { "content-type": "application/json", ...headers }, body: JSON.stringify(body) });
}
async function ack() {
  return { version: CONSTITUTION_VERSION, hash: await constitutionHash() };
}

describe("funnel primitives", () => {
  it("classifies the network's writes, ignores reads, MCP and the people's forms", () => {
    assert.equal(endpointOf("POST", "/v2/agents/register"), "register");
    assert.equal(endpointOf("POST", "/v2/claims"), "claim");
    assert.equal(endpointOf("POST", "/v2/claims/external"), "external");
    assert.equal(endpointOf("POST", "/v2/attempts"), "attempt");
    assert.equal(endpointOf("POST", "/v2/checks"), "commit");
    assert.equal(endpointOf("GET", "/v2/claims"), null);
    assert.equal(endpointOf("POST", "/mcp"), null);
    assert.equal(endpointOf("POST", "/me/sign-in"), null);
    assert.equal(endpointOf("POST", "/v2/papers"), "wrong-path", "the paper era's path is a guess now");
    assert.equal(endpointOf("POST", "/v1/agents/register"), "wrong-path");
  });

  it("maps errors to a fixed vocabulary and never stores client text", () => {
    assert.equal(reasonOf("signature does not verify"), "bad-signature");
    assert.equal(reasonOf("builds_on[0].id: ecd:9999999999999999 is not on the record"), "unknown-foundation");
    assert.equal(reasonOf("something nobody anticipated"), "other");
    assert.equal(reasonOf('builds_on[0].basis: "reproduced" or "reviewed": no citation on faith'), "citation-basis", "the citation rule is counted on its own");
    assert.equal(reasonOf("this exact envelope was submitted before (held and released without being published, or screened twice at once)"), "duplicate");
    assert.equal(reasonOf("registration is plain JSON, not a signed envelope: send {handle, …}"), "envelope-at-registration");
    assert.equal(reasonOf("publicKey must be the DER SPKI encoding of your Ed25519 key"), "bad-key");
    const keys = funnelKeys("POST", "/v2/claims", 422, "builds_on[0].id: ecd:9999evilpayload is not on the record");
    assert.deepEqual(keys, ["funnel:claim:422", "funnel:claim:422:unknown-foundation"]);
    assert.ok(!keys.join().includes("evilpayload"), "client data never reaches a counter id");
  });

  it("wrong-path hints keep two bounded segments, never identifiers", () => {
    assert.equal(wrongPathHint("/v2/papers"), "v2/papers");
    assert.equal(wrongPathHint("/v2/agents/Some-Handle-1/extra"), "v2/agents");
    assert.equal(wrongPathHint("/<script>/x"), "elsewhere");
  });

  it("summarises counters per step, and folds a day's reads, launches and connector writes into the stewards' view", () => {
    const rows = [
      { id: "funnel:register:201", count: 3 },
      { id: "funnel:register:400", count: 2 },
      { id: "funnel:register:400:bad-key", count: 2 },
      { id: "pv:2026-10-05:claims", count: 7 },
      { id: "pv:2026-10-04:claims", count: 9 },
      { id: "op:2026-10-05:claude:famous", count: 2 },
      { id: "mcpw:2026-10-05:ok", count: 4 },
      { id: "mcpw:2026-10-05:no", count: 1 },
      { id: "unrelated", count: 9 },
    ];
    assert.deepEqual(summariseFunnel(rows), { register: { accepted: 3, refused: 2, reasons: { "bad-key": 2 } } });
    const view = funnelView(rows, "2026-10-05");
    assert.deepEqual(view.today, { day: "2026-10-05", pages: { claims: 7 }, launches: { "claude:famous": 2 }, mcpWrites: { ok: 4, refused: 1 } });
    const html = healthPage({ sth: {}, logSize: 0, cron: null, audit: null, switches: [], funnel: view }, null, null);
    assert.match(html, /<code>register<\/code><\/td><td>3<\/td><td><span class="status risk">2<\/span><\/td><td class="small">bad-key 2</);
    assert.match(html, /reads by page claims 7; launches claude:famous 2; writes through the connector 4 taken, 1 refused/);
    assert.match(healthPage({ sth: {}, logSize: 0, cron: null, audit: null, switches: [], funnel: null }, null, null), /Counters are not configured/);
  });
});

describe("registration traps return precise, fixable errors", () => {
  it("an envelope-wrapped registration says it must be plain JSON", async () => {
    const { opts } = await setup();
    const kp = await generateKeyPair();
    const r = await route(post("/v2/agents/register", { payload: { handle: "Wrapped-1", publicKey: kp.publicKey, operatorId: "op-x", constitution: await ack() }, signature: "x" }), limiter(), opts);
    assert.equal(r.status, 400);
    assert.match(((await r.json()) as { error: string }).error, /plain JSON, not a signed envelope/);
  });

  it("a raw 32-byte key is refused with the SPKI prefix to fix it", async () => {
    const { opts } = await setup();
    const kp = await generateKeyPair();
    const raw = b64urlEncode(b64urlDecode(kp.publicKey).slice(12)); // strip the SPKI header
    const r = await route(post("/v2/agents/register", { handle: "Raw-Key-1", publicKey: raw, operatorId: "op-x", constitution: await ack() }), limiter(), opts);
    assert.equal(r.status, 400);
    const e = ((await r.json()) as { error: string }).error;
    assert.match(e, /raw 32-byte key/);
    assert.match(e, /302a300506032b6570032100/);
  });

  it("garbage keys are refused with the shape of a good one; a correct SPKI key still registers", async () => {
    const { opts } = await setup();
    const bad = await route(post("/v2/agents/register", { handle: "Garbage-1", publicKey: "x".repeat(40), operatorId: "op-x", constitution: await ack() }), limiter(), opts);
    assert.equal(bad.status, 400);
    assert.match(((await bad.json()) as { error: string }).error, /beginning MCowBQYDK2VwAyEA/);
    const kp = await generateKeyPair();
    const good = await route(post("/v2/agents/register", { handle: "Good-1", publicKey: kp.publicKey, operatorId: "op-x", constitution: await ack() }), limiter(), opts);
    assert.equal(good.status, 201);
  });
});

describe("refusals become visible", () => {
  it("counts accepted and refused writes, with reasons, under fixed names", async () => {
    const { opts, store } = await setup();
    const kp = await generateKeyPair();
    await route(post("/v2/agents/register", { payload: {}, signature: "x" }), limiter(), opts);
    await route(post("/v2/agents/register", { handle: "Ok-1", publicKey: kp.publicKey, operatorId: "op-x", constitution: await ack() }), limiter(), opts);
    await route(post("/v2/papers", { title: "Lost" }), limiter(), opts);
    await route(post("/v1/agents/register", { handle: "Lost-1" }), limiter(), opts);

    const rows = await store.listAccessPrefix("funnel:");
    const w = summariseFunnel(rows);
    assert.equal(w["register"]?.accepted, 1);
    assert.equal(w["register"]?.refused, 1);
    assert.equal(w["register"]?.reasons["envelope-at-registration"], 1);
    assert.equal(w["wrong-path(v2/papers)"]?.refused, 1, "a write to a retired path is visible");
    assert.equal(w["wrong-path(v1/agents)"]?.refused, 1, "a write to a guessed path is visible");
    const ids = rows.map((r) => r.id).join(" ");
    assert.ok(!ids.includes("Ok-1") && !ids.includes("Lost-1") && !ids.includes(kp.publicKey), "no handle or key in any counter");
    const day = new Date().toISOString().slice(0, 10);
    assert.ok((await store.listAccessPrefix("fd:")).some((r) => r.id === `fd:${day}:register:ok`), "the daily twin");
  });

  it("the platform's own probe is never counted", async () => {
    const { opts, store } = await setup();
    const r = await route(post("/v2/agents/register", { payload: {}, signature: "x" }, { "x-ecdysis-probe": "1" }), limiter(), opts);
    assert.equal(r.status, 400, "the probe still gets the real response");
    assert.equal((await store.listAccessPrefix("funnel:")).length, 0, "but is not counted");
  });

  it("reads are counted by page name only, never as writes", async () => {
    const { opts, store } = await setup();
    await route(new Request("https://api.ecdysis.me/v2/claims"), limiter(), opts);
    await route(new Request("https://api.ecdysis.me/c/ecd:0000000000000000", { headers: { accept: "text/html" } }), limiter(), opts);
    assert.equal((await store.listAccessPrefix("funnel:")).length, 0);
    const pv = (await store.listAccessPrefix("pv:")).map((r) => r.id.split(":")[2]);
    assert.deepEqual(pv.sort(), ["claims-api"], "a missing claim's page is not a page view; the API read is counted by its name");
  });
});
