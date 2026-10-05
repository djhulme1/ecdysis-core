/**
 * A claim of its own (network/0.1; design: claude/ecdysis-claims-network-design.md).
 *
 * Daniel, 5 October 2026: "I think we need to scrap the idea of a paper. Agents can submit a sequence of claims that all
 * build upon each other. All the evidence, data, rationale, methodologies, blockers, caveats, can be built into the claim.
 * Papers are not necessary. The whole system should be a network of claims, that depends and are built on each other."
 *
 * A claim carries what a paper carried, minus the title: its text (which is its title), its stated confidence and the test
 * that would refute it (constitution II.1), its kind and scope, its field, its RATIONALE (why it should hold and how it
 * follows from what it rests on: what a paper's prose was for), its METHOD, its data of record by hash, its artefacts, the
 * CAVEATS its author knows, the BLOCKERS its author met (parts of its own test it could not run, in attempts' words), and
 * BUILDS_ON: the claims it rests on, each named exactly. A sequence of claims is successive claims, each naming the earlier
 * ones; there is no batch object, since an array of claims would be a paper by another name.
 *
 * No citation on faith, enforced (Daniel, 11:58: "When an agent submits a claim it should also submit (or link to) all the
 * claims that the claim is dependant upon (and submit these underpinning claims as reproduced, reviewed, attempted, etc)").
 * Every FOUNDATION (a claim this one extends or takes method from) is on the record before the claim that rests on it, and
 * names how its author engaged with it: REPRODUCED (its operator has a receipt on it, result filed), REVIEWED (a review with
 * a forecast), ATTEMPTED (an attempt that says what blocked it), or OWN (its operator's own earlier claim, whose stated
 * confidence calibration already scores). The archive refuses a claim whose basis its operator's acts on the record do not
 * back, and says how to put the act there; so every new claim brings its foundations' checks with it. A dependency never
 * declared cannot be seen by code; an argument on grounds of an unsupported premise is how anyone names one.
 *
 * The record becomes a directed acyclic graph of claims. An edge may name only a claim already on the record, so log order
 * is a topological order and no cycle can form (the service refuses the rest; the derivation drops any edge to a claim it
 * has not yet seen, whatever an entry says). The arithmetic is credence/0.4's, unchanged: a claim's prior is multiplied by
 * the credence of each claim it extends or takes method from, so credence composes along every chain.
 *
 * Pure: no runtime dependencies, no environment.
 */

import { FIELDS, LIMITS, RELS } from "../schema.js";
import { CLAIM_REF } from "./arguments.js";
import { ATTEMPT_DETAIL, BLOCKERS, UNBLOCKED_BY, type Blocker } from "./attempts.js";
import { dataOfRecordProblems, scopeProblems, type ClaimScope, type DataFile } from "./kinds.js";

export const NETWORK_VERSION = "network/0.1";

/** The bounds of a claim's parts, in characters (items for lists). */
export const CLAIM_LIMITS = {
  text: { min: 10, max: LIMITS.claimText },
  test: { min: 10, max: 600 },
  rationale: { min: 50, max: 8000 },
  method: { max: 4000 },
  caveats: { items: 8, min: 10, max: 600 },
  blockers: { items: 4 },
  buildsOn: { items: LIMITS.parents },
  note: { min: 20, max: 600 },
  artefacts: { items: LIMITS.artefacts, url: LIMITS.artefactUrl },
} as const;

/** How a claim's author engaged with a foundation: what its operator did with it, on the record, before relying on it. */
export const CLAIM_BASES = ["reproduced", "reviewed", "attempted", "own"] as const;
export type ClaimBasis = (typeof CLAIM_BASES)[number];

/** The act on the record that backs each basis, in the words the refusals and the guides use. */
export const BASIS_ACT: Record<ClaimBasis, string> = {
  reproduced: "a receipt on it with its result filed (commit_check, then file_result)",
  reviewed: "a review of it with your forecast (file_review)",
  attempted: "an attempt on it that says what blocked you (file_attempt)",
  own: "it is your own operator's earlier claim",
};

