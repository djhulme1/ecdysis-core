/**
 * Identified links (literature/0.1): the dependencies between claims from
 * human literature, identified by agents reading the papers (Ecdysis v2;
 * design: claude/ecdysis-literature-network-design.md; Daniel, 5 October
 * 2026: "Does it mean adding a new type of claims tag, like 'identified'?",
 * and "Bombus shouldn't check claims, just start creating the dependency map,
 * and allowing us to get data on the site to help direct agents").
 *
 * A claim published here names what it builds on when it is published, with
 * the basis its author relied on (reproduced or reviewed). A claim registered
 * from human literature names nothing: its paper rests on earlier papers, but
 * nobody on the record wrote it. An agent that reads the citing paper can
 * IDENTIFY such a dependency, quoting the citing paper's own sentence as its
 * evidence. That is a third way of knowing a link, after reviewed and
 * reproduced, and the link carries the basis "identified".
 *
 *   claim.link    {id, from, to, rel, basis: "identified", quote, where?, handle, operatorId, models?}
 *   claim.unlink  {link, reason, handle, operatorId}
 *
 *   from   the literature claim that rests on another: the citing paper's;
 *   to     the literature claim it rests on: the cited paper's;
 *   rel    extends (builds on its result) or method (uses its method): a
 *          DEPENDENCY; replicates or refutes: the literature's own evidence
 *          about the claim, recorded and shown, never reliance. Background is
 *          no link: a mention is not a dependency.
 *
 * The id is "lnk:" and 16 hex characters of the SHA-256 of {from, to, rel,
 * operatorId}: one operator identifies a link once, and a second operator
 * identifying the same link CORROBORATES it, under an id of its own. A link
 * is withdrawn, never edited, by an agent of the operator that identified it
 * (claim.unlink, with the reason, on the log), and a withdrawn link stays
 * withdrawn. The links stay a DAG: one whose `to` already rests on its
 * `from` through links in force would close a cycle and is refused (by the
 * service before writing, and by the fold for any entry that got past it).
 *
 * What a link does is steer, and nothing else. RELIANCE N(c) is how much of
 * the literature rests on a claim through identified dependencies, through
 * every path, halved for each step away and weighed by who identified each
 * step:
 *
 *   N(c) = Σ over the claims d resting on c of  w(d, c) · (1 + ½ · N(d))
 *
 * where w(d, c) is the tier weight (verified 1, account ½, unverified ¼, as
 * use is weighed) of the best operator in force that identified a dependency
 * of d on c. Dependencies that no verified operator has identified count at
 * their weight and, all together, never add more than OTHER_CAP to a claim's
 * reliance: a free identity filing a thousand links moves the queues by at
 * most two units of stakes, the way everything from operators who are not
 * verified never moves a credence by more than 3:1. Reliance enters stakes
 * (stakes/0.2: S = U + log2(1 + R) + log2(1 + N)), which rank what is worth
 * checking; never credence, a status, a threshold or anyone's record. A link
 * moves no credence because it is an agent's reading of someone else's paper,
 * not a reliance the agent stands behind: if links moved credence, linking a
 * claim to a refuted one would lower it by assertion rather than by work.
 *
 * Pure: no runtime dependencies, no environment.
 */

import { CREDENCE_V2_PARAMS, type Tier } from "./credence.js";

export const LINKS_VERSION = "links/0.1";

/** The relations a link may carry. Background is no link. */
export const LINK_RELS = ["extends", "method", "replicates", "refutes"] as const;
export type LinkRel = (typeof LINK_RELS)[number];
/** The relations that are dependencies: the claim rests on the other, so they count towards reliance. */
export const RESTS_ON: ReadonlySet<LinkRel> = new Set<LinkRel>(["extends", "method"]);

/** A link's id: "lnk:" and 16 hex characters. */
export const LINK_ID = /^lnk:[0-9a-f]{16}$/;
/** The evidence: the citing paper's own sentence, verbatim. */
export const LINK_EVIDENCE = { min: 20, max: 600 } as const;
/** Where in the citing paper the sentence is: a section, or "Semantic Scholar context". */
export const LINK_WHERE = { min: 2, max: 80 } as const;
/** Why a link is withdrawn, on the log. */
export const UNLINK_REASON = { min: 10, max: 300 } as const;

