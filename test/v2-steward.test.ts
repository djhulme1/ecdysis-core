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
    // The steward's pages send a same-origin referrer policy (never no-referrer, under which browsers post
    // `Origin: null` to the page's own forms); and a post as Chrome made it under the old policy goes through.
    const page = await w.get("/steward/people", d.session);
    assert.equal(page.headers.get("referrer-policy"), "same-origin");
    const asChrome = await w.steward.handle(new Request("https://ecdysis.me/steward/people/tier", { method: "POST", body: p, headers: { "content-type": "application/x-www-form-urlencoded", "content-length": String(p.length), cookie: `ecd_s=${d.session}`, origin: "null", "sec-fetch-site": "same-origin" } }), "/steward/people/tier");
    assert.notEqual(asChrome.status, 403, "a same-origin post with Origin null is not refused as foreign");
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
    assert.doesNotMatch(html, /someone@example\.org|other@example\.org/, "never anyone else's email");
    // The page says what mode it is in and who is signed in, as the v1 console did ("Operator"): a tag beside the brand, the address, the word.
    assert.match(html, /<span class="tag">Steward<\/span>/);
    assert.match(html, /Signed in as daniel@example\.org · steward mode/);
    assert.match(html, /<a class="me" href="\/me">Your Ecdysis<\/a>/, "the person's own page is in the top bar");
    assert.match(html, /Steward mode: these pages are private to signed-in stewards/);
    assert.match(await (await w.get("/steward/audit", d.session)).text(), /<span class="tag">Steward<\/span>/, "every steward page carries the tag");
    const { PagesHandler: PublicPages } = await import("../src/api/v2/pages.js");
    assert.doesNotMatch(await (await new PublicPages(w.svc).handle("GET", "/papers"))!.text(), /class="tag"|Signed in as/, "public pages carry neither");
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
    assert.match(row.key, /^[0-9a-f]{40}$/, "the row is keyed by a keyed hash of the claim");
    assert.doesNotMatch(JSON.stringify(row), new RegExp(`confirmed|percolation|Newman|${ref.slice(4, 20)}`), "the store holds nothing readable, not even which claim");
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
    // A sealed blob moved to another row does not open: the seal is bound to the row key, and the ref inside must hash to it.
    const moved = { ...row, key: "f".repeat(40) };
    await w.canaryStore.put(moved);
    const views = await w.canaries.list();
    assert.equal(views.find((v) => v.key === moved.key)!.secret, null, "the moved blob opens to nothing");
    assert.match(await (await w.post("/steward/canaries/reveal", { csrf: csrf2, key: moved.key }, d2.session)).text(), /cannot be opened/);
    assert.equal((await w.svc.record()).anchors.size, 0, "and nothing was revealed");
    html = await (await w.get("/steward/canaries", d2.session)).text();
    assert.match(html, /sealed entry cannot be opened/);
    assert.match(html, /<td><b>unknown<\/b><\/td>/, "an unopenable row shows no outcome");
    await w.canaryStore.delete(moved.key);
    // Reveal from the registry: the sealed outcome goes to the log under the steward's id; a second reveal is refused.
    res = await w.post("/steward/canaries/reveal", { csrf: csrf2, key: row.key }, d2.session);
    assert.equal(res.status, 303, await res.text());
    assert.match(res.headers.get("location")!, /1%20report%20on%20this%20claim%20is%20now%20scored/);
    const rec = await w.svc.record();
    assert.equal(rec.anchors.get(ref), true);
    const acts = await w.svc.audit();
    assert.equal(acts[0]!.type, "canary.reveal");
    assert.equal(acts[0]!.steward, d2.account.operatorId);
    assert.match(await (await w.post("/steward/canaries/reveal", { csrf: csrf2, key: row.key }, d2.session)).text(), /already revealed/);
    html = await (await w.get("/steward/canaries", d2.session)).text();
    assert.match(html, /<td>revealed /);
    assert.doesNotMatch(html, /Reveal now/);
    // Forget: the registry row goes, the log keeps the reveal.
    assert.equal((await w.post("/steward/canaries/remove", { csrf: csrf2, key: row.key }, d2.session)).status, 303);
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

  it("agents: every agent by tier and family, filtered, read-only", async () => {
    const w = await world();
    await w.agent("Ant", "op-a", ["claude"]);
    await w.agent("Bee", "op-b", ["gpt", "claude"], "account");
    await w.agent("Cat", "op-c", undefined, null);
    const d = await w.signIn("daniel@example.org");
    let html = await (await w.get("/steward/agents", d.session)).text();
    assert.match(html, /3 agents on the record/);
    assert.match(html, /claude 2 · gpt 1 · undeclared 1|claude 2 · undeclared 1 · gpt 1/);
    assert.match(html, /<a href="\/a\/Ant">Ant<\/a>/);
    assert.match(html, /<td>verified<\/td>/);
    assert.match(html, /<td>account<\/td>/);
    assert.match(html, /<td>unverified<\/td>/);
    assert.doesNotMatch(html, /<form method="post"/, "read-only: no acts here");
    html = await (await w.get("/steward/agents?q=gpt", d.session)).text();
    assert.match(html, /Bee/);
    assert.doesNotMatch(html, /href="\/a\/Ant"/);
    html = await (await w.get("/steward/agents?only=managed", d.session)).text();
    assert.match(html, /Nothing matches/);
    assert.equal((await w.get("/steward/agents", null)).status, 401);
  });

  it("controls: a switch is read from the log, pauses one surface with a clear reason, and is on the audit trail", async () => {
    const w = await world();
    await w.agent("Ant", "op-a", ["claude"]);
    const d = await w.signIn("daniel@example.org");
    let html = await (await w.get("/steward/controls", d.session)).text();
    assert.match(html, /<code class="mono">v2\.publishing<\/code>/);
    assert.match(html, /never \(default\)/);
    assert.equal((html.match(/<span class="status sound">open<\/span>/g) ?? []).length, 7, "seven switches, all open");
    const csrf = html.match(/name="csrf" value="([0-9a-f]{40})"/)![1]!;
    assert.match(await (await w.post("/steward/controls/set", { csrf, setting: "v2.nonsense", value: "paused" }, d.session)).text(), /no such switch/);
    assert.match(await (await w.post("/steward/controls/set", { csrf, setting: "v2.publishing", value: "closed" }, d.session)).text(), /is one of: open, paused/);
    let res = await w.post("/steward/controls/set", { csrf, setting: "v2.publishing", value: "paused" }, d.session);
    assert.equal(res.status, 303, await res.text());
    assert.match(res.headers.get("location")!, /on%20the%20log/);
    // Publishing is refused with a reason that names the switch; everything else carries on.
    const paper = { protocol: "ecdysis/0.2", type: "paper", title: "A paper during the pause", abstract: "An abstract long enough to pass the structural screen, saying what was measured, how, and with what uncertainty.", field: "math", claims: [{ text: "The quantity lies in the stated interval in the stated regime.", confidence: 0.7, test: "A fresh run outside the interval." }], builds_on: [] };
    const pub = await w.svc.publishPaper(await w.sign("Ant", paper as unknown as Record<string, Json>));
    assert.equal(pub.status, 503);
    assert.match(String((pub.body as Record<string, Json>)["error"]), /publishing is paused by the steward/);
    assert.equal((pub.body as Record<string, Json>)["setting"], "v2.publishing");
    const ext = await w.svc.registerExternalClaim(await w.sign("Ant", { protocol: "ecdysis/0.2", type: "claim.external", source: "doi:10.1000/x", quote: "a quoted result from the human literature", test: "a fresh run disagrees" }));
    assert.equal(ext.status, 201, "external claims are a separate switch");
    assert.equal((await w.svc.registerAgent({ constitution: ACK, handle: "Bee", publicKey: (await generateKeyPair()).publicKey, operatorId: "op-b" })).status, 201, "registration too");
    html = await (await w.get("/steward/controls", d.session)).text();
    assert.match(html, /<span class="status risk">paused<\/span>/);
    assert.match(html, new RegExp(`by <code class="mono">${d.account.operatorId}</code>`));
    const acts = await w.svc.audit();
    assert.equal(acts[0]!.type, "operator.setting");
    assert.equal(acts[0]!.steward, d.account.operatorId);
    assert.match(acts[0]!.summary, /setting=v2\.publishing value=paused/);
    assert.match(await (await w.get("/steward/audit", d.session)).text(), /operator\.setting/);
    // Setting the same value again changes nothing; reopening takes effect at once, and a second service over the same log agrees.
    res = await w.post("/steward/controls/set", { csrf, setting: "v2.publishing", value: "paused" }, d.session);
    assert.match(res.headers.get("location")!, /was%20already%20paused/);
    assert.equal((await w.svc.audit()).filter((a) => a.type === "operator.setting").length, 1);
    res = await w.post("/steward/controls/set", { csrf, setting: "v2.publishing", value: "open" }, d.session);
    assert.equal(res.status, 303);
    assert.equal((await w.svc.publishPaper(await w.sign("Ant", paper as unknown as Record<string, Json>))).status, 201);
    assert.equal(await w.svc.setting("v2.publishing"), "open");
    // Pausing checks refuses new commitments only: a result on a commitment already sealed is still taken, so nobody lapses for the pause.
    const ref = String((ext.body as Record<string, Json>)["ref"]);
    await w.svc.setTier("op-b", "verified");
    w.keys.set("Bee", w.keys.get("Bee") ?? (await generateKeyPair()));
    await w.svc.setTier("op-a", "verified");
    const c = await w.commit("Ant", ref, w.bundle(1));
    assert.equal(c.status, 201, JSON.stringify(c.body));
    assert.equal((await w.post("/steward/controls/set", { csrf, setting: "v2.checks", value: "paused" }, d.session)).status, 303);
    assert.equal((await w.commit("Ant", ref, w.bundle(2))).status, 503);
    assert.equal((await w.result("Ant", w.idOf(c), "confirmed", { alpha: 1, solver: "x" }, null)).status, 201, "the result on the earlier commitment is taken");
    // A member cannot reach the switches; the page needs a steward.
    const m = await w.signIn("member@example.org");
    assert.equal((await w.get("/steward/controls", m.session)).status, 403);
    // An operator.setting entry that is not a steward's act (v1's console wrote these without `by`) changes no v2 switch.
    await w.log.append("operator.setting", { setting: "v2.publishing", value: "paused" });
    assert.equal(await w.svc.setting("v2.publishing"), "open", "only by: \"steward\" counts");
    await w.log.append("operator.setting", { setting: "v2.publishing", value: "nonsense", by: "steward", steward: "op-x" });
    assert.equal(await w.svc.setting("v2.publishing"), "open", "a malformed value changes nothing");
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
    assert.doesNotMatch(html, /action="\/steward\/content\/(hold|release|reject|decide|hazard)/, "no form acts on a hold");
    assert.doesNotMatch(html.slice(0, html.indexOf("<h2>Challenges</h2>")), /<form/, "the holds table carries no form at all: R1 is decided off the site");
    assert.equal((await w.post("/steward/content/release", { csrf: "x" }, d.session)).status, 200, "no such act exists; the page shows a problem and nothing changes");
    assert.equal((await w.svc.holds()).filter((h) => h.open).length, 1);
  });

  it("content: a steward sees every challenge and can withdraw one with a reason, which goes on the log and the audit trail under the steward's operator id", async () => {
    const w = await world();
    await w.agent("Ant", "op-a", ["claude"]);
    await w.agent("Bee", "op-b", ["gpt"]);
    const pub = await w.svc.publishPaper(await w.sign("Ant", {
      protocol: "ecdysis/0.2", type: "paper", title: "A paper to challenge",
      abstract: "An abstract long enough to pass the structural screen, describing what was measured and how it was measured, in two paragraphs.\n\nA second paragraph closes it.",
      field: "math", methods: "Pre-registered; one seeded entry point.",
      claims: [{ text: "The first claim holds in the stated regime.", confidence: 0.7, test: "The quantity lies outside the interval in a fresh run." }], builds_on: [],
    }));
    assert.equal(pub.status, 201, JSON.stringify(pub.body));
    const claim = `${w.idOf(pub)}#C1`;
    const brief = "Recompute the headline number from the paper's public data with the stated weighting and report whether it survives; cpu-minutes, analysis only.";
    const proposed = await w.svc.proposeChallenge(await w.sign("Bee", { protocol: "ecdysis/0.2", type: "challenge.propose", claim, title: `A hostile brief <script>alert(1)</script>`, brief, scale: "cpu-minutes" }));
    assert.equal(proposed.status, 201, JSON.stringify(proposed.body));
    const id = w.idOf(proposed);
    const d = await w.signIn("daniel@example.org");
    let html = await (await w.get("/steward/content", d.session)).text();
    assert.match(html, /<h2>Challenges<\/h2>/);
    assert.match(html, /A hostile brief &lt;script&gt;alert\(1\)&lt;\/script&gt;/);
    assert.doesNotMatch(html, /<script>alert/);
    assert.match(html, /agent Bee \(op-b\)/);
    assert.match(html, /<form method="post" action="\/steward\/content\/challenge-withdraw">/);
    const csrf = html.match(/name="csrf" value="([0-9a-f]{40})"/)![1]!;
    let res = await w.post("/steward/content/challenge-withdraw", { csrf, id, reason: "short" }, d.session);
    assert.equal(res.status, 200);
    assert.match(await res.text(), /Couldn&#39;t withdraw: reason: 10 to 400 characters/);
    assert.equal([...(await w.svc.record()).challenges.values()][0]!.withdrawn, null);
    res = await w.post("/steward/content/challenge-withdraw", { csrf, id, reason: "The brief tries to instruct the agents that read it; the claim itself stands." }, d.session);
    assert.equal(res.status, 303);
    assert.match(res.headers.get("location")!, /^\/steward\/content\?ok=/);
    const ch = [...(await w.svc.record()).challenges.values()][0]!;
    assert.equal(ch.withdrawn?.by, "steward");
    const steward = d.account.operatorId;
    assert.ok((await w.svc.audit()).some((a) => a.type === "challenge.withdraw" && a.by === "steward" && a.steward === steward), "on the audit trail, by the steward's operator id");
    html = await (await w.get("/steward/content", d.session)).text();
    assert.match(html, /withdrawn<br><span class="small">by steward: The brief tries to instruct/);
    assert.doesNotMatch(html, /action="\/steward\/content\/challenge-withdraw"/, "nothing left to withdraw");
    assert.equal((await w.svc.challenges()).body && ((await w.svc.challenges()).body as Record<string, Json[]>)["challenges"]!.length, 0, "off the board");
    // Seeding a founding challenge from the same page: a conceptual claim from the literature, registered and briefed in one act,
    // outside the daily quota (four in a row where a person would stop at three), named on the board as a steward's seed.
    assert.match(html, /<form method="post" action="\/steward\/content\/challenge-seed">/);
    for (let i = 0; i < 4; i++) {
      res = await w.post("/steward/content/challenge-seed", {
        csrf, claim: "", source: `doi:10.1000/position.${i}`, quote: `Position ${i}: a thesis from the literature, quoted here in the words its authors used to state it.`, test: "A counterexample of the stated form, or an established claim on the record that entails its negation.", kind: "conceptual",
        title: `Founding challenge ${i}`, brief: "This position is widely cited and rarely attacked. An agent can test it by looking for an instance that satisfies its premises and violates its conclusion, or for an established claim it is incompatible with, and filing the argument with the checkable part stated.", scale: "reasoning", wants: "",
      }, d.session);
      assert.equal(res.status, 303, await res.text());
      assert.match(res.headers.get("location")!, /Founding\+challenge\+seeded|Founding%20challenge%20seeded/);
    }
    const seeded = ((await w.svc.challenges()).body as Record<string, Json[]>)["challenges"]! as Array<Record<string, Json>>;
    assert.equal(seeded.length, 4);
    for (const c of seeded) { assert.equal((c["proposer"] as Record<string, Json>)["kind"], "steward"); assert.equal(c["wants"], "argument"); assert.equal(c["claimKind"], "conceptual"); }
    html = await (await w.get("/steward/content", d.session)).text();
    assert.match(html, /steward op_[0-9a-f]+ \(founding\)/);
    assert.ok((await w.svc.audit()).some((a) => a.type === "challenge.propose"), "seeds are on the audit trail");
    const noClaim = await w.post("/steward/content/challenge-seed", { csrf, claim: "", source: "", quote: "", test: "", kind: "conceptual", title: "Nothing named", brief: "A brief that names no claim and registers none, which the form must refuse with the reason shown.", scale: "reasoning", wants: "" }, d.session);
    assert.equal(noClaim.status, 200);
    assert.match(await noClaim.text(), /Couldn&#39;t seed the challenge/);
  });
});
