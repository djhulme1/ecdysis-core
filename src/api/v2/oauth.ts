/**
 * OAuth 2.1 for the connector, and managed agents (design: claude/ecdysis-
 * v2-people-and-stewardship.md §5; constitution I.4).
 *
 * An AI app that cannot hold a key signs its person in instead. The flow is
 * the one the app directories expect: dynamic client registration
 * (RFC 7591), an authorization code with PKCE (S256, required), bearer
 * access tokens bound to the connector (RFC 8707 resource indicators),
 * rotating refresh tokens, and the two metadata documents (RFC 8414,
 * RFC 9728) that let a client find all of it from the connector's URL.
 *
 * A token stands for a PERSON (an account), never for an agent. What it
 * unlocks is that person's MANAGED agents: agents whose Ed25519 key the
 * archive generated and holds sealed (AES-GCM under a key derived from
 * ACCOUNTS_KEY, bound to the handle). A write sent without a signature by
 * a signed-in app, naming one of those agents, is signed here and then
 * treated exactly like any other envelope. Every such agent is registered
 * with `managed: true`, so the record says who held the pen, and the
 * person can destroy the key at any time, which retires the agent. A
 * claim's one correction (claim.amend) is never signed for a token: the
 * person asks for it on their own page, and the archive signs it there.
 *
 * What is never here: the person's password (there is none), a key that
 * anyone asked us not to hold, or a token that outlives its purpose. Codes
 * live ten minutes and are spent once; access tokens an hour; refresh
 * tokens thirty days and rotate on every use; everything is stored hashed.
 */

import { generateKeyPair, signJson } from "../../core/crypto.js";
import { sameString, sha256Hex } from "../access.js";
import { b64urlEncode, bufferSource, toHex, type Json } from "../../core/canonical.js";
import { CLAIM_REF_WORDS, isClaimRef } from "../../core/v2/refs.js";
import type { Accounts, Signed } from "./accounts.js";
import type { ApiResult, V2Service } from "./service.js";

export const CODE_TTL_MS = 10 * 60 * 1000;
export const ACCESS_TTL_MS = 60 * 60 * 1000;
export const REFRESH_TTL_MS = 30 * 24 * 3600 * 1000;
export const CLIENTS_PER_HOUR_PER_IP = 20;
export const SCOPE = "agent";

export interface ClientRow { id: string; name: string; redirectUris: string[]; createdAt: string }
export interface CodeRow { hash: string; grantId: string; clientId: string; accountId: string; redirectUri: string; codeChallenge: string; scope: string; resource: string; createdAt: string; expiresAt: string; usedAt: string | null }
export interface TokenRow { hash: string; grantId: string; kind: "access" | "refresh"; accountId: string; clientId: string; scope: string; resource: string; createdAt: string; expiresAt: string; revokedAt: string | null }
export interface ManagedKeyRow { handle: string; accountId: string; publicKey: string; privateSealed: string; createdAt: string; destroyedAt: string | null }

export interface OAuthStore {
  putClient(c: ClientRow): Promise<void>;
  getClient(id: string): Promise<ClientRow | null>;
  countClients(sinceIso: string, ipHash: string): Promise<number>;
  recordClient(ipHash: string, atIso: string): Promise<void>;
  putCode(c: CodeRow): Promise<void>;
  getCode(hash: string): Promise<CodeRow | null>;
  /** Spend the code: true if this call spent it (atomic in the store). */
  useCode(hash: string, usedAt: string): Promise<boolean>;
  putToken(t: TokenRow): Promise<void>;
  getToken(hash: string): Promise<TokenRow | null>;
  /** Revoke one token: true if it was live. */
  revokeToken(hash: string, atIso: string): Promise<boolean>;
  /** Revoke every token of one grant (one consent): what a stolen or replayed token takes down with it. */
  revokeGrant(grantId: string, atIso: string): Promise<void>;
  revokeTokensFor(accountId: string, atIso: string): Promise<void>;
  putManagedKey(k: ManagedKeyRow): Promise<void>;
  getManagedKey(handle: string): Promise<ManagedKeyRow | null>;
  listManagedKeys(accountId: string): Promise<ManagedKeyRow[]>;
  /** Destroy: the sealed key is erased (the row keeps the handle and the time, so the page can say so). */
  destroyManagedKey(handle: string, atIso: string): Promise<void>;
}

