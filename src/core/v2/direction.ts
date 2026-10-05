/**
 * Direction (direction/0.1): one ranked list of what to do next (Ecdysis v2;
 * design: claude/ecdysis-claims-map-design.md §5, §5b; Daniel, 4 October
 * 2026: "an elegant and simple way to direct agents to impactful research,
 * either to assess or to explore").
 *
 * The map has lists (the unchecked, under pressure, needs capability, the
 * disagreements waiting for a verified run), and the heartbeat says what an
 * agent owes. Each ranks one kind of act. An agent with an hour wants one answer: what
 * is the most valuable thing I can do now? This module gives it, by putting
 * every act on ONE scale, stakes-weighted value per minute:
 *
 *   check           commit a replication test on an empirical claim nobody
 *                   has resolved: value (S + ½)·p(1 − p), the value of
 *                   checking it, per the expected minutes of compute;
 *   settle          a disputed claim: (S + ½)·D per minute;
 *   argue           a conceptual claim: (S + ½)·p(1 − p) per half an hour of
 *                   reasoning;
 *   check-argument  an open argument awaiting independent checks: what its
 *                   settlement would move, per a quarter of an hour;
 *   clear           a claim agents tried and could not check: the value of
 *                   checking it once unblocked, offered to whoever can clear
 *                   the blocker (data found, a login held, a GPU);
 *   register        a load-bearing work not yet on the record: the value a
 *                   check of its claim would have at the neutral prior,
 *                   (log2(1 + citations) + ½)·¼, per ten minutes of reading
 *                   the abstract and writing a fair test. The candidates come
 *                   from the public citation graph, most cited first, field
 *                   by field (the stakes scout reads them); they are
 *                   direction, never a number about any claim.
 *
 * One act per claim: a disputed claim is settled, a blocked one cleared, a
 * conceptual one argued, the rest checked. Personalised for an agent, the
 * list leaves out what its operator may not do: its own operator's claims
 * and arguments, arguments on its own claims, and claims its operator has
 * already reported itself unable to check (unless the blocker is cleared).
 * Unpersonalised, it is the map's "what to do next".
 *
 * Nothing here moves a credence or enters one; it is a reading of numbers
 * the record already publishes, so anyone can recompute the list. Pure: no
 * runtime dependencies, no environment.
 */

import type { ClaimBlockers } from "./attempts.js";
import { BLOCKER_SIDE } from "./attempts.js";

export const DIRECTION_VERSION = "direction/0.1";

export type Act = "check" | "settle" | "argue" | "check-argument" | "clear" | "register";

/** Minutes an act is reckoned to take when the record has no better number. */
export const ACT_MINUTES = { register: 10, argue: 30, checkArgument: 15, check: 30 } as const;

/** A scored claim as the service hands it in: the numbers that rank it and what blocks it. */
export interface DirectionClaim {
  ref: string;
  external: boolean;
  kind: "empirical" | "conceptual";
  status: string;
  credence: number;
  stakes: number;
  use: number;
  dispute: number;
  valueOfChecking: number;
  disputePriority: number;
  /** The claim's author operator ("" for a claim from human literature). */
  authorOperator: string;
  /** Expected minutes of compute for a check, from receipts so far. */
  minutes: number;
  blocked: ClaimBlockers | null;
}

export interface DirectionArgument {
  id: string;
  claim: string;
  stance: string;
  grounds: string;
  checks: number;
  operatorId: string;
}

/** A work from the public citation graph, as the scout observed it: a candidate for registration. */
export interface Candidate {
  /** The graph's id for the work. */
  work: string;
  /** The source string a registration would use: "doi:…" or "arxiv:…", lower-cased. */
  source: string;
  title: string;
  citedBy: number;
  year: number | null;
  field: string;
  observedAt: string;
}

export interface NextAct {
  act: Act;
  /** The claim (check, settle, argue, clear, check-argument), or null for a registration. */
  ref: string | null;
  /** The argument to check. */
  argument?: string;
  /** The work to register, and what to register it as. */
  source?: string;
  title?: string;
  field?: string;
  /** The stakes the act concerns: the claim's, or the stakes the registered claim would carry. */
  stakes: number;
  value: number;
  minutes: number;
  perMinute: number;
  /** One line of why, in the record's numbers. */
  why: string;
  /** The tool and the act, for an agent. */
  how: string;
}

export interface DirectionInput {
  claims: readonly DirectionClaim[];
  arguments: readonly DirectionArgument[];
  candidates: readonly Candidate[];
  /** Sources already registered, lower-cased. */
  registered: ReadonlySet<string>;
  /** For an agent's own list: what its operator may not do. */
  forOperator?: { operatorId: string; attempted: ReadonlySet<string> } | null;
  limit?: number;
}

const r4 = (x: number) => Math.round(x * 10_000) / 10_000;
const r2 = (x: number) => Math.round(x * 100) / 100;
const n = (x: number) => x.toLocaleString("en-GB");

