/**
 * credence/0.3 — one score per claim, moved only by evidence (Ecdysis v2;
 * design: claude/ecdysis-v2-design.md §5; sanity check §5; arguments:
 * claude/ecdysis-conceptual-claims-design.md).
 *
 *   ℓ(c) = logit(q̃) + Σ_o w_o·e_o,   p = σ(ℓ)
 *   q̃    = ε + (1 − ε)·[½ + ρ_a(q − ½)]·Π_f p(f)
 *
 * credence/0.1 without v1's acceptance step (β was added to every accepted
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
 *                  each earlier counted VERIFIED item with families T that
 *                  points the SAME WAY, by 1 − ½·|S∩T|/|S|: a second Claude-only
 *                  confirmation after a Claude confirmation weighs ½; a
 *                  three-model confirmation after a Claude one weighs 5/6; a
 *                  Claude FAILURE after a Claude confirmation weighs 1, since a
 *                  dissent demonstrably did not share the earlier item's error
 *                  (Daniel, 3 Oct). Undeclared items are not discounted against
 *                  each other and count as no family towards "established".
 * Items under a fabrication finding weigh nothing. Everything from operators
 * who are not verified, checks and reviews together, moves a claim by at
 * most ln 3; verified operators' reviews together at most ln 3 as well:
 * verified operators' checks are the trust anchor, and a cheap crowd must
 * not be able to carry a claim far on its own. Use is weighed by the citing
 * operator's tier for the same reason.
 *
 * CALIBRATION (Daniel, 3 Oct). ρ_a is derived from the author's record:
 * over the operator's n claims published EARLIER in the log that have since
 * resolved (truth T_i ∈ {0, 1}: a revealed canary's outcome, else established
 * or refuted at the bar for zero use), with stated confidence q_i,
 *
 *   ρ_a = (k·ρ0 + Σ_i (1 − 2(q_i − T_i)²)) / (k + n),   k = 4, ρ0 = ½,
 *
 * clamped to [0, 1]. A newcomer has ρ0 = ½; an author who states ½ keeps ½
 * (uninformative is not wrong); one who is confident and right earns trust;
 * one who is confident and wrong loses it, so overstating costs twice: the
 * claim's own credence and every later claim's prior. A record of being
 * wrong earns ρ = 0 (the stated confidence is ignored), never an inversion,
 * which would reward understating. Only strictly earlier claims count, so no
 * claim's resolution feeds its own prior and the claims of one paper do not
 * feed each other; the record is otherwise the one on the log now.
 *
 * FOUNDATIONS. A claim's prior is multiplied by the credence of each Ecdysis
 * claim it rests on. A registered claim from human literature is taken at
 * FACE VALUE (factor 1) by the papers resting on it until verified evidence
 * counts against it; from then on the factor is its credence relative to its
 * unevidenced value, min(1, p_verified / q̃), so a confirmation never lowers
 * what rests on it and the factor is continuous in the evidence (Daniel,
 * 3 Oct: registering a human claim must cost the dependant nothing).
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
 * truth statuses (established, supported, contested, refuted) depend on
 * REPLICATIONS only: contested is judged on replication mass alone, so one
 * dissenting review never flips a supported claim (reviews still feed the
 * dispute number D, which ranks the queue); re-runs and reviews move
 * credence and set the `reproduced` flag, never a status. Established also
 * needs confirming replications from two DECLARED model families and two
 * distinct verified operators.
 *
 * ARGUMENTS (credence/0.3; arguments.ts). A claim is EMPIRICAL or CONCEPTUAL.
 * Settled arguments move credence too, through `arguments` in the options:
 *   upheld counterexample (conceptual)   status refuted; log-odds −counterexampleStep
 *   upheld contradiction with an         credence capped at 1 − (its credence) while it
 *     ESTABLISHED claim                  stays established; status contested
 *   upheld logical gap / unsupported     −upheldStep × the arguer's tier weight, one per
 *     premise                            operator
 *   upheld statistical / methodological  the author's calibration ρ_a is multiplied by
 *     flaw (empirical)                   methodologyFactor per assessment: the stated
 *                                        confidence counts for less, nothing moves
 *                                        towards false
 *   a refuting argument DISMISSED        +corroborationStep per distinct VERIFIED arguer,
 *                                        all corroboration capped at corroborationCap
 * Verified arguers' effects count towards the verified sum (statuses); others
 * join the unverified pool under its cap. A conceptual claim's status is
 * refuted (counterexample) → contested (contradiction cap) → supported
 * (dismissed attacks from supportedAttacks verified arguers and credence at
 * the supported bar) → unchecked; never established. A contradiction cap is
 * applied in a second pass, so claims resting on a capped claim see the cap.
 *
 * Pure and deterministic: the same inputs give the same numbers anywhere.
 */

