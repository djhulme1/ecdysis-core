/**
 * Amendments under Article V (v2): anyone proposes; only operators with
 * verified work vote; one operator one vote; two thirds and a fifth; the
 * window closes the tally; entrenched articles need the operator key (R2),
 * which the archive's own log key can never stand in for.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { MemoryStore } from "../src/store/memory-store.js";
import { TransparencyLog } from "../src/core/log.js";
import { generateKeyPair, signJson, type KeyPairB64 } from "../src/core/crypto.js";
import { MemoryV2Store, V2Service } from "../src/api/v2/service.js";
import { V2Governance } from "../src/api/v2/governance.js";
import { CONSTITUTION_VERSION, constitutionHash, REVIEW_WINDOW_DAYS } from "../src/core/constitution.js";
import type { Bundle, Outputs } from "../src/core/v2/receipts.js";
import type { Json } from "../src/core/canonical.js";

const ACK = { version: CONSTITUTION_VERSION, hash: await constitutionHash() };
const DAY = 24 * 3600 * 1000;

async function world() {
  const clock = { t: Date.UTC(2026, 9, 3, 9, 0, 0) };
  const now = () => new Date(clock.t);
  const logStore = new MemoryStore();
  const log = new TransparencyLog(logStore, now);
  const logKey = await generateKeyPair();
  const operatorKey = await generateKeyPair();
  const v2store = new MemoryV2Store(() => (logStore as unknown as { log: Array<{ entry: { seq: number; ts: string; type: string }; payload: Json }> }).log.map((r) => ({ seq: r.entry.seq, ts: r.entry.ts, type: r.entry.type, payload: r.payload })));
  const svc = new V2Service({ log, store: v2store, logPrivateKey: logKey.privateKey, now });
  const gov = new V2Governance({ v2: svc, log, operatorPublicKey: operatorKey.publicKey, now });
  const keys = new Map<string, KeyPairB64>();
  const agent = async (handle: string, op: string, models?: string[], tier: "account" | "verified" | null = "verified") => {
    const kp = await generateKeyPair();
    keys.set(handle, kp);
    assert.equal((await svc.registerAgent({ handle, publicKey: kp.publicKey, operatorId: op, constitution: ACK, ...(models ? { models } : {}) })).status, 201);
    if (tier) await svc.setTier(op, tier);
    return kp;
  };
  const ts = () => now().toISOString().replace(/\.\d{3}Z$/, "Z");
  const sign = async (handle: string, payload: Record<string, Json>) => {
    const kp = keys.get(handle)!;
    const full: Json = { ...payload, agent: { handle, publicKey: kp.publicKey }, ts: ts() };
    return { payload: full, signature: await signJson(kp.privateKey, full) } as Json;
  };
  const bundle = (n: number): Bundle => ({ repo: "https://github.com/example/rep", commit: n.toString(16).padStart(40, "0"), image: "sha256:" + "a".repeat(64), run: "python run.py", outputs: [{ name: "alpha", tolerance: 0.01 }], runtimeMinutes: 5 });
  const commit = async (handle: string, target: string, b: Bundle) => svc.commitCheck(await sign(handle, { protocol: "ecdysis/0.2", type: "check.commit", target, kind: "replication", bundle: b as unknown as Json }));
  const result = async (handle: string, id: string, outcome: string, outputs: Outputs, cross: { receipt: string; outputs: Outputs } | null) =>
    svc.fileResult(await sign(handle, { protocol: "ecdysis/0.2", type: "check.result", commit: id, outcome, outputs, crossCheck: cross as unknown as Json }));
  const propose = async (handle: string, articleId: string, change: string) => gov.propose(await sign(handle, { protocol: "ecdysis/0.2", type: "governance.proposal", articleId, change }));
  const vote = async (handle: string, proposal: string, choice: "yes" | "no") => gov.vote(await sign(handle, { protocol: "ecdysis/0.2", type: "governance.vote", proposal, choice }));
  const idOf = (r: { body: Json }) => String((r.body as Record<string, Json>)["id"]);
  /** A paper by `handle` with one claim stated at 0.9; returns the claim ref. */
  const paper = async (handle: string, title: string) => {
    const r = await svc.publishPaper(await sign(handle, { protocol: "ecdysis/0.2", type: "paper", title, abstract: "An abstract long enough to pass the structural screen, saying what was measured, how, and with what uncertainty, for the record.", field: "math", claims: [{ text: `${title}: the measured quantity lies in the stated interval.`, confidence: 0.9, test: "The quantity lies outside the interval in a fresh run." }], builds_on: [] }));
    assert.equal(r.status, 201, JSON.stringify(r.body));
    return String(((r.body as Record<string, Json>)["claims"] as string[])[0]);
  };
  /**
   * Verified work, two deterministic ways. A RECEIPT survives a cross-check
   * when it is the only earlier receipt of its claim and someone else checks
   * next (the draw has one candidate). A CLAIM reaches established when two
   * verified operators on different model families replicate it.
   */
  const receiptWork = async (handle: string, checker: string, ref: string, n: number) => {
    const c = await commit(handle, ref, bundle(n));
    assert.equal(c.status, 201, JSON.stringify(c.body));
    assert.equal((c.body as Record<string, Json>)["crossCheck"], null, "the first receipt of the claim: nothing to cross-check");
    assert.equal((await result(handle, idOf(c), "confirmed", { alpha: 1 + n }, null)).status, 201);
    const c2 = await commit(checker, ref, bundle(100 + n));
    const cross = (c2.body as Record<string, Json>)["crossCheck"] as Record<string, Json>;
    assert.equal(cross["receipt"], idOf(c));
    assert.equal((await result(checker, idOf(c2), "confirmed", { alpha: 1 + n }, { receipt: idOf(c), outputs: (await v2store.getOutputs(idOf(c)))! })).status, 201);
    return idOf(c);
  };
  const claimWork = async (handle: string, replicators: [string, string], n: number) => {
    const ref = await paper(handle, `Result ${n} by ${handle}`);
    const c1 = await commit(replicators[0], ref, bundle(200 + n));
    assert.equal((await result(replicators[0], idOf(c1), "confirmed", { alpha: n }, null)).status, 201);
    const c2 = await commit(replicators[1], ref, bundle(300 + n));
    assert.equal((await result(replicators[1], idOf(c2), "confirmed", { alpha: n }, { receipt: idOf(c1), outputs: { alpha: n } })).status, 201);
    assert.equal((await svc.scores()).claims.get(ref)!.status, "established", "two verified replications on two families");
    return ref;
  };
  return { svc, gov, agent, sign, commit, result, propose, vote, idOf, receiptWork, claimWork, keys, operatorKey, logKey, tick: (ms: number) => { clock.t += ms; }, now, v2store };
}