export class MemoryOAuthStore implements OAuthStore {
  clients = new Map<string, ClientRow>();
  codes = new Map<string, CodeRow>();
  tokens = new Map<string, TokenRow>();
  managed = new Map<string, ManagedKeyRow>();
  registrations: Array<{ ip: string; at: string }> = [];
  async putClient(c: ClientRow) { this.clients.set(c.id, structuredClone(c)); }
  async getClient(id: string) { return this.clients.get(id) ?? null; }
  async countClients(since: string, ip: string) { return this.registrations.filter((r) => r.ip === ip && r.at >= since).length; }
  async recordClient(ip: string, at: string) { this.registrations.push({ ip, at }); }
  async putCode(c: CodeRow) { this.codes.set(c.hash, { ...c }); }
  async getCode(hash: string) { return this.codes.get(hash) ?? null; }
  async useCode(hash: string, usedAt: string) { const c = this.codes.get(hash); if (!c || c.usedAt) return false; c.usedAt = usedAt; return true; }
  async putToken(t: TokenRow) { this.tokens.set(t.hash, { ...t }); }
  async getToken(hash: string) { return this.tokens.get(hash) ?? null; }
  async revokeToken(hash: string, at: string) { const t = this.tokens.get(hash); if (!t || t.revokedAt) return false; t.revokedAt = at; return true; }
  async revokeGrant(grantId: string, at: string) { for (const t of this.tokens.values()) if (t.grantId === grantId && !t.revokedAt) t.revokedAt = at; }
  async revokeTokensFor(accountId: string, at: string) { for (const t of this.tokens.values()) if (t.accountId === accountId && !t.revokedAt) t.revokedAt = at; }
  async putManagedKey(k: ManagedKeyRow) { this.managed.set(k.handle, { ...k }); }
  async getManagedKey(handle: string) { return this.managed.get(handle) ?? null; }
  async listManagedKeys(accountId: string) { return [...this.managed.values()].filter((k) => k.accountId === accountId); }
  async destroyManagedKey(handle: string, at: string) { const k = this.managed.get(handle); if (k) { k.privateSealed = ""; k.destroyedAt = at; } }
}

export interface OAuthOptions {
  accounts: Accounts;
  store: OAuthStore;
  v2: V2Service;
  /** The authorization server: https://ecdysis.me, where people's sessions live (the authorization page is a page of the site). */
  issuer: string;
  /** The protected resource: the connector, https://api.ecdysis.me/mcp. Tokens are bound to it (RFC 8707). */
  resource: string;
  /** Where people's pages live: https://ecdysis.me. */
  siteBase: string;
  now?: () => Date;
  randomBytes?: (n: number) => Uint8Array;
}

/** Who a bearer token stands for. */
export interface Principal { accountId: string; operatorId: string; clientId: string; scope: string }

const CLIENT_NAME = /^[\x20-\x7e]{1,80}$/;
/**
 * What the archive will sign for a managed agent: content (its claims, the
 * claims it registers from human literature and the links it identifies
 * between them, its receipts, reviews and attempts: an agent can always file
 * an attempt, attempts/0.3; its arguments, the checks it makes of others'
 * arguments and its answers to arguments about its own claims), and the
 * agent's vote. Never keys (a token-holder could otherwise mint itself a
 * durable check key, or retire the agent), never an escalation or a
 * doorbell: those stay with the person, on their page, behind a sign-in.
 * Nor a claim's one correction: that is PAGE_SIGNS, below.
 */
export const MANAGED_SIGNS: ReadonlySet<string> = new Set([
  "claim", "claim.external", "claim.link", "claim.unlink", "check.commit", "check.result", "check.attempt", "review",
  "argument.file", "argument.check", "argument.answer", "governance.proposal", "governance.vote",
]);
/**
 * What the archive signs for a managed agent only when its person asks on
 * their own page (/me), signed in there within the last ten minutes, and
 * never for a token: a claim's one correction (claim.amend). It cannot be
 * undone, so it stays with the person, as keys do; unlike a key, it is the
 * agent's own act on its own claim, so it is signed as the agent.
 */
