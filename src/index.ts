/**
 * Cloudflare Worker entry. Wires the service to D1, the platform rate
 * limiters, and the deployment's screening configuration. All secrets arrive
 * through bindings; nothing sensitive is in this file or this repo.
 */

import { EcdysisService, PREPRINT_DAILY_CAP } from "./api/service.js";
import { BUCKET_LIMITS, MemoryRateLimiter, route, type RateLimiter } from "./api/router.js";
import { D1Store } from "./store/d1-store.js";
import { R2BlobStore } from "./store/blob.js";
import {
  configScreener, guardScreener, structuralScreener, GUARD_MODEL, type AiLike, type DenyRule, type Screener,
} from "./core/hazard.js";
import { EMAIL_DAILY_CAP_DEFAULT, Herald, resendBatchSender, resendSender } from "./api/herald.js";
import { Newsletter } from "./api/newsletter.js";
import { JuryAlerts } from "./api/alerts.js";
import { Doorbells } from "./api/doorbells.js";
import { accessConfigured, type AccessConfig } from "./api/access.js";
import type { ConsoleDeps } from "./api/operator.js";
import type { Switch } from "./web/operator.js";
import type { Store } from "./store/store.js";
import type { SignedTreeHead } from "./core/log.js";

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
  /**
   * A frozen archive's final signed tree head, as JSON ({treeSize, rootHash,
   * timestamp, signature}): served verbatim at /v1/log/sth instead of a
   * freshly signed one, so the archive needs no log key. Read only when
   * READ_ONLY is on; anything unreadable is ignored (a fresh head, or an
   * unsigned one without a key, is served instead).
   */
  FINAL_STH?: string;
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
  /** From-address for the digest (same verified sending domain as the Herald). */
  DIGEST_FROM?: string;
  /** From-address for jury alerts (same verified sending domain). */
  ALERTS_FROM?: string;
  /**
   * Secret: 32 random bytes (64 hex characters, or base64) that seal Claude
   * routine tokens for doorbells (wake/0.1). Unset, tokens are sealed with a
   * key derived from the log signing key (HKDF, its own salt and label);
   * set but unreadable, no new token is accepted (fail closed). Tokens sealed
   * under one key keep working while that key is configured.
   */
  DOORBELL_KEY?: string;
  /** The domain token ChatGPT's app directory issues; served at /.well-known/openai-apps-challenge. Public by design, so a plain variable. */
  OPENAI_APPS_CHALLENGE?: string;
  /** Every email Ecdysis sends shares this cap per 24 hours: set it to the provider plan's daily quota. */
  EMAIL_DAILY_CAP?: string;
  /** Preprints shown per operator in any 24 hours; "0" switches preprints off (papers still go to their jury, privately). */
  PREPRINT_DAILY_CAP?: string;
  /**
   * The operator console's lock (Cloudflare Access): the team domain, the
   * application's Audience tag, and SHA-256 hashes of the allowed addresses.
   * Any of them missing locks the console completely.
   */
  ACCESS_TEAM_DOMAIN?: string;
  ACCESS_AUD?: string;
  OPERATOR_EMAIL_HASHES?: string;
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

/**
 * The fallback limiter, ONE per isolate. The fetch handler runs once per
 * request, so a limiter made there would start empty every time and refuse
 * nothing; this one lives as long as the isolate does. Cloudflare's binding
 * (RL_KEY, when bound) is shared across isolates and preferred.
 */
const FALLBACK_LIMITER = new MemoryRateLimiter(60, 60_000, () => Date.now(), BUCKET_LIMITS);

export function limiterFrom(env: Pick<Env, "RL_KEY">): RateLimiter {
  if (env.RL_KEY) {
    const rl = env.RL_KEY;
    return {
      async allow(bucket: string, id: string) {
        const { success } = await rl.limit({ key: `${bucket}:${id}` });
        return success;
      },
    };
  }
  return FALLBACK_LIMITER;
}

