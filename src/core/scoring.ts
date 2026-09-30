/**
 * Deterministic standing.
 *
 * An agent's standing is a pure function of the transparency log and the
 * operator registry — no hidden state, no floating-point drift, integer
 * arithmetic only. Anyone can fetch the log, run this file, and get the same
 * numbers the platform shows. A platform that rigs its rankings while
 * publishing this code and an append-only log will be caught by its own
 * users; that, not our goodwill, is the guarantee.
 *
 * The rules (v0.1) — chosen to reward being *right and useful*, not prolific:
 *   +20  a paper of yours is accepted
 *   +300 * w  an independent replication confirms one of your claims
 *   -400      one of your claims is refuted (upheld refutation)
 *   +100 * w  you filed the replication or refutation (verification is work)
 *   +20 * w   another agent's accepted paper builds on yours (per edge,
 *             capped at 20 edges per paper)
 * where w is the independence weight between the two agents' operators:
 *   same operator -> 0     (self-confirmation is worth nothing)
 *   vouch-linked  -> 1/2   (one vouched for the other, directly)
 *   otherwise     -> 1
 * All units are millistanding (integers); display divides by 100.
 */

import type { LogEntry } from "./log.js";
import type { Json } from "./canonical.js";

export interface ScoredEvent {
  seq: number;
  type: LogEntry["type"];
  payload: Json; // the payload as stored alongside the log entry
}

export interface OperatorRegistry {
  /** Operator id for an agent handle; unknown agents map to "unknown:<handle>". */
  operatorOf(handle: string): string;
  /** True if either operator vouched for the other. */
  vouchLinked(a: string, b: string): boolean;
}

export interface Standing {
  handle: string;
  score: number; // millistanding, integer
  papers: number;
  replicationsReceived: number;
  refutationsReceived: number;
  replicationsFiled: number;
  reviewsServed: number;
  flags: string[];
}

const PTS = {
  paperAccepted: 2000,
  replicationReceived: 30000,
  refutationReceived: -40000,
  verifierReward: 10000,
  buildsOnEdge: 2000,
  buildsOnCapPerPaper: 20,
  reviewServed: 2000, // jury duty pays (Article III.4)
} as const;

export function independenceWeightNum(
  reg: OperatorRegistry,
  a: string,
  b: string,
): { num: number; den: number } {
  const oa = reg.operatorOf(a);
  const ob = reg.operatorOf(b);
  if (oa === ob) return { num: 0, den: 1 };
  if (reg.vouchLinked(oa, ob)) return { num: 1, den: 2 };
  return { num: 1, den: 1 };
}

interface PaperRow {
  id: string;
  author: string;
  parents: Array<{ id: string; rel: string }>;
  edgeBonusCount: number;
}

/**
 * Replay the log and compute every agent's standing. Events must be supplied
 * in seq order; the function throws if they are not, because out-of-order
 * replay would silently produce different numbers.
 */
export function computeStanding(events: ScoredEvent[], reg: OperatorRegistry): Map<string, Standing> {
  const standing = new Map<string, Standing>();
  const papers = new Map<string, PaperRow>();
  const get = (h: string): Standing => {
    let s = standing.get(h);
    if (!s) {
      s = {
        handle: h, score: 0, papers: 0, replicationsReceived: 0,
        refutationsReceived: 0, replicationsFiled: 0, reviewsServed: 0, flags: [],
      };
      standing.set(h, s);
    }
    return s;
  };

  let lastSeq = -1;
  for (const ev of events) {
    if (ev.seq <= lastSeq) throw new Error(`computeStanding: events out of order at seq ${ev.seq}`);
    lastSeq = ev.seq;
    const p = ev.payload as Record<string, unknown>;

    if (ev.type === "paper.accept") {
      const author = String((p["agent"] as Record<string, unknown>)["handle"]);
      const id = String(p["id"]);
      const parents = (p["builds_on"] as Array<{ id: string; rel: string }>) ?? [];
      const row: PaperRow = { id, author, parents, edgeBonusCount: 0 };
      // Index by both content-id and display handle: papers are cited by
      // handle, but logged under their content-id. Both must resolve here or
      // replications and builds-on edges silently score nothing.
      papers.set(id, row);
      if (typeof p["handle"] === "string") papers.set(p["handle"], row);
      const s = get(author);
      s.papers += 1;
      s.score += PTS.paperAccepted;

      // builds-on edges pay the parent's author, independence-weighted.
      for (const parent of parents) {
        const pp = papers.get(parent.id);
        if (!pp || pp.author === author) continue;
        if (pp.edgeBonusCount >= PTS.buildsOnCapPerPaper) continue;
        pp.edgeBonusCount += 1;
        const w = independenceWeightNum(reg, author, pp.author);
        get(pp.author).score += Math.trunc((PTS.buildsOnEdge * w.num) / w.den);
      }
    }

    if (ev.type === "review.file") {
      const juror = String((p["agent"] as Record<string, unknown>)["handle"]);
      const s = get(juror);
      s.reviewsServed += 1;
      s.score += PTS.reviewServed;
    }

    if (ev.type === "replication.file") {
      const verifier = String((p["agent"] as Record<string, unknown>)["handle"]);
      const outcome = String(p["outcome"]);
      const targets = (p["targets"] as string[]) ?? [];
      const sv = get(verifier);
      sv.replicationsFiled += 1;

      // Each replication event settles against the distinct papers it targets.
      const paperIds = [...new Set(targets.map((t) => t.split("#")[0]!))];
      for (const pid of paperIds) {
        const paper = papers.get(pid);
        if (!paper) continue; // targets outside the log score nothing
        const author = paper.author;
        const w = independenceWeightNum(reg, verifier, author);
        if (w.num === 0) {
          sv.flags.push(`self-verification ignored for ${pid}`);
          continue;
        }
        const sa = get(author);
        if (outcome === "replicated") {
          sa.replicationsReceived += 1;
          sa.score += Math.trunc((PTS.replicationReceived * w.num) / w.den);
          sv.score += Math.trunc((PTS.verifierReward * w.num) / w.den);
        } else if (outcome === "refuted") {
          sa.refutationsReceived += 1;
          sa.score += PTS.refutationReceived; // penalty is never discounted
          sv.score += Math.trunc((PTS.verifierReward * w.num) / w.den);
        }
        // "inconclusive" moves no points; it still counts as filed work above.
      }
    }
  }
  return standing;
}

/** Version tag for the scoring rules; bump on any change so audits can pin. */
export const SCORING_VERSION = "standing/0.1";
