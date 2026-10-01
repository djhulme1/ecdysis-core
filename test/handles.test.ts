/**
 * Paper handles: always valid citation ids, and never shared by two papers.
 * The six-character form drops two symbols of its alphabet, so about one
 * paper in seventy-five would have come out too short to be citable; those,
 * and any collision within a month, fall back to eight hex characters.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { displayHandle, isEcdysisHandle } from "../src/core/ids.js";
import { EcdysisService } from "../src/api/service.js";
import { MemoryStore } from "../src/store/memory-store.js";
import { generateKeyPair, signJson } from "../src/core/crypto.js";
import { CONSTITUTION_VERSION, constitutionHash } from "../src/core/constitution.js";
import { structuralScreener } from "../src/core/hazard.js";
import type { Json } from "../src/core/canonical.js";

describe("paper handles", () => {
  it("are always valid Ecdysis ids, whatever the hash", async () => {
    const at = new Date(Date.UTC(2026, 9, 1));
    let fallbacks = 0;
    for (let i = 0; i < 3000; i++) {
      const cid = `ecd:cid:${i.toString(16).padStart(32, "0")}`;
      const h = await displayHandle(cid, at);
      assert.ok(isEcdysisHandle(h), `${cid} -> ${h}`);
      assert.match(h, /^ecd:2610\./);
      if (/^ecd:2610\.[0-9a-f]{8}$/.test(h)) fallbacks += 1;
    }
    assert.ok(fallbacks > 0 && fallbacks < 120, `the short form usually holds (${fallbacks} fallbacks in 3000)`);
    // Later attempts are different, valid and deterministic.
    const a1 = await displayHandle("ecd:cid:abc", at, 1);
    assert.ok(isEcdysisHandle(a1));
    assert.notEqual(a1, await displayHandle("ecd:cid:abc", at, 2));
    assert.equal(a1, await displayHandle("ecd:cid:abc", at, 1));
  });

  it("are never shared: a taken handle mints the next attempt", async () => {
    const store = new MemoryStore();
    let t = Date.UTC(2026, 9, 1, 9, 0, 0);
    const svc = new EcdysisService({ store, screeners: [structuralScreener()], sthPrivateKey: null, now: () => new Date((t += 1000)), reviewAll: false });
    const kp = await generateKeyPair();
    await svc.registerAgent({ handle: "Author-1", publicKey: kp.publicKey, operatorId: "op-a", constitution: { version: CONSTITUTION_VERSION, hash: await constitutionHash() } });
    for (let i = 0; i < 3; i++) await store.bumpAccepted("Author-1");
    const payload: Json = {
      protocol: "ecdysis/0.1", type: "paper", title: "A careful measurement of a benign quantity",
      abstract: "We measure a benign quantity with seeds and configs attached so anyone can recompute it.",
      field: "ml", claims: [{ text: "The quantity is within the stated interval", confidence: 0.7 }],
      builds_on: [{ id: "arxiv:1706.03762", rel: "background" }, { id: "arxiv:2201.02177", rel: "replicates" }],
      agent: { handle: "Author-1", publicKey: kp.publicKey }, ts: "2026-10-01T09:00:00Z",
    };
    const envelope = { payload, signature: await signJson(kp.privateKey, payload) };
    // Squat the handle this paper would get with a different paper record.
    const { contentId } = await import("../src/core/ids.js");
    const cid = await contentId(envelope as unknown as Json);
    const usual = await displayHandle(cid, new Date(t + 1000));
    await store.putPaper({ cid: "ecd:cid:" + "f".repeat(32), handle: usual, seq: 0, payload: payload as never, signature: "x" });
    const r = await svc.submitPaper(envelope);
    assert.equal(r.status, 201, JSON.stringify(r.body));
    const minted = String((r.body as Record<string, Json>)["id"]);
    assert.notEqual(minted, usual);
    assert.ok(isEcdysisHandle(minted));
    assert.equal((await store.getPaper(minted))!.cid, cid);
    assert.equal((await store.getPaper(usual))!.cid, "ecd:cid:" + "f".repeat(32), "the earlier paper keeps its handle");
  });
});
