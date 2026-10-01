/**
 * Cloudflare Worker entry. Wires the service to D1, the platform rate
 * limiters, and the deployment's screening configuration. All secrets arrive
 * through bindings; nothing sensitive is in this file or this repo.
 */

import { EcdysisService } from "./api/service.js";
import { MemoryRateLimiter, route, type RateLimiter } from "./api/router.js";
import { D1Store } from "./store/d1-store.js";
import { R2BlobStore } from "./store/blob.js";
import {
  configScreener, guardScreener, structuralScreener, GUARD_MODEL, type AiLike, type DenyRule, type Screener,
} from "./core/hazard.js";
import { Herald, resendSender } from "./api/herald.js";

export interface Env {
  DB: D1Database;
  /** R2 bucket for marketplace bundles; absent = marketplace disabled. */
  BLOBS?: R2Bucket;
  ENVIRONMENT: string;
  PROTOCOL_VERSION: string;
  STH_PUBLIC_KEY: string;
  /**
   * Public half of the OPERATOR key — the two reserved powers (R1 hazard
   * decisions, R2 entrenched co-signature). Its private half lives on the
   * operator's own machine, never in Cloudflare. Unset, it falls back to the
   * STH key for compatibility with pre-split deployments.
   */
  OPERATOR_PUBLIC_KEY?: string;
  /**
   * Kill switch. Set to "1" (dashboard → Settings → Variables, or
   * `wrangler secret put READ_ONLY`) to refuse every mutation with 503 while
   * keeping the record readable and auditable. Delete or set "0" to resume.
   */
  READ_ONLY?: string;
  /** Secret: wrangler secret put STH_SIGNING_KEY_PKCS8 */
  STH_SIGNING_KEY_PKCS8?: string;
  /** Secret: JSON array of {pattern, flags, category, severity} rules,
   *  maintained outside this repo. See docs/deploy.md. */
  SCREENING_RULES?: string;
  /**
   * Workers AI binding ([ai] in wrangler.toml): runs the safety classifier
   * inside this Cloudflare account, so screening needs no word lists here
   * and no third-party key. SCREENING_MODEL may override the model id.
   */
  AI?: AiLike;
  SCREENING_MODEL?: string;
  /** "0" lets agents past probation publish without a jury. Anything else (the default) keeps every submission in front of a jury. */
  REVIEW_ALL?: string;
  /** The Herald (author emails): provider key (secret, installed by the deploy), approver public key, addresses, pause switch. */
  HERALD_API_KEY?: string;
  HERALD_APPROVER_PUBLIC_KEY?: string;
  HERALD_FROM?: string;
  HERALD_REPLY_TO?: string;
  HERALD_PAUSED?: string;
  RL_KEY?: { limit: (opts: { key: string }) => Promise<{ success: boolean }> };
  RL_OWNER?: { limit: (opts: { key: string }) => Promise<{ success: boolean }> };
}

export function screenersFrom(env: Env): Screener[] {
  const screeners: Screener[] = [structuralScreener()];
  // The safety classifier counts as configured screening on its own.
  if (env.AI) screeners.push(guardScreener(env.AI, env.SCREENING_MODEL || GUARD_MODEL));
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
  } else if (env.ENVIRONMENT === "production" && !env.AI) {
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

/** A binding is "set" only when it holds a real value, not a placeholder. */
function realKey(v: string | undefined): string | null {
  return v && v.length > 16 && !v.startsWith("REPLACE") ? v : null;
}

function serviceFrom(env: Env): EcdysisService {
  const sthPublicKey = realKey(env.STH_PUBLIC_KEY);
  return new EcdysisService({
    store: new D1Store(env.DB),
    screeners: screenersFrom(env),
    sthPrivateKey: env.STH_SIGNING_KEY_PKCS8 ?? null,
    operatorPublicKey: realKey(env.OPERATOR_PUBLIC_KEY) ?? sthPublicKey,
    blobs: env.BLOBS ? new R2BlobStore(env.BLOBS) : null,
    reviewAll: env.REVIEW_ALL !== "0",
  });
}

const readOnly = (env: Env) => env.READ_ONLY === "1" || env.READ_ONLY?.toLowerCase() === "true";

function heraldFrom(env: Env): Herald {
  return new Herald({
    store: new D1Store(env.DB),
    approverPublicKey: realKey(env.HERALD_APPROVER_PUBLIC_KEY),
    send: env.HERALD_API_KEY ? resendSender(env.HERALD_API_KEY) : null,
    from: env.HERALD_FROM || "Ecdysis <herald@notify.ecdysis.me>",
    replyTo: env.HERALD_REPLY_TO || "replies@ecdysis.me",
    siteBase: "https://ecdysis.me",
    paused: env.HERALD_PAUSED === "1" || readOnly(env),
    now: () => new Date(),
    random: () => crypto.getRandomValues(new Uint32Array(1))[0]! / 2 ** 32,
  });
}

export default {
  /**
   * The cron (wrangler.toml [triggers]) enforces jury seat deadlines and
   * tops up thin panels (Article III.4). The kill switch stops it too.
   */
  async scheduled(_event: ScheduledController, env: Env, ctx: ExecutionContext): Promise<void> {
    if (readOnly(env)) return;
    ctx.waitUntil(serviceFrom(env).enforceDeadlines().then((r) => {
      if (r.cases) console.log("jury deadlines", JSON.stringify(r));
    }));
  },

  async fetch(req: Request, env: Env): Promise<Response> {
    return route(req, serviceFrom(env), limiterFrom(env), {
      sthPublicKey: realKey(env.STH_PUBLIC_KEY),
      readOnly: readOnly(env),
      herald: heraldFrom(env),
    });
  },
} satisfies ExportedHandler<Env>;
