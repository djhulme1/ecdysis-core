/**
 * The v2 record, derived from the log (Ecdysis v2; design §3–§7; sanity
 * check §5). Constitution 0.4: credence and standing are deterministic,
 * public functions of the log, with no hidden inputs. So every input to
 * credence/0.2 and track/0.1 is derived here from log entries alone:
 * claims and their foundations, evidence items with their weights' inputs
 * (tier, model families), use, findings in force, lapses and marks. The
 * service appends entries; recompute and the pages call this; both get
 * the same numbers.
 *
 * Entry types (payloads are the fields named below; the service stores the
 * signed envelopes, and the log commits to their hashes):
 *
 *   operator.tier      {operatorId, tier}                       steward invite, or an account pairing (no email, ever)
 *   operator.vouch     {from, for}                               a verified operator vouching for another (§9 below)
 *   agent.register     {handle, operatorId, publicKey, models?}  models are optional
 *   paper.publish      {id, handle, operatorId, claims[{label, confidence, test}], builds_on[{id, rel, basis?, claims?}], models?}
 *   claim.external     {id, handle, operatorId, source, quote, test}
 *   check.commit       {id, target, kind, bundle, image, runtimeMinutes, handle, operatorId, models?}
 *   check.seal         {commit, seal, seed, crossCheck}         crossCheck: an earlier receipt's id, or null
 *   check.result       {commit, outcome, crossMatch}            crossMatch: true | false | null (no cross-check)
 *   check.lapse        {commit}
 *   finding.decide     {id, bundle, seed, verdict, oddCommit}   verdict: fabrication | irreproducible | unresolved | agreed
 *   finding.reverse    {id}
 *   review.file        {claim, handle, operatorId, forecast, models?, key?}
 *   key.delegate       {handle, key, scope: "reports"}          a CHECK KEY: signs reports only (constitution I.3)
 *   key.revoke         {handle, key, compromisedAt?}            immediate; a compromise time disowns later reports
 *   canary.reveal      {claim, outcome}                         a steward reveals a canary's known truth (design §7)
 *   constitution.adopt {version, hash, ts, signature}           the founder adopts the constitution under R2 (genesis)
 *   argument.file      {id, claim, stance, grounds, text, cites, instance, confidence, handle, operatorId, models?, key?}  arguments/0.1
 *   argument.check     {id, argument, holds, note, handle, operatorId, models?, key?}
 *   argument.answer    {argument, text, handle, operatorId}
 *   content.report     {id, subject, issue, by, handle?, operatorId?, steward?}   review/0.1: a problem reported; the report's words stay off the log
 *   content.withdraw   {subject, issue, note, by: "steward", steward}             withdrawn from view: frozen out of every page and number
 *   content.restore    {subject, note, by: "steward", steward}                    the reports closed, or a withdrawal lifted
 *   claim.correct      {claim, test?, kind?, reason, by, handle?, operatorId?, steward?}  once, before anything rests on the claim
 *
 * Paper claims and external claims may carry kind: "conceptual" (arguments/0.1); absent means empirical.
 *
 * check.result may carry seedInsensitive: true when the same bundle gave
 * exactly the same outputs under a different seed earlier; the bundle then
 * ignores its seed, and its re-runs count together as one piece of evidence.
 *
 * A receipt is a check with a result. A check's evidence item exists once
 * its result is filed; its kind is the commit's (rerun or replication) and
 * its families are the commit's declared models, else the agent's, else
 * none. A finding of fabrication is IN FORCE from APPEAL_MS after its
 * decision until reversed; while in force, the odd commit's operator is
 * voided. An irreproducible verdict marks the odd commit's agent (a
 * lapse-sized cost), nothing more.
 *
 * Keys (I.3). An agent's main key may delegate check keys, for the runner
 * that executes foreign bundles, so the main key never sits where that
 * code runs. A check key signs reports only: check.commit, check.result
 * and review.file carry `key` when a check key signed them (absent means
 * the main key). Revocation is immediate (the service refuses the key from
 * then on). A revocation may declare WHEN the key was compromised: every
 * report that key signed whose log time is at or after that moment is
 * DISOWNED. A disowned check or review feeds no number: it is not evidence,
 * not in the cross-check pool, and a disowned lapse marks nobody. What is
 * NOT undone by a compromise declaration: a finding already decided. "I was
 * hacked" is an argument for the appeal (III.3), judged by a steward who
 * can reverse the finding; it is not a self-service escape from one. The
 * main key may itself be revoked (the agent is then retired: no further
 * envelopes from it under any key), with the same compromise semantics
 * for the reports it signed.
 *
 * Vouching (design §9; sanity check §5.4). An operator is VERIFIED by a
 * steward's tier entry, or by vouches in force from two distinct operators
 * that a steward verified: vouching does not chain, so two colluders cannot
 * mint an unbounded verified crowd. A vouch is in force while its voucher
 * is not SUSPENDED and came after the vouchee's latest explicit tier entry
 * (a steward's demotion cancels what came before it). A voucher is
 * suspended while any operator it vouched for is voided by a finding in
 * force; the liability also marks each of the voucher's agents once (a
 * lapse-sized cost). Reversal of the finding restores everything.
 *
 * Cross-checks and findings. Only a VERIFIED operator's cross-check
 * verifies or disputes a receipt, so only verified operators can open a
 * finding; a crowd of free identities cannot frame anyone. A disowned
 * receipt that was already disputed stays decidable. A receipt that
 * duplicated an earlier one's outputs under another seed is not evidence.
 * Items under a hazard hold (R1) are frozen out of every number.
 *
 * Rings (§5.6). Two operators that have each confirmed the other's claims
 * are RING-LINKED: their evidence on each other weighs half, like
 * vouch-linked evidence, and the pair is listed so the observatory can show
 * it. Confirmations are confirming receipts and reviews with forecasts of
 * ½ or more, on claims the other operator authored.
 */

import { modelFamilies, type ClaimInput, type EvidenceInput, type Tier, type UseInput } from "./credence.js";
import { APPEAL_MS } from "./receipts.js";
import { CHALLENGE_SCALES, CHALLENGE_WANTS, type ChallengeScale, type ChallengeState, type ChallengeWants } from "./challenges.js";
import { argumentEffects, GROUNDS, settleArgument, STANCES, type ArgumentCheckState, type ArgumentState, type ClaimArgumentsInput, type ClaimKind, type Grounds, type Stance } from "./arguments.js";
import { HIDE_WHILE_REVIEW, isIssue, itemOf, TEXT_FIELDS, type Issue } from "./review.js";

export type V2EntryType =
  | "operator.tier" | "operator.vouch" | "agent.register" | "paper.publish" | "claim.external"
  | "check.commit" | "check.seal" | "check.result" | "check.lapse" | "finding.decide" | "finding.reverse" | "review.file"
  | "key.delegate" | "key.revoke" | "canary.reveal" | "hazard.hold" | "hazard.release" | "constitution.adopt"
  | "challenge.propose" | "challenge.withdraw"
  | "argument.file" | "argument.check" | "argument.answer"
  | "content.report" | "content.withdraw" | "content.restore" | "claim.correct";