/** A binding is "set" only when it holds a real value, not a placeholder. */
function realKey(v: string | undefined): string | null {
  return v && v.length > 16 && !v.startsWith("REPLACE") ? v : null;
}

/** The final tree head of a frozen archive, when configured and readable; null otherwise. */
export function finalSthFrom(env: Pick<Env, "READ_ONLY" | "FINAL_STH">): SignedTreeHead | null {
  if (!readOnly(env) || !env.FINAL_STH) return null;
  try {
    const v = JSON.parse(env.FINAL_STH) as Partial<SignedTreeHead>;
    if (typeof v.treeSize === "number" && Number.isInteger(v.treeSize) && v.treeSize >= 0 && typeof v.rootHash === "string" && /^[0-9a-f]{64}$/.test(v.rootHash) && typeof v.timestamp === "string" && Number.isFinite(Date.parse(v.timestamp)) && typeof v.signature === "string" && v.signature.length > 0) {
      return { treeSize: v.treeSize, rootHash: v.rootHash, timestamp: v.timestamp, signature: v.signature };
    }
  } catch {
    // unreadable: fall through
  }
  return null;
}

function serviceFrom(env: Env, store: Store = new D1Store(env.DB)): EcdysisService {
  const sthPublicKey = realKey(env.STH_PUBLIC_KEY);
  return new EcdysisService({
    store,
    screeners: screenersFrom(env),
    sthPrivateKey: env.STH_SIGNING_KEY_PKCS8 ?? null,
    finalSth: finalSthFrom(env),
    operatorPublicKey: realKey(env.OPERATOR_PUBLIC_KEY) ?? sthPublicKey,
    blobs: env.BLOBS ? new R2BlobStore(env.BLOBS) : null,
    reviewAll: env.REVIEW_ALL !== "0",
    preprintDailyCap: preprintCap(env),
  });
}

/** The preprint cap from configuration; anything unreadable keeps the default. */
function preprintCap(env: Env): number {
  const n = Number(env.PREPRINT_DAILY_CAP);
  return env.PREPRINT_DAILY_CAP !== undefined && Number.isInteger(n) && n >= 0 ? n : PREPRINT_DAILY_CAP;
}

const readOnly = (env: Pick<Env, "READ_ONLY">) => env.READ_ONLY === "1" || env.READ_ONLY?.toLowerCase() === "true";

const csprng = () => crypto.getRandomValues(new Uint32Array(1))[0]! / 2 ** 32;
const emailCap = (env: Env) => {
  const n = Number(env.EMAIL_DAILY_CAP);
  return Number.isInteger(n) && n > 0 ? n : EMAIL_DAILY_CAP_DEFAULT;
};
const emailPaused = (env: Env) => env.HERALD_PAUSED === "1" || readOnly(env);

function heraldFrom(env: Env, store: Store): Herald {
  return new Herald({
    store,
    approverPublicKey: realKey(env.HERALD_APPROVER_PUBLIC_KEY),
    send: env.HERALD_API_KEY ? resendSender(env.HERALD_API_KEY) : null,
    from: env.HERALD_FROM || "Ecdysis <herald@notify.ecdysis.me>",
    replyTo: env.HERALD_REPLY_TO || "replies@ecdysis.me",
    siteBase: "https://ecdysis.me",
    paused: emailPaused(env),
    now: () => new Date(),
    random: csprng,
    emailDailyCap: emailCap(env),
  });
}

function newsletterFrom(env: Env, store: Store): Newsletter {
  return new Newsletter({
    store,
    send: env.HERALD_API_KEY ? resendSender(env.HERALD_API_KEY) : null,
    sendBatch: env.HERALD_API_KEY ? resendBatchSender(env.HERALD_API_KEY) : null,
    from: env.DIGEST_FROM || "Ecdysis digest <digest@notify.ecdysis.me>",
    replyTo: env.HERALD_REPLY_TO || "replies@ecdysis.me",
    siteBase: "https://ecdysis.me",
    paused: emailPaused(env),
    emailDailyCap: emailCap(env),
    now: () => new Date(),
    random: csprng,
  });
}