describe("amendments (Article V, v2)", () => {
  it("anyone proposes; only operators with verified work vote; one operator one vote; quorum and supermajority; the window closes the tally", async () => {
    const w = await world();
    await w.agent("Ant", "op-a", ["claude"]);
    await w.agent("Bee", "op-b", ["gpt"]);
    await w.agent("Cat", "op-c", ["gemini"]);
    await w.agent("New", "op-n", ["grok"], null);
    const ext = await w.svc.registerExternalClaim(await w.sign("Ant", { protocol: "ecdysis/0.2", type: "claim.external", source: "arxiv:1706.03762", quote: "attention alone reaches 28.4 BLEU on WMT14 En-De", test: "BLEU below 27 with the stated setup" }));
    const ref = String((ext.body as Record<string, Json>)["ref"]);
    // Nobody has verified work yet: a proposal is open to all, a vote to none.
    const p = await w.propose("New", "III", "Extend the result deadline from seven to ten days: bundles on CPU-only machines often need the extra time, and lapses for want of compute teach nothing.");
    assert.equal(p.status, 201, JSON.stringify(p.body));
    const pid = w.idOf(p);
    assert.equal((p.body as Record<string, Json>)["entrenched"], false);
    assert.equal((await w.vote("Ant", pid, "yes")).status, 403, "no verified work, no vote");
    assert.equal((await w.propose("New", "IX", "There is no Article IX, so this proposal must be refused for its article id alone.")).status, 400);
    // One open proposal per operator: every proposal costs every reader of /v2/governance a tally, so a flood is refused.
    const second = await w.propose("New", "IV", "A second proposal from the same operator while the first is still open; it must wait for that window to close.");
    assert.equal(second.status, 429, JSON.stringify(second.body));
    assert.deepEqual((second.body as Record<string, Json>)["open"], [pid]);
    // Bee's receipt is cross-checked by Cat: Bee has verified work; Cat's receipt is then cross-checked by Ant: Cat has too.
    await w.receiptWork("Bee", "Cat", ref, 1);
    let el = await w.gov.electorate(w.now());
    assert.ok(el.has("op-b"), "a receipt that survived a cross-check");
    assert.ok(!el.has("op-c"), "the checker's own receipt has not been checked");
    await w.claimWork("Cat", ["Ant", "Bee"], 2);
    el = await w.gov.electorate(w.now());
    assert.ok(el.has("op-c"), "a claim that reached established");
    assert.ok(!el.has("op-n"));
    const eligible = el.size;
    // Votes: Bee yes, Cat no → 1 of 2: no supermajority. Cat changes its mind: the latest vote stands.
    assert.equal((await w.vote("Bee", pid, "yes")).status, 200);
    assert.equal((await w.vote("New", pid, "yes")).status, 403, "unverified operators still cannot vote");
    let st = (await w.vote("Cat", pid, "no")).body as Record<string, Json>;
    assert.equal(st["open"], true);
    assert.equal(st["passed"], false);
    assert.match(String(st["reason"]), /supermajority not met/);
    st = (await w.vote("Cat", pid, "yes")).body as Record<string, Json>;
    assert.equal(st["yesOperators"], 2);
    assert.equal(st["noOperators"], 0);
    assert.equal(st["passed"], false, "open: not passed until the window closes");
    assert.match(String(st["reason"]), /voting is open/);
    // The same signed vote twice is refused; a fresh one is fine.
    w.tick(1000);
    const env = await w.sign("Bee", { protocol: "ecdysis/0.2", type: "governance.vote", proposal: pid, choice: "yes" });
    assert.equal((await w.gov.vote(env)).status, 200);
    assert.equal((await w.gov.vote(env)).status, 409);
    // The window closes: the tally is final over the electorate as it stood then.
    w.tick(REVIEW_WINDOW_DAYS * DAY + 1000);
    assert.equal((await w.vote("Bee", pid, "no")).status, 409, "closed");
    st = (await w.gov.status(pid)).body as Record<string, Json>;
    assert.equal(st["open"], false);
    assert.equal(st["passed"], true);
    assert.equal(st["reason"], "adopted");
    assert.equal(st["eligibleOperators"], eligible, "the electorate as it stood when the window closed");
    const summary = (await w.gov.summary()).body as Record<string, Json>;
    assert.equal((summary["proposals"] as unknown[]).length, 1);
    assert.equal(summary["eligibleOperators"], eligible);
  });

  it("an entrenched article needs the operator key's co-signature, and the archive's own log key cannot stand in for it", async () => {
    const w = await world();
    await w.agent("Ant", "op-a", ["claude"]);
    await w.agent("Bee", "op-b", ["gpt"]);
    await w.agent("Cat", "op-c", ["gemini"]);
    const ext = await w.svc.registerExternalClaim(await w.sign("Ant", { protocol: "ecdysis/0.2", type: "claim.external", source: "arxiv:1706.03762", quote: "attention alone reaches 28.4 BLEU on WMT14 En-De", test: "BLEU below 27 with the stated setup" }));
    const ref = String((ext.body as Record<string, Json>)["ref"]);
    await w.receiptWork("Bee", "Cat", ref, 1);
    await w.claimWork("Cat", ["Ant", "Bee"], 2);
    const p = await w.propose("Ant", "0", "Amend 0.5 so that two agents of one operator count as two voices when they run on different model families; the diversity discount already handles the rest.");
    assert.equal(p.status, 201);
    const pid = w.idOf(p);
    assert.equal((p.body as Record<string, Json>)["entrenched"], true);
    await w.vote("Bee", pid, "yes");
    await w.vote("Cat", pid, "yes");
    w.tick(REVIEW_WINDOW_DAYS * DAY + 1000);
    let st = (await w.gov.status(pid)).body as Record<string, Json>;
    assert.equal(st["passed"], false);
    assert.match(String(st["reason"]), /R2 co-signature missing/);
    // The log key signs a co-signature: refused. Only the operator key counts.
    const forged = await signJson(w.logKey.privateKey, { op: "cosign", proposal: pid });
    assert.equal((await w.gov.cosign({ proposal: pid, signature: forged })).status, 401);
    // The operator key, on the owner's machine, signs {op: "cosign", proposal}: the amendment passes.
    const sig = await signJson(w.operatorKey.privateKey, { op: "cosign", proposal: pid });
    const co = await w.gov.cosign({ proposal: pid, signature: sig });
    assert.equal(co.status, 200, JSON.stringify(co.body));
    st = co.body as Record<string, Json>;
    assert.equal(st["cosigned"], true);
    assert.equal(st["passed"], true);
    assert.equal((await w.gov.cosign({ proposal: pid, signature: sig })).status, 409, "once");
    // An ordinary article never takes a co-signature.
    const q = await w.propose("Ant", "IV", "Standing should also reward a review whose forecast was right, in proportion to how much it moved credence towards the truth.");
    assert.equal((await w.gov.cosign({ proposal: w.idOf(q), signature: await signJson(w.operatorKey.privateKey, { op: "cosign", proposal: w.idOf(q) }) })).status, 409);
    // Without an operator key configured, nothing entrenched can pass.
    const noKey = new V2Governance({ v2: w.svc, log: (w.svc as unknown as { o: { log: TransparencyLog } }).o.log, operatorPublicKey: null, now: w.now });
    assert.equal((await noKey.cosign({ proposal: pid, signature: sig })).status, 501);
  });
});
