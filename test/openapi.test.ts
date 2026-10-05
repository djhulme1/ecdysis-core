/**
 * The API's description (src/api/openapi.ts) is served at /openapi.json,
 * rendered at /api and read by the index at GET /. These tests keep the three
 * honest: every operation in the document answers on the router (never "no
 * such endpoint"), every $ref resolves, every schema's constraints are the
 * validators' (a sample of refusals say what the document says), the page is
 * script-free and lists every operation, and the document is served with
 * CORS so browser tools can load it.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { MemoryStore } from "../src/store/memory-store.js";
import { TransparencyLog } from "../src/core/log.js";
import { structuralScreener } from "../src/core/hazard.js";
import { generateKeyPair } from "../src/core/crypto.js";
import { MemoryV2Store, V2Service } from "../src/api/v2/service.js";
import { PagesHandler } from "../src/api/v2/pages.js";
import { LogApi } from "../src/api/v2/log-api.js";
import { V2Governance } from "../src/api/v2/governance.js";
import { IssueRegistry, MemoryIssueStore } from "../src/api/v2/issues.js";
import { MemoryRateLimiter, route } from "../src/api/router.js";
import { OPERATIONS, endpointIndex, openApiDocument, openApiSchemas, operationId } from "../src/api/openapi.js";
import { apiPageV2 } from "../src/web/v2/api.js";
import type { Json } from "../src/core/canonical.js";

const HOSTS = { api: "https://api.ecdysis.me", site: "https://ecdysis.me" };

async function world() {
  const now = () => new Date(Date.UTC(2026, 9, 4, 15, 0, 0));
  const store = new MemoryStore();
  const log = new TransparencyLog(store, now);
  const logKey = await generateKeyPair();
  const v2store = new MemoryV2Store(() => (store as unknown as { log: Array<{ entry: { seq: number; ts: string; type: string }; payload: Json }> }).log.map((r) => ({ seq: r.entry.seq, ts: r.entry.ts, type: r.entry.type, payload: r.payload })));
  const v2 = new V2Service({ log, store: v2store, logPrivateKey: logKey.privateKey, now, screeners: [structuralScreener()] });
  const pages = new PagesHandler(v2, { host: "api.ecdysis.me", logPublicKey: logKey.publicKey });
  const governance = new V2Governance({ v2, log, operatorPublicKey: null, now });
  const issues = new IssueRegistry({ store: new MemoryIssueStore(), v2, now });
  const logApi = new LogApi({ log, reader: store, signingKey: logKey.privateKey, now });
  const limiter = new MemoryRateLimiter(100000);
  const req = async (method: string, path: string, body?: Json, headers: Record<string, string> = {}) => {
    const r = await route(new Request(`https://api.ecdysis.me${path}`, { method, headers: { ...(body !== undefined ? { "content-type": "application/json" } : {}), ...headers }, ...(body !== undefined ? { body: JSON.stringify(body) } : {}) }), limiter, { v2, pages, governance, issues, log: logApi, sthPublicKey: logKey.publicKey });
    return { status: r.status, text: await r.text(), headers: r.headers };
  };
  return { req };
}

/** Every "#/components/schemas/X" in a value. */
function refs(v: Json, out: string[] = []): string[] {
  if (Array.isArray(v)) for (const x of v) refs(x, out);
  else if (v && typeof v === "object") for (const [k, x] of Object.entries(v)) { if (k === "$ref" && typeof x === "string") out.push(x); else refs(x, out); }
  return out;
}