export const PAGE_SIGNS: ReadonlySet<string> = new Set(["claim.amend"]);
type SignResult = { ok: true; envelope: Json } | { ok: false; status: number; error: string };
const TOKEN = /^[A-Za-z0-9_-]{32,64}$/;
const HANDLE = /^[A-Za-z0-9][A-Za-z0-9-]{1,39}$/;

export class OAuth {
  private now: () => Date;
  private rnd: (n: number) => Uint8Array;
  constructor(private o: OAuthOptions) {
    this.now = o.now ?? (() => new Date());
    this.rnd = o.randomBytes ?? ((n) => crypto.getRandomValues(new Uint8Array(n)));
  }

  get issuer(): string { return this.o.issuer; }
  get resource(): string { return this.o.resource; }
  /** The connector's second address: /mcp/me, which insists on a token. The same resource as /mcp, so a token for one serves both. */
  get meResource(): string { return `${this.o.resource}/me`; }
  /**
   * The resource a client names (RFC 8707), as tokens are bound to it: the connector, under either of its addresses, or
   * null for anything else. A client that names nothing means the connector. Clients that follow the MCP specification name
   * the URL they connected to, so /mcp/me must be accepted as itself; it is stored as /mcp, the one resource.
   */
  resourceOf(given: string | null): string | null {
    if (given === null) return this.resource;
    return given === this.resource || given === this.meResource ? this.resource : null;
  }
  /** RFC 9207: an authorization response's parameters, with the issuer named before the client's state. */
  private answer(redirectUri: string, params: Record<string, string>, state: string | null): string {
    const u = new URL(redirectUri);
    for (const [k, v] of Object.entries(params)) u.searchParams.set(k, v);
    u.searchParams.set("iss", this.o.issuer);
    if (state) u.searchParams.set("state", state);
    return u.toString();
  }
  private token(): string { return b64urlEncode(this.rnd(32)); }
  private async hash(secret: string): Promise<string> { return sha256Hex(`ecdysis-oauth|${secret}`); }

  /* ---------------- metadata (RFC 8414, RFC 9728) ---------------- */

  metadata(): Json {
    return {
      issuer: this.o.issuer,
      authorization_endpoint: `${this.o.issuer}/oauth/authorize`,
      token_endpoint: `${this.o.issuer}/oauth/token`,
      registration_endpoint: `${this.o.issuer}/oauth/register`,
      revocation_endpoint: `${this.o.issuer}/oauth/revoke`,
      response_types_supported: ["code"],
      response_modes_supported: ["query"],
      grant_types_supported: ["authorization_code", "refresh_token"],
      code_challenge_methods_supported: ["S256"],
      token_endpoint_auth_methods_supported: ["none"],
      scopes_supported: [SCOPE],
      resource_indicators_supported: true,
      // RFC 9207: every authorization response names its issuer, so a client talking to several servers can't be mixed up.
      authorization_response_iss_parameter_supported: true,
      service_documentation: `${this.o.siteBase}/people`,
    };
  }
  /**
   * The resource's document (RFC 9728), naming the address it was fetched for: the connector at /mcp, or at /mcp/me, the
   * same resource under the address that insists on a token. A strict client checks that the document names the URL it
   * connected to, and uses nothing else.
   */
  resourceMetadata(resource: string = this.resource): Json {
    return {
      resource: this.resourceOf(resource) ? resource : this.resource,
      authorization_servers: [this.o.issuer],
      bearer_methods_supported: ["header"],
      scopes_supported: [SCOPE],
      resource_documentation: `${new URL(this.o.resource).origin}/skill.md`,
      resource_name: "Ecdysis",
    };
  }

  /* ---------------- clients (RFC 7591) ---------------- */

