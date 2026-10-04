/**
 * Trigger-URL doorbells and Standard Webhooks signatures.
 *
 * Guarantees tested here: a person can paste the trigger URL of an
 * automation from a known service (Zapier, Make, n8n Cloud, Pipedream,
 * Power Automate, Apps Script, IFTTT) and nothing else, so a pasted URL
 * can't point Ecdysis at a private network, a look-alike host or Ecdysis
 * itself; the URL is kept only after it took a ring, sealed, and erased
 * when the doorbell changes or stops; no redirect is ever followed, and the
 * one accepted (Apps Script's 302 to its own echo) is never fetched; every
 * delivery to a webhook or a trigger carries Standard Webhooks headers
 * whose v1 signature matches the spec's own test vector and whose v1a
 * signature verifies with the log key; and the body is Ecdysis's own data.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { Doorbells, type DoorbellOptions } from "../src/api/doorbells.js";
import { MemoryStore } from "../src/store/memory-store.js";
import { EcdysisService } from "../src/api/service.js";
import { generateKeyPair, signJson, verifyJson, type KeyPairB64 } from "../src/core/crypto.js";
import { CONSTITUTION_VERSION, constitutionHash } from "../src/core/constitution.js";
import { structuralScreener } from "../src/core/hazard.js";
import type { Json } from "../src/core/canonical.js";
import { fireUrlCheck } from "../src/core/wake.js";
import { newSecret, secretBytes, signV1, standardHeaders, verifyDelivery, whpk } from "../src/core/webhooks.js";

const T0 = Date.UTC(2026, 9, 2, 9, 0, 0);
const HOUR = 3600 * 1000;
const DAY = 24 * HOUR;
const iso = (ms: number) => new Date(ms).toISOString().replace(/\.\d{3}Z$/, "Z");
const LINK = /https:\/\/ecdysis\.me\/doorbell\/([0-9a-f]{32})\/([0-9a-f]{64})/;
const ZAP = "https://hooks.zapier.com/hooks/catch/1234567/abcdef1/";
const GAS = "https://script.google.com/macros/s/AKfycbx_abcdefghijklmnopqrstuvwxyz0123456789/exec";

interface Call { url: string; headers: Record<string, string>; body: string; redirect?: string }

async function world() {
  let now = T0;
  const store = new MemoryStore();
  const log = await generateKeyPair();
  const calls: Call[] = [];
  let handler: (url: string, body: string) => Response = () => new Response("{}", { status: 200 });
  const fetchImpl = (async (input: RequestInfo | URL, init?: RequestInit) => {
    const headers: Record<string, string> = {};
    new Headers(init?.headers).forEach((v, k) => { headers[k] = v; });
    const body = String(init?.body ?? "");
    calls.push({ url: String(input), headers, body, redirect: init?.redirect });
    return handler(String(input), body);
  }) as typeof fetch;
  let n = 11;
  const random = () => ((n++ * 2654435761) % 4294967296) / 4294967296;
  const make = (over: Partial<DoorbellOptions> = {}) => new Doorbells({
    store, siteBase: "https://ecdysis.me", apiBase: "https://api.ecdysis.me", sthPrivateKey: log.privateKey,
    sealSecret: null, readOnly: false, fetchImpl, now: () => new Date(now), random, v2: true, ...over,
  });
  const svc = new EcdysisService({ store, screeners: [structuralScreener()], sthPrivateKey: log.privateKey, now: () => new Date(now) });
  const ack = { version: CONSTITUTION_VERSION, hash: await constitutionHash() };
  const keys = new Map<string, KeyPairB64>();
  const add = async (handle: string) => {
    const kp = await generateKeyPair();
    assert.equal((await svc.registerAgent({ handle, publicKey: kp.publicKey, operatorId: `op-${handle}`, constitution: ack })).status, 201);
    keys.set(handle, kp);
  };
  const signed = async (handle: string, extra: Record<string, Json>) => {
    const kp = keys.get(handle)!;
    const payload = { protocol: "ecdysis/0.2", agent: { handle, publicKey: kp.publicKey }, ts: iso(now), ...extra } as Json;
    return { payload, signature: await signJson(kp.privateKey, payload) } as Json;
  };
  return {
    store, log, calls, add, signed, make, bells: make(),
    on(h: (url: string, body: string) => Response) { handler = h; },
    tick(ms: number) { now += ms; },
    get now() { return now; },
  };
}
type World = Awaited<ReturnType<typeof world>>;

async function pending(w: World, handle: string, kind = "fire-url") {
  await w.add(handle);
  const r = await w.bells.request(await w.signed(handle, { type: "doorbell.set", kind }));
  assert.equal(r.status, 202, JSON.stringify(r.body));
  const [, id, token] = String((r.body as Record<string, Json>)["for_your_person"]).match(LINK)!;
  return { id: id!, token: token! };
}

const fire = (w: World, id: string, token: string, url: string, platform = "other") =>
  w.bells.page(id, token, "POST", new URLSearchParams({ action: "fire", url, platform }));

describe("Standard Webhooks", () => {
  it("signs v1 exactly as the specification's own test vector", async () => {
    const sig = await signV1("whsec_C2FVsBQIhrscChlQIMV+b5sSYspob7oD", "msg_27UH4WbU6Z5A5EzD8u03UvzRbpk", 1649367553, '{"email":"test@example.com","username":"test_user"}');
    assert.equal(sig, "v1,tZ1I4/hDygAJgO5TYxiSd6Sd0kDW6hPenDe+bTa3Kkw=");
  });

  it("makes secrets of 32 bytes, refuses short or malformed ones, and lists v1 then v1a", async () => {
    const s = newSecret();
    assert.match(s, /^whsec_[A-Za-z0-9+/]+=*$/);
    assert.equal(secretBytes(s)!.length, 32);
    assert.equal(secretBytes("whsec_" + btoa("short")), null);
    assert.equal(secretBytes("sk_live_abc"), null);
    const log = await generateKeyPair();
    const h = await standardHeaders({ id: "msg_abc", timestamp: 1700000000, body: "{}", secret: s, logKeyPkcs8: log.privateKey });
    const [v1, v1a] = h["webhook-signature"]!.split(" ");
    assert.match(v1!, /^v1,/);
    assert.match(v1a!, /^v1a,/);
    assert.ok(await verifyDelivery({ headers: h, body: "{}", nowS: 1700000100, secret: s }), "v1 verifies with the secret");
    assert.ok(await verifyDelivery({ headers: h, body: "{}", nowS: 1700000100, publicKeySpkiB64url: log.publicKey }), "v1a verifies with the log key alone");
    assert.ok(!(await verifyDelivery({ headers: h, body: "{} ", nowS: 1700000100, secret: s })), "one byte more and it fails");
    assert.ok(!(await verifyDelivery({ headers: h, body: "{}", nowS: 1700000400, secret: s })), "more than five minutes late");
    assert.ok(!(await verifyDelivery({ headers: h, body: "{}", nowS: 1700000100, secret: newSecret() })), "another secret");
    await assert.rejects(standardHeaders({ id: "msg.with.dots", timestamp: 1, body: "{}", secret: s }), /webhook-id/);
    assert.match(whpk(log.publicKey)!, /^whpk_[A-Za-z0-9+/]{43}=$/, "the log key as a raw 32-byte whpk_ key");
  });
});

describe("trigger URLs", () => {
  it("accept each known service's trigger and refuse everything else", () => {
    for (const ok of [
      ZAP, "https://hooks.zapier.com/hooks/catch/1234567/abcdef1",
      "https://hook.eu1.make.com/abcdefghij1234567890",
      "https://myteam.app.n8n.cloud/webhook/5f1c2d3e-aaaa-bbbb-cccc-1234567890ab",
      "https://eo1a2b3c4d5e6f7.m.pipedream.net",
      "https://prod-27.westus.logic.azure.com:443/workflows/0123456789abcdef0123456789abcdef/triggers/manual/paths/invoke?api-version=2016-06-01&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=abc",
      "https://default0123456789abcdef.01.environment.api.powerplatform.com:443/powerautomate/automations/direct/workflows/0123456789abcdef0123456789abcdef/triggers/manual/paths/invoke?api-version=1&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=xyz",
      GAS, "https://maker.ifttt.com/trigger/ecdysis_wake/with/key/abcdefghijklmnop",
    ]) {
      const c = fireUrlCheck(ok);
      assert.ok(c.ok, `${ok}: ${c.ok ? "" : c.problem}`);
      if (c.ok) assert.ok(!c.url.includes(":443"), "normalised without the port");
    }
    for (const bad of [
      "http://hooks.zapier.com/hooks/catch/1/a/", "https://hooks.zapier.com.evil.example/hooks/catch/1/a/", "https://evilhooks.zapier.com/hooks/catch/1/a/",
      "https://hooks.zapier.com/admin", "https://user:pw@hooks.zapier.com/hooks/catch/1/a/", "https://hooks.zapier.com:8443/hooks/catch/1/a/",
      "https://hooks.zapier.com/hooks/catch/1/a/#x", "https://script.google.com/macros/s/AKfycbx_abcdefghijklmnopqrstuvwxyz0123456789/dev",
      "https://script.googleusercontent.com/macros/echo?user_content_key=x", "https://127.0.0.1/hook", "https://localhost/hook",
      "https://api.ecdysis.me/v2/agents/doorbell", "https://example.com/webhook", "https://169.254.169.254/latest/meta-data",
      "https://myteam.app.n8n.cloud/webhook-test/abc", "https://x.logic.azure.com/workflows/abc/triggers/manual/paths/invoke", "not a url", "", "https://hook.eu1.make.com/short",
    ]) assert.ok(!fireUrlCheck(bad).ok, `refused: ${bad}`);
  });

  it("are kept only after they took a signed ring, sealed, with a secret shown once that verifies the next ring", async () => {
    const w = await world();
    const { id, token } = await pending(w, "Zap-1");
    // A URL Ecdysis doesn't ring: refused before anything is sent.
    const bad = await fire(w, id, token, "https://internal.example.org/hook");
    assert.equal(bad.status, 422);
    assert.equal(w.calls.length, 0);
    // The trigger fails: nothing kept.
    w.on(() => new Response("down", { status: 500 }));
    const failed = await fire(w, id, token, ZAP);
    assert.match(failed.html, /Nothing was kept/);
    assert.equal((await w.store.getDoorbell("Zap-1"))!.status, "pending");
    assert.equal((await w.store.getDoorbell("Zap-1"))!.targetSealed, null);
    // It works.
    w.calls.length = 0;
    w.on(() => new Response('{"status":"success"}', { status: 200 }));
    const ok = await fire(w, id, token, ZAP, "chatgpt");
    assert.equal(ok.status, 200, ok.html.slice(0, 1200));
    const secret = ok.html.match(/whsec_[A-Za-z0-9+/]+=*/)![0];
    assert.match(ok.html, /it isn&#39;t shown again/);
    assert.equal(w.calls.length, 1);
    const c = w.calls[0]!;
    assert.equal(c.url, ZAP);
    assert.equal(c.redirect, "manual", "never follows a redirect");
    const body = JSON.parse(c.body) as Record<string, Json>;
    assert.equal(body["event"], "ecdysis.wake");
    assert.equal(body["agent"], "Zap-1");
    assert.equal(body["heartbeat"], "https://api.ecdysis.me/v2/heartbeat?agent=Zap-1");
    assert.ok(await verifyJson(w.log.publicKey, body["payload"]!, String(body["signature"])), "the ring inside verifies with the log key");
    assert.ok(await verifyDelivery({ headers: c.headers, body: c.body, nowS: Math.floor(w.now / 1000), secret }), "v1 verifies with the secret shown");
    assert.ok(await verifyDelivery({ headers: c.headers, body: c.body, nowS: Math.floor(w.now / 1000), publicKeySpkiB64url: w.log.publicKey }), "v1a verifies with the log key");
    assert.equal(c.headers["webhook-id"], `msg_${(body["payload"] as Record<string, Json>)["id"]}`);
    // Kept sealed: the URL and the secret never appear in the clear.
    const d = (await w.store.getDoorbell("Zap-1"))!;
    assert.equal(d.kind, "fire-url");
    assert.equal(d.status, "active");
    assert.ok(!JSON.stringify(d).includes("hooks/catch"), "the URL is sealed");
    assert.ok(!JSON.stringify(d).includes(secret.slice(6, 30)), "the secret is sealed");
    assert.equal(d.settings!.host, "hooks.zapier.com");
    assert.equal(d.settings!.service, "Zapier");
    // The page names the host, never the URL, and never shows the secret again.
    const again = await w.bells.page(id, token, "GET", null);
    assert.match(again.html, /a trigger URL at hooks\.zapier\.com \(Zapier\)/);
    assert.ok(!again.html.includes("abcdef1/"));
    assert.ok(!again.html.includes(secret));
    // The sweep rings it, signed under the same secret.
    w.calls.length = 0;
    w.tick(DAY + HOUR);
    await w.bells.notify();
    assert.equal(w.calls.length, 1);
    assert.ok(await verifyDelivery({ headers: w.calls[0]!.headers, body: w.calls[0]!.body, nowS: Math.floor(w.now / 1000), secret }));
  });

  it("take Apps Script's redirect to its own echo as delivered, without following it, and no other redirect", async () => {
    const w = await world();
    const { id, token } = await pending(w, "Gas-1");
    w.on((url) => (url === GAS ? new Response(null, { status: 302, headers: { location: "https://evil.example/collect" } }) : new Response("", { status: 404 })));
    const wrong = await fire(w, id, token, GAS, "gemini");
    assert.match(wrong.html, /unexpected redirect/);
    assert.equal(w.calls.length, 1, "the redirect was not followed");
    w.calls.length = 0;
    w.on((url) => (url === GAS ? new Response(null, { status: 302, headers: { location: "https://script.googleusercontent.com/macros/echo?user_content_key=AbC-123_x&lib=Mxyz" } }) : new Response("", { status: 404 })));
    const ok = await fire(w, id, token, GAS, "gemini");
    assert.equal(ok.status, 200, ok.html.slice(0, 800));
    assert.equal(w.calls.length, 1, "the echo is never fetched");
    assert.equal((await w.store.getDoorbell("Gas-1"))!.status, "active");
    // Zapier redirecting is a failure: only Google's echo is accepted, and only from script.google.com.
    const z = await pending(w, "Zap-2");
    w.on(() => new Response(null, { status: 302, headers: { location: "https://script.googleusercontent.com/macros/echo?user_content_key=x" } }));
    assert.match((await fire(w, z.id, z.token, ZAP)).html, /redirected \(302\)/);
  });

  it("forget the URL and its secret when the doorbell switches or stops", async () => {
    const w = await world();
    const { id, token } = await pending(w, "Zap-3");
    assert.equal((await fire(w, id, token, ZAP)).status, 200);
    await w.bells.page(id, token, "POST", new URLSearchParams({ action: "self", platform: "other" }));
    let d = (await w.store.getDoorbell("Zap-3"))!;
    assert.equal(d.kind, "self");
    assert.equal(d.targetSealed, null);
    assert.equal(d.settings!.signing ?? null, null);
    assert.equal(d.settings!.host ?? null, null);
    assert.equal((await fire(w, id, token, ZAP)).status, 200);
    await w.bells.page(id, token, "POST", new URLSearchParams({ action: "stop" }));
    d = (await w.store.getDoorbell("Zap-3"))!;
    assert.equal(d.status, "stopped");
    assert.equal(d.targetSealed, null);
    assert.equal(d.settings!.signing, null);
  });

  it("are offered on the page to the apps that can use one, with the services named", async () => {
    const w = await world();
    const { id, token } = await pending(w, "Zap-4", "claude-routine");
    for (const p of ["chatgpt", "gemini", "copilot", "code", "other"]) {
      const page = await w.bells.page(id, token, "GET", null, new URLSearchParams({ for: p }));
      assert.match(page.html, /name="action" value="fire"/, `${p} offers a trigger URL`);
      assert.match(page.html, /Zapier, Make, n8n, Pipedream, Power Automate/);
    }
    const grok = await w.bells.page(id, token, "GET", null, new URLSearchParams({ for: "grok" }));
    assert.doesNotMatch(grok.html, /name="action" value="fire"/, "Grok's own automations have no inbound trigger");
  });
});

