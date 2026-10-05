/**
 * The claims map (map/0.1): how completely the literature has been
 * assessed, field by field, and where the stakes still sit (Ecdysis v2;
 * design: claude/ecdysis-claims-map-design.md §5, Daniel, 4 October 2026:
 * "paint a picture of how complete we have been in assessing the claims
 * across the whole scientific literature, and how important each claim is").
 *
 * Per field, a funnel with both a count and a sum of stakes at each stage,
 * so the headline is honest about importance rather than volume:
 *
 *   works in the field (the citation graph's count, the denominator)
 *   → sources registered → claims registered → attempted → blocked, by
 *   blocker → assessed (a receipt that reached a result, or a settled
 *   argument) → resolved (established or refuted).
 *
 * Four lists fall out, each recomputable by anyone from the same log:
 *   the unchecked      highest stakes, no evidence, no attempt: where effort
 *                      should go;
 *   under pressure     highest pressure (stakes × (1 − 2^−n) over verified
 *                      operators stopped by something only the authors can
 *                      supply): where authors, funders and journals should
 *                      look;
 *   needs capability   blocked on the operator's side (a paywall, restricted
 *                      data, a closed artefact, apparatus, compute), highest
 *                      stakes first: where laboratories, sponsors and
 *                      operators with access can help; no pressure on anyone;
 *   cleared            blockers removed recently, by whom: where the record
 *                      is already changing behaviour.
 *
 * A field is the source paper's field in the citation graph (OpenAlex's 26
 * fields, as the stakes scout observed it), or for a claim published here its
 * declared field. Coverage is the registered sources' citations as a share
 * of the field's, when the scout has observed the field's totals. Pure: the
 * service hands in the scored claims; nothing here reads the environment.
 */

import type { Blocker, ClaimBlockers } from "./attempts.js";
import { pressure } from "./attempts.js";

export const MAP_VERSION = "map/0.1";
/** Claims whose source the scout has not yet placed in a field. */
export const UNPLACED_FIELD = "Not yet placed";

export interface MapClaim {
  ref: string;
  external: boolean;
  field: string;
  /** The registered source, lower-cased, for a claim from human literature; null for a claim published here. */
  source: string | null;
  stakes: number;
  reach: number;
  use: number;
  credence: number;
  status: string;
  /** At least one attempt was ever filed on it (cleared or not). */
  attempted: boolean;
  /** What blocks it as it stands, or null. */
  blocked: ClaimBlockers | null;
  /** A receipt reached a result (not inconclusive, not disowned) or an argument settled. */
  assessed: boolean;
  /** established or refuted. */
  resolved: boolean;
  /** Attempts filed, counting every operator once per blocker. */
  attempts: number;
}

export type { FieldObservation } from "./stakes.js";
import type { FieldObservation } from "./stakes.js";

export interface Stage { claims: number; stakes: number }

export interface FieldRow {
  field: string;
  /** Distinct registered sources in the field (external claims), and the citations the scout observed for them. */
  sources: number;
  sourcesCitedBy: number;
  registered: Stage;
  attempted: Stage;
  blocked: Stage & { byBlocker: Partial<Record<Blocker, Stage>> };
  assessed: Stage;
  resolved: Stage;
  /** The field's totals in the citation graph, when observed. */
  denominator: FieldObservation | null;
  /** Registered sources' citations as a share of the field's, when the denominator is known. */
  coverage: number | null;
  /** The share of registered stakes that reached an assessment. */
  assessedShare: number | null;
}

export interface MapView {
  version: typeof MAP_VERSION;
  fields: FieldRow[];
  totals: Omit<FieldRow, "field" | "denominator" | "coverage">;
  unchecked: Array<{ ref: string; field: string; stakes: number; reach: number; use: number; credence: number; status: string; external: boolean }>;
  underPressure: Array<{ ref: string; field: string; stakes: number; pressure: number; verifiedOperators: number; blockers: Blocker[]; dominant: Blocker | null }>;
  /** Claims blocked on the operator's side: what an operator would need (`capability`), and how many have tried. */
  needsCapability: Array<{ ref: string; field: string; stakes: number; capability: Blocker[]; verifiedOperators: number; otherOperators: number; unblockedBy: string | null }>;
  cleared: Array<{ ref: string; field: string; blocker: Blocker; by: string; how: string | null; at: string; stakes: number }>;
}

export interface ClearedInput { ref: string; blocker: Blocker; by: string; how: string | null; at: string; seq: number }

const stage = (): Stage => ({ claims: 0, stakes: 0 });
const add = (s: Stage, c: { stakes: number }) => { s.claims += 1; s.stakes += c.stakes; };
const r4 = (x: number) => Math.round(x * 10_000) / 10_000;
const roundStage = (s: Stage): Stage => ({ claims: s.claims, stakes: r4(s.stakes) });

