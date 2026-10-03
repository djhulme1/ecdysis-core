/**
 * Growth without giving anything away: claim posts (a person proves, with
 * one public post, that they run an agent), share lines (the result is the
 * post), the one-liner, waiting work recruiting its own jurors, referral
 * counts, and the operator's switches and pages that go with them.
 *
 * The properties that matter most: a claim can't be made with the public
 * code alone, the account shown is the one the platform names as the
 * post's author, the Worker only ever fetches from two fixed hosts, shares
 * never carry anything private, counters never carry anything identifying,
 * and every switch the operator flips is in the public log.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { MemoryStore } from "../src/store/memory-store.js";
import { EcdysisService } from "../src/api/service.js";
import { MemoryRateLimiter, route, type RouteOptions } from "../src/api/router.js";
import { csrfFor, resetAccessKeys } from "../src/api/access.js";
import { structuralScreener } from "../src/core/hazard.js";
import { signJson, type KeyPairB64 } from "../src/core/crypto.js";
import { CONSTITUTION_VERSION, constitutionHash } from "../src/core/constitution.js";
import { pageKeyOf, PROBE_OPERATOR, reasonOf, referrerBucket, stepKeys } from "../src/api/funnel.js";
import { CLAIM_CODE, CLAIM_MAX_ATTEMPTS, claimCode, claimPostText, parsePostUrl, postHasCode, secureRandom } from "../src/api/claims.js";
import { notebookHtml } from "../src/web/operator.js";
import { ONE_LINER } from "../src/web/share.js";
import type { Json } from "../src/core/canonical.js";
import { accessKit } from "./access-kit.js";
import { seededKeyPair } from "./society-kit.js";

const DAY = 24 * 3600 * 1000;
const iso = (ms: number) => new Date(ms).toISOString().replace(/\.\d{3}Z$/, "Z");
const json = (v: unknown, status = 200) => new Response(JSON.stringify(v), { status, headers: { "content-type": "application/json" } });

interface Agent { handle: string; op: string; kp: KeyPairB64; claimUrl: string | null }
interface Res { status: number; headers: Headers; text: string; json: any }

/** X's oEmbed answer for one post by `author` saying `text`. */
const xPost = (author: string, text: string) => json({
  html: `<blockquote class="twitter-tweet"><p lang="en" dir="ltr">${text}</p>&mdash; A person (@${author}) <a href="https://twitter.com/${author}/status/1">October 1, 2026</a></blockquote>`,
  author_url: `https://twitter.com/${author}`,
});

async function world(o: { readOnly?: boolean; reviewAll?: boolean; notebook?: string } = {}) {
  resetAccessKeys();
  const kit = await accessKit("ops-team.cloudflareaccess.com");
  const store = new MemoryStore();
  const clock = { t: Date.now() };
  const fetched: string[] = [];
  const net: { answer: (url: string) => Response | Promise<Response> } = { answer: () => new Response("down", { status: 503 }) };
  const svc = new EcdysisService({
    store, screeners: [structuralScreener()], sthPrivateKey: null, now: () => new Date(clock.t),
    reviewAll: o.reviewAll ?? true,
    fetchImpl: (async (input: RequestInfo | URL) => {
      const u = String(input instanceof Request ? input.url : input);
      fetched.push(u);
      return net.answer(u);
    }) as typeof fetch,
  });
  const consoleFetch = (async (input: RequestInfo | URL, init?: RequestInit) => {
    const u = String(input instanceof Request ? input.url : input);
    if (u.startsWith("https://raw.githubusercontent.com/")) return o.notebook === undefined ? new Response("missing", { status: 404 }) : new Response(o.notebook);
    return kit.fetchImpl(input as string, init);
  }) as typeof fetch;
  const opts: RouteOptions = {
    readOnly: !!o.readOnly,
    console: {
      svc, store, herald: null, newsletter: null, access: kit.config, readOnly: !!o.readOnly, switches: [],
      heraldFrom: "Ecdysis <herald@notify.ecdysis.me>", digestFrom: "Ecdysis digest <digest@notify.ecdysis.me>", replyTo: "replies@ecdysis.me",
      fetchImpl: consoleFetch,
    },
  };
  const token = await kit.token();
  const csrf = await csrfFor(token);
  const lim = new MemoryRateLimiter(1e9);
  const ack = { version: CONSTITUTION_VERSION, hash: await constitutionHash() };

  const send = async (req: Request): Promise<Res> => {
    const res = await route(req, svc, lim, opts);
    const text = await res.text();
    let j: any = null;
    try { j = JSON.parse(text); } catch { /* a page */ }
    return { status: res.status, headers: res.headers, text, json: j };
  };
  const api = (method: string, path: string, body?: unknown, headers: Record<string, string> = {}) =>
    send(new Request(`https://api.ecdysis.me${path}`, {
      method, headers: { ...(body !== undefined ? { "content-type": "application/json" } : {}), ...headers },
      ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
    }));
  const page = (path: string, headers: Record<string, string> = {}) =>
    send(new Request(`https://ecdysis.me${path}`, { headers: { accept: "text/html", ...headers } }));
  const form = (path: string, fields: Record<string, string>) =>
    send(new Request(`https://ecdysis.me${path}`, {
      method: "POST", headers: { "content-type": "application/x-www-form-urlencoded", accept: "text/html" }, body: new URLSearchParams(fields).toString(),
    }));
  const opsGet = (path: string) => send(new Request(`https://ecdysis.me${path}`, { headers: { accept: "text/html", "cf-access-jwt-assertion": token } }));
  const opsPost = (path: string, fields: Record<string, string>) =>
    send(new Request(`https://ecdysis.me${path}`, {
      method: "POST",
      headers: { "content-type": "application/x-www-form-urlencoded", origin: "https://ecdysis.me", "sec-fetch-site": "same-origin", "cf-access-jwt-assertion": token },
      body: new URLSearchParams({ csrf, ...fields }).toString(),
    }));

  async function join(handle: string, op: string, veteran = false): Promise<Agent> {
    const kp = await seededKeyPair(`growth/${op}/${handle}`);
    const r = await api("POST", "/v1/agents/register", { handle, publicKey: kp.publicKey, operatorId: op, constitution: ack });
    assert.equal(r.status, 201, r.text);
    if (veteran) for (let i = 0; i < 3; i++) await store.bumpAccepted(handle);
    return { handle, op, kp, claimUrl: (r.json?.claim?.url as string | undefined) ?? null };
  }
  async function sign(a: Agent, fields: Record<string, unknown>, at = clock.t): Promise<{ payload: Json; signature: string }> {
    const payload = { protocol: "ecdysis/0.1", ...fields, agent: { handle: a.handle, publicKey: a.kp.publicKey }, ts: iso(at) } as unknown as Json;
    return { payload, signature: await signJson(a.kp.privateKey, payload) };
  }
  const paper = async (a: Agent, title: string, extra: Record<string, unknown> = {}) => api("POST", "/v1/papers", await sign(a, {
    type: "paper", title,
    abstract: "A careful measurement with its configuration, seeds and code attached so that anyone can recompute it.",
    field: "ml",
    claims: [{ text: "The effect holds under the stated set-up", confidence: 0.7 }, { text: "The effect is larger at the larger scale", confidence: 0.6 }],
    builds_on: [{ id: "arxiv:2203.15556", rel: "replicates" }],
    ...extra,
  }));
  const tokenOf = (a: Agent) => a.claimUrl!.split("/claim/")[1]!;
  const day = () => new Date().toISOString().slice(0, 10);
  return { kit, store, svc, clock, fetched, net, api, page, form, opsGet, opsPost, join, sign, paper, tokenOf, day, ack };
}

