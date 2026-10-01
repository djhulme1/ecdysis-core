/**
 * jury/0.3: practice reviews, apprentice seats, seat deadlines and redraws.
 *
 * Guarantees:
 *  - practice cases are generated with answers that are actually right
 *    (exact values recomputed independently), and scoring needs the flaw
 *    named, so guessing cannot qualify;
 *  - qualification needs both kinds of case, is logged, and has limits;
 *  - an apprentice sits only beside two experienced jurors, at most one
 *    per panel, however many apprentices a sybil operator farm produces;
 *  - a seat lapses 48 hours after seating without a vote: the juror sits
 *    out 72 hours, the seat is redrawn deterministically, and every change
 *    is logged; votes already cast can then decide a smaller panel;
 *  - thin panels are topped up as the pool grows; genesis-era cases with no
 *    jurors are left to the genesis rule.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { EcdysisService } from "../src/api/service.js";
import { MemoryStore } from "../src/store/memory-store.js";
import { generateKeyPair, signJson, type KeyPairB64 } from "../src/core/crypto.js";
import { CONSTITUTION_VERSION, constitutionHash } from "../src/core/constitution.js";
import { structuralScreener } from "../src/core/hazard.js";
import {
  exactStreakExpectation, generatePracticeCase, practiceProgress, scorePractice, type PracticeAnswer,
} from "../src/core/practice.js";
import { drawReplacements, selectJuryFielded, JURY_VERSION, LAPSE_PENALTY_MS, SEAT_DEADLINE_MS } from "../src/core/jury.js";
import type { Json } from "../src/core/canonical.js";

/** Deterministic PRNG for tests (mulberry32). */
function prng(seed: number) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const iso = (ms: number) => new Date(ms).toISOString().replace(/\.\d{3}Z$/, "Z");

async function setup(seed = 7) {
  const store = new MemoryStore();
  const clock = { t: Date.UTC(2026, 9, 1, 12, 0, 0) };
  const svc = new EcdysisService({
    store, screeners: [structuralScreener()], sthPrivateKey: null,
    now: () => new Date(clock.t), random: prng(seed),
  });
  const ack = { version: CONSTITUTION_VERSION, hash: await constitutionHash() };
  const keys = new Map<string, KeyPairB64>();
  const add = async (handle: string, op: string, accepted = 0) => {
    const kp = await generateKeyPair();
    const r = await svc.registerAgent({ handle, publicKey: kp.publicKey, operatorId: op, constitution: ack });
    assert.equal(r.status, 201, JSON.stringify(r.body));
    for (let i = 0; i < accepted; i++) await store.bumpAccepted(handle);
    keys.set(handle, kp);
    return kp;
  };
  return { store, svc, clock, add, keys };
}

async function signed(kp: KeyPairB64, payload: Json) {
  return { payload, signature: await signJson(kp.privateKey, payload) } as Json;
}

async function submitPaper(svc: EcdysisService, kp: KeyPairB64, handle: string, ts: string, title = "A small replication with seeds attached") {
  const payload: Json = {
    protocol: "ecdysis/0.1", type: "paper", title,
    abstract: "We re-run a published analysis at small scale and report the outcome with seeds attached.",
    field: "ml", claims: [{ text: "The effect replicates at small scale.", confidence: 0.6 }],
    builds_on: [{ id: "arxiv:1706.03762", rel: "replicates" }],
    agent: { handle, publicKey: kp.publicKey }, ts,
  };
  const r = await svc.submitPaper(await signed(kp, payload));
  assert.equal(r.status, 202, JSON.stringify(r.body));
  return (r.body as { id: string }).id;
}

