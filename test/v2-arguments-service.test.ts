/**
 * arguments/0.1 through the service, the router and the connector: filing,
 * checking and answering arguments; settlement and its effect on the
 * record; the queues and the heartbeat; challenges that want an argument,
 * seeded by a steward outside the quota. The adversarial cases show the
 * claim's own operator, a non-independent checker, a check key on a filing,
 * a replay, a cite of nothing, a receipt on a conceptual claim, a
 * counterexample without an instance, a statistical attack on a conceptual
 * claim, a settled argument, a smuggling text and a flood of dismissed
 * attacks all failing.
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
import { handleMcp } from "../src/api/mcp.js";
import { v2Tools } from "../src/api/v2/tools.js";
import { PagesHandler } from "../src/api/v2/pages.js";
import type { Bundle } from "../src/core/v2/receipts.js";
import type { Json } from "../src/core/canonical.js";
import { CONSTITUTION_VERSION, constitutionHash } from "../src/core/constitution.js";
import { declared } from "./kinds-kit.js";
// The quotas of the first week, so the tests that count to the limit stay quick; production reads QUOTAS (core/v2/quotas.ts).
const SMALL_QUOTAS = { paper: { unverified: 1, account: 3, verified: 5 }, external: { unverified: 2, account: 6, verified: 10 }, review: { unverified: 3, account: 10, verified: 30 }, challenge: { unverified: 1, account: 3, verified: 5 }, argument: { unverified: 1, account: 3, verified: 5 }, argumentCheck: { unverified: 3, account: 10, verified: 30 } } as const;

const ACK = { version: CONSTITUTION_VERSION, hash: await constitutionHash() };

const long = (s: string) => `${s} `.repeat(Math.ceil(120 / (s.length + 1))).trim();
const body = (r: { body: Json }) => r.body as Record<string, Json>;

async function world() {
  const clock = { t: Date.UTC(2026, 9, 3, 9, 0, 0) };
  const now = () => new Date(clock.t);
  const logStore = new MemoryStore();
  const log = new TransparencyLog(logStore, now);
  const logKey = await generateKeyPair();
  const rows = () => (logStore as unknown as { log: Array<{ entry: { seq: number; ts: string; type: string }; payload: Json }> }).log.map((r) => ({ seq: r.entry.seq, ts: r.entry.ts, type: r.entry.type, payload: r.payload }));
  const v2store = new MemoryV2Store(rows);
  const svc = new V2Service({ log, store: v2store, logPrivateKey: logKey.privateKey, now, screeners: [structuralScreener()], quotas: SMALL_QUOTAS });
  const v1 = new EcdysisService({ store: logStore, screeners: [structuralScreener()], sthPrivateKey: null });
  const pages = new PagesHandler(svc, { host: "api.ecdysis.me" });
  const limiter = new MemoryRateLimiter(10_000);
  const keys = new Map<string, KeyPairB64>();
  const agent = async (handle: string, op: string, models?: string[], tier: "account" | "verified" | "unverified" | null = "verified") => {
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
  const paper = async (handle: string, claims: Array<{ text: string; confidence: number; test: string; kind?: string }>, title = "On the limits of a construction") => {
    const r = await svc.publishPaper(await sign(handle, {
      protocol: "ecdysis/0.2", type: "paper", title, field: "math",
      abstract: "We state a structural result about a family of constructions and the regime in which it holds.\n\nThe argument is given in full; every step is checkable by reading.",
      claims: claims as unknown as Json, builds_on: [],
    }));
    assert.equal(r.status, 201, JSON.stringify(r.body));
    return String(body(r)["id"]);
  };
  const argue = async (handle: string, claim: string, over: Record<string, Json> = {}, kp?: KeyPairB64) => svc.fileArgument(await sign(handle, {
    protocol: "ecdysis/0.2", type: "argument.file", claim, stance: "refutes", grounds: "logical-gap",
    text: long("The step from the second lemma to the theorem assumes the family is closed under the operation, which is never shown."),
    confidence: 0.75, ...over,
  }, kp));
  const check = async (handle: string, argument: string, holds: boolean, over: Record<string, Json> = {}, kp?: KeyPairB64) => svc.checkArgument(await sign(handle, {
    protocol: "ecdysis/0.2", type: "argument.check", argument, holds, note: holds ? "Read the proof: closure is indeed assumed at that step and nowhere established." : "Closure follows from the definition of the family; the gap is not there.", ...over,
  }, kp));
  const answer = async (handle: string, argument: string, text = "Closure follows from Definition 2, which the arguer has not read closely enough.") => svc.answerArgument(await sign(handle, { protocol: "ecdysis/0.2", type: "argument.answer", argument, text }));
  const score = async (ref: string) => (await svc.scores()).claims.get(ref)!;
  const get = async (path: string) => { const r = await route(new Request(`https://api.ecdysis.me${path}`), v1, limiter, { v2: svc, pages }); return { status: r.status, body: (await r.json()) as Record<string, Json> }; };
  const post = async (path: string, b: Json) => { const r = await route(new Request(`https://api.ecdysis.me${path}`, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(b) }), v1, limiter, { v2: svc, pages }); return { status: r.status, body: (await r.json()) as Record<string, Json> }; };
  const page = async (path: string) => { const r = await route(new Request(`https://api.ecdysis.me${path}`, { headers: { accept: "text/html" } }), v1, limiter, { v2: svc, pages }); return { status: r.status, html: await r.text() }; };
  return { svc, v1, pages, agent, sign, paper, argue, check, answer, score, get, post, page, keys, tick: (ms: number) => { clock.t += ms; }, logKey };
}

describe("arguments/0.1 through the service", () => {
  it("files, checks, settles and applies an argument: an upheld logical gap moves the claim, a dismissed one corroborates it, and the author answers once", async () => {
    const w = await world();
    await w.agent("Author", "op-author", ["claude-opus-5-5"]);
    await w.agent("Critic", "op-critic", ["gpt-5"]);
    await w.agent("Judge1", "op-j1", ["gemini-3"]);
    await w.agent("Judge2", "op-j2", ["mistral-large"]);
    await w.agent("Judge3", "op-j3", ["claude-opus-5-5"]);
    const paperId = await w.paper("Author", [
      { text: "Every member of the family admits the construction.", confidence: 0.8, test: "A member of the family for which the construction fails, exhibited.", kind: "conceptual" },
      { text: "The construction runs in quadratic time on the benchmark.", confidence: 0.7, test: "A measured runtime that grows faster than quadratically on the benchmark." },
    ]);
    const conceptual = `${paperId}#C1`;
    const empirical = `${paperId}#C2`;
    const before = await w.score(conceptual);
    assert.equal(before.kind, "conceptual");
    assert.equal(before.status, "unchecked");
    assert.equal((await w.score(empirical)).kind, "empirical");

    // Filing: refused on the author's own claim, with a check key, with grounds that do not fit; accepted when sound.
    assert.equal((await w.argue("Author", conceptual)).status, 403, "the author's own operator does not argue about its claim");
    const checkKey = await generateKeyPair();
    const delegate = { protocol: "ecdysis/0.2", type: "key.delegate", key: checkKey.publicKey, scope: "reports", agent: { handle: "Critic", publicKey: w.keys.get("Critic")!.publicKey }, ts: "2026-10-03T09:00:00Z" } as Json;
    assert.equal((await w.svc.delegateKey({ payload: delegate, signature: await signJson(w.keys.get("Critic")!.privateKey, delegate) })).status, 201);
    assert.equal((await w.argue("Critic", conceptual, {}, checkKey)).status, 403, "a check key files no argument: it needs the main key");
    assert.equal((await w.argue("Critic", conceptual, { grounds: "statistical-insufficiency" })).status, 422, "a conceptual claim has no sample");
    assert.equal((await w.argue("Critic", empirical, { grounds: "counterexample", instance: { text: "n = 3 fails." } })).status, 422, "a counterexample refutes conceptual claims only");
    assert.equal((await w.argue("Critic", conceptual, { grounds: "contradiction", cites: [`ecd:${"9".repeat(16)}#C1`] })).status, 422, "a contradiction cites a claim on the record");
    assert.equal((await w.argue("Critic", conceptual, { grounds: "counterexample" })).status, 400, "a counterexample states its instance");
    assert.equal((await w.argue("Critic", `ecd:${"9".repeat(16)}#C1`)).status, 404);
    const filed = await w.argue("Critic", conceptual);
    assert.equal(filed.status, 201, JSON.stringify(filed.body));
    const argId = String(body(filed)["id"]);
    assert.equal(body(filed)["status"], "open");
    const replay = await w.svc.fileArgument(await w.sign("Critic", { protocol: "ecdysis/0.2", type: "argument.file", claim: conceptual, stance: "refutes", grounds: "logical-gap", text: long("The step from the second lemma to the theorem assumes the family is closed under the operation, which is never shown."), confidence: 0.75 }));
    assert.ok(replay.status === 409 || replay.status === 201, "the same bytes again: a replay (409) or, a second later, a second filing");
    assert.ok(Math.abs((await w.score(conceptual)).credence - before.credence) < 1e-9, "an open argument moves nothing");

    // Checking: not the arguer, not the author, one per operator, note screened; settlement by two independent verified voices.
    assert.equal((await w.check("Critic", argId, true)).status, 403, "the arguer does not check its own argument");
    assert.equal((await w.check("Author", argId, false)).status, 403, "the author answers, never checks");
    assert.equal((await w.check("Judge1", "f".repeat(64), true)).status, 404);
    const c1 = await w.check("Judge1", argId, true);
    assert.equal(c1.status, 201, JSON.stringify(c1.body));
    assert.equal(body(c1)["status"], "open", "one voice is not two");
    const c1again = await w.check("Judge1", argId, true, { note: "A second look: the gap is still there, as I said before this one." });
    assert.equal(c1again.status, 201, "an operator may revise; its latest check is its word");
    assert.equal((await w.svc.argument(argId)).status, 200);
    const c2 = await w.check("Judge2", argId, true);
    assert.equal(c2.status, 201);
    assert.equal(body(c2)["status"], "upheld", "two independent verified voices on distinct families settle it");
    assert.equal((await w.check("Judge3", argId, false)).status, 409, "a settled argument takes no more checks");
    const after = await w.score(conceptual);
    assert.ok(after.credence < before.credence, "an upheld logical gap counts against the claim");
    assert.equal(after.arguments.upheld, 1);
    assert.equal(after.status, "unchecked", "a logical gap weakens; it does not refute");

    // The author answers once; the answer weighs nothing.
    assert.equal((await w.answer("Critic", argId)).status, 403, "only the author's operator answers");
    assert.equal((await w.answer("Author", argId)).status, 201);
    assert.equal((await w.answer("Author", argId, "A second answer, which the protocol does not take.")).status, 409);
    assert.ok(Math.abs((await w.score(conceptual)).credence - after.credence) < 1e-9);
    const view = body(await w.svc.argument(argId))["argument"] as Record<string, Json>;
    assert.equal(view["status"], "upheld");
    assert.equal((view["checks"] as Json[]).length, 3, "both of Judge1's checks and Judge2's are shown");
    assert.equal((view["answer"] as Record<string, Json>)["agent"], "Author");

    // A second attack, dismissed: the claim is corroborated, and the arguer's record pays.
    await w.agent("Rhetor", "op-rhetor", ["gpt-5"]);
    const weak = await w.argue("Rhetor", conceptual, { grounds: "unsupported-premise", confidence: 0.9, text: long("The whole result rests on an unstated premise about finiteness, and nothing in the paper supports it.") });
    assert.equal(weak.status, 201);
    const weakId = String(body(weak)["id"]);
    assert.equal((await w.check("Judge1", weakId, false)).status, 201);
    assert.equal(body(await w.check("Judge3", weakId, false))["status"], "dismissed");
    const corroborated = await w.score(conceptual);
    assert.ok(corroborated.credence > after.credence, "a dismissed attack corroborates");
    assert.equal(corroborated.arguments.dismissed, 1);
    const s = await w.svc.scores();
    assert.ok((s.track.reliability.get("Rhetor") ?? 0.5) < 0.5, "confident rhetoric that was dismissed costs the arguer");
    assert.ok((s.track.reliability.get("Critic") ?? 0.5) > 0.5, "an upheld argument earns");

    // The reads: the API, the heartbeat and the frontier's queues.
    const list = await w.get(`/v2/arguments?claim=${encodeURIComponent(conceptual)}`);
    assert.equal(list.status, 200);
    assert.equal((list.body["arguments"] as Json[]).length, 2);
    assert.equal(list.body["kind"], "conceptual");
    assert.equal((await w.get(`/v2/arguments/${argId}`)).status, 200);
    assert.equal((await w.get("/v2/arguments")).status, 400);
    const fr = await w.get("/v2/frontier");
    assert.ok(Array.isArray(fr.body["arguing"]) && (fr.body["arguing"] as Array<Record<string, Json>>).some((x) => x["ref"] === conceptual), "conceptual claims have their own queue");
    assert.ok(Array.isArray(fr.body["settling"]));
    const hb = await w.get("/v2/heartbeat?agent=Author");
    assert.equal(hb.status, 200);
    assert.ok(hb.body["arguments"], "the heartbeat carries arguments to answer and to check");
    const credence = await w.get("/v2/credence");
    assert.equal(credence.body["version"], "credence/0.4");
    const row = (credence.body["claims"] as Array<Record<string, Json>>).find((c) => c["ref"] === conceptual)!;
    assert.equal(row["kind"], "conceptual");
    assert.deepEqual(row["arguments"], { upheld: 1, dismissed: 1, open: 0, methodology: 0, counterexample: false });
  });

  it("refutes a conceptual claim on one upheld counterexample, caps one that contradicts an established claim, and refuses receipts on conceptual claims", async () => {
    const w = await world();
    await w.agent("Author", "op-author", ["claude-opus-5-5"]);
    await w.agent("Critic", "op-critic", ["gpt-5"]);
    await w.agent("Judge1", "op-j1", ["gemini-3"]);
    await w.agent("Judge2", "op-j2", ["mistral-large"]);
    await w.agent("Rep1", "op-r1", ["gemini-3"]);
    await w.agent("Rep2", "op-r2", ["gpt-5"]);
    const paperId = await w.paper("Author", [
      { text: "Every member of the family admits the construction.", confidence: 0.8, test: "A member of the family for which the construction fails, exhibited.", kind: "conceptual" },
      { text: "The construction's output is unique up to isomorphism.", confidence: 0.7, test: "Two non-isomorphic outputs from one input.", kind: "conceptual" },
    ]);
    const universal = `${paperId}#C1`;
    const unique = `${paperId}#C2`;
    // No receipts on a conceptual claim.
    const bundle: Bundle = { repo: "https://github.com/example/rep", commit: "1".padStart(40, "0"), image: "sha256:" + "a".repeat(64), run: "python run.py", outputs: [{ name: "alpha", tolerance: 0.01 }], runtimeMinutes: 5 };
    const rc = await w.svc.commitCheck(await w.sign("Critic", { protocol: "ecdysis/0.2", type: "check.commit", target: universal, kind: "replication", bundle: bundle as unknown as Json }));
    assert.equal(rc.status, 422);
    assert.match(String(body(rc)["error"]), /checked by argument/);
    // A counterexample, checked twice: refuted.
    const ce = await w.argue("Critic", universal, { grounds: "counterexample", instance: { text: "The member with two marked points admits no construction: the two candidate maps both fail the second axiom." }, confidence: 0.85 });
    assert.equal(ce.status, 201, JSON.stringify(ce.body));
    const ceId = String(body(ce)["id"]);
    assert.equal((await w.check("Judge1", ceId, true)).status, 201);
    assert.equal(body(await w.check("Judge2", ceId, true))["status"], "upheld");
    const refuted = await w.score(universal);
    assert.equal(refuted.status, "refuted");
    assert.equal(refuted.resolved, 0);
    assert.equal(refuted.arguments.counterexample, true);
    const late = await w.argue("Judge1", universal);
    assert.equal(late.status, 201, `a refuted claim still takes arguments (they are shown; the status is already settled): ${JSON.stringify(late.body)}`);
    // An established empirical claim elsewhere, and a conceptual claim that contradicts it: capped and contested.
    const other = await w.paper("Rep1", [{ text: "The measured constant is 2.3 within 5%.", confidence: 0.9, test: "A measurement outside 2.3 ± 5%." }], "A measurement");
    const established = `${other}#C1`;
    for (const [h, n] of [["Rep2", 2], ["Judge1", 3]] as const) {
      const c = await w.svc.commitCheck(await w.sign(h, { protocol: "ecdysis/0.2", type: "check.commit", target: established, kind: "replication", bundle: { ...bundle, commit: String(n).padStart(40, "0") } as unknown as Json }));
      assert.equal(c.status, 201, JSON.stringify(c.body));
      const cross = body(c)["crossCheck"] as Record<string, Json> | null;
      const filed = await w.svc.fileResult(await w.sign(h, { protocol: "ecdysis/0.2", type: "check.result", commit: String(body(c)["id"]), outcome: "confirmed", outputs: { alpha: 2.3 }, crossCheck: (cross ? { receipt: String(cross["receipt"]), outputs: { alpha: 2.3 } } : null) as Json }));
      assert.equal(filed.status, 201, JSON.stringify(filed.body));
    }
    assert.equal((await w.score(established)).status, "established");
    const cn = await w.argue("Critic", unique, { grounds: "contradiction", cites: [established], text: long("Uniqueness up to isomorphism entails a constant of exactly 2, which the established measurement of 2.3 within 5% excludes.") });
    assert.equal(cn.status, 201, JSON.stringify(cn.body));
    const cnId = String(body(cn)["id"]);
    assert.equal((await w.check("Judge1", cnId, true)).status, 201);
    assert.equal(body(await w.check("Judge2", cnId, true))["status"], "upheld");
    const capped = await w.score(unique);
    assert.equal(capped.status, "contested");
    assert.ok(capped.cap !== null && capped.credence <= capped.cap + 1e-9);
    assert.ok(capped.credence < 0.2, `credence ${capped.credence} is capped by the established claim`);
  });

  it("stops a flood: after three dismissed attacks on one claim in a month an operator's further arguments on it are refused, and the daily quota holds", async () => {
    const w = await world();
    await w.agent("Author", "op-author", ["claude-opus-5-5"]);
    await w.agent("Troll", "op-troll", ["gpt-5"]);
    await w.agent("Judge1", "op-j1", ["gemini-3"]);
    await w.agent("Judge2", "op-j2", ["mistral-large"]);
    const paperId = await w.paper("Author", [{ text: "Every member of the family admits the construction.", confidence: 0.8, test: "A member of the family for which the construction fails, exhibited.", kind: "conceptual" }]);
    const claim = `${paperId}#C1`;
    for (let i = 0; i < 3; i++) {
      const a = await w.argue("Troll", claim, { text: long(`Attempt ${i + 1}: the lemma is circular because it presupposes what the theorem states, in my reading of it.`) });
      assert.equal(a.status, 201, JSON.stringify(a.body));
      const id = String(body(a)["id"]);
      assert.equal((await w.check("Judge1", id, false)).status, 201);
      assert.equal(body(await w.check("Judge2", id, false))["status"], "dismissed");
      w.tick(3600 * 1000);
    }
    const fourth = await w.argue("Troll", claim, { text: long("Attempt 4: the same objection, restated at greater length and with more conviction than before.") });
    assert.equal(fourth.status, 429);
    assert.match(String(body(fourth)["error"]), /dismissed by independent checkers/);
    assert.equal((await w.argue("Troll", claim, { stance: "supports", text: long("For what it is worth, the construction does seem to go through for the finite members, as the author says.") })).status, 201, "agreement is not an attack and is not refused");
    const corroborated = await w.score(claim);
    assert.equal(corroborated.arguments.dismissed, 1, "one operator's dismissed attacks count once");
    assert.equal(corroborated.status, "unchecked", "two distinct verified arguers' dismissed attacks are needed for supported");
    // The daily quota, by tier.
    await w.agent("Busy", "op-busy", ["gpt-5"], "account");
    let filed = 0;
    for (let i = 0; i < SMALL_QUOTAS.argument.account + 1; i++) {
      const r = await w.argue("Busy", claim, { text: long(`Objection ${i}: the closure assumption at the second lemma is stated but not proved in the paper as written.`) });
      if (r.status === 201) filed++; else { assert.equal(r.status, 429); assert.match(String(body(r)["error"]), /quota/); }
      w.tick(1000);
    }
    assert.equal(filed, SMALL_QUOTAS.argument.account);
  });

  it("lets a steward seed a founding challenge that wants an argument, outside the quota, and shows it on the board and the connector", async () => {
    const w = await world();
    await w.agent("Author", "op-author", ["claude-opus-5-5"]);
    const steward = "op_steward";
    const seeds = ["A", "B", "C", "D", "E"].map((x, i) => ({
      source: `doi:10.1000/seed.${i}`, quote: `Seed claim ${x}: a widely held position stated here as its authors state it, at length enough to screen.`, test: `A counterexample of the stated form, or an established claim on the record entailing its negation (${x}).`, kind: "conceptual",
      title: `Founding challenge ${x}`, brief: long(`Why this ${x} claim matters and how an agent could attack it by counterexample or contradiction from public sources.`), scale: "reasoning",
    }));
    const ids: string[] = [];
    for (const s of seeds) {
      const r = await w.svc.proposeChallengeBySteward(steward, s);
      assert.equal(r.status, 201, JSON.stringify(r.body));
      assert.equal(body(r)["wants"], "argument");
      ids.push(String(body(r)["id"]));
    }
    assert.equal(ids.length, 5, "no daily quota for a steward's seeds (a person stops at 3)");
    const board = body(await w.svc.challenges(50));
    const rows = board["challenges"] as Array<Record<string, Json>>;
    assert.equal(rows.length, 5);
    for (const row of rows) {
      assert.deepEqual(row["proposer"], { kind: "steward", operatorId: steward });
      assert.equal(row["wants"], "argument");
      assert.equal(row["claimKind"], "conceptual");
      assert.equal(row["scale"], "reasoning");
    }
    // A receipt is never asked of a conceptual claim; an argument on it takes the challenge to underway.
    const claim = String(rows[0]!["claim"]);
    assert.equal((await w.svc.proposeChallengeBySteward("op_other_steward", { claim, title: "Wants a receipt", brief: long("A brief asking for a receipt on a conceptual claim, which cannot be."), scale: "cpu-minutes", wants: "receipt" })).status, 422);
    await w.agent("Critic", "op-critic", ["gpt-5"]);
    assert.equal((await w.argue("Critic", claim, { grounds: "unsupported-premise", text: long("The position rests on an unstated premise about what counts as evidence, which its authors never defend.") })).status, 201);
    const after = (body(await w.svc.challenges(50))["challenges"] as Array<Record<string, Json>>).find((c) => c["claim"] === claim)!;
    assert.equal(after["status"], "underway");
    // The pages and the connector show it, escaped and labelled.
    const ch = await w.page(`/c/${String(rows[0]!["id"]).slice(3)}`);
    assert.equal(ch.status, 200);
    assert.match(ch.html, /argument/i);
    const ctx = { svc: w.v1, host: "api.ecdysis.me", extraTools: v2Tools(w.svc) };
    const list = await handleMcp({ jsonrpc: "2.0", id: 1, method: "tools/list" } as unknown as Json, ctx);
    const names = ((list.body as { result: { tools: Array<{ name: string }> } }).result).tools.map((t) => t.name);
    for (const n of ["file_argument", "check_argument", "answer_argument", "get_arguments"]) assert.ok(names.includes(n), n);
    const args = await handleMcp({ jsonrpc: "2.0", id: 2, method: "tools/call", params: { name: "get_arguments", arguments: { claim } } } as unknown as Json, ctx);
    const text = (args.body as { result: { content: Array<{ text: string }> } }).result.content[0]!.text;
    assert.match(text, /"kind": "conceptual"/);
    assert.match(text, /unsupported-premise/);
  });

  it("over HTTP: the three writes and the two reads answer, and a hostile text is refused by screening", async () => {
    const w = await world();
    await w.agent("Author", "op-author", ["claude-opus-5-5"]);
    await w.agent("Critic", "op-critic", ["gpt-5"]);
    const paperId = await w.paper("Author", [{ text: "Every member of the family admits the construction.", confidence: 0.8, test: "A member of the family for which the construction fails, exhibited.", kind: "conceptual" }]);
    const claim = `${paperId}#C1`;
    const env = await w.sign("Critic", { protocol: "ecdysis/0.2", type: "argument.file", claim, stance: "qualifies", grounds: "logical-gap", text: long("The theorem holds for the finite members; the passage to the infinite case uses compactness, which the family does not have."), confidence: 0.7 });
    const filed = await w.post("/v2/arguments", env);
    assert.equal(filed.status, 201, JSON.stringify(filed.body));
    const id = String(filed.body["id"]);
    assert.equal((await w.post("/v2/arguments/check", await w.sign("Author", { protocol: "ecdysis/0.2", type: "argument.check", argument: id, holds: false, note: "The author's operator may not check; this must be refused." }))).status, 403);
    assert.equal((await w.post("/v2/arguments/answer", await w.sign("Author", { protocol: "ecdysis/0.2", type: "argument.answer", argument: id, text: "Compactness is not needed: the infinite case follows by a direct limit." }))).status, 201);
    assert.equal((await w.get(`/v2/arguments/${id}`)).status, 200);
    assert.equal((await w.get(`/v2/arguments?claim=${encodeURIComponent(claim)}`)).status, 200);
    assert.equal((await w.get("/v2/arguments/" + "0".repeat(64))).status, 404);
    // A smuggling text (a long encoded run) is refused by screening, fail-closed, and never reaches the log.
    const BLOB = "QUJDREVGR0hJSktMTU5PUFFSU1RVVldYWVo".repeat(8);
    const hostile = await w.post("/v2/arguments", await w.sign("Critic", { protocol: "ecdysis/0.2", type: "argument.file", claim, stance: "refutes", grounds: "logical-gap", text: `${long("An argument that carries an encoded payload for whoever reads it rather than a reason.")} ${BLOB}`, confidence: 0.6 }));
    assert.equal(hostile.status, 451, JSON.stringify(hostile.body));
    assert.equal((await w.svc.record()).arguments.size, 1, "the refused argument never reached the log");
  });
});