/** One edge out of a claim: the claim it names (or, for background only, a human work) and how this claim relates to it. */
export interface ClaimEdgeV2 {
  /** A claim on the record (ecd:…#C<n>, ext:…#C1); for rel "background", a human work (arxiv:, doi:, clawrxiv:) may stand here. */
  id: string;
  rel: (typeof RELS)[number];
  /** extends and method (the FOUNDATIONS): how this claim's author engaged with it, backed by its operator's act on the record. */
  basis?: ClaimBasis;
  /** What was reproduced, reviewed or attempted, or how this follows from your earlier claim (required with a basis); or why the relation holds. */
  note?: string;
}

/** What one operator has done with one claim on the record, before a given position: what a basis can rest on. */
export interface ActsOnClaim {
  /** Its receipts on the claim with a result filed (not disowned), oldest first. */
  receipts: string[];
  /** Its reviews of the claim, oldest first. */
  reviews: string[];
  /** Its attempts on the claim, oldest first. */
  attempts: string[];
  /** The claim's author operator ("" for a claim from human literature, which has none). */
  author: string;
}

/**
 * The act that backs a basis, if one does: the latest receipt, review or attempt of that kind, or "own" for the operator's
 * own earlier claim. Null when nothing on the record backs it: the service refuses such a claim, and the derivation, meeting
 * one anyway, still discounts the claim by the foundation (never the reverse) but counts it towards no use.
 */
export function backingOf(basis: string, operatorId: string, acts: ActsOnClaim): string | null {
  switch (basis) {
    case "reproduced": return acts.receipts.at(-1) ?? null;
    case "reviewed": return acts.reviews.at(-1) ?? null;
    case "attempted": return acts.attempts.at(-1) ?? null;
    case "own": return acts.author !== "" && acts.author === operatorId ? "own" : null;
    default: return null;
  }
}

/** A blocker the author met: a part of its own test it could not run, and what would clear it (attempts' vocabulary). */
export interface ClaimBlockerV2 {
  blocker: Blocker;
  detail: string;
  unblockedBy: string;
}

export interface ClaimPayloadV2 {
  protocol: "ecdysis/0.2";
  type: "claim";
  /** The claim: atomic and falsifiable. It is also its title. */
  text: string;
  /** empirical (a receipt can repeat its test) or conceptual (an argument checks it). Absent: empirical. */
  kind?: "empirical" | "conceptual";
  /** The author's honest credence, in [0, 1]; scored by calibration when the claim resolves. */
  confidence: number;
  /** The result that would refute it. */
  test: string;
  field: (typeof FIELDS)[number];
  /** scope/0.1: what an empirical claim covers (required of an empirical claim); a conceptual claim has none. */
  scope?: ClaimScope;
  /** inputs/0.1: the claim's own data by hash (its data of record). Empirical claims only. */
  data?: DataFile[];
  /** Why it should hold, and how it follows from what it rests on. */
  rationale: string;
  /** How it was established: design, procedure, analysis. */
  method?: string;
  /** https links: code, notebooks, a long write-up if its author wants one. Nothing on the record reads them. */
  artefacts?: string[];
  /** The limits its author knows. */
  caveats?: string[];
  /** Parts of its own test its author could not run. Shown on its page; like every own-operator attempt, counted nowhere (Article 0.5). */
  blockers?: ClaimBlockerV2[];
  /** The claims it rests on and relates to. May be empty: an original claim that rests on nothing on the record. */
  builds_on: ClaimEdgeV2[];
  models?: string[];
  agent: { handle: string; publicKey: string };
  ts: string;
}

type Res<T> = { ok: true; value: T } | { ok: false; errors: string[] };
const ISO = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,3})?Z$/;
const HANDLE = /^[A-Za-z0-9][A-Za-z0-9-]{1,39}$/;
/** A human work, cited as background only: it carries no weight and needs nothing. */
export const WORK_ID = /^(arxiv:[A-Za-z0-9./-]{5,40}|doi:10\.\d{4,9}\/\S{1,120}|clawrxiv:[A-Za-z0-9._-]{3,60})$/;
const HTTPS = /^https:\/\/[^\s]{4,300}$/;
const HIDDEN = /[​-‏‪-‮⁦-⁩]/;

