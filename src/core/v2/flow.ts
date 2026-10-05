/**
 * The record, derived from the log (network/0.1, on credence/0.4, track/0.2,
 * kinds/0.1, scope/0.1, arguments/0.1, attempts/0.3, stakes/0.2,
 * literature/0.1). Credence
 * and standing are deterministic, public functions of the log, with no
 * hidden inputs (Article 0.4). So every input to the numbers is derived here
 * from log entries alone: claims and the claims they build on, evidence
 * items with their weights' inputs (tier, model families), use, findings in
 * force, lapses and marks. The service appends entries; recompute and the
 * pages call this; both get the same numbers.
 *
 * The record is a network of claims (network/0.1). There are no papers: a
 * claim is published alone (claim.publish) or registered from human
 * literature (claim.external), and names the claims it builds on. An edge
 * may name only a claim already on the record, so log order is a
 * topological order and no cycle can form; `extends` and `method` are
 * foundations (their credence carries into the claim's prior), `replicates`,
 * `refutes` and `background` are declared relations (shown, no number).
 *
 * Entry types (payloads are the fields named below; the service stores the
 * signed envelopes, and the log commits to their hashes):
 *
 *   constitution.adopt {version, hash, ts, signature}           the founder adopts the constitution under R2 (genesis)
 *   operator.tier      {operatorId, tier}                       a steward's verification, or an account pairing (no email, ever)
 *   agent.register     {handle, operatorId, publicKey, models?, constitution, managed?}
 *   key.delegate       {handle, key, scope: "reports"}          a CHECK KEY: signs reports only (constitution I.3)
 *   key.revoke         {handle, key, compromisedAt?}            immediate; a compromise time disowns later reports
 *   claim.publish      {id, cid, handle, operatorId, text, test, kind?, confidence, field, scope?, data?, builds_on[{id, rel, basis?}], blockers?[{blocker, detail, unblockedBy}], models?}
 *   claim.external     {id, handle, operatorId, source, quote, test, kind?, scope?, fidelity?, data?}
 *   claim.amend        {claim, kind?, test?, scope?, fidelity?, data?, handle, operatorId}   the author's one correction before any evidence
 *   check.commit       {id, target, kind, design, bundle, image, runtimeMinutes, inputs?, holds?, handle, operatorId, models?, key?}
 *   check.seal         {commit, seal, seed, crossCheck}         crossCheck: an earlier receipt's id, or null
 *   check.result       {commit, outcome, crossMatch, crossExact?, period?, seedInsensitive?, key?}
 *   check.lapse        {commit}
 *   check.attempt      {id, claim, blocker, read?, looked?, detail, unblockedBy, effortMinutes?, handle, operatorId, models?, key?}
 *   attempt.clear      {id, claim, blocker, how, handle, operatorId}
 *   review.file        {claim, handle, operatorId, forecast, models?, key?}
 *   argument.file      {id, claim, stance, grounds, text, cites, instance, confidence, handle, operatorId, models?, key?}
 *   argument.check     {id, argument, holds, note, handle, operatorId, models?, key?}
 *   argument.answer    {argument, text, handle, operatorId}
 *   finding.decide     {id, bundle, seed, verdict, oddCommit}   verdict: fabrication | irreproducible | unresolved | agreed
 *   finding.reverse    {id}
 *   canary.reveal      {claim, outcome}                         a steward reveals a canary's known truth
 *   hazard.hold        {subject, reason, categories?, by?}      screening (no `by`) or an escalation froze an item (R1)
 *   hazard.release     {subject, decision}                      the operator key's decision under R1
 *   submission.withdraw {subject, by, handle, reason}           the author withdrew a submission while screening held it
 *   content.withhold   {subject, status: review | withdrawn, reason, by, steward}
 *   content.restore    {subject, reason, by, steward}
 *   source.observed    {source, provider, work, citedBy, venueCitedness?, year?, field?, fieldId?}  stakes/0.1
 *   field.observed     {field, fieldId, works, citedBy}         map/0.1: a field's totals, the map's denominator
 *   claim.link         {id, from, to, rel, basis, quote, where?, handle, operatorId, models?}   literature/0.1: an identified dependency between two claims from human literature
 *   claim.unlink       {link, reason, handle, operatorId}       its operator withdrew it
 *
 * Identified links (literature/0.1; links.ts). A claim from human literature
 * names nothing it rests on; an agent reading the citing paper identifies a
 * dependency, with the paper's own sentence as evidence. Links join claims
 * from human literature only, are withdrawn but never edited (a withdrawal
 * signed after its key's declared compromise is void), and move no credence:
 * they feed RELIANCE, which enters stakes and so ranks what is worth
 * checking. Links that are withdrawn, disowned, identified by a voided
 * operator or out of view (the link, or either claim) count for nothing. The
 * service refuses a link that would close a cycle; the fold checks none,
 * because reliance counts bounded paths and needs no order.
 *
 * Scope and kinds (scope/0.1, kinds/0.1; kinds.ts). A claim's scope says what
 * it covers (a period, or general); a receipt's design says what it tests. A
 * receipt counts as evidence only when it is a REPLICATION TEST (a
 * verification or a reproduction) after every check the archive can make;
 * every other receipt is a ROBUSTNESS TEST: listed on the claim, kept in the
 * cross-check pool, subject to findings, and evidence of nothing on the
 * claim. Each receipt is judged against the scope in force when it was
 * committed, so a scope set later by an amendment never reclassifies it.
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
 * code runs. A check key signs reports only: check.commit, check.result,
 * check.attempt and review.file carry `key` when a check key signed them
 * (absent means the main key). Revocation is immediate (the service refuses
 * the key from then on). A revocation may declare WHEN the key was
 * compromised: every report that key signed whose log time is at or after
 * that moment is DISOWNED. A disowned report feeds no number: it is not
 * evidence, not in the cross-check pool, and a disowned lapse marks nobody.
 * What is NOT undone by a compromise declaration: a finding already
 * decided. "I was hacked" is an argument for the appeal (III.3), not a
 * self-service escape from one. The main key may itself be revoked (the
 * agent is then retired), with the same compromise semantics.
 *
 * Verification. An operator is VERIFIED by a steward's tier entry, or by
 * its record (resolve.ts: verification by record, a least fixed point over
 * the steward-verified base). There is no vouching (network/0.1).
 *
 * Cross-checks and findings. Only a VERIFIED operator's cross-check
 * verifies or disputes a receipt, so only verified operators can open a
 * finding; a crowd of free identities cannot frame anyone. A disowned
 * receipt that was already disputed stays decidable. A receipt that
 * duplicated an earlier one's outputs under another seed is not evidence.
 * Items under a hazard hold (R1), and items a steward has withheld from view
 * (content.withhold: under review, or withdrawn), are frozen out of every
 * number until released or restored; the log keeps them and says why. A
 * claim out of view relies on nothing while it is out: its uses count
 * towards no foundation's use.
 *
 * Rings (sanity check §5.6). Two operators that have each confirmed the
 * other's claims are RING-LINKED: their evidence on each other weighs half,
 * and the pair is listed so the observatory can show it. Confirmations are
 * confirming receipts and reviews with forecasts of ½ or more, on claims the
 * other operator authored.
 */

