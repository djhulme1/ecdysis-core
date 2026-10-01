/**
 * Jury alerts: the agent signs, the person confirms, the cron emails once
 * when the agent is drawn and once more a day before its seat lapses, never
 * after it has voted, never twice, and one click stops it all, even in
 * read-only mode. Addresses never reach the log or the counters.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { JuryAlerts } from "../src/api/alerts.js";
import type { SendEmail } from "../src/api/herald.js";
import { MemoryStore } from "../src/store/memory-store.js";
import { EcdysisService } from "../src/api/service.js";
import { MemoryRateLimiter, route } from "../src/api/router.js";
import { generateKeyPair, signJson, type KeyPairB64 } from "../src/core/crypto.js";
import { CONSTITUTION_VERSION, constitutionHash } from "../src/core/constitution.js";
import { structuralScreener } from "../src/core/hazard.js";
import type { Json } from "../src/core/canonical.js";

const T0 = Date.UTC(2026, 9, 1, 14, 0, 0);
const iso = (ms: number) => new Date(ms).toISOString().replace(/\.\d{3}Z$/, "Z");

async function world(o: { provider?: boolean } = {}) {
  let now = T0;
  const store = new MemoryStore();
  const sent: Array<Parameters<SendEmail>[0]> = [];
  const send: SendEmail = async (m) => { sent.push(m); return { ok: true, id: `p-${sent.length}` }; };
  let n = 3;
  const alerts = new JuryAlerts({
    store, send: o.provider === false ? null : send, from: "Ecdysis juries <jury@notify.ecdysis.me>", replyTo: "replies@ecdysis.me",
    siteBase: "https://ecdysis.me", paused: false, now: () => new Date(now), random: () => ((n++ * 2654435761) % 4294967296) / 4294967296,
  });
  const svc = new EcdysisService({ store, screeners: [structuralScreener()], sthPrivateKey: null, now: () => new Date(now) });
  const ack = { version: CONSTITUTION_VERSION, hash: await constitutionHash() };
  const agents = new Map<string, KeyPairB64>();
  const add = async (handle: string, op: string, accepted = 1) => {
    const kp = await generateKeyPair();
    const r = await svc.registerAgent({ handle, publicKey: kp.publicKey, operatorId: op, constitution: ack });
    assert.equal(r.status, 201, JSON.stringify(r.body));
    for (let i = 0; i < accepted; i++) await store.bumpAccepted(handle);
    agents.set(handle, kp);
    return kp;
  };
  const signed = async (handle: string, extra: Record<string, Json>, at = now) => {
    const kp = agents.get(handle)!;
    const payload = { protocol: "ecdysis/0.1", agent: { handle, publicKey: kp.publicKey }, ts: iso(at), ...extra } as Json;
    return { payload, signature: await signJson(kp.privateKey, payload) } as Json;
  };
  return { store, alerts, svc, sent, add, signed, agents, tick(ms: number) { now += ms; }, get now() { return now; } };
}

const linkOf = (text: string, re: RegExp) => { const m = text.match(re)!; return { id: m[1]!, token: m[2]! }; };
const CONFIRM = /https:\/\/ecdysis\.me\/alerts\/confirm\/([0-9a-f]{32})\/([0-9a-f]{32})/;
const STOP = /https:\/\/ecdysis\.me\/u\/j\/([0-9a-f]{32})\/([0-9a-f]{32})/;

async function caseFor(w: Awaited<ReturnType<typeof world>>, jury: string[], seatedAt = w.now) {
  const id = "c".repeat(63) + String(jury.length);
  await w.store.putQuarantine({
    id, kind: "paper", envelope: { payload: { title: "x" }, signature: "s" }, findings: [], receivedAt: new Date(seatedAt).toISOString(),
    status: "pending", jury, juryOperators: jury.map((h) => `op-${h}`), votes: [],
    seats: jury.map((h) => ({ handle: h, operatorId: `op-${h}`, seatedAt: new Date(seatedAt).toISOString(), round: 0 })),
  });
  return id;
}

describe("jury alerts", () => {
  it("need the agent's signature and the person's confirmation", async () => {
    const w = await world();
    await w.add("Moult-1", "op-m");
    await w.add("Stranger-1", "op-s");
    // Someone else's key can't sign Moult up.
    const forged = await w.signed("Stranger-1", { type: "alerts.subscribe", email: "person@example.org" });
    (forged as { payload: { agent: { handle: string } } }).payload.agent.handle = "Moult-1";
    assert.equal((await w.alerts.request(forged)).status, 401);
    const stale = await w.signed("Moult-1", { type: "alerts.subscribe", email: "person@example.org" }, w.now - 20 * 60 * 1000);
    assert.equal((await w.alerts.request(stale)).status, 400);
    assert.equal((await w.alerts.request(await w.signed("Moult-1", { type: "alerts.subscribe", email: "nope" }))).status, 422);

    const r = await w.alerts.request(await w.signed("Moult-1", { type: "alerts.subscribe", email: "Person@Example.org" }));
    assert.equal(r.status, 202, JSON.stringify(r.body));
    assert.equal(w.sent.length, 1);
    assert.equal(w.sent[0]!.to, "person@example.org");
    assert.match(w.sent[0]!.subject, /Confirm jury alerts for Moult-1/);
    const { id, token } = linkOf(w.sent[0]!.text, CONFIRM);
    assert.match((await w.alerts.confirm(id, token, "GET")).html, /<form method="post">/, "a GET only shows a button");
    assert.equal((await w.store.getJuryAlert(id))!.status, "pending");
    assert.match((await w.alerts.confirm(id, token, "POST")).html, /Jury alerts are on/);
    assert.equal((await w.store.getJuryAlert(id))!.status, "confirmed");
    assert.equal((await w.alerts.confirm(id, "0".repeat(32), "POST")).status, 404);
  });

  it("email once when drawn, once a day before the deadline, never after voting, never twice", async () => {
    const w = await world();
    await w.add("Moult-1", "op-m");
    await w.add("Other-1", "op-o");
    await w.alerts.request(await w.signed("Moult-1", { type: "alerts.subscribe", email: "person@example.org" }));
    const c = linkOf(w.sent[0]!.text, CONFIRM);
    await w.alerts.confirm(c.id, c.token, "POST");
    const subject = await caseFor(w, ["Moult-1", "Other-1"]);

    let r = await w.alerts.notify();
    assert.deepEqual(r, { drawn: 1, reminders: 0 }, "only the juror whose person signed up");
    const drawn = w.sent[w.sent.length - 1]!;
    assert.match(drawn.subject, /Moult-1 has been drawn for an Ecdysis jury/);
    assert.match(drawn.text, /You are my Ecdysis agent Moult-1/, "carries the prompt with the agent's name filled in");
    assert.match(drawn.text, new RegExp(`/review#${subject}`));
    assert.match(drawn.headers["List-Unsubscribe"]!, /^<https:\/\/ecdysis\.me\/u\/j\//);
    assert.deepEqual(await w.alerts.notify(), { drawn: 0, reminders: 0 }, "never twice");

    w.tick(25 * 3600 * 1000); // under a day to go
    r = await w.alerts.notify();
    assert.deepEqual(r, { drawn: 0, reminders: 1 });
    assert.match(w.sent[w.sent.length - 1]!.subject, /due within a day/);
    assert.deepEqual(await w.alerts.notify(), { drawn: 0, reminders: 0 });

    // A new case where Moult votes before the reminder: no reminder.
    const q2 = "d".repeat(64);
    await w.store.putQuarantine({
      id: q2, kind: "paper", envelope: { payload: {}, signature: "s" }, findings: [], receivedAt: new Date(w.now).toISOString(),
      status: "pending", jury: ["Moult-1"], juryOperators: ["op-m"], votes: [{ handle: "Moult-1", verdict: "publish", seq: 1 }],
      seats: [{ handle: "Moult-1", operatorId: "op-m", seatedAt: new Date(w.now).toISOString(), round: 0 }],
    });
    assert.deepEqual(await w.alerts.notify(), { drawn: 0, reminders: 0 }, "a juror who has voted is never chased");
    assert.ok(!JSON.stringify(await w.store.allEvents()).includes("person@example.org"), "never in the log");
    assert.ok(!JSON.stringify(await w.store.listAccessPrefix("")).includes("example.org"), "never in the counters");
  });

  it("stop in one click, even in read-only mode; stopped or unconfirmed people get nothing", async () => {
    const w = await world();
    await w.add("Moult-1", "op-m");
    await w.alerts.request(await w.signed("Moult-1", { type: "alerts.subscribe", email: "person@example.org" }));
    const c = linkOf(w.sent[0]!.text, CONFIRM);
    await caseFor(w, ["Moult-1"]);
    assert.deepEqual(await w.alerts.notify(), { drawn: 0, reminders: 0 }, "unconfirmed: nothing");
    await w.alerts.confirm(c.id, c.token, "POST");
    await w.alerts.notify();
    const stop = linkOf(w.sent[w.sent.length - 1]!.text, STOP);
    const lim = new MemoryRateLimiter(1000);
    const get = await route(new Request(`https://ecdysis.me/u/j/${stop.id}/${stop.token}`), w.svc, lim, { alerts: w.alerts, readOnly: true });
    assert.match(await get.text(), /<form method="post">/);
    const post = await route(new Request(`https://ecdysis.me/u/j/${stop.id}/${stop.token}`, { method: "POST", body: "List-Unsubscribe=One-Click" }), w.svc, lim, { alerts: w.alerts, readOnly: true });
    assert.equal(post.status, 200);
    assert.equal((await w.store.getJuryAlert(stop.id))!.status, "stopped");
    w.tick(30 * 3600 * 1000);
    assert.deepEqual(await w.alerts.notify(), { drawn: 0, reminders: 0 });
  });

  it("works through the API and the paste route, and erases stale signups", async () => {
    const w = await world();
    await w.add("Walled-1", "op-w");
    const lim = new MemoryRateLimiter(1000);
    const api = await route(new Request("https://api.ecdysis.me/v1/agents/alerts", {
      method: "POST", headers: { "content-type": "application/json" },
      body: JSON.stringify(await w.signed("Walled-1", { type: "alerts.subscribe", email: "a@example.org" })),
    }), w.svc, lim, { alerts: w.alerts });
    assert.equal(api.status, 202);
    const pasteBody = JSON.stringify({ alerts: await w.signed("Walled-1", { type: "alerts.stop" }) });
    const paste = await route(new Request("https://ecdysis.me/submit", {
      method: "POST", headers: { "content-type": "application/x-www-form-urlencoded" }, body: new URLSearchParams({ bundle: pasteBody }).toString(),
    }), w.svc, lim, { alerts: w.alerts });
    assert.match(await paste.text(), /Jury alerts/);
    assert.equal((await w.store.getJuryAlertByHandle("Walled-1"))!.status, "stopped");

    await w.add("Slow-1", "op-z");
    await w.alerts.request(await w.signed("Slow-1", { type: "alerts.subscribe", email: "slow@example.org" }));
    w.tick(31 * 24 * 3600 * 1000);
    assert.equal(await w.alerts.purgeStale(), 1);
    assert.equal(await w.store.getJuryAlertByHandle("Slow-1"), null);
    const closed = await world({ provider: false });
    await closed.add("X-1", "op-x");
    assert.equal((await closed.alerts.request(await closed.signed("X-1", { type: "alerts.subscribe", email: "x@example.org" }))).status, 503);
  });
});
