/**
 * Doors (attribution at sign-up): a link that names its channel
 * (?via=moltbook) sets a cookie on the page it lands on; when that browser
 * makes an account, the account records the door and the country Cloudflare
 * saw, once; the stewards count accounts by month, door and country, and
 * nothing names an account. A bad door value is ignored, a later sign-in
 * changes nothing, and deleting the account removes both.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { MemoryStore } from "../src/store/memory-store.js";
import { TransparencyLog } from "../src/core/log.js";
import { generateKeyPair } from "../src/core/crypto.js";
import { MemoryV2Store, V2Service } from "../src/api/v2/service.js";
import { structuralScreener } from "../src/core/hazard.js";
import { Accounts, countryOf, DOOR_COOKIE, doorOf, MemoryAccountStore } from "../src/api/v2/accounts.js";
import { MeHandler } from "../src/api/v2/me.js";
import { StewardHandler } from "../src/api/v2/steward.js";
import { sha256Hex } from "../src/api/access.js";
import { V2Governance } from "../src/api/v2/governance.js";
import { V2Feeds } from "../src/api/v2/feed.js";
import { PagesHandler } from "../src/api/v2/pages.js";
import { route, MemoryRateLimiter } from "../src/api/router.js";
import type { Json } from "../src/core/canonical.js";

const LOG_KEY = await generateKeyPair();
const KEY = "ab".repeat(32);
const BROWSER = "browser-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";

async function world() {
  const clock = { t: Date.UTC(2026, 11, 7, 9, 0, 0) };
  const now = () => new Date(clock.t);
  const sent: Array<{ to: string; text: string }> = [];
  const store = new MemoryAccountStore();
  const accounts = new Accounts({
    store, key: KEY, send: async (m) => { sent.push({ to: m.to, text: m.text }); return { ok: true, id: `m${sent.length}` }; },
    from: "Ecdysis <accounts@notify.ecdysis.me>", replyTo: "replies@ecdysis.me", siteBase: "https://ecdysis.me",
    stewardEmailHashes: [await sha256Hex("daniel@example.org")], now,
  });
  const logStore = new MemoryStore();
  const log = new TransparencyLog(logStore, now);
  const v2store = new MemoryV2Store(() => (logStore as unknown as { log: Array<{ entry: { seq: number; ts: string; type: string }; payload: Json }> }).log.map((r) => ({ seq: r.entry.seq, ts: r.entry.ts, type: r.entry.type, payload: r.payload })));
  const v2 = new V2Service({ log, store: v2store, logPrivateKey: LOG_KEY.privateKey, now, screeners: [structuralScreener()], pairing: (code, ip) => accounts.consumePairing(code, ip) });
  const governance = new V2Governance({ v2, log, operatorPublicKey: null, now });
  const feeds = new V2Feeds(v2, { site: "https://ecdysis.me", api: "https://api.ecdysis.me" });
  const me = new MeHandler({ accounts, v2, governance, feeds, secure: false });
  const pages = new PagesHandler(v2, { host: "api.ecdysis.me", accounts, secure: false });
  const steward = new StewardHandler({ accounts, v2, access: null, now });
  const limiter = new MemoryRateLimiter(1000);
  const site = (path: string) => route(new Request(`https://ecdysis.me${path}`, { headers: { accept: "text/html" } }), limiter, { v2, pages });
  const meGet = (path: string, cookies: Record<string, string>, headers: Record<string, string> = {}, ip = "1.1.1.1") =>
    me.handle(new Request(`https://ecdysis.me${path}`, { headers: { cookie: Object.entries(cookies).map(([k, v]) => `${k}=${v}`).join("; "), ...headers } }), path.split("?")[0]!, ip);
  const linkToken = () => sent.at(-1)!.text.match(/\/me\/login\?t=([A-Za-z0-9_-]+)/)![1]!;
  const cookieOf = (res: Response, name: string) => { const c = res.headers.getSetCookie().find((x) => x.startsWith(`${name}=`)); return c ? decodeURIComponent(c.split(";")[0]!.slice(name.length + 1)) : null; };
  /** Make an account through /me/login the way a browser does: ask for the link, then follow it with these cookies and headers (each sign-up from its own connection, as the sign-up limit is per connection). */
  let n = 0;
  const signUp = async (email: string, cookies: Record<string, string>, headers: Record<string, string> = {}) => {
    const ip = `10.0.0.${++n}`;
    const r = await accounts.requestLink(email, ip, BROWSER);
    assert.ok(r.ok, JSON.stringify(r));
    const res = await meGet(`/me/login?t=${linkToken()}`, { ecd_b: BROWSER, ...cookies }, headers, ip);
    assert.equal(res.status, 303, await res.text());
    const session = cookieOf(res, "ecd_s")!;
    const signed = await accounts.session(session);
    assert.ok(signed, "signed in");
    return { session, signed, account: signed.account };
  };
  const stewardGet = (path: string, session: string) => steward.handle(new Request(`https://ecdysis.me${path}`, { headers: { cookie: `ecd_s=${session}` } }), path.split("?")[0]!);
  return { accounts, store, site, meGet, signUp, stewardGet, cookieOf, tick: (ms: number) => { clock.t += ms; } };
}

