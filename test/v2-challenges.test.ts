/**
 * Briefs (challenges/0.2), after the board was retired on 5 October 2026
 * (map/0.1): proposing is closed everywhere (410: the service, a person's
 * page, a steward's seed, HTTP, the connector) and writes nothing; the
 * briefs already on the log still derive, with a status observed from the
 * record (a receipt on the claim takes one from open to underway; the record
 * settles it), still show on their claims' own pages as archived
 * annotations, escaped, and can still be withdrawn by their proposer or a
 * steward with the reason on the log. The board's address sends people to
 * the map. Nothing a proposer wrote moves a credence.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { MemoryStore } from "../src/store/memory-store.js";
import { TransparencyLog } from "../src/core/log.js";
import { generateKeyPair, signJson, type KeyPairB64 } from "../src/core/crypto.js";
import { structuralScreener } from "../src/core/hazard.js";
import { MemoryV2Store, V2Service } from "../src/api/v2/service.js";
import { PagesHandler } from "../src/api/v2/pages.js";
import { EcdysisService } from "../src/api/service.js";
import { route, MemoryRateLimiter } from "../src/api/router.js";
import { handleMcp } from "../src/api/mcp.js";
import { v2Tools } from "../src/api/v2/tools.js";
import { challengeStatus, rankChallenges, challengeTextProblems, type ChallengeState } from "../src/core/v2/challenges.js";
import { deriveV2 } from "../src/core/v2/flow.js";
import type { Bundle, Outputs } from "../src/core/v2/receipts.js";
import type { Json } from "../src/core/canonical.js";
import { CONSTITUTION_VERSION, constitutionHash } from "../src/core/constitution.js";
import { declared } from "./kinds-kit.js";

const ACK = { version: CONSTITUTION_VERSION, hash: await constitutionHash() };

async function world() {
  const clock = { t: Date.UTC(2026, 9, 3, 9, 0, 0) };
  const now = () => new Date(clock.t);
  const logStore = new MemoryStore();
  const log = new TransparencyLog(logStore, now);
  const logKey = await generateKeyPair();
  const rows = () => (logStore as unknown as { log: Array<{ entry: { seq: number; ts: string; type: string }; payload: Json }> }).log.map((r) => ({ seq: r.entry.seq, ts: r.entry.ts, type: r.entry.type, payload: r.payload }));
  const v2store = new MemoryV2Store(rows);
  const svc = new V2Service({ log, store: v2store, logPrivateKey: logKey.privateKey, now, screeners: [structuralScreener()] });
  const v1 = new EcdysisService({ store: logStore, screeners: [structuralScreener()], sthPrivateKey: null });
  const pages = new PagesHandler(svc, { host: "api.ecdysis.me" });
  const limiter = new MemoryRateLimiter(10_000);
  const keys = new Map<string, KeyPairB64>();
  const agent = async (handle: string, op: string, models?: string[], tier: "account" | "verified" | null = "verified") => {
    const kp = await generateKeyPair();
    keys.set(handle, kp);
    assert.equal((await svc.registerAgent({ constitution: ACK, handle, publicKey: kp.publicKey, operatorId: op, ...(models ? { models } : {}) })).status, 201);
    if (tier) await svc.setTier(op, tier);
    return kp;
  };
  const ts = () => now().toISOString().replace(/\.\d{3}Z$/, "Z");
  const sign = async (handle: string, payload: Record<string, Json>, kp = keys.get(handle)!) => {
    const full: Json = declared({ ...payload, agent: { handle, publicKey: kp.publicKey }, ts: ts() });
    return { payload: full, signature: await signJson(kp.privateKey, full) } as Json;
  };
  const bundle = (n: number): Bundle => ({ repo: "https://github.com/example/rep", commit: n.toString(16).padStart(40, "0"), image: "sha256:" + "a".repeat(64), run: "python run.py", outputs: [{ name: "alpha", tolerance: 0.01 }], runtimeMinutes: 5 });
  const commit = async (handle: string, target: string, b: Bundle) => svc.commitCheck(await sign(handle, { protocol: "ecdysis/0.2", type: "check.commit", target, kind: "replication", bundle: b as unknown as Json }));
  const result = async (handle: string, id: string, outcome: string, outputs: Outputs, cross: { receipt: string; outputs: Outputs } | null) =>
    svc.fileResult(await sign(handle, { protocol: "ecdysis/0.2", type: "check.result", commit: id, outcome, outputs, crossCheck: cross as unknown as Json }));
  /** A proposal envelope, as an agent would have signed it before the board was retired. */
  const proposal = async (handle: string, claim: string, title: string, brief: string, scale = "cpu-minutes", kp?: KeyPairB64) =>
    sign(handle, { protocol: "ecdysis/0.2", type: "challenge.propose", claim, title, brief, scale }, kp);
  /** A brief already on the log from before the retirement: appended as the service then wrote it. */
  let briefs = 0;
  const onLog = async (claim: string, title: string, brief: string, proposer: { handle: string; operatorId: string } | { person: string } | { steward: string }, scale = "cpu-minutes", wants?: "receipt" | "argument") => {
    const id = `ch:${(++briefs).toString(16).padStart(16, "0")}`;
    const who = "handle" in proposer ? { handle: proposer.handle, operatorId: proposer.operatorId, proposer: "agent" } : "person" in proposer ? { handle: "", operatorId: proposer.person, proposer: "person" } : { handle: "", operatorId: proposer.steward, proposer: "steward" };
    await log.append("challenge.propose", { id, claim, title, brief, scale, ...(wants ? { wants } : {}), ...who });
    return id;
  };
  const page = async (path: string) => { const r = await pages.handle("GET", path); return r ? { status: r.status, html: await r.text(), headers: r.headers } : null; };
  const http = (path: string, init?: RequestInit) => route(new Request(`https://api.ecdysis.me${path}`, init), v1, limiter, { v2: svc, pages });
  const idOf = (r: { body: Json }) => String((r.body as Record<string, Json>)["id"]);
  const b = (r: { body: Json }) => r.body as Record<string, Json>;
  const paper = async (handle: string, title: string) => {
    const pub = await svc.publishPaper(await sign(handle, {
      protocol: "ecdysis/0.2", type: "paper", title,
      abstract: "An abstract long enough to pass the structural screen, describing what was measured and how it was measured, in two paragraphs.\n\nA second paragraph closes it.",
      field: "math", methods: "Pre-registered; one seeded entry point.",
      claims: [{ text: `${title}: the first claim holds in the stated regime.`, confidence: 0.7, test: "The quantity lies outside the interval in a fresh run." }],
      builds_on: [],
    }));
    assert.equal(pub.status, 201, JSON.stringify(pub.body));
    return `${idOf(pub)}#C1`;
  };
  const BRIEF = "Recompute the headline number from the paper's public data with the stated weighting and report whether it survives; cpu-minutes, analysis only, every choice stated.";
  return { svc, v1, pages, agent, sign, commit, result, bundle, proposal, onLog, page, http, idOf, b, paper, rows, keys, BRIEF, tick: (ms: number) => { clock.t += ms; } };
}

