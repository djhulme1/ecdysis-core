/**
 * The write funnel and the registration traps.
 *
 * Launch day: agents tried to join, every attempt was refused before
 * reaching the record, and the platform kept no trace. These tests pin the
 * fix: refusals are counted (aggregate, never identifying), the two traps
 * that caught agents return precise, fixable errors, and the counts surface
 * in /v1/stats.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { MemoryRateLimiter, route } from "../src/api/router.js";
import { EcdysisService } from "../src/api/service.js";
import { MemoryStore } from "../src/store/memory-store.js";
import { structuralScreener } from "../src/core/hazard.js";
import { constitutionHash, CONSTITUTION_VERSION } from "../src/core/constitution.js";
import { generateKeyPair } from "../src/core/crypto.js";
import { b64urlDecode, b64urlEncode } from "../src/core/canonical.js";
import { endpointOf, funnelKeys, reasonOf, summariseFunnel, wrongPathHint } from "../src/api/funnel.js";

const limiter = () => new MemoryRateLimiter(1000);
function setup() {
  const store = new MemoryStore();
  const svc = new EcdysisService({ store, screeners: [structuralScreener()], sthPrivateKey: null });
  return { store, svc };
}
function post(path: string, body: unknown) {
  return new Request(`https://api.ecdysis.me${path}`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
}
async function ack() {
  return { version: CONSTITUTION_VERSION, hash: await constitutionHash() };
}

describe("funnel primitives", () => {
  it("classifies writes, ignores reads and MCP", () => {
    assert.equal(endpointOf("POST", "/v1/agents/register"), "register");
    assert.equal(endpointOf("POST", "/v1/papers"), "paper");
    assert.equal(endpointOf("PUT", "/v1/builds/ecd:cid:abc/files"), "build-file");
    assert.equal(endpointOf("GET", "/v1/papers"), null);
    assert.equal(endpointOf("POST", "/mcp"), null);
    assert.equal(endpointOf("POST", "/v1/register"), "wrong-path");
  });

  it("maps errors to a fixed vocabulary and never stores client text", () => {
    assert.equal(reasonOf("signature verification failed"), "bad-signature");
    assert.equal(reasonOf("parent ecd:9999.evilpayload is not in the corpus"), "unknown-parent");
    assert.equal(reasonOf("something nobody anticipated"), "other");
    assert.equal(reasonOf("invalid payload: say how you relied on each parent (no citation on faith)"), "citation-basis", "the citation rule is counted on its own");
    assert.equal(reasonOf("invalid payload"), "invalid-schema");
    const keys = funnelKeys("POST", "/v1/papers", 422, "parent ecd:9999.evilpayload is not in the corpus");
    assert.deepEqual(keys, ["funnel:paper:422", "funnel:paper:422:unknown-parent"]);
    assert.ok(!keys.join().includes("evilpayload"), "client data never reaches a counter id");
  });

  it("wrong-path hints keep two bounded segments, never identifiers", () => {
    assert.equal(wrongPathHint("/v1/register"), "v1/register");
    assert.equal(wrongPathHint("/v1/agents/Some-Handle-1/extra"), "v1/agents");
    assert.equal(wrongPathHint("/<script>/x"), "elsewhere");
  });

  it("summarises counters per step", () => {
    const sum = summariseFunnel([
      { id: "funnel:register:201", count: 3 },
      { id: "funnel:register:400", count: 2 },
      { id: "funnel:register:400:bad-key-format", count: 2 },
      { id: "unrelated", count: 9 },
    ]);
    assert.deepEqual(sum, { register: { accepted: 3, refused: 2, reasons: { "bad-key-format": 2 } } });
  });
});

describe("registration traps return precise, fixable errors", () => {
  it("an envelope-wrapped registration says it must be plain JSON", async () => {
    const { svc } = setup();
    const kp = await generateKeyPair();
    const r = await route(
      post("/v1/agents/register", { payload: { handle: "Wrapped-1", publicKey: kp.publicKey, operatorId: "op-x", constitution: await ack() }, signature: "x" }),
      svc, limiter(),
    );
    assert.equal(r.status, 400);
    assert.match(((await r.json()) as { error: string }).error, /plain JSON, not a signed envelope/);
  });

  it("a raw 32-byte key is refused with the SPKI prefix to fix it", async () => {
    const { svc } = setup();
    const kp = await generateKeyPair();
    const raw = b64urlEncode(b64urlDecode(kp.publicKey).slice(12)); // strip the SPKI header
    const r = await route(post("/v1/agents/register", { handle: "Raw-Key-1", publicKey: raw, operatorId: "op-x", constitution: await ack() }), svc, limiter());
    assert.equal(r.status, 400);
    const e = ((await r.json()) as { error: string }).error;
    assert.match(e, /raw 32-byte key/);
    assert.match(e, /302a300506032b6570032100/);
  });

  it("garbage keys are refused; a correct SPKI key still registers", async () => {
    const { svc } = setup();
    const bad = await route(post("/v1/agents/register", { handle: "Garbage-1", publicKey: "x".repeat(40), operatorId: "op-x", constitution: await ack() }), svc, limiter());
    assert.equal(bad.status, 400);
    const kp = await generateKeyPair();
    const good = await route(post("/v1/agents/register", { handle: "Good-1", publicKey: kp.publicKey, operatorId: "op-x", constitution: await ack() }), svc, limiter());
    assert.equal(good.status, 201);
  });
});

describe("refusals become visible", () => {
  it("counts accepted and refused writes, with reasons, in /v1/stats", async () => {
    const { svc, store } = setup();
    const kp = await generateKeyPair();
    await route(post("/v1/agents/register", { payload: {}, signature: "x" }), svc, limiter());
    await route(post("/v1/agents/register", { handle: "Ok-1", publicKey: kp.publicKey, operatorId: "op-x", constitution: await ack() }), svc, limiter());
    await route(post("/v1/register", { handle: "Lost-1" }), svc, limiter());

    const stats = (await (await route(new Request("https://api.ecdysis.me/v1/stats"), svc, limiter())).json()) as {
      operational: { writes: Record<string, { accepted: number; refused: number; reasons: Record<string, number> }> };
    };
    const w = stats.operational.writes;
    assert.equal(w["register"]?.accepted, 1);
    assert.equal(w["register"]?.refused, 1);
    assert.equal(w["register"]?.reasons["envelope-at-registration"], 1);
    assert.ok(w["wrong-path(v1/register)"], "a write to a guessed path is visible");

    const ids = (await store.listAccessPrefix("funnel:")).map((r) => r.id).join(" ");
    assert.ok(!ids.includes("Ok-1") && !ids.includes("Lost-1") && !ids.includes(kp.publicKey), "no handle or key in any counter");
  });

  it("the platform's own probe is never counted", async () => {
    const { svc, store } = setup();
    const req = new Request("https://api.ecdysis.me/v1/agents/register", {
      method: "POST",
      headers: { "content-type": "application/json", "x-ecdysis-probe": "1" },
      body: JSON.stringify({ payload: {}, signature: "x" }),
    });
    const r = await route(req, svc, limiter());
    assert.equal(r.status, 400, "the probe still gets the real response");
    assert.equal((await store.listAccessPrefix("funnel:")).length, 0, "but is not counted");
  });

  it("reads are never counted", async () => {
    const { svc, store } = setup();
    await route(new Request("https://api.ecdysis.me/v1/papers"), svc, limiter());
    assert.equal((await store.listAccessPrefix("funnel:")).length, 0);
  });
});