export const RELIANCE_PARAMS = {
  /** Each step away from a claim counts for this share of the step before it. */
  decay: 0.5,
  /** Dependencies no verified operator has identified add, all together, at most this much to a claim's reliance. */
  otherCap: 3,
} as const;

const CLAIM_ID = /^(ecd|ext):[0-9a-f]{16}$/;
const ISO = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,3})?Z$/;
const HANDLE = /^[A-Za-z0-9][A-Za-z0-9-]{1,39}$/;
/** Characters that make a text lie to its reader: bidirectional controls, zero-width and invisible ones, tags, and controls other than newline and tab. */
const UNSAFE = /[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F-\u009F­؜​-‏‪-‮⁠-⁩﻿]|[\u{E0000}-\u{E007F}]/u;

export interface LinkPayload {
  protocol: "ecdysis/0.2";
  type: "claim.link";
  /** The citing paper's claim: the one that rests on the other. */
  from: string;
  /** The cited paper's claim: the one it rests on. */
  to: string;
  rel: LinkRel;
  basis: "identified";
  evidence: { quote: string; where?: string };
  models?: string[];
  agent: { handle: string; publicKey: string };
  ts: string;
}

export interface UnlinkPayload {
  protocol: "ecdysis/0.2";
  type: "claim.unlink";
  /** The link's id, as its 201 gave it. */
  link: string;
  reason: string;
  agent: { handle: string; publicKey: string };
  ts: string;
}

/** Every field a link may carry: anything else is refused by name, so a misspelt field is never silently dropped. */
export const LINK_FIELDS: readonly string[] = ["protocol", "type", "from", "to", "rel", "basis", "evidence", "models", "agent", "ts"];

type Res<T> = { ok: true; value: T } | { ok: false; errors: string[] };

function words(v: unknown, name: string, min: number, max: number, errors: string[]): void {
  if (typeof v !== "string" || v.trim().length < min || v.length > max) { errors.push(`${name}: ${min} to ${max} characters`); return; }
  if (UNSAFE.test(v)) errors.push(`${name}: no control, zero-width or bidirectional characters`);
}
function agentOk(v: unknown, errors: string[]): void {
  const a = v as { handle?: unknown; publicKey?: unknown } | null;
  if (!a || typeof a !== "object" || typeof a.handle !== "string" || !HANDLE.test(a.handle) || typeof a.publicKey !== "string" || a.publicKey.length < 20) errors.push("agent: {handle, publicKey}");
}

export function validateLinkV2(p: unknown): Res<LinkPayload> {
  const x = p as Partial<LinkPayload> | null;
  if (!x || typeof x !== "object" || Array.isArray(x)) return { ok: false, errors: ["payload: an object"] };
  const errors: string[] = [];
  for (const k of Object.keys(x)) if (!LINK_FIELDS.includes(k)) errors.push(`${k}: not a field of a link (a link carries ${LINK_FIELDS.filter((f) => f !== "protocol" && f !== "type").join(", ")})`);
  if (x.protocol !== "ecdysis/0.2") errors.push('protocol: "ecdysis/0.2"');
  if (x.type !== "claim.link") errors.push('type: "claim.link"');
  // Whether an end is a claim from human literature on the record is the service's to say (422), with the record in hand.
  const end = (v: unknown, name: string, what: string) => {
    if (typeof v !== "string" || !CLAIM_ID.test(v)) errors.push(`${name}: ${what}, a claim from human literature on the record (ext: and 16 hex characters)`);
  };
  end(x.from, "from", "the claim that rests on the other (the citing paper's)");
  end(x.to, "to", "the claim it rests on (the cited paper's)");
  if (typeof x.from === "string" && x.from === x.to) errors.push("to: a claim cannot rest on itself");
  if (!(LINK_RELS as readonly unknown[]).includes(x.rel)) errors.push(`rel: ${LINK_RELS.join(", ")} (extends and method are dependencies; replicates and refutes record the literature's own evidence; a mention is not a link)`);
  if (x.basis !== "identified") errors.push('basis: "identified" (read from the citing paper, not reviewed or reproduced)');
  const ev = x.evidence as { quote?: unknown; where?: unknown } | undefined;
  if (!ev || typeof ev !== "object" || Array.isArray(ev)) errors.push(`evidence: {quote (the citing paper's own sentence that relies on the cited work, verbatim, ${LINK_EVIDENCE.min} to ${LINK_EVIDENCE.max} characters), where? (the section, or "Semantic Scholar context")}`);
  else {
    for (const k of Object.keys(ev)) if (k !== "quote" && k !== "where") errors.push(`evidence.${k}: not a field of the evidence (quote, where)`);
    words(ev.quote, "evidence.quote", LINK_EVIDENCE.min, LINK_EVIDENCE.max, errors);
    if (ev.where !== undefined) words(ev.where, "evidence.where", LINK_WHERE.min, LINK_WHERE.max, errors);
  }
  if (x.models !== undefined && (!Array.isArray(x.models) || x.models.length === 0 || x.models.length > 8 || x.models.some((m) => typeof m !== "string" || m.trim().length < 2 || m.length > 80))) errors.push("models: optional; 1 to 8 model names of 2 to 80 characters");
  agentOk(x.agent, errors);
  if (typeof x.ts !== "string" || !ISO.test(x.ts)) errors.push("ts: ISO-8601 UTC");
  return errors.length ? { ok: false, errors } : { ok: true, value: x as LinkPayload };
}

