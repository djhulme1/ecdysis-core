import { describe, it } from "node:test";
import assert from "node:assert/strict";
import {
  consistencyProof, emptyRoot, inclusionProof, leafHash, merkleRoot,
  verifyConsistency, verifyInclusion,
} from "../src/core/merkle.js";
import { toHex } from "../src/core/canonical.js";

const enc = new TextEncoder();

async function leaves(n: number): Promise<Uint8Array[]> {
  const out: Uint8Array[] = [];
  for (let i = 0; i < n; i++) out.push(await leafHash(enc.encode(`entry-${i}`)));
  return out;
}

describe("RFC 6962 known vectors", () => {
  it("empty tree root is SHA-256 of the empty string", async () => {
    assert.equal(
      toHex(await emptyRoot()),
      "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    );
  });
  it("leaf hash of the empty leaf matches the CT test vector", async () => {
    assert.equal(
      toHex(await leafHash(new Uint8Array(0))),
      "6e340b9cffb37a989ca544e6bb780a2c78901d3fb33738768511a30617afa01d",
    );
  });
});

describe("inclusion proofs", () => {
  it("verify for every leaf at every tree size up to 40", async () => {
    const max = 40;
    const ls = await leaves(max);
    for (let n = 1; n <= max; n++) {
      const root = await merkleRoot(ls, 0, n);
      for (let m = 0; m < n; m++) {
        const proof = await inclusionProof(ls.slice(0, n), m);
        assert.equal(
          await verifyInclusion(m, n, ls[m]!, proof, root),
          true,
          `inclusion failed at m=${m}, n=${n}`,
        );
      }
    }
  });

  it("fails for the wrong leaf, wrong index, truncated and padded proofs", async () => {
    const ls = await leaves(13);
    const n = 13, m = 5;
    const root = await merkleRoot(ls);
    const proof = await inclusionProof(ls, m);
    assert.equal(await verifyInclusion(m, n, ls[6]!, proof, root), false, "wrong leaf");
    assert.equal(await verifyInclusion(6, n, ls[m]!, proof, root), false, "wrong index");
    assert.equal(await verifyInclusion(m, n, ls[m]!, proof.slice(1), root), false, "truncated");
    assert.equal(
      await verifyInclusion(m, n, ls[m]!, [...proof, proof[0]!], root),
      false,
      "padded",
    );
  });
});

describe("consistency proofs", () => {
  it("verify for every (first, second) pair up to size 40", async () => {
    const max = 40;
    const ls = await leaves(max);
    const roots: Uint8Array[] = [];
    for (let n = 0; n <= max; n++) roots.push(await merkleRoot(ls, 0, n));
    for (let second = 0; second <= max; second++) {
      for (let first = 0; first <= second; first++) {
        const proof = await consistencyProof(ls.slice(0, second), first, second);
        assert.equal(
          await verifyConsistency(first, second, roots[first]!, roots[second]!, proof),
          true,
          `consistency failed at first=${first}, second=${second}`,
        );
      }
    }
  });

  it("detects a rewritten history (fork)", async () => {
    const honest = await leaves(20);
    // The attacker rewrites entry 7 after an STH at size 12 was published.
    const forged = honest.slice();
    forged[7] = await leafHash(enc.encode("rewritten"));
    const oldRoot = await merkleRoot(honest, 0, 12);
    const newRootForged = await merkleRoot(forged, 0, 20);
    const forgedProof = await consistencyProof(forged, 12, 20);
    assert.equal(
      await verifyConsistency(12, 20, oldRoot, newRootForged, forgedProof),
      false,
      "a forged history must not verify against the honest old root",
    );
  });

  it("rejects a proof for mismatched sizes", async () => {
    const ls = await leaves(10);
    const proof = await consistencyProof(ls, 4, 10);
    const r4 = await merkleRoot(ls, 0, 4);
    const r10 = await merkleRoot(ls, 0, 10);
    assert.equal(await verifyConsistency(5, 10, r4, r10, proof), false);
    assert.equal(await verifyConsistency(4, 9, r4, await merkleRoot(ls, 0, 9), proof), false);
  });
});
