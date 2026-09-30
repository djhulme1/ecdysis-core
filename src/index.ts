/**
 * Cloudflare Worker entry. Wires the service to D1, the platform rate
 * limiters, and the deployment's screening configuration. All secrets arrive
 * through bindings; nothing sensitive is in this file or this repo.
 */

import { EcdysisService } from "./api/service.js";
import { MemoryRateLimiter, route, type RateLimiter } from "./api/router.js";
import { D1Store } from "./store/d1-store.js";
import { configScreener, structuralScreener, type DenyRule, type Screener } from "./core/hazard.js";

export interface Env {
  DB: D1Database;
  ENVIRONMENT: string;
  PROTOCOL_VERSION: string;
  STH_PUBLIC_KEY: string;
  /** Secret: wrangler secret put STH_SIGNING_KEY_PKCS8 */
  STH_SIGNING_KEY_PKCS8?: string;
  /** Secret: JSON array of {pattern, flags, category, severity} rules,
   *  maintained outside this repo. See docs/deploy.md. */
  SCREENING_RULES?: string;
  RL_KEY?: { limit: (opts: { key: string }) => Promise<{ success: boolean }> };
  RL_OWNER?: { limit: (opts: { key: string }) => Promise<{ success: boolean }> };
}

function screenersFrom(env: Env): Screener[] {
  const screeners: Screener[] = [structuralScreener()];
  if (env.SCREENING_RULES) {
    try {
      const raw = JSON.parse(env.SCREENING_RULES) as Array<{
        pattern: string; flags?: string; category: string; severity: 2 | 3;
      }>;
      const rules: DenyRule[] = raw.map((r) => ({
        pattern: new RegExp(r.pattern, r.flags ?? "i"),
        category: r.category,
        severity: r.severity === 3 ? 3 : 2,
      }));
      screeners.push(configScreener(rules));
    } catch (e) {
      console.error("SCREENING_RULES failed to parse; failing closed", e);
      // A screener that always demands review: misconfiguration must never
      // silently disable screening.
      screeners.push({
        name: "config-broken",
        async screen() {
          return [{
            screener: "config-broken", severity: 2 as const,
            category: "screening-misconfigured",
            note: "SCREENING_RULES failed to parse; all submissions go to review",
          }];
        },
      });
    }
  } else if (env.ENVIRONMENT === "production") {
    // Production with no screening rules configured: fail closed entirely.
    screeners.push({
      name: "no-config",
      async screen() {
        return [{
          screener: "no-config", severity: 2 as const,
          category: "screening-not-configured",
          note: "no screening provider configured; all submissions go to review",
        }];
      },
    });
  }
  return screeners;
}

function limiterFrom(env: Env): RateLimiter {
  if (env.RL_KEY) {
    const rl = env.RL_KEY;
    return {
      async allow(bucket: string, id: string) {
        const { success } = await rl.limit({ key: `${bucket}:${id}` });
        return success;
      },
    };
  }
  return new MemoryRateLimiter();
}

export default {
  async fetch(req: Request, env: Env): Promise<Response> {
    const svc = new EcdysisService({
      store: new D1Store(env.DB),
      screeners: screenersFrom(env),
      sthPrivateKey: env.STH_SIGNING_KEY_PKCS8 ?? null,
      // v0.1: the log-signing keypair doubles as the operator key holding the
      // two reserved powers (R1 hazard decisions, R2 entrenched co-signature).
      // Split them, or move to threshold keys, without code changes here.
      operatorPublicKey: env.STH_PUBLIC_KEY?.startsWith("REPLACE") ? null : env.STH_PUBLIC_KEY ?? null,
    });
    return route(req, svc, limiterFrom(env));
  },
} satisfies ExportedHandler<Env>;
