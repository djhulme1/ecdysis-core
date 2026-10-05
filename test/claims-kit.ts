/**
 * network/0.1 for tests: a claim payload with everything a claim must carry
 * (text, test, confidence, field, rationale, what it builds on), signed, with
 * its id computed exactly as the archive computes it, "ecd:" and the first
 * 16 hex characters of the SHA-256 of {p: payload, s: signature}, so a test
 * can name a claim before it is sent, as an author writing a line does.
 *
 * Empirical claims get a scope general by construction unless the test gives
 * one (kinds-kit.ts, GENERAL): the rules of scope are tested in
 * test/v2-kinds.test.ts, which states every field itself.
 */
import { hashJson, type Json } from "../src/core/canonical.js";
import { signJson } from "../src/core/crypto.js";
import { claimIdOf } from "../src/core/v2/refs.js";
import { GENERAL } from "./kinds-kit.js";

export interface ClaimOpts {
  text?: string;
  test?: string;
  confidence?: number;
  field?: string;
  kind?: "empirical" | "conceptual";
  scope?: Json;
  data?: Json;
  rationale?: string;
  method?: string;
  artefacts?: string[];
  caveats?: string[];
  blockers?: Json[];
  builds_on?: Json[];
  models?: string[];
  ts?: string;
  /** Fields to leave out, so a test can send a claim without one. */
  omit?: string[];
  /** Fields a claim does not carry, to send anyway. */
  extra?: Record<string, Json>;
}

const TS = "2026-10-05T09:00:00Z";

/** A complete claim payload; `o` overrides any field, and `undefined` leaves one out. */
export function claimPayload(agent: { handle: string; publicKey: string }, o: ClaimOpts = {}): Json {
  const kind = o.kind ?? "empirical";
  const p: Record<string, Json | undefined> = {
    protocol: "ecdysis/0.2", type: "claim",
    text: o.text ?? "Grokking appears in modular addition after weight decay.",
    ...(o.kind ? { kind: o.kind } : {}),
    confidence: o.confidence ?? 0.7,
    test: o.test ?? "Test accuracy stays below 50% for 10^5 steps after the training loss converges.",
    field: o.field ?? "ml",
    ...(o.scope !== undefined ? { scope: o.scope } : kind === "conceptual" ? {} : { scope: GENERAL }),
    ...(o.data !== undefined ? { data: o.data } : {}),
    rationale: o.rationale ?? "Weight decay makes the generalising circuit cheaper than memorisation, so it wins once the loss has converged.",
    ...(o.method !== undefined ? { method: o.method } : {}),
    ...(o.artefacts !== undefined ? { artefacts: o.artefacts } : {}),
    ...(o.caveats !== undefined ? { caveats: o.caveats } : {}),
    ...(o.blockers !== undefined ? { blockers: o.blockers } : {}),
    builds_on: (o.builds_on ?? []) as Json,
    ...(o.models !== undefined ? { models: o.models } : {}),
    agent: { handle: agent.handle, publicKey: agent.publicKey },
    ts: o.ts ?? TS,
    ...(o.extra ?? {}),
  };
  for (const k of o.omit ?? []) delete p[k];
  return p as Json;
}

/** The id a signed claim will have: what the author can compute before sending. */
export async function claimIdFor(payload: Json, signature: string): Promise<string> {
  return claimIdOf(await hashJson({ p: payload, s: signature }));
}

/** A claim, signed: its envelope, its id and its cid (the full hash the archive keeps its envelope under). */
export async function signedClaim(agent: { handle: string; publicKey: string; privateKey: string }, o: ClaimOpts = {}): Promise<{ envelope: Json; id: string; cid: string; payload: Json }> {
  const payload = claimPayload(agent, o);
  const signature = await signJson(agent.privateKey, payload);
  const cid = await hashJson({ p: payload, s: signature });
  return { envelope: { payload, signature }, id: claimIdOf(cid), cid, payload };
}

/** A foundation: a claim this one relies on, with how (no citation on faith). */
export const relies = (id: string, rel: "extends" | "method" = "extends", basis: "reproduced" | "reviewed" = "reproduced"): Json =>
  ({ id, rel, basis, note: basis === "reproduced" ? "Re-ran its bundle under a fresh seed; the outputs matched within tolerance." : "Checked its method and data against the stated test." });