describe("practice cases", () => {
  it("the exact streak expectation matches known values", () => {
    assert.ok(Math.abs(exactStreakExpectation(3, 0.5, 1) - 5 / 12) < 1e-12);
    assert.ok(Math.abs(exactStreakExpectation(4, 0.5, 1) - 17 / 42) < 1e-12);
    assert.equal(exactStreakExpectation(100, 0.5, 3).toFixed(4), "0.4603");
  });

  it("generated answers are right: flawed values are off by at least 0.03, sound ones exact", () => {
    const rand = prng(42);
    let flawed = 0, sound = 0;
    for (let i = 0; i < 64; i++) {
      const c = generatePracticeCase(i, rand, { soundSoFar: sound, flawedSoFar: flawed });
      c.answer.verdict === "publish" ? sound++ : flawed++;
      if (c.family !== "streak") continue;
      for (const [j, claim] of c.paper.claims.slice(0, 3).entries()) {
        const m = claim.text.match(/Bernoulli\(([\d.]+)\) sequences of length (\d+).*?after (\d+) consecutive.*? is ([\d.]+) \(exact\)/);
        assert.ok(m, claim.text);
        const exact = exactStreakExpectation(Number(m![2]), Number(m![1]), Number(m![3]));
        const shown = Number(m![4]);
        if (c.answer.flaws.includes(`C${j + 1}`)) assert.ok(Math.abs(shown - exact) >= 0.029, "a planted error is visible");
        else assert.ok(Math.abs(shown - exact) < 1e-4, "an honest value is exact to 4 dp");
      }
    }
    assert.ok(sound > 10 && flawed > 10, "both kinds are common");
  });

  it("scoring needs the right verdict and, for flawed cases, the flaw named", () => {
    const flawed: PracticeAnswer = { verdict: "reject", flaws: ["C2"], explanation: "" };
    const sound: PracticeAnswer = { verdict: "publish", flaws: [], explanation: "" };
    assert.equal(scorePractice(flawed, "reject", ["c2"]), true);
    assert.equal(scorePractice(flawed, "reject", ["C2", "relation"]), true, "one extra label tolerated");
    assert.equal(scorePractice(flawed, "reject", ["C1", "C2", "C3"]), false, "a scattergun is not an answer");
    assert.equal(scorePractice(flawed, "reject", ["C1"]), false);
    assert.equal(scorePractice(flawed, "publish", []), false);
    assert.equal(scorePractice(sound, "publish", []), true);
    assert.equal(scorePractice(sound, "reject", ["C1"]), false);
  });

  it("qualification needs five right at 80%, two flawed and one sound", () => {
    const row = (correct: boolean, verdict: string) => ({ correct, answer: { verdict } });
    assert.equal(practiceProgress([row(true, "reject"), row(true, "reject"), row(true, "reject"), row(true, "reject"), row(true, "reject")]).qualified, false, "no sound case");
    assert.equal(practiceProgress([row(true, "reject"), row(true, "reject"), row(true, "publish"), row(true, "publish"), row(true, "reject")]).qualified, true);
    assert.equal(practiceProgress([row(true, "reject"), row(true, "reject"), row(true, "publish"), row(true, "publish"), row(true, "reject"), row(false, "reject"), row(false, "publish")]).qualified, false, "accuracy 5/7 < 80%");
  });
});

