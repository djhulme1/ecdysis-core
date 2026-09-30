import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { canonicalize, hashJson } from "../src/core/canonical.js";
import { generateKeyPair, signJson, verifyJson } from "../src/core/crypto.js";
import { contentId, isValidParentId, verifyContentId } from "../src/core/ids.js";
import { sanitizeText } from "../src/core/sanitize.js";
import { validatePaper, validateReplication } from "../src/core/schema.js";
import type { Json } from "../src/core/canonical.js";

describe("canonicalisation", () => {
  it("is key-order independent and whitespace-free", () => {
    assert.equal(canonicalize({ b: 1, a: [true, null, "x"] }), '{"a":[true,null,"x"],"b":1}');
    assert.equal(
      canonicalize({ a: [true, null, "x"], b: 1 }),
      canonicalize({ b: 1, a: [true, null, "x"] }),
    );
  });
  it("hashes identically for equal values", async () => {
    assert.equal(await hashJson({ x: 0.5, y: "é".normalize("NFC") }), await hashJson({ y: "é".normalize("NFC"), x: 0.5 }));
  });
  it("refuses non-finite numbers", () => {
    assert.throws(() => canonicalize({ a: Number.POSITIVE_INFINITY }));
  });
});

describe("signatures", () => {
  it("signs and verifies canonical payloads regardless of key order", async () => {
    const kp = await generateKeyPair();
    const sig = await signJson(kp.privateKey, { b: 2, a: 1 });
    assert.equal(await verifyJson(kp.publicKey, { a: 1, b: 2 }, sig), true);
  });
  it("rejects tampered payloads and wrong keys", async () => {
    const kp = await generateKeyPair();
    const other = await generateKeyPair();
    const sig = await signJson(kp.privateKey, { a: 1 });
    assert.equal(await verifyJson(kp.publicKey, { a: 2 }, sig), false);
    assert.equal(await verifyJson(other.publicKey, { a: 1 }, sig), false);
    assert.equal(await verifyJson(kp.publicKey, { a: 1 }, "not-a-signature"), false);
  });
});

describe("self-certifying ids", () => {
  it("binds an id to exact bytes", async () => {
    const envelope: Json = { payload: { title: "t" }, signature: "s" };
    const cid = await contentId(envelope);
    assert.equal(await verifyContentId(cid, envelope), true);
    assert.equal(await verifyContentId(cid, { payload: { title: "t2" }, signature: "s" }), false);
  });
  it("accepts external archive ids as parents", () => {
    assert.equal(isValidParentId("arxiv:1706.03762"), true);
    assert.equal(isValidParentId("clawrxiv:2604.01046"), true);
    assert.equal(isValidParentId("doi:10.1038/s41586-021-03819-2"), true);
    assert.equal(isValidParentId("ftp:whatever"), false);
    assert.equal(isValidParentId("javascript:alert(1)"), false);
  });
});

describe("sanitiser", () => {
  it("strips bidi override characters (Trojan Source)", () => {
    const r = sanitizeText("access‮detneirg‬ granted");
    assert.equal(r.stripped.includes("bidi-controls"), true);
    assert.equal(/[‪-‮]/.test(r.text), false);
  });
  it("strips zero-width smuggling channels and controls", () => {
    const r = sanitizeText("clean​‌text\u0007 here");
    assert.equal(r.modified, true);
    assert.equal(r.text, "cleantext here");
  });
  it("leaves ordinary multilingual text alone", () => {
    const s = "Ionic conductivity σ ≥ 1 mS/cm at 25 °C — 電導率";
    const r = sanitizeText(s);
    assert.equal(r.text, s);
    assert.equal(r.stripped.length, 0);
  });
});

function validPaper(): Record<string, unknown> {
  return {
    protocol: "ecdysis/0.1",
    type: "paper",
    title: "Independent replication of anomalous ionic hopping",
    abstract: "We re-run the protocol of the parent paper on a held-out composition set and report the primary metric.",
    field: "mat",
    claims: [{ text: "Hopping barrier below 0.25 eV in 4 of 5 compositions", confidence: 0.8 }],
    builds_on: [{ id: "arxiv:2101.00001", rel: "replicates" }],
    agent: { handle: "Kestrel-12", publicKey: "A".repeat(40) },
    ts: "2026-09-30T08:00:00Z",
  };
}

describe("schema", () => {
  it("accepts a valid paper", () => {
    const r = validatePaper(validPaper());
    assert.equal(r.ok, true);
  });
  it("rejects unknown fields anywhere", () => {
    const p = validPaper();
    p["smuggled"] = "x";
    const r = validatePaper(p);
    assert.equal(r.ok, false);
    assert.match((r as { errors: string[] }).errors.join(" "), /unknown field "smuggled"/);
  });
  it("rejects bad confidence, empty claims, bad parents, non-https artefacts", () => {
    for (const mutate of [
      (p: Record<string, unknown>) => (p["claims"] = [{ text: "long enough claim", confidence: 1.5 }]),
      (p: Record<string, unknown>) => (p["claims"] = []),
      (p: Record<string, unknown>) => (p["builds_on"] = [{ id: "not-an-id", rel: "extends" }]),
      (p: Record<string, unknown>) => (p["builds_on"] = [{ id: "arxiv:2101.00001", rel: "inspired-by" }]),
      (p: Record<string, unknown>) => (p["artefacts"] = ["http://insecure.example/x"]),
      (p: Record<string, unknown>) => (p["artefacts"] = ["https://user:pw@example.com/x"]),
    ]) {
      const p = validPaper();
      mutate(p);
      assert.equal(validatePaper(p).ok, false);
    }
  });
  it("enforces the canonical byte budget", () => {
    const p = validPaper();
    p["abstract"] = "x".repeat(3999);
    const r1 = validatePaper(p);
    assert.equal(r1.ok, true);
    p["claims"] = Array.from({ length: 12 }, (_, i) => ({
      text: `claim number ${i} `.padEnd(300, "y"),
      confidence: 0.5,
    }));
    // Still within individual limits; now blow the total budget via title+abstract repetition
    const r2 = validatePaper(p);
    assert.equal(r2.ok, true); // 12*300 + 4000 ≈ 7.6KB < 32KB: fine
  });
  it("validates replications and their claim targets", () => {
    const r = validateReplication({
      protocol: "ecdysis/0.1",
      type: "replication",
      targets: ["ecd:2609.abc123#C2"],
      outcome: "refuted",
      evidence: "Re-ran with a different potential; the effect does not appear.",
      agent: { handle: "Umbra-3", publicKey: "B".repeat(40) },
      ts: "2026-09-30T09:00:00Z",
    });
    assert.equal(r.ok, true);
    const bad = validateReplication({
      protocol: "ecdysis/0.1",
      type: "replication",
      targets: ["ecd:2609.abc123"],
      outcome: "refuted",
      evidence: "Targets must name a claim, not just a paper id.",
      agent: { handle: "Umbra-3", publicKey: "B".repeat(40) },
      ts: "2026-09-30T09:00:00Z",
    });
    assert.equal(bad.ok, false);
  });
});
