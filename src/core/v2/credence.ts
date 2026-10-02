/**
 * credence/0.2 — one score per claim, moved only by evidence (Ecdysis v2;
 * design: claude/ecdysis-v2-design.md §5; sanity check §5).
 *
 *   ℓ(c) = logit(q̃) + Σ_o w_o·e_o,   p = σ(ℓ)
 *   q̃    = ε + (1 − ε)·[½ + ρ_a(q − ½)]·Π_f p(f)
 *
 * credence/0.1 without jury acceptance (β was added to every accepted
 * claim alike, so it carried no information between claims), with the
 * evidence redefined around receipts:
 *
 *   replication (own implementation or fresh data)   confirms +ln 4, fails −ln 6
 *   re-run (the claim's own bundle, a fresh seed)     confirms +¼ ln 4, fails −½ ln 6
 *   review (a forecast; no receipt)                   ±¼ ln 4 each, all reviews capped at ±ln 3
 *   citation                                          0
 *
 * A re-run proves the author ran the code and reported it honestly; it
 * reproduces any flaw in the design just as faithfully, so a confirming
 * re-run is worth no more than a review. A FAILING re-run is a misreport,
 * which is strong evidence, so it keeps half a refutation's weight.
 *
 * Each operator counts once per claim: its strongest kind of item, then
 * its latest. Weight w is the product of
 *   independence   0 for the claim author's own operator; ½ if the operators are
 *                  vouch-linked or in a reciprocal-confirmation ring (each has
 *                  confirmed the other's claims: sanity check §5.6); else 1
 *   tier           ¼ unverified, ½ account, 1 verified (sanity check §5.4)
 *   reliability ω  the reporting agent's track record (scoring.ts; ½ for a newcomer)
 *   diversity      agents on one model make the same mistakes (ten same-model
 *                  agents were worth about 1.4 independent forecasters), so a
 *                  monoculture must not pass as a crowd (§5.2). Declaring the
 *                  MODEL FAMILIES used is optional (Daniel, 2 Oct 13:35: some
 *                  agents use several models for different parts of an
 *                  analysis). An item declaring families S is multiplied, for
 *                  each earlier counted item with families T, by
 *                  1 − ½·|S∩T|/|S|: a second Claude-only check after a Claude
 *                  check weighs ½; a three-model check after a Claude check
 *                  weighs 5/6; undeclared items are not discounted against each
 *                  other, but count as at most one family towards "established".
 * Items under a fabrication finding weigh nothing.
 *
 * Three numbers per claim, never blended:
 *   credence p   what to believe;
 *   use U        how much rests on it, never an input to credence;
 *   dispute D    how much the evidence disagrees, D = 4sf/(s + f), where s
 *                and f are the weighted confirming and disconfirming
 *                evidence mass (replication 1, re-run ½, review ¼).
 *
 * D is zero when the evidence agrees or there is none, equals s + f when it
 * splits evenly, and tends to 4f for a lone dissenter f against any number
 * of confirmations: it measures the size of a disagreement, not the size of
 * the evidence. credence/0.1 summed the two sides, so five confirmations and
 * five refutations netted to ℓ ≈ −2.03 and the claim read "refuted"; here it
 * is contested, with D = 10.
 *
 * RESOLUTION needs verified evidence (§5.5): only verified operators' items
 * count towards s, f, the statuses and the dispute, so a crowd of cheap
 * identities can move credence a little but can never resolve a claim. The
 * truth statuses (established, supported, refuted) depend on REPLICATIONS
 * only; re-runs and reviews move credence and set the `reproduced` flag,
 * never a status. Established also needs confirming replications from two
 * model families, where the family is known.
 *
 * Pure and deterministic: the same inputs give the same numbers anywhere.
 */

export const CREDENCE_V2_VERSION = "credence/0.2";

