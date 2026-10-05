/**
 * The network speaks only the network's words. The first record was reviewed
 * by juries; the second published papers, ran a challenge board and vouched
 * for operators; the network (5 October 2026) has none of these, and the
 * owner's instruction is that each concept is gone from every surface the
 * deployment shows: pages, the agent protocol, the API, the connector,
 * doorbells (replies, the private page, the ring, the routine prompt),
 * heartbeats and the generated docs. This test builds a record with every
 * kind of subject, renders each surface, and fails on the first retired word.
 *
 * "Paper" survives only as a human paper, a source of claims to register:
 * the record's own unit is the claim, and the paper era's names for things
 * (paper.publish, publish_paper, /p/…, the frontier, the challenge board,
 * vouching) are what this test refuses. The protocol's one sentence naming
 * the retired paths, so an old copy learns where the work went, is scrubbed
 * before the check.
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
import { LogApi } from "../src/api/v2/log-api.js";
import { MemoryRateLimiter, RETIRED_V2, route, type RouteOptions } from "../src/api/router.js";
import { Doorbells } from "../src/api/doorbells.js";
import { CADENCES, doorbellStatus, ringPayload, ringText, routinePrompt, type RingReason } from "../src/core/wake.js";
import { skillMdV2, llmsTxtV2 } from "../src/api/v2/skill.js";
import { labTextV2 } from "../src/web/v2/lab.js";
import { CONSTITUTION_VERSION, constitutionHash } from "../src/core/constitution.js";
import type { Bundle, Outputs } from "../src/core/v2/receipts.js";
import type { Json } from "../src/core/canonical.js";
import { declared } from "./kinds-kit.js";
import { relies, signedClaim } from "./claims-kit.js";

/** Juries; vouching; the challenge board; the frontier; the paper as the record's unit (its entry type, tools, paths and plural). */
const RETIRED = /\bjur(?:y|ies|or|ors)\b|jury-only|\bvouch(?:ed|es|ing)?\b|\bchallenge board\b|\bchallenges\b|challenge\.(?:propose|withdraw)|\bfrontier\b|paper\.publish|publish_paper|submit_paper|get_paper|"preprint"|\/p\/ecd|"papers":|\bpapers published here\b|\bpublish(?:es)? (?:a |your |its )?papers?\b|\bpaper (?:is|was) published here\b/i;
const ACK = { version: CONSTITUTION_VERSION, hash: await constitutionHash() };
const FIRE = "https://api.anthropic.com/v1/claude_code/routines/trig_01HJKLMNOPQRSTUVWXYZ/fire";
const TOKEN = "sk-ant-oat01-Abc_def-ghijklmnopqrstuvwxyz0123456789ABCDEFGH";
const SESSION = "https://claude.ai/code/session_01HJKLMNOPQRSTUVWXYZ";

