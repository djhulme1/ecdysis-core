import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { TransparencyLog } from "../src/core/log.js";
import { MemoryStore } from "../src/store/memory-store.js";
import { generateKeyPair } from "../src/core/crypto.js";

function fixedClock(): () => Date {
  let t = Date.UTC(2026, 8, 30, 8, 0, 0);
  return () => new Date((t += 1000));
}

describe("transparency log", () => {
  it("appends, proves inclusion, and stays consistent as it grows", async () => {
    const store = new MemoryStore();
    const log = new TransparencyLog(store, fixedClock());
    const roots: string[] = [await log.root(0)];
    for (let i = 0; i < 17; i++) {
      await log.append("claim.publish", { id: `ecd:${i.toString(16).padStart(16, "0")}` });
      roots.push(await log.root());
    }
    // Inclusion of every entry in the final tree.
    const n = await log.size();
    const finalRoot = await log.root(n);
    for (let i = 0; i < n; i++) {
      const { proof, treeSize } = await log.proveInclusion(i);
      const row = await store.getEntry(i);
      assert.equal(
        await TransparencyLog.verifyEntryInclusion(row!.entry, proof, treeSize, finalRoot),
        true,
        `inclusion of entry ${i}`,
      );
    }
    // Consistency between every earlier size and now.
    for (let m = 0; m <= n; m++) {
      const proof = await log.proveConsistency(m, n);
      assert.equal(
        await TransparencyLog.verifyLogConsistency(m, n, roots[m]!, finalRoot, proof),
        true,
        `consistency ${m} -> ${n}`,
      );
    }
  });

  it("signs tree heads that verify with the public key only", async () => {
    const store = new MemoryStore();
    const log = new TransparencyLog(store, fixedClock());
    await log.append("claim.publish", { id: "ecd:0000000000000000" });
    const kp = await generateKeyPair();
    const sth = await log.signedTreeHead(kp.privateKey);
    assert.equal(await TransparencyLog.verifySth(kp.publicKey, sth), true);
    assert.equal(
      await TransparencyLog.verifySth(kp.publicKey, { ...sth, treeSize: sth.treeSize + 1 }),
      false,
      "an altered STH must not verify",
    );
  });

  it("audit detects tampering with entries, chain order, and leaf hashes", async () => {
    const mk = async () => {
      const store = new MemoryStore();
      const log = new TransparencyLog(store, fixedClock());
      for (let i = 0; i < 8; i++) await log.append("claim.publish", { id: `ecd:${i.toString(16).padStart(16, "0")}` });
      return { store, log };
    };

    {
      const { store, log } = await mk();
      assert.equal(await log.audit(), null, "an untouched log audits clean");
      store._tamper(3, (row) => {
        row.entry.payloadHash = "0".repeat(64);
      });
      assert.match((await log.audit())!, /hash mismatch|breaks the chain/);
    }
    {
      const { store, log } = await mk();
      store._tamper(5, (row) => {
        row.entry.prevHash = "f".repeat(64);
      });
      assert.match((await log.audit())!, /breaks the chain|hash mismatch/);
    }
    {
      const { store, log } = await mk();
      store._tamper(2, (row) => {
        row.leafHash = "a".repeat(64);
      });
      assert.match((await log.audit())!, /leaf hash 2 mismatch/);
    }
  });
});
