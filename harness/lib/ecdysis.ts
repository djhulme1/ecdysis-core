/**
 * The staging harness's client: everything needed to populate and exercise
 * a STAGING deployment of Ecdysis over its public API, with as many
 * operators and agents as a run likes. It seeds the record after a reset
 * (harness/seed.ts) and is the scaffolding for the red team's own scripts.
 *
 *   const s = await Staging.connect();          // ECDYSIS_URL and STAGING_DOOR_KEY from the environment
 *   const op = await s.operator("x@staging.ecdysis.me", { tier: "verified" });
 *   const a = await s.agent("probe-1", op);
 *   const claim = await a.publish({ text: "…", test: "…", confidence: 0.8 });
 *   const c = await a.commit(claim.id);          // a receipt: commit, then result
 *   await a.result(c.id, "confirmed", { alpha: 1 }, c.crossCheck);
 *
 * It refuses to run against anything but a deployment whose index says it is
 * staging: the production index has no environment field, so the harness
 * cannot be pointed at the record of science by accident, and the staging
 * door (api/v2/staging-door.ts) exists nowhere else in any case. Every
 * request is marked as a probe, so a staging deployment's counters never
 * take a run for visitors.
 *
 * Signing and ids use the archive's own code (src/core), so an envelope made
 * here is exactly what an honest agent would send.
 */
import { hashJson, type Json } from "../../src/core/canonical.js";
import { generateKeyPair, signJson, type KeyPairB64 } from "../../src/core/crypto.js";
import { claimIdOf } from "../../src/core/v2/refs.js";
import { claimPayload, type ClaimOpts } from "../../test/claims-kit.js";
import { declared } from "../../test/kinds-kit.js";

export type Tier = "unverified" | "account" | "verified";
export interface Operator {
  email: string;
  operatorId: string;
  accountId: string;
  role: string;
  /** The one-use pairing code, spent by the first agent registered under it. */
  pairing: string | null;
  tier: Tier | null;
  /** The first agent registered under the operator, which sponsors the rest. */
  sponsorBy?: Agent;
}
export interface Bundle { repo: string; commit: string; image?: string; imageRef?: string; run: string; outputs: Array<{ name: string; tolerance?: number; relative?: boolean }>; runtimeMinutes: number }
export interface Commitment { id: string; status: number; seed: string | null; crossCheck: { receipt: string; outputs: Record<string, Json> } | null; body: Record<string, Json> }
export type Outputs = Record<string, number | string | boolean>;

const HEADERS = { accept: "application/json", "content-type": "application/json", "x-ecdysis-probe": "1" };
const DOOR_KEY = /^[0-9a-f]{64}$/i;

/** ISO-8601 UTC to the second, as the archive writes timestamps. */
export const ts = (d = new Date()): string => d.toISOString().replace(/\.\d{3}Z$/, "Z");

export class Staging {
  private constructor(readonly base: string, private doorKey: string | null, readonly constitution: { version: string; hash: string }) {}

  /**
   * Connect to the staging deployment named by ECDYSIS_URL, with the door key STAGING_DOOR_KEY (optional: without it, only
   * unpaired operators can be made). Refuses anything that does not say it is staging.
   */
  static async connect(base = process.env.ECDYSIS_URL ?? "", doorKey: string | null = process.env.STAGING_DOOR_KEY ?? null): Promise<Staging> {
    const b = base.replace(/\/+$/, "");
    if (!b) throw new Error("ECDYSIS_URL: the staging deployment's address");
    const index = (await (await fetch(`${b}/`, { headers: HEADERS })).json()) as { environment?: string };
    if (index.environment !== "staging") throw new Error(`refusing: ${b} does not say it is the staging deployment (environment: ${index.environment ?? "none"}); the harness runs against staging only`);
    const record = (await (await fetch(`${b}/v2/record`, { headers: HEADERS })).json()) as { constitution: { version: string; hash: string } | null };
    if (!record.constitution) throw new Error("the staging record has not opened: run the Staging workflow (genesis) first");
    if (doorKey !== null && !DOOR_KEY.test(doorKey)) throw new Error("STAGING_DOOR_KEY: 64 hex characters");
    return new Staging(b, doorKey, record.constitution);
  }

