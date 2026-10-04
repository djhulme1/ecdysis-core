/**
 * Standard Webhooks (https://www.standardwebhooks.com, spec v1.0.0), as
 * Ecdysis signs what it sends to an address someone gave it: doorbell rings
 * to webhooks and trigger URLs, and MCP event deliveries.
 *
 * Every delivery carries three headers: webhook-id (unique per message,
 * kept across retries, never containing a full stop), webhook-timestamp
 * (Unix seconds) and webhook-signature, a space-separated list of
 * signatures over the exact bytes "<id>.<timestamp>.<body>":
 *  - "v1,<base64>": HMAC-SHA256 under a shared secret "whsec_<base64>"
 *    (24 to 64 random bytes). Every Standard Webhooks library verifies it,
 *    and so do no-code tools that can compute an HMAC.
 *  - "v1a,<base64>": Ed25519 under the Ecdysis log key, whose public half
 *    is published ("whpk_<base64>" is its raw 32 bytes). Nobody needs a
 *    shared secret to check it, but few libraries do it yet.
 * A receiver tries each signature until one verifies, and refuses a
 * timestamp more than five minutes from its own clock.
 *
 * Pure: no environment, no I/O; WebCrypto only.
 */

import { b64urlDecode, bufferSource } from "./canonical.js";

const te = new TextEncoder();

/** Standard (padded) base64, as Standard Webhooks writes signatures and secrets. */
export function toB64(bytes: Uint8Array): string {
  let bin = "";
  for (let i = 0; i < bytes.length; i++) bin += String.fromCharCode(bytes[i]!);
  return btoa(bin);
}

export function fromB64(s: string): Uint8Array | null {
  if (!/^[A-Za-z0-9+/]+={0,2}$/.test(s)) return null;
  try {
    const bin = atob(s);
    const out = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
    return out;
  } catch {
    return null;
  }
}

/** A fresh shared secret: "whsec_" and 32 random bytes in base64. */
export function newSecret(randomBytes: (n: number) => Uint8Array = (n) => crypto.getRandomValues(new Uint8Array(n))): string {
  return `whsec_${toB64(randomBytes(32))}`;
}

/** The key bytes of a "whsec_" secret, or null when it isn't one (Standard Webhooks: 24 to 64 bytes). */
export function secretBytes(secret: unknown): Uint8Array | null {
  if (typeof secret !== "string" || !secret.startsWith("whsec_") || secret.length > 200) return null;
  const b = fromB64(secret.slice(6));
  return b && b.length >= 24 && b.length <= 64 ? b : null;
}

/** What is signed: the id, the timestamp and the body, joined by full stops. */
export const signedContent = (id: string, timestamp: number, body: string) => `${id}.${timestamp}.${body}`;

/** "v1,<base64 HMAC-SHA256>" under a whsec_ secret. */
export async function signV1(secret: string, id: string, timestamp: number, body: string): Promise<string | null> {
  const key = secretBytes(secret);
  if (!key) return null;
  const k = await crypto.subtle.importKey("raw", bufferSource(key), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  return `v1,${toB64(new Uint8Array(await crypto.subtle.sign("HMAC", k, bufferSource(te.encode(signedContent(id, timestamp, body))))))}`;
}

/** "v1a,<base64 Ed25519>" under a PKCS#8 private key (base64url, as Ecdysis keeps keys). */
export async function signV1a(pkcs8B64url: string, id: string, timestamp: number, body: string): Promise<string> {
  const k = await crypto.subtle.importKey("pkcs8", bufferSource(b64urlDecode(pkcs8B64url)), { name: "Ed25519" }, false, ["sign"]);
  return `v1a,${toB64(new Uint8Array(await crypto.subtle.sign({ name: "Ed25519" }, k, bufferSource(te.encode(signedContent(id, timestamp, body))))))}`;
}

/**
 * The three headers for one delivery. At least one key must be given;
 * signatures are listed v1 first, as libraries that know only v1 expect.
 */
export async function standardHeaders(o: { id: string; timestamp: number; body: string; secret?: string | null; logKeyPkcs8?: string | null }): Promise<Record<string, string>> {
  if (o.id.includes(".") || !/^[A-Za-z0-9_-]{1,128}$/.test(o.id)) throw new Error("webhook-id: letters, digits, _ and - only");
  const sigs: string[] = [];
  if (o.secret) {
    const v1 = await signV1(o.secret, o.id, o.timestamp, o.body);
    if (v1) sigs.push(v1);
  }
  if (o.logKeyPkcs8) sigs.push(await signV1a(o.logKeyPkcs8, o.id, o.timestamp, o.body));
  if (!sigs.length) throw new Error("nothing to sign with");
  return { "webhook-id": o.id, "webhook-timestamp": String(o.timestamp), "webhook-signature": sigs.join(" ") };
}

/** Five minutes either way: what the reference libraries allow. */
export const TOLERANCE_S = 300;

/**
 * Check a delivery as a receiver would: a v1 signature under the secret, or
 * a v1a one under the public key, on a timestamp within tolerance.
 */
export async function verifyDelivery(o: {
  headers: Record<string, string>; body: string; nowS: number; secret?: string | null; publicKeySpkiB64url?: string | null;
}): Promise<boolean> {
  const id = o.headers["webhook-id"] ?? "";
  const ts = Number(o.headers["webhook-timestamp"]);
  if (!id || !Number.isInteger(ts) || Math.abs(o.nowS - ts) > TOLERANCE_S) return false;
  const content = te.encode(signedContent(id, ts, o.body));
  for (const s of (o.headers["webhook-signature"] ?? "").split(" ")) {
    const [v, sig] = s.split(",", 2);
    const bytes = sig ? fromB64(sig) : null;
    if (!bytes) continue;
    if (v === "v1" && o.secret) {
      const expected = await signV1(o.secret, id, ts, o.body);
      if (expected && timingSafeEqual(expected, s)) return true;
    }
    if (v === "v1a" && o.publicKeySpkiB64url) {
      try {
        const k = await crypto.subtle.importKey("spki", bufferSource(b64urlDecode(o.publicKeySpkiB64url)), { name: "Ed25519" }, false, ["verify"]);
        if (await crypto.subtle.verify({ name: "Ed25519" }, k, bufferSource(bytes), bufferSource(content))) return true;
      } catch {
        // an unreadable key verifies nothing
      }
    }
  }
  return false;
}

/** The log key's public half as Standard Webhooks writes an Ed25519 key: "whpk_" and its raw 32 bytes in base64. */
export function whpk(spkiB64url: string): string | null {
  try {
    const spki = b64urlDecode(spkiB64url);
    // Ed25519 SPKI is a fixed 12-byte prefix and the 32-byte key.
    return spki.length === 44 ? `whpk_${toB64(spki.slice(12))}` : null;
  } catch {
    return null;
  }
}

function timingSafeEqual(a: string, b: string): boolean {
  if (a.length !== b.length) return false;
  let d = 0;
  for (let i = 0; i < a.length; i++) d |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return d === 0;
}