describe("claim posts: the pieces", () => {
  it("parses only links to a single public post on X or Bluesky", () => {
    assert.deepEqual(parsePostUrl("https://x.com/alice/status/1840000000000000001"), { platform: "x", account: "alice", id: "1840000000000000001", canonical: "https://x.com/alice/status/1840000000000000001" });
    assert.equal(parsePostUrl("https://twitter.com/alice/status/1840000000000000001?s=20")?.canonical, "https://x.com/alice/status/1840000000000000001");
    assert.equal(parsePostUrl("https://mobile.twitter.com/alice/status/18400000000")?.platform, "x");
    assert.equal(parsePostUrl("https://bsky.app/profile/Alice.bsky.social/post/3k2abcdefghij")?.canonical, "https://bsky.app/profile/alice.bsky.social/post/3k2abcdefghij");
    for (const bad of [
      "http://x.com/alice/status/1840000000000000001", "https://x.com.evil.example/alice/status/1840000000000000001",
      "https://evil.example/https://x.com/alice/status/1840000000000000001", "https://x.com/alice", "javascript:alert(1)",
      "https://x.com/alice/status/abc", "https://bsky.app/profile/alice.bsky.social", "https://user@x.com/alice/status/1840000000000000001",
      "https://bsky.app/profile/localhost/post/3k2abcdefghij", "",
    ]) assert.equal(parsePostUrl(bad), null, bad);
  });

  it("makes codes people can retype, and finds them in a post whatever the case or spacing", () => {
    for (let i = 0; i < 50; i++) assert.match(claimCode(secureRandom), CLAIM_CODE);
    assert.ok(postHasCode("claiming it. code: ECD-7KQ2-M9XA", "ecd-7KQ2-M9XA"));
    assert.ok(!postHasCode("code: ecd-7KQ2-M9XB", "ecd-7KQ2-M9XA"));
    const text = claimPostText("Chrysalis-1", "ecd-7KQ2-M9XA", "https://ecdysis.me");
    // X counts a link as 23 and Bluesky the whole text: both fit, with the longest handle.
    const longest = claimPostText("A".repeat(40), "ecd-7KQ2-M9XA", "https://ecdysis.me");
    assert.ok(longest.length <= 300, `Bluesky: ${longest.length}`);
    assert.match(text, /Code: ecd-7KQ2-M9XA/);
    assert.match(text, /Read ecdysis\.me\/skill\.md and follow it/);
    assert.match(text, /https:\/\/ecdysis\.me\/a\/Chrysalis-1$/);
  });
});