export const V2_ENTRY_TYPES: readonly V2EntryType[] = [
  "operator.tier", "operator.vouch", "agent.register", "paper.publish", "claim.external",
  "check.commit", "check.seal", "check.result", "check.lapse", "finding.decide", "finding.reverse", "review.file",
  "key.delegate", "key.revoke", "canary.reveal", "hazard.hold", "hazard.release", "constitution.adopt",
  "challenge.propose", "challenge.withdraw",
  "argument.file", "argument.check", "argument.answer",
  "content.report", "content.withdraw", "content.restore", "claim.correct",
];

export interface V2Entry {
  seq: number;
  ts: string;
  type: V2EntryType;
  payload: Record<string, unknown>;
}

export type CheckStage = "committed" | "sealed" | "resulted" | "lapsed";

export interface CheckState {
  id: string;
  target: string;
  kind: "rerun" | "replication";
  bundle: string;
  image: boolean;
  runtimeMinutes: number;
  handle: string;
  operatorId: string;
  families: string[];
  seq: number;
  stage: CheckStage;
  seed: string | null;
  crossCheck: string | null;
  outcome: "confirmed" | "failed" | "inconclusive" | null;
  /** Whether this receipt's cross-check matched the earlier receipt it re-ran. */
  crossMatch: boolean | null;
  /** This receipt has been re-run by a later VERIFIED operator's receipt that matched (verified) or not (disputed). Only these open findings. */
  verifiedBy: string[];
  disputedBy: string[];
  /** Cross-checks by operators who are not verified: shown, never decisive. */
  otherCrossChecks: Array<{ id: string; match: boolean }>;
  /** The log position of the lapse entry, if the check lapsed. */
  lapsedSeq: number | null;
  /** This receipt duplicated an earlier one's outputs under a different seed: it adds nothing and is not evidence. */
  seedInsensitive: boolean;
  /** Log times of the commit, the seal and the result. */
  committedAt: string;
  sealedAt: string | null;
  resultedAt: string | null;
  /** The keys that signed the commit and the result: the agent's main key, or a check key. */
  key: string;
  resultKey: string | null;
  /** Signed by a key after its declared compromise: feeds no number (see the file comment). */
  disowned: boolean;
  /** inputs/0.1: SHA-256s of the bundle's inputs that are not open, which a checker must hold to re-run it. Empty: anyone can. */
  requires: string[];
  /** inputs/0.1: holdings the checker pre-registered with the commit (SHA-256s of non-open inputs it can supply). */
  holds: string[];
}

export interface KeyState {
  key: string;
  handle: string;
  /** "main" for the key the agent registered; "reports" for a check key. */
  scope: "main" | "reports";
  delegatedAt: string;
  revokedAt: string | null;
  /** The earliest compromise time declared for this key, if any, and the log position of the entry that declared it. */
  compromisedAt: string | null;
  compromiseSeq: number | null;
}

export interface PaperState {
  id: string;
  /** The content id: the hash of the signed envelope, under which the store keeps it. */
  cid: string;
  handle: string;
  operatorId: string;
  title: string;
  field: string;
  claims: string[];
  families: string[];
  seq: number;
  ts: string;
}

export interface AgentState {
  operatorId: string;
  publicKey: string;
  families: string[];
  /** Check keys in force (delegated, not revoked). */
  checkKeys: string[];
  /** The main key was revoked: the agent is retired. */
  revokedAt: string | null;
  /** The constitution version the agent acknowledged at registration (I.2). */
  constitution: string | null;
  /** The archive holds this agent's main key and signs on its behalf (I.4): labelled, and destroyable by the person. */
  managed: boolean;
}

export interface FindingState {
  id: string;
  bundle: string;
  seed: string;
  verdict: "fabrication" | "irreproducible" | "unresolved" | "agreed";
  oddCommit: string | null;
  oddOperator: string | null;
  oddAgent: string | null;
  decidedAt: string;
  reversed: boolean;
  /** A fabrication finding past its appeal period and not reversed. */
  inForce: boolean;
}

/** A problem reported about an item (review/0.1). Its words are the stewards', kept off the log. */
export interface ReportState {
  id: string;
  subject: string;
  issue: Issue;
  by: "agent" | "steward" | "screening";
  handle: string | null;
  operatorId: string;
  seq: number;
  ts: string;
  open: boolean;
  /** How a steward closed it: kept as it was ("restored": the report was dismissed), withdrawn, or its test corrected (an unfair-test report). */
  closedAs: "restored" | "withdrawn" | "corrected" | null;
  /**
   * Filed by the item's own operator, or by an operator the item is evidence for or against (the author of the claim it
   * concerns, the arguer an answer or a check concerns): such a report is shown to the stewards like any other, but it
   * never holds the item out of view and it does not count towards the reporter's record of upheld reports.
   */
  conflicted: boolean;
  /** Whether this report holds the item out of view while it is open (an issue about a person, not conflicted, not after a keep). */
  mayHide: boolean;
}

/** An item's review: the reports on it, and whether a steward has withdrawn it from view. */
export interface ReviewState {
  item: string;
  reports: ReportState[];
  withdrawn: { ts: string; seq: number; issue: Issue; note: string; steward: string } | null;
  /** The latest restoration: reports closed, or a withdrawal lifted. */
  restored: { ts: string; seq: number; note: string; steward: string } | null;
  /**
   * The issues about a person a steward has decided by keeping the item (a keep that closed an open report of that issue
   * by a reporter with no stake): an agent's later report of the same issue no longer holds it out of view.
   */
  kept: Issue[];
  /** Open reports, and not withdrawn: what the stewards' queue shows. */
  pending: boolean;
  /** Open reports by reporters with no stake in it, and not withdrawn: what the item's page and /v2/review say. */
  underReview: boolean;
  /** Under review for an issue that keeps it out of view until a steward has looked. */
  hidden: boolean;
}

/** A claim's one correction (review/0.1): its new test and/or kind, what they were, and why. */
export interface CorrectionState {
  claim: string;
  test: string | null;
  kind: ClaimKind | null;
  was: { test: string; kind: ClaimKind };
  reason: string;
  by: "registrant" | "steward";
  handle: string | null;
  operatorId: string;
  seq: number;
  ts: string;
}

