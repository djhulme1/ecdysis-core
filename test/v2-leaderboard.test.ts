/**
 * The leaderboard (leaderboard/0.1): credence banked on claims that resolved without the reporter's operator, credence at
 * risk, operators' totals with the net-negative mark, and the audit list that aims checks at the work carrying the most
 * credence. Adversarial: volume buys no rank, a misvalidation shows as a loss, splitting work across agents changes no
 * operator's total, an operator's own work never comes back to it as an audit, and hostile operator ids are escaped.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { MemoryStore } from "../src/store/memory-store.js";
import { TransparencyLog } from "../src/core/log.js";
import { generateKeyPair, signJson, type KeyPairB64 } from "../src/core/crypto.js";
import { structuralScreener } from "../src/core/hazard.js";
import { MemoryV2Store, V2Service } from "../src/api/v2/service.js";
import { EcdysisService } from "../src/api/service.js";
import { route, MemoryRateLimiter } from "../src/api/router.js";
import { PagesHandler, V2_SITEMAP_PAGES } from "../src/api/v2/pages.js";
import { handleMcp } from "../src/api/mcp.js";
import { v2Tools } from "../src/api/v2/tools.js";
import { auditList, buildLeaderboard, contributionsOf, leaderboardInputOf, LEADERBOARD_VERSION } from "../src/core/v2/leaderboard.js";
import { leaderboardPageV2 } from "../src/web/v2/leaderboard.js";
import { resolveV2 } from "../src/core/v2/resolve.js";
import type { ScoredReport } from "../src/core/v2/scoring.js";
import { scriptedLog } from "../scripts/v2-replay-audit.js";
import type { Bundle } from "../src/core/v2/receipts.js";
import type { Json } from "../src/core/canonical.js";
import { CONSTITUTION_VERSION, constitutionHash } from "../src/core/constitution.js";
import { declared } from "./kinds-kit.js";

const ACK = { version: CONSTITUTION_VERSION, hash: await constitutionHash() };
const body = (r: { body: Json }) => r.body as Record<string, Json>;
const near = (a: number, b: number) => Math.abs(a - b) < 1e-9;

/** A scored report as scoring.ts writes one: the move, and where its claim resolved without the reporter's operator. */
function rep(agent: string, claim: string, before: number, after: number, resolved: 0 | 1 | null, over: Partial<ScoredReport> = {}): ScoredReport {
  return { id: `${agent}-${claim}-${before}-${after}`, agent, claim, seq: 1, before, after, resolved, credit: 0, operatorId: `op-${agent.toLowerCase()}`, kind: "replication", ...over };
}
const agentsOf = (...handles: string[]) => new Map(handles.map((h) => [h, `op-${h.toLowerCase()}`] as const));

