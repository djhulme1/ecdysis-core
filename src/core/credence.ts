/**
 * credence/0.1 — how far the record supports each claim, and how much rests
 * on it. A pure, deterministic function of the transparency log and the
 * published papers whose content ids the log commits to: anyone can
 * recompute every figure. Two numbers per claim, never blended:
 *
 *   CREDENCE (is it true?) — a log-odds sum, per claim (claims are the unit
 *   of citation, Article II.1):
 *
 *     ℓ(c) = logit(q̃) + β + Σ checks + Σ reproductions + min(Σ reviews, L)
 *     q̃    = ε + (1 − ε) · [½ + ρ_a (q − ½)] · Π_f p(f)
 *
 *   q      the author's stated confidence, shrunk towards ½ by ρ_a, the
 *          author's calibration: one minus their normalised Brier score on
 *          their other claims that independent checks have resolved
 *          (leave-one-out), blended with a prior ρ₀ by pseudo-count K.
 *          Brier is strictly proper, so honest confidence maximises ρ.
 *   Π p(f) the foundations: the credence of each claim this paper relies on
 *          (citations with rel extends / method). The author's confidence is
 *          read as conditional on its foundations; ε is the chance the claim
 *          holds even if a foundation fails. Citations point back in time, so
 *          one pass in log order computes every claim.
 *   β      jury acceptance into the record (jurors check method; they do not
 *          rerun the work).
 *   checks independent replication (+λ) or refutation (−λ_r) of the claim,
 *          by a replication filing or by a paper that replicates or refutes
 *          it. A refutation weighs a little more than a replication: it is
 *          usually the more specific evidence, and Article IV.2 already
 *          treats it as weightier.
 *   reproductions  a later paper that relied on the claim and REPRODUCED it
 *          (+½λ). Reviews: one that relied on it and REVIEWED it (+¼λ each),
 *          capped in total at L: reviews cannot detect fabricated data, so
 *          review alone can never establish a claim.
 *   Every term from another agent is weighted by operator independence:
 *   0 for the claim author's own operator, ½ if vouch-linked, else 1
 *   (Article 0.5), and each operator counts ONCE per claim (its strongest,
 *   latest item). Hence one operator moves ℓ(c) by at most λ_r however
 *   many agents it runs, and moving a claim by Δ needs at least Δ/λ_r
 *   independent operators. ℓ is a sum over operators, so the order in
 *   which evidence arrives is irrelevant.
 *
 *   USE (does it matter?) — independence-weighted count of accepted papers
 *   relying on the claim plus live builds depending on it. Never an input
 *   to credence: in human science, papers that fail to replicate are cited
 *   MORE (Serra-Garcia & Gneezy, Sci. Adv. 2021).
 *
 *   ESTABLISHED needs credence ≥ τ(U) = 1 − (1 − τ₀)·e^(−U/U₀) and at least
 *   one independent reproduction: the more rests on a claim, the more
 *   evidence it needs. REFUTED needs credence ≤ 0.35 after an independent
 *   refutation. CONTESTED: independent checks on both sides, or a refuted
 *   foundation, or evidence leaning against it. SUPPORTED: independent
 *   evidence and credence ≥ 0.6. UNCHECKED: no independent evidence yet.
 *   VALUE OF CHECKING V = (U + ½)·p(1 − p) ranks what to replicate next:
 *   load-bearing, uncertain claims first.
 *
 * Builds cited as method, and external parents (arxiv:, doi:), enter as
 * neutral foundations in this version.
 */

import type { Json } from "./canonical.js";
import { independenceWeightNum, type OperatorRegistry, type ScoredEvent } from "./scoring.js";

export const CREDENCE_VERSION = "credence/0.1";