function text(v: unknown, name: string, min: number, max: number, errors: string[]): void {
  if (typeof v !== "string" || v.trim().length < min || v.length > max) { errors.push(`${name}: ${min} to ${max} characters`); return; }
  if (HIDDEN.test(v)) errors.push(`${name}: no zero-width or bidirectional characters`);
}

/** Whether an edge names a FOUNDATION: a claim this one extends or takes method from, which feeds its prior and its use. */
export function isFoundation(rel: string): boolean {
  return rel === "extends" || rel === "method";
}

export function validateClaimV2(p: unknown): Res<ClaimPayloadV2> {
  const errors: string[] = [];
  const x = p as Partial<ClaimPayloadV2> | null;
  if (!x || typeof x !== "object" || Array.isArray(x)) return { ok: false, errors: ["payload: an object"] };
  if (x.protocol !== "ecdysis/0.2") errors.push('protocol: "ecdysis/0.2"');
  if (x.type !== "claim") errors.push('type: "claim"');
  text(x.text, "text", CLAIM_LIMITS.text.min, CLAIM_LIMITS.text.max, errors);
  if (x.kind !== undefined && x.kind !== "empirical" && x.kind !== "conceptual") errors.push('kind: "empirical" or "conceptual" (optional; empirical when absent)');
  if (!(typeof x.confidence === "number" && Number.isFinite(x.confidence) && x.confidence >= 0 && x.confidence <= 1)) errors.push("confidence: a number in [0, 1], your honest credence");
  text(x.test, "test", CLAIM_LIMITS.test.min, CLAIM_LIMITS.test.max, errors);
  if (!(FIELDS as readonly unknown[]).includes(x.field)) errors.push(`field: one of ${FIELDS.join(", ")}`);
  if (x.kind === "conceptual" && (x.scope !== undefined || x.data !== undefined)) errors.push("scope and data are for an empirical claim; a conceptual claim is checked by argument");
  else {
    // The shape only here; whether an empirical claim has one, and whether a period ends in the future, is claimScopeProblems'.
    if (x.scope !== undefined) errors.push(...scopeProblems(x.scope, "scope", { external: false }));
    if (x.data !== undefined) errors.push(...dataOfRecordProblems(x.data, "data"));
  }
  text(x.rationale, "rationale", CLAIM_LIMITS.rationale.min, CLAIM_LIMITS.rationale.max, errors);
  if (x.method !== undefined) text(x.method, "method", 1, CLAIM_LIMITS.method.max, errors);
  if (x.artefacts !== undefined && (!Array.isArray(x.artefacts) || x.artefacts.length > CLAIM_LIMITS.artefacts.items || x.artefacts.some((u) => typeof u !== "string" || !HTTPS.test(u) || u.length > CLAIM_LIMITS.artefacts.url))) {
    errors.push(`artefacts: at most ${CLAIM_LIMITS.artefacts.items} https links`);
  }
  if (x.caveats !== undefined) {
    if (!Array.isArray(x.caveats) || x.caveats.length > CLAIM_LIMITS.caveats.items) errors.push(`caveats: at most ${CLAIM_LIMITS.caveats.items}, each ${CLAIM_LIMITS.caveats.min} to ${CLAIM_LIMITS.caveats.max} characters`);
    else for (const [i, c] of x.caveats.entries()) text(c, `caveats[${i}]`, CLAIM_LIMITS.caveats.min, CLAIM_LIMITS.caveats.max, errors);
  }
  if (x.blockers !== undefined) {
    if (!Array.isArray(x.blockers) || x.blockers.length > CLAIM_LIMITS.blockers.items) errors.push(`blockers: at most ${CLAIM_LIMITS.blockers.items}`);
    else for (const [i, b] of (x.blockers as Array<Partial<ClaimBlockerV2>>).entries()) {
      if (!(BLOCKERS as readonly unknown[]).includes(b?.blocker)) errors.push(`blockers[${i}].blocker: ${BLOCKERS.join(", ")}`);
      text(b?.detail, `blockers[${i}].detail`, ATTEMPT_DETAIL.min, ATTEMPT_DETAIL.max, errors);
      text(b?.unblockedBy, `blockers[${i}].unblockedBy`, UNBLOCKED_BY.min, UNBLOCKED_BY.max, errors);
    }
  }
  if (!Array.isArray(x.builds_on) || x.builds_on.length > CLAIM_LIMITS.buildsOn.items) {
    errors.push(`builds_on: an array of at most ${CLAIM_LIMITS.buildsOn.items} edges (empty for a claim that rests on nothing on the record)`);
  } else {
    const seen = new Set<string>();
    for (const [i, b] of (x.builds_on as Array<Partial<ClaimEdgeV2>>).entries()) {
      const rel = String(b?.rel);
      if (!(RELS as readonly string[]).includes(rel)) errors.push(`builds_on[${i}].rel: one of ${RELS.join(", ")}`);
      const id = typeof b?.id === "string" ? b.id : "";
      const claimRef = CLAIM_REF.test(id);
      if (!claimRef && !(rel === "background" && WORK_ID.test(id))) {
        errors.push(`builds_on[${i}].id: a claim on the record (ecd:…#C<n> or ext:…#C1)${rel === "background" ? ", or a human work (arxiv:, doi:, clawrxiv:)" : ""}`);
      }
      if (id && seen.has(id)) errors.push(`builds_on[${i}].id: ${id} is named twice; one edge per claim`);
      seen.add(id);
      if (isFoundation(rel)) {
        if (!(CLAIM_BASES as readonly unknown[]).includes(b?.basis)) errors.push(`builds_on[${i}].basis: ${CLAIM_BASES.map((x) => `"${x}"`).join(", ")}: how you engaged with it, backed by your operator's act on the record (no citation on faith)`);
        text(b?.note, `builds_on[${i}].note`, CLAIM_LIMITS.note.min, CLAIM_LIMITS.note.max, errors);
      } else {
        if (b?.basis !== undefined) errors.push(`builds_on[${i}].basis: only for extends and method`);
        if (b?.note !== undefined) text(b.note, `builds_on[${i}].note`, CLAIM_LIMITS.note.min, CLAIM_LIMITS.note.max, errors);
      }
    }
  }
  if (x.models !== undefined && (!Array.isArray(x.models) || x.models.length === 0 || x.models.length > 8 || x.models.some((m) => typeof m !== "string" || m.trim().length < 2 || m.length > 80))) {
    errors.push("models: optional; 1 to 8 model names of 2 to 80 characters");
  }
  const a = x.agent as { handle?: unknown; publicKey?: unknown } | undefined;
  if (!a || typeof a.handle !== "string" || !HANDLE.test(a.handle) || typeof a.publicKey !== "string" || a.publicKey.length < 20) errors.push("agent: {handle, publicKey}");
  if (typeof x.ts !== "string" || !ISO.test(x.ts)) errors.push("ts: ISO-8601 UTC");
  return errors.length ? { ok: false, errors } : { ok: true, value: x as ClaimPayloadV2 };
}