describe("leaderboard/0.1, the core", () => {
  it("banks the move towards where the claim resolved, and a move the other way as a loss; unresolved moves are at risk", () => {
    const board = buildLeaderboard({
      reports: [
        rep("Ant", "c1", 0.5, 0.7, 1),   // towards established: +0.2
        rep("Bee", "c1", 0.7, 0.6, 1),   // away from established: −0.1, a misvalidation
        rep("Cat", "c2", 0.5, 0.3, 0),   // towards refuted: +0.2
        rep("Dog", "c3", 0.5, 0.8, null), // nothing resolved: 0.3 at risk
      ],
      agents: agentsOf("Ant", "Bee", "Cat", "Dog", "Emu"),
      stakes: () => 0,
    });
    assert.equal(board.version, LEADERBOARD_VERSION);
    const by = new Map(board.agents.map((a) => [a.agent, a] as const));
    assert.ok(near(by.get("Ant")!.banked, 0.2) && near(by.get("Cat")!.banked, 0.2) && near(by.get("Bee")!.banked, -0.1));
    assert.equal(by.get("Ant")!.rank, 1);
    assert.equal(by.get("Cat")!.rank, 1, "equal credence banked, equal rank");
    assert.equal(by.get("Bee")!.rank, 3, "competition ranking: two ahead of it");
    assert.equal(by.get("Bee")!.netNegative, true);
    assert.deepEqual([by.get("Bee")!.right, by.get("Bee")!.wrong, by.get("Bee")!.open], [0, 1, 0]);
    assert.equal(by.get("Dog")!.rank, null, "nothing of Dog's has resolved: not ranked");
    assert.ok(near(by.get("Dog")!.atRisk, 0.3) && by.get("Dog")!.banked === 0);
    assert.deepEqual(board.agents.map((a) => a.agent), ["Ant", "Cat", "Bee", "Dog"], "ranked first, by rank and name; then the unranked by credence at risk");
    assert.equal(board.operators.find((o) => o.operatorId === "op-bee")!.netNegative, true);
    assert.equal(board.totals.quiet, 1, "Emu filed nothing that moves credence");
    assert.deepEqual([board.totals.rankedAgents, board.totals.resolvedReports, board.totals.openReports], [3, 3, 1]);
    assert.ok(near(board.totals.banked, 0.3) && near(board.totals.atRisk, 0.3));
  });

  it("a report that moved nothing (evidence on one's own claim, Article 0.5) counts nowhere", () => {
    const board = buildLeaderboard({ reports: [rep("Ant", "c1", 0.6, 0.6, 1), rep("Ant", "c2", 0.6, 0.6, null)], agents: agentsOf("Ant"), stakes: () => 0 });
    assert.deepEqual(board.agents, []);
    assert.equal(board.totals.quiet, 1);
    assert.equal(contributionsOf([rep("Ant", "c1", 0.6, 0.6, 1)], () => "op-ant").length, 0);
  });

  it("arguments and their checks count from a neutral half against their own settlement, under the agent's operator", () => {
    const c = contributionsOf([{ id: "arg1", agent: "Ant", claim: "c1", seq: 3, before: 0.5, after: 0.9, resolved: 1, credit: 0.24 }], (a) => (a === "Ant" ? "op-x" : undefined));
    assert.equal(c.length, 1);
    assert.equal(c[0]!.kind, "argument");
    assert.equal(c[0]!.operatorId, "op-x", "an argument report carries no operator: the record's agent says whose it is");
    assert.ok(near(c[0]!.banked, 0.4));
  });

  it("penalties always have a row: a lapse, a finding in force, a voided operator", () => {
    const board = buildLeaderboard({
      reports: [], agents: agentsOf("Ant", "Bee", "Cat", "Dog"), stakes: () => 0,
      lapses: new Map([["Ant", 2]]), findings: new Map([["Bee", 1]]), voidedOperators: new Set(["op-bee", "op-cat"]),
    });
    const by = new Map(board.agents.map((a) => [a.agent, a] as const));
    assert.equal(by.get("Ant")!.lapses, 2);
    assert.equal(by.get("Bee")!.findings, 1);
    assert.equal(by.get("Bee")!.voided, true);
    assert.equal(by.get("Cat")!.voided, true);
    assert.equal(by.has("Dog"), false);
    assert.equal(board.operators.find((o) => o.operatorId === "op-cat")!.voided, true);
  });

  it("the audit list: claims by (stakes + ½) × credence at risk, resolved work left out, one row per claim, an operator's own work and claims left out of its list", () => {
    const reports = [
      rep("Ant", "c1", 0.5, 0.66, null), rep("Ant", "c1", 0.66, 0.71, null, { id: "ant-2" }), // 0.21 at risk on c1
      rep("Bee", "c2", 0.5, 0.9, null),                                                      // 0.4 at risk on c2
      rep("Cat", "c3", 0.5, 0.7, 1),                                                         // banked: never offered
      rep("Dog", "c4", 0.5, 0.45, null, { kind: "review" }),                                 // 0.05 at risk on c4
    ];
    const stakes = (c: string) => (c === "c1" ? 3 : 0);
    const all = auditList(contributionsOf(reports, () => undefined), stakes);
    assert.deepEqual(all.map((i) => i.claim), ["c1", "c2", "c4"], "c1: 3.5 × 0.21 = 0.735; c2: 0.5 × 0.4 = 0.2; c4: 0.5 × 0.05");
    assert.ok(near(all[0]!.weight, 3.5 * 0.21) && near(all[0]!.atRisk, 0.21));
    assert.equal(all[0]!.contributions.length, 1, "Ant's two reports on c1 are one line, not two");
    assert.ok(near(all[0]!.contributions[0]!.moved, 0.21) && all[0]!.contributions[0]!.reports === 2);
    assert.equal(all[0]!.contributions[0]!.id, "Ant-c1-0.5-0.66", "the line points at the heavier report");
    assert.match(all[0]!.how, /^commit_check against c1/);
    const forAnt = auditList(contributionsOf(reports, () => undefined), stakes, { exclude: (c) => c.operatorId === "op-ant", skipClaim: (c) => c === "c4" });
    assert.deepEqual(forAnt.map((i) => i.claim), ["c2"], "Ant's own work is not offered to Ant, nor a claim it authored");
    const conceptual = auditList(contributionsOf(reports, () => undefined), stakes, { kindOf: () => "conceptual" });
    assert.match(conceptual[0]!.how, /check_argument/);
    const voided = buildLeaderboard({ reports, agents: agentsOf("Ant", "Bee", "Cat", "Dog"), stakes, voidedOperators: new Set(["op-ant"]) });
    assert.ok(!voided.audit.some((i) => i.claim === "c1"), "a voided operator's work is offered to no one: it counts for nothing already");
  });

  it("adversarial: volume buys no rank, and filing more only adds to what is at risk", () => {
    const flood = Array.from({ length: 60 }, (_, i) => rep("Spam", `c${i}`, 0.55, 0.59, null, { id: `s${i}`, kind: "review" }));
    const board = buildLeaderboard({ reports: [...flood, rep("Honest", "x1", 0.5, 0.6, 1)], agents: agentsOf("Spam", "Honest"), stakes: () => 0 });
    const spam = board.agents.find((a) => a.agent === "Spam")!;
    const honest = board.agents.find((a) => a.agent === "Honest")!;
    assert.equal(spam.rank, null, "sixty reviews on claims nobody has settled rank nothing");
    assert.equal(spam.banked, 0);
    assert.ok(near(spam.atRisk, 60 * 0.04));
    assert.equal(honest.rank, 1, "one report the record confirmed outranks any volume of unconfirmed ones");
    // The same flood on claims that resolved against it is sixty losses, and the operator is marked.
    const wrong = buildLeaderboard({ reports: flood.map((r) => ({ ...r, resolved: 0 as const })), agents: agentsOf("Spam"), stakes: () => 0 });
    assert.ok(near(wrong.agents[0]!.banked, -60 * 0.04));
    assert.equal(wrong.agents[0]!.netNegative, true);
    assert.equal(wrong.operators[0]!.netNegative, true);
  });

  it("adversarial: splitting an operator's work across many agents changes none of its totals", () => {
    const work = [rep("A", "c1", 0.5, 0.7, 1), rep("A", "c2", 0.5, 0.4, 1), rep("A", "c3", 0.5, 0.6, null), rep("A", "c4", 0.4, 0.3, 0)];
    const one = buildLeaderboard({ reports: work.map((r) => ({ ...r, operatorId: "op-x" })), agents: new Map([["A", "op-x"]]), stakes: () => 0 });
    const split = work.map((r, i) => ({ ...r, agent: `A${i}`, operatorId: "op-x" }));
    const many = buildLeaderboard({ reports: split, agents: new Map(split.map((r) => [r.agent, "op-x"] as const)), stakes: () => 0 });
    const [o1, o2] = [one.operators[0]!, many.operators[0]!];
    assert.ok(near(o1.banked, o2.banked) && near(o1.atRisk, o2.atRisk));
    assert.deepEqual([o1.right, o1.wrong, o1.open], [o2.right, o2.wrong, o2.open]);
    assert.equal(o2.agents.length, 4);
  });
});

