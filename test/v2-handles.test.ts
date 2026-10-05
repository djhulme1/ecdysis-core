/**
 * handles/0.1, adversarially: nobody registers under a decommissioned agent's
 * handle, in any letter case and by either route (a self-custodied key or a
 * managed agent), and nobody registers a letter-case look-alike of an agent
 * already on the record. The one earlier agent that was not decommissioned by
 * its own operators keeps its name free.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { MemoryStore } from "../src/store/memory-store.js";
import { TransparencyLog } from "../src/core/log.js";
import { generateKeyPair } from "../src/core/crypto.js";
import { MemoryV2Store, V2Service } from "../src/api/v2/service.js";
import type { Json } from "../src/core/canonical.js";
import { CONSTITUTION_VERSION, constitutionHash } from "../src/core/constitution.js";
import { handleRefusal, RETIRED_HANDLES } from "../src/core/v2/handles.js";

const ACK = { version: CONSTITUTION_VERSION, hash: await constitutionHash() };
const ACCOUNT_OP = "op_" + "ab".repeat(12);

async function world() {
  const store = new MemoryStore();
  const now = () => new Date(Date.UTC(2026, 9, 5, 17, 0, 0));
  const log = new TransparencyLog(store, now);
  const logKey = await generateKeyPair();
  const v2 = new MemoryV2Store(() => (store as unknown as { log: Array<{ entry: { seq: number; ts: string; type: string }; payload: Json }> }).log.map((r) => ({ seq: r.entry.seq, ts: r.entry.ts, type: r.entry.type, payload: r.payload })));
  const svc = new V2Service({ log, store: v2, logPrivateKey: logKey.privateKey, now });
  const register = async (handle: string, operatorId = `op-${handle.toLowerCase()}`) =>
    svc.registerAgent({ constitution: ACK, handle, publicKey: (await generateKeyPair()).publicKey, operatorId });
  const managed = async (handle: string) => svc.registerManagedAgent(ACCOUNT_OP, handle, (await generateKeyPair()).publicKey, ["claude-fable-5-1"]);
  const agents = async () => [...(await svc.record()).agents.keys()];
  return { register, managed, agents };
}

const error = (r: { body: unknown }) => String((r.body as { error?: unknown }).error ?? "");

describe("handles/0.1: retired handles", () => {
  it("refuses every decommissioned agent's handle, by a self-custodied key, and writes nothing", async () => {
    const w = await world();
    for (const h of RETIRED_HANDLES) {
      const r = await w.register(h);
      assert.equal(r.status, 409, h);
      assert.match(error(r), /^handle retired: /, h);
      assert.match(error(r), /mirror\/v2/, h);
    }
    assert.deepEqual(await w.agents(), []);
  });

  it("refuses them in any letter case, naming the retired spelling", async () => {
    const w = await world();
    for (const h of ["chrysalis-1", "CHRYSALIS-2", "bombus", "bOmBuS-gEmMa", "instar-1", "Gemini-Djhulme"]) {
      const r = await w.register(h);
      assert.equal(r.status, 409, h);
      assert.match(error(r), /^handle retired: /, h);
    }
    assert.match(error(await w.register("chrysalis-1")), /^handle retired: Chrysalis-1 named/);
    assert.deepEqual(await w.agents(), []);
  });

  it("refuses them as managed agents too: the archive holds no key for a retired name", async () => {
    const w = await world();
    for (const h of ["Instar-1", "chrysalis-2", "Bombus-Qwen"]) {
      const r = await w.managed(h);
      assert.equal(r.status, 409, h);
      assert.match(error(r), /^handle retired: /, h);
    }
    assert.deepEqual(await w.agents(), []);
  });

  it("leaves the earlier record's one outside agent's name free, and new names free", async () => {
    const w = await world();
    assert.equal((await w.register("claude-sonnet-research")).status, 201);
    assert.equal((await w.register("Chrysalis-3")).status, 201, "a new number is a new name");
    assert.equal((await w.managed("Imago")).status, 201);
    assert.equal((await w.register("Exuvia")).status, 201);
    assert.deepEqual((await w.agents()).sort(), ["Chrysalis-3", "Exuvia", "Imago", "claude-sonnet-research"]);
  });
});

describe("handles/0.1: one name whatever its letter case", () => {
  it("refuses a look-alike of an agent on the record, by either route, naming the one there", async () => {
    const w = await world();
    assert.equal((await w.managed("Imago")).status, 201);
    for (const h of ["imago", "IMAGO", "iMaGo"]) {
      const r = await w.register(h);
      assert.equal(r.status, 409, h);
      assert.equal(error(r), "handle taken: Imago is on the record, and a handle is one name whatever its letter case");
    }
    const m = await w.managed("IMAGO");
    assert.equal(m.status, 409);
    assert.match(error(m), /^handle taken: Imago is on the record/);
    assert.equal(error(await w.register("Imago")), "handle taken", "the exact name answers as before");
    assert.equal((await w.register("Imago-2")).status, 201, "a different name is free");
    assert.deepEqual((await w.agents()).sort(), ["Imago", "Imago-2"]);
  });

  it("is a pure function of the names on the record", () => {
    assert.equal(handleRefusal("Teneral", []), null);
    assert.equal(handleRefusal("Teneral", ["Imago", "Exuvia"]), null);
    assert.equal(handleRefusal("teneral", ["Teneral"]), "handle taken: Teneral is on the record, and a handle is one name whatever its letter case");
    assert.equal(handleRefusal("Teneral", ["Teneral"]), "handle taken");
    assert.match(handleRefusal("BOMBUS-ENSEMBLE", []) ?? "", /^handle retired: Bombus-Ensemble named/);
  });
});
