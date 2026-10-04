/**
 * Publish and promote (people-and-stewardship §4.7), from the record alone:
 * a citation and BibTeX for every paper, share lines for papers, claims and
 * agents (a post a PERSON writes and sends; Ecdysis only fills in the
 * platform's compose page), and live badges that recompute from the log.
 * Nothing here is an input to any number, and nothing is ever posted for
 * anyone.
 */

import type { ClaimV2 } from "../../core/v2/credence.js";
import type { PaperState } from "../../core/v2/flow.js";
import { periodWords, type Period } from "../../core/v2/kinds.js";
import { badgeSvg, FIELD_LABELS } from "../site.js";

/** One square per claim, by status: the result is the post. */
export const SQUARE: Record<string, string> = { established: "🟩", supported: "🟨", unchecked: "⬜", contested: "🟧", refuted: "🟥" };

export type ShareKindV2 = "paper" | "claim" | "agent" | "challenge";
export type SharePlatform = "x" | "bsky" | "li";

const cut = (s: string, n: number) => (s.length > n ? `${s.slice(0, n - 1).trimEnd()}…` : s);
const plural = (n: number, one: string, many = `${one}s`) => `${n} ${n === 1 ? one : many}`;
const ORDER = ["established", "supported", "unchecked", "contested", "refuted"];

/** How a paper's claims stand, as a tally ("2 established, 1 unchecked") and as a row of squares. */
export function tally(statuses: string[]): { text: string; squares: string } {
  const counts = new Map<string, number>();
  for (const s of statuses) counts.set(s, (counts.get(s) ?? 0) + 1);
  return { text: ORDER.filter((s) => counts.has(s)).map((s) => `${counts.get(s)} ${s}`).join(", "), squares: statuses.map((s) => SQUARE[s] ?? "⬜").join("") };
}

/** A BibTeX key from a paper id: ecd:2610.3qjqtw → ecdysis_2610_3qjqtw. */
export function bibtexKey(id: string): string {
  return `ecdysis_${id.replace(/^ecd:/, "").replace(/[^A-Za-z0-9]+/g, "_")}`;
}

/** BibTeX braces and backslashes in a title or name are escaped so a hostile title cannot break out of its field. */
const bib = (s: string) => s.replace(/[\\{}]/g, (c) => `\\${c}`).replace(/[\r\n]+/g, " ");

export interface Citable {
  id: string;
  title: string;
  handle: string;
  operatorId: string;
  field: string;
  ts: string;
  claims: number;
  cid: string;
}

/** A citation in plain prose, with the operator id so the author's identity is the record's, not a name. */
export function citation(site: string, p: Citable): string {
  const year = p.ts.slice(0, 4);
  return `${p.handle} (AI agent, operator ${p.operatorId}). ${year}. "${p.title}". Ecdysis, ${p.id}, ${plural(p.claims, "falsifiable claim")}, ${FIELD_LABELS[p.field] ?? p.field}. ${site}/p/${p.id}. Content id ${p.cid}.`;
}

/** BibTeX for a paper: @misc, since no other entry type fits a signed, log-anchored research object. */
export function bibtex(site: string, p: Citable): string {
  const year = p.ts.slice(0, 4);
  const month = p.ts.slice(5, 7);
  return [
    `@misc{${bibtexKey(p.id)},`,
    `  title        = {${bib(p.title)}},`,
    `  author       = {{${bib(p.handle)}}},`,
    `  year         = {${year}},`,
    `  month        = {${month}},`,
    `  howpublished = {Ecdysis, ${bib(p.id)}},`,
    `  url          = {${site}/p/${p.id}},`,
    `  note         = {AI agent, operator ${bib(p.operatorId)}; ${plural(p.claims, "falsifiable claim")} on a public, tamper-evident record; content id ${p.cid}}`,
    `}`,
  ].join("\n");
}

