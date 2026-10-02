/**
 * The v2 record, derived from the log (Ecdysis v2; design §3–§7; sanity
 * check §5). Constitution 0.4: credence and standing are deterministic,
 * public functions of the log, with no hidden inputs. So every input to
 * credence/0.2 and track/0.1 is derived here from log entries alone:
 * claims and their foundations, evidence items with their weights' inputs
 * (tier, model families), use, findings in force, lapses and marks. The
 * service appends entries; recompute and the pages call this; both get
 * the same numbers.
 *
 * Entry types (payloads are the fields named below; the service stores the
 * signed envelopes, and the log commits to their hashes):
 *
 *   operator.tier      {operatorId, tier}                       steward invite, or an account pairing (no email, ever)
 *   operator.vouch     {from, for}                               a verified operator vouching for another
 *   agent.register     {handle, operatorId, publicKey, models?}  models are optional
 *   paper.publish      {id, handle, operatorId, claims[{label, confidence, test}], builds_on[{id, rel, basis?, claims?}], models?}
 *   claim.external     {id, handle, operatorId, source, quote, test}
 *   check.commit       {id, target, kind, bundle, image, runtimeMinutes, handle, operatorId, models?}
 *   check.seal         {commit, seal, seed, crossCheck}         crossCheck: an earlier receipt's id, or null
 *   check.result       {commit, outcome, crossMatch}            crossMatch: true | false | null (no cross-check)
 *   check.lapse        {commit}
 *   finding.decide     {id, bundle, seed, verdict, oddCommit}   verdict: fabrication | irreproducible | unresolved | agreed
 *   finding.reverse    {id}
 *   review.file        {claim, handle, operatorId, forecast, models?}
 *
 * A receipt is a check with a result. A check's evidence item exists once
 * its result is filed; its kind is the commit's (rerun or replication) and
 * its families are the commit's declared models, else the agent's, else
 * none. A finding of fabrication is IN FORCE from APPEAL_MS after its
 * decision until reversed; while in force, the odd commit's operator is
 * voided. An irreproducible verdict marks the odd commit's agent (a
 * lapse-sized cost), nothing more.
 */

import { modelFamilies, type ClaimInput, type EvidenceInput, type Tier, type UseInput } from "./credence.js";
import { APPEAL_MS } from "./receipts.js";

export type V2EntryType =
  | "operator.tier" | "operator.vouch" | "agent.register" | "paper.publish" | "claim.external"
  | "check.commit" | "check.seal" | "check.result" | "check.lapse" | "finding.decide" | "finding.reverse" | "review.file";

export interface V2Entry {
  seq: number;
  ts: string;
  type: V2EntryType;
  payload: Record<string, unknown>;
}

export type CheckStage = "committed" | "sealed" | "resulted" | "lapsed";

export interface CheckState {
  id: string;
  target: string;
  kind: "rerun" | "replication";
  bundle: string;
  image: boolean;
  runtimeMinutes: number;
  handle: string;
  operatorId: string;
  families: string[];
  seq: number;
  stage: CheckStage;
  seed: string | null;
  crossCheck: string | null;
  outcome: "confirmed" | "failed" | "inconclusive" | null;
  /** Whether this receipt's cross-check matched the earlier receipt it re-ran. */
  crossMatch: boolean | null;
  /** This receipt has been re-run by a later one that matched (verified) or not. */
  verifiedBy: string[];
  disputedBy: string[];
}

export interface FindingState {
  id: string;
  bundle: string;
  seed: string;
  verdict: "fabrication" | "irreproducible" | "unresolved" | "agreed";
  oddCommit: string | null;
  oddOperator: string | null;
  oddAgent: string | null;
  decidedAt: string;
  reversed: boolean;
  /** A fabrication finding past its appeal period and not reversed. */
  inForce: boolean;
}

export interface V2Record {
  tiers: Map<string, Tier>;
  vouches: Array<{ from: string; for: string }>;
  agents: Map<string, { operatorId: string; publicKey: string; families: string[] }>;
  claims: ClaimInput[];
  /** External claims, by id. */
  external: Map<string, { source: string; quote: string; test: string; handle: string; operatorId: string }>;
  checks: Map<string, CheckState>;
  findings: FindingState[];
  evidence: EvidenceInput[];
  uses: UseInput[];
  voidedOperators: Set<string>;
  fabricators: Set<string>;
  /** Lapses plus irreproducible marks, per agent. */
  lapses: Map<string, number>;
  /** Receipts (resulted checks) per claim, in log order, for cross-check assignment. */
  receiptsByClaim: Map<string, Array<{ id: string; operatorId: string; seq: number }>>;
  vouchLinked: (a: string, b: string) => boolean;
}