export function validateUnlinkV2(p: unknown): Res<UnlinkPayload> {
  const x = p as Partial<UnlinkPayload> | null;
  if (!x || typeof x !== "object" || Array.isArray(x)) return { ok: false, errors: ["payload: an object"] };
  const errors: string[] = [];
  if (x.protocol !== "ecdysis/0.2") errors.push('protocol: "ecdysis/0.2"');
  if (x.type !== "claim.unlink") errors.push('type: "claim.unlink"');
  if (typeof x.link !== "string" || !LINK_ID.test(x.link)) errors.push("link: the link's id (lnk: and 16 hex characters), as its 201 gave it");
  words(x.reason, "reason", UNLINK_REASON.min, UNLINK_REASON.max, errors);
  agentOk(x.agent, errors);
  if (typeof x.ts !== "string" || !ISO.test(x.ts)) errors.push("ts: ISO-8601 UTC");
  return errors.length ? { ok: false, errors } : { ok: true, value: x as UnlinkPayload };
}

/** A link's id from the SHA-256 (hex) of {from, to, rel, operatorId}. */
export function linkIdOf(hash: string): string {
  return `lnk:${hash.slice(0, 16)}`;
}

/** One identification, as the log carries it, with what the derivation adds. */
export interface LinkState {
  id: string;
  from: string;
  to: string;
  rel: LinkRel;
  /** The citing paper's sentence, and where in it. */
  quote: string;
  where: string | null;
  handle: string;
  operatorId: string;
  families: string[];
  seq: number;
  ts: string;
  /** The key that signed it: the identifying agent's main key (a check key signs reports only). */
  key: string;
  /** The identifying operator's tier, once tiers are known. */
  tier: Tier;
  /** Signed after its key's declared compromise: feeds no number, like a disowned report. */
  disowned: boolean;
  /** Withdrawn by its operator (claim.unlink): kept on the log and shown as withdrawn, counted nowhere. */
  withdrawn: { seq: number; ts: string; reason: string; handle: string } | null;
}

/** The identifications of one link (from, to, rel) in force and in view, grouped: what the pages, the line and reliance read. */
export interface LinkEdge {
  from: string;
  to: string;
  rel: LinkRel;
  basis: "identified";
  /** Each operator's identification, oldest first. */
  by: Array<{ id: string; handle: string; operatorId: string; tier: Tier; quote: string; where: string | null; seq: number; ts: string }>;
  /** The best tier weight among them: what a dependency weighs in reliance. */
  weight: number;
  /** A verified operator identified it. */
  verified: boolean;
  /** The first identification's position on the log. */
  seq: number;
}

/**
 * Whether a link from `from` to `to` would close a cycle: whether `to` already rests on `from` through the links in force
 * (`restsOn` gives the claims a claim rests on through them). Iterative, so a long chain cannot exhaust the stack.
 */
export function closesCycle(restsOn: (claim: string) => Iterable<string>, from: string, to: string): boolean {
  if (from === to) return true;
  const seen = new Set<string>([to]);
  const stack = [to];
  while (stack.length) {
    const at = stack.pop()!;
    for (const next of restsOn(at)) {
      if (next === from) return true;
      if (!seen.has(next)) { seen.add(next); stack.push(next); }
    }
  }
  return false;
}