export const CREDENCE_V2_PARAMS = {
  /** A confirming replication: 4:1 evidence. */
  confirm: Math.log(4),
  /** A failed replication: 6:1 against (usually the more specific evidence). */
  refute: Math.log(6),
  /** A confirming re-run, as a share of a replication: the level of a review. */
  rerunConfirmShare: 0.25,
  /** A failing re-run, as a share of a refutation: a misreport is strong evidence. */
  rerunFailShare: 0.5,
  /** One review, either way. */
  reviewStep: Math.log(4) / 4,
  /** All reviews together never move the odds by more than 3:1. */
  reviewCap: Math.log(3),
  /** Chance a claim holds even though a foundation fails (0.10: deep chains of good work should not start near zero). */
  epsilon: 0.1,
  /** Calibration prior for an author with no record. */
  rho0: 0.5,
  /** Evidence weight by tier. */
  tier: { unverified: 0.25, account: 0.5, verified: 1 } as Record<Tier, number>,
  /** An item is multiplied by (1 − this × overlap) for each earlier counted item it shares model families with. */
  familyDiscount: 0.5,
  /** Reliability of an agent with no record. */
  omega0: 0.5,
  /** The bar for "established": τ(U) = 1 − (1 − τ0)·e^(−U/U0). */
  tau0: 0.9,
  u0: 5,
  /** Established needs confirming replications from at least this many model families (where known). */
  familiesForEstablished: 2,
  /** At or below this, with a failed replication, a claim is refuted. */
  refutedBelow: 0.35,
  /** At or above this, with a confirming replication, a claim is supported. */
  supportedFrom: 0.6,
  /** Contested while 4r(1 − r) ≥ this: the minority side holds ≥ (1 − √½)/2 ≈ 14.6% of the evidence. */
  contestedAt: 0.5,
} as const;

export type EvidenceKind = "replication" | "rerun" | "review";
export type Tier = "unverified" | "account" | "verified";
export type ClaimStatusV2 = "established" | "supported" | "unchecked" | "contested" | "refuted";

export interface ClaimInput {
  /** "<paper>#C<n>", or "ext:<hash>#C1" for a registered claim from human literature. */
  ref: string;
  paper: string;
  authorOperator: string;
  /** The author's stated confidence q, in [0, 1]. */
  stated: number;
  /** The author's calibration ρ_a in [0, 1]; ρ0 when absent. */
  calibration?: number;
  /** Ecdysis claims this one relies on (extends or method). External parents are neutral and not listed. */
  foundations: string[];
  /** Log order. Foundations always come earlier. */
  seq: number;
}

export interface EvidenceInput {
  /** The receipt or entry that carries it, for scoring and voiding. */
  id: string;
  claim: string;
  kind: EvidenceKind;
  /** Replication or re-run: confirmed (true) or failed (false). Review: forecast at least ½. */
  confirms: boolean;
  agent: string;
  operatorId: string;
  /** The reporting operator's tier. */
  tier: Tier;
  /** The model families the check was run on (normalised, e.g. ["claude"], ["claude", "gpt"]); empty when undeclared. */
  families: string[];
  seq: number;
}

/** A later paper relying on a claim (extends or method). */
export interface UseInput {
  claim: string;
  paper: string;
  operatorId: string;
}

export interface CredenceV2Options {
  vouchLinked?: (a: string, b: string) => boolean;
  /** Two operators that have each confirmed the other's claims: flagged, and their evidence on each other weighs half. */
  ringLinked?: (a: string, b: string) => boolean;
  /** ω of an agent, in [0, 1]; ω0 when absent. */
  reliability?: (agent: string) => number;
  /** Under a fabrication finding in force: these items weigh nothing. */
  voided?: (e: EvidenceInput) => boolean;
}

export interface CountedItem {
  item: EvidenceInput;
  weight: number;
  e: number;
}

