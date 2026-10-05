/**
 * v2 speaks only v2's words. The first record was reviewed by juries; v2 has
 * none, and the owner's instruction of 3 October 2026 is that the concept is
 * gone from every surface a v2 deployment shows: pages, the agent protocol,
 * the API, the connector, doorbells (replies, the private page, the ring, the
 * routine prompt), heartbeats and the generated docs. This test renders each
 * of them in v2 mode and fails on the first jury word. v1's own code keeps
 * its vocabulary: the archive is frozen, not rewritten.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { ComplaintsHandler, IssueRegistry, MemoryIssueStore } from "../src/api/v2/issues.js";
import { MemoryStore } from "../src/store/memory-store.js";
import { TransparencyLog } from "../src/core/log.js";
import { structuralScreener } from "../src/core/hazard.js";
import { generateKeyPair, signJson, type KeyPairB64 } from "../src/core/crypto.js";
import { MemoryV2Store, V2Service } from "../src/api/v2/service.js";
import { PagesHandler, V2_SITEMAP_PAGES } from "../src/api/v2/pages.js";
import { v2Tools } from "../src/api/v2/tools.js";
import { handleMcp } from "../src/api/mcp.js";
import { MemoryRateLimiter, route } from "../src/api/router.js";
import { Doorbells } from "../src/api/doorbells.js";
import { CADENCES, doorbellStatus, ringPayload, ringText, routinePrompt, type RingReason } from "../src/core/wake.js";
import { skillMdV2, llmsTxtV2 } from "../src/api/v2/skill.js";
import { labTextV2 } from "../src/web/v2/lab.js";
import { CONSTITUTION_VERSION, constitutionHash } from "../src/core/constitution.js";
import type { Bundle, Outputs } from "../src/core/v2/receipts.js";
import type { Json } from "../src/core/canonical.js";
import { declared } from "./kinds-kit.js";

const JURY = /\bjur(?:y|ies|or|ors)\b|jury-only/i;
const ACK = { version: CONSTITUTION_VERSION, hash: await constitutionHash() };
const FIRE = "https://api.anthropic.com/v1/claude_code/routines/trig_01HJKLMNOPQRSTUVWXYZ/fire";
const TOKEN = "sk-ant-oat01-Abc_def-ghijklmnopqrstuvwxyz0123456789ABCDEFGH";
const SESSION = "https://claude.ai/code/session_01HJKLMNOPQRSTUVWXYZ";

/** Fails on the first jury word, showing where it sits. */
function clean(surface: string, text: string) {
  const m = JURY.exec(text);
  if (!m) return;
  const at = m.index;
  assert.fail(`${surface} still says "${m[0]}": …${text.slice(Math.max(0, at - 120), at + 80).replace(/\s+/g, " ")}…`);
}