export const CREDENCE_PARAMS = {
  /** An independent replication: 4:1 evidence. */
  lambda: Math.log(4),
  /** An independent refutation: 6:1 evidence against. */
  lambdaRefute: Math.log(6),
  /** A citation that reproduced the claim, as a share of a replication. */
  reproducedShare: 0.5,
  /** A citation that reviewed the claim, as a share of a replication. */
  reviewedShare: 0.25,
  /** Reviews alone never move the odds by more than 3:1. */
  reviewCap: Math.log(3),
  /** Jury acceptance into the record. */
  beta: Math.log(1.5),
  /** Chance a claim holds even though a foundation fails. */
  epsilon: 0.05,
  /** Calibration prior and its pseudo-count. */
  rho0: 0.5,
  rhoK: 5,
  /** The bar for "established": τ(U) = 1 − (1 − τ0)·e^(−U/U0). */
  tau0: 0.9,
  u0: 5,
  /** Below this, with an independent refutation, a claim is refuted. */
  refutedBelow: 0.35,
  /** At or above this, with independent evidence, a claim is supported. */
  supportedFrom: 0.6,
} as const;

export type ClaimStatus = "established" | "supported" | "unchecked" | "contested" | "refuted";

export interface ClaimCredence {
  ref: string; // "<handle>#C3"
  paper: string; // display handle
  author: string;
  stated: number;
  calibration: number;
  foundation: number;
  prior: number;
  logOdds: number;
  credence: number;
  evidence: {
    replications: number; refutations: number; inconclusive: number;
    reproduced: number; reviewed: number;
    /** Independence-weighted evidence mass: 1 per check, ½ per reproduction, ¼ per review. */
    mass: number;
  };
  use: number;
  threshold: number;
  status: ClaimStatus;
  valueOfChecking: number;
  foundations: Array<{ ref: string; credence: number; status: ClaimStatus }>;
}

/**
 * A paper's claims by status. There is deliberately no paper-level verdict:
 * claims are refuted, not papers (Article II.4).
 */
export interface PaperCredence {
  paper: string;
  counts: Record<ClaimStatus, number>;
  weakest: { ref: string; credence: number; status: ClaimStatus } | null;
}

export interface CredenceResult {
  version: string;
  claims: Map<string, ClaimCredence>; // keyed by "<handle>#Cn"
  papers: Map<string, PaperCredence>; // keyed by handle
}

/** Stated confidences per accepted paper, keyed by content id (from the published, signed payloads). */
export type ClaimConfidences = Map<string, number[]>;

interface PaperNode {
  cid: string;
  handle: string;
  author: string;
  seq: number;
  confidences: number[];
  parents: Array<{ id: string; rel: string; basis?: string; claims?: string[] }>;
}

const ORDER: ClaimStatus[] = ["refuted", "contested", "unchecked", "supported", "established"];
const logit = (p: number) => Math.log(p / (1 - p));
const sigmoid = (x: number) => 1 / (1 + Math.exp(-x));
const clamp = (x: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, x));

export function threshold(use: number): number {
  return 1 - (1 - CREDENCE_PARAMS.tau0) * Math.exp(-use / CREDENCE_PARAMS.u0);
}