import { ARGUMENT_PARAMS, type ClaimArgumentsInput, type ClaimKind } from "./arguments.js";

export const CREDENCE_V2_VERSION = "credence/0.3";

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
  /**
   * Everything from operators who are not verified (unverified and account
   * tiers; checks and reviews alike) never moves the odds by more than 3:1
   * all together. Accounts cost an email and unverified operator ids cost
   * nothing, so a crowd of them is cheap to assemble; verified operators are
   * the trust anchor. Without this cap ten undeclared unverified sybils
   * could carry a false claim from a half to 0.85 while its status still
   * read "unchecked"; with separate caps for checks and reviews they could
   * still reach 0.9.
   */
  unverifiedCap: Math.log(3),
  /** Chance a claim holds even though a foundation fails (0.10: deep chains of good work should not start near zero). */
  epsilon: 0.1,
  /** Calibration prior for an author with no record, and its weight in resolved claims: ρ_a = (k·ρ0 + Σ(1 − 2(q − T)²)) / (k + n). */
  rho0: 0.5,
  rhoK: 4,
  /** Evidence weight by tier. */
  tier: { unverified: 0.25, account: 0.5, verified: 1 } as Record<Tier, number>,
  /** An item is multiplied by (1 − this × overlap) for each earlier counted item it shares model families with. */
  familyDiscount: 0.5,
  /** Reliability of an agent with no record. */
  omega0: 0.5,
  /** The bar for "established": τ(U) = 1 − (1 − τ0)·e^(−U/U0). */
  tau0: 0.9,
  u0: 5,
  /** Established needs confirming replications from at least this many DECLARED model families (undeclared is no family)... */
  familiesForEstablished: 2,
  /** ...filed by at least this many distinct verified operators (one receipt declaring two models is one operator's word). */
  operatorsForEstablished: 2,
  /**
   * Log-odds pass unchanged up to ±softLogOdds and are compressed smoothly
   * beyond, never exceeding ±maxLogOdds: a prior of exactly 0 or 1, or
   * thirty confirmations, never saturate the arithmetic, so credence stays
   * strictly inside (0, 1) and the next failure still moves it. Below 8
   * (credence 0.9997) nothing is touched.
   */
  softLogOdds: 8,
  maxLogOdds: 12,
  /** At or below this, with a failed replication, a claim is refuted. */
  refutedBelow: 0.35,
  /** At or above this, with a confirming replication, a claim is supported. */
  supportedFrom: 0.6,
  /** Contested while 4r(1 − r) ≥ this, r the confirming share of the verified REPLICATION mass: the minority side holds ≥ (1 − √½)/2 ≈ 14.6% of it. */
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
  /** The author's calibration ρ_a in [0, 1]. Absent: derived from the operator's record of earlier resolved claims (ρ0 with none). */
  calibration?: number;
  /** A registered claim from human literature: taken at face value by what rests on it until verified evidence counts against it. */
  external?: boolean;
  /** arguments/0.1: empirical (a receipt can repeat its test) or conceptual (its test names a refuter in words). Absent: empirical. */
  kind?: ClaimKind;
  /** Claims this one relies on (extends or method), Ecdysis claims and registered external ones alike. Unregistered sources are not listed. */
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
  /**
   * inputs/0.1: false for a receipt whose bundle needs inputs not everyone
   * can obtain and which no verified, independent cross-check has yet
   * matched. The audit that makes a receipt evidence (every receipt of a
   * living claim is eventually re-run) is not guaranteed for it, so it is
   * weighed as an unverified operator's would be, whatever its operator's
   * tier, and settles nothing. Absent or true: weighed by tier as usual.
   */
  auditable?: boolean;
}

/** A later paper relying on a claim (extends or method). */
export interface UseInput {
  claim: string;
  paper: string;
  operatorId: string;
  /** The citing operator's tier: use is weighed by it, so free identities cannot raise a claim's threshold or hijack the queues. Absent: unverified. */
  tier?: Tier;
}

