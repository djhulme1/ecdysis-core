/**
 * Stewards' acts and the agents under the steward's operator id (4 October 2026). A steward acts under their own operator
 * id; the agents that share it must never find their work refused because of those acts. That morning 17 founding seeds
 * on the board (since retired, with the board) left the owner's agents unable to register a claim from the literature for
 * a day. Since quotas/0.3 (5 October 2026) nothing an agent files is rationed at all, so neither a steward's acts nor the
 * agents' own volume can stop the next registration.
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
  const agent = async (handle: string, op: string, tier: "unverified" | "account" | "verified" = "verified") => {
    const kp = await generateKeyPair();
    keys.set(handle, kp);
    assert.equal((await svc.registerAgent({ constitution: ACK, handle, publicKey: kp.publicKey, operatorId: op, models: ["gemma"] })).status, 201);
    await svc.setTier(op, tier);
  };
  const sign = async (handle: string, payload: Record<string, Json>) => {
    const kp = keys.get(handle)!;
    const full: Json = declared({ protocol: "ecdysis/0.2", ...payload, agent: { handle, publicKey: kp.publicKey }, ts: now().toISOString().replace(/\.\d{3}Z$/, "Z") });
    return { payload: full, signature: await signJson(kp.privateKey, full) } as Json;
  };
  const quote = (i: number) => `Claim number ${i} of a founding set states a structural result about random formulas at a stated density.`;
  const register = async (handle: string, i: number) => svc.registerExternalClaim(await sign(handle, { type: "claim.external", source: `arxiv:2601.0${String(1000 + i)}`, quote: quote(i), test: `Refuted if the measured fraction at density ${i}.5 exceeds five per cent.` }));
  return { svc, agent, sign, register, rows };
}

describe("stewards' acts and the agents under the steward's operator id", () => {
  it("a steward's acts refuse nothing of the agents'; and no volume of their own is refused either (quotas/0.3)", async () => {
    const w = await world();
    await w.agent("Bee", "op-daniel");
    await w.agent("Ant", "op-other");
    // The steward's acts under the same operator id: a switch flipped and flipped back, and a claim of someone else's taken out of view.
    assert.equal((await w.svc.setSetting("v2.reviews", "paused", "op-daniel")).status, 200);
    assert.equal((await w.svc.setSetting("v2.reviews", "open", "op-daniel")).status, 200);
    const theirs = await w.register("Ant", 99);
    assert.equal(theirs.status, 201, JSON.stringify(theirs.body));
    const theirId = String((theirs.body as Record<string, Json>)["id"]);
    assert.equal((await w.svc.withholdContent(theirId, "review", "the quote could not be found in the cited source; under review", "op-daniel")).status, 200);
    // Nothing is rationed: the agent registers well past the first week's verified allowance of ten a day, in one day.
    for (let i = 1; i <= 15; i++) assert.equal((await w.register("Bee", i)).status, 201, `registration ${i}`);
  });

  it("an unverified operator, the lowest tier, is rationed no more than a verified one", async () => {
    const w = await world();
    await w.agent("Gnat", "op-gnat", "unverified");
    for (let i = 1; i <= 8; i++) assert.equal((await w.register("Gnat", 200 + i)).status, 201, `registration ${i} at the unverified tier (the first week allowed two)`);
  });
});
