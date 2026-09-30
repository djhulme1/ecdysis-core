/**
 * RFC 6962 Merkle tree: roots, inclusion proofs, and consistency proofs.
 *
 * This is the machinery behind Ecdysis's central integrity claim: the record
 * of papers, claims and replications is append-only, and anyone can check it.
 *
 *  - An *inclusion proof* shows a specific entry is in the tree with a given
 *    root, in O(log n) hashes.
 *  - A *consistency proof* shows that the tree at size n is an extension of
 *    the tree at size m < n — nothing already logged was altered or removed.
 *    Auditors fetch Signed Tree Heads over time and verify consistency
 *    between them; a single failure is public, undeniable proof of tampering.
 *
 * Domain separation follows RFC 6962: leaves are hashed with a 0x00 prefix and
 * internal nodes with 0x01, so a leaf can never be reinterpreted as a node.
 */

import { sha256 } from "./canonical.js";

const LEAF = 0x00;
const NODE = 0x01;

export type Hash = Uint8Array;

/** Hash of the empty tree: SHA-256 of the empty string. */
export function emptyRoot(): Promise<Hash> {
  return sha256(new Uint8Array(0));
}

/** Leaf hash: SHA-256(0x00 || entry). */
export async function leafHash(entry: Uint8Array): Promise<Hash> {
  const buf = new Uint8Array(1 + entry.length);
  buf[0] = LEAF;
  buf.set(entry, 1);
  return sha256(buf);
}

/** Internal node hash: SHA-256(0x01 || left || right). */
export async function nodeHash(left: Hash, right: Hash): Promise<Hash> {
  const buf = new Uint8Array(1 + left.length + right.length);
  buf[0] = NODE;
  buf.set(left, 1);
  buf.set(right, 1 + left.length);
  return sha256(buf);
}

function eq(a: Hash, b: Hash): boolean {
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a[i]! ^ b[i]!;
  return diff === 0;
}

/** Largest power of two strictly less than n (n >= 2). */
function splitPoint(n: number): number {
  let k = 1;
  while (k << 1 < n) k <<= 1;
  return k;
}

/** Merkle Tree Hash of leaf hashes[start:end]. */
export async function merkleRoot(hashes: Hash[], start = 0, end = hashes.length): Promise<Hash> {
  const n = end - start;
  if (n === 0) return emptyRoot();
  if (n === 1) return hashes[start]!;
  const k = splitPoint(n);
  const [l, r] = await Promise.all([
    merkleRoot(hashes, start, start + k),
    merkleRoot(hashes, start + k, end),
  ]);
  return nodeHash(l, r);
}

/** Inclusion proof (audit path) for leaf `m` in leaves[start:end]. */
export async function inclusionProof(
  hashes: Hash[],
  m: number,
  start = 0,
  end = hashes.length,
): Promise<Hash[]> {
  const n = end - start;
  if (n <= 1) return [];
  const k = splitPoint(n);
  if (m < k) {
    const path = await inclusionProof(hashes, m, start, start + k);
    path.push(await merkleRoot(hashes, start + k, end));
    return path;
  } else {
    const path = await inclusionProof(hashes, m - k, start + k, end);
    path.push(await merkleRoot(hashes, start, start + k));
    return path;
  }
}

/**
 * Recompute a root from an inclusion proof (RFC 6962 §2.1.1). Returns the root
 * the proof implies, or null if the proof is malformed. Callers compare the
 * result against a trusted Signed Tree Head.
 */
export async function rootFromInclusionProof(
  leafIndex: number,
  treeSize: number,
  leaf: Hash,
  proof: Hash[],
): Promise<Hash | null> {
  if (leafIndex >= treeSize || leafIndex < 0) return null;
  let fn = leafIndex;
  let sn = treeSize - 1;
  let r = leaf;
  for (const p of proof) {
    if (sn === 0) return null; // proof too long
    if ((fn & 1) === 1 || fn === sn) {
      r = await nodeHash(p, r);
      while ((fn & 1) === 0 && fn !== 0) {
        fn >>= 1;
        sn >>= 1;
      }
    } else {
      r = await nodeHash(r, p);
    }
    fn >>= 1;
    sn >>= 1;
  }
  return sn === 0 ? r : null; // proof too short if sn != 0
}

export async function verifyInclusion(
  leafIndex: number,
  treeSize: number,
  leaf: Hash,
  proof: Hash[],
  root: Hash,
): Promise<boolean> {
  const r = await rootFromInclusionProof(leafIndex, treeSize, leaf, proof);
  return r !== null && eq(r, root);
}

/** Consistency proof between sizes `first` and `second` (RFC 6962 §2.1.2). */
export async function consistencyProof(hashes: Hash[], first: number, second: number): Promise<Hash[]> {
  if (first < 0 || first > second || second > hashes.length) {
    throw new Error("consistencyProof: bad sizes");
  }
  if (first === 0 || first === second) return [];
  return subproof(hashes, first, 0, second, true);
}

async function subproof(
  hashes: Hash[],
  m: number,
  start: number,
  end: number,
  b: boolean,
): Promise<Hash[]> {
  const n = end - start;
  if (m === n) {
    return b ? [] : [await merkleRoot(hashes, start, end)];
  }
  const k = splitPoint(n);
  if (m <= k) {
    const proof = await subproof(hashes, m, start, start + k, b);
    proof.push(await merkleRoot(hashes, start + k, end));
    return proof;
  } else {
    const proof = await subproof(hashes, m - k, start + k, end, false);
    proof.push(await merkleRoot(hashes, start, start + k));
    return proof;
  }
}

/**
 * Verify a consistency proof (RFC 6962 §2.1.2 verification algorithm). Given
 * the two tree sizes and their roots, returns true iff the proof shows the
 * larger tree is an append-only extension of the smaller one.
 */
export async function verifyConsistency(
  first: number,
  second: number,
  firstRoot: Hash,
  secondRoot: Hash,
  proof: Hash[],
): Promise<boolean> {
  if (first > second) return false;
  if (first === second) return proof.length === 0 && eq(firstRoot, secondRoot);
  if (first === 0) return proof.length === 0; // any tree extends the empty tree

  // Work on a local copy; step 1 may prepend first_hash.
  let path = proof.slice();
  if (isPowerOfTwo(first)) path = [firstRoot, ...path];
  if (path.length === 0) return false;

  let fn = first - 1;
  let sn = second - 1;
  // Step 3: shift while LSB(fn) set.
  while (fn & 1) {
    fn >>= 1;
    sn >>= 1;
  }

  let fr = path[0]!;
  let sr = path[0]!;
  for (let i = 1; i < path.length; i++) {
    if (sn === 0) return false;
    const c = path[i]!;
    if (fn & 1 || fn === sn) {
      fr = await nodeHash(c, fr);
      sr = await nodeHash(c, sr);
      while ((fn & 1) === 0 && fn !== 0) {
        fn >>= 1;
        sn >>= 1;
      }
    } else {
      sr = await nodeHash(sr, c);
    }
    fn >>= 1;
    sn >>= 1;
  }

  return sn === 0 && eq(fr, firstRoot) && eq(sr, secondRoot);
}

function isPowerOfTwo(n: number): boolean {
  return n > 0 && (n & (n - 1)) === 0;
}

export const _internal = { eq, splitPoint, isPowerOfTwo };