  async get<T = Json>(path: string): Promise<{ status: number; body: T }> {
    const r = await fetch(`${this.base}${path}`, { headers: HEADERS, signal: AbortSignal.timeout(30_000) });
    return { status: r.status, body: (await r.json()) as T };
  }
  async post<T = Json>(path: string, body: Json): Promise<{ status: number; body: T }> {
    const r = await fetch(`${this.base}${path}`, { method: "POST", headers: HEADERS, body: JSON.stringify(body), signal: AbortSignal.timeout(30_000) });
    return { status: r.status, body: (await r.json()) as T };
  }

  /** Through the staging door: an account for the address, its operator id, a pairing code, and the tier asked for. */
  async operator(email: string, o: { tier?: Tier; pairing?: boolean } = {}): Promise<Operator> {
    if (!this.doorKey) throw new Error("STAGING_DOOR_KEY is needed to make operators with accounts; set it, or use unpaired(…)");
    const r = await this.post<Record<string, Json>>("/staging/door", { key: this.doorKey, email, pairing: o.pairing ?? true, ...(o.tier ? { tier: o.tier } : {}) });
    if (r.status !== 200 && r.status !== 201) throw new Error(`the door refused ${email}: ${r.status} ${JSON.stringify(r.body)}`);
    return { email, operatorId: String(r.body["operatorId"]), accountId: String(r.body["accountId"]), role: String(r.body["role"]), pairing: typeof r.body["pairing"] === "string" ? r.body["pairing"] : null, tier: (r.body["tier"] as Tier | null | undefined) ?? null };
  }

  /** An operator with no account at all: any stable string, as the protocol allows (unverified, weighs a quarter). */
  unpaired(operatorId: string): Operator {
    return { email: "", operatorId, accountId: "", role: "none", pairing: null, tier: "unverified" };
  }

  /** Register an agent under an operator: a fresh key, held here, never anywhere else. */
  async agent(handle: string, op: Operator, models: string[] = []): Promise<Agent> {
    const keys = await generateKeyPair();
    const body: Record<string, Json> = { handle, publicKey: keys.publicKey, constitution: this.constitution, ...(models.length ? { models } : {}) };
    if (op.email) {
      // An account's operator id (op_…) takes agents by pairing code only, one code an agent: the door makes a fresh one each time.
      const code = op.pairing ?? (await this.operator(op.email, { pairing: true })).pairing;
      if (!code) throw new Error(`no pairing code for ${op.email}`);
      body["pairing"] = code;
      op.pairing = null;
    } else {
      body["operatorId"] = op.operatorId;
      // An operator id that already has agents is someone's: a second agent joins it with the first's sponsorship.
      if (op.sponsorBy) body["sponsor"] = await op.sponsorBy.sponsor(handle, keys.publicKey) as unknown as Json;
    }
    const r = await this.post<Record<string, Json>>("/v2/agents/register", body);
    if (r.status !== 201) throw new Error(`registration of ${handle} refused: ${r.status} ${JSON.stringify(r.body)}`);
    const a = new Agent(this, handle, keys, op.operatorId);
    if (!op.sponsorBy) op.sponsorBy = a;
    return a;
  }

  /** The record's numbers as the archive serves them. */
  async record(): Promise<Record<string, Json>> { return (await this.get<Record<string, Json>>("/v2/record")).body; }
  async claim(id: string): Promise<Record<string, Json>> { return (await this.get<Record<string, Json>>(`/v2/claims/${encodeURIComponent(id)}`)).body; }
  async leaderboard(): Promise<Record<string, Json>> { return (await this.get<Record<string, Json>>("/v2/leaderboard")).body; }
}

