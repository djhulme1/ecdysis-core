/**
 * Reserved power R1 in v2: a hold (from screening or an escalation) freezes
 * an item out of every page, queue and number and refuses new reports on
 * it; only the OPERATOR key decides it (never the log key, never a steward's
 * session, never an agent); releasing a paper held at screening publishes it
 * from the envelope it was held with; rejecting leaves the item frozen for
 * good.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { MemoryStore } from "../src/store/memory-store.js";
import { TransparencyLog } from "../src/core/log.js";
import { generateKeyPair, signJson, type KeyPairB64 } from "../src/core/crypto.js";
import { MemoryV2Store, V2Service } from "../src/api/v2/service.js";
import { PagesHandler } from "../src/api/v2/pages.js";
import { contentPage } from "../src/web/steward.js";
import type { Screener } from "../src/core/hazard.js";
import type { Bundle, Outputs } from "../src/core/v2/receipts.js";
import type { Json } from "../src/core/canonical.js";
import { CONSTITUTION_VERSION, constitutionHash } from "../src/core/constitution.js";
const ACK = { version: CONSTITUTION_VERSION, hash: await constitutionHash() };

type R = Record<string, Json>;

/** A screener that asks for a human look at any paper whose title says so. */
const askForHuman: Screener = {
  name: "test-screener",
  async screen(payload) {
    const title = String((payload as unknown as R)["title"] ?? "");
    return title.includes("LOOK") ? [{ screener: "test-screener", severity: 2, category: "test", note: "the title asked for a look" }] : [];
  },
};

async function world(o: { operatorKey?: boolean } = {}) {
  const clock = { t: Date.UTC(2026, 9, 3, 9, 0, 0) };
  const now = () => new Date(clock.t);
  const logStore = new MemoryStore();
  const log = new TransparencyLog(logStore, now);
  const logKey = await generateKeyPair();
  const operatorKey = await generateKeyPair();
  const v2store = new MemoryV2Store(() => (logStore as unknown as { log: Array<{ entry: { seq: number; ts: string; type: string }; payload: Json }> }).log.map((r) => ({ seq: r.entry.seq, ts: r.entry.ts, type: r.entry.type, payload: r.payload })));
  const svc = new V2Service({ log, store: v2store, logPrivateKey: logKey.privateKey, now, screeners: [askForHuman], operatorPublicKey: o.operatorKey === false ? null : operatorKey.publicKey });
  const pages = new PagesHandler(svc, { host: "api.ecdysis.me" });
  // With an operator key configured, the record opens only at genesis: the founder adopts the constitution under R2 first.
  if (o.operatorKey !== false) {
    const ts = now().toISOString().replace(/\.\d{3}Z$/, "Z");
    const adoption = { op: "adopt", version: ACK.version, hash: ACK.hash, ts };
    const r = await svc.adoptConstitution({ version: ACK.version, hash: ACK.hash, ts, signature: await signJson(operatorKey.privateKey, adoption) });
    assert.equal(r.status, 201, JSON.stringify(r.body));
  }
  const keys = new Map<string, KeyPairB64>();
  const agent = async (handle: string, op: string, models?: string[], tier: "account" | "verified" | null = "verified") => {
    const kp = await generateKeyPair();
    keys.set(handle, kp);
    assert.equal((await svc.registerAgent({ constitution: ACK, handle, publicKey: kp.publicKey, operatorId: op, ...(models ? { models } : {}) })).status, 201);
    if (tier) await svc.setTier(op, tier, "op-steward");
    return kp;
  };
  const ts = () => now().toISOString().replace(/\.\d{3}Z$/, "Z");
  const sign = async (handle: string, payload: Record<string, Json>) => {
    const kp = keys.get(handle)!;
    const full: Json = { ...payload, agent: { handle, publicKey: kp.publicKey }, ts: ts() };
    return { payload: full, signature: await signJson(kp.privateKey, full) } as Json;
  };
  const bundle = (n: number): Bundle => ({ repo: "https://github.com/example/rep", commit: n.toString(16).padStart(40, "0"), image: "sha256:" + "a".repeat(64), run: "python run.py", outputs: [{ name: "alpha", tolerance: 0.01 }, { name: "solver" }], runtimeMinutes: 5 });
  const commit = async (handle: string, target: string, b: Bundle) => svc.commitCheck(await sign(handle, { protocol: "ecdysis/0.2", type: "check.commit", target, kind: "replication", bundle: b as unknown as Json }));
  const result = async (handle: string, id: string, outcome: string, outputs: Outputs, cross: { receipt: string; outputs: Outputs } | null) =>
    svc.fileResult(await sign(handle, { protocol: "ecdysis/0.2", type: "check.result", commit: id, outcome, outputs, crossCheck: cross as unknown as Json }));
  const paper = (handle: string, title: string, builds_on: Json[] = []) =>
    sign(handle, { protocol: "ecdysis/0.2", type: "paper", title, abstract: "An abstract long enough to pass the structural screen and say what the paper claims and how it was tested.", field: "math", claims: [{ text: `${title}: the measured quantity lies in the stated interval.`, confidence: 0.7, test: "The quantity lies outside the interval in a fresh run." }], builds_on });
  const review = (handle: string, claim: string) => sign(handle, { protocol: "ecdysis/0.2", type: "review", claim, forecast: 0.6, rationale: "The method is sound and the solver settings match the paper; I expect it to replicate." });
  const escalate = async (handle: string, subject: string) => svc.escalate(await sign(handle, { protocol: "ecdysis/0.2", type: "hazard.escalate", subject, reason: "The quoted claim links to material a person should look at before it spreads further." }));
  /** The owner's decision, signed on the owner's machine with the operator key (here: the test's). */
  const decide = async (subject: string, decision: "release" | "reject", key: KeyPairB64 = operatorKey, at: string = ts()) =>
    svc.decideHazard({ subject, decision, ts: at, signature: await signJson(key.privateKey, { op: "hazard", subject, decision, ts: at }) });
  const page = async (path: string) => { const res = await pages.handle("GET", path, "text/html"); return { status: res?.status ?? 0, html: res ? await res.text() : "" }; };
  const idOf = (r: { body: Json }) => String((r.body as R)["id"]);
  return { svc, pages, agent, sign, bundle, commit, result, paper, review, escalate, decide, page, idOf, logKey, operatorKey, ts, now, tick: (ms: number) => { clock.t += ms; } };
}