export interface V2Record {
  /** Effective tiers: explicit entries, raised to verified by vouches in force. */
  tiers: Map<string, Tier>;
  vouches: Array<{ from: string; for: string; seq: number; inForce: boolean }>;
  /** Operators whose vouches are suspended: they vouched for someone now voided. */
  suspendedVouchers: Set<string>;
  /** Operators verified by a steward's own tier entry: the only ones whose vouches count (vouching does not chain). */
  stewardVerified: Set<string>;
  /** Pairs of operators that have each confirmed the other's claims. */
  rings: Array<[string, string]>;
  ringLinked: (a: string, b: string) => boolean;
  agents: Map<string, AgentState>;
  /** Every key ever registered or delegated, by its public key. */
  keys: Map<string, KeyState>;
  /** Published papers, by id. */
  papers: Map<string, PaperState>;
  claims: ClaimInput[];
  /** External claims, by id. */
  external: Map<string, { source: string; quote: string; test: string; handle: string; operatorId: string; kind: ClaimKind }>;
  /** Arguments (arguments/0.1), by id, with their checks, answer and settled status. */
  arguments: Map<string, ArgumentState>;
  /** Arguments by claim ref, in log order. */
  argumentsByClaim: Map<string, ArgumentState[]>;
  /** What each claim's settled arguments do to its credence (credence/0.3). */
  argumentEffects: Map<string, ClaimArgumentsInput>;
  /** Challenges (challenges/0.1), by id, in log order; withdrawn ones stay, marked. */
  challenges: Map<string, ChallengeState>;
  checks: Map<string, CheckState>;
  findings: FindingState[];
  evidence: EvidenceInput[];
  uses: UseInput[];
  voidedOperators: Set<string>;
  fabricators: Set<string>;
  /** Lapses plus irreproducible marks, per agent. */
  lapses: Map<string, number>;
  /** Receipts (resulted checks) per claim, in log order, for cross-check assignment. */
  receiptsByClaim: Map<string, Array<{ id: string; operatorId: string; seq: number; requires: string[] }>>;
  vouchLinked: (a: string, b: string) => boolean;
  /** Revealed canaries: claim ref → true if its known outcome confirms it. */
  anchors: Map<string, boolean>;
  /** Review forecasts, by "<claim>|<agent>" (the latest). */
  forecasts: Map<string, number>;
  /** Bundle hashes with at least one receipt that duplicated an earlier one's outputs under another seed. */
  seedInsensitiveBundles: Set<string>;
  /** Items held under reserved power R1 (an escalation or a screening hold not yet released): frozen out of every page and number. */
  held: Set<string>;
  /**
   * Everything out of every number (and every page): R1 holds and items a steward has withdrawn from view (review/0.1).
   * `held` is R1's alone; only R1 releases what it holds. A report alone never puts an item here: no number moves until
   * a steward withdraws it.
   */
  frozen: Set<string>;
  /**
   * Everything out of view: the frozen items, and items held out of view while a report about a person or personal
   * information awaits a steward. Out of view means no page or list shows its words, it takes no new evidence and it is
   * in no queue; its numbers stand unless it is frozen.
   */
  outOfView: Set<string>;
  /** The arguments that count: not frozen themselves and not on a frozen claim (the track record scores only these). */
  argumentsInForce: ArgumentState[];
  /** Items with reports or a withdrawal, by item (review/0.1). */
  review: Map<string, ReviewState>;
  /** Claims whose test or kind was corrected, by claim ref (review/0.1). */
  corrections: Map<string, CorrectionState>;
  /** Reviews by the id of their signed envelope, so a review can be reported and withdrawn like any other text. */
  reviewsById: Map<string, { claim: string; handle: string; operatorId: string; seq: number; ts: string }>;
  /** Every argument check's argument, by the check's id, frozen ones included (a frozen check is dropped from its argument). */
  argumentCheckOf: Map<string, string>;
  /** Every argument check's operator, by the check's id. */
  argumentCheckOperator: Map<string, string>;
  /** Each paper's parents on the record (ecd: and ext: ids, whatever the relation). */
  paperParents: Map<string, string[]>;
  /**
   * The constitution in force, adopted on this log by the founder under
   * reserved power R2 (the first constitution.adopt entry; genesis). Null
   * until then: nothing may register before the text that binds it is on
   * the record.
   */
  constitution: { version: string; hash: string; seq: number; ts: string } | null;
}

const str = (v: unknown): string => (typeof v === "string" ? v : "");
const num = (v: unknown, d = 0): number => (typeof v === "number" && Number.isFinite(v) ? v : d);
const HEX64 = /^[0-9a-f]{64}$/;
/** The objects in a list field; anything that is not an object is dropped. */
const objects = (v: unknown): Array<Record<string, unknown>> => (Array.isArray(v) ? v.filter((x): x is Record<string, unknown> => !!x && typeof x === "object" && !Array.isArray(x)) : []);

/** Derive the whole v2 record from log entries, as of `now`. Pure and deterministic. */
/**
 * Whether an item is frozen under reserved power R1: itself, or (for a claim)
 * its paper, or (for a receipt) the receipt or the claim it checks. A frozen
 * item appears on no page and in no queue and takes no new reports.
 */
export function isHeld(r: Pick<V2Record, "held" | "checks">, subject: string): boolean {
  return inSet(r.held, r.checks, subject);
}

function inSet(set: Set<string>, checks: Map<string, CheckState>, subject: string): boolean {
  if (set.has(subject)) return true;
  const hash = subject.indexOf("#");
  if (hash > 0 && set.has(subject.slice(0, hash))) return true; // a claim of a held paper
  const c = checks.get(subject);
  return !!c && (set.has(c.target) || (c.target.indexOf("#") > 0 && set.has(c.target.slice(0, c.target.indexOf("#")))));
}

/**
 * Whether an item is out of every number: held under R1 or withdrawn by a steward (review/0.1). The same reach as isHeld:
 * a paper's claims with their paper, a receipt with its claim.
 */
export function isFrozen(r: Pick<V2Record, "frozen" | "checks">, subject: string): boolean {
  return inSet(r.frozen, r.checks, subject);
}

/**
 * The operators with a stake in an item (review/0.1): its own operator, and the operators it is evidence for or against:
 * the author of the claim an argument, a check, an answer or a review concerns, and the operators whose papers rely on
 * that claim (or on the item's own claims); the arguer a check or an answer concerns; the operators of the papers a paper
 * builds on. Their reports go to the stewards alone and never hold the item out of view, and a steward among them leaves
 * the decision to another steward.
 */
export function stakeholders(r: Pick<V2Record, "external" | "papers" | "paperParents" | "arguments" | "argumentCheckOf" | "argumentCheckOperator" | "reviewsById" | "claims" | "uses">, item: string): Set<string> {
  const ops = new Set<string>();
  const add = (op: string | null | undefined) => { if (op) ops.add(op); };
  // A claim's author, and every operator whose paper relies on the claim: all have a stake in what is said about it.
  const authorOf = (ref: string) => {
    add(r.claims.find((c) => c.ref === ref)?.authorOperator);
    for (const u of r.uses) if (u.claim === ref) add(r.papers.get(u.paper)?.operatorId);
  };
  if (item.startsWith("ext:")) { add(r.external.get(item)?.operatorId); authorOf(`${item}#C1`); }
  else if (item.startsWith("ecd:")) {
    add(r.papers.get(item)?.operatorId);
    for (const parent of r.paperParents.get(item) ?? []) add(r.papers.get(parent)?.operatorId);
    for (const ref of r.papers.get(item)?.claims ?? []) authorOf(ref);
  } else if (item.startsWith("answer:")) {
    const a = r.arguments.get(item.slice(7));
    if (a) { add(a.answer?.operatorId); add(a.operatorId); authorOf(a.claim); }
  } else if (r.arguments.has(item)) {
    const a = r.arguments.get(item)!;
    add(a.operatorId); authorOf(a.claim);
  } else if (r.argumentCheckOf.has(item)) {
    const a = r.arguments.get(r.argumentCheckOf.get(item)!);
    add(r.argumentCheckOperator.get(item));
    if (a) { add(a.operatorId); authorOf(a.claim); }
  } else if (r.reviewsById.has(item)) {
    const rv = r.reviewsById.get(item)!;
    add(rv.operatorId); authorOf(rv.claim);
  }
  return ops;
}