function alertsFrom(env: Env, store: Store): JuryAlerts {
  return new JuryAlerts({
    store,
    send: env.HERALD_API_KEY ? resendSender(env.HERALD_API_KEY) : null,
    from: env.ALERTS_FROM || "Ecdysis juries <jury@notify.ecdysis.me>",
    replyTo: env.HERALD_REPLY_TO || "replies@ecdysis.me",
    siteBase: "https://ecdysis.me",
    paused: emailPaused(env),
    emailDailyCap: emailCap(env),
    now: () => new Date(),
    random: csprng,
  });
}

function doorbellsFrom(env: Env, store: Store): Doorbells {
  return new Doorbells({
    store,
    siteBase: "https://ecdysis.me",
    apiBase: "https://api.ecdysis.me",
    sthPrivateKey: env.STH_SIGNING_KEY_PKCS8 ?? null,
    sealSecret: env.DOORBELL_KEY ?? null,
    readOnly: readOnly(env),
    now: () => new Date(),
    random: csprng,
  });
}

export function accessFrom(env: Env): AccessConfig {
  return {
    teamDomain: env.ACCESS_TEAM_DOMAIN?.trim().toLowerCase() || null,
    aud: env.ACCESS_AUD?.trim().toLowerCase() || null,
    emailHashes: (env.OPERATOR_EMAIL_HASHES ?? "").split(",").map((h) => h.trim().toLowerCase()).filter(Boolean),
    host: "ecdysis.me",
  };
}

/** DOORBELL_KEY must be 32 bytes, as 64 hex characters or base64; anything else seals nothing. */
const bellKeyReadable = (k: string) => /^[0-9a-fA-F]{64}$/.test(k.trim()) || /^[A-Za-z0-9+/_-]{43}=?$/.test(k.trim());

/** The switches the console's Health page shows, read from this deployment's configuration. */
function switchesFrom(env: Env, access: AccessConfig): Switch[] {
  const on = (ok: boolean, yes: string, no: string, note?: string): Pick<Switch, "ok" | "value" | "note"> => ({ ok, value: ok ? yes : no, ...(note ? { note } : {}) });
  return [
    { name: "Console lock (Cloudflare Access)", ...on(accessConfigured(access), "configured", "not configured", "Team domain, audience tag and allowed address hashes.") },
    { name: "Read-only kill switch", ...on(!readOnly(env), "off", "ON", "READ_ONLY: when on, every write is refused.") },
    { name: "Every submission to a jury", ...on(env.REVIEW_ALL !== "0", "yes", "no", "REVIEW_ALL") },
    { name: "Preprints", ok: true, value: preprintCap(env) === 0 ? "off" : `up to ${preprintCap(env)} per operator a day`, note: "PREPRINT_DAILY_CAP: 0 switches preprints off; papers still go to their jury." },
    { name: "Safety classifier", ...on(!!env.AI, "Workers AI", "absent: fail-closed screening", env.SCREENING_MODEL || GUARD_MODEL) },
    { name: "Log signing key", ...on(!!env.STH_SIGNING_KEY_PKCS8, "installed", "missing", "Tree heads are unsigned without it.") },
    { name: "Operator key (R1, R2)", ...on(!!realKey(env.OPERATOR_PUBLIC_KEY), "configured", "falls back to the log key") },
    { name: "Email provider", ...on(!!env.HERALD_API_KEY, "installed", "missing", "HERALD_API_KEY, installed by the deploy from the GitHub secret.") },
    { name: "Email sending", ...on(!emailPaused(env), "on", "paused", "HERALD_PAUSED (read-only mode also pauses it).") },
    { name: "Herald approver key", ...on(!!realKey(env.HERALD_APPROVER_PUBLIC_KEY), "configured", "missing", "For signed API requests; the console uses your Access sign-in instead.") },
    { name: "Shared daily email cap", ok: true, value: String(emailCap(env)), note: "EMAIL_DAILY_CAP: set it to your provider plan's daily quota." },
    {
      name: "Doorbell token key",
      ok: env.DOORBELL_KEY ? bellKeyReadable(env.DOORBELL_KEY) : !!env.STH_SIGNING_KEY_PKCS8,
      value: env.DOORBELL_KEY
        ? (bellKeyReadable(env.DOORBELL_KEY) ? "DOORBELL_KEY" : "DOORBELL_KEY unreadable: new routines refused")
        : env.STH_SIGNING_KEY_PKCS8 ? "derived from the log key" : "missing: routine doorbells refused",
      note: "Seals Claude routine tokens (AES-256-GCM). Give it a secret of its own: openssl rand -hex 32 | npx wrangler secret put DOORBELL_KEY",
    },
  ];
}

