/**
 * Environments (docs/ENVIRONMENTS.md): production is the record of science;
 * staging is a disposable record of its own with a door that signs people in
 * without a link. These tests hold the lines that keep the two apart: the
 * production configuration can never carry the staging door or lose a lock;
 * every response names its deployment; a disposable deployment says so on
 * every page and document and refuses indexing; and the door exists only
 * where it is built, refuses a wrong key in constant time, and does what it
 * says for a browser and for a harness.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { MemoryStore } from "../src/store/memory-store.js";
import { TransparencyLog } from "../src/core/log.js";
import { generateKeyPair, signJson } from "../src/core/crypto.js";
import { MemoryV2Store, V2Service } from "../src/api/v2/service.js";
import { structuralScreener } from "../src/core/hazard.js";
import { Accounts, MemoryAccountStore } from "../src/api/v2/accounts.js";
import { PagesHandler } from "../src/api/v2/pages.js";
import { LogApi } from "../src/api/v2/log-api.js";
import { MemoryRateLimiter, route } from "../src/api/router.js";
import { ENV_HEADER, environmentBanner, environmentNotice, environmentOf, labelResponse, noticeInto, ROBOTS_DISALLOW } from "../src/api/environment.js";
import { DOOR_KEY, doorNext, StagingDoor } from "../src/api/v2/staging-door.js";
import { hostsFrom } from "../src/index.js";
import { sha256Hex } from "../src/api/access.js";
import { CONSTITUTION_VERSION, constitutionHash } from "../src/core/constitution.js";
import type { Json } from "../src/core/canonical.js";

const TOML = readFileSync(new URL("../wrangler.toml", import.meta.url), "utf8");
/** The top-level table of wrangler.toml, before any [env.*] section. */
const TOP = TOML.slice(0, TOML.search(/^\[env\./m));
const STAGING = TOML.slice(TOML.indexOf("[env.staging]"));
const KEY = "ab".repeat(32);
const DOOR = "five-random-words-joined-by-hyphens";
const ACK = { version: CONSTITUTION_VERSION, hash: await constitutionHash() };

describe("wrangler.toml keeps production and staging apart", () => {
  it("production is ENVIRONMENT = \"production\" at the top level, and only [env.staging] is staging", () => {
    assert.match(TOP, /^ENVIRONMENT\s*=\s*"production"/m, "the top-level vars name production");
    assert.ok(!/^ENVIRONMENT\s*=\s*"staging"/m.test(TOP), "nothing at the top level is staging");
    assert.match(STAGING, /^ENVIRONMENT\s*=\s*"staging"/m, "the staging environment names itself");
    assert.equal((TOML.match(/^ENVIRONMENT\s*=\s*"staging"/gm) ?? []).length, 1, "staging is declared once");
  });
  it("the staging door's key is a secret and never a variable, anywhere in the configuration", () => {
    assert.ok(!/STAGING_DOOR_KEY\s*=/.test(TOML), "no STAGING_DOOR_KEY variable in wrangler.toml");
  });
  it("staging has a database, a log key and an operator key of its own, never production's", () => {
    const prodDb = TOP.match(/^database_id\s*=\s*"([^"]+)"/m)?.[1];
    const stagingDb = STAGING.match(/^database_id\s*=\s*"([^"]+)"/m)?.[1];
    assert.ok(prodDb && stagingDb, "both pin a database");
    assert.notEqual(prodDb, stagingDb, "the staging database is never production's");
    // Staging's public keys are Worker secrets the Staging workflow installs beside the private halves: the configuration
    // pins neither, so production's can never be written into the staging block.
    assert.ok(TOP.match(/^STH_PUBLIC_KEY\s*=\s*"([^"]+)"/m)?.[1], "production pins its log key");
    assert.ok(!/^STH_PUBLIC_KEY\s*=/m.test(STAGING), "staging pins no log key in the configuration");
    assert.ok(!/^OPERATOR_PUBLIC_KEY\s*=/m.test(STAGING), "staging pins no operator key in the configuration");
    assert.match(stagingDb!, /^REPLACE_WITH_STAGING_D1_ID$/, "the staging database id is looked up by name at deploy time, never committed");
    assert.match(STAGING, /^name\s*=\s*"ecdysis-core-staging"/m, "a Worker of its own");
    const prodNs = [...TOP.matchAll(/^namespace_id\s*=\s*"(\d+)"/gm)].map((m) => m[1]);
    const stagingNs = [...STAGING.matchAll(/^namespace_id\s*=\s*"(\d+)"/gm)].map((m) => m[1]);
    assert.ok(prodNs.length && stagingNs.length && !prodNs.some((n) => stagingNs.includes(n)), "limiter namespaces are not shared");
  });
  it("staging sends no email and spends no model credits", () => {
    assert.match(STAGING, /^HERALD_PAUSED\s*=\s*"1"/m);
    assert.match(STAGING, /^CONTEXT_PAUSED\s*=\s*"1"/m);
    assert.ok(!/^\[env\.staging\.ai\]/m.test(TOML), "no Workers AI binding on staging: the account's daily budget is production's");
  });
  it("the staging steward list is the three of the team, as address hashes, with production's two unchanged", async () => {
    const prod = TOP.match(/^OPERATOR_EMAIL_HASHES\s*=\s*"([^"]+)"/m)![1]!.split(",");
    const staging = STAGING.match(/^OPERATOR_EMAIL_HASHES\s*=\s*"([^"]+)"/m)![1]!.split(",");
    for (const h of prod) assert.ok(staging.includes(h), "every production steward is a staging steward");
    assert.equal(staging.length, 3);
    assert.ok(staging.includes(await sha256Hex("chris@hulme.ai")), "the third is Chris");
    assert.ok(!prod.includes(await sha256Hex("chris@hulme.ai")), "production's list is the owner's to change, not this pull request's");
  });
});

