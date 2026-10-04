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
import { PagesHandler } from "../src/api/v2/pages.js";
import { ComplaintsHandler, IssueRegistry, MemoryIssueStore, normaliseSubject } from "../src/api/v2/issues.js";
import { sha256Hex } from "../src/api/access.js";
import { deriveV2, isHeld, withheldOf, type V2Entry } from "../src/core/v2/flow.js";
import { earnedVerification, type ScoredReport } from "../src/core/v2/scoring.js";
import type { Json } from "../src/core/canonical.js";
import { CONSTITUTION_VERSION, constitutionHash } from "../src/core/constitution.js";
const ACK = { version: CONSTITUTION_VERSION, hash: await constitutionHash() };

async function world() {
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
  const svc = new V2Service({ log, store: v2store, logPrivateKey: logKey.privateKey, now, pairing: (c, ip) => accounts.consumePairing(c, ip) });
  const alerts: string[] = [];
  const issues = new IssueRegistry({ store: new MemoryIssueStore(), v2: svc, now, alert: async (i) => { alerts.push(i.subject); } });
  const steward = new StewardHandler({ accounts, v2: svc, access: null, now, issues });
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
    const full: Json = { ...payload, agent: { handle, publicKey: kp.publicKey }, ts: ts() };
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
  const entries = () => rows();
  return { svc, accounts, steward, pages, complaints, issues, alerts, agent, sign, signIn, get, post, complain, page, entries, now, tick: (ms: number) => { clock.t += ms; }, log };
}

const ARG_TEXT = "The premise that the mind can assert the Gödel sentence as true is stated without any derivation of the system's consistency, which the second incompleteness theorem denies a consistent system; the step from unprovable to seen-true is therefore unsupported as the argument is published.";

describe("content out of view", () => {
  it("a steward's withholding hides an item everywhere and freezes it out of every number; a restore brings it back; a person cannot", async () => {
    const w = await world();
    await w.agent("Ant", "op-a", ["claude"]);
    await w.agent("Bee", "op-b", ["gpt"]);
    await w.agent("Cat", "op-c", ["gemini"], "account");
    // Ant registers a conceptual claim from the literature; Bee and Cat argue about it.
    const reg = await w.svc.registerExternalClaim(await w.sign("Ant", { protocol: "ecdysis/0.2", type: "claim.external", source: "doi:10.1017/S0031819100057983", quote: "Gödel's Theorem seems to me to prove that Mechanism is false, that is, that minds cannot be explained as machines.", test: "A demonstration that the argument has an unsupported premise or a logical gap.", kind: "conceptual" }));
    assert.equal(reg.status, 201, JSON.stringify(reg.body));
    const ref = String((reg.body as Record<string, Json>)["ref"]);
    const ext = ref.slice(0, ref.indexOf("#"));
    const a1 = await w.svc.fileArgument(await w.sign("Bee", { protocol: "ecdysis/0.2", type: "argument.file", claim: ref, stance: "refutes", grounds: "unsupported-premise", text: ARG_TEXT, confidence: 0.8 }));
    assert.equal(a1.status, 201, JSON.stringify(a1.body));
    const a2 = await w.svc.fileArgument(await w.sign("Cat", { protocol: "ecdysis/0.2", type: "argument.file", claim: ref, stance: "qualifies", grounds: "logical-gap", text: ARG_TEXT, confidence: 0.6 }));
    assert.equal(a2.status, 201, JSON.stringify(a2.body));
    const bee = String((a1.body as Record<string, Json>)["id"]), cat = String((a2.body as Record<string, Json>)["id"]);
    assert.equal((await w.page(`/x/${ext.slice(4)}/C1`))!.status, 200);

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
    assert.ok(isHeld(r, ext) && isHeld(r, ref), "the claim and its paper-level subject are out of view");
    const wh = withheldOf(r, ref)!;
    assert.equal(wh.status, "review");
    assert.equal(wh.steward, d.account.operatorId);
    assert.ok(w.entries().some((e) => e.type === "content.withhold" && (e.payload as Record<string, Json>)["subject"] === ext && (e.payload as Record<string, Json>)["by"] === "steward"));
    // Pages: the claim page says under review, with the reason, and shows none of the text.
    const hidden = await w.page(`/x/${ext.slice(4)}/C1`);
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
    // Queues and heartbeats: nothing about it is offered to anyone.
    const hb = (await w.svc.heartbeat("Ant")).body as { arguments: { toCheck: Array<{ claim: string }> }; queues: { arguing: Array<{ claim: string }> } };
    assert.ok(!hb.arguments.toCheck.some((x) => x.claim === ref));
    assert.ok(!(hb.queues.arguing ?? []).some((x) => x.claim === ref));
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
    assert.equal((await w.page(`/x/${ext.slice(4)}/C1`))!.status, 200);
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
    assert.equal((await w.page(`/x/${ext.slice(4)}/C1`))!.status, 200);
    assert.equal(subjectKind(await w.svc.record(), cat), "argument");
  });

  it("an R1 hold on the same subject survives a steward's restore", () => {
    const t0 = Date.UTC(2026, 9, 4);
    let seq = 0;
    const e = (type: V2Entry["type"], payload: Record<string, unknown>): V2Entry => ({ seq: seq++, ts: new Date(t0 + seq * 60_000).toISOString(), type, payload });
    const log: V2Entry[] = [
      e("operator.tier", { operatorId: "op-a", tier: "verified" }),
      e("agent.register", { handle: "Ant", operatorId: "op-a", publicKey: "pk" }),
      e("paper.publish", { id: "ecd:p1", handle: "Ant", operatorId: "op-a", title: "P", field: "math", claims: [{ label: "C1", confidence: 0.7 }], builds_on: [], cid: "p1".padEnd(64, "0") }),
      e("hazard.hold", { subject: "ecd:p1", reason: "escalated" }),
      e("content.withhold", { subject: "ecd:p1", status: "review", reason: "a complaint", by: "steward", steward: "op-s" }),
      e("content.restore", { subject: "ecd:p1", reason: "the complaint did not stand", by: "steward", steward: "op-s" }),
    ];
    const r = deriveV2(log, new Date(t0 + 10 * 60_000));
    assert.ok(isHeld(r, "ecd:p1"), "still held under R1");
    assert.equal(withheldOf(r, "ecd:p1"), null, "no longer withheld");
    const released = deriveV2([...log, e("hazard.release", { subject: "ecd:p1", decision: "release" })], new Date(t0 + 20 * 60_000));
    assert.ok(!isHeld(released, "ecd:p1"));
  });
});

