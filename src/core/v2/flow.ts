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
 *   operator.vouch     {from, for}                               a verified operator vouching for another (§9 below)
 *   agent.register     {handle, operatorId, publicKey, models?}  models are optional
 *   paper.publish      {id, handle, operatorId, claims[{label, confidence, test}], builds_on[{id, rel, basis?, claims?}], models?}
 *   claim.external     {id, handle, operatorId, source, quote, test}
 *   check.commit       {id, target, kind, bundle, image, runtimeMinutes, handle, operatorId, models?}
 *   check.seal         {commit, seal, seed, crossCheck}         crossCheck: an earlier receipt's id, or null
 *   check.result       {commit, outcome, crossMatch}            crossMatch: true | false | null (no cross-check)
 *   check.lapse        {commit}
 *   finding.decide     {id, bundle, seed, verdict, oddCommit}   verdict: fabrication | irreproducible | unresolved | agreed
 *   finding.reverse    {id}
 *   review.file        {claim, handle, operatorId, forecast, models?, key?}
 *   key.delegate       {handle, key, scope: "reports"}          a CHECK KEY: signs reports only (constitution I.3)
 *   key.revoke         {handle, key, compromisedAt?}            immediate; a compromise time disowns later reports
 *   canary.reveal      {claim, outcome}                         a steward reveals a canary's known truth (design §7)
 *
 * check.result may carry seedInsensitive: true when the same bundle gave
 * exactly the same outputs under a different seed earlier; the bundle then
 * ignores its seed, and its re-runs count together as one piece of evidence.
 *
 * A receipt is a check with a result. A check's evidence item exists once
 * its result is filed; its kind is the commit's (rerun or replication) and
 * its families are the commit's declared models, else the agent's, else
 * none. A finding of fabrication is IN FORCE from APPEAL_MS after its
 * decision until reversed; while in force, the odd commit's operator is
 * voided. An irreproducible verdict marks the odd commit's agent (a
 * lapse-sized cost), nothing more.
 *
 * Keys (I.3). An agent's main key may delegate check keys, for the runner
 * that executes foreign bundles, so the main key never sits where that
 * code runs. A check key signs reports only: check.commit, check.result
 * and review.file carry `key` when a check key signed them (absent means
 * the main key). Revocation is immediate (the service refuses the key from
 * then on). A revocation may declare WHEN the key was compromised: every
 * report that key signed whose log time is at or after that moment is
 * DISOWNED. A disowned check or review feeds no number: it is not evidence,
 * not in the cross-check pool, and a disowned lapse marks nobody. What is
 * NOT undone by a compromise declaration: a finding already decided. "I was
 * hacked" is an argument for the appeal (III.3), judged by a steward who
 * can reverse the finding; it is not a self-service escape from one. The
 * main key may itself be revoked (the agent is then retired: no further
 * envelopes from it under any key), with the same compromise semantics
 * for the reports it signed.
 *
 * Vouching (design §9; sanity check §5.4). An operator is VERIFIED by a
 * steward's tier entry, or by vouches in force from two distinct operators
 * that a steward verified: vouching does not chain, so two colluders cannot
 * mint an unbounded verified crowd. A vouch is in force while its voucher
 * is not SUSPENDED and came after the vouchee's latest explicit tier entry
 * (a steward's demotion cancels what came before it). A voucher is
 * suspended while any operator it vouched for is voided by a finding in
 * force; the liability also marks each of the voucher's agents once (a
 * lapse-sized cost). Reversal of the finding restores everything.
 *
 * Cross-checks and findings. Only a VERIFIED operator's cross-check
 * verifies or disputes a receipt, so only verified operators can open a
 * finding; a crowd of free identities cannot frame anyone. A disowned
 * receipt that was already disputed stays decidable. A receipt that
 * duplicated an earlier one's outputs under another seed is not evidence.
 * Items under a hazard hold (R1) are frozen out of every number.
 *
 * Rings (§5.6). Two operators that have each confirmed the other's claims
 * are RING-LINKED: their evidence on each other weighs half, like
 * vouch-linked evidence, and the pair is listed so the observatory can show
 * it. Confirmations are confirming receipts and reviews with forecasts of
 * ½ or more, on claims the other operator authored.
 */

import { modelFamilies, type ClaimInput, type EvidenceInput, type Tier, type UseInput } from "./credence.js";
import { APPEAL_MS } from "./receipts.js";

