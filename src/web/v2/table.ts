/**
 * The catalogue table (table/0.1): every list of things on the site is one of these. A table you can search, filter, sort
 * and page through, with no script: the filters are a GET form that submits to the page itself, the column headings are
 * links that sort, each active filter is a pill whose link removes it, and the server does the work. On a phone each row
 * stacks into a block, its values labelled, so nothing scrolls sideways.
 *
 * Pure: the query is read from the URL, the rows are filtered, sorted and cut here, and the markup is a string with every
 * value escaped by the cell renderers (cells return trusted markup; anything from a submission must be escaped by them).
 */

import { esc } from "../design.js";

export interface TableQuery {
  /** Free text, matched case-insensitively against each row's searchable text. */
  q: string;
  sort: string;
  order: "asc" | "desc";
  /** 1-based. */
  page: number;
  /** One value per filter, by name; absent filters are not set. */
  filters: Record<string, string>;
}

export interface FilterSpec {
  name: string;
  label: string;
  /** The choices: [value, label]. The first choice of a select is always "any" (the empty value), added here. */
  options: ReadonlyArray<readonly [string, string]>;
  /** What "any" reads as in the select (default "Any"). */
  any?: string;
}

export interface SortSpec<R> {
  key: string;
  /** The value rows are ordered by; strings sort alphabetically, numbers numerically; null sorts last whatever the order. */
  by: (r: R) => number | string | null;
  /** The order a first click on the heading gives (numbers usually descending, names ascending). */
  first?: "asc" | "desc";
}

export interface QuerySpec<R> {
  sorts: ReadonlyArray<SortSpec<R>>;
  defaultSort: string;
  filters: ReadonlyArray<FilterSpec>;
  perPage?: number;
}

export const PER_PAGE = 50;
const MAX_Q = 120;

/** The query a URL asks for, every part checked against what the table offers: anything unknown falls back to the default. */
export function tableQuery<R>(params: URLSearchParams, spec: QuerySpec<R>): TableQuery {
  const sortKey = params.get("sort") ?? "";
  const sort = spec.sorts.find((s) => s.key === sortKey) ?? spec.sorts.find((s) => s.key === spec.defaultSort) ?? spec.sorts[0];
  const orderParam = params.get("order");
  const order = orderParam === "asc" || orderParam === "desc" ? orderParam : sort?.first ?? "desc";
  const page = Math.max(1, Math.min(10_000, Math.floor(Number(params.get("page") ?? "1")) || 1));
  const filters: Record<string, string> = {};
  for (const f of spec.filters) {
    const v = params.get(f.name);
    if (v && f.options.some(([value]) => value === v)) filters[f.name] = v;
  }
  return { q: (params.get("q") ?? "").trim().slice(0, MAX_Q), sort: sort?.key ?? spec.defaultSort, order, page, filters };
}

/**
 * Filter, sort and cut rows by a query. `text` is what the search box searches (the claim, its id, its source, its author);
 * `match` says whether a row passes one filter. Ties keep the incoming order, so the caller's default order is stable.
 */
export function applyQuery<R>(rows: readonly R[], q: TableQuery, spec: QuerySpec<R> & { text: (r: R) => string; match: (r: R, filter: string, value: string) => boolean }): { total: number; rows: R[]; pages: number; page: number } {
  const needle = q.q.toLowerCase();
  const words = needle.split(/\s+/).filter(Boolean);
  const kept = rows.filter((r) => {
    for (const [name, value] of Object.entries(q.filters)) if (!spec.match(r, name, value)) return false;
    if (!words.length) return true;
    const hay = spec.text(r).toLowerCase();
    return words.every((w) => hay.includes(w));
  });
  const sort = spec.sorts.find((s) => s.key === q.sort);
  const ordered = sort ? kept.map((r, i) => ({ r, i, v: sort.by(r) })).sort((a, b) => {
    if (a.v === null || b.v === null) return a.v === b.v ? a.i - b.i : a.v === null ? 1 : -1;
    const c = typeof a.v === "number" && typeof b.v === "number" ? a.v - b.v : String(a.v).localeCompare(String(b.v));
    return c === 0 ? a.i - b.i : q.order === "asc" ? c : -c;
  }).map((x) => x.r) : kept;
  const per = spec.perPage ?? PER_PAGE;
  const pages = Math.max(1, Math.ceil(ordered.length / per));
  const page = Math.min(q.page, pages);
  return { total: ordered.length, rows: ordered.slice((page - 1) * per, page * per), pages, page };
}

