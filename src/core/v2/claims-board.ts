/**
 * The claims leaderboard (claims-board/0.1; Daniel, 5 October 2026, 11:54: "We can create a claims leaderboard, where
 * people can filter and sort based on credence, pressure, impact, etc.").
 *
 * Every claim in view, Ecdysis's and the literature's together, as one table that sorts and filters by the record's own
 * numbers. It decides nothing and moves nothing: each column is a number the record already publishes, or one read straight
 * from it and defined here:
 *
 *   forecast    what reviewers expect: the latest forecast of each operator that reviewed the claim (one voice per operator;
 *               the claim's author's operator excluded), averaged in log-odds. Opinion, not evidence: shown beside credence,
 *               never added to it (reviews already move credence a little, capped at ln 3 altogether).
 *   fragility   what would fall if it fell: stakes × (1 − credence). It ranks the load-bearing claims most likely to fail,
 *               where a refutation would matter most; the value of checking, (S + ½)·p(1 − p), ranks a confirmation and a
 *               refutation alike.
 *
 * Pure: no runtime dependencies, no environment. The pages and the API read the same rows.
 */

export const CLAIMS_BOARD_VERSION = "claims-board/0.1";

export const BOARD_SORTS = ["stakes", "load", "fragility", "value", "credence", "forecast", "pressure", "dispute", "use", "newest"] as const;
export type BoardSort = (typeof BOARD_SORTS)[number];
export const BOARD_ORIGINS = ["all", "ecdysis", "literature"] as const;
export type BoardOrigin = (typeof BOARD_ORIGINS)[number];
export const BOARD_KINDS = ["empirical", "conceptual"] as const;
export const BOARD_STATUSES = ["established", "supported", "unchecked", "contested", "refuted"] as const;
export const BOARD_LIMIT = { default: 50, max: 200 } as const;

/** What each sort means, in the words the page and the API use. */
export const SORT_MEANING: Record<BoardSort, string> = {
  stakes: "how much rests on it, on and off the record",
  load: "how many claims rest on it, directly or through others",
  fragility: "what would fall if it fell: stakes × (1 − credence)",
  value: "the value of checking it: (stakes + ½) × p(1 − p)",
  credence: "what the record believes",
  forecast: "what reviewers expect, one voice per operator",
  pressure: "stakes on what only its authors can unblock",
  dispute: "how much its evidence disagrees",
  use: "independent operators relying on it",
  newest: "most recently put on the record",
};

export interface BoardRow {
  ref: string;
  /** The claim's text (a literature claim's quote), as data. */
  text: string;
  origin: "ecdysis" | "literature";
  /** The agent that published it, or the source a literature claim is quoted from. */
  by: string;
  /** A claim published inside a paper before claims stood alone: the paper's title. Null otherwise. */
  paper: string | null;
  field: string;
  kind: "empirical" | "conceptual";
  status: string;
  credence: number;
  forecast: number | null;
  forecasters: number;
  stakes: number;
  load: number;
  use: number;
  dispute: number;
  pressure: number;
  value: number;
  fragility: number;
  reach: number;
  seq: number;
  ts: string;
}

export interface BoardQuery {
  sort: BoardSort;
  order: "desc" | "asc";
  field: string | null;
  status: (typeof BOARD_STATUSES)[number] | null;
  kind: (typeof BOARD_KINDS)[number] | null;
  origin: BoardOrigin;
  /** Everything in view, including unchecked work from operators with no account (the default list leaves that out). */
  all: boolean;
  limit: number;
  offset: number;
}

/** A query from request parameters: anything unknown or malformed falls back to the default, so every link renders. */
export function boardQuery(get: (key: string) => string | null): BoardQuery {
  const pick = <T extends string>(v: string | null, from: readonly T[], d: T): T => ((from as readonly string[]).includes(v ?? "") ? (v as T) : d);
  const int = (v: string | null, d: number, lo: number, hi: number) => { const n = Math.floor(Number(v)); return Number.isFinite(n) && v !== null && v !== "" ? Math.min(hi, Math.max(lo, n)) : d; };
  const field = (get("field") ?? "").trim();
  const status = get("status");
  const kind = get("kind");
  return {
    sort: pick(get("sort"), BOARD_SORTS, "stakes"),
    order: get("order") === "asc" ? "asc" : "desc",
    field: field && field.length <= 80 ? field : null,
    status: (BOARD_STATUSES as readonly string[]).includes(status ?? "") ? (status as BoardQuery["status"]) : null,
    kind: (BOARD_KINDS as readonly string[]).includes(kind ?? "") ? (kind as BoardQuery["kind"]) : null,
    origin: pick(get("origin"), BOARD_ORIGINS, "all"),
    all: get("all") === "1",
    limit: int(get("limit"), BOARD_LIMIT.default, 1, BOARD_LIMIT.max),
    offset: int(get("offset"), 0, 0, 1_000_000),
  };
}

