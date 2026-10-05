/**
 * Cloudflare Worker entry. Wires the service to D1, the platform rate
 * limiters, and the deployment's screening configuration. All secrets arrive
 * through bindings; nothing sensitive is in this file or this repo.
 */

import { EcdysisService, PREPRINT_DAILY_CAP } from "./api/service.js";
import { BUCKET_LIMITS, MemoryRateLimiter, route, type RateLimiter } from "./api/router.js";
import { V2Cache, V2Service } from "./api/v2/service.js";
import { Accounts } from "./api/v2/accounts.js";
import { MeHandler } from "./api/v2/me.js";
import { StewardHandler } from "./api/v2/steward.js";
import { PagesHandler } from "./api/v2/pages.js";
import { Notifier } from "./api/v2/notify.js";
import { V2Governance } from "./api/v2/governance.js";
import { OAuth } from "./api/v2/oauth.js";
import { OAuthHandler } from "./api/v2/oauth-http.js";
import { V2Feeds } from "./api/v2/feed.js";
import { CanaryRegistry } from "./api/v2/canaries.js";
import { D1CanaryStore } from "./store/v2/canaries-d1.js";
import { ComplaintsHandler, IssueRegistry } from "./api/v2/issues.js";
import { D1IssueStore } from "./store/v2/issues-d1.js";
import { QuoteScout } from "./api/v2/quotes.js";
import { StakesScout, type CandidateSet, type CandidateStore } from "./api/v2/stakes-scout.js";
import { D1QuoteCheckStore } from "./store/v2/quotes-d1.js";
import { sha256Hex } from "./api/access.js";
import { D1OAuthStore } from "./store/v2/oauth-d1.js";
import { TransparencyLog } from "./core/log.js";
import { D1V2Store } from "./store/v2/d1.js";
import { D1AccountStore } from "./store/v2/accounts-d1.js";
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
import { signJson, verifyJson } from "./core/crypto.js";
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
   * Ecdysis v2 (docs/v2/PLAN.md): "1" serves v2 (pages, /v2/*, the v2
   * connector tools) from this deployment. On since the switchover of
   * 3 October 2026, with v2's own database and log key.
   */
  ECDYSIS_V2?: string;
  /** Where the frozen v1 record lives after the switchover (https://v1.ecdysis.me); linked from v2's landing page when set. */
  V1_ARCHIVE_URL?: string;
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
   * Finding categories (comma-separated, matching the rules' and the classifier's labels) that are the stewards' business
   * rather than a hazard: a paper with such findings is published and put under review for a steward; a short text is
   * refused. Deployment configuration, like the rules themselves. Unset: every review verdict goes to R1.
   */
  SCREEN_STEWARD_CATEGORIES?: string;
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
  /** Where a new complaint is announced (a comma-separated list of addresses: the stewards' own); unset, nobody is emailed and the queue waits to be read. */
  ISSUE_ALERT_TO?: string;
  HERALD_APPROVER_PUBLIC_KEY?: string;
  HERALD_FROM?: string;
  HERALD_REPLY_TO?: string;
  HERALD_PAUSED?: string;
  /** From-address for the digest (same verified sending domain as the Herald). */
  DIGEST_FROM?: string;
  /** From-address for jury alerts (same verified sending domain). */
  ALERTS_FROM?: string;
  /** From-address for email doorbells (same verified sending domain); every ring and confirmation comes from it, so filters can name it. */
  DOORBELL_FROM?: string;
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
  /**
   * Secret: 32 random bytes as 64 hex characters, keying the account store
   * (v2): emails are kept as an HMAC under it for lookup and sealed under it
   * for sending. Unset or unreadable: accounts are closed (fail closed).
   * openssl rand -hex 32 | npx wrangler secret put ACCOUNTS_KEY
   */
  ACCOUNTS_KEY?: string;
  /** Sender for sign-in links; defaults to accounts@notify.ecdysis.me. */
  ACCOUNTS_FROM?: string;
  /**
   * Cloudflare's rate-limiting bindings (wrangler.toml, [[ratelimits]]): one
   * limit per binding, per key, per Cloudflare location, shared by every
   * isolate there. RL_KEY carries the ordinary ceiling (reads and writes per
   * address), RL_MCP the connector's per-connection ceiling, RL_AGENT the
   * connector's per-agent one. Any that is missing falls back to the
   * in-memory limiter for its buckets alone.
   */
  RL_KEY?: RateLimitBinding;
  RL_MCP?: RateLimitBinding;
  RL_AGENT?: RateLimitBinding;
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

export interface RateLimitBinding {
  limit: (opts: { key: string }) => Promise<{ success: boolean }>;
}

/**
 * The fallback limiter, ONE per isolate. The fetch handler runs once per
 * request, so a limiter made there would start empty every time and refuse
 * nothing; this one lives as long as the isolate does. Cloudflare's bindings,
 * when bound, are shared across the isolates of a location and preferred.
 */
const FALLBACK_LIMITER = new MemoryRateLimiter(60, 60_000, () => Date.now(), BUCKET_LIMITS);

/**
 * The limiter for a request: each bucket goes to the binding that carries
 * its ceiling (one binding has one limit for every key, so the connector's
 * 600 a minute cannot share RL_KEY's 60), and a bucket whose binding is not
 * bound, or whose binding fails, falls back to the in-memory limiter, so
 * there is always a ceiling and a platform hiccup never opens the gates.
 */
export function limiterFrom(env: Pick<Env, "RL_KEY" | "RL_MCP" | "RL_AGENT">): RateLimiter {
  if (!env.RL_KEY && !env.RL_MCP && !env.RL_AGENT) return FALLBACK_LIMITER;
  const bindingFor = (bucket: string): RateLimitBinding | undefined => {
    if (bucket === "mcp") return env.RL_MCP;
    if (bucket === "mcp-agent") return env.RL_AGENT;
    // Every other bucket carries the default ceiling, which is RL_KEY's; a bucket with a ceiling of its own and no binding falls back.
    return BUCKET_LIMITS[bucket] === undefined ? env.RL_KEY : undefined;
  };
  return {
    async allow(bucket: string, id: string) {
      const rl = bindingFor(bucket);
      if (!rl) return FALLBACK_LIMITER.allow(bucket, id);
      try {
        const { success } = await rl.limit({ key: `${bucket}:${id}` });
        return success;
      } catch {
        return FALLBACK_LIMITER.allow(bucket, id);
      }
    },
  };
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

/** Ecdysis v2, when switched on: the same log and database, the v2 tables, the log key as the sealer. */
/** Accounts for people (v2), present whenever v2 is; closed without ACCOUNTS_KEY. */
function accountsFrom(env: Env, store: D1AccountStore): Accounts {
  return new Accounts({
    store,
    key: env.ACCOUNTS_KEY ?? null,
    // The email pause switch covers sign-in links too: paused, accounts can still be used but not entered.
    send: env.HERALD_API_KEY && !emailPaused(env) ? resendSender(env.HERALD_API_KEY) : null,
    from: env.ACCOUNTS_FROM || "Ecdysis <accounts@notify.ecdysis.me>",
    replyTo: env.HERALD_REPLY_TO || "replies@ecdysis.me",
    siteBase: "https://ecdysis.me",
    stewardEmailHashes: accessFrom(env).emailHashes,
  });
}

/**
 * One per isolate: the v2 log's rows and the records derived from them. The
 * handlers below are built per request (they are cheap); the cache is not, so
 * the log is read once and extended, and a burst of requests derives the
 * record once a minute rather than once a request.
 */
const V2_CACHE = new V2Cache();

function v2From(env: Env, store: D1Store, waitUntil: ((p: Promise<unknown>) => void) | null = null, frozen = readOnly(env), keysAgree = true): { v2: V2Service; me: MeHandler; steward: StewardHandler; pages: PagesHandler; notifier: Notifier; governance: V2Governance; oauth: { logic: OAuth; http: OAuthHandler }; complaints: ComplaintsHandler; quotes: QuoteScout; stakes: StakesScout; issues: IssueRegistry } | null {
  if (env.ECDYSIS_V2 !== "1") return null;
  const accountStore = new D1AccountStore(env.DB);
  const accounts = accountsFrom(env, accountStore);
  const log = new TransparencyLog(store);
  const v2 = new V2Service({
    log,
    cache: V2_CACHE,
    store: new D1V2Store(env.DB, store),
    logPrivateKey: env.STH_SIGNING_KEY_PKCS8 ?? null,
    screeners: screenersFrom(env),
    stewardCategories: new Set((env.SCREEN_STEWARD_CATEGORIES ?? "").split(",").map((c) => c.trim()).filter(Boolean)),
    pairing: (code, ip) => accounts.consumePairing(code, ip),
    // R1 needs the operator key and only that (never the log key, which lives in this Worker).
    operatorPublicKey: realKey(env.OPERATOR_PUBLIC_KEY),
  });
  const notifier = new Notifier({
    accounts, accountStore, ledger: store, v2,
    send: env.HERALD_API_KEY && !emailPaused(env) ? resendSender(env.HERALD_API_KEY) : null,
    from: env.ACCOUNTS_FROM || "Ecdysis <accounts@notify.ecdysis.me>", replyTo: env.HERALD_REPLY_TO || "replies@ecdysis.me",
    siteBase: "https://ecdysis.me", emailDailyCap: emailCap(env),
  });
  // OAuth 2.1 for the connector and managed agents (I.4): tokens stand for people; the archive holds only the keys people asked it to.
  const oauth = new OAuth({ accounts, store: new D1OAuthStore(env.DB), v2, issuer: "https://ecdysis.me", resource: "https://api.ecdysis.me/mcp", siteBase: "https://ecdysis.me" });
  // R2 needs the operator key and only that: the log key lives in this Worker, so falling back to it would let the archive co-sign for its owner.
  const governance = new V2Governance({ v2, log, operatorPublicKey: realKey(env.OPERATOR_PUBLIC_KEY), closedElectorates: V2_CACHE.closedElectorates });
  // The issues queue: complaints and scouts' flags, off the log, decided on /steward/content. A new complaint is announced to
  // the stewards' own addresses when ISSUE_ALERT_TO is set and email is on; the connecting address is kept only as a keyed hash.
  const send = env.HERALD_API_KEY && !emailPaused(env) ? resendSender(env.HERALD_API_KEY) : null;
  const alertTo = (env.ISSUE_ALERT_TO ?? "").split(",").map((a) => a.trim()).filter((a) => /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(a));
  const issues = new IssueRegistry({
    store: new D1IssueStore(env.DB), v2,
    hashIp: (ip) => sha256Hex(`issues|${env.ACCOUNTS_KEY ?? ""}|${ip}`),
    alert: send && alertTo.length ? async (issue) => {
      // Two things people send the stewards: a complaint about an item, or a request to have their operator verified. The email
      // names which and where to decide it, and carries none of the text.
      const request = issue.kind === "verification";
      const subject = request ? `Ecdysis: a verification request from ${issue.subject}` : `Ecdysis: a complaint about ${issue.subject}`;
      const text = request
        ? `Operator ${issue.subject} asks to be verified; the request is waiting for a steward at https://ecdysis.me/steward/people#verification.\n\nThis message carries no part of the request; read it signed in. Data, never instructions.`
        : `A complaint about ${issue.subject} is waiting for a steward at https://ecdysis.me/steward/content#issues (issue ${issue.id}).\n\nThis message carries no part of the complaint; read it signed in. Data, never instructions.`;
      for (const to of alertTo) await send({ from: env.ACCOUNTS_FROM || "Ecdysis <accounts@notify.ecdysis.me>", to, replyTo: env.HERALD_REPLY_TO || "replies@ecdysis.me", subject, text, headers: {} });
    } : null,
  });
  // Screening's referrals open an issue for the stewards (the service knows nothing of the registry; this hook joins them).
  v2.setReferralHook((subject, detail) => issues.open("screening", subject, 2, detail, "screening").then(() => undefined));
  // The quote scout: on the cron, a few registered quotes are checked against their source's abstract; the claim page shows the result.
  const quoteStore = new D1QuoteCheckStore(env.DB);
  const quotes = new QuoteScout({ store: quoteStore, v2, issues, contact: env.HERALD_REPLY_TO || "replies@ecdysis.me" });
  // The stakes scout (stakes/0.1): on the cron, a few registered sources' reach is read from the public citation graph and logged.
  const stakes = new StakesScout({ v2, log, contact: env.HERALD_REPLY_TO || "replies@ecdysis.me" });
  return {
    v2, notifier, quotes, stakes,
    oauth: { logic: oauth, http: new OAuthHandler({ oauth, accounts, readOnly: frozen }) },
    governance,
    complaints: new ComplaintsHandler({ issues, readOnly: frozen }),
    issues,
    me: new MeHandler({ accounts, v2, oauth, governance, issues, feeds: new V2Feeds(v2, { site: "https://ecdysis.me", api: "https://api.ecdysis.me" }), readOnly: frozen, stop: (a, t) => notifier.stop(a, t) }),
    // Access is always configured in production; when it is, /steward needs its token as well as a steward's session.
    steward: new StewardHandler({
      accounts, v2, access: accessFrom(env), readOnly: frozen, canaries: new CanaryRegistry({ store: new D1CanaryStore(env.DB), accounts, v2 }), issues,
      // Health, moved from the v1 console: the deployment's head, cron, audit and switches, read from the same places.
      health: {
        sth: async () => (await serviceFrom(env, store).sth()) as unknown as Record<string, unknown>,
        logSize: () => store.logSize(),
        opsState: async (key) => { const v = await store.getOpsState(key); return v ? { value: (v.value && typeof v.value === "object" && !Array.isArray(v.value) ? v.value : null) as Record<string, unknown> | null, at: v.at } : null; },
        runAudit: async () => {
          const r = await serviceFrom(env, store).audit();
          const body = r.body as { intact?: boolean; problem?: string | null };
          const size = await store.logSize();
          await store.putOpsState("audit:last", { intact: !!body.intact, problem: body.problem ?? null, size }, new Date().toISOString());
          return { intact: !!body.intact, problem: body.problem ?? null, size };
        },
        switches: switchesFrom(env, accessFrom(env), keysAgree),
      },
    }),
    pages: new PagesHandler(v2, {
      host: "api.ecdysis.me", logPublicKey: realKey(env.STH_PUBLIC_KEY), governance, accounts, archive: env.V1_ARCHIVE_URL ?? null, quotes: quoteStore,
      count: async (keys) => { for (const k of keys) await store.bumpAccess(k).catch(() => {}); },
      ...(waitUntil ? { waitUntil } : {}),
    }),
  };
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

/**
 * The doorbells, for the request path and the cron alike. With v2 on, the
 * agents live on the log, so the v2 service must be passed: without it the
 * resolver falls back to v1's agents table, which knows no v2 agent, and
 * every v2 agent's doorbell.set is refused as "unknown agent" (as happened
 * live on 3 October, when the request path was built without v2).
 */
export function doorbellsFrom(
  env: Pick<Env, "STH_SIGNING_KEY_PKCS8" | "DOORBELL_KEY" | "READ_ONLY"> & Partial<Pick<Env, "HERALD_API_KEY" | "HERALD_PAUSED" | "HERALD_REPLY_TO" | "EMAIL_DAILY_CAP" | "DOORBELL_FROM">>,
  store: Store,
  v2: V2Service | null,
): Doorbells {
  const cap = Number(env.EMAIL_DAILY_CAP);
  return new Doorbells({
    store,
    siteBase: "https://ecdysis.me",
    apiBase: "https://api.ecdysis.me",
    sthPrivateKey: env.STH_SIGNING_KEY_PKCS8 ?? null,
    sealSecret: env.DOORBELL_KEY ?? null,
    readOnly: readOnly(env),
    now: () => new Date(),
    random: csprng,
    // Email doorbells: the same provider, pause switch and shared daily cap as every other email Ecdysis sends.
    email: {
      send: env.HERALD_API_KEY && env.HERALD_PAUSED !== "1" && !readOnly(env) ? resendSender(env.HERALD_API_KEY) : null,
      from: env.DOORBELL_FROM || "Ecdysis doorbell <wake@notify.ecdysis.me>",
      replyTo: env.HERALD_REPLY_TO || "replies@ecdysis.me",
      dailyCap: Number.isInteger(cap) && cap > 0 ? cap : EMAIL_DAILY_CAP_DEFAULT,
    },
    // v2 adds its own reasons to ring (owed checks, disputes on what an agent relies on) and its agents live on the log,
    // not in v1's table: a doorbell is theirs to set with the main key only.
    ...(v2 ? {
      v2: true,
      extraReasons: (handles: string[]) => v2.ringReasons(handles),
      resolveAgent: async (handle: string) => { const a = (await v2.record()).agents.get(handle); return a && !a.revokedAt ? { publicKey: a.publicKey, operatorId: a.operatorId } : null; },
    } : {}),
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

let KEY_AGREEMENT: Promise<boolean> | null = null;
/**
 * Once per isolate: the installed log key must be the other half of the
 * pinned public key. If it is not (a key swapped by mistake, or the new
 * key installed before the pin was changed at a switchover), every write
 * is refused as if the kill switch were on: a seal or a head the pinned
 * key cannot verify must never be made. Nothing to compare (no pin, or no
 * key) passes: unsigned heads are a known state, not a mismatch.
 */
export async function logKeysAgree(env: Pick<Env, "STH_SIGNING_KEY_PKCS8" | "STH_PUBLIC_KEY">): Promise<boolean> {
  const pub = realKey(env.STH_PUBLIC_KEY);
  const prv = env.STH_SIGNING_KEY_PKCS8;
  if (!pub || !prv) return true;
  if (!KEY_AGREEMENT) {
    KEY_AGREEMENT = (async () => {
      try {
        const probe = { op: "key-check" };
        return await verifyJson(pub, probe, await signJson(prv, probe));
      } catch {
        return false;
      }
    })();
  }
  return KEY_AGREEMENT;
}
/** Tests only: forget the cached answer. */
export function resetKeyAgreement(): void {
  KEY_AGREEMENT = null;
}

/** DOORBELL_KEY must be 32 bytes, as 64 hex characters or base64; anything else seals nothing. */
const bellKeyReadable = (k: string) => /^[0-9a-fA-F]{64}$/.test(k.trim()) || /^[A-Za-z0-9+/_-]{43}=?$/.test(k.trim());

/** The switches the console's Health page shows, read from this deployment's configuration. */
/**
 * The v1 operator console (/operator) is view-only on a v2 deployment: its
 * actions (Herald drafts, juror invites, v1 controls) belong to the record
 * that was frozen at the switchover, and stewardship moved to /steward. Its
 * pages still answer, behind Access, for the Health view. Frozen deployments
 * are view-only as before.
 */
export function consoleReadOnly(env: Pick<Env, "ECDYSIS_V2">, frozen: boolean): boolean {
  return frozen || env.ECDYSIS_V2 === "1";
}

function switchesFrom(env: Env, access: AccessConfig, keysAgree = true): Switch[] {
  const on = (ok: boolean, yes: string, no: string, note?: string): Pick<Switch, "ok" | "value" | "note"> => ({ ok, value: ok ? yes : no, ...(note ? { note } : {}) });
  return [
    ...(env.ECDYSIS_V2 === "1" ? [{ name: "Ecdysis v2", ok: true, value: "live: this console is view-only", note: "Stewardship is at /steward; the v1 record is archived. Addresses in OPERATOR_EMAIL_HASHES are the stewards." }] : []),
    { name: "Console lock (Cloudflare Access)", ...on(accessConfigured(access), "configured", "not configured", "Team domain, audience tag and allowed address hashes.") },
    { name: "Read-only kill switch", ...on(!readOnly(env), "off", "ON", "READ_ONLY: when on, every write is refused.") },
    { name: "Log key matches its pin", ...on(keysAgree, "yes", "NO: writes refused", "The installed signing key must be the other half of STH_PUBLIC_KEY; until it is, every write is refused.") },
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
   * thin panels (Article III.4), erases stale unconfirmed digest signups and,
   * when v2 is on, seals orphaned commitments and lapses overdue checks.
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
        const v2 = v2From(env, store);
        const rang = await doorbellsFrom(env, store, v2?.v2 ?? null).notify().catch((e) => {
          console.error("doorbells failed", e);
          return { rung: 0, failed: 0, paused: 0, waiting: 0, error: String((e as Error)?.message ?? e).slice(0, 200) };
        });
        // v2: seal any commitment whose seal never reached the log, and lapse sealed checks past their deadline.
        const swept = v2 ? await v2.v2.sweepLapses().catch((e) => { console.error("v2 sweep failed", e); return { lapsed: [] as string[], sealed: [] as string[] }; }) : { lapsed: [], sealed: [] };
        // v2: alert emails people asked for, once each, within the shared daily cap.
        const alerted = v2 ? await v2.notifier.run().catch((e) => { console.error("v2 alerts failed", e); return { sent: 0, skipped: 0, events: 0 }; }) : { sent: 0, skipped: 0, events: 0 };
        const digested = v2 ? await v2.notifier.digest().catch((e) => { console.error("v2 digest failed", e); return { sent: 0, skipped: 0 }; }) : { sent: 0, skipped: 0 };
        // v2: a few registered quotes checked against their sources (arXiv asks for a pause between requests; six a run, every quarter hour, is well within it).
        const quoted = v2 ? await v2.quotes.run(6).catch((e) => { console.error("quote scout failed", e); return { checked: 0, verified: 0, mismatched: 0, unresolvable: 0, errors: 0 }; }) : { checked: 0, verified: 0, mismatched: 0, unresolvable: 0, errors: 0 };
        // v2 (stakes/0.1): a few registered sources' reach read from OpenAlex or Semantic Scholar and logged (five a run, a second apart).
        const staked = v2 ? await v2.stakes.run(5).catch((e) => { console.error("stakes scout failed", e); return { observed: 0, unresolved: 0, errors: 0, fields: 0, candidates: 0 }; }) : { observed: 0, unresolved: 0, errors: 0, fields: 0, candidates: 0 };
        if (r.cases || purged || sent.drawn || sent.reminders || rang.rung || rang.failed || swept.lapsed.length || swept.sealed.length) console.log("cron", JSON.stringify({ ...r, purged, alerts: sent, doorbells: rang, v2: swept }));
        await store.putOpsState("cron:last", {
          ok: true, ...r, purged, alertsDrawn: sent.drawn, alertsReminders: sent.reminders,
          doorbellsRung: rang.rung, doorbellsFailed: rang.failed, doorbellsPaused: rang.paused, doorbellsWaiting: rang.waiting,
          ...("error" in rang ? { doorbellsError: rang.error } : {}),
          v2Lapsed: swept.lapsed.length, v2Sealed: swept.sealed.length, v2AlertsSent: alerted.sent, v2DigestsSent: digested.sent,
          v2QuotesChecked: quoted.checked, v2QuotesVerified: quoted.verified, v2QuotesMismatched: quoted.mismatched,
          v2SourcesObserved: staked.observed, v2SourcesUnresolved: staked.unresolved, v2SourcesErrors: staked.errors, v2FieldsObserved: staked.fields, v2CandidatesRead: staked.candidates,
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
    // A log key that does not match its pin freezes every write, as the kill switch would: nothing the pinned key cannot verify is ever signed.
    const keysAgree = await logKeysAgree(env);
    if (!keysAgree) console.error("log key mismatch: STH_SIGNING_KEY_PKCS8 is not the other half of STH_PUBLIC_KEY; writes are refused");
    const frozen = readOnly(env) || !keysAgree;
    const v2 = v2From(env, store, (p) => ctx.waitUntil(p), frozen, keysAgree);
    const consoleDeps: ConsoleDeps = {
      svc, store, herald, newsletter, access,
      readOnly: consoleReadOnly(env, frozen),
      switches: switchesFrom(env, access, keysAgree),
      heraldFrom: env.HERALD_FROM || "Ecdysis <herald@notify.ecdysis.me>",
      digestFrom: env.DIGEST_FROM || "Ecdysis digest <digest@notify.ecdysis.me>",
      replyTo: env.HERALD_REPLY_TO || "replies@ecdysis.me",
    };
    return route(req, svc, limiterFrom(env), {
      sthPublicKey: realKey(env.STH_PUBLIC_KEY),
      readOnly: frozen,
      herald,
      newsletter,
      alerts,
      doorbells: doorbellsFrom(env, store, v2?.v2 ?? null),
      openaiAppsChallenge: env.OPENAI_APPS_CHALLENGE ?? null,
      console: consoleDeps,
      waitUntil: (p) => ctx.waitUntil(p),
      v2: v2?.v2 ?? null,
      me: v2?.me ?? null,
      steward: v2?.steward ?? null,
      complaints: v2?.complaints ?? null,
      issues: v2?.issues ?? null,
      pages: v2?.pages ?? null,
      governance: v2?.governance ?? null,
      oauth: v2?.oauth ?? null,
      archive: env.V1_ARCHIVE_URL ?? null,
    });
  },
} satisfies ExportedHandler<Env>;