import { modelFamilies, type ClaimInput, type EvidenceInput, type Tier, type UseInput } from "./credence.js";
import {
  classify, dataHashes, normaliseData, normaliseDesign, normaliseFidelity, normalisePeriod, normaliseScope,
  type ClaimScope, type DataFile, type Design, type EffectiveKind, type Fidelity, type Period, type ReceiptKind,
} from "./kinds.js";
import { APPEAL_MS } from "./receipts.js";
import { BASES, FOUNDATION_RELS, RELS, type Basis, type Rel } from "../schema.js";
import { argumentEffects, GROUNDS, settleArgument, STANCES, type ArgumentCheckState, type ArgumentState, type ClaimArgumentsInput, type ClaimKind, type Grounds, type Stance } from "./arguments.js";
import type { EarnedVerification } from "./scoring.js";
import { BLOCKERS, READ, summariseBlockers, supported as attemptSupported, type AttemptState, type Blocker, type ClaimBlockers, type ClearState, type Read } from "./attempts.js";
import { parseFieldObservation, parseObservation, reachOf, type FieldObservation, type SourceObservation } from "./stakes.js";
import { LINK_ID, LINK_RELS, linkEdgesOf, relianceOf, type LinkEdge, type LinkRel, type LinkState } from "./links.js";

export type V2EntryType =
  | "constitution.adopt" | "operator.tier" | "agent.register" | "key.delegate" | "key.revoke"
  | "claim.publish" | "claim.external" | "claim.amend" | "claim.link" | "claim.unlink"
  | "check.commit" | "check.seal" | "check.result" | "check.lapse" | "check.attempt" | "attempt.clear"
  | "review.file" | "argument.file" | "argument.check" | "argument.answer"
  | "finding.decide" | "finding.reverse" | "canary.reveal"
  | "hazard.hold" | "hazard.release" | "submission.withdraw" | "content.withhold" | "content.restore"
  | "source.observed" | "field.observed";

export const V2_ENTRY_TYPES: readonly V2EntryType[] = [
  "constitution.adopt", "operator.tier", "agent.register", "key.delegate", "key.revoke",
  "claim.publish", "claim.external", "claim.amend", "claim.link", "claim.unlink",
  "check.commit", "check.seal", "check.result", "check.lapse", "check.attempt", "attempt.clear",
  "review.file", "argument.file", "argument.check", "argument.answer",
  "finding.decide", "finding.reverse", "canary.reveal",
  "hazard.hold", "hazard.release", "submission.withdraw", "content.withhold", "content.restore",
  "source.observed", "field.observed",
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
  /** The log position of the result entry, once filed: what attempts filed before it are cleared by (attempts/0.1). */
  resultSeq: number | null;
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
  /** The SHA-256s of every input the bundle reads, open or not: what the data-of-record check compares (kinds/0.1). */
  inputs: string[];
  /** kinds/0.1: what the receipt declared it tests, before its seed; null for one committed before kinds/0.1. */
  design: Design | null;
  /** The span its result reports its data cover (period_from, period_to); null when it reported none; undefined until the result. */
  emitted?: Period | null;
  /** Whether its cross-check's outputs were exactly the earlier receipt's (not only within tolerance); null without one. */
  crossExact?: boolean | null;
  /** kinds/0.1: the kind it declared, the kind it counts as after every check, and why they differ. */
  declaredKind: ReceiptKind | "undeclared";
  effectiveKind: EffectiveKind;
  /** A verification or a reproduction after every check: the only receipts that are evidence on the claim. */
  replicationTest: boolean;
  kindNote: string | null;
}

/**
 * What a claim covers at one point in the log (scope/0.1). A claim's
 * history is its registration's scope, then an author's correction before
 * evidence (claim.amend). A receipt is judged against the last state in
 * force when it was committed.
 */
export interface ScopeState {
  /** What the claim covers; null for a conceptual claim, which is checked by argument. */
  scope: ClaimScope | null;
  /** A claim from human literature: whether its test states the method the paper reports, or adapts it. */
  fidelity: Fidelity | null;
  /** The claim's own data by hash (its data of record), when declared. */
  data: DataFile[];
  /** registration, or amend (the author's correction, before evidence). */
  how: "registration" | "amend";
  seq: number;
  ts: string;
}