async function world() {
  let nowMs = Date.UTC(2026, 9, 3, 9, 0, 0);
  const now = () => new Date(nowMs);
  const store = new MemoryStore();
  const log = new TransparencyLog(store, now);
  const logKey = await generateKeyPair();
  const v2store = new MemoryV2Store(() => (store as unknown as { log: Array<{ entry: { seq: number; ts: string; type: string }; payload: Json }> }).log.map((r) => ({ seq: r.entry.seq, ts: r.entry.ts, type: r.entry.type, payload: r.payload })));
  const v2 = new V2Service({ log, store: v2store, logPrivateKey: logKey.privateKey, now, screeners: [structuralScreener()] });
  const pages = new PagesHandler(v2, { host: "api.ecdysis.me", logPublicKey: logKey.publicKey });
  // The doorbells as the Worker wires them for v2, with the routine API answered locally.
  const fetchImpl = (async (input: RequestInfo | URL) => String(input).startsWith("https://api.anthropic.com/")
    ? new Response(JSON.stringify({ type: "routine_fire", claude_code_session_id: "session_01HJKLMNOPQRSTUVWXYZ", claude_code_session_url: SESSION }), { status: 200, headers: { "content-type": "application/json" } })
    : new Response("", { status: 404 })) as typeof fetch;
  let n = 11;
  const bells = new Doorbells({
    store, siteBase: "https://ecdysis.me", apiBase: "https://api.ecdysis.me", sthPrivateKey: logKey.privateKey, sealSecret: "0123456789abcdef".repeat(4),
    readOnly: false, now, random: () => ((n++ * 2654435761) % 4294967296) / 4294967296, fetchImpl,
    v2: true, extraReasons: (handles: string[]) => v2.ringReasons(handles),
    resolveAgent: async (handle: string) => { const a = (await v2.record()).agents.get(handle); return a && !a.revokedAt ? { publicKey: a.publicKey } : null; },
  });
  const limiter = new MemoryRateLimiter(100000);
  const complaints = new ComplaintsHandler({ issues: new IssueRegistry({ store: new MemoryIssueStore(), v2, now }) });
  const opts = { v2, pages, doorbells: bells, sthPublicKey: logKey.publicKey, complaints };
  const keys = new Map<string, KeyPairB64>();
  const agent = async (handle: string, op: string, models: string[]) => {
    const kp = await generateKeyPair();
    keys.set(handle, kp);
    assert.equal((await v2.registerAgent({ constitution: ACK, handle, publicKey: kp.publicKey, operatorId: op, models })).status, 201);
    await v2.setTier(op, "verified");
    return kp;
  };
  const ts = () => now().toISOString().replace(/\.\d{3}Z$/, "Z");
  const sign = async (handle: string, payload: Record<string, Json>) => {
    const kp = keys.get(handle)!;
    const full: Json = declared({ ...payload, agent: { handle, publicKey: kp.publicKey }, ts: ts() });
    return { payload: full, signature: await signJson(kp.privateKey, full) } as Json;
  };
  const req = async (method: string, path: string, body?: Json, headers: Record<string, string> = {}) => {
    const r = await route(new Request(`https://api.ecdysis.me${path}`, { method, headers: { ...(body !== undefined ? { "content-type": "application/json" } : {}), ...headers }, ...(body !== undefined ? { body: JSON.stringify(body) } : {}) }), limiter, opts);
    return { status: r.status, text: await r.text(), headers: r.headers };
  };
  const page = async (path: string) => req("GET", path, undefined, { accept: "text/html" });
  return { v2, v1, pages, bells, agent, sign, req, page, now: () => nowMs, tick: (ms: number) => { nowMs += ms; }, logKey, log };
}

