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
import { CanaryRegistry, MemoryCanaryStore } from "../src/api/v2/canaries.js";
import { sha256Hex } from "../src/api/access.js";
import type { Bundle, Outputs } from "../src/core/v2/receipts.js";
import type { Json } from "../src/core/canonical.js";
import { CONSTITUTION_VERSION, constitutionHash } from "../src/core/constitution.js";
const ACK = { version: CONSTITUTION_VERSION, hash: await constitutionHash() };

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
  const canaryStore = new MemoryCanaryStore();
  const canaries = new CanaryRegistry({ store: canaryStore, accounts, v2: svc, now });
  const steward = new StewardHandler({ accounts, v2: svc, access: null, now, canaries });
  const keys = new Map<string, KeyPairB64>();
  const agent = async (handle: string, op: string, models?: string[], tier: "account" | "verified" | null = "verified") => {
    const kp = await generateKeyPair();
    keys.set(handle, kp);
    assert.equal((await svc.registerAgent({ constitution: ACK, handle, publicKey: kp.publicKey, operatorId: op, ...(models ? { models } : {}) })).status, 201);
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
    return steward.handle(new Request(`https://ecdysis.me${path}`, { method: "POST", body: p, headers: { "content-type": "application/x-www-form-urlencoded", "content-length": String(p.length), cookie: `ecd_s=${session}`, origin: "https://ecdysis.me" } }), path);
  };
  const idOf = (r: { body: Json }) => String((r.body as Record<string, Json>)["id"]);
  return { svc, accounts, steward, canaries, canaryStore, agent, sign, commit, result, bundle, signIn, get, post, idOf, tick: (ms: number) => { clock.t += ms; }, keys, log };
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
    // Access present but half-configured (no audience, say) fails closed rather than silently dropping the lock.
    const half = new StewardHandler({ accounts: w.accounts, v2: w.svc, access: { teamDomain: "team.cloudflareaccess.com", aud: "", emailHashes: [], host: "ecdysis.me" } });
    const h = await half.handle(new Request("https://ecdysis.me/steward", { headers: { cookie: `ecd_s=${d.session}` } }), "/steward");
    assert.equal(h.status, 503);
    assert.match(await h.text(), /not fully configured/);
    // A cross-site POST is refused before anything is read.
    const csrf = (await (await w.get("/steward/evidence", d.session)).text()).match(/name="csrf" value="([0-9a-f]{40})"/)![1]!;
    const p = new URLSearchParams({ csrf, operatorId: "op-x", tier: "verified" }).toString();
    const cross = await w.steward.handle(new Request("https://ecdysis.me/steward/people/tier", { method: "POST", body: p, headers: { "content-type": "application/x-www-form-urlencoded", "content-length": String(p.length), cookie: `ecd_s=${d.session}`, origin: "https://evil.example" } }), "/steward/people/tier");
    assert.equal(cross.status, 403);
    assert.match(await cross.text(), /did not come from this site/);
    // The role is read from the list as it stands: struck off, a steward's open session stops working at once.
    const struck = new StewardHandler({ accounts: new Accounts({ store: w.accounts["o"].store, key: "ab".repeat(32), send: null, from: "a@notify.ecdysis.me", replyTo: "r@ecdysis.me", siteBase: "https://ecdysis.me", stewardEmailHashes: [], now: () => new Date() }), v2: w.svc, access: null });
    assert.equal((await struck.handle(new Request("https://ecdysis.me/steward", { headers: { cookie: `ecd_s=${d.session}` } }), "/steward")).status, 403);
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
    // Not their own operator: a steward cannot verify themselves.
    assert.equal((await w.post("/steward/people/tier", { csrf, operatorId: d.account.operatorId, tier: "verified" }, d.session)).status, 200, "shown as a problem");
    assert.notEqual((await w.svc.record()).tiers.get(d.account.operatorId), "verified");
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

  it("canaries: a private registry with sealed outcomes, revealed from the registry with the outcome recorded at planting", async () => {
    const w = await world();
    await w.agent("Ant", "op-a", ["claude"]);
    await w.agent("Bee", "op-b", ["gpt"]);
    const ext = await w.svc.registerExternalClaim(await w.sign("Ant", { protocol: "ecdysis/0.2", type: "claim.external", source: "doi:10.1000/known", quote: "the site percolation threshold of the square lattice is 0.5927", test: "a fresh estimate outside 0.59 to 0.60" }));
    const ref = String((ext.body as Record<string, Json>)["ref"]);
    const other = await w.svc.registerExternalClaim(await w.sign("Ant", { protocol: "ecdysis/0.2", type: "claim.external", source: "doi:10.1000/other", quote: "an ordinary external claim that is no canary", test: "a fresh run disagrees" }));
    const otherRef = String((other.body as Record<string, Json>)["ref"]);
    const d = await w.signIn("daniel@example.org");
    let html = await (await w.get("/steward/canaries", d.session)).text();
    assert.match(html, /No canaries registered/);
    const csrf = html.match(/name="csrf" value="([0-9a-f]{40})"/)![1]!;
    // Refusals: not an external claim, not on the record, a bad outcome, a bad date.
    assert.match(await (await w.post("/steward/canaries/register", { csrf, claim: "ecd:2610.abcdef#C1", outcome: "confirmed", label: "x" }, d.session)).text(), /a canary is an external claim/);
    assert.match(await (await w.post("/steward/canaries/register", { csrf, claim: "ext:0000000000000000#C1", outcome: "confirmed", label: "x" }, d.session)).text(), /no such claim on the record/);
    assert.match(await (await w.post("/steward/canaries/register", { csrf, claim: ref, outcome: "maybe", label: "x" }, d.session)).text(), /outcome: confirmed/);
    assert.match(await (await w.post("/steward/canaries/register", { csrf, claim: ref, outcome: "confirmed", label: "x", revealAfter: "soon" }, d.session)).text(), /reveal after: a date/);
    // Registered: the outcome is sealed in the store, opened only for the steward's page.
    let res = await w.post("/steward/canaries/register", { csrf, claim: ref, outcome: "confirmed", label: "B2 square-lattice percolation", source: "Newman & Ziff 2000", revealAfter: "2026-12-01" }, d.session);
    assert.equal(res.status, 303, await res.text());
    const row = (await w.canaryStore.list())[0]!;
    assert.equal(row.claim, ref);
    assert.doesNotMatch(row.sealed, /confirmed|percolation|Newman/, "the store holds nothing readable");
    assert.equal(row.revealAfter, "2026-12-01T00:00:00.000Z");
    assert.equal(row.registeredBy, d.account.operatorId);
    assert.match(await (await w.post("/steward/canaries/register", { csrf, claim: ref, outcome: "refuted", label: "again" }, d.session)).text(), /already in the registry/);
    html = await (await w.get("/steward/canaries", d.session)).text();
    assert.match(html, /B2 square-lattice percolation/);
    assert.match(html, /known to hold/);
    assert.match(html, /Newman &amp; Ziff 2000/);
    assert.match(html, /<span class="status sound">live<\/span>/);
    assert.match(html, /<td>0<\/td>/, "no reports yet");
    assert.doesNotMatch(html, new RegExp(otherRef.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")), "the other external claim is no canary");
    // Nothing public tells the canary apart: its page and the record say nothing.
    const { PagesHandler } = await import("../src/api/v2/pages.js");
    const pub = await (await new PagesHandler(w.svc).handle("GET", `/x/${ref.slice(4, 20)}/C1`))!.text();
    assert.doesNotMatch(pub, /canary|known to/);
    assert.equal((await w.svc.record()).anchors.size, 0);
    // A report comes in; the registry counts it. Then the date passes: the overview says one canary is due.
    const c = await w.commit("Bee", ref, w.bundle(1));
    await w.result("Bee", w.idOf(c), "confirmed", { alpha: 0.5927, solver: "x" }, null);
    html = await (await w.get("/steward/canaries", d.session)).text();
    assert.match(html, /<td>1<\/td>\s*<td>1 Dec 2026/);
    assert.match(await (await w.get("/steward", d.session)).text(), /0 canaries due for reveal/);
    w.tick(60 * 24 * 60 * MIN);
    const d2 = await w.signIn("daniel@example.org");
    assert.match(await (await w.get("/steward", d2.session)).text(), /1 canary due for reveal/);
    html = await (await w.get("/steward/canaries", d2.session)).text();
    assert.match(html, /<span class="status risk">due<\/span>/);
    const csrf2 = html.match(/name="csrf" value="([0-9a-f]{40})"/)![1]!;
    // Reveal from the registry: the sealed outcome goes to the log under the steward's id; a second reveal is refused.
    res = await w.post("/steward/canaries/reveal", { csrf: csrf2, claim: ref }, d2.session);
    assert.equal(res.status, 303, await res.text());
    assert.match(res.headers.get("location")!, /1%20report%20on%20this%20claim%20is%20now%20scored/);
    const rec = await w.svc.record();
    assert.equal(rec.anchors.get(ref), true);
    const acts = await w.svc.audit();
    assert.equal(acts[0]!.type, "canary.reveal");
    assert.equal(acts[0]!.steward, d2.account.operatorId);
    assert.match(await (await w.post("/steward/canaries/reveal", { csrf: csrf2, claim: ref }, d2.session)).text(), /already revealed/);
    html = await (await w.get("/steward/canaries", d2.session)).text();
    assert.match(html, /<td>revealed /);
    assert.doesNotMatch(html, /Reveal now/);
    // Forget: the registry row goes, the log keeps the reveal.
    assert.equal((await w.post("/steward/canaries/remove", { csrf: csrf2, claim: ref }, d2.session)).status, 303);
    assert.equal((await w.canaryStore.list()).length, 0);
    assert.equal((await w.svc.record()).anchors.get(ref), true);
    // A member, or a visitor, sees none of this.
    const m = await w.signIn("member@example.org");
    assert.equal((await w.get("/steward/canaries", m.session)).status, 403);
    assert.equal((await w.get("/steward/canaries", null)).status, 401);
    // Without a registry configured, the page does not exist.
    const bare = new StewardHandler({ accounts: w.accounts, v2: w.svc, access: null });
    assert.equal((await bare.handle(new Request("https://ecdysis.me/steward/canaries", { headers: { cookie: `ecd_s=${d2.session}` } }), "/steward/canaries")).status, 404);
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
