/**
 * The operator console's lock. Two layers, and both must agree:
 *
 *  1. Cloudflare Access sits in front of ecdysis.me/operator. Nobody reaches
 *     the Worker on that path without signing in with a one-time code sent
 *     to the operator's own address.
 *  2. This module checks, on every request, the token Access attaches
 *     (Cf-Access-Jwt-Assertion): RS256 against the team's published keys,
 *     the right audience, issuer and token type, inside its validity window,
 *     for an allowed address. So a policy mistake in the dashboard, a request
 *     on another hostname, or a forged header all still fail.
 *
 * Fails closed: with no team domain, no audience or no allowed address
 * configured, nothing gets in. Allowed addresses are configured as SHA-256
 * hashes, so the public repository never holds them.
 */

export interface AccessConfig {
  /** e.g. "withered-base-4068.cloudflareaccess.com" */
  teamDomain: string | null;
  /** The Access application's Audience (AUD) tag. */
  aud: string | null;
  /** Hex SHA-256 of each allowed address, lowercased before hashing. */
  emailHashes: string[];
  /** The only hostname the console answers on. */
  host: string;
}

export type AccessRefusal =
  | "not-configured" | "wrong-host" | "no-token" | "malformed" | "bad-algorithm" | "unknown-key"
  | "certs-unavailable" | "bad-signature" | "wrong-audience" | "wrong-issuer" | "wrong-type"
  | "expired" | "not-yet-valid" | "no-email" | "not-allowed";

export type AccessVerdict =
  | { ok: true; email: string; token: string }
  | { ok: false; reason: AccessRefusal };

const TEAM_DOMAIN = /^[a-z0-9][a-z0-9-]{0,62}\.cloudflareaccess\.com$/;
const LEEWAY_S = 60;
const KEYS_TTL_MS = 10 * 60 * 1000;
const REFETCH_GAP_MS = 30 * 1000;

interface KeySet { fetchedAt: number; keys: Map<string, CryptoKey> }
const keyCache = new Map<string, KeySet>();

/** Tests only: forget cached signing keys. */
export function resetAccessKeys(): void {
  keyCache.clear();
}

function b64urlBytes(s: string): Uint8Array<ArrayBuffer> {
  const b64 = s.replace(/-/g, "+").replace(/_/g, "/") + "===".slice((s.length + 3) % 4);
  const bin = atob(b64);
  const out = new Uint8Array(new ArrayBuffer(bin.length));
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}

function b64urlJson(s: string): Record<string, unknown> | null {
  try {
    const v = JSON.parse(new TextDecoder().decode(b64urlBytes(s))) as unknown;
    return v && typeof v === "object" && !Array.isArray(v) ? (v as Record<string, unknown>) : null;
  } catch {
    return null;
  }
}