export class Agent {
  constructor(readonly s: Staging, readonly handle: string, readonly keys: KeyPairB64, readonly operatorId: string) {}

  /** Sign a payload as this agent: protocol, agent and ts added, the declarations a test payload leaves out filled in. */
  async sign(payload: Record<string, Json>): Promise<{ payload: Json; signature: string }> {
    const full = declared({ protocol: "ecdysis/0.2", ...payload, agent: { handle: this.handle, publicKey: this.keys.publicKey }, ts: ts() } as Json);
    return { payload: full, signature: await signJson(this.keys.privateKey, full) };
  }

  /** A sponsor signature so another agent may join this operator unpaired. */
  async sponsor(handle: string, publicKey: string): Promise<{ handle: string; signature: string }> {
    return { handle: this.handle, signature: await signJson(this.keys.privateKey, { op: "sponsor", handle, publicKey }) };
  }

  /** Publish one claim; its id is computed before sending, as an author writing a line does. */
  async publish(o: ClaimOpts): Promise<{ id: string; status: number; body: Record<string, Json> }> {
    const payload = claimPayload({ handle: this.handle, publicKey: this.keys.publicKey }, { ts: ts(), ...o });
    const signature = await signJson(this.keys.privateKey, payload);
    const id = claimIdOf(await hashJson({ p: payload, s: signature }));
    const r = await this.s.post<Record<string, Json>>("/v2/claims", { payload, signature });
    return { id, status: r.status, body: r.body };
  }

  /** A receipt's first step: commit a bundle against a claim. The reply carries the seed and, usually, a receipt to cross-check. */
  async commit(target: string, bundle: Bundle = defaultBundle(), kind: "rerun" | "replication" = "replication"): Promise<Commitment> {
    const r = await this.s.post<Record<string, Json>>("/v2/checks", await this.sign({ type: "check.commit", target, kind, bundle: bundle as unknown as Json }));
    const cross = r.body["crossCheck"] as { receipt: string; outputs: Record<string, Json> } | null | undefined;
    return { id: String(r.body["id"] ?? ""), status: r.status, seed: typeof r.body["seed"] === "string" ? r.body["seed"] : null, crossCheck: cross ?? null, body: r.body };
  }

  /** A receipt's second step: the outcome and outputs, and the cross-check's outputs when one was assigned. */
  async result(commit: string, outcome: "confirmed" | "failed" | "inconclusive", outputs: Outputs, crossCheck: { receipt: string; outputs: Record<string, Json> } | null): Promise<{ status: number; body: Record<string, Json> }> {
    return this.s.post<Record<string, Json>>("/v2/checks/result", await this.sign({ type: "check.result", commit, outcome, outputs, crossCheck: crossCheck as unknown as Json }));
  }

  async review(claim: string, forecast: number, rationale: string): Promise<{ status: number; body: Record<string, Json> }> {
    return this.s.post<Record<string, Json>>("/v2/reviews", await this.sign({ type: "review", claim, forecast, rationale }));
  }

  async attempt(claim: string, blocker: string, detail: string, unblockedBy: string): Promise<{ status: number; body: Record<string, Json> }> {
    return this.s.post<Record<string, Json>>("/v2/attempts", await this.sign({ type: "check.attempt", claim, blocker, detail, unblockedBy }));
  }
}

let bundles = 0;
/** A bundle that looks like a real one: the archive runs nothing, so what matters is the shape and the outputs declared. */
export function defaultBundle(): Bundle {
  bundles += 1;
  return { repo: "https://github.com/example/replication", commit: bundles.toString(16).padStart(40, "0"), image: `sha256:${"a".repeat(64)}`, run: "python run.py", outputs: [{ name: "alpha", tolerance: 0.01 }, { name: "solver" }], runtimeMinutes: 5 };
}

/** One line of JSON per finding, so a run's output can be kept and compared. */
export function report(run: string, result: Record<string, Json>): void {
  process.stdout.write(`${JSON.stringify({ run, at: ts(), ...result })}\n`);
}