describe("volunteering through practice", () => {
  it("an agent with no accepted work qualifies by answering correctly, and the qualification is logged", async () => {
    const { svc, store, add } = await setup();
    const kp = await add("Volunteer-1", "op-vol");
    let qualified = false;
    for (let i = 0; i < 12 && !qualified; i++) {
      const req = await svc.practiceCase(await signed(kp, { protocol: "ecdysis/0.1", type: "practice.request", agent: { handle: "Volunteer-1", publicKey: kp.publicKey }, ts: iso(Date.UTC(2026, 9, 1, 12, 0, 0)) }));
      assert.equal(req.status, 200, JSON.stringify(req.body));
      const c = req.body as Record<string, any>;
      // Answer correctly using the server-held key (a test-only peek).
      const rec = (await store.getPractice(c.caseId))!;
      const exp = rec.answer as unknown as PracticeAnswer;
      const ans = await svc.practiceAnswer(await signed(kp, {
        protocol: "ecdysis/0.1", type: "practice.answer", caseId: c.caseId, verdict: exp.verdict, flaws: exp.flaws,
        rationale: "Recomputed the values and checked each relation against the parent paper.",
        agent: { handle: "Volunteer-1", publicKey: kp.publicKey }, ts: iso(Date.UTC(2026, 9, 1, 12, 0, 0)),
      }));
      assert.equal(ans.status, 200, JSON.stringify(ans.body));
      assert.equal((ans.body as Record<string, any>).correct, true);
      qualified = !!(ans.body as Record<string, any>).qualified;
    }
    assert.ok(qualified, "qualified within 12 cases");
    const events = await store.allEvents();
    assert.ok(events.some((e) => e.type === "juror.qualify"), "the qualification is on the log");
    assert.ok((await store.getAgent("Volunteer-1"))!.practiceQualifiedAt);
    const hb = (await svc.heartbeat("Volunteer-1")).body as Record<string, any>;
    assert.equal(hb.juror.kind, "practice-qualified");
  });

  it("one open case at a time, owners only, no second answers, and daily limits", async () => {
    const { svc, add, clock } = await setup();
    const kp = await add("Volunteer-2", "op-vol2");
    const other = await add("Other-2", "op-other2");
    const reqFor = async (k: KeyPairB64, h: string) => svc.practiceCase(await signed(k, { protocol: "ecdysis/0.1", type: "practice.request", agent: { handle: h, publicKey: k.publicKey }, ts: iso(clock.t) }));
    const a = (await reqFor(kp, "Volunteer-2")).body as Record<string, any>;
    const again = (await reqFor(kp, "Volunteer-2")).body as Record<string, any>;
    assert.equal(again.caseId, a.caseId, "the open case is returned again");
    const answer = async (k: KeyPairB64, h: string, id: string) => svc.practiceAnswer(await signed(k, {
      protocol: "ecdysis/0.1", type: "practice.answer", caseId: id, verdict: "publish", flaws: [],
      rationale: "Looked at it carefully and found nothing wrong with it at all.", agent: { handle: h, publicKey: k.publicKey }, ts: iso(clock.t),
    }));
    assert.equal((await answer(other, "Other-2", a.caseId)).status, 404, "not yours");
    assert.equal((await answer(kp, "Volunteer-2", a.caseId)).status, 200);
    assert.equal((await answer(kp, "Volunteer-2", a.caseId)).status, 409, "no second answers");
    for (let i = 0; i < 11; i++) {
      const c = (await reqFor(kp, "Volunteer-2")).body as Record<string, any>;
      await answer(kp, "Volunteer-2", c.caseId);
    }
    assert.equal((await reqFor(kp, "Volunteer-2")).status, 429, "12 a day");
    clock.t += 25 * 3600 * 1000;
    assert.equal((await reqFor(kp, "Volunteer-2")).status, 200, "tomorrow is another day");
  });
});

describe("apprentice seats", () => {
  const cand = (handle: string, op: string, accepted: number, apprentice = false) =>
    ({ handle, operatorId: op, standing: 0, acceptedCount: accepted, fieldCompetent: false, apprentice });
  const never = () => false;

  it("an apprentice sits only beside two experienced jurors, and never more than one", async () => {
    const vets1 = [cand("V1", "op-v1", 1)];
    const appr = Array.from({ length: 10 }, (_, i) => cand(`A${i}`, `op-a${i}`, 0, true));
    const thin = await selectJuryFielded("ab".repeat(32), [...vets1, ...appr], "op-author", never);
    assert.deepEqual(thin.jurors, ["V1"], "one experienced juror: no apprentice");
    const vets = [cand("V1", "op-v1", 1), cand("V2", "op-v2", 1)];
    for (const seed of ["ab", "cd", "ef", "01"]) {
      const sel = await selectJuryFielded(seed.repeat(32), [...vets, ...appr], "op-author", never);
      assert.equal(sel.apprentices.length, 1, "a sybil farm of ten apprentices still gets one seat");
      assert.equal(sel.jurors.length, 3);
      assert.equal(sel.juryVersion, JURY_VERSION);
    }
    const ownOp = await selectJuryFielded("ab".repeat(32), [...vets, cand("A-own", "op-author", 0, true)], "op-author", never);
    assert.equal(ownOp.apprentices.length, 0, "never the author's own operator");
  });

  it("replacement draws are deterministic and respect the apprentice rule", async () => {
    const pool = [cand("V1", "op-v1", 1), cand("V2", "op-v2", 1), cand("V3", "op-v3", 1), cand("A1", "op-a1", 0, true)];
    const o = { submitterOperator: "op-x", seatedOperators: new Set(["op-v1"]), count: 2, experiencedSeated: 1, apprenticeSeated: false };
    const a = await drawReplacements("ab".repeat(32), 1, pool, o);
    const b = await drawReplacements("ab".repeat(32), 1, pool, o);
    assert.deepEqual(a, b);
    assert.ok(a.every((d) => !d.apprentice), "two experienced replacements available, so no apprentice needed");
    const c = await drawReplacements("ab".repeat(32), 1, pool.filter((x) => x.handle !== "V3"), o);
    assert.deepEqual(c.map((d) => [d.handle, d.apprentice]), [["V2", false], ["A1", true]], "with two experienced seated, the last seat may go to an apprentice");
  });
});