export async function sha256Hex(text: string): Promise<string> {
  const d = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return [...new Uint8Array(d)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

/** True when the console can possibly admit anyone. */
export function accessConfigured(cfg: AccessConfig): boolean {
  return !!cfg.teamDomain && TEAM_DOMAIN.test(cfg.teamDomain) && !!cfg.aud && /^[0-9a-f]{32,128}$/.test(cfg.aud) &&
    cfg.emailHashes.some((h) => /^[0-9a-f]{64}$/.test(h));
}

async function loadKeys(teamDomain: string, fetchImpl: typeof fetch, now: number, force: boolean): Promise<KeySet | null> {
  const cached = keyCache.get(teamDomain);
  if (cached && !force && now - cached.fetchedAt < KEYS_TTL_MS) return cached;
  if (cached && force && now - cached.fetchedAt < REFETCH_GAP_MS) return cached; // don't hammer on unknown kids
  try {
    const r = await fetchImpl(`https://${teamDomain}/cdn-cgi/access/certs`, { headers: { accept: "application/json" } });
    if (!r.ok) return cached ?? null;
    const body = (await r.json()) as { keys?: Array<Record<string, unknown>> };
    const keys = new Map<string, CryptoKey>();
    for (const jwk of body.keys ?? []) {
      if (jwk["kty"] !== "RSA" || typeof jwk["kid"] !== "string" || typeof jwk["n"] !== "string" || typeof jwk["e"] !== "string") continue;
      if (jwk["alg"] !== undefined && jwk["alg"] !== "RS256") continue;
      const key = await crypto.subtle.importKey(
        "jwk", { kty: "RSA", n: jwk["n"] as string, e: jwk["e"] as string, alg: "RS256", ext: true },
        { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" }, false, ["verify"],
      );
      keys.set(jwk["kid"] as string, key);
    }
    if (keys.size === 0) return cached ?? null;
    const set = { fetchedAt: now, keys };
    keyCache.set(teamDomain, set);
    return set;
  } catch {
    return cached ?? null;
  }
}

/**
 * Verify the Access token on a console request. Only the header Cloudflare
 * sets after Access admits a request counts; the browser cookie never does.
 */
export async function verifyAccess(
  req: Request, cfg: AccessConfig, fetchImpl: typeof fetch = fetch, nowMs: number = Date.now(),
): Promise<AccessVerdict> {
  if (!accessConfigured(cfg)) return { ok: false, reason: "not-configured" };
  if (new URL(req.url).hostname.toLowerCase() !== cfg.host) return { ok: false, reason: "wrong-host" };
  const token = req.headers.get("cf-access-jwt-assertion") ?? "";
  if (!token) return { ok: false, reason: "no-token" };
  const parts = token.split(".");
  if (parts.length !== 3 || parts.some((p) => !/^[A-Za-z0-9_-]+$/.test(p)) || token.length > 8192) {
    return { ok: false, reason: "malformed" };
  }
  const header = b64urlJson(parts[0]!);
  const claims = b64urlJson(parts[1]!);
  if (!header || !claims) return { ok: false, reason: "malformed" };
  if (header["alg"] !== "RS256") return { ok: false, reason: "bad-algorithm" };
  const kid = typeof header["kid"] === "string" ? (header["kid"] as string) : "";
  if (!kid) return { ok: false, reason: "unknown-key" };

  const team = cfg.teamDomain!;
  let set = await loadKeys(team, fetchImpl, nowMs, false);
  if (set && !set.keys.has(kid)) set = await loadKeys(team, fetchImpl, nowMs, true); // keys rotate
  if (!set) return { ok: false, reason: "certs-unavailable" };
  const key = set.keys.get(kid);
  if (!key) return { ok: false, reason: "unknown-key" };
  let good = false;
  try {
    good = await crypto.subtle.verify(
      "RSASSA-PKCS1-v1_5", key, b64urlBytes(parts[2]!), new TextEncoder().encode(`${parts[0]}.${parts[1]}`),
    );
  } catch {
    good = false;
  }
  if (!good) return { ok: false, reason: "bad-signature" };

  const aud = claims["aud"];
  const auds = Array.isArray(aud) ? aud : [aud];
  if (!auds.includes(cfg.aud)) return { ok: false, reason: "wrong-audience" };
  if (claims["iss"] !== `https://${team}`) return { ok: false, reason: "wrong-issuer" };
  // Access also signs "meta" tokens (they travel in login redirects); only an
  // application token proves a signed-in person.
  if (claims["type"] !== "app") return { ok: false, reason: "wrong-type" };
  const now = Math.floor(nowMs / 1000);
  const exp = Number(claims["exp"]);
  if (!Number.isFinite(exp) || now > exp + LEEWAY_S) return { ok: false, reason: "expired" };
  for (const k of ["nbf", "iat"]) {
    if (claims[k] !== undefined && !(Number(claims[k]) <= now + LEEWAY_S)) return { ok: false, reason: "not-yet-valid" };
  }
  const email = typeof claims["email"] === "string" ? (claims["email"] as string).trim().toLowerCase() : "";
  if (!email) return { ok: false, reason: "no-email" };
  if (!cfg.emailHashes.includes(await sha256Hex(email))) return { ok: false, reason: "not-allowed" };
  return { ok: true, email, token };
}

/**
 * The console's anti-forgery token: bound to this sign-in's Access token,
 * which only the signed-in browser holds (an HttpOnly cookie that Access
 * turns into the header). A forged cross-site form cannot know it.
 */
export async function csrfFor(token: string): Promise<string> {
  return (await sha256Hex(`ecdysis-operator-csrf|${token}`)).slice(0, 40);
}

/** Constant-time comparison of two short ASCII strings. */
export function sameString(a: string, b: string): boolean {
  if (a.length !== b.length) return false;
  let d = 0;
  for (let i = 0; i < a.length; i++) d |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return d === 0;
}