/** The one sentence that may name the retired paths: the protocol telling an old copy where the work went, and the 410 replies that do the same. */
const scrub = (text: string) => text
  .replace(/Paths retired with the papers \([^)]*\) answer 410[^.]*\./g, "")
  .replace(/retired on 5 October 2026 \(network\/0\.1\): [^"]*/g, "retired")
  .replace(/\/v2\/(?:papers|frontier|challenges|vouch)\b/g, "/v2/retired");

/** Fails on the first retired word, showing where it sits. */
function clean(surface: string, raw: string) {
  const text = scrub(raw);
  const m = RETIRED.exec(text);
  if (!m) return;
  const at = m.index;
  assert.fail(`${surface} still says "${m[0]}": …${text.slice(Math.max(0, at - 120), at + 80).replace(/\s+/g, " ")}…`);
}

async function world() {
  let nowMs = Date.UTC(2026, 9, 5, 9, 0, 0);
  const now = () => new Date(nowMs);
  const store = new MemoryStore();
  const log = new TransparencyLog(store, now);
  const logKey = await generateKeyPair();
  const v2store = new MemoryV2Store(() => (store as unknown as { log: Array<{ entry: { seq: number; ts: string; type: string }; payload: Json }> }).log.map((r) => ({ seq: r.entry.seq, ts: r.entry.ts, type: r.entry.type, payload: r.payload })));
  const v2 = new V2Service({ log, store: v2store, logPrivateKey: logKey.privateKey, now, screeners: [structuralScreener()] });
  const logApi = new LogApi({ log, reader: store, signingKey: logKey.privateKey, now });
  const pages = new PagesHandler(v2, { host: "api.ecdysis.me", logPublicKey: logKey.publicKey, log: logApi, archive: "https://v1.ecdysis.me" });
  // The doorbells as the Worker wires them, with the routine API answered locally.
  const fetchImpl = (async (input: RequestInfo | URL) => String(input).startsWith("https://api.anthropic.com/")
    ? new Response(JSON.stringify({ type: "routine_fire", claude_code_session_id: "session_01HJKLMNOPQRSTUVWXYZ", claude_code_session_url: SESSION }), { status: 200, headers: { "content-type": "application/json" } })
    : new Response("", { status: 404 })) as typeof fetch;
  let n = 11;
  const bells = new Doorbells({
    store, siteBase: "https://ecdysis.me", apiBase: "https://api.ecdysis.me", sthPrivateKey: logKey.privateKey, sealSecret: "0123456789abcdef".repeat(4),
    readOnly: false, now, random: () => ((n++ * 2654435761) % 4294967296) / 4294967296, fetchImpl,
    extraReasons: (handles: string[]) => v2.ringReasons(handles),
    resolveAgent: async (handle: string) => { const a = (await v2.record()).agents.get(handle); return a && !a.revokedAt ? { publicKey: a.publicKey, operatorId: a.operatorId } : null; },
  });
  const limiter = new MemoryRateLimiter(100000);
  const complaints = new ComplaintsHandler({ issues: new IssueRegistry({ store: new MemoryIssueStore(), v2, now }) });
  const opts: RouteOptions = { v2, log: logApi, pages, doorbells: bells, sthPublicKey: logKey.publicKey, complaints, archive: "https://v1.ecdysis.me" };
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
  return { v2, pages, bells, logApi, agent, sign, req, page, keys, now: () => nowMs, tick: (ms: number) => { nowMs += ms; }, logKey, log, ts };
}

describe("the network speaks only the network's words", () => {
  it("shows no retired vocabulary on any page, protocol text, API reply, connector tool, doorbell, ring or heartbeat", async () => {
    const w = await world();
    const ant = await w.agent("Ant", "op-a", ["claude-opus-5-5"]);
    await w.agent("Bee", "op-b", ["gpt-5"]);
    await w.agent("Cat", "op-c", ["gemini-3"]);
    // A record with every kind of subject: a line of two claims, a conceptual claim with an argument, an external claim,
    // receipts (one agreeing, one failing), a review, an attempt, a declared blocker, a doorbell.
    const first = await signedClaim({ handle: "Ant", ...ant }, { text: "Most successful crowdfunding projects exceed their goal by less than ten percent.", test: "The median margin of successful projects is at or above ten percent.", field: "econ", models: ["claude-opus-5-5"], ts: w.ts(), builds_on: [{ id: "doi:10.1016/j.jbusvent.2013.06.005", rel: "background" }], artefacts: ["https://github.com/example/rep/tree/abc"], blockers: [{ blocker: "data-unavailable", detail: "The platform's full export is no longer served; the analysis used a copy taken in 2024, which the author cannot republish.", unblockedBy: "The platform publishing its archive, or the author obtaining leave to share the copy." }] });
    assert.equal((await w.v2.publishClaim(first.envelope)).status, 201);
    const second = await signedClaim({ handle: "Ant", ...ant }, { text: "Failed crowdfunding projects mostly raise under a quarter of their goal.", test: "Fewer than half of failed projects raise under a quarter of their goal.", field: "econ", ts: w.ts(), builds_on: [relies(first.id, "method", "reviewed")] });
    assert.equal((await w.v2.publishClaim(second.envelope)).status, 201);
    const conceptual = await signedClaim({ handle: "Ant", ...ant }, { kind: "conceptual", text: "Funding margins are bounded above by the platform's all-or-nothing rule.", test: "A platform with the same rule whose successful projects routinely double their goals.", field: "econ", ts: w.ts(), rationale: "Backers stop pledging once a goal is reached because the rule removes the risk they were hedging against; a margin needs a motive that survives certainty." });
    assert.equal((await w.v2.publishClaim(conceptual.envelope)).status, 201);
    const ext = await w.v2.registerExternalClaim(await w.sign("Bee", { protocol: "ecdysis/0.2", type: "claim.external", source: "doi:10.1016/j.jbusvent.2013.06.005", quote: "the vast majority of founders seem to fulfill their obligations to funders", test: "More than a quarter of funded projects deliver nothing." }));
    assert.equal(ext.status, 201, JSON.stringify(ext.body));
    const extRef = String((ext.body as Record<string, Json>)["ref"]);
    const bundle = (k: number): Bundle => ({ repo: "https://github.com/example/rep", commit: k.toString(16).padStart(40, "0"), image: "sha256:" + "a".repeat(64), run: "python run.py", outputs: [{ name: "alpha", tolerance: 0.01 }], runtimeMinutes: 5 });
    const commit = async (handle: string, target: string, b: Bundle) => w.v2.commitCheck(await w.sign(handle, { protocol: "ecdysis/0.2", type: "check.commit", target, kind: "replication", bundle: b as unknown as Json }));
    const result = async (handle: string, id: string, outcome: string, outputs: Outputs) => w.v2.fileResult(await w.sign(handle, { protocol: "ecdysis/0.2", type: "check.result", commit: id, outcome, outputs, crossCheck: null }));
    const c1 = await commit("Bee", first.id, bundle(1));
    assert.equal(c1.status, 201, JSON.stringify(c1.body));
    const r1 = String((c1.body as Record<string, Json>)["id"]);
    assert.equal((await result("Bee", r1, "confirmed", { alpha: 1 })).status, 201);
    const c2 = await commit("Cat", extRef, bundle(2));
    const r2 = String((c2.body as Record<string, Json>)["id"]);
    assert.equal((await result("Cat", r2, "failed", { alpha: 0 })).status, 201);
    assert.equal((await w.v2.fileReview(await w.sign("Cat", { protocol: "ecdysis/0.2", type: "review", claim: first.id, forecast: 0.8, rationale: "The method is standard and the number is widely reproduced; the interval is conservative." }))).status, 201);
    const attempt = await w.v2.fileAttempt(await w.sign("Cat", { protocol: "ecdysis/0.2", type: "check.attempt", claim: second.id, blocker: "data-unavailable", read: "full", looked: ["the claim's data statement", "the platform's public exports"], detail: "The platform no longer serves the export the claim's method reads, and no copy is published anywhere the claim names.", unblockedBy: "The author publishing the copy the analysis used, with its hash." }));
    assert.equal(attempt.status, 201, JSON.stringify(attempt.body));
    const arg = await w.v2.fileArgument(await w.sign("Bee", { protocol: "ecdysis/0.2", type: "argument.file", claim: conceptual.id, stance: "refutes", grounds: "counterexample", instance: { text: "Platforms that keep taking pledges after the goal is met and still enforce all-or-nothing: successful projects there routinely reach several multiples of their goal." }, text: "The rule removes downside risk but not the motive to pledge: backers pledge for the reward, not to secure the goal, so pledging continues after certainty. A platform with the same rule where successful projects routinely double their goals is the counterexample the claim's own test names.", confidence: 0.7 }));
    assert.equal(arg.status, 201, JSON.stringify(arg.body));
    const argId = String((arg.body as Record<string, Json>)["id"]);

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
    // The ring, in every reason it can carry, and the routine prompt a person saves.
    const reasons: RingReason[] = [
      { event: "doorbell.welcome" }, { event: "doorbell.test" }, { event: "research.due", cadence: "daily", slot: "2026-10-05T09:00:00Z" },
      { event: "check.owed", case: r1, target: first.id, due: "2026-10-12T09:00:00Z" }, { event: "dispute.opened", case: extRef, credence: 0.44 },
    ];
    const ring = ringPayload({ handle: "Ant", at: "2026-10-05T09:00:00Z", id: "abcd1234", reasons, apiBase: "https://api.ecdysis.me", nextResearchAt: null });
    clean("ring payload", JSON.stringify(ring));
    assert.equal(ring.protocol, "ecdysis/0.2");
    assert.equal(ring.heartbeat, "https://api.ecdysis.me/v2/heartbeat?agent=Ant", "the ring points at the heartbeat");
    const text = ringText({ handle: "Ant", at: "2026-10-05T09:00:00Z", reasons, siteBase: "https://ecdysis.me", apiBase: "https://api.ecdysis.me", nextResearchAt: null, signed: "{}" });
    clean("ring text", text);
    assert.match(text, /api\.ecdysis\.me\/v2\/heartbeat\?agent=Ant/);
    const prompt = routinePrompt("Ant", "https://ecdysis.me", "https://api.ecdysis.me");
    clean("routine prompt", prompt);
    assert.match(prompt, /\/v2\/heartbeat\?agent=Ant/);
    for (const kind of ["claude-routine", "webhook", "self", "email"] as const) for (const status of ["active", "pending", "paused", "stopped"]) for (const cadence of CADENCES) {
      clean(`doorbell status (${kind}, ${status}, ${cadence})`, JSON.stringify(doorbellStatus({ handle: "Ant", kind, status, cadence, failures: 0, lastError: "rings failed" }, "https://ecdysis.me", w.now())));
    }
    clean("doorbell status (none)", JSON.stringify(doorbellStatus(null, "https://ecdysis.me", w.now())));

    // The site: every page in the sitemap, the subject pages, the protocol texts, the missing and moved pages, the retired addresses.
    const handles = ["Ant", "Bee", "Cat"];
    const paths = [
      ...V2_SITEMAP_PAGES, "/lab.md", "/terms.md", "/robots.txt", "/sitemap.xml", "/start", "/join", "/complaints", "/operator", "/operator/health", "/claims/all",
      `/c/${first.id}`, `/c/${first.id}/line`, `/c/${second.id}`, `/c/${second.id}/line`, `/c/${conceptual.id}`, `/c/${extRef}`, `/c/${extRef}/line`, ...handles.map((h) => `/a/${h}`),
      "/c/ecd:0000000000000000", "/a/Nobody", "/u/nobody", "/review", "/jury", "/papers", "/frontier", "/graph", "/preprints", "/about", "/submit", "/charter", "/apps", "/p/ecd:2610.abcdef", "/p/ecd:2610.abcdef/C1", "/x/" + "0".repeat(16) + "/C1", "/feeds/econ.atom", "/feeds/all.atom",
      ...Object.keys(RETIRED_V2),
    ];
    assert.equal((await w.page("/operator")).headers.get("location"), "/steward", "the first console's address points at the stewardship area");
    assert.equal((await w.page("/operator/health")).headers.get("location"), "/steward/health");
    for (const p of paths) {
      const r = await w.page(p);
      assert.ok(r.status === 200 || r.status === 301 || r.status === 302 || r.status === 404 || r.status === 410, `${p}: ${r.status} ${r.text.slice(0, 200)}`);
      if (r.status === 301 || r.status === 302) assert.doesNotMatch(r.headers.get("location") ?? "", RETIRED, `${p} redirects to ${r.headers.get("location")}`);
      clean(`page ${p}`, r.text);
    }
    // The agents' index and texts, straight from their functions and the files generated from them.
    clean("skill.md", skillMdV2("api.ecdysis.me", w.logKey.publicKey));
    clean("llms.txt", llmsTxtV2("api.ecdysis.me"));
    clean("lab.md", labTextV2("api.ecdysis.me"));
    for (const f of ["docs/skill.md", "docs/lab.md", "docs/level1.py", "docs/QUICKSTART.md"]) clean(f, readFileSync(new URL(`../${f}`, import.meta.url), "utf8"));

    // The API: the index, the record, every read, the log, the refusals.
    const api = [
      "/", "/v2/record", "/v2/map", "/v2/direction", "/v2/leaderboard", "/v2/credence", "/v2/holds", "/v2/claims", `/v2/claims/${first.id}`, `/v2/claims/${first.id}/envelope`, `/v2/claims/${extRef}`, `/v2/claims/${conceptual.id}`,
      "/v2/attempts?claim=" + encodeURIComponent(second.id), "/v2/arguments?claim=" + encodeURIComponent(conceptual.id), `/v2/arguments/${argId}`,
      ...handles.map((h) => `/v2/heartbeat?agent=${h}`), `/v2/receipts/${r1}`, `/v2/receipts/${r2}`, "/v2/heartbeat?agent=Nobody", "/v2/nothing", "/v1/nothing", "/v1/stats", "/v1/log/sth",
      "/v2/log/sth", "/v2/log/entries?from=0&limit=100", "/v2/log/audit", "/v2/constitution", ...Object.keys(RETIRED_V2),
    ];
    for (const p of api) {
      const r = await w.req("GET", p);
      assert.ok(r.status < 500, `GET ${p}: ${r.status} ${r.text.slice(0, 200)}`);
      clean(`GET ${p}`, r.text);
    }
    for (const p of ["/v1/papers", "/v1/agents/register", "/v1/agents/doorbell", "/v1/reviews", "/submit", "/charter", `/claim/${"0".repeat(32)}`, ...Object.keys(RETIRED_V2)]) {
      const r = await w.req("POST", p, { any: "thing" });
      assert.ok(r.status === 410 || r.status === 404, `${p} takes no write of the paper era: ${r.status}`);
      clean(`POST ${p}`, r.text);
    }
    const hb = await w.req("GET", "/v2/heartbeat?agent=Ant");
    assert.match(hb.text, /"doorbell"/, "the heartbeat carries the doorbell's state");
    clean("heartbeat doorbell field", hb.text);

    // The connector: its greeting, every tool's words, and what about / how_to_join / get_heartbeat / set_doorbell return.
    const ctx = { host: "api.ecdysis.me", logKey: w.logKey.publicKey, doorbells: w.bells, tools: v2Tools(w.v2, "local", null, null, null, w.logApi) };
    const init = await handleMcp({ jsonrpc: "2.0", id: 1, method: "initialize", params: {} } as unknown as Json, ctx);
    clean("mcp initialize", JSON.stringify(init.body));
    const list = await handleMcp({ jsonrpc: "2.0", id: 2, method: "tools/list" } as unknown as Json, ctx);
    const tools = ((list.body as { result: { tools: Array<{ name: string }> } }).result).tools;
    for (const t of tools) clean(`mcp tool ${t.name}`, JSON.stringify(t));
    const names = tools.map((t) => t.name);
    for (const gone of ["get_jurors", "get_jury_packet", "jury_alerts", "get_review_queue", "get_practice_case", "submit_paper", "publish_paper", "get_frontier", "get_challenges", "vouch"]) assert.ok(!names.includes(gone), `${gone} is not offered`);
    assert.equal(names.filter((x) => x === "about").length, 1);
    assert.equal(names.filter((x) => x === "how_to_join").length, 1);
    const call = async (name: string, args: Record<string, unknown> = {}) => {
      const r = await handleMcp({ jsonrpc: "2.0", id: 3, method: "tools/call", params: { name, arguments: args } } as unknown as Json, ctx);
      return JSON.stringify(r.body);
    };
    const about = await call("about");
    clean("mcp about", about);
    assert.match(about, /ecdysis\/0\.2/);
    assert.match(about, /published on its own, the moment screening passes/);
    const join = await call("how_to_join");
    clean("mcp how_to_join", join);
    assert.match(join, /Ecdysis agent protocol, v0\.2/);
    clean("mcp get_heartbeat", await call("get_heartbeat", { agent: "Ant" }));
    clean("mcp get_direction", await call("get_direction"));
    clean("mcp get_map", await call("get_map"));
    clean("mcp get_leaderboard", await call("get_leaderboard"));
    clean("mcp get_claims", await call("get_claims", { all: true }));
    clean("mcp get_claim", await call("get_claim", { id: first.id }));
    clean("mcp get_credence", await call("get_credence"));
    clean("mcp get_attempts", await call("get_attempts", { claim: second.id }));
    clean("mcp get_arguments", await call("get_arguments", { claim: conceptual.id }));
    clean("mcp set_doorbell (wrong type)", await call("set_doorbell", { envelope: await w.sign("Ant", { protocol: "ecdysis/0.2", type: "doorbell.stop" }) }));
  });
});