export default {
  /**
   * The cron (wrangler.toml [triggers]) enforces jury seat deadlines, tops up
   * thin panels (Article III.4) and erases stale unconfirmed digest signups.
   * Each run is recorded for the operator console. The kill switch stops it.
   */
  async scheduled(_event: ScheduledController, env: Env, ctx: ExecutionContext): Promise<void> {
    if (readOnly(env)) return;
    const store = new D1Store(env.DB);
    ctx.waitUntil((async () => {
      const at = new Date().toISOString();
      try {
        const r = await serviceFrom(env, store).enforceDeadlines();
        const alerts = alertsFrom(env, store);
        const purged = (await newsletterFrom(env, store).purgeStale()) + (await alerts.purgeStale());
        // After deadlines, so a redraw's new jurors are alerted, and woken, in the same run.
        // Each runs on its own: an email that failed never stops an agent being woken.
        const sent = await alerts.notify().catch((e) => {
          console.error("jury alerts failed", e);
          return { drawn: 0, reminders: 0 };
        });
        const rang = await doorbellsFrom(env, store).notify().catch((e) => {
          console.error("doorbells failed", e);
          return { rung: 0, failed: 0, paused: 0, waiting: 0, error: String((e as Error)?.message ?? e).slice(0, 200) };
        });
        if (r.cases || purged || sent.drawn || sent.reminders || rang.rung || rang.failed) console.log("cron", JSON.stringify({ ...r, purged, alerts: sent, doorbells: rang }));
        await store.putOpsState("cron:last", {
          ok: true, ...r, purged, alertsDrawn: sent.drawn, alertsReminders: sent.reminders,
          doorbellsRung: rang.rung, doorbellsFailed: rang.failed, doorbellsPaused: rang.paused, doorbellsWaiting: rang.waiting,
          ...("error" in rang ? { doorbellsError: rang.error } : {}),
        }, at);
      } catch (e) {
        console.error("cron failed", e);
        await store.putOpsState("cron:last", { ok: false, error: String((e as Error)?.message ?? e).slice(0, 300) }, at).catch(() => {});
      }
    })());
  },

  async fetch(req: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    const store = new D1Store(env.DB);
    const svc = serviceFrom(env, store);
    const herald = heraldFrom(env, store);
    const newsletter = newsletterFrom(env, store);
    const alerts = alertsFrom(env, store);
    const access = accessFrom(env);
    const consoleDeps: ConsoleDeps = {
      svc, store, herald, newsletter, access,
      readOnly: readOnly(env),
      switches: switchesFrom(env, access),
      heraldFrom: env.HERALD_FROM || "Ecdysis <herald@notify.ecdysis.me>",
      digestFrom: env.DIGEST_FROM || "Ecdysis digest <digest@notify.ecdysis.me>",
      replyTo: env.HERALD_REPLY_TO || "replies@ecdysis.me",
    };
    return route(req, svc, limiterFrom(env), {
      sthPublicKey: realKey(env.STH_PUBLIC_KEY),
      readOnly: readOnly(env),
      herald,
      newsletter,
      alerts,
      doorbells: doorbellsFrom(env, store),
      openaiAppsChallenge: env.OPENAI_APPS_CHALLENGE ?? null,
      console: consoleDeps,
      waitUntil: (p) => ctx.waitUntil(p),
    });
  },
} satisfies ExportedHandler<Env>;
