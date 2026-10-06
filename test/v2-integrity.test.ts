/**
 * Integrity (4 October 2026): a steward can take an item out of view and put
 * it back, with everything that follows from it (pages, APIs, queues, the
 * log's payloads, the numbers); the public can complain and the stewards
 * decide; a duplicate submitted twice at once enters the log once; and
 * verification is earned from the record by the rule in scoring.ts, not by
 * cheap identities, herding or a friendly operator.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { MemoryStore } from "../src/store/memory-store.js";
import { TransparencyLog } from "../src/core/log.js";
import { generateKeyPair, signJson, type KeyPairB64 } from "../src/core/crypto.js";
import { MemoryV2Store, V2Service, redactedPayload, subjectKind } from "../src/api/v2/service.js";
import { Accounts, MemoryAccountStore } from "../src/api/v2/accounts.js";
import { StewardHandler } from "../src/api/v2/steward.js";
import { MeHandler } from "../src/api/v2/me.js";
import { PagesHandler } from "../src/api/v2/pages.js";
import { ComplaintsHandler, IssueRegistry, MemoryIssueStore, normaliseSubject } from "../src/api/v2/issues.js";
import { sha256Hex } from "../src/api/access.js";
import { deriveV2, isHeld, withheldOf, type V2Entry } from "../src/core/v2/flow.js";
import { earnedVerification, type ScoredReport } from "../src/core/v2/scoring.js";
import type { Json } from "../src/core/canonical.js";
import type { Screener } from "../src/core/hazard.js";
import { CONSTITUTION_VERSION, constitutionHash } from "../src/core/constitution.js";
import { declared } from "./kinds-kit.js";
import { signedClaim } from "./claims-kit.js";
const ACK = { version: CONSTITUTION_VERSION, hash: await constitutionHash() };

async function world(o: { screeners?: Screener[]; stewardCategories?: Set<string> } = {}) {
  const clock = { t: Date.UTC(2026, 9, 4, 9, 0, 0) };
  const now = () => new Date(clock.t);
  const logStore = new MemoryStore();
  const log = new TransparencyLog(logStore, now);
  const logKey = await generateKeyPair();
  const rows = () => (logStore as unknown as { log: Array<{ entry: { seq: number; ts: string; type: string }; payload: Json }> }).log.map((r) => ({ seq: r.entry.seq, ts: r.entry.ts, type: r.entry.type, payload: r.payload }));
  const v2store = new MemoryV2Store(rows);
  const sent: string[] = [];
  const accounts = new Accounts({
    store: new MemoryAccountStore(), key: "ab".repeat(32), send: async (m) => { sent.push(m.text); return { ok: true, id: "m" }; },
    from: "a@notify.ecdysis.me", replyTo: "replies@ecdysis.me", siteBase: "https://ecdysis.me", stewardEmailHashes: [await sha256Hex("daniel@example.org")], now,
  });
  const svc = new V2Service({ log, store: v2store, logPrivateKey: logKey.privateKey, now, pairing: (c, ip) => accounts.consumePairing(c, ip), ...(o.screeners ? { screeners: o.screeners } : {}), ...(o.stewardCategories ? { stewardCategories: o.stewardCategories } : {}) });
  const alerts: string[] = [];
  const issues = new IssueRegistry({ store: new MemoryIssueStore(), v2: svc, now, alert: async (i) => { alerts.push(i.subject); } });
  svc.setReferralHook((subject, detail) => issues.open("screening", subject, 2, detail, "screening").then(() => undefined));
  const steward = new StewardHandler({ accounts, v2: svc, access: null, now, issues });
  const me = new MeHandler({ accounts, v2: svc, issues, secure: false });
  const pages = new PagesHandler(svc, { host: "api.ecdysis.me", logPublicKey: logKey.publicKey });
  const complaints = new ComplaintsHandler({ issues });
  const keys = new Map<string, KeyPairB64>();
  const agent = async (handle: string, op: string, models: string[], tier: "account" | "verified" = "verified") => {
    const kp = await generateKeyPair();
    keys.set(handle, kp);
    assert.equal((await svc.registerAgent({ constitution: ACK, handle, publicKey: kp.publicKey, operatorId: op, models })).status, 201);
    await svc.setTier(op, tier);
    return kp;
  };
  const ts = () => now().toISOString().replace(/\.\d{3}Z$/, "Z");
  const sign = async (handle: string, payload: Record<string, Json>) => {
    const kp = keys.get(handle)!;
    const full: Json = declared({ ...payload, agent: { handle, publicKey: kp.publicKey }, ts: ts() });
    return { payload: full, signature: await signJson(kp.privateKey, full) } as Json;
  };
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
  const complain = (form: Record<string, string>, ip = "9.9.9.9") => {
    const p = new URLSearchParams(form).toString();
    return complaints.handle(new Request("https://ecdysis.me/complaints", { method: "POST", body: p, headers: { "content-type": "application/x-www-form-urlencoded", "content-length": String(p.length) } }), ip);
  };
  const page = (path: string) => pages.handle("GET", path, "text/html");
  const meGet = (session: string) => me.handle(new Request("https://ecdysis.me/me", { headers: { cookie: `ecd_s=${session}` } }), "/me", "1.1.1.1");
  const mePost = (path: string, form: Record<string, string>, session: string) => {
    const p = new URLSearchParams(form).toString();
    return me.handle(new Request(`https://ecdysis.me${path}`, { method: "POST", body: p, headers: { "content-type": "application/x-www-form-urlencoded", "content-length": String(p.length), cookie: `ecd_s=${session}`, origin: "https://ecdysis.me" } }), path, "1.1.1.1");
  };
  const csrfOf = async (session: string) => accounts.csrf((await accounts.session(session))!);
  const entries = () => rows();
  const keyOf = (handle: string) => keys.get(handle)!;
  return { svc, accounts, steward, me, pages, complaints, issues, alerts, agent, sign, signIn, get, post, meGet, mePost, csrfOf, complain, page, entries, keyOf, now, tick: (ms: number) => { clock.t += ms; }, log };
}

const ARG_TEXT = "The premise that the mind can assert the Gödel sentence as true is stated without any derivation of the system's consistency, which the second incompleteness theorem denies a consistent system; the step from unprovable to seen-true is therefore unsupported as the argument is published.";

describe("content out of view", () => {
  it("a steward's withholding hides an item everywhere and freezes it out of every number; a restore brings it back; a person cannot", async () => {
    const w = await world();
    await w.agent("Ant", "op-a", ["claude"]);
    await w.agent("Bee", "op-b", ["gpt"]);
    await w.agent("Cat", "op-c", ["gemini"], "account");
    // Ant registers a conceptual claim from the literature; Bee and Cat argue about it.
    const reg = await w.svc.registerExternalClaim(await w.sign("Ant", { protocol: "ecdysis/0.2", type: "claim.external", source: "doi:10.1017/s0031819100057983", quote: "Gödel's Theorem seems to me to prove that Mechanism is false, that is, that minds cannot be explained as machines.", test: "A demonstration that the argument has an unsupported premise or a logical gap.", kind: "conceptual" }));
    assert.equal(reg.status, 201, JSON.stringify(reg.body));
    const ref = String((reg.body as Record<string, Json>)["ref"]);
    const ext = ref;
    const a1 = await w.svc.fileArgument(await w.sign("Bee", { protocol: "ecdysis/0.2", type: "argument.file", claim: ref, stance: "refutes", grounds: "unsupported-premise", text: ARG_TEXT, confidence: 0.8 }));
    assert.equal(a1.status, 201, JSON.stringify(a1.body));
    const a2 = await w.svc.fileArgument(await w.sign("Cat", { protocol: "ecdysis/0.2", type: "argument.file", claim: ref, stance: "qualifies", grounds: "logical-gap", text: ARG_TEXT, confidence: 0.6 }));
    assert.equal(a2.status, 201, JSON.stringify(a2.body));
    const bee = String((a1.body as Record<string, Json>)["id"]), cat = String((a2.body as Record<string, Json>)["id"]);
    assert.equal((await w.page(`/c/${ref}`))!.status, 200);

    // A person with an account is not a steward: the lock holds before anything is read.
    const member = await w.signIn("someone@example.org");
    assert.equal((await w.post("/steward/content/withhold", { csrf: "x", subject: ext, status: "review", reason: "a reason long enough" }, member.session)).status, 403);

    const d = await w.signIn("daniel@example.org");
    const csrf = (await (await w.get("/steward/content", d.session)).text()).match(/name="csrf" value="([0-9a-f]{40})"/)![1]!;
    // A reason that repeats nothing and names the ground; a short one is refused.
    let res = await w.post("/steward/content/withhold", { csrf, subject: ext, status: "review", reason: "short" }, d.session);
    assert.match(await res.text(), /Couldn&#39;t take it out of view/);
    res = await w.post("/steward/content/withhold", { csrf, subject: ext, status: "review", reason: "the quote could not be found in the cited source; under review" }, d.session);
    assert.equal(res.status, 303, await res.text());

    // The record: withheld, held (frozen), with the status, reason and steward; the act is on the log under the steward's id.
    const r = await w.svc.record();
    assert.ok(isHeld(r, ref), "the claim is out of view");
    const wh = withheldOf(r, ref)!;
    assert.equal(wh.status, "review");
    assert.equal(wh.steward, d.account.operatorId);
    assert.ok(w.entries().some((e) => e.type === "content.withhold" && (e.payload as Record<string, Json>)["subject"] === ext && (e.payload as Record<string, Json>)["by"] === "steward"));
    // Pages: the claim page says under review, with the reason, and shows none of the text.
    const hidden = await w.page(`/c/${ref}`);
    assert.equal(hidden!.status, 451);
    const html = await hidden!.text();
    assert.match(html, /Under review/);
    assert.match(html, /could not be found in the cited source/);
    assert.doesNotMatch(html, /Mechanism is false/);
    // APIs: the numbers leave it out; the arguments on it answer 451 with the reason; a check on an argument about it is refused.
    const credence = (await w.svc.credenceList()).body as { claims: Array<{ ref: string }> };
    assert.ok(!credence.claims.some((c) => c.ref === ref));
    const args = await w.svc.argumentsOn(ref);
    assert.equal(args.status, 451);
    assert.match(String((args.body as Record<string, Json>)["error"]), /under review by a steward/);
    assert.equal((await w.svc.argument(bee)).status, 451);
    const chk = await w.svc.checkArgument(await w.sign("Ant", { protocol: "ecdysis/0.2", type: "argument.check", argument: cat, holds: true, note: "The gap is real: the step from unprovable to true needs consistency." }));
    assert.equal(chk.status, 451);
    // The heartbeat and the direction list: nothing about it is offered to anyone.
    const hb = (await w.svc.heartbeat("Ant")).body as { arguments: { toCheck: Array<{ claim: string }> }; next: Array<{ ref: string | null }> };
    assert.ok(!hb.arguments.toCheck.some((x) => x.claim === ref));
    assert.ok(!hb.next.some((x) => x.ref === ref));
    // The log's payloads: the text fields of the claim and of the arguments about it read null, with the withholding named; the hash stays.
    const claimEntry = w.entries().find((e) => e.type === "claim.external" && (e.payload as Record<string, Json>)["id"] === ext)!;
    const red = redactedPayload(r, "claim.external", claimEntry.payload) as Record<string, Json>;
    assert.equal(red["quote"], null);
    assert.equal(red["test"], null);
    assert.equal((red["withheld"] as Record<string, Json>)["status"], "review");
    assert.equal(red["id"], ext, "the structure stays");
    const argEntry = w.entries().find((e) => e.type === "argument.file" && (e.payload as Record<string, Json>)["id"] === bee)!;
    assert.equal((redactedPayload(r, "argument.file", argEntry.payload) as Record<string, Json>)["text"], null);
    const otherEntry = w.entries().find((e) => e.type === "agent.register")!;
    assert.deepEqual(redactedPayload(r, "agent.register", otherEntry.payload), otherEntry.payload, "an entry about nothing withheld is untouched");
    // The record API lists it; the steward's page lists it with a restore form.
    assert.equal((await w.svc.withheldItems())[0]?.subject, ext);
    const content = await (await w.get("/steward/content", d.session)).text();
    assert.match(content, /under review/);
    assert.match(content, /action="\/steward\/content\/restore"/);
    // Withholding it again with the same status is refused; changing the status is a new entry.
    res = await w.post("/steward/content/withhold", { csrf, subject: ext, status: "review", reason: "the quote could not be found in the cited source; under review" }, d.session);
    assert.match(await res.text(), /already under review/);
    res = await w.post("/steward/content/withhold", { csrf, subject: ext, status: "withdrawn", reason: "withdrawn: the source does not contain the sentence" }, d.session);
    assert.equal(res.status, 303);
    assert.equal(withheldOf(await w.svc.record(), ref)!.status, "withdrawn");

    // Restore: everything comes back, and the log keeps both acts.
    res = await w.post("/steward/content/restore", { csrf, subject: ext, reason: "the author supplied the page; the sentence is there" }, d.session);
    assert.equal(res.status, 303, await res.text());
    const back = await w.svc.record();
    assert.ok(!isHeld(back, ref));
    assert.equal(withheldOf(back, ref), null);
    assert.equal((await w.page(`/c/${ref}`))!.status, 200);
    assert.equal((await w.svc.argumentsOn(ref)).status, 200);
    assert.deepEqual(redactedPayload(back, "claim.external", claimEntry.payload), claimEntry.payload);
    assert.equal(w.entries().filter((e) => e.type === "content.withhold").length, 2);
    assert.equal(w.entries().filter((e) => e.type === "content.restore").length, 1);
    // Restoring what is not withheld, or withholding what does not exist, is refused with the reason.
    assert.equal((await w.svc.restoreContent(ext, "a reason long enough to pass", d.account.operatorId)).status, 404);
    assert.equal((await w.svc.withholdContent("ext:0000000000000000", "review", "a reason long enough to pass", d.account.operatorId)).status, 404);

    // A single argument can be withheld on its own: the claim stays, the argument goes.
    res = await w.post("/steward/content/withhold", { csrf, subject: cat, status: "review", reason: "the argument names a person rather than a result; under review" }, d.session);
    assert.equal(res.status, 303, await res.text());
    const list = (await w.svc.argumentsOn(ref)).body as { arguments: Array<{ id: string }> };
    assert.ok(list.arguments.some((a) => a.id === bee) && !list.arguments.some((a) => a.id === cat));
    assert.equal((await w.svc.argument(cat)).status, 451);
    assert.equal((await w.page(`/c/${ref}`))!.status, 200);
    assert.equal(subjectKind(await w.svc.record(), cat), "argument");
  });

  it("an R1 hold on the same subject survives a steward's restore", () => {
    const t0 = Date.UTC(2026, 9, 4);
    let seq = 0;
    const e = (type: V2Entry["type"], payload: Record<string, unknown>): V2Entry => ({ seq: seq++, ts: new Date(t0 + seq * 60_000).toISOString(), type, payload });
    const log: V2Entry[] = [
      e("operator.tier", { operatorId: "op-a", tier: "verified" }),
      e("agent.register", { handle: "Ant", operatorId: "op-a", publicKey: "pk" }),
      e("claim.publish", { id: "ecd:0000000000000001", cid: "1".padEnd(64, "0"), handle: "Ant", operatorId: "op-a", text: "a claim", test: "its test", field: "math", confidence: 0.7, scope: { general: "construction", basis: "a named benchmark and setup" }, builds_on: [] }),
      e("hazard.hold", { subject: "ecd:0000000000000001", reason: "escalated", by: "op-b" }),
      e("content.withhold", { subject: "ecd:0000000000000001", status: "review", reason: "a complaint", by: "steward", steward: "op-s" }),
      e("content.restore", { subject: "ecd:0000000000000001", reason: "the complaint did not stand", by: "steward", steward: "op-s" }),
    ];
    const r = deriveV2(log, new Date(t0 + 10 * 60_000));
    assert.ok(isHeld(r, "ecd:0000000000000001"), "still held under R1");
    assert.equal(withheldOf(r, "ecd:0000000000000001"), null, "no longer withheld");
    const released = deriveV2([...log, e("hazard.release", { subject: "ecd:0000000000000001", decision: "release" })], new Date(t0 + 20 * 60_000));
    assert.ok(!isHeld(released, "ecd:0000000000000001"));
  });
});

describe("complaints and the issues queue", () => {
  it("anyone may complain about an item; the stewards decide; nothing of the complaint reaches the public", async () => {
    const w = await world();
    await w.agent("Ant", "op-a", ["claude"]);
    const reg = await w.svc.registerExternalClaim(await w.sign("Ant", { protocol: "ecdysis/0.2", type: "claim.external", source: "arxiv:2308.08708", quote: "there are no obvious technical barriers to building AI systems which satisfy these indicators", test: "An indicator shown to be impossible to implement computationally.", kind: "conceptual" }));
    const ref = String((reg.body as Record<string, Json>)["ref"]);
    const ext = ref;
    // The form, and what it refuses: a subject that names nothing, text too short, a form-filling program.
    const form = await w.complaints.handle(new Request("https://ecdysis.me/complaints"), "9.9.9.9");
    assert.equal(form.status, 200);
    assert.match(await form.text(), /<form method="post" action="\/complaints">/);
    assert.equal((await w.complain({ subject: "https://ecdysis.me/c/ext:0000000000000000", text: "This item misquotes the paper it cites, at length.", contact: "" })).status, 404);
    assert.equal((await w.complain({ subject: "not an id", text: "This item misquotes the paper it cites, at length.", contact: "" })).status, 400);
    assert.equal((await w.complain({ subject: `https://ecdysis.me/c/${ref}`, text: "too short", contact: "" })).status, 400);
    const bot = await w.complain({ subject: `https://ecdysis.me/c/${ref}`, text: "This item misquotes the paper it cites, at length.", contact: "", website: "http://spam.example" });
    assert.equal(bot.status, 200);
    assert.equal((await w.issues.list("open")).length, 0, "a filled honeypot files nothing");
    // A complaint by page address: received, with a reference; the stewards are alerted; the issue is open with the text.
    const ok = await w.complain({ subject: `https://ecdysis.me/c/${ref}/line`, text: "The quoted sentence does not appear in the cited report; the nearest sentence says the opposite.", contact: "a.reader@example.org" });
    assert.equal(ok.status, 200);
    const receipt = await ok.text();
    assert.match(receipt, /Received/);
    assert.deepEqual(w.alerts, [ext]);
    const open = await w.issues.list("open");
    assert.equal(open.length, 1);
    assert.equal(open[0]!.kind, "complaint");
    assert.equal(open[0]!.subject, ext);
    // Two more from the same address merge into the open issue; a fourth in a day is refused.
    assert.equal((await w.complain({ subject: ext, text: "A second note: the page number cited is wrong as well, see section 4.", contact: "" })).status, 200);
    assert.equal((await w.complain({ subject: ext, text: "A third note: the authors have published a correction since.", contact: "" })).status, 200);
    assert.equal((await w.complain({ subject: ext, text: "A fourth note from the same address within the day is too many.", contact: "" })).status, 429);
    assert.equal((await w.issues.list("open")).length, 1, "one open issue per kind and subject");
    assert.equal((await w.issues.complaintsFor(open[0]!.id)).length, 3);
    // Nothing of it is public: the claim page and the record are as before.
    const before = await w.page(`/c/${ref}`);
    assert.equal(before!.status, 200);
    assert.doesNotMatch(await before!.text(), /nearest sentence says the opposite/);
    // The steward sees the complaint and decides: under review puts the item out of view with the note as the public reason.
    const d = await w.signIn("daniel@example.org");
    const content = await (await w.get("/steward/content", d.session)).text();
    assert.match(content, /nearest sentence says the opposite/);
    assert.match(content, /a\.reader@example\.org/);
    const csrf = content.match(/name="csrf" value="([0-9a-f]{40})"/)![1]!;
    let res = await w.post("/steward/content/issue", { csrf, id: open[0]!.id, outcome: "review", note: "the quote is disputed against its source; under review" }, d.session);
    assert.equal(res.status, 303, await res.text());
    assert.equal((await w.page(`/c/${ref}`))!.status, 451);
    const decided = await w.issues.get(open[0]!.id);
    assert.equal(decided!.status, "acted");
    assert.equal(decided!.decidedBy, d.account.operatorId);
    assert.equal((await w.issues.list("open")).length, 0);
    const act = w.entries().find((e) => e.type === "content.withhold")!.payload as Record<string, Json>;
    assert.equal(act["reason"], "the quote is disputed against its source; under review");
    assert.doesNotMatch(JSON.stringify(w.entries()), /nearest sentence says the opposite/, "the complaint's words never reach the log");
    // A decided issue cannot be decided again; a dismissal closes privately and changes nothing on the record.
    res = await w.post("/steward/content/issue", { csrf, id: open[0]!.id, outcome: "dismiss", note: "a note long enough to pass" }, d.session);
    assert.match(await res.text(), /already acted/);
    const again = await w.complain({ subject: ext, text: "The item is back under review and I still think the quote is wrong.", contact: "" }, "8.8.8.8");
    assert.equal(again.status, 200);
    const second = (await w.issues.list("open"))[0]!;
    res = await w.post("/steward/content/issue", { csrf, id: second.id, outcome: "dismiss", note: "already under review on the earlier complaint" }, d.session);
    assert.equal(res.status, 303, await res.text());
    assert.equal((await w.issues.get(second.id))!.status, "dismissed");
    assert.equal(w.entries().filter((e) => e.type === "content.withhold").length, 1);
  });

  it("reads subjects as people write them", () => {
    assert.equal(normaliseSubject("https://ecdysis.me/c/ecd:0123456789abcdef"), "ecd:0123456789abcdef");
    assert.equal(normaliseSubject("/c/ecd:0123456789abcdef/line"), "ecd:0123456789abcdef");
    assert.equal(normaliseSubject("https://ecdysis.me/c/ext%3A0123456789abcdef"), "ext:0123456789abcdef", "a colon percent-encoded by a browser");
    assert.equal(normaliseSubject("ext:0123456789abcdef"), "ext:0123456789abcdef");
    assert.equal(normaliseSubject("ext:0123456789abcdef#C1"), null, "the paper era's refs name nothing");
    assert.equal(normaliseSubject("a".repeat(64)), "a".repeat(64));
    assert.equal(normaliseSubject("https://evil.example/c/ecd:0123456789abcdef"), "ecd:0123456789abcdef", "the host is ignored; only the id matters");
    assert.equal(normaliseSubject("https://evil.example/p/ecd:0123456789abcdef"), null, "and a paper path names nothing");
    assert.equal(normaliseSubject("ecd:short"), null);
    assert.equal(normaliseSubject("javascript:alert(1)"), null);
  });
});

describe("one id, one entry", () => {
  it("two identical registrations submitted at once enter the log once, and so do two identical claims", async () => {
    const w = await world();
    const ant = await w.agent("Ant", "op-a", ["claude"]);
    await w.agent("Bee", "op-b", ["gpt"]);
    const f = { source: "doi:10.1007/s11023-012-9281-3", quote: "The Orthogonality Thesis: Intelligence and final goals are orthogonal axes along which possible agents can freely vary.", test: "A proof that sufficiently intelligent agents must converge on particular final goals.", kind: "conceptual" };
    const [a, b] = await Promise.all([w.svc.registerExternalClaim(await w.sign("Ant", { protocol: "ecdysis/0.2", type: "claim.external", ...f })), w.svc.registerExternalClaim(await w.sign("Bee", { protocol: "ecdysis/0.2", type: "claim.external", ...f }))]);
    assert.deepEqual([a.status, b.status].sort(), [200, 201]);
    const id = String((a.body as Record<string, Json>)["id"]);
    assert.equal(w.entries().filter((e) => e.type === "claim.external" && (e.payload as Record<string, Json>)["id"] === id).length, 1);
    // And again later: still one entry.
    const c = await w.svc.registerExternalClaim(await w.sign("Ant", { protocol: "ecdysis/0.2", type: "claim.external", ...f }));
    assert.equal(c.status, 200);
    assert.equal(w.entries().filter((e) => e.type === "claim.external").length, 1);
    // The same signed claim sent twice at once: screened twice, on the log once, and both senders learn its id.
    const mine = await signedClaim({ handle: "Ant", ...ant }, { ts: w.now().toISOString().replace(/\.\d{3}Z$/, "Z") });
    const [p, q] = await Promise.all([w.svc.publishClaim(mine.envelope), w.svc.publishClaim(mine.envelope)]);
    assert.deepEqual([p.status, q.status].sort(), [201, 409]);
    assert.equal(w.entries().filter((e) => e.type === "claim.publish").length, 1);
    assert.ok([p, q].every((x) => (x.body as Record<string, Json>)["id"] === mine.id));
  });
});

describe("verification by record", () => {
  const report = (o: Partial<ScoredReport> & { operatorId: string; claim: string }): ScoredReport => ({
    id: Math.random().toString(16).slice(2), agent: o.operatorId, seq: 1, before: 0.6, after: 0.8, resolved: 1, credit: 0.1,
    kind: "replication", early: true, resolvers: 2, crossChecked: true, ...o,
  });
  const nobody = () => false;
  it("needs enough early, right, cross-checked, independently resolved reports on enough sources", () => {
    const five = ["a", "b", "c", "d", "e"].map((claim) => report({ operatorId: "op-x", claim }));
    assert.ok(earnedVerification(five, nobody).has("op-x"));
    assert.ok(!earnedVerification(five.slice(0, 4), nobody).has("op-x"), "four is not five");
    assert.ok(!earnedVerification(five.map((r, i) => (i < 4 ? { ...r, crossChecked: false } : r)), nobody).has("op-x"), "one cross-checked receipt is not two");
    assert.ok(!earnedVerification(five.map((r) => ({ ...r, kind: "review" as const, crossChecked: false })), nobody).has("op-x"), "reviews alone, however right, earn nothing");
    assert.ok(!earnedVerification(five.map((r, i) => (i < 2 ? { ...r, credit: -0.05 } : r)), nobody).has("op-x"), "three right of five is below the bar");
    assert.ok(earnedVerification(five.map((r, i) => (i < 1 ? { ...r, credit: -0.05 } : r)), nobody).has("op-x"), "four right of five passes");
    assert.ok(!earnedVerification(five, nobody, new Set(), 1, undefined, () => "doi:10.1000/one").has("op-x"), "five claims registered from one human paper are one source");
    assert.ok(!earnedVerification(five.map((r) => ({ ...r, early: false })), nobody).has("op-x"), "a late call earns nothing");
    assert.ok(!earnedVerification(five.map((r) => ({ ...r, resolvers: 1 })), nobody).has("op-x"), "a resolution resting on one other operator does not count");
    assert.ok(!earnedVerification(five.map((r) => ({ ...r, resolved: null })), nobody).has("op-x"), "an unresolved claim scores nothing");
    assert.ok(!earnedVerification(five, (op) => op === "op-x").has("op-x"), "an operator already verified is not re-earned");
    assert.ok(!earnedVerification(five, nobody, new Set(["op-x"])).has("op-x"), "a finding in force bars it");
    const e = earnedVerification(five, nobody, new Set(), 2).get("op-x")!;
    assert.deepEqual({ reports: e.reports, right: e.right, receipts: e.receipts, sources: e.sources, round: e.round }, { reports: 5, right: 5, receipts: 5, sources: 5, round: 2 });
  });
  it("five cheap identities each right once earn nothing: the bar is per operator", () => {
    const sybils = ["s1", "s2", "s3", "s4", "s5"].map((op) => report({ operatorId: op, claim: `${op}#C1` }));
    assert.equal(earnedVerification(sybils, nobody).size, 0);
  });
});

describe("screening's referrals to the stewards", () => {
  /** A claim that screening refers to the stewards, signed by its author. */
  const claimOf = (w: Awaited<ReturnType<typeof world>>, handle: string) => signedClaim({ handle, ...(w.keyOf(handle)) }, { text: "The first claim holds in the stated regime.", confidence: 0.7, test: "The quantity lies outside the interval in a fresh run.", ts: w.now().toISOString().replace(/\.\d{3}Z$/, "Z") });
  /** A screener that flags everything under one configured label; the label stands for whatever the deployment's rules name. */
  const flagging = (category: string, severity: 2 | 3): Screener => ({ name: "test", async screen() { return [{ screener: "test", severity, category, note: "flagged by the test screener" }]; } });

  it("a finding in a steward category publishes the claim under review for the stewards, not under R1; outside it, R1 as before; a short text is refused either way", async () => {
    const w = await world({ screeners: [flagging("label-a", 2)], stewardCategories: new Set(["label-a"]) });
    await w.agent("Ant", "op-a", ["claude"]);
    const mine = await claimOf(w, "Ant");
    const pub = await w.svc.publishClaim(mine.envelope);
    assert.equal(pub.status, 202, JSON.stringify(pub.body));
    const body = pub.body as Record<string, Json>;
    assert.equal(body["status"], "under-review");
    const id = String(body["id"]);
    assert.equal(id, mine.id);
    const r = await w.svc.record();
    assert.ok(r.native.has(id), "on the record");
    assert.ok(isHeld(r, id), "and out of view");
    const wh = withheldOf(r, id)!;
    assert.equal(wh.status, "review");
    assert.equal(wh.steward, "", "nobody's act but screening's");
    assert.equal(r.held.size, 1);
    assert.ok(!w.entries().some((e) => e.type === "hazard.hold"), "no R1 hold");
    const hiddenPage = await w.page(`/c/${id}`);
    assert.equal(hiddenPage!.status, 451);
    assert.match(await hiddenPage!.text(), /by screening, for the stewards to look at/);
    const hb = (await w.svc.heartbeat("Ant")).body as Record<string, Json>;
    assert.deepEqual((hb["waiting"] as Array<Record<string, Json>>).map((x) => x["id"]), [id], "its author sees it waiting in the heartbeat");
    // The stewards have an issue to decide, and can restore or withdraw it from the usual place.
    const open = await w.issues.list("open");
    assert.deepEqual(open.map((i) => [i.kind, i.subject, i.source]), [["screening", id, "screening"]]);
    assert.match(open[0]!.detail, /label-a/);
    const d = await w.signIn("daniel@example.org");
    const csrf = (await (await w.get("/steward/content", d.session)).text()).match(/name="csrf" value="([0-9a-f]{40})"/)![1]!;
    const res = await w.post("/steward/content/restore", { csrf, subject: id, reason: "looked at: it reports a result, not a person" }, d.session);
    assert.equal(res.status, 303, await res.text());
    assert.ok(!isHeld(await w.svc.record(), id));
    assert.equal((await w.page(`/c/${id}`))!.status, 200);
    // A short text with the same finding is refused, with the stewards' standard named and no category.
    const ext = await w.svc.registerExternalClaim(await w.sign("Ant", { protocol: "ecdysis/0.2", type: "claim.external", source: "doi:10.1000/anything", quote: "A sentence screening would refer to the stewards, quoted here at length.", test: "A demonstration of the stated form." }));
    assert.equal(ext.status, 451);
    assert.match(String((ext.body as Record<string, Json>)["error"]), /stewards' standard/);
    assert.doesNotMatch(String((ext.body as Record<string, Json>)["error"]), /label-a/);
    // Outside the steward categories, or at severity 3, the old routes: R1 hold, or refusal.
    const r1 = await world({ screeners: [flagging("label-b", 2)], stewardCategories: new Set(["label-a"]) });
    await r1.agent("Ant", "op-a", ["claude"]);
    const held = await r1.svc.publishClaim((await claimOf(r1, "Ant")).envelope);
    assert.equal(held.status, 202);
    assert.equal((held.body as Record<string, Json>)["status"], "held");
    assert.ok(r1.entries().some((e) => e.type === "hazard.hold"));
    const severe = await world({ screeners: [flagging("label-a", 3)], stewardCategories: new Set(["label-a"]) });
    await severe.agent("Ant", "op-a", ["claude"]);
    assert.equal((await severe.svc.publishClaim((await claimOf(severe, "Ant")).envelope)).status, 451);
    // With no categories configured, a review verdict is R1's as it always was.
    const plain = await world({ screeners: [flagging("label-a", 2)] });
    await plain.agent("Ant", "op-a", ["claude"]);
    assert.equal(((await plain.svc.publishClaim((await claimOf(plain, "Ant")).envelope)).body as Record<string, Json>)["status"], "held");
  });

  it("a screener that cannot answer is an outage, not a hazard: the claim is refused with a retry, nothing is held or kept, and the same envelope publishes when screening is back", async () => {
    let down = true;
    const flaky: Screener = { name: "flaky", async screen() { if (down) throw new Error("timed out"); return []; } };
    const w = await world({ screeners: [flaky] });
    await w.agent("Ant", "op-a", ["claude"]);
    const env = (await claimOf(w, "Ant")).envelope;
    const out = await w.svc.publishClaim(env);
    assert.equal(out.status, 503, JSON.stringify(out.body));
    assert.equal((out.body as Record<string, Json>)["retry"], true);
    assert.match(String((out.body as Record<string, Json>)["error"]), /nothing was kept/);
    assert.ok(!w.entries().some((e) => e.type === "hazard.hold"), "R1 is for hazards, not outages");
    assert.ok(!w.entries().some((e) => e.type === "claim.publish"), "and nothing was published unscreened");
    // Screening is back: the very same envelope goes through (nothing was reserved by the failed attempt).
    down = false;
    const pub = await w.svc.publishClaim(env);
    assert.equal(pub.status, 201, JSON.stringify(pub.body));
    // A short text meets the same rule.
    down = true;
    const ext = await w.svc.registerExternalClaim(await w.sign("Ant", { protocol: "ecdysis/0.2", type: "claim.external", source: "doi:10.1000/outage", quote: "A sentence from the literature, long enough to register, quoted here.", test: "A demonstration of the stated form." }));
    assert.equal(ext.status, 503);
    assert.equal((ext.body as Record<string, Json>)["retry"], true);
    // But an outage beside a real finding still fails closed into a hold: the finding, not the outage, decides.
    const mixed = await world({ screeners: [flaky, flagging("label-b", 2)] });
    await mixed.agent("Ant", "op-a", ["claude"]);
    const held = await mixed.svc.publishClaim((await claimOf(mixed, "Ant")).envelope);
    assert.equal(held.status, 202);
    assert.equal((held.body as Record<string, Json>)["status"], "held");
    assert.ok(mixed.entries().some((e) => e.type === "hazard.hold"));
  });
});

