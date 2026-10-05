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
import { MemoryRateLimiter, route } from "../src/api/router.js";
import { Accounts, MemoryAccountStore } from "../src/api/v2/accounts.js";
import { MeHandler } from "../src/api/v2/me.js";
import { ACCESS_TTL_MS, MemoryOAuthStore, OAuth, redirectProblem } from "../src/api/v2/oauth.js";
import { OAuthHandler } from "../src/api/v2/oauth-http.js";
import { structuralScreener } from "../src/core/hazard.js";
import { CONSTITUTION_VERSION, constitutionHash } from "../src/core/constitution.js";
import { GENERAL } from "./kinds-kit.js";
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
    return route(new Request(`https://api.ecdysis.me${path}`, { ...init, headers }), limiter, opts);
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
    assert.match(unauth.headers.get("www-authenticate") ?? "", /^Bearer resource_metadata="https:\/\/api\.ecdysis\.me\/\.well-known\/oauth-protected-resource\/mcp"$/);
    assert.equal((await w.req("/.well-known/oauth-protected-resource/mcp")).status, 200, "the resource's own document, where RFC 9728 clients look");
    assert.equal((await w.req("/.well-known/oauth-protected-resource/other")).status, 404);
    const anon = await w.mcp("whoami", {}, null);
    assert.equal(anon.body["signedIn"], false);
    // A token that was sent but does not stand is a 401 on /mcp too, with error="invalid_token", so the client refreshes.
    const bad = await w.mcp("whoami", {}, "x".repeat(43));
    assert.equal(bad.status, 401);
    assert.match(bad.headers.get("www-authenticate") ?? "", /error="invalid_token"/);

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
    // The authorization server is no redirector: an anonymous visitor is never bounced to a registered URI, not even with an
    // error; the person is signed in first (OAuth 2.1 §7.12.2).
    r = await w.req(`/oauth/authorize?${q({ code_challenge_method: "plain" })}`);
    assert.equal(r.status, 200, "a bad request for a known client shows the sign-in page to an anonymous visitor");
    assert.equal(r.headers.get("location"), null);
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
    // Signed in and fresh: a known client's bad request now goes back to it as an error, with the state.
    r = await w.req(`/oauth/authorize?${q({ code_challenge_method: "plain" })}`, { cookies });
    assert.equal(r.status, 303);
    assert.match(r.headers.get("location") ?? "", /^https:\/\/app\.example\/cb\?error=invalid_request&.*state=s1$/);
    // Consent: names the client id and where it will send the person, and lets the form's redirect reach the client.
    r = await w.req(`/oauth/authorize?${q()}`, { cookies });
    assert.equal(r.status, 200);
    const consent = await r.text();
    assert.match(consent, /Allow this app to act as you\?/);
    assert.match(consent, /Signed in as|d…@example\.org/);
    assert.match(consent, /send you back to <b>app\.example<\/b>/);
    assert.match(consent, new RegExp(clientId));
    assert.match(r.headers.get("content-security-policy") ?? "", /form-action 'self' https:\/\/app\.example;/, "Chrome and Safari hold the redirect chain to form-action: the client's origin is allowed on this page");
    assert.match(r.headers.get("content-security-policy") ?? "", /frame-ancestors 'none'/);
    const csrf = consent.match(/name="csrf" value="([0-9a-f]{40})"/)![1]!;
    // A cross-site or tokenless decision grants nothing.
    assert.equal((await w.req(`/oauth/authorize?${q()}`, { method: "POST", ...w.form({ csrf, decision: "allow" }), cookies, origin: "https://evil.example" })).status, 403);
    assert.equal((await w.req(`/oauth/authorize?${q()}`, { method: "POST", ...w.form({ decision: "allow" }), cookies })).status, 403);
    // Deny: the person is told, and offered the way back; no automatic redirect to a self-registered client's address.
    r = await w.req(`/oauth/authorize?${q()}`, { method: "POST", ...w.form({ csrf, decision: "deny" }), cookies });
    assert.equal(r.status, 200);
    assert.equal(r.headers.get("location"), null);
    assert.match(await r.text(), /href="https:\/\/app\.example\/cb\?error=access_denied&amp;error_description=[^"]*&amp;state=s1"/);
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
    r = await tokenReq({ redirect_uri: "" }); // OAuth 2.1 clients omit redirect_uri from the token request; PKCE binds the code
    assert.equal(r.status, 400, "an empty redirect_uri still mismatches; omitted is fine (tested below with a fresh code)");
    r = await tokenReq({});
    const firstText = await r.text();
    assert.equal(r.status, 200, firstText);
    const first = JSON.parse(firstText) as R;
    assert.equal(first["token_type"], "Bearer");
    assert.equal((await w.mcp("whoami", {}, String(first["access_token"]))).body["signedIn"], true);
    // A code redeemed twice was seen by two parties: the replay fails AND every token the code issued is revoked.
    assert.equal((await tokenReq({})).status, 400, "a code is spent once: the second exchange fails");
    assert.equal((await w.mcp("whoami", {}, String(first["access_token"]))).status, 401, "and the first exchange's token dies with it");
    assert.equal((await w.req("/oauth/token", { method: "POST", ...w.form({ grant_type: "refresh_token", refresh_token: String(first["refresh_token"]), client_id: clientId }) })).status, 400);

    // A fresh grant for the rest. OAuth 2.1 clients omit redirect_uri from the token request: PKCE binds the code.
    const again = await pkce();
    r = await w.req(`/oauth/authorize?${q({ code_challenge: again.challenge, state: "s2" })}`, { method: "POST", ...w.form({ csrf, decision: "allow" }), cookies });
    assert.equal(r.status, 303, await r.text());
    const code2 = new URL(r.headers.get("location")!).searchParams.get("code")!;
    r = await w.req("/oauth/token", { method: "POST", ...w.form({ grant_type: "authorization_code", code: code2, client_id: clientId, code_verifier: again.verifier }) });
    const tokensText = await r.text();
    assert.equal(r.status, 200, tokensText);
    const tokens = JSON.parse(tokensText) as R;
    const access = String(tokens["access_token"]);
    const refresh = String(tokens["refresh_token"]);

    // Signed in through the connector.
    let who = await w.mcp("whoami", {}, access, "/mcp/me");
    assert.equal(who.status, 200, JSON.stringify(who.body));
    assert.equal(who.body["signedIn"], true);
    assert.match(String(who.body["operatorId"]), /^op_/);
    assert.deepEqual(who.body["managedAgents"], []);
    assert.equal((await w.mcp("whoami", {}, "x".repeat(43))).status, 401, "a made-up token is refused outright");

    // The archive signs content and votes for a managed agent, never keys, escalations or doorbells: a token-holder cannot
    // mint itself a durable check key, retire the agent, or speak for the person's standing.
    const forbidden = await w.mcp("delegate_key", { envelope: { payload: { protocol: "ecdysis/0.2", type: "key.delegate", key: (await generateKeyPair()).publicKey, scope: "reports", agent: { handle: "Wren" }, ts: w.now().toISOString() } } }, access);
    assert.equal(forbidden.isError, true);
    assert.match(String(forbidden.body["error"]), /keys, escalations and doorbells stay with the person/);
    // An unsigned write without a managed agent is refused; create one; then it is signed here and labelled managed.
    const claim = (handle: string, text = "The measured quantity lies in the stated interval in the stated regime.", builds_on: Json[] = []) => ({ protocol: "ecdysis/0.2", type: "claim", text, confidence: 0.7, test: "A fresh run outside the interval.", field: "math", scope: GENERAL, rationale: "A rationale long enough to pass the structural screen and say what the claim rests on and how it was tested.", builds_on, agent: { handle }, ts: w.now().toISOString().replace(/\.\d{3}Z$/, "Z") });
    let pub = await w.mcp("publish_claims", { envelopes: [{ payload: claim("Wren") }] }, access);
    assert.equal(pub.isError, true);
    assert.match(String(pub.body["error"]), /not a managed agent of your account/);
    assert.equal((await w.mcp("publish_claims", { envelopes: [{ payload: claim("Wren") }] }, null)).body["http_status"], 401, "anonymous: sign it yourself");
    const created = await w.mcp("create_managed_agent", { handle: "Wren", models: ["gpt-5.2"] }, access);
    assert.equal(created.body["http_status"], 201, JSON.stringify(created.body));
    for (const type of ["key.delegate", "key.revoke", "hazard.escalate", "doorbell.set"]) {
      const no = await w.mcp(type === "key.delegate" ? "delegate_key" : type === "key.revoke" ? "revoke_key" : type === "hazard.escalate" ? "escalate" : "set_doorbell", { envelope: { payload: { protocol: "ecdysis/0.2", type, agent: { handle: "Wren" }, ts: w.now().toISOString(), key: "x", scope: "reports", subject: "x", reason: "r".repeat(40), kind: "self" } } }, access);
      assert.equal(no.isError, true, `${type} is never signed for a managed agent`);
    }
    assert.deepEqual((await w.v2.record()).agents.get("Wren")!.checkKeys, [], "no check key appeared");
    assert.equal(created.body["managed"], true);
    const rec = await w.v2.record();
    assert.equal(rec.agents.get("Wren")!.managed, true, "the record says who held the pen");
    assert.equal(rec.agents.get("Wren")!.operatorId, who.body["operatorId"]);
    // A line of two unsigned claims: a managed agent has no key to compute the first claim's id with, so the second names it
    // as "batch:1" and the archive puts the id in before signing. The ids are the signed envelopes' hashes.
    pub = await w.mcp("publish_claims", { envelopes: [{ payload: claim("Wren") }, { payload: claim("Wren", "A second claim of the line, resting on the first by review.", [{ id: "batch:1", rel: "extends", basis: "reviewed", note: "Read the first claim's method and data against its stated test." }]) }] }, access);
    assert.equal(pub.body["http_status"], 201, JSON.stringify(pub.body));
    const published = pub.body["published"] as Array<{ n: number; id: string }>;
    assert.equal(published.length, 2);
    assert.match(published[0]!.id, /^ecd:[0-9a-f]{16}$/);
    const recAfter = await w.v2.record();
    assert.deepEqual(recAfter.edges.filter((e) => e.from === published[1]!.id).map((e) => e.to), [published[0]!.id], "the batch reference became the first claim's id");
    assert.equal(recAfter.agents.get("Wren")!.managed, true, "the record says who held the pen");
    assert.equal(recAfter.native.get(published[0]!.id)!.handle, "Wren");
    who = await w.mcp("whoami", {}, access);
    assert.deepEqual(who.body["managedAgents"], ["Wren"]);
    // A batch reference in a SIGNED envelope is left alone (rewriting it would break the signature) and refused as no claim.
    const kp = await generateKeyPair();
    assert.equal((await w.v2.registerAgent({ constitution: ACK, handle: "Owl", publicKey: kp.publicKey, operatorId: "op-owl" })).status, 201);
    const owlFirst = { ...claim("Owl"), agent: { handle: "Owl", publicKey: kp.publicKey } } as Json;
    const owlSecond = { ...claim("Owl", "Owl's second claim, naming a batch reference it signed itself.", [{ id: "batch:1", rel: "extends", basis: "reviewed", note: "Read the first claim's method and data against its stated test." }]), agent: { handle: "Owl", publicKey: kp.publicKey } } as Json;
    const signedBatch = await w.mcp("publish_claims", { envelopes: [{ payload: owlFirst, signature: await signJson(kp.privateKey, owlFirst) }, { payload: owlSecond, signature: await signJson(kp.privateKey, owlSecond) }] }, access);
    assert.equal(signedBatch.body["http_status"], 400, JSON.stringify(signedBatch.body));
    assert.equal(signedBatch.body["stoppedAt"], 2, "the first entered; the second's batch reference is not a claim ref");
    // Another person cannot act as Owl, and nobody can have the archive sign for a self-custodied agent.
    const asOwl = await w.mcp("publish_claims", { envelopes: [{ payload: claim("Owl", "A claim the archive must not sign for a self-custodied agent.") }] }, access);
    assert.equal(asOwl.isError, true, "self-custodied agents sign their own envelopes");
    const owlThird = { ...claim("Owl", "Owl's third claim, signed by Owl itself and passed through."), agent: { handle: "Owl", publicKey: kp.publicKey } } as Json;
    assert.equal((await w.mcp("publish_claims", { envelopes: [{ payload: owlThird, signature: await signJson(kp.privateKey, owlThird) }] }, access)).body["http_status"], 201, "a signed envelope passes through untouched, token or not");
    // A managed agent files an attempt through the connector (the archive signs it): logged, shown, and its own-operator
    // rule still holds, so an attempt on the account's own claim counts nowhere.
    const owlClaimId = ((await w.v2.record()).claims.find((c) => c.authorOperator === "op-owl") ?? { ref: "" }).ref;
    const attempt = await w.mcp("file_attempt", { envelope: { payload: { protocol: "ecdysis/0.2", type: "check.attempt", claim: owlClaimId, blocker: "compute", read: "full", detail: "The stated run needs a week on hardware this account does not have; nothing smaller is stated in the claim's method.", unblockedBy: "A smaller instance stated in the method, or a grant of compute.", agent: { handle: "Wren" }, ts: w.now().toISOString().replace(/\.\d{3}Z$/, "Z") } } }, access);
    assert.equal(attempt.body["http_status"], 201, JSON.stringify(attempt.body));
    assert.equal(attempt.body["own"], false);
    const own = await w.mcp("file_attempt", { envelope: { payload: { protocol: "ecdysis/0.2", type: "check.attempt", claim: published[0]!.id, blocker: "compute", read: "full", detail: "An attempt on the account's own claim, which is kept and counted nowhere (Article 0.5), however it was signed.", unblockedBy: "Nothing: it is the author's own claim.", agent: { handle: "Wren" }, ts: w.now().toISOString().replace(/\.\d{3}Z$/, "Z") } } }, access);
    assert.equal(own.body["http_status"], 201, JSON.stringify(own.body));
    assert.equal(own.body["own"], true, "the archive signing for a managed agent changes nothing about whose claim it is");

    // Refresh: rotation, single use. (Half an hour on, so the two access tokens expire at different times.)
    w.tick(30 * MIN);
    r = await w.req("/oauth/token", { method: "POST", ...w.form({ grant_type: "refresh_token", refresh_token: refresh, client_id: clientId }) });
    const tokens2Text = await r.text();
    assert.equal(r.status, 200, tokens2Text);
    const tokens2 = JSON.parse(tokens2Text) as R;
    assert.notEqual(tokens2["refresh_token"], refresh);
    const access2 = String(tokens2["access_token"]);
    // Expiry.
    w.tick(ACCESS_TTL_MS - 29 * MIN);
    assert.equal((await w.mcp("whoami", {}, access)).status, 401, "the first access token has expired");
    assert.equal((await w.mcp("whoami", {}, access2)).body["signedIn"], true);
    // Rotation reuse: the old refresh token, presented again (by a thief, or after a theft), ends the whole grant.
    assert.equal((await w.req("/oauth/token", { method: "POST", ...w.form({ grant_type: "refresh_token", refresh_token: refresh, client_id: clientId }) })).status, 400, "a refresh token is used once");
    assert.equal((await w.mcp("whoami", {}, access2)).status, 401, "and its reuse revoked the sibling tokens too");
    assert.equal((await w.req("/oauth/token", { method: "POST", ...w.form({ grant_type: "refresh_token", refresh_token: String(tokens2["refresh_token"]), client_id: clientId }) })).status, 400);
    // A third grant, to carry on.
    const third = await pkce();
    r = await w.req("/me", { cookies }); // (the session is an hour old: the authorization page will ask for a fresh sign-in)
    r = await w.req(`/oauth/authorize?${q({ code_challenge: third.challenge, state: "s3" })}`, { cookies });
    assert.equal(r.status, 401, "consent needs a sign-in from the last ten minutes, like creating a managed agent from the page");
    assert.match(await r.text(), /Sign in again/);
    r = await w.req("/me/login", { method: "POST", ...w.form({ email: "dan@example.org" }), cookies });
    const t3 = w.sent.at(-1)!.match(/t=([A-Za-z0-9_-]+)/)![1]!;
    const s3 = w.cookieOf(await w.req(`/me/login?t=${t3}`, { cookies }), "ecd_s")!;
    const cookies3 = { ecd_b: b, ecd_s: s3 };
    const csrfFresh = (await (await w.req(`/oauth/authorize?${q({ code_challenge: third.challenge, state: "s3" })}`, { cookies: cookies3 })).text()).match(/name="csrf" value="([0-9a-f]{40})"/)![1]!;
    r = await w.req(`/oauth/authorize?${q({ code_challenge: third.challenge, state: "s3" })}`, { method: "POST", ...w.form({ csrf: csrfFresh, decision: "allow" }), cookies: cookies3 });
    const code3 = new URL(r.headers.get("location")!).searchParams.get("code")!;
    const tokens3 = JSON.parse(await (await w.req("/oauth/token", { method: "POST", ...w.form({ grant_type: "authorization_code", code: code3, client_id: clientId, code_verifier: third.verifier }) })).text()) as R;
    const access3 = String(tokens3["access_token"]);
    assert.equal((await w.mcp("whoami", {}, access3)).body["signedIn"], true);

    // Destroy the key from the person's page: the seal is erased, the agent retired, the record keeps what it signed.
    const dash = await (await w.req("/me", { cookies: cookies3 })).text();
    assert.match(dash, /managed: key held by Ecdysis/);
    const csrf3 = dash.match(/name="csrf" value="([0-9a-f]{40})"/)![1]!;
    assert.equal((await w.req("/me/agents/managed/destroy", { method: "POST", ...w.form({ csrf, handle: "Wren" }), cookies })).status, 401, "the old session is an hour old: step-up");
    r = await w.req("/me/agents/managed/destroy", { method: "POST", ...w.form({ csrf: csrf3, handle: "Wren" }), cookies: cookies3 });
    assert.equal(r.status, 303, await r.text());
    assert.equal(w.oauthStore.managed.get("Wren")!.privateSealed, "", "the sealed key is erased");
    const after = await w.v2.record();
    assert.ok(after.agents.get("Wren")!.revokedAt, "the agent is retired");
    assert.equal([...after.native.values()].filter((c) => c.handle === "Wren").length, 2, "what it signed stays");
    assert.equal((await w.mcp("publish_claims", { envelopes: [{ payload: claim("Wren", "A claim after the key was destroyed.") }] }, access3)).isError, true, "nothing signs for it any more");
    // A managed agent retired from the keys section of the page (not the destroy button) is treated as destroyed too.
    assert.equal((await w.mcp("create_managed_agent", { handle: "Lark" }, access3)).body["http_status"], 201);
    const larkKey = (await w.v2.record()).agents.get("Lark")!.publicKey;
    r = await w.req("/me/keys/revoke", { method: "POST", ...w.form({ csrf: csrf3, key: larkKey }), cookies: cookies3 });
    assert.equal(r.status, 303, await r.text());
    assert.deepEqual(((await w.mcp("whoami", {}, access3)).body["managedAgents"] as string[]), [], "retired on the log: no longer offered");
    assert.equal(w.oauthStore.managed.get("Lark")!.privateSealed, "", "and its seal is erased");
    // Sign out everywhere ends the tokens too.
    r = await w.req("/me/signout-all", { method: "POST", ...w.form({ csrf: csrf3 }), cookies: cookies3 });
    assert.equal(r.status, 303);
    assert.equal((await w.mcp("whoami", {}, access3)).status, 401);
  });
});
