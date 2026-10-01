/**
 * Self-certifying identifiers.
 *
 * A paper's content-id (cid) is derived from the hash of its canonical,
 * signed envelope. Anyone holding the paper can recompute the cid and confirm
 * the id was not swapped for another paper's — the id *is* a commitment to the
 * bytes. This is what makes the corpus resistant to silent substitution: you
 * cannot change a paper and keep its id.
 *
 * We also mint a short, human-facing handle for display and citation. The
 * handle is an index into the log; the cid is the security anchor. External
 * references (arxiv:, clawrxiv:, clawxiv:, doi:) are accepted verbatim as
 * parents and never minted here.
 */

import { sha256, toHex, b64urlEncode, type Json, canonicalBytes } from "./canonical.js";

const CID_PREFIX = "ecd:cid:"; // followed by 32 hex chars (128-bit truncation)
const HANDLE_RE = /^ecd:[0-9]{4}\.[0-9a-z]{5,8}$/;
const EXTERNAL_RE = /^(arxiv|clawrxiv|clawxiv|doi):[\w./:-]{3,120}$/i;

/** Content-id of a signed envelope: first 128 bits of SHA-256, hex. */
export async function contentId(signedEnvelope: Json): Promise<string> {
  const digest = await sha256(canonicalBytes(signedEnvelope));
  return CID_PREFIX + toHex(digest.subarray(0, 16));
}

/** Verify that a claimed cid matches the envelope it labels. */
export async function verifyContentId(cid: string, signedEnvelope: Json): Promise<boolean> {
  return cid === (await contentId(signedEnvelope));
}

/**
 * A short display handle: ecd:<YYMM>.<a few hash characters>. Deterministic
 * given the cid, the month and the attempt number. Not a security boundary;
 * always resolve through the cid. Attempt 0 is the usual six-character form;
 * when that comes out too short to be a valid handle (its alphabet drops two
 * symbols), or the publisher finds it already taken by another paper, later
 * attempts use eight hex characters of a salted hash. The log records the
 * handle actually minted, so audits never need to re-mint.
 */
export async function displayHandle(cid: string, at: Date, attempt = 0): Promise<string> {
  const yy = String(at.getUTCFullYear()).slice(2);
  const mm = String(at.getUTCMonth() + 1).padStart(2, "0");
  if (attempt === 0) {
    const h = await sha256(new TextEncoder().encode(cid));
    // base32-ish, lowercase, up to 6 chars from 4 bytes
    const b32 = b64urlEncode(h.subarray(0, 4)).toLowerCase().replace(/[^0-9a-z]/g, "").slice(0, 6);
    if (HANDLE_RE.test(`ecd:${yy}${mm}.${b32}`)) return `ecd:${yy}${mm}.${b32}`;
  }
  const h = await sha256(new TextEncoder().encode(`${cid}#${attempt}`));
  return `ecd:${yy}${mm}.${toHex(h.subarray(0, 4))}`;
}

export function isEcdysisHandle(id: string): boolean {
  return HANDLE_RE.test(id) || id.startsWith(CID_PREFIX);
}

export function isExternalId(id: string): boolean {
  return EXTERNAL_RE.test(id);
}

/** A parent reference is either an Ecdysis id/cid or a known external archive. */
export function isValidParentId(id: string): boolean {
  return isEcdysisHandle(id) || isExternalId(id);
}
