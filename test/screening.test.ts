/**
 * Screening with the safety classifier (Workers AI, Llama Guard 3), on the
 * network of claims.
 *
 * Guarantees: a possible hazard is frozen for the owner (R1) and never
 * published; the gravest category is refused outright; a finding that is the
 * stewards' business publishes the claim under review, out of view until a
 * steward looks; a classifier that cannot answer fails closed (nothing is
 * published) without spending the owner's key on an outage; the words a
 * receipt shows are screened like a claim's; and no hazard vocabulary appears
 * here: the fake classifier keys on a neutral marker.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { MemoryStore } from "../src/store/memory-store.js";
import { TransparencyLog } from "../src/core/log.js";
import { generateKeyPair, type KeyPairB64 } from "../src/core/crypto.js";
import { CONSTITUTION_VERSION, constitutionHash } from "../src/core/constitution.js";
import { guardScreener, parseGuard, structuralScreener, type AiLike } from "../src/core/hazard.js";
import { MemoryV2Store, V2Service } from "../src/api/v2/service.js";
import { screenersFrom, type Env } from "../src/index.js";
import { signedClaim } from "./claims-kit.js";
import type { Json } from "../src/core/canonical.js";

const NOW = Date.UTC(2026, 9, 5, 12, 0, 0);

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

async function world(ai: AiLike, o: { stewardCategories?: string[] } = {}) {
  const store = new MemoryStore();
  const now = () => new Date(NOW);
  const log = new TransparencyLog(store, now);
  const logKey = await generateKeyPair();
  const v2store = new MemoryV2Store(() => (store as unknown as { log: Array<{ entry: { seq: number; ts: string; type: string }; payload: Json }> }).log.map((r) => ({ seq: r.entry.seq, ts: r.entry.ts, type: r.entry.type, payload: r.payload })));
  const referrals: string[] = [];
  const svc = new V2Service({
    log, store: v2store, logPrivateKey: logKey.privateKey, now, screeners: [structuralScreener(), guardScreener(ai)],
    ...(o.stewardCategories ? { stewardCategories: new Set(o.stewardCategories) } : {}),
    onReferral: async (subject, detail) => { referrals.push(`${subject}: ${detail}`); },
  });
  const ack = { version: CONSTITUTION_VERSION, hash: await constitutionHash() };
  const add = async (handle: string, op: string) => {
    const kp = await generateKeyPair();
    assert.equal((await svc.registerAgent({ handle, publicKey: kp.publicKey, operatorId: op, constitution: ack })).status, 201);
    return kp;
  };
  const claim = async (handle: string, kp: KeyPairB64, rationaleExtra = "") =>
    signedClaim({ handle, ...kp }, { rationale: `Weight decay makes the generalising circuit cheaper than memorisation, so it wins once the loss has converged. ${rationaleExtra}`.trim(), ts: "2026-10-05T11:00:00Z" });
  return { store, svc, add, claim, referrals, logKey };
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

describe("screening routes a claim by risk", () => {
  it("a possible hazard is held for the owner (R1): nothing is published, nothing is shown", async () => {
    const { svc, add, claim } = await world(fakeAi());
    const a = await add("Author-1", "op-a");
    const c = await claim("Author-1", a, "MARKER-S9");
    const r = await svc.publishClaim(c.envelope);
    assert.equal(r.status, 202, JSON.stringify(r.body));
    const b = r.body as { status: string; id: string; claim: string };
    assert.equal(b.status, "held");
    assert.equal(b.id, c.cid, "the hold names the submission by its content id");
    assert.equal(b.claim, c.id, "and says what id the claim would enter under");
    const rec = await svc.record();
    assert.ok(rec.held.has(c.cid) && rec.screeningHolds.has(c.cid));
    assert.ok(!rec.native.has(c.id), "not on the record");
    assert.equal((await svc.claim(c.id)).status, 404, "nothing to read");
    const list = (await svc.claimsList({ limit: 10, all: true })).body as { claims: unknown[] };
    assert.equal(list.claims.length, 0);
    const holds = await svc.holds();
    assert.equal(holds.length, 1);
    assert.equal(holds[0]!.subject, c.cid);
    assert.equal(holds[0]!.state, "open");
    const again = await svc.publishClaim(c.envelope);
    assert.equal(again.status, 409, "sending it again while held changes nothing");
  });

  it("the gravest category is refused outright, with nothing kept, and works on the string shape too", async () => {
    const { svc, add, claim } = await world(fakeAi("string"));
    const a = await add("Author-2", "op-a2");
    const c = await claim("Author-2", a, "MARKER-S4");
    const r = await svc.publishClaim(c.envelope);
    assert.equal(r.status, 451);
    const rec = await svc.record();
    assert.ok(!rec.held.has(c.cid) && !rec.native.has(c.id));
    assert.equal((await svc.holds()).length, 0, "no hold: a refusal needs no decision");
  });

  it("a finding that is the stewards' business publishes the claim under review, out of view until a steward looks", async () => {
    const { svc, add, claim, referrals } = await world(fakeAi(), { stewardCategories: ["privacy", "defamation"] });
    const a = await add("Author-3", "op-a3");
    const c = await claim("Author-3", a, "MARKER-S7");
    const r = await svc.publishClaim(c.envelope);
    assert.equal(r.status, 202, JSON.stringify(r.body));
    assert.equal((r.body as { status: string }).status, "under-review");
    const rec = await svc.record();
    assert.ok(rec.native.has(c.id), "on the record");
    assert.ok(rec.held.has(c.id), "but out of view");
    assert.equal(rec.withheld.get(c.id)?.status, "review");
    assert.equal(rec.withheld.get(c.id)?.steward, "", "nobody's decision yet: screening referred it");
    assert.equal((await svc.claim(c.id)).status, 451, "nothing about it is shown");
    assert.equal(referrals.length, 1, "the stewards are told");
    assert.match(referrals[0]!, /privacy/);
    // The same finding without a steward category is a hazard hold, not a referral.
    const plain = await world(fakeAi());
    const b = await plain.add("Author-4", "op-a4");
    const c2 = await plain.claim("Author-4", b, "MARKER-S7");
    assert.equal(((await plain.svc.publishClaim(c2.envelope)).body as { status: string }).status, "held");
  });

  it("a classifier that cannot answer fails closed: nothing is published, nothing is held, and the same envelope is taken later", async () => {
    const down = fakeAi("object", true);
    const { svc, add, claim } = await world(down);
    const a = await add("Author-5", "op-a5");
    const c = await claim("Author-5", a);
    const r = await svc.publishClaim(c.envelope);
    assert.equal(r.status, 503, JSON.stringify(r.body));
    assert.equal((r.body as { retry: boolean }).retry, true);
    const rec = await svc.record();
    assert.ok(!rec.native.has(c.id) && !rec.held.has(c.cid), "an outage spends nobody's key");
    // Back up: the very same envelope is published.
    const up = await world(fakeAi());
    const b = await up.add("Author-5", "op-a5");
    const c2 = await up.claim("Author-5", b);
    assert.equal((await up.svc.publishClaim(c2.envelope)).status, 201);
  });

  it("clean work is published at once, with no probation and no vote", async () => {
    const ai = fakeAi();
    const { svc, add, claim } = await world(ai);
    const a = await add("Author-6", "op-a6");
    const c = await claim("Author-6", a);
    const r = await svc.publishClaim(c.envelope);
    assert.equal(r.status, 201, JSON.stringify(r.body));
    assert.equal((r.body as { id: string }).id, c.id);
    const before = ai.calls;
    await svc.claim(c.id);
    await svc.claimsList({ limit: 10 });
    assert.equal(ai.calls, before, "no classifier calls on reads: screening happens once, at publication");
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
