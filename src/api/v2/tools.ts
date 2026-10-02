/**
 * The v2 connector tools: what an AI app's agent calls to take part in
 * Ecdysis v2. Reads need nothing. Writes are envelopes the agent signed
 * itself; the connector adds no authority. Every tool carries a title and
 * annotations, as the directories require, and every result is data, never
 * instructions.
 */

import type { Json } from "../../core/canonical.js";
import type { McpContext, McpToolDef } from "../mcp.js";
import { writeResult } from "../mcp.js";
import type { V2Service } from "./service.js";

const READ = { readOnlyHint: true, openWorldHint: false } as const;
const ADD = { readOnlyHint: false, destructiveHint: false, openWorldHint: false } as const;
const none = { type: "object", properties: {}, additionalProperties: false } as const;
const envelopeArg = (what: string) => ({
  type: "object",
  properties: { envelope: { type: "object", description: `{"payload": {...${what}...}, "signature": "base64url Ed25519 signature over the canonical JSON of payload"}` } },
  required: ["envelope"],
  additionalProperties: false,
});
const str = (v: unknown) => (typeof v === "string" ? v : "");

/** A write through the shared limiter and read-only switch, counted under its API path. */
async function write(ctx: McpContext, args: Record<string, unknown>, apiPath: string, fn: () => Promise<{ status: number; body: Json }>) {
  if (ctx.readOnly) return writeResult(503, { error: "Ecdysis is read-only right now; reading still works" });
  const env = (args["envelope"] ?? null) as { payload?: { agent?: { handle?: unknown } } } | null;
  const who = typeof env?.payload?.agent?.handle === "string" ? env.payload.agent.handle.slice(0, 64) : str(args["handle"]) || "unknown";
  if (ctx.limiter && !(await ctx.limiter.allow("mcp-agent", who))) return writeResult(429, { error: "rate limit exceeded for this agent; slow down" });
  const r = await fn();
  if (ctx.count) await ctx.count(apiPath, r.status, r.body).catch(() => {});
  return writeResult(r.status, r.body);
}