describe("the environment is read strictly", () => {
  it("only staging and development are not production", () => {
    assert.equal(environmentOf("production"), "production");
    assert.equal(environmentOf("staging"), "staging");
    assert.equal(environmentOf(" Staging "), "staging");
    assert.equal(environmentOf("development"), "development");
    assert.equal(environmentOf(undefined), "production");
    assert.equal(environmentOf(""), "production");
    assert.equal(environmentOf("stagin"), "production", "a misspelling opens nothing");
    assert.equal(environmentOf("test"), "production");
  });
  it("production's hosts are fixed whatever the request says; staging answers for the host it arrived on, or its variables", () => {
    assert.deepEqual(hostsFrom({ ENVIRONMENT: "production", SITE_HOST: "evil.example", API_HOST: "evil.example" }, "evil.example"), { site: "ecdysis.me", api: "api.ecdysis.me" });
    assert.deepEqual(hostsFrom({ ENVIRONMENT: "staging" }, "ecdysis-core-staging.ecdysis.workers.dev"), { site: "ecdysis-core-staging.ecdysis.workers.dev", api: "ecdysis-core-staging.ecdysis.workers.dev" });
    assert.deepEqual(hostsFrom({ ENVIRONMENT: "staging", SITE_HOST: "staging.ecdysis.me", API_HOST: "api-staging.ecdysis.me" }, "whatever.workers.dev"), { site: "staging.ecdysis.me", api: "api-staging.ecdysis.me" });
    assert.deepEqual(hostsFrom({ ENVIRONMENT: "staging" }, "not a host!"), { site: "ecdysis.me", api: "api.ecdysis.me" }, "an unparseable host falls back");
    assert.deepEqual(hostsFrom({ ENVIRONMENT: "staging" }), { site: "ecdysis.me", api: "api.ecdysis.me" }, "the cron has no request");
  });
});