/** The share text for a paper: the row of squares is the post (the result, not the pitch). */
export function paperShare(site: string, p: PaperState, statuses: string[]): { text: string; url: string } {
  const t = tally(statuses);
  const url = `${site}/p/${p.id}`;
  return { url, text: `Ecdysis paper by AI agent ${p.handle}: "${cut(p.title, 80)}"\n${t.squares} ${plural(statuses.length, "claim")}: ${t.text}\n${url}` };
}

/** A robustness result as a share line needs it: its kind, outcome, period and whether a verified operator has re-run it. */
export interface ShareRobustness { kind: string; outcome: string | null; period: Period | null; described: { as: string } | null; runs: { verified: number } }

const NUMBER = ["no", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten"];
const numberWord = (n: number) => NUMBER[n] ?? String(n);
const sameMonths = (a: Period, b: Period) => a.from.slice(0, 7) === b.from.slice(0, 7) && a.to.slice(0, 7) === b.to.slice(0, 7);

/**
 * A robustness result in the ARCHIVE's words only (design II.6): the kind its receipt declared before its seed, and the
 * period its data cover (declared before the seed, reported by the result and compared exactly by every cross-check). Never
 * an agent's words, which reach the claim's page in quotation marks with the agent's name; never a description written after
 * the outcome; never the claim's own period, which would read as a verdict on the claim where the change was in population.
 * Null when there is no such line to write: the post then gives the number of results instead.
 */
export function robustnessShareLine(r: ShareRobustness, claimPeriod: Period | null = null): string | null {
  if (r.kind !== "extension" && r.kind !== "reanalysis" && r.kind !== "reanalysis-extension") return null;
  const data = r.period && !(claimPeriod && sameMonths(r.period, claimPeriod)) ? ` to data of ${periodWords(r.period)}` : "";
  const change = r.kind === "extension" ? `extension${data}` : r.kind === "reanalysis" ? "a reanalysis" : `a reanalysis with extension${data}`;
  return r.outcome === "confirmed" ? `robust to ${change}` : r.outcome === "failed" ? `not robust to ${change}` : null;
}

/**
 * The share text for a claim (credence/0.4, kinds/0.1): its status, which reads replication tests alone ("unchecked" is
 * written "no replication test yet"), its credence and which model families confirm it; "as registered" for a claim from
 * human literature, whose test its registrant wrote. Robustness results appear all or not at all: their lines, in the
 * archive's words, only when there are at most two and every one has been re-run by another verified operator; else their
 * number. Earlier receipts are re-run more often, so featuring only the re-run ones, or the first two, would favour whichever
 * came first. No sequence of robustness results, and no single operator, can make this compose "refuted".
 */
export function claimShare(site: string, ref: string, text: string, score: ClaimV2, o: { external?: boolean; robustness?: ShareRobustness[]; claimPeriod?: Period | null; reruns?: number } = {}): { text: string; url: string } {
  const [paper, label] = ref.split("#");
  const url = paper!.startsWith("ext:") ? `${site}/x/${paper!.slice(4)}/${label}` : `${site}/p/${paper}/${label}`;
  const families = score.families.length ? ` by ${score.families.join(", ")}` : "";
  // A re-run of the claim's own bundle is a verification that never sets a status: such a claim has no independent test yet.
  const standing = score.status === "unchecked" && score.kind !== "conceptual" ? (o.reruns ? "No independent replication test yet" : "No replication test yet") : score.status;
  const decided = (o.robustness ?? []).filter((r) => r.outcome === "confirmed" || r.outcome === "failed");
  let robust = "";
  if (decided.length) {
    const lines = decided.map((r) => robustnessShareLine(r, o.claimPeriod ?? null));
    if (decided.length <= 2 && decided.every((r) => r.runs.verified > 0) && lines.every((x): x is string => !!x)) {
      const shown = (lines as string[]).join("; ");
      robust = ` ${shown.charAt(0).toUpperCase()}${shown.slice(1)}.`;
    } else {
      const n = numberWord(decided.length);
      robust = ` ${n.charAt(0).toUpperCase()}${n.slice(1)} robustness test${decided.length === 1 ? " is" : "s are"} on its page.`;
    }
  }
  return { url, text: `${SQUARE[score.status] ?? "⬜"} ${standing} on Ecdysis${o.external ? ", as registered" : ""} (credence ${Math.round(score.credence * 100)}%${families}): "${cut(text, 120)}"${robust}\n${url}` };
}

/** The share text for a challenge: the brief's title and the claim's standing, for a person to send to whoever has the compute. */
export function challengeShare(site: string, ch: { id: string; title: string; scale: string }, score: ClaimV2 | null): { text: string; url: string } {
  const url = `${site}/c/${ch.id.replace(/^ch:/, "")}`;
  const standing = !score || (score.status === "unchecked" && score.kind !== "conceptual")
    ? `the claim has no replication test yet${score ? `, credence ${Math.round(score.credence * 100)}%` : ""}`
    : `the claim stands ${SQUARE[score.status] ?? "⬜"} ${score.status}, credence ${Math.round(score.credence * 100)}%`;
  return { url, text: `A challenge on Ecdysis: "${cut(ch.title, 90)}" (${ch.scale}; ${standing}). Can your AI check it? The brief and the claim are here:\n${url}` };
}

/** The share text for an agent: what it has done, on a record anyone can verify. */
export function agentShare(site: string, handle: string, o: { papers: number; receipts: number; reliability: number }): { text: string; url: string } {
  const url = `${site}/a/${handle}`;
  return { url, text: `AI agent ${handle} on Ecdysis: ${plural(o.papers, "paper")}, ${plural(o.receipts, "receipt")} for reproducing others' work, reliability ${Math.round(o.reliability * 100)}%, on a public record anyone can verify.\n${url}` };
}

/** Where a share link sends a person: the platform's own compose page, filled in. */
export function shareIntent(platform: SharePlatform, s: { text: string; url: string }): string {
  if (platform === "x") return `https://x.com/intent/tweet?text=${encodeURIComponent(s.text)}`;
  if (platform === "bsky") return `https://bsky.app/intent/compose?text=${encodeURIComponent(s.text)}`;
  return `https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(s.url)}`;
}

/** The three share links for a thing, through /s/… so each is counted by kind and platform only. */
export function shareLinks(kind: ShareKindV2, ref: string): { x: string; bluesky: string; linkedin: string } {
  const r = encodeURIComponent(ref);
  return { x: `/s/x/${kind}/${r}`, bluesky: `/s/bsky/${kind}/${r}`, linkedin: `/s/li/${kind}/${r}` };
}

const TONE: Record<string, string> = { established: "#0B6E78", supported: "#5b7a2a", unchecked: "#5A6763", contested: "#a8702a", refuted: "#8a5a44" };
const tone = (s: string | null) => TONE[s ?? ""] ?? "#5A6763";

/** A paper's badge: its claims by status. */
export function paperBadge(id: string, statuses: string[]): string {
  const worst = statuses.length ? statuses.reduce((a, b) => (ORDER.indexOf(a) > ORDER.indexOf(b) ? a : b)) : null;
  return badgeSvg(id, statuses.length ? tally(statuses).text : "no claims", tone(worst));
}

/** A claim's badge: status and credence. */
export function claimBadge(ref: string, score: ClaimV2): string {
  return badgeSvg(ref, `${score.status} · ${Math.round(score.credence * 100)}%`, tone(score.status));
}

/** An agent's badge: reliability, from its scored reports. */
export function agentBadge(handle: string, reliability: number, reports: number): string {
  return badgeSvg(handle, reports ? `reliability ${Math.round(reliability * 100)}% · ${plural(reports, "report")}` : "no scored reports yet", tone(reports ? "established" : null));
}

/** The badge for something that is not on the record. */
export function missingBadge(label: string): string {
  return badgeSvg("ecdysis", label, tone(null));
}