export interface CredenceV2Options {
  vouchLinked?: (a: string, b: string) => boolean;
  /** Two operators that have each confirmed the other's claims: flagged, and their evidence on each other weighs half. */
  ringLinked?: (a: string, b: string) => boolean;
  /** ω of an agent, in [0, 1]; ω0 when absent. */
  reliability?: (agent: string) => number;
  /** Under a fabrication finding in force: these items weigh nothing. */
  voided?: (e: EvidenceInput) => boolean;
  /** Revealed canaries (design §7): claim ref → true if its known outcome confirms it. They resolve a claim for the calibration record, whatever the evidence says. */
  anchors?: Map<string, boolean>;
  /** arguments/0.1: what each claim's SETTLED arguments do to it (arguments.ts, argumentEffects), by claim ref. Absent: none. */
  arguments?: Map<string, ClaimArgumentsInput>;
}

export interface CountedItem {
  item: EvidenceInput;
  weight: number;
  e: number;
}

export interface EvidenceSum {
  /** Σ w·e over checks plus the capped review sum (all tiers). */
  sum: number;
  /** The same from VERIFIED operators alone (their checks and their capped reviews): what the truth statuses are tested against (§5.5). */
  sumVerified: number;
  /** Distinct verified operators whose counted item is a confirming replication. */
  confirmingOperators: number;
  /** Weighted confirming and disconfirming evidence mass, VERIFIED operators only (what can resolve a claim): the dispute number's inputs. */
  s: number;
  f: number;
  /** The same from verified REPLICATIONS alone: what the contested status is judged on. */
  sReplication: number;
  fReplication: number;
  /** Verified confirming / failing replications exist. */
  confirmingReplication: boolean;
  failingReplication: boolean;
  /** Model families declared by verified confirming replications; "?" stands for all undeclared ones together (it is no family for "established"). */
  confirmingFamilies: Set<string>;
  /** Any re-run of the claim's own bundle (any tier) matched. */
  reproduced: boolean;
  /** The items that counted (one per operator), with their weights. */
  counted: CountedItem[];
}

export interface ClaimV2 {
  ref: string;
  paper: string;
  /** A registered claim from human literature. */
  external: boolean;
  /** arguments/0.1: empirical or conceptual. */
  kind: ClaimKind;
  /** An upheld contradiction with an established claim caps this one's credence here (1 − that claim's credence); null when none applies. */
  cap: number | null;
  /** Settled arguments counted against and for this claim, and open ones awaiting checks. */
  arguments: { upheld: number; dismissed: number; open: number; methodology: number; counterexample: boolean };
  /** The calibration ρ_a the prior used: given, or derived from the author's record of earlier resolved claims. */
  calibration: number;
  prior: number;
  logOdds: number;
  credence: number;
  /** Credence from verified operators' evidence alone: the number the truth statuses are tested against (§5.5). */
  credenceVerified: number;
  s: number;
  f: number;
  dispute: number;
  use: number;
  threshold: number;
  status: ClaimStatusV2;
  /** The claim's resolution at the bar for zero use (a revealed canary's truth first): 1 established, 0 refuted, null not yet. What the author's calibration record and the track record are judged against. */
  resolved: 0 | 1 | null;
  /** A re-run of the claim's own bundle matched: the author reported honestly. Says nothing about truth. */
  reproduced: boolean;
  /** Model families whose verified replications confirm the claim. */
  families: string[];
  valueOfChecking: number;
  disputePriority: number;
  /** Each foundation with the factor it contributed to this claim's prior: its credence, or for an external claim at face value 1 until verified evidence counts against it. */
  foundations: Array<{ ref: string; credence: number; status: ClaimStatusV2; factor: number }>;
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
  const q = P.epsilon + (1 - P.epsilon) * a * foundationCredences.reduce((x, y) => x * y, 1);
  // Never exactly 0 or 1: logit must stay finite whatever the inputs.
  return Math.min(1 - 1e-6, Math.max(1e-6, q));
}

/**
 * Log-odds compressed beyond ±softLogOdds towards ±maxLogOdds: identity in
 * the ordinary range, strictly monotone everywhere, so credence never
 * saturates to exactly 0 or 1 and later evidence always moves it.
 */
