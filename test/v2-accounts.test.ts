/**
 * Accounts for people (v2): magic links that work once, briefly, in one
 * browser; sessions; step-up; pairing codes that register an agent under the
 * person's operator id; rate limits; the steward role from configuration;
 * and /me end to end through Request objects. Nothing here touches a number.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { MemoryStore } from "../src/store/memory-store.js";
import { TransparencyLog } from "../src/core/log.js";
import { generateKeyPair } from "../src/core/crypto.js";
import { MemoryV2Store, V2Service } from "../src/api/v2/service.js";
import { Accounts, LINKS_PER_HOUR, MemoryAccountStore, PAIRING_ATTEMPTS_PER_HOUR, SIGNUPS_PER_HOUR } from "../src/api/v2/accounts.js";
import { MeHandler } from "../src/api/v2/me.js";
import { sha256Hex } from "../src/api/access.js";
import type { Json } from "../src/core/canonical.js";

const MIN = 60 * 1000;
const KEY = "ab".repeat(32);

function world(o: { key?: string | null; stewards?: string[]; send?: boolean } = {}) {
  const clock = { t: Date.UTC(2026, 9, 3, 9, 0, 0) };
  const now = () => new Date(clock.t);
  const sent: Array<{ to: string; text: string; subject: string }> = [];
  const store = new MemoryAccountStore();
  // A deterministic stand-in for the Worker's CSPRNG (xorshift32, high byte), so codes look like real ones.
  let seed = 0x9e3779b9;
  const randomBytes = (n: number) => { const b = new Uint8Array(n); for (let i = 0; i < n; i++) { seed ^= seed << 13; seed ^= seed >>> 17; seed ^= seed << 5; seed >>>= 0; b[i] = (seed >>> 24) & 0xff; } return b; };
  const accounts = new Accounts({
    store, key: o.key === undefined ? KEY : o.key,
    send: o.send === false ? null : async (m) => { sent.push({ to: m.to, text: m.text, subject: m.subject }); return { ok: true, id: `m${sent.length}` }; },
    from: "Ecdysis <accounts@notify.ecdysis.me>", replyTo: "replies@ecdysis.me", siteBase: "https://ecdysis.me",
    stewardEmailHashes: o.stewards ?? [], now, randomBytes,
  });
  const logStore = new MemoryStore();
  const log = new TransparencyLog(logStore, now);
  const v2store = new MemoryV2Store(() => (logStore as unknown as { log: Array<{ entry: { seq: number; ts: string; type: string }; payload: Json }> }).log.map((r) => ({ seq: r.entry.seq, ts: r.entry.ts, type: r.entry.type, payload: r.payload })));
  const v2 = new V2Service({ log, store: v2store, logPrivateKey: null, now, pairing: (code, ip) => accounts.consumePairing(code, ip) });
  const me = new MeHandler({ accounts, v2, secure: false });
  const tick = (ms: number) => { clock.t += ms; };
  const linkToken = () => { const m = sent.at(-1)!.text.match(/\/me\/login\?t=([A-Za-z0-9_-]+)/); return m![1]!; };
  /** Sign in as `email` from browser `b` and return the session cookie value. */
  const signIn = async (email: string, b = "browser-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", ip = "1.1.1.1") => {
    const r = await accounts.requestLink(email, ip, b);
    assert.ok(r.ok, JSON.stringify(r));
    const c = await accounts.completeLink(linkToken(), b, ip);
    assert.ok(c.ok, JSON.stringify(c));
    return c;
  };
  return { accounts, store, v2, me, now, tick, sent, linkToken, signIn, log };
}

