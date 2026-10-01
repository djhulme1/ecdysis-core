/**
 * Ed25519 identity for agents and for the log's Signed Tree Heads.
 *
 * Uses WebCrypto's native Ed25519, available on Node >= 20 and on Cloudflare
 * Workers, so the same code signs in the reference agent and verifies in the
 * Worker. Keys are exchanged as base64url: SPKI for public keys, PKCS#8 for
 * private keys. Private keys never leave the machine that generates them; the
 * server only ever sees public keys and signatures.
 */

import { b64urlDecode, b64urlEncode, canonicalBytes, type Json } from "./canonical.js";

const ALG = "Ed25519" as const;

export interface KeyPairB64 {
  publicKey: string; // base64url SPKI
  privateKey: string; // base64url PKCS#8
}

/** Generate a fresh Ed25519 keypair, exported as base64url strings. */
export async function generateKeyPair(): Promise<KeyPairB64> {
  const kp = (await crypto.subtle.generateKey({ name: ALG }, true, [
    "sign",
    "verify",
  ])) as CryptoKeyPair;
  const spki = new Uint8Array(await crypto.subtle.exportKey("spki", kp.publicKey));
  const pkcs8 = new Uint8Array(await crypto.subtle.exportKey("pkcs8", kp.privateKey));
  return { publicKey: b64urlEncode(spki), privateKey: b64urlEncode(pkcs8) };
}

/**
 * Diagnose a submitted public key before it is registered, so a bad
 * encoding fails loudly at registration instead of silently at every
 * later signature check. "raw32" is the common trap: libraries often hand
 * out the bare 32-byte Ed25519 key, not its SPKI wrapping.
 */
export async function publicKeyProblem(b64: string): Promise<null | "undecodable" | "raw32" | "not-ed25519-spki"> {
  let bytes: Uint8Array;
  try {
    bytes = b64urlDecode(b64);
  } catch {
    return "undecodable";
  }
  if (bytes.length === 32) return "raw32";
  try {
    await importPublic(b64);
    return null;
  } catch {
    return "not-ed25519-spki";
  }
}

async function importPublic(spkiB64: string): Promise<CryptoKey> {
  return crypto.subtle.importKey(
    "spki",
    b64urlDecode(spkiB64) as unknown as BufferSource,
    { name: ALG },
    false,
    ["verify"],
  );
}

async function importPrivate(pkcs8B64: string): Promise<CryptoKey> {
  return crypto.subtle.importKey(
    "pkcs8",
    b64urlDecode(pkcs8B64) as unknown as BufferSource,
    { name: ALG },
    false,
    ["sign"],
  );
}

/** Sign raw bytes; returns base64url signature. */
export async function signBytes(privateKeyB64: string, bytes: Uint8Array): Promise<string> {
  const key = await importPrivate(privateKeyB64);
  const sig = new Uint8Array(await crypto.subtle.sign({ name: ALG }, key, bytes as unknown as BufferSource));
  return b64urlEncode(sig);
}

/** Verify a base64url signature over raw bytes. Never throws; returns bool. */
export async function verifyBytes(
  publicKeyB64: string,
  bytes: Uint8Array,
  signatureB64: string,
): Promise<boolean> {
  try {
    const key = await importPublic(publicKeyB64);
    return await crypto.subtle.verify(
      { name: ALG },
      key,
      b64urlDecode(signatureB64) as unknown as BufferSource,
      bytes as unknown as BufferSource,
    );
  } catch {
    return false;
  }
}

/** Sign the canonical bytes of a JSON value. */
export async function signJson(privateKeyB64: string, value: Json): Promise<string> {
  return signBytes(privateKeyB64, canonicalBytes(value));
}

/** Verify a signature over the canonical bytes of a JSON value. */
export async function verifyJson(
  publicKeyB64: string,
  value: Json,
  signatureB64: string,
): Promise<boolean> {
  return verifyBytes(publicKeyB64, canonicalBytes(value), signatureB64);
}
