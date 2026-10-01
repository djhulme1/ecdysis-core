/**
 * The Herald: author emails from Ecdysis.
 *
 * Guarantees: nothing is drafted or sent without the approver key; plain
 * text with a one-click unsubscribe; the suppression list is honoured
 * before every send and forever; daily caps; a pause switch; recipient
 * addresses never reach the public log or the counters; unsubscribing works
 * even in read-only mode.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { Herald, HERALD_DOMAIN_CAP, type SendEmail } from "../src/api/herald.js";
import { MemoryStore } from "../src/store/memory-store.js";
import { EcdysisService } from "../src/api/service.js";
import { MemoryRateLimiter, route } from "../src/api/router.js";
import { generateKeyPair, signJson, type KeyPairB64 } from "../src/core/crypto.js";
import { structuralScreener } from "../src/core/hazard.js";
import type { Json } from "../src/core/canonical.js";

const NOW = Date.UTC(2026, 9, 1, 13, 0, 0);
const iso = (ms: number) => new Date(ms).toISOString().replace(/\.\d{3}Z$/, "Z");

function seq() {
  let i = 0;
  return () => ((i++ * 2654435761) % 4294967296) / 4294967296;
}

async function world(o: { paused?: boolean; provider?: boolean } = {}) {
  const store = new MemoryStore();
  const approver = await generateKeyPair();
  const sent: Array<Parameters<SendEmail>[0]> = [];
  const send: SendEmail = async (m) => { sent.push(m); return { ok: true, id: `prov-${sent.length}` }; };
  const herald = new Herald({
    store, approverPublicKey: approver.publicKey, send: o.provider === false ? null : send,
    from: "Ecdysis <herald@notify.ecdysis.me>", replyTo: "replies@ecdysis.me", siteBase: "https://ecdysis.me",
    paused: !!o.paused, now: () => new Date(NOW), random: seq(),
  });
  const svc = new EcdysisService({ store, screeners: [structuralScreener()], sthPrivateKey: null, now: () => new Date(NOW) });
  return { store, approver, herald, sent, svc };
}

async function signed(kp: KeyPairB64, payload: Record<string, Json>) {
  const p = { ...payload, ts: iso(NOW) } as Json;
  return { payload: p, signature: await signJson(kp.privateKey, p) } as Json;
}

const BODY = "Dear Professors Miller and Sanjurjo,\n\nAn independent AI agent has re-run your streak-selection analysis and it reproduced. The record is at https://ecdysis.me/p/ecd:2610.3qjqtw.";

async function draft(w: Awaited<ReturnType<typeof world>>, to = "author@example.edu") {
  const r = await w.herald.draft(await signed(w.approver, { type: "herald.draft", to, subject: "Your result was independently reproduced", body: BODY, kind: "replication", workId: "arxiv:1902.01265", paperId: "ecd:2610.3qjqtw" }));
  return r;
}

describe("the Herald", () => {
  it("drafts and sends only with the approver key, as plain text with a one-click unsubscribe", async () => {
    const w = await world();
    const stranger = await generateKeyPair();
    const forged = await w.herald.draft(await signed(stranger, { type: "herald.draft", to: "a@example.edu", subject: "Hello there", body: BODY, kind: "replication" }));
    assert.equal(forged.status, 401);

    const d = await draft(w);
    assert.equal(d.status, 201, JSON.stringify(d.body));
    const id = (d.body as Record<string, string>).id!;
    assert.match((d.body as Record<string, string>).preview!, /never receive email from Ecdysis: https:\/\/ecdysis\.me\/u\/[0-9a-f]{32}\/[0-9a-f]{32}/);
    assert.equal(w.sent.length, 0, "drafting sends nothing");

    const s = await w.herald.send(await signed(w.approver, { type: "herald.send", id }));
    assert.equal(s.status, 200, JSON.stringify(s.body));
    assert.equal(w.sent.length, 1);
    const m = w.sent[0]!;
    assert.equal(m.to, "author@example.edu");
    assert.equal(m.replyTo, "replies@ecdysis.me");
    assert.match(m.headers["List-Unsubscribe"]!, /^<https:\/\/ecdysis\.me\/u\//);
    assert.equal(m.headers["List-Unsubscribe-Post"], "List-Unsubscribe=One-Click");
    assert.ok(!/<a |<img|<html/i.test(m.text), "plain text");
    assert.equal((await w.herald.send(await signed(w.approver, { type: "herald.send", id }))).status, 409, "never sent twice");
  });

  it("refuses HTML, bad addresses and stale requests", async () => {
    const w = await world();
    const html = await w.herald.draft(await signed(w.approver, { type: "herald.draft", to: "a@example.edu", subject: "Hello there", body: BODY + " <a href='x'>click</a>", kind: "replication" }));
    assert.equal(html.status, 422);
    const bad = await w.herald.draft(await signed(w.approver, { type: "herald.draft", to: "not an address", subject: "Hello there", body: BODY, kind: "replication" }));
    assert.equal(bad.status, 422);
    const p = { type: "herald.list", ts: iso(NOW - 20 * 60 * 1000) } as Json;
    const stale = await w.herald.list({ payload: p, signature: await signJson(w.approver.privateKey, p) } as Json);
    assert.equal(stale.status, 400);
  });

  it("an unsubscribe is honoured forever, before every send, and works in read-only mode", async () => {
    const w = await world();
    const d1 = (await draft(w)).body as Record<string, string>;
    const d2 = (await draft(w)).body as Record<string, string>;
    const link = d1.preview!.match(/https:\/\/ecdysis\.me(\/u\/[0-9a-f]{32}\/[0-9a-f]{32})/)![1]!;
    const get = await route(new Request(`https://ecdysis.me${link}`, { headers: { accept: "text/html" } }), w.svc, new MemoryRateLimiter(100), { herald: w.herald });
    assert.match(await get.text(), /<form method="post">/, "a GET only shows a button, so link scanners can't unsubscribe anyone");
    assert.equal(await w.store.isSuppressed("author@example.edu"), false);
    const post = await route(new Request(`https://ecdysis.me${link}`, { method: "POST", body: "List-Unsubscribe=One-Click" }), w.svc, new MemoryRateLimiter(100), { herald: w.herald, readOnly: true });
    assert.equal(post.status, 200, "honoured even in read-only mode");
    assert.equal(await w.store.isSuppressed("AUTHOR@example.edu"), true, "case-insensitive");
    const s = await w.herald.send(await signed(w.approver, { type: "herald.send", id: d2.id! }));
    assert.equal(s.status, 409, "the second draft is never sent");
    assert.equal(w.sent.length, 0);
    assert.equal((await draft(w)).status, 409, "nor can a new one be drafted");
    const wrong = await route(new Request(`https://ecdysis.me/u/${"0".repeat(32)}/${"1".repeat(32)}`, { method: "POST" }), w.svc, new MemoryRateLimiter(100), { herald: w.herald });
    assert.equal(wrong.status, 404);
  });

  it("caps sends per domain, pauses on demand, and refuses without a provider", async () => {
    const w = await world();
    for (let i = 0; i < HERALD_DOMAIN_CAP; i++) {
      const id = ((await draft(w, `a${i}@example.edu`)).body as Record<string, string>).id!;
      assert.equal((await w.herald.send(await signed(w.approver, { type: "herald.send", id }))).status, 200);
    }
    const over = ((await draft(w, "z@example.edu")).body as Record<string, string>).id!;
    assert.equal((await w.herald.send(await signed(w.approver, { type: "herald.send", id: over }))).status, 429);
    const other = ((await draft(w, "x@other.org")).body as Record<string, string>).id!;
    assert.equal((await w.herald.send(await signed(w.approver, { type: "herald.send", id: other }))).status, 200, "other domains unaffected");

    const p = await world({ paused: true });
    const pid = ((await draft(p)).body as Record<string, string>).id!;
    assert.equal((await p.herald.send(await signed(p.approver, { type: "herald.send", id: pid }))).status, 503);
    const n = await world({ provider: false });
    const nid = ((await draft(n)).body as Record<string, string>).id!;
    assert.equal((await n.herald.send(await signed(n.approver, { type: "herald.send", id: nid }))).status, 501);
  });

  it("addresses never reach the public log or the counters", async () => {
    const w = await world();
    const id = ((await draft(w)).body as Record<string, string>).id!;
    const r = await route(new Request("https://api.ecdysis.me/v1/herald/send", {
      method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(await signed(w.approver, { type: "herald.send", id })),
    }), w.svc, new MemoryRateLimiter(100), { herald: w.herald });
    assert.equal(r.status, 200);
    const events = await w.store.allEvents();
    assert.ok(!JSON.stringify(events).includes("author@example.edu"), "not in the log");
    const counters = await w.store.listAccessPrefix("funnel:");
    assert.ok(counters.some((c) => c.id === "funnel:herald:200"));
    assert.ok(!JSON.stringify(counters).includes("example.edu"), "not in the counters");
  });
});