describe("reserved power R1 (holds)", () => {
  it("an escalation freezes a claim out of pages, queues, numbers and reports until the operator key releases it", async () => {
    const w = await world();
    await w.agent("Ant", "op-a", ["claude"]);
    await w.agent("Bee", "op-b", ["gpt"]);
    await w.agent("Cat", "op-c", ["gemini"]);
    const p = await w.svc.publishPaper(await w.paper("Ant", "A quiet result"));
    assert.equal(p.status, 201);
    const ref = ((p.body as R)["claims"] as string[])[0]!;
    const paperId = ref.split("#")[0]!;
    // Before: on every page and in the queue, checkable.
    const c1 = await w.commit("Bee", ref, w.bundle(1));
    assert.equal(c1.status, 201);
    await w.result("Bee", w.idOf(c1), "confirmed", { alpha: 1.5, solver: "x" }, null);
    assert.ok(((await w.svc.frontier()).body as R)["checking"] && ((await w.svc.credenceList()).body as R)["claims"]);
    assert.equal((await w.page(`/p/${paperId}/C1`)).status, 200);
    // Cat escalates.
    const esc = await w.escalate("Cat", ref);
    assert.equal(esc.status, 202, JSON.stringify(esc.body));
    let rec = await w.svc.record();
    assert.ok(rec.held.has(ref));
    assert.equal(rec.evidence.filter((e) => e.claim === ref).length, 0, "evidence on a frozen claim counts for nothing while it is frozen");
    const fr = (await w.svc.frontier()).body as R;
    assert.ok(!(fr["checking"] as R[]).some((x) => x["ref"] === ref), "out of the queue");
    assert.ok(!((await w.svc.credenceList()).body as R)["claims"]!.toString().includes(ref), "out of the public numbers");
    assert.equal((await w.page(`/p/${paperId}/C1`)).status, 451, "the page says frozen, shows nothing");
    assert.match((await w.page(`/p/${paperId}/C1`)).html, /Frozen/);
    assert.equal((await w.page(`/p/${paperId}`)).status, 200, "the paper itself is not held, only the claim");
    assert.ok(!(await w.page(`/p/${paperId}`)).html.includes(w.idOf(c1)), "but the frozen claim's receipts are not shown on it");
    assert.equal((await w.svc.receipt(w.idOf(c1))).status, 451, "a receipt on a frozen claim is frozen with it");
    assert.equal((await w.commit("Cat", ref, w.bundle(2))).status, 451, "no new checks");
    assert.equal((await w.svc.fileReview(await w.review("Bee", ref))).status, 451, "no reviews");
    const dep = await w.svc.publishPaper(await w.paper("Bee", "Building on a frozen claim", [{ id: paperId, rel: "extends", basis: "reviewed", claims: ["C1"], note: "Took the interval from this paper after checking the derivation and the solver settings." }]));
    assert.equal(dep.status, 451, "no building on it");
    // Who may decide: not the log key, not a wrong signature, not nobody.
    assert.equal((await w.decide(ref, "release", w.logKey)).status, 401, "the log key cannot stand in for the operator key");
    assert.equal((await w.svc.decideHazard({ subject: ref, decision: "release", ts: w.ts(), signature: "nope" })).status, 401);
    assert.equal((await w.svc.decideHazard({ subject: ref, decision: "release", signature: "nope" })).status, 400, "the signed object carries the time");
    const stale = new Date(w.now().getTime() - 2 * 3600_000).toISOString().replace(/\.\d{3}Z$/, "Z");
    assert.equal((await w.decide(ref, "release", w.operatorKey, stale)).status, 400, "a decision signed two hours ago is not accepted: no replays");
    assert.equal((await w.decide("ecd:nothere#C1", "release")).status, 404);
    const keyless = await world({ operatorKey: false });
    assert.equal((await keyless.decide("anything", "release")).status, 501, "without an operator key, holds stay held");
    // The owner releases: everything is back.
    const rel = await w.decide(ref, "release");
    assert.equal(rel.status, 200, JSON.stringify(rel.body));
    rec = await w.svc.record();
    assert.ok(!rec.held.has(ref));
    assert.equal(rec.evidence.filter((e) => e.claim === ref).length, 1, "the receipt counts again");
    assert.equal((await w.page(`/p/${paperId}/C1`)).status, 200);
    assert.equal((await w.commit("Cat", ref, w.bundle(2))).status, 201);
    assert.equal((await w.decide(ref, "release")).status, 404, "nothing held any more");
  });

  it("rejecting a hold leaves the item frozen for good; a later release can still lift it", async () => {
    const w = await world();
    await w.agent("Ant", "op-a", ["claude"]);
    await w.agent("Cat", "op-c", ["gemini"]);
    const p = await w.svc.publishPaper(await w.paper("Ant", "Another quiet result"));
    const ref = ((p.body as R)["claims"] as string[])[0]!;
    assert.equal((await w.escalate("Cat", ref)).status, 202);
    assert.equal((await w.decide(ref, "reject")).status, 200);
    const rec = await w.svc.record();
    assert.ok(rec.held.has(ref), "rejected: still frozen");
    const holds = await w.svc.holds();
    assert.equal(holds.filter((h) => h.type === "hazard.hold" && h.subject === ref)[0]!.open, false, "but the hold is decided, not open");
    assert.equal((await w.commit("Cat", ref, w.bundle(1))).status, 451);
    assert.equal((await w.decide(ref, "release")).status, 200, "the owner can still change the decision");
    assert.ok(!(await w.svc.record()).held.has(ref));
  });

  it("a paper held at screening is published by the operator key's release, from the envelope it was held with, and never by anything else", async () => {
    const w = await world();
    await w.agent("Ant", "op-a", ["claude"]);
    const held = await w.svc.publishPaper(await w.paper("Ant", "Please LOOK at this one"));
    assert.equal(held.status, 202, JSON.stringify(held.body));
    const cid = String((held.body as R)["id"]);
    let rec = await w.svc.record();
    assert.ok(rec.held.has(cid));
    assert.equal(rec.papers.size, 0, "nothing published");
    assert.equal((await w.page("/papers")).html.includes("LOOK"), false, "nothing shown");
    assert.ok((await w.svc.holds()).some((h) => h.subject === cid && h.open));
    // A steward's session has no release; neither has an agent. Only the operator key's signature over the decision does.
    assert.equal((await w.decide(cid, "release", w.logKey)).status, 401);
    const rel = await w.decide(cid, "release");
    assert.equal(rel.status, 200, JSON.stringify(rel.body));
    assert.equal((rel.body as R)["published"], true);
    rec = await w.svc.record();
    assert.equal(rec.papers.size, 1);
    const id = `ecd:${cid.slice(0, 16)}`;
    assert.ok(rec.papers.has(id));
    assert.equal((await w.page(`/p/${id}`)).status, 200);
    assert.match((await w.page(`/p/${id}`)).html, /LOOK at this one/);
    assert.equal((await w.decide(cid, "release")).status, 404, "decided");
    // Rejected at screening: never published, and the envelope is not reachable as a paper.
    const held2 = await w.svc.publishPaper(await w.paper("Ant", "LOOK again"));
    const cid2 = String((held2.body as R)["id"]);
    assert.equal((await w.decide(cid2, "reject")).status, 200);
    assert.equal((await w.svc.record()).papers.size, 1);
    assert.equal((await w.page(`/p/ecd:${cid2.slice(0, 16)}`)).status, 404);
  });

  // 4 October 2026, Daniel: "I won't remember not to do things." A submission he has rejected must stay rejected, whatever
  // he signs later.
  it("a submission rejected at screening is rejected for good: a later release, signed by mistake, is refused and publishes nothing", async () => {
    const w = await world();
    await w.agent("Ant", "op-a", ["claude"]);
    const held = await w.svc.publishPaper(await w.paper("Ant", "A critique to LOOK at before it goes out"));
    assert.equal(held.status, 202, JSON.stringify(held.body));
    const cid = String((held.body as R)["id"]);
    assert.equal((await w.decide(cid, "reject")).status, 200);
    w.tick(90 * 24 * 3600_000);   // months on, the owner has forgotten
    const later = await w.decide(cid, "release");
    assert.equal(later.status, 409, JSON.stringify(later.body));
    assert.match(JSON.stringify(later.body), /rejected under R1 for good/);
    assert.equal((await w.decide(cid, "reject")).status, 409, "nor is it decided twice");
    const rec = await w.svc.record();
    assert.equal(rec.papers.size, 0, "nothing published");
    assert.ok(rec.held.has(cid) && rec.rejectedForGood.has(cid));
    assert.equal((await w.page(`/p/ecd:${cid.slice(0, 16)}`)).status, 404);
    const rows = await w.svc.holds();
    assert.equal(rows.find((h) => h.type === "hazard.hold" && h.subject === cid)!.state, "rejected for good");
    assert.equal(rows.filter((h) => h.type === "hazard.release").length, 1, "the refused release never reached the log");
    assert.match(contentPage({ holds: rows }, null, null), /<td>rejected for good<\/td>/, "the stewards' page says so");
    // Its author fixes it and submits it again: a new submission, screened again, and the owner's to decide afresh.
    const again = await w.svc.publishPaper(await w.paper("Ant", "A corrected critique to LOOK at"));
    assert.equal(again.status, 202);
    const cid2 = String((again.body as R)["id"]);
    assert.notEqual(cid2, cid);
    const rel = await w.decide(cid2, "release");
    assert.equal(rel.status, 200, JSON.stringify(rel.body));
    assert.equal((rel.body as R)["published"], true);
    assert.ok((await w.svc.record()).papers.has(`ecd:${cid2.slice(0, 16)}`));
  });

  it("adversarial: a release written to the log after a rejection, by any means, lifts nothing and publishes nothing", async () => {
    const w = await world();
    await w.agent("Ant", "op-a", ["claude"]);
    const held = await w.svc.publishPaper(await w.paper("Ant", "Another one to LOOK at"));
    const cid = String((held.body as R)["id"]);
    assert.equal((await w.decide(cid, "reject")).status, 200);
    // As if an older server, a replayed request or a direct write appended a release after the rejection.
    await (w.svc as unknown as { o: { log: { append: (t: string, p: Json) => Promise<unknown> } } }).o.log.append("hazard.release", { subject: cid, decision: "release" });
    const rec = await w.svc.record();
    assert.ok(rec.held.has(cid), "still out of view");
    assert.ok(rec.rejectedForGood.has(cid));
    assert.equal(rec.papers.size, 0);
    assert.equal((await w.decide(cid, "release")).status, 409);
    // An escalation is not a submission: rejecting one still leaves it the owner's to release (the test above).
    await w.agent("Cat", "op-c", ["gemini"]);
    const p = await w.svc.publishPaper(await w.paper("Ant", "A quiet result on the record"));
    const ref = ((p.body as R)["claims"] as string[])[0]!;
    assert.equal((await w.escalate("Cat", ref)).status, 202);
    assert.equal((await w.decide(ref, "reject")).status, 200);
    assert.ok(!(await w.svc.record()).rejectedForGood.has(ref));
    assert.equal((await w.svc.holds()).find((h) => h.type === "hazard.hold" && h.subject === ref)!.state, "rejected");
  });
});
