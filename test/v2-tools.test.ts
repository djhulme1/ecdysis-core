/**
 * The connector tools through the MCP dispatcher (listed with titles and
 * annotations, writes signed by the agent, refusals as tool errors with the
 * status), the receipt flow end to end over HTTP through the router, the
 * recomputation of every served number from the log alone, and the sitemap.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { MemoryStore } from "../src/store/memory-store.js";
import { TransparencyLog } from "../src/core/log.js";
import { structuralScreener } from "../src/core/hazard.js";
import { generateKeyPair, signJson } from "../src/core/crypto.js";
import { handleMcp } from "../src/api/mcp.js";
import { MemoryV2Store, V2Service } from "../src/api/v2/service.js";
import { v2Tools } from "../src/api/v2/tools.js";
import { LogApi } from "../src/api/v2/log-api.js";
import { PagesHandler } from "../src/api/v2/pages.js";
import { MemoryRateLimiter, route, type RouteOptions } from "../src/api/router.js";
import { recomputeV2 } from "../src/api/v2/recompute.js";
import type { Json } from "../src/core/canonical.js";
import { CONSTITUTION_VERSION, constitutionHash } from "../src/core/constitution.js";
import { declared } from "./kinds-kit.js";
import { signedClaim } from "./claims-kit.js";
const ACK = { version: CONSTITUTION_VERSION, hash: await constitutionHash() };

async function world() {
  const store = new MemoryStore();
  const log = new TransparencyLog(store);
  const logKey = await generateKeyPair();
  const v2 = new MemoryV2Store(() => (store as unknown as { log: Array<{ entry: { seq: number; ts: string; type: string }; payload: Json }> }).log.map((r) => ({ seq: r.entry.seq, ts: r.entry.ts, type: r.entry.type, payload: r.payload })));
  const svc = new V2Service({ log, store: v2, logPrivateKey: logKey.privateKey, screeners: [structuralScreener()] });
  const logApi = new LogApi({ log, reader: store, signingKey: logKey.privateKey });
  const pages = new PagesHandler(svc, { host: "api.ecdysis.me", logPublicKey: logKey.publicKey, log: logApi, archive: "https://v1.ecdysis.me" });
  const opts: RouteOptions = { v2: svc, log: logApi, pages, sthPublicKey: logKey.publicKey, archive: "https://v1.ecdysis.me" };
  const limiter = new MemoryRateLimiter(1000);
  const post = async (path: string, body: Json) => {
    const r = await route(new Request(`https://api.ecdysis.me${path}`, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body) }), limiter, opts);
    return { status: r.status, body: (await r.json()) as Record<string, Json> };
  };
  const get = async (path: string) => {
    const r = await route(new Request(`https://api.ecdysis.me${path}`), limiter, opts);
    return { status: r.status, body: (await r.json()) as Record<string, Json> };
  };
  const site = async (path: string) => route(new Request(`https://ecdysis.me${path}`, { headers: { accept: "text/html" } }), limiter, opts);
  return { store, log, logKey, svc, logApi, pages, opts, limiter, post, get, site };
}

describe("the connector tools", () => {
  it("lists them with titles and annotations, runs a signed write, and answers a refused read as a tool error", async () => {
    const w = await world();
    const ctx = { host: "api.ecdysis.me", logKey: w.logKey.publicKey, tools: v2Tools(w.svc, "local", null, null, null, w.logApi) };
    const list = await handleMcp({ jsonrpc: "2.0", id: 1, method: "tools/list" } as unknown as Json, ctx);
    const tools = ((list.body as { result: { tools: Array<{ name: string; title?: string; annotations?: Record<string, unknown> }> } }).result).tools;
    const names = tools.map((t) => t.name);
    for (const n of ["get_direction", "get_map", "get_claims", "get_claim", "get_heartbeat", "get_credence", "register_agent", "publish_claims", "register_claim", "commit_check", "file_result", "file_review", "file_attempt", "escalate", "about", "get_constitution", "get_tree_head", "get_inclusion_proof", "set_doorbell", "stop_doorbell"]) assert.ok(names.includes(n), n);
    assert.equal(new Set(names).size, names.length, "no tool is listed twice");
    for (const n of ["publish_paper", "submit_paper", "get_frontier", "get_challenges", "get_graph", "vouch", "describe_check", "set_scope"]) assert.ok(!names.includes(n), `${n} is gone with the papers`);
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
    const claim = await call("register_claim", { envelope: { payload: declared(payload), signature: await signJson(kp.privateKey, declared(payload)) } });
    assert.equal(claim.body["http_status"], 201, JSON.stringify(claim.body));
    const forged = await call("register_claim", { envelope: { payload: declared(payload), signature: "AAAA".repeat(20) } });
    assert.equal(forged.isError, true);
    assert.equal(forged.body["http_status"], 401);
    const hb = await call("get_heartbeat", { agent: "Moth-1" });
    assert.equal(hb.isError, false);
    assert.equal(hb.body["tier"], "unverified");
    assert.ok(Array.isArray(hb.body["next"]), "the heartbeat carries what to do next");
    const dir = await call("get_direction", {});
    assert.ok(Array.isArray(dir.body["next"]));
    const map = await call("get_map", {});
    assert.ok(Array.isArray(map.body["fields"]));

    // A refused read is a tool error carrying the status the HTTP API would have answered, not ordinary data the model
    // might read as a fact (an agent asking for a receipt that does not exist must see the refusal).
    const noReceipt = await call("get_receipt", { id: "0".repeat(64) });
    assert.equal(noReceipt.isError, true, "an unknown receipt is a tool error");
    assert.equal(noReceipt.body["http_status"], 404);
    assert.equal(noReceipt.body["error"], "no such receipt");
    const noAgent = await call("get_heartbeat", { agent: "Nobody-9" });
    assert.equal(noAgent.isError, true, "an unknown agent is a tool error");
    assert.equal(noAgent.body["http_status"], 404);
    const noClaim = await call("get_arguments", { claim: "ext:0000000000000000" });
    assert.equal(noClaim.isError, true);
    assert.equal(noClaim.body["http_status"], 404);
    const noArgs = await call("get_arguments", {});
    assert.equal(noArgs.isError, true, "neither claim nor id given is a refusal, with the missing argument named");
    assert.equal(noArgs.body["http_status"], 400);
    assert.match(String(noArgs.body["error"]), /claim/);
    const noAttempts = await call("get_attempts", { claim: "ext:0000000000000000" });
    assert.equal(noAttempts.isError, true);
    assert.equal(noAttempts.body["http_status"], 404);
    const someArgs = await call("get_arguments", { claim: String(claim.body["ref"]) });
    assert.equal(someArgs.isError, false, JSON.stringify(someArgs.body));
    assert.ok(Array.isArray(someArgs.body["arguments"]), "a known claim's arguments are data");
    const head = await call("get_tree_head", {});
    assert.equal(head.isError, false);
    assert.ok(head.body["signature"], "signed");
  });
});

describe("the network over HTTP", () => {
  it("runs the receipt flow end to end through the router, with the steward's switches public and the paper era answered 410", async () => {
    const w = await world();
    const kp = await generateKeyPair();
    const reg = await w.post("/v2/agents/register", { handle: "Moth-1", publicKey: kp.publicKey, operatorId: "op-moth", constitution: ACK });
    assert.equal(reg.status, 201, JSON.stringify(reg.body));
    const sign = async (raw: Json) => { const payload = declared(raw); return { payload, signature: await signJson(kp.privateKey, payload) } as Json; };
    const ext = await w.post("/v2/claims/external", await sign({ protocol: "ecdysis/0.2", type: "claim.external", source: "arxiv:1706.03762", quote: "attention alone reaches 28.4 BLEU on WMT14 En-De", test: "BLEU below 27 with the stated setup", agent: { handle: "Moth-1", publicKey: kp.publicKey }, ts: "2026-10-03T09:00:00Z" }));
    assert.equal(ext.status, 201);
    const ref = String(ext.body["ref"]);
    const commit = await w.post("/v2/checks", await sign({ protocol: "ecdysis/0.2", type: "check.commit", target: ref, kind: "replication", bundle: { repo: "https://github.com/example/rep", commit: "a".repeat(40), run: "python run.py", outputs: [{ name: "bleu", tolerance: 0.1 }], runtimeMinutes: 20 }, agent: { handle: "Moth-1", publicKey: kp.publicKey }, ts: "2026-10-03T09:01:00Z" }));
    assert.equal(commit.status, 201, JSON.stringify(commit.body));
    const res = await w.post("/v2/checks/result", await sign({ protocol: "ecdysis/0.2", type: "check.result", commit: commit.body["id"] ?? null, outcome: "confirmed", outputs: { bleu: 28.3 }, crossCheck: null, agent: { handle: "Moth-1", publicKey: kp.publicKey }, ts: "2026-10-03T09:02:00Z" }));
    assert.equal(res.status, 201, JSON.stringify(res.body));
    const rec = await w.get("/v2/record");
    assert.equal(rec.body["receipts"], 1);
    assert.deepEqual(rec.body["settings"], { "v2.registration": "open", "v2.publishing": "open", "v2.external": "open", "v2.checks": "open", "v2.reviews": "open", "v2.arguments": "open", "v2.amendments": "open", "v2.flags": "open" }, "the steward's switches are public; attempts have none (attempts/0.3)");
    const cred = await w.get("/v2/credence");
    const claims = cred.body["claims"] as Array<Record<string, Json>>;
    assert.equal(claims[0]!["ref"], ref);
    assert.equal(claims[0]!["status"], "unchecked", "the registrant's own unverified receipt moves credence but cannot resolve");
    assert.equal((await w.get("/v2/heartbeat?agent=Moth-1")).status, 200);
    assert.deepEqual((await w.get("/v2/holds")).body["holds"], [], "nothing held");
    // R1 over HTTP: no operator key on this service, so holds stay held and nobody can decide them from here.
    assert.equal((await w.post("/v2/hazard/decision", { subject: ref, decision: "release", signature: "x" })).status, 501);
    assert.equal((await w.get("/v2/nothing")).status, 404);
    // The paper era's writes answer 410 with where the work went; the first record's API is archived.
    const paper = await w.post("/v2/papers", { payload: {}, signature: "x" });
    assert.equal(paper.status, 410);
    assert.match(String(paper.body["error"]), /there are no papers/);
    const v1write = await w.post("/v1/agents/register", { handle: "Old-1", publicKey: kp.publicKey, operatorId: "op-old" });
    assert.equal(v1write.status, 410);
    assert.match(String(v1write.body["error"]), /archived/);
    assert.equal((await w.get("/v1/stats")).status, 410);

    // The launcher types the network's prompts: direction and receipts, never juries or papers; the GitHub fallback is the protocol on main.
    const launch = async (what: string) => route(new Request(`https://ecdysis.me/o/chatgpt/${what}`), w.limiter, w.opts);
    const l = await launch("famous");
    assert.equal(l.status, 302);
    const typed = decodeURIComponent(l.headers.get("location")!);
    assert.match(typed, /get_direction/);
    assert.match(typed, /file the outputs as a receipt/);
    assert.doesNotMatch(typed, /jury|challenges|paper|people#stuck/);
    assert.match(typed, /ecdysis-core\/main\/docs\/skill\.md/, "the GitHub fallback is the protocol, at docs/skill.md on main");
    assert.equal((await launch("juror")).status, 404, "a first-record starter is not offered");
    assert.equal((await launch("paste")).status, 404);
  });
});

describe("verify, don't trust", () => {
  it("recomputes every served credence from the public log alone, through the router", async () => {
    const w = await world();
    const getJson = async <T>(path: string): Promise<T> => {
      const r = await route(new Request(`https://api.ecdysis.me${path}`), w.limiter, w.opts);
      if (!r.ok) throw new Error(`${path}: ${r.status}`);
      return (await r.json()) as T;
    };
    const sign = async (kp: { privateKey: string }, raw: Json) => { const payload = declared(raw); return { payload, signature: await signJson(kp.privateKey, payload) } as Json; };
    const a = await generateKeyPair(); const b = await generateKeyPair(); const c = await generateKeyPair();
    for (const [h, kp, op, m] of [["Ant", a, "op-a", "claude"], ["Bee", b, "op-b", "gpt"], ["Cat", c, "op-c", "gemini"]] as const) {
      assert.equal((await w.svc.registerAgent({ handle: h, publicKey: kp.publicKey, operatorId: op, models: [m], constitution: ACK })).status, 201);
      await w.svc.setTier(op, "verified");
    }
    const ext = await w.svc.registerExternalClaim(await sign(a, { protocol: "ecdysis/0.2", type: "claim.external", source: "arxiv:1706.03762", quote: "attention alone reaches 28.4 BLEU on WMT14 En-De", test: "BLEU below 27 with the stated setup", agent: { handle: "Ant", publicKey: a.publicKey }, ts: "2026-10-03T09:00:00Z" }));
    const ref = String((ext.body as Record<string, Json>)["ref"]);
    const own = await signedClaim({ handle: "Ant", ...a }, { ts: "2026-10-03T09:00:30Z" });
    assert.equal((await w.svc.publishClaim(own.envelope)).status, 201);
    const bundle = (n: number) => ({ repo: "https://github.com/example/rep", commit: n.toString(16).padStart(40, "0"), image: "sha256:" + "a".repeat(64), run: "python run.py", outputs: [{ name: "alpha", tolerance: 0.01 }], runtimeMinutes: 5 });
    const c1 = await w.svc.commitCheck(await sign(b, { protocol: "ecdysis/0.2", type: "check.commit", target: ref, kind: "replication", bundle: bundle(1) as unknown as Json, agent: { handle: "Bee", publicKey: b.publicKey }, ts: "2026-10-03T09:00:00Z" }));
    const id1 = String((c1.body as Record<string, Json>)["id"]);
    await w.svc.fileResult(await sign(b, { protocol: "ecdysis/0.2", type: "check.result", commit: id1, outcome: "confirmed", outputs: { alpha: 28.4 }, crossCheck: null, agent: { handle: "Bee", publicKey: b.publicKey }, ts: "2026-10-03T09:01:00Z" }));
    await w.svc.fileReview(await sign(c, { protocol: "ecdysis/0.2", type: "review", claim: ref, forecast: 0.7, rationale: "Widely reproduced; the setup is standard and the figure is conservative for the stated hardware.", agent: { handle: "Cat", publicKey: c.publicKey }, ts: "2026-10-03T09:02:00Z" }));
    const report = await recomputeV2(getJson, new Date(), { publicKey: w.logKey.publicKey });
    assert.deepEqual(report.mismatches, []);
    assert.equal(report.compared, 2, "the registered claim and the published one");
    assert.ok(report.entries >= 9, "registrations, tiers, the claims, the receipt and the review are all public");
    assert.equal(report.receipts, 1);
    // The review is public as filed: nothing withheld, the forecast present; the claim's words are on the log.
    const page = await getJson<{ entries: Array<{ type: string; payload: Record<string, unknown>; withheld?: string[] }> }>("/v2/log/entries?from=0&limit=200");
    const review = page.entries.find((e) => e.type === "review.file")!;
    assert.equal(review.withheld, undefined);
    assert.equal(review.payload["forecast"], 0.7);
    const published = page.entries.find((e) => e.type === "claim.publish")!;
    assert.equal(published.payload["id"], own.id);
    assert.equal(published.payload["text"], "Grokking appears in modular addition after weight decay.");
  });
});

describe("the sitemap", () => {
  it("lists the network's pages and the claims in view, never unchecked work from an operator with no standing", async () => {
    const w = await world();
    const sitemap = await (await w.site("/sitemap.xml")).text();
    for (const p of ["/claims", "/map", "/leaderboard", "/lab", "/kit", "/api"]) assert.match(sitemap, new RegExp(`<loc>https://ecdysis\\.me${p}</loc>`), p);
    assert.doesNotMatch(sitemap, /\/papers<|\/frontier<|\/graph<|\/review<|\/dashboard<|\/commons<|\/apps<|\/charter<|\/about</, "no retired or moved page is advertised");
    const kp = await generateKeyPair();
    assert.equal((await w.svc.registerAgent({ constitution: ACK, handle: "Moth-2", publicKey: kp.publicKey, operatorId: "op-moth" })).status, 201);
    const c = await signedClaim({ handle: "Moth-2", ...kp }, { ts: "2026-10-03T09:00:00Z" });
    assert.equal((await w.svc.publishClaim(c.envelope)).status, 201);
    const loc = new RegExp(`<loc>https://ecdysis\\.me/c/${c.id.replace(/[.:]/g, "\\$&")}</loc>`);
    // An operator with no account is listed once someone else checks its work (core/v2/visibility.ts); with an account, at once.
    assert.doesNotMatch(await (await w.site("/sitemap.xml")).text(), loc, "unchecked work from an operator with no account is not advertised");
    await w.svc.setTier("op-moth", "account");
    assert.match(await (await w.site("/sitemap.xml")).text(), loc, "published claims are listed");
  });
});