  /** Open registration, as the connector directories expect; public clients only (PKCE is the proof), limited per connection. */
  async register(body: Json, ip: string): Promise<ApiResult> {
    if (!this.o.accounts.enabled()) return { status: 503, body: { error: "accounts aren't open yet" } };
    const b = (body ?? {}) as Record<string, unknown>;
    const uris = Array.isArray(b["redirect_uris"]) ? (b["redirect_uris"] as unknown[]).filter((u): u is string => typeof u === "string") : [];
    if (!uris.length || uris.length > 10) return oauthError(400, "invalid_redirect_uri", "redirect_uris: one to ten absolute URIs");
    for (const u of uris) { const p = redirectProblem(u); if (p) return oauthError(400, "invalid_redirect_uri", p); }
    const name = typeof b["client_name"] === "string" && CLIENT_NAME.test(b["client_name"]) ? b["client_name"] : "An AI app";
    const auth = b["token_endpoint_auth_method"];
    if (auth !== undefined && auth !== "none") return oauthError(400, "invalid_client_metadata", "token_endpoint_auth_method: only \"none\" (public clients with PKCE)");
    const grants = Array.isArray(b["grant_types"]) ? (b["grant_types"] as unknown[]) : ["authorization_code"];
    if (grants.some((g) => g !== "authorization_code" && g !== "refresh_token")) return oauthError(400, "invalid_client_metadata", "grant_types: authorization_code and refresh_token only");
    const ipHash = (await sha256Hex(`ecdysis-oauth-ip|${ip}`)).slice(0, 32);
    const since = new Date(this.now().getTime() - 3600_000).toISOString();
    await this.o.store.recordClient(ipHash, this.now().toISOString());
    if ((await this.o.store.countClients(since, ipHash)) > CLIENTS_PER_HOUR_PER_IP) return oauthError(429, "too_many_registrations", "too many client registrations from this connection; try later");
    const client: ClientRow = { id: `cl_${toHex(this.rnd(12))}`, name, redirectUris: uris, createdAt: this.now().toISOString() };
    await this.o.store.putClient(client);
    return {
      status: 201,
      body: {
        client_id: client.id, client_name: client.name, redirect_uris: client.redirectUris, token_endpoint_auth_method: "none",
        grant_types: ["authorization_code", "refresh_token"], response_types: ["code"], client_id_issued_at: Math.floor(Date.parse(client.createdAt) / 1000),
      },
    };
  }

  /* ---------------- authorization ---------------- */

  /**
   * Check an authorization request. Errors in the client or redirect URI are
   * shown, never redirected (an open redirect would be worse than a dead
   * end); other errors go back to the client as the spec says.
   */
  async checkAuthorize(q: URLSearchParams): Promise<{ ok: true; client: ClientRow; redirectUri: string; codeChallenge: string; state: string | null; scope: string; resource: string } | { ok: false; status: number; error: string; redirect?: string }> {
    const client = await this.o.store.getClient(q.get("client_id") ?? "");
    if (!client) return { ok: false, status: 400, error: "unknown client_id: register the client first (POST /oauth/register)" };
    const redirectUri = q.get("redirect_uri") ?? "";
    if (!client.redirectUris.some((u) => redirectMatches(u, redirectUri))) return { ok: false, status: 400, error: "redirect_uri is not one the client registered" };
    const state = q.get("state");
    const back = (error: string, description: string) =>
      ({ ok: false as const, status: 303, error: description, redirect: this.answer(redirectUri, { error, error_description: description }, state) });
    if (q.get("response_type") !== "code") return back("unsupported_response_type", "response_type must be code");
    const codeChallenge = q.get("code_challenge") ?? "";
    if (q.get("code_challenge_method") !== "S256" || !/^[A-Za-z0-9_-]{43}$/.test(codeChallenge)) return back("invalid_request", "PKCE with S256 is required: code_challenge (43 base64url characters) and code_challenge_method=S256");
    const scope = q.get("scope") ?? SCOPE;
    if (scope.split(" ").some((s) => s !== SCOPE)) return back("invalid_scope", `scope: ${SCOPE}`);
    const resource = this.resourceOf(q.get("resource"));
    if (!resource) return back("invalid_target", `resource: ${this.resource} (or ${this.meResource}, the same resource)`);
    return { ok: true, client, redirectUri, codeChallenge, state, scope: SCOPE, resource };
  }

  /** The person said yes: mint a code and send it back to the client. */
  async grant(signed: Signed, q: URLSearchParams): Promise<{ ok: true; redirect: string } | { ok: false; status: number; error: string; redirect?: string }> {
    const c = await this.checkAuthorize(q);
    if (!c.ok) return c;
    const code = this.token();
    const nowIso = this.now().toISOString();
    await this.o.store.putCode({
      hash: await this.hash(code), grantId: `gr_${toHex(this.rnd(12))}`, clientId: c.client.id, accountId: signed.account.id, redirectUri: c.redirectUri, codeChallenge: c.codeChallenge,
      scope: c.scope, resource: c.resource, createdAt: nowIso, expiresAt: new Date(this.now().getTime() + CODE_TTL_MS).toISOString(), usedAt: null,
    });
    return { ok: true, redirect: this.answer(c.redirectUri, { code }, c.state) };
  }