describe("leaderboard/0.1 on the scripted record", () => {
  it("every agent's credence banked is its resolved moves, signed; ranks, marks and the audit list follow", () => {
    const { record: r, scores: s } = resolveV2(scriptedLog(), new Date(Date.UTC(2026, 10, 1)));
    const board = buildLeaderboard(leaderboardInputOf(r, s, Number.MAX_SAFE_INTEGER, 50));
    assert.ok(board.totals.rankedAgents >= 5, "the scripted record resolves claims, so agents rank");
    for (const a of board.agents) {
      const mine = s.track.reports.filter((x) => x.agent === a.agent && Math.abs(x.after - x.before) > 1e-9 && !r.held.has(x.claim));
      const banked = mine.filter((x) => x.resolved !== null).reduce((acc, x) => acc + (x.after - x.before) * (2 * x.resolved! - 1), 0);
      assert.ok(near(a.banked, banked), `${a.agent}: ${a.banked} = ${banked}`);
      assert.equal(a.rank === null, a.right + a.wrong === 0, `${a.agent} is ranked exactly when something of its resolved`);
      assert.equal(a.netNegative, a.banked < -1e-9);
      if (r.voidedOperators.has(a.operatorId)) assert.ok(a.voided && a.banked === 0 && a.atRisk === 0, "a voided operator's work counts for nothing");
    }
    assert.ok(board.agents.some((a) => a.netNegative), "the scripted record has a misvalidation, and it shows");
    const ranked = board.agents.filter((a) => a.rank !== null);
    for (let i = 1; i < ranked.length; i++) assert.ok(ranked[i - 1]!.banked >= ranked[i]!.banked - 1e-9, "ranked by credence banked");
    for (const o of board.operators) assert.ok(near(o.banked, board.agents.filter((a) => a.operatorId === o.operatorId).reduce((acc, a) => acc + a.banked, 0)), `${o.operatorId} sums its agents`);
    for (const i of board.audit) {
      assert.ok(!r.held.has(i.claim));
      for (const c of i.contributions) assert.ok(!r.voidedOperators.has(c.operatorId));
    }
    assert.ok(board.audit.every((x, k) => k === 0 || board.audit[k - 1]!.weight >= x.weight), "the audit list is in order of weight");
  });
});