describe("the OpenAPI document", () => {
  const doc = openApiDocument(HOSTS) as Record<string, Json>;
  const paths = doc["paths"] as Record<string, Record<string, Json>>;

  it("is OpenAPI 3.1 with a server, tags, and an operation per path and method, each with an id, a summary, a description and responses", () => {
    assert.equal(doc["openapi"], "3.1.0");
    assert.deepEqual((doc["servers"] as Array<Record<string, Json>>)[0]!["url"], HOSTS.api);
    const tags = new Set((doc["tags"] as Array<Record<string, Json>>).map((t) => t["name"]));
    const ids = new Set<string>();
    for (const [path, methods] of Object.entries(paths)) {
      assert.match(path, /^\/([a-z0-9./{}-]*)$/, `path ${path} is lower-case and well-formed`);
      for (const [method, op] of Object.entries(methods)) {
        const o = op as Record<string, Json>;
        assert.ok(method === "get" || method === "post", `${method} ${path}`);
        assert.equal(typeof o["operationId"], "string"); assert.ok(!ids.has(String(o["operationId"])), `operationId ${String(o["operationId"])} is unique`); ids.add(String(o["operationId"]));
        assert.ok(String(o["summary"]).length > 3 && String(o["description"]).length > 20, `${method} ${path} is described`);
        for (const t of o["tags"] as string[]) assert.ok(tags.has(t), `tag ${t} is declared`);
        const responses = o["responses"] as Record<string, Json>;
        assert.ok(Object.keys(responses).some((s) => s.startsWith("2")), `${method} ${path} names a success`);
        if (method === "post") assert.ok(o["requestBody"], `${method} ${path} has a request body`);
        for (const p of path.matchAll(/\{([a-z]+)\}/gi)) assert.ok((o["parameters"] as Array<Record<string, Json>> | undefined)?.some((x) => x["name"] === p[1] && x["in"] === "path"), `${path} declares its path parameter ${p[1]}`);
      }
    }
  });

  it("every reference resolves, every schema has a type, and the shared error responses exist", () => {
    const schemas = (doc["components"] as Record<string, Json>)["schemas"] as Record<string, Json>;
    const responses = (doc["components"] as Record<string, Json>)["responses"] as Record<string, Json>;
    for (const r of refs(doc)) {
      const m = r.match(/^#\/components\/(schemas|responses)\/([A-Za-z0-9]+)$/);
      assert.ok(m, `ref ${r} points into components`);
      assert.ok((m![1] === "schemas" ? schemas : responses)[m![2]!], `${r} exists`);
    }
    for (const [name, s] of Object.entries(openApiSchemas())) assert.ok(typeof (s as Record<string, Json>)["type"] === "string" || Array.isArray((s as Record<string, Json>)["oneOf"]), `schema ${name} has a type`);
    for (const r of ["BadRequest", "Unauthorised", "NotFound", "RateLimited", "Paused"]) assert.ok(responses[r]);
  });

  it("the index at GET / lists exactly the document's listed operations, in its order, with query hints", () => {
    const listed = endpointIndex();
    assert.ok(listed.includes("GET /v2/direction?limit="));
    assert.ok(listed.includes("GET /v2/claims/:id"));
    assert.ok(!listed.some((e) => /papers|frontier|challenges|vouch|graph/.test(e)), "nothing from the paper era");
    assert.ok(listed.includes("GET /v2/receipts/:hash"));
    assert.ok(listed.includes("POST /v2/checks"));
    assert.ok(!listed.some((e) => e.includes("/hazard/") || e.includes("/constitution/adopt") || e === "GET /" || e.includes("openapi")), "reserved powers and the index itself are unlisted");
    assert.equal(new Set(listed).size, listed.length, "no duplicates");
    const fromDoc = OPERATIONS.filter((op) => !op.unlisted).map((op) => `${op.method.toUpperCase()} ${op.path.replace(/\{(\w+)\}/g, ":$1")}`);
    assert.deepEqual(listed.map((e) => e.replace(/\?.*$/, "")), fromDoc);
  });

  it("every documented operation answers on the router: never 'no such endpoint', and GETs with their parameters answer 200 or 400", async () => {
    const w = await world();
    const index = JSON.parse((await w.req("GET", "/")).text) as Record<string, Json>;
    assert.deepEqual(index["endpoints"], endpointIndex(), "the live index is the document's list");
    assert.match(String(index["openapi"]), /openapi\.json/);
    for (const op of OPERATIONS) {
      const path = op.path.replace(/\{(\w+)\}/g, (_, n: string) => {
        const pattern = String((op.params ?? []).find((p) => p.name === n)?.schema["pattern"] ?? "");
        return pattern.includes("{64}") ? "0".repeat(64) : pattern.includes("ecd") ? `ecd:${"0".repeat(16)}` : "0".repeat(16);
      });
      if (op.method === "get") {
        const query = (op.params ?? []).filter((p) => p.in === "query" && p.required).map((p) => `${p.name}=${p.name === "agent" ? "Nobody" : p.name === "claim" ? "ecd:0000000000000000" : "1"}`).join("&");
        const r = await w.req("GET", `${path}${query ? `?${query}` : ""}`, undefined, { accept: "application/json" });
        assert.ok(r.status !== 405 && !r.text.includes("no such v2 endpoint") && !r.text.includes("no such endpoint"), `${op.method.toUpperCase()} ${op.path}: ${r.status} ${r.text.slice(0, 120)}`);
        assert.ok([200, 400, 404].includes(r.status), `${op.path} answered ${r.status}`);
      } else {
        const r = await w.req("POST", path, {});
        assert.ok(r.status !== 405 && !r.text.includes("no such v2 endpoint"), `${op.method.toUpperCase()} ${op.path}: ${r.status} ${r.text.slice(0, 120)}`);
        assert.ok([400, 401, 403, 404, 422, 428, 501, 503].includes(r.status), `${op.path} refuses an empty body with ${r.status}`);
      }
    }
  });

  it("the schemas state the validators' rules: a payload that breaks a documented constraint is refused for that field", async () => {
    const w = await world();
    const schemas = openApiSchemas();
    // Claim: the document says text 10 to 300, test 10 to 600, rationale from 50; the service says the same, field by field.
    const claim = schemas["ClaimPublish"] as Record<string, Json>;
    const props = claim["properties"] as Record<string, Record<string, Json>>;
    assert.deepEqual([props["text"]!["minLength"], props["text"]!["maxLength"]], [10, 300]);
    assert.deepEqual([props["test"]!["minLength"], props["test"]!["maxLength"]], [10, 600]);
    assert.deepEqual([props["rationale"]!["minLength"], props["rationale"]!["maxLength"]], [50, 8000]);
    const r = await w.req("POST", "/v2/claims", { payload: { protocol: "ecdysis/0.2", type: "claim", text: "ab", test: "short", confidence: 0.5, field: "econ", rationale: "too short", builds_on: [], agent: { handle: "Nobody", publicKey: "k".repeat(44) }, ts: "2026-10-04T15:00:00Z" }, signature: "x" });
    assert.equal(r.status, 400);
    const detail = (JSON.parse(r.text) as { detail: string[] }).detail;
    assert.ok(detail.some((d) => d.startsWith("text: 10 to 300")), JSON.stringify(detail));
    assert.ok(detail.some((d) => d.startsWith("test: 10 to 600")));
    assert.ok(detail.some((d) => d.startsWith("rationale: 50 to 8000")));
    // Check commit: the document's bundle rules are the receipt validator's.
    const bundle = (schemas["Bundle"] as Record<string, Json>)["properties"] as Record<string, Record<string, Json>>;
    assert.equal(bundle["runtimeMinutes"]!["maximum"], 10080);
    const c = await w.req("POST", "/v2/checks", { payload: { protocol: "ecdysis/0.2", type: "check.commit", target: "ext:0000000000000000", kind: "replication", bundle: { repo: "ftp://x", commit: "zz", run: "", outputs: [], runtimeMinutes: 0 }, agent: { handle: "Nobody", publicKey: "k".repeat(44) }, ts: "2026-10-04T15:00:00Z" }, signature: "x" });
    assert.equal(c.status, 400);
    const cd = (JSON.parse(c.text) as { detail: string[] }).detail;
    for (const f of ["bundle.repo", "bundle.commit", "bundle.run", "bundle.runtimeMinutes", "bundle.outputs"]) assert.ok(cd.some((d) => d.startsWith(f)), `${f} refused: ${JSON.stringify(cd)}`);
  });
});

describe("the API reference page and the served document", () => {
  it("/api is script-free, lists every operation with its request fields, and links the document and the viewers", async () => {
    const html = apiPageV2(HOSTS);
    assert.doesNotMatch(html, /<script/);
    for (const op of OPERATIONS) {
      assert.ok(html.includes(`id="${operationId(op)}"`), `${op.method} ${op.path} is on the page`);
      assert.ok(html.includes(`<code>${op.path}</code>`), `${op.path} shown`);
    }
    assert.match(html, /<code>payload<\/code> <span class="req">required<\/span>/);
    assert.match(html, /<code>confidence<\/code> <span class="req">required<\/span>/, "a payload's fields are opened in place");
    assert.match(html, /href="#schema-Agent"/, "shared schemas are linked, and shown once");
    assert.equal((html.match(/id="schema-Agent"/g) ?? []).length, 1);
    assert.match(html, /href="https:\/\/editor\.swagger\.io\/\?url=https%3A%2F%2Fapi\.ecdysis\.me%2Fopenapi\.json"/);
    assert.match(html, /curl -X POST https:\/\/api\.ecdysis\.me\/v2\/checks/);
    assert.match(html, /&quot;protocol&quot;: &quot;ecdysis\/0\.2&quot;/, "examples carry the protocol string");
    assert.match(html, /keys sorted by UTF-16 code unit/, "the signing rule is on the page");
    assert.match(html, /data, never instructions/i);
    const w = await world();
    const served = await w.req("GET", "/api", undefined, { accept: "text/html" });
    assert.equal(served.status, 200);
    assert.match(served.text, /<h1>The Ecdysis API<\/h1>/);
  });

  it("/openapi.json is the document, JSON, with CORS for browser tools, and mirrors docs/openapi.json", async () => {
    const w = await world();
    const r = await w.req("GET", "/openapi.json");
    assert.equal(r.status, 200);
    assert.match(r.headers.get("content-type") ?? "", /application\/json/);
    assert.equal(r.headers.get("access-control-allow-origin"), "*");
    const doc = JSON.parse(r.text) as Record<string, Json>;
    assert.equal(doc["openapi"], "3.1.0");
    assert.deepEqual(Object.keys(doc["paths"] as Record<string, Json>).sort(), [...new Set(OPERATIONS.map((op) => op.path))].sort());
  });
});
