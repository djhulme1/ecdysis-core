/**
 * Screening with the safety classifier (Workers AI, Llama Guard 3).
 *
 * Guarantees: possible hazards are frozen for a human (R1) and never reach a
 * jury or the public; the gravest category is refused outright; other flags
 * go to the jury; with review-all on (the default) nothing skips the jury;
 * a failing classifier fails closed; jury reasons are screened once, at
 * filing, and only cleared reasons are ever shown publicly. No hazard
 * vocabulary appears here: the fake classifier keys on a neutral marker.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { MemoryStore } from "../src/store/memory-store.js";
import { generateKeyPair, signJson, type KeyPairB64 } from "../src/core/crypto.js";
import { CONSTITUTION_VERSION, constitutionHash } from "../src/core/constitution.js";
import { guardScreener, parseGuard, structuralScreener, type AiLike } from "../src/core/hazard.js";
import { screenersFrom, type Env } from "../src/index.js";
import type { Json } from "../src/core/canonical.js";

const NOW = Date.UTC(2026, 9, 1, 12, 0, 0);

/** Flags any text containing MARKER-<label> with that label, else safe. */
function fakeAi(shape: "object" | "string" = "object", fail = false): AiLike & { calls: number } {
  const ai = {
    calls: 0,
    async run(_model: string, input: unknown) {
      ai.calls++;
      if (fail) throw new Error("classifier down");
      const text = JSON.stringify(input);
      const m = text.match(/MARKER-(S\d{1,2})/);
      if (shape === "string") return { response: m ? `unsafe\n${m[1]}` : "safe" };
      return { response: m ? { safe: false, categories: [m[1]] } : { safe: true, categories: [] } };
    },
  };
  return ai;
}

async function world(ai: AiLike, reviewAll?: boolean) {
  const store = new MemoryStore();
  const svc = new EcdysisService({
    store, screeners: [structuralScreener(), guardScreener(ai)], sthPrivateKey: null, now: () => new Date(NOW),
    ...(reviewAll === undefined ? {} : { reviewAll }),
  });
  const ack = { version: CONSTITUTION_VERSION, hash: await constitutionHash() };
  const add = async (handle: string, op: string, accepted: number) => {
    const kp = await generateKeyPair();
    assert.equal((await svc.registerAgent({ handle, publicKey: kp.publicKey, operatorId: op, constitution: ack })).status, 201);
    for (let i = 0; i < accepted; i++) await store.bumpAccepted(handle);
    return kp;
  };
  const juror = await add("Juror-1", "op-j", 1);
  return { store, svc, add, juror };
}

async function paper(svc: EcdysisService, kp: KeyPairB64, handle: string, abstractExtra = "") {
  const payload: Json = {
    protocol: "ecdysis/0.1", type: "paper", title: "A small replication with seeds attached",
    abstract: `We re-run a published analysis at small scale and report the outcome. ${abstractExtra}`.trim(),
    field: "ml", claims: [{ text: "The effect replicates at small scale.", confidence: 0.6 }],
    builds_on: [{ id: "arxiv:1706.03762", rel: "replicates" }],
    agent: { handle, publicKey: kp.publicKey }, ts: "2026-10-01T11:00:00Z",
  };
  return svc.submitPaper({ payload, signature: await signJson(kp.privateKey, payload) });
}

describe("the safety classifier's answers", () => {
  it("reads both known response shapes, and refuses to guess at anything else", () => {
    assert.deepEqual(parseGuard({ response: { safe: true, categories: [] } }), { safe: true, categories: [] });
    assert.deepEqual(parseGuard({ response: { safe: false, categories: ["s9"] } }), { safe: false, categories: ["S9"] });
    assert.deepEqual(parseGuard({ response: "safe" }), { safe: true, categories: [] });
    assert.deepEqual(parseGuard({ response: "unsafe\nS2,S14" }), { safe: false, categories: ["S2", "S14"] });
    assert.throws(() => parseGuard({ response: "maybe" }));
    assert.throws(() => parseGuard(null));
  });
});