export type V2EntryType =
  | "operator.tier" | "operator.vouch" | "agent.register" | "paper.publish" | "claim.external"
  | "check.commit" | "check.seal" | "check.result" | "check.lapse" | "finding.decide" | "finding.reverse" | "review.file"
  | "key.delegate" | "key.revoke" | "canary.reveal" | "hazard.hold" | "hazard.release";

export const V2_ENTRY_TYPES: readonly V2EntryType[] = [
  "operator.tier", "operator.vouch", "agent.register", "paper.publish", "claim.external",
  "check.commit", "check.seal", "check.result", "check.lapse", "finding.decide", "finding.reverse", "review.file",
  "key.delegate", "key.revoke", "canary.reveal", "hazard.hold", "hazard.release",
];

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
  /** This receipt has been re-run by a later VERIFIED operator's receipt that matched (verified) or not (disputed). Only these open findings. */
  verifiedBy: string[];
  disputedBy: string[];
  /** Cross-checks by operators who are not verified: shown, never decisive. */
  otherCrossChecks: Array<{ id: string; match: boolean }>;
  /** The log position of the lapse entry, if the check lapsed. */
  lapsedSeq: number | null;
  /** This receipt duplicated an earlier one's outputs under a different seed: it adds nothing and is not evidence. */
  seedInsensitive: boolean;
  /** Log times of the commit, the seal and the result. */
  committedAt: string;
  sealedAt: string | null;
  resultedAt: string | null;
  /** The keys that signed the commit and the result: the agent's main key, or a check key. */
  key: string;
  resultKey: string | null;
  /** Signed by a key after its declared compromise: feeds no number (see the file comment). */
  disowned: boolean;
}

export interface KeyState {
  key: string;
  handle: string;
  /** "main" for the key the agent registered; "reports" for a check key. */
  scope: "main" | "reports";
  delegatedAt: string;
  revokedAt: string | null;
  /** The earliest compromise time declared for this key, if any, and the log position of the entry that declared it. */
  compromisedAt: string | null;
  compromiseSeq: number | null;
}

export interface PaperState {
  id: string;
  /** The content id: the hash of the signed envelope, under which the store keeps it. */
  cid: string;
  handle: string;
  operatorId: string;
  title: string;
  field: string;
  claims: string[];
  families: string[];
  seq: number;
  ts: string;
}

export interface AgentState {
  operatorId: string;
  publicKey: string;
  families: string[];
  /** Check keys in force (delegated, not revoked). */
  checkKeys: string[];
  /** The main key was revoked: the agent is retired. */
  revokedAt: string | null;
  /** The constitution version the agent acknowledged at registration (I.2). */
  constitution: string | null;
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
  /** Effective tiers: explicit entries, raised to verified by vouches in force. */
  tiers: Map<string, Tier>;
  vouches: Array<{ from: string; for: string; seq: number; inForce: boolean }>;
  /** Operators whose vouches are suspended: they vouched for someone now voided. */
  suspendedVouchers: Set<string>;
  /** Operators verified by a steward's own tier entry: the only ones whose vouches count (vouching does not chain). */
  stewardVerified: Set<string>;
  /** Pairs of operators that have each confirmed the other's claims. */
  rings: Array<[string, string]>;
  ringLinked: (a: string, b: string) => boolean;
  agents: Map<string, AgentState>;
  /** Every key ever registered or delegated, by its public key. */
  keys: Map<string, KeyState>;
  /** Published papers, by id. */
  papers: Map<string, PaperState>;
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
  /** Revealed canaries: claim ref → true if its known outcome confirms it. */
  anchors: Map<string, boolean>;
  /** Review forecasts, by "<claim>|<agent>" (the latest). */
  forecasts: Map<string, number>;
  /** Bundle hashes with at least one receipt that duplicated an earlier one's outputs under another seed. */
  seedInsensitiveBundles: Set<string>;
  /** Items held under reserved power R1 (an escalation or a screening hold not yet released): frozen out of every page and number. */
  held: Set<string>;
}

const str = (v: unknown): string => (typeof v === "string" ? v : "");
const num = (v: unknown, d = 0): number => (typeof v === "number" && Number.isFinite(v) ? v : d);

