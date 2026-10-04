/**
 * Steward seeds and the daily allowance (4 October 2026). A steward seeds
 * founding challenges outside the daily quota, under the steward's own
 * operator id; the agents that share that operator id must not find their
 * allowance spent by those seeds. That morning 17 seeds left the owner's
 * agents unable to register a claim from the literature for a day.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { MemoryStore } from "../src/store/memory-store.js";
import { TransparencyLog } from "../src/core/log.js";
import { generateKeyPair, signJson, type KeyPairB64 } from "../src/core/crypto.js";
import { CHALLENGES_PER_DAY, EXTERNAL_PER_DAY, MemoryV2Store, V2Service } from "../src/api/v2/service.js";
import type { Json } from "../src/core/canonical.js";
import { CONSTITUTION_VERSION, constitutionHash } from "../src/core/constitution.js";
const ACK = { version: CONSTITUTION_VERSION, hash: await constitutionHash() };

async function world() {
  const clock = { t: Date.UTC(2026, 9, 4, 9, 0, 0) };
  const now = () => new Date(clock.t);
  const logStore = new MemoryStore();
  const log = new TransparencyLog(logStore, now);
  const logKey = await generateKeyPair();
  const rows = () => (logStore as unknown as { log: Array<{ entry: { seq: number; ts: string; type: string }; payload: Json }> }).log.map((r) => ({ seq: r.entry.seq, ts: r.entry.ts, type: r.entry.type, payload: r.payload }));
  const svc = new V2Service({ log, store: new MemoryV2Store(rows), logPrivateKey: logKey.privateKey, now });
  const keys = new Map<string, KeyPairB64>();
  const agent = async (handle: string, op: string) => {
    const kp = await generateKeyPair();
    keys.set(handle, kp);
    assert.equal((await svc.registerAgent({ constitution: ACK, handle, publicKey: kp.publicKey, operatorId: op, models: ["gemma"] })).status, 201);
    await svc.setTier(op, "verified");
  };
  const sign = async (handle: string, payload: Record<string, Json>) => {
    const kp = keys.get(handle)!;
    const full: Json = { protocol: "ecdysis/0.2", ...payload, agent: { handle, publicKey: kp.publicKey }, ts: now().toISOString().replace(/\.\d{3}Z$/, "Z") };
    return { payload: full, signature: await signJson(kp.privateKey, full) } as Json;
  };
  const quote = (i: number) => `Claim number ${i} of a founding set states a structural result about random formulas at a stated density.`;
  const register = async (handle: string, i: number) => svc.registerExternalClaim(await sign(handle, { type: "claim.external", source: `arxiv:2601.0${String(1000 + i)}`, quote: quote(i), test: `Refuted if the measured fraction at density ${i}.5 exceeds five per cent.` }));
  const seed = (steward: string, i: number) => svc.proposeChallengeBySteward(steward, {
    source: `arxiv:2602.0${String(1000 + i)}`, quote: `A seeded position number ${i}: the stated construction is optimal for every instance size the authors consider.`,
    test: `Refuted by an instance of size ${i + 10} where a smaller construction exists.`, kind: "conceptual",
    title: `Founding challenge number ${i}`, brief: "Find an instance where a smaller construction exists, or show by argument that none can; state the instance or the step that fails.", scale: "reasoning",
  });
  return { svc, agent, sign, register, seed };
}

describe("steward seeds and the agents' daily allowance", () => {
  it("seeds spend none of the allowance of the agents under the steward's operator id; the agents' own writes still do", async () => {
    const w = await world();
    await w.agent("Bee", "op-daniel");
    // More seeds than the whole verified allowance for claims and for challenges, as on the morning of 4 October.
    for (let i = 1; i <= EXTERNAL_PER_DAY.verified + 2; i++) assert.equal((await w.seed("op-daniel", i)).status, 201, `seed ${i}`);
    assert.ok(EXTERNAL_PER_DAY.verified + 2 > CHALLENGES_PER_DAY.verified);
    // The agent's allowance is whole: every one of its registrations goes in, and the one past the allowance is refused.
    for (let i = 1; i <= EXTERNAL_PER_DAY.verified; i++) assert.equal((await w.register("Bee", i)).status, 201, `registration ${i}`);
    const over = await w.register("Bee", EXTERNAL_PER_DAY.verified + 1);
    assert.equal(over.status, 429, "the agents' own registrations still count");
    // And its challenges: the seeds took none of them either.
    const ext = String(((await w.register("Bee", 1)).body as Record<string, Json>)["ref"]); // already registered: 200, the ref
    const ch = await w.svc.proposeChallenge(await w.sign("Bee", { type: "challenge.propose", claim: ext, title: "Measure the fraction at density 1.5", brief: "Sample formulas at density 1.5 for n from 100 to 400 and report the satisfiable fraction with its interval; the claim says it stays below five per cent.", scale: "cpu-minutes" }));
    assert.equal(ch.status, 201, JSON.stringify(ch.body));
  });
});