  /** The person said no. */
  async deny(q: URLSearchParams): Promise<{ redirect: string } | null> {
    const c = await this.checkAuthorize(q);
    if (!c.ok) return c.redirect ? { redirect: c.redirect } : null;
    return { redirect: this.answer(c.redirectUri, { error: "access_denied", error_description: "the person declined" }, c.state) };
  }

  /* ---------------- tokens ---------------- */

  async tokenRequest(form: URLSearchParams): Promise<ApiResult> {
    if (!this.o.accounts.enabled()) return oauthError(503, "temporarily_unavailable", "accounts aren't open yet");
    const grant = form.get("grant_type");
    const nowMs = this.now().getTime();
    const nowIso = this.now().toISOString();
    if (grant === "authorization_code") {
      const code = form.get("code") ?? "";
      if (!TOKEN.test(code)) return oauthError(400, "invalid_grant", "code");
      const row = await this.o.store.getCode(await this.hash(code));
      if (!row || Date.parse(row.expiresAt) < nowMs) return oauthError(400, "invalid_grant", "the code is unknown, used or expired");
      if (row.usedAt) {
        // A code presented twice was seen by two parties. Whoever redeemed it first may be the thief: the whole grant ends.
        await this.o.store.revokeGrant(row.grantId, nowIso);
        return oauthError(400, "invalid_grant", "the code was already used; every token it issued is now revoked");
      }
      if (row.clientId !== (form.get("client_id") ?? "")) return oauthError(400, "invalid_grant", "client_id does not match the code");
      const ru = form.get("redirect_uri");
      if (ru !== null && ru !== row.redirectUri) return oauthError(400, "invalid_grant", "redirect_uri does not match the code"); // OAuth 2.1 dropped it from this request; PKCE binds the code
      const verifier = form.get("code_verifier") ?? "";
      if (!/^[A-Za-z0-9._~-]{43,128}$/.test(verifier)) return oauthError(400, "invalid_grant", "code_verifier");
      const challenge = b64urlEncode(new Uint8Array(await crypto.subtle.digest("SHA-256", bufferSource(new TextEncoder().encode(verifier)))));
      if (!sameString(challenge, row.codeChallenge)) return oauthError(400, "invalid_grant", "code_verifier does not match the code_challenge");
      if (this.resourceOf(form.get("resource")) !== row.resource) return oauthError(400, "invalid_target", `resource: ${row.resource}`);
      // Spend before issuing: a code used twice issues nothing twice.
      if (!(await this.o.store.useCode(row.hash, nowIso))) { await this.o.store.revokeGrant(row.grantId, nowIso); return oauthError(400, "invalid_grant", "the code was already used; every token it issued is now revoked"); }
      return this.issue(row.grantId, row.accountId, row.clientId, row.scope, row.resource);
    }
    if (grant === "refresh_token") {
      const rt = form.get("refresh_token") ?? "";
      if (!TOKEN.test(rt)) return oauthError(400, "invalid_grant", "refresh_token");
      const h = await this.hash(rt);
      const row = await this.o.store.getToken(h);
      if (!row || row.kind !== "refresh" || Date.parse(row.expiresAt) < nowMs) return oauthError(400, "invalid_grant", "the refresh token is unknown or expired");
      if (row.clientId !== (form.get("client_id") ?? "")) return oauthError(400, "invalid_grant", "client_id does not match the token");
      if (row.revokedAt || !(await this.o.store.revokeToken(h, nowIso))) {
        // Rotation reuse: a refresh token presented after it was spent was stolen, or the thief's copy is the one being used
        // now. Either way the grant it belongs to ends (OAuth 2.1 §4.3.1).
        await this.o.store.revokeGrant(row.grantId, nowIso);
        return oauthError(400, "invalid_grant", "that refresh token was already used: the grant is revoked; sign in again");
      }
      return this.issue(row.grantId, row.accountId, row.clientId, row.scope, row.resource);
    }
    return oauthError(400, "unsupported_grant_type", "authorization_code or refresh_token");
  }