describe("seat deadlines (Article III.4)", () => {
  it("a lapsed seat is redrawn, logged, and the juror sits out; votes cast still count", async () => {
    const { svc, store, add, clock } = await setup();
    const author = await add("Author-1", "op-author");
    await add("V1", "op-v1", 1);
    await add("V2", "op-v2", 1);
    const id = await submitPaper(svc, author, "Author-1", iso(clock.t));
    const before = (await store.getQuarantine(id))!;
    assert.equal(before.jury.length, 2);
    assert.equal((await svc.enforceDeadlines()).cases, 0, "nothing lapses early");

    await add("V3", "op-v3", 1); // the pool grows while the case waits
    clock.t += SEAT_DEADLINE_MS + 60_000;
    const r = await svc.enforceDeadlines();
    assert.equal(r.lapsed, 2);
    const after = (await store.getQuarantine(id))!;
    assert.ok(after.jury.includes("V3"), "the new juror is seated");
    assert.ok(!after.jury.includes(before.jury[0]!), "the lapsed jurors are gone");
    for (const h of before.jury) {
      const a = (await store.getAgent(h))!;
      assert.equal(a.ineligibleUntil, new Date(clock.t + LAPSE_PENALTY_MS).toISOString());
    }
    const log = await store.allEvents?.();
    if (log) assert.ok(log.some((e: { type: string }) => e.type === "jury.redraw"), "the redraw is logged");
    const hb = (await svc.heartbeat(before.jury[0]!)).body as Record<string, any>;
    assert.equal(hb.juror.status, "sitting out");
  });

  it("when the remaining votes decide a smaller panel, the case is decided", async () => {
    const { svc, store, add, clock, keys } = await setup();
    const author = await add("Author-2", "op-author2");
    await add("V1", "op-v1", 1);
    await add("V2", "op-v2", 1);
    const id = await submitPaper(svc, author, "Author-2", iso(clock.t));
    const q = (await store.getQuarantine(id))!;
    const voter = q.jury[0]!;
    const kp = keys.get(voter)!;
    const rv = await svc.fileReview(await signed(kp, {
      protocol: "ecdysis/0.1", type: "review", subject: id, verdict: "publish",
      rationale: "Method and evidence support the claims; seeds and settings are stated.", agent: { handle: voter, publicKey: kp.publicKey }, ts: iso(clock.t),
    }));
    assert.equal(rv.status, 202, "two jurors: one vote waits for the other");
    clock.t += SEAT_DEADLINE_MS + 60_000;
    const r = await svc.enforceDeadlines();
    assert.equal(r.decided, 1, "the silent juror lapsed, nobody else is eligible, and the cast vote decides");
    assert.equal((await store.getQuarantine(id))!.status, "released");
  });

  it("thin panels are topped up as the pool grows; genesis-era cases are left alone", async () => {
    const { svc, store, add, clock } = await setup();
    const author = await add("Author-3", "op-author3");
    const genesis = await submitPaper(svc, author, "Author-3", iso(clock.t), "Submitted before any jurors existed at all");
    assert.deepEqual((await store.getQuarantine(genesis))!.jury, []);
    await add("V1", "op-v1", 1);
    const thin = await submitPaper(svc, author, "Author-3", iso(clock.t + 1000), "Submitted when one juror existed");
    assert.deepEqual((await store.getQuarantine(thin))!.jury, ["V1"]);
    await add("V2", "op-v2", 1);
    const r = await svc.enforceDeadlines();
    assert.equal(r.seated, 1);
    assert.deepEqual((await store.getQuarantine(thin))!.jury.sort(), ["V1", "V2"]);
    assert.deepEqual((await store.getQuarantine(genesis))!.jury, [], "the genesis rule still applies");
  });
});
