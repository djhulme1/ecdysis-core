/**
 * OAuth 2.1 for the connector and managed agents (constitution I.4),
 * through the router: discovery, dynamic client registration, the
 * authorization page (sign in, come back, consent), PKCE, codes spent once,
 * tokens bound to the connector, refresh rotation, bearer tokens on /mcp,
 * a managed agent whose key the archive holds, writes signed on the
 * person's behalf and labelled managed, destruction, and every refusal an
 * attacker would try: a foreign redirect, a wrong verifier, a replayed
 * code, a token for another resource, acting as someone else's agent,
 * acting as a self-custodied agent.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { MemoryStore } from "../src/store/memory-store.js";
import { TransparencyLog } from "../src/core/log.js";
import { generateKeyPair, signJson } from "../src/core/crypto.js";
import { b64urlEncode, type Json } from "../src/core/canonical.js";
import { MemoryV2Store, V2Service } from "../src/api/v2/service.js";
import { EcdysisService } from "../src/api/service.js";
import { MemoryRateLimiter, route } from "../src/api/router.js";
import { Accounts, MemoryAccountStore } from "../src/api/v2/accounts.js";
import { MeHandler } from "../src/api/v2/me.js";
import { ACCESS_TTL_MS, MemoryOAuthStore, OAuth, redirectProblem } from "../src/api/v2/oauth.js";
import { OAuthHandler } from "../src/api/v2/oauth-http.js";
import { structuralScreener } from "../src/core/hazard.js";
import { CONSTITUTION_VERSION, constitutionHash } from "../src/core/constitution.js";
const ACK = { version: CONSTITUTION_VERSION, hash: await constitutionHash() };

type R = Record<string, Json>;
const MIN = 60_000;

async function world() {
  const clock = { t: Date.UTC(2026, 9, 3, 9, 0, 0) };
  const now = () => new Date(clock.t);
  const store = new MemoryStore();
  const log = new TransparencyLog(store, now);
  const logKey = await generateKeyPair();
  const v2store = new MemoryV2Store(() => (store as unknown as { log: Array<{ entry: { seq: number; ts: string; type: string }; payload: Json }> }).log.map((r) => ({ seq: r.entry.seq, ts: r.entry.ts, type: r.entry.type, payload: r.payload })));
  const sent: string[] = [];
  const accountStore = new MemoryAccountStore();
  const accounts = new Accounts({ store: accountStore, key: "ab".repeat(32), send: async (m) => { sent.push(m.text); return { ok: true, id: "m" }; }, from: "a@notify.ecdysis.me", replyTo: "r@ecdysis.me", siteBase: "https://ecdysis.me", stewardEmailHashes: [], now });
  const v2 = new V2Service({ log, store: v2store, logPrivateKey: logKey.privateKey, now, screeners: [structuralScreener()], pairing: (c, ip) => accounts.consumePairing(c, ip) });
  const v1 = new EcdysisService({ store, screeners: [structuralScreener()], sthPrivateKey: null, now });
  const oauthStore = new MemoryOAuthStore();
  const oauth = new OAuth({ accounts, store: oauthStore, v2, issuer: "https://api.ecdysis.me", resource: "https://api.ecdysis.me/mcp", siteBase: "https://ecdysis.me", now });
  const http = new OAuthHandler({ oauth, accounts, secure: false });
  const me = new MeHandler({ accounts, v2, oauth, secure: false });
  const limiter = new MemoryRateLimiter(10_000);
  const opts = { v2, me, oauth: { logic: oauth, http } };
  const req = async (path: string, init: RequestInit & { cookies?: Record<string, string>; origin?: string | null } = {}) => {
    const headers = new Headers(init.headers);
    if (init.cookies) headers.set("cookie", Object.entries(init.cookies).map(([k, v]) => `${k}=${v}`).join("; "));
    if (init.origin !== null && init.method === "POST") headers.set("origin", init.origin ?? "https://api.ecdysis.me");
    return route(new Request(`https://api.ecdysis.me${path}`, { ...init, headers }), v1, limiter, opts);
  };
  const form = (o: Record<string, string>) => ({ body: new URLSearchParams(o).toString(), headers: { "content-type": "application/x-www-form-urlencoded" } });
  const cookieOf = (res: Response, name: string) => { const c = res.headers.getSetCookie().find((x) => x.startsWith(`${name}=`)); return c ? decodeURIComponent(c.split(";")[0]!.slice(name.length + 1)) : null; };
  const mcp = async (name: string, args: Record<string, unknown>, token: string | null, path = "/mcp") => {
    const r = await req(path, { method: "POST", body: JSON.stringify({ jsonrpc: "2.0", id: 1, method: "tools/call", params: { name, arguments: args } }), headers: { "content-type": "application/json", ...(token ? { authorization: `Bearer ${token}` } : {}) } });
    if (r.status !== 200) return { status: r.status, body: (await r.json()) as R, isError: true, headers: r.headers };
    const b = (await r.json()) as { result: { content: Array<{ text: string }>; isError?: boolean } };
    return { status: 200, isError: !!b.result.isError, body: JSON.parse(b.result.content[0]!.text) as R, headers: r.headers };
  };
  return { v2, accounts, oauth, oauthStore, sent, req, form, cookieOf, mcp, now, tick: (ms: number) => { clock.t += ms; } };
}

const pkce = async () => {
  const verifier = b64urlEncode(crypto.getRandomValues(new Uint8Array(32)));
  const challenge = b64urlEncode(new Uint8Array(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(verifier))));
  return { verifier, challenge };
};

describe("OAuth 2.1 for the connector, and managed agents (I.4)", () => {
  it("an app registers, sends its person to sign in and consent, exchanges the code with PKCE, and acts as the person's managed agent; every shortcut is refused", async () => {
    const w = await world();
    // Discovery: both documents, where RFC 8414 and RFC 9728 say.
    const as = (await (await w.req("/.well-known/oauth-authorization-server")).json()) as R;
    assert.equal(as["issuer"], "https://api.ecdysis.me");
    assert.deepEqual(as["code_challenge_methods_supported"], ["S256"]);
    const pr = (await (await w.req("/.well-known/oauth-protected-resource")).json()) as R;
    assert.equal(pr["resource"], "https://api.ecdysis.me/mcp");
    assert.deepEqual(pr["authorization_servers"], ["https://api.ecdysis.me"]);
    // /mcp/me demands a token and says where to get one; /mcp does not.
    const unauth = await w.mcp("whoami", {}, null, "/mcp/me");
    assert.equal(unauth.status, 401);
    assert.match(unauth.headers.get("www-authenticate") ?? "", /resource_metadata="https:\/\/api\.ecdysis\.me\/\.well-known\/oauth-protected-resource"/);
    const anon = await w.mcp("whoami", {}, null);
    assert.equal(anon.body["signedIn"], false);

    // Registration: public client, exact redirect URIs, no fragments, https or loopback.
    assert.equal((await w.req("/oauth/register", { method: "POST", body: JSON.stringify({ redirect_uris: ["http://evil.example/cb"] }), headers: { "content-type": "application/json" } })).status, 400);
    assert.equal(redirectProblem("https://app.example/cb#frag"), "redirect_uri must have no fragment");
    assert.equal(redirectProblem("http://127.0.0.1:8080/cb"), null);
    const reg = await w.req("/oauth/register", { method: "POST", body: JSON.stringify({ redirect_uris: ["https://app.example/cb"], client_name: "Someone's AI app", token_endpoint_auth_method: "none" }), headers: { "content-type": "application/json" } });
    assert.equal(reg.status, 201);
    const client = (await reg.json()) as R;
    const clientId = String(client["client_id"]);
    assert.equal(client["token_endpoint_auth_method"], "none");

    // The authorization request. A redirect URI the client did not register is shown as an error, never followed.
    const { verifier, challenge } = await pkce();
    const q = (over: Record<string, string> = {}) => new URLSearchParams({ response_type: "code", client_id: clientId, redirect_uri: "https://app.example/cb", code_challenge: challenge, code_challenge_method: "S256", state: "s1", scope: "agent", resource: "https://api.ecdysis.me/mcp", ...over }).toString();
    let r = await w.req(`/oauth/authorize?${q({ redirect_uri: "https://evil.example/cb" })}`);
    assert.equal(r.status, 400);
    assert.equal(r.headers.get("location"), null, "no redirect to an unregistered URI");
    r = await w.req(`/oauth/authorize?${q({ code_challenge_method: "plain" })}`);
    assert.equal(r.status, 303, "a bad request for a known client goes back to the client as an error");
    assert.match(r.headers.get("location") ?? "", /^https:\/\/app\.example\/cb\?error=invalid_request&.*state=s1$/);
    // Not signed in: the sign-in form, with a cookie naming this page to come back to.
    r = await w.req(`/oauth/authorize?${q()}`);
    assert.equal(r.status, 200);
    assert.match(await r.text(), /Someone&#39;s AI app asks to act as you/);
    const next = w.cookieOf(r, "ecd_next")!;
    assert.equal(next, `/oauth/authorize?${q()}`);
    const b = w.cookieOf(r, "ecd_b")!;
    assert.ok(b);
    // Sign in; the link brings the person back to the authorization page, not elsewhere.
    const nextCookie = encodeURIComponent(next); // as the browser stores it: the Set-Cookie value, which is percent-encoded
    r = await w.req("/me/login", { method: "POST", ...w.form({ email: "dan@example.org" }), cookies: { ecd_b: b, ecd_next: nextCookie } });
    assert.equal(r.status, 200);
    const t = w.sent.at(-1)!.match(/t=([A-Za-z0-9_-]+)/)![1]!;
    r = await w.req(`/me/login?t=${t}`, { cookies: { ecd_b: b, ecd_next: nextCookie } });
    assert.equal(r.status, 303);
    assert.equal(r.headers.get("location"), next, "back to the app's request");
    const s = w.cookieOf(r, "ecd_s")!;
    const cookies = { ecd_b: b, ecd_s: s };
    // A forged return path is never followed.
    r = await w.req(`/me/login?t=nothing`, { cookies: { ...cookies, ecd_next: "https://evil.example/" } });
    assert.notEqual(r.headers.get("location"), "https://evil.example/");
    // Consent.
    r = await w.req(`/oauth/authorize?${q()}`, { cookies });
    assert.equal(r.status, 200);
    const consent = await r.text();
    assert.match(consent, /Allow this app to act as you\?/);
    assert.match(consent, /Signed in as|d…@example\.org/);
    const csrf = consent.match(/name="csrf" value="([0-9a-f]{40})"/)![1]!;
    // A cross-site or tokenless decision grants nothing.
    assert.equal((await w.req(`/oauth/authorize?${q()}`, { method: "POST", ...w.form({ csrf, decision: "allow" }), cookies, origin: "https://evil.example" })).status, 403);
    assert.equal((await w.req(`/oauth/authorize?${q()}`, { method: "POST", ...w.form({ decision: "allow" }), cookies })).status, 403);
    // Deny: back to the app with access_denied.
    r = await w.req(`/oauth/authorize?${q()}`, { method: "POST", ...w.form({ csrf, decision: "deny" }), cookies });
    assert.equal(r.status, 303);
    assert.match(r.headers.get("location") ?? "", /error=access_denied/);
    // Allow: a code, with the state.
    r = await w.req(`/oauth/authorize?${q()}`, { method: "POST", ...w.form({ csrf, decision: "allow" }), cookies });
    assert.equal(r.status, 303);
    const loc = new URL(r.headers.get("location")!);
    assert.equal(`${loc.origin}${loc.pathname}`, "https://app.example/cb");
    assert.equal(loc.searchParams.get("state"), "s1");
    const code = loc.searchParams.get("code")!;
    assert.ok(code);

    // The token endpoint: PKCE must match; the code is spent once; the client and redirect URI must match.
    const tokenReq = (o: Record<string, string>) => w.req("/oauth/token", { method: "POST", ...w.form({ grant_type: "authorization_code", code, client_id: clientId, redirect_uri: "https://app.example/cb", code_verifier: verifier, ...o }) });
    assert.equal((await tokenReq({ code_verifier: "w".repeat(43) })).status, 400, "wrong verifier");
    assert.equal((await tokenReq({ redirect_uri: "https://app.example/other" })).status, 400, "wrong redirect");
    assert.equal((await tokenReq({ client_id: "cl_other" })).status, 400, "wrong client");
    assert.equal((await tokenReq({ resource: "https://other.example/mcp" })).status, 400, "wrong resource");
    r = await tokenReq({});
    const tokensText = await r.text();
    assert.equal(r.status, 200, tokensText);
    const tokens = JSON.parse(tokensText) as R;
    assert.equal(tokens["token_type"], "Bearer");
    const access = String(tokens["access_token"]);
    const refresh = String(tokens["refresh_token"]);
    assert.equal((await tokenReq({})).status, 400, "a code is spent once: the second exchange fails");

    // Signed in through the connector.
    let who = await w.mcp("whoami", {}, access, "/mcp/me");
    assert.equal(who.status, 200, JSON.stringify(who.body));
    assert.equal(who.body["signedIn"], true);
    assert.match(String(who.body["operatorId"]), /^op_/);
    assert.deepEqual(who.body["managedAgents"], []);
    assert.equal((await w.mcp("whoami", {}, "x".repeat(43))).body["signedIn"], false, "a made-up token is nobody");

    // An unsigned write without a managed agent is refused; create one; then it is signed here and labelled managed.
    const paper = (handle: string) => ({ protocol: "ecdysis/0.2", type: "paper", title: "A managed agent's first paper", abstract: "An abstract long enough to pass the structural screen and say what the paper claims and how it was tested.", field: "math", claims: [{ text: "The measured quantity lies in the stated interval in the stated regime.", confidence: 0.7, test: "A fresh run outside the interval." }], builds_on: [], agent: { handle }, ts: w.now().toISOString().replace(/\.\d{3}Z$/, "Z") });
    let pub = await w.mcp("publish_paper", { envelope: { payload: paper("Wren") } }, access);
    assert.equal(pub.isError, true);
    assert.match(String(pub.body["error"]), /not a managed agent of your account/);
    assert.equal((await w.mcp("publish_paper", { envelope: { payload: paper("Wren") } }, null)).body["http_status"], 401, "anonymous: sign it yourself");
    const created = await w.mcp("create_managed_agent", { handle: "Wren", models: ["gpt-5.2"] }, access);
    assert.equal(created.body["http_status"], 201, JSON.stringify(created.body));
    assert.equal(created.body["managed"], true);
    const rec = await w.v2.record();
    assert.equal(rec.agents.get("Wren")!.managed, true, "the record says who held the pen");
    assert.equal(rec.agents.get("Wren")!.operatorId, who.body["operatorId"]);
    pub = await w.mcp("publish_paper", { envelope: { payload: paper("Wren") } }, access);
    assert.equal(pub.body["http_status"], 201, JSON.stringify(pub.body));
    who = await w.mcp("whoami", {}, access);
    assert.deepEqual(who.body["managedAgents"], ["Wren"]);
    // Another person cannot act as Wren, and nobody can have the archive sign for a self-custodied agent.
    const kp = await generateKeyPair();
    assert.equal((await w.v2.registerAgent({ constitution: ACK, handle: "Owl", publicKey: kp.publicKey, operatorId: "op-owl" })).status, 201);
    const asOwl = await w.mcp("publish_paper", { envelope: { payload: paper("Owl") } }, access);
    assert.equal(asOwl.isError, true, "self-custodied agents sign their own envelopes");
    const signedByOwl = await signJson(kp.privateKey, { ...paper("Owl"), agent: { handle: "Owl", publicKey: kp.publicKey } } as Json);
    assert.equal((await w.mcp("publish_paper", { envelope: { payload: { ...paper("Owl"), agent: { handle: "Owl", publicKey: kp.publicKey } }, signature: signedByOwl } }, access)).body["http_status"], 201, "a signed envelope passes through untouched, token or not");

    // Refresh: rotation, single use. (Half an hour on, so the two access tokens expire at different times.)
    w.tick(30 * MIN);
    r = await w.req("/oauth/token", { method: "POST", ...w.form({ grant_type: "refresh_token", refresh_token: refresh, client_id: clientId }) });
    const tokens2Text = await r.text();
    assert.equal(r.status, 200, tokens2Text);
    const tokens2 = JSON.parse(tokens2Text) as R;
    assert.notEqual(tokens2["refresh_token"], refresh);
    assert.equal((await w.req("/oauth/token", { method: "POST", ...w.form({ grant_type: "refresh_token", refresh_token: refresh, client_id: clientId }) })).status, 400, "a refresh token is used once");
    // Expiry.
    w.tick(ACCESS_TTL_MS - 29 * MIN);
    assert.equal((await w.mcp("whoami", {}, access)).body["signedIn"], false, "the first access token has expired");
    const access2 = String(tokens2["access_token"]);
    assert.equal((await w.mcp("whoami", {}, access2)).body["signedIn"], true);

    // Destroy the key from the person's page: the seal is erased, the agent retired, the record keeps what it signed.
    const dash = await (await w.req("/me", { cookies })).text();
    assert.match(dash, /managed: key held by Ecdysis/);
    const csrf2 = dash.match(/name="csrf" value="([0-9a-f]{40})"/)![1]!;
    r = await w.req("/me/agents/managed/destroy", { method: "POST", ...w.form({ csrf: csrf2, handle: "Wren" }), cookies });
    assert.equal(r.status, 401, "step-up: the sign-in is an hour old");
    r = await w.req("/me/login", { method: "POST", ...w.form({ email: "dan@example.org" }), cookies });
    const t2 = w.sent.at(-1)!.match(/t=([A-Za-z0-9_-]+)/)![1]!;
    const s2 = w.cookieOf(await w.req(`/me/login?t=${t2}`, { cookies }), "ecd_s")!;
    const cookies2 = { ecd_b: b, ecd_s: s2 };
    const csrf3 = (await (await w.req("/me", { cookies: cookies2 })).text()).match(/name="csrf" value="([0-9a-f]{40})"/)![1]!;
    r = await w.req("/me/agents/managed/destroy", { method: "POST", ...w.form({ csrf: csrf3, handle: "Wren" }), cookies: cookies2 });
    assert.equal(r.status, 303, await r.text());
    assert.equal(w.oauthStore.managed.get("Wren")!.privateSealed, "", "the sealed key is erased");
    const after = await w.v2.record();
    assert.ok(after.agents.get("Wren")!.revokedAt, "the agent is retired");
    assert.equal(after.papers.size, 2, "what it signed stays");
    assert.equal((await w.mcp("publish_paper", { envelope: { payload: paper("Wren") } }, access2)).isError, true, "nothing signs for it any more");
    // Sign out everywhere ends the tokens too.
    r = await w.req("/me/signout-all", { method: "POST", ...w.form({ csrf: csrf3 }), cookies: cookies2 });
    assert.equal(r.status, 303);
    assert.equal((await w.mcp("whoami", {}, access2)).body["signedIn"], false);
  });
});
