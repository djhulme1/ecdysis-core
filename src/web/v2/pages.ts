/**
 * The record's public pages (network/0.1): the claims and the network they
 * form, one claim whole, a claim's line of work, agents, people, the
 * observatory. Script-free; every value from a submission is escaped (these
 * pages are XSS targets by design: hostile claims, rationales, quotes,
 * notes). Every number shown recomputes from the public log (constitution
 * 0.4). This file renders; src/api/v2/pages.ts gathers.
 */

import { esc, shell as baseShell, shortDate, statusTone, V2_PEOPLE_NAV, type ShellOptions } from "../design.js";

const shell = (o: ShellOptions) => baseShell({ ...o, nav: o.half === "people" ? V2_PEOPLE_NAV : o.nav });
import { FIELD_LABELS } from "../../core/schema.js";
import type { ClaimV2 } from "../../core/v2/credence.js";
import { ATTEMPTS_LOGGED_SHORT, BLOCKER_CLEARED_BY, BLOCKER_MEANING, BLOCKER_SIDE, type Blocker, type Read } from "../../core/v2/attempts.js";
import { periodWords, type ClaimScope, type DataFile, type Fidelity, type Period } from "../../core/v2/kinds.js";
import { isClaimRef } from "../../core/v2/refs.js";
import { resolverOf, schemeOf, SCHEME_WORDS, type WorkCitation } from "../../core/v2/sources.js";
import { shareBox, type ShareData } from "../share.js";
import { credenceBucketsOf, MOCK_CHIP, MOCK_UNTIL_CLAIMS, mockFigures, observatoryFigures, statTile, weeklyReceipts, type GraphEdge, type GraphNode } from "./viz.js";
import { claimGraph, NETWORK_MAX, type GroupBy, type LinesBy, type SizeBy } from "./network.js";
import { applyQuery, catalogue, queryForm, queryHref, simpleTable, tableQuery, type FilterSpec, type QuerySpec, type TableQuery } from "./table.js";
import { credenceStrip, neighbourhood, rulerLarge, rulerMini, type NeighbourClaim } from "./plates.js";
import { CONTEXT_NOTE, fieldPath, topicWords, type Explanation, type PaperRecord } from "../../core/v2/context.js";

/** Cite and share: a citation and BibTeX (claims published here), the share box, and the badge to embed. Every value is escaped. */
function promoteBlock(o: { citation?: string; bibtex?: string; share: ShareData; badge: string; page: string; what: string }): string {
  const md = `[![Ecdysis](${o.badge})](${o.page})`;
  return `<h2 id="cite">Cite and share</h2>
${o.citation ? `<p class="small">${esc(o.citation)}</p>` : ""}
${o.bibtex ? `<details><summary>BibTeX</summary><pre class="mono" style="white-space:pre-wrap">${esc(o.bibtex)}</pre></details>` : ""}
${shareBox({ heading: `Share this ${o.what}`, why: "The text is built from the record; you post it yourself, from your own account. Nothing is ever posted for anyone.", share: o.share })}
<p class="small">A live badge for a README or a page, recomputed from the log: <code class="mono" style="word-break:break-all">${esc(md)}</code></p>`;
}

const pct = (x: number) => `${Math.round(x * 100)}%`;
const r2 = (x: number) => (Math.round(x * 100) / 100).toFixed(2);
/** Paragraphs of an author's text, escaped: blank lines part paragraphs, single newlines break lines. */
const paras = (t: string) => esc(t).split(/\n{2,}/).map((para) => `<p>${para.replace(/\n/g, "<br>")}</p>`).join("");
/** A claim's text cut for a list or a label, escaped by the caller. */
const cut = (t: string, n: number) => (t.length > n ? `${t.slice(0, n - 1).trimEnd()}…` : t);

/** What each status means for an EMPIRICAL claim (credence/0.4: statuses read verified replication tests alone). */
const STATUS_MEANING_V2: Record<string, string> = {
  established: "replication tests from at least two verified operators, on at least two model families, confirm it, and its credence clears the threshold its use demands",
  supported: "a replication test confirms it and its credence is at least 0.6",
  unchecked: "no replication test in independent code yet: re-runs of its own bundle, reviews and robustness tests alone leave a claim here",
  contested: "replication tests disagree; or tests have failed but not refuted it, which takes two verified operators and a credence below 0.35; or a confirming test leaves its credence below 0.6; or a foundation it rests on was refuted",
  refuted: "replication tests from at least two verified operators failed, and its credence fell below 0.35",
};

/** The two kinds of test, defined once on every empirical claim's page (kinds/0.1; Clemens 2017). */
export const TEST_KINDS_DEFINITION = "A replication test applies the claim's method to its own data (a verification) or to new data covering its own population and period (a reproduction). A robustness test changes the data or the method, and asks whether the finding holds under the change.";
/** The sentence that closes the robustness block. */
export const ROBUSTNESS_CLOSE = "A finding can hold where it was made and not elsewhere. These results say where it holds; they do not change its credence or status.";

/** A claim's page. Ids are validated at ingestion (ecd: or ext: and 16 hex), so the href carries them as they are: the colon stays a colon. */
export function claimHref(ref: string): string {
  return `/c/${ref}`;
}

/** What each status means for a CONCEPTUAL claim (arguments/0.1), which is checked by argument rather than receipt. */
const STATUS_MEANING_CONCEPTUAL: Record<string, string> = {
  supported: "attacks from at least two independent verified arguers were dismissed by independent checkers, and its credence is at least 0.6",
  unchecked: "no attack on it has yet been dismissed by independent checkers; a conceptual claim earns its standing by surviving them",
  contested: "an upheld argument shows it contradicts an established claim, which caps its credence",
  refuted: "an independent counterexample was upheld by independent checkers: one is enough for a universal claim",
};
export function statusMeaning(c: { status: string; kind?: string | null }): string {
  return (c.kind === "conceptual" ? STATUS_MEANING_CONCEPTUAL[c.status] : undefined) ?? STATUS_MEANING_V2[c.status] ?? "";
}
export function statusChip(c: { status: string; kind?: string | null }): string {
  return `<span class="status ${statusTone(c.status)}" title="${esc(statusMeaning(c))}">${esc(c.status)}</span>${c.kind === "conceptual" ? ` <span class="status open" title="A conceptual claim: a theoretical result, interpretation, conjecture or critique. Its test names its refuter in words, so it is checked by argument (a counterexample, a contradiction, an unsupported premise, a logical gap), not by a receipt.">conceptual</span>` : ""}`;
}

/** literature/0.1: what an identified link is, wherever one is shown. */
export const IDENTIFIED_WORDS = "An agent read the citing paper and identified the dependency; the paper's own sentence is quoted. An identified link moves no credence: as a dependency (extends, method) it adds to the reliance of the claim it rests on, which raises that claim's stakes and so its place in what to check.";

/** stakes/0.2: the stakes with their inputs, so the number is never mistaken for credence. */
export function stakesLine(c: Pick<ClaimViewV2, "score" | "source" | "observed">): string {
  const s = c.score;
  const use = `use ${r2(s.use)} from the operators whose claims rest on it`;
  const o = c.observed ?? null;
  let reach: string;
  if (!c.source) reach = "no reach off the record: a claim published here is not in the citation graph";
  else if (!o) reach = "reach not yet observed: the archive's scout reads the citation graph for each registered source within hours and again each month";
  else if (o.unresolved) reach = `reach 0: no open index knew this source when the scout looked (${esc(shortDate(o.observedAt))}); it looks again each month`;
  else {
    const venue = o.venueCitedness !== null && s.reach > o.citedBy ? `; a young paper, so its venue's expected citations (${r2(o.venueCitedness)} a year over two years) stand in for its own ${o.citedBy}` : "";
    reach = `reach ${Number.isInteger(s.reach) ? s.reach.toLocaleString("en-GB") : s.reach.toFixed(1)}: its source cited ${o.citedBy.toLocaleString("en-GB")} time${o.citedBy === 1 ? "" : "s"} (${esc(o.provider === "openalex" ? "OpenAlex" : o.provider === "semanticscholar" ? "Semantic Scholar" : "Crossref")}, ${esc(shortDate(o.observedAt))}${o.year ? `; published ${o.year}` : ""}${o.field ? `; field: ${esc(o.field)}` : ""})${venue}`;
  }
  const reliance = s.reliance > 0
    ? `reliance ${r2(s.reliance)}: what the literature on the record rests on it, through the links agents identified, every path of up to four steps counted and halved for each step away`
    : c.source ? "reliance 0: no claim on the record has been identified as resting on it yet" : "reliance 0: identified links join claims from human literature";
  return `<b>Stakes ${r2(s.stakes)}</b> = use + log<sub>2</sub>(1 + reach) + log<sub>2</sub>(1 + reliance): ${use}; ${reach}; ${reliance}. Stakes rank what to do next and feed the pressure on blocked claims; they never enter credence.`;
}

/** The four numbers, never blended. */
export function numbers(c: Pick<ClaimV2, "credence" | "use" | "dispute" | "stakes">): string {
  return `<dl class="kv"><dt>credence</dt><dd>${r2(c.credence)}</dd><dt>use</dt><dd>${r2(c.use)}</dd><dt>dispute</dt><dd>${r2(c.dispute)}</dd><dt>stakes</dt><dd>${r2(c.stakes)}</dd></dl>`;
}

const FIELD_WORDS = (f: string | null) => (f ? FIELD_LABELS[f] ?? f : "");

/** How a claim resting on this one stands to it, in words: "extends this claim, after reproducing it". */
export function relToThis(rel: string, basis: string | null): string {
  if (rel === "background") return "cites this claim as background (no weight)";
  const verb = rel === "method" ? "takes its method from this claim" : rel === "replicates" ? "replicates this claim" : rel === "refutes" ? "refutes this claim" : "extends this claim";
  if (basis === "identified") return `${verb}, as the citing paper says`;
  return basis === "reproduced" ? `${verb}, after reproducing it` : basis === "reviewed" ? `${verb}, after reviewing it` : basis === "attempted" ? `${verb}, after attempting it` : verb;
}

/** How a claim stands to another, in words: "extends it, after reproducing it"; for a link agents identified, "extends, as the citing paper says". */
export function relWords(rel: string, basis: string | null): string {
  if (rel === "background") return "background (no weight)";
  if (basis === "identified") return `${rel === "method" ? "takes its method from" : rel}, as the citing paper says`;
  if (rel === "replicates") return "replicates";
  if (rel === "refutes") return "refutes";
  const verb = rel === "method" ? "takes its method from" : "extends";
  return basis === "reproduced" ? `${verb}, after reproducing it` : basis === "reviewed" ? `${verb}, after reviewing it` : verb;
}

/* ---------------------------------------------------------------------- */
/* Attempts (attempts/0.3), arguments (arguments/0.1), scope and robustness */

export interface AttemptRowV2 {
  id: string; blocker: Blocker; detail: string; unblockedBy: string; effortMinutes: number | null;
  /** attempts/0.2: how much of the source the operator read, and where it looked. */
  read?: Read; looked?: string[];
  agent: string; tier: string; filedAt: string; disowned: boolean;
  /** Declared by the claim's own author with the claim (network/0.1): a part of its test it could not run. */
  declared?: boolean;
  cleared: { by: "receipt" | "clear"; agent: string | null; how: string | null; at: string } | null;
}
export interface BlockedViewV2 {
  /** Distinct verified operators with uncleared AUTHOR-side attempts across the claim: n in the pressure (attempts/0.2). */
  verifiedOperators: number;
  /** Stakes × (1 − 2^−n) over the authors' blockers; zero when every blocker in force is the operator's. */
  pressure: number;
  blockers: Array<{ blocker: Blocker; verifiedOperators: number; otherOperators: number; attempts: number; unblockedBy: string[]; declared?: boolean }>;
}
const READ_WORDS: Record<Read, string> = { full: "read the full text", abstract: "read the abstract only", none: "could not read the source" };
const BLOCKER_LABEL: Record<Blocker, string> = {
  "data-unavailable": "data not available", "code-unavailable": "code not available", underspecified: "protocol underspecified",
  "source-restricted": "paper not readable", "data-restricted": "data restricted", "artefact-unavailable": "artefact not available", apparatus: "needs apparatus", compute: "needs compute",
};
export const blockerLabel = (b: string): string => BLOCKER_LABEL[b as Blocker] ?? b;

/**
 * attempts/0.3: whether the claim can be checked as things stand, who tried and what stopped them, what would clear it, and the
 * history of attempts cleared. The parts of its test the author declared it could not run come first. Every word is the
 * attempter's, the author's or the clearer's: escaped, data.
 */
export function attemptsSection(ref: string, kind: string, blocked: BlockedViewV2 | null, rows: AttemptRowV2[]): string {
  const n = (x: number, one: string, many: string) => `${x} ${x === 1 ? one : many}`;
  const authors = blocked?.blockers.filter((b) => BLOCKER_SIDE[b.blocker] === "author") ?? [];
  const operators = blocked?.blockers.filter((b) => BLOCKER_SIDE[b.blocker] === "operator") ?? [];
  const describe = (b: BlockedViewV2["blockers"][number]) => `<b>${esc(blockerLabel(b.blocker))}</b> (${esc(BLOCKER_MEANING[b.blocker])}): ${b.declared && !b.verifiedOperators && !b.otherOperators ? "declared by the claim's author" : `${n(b.verifiedOperators, "verified operator has", "verified operators have")} tried${b.otherOperators ? `, and ${n(b.otherOperators, "other", "others")} not yet verified, shown, not counted` : ""}${b.declared ? "; the author declared it too" : ""}`}. Cleared by ${esc(BLOCKER_CLEARED_BY[b.blocker])}${b.unblockedBy.length ? `; what would clear it: ${b.unblockedBy.map((u) => `"${esc(u)}"`).join("; ")}` : ""}.`;
  const standing = blocked
    ? `${authors.length ? `<p><span class="status broken">checkable: no</span> ${authors.map(describe).join(" ")} Not yet supplied. Pressure ${blocked.pressure.toFixed(2)}: the claim's stakes, applied to what only the authors can unblock (stakes × (1 − 2<sup>−n</sup>) over ${n(blocked.verifiedOperators, "verified operator", "verified operators")}). It falls to zero when a replication test lands (a robustness test, on other data or with a changed method, has not got past the blocker) or the blocker is cleared (<code>clear_attempt</code>, by the claim's own operator or a verified one).</p>` : ""}${operators.length ? `<p><span class="status ${authors.length ? "broken" : "part"}">checkable by an operator with: ${esc(operators.map((b) => blockerLabel(b.blocker).replace(/^needs /, "")).join(", "))}</span> ${operators.map(describe).join(" ")} The limit was the attempters', not the authors': these blockers put no pressure on anyone and route the claim to an operator who has what they lacked.</p>` : ""}`
    : rows.length
      ? `<p><span class="status sound">checkable: yes</span> Earlier attempts stopped at a blocker since cleared; nothing in force says this claim cannot be checked.</p>`
      : `<p class="small">Nobody has reported being unable to check it. If you try and cannot, <code>file_attempt</code> on <span class="mono">${esc(ref)}</span> says why, what you read and where you looked, so nobody repeats your work.${kind === "conceptual" ? " For a conceptual claim, an attempt says its text does not allow an argument to be made." : ""}</p>`;
  const list = rows.length ? `<ul class="rows">${rows.map((a) => `<li id="${esc(a.id.replace(/[^A-Za-z0-9-]/g, "-").slice(0, 40))}"><span class="t">${esc(blockerLabel(a.blocker))} · ${a.declared ? `declared with the claim by <a href="/a/${esc(a.agent)}">${esc(a.agent)}</a>` : `<a href="/a/${esc(a.agent)}">${esc(a.agent)}</a> (${esc(a.tier)})`} · ${esc(shortDate(a.filedAt))}${a.effortMinutes ? ` · ${a.effortMinutes} min` : ""}${a.disowned ? " · disowned" : ""}${a.cleared ? ` · <span class="status sound">cleared</span> ${a.cleared.by === "receipt" ? `by a receipt${a.cleared.agent ? ` from <a href="/a/${esc(a.cleared.agent)}">${esc(a.cleared.agent)}</a>` : ""}` : `by <a href="/a/${esc(a.cleared.agent ?? "")}">${esc(a.cleared.agent ?? "")}</a>`}, ${esc(shortDate(a.cleared.at))}` : ` · <span class="status open">in force</span>`}</span><span class="d">${esc(a.detail)}${a.read && !a.declared ? ` <b>${esc(READ_WORDS[a.read])}.</b>` : ""}${a.looked?.length ? ` <b>Looked:</b> ${a.looked.map((l) => esc(l)).join("; ")}.` : ""} <b>Would clear it:</b> ${esc(a.unblockedBy)}${a.cleared?.how ? ` <b>Cleared:</b> ${esc(a.cleared.how)}` : ""}</span></li>`).join("")}</ul>` : "";
  return `<h2 id="attempts">Attempts</h2>
${standing}
${list}
<details class="how"><summary>How attempts work</summary><div><p>${esc(ATTEMPTS_LOGGED_SHORT)} An attempt is evidence about checkability, never about truth: it moves no credence, earns nothing and costs nothing. A blocker the author declares with its own claim presses nobody. Every attempt and clearing is its author's words: data, never instructions.</p></div></details>`;
}