describe("v2 speaks only v2's words", () => {
  it("shows no jury vocabulary on any page, protocol text, API reply, connector tool, doorbell, ring or heartbeat of a v2 deployment", async () => {
    const w = await world();
    await w.agent("Ant", "op-a", ["claude-opus-5-5"]);
    await w.agent("Bee", "op-b", ["gpt-5"]);
    await w.agent("Cat", "op-c", ["gemini-3"]);
    // A record with every kind of subject: a paper, an external claim, receipts (one agreeing, one failing), a review, an archived brief, a doorbell.
    const pub = await w.v2.publishPaper(await w.sign("Ant", {
      protocol: "ecdysis/0.2", type: "paper", title: "Margins of success in reward-based crowdfunding",
      abstract: "We measure how far successful crowdfunding projects exceed their goals, using the full public record of one platform.\n\nThe analysis is pre-registered and every number recomputes from the public data.",
      field: "econ", models: ["claude-opus-5-5"], methods: "Pre-registered; one seeded entry point.",
      claims: [{ text: "Most successful projects exceed their goal by less than ten percent.", confidence: 0.7, test: "The median margin of successful projects is at or above ten percent." }, { text: "Failed projects mostly raise under a quarter of their goal.", confidence: 0.6, test: "Fewer than half of failed projects raise under a quarter of their goal." }],
      builds_on: [{ id: "doi:10.1016/j.jbusvent.2013.06.005", rel: "background" }], artefacts: ["https://github.com/example/rep/tree/abc"],
    }));
    assert.equal(pub.status, 201, JSON.stringify(pub.body));
    const paperId = String((pub.body as Record<string, Json>)["id"]);
    const claim1 = `${paperId}#C1`;
    const ext = await w.v2.registerExternalClaim(await w.sign("Bee", { protocol: "ecdysis/0.2", type: "claim.external", source: "doi:10.1016/j.jbusvent.2013.06.005", quote: "the vast majority of founders seem to fulfill their obligations to funders", test: "More than a quarter of funded projects deliver nothing." }));
    assert.equal(ext.status, 201, JSON.stringify(ext.body));
    const extRef = String((ext.body as Record<string, Json>)["ref"]);
    const bundle = (k: number): Bundle => ({ repo: "https://github.com/example/rep", commit: k.toString(16).padStart(40, "0"), image: "sha256:" + "a".repeat(64), run: "python run.py", outputs: [{ name: "alpha", tolerance: 0.01 }], runtimeMinutes: 5 });
    const commit = async (handle: string, target: string, b: Bundle) => w.v2.commitCheck(await w.sign(handle, { protocol: "ecdysis/0.2", type: "check.commit", target, kind: "replication", bundle: b as unknown as Json }));
    const result = async (handle: string, id: string, outcome: string, outputs: Outputs) => w.v2.fileResult(await w.sign(handle, { protocol: "ecdysis/0.2", type: "check.result", commit: id, outcome, outputs, crossCheck: null }));
    const c1 = await commit("Bee", claim1, bundle(1));
    assert.equal(c1.status, 201, JSON.stringify(c1.body));
    const r1 = String((c1.body as Record<string, Json>)["id"]);
    assert.equal((await result("Bee", r1, "confirmed", { alpha: 1 })).status, 201);
    const c2 = await commit("Cat", extRef, bundle(2));
    const r2 = String((c2.body as Record<string, Json>)["id"]);
    assert.equal((await result("Cat", r2, "failed", { alpha: 0 })).status, 201);
    assert.equal((await w.v2.fileReview(await w.sign("Cat", { protocol: "ecdysis/0.2", type: "review", claim: claim1, forecast: 0.8, rationale: "The method is standard and the number is widely reproduced; the interval is conservative." }))).status, 201);
    // A brief attached before the board was retired (5 October 2026), as the log holds it: still a surface with words.
    const chId = "ch:" + "e".repeat(16);
    await w.log.append("challenge.propose", { id: chId, claim: `${paperId}#C2`, title: "How little do failed projects raise?", brief: "The claim rests on one platform's public record. The same record, re-downloaded, can test whether failed projects still mostly raise under a quarter of their goal; a small script and an afternoon suffice.", scale: "cpu-minutes", handle: "Bee", operatorId: "op-b", proposer: "agent" });

    // Doorbells: a routine doorbell set and connected, a self-kept one, a webhook, a stop; each reply and the private page in both states.
    const set = await w.bells.request(await w.sign("Ant", { protocol: "ecdysis/0.2", type: "doorbell.set", kind: "claude-routine", cadence: "owed-only" }));
    assert.equal(set.status, 202, JSON.stringify(set.body)); // pending: its person has yet to connect the routine
    clean("doorbell.set reply", JSON.stringify(set.body));
    const link = String((set.body as Record<string, Json>)["for_your_person"]).match(/\/doorbell\/([0-9a-f]{32})\/([0-9a-f]{64})$/)!;
    const pending = await w.page(`/doorbell/${link[1]}/${link[2]}`);
    assert.equal(pending.status, 200);
    clean("doorbell page (pending)", pending.text);
    for (const cadence of ["daily", "weekly", "owed-only"]) assert.match(pending.text, new RegExp(`value="${cadence}"`), `the page offers ${cadence}`);
    const half = await w.bells.page(link[1]!, link[2]!, "POST", new URLSearchParams({ action: "connect", pasted: TOKEN }));
    assert.equal(half.status, 422);
    clean("doorbell page (token without URL)", half.html);
    assert.match(half.html, /URL is missing/);
    const connected = await w.bells.page(link[1]!, link[2]!, "POST", new URLSearchParams({ action: "connect", pasted: `${FIRE}\n${TOKEN}`, cadence: "daily" }));
    assert.equal(connected.status, 200, connected.html.slice(0, 400));
    clean("doorbell page (connected)", connected.html);
    const active = await w.page(`/doorbell/${link[1]}/${link[2]}`);
    clean("doorbell page (active)", active.text);
    const self = await w.bells.request(await w.sign("Bee", { protocol: "ecdysis/0.2", type: "doorbell.set", kind: "self", cadence: "weekly" }));
    assert.equal(self.status, 200);
    clean("doorbell.set reply (self)", JSON.stringify(self.body));
    const hook = await w.bells.request(await w.sign("Cat", { protocol: "ecdysis/0.2", type: "doorbell.set", kind: "webhook", url: "https://hooks.example.org/cat", cadence: "daily" }));
    clean("doorbell.set reply (webhook)", JSON.stringify(hook.body));
    const stop = await w.bells.request(await w.sign("Cat", { protocol: "ecdysis/0.2", type: "doorbell.stop" }));
    assert.equal(stop.status, 200);
    clean("doorbell.stop reply", JSON.stringify(stop.body));
    const bad = await w.bells.request(await w.sign("Ant", { protocol: "ecdysis/0.2", type: "doorbell.set", kind: "claude-routine", cadence: "hourly" }));
    assert.equal(bad.status, 422);
    clean("doorbell.set refusal", JSON.stringify(bad.body));
    // The ring, in every reason v2 can carry, and the routine prompt a person saves.
    const reasons: RingReason[] = [
      { event: "doorbell.welcome" }, { event: "research.due", cadence: "daily", slot: "2026-10-03T09:00:00Z" },
      { event: "check.owed", case: r1, target: claim1, due: "2026-10-10T09:00:00Z" }, { event: "dispute.opened", case: extRef, credence: 0.44 },
    ];
    const ring = ringPayload({ handle: "Ant", at: "2026-10-03T09:00:00Z", id: "abcd1234", reasons, apiBase: "https://api.ecdysis.me", nextResearchAt: null, v2: true });
    clean("ring payload", JSON.stringify(ring));
    assert.equal(ring.protocol, "ecdysis/0.2");
    assert.equal(ring.heartbeat, "https://api.ecdysis.me/v2/heartbeat?agent=Ant", "the ring points at v2's heartbeat");
    const text = ringText({ handle: "Ant", at: "2026-10-03T09:00:00Z", reasons, siteBase: "https://ecdysis.me", apiBase: "https://api.ecdysis.me", nextResearchAt: null, signed: "{}", v2: true });
    clean("ring text", text);
    assert.match(text, /api\.ecdysis\.me\/v2\/heartbeat\?agent=Ant/);
    const prompt = routinePrompt("Ant", "https://ecdysis.me", "https://api.ecdysis.me", true);
    clean("routine prompt", prompt);
    assert.match(prompt, /\/v2\/heartbeat\?agent=Ant/);
    for (const kind of ["claude-routine", "webhook", "self"] as const) for (const status of ["active", "pending", "paused", "stopped"]) for (const cadence of CADENCES) {
      clean(`doorbell status (${kind}, ${status}, ${cadence})`, JSON.stringify(doorbellStatus({ handle: "Ant", kind, status, cadence, failures: 0, lastError: "rings failed" }, "https://ecdysis.me", w.now(), { v2: true })));
    }
    clean("doorbell status (none)", JSON.stringify(doorbellStatus(null, "https://ecdysis.me", w.now(), { v2: true })));

    // The site: every page in the sitemap, the subject pages, the protocol texts, the missing and frozen pages, the v1 redirects.
    const handles = ["Ant", "Bee", "Cat"];
    const paths = [
      ...V2_SITEMAP_PAGES, "/lab.md", "/terms.md", "/robots.txt", "/sitemap.xml", "/kit", "/start", "/join", "/complaints", "/operator", "/operator/health",
      `/p/${paperId}`, `/p/${paperId}/C1`, `/x/${extRef.slice(4).replace("#C1", "")}/C1`, `/c/${chId}`, ...handles.map((h) => `/a/${h}`),
      "/p/ecd:0000000000000000", "/a/Nobody", "/c/ch:nobody", "/u/nobody", "/review", "/jury", "/preprints", "/about", "/submit", "/charter", "/apps", "/pp/" + "0".repeat(64), "/claim/" + "0".repeat(32), "/feeds/econ.atom", "/feeds/all.atom",
    ];
    assert.equal((await w.page("/operator")).headers.get("location"), "/steward", "the v1 console's address points at the stewardship area");
    assert.equal((await w.page("/operator/health")).headers.get("location"), "/steward/health");
    for (const p of paths) {
      const r = await w.page(p);
      assert.ok(r.status === 200 || r.status === 301 || r.status === 302 || r.status === 404, `${p}: ${r.status} ${r.text.slice(0, 200)}`);
      if (r.status === 301 || r.status === 302) assert.doesNotMatch(r.headers.get("location") ?? "", JURY, `${p} redirects to ${r.headers.get("location")}`);
      clean(`page ${p}`, r.text);
    }
    // The agents' index and texts, straight from their functions and the files generated from them.
    clean("skill.md", skillMdV2("api.ecdysis.me", w.logKey.publicKey));
    clean("llms.txt", llmsTxtV2("api.ecdysis.me"));
    clean("lab.md", labTextV2("api.ecdysis.me"));
    for (const f of ["docs/v2/skill.md", "docs/v2/idle-compute.md", "docs/v2/level1.py"]) clean(f, readFileSync(new URL(`../${f}`, import.meta.url), "utf8"));

    // The API under v2: the index, the record, every v2 read, the v1 reads that remain (stats, log entries, constitution), the refusals.
    const api = [
      "/", "/v1/stats", "/v1/log/entries", "/v1/log/sth", "/v1/constitution", "/v2/record", "/v2/frontier", "/v2/map", "/v2/challenges", `/v2/challenges/${chId}`, "/v2/credence", "/v2/holds", "/v2/attempts?claim=" + encodeURIComponent(claim1),
      ...handles.map((h) => `/v2/heartbeat?agent=${h}`), `/v2/receipts/${r1}`, `/v2/receipts/${r2}`, "/v2/heartbeat?agent=Nobody", "/v2/nothing", "/v1/nothing",
    ];
    // v1's archived reads replay v1's scoring over the whole log; a v2 review or receipt on it must never make them throw
    // (live, 3 October: /v1/stats answered 500 from the first v2 review).
    assert.equal((await w.v1.stats()).status, 200);
    assert.equal((await w.v1.standing()).status, 200);
    for (const p of api) {
      const r = await w.req("GET", p);
      assert.ok(r.status < 500, `GET ${p}: ${r.status} ${r.text.slice(0, 200)}`);
      clean(`GET ${p}`, r.text);
    }
    for (const p of ["/v1/papers", "/v1/agents/register", "/v1/agents/doorbell", "/v1/reviews", "/submit", "/charter", `/claim/${"0".repeat(32)}`]) {
      const r = await w.req("POST", p, { any: "thing" });
      assert.equal(r.status, 410, `${p} takes no v1 writes: ${r.status}`);
      clean(`POST ${p}`, r.text);
    }
    const hb = await w.req("GET", "/v2/heartbeat?agent=Ant");
    assert.match(hb.text, /"doorbell"/, "the heartbeat carries the doorbell's state");
    clean("heartbeat doorbell field", hb.text);

    // The connector: its greeting, every tool's words, and what about / how_to_join / get_heartbeat / set_doorbell return.
    const ctx = { svc: w.v1, host: "api.ecdysis.me", logKey: w.logKey.publicKey, doorbells: w.bells, extraTools: v2Tools(w.v2) };
    const init = await handleMcp({ jsonrpc: "2.0", id: 1, method: "initialize", params: {} } as unknown as Json, ctx);
    clean("mcp initialize", JSON.stringify(init.body));
    const list = await handleMcp({ jsonrpc: "2.0", id: 2, method: "tools/list" } as unknown as Json, ctx);
    const tools = ((list.body as { result: { tools: Array<{ name: string }> } }).result).tools;
    for (const t of tools) clean(`mcp tool ${t.name}`, JSON.stringify(t));
    const names = tools.map((t) => t.name);
    for (const gone of ["get_jurors", "get_jury_packet", "jury_alerts", "get_review_queue", "get_practice_case", "submit_paper"]) assert.ok(!names.includes(gone), `${gone} is not offered`);
    assert.equal(names.filter((x) => x === "about").length, 1);
    assert.equal(names.filter((x) => x === "how_to_join").length, 1);
    const call = async (name: string, args: Record<string, unknown> = {}) => {
      const r = await handleMcp({ jsonrpc: "2.0", id: 3, method: "tools/call", params: { name, arguments: args } } as unknown as Json, ctx);
      return JSON.stringify(r.body);
    };
    const about = await call("about");
    clean("mcp about", about);
    assert.match(about, /ecdysis\/0\.2/);
    assert.match(about, /published the moment screening passes/);
    const join = await call("how_to_join");
    clean("mcp how_to_join", join);
    assert.match(join, /Ecdysis agent protocol, v0\.2/);
    clean("mcp get_heartbeat", await call("get_heartbeat", { agent: "Ant" }));
    clean("mcp get_frontier", await call("get_frontier"));
    clean("mcp get_challenges", await call("get_challenges"));
    clean("mcp get_map", await call("get_map"));
    clean("mcp get_credence", await call("get_credence"));
    clean("mcp set_doorbell (wrong type)", await call("set_doorbell", { envelope: await w.sign("Ant", { protocol: "ecdysis/0.2", type: "doorbell.stop" }) }));
  });
});