export function clampLogOdds(x: number): number {
  if (!Number.isFinite(x)) return x > 0 ? P.maxLogOdds : x < 0 ? -P.maxLogOdds : 0;
  const a = Math.abs(x);
  if (a <= P.softLogOdds) return x;
  const room = P.maxLogOdds - P.softLogOdds;
  const compressed = P.softLogOdds + room * Math.tanh((a - P.softLogOdds) / room);
  return x < 0 ? -compressed : compressed;
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
export function modelFamily(model: unknown): string | null {
  if (typeof model !== "string" || !model) return null;
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
export function modelFamilies(models: unknown): string[] {
  const list: unknown[] = models == null ? [] : Array.isArray(models) ? models : [models];
  return [...new Set(list.map(modelFamily).filter((x): x is string => !!x))].sort();
}

/** A counted item's families and direction, as seen by the items counted after it. */
export interface EarlierItem {
  families: string[];
  confirms: boolean;
}

/**
 * The diversity factor of an item declaring families s and pointing one way,
 * given the verified items counted before it: discounted for each earlier
 * item it AGREES with and shares a family with; never for a dissent, which
 * demonstrably did not share the earlier item's error.
 */
export function diversityFactor(s: string[], confirms: boolean, earlier: EarlierItem[]): number {
  if (s.length === 0) return 1;
  let f = 1;
  for (const t of earlier) {
    if (t.confirms !== confirms) continue;
    const overlap = s.filter((x) => t.families.includes(x)).length / s.length;
    f *= 1 - P.familyDiscount * overlap;
  }
  return f;
}

/**
 * ρ_a from an author's record: the operator's earlier claims that have
 * resolved, each with the stated confidence q and the truth T.
 * (k·ρ0 + Σ(1 − 2(q − T)²)) / (k + n), clamped to [0, 1]: ρ0 with no record.
 */
export function calibrationOf(record: ReadonlyArray<{ stated: number; truth: 0 | 1 }>): number {
  let sum = P.rhoK * P.rho0;
  for (const r of record) sum += 1 - 2 * (r.stated - r.truth) ** 2;
  return Math.max(0, Math.min(1, sum / (P.rhoK + record.length)));
}

/** A claim's resolution: a revealed canary's known truth first; else established → 1, refuted → 0, anything else not yet. */
export function resolutionOf(status: ClaimStatusV2, anchor: boolean | undefined): 0 | 1 | null {
  if (anchor !== undefined) return anchor ? 1 : 0;
  return status === "established" ? 1 : status === "refuted" ? 0 : null;
}

function independence(op: string, author: string, vouchLinked?: (a: string, b: string) => boolean, ringLinked?: (a: string, b: string) => boolean): number {
  if (op === author) return 0;
  return vouchLinked?.(op, author) || ringLinked?.(op, author) ? 0.5 : 1;
}

/** Two operators linked by a vouch or a ring are not two independent voices on a third party's claim either: the later one weighs half. */
function linkedTo(op: string, earlier: string[], vouchLinked?: (a: string, b: string) => boolean, ringLinked?: (a: string, b: string) => boolean): boolean {
  return earlier.some((other) => other !== op && (vouchLinked?.(op, other) || ringLinked?.(op, other)));
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
  let unverified = 0; // every item, check or review, from an operator who is not verified
  let reviews = 0; // verified operators' reviews
  let s = 0;
  let f = 0;
  let sReplication = 0;
  let fReplication = 0;
  let confirmingReplication = false;
  let failingReplication = false;
  let reproduced = false;
  let confirmingOperators = 0;
  const confirmingFamilies = new Set<string>();
  // Only VERIFIED items set the families that discount later ones: an unverified sybil declaring every family (its own
  // weight capped at ln 3 all together) could otherwise multiply every later verified replication by a half per sybil.
  const earlier: EarlierItem[] = [];
  const earlierOperators: string[] = [];
  const counted: CountedItem[] = [];
  for (const e of [...best.values()].sort((a, b) => a.seq - b.seq)) {
    // inputs/0.1: a receipt the audit cannot yet reach is weighed as an unverified operator's, whatever its operator's tier.
    const tier: Tier = e.auditable === false ? "unverified" : e.tier;
    const omega = Math.max(0, Math.min(1, o.reliability ? o.reliability(e.agent) : P.omega0));
    const diversity = diversityFactor(e.families, e.confirms, earlier);
    const linked = linkedTo(e.operatorId, earlierOperators, o.vouchLinked, o.ringLinked) ? 0.5 : 1;
    const w = independence(e.operatorId, authorOperator, o.vouchLinked, o.ringLinked) * P.tier[tier] * omega * diversity * linked;
    if (w <= 0) continue;
    if (tier === "verified") earlier.push({ families: e.families, confirms: e.confirms });
    earlierOperators.push(e.operatorId);
    let ev: number;
    if (e.kind === "review") {
      ev = e.confirms ? P.reviewStep : -P.reviewStep;
      if (tier === "verified") reviews += w * ev; else unverified += w * ev;
    } else if (e.kind === "rerun") {
      ev = e.confirms ? P.confirm * P.rerunConfirmShare : -P.refute * P.rerunFailShare;
      if (tier === "verified") checks += w * ev; else unverified += w * ev;
      if (e.confirms) reproduced = true;
    } else {
      ev = e.confirms ? P.confirm : -P.refute;
      if (tier === "verified") checks += w * ev; else unverified += w * ev;
      if (tier === "verified") {
        if (e.confirms) {
          confirmingReplication = true;
          confirmingOperators++;
          if (e.families.length === 0) confirmingFamilies.add("?");
          for (const fam of e.families) confirmingFamilies.add(fam);
        } else failingReplication = true;
      }
    }
    if (tier === "verified") {
      if (e.confirms) s += w * MASS[e.kind];
      else f += w * MASS[e.kind];
      if (e.kind === "replication") {
        if (e.confirms) sReplication += w;
        else fReplication += w;
      }
    }
    counted.push({ item: e, weight: w, e: ev });
  }
  const cappedReviews = Math.max(-P.reviewCap, Math.min(P.reviewCap, reviews));
  const cappedUnverified = Math.max(-P.unverifiedCap, Math.min(P.unverifiedCap, unverified));
  return {
    sum: checks + cappedUnverified + cappedReviews, sumVerified: checks + cappedReviews,
    s, f, sReplication, fReplication, confirmingReplication, failingReplication, confirmingOperators, confirmingFamilies, reproduced, counted,
  };
}

/** The status rules (sanity check §5.3), in order. Statuses come from verified replications only. */
export function statusOf(x: {
  /** Credence from VERIFIED evidence alone (§5.5): a crowd of cheap identities can move the displayed number a little, never a status. */
  credence: number;
  /** Weighted confirming and failing mass from verified REPLICATIONS alone: a dissenting review never makes a claim contested. */
  sReplication: number; fReplication: number;
  threshold: number;
  confirmingReplication: boolean; failingReplication: boolean;
  /** Distinct DECLARED model families among the verified confirming replications (familyCount). */
  confirmingFamilies: number; confirmingOperators?: number; foundationRefuted: boolean;
}): ClaimStatusV2 {
  const mass = x.sReplication + x.fReplication;
  const r = mass > 0 ? x.sReplication / mass : 0;
  const anyReplication = x.confirmingReplication || x.failingReplication;
  // A dispute is between replications: reviews and re-runs, however they disagree, never make a claim contested (the dispute number still ranks it).
  if (x.sReplication > 0 && x.fReplication > 0 && 4 * r * (1 - r) >= P.contestedAt) return "contested";
  if (x.credence <= P.refutedBelow && x.failingReplication) return "refuted";
  if (x.foundationRefuted) return "contested";
  // Established: two or more independent verified replications (distinct operators) on two or more declared model families.
  if (x.credence >= x.threshold && x.confirmingReplication && x.confirmingFamilies >= P.familiesForEstablished && (x.confirmingOperators ?? P.operatorsForEstablished) >= P.operatorsForEstablished) return "established";
  if (x.confirmingReplication && x.credence >= P.supportedFrom) return "supported";
  if (!anyReplication) return "unchecked";
  return "contested";
}

/** Families that count towards "established": each DECLARED family once; undeclared ("?") is no family (Daniel, 3 Oct: two declared families). */
export function familyCount(fams: ReadonlySet<string>): number {
  return fams.size - (fams.has("?") ? 1 : 0);
}

/**
 * What a foundation contributes to the prior of a claim resting on it: its
 * credence; for a registered human claim, face value until verified
 * evidence counts against it, then min(1, p_verified / q̃).
 */
export function foundationFactor(x: Pick<ClaimV2, "external" | "credence" | "credenceVerified" | "prior">): number {
  return x.external ? Math.min(1, x.credenceVerified / x.prior) : x.credence;
}

/** The same factor if the foundation gained one more confirming replication at full weight. */
function raisedFoundationFactor(x: Pick<ClaimV2, "external" | "credence" | "credenceVerified" | "prior">): number {
  return x.external ? Math.min(1, sigma(logit(x.credenceVerified) + P.confirm) / x.prior) : sigma(logit(x.credence) + P.confirm);
}

/**
 * Settled arguments' log-odds on a claim (arguments/0.1). Verified arguers'
 * effects count towards the verified sum, which the statuses are tested
 * against; other arguers' upheld attacks are capped on their own at the
 * unverified cap. Corroboration (dismissed attacks) counts from verified
 * arguers only, capped.
 */
export function sumArguments(a: ClaimArgumentsInput | undefined): { verified: number; other: number } {
  if (!a) return { verified: 0, other: 0 };
  const A = ARGUMENT_PARAMS;
  let verified = 0;
  let other = 0;
  for (const x of a.upheldAttacks) {
    const v = -A.upheldStep * P.tier[x.tier];
    if (x.tier === "verified") verified += v; else other += v;
  }
  const corroboration = a.dismissedAttacks.filter((x) => x.tier === "verified").length * A.corroborationStep;
  verified += Math.min(A.corroborationCap, corroboration);
  if (a.refuted) verified -= A.counterexampleStep;
  return { verified, other: Math.max(-P.unverifiedCap, other) };
}

/**
 * A conceptual claim's status: refuted by an upheld counterexample; contested
 * under a contradiction cap; supported once attacks from enough distinct
 * verified arguers have been dismissed and the verified credence clears the
 * supported bar; else unchecked. Never established.
 */
export function conceptualStatusOf(credenceVerified: number, a: ClaimArgumentsInput | undefined, capped: boolean): ClaimStatusV2 {
  if (a?.refuted) return "refuted";
  if (capped) return "contested";
  const dismissed = a ? a.dismissedAttacks.filter((x) => x.tier === "verified").length : 0;
  return dismissed >= ARGUMENT_PARAMS.supportedAttacks && credenceVerified >= P.supportedFrom ? "supported" : "unchecked";
}

/**
 * Every claim's credence, use, dispute and status, and what would raise it
 * most. Claims are processed in log order, each with all its evidence, so
 * a claim's prior uses its foundations' current credence. Contradiction
 * caps need the cited claims' numbers, so the computation runs twice when
 * any applies: the first pass finds the caps, the second applies them where
 * every dependant can see them.
 */
export function computeCredenceV2(
  claims: ClaimInput[],
  evidence: EvidenceInput[],
  uses: UseInput[],
  o: CredenceV2Options = {},
): Map<string, ClaimV2> {
  const first = credencePass(claims, evidence, uses, o, new Map());
  const caps = new Map<string, number>();
  for (const c of claims) {
    const a = o.arguments?.get(c.ref);
    if (!a || a.contradictions.length === 0) continue;
    let cap = Infinity;
    for (const ref of a.contradictions) {
      const cited = first.get(ref);
      if (cited && ref !== c.ref && cited.status === "established") cap = Math.min(cap, 1 - cited.credence);
    }
    if (cap < Infinity) caps.set(c.ref, Math.max(1e-6, cap));
  }
  return caps.size ? credencePass(claims, evidence, uses, o, caps) : first;
}

function credencePass(claims: ClaimInput[], evidence: EvidenceInput[], uses: UseInput[], o: CredenceV2Options, caps: Map<string, number>): Map<string, ClaimV2> {
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
    const w = independence(u.operatorId, a, o.vouchLinked, o.ringLinked) * P.tier[u.tier ?? "unverified"];
    const m = useBy.get(u.claim) ?? new Map<string, number>();
    m.set(u.paper, Math.max(m.get(u.paper) ?? 0, w));
    useBy.set(u.claim, m);
  }
  // The calibration record: per author operator, the stated confidence and truth of each claim resolved so far. A claim
  // joins the record only once the log has moved past its position, so the claims of one paper never feed each other.
  const record = new Map<string, Array<{ stated: number; truth: 0 | 1 }>>();
  let pending: Array<{ op: string; stated: number; truth: 0 | 1 }> = [];
  let pendingSeq: number | null = null;
  const flush = () => {
    for (const p of pending) record.set(p.op, [...(record.get(p.op) ?? []), { stated: p.stated, truth: p.truth }]);
    pending = [];
  };
  for (const c of sorted) {
    if (pendingSeq !== null && c.seq !== pendingSeq) flush();
    pendingSeq = c.seq;
    const kind: ClaimKind = c.kind === "conceptual" ? "conceptual" : "empirical";
    const args = o.arguments?.get(c.ref);
    const found = c.foundations.map((ref) => out.get(ref)).filter((x): x is ClaimV2 => !!x);
    // arguments/0.1: each upheld methodological assessment halves the weight of the author's stated confidence.
    const calibration = (c.calibration ?? calibrationOf(record.get(c.authorOperator) ?? [])) * ARGUMENT_PARAMS.methodologyFactor ** (args?.methodology ?? 0);
    const prior = priorOf(c.stated, calibration, found.map(foundationFactor));
    const ev = sumEvidence(byClaim.get(c.ref) ?? [], c.authorOperator, o);
    const arg = sumArguments(args);
    const cap = caps.get(c.ref) ?? null;
    const capped = (p: number) => (cap === null ? p : Math.min(p, cap));
    const total = ev.sum + arg.verified + arg.other;
    const credence = capped(sigma(clampLogOdds(logit(prior) + total)));
    const logOdds = logit(credence);
    const credenceVerified = capped(sigma(clampLogOdds(logit(prior) + ev.sumVerified + arg.verified)));
    const use = [...(useBy.get(c.ref)?.values() ?? [])].reduce((x, y) => x + y, 0);
    const threshold = thresholdOf(use);
    const foundationRefuted = found.some((x) => x.status === "refuted");
    const statusAt = (bar: number): ClaimStatusV2 => {
      if (kind === "conceptual") return conceptualStatusOf(credenceVerified, args, cap !== null);
      const st = statusOf({
        credence: credenceVerified, sReplication: ev.sReplication, fReplication: ev.fReplication, threshold: bar,
        confirmingReplication: ev.confirmingReplication, failingReplication: ev.failingReplication,
        confirmingFamilies: familyCount(ev.confirmingFamilies), confirmingOperators: ev.confirmingOperators,
        foundationRefuted,
      });
      // An upheld contradiction with an established claim leaves an empirical claim contested too, unless the evidence already refutes it.
      return cap !== null && st !== "refuted" ? "contested" : st;
    };
    const status = statusAt(threshold);
    // Resolved at the bar for zero use: a citation raises what a claim must clear to READ established, never what a record is judged against.
    const resolved = resolutionOf(statusAt(thresholdOf(0)), o.anchors?.get(c.ref));
    if (resolved !== null && c.calibration === undefined && c.authorOperator) pending.push({ op: c.authorOperator, stated: c.stated, truth: resolved });
    const dispute = disputeOf(ev.s, ev.f);
    sums.set(c.ref, total);
    out.set(c.ref, {
      ref: c.ref, paper: c.paper, external: c.external === true, kind, cap, calibration, prior, logOdds, credence, credenceVerified, s: ev.s, f: ev.f, dispute, use, threshold, status, resolved,
      arguments: { upheld: args?.upheldAttacks.length ?? 0, dismissed: args?.dismissedAttacks.length ?? 0, open: args?.open ?? 0, methodology: args?.methodology ?? 0, counterexample: args?.refuted ?? false },
      reproduced: ev.reproduced,
      families: [...ev.confirmingFamilies].filter((x) => x !== "?").sort(),
      valueOfChecking: (use + 0.5) * credence * (1 - credence),
      disputePriority: (use + 0.5) * dispute,
      foundations: found.map((x) => ({ ref: x.ref, credence: x.credence, status: x.status, factor: foundationFactor(x) })),
      disputedFoundation: found.some((x) => x.status === "contested"),
      lift: [],
    });
  }
  // What would raise each claim most: one more confirming replication (full weight) of each foundation.
  for (const c of sorted) {
    const me = out.get(c.ref)!;
    if (me.foundations.length === 0) continue;
    const found = me.foundations.map((fd) => out.get(fd.ref)!);
    const base = found.map(foundationFactor);
    me.lift = found
      .map((fd, i) => {
        const raised = base.map((v, j) => (j === i ? raisedFoundationFactor(fd) : v));
        const to = sigma(clampLogOdds(logit(priorOf(c.stated, me.calibration, raised)) + (sums.get(c.ref) ?? 0)));
        return { ref: fd.ref, from: me.credence, to, gain: to - me.credence };
      })
      .sort((a, b) => b.gain - a.gain || (a.ref < b.ref ? -1 : 1));
  }
  return out;
}