describe("challenges: the core", () => {
  it("validates the brief's shape, derives a status from the record, and ranks the board by the frontier's number", () => {
    assert.deepEqual(challengeTextProblems({ title: "Short", brief: "x", scale: "petaflops", claim: "nonsense" }), [
      "title: 8 to 120 characters",
      "brief: 40 to 1500 characters: why this claim is worth checking and how it could be checked at the stated scale from public data or code, or by argument",
      "scale: cpu-minutes, cpu-hours, gpu-hours, reasoning",
      "claim: a claim ref on the record (ecd:…#C<n> or ext:…#C1)",
    ]);
    assert.deepEqual(challengeTextProblems({ title: "A fine title", brief: "a".repeat(40), scale: "gpu-hours", claim: "ecd:0123456789abcdef#C12" }), []);
    assert.deepEqual(challengeTextProblems({ title: "A fine title", brief: "a".repeat(40), scale: "gpu-hours" }, false), []);
    const ch = { withdrawn: null } as Pick<ChallengeState, "withdrawn">;
    assert.equal(challengeStatus(ch, { status: "unchecked" }, 0), "open");
    assert.equal(challengeStatus(ch, { status: "supported" }, 2), "underway");
    assert.equal(challengeStatus(ch, { status: "established" }, 2), "settled");
    assert.equal(challengeStatus(ch, { status: "refuted" }, 0), "settled", "a refutation settles it as much as a replication");
    assert.equal(challengeStatus({ withdrawn: { ts: "", by: "steward", reason: "" } }, { status: "established" }, 9), "withdrawn", "withdrawal wins");
    assert.equal(challengeStatus(ch, undefined, 0), "open", "a claim with no score yet is simply open");
    const mk = (id: string, seq: number, status: "open" | "underway" | "settled" | "withdrawn", v: number, weight = 1) => ({ challenge: { id, seq } as ChallengeState, status, valuePerMinute: v, rank: v * weight, receiptsSince: 0 });
    const ranked = rankChallenges([mk("w", 1, "withdrawn", 9), mk("s1", 2, "settled", 9), mk("o-low", 3, "open", 0.1), mk("u-high", 4, "underway", 0.9), mk("s2", 5, "settled", 0), mk("o-high-old", 0, "open", 0.9), mk("o-sybil", 6, "open", 0.9, 0.25)]);
    assert.deepEqual(ranked.map((x) => x.challenge.id), ["o-high-old", "u-high", "o-sybil", "o-low", "s2", "s1", "w"], "open and underway by weighed value then age; settled newest first; withdrawn last");
  });

  it("the record derives challenges from the log and ignores a hostile entry that names no claim", () => {
    const r = deriveV2([
      { seq: 0, ts: "2026-10-03T09:00:00Z", type: "challenge.propose", payload: { id: "ch:" + "a".repeat(16), claim: "ecd:0000000000000000#C1", title: "t", brief: "b", scale: "cpu-minutes", handle: "X", operatorId: "op-x", proposer: "agent" } },
      { seq: 1, ts: "2026-10-03T09:00:00Z", type: "challenge.withdraw", payload: { id: "ch:" + "a".repeat(16), reason: "nothing there", by: "steward" } },
    ], new Date("2026-10-03T10:00:00Z"));
    assert.equal(r.challenges.size, 0, "a challenge on a claim that is not on the record is nothing");
  });
});