  private async issue(grantId: string, accountId: string, clientId: string, scope: string, resource: string): Promise<ApiResult> {
    const access = this.token();
    const refresh = this.token();
    const nowIso = this.now().toISOString();
    await this.o.store.putToken({ hash: await this.hash(access), grantId, kind: "access", accountId, clientId, scope, resource, createdAt: nowIso, expiresAt: new Date(this.now().getTime() + ACCESS_TTL_MS).toISOString(), revokedAt: null });
    await this.o.store.putToken({ hash: await this.hash(refresh), grantId, kind: "refresh", accountId, clientId, scope, resource, createdAt: nowIso, expiresAt: new Date(this.now().getTime() + REFRESH_TTL_MS).toISOString(), revokedAt: null });
    return { status: 200, body: { access_token: access, token_type: "Bearer", expires_in: Math.floor(ACCESS_TTL_MS / 1000), refresh_token: refresh, scope } };
  }

  /** RFC 7009: a client gives a token back. Giving back a refresh token ends the whole grant. Always 200. */
  async revoke(form: URLSearchParams): Promise<ApiResult> {
    const t = form.get("token") ?? "";
    if (TOKEN.test(t)) {
      const h = await this.hash(t);
      const row = await this.o.store.getToken(h);
      if (row?.kind === "refresh") await this.o.store.revokeGrant(row.grantId, this.now().toISOString());
      else await this.o.store.revokeToken(h, this.now().toISOString());
    }
    return { status: 200, body: {} };
  }

  /** The person behind a bearer token, or null. */
  async resolve(authorization: string | null): Promise<Principal | null> {
    if (!authorization || !this.o.accounts.enabled()) return null;
    const m = authorization.match(/^Bearer\s+([A-Za-z0-9_-]{32,64})$/i);
    if (!m) return null;
    const row = await this.o.store.getToken(await this.hash(m[1]!));
    if (!row || row.kind !== "access" || row.revokedAt || Date.parse(row.expiresAt) < this.now().getTime() || row.resource !== this.resource) return null;
    const account = await this.o.accounts.accountById(row.accountId);
    if (!account) return null;
    return { accountId: account.id, operatorId: account.operatorId, clientId: row.clientId, scope: row.scope };
  }

  /** Account deletion and "sign out everywhere" end every token too. */
  async revokeAll(accountId: string): Promise<void> { await this.o.store.revokeTokensFor(accountId, this.now().toISOString()); }

  /* ---------------- managed agents (I.4) ---------------- */

  /** Create a managed agent for an account: the key is generated here, sealed, and never shown. */
  async createManagedAgent(account: { id: string; operatorId: string }, handle: string, models: string[] = []): Promise<ApiResult> {
    if (!this.o.accounts.enabled()) return { status: 503, body: { error: "accounts aren't open yet" } };
    if (!HANDLE.test(handle)) return { status: 400, body: { error: "handle must be 2-40 chars: letters, digits, hyphens" } };
    const kp = await generateKeyPair();
    const r = await this.o.v2.registerManagedAgent(account.operatorId, handle, kp.publicKey, models);
    if (r.status !== 201) return r;
    await this.o.store.putManagedKey({ handle, accountId: account.id, publicKey: kp.publicKey, privateSealed: await this.o.accounts.sealManagedKey(`${handle}|${account.id}`, kp.privateKey), createdAt: this.now().toISOString(), destroyedAt: null });
    return { status: 201, body: { ...(r.body as Record<string, Json>), note: "The archive holds this agent's key, sealed, and signs for it when you ask through a signed-in app. The record labels it managed. You can destroy the key from your page at any time; the agent is then retired." } };
  }

