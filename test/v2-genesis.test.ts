/**
 * Genesis: the founder adopts the constitution (2.1.0, the network of
 * claims) under reserved power R2, and the record opens. Before that entry
 * nothing may register; the entry is accepted once, for the text the
 * archive carries, signed by the operator key and no other.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { MemoryStore } from "../src/store/memory-store.js";
import { TransparencyLog } from "../src/core/log.js";
import { generateKeyPair, signJson } from "../src/core/crypto.js";
import { MemoryV2Store, V2Service } from "../src/api/v2/service.js";
import { route } from "../src/api/router.js";
import { MemoryRateLimiter } from "../src/api/router.js";
import { structuralScreener } from "../src/core/hazard.js";
import { CONSTITUTION_HASH, CONSTITUTION_V1_HASH, CONSTITUTION_VERSION, constitutionHash } from "../src/core/constitution.js";
import type { Json } from "../src/core/canonical.js";

async function world(withOperatorKey = true) {
  const clock = { t: Date.UTC(2026, 9, 4, 9, 0, 0) };
  const now = () => new Date(clock.t);
  const logStore = new MemoryStore();
  const log = new TransparencyLog(logStore, now);
  const logKey = await generateKeyPair();
  const operatorKey = await generateKeyPair();
  const store = new MemoryV2Store(() => (logStore as unknown as { log: Array<{ entry: { seq: number; ts: string; type: string }; payload: Json }> }).log.map((r) => ({ seq: r.entry.seq, ts: r.entry.ts, type: r.entry.type, payload: r.payload })));
  const svc = new V2Service({ log, store, logPrivateKey: logKey.privateKey, now, operatorPublicKey: withOperatorKey ? operatorKey.publicKey : null });
  const ts = () => now().toISOString().replace(/\.\d{3}Z$/, "Z");
  const hash = await constitutionHash();
  const adopt = async (o: { key?: string; version?: string; hash?: string; ts?: string } = {}) => {
    const body = { version: o.version ?? CONSTITUTION_VERSION, hash: o.hash ?? hash, ts: o.ts ?? ts() };
    const signature = await signJson(o.key ?? operatorKey.privateKey, { op: "adopt", ...body });
    return svc.adoptConstitution({ ...body, signature });
  };
  const register = async (handle: string) => {
    const kp = await generateKeyPair();
    return svc.registerAgent({ handle, publicKey: kp.publicKey, operatorId: `op-${handle}`, constitution: { version: CONSTITUTION_VERSION, hash } });
  };
  return { svc, log, logStore, logKey, operatorKey, adopt, register, clock, now, hash };
}

describe("genesis: the constitution is adopted under R2 before anything else", () => {
  it("the record is closed until the founder adopts; then it opens, and entry 0 is the adoption", async () => {
    const w = await world();
    const before = await w.register("Early");
    assert.equal(before.status, 503, JSON.stringify(before.body));
    assert.equal((before.body as { status?: string }).status, "before genesis");
    assert.deepEqual((before.body as { constitution?: Json }).constitution, { version: "2.1.0", hash: CONSTITUTION_HASH }, "the refusal names the text that will be adopted");
    const r = await w.adopt();
    assert.equal(r.status, 201, JSON.stringify(r.body));
    assert.equal((r.body as { seq: number }).seq, 0, "the first entry of the record");
    const rec = await w.svc.record();
    assert.deepEqual(rec.constitution && { version: rec.constitution.version, hash: rec.constitution.hash, seq: rec.constitution.seq }, { version: "2.1.0", hash: CONSTITUTION_HASH, seq: 0 });
    const after = await w.register("Moth-1");
    assert.equal(after.status, 201, JSON.stringify(after.body));
    assert.deepEqual((after.body as { constitution: Json }).constitution, { version: "2.1.0", hash: CONSTITUTION_HASH }, "the agent acknowledged the adopted text");
  });

  it("only the operator key adopts: the log key, a stranger, a stale time, a wrong text and a second adoption are all refused", async () => {
    const w = await world();
    assert.equal((await w.adopt({ key: w.logKey.privateKey })).status, 401, "the log key can never stand in for the operator key");
    assert.equal((await w.adopt({ key: (await generateKeyPair()).privateKey })).status, 401);
    assert.equal((await w.adopt({ ts: new Date(w.clock.t - 2 * 3600_000).toISOString().replace(/\.\d{3}Z$/, "Z") })).status, 400, "a signature captured earlier cannot be replayed");
    const wrongText = await w.adopt({ version: "1.0.0", hash: CONSTITUTION_V1_HASH });
    assert.equal(wrongText.status, 409, "the archive adopts only the text it carries");
    assert.match(String((wrongText.body as { error: string }).error), /carries constitution 2\.1\.0/);
    assert.equal((await w.adopt({ hash: "ab".repeat(32) })).status, 409);
    assert.equal((await w.svc.record()).constitution, null, "nothing refused reached the log");
    assert.equal((await w.adopt()).status, 201);
    const again = await w.adopt();
    assert.equal(again.status, 409, "adoption is genesis: once");
    assert.equal((await w.svc.record()).constitution!.seq, 0);
  });

  it("fails closed without an operator key, and the public record says whether the record has opened", async () => {
    const closed = await world(false);
    const r = await closed.adopt();
    assert.equal(r.status, 501, "no operator key: nothing can be adopted");
    // Without an operator key (tests, local harnesses) registration is not gated: the module's text stands in, as before.
    assert.equal((await closed.register("Local")).status, 201);
    // Over HTTP: /v2/record shows the adoption, or null before it.
    const w = await world();
    const read = async () => (await (await route(new Request("https://api.ecdysis.me/v2/record"), new MemoryRateLimiter(), { v2: w.svc })).json()) as { constitution: Json };
    assert.equal((await read()).constitution, null);
    const body = { version: CONSTITUTION_VERSION, hash: w.hash, ts: w.now().toISOString().replace(/\.\d{3}Z$/, "Z") };
    const res = await route(new Request("https://api.ecdysis.me/v2/constitution/adopt", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ ...body, signature: await signJson(w.operatorKey.privateKey, { op: "adopt", ...body }) }) }), new MemoryRateLimiter(), { v2: w.svc });
    assert.equal(res.status, 201, await res.text());
    const shown = (await read()).constitution as { version: string; hash: string; seq: number };
    assert.equal(shown.version, "2.1.0");
    assert.equal(shown.hash, CONSTITUTION_HASH);
    assert.equal(shown.seq, 0);
  });
});

describe("the log key must match its pin", () => {
  it("a signing key that is not the pinned public key's other half freezes every write; matching keys, or nothing to compare, pass", async () => {
    const { logKeysAgree, resetKeyAgreement } = await import("../src/index.js");
    const a = await generateKeyPair();
    const b = await generateKeyPair();
    resetKeyAgreement();
    assert.equal(await logKeysAgree({ STH_SIGNING_KEY_PKCS8: a.privateKey, STH_PUBLIC_KEY: a.publicKey }), true);
    resetKeyAgreement();
    assert.equal(await logKeysAgree({ STH_SIGNING_KEY_PKCS8: a.privateKey, STH_PUBLIC_KEY: b.publicKey }), false, "the new key installed before the pin moved, or a key swapped by mistake");
    resetKeyAgreement();
    assert.equal(await logKeysAgree({ STH_SIGNING_KEY_PKCS8: "not-a-key", STH_PUBLIC_KEY: a.publicKey }), false, "an unreadable key is a mismatch, not a pass");
    resetKeyAgreement();
    assert.equal(await logKeysAgree({ STH_SIGNING_KEY_PKCS8: a.privateKey, STH_PUBLIC_KEY: "REPLACE_WITH_YOUR_STH_PUBLIC_KEY" }), true, "no pin: nothing to compare");
    resetKeyAgreement();
    assert.equal(await logKeysAgree({ STH_PUBLIC_KEY: a.publicKey }), true, "no key: heads are unsigned, a known state");
    resetKeyAgreement();
  });
});