describe("accounts (v2)", () => {
  it("are closed without a readable key", async () => {
    const w = world({ key: null });
    assert.equal(w.accounts.enabled(), false);
    const r = await w.accounts.requestLink("a@example.org", "1.1.1.1", null);
    assert.equal(r.ok, false);
    assert.equal((r as { status: number }).status, 503);
    const res = await w.me.handle(new Request("https://ecdysis.me/me"), "/me", "1.1.1.1");
    assert.equal(res.status, 503);
    assert.match(await res.text(), /aren't open yet/);
    assert.equal(world({ key: "not-hex" }).accounts.enabled(), false);
  });

  it("sign in by a magic link that works once, for 15 minutes, in the browser that asked; the account gets an opaque operator id", async () => {
    const w = world();
    const b = "browser-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
    const r = await w.accounts.requestLink("  Dan@Example.ORG ", "1.1.1.1", null);
    assert.ok(r.ok && r.sent);
    assert.equal(w.sent[0]!.to, "dan@example.org", "normalised");
    assert.match(w.sent[0]!.text, /works once, for 15 minutes/);
    const t = w.linkToken();
    const wrongBrowser = await w.accounts.completeLink(t, "browser-bbbbbbbbbbbbbbbbbbbbbbbbbbbbbb", "1.1.1.1");
    assert.equal(wrongBrowser.ok, false);
    assert.equal((wrongBrowser as { status: number }).status, 403);
    const c = await w.accounts.completeLink(t, r.browser, "1.1.1.1");
    assert.ok(c.ok);
    assert.ok(c.created);
    assert.match(c.account.operatorId, /^op_[0-9a-f]{24}$/);
    assert.equal(c.account.role, "member");
    const again = await w.accounts.completeLink(t, r.browser, "1.1.1.1");
    assert.equal(again.ok, false, "single use");
    assert.equal((again as { status: number }).status, 410);
    // The same address signs in to the same account; a link left too long expires.
    await w.accounts.requestLink("dan@example.org", "1.1.1.1", b);
    const t2 = w.linkToken();
    w.tick(16 * MIN);
    const late = await w.accounts.completeLink(t2, b, "1.1.1.1");
    assert.equal((late as { status: number }).status, 410);
    await w.accounts.requestLink("dan@example.org", "1.1.1.1", b);
    const c2 = await w.accounts.completeLink(w.linkToken(), b, "1.1.1.1");
    assert.ok(c2.ok && !c2.created && c2.account.id === c.account.id);
    // The database holds no readable address: a keyed hash and a seal that only the key opens.
    const row = w.store.accounts.get(c.account.id)!;
    assert.ok(!row.emailSealed.includes("example"));
    assert.equal(row.emailHash, await w.accounts.emailHash("dan@example.org"));
    assert.equal(await w.accounts.emailOf(row), "dan@example.org");
    assert.equal(await world({ key: "cd".repeat(32) }).accounts.unseal(row.emailSealed), null, "a different key opens nothing");
  });

  it("does not reveal whether an address has an account, and limits links and sign-ups", async () => {
    const w = world();
    const fresh = await w.accounts.requestLink("new@example.org", "1.1.1.1", null);
    await w.signIn("old@example.org");
    const known = await w.accounts.requestLink("old@example.org", "1.1.1.1", null);
    assert.deepEqual([fresh.ok, known.ok], [true, true], "the same answer either way");
    for (let i = 1; i < LINKS_PER_HOUR; i++) assert.ok((await w.accounts.requestLink("new@example.org", `9.9.9.${i}`, null)).ok);
    const over = await w.accounts.requestLink("new@example.org", "9.9.9.99", null);
    assert.equal((over as { status: number }).status, 429, "per address");
    for (let i = 0; i < LINKS_PER_HOUR; i++) assert.ok((await w.accounts.requestLink(`p${i}@example.org`, "5.5.5.5", null)).ok);
    assert.equal(((await w.accounts.requestLink("q@example.org", "5.5.5.5", null)) as { status: number }).status, 429, "per connection");
    w.tick(61 * MIN);
    assert.ok((await w.accounts.requestLink("q@example.org", "5.5.5.5", null)).ok, "an hour later");
    // Sign-ups per connection.
    const w2 = world();
    for (let i = 0; i < SIGNUPS_PER_HOUR; i++) await w2.signIn(`s${i}@example.org`, "browser-cccccccccccccccccccccccccccccc", "7.7.7.7");
    await w2.accounts.requestLink("s9@example.org", "7.7.7.7", "browser-cccccccccccccccccccccccccccccc");
    const r = await w2.accounts.completeLink(w2.linkToken(), "browser-cccccccccccccccccccccccccccccc", "7.7.7.7");
    assert.equal((r as { status: number }).status, 429);
  });

  it("sessions last 30 days, rotate on sign-in, end on sign-out, and carry a step-up window and an anti-forgery token", async () => {
    const w = world();
    const c = await w.signIn("dan@example.org");
    const s = await w.accounts.session(c.session);
    assert.ok(s && s.account.id === c.account.id);
    assert.equal(w.accounts.fresh(s!), true);
    assert.equal(await w.accounts.csrfOk(s!, await w.accounts.csrf(s!)), true);
    assert.equal(await w.accounts.csrfOk(s!, "0".repeat(40)), false);
    assert.equal(await w.accounts.csrfOk(s!, null), false);
    w.tick(11 * MIN);
    assert.equal(w.accounts.fresh((await w.accounts.session(c.session))!), false, "sensitive actions need a fresh sign-in");
    const c2 = await w.signIn("dan@example.org");
    assert.notEqual(c2.session, c.session, "a new cookie each sign-in");
    assert.ok(await w.accounts.session(c.session), "the old one still works until sign-out or expiry");
    await w.accounts.signOut((await w.accounts.session(c.session))!);
    assert.equal(await w.accounts.session(c.session), null);
    assert.ok(await w.accounts.session(c2.session));
    const c3 = await w.signIn("dan@example.org");
    await w.accounts.signOutEverywhere((await w.accounts.session(c3.session))!);
    assert.equal(await w.accounts.session(c2.session), null);
    assert.equal(await w.accounts.session(c3.session), null);
    const c4 = await w.signIn("dan@example.org");
    w.tick(31 * 24 * 60 * MIN);
    assert.equal(await w.accounts.session(c4.session), null, "expired");
    assert.equal(await w.accounts.session("garbage"), null);
  });

  it("pairing codes register an agent under the person's operator id, once, within a day, with guesses limited", async () => {
    const w = world();
    const c = await w.signIn("dan@example.org");
    const s = (await w.accounts.session(c.session))!;
    const code = await w.accounts.newPairingCode(s);
    assert.match(code, /^[a-z2-9]{5}-[a-z2-9]{5}-[a-z2-9]{5}$/);
    const kp = await generateKeyPair();
    const reg = await w.v2.registerAgent({ handle: "Moth", publicKey: kp.publicKey, pairing: code.toUpperCase() }, "1.1.1.1");
    assert.equal(reg.status, 201, JSON.stringify(reg.body));
    const body = reg.body as Record<string, Json>;
    assert.equal(body["operatorId"], c.account.operatorId);
    assert.equal(body["tier"], "account");
    const rec = await w.v2.record();
    assert.equal(rec.agents.get("Moth")!.operatorId, c.account.operatorId);
    assert.equal(rec.tiers.get(c.account.operatorId), "account", "the operator enters the record at the account tier");
    // Once.
    const kp2 = await generateKeyPair();
    assert.equal((await w.v2.registerAgent({ handle: "Moth2", publicKey: kp2.publicKey, pairing: code }, "1.1.1.1")).status, 404);
    // Nobody can claim an account's operator id without a code.
    assert.equal((await w.v2.registerAgent({ handle: "Thief", publicKey: kp2.publicKey, operatorId: c.account.operatorId }, "1.1.1.1")).status, 400);
    // With a code, the operator id is the code's.
    const code2 = await w.accounts.newPairingCode(s);
    assert.equal((await w.v2.registerAgent({ handle: "Moth2", publicKey: kp2.publicKey, pairing: code2, operatorId: "someone-else" }, "1.1.1.1")).status, 400);
    assert.equal((await w.v2.registerAgent({ handle: "Moth2", publicKey: kp2.publicKey, pairing: code2 }, "1.1.1.1")).status, 201, "pairing a second agent needs a second code");
    // Expiry and guessing.
    const code3 = await w.accounts.newPairingCode(s);
    w.tick(25 * 60 * MIN);
    assert.equal((await w.accounts.consumePairing(code3, "2.2.2.2") as { status: number }).status, 404, "expired");
    assert.equal((await w.accounts.consumePairing("nonsense", "2.2.2.2") as { status: number }).status, 400);
    for (let i = 0; i < PAIRING_ATTEMPTS_PER_HOUR; i++) assert.equal((await w.accounts.consumePairing("aaaaa-aaaaa-aaaaa", "3.3.3.3") as { status: number }).status, 404);
    assert.equal((await w.accounts.consumePairing("aaaaa-aaaaa-aaaaa", "3.3.3.3") as { status: number }).status, 429, "guesses are limited per connection");
    // Unverified registration still works without any account.
    const kp3 = await generateKeyPair();
    const un = await w.v2.registerAgent({ handle: "Loner", publicKey: kp3.publicKey, operatorId: "my-own-id" }, "1.1.1.1");
    assert.equal(un.status, 201);
    assert.equal((un.body as Record<string, Json>)["tier"], "unverified");
  });

  it("gives the steward role to the configured addresses and nobody else", async () => {
    const w = world({ stewards: [await sha256Hex("daniel@example.org")] });
    const d = await w.signIn("Daniel@Example.org");
    assert.equal(d.account.role, "steward");
    const o = await w.signIn("other@example.org", "browser-dddddddddddddddddddddddddddddd");
    assert.equal(o.account.role, "member");
  });

  it("/me end to end: sign in, pair, issue and revoke a check key with step-up, save interests, delete; the log keeps the operator id", async () => {
    const w = world();
    const ip = "1.1.1.1";
    const get = (path: string, cookies: Record<string, string> = {}) => w.me.handle(new Request(`https://ecdysis.me${path}`, { headers: { cookie: Object.entries(cookies).map(([k, v]) => `${k}=${v}`).join("; ") } }), path.split("?")[0]!, ip);
    const post = (path: string, form: Record<string, string | string[]>, cookies: Record<string, string> = {}) => {
      const p = new URLSearchParams();
      for (const [k, v] of Object.entries(form)) for (const x of Array.isArray(v) ? v : [v]) p.append(k, x);
      return w.me.handle(new Request(`https://ecdysis.me${path}`, { method: "POST", body: p.toString(), headers: { "content-type": "application/x-www-form-urlencoded", "content-length": String(p.toString().length), cookie: Object.entries(cookies).map(([k, v]) => `${k}=${v}`).join("; ") } }), path, ip);
    };
    const cookieOf = (res: Response, name: string) => { const c = res.headers.getSetCookie().find((x) => x.startsWith(`${name}=`)); return c ? decodeURIComponent(c.split(";")[0]!.slice(name.length + 1)) : null; };

    let res = await get("/me");
    assert.equal(res.status, 200);
    assert.match(await res.text(), /Email me a sign-in link/);
    assert.equal((await get("/me/pairing")).status, 401, "nothing personal without a session");

    res = await post("/me/login", { email: "dan@example.org" });
    assert.equal(res.status, 200);
    assert.match(await res.text(), /Check your email/);
    const b = cookieOf(res, "ecd_b")!;
    assert.ok(b, "the browser cookie is set with the request");
    assert.match(res.headers.getSetCookie()[0]!, /HttpOnly; SameSite=Lax/);
    res = await get(`/me/login?t=${w.linkToken()}`);
    assert.equal(res.status, 403, "the link needs the browser cookie");
    res = await get(`/me/login?t=${w.linkToken()}`, { ecd_b: b });
    assert.equal(res.status, 303);
    assert.equal(res.headers.get("location"), "/me");
    const s = cookieOf(res, "ecd_s")!;
    assert.ok(s);
    const cookies = { ecd_b: b, ecd_s: s };

    res = await get("/me", cookies);
    assert.equal(res.status, 200);
    let html = await res.text();
    assert.match(html, /Operator <code class="mono">op_/);
    assert.equal(res.headers.get("cache-control"), "no-store");
    assert.match(res.headers.get("x-robots-tag")!, /noindex/);
    const csrf = html.match(/name="csrf" value="([0-9a-f]{40})"/)![1]!;
    const operatorId = html.match(/op_[0-9a-f]{24}/)![0];

    assert.equal((await post("/me/pairing", {}, cookies)).status, 403, "a form without the token is refused");
    assert.equal((await post("/me/pairing", { csrf: "f".repeat(40) }, cookies)).status, 403);
    res = await post("/me/pairing", { csrf }, cookies);
    assert.equal(res.status, 200);
    const code = (await res.text()).match(/font-size:1.4rem">([a-z2-9]{5}-[a-z2-9]{5}-[a-z2-9]{5})</)![1]!;
    const kp = await generateKeyPair();
    assert.equal((await w.v2.registerAgent({ handle: "Moth", publicKey: kp.publicKey, pairing: code }, ip)).status, 201);

    res = await get("/me", cookies);
    html = await res.text();
    assert.match(html, /Moth/);
    res = await post("/me/keys/issue", { csrf, handle: "Moth", label: "lab box" }, cookies);
    html = await res.text();
    assert.equal(res.status, 200, html);
    const pub = html.match(/<pre class="mono">(MCowBQYDK2VwAyEA[A-Za-z0-9_-]+)<\/pre>/)![1]!;
    assert.match(html, /<pre class="mono">MC4CAQAwBQYDK2VwBCIEI/, "the private half is shown once");
    let rec = await w.v2.record();
    assert.deepEqual(rec.agents.get("Moth")!.checkKeys, [pub]);
    assert.equal((await w.store.prefs.size), 0);

    res = await post("/me/interests", { csrf, fields: ["math", "ml", "bogus"], topics: "random 3-SAT\n\nspiking networks", claims: "ecd:2610.3qjqtw#C1\nnot a ref" }, cookies);
    assert.equal(res.status, 303);
    const prefs = (await w.store.getPreferences((await w.accounts.session(s))!.account.id))!;
    assert.deepEqual(prefs.interests.fields, ["math", "ml"]);
    assert.deepEqual(prefs.interests.topics, ["random 3-SAT", "spiking networks"]);
    assert.deepEqual(prefs.interests.claims, ["ecd:2610.3qjqtw#C1"]);
    res = await post("/me/notifications", { csrf, digest: "weekly", alerts: ["check.owed", "nonsense"] }, cookies);
    assert.equal(res.status, 303);
    assert.deepEqual((await w.store.getPreferences(prefs === null ? "" : (await w.accounts.session(s))!.account.id))!.notifications, { digest: "weekly", alerts: ["check.owed"] });

    // Step-up: eleven minutes on, revoking asks for a fresh sign-in; interests do not.
    w.tick(11 * MIN);
    res = await post("/me/keys/revoke", { csrf, key: pub, compromisedAt: "2026-10-03T09:05:00Z" }, cookies);
    assert.equal(res.status, 401);
    assert.match(await res.text(), /Sign in again/);
    assert.equal((await post("/me/interests", { csrf, topics: "x" }, cookies)).status, 303);
    // Sign in again (same browser), then revoke.
    await post("/me/login", { email: "dan@example.org" }, cookies);
    res = await get(`/me/login?t=${w.linkToken()}`, cookies);
    const s2 = cookieOf(res, "ecd_s")!;
    const cookies2 = { ecd_b: b, ecd_s: s2 };
    const csrf2 = (await (await get("/me", cookies2)).text()).match(/name="csrf" value="([0-9a-f]{40})"/)![1]!;
    assert.notEqual(csrf2, csrf, "the token follows the session");
    res = await post("/me/keys/revoke", { csrf: csrf2, key: pub, compromisedAt: "2026-10-03T09:05:00Z" }, cookies2);
    assert.equal(res.status, 303, await res.text());
    rec = await w.v2.record();
    assert.deepEqual(rec.agents.get("Moth")!.checkKeys, []);
    assert.equal(rec.keys.get(pub)!.compromisedAt, "2026-10-03T09:05:00Z");
    // Another account cannot touch Moth's keys.
    const other = await w.signIn("other@example.org", "browser-eeeeeeeeeeeeeeeeeeeeeeeeeeeeee", "2.2.2.2");
    const oc = { ecd_b: "browser-eeeeeeeeeeeeeeeeeeeeeeeeeeeeee", ecd_s: other.session };
    const ocsrf = (await (await get("/me", oc)).text()).match(/name="csrf" value="([0-9a-f]{40})"/)![1]!;
    res = await post("/me/keys/revoke", { csrf: ocsrf, key: kp.publicKey }, oc);
    assert.equal(res.status, 403);
    res = await post("/me/keys/issue", { csrf: ocsrf, handle: "Moth" }, oc);
    assert.equal(res.status, 403);

    // Delete: the account goes, the operator id and the agent stay on the log.
    res = await post("/me/delete", { csrf: csrf2 }, cookies2);
    assert.equal(res.status, 400, "needs the confirmation");
    res = await post("/me/delete", { csrf: csrf2, confirm: "delete" }, cookies2);
    assert.equal(res.status, 200);
    assert.match(res.headers.getSetCookie()[0]!, /ecd_s=; .*Max-Age=0/);
    assert.equal(await w.accounts.session(s2), null);
    assert.equal(w.store.accounts.size, 1, "only the other account remains");
    rec = await w.v2.record();
    assert.equal(rec.agents.get("Moth")!.operatorId, operatorId, "the record is untouched");
  });

  it("read-only mode still signs people out but changes nothing", async () => {
    const w = world();
    const ro = new MeHandler({ accounts: w.accounts, v2: w.v2, secure: false, readOnly: true });
    const c = await w.signIn("dan@example.org");
    const s = (await w.accounts.session(c.session))!;
    const csrf = await w.accounts.csrf(s);
    const post = (path: string, form: Record<string, string>) => {
      const p = new URLSearchParams(form).toString();
      return ro.handle(new Request(`https://ecdysis.me${path}`, { method: "POST", body: p, headers: { "content-type": "application/x-www-form-urlencoded", "content-length": String(p.length), cookie: `ecd_s=${c.session}` } }), path, "1.1.1.1");
    };
    assert.equal((await post("/me/pairing", { csrf })).status, 503);
    assert.equal((await post("/me/login", { email: "x@example.org" })).status, 503);
    assert.equal((await post("/me/signout", { csrf })).status, 303);
    assert.equal(await w.accounts.session(c.session), null);
  });
});
