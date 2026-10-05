import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { canonicalize, hashJson } from "../src/core/canonical.js";
import { generateKeyPair, signJson, verifyJson } from "../src/core/crypto.js";
import { sanitizeText } from "../src/core/sanitize.js";

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
