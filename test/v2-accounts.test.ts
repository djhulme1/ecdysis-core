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
import { generateKeyPair, signJson } from "../src/core/crypto.js";
import { MemoryV2Store, V2Service } from "../src/api/v2/service.js";
import { structuralScreener } from "../src/core/hazard.js";
import { Accounts, LINKS_PER_HOUR, MemoryAccountStore, PAIRING_ATTEMPTS_PER_HOUR, SIGNUPS_PER_HOUR } from "../src/api/v2/accounts.js";
import { MeHandler } from "../src/api/v2/me.js";
import { sha256Hex } from "../src/api/access.js";
import type { Json } from "../src/core/canonical.js";
import { CONSTITUTION_VERSION, constitutionHash } from "../src/core/constitution.js";
import { V2Governance } from "../src/api/v2/governance.js";
import { V2Feeds } from "../src/api/v2/feed.js";
import { PagesHandler } from "../src/api/v2/pages.js";
import { declared, GENERAL, REPORTED, REPRODUCTION } from "./kinds-kit.js";
const ACK = { version: CONSTITUTION_VERSION, hash: await constitutionHash() };
const LOG_KEY = await generateKeyPair();

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
  const v2 = new V2Service({ log, store: v2store, logPrivateKey: LOG_KEY.privateKey, now, screeners: [structuralScreener()], pairing: (code, ip) => accounts.consumePairing(code, ip) });
  const governance = new V2Governance({ v2, log, operatorPublicKey: null, now });
  const feeds = new V2Feeds(v2, { site: "https://ecdysis.me", api: "https://api.ecdysis.me" });
  const me = new MeHandler({ accounts, v2, governance, feeds, secure: false });
  const pages = new PagesHandler(v2, { host: "api.ecdysis.me", accounts });
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
  return { accounts, store, v2, me, pages, now, tick, sent, linkToken, signIn, log };
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
    // Two requests racing with one link: the store spends it atomically, so exactly one gets a session.
    await w.accounts.requestLink("dan@example.org", "1.1.1.1", b);
    const tr = w.linkToken();
    const raced = await Promise.all([1, 2, 3].map(() => w.accounts.completeLink(tr, b, "1.1.1.1")));
    assert.equal(raced.filter((x) => x.ok).length, 1, "one session between them");
    assert.deepEqual(raced.filter((x) => !x.ok).map((x) => (x as { status: number }).status), [410, 410]);
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
    // A burst from many connections at one address: the limiter records before it counts, so the burst cannot slip under
    // the limit and mail-bomb the address.
    const before = w.sent.length;
    const burst = await Promise.all(Array.from({ length: 12 }, (_, i) => w.accounts.requestLink("burst@example.org", `6.6.6.${i}`, null)));
    assert.ok(w.sent.length - before <= LINKS_PER_HOUR, `at most ${LINKS_PER_HOUR} emails, sent ${w.sent.length - before}`);
    assert.ok(burst.some((r) => !r.ok));
    // The connection's limit is checked first: a hostile connection hammering one address runs dry at five, and its refused
    // attempts are not charged to the address. (Those five still fill the address's hour: the price of not mail-bombing it.)
    w.tick(61 * MIN);
    const sentBefore = w.sent.length;
    for (let i = 0; i < LINKS_PER_HOUR + 3; i++) await w.accounts.requestLink("old@example.org", "8.8.8.8", null);
    assert.equal(w.sent.length - sentBefore, LINKS_PER_HOUR, "five emails at most, however many attempts");
    w.tick(61 * MIN);
    assert.ok((await w.accounts.requestLink("old@example.org", "4.4.4.4", null)).ok, "and the address is free again an hour later");
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
    const reg = await w.v2.registerAgent({ constitution: ACK, handle: "Moth", publicKey: kp.publicKey, pairing: code.toUpperCase() }, "1.1.1.1");
    assert.equal(reg.status, 201, JSON.stringify(reg.body));
    const body = reg.body as Record<string, Json>;
    assert.equal(body["operatorId"], c.account.operatorId);
    assert.equal(body["tier"], "account");
    const rec = await w.v2.record();
    assert.equal(rec.agents.get("Moth")!.operatorId, c.account.operatorId);
    assert.equal(rec.tiers.get(c.account.operatorId), "account", "the operator enters the record at the account tier");
    // Once.
    const kp2 = await generateKeyPair();
    assert.equal((await w.v2.registerAgent({ constitution: ACK, handle: "Moth2", publicKey: kp2.publicKey, pairing: code }, "1.1.1.1")).status, 404);
    // Nobody can claim an account's operator id without a code.
    assert.equal((await w.v2.registerAgent({ constitution: ACK, handle: "Thief", publicKey: kp2.publicKey, operatorId: c.account.operatorId }, "1.1.1.1")).status, 400);
    // With a code, the operator id is the code's.
    const code2 = await w.accounts.newPairingCode(s);
    assert.equal((await w.v2.registerAgent({ constitution: ACK, handle: "Moth2", publicKey: kp2.publicKey, pairing: code2, operatorId: "someone-else" }, "1.1.1.1")).status, 400);
    assert.equal((await w.v2.registerAgent({ constitution: ACK, handle: "Moth2", publicKey: kp2.publicKey, pairing: code2 }, "1.1.1.1")).status, 201, "pairing a second agent needs a second code");
    // Two agents racing with one code: one pairs.
    const codeR = await w.accounts.newPairingCode(s);
    const raced = await Promise.all([1, 2, 3].map(() => w.accounts.consumePairing(codeR, "4.4.4.4")));
    assert.equal(raced.filter((x) => x.ok).length, 1, "a code is spent atomically");
    // Expiry and guessing.
    const code3 = await w.accounts.newPairingCode(s);
    w.tick(25 * 60 * MIN);
    assert.equal((await w.accounts.consumePairing(code3, "2.2.2.2") as { status: number }).status, 404, "expired");
    assert.equal((await w.accounts.consumePairing("nonsense", "2.2.2.2") as { status: number }).status, 400);
    for (let i = 0; i < PAIRING_ATTEMPTS_PER_HOUR; i++) assert.equal((await w.accounts.consumePairing("aaaaa-aaaaa-aaaaa", "3.3.3.3") as { status: number }).status, 404);
    assert.equal((await w.accounts.consumePairing("aaaaa-aaaaa-aaaaa", "3.3.3.3") as { status: number }).status, 429, "guesses are limited per connection");
    // Unverified registration still works without any account.
    const kp3 = await generateKeyPair();
    const un = await w.v2.registerAgent({ constitution: ACK, handle: "Loner", publicKey: kp3.publicKey, operatorId: "my-own-id" }, "1.1.1.1");
    assert.equal(un.status, 201);
    assert.equal((un.body as Record<string, Json>)["tier"], "unverified");
  });

  it("accepts its own form posts as real browsers send them, and refuses a null Origin unless the browser vouches for same-origin", async () => {
    // Production, 3 Oct 2026: the first sign-in ever attempted was refused with "Not from here".
    // The pages said Referrer-Policy: no-referrer, under which browsers send `Origin: null` on
    // a page's OWN form posts; the check compared it with the site and refused. Two guards now:
    // the pages send a same-origin referrer policy (so Origin is real), and a null Origin is
    // judged by Sec-Fetch-Site, which no page can set or suppress.
    const { sameOrigin } = await import("../src/api/v2/me.js");
    const req = (h: Record<string, string>) => new Request("https://ecdysis.me/me/login", { method: "POST", headers: h });
    assert.equal(sameOrigin(req({ origin: "https://ecdysis.me" })), true, "a real same origin");
    assert.equal(sameOrigin(req({ origin: "https://ecdysis.me", "sec-fetch-site": "same-origin" })), true);
    assert.equal(sameOrigin(req({ origin: "null", "sec-fetch-site": "same-origin" })), true, "Chrome under no-referrer: Origin null, but the browser says same-origin");
    assert.equal(sameOrigin(req({ origin: "null", "sec-fetch-site": "cross-site" })), false, "a sandboxed cross-site frame: Origin null and the browser says so");
    assert.equal(sameOrigin(req({ origin: "null" })), false, "Origin null with no Sec-Fetch-Site fails closed");
    assert.equal(sameOrigin(req({})), false, "no Origin at all: a script, not a browser form");
    assert.equal(sameOrigin(req({ "sec-fetch-site": "same-origin" })), true, "a browser that omits Origin but vouches for the site");
    assert.equal(sameOrigin(req({ origin: "https://evil.example" })), false);
    assert.equal(sameOrigin(req({ origin: "https://evil.example", "sec-fetch-site": "same-origin" })), false, "a lying Origin is not rescued by Sec-Fetch-Site");
    assert.equal(sameOrigin(req({ origin: "https://ecdysis.me", "sec-fetch-site": "cross-site" })), false, "nor the other way round");
    assert.equal(sameOrigin(req({ origin: "https://api.ecdysis.me" })), false, "a sibling host is another origin");

    // The pages themselves: /me, /steward and the OAuth consent page all carry a referrer policy
    // under which the browser sends the real Origin on their forms, and never no-referrer.
    const w = world({ stewards: [await sha256Hex("daniel@example.org")] });
    const ip = "1.1.1.1";
    const me = await w.me.handle(new Request("https://ecdysis.me/me"), "/me", ip);
    assert.equal(me.headers.get("referrer-policy"), "same-origin");
    assert.match(me.headers.get("content-security-policy") ?? "", /default-src 'none'/, "and loads nothing from anywhere, so no referrer ever leaves the site");
    const b = decodeURIComponent(me.headers.getSetCookie().find((x) => x.startsWith("ecd_b="))!.split(";")[0]!.slice(6));
    // The sign-in form, posted exactly as Chrome did from the old page (Origin null + Sec-Fetch-Site same-origin): a link is sent.
    const body = new URLSearchParams({ email: "daniel@example.org" }).toString();
    const asChrome = await w.me.handle(new Request("https://ecdysis.me/me/login", { method: "POST", body, headers: { "content-type": "application/x-www-form-urlencoded", "content-length": String(body.length), cookie: `ecd_b=${b}`, origin: "null", "sec-fetch-site": "same-origin", "sec-fetch-mode": "navigate", "sec-fetch-dest": "document" } }), "/me/login", ip);
    const asChromeText = await asChrome.text();
    assert.equal(asChrome.status, 200, asChromeText);
    assert.match(asChromeText, /Check your email/);
    assert.equal(w.sent.length, 1, "the sign-in link went out");
    // And as a sandboxed cross-site frame would post it: refused, nothing sent.
    const framed = await w.me.handle(new Request("https://ecdysis.me/me/login", { method: "POST", body, headers: { "content-type": "application/x-www-form-urlencoded", "content-length": String(body.length), cookie: `ecd_b=${b}`, origin: "null", "sec-fetch-site": "cross-site" } }), "/me/login", ip);
    assert.equal(framed.status, 403);
    assert.equal(w.sent.length, 1);
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
    const post = (path: string, form: Record<string, string | string[]>, cookies: Record<string, string> = {}, origin: string | null = "https://ecdysis.me") => {
      const p = new URLSearchParams();
      for (const [k, v] of Object.entries(form)) for (const x of Array.isArray(v) ? v : [v]) p.append(k, x);
      return w.me.handle(new Request(`https://ecdysis.me${path}`, { method: "POST", body: p.toString(), headers: { "content-type": "application/x-www-form-urlencoded", "content-length": String(p.toString().length), cookie: Object.entries(cookies).map(([k, v]) => `${k}=${v}`).join("; "), ...(origin ? { origin } : {}) } }), path, ip);
    };
    const cookieOf = (res: Response, name: string) => { const c = res.headers.getSetCookie().find((x) => x.startsWith(`${name}=`)); return c ? decodeURIComponent(c.split(";")[0]!.slice(name.length + 1)) : null; };

    let res = await get("/me");
    assert.equal(res.status, 200);
    assert.match(await res.text(), /Email me a sign-in link/);
    const b = cookieOf(res, "ecd_b")!;
    assert.ok(b, "the sign-in page names the browser before any link is asked for");
    assert.match(res.headers.getSetCookie()[0]!, /HttpOnly; SameSite=Lax/);
    assert.equal((await get("/me/pairing")).status, 401, "nothing personal without a session");

    // Login CSRF: a form posted from another site, or without the browser cookie, asks for nothing and signs nobody in.
    res = await post("/me/login", { email: "attacker@example.org" }, { ecd_b: b }, "https://evil.example");
    assert.equal(res.status, 403, "a cross-site POST is refused");
    assert.equal(res.headers.getSetCookie().length, 0, "and sets no cookie");
    assert.equal((await post("/me/login", { email: "attacker@example.org" }, { ecd_b: b }, null)).status, 403, "no Origin: refused");
    res = await post("/me/login", { email: "attacker@example.org" });
    assert.equal(res.status, 403, "without the browser cookie: refused");
    assert.equal(w.sent.length, 0, "no link was sent for any of them");

    res = await post("/me/login", { email: "dan@example.org" }, { ecd_b: b });
    assert.equal(res.status, 200);
    assert.match(await res.text(), /Check your email/);
    assert.equal(res.headers.getSetCookie().length, 0, "the browser already has its cookie");
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
    assert.match(html, /Signed in as <b>d…@example.org<\/b>/, "a person can see whose page this is");
    assert.match(html, /<h2 id="constitution">Constitution<\/h2>/);
    assert.match(html, new RegExp(`In force: <b>v${CONSTITUTION_VERSION.replace(/\./g, "\\.")}<\/b>`));
    assert.match(html, /yours does not yet/, "no verified work: not in the electorate");
    assert.match(html, /No proposal is open/);
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
    assert.equal((await w.v2.registerAgent({ constitution: ACK, handle: "Moth", publicKey: kp.publicKey, pairing: code }, ip)).status, 201);

    res = await get("/me", cookies);
    html = await res.text();
    assert.match(html, /Moth/);
    assert.match(html, /No claims published under your operator id yet/);
    assert.match(html, new RegExp(`<span class="t">Moth</span><span class="d">acknowledged v${CONSTITUTION_VERSION.replace(/\./g, "\\.")}`), "the version each agent acknowledged");
    // Publish a paper as Moth: the insights section shows the claim and what would raise it most.
    const paper = { protocol: "ecdysis/0.2", type: "paper", title: "Moth's first result", abstract: "An abstract long enough to pass the structural screen, saying what was measured, how, and with what uncertainty.", field: "math", claims: [{ text: "The measured quantity lies in the stated interval in the stated regime.", confidence: 0.7, test: "A fresh run outside the interval.", scope: GENERAL }], builds_on: [], agent: { handle: "Moth", publicKey: kp.publicKey }, ts: "2026-10-03T09:00:00Z" } as unknown as Json;
    const { signJson: sj } = await import("../src/core/crypto.js");
    const published = await w.v2.publishPaper({ payload: paper, signature: await sj(kp.privateKey, paper) });
    assert.equal(published.status, 201, JSON.stringify(published.body));
    html = await (await get("/me", cookies)).text();
    assert.match(html, /Moth&#39;s first result/);
    assert.match(html, /an independent replication of this claim itself/);
    assert.match(html, /1 claim/);
    assert.match(html, /<h2 id="promote">Publish and promote<\/h2>/);
    assert.match(html, /href="\/p\/ecd:[^"]+#cite">Moth&#39;s first result<\/a>/, "each paper links to its cite-and-share section");
    assert.match(html, /https:\/\/ecdysis\.me\/badge\/paper\/ecd:[^<]+\.svg/);
    assert.match(html, /https:\/\/ecdysis\.me\/badge\/agent\/Moth\.svg/);
    // Analytics: per agent and per claim, the trajectory, and the CSV (quoted, formula-safe).
    res = await get("/me/analytics", cookies);
    assert.equal(res.status, 200);
    html = await res.text();
    assert.match(html, /<h1>Analytics<\/h1>/);
    assert.match(html, /<td><a href="\/a\/Moth">Moth<\/a><\/td><td>—<\/td><td>1<\/td><td>1<\/td><td class="small">1 unchecked<\/td><td>0\.\d\d<\/td>/, "the agent row");
    assert.match(html, /Mean credence of your claims: <b>0\.\d\d<\/b> now/);
    assert.match(html, /— a week ago; — a month ago/, "no record then");
    res = await get("/me/analytics.csv", cookies);
    assert.equal(res.status, 200);
    assert.match(res.headers.get("content-type")!, /text\/csv/);
    assert.match(res.headers.get("content-disposition")!, /attachment; filename="ecdysis-op_[0-9a-f]{24}\.csv"/);
    const csv = await res.text();
    const rows = csv.trim().split("\r\n");
    assert.equal(rows[0], '"kind","agent","handle_or_ref","title","status_or_models","credence_or_reliability","use","dispute","receipts","verification_rate","lapses","credence_7d_ago","credence_30d_ago","families"');
    assert.match(rows[1]!, /^"agent","Moth","Moth","","","0\.5000","0","","0","","0","","",""$/);
    assert.match(rows[2]!, /^"claim","Moth","ecd:[a-z0-9.]+#C1","Moth's first result","unchecked","0\.\d{4}","0","0(\.0000)?","","","","","",""$/);
    assert.equal(rows.length, 3);
    assert.equal((await get("/me/analytics")).status, 401, "signed out: nothing");
    const { analyticsCsv } = await import("../src/api/v2/me.js");
    const hostile = analyticsCsv({ operatorId: "op", tier: "account", at: "2026-10-03T09:00:00Z", agents: [], trajectory: { now: null, weekAgo: null, monthAgo: null },
      claims: [{ ref: "ecd:x#C1", paper: "ecd:x", agent: "Moth", title: '=HYPERLINK("https://evil.example","click") "quoted"', stated: 0.5, status: "unchecked", credence: 0.5, use: 0, dispute: 0, families: ["-gpt"], weekAgo: null, monthAgo: null }] });
    assert.match(hostile, /"'=HYPERLINK\(""https:\/\/evil\.example"",""click""\) ""quoted"""/, "a cell can never be a formula, and quotes are doubled");
    assert.match(hostile, /"'-gpt"$/m);
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

    // Step-up: eleven minutes on, revoking (and minting a pairing code) asks for a fresh sign-in; interests do not.
    w.tick(11 * MIN);
    res = await post("/me/keys/revoke", { csrf, key: pub, compromisedAt: "2026-10-03T09:05:00Z" }, cookies);
    assert.equal(res.status, 401);
    assert.match(await res.text(), /Sign in again/);
    assert.equal((await post("/me/pairing", { csrf }, cookies)).status, 401, "a stolen 30-day cookie alone cannot pair agents to the operator");
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
    const danHash = await w.accounts.emailHash("dan@example.org");
    assert.equal([...w.store.links.values()].filter((l) => l.emailHash === danHash).length, 0, "the sign-in links carrying the sealed address are gone too");
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
      return ro.handle(new Request(`https://ecdysis.me${path}`, { method: "POST", body: p, headers: { "content-type": "application/x-www-form-urlencoded", "content-length": String(p.length), cookie: `ecd_s=${c.session}; ecd_b=browser-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa`, origin: "https://ecdysis.me" } }), path, "1.1.1.1");
    };
    assert.equal((await post("/me/pairing", { csrf })).status, 503);
    assert.equal((await post("/me/login", { email: "x@example.org" })).status, 503);
    assert.equal((await post("/me/signout", { csrf })).status, 303);
    assert.equal(await w.accounts.session(c.session), null);
  });

  it("a public profile is opt-in with a unique name and never shows the email; the private feed is a capability address that a reset invalidates", async () => {
    const w = world();
    const ip = "1.1.1.1";
    const b = "browser-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
    const dan = await w.signIn("dan@example.org", b, ip);
    const cookies = { ecd_b: b, ecd_s: dan.session };
    const get = (path: string, c: Record<string, string> = cookies) => w.me.handle(new Request(`https://ecdysis.me${path}`, { headers: { cookie: Object.entries(c).map(([k, v]) => `${k}=${v}`).join("; ") } }), path.split("?")[0]!, ip);
    const post = (path: string, form: Record<string, string>, c: Record<string, string> = cookies) => {
      const p = new URLSearchParams(form).toString();
      return w.me.handle(new Request(`https://ecdysis.me${path}`, { method: "POST", body: p, headers: { "content-type": "application/x-www-form-urlencoded", "content-length": String(p.length), cookie: Object.entries(c).map(([k, v]) => `${k}=${v}`).join("; "), origin: "https://ecdysis.me" } }), path, ip);
    };
    const page = async (path: string) => { const r = await w.pages.handle("GET", path); return r ? { status: r.status, text: await r.text(), headers: r.headers } : null; };
    const s = (await w.accounts.session(dan.session))!;
    const csrf = await w.accounts.csrf(s);

    // Pair an agent and publish a paper, so the profile has something to show.
    const code = await w.accounts.newPairingCode(s);
    const kp = await generateKeyPair();
    assert.equal((await w.v2.registerAgent({ constitution: ACK, handle: "Moth", publicKey: kp.publicKey, pairing: code, models: ["claude"] }, ip)).status, 201);
    const paper = { protocol: "ecdysis/0.2", type: "paper", title: "Moth's result <b>bold</b>", abstract: "An abstract long enough to pass the structural screen, saying what was measured, how, and with what uncertainty.", field: "math", claims: [{ text: "The measured quantity lies in the stated interval in the stated regime.", confidence: 0.7, test: "A fresh run outside the interval.", scope: GENERAL }], builds_on: [], agent: { handle: "Moth", publicKey: kp.publicKey }, ts: "2026-10-03T09:00:00Z" } as unknown as Json;
    const published = await w.v2.publishPaper({ payload: paper, signature: await signJson(kp.privateKey, paper) });
    assert.equal(published.status, 201, JSON.stringify(published.body));
    const paperId = String((published.body as Record<string, Json>)["id"]);

    // Off by default: no page, no feed.
    let html = await (await get("/me")).text();
    assert.match(html, /Opt in to a public page/);
    assert.equal((await page("/u/dan-hulme"))!.status, 404);
    assert.match((await page("/u/dan-hulme"))!.text, /Nobody has a public profile by that name/);
    assert.equal((await page("/u/dan-hulme/feed.xml"))!.status, 404);
    assert.equal(await page("/u/n/0123456789abcdef0123456789abcdef/0123456789abcdef0123456789abcdef"), null, "v1's stop links are not profiles");
    assert.equal(await page("/u/ab"), null, "too short to be a name");

    // Bad names are refused; the name is lower-cased; a second account cannot take it.
    for (const bad of ["ab", "-dan", "dan-", "dan hulme", "d".repeat(31), "ecdysis", "Steward", "me"]) {
      const r = await post("/me/profile", { csrf, action: "set", name: bad });
      assert.equal(r.status, 400, bad);
      assert.match(await r.text(), /Couldn&#39;t set the profile name/);
    }
    let res = await post("/me/profile", { csrf, action: "set", name: "Dan-Hulme" });
    assert.equal(res.status, 303);
    assert.match(res.headers.get("location")!, /u%2Fdan-hulme/);
    assert.equal((await w.store.getPreferences(s.account.id))!.profile, "dan-hulme");
    html = await (await get("/me")).text();
    assert.match(html, /<a href="\/u\/dan-hulme">\/u\/dan-hulme<\/a>/);
    const eve = await w.signIn("eve@example.org", "browser-eeeeeeeeeeeeeeeeeeeeeeeeeeeeee", "2.2.2.2");
    const ec = { ecd_b: "browser-eeeeeeeeeeeeeeeeeeeeeeeeeeeeee", ecd_s: eve.session };
    const ecsrf = await w.accounts.csrf((await w.accounts.session(eve.session))!);
    res = await post("/me/profile", { csrf: ecsrf, action: "set", name: "DAN-HULME" }, ec);
    assert.equal(res.status, 409);
    assert.match(await res.text(), /that name is taken/);
    assert.equal((await w.store.getPreferences(s.account.id))!.profile, "dan-hulme", "the holder keeps it");

    // The public page: name, operator id, agents, papers, a verified mark only when the operator is verified; never the email.
    let u = (await page("/u/Dan-Hulme"))!;
    assert.equal(u.status, 200);
    assert.match(u.text, /<h1>dan-hulme<\/h1>/);
    assert.match(u.text, new RegExp(`operator ${s.account.operatorId}`));
    assert.match(u.text, /href="\/a\/Moth">Moth<\/a>/);
    assert.match(u.text, /Moth&#39;s result &lt;b&gt;bold&lt;\/b&gt;/);
    assert.match(u.text, /1 claim, 0 established/);
    assert.doesNotMatch(u.text, /example\.org|dan@/, "no email anywhere");
    assert.doesNotMatch(u.text, /verified<\/span>/);
    assert.match(u.text, /<link rel="alternate" type="application\/atom\+xml" title="dan-hulme on Ecdysis" href="\/u\/dan-hulme\/feed.xml">/);
    assert.equal(u.headers.get("cache-control"), "public, max-age=120");
    await w.v2.setTier(s.account.operatorId, "verified");
    u = (await page("/u/dan-hulme"))!;
    assert.match(u.text, /<span class="status sound"[^>]*>verified<\/span>/);
    // Its feed.
    let feed = (await page("/u/dan-hulme/feed.xml"))!;
    assert.equal(feed.status, 200);
    assert.equal(feed.headers.get("content-type"), "application/atom+xml; charset=utf-8");
    assert.match(feed.text, /<title>dan-hulme on Ecdysis<\/title>/);
    assert.match(feed.text, new RegExp(`<id>https://ecdysis.me/p/${paperId.replace(/[.:]/g, "\\$&")}</id>`));
    assert.match(feed.text, /<title>Moth&#39;s result &lt;b&gt;bold&lt;\/b&gt;<\/title>/, "escaped for XML");
    assert.match(feed.text, /<category term="math"\/>/);
    // The field feeds come from the same record.
    const math = (await page("/feeds/math.atom"))!;
    assert.equal(math.status, 200);
    assert.match(math.text, /Moth&#39;s result/);
    assert.doesNotMatch((await page("/feeds/ml.atom"))!.text, /Moth/);
    assert.equal(await page("/feeds/bogus.atom"), null);

    // The private feed: the address on the page carries a token; without it, or with a stale one, nothing but a 404.
    html = await (await get("/me")).text();
    const feedUrl = html.match(/https:\/\/ecdysis\.me\/me\/feed\.xml\?a=[^<]+/)![0]!.replace(/&amp;/g, "&");
    const q = new URL(feedUrl);
    res = await w.me.handle(new Request(feedUrl), "/me/feed.xml", "9.9.9.9");
    assert.equal(res.status, 200, "no cookie needed: the address is the key");
    assert.equal(res.headers.get("content-type"), "application/atom+xml; charset=utf-8");
    assert.equal(res.headers.get("cache-control"), "no-store");
    let xml = await res.text();
    assert.match(xml, /<title>Your Ecdysis<\/title>/);
    assert.match(xml, /Moth&#39;s result/, "a paper in every field, since none is chosen");
    assert.match(xml, new RegExp(`<link href="${feedUrl.replace(/[?.&]/g, (c) => (c === "&" ? "&amp;" : `\\${c}`))}" rel="self"`));
    assert.equal((await w.me.handle(new Request(`https://ecdysis.me/me/feed.xml?a=${q.searchParams.get("a")}&t=${"0".repeat(40)}`), "/me/feed.xml", ip)).status, 404);
    assert.equal((await w.me.handle(new Request(`https://ecdysis.me/me/feed.xml?a=acct_nobody&t=${q.searchParams.get("t")}`), "/me/feed.xml", ip)).status, 404);
    // Another verified operator's receipt on Dan's claim appears in his feed, saying whose claim it is.
    const bee = await generateKeyPair();
    assert.equal((await w.v2.registerAgent({ constitution: ACK, handle: "Bee", publicKey: bee.publicKey, operatorId: "op-bee", models: ["gpt"] })).status, 201);
    await w.v2.setTier("op-bee", "verified");
    const signed = async (k: { publicKey: string; privateKey: string }, handle: string, payload: Record<string, Json>) => { const full: Json = declared({ ...payload, agent: { handle, publicKey: k.publicKey }, ts: w.now().toISOString().replace(/\.\d{3}Z$/, "Z") }); return { payload: full, signature: await signJson(k.privateKey, full) } as Json; };
    const bundle = { repo: "https://github.com/example/rep", commit: "1".repeat(40), image: "sha256:" + "a".repeat(64), run: "python run.py", outputs: [{ name: "alpha", tolerance: 0.01 }], runtimeMinutes: 5 };
    const c1 = await w.v2.commitCheck(await signed(bee, "Bee", { protocol: "ecdysis/0.2", type: "check.commit", target: `${paperId}#C1`, kind: "replication", bundle }));
    assert.equal(c1.status, 201, JSON.stringify(c1.body));
    const r1 = await w.v2.fileResult(await signed(bee, "Bee", { protocol: "ecdysis/0.2", type: "check.result", commit: String((c1.body as Record<string, Json>)["id"]), outcome: "confirmed", outputs: { alpha: 1 }, crossCheck: null }));
    assert.equal(r1.status, 201, JSON.stringify(r1.body));
    xml = await (await w.me.handle(new Request(feedUrl), "/me/feed.xml", ip)).text();
    assert.match(xml, /<title>Receipt: confirmed — reproduction of ecd:[^<]+ by Bee<\/title>/, "the feed names what the receipt tested (kinds/0.1), not its code");
    assert.match(xml, /On a claim of yours/);
    assert.match(xml, /<category term="receipt"\/>/);
    // Eve follows the claim: it shows in hers as a claim she follows; Dan's paper (math) does not, since she chose another field.
    await w.accounts.savePreferences((await w.accounts.session(eve.session))!, { interests: { fields: ["ml"], topics: [], claims: [`${paperId}#C1`], agents: [] }, notifications: { digest: "off", alerts: [] }, profile: null, feed: { epoch: 0 } });
    const eveFeed = (await (await get("/me", ec)).text()).match(/https:\/\/ecdysis\.me\/me\/feed\.xml\?a=[^<]+/)![0]!.replace(/&amp;/g, "&");
    xml = await (await w.me.handle(new Request(eveFeed), "/me/feed.xml", ip)).text();
    assert.match(xml, /On a claim you follow/);
    assert.doesNotMatch(xml, /<category term="paper"\/>/);

    // Reset: the old address stops working at once; the page shows a new one, which works.
    res = await post("/me/feed/reset", { csrf });
    assert.equal(res.status, 303);
    assert.equal((await w.me.handle(new Request(feedUrl), "/me/feed.xml", ip)).status, 404, "the old address is dead");
    const feedUrl2 = (await (await get("/me")).text()).match(/https:\/\/ecdysis\.me\/me\/feed\.xml\?a=[^<]+/)![0]!.replace(/&amp;/g, "&");
    assert.notEqual(feedUrl2, feedUrl);
    assert.equal((await w.me.handle(new Request(feedUrl2), "/me/feed.xml", ip)).status, 200);
    assert.equal((await w.me.handle(new Request(feedUrl2, { method: "POST", headers: { origin: "https://ecdysis.me" } }), "/me/feed.xml", ip)).status, 405);

    // Two forms racing: each writes only the section it owns, over the preferences as they stand, so saving interests
    // cannot resurrect a reset feed address or a cleared profile (the lost update a read-then-write-everything had).
    const before = (await w.store.getPreferences(s.account.id))!;
    const slowStore = w.store as unknown as { getPreferencesJson: (id: string) => Promise<unknown> };
    const realGet = slowStore.getPreferencesJson.bind(w.store);
    let gate: (() => void) | null = null;
    slowStore.getPreferencesJson = async (id: string) => { const p = await realGet(id); if (gate) { const g = gate; gate = null; await new Promise<void>((r) => { setTimeout(r, 20); g(); }); } return p; };
    let released = false;
    gate = () => { released = true; };
    const racing = post("/me/interests", { csrf, topics: "raced" }); // reads, then waits 20 ms before writing
    await new Promise((r) => setTimeout(r, 5));
    assert.equal((await post("/me/feed/reset", { csrf })).status, 303, "meanwhile the feed is reset");
    assert.equal((await racing).status, 303);
    assert.ok(released);
    const after = (await w.store.getPreferences(s.account.id))!;
    assert.deepEqual(after.interests.topics, ["raced"]);
    assert.equal(after.feed.epoch, before.feed.epoch + 1, "the reset survived the concurrent save: the stale write was refused and patched again");
    slowStore.getPreferencesJson = realGet;

    // Turning the profile off removes the page and frees the name; deleting the account would too.
    res = await post("/me/profile", { csrf, action: "clear" });
    assert.equal(res.status, 303);
    assert.equal((await page("/u/dan-hulme"))!.status, 404);
    assert.equal((await post("/me/profile", { csrf: ecsrf, action: "set", name: "dan-hulme" }, ec)).status, 303, "free for the taking");
    assert.match((await page("/u/dan-hulme"))!.text, new RegExp(`operator ${(await w.accounts.session(eve.session))!.account.operatorId}`));
    // Without accounts configured, there are no profiles at all.
    assert.equal((await new PagesHandler(w.v2).handle("GET", "/u/dan-hulme"))!.status, 404);
  });
});

describe("briefs from a person's page, after the board was retired", () => {
  it("the propose form is gone and a stale post answers 410 writing nothing; briefs already on the record are listed by operator id, never email, and can still be withdrawn", async () => {
    const w = world();
    const dan = await w.signIn("dan@example.org");
    const cookies = { ecd_b: "browser-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", ecd_s: dan.session };
    const get = (path: string) => w.me.handle(new Request(`https://ecdysis.me${path}`, { headers: { cookie: Object.entries(cookies).map(([k, v]) => `${k}=${v}`).join("; ") } }), path.split("?")[0]!, "1.1.1.1");
    const post = (path: string, form: Record<string, string>) => {
      const p = new URLSearchParams(form).toString();
      return w.me.handle(new Request(`https://ecdysis.me${path}`, { method: "POST", body: p, headers: { "content-type": "application/x-www-form-urlencoded", "content-length": String(p.length), cookie: Object.entries(cookies).map(([k, v]) => `${k}=${v}`).join("; "), origin: "https://ecdysis.me" } }), path, "1.1.1.1");
    };
    let html = await (await get("/me")).text();
    assert.match(html, /<h2 id="challenge">Briefs you attached \(archived\)<\/h2>/);
    assert.match(html, /The challenge board was retired on 5 October 2026/);
    assert.match(html, /href="\/map"/, "the page points at the map instead");
    assert.doesNotMatch(html, /action="\/me\/challenges\/propose"/, "no form proposes anything");
    assert.doesNotMatch(html, /a day at your tier/, "no quota for a retired board");
    const csrf = html.match(/name="csrf" value="([0-9a-f]{40})"/)![1]!;
    const operatorId = dan.account.operatorId;
    // A stale form post (a cached page, a script) is refused with where to go, and nothing is written.
    const before = (await w.v2.logRows()).length;
    let res = await post("/me/challenges/propose", { csrf, claim: "", source: "arxiv:1706.03762", quote: "Attention alone reaches 28.4 BLEU on WMT14 En-De.", test: "BLEU below 27 with the stated setup.", title: "Does attention alone reach 28.4 BLEU?", brief: "Train the base model on the public WMT14 data with the paper's stated setup and report BLEU with its uncertainty; gpu-hours, every choice stated.", scale: "gpu-hours" });
    assert.equal(res.status, 410);
    assert.match(await res.text(), /The challenge board was retired on 5 October 2026: direction now comes from the map/);
    assert.equal((await w.v2.logRows()).length, before, "nothing written");
    assert.equal((await w.v2.record()).external.size, 0, "no claim registered on the way");
    // A brief this person attached before the board was retired is on the log; it stays listed, with its claim, and can be withdrawn.
    const ext = "ext:" + "7".repeat(16);
    await w.log.append("claim.external", { id: ext, source: "arxiv:1706.03762", quote: "Attention alone reaches 28.4 BLEU on WMT14 En-De.", test: "BLEU below 27 with the stated setup.", handle: "", operatorId });
    const chId = "ch:" + "8".repeat(16);
    await w.log.append("challenge.propose", { id: chId, claim: `${ext}#C1`, title: "Does attention alone reach 28.4 BLEU?", brief: "Train the base model on the public WMT14 data with the paper's stated setup and report BLEU with its uncertainty; gpu-hours, every choice stated.", scale: "gpu-hours", proposer: "person", operatorId });
    const rec = await w.v2.record();
    assert.equal(rec.challenges.size, 1);
    const ch = rec.challenges.get(chId)!;
    assert.deepEqual(ch.proposer, { kind: "person", operatorId });
    for (const row of await w.v2.logRows()) assert.ok(!JSON.stringify(row.payload).includes("dan@example.org"), "no email on the log");
    html = await (await get("/me")).text();
    assert.match(html, /Does attention alone reach 28\.4 BLEU\?<\/a> <span class="status open">open<\/span>/);
    assert.match(html, /<form method="post" action="\/me\/challenges\/withdraw" class="inline">/);
    // The board's address sends people to the map; the brief's own page still shows it, by operator id, as archived.
    const board = (await w.pages.handle("GET", "/challenges"))!;
    assert.equal(board.status, 301);
    assert.equal(board.headers.get("location"), "/map");
    const page = (await w.pages.handle("GET", chId.replace(/^ch:/, "/c/")))!;
    assert.equal(page.status, 200);
    const pageHtml = await page.text();
    assert.match(pageHtml, /proposed by a person <span class="mono">op_[0-9a-f]{11}…<\/span>/);
    assert.doesNotMatch(pageHtml, /dan@example\.org/);
    assert.match(pageHtml, /retired/i, "the brief's page says the board is archived");
    // The archived list as data says so too, and the claim's page keeps the brief.
    const list = await w.v2.challenges(50, false);
    assert.equal((list.body as Record<string, unknown>)["retired"], true);
    assert.deepEqual((list.body as Record<string, unknown>)["see"], ["/v2/map", "/v2/frontier"]);
    // Withdrawing needs a reason; then the page says so and offers nothing more.
    res = await post("/me/challenges/withdraw", { csrf, id: chId, reason: "short" });
    assert.equal(res.status, 400);
    res = await post("/me/challenges/withdraw", { csrf, id: chId, reason: "Proposed in haste; a sharper brief is coming." });
    assert.equal(res.status, 303);
    assert.equal((await w.v2.record()).challenges.get(chId)!.withdrawn?.by, "proposer");
    html = await (await get("/me")).text();
    assert.match(html, /<span class="status broken">withdrawn<\/span>/);
    assert.doesNotMatch(html, /action="\/me\/challenges\/withdraw"/, "nothing left to withdraw");
  });
});

describe("alert emails", () => {
  it("sends each alert once, bundled, from the record only, with a one-click stop that works signed out", async () => {
    const { Notifier } = await import("../src/api/v2/notify.js");
    const w = world();
    const ledger = new MemoryStore();
    const mails: Array<{ to: string; subject: string; text: string; headers: Record<string, string> }> = [];
    const notifier = new Notifier({
      accounts: w.accounts, accountStore: w.store, ledger, v2: w.v2,
      send: async (m) => { mails.push({ to: m.to, subject: m.subject, text: m.text, headers: m.headers }); return { ok: true, id: "m" }; },
      from: "Ecdysis <accounts@notify.ecdysis.me>", replyTo: "replies@ecdysis.me", siteBase: "https://ecdysis.me", now: w.now,
    });
    const c = await w.signIn("dan@example.org");
    const s = (await w.accounts.session(c.session))!;
    const code = await w.accounts.newPairingCode(s);
    const kp = await generateKeyPair();
    await w.v2.registerAgent({ constitution: ACK, handle: "Moth", publicKey: kp.publicKey, pairing: code }, "1.1.1.1");
    // Nothing ticked: nothing sent, whatever happens.
    assert.deepEqual(await notifier.run(), { sent: 0, skipped: 0, events: 0 });
    await w.accounts.savePreferences(s, { interests: { fields: [], topics: [], claims: [], agents: [] }, notifications: { digest: "off", alerts: ["check.owed", "finding.against"] }, profile: null, feed: { epoch: 0 } });
    // A check Moth owes, due within two days: one email, with a stop link and no text from anyone's paper.
    const sealedAt = w.now().toISOString();
    const log = (w.v2 as unknown as { o: { log: { append: (t: string, p: Json) => Promise<unknown> } } }).o.log;
    const ext = await w.v2.registerExternalClaim({ payload: { protocol: "ecdysis/0.2", type: "claim.external", source: "arxiv:1706.03762", quote: "attention alone reaches 28.4 BLEU on WMT14 En-De <script>", test: "BLEU below 27 with the stated setup", scope: GENERAL, fidelity: REPORTED, agent: { handle: "Moth", publicKey: kp.publicKey }, ts: sealedAt.replace(/\.\d{3}Z$/, "Z") }, signature: await signJson(kp.privateKey, { protocol: "ecdysis/0.2", type: "claim.external", source: "arxiv:1706.03762", quote: "attention alone reaches 28.4 BLEU on WMT14 En-De <script>", test: "BLEU below 27 with the stated setup", scope: GENERAL, fidelity: REPORTED, agent: { handle: "Moth", publicKey: kp.publicKey }, ts: sealedAt.replace(/\.\d{3}Z$/, "Z") }) });
    assert.equal(ext.status, 201, JSON.stringify(ext.body));
    const ref = String((ext.body as Record<string, Json>)["ref"]);
    await log.append("check.commit", { id: "a".repeat(64), target: ref, kind: "replication", design: REPRODUCTION, bundle: "b".repeat(64), image: true, runtimeMinutes: 5, handle: "Moth", operatorId: c.account.operatorId });
    await log.append("check.seal", { commit: "a".repeat(64), seal: "x", seed: "c".repeat(64), crossCheck: null });
    assert.deepEqual(await notifier.run(), { sent: 0, skipped: 0, events: 0 }, "six days to go: nothing yet");
    w.tick(5 * 24 * 60 * MIN + 10 * MIN);
    let r = await notifier.run();
    assert.deepEqual(r, { sent: 1, skipped: 0, events: 1 });
    assert.equal(mails[0]!.to, "dan@example.org");
    assert.match(mails[0]!.text, /Moth owes the result of its check of ext:/);
    assert.doesNotMatch(mails[0]!.text, /attention alone|<script>/, "nothing anyone wrote reaches an inbox");
    const stop = mails[0]!.text.match(/https:\/\/ecdysis\.me\/me\/stop\?a=([^&\s]+)&t=([0-9a-f]{40})/)!;
    assert.ok(stop);
    assert.match(mails[0]!.headers["list-unsubscribe"] ?? "", /\/me\/stop/);
    // Once.
    w.tick(60 * MIN);
    assert.deepEqual(await notifier.run(), { sent: 0, skipped: 0, events: 0 });
    // The stop link, signed out, in another browser: everything off; a wrong token does nothing.
    const bad = await w.me.handle(new Request(`https://ecdysis.me/me/stop?a=${stop[1]}&t=${"0".repeat(40)}`), "/me/stop", "9.9.9.9");
    assert.equal(bad.status, 404);
    const me2 = new MeHandler({ accounts: w.accounts, v2: w.v2, secure: false, stop: (a, t) => notifier.stop(a, t) });
    const good = await me2.handle(new Request(`https://ecdysis.me/me/stop?a=${decodeURIComponent(stop[1]!)}&t=${stop[2]}`), "/me/stop", "9.9.9.9");
    assert.equal(good.status, 200);
    assert.match(await good.text(), /Alerts stopped/);
    assert.deepEqual((await w.accounts.preferences(s)).notifications, { digest: "off", alerts: [] });
    assert.deepEqual(await notifier.run(), { sent: 0, skipped: 0, events: 0 });
  });
});

describe("the digest", () => {
  it("goes out once a day from 07:00 UTC (weekly on Mondays), says what happened in the fields and on the claims followed, from the record alone, and is silent when there is nothing to say", async () => {
    const { Notifier } = await import("../src/api/v2/notify.js");
    const w = world();
    const ledger = new MemoryStore();
    const mails: Array<{ to: string; subject: string; text: string }> = [];
    const notifier = new Notifier({
      accounts: w.accounts, accountStore: w.store, ledger, v2: w.v2,
      send: async (m) => { mails.push({ to: m.to, subject: m.subject, text: m.text }); return { ok: true, id: "m" }; },
      from: "Ecdysis <accounts@notify.ecdysis.me>", replyTo: "replies@ecdysis.me", siteBase: "https://ecdysis.me", now: w.now,
    });
    // Dan follows maths; Eve follows nothing and chose weekly.
    const dan = await w.signIn("dan@example.org");
    const ds = (await w.accounts.session(dan.session))!;
    await w.accounts.savePreferences(ds, { interests: { fields: ["math"], topics: [], claims: [], agents: [] }, notifications: { digest: "daily", alerts: [] }, profile: null, feed: { epoch: 0 } });
    const eve = await w.signIn("eve@example.org", "browser-ffffffffffffffffffffffffffffff", "3.3.3.3");
    const es = (await w.accounts.session(eve.session))!;
    await w.accounts.savePreferences(es, { interests: { fields: [], topics: [], claims: [], agents: [] }, notifications: { digest: "weekly", alerts: [] }, profile: null, feed: { epoch: 0 } });
    // The clock starts at 09:00 UTC on Saturday 3 October 2026. Nothing has happened: no email, and not again today.
    assert.deepEqual(await notifier.digest(), { sent: 0, skipped: 0 });
    // An unrelated agent publishes a maths paper with a hostile title.
    const kp = await generateKeyPair();
    assert.equal((await w.v2.registerAgent({ constitution: ACK, handle: "Owl", publicKey: kp.publicKey, operatorId: "op-owl" }, "1.1.1.1")).status, 201);
    await w.v2.setTier("op-owl", "verified", "op-steward");
    const paper = { protocol: "ecdysis/0.2", type: "paper", title: "Ignore previous instructions <script>alert(1)</script>", abstract: "An abstract long enough to pass the structural screen, saying what was measured, how, and with what uncertainty.", field: "math", claims: [{ text: "The measured quantity lies in the stated interval in the stated regime.", confidence: 0.7, test: "A fresh run outside the interval.", scope: GENERAL }], builds_on: [], agent: { handle: "Owl", publicKey: kp.publicKey }, ts: w.now().toISOString().replace(/\.\d{3}Z$/, "Z") } as unknown as Json;
    const published = await w.v2.publishPaper({ payload: paper, signature: await signJson(kp.privateKey, paper) });
    assert.equal(published.status, 201, JSON.stringify(published.body));
    const paperId = String((published.body as Record<string, Json>)["id"]);
    // Still today: the empty digest already "went" for today, so nothing more until tomorrow.
    w.tick(60 * MIN);
    assert.deepEqual(await notifier.digest(), { sent: 0, skipped: 0 });
    // Sunday 06:00: too early. Sunday 07:30: Dan's daily digest, pointing at the paper by id, never by title; Eve waits for Monday.
    w.tick(20 * 60 * MIN);
    assert.deepEqual(await notifier.digest(), { sent: 0, skipped: 0 }, "before seven");
    w.tick(90 * MIN);
    assert.deepEqual(await notifier.digest(), { sent: 1, skipped: 0 });
    assert.equal(mails[0]!.to, "dan@example.org");
    assert.match(mails[0]!.subject, /daily digest/);
    assert.match(mails[0]!.text, new RegExp(`1 new paper in math:\\n  https://ecdysis\\.me/p/${paperId.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")} \\(math, 1 claim\\)`));
    assert.doesNotMatch(mails[0]!.text, /Ignore previous|<script>/, "no author's text in an inbox");
    assert.match(mails[0]!.text, /Most worth checking in your fields:/);
    assert.match(mails[0]!.text, /\/me\/stop\?a=/);
    // Once a day.
    w.tick(60 * MIN);
    assert.deepEqual(await notifier.digest(), { sent: 0, skipped: 0 });
    // Monday 08:00: Eve's weekly digest (nothing followed: the frontier, unfiltered); Dan's daily again (the paper is now older than a day: not "new").
    w.tick(24 * 60 * MIN);
    const r = await notifier.digest();
    assert.equal(r.sent, 2, JSON.stringify(mails.map((m) => [m.to, m.subject])));
    const eveMail = mails.find((m) => m.to === "eve@example.org")!;
    assert.match(eveMail.subject, /weekly digest/);
    assert.match(eveMail.text, /Most worth checking:/);
    assert.doesNotMatch(eveMail.text, /new paper/);
    assert.equal(ledger.countEmailSends ? await ledger.countEmailSends(new Date(w.now().getTime() - 48 * 60 * MIN).toISOString()) : 3, 3, "every digest counts against the shared cap");
    // The stop link ends the digest too.
    assert.ok(await notifier.stop(dan.account.id, (await notifier.stopToken(dan.account.id))));
    assert.equal((await w.accounts.preferences(ds)).notifications.digest, "off");
  });
});