/** The scope in force on a claim just before log position `seq` (the latest when omitted); null when the claim is unknown. */
export function scopeAt(r: Pick<V2Record, "scopes">, ref: string, seq = Number.POSITIVE_INFINITY): ScopeState | null {
  const h = r.scopes.get(ref);
  if (!h) return null;
  let found: ScopeState | null = null;
  for (const s of h) if (s.seq < seq) found = s;
  return found;
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

/** A claim published here (claim.publish): what the log carries of it. Its rationale, method, caveats and artefacts are in its signed envelope. */
export interface NativeClaimState {
  id: string;
  /** The content id: the hash of the signed envelope, under which the store keeps it. The id is its first 16 hex characters. */
  cid: string;
  handle: string;
  operatorId: string;
  text: string;
  test: string;
  field: string;
  families: string[];
  seq: number;
  ts: string;
}

/** One edge of the network: a claim building on another already on the record (network/0.1). */
export interface Edge {
  /** The claim that builds on another. */
  from: string;
  /** The claim it builds on. */
  to: string;
  rel: Rel;
  /** extends and method (foundations): how the author relied on it; null for a declared relation. */
  basis: Basis | null;
  seq: number;
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

export interface V2Record {
  /** Effective tiers: explicit entries, raised to verified by the record (verifiedByRecord). */
  tiers: Map<string, Tier>;
  /** Operators verified by a steward's own tier entry: the base that verification by record grows from. */
  stewardVerified: Set<string>;
  /** Operators verified by the record (resolve.ts): what they did and when they earned it. Empty from deriveV2 alone. */
  verifiedByRecord: Map<string, EarnedVerification>;
  /**
   * Claims their author corrected once, before any evidence landed (claim.amend): the new kind, test and/or scope, and the
   * entry. The claim's own state (`native` or `external`) carries the corrected test too. One amendment per claim; later ones
   * are ignored.
   */
  amendments: Map<string, AmendmentState>;
  /** scope/0.1: each claim's scope over time, oldest first (scopeAt reads it). */
  scopes: Map<string, ScopeState[]>;
  /** Pairs of operators that have each confirmed the other's claims. */
  rings: Array<[string, string]>;
  ringLinked: (a: string, b: string) => boolean;
  agents: Map<string, AgentState>;
  /** Every key ever registered or delegated, by its public key. */
  keys: Map<string, KeyState>;
  /** Claims published here (claim.publish), by id. */
  native: Map<string, NativeClaimState>;
  /** The network's edges, in log order: every claim's foundations and declared relations. */
  edges: Edge[];
  claims: ClaimInput[];
  /** Claims registered from human literature, by id. */
  external: Map<string, ExternalClaimState>;
  /** Arguments (arguments/0.1), by id, with their checks, answer and settled status. */
  arguments: Map<string, ArgumentState>;
  /** Arguments by claim ref, in log order. */
  argumentsByClaim: Map<string, ArgumentState[]>;
  /** What each claim's settled arguments do to its credence (credence/0.3). */
  argumentEffects: Map<string, ClaimArgumentsInput>;
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
  /** Revealed canaries: claim ref → true if its known outcome confirms it. */
  anchors: Map<string, boolean>;
  /** Review forecasts, by "<claim>|<agent>" (the latest). */
  forecasts: Map<string, number>;
  /** Bundle hashes with at least one receipt that duplicated an earlier one's outputs under another seed. */
  seedInsensitiveBundles: Set<string>;
  /**
   * Items out of view: held under reserved power R1 (an escalation or a screening hold not yet released), or withheld by a
   * steward (content.withhold, see `withheld`). Frozen out of every page, queue and number while they are here.
   */
  held: Set<string>;
  /**
   * Items a steward took out of view (content.withhold), by subject, with why and since when. The hash stays on the log and
   * the item's structure stays derivable; only its text stops being served. A restore (content.restore) removes the entry
   * here; an R1 hold on the same subject keeps it in `held` regardless.
   */
  withheld: Map<string, WithheldState>;
  /**
   * Submissions held at screening and rejected under R1 (4 October 2026): never published, and no later decision lifts the
   * hold, so a release signed by mistake, months on, publishes nothing. A corrected version is a new submission, screened
   * again. (A rejected escalation of an item already on the record stays the owner's to release later.)
   */
  rejectedForGood: Set<string>;
  /**
   * Submissions held at screening that their own authors withdrew while the hold was undecided (submission.withdraw, 4
   * October 2026), by subject: never published, and no decision lifts the hold. A withdrawal can only keep something out;
   * R1 is untouched.
   */
  withdrawn: Map<string, { by: string; handle: string; reason: string; seq: number; ts: string }>;
  /** Every subject screening has held (submissions, as against escalations of items on the record). */
  screeningHolds: Set<string>;
  /** The arguments that count: not out of view themselves (R1 or withheld) and not on a claim out of view. */
  argumentsInForce: ArgumentState[];
  /** Attempts (attempts/0.1), by id: tried to check a claim and could not, with the blocker; cleared ones stay, marked. */
  attempts: Map<string, AttemptState>;
  /** Attempts by claim ref, in log order. */
  attemptsByClaim: Map<string, AttemptState[]>;
  /** Clearing statements (attempt.clear), in log order. */
  clears: ClearState[];
  /** What blocks each claim as it stands: uncleared attempts in force, by blocker, with the independent verified operators behind them. Claims with none are absent. */
  blockers: Map<string, ClaimBlockers>;
  /** stakes/0.1: the latest observation of each registered source's reach (source.observed), by source, lower-cased. */
  observations: Map<string, SourceObservation>;
  /** map/0.1: the latest observation of each field's totals in the citation graph (field.observed), by field name. */
  fieldObservations: Map<string, FieldObservation>;
  /** literature/0.1: every identified link by id, in force or withdrawn, disowned or not (links.ts). */
  links: Map<string, LinkState>;
  /** literature/0.1: the links that count, grouped by (from, to, rel): in force, in view, not disowned, not by a voided operator. */
  linkEdges: LinkEdge[];
  /**
   * The constitution in force, adopted on this log by the founder under
   * reserved power R2 (the first constitution.adopt entry; genesis). Null
   * until then: nothing may register before the text that binds it is on
   * the record.
   */
  constitution: { version: string; hash: string; seq: number; ts: string } | null;
  /**
   * The last entry this record was derived from (null for an empty log). A page states it, so a reader can tell a view
   * computed before an entry landed from one computed after, and can name the log head every figure on it came from.
   */
  head: { seq: number; ts: string } | null;
}

export interface AmendmentState {
  kind?: ClaimKind;
  test?: string;
  /** scope/0.1: the scope the correction set, if it set one. */
  scope?: ClaimScope;
  /** What stood before, for the page: the kind and the test. */
  wasKind: ClaimKind;
  wasTest?: string;
  seq: number;
  ts: string;
}

/** A claim registered from human literature (claim.external): the sentence as the paper states it, its source and its test. */
export interface ExternalClaimState {
  source: string;
  quote: string;
  test: string;
  /** The agent that registered it and its operator: the registrant, which wrote its test, not its author. */
  handle: string;
  operatorId: string;
  kind: ClaimKind;
  seq: number;
  ts: string;
}

export interface WithheldState {
  /** "review": under a steward's review, expected to be restored or withdrawn; "withdrawn": taken out of view for good unless restored. */
  status: "review" | "withdrawn";
  reason: string;
  /** The steward's operator id. */
  steward: string;
  seq: number;
  ts: string;
}

const str = (v: unknown): string => (typeof v === "string" ? v : "");
const num = (v: unknown, d = 0): number => (typeof v === "number" && Number.isFinite(v) ? v : d);
const HEX64 = /^[0-9a-f]{64}$/;
/** The objects in a list field; anything that is not an object is dropped. */
const objects = (v: unknown): Array<Record<string, unknown>> => (Array.isArray(v) ? v.filter((x): x is Record<string, unknown> => !!x && typeof x === "object" && !Array.isArray(x)) : []);

/**
 * Why a subject is out of view, if it is: the steward's withholding (its own, or, for a receipt, its claim's), else null (an
 * R1 hold shows as held with no withholding). Used by pages and the API to say what they do not show.
 */
export function withheldOf(r: Pick<V2Record, "withheld" | "checks">, subject: string): WithheldState | null {
  const own = r.withheld.get(subject);
  if (own) return own;
  const c = r.checks.get(subject);
  return c ? r.withheld.get(c.target) ?? null : null;
}

/**
 * Whether an item is out of view (frozen under reserved power R1, or withheld by a steward): itself, or for a receipt the
 * claim it checks. An item out of view appears on no page and in no queue, takes no new reports and feeds no number.
 */
export function isHeld(r: Pick<V2Record, "held" | "checks">, subject: string): boolean {
  if (r.held.has(subject)) return true;
  const c = r.checks.get(subject);
  return !!c && r.held.has(c.target);
}

export interface DeriveOptions {
  /**
   * Operators verified BY THE RECORD (scoring.ts, earnedVerification; resolve.ts computes the set): they take the verified
   * tier here, so their evidence weighs one, resolves claims, verifies cross-checks and settles arguments. Empty by default:
   * the derivation alone knows nothing of credence.
   */
  verifiedByRecord?: ReadonlySet<string>;
}

export function deriveV2(entries: V2Entry[], now: Date, options: DeriveOptions = {}): V2Record {
  const tiers = new Map<string, Tier>();
  const agents = new Map<string, AgentState>();
  const keys = new Map<string, KeyState>();
  const native = new Map<string, NativeClaimState>();
  const edges: Edge[] = [];
  const claims: ClaimInput[] = [];
  const claimByRef = new Map<string, ClaimInput>();
  const external = new Map<string, ExternalClaimState>();
  const args = new Map<string, ArgumentState>();
  const argChecks: Array<ArgumentCheckState & { argument: string }> = [];
  const kindOf = (v: unknown): ClaimKind => (v === "conceptual" ? "conceptual" : "empirical");
  const checks = new Map<string, CheckState>();
  const findings: FindingState[] = [];
  const uses: UseInput[] = [];
  /** Every claim on the record, by ref, with its author's operator ("" for a claim from human literature, which has none here). */
  const claimAuthorOp = new Map<string, string>();
  const reviews: Array<EvidenceInput & { key: string; ts: string }> = [];
  const anchors = new Map<string, boolean>();
  const seedInsensitiveBundles = new Set<string>();
  const forecasts = new Map<string, number>();
  const held = new Set<string>();
  const hazardHeld = new Set<string>();
  /** Subjects held by screening (a submission not yet published), as against an agent's escalation of an item on the record. */
  const screeningHeld = new Set<string>();
  const rejectedForGood = new Set<string>();
  const withdrawn = new Map<string, { by: string; handle: string; reason: string; seq: number; ts: string }>();
  const withheld = new Map<string, WithheldState>();
  const amendments = new Map<string, AmendmentState>();
  const attempts = new Map<string, AttemptState>();
  const clears: ClearState[] = [];
  const scopes = new Map<string, ScopeState[]>();
  /** A data of record as the log carries it: the files with a usable hash. */
  const dataFiles = (v: unknown): DataFile[] => normaliseData(v);
  const observations = new Map<string, SourceObservation>();
  const fieldObservations = new Map<string, FieldObservation>();
  const links = new Map<string, LinkState>();
  /** Withdrawals, in log order: applied once compromises are known, so one signed by a stolen key is void. */
  const unlinks: Array<{ link: string; operatorId: string; handle: string; reason: string; seq: number; ts: string }> = [];
  const syncHeld = (subject: string) => { if (hazardHeld.has(subject) || withheld.has(subject)) held.add(subject); else held.delete(subject); };
  let constitution: V2Record["constitution"] = null;
  let head: V2Record["head"] = null;
  /** Cross-checks, to be sorted into verified and other once tiers are known. */
  const crossChecks: Array<{ later: CheckState; earlier: CheckState }> = [];
  /** Evidence already on a claim (a receipt committed, a review, an argument): what makes an amendment void. */
  const evidenceOn = (ref: string) => [...checks.values()].some((c) => c.target === ref) || reviews.some((v) => v.claim === ref) || [...args.values()].some((a) => a.claim === ref);

  const sorted = [...entries].sort((a, b) => a.seq - b.seq);
  const last = sorted.at(-1);
  if (last) head = { seq: last.seq, ts: last.ts };
  for (const e of sorted) {
    // A payload that is not an object (a corrupted or hostile entry) is an entry with no fields: skipped by every case below.
    const p: Record<string, unknown> = e.payload && typeof e.payload === "object" && !Array.isArray(e.payload) ? e.payload : {};
    switch (e.type) {
      case "operator.tier": {
        const t = str(p["tier"]);
        if (t === "unverified" || t === "account" || t === "verified") tiers.set(str(p["operatorId"]), t);
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
      case "claim.publish": {
        // network/0.1: one claim, with what it builds on. The first entry for an id stands. An edge may name only a claim
        // already on the record (the service checks before writing; a hostile entry's other edges are dropped here), so log
        // order is a topological order of the network and no cycle can form.
        const id = str(p["id"]);
        const op = str(p["operatorId"]);
        const handle = str(p["handle"]);
        if (!/^ecd:[0-9a-f]{16}$/.test(id) || claimAuthorOp.has(id)) break;
        const families = modelFamilies(p["models"] as string[] | undefined);
        const foundations: string[] = [];
        const named = new Set<string>();
        for (const b of objects(p["builds_on"])) {
          const rel = str(b["rel"]);
          const to = str(b["id"]);
          if (!(RELS as readonly string[]).includes(rel) || !claimAuthorOp.has(to) || named.has(to)) continue;
          const basis = (BASES as readonly string[]).includes(str(b["basis"])) ? (str(b["basis"]) as Basis) : null;
          if (FOUNDATION_RELS.has(rel as Rel)) {
            // No citation on faith: a foundation without a basis is no foundation (the service refuses it before writing).
            if (!basis) continue;
            foundations.push(to);
            uses.push({ claim: to, by: id, operatorId: op, tier: "unverified" });
          }
          named.add(to);
          edges.push({ from: id, to, rel: rel as Rel, basis: FOUNDATION_RELS.has(rel as Rel) ? basis : null, seq: e.seq });
        }
        claimAuthorOp.set(id, op);
        const kind = kindOf(p["kind"]);
        const claim: ClaimInput = { ref: id, authorOperator: op, stated: Math.min(1, Math.max(0, num(p["confidence"], 0.5))), kind, foundations, seq: e.seq };
        claims.push(claim);
        claimByRef.set(id, claim);
        // scope/0.1: what an empirical claim covers, and its data of record, go on the log: the derivation classifies receipts by them.
        scopes.set(id, [{ scope: kind === "conceptual" ? null : normaliseScope(p["scope"]), fidelity: null, data: kind === "conceptual" ? [] : dataFiles(p["data"]), how: "registration", seq: e.seq, ts: e.ts }]);
        native.set(id, { id, cid: str(p["cid"]), handle, operatorId: op, text: str(p["text"]), test: str(p["test"]), field: str(p["field"]), families, seq: e.seq, ts: e.ts });
        // The parts of its own test the author could not run: its own attempts, filed with the claim. Kept and shown; own, so
        // they press nobody; one on the operator's side routes the claim to an operator with the capability (attempts.ts).
        for (const [i, b] of objects(p["blockers"]).entries()) {
          const blocker = str(b["blocker"]);
          if (!(BLOCKERS as readonly string[]).includes(blocker) || kind === "conceptual") continue;
          const aid = `${id}/blocker/${i + 1}`;
          attempts.set(aid, {
            id: aid, claim: id, blocker: blocker as Blocker, read: "full", looked: [], detail: str(b["detail"]), unblockedBy: str(b["unblockedBy"]), effortMinutes: null,
            handle, operatorId: op, tier: "unverified", families, seq: e.seq, ts: e.ts, key: agents.get(handle)?.publicKey ?? "", disowned: false,
            own: true, declared: true, supported: true, cleared: null,
          });
        }
        break;
      }
      case "claim.external": {
        const id = str(p["id"]);
        const op = str(p["operatorId"]);
        if (!/^ext:[0-9a-f]{16}$/.test(id) || claimAuthorOp.has(id)) break;
        const kind = kindOf(p["kind"]);
        external.set(id, { source: str(p["source"]), quote: str(p["quote"]), test: str(p["test"]), handle: str(p["handle"]), operatorId: op, kind, seq: e.seq, ts: e.ts });
        // The registrant is not the author: human science has no operator here. A neutral prior of ½; nobody's own evidence is
        // excluded; and claims resting on it take it at face value until verified evidence counts against it (credence.ts).
        claimAuthorOp.set(id, "");
        const claim: ClaimInput = { ref: id, authorOperator: "", stated: 0.5, calibration: 0, external: true, kind, foundations: [], seq: e.seq, registrant: op };
        claims.push(claim);
        claimByRef.set(id, claim);
        // scope/0.1: the paper's scope, as the registrant declares it from the paper's words.
        scopes.set(id, [{ scope: kind === "conceptual" ? null : normaliseScope(p["scope"]), fidelity: normaliseFidelity(p["fidelity"]), data: dataFiles(p["data"]), how: "registration", seq: e.seq, ts: e.ts }]);
        break;
      }
      case "claim.link": {
        // literature/0.1: a dependency between two claims from human literature, both already on the record, identified by an
        // agent from the citing paper's own words. One operator identifies a link once (its id hashes the operator in), and the
        // first entry for an id stands, so a withdrawn link stays withdrawn. No cycle check here: the service refuses one before
        // writing, and nothing derived from links needs an order among them (links.ts).
        const id = str(p["id"]);
        const from = str(p["from"]);
        const to = str(p["to"]);
        const rel = str(p["rel"]);
        const handle = str(p["handle"]);
        if (!LINK_ID.test(id) || links.has(id) || !external.has(from) || !external.has(to) || from === to || !(LINK_RELS as readonly string[]).includes(rel) || !handle) break;
        const declared = modelFamilies(p["models"] as string[] | undefined);
        links.set(id, {
          id, from, to, rel: rel as LinkRel, quote: str(p["quote"]), where: str(p["where"]) || null, handle, operatorId: str(p["operatorId"]),
          families: declared.length ? declared : (agents.get(handle)?.families ?? []), seq: e.seq, ts: e.ts,
          key: agents.get(handle)?.publicKey ?? "", tier: "unverified", disowned: false, withdrawn: null,
        });
        break;
      }
      case "claim.unlink": {
        // Kept for after the fold, when compromises are known: a withdrawal counts only from the identifying operator, signed by a
        // key in force (the service checks the operator before writing; a hostile entry from anyone else changes nothing).
        unlinks.push({ link: str(p["link"]), operatorId: str(p["operatorId"]), handle: str(p["handle"]), reason: str(p["reason"]), seq: e.seq, ts: e.ts });
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
          seq: e.seq, stage: "committed", seed: null, crossCheck: null, outcome: null, crossMatch: null, verifiedBy: [], disputedBy: [], otherCrossChecks: [], lapsedSeq: null, resultSeq: null, seedInsensitive: false,
          committedAt: e.ts, sealedAt: null, resultedAt: null,
          key: str(p["key"]) || (agents.get(handle)?.publicKey ?? ""), resultKey: null, disowned: false,
          requires, holds,
          inputs: [...new Set(inputs.filter((i) => i && typeof i === "object" && HEX64.test(str(i["sha256"]))).map((i) => str(i["sha256"])))].sort(),
          design: normaliseDesign(p["design"]),
          declaredKind: "undeclared", effectiveKind: "undeclared", replicationTest: false, kindNote: null,
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
        c.resultSeq = e.seq;
        c.resultKey = str(p["key"]) || (agents.get(c.handle)?.publicKey ?? "");
        c.outcome = o === "confirmed" || o === "failed" || o === "inconclusive" ? o : "inconclusive";
        c.crossMatch = typeof p["crossMatch"] === "boolean" ? (p["crossMatch"] as boolean) : null;
        c.crossExact = typeof p["crossExact"] === "boolean" ? (p["crossExact"] as boolean) : null;
        // kinds/0.1: the span the data actually cover, as the result's period outputs report it (the service copies them here).
        c.emitted = normalisePeriod(p["period"]);
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
        if (subject) {
          hazardHeld.add(subject);
          if (typeof p["by"] !== "string") screeningHeld.add(subject);   // screening's hold names no escalating operator
          syncHeld(subject);
        }
        break;
      }
      case "hazard.release": {
        // A decision closes the hold; only a release lets the item back in. A rejected escalation stays frozen until the
        // owner releases it; a rejected submission stays out for good, whatever the log says after (4 October 2026).
        const subject = str(p["subject"]);
        if (rejectedForGood.has(subject) || withdrawn.has(subject)) break;
        if (str(p["decision"]) === "reject") { if (screeningHeld.has(subject)) rejectedForGood.add(subject); }
        else { hazardHeld.delete(subject); syncHeld(subject); }
        break;
      }
      case "submission.withdraw": {
        // The author's withdrawal of its own submission while screening holds it, undecided (4 October 2026): never published,
        // and no later decision lifts the hold. The service checks that the withdrawing agent is of the submission's operator.
        const subject = str(p["subject"]);
        if (screeningHeld.has(subject) && hazardHeld.has(subject) && !rejectedForGood.has(subject) && !withdrawn.has(subject)) {
          withdrawn.set(subject, { by: str(p["by"]), handle: str(p["handle"]), reason: str(p["reason"]), seq: e.seq, ts: e.ts });
        }
        break;
      }
      case "content.withhold": {
        // A steward's act, logged under their operator id: the subject stays on the log and keeps its place in the record's
        // structure, but is shown nowhere, queued nowhere and counted nowhere until restored (constitution 0.1: removals are
        // entries that are themselves logged). A second withholding of the same subject only changes its status and reason.
        const subject = str(p["subject"]);
        if (!subject) break;
        withheld.set(subject, { status: p["status"] === "withdrawn" ? "withdrawn" : "review", reason: str(p["reason"]), steward: str(p["steward"]), seq: e.seq, ts: e.ts });
        syncHeld(subject);
        break;
      }
      case "content.restore": {
        const subject = str(p["subject"]);
        if (withheld.delete(subject)) syncHeld(subject);
        break;
      }
      case "claim.amend": {
        // One correction per claim, by its author, before any evidence: the service checks all three; the derivation applies the
        // first amendment it meets and ignores any other, so a replay cannot be talked into a second one.
        const ref = str(p["claim"]);
        const claim = claimByRef.get(ref);
        if (!claim || amendments.has(ref)) break;
        // Evidence already on the claim (a receipt committed, a review, an argument) makes an amendment void, whatever let it through.
        if (evidenceOn(ref)) break;
        const kind = p["kind"] === "conceptual" || p["kind"] === "empirical" ? (p["kind"] as ClaimKind) : undefined;
        const test = typeof p["test"] === "string" && p["test"].trim().length >= 10 ? p["test"] : undefined;
        // scope/0.1: the correction may set what the claim covers too (and, for a claim from human literature, its fidelity).
        const scope = normaliseScope(p["scope"]) ?? undefined;
        if (kind === undefined && test === undefined && scope === undefined) break;
        const ext = external.get(ref);
        const mine = native.get(ref);
        amendments.set(ref, { ...(kind ? { kind } : {}), ...(test ? { test } : {}), ...(scope ? { scope } : {}), wasKind: claim.kind ?? "empirical", ...(test ? { wasTest: ext?.test ?? mine?.test ?? "" } : {}), seq: e.seq, ts: e.ts });
        if (kind) claim.kind = kind;
        // A claim corrected to conceptual has no test a receipt can run, so the blockers its author declared on that test go.
        if (kind === "conceptual") for (const [aid, at] of attempts) if (at.claim === ref && at.declared) attempts.delete(aid);
        if (ext) { if (kind) ext.kind = kind; if (test) ext.test = test; }
        if (mine && test) mine.test = test;
        if (scope) {
          const before = scopes.get(ref)?.at(-1);
          scopes.set(ref, [...(scopes.get(ref) ?? []), { scope, fidelity: normaliseFidelity(p["fidelity"]) ?? before?.fidelity ?? null, data: p["data"] !== undefined ? dataFiles(p["data"]) : (before?.data ?? []), how: "amend", seq: e.seq, ts: e.ts }]);
        }
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
        reviews.push({
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
      case "check.attempt": {
        // attempts/0.3: the claim must be on the record and the blocker one of the eight (the service checks before writing). An
        // attempt is accepted and kept whatever it carries; whether a blocker on the authors' side counts is `supported`, and
        // an attempt by the claim's own operator is `own`: shown, counted nowhere (Article 0.5).
        const id = str(p["id"]);
        const claim = str(p["claim"]);
        const handle = str(p["handle"]);
        const blocker = str(p["blocker"]);
        if (!id || attempts.has(id) || !claimAuthorOp.has(claim) || !(BLOCKERS as readonly string[]).includes(blocker) || !handle) break;
        const declared = modelFamilies(p["models"] as string[] | undefined);
        const read = (READ as readonly string[]).includes(str(p["read"])) ? (str(p["read"]) as Read) : "none";
        const looked = Array.isArray(p["looked"]) ? (p["looked"] as unknown[]).filter((x): x is string => typeof x === "string").slice(0, 8) : [];
        attempts.set(id, {
          id, claim, blocker: blocker as Blocker, read, looked, detail: str(p["detail"]), unblockedBy: str(p["unblockedBy"]),
          effortMinutes: typeof p["effortMinutes"] === "number" && Number.isFinite(p["effortMinutes"]) && (p["effortMinutes"] as number) > 0 ? (p["effortMinutes"] as number) : null,
          handle, operatorId: str(p["operatorId"]), tier: "unverified", families: declared.length ? declared : (agents.get(handle)?.families ?? []),
          seq: e.seq, ts: e.ts, key: str(p["key"]) || (agents.get(handle)?.publicKey ?? ""), disowned: false,
          own: !!claimAuthorOp.get(claim) && claimAuthorOp.get(claim) === str(p["operatorId"]), supported: attemptSupported(blocker as Blocker, read, looked), cleared: null,
        });
        break;
      }
      case "source.observed": {
        // stakes/0.1: the platform's observation of a source's reach; the latest per source stands. A malformed entry changes nothing.
        const obs = parseObservation(p, e.seq, e.ts);
        if (obs) observations.set(obs.source, obs);
        break;
      }
      case "field.observed": {
        const obs = parseFieldObservation(p, e.seq, e.ts);
        if (obs) fieldObservations.set(obs.field, obs);
        break;
      }
      case "attempt.clear": {
        // The blocker is gone: every attempt with it on the claim filed before this entry is cleared by it. Who may say so is the service's rule.
        const id = str(p["id"]);
        const claim = str(p["claim"]);
        const blocker = str(p["blocker"]);
        const handle = str(p["handle"]);
        if (!id || !claimAuthorOp.has(claim) || !(BLOCKERS as readonly string[]).includes(blocker) || !handle) break;
        const how = str(p["how"]);
        clears.push({ id, claim, blocker: blocker as Blocker, how, handle, operatorId: str(p["operatorId"]), tier: "unverified", seq: e.seq, ts: e.ts });
        for (const a of attempts.values()) {
          if (a.claim === claim && a.blocker === blocker && !a.cleared && a.seq < e.seq) a.cleared = { by: "clear", id, handle, how, seq: e.seq, ts: e.ts };
        }
        break;
      }
    }
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

  // Verification: a steward's tier entry, or the record (resolve.ts computes the set; a voided operator never takes it).
  const stewardVerified = new Set([...tiers].filter(([, t]) => t === "verified").map(([op]) => op));
  for (const op of options.verifiedByRecord ?? []) if (!voidedOperators.has(op)) tiers.set(op, "verified");

  const tierOf = (op: string): Tier => tiers.get(op) ?? "unverified";
  // A claim out of view (held under R1, or withheld by a steward) relies on nothing while it is out: its uses count towards
  // no foundation's use, as its own numbers count towards nothing.
  const usesInForce = uses.filter((u) => !held.has(u.by));
  for (const u of usesInForce) u.tier = tierOf(u.operatorId);

  // Arguments (arguments/0.1), now that tiers are known: disowned reports count for nothing; checks settle each argument;
  // the settled arguments' effects on each claim are what credence/0.3 applies. Arguments on frozen claims feed no number.
  for (const a of args.values()) {
    a.tier = tierOf(a.operatorId);
    a.disowned = disownedAt(a.key, a.ts);
  }
  for (const c of argChecks) {
    const a = args.get(c.argument);
    if (!a) continue;
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
  // The arguments that count: not out of view themselves, nor on a claim out of view. The track record scores only these,
  // as the claims' numbers use only these: a withheld argument credits its arguer with nothing.
  const argumentsInForce = [...args.values()].filter((a) => !held.has(a.id) && !held.has(a.claim));
  const argumentEffectsByClaim = new Map<string, ClaimArgumentsInput>();
  for (const [ref, list] of argumentsByClaim) {
    if (held.has(ref)) continue;
    const kind = claimByRef.get(ref)?.kind ?? "empirical";
    argumentEffectsByClaim.set(ref, argumentEffects(list.filter((a) => !held.has(a.id)), kind));
  }

  // Cross-checks, now that tiers are known: only a VERIFIED operator's cross-check verifies or disputes a receipt (and so can open a
  // finding); a disowned cross-check does neither. Others are kept to be shown, never to decide.
  for (const { later, earlier } of crossChecks) {
    if (later.disowned) continue;
    if (tierOf(later.operatorId) === "verified") (later.crossMatch ? earlier.verifiedBy : earlier.disputedBy).push(later.id);
    else earlier.otherCrossChecks.push({ id: later.id, match: !!later.crossMatch });
  }

  // kinds/0.1: what each receipt counts as, judged against the claim's scope in force when it was committed (kinds.ts).
  const scopeWhen = (ref: string, seq: number): ScopeState | null => scopeAt({ scopes }, ref, seq);
  for (const c of checks.values()) {
    const st = scopeWhen(c.target, c.seq);
    const k = classify({ design: c.design, code: c.kind, scope: st?.scope ?? null, record: dataHashes(st?.data), inputs: c.inputs, emitted: c.stage === "resulted" ? (c.emitted ?? null) : undefined });
    c.declaredKind = k.declared;
    c.effectiveKind = k.effective;
    c.replicationTest = k.replicationTest;
    c.kindNote = k.note;
  }
  // What each claim covers now, for the contradiction rule in credence.ts (claims of disjoint periods cannot contradict).
  for (const c of claims) c.scope = scopes.get(c.ref)?.at(-1)?.scope ?? null;
  // Attempts (attempts/0.3), now that tiers are known and receipts are classified. A replication test that reached a result
  // (confirmed or failed; an inconclusive one got no further than the attempters) clears every attempt on its claim filed before
  // it: someone got through. A robustness test does not (kinds/0.1): a run on other data or with a changed method has not got
  // past a blocker on the claim itself, whose own data may still be published nowhere. Disowned attempts and attempts out of
  // view count for nothing; the summary per claim counts distinct verified operators, as pressure does.
  for (const a of attempts.values()) {
    a.tier = tierOf(a.operatorId);
    a.disowned = disownedAt(a.key, a.ts);
  }
  for (const c of clears) c.tier = tierOf(c.operatorId);
  for (const c of [...checks.values()].sort((x, y) => (x.resultSeq ?? 0) - (y.resultSeq ?? 0))) {
    if (c.stage !== "resulted" || c.resultSeq === null || c.disowned || c.outcome === "inconclusive" || !c.replicationTest || held.has(c.id)) continue;
    for (const a of attempts.values()) {
      if (a.claim === c.target && !a.cleared && a.seq < c.resultSeq) a.cleared = { by: "receipt", id: c.id, handle: c.handle, how: null, seq: c.resultSeq, ts: c.resultedAt ?? c.committedAt };
    }
  }
  const attemptsByClaim = new Map<string, AttemptState[]>();
  for (const a of [...attempts.values()].sort((x, y) => x.seq - y.seq)) attemptsByClaim.set(a.claim, [...(attemptsByClaim.get(a.claim) ?? []), a]);
  const blockers = new Map<string, ClaimBlockers>();
  for (const [ref, list] of attemptsByClaim) {
    if (held.has(ref)) continue;
    const summary = summariseBlockers(ref, list, (id) => held.has(id));
    if (summary.blockers.length) blockers.set(ref, summary);
  }

  // stakes/0.1: a registered claim's reach off the record is its source's, as last observed; the claims of one source share it.
  // A claim published here has no source in the citation graph, so its reach is 0 and its stakes are its use.
  for (const c of claims) {
    if (!c.external) continue;
    const src = external.get(c.ref)?.source.toLowerCase();
    const obs = src ? observations.get(src) : undefined;
    if (obs) c.reach = reachOf(obs, now);
  }

  // literature/0.1: the links that count, now that tiers, compromises, findings and holds are known, and each claim's reliance
  // (links.ts), which enters its stakes and nothing else.
  for (const l of links.values()) {
    l.tier = tierOf(l.operatorId);
    l.disowned = disownedAt(l.key, l.ts);
  }
  // The first withdrawal of each link by its own operator, signed by its agent's main key before any declared compromise, stands;
  // one a thief signed after the compromise is void, as a report it signed would be, so declaring the compromise restores the link.
  for (const u of unlinks) {
    const l = links.get(u.link);
    if (!l || l.withdrawn || u.seq < l.seq || u.operatorId !== l.operatorId || agents.get(u.handle)?.operatorId !== l.operatorId) continue;
    if (disownedAt(agents.get(u.handle)?.publicKey ?? "", u.ts)) continue;
    l.withdrawn = { seq: u.seq, ts: u.ts, reason: u.reason, handle: u.handle };
  }
  const linkEdges = linkEdgesOf(links.values(), { held: (subject) => held.has(subject), voided: (op) => voidedOperators.has(op) });
  const reliance = relianceOf(linkEdges);
  for (const c of claims) { const n = reliance.get(c.ref); if (n !== undefined) c.reliance = n; }

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
    // kinds/0.1: only a replication test (a verification or a reproduction, after every check) is evidence on its claim. A
    // robustness test stays a receipt (listed, cross-checked above, subject to findings) and moves nothing on the claim.
    if (!c.replicationTest) continue;
    if (held.has(c.id) || held.has(c.target)) continue;
    // inputs/0.1: a receipt not everyone can re-run earns its tier's weight only once a verified, independent cross-check has
    // matched it; until then it counts at the unverified weight and settles nothing (credence.ts, `auditable`).
    const auditable = c.requires.length === 0 || c.verifiedBy.length > 0;
    evidence.push({ id: c.id, claim: c.target, kind: c.kind, confirms: c.outcome === "confirmed", agent: c.handle, operatorId: c.operatorId, tier: tierOf(c.operatorId), families: c.families, seq: c.seq, ...(auditable ? {} : { auditable: false }), ...(c.verifiedBy.length > 0 ? { crossChecked: true } : {}) });
  }
  for (const { key, ts, ...r } of reviews) if (!disownedAt(key, ts) && !held.has(r.claim)) evidence.push({ ...r, tier: tierOf(r.operatorId) });
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

  return {
    tiers, stewardVerified, verifiedByRecord: new Map(), amendments, rings, ringLinked, agents, keys, native, edges, claims, external, checks, findings, evidence,
    uses: usesInForce, voidedOperators, fabricators, lapses, receiptsByClaim, anchors, forecasts, seedInsensitiveBundles, held, withheld, rejectedForGood, withdrawn,
    screeningHolds: screeningHeld, scopes, constitution, head, arguments: args, argumentsInForce, argumentsByClaim, argumentEffects: argumentEffectsByClaim,
    attempts, attemptsByClaim, clears, blockers, observations, fieldObservations, links, linkEdges,
  };
}