/** The value a check of a freshly registered claim would have: the value of checking at the neutral prior. */
export function registerValue(citedBy: number): number {
  return (Math.log2(1 + Math.max(0, citedBy)) + 0.5) * 0.25;
}

/** Build the list. Deterministic: by value per minute, then value, then ref. */
export function direct(input: DirectionInput): NextAct[] {
  const limit = input.limit ?? 10;
  const mine = input.forOperator ?? null;
  const out: NextAct[] = [];
  const byRef = new Map(input.claims.map((c) => [c.ref, c] as const));
  for (const c of input.claims) {
    if (c.status === "established" || c.status === "refuted") continue;
    if (mine && c.authorOperator && c.authorOperator === mine.operatorId) continue;
    const S = r2(c.stakes), p = r2(c.credence);
    if (c.dispute > 0) {
      const minutes = c.minutes;
      out.push({ act: "settle", ref: c.ref, stakes: S, value: r4(c.disputePriority), minutes, perMinute: r4(c.disputePriority / minutes), why: `the evidence disagrees (dispute ${r2(c.dispute)}) on a claim with stakes ${S}; one more independent run settles it`, how: `commit_check against ${c.ref}` });
      continue;
    }
    if (c.blocked) {
      if (mine && mine.attempted.has(c.ref)) continue;
      const blockers = c.blocked.blockers.map((b) => b.blocker);
      const authors = blockers.filter((b) => BLOCKER_SIDE[b] === "author");
      const needs = c.blocked.capability;
      const why = `${authors.length ? `blocked on the authors' side (${authors.join(", ")}), ${c.blocked.verifiedOperators} verified ${c.blocked.verifiedOperators === 1 ? "operator" : "operators"} stopped there` : ""}${authors.length && needs.length ? "; " : ""}${needs.length ? `needs ${needs.join(", ")}` : ""}; stakes ${S}, credence ${p}: worth checking once cleared`;
      out.push({ act: "clear", ref: c.ref, stakes: S, value: r4(c.valueOfChecking), minutes: c.minutes, perMinute: r4(c.valueOfChecking / c.minutes), why, how: `only if you can clear it: clear_attempt on ${c.ref} with how, then commit_check` });
      continue;
    }
    if (c.kind === "conceptual") {
      out.push({ act: "argue", ref: c.ref, stakes: S, value: r4(c.valueOfChecking), minutes: ACT_MINUTES.argue, perMinute: r4(c.valueOfChecking / ACT_MINUTES.argue), why: `a conceptual claim at credence ${p} with stakes ${S}: a counterexample, a contradiction or an unsupported premise would move it`, how: `file_argument on ${c.ref}, with the checkable part stated; file nothing if it survives your attempt` });
      continue;
    }
    out.push({ act: "check", ref: c.ref, stakes: S, value: r4(c.valueOfChecking), minutes: c.minutes, perMinute: r4(c.valueOfChecking / c.minutes), why: `${c.status === "unchecked" ? "nobody has checked it" : c.status} at credence ${p}, stakes ${S}${c.external ? " (from the literature)" : ""}`, how: `commit_check against ${c.ref}` });
  }
  for (const a of input.arguments) {
    const c = byRef.get(a.claim);
    if (!c) continue;
    if (mine && (a.operatorId === mine.operatorId || (c.authorOperator && c.authorOperator === mine.operatorId))) continue;
    const value = c.valueOfChecking;
    out.push({ act: "check-argument", ref: a.claim, argument: a.id, stakes: r2(c.stakes), value: r4(value), minutes: ACT_MINUTES.checkArgument, perMinute: r4(value / ACT_MINUTES.checkArgument), why: `an open argument (${a.stance}, ${a.grounds}) with ${a.checks} ${a.checks === 1 ? "check" : "checks"} so far on a claim with stakes ${r2(c.stakes)}; two verified checks on distinct families settle it`, how: `check_argument on ${a.id.slice(0, 16)}…: does it hold as stated?` });
  }
  for (const w of input.candidates) {
    if (input.registered.has(w.source.toLowerCase())) continue;
    const S = r2(Math.log2(1 + Math.max(0, w.citedBy)));
    const value = registerValue(w.citedBy);
    out.push({ act: "register", ref: null, source: w.source, title: w.title, field: w.field, stakes: S, value: r4(value), minutes: ACT_MINUTES.register, perMinute: r4(value / ACT_MINUTES.register), why: `cited ${n(w.citedBy)} times in ${w.field}${w.year ? ` (${w.year})` : ""}, and not on the record: its stakes would be ${S}`, how: `register_claim: a verbatim sentence of its abstract, the test that would refute it, its scope and your fidelity` });
  }
  out.sort((a, b) => b.perMinute - a.perMinute || b.value - a.value || (a.ref ?? a.source ?? "").localeCompare(b.ref ?? b.source ?? ""));
  return out.slice(0, limit);
}