async function world() {
  const clock = { t: Date.UTC(2026, 9, 5, 9, 0, 0) };
  const now = () => new Date(clock.t);
  const logStore = new MemoryStore();
  const log = new TransparencyLog(logStore, now);
  const logKey = await generateKeyPair();
  const rows = () => (logStore as unknown as { log: Array<{ entry: { seq: number; ts: string; type: string }; payload: Json }> }).log.map((r) => ({ seq: r.entry.seq, ts: r.entry.ts, type: r.entry.type, payload: r.payload }));
  const svc = new V2Service({ log, store: new MemoryV2Store(rows), logPrivateKey: logKey.privateKey, now, screeners: [structuralScreener()] });
  const v1 = new EcdysisService({ store: logStore, screeners: [structuralScreener()], sthPrivateKey: null });
  const pages = new PagesHandler(svc, { host: "api.ecdysis.me" });
  const limiter = new MemoryRateLimiter(10_000);
  const keys = new Map<string, KeyPairB64>();
  const agent = async (handle: string, op: string, models: string[]) => {
    const kp = await generateKeyPair();
    keys.set(handle, kp);
    assert.equal((await svc.registerAgent({ constitution: ACK, handle, publicKey: kp.publicKey, operatorId: op, models })).status, 201);
    await svc.setTier(op, "verified");
  };
  const sign = async (handle: string, payload: Record<string, Json>) => {
    const kp = keys.get(handle)!;
    const full: Json = declared({ ...payload, agent: { handle, publicKey: kp.publicKey }, ts: now().toISOString().replace(/\.\d{3}Z$/, "Z") });
    return { payload: full, signature: await signJson(kp.privateKey, full) } as Json;
  };
  const register = async (handle: string, source: string, quote: string) => {
    const r = await svc.registerExternalClaim(await sign(handle, { protocol: "ecdysis/0.2", type: "claim.external", source, quote, test: "A multi-site replication with the stated protocol finds no effect." }));
    assert.equal(r.status, 201, JSON.stringify(r.body));
    return String(body(r)["ref"]);
  };
  const bundle = (n: number): Bundle => ({ repo: "https://github.com/example/rep", commit: n.toString(16).padStart(40, "0"), image: "sha256:" + "a".repeat(64), run: "python run.py", outputs: [{ name: "alpha", tolerance: 0.01 }], runtimeMinutes: 5 });
  /** A replication test, filed; the seal's cross-check, if any, re-run with matching outputs. */
  const check = async (handle: string, target: string, n: number, outcome: "confirmed" | "failed") => {
    const c = await svc.commitCheck(await sign(handle, { protocol: "ecdysis/0.2", type: "check.commit", target, kind: "replication", bundle: bundle(n) as unknown as Json }));
    assert.equal(c.status, 201, JSON.stringify(c.body));
    const cross = body(c)["crossCheck"] as Record<string, Json> | null;
    const r = await svc.fileResult(await sign(handle, { protocol: "ecdysis/0.2", type: "check.result", commit: String(body(c)["id"]), outcome, outputs: { alpha: 1 }, crossCheck: cross ? { receipt: String(cross["receipt"]), outputs: { alpha: 1 } } : null }));
    assert.equal(r.status, 201, JSON.stringify(r.body));
    return String(body(c)["id"]);
  };
  const get = async (path: string) => { const r = await route(new Request(`https://api.ecdysis.me${path}`), v1, limiter, { v2: svc, pages }); return { status: r.status, body: (await r.json()) as Record<string, Json> }; };
  const page = async (path: string) => { const r = await route(new Request(`https://api.ecdysis.me${path}`, { headers: { accept: "text/html" } }), v1, limiter, { v2: svc, pages }); return { status: r.status, html: await r.text() }; };
  return { svc, v1, agent, register, check, get, page };
}

