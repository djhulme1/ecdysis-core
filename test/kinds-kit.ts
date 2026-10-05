/**
 * scope/0.1 and kinds/0.1 (4 October 2026) made every new empirical claim
 * declare its scope (and a claim from human literature its fidelity to the
 * paper), and every commit declare what it tests (design). The tests written
 * before them exercise other rules: receipts, cross-checks, findings, keys,
 * holds, pages. This fills those fields, wherever a payload leaves them out,
 * with the declarations that keep their receipts what those tests meant them
 * to be: replication tests (reproductions: the stated method, run afresh on
 * new samples under the archive's seed) of claims general by construction.
 *
 * The rules themselves are tested in test/v2-kinds.test.ts, which never uses
 * this, so a payload that omits a field there is refused as it would be in
 * production.
 */
import type { Json } from "../src/core/canonical.js";

export const GENERAL: Json = { general: "construction", basis: "a named benchmark and setup: every run samples the same population" };
export const REPORTED: Json = { as: "reported", basis: "the test states the method and the thresholds the paper reports" };
export const REPRODUCTION: Json = { method: "stated", data: "new", basis: "the claim's stated method, run afresh on new samples under the archive's seed" };

/** A payload with the declarations it leaves out filled in (see above); anything it states is kept as it is. */
export function declared<T extends Json>(payload: T): T {
  const p = payload as Record<string, Json>;
  if (!p || typeof p !== "object" || Array.isArray(p)) return payload;
  if (p["type"] === "claim.external" && p["kind"] !== "conceptual" && !("scope" in p)) return { ...p, scope: GENERAL, ...("fidelity" in p ? {} : { fidelity: REPORTED }) } as unknown as T;
  if (p["type"] === "check.commit" && !("design" in p)) return { ...p, design: REPRODUCTION } as unknown as T;
  if (p["type"] === "claim" && p["kind"] !== "conceptual" && !("scope" in p)) return { ...p, scope: GENERAL } as unknown as T;
  return payload;
}
