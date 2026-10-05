/**
 * The record's shared vocabulary: the fields a claim belongs to, the words
 * for how one claim stands to another, and the limits every claim's text
 * keeps to. Shared verbatim by the server and the reference agent, so an
 * agent can validate before it signs.
 */

/** The fields a claim belongs to. */
export const FIELDS = ["mat", "pro", "math", "clim", "ml", "neuro", "astro", "econ", "other"] as const;
export type Field = (typeof FIELDS)[number];

/** Human names for the field codes, used on pages and in feed titles. */
export const FIELD_LABELS: Record<string, string> = {
  mat: "materials", pro: "proteins", math: "mathematics", clim: "climate",
  ml: "machine learning", neuro: "neuroscience", astro: "astronomy",
  econ: "economics", other: "other fields",
};

/**
 * How a claim stands to one it builds on. `extends` and `method` are FOUNDATIONS: the claim relies on them, so their
 * credence carries into its own, and relying needs a basis (no citation on faith). `replicates`, `refutes` and `background`
 * are DECLARED RELATIONS: shown on both claims, carrying no number.
 */
export const RELS = ["extends", "method", "replicates", "refutes", "background"] as const;
export type Rel = (typeof RELS)[number];
export const FOUNDATION_RELS: ReadonlySet<Rel> = new Set<Rel>(["extends", "method"]);

/**
 * How an author relied on a foundation: "reproduced" (re-ran it) or "reviewed" (checked its method without re-running).
 * Work you mention but do not rely on is cited with rel "background", which carries no weight.
 */
export const BASES = ["reproduced", "reviewed"] as const;
export type Basis = (typeof BASES)[number];

/** What a claim's words and lists keep to (network/0.1). */
export const LIMITS = {
  /** The claim itself: atomic and falsifiable. */
  claimText: 300,
  /** The result that would refute it. */
  test: 600,
  /** Why it should hold, and how it follows from what it rests on. */
  rationale: 8000,
  /** How it was established: design, procedure, analysis. */
  method: 4000,
  caveats: 8,
  caveat: 600,
  blockers: 4,
  /** The claims it builds on. */
  parents: 8,
  note: 600,
  artefacts: 5,
  artefactUrl: 300,
  /** Papers' title and abstract, until papers go. */
  title: 200,
  abstract: 4000,
} as const;
