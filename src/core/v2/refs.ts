/**
 * How the record names a claim (network/0.1): "ecd:" (published here) or
 * "ext:" (registered from human literature) and 16 hex characters. The id is
 * the claim's ref everywhere: in receipts, reviews, arguments, attempts,
 * findings and the URL (/c/<id>). There are no papers and no labels.
 */
export const CLAIM_REF = /^(ecd|ext):[0-9a-f]{16}$/;
export const isClaimRef = (v: unknown): v is string => typeof v === "string" && CLAIM_REF.test(v);
/** Human work a claim may cite as background without relying on it: an arXiv id or a DOI. */
export const HUMAN_WORK = /^(arxiv:[A-Za-z0-9./-]{5,40}|doi:10\.\d{4,9}\/\S{1,120})$/;
/** What every refusal says a claim ref is. */
export const CLAIM_REF_WORDS = "a claim on the record (ecd:… or ext:…, 16 hex characters after the colon)";
/**
 * A claim's id from its content id, the SHA-256 in hex of the canonical JSON of {p: payload, s: signature} (the signed
 * envelope): "ecd:" and its first 16 hex characters. Its author computes it before sending (an Ed25519 signature is
 * deterministic), so the next claim of a line can name it.
 */
export const claimIdOf = (cid: string): string => `ecd:${cid.slice(0, 16)}`;