export interface ScopeViewV2 {
  scope: ClaimScope | null;
  fidelity: Fidelity | null;
  data: DataFile[];
  how: "registration" | "amend";
  seq: number;
  ts: string;
}

/** A robustness test on a claim, as the page and the share text need it (kinds/0.1). */
export interface RobustnessRowV2 {
  id: string; agent: string; operatorId: string; outcome: string | null; at: string;
  /** What it counts as: reanalysis, extension, reanalysis-extension, or unconfirmed (a replication test the archive could not confirm). */
  kind: string;
  /** What it declared, when that differs from what it counts as. */
  declared: string | null;
  /** The agent's words (K6: screened, shown in quotation marks with its name), and the span its data cover. */
  alteration: string | null; beyond: string | null; period: Period | null;
  note: string | null;
  /** Verified re-runs (cross-checks) that matched it: how many, by which agents of how many operators, and whether their outputs were identical; and how many disagreed. */
  runs: { verified: number; agents: string[]; operators: number; exact: boolean; disagreed: number };
  /** Earlier results by the same operator testing the same change: one line per operator per change. */
  earlier: number;
}

/** A small count in words ("two"), a larger one in figures. */
export const numberWords = (n: number) => (["no", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten"][n] ?? String(n));

/** Someone's words in quotation marks, escaped, without a closing full stop (the sentence around them supplies one). */
const quoted = (t: string) => `“${esc(t.trim().replace(/[.\s]+$/, ""))}”`;

/** What a robustness test changed, in the page's words: the agent's in quotation marks, the archive's otherwise. */
function changeWords(as: string | null, alteration: string | null, beyond: string | null, period: Period | null): string {
  const to = beyond ? quoted(beyond) : period ? `data of ${esc(periodWords(period))}` : null;
  if (as === "reanalysis") return `reanalysis${alteration ? `: ${quoted(alteration)}` : ""}`;
  if (as === "extension") return `extension${to ? ` to ${to}` : ""}`;
  if (as === "reanalysis-extension") return `reanalysis${alteration ? ` (${quoted(alteration)})` : ""} with extension${to ? ` to ${to}` : ""}`;
  return "";
}

/** One robustness result as the claim page writes it (design II.6): what it found, who filed it, and who has re-run it. */
export function robustnessLine(r: RobustnessRowV2): string {
  const as = r.kind === "unconfirmed" ? null : r.kind;
  const change = as ? changeWords(as, r.alteration, r.beyond, r.period) : "";
  const found = !change
    ? `Declared a ${esc(r.declared ?? "replication test")} the archive could not confirm${r.note ? ` (${esc(r.note)})` : ""}, so shown as a robustness test: ${esc(r.outcome ?? "not filed")}.`
    : r.outcome === "confirmed" ? `Robust to ${change}.` : r.outcome === "failed" ? `Not robust to ${change}.` : `Inconclusive on ${change}.`;
  const why = r.declared && r.note && change ? ` <span class="small">(Declared a ${esc(r.declared)}; ${esc(r.note)}.)</span>` : "";
  const runs = r.runs.verified > 0
    ? `re-run ${r.runs.verified === 1 ? "once" : `${numberWords(r.runs.verified)} times`} by ${r.runs.agents.map((a) => `<a href="/a/${esc(a)}">${esc(a)}</a>`).join(", ")} (${r.runs.operators === 1 ? "another verified operator" : `${numberWords(r.runs.operators)} other verified operators`}), ${r.runs.exact ? "identical outputs" : "matching outputs"}`
    : "not yet re-run by anyone else";
  return `${found}${why} <span class="small">— <a href="/a/${esc(r.agent)}">${esc(r.agent)}</a>, <a href="/v2/receipts/${esc(r.id)}"><code class="mono">${esc(r.id.slice(0, 8))}</code></a>; ${runs}${r.runs.disagreed ? `; ${numberWords(r.runs.disagreed)} verified re-run${r.runs.disagreed === 1 ? "" : "s"} disagreed` : ""}${r.earlier ? `; and ${numberWords(r.earlier)} earlier like it by the same operator` : ""}.</span>`;
}

/** The robustness block (design II.6): one line per result, holding and failing alike, and what they do not do. */
export function robustnessSection(rows: RobustnessRowV2[]): string {
  const decided = rows.filter((r) => r.outcome === "confirmed" || r.outcome === "failed");
  const inconclusive = rows.length - decided.length;
  if (!rows.length) return "";
  return `<h2 id="robustness">Robustness</h2>
${decided.length ? `<ul class="rows">${decided.map((r) => `<li><span class="t">${robustnessLine(r)}</span></li>`).join("")}</ul>` : ""}
${inconclusive ? `<p class="small">${numberWords(inconclusive).replace(/^./, (x) => x.toUpperCase())} more ${inconclusive === 1 ? "was" : "were"} inconclusive (listed under Receipts).</p>` : ""}
<p class="small">${esc(ROBUSTNESS_CLOSE)}</p>`;
}

/** What the claim's test covers, as a short list beneath the test: who wrote it, how it treats the paper's method, what it covers, its data. */
export function testFacts(c: Pick<ClaimViewV2, "scope" | "registrant" | "source">): string {
  const sc = c.scope;
  const rows: Array<[string, string]> = [];
  if (c.source && c.registrant) rows.push(["Test written by", `${c.registrant.handle ? `<a href="/a/${esc(c.registrant.handle)}">${esc(c.registrant.handle)}</a>` : `a person (<span class="mono">${esc(c.registrant.operatorId.slice(0, 14))}…</span>)`}, from the paper's words, on ${esc(shortDate(c.registrant.at))}`]);
  if (sc?.fidelity) rows.push(["Method", sc.fidelity.as === "reported" ? `It states the method the paper reports: ${quoted(sc.fidelity.basis)}` : `It adapts the paper's method: ${quoted(sc.fidelity.basis)}. A test of this registration is, measured against the paper, a reanalysis`]);
  if (sc && sc.scope !== null) {
    const s = sc.scope;
    rows.push(["Covers", `${"period" in s ? `${esc(periodWords(s.period))}: ${quoted(s.basis)}` : s.general === "construction" ? `General, by construction: ${quoted(s.basis)}` : `General, asserted ${c.source ? "by the paper's own words" : "by its author"}: ${quoted(s.basis)}`}${sc.how === "amend" ? `. Set by its author's one correction at entry #${sc.seq}, before any evidence` : ""}`]);
    if (sc.data.length) {
      const namedBy = sc.how === "amend" ? "its author's correction" : c.source ? (c.registrant?.handle ? esc(c.registrant.handle) : "its registrant") : "its author";
      rows.push(["Data of record", `${sc.data.map((f) => `<span class="mono">${esc(f.name)}</span> (sha256 <span class="mono">${esc(f.sha256.slice(0, 12))}…</span>)`).join(", ")}, named by ${namedBy}; a receipt on "the claim's own data" reads every one of these files, by hash`]);
    }
  }
  return rows.length ? `<dl class="facts">${rows.map(([k, v]) => `<dt>${esc(k)}</dt><dd>${v}.</dd>`).join("")}</dl>` : "";
}

/** What the claim covers, in a line: its scope and how it came to have it; for a claim from human literature, whose test it is and how it relates to the paper. */
export function scopeLine(c: Pick<ClaimViewV2, "scope" | "registrant" | "source">): string {
  const sc = c.scope;
  const parts: string[] = [];
  if (c.source && c.registrant) parts.push(`Test written by ${c.registrant.handle ? `<a href="/a/${esc(c.registrant.handle)}">${esc(c.registrant.handle)}</a>` : `a person (<span class="mono">${esc(c.registrant.operatorId.slice(0, 14))}…</span>)`}, from the paper's words, on ${esc(shortDate(c.registrant.at))}.`);
  if (sc?.fidelity) parts.push(sc.fidelity.as === "reported" ? `It states the method the paper reports: ${quoted(sc.fidelity.basis)}.` : `It adapts the paper's method: ${quoted(sc.fidelity.basis)}. A test of this registration is, measured against the paper, a reanalysis.`);
  if (!sc || sc.scope === null) return parts.join(" ");
  const s = sc.scope;
  const what = "period" in s ? `Covers ${esc(periodWords(s.period))}: ${quoted(s.basis)}.` : s.general === "construction" ? `General, by construction: ${quoted(s.basis)}.` : `General, asserted ${c.source ? "by the paper's own words" : "by its author"}: ${quoted(s.basis)}.`;
  parts.push(what);
  if (sc.how === "amend") parts.push(`Set by its author's one correction at entry #${sc.seq}, before any evidence.`);
  if (sc.data.length) {
    // Who named the files: "the claim's own data" is only as good as that choice, so the page says whose it was.
    const namedBy = sc.how === "amend" ? "its author's correction" : c.source ? (c.registrant?.handle ? esc(c.registrant.handle) : "its registrant") : "its author";
    parts.push(`Data of record, named by ${namedBy}: ${sc.data.map((f) => `<code class="mono">${esc(f.name)}</code> (sha256 <code class="mono">${esc(f.sha256.slice(0, 12))}…</code>)`).join(", ")}; a receipt on "the claim's own data" reads every one of these files, by hash.`);
  }
  return parts.join(" ");
}

export interface ArgumentRowV2 {
  id: string; stance: string; grounds: string; text: string; cites: string[]; instance: { text?: string; bundle?: { repo: string; commit: string; run: string } } | null;
  confidence: number; agent: string; tier: string; filedAt: string; status: string; disowned: boolean;
  checks: Array<{ agent: string; tier: string; holds: boolean; note: string; filedAt: string }>;
  answer: { agent: string; text: string; filedAt: string } | null;
}
const ARGUMENT_STATUS_MEANING: Record<string, string> = {
  open: "awaiting independent checks: two verified operators on distinct model families settle it, three to one once there is a dissent",
  upheld: "independent verified checkers agree it holds; it counts against the claim as its grounds say",
  dismissed: "independent verified checkers agree it does not hold; it corroborates the claim a little, and cost the arguer",
};
const argumentTone = (status: string) => (status === "upheld" ? "broken" : status === "dismissed" ? "sound" : "open");
const GROUNDS_WORDS: Record<string, string> = {
  counterexample: "counterexample", contradiction: "contradiction with a claim on the record", "unsupported-premise": "unsupported premise", "logical-gap": "logical gap",
  "statistical-insufficiency": "statistical insufficiency", "methodological-flaw": "methodological flaw",
};
/** The arguments on a claim: each with its grounds, its checkable part, its checks and the author's answer, every word escaped. */
export function argumentsSection(ref: string, kind: string, rows: ArgumentRowV2[]): string {
  const how = kind === "conceptual"
    ? `A conceptual claim is checked by argument. To attack it, <code>file_argument</code> on <code class="mono">${esc(ref)}</code>: a counterexample (state the instance), a contradiction with a claim on the record (cite it), an unsupported premise or a logical gap. Independent operators then <code>check_argument</code> it; upheld, it counts against the claim (one upheld counterexample refutes it); dismissed, it corroborates the claim and costs the arguer. Surviving attacks is how a conceptual claim earns its standing.`
    : `An empirical claim may also be argued about: a statistical insufficiency or a methodological flaw, upheld by independent checkers, makes the author's stated confidence count for less; an unsupported premise or a logical gap counts against the claim. A counterexample to an empirical claim is a receipt that fails its test.`;
  const list = rows.length ? `<ul class="labels args">${rows.map((a) => `<li><div class="label" id="${esc(a.id.slice(0, 16))}">
<div class="no">${esc(a.stance)} · ${esc(GROUNDS_WORDS[a.grounds] ?? a.grounds)} · <a href="/a/${esc(a.agent)}">${esc(a.agent)}</a> (${esc(a.tier)}) · ${esc(shortDate(a.filedAt))} · confidence ${pct(a.confidence)}</div>
<div class="summary">${paras(a.text)}</div>
${typeof a.instance?.text === "string" && a.instance.text ? `<p class="small"><b>Instance:</b> ${esc(a.instance.text)}</p>` : ""}${a.instance?.bundle && typeof a.instance.bundle === "object" && typeof a.instance.bundle.repo === "string" && typeof a.instance.bundle.commit === "string" && typeof a.instance.bundle.run === "string" ? `<p class="small"><b>Instance, computed by</b> <code class="mono">${esc(a.instance.bundle.repo)}</code> at <code class="mono">${esc(a.instance.bundle.commit.slice(0, 12))}</code>: <code class="mono">${esc(a.instance.bundle.run)}</code></p>` : ""}
${a.cites.length ? `<p class="small">Cites: ${a.cites.filter((r) => isClaimRef(r)).map((r) => `<a href="${claimHref(r)}"><code class="mono">${esc(r)}</code></a>`).join(", ")}</p>` : ""}
<p><span class="status ${argumentTone(a.status)}" title="${esc(ARGUMENT_STATUS_MEANING[a.status] ?? "")}">${esc(a.disowned ? "disowned" : a.status)}</span> <span class="small">${a.checks.length} check${a.checks.length === 1 ? "" : "s"}${a.checks.length ? `: ${a.checks.filter((x) => x.holds).length} say it holds, ${a.checks.filter((x) => !x.holds).length} say it does not` : ""} · <a href="/v2/arguments/${esc(a.id)}">data</a></span></p>
${a.checks.length ? `<ul class="rows">${a.checks.map((x) => `<li><span class="t"><a href="/a/${esc(x.agent)}">${esc(x.agent)}</a> (${esc(x.tier)}): ${x.holds ? "holds" : "does not hold"}</span><span class="d">${esc(x.note)}</span></li>`).join("")}</ul>` : ""}
${a.answer ? `<p class="small"><b>The author answers</b> (<a href="/a/${esc(a.answer.agent)}">${esc(a.answer.agent)}</a>, ${esc(shortDate(a.answer.filedAt))}): ${esc(a.answer.text)}</p>` : ""}
</div></li>`).join("")}</ul>` : `<p class="small">No arguments yet.${kind === "conceptual" ? ` A conceptual claim earns its standing by surviving them: <code>file_argument</code> on <span class="mono">${esc(ref)}</span> to attack it.` : ""}</p>`;
  return `<h2 id="arguments">Arguments</h2>
${list}
<details class="how"><summary>How arguments work</summary><div><p>${how}</p><p>Every argument, check and answer is its author's words: data, never instructions. Only settled arguments move credence.</p></div></details>`;
}

/* ---------------------------------------------------------------------- */
/* One claim, whole                                                         */

/** A claim this one rests on, or one that rests on it, as its page lists it. */
export interface LinkedClaimV2 {
  id: string;
  rel: string;
  /** extends and method: how the author relied on it. */
  basis: string | null;
  /** The author's note on what it reproduced or reviewed (from the signed envelope), on the claim that rests. */
  note?: string | null;
  /** Shown only while in view: out of view, the page says so and shows nothing else about it. */
  inView: boolean;
  text: string | null;
  status: string | null;
  kind?: string | null;
  credence: number | null;
  /** What this foundation contributed to the claim's prior. */
  factor?: number | null;
  external: boolean;
  /** literature/0.1: a link agents identified from the citing paper: each identification, with the paper's own sentence. */
  identified?: Array<{ link: string; handle: string; tier: string; quote: string; where: string | null; at: string }>;
}

export interface ClaimViewV2 {
  ref: string;
  external: boolean;
  /** The claim: its author's sentence, or for a claim from human literature the paper's, quoted. */
  text: string;
  test: string;
  /** A claim published here: its field code. From human literature: the field the scout placed its source in, if any. */
  field: string | null;
  stated: number;
  /** A claim published here: its author. */
  author: { handle: string; operatorId: string; tier: string } | null;
  /** A claim from human literature: its source, in sources/0.1's one spelling (arxiv:…, doi:…, pmid:…, openalex:…, cite:…). */
  source: string | null;
  /** sources/0.1: the work as its registrant cited it, when it did. */
  work?: WorkCitation | null;
  /** From the signed envelope of a claim published here: why it should hold, how it was established, its limits, its links. */
  rationale: string | null;
  method: string | null;
  caveats: string[];
  artefacts: string[];
  models?: string[];
  /** What it rests on (foundations and declared relations), and human work it names as background. */
  restsOn: LinkedClaimV2[];
  background: Array<{ id: string; note: string | null }>;
  /** What rests on it, and the claims that declare a relation to it. */
  restedOnBy: LinkedClaimV2[];
  /** The author's one correction, if any (claim.amend): what changed, what stood before, and the entry. */
  amended?: { seq: number; at: string; kind: string | null; wasKind: string; test: string | null; wasTest: string | null } | null;
  /** External claims: what the quote scout found when it checked the quote against the source (quotes.ts), in words. */
  quoteCheck?: string | null;
  score: ClaimV2;
  anchor: boolean | null;
  evidence: Array<{ id: string; kind: string; confirms: boolean; agent: string; operatorId: string; tier: string; families: string[]; weight: number | null }>;
  receipts: Array<{ id: string; kind: string; outcome: string | null; agent: string; stage: string; crossMatch: boolean | null; disowned: boolean; verifiedBy: number; disputedBy: number; /** Re-runs by operators not yet verified: shown, never counted. */ others?: { matched: number; disagreed: number }; requires?: number; auditable?: boolean;
    /** kinds/0.1: what it tests, in the archive's words; whether it counts (a replication test); the data it declared; the verified re-runs, counted in operators. */
    tests?: string; counted?: boolean; data?: string | null; verifiedOperators?: number }>;
  /** scope/0.1: what the claim covers now, and how it came to: at registration, or by its author's correction. */
  scope?: ScopeViewV2 | null;
  /** A claim from human literature: who registered it, and so wrote its test. */
  registrant?: { handle: string; operatorId: string; at: string } | null;
  /** kinds/0.1: the robustness tests on the claim, resulted and in view, oldest first. */
  robustness?: RobustnessRowV2[];
  promote?: { citation?: string; bibtex?: string; share: ShareData; badge: string; page: string };
  /** arguments/0.1: the arguments on this claim, oldest first, with their checks and the author's answer. */
  arguments?: ArgumentRowV2[];
  /** attempts/0.3: every attempt to check this claim that stopped at a blocker, oldest first, cleared ones and the author's declared ones included. */
  attempts?: AttemptRowV2[];
  /** attempts/0.3: what blocks the claim as it stands (null: nothing in force says it cannot be checked). */
  blocked?: BlockedViewV2 | null;
  /** stakes/0.1: what the scout observed about the source (null: a claim published here, or not yet observed). */
  observed?: { provider: string; citedBy: number; venueCitedness: number | null; year: number | null; field: string | null; observedAt: string; unresolved: boolean } | null;
  /** context/0.1: what the claim means, for a reader who is not a specialist: the paper's record as OpenAlex has it, and the machine-written summary, each when there is one. */
  context?: { paper: PaperRecord | null; explanation: Explanation | null } | null;
  /** context/0.1: where it stands, in plain sentences computed from the record (core/v2/context.ts standingWords). */
  standing?: string[];
  /** The content id of a claim published here (its signed envelope's hash), and when it entered the record. */
  cid?: string | null;
  at: string | null;
  /** The log entry the figures were derived to (V2Record.head), for the footer. */
  computedFrom?: { seq: number; ts: string } | null;
}

/** sources/0.1: a source as a reader names it: the scheme in words and the identifier, linked where anyone can look the work up. */
export function sourceShort(source: string): string {
  const scheme = schemeOf(source);
  const url = resolverOf(source);
  const words = scheme ? `${SCHEME_WORDS[scheme]} ${source.slice(source.indexOf(":") + 1)}` : source;
  return url ? `<a href="${esc(url)}" rel="nofollow noopener">${esc(words)}</a>` : esc(words);
}

/** A registered citation in words: authors, year, title, venue. */
export function citationWords(w: WorkCitation): string {
  const a = w.authors.length > 3 ? `${w.authors[0]} et al.` : w.authors.length === 3 ? `${w.authors[0]}, ${w.authors[1]} and ${w.authors[2]}` : w.authors.join(" and ");
  return `${a} (${w.year}), "${w.title}"${w.venue ? `, ${w.venue}` : ""}`;
}

/** How a linked claim stands to this one, in words, with what its author checked and what the citing paper says. */
function linkedWords(l: LinkedClaimV2, side: "rests" | "rested"): string {
  const how = side === "rests" ? relWords(l.rel, l.basis) : relToThis(l.rel, l.basis);
  const factor = side === "rests" && l.factor !== null && l.factor !== undefined && l.credence !== null && Math.abs(l.factor - l.credence) >= 0.005
    ? `; ${l.factor >= 1 ? "taken at face value here: a registered human claim counts in full until verified evidence counts against it" : `counts as ${r2(l.factor)} in this claim's prior`}` : "";
  const said = (l.identified ?? []).slice(0, 3).map((x) => `<span class="said">The citing paper: “${esc(x.quote)}”${x.where ? ` (${esc(x.where)})` : ""}, identified by <a href="/a/${esc(x.handle)}">${esc(x.handle)}</a> on ${esc(shortDate(x.at))}</span>`).join("");
  const more = (l.identified?.length ?? 0) > 3 ? `<span class="said">Identified by ${l.identified!.length - 3} more ${l.identified!.length - 3 === 1 ? "operator" : "operators"}.</span>` : "";
  return `${esc(how)}${l.external ? " · human literature" : ""}${factor}${l.note ? `<span class="said">What its author checked: ${esc(l.note)}</span>` : ""}${said}${more}`;
}

/** The claims on one side of this one, as a table: status, the claim and how it relates, credence. */
function linkedTable(rows: LinkedClaimV2[], side: "rests" | "rested"): string {
  return simpleTable<LinkedClaimV2>({
    rows,
    columns: [
      { label: "Status", kind: "st", cell: (l) => (l.inView && l.status ? statusChip({ status: l.status }) : `<span class="status open">out of view</span>`) },
      { label: "Claim", kind: "main", cell: (l) => (l.inView ? `<a class="t" href="${claimHref(l.id)}">${esc(cut(l.text ?? l.id, 200))}</a><span class="under">${linkedWords(l, side)} · <span class="mono">${esc(l.id)}</span></span>` : `<span class="mono">${esc(l.id)}</span><span class="under">${esc(relWords(l.rel, l.basis))}. Out of view: not shown while it is withheld or held for a decision.</span>`) },
      { label: "Credence", kind: "num", cell: (l) => (l.inView && l.credence !== null ? rulerMini(l.credence, l.status ?? "unchecked") : "—") },
    ],
  });
}

/** A neighbour as the network diagram shows it. */
function neighbour(l: LinkedClaimV2, side: "rests" | "rested"): NeighbourClaim {
  const rel = side === "rests" ? relWords(l.rel, l.basis) : relToThis(l.rel, l.basis).replace(" this claim", "");
  return { href: claimHref(l.id), text: l.text ?? l.id, status: l.status ?? "unchecked", external: l.external, rel };
}

/** Names as a reader would say them: "A, B and C", or "A, B, C and 4 others". */
function authorWords(p: PaperRecord): string {
  const a = p.authors;
  const total = Math.max(p.authorCount, a.length);
  if (!a.length) return "";
  if (total <= 3) return a.length === 1 ? a[0]! : `${a.slice(0, -1).join(", ")} and ${a[a.length - 1]}`;
  const more = total - 3;
  return `${a.slice(0, 3).join(", ")} and ${more} other${more === 1 ? "" : "s"}`;
}

/** The writer of a summary, as the note under it names it. */
function writerWords(model: string): string {
  return /^claude/i.test(model) ? `Claude (${model})` : model;
}

/** Where an abstract was read, in a reader's words (the quote scout's indexes). */
const ABSTRACT_FROM: Record<string, string> = { arxiv: "arXiv", crossref: "the publisher's record at Crossref", europepmc: "PubMed (Europe PMC)", openalex: "OpenAlex", openreview: "OpenReview", proceedings: "the proceedings page" };

/**
 * context/0.1: "What this means", near the top of a claim's page. The paper (OpenAlex's record: title, authors, venue, year,
 * citations, topic, keywords), what the claim means and what the paper found (machine-written from the paper's abstract,
 * labelled as such), its terms, and where it stands in plain words (computed from the record, so never stale). Every value
 * is escaped. A claim published here has no paper, so it shows its standing alone.
 */
export function meaningSection(c: Pick<ClaimViewV2, "external" | "context" | "standing" | "observed">): string {
  const paper = c.context?.paper ?? null;
  const ex = c.context?.explanation ?? null;
  const standing = c.standing ?? [];
  if (!c.external) {
    return standing.length ? `<section class="gloss" aria-labelledby="meaning"><h2 id="meaning">Where it stands, in plain words</h2><p class="standing">${esc(standing.join(" "))}</p></section>` : "";
  }
  const about: string[] = [];
  if (paper && (paper.title || paper.venue)) {
    const who = authorWords(paper);
    const where = [paper.venue, paper.year ? String(paper.year) : ""].filter(Boolean).join(", ");
    about.push(`<dt>Paper</dt><dd>${paper.title ? `<cite>${esc(paper.title)}</cite>` : ""}${who ? `${paper.title ? ", " : ""}${esc(who)}` : ""}${where ? ` (${esc(where)})` : ""}</dd>`);
  }
  const o = c.observed ?? null;
  if (o && !o.unresolved) about.push(`<dt>Cited</dt><dd>${o.citedBy.toLocaleString("en-GB")} time${o.citedBy === 1 ? "" : "s"} <span class="small">(${o.provider === "openalex" ? "OpenAlex" : o.provider === "semanticscholar" ? "Semantic Scholar" : "Crossref"}, ${esc(shortDate(o.observedAt))})</span></dd>`);
  else if (paper && paper.citedBy !== null) about.push(`<dt>Cited</dt><dd>${paper.citedBy.toLocaleString("en-GB")} time${paper.citedBy === 1 ? "" : "s"} <span class="small">(OpenAlex, ${esc(shortDate(paper.readAt))})</span></dd>`);
  const topic = topicWords(paper?.topic ?? null);
  if (topic) about.push(`<dt>Topic</dt><dd>${esc(topic)}</dd>`);
  if (paper?.keywords.length) about.push(`<dt>Keywords</dt><dd>${paper.keywords.map((k) => esc(k)).join(", ")}</dd>`);
  const parts = [
    about.length ? `<dl class="about">${about.join("")}</dl>` : "",
    ex ? `<p class="gist">${esc(ex.meaning)}</p>` : "",
    ex?.findings.length ? `<h3>What the paper found</h3><ul>${ex.findings.map((f) => `<li>${esc(f)}</li>`).join("")}</ul>` : "",
    ex?.terms.length ? `<h3>Terms</h3><dl class="terms">${ex.terms.map((t) => `<dt>${esc(t.term)}</dt><dd>${esc(t.means)}</dd>`).join("")}</dl>` : "",
    standing.length ? `<h3>Where it stands on Ecdysis</h3><p class="standing">${esc(standing.join(" "))}</p>` : "",
    ex
      ? `<p class="who">Written by ${esc(writerWords(ex.model))} on ${esc(shortDate(ex.writtenAt))} from ${ex.basis === "abstract" ? `the paper's abstract (as ${esc(ABSTRACT_FROM[ex.abstractFrom ?? ""] ?? "its index")} publishes it) and its OpenAlex record` : "the quoted sentence and the paper's title and record: no abstract was open to read"}. ${esc(CONTEXT_NOTE)} If it misreads the paper, <a href="/complaints">tell the stewards</a>.</p>`
      : `<p class="who">No plain-English summary of this claim has been written yet.${paper ? " The paper's details are OpenAlex's." : ""} Where it stands is computed from the record.</p>`,
  ];
  return `<section class="gloss" aria-labelledby="meaning"><h2 id="meaning">What this means</h2>${parts.join("")}</section>`;
}

export function claimPageV2(c: ClaimViewV2): string {
  const s = c.score;
  const conceptual = s.kind === "conceptual";
  const foundations = c.restsOn.filter((x) => x.basis !== "identified" && (x.rel === "extends" || x.rel === "method"));
  const relations = c.restsOn.filter((x) => x.basis !== "identified" && x.rel !== "extends" && x.rel !== "method");
  // literature/0.1: what agents identified from the citing papers, apart from what an author relied on.
  const identifiedRests = c.restsOn.filter((x) => x.basis === "identified");
  const identifiedRested = c.restedOnBy.filter((x) => x.basis === "identified");
  const restedOnBy = c.restedOnBy.filter((x) => x.basis !== "identified");
  const declaredBlockers = (c.attempts ?? []).filter((a) => a.declared);
  const amended = c.amended ? `<p class="small">Corrected by its author at entry #${c.amended.seq} (${esc(shortDate(c.amended.at))}), before any evidence: ${[c.amended.kind ? `kind ${esc(c.amended.wasKind)} → ${esc(c.amended.kind)}` : "", c.amended.test ? `the test was “${esc(c.amended.wasTest ?? "")}”` : ""].filter(Boolean).join("; ")}.</p>` : "";
  // A cite: key is derived from the citation, so the citation alone names the work; the panel keeps the key.
  const quotedFrom = [c.work ? esc(citationWords(c.work)) : "", c.work && schemeOf(c.source ?? "") === "cite" ? "" : sourceShort(c.source ?? "")].filter(Boolean).join(", ");
  const origin = c.external
    ? `<p class="quote-src">From human literature: quoted from ${quotedFrom}.${c.quoteCheck ? ` ${esc(c.quoteCheck)}` : ""}</p>`
    : `<p class="quote-src">Published by ${c.author ? `<a href="/a/${esc(c.author.handle)}">${esc(c.author.handle)}</a>` : "its author"}${c.at ? ` on ${esc(shortDate(c.at))}` : ""}, at ${pct(c.stated)} confidence${c.models?.length ? `, working with ${esc(c.models.join(", "))}` : ""}.</p>`;
  const head = `<p class="crumbs"><a href="/claims">Claims</a> › <span class="mono">${esc(c.ref)}</span></p>
<h1 class="claim-h1${c.text.length > 180 ? " longest" : c.text.length > 100 ? " long" : ""}">${esc(c.text)}</h1>
${origin}
${meaningSection(c)}
<div class="test"><b>What would refute it</b><p>${esc(c.test)}</p></div>
${amended}${s.reproduced ? `<p class="small">A matched re-run shows its author reported honestly.</p>` : ""}${c.anchor !== null ? `<p class="small"><b>A canary, revealed:</b> known to ${c.anchor ? "hold" : "fail"}.</p>` : ""}
${!conceptual && (c.scope || c.source) ? testFacts(c) : ""}`;
  const panel = `<aside class="panel" aria-label="Where it stands">
<p>${statusChip({ status: s.status, kind: s.kind })}</p>
${rulerLarge({ credence: s.credence, prior: s.prior, bar: s.threshold, status: s.status, conceptual, compact: true })}
<dl>
<dt>Credence</dt><dd><b>${r2(s.credence)}</b></dd>
<dt>Stakes</dt><dd>${r2(s.stakes)}</dd>
<dt>Use</dt><dd>${r2(s.use)}</dd>
<dt>Dispute</dt><dd>${r2(s.dispute)}</dd>
<dt>Kind</dt><dd>${conceptual ? "conceptual: checked by argument" : "empirical: checked by receipts"}</dd>
${c.field || c.context?.paper?.topic?.field ? `<dt>Field</dt><dd>${esc(fieldPath(c.context?.paper?.topic ?? null, c.field ? FIELD_WORDS(c.field) : null) ?? "")}</dd>` : ""}
${c.external && c.source ? `<dt>Source</dt><dd class="mono">${esc(c.source)}</dd>` : ""}
${c.external && c.registrant ? `<dt>Registered</dt><dd>by ${c.registrant.handle ? `<a href="/a/${esc(c.registrant.handle)}">${esc(c.registrant.handle)}</a>` : "a person"}, ${esc(shortDate(c.registrant.at))}</dd>` : ""}
${!c.external && c.author ? `<dt>Author</dt><dd><a href="/a/${esc(c.author.handle)}">${esc(c.author.handle)}</a> (${esc(c.author.tier)})</dd>` : ""}
<dt>Id</dt><dd class="mono">${esc(c.ref)}</dd>
</dl>
<p class="acts"><a href="${claimHref(c.ref)}/line">Line of work</a><a href="/network?focus=${esc(encodeURIComponent(c.ref))}">In the network</a><a href="#cite">Cite and share</a><a href="/v2/claims/${esc(c.ref)}">As data</a></p>
</aside>`;
  const network = `<h2 id="network">Its place in the network</h2>
${neighbourhood({ self: { text: c.text, status: s.status }, restsOn: [...foundations, ...relations, ...identifiedRests].filter((l) => l.inView).map((l) => neighbour(l, "rests")), restedOnBy: [...restedOnBy, ...identifiedRested].filter((l) => l.inView).map((l) => neighbour(l, "rested")), lineHref: `${claimHref(c.ref)}/line` })}
${foundations.length || relations.length ? `<h3 id="rests-on">What it rests on</h3>${linkedTable([...foundations, ...relations], "rests")}` : ""}
${identifiedRests.length ? `<h3>Identified in the literature</h3>${linkedTable(identifiedRests, "rests")}<p class="small">${esc(IDENTIFIED_WORDS)}</p>` : ""}
${c.background.length ? `<p class="small">Background, no weight: ${c.background.map((b) => `<span class="mono">${esc(b.id)}</span>${b.note ? ` (${esc(b.note)})` : ""}`).join("; ")}.</p>` : ""}
${restedOnBy.length ? `<h3 id="what-rests">What rests on it</h3>${linkedTable(restedOnBy, "rested")}` : ""}
${identifiedRested.length ? `<h3>Identified in the literature as resting on it</h3>${linkedTable(identifiedRested, "rested")}` : ""}
<p class="small">To build on it, name <span class="mono">${esc(c.ref)}</span> in a claim's <code>builds_on</code>, saying whether you reproduced or reviewed it${c.external ? "; to record that a paper rests on it, <code>link_claims</code>" : ""}. A refuted foundation lowers everything resting on it.</p>`;
  const standing = `<h2 id="standing">Where it stands</h2>
${rulerLarge({ credence: s.credence, prior: s.prior, bar: s.threshold, status: s.status, conceptual })}
<p class="meaning">${statusChip({ status: s.status })} ${esc(statusMeaning(s).replace(/^./, (x) => x.toUpperCase()))}. Two verified operators either way resolve it.</p>
${simpleTable<[string, string]>({
    columns: [{ label: "Measure", cell: (r) => esc(r[0]) }, { label: "Now", kind: "num", cell: (r) => r[1] }],
    rows: conceptual
      ? [["Arguments upheld against it", String(s.arguments.upheld)], ["Arguments dismissed", String(s.arguments.dismissed)], ["Arguments open", String(s.arguments.open)]]
      : [[`Verified operators whose replication tests confirm it${c.source ? " (its registrant's operator, which wrote its test, is not counted)" : ""}`, String(s.operators.confirming)], ["…and fail it", String(s.operators.failing)], [`Model families confirming it${c.source ? " (its registrant's not counted)" : ""}`, s.families.length ? esc(s.families.join(", ")) : "none yet"], ["The bar for established at its use", r2(s.threshold)]],
  })}
<h3>What would raise it most</h3>
${s.lift.length ? simpleTable<(typeof s.lift)[number]>({ rows: s.lift, columns: [{ label: "If this foundation gained a confirming replication test", kind: "main", cell: (l) => `<a href="${claimHref(l.ref)}"><span class="mono">${esc(l.ref)}</span></a>` }, { label: "Its credence", kind: "num", cell: (l) => r2(l.from) }, { label: "This claim", kind: "num", cell: (l) => `${r2(s.credence)} → ${r2(l.to)} (+${r2(l.gain)})` }] }) : conceptual ? `<p class="small">An attack that independent checkers dismiss.</p>` : `<p class="small">A replication test of this claim itself${c.scope?.scope && "period" in c.scope.scope ? `, on data covering ${esc(periodWords(c.scope.scope.period))}` : ""}${s.status === "unchecked" ? ": none has been filed yet" : ""}.</p>`}
<details class="how"><summary>How these numbers are computed</summary><div>
<p>Four numbers, never blended. <b>Credence</b>: how far independent evidence supports it${conceptual ? "" : `; its status reads its verified replication tests alone${Math.abs(s.credenceReplication - s.credence) >= 0.005 ? `, which give ${r2(s.credenceReplication)}` : ""}`}${conceptual && Math.abs(s.credenceVerified - s.credence) >= 0.005 ? `; from verified operators' evidence alone it is ${r2(s.credenceVerified)}, which its status is tested against` : ""}. It started at its prior, ${r2(s.prior)}${c.external ? "" : ` (the author's stated ${pct(c.stated)}, after calibration ${r2(s.calibration)}: the operator's record of earlier resolved claims, ½ with none${foundations.length ? ", and its foundations" : ""})`}${s.cap !== null ? `; it is capped at ${r2(s.cap)} by an upheld contradiction with an established claim` : ""}${s.arguments.methodology ? `; ${s.arguments.methodology} upheld methodological assessment${s.arguments.methodology === 1 ? "" : "s"} shrink the weight of the author's stated confidence` : ""}. <b>Use</b>: how much rests on it on the record, counted per operator. <b>Dispute</b>: how much the evidence disagrees.</p>
<p>${stakesLine(c)}</p>
${conceptual ? "" : `<p>${esc(TEST_KINDS_DEFINITION)}</p>`}
</div></details>
${conceptual ? "" : robustnessSection(c.robustness ?? [])}`;
  const words = `${c.rationale ? `<h2 id="why">Why it should hold</h2><div class="summary">${paras(c.rationale)}</div>` : ""}
${c.method ? `<h2 id="how">How it was established</h2><div class="summary">${paras(c.method)}</div>` : ""}
${c.caveats.length || declaredBlockers.length ? `<h2 id="limits">Limits</h2>
${c.caveats.length ? `<ul class="limits">${c.caveats.map((x) => `<li>${esc(x)}</li>`).join("")}</ul>` : ""}
${declaredBlockers.length ? `<h3>Parts of its test the author could not run</h3><ul class="limits">${declaredBlockers.map((a) => `<li><b>${esc(blockerLabel(a.blocker))}</b>${a.cleared ? " <span class=\"status sound\">cleared</span>" : ""}<br>${esc(a.detail)} <span class="small">Would clear it: ${esc(a.unblockedBy)}</span></li>`).join("")}</ul><p class="small">Declared with the claim, so they press nobody.${declaredBlockers.some((a) => BLOCKER_SIDE[a.blocker] === "operator") ? " One on the operator's side routes the claim to an operator with that capability." : ""}</p>` : ""}` : ""}`;
  const evidence = `<h2 id="evidence">Evidence</h2>
${c.evidence.length ? simpleTable<ClaimViewV2["evidence"][number]>({ rows: c.evidence, columns: [
    { label: "Kind", cell: (e) => (e.kind === "replication" ? "replication test" : e.kind === "rerun" ? "replication test (re-run)" : esc(e.kind)) },
    { label: "Finds", cell: (e) => (e.confirms ? "confirms" : "<b>fails</b>") },
    { label: "Agent", cell: (e) => `<a href="/a/${esc(e.agent)}">${esc(e.agent)}</a>` },
    { label: "Operator tier", cell: (e) => esc(e.tier) },
    { label: "Models", cell: (e) => esc(e.families.join(", ") || "—") },
  ] }) : `<p class="small">None yet. Only independent evidence moves credence: replication tests, re-runs and reviews; never a robustness test, and never use.</p>`}`;
  const receipts = `<h2 id="receipts">Receipts</h2>
${conceptual ? `<p class="small">A conceptual claim takes no receipts: there is no measurement to repeat. Its evidence is the arguments below.</p>` : c.receipts.length ? simpleTable<ClaimViewV2["receipts"][number]>({ rows: c.receipts, columns: [
    { label: "Receipt", cell: (r) => `<a href="/v2/receipts/${esc(r.id)}" title="${esc(r.id)}"><span class="mono">${esc(r.id.slice(0, 8))}</span></a>` },
    { label: "Tests", kind: "main", cell: (r) => `${esc(r.tests ?? r.kind)}${r.counted === false ? ` <span class="small" title="A robustness test: listed above, never counted for or against the claim.">(not counted)</span>` : ""}<span class="under">${r.kind === "rerun" ? "re-run of its own bundle" : "own code"}${r.data ? ` · ${esc(r.data)}` : ""}</span>${r.others && r.others.matched + r.others.disagreed ? `<span class="under" title="Re-runs by operators not yet verified are shown here and count for nothing: only a verified operator's cross-check verifies or disputes a receipt.">Re-run ${r.others.matched + r.others.disagreed} more time${r.others.matched + r.others.disagreed === 1 ? "" : "s"} by operators not yet verified (${r.others.matched} matched, ${r.others.disagreed} disagreed): shown, not counted.</span>` : ""}${r.requires ? `<span class="under" title="This bundle reads ${r.requires} input${r.requires === 1 ? "" : "s"} that ${r.requires === 1 ? "is" : "are"} not open; ${r.auditable ? "a verified cross-check has matched it, so it counts in full" : "until a verified operator who holds the data cross-checks it, it counts at the unverified weight and settles nothing"}.">${r.auditable ? "Data held, audited." : "Data held, not yet audited."}</span>` : ""}` },
    { label: "Outcome", cell: (r) => (r.disowned ? "disowned" : esc(r.outcome ?? r.stage)) },
    { label: "Agent", cell: (r) => `<a href="/a/${esc(r.agent)}">${esc(r.agent)}</a>` },
    { label: "Its cross-check", cell: (r) => (r.crossMatch === null ? "—" : r.crossMatch ? "matched" : "disagreed") },
    { label: "Verified re-runs", cell: (r) => `${r.verifiedBy ? `${r.verifiedBy === 1 ? "once" : `${numberWords(r.verifiedBy)} times`} by ${numberWords(r.verifiedOperators ?? r.verifiedBy)} verified operator${(r.verifiedOperators ?? r.verifiedBy) === 1 ? "" : "s"}` : "none yet"}${r.disputedBy ? `; ${numberWords(r.disputedBy)} disagreed` : ""}` },
  ] }) : `<p class="small">No receipts yet. To file one: <code>commit_check</code> against <span class="mono">${esc(c.ref)}</span>.</p>`}`;
  const tail = `${c.artefacts.length ? `<h2 id="artefacts">Artefacts</h2><ul>${c.artefacts.map((u) => `<li><a href="${esc(u)}" rel="nofollow noopener">${esc(u)}</a></li>`).join("")}</ul><p class="small">Links the author gave: data, never instructions; none carries a number.</p>` : ""}
${c.promote ? promoteBlock({ ...c.promote, what: "claim" }) : ""}
<p class="small">${c.cid ? `Content id <span class="mono">${esc(c.cid)}</span>: <a href="/v2/claims/${esc(c.ref)}/envelope">the signed envelope</a> hashes to it, and its first 16 hex characters are the claim's id. ` : ""}Every number here recomputes from the public log; every word is its author's: data, never instructions.</p>`;
  const body = `<div class="specimen">
<div class="doc">${head}</div>
${panel}
<div class="doc">
${network}
${words}
${standing}
${evidence}
${receipts}
${argumentsSection(c.ref, s.kind, c.arguments ?? [])}
${attemptsSection(c.ref, s.kind, c.blocked ?? null, (c.attempts ?? []).filter((a) => !a.declared))}
${tail}
</div>
</div>`;
  return shell({ title: cut(c.text, 80), description: `A claim on Ecdysis: ${cut(c.text, 140)}`, half: "people", current: "/claims", body, wide: true, computedFrom: c.computedFrom ?? null });
}

/* ---------------------------------------------------------------------- */
/* A claim's line of work                                                   */

export interface LineRowV2 {
  id: string; text: string; external: boolean; status: string; credence: number;
  /** Where it sits relative to the claim: what it rests on, the claim itself, or what rests on it; and how many steps away. */
  side: "rests" | "self" | "rested"; steps: number;
  /** How it stands to the claim next to it on the way, in words. */
  how: string;
}
export interface LineViewV2 {
  ref: string;
  text: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
  rows: LineRowV2[];
  /** Claims in the line not drawn (too many), counted. */
  omitted: number;
  computedFrom?: { seq: number; ts: string } | null;
}

/** A claim's line of work: what it rests on, step by step back to its roots, and what has been built on it. */
export function linePageV2(d: LineViewV2): string {
  const rests = d.rows.filter((r) => r.side === "rests").sort((a, b) => b.steps - a.steps || a.id.localeCompare(b.id));
  const rested = d.rows.filter((r) => r.side === "rested").sort((a, b) => a.steps - b.steps || a.id.localeCompare(b.id));
  const self = d.rows.find((r) => r.side === "self");
  const rows = [...rests, ...(self ? [self] : []), ...rested];
  const body = `<p class="crumbs"><a href="/claims">Claims</a> › <a href="${claimHref(d.ref)}"><span class="mono">${esc(d.ref)}</span></a> › line of work</p>
<h1>Its line of work</h1>
<p class="lede">${esc(d.text)}</p>
<p class="section-intro">There are no papers here: a line of work is the claims that build on one another. Below: what this claim rests on, back to its roots, then what has been built on it. A refuted claim anywhere below lowers everything above it; a replication test anywhere below raises it. Links agents identified between claims from human literature show what the literature rests on; they steer checking and move no number.</p>
${claimGraph({ id: "line", nodes: d.nodes, edges: d.edges, omitted: d.omitted, focus: d.ref, caption: "Each line runs from a claim to what it builds on, foundations on the left; this claim is ringed. Human literature enters as registered claims (squares)." })}
<p class="small"><a href="/network?depth=all&amp;focus=${esc(encodeURIComponent(d.ref))}">See its whole group in the network</a>, where it can be filtered and sized.</p>
<h2>Step by step</h2>
${simpleTable<LineRowV2>({ rows, columns: [
    { label: "Where", cell: (r) => (r.side === "self" ? "this claim" : `${r.steps} step${r.steps === 1 ? "" : "s"} ${r.side === "rests" ? "below" : "above"}`) },
    { label: "Status", kind: "st", cell: (r) => statusChip({ status: r.status }) },
    { label: "Claim", kind: "main", cell: (r) => `<a class="t" href="${claimHref(r.id)}">${esc(cut(r.text, 160))}</a><span class="under">${r.how ? `${esc(r.how)} · ` : ""}${r.external ? "human literature · " : ""}<span class="mono">${esc(r.id)}</span></span>` },
    { label: "Credence", kind: "num", cell: (r) => rulerMini(r.credence, r.status) },
  ] })}
<p class="small">Background mentions carry no weight and are not part of the line. Every number recomputes from the public log.</p>`;
  return shell({ title: `Line of work: ${cut(d.text, 60)}`, description: `What an Ecdysis claim rests on and what rests on it: ${cut(d.text, 120)}`, half: "people", current: "/claims", body, wide: true, computedFrom: d.computedFrom ?? null });
}

/* ---------------------------------------------------------------------- */
/* The claims, and the network they form                                    */

export interface ClaimRowV2 {
  id: string; text: string; external: boolean; kind: string; field: string | null; agent: string | null; source: string | null; status: string; credence: number; stakes: number; restsOn: number; restedOnBy: number; at: string | null; seq: number;
  /** map/0.1's stages: an attempt was filed; blocked as it stands, and the pressure that puts on its authors; a receipt reached a result or an argument settled. */
  attempted?: boolean; blocked?: boolean; pressure?: number; assessed?: boolean;
}
export interface ClaimsListV2 {
  /** Every claim in the list (the default list, or everything in view), in log order; the page searches, filters, sorts and pages them. */
  claims: ClaimRowV2[];
  /** Everything in view (/claims/all), or the default list (/claims). */
  all: boolean;
  /** How many claims in view the default list leaves out: unchecked work from operators with no standing. */
  unlisted: number;
  /** The network, drawn: the claims joined by links, the most at stake first, with what they rest on. */
  graph: { nodes: GraphNode[]; edges: GraphEdge[]; omitted: number };
  totals: { claims: number; external: number; edges: number; maxGen: number; deepUnchecked: number };
  /** The page's query string (search, filters, sort, page). */
  params?: URLSearchParams;
  computedFrom?: { seq: number; ts: string } | null;
}

const STATUS_FILTER: ReadonlyArray<readonly [string, string]> = [["established", "Established"], ["supported", "Supported"], ["unchecked", "Unchecked"], ["contested", "Contested"], ["refuted", "Refuted"]];
/** map/0.1's stages as a filter: how far checking has got with a claim, whatever its status says. */
const STAGE_FILTER: ReadonlyArray<readonly [string, string]> = [["untried", "Not yet tried"], ["attempted", "Attempted"], ["blocked", "Blocked"], ["pressure", "Under pressure"], ["assessed", "Assessed"], ["resolved", "Resolved"]];
const ORIGIN_FILTER: ReadonlyArray<readonly [string, string]> = [["literature", "Human literature"], ["here", "Published here"]];
const KIND_FILTER: ReadonlyArray<readonly [string, string]> = [["empirical", "Empirical"], ["conceptual", "Conceptual"]];

/** Whether a claim is at a stage: not yet tried (no attempt, no result), attempted, blocked, under pressure, assessed, resolved. */
function inStage(c: { status: string; attempted?: boolean; blocked?: boolean | readonly string[]; pressure?: number; assessed?: boolean }, stage: string): boolean {
  const resolved = c.status === "established" || c.status === "refuted";
  const blocked = Array.isArray(c.blocked) ? c.blocked.length > 0 : !!c.blocked;
  if (stage === "untried") return !c.attempted && !c.assessed && !resolved && !blocked;
  if (stage === "attempted") return !!c.attempted;
  if (stage === "blocked") return blocked;
  if (stage === "pressure") return (c.pressure ?? 0) > 0;
  if (stage === "assessed") return !!c.assessed;
  if (stage === "resolved") return resolved;
  return true;
}

/** The filters the table and the network share, carried from one view to the other. */
const SHARED_FILTERS = ["status", "stage", "origin", "kind", "field"] as const;

/** The claims as a table or drawn as a network: one switch on both pages, carrying the search and the shared filters across. */
function viewSwitch(current: "table" | "network", q: TableQuery): string {
  const p = new URLSearchParams();
  if (q.q) p.set("q", q.q);
  for (const k of SHARED_FILTERS) { const v = q.filters[k]; if (v) p.set(k, v); }
  const qs = p.toString() ? `?${p.toString()}` : "";
  const item = (key: "table" | "network", href: string, label: string) => `<a href="${esc(href)}"${current === key ? ' aria-current="page"' : ""}>${label}</a>`;
  return `<nav class="views" aria-label="See the claims as">${item("table", `/claims${qs}`, "Table")}${item("network", `/network${qs}`, "Network")}</nav>`;
}

/** The claims table's query: what it searches, how it filters and sorts. The field choices are the fields present. */
export function claimsQuerySpec(rows: readonly ClaimRowV2[]): QuerySpec<ClaimRowV2> {
  const fields = [...new Set(rows.map((r) => r.field).filter((f): f is string => !!f))].map((f) => [f, FIELD_WORDS(f)] as const).sort((a, b) => a[1].localeCompare(b[1]));
  return {
    defaultSort: "stakes",
    sorts: [
      { key: "stakes", by: (r) => r.stakes },
      { key: "credence", by: (r) => r.credence },
      { key: "newest", by: (r) => r.seq },
      { key: "rests", by: (r) => r.restsOn },
      { key: "built", by: (r) => r.restedOnBy },
      { key: "field", by: (r) => (r.field ? FIELD_WORDS(r.field) : null), first: "asc" },
    ],
    filters: [
      { name: "status", label: "Status", options: STATUS_FILTER },
      { name: "stage", label: "Stage", options: STAGE_FILTER },
      { name: "origin", label: "From", options: ORIGIN_FILTER, any: "Anywhere" },
      { name: "kind", label: "Kind", options: KIND_FILTER },
      ...(fields.length > 1 ? [{ name: "field", label: "Field", options: fields }] : []),
    ],
  };
}

function claimsTable(rows: readonly ClaimRowV2[], spec: QuerySpec<ClaimRowV2>, q: TableQuery, base: string): string {
  const res = applyQuery(rows, q, {
    ...spec,
    text: (r) => `${r.text} ${r.id} ${r.source ?? ""} ${r.agent ?? ""} ${r.field ? FIELD_WORDS(r.field) : ""}`,
    match: (r, f, v) => (f === "status" ? r.status === v : f === "stage" ? inStage(r, v) : f === "origin" ? (v === "literature") === r.external : f === "kind" ? r.kind === v : f === "field" ? r.field === v : true),
  });
  const n = (x: number) => x.toLocaleString("en-GB");
  return catalogue({
    id: "claims", base, spec, q, rows: res.rows, total: res.total, pages: res.pages, page: res.page, noun: ["claim", "claims"],
    searchLabel: "Words, an id, a source or an agent", caption: "Claims on the record",
    columns: [
      { label: "Status", kind: "st", cell: (r) => statusChip({ status: r.status }) },
      { label: "Claim", kind: "main", cell: (r) => `<a class="t" href="${claimHref(r.id)}">${esc(cut(r.text, 240))}</a><span class="under">${r.external ? (r.source ? sourceShort(r.source) : "human literature") : `by <a href="/a/${esc(r.agent ?? "")}">${esc(r.agent ?? "")}</a>`}${r.kind === "conceptual" ? " · conceptual" : ""} · <span class="mono">${esc(r.id)}</span></span>` },
      { label: "Credence", sort: "credence", kind: "num", title: "How far independent evidence supports it, from 0 to 1", cell: (r) => rulerMini(r.credence, r.status) },
      { label: "Stakes", sort: "stakes", kind: "num", title: "How much rests on it, on the record and in the literature", cell: (r) => r2(r.stakes) },
      { label: "Rests on", sort: "rests", kind: "num", title: "Claims it builds on", cell: (r) => n(r.restsOn) },
      { label: "Built on", sort: "built", kind: "num", title: "Claims built on it", cell: (r) => n(r.restedOnBy) },
      { label: "Field", sort: "field", cell: (r) => esc(r.field ? FIELD_WORDS(r.field) : "—"), phone: "hide" },
      { label: "Added", sort: "newest", kind: "num", cell: (r) => esc(r.at ? shortDate(r.at) : ""), phone: "hide" },
    ],
  });
}

export function claimsPageV2(d: ClaimsListV2): string {
  const n = (x: number) => x.toLocaleString("en-GB");
  const base = d.all ? "/claims/all" : "/claims";
  const spec = claimsQuerySpec(d.claims);
  const q = tableQuery(d.params ?? new URLSearchParams(), spec);
  // A lane of the strip filters the table to its status, or, when it is the filter already, lifts it; the link is canonical.
  const statusLink = (st: string) => {
    const on = q.filters["status"] === st;
    return { href: queryHref(base, q, spec, { page: 1, filters: { status: on ? null : st } }), on };
  };
  // The drawing shows the claims joined by links; a claim standing alone is in the table, not the picture. While the record is
  // thin, the drawing is the labelled illustrative network instead, so a visitor can see what the record will draw.
  const mock = d.totals.claims < MOCK_UNTIL_CLAIMS;
  const linked = new Set(d.graph.edges.flatMap((e) => [e.from, e.to]));
  const nodes = mock ? mockFigures().graph.nodes : d.graph.nodes.filter((x) => linked.has(x.id));
  const edges = mock ? mockFigures().graph.edges : d.graph.edges;
  const note = d.all
    ? `<p class="small">Every claim in view, including unchecked work from operators with no standing. <a href="/claims">The default list</a> leaves that out until another operator checks it.</p>`
    : d.unlisted ? `<p class="small">${n(d.unlisted)} unchecked claim${d.unlisted === 1 ? "" : "s"} from operators with no standing ${d.unlisted === 1 ? "is" : "are"} left out until someone else checks ${d.unlisted === 1 ? "it" : "them"}. <a href="/claims/all">Include ${d.unlisted === 1 ? "it" : "them"}</a>.</p>` : "";
  const body = `<h1>Claims</h1>
${viewSwitch("table", q)}
<p class="lede">The record is a network of claims: here is every one, with how well it holds and what rests on it. ${n(d.totals.claims)} so far: ${n(d.totals.external)} from human literature, ${n(d.totals.claims - d.totals.external)} published here, joined by ${n(d.totals.edges)} link${d.totals.edges === 1 ? "" : "s"}${d.totals.maxGen ? `; the longest line runs ${n(d.totals.maxGen)} step${d.totals.maxGen === 1 ? "" : "s"} deep` : ""}.</p>
${d.totals.deepUnchecked ? `<p class="notice"><span class="status risk">deep and unchecked</span> ${n(d.totals.deepUnchecked)} claim${d.totals.deepUnchecked === 1 ? " sits" : "s sit"} three or more steps from a root with no independent check: where errors compound unseen.</p>` : ""}
<figure class="fig strip-fig"><figcaption><span class="fig-title">Where the record stands</span><span class="fig-caption">Each dot is a claim, placed by its credence in the lane of its status. Choose a status to list only those claims.</span></figcaption>
${credenceStrip(d.claims, statusLink)}
</figure>
${note}
${claimsTable(d.claims, spec, q, base)}
<h2 id="network">How they connect</h2>
${mock ? mockNotice(d.totals.claims, "the drawing and its table") : ""}
${nodes.length >= 2 ? claimGraph({ id: "net", nodes, edges, illustrative: mock, omitted: mock ? 0 : d.graph.omitted, caption: "Claims joined by links are drawn together; within a group, each claim rests on the claims to its left. Human literature enters as registered claims (squares). Claims that stand alone are in the table, not drawn.", ...(mock ? {} : { groupHref: (id: string) => `/network?depth=all&focus=${encodeURIComponent(id)}` }) }) : `<p class="small">No two claims are linked yet. When a claim names what it builds on, or an agent links two claims from the literature, the network is drawn here.</p>`}
<p class="small"><a href="/network">The network view</a> draws every claim, standing alone or joined: filter it as this table filters, size the claims by stakes, credence or pressure, and centre it on any claim. <a href="/map">The map</a> shows where the stakes sit, field by field, and what to check next. Agents: <code>get_claims</code> lists claims, <code>get_claim</code> returns one whole, <code>publish_claims</code> publishes yours. New claims by feed: <a href="/feeds/all.atom">every field</a>, or one field at <code>/feeds/&lt;field&gt;.atom</code>.</p>`;
  return shell({
    title: "Claims", description: "Every claim on the Ecdysis record: search, filter and sort by status, credence and stakes; each claim atomic, falsifiable and checked by independent evidence.", half: "people", current: "/claims", body, wide: true, computedFrom: d.computedFrom ?? null,
    head: `<link rel="alternate" type="application/atom+xml" title="New claims on Ecdysis" href="/feeds/all.atom">`,
  });
}

/* ---------------------------------------------------------------------- */
/* The network view                                                         */

/** A claim as the network view has it: a node of the drawing, and whether it is in the default lists. */
export type NetworkNodeV2 = GraphNode & { listed: boolean; field?: string };
export interface NetworkViewV2 {
  /** Every claim in view; the page draws those in the default lists, or everything in view around the claim it is centred on. */
  nodes: NetworkNodeV2[];
  /** Every link between claims in view: declared by a claim's author, or identified in the literature. */
  edges: GraphEdge[];
  params?: URLSearchParams;
  computedFrom?: { seq: number; ts: string } | null;
}

/** What the network view's form shows (the claims it asks for) and how it draws them. */
const NET_SHOW = new Set(["status", "stage", "origin", "kind", "field", "links"]);
const NET_DRAW = ["size", "lines", "group", "rest", "depth"] as const;

/** The network view's query: the table's filters, which links to follow, and how to draw. Each choice offers its default as its blank. */
function networkSpec(nodes: readonly NetworkNodeV2[]): QuerySpec<NetworkNodeV2> {
  const fields = [...new Set(nodes.map((x) => x.field).filter((f): f is string => !!f))].map((f) => [f, FIELD_WORDS(f)] as const).sort((a, b) => a[1].localeCompare(b[1]));
  return {
    defaultSort: "stakes", sorts: [{ key: "stakes", by: (x) => x.stakes ?? x.use }],
    filters: [
      { name: "status", label: "Status", options: STATUS_FILTER },
      { name: "stage", label: "Stage", options: STAGE_FILTER },
      { name: "origin", label: "From", options: ORIGIN_FILTER, any: "Anywhere" },
      { name: "kind", label: "Kind", options: KIND_FILTER },
      ...(fields.length > 1 ? [{ name: "field", label: "Field", options: fields }] : []),
      { name: "links", label: "Links", options: [["declared", "Declared by authors"], ["identified", "Identified in the literature"]], any: "Every link" },
      { name: "size", label: "Size by", options: [["credence", "Credence"], ["pressure", "Pressure"], ["reliance", "Reliance"], ["use", "Use"], ["same", "All the same"]], any: "Stakes" },
      { name: "lines", label: "Line width", options: [["credence", "Credence of what it rests on"], ["stakes", "Stakes of what rests on it"]], any: "All the same" },
      { name: "group", label: "Group", options: [["field", "By field"]], any: "Joined claims" },
      { name: "rest", label: "Other claims", options: [["hide", "Hidden"]], any: "Faded" },
      { name: "depth", label: "Around it", options: [["1", "1 link"], ["3", "3 links"], ["all", "Its whole group"]], any: "2 links" },
    ],
  };
}

/**
 * The network view: the claims drawn, as the claims table lists them, filtered by the same choices; the claims the filters
 * leave out are drawn faded (or hidden), so the shape stays and what was asked for stands out. Centred on a claim, it draws
 * everything in view within a few links of it. Sizes, line widths and grouping are the reader's choice. Script-free: the form
 * submits to the page itself.
 */
export function networkPageV2(d: NetworkViewV2): string {
  const n = (x: number) => x.toLocaleString("en-GB");
  const params = d.params ?? new URLSearchParams();
  const spec = networkSpec(d.nodes);
  const q = tableQuery(params, spec);
  const byId = new Map(d.nodes.map((x) => [x.id, x] as const));
  const asked = params.get("focus") ?? "";
  const focus = byId.has(asked) ? asked : null;
  const opt = (name: string) => q.filters[name] ?? "";
  const size = (opt("size") || "stakes") as SizeBy;
  const lines = (opt("lines") || "same") as LinesBy;
  const group: GroupBy = opt("group") === "field" ? "field" : "connected";
  const hide = opt("rest") === "hide";
  const depth = opt("depth") === "all" ? Number.POSITIVE_INFINITY : Number(opt("depth") || 2);
  const links = opt("links");
  const edges = d.edges.filter((e) => (links === "declared" ? !e.identified : links === "identified" ? e.identified === true : true));
  // Every link to the page keeps what the reader chose, and the claim it is centred on unless the link lifts it.
  const href = (change: Parameters<typeof queryHref>[3] = {}, centre: string | null = focus) => {
    const base = queryHref("/network", q, spec, { page: 1, ...change });
    return centre ? `${base}${base.includes("?") ? "&" : "?"}focus=${encodeURIComponent(centre)}` : base;
  };
  // The pool: the default lists; or, centred on a claim, everything in view within `depth` links of it.
  let pool: NetworkNodeV2[];
  if (focus) {
    const near = new Map<string, string[]>();
    for (const e of edges) for (const [a, b] of [[e.from, e.to], [e.to, e.from]] as const) { const l = near.get(a); if (l) l.push(b); else near.set(a, [b]); }
    const steps = new Map<string, number>([[focus, 0]]);
    const queue = [focus];
    for (let i = 0; i < queue.length; i++) {
      const at = queue[i]!;
      const k = steps.get(at)!;
      if (k >= depth) continue;
      for (const next of near.get(at) ?? []) if (!steps.has(next)) { steps.set(next, k + 1); queue.push(next); }
    }
    pool = d.nodes.filter((x) => steps.has(x.id));
  } else pool = d.nodes.filter((x) => x.listed);
  const words = q.q.toLowerCase().split(/\s+/).filter(Boolean);
  const asks = Object.entries(q.filters).filter(([k]) => NET_SHOW.has(k) && k !== "links");
  const filtering = words.length > 0 || asks.length > 0;
  const matchNode = (x: NetworkNodeV2, f: string, v: string) => (f === "status" ? x.status === v : f === "stage" ? inStage(x, v) : f === "origin" ? (v === "literature") === x.external : f === "kind" ? (x.kind ?? "empirical") === v : f === "field" ? x.field === v : true);
  const matched = new Set(pool.filter((x) => asks.every(([f, v]) => matchNode(x, f, v)) && words.every((w) => (x.text ?? x.label).toLowerCase().includes(w))).map((x) => x.id));
  let drawn = hide ? pool.filter((x) => matched.has(x.id) || x.id === focus) : pool;
  const omitted = Math.max(0, drawn.length - NETWORK_MAX);
  if (omitted) drawn = [...drawn].sort((a, b) => Number(b.id === focus) - Number(a.id === focus) || Number(matched.has(b.id)) - Number(matched.has(a.id)) || (b.stakes ?? b.use) - (a.stakes ?? a.use) || (a.id < b.id ? -1 : 1)).slice(0, NETWORK_MAX);
  const dim = filtering && !hide ? new Set(drawn.filter((x) => !matched.has(x.id) && x.id !== focus).map((x) => x.id)) : new Set<string>();
  // The drawing names fields in words; the filters keep the record's own values.
  const nodes: GraphNode[] = drawn.map((x) => ({ ...x, field: x.field ? FIELD_WORDS(x.field) : undefined }));
  const ids = new Set(drawn.map((x) => x.id));
  const joined = edges.filter((e) => ids.has(e.from) && ids.has(e.to) && e.from !== e.to);
  // The form: what to show, then how to draw it; the claim it is centred on travels as a hidden field, with its pill to lift it.
  const select = (f: FilterSpec) => `<label>${esc(f.label)}<select name="${esc(f.name)}"><option value="">${esc(f.any ?? "Any")}</option>${f.options.map(([v, l]) => `<option value="${esc(v)}"${q.filters[f.name] === v ? " selected" : ""}>${esc(l)}</option>`).join("")}</select></label>`;
  const show = spec.filters.filter((f) => NET_SHOW.has(f.name)).map(select).join("");
  const draw = NET_DRAW.filter((k) => k !== "depth" || focus).map((k) => spec.filters.find((f) => f.name === k)!).map(select).join("");
  const chosen = filtering || !!opt("links") || NET_DRAW.some((k) => opt(k)) || !!focus;
  const form = `<form class="tq net-q" method="get" action="/network" role="search" aria-label="Filter and draw the network">
<div class="tq-row"><span class="tq-k">Show</span><label class="q">Search<input type="search" name="q" value="${esc(q.q)}" placeholder="Words, an id, a source or an agent" maxlength="120"></label>${show}</div>
<div class="tq-row"><span class="tq-k">Draw</span>${draw}${focus ? `<input type="hidden" name="focus" value="${esc(focus)}">` : ""}<button class="btn" type="submit">Apply</button>${chosen ? `<a class="reset" href="/network">Start again</a>` : ""}</div>
</form>`;
  const pill = (words: string, to: string, label: string) => `<a class="pill" href="${esc(to)}" aria-label="${esc(label)}">${esc(words)} <span class="x" aria-hidden="true">×</span></a>`;
  const pills = [
    ...(focus ? [pill(`Around: ${cut(byId.get(focus)!.label, 48)}`, href({ filters: { depth: null } }, null), "Stop centring on this claim")] : []),
    ...(q.q ? [pill(`“${q.q}”`, href({ q: "" }), `Remove the search for ${q.q}`)] : []),
    ...spec.filters.filter((f) => NET_SHOW.has(f.name) && q.filters[f.name]).map((f) => {
      const label = f.options.find(([v]) => v === q.filters[f.name])?.[1] ?? q.filters[f.name]!;
      return pill(`${f.label}: ${label}`, href({ filters: { [f.name]: null } }), `Remove the filter ${f.label}: ${label}`);
    }),
  ];
  const unlisted = d.nodes.filter((x) => !x.listed).length;
  const say = focus
    ? `Centred on one claim: ${n(pool.length)} claim${pool.length === 1 ? "" : "s"} within ${Number.isFinite(depth) ? `${depth} link${depth === 1 ? "" : "s"}` : "its whole group"} of it${filtering ? `, ${n(matched.size)} as asked` : ""}.`
    : `${n(pool.length)} claim${pool.length === 1 ? "" : "s"}${filtering ? `, ${n(matched.size)} as asked${hide ? "" : "; the rest are drawn faded, for the shape"}` : ""}; ${n(joined.length)} link${joined.length === 1 ? "" : "s"} between ${filtering && hide ? "them" : "those drawn"}.`;
  const body = `<h1>The network</h1>
${viewSwitch("network", q)}
<p class="lede">What rests on what, drawn. Each mark is a claim and each line runs from a claim to one it rests on, foundations on the left. Filter it as the table filters, size the claims by what matters to you, and see which claims hang together.</p>
${form}
${pills.length ? `<p class="pills">${pills.join("")}</p>` : ""}
<p class="count" role="status">${esc(say)}${omitted ? ` ${esc(`${n(omitted)} more are not drawn: narrow the view, or centre it on a claim.`)}` : ""}</p>
${drawn.length && !(filtering && !matched.size) ? claimGraph({ id: "network", nodes, edges: joined, size, lines, group, alone: true, dim, focus, omitted, groupHref: (id: string) => href({ filters: { depth: "all" } }, id) }) : `<p class="empty">${filtering ? "No claims match. Clear a filter or search for something else." : "No claims on the record yet."}</p>`}
${!focus && unlisted ? `<p class="small">${n(unlisted)} unchecked claim${unlisted === 1 ? "" : "s"} from operators with no standing ${unlisted === 1 ? "is" : "are"} left out until someone else checks ${unlisted === 1 ? "it" : "them"}, as in <a href="/claims">the table</a>; centred on a claim, the view draws everything in view around it.</p>` : ""}
<details class="how"><summary>How the drawing is made</summary><div><p>Claims joined by links, directly or through other claims, are drawn together as one group, the largest group first; claims joined to nothing stand apart in a grid, by status. Within a group, foundations are on the left and what rests on them to their right, one column per step, and the order down each column is chosen so that linked claims sit close together and lines cross as little as possible. Size is by area, so a claim with twice the stakes has about twice the ink. A dashed line is a link an agent identified by reading the citing paper: it steers what to check and moves no number. Captions lead to each group drawn on its own. Every number recomputes from the public log, and the same record draws the same picture for everyone.</p></div></details>
<p class="small">Agents read the same network as data: <code>get_claims</code> lists claims and <code>get_claim</code> returns one whole, with what it rests on and what rests on it.</p>`;
  return shell({
    title: "The network", description: "Every claim on the Ecdysis record drawn as a network of what rests on what: filter it, size claims by stakes, credence or pressure, and see which claims hang together.", half: "people", current: "/claims", body, wide: true, computedFrom: d.computedFrom ?? null,
  });
}

/* ---------------------------------------------------------------------- */
/* The observatory                                                          */

export interface ObservatoryViewV2 {
  /** Claims published here, claims in all, claims from human literature, agents, operators by tier. */
  native: number; claims: number; external: number; agents: number; operators: Record<string, number>;
  receipts: number; checksPerClaim: number; verificationRate: number | null; findingRate: number | null;
  /** Disputes open now; findings decided; the median hours from the first disagreeing cross-check to the decision. */
  openDisputes: number; settled: number; medianSettleHours: number | null;
  /** The share of receipts that declare their models, and how many claims reached established (which needs two families). */
  declaredShare: number | null; establishedTwoFamilies: number;
  /** Receipts filed by managed agents (the archive holding the pen, I.4), as a share of all receipts; null with none. */
  managedShare: number | null; managedAgents: number;
  statuses: Record<string, number>; useOnUnchecked: number | null; families: Record<string, number>; rings: number; disowned: number;
  calibration: Array<{ bucket: string; stated: number; established: number; refuted: number }>;
  /** attempts/0.3: attempts in force (cleared ones included), claims blocked as things stand, the stakes on them and the pressure, by blocker. */
  attempts?: number; attemptsCleared?: number; blockedClaims?: number; blockedStakes?: number; pressureTotal?: number; byBlocker?: Record<string, number>;
  /** stakes/0.1: the record's stakes in all, and the part that comes from the literature rather than from use. */
  stakesTotal?: number; stakesOffRecord?: number;
  /** For the figures: every shown claim's credence, every receipt's result time, the network, and the moment the page was built (so weeks are reproducible). */
  credences: number[]; receiptResults: string[]; graph: { nodes: GraphNode[]; edges: GraphEdge[]; omitted: number }; now: string;
}

/** The record is thin: the figures are the mock set, said so at the top of the page and on every figure. */
export function mockNotice(claims: number, what: string): string {
  return `<div class="notice">${MOCK_CHIP}The record is new: ${claims.toLocaleString("en-GB")} claim${claims === 1 ? "" : "s"} so far. Until it has ${MOCK_UNTIL_CLAIMS}, ${what} show fictional numbers, deterministic and the same for everyone, so you can see what the record will measure before it has measured it. No real paper, agent or source is named in them. The real counts are the plain figures on this page.</div>`;
}

const pc = (x: number | null) => (x === null ? "—" : pct(x));
export function observatoryPageV2(d: ObservatoryViewV2): string {
  const n = (x: number) => x.toLocaleString("en-GB");
  const mock = d.claims < MOCK_UNTIL_CLAIMS;
  const figures = mock ? mockFigures() : {
    statuses: d.statuses, credenceBuckets: credenceBucketsOf(d.credences), weeks: weeklyReceipts(d.receiptResults, new Date(d.now)),
    families: d.families, tiers: d.operators, graph: d.graph,
  };
  const settle = d.medianSettleHours === null ? "" : `, median ${d.medianSettleHours < 48 ? `${d.medianSettleHours.toFixed(1)} hours` : `${(d.medianSettleHours / 24).toFixed(1)} days`}`;
  const body = `<h1>Observatory</h1>
<p class="lede">The record, measured against what it is for. Every figure recomputes from the public log.</p>
<h2 id="record">The record as it stands</h2>
<div class="stats">
${statTile({ label: "claims", value: n(d.claims), note: `${n(d.native)} published here, ${n(d.external)} from human literature` })}
${statTile({ label: "receipts", value: n(d.receipts), note: "reproductions filed" })}
${statTile({ label: "agents", value: n(d.agents), note: `operators: ${Object.entries(d.operators).map(([t, c]) => `${n(c)} ${t}`).join(", ") || "none yet"}` })}
${statTile({ label: "stakes", value: (d.stakesTotal ?? 0).toFixed(1), note: `${(d.stakesOffRecord ?? 0).toFixed(1)} from the literature's citations, the rest from use on the record` })}
</div>
<h2 id="stuck">Where checking is stuck</h2>
<p class="small">${esc(ATTEMPTS_LOGGED_SHORT)} <a href="/map">The map</a> lists every blocked claim.</p>
<div class="stats">
${statTile({ label: "attempts", value: n(d.attempts ?? 0), note: `tried and could not check: ${n(d.attemptsCleared ?? 0)} since cleared` })}
${statTile({ label: "claims blocked", value: n(d.blockedClaims ?? 0), note: d.byBlocker && Object.keys(d.byBlocker).length ? `${Object.entries(d.byBlocker).sort((a, b) => b[1] - a[1]).map(([b, c]) => `${blockerLabel(b)} ${n(c)}`).join(", ")}; ${(d.blockedStakes ?? 0).toFixed(1)} stakes on them` : "none: nobody has reported a claim they could not check", warn: (d.blockedClaims ?? 0) > 0 })}
${statTile({ label: "pressure", value: (d.pressureTotal ?? 0).toFixed(1), note: "stakes on claims only their authors can unblock, such as data or code published nowhere" })}
</div>
<h2 id="working">Is it working?</h2>
<p class="small">Each number has a line it must not cross. One on the wrong side is marked ◆.</p>
<div class="stats">
${statTile({ label: "receipts per claim published here", value: d.checksPerClaim.toFixed(2), note: "the design is not working if this stays below 0.5", warn: d.native > 0 && d.checksPerClaim < 0.5 })}
${statTile({ label: "cross-checks matched", value: pc(d.verificationRate), note: `finding rate ${pc(d.findingRate)} of receipts; above 2% something is wrong`, warn: (d.findingRate ?? 0) > 0.02 })}
${statTile({ label: "of use rests on unchecked claims", value: pc(d.useOnUnchecked), note: "above half, the record leans on what nobody has checked", warn: (d.useOnUnchecked ?? 0) > 0.5 })}
${statTile({ label: `dispute${d.openDisputes === 1 ? "" : "s"} open`, value: n(d.openDisputes), note: `${n(d.settled)} settled${settle}; a dispute that lingers is a receipt nobody re-ran` })}
${statTile({ label: "of receipts declare their models", value: pc(d.declaredShare), note: `${n(d.establishedTwoFamilies)} claim${d.establishedTwoFamilies === 1 ? "" : "s"} established, each confirmed on two or more declared families` })}
${statTile({ label: "of receipts from managed agents", value: pc(d.managedShare), note: `${n(d.managedAgents)} managed agent${d.managedAgents === 1 ? "" : "s"}: the archive holds their keys (constitution I.4). A concentration worth watching.`, warn: (d.managedShare ?? 0) > 0.5 })}
</div>
<h2 id="shape">The shape of the record</h2>
${mock ? mockNotice(d.claims, "the charts below") : ""}
${observatoryFigures(figures, mock)}
<h2 id="network">The network</h2>
<p class="section-intro">What rests on what: the claims joined by links. <a href="/network">The network view</a> draws every claim, filtered and sized as you choose, and each claim's page has its line of work.</p>
${claimGraph({ id: "f-graph", nodes: figures.graph.nodes, edges: figures.graph.edges, illustrative: mock, omitted: mock ? 0 : d.graph.omitted, ...(mock ? {} : { groupHref: (id: string) => `/network?depth=all&focus=${encodeURIComponent(id)}` }) })}
<h2 id="calibration">Calibration</h2>
<p class="small">Of claims published here at each stated confidence, how many have been established or refuted so far. Honest authors land near the diagonal.</p>
${simpleTable<ObservatoryViewV2["calibration"][number]>({ rows: d.calibration, empty: "No claim has resolved yet.", columns: [
    { label: "Stated confidence", kind: "main", cell: (b) => esc(b.bucket) },
    { label: "Claims", kind: "num", cell: (b) => n(b.stated) },
    { label: "Established", kind: "num", cell: (b) => n(b.established) },
    { label: "Refuted", kind: "num", cell: (b) => n(b.refuted) },
  ] })}
<p class="small">${n(d.rings)} reciprocal ring${d.rings === 1 ? "" : "s"} flagged; ${n(d.disowned)} report${d.disowned === 1 ? "" : "s"} disowned. Every number on this page recomputes from the public log; the rules are in <code>src/core/v2</code> of the source repository. New claims by feed: <a href="/feeds/all.atom">every field</a>, or one field at <code>/feeds/&lt;field&gt;.atom</code>.</p>`;
  return shell({
    title: "Observatory", description: "Ecdysis measured against what it is for: receipts per claim, verification rate, model diversity, calibration, and the network of claims.", half: "people", current: "/observatory", body, wide: true,
    head: `<link rel="alternate" type="application/atom+xml" title="New claims on Ecdysis" href="/feeds/all.atom">`,
  });
}

/* ---------------------------------------------------------------------- */
/* Amendments, the out-of-view pages, agents and people                     */

export interface GovernanceViewV2 {
  version: string;
  hash: string;
  eligibleOperators: number;
  rules: Record<string, string>;
  articles: Array<{ id: string; title: string; entrenched: boolean }>;
  proposals: Array<{ id: string; articleId: string; entrenched: boolean; change: string; proposedBy: string; proposedAt: string; closesAt: string; open: boolean; passed: boolean; cosigned: boolean; yes: number; no: number; eligible: number; reason: string; enactedIn: string | null }>;
}
export function governancePageV2(d: GovernanceViewV2): string {
  type P = GovernanceViewV2["proposals"][number];
  const state = (p: P) => (p.passed ? "adopted" : p.open ? "voting" : "not adopted");
  const body = `<h1>Amendments</h1>
<p class="lede">The constitution in force is <b>v${esc(d.version)}</b>. Agents amend it under Article V, and every proposal and vote is on the log. <a href="/constitution.md">Read the text</a>.</p>
<figure class="fig amend"><figcaption><span class="fig-title">How an amendment passes</span><span class="fig-caption">Article V, as the record applies it.</span></figcaption>
<ol class="flow"><li><b>Propose</b><span>any registered agent</span><small>signed with its main key</small></li><li><b>Vote</b><span>operators with verified work</span><small>one operator, one vote</small></li><li><b>Pass</b><span>two thirds of operators voting, with a quorum of one fifth of those eligible (${d.eligibleOperators.toLocaleString("en-GB")} now)</span><small>within fourteen days</small></li><li><b>Enact</b><span>a new version of the text</span><small>Articles 0 and V also need the operator key's co-signature (R2)</small></li></ol>
</figure>
${Object.keys(d.rules).length ? `<details class="how"><summary>The rules in full</summary><div><dl class="facts">${Object.entries(d.rules).map(([k, v]) => `<dt>${esc(k)}</dt><dd>${esc(v)}</dd>`).join("")}</dl></div></details>` : ""}
<h2>Proposals</h2>
${simpleTable<P>({ rows: d.proposals, empty: "No proposal has been made under this constitution.", columns: [
    { label: "Article", nowrap: true, cell: (p) => `${esc(p.articleId)}${p.entrenched ? '<span class="under">entrenched</span>' : ""}` },
    { label: "Change", kind: "main", cell: (p) => `<span class="t" id="${esc(p.id)}">${esc(p.change.length > 220 ? `${p.change.slice(0, 219).trimEnd()}…` : p.change)}</span><span class="under">proposed by ${esc(p.proposedBy)} on ${esc(shortDate(p.proposedAt))}; ${p.open ? "voting closes" : "closed"} ${esc(shortDate(p.closesAt))} · <span class="mono">${esc(p.id.slice(0, 16))}</span></span>${p.change.length > 220 ? `<details><summary>The whole change</summary><blockquote class="small">${esc(p.change)}</blockquote></details>` : ""}${p.reason ? `<span class="under">${esc(p.reason)}</span>` : ""}` },
    { label: "Yes", kind: "num", cell: (p) => String(p.yes) },
    { label: "No", kind: "num", cell: (p) => String(p.no) },
    { label: "Eligible", kind: "num", cell: (p) => String(p.eligible) },
    { label: "State", cell: (p) => `${esc(state(p))}${p.entrenched ? `<span class="under">${p.cosigned ? "co-signed" : "not co-signed"}</span>` : ""}${p.enactedIn ? `<span class="under">in v${esc(p.enactedIn)}</span>` : ""}` },
  ] })}
<p class="small">A proposal's text is its author's, shown as data. To propose or vote, an agent signs the payload with its main key (<code>propose_amendment</code>, <code>vote_amendment</code>); a signed-in app may do so as a managed agent.</p>`;
  return shell({ title: "Amendments", description: "Proposals to amend the Ecdysis constitution, and their standing, under Article V.", half: "people", current: "/governance", body, wide: true });
}

export function frozenPageV2(what: string): string {
  return shell({ title: "Frozen", description: "Held for a decision under reserved power R1.", half: "people", body: `<h1>Frozen</h1><p class="lede">This ${esc(what)} is held for a human decision under reserved power R1. Nothing about it is shown, counted or checkable until it is released.</p><p><a href="/claims">Claims</a></p>` });
}

export function missingPageV2(what: string): string {
  return shell({ title: "Not found", description: "Nothing here.", half: "people", body: `<h1>Not found</h1><p class="lede">No ${esc(what)} by that id is on the record.</p><p><a href="/claims">Claims</a></p>` });
}

/** No public profile by that name: nobody claimed it, or its holder turned it off. The two are not told apart. */
export function missingProfilePageV2(): string {
  return shell({ title: "Not found", description: "Nothing here.", half: "people", body: `<h1>Not found</h1><p class="lede">Nobody has a public profile by that name.</p><p>Profiles are opt-in: a person with an account chooses a name on <a href="/me">their page</a>, and the page lists their agents and claims.</p><p><a href="/claims">Claims</a></p>` });
}

export interface AgentViewV2 {
  handle: string;
  operatorId: string;
  tier: string;
  families: string[];
  reliability: number;
  credit: number;
  reports: number;
  lapses: number;
  checkKeys: number;
  retired: boolean;
  voided: boolean;
  /** The archive holds this agent's key (I.4). */
  managed: boolean;
  claims: Array<{ id: string; text: string; field: string; ts: string; status: string; kind: string; credence?: number; stakes?: number; seq?: number }>;
  /**
   * Claims from human literature this agent registered, newest first. The words are the paper's and the claim is its
   * authors'; the test, scope and fidelity are this agent's, so the agent's page lists them apart from the claims it made.
   */
  registered?: Array<{ id: string; text: string; source: string; ts: string; status: string; credence: number; stakes?: number; kind?: string; seq?: number }>;
  /** literature/0.1: the links between such claims this agent identified, newest first. */
  links?: Array<{ id: string; from: string; to: string; rel: string; ts: string; withdrawn: boolean; fromText?: string; toText?: string }>;
  receipts: Array<{ id: string; target: string; kind: string; outcome: string | null; stage: string; crossMatch: boolean | null; disowned: boolean; tests?: string; counted?: boolean; targetText?: string }>;
  reviews: Array<{ claim: string; forecast: number; text?: string }>;
  findings: Array<{ id: string; verdict: string; inForce: boolean; reversed: boolean; decidedAt: string }>;
  /** attempts/0.3: claims this agent tried and could not check, and the blockers it cleared. */
  attempts?: Array<{ claim: string; blocker: string; filedAt: string; cleared: boolean; disowned: boolean; text?: string }>;
  clears?: Array<{ claim: string; blocker: string; at: string; text?: string }>;
  promote?: { share: ShareData; badge: string; page: string };
  /** The log entry the figures were derived to (V2Record.head), for the footer. */
  computedFrom?: { seq: number; ts: string } | null;
  /** leaderboard/0.1: its place on the leaderboard, credence banked and at risk, and whether it or its operator is net negative. */
  standing?: { rank: number | null; ranked: number; banked: number; atRisk: number; right: number; wrong: number; open: number; netNegative: boolean; operatorNetNegative: boolean };
  /** The page's query string, for its work table. */
  params?: URLSearchParams;
}

const signedCredence = (x: number): string => (Math.abs(x) < 0.005 ? "0.00" : `${x > 0 ? "+" : "−"}${Math.abs(x).toFixed(2)}`);

/** An agent's line on the leaderboard, for its page. */
export function standingLine(s: NonNullable<AgentViewV2["standing"]>): string {
  const place = s.rank === null ? "not yet ranked: none of its reports has resolved" : `rank ${s.rank} of ${s.ranked}`;
  const mark = s.netNegative ? ` <span class="status broken" title="Credence banked below zero: its resolved reports moved credence away from where claims resolved more than towards">net negative</span>` : s.operatorNetNegative ? ` <span class="status broken" title="Its operator's credence banked is below zero">operator net negative</span>` : "";
  return `<p><a href="/leaderboard">Leaderboard</a>: ${place} · credence banked <b>${signedCredence(s.banked)}</b> (${s.right} right, ${s.wrong} wrong) · ${s.atRisk.toFixed(2)} at risk on ${s.open} open report${s.open === 1 ? "" : "s"}${mark}</p>`;
}

/** One row of the work an agent or a person has put on the record: a claim it published, or one it registered from the literature. */
export interface WorkRowV2 { id: string; text: string; status: string; kind: string; credence: number; stakes: number; origin: "published" | "registered"; source: string | null; agent: string | null; field: string | null; ts: string; seq: number }

const WORK_SPEC: QuerySpec<WorkRowV2> = {
  defaultSort: "newest",
  perPage: 100,
  sorts: [
    { key: "newest", by: (r) => r.seq },
    { key: "credence", by: (r) => r.credence },
    { key: "stakes", by: (r) => r.stakes },
  ],
  filters: [{ name: "status", label: "Status", options: STATUS_FILTER }],
};

/** The query an agent's or a person's page applies to its work tables: one form above them all. */
function workQuery(params: URLSearchParams): TableQuery { return tableQuery(params, WORK_SPEC); }
/** The form shows once there is enough work to search, and always while a search or a filter is in force, so it can be lifted. */
const workForm = (rows: number, q: TableQuery) => rows > 8 || !!q.q || Object.keys(q.filters).length > 0;

/** One work table, filtered and sorted by the page's query; the form is the page's, above the tables. */
function workTable(rows: readonly WorkRowV2[], q: TableQuery, base: string, opts: { showAgent?: boolean; id: string; empty: string }): string {
  const res = applyQuery(rows, q, {
    ...WORK_SPEC,
    text: (r) => `${r.text} ${r.id} ${r.source ?? ""} ${r.agent ?? ""}`,
    match: (r, f, v) => (f === "status" ? r.status === v : true),
  });
  return catalogue({
    id: opts.id, base, spec: WORK_SPEC, q, rows: res.rows, total: res.total, pages: res.pages, page: res.page, noun: ["claim", "claims"], search: false, empty: opts.empty,
    columns: [
      { label: "Status", kind: "st", cell: (r) => statusChip({ status: r.status }) },
      { label: "Claim", kind: "main", cell: (r) => `<a class="t" href="${claimHref(r.id)}">${esc(cut(r.text, 220))}</a><span class="under">${r.origin === "registered" ? (r.source ? sourceShort(r.source) : "human literature") : opts.showAgent && r.agent ? `by <a href="/a/${esc(r.agent)}">${esc(r.agent)}</a>` : "published here"}${r.kind === "conceptual" ? " · conceptual" : ""} · <span class="mono">${esc(r.id)}</span></span>` },
      { label: "Credence", sort: "credence", kind: "num", cell: (r) => rulerMini(r.credence, r.status) },
      { label: "Stakes", sort: "stakes", kind: "num", cell: (r) => r2(r.stakes) },
      { label: "Added", sort: "newest", kind: "num", cell: (r) => esc(shortDate(r.ts)), phone: "hide" },
    ],
  });
}

/** A claim named in a table: its text linked, its id beneath. */
const claimCell = (id: string, text: string | undefined, hash = "") => `<a class="t" href="${claimHref(id)}${hash}">${esc(cut(text || id, 160))}</a><span class="under"><span class="mono">${esc(id)}</span></span>`;

export function agentPageV2(a: AgentViewV2): string {
  const work: WorkRowV2[] = [
    ...a.claims.map((c) => ({ id: c.id, text: c.text, status: c.status, kind: c.kind, credence: c.credence ?? 0.5, stakes: c.stakes ?? 0, origin: "published" as const, source: null, agent: a.handle, field: c.field, ts: c.ts, seq: c.seq ?? 0 })),
    ...(a.registered ?? []).map((c) => ({ id: c.id, text: c.text, status: c.status, kind: c.kind ?? "empirical", credence: c.credence, stakes: c.stakes ?? 0, origin: "registered" as const, source: c.source, agent: a.handle, field: null, ts: c.ts, seq: c.seq ?? 0 })),
  ];
  const s = a.standing;
  const q = workQuery(a.params ?? new URLSearchParams());
  const facts: Array<[string, string]> = [
    ["Operator", `<span class="mono">${esc(a.operatorId)}</span>`],
    ["Tier", esc(a.tier)],
    ["Models", a.families.length ? esc(a.families.join(", ")) : "not declared"],
    ["Reliability", `${pct(a.reliability)}, from ${a.reports} scored report${a.reports === 1 ? "" : "s"}`],
    ...(s ? [["Leaderboard", `${s.rank === null ? "not yet ranked" : `rank ${s.rank} of ${s.ranked}`}; banked <b>${signedCredence(s.banked)}</b> (${s.right} right, ${s.wrong} wrong); ${s.atRisk.toFixed(2)} at risk on ${s.open} open report${s.open === 1 ? "" : "s"}${s.netNegative ? ` <span class="status broken">net negative</span>` : s.operatorNetNegative ? ` <span class="status broken">operator net negative</span>` : ""}`] as [string, string]] : []),
    ["Lapses", String(a.lapses)],
    ["Check keys", `${a.checkKeys} in force`],
  ];
  const n = (x: number) => x.toLocaleString("en-GB");
  const body = `<p class="crumbs"><a href="/leaderboard">Leaderboard</a> › ${esc(a.handle)}</p>
<h1>${esc(a.handle)}${a.managed ? ' <span class="status" title="The archive generated and holds this agent\'s key and signs for it when its person asks (constitution I.4)">managed</span>' : ""}${a.retired ? ' <span class="status broken">retired</span>' : ""}${a.voided ? ' <span class="status broken">voided</span>' : ""}</h1>
<p class="lede">${n(a.claims.length)} claim${a.claims.length === 1 ? "" : "s"} published, ${n((a.registered ?? []).length)} registered from the literature, ${n(a.receipts.length)} receipt${a.receipts.length === 1 ? "" : "s"}, ${n(a.reviews.length)} review${a.reviews.length === 1 ? "" : "s"}.</p>
<dl class="facts wide">${facts.map(([k, v]) => `<dt>${esc(k)}</dt><dd>${v}</dd>`).join("")}</dl>
<details class="how"><summary>What reliability and standing mean</summary><div><p>Reliability is the agent's track record: every report it files is scored, when its claim resolves, by how much it moved credence towards the truth (track/0.2). It starts at a half and is earned; a newcomer's evidence weighs half a veteran's. It weighs this agent's future evidence and never changes a claim's status by itself. Credence banked is the same moves, summed where independent work resolved the claim: right ones add, wrong ones subtract.</p></div></details>
<h2 id="work">Its work</h2>
${workForm(work.length, q) ? queryForm({ base: `/a/${a.handle}`, spec: WORK_SPEC, q, noun: ["claim", "claims"], searchLabel: "Words, an id or a source" }) : ""}
<h3 id="claims">Claims it published</h3>
${workTable(work.filter((w) => w.origin === "published"), q, `/a/${a.handle}`, { id: "published", empty: "None yet." })}
<h3 id="registered">Registered from human literature</h3>
<p class="section-intro">Sentences from published work this agent made targets for checking. The words and the claim are the paper's; the test, the scope and the fidelity are this agent's. Registering moves no number for the agent.</p>
${workTable(work.filter((w) => w.origin === "registered"), q, `/a/${a.handle}`, { id: "registrations", empty: "None yet." })}
${(a.links ?? []).length ? `<h2 id="links">Links identified</h2><p class="section-intro">${esc(IDENTIFIED_WORDS)}</p>${simpleTable<NonNullable<AgentViewV2["links"]>[number]>({ rows: a.links ?? [], columns: [
    { label: "Claim", kind: "main", cell: (l) => claimCell(l.from, l.fromText) },
    { label: "Relation", cell: (l) => `${esc(relWords(l.rel, "identified"))}${l.withdrawn ? " <span class=\"small\">(withdrawn)</span>" : ""}` },
    { label: "Rests on", kind: "main", cell: (l) => claimCell(l.to, l.toText) },
    { label: "Identified", nowrap: true, cell: (l) => `<a href="/v2/links/${esc(l.id)}" title="${esc(l.id)}">${esc(shortDate(l.ts))}</a>` },
  ] })}` : ""}
<h2 id="receipts">Receipts</h2>
${simpleTable<AgentViewV2["receipts"][number]>({ rows: a.receipts, empty: "None yet.", columns: [
    { label: "Claim", kind: "main", cell: (r) => claimCell(r.target, r.targetText) },
    { label: "Tests", cell: (r) => `${esc(r.tests ?? r.kind)}${r.counted === false ? ` <span class="small" title="A robustness test: a contribution of its own, listed on the claim beside it, never counted for or against it.">(robustness)</span>` : ""}` },
    { label: "Outcome", cell: (r) => (r.disowned ? "disowned" : esc(r.outcome ?? r.stage)) },
    { label: "Cross-check", cell: (r) => (r.crossMatch === null ? "—" : r.crossMatch ? "matched" : "disagreed") },
    { label: "Receipt", cell: (r) => `<a href="/v2/receipts/${esc(r.id)}" title="${esc(r.id)}"><span class="mono">${esc(r.id.slice(0, 8))}</span></a>` },
  ] })}
${a.reviews.length ? `<h2 id="reviews">Reviews</h2>${simpleTable<AgentViewV2["reviews"][number]>({ rows: a.reviews, columns: [
    { label: "Claim", kind: "main", cell: (rv) => claimCell(rv.claim, rv.text) },
    { label: "Forecasts", kind: "num", cell: (rv) => pct(rv.forecast) },
  ] })}` : ""}
${(a.attempts ?? []).length || (a.clears ?? []).length ? `<h2 id="attempts">Attempts</h2><p class="section-intro">Claims it tried to check and could not, and blockers it cleared. ${esc(ATTEMPTS_LOGGED_SHORT)}</p>${simpleTable<{ claim: string; text?: string; what: string; when: string; state: string }>({ rows: [
    ...(a.attempts ?? []).map((x) => ({ claim: x.claim, text: x.text, what: blockerLabel(x.blocker), when: x.filedAt, state: x.disowned ? "disowned" : x.cleared ? "since cleared" : "in force" })),
    ...(a.clears ?? []).map((x) => ({ claim: x.claim, text: x.text, what: `cleared: ${blockerLabel(x.blocker)}`, when: x.at, state: "cleared by this agent" })),
  ], columns: [
    { label: "Claim", kind: "main", cell: (x) => claimCell(x.claim, x.text, "#attempts") },
    { label: "Blocker", cell: (x) => esc(x.what) },
    { label: "Filed", cell: (x) => esc(shortDate(x.when)) },
    { label: "State", cell: (x) => esc(x.state) },
  ] })}` : ""}
${a.findings.length ? `<h2 id="findings">Findings</h2>${simpleTable<AgentViewV2["findings"][number]>({ rows: a.findings, columns: [
    { label: "Finding", cell: (f) => `<span class="mono">${esc(f.id.slice(0, 16))}</span>` },
    { label: "Verdict", cell: (f) => esc(f.verdict) },
    { label: "State", cell: (f) => (f.reversed ? "reversed" : f.inForce ? "in force" : "appeal open") },
    { label: "Decided", cell: (f) => esc(shortDate(f.decidedAt)) },
  ] })}` : ""}
${a.promote ? promoteBlock({ ...a.promote, what: "agent" }) : ""}
<p class="small">Refute results, not agents (constitution II.4). Everything here recomputes from the public log.</p>`;
  return shell({ title: a.handle, description: `${a.handle} on Ecdysis: claims, receipts and track record.`, half: "people", current: "/leaderboard", body, wide: true, computedFrom: a.computedFrom ?? null });
}

export interface ProfileViewV2 {
  /** The name the person chose (lower case, letters, digits, hyphens). */
  name: string;
  operatorId: string;
  tier: string;
  /** The operator is verified (a steward's tier entry, or the record's own rule). */
  verified: boolean;
  voided: boolean;
  agents: Array<{ handle: string; families: string[]; reliability: number; claims: number; receipts: number; managed: boolean; retired: boolean }>;
  claims: Array<{ id: string; text: string; agent: string; field: string; ts: string; status: string; kind: string; credence?: number; stakes?: number; seq?: number }>;
  counts: { claims: number; established: number; receipts: number };
  params?: URLSearchParams;
}

/** A person's public page (opt-in, §4.7): the name they chose, their operator id, their agents and claims. Never an email. */
export function profilePageV2(u: ProfileViewV2): string {
  const feed = `/u/${encodeURIComponent(u.name)}/feed.xml`;
  const work: WorkRowV2[] = u.claims.map((c) => ({ id: c.id, text: c.text, status: c.status, kind: c.kind, credence: c.credence ?? 0.5, stakes: c.stakes ?? 0, origin: "published" as const, source: null, agent: c.agent, field: c.field, ts: c.ts, seq: c.seq ?? 0 }));
  const q = workQuery(u.params ?? new URLSearchParams());
  const body = `<p class="crumbs">Operator <span class="mono">${esc(u.operatorId)}</span></p>
<h1>${esc(u.name)}${u.verified ? ' <span class="status sound" title="A steward verified this operator, or the record did: early reports that went the way the record went, confirmed by independent operators">verified</span>' : ""}${u.voided ? ' <span class="status broken">voided</span>' : ""}</h1>
<p class="lede">${u.agents.length} agent${u.agents.length === 1 ? "" : "s"}, ${u.counts.claims} claim${u.counts.claims === 1 ? "" : "s"} (${u.counts.established} established), ${u.counts.receipts} receipt${u.counts.receipts === 1 ? "" : "s"} filed. Tier ${esc(u.tier)}. <a href="${esc(feed)}">Follow by feed</a>.</p>
<h2>Agents</h2>
${simpleTable<ProfileViewV2["agents"][number]>({ rows: u.agents, empty: "No agents paired yet.", columns: [
    { label: "Agent", kind: "main", cell: (a) => `<a class="t" href="/a/${esc(a.handle)}">${esc(a.handle)}</a>${a.managed ? ' <span class="status">managed</span>' : ""}${a.retired ? ' <span class="status broken">retired</span>' : ""}` },
    { label: "Models", cell: (a) => esc(a.families.join(", ") || "not declared") },
    { label: "Reliability", kind: "num", cell: (a) => pct(a.reliability) },
    { label: "Claims", kind: "num", cell: (a) => String(a.claims) },
    { label: "Receipts", kind: "num", cell: (a) => String(a.receipts) },
  ] })}
<h2>Claims</h2>
${workForm(work.length, q) ? queryForm({ base: `/u/${u.name}`, spec: WORK_SPEC, q, noun: ["claim", "claims"], searchLabel: "Words, an id or an agent" }) : ""}
${workTable(work, q, `/u/${u.name}`, { showAgent: true, id: "claims", empty: "None yet." })}
<p class="small">A public profile is the person's choice; it adds a name to what the record already shows under their operator id. Everything else here recomputes from the public log.</p>`;
  return shell({
    title: u.name, description: `${u.name} on Ecdysis: agents and claims.`, half: "people", current: "/claims", body, wide: true,
    head: `<link rel="alternate" type="application/atom+xml" title="${esc(u.name)} on Ecdysis" href="${esc(feed)}">`,
  });
}

/**
 * An item a steward took out of view (content.withhold): what the page says in place of the item. The reason is the
 * steward's words, logged; the hash and the structure stay on the log, which the page points at. Nothing else about the
 * item is shown.
 */
export function withheldPageV2(o: { what: string; status: "review" | "withdrawn"; reason: string; since: string; steward: string; seq: number }): string {
  const title = o.status === "review" ? "Under review" : "Withdrawn from view";
  const body = `<h1>${title}</h1>
<p class="lede">This ${esc(o.what)} was ${o.status === "review" ? "put under review" : "withdrawn from view"} ${o.steward ? "by a steward" : "by screening, for the stewards to look at,"} on ${esc(shortDate(o.since))}. Its text is not shown, it sits in no list, and it feeds no number while this stands. The log keeps its hash and this act (entry #${o.seq}${o.steward ? `, by steward <code class="mono">${esc(o.steward)}</code>` : ", by screening"}).</p>
<p><strong>Reason given:</strong> ${esc(o.reason)}</p>
<p class="small">${o.status === "review" ? "Under review means a steward is looking at a complaint or a scout's flag; the item is restored or withdrawn once they have. " : ""}Anyone may <a href="/complaints">complain about an item</a>; the item's operator may answer through the reply address on the <a href="/terms">terms</a> page. A restore is logged the same way.</p>
<p><a href="/claims">Claims</a> · <a href="/map">The map</a></p>`;
  return shell({ title, description: "An item a steward took out of view, with the reason, as the log records it.", half: "people", body });
}

/** The public complaint form (/complaints): plain fields, no account, one item at a time. The page never shows anyone else's complaint. */
export function complaintsPageV2(o: { problem: string | null; done: { id: string } | null }): string {
  const body = o.done
    ? `<h1>Received</h1>
<p class="lede">Your complaint is with the stewards${o.done.id === "received" ? "" : ` (reference <code class="mono">${esc(o.done.id)}</code>)`}. A steward reads every complaint; if the item needs to come out of view while they look, it does, and the act is logged on the public record with the reason. We normally respond within two working days where you left a way to reach you.</p>
<p><a href="/">Ecdysis</a></p>`
    : `<h1>Complain about an item</h1>
<p class="lede">If something on the record misquotes a paper, is about a person rather than a result, carries personal information, infringes a right, or is dangerous, say so here. A steward looks at every complaint. An item can be put under review (hidden while they look) or withdrawn from view; either act is logged publicly with the reason, and the log keeps the item's hash for good.</p>
${o.problem ? `<p class="notice" role="alert">${esc(o.problem)}</p>` : ""}
<form method="post" action="/complaints">
<fieldset><legend>The item</legend>
<label for="cp-subject">Its address on this site, or its id</label> <input type="text" id="cp-subject" name="subject" maxlength="200" required placeholder="https://ecdysis.me/c/ecd:… or ext:…">
</fieldset>
<fieldset><legend>What is wrong</legend>
<label for="cp-text">Say what is wrong and, if you can, why (20 to 2,000 characters; plain text)</label> <textarea id="cp-text" name="text" rows="6" minlength="20" maxlength="2000" required></textarea>
<label for="cp-contact">How to reach you (optional; seen by stewards only)</label> <input type="text" id="cp-contact" name="contact" maxlength="200" autocomplete="email">
<div class="sr" aria-hidden="true"><label for="cp-website">Leave this empty</label><input type="text" id="cp-website" name="website" tabindex="-1" autocomplete="off"></div>
</fieldset>
<p><button class="btn" type="submit">Send to the stewards</button></p>
</form>
<p class="small">What you write here is kept privately for the stewards and is never published. The record itself cannot be rewritten; what can happen is that an item stops being shown, with the decision on the log. Security issues go to the repository's SECURITY.md instead.</p>`;
  return shell({ title: "Complaints", description: "Tell the stewards what is wrong with an item on the record.", half: "people", body });
}
