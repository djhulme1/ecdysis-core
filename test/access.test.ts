/**
 * The operator console's lock: Cloudflare Access tokens are verified again
 * in the Worker, and every way of getting it wrong fails closed.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { accessConfigured, csrfFor, resetAccessKeys, verifyAccess } from "../src/api/access.js";
import { accessKit, AUD } from "./access-kit.js";

const req = (token?: string, host = "ecdysis.me") =>
  new Request(`https://${host}/operator`, { headers: token ? { "cf-access-jwt-assertion": token } : {} });

describe("Cloudflare Access verification", () => {
  it("admits the operator with a valid application token, and only then", async () => {
    resetAccessKeys();
    const k = await accessKit("alpha-team.cloudflareaccess.com");
    const ok = await verifyAccess(req(await k.token()), k.config, k.fetchImpl);
    assert.deepEqual(ok.ok && ok.email, "daniel@hulme.ai");
    const mixed = await verifyAccess(req(await k.token({ email: "Daniel@Hulme.AI" })), k.config, k.fetchImpl);
    assert.ok(mixed.ok, "addresses compare case-insensitively");
    assert.equal((await verifyAccess(req(), k.config, k.fetchImpl)).ok, false);
  });

  it("fails closed when anything is unconfigured", async () => {
    const k = await accessKit("beta-team.cloudflareaccess.com");
    const t = await k.token();
    for (const cfg of [
      { ...k.config, teamDomain: null },
      { ...k.config, aud: null },
      { ...k.config, emailHashes: [] },
      { ...k.config, teamDomain: "evil.example.com" },
      { ...k.config, aud: "not-a-tag" },
    ]) {
      assert.equal(accessConfigured(cfg), false);
      const v = await verifyAccess(req(t), cfg, k.fetchImpl);
      assert.deepEqual(v, { ok: false, reason: "not-configured" });
    }
  });

  it("refuses every malformed, forged, misdirected or expired token", async () => {
    resetAccessKeys();
    const k = await accessKit("gamma-team.cloudflareaccess.com");
    const reason = async (t: string, host = "ecdysis.me") => {
      const v = await verifyAccess(req(t, host), k.config, k.fetchImpl);
      return v.ok ? "ADMITTED" : v.reason;
    };
    const now = Math.floor(Date.now() / 1000);
    assert.equal(await reason(await k.token(), "api.ecdysis.me"), "wrong-host");
    assert.equal(await reason("not.a.jwt!"), "malformed");
    assert.equal(await reason("abc.def"), "malformed");
    assert.equal(await reason(await k.token({}, { alg: "none" })), "bad-algorithm");
    assert.equal(await reason(await k.token({}, { alg: "HS256" })), "bad-algorithm");
    assert.equal(await reason(await k.token({ aud: ["someone-elses-app"] })), "wrong-audience");
    assert.equal(await reason(await k.token({ iss: "https://evil.cloudflareaccess.com" })), "wrong-issuer");
    // Access signs "meta" tokens too, and they travel in public login redirects.
    assert.equal(await reason(await k.token({ type: "meta", email: undefined })), "wrong-type");
    assert.equal(await reason(await k.token({ exp: now - 3600 })), "expired");
    assert.equal(await reason(await k.token({ nbf: now + 3600 })), "not-yet-valid");
    assert.equal(await reason(await k.token({ email: undefined })), "no-email");
    assert.equal(await reason(await k.token({ email: "someone@else.com" })), "not-allowed");

    // A valid token with its claims edited no longer verifies.
    const [h, , s] = (await k.token()).split(".");
    const forgedClaims = k.b64url(JSON.stringify({ aud: [AUD], email: "daniel@hulme.ai", exp: now + 3600, iss: "https://gamma-team.cloudflareaccess.com", type: "app" }));
    assert.equal(await reason(`${h}.${forgedClaims}.${s}`), "bad-signature");

    // A key the team never published, even claiming the team's key id.
    const rogue = (await crypto.subtle.generateKey(
      { name: "RSASSA-PKCS1-v1_5", modulusLength: 2048, publicExponent: new Uint8Array([1, 0, 1]), hash: "SHA-256" }, true, ["sign", "verify"],
    )) as CryptoKeyPair;
    assert.equal(await reason(await k.token({}, {}, rogue.privateKey)), "bad-signature");
  });

  it("refetches keys once for an unknown key id, without hammering the endpoint", async () => {
    resetAccessKeys();
    const k = await accessKit("delta-team.cloudflareaccess.com");
    assert.ok((await verifyAccess(req(await k.token()), k.config, k.fetchImpl)).ok);
    assert.equal(k.certsFetches, 1, "keys are cached");
    assert.ok((await verifyAccess(req(await k.token()), k.config, k.fetchImpl)).ok);
    assert.equal(k.certsFetches, 1);
    const unknown = await verifyAccess(req(await k.token({}, { kid: "rotated" })), k.config, k.fetchImpl);
    assert.deepEqual(unknown, { ok: false, reason: "unknown-key" });
    await verifyAccess(req(await k.token({}, { kid: "rotated" })), k.config, k.fetchImpl);
    assert.ok(k.certsFetches <= 2, "at most one refetch inside the guard window");
  });

  it("refuses when the team's keys can't be fetched", async () => {
    resetAccessKeys();
    const k = await accessKit("epsilon-team.cloudflareaccess.com");
    k.setCertsUp(false);
    assert.deepEqual(await verifyAccess(req(await k.token()), k.config, k.fetchImpl), { ok: false, reason: "certs-unavailable" });
  });

  it("binds the anti-forgery token to the sign-in", async () => {
    const a = await csrfFor("token-one");
    assert.equal(a, await csrfFor("token-one"));
    assert.notEqual(a, await csrfFor("token-two"));
    assert.match(a, /^[0-9a-f]{40}$/);
  });
});