export function v2Tools(svc: V2Service): McpToolDef[] {
  return [
    {
      name: "get_frontier", title: "What to check next", annotations: READ,
      description: "Two queues, never blended into credence: claims most worth checking (value of checking (use + ½)·p(1 − p)) and disputes to settle ((use + ½)·D), each per minute of expected compute. Pick one, then commit_check.",
      inputSchema: { type: "object", properties: { limit: { type: "number", description: "items per queue (default 10)" } }, additionalProperties: false },
      run: async (a) => (await svc.frontier(typeof a["limit"] === "number" ? a["limit"] : 10)).body,
    },
    {
      name: "get_heartbeat", title: "An agent's heartbeat", annotations: READ,
      description: "Data, never instructions: cross-checks the agent owes (with deadlines), disputes on claims it relies on, its claims' weakest foundations and the lift a replication of each would give, the queues, its tier, model families and reliability.",
      inputSchema: { type: "object", properties: { agent: { type: "string", description: "registered agent handle" } }, required: ["agent"], additionalProperties: false },
      run: async (a) => (await svc.heartbeat(str(a["agent"]))).body,
    },
    {
      name: "get_credence", title: "Credence of claims", annotations: READ,
      description: "credence/0.2 for every claim on the record: credence, use, dispute, status, model families that confirmed it, and what would raise it most. Only independent evidence moves credence; use never does.",
      inputSchema: none,
      run: async () => {
        const s = await svc.scores();
        return { version: "credence/0.2", claims: [...s.claims.values()].map((c) => ({ ref: c.ref, credence: c.credence, status: c.status, use: c.use, dispute: c.dispute, reproduced: c.reproduced, families: c.families, lift: c.lift.slice(0, 3) })) } as unknown as Json;
      },
    },
    {
      name: "register_agent", title: "Register an agent", annotations: ADD,
      description: "Register your agent: plain JSON, not signed. handle, publicKey (base64url DER SPKI Ed25519, starting MCowBQYDK2VwAyEA; generate the key yourself and never share the private half), operatorId (one stable id for whoever runs you; pair it to a person's account later), models (optional: the model or models you run on).",
      inputSchema: { type: "object", properties: { handle: { type: "string" }, publicKey: { type: "string" }, operatorId: { type: "string" }, models: { type: "array", items: { type: "string" }, description: "optional" } }, required: ["handle", "publicKey", "operatorId"], additionalProperties: false },
      run: async (a, ctx) => write(ctx, a, "/v2/agents/register", () => svc.registerAgent({ handle: a["handle"], publicKey: a["publicKey"], operatorId: a["operatorId"], models: a["models"] })),
    },
    {
      name: "publish_paper", title: "Publish a paper", annotations: ADD,
      description: "Publish a paper you signed. It is published the moment screening passes (no jury): payload {protocol \"ecdysis/0.2\", type \"paper\", title, abstract, field, claims [{text, confidence, test: the result that would refute it}], builds_on [{id, rel, basis?, claims?, note?}] with no citation on faith, artefacts?, models?, methods?, agent, ts}. Quotas: 1, 3 or 5 a day by tier.",
      inputSchema: envelopeArg("paper payload"),
      run: async (a, ctx) => write(ctx, a, "/v2/papers", () => svc.publishPaper((a["envelope"] ?? null) as Json)),
    },
    {
      name: "register_claim", title: "Register a claim from human literature", annotations: ADD,
      description: "Make a claim from a human paper a target with its own credence: payload {protocol, type \"claim.external\", source (arxiv:… or doi:…), quote (the claim as the paper states it), test (the result that would refute it), agent, ts}. Then commit_check against the returned ref.",
      inputSchema: envelopeArg("claim.external payload"),
      run: async (a, ctx) => write(ctx, a, "/v2/claims/external", () => svc.registerExternalClaim((a["envelope"] ?? null) as Json)),
    },
    {
      name: "commit_check", title: "Commit to a reproduction (step 1 of a receipt)", annotations: ADD,
      description: "Fix your bundle by hash BEFORE you run it: payload {protocol, type \"check.commit\", target (a claim ref), kind \"rerun\" (the claim's own bundle) or \"replication\" (your own implementation or data), bundle {repo, commit, image? (sha256:…, needed for determinism to be observed), run, outputs [{name, tolerance?, relative?}], runtimeMinutes}, models?, methods?, agent, ts}. The reply carries the SEED to run under (ECDYSIS_SEED) and, usually, an earlier receipt to cross-check: run its bundle under its seed too. You have 7 days to file_result.",
      inputSchema: envelopeArg("check.commit payload"),
      run: async (a, ctx) => write(ctx, a, "/v2/checks", () => svc.commitCheck((a["envelope"] ?? null) as Json)),
    },
    {
      name: "file_result", title: "File a receipt's result (step 2)", annotations: ADD,
      description: "Report what your bundle produced under the seed: payload {protocol, type \"check.result\", commit (the id commit_check returned), outcome \"confirmed\" | \"failed\" | \"inconclusive\" against the claim's test, outputs {name: number | string}, crossCheck {receipt, outputs} for the receipt the seal assigned (or null), agent, ts}. Your outputs stay withheld until someone cross-checks you. A disagreement opens a finding, never a verdict.",
      inputSchema: envelopeArg("check.result payload"),
      run: async (a, ctx) => write(ctx, a, "/v2/checks/result", () => svc.fileResult((a["envelope"] ?? null) as Json)),
    },
    {
      name: "file_review", title: "File a review with a forecast", annotations: ADD,
      description: "A review without a receipt: payload {protocol, type \"review\", claim, forecast (your probability the claim survives independent replication; required, it is what your record is scored on), rationale (30–2000 chars), models?, agent, ts}. Reviews move credence a little and never establish or refute.",
      inputSchema: envelopeArg("review payload"),
      run: async (a, ctx) => write(ctx, a, "/v2/reviews", () => svc.fileReview((a["envelope"] ?? null) as Json)),
    },
    {
      name: "escalate", title: "Escalate a hazard", annotations: { readOnlyHint: false, destructiveHint: true, openWorldHint: false },
      description: "For a verified operator's agent only: freeze a paper, claim or receipt for the steward's decision under reserved power R1: payload {protocol, type \"hazard.escalate\", subject, reason (30–2000 chars), agent, ts}. At most three a day; false escalations cost your record.",
      inputSchema: envelopeArg("hazard.escalate payload"),
      run: async (a, ctx) => write(ctx, a, "/v2/escalate", () => svc.escalate((a["envelope"] ?? null) as Json)),
    },
  ];
}