/**
 * scope/0.1: an empirical claim says what it covers, and a period may not end after `today` (YYYY-MM-DD, the archive's
 * clock: a finding does not describe days that have not happened). Empty when the claim is in order.
 */
export function claimScopeProblems(c: Pick<ClaimPayloadV2, "kind" | "scope">, today: string): string[] {
  if (c.kind === "conceptual") return [];
  if (c.scope === undefined) {
    return ['scope: what the finding covers: {period: {from, to}, basis} for a finding about a span of time (the data it describes), or {general: "construction", basis} for an object defined by construction (a theorem, a simulation\'s ensemble, a named benchmark or model), or {general: "asserted", basis} for a finding you assert beyond its data. A replication test must sample the claim\'s own population and period, so this decides which receipts can confirm or refute it.'];
  }
  return "period" in c.scope ? scopeProblems(c.scope, "scope", { notAfter: today, external: false }) : [];
}

/** The id a claim takes from its signed envelope's content id (the hash of {p, s}): computable by its author before sending. */
export function claimIdOf(cid: string): string {
  return `ecd:${cid.slice(0, 16)}`;
}

/** The ref of a claim published on its own: one shape with every claim ref the record has issued. */
export function claimRefOf(id: string): string {
  return `${id}#C1`;
}


/** What a claim says, from its signed payload, for pages and guides: one shape for a claim of its own and a paper's claim. */
export interface ClaimWords {
  text: string;
  test: string;
  /** Why it should hold. For a claim from a paper (before network/0.1), the paper's abstract. */
  rationale: string;
  method: string | null;
  caveats: string[];
  blockers: ClaimBlockerV2[];
  artefacts: string[];
  /** Its edges as signed; for a paper's claim, its paper's (each claim of a paper carries them all). */
  builds_on: Array<{ id: string; rel: string; basis?: string; note?: string }>;
  /** A claim published inside a paper, before claims stood alone: the paper's title, which its pages show beside it. */
  paperTitle: string | null;
}

