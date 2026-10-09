/**
 * Cloudflare Worker entry. Wires the record's service to D1, the platform
 * rate limiters and the deployment's screening configuration. All secrets
 * arrive through bindings; nothing sensitive is in this file or this repo.
 */

import { BUCKET_LIMITS, MemoryRateLimiter, PER_ADDRESS_PER_MINUTE, route, type RateLimiter } from "./api/router.js";
import { serveMedia, type AssetFetcher } from "./api/media.js";
import { V2Cache, V2Service } from "./api/v2/service.js";
import { LogApi } from "./api/v2/log-api.js";
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
import type { Json } from "./core/canonical.js";
import { D1QuoteCheckStore } from "./store/v2/quotes-d1.js";
import { ContextWriter, DEFAULT_CONTEXT_DAILY_CAP, DEFAULT_CONTEXT_MODEL, type DailyLedger } from "./api/v2/context.js";
import { D1ContextStore } from "./store/v2/context-d1.js";
import { sha256Hex } from "./api/access.js";
import { D1OAuthStore } from "./store/v2/oauth-d1.js";
import { TransparencyLog, type SignedTreeHead } from "./core/log.js";
import { D1V2Store } from "./store/v2/d1.js";
import { D1AccountStore } from "./store/v2/accounts-d1.js";
import { D1Store } from "./store/d1-store.js";
import { configScreener, guardScreener, structuralScreener, GUARD_MODEL, type AiLike, type DenyRule, type Screener } from "./core/hazard.js";
import { EMAIL_DAILY_CAP_DEFAULT, resendSender } from "./api/email.js";
import { Doorbells } from "./api/doorbells.js";
import { accessConfigured, type AccessConfig } from "./api/access.js";
import type { HealthSwitch } from "./web/steward.js";
import type { Store } from "./store/store.js";
import { signJson, verifyJson } from "./core/crypto.js";