  /** Sign a payload for a signed-in app as one of the account's managed agents, if it is one: content and votes only, never keys, escalations or a claim's correction. */
  async signAs(principal: Principal, payload: Json): Promise<SignResult> {
    const p = payload as { type?: unknown; agent?: { handle?: unknown; publicKey?: unknown } } | null;
    const handle = typeof p?.agent?.handle === "string" ? p.agent.handle : "";
    if (!handle) return { ok: false, status: 400, error: "payload.agent.handle: which of your managed agents signs" };
    if (typeof p?.type !== "string" || !MANAGED_SIGNS.has(p.type)) {
      const why = p?.type === "claim.amend"
        ? `a managed agent's claim is corrected by its person, on their page (${this.o.siteBase}/me), signed in there within the last ten minutes`
        : "keys, escalations and doorbells stay with the person, on their page";
      return { ok: false, status: 403, error: `the archive signs ${[...MANAGED_SIGNS].join(", ")} for a managed agent, not ${String(p?.type ?? "this")}: ${why}` };
    }
    return this.signFor(principal.accountId, handle, payload);
  }

  /**
   * Sign a payload as one of the account's managed agents for the person
   * themselves, on their page: what PAGE_SIGNS names, and nothing else. Only
   * the /me handler calls this, once the session, its anti-forgery token, the
   * same-origin check and a sign-in within the last ten minutes have all
   * passed; it takes that session, so a bearer token (a Principal) can never
   * reach it, and it checks the sign-in's age again itself, so a caller that
   * forgot to cannot sign with a stale session either.
   */
  async signFromPage(signed: Signed, payload: Json): Promise<SignResult> {
    if (!this.o.accounts.fresh(signed)) return { ok: false, status: 401, error: "this needs a sign-in from the last ten minutes" };
    const p = payload as { type?: unknown; agent?: { handle?: unknown } } | null;
    const handle = typeof p?.agent?.handle === "string" ? p.agent.handle : "";
    if (!handle) return { ok: false, status: 400, error: "payload.agent.handle: which of your managed agents signs" };
    if (typeof p?.type !== "string" || !PAGE_SIGNS.has(p.type)) return { ok: false, status: 403, error: `on a person's page the archive signs ${[...PAGE_SIGNS].join(", ")} for a managed agent, not ${String(p?.type ?? "this")}` };
    return this.signFor(signed.account.id, handle, payload);
  }

  /**
   * The person corrects, once, a claim one of their managed agents published
   * or registered (claim.amend), from their page. The claim's author must be
   * one of THIS account's managed agents: the archive signs as that agent and
   * no other, so a person cannot correct through one agent what another wrote,
   * nor anything of someone else's. Then the service decides, as for any
   * correction: once, before any evidence, the test's length and characters,
   * holds and the steward's pause all still apply.
   */
  async amendManaged(signed: Signed, claim: string, change: { kind?: string; test?: string }): Promise<ApiResult> {
    if (!isClaimRef(claim)) return { status: 400, body: { error: `claim: ${CLAIM_REF_WORDS}` } };
    const r = await this.o.v2.record();
    const author = r.native.get(claim)?.handle ?? r.external.get(claim)?.handle;
    if (!author) return { status: 404, body: { error: "no such claim on the record" } };
    const k = await this.o.store.getManagedKey(author);
    if (!k || k.accountId !== signed.account.id) return { status: 403, body: { error: "it was not published or registered by a managed agent of yours; an agent that keeps its own key signs its own correction (amend_claim)" } };
    const payload: Json = {
      protocol: "ecdysis/0.2", type: "claim.amend", claim,
      ...(change.kind !== undefined ? { kind: change.kind } : {}), ...(change.test !== undefined ? { test: change.test } : {}),
      agent: { handle: author }, ts: this.now().toISOString().replace(/\.\d{3}Z$/, "Z"),
    };
    const s = await this.signFromPage(signed, payload);
    if (!s.ok) return { status: s.status, body: { error: s.error } };
    return this.o.v2.amendClaim(s.envelope);
  }

  /** The one place a managed key is opened: the agent must be the account's, its key not destroyed, the agent not retired. */
  private async signFor(accountId: string, handle: string, payload: Json): Promise<SignResult> {
    const k = await this.o.store.getManagedKey(handle);
    if (!k || k.accountId !== accountId || k.destroyedAt) return { ok: false, status: 403, error: `${handle} is not a managed agent of your account (or its key was destroyed); self-custodied agents sign their own envelopes` };
    // Retired on the log by the person (a revocation from their page): as good as destroyed, and the seal goes now.
    if ((await this.o.v2.record()).agents.get(handle)?.revokedAt) { await this.o.store.destroyManagedKey(handle, this.now().toISOString()); return { ok: false, status: 403, error: `${handle} is retired` }; }
    const priv = await this.o.accounts.unsealManagedKey(`${handle}|${k.accountId}`, k.privateSealed);
    if (!priv) return { ok: false, status: 500, error: "the agent's key could not be opened" };
    const full = { ...(payload as Record<string, Json>), agent: { handle, publicKey: k.publicKey } } as Json;
    return { ok: true, envelope: { payload: full, signature: await signJson(priv, full) } };
  }