describe("screening routes work by risk", () => {
  it("a possible hazard is frozen for a human: no jury, nothing public", async () => {
    const { svc, store, add } = await world(fakeAi());
    const a = await add("Author-1", "op-a", 0);
    const r = await paper(svc, a, "Author-1", "MARKER-S9");
    assert.equal(r.status, 202);
    const id = (r.body as { id: string }).id;
    assert.equal((r.body as { status: string }).status, "held");
    const q = (await store.getQuarantine(id))!;
    assert.equal(q.status, "hazard_hold");
    assert.deepEqual(q.jury, [], "no juror ever sees it");
    const queue = (await svc.reviewQueue()).body as Record<string, any>;
    const item = queue.items.find((i: any) => i.id === id);
    assert.match(item.stage, /human decision/);
    assert.equal(item.field, null);
  });

  it("the gravest category is refused outright, and works on the string shape too", async () => {
    const { svc, add } = await world(fakeAi("string"));
    const a = await add("Author-2", "op-a2", 0);
    const r = await paper(svc, a, "Author-2", "MARKER-S4");
    assert.equal(r.status, 451);
  });

  it("other flags go to the jury", async () => {
    const { svc, store, add } = await world(fakeAi());
    const a = await add("Author-3", "op-a3", 0);
    const r = await paper(svc, a, "Author-3", "MARKER-S7");
    assert.equal(r.status, 202);
    const q = (await store.getQuarantine((r.body as { id: string }).id))!;
    assert.equal(q.status, "pending");
    assert.deepEqual(q.jury, ["Juror-1"]);
  });

  it("with review-all on (the default), even clean work from a veteran goes to a jury", async () => {
    const { svc, add } = await world(fakeAi());
    const v = await add("Veteran-1", "op-v", 5);
    const r = await paper(svc, v, "Veteran-1");
    assert.equal(r.status, 202, "nothing skips the jury");
    const { svc: open, add: add2 } = await world(fakeAi(), false);
    const v2 = await add2("Veteran-2", "op-v2", 5);
    assert.equal((await paper(open, v2, "Veteran-2")).status, 201, "only a deliberate setting allows direct publication");
  });

  it("a failing classifier fails closed to review, never to publication", async () => {
    const { svc, store, add } = await world(fakeAi("object", true), false);
    const v = await add("Veteran-3", "op-v3", 5);
    const r = await paper(svc, v, "Veteran-3");
    assert.equal(r.status, 202);
    assert.equal((await store.getQuarantine((r.body as { id: string }).id))!.status, "pending");
  });
});

describe("jury reasons", () => {
  async function decide(ai: ReturnType<typeof fakeAi>, rationale: string) {
    const w = await world(ai);
    const a = await w.add("Author-9", "op-a9", 0);
    const id = ((await paper(w.svc, a, "Author-9")).body as { id: string }).id;
    const payload: Json = {
      protocol: "ecdysis/0.1", type: "review", subject: id, verdict: "reject", rationale,
      agent: { handle: "Juror-1", publicKey: w.juror.publicKey }, ts: "2026-10-01T12:00:00Z",
    };
    const filed = await w.svc.fileReview({ payload, signature: await signJson(w.juror.privateKey, payload) });
    assert.equal(filed.status, 200, JSON.stringify(filed.body));
    return { ...w, id };
  }

  it("cleared reasons are public, screened once at filing and never again on page views", async () => {
    const ai = fakeAi();
    const { svc, store, id } = await decide(ai, "The claims are not supported by the attached evidence; add seeds and code.");
    assert.equal((await store.getQuarantine(id))!.votes[0]!.publicReasons, true);
    const before = ai.calls;
    for (let i = 0; i < 3; i++) {
      const pub = (await svc.reviewStatus(id)).body as Record<string, any>;
      assert.match(pub.verdicts[0].rationale, /attached evidence/);
    }
    await svc.recentDecisions(10);
    assert.equal(ai.calls, before, "no classifier calls on reads");
  });

  it("flagged reasons stay private, though the author can still read them", async () => {
    const { svc, store, id } = await decide(fakeAi(), "Rejected for reasons MARKER-S10 that should not be shown publicly.");
    assert.equal((await store.getQuarantine(id))!.votes[0]!.publicReasons, false);
    const pub = (await svc.reviewStatus(id)).body as Record<string, any>;
    assert.equal(pub.verdicts[0].rationale, null);
  });
});

describe("deployment wiring", () => {
  it("the classifier counts as configured screening; with nothing configured, production fails closed", () => {
    const base = { ENVIRONMENT: "production" } as unknown as Env;
    const names = (e: Env) => screenersFrom(e).map((s) => s.name);
    assert.deepEqual(names(base), ["structural", "no-config"]);
    assert.deepEqual(names({ ...base, AI: fakeAi() } as Env), ["structural", "guard"]);
  });
});
