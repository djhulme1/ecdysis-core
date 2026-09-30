/**
 * Deterministic serialisation and hashing.
 *
 * Every signature and every content-address in Ecdysis is taken over the
 * *canonical* bytes of a value, not over whatever JSON a client happened to
 * send. Two agents that encode the same object must produce identical bytes,
 * or signatures would not verify and ids would not match. We use a subset of
 * JSON Canonicalisation Scheme (RFC 8785): object keys sorted by UTF-16 code
 * unit, no insignificant whitespace, and ECMAScript number formatting (which
 * `JSON.stringify` already implements for a single number).
 *
 * The functions here are pure and identical on Node and on Cloudflare Workers.
 */

export type Json =
  | null
  | boolean
  | number
  | string
  | Json[]
  | { [k: string]: Json };

/** Serialise `value` to canonical JSON text. Throws on non-finite numbers. */
export function canonicalize(value: Json): string {
  return encode(value);
}

function encode(v: Json): string {
  if (v === null) return "null";
  const t = typeof v;
  if (t === "boolean") return v ? "true" : "false";
  if (t === "number") {
    if (!Number.isFinite(v as number)) {
      throw new Error("canonicalize: non-finite number is not representable");
    }
    // JSON.stringify of a lone number is exactly the ECMAScript Number->String
    // algorithm that RFC 8785 mandates.
    return JSON.stringify(v);
  }
  if (t === "string") return JSON.stringify(v);
  if (Array.isArray(v)) {
    return "[" + v.map(encode).join(",") + "]";
  }
  if (t === "object") {
    const obj = v as { [k: string]: Json };
    const keys = Object.keys(obj).sort(compareCodeUnits);
    const parts: string[] = [];
    for (const k of keys) {
      const val = obj[k];
      if (val === undefined) continue; // undefined is not JSON; skip
      parts.push(JSON.stringify(k) + ":" + encode(val));
    }
    return "{" + parts.join(",") + "}";
  }
  throw new Error(`canonicalize: unsupported type ${t}`);
}

/** RFC 8785 sorts by UTF-16 code unit, which is what `<` on JS strings does. */
function compareCodeUnits(a: string, b: string): number {
  return a < b ? -1 : a > b ? 1 : 0;
}

const enc = new TextEncoder();

/** Canonical UTF-8 bytes of a value. */
export function canonicalBytes(value: Json): Uint8Array {
  return enc.encode(canonicalize(value));
}

/** Lowercase hex of a byte array. */
export function toHex(bytes: Uint8Array): string {
  let s = "";
  for (let i = 0; i < bytes.length; i++) {
    s += bytes[i]!.toString(16).padStart(2, "0");
  }
  return s;
}

/** Parse lowercase/uppercase hex to bytes. Throws on odd length or non-hex. */
export function fromHex(hex: string): Uint8Array {
  if (hex.length % 2 !== 0) throw new Error("fromHex: odd-length string");
  const out = new Uint8Array(hex.length / 2);
  for (let i = 0; i < out.length; i++) {
    const byte = Number.parseInt(hex.slice(i * 2, i * 2 + 2), 16);
    if (Number.isNaN(byte)) throw new Error("fromHex: invalid hex");
    out[i] = byte;
  }
  return out;
}

/**
 * Coerce a Uint8Array to the BufferSource type WebCrypto wants. Recent TS libs
 * type `Uint8Array` as generic over `ArrayBufferLike` (it might be backed by a
 * SharedArrayBuffer), which is not assignable to `BufferSource`; at runtime our
 * arrays are always plain-buffer-backed, so this cast is sound.
 */
export function bufferSource(bytes: Uint8Array): BufferSource {
  return bytes as unknown as BufferSource;
}

/** SHA-256 of raw bytes, returned as bytes. */
export async function sha256(bytes: Uint8Array): Promise<Uint8Array> {
  const digest = await crypto.subtle.digest("SHA-256", bufferSource(bytes));
  return new Uint8Array(digest);
}

/** SHA-256 of a value's canonical bytes, as lowercase hex. */
export async function hashJson(value: Json): Promise<string> {
  return toHex(await sha256(canonicalBytes(value)));
}

/** URL-safe base64 without padding (used for keys and signatures). */
export function b64urlEncode(bytes: Uint8Array): string {
  let bin = "";
  for (let i = 0; i < bytes.length; i++) bin += String.fromCharCode(bytes[i]!);
  return btoa(bin).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

export function b64urlDecode(s: string): Uint8Array {
  const pad = s.length % 4 === 0 ? "" : "=".repeat(4 - (s.length % 4));
  const bin = atob(s.replace(/-/g, "+").replace(/_/g, "/") + pad);
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}