/**
 * The links that count, grouped by (from, to, rel): not withdrawn, not disowned, not identified by a voided operator, and in
 * view (the link itself and both its claims). Ordered by first identification.
 */
export function linkEdgesOf(links: Iterable<LinkState>, o: { held: (subject: string) => boolean; voided: (operatorId: string) => boolean }): LinkEdge[] {
  const groups = new Map<string, LinkEdge>();
  const sorted = [...links].sort((a, b) => a.seq - b.seq);
  for (const l of sorted) {
    if (l.withdrawn || l.disowned || o.voided(l.operatorId) || o.held(l.id) || o.held(l.from) || o.held(l.to)) continue;
    const key = `${l.from}|${l.to}|${l.rel}`;
    const g = groups.get(key) ?? { from: l.from, to: l.to, rel: l.rel, basis: "identified" as const, by: [], weight: 0, verified: false, seq: l.seq };
    g.by.push({ id: l.id, handle: l.handle, operatorId: l.operatorId, tier: l.tier, quote: l.quote, where: l.where, seq: l.seq, ts: l.ts });
    g.weight = Math.max(g.weight, CREDENCE_V2_PARAMS.tier[l.tier]);
    g.verified = g.verified || l.tier === "verified";
    groups.set(key, g);
  }
  return [...groups.values()].sort((a, b) => a.seq - b.seq);
}

/**
 * Reliance of every claim with something resting on it through identified dependencies (extends, method): N(c) = Σ_{d resting
 * on c} w(d, c)·(1 + decay·N(d)), counting a pair (d, c) once with its best weight whatever relations join them. Computed
 * twice: once over the dependencies a verified operator identified (weight 1), once over all of them (at their weights); the
 * difference, what only operators who are not verified identified, adds at most otherCap. Claims nothing rests on are absent.
 * Dependants are taken before what they rest on (Kahn's order), so the computation is linear in the links and never recurses;
 * a cycle, which the fold never lets in, would leave its claims at 0.
 */
export function relianceOf(edges: readonly LinkEdge[], params: { decay?: number; otherCap?: number } = {}): Map<string, number> {
  const decay = params.decay ?? RELIANCE_PARAMS.decay;
  const cap = params.otherCap ?? RELIANCE_PARAMS.otherCap;
  const all = new Map<string, Map<string, number>>();
  const verified = new Map<string, Map<string, number>>();
  const put = (m: Map<string, Map<string, number>>, from: string, to: string, w: number) => {
    const into = m.get(to) ?? new Map<string, number>();
    into.set(from, Math.max(into.get(from) ?? 0, w));
    m.set(to, into);
  };
  for (const e of edges) {
    if (!RESTS_ON.has(e.rel) || e.from === e.to || !(e.weight > 0)) continue;
    put(all, e.from, e.to, e.weight);
    if (e.verified) put(verified, e.from, e.to, 1);
  }
  const pass = (into: Map<string, Map<string, number>>): Map<string, number> => {
    // into: c → (d → w) for every d resting on c. Kahn: a claim is ready once every claim resting on it is done.
    const restsOn = new Map<string, string[]>();
    const waiting = new Map<string, number>();
    const nodes = new Set<string>();
    for (const [c, ds] of into) {
      nodes.add(c);
      waiting.set(c, (waiting.get(c) ?? 0) + ds.size);
      for (const d of ds.keys()) {
        nodes.add(d);
        const list = restsOn.get(d);
        if (list) list.push(c); else restsOn.set(d, [c]);
      }
    }
    const n = new Map<string, number>();
    const ready = [...nodes].filter((x) => !(waiting.get(x) ?? 0)).sort();
    while (ready.length) {
      const d = ready.pop()!;
      for (const c of restsOn.get(d) ?? []) {
        const w = into.get(c)!.get(d)!;
        n.set(c, (n.get(c) ?? 0) + w * (1 + decay * (n.get(d) ?? 0)));
        const left = (waiting.get(c) ?? 0) - 1;
        waiting.set(c, left);
        if (left === 0) ready.push(c);
      }
    }
    return n;
  };
  const nAll = pass(all);
  const nVerified = pass(verified);
  const out = new Map<string, number>();
  for (const [c, x] of nAll) {
    const v = nVerified.get(c) ?? 0;
    const total = v + Math.min(cap, Math.max(0, x - v));
    if (total > 0) out.set(c, total);
  }
  return out;
}
