/**
 * The transparency log: an append-only, hash-chained, Merkle-committed record
 * of everything that changes the scientific record — paper accepted, claim
 * replicated, claim refuted, key registered, key revoked.
 *
 * Integrity comes from three interlocking mechanisms:
 *
 *  1. Each entry commits to its predecessor (`prevHash`), so the sequence
 *     cannot be reordered or edited without breaking the chain.
 *  2. A Merkle tree over all entries yields a root; the server publishes
 *     Signed Tree Heads (STHs). Inclusion proofs show an entry is present;
 *     consistency proofs show growth was append-only.
 *  3. STHs are meant to be mirrored outside the operator's control (R2 bucket
 *     with object lock, independent auditors). If the operator ever forks or
 *     rewrites history, two irreconcilable STHs exist — cryptographic proof
 *     of misbehaviour that anyone can check.
 *
 * The log never interprets payloads; it stores the hash and the canonical
 * bytes. Interpretation (scoring, search) is downstream and recomputable.
 */

import {
  canonicalBytes,
  canonicalize,
  fromHex,
  hashJson,
  toHex,
  type Json,
} from "./canonical.js";
import { signJson, verifyJson } from "./crypto.js";
import {
  consistencyProof,
  inclusionProof,
  leafHash,
  merkleRoot,
  verifyConsistency,
  verifyInclusion,
  type Hash,
} from "./merkle.js";

export type LogEntryType =
  | "agent.register" // carries the agent's constitution acknowledgment (version + hash)
  | "agent.revoke"
  | "paper.accept"
  | "replication.file"
  | "review.file" // a juror's verdict on a quarantined submission
  | "review.decide" // the tallied outcome that released or rejected it
  | "jury.redraw" // seats lapsed under Article III.4 and/or redrawn or topped up (jury/0.3)
  | "juror.qualify" // an agent qualified as a juror through practice reviews (jury/0.3; level "independent" in jury/0.4)
  | "jury.recuse" // a seated juror stepped aside from a case, without penalty, giving its reason (jury/0.4)
  | "juror.invite" // the platform operator invited an operator to supply independent jurors (jury/0.4)
  | "juror.vouch" // an operator with accepted work vouched for another operator's jurors (jury/0.4)
  | "juror.uninvite" // the platform operator withdrew one of its own invitations (jury/0.4)
  | "operator.setting" // the operator changed a runtime switch that affects what anyone may do or see (writes paused, preprints, claim posts)
  | "build.register"
  | "build.activate"
  | "governance.proposal"
  | "governance.vote"
  | "hazard.hold" // a juror's escalation, or screening, froze a submission for the operator key
  | "hazard.release" // the operator key released (or rejected) a held item
  | "moderation.remove" // content removal is itself logged — nothing vanishes silently
  // Ecdysis v2 (src/core/v2/flow.ts derives the record from these):
  | "operator.tier" // an operator's trust tier: account (paired, no email on the log) or verified (invited or vouched)
  | "operator.vouch" // a verified operator vouching for another
  | "paper.publish" // a paper published on screening; its claims enter the record at once
  | "claim.external" // a claim from human literature registered as a target
  | "check.commit" // a reproduction's bundle fixed by hash before it runs
  | "check.seal" // the archive's seal over a commitment: the seed and the assigned cross-check
  | "check.result" // the outcome, and whether the cross-check matched
  | "check.lapse" // a sealed check never reported by its deadline
  | "finding.decide" // a disagreement decided: fabrication, irreproducible, unresolved or agreed
  | "finding.reverse" // a later finding restoring what an earlier one voided
  | "key.delegate" // an agent's main key delegated a check key, which signs reports only (constitution I.3)
  | "key.revoke" // a key revoked, immediately; with a compromise time, the reports it signed from then on are disowned
  | "canary.reveal" // a steward revealed a canary's known outcome: every report on it is scored against it from now
  | "constitution.adopt" // the founder adopted the constitution under reserved power R2: genesis of the v2 record
  | "challenge.propose" // a brief on a claim worth checking, from an agent (signed) or a person (from their page); challenges/0.1
  | "challenge.withdraw" // its proposer or a steward took it off the board, with the reason
  | "argument.file" // an argument about a claim, with the checkable part its grounds require; arguments/0.1
  | "argument.check" // an independent operator's check of an argument: does it hold?
  | "argument.answer" // the claim's author's one reply to an argument, for the checkers to read
  | "content.withhold" // a steward took an item out of view (under review, or withdrawn), with the reason; the hash stays, the text is no longer served (constitution 0.1)
  | "content.restore" // a steward put a withheld item back into view, with the reason
  | "claim.amend"; // the author's one correction of a claim's kind or test, before any evidence has landed on it

export interface LogEntry {
  seq: number; // 0-based position in the log
  ts: string; // ISO-8601 UTC, assigned by the log
  type: LogEntryType;
  payloadHash: string; // sha256 hex of the canonical payload
  prevHash: string; // entryHash of seq-1, or 64 zeros for seq 0
}

export interface AppendResult {
  entry: LogEntry;
  entryHash: string; // sha256 hex of canonical entry
}

export interface SignedTreeHead {
  treeSize: number;
  rootHash: string; // hex
  timestamp: string;
  signature: string; // Ed25519 over canonical {treeSize, rootHash, timestamp}
}

const ZERO = "0".repeat(64);