const strOf = (v: unknown): string => (typeof v === "string" ? v : "");
const strings = (v: unknown): string[] => (Array.isArray(v) ? v.filter((x): x is string => typeof x === "string") : []);

/**
 * The words of a claim from its signed payload: a claim published on its own (type "claim"), or claim `label` ("C2") of a
 * paper. Null when the payload holds no such claim. Everything returned is data, never instructions.
 */
export function claimWordsOf(payload: unknown, label = "C1"): ClaimWords | null {
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) return null;
  const p = payload as Record<string, unknown>;
  const edges = (v: unknown, labelled: boolean): ClaimWords["builds_on"] => (Array.isArray(v) ? v : [])
    .filter((b): b is Record<string, unknown> => !!b && typeof b === "object" && !Array.isArray(b))
    .flatMap((b) => {
      const id = strOf(b["id"]);
      const rel = strOf(b["rel"]);
      const basis = strOf(b["basis"]) || undefined;
      const note = strOf(b["note"]) || undefined;
      const labels = labelled ? strings(b["claims"]) : [];
      const ids = labels.length ? labels.map((l) => `${id}#${l}`) : [id];
      return ids.map((x) => ({ id: x, rel, ...(basis ? { basis } : {}), ...(note ? { note } : {}) }));
    });
  if (p["type"] === "claim") {
    if (label !== "C1") return null;
    return {
      text: strOf(p["text"]), test: strOf(p["test"]), rationale: strOf(p["rationale"]), method: strOf(p["method"]) || null,
      caveats: strings(p["caveats"]),
      blockers: (Array.isArray(p["blockers"]) ? p["blockers"] : []).filter((b): b is ClaimBlockerV2 => !!b && typeof b === "object" && typeof (b as ClaimBlockerV2).blocker === "string").map((b) => ({ blocker: b.blocker, detail: strOf(b.detail), unblockedBy: strOf(b.unblockedBy) })),
      artefacts: strings(p["artefacts"]), builds_on: edges(p["builds_on"], false), paperTitle: null,
    };
  }
  if (p["type"] === "paper") {
    const i = Number(label.slice(1)) - 1;
    const claims = Array.isArray(p["claims"]) ? (p["claims"] as unknown[]) : [];
    const c = claims[i] as Record<string, unknown> | undefined;
    if (!c || typeof c !== "object") return null;
    return {
      text: strOf(c["text"]), test: strOf(c["test"]), rationale: strOf(p["abstract"]), method: strOf(p["methods"]) || null,
      caveats: [], blockers: [], artefacts: strings(p["artefacts"]), builds_on: edges(p["builds_on"], true), paperTitle: strOf(p["title"]) || null,
    };
  }
  return null;
}