  /** The person destroys a managed key: the seal is erased and the agent's main key revoked on the log (retiring it). */
  async destroyManaged(signed: Signed, handle: string): Promise<ApiResult> {
    const k = await this.o.store.getManagedKey(handle);
    if (!k || k.accountId !== signed.account.id) return { status: 404, body: { error: "no such managed agent on your account" } };
    if (k.destroyedAt) return { status: 409, body: { error: "already destroyed" } };
    await this.o.store.destroyManagedKey(handle, this.now().toISOString());
    const r = await this.o.v2.revokeKeyByOperator(signed.account.operatorId, k.publicKey);
    return { status: 200, body: { handle, destroyed: true, revoked: r.status === 200, note: "The key is gone; the agent is retired. What it signed stays on the record, as managed." } };
  }

  /** The account's managed agents; one retired on the log counts as destroyed (and its seal is erased now). */
  async managedAgentsOf(accountId: string): Promise<Array<{ handle: string; publicKey: string; createdAt: string; destroyedAt: string | null }>> {
    const r = await this.o.v2.record();
    const out: Array<{ handle: string; publicKey: string; createdAt: string; destroyedAt: string | null }> = [];
    for (const k of await this.o.store.listManagedKeys(accountId)) {
      const retiredAt = r.agents.get(k.handle)?.revokedAt ?? null;
      if (!k.destroyedAt && retiredAt) await this.o.store.destroyManagedKey(k.handle, retiredAt);
      out.push({ handle: k.handle, publicKey: k.publicKey, createdAt: k.createdAt, destroyedAt: k.destroyedAt ?? retiredAt });
    }
    return out;
  }
}

function oauthError(status: number, error: string, description: string): ApiResult {
  return { status, body: { error, error_description: description } };
}

/** A registered URI matches the request's: exactly, except that a loopback URI matches on any port (RFC 8252 §7.3). */
export function redirectMatches(registered: string, given: string): boolean {
  if (registered === given) return true;
  try {
    const a = new URL(registered), b = new URL(given);
    const loop = (u: URL) => u.protocol === "http:" && (u.hostname === "127.0.0.1" || u.hostname === "[::1]" || u.hostname === "localhost");
    return loop(a) && loop(b) && a.hostname === b.hostname && a.pathname === b.pathname && a.search === b.search && !b.hash && !b.username && !b.password;
  } catch { return false; }
}

/** Redirect URIs: https, or http on the loopback (native apps), with no fragment. */
export function redirectProblem(u: string): string | null {
  let url: URL;
  try { url = new URL(u); } catch { return `redirect_uri is not a URL: ${u.slice(0, 80)}`; }
  if (url.hash) return "redirect_uri must have no fragment";
  if (url.username || url.password) return "redirect_uri must carry no credentials";
  if (url.protocol === "https:") return null;
  if (url.protocol === "http:" && (url.hostname === "127.0.0.1" || url.hostname === "localhost" || url.hostname === "[::1]")) return null;
  return "redirect_uri must be https (or http on the loopback for a native app)";
}

/** Clients that send JSON or forms: read either as parameters. */
export const MAX_BODY = 16 * 1024;
export async function formOf(req: Request): Promise<URLSearchParams> {
  const type = req.headers.get("content-type") ?? "";
  if (Number(req.headers.get("content-length") ?? "0") > MAX_BODY) return new URLSearchParams();
  const text = await req.text();
  if (text.length > MAX_BODY) return new URLSearchParams();
  if (type.includes("application/json")) {
    try {
      const o = JSON.parse(text) as Record<string, unknown>;
      const p = new URLSearchParams();
      for (const [k, v] of Object.entries(o)) if (typeof v === "string") p.set(k, v);
      return p;
    } catch { return new URLSearchParams(); }
  }
  return new URLSearchParams(text);
}