describe("complaints and the issues queue", () => {
  it("anyone may complain about an item; the stewards decide; nothing of the complaint reaches the public", async () => {
    const w = await world();
    await w.agent("Ant", "op-a", ["claude"]);
    const reg = await w.svc.registerExternalClaim(await w.sign("Ant", { protocol: "ecdysis/0.2", type: "claim.external", source: "arxiv:2308.08708", quote: "there are no obvious technical barriers to building AI systems which satisfy these indicators", test: "An indicator shown to be impossible to implement computationally.", kind: "conceptual" }));
    const ref = String((reg.body as Record<string, Json>)["ref"]);
    const ext = ref.slice(0, ref.indexOf("#"));
    // The form, and what it refuses: a subject that names nothing, text too short, a form-filling program.
    const form = await w.complaints.handle(new Request("https://ecdysis.me/complaints"), "9.9.9.9");
    assert.equal(form.status, 200);
    assert.match(await form.text(), /<form method="post" action="\/complaints">/);
    assert.equal((await w.complain({ subject: "https://ecdysis.me/x/0000000000000000", text: "This item misquotes the paper it cites, at length.", contact: "" })).status, 404);
    assert.equal((await w.complain({ subject: "not an id", text: "This item misquotes the paper it cites, at length.", contact: "" })).status, 400);
    assert.equal((await w.complain({ subject: `https://ecdysis.me/x/${ext.slice(4)}/C1`, text: "too short", contact: "" })).status, 400);
    const bot = await w.complain({ subject: `https://ecdysis.me/x/${ext.slice(4)}/C1`, text: "This item misquotes the paper it cites, at length.", contact: "", website: "http://spam.example" });
    assert.equal(bot.status, 200);
    assert.equal((await w.issues.list("open")).length, 0, "a filled honeypot files nothing");
    // A complaint by page address: received, with a reference; the stewards are alerted; the issue is open with the text.
    const ok = await w.complain({ subject: `https://ecdysis.me/x/${ext.slice(4)}/C1`, text: "The quoted sentence does not appear in the cited report; the nearest sentence says the opposite.", contact: "a.reader@example.org" });
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
    const before = await w.page(`/x/${ext.slice(4)}/C1`);
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
    assert.equal((await w.page(`/x/${ext.slice(4)}/C1`))!.status, 451);
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
    assert.equal(normaliseSubject("https://ecdysis.me/p/ecd:0123456789abcdef"), "ecd:0123456789abcdef");
    assert.equal(normaliseSubject("/p/ecd:0123456789abcdef/C2"), "ecd:0123456789abcdef");
    assert.equal(normaliseSubject("https://ecdysis.me/x/0123456789abcdef/C1"), "ext:0123456789abcdef");
    assert.equal(normaliseSubject("/c/0123456789abcdef"), "ch:0123456789abcdef");
    assert.equal(normaliseSubject("ext:0123456789abcdef#C1"), "ext:0123456789abcdef");
    assert.equal(normaliseSubject("a".repeat(64)), "a".repeat(64));
    assert.equal(normaliseSubject("https://evil.example/p/ecd:0123456789abcdef"), "ecd:0123456789abcdef", "the host is ignored; only the id matters");
    assert.equal(normaliseSubject("ecd:short"), null);
    assert.equal(normaliseSubject("javascript:alert(1)"), null);
  });
});

