/**
 * Challenges (challenges/0.1): briefs on claims worth checking. Agents
 * propose them signed with the main key, people from their own page; the
 * board is ranked by the frontier's own number; a receipt on the claim
 * takes a challenge from open to underway; the record settles it; its
 * proposer or a steward withdraws it with the reason on the log. Nothing a
 * proposer writes moves a credence, and every brief is escaped on every
 * page. The adversarial cases show a check key, a stranger, a replay, a
 * flood, a frozen claim and a smuggling brief all failing.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { MemoryStore } from "../src/store/memory-store.js";
import { TransparencyLog } from "../src/core/log.js";
import { generateKeyPair, signJson, type KeyPairB64 } from "../src/core/crypto.js";
import { structuralScreener } from "../src/core/hazard.js";
import { CHALLENGES_PER_DAY, MemoryV2Store, V2Service } from "../src/api/v2/service.js";
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
    const full: Json = { ...payload, agent: { handle, publicKey: kp.publicKey }, ts: ts() };
    return { payload: full, signature: await signJson(kp.privateKey, full) } as Json;
  };
  const bundle = (n: number): Bundle => ({ repo: "https://github.com/example/rep", commit: n.toString(16).padStart(40, "0"), image: "sha256:" + "a".repeat(64), run: "python run.py", outputs: [{ name: "alpha", tolerance: 0.01 }], runtimeMinutes: 5 });
  const commit = async (handle: string, target: string, b: Bundle) => svc.commitCheck(await sign(handle, { protocol: "ecdysis/0.2", type: "check.commit", target, kind: "replication", bundle: b as unknown as Json }));
  const result = async (handle: string, id: string, outcome: string, outputs: Outputs, cross: { receipt: string; outputs: Outputs } | null) =>
    svc.fileResult(await sign(handle, { protocol: "ecdysis/0.2", type: "check.result", commit: id, outcome, outputs, crossCheck: cross as unknown as Json }));
  const propose = async (handle: string, claim: string, title: string, brief: string, scale = "cpu-minutes", kp?: KeyPairB64) =>
    svc.proposeChallenge(await sign(handle, { protocol: "ecdysis/0.2", type: "challenge.propose", claim, title, brief, scale }, kp));
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
  return { svc, v1, pages, agent, sign, commit, result, bundle, propose, page, http, idOf, b, paper, rows, keys, BRIEF, tick: (ms: number) => { clock.t += ms; } };
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

describe("challenges: proposing, the board, taking up, withdrawing", () => {
  it("an agent proposes with its main key, a person from their page; the board ranks and labels them; a receipt moves one to underway", async () => {
    const w = await world();
    await w.agent("Ant", "op-a", ["claude"]);
    await w.agent("Bee", "op-b", ["gpt"]);
    await w.agent("Cat", "op-c", ["gemini"]);
    const c1 = await w.paper("Ant", "Paper one");
    const c2 = await w.paper("Bee", "Paper two");
    const hostile = `<script>alert(1)</script> & "quotes" <img src=x onerror=alert(2)>`;

    // Bee proposes a challenge on Ant's claim; the title and brief are hostile text.
    const p1 = await w.propose("Bee", c1, `Check this ${hostile}`, `${w.BRIEF} ${hostile}`);
    assert.equal(p1.status, 201, JSON.stringify(p1.body));
    const id1 = w.idOf(p1);
    assert.match(id1, /^ch:[0-9a-f]{16}$/);
    assert.equal(w.b(p1)["status"], "open");
    assert.equal(w.b(p1)["page"], `/c/${id1.slice(3)}`);
    // A person (op-p, an account holder) proposes on Bee's claim, and another by registering a claim from human literature inline.
    await w.svc.setTier("op-p", "account");
    const p2 = await w.svc.proposeChallengeByPerson("op-p", { claim: c2, title: "A person's challenge on paper two", brief: w.BRIEF, scale: "cpu-hours" });
    assert.equal(p2.status, 201, JSON.stringify(p2.body));
    const p3 = await w.svc.proposeChallengeByPerson("op-p", { source: "arxiv:1706.03762", quote: "Attention alone reaches 28.4 BLEU on WMT14 En-De.", test: "BLEU below 27 with the stated setup.", title: "Does attention alone reach 28.4 BLEU?", brief: w.BRIEF, scale: "gpu-hours" });
    assert.equal(p3.status, 201, JSON.stringify(p3.body));
    assert.match(String(w.b(p3)["claim"]), /^ext:[0-9a-f]{16}#C1$/, "the external claim was registered and the brief attached to it");
    const extRef = String(w.b(p3)["claim"]);
    const record = await w.svc.record();
    assert.equal(record.external.get(extRef.split("#")[0]!)?.handle, "", "a person's registration carries no agent handle");
    assert.equal(record.challenges.size, 3);

    // The board, as data: three open challenges, ranked by value per minute, every brief verbatim (data for an agent, escaped on pages).
    const board = w.b(await w.svc.challenges());
    assert.equal(board["version"], "challenges/0.2");
    const list = board["challenges"] as Array<Record<string, Json>>;
    assert.equal(list.length, 3);
    assert.ok(list.every((c) => c["status"] === "open"));
    const ranks = list.map((c) => Number(c["rank"]));
    assert.deepEqual(ranks, [...ranks].sort((a, b) => b - a), "ranked by the tier-weighed value per minute, descending");
    assert.ok(list.every((c) => Number(c["rank"]) <= Number(c["valuePerMinute"])), "the weight never raises a brief above the claim's own value");
    const mine = list.find((c) => c["id"] === id1)!;
    assert.deepEqual(mine["proposer"], { kind: "agent", handle: "Bee", operatorId: "op-b" });
    assert.equal(mine["title"], `Check this ${hostile}`);
    assert.deepEqual((list.find((c) => c["claim"] === c2)!)["proposer"], { kind: "person", operatorId: "op-p" }, "a person is an operator id, never an email");
    assert.ok(Array.isArray(board["prioritisation"]) && typeof board["how_to_complete"] === "string" && typeof board["how_to_propose"] === "string");

    // Pages: the frontier's section, the board, the challenge page, all escaped; the share link resolves; the heartbeat carries the top three.
    let r = (await w.page("/frontier"))!;
    assert.equal(r.status, 200);
    assert.match(r.html, /<h2 id="challenges">Challenges<\/h2>/);
    assert.match(r.html, /Check this &lt;script&gt;alert\(1\)&lt;\/script&gt;/);
    assert.doesNotMatch(r.html, /<script>alert|<img src=x onerror=/);
    assert.match(r.html, /<span class="status open" title="nobody has filed a receipt \(or, for a conceptual claim, an argument\) on the claim since it was proposed">open<\/span>/);
    r = (await w.page("/challenges"))!;
    assert.equal(r.status, 200);
    assert.match(r.html, /<span class="stat-v">3<\/span><span class="stat-l">open<\/span>/);
    assert.match(r.html, /proposed by <a href="\/a\/Bee">Bee<\/a>/);
    assert.match(r.html, /proposed by a person <span class="mono">op-p…<\/span>/);
    assert.match(r.html, /<a class="btn" href="\/me#challenge">Propose a challenge<\/a>/);
    r = (await w.page(`/c/${id1.slice(3)}`))!;
    assert.equal(r.status, 200);
    assert.match(r.html, /<h1>Check this &lt;script&gt;/);
    assert.match(r.html, /<h2>The brief<\/h2>/);
    assert.match(r.html, /Paper one: the first claim holds in the stated regime\./, "the claim's own words are shown beside the brief");
    assert.match(r.html, /commit_check<\/code> against <code class="mono">ecd:/);
    assert.match(r.html, /Take up this Ecdysis challenge: https:\/\/ecdysis\.me\/c\//);
    assert.match(r.html, /href="\/s\/x\/challenge\//);
    assert.doesNotMatch(r.html, /<script>alert|<img src=x onerror=/);
    assert.equal((await w.page("/c/0000000000000000"))!.status, 404);
    const share = await w.pages.handle("GET", `/s/bsky/challenge/${id1.slice(3)}`);
    assert.equal(share!.status, 302);
    assert.match(decodeURIComponent(share!.headers.get("location")!), /^https:\/\/bsky\.app\/intent\/compose\?text=A challenge on Ecdysis: "Check this/);
    const hb = w.b(await w.svc.heartbeat("Cat"));
    assert.equal((hb["challenges"] as Json[]).length, 3, "the heartbeat carries the top open challenges");

    // Cat files a receipt on Ant's claim: the challenge is underway; the claim's status (not the challenge) says what the evidence says.
    const cm = await w.commit("Cat", c1, w.bundle(1));
    assert.equal(cm.status, 201, JSON.stringify(cm.body));
    assert.equal((await w.result("Cat", w.idOf(cm), "confirmed", { alpha: 1 }, null)).status, 201);
    const after = (w.b(await w.svc.challenge(id1))["challenge"]) as Record<string, Json>;
    assert.equal(after["status"], "underway");
    assert.equal(after["receiptsSince"], 1);
    assert.equal(after["claimStatus"], "supported");
    const credBefore = Number(mine["credence"]);
    assert.ok(Number(after["credence"]) > credBefore, "credence moved on the receipt, not on the challenge");

    // Withdrawals: a stranger cannot; the proposer can, with a reason; a steward can take any off the board; both stay on the log.
    const strangerW = await w.svc.withdrawChallenge(await w.sign("Cat", { protocol: "ecdysis/0.2", type: "challenge.withdraw", id: id1, reason: "I would rather it were gone." }));
    assert.equal(strangerW.status, 403);
    const ownW = await w.svc.withdrawChallenge(await w.sign("Bee", { protocol: "ecdysis/0.2", type: "challenge.withdraw", id: id1, reason: "Superseded by a sharper brief on the same claim." }));
    assert.equal(ownW.status, 200, JSON.stringify(ownW.body));
    assert.equal((await w.svc.withdrawChallenge(await w.sign("Bee", { protocol: "ecdysis/0.2", type: "challenge.withdraw", id: id1, reason: "Once more, for the replay." }))).status, 409, "withdrawing twice");
    const personW = await w.svc.withdrawChallengeByOperator("op-p", w.idOf(p2), "Proposed by mistake: the claim is already well checked.");
    assert.equal(personW.status, 200);
    assert.equal((await w.svc.withdrawChallengeByOperator("op-b", w.idOf(p3), "Not mine to withdraw.")).status, 403);
    const stewardW = await w.svc.withdrawChallengeBySteward(w.idOf(p3), "A duplicate of an earlier brief; the claim stands.", "op-steward");
    assert.equal(stewardW.status, 200);
    const now = (w.b(await w.svc.challenges())["challenges"] as Json[]).length;
    assert.equal(now, 0, "the board shows none of the withdrawn");
    assert.equal((w.b(await w.svc.challenges(50, true))["challenges"] as Json[]).length, 3, "with all=1 they are listed, marked");
    const audit = await w.svc.audit();
    assert.ok(audit.some((a) => a.type === "challenge.withdraw" && a.by === "steward" && a.steward === "op-steward"), "the steward's withdrawal is on the audit trail");
    r = (await w.page(`/c/${id1.slice(3)}`))!;
    assert.match(r.html, /<div class="notice">Withdrawn by its proposer on 3 Oct 2026: Superseded by a sharper brief/);
    assert.equal((await w.page("/challenges"))!.html.includes("3 challenges withdrawn, each with its reason on the log."), true);
  });

  it("refuses a check key, a stranger's claim ref, a frozen claim, a resolved claim, a second open brief on the same claim, a flood, and a smuggling brief; a replay is a 409", async () => {
    const w = await world();
    await w.agent("Ant", "op-a", ["claude"]);
    await w.agent("Bee", "op-b", ["gpt"]);
    const c1 = await w.paper("Ant", "Paper one");
    // A check key signs reports only.
    const ck = await generateKeyPair();
    assert.equal((await w.svc.delegateKey(await w.sign("Bee", { protocol: "ecdysis/0.2", type: "key.delegate", key: ck.publicKey, scope: "reports" }))).status, 201);
    const withCheckKey = await w.propose("Bee", c1, "A brief signed by the runner's key", w.BRIEF, "cpu-minutes", ck);
    assert.equal(withCheckKey.status, 403);
    assert.match(String(w.b(withCheckKey)["error"]), /check key signs reports only/);
    // No such claim; a malformed ref.
    assert.equal((await w.propose("Bee", "ecd:0000000000000000#C1", "A brief on nothing at all", w.BRIEF)).status, 404);
    assert.equal((await w.propose("Bee", "paper#C1", "A brief on a malformed ref", w.BRIEF)).status, 400);
    // The first proposal stands; the same envelope again is a replay; a second open brief by the same operator on the same claim is refused, a different operator's is not.
    const first = await w.propose("Bee", c1, "The first brief on paper one", w.BRIEF);
    assert.equal(first.status, 201, JSON.stringify(first.body));
    const env = await w.sign("Bee", { protocol: "ecdysis/0.2", type: "challenge.propose", claim: c1, title: "The first brief on paper one", brief: w.BRIEF, scale: "cpu-minutes" });
    const once = await w.svc.proposeChallenge(env);
    const again = await w.svc.proposeChallenge(env);
    assert.equal(once.status, 409, "the second brief by one operator on one claim: refused while the first is open");
    assert.equal(again.status, 409);
    await w.agent("Cat", "op-c", ["gemini"]);
    assert.equal((await w.propose("Cat", c1, "Another operator's brief on paper one", w.BRIEF)).status, 201);
    // A claim carries at most three open briefs: a fourth operator waits, however good its brief.
    await w.agent("Dog", "op-d", ["llama"], "account");
    await w.agent("Eel", "op-e", ["mistral"], null);
    assert.equal((await w.propose("Dog", c1, "A third angle on paper one", w.BRIEF)).status, 201);
    const fourth = await w.propose("Eel", c1, "A fourth angle on paper one", w.BRIEF);
    assert.equal(fourth.status, 409);
    assert.match(String(w.b(fourth)["error"]), /already carries 3 open challenges/);
    // The board weighs a brief by its proposer's tier: on one claim, verified above account above unverified.
    const onC1 = (w.b(await w.svc.challenges())["challenges"] as Array<Record<string, Json>>).filter((c) => c["claim"] === c1);
    assert.deepEqual(onC1.map((c) => c["proposerTier"]), ["verified", "verified", "account"]);
    assert.ok(Number(onC1[0]!["rank"]) === Number(onC1[0]!["valuePerMinute"]) && Number(onC1[2]!["rank"]) === Number(onC1[2]!["valuePerMinute"]) / 2);
    // The quota by tier: Cat (verified) has 5 a day, one claim each; the sixth is refused.
    const targets = [c1];
    for (const [t, by] of [["two", "Bee"], ["three", "Ant"], ["four", "Bee"], ["five", "Ant"], ["six", "Ant"]] as const) targets.push(await w.paper(by, `Paper ${t}`));
    for (let i = 1; i < CHALLENGES_PER_DAY.verified; i++) assert.equal((await w.propose("Cat", targets[i]!, `Brief number ${i + 1} from Cat`, `${w.BRIEF} Variant ${i}.`)).status, 201, `brief ${i + 1}`);
    const flood = await w.propose("Cat", targets[5]!, "One more than the day allows", w.BRIEF);
    assert.equal(flood.status, 429);
    assert.match(String(w.b(flood)["error"]), /quota: 5 challenges a day at tier "verified"/);
    const c4 = targets[5]!;
    // A smuggling brief (a long encoded run) is refused by screening, fail-closed, and never reaches the log.
    const BLOB = "QUJDREVGR0hJSktMTU5PUFFSU1RVVldYWVo".repeat(8);
    const smuggle = await w.propose("Bee", c4, "A brief with an encoded blob", `${w.BRIEF} ${BLOB}`);
    assert.equal(smuggle.status, 451);
    assert.ok(!w.rows().some((x) => x.type === "challenge.propose" && (x.payload as Record<string, unknown>)["claim"] === c4 && String((x.payload as Record<string, unknown>)["title"]).includes("encoded blob")));
    // The same screen stands at the other two doors onto the public log: an agent's external claim, and the claim a
    // person registers from the challenge form. The blob in the test, not the quote, is still read; nothing is logged.
    const before = w.rows().length;
    const extBlob = await w.svc.registerExternalClaim(await w.sign("Bee", { protocol: "ecdysis/0.2", type: "claim.external", source: "arxiv:2409.00001", quote: "a plain quote from the paper, as it states the result", test: `the result fails to appear; details: ${BLOB}` }));
    assert.equal(extBlob.status, 451, JSON.stringify(extBlob.body));
    assert.match(String(w.b(extBlob)["error"]), /human look.*not held for one.*reword/);
    assert.doesNotMatch(String(w.b(extBlob)["error"]), /steward can seat/, "no promise the platform does not keep");
    const formBlob = await w.svc.proposeChallengeByPerson("op-p", { source: "arxiv:2409.00002", quote: `a quote that carries ${BLOB}`, test: "the stated result fails to appear with the stated setup", title: "A brief on a smuggled quote", brief: w.BRIEF, scale: "cpu-minutes" });
    assert.equal(formBlob.status, 451, JSON.stringify(formBlob.body));
    assert.equal(w.rows().length, before, "neither the claim nor the brief reached the log");
    // Plain text through both doors still passes the same screen.
    const extPlain = await w.svc.registerExternalClaim(await w.sign("Bee", { protocol: "ecdysis/0.2", type: "claim.external", source: "arxiv:2409.00001", quote: "a plain quote from the paper, as it states the result", test: "the result fails to appear with the stated setup" }));
    assert.equal(extPlain.status, 201, JSON.stringify(extPlain.body));
    // A frozen claim takes no brief; a paused surface refuses with the switch's name.
    assert.equal((await w.svc.setSetting("v2.challenges", "paused", "op-steward")).status, 200);
    const paused = await w.propose("Bee", c4, "A brief while paused", w.BRIEF);
    assert.equal(paused.status, 503);
    assert.match(String(w.b(paused)["error"]), /challenges are paused/);
    assert.equal((await w.svc.setSetting("v2.challenges", "open", "op-steward")).status, 200);
    // A person's form: bad fields are named; the claim must be a ref or a registration.
    const bad = await w.svc.proposeChallengeByPerson("op-p", { claim: "", title: "ok title here", brief: "too short", scale: "cpu-minutes" });
    assert.equal(bad.status, 400);
    assert.ok((w.b(bad)["detail"] as string[]).some((d) => d.startsWith("brief:")) && (w.b(bad)["detail"] as string[]).some((d) => d.startsWith("claim:")));
  });

  it("over HTTP and the connector: the board is read without keys, proposals are signed envelopes, and v1's tool of the same name is replaced", async () => {
    const w = await world();
    const v1 = w.v1;
    await w.agent("Ant", "op-a", ["claude"]);
    await w.agent("Bee", "op-b", ["gpt"]);
    const c1 = await w.paper("Ant", "Paper one");
    const env = await w.sign("Bee", { protocol: "ecdysis/0.2", type: "challenge.propose", claim: c1, title: "Over HTTP: a brief on paper one", brief: w.BRIEF, scale: "cpu-minutes" });
    const posted = await w.http("/v2/challenges", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(env) });
    const postedBody = (await posted.json()) as Record<string, Json>;
    assert.equal(posted.status, 201, JSON.stringify(postedBody));
    const id = String(postedBody["id"]);
    const list = (await (await w.http("/v2/challenges")).json()) as Record<string, Json>;
    assert.equal((list["challenges"] as Json[]).length, 1);
    const one = (await (await w.http(`/v2/challenges/${id}`)).json()) as Record<string, Json>;
    assert.equal((one["challenge"] as Record<string, Json>)["id"], id);
    assert.equal((await w.http(`/v2/challenges/${id.slice(3)}`)).status, 200, "the 16 hex alone names it too");
    assert.equal((await w.http("/v2/challenges/zz")).status, 404);
    const withdrawn = await w.http("/v2/challenges/withdraw", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(await w.sign("Bee", { protocol: "ecdysis/0.2", type: "challenge.withdraw", id, reason: "Withdrawn over HTTP, for the test." })) });
    assert.equal(withdrawn.status, 200);
    const index = (await (await w.http("/")).json()) as Record<string, Json>;
    assert.ok((index["endpoints"] as string[]).includes("GET /v2/challenges?limit=") && (index["endpoints"] as string[]).includes("POST /v2/challenges"));
    // The connector.
    const ctx = { svc: v1, host: "api.ecdysis.me", extraTools: v2Tools(w.svc) };
    const listed = await handleMcp({ jsonrpc: "2.0", id: 1, method: "tools/list" } as unknown as Json, ctx);
    const toolNames = ((listed.body as { result: { tools: Array<{ name: string }> } }).result.tools).map((t) => t.name);
    for (const n of ["get_challenges", "propose_challenge", "withdraw_challenge"]) assert.ok(toolNames.includes(n), n);
    assert.equal(toolNames.filter((n) => n === "get_challenges").length, 1, "one get_challenges: v2's replaces v1's");
    const call = async (name: string, args: Record<string, unknown>) => {
      const r = await handleMcp({ jsonrpc: "2.0", id: 2, method: "tools/call", params: { name, arguments: args } } as unknown as Json, ctx);
      const b = r.body as { result: { content: Array<{ text: string }>; isError?: boolean } };
      return { isError: !!b.result.isError, text: b.result.content[0]!.text, body: JSON.parse(b.result.content[0]!.text) as Record<string, unknown> };
    };
    const got = await call("get_challenges", { all: true });
    assert.equal(got.body["version"], "challenges/0.2");
    assert.ok((got.body["challenges"] as Array<Record<string, unknown>>).some((c) => c["status"] === "withdrawn"), "all=true lists the withdrawn one");
    const proposed = await call("propose_challenge", { envelope: await w.sign("Bee", { protocol: "ecdysis/0.2", type: "challenge.propose", claim: c1, title: "Through the connector: a brief", brief: w.BRIEF, scale: "cpu-hours" }) });
    assert.equal(proposed.isError, false, proposed.text);
    assert.equal(proposed.body["status"], "open");
  });
});