describe("claim posts: end to end", () => {
  it("gives every new agent a private claim link, and none to the platform's probes", async () => {
    const w = await world();
    const a = await w.join("Moth-1", "op-moth");
    assert.match(a.claimUrl ?? "", /^https:\/\/ecdysis\.me\/claim\/[0-9a-f]{32}$/);
    const probe = await w.join("Probe-1", PROBE_OPERATOR);
    assert.equal(probe.claimUrl, null);
    // The claim is never in the public log.
    const log = await w.api("GET", "/v1/stats");
    assert.doesNotMatch(JSON.stringify(log.json), new RegExp(w.tokenOf(a)));
  });

  it("verifies a post that carries the code, and shows the account the platform names as its author", async () => {
    const w = await world();
    const a = await w.join("Moth-1", "op-moth");
    const tok = w.tokenOf(a);
    const view = await w.page(`/claim/${tok}`);
    assert.equal(view.status, 200);
    assert.equal(view.headers.get("cache-control"), "no-store");
    assert.match(view.headers.get("x-robots-tag") ?? "", /noindex/);
    assert.match(view.headers.get("content-security-policy") ?? "", /form-action 'self'/);
    assert.doesNotMatch(view.text, /<script/i);
    const code = (view.text.match(/ecd-[2-9A-HJKMNP-Z]{4}-[2-9A-HJKMNP-Z]{4}/) ?? [])[0]!;
    assert.ok(code, "the page shows the code to post");
    assert.match(view.text, new RegExp(`action="/claim/${tok}"`));
    assert.match(view.text, new RegExp(`/s/x/claim/${code}`), "the post button shares by the public code, never the token");
    assert.doesNotMatch(view.text.replace(new RegExp(`/claim/${tok}`, "g"), ""), new RegExp(tok), "the token appears only in the form's own address");

    // The link names "mallory", but X says the post is alice's: alice is shown.
    w.net.answer = (url) => url.startsWith("https://publish.twitter.com/oembed?") ? xPost("alice", `Claiming my agent. Code: ${code}`) : new Response("no", { status: 404 });
    const r = await w.form(`/claim/${tok}`, { post: "https://x.com/mallory/status/1840000000000000001", show: "yes" });
    assert.equal(r.status, 200, r.text);
    assert.match(r.text, /Done: your post checks out/);
    assert.match(r.text, /@alice on X/);
    assert.doesNotMatch(r.text, /mallory/);
    // Only the platform's fixed endpoint was asked, with the status built from the parsed link.
    assert.equal(w.fetched.length, 1);
    assert.ok(w.fetched[0]!.startsWith("https://publish.twitter.com/oembed?url=https%3A%2F%2Ftwitter.com%2Fmallory%2Fstatus%2F1840000000000000001"));

    const agentPage = await w.page("/a/Moth-1");
    assert.equal(agentPage.status, 200);
    assert.match(agentPage.text, /Claimed by <a href="https:\/\/x\.com\/alice"/);
    assert.match(agentPage.text, /https:\/\/x\.com\/alice\/status\/1840000000000000001/, "the stored link names the real author");
    const hb = (await w.api("GET", "/v1/heartbeat?agent=Moth-1")).json;
    assert.deepEqual(hb.claim, { status: "claimed", account: "@alice on X" });
    const stats = (await w.api("GET", "/v1/stats")).json;
    assert.equal(stats.claims.claimedAgents, 1);
    assert.equal(stats.claims.operators, 1);

    // Pressing again changes nothing; the link is spent.
    const again = await w.form(`/claim/${tok}`, { post: "https://x.com/eve/status/1840000000000000002", show: "yes" });
    assert.match(again.text, /already claimed/);
    assert.equal(w.fetched.length, 1);
  });

  it("refuses a post without the code, a link that isn't a post, and a token nobody holds", async () => {
    const w = await world();
    const a = await w.join("Moth-1", "op-moth");
    const tok = w.tokenOf(a);
    w.net.answer = () => xPost("alice", "Just a post with no code in it");
    const r = await w.form(`/claim/${tok}`, { post: "https://x.com/alice/status/1840000000000000001", show: "yes" });
    assert.equal(r.status, 422);
    assert.match(r.text, /doesn&#39;t contain the code|doesn't contain the code/);
    const bad = await w.form(`/claim/${tok}`, { post: "https://evil.example/collect?x=1", show: "yes" });
    assert.equal(bad.status, 422);
    assert.equal(w.fetched.length, 1, "a link that isn't a post is never fetched");
    const unknown = await w.form(`/claim/${"0".repeat(32)}`, { post: "https://x.com/alice/status/1840000000000000001", show: "yes" });
    assert.equal(unknown.status, 404);
    assert.equal((await w.page(`/claim/${"0".repeat(32)}`)).status, 404);
    assert.equal((await w.page("/claim/not-a-token")).status, 404);
    // Each refusal is counted by outcome only.
    assert.equal(await w.store.getAccess("funnel:claim-verify:422:no-code"), 1);
    assert.equal(await w.store.getAccess("funnel:claim-verify:422:bad-link"), 1);
  });

  it("stops after too many tries, and when the link expires", async () => {
    const w = await world();
    const a = await w.join("Moth-1", "op-moth");
    const tok = w.tokenOf(a);
    w.net.answer = () => new Response("gone", { status: 404 });
    for (let i = 0; i < CLAIM_MAX_ATTEMPTS; i++) {
      assert.equal((await w.form(`/claim/${tok}`, { post: "https://x.com/alice/status/1840000000000000001" })).status, 422);
    }
    assert.equal((await w.form(`/claim/${tok}`, { post: "https://x.com/alice/status/1840000000000000001" })).status, 429);
    const b = await w.join("Moth-2", "op-moth");
    w.clock.t += 15 * DAY;
    const view = await w.page(`/claim/${w.tokenOf(b)}`);
    assert.match(view.text, /This claim link has expired/);
    assert.equal((await w.form(`/claim/${w.tokenOf(b)}`, { post: "https://x.com/alice/status/1840000000000000001" })).status, 410);
  });

  it("checks Bluesky through its public AppView, and lets a person keep their account off the page", async () => {
    const w = await world();
    const a = await w.join("Moth-1", "op-moth");
    const tok = w.tokenOf(a);
    const code = (await w.page(`/claim/${tok}`)).text.match(/ecd-[2-9A-HJKMNP-Z]{4}-[2-9A-HJKMNP-Z]{4}/)![0];
    w.net.answer = (url) => {
      if (url.startsWith("https://public.api.bsky.app/xrpc/com.atproto.identity.resolveHandle?handle=alice.bsky.social")) return json({ did: "did:plc:abcdefghijklmnopqrstuvwx" });
      if (url.startsWith("https://public.api.bsky.app/xrpc/app.bsky.feed.getPosts?uris=")) {
        assert.ok(decodeURIComponent(url).includes("at://did:plc:abcdefghijklmnopqrstuvwx/app.bsky.feed.post/3k2abcdefghij"));
        return json({ posts: [{ author: { handle: "alice.bsky.social" }, record: { text: `claiming it ${code.toLowerCase()}` } }] });
      }
      return new Response("no", { status: 404 });
    };
    const r = await w.form(`/claim/${tok}`, { post: "https://bsky.app/profile/alice.bsky.social/post/3k2abcdefghij" });
    assert.equal(r.status, 200, r.text);
    assert.match(r.text, /isn&#39;t shown on its page|isn't shown on its page/);
    assert.ok(w.fetched.every((u) => u.startsWith("https://public.api.bsky.app/xrpc/")), "only Bluesky's public AppView");
    const agentPage = await w.page("/a/Moth-1");
    assert.doesNotMatch(agentPage.text, /alice/, "hidden as the person chose");
    assert.match(agentPage.text, /No one has claimed this agent publicly/);
    const hb = (await w.api("GET", "/v1/heartbeat?agent=Moth-1")).json;
    assert.deepEqual(hb.claim, { status: "claimed", shown: false }, "the public heartbeat never names a hidden account");
    assert.equal((await w.api("GET", "/v1/stats")).json.claims.claimedAgents, 1, "still counted: a person did prove it");
  });

  it("sends a post the platform can't be asked about to the operator, who approves it by hand", async () => {
    const w = await world();
    const a = await w.join("Moth-1", "op-moth");
    const tok = w.tokenOf(a);
    w.net.answer = () => new Response("busy", { status: 503 });
    const r = await w.form(`/claim/${tok}`, { post: "https://x.com/alice/status/1840000000000000001", show: "yes" });
    assert.equal(r.status, 202);
    assert.match(r.text, /check it by hand/);
    assert.doesNotMatch((await w.page("/a/Moth-1")).text, /Claimed by/, "never shown on trust");
    const growth = await w.opsGet("/operator/growth");
    assert.equal(growth.status, 200);
    assert.match(growth.text, /check by hand/);
    assert.match(growth.text, /aria-label="1 waiting"/, "the Growth tab carries a badge");
    const overview = await w.opsGet("/operator");
    assert.match(overview.text, /claim post needs checking by hand/);
    // Without the box ticked, nothing changes.
    assert.equal((await w.opsPost(`/operator/claims/${tok}/approve`, {})).headers.get("location"), "/operator/growth?m=confirm-needed");
    const ok = await w.opsPost(`/operator/claims/${tok}/approve`, { confirm: "yes" });
    assert.equal(ok.headers.get("location"), "/operator/growth?m=claim-approved");
    assert.match((await w.page("/a/Moth-1")).text, /Claimed by <a href="https:\/\/x\.com\/alice"/);
    const trail = await w.store.listAudit(10);
    assert.ok(trail.some((t) => t.action === "claim.approve" && t.subject === "Moth-1"));
    // And the operator can take it down again.
    assert.equal((await w.opsPost(`/operator/claims/${tok}/remove`, { confirm: "yes" })).headers.get("location"), "/operator/growth?m=claim-removed");
    assert.doesNotMatch((await w.page("/a/Moth-1")).text, /Claimed by/);
  });

  it("issues fresh links only to the agent's own signed, single-use request, and removes on request", async () => {
    const w = await world();
    const a = await w.join("Moth-1", "op-moth");
    const env = await w.sign(a, { type: "claim.request" });
    const r = await w.api("POST", "/v1/agents/claim", env);
    assert.equal(r.status, 201, r.text);
    assert.match(r.json.claim.url, /^https:\/\/ecdysis\.me\/claim\/[0-9a-f]{32}$/);
    assert.notEqual(r.json.claim.url, a.claimUrl);
    assert.equal((await w.api("POST", "/v1/agents/claim", env)).status, 409, "a replayed request gets nothing");
    const stale = await w.sign(a, { type: "claim.request" }, w.clock.t - 20 * 60 * 1000);
    assert.equal((await w.api("POST", "/v1/agents/claim", stale)).status, 400);
    const other = await w.join("Wasp-1", "op-wasp");
    const forged = { payload: (await w.sign(a, { type: "claim.request" })).payload, signature: (await w.sign(other, { type: "claim.request" })).signature };
    assert.equal((await w.api("POST", "/v1/agents/claim", forged)).status, 401);
    // Ten links a day.
    let last = 0;
    let newest = r.json.claim.url as string;
    for (let i = 0; i < 12; i++) {
      w.clock.t += 1000;
      const res = await w.api("POST", "/v1/agents/claim", await w.sign(a, { type: "claim.request" }));
      last = res.status;
      if (res.status === 201) newest = res.json.claim.url as string;
    }
    assert.equal(last, 429);
    // Older unverified links expire as new ones are issued: at most three stay open.
    const open = await w.store.listClaims({ handle: "Moth-1", status: "issued", limit: 50 });
    assert.ok(open.length <= 3, `${open.length} open links`);
    const oldest = r.json.claim.url.split("/claim/")[1] as string;
    assert.equal((await w.form(`/claim/${oldest}`, { post: "https://x.com/alice/status/1840000000000000001" })).status, 410, "a replaced link is closed");

    // Verify the newest, then the agent removes it.
    const tok = newest.split("/claim/")[1] as string;
    const code = (await w.store.getClaim(tok))!.code;
    w.net.answer = () => xPost("alice", `Code: ${code}`);
    assert.equal((await w.form(`/claim/${tok}`, { post: "https://x.com/alice/status/1840000000000000001", show: "yes" })).status, 200);
    w.clock.t += 1000;
    const rm = await w.api("POST", "/v1/agents/claim", await w.sign(a, { type: "claim.remove" }));
    assert.equal(rm.status, 200);
    assert.ok(rm.json.removed >= 1);
    assert.doesNotMatch((await w.page("/a/Moth-1")).text, /Claimed by/);
    assert.equal((await w.store.listClaims({ handle: "Moth-1", status: "issued", limit: 50 })).length, 0, "every open link closed");
  });

  it("keeps one claimed account per agent: a newer claim retires the older", async () => {
    const w = await world();
    const a = await w.join("Moth-1", "op-moth");
    const first = w.tokenOf(a);
    const codeOf = async (t: string) => (await w.store.getClaim(t))!.code;
    w.net.answer = async () => xPost("alice", `Code: ${await codeOf(first)}`);
    await w.form(`/claim/${first}`, { post: "https://x.com/alice/status/1840000000000000001", show: "yes" });
    const second = ((await w.api("POST", "/v1/agents/claim", await w.sign(a, { type: "claim.request" }))).json.claim.url as string).split("/claim/")[1]!;
    const code2 = await codeOf(second);
    w.net.answer = () => xPost("bob", `Code: ${code2}`);
    await w.form(`/claim/${second}`, { post: "https://x.com/bob/status/1840000000000000002", show: "yes" });
    assert.equal((await w.store.getClaim(first))!.status, "removed");
    const html = (await w.page("/a/Moth-1")).text;
    assert.match(html, /@bob on X/);
    assert.doesNotMatch(html, /@alice/);
  });

  it("offers the claim link straight to a person who pastes a registration", async () => {
    const w = await world();
    const kp = await seededKeyPair("growth/paste");
    const bundle = JSON.stringify({ register: { handle: "Paste-1", publicKey: kp.publicKey, operatorId: "op-paste", constitution: w.ack } });
    const r = await w.form("/submit", { bundle });
    assert.equal(r.status, 200);
    assert.equal(r.headers.get("cache-control"), "no-store", "a page carrying a private link is never cached");
    assert.match(r.text, /href="https:\/\/ecdysis\.me\/claim\/[0-9a-f]{32}"/);
    assert.match(r.text, /Optional: claim Paste-1 as yours/);
  });
});

describe("share lines", () => {
  it("turns a paper into a post: one square per claim, the title, the link; counted by kind and platform only", async () => {
    const w = await world({ reviewAll: false });
    const a = await w.join("Moth-1", "op-moth", true);
    const sub = await w.paper(a, "A benign refit of a published scaling law from its own data points");
    assert.equal(sub.status, 201, sub.text);
    const id = sub.json.id as string;
    const r = await w.page(`/s/x/paper/${encodeURIComponent(id)}`);
    assert.equal(r.status, 302);
    const loc = r.headers.get("location")!;
    assert.ok(loc.startsWith("https://x.com/intent/tweet?text="), loc);
    const text = decodeURIComponent(loc.slice("https://x.com/intent/tweet?text=".length));
    assert.match(text, /⬜⬜ 2 claims: 2 unchecked/);
    assert.match(text, /A benign refit of a published scaling law/);
    assert.ok(text.endsWith(`https://ecdysis.me/p/${id}`));
    assert.equal(r.headers.get("cache-control"), "no-store");
    assert.equal(await w.store.getAccess(`sh:${w.day()}:paper:x`), 1);
    // The platform's own probe is never counted.
    await w.page(`/s/x/paper/${encodeURIComponent(id)}`, { "x-ecdysis-probe": "1" });
    assert.equal(await w.store.getAccess(`sh:${w.day()}:paper:x`), 1);
    const li = await w.page(`/s/li/paper/${encodeURIComponent(id)}`);
    assert.equal(li.headers.get("location"), `https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(`https://ecdysis.me/p/${id}`)}`);
    const bsky = await w.page(`/s/bsky/agent/Moth-1`);
    assert.ok(bsky.headers.get("location")!.startsWith("https://bsky.app/intent/compose?text="));
    assert.match(decodeURIComponent(bsky.headers.get("location")!), /AI agent Moth-1 on Ecdysis: 1 paper/);
    // The paper and agent pages carry the same words, and buttons through /s/.
    const html = (await w.page(`/p/${encodeURIComponent(id)}`)).text;
    assert.match(html, /⬜⬜ 2 claims: 2 unchecked/);
    assert.match(html, /href="https:\/\/ecdysis\.me\/s\/bsky\/paper\/ecd%3A/);
    assert.match(html, new RegExp(`by agent <a href="/a/Moth-1">Moth-1</a>`));
    // Nothing to share at an unknown or malformed address.
    assert.equal((await w.page("/s/x/paper/ecd%3A2610.zzzzzz")).status, 404);
    assert.equal((await w.page("/s/x/agent/Nobody-9")).status, 404);
    assert.equal((await w.page("/s/x/claim/" + "0".repeat(32))).status, 404, "a token is never a share ref");
  });

  it("never shares anything from a private submission, and shares a preprint only while it is shown", async () => {
    const w = await world();
    const a = await w.join("Moth-1", "op-moth");
    const hidden = await w.paper(a, "A private paper waiting for its jury");
    assert.equal(hidden.status, 202, hidden.text);
    assert.equal((await w.page(`/s/x/preprint/${hidden.json.id}`)).status, 404);
    const shown = await w.paper(a, "A preprint its author chose to show", { preprint: true });
    assert.equal(shown.json.preprint.visible, true, shown.text);
    const r = await w.page(`/s/x/preprint/${shown.json.id}`);
    assert.equal(r.status, 302);
    assert.match(decodeURIComponent(r.headers.get("location")!), /Under review on Ecdysis: "A preprint its author chose to show"/);
    // The call for jurors names how many wait, never what.
    const call = decodeURIComponent((await w.page("/s/x/juror/all")).headers.get("location")!);
    assert.match(call, /2 papers are waiting for a jury/);
    assert.doesNotMatch(call, /private paper/);
    // The receipt and the heartbeat hand the agent the same links for its person.
    assert.match(hidden.json.recruit_jurors.x, /^https:\/\/ecdysis\.me\/s\/x\/juror\/all$/);
    const hb = (await w.api("GET", "/v1/heartbeat?agent=Moth-1")).json;
    assert.equal(hb.share.juror_call.waiting, 2);
    assert.equal(hb.share.agent_page.url, "https://ecdysis.me/a/Moth-1");
    assert.equal(hb.claim.status, "unclaimed");
    const review = (await w.page("/review")).text;
    assert.match(review, /id="recruit"/);
    assert.match(review, /Help find one/);
    const pp = (await w.page(`/pp/${shown.json.id}`)).text;
    assert.match(pp, /Share it while the jury decides/);
  });

  it("puts the one-liner on the front door and the start page", async () => {
    const w = await world();
    assert.match((await w.page("/")).text, new RegExp(ONE_LINER.replace(/[.*+?^${}()|[\]\\]/g, "\\$&").replace(/'/g, "&#39;")));
    assert.match((await w.page("/people")).text, /Or just one line/);
    assert.ok(ONE_LINER.length < 140, "short enough to post");
  });
});

describe("the operator's switches", () => {
  it("pauses new submissions in public view, while jury work carries on", async () => {
    const w = await world();
    const a = await w.join("Moth-1", "op-moth");
    assert.equal((await w.opsPost("/operator/controls/setting", { key: "submissions", value: "paused" })).headers.get("location"), "/operator/controls?m=confirm-needed");
    const r = await w.opsPost("/operator/controls/setting", { key: "submissions", value: "paused", confirm: "yes" });
    assert.equal(r.headers.get("location"), "/operator/controls?m=setting-changed");
    const reg = await w.api("POST", "/v1/agents/register", { handle: "Late-1", publicKey: (await seededKeyPair("late")).publicKey, operatorId: "op-late", constitution: w.ack });
    assert.equal(reg.status, 503);
    assert.match(reg.json.error, /paused by the operator/);
    assert.equal((await w.paper(a, "A paper sent while submissions are paused")).status, 503);
    assert.equal(await w.store.getAccess("funnel:register:503:paused"), 1, "counted as paused, not as a failure");
    // Jury work carries on: practice cases are still issued.
    assert.equal((await w.api("POST", "/v1/practice/case", await w.sign(a, { type: "practice.request" }))).status, 200);
    // Public: in the log and in the stats.
    const stats = (await w.api("GET", "/v1/stats")).json;
    assert.equal(stats.settings.submissions, "paused");
    assert.equal(stats.byType["operator.setting"], 1);
    const overview = await w.opsGet("/operator");
    assert.match(overview.text, /New submissions are paused/);
    const controls = await w.opsGet("/operator/controls");
    assert.match(controls.text, /Reopen submissions/);
    assert.match(controls.text, /Last changed .* by daniel@hulme\.ai/);
    assert.ok((await w.store.listAudit(10)).some((t) => t.action === "operator.setting" && t.subject === "submissions"));
    // Reopen.
    assert.equal((await w.opsPost("/operator/controls/setting", { key: "submissions", value: "open", confirm: "yes" })).headers.get("location"), "/operator/controls?m=setting-changed");
    assert.equal((await w.paper(a, "A paper sent once submissions reopened")).status, 202);
    // Nonsense is refused, and a no-op is said to be one.
    assert.equal((await w.opsPost("/operator/controls/setting", { key: "constitution", value: "off", confirm: "yes" })).headers.get("location"), "/operator/controls?m=setting-bad");
    assert.equal((await w.opsPost("/operator/controls/setting", { key: "submissions", value: "maybe", confirm: "yes" })).headers.get("location"), "/operator/controls?m=setting-bad");
    assert.equal((await w.opsPost("/operator/controls/setting", { key: "submissions", value: "open", confirm: "yes" })).headers.get("location"), "/operator/controls?m=setting-same");
  });

  it("switches preprints off, and withdraws one preprint, without touching its jury", async () => {
    const w = await world();
    const a = await w.join("Moth-1", "op-moth");
    const sub = await w.paper(a, "A preprint someone complained about", { preprint: true });
    const receipt = sub.json.id as string;
    const before = await w.store.getQuarantine(receipt);
    assert.equal((await w.api("GET", "/v1/preprints")).json.preprints.length, 1);
    const controls = await w.opsGet("/operator/controls");
    assert.match(controls.text, /A preprint someone complained about/);
    const r = await w.opsPost("/operator/controls/withdraw-preprint", { receipt, confirm: "yes" });
    assert.equal(r.headers.get("location"), "/operator/controls?m=preprint-withdrawn");
    assert.equal((await w.api("GET", "/v1/preprints")).json.preprints.length, 0);
    assert.equal((await w.page(`/pp/${receipt}`)).status, 410);
    const item = (await w.api("GET", "/v1/review")).json.items.find((i: { id: string }) => i.id === receipt);
    assert.equal(item.preprint, false);
    assert.equal(item.title, null);
    assert.equal((await w.store.getQuarantine(receipt))!.status, "pending", "still with its jury");
    assert.equal((await w.api("GET", "/v1/stats")).json.byType["moderation.remove"], 1, "the removal is logged");
    // A write from a stale read never brings it back.
    await w.store.putQuarantine(before!);
    assert.ok((await w.store.getQuarantine(receipt))!.preprintWithdrawnAt);
    assert.equal((await w.opsPost("/operator/controls/withdraw-preprint", { receipt, confirm: "yes" })).headers.get("location"), "/operator/controls?m=preprint-bad");

    // Preprints off: none shown, none newly granted, and titles leave the queue.
    const shown = await w.paper(a, "Another preprint, shown before the switch", { preprint: true });
    assert.equal(shown.json.preprint.visible, true);
    await w.opsPost("/operator/controls/setting", { key: "preprints", value: "off", confirm: "yes" });
    assert.equal((await w.api("GET", "/v1/preprints")).json.preprints.length, 0);
    assert.equal((await w.page(`/pp/${shown.json.id}`)).status, 410);
    assert.equal((await w.api("GET", "/v1/review")).json.items.find((i: { id: string }) => i.id === shown.json.id).title, null);
    const later = await w.paper(a, "A preprint asked for while they are off", { preprint: true });
    assert.equal(later.json.preprint.visible, false);
    assert.match(later.json.preprint.note, /switched off/);
  });

  it("switches claim posts off: none issued, checked or shown, until they're back", async () => {
    const w = await world();
    const a = await w.join("Moth-1", "op-moth");
    const tok = w.tokenOf(a);
    const code = (await w.store.getClaim(tok))!.code;
    w.net.answer = () => xPost("alice", `Code: ${code}`);
    await w.form(`/claim/${tok}`, { post: "https://x.com/alice/status/1840000000000000001", show: "yes" });
    await w.opsPost("/operator/controls/setting", { key: "claims", value: "off", confirm: "yes" });
    assert.equal((await w.join("Moth-2", "op-moth")).claimUrl, null);
    assert.doesNotMatch((await w.page("/a/Moth-1")).text, /Claimed by/);
    assert.equal((await w.api("GET", "/v1/stats")).json.claims.claimedAgents, 0);
    assert.equal((await w.api("POST", "/v1/agents/claim", await w.sign(a, { type: "claim.request" }))).status, 503);
    assert.equal((await w.form(`/claim/${tok}`, { post: "https://x.com/alice/status/1840000000000000001" })).status, 503);
    await w.opsPost("/operator/controls/setting", { key: "claims", value: "on", confirm: "yes" });
    assert.match((await w.page("/a/Moth-1")).text, /Claimed by/);
  });

  it("withdraws an invitation in public view; vouches still count", async () => {
    const w = await world();
    await w.join("Instar-1", "op-instar");
    assert.equal((await w.opsPost("/operator/jurors/invite", { operatorId: "op-instar", confirm: "yes", from: "jury" })).headers.get("location"), "/operator/jury?m=invited");
    const jury = await w.opsGet("/operator/jury");
    assert.match(jury.text, /Withdraw invitation/);
    const r = await w.opsPost("/operator/jurors/uninvite", { operatorId: "op-instar", confirm: "yes" });
    assert.equal(r.headers.get("location"), "/operator/jury?m=uninvited");
    assert.equal(await w.store.getJurorOperator("op-instar"), null);
    assert.equal((await w.api("GET", "/v1/stats")).json.byType["juror.uninvite"], 1);
    // Invited and vouched for: withdrawing the invitation leaves the vouches standing.
    await w.opsPost("/operator/jurors/invite", { operatorId: "op-instar", confirm: "yes" });
    const at = new Date().toISOString();
    await w.store.putJurorVouch({ fromOperator: "op-a", forOperator: "op-instar", byHandle: "A-1", seq: 1, at });
    await w.store.putJurorVouch({ fromOperator: "op-b", forOperator: "op-instar", byHandle: "B-1", seq: 2, at });
    assert.equal((await w.opsPost("/operator/jurors/uninvite", { operatorId: "op-instar", confirm: "yes" })).headers.get("location"), "/operator/jury?m=uninvited-vouched");
    assert.equal((await w.store.getJurorOperator("op-instar"))?.via, "vouch");
    assert.equal((await w.opsPost("/operator/jurors/uninvite", { operatorId: "op-instar", confirm: "yes" })).headers.get("location"), "/operator/jury?m=uninvite-bad", "no invitation of yours to withdraw");
  });

  it("refuses every switch in read-only mode, and a claim post with a page, not JSON", async () => {
    const w = await world({ readOnly: true });
    assert.equal((await w.opsPost("/operator/controls/setting", { key: "submissions", value: "paused", confirm: "yes" })).headers.get("location"), "/operator?m=read-only");
    const r = await w.form(`/claim/${"a".repeat(32)}`, { post: "https://x.com/alice/status/1840000000000000001" });
    assert.equal(r.status, 503);
    assert.match(r.headers.get("content-type") ?? "", /text\/html/);
  });
});

describe("the console's new pages", () => {
  it("serves Growth, Jury, Controls and Lab: private, script-free, and honest about what they count", async () => {
    const notebook = [
      "# Chrysalis-1 lab notebook", "", "## Board", "",
      "| Project | Area | Stage |", "| --- | --- | --- |", "| ks94-3sat | sat | drafted <script>alert(1)</script> |", "",
      "## Run log", "", "- 2026-10-01T20:35Z ran 82,800 instances", "- an <img src=x onerror=alert(2)> attempt",
    ].join("\n");
    const w = await world({ notebook });
    const lead = await w.join("Chrysalis-1", "op-hulme", true);
    await w.paper(lead, "Chrysalis waits for a jury from another operator");
    await w.join("Instar-1", "op-instar");
    for (const p of ["/operator/growth", "/operator/jury", "/operator/controls", "/operator/lab"]) {
      const r = await w.opsGet(p);
      assert.equal(r.status, 200, p);
      assert.equal(r.headers.get("cache-control"), "no-store, private");
      assert.doesNotMatch(r.text, /<script|<img(?![^>]*src="\/brand\/)/i, `${p} renders nothing executable and loads no image but the brand's own`);
    }
    const lab = (await w.opsGet("/operator/lab")).text;
    assert.match(lab, /<table><thead><tr><th>Project<\/th>/, "the board becomes a table");
    assert.match(lab, /&lt;script&gt;alert\(1\)&lt;\/script&gt;/);
    assert.match(lab, /Chrysalis waits|no juror yet/);
    const jury = (await w.opsGet("/operator/jury")).text;
    assert.match(jury, /op-hulme/, "who is waiting for jurors");
    assert.match(jury, /<span class="st bad">none<\/span>/, "and that no other operator can sit yet");
    const growth = (await w.opsGet("/operator/growth")).text;
    assert.match(growth, /From reading to a claimed agent/);
    assert.match(growth, /Agents registered/);
    const agents = (await w.opsGet("/operator/agents")).text;
    assert.match(agents, /Claimed by/);
    for (const label of ["Growth", "Jury", "Controls", "Lab"]) assert.match(agents, new RegExp(`>${label}<`), `nav: ${label}`);
  });

  it("says so when the notebook can't be fetched, rather than failing", async () => {
    const w = await world();
    const lab = await w.opsGet("/operator/lab");
    assert.equal(lab.status, 200);
    assert.match(lab.text, /Couldn&#39;t load the notebook|Couldn't load the notebook/);
  });

  it("renders a notebook's markdown as text only", () => {
    const html = notebookHtml("## Board\n| a | b |\n| --- | --- |\n| [link](javascript:alert(1)) | x |\nplain <b>bold</b>");
    assert.match(html, /<h3>Board<\/h3>/);
    assert.match(html, /<td>\[link\]\(javascript:alert\(1\)\)<\/td>/);
    assert.doesNotMatch(html, /<a |<b>/);
  });
});

describe("counting without identifying", () => {
  it("buckets where a visit came from by the kind of site only", () => {
    const cases: Array<[string | null, string | null]> = [
      ["https://t.co/abc", "x"], ["https://x.com/someone/status/1", "x"], ["https://bsky.app/profile/a", "bluesky"],
      ["https://www.linkedin.com/feed/", "linkedin"], ["https://news.ycombinator.com/item?id=1", "hn"], ["https://old.reddit.com/r/x", "reddit"],
      ["https://github.com/djhulme1/ecdysis-core", "github"], ["https://www.moltbook.com/post/1", "moltbook"], ["https://chatgpt.com/", "ai"],
      ["https://claude.ai/chat/1", "ai"], ["https://gemini.google.com/app", "ai"], ["https://www.google.co.uk/", "search"],
      ["https://duckduckgo.com/", "search"], ["https://example.org/blog", "other"], ["https://ecdysis.me/people", null],
      ["https://api.ecdysis.me/v1", null], ["not a url", null], [null, null], ["https://x.com.evil.example/", "other"],
    ];
    for (const [ref, want] of cases) assert.equal(referrerBucket(ref), want, String(ref));
  });

  it("counts a person's visit from another site, once, by bucket", async () => {
    const w = await world();
    await w.page("/papers", { referer: "https://t.co/xyz" });
    await w.page("/papers", { referer: "https://ecdysis.me/people" });
    await w.api("GET", "/v1/papers", undefined, { referer: "https://t.co/xyz" });
    assert.equal(await w.store.getAccess(`rf:${w.day()}:x`), 1);
    const growth = (await w.opsGet("/operator/growth")).text;
    assert.match(growth, /<td>X<\/td><td class="num">1<\/td>/);
  });

  it("names claim and agent pages, and counts claim outcomes from a fixed vocabulary", () => {
    assert.equal(pageKeyOf("GET", "/a/Moth-1", "text/html"), "agent-page");
    assert.equal(pageKeyOf("GET", `/claim/${"a".repeat(32)}`, "text/html"), "claim");
    assert.equal(pageKeyOf("GET", "/s/x/paper/ecd%3A2610.abcdef", "text/html"), null, "a share redirect is not a page view");
    assert.deepEqual(stepKeys("claim-verify", 422, "no-code", "2026-10-01"), ["funnel:claim-verify:422", "funnel:claim-verify:422:no-code", "fd:2026-10-01:claim-verify:no"]);
    assert.deepEqual(stepKeys("claim-verify", 200, "verified", "2026-10-01"), ["funnel:claim-verify:200", "fd:2026-10-01:claim-verify:ok"]);
    assert.equal(reasonOf("new submissions are paused by the operator for now"), "paused");
    assert.equal(reasonOf("claim posts are switched off right now; try again later"), "paused");
    assert.equal(reasonOf("claim limit: 10 claim links a day per agent; try again tomorrow"), "claim-limit");
    assert.equal(reasonOf("this exact request was already sent; sign a fresh one"), "duplicate");
  });

  it("keeps crawlers off share and claim addresses", async () => {
    const w = await world();
    const robots = (await w.page("/robots.txt")).text;
    assert.match(robots, /Disallow: \/s\//);
    assert.match(robots, /Disallow: \/claim\//);
  });
});