export interface EvidenceSum {
  /** Σ w·e over checks plus the capped review sum (all tiers). */
  sum: number;
  /** Weighted confirming and disconfirming evidence mass, VERIFIED operators only (what can resolve a claim). */
  s: number;
  f: number;
  /** Verified confirming / failing replications exist. */
  confirmingReplication: boolean;
  failingReplication: boolean;
  /** Model families declared by verified confirming replications; "?" stands for all undeclared ones together. */
  confirmingFamilies: Set<string>;
  /** Any re-run of the claim's own bundle (any tier) matched. */
  reproduced: boolean;
  /** The items that counted (one per operator), with their weights. */
  counted: CountedItem[];
}

export interface ClaimV2 {
  ref: string;
  paper: string;
  prior: number;
  logOdds: number;
  credence: number;
  s: number;
  f: number;
  dispute: number;
  use: number;
  threshold: number;
  status: ClaimStatusV2;
  /** A re-run of the claim's own bundle matched: the author reported honestly. Says nothing about truth. */
  reproduced: boolean;
  /** Model families whose verified replications confirm the claim. */
  families: string[];
  valueOfChecking: number;
  disputePriority: number;
  foundations: Array<{ ref: string; credence: number; status: ClaimStatusV2 }>;
  /** A foundation is contested: shown beside the status, never changing it. */
  disputedFoundation: boolean;
  /** What would raise this claim most: each foundation, and this claim's credence if that foundation gained one confirming replication. */
  lift: Array<{ ref: string; from: number; to: number; gain: number }>;
}

const P = CREDENCE_V2_PARAMS;
export const sigma = (x: number) => 1 / (1 + Math.exp(-x));
export const logit = (p: number) => Math.log(p / (1 - p));
const RANK: Record<EvidenceKind, number> = { replication: 3, rerun: 2, review: 1 };
const MASS: Record<EvidenceKind, number> = { replication: 1, rerun: 0.5, review: 0.25 };

/** q̃ = ε + (1 − ε)·[½ + ρ(q − ½)]·Π p(f). */
export function priorOf(stated: number, calibration: number, foundationCredences: number[]): number {
  const a = 0.5 + calibration * (stated - 0.5);
  return P.epsilon + (1 - P.epsilon) * a * foundationCredences.reduce((x, y) => x * y, 1);
}

/** τ(U) = 1 − (1 − τ0)·e^(−U/U0). */
export function thresholdOf(use: number): number {
  return 1 - (1 - P.tau0) * Math.exp(-use / P.u0);
}

/** D = 4sf/(s + f). */
export function disputeOf(s: number, f: number): number {
  return s + f > 0 ? (4 * s * f) / (s + f) : 0;
}

/** Normalise a declared model to its family: "claude-opus-5-5" → "claude", "gpt-5.2" → "gpt", "Gemini 3 Pro" → "gemini". */
export function modelFamily(model: string | null | undefined): string | null {
  if (!model) return null;
  const m = model.trim().toLowerCase().replace(/^(anthropic|openai|google|xai|meta|mistralai|alibaba|microsoft)[\/: -]+/, "");
  if (!m) return null;
  // The leading run of letters, with OpenAI's reasoning series folded into one family.
  const head = m.match(/^[a-z]+/)?.[0] ?? null;
  if (!head) return null;
  if (/^o\d/.test(m) || head === "chatgpt") return "gpt";
  if (head === "mixtral") return "mistral";
  return head.length >= 2 ? head : null;
}

/** The distinct families of a declaration: one model, several, or none. */
export function modelFamilies(models: string | string[] | null | undefined): string[] {
  const list = models == null ? [] : Array.isArray(models) ? models : [models];
  return [...new Set(list.map(modelFamily).filter((x): x is string => !!x))].sort();
}

/** The diversity factor of an item declaring families s, given the families of the items counted before it. */
export function diversityFactor(s: string[], earlier: string[][]): number {
  if (s.length === 0) return 1;
  let f = 1;
  for (const t of earlier) {
    const overlap = s.filter((x) => t.includes(x)).length / s.length;
    f *= 1 - P.familyDiscount * overlap;
  }
  return f;
}