describe("doors: attribution at sign-up", () => {
  it("validates door names and country codes", () => {
    assert.equal(doorOf("moltbook"), "moltbook");
    assert.equal(doorOf("india-aim"), "india-aim");
    assert.equal(doorOf("Moltbook"), null, "lower case only");
    assert.equal(doorOf("a".repeat(33)), null, "at most 32");
    assert.equal(doorOf("x y"), null);
    assert.equal(doorOf(""), null);
    assert.equal(doorOf(null), null);
    assert.equal(countryOf("IN"), "IN");
    assert.equal(countryOf("gb"), "GB");
    assert.equal(countryOf("XX"), null, "Cloudflare's placeholder for unknown");
    assert.equal(countryOf("T1"), null, "Tor");
    assert.equal(countryOf("GBR"), null);
    assert.equal(countryOf(null), null);
  });

  it("a ?via= link sets the door cookie on the page it lands on, without caching it, and a bad value sets nothing", async () => {
    const w = await world();
    const r = await w.site("/connect?via=moltbook");
    assert.equal(r.status, 200);
    assert.equal(w.cookieOf(r, DOOR_COOKIE), "moltbook");
    assert.equal(r.headers.get("cache-control"), "no-store", "a response carrying someone's cookie is cached for nobody");
    assert.match(r.headers.getSetCookie().find((x) => x.startsWith(`${DOOR_COOKIE}=`)) ?? "", /Max-Age=7776000; HttpOnly; SameSite=Lax/);
    const plain = await w.site("/connect");
    assert.equal(w.cookieOf(plain, DOOR_COOKIE), null);
    assert.equal(plain.headers.get("cache-control"), "public, max-age=120", "an ordinary page keeps its caching");
    const bad = await w.site("/connect?via=Mol%20tbook");
    assert.equal(w.cookieOf(bad, DOOR_COOKIE), null);
    const me = await w.meGet("/me?via=clawhub", {});
    assert.equal(w.cookieOf(me, DOOR_COOKIE), "clawhub", "the sign-in page too");
  });

  it("the account records the door and the country once, at creation, and never from a later sign-in", async () => {
    const w = await world();
    const a = await w.signUp("priya@example.org", { [DOOR_COOKIE]: "india-aim" }, { "cf-ipcountry": "IN" });
    assert.equal(a.account.door, "india-aim");
    assert.equal(a.account.country, "IN");
    const b = await w.signUp("sam@example.org", {}, {});
    assert.equal(b.account.door, null);
    assert.equal(b.account.country, null);
    const c = await w.signUp("tor@example.org", { [DOOR_COOKIE]: "x" }, { "cf-ipcountry": "T1" });
    assert.equal(c.account.door, "x");
    assert.equal(c.account.country, null, "a Tor placeholder is no country");
    // Priya signs in again from elsewhere with another door: nothing changes.
    const again = await w.signUp("priya@example.org", { [DOOR_COOKIE]: "moltbook" }, { "cf-ipcountry": "GB" });
    assert.equal(again.account.id, a.account.id);
    assert.equal(again.account.door, "india-aim");
    assert.equal(again.account.country, "IN");
    // Deleting the account removes both.
    await w.accounts.deleteAccount(again.signed);
    assert.equal(await w.accounts.accountForOperator(a.account.operatorId), null);
  });

  it("the stewards count accounts by month, door and country, as a page and as CSV, naming no account", async () => {
    const w = await world();
    await w.signUp("priya@example.org", { [DOOR_COOKIE]: "india-aim" }, { "cf-ipcountry": "IN" });
    await w.signUp("arjun@example.org", { [DOOR_COOKIE]: "india-aim" }, { "cf-ipcountry": "IN" });
    await w.signUp("lee@example.org", { [DOOR_COOKIE]: "moltbook" }, { "cf-ipcountry": "GB" });
    await w.signUp("sam@example.org", {}, { "cf-ipcountry": "US" });
    w.tick(31 * 24 * 3600 * 1000);
    await w.signUp("kim@example.org", { [DOOR_COOKIE]: "moltbook" }, { "cf-ipcountry": "GB" });
    const d = await w.signUp("daniel@example.org", {}, {});
    const rows = await w.accounts.doors("2026-01-01");
    assert.deepEqual(rows, [
      { month: "2026-12", door: null, country: "US", count: 1 },
      { month: "2026-12", door: "india-aim", country: "IN", count: 2 },
      { month: "2026-12", door: "moltbook", country: "GB", count: 1 },
      { month: "2027-01", door: null, country: null, count: 1 },
      { month: "2027-01", door: "moltbook", country: "GB", count: 1 },
    ]);
    const page = await w.stewardGet("/steward/people/doors", d.session);
    assert.equal(page.status, 200);
    const html = await page.text();
    assert.match(html, /<h1>Doors<\/h1>/);
    assert.match(html, /<tr><td>india-aim<\/td><td>2<\/td><\/tr>/);
    assert.match(html, /<tr><td>IN<\/td><td>2<\/td><\/tr>/);
    assert.doesNotMatch(html.split("<main")[1]!, /example\.org|acct_|op_[0-9a-f]{24}/, "no account is named (the header names only the signed-in steward)");
    const csv = await w.stewardGet("/steward/people/doors?format=csv", d.session);
    assert.match(csv.headers.get("content-type") ?? "", /text\/csv/);
    assert.equal(await csv.text(), "month,door,country,accounts\r\n2026-12,,US,1\r\n2026-12,india-aim,IN,2\r\n2026-12,moltbook,GB,1\r\n2027-01,,,1\r\n2027-01,moltbook,GB,1\r\n");
    const people = await (await w.stewardGet("/steward/people", d.session)).text();
    assert.match(people, /<a href="\/steward\/people\/doors">Doors<\/a>/);
    const privacy = await (await w.site("/privacy")).text();
    assert.match(privacy, /the door you came through/);
    assert.match(privacy, /Three, all first-party/);
  });
});
