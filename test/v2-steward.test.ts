/**
 * The stewardship area: two locks (Cloudflare Access when configured, a
 * signed-in steward), step-up for acts, and every act on the log with the
 * steward's operator id. Reserved power R1 is not here: holds are listed,
 * never released.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { MemoryStore } from "../src/store/memory-store.js";
import { TransparencyLog } from "../src/core/log.js";
import { generateKeyPair, signJson, type KeyPairB64 } from "../src/core/crypto.js";
import { MemoryV2Store, V2Service } from "../src/api/v2/service.js";
import { Accounts, MemoryAccountStore } from "../src/api/v2/accounts.js";
import { StewardHandler } from "../src/api/v2/steward.js";
import { sha256Hex } from "../src/api/access.js";
import type { Bundle, Outputs } from "../src/core/v2/receipts.js";
import type { Json } from "../src/core/canonical.js";

const MIN = 60 * 1000;

async function world() {
  const clock = { t: Date.UTC(2026, 9, 3, 9, 0, 0) };
  const now = () => new Date(clock.t);
  const logStore = new MemoryStore();
  const log = new TransparencyLog(logStore, now);
  const logKey = await generateKeyPair();
  const v2store = new MemoryV2Store(() => (logStore as unknown as { log: Array<{ entry: { seq: number; ts: string; type: string }; payload: Json }> }).log.map((r) => ({ seq: r.entry.seq, ts: r.entry.ts, type: r.entry.type, payload: r.payload })));
  const sent: string[] = [];
  const accounts = new Accounts({
    store: new MemoryAccountStore(), key: "ab".repeat(32), send: async (m) => { sent.push(m.text); return { ok: true, id: "m" }; },
    from: "a@notify.ecdysis.me", replyTo: "replies@ecdysis.me", siteBase: "https://ecdysis.me", stewardEmailHashes: [await sha256Hex("daniel@example.org")], now,
  });
  const svc = new V2Service({ log, store: v2store, logPrivateKey: logKey.privateKey, now, pairing: (c, ip) => accounts.consumePairing(c, ip) });
  const steward = new StewardHandler({ accounts, v2: svc, access: null, now });
  const keys = new Map<string, KeyPairB64>();
  const agent = async (handle: string, op: string, models?: string[], tier: "account" | "verified" | null = "verified") => {
    const kp = await generateKeyPair();
    keys.set(handle, kp);
    assert.equal((await svc.registerAgent({ handle, publicKey: kp.publicKey, operatorId: op, ...(models ? { models } : {}) })).status, 201);
    if (tier) await svc.setTier(op, tier);
    return kp;
  };
  const ts = () => now().toISOString().replace(/\.\d{3}Z$/, "Z");
  const sign = async (handle: string, payload: Record<string, Json>) => {
    const kp = keys.get(handle)!;
    const full: Json = { ...payload, agent: { handle, publicKey: kp.publicKey }, ts: ts() };
    return { payload: full, signature: await signJson(kp.privateKey, full) } as Json;
  };
  const bundle = (n: number): Bundle => ({ repo: "https://github.com/example/rep", commit: n.toString(16).padStart(40, "0"), image: "sha256:" + "a".repeat(64), run: "python run.py", outputs: [{ name: "alpha", tolerance: 0.01 }, { name: "solver" }], runtimeMinutes: 5 });
  const commit = async (handle: string, target: string, b: Bundle) => svc.commitCheck(await sign(handle, { protocol: "ecdysis/0.2", type: "check.commit", target, kind: "replication", bundle: b as unknown as Json }));
  const result = async (handle: string, id: string, outcome: string, outputs: Outputs, cross: { receipt: string; outputs: Outputs } | null) =>
    svc.fileResult(await sign(handle, { protocol: "ecdysis/0.2", type: "check.result", commit: id, outcome, outputs, crossCheck: cross as unknown as Json }));
  const signIn = async (email: string) => {
    const b = "browser-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
    const r = await accounts.requestLink(email, "1.1.1.1", b);
    assert.ok(r.ok);
    const c = await accounts.completeLink(sent.at(-1)!.match(/t=([A-Za-z0-9_-]+)/)![1]!, b, "1.1.1.1");
    assert.ok(c.ok);
    return c;
  };
  const get = (path: string, session: string | null) => steward.handle(new Request(`https://ecdysis.me${path}`, { headers: session ? { cookie: `ecd_s=${session}` } : {} }), path.split("?")[0]!);
  const post = (path: string, form: Record<string, string>, session: string) => {
    const p = new URLSearchParams(form).toString();
    return steward.handle(new Request(`https://ecdysis.me${path}`, { method: "POST", body: p, headers: { "content-type": "application/x-www-form-urlencoded", "content-length": String(p.length), cookie: `ecd_s=${session}` } }), path);
  };
  const idOf = (r: { body: Json }) => String((r.body as Record<string, Json>)["id"]);
  return { svc, accounts, steward, agent, sign, commit, result, bundle, signIn, get, post, idOf, tick: (ms: number) => { clock.t += ms; }, keys, log };
}

describe("the stewardship area", () => {
  it("admits only a signed-in steward, and only through Access when Access is configured", async () => {
    const w = await world();
    assert.equal((await w.get("/steward", null)).status, 401);
    const member = await w.signIn("someone@example.org");
    assert.equal((await w.get("/steward", member.session)).status, 403);
    const d = await w.signIn("daniel@example.org");
    assert.equal((await w.get("/steward", d.session)).status, 200);
    // With Access configured, the header is required even for a steward.
    const locked = new StewardHandler({ accounts: w.accounts, v2: w.svc, access: { teamDomain: "team.cloudflareaccess.com", aud: "a".repeat(64), emailHashes: [await sha256Hex("daniel@example.org")], host: "ecdysis.me" } });
    const r = await locked.handle(new Request("https://ecdysis.me/steward", { headers: { cookie: `ecd_s=${d.session}` } }), "/steward");
    assert.equal(r.status, 403);
    assert.match(await r.text(), /Cloudflare Access/);
  });

  it("people: lists operators by id and handle, sets tiers with step-up, and the act is on the log under the steward's operator id", async () => {
    const w = await world();
    await w.agent("Ant", "op-a", ["claude"], null);
    await w.agent("Bee", "op-b", ["gpt"], "account");
    const d = await w.signIn("daniel@example.org");
    let res = await w.get("/steward/people?q=ant", d.session);
    let html = await res.text();
    assert.match(html, /op-a/);
    assert.doesNotMatch(html, /op-b/);
    res = await w.get("/steward/people", d.session);
    html = await res.text();
    assert.match(html, /op-b/);
    assert.doesNotMatch(html, /example\.org/, "never an email");
    const csrf = html.match(/name="csrf" value="([0-9a-f]{40})"/)![1]!;
    assert.equal((await w.post("/steward/people/tier", { operatorId: "op-a", tier: "verified" }, d.session)).status, 200, "no token: refused (page with the problem)");
    res = await w.post("/steward/people/tier", { csrf, operatorId: "op-a", tier: "verified" }, d.session);
    assert.equal(res.status, 303);
    const rec = await w.svc.record();
    assert.equal(rec.tiers.get("op-a"), "verified");
    const rows = (await w.svc.audit()).filter((x) => x.type === "operator.tier");
    assert.equal(rows.length, 1);
    assert.equal(rows[0]!.by, "steward");
    assert.equal(rows[0]!.steward, d.account.operatorId);
    assert.equal((await w.post("/steward/people/tier", { csrf, operatorId: "op-a", tier: "verified" }, d.session)).status, 200, "already at that tier: shown as a problem");
    assert.equal((await w.post("/steward/people/tier", { csrf, operatorId: "op-a", tier: "king" }, d.session)).status, 200);
    assert.equal((await w.svc.record()).tiers.get("op-a"), "verified");
    w.tick(11 * MIN);
    res = await w.post("/steward/people/tier", { csrf, operatorId: "op-a", tier: "account" }, d.session);
    assert.equal(res.status, 401, "step-up");
    assert.equal((await w.svc.record()).tiers.get("op-a"), "verified");
    html = await (await w.get("/steward/audit", d.session)).text();
    assert.match(html, /operator\.tier/);
  });

  it("evidence: shows findings and disputes, and a reversal restores what a finding voided", async () => {
    const w = await world();
    await w.agent("Ant", "op-a", ["claude"]);
    await w.agent("Liar", "op-l", ["gpt"]);
    await w.agent("Cat", "op-c", ["gemini"]);
    await w.agent("Dog", "op-d", ["grok"]);
    await w.agent("Emu", "op-e", ["mistral"]);
    const ext = await w.svc.registerExternalClaim(await w.sign("Ant", { protocol: "ecdysis/0.2", type: "claim.external", source: "arxiv:1706.03762", quote: "attention alone reaches 28.4 BLEU on WMT14 En-De", test: "BLEU below 27 with the stated setup" }));
    const ref = String((ext.body as Record<string, Json>)["ref"]);
    const liar = await w.commit("Liar", ref, w.bundle(1));
    const idL = w.idOf(liar);
    await w.result("Liar", idL, "confirmed", { alpha: 28.4, solver: "x" }, null);
    let finding: Record<string, Json> = {};
    for (const [h, n] of [["Cat", 2], ["Dog", 3], ["Emu", 4]] as const) {
      const c = await w.commit(h, ref, w.bundle(n));
      const r = await w.result(h, w.idOf(c), "failed", { alpha: 26.1 + n / 10, solver: "y" }, { receipt: idL, outputs: { alpha: 26.0, solver: "x" } });
      finding = (r.body as Record<string, Json>)["finding"] as Record<string, Json>;
    }
    assert.equal(finding["verdict"], "fabrication");
    const d = await w.signIn("daniel@example.org");
    let html = await (await w.get("/steward/evidence", d.session)).text();
    assert.match(html, /fabrication/);
    assert.match(html, /Liar/);
    assert.match(html, /appeal open until/);
    html = await (await w.get("/steward", d.session)).text();
    assert.match(html, /1 finding in the appeal window/);
    w.tick(15 * 24 * 60 * MIN);
    assert.deepEqual([...(await w.svc.record()).voidedOperators], ["op-l"]);
    // Sign in again for step-up, then reverse.
    const d2 = await w.signIn("daniel@example.org");
    html = await (await w.get("/steward/evidence", d2.session)).text();
    assert.match(html, /in force/);
    const csrf = html.match(/name="csrf" value="([0-9a-f]{40})"/)![1]!;
    const res = await w.post("/steward/evidence/reverse", { csrf, id: String(finding["id"]) }, d2.session);
    assert.equal(res.status, 303);
    const rec = await w.svc.record();
    assert.equal(rec.voidedOperators.size, 0);
    assert.equal(rec.findings[0]!.reversed, true);
    const acts = await w.svc.audit();
    assert.equal(acts[0]!.type, "finding.reverse");
    assert.equal(acts[0]!.steward, d2.account.operatorId);
    assert.equal((await w.post("/steward/evidence/reverse", { csrf, id: String(finding["id"]) }, d2.session)).status, 200, "already reversed: a problem, not a change");
  });

  it("content: lists hazard holds from escalations, and offers no way to release them", async () => {
    const w = await world();
    await w.agent("Ant", "op-a", ["claude"]);
    await w.agent("Bee", "op-b", ["gpt"]);
    const ext = await w.svc.registerExternalClaim(await w.sign("Ant", { protocol: "ecdysis/0.2", type: "claim.external", source: "arxiv:1706.03762", quote: "attention alone reaches 28.4 BLEU on WMT14 En-De", test: "BLEU below 27 with the stated setup" }));
    const ref = String((ext.body as Record<string, Json>)["ref"]);
    const esc = await w.svc.escalate(await w.sign("Bee", { protocol: "ecdysis/0.2", type: "hazard.escalate", subject: ref, reason: "The quoted claim links to material that should be looked at by a person before it spreads." }));
    assert.equal(esc.status, 202);
    const d = await w.signIn("daniel@example.org");
    const html = await (await w.get("/steward/content", d.session)).text();
    assert.match(html, /hazard\.hold/);
    assert.match(html, /op-b/);
    assert.match(html, /open/);
    assert.doesNotMatch(html, /action="\/steward\/content/, "no form acts on a hold");
    assert.equal((await w.post("/steward/content/release", { csrf: "x" }, d.session)).status, 200, "no such act exists; the page shows a problem and nothing changes");
    assert.equal((await w.svc.holds()).filter((h) => h.open).length, 1);
  });
});