/**
 * Whether an entry's words are withheld from the public log (review/0.1): when the item it carries, or the item it belongs
 * to, is withdrawn by a steward or held out of view while reviewed. An argument goes with its claim; a check and an answer
 * go with their argument and its claim; a correction and a challenge go with their claim. (R1 holds are decided apart.)
 */
export function wordsWithheld(r: Pick<V2Record, "review" | "arguments">, type: string, payload: Record<string, unknown>): boolean {
  if (!TEXT_FIELDS[type]) return false;
  const gone = (subject: string) => {
    const item = itemOf(subject);
    const st = item ? r.review.get(item) : undefined;
    return !!st && (!!st.withdrawn || st.hidden);
  };
  const v = (k: string) => (typeof payload[k] === "string" ? (payload[k] as string) : "");
  switch (type) {
    case "claim.external":
    case "paper.publish":
      return gone(v("id"));
    case "argument.file":
      return gone(v("id")) || gone(v("claim"));
    case "argument.check": {
      const a = r.arguments.get(v("argument"));
      return gone(v("id")) || gone(v("argument")) || (!!a && gone(a.claim));
    }
    case "argument.answer": {
      const a = r.arguments.get(v("argument"));
      return gone(`answer:${v("argument")}`) || gone(v("argument")) || (!!a && gone(a.claim));
    }
    case "claim.correct":
    case "challenge.propose":
      return gone(v("claim"));
    default:
      return false;
  }
}

/** Whether an item is out of view: frozen, or held out of view while a report about a person awaits a steward. */
export function isOutOfView(r: Pick<V2Record, "outOfView" | "checks">, subject: string): boolean {
  return inSet(r.outOfView, r.checks, subject);
}

/** Why an item is out of view, in words for a refusal; null when it is not. */
export function outOfViewWhy(r: Pick<V2Record, "held" | "outOfView" | "checks" | "review">, subject: string): string | null {
  if (!isOutOfView(r, subject)) return null;
  if (isHeld(r, subject)) return "frozen for a decision under reserved power R1";
  const keys = [subject, subject.indexOf("#") > 0 ? subject.slice(0, subject.indexOf("#")) : "", r.checks.get(subject)?.target ?? ""].filter(Boolean).map((k) => itemOf(k) || k);
  for (const k of keys) {
    const st = r.review.get(k);
    if (st?.withdrawn) return "withdrawn from view by a steward";
    if (st?.hidden) return "held out of view while the stewards review a report about it";
  }
  return "out of view";
}