/** Build the map from scored claims, the clearings and the fields observed. Deterministic: fields sort by registered stakes, lists by their number then ref. */
export function buildMap(claims: readonly MapClaim[], cleared: readonly ClearedInput[], fieldObservations: ReadonlyMap<string, FieldObservation>, sourceCitations: ReadonlyMap<string, number>, limit = 20): MapView {
  type Row = FieldRow & { sourceSet: Set<string> };
  const rows = new Map<string, Row>();
  const totalsSources = new Set<string>();
  const fresh = (field: string): Row => ({ field, sources: 0, sourcesCitedBy: 0, registered: stage(), attempted: stage(), blocked: { ...stage(), byBlocker: {} as Partial<Record<Blocker, Stage>> }, assessed: stage(), resolved: stage(), denominator: fieldObservations.get(field) ?? null, coverage: null, assessedShare: null, sourceSet: new Set<string>() });
  const totals = fresh("all");
  const tally = (row: Row, c: MapClaim) => {
    add(row.registered, c);
    if (c.attempted) add(row.attempted, c);
    if (c.blocked) {
      add(row.blocked, c);
      for (const b of c.blocked.blockers) { const s = row.blocked.byBlocker[b.blocker] ?? stage(); add(s, c); row.blocked.byBlocker[b.blocker] = s; }
    }
    if (c.assessed) add(row.assessed, c);
    if (c.resolved) add(row.resolved, c);
    if (c.source && !row.sourceSet.has(c.source)) { row.sourceSet.add(c.source); row.sources += 1; row.sourcesCitedBy += sourceCitations.get(c.source) ?? 0; }
  };
  for (const c of claims) {
    const row = rows.get(c.field) ?? fresh(c.field);
    rows.set(c.field, row);
    tally(row, c);
    if (c.source) totalsSources.add(c.source);
    tally(totals, c);
  }
  const finish = (row: Row): FieldRow => {
    const { sourceSet, ...rest } = row;
    void sourceSet;
    const byBlocker: Partial<Record<Blocker, Stage>> = {};
    for (const [k, v] of Object.entries(rest.blocked.byBlocker) as Array<[Blocker, Stage]>) byBlocker[k] = roundStage(v);
    return {
      ...rest,
      sourcesCitedBy: rest.sourcesCitedBy,
      registered: roundStage(rest.registered), attempted: roundStage(rest.attempted), blocked: { ...roundStage(rest.blocked), byBlocker }, assessed: roundStage(rest.assessed), resolved: roundStage(rest.resolved),
      coverage: rest.denominator && rest.denominator.citedBy > 0 ? r4(Math.min(1, rest.sourcesCitedBy / rest.denominator.citedBy)) : null,
      assessedShare: rest.registered.stakes > 0 ? r4(rest.assessed.stakes / rest.registered.stakes) : null,
    };
  };
  const fields = [...rows.values()].map(finish).sort((a, b) => b.registered.stakes - a.registered.stakes || b.registered.claims - a.registered.claims || a.field.localeCompare(b.field));
  const t = finish(totals);
  const { field: _f, denominator: _d, coverage: _c, ...totalsOut } = t;
  void _f; void _d; void _c;
  const unchecked = claims.filter((c) => !c.assessed && !c.attempted && !c.resolved && !c.blocked)
    .sort((a, b) => b.stakes - a.stakes || a.ref.localeCompare(b.ref)).slice(0, limit)
    .map((c) => ({ ref: c.ref, field: c.field, stakes: r4(c.stakes), reach: c.reach, use: r4(c.use), credence: r4(c.credence), status: c.status, external: c.external }));
  // Under pressure: the authors' blockers only (attempts/0.2); every blocker in force is listed, the pressure counts the authors'.
  const underPressure = claims.filter((c) => c.blocked && c.blocked.dominant !== null)
    .map((c) => ({ ref: c.ref, field: c.field, stakes: r4(c.stakes), pressure: r4(pressure(c.stakes, c.blocked!.verifiedOperators)), verifiedOperators: c.blocked!.verifiedOperators, blockers: c.blocked!.blockers.map((b) => b.blocker), dominant: c.blocked!.dominant }))
    .sort((a, b) => b.pressure - a.pressure || b.verifiedOperators - a.verifiedOperators || b.stakes - a.stakes || a.ref.localeCompare(b.ref)).slice(0, limit);
  // Needs capability: the operator's blockers, highest stakes first; the operators counted are those stopped on that side.
  const needsCapability = claims.filter((c) => c.blocked && c.blocked.capability.length > 0)
    .map((c) => {
      const ops = c.blocked!.blockers.filter((b) => b.side === "operator");
      return { ref: c.ref, field: c.field, stakes: r4(c.stakes), capability: c.blocked!.capability, verifiedOperators: Math.max(0, ...ops.map((b) => b.verifiedOperators)), otherOperators: Math.max(0, ...ops.map((b) => b.otherOperators)), unblockedBy: ops[0]?.unblockedBy[0] ?? null };
    })
    .sort((a, b) => b.stakes - a.stakes || b.verifiedOperators - a.verifiedOperators || a.ref.localeCompare(b.ref)).slice(0, limit);
  const byRef = new Map(claims.map((c) => [c.ref, c] as const));
  const clearedOut = [...cleared].sort((a, b) => b.seq - a.seq).slice(0, limit)
    .map((x) => ({ ref: x.ref, field: byRef.get(x.ref)?.field ?? UNPLACED_FIELD, blocker: x.blocker, by: x.by, how: x.how, at: x.at, stakes: r4(byRef.get(x.ref)?.stakes ?? 0) }));
  return { version: MAP_VERSION, fields, totals: totalsOut, unchecked, underPressure, needsCapability, cleared: clearedOut };
}
