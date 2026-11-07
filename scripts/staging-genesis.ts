/**
 * Genesis on the STAGING record: adopt the constitution in force under
 * reserved power R2, signed with the staging operator key the Staging
 * workflow made moments ago and will never keep. Run by that workflow
 * (.github/workflows/staging.yml) after a reset's migrations and deploy.
 *
 * It adopts only on a deployment whose index says it is staging: the
 * production index carries no environment field, so this script cannot
 * open the record of science even by accident, and the production operator
 * key never passes through a workflow in any case (docs/FRESH-START.md).
 *
 * Environment:
 *   ECDYSIS_URL                    the staging deployment (its workers.dev address)
 *   STAGING_OPERATOR_PRIVATE_KEY   base64url PKCS#8, made in the same run
 */
import { signJson } from "../src/core/crypto.js";
import { CONSTITUTION_VERSION, constitutionHash } from "../src/core/constitution.js";

const BASE = (process.env.ECDYSIS_URL ?? "").replace(/\/+$/, "");
const KEY = process.env.STAGING_OPERATOR_PRIVATE_KEY ?? "";
if (!BASE) throw new Error("ECDYSIS_URL: the staging deployment's address");
if (!/^[A-Za-z0-9_-]{40,200}$/.test(KEY)) throw new Error("STAGING_OPERATOR_PRIVATE_KEY: the staging operator key, base64url PKCS#8");

const headers = { accept: "application/json", "x-ecdysis-probe": "1" };
const index = (await (await fetch(`${BASE}/`, { headers })).json()) as { environment?: string };
if (index.environment !== "staging") throw new Error(`refusing: ${BASE} does not say it is the staging deployment (environment: ${index.environment ?? "none"})`);

const record = (await (await fetch(`${BASE}/v2/record`, { headers })).json()) as { constitution: { version: string; hash: string } | null; agents: number };
if (record.constitution) {
  process.stdout.write(`staging-genesis: already adopted (${record.constitution.version} ${record.constitution.hash.slice(0, 8)}…), ${record.agents} agents; nothing to do\n`);
  process.exit(0);
}

// The text this checkout carries is the text the deployment carries: both came from the same commit.
const adoption = { version: CONSTITUTION_VERSION, hash: await constitutionHash(), ts: new Date().toISOString().replace(/\.\d{3}Z$/, "Z") };
const signature = await signJson(KEY, { op: "adopt", ...adoption });
const r = await fetch(`${BASE}/v2/constitution/adopt`, { method: "POST", headers: { ...headers, "content-type": "application/json" }, body: JSON.stringify({ ...adoption, signature }) });
const body = (await r.json()) as Record<string, unknown>;
if (r.status !== 201) throw new Error(`adoption refused: ${r.status} ${JSON.stringify(body)}`);
process.stdout.write(`staging-genesis: adopted constitution ${adoption.version} at seq ${String(body["seq"])} on ${BASE}\n`);

const sth = (await (await fetch(`${BASE}/v2/log/sth`, { headers })).json()) as { treeSize?: number; signature?: string };
if (sth.treeSize !== 1 || !sth.signature) throw new Error(`the head after genesis is not a signed head of size 1: ${JSON.stringify(sth)}`);
process.stdout.write("staging-genesis: the head is signed at size 1; the staging record is open\n");