describe("webhooks sign with Standard Webhooks too", () => {
  it("get a shared secret at set-up, shown once, and every request after carries v1 and v1a", async () => {
    const w = await world();
    await w.add("Hook-1");
    w.on((url, body) => new Response(body, { status: 200 })); // echoes the challenge
    const r = await w.bells.request(await w.signed("Hook-1", { type: "doorbell.set", kind: "webhook", url: "https://agent.example.org/ring" }));
    assert.equal(r.status, 200, JSON.stringify(r.body));
    const secret = String((r.body as Record<string, Json>)["signing_secret"]);
    assert.match(secret, /^whsec_/);
    const verify = w.calls[0]!;
    assert.ok(await verifyDelivery({ headers: verify.headers, body: verify.body, nowS: Math.floor(w.now / 1000), secret }), "the challenge itself is signed with the secret it brings");
    w.calls.length = 0;
    w.tick(DAY + HOUR);
    await w.bells.notify();
    const ring = w.calls[0]!;
    assert.ok(await verifyDelivery({ headers: ring.headers, body: ring.body, nowS: Math.floor(w.now / 1000), secret }));
    assert.ok(await verifyDelivery({ headers: ring.headers, body: ring.body, nowS: Math.floor(w.now / 1000), publicKeySpkiB64url: w.log.publicKey }));
    assert.ok(!JSON.stringify(await w.store.getDoorbell("Hook-1")).includes(secret.slice(6, 30)), "kept sealed");
  });
});

describe("trigger URLs and a stop pressed meanwhile", () => {
  it("keep nothing if the doorbell was stopped while the trigger was being rung", async () => {
    const w = await world();
    const { id, token } = await pending(w, "Zap-9");
    w.on(() => {
      // The person presses stop in another window while Ecdysis rings the trigger.
      void w.bells.page(id, token, "POST", new URLSearchParams({ action: "stop" }));
      return new Response("{}", { status: 200 });
    });
    const p = await fire(w, id, token, ZAP);
    // The stop's write lands before the trigger's answer is handled.
    await new Promise((r) => setTimeout(r, 0));
    const d = (await w.store.getDoorbell("Zap-9"))!;
    assert.equal(d.status, "stopped", p.html.slice(0, 300));
    assert.equal(d.targetSealed, null, "the URL was never kept over the stop");
  });
});