/** A link to this table with the query changed: defaults left out, so every address is canonical and shareable. */
export function queryHref<R>(base: string, q: TableQuery, spec: QuerySpec<R>, change: Partial<Omit<TableQuery, "filters">> & { filters?: Record<string, string | null> } = {}): string {
  const x = { ...q, ...change, filters: { ...q.filters } };
  for (const [k, v] of Object.entries(change.filters ?? {})) { if (v === null || v === "") delete x.filters[k]; else x.filters[k] = v; }
  const p = new URLSearchParams();
  if (x.q) p.set("q", x.q);
  for (const f of spec.filters) if (x.filters[f.name]) p.set(f.name, x.filters[f.name]!);
  const sort = spec.sorts.find((s) => s.key === x.sort);
  if (x.sort !== spec.defaultSort) p.set("sort", x.sort);
  if (x.order !== (sort?.first ?? "desc")) p.set("order", x.order);
  if (x.page > 1) p.set("page", String(x.page));
  const s = p.toString();
  return s ? `${base}?${s}` : base;
}

export interface Column<R> {
  /** A sort key from the spec, when the heading sorts. */
  sort?: string;
  label: string;
  /** Says what the column is, as the heading's title. */
  title?: string;
  cell: (r: R) => string;
  /** "num" right-aligns and uses tabular figures; "main" is the column a row is about (on a phone it leads the block). */
  kind?: "num" | "main" | "st";
  /** On a phone: shown with its label (default), or hidden. */
  phone?: "show" | "hide";
  /** Keep the cell on one line (ids, dates, short codes). */
  nowrap?: boolean;
}

/** The search and filter form for a table, and the active filters as pills that remove themselves. Submits to `base` by GET. */
export function queryForm<R>(o: { base: string; spec: QuerySpec<R>; q: TableQuery; noun: [string, string]; searchLabel?: string }): string {
  const hidden = `${o.q.sort !== o.spec.defaultSort ? `<input type="hidden" name="sort" value="${esc(o.q.sort)}">` : ""}${o.q.order !== (o.spec.sorts.find((s) => s.key === o.q.sort)?.first ?? "desc") ? `<input type="hidden" name="order" value="${esc(o.q.order)}">` : ""}`;
  const selects = o.spec.filters.map((f) => `<label>${esc(f.label)}<select name="${esc(f.name)}"><option value="">${esc(f.any ?? "Any")}</option>${f.options.map(([v, l]) => `<option value="${esc(v)}"${o.q.filters[f.name] === v ? " selected" : ""}>${esc(l)}</option>`).join("")}</select></label>`).join("");
  const active = !!o.q.q || Object.keys(o.q.filters).length > 0;
  const form = `<form class="tq" method="get" action="${esc(o.base)}" role="search" aria-label="Search and filter ${esc(o.noun[1])}">
<label class="q">Search<input type="search" name="q" value="${esc(o.q.q)}" placeholder="${esc(o.searchLabel ?? `Search ${o.noun[1]}`)}" maxlength="${MAX_Q}"></label>
${selects}${hidden}<button class="btn" type="submit">Apply</button>${active ? `<a class="reset" href="${esc(queryHref(o.base, o.q, o.spec, { q: "", page: 1, filters: Object.fromEntries(Object.keys(o.q.filters).map((k) => [k, null])) }))}">Clear</a>` : ""}
</form>`;
  const pills = [
    ...(o.q.q ? [`<a class="pill" href="${esc(queryHref(o.base, o.q, o.spec, { q: "", page: 1 }))}" aria-label="Remove the search for ${esc(o.q.q)}">“${esc(o.q.q)}” <span class="x" aria-hidden="true">×</span></a>`] : []),
    ...o.spec.filters.filter((f) => o.q.filters[f.name]).map((f) => {
      const label = f.options.find(([v]) => v === o.q.filters[f.name])?.[1] ?? o.q.filters[f.name]!;
      return `<a class="pill" href="${esc(queryHref(o.base, o.q, o.spec, { page: 1, filters: { [f.name]: null } }))}" aria-label="Remove the filter ${esc(f.label)}: ${esc(label)}">${esc(f.label)}: ${esc(label)} <span class="x" aria-hidden="true">×</span></a>`;
    }),
  ];
  return `${form}${pills.length ? `<p class="pills">${pills.join("")}</p>` : ""}`;
}

/**
 * The table, with its search and filter form, the active filters as pills, a count, sortable headings and the pager.
 * `base` is the page's own path (the form submits to it). With `search: false` the form is left out (a short table, or a
 * page that puts one form above several tables).
 */