describe("leaderboard/0.1, served", () => {
  it("a revealed outcome banks the right report and charges the wrong one; the operator below zero is marked on the board and on its agent's page", async () => {
    const w = await world();
    await w.agent("Ant", "op-a", ["claude"]);
    await w.agent("Bee", "op-b", ["gpt"]);
    await w.agent("Dog", "<b>op-d</b>", ["grok"]);
    const canary = await w.register("Ant", "doi:10.1126/science.aac4716", "ego depletion: a demanding first task reduces performance on a second self-control task");
    const open = await w.register("Ant", "arxiv:2203.15556", "the compute-optimal token count scales linearly with parameters");
    await w.check("Bee", canary, 1, "confirmed"); // wrong: the canary is known to fail
    await w.check("Dog", canary, 2, "failed");    // right
    await w.check("Bee", open, 3, "confirmed");   // unresolved: at risk, and offered for audit
    let lb = body(await w.get("/v2/leaderboard"));
    assert.equal(lb["version"], LEADERBOARD_VERSION);
    assert.equal((lb["totals"] as Record<string, Json>)["rankedAgents"], 0, "before the outcome is known nothing is banked");
    assert.equal((await w.svc.revealCanary(canary, "refuted", "op-steward")).status, 200);
    lb = body(await w.get("/v2/leaderboard"));
    const agents = lb["agents"] as Array<Record<string, Json>>;
    const by = new Map(agents.map((a) => [String(a["agent"]), a] as const));
    assert.equal(by.get("Dog")!["rank"], 1);
    assert.ok(Number(by.get("Dog")!["banked"]) > 0);
    assert.ok(Number(by.get("Bee")!["banked"]) < 0, "confirming a claim that turned out false banks a loss");
    assert.equal(by.get("Bee")!["netNegative"], true);
    assert.ok(Number(by.get("Bee")!["atRisk"]) > 0, "its confirmation of the open claim is still at risk");
    assert.equal((lb["operators"] as Array<Record<string, Json>>).find((o) => o["operatorId"] === "op-b")!["netNegative"], true);
    const audit = lb["audit"] as Array<Record<string, Json>>;
    assert.deepEqual(audit.map((i) => i["claim"]), [open], "the resolved claim is banked work, offered to no one; the open one is");
    assert.equal((audit[0]!["contributions"] as Array<Record<string, Json>>)[0]!["agent"], "Bee");
    assert.match(String(lb["note"]), /never instructions/);
    // Each agent's heartbeat: its own standing, and audits that leave out its own operator's work.
    const dog = body(await w.svc.heartbeat("Dog"));
    assert.equal((dog["standing"] as Record<string, Json>)["rank"], 1);
    assert.deepEqual((dog["audit"] as Array<Record<string, Json>>).map((i) => i["claim"]), [open]);
    const bee = body(await w.svc.heartbeat("Bee"));
    assert.equal((bee["standing"] as Record<string, Json>)["netNegative"], true);
    assert.deepEqual(bee["audit"], [], "Bee is never offered its own work to audit");
    assert.match(String(bee["note"]), /even an attempt is logged/i);
    // The pages: the board, and the mark on the agent's page.
    const pg = await w.page("/leaderboard");
    assert.equal(pg.status, 200);
    assert.match(pg.html, /<h1>Leaderboard<\/h1>/);
    assert.match(pg.html, /net negative/);
    assert.match(pg.html, /href="\/leaderboard" aria-current="page"|aria-current="page"[^>]*href="\/leaderboard"/);
    assert.doesNotMatch(pg.html, /<b>op-d<\/b>/, "an operator id is the operator's own text: escaped");
    assert.match(pg.html, /&lt;b&gt;op-d&lt;\/b&gt;/);
    assert.doesNotMatch(pg.html, /<script/);
    const beePage = await w.page("/a/Bee");
    assert.match(beePage.html, /net negative/);
    assert.match((await w.page("/a/Dog")).html, /rank 1 of 2/, "Dog and Bee both have a resolved report");
    const map = await w.page("/map");
    assert.doesNotMatch(map.html, /href="\/review"/, "the map carries the v2 navigation, never the first record's");
    assert.match(map.html, /<nav class="sub"[^>]*>.*href="\/leaderboard"/s);
    // The connector reads the same thing.
    const ctx = { svc: w.v1, host: "api.ecdysis.me", extraTools: v2Tools(w.svc) };
    const tool = await handleMcp({ jsonrpc: "2.0", id: 1, method: "tools/call", params: { name: "get_leaderboard", arguments: { limit: 1, audit: 1 } } } as unknown as Json, ctx);
    const got = JSON.parse((tool.body as { result: { content: Array<{ text: string }> } }).result.content[0]!.text) as Record<string, Json>;
    assert.equal((got["agents"] as Json[]).length, 1);
    assert.equal((got["agents"] as Array<Record<string, Json>>)[0]!["agent"], "Dog");
    assert.ok(V2_SITEMAP_PAGES.includes("/leaderboard"));
  });

  it("an empty record says nothing has resolved, ranks nobody and lists nothing to audit", () => {
    const html = leaderboardPageV2({ version: LEADERBOARD_VERSION, agents: [], operators: [], audit: [], totals: { rankedAgents: 0, rankedOperators: 0, resolvedReports: 0, openReports: 0, banked: 0, atRisk: 0, quiet: 3 }, claims: {} });
    assert.match(html, /Nothing has resolved yet/);
    assert.match(html, /Nothing to audit/);
    assert.match(html, /3 other agents have filed nothing/);
  });
});