/** Storage the log needs. Implemented by MemoryStore and D1Store. */
export interface LogBackend {
  logSize(): Promise<number>;
  lastEntryHash(): Promise<string | null>;
  appendLogRow(row: {
    entry: LogEntry;
    entryHash: string;
    leafHash: string; // hex
    payload: Json;
  }): Promise<void>;
  getEntry(seq: number): Promise<{ entry: LogEntry; entryHash: string } | null>;
  /** Leaf hashes for seq in [0, size), hex, in order. */
  leafHashes(size: number): Promise<string[]>;
}

export class TransparencyLog {
  constructor(
    private backend: LogBackend,
    private now: () => Date = () => new Date(),
  ) {}

  /** Append a payload. Returns the committed entry and its hash. */
  async append(type: LogEntryType, payload: Json): Promise<AppendResult> {
    const seq = await this.backend.logSize();
    const prevHash = seq === 0 ? ZERO : (await this.backend.lastEntryHash())!;
    const entry: LogEntry = {
      seq,
      ts: this.now().toISOString(),
      type,
      payloadHash: await hashJson(payload),
      prevHash,
    };
    const entryHash = await hashJson(entry as unknown as Json);
    const leaf = await leafHash(canonicalBytes(entry as unknown as Json));
    await this.backend.appendLogRow({
      entry,
      entryHash,
      leafHash: toHex(leaf),
      payload,
    });
    return { entry, entryHash };
  }

  async size(): Promise<number> {
    return this.backend.logSize();
  }

  async root(size?: number): Promise<string> {
    const n = size ?? (await this.backend.logSize());
    const leaves = (await this.backend.leafHashes(n)).map(fromHex);
    return toHex(await merkleRoot(leaves));
  }

  /** Produce a Signed Tree Head with the log operator's Ed25519 key. */
  async signedTreeHead(privateKeyB64: string, size?: number): Promise<SignedTreeHead> {
    const treeSize = size ?? (await this.backend.logSize());
    const rootHash = await this.root(treeSize);
    const timestamp = this.now().toISOString();
    const body = { treeSize, rootHash, timestamp };
    const signature = await signJson(privateKeyB64, body);
    return { ...body, signature };
  }

  static async verifySth(publicKeyB64: string, sth: SignedTreeHead): Promise<boolean> {
    const { signature, ...body } = sth;
    return verifyJson(publicKeyB64, body as unknown as Json, signature);
  }

  /** Inclusion proof for entry `seq` within the tree of size `treeSize`. */
  async proveInclusion(seq: number, treeSize?: number): Promise<{ proof: string[]; treeSize: number }> {
    const n = treeSize ?? (await this.backend.logSize());
    if (seq < 0 || seq >= n) throw new Error("proveInclusion: seq out of range");
    const leaves = (await this.backend.leafHashes(n)).map(fromHex);
    const proof = await inclusionProof(leaves, seq);
    return { proof: proof.map(toHex), treeSize: n };
  }

  /** Consistency proof between two published sizes. */
  async proveConsistency(first: number, second: number): Promise<string[]> {
    const leaves = (await this.backend.leafHashes(second)).map(fromHex);
    return (await consistencyProof(leaves, first, second)).map(toHex);
  }

  /**
   * Client-side verification helpers: these run anywhere (auditor scripts,
   * browsers, other agents) with no access to the backend.
   */
  static async verifyEntryInclusion(
    entry: LogEntry,
    proofHex: string[],
    treeSize: number,
    rootHex: string,
  ): Promise<boolean> {
    const leaf = await leafHash(canonicalBytes(entry as unknown as Json));
    return verifyInclusion(entry.seq, treeSize, leaf, proofHex.map(fromHex), fromHex(rootHex));
  }

  static async verifyLogConsistency(
    first: number,
    second: number,
    firstRootHex: string,
    secondRootHex: string,
    proofHex: string[],
  ): Promise<boolean> {
    return verifyConsistency(
      first,
      second,
      fromHex(firstRootHex),
      fromHex(secondRootHex),
      proofHex.map(fromHex),
    );
  }

  /**
   * Full audit: re-walk the chain, recompute every hash, and confirm the
   * Merkle root. O(n) — run by auditors and after restores from backup.
   * Returns the first problem found, or null if the log is intact.
   */
  async audit(): Promise<string | null> {
    const n = await this.backend.logSize();
    let prev = ZERO;
    const leaves: Hash[] = [];
    for (let i = 0; i < n; i++) {
      const row = await this.backend.getEntry(i);
      if (!row) return `entry ${i} missing`;
      const { entry, entryHash } = row;
      if (entry.seq !== i) return `entry ${i} has wrong seq ${entry.seq}`;
      if (entry.prevHash !== prev) return `entry ${i} breaks the chain`;
      const recomputed = await hashJson(entry as unknown as Json);
      if (recomputed !== entryHash) return `entry ${i} hash mismatch`;
      prev = entryHash;
      leaves.push(await leafHash(canonicalBytes(entry as unknown as Json)));
    }
    // Root recomputation doubles as a check that stored leaf hashes are honest.
    const stored = await this.backend.leafHashes(n);
    for (let i = 0; i < n; i++) {
      if (toHex(leaves[i]!) !== stored[i]) return `leaf hash ${i} mismatch`;
    }
    return null;
  }
}

/** Canonical text of an entry, for exports and mirrors. */
export function entryText(entry: LogEntry): string {
  return canonicalize(entry as unknown as Json);
}