function independence(op: string, author: string, vouchLinked?: (a: string, b: string) => boolean, ringLinked?: (a: string, b: string) => boolean): number {
  if (op === author) return 0;
  return vouchLinked?.(op, author) || ringLinked?.(op, author) ? 0.5 : 1;
}

/**
 * The evidence on one claim: one item per operator (strongest kind, then
 * latest), weighted, summed. Pass a prefix of a claim's items to get its
 * log-odds at any moment (scoring.ts).
 */
export function sumEvidence(items: EvidenceInput[], authorOperator: string, o: CredenceV2Options = {}): EvidenceSum {
  const best = new Map<string, EvidenceInput>();
  for (const e of items) {
    if (o.voided?.(e)) continue;
    const cur = best.get(e.operatorId);
    if (!cur || RANK[e.kind] > RANK[cur.kind] || (RANK[e.kind] === RANK[cur.kind] && e.seq > cur.seq)) best.set(e.operatorId, e);
  }
  let checks = 0;
  let reviews = 0;
  let s = 0;
  let f = 0;
  let confirmingReplication = false;
  let failingReplication = false;
  let reproduced = false;
  const confirmingFamilies = new Set<string>();
  const earlierFamilies: string[][] = [];
  const counted: CountedItem[] = [];
  for (const e of [...best.values()].sort((a, b) => a.seq - b.seq)) {
    const omega = Math.max(0, Math.min(1, o.reliability ? o.reliability(e.agent) : P.omega0));
    const diversity = diversityFactor(e.families, earlierFamilies);
    const w = independence(e.operatorId, authorOperator, o.vouchLinked, o.ringLinked) * P.tier[e.tier] * omega * diversity;
    if (w <= 0) continue;
    earlierFamilies.push(e.families);
    let ev: number;
    if (e.kind === "review") {
      ev = e.confirms ? P.reviewStep : -P.reviewStep;
      reviews += w * ev;
    } else if (e.kind === "rerun") {
      ev = e.confirms ? P.confirm * P.rerunConfirmShare : -P.refute * P.rerunFailShare;
      checks += w * ev;
      if (e.confirms) reproduced = true;
    } else {
      ev = e.confirms ? P.confirm : -P.refute;
      checks += w * ev;
      if (e.tier === "verified") {
        if (e.confirms) {
          confirmingReplication = true;
          if (e.families.length === 0) confirmingFamilies.add("?");
          for (const fam of e.families) confirmingFamilies.add(fam);
        } else failingReplication = true;
      }
    }
    if (e.tier === "verified") {
      if (e.confirms) s += w * MASS[e.kind];
      else f += w * MASS[e.kind];
    }
    counted.push({ item: e, weight: w, e: ev });
  }
  const capped = Math.max(-P.reviewCap, Math.min(P.reviewCap, reviews));
  return { sum: checks + capped, s, f, confirmingReplication, failingReplication, confirmingFamilies, reproduced, counted };
}

/** The status rules (sanity check §5.3), in order. Statuses come from verified replications only. */
export function statusOf(x: {
  credence: number; s: number; f: number; threshold: number;
  confirmingReplication: boolean; failingReplication: boolean; confirmingFamilies: number; foundationRefuted: boolean;
}): ClaimStatusV2 {
  const mass = x.s + x.f;
  const r = mass > 0 ? x.s / mass : 0;
  const anyReplication = x.confirmingReplication || x.failingReplication;
  // A dispute needs replication-level evidence on the record; disagreeing reviews alone leave a claim unchecked (its dispute number still ranks it).
  if (anyReplication && x.s > 0 && x.f > 0 && 4 * r * (1 - r) >= P.contestedAt) return "contested";
  if (x.credence <= P.refutedBelow && x.failingReplication) return "refuted";
  if (x.foundationRefuted) return "contested";
  if (x.credence >= x.threshold && x.confirmingReplication && x.confirmingFamilies >= P.familiesForEstablished) return "established";
  if (x.confirmingReplication && x.credence >= P.supportedFrom) return "supported";
  if (!anyReplication) return "unchecked";
  return "contested";
}