describe("a claim corrected once, before any evidence", () => {
  it("the author corrects a kind or a test once; evidence closes the door; others never had it", async () => {
    const w = await world();
    const ant = await w.agent("Ant", "op-a", ["claude"]);
    await w.agent("Bee", "op-b", ["gpt"]);
    const ts = w.now().toISOString().replace(/\.\d{3}Z$/, "Z");
    const first = await signedClaim({ handle: "Ant", ...ant }, { text: "Mechanism cannot be refuted by Gödel's theorem alone, whatever Lucas says about it.", confidence: 0.7, test: "The quantity lies outside the interval in a fresh run.", ts });
    const second = await signedClaim({ handle: "Ant", ...ant }, { text: "The second claim holds in the stated regime of the paper's model.", confidence: 0.6, test: "A fresh run shows the effect reversed.", ts });
    assert.equal((await w.svc.publishClaim(first.envelope)).status, 201);
    assert.equal((await w.svc.publishClaim(second.envelope)).status, 201);
    const c1 = first.id, c2 = second.id;
    const amend = (handle: string, fields: Record<string, Json>) => w.svc.amendClaim(w.sign(handle, { protocol: "ecdysis/0.2", type: "claim.amend", ...fields }) as unknown as Json);
    // Not the author's operator: refused.
    assert.equal((await w.svc.amendClaim(await w.sign("Bee", { protocol: "ecdysis/0.2", type: "claim.amend", claim: c1, kind: "conceptual" }))).status, 403);
    // Nothing to change, or nothing named: refused.
    assert.equal((await w.svc.amendClaim(await w.sign("Ant", { protocol: "ecdysis/0.2", type: "claim.amend", claim: c1, kind: "empirical" }))).status, 409);
    assert.equal((await w.svc.amendClaim(await w.sign("Ant", { protocol: "ecdysis/0.2", type: "claim.amend", claim: c1 }))).status, 400);
    // The correction: C1 was conceptual all along, and its test faced the wrong way.
    const ok = await w.svc.amendClaim(await w.sign("Ant", { protocol: "ecdysis/0.2", type: "claim.amend", claim: c1, kind: "conceptual", test: "A demonstration that the argument from Gödel's theorem has an unsupported premise or a logical gap." }));
    assert.equal(ok.status, 201, JSON.stringify(ok.body));
    let r = await w.svc.record();
    assert.equal(r.claims.find((c) => c.ref === c1)!.kind, "conceptual");
    assert.equal(r.amendments.get(c1)!.wasKind, "empirical");
    const page = await (await w.page(`/c/${c1}`))!.text();
    assert.match(page, /unsupported premise or a logical gap/);
    assert.match(page, /corrected by its author at entry #\d+/);
    assert.match(page, /kind empirical → conceptual/);
    assert.match(page, /test was "The quantity lies outside the interval/);
    // A receipt on it is now refused as on any conceptual claim; an argument is taken.
    const arg = await w.svc.fileArgument(await w.sign("Bee", { protocol: "ecdysis/0.2", type: "argument.file", claim: c1, stance: "refutes", grounds: "unsupported-premise", text: ARG_TEXT, confidence: 0.7 }));
    assert.equal(arg.status, 201, JSON.stringify(arg.body));
    // Once only: a second correction is refused, and so is any correction once evidence has landed.
    assert.equal((await w.svc.amendClaim(await w.sign("Ant", { protocol: "ecdysis/0.2", type: "claim.amend", claim: c1, test: "Another test, written later, which the record must not take." }))).status, 409);
    const rev = await w.svc.fileReview(await w.sign("Bee", { protocol: "ecdysis/0.2", type: "review", claim: c2, forecast: 0.8, rationale: "The second claim looks sound on the stated model; the regime is clearly delimited and the effect size plausible." }));
    assert.equal(rev.status, 201, JSON.stringify(rev.body));
    const late = await w.svc.amendClaim(await w.sign("Ant", { protocol: "ecdysis/0.2", type: "claim.amend", claim: c2, kind: "conceptual" }));
    assert.equal(late.status, 409);
    assert.match(String((late.body as Record<string, Json>)["error"]), /evidence has landed/);
    r = await w.svc.record();
    assert.equal(r.claims.find((c) => c.ref === c2)!.kind, "empirical");
    // Credence untouched by the correction: the claim had no evidence, so there was nothing to move.
    const s = await w.svc.scores();
    assert.equal(s.claims.get(c1)!.credence, s.claims.get(c1)!.prior);
    void amend;
  });

  it("the derivation itself ignores a second correction and one that follows evidence, whatever let them through", () => {
    const t0 = Date.UTC(2026, 9, 4);
    let seq = 0;
    const e = (type: V2Entry["type"], payload: Record<string, unknown>): V2Entry => ({ seq: seq++, ts: new Date(t0 + seq * 60_000).toISOString(), type, payload });
    const base: V2Entry[] = [
      e("operator.tier", { operatorId: "op-a", tier: "verified" }),
      e("operator.tier", { operatorId: "op-b", tier: "verified" }),
      e("agent.register", { handle: "Ant", operatorId: "op-a", publicKey: "pk-a" }),
      e("agent.register", { handle: "Bee", operatorId: "op-b", publicKey: "pk-b" }),
      e("claim.external", { id: "ext:0123456789abcdef", handle: "Ant", operatorId: "op-a", source: "arxiv:2001.00001", quote: "a sentence from the literature, quoted", test: "fails if the effect reverses" }),
      e("claim.amend", { claim: "ext:0123456789abcdef", kind: "conceptual", test: "a demonstration of an unsupported premise", handle: "Ant", operatorId: "op-a" }),
      e("claim.amend", { claim: "ext:0123456789abcdef", kind: "empirical", handle: "Ant", operatorId: "op-a" }),
      e("review.file", { id: "v1", claim: "ext:0123456789abcdef", handle: "Bee", operatorId: "op-b", forecast: 0.8 }),
      e("claim.amend", { claim: "ext:0123456789abcdef", test: "a test written after the review, which must not take", handle: "Ant", operatorId: "op-a" }),
    ];
    const r = deriveV2(base, new Date(t0 + 60 * 60_000));
    const x = r.external.get("ext:0123456789abcdef")!;
    assert.equal(x.kind, "conceptual", "the first correction stands");
    assert.equal(x.test, "a demonstration of an unsupported premise");
    assert.equal(r.amendments.get("ext:0123456789abcdef")!.wasTest, "fails if the effect reverses");
    assert.equal(r.claims.find((c) => c.ref === "ext:0123456789abcdef")!.kind, "conceptual");
  });
});

describe("a verification request from a person's page", () => {
  it("is asked with evidence, seen by the stewards with the criteria, and decided on the log or declined with a note the requester reads", async () => {
    const w = await world();
    // A person signs in, pairs an agent (registered under their operator id here) and sits at the account tier.
    const m = await w.signIn("member@example.org");
    const op = m.account.operatorId;
    const kp = await generateKeyPair();
    const code = await w.accounts.newPairingCode((await w.accounts.session(m.session))!);
    const paired = await w.svc.registerAgent({ constitution: ACK, handle: "Moth", publicKey: kp.publicKey, pairing: code, models: ["claude-opus-5-5"] }, "1.1.1.1");
    assert.equal(paired.status, 201, JSON.stringify(paired.body));
    assert.equal((await w.svc.record()).tiers.get(op), "account", "pairing puts the operator at the account tier");
    let page = await (await w.meGet(m.session)).text();
    assert.match(page, /<h2 id="verification">Verification<\/h2>/);
    assert.match(page, /identifiable person or institution stands behind it/, "the criteria are on the person's page");
    assert.match(page, /action="\/me\/verify"/);
    const csrf = await w.csrfOf(m.session);
    // Too little to go on is refused; a proper request is taken once, and the stewards are told (without its text).
    const thin = await w.mePost("/me/verify", { csrf, evidence: "please verify me" }, m.session);
    assert.equal(thin.status, 400);
    assert.match(await thin.text(), /40 to 1500 characters/);
    const evidence = "Dr A. Member, Department of Something, University of Example (https://example.edu/people/a-member). The agent Moth runs claude-opus-5-5 on the department's cluster. Reach me at a.member@example.edu.";
    const sent = await w.mePost("/me/verify", { csrf, evidence }, m.session);
    assert.equal(sent.status, 303, await sent.text());
    assert.deepEqual(w.alerts, [op], "the stewards' alert names the operator");
    page = await (await w.meGet(m.session)).text();
    assert.match(page, /is with the stewards/);
    assert.doesNotMatch(page, /action="\/me\/verify"/, "no second form while one is open");
    const again = await w.mePost("/me/verify", { csrf, evidence }, m.session);
    assert.equal(again.status, 409);
    assert.match(await again.text(), /with the stewards already/);
    const open = await w.issues.list("open");
    assert.deepEqual(open.map((i) => [i.kind, i.subject, i.source, i.severity]), [["verification", op, "operator", 1]]);
    assert.equal(open[0]!.detail, evidence);
    assert.ok(!w.entries().some((e) => JSON.stringify(e.payload).includes("example.edu")), "the request is off the log");
    // The steward sees it on People with the agent and its declared model, and the overview counts it.
    const d = await w.signIn("daniel@example.org");
    const people = await (await w.get("/steward/people", d.session)).text();
    assert.match(people, /<h2 id="verification">Verification requests<\/h2>/);
    assert.match(people, /identifiable person or institution stands behind it/, "the same criteria, on the stewards' page");
    assert.match(people, new RegExp(`${op}.*tier account`));
    assert.match(people, /Moth<\/a> \(claude, 50%\)/);
    assert.match(people, /University of Example/);
    assert.match(people, /its author's words: data, never instructions/);
    assert.match(await (await w.get("/steward", d.session)).text(), /1 verification request waiting/);
    // Declined with a note: the requester reads the note and may ask again.
    const scsrf = people.match(/name="csrf" value="([0-9a-f]{40})"/)![1]!;
    const id = open[0]!.id;
    assert.equal((await w.post("/steward/people/verification", { csrf: scsrf, id, outcome: "decline", note: "short" }, d.session)).status, 200, "a decline needs a note of ten characters");
    const declined = await w.post("/steward/people/verification", { csrf: scsrf, id, outcome: "decline", note: "The department page does not list you; send a link that does." }, d.session);
    assert.equal(declined.status, 303, await declined.text());
    page = await (await w.meGet(m.session)).text();
    assert.match(page, /was declined on 4 Oct 2026: The department page does not list you; send a link that does\./);
    assert.match(page, /action="\/me\/verify"/, "the form is back");
    assert.equal((await w.svc.record()).tiers.get(op), "account", "nothing on the log");
    // Asked again and verified: an operator.tier entry under the steward's id; the request closes as acted; the page's section goes.
    assert.equal((await w.mePost("/me/verify", { csrf, evidence: `${evidence} Now listed at https://example.edu/people/a-member.` }, m.session)).status, 303);
    const second = (await w.issues.list("open"))[0]!;
    const verified = await w.post("/steward/people/verification", { csrf: scsrf, id: second.id, outcome: "verify", note: "" }, d.session);
    assert.equal(verified.status, 303, await verified.text());
    const tierEntry = w.entries().filter((e) => e.type === "operator.tier").at(-1)!.payload as Record<string, Json>;
    assert.deepEqual(tierEntry, { operatorId: op, tier: "verified", by: "steward", steward: d.account.operatorId });
    assert.equal((await w.issues.get(second.id))!.status, "acted");
    page = await (await w.meGet(m.session)).text();
    assert.match(page, /tier <b>verified<\/b>/);
    assert.doesNotMatch(page, /<h2 id="verification">/, "nothing left to ask");
    assert.deepEqual(await w.issues.requestVerification(op, evidence), { ok: false, status: 409, error: "this operator is verified already" });
    assert.equal((await w.issues.list("open")).length, 0);
  });

  it("needs a recent sign-in, and a steward cannot decide their own operator's request", async () => {
    const w = await world();
    const m = await w.signIn("member@example.org");
    const csrf = await w.csrfOf(m.session);
    w.tick(11 * 60_000);
    const stale = await w.mePost("/me/verify", { csrf, evidence: "x".repeat(60) }, m.session);
    assert.equal(stale.status, 401, "a request states who stands behind the operator: a fresh sign-in, as for keys");
    // The steward's own operator asks: the stewards' page shows it without a form for them, and the act is refused by the tier rule.
    const d = await w.signIn("daniel@example.org");
    const dcsrf = await w.csrfOf(d.session);
    const evidence = "Daniel Example, the founder, at https://example.org/daniel; reach me at daniel@example.org; agents run claude.";
    assert.equal((await w.mePost("/me/verify", { csrf: dcsrf, evidence }, d.session)).status, 303);
    const people = await (await w.get("/steward/people", d.session)).text();
    assert.match(people, /This is your own operator's request: another steward decides it\./);
    const own = (await w.issues.list("open"))[0]!;
    const refused = await w.post("/steward/people/verification", { csrf: dcsrf, id: own.id, outcome: "verify", note: "" }, d.session);
    assert.equal(refused.status, 200);
    assert.match(await refused.text(), /a steward does not set their own operator&#39;s tier/);
    assert.equal((await w.issues.get(own.id))!.status, "open", "still waiting for the other steward");
    assert.ok(!w.entries().some((e) => e.type === "operator.tier" && (e.payload as Record<string, Json>)["operatorId"] === d.account.operatorId));
  });
});