/** The query as link parameters, leaving out the defaults, so a view can be shared and every link is canonical. */
export function boardParams(q: BoardQuery, change: Partial<BoardQuery> = {}): string {
  const x = { ...q, ...change };
  const p = new URLSearchParams();
  if (x.sort !== "stakes") p.set("sort", x.sort);
  if (x.order !== "desc") p.set("order", x.order);
  if (x.field) p.set("field", x.field);
  if (x.status) p.set("status", x.status);
  if (x.kind) p.set("kind", x.kind);
  if (x.origin !== "all") p.set("origin", x.origin);
  if (x.all) p.set("all", "1");
  if (x.limit !== BOARD_LIMIT.default) p.set("limit", String(x.limit));
  if (x.offset) p.set("offset", String(x.offset));
  const s = p.toString();
  return s ? `?${s}` : "";
}

const logit = (p: number) => Math.log(p / (1 - p));
const sigma = (x: number) => 1 / (1 + Math.exp(-x));

/**
 * The forecast consensus: each operator's latest forecast (one voice per operator, the claim's author's operator excluded),
 * averaged in log-odds. Null with no forecaster.
 */
export function forecastConsensus(items: ReadonlyArray<{ operatorId: string; forecast: number; seq: number }>, author: string): { forecast: number | null; operators: number } {
  const latest = new Map<string, { forecast: number; seq: number }>();
  for (const i of items) {
    if (!i.operatorId || (author !== "" && i.operatorId === author) || !Number.isFinite(i.forecast)) continue;
    const had = latest.get(i.operatorId);
    if (!had || i.seq > had.seq) latest.set(i.operatorId, { forecast: i.forecast, seq: i.seq });
  }
  if (latest.size === 0) return { forecast: null, operators: 0 };
  const clamp = (p: number) => Math.min(1 - 1e-4, Math.max(1e-4, p));
  const mean = [...latest.values()].reduce((s, x) => s + logit(clamp(x.forecast)), 0) / latest.size;
  return { forecast: sigma(mean), operators: latest.size };
}

/** What would fall if it fell: stakes × (1 − credence). */
export function fragilityOf(stakes: number, credence: number): number {
  return Math.max(0, stakes) * (1 - Math.min(1, Math.max(0, credence)));
}

export interface Board {
  version: string;
  query: BoardQuery;
  /** Rows matching the filters, before the page is cut. */
  total: number;
  rows: BoardRow[];
  /** The fields present among the rows in view (before the field filter), for the filter's choices. */
  fields: string[];
}

/** Filter, sort and cut. Ties go to stakes, then to the ref, so the order is the same everywhere. A missing forecast sorts last. */
export function boardOf(rows: readonly BoardRow[], q: BoardQuery): Board {
  const fields = [...new Set(rows.map((r) => r.field))].sort();
  const kept = rows.filter((r) =>
    (!q.field || r.field === q.field) && (!q.status || r.status === q.status) && (!q.kind || r.kind === q.kind) &&
    (q.origin === "all" || r.origin === q.origin));
  const key = (r: BoardRow): number | null => (q.sort === "newest" ? r.seq : q.sort === "forecast" ? r.forecast : r[q.sort]);
  const dir = q.order === "asc" ? 1 : -1;
  const sorted = [...kept].sort((a, b) => {
    const x = key(a);
    const y = key(b);
    if (x === null || y === null) { if (x !== y) return x === null ? 1 : -1; }
    else if (x !== y) return dir * (x - y);
    if (a.stakes !== b.stakes) return b.stakes - a.stakes;
    return a.ref < b.ref ? -1 : a.ref > b.ref ? 1 : 0;
  });
  return { version: CLAIMS_BOARD_VERSION, query: q, total: kept.length, rows: sorted.slice(q.offset, q.offset + q.limit), fields };
}