export function catalogue<R>(o: {
  id: string; base: string; spec: QuerySpec<R>; q: TableQuery; columns: ReadonlyArray<Column<R>>; rows: readonly R[];
  total: number; pages: number; page: number; noun: [string, string]; searchLabel?: string; search?: boolean; empty?: string; caption?: string;
}): string {
  const n = (x: number) => x.toLocaleString("en-GB");
  const per = o.spec.perPage ?? PER_PAGE;
  const from = o.total ? (o.page - 1) * per + 1 : 0;
  const to = Math.min(o.total, o.page * per);
  const filtered = !!o.q.q || Object.keys(o.q.filters).length > 0;
  const count = `<p class="count" role="status">${o.total === 1 ? `1 ${esc(o.noun[0])}` : `${n(o.total)} ${esc(o.noun[1])}`}${o.pages > 1 ? `, showing ${n(from)}–${n(to)}` : ""}</p>`;
  const head = o.columns.map((c) => {
    const cls = c.kind === "num" ? ' class="num"' : "";
    const title = c.title ? ` title="${esc(c.title)}"` : "";
    if (!c.sort) return `<th scope="col"${cls}${title}><span>${esc(c.label)}</span></th>`;
    const active = o.q.sort === c.sort;
    const spec = o.spec.sorts.find((s) => s.key === c.sort);
    const next = active ? (o.q.order === "desc" ? "asc" : "desc") : spec?.first ?? "desc";
    const sorted = active ? ` aria-sort="${o.q.order === "desc" ? "descending" : "ascending"}"` : "";
    return `<th scope="col"${cls}${title}${sorted}><a href="${esc(queryHref(o.base, o.q, o.spec, { sort: c.sort, order: next, page: 1 }))}">${esc(c.label)}${active ? `<span class="dir" aria-hidden="true">${o.q.order === "desc" ? "▼" : "▲"}</span>` : ""}</a></th>`;
  }).join("");
  const body = o.rows.map((r) => `<tr>${o.columns.map((c) => cellOf(c, r)).join("")}</tr>`).join("");
  const table = o.rows.length
    ? `<div class="ledger-scroll"><table class="ledger" id="${esc(o.id)}">${o.caption ? `<caption class="sr">${esc(o.caption)}</caption>` : ""}<thead><tr>${head}</tr></thead><tbody>${body}</tbody></table></div>`
    : `<p class="empty">${esc(filtered ? `No ${o.noun[1]} match. Clear a filter or search for something else.` : o.empty ?? `No ${o.noun[1]} yet.`)}</p>`;
  const pager = o.pages > 1 ? `<nav class="pager" aria-label="Pages of ${esc(o.noun[1])}">${o.page > 1 ? `<a href="${esc(queryHref(o.base, o.q, o.spec, { page: o.page - 1 }))}" rel="prev">Previous</a>` : "<span></span>"}<span>Page ${n(o.page)} of ${n(o.pages)}</span>${o.page < o.pages ? `<a href="${esc(queryHref(o.base, o.q, o.spec, { page: o.page + 1 }))}" rel="next">Next</a>` : "<span></span>"}</nav>` : "";
  return `<div class="catalogue">${o.search !== false ? queryForm(o) : ""}${o.rows.length || filtered ? count : ""}${table}${pager}</div>`;
}

/** One cell: its kind as a class (and nowrap), labelled for the phone's stacked layout unless it is the row's main cell. */
function cellOf<R>(c: Omit<Column<R>, "sort">, r: R): string {
  const cls = [c.kind, c.nowrap ? "nw" : ""].filter(Boolean).join(" ");
  return `<td${cls ? ` class="${cls}"` : ""}${c.kind !== "main" ? ` data-label="${esc(c.label)}"` : ""}${c.phone === "hide" ? ' data-phone="hide"' : ""}>${c.cell(r)}</td>`;
}

/** A plain table in the same style, for short lists that need neither search nor sorting (a claim's receipts, an agent's links). */
export function simpleTable<R>(o: { columns: ReadonlyArray<Omit<Column<R>, "sort">>; rows: readonly R[]; caption?: string; empty?: string }): string {
  if (!o.rows.length) return o.empty ? `<p class="small">${esc(o.empty)}</p>` : "";
  const head = o.columns.map((c) => `<th scope="col"${c.kind === "num" ? ' class="num"' : ""}${c.title ? ` title="${esc(c.title)}"` : ""}><span>${esc(c.label)}</span></th>`).join("");
  const body = o.rows.map((r) => `<tr>${o.columns.map((c) => cellOf(c, r)).join("")}</tr>`).join("");
  return `<div class="ledger-scroll"><table class="ledger">${o.caption ? `<caption class="sr">${esc(o.caption)}</caption>` : ""}<thead><tr>${head}</tr></thead><tbody>${body}</tbody></table></div>`;
}