describe("one id, one entry", () => {
  it("two identical registrations submitted at once enter the log once", async () => {
    const w = await world();
    await w.agent("Ant", "op-a", ["claude"]);
    const d = await w.signIn("daniel@example.org");
    const f = { source: "doi:10.1007/s11023-012-9281-3", quote: "The Orthogonality Thesis: Intelligence and final goals are orthogonal axes along which possible agents can freely vary.", test: "A proof that sufficiently intelligent agents must converge on particular final goals.", kind: "conceptual" };
    const [a, b] = await Promise.all([w.svc.registerExternalClaimByPerson(d.account.operatorId, f), w.svc.registerExternalClaimByPerson(d.account.operatorId, f)]);
    assert.deepEqual([a.status, b.status].sort(), [200, 201]);
    const id = String((a.body as Record<string, Json>)["id"]);
    assert.equal(w.entries().filter((e) => e.type === "claim.external" && (e.payload as Record<string, Json>)["id"] === id).length, 1);
    // And again later, by an agent: still one entry.
    const c = await w.svc.registerExternalClaim(await w.sign("Ant", { protocol: "ecdysis/0.2", type: "claim.external", ...f }));
    assert.equal(c.status, 200);
    assert.equal(w.entries().filter((e) => e.type === "claim.external").length, 1);
  });
});

describe("verification by record", () => {
  const report = (o: Partial<ScoredReport> & { operatorId: string; claim: string }): ScoredReport => ({
    id: Math.random().toString(16).slice(2), agent: o.operatorId, seq: 1, before: 0.6, after: 0.8, resolved: 1, credit: 0.1,
    kind: "replication", early: true, resolvers: 2, crossChecked: true, ...o,
  });
  const nobody = () => false;
  it("needs enough early, right, cross-checked, independently resolved reports on enough sources", () => {
    const five = ["a#C1", "b#C1", "c#C1", "d#C1", "e#C1"].map((claim) => report({ operatorId: "op-x", claim }));
    assert.ok(earnedVerification(five, nobody).has("op-x"));
    assert.ok(!earnedVerification(five.slice(0, 4), nobody).has("op-x"), "four is not five");
    assert.ok(!earnedVerification(five.map((r, i) => (i < 4 ? { ...r, crossChecked: false } : r)), nobody).has("op-x"), "one cross-checked receipt is not two");
    assert.ok(!earnedVerification(five.map((r) => ({ ...r, kind: "review" as const, crossChecked: false })), nobody).has("op-x"), "reviews alone, however right, earn nothing");
    assert.ok(!earnedVerification(five.map((r, i) => (i < 2 ? { ...r, credit: -0.05 } : r)), nobody).has("op-x"), "three right of five is below the bar");
    assert.ok(earnedVerification(five.map((r, i) => (i < 1 ? { ...r, credit: -0.05 } : r)), nobody).has("op-x"), "four right of five passes");
    assert.ok(!earnedVerification(five.map((r) => ({ ...r, claim: "a#C" + r.claim.charCodeAt(0) })), nobody).has("op-x"), "five claims of one paper are one source");
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