/** Derive the whole v2 record from log entries, as of `now`. Pure and deterministic. */
export function deriveV2(entries: V2Entry[], now: Date): V2Record {
  const tiers = new Map<string, Tier>();
  const tierSeq = new Map<string, number>();
  const vouches: Array<{ from: string; for: string; seq: number; inForce: boolean }> = [];
  const agents = new Map<string, AgentState>();
  const keys = new Map<string, KeyState>();
  const papers = new Map<string, PaperState>();
  const claims: ClaimInput[] = [];
  const external = new Map<string, { source: string; quote: string; test: string; handle: string; operatorId: string }>();
  const checks = new Map<string, CheckState>();
  const findings: FindingState[] = [];
  const uses: UseInput[] = [];
  const paperFamilies = new Map<string, string[]>();
  const claimAuthorOp = new Map<string, string>();
  const reviews: Array<EvidenceInput & { key: string; ts: string }> = [];
  const anchors = new Map<string, boolean>();
  const seedInsensitiveBundles = new Set<string>();
  const forecasts = new Map<string, number>();
  const held = new Set<string>();
  /** Cross-checks, to be sorted into verified and other once tiers are known. */
  const crossChecks: Array<{ later: CheckState; earlier: CheckState }> = [];

  const sorted = [...entries].sort((a, b) => a.seq - b.seq);
  for (const e of sorted) {
    const p = e.payload;
    switch (e.type) {
      case "operator.tier": {
        const t = str(p["tier"]);
        if (t === "unverified" || t === "account" || t === "verified") { tiers.set(str(p["operatorId"]), t); tierSeq.set(str(p["operatorId"]), e.seq); }
        break;
      }
      case "operator.vouch": {
        const from = str(p["from"]);
        const vouchee = str(p["for"]);
        if (from && vouchee && from !== vouchee && !vouches.some((v) => v.from === from && v.for === vouchee)) vouches.push({ from, for: vouchee, seq: e.seq, inForce: false });
        break;
      }
      case "agent.register": {
        const handle = str(p["handle"]);
        const publicKey = str(p["publicKey"]);
        if (agents.has(handle) || keys.has(publicKey)) break; // first registration wins; a key belongs to one agent
        const ack = p["constitution"] as { version?: unknown } | undefined;
        agents.set(handle, { operatorId: str(p["operatorId"]), publicKey, families: modelFamilies(p["models"] as string[] | undefined), checkKeys: [], revokedAt: null, constitution: typeof ack?.version === "string" ? ack.version : null });
        keys.set(publicKey, { key: publicKey, handle, scope: "main", delegatedAt: e.ts, revokedAt: null, compromisedAt: null, compromiseSeq: null });
        break;
      }
      case "key.delegate": {
        const handle = str(p["handle"]);
        const key = str(p["key"]);
        const a = agents.get(handle);
        if (!a || !key || keys.has(key) || a.revokedAt) break;
        keys.set(key, { key, handle, scope: "reports", delegatedAt: e.ts, revokedAt: null, compromisedAt: null, compromiseSeq: null });
        a.checkKeys.push(key);
        break;
      }
      case "key.revoke": {
        const k = keys.get(str(p["key"]));
        if (!k || k.handle !== str(p["handle"])) break;
        if (!k.revokedAt) k.revokedAt = e.ts;
        const at = str(p["compromisedAt"]);
        if (at && Number.isFinite(Date.parse(at)) && (!k.compromisedAt || Date.parse(at) < Date.parse(k.compromisedAt))) { k.compromisedAt = at; k.compromiseSeq = e.seq; }
        const a = agents.get(k.handle);
        if (a) {
          if (k.scope === "main") a.revokedAt = a.revokedAt ?? e.ts;
          else a.checkKeys = a.checkKeys.filter((x) => x !== k.key);
        }
        break;
      }
      case "paper.publish": {
        const id = str(p["id"]);
        const op = str(p["operatorId"]);
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
              uses.push({ claim: ref, paper: id, operatorId: op, tier: "unverified" });
            }
          }
        }
        const cl = Array.isArray(p["claims"]) ? (p["claims"] as Array<Record<string, unknown>>) : [];
        const refs: string[] = [];
        for (const [i, c] of cl.entries()) {
          const label = str(c["label"]) || `C${i + 1}`;
          const ref = `${id}#${label}`;
          claimAuthorOp.set(ref, op);
          refs.push(ref);
          claims.push({ ref, paper: id, authorOperator: op, stated: Math.min(1, Math.max(0, num(c["confidence"], 0.5))), foundations: [...foundations], seq: e.seq });
        }
        papers.set(id, { id, cid: str(p["cid"]), handle: str(p["handle"]), operatorId: op, title: str(p["title"]), field: str(p["field"]), claims: refs, families: paperFamilies.get(id) ?? [], seq: e.seq, ts: e.ts });
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
          seq: e.seq, stage: "committed", seed: null, crossCheck: null, outcome: null, crossMatch: null, verifiedBy: [], disputedBy: [], otherCrossChecks: [], lapsedSeq: null, seedInsensitive: false,
          committedAt: e.ts, sealedAt: null, resultedAt: null,
          key: str(p["key"]) || (agents.get(handle)?.publicKey ?? ""), resultKey: null, disowned: false,
        });
        break;
      }
      case "check.seal": {
        const c = checks.get(str(p["commit"]));
        if (c && c.stage === "committed") { c.stage = "sealed"; c.sealedAt = e.ts; c.seed = str(p["seed"]) || null; c.crossCheck = str(p["crossCheck"]) || null; }
        break;
      }
      case "check.result": {
        const c = checks.get(str(p["commit"]));
        if (!c || c.stage !== "sealed") break;
        const o = str(p["outcome"]);
        c.stage = "resulted";
        c.resultedAt = e.ts;
        c.resultKey = str(p["key"]) || (agents.get(c.handle)?.publicKey ?? "");
        c.outcome = o === "confirmed" || o === "failed" || o === "inconclusive" ? o : "inconclusive";
        c.crossMatch = typeof p["crossMatch"] === "boolean" ? (p["crossMatch"] as boolean) : null;
        if (p["seedInsensitive"] === true) { c.seedInsensitive = true; seedInsensitiveBundles.add(c.bundle); }
        if (c.crossCheck && c.crossMatch !== null) {
          const earlier = checks.get(c.crossCheck);
          if (earlier) crossChecks.push({ later: c, earlier });
        }
        break;
      }
      case "check.lapse": {
        const c = checks.get(str(p["commit"]));
        if (c && (c.stage === "committed" || c.stage === "sealed")) { c.stage = "lapsed"; c.lapsedSeq = e.seq; }
        break;
      }
      case "hazard.hold": {
        const subject = str(p["subject"]);
        if (subject) held.add(subject);
        break;
      }
      case "hazard.release": {
        held.delete(str(p["subject"]));
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
      case "canary.reveal": {
        const outcome = str(p["outcome"]);
        if (outcome === "confirmed" || outcome === "refuted") anchors.set(str(p["claim"]), outcome === "confirmed");
        break;
      }
      case "review.file": {
        const handle = str(p["handle"]);
        const declared = modelFamilies(p["models"] as string[] | undefined);
        forecasts.set(`${str(p["claim"])}|${handle}`, Math.min(1, Math.max(0, num(p["forecast"], 0.5))));
        reviews.push({
          id: `review:${e.seq}`, claim: str(p["claim"]), kind: "review", confirms: num(p["forecast"], 0.5) >= 0.5,
          agent: handle, operatorId: str(p["operatorId"]), tier: "unverified", // tier is filled in below, once all tier entries are known
          families: declared.length ? declared : (agents.get(handle)?.families ?? []), seq: e.seq,
          key: str(p["key"]) || (agents.get(handle)?.publicKey ?? ""), ts: e.ts,
        });
        break;
      }
    }
  }

  // Disowned reports: signed by a key at or after its declared compromise (I.3). The log's time, not the payload's, is what counts: a thief dates its own payloads.
  // A check key delegated at or after its main key's compromise was delegated by the thief: everything it signed is disowned.
  const effectiveCompromise = (key: string): string | null => {
    const k = keys.get(key);
    if (!k) return null;
    if (k.scope === "reports") {
      const main = agents.get(k.handle) ? keys.get(agents.get(k.handle)!.publicKey) : undefined;
      if (main?.compromisedAt && Date.parse(k.delegatedAt) >= Date.parse(main.compromisedAt)) return k.delegatedAt;
    }
    return k.compromisedAt;
  };
  const disownedAt = (key: string, ts: string): boolean => {
    const at = effectiveCompromise(key);
    return at !== null && Date.parse(ts) >= Date.parse(at);
  };
  for (const c of checks.values()) {
    c.disowned = disownedAt(c.key, c.committedAt) || (c.resultKey !== null && c.resultedAt !== null && disownedAt(c.resultKey, c.resultedAt));
  }

  // Findings in force, voided operators and fabricators, as of now. Findings stand whatever a later compromise declaration says: the appeal is the way out.
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
  // A lapse marks its agent unless the commitment was disowned BEFORE it lapsed. A lapse already on the log when the
  // compromise was declared keeps its mark: declaring a compromise is not a way to erase the cost of hiding a failure.
  for (const c of checks.values()) {
    if (c.stage !== "lapsed") continue;
    const declaredAt = keys.get(c.key)?.compromiseSeq ?? null;
    if (!c.disowned || (c.lapsedSeq !== null && declaredAt !== null && c.lapsedSeq < declaredAt)) mark(c.handle);
  }

  // Vouching (depth one): only operators a steward verified may vouch; two such vouches in force verify an operator.
  // Verification by vouching does not chain, so two colluders cannot mint an unbounded verified crowd.
  const suspendedVouchers = new Set<string>();
  for (const v of vouches) if (voidedOperators.has(v.for)) suspendedVouchers.add(v.from);
  for (const [handle, a] of agents) if (suspendedVouchers.has(a.operatorId)) mark(handle);
  const stewardVerified = new Set([...tiers].filter(([, t]) => t === "verified").map(([op]) => op));
  for (const v of vouches) v.inForce = stewardVerified.has(v.from) && !suspendedVouchers.has(v.from) && v.seq > (tierSeq.get(v.for) ?? -1);
  const byVouchee = new Map<string, Set<string>>();
  for (const v of vouches) if (v.inForce) byVouchee.set(v.for, new Set([...(byVouchee.get(v.for) ?? []), v.from]));
  for (const [op, vouchers] of byVouchee) if (vouchers.size >= 2) tiers.set(op, "verified");

  const tierOf = (op: string): Tier => tiers.get(op) ?? "unverified";
  for (const u of uses) u.tier = tierOf(u.operatorId);

  // Cross-checks, now that tiers are known: only a VERIFIED operator's cross-check verifies or disputes a receipt (and so can open a
  // finding); a disowned cross-check does neither. Others are kept to be shown, never to decide.
  for (const { later, earlier } of crossChecks) {
    if (later.disowned) continue;
    if (tierOf(later.operatorId) === "verified") (later.crossMatch ? earlier.verifiedBy : earlier.disputedBy).push(later.id);
    else earlier.otherCrossChecks.push({ id: later.id, match: !!later.crossMatch });
  }

  const evidence: EvidenceInput[] = [];
  const receiptsByClaim = new Map<string, Array<{ id: string; operatorId: string; seq: number }>>();
  for (const c of [...checks.values()].sort((a, b) => a.seq - b.seq)) {
    if (c.stage !== "resulted" || !c.outcome) continue;
    // A disowned receipt is no longer its agent's evidence, but one already under dispute stays in the pool so the finding can
    // still be decided: declaring a compromise does not close an open finding.
    if (c.disowned && c.disputedBy.length === 0) continue;
    receiptsByClaim.set(c.target, [...(receiptsByClaim.get(c.target) ?? []), { id: c.id, operatorId: c.operatorId, seq: c.seq }]);
    if (c.disowned || c.outcome === "inconclusive") continue;
    // A receipt whose outputs duplicate an earlier one's under a different seed adds nothing: the bundle ignored its seed.
    if (c.seedInsensitive) continue;
    if (held.has(c.id)) continue;
    evidence.push({ id: c.id, claim: c.target, kind: c.kind, confirms: c.outcome === "confirmed", agent: c.handle, operatorId: c.operatorId, tier: tierOf(c.operatorId), families: c.families, seq: c.seq });
  }
  for (const { key, ts, ...r } of reviews) if (!disownedAt(key, ts)) evidence.push({ ...r, tier: tierOf(r.operatorId) });
  evidence.sort((a, b) => a.seq - b.seq);

  // Rings: X confirmed a claim of Y's and Y confirmed a claim of X's.
  const confirmed = new Set<string>();
  for (const e of evidence) {
    if (!e.confirms) continue;
    const author = claimAuthorOp.get(e.claim);
    if (author && author !== e.operatorId) confirmed.add(`${e.operatorId}|${author}`);
  }
  const rings: Array<[string, string]> = [];
  for (const pair of confirmed) {
    const [x, y] = pair.split("|") as [string, string];
    if (x < y && confirmed.has(`${y}|${x}`)) rings.push([x, y]);
  }
  const ringKeys = new Set(rings.map(([x, y]) => `${x}|${y}`));
  const ringLinked = (a: string, b: string) => ringKeys.has(a < b ? `${a}|${b}` : `${b}|${a}`);

  const vouchLinked = (a: string, b: string) => vouches.some((v) => (v.from === a && v.for === b) || (v.from === b && v.for === a));
  return { tiers, vouches, suspendedVouchers, stewardVerified, rings, ringLinked, agents, keys, papers, claims, external, checks, findings, evidence, uses, voidedOperators, fabricators, lapses, receiptsByClaim, vouchLinked, anchors, forecasts, seedInsensitiveBundles, held };
}