describe("every response names its deployment; a disposable one says so everywhere", () => {
  const html = () => new Response("<!doctype html><html><head><title>t</title></head><body class=\"x\"><main>hello</main></body></html>", { status: 200, headers: { "content-type": "text/html; charset=utf-8", "content-length": "99" } });
  it("production: the header only, and nothing else touched", async () => {
    const r = await labelResponse(html(), "production", "/");
    assert.equal(r.headers.get(ENV_HEADER), "production");
    assert.equal(r.headers.get("x-robots-tag"), null);
    assert.ok(!(await r.text()).includes("data-ecdysis-env"), "no banner on production");
  });
  it("staging: the header, no indexing, and the banner after <body> on every page", async () => {
    const r = await labelResponse(html(), "staging", "/claims");
    assert.equal(r.headers.get(ENV_HEADER), "staging");
    assert.equal(r.headers.get("x-robots-tag"), "noindex, nofollow");
    assert.equal(r.headers.get("content-length"), null, "a rewritten body is measured afresh");
    const text = await r.text();
    assert.match(text, /<body class="x">\n<div role="status" data-ecdysis-env="staging"/, "the banner is the first thing in the body");
    assert.ok(text.includes(environmentNotice("staging")!.split(" (API")[0]!.replace("https://ecdysis.me", '<a href="https://ecdysis.me" style="color:#242629">https://ecdysis.me</a>')), "it names the live record");
    assert.ok(text.endsWith("</html>"), "the rest of the page is untouched");
    assert.ok(!environmentBanner("staging").includes("<script"), "no script: the pages' CSP allows none");
  });
  it("staging: the documents an agent reads before it writes begin with the notice", async () => {
    const md = new Response("# Ecdysis\n\nRead this.", { headers: { "content-type": "text/markdown; charset=utf-8" } });
    const r = await labelResponse(md, "staging", "/skill.md");
    const text = await r.text();
    assert.ok(text.startsWith("> **STAGING.** This is the staging record"), text.slice(0, 80));
    assert.ok(text.endsWith("# Ecdysis\n\nRead this."));
    assert.equal(noticeInto("---\nname: x\n---\n\n# Title\n", "> N.\n\n"), "---\nname: x\n---\n\n> N.\n\n# Title\n", "after front matter");
    assert.equal(noticeInto("---\nunterminated\n", "> N.\n\n"), "> N.\n\n---\nunterminated\n", "an unterminated block is text");
    const txt = new Response("# Ecdysis\n", { headers: { "content-type": "text/plain; charset=utf-8" } });
    assert.ok((await (await labelResponse(txt, "staging", "/llms.txt")).text()).startsWith("# STAGING: This is the staging record"));
    const other = new Response("just text", { headers: { "content-type": "text/plain; charset=utf-8" } });
    assert.equal(await (await labelResponse(other, "staging", "/badge/sth.txt")).text(), "just text", "other text is left alone");
  });
  it("staging: JSON and media bodies are untouched, only labelled", async () => {
    const j = new Response('{"a":1}', { headers: { "content-type": "application/json; charset=utf-8" } });
    const r = await labelResponse(j, "staging", "/v2/record");
    assert.equal(await r.text(), '{"a":1}');
    assert.equal(r.headers.get(ENV_HEADER), "staging");
    const err = await labelResponse(new Response("<html><body>no</body></html>", { status: 404, headers: { "content-type": "text/html" } }), "staging", "/x");
    assert.equal(await err.text(), "<html><body>no</body></html>", "an error page carries no banner");
  });
});

async function world(o: { environment?: "production" | "staging"; door?: boolean; stewards?: string[] } = {}) {
  const now = () => new Date(Date.UTC(2026, 10, 1, 9, 0, 0));
  const accountStore = new MemoryAccountStore();
  const accounts = new Accounts({ store: accountStore, key: KEY, send: null, from: "Ecdysis <accounts@notify.ecdysis.me>", replyTo: "replies@ecdysis.me", siteBase: "https://staging.example", stewardEmailHashes: o.stewards ?? [], now });
  const store = new MemoryStore();
  const log = new TransparencyLog(store, now);
  const logKey = await generateKeyPair();
  const v2store = new MemoryV2Store(() => (store as unknown as { log: Array<{ entry: { seq: number; ts: string; type: string }; payload: Json }> }).log.map((r) => ({ seq: r.entry.seq, ts: r.entry.ts, type: r.entry.type, payload: r.payload })));
  const operatorKey = await generateKeyPair();
  const v2 = new V2Service({ log, store: v2store, logPrivateKey: logKey.privateKey, now, screeners: [structuralScreener()], pairing: (code, ip) => accounts.consumePairing(code, ip), operatorPublicKey: operatorKey.publicKey });
  const logApi = new LogApi({ log, reader: store, signingKey: logKey.privateKey, now });
  const pages = new PagesHandler(v2, { host: "staging.example", logPublicKey: logKey.publicKey, log: logApi });
  // Genesis: the record opens when the founder adopts the constitution under R2, as every reset of staging does first.
  const adoption = { version: ACK.version, hash: ACK.hash, ts: now().toISOString().replace(/\.\d{3}Z$/, "Z") };
  const adopted = await v2.adoptConstitution({ ...adoption, signature: await signJson(operatorKey.privateKey, { op: "adopt", ...adoption }) });
  assert.equal(adopted.status, 201, JSON.stringify(adopted.body));
  const door = o.door ? new StagingDoor({ accounts, v2, key: DOOR, secure: false }) : null;
  const opts = { v2, log: logApi, pages, sthPublicKey: logKey.publicKey, environment: o.environment ?? "staging" as const, stagingDoor: door };
  const req = (path: string, init: RequestInit & { accept?: string } = {}) => {
    const headers = new Headers(init.headers);
    if (init.accept) headers.set("accept", init.accept);
    return new Request(`https://staging.example${path}`, { ...init, headers });
  };
  const entries = () => (store as unknown as { log: Array<{ entry: { seq: number; type: string }; payload: Record<string, unknown> }> }).log;
  return { v2, accounts, log, opts, req, door, entries };
}
const limiter = () => new MemoryRateLimiter(100_000);

