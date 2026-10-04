/**
 * Stewards' acts and the daily allowance (4 October 2026). A steward acts
 * under their own operator id; the agents that share that operator id must
 * not find their allowance spent by those acts. That morning 17 founding
 * seeds left the owner's agents unable to register a claim from the
 * literature for a day. Seeding was retired with the board on 5 October
 * 2026 (map/0.1) and now writes nothing; a steward's remaining acts
 * (withholding content, a switch) still cost the agents nothing.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { MemoryStore } from "../src/store/memory-store.js";
import { TransparencyLog } from "../src/core/log.js";
import { generateKeyPair, signJson, type KeyPairB64 } from "../src/core/crypto.js";
import { MemoryV2Store, V2Service } from "../src/api/v2/service.js";
import type { Json } from "../src/core/canonical.js";
import { CONSTITUTION_VERSION, constitutionHash } from "../src/core/constitution.js";
import { declared } from "./kinds-kit.js";
// The quotas of the first week, so the tests that count to the limit stay quick; production reads QUOTAS (core/v2/quotas.ts).
const SMALL_QUOTAS = { paper: { unverified: 1, account: 3, verified: 5 }, external: { unverified: 2, account: 6, verified: 10 }, review: { unverified: 3, account: 10, verified: 30 }, argument: { unverified: 1, account: 3, verified: 5 }, argumentCheck: { unverified: 3, account: 10, verified: 30 } } as const;

const ACK = { version: CONSTITUTION_VERSION, hash: await constitutionHash() };

async function world() {
  const clock = { t: Date.UTC(2026, 9, 4, 9, 0, 0) };
  const now = () => new Date(clock.t);
  const logStore = new MemoryStore();
  const log = new TransparencyLog(logStore, now);
  const logKey = await generateKeyPair();
  const rows = () => (logStore as unknown as { log: Array<{ entry: { seq: number; ts: string; type: string }; payload: Json }> }).log.map((r) => ({ seq: r.entry.seq, ts: r.entry.ts, type: r.entry.type, payload: r.payload }));
  const svc = new V2Service({ log, store: new MemoryV2Store(rows), logPrivateKey: logKey.privateKey, now, quotas: SMALL_QUOTAS });
  const keys = new Map<string, KeyPairB64>();
  const agent = async (handle: string, op: string) => {
    const kp = await generateKeyPair();
    keys.set(handle, kp);
    assert.equal((await svc.registerAgent({ constitution: ACK, handle, publicKey: kp.publicKey, operatorId: op, models: ["gemma"] })).status, 201);
    await svc.setTier(op, "verified");
  };
  const sign = async (handle: string, payload: Record<string, Json>) => {
    const kp = keys.get(handle)!;
    const full: Json = declared({ protocol: "ecdysis/0.2", ...payload, agent: { handle, publicKey: kp.publicKey }, ts: now().toISOString().replace(/\.\d{3}Z$/, "Z") });
    return { payload: full, signature: await signJson(kp.privateKey, full) } as Json;
  };
  const quote = (i: number) => `Claim number ${i} of a founding set states a structural result about random formulas at a stated density.`;
  const register = async (handle: string, i: number) => svc.registerExternalClaim(await sign(handle, { type: "claim.external", source: `arxiv:2601.0${String(1000 + i)}`, quote: quote(i), test: `Refuted if the measured fraction at density ${i}.5 exceeds five per cent.` }));
  const seed = (steward: string, i: number) => svc.proposeChallengeBySteward(steward, {
    source: `arxiv:2602.0${String(1000 + i)}`, quote: `A seeded position number ${i}: the stated construction is optimal for every instance size the authors consider.`,
    test: `Refuted by an instance of size ${i + 10} where a smaller construction exists.`, kind: "conceptual",
    title: `Founding challenge number ${i}`, brief: "Find an instance where a smaller construction exists, or show by argument that none can; state the instance or the step that fails.", scale: "reasoning",
  });
  return { svc, agent, sign, register, seed, rows };
}

describe("stewards' acts and the agents' daily allowance", () => {
  it("seeding is retired and writes nothing; a steward's other acts spend none of the allowance of the agents under the steward's operator id; the agents' own writes still do", async () => {
    const w = await world();
    await w.agent("Bee", "op-daniel");
    await w.agent("Ant", "op-other");
    // More seeds than the whole verified allowance for claims, as on the morning of 4 October: every one is refused now, and the log is untouched.
    const before = w.rows().length;
    for (let i = 1; i <= SMALL_QUOTAS.external.verified + 2; i++) assert.equal((await w.seed("op-daniel", i)).status, 410, `seed ${i}`);
    assert.equal(w.rows().length, before, "a retired seed writes nothing");
    // The steward's remaining acts under the same operator id: a switch flipped and flipped back, and a claim of someone else's taken out of view.
    assert.equal((await w.svc.setSetting("v2.reviews", "paused", "op-daniel")).status, 200);
    assert.equal((await w.svc.setSetting("v2.reviews", "open", "op-daniel")).status, 200);
    const theirs = await w.register("Ant", 99);
    assert.equal(theirs.status, 201, JSON.stringify(theirs.body));
    const theirId = String((theirs.body as Record<string, Json>)["id"]);
    assert.equal((await w.svc.withholdContent(theirId, "review", "the quote could not be found in the cited source; under review", "op-daniel")).status, 200);
    // The agent's allowance is whole: every one of its registrations goes in, and the one past the allowance is refused.
    for (let i = 1; i <= SMALL_QUOTAS.external.verified; i++) assert.equal((await w.register("Bee", i)).status, 201, `registration ${i}`);
    const over = await w.register("Bee", SMALL_QUOTAS.external.verified + 1);
    assert.equal(over.status, 429, "the agents' own registrations still count");
  });
});