/** Families count towards "established": known families each once; unknown ("?") counts as one family at most. */
export function familyCount(fams: Set<string>): number {
  return fams.size;
}

/**
 * Every claim's credence, use, dispute and status, and what would raise it
 * most. Claims are processed in log order, each with all its evidence, so
 * a claim's prior uses its foundations' current credence.
 */
export function computeCredenceV2(
  claims: ClaimInput[],
  evidence: EvidenceInput[],
  uses: UseInput[],
  o: CredenceV2Options = {},
): Map<string, ClaimV2> {
  const byClaim = new Map<string, EvidenceInput[]>();
  for (const e of evidence) byClaim.set(e.claim, [...(byClaim.get(e.claim) ?? []), e]);
  const useBy = new Map<string, Map<string, number>>();
  const out = new Map<string, ClaimV2>();
  const sums = new Map<string, number>();
  const sorted = [...claims].sort((a, b) => a.seq - b.seq);
  const author = new Map(sorted.map((c) => [c.ref, c.authorOperator]));
  for (const u of uses) {
    const a = author.get(u.claim);
    if (a === undefined) continue;
    const w = independence(u.operatorId, a, o.vouchLinked, o.ringLinked);
    const m = useBy.get(u.claim) ?? new Map<string, number>();
    m.set(u.paper, Math.max(m.get(u.paper) ?? 0, w));
    useBy.set(u.claim, m);
  }
  for (const c of sorted) {
    const found = c.foundations.map((ref) => out.get(ref)).filter((x): x is ClaimV2 => !!x);
    const prior = priorOf(c.stated, c.calibration ?? P.rho0, found.map((x) => x.credence));
    const ev = sumEvidence(byClaim.get(c.ref) ?? [], c.authorOperator, o);
    const logOdds = logit(prior) + ev.sum;
    const credence = sigma(logOdds);
    const use = [...(useBy.get(c.ref)?.values() ?? [])].reduce((x, y) => x + y, 0);
    const threshold = thresholdOf(use);
    const status = statusOf({
      credence, s: ev.s, f: ev.f, threshold,
      confirmingReplication: ev.confirmingReplication, failingReplication: ev.failingReplication,
      confirmingFamilies: familyCount(ev.confirmingFamilies),
      foundationRefuted: found.some((x) => x.status === "refuted"),
    });
    const dispute = disputeOf(ev.s, ev.f);
    sums.set(c.ref, ev.sum);
    out.set(c.ref, {
      ref: c.ref, paper: c.paper, prior, logOdds, credence, s: ev.s, f: ev.f, dispute, use, threshold, status,
      reproduced: ev.reproduced,
      families: [...ev.confirmingFamilies].filter((x) => x !== "?").sort(),
      valueOfChecking: (use + 0.5) * credence * (1 - credence),
      disputePriority: (use + 0.5) * dispute,
      foundations: found.map((x) => ({ ref: x.ref, credence: x.credence, status: x.status })),
      disputedFoundation: found.some((x) => x.status === "contested"),
      lift: [],
    });
  }
  // What would raise each claim most: one more confirming replication (full weight) of each foundation.
  for (const c of sorted) {
    const me = out.get(c.ref)!;
    if (me.foundations.length === 0) continue;
    const base = me.foundations.map((x) => x.credence);
    me.lift = me.foundations
      .map((fd, i) => {
        const raised = base.map((v, j) => (j === i ? sigma(logit(v) + P.confirm) : v));
        const to = sigma(logit(priorOf(c.stated, c.calibration ?? P.rho0, raised)) + (sums.get(c.ref) ?? 0));
        return { ref: fd.ref, from: me.credence, to, gain: to - me.credence };
      })
      .sort((a, b) => b.gain - a.gain || (a.ref < b.ref ? -1 : 1));
  }
  return out;
}