describe("the router on a disposable deployment", () => {
  it("names the environment in the agents' index, refuses crawlers, and labels every response", async () => {
    const w = await world({ environment: "staging" });
    const index = await route(w.req("/"), limiter(), w.opts);
    const body = (await index.json()) as { environment?: string; notice?: string };
    assert.equal(body.environment, "staging");
    assert.match((body as { logPublicKey?: string }).logPublicKey ?? "", /^[A-Za-z0-9_-]{40,}$/, "a staging index names its own log key, so a check needs nothing pinned");
    assert.match(body.notice ?? "", /disposable/);
    assert.equal(index.headers.get(ENV_HEADER), "staging");
    const robots = await route(w.req("/robots.txt"), limiter(), w.opts);
    assert.equal(await robots.text(), ROBOTS_DISALLOW);
    const page = await route(w.req("/", { accept: "text/html" }), limiter(), w.opts);
    assert.match(await page.text(), /data-ecdysis-env="staging"/, "the landing page carries the banner");
    const skill = await (await route(w.req("/skill.md"), limiter(), w.opts)).text();
    // skill.md opens with YAML front matter for skill registries; the notice comes straight after it, before the title.
    assert.ok(skill.startsWith("---\nname: ecdysis\n"), "the front matter is still first");
    const fm = skill.indexOf("\n---\n", 4) + 5;
    assert.ok(skill.slice(fm).startsWith("\n> **STAGING.** This is the staging record"), skill.slice(fm, fm + 60));
    assert.match(skill, /\n\n# Ecdysis agent protocol/, "the title follows the notice");
    assert.equal((skill.match(/^---$/gm) ?? []).length, 2, "one front matter block, untouched");
    const heartbeat = await route(w.req("/heartbeat.md"), limiter(), w.opts);
    if (heartbeat.status === 200) assert.ok((await heartbeat.text()).startsWith("> **STAGING.**"), "heartbeat.md begins with the notice");
  });
  it("production's index, robots and pages carry none of it, only the header", async () => {
    const w = await world({ environment: "production" });
    const body = (await (await route(w.req("/"), limiter(), w.opts)).json()) as { environment?: string };
    assert.equal(body.environment, undefined);
    assert.equal((body as { logPublicKey?: string }).logPublicKey, undefined);
    const robots = await route(w.req("/robots.txt"), limiter(), w.opts);
    assert.notEqual(await robots.text(), ROBOTS_DISALLOW);
    const page = await route(w.req("/", { accept: "text/html" }), limiter(), w.opts);
    assert.ok(!(await page.text()).includes("data-ecdysis-env"));
    assert.equal(page.headers.get(ENV_HEADER), "production");
  });
});

describe("the staging door", () => {
  it("does not exist where it is not built, whatever the key, and nothing under /staging/ does", async () => {
    const w = await world({ environment: "production", door: false });
    for (const path of [`/staging/door?key=${DOOR}&email=a@b.co`, "/staging/door", "/staging/anything", "/staging/"]) {
      const r = await route(w.req(path), limiter(), w.opts);
      assert.equal(r.status, 404, path);
    }
    const post = await route(w.req("/staging/door", { method: "POST", body: JSON.stringify({ key: DOOR, email: "a@b.co" }), headers: { "content-type": "application/json" } }), limiter(), w.opts);
    assert.equal(post.status, 404);
  });
  it("refuses to be built with anything but a 64-hex key, and a wrong key learns nothing", async () => {
    const w = await world({ door: true });
    assert.throws(() => new StagingDoor({ accounts: w.accounts, v2: w.v2, key: "short" }));
    assert.ok(DOOR_KEY.test(DOOR) && DOOR_KEY.test("ab".repeat(32)) && !DOOR_KEY.test("too-short-to-be-a-key") && !DOOR_KEY.test("has a space in it, so it is no key") && !DOOR_KEY.test("x".repeat(129)));
    for (const key of ["", "x".repeat(64), DOOR.slice(0, -1) + "x", DOOR.toUpperCase(), DOOR + "s"]) {
      const r = await route(w.req(`/staging/door?key=${key}&email=not-an-address`), limiter(), w.opts);
      assert.equal(r.status, 403, "the key is checked before the address");
      assert.match(await r.text(), /door key does not match/);
    }
    const bad = await route(w.req(`/staging/door?key=${DOOR}&email=not-an-address`), limiter(), w.opts);
    assert.equal(bad.status, 400, "with the right key, the address is checked");
    const other = await route(w.req("/staging/door", { method: "DELETE" }), limiter(), w.opts);
    assert.equal(other.status, 405);
  });
  it("signs a browser in and sends it to its page; the steward list of the staging deployment decides the role", async () => {
    const w = await world({ door: true, stewards: [await sha256Hex("lucy@hulme.ai")] });
    const r = await route(w.req(`/staging/door?key=${DOOR}&email=Lucy@hulme.ai&next=/steward/people`), limiter(), w.opts);
    assert.equal(r.status, 303);
    assert.equal(r.headers.get("location"), "/steward/people");
    const cookie = r.headers.get("set-cookie") ?? "";
    assert.match(cookie, /^ecd_s=[A-Za-z0-9_-]{32,64}; Path=\/; Max-Age=2592000; HttpOnly; SameSite=Lax$/);
    const signed = await w.accounts.session(cookie.slice("ecd_s=".length).split(";")[0]!);
    assert.ok(signed);
    assert.equal(signed!.account.role, "steward");
    assert.ok(await w.accounts.isSteward(signed!.account));
    const member = await route(w.req(`/staging/door?key=${DOOR}&email=someone@example.org&next=https://evil.example/`), limiter(), w.opts);
    assert.equal(member.headers.get("location"), "/me", "an outside address as next is ignored");
    const s2 = await w.accounts.session((member.headers.get("set-cookie") ?? "").slice("ecd_s=".length).split(";")[0]!);
    assert.equal(s2!.account.role, "member");
    assert.equal(doorNext("/me/agents"), "/me/agents");
    assert.equal(doorNext("/steward"), "/steward");
    assert.equal(doorNext("//evil.example"), null);
    assert.equal(doorNext("/claims"), null);
  });
  it("hands a harness an operator with a pairing code that registers an agent, at the tier it asked for, signed off by the door on the log", async () => {
    const w = await world({ door: true });
    const post = (body: Json) => route(w.req("/staging/door", { method: "POST", body: JSON.stringify(body), headers: { "content-type": "application/json" } }), limiter(), w.opts);
    const r = await post({ key: DOOR, email: "sybil-1@red.example", pairing: true, tier: "verified" });
    assert.equal(r.status, 201, await r.clone().text());
    const b = (await r.json()) as { operatorId: string; accountId: string; role: string; created: boolean; pairing: string; tier: string; note: string };
    assert.match(b.operatorId, /^op_[0-9a-f]{24}$/);
    assert.equal(b.role, "member");
    assert.equal(b.created, true);
    assert.match(b.pairing, /^[a-z2-9]{5}-[a-z2-9]{5}-[a-z2-9]{5}$/);
    assert.equal(b.tier, "verified");
    assert.match(b.note, /staging record only/);
    const key = await generateKeyPair();
    const reg = await w.v2.registerAgent({ handle: "sybil-1", publicKey: key.publicKey, pairing: b.pairing, constitution: ACK }, "9.9.9.9");
    assert.equal(reg.status, 201, JSON.stringify(reg.body));
    const rec = await w.v2.record();
    assert.equal(rec.agents.get("sybil-1")?.operatorId, b.operatorId);
    assert.equal(rec.tiers.get(b.operatorId), "verified");
    const tierEntry = w.entries().find((e) => e.entry.type === "operator.tier" && e.payload["tier"] === "verified");
    assert.equal(tierEntry?.payload["steward"], "staging-door", "the log says who set it");
    const again = await post({ key: DOOR, email: "sybil-1@red.example", tier: "verified" });
    assert.equal(again.status, 200);
    assert.equal(((await again.json()) as { created: boolean; tier: string }).tier, "verified", "already at that tier is not a failure");
    const used = await w.v2.registerAgent({ handle: "sybil-2", publicKey: (await generateKeyPair()).publicKey, pairing: b.pairing, constitution: ACK }, "9.9.9.9");
    assert.equal(used.status, 404, "a pairing code works once");
    const badTier = await post({ key: DOOR, email: "x@y.co", tier: "god" });
    assert.equal(badTier.status, 400);
  });
});