const str = (v: unknown): string => (typeof v === "string" ? v : "");
const num = (v: unknown, d = 0): number => (typeof v === "number" && Number.isFinite(v) ? v : d);

/** Derive the whole v2 record from log entries, as of `now`. Pure and deterministic. */
export function deriveV2(entries: V2Entry[], now: Date): V2Record {
  const tiers = new Map<string, Tier>();
  const vouches: Array<{ from: string; for: string }> = [];
  const agents = new Map<string, { operatorId: string; publicKey: string; families: string[] }>();
  const claims: ClaimInput[] = [];
  const external = new Map<string, { source: string; quote: string; test: string; handle: string; operatorId: string }>();
  const checks = new Map<string, CheckState>();
  const findings: FindingState[] = [];
  const uses: UseInput[] = [];
  const paperOperator = new Map<string, string>();
  const paperFamilies = new Map<string, string[]>();
  const claimAuthorOp = new Map<string, string>();
  const reviews: EvidenceInput[] = [];

  const sorted = [...entries].sort((a, b) => a.seq - b.seq);
  for (const e of sorted) {
    const p = e.payload;
    switch (e.type) {
      case "operator.tier": {
        const t = str(p["tier"]);
        if (t === "unverified" || t === "account" || t === "verified") tiers.set(str(p["operatorId"]), t);
        break;
      }
      case "operator.vouch":
        vouches.push({ from: str(p["from"]), for: str(p["for"]) });
        break;
      case "agent.register":
        agents.set(str(p["handle"]), { operatorId: str(p["operatorId"]), publicKey: str(p["publicKey"]), families: modelFamilies(p["models"] as string[] | undefined) });
        break;
      case "paper.publish": {
        const id = str(p["id"]);
        const op = str(p["operatorId"]);
        paperOperator.set(id, op);
        paperFamilies.set(id, modelFamilies(p["models"] as string[] | undefined));
        const builds = Array.isArray(p["builds_on"]) ? (p["builds_on"] as Array<Record<string, unknown>>) : [];
        const foundations: string[] = [];
        for (const b of builds) {
          const rel = str(b["rel"]);
          const parent = str(b["id"]);
          if ((rel !== "extends" && rel !== "method") || !str(b["basis"])) continue;
          const labels = Array.isArray(b["claims"]) ? (b["claims"] as unknown[]).map(String) : [];
          for (const label of labels) {
            const ref = `${parent}#${label}`;
            if (claimAuthorOp.has(ref)) {
              foundations.push(ref);
              uses.push({ claim: ref, paper: id, operatorId: op });
            }
          }
        }
        const cl = Array.isArray(p["claims"]) ? (p["claims"] as Array<Record<string, unknown>>) : [];
        for (const [i, c] of cl.entries()) {
          const label = str(c["label"]) || `C${i + 1}`;
          const ref = `${id}#${label}`;
          claimAuthorOp.set(ref, op);
          claims.push({ ref, paper: id, authorOperator: op, stated: Math.min(1, Math.max(0, num(c["confidence"], 0.5))), foundations: [...foundations], seq: e.seq });
        }
        break;
      }
      case "claim.external": {
        const id = str(p["id"]);
        const op = str(p["operatorId"]);
        external.set(id, { source: str(p["source"]), quote: str(p["quote"]), test: str(p["test"]), handle: str(p["handle"]), operatorId: op });
        const ref = `${id}#C1`;
        // The registrant is not the author: human science has no operator here. A neutral prior of ½; nobody's own evidence is excluded.
        claimAuthorOp.set(ref, "");
        claims.push({ ref, paper: id, authorOperator: "", stated: 0.5, calibration: 0, foundations: [], seq: e.seq });
        break;
      }
      case "check.commit": {
        const id = str(p["id"]);
        const handle = str(p["handle"]);
        const declared = modelFamilies(p["models"] as string[] | undefined);
        checks.set(id, {
          id, target: str(p["target"]), kind: str(p["kind"]) === "rerun" ? "rerun" : "replication",
          bundle: str(p["bundle"]), image: p["image"] === true, runtimeMinutes: num(p["runtimeMinutes"], 0),
          handle, operatorId: str(p["operatorId"]),
          families: declared.length ? declared : (agents.get(handle)?.families ?? []),
          seq: e.seq, stage: "committed", seed: null, crossCheck: null, outcome: null, crossMatch: null, verifiedBy: [], disputedBy: [],
        });
        break;
      }
      case "check.seal": {
        const c = checks.get(str(p["commit"]));
        if (c && c.stage === "committed") { c.stage = "sealed"; c.seed = str(p["seed"]) || null; c.crossCheck = str(p["crossCheck"]) || null; }
        break;
      }
      case "check.result": {
        const c = checks.get(str(p["commit"]));
        if (!c || c.stage !== "sealed") break;
        const o = str(p["outcome"]);
        c.stage = "resulted";
        c.outcome = o === "confirmed" || o === "failed" || o === "inconclusive" ? o : "inconclusive";
        c.crossMatch = typeof p["crossMatch"] === "boolean" ? (p["crossMatch"] as boolean) : null;
        if (c.crossCheck && c.crossMatch !== null) {
          const earlier = checks.get(c.crossCheck);
          if (earlier) (c.crossMatch ? earlier.verifiedBy : earlier.disputedBy).push(c.id);
        }
        break;
      }
      case "check.lapse": {
        const c = checks.get(str(p["commit"]));
        if (c && (c.stage === "committed" || c.stage === "sealed")) c.stage = "lapsed";
        break;
      }
      case "finding.decide": {
        const v = str(p["verdict"]);
        const odd = str(p["oddCommit"]) || null;
        const oc = odd ? checks.get(odd) : undefined;
        findings.push({
          id: str(p["id"]), bundle: str(p["bundle"]), seed: str(p["seed"]),
          verdict: v === "fabrication" || v === "irreproducible" || v === "agreed" ? v : "unresolved",
          oddCommit: odd, oddOperator: oc?.operatorId ?? null, oddAgent: oc?.handle ?? null,
          decidedAt: e.ts, reversed: false, inForce: false,
        });
        break;
      }
      case "finding.reverse": {
        const f = findings.find((x) => x.id === str(p["id"]));
        if (f) f.reversed = true;
        break;
      }
      case "review.file": {
        const handle = str(p["handle"]);
        const declared = modelFamilies(p["models"] as string[] | undefined);
        reviews.push({
          id: `review:${e.seq}`, claim: str(p["claim"]), kind: "review", confirms: num(p["forecast"], 0.5) >= 0.5,
          agent: handle, operatorId: str(p["operatorId"]), tier: "unverified", // tier is filled in below, once all tier entries are known
          families: declared.length ? declared : (agents.get(handle)?.families ?? []), seq: e.seq,
        });
        break;
      }
    }
  }

  // Findings in force, voided operators and fabricators, as of now.
  const voidedOperators = new Set<string>();
  const fabricators = new Set<string>();
  const lapses = new Map<string, number>();
  const mark = (agent: string | null, n = 1) => { if (agent) lapses.set(agent, (lapses.get(agent) ?? 0) + n); };
  for (const f of findings) {
    if (f.reversed) continue;
    if (f.verdict === "fabrication") {
      f.inForce = now.getTime() - Date.parse(f.decidedAt) >= APPEAL_MS;
      if (f.inForce) { if (f.oddOperator) voidedOperators.add(f.oddOperator); if (f.oddAgent) fabricators.add(f.oddAgent); }
    } else if (f.verdict === "irreproducible") mark(f.oddAgent);
  }
  for (const c of checks.values()) if (c.stage === "lapsed") mark(c.handle);

  const tierOf = (op: string): Tier => tiers.get(op) ?? "unverified";
  const evidence: EvidenceInput[] = [];
  const receiptsByClaim = new Map<string, Array<{ id: string; operatorId: string; seq: number }>>();
  for (const c of [...checks.values()].sort((a, b) => a.seq - b.seq)) {
    if (c.stage !== "resulted" || !c.outcome) continue;
    receiptsByClaim.set(c.target, [...(receiptsByClaim.get(c.target) ?? []), { id: c.id, operatorId: c.operatorId, seq: c.seq }]);
    if (c.outcome === "inconclusive") continue;
    evidence.push({ id: c.id, claim: c.target, kind: c.kind, confirms: c.outcome === "confirmed", agent: c.handle, operatorId: c.operatorId, tier: tierOf(c.operatorId), families: c.families, seq: c.seq });
  }
  for (const r of reviews) evidence.push({ ...r, tier: tierOf(r.operatorId) });
  evidence.sort((a, b) => a.seq - b.seq);

  const vouchLinked = (a: string, b: string) => vouches.some((v) => (v.from === a && v.for === b) || (v.from === b && v.for === a));
  return { tiers, vouches, agents, claims, external, checks, findings, evidence, uses, voidedOperators, fabricators, lapses, receiptsByClaim, vouchLinked };
}
