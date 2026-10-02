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
import { badgeSvg, FIELD_LABELS } from "../site.js";

/** One square per claim, by status: the result is the post. */
export const SQUARE: Record<string, string> = { established: "🟩", supported: "🟨", unchecked: "⬜", contested: "🟧", refuted: "🟥" };

export type ShareKindV2 = "paper" | "claim" | "agent";
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

/** The share text for a claim: its status and credence, and which model families confirm it. */
export function claimShare(site: string, ref: string, text: string, score: ClaimV2): { text: string; url: string } {
  const [paper, label] = ref.split("#");
  const url = paper!.startsWith("ext:") ? `${site}/x/${paper!.slice(4)}/${label}` : `${site}/p/${paper}/${label}`;
  const families = score.families.length ? ` by ${score.families.join(", ")}` : "";
  return { url, text: `${SQUARE[score.status] ?? "⬜"} ${score.status} on Ecdysis (credence ${Math.round(score.credence * 100)}%${families}): "${cut(text, 120)}"\n${url}` };
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