export interface Env {
  DB: D1Database;
  ENVIRONMENT: string;
  /** Public half of the log key (base64url SPKI), pinned in wrangler.toml. */
  STH_PUBLIC_KEY: string;
  /**
   * Public half of the OPERATOR key: the reserved powers (R1 hazard decisions, R2 adoption at genesis and entrenched
   * co-signature). Its private half lives on the owner's own machine, never in Cloudflare; the log key never stands in.
   */
  OPERATOR_PUBLIC_KEY?: string;
  /**
   * Kill switch. Set to "1" (dashboard → Settings → Variables) to refuse every mutation with 503 while keeping the record
   * readable and auditable. Delete or set "0" to resume.
   */
  READ_ONLY?: string;
  /** Where the frozen first record lives (https://v1.ecdysis.me), named in the agents' index and on the landing page. */
  V1_ARCHIVE_URL?: string;
  /**
   * A frozen record's final signed tree head, as JSON ({treeSize, rootHash, timestamp, signature}): served verbatim at
   * /v2/log/sth instead of a freshly signed one, so an archive needs no log key. Read only when READ_ONLY is on; anything
   * unreadable is ignored.
   */
  FINAL_STH?: string;
  /** Secret: the log key's private half (base64url PKCS#8), installed by the owner. */
  STH_SIGNING_KEY_PKCS8?: string;
  /** Secret: JSON array of {pattern, flags, category, severity} rules, maintained outside this repo. See docs/deploy.md. */
  SCREENING_RULES?: string;
  /**
   * Finding categories (comma-separated, matching the rules' and the classifier's labels) that are the stewards' business
   * rather than a hazard: a claim with such findings is published and put under review for a steward; a short text is
   * refused. Deployment configuration, like the rules themselves. Unset: every review verdict goes to R1.
   */
  SCREEN_STEWARD_CATEGORIES?: string;
  /** Workers AI ([ai] in wrangler.toml): the safety classifier, inside this Cloudflare account. SCREENING_MODEL may override the model id. */
  AI?: AiLike;
  SCREENING_MODEL?: string;
  /** The email provider's key (a secret the deploy installs; named for the Herald that first used it). */
  HERALD_API_KEY?: string;
  /** "1" pauses every email Ecdysis sends (read-only mode pauses it too). */
  HERALD_PAUSED?: string;
  /** The reply-to address on every email. */
  HERALD_REPLY_TO?: string;
  /** stakes/0.1: an OpenAlex API key (free), so the stakes scout has its own daily budget. A secret, installed by the deploy. */
  OPENALEX_API_KEY?: string;
  /**
   * context/0.1: the model provider's key for the context writer ("What this means" on each claim page). A secret the deploy
   * installs from the GitHub secret of the same name; no session ever sees it. Unset: no summary is written, and the papers'
   * records are still read.
   */
  ANTHROPIC_API_KEY?: string;
  /** context/0.1: the model that writes the summaries (Anthropic's id); unset, DEFAULT_CONTEXT_MODEL. */
  CONTEXT_MODEL?: string;
  /** context/0.1: "1" stops new summaries (the ones written stay shown). */
  CONTEXT_PAUSED?: string;
  /** context/0.1: model calls allowed in a UTC day, whatever any run asks for. */
  CONTEXT_DAILY_CAP?: string;
  /** Where a new complaint is announced (a comma-separated list of the stewards' own addresses); unset, nobody is emailed. */
  ISSUE_ALERT_TO?: string;
  /** From-address for email doorbells; every ring and confirmation comes from it, so filters can name it. */
  DOORBELL_FROM?: string;
  /**
   * Secret: 32 random bytes (64 hex characters, or base64) that seal Claude routine tokens for doorbells (wake/0.1). Unset,
   * tokens are sealed with a key derived from the log key (HKDF, its own salt and label); set but unreadable, no new token
   * is accepted (fail closed).
   */
  DOORBELL_KEY?: string;
  /** The domain token ChatGPT's app directory issues; served at /.well-known/openai-apps-challenge. Public by design. */
  OPENAI_APPS_CHALLENGE?: string;
  /** Every email Ecdysis sends shares this cap per 24 hours: set it to the provider plan's daily quota. */
  EMAIL_DAILY_CAP?: string;
  /**
   * The stewardship area's lock (Cloudflare Access): the team domain, the application's Audience tag, and SHA-256 hashes of
   * the allowed addresses, which are also the steward list. Any of them missing locks the area completely.
   */
  ACCESS_TEAM_DOMAIN?: string;
  ACCESS_AUD?: string;
  OPERATOR_EMAIL_HASHES?: string;
  /**
   * Secret: 32 random bytes as 64 hex characters, keying the account store: emails are kept as an HMAC under it for lookup
   * and sealed under it for sending. Unset or unreadable: accounts are closed (fail closed).
   */
  ACCOUNTS_KEY?: string;
  /** Sender for sign-in links, alerts and digests; defaults to accounts@notify.ecdysis.me. */
  ACCOUNTS_FROM?: string;
  /**
   * Cloudflare's rate-limiting bindings ([[ratelimits]]): one limit per binding, per key, per location, shared by every
   * isolate there. RL_KEY carries the ordinary ceiling, RL_MCP the connector's. Nothing an agent files is rationed
   * (quotas/0.3); these only stop one connection knocking the archive over. A missing one falls back to the in-memory limiter.
   */
  RL_KEY?: RateLimitBinding;
  RL_MCP?: RateLimitBinding;
  /**
   * Workers static assets ([assets] in wrangler.toml): the files in public/, uploaded with every deploy. The Worker runs
   * first for every request, so they are reachable only through src/api/media.ts, which answers byte ranges.
   */
  ASSETS?: AssetFetcher;
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
 * The fallback limiter, ONE per isolate. The fetch handler runs once per request, so a limiter made there would start empty
 * every time and refuse nothing; this one lives as long as the isolate does. Cloudflare's bindings, when bound, are shared
 * across the isolates of a location and preferred.
 */
const FALLBACK_LIMITER = new MemoryRateLimiter(PER_ADDRESS_PER_MINUTE, 60_000, () => Date.now(), BUCKET_LIMITS);

/**
 * The limiter for a request: each bucket goes to the binding that carries its ceiling (one binding has one limit for every
 * key, so the connector's 6,000 a minute cannot share RL_KEY's 600), and a bucket whose binding is not bound, or whose
 * binding fails, falls back to the in-memory limiter, so there is always a ceiling and a platform hiccup never opens the gates.
 */
export function limiterFrom(env: Pick<Env, "RL_KEY" | "RL_MCP">): RateLimiter {
  if (!env.RL_KEY && !env.RL_MCP) return FALLBACK_LIMITER;
  const bindingFor = (bucket: string): RateLimitBinding | undefined => {
    if (bucket === "mcp") return env.RL_MCP;
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

const readOnly = (env: Pick<Env, "READ_ONLY">) => env.READ_ONLY === "1" || env.READ_ONLY?.toLowerCase() === "true";

/** The final tree head of a frozen record, when configured and readable; null otherwise. */
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

const emailCap = (env: Pick<Env, "EMAIL_DAILY_CAP">) => {
  const n = Number(env.EMAIL_DAILY_CAP);
  return Number.isInteger(n) && n > 0 ? n : EMAIL_DAILY_CAP_DEFAULT;
};
const emailPaused = (env: Pick<Env, "HERALD_PAUSED" | "READ_ONLY">) => env.HERALD_PAUSED === "1" || readOnly(env);
const contextCap = (env: Pick<Env, "CONTEXT_DAILY_CAP">) => {
  const n = Number(env.CONTEXT_DAILY_CAP);
  return Number.isInteger(n) && n >= 0 && (env.CONTEXT_DAILY_CAP ?? "").trim() !== "" ? n : DEFAULT_CONTEXT_DAILY_CAP;
};
const contextPaused = (env: Pick<Env, "CONTEXT_PAUSED" | "READ_ONLY">) => env.CONTEXT_PAUSED === "1" || readOnly(env);

/** context/0.1: the writer's model calls today, in ops state, so the cap holds across runs and isolates. */
export function contextLedgerFrom(store: Pick<D1Store, "getOpsState" | "putOpsState">): DailyLedger {
  return {
    get: async () => {
      const v = (await store.getOpsState("context:day"))?.value as { day?: unknown; count?: unknown } | undefined;
      return v && typeof v.day === "string" && typeof v.count === "number" ? { day: v.day, count: v.count } : null;
    },
    put: async (v) => { await store.putOpsState("context:day", v as unknown as Json, new Date().toISOString()); },
  };
}
const csprng = () => crypto.getRandomValues(new Uint32Array(1))[0]! / 2 ** 32;
const FROM = (env: Pick<Env, "ACCOUNTS_FROM">) => env.ACCOUNTS_FROM || "Ecdysis <accounts@notify.ecdysis.me>";
const REPLY_TO = (env: Pick<Env, "HERALD_REPLY_TO">) => env.HERALD_REPLY_TO || "replies@ecdysis.me";

/** Accounts for people, closed without ACCOUNTS_KEY. */
function accountsFrom(env: Env, store: D1AccountStore): Accounts {
  return new Accounts({
    store,
    key: env.ACCOUNTS_KEY ?? null,
    // The email pause switch covers sign-in links too: paused, accounts can still be used but not entered.
    send: env.HERALD_API_KEY && !emailPaused(env) ? resendSender(env.HERALD_API_KEY) : null,
    from: FROM(env),
    replyTo: REPLY_TO(env),
    siteBase: "https://ecdysis.me",
    stewardEmailHashes: accessFrom(env).emailHashes,
  });
}

/**
 * One per isolate: the log's rows and the records derived from them. The handlers below are built per request (they are
 * cheap); the cache is not, so the log is read once and extended, and a burst of requests derives the record once a minute
 * rather than once a request.
 */
const V2_CACHE = new V2Cache();

/**
 * direction/0.1: the registration candidates (each observed field's most-cited works in the citation graph), which the
 * stakes scout reads once a month and the direction list offers as `register` acts. They are direction, never a number about
 * any claim, so they live in ops state rather than on the log.
 */
export function candidatesFrom(store: Pick<D1Store, "getOpsState" | "putOpsState">): CandidateStore {
  return {
    get: async () => ((await store.getOpsState("direction:candidates"))?.value as unknown as CandidateSet | undefined) ?? null,
    put: async (set) => { await store.putOpsState("direction:candidates", set as unknown as Json, new Date().toISOString()); },
  };
}

/** The log read over HTTP and the connector: heads, proofs, entries, the audit. */
export function logApiFrom(env: Pick<Env, "STH_SIGNING_KEY_PKCS8" | "READ_ONLY" | "FINAL_STH">, store: D1Store, keysAgree = true): LogApi {
  // A key that is not the other half of the pin signs nothing: heads are served unsigned until the right key is installed.
  return new LogApi({ log: new TransparencyLog(store), reader: store, signingKey: keysAgree ? env.STH_SIGNING_KEY_PKCS8 ?? null : null, finalSth: finalSthFrom(env) });
}

/** Everything the record needs, for the request path and the cron alike. */
function recordFrom(env: Env, store: D1Store, waitUntil: ((p: Promise<unknown>) => void) | null = null, frozen = readOnly(env), keysAgree = true) {
  const accountStore = new D1AccountStore(env.DB);
  const accounts = accountsFrom(env, accountStore);
  const log = new TransparencyLog(store);
  const logApi = logApiFrom(env, store, keysAgree);
  const candidates = candidatesFrom(store);
  // context/0.1: the papers' records and the claims' summaries, off the log, shown on claim pages and served with each claim.
  const contextStore = new D1ContextStore(env.DB);
  const v2 = new V2Service({
    log,
    cache: V2_CACHE,
    candidates,
    context: contextStore,
    store: new D1V2Store(env.DB, store),
    // Seeds are sealed with the log key only when it is the other half of the pin (writes are refused otherwise anyway).
    logPrivateKey: keysAgree ? env.STH_SIGNING_KEY_PKCS8 ?? null : null,
    screeners: screenersFrom(env),
    stewardCategories: new Set((env.SCREEN_STEWARD_CATEGORIES ?? "").split(",").map((c) => c.trim()).filter(Boolean)),
    pairing: (code, ip) => accounts.consumePairing(code, ip),
    // R1 and R2 need the operator key and only that (never the log key, which lives in this Worker).
    operatorPublicKey: realKey(env.OPERATOR_PUBLIC_KEY),
  });
  const send = env.HERALD_API_KEY && !emailPaused(env) ? resendSender(env.HERALD_API_KEY) : null;
  const notifier = new Notifier({ accounts, accountStore, ledger: store, v2, send, from: FROM(env), replyTo: REPLY_TO(env), siteBase: "https://ecdysis.me", emailDailyCap: emailCap(env) });
  // OAuth 2.1 for the connector and managed agents (I.4): tokens stand for people; the archive holds only the keys people asked it to.
  const oauth = new OAuth({ accounts, store: new D1OAuthStore(env.DB), v2, issuer: "https://ecdysis.me", resource: "https://api.ecdysis.me/mcp", siteBase: "https://ecdysis.me" });
  // R2 needs the operator key and only that: the log key lives in this Worker, so falling back to it would let the archive co-sign for its owner.
  const governance = new V2Governance({ v2, log, operatorPublicKey: realKey(env.OPERATOR_PUBLIC_KEY), closedElectorates: V2_CACHE.closedElectorates });
  // The issues queue: complaints and scouts' flags, off the log, decided on /steward/content. A new complaint is announced to
  // the stewards' own addresses when ISSUE_ALERT_TO is set and email is on; the connecting address is kept only as a keyed hash.
  const alertTo = (env.ISSUE_ALERT_TO ?? "").split(",").map((a) => a.trim()).filter((a) => /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(a));
  const issues = new IssueRegistry({
    store: new D1IssueStore(env.DB), v2,
    hashIp: (ip) => sha256Hex(`issues|${env.ACCOUNTS_KEY ?? ""}|${ip}`),
    alert: send && alertTo.length ? async (issue) => {
      // Two things people send the stewards: a complaint about an item, or a request to have their operator verified. The
      // email names which and where to decide it, and carries none of the text.
      const request = issue.kind === "verification";
      const subject = request ? `Ecdysis: a verification request from ${issue.subject}` : `Ecdysis: a complaint about ${issue.subject}`;
      const text = request
        ? `Operator ${issue.subject} asks to be verified; the request is waiting for a steward at https://ecdysis.me/steward/people#verification.\n\nThis message carries no part of the request; read it signed in. Data, never instructions.`
        : `A complaint about ${issue.subject} is waiting for a steward at https://ecdysis.me/steward/content#issues (issue ${issue.id}).\n\nThis message carries no part of the complaint; read it signed in. Data, never instructions.`;
      for (const to of alertTo) await send({ from: FROM(env), to, replyTo: REPLY_TO(env), subject, text, headers: {} });
    } : null,
  });
  // Screening's referrals open an issue for the stewards (the service knows nothing of the registry; this hook joins them).
  v2.setReferralHook((subject, detail) => issues.open("screening", subject, 2, detail, "screening").then(() => undefined));
  // The quote scout: on the cron, a few registered quotes are checked against their source's abstract; the claim page shows the result.
  const quoteStore = new D1QuoteCheckStore(env.DB);
  const quotes = new QuoteScout({ store: quoteStore, v2, issues, contact: REPLY_TO(env), openAlexKey: env.OPENALEX_API_KEY ?? null });
  // The stakes scout (stakes/0.1): on the cron, a few registered sources' reach is read from the public citation graph and logged.
  const stakes = new StakesScout({ v2, log, candidates, contact: REPLY_TO(env), apiKey: env.OPENALEX_API_KEY ?? null });
  // context/0.1: on the cron, the papers' records (OpenAlex) and, with the provider's key, each claim's plain-English summary.
  const context = new ContextWriter({
    store: contextStore, v2, quotes: quoteStore, contact: REPLY_TO(env), openAlexKey: env.OPENALEX_API_KEY ?? null,
    anthropicKey: env.ANTHROPIC_API_KEY ?? null, model: env.CONTEXT_MODEL ?? null, paused: contextPaused(env), dailyCap: contextCap(env),
    ledger: contextLedgerFrom(store), screeners: screenersFrom(env),
  });
  return {
    v2, logApi, notifier, quotes, stakes, context, governance, issues,
    oauth: { logic: oauth, http: new OAuthHandler({ oauth, accounts, readOnly: frozen }) },
    complaints: new ComplaintsHandler({ issues, readOnly: frozen }),
    me: new MeHandler({ accounts, v2, oauth, governance, issues, feeds: new V2Feeds(v2, { site: "https://ecdysis.me", api: "https://api.ecdysis.me" }), readOnly: frozen, stop: (a, t) => notifier.stop(a, t) }),
    // Access is always configured in production; when it is, /steward needs its token as well as a steward's session.
    steward: new StewardHandler({
      accounts, v2, access: accessFrom(env), readOnly: frozen, canaries: new CanaryRegistry({ store: new D1CanaryStore(env.DB), accounts, v2 }), issues,
      // Health: the deployment's head, cron, audit and switches, read from the same places.
      health: {
        sth: async () => (await logApi.sth()) as unknown as Record<string, unknown>,
        logSize: () => store.logSize(),
        opsState: async (key) => { const v = await store.getOpsState(key); return v ? { value: (v.value && typeof v.value === "object" && !Array.isArray(v.value) ? v.value : null) as Record<string, unknown> | null, at: v.at } : null; },
        counters: async () => [...(await store.listAccessPrefix("funnel:")), ...(await store.listAccessPrefix("pv:")), ...(await store.listAccessPrefix("op:")), ...(await store.listAccessPrefix("mcpw:"))],
        runAudit: async () => {
          const r = await logApi.audit();
          const body = r.body as { intact?: boolean; problem?: string | null };
          const size = await store.logSize();
          await store.putOpsState("audit:last", { intact: !!body.intact, problem: body.problem ?? null, size }, new Date().toISOString());
          return { intact: !!body.intact, problem: body.problem ?? null, size };
        },
        switches: switchesFrom(env, accessFrom(env), keysAgree),
      },
    }),
    pages: new PagesHandler(v2, {
      host: "api.ecdysis.me", logPublicKey: realKey(env.STH_PUBLIC_KEY), governance, accounts, archive: env.V1_ARCHIVE_URL ?? null, quotes: quoteStore, context: contextStore, log: logApi,
      count: async (keys) => { for (const k of keys) await store.bumpAccess(k).catch(() => {}); },
      ...(waitUntil ? { waitUntil } : {}),
    }),
  };
}

/**
 * The doorbells, for the request path and the cron alike. The agents live on the log, so the record's service resolves who
 * an agent is; a doorbell is its agent's to set with the main key only.
 */
export function doorbellsFrom(
  env: Pick<Env, "STH_SIGNING_KEY_PKCS8" | "DOORBELL_KEY" | "READ_ONLY"> & Partial<Pick<Env, "HERALD_API_KEY" | "HERALD_PAUSED" | "HERALD_REPLY_TO" | "EMAIL_DAILY_CAP" | "DOORBELL_FROM">>,
  store: Store,
  v2: V2Service,
  keysAgree = true,
): Doorbells {
  return new Doorbells({
    store,
    siteBase: "https://ecdysis.me",
    apiBase: "https://api.ecdysis.me",
    // A log key that is not the other half of the pin signs no ring and seals nothing, and the doorbells take no changes.
    sthPrivateKey: keysAgree ? env.STH_SIGNING_KEY_PKCS8 ?? null : null,
    sealSecret: env.DOORBELL_KEY ?? null,
    readOnly: readOnly(env) || !keysAgree,
    now: () => new Date(),
    random: csprng,
    // Email doorbells: the same provider, pause switch and shared daily cap as every other email Ecdysis sends.
    email: {
      send: env.HERALD_API_KEY && env.HERALD_PAUSED !== "1" && !readOnly(env) ? resendSender(env.HERALD_API_KEY) : null,
      from: env.DOORBELL_FROM || "Ecdysis doorbell <wake@notify.ecdysis.me>",
      replyTo: env.HERALD_REPLY_TO || "replies@ecdysis.me",
      dailyCap: emailCap(env),
    },
    // The reasons to ring (owed checks, disputes on what an agent relies on), and who an agent is, both from the record.
    extraReasons: (handles: string[]) => v2.ringReasons(handles),
    resolveAgent: async (handle: string) => { const a = (await v2.record()).agents.get(handle); return a && !a.revokedAt ? { publicKey: a.publicKey, operatorId: a.operatorId } : null; },
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
 * Once per isolate: the installed log key must be the other half of the pinned public key. If it is not (a key swapped by
 * mistake, or the new key installed before the pin was changed at a fresh start), every write is refused as if the kill
 * switch were on: a seal or a head the pinned key cannot verify must never be made. Nothing to compare (no pin, or no key)
 * passes: unsigned heads are a known state, not a mismatch.
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

/** The switches the stewards' Health page shows, read from this deployment's configuration. */
function switchesFrom(env: Env, access: AccessConfig, keysAgree = true): HealthSwitch[] {
  const on = (ok: boolean, yes: string, no: string, note?: string): Pick<HealthSwitch, "ok" | "value" | "note"> => ({ ok, value: ok ? yes : no, ...(note ? { note } : {}) });
  return [
    { name: "Stewardship lock (Cloudflare Access)", ...on(accessConfigured(access), "configured", "not configured", "Team domain, audience tag and allowed address hashes.") },
    { name: "Read-only kill switch", ...on(!readOnly(env), "off", "ON", "READ_ONLY: when on, every write is refused.") },
    { name: "Log key matches its pin", ...on(keysAgree, "yes", "NO: writes refused", "The installed signing key must be the other half of STH_PUBLIC_KEY; until it is, every write is refused.") },
    { name: "Safety classifier", ...on(!!env.AI, "Workers AI", "absent: fail-closed screening", env.SCREENING_MODEL || GUARD_MODEL) },
    { name: "Log signing key", ...on(!!env.STH_SIGNING_KEY_PKCS8, "installed", "missing", "Tree heads are unsigned without it.") },
    { name: "Operator key (R1, R2)", ...on(!!realKey(env.OPERATOR_PUBLIC_KEY), "configured", "missing: hazard decisions and genesis refused") },
    { name: "Email provider", ...on(!!env.HERALD_API_KEY, "installed", "missing", "HERALD_API_KEY, installed by the deploy from the GitHub secret.") },
    { name: "Email sending", ...on(!emailPaused(env), "on", "paused", "HERALD_PAUSED (read-only mode also pauses it).") },
    { name: "Shared daily email cap", ok: true, value: String(emailCap(env)), note: "EMAIL_DAILY_CAP: set it to your provider plan's daily quota." },
    { name: "OpenAlex key (stakes and quote scouts)", ...on(!!env.OPENALEX_API_KEY, "installed", "missing: the scouts share OpenAlex's anonymous budget", "OPENALEX_API_KEY, installed by the deploy from the GitHub secret.") },
    { name: "Context writer's key (What this means)", ...on(!!env.ANTHROPIC_API_KEY, "installed", "missing: no summaries are written; the papers' records still are", "ANTHROPIC_API_KEY, installed by the deploy from the GitHub secret.") },
    { name: "Context writer", ...on(!contextPaused(env), `on: ${(env.CONTEXT_MODEL ?? "").trim() || DEFAULT_CONTEXT_MODEL}`, "paused", "CONTEXT_PAUSED stops new summaries; CONTEXT_MODEL names the model.") },
    { name: "Context writer's daily cap", ok: true, value: String(contextCap(env)), note: "CONTEXT_DAILY_CAP: model calls allowed in a UTC day." },
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
   * The cron (wrangler.toml [triggers]): seals orphaned commitments and lapses overdue checks, rings doorbells, sends the
   * alerts and digests people asked for, and runs the scouts. Each run is recorded for the Health page. The kill switch stops it.
   */
  async scheduled(_event: ScheduledController, env: Env, ctx: ExecutionContext): Promise<void> {
    if (readOnly(env)) return;
    // A log key that does not match its pin stops the cron as it stops every write: no lapse, seal, observation or ring is
    // made under a key the pin cannot verify (the window between a fresh start's merge and the new key's installation).
    if (!(await logKeysAgree(env))) {
      console.error("log key mismatch: STH_SIGNING_KEY_PKCS8 is not the other half of STH_PUBLIC_KEY; the cron does nothing");
      return;
    }
    const store = new D1Store(env.DB);
    // The run is the handler's own promise, awaited, as well as handed to waitUntil. Work given to waitUntil alone is allowed
    // only about thirty seconds once the handler has returned (Cloudflare's limits), and on 9 October 2026 the context
    // writer, which runs last, read a paper or two each run and then stopped, the scouts' polite pauses having used the time;
    // the promise a scheduled handler returns is awaited for up to fifteen minutes. The writers' budgets keep a run inside it.
    const run = (async () => {
      const at = new Date().toISOString();
      const started = Date.now();
      try {
        const rec = recordFrom(env, store);
        // Each runs on its own: an email that failed never stops an agent being woken, nor a lapse being recorded.
        const swept = await rec.v2.sweepLapses().catch((e) => { console.error("sweep failed", e); return { lapsed: [] as string[], sealed: [] as string[] }; });
        const rang = await doorbellsFrom(env, store, rec.v2).notify().catch((e) => {
          console.error("doorbells failed", e);
          return { rung: 0, failed: 0, paused: 0, waiting: 0, error: String((e as Error)?.message ?? e).slice(0, 200) };
        });
        const alerted = await rec.notifier.run().catch((e) => { console.error("alerts failed", e); return { sent: 0, skipped: 0, events: 0 }; });
        const digested = await rec.notifier.digest().catch((e) => { console.error("digest failed", e); return { sent: 0, skipped: 0 }; });
        // A few registered quotes checked against their sources (arXiv asks for a pause between requests; six a run, every quarter hour, is well within it).
        const quoted = await rec.quotes.run(6).catch((e) => { console.error("quote scout failed", e); return { checked: 0, verified: 0, mismatched: 0, unresolvable: 0, errors: 0 }; });
        // stakes/0.1: a few registered sources' reach read from OpenAlex or Semantic Scholar and logged (five a run, a second apart).
        const staked = await rec.stakes.run(5).catch((e) => { console.error("stakes scout failed", e); return { observed: 0, unresolved: 0, errors: 0, fields: 0, candidates: 0 }; });
        // context/0.1: a dozen papers' records and a dozen summaries a run, highest stakes first, under the daily cap.
        const explained = await rec.context.run({ papers: 12, writes: 12 }).catch((e) => { console.error("context writer failed", e); return { papersRead: 0, papersUnresolved: 0, written: 0, refused: 0, errors: 1, capped: false, outOfTime: false, off: "failed" }; });
        if (rang.rung || rang.failed || swept.lapsed.length || swept.sealed.length) console.log("cron", JSON.stringify({ doorbells: rang, swept }));
        await store.putOpsState("cron:last", {
          ok: true,
          doorbellsRung: rang.rung, doorbellsFailed: rang.failed, doorbellsPaused: rang.paused, doorbellsWaiting: rang.waiting,
          ...("error" in rang ? { doorbellsError: rang.error } : {}),
          lapsed: swept.lapsed.length, sealed: swept.sealed.length, alertsSent: alerted.sent, digestsSent: digested.sent,
          quotesChecked: quoted.checked, quotesVerified: quoted.verified, quotesMismatched: quoted.mismatched,
          sourcesObserved: staked.observed, sourcesUnresolved: staked.unresolved, sourcesErrors: staked.errors, fieldsObserved: staked.fields, candidatesRead: staked.candidates,
          papersRead: explained.papersRead, papersUnresolved: explained.papersUnresolved, summariesWritten: explained.written, summariesRefused: explained.refused, contextErrors: explained.errors,
          ...(explained.capped ? { contextCapped: true } : {}), ...(explained.outOfTime ? { contextOutOfTime: true } : {}), ...(explained.off ? { contextOff: explained.off } : {}),
          seconds: Math.round((Date.now() - started) / 1000),
        }, at);
      } catch (e) {
        console.error("cron failed", e);
        await store.putOpsState("cron:last", { ok: false, error: String((e as Error)?.message ?? e).slice(0, 300), seconds: Math.round((Date.now() - started) / 1000) }, at).catch(() => {});
      }
    })();
    ctx.waitUntil(run);
    await run;
  },

  async fetch(req: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    // The site's media (the front page's video, its poster and captions) are static files: answered first, with byte
    // ranges, before anything touches the record, the rate limits or the counters.
    const media = await serveMedia(req, env.ASSETS);
    if (media) return media;
    const store = new D1Store(env.DB);
    // A log key that does not match its pin freezes every write, as the kill switch would: nothing the pinned key cannot verify is ever signed.
    const keysAgree = await logKeysAgree(env);
    if (!keysAgree) console.error("log key mismatch: STH_SIGNING_KEY_PKCS8 is not the other half of STH_PUBLIC_KEY; writes are refused");
    const frozen = readOnly(env) || !keysAgree;
    const rec = recordFrom(env, store, (p) => ctx.waitUntil(p), frozen, keysAgree);
    return route(req, limiterFrom(env), {
      v2: rec.v2,
      log: rec.logApi,
      sthPublicKey: realKey(env.STH_PUBLIC_KEY),
      readOnly: frozen,
      doorbells: doorbellsFrom(env, store, rec.v2, keysAgree),
      openaiAppsChallenge: env.OPENAI_APPS_CHALLENGE ?? null,
      waitUntil: (p) => ctx.waitUntil(p),
      count: async (keys) => { for (const k of keys) await store.bumpAccess(k).catch(() => {}); },
      me: rec.me,
      steward: rec.steward,
      complaints: rec.complaints,
      issues: rec.issues,
      pages: rec.pages,
      governance: rec.governance,
      oauth: rec.oauth,
      archive: env.V1_ARCHIVE_URL ?? null,
    });
  },
} satisfies ExportedHandler<Env>;