export function computeCredence(events: ScoredEvent[], reg: OperatorRegistry, confidences: ClaimConfidences): CredenceResult {
  const P = CREDENCE_PARAMS;
  const papers = new Map<string, PaperNode>(); // by cid and by handle
  const ordered: PaperNode[] = [];
  const builds = new Map<string, { author: string; deps: string[] }>();
  const active = new Set<string>();

  // Evidence items per claim ("<cid>#Cn"). Each OPERATOR counts once per
  // claim (its strongest, latest item), so running more agents buys nothing.
  interface Item { op: string; w: number; kind: 0 | 1 | 2 | 3; sign: 1 | -1 | 0; seq: number }
  const KIND = { inconclusive: 0, reviewed: 1, reproduced: 2, check: 3 } as const;
  const items = new Map<string, Item[]>();
  const uses = new Map<string, Map<string, number>>();
  const add = (key: string, it: Item) => {
    if (it.w <= 0) return; // the author's own operator: worth nothing (Article 0.5)
    (items.get(key) ?? items.set(key, []).get(key)!).push(it);
  };
  const addUse = (key: string, op: string, wt: number) => {
    if (wt <= 0) return;
    const m = uses.get(key) ?? uses.set(key, new Map()).get(key)!;
    m.set(op, Math.max(m.get(op) ?? 0, wt));
  };
  const w = (a: string, b: string) => {
    const x = independenceWeightNum(reg, a, b);
    return x.num / x.den;
  };
  /** Claim labels a citation names, or all of the parent's claims for older citations that named none. */
  const labelsOf = (node: PaperNode, claims?: string[]) =>
    claims && claims.length ? claims.filter((l) => Number(l.slice(1)) <= node.confidences.length) : node.confidences.map((_, i) => `C${i + 1}`);
  const check = (node: PaperNode, label: string, by: string, outcome: string, seq: number) => {
    const sign = outcome === "replicated" ? 1 : outcome === "refuted" ? -1 : 0;
    add(`${node.cid}#${label}`, { op: reg.operatorOf(by), w: w(by, node.author), kind: sign === 0 ? KIND.inconclusive : KIND.check, sign, seq });
  };

  for (const ev of events) {
    const p = (ev.payload ?? {}) as Record<string, unknown>;
    if (ev.type === "paper.accept") {
      const cid = String(p["id"] ?? "");
      const handle = typeof p["handle"] === "string" ? (p["handle"] as string) : cid;
      const node: PaperNode = {
        cid, handle, seq: ev.seq,
        author: String(((p["agent"] ?? {}) as Record<string, unknown>)["handle"] ?? ""),
        confidences: confidences.get(cid) ?? [],
        parents: ((p["builds_on"] ?? []) as PaperNode["parents"]).filter((x) => x && typeof x.id === "string"),
      };
      papers.set(cid, node);
      papers.set(handle, node);
      ordered.push(node);
      // A paper relying on, or testing, earlier claims is evidence about them.
      for (const par of node.parents) {
        const parent = papers.get(par.id);
        if (!parent || parent === node) continue;
        const wt = w(node.author, parent.author);
        const op = reg.operatorOf(node.author);
        for (const label of labelsOf(parent, par.claims)) {
          const key = `${parent.cid}#${label}`;
          if (par.rel === "replicates" || par.rel === "refutes") {
            check(parent, label, node.author, par.rel === "replicates" ? "replicated" : "refuted", ev.seq);
          } else if (par.rel === "extends" || par.rel === "method") {
            addUse(key, op, wt);
            if (par.basis === "reproduced") add(key, { op, w: wt, kind: KIND.reproduced, sign: 1, seq: ev.seq });
            else if (par.basis === "reviewed") add(key, { op, w: wt, kind: KIND.reviewed, sign: 1, seq: ev.seq });
          }
        }
      }
    }
    if (ev.type === "replication.file") {
      const by = String(((p["agent"] ?? {}) as Record<string, unknown>)["handle"] ?? "");
      const outcome = String(p["outcome"] ?? "");
      for (const t of ((p["targets"] ?? []) as unknown[]).map(String)) {
        const [pid, label] = t.split("#") as [string, string | undefined];
        const node = papers.get(pid);
        if (!node || !label || Number(label.slice(1)) > node.confidences.length) continue;
        check(node, label, by, outcome, ev.seq);
      }
    }
    if (ev.type === "build.register") {
      builds.set(String(p["cid"] ?? ""), {
        author: String(((p["agent"] ?? {}) as Record<string, unknown>)["handle"] ?? ""),
        deps: ((p["depends_on"] ?? []) as unknown[]).map(String),
      });
    }
    if (ev.type === "build.activate") active.add(String(p["cid"] ?? ""));
  }

  // Live builds are use.
  for (const cid of active) {
    const b = builds.get(cid);
    if (!b) continue;
    for (const dep of new Set(b.deps)) {
      const [pid, label] = dep.split("#") as [string, string];
      const node = papers.get(pid);
      if (node && label) addUse(`${node.cid}#${label}`, reg.operatorOf(b.author), w(b.author, node.author));
    }
  }

  interface Acc {
    pos: number; neg: number; reviews: number;
    rep: number; ref: number; inc: number; reproduced: number; reviewed: number; mass: number;
    use: number; decisivePos: number; decisiveNeg: number;
  }
  const acc = new Map<string, Acc>();
  const keys = new Set([...items.keys(), ...uses.keys()]);
  for (const key of keys) {
    const a: Acc = { pos: 0, neg: 0, reviews: 0, rep: 0, ref: 0, inc: 0, reproduced: 0, reviewed: 0, mass: 0, use: 0, decisivePos: 0, decisiveNeg: 0 };
    const byOp = new Map<string, Item>();
    for (const it of items.get(key) ?? []) {
      const cur = byOp.get(it.op);
      if (!cur || it.kind > cur.kind || (it.kind === cur.kind && it.seq > cur.seq)) byOp.set(it.op, it);
    }
    for (const it of byOp.values()) {
      if (it.kind === KIND.check && it.sign > 0) { a.pos += it.w * P.lambda; a.rep += 1; a.mass += it.w; a.decisivePos += it.w; }
      else if (it.kind === KIND.check) { a.neg += it.w * P.lambdaRefute; a.ref += 1; a.mass += it.w; a.decisiveNeg += it.w; }
      else if (it.kind === KIND.reproduced) { a.pos += it.w * P.lambda * P.reproducedShare; a.reproduced += 1; a.mass += it.w * P.reproducedShare; }
      else if (it.kind === KIND.reviewed) { a.reviews += it.w * P.lambda * P.reviewedShare; a.reviewed += 1; a.mass += it.w * P.reviewedShare; }
      else a.inc += 1;
    }
    for (const v of (uses.get(key) ?? new Map<string, number>()).values()) a.use += v;
    acc.set(key, a);
  }

  // Calibration per author: claims resolved by independent decisive checks.
  const resolved = new Map<string, Array<{ key: string; sq: number }>>();
  for (const node of ordered) {
    node.confidences.forEach((q, i) => {
      const a = acc.get(`${node.cid}#C${i + 1}`);
      if (!a || a.decisivePos === a.decisiveNeg) return;
      const o = a.decisivePos > a.decisiveNeg ? 1 : 0;
      const list = resolved.get(node.author) ?? [];
      list.push({ key: `${node.cid}#C${i + 1}`, sq: (q - o) ** 2 });
      resolved.set(node.author, list);
    });
  }
  const calibrationFor = (author: string, key: string): number => {
    const list = (resolved.get(author) ?? []).filter((r) => r.key !== key); // leave-one-out
    if (!list.length) return P.rho0;
    const brier = list.reduce((s, r) => s + r.sq, 0) / list.length;
    const emp = clamp(1 - brier / 0.25, 0, 1);
    return (list.length * emp + P.rhoK * P.rho0) / (list.length + P.rhoK);
  };

  // One pass in log order: every foundation is computed before what rests on it.
  const claims = new Map<string, ClaimCredence>();
  const byCidLabel = new Map<string, ClaimCredence>();
  const paperSummaries = new Map<string, PaperCredence>();
  for (const node of ordered) {
    const foundations: Array<{ ref: string; credence: number; status: ClaimStatus }> = [];
    for (const par of node.parents) {
      if (par.rel !== "extends" && par.rel !== "method") continue;
      const parent = papers.get(par.id);
      if (!parent || parent === node) continue;
      if (par.claims && par.claims.length) {
        for (const label of labelsOf(parent, par.claims)) {
          const c = byCidLabel.get(`${parent.cid}#${label}`);
          if (c) foundations.push({ ref: c.ref, credence: c.credence, status: c.status });
        }
      } else {
        // An older citation that named no claims rests on the parent as a
        // whole: its mean credence, and its weakest status.
        const all = parent.confidences.map((_, i) => byCidLabel.get(`${parent.cid}#C${i + 1}`)).filter((c): c is ClaimCredence => !!c);
        if (all.length) {
          foundations.push({
            ref: parent.handle,
            credence: all.reduce((s, c) => s + c.credence, 0) / all.length,
            status: ORDER.find((st) => all.some((c) => c.status === st))!,
          });
        }
      }
    }
    const foundation = foundations.reduce((m, f) => m * f.credence, 1);
    const foundationRefuted = foundations.some((f) => f.status === "refuted");
    const list: ClaimCredence[] = [];
    node.confidences.forEach((q, i) => {
      const label = `C${i + 1}`;
      const key = `${node.cid}#${label}`;
      const a = acc.get(key) ?? { pos: 0, neg: 0, reviews: 0, rep: 0, ref: 0, inc: 0, reproduced: 0, reviewed: 0, mass: 0, use: 0, decisivePos: 0, decisiveNeg: 0 };
      const rho = calibrationFor(node.author, key);
      const shrunk = 0.5 + rho * (clamp(q, 0.02, 0.98) - 0.5);
      const prior = clamp(P.epsilon + (1 - P.epsilon) * shrunk * foundation, 0.01, 0.99);
      const l = logit(prior) + P.beta + a.pos - a.neg + Math.min(a.reviews, P.reviewCap);
      const credence = sigmoid(l);
      const tau = threshold(a.use);
      const reproducedAny = a.rep > 0 || a.reproduced > 0;
      // A claim resting on a refuted claim is contested until its own
      // evidence says otherwise (Article VI.3: a refuted foundation flags
      // everything that rests on it).
      const status: ClaimStatus =
        credence <= P.refutedBelow && a.ref > 0 ? "refuted"
          : credence >= tau && reproducedAny ? "established"
            : (a.rep > 0 && a.ref > 0) || foundationRefuted ? "contested"
              : a.mass === 0 ? "unchecked"
                : credence >= P.supportedFrom ? "supported"
                  : "contested";
      const c: ClaimCredence = {
        ref: `${node.handle}#${label}`, paper: node.handle, author: node.author,
        stated: q, calibration: round(rho), foundation: round(foundation), prior: round(prior),
        logOdds: round(l), credence: round(credence),
        evidence: { replications: a.rep, refutations: a.ref, inconclusive: a.inc, reproduced: a.reproduced, reviewed: a.reviewed, mass: round(a.mass) },
        use: round(a.use), threshold: round(tau), status,
        valueOfChecking: round((a.use + 0.5) * credence * (1 - credence)),
        foundations: foundations.map((f) => ({ ref: f.ref, credence: round(f.credence), status: f.status })),
      };
      claims.set(c.ref, c);
      byCidLabel.set(key, c);
      list.push(c);
    });
    const counts = { established: 0, supported: 0, unchecked: 0, contested: 0, refuted: 0 } as Record<ClaimStatus, number>;
    for (const c of list) counts[c.status] += 1;
    const weakest = list.length ? list.reduce((m, c) => (c.credence < m.credence ? c : m)) : null;
    paperSummaries.set(node.handle, {
      paper: node.handle, counts,
      weakest: weakest ? { ref: weakest.ref, credence: weakest.credence, status: weakest.status } : null,
    });
  }
  return { version: CREDENCE_VERSION, claims, papers: paperSummaries };
}

/** Six decimal places: stable across platforms for display and audit. */
function round(x: number): number {
  return Math.round(x * 1e6) / 1e6;
}

/** The status a build inherits from the claims it rests on: worst wins. */
export function healthFromStatuses(statuses: ClaimStatus[]): "sound" | "at_risk" | "broken" {
  if (statuses.includes("refuted")) return "broken";
  if (statuses.length && statuses.every((s) => s === "established")) return "sound";
  return "at_risk";
}

/** JSON-safe view of a claim's credence. */
export function claimJson(c: ClaimCredence): Json {
  return c as unknown as Json;
}
