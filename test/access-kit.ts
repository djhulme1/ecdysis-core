/**
 * Test kit: a stand-in Cloudflare Access team. It holds a real RS256 key,
 * serves its public half the way /cdn-cgi/access/certs does, and signs
 * tokens with whatever claims a test needs.
 */
import { sha256Hex, type AccessConfig } from "../src/api/access.js";

export const AUD = "99fb059aa0ff3e3a5da1bfa8a7aee965999dff834cc6a335637aae4310d2ddf0";
export const OPERATOR = "daniel@hulme.ai";

const b64url = (bytes: Uint8Array | ArrayBuffer | string): string => {
  const u8 = typeof bytes === "string" ? new TextEncoder().encode(bytes) : bytes instanceof Uint8Array ? bytes : new Uint8Array(bytes);
  let s = "";
  for (const b of u8) s += String.fromCharCode(b);
  return btoa(s).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
};

export async function accessKit(teamDomain: string) {
  const kp = (await crypto.subtle.generateKey(
    { name: "RSASSA-PKCS1-v1_5", modulusLength: 2048, publicExponent: new Uint8Array([1, 0, 1]), hash: "SHA-256" },
    true, ["sign", "verify"],
  )) as CryptoKeyPair;
  const jwk = await crypto.subtle.exportKey("jwk", kp.publicKey);
  const kid = `kid-${teamDomain.slice(0, 6)}`;
  let certsFetches = 0;
  let certsUp = true;
  const fetchImpl = (async (url: string | URL | Request) => {
    const u = String(url instanceof Request ? url.url : url);
    if (u !== `https://${teamDomain}/cdn-cgi/access/certs`) return new Response("no", { status: 404 });
    certsFetches += 1;
    if (!certsUp) return new Response("down", { status: 503 });
    return new Response(JSON.stringify({ keys: [{ ...jwk, kid, alg: "RS256", use: "sig" }], public_cert: {}, public_certs: [] }), {
      headers: { "content-type": "application/json" },
    });
  }) as typeof fetch;

  const config: AccessConfig = { teamDomain, aud: AUD, emailHashes: [await sha256Hex(OPERATOR)], host: "ecdysis.me" };

  async function token(claims: Record<string, unknown> = {}, header: Record<string, unknown> = {}, key: CryptoKey = kp.privateKey): Promise<string> {
    const now = Math.floor(Date.now() / 1000);
    const body = {
      aud: [AUD], email: OPERATOR, exp: now + 3600, iat: now, nbf: now, iss: `https://${teamDomain}`, type: "app",
      sub: "7a1c0de3-0000-4000-8000-000000000001", identity_nonce: "n", country: "GB", ...claims,
    };
    const data = `${b64url(JSON.stringify({ alg: "RS256", kid, typ: "JWT", ...header }))}.${b64url(JSON.stringify(body))}`;
    const sig = await crypto.subtle.sign("RSASSA-PKCS1-v1_5", key, new TextEncoder().encode(data));
    return `${data}.${b64url(sig)}`;
  }

  return {
    config, fetchImpl, token, kid,
    get certsFetches() { return certsFetches; },
    setCertsUp(up: boolean) { certsUp = up; },
    b64url,
  };
}