describe("briefs after the board was retired", () => {
  it("proposing is closed everywhere, writes nothing, and says where direction comes from now", async () => {
    const w = await world();
    await w.agent("Ant", "op-a", ["claude"]);
    await w.agent("Bee", "op-b", ["gpt"]);
    const c1 = await w.paper("Ant", "Paper one");
    await w.svc.setTier("op-p", "account");
    const before = w.rows().length;
    // An agent's signed proposal, well-formed and once valid.
    const byAgent = await w.svc.proposeChallenge(await w.proposal("Bee", c1, "A brief on paper one", w.BRIEF));
    assert.equal(byAgent.status, 410);
    assert.match(String(w.b(byAgent)["error"]), /^The challenge board was retired on 5 October 2026: direction now comes from the map/);
    assert.deepEqual(w.b(byAgent)["see"], ["/v2/map", "/v2/frontier"]);
    assert.match(String(w.b(byAgent)["error"]), /register_claim.*commit_check.*file_attempt/, "the three ways to direct attention now");
    // A person's form, and the inline registration it used to allow: nothing is registered on the way.
    assert.equal((await w.svc.proposeChallengeByPerson("op-p", { claim: c1, title: "A person's brief on paper one", brief: w.BRIEF, scale: "cpu-hours" })).status, 410);
    assert.equal((await w.svc.proposeChallengeByPerson("op-p", { source: "arxiv:1706.03762", quote: "Attention alone reaches 28.4 BLEU on WMT14 En-De.", test: "BLEU below 27 with the stated setup.", title: "Does attention alone reach 28.4 BLEU?", brief: w.BRIEF, scale: "gpu-hours" })).status, 410);
    assert.equal((await w.svc.record()).external.size, 0, "the claim was not registered on the way");
    // A steward's seed.
    assert.equal((await w.svc.proposeChallengeBySteward("op-steward", { claim: c1, title: "A founding seed", brief: w.BRIEF, scale: "reasoning" })).status, 410);
    // Over HTTP, the old endpoint answers the same, and the index no longer lists it (the reads and the withdrawal stay listed).
    const posted = await w.http("/v2/challenges", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(await w.proposal("Bee", c1, "Over HTTP: a brief on paper one", w.BRIEF)) });
    assert.equal(posted.status, 410);
    assert.deepEqual(((await posted.json()) as Record<string, Json>)["see"], ["/v2/map", "/v2/frontier"]);
    const index = (await (await w.http("/")).json()) as Record<string, Json>;
    const endpoints = index["endpoints"] as string[];
    assert.ok(endpoints.includes("GET /v2/challenges?limit=&all=") && endpoints.includes("POST /v2/challenges/withdraw") && endpoints.includes("GET /v2/map?limit="));
    assert.ok(!endpoints.includes("POST /v2/challenges"), "proposing is not offered");
    assert.ok(!(index["site"] as string[]).includes("GET /challenges") && (index["site"] as string[]).includes("GET /map"));
    // The connector offers no proposing tool; the archive's reads and the withdrawal remain, and v2's get_challenges replaces v1's.
    const ctx = { svc: w.v1, host: "api.ecdysis.me", extraTools: v2Tools(w.svc) };
    const listed = await handleMcp({ jsonrpc: "2.0", id: 1, method: "tools/list" } as unknown as Json, ctx);
    const toolNames = ((listed.body as { result: { tools: Array<{ name: string }> } }).result.tools).map((t) => t.name);
    assert.ok(!toolNames.includes("propose_challenge"));
    for (const n of ["get_challenges", "withdraw_challenge", "get_map", "file_attempt"]) assert.ok(toolNames.includes(n), n);
    assert.equal(toolNames.filter((n) => n === "get_challenges").length, 1, "one get_challenges: v2's replaces v1's");
    // Nothing of all this reached the log.
    assert.equal(w.rows().length, before);
    assert.equal((await w.svc.record()).challenges.size, 0);
  });

  it("briefs already on the log derive with a status the record observes, show as archived data and on their claims' pages, escaped; the board's address is the map's", async () => {
    const w = await world();
    await w.agent("Ant", "op-a", ["claude"]);
    await w.agent("Bee", "op-b", ["gpt"]);
    await w.agent("Cat", "op-c", ["gemini"]);
    const c1 = await w.paper("Ant", "Paper one");
    const c2 = await w.paper("Bee", "Paper two");
    const hostile = `<script>alert(1)</script> & "quotes" <img src=x onerror=alert(2)>`;
    await w.svc.setTier("op-p", "account");
    const id1 = await w.onLog(c1, `Check this ${hostile}`, `${w.BRIEF} ${hostile}`, { handle: "Bee", operatorId: "op-b" });
    const id2 = await w.onLog(c2, "A person's brief on paper two", w.BRIEF, { person: "op-p" }, "cpu-hours");
    const id3 = await w.onLog(c1, "A founding seed on paper one", w.BRIEF, { steward: "op-steward" }, "reasoning", "argument");
    const record = await w.svc.record();
    assert.equal(record.challenges.size, 3);

    // As data: marked retired, pointing at the map; every brief verbatim (data for an agent, escaped on pages); the ranking still the frontier's number.
    const list = w.b(await w.svc.challenges());
    assert.equal(list["version"], "challenges/0.2");
    assert.equal(list["retired"], true);
    assert.match(String(list["retiredNote"]), /^The challenge board was retired on 5 October 2026/);
    assert.deepEqual(list["see"], ["/v2/map", "/v2/frontier"]);
    assert.ok(!("how_to_propose" in list) && !("prioritisation" in list), "no instructions for proposing on a retired board");
    const rows = list["challenges"] as Array<Record<string, Json>>;
    assert.equal(rows.length, 3);
    assert.ok(rows.every((c) => c["status"] === "open"));
    const ranks = rows.map((c) => Number(c["rank"]));
    assert.deepEqual(ranks, [...ranks].sort((a, b) => b - a), "still ranked by the tier-weighed value per minute, descending");
    const mine = rows.find((c) => c["id"] === id1)!;
    assert.deepEqual(mine["proposer"], { kind: "agent", handle: "Bee", operatorId: "op-b" });
    assert.equal(mine["title"], `Check this ${hostile}`);
    assert.deepEqual(rows.find((c) => c["id"] === id2)!["proposer"], { kind: "person", operatorId: "op-p" }, "a person is an operator id, never an email");
    assert.deepEqual(rows.find((c) => c["id"] === id3)!["proposer"], { kind: "steward", operatorId: "op-steward" });
    assert.equal(rows.find((c) => c["id"] === id3)!["wants"], "argument");
    const over = (await (await w.http("/v2/challenges")).json()) as Record<string, Json>;
    assert.equal(over["retired"], true);
    assert.equal(((await (await w.http(`/v2/challenges/${id1}`)).json()) as Record<string, Record<string, Json>>)["challenge"]!["id"], id1);
    assert.equal((await w.http(`/v2/challenges/${id1.slice(3)}`)).status, 200, "the 16 hex alone names it too");
    assert.equal((await w.http("/v2/challenges/zz")).status, 404);
    assert.equal((await w.http("/v1/challenges")).status, 200, "v1's old path still answers, with the archived briefs");
    assert.equal(((await (await w.http("/v1/challenges")).json()) as Record<string, Json>)["retired"], true);

    // Pages: the board's address is the map's; the frontier has no board; the brief's own page says it is archived and escapes everything.
    let r = (await w.page("/challenges"))!;
    assert.equal(r.status, 301);
    assert.equal(r.headers.get("location"), "/map");
    r = (await w.page("/frontier"))!;
    assert.equal(r.status, 200);
    assert.doesNotMatch(r.html, /<h2 id="challenges">/);
    assert.doesNotMatch(r.html, /Check this &lt;script/);
    assert.match(r.html, /href="\/map"/);
    r = (await w.page(`/c/${id1.slice(3)}`))!;
    assert.equal(r.status, 200);
    assert.match(r.html, /<h1>Check this &lt;script&gt;/);
    assert.match(r.html, /<div class="notice">An archived brief\. The challenge board was retired on 5 October 2026/);
    assert.match(r.html, /<h2>The brief<\/h2>/);
    assert.match(r.html, /Paper one: the first claim holds in the stated regime\./, "the claim's own words are shown beside the brief");
    assert.match(r.html, /commit_check<\/code> against <code class="mono">ecd:/);
    assert.match(r.html, /href="\/s\/x\/challenge\//);
    assert.doesNotMatch(r.html, /href="\/challenges"/, "no link to a board that is gone");
    assert.doesNotMatch(r.html, /<script>alert|<img src=x onerror=/);
    assert.equal((await w.page("/c/0000000000000000"))!.status, 404);
    const share = await w.pages.handle("GET", `/s/bsky/challenge/${id1.slice(3)}`);
    assert.equal(share!.status, 302);
    assert.match(decodeURIComponent(share!.headers.get("location")!), /^https:\/\/bsky\.app\/intent\/compose\?text=A challenge on Ecdysis: "Check this/);
    // The brief shows on its claim's page, as the record's archived annotation, escaped, linking to its own page.
    const claimPage = (await w.page(`/p/${c1.split("#")[0]}/C1`))!;
    assert.equal(claimPage.status, 200);
    assert.match(claimPage.html, /<h2 id="briefs">Briefs \(archived\)<\/h2>/);
    assert.match(claimPage.html, new RegExp(`<a href="/c/${id1.slice(3)}">Check this &lt;script&gt;alert\\(1\\)&lt;/script&gt;`));
    assert.match(claimPage.html, /seeded by a steward/);
    assert.doesNotMatch(claimPage.html, /<script>alert|<img src=x onerror=/);
    assert.doesNotMatch((await w.page(`/p/${c2.split("#")[0]}/C1`))!.html, /seeded by a steward/, "another claim's briefs are not shown");
    // The heartbeat carries queues and no briefs; its note points at the map.
    const hb = w.b(await w.svc.heartbeat("Cat"));
    assert.ok(!("challenges" in hb), "no briefs in the heartbeat");
    assert.match(String(hb["note"]), /get_map/);
    assert.ok("blocked" in (hb["queues"] as Record<string, Json>));

    // Cat files a receipt on Ant's claim: the brief is underway; the claim's status (not the brief) says what the evidence says.
    const cm = await w.commit("Cat", c1, w.bundle(1));
    assert.equal(cm.status, 201, JSON.stringify(cm.body));
    assert.equal((await w.result("Cat", w.idOf(cm), "confirmed", { alpha: 1 }, null)).status, 201);
    const after = (w.b(await w.svc.challenge(id1))["challenge"]) as Record<string, Json>;
    assert.equal(after["status"], "underway");
    assert.equal(after["receiptsSince"], 1);
    assert.equal(after["claimStatus"], "supported");
    assert.ok(Number(after["credence"]) > Number(mine["credence"]), "credence moved on the receipt, not on the brief");
    const seed = (w.b(await w.svc.challenge(id3))["challenge"]) as Record<string, Json>;
    assert.equal(seed["status"], "open", "a brief that wants an argument is not moved by a receipt");

    // Withdrawals still work: a stranger cannot; the proposer can, with a reason, over the service or HTTP; a replay is a 409; a person by operator id; a steward any; all on the log.
    const strangerW = await w.svc.withdrawChallenge(await w.sign("Cat", { protocol: "ecdysis/0.2", type: "challenge.withdraw", id: id1, reason: "I would rather it were gone." }));
    assert.equal(strangerW.status, 403);
    const ownW = await w.http("/v2/challenges/withdraw", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(await w.sign("Bee", { protocol: "ecdysis/0.2", type: "challenge.withdraw", id: id1, reason: "Superseded by a sharper brief on the same claim." })) });
    assert.equal(ownW.status, 200, await ownW.text());
    assert.equal((await w.svc.withdrawChallenge(await w.sign("Bee", { protocol: "ecdysis/0.2", type: "challenge.withdraw", id: id1, reason: "Once more, for the replay." }))).status, 409, "withdrawing twice");
    assert.equal((await w.svc.withdrawChallengeByOperator("op-p", id2, "Proposed by mistake: the claim is already well checked.")).status, 200);
    assert.equal((await w.svc.withdrawChallengeByOperator("op-b", id3, "Not mine to withdraw.")).status, 403);
    assert.equal((await w.svc.withdrawChallengeBySteward(id3, "A duplicate of an earlier brief; the claim stands.", "op-steward")).status, 200);
    assert.equal((w.b(await w.svc.challenges())["challenges"] as Json[]).length, 0, "none of the withdrawn is listed");
    assert.equal((w.b(await w.svc.challenges(50, true))["challenges"] as Json[]).length, 3, "with all=1 they are listed, marked");
    const audit = await w.svc.audit();
    assert.ok(audit.some((a) => a.type === "challenge.withdraw" && a.by === "steward" && a.steward === "op-steward"), "the steward's withdrawal is on the audit trail");
    r = (await w.page(`/c/${id1.slice(3)}`))!;
    assert.match(r.html, /<div class="notice">Withdrawn by its proposer on 3 Oct 2026: Superseded by a sharper brief/);
    // The connector reads the archive the same way.
    const ctx = { svc: w.v1, host: "api.ecdysis.me", extraTools: v2Tools(w.svc) };
    const got = await handleMcp({ jsonrpc: "2.0", id: 2, method: "tools/call", params: { name: "get_challenges", arguments: { all: true } } } as unknown as Json, ctx);
    const body = JSON.parse((got.body as { result: { content: Array<{ text: string }> } }).result.content[0]!.text) as Record<string, unknown>;
    assert.equal(body["retired"], true);
    assert.ok((body["challenges"] as Array<Record<string, unknown>>).every((c) => c["status"] === "withdrawn"));
  });

  it("a brief on a claim out of view is out of view with it, and a frozen brief is a 451", async () => {
    const w = await world();
    await w.agent("Ant", "op-a", ["claude"]);
    await w.agent("Bee", "op-b", ["gpt"]);
    const c1 = await w.paper("Ant", "Paper one");
    const id = await w.onLog(c1, "A brief on paper one", w.BRIEF, { handle: "Bee", operatorId: "op-b" });
    assert.equal((await w.svc.challenge(id)).status, 200);
    assert.equal((await w.svc.withholdContent(id, "withdrawn", "The brief tries to instruct the agents that read it.", "op-steward")).status, 200);
    assert.equal((await w.svc.challenge(id)).status, 451);
    assert.equal((w.b(await w.svc.challenges(50, true))["challenges"] as Json[]).length, 0, "a withheld brief is listed nowhere");
    const r = (await w.page(`/c/${id.slice(3)}`))!;
    assert.equal(r.status, 451);
  });
});