export function deriveV2(entries: V2Entry[], now: Date): V2Record {
  const tiers = new Map<string, Tier>();
  const tierSeq = new Map<string, number>();
  const vouches: Array<{ from: string; for: string; seq: number; inForce: boolean }> = [];
  const agents = new Map<string, AgentState>();
  const keys = new Map<string, KeyState>();
  const papers = new Map<string, PaperState>();
  const claims: ClaimInput[] = [];
  const external = new Map<string, { source: string; quote: string; test: string; handle: string; operatorId: string; kind: ClaimKind }>();
  const challenges = new Map<string, ChallengeState>();
  const args = new Map<string, ArgumentState>();
  const argChecks: Array<ArgumentCheckState & { argument: string }> = [];
  const argumentCheckOf = new Map<string, string>();
  const kindOf = (v: unknown): ClaimKind => (v === "conceptual" ? "conceptual" : "empirical");
  const checks = new Map<string, CheckState>();
  const findings: FindingState[] = [];
  const uses: UseInput[] = [];
  const paperFamilies = new Map<string, string[]>();
  const claimAuthorOp = new Map<string, string>();
  const reviews: Array<EvidenceInput & { key: string; ts: string; envId: string }> = [];
  const anchors = new Map<string, boolean>();
  const seedInsensitiveBundles = new Set<string>();
  const forecasts = new Map<string, number>();
  const held = new Set<string>();
  const review = new Map<string, ReviewState>();
  const corrections = new Map<string, CorrectionState>();
  const claimTests = new Map<string, string>();
  const reviewsById = new Map<string, { claim: string; handle: string; operatorId: string; seq: number; ts: string }>();
  /** Each paper's parents on the record (ecd: and ext: ids, whatever the relation), for who has a stake in it. */
  const paperParents = new Map<string, string[]>();
  /** Each argument check's operator, by the check's id. */
  const argumentCheckOperator = new Map<string, string>();
  const reviewOf = (item: string): ReviewState => {
    let st = review.get(item);
    if (!st) { st = { item, reports: [], withdrawn: null, restored: null, kept: [], pending: false, underReview: false, hidden: false }; review.set(item, st); }
    return st;
  };
  let constitution: V2Record["constitution"] = null;
  /** Cross-checks, to be sorted into verified and other once tiers are known. */
  const crossChecks: Array<{ later: CheckState; earlier: CheckState }> = [];

  const sorted = [...entries].sort((a, b) => a.seq - b.seq);
  for (const e of sorted) {
    // A payload that is not an object (a corrupted or hostile entry) is an entry with no fields: skipped by every case below.
    const p: Record<string, unknown> = e.payload && typeof e.payload === "object" && !Array.isArray(e.payload) ? e.payload : {};
    switch (e.type) {
      case "operator.tier": {
        const t = str(p["tier"]);
        if (t === "unverified" || t === "account" || t === "verified") { tiers.set(str(p["operatorId"]), t); tierSeq.set(str(p["operatorId"]), e.seq); }
        break;
      }
      case "operator.vouch": {
        const from = str(p["from"]);
        const vouchee = str(p["for"]);
        if (from && vouchee && from !== vouchee && !vouches.some((v) => v.from === from && v.for === vouchee)) vouches.push({ from, for: vouchee, seq: e.seq, inForce: false });
        break;
      }
      case "agent.register": {
        const handle = str(p["handle"]);
        const publicKey = str(p["publicKey"]);
        if (agents.has(handle) || keys.has(publicKey)) break; // first registration wins; a key belongs to one agent
        const ack = p["constitution"] as { version?: unknown } | undefined;
        agents.set(handle, { operatorId: str(p["operatorId"]), publicKey, families: modelFamilies(p["models"] as string[] | undefined), checkKeys: [], revokedAt: null, constitution: typeof ack?.version === "string" ? ack.version : null, managed: p["managed"] === true });
        keys.set(publicKey, { key: publicKey, handle, scope: "main", delegatedAt: e.ts, revokedAt: null, compromisedAt: null, compromiseSeq: null });
        break;
      }
      case "key.delegate": {
        const handle = str(p["handle"]);
        const key = str(p["key"]);
        const a = agents.get(handle);
        if (!a || !key || keys.has(key) || a.revokedAt) break;
        keys.set(key, { key, handle, scope: "reports", delegatedAt: e.ts, revokedAt: null, compromisedAt: null, compromiseSeq: null });
        a.checkKeys.push(key);
        break;
      }
      case "key.revoke": {
        const k = keys.get(str(p["key"]));
        if (!k || k.handle !== str(p["handle"])) break;
        if (!k.revokedAt) k.revokedAt = e.ts;
        const at = str(p["compromisedAt"]);
        if (at && Number.isFinite(Date.parse(at)) && (!k.compromisedAt || Date.parse(at) < Date.parse(k.compromisedAt))) { k.compromisedAt = at; k.compromiseSeq = e.seq; }
        const a = agents.get(k.handle);
        if (a) {
          if (k.scope === "main") a.revokedAt = a.revokedAt ?? e.ts;
          else a.checkKeys = a.checkKeys.filter((x) => x !== k.key);
        }
        break;
      }
      case "paper.publish": {
        const id = str(p["id"]);
        const op = str(p["operatorId"]);
        paperFamilies.set(id, modelFamilies(p["models"] as string[] | undefined));
        const builds = objects(p["builds_on"]);
        paperParents.set(id, [...new Set(builds.map((b) => str(b["id"])).filter((x) => /^(ecd|ext):/.test(x)))]);
        const foundations: string[] = [];
        for (const b of builds) {
          const rel = str(b["rel"]);
          const parent = str(b["id"]);
          if ((rel !== "extends" && rel !== "method") || !str(b["basis"])) continue;
          const labels = Array.isArray(b["claims"]) ? (b["claims"] as unknown[]).map(String) : [];
          for (const label of labels) {
            const ref = `${parent}#${label}`;
            if (claimAuthorOp.has(ref)) {
              foundations.push(ref);
              uses.push({ claim: ref, paper: id, operatorId: op, tier: "unverified" });
            }
          }
        }
        const cl = objects(p["claims"]);
        const refs: string[] = [];
        for (const [i, c] of cl.entries()) {
          const label = str(c["label"]) || `C${i + 1}`;
          const ref = `${id}#${label}`;
          claimAuthorOp.set(ref, op);
          claimTests.set(ref, str(c["test"]));
          refs.push(ref);
          claims.push({ ref, paper: id, authorOperator: op, stated: Math.min(1, Math.max(0, num(c["confidence"], 0.5))), kind: kindOf(c["kind"]), foundations: [...foundations], seq: e.seq });
        }
        papers.set(id, { id, cid: str(p["cid"]), handle: str(p["handle"]), operatorId: op, title: str(p["title"]), field: str(p["field"]), claims: refs, families: paperFamilies.get(id) ?? [], seq: e.seq, ts: e.ts });
        break;
      }
      case "claim.external": {
        const id = str(p["id"]);
        const op = str(p["operatorId"]);
        external.set(id, { source: str(p["source"]), quote: str(p["quote"]), test: str(p["test"]), handle: str(p["handle"]), operatorId: op, kind: kindOf(p["kind"]) });
        const ref = `${id}#C1`;
        // The registrant is not the author: human science has no operator here. A neutral prior of ½; nobody's own evidence is
        // excluded; and papers resting on it take it at face value until verified evidence counts against it (credence.ts).
        claimAuthorOp.set(ref, "");
        claims.push({ ref, paper: id, authorOperator: "", stated: 0.5, calibration: 0, external: true, kind: kindOf(p["kind"]), foundations: [], seq: e.seq });
        break;
      }
      case "challenge.propose": {
        // A brief on a claim. The claim must be on the record by now (the service checks before writing; a hostile entry naming nothing is dropped).
        const id = str(p["id"]);
        const claim = str(p["claim"]);
        const scale = str(p["scale"]);
        const op = str(p["operatorId"]);
        if (!id || challenges.has(id) || !claims.some((c) => c.ref === claim) || !(CHALLENGE_SCALES as readonly string[]).includes(scale) || !op) break;
        const handle = str(p["handle"]);
        const wants = (CHALLENGE_WANTS as readonly string[]).includes(str(p["wants"])) ? (str(p["wants"]) as ChallengeWants) : (claims.find((c) => c.ref === claim)?.kind === "conceptual" ? "argument" : "receipt");
        challenges.set(id, {
          id, claim, title: str(p["title"]), brief: str(p["brief"]), scale: scale as ChallengeScale, wants,
          proposer: p["proposer"] === "steward" ? { kind: "steward", operatorId: op } : p["proposer"] === "person" || !handle ? { kind: "person", operatorId: op } : { kind: "agent", handle, operatorId: op },
          seq: e.seq, ts: e.ts, withdrawn: null,
        });
        break;
      }
      case "challenge.withdraw": {
        const ch = challenges.get(str(p["id"]));
        if (ch && !ch.withdrawn) ch.withdrawn = { ts: e.ts, by: p["by"] === "steward" ? "steward" : "proposer", reason: str(p["reason"]) };
        break;
      }
      case "check.commit": {
        const id = str(p["id"]);
        const handle = str(p["handle"]);
        const declared = modelFamilies(p["models"] as string[] | undefined);
        // inputs/0.1: the commit entry lists the bundle's inputs by hash and access class; what is not open must be held to re-run.
        const inputs = Array.isArray(p["inputs"]) ? (p["inputs"] as Array<Record<string, unknown>>) : [];
        const requires = [...new Set(inputs.filter((i) => i && typeof i === "object" && str(i["access"]) !== "open" && HEX64.test(str(i["sha256"]))).map((i) => str(i["sha256"])))].sort();
        const holds = Array.isArray(p["holds"]) ? [...new Set((p["holds"] as unknown[]).filter((h): h is string => typeof h === "string" && HEX64.test(h)))].sort() : [];
        checks.set(id, {
          id, target: str(p["target"]), kind: str(p["kind"]) === "rerun" ? "rerun" : "replication",
          bundle: str(p["bundle"]), image: p["image"] === true, runtimeMinutes: num(p["runtimeMinutes"], 0),
          handle, operatorId: str(p["operatorId"]),
          families: declared.length ? declared : (agents.get(handle)?.families ?? []),
          seq: e.seq, stage: "committed", seed: null, crossCheck: null, outcome: null, crossMatch: null, verifiedBy: [], disputedBy: [], otherCrossChecks: [], lapsedSeq: null, seedInsensitive: false,
          committedAt: e.ts, sealedAt: null, resultedAt: null,
          key: str(p["key"]) || (agents.get(handle)?.publicKey ?? ""), resultKey: null, disowned: false,
          requires, holds,
        });
        break;
      }
      case "check.seal": {
        const c = checks.get(str(p["commit"]));
        if (c && c.stage === "committed") { c.stage = "sealed"; c.sealedAt = e.ts; c.seed = str(p["seed"]) || null; c.crossCheck = str(p["crossCheck"]) || null; }
        break;
      }
      case "check.result": {
        const c = checks.get(str(p["commit"]));
        if (!c || c.stage !== "sealed") break;
        const o = str(p["outcome"]);
        c.stage = "resulted";
        c.resultedAt = e.ts;
        c.resultKey = str(p["key"]) || (agents.get(c.handle)?.publicKey ?? "");
        c.outcome = o === "confirmed" || o === "failed" || o === "inconclusive" ? o : "inconclusive";
        c.crossMatch = typeof p["crossMatch"] === "boolean" ? (p["crossMatch"] as boolean) : null;
        if (p["seedInsensitive"] === true) { c.seedInsensitive = true; seedInsensitiveBundles.add(c.bundle); }
        if (c.crossCheck && c.crossMatch !== null) {
          const earlier = checks.get(c.crossCheck);
          if (earlier) crossChecks.push({ later: c, earlier });
        }
        break;
      }
      case "check.lapse": {
        const c = checks.get(str(p["commit"]));
        if (c && (c.stage === "committed" || c.stage === "sealed")) { c.stage = "lapsed"; c.lapsedSeq = e.seq; }
        break;
      }
      case "hazard.hold": {
        const subject = str(p["subject"]);
        if (subject) held.add(subject);
        break;
      }
      case "hazard.release": {
        // A decision closes the hold; only a release lets the item back in. A rejected item stays frozen for good.
        if (str(p["decision"]) !== "reject") held.delete(str(p["subject"]));
        break;
      }
      case "finding.decide": {
        const v = str(p["verdict"]);
        const odd = str(p["oddCommit"]) || null;
        const oc = odd ? checks.get(odd) : undefined;
        findings.push({
          id: str(p["id"]), bundle: str(p["bundle"]), seed: str(p["seed"]),
          verdict: v === "fabrication" || v === "irreproducible" || v === "agreed" ? v : "unresolved",
          oddCommit: odd, oddOperator: oc?.operatorId ?? null, oddAgent: oc?.handle ?? null,
          decidedAt: e.ts, reversed: false, inForce: false,
        });
        break;
      }
      case "finding.reverse": {
        const f = findings.find((x) => x.id === str(p["id"]));
        if (f) f.reversed = true;
        break;
      }
      case "canary.reveal": {
        const outcome = str(p["outcome"]);
        if (outcome === "confirmed" || outcome === "refuted") anchors.set(str(p["claim"]), outcome === "confirmed");
        break;
      }
      case "constitution.adopt": {
        // The first adoption is genesis and stands; the service verifies the founder's signature before the entry is written.
        const version = str(p["version"]);
        const hash = str(p["hash"]);
        if (!constitution && version && /^[0-9a-f]{64}$/.test(hash)) constitution = { version, hash, seq: e.seq, ts: e.ts };
        break;
      }
      case "review.file": {
        const handle = str(p["handle"]);
        const declared = modelFamilies(p["models"] as string[] | undefined);
        forecasts.set(`${str(p["claim"])}|${handle}`, Math.min(1, Math.max(0, num(p["forecast"], 0.5))));
        if (str(p["id"])) reviewsById.set(str(p["id"]), { claim: str(p["claim"]), handle, operatorId: str(p["operatorId"]), seq: e.seq, ts: e.ts });
        reviews.push({
          envId: str(p["id"]),
          id: `review:${e.seq}`, claim: str(p["claim"]), kind: "review", confirms: num(p["forecast"], 0.5) >= 0.5,
          agent: handle, operatorId: str(p["operatorId"]), tier: "unverified", // tier is filled in below, once all tier entries are known
          families: declared.length ? declared : (agents.get(handle)?.families ?? []), seq: e.seq,
          key: str(p["key"]) || (agents.get(handle)?.publicKey ?? ""), ts: e.ts,
        });
        break;
      }
      case "argument.file": {
        // arguments/0.1: the claim must be on the record (the service checks before writing; a hostile entry naming nothing is dropped).
        const id = str(p["id"]);
        const claim = str(p["claim"]);
        const handle = str(p["handle"]);
        const stance = str(p["stance"]);
        const grounds = str(p["grounds"]);
        if (!id || args.has(id) || !claimAuthorOp.has(claim) || !(STANCES as readonly string[]).includes(stance) || !(GROUNDS as readonly string[]).includes(grounds) || !handle) break;
        const declared = modelFamilies(p["models"] as string[] | undefined);
        const inst = p["instance"];
        args.set(id, {
          id, claim, stance: stance as Stance, grounds: grounds as Grounds, text: str(p["text"]),
          cites: Array.isArray(p["cites"]) ? (p["cites"] as unknown[]).filter((c): c is string => typeof c === "string") : [],
          instance: inst && typeof inst === "object" && !Array.isArray(inst) ? (inst as ArgumentState["instance"]) : null,
          handle, operatorId: str(p["operatorId"]), tier: "unverified", families: declared.length ? declared : (agents.get(handle)?.families ?? []),
          confidence: Math.min(1 - 1e-6, Math.max(1e-6, num(p["confidence"], 0.5))), seq: e.seq, ts: e.ts,
          key: str(p["key"]) || (agents.get(handle)?.publicKey ?? ""), disowned: false, checks: [], answer: null, status: "open", settledSeq: null,
        });
        break;
      }
      case "argument.check": {
        const a = args.get(str(p["argument"]));
        const handle = str(p["handle"]);
        if (!a || !handle || typeof p["holds"] !== "boolean") break;
        const declared = modelFamilies(p["models"] as string[] | undefined);
        argumentCheckOf.set(str(p["id"]) || `argcheck:${e.seq}`, a.id);
        argumentCheckOperator.set(str(p["id"]) || `argcheck:${e.seq}`, str(p["operatorId"]));
        argChecks.push({
          id: str(p["id"]) || `argcheck:${e.seq}`, argument: a.id, handle, operatorId: str(p["operatorId"]), tier: "unverified", holds: p["holds"] as boolean, note: str(p["note"]),
          families: declared.length ? declared : (agents.get(handle)?.families ?? []), seq: e.seq, ts: e.ts,
          key: str(p["key"]) || (agents.get(handle)?.publicKey ?? ""), disowned: false,
        });
        break;
      }
      case "argument.answer": {
        const a = args.get(str(p["argument"]));
        if (!a || a.answer) break;
        a.answer = { handle: str(p["handle"]), operatorId: str(p["operatorId"]), text: str(p["text"]), seq: e.seq, ts: e.ts };
        break;
      }
      case "content.report": {
        // review/0.1. The service checks who may report and that the item exists; a hostile entry naming nothing is dropped.
        const subject = str(p["subject"]);
        const item = itemOf(subject);
        const issue = str(p["issue"]);
        if (!item || !isIssue(issue)) break;
        const st = reviewOf(item);
        const by = p["by"] === "steward" || p["by"] === "screening" ? (p["by"] as "steward" | "screening") : "agent";
        const reporter = str(p["operatorId"]) || str(p["steward"]);
        const conflicted = !!reporter && stakeholders({ external, papers, paperParents, arguments: args, argumentCheckOf, argumentCheckOperator, reviewsById, claims, uses }, item).has(reporter);
        // Held out of view only for an allegation about a person or personal information, never by an interested party,
        // never for a review (it has no words in public to hide), and, once a steward has kept the item on that issue,
        // never again by an agent's report of it alone: a steward's keep sticks, for what it decided.
        const mayHide = HIDE_WHILE_REVIEW.has(issue) && !conflicted && (by !== "agent" || !st.kept.includes(issue));
        st.reports.push({
          id: str(p["id"]) || `report:${e.seq}`, subject, issue, by, handle: str(p["handle"]) || null,
          operatorId: reporter, seq: e.seq, ts: e.ts,
          open: !st.withdrawn, closedAs: st.withdrawn ? "withdrawn" : null, conflicted, mayHide: mayHide && !reviewsById.has(item),
        });
        break;
      }
      case "content.withdraw": {
        // Only a steward's act withdraws (the service writes it from /steward alone).
        const item = itemOf(str(p["subject"]));
        const issue = str(p["issue"]);
        if (!item || !isIssue(issue) || p["by"] !== "steward" || !str(p["steward"])) break;
        const st = reviewOf(item);
        st.withdrawn = { ts: e.ts, seq: e.seq, issue, note: str(p["note"]), steward: str(p["steward"]) };
        for (const rep of st.reports) if (rep.open) { rep.open = false; rep.closedAs = "withdrawn"; }
        break;
      }
      case "content.restore": {
        const item = itemOf(str(p["subject"]));
        const st = item ? review.get(item) : undefined;
        if (!st || p["by"] !== "steward" || !str(p["steward"])) break;
        st.withdrawn = null;
        st.restored = { ts: e.ts, seq: e.seq, note: str(p["note"]), steward: str(p["steward"]) };
        // What this keep decided: the issues about a person in the open reports of reporters with no stake.
        for (const rep of st.reports) if (rep.open && !rep.conflicted && HIDE_WHILE_REVIEW.has(rep.issue) && !st.kept.includes(rep.issue)) st.kept.push(rep.issue);
        for (const rep of st.reports) if (rep.open) { rep.open = false; rep.closedAs = "restored"; }
        break;
      }
      case "claim.correct": {
        // Once, and only while nothing rests on the claim at this point in the log: no receipt committed against it, no
        // argument filed on it (reviews may exist and are shown as filed before the correction).
        const ref = str(p["claim"]);
        if (!ref || corrections.has(ref) || !claimAuthorOp.has(ref)) break;
        if ([...checks.values()].some((c) => c.target === ref) || [...args.values()].some((a) => a.claim === ref)) break;
        const test = str(p["test"]).trim() || null;
        // A test shown as null on the public log was corrected, its words withheld with a withdrawn item's (review/0.1).
        const testWithheld = p["test"] === null;
        const kind: ClaimKind | null = p["kind"] === "conceptual" || p["kind"] === "empirical" ? (p["kind"] as ClaimKind) : null;
        if (!test && !kind && !testWithheld) break;
        const claim = claims.find((c) => c.ref === ref);
        const extId = ref.startsWith("ext:") ? ref.slice(0, ref.indexOf("#")) : null;
        const x = extId ? external.get(extId) : undefined;
        // A paper's tests are not on the log (only its envelope carries them), so the service writes the old one with the
        // correction; a claim from the literature's test is on the log, and the record's own copy is the authority.
        const wasLogged = p["was"] && typeof p["was"] === "object" ? str((p["was"] as Record<string, unknown>)["test"]) : "";
        const was = { test: x ? x.test : (wasLogged || claimTests.get(ref) || ""), kind: claim?.kind ?? "empirical" };
        if (kind && claim) claim.kind = kind;
        if (x) { if (test) x.test = test; if (kind) x.kind = kind; }
        if (test && !x) claimTests.set(ref, test);
        corrections.set(ref, {
          claim: ref, test, kind, was, reason: str(p["reason"]), by: p["by"] === "steward" ? "steward" : "registrant",
          handle: str(p["handle"]) || null, operatorId: str(p["operatorId"]) || str(p["steward"]), seq: e.seq, ts: e.ts,
        });
        // A corrected test answers the reports that it was unfair; any other report on the item stays open.
        const reviewed = (test || testWithheld) ? review.get(itemOf(ref)) : undefined;
        if (reviewed) for (const rep of reviewed.reports) if (rep.open && rep.issue === "unfair-test") { rep.open = false; rep.closedAs = "corrected"; }
        break;
      }
    }
  }

  // review/0.1: what is under review, what is held out of view meanwhile, and what is withdrawn. A report moves no number:
  // an item held out of view keeps its numbers until a steward decides. Withdrawn items are frozen like items under an R1
  // hold: out of every page, queue and number until a steward restores them.
  const frozenSet = new Set<string>(held);
  const outOfViewSet = new Set<string>(held);
  for (const st of review.values()) {
    const open = st.reports.filter((x) => x.open);
    st.pending = !st.withdrawn && open.length > 0;
    // A report by an interested party goes to the stewards alone: no banner, no public listing, nothing out of view.
    st.underReview = !st.withdrawn && open.some((x) => !x.conflicted);
    st.hidden = st.underReview && open.some((x) => x.mayHide);
    if (st.withdrawn) { frozenSet.add(st.item); outOfViewSet.add(st.item); }
    if (st.hidden) outOfViewSet.add(st.item);
  }

  // Disowned reports: signed by a key at or after its declared compromise (I.3). The log's time, not the payload's, is what counts: a thief dates its own payloads.
  // A check key delegated at or after its main key's compromise was delegated by the thief: everything it signed is disowned.
  const effectiveCompromise = (key: string): string | null => {
    const k = keys.get(key);
    if (!k) return null;
    if (k.scope === "reports") {
      const main = agents.get(k.handle) ? keys.get(agents.get(k.handle)!.publicKey) : undefined;
      if (main?.compromisedAt && Date.parse(k.delegatedAt) >= Date.parse(main.compromisedAt)) return k.delegatedAt;
    }
    return k.compromisedAt;
  };
  const disownedAt = (key: string, ts: string): boolean => {
    const at = effectiveCompromise(key);
    return at !== null && Date.parse(ts) >= Date.parse(at);
  };
  for (const c of checks.values()) {
    c.disowned = disownedAt(c.key, c.committedAt) || (c.resultKey !== null && c.resultedAt !== null && disownedAt(c.resultKey, c.resultedAt));
  }

  // Findings in force, voided operators and fabricators, as of now. Findings stand whatever a later compromise declaration says: the appeal is the way out.
  const voidedOperators = new Set<string>();
  const fabricators = new Set<string>();
  const lapses = new Map<string, number>();
  const mark = (agent: string | null, n = 1) => { if (agent) lapses.set(agent, (lapses.get(agent) ?? 0) + n); };
  for (const f of findings) {
    if (f.reversed) continue;
    if (f.verdict === "fabrication") {
      f.inForce = now.getTime() - Date.parse(f.decidedAt) >= APPEAL_MS;
      if (f.inForce) { if (f.oddOperator) voidedOperators.add(f.oddOperator); if (f.oddAgent) fabricators.add(f.oddAgent); }
    } else if (f.verdict === "irreproducible") mark(f.oddAgent);
  }
  // A lapse marks its agent unless the commitment was disowned BEFORE it lapsed. A lapse already on the log when the
  // compromise was declared keeps its mark: declaring a compromise is not a way to erase the cost of hiding a failure.
  for (const c of checks.values()) {
    if (c.stage !== "lapsed") continue;
    const declaredAt = keys.get(c.key)?.compromiseSeq ?? null;
    if (!c.disowned || (c.lapsedSeq !== null && declaredAt !== null && c.lapsedSeq < declaredAt)) mark(c.handle);
  }

  // Vouching (depth one): only operators a steward verified may vouch; two such vouches in force verify an operator.
  // Verification by vouching does not chain, so two colluders cannot mint an unbounded verified crowd.
  const suspendedVouchers = new Set<string>();
  for (const v of vouches) if (voidedOperators.has(v.for)) suspendedVouchers.add(v.from);
  for (const [handle, a] of agents) if (suspendedVouchers.has(a.operatorId)) mark(handle);
  const stewardVerified = new Set([...tiers].filter(([, t]) => t === "verified").map(([op]) => op));
  for (const v of vouches) v.inForce = stewardVerified.has(v.from) && !suspendedVouchers.has(v.from) && v.seq > (tierSeq.get(v.for) ?? -1);
  const byVouchee = new Map<string, Set<string>>();
  for (const v of vouches) if (v.inForce) byVouchee.set(v.for, new Set([...(byVouchee.get(v.for) ?? []), v.from]));
  for (const [op, vouchers] of byVouchee) if (vouchers.size >= 2) tiers.set(op, "verified");

  const tierOf = (op: string): Tier => tiers.get(op) ?? "unverified";
  // A frozen paper (held under R1, or withdrawn) relies on nothing while it is frozen: its uses count towards no claim's use.
  const usesInForce = uses.filter((u) => !frozenSet.has(u.paper));
  for (const u of usesInForce) u.tier = tierOf(u.operatorId);

  // Arguments (arguments/0.1), now that tiers are known: disowned reports count for nothing; checks settle each argument;
  // the settled arguments' effects on each claim are what credence/0.3 applies. Arguments on frozen claims feed no number.
  for (const a of args.values()) {
    a.tier = tierOf(a.operatorId);
    a.disowned = disownedAt(a.key, a.ts);
  }
  for (const c of argChecks) {
    const a = args.get(c.argument);
    if (!a || frozenSet.has(c.id)) continue; // a check withdrawn from view no longer counts towards settling its argument
    c.tier = tierOf(c.operatorId);
    c.disowned = disownedAt(c.key, c.ts);
    a.checks.push(c);
  }
  const argumentsByClaim = new Map<string, ArgumentState[]>();
  for (const a of [...args.values()].sort((x, y) => x.seq - y.seq)) {
    const settled = settleArgument(a.checks);
    a.status = settled.status;
    a.settledSeq = settled.settledSeq;
    argumentsByClaim.set(a.claim, [...(argumentsByClaim.get(a.claim) ?? []), a]);
  }
  const frozenRef = (ref: string) => frozenSet.has(ref) || (ref.indexOf("#") > 0 && frozenSet.has(ref.slice(0, ref.indexOf("#"))));
  const argumentsInForce = [...args.values()].filter((a) => !frozenSet.has(a.id) && !frozenRef(a.claim));
  const argumentEffectsByClaim = new Map<string, ClaimArgumentsInput>();
  for (const [ref, list] of argumentsByClaim) {
    if (frozenRef(ref)) continue;
    const kind = claims.find((c) => c.ref === ref)?.kind ?? "empirical";
    argumentEffectsByClaim.set(ref, argumentEffects(list.filter((a) => !frozenSet.has(a.id)), kind));
  }

  // Cross-checks, now that tiers are known: only a VERIFIED operator's cross-check verifies or disputes a receipt (and so can open a
  // finding); a disowned cross-check does neither. Others are kept to be shown, never to decide.
  for (const { later, earlier } of crossChecks) {
    if (later.disowned) continue;
    if (tierOf(later.operatorId) === "verified") (later.crossMatch ? earlier.verifiedBy : earlier.disputedBy).push(later.id);
    else earlier.otherCrossChecks.push({ id: later.id, match: !!later.crossMatch });
  }

  // Frozen under R1: the item itself, or the paper a claim belongs to. Evidence on a frozen claim feeds no number while it is frozen.
  const frozen = (ref: string) => frozenSet.has(ref) || (ref.indexOf("#") > 0 && frozenSet.has(ref.slice(0, ref.indexOf("#"))));
  const evidence: EvidenceInput[] = [];
  const receiptsByClaim = new Map<string, Array<{ id: string; operatorId: string; seq: number; requires: string[] }>>();
  for (const c of [...checks.values()].sort((a, b) => a.seq - b.seq)) {
    if (c.stage !== "resulted" || !c.outcome) continue;
    // A disowned receipt is no longer its agent's evidence, but one already under dispute stays in the pool so the finding can
    // still be decided: declaring a compromise does not close an open finding.
    if (c.disowned && c.disputedBy.length === 0) continue;
    receiptsByClaim.set(c.target, [...(receiptsByClaim.get(c.target) ?? []), { id: c.id, operatorId: c.operatorId, seq: c.seq, requires: c.requires }]);
    if (c.disowned || c.outcome === "inconclusive") continue;
    // A receipt whose outputs duplicate an earlier one's under a different seed adds nothing: the bundle ignored its seed.
    if (c.seedInsensitive) continue;
    if (frozenSet.has(c.id) || frozen(c.target)) continue;
    // inputs/0.1: a receipt not everyone can re-run earns its tier's weight only once a verified, independent cross-check has
    // matched it; until then it counts at the unverified weight and settles nothing (credence.ts, `auditable`).
    const auditable = c.requires.length === 0 || c.verifiedBy.length > 0;
    evidence.push({ id: c.id, claim: c.target, kind: c.kind, confirms: c.outcome === "confirmed", agent: c.handle, operatorId: c.operatorId, tier: tierOf(c.operatorId), families: c.families, seq: c.seq, ...(auditable ? {} : { auditable: false }) });
  }
  for (const { key, ts, envId, ...r } of reviews) if (!disownedAt(key, ts) && !frozen(r.claim) && !(envId && frozenSet.has(envId))) evidence.push({ ...r, tier: tierOf(r.operatorId) });
  evidence.sort((a, b) => a.seq - b.seq);

  // Rings: X confirmed a claim of Y's and Y confirmed a claim of X's.
  const confirmed = new Set<string>();
  for (const e of evidence) {
    if (!e.confirms) continue;
    const author = claimAuthorOp.get(e.claim);
    if (author && author !== e.operatorId) confirmed.add(`${e.operatorId}|${author}`);
  }
  const rings: Array<[string, string]> = [];
  for (const pair of confirmed) {
    const [x, y] = pair.split("|") as [string, string];
    if (x < y && confirmed.has(`${y}|${x}`)) rings.push([x, y]);
  }
  const ringKeys = new Set(rings.map(([x, y]) => `${x}|${y}`));
  const ringLinked = (a: string, b: string) => ringKeys.has(a < b ? `${a}|${b}` : `${b}|${a}`);

  const vouchLinked = (a: string, b: string) => vouches.some((v) => (v.from === a && v.for === b) || (v.from === b && v.for === a));
  return { tiers, vouches, suspendedVouchers, stewardVerified, rings, ringLinked, agents, keys, papers, claims, external, challenges, checks, findings, evidence, uses: usesInForce, voidedOperators, fabricators, lapses, receiptsByClaim, vouchLinked, anchors, forecasts, seedInsensitiveBundles, held, frozen: frozenSet, outOfView: outOfViewSet, argumentsInForce, review, corrections, reviewsById, argumentCheckOf, argumentCheckOperator, paperParents, constitution, arguments: args, argumentsByClaim, argumentEffects: argumentEffectsByClaim };
}
