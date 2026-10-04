/**
 * review/0.1: reports of problems with items on the record, the stewards' review of them, withdrawal from view, and the
 * once-only correction of a claim's test (the owner's decisions of 4 Oct 2026). The adversarial cases show an
 * unverified crowd failing to hide anyone's work, a report's words never reaching the public log, a forged withdrawal
 * changing nothing, a correction after evidence failing, an R1 hold untouched by review, and withdrawn words served
 * nowhere while every number still recomputes from the public log.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { MemoryStore } from "../src/store/memory-store.js";
import { TransparencyLog } from "../src/core/log.js";
import { generateKeyPair, signJson, type KeyPairB64 } from "../src/core/crypto.js";
import { structuralScreener, type Screener } from "../src/core/hazard.js";
import { MemoryV2Store, V2Service } from "../src/api/v2/service.js";
import { EcdysisService } from "../src/api/service.js";
import { route, MemoryRateLimiter } from "../src/api/router.js";
import { handleMcp } from "../src/api/mcp.js";
import { v2Tools } from "../src/api/v2/tools.js";
import { PagesHandler } from "../src/api/v2/pages.js";
import { StewardHandler, type StewardHealth } from "../src/api/v2/steward.js";
import { Accounts, MemoryAccountStore } from "../src/api/v2/accounts.js";
import { sha256Hex } from "../src/api/access.js";
import { recomputeV2 } from "../src/api/v2/recompute.js";
import { deriveV2, type V2Entry } from "../src/core/v2/flow.js";
import { itemOf, reportCap, REPORTS_PER_DAY, REPORTS_PER_DAY_DAMPED, TEXT_FIELDS, withholdText } from "../src/core/v2/review.js";
import type { Bundle } from "../src/core/v2/receipts.js";
import type { Json } from "../src/core/canonical.js";
import { CONSTITUTION_VERSION, constitutionHash } from "../src/core/constitution.js";
const ACK = { version: CONSTITUTION_VERSION, hash: await constitutionHash() };

const MIN = 60 * 1000;
const body = (r: { body: Json }) => r.body as Record<string, Json>;
const NOTE = "The quote drops the formula: the paper says K-SAT where this says -SAT, so these are not the source's words.";
const PERSON_NOTE = "The abstract names a private individual and says they falsified data; nothing in the paper supports it.";

async function world(screeners: Screener[] = [structuralScreener()]) {
  const clock = { t: Date.UTC(2026, 9, 4, 9, 0, 0) };
  const now = () => new Date(clock.t);
  const logStore = new MemoryStore();
  const log = new TransparencyLog(logStore, now);
  const logKey = await generateKeyPair();
  const rows = () => (logStore as unknown as { log: Array<{ entry: { seq: number; ts: string; type: string }; payload: Json }> }).log.map((r) => ({ seq: r.entry.seq, ts: r.entry.ts, type: r.entry.type, payload: r.payload }));
  const svc = new V2Service({ log, store: new MemoryV2Store(rows), logPrivateKey: logKey.privateKey, now, screeners });
  const v1 = new EcdysisService({ store: logStore, screeners: [structuralScreener()], sthPrivateKey: null });
  const pages = new PagesHandler(svc, { host: "api.ecdysis.me" });
  const limiter = new MemoryRateLimiter(10_000);
  const sent: string[] = [];
  const accounts = new Accounts({
    store: new MemoryAccountStore(), key: "ab".repeat(32), send: async (m) => { sent.push(m.text); return { ok: true, id: "m" }; },
    from: "a@notify.ecdysis.me", replyTo: "replies@ecdysis.me", siteBase: "https://ecdysis.me", stewardEmailHashes: [await sha256Hex("daniel@example.org")], now,
  });
  let lastAudit: { intact: boolean; problem: string | null; size: number } | null = null;
  const audits: string[] = [];
  const health: StewardHealth = {
    sth: async () => ({ treeSize: rows().length, rootHash: "ab".repeat(32), timestamp: now().toISOString(), signature: "c2ln" }),
    logSize: async () => rows().length,
    ops: async (key) => (key === "cron:last" ? { value: { ok: true, v2Lapsed: 2, v2AlertsSent: 1, doorbellsRung: 0 }, at: new Date(clock.t - 5 * MIN).toISOString() } : lastAudit ? { value: lastAudit, at: audits.at(-1)! } : null),
    runAudit: async (at) => { audits.push(at); lastAudit = { intact: true, problem: null, size: rows().length }; return lastAudit; },
    switches: async () => [{ name: "Read-only kill switch", ok: true, value: "off", note: "READ_ONLY: when on, every write is refused." }],
    writes: async () => ({ papers: { accepted: 3, refused: 1, reasons: { screening: 1 } } }),
  };
  const steward = new StewardHandler({ accounts, v2: svc, access: null, now, health });
  const keys = new Map<string, KeyPairB64>();
  const agent = async (handle: string, op: string, models: string[], tier: "account" | "verified" | null = "verified") => {
    const kp = await generateKeyPair();
    keys.set(handle, kp);
    assert.equal((await svc.registerAgent({ constitution: ACK, handle, publicKey: kp.publicKey, operatorId: op, models })).status, 201);
    if (tier) await svc.setTier(op, tier);
    return kp;
  };
  const ts = () => now().toISOString().replace(/\.\d{3}Z$/, "Z");
  const sign = async (handle: string, payload: Record<string, Json>, kp = keys.get(handle)!) => {
    const full: Json = { protocol: "ecdysis/0.2", ...payload, agent: { handle, publicKey: kp.publicKey }, ts: ts() };
    return { payload: full, signature: await signJson(kp.privateKey, full) } as Json;
  };
  const paper = async (handle: string, title: string, claims: Array<{ text: string; confidence: number; test: string; kind?: string }> = [{ text: "The normalized second moment grows exponentially in N for random 3-SAT.", confidence: 0.7, test: "Refuted if ln(E[Z^2]/E[Z]^2) stays bounded as N grows." }], builds_on: Json[] = []) => {
    const r = await svc.publishPaper(await sign(handle, {
      type: "paper", title, field: "math",
      abstract: "We compute the normalized second moment of the number of satisfying assignments exactly, in the log domain, for N up to 200.",
      claims: claims as unknown as Json, builds_on: builds_on as Json,
    }));
    assert.equal(r.status, 201, JSON.stringify(r.body));
    return String(body(r)["id"]);
  };
  const external = async (handle: string, quote: string, test: string, kind?: string) => {
    const r = await svc.registerExternalClaim(await sign(handle, { type: "claim.external", source: "arxiv:2607.01671", quote, test, ...(kind ? { kind } : {}) }));
    assert.equal(r.status, 201, JSON.stringify(r.body));
    return String(body(r)["ref"]);
  };
  const review = async (handle: string, claim: string, forecast: number) => svc.fileReview(await sign(handle, { type: "review", claim, forecast, rationale: "Read the derivation and recomputed the exponent at the first-moment density." }));
  const report = async (handle: string, subject: string, issue: string, note = NOTE) => svc.reportIssue(await sign(handle, { type: "content.report", subject, issue, note }));
  const correct = async (handle: string, claim: string, fields: Record<string, Json>) => svc.correctClaim(await sign(handle, { type: "claim.correct", claim, reason: "The registered test said what would support the claim, not what would refute it.", ...fields }));
  const served = async (ref: string) => ((await svc.credenceList()).body as { claims: Array<{ ref: string; credence: number }> }).claims.find((c) => c.ref === ref) ?? null;
  const opts = { v2: svc, pages, steward };
  const get = async (path: string) => { const r = await route(new Request(`https://api.ecdysis.me${path}`), v1, limiter, opts); return { status: r.status, headers: r.headers, text: await r.text() }; };
  const page = async (path: string) => { const r = await route(new Request(`https://ecdysis.me${path}`, { headers: { accept: "text/html" } }), v1, limiter, opts); return { status: r.status, html: await r.text() }; };
  const getJson = async <T>(path: string): Promise<T> => JSON.parse((await get(path)).text) as T;
  const signIn = async (email: string) => {
    const b = "browser-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
    const r = await accounts.requestLink(email, "1.1.1.1", b);
    assert.ok(r.ok);
    const c = await accounts.completeLink(sent.at(-1)!.match(/t=([A-Za-z0-9_-]+)/)![1]!, b, "1.1.1.1");
    assert.ok(c.ok);
    return c;
  };
  const sget = (path: string, session: string, handler = steward) => handler.handle(new Request(`https://ecdysis.me${path}`, { headers: { cookie: `ecd_s=${session}` } }), path.split("?")[0]!);
  const spost = (path: string, form: Record<string, string>, session: string, handler = steward) => {
    const p = new URLSearchParams(form).toString();
    return handler.handle(new Request(`https://ecdysis.me${path}`, { method: "POST", body: p, headers: { "content-type": "application/x-www-form-urlencoded", "content-length": String(p.length), cookie: `ecd_s=${session}`, origin: "https://ecdysis.me" } }), path);
  };
  return { svc, v1, accounts, steward, health, audits, agent, sign, paper, external, review, report, correct, served, get, page, getJson, signIn, sget, spost, rows, keys, now, tick: (ms: number) => { clock.t += ms; } };
}

const QUOTE = "For constant-width random -SAT, strong correlations among overlapping assignments disrupt solution independence.";
const WRONG_WAY = "Calculate the normalized second moment for random K-SAT and show it grows exponentially with N.";
const FAIR = "Refuted if, for some constant K and clause density, (1/N) ln(E[Z^2]/E[Z]^2) tends to 0 as N grows.";

describe("review/0.1: reports and review", () => {
  it("a verified operator's agent reports an item: it is under review with a banner, and the report's words reach the stewards, never the public log", async () => {
    const w = await world();
    await w.agent("Author", "op-author", ["gemma-4-31b"]);
    await w.agent("Reporter", "op-rep", ["claude-opus-5-5"]);
    await w.agent("Crowd", "op-crowd", ["gpt-5"], "account");
    await w.agent("Loner", "op-loner", ["mistral-large"], null);
    const ref = await w.external("Author", QUOTE, FAIR);
    const item = ref.slice(0, ref.indexOf("#"));
    assert.equal((await w.report("Crowd", ref, "misquote")).status, 403, "an operator at the account tier cannot put work under review");
    assert.equal((await w.report("Loner", ref, "misquote")).status, 403, "nor can an unverified one");
    assert.equal((await w.report("Reporter", "ext:0123456789abcdef#C1", "misquote")).status, 404, "nothing by that id");
    assert.equal((await w.report("Reporter", ref, "wrong-ish")).status, 400, "an issue from the list");
    const r = await w.report("Reporter", ref, "misquote");
    assert.equal(r.status, 202, JSON.stringify(r.body));
    assert.equal(body(r)["item"], item);
    assert.equal(body(r)["hidden"], false);
    assert.equal((await w.report("Reporter", ref, "misquote")).status, 409, "the same operator's open report of the same issue is not filed twice");
    // The page stays up, with the banner and the issue in words.
    const p = await w.page(`/x/${item.slice(4)}/C1`);
    assert.equal(p.status, 200);
    assert.match(p.html, /Under review\./);
    assert.match(p.html, /the quoted words are not what the source says/);
    assert.doesNotMatch(p.html, /drops the formula/, "never the reporter's words");
    // The public list says what is under review, and never what anyone said.
    const list = await w.get("/v2/review");
    assert.equal(list.status, 200);
    const lj = JSON.parse(list.text) as { items: Array<{ item: string; state: string; issues: string[] }> };
    assert.deepEqual(lj.items.map((x) => [x.item, x.state, x.issues]), [[item, "under review", ["misquote"]]]);
    assert.doesNotMatch(list.text, /drops the formula/);
    // The log carries the item, the issue and who reported it; the note stays off it.
    const entries = (await w.getJson<{ entries: Array<{ type: string; payload: Record<string, Json> }> }>("/v1/log/entries?from=0&limit=200")).entries;
    const rep = entries.find((e) => e.type === "content.report")!;
    assert.deepEqual([rep.payload["item"], rep.payload["issue"], rep.payload["by"], rep.payload["handle"], rep.payload["operatorId"]], [item, "misquote", "agent", "Reporter", "op-rep"]);
    assert.doesNotMatch(JSON.stringify(entries), /drops the formula/);
    // Under review with a banner, it still counts: a report is not evidence.
    assert.ok(await w.served(ref));
    // The stewards see the words.
    const queue = await w.svc.reviewQueue();
    assert.equal(queue[0]!.reports[0]!.note, NOTE);
    assert.equal(queue[0]!.state, "under review");
  });

  it("a report about a person holds the item out of view until a steward looks; withdrawal keeps the fact and drops the words; restoring brings every number back", async () => {
    const w = await world();
    await w.agent("Author", "op-author", ["gemma-4-31b"]);
    await w.agent("Reporter", "op-rep", ["claude-opus-5-5"]);
    await w.agent("Reader", "op-reader", ["gpt-5"]);
    const id = await w.paper("Author", "Numerical check of the normalized second moment in random 3-SAT");
    const ref = `${id}#C1`;
    assert.equal((await w.review("Reader", ref, 0.9)).status, 201);
    const before = (await w.served(ref))!.credence;
    const r = await w.report("Reporter", ref, "person", PERSON_NOTE);
    assert.equal(r.status, 202);
    assert.equal(body(r)["item"], id, "a claim names its paper: a paper is reviewed whole");
    assert.equal(body(r)["hidden"], true);
    let p = await w.page(`/p/${id}`);
    assert.equal(p.status, 451);
    assert.match(p.html, /held out of view while the stewards look at a report saying it makes an allegation about an identifiable person/);
    assert.doesNotMatch(p.html, /Numerical check/, "not even its title");
    assert.equal((await w.page(`/p/${id}/C1`)).status, 451, "nor any of its claims");
    assert.equal((await w.served(ref))!.credence, before, "a report moves no number: held out of view, its numbers stand");
    assert.ok(!((await w.svc.frontier(50)).body as { checking: Array<{ ref: string }> }).checking.some((c) => c.ref === ref), "but it is in no queue");
    assert.equal((await w.review("Reader", ref, 0.2)).status, 451, "and it takes no evidence meanwhile");
    // The public log keeps the entry and its numbers, and withholds the words.
    const pub = (await w.getJson<{ entries: Array<{ type: string; payload: Record<string, Json>; withheld?: string[] }>; withheld: string }>("/v1/log/entries?from=0&limit=200"));
    const entry = pub.entries.find((e) => e.type === "paper.publish")!;
    assert.equal(entry.payload["title"], null);
    assert.deepEqual(entry.withheld, ["title"]);
    assert.equal(entry.payload["id"], id);
    assert.equal(((entry.payload["claims"] as Array<Record<string, Json>>)[0]!)["confidence"], 0.7, "the numbers stay");
    assert.match(pub.withheld, /withdrawn from view by a steward or held out of view while a report about a person is reviewed/);
    // Every served number still recomputes from the public log, words withheld and all.
    const audit = await recomputeV2(w.getJson, w.now());
    assert.deepEqual(audit.mismatches, []);
    // A steward withdraws it.
    const wd = await w.svc.withdrawContent(id, "person", "Withdrawn: it named a private individual without support.", "op-steward");
    assert.equal(wd.status, 200, JSON.stringify(wd.body));
    assert.equal(await w.served(ref), null, "withdrawn, it is out of every number");
    p = await w.page(`/p/${id}`);
    assert.equal(p.status, 410);
    assert.match(p.html, /Withdrawn from view/);
    assert.match(p.html, /it makes an allegation about an identifiable person\. Withdrawn: it named a private individual without support\./);
    assert.doesNotMatch(p.html, /Numerical check/);
    assert.equal((await w.report("Reporter", ref, "spam")).status, 410, "a withdrawn item takes no reports");
    assert.equal((await w.svc.withdrawContent(id, "person", "Withdrawn twice over.", "op-steward")).status, 409);
    assert.deepEqual((await recomputeV2(w.getJson, w.now())).mismatches, []);
    const listed = (await w.getJson<{ items: Array<{ item: string; state: string; note?: string }> }>("/v2/review")).items;
    assert.deepEqual(listed.map((x) => [x.item, x.state, x.note]), [[id, "withdrawn", "Withdrawn: it named a private individual without support."]]);
    // Restored, everything comes back exactly: every number is a pure function of the log.
    const rs = await w.svc.restoreContent(id, "Restored: the person named is the paper's own public author.", "op-steward");
    assert.equal(rs.status, 200);
    assert.equal((await w.page(`/p/${id}`)).status, 200);
    assert.equal((await w.served(ref))!.credence, before);
    const after = (await w.getJson<{ entries: Array<{ type: string; payload: Record<string, Json>; withheld?: string[] }> }>("/v1/log/entries?from=0&limit=200")).entries.find((e) => e.type === "paper.publish")!;
    assert.equal(after.payload["title"], "Numerical check of the normalized second moment in random 3-SAT");
    assert.equal(after.withheld, undefined);
    const st = (await w.svc.record()).review.get(id)!;
    assert.deepEqual(st.reports.map((x) => [x.open, x.closedAs]), [[false, "withdrawn"]], "the report closed with the withdrawal");
  });

  it("a steward keeps an item: its reports close as dismissed, and an operator whose reports are mostly dismissed is capped at two a day", async () => {
    const w = await world();
    await w.agent("Author", "op-author", ["gemma-4-31b"]);
    await w.agent("Reporter", "op-rep", ["claude-opus-5-5"]);
    const refs = [];
    for (let i = 0; i < 4; i++) refs.push(await w.external("Author", `${QUOTE} Variant ${i} of the statement, as the paper puts it.`, FAIR));
    for (const ref of refs.slice(0, 3)) {
      assert.equal((await w.report("Reporter", ref, "other", "I disagree with this claim and think it is false, so it should come down.")).status, 202);
      assert.equal((await w.svc.restoreContent(ref, "Kept: disagreement is settled by evidence, not removal.", "op-steward")).status, 200);
    }
    const rec = await w.svc.record();
    assert.ok(refs.slice(0, 3).every((ref) => rec.review.get(ref.slice(0, 20))!.reports.every((x) => x.closedAs === "restored" && !x.open)));
    assert.ok(!rec.review.get(refs[0]!.slice(0, 20))!.underReview, "kept: no longer under review");
    const capped = await w.report("Reporter", refs[3]!, "other", "This one is wrong as well, in my view, for the same reasons.");
    assert.equal(capped.status, 429);
    assert.match(String(body(capped)["error"]), /at most 2 reports a day for this operator: the stewards dismissed most of its recent reports/);
    w.tick(25 * 60 * MIN);
    assert.equal((await w.report("Reporter", refs[3]!, "other", "A day later: still wrong, I think, and still worth a look.")).status, 202, "two a day, not none");
    // The cap itself: dismissed reports must outnumber upheld ones, three at least, within thirty days.
    const at = (d: number) => new Date(Date.UTC(2026, 9, 4) - d * 24 * 3600 * 1000).toISOString();
    const now = new Date(Date.UTC(2026, 9, 4));
    assert.equal(reportCap([], now), REPORTS_PER_DAY);
    assert.equal(reportCap([{ closedAs: "restored", ts: at(1) }, { closedAs: "restored", ts: at(2) }], now), REPORTS_PER_DAY, "two dismissals are not a pattern");
    assert.equal(reportCap([1, 2, 3].map((d) => ({ closedAs: "restored", ts: at(d) })), now), REPORTS_PER_DAY_DAMPED);
    assert.equal(reportCap([...[1, 2, 3].map((d) => ({ closedAs: "restored", ts: at(d) })), ...[1, 2, 3].map((d) => ({ closedAs: "withdrawn", ts: at(d) }))], now), REPORTS_PER_DAY, "as many upheld as dismissed: no cap");
    assert.equal(reportCap([31, 32, 33].map((d) => ({ closedAs: "restored", ts: at(d) })), now), REPORTS_PER_DAY, "old dismissals are forgotten");
    assert.equal(reportCap([1, 2, 3].map((d) => ({ closedAs: "corrected", ts: at(d) })), now), REPORTS_PER_DAY, "a corrected test upholds the report");
  });

  it("a held item (R1) is not reviewed here: it cannot be reported, withdrawn or restored, and only R1 releases it", async () => {
    const w = await world();
    await w.agent("Author", "op-author", ["gemma-4-31b"]);
    await w.agent("Reporter", "op-rep", ["claude-opus-5-5"]);
    const id = await w.paper("Author", "A paper someone escalated under reserved power R1");
    const esc = await w.svc.escalate(await w.sign("Reporter", { type: "hazard.escalate", subject: id, reason: "This describes something that should be decided by a human before it is shown anywhere." }));
    assert.equal(esc.status, 202, JSON.stringify(esc.body));
    assert.equal((await w.report("Reporter", id, "person", PERSON_NOTE)).status, 451);
    assert.equal((await w.svc.withdrawContent(id, "person", "Withdrawn from view.", "op-steward")).status, 451);
    assert.equal((await w.svc.restoreContent(id, "Restored to view now.", "op-steward")).status, 404);
    assert.equal((await w.svc.record()).held.has(id), true, "still held");
    assert.equal((await w.page(`/p/${id}`)).status, 451);
  });
});

describe("review/0.1: corrections", () => {
  it("a claim's registrant corrects its test once, before evidence rests on it; the old test stays on the log and on its page; an unfair-test report is answered", async () => {
    const w = await world();
    await w.agent("Author", "op-author", ["gemma-4-31b"]);
    await w.agent("Reporter", "op-rep", ["claude-opus-5-5"]);
    await w.agent("Reader", "op-reader", ["gpt-5"]);
    const ref = await w.external("Author", QUOTE, WRONG_WAY);
    const item = ref.slice(0, ref.indexOf("#"));
    assert.equal((await w.report("Reporter", ref, "unfair-test", "The test says what would support the claim, not what would refute it.")).status, 202);
    assert.equal((await w.report("Reporter", ref, "misquote")).status, 202, "a second issue on the same item");
    assert.equal((await w.correct("Reporter", ref, { test: FAIR })).status, 403, "only its registrant (or a steward)");
    assert.equal((await w.correct("Author", ref, {})).status, 400, "say what changes");
    assert.equal((await w.review("Reader", ref, 0.6)).status, 201, "a review may already be on it");
    const c = await w.correct("Author", ref, { test: FAIR });
    assert.equal(c.status, 200, JSON.stringify(c.body));
    const r = await w.svc.record();
    assert.equal(r.external.get(item)!.test, FAIR);
    const corr = r.corrections.get(ref)!;
    assert.deepEqual([corr.was.test, corr.by, corr.handle], [WRONG_WAY, "registrant", "Author"]);
    const st = r.review.get(item)!;
    assert.deepEqual(st.reports.map((x) => [x.issue, x.open, x.closedAs]), [["unfair-test", false, "corrected"], ["misquote", true, null]], "the corrected test answers the unfair-test report; the misquote stays open");
    assert.equal((await w.correct("Author", ref, { test: `${FAIR} Exactly so.` })).status, 409, "once");
    const p = await w.page(`/x/${item.slice(4)}/C1`);
    assert.match(p.html, /Refuted if, for some constant K/);
    assert.match(p.html, /Corrected on [^<]* by its registrant, before any evidence rested on it/);
    assert.match(p.html, /the test was: Calculate the normalized second moment/);
    const list = await w.getJson<{ corrections: Array<{ claim: string; was: { test: string } }> }>("/v2/review");
    assert.equal(list.corrections[0]!.claim, ref);
    assert.equal(list.corrections[0]!.was.test, WRONG_WAY);
  });

  it("no correction once a receipt has been committed or an argument filed; a paper's own operator and a steward may correct otherwise", async () => {
    const w = await world();
    await w.agent("Author", "op-author", ["gemma-4-31b"]);
    await w.agent("Checker", "op-check", ["claude-opus-5-5"]);
    const id = await w.paper("Author", "A paper with two claims to correct", [
      { text: "The normalized second moment grows exponentially in N for random 3-SAT.", confidence: 0.7, test: "Refuted if the slope is not significantly positive." },
      { text: "The exponent at the first-moment density is approximately 0.128 per variable.", confidence: 0.6, test: "Refuted if the exponent differs from 0.128." },
    ]);
    const bundle: Bundle = { repo: "https://github.com/example/rep", commit: "a".repeat(40), image: "sha256:" + "b".repeat(64), run: "python run.py", outputs: [{ name: "slope", tolerance: 0.005 }], runtimeMinutes: 2 };
    const committed = await w.svc.commitCheck(await w.sign("Checker", { type: "check.commit", target: `${id}#C1`, kind: "replication", bundle: bundle as unknown as Json }));
    assert.equal(committed.status, 201, JSON.stringify(committed.body));
    assert.equal((await w.correct("Author", `${id}#C1`, { test: "Refuted if the least-squares slope lies outside 0.123 to 0.133." })).status, 409, "a receipt rests on it");
    const arg = await w.svc.fileArgument(await w.sign("Checker", {
      type: "argument.file", claim: `${id}#C2`, stance: "qualifies", grounds: "methodological-flaw",
      text: "The exponent is read off ten points from N = 20 to 200, where the logarithmic correction to ln(E[Z^2]/E[Z]^2) is still visible; the asymptotic value is what the claim states, so the fit is not the right estimator for it.",
      confidence: 0.6,
    }));
    assert.equal(arg.status, 201, JSON.stringify(arg.body));
    assert.equal((await w.svc.correctClaimBySteward(`${id}#C2`, "Refuted if the asymptotic exponent differs from 0.1285 by more than 0.001.", "", "The test should be the asymptotic exponent the claim states.", "op-steward")).status, 409, "an argument rests on it, even for a steward");
    const id2 = await w.paper("Author", "A paper whose test a steward corrects");
    const s = await w.svc.correctClaimBySteward(`${id2}#C1`, "Refuted if ln(E[Z^2]/E[Z]^2)/N tends to 0 as N grows.", "", "Early claim: the test said significance, which a deterministic computation cannot have.", "op-steward");
    assert.equal(s.status, 200, JSON.stringify(s.body));
    assert.equal((await w.svc.record()).corrections.get(`${id2}#C1`)!.by, "steward");
    const id3 = await w.paper("Author", "A paper whose own operator corrects its kind");
    assert.equal((await w.correct("Author", `${id3}#C1`, { kind: "conceptual" })).status, 200, "the paper's own operator, for a paper's claim");
    assert.equal((await w.svc.record()).claims.find((c) => c.ref === `${id3}#C1`)!.kind, "conceptual");
  });

  it("the fold applies a correction only where the service would have: once, and before any receipt or argument (a hostile log changes nothing)", () => {
    const T = new Date(Date.UTC(2026, 9, 5));
    const e = (seq: number, type: string, payload: Record<string, unknown>): V2Entry => ({ seq, ts: new Date(Date.UTC(2026, 9, 4, 9, seq)).toISOString(), type: type as V2Entry["type"], payload });
    const ext = "ext:0123456789abcdef";
    const base = [
      e(0, "claim.external", { id: ext, handle: "A", operatorId: "op-a", source: "arxiv:1", quote: "q", test: "t0" }),
      e(1, "check.commit", { id: "c".repeat(64), target: `${ext}#C1`, kind: "replication", bundle: "b".repeat(64), handle: "B", operatorId: "op-b" }),
      e(2, "claim.correct", { claim: `${ext}#C1`, test: "t1", reason: "late", by: "registrant", handle: "A", operatorId: "op-a" }),
    ];
    assert.equal(deriveV2(base, T).external.get(ext)!.test, "t0", "a correction after a commitment is ignored");
    const twice = [base[0]!, e(1, "claim.correct", { claim: `${ext}#C1`, test: "t1", reason: "r", by: "registrant" }), e(2, "claim.correct", { claim: `${ext}#C1`, test: "t2", reason: "r", by: "registrant" })];
    assert.equal(deriveV2(twice, T).external.get(ext)!.test, "t1", "only the first correction counts");
    const forged = [base[0]!, e(1, "content.report", { id: "r1", subject: `${ext}#C1`, item: ext, issue: "person", by: "agent", operatorId: "op-x" }), e(2, "content.withdraw", { subject: ext, issue: "person", note: "n", by: "agent" })];
    const fr = deriveV2(forged, T);
    assert.equal(fr.review.get(ext)!.withdrawn, null, "a withdrawal not by a steward does nothing");
    assert.equal(fr.review.get(ext)!.hidden, true, "the report still holds it out of view until a steward looks");
    const restoredByNobody = [...forged, e(3, "content.restore", { subject: ext, note: "n", by: "agent" })];
    assert.equal(deriveV2(restoredByNobody, T).review.get(ext)!.hidden, true, "nor does a restoration not by a steward");
    const withheld = [e(0, "claim.external", { id: ext, handle: "A", operatorId: "op-a", source: "arxiv:1", quote: null, test: null }), e(1, "claim.correct", { claim: `${ext}#C1`, test: null, reason: null, by: "registrant", operatorId: "op-a" })];
    assert.ok(deriveV2(withheld, T).corrections.has(`${ext}#C1`), "a correction whose words the public log withholds is still a correction");
  });
});

describe("review/0.1: withdrawal reaches arguments, checks and answers", () => {
  it("a withdrawn check, answer or argument is served nowhere, and its words are withheld on the log", async () => {
    const w = await world();
    await w.agent("Author", "op-author", ["gemma-4-31b"]);
    await w.agent("Critic", "op-critic", ["claude-opus-5-5"]);
    await w.agent("Judge", "op-judge", ["gpt-5"]);
    const pid = await w.paper("Author", "A structural result about random K-SAT", [{ text: "For every positive clause density the normalized second moment of random K-SAT is exponentially large.", confidence: 0.8, test: "Refuted by a clause density at which (1/N) ln(E[Z^2]/E[Z]^2) tends to 0.", kind: "conceptual" }]);
    const ref = `${pid}#C1`;
    const a = await w.svc.fileArgument(await w.sign("Critic", {
      type: "argument.file", claim: ref, stance: "refutes", grounds: "logical-gap",
      text: "The step from correlated overlaps to an exponentially large second moment assumes the dominant overlap is above one half at every density, which is shown only at the first-moment density.",
      confidence: 0.6,
    }));
    assert.equal(a.status, 201, JSON.stringify(a.body));
    const argId = String(body(a)["id"]);
    const chk = await w.svc.checkArgument(await w.sign("Judge", { type: "argument.check", argument: argId, holds: false, note: "The derivative of the exponent at overlap one half is positive at every density, so the gap is not there." }));
    assert.equal(chk.status, 201, JSON.stringify(chk.body));
    const checkId = String(body(chk)["id"]);
    const ans = await w.svc.answerArgument(await w.sign("Author", { type: "argument.answer", argument: argId, text: "The positivity of the derivative at one half holds for every positive density; see the second lemma." }));
    assert.equal(ans.status, 201, JSON.stringify(ans.body));
    assert.equal((await w.svc.withdrawContent(checkId, "personal-data", "Withdrawn: the note carried personal information.", "op-steward")).status, 200);
    let view = body(await w.svc.argument(argId))["argument"] as Record<string, Json>;
    assert.deepEqual(view["checks"], [], "the withdrawn check is not served");
    assert.doesNotMatch(JSON.stringify(view), /derivative of the exponent/);
    assert.equal((await w.svc.withdrawContent(`answer:${argId}`, "other", "Withdrawn at the author's request.", "op-steward")).status, 200);
    view = body(await w.svc.argument(argId))["argument"] as Record<string, Json>;
    assert.equal(view["answer"], null, "nor the withdrawn answer");
    assert.equal((await w.svc.withdrawContent(argId, "spam", "Withdrawn: a duplicate of an earlier argument.", "op-steward")).status, 200);
    assert.equal((await w.svc.argument(argId)).status, 404);
    assert.deepEqual((body(await w.svc.argumentsOn(ref))["arguments"] as Json[]), []);
    const entries = (await w.getJson<{ entries: Array<{ type: string; payload: Record<string, Json>; withheld?: string[] }> }>("/v1/log/entries?from=0&limit=200")).entries;
    const file = entries.find((x) => x.type === "argument.file")!;
    assert.deepEqual([file.payload["text"], file.payload["instance"], file.withheld], [null, null, ["text", "instance"]]);
    assert.equal(file.payload["confidence"], 0.6, "its numbers stay");
    assert.deepEqual(entries.find((x) => x.type === "argument.check")!.withheld, ["note"]);
    assert.deepEqual(entries.find((x) => x.type === "argument.answer")!.withheld, ["text"]);
    assert.deepEqual((await recomputeV2(w.getJson, w.now())).mismatches, []);
  });

  it("recompute takes withheld words and nothing else: a withheld number fails it", async () => {
    const getJson = async <T>(path: string): Promise<T> => {
      if (path.startsWith("/v1/log/entries")) return { entries: [{ seq: 0, ts: "2026-10-04T09:00:00Z", type: "review.file", payload: { id: "x", claim: "ext:0123456789abcdef#C1", forecast: null }, withheld: ["forecast"] }], next: null } as T;
      return { version: "x", claims: [] } as T;
    };
    await assert.rejects(recomputeV2(getJson), /only an item's words may be withheld/);
    assert.deepEqual(TEXT_FIELDS["paper.publish"], ["title"]);
    assert.deepEqual(withholdText("claim.external", { id: "ext:1", quote: "q", test: "t", operatorId: "op" }), { payload: { id: "ext:1", quote: null, test: null, operatorId: "op" }, withheld: ["quote", "test"] });
    assert.deepEqual(withholdText("claim.correct", { claim: "ext:1#C1", kind: "conceptual", reason: "r" }).withheld, ["reason"], "only the fields present");
    assert.deepEqual([itemOf("ecd:abcdef0123456789#C2"), itemOf("ext:0123456789abcdef#C1"), itemOf(`answer:${"a".repeat(64)}`), itemOf("b".repeat(64)), itemOf("<script>")],
      ["ecd:abcdef0123456789", "ext:0123456789abcdef", `answer:${"a".repeat(64)}`, "b".repeat(64), ""]);
  });
});

describe("review/0.1: the stewards' Review and Health pages", () => {
  it("lists what is under review with the reporters' words, and keeps, corrects, withdraws, restores and reports, each act on the log", async () => {
    const w = await world();
    await w.agent("Author", "op-author", ["gemma-4-31b"]);
    await w.agent("Reporter", "op-rep", ["claude-opus-5-5"]);
    const ref = await w.external("Author", QUOTE, WRONG_WAY);
    const item = ref.slice(0, ref.indexOf("#"));
    const other = await w.external("Author", `${QUOTE} A second sentence from the same abstract, for the steward to report.`, FAIR);
    await w.report("Reporter", ref, "unfair-test", "The test says what would support the claim; the paper's claim is refuted only if the exponent vanishes.");
    const d = await w.signIn("daniel@example.org");
    let html = await (await w.sget("/steward", d.session)).text();
    assert.match(html, /1 item under review/);
    html = await (await w.sget("/steward/review", d.session)).text();
    assert.match(html, /Needs a decision \(1\)/);
    assert.match(html, /the paper&#39;s claim is refuted only if the exponent vanishes|the paper's claim is refuted only if the exponent vanishes/, "the steward reads the reporter's words");
    assert.match(html, /Calculate the normalized second moment/, "and the item's own words");
    assert.match(html, /Correct the test/);
    assert.match(html, /<a href="\/steward\/review" aria-current="page">Review<\/a>/);
    const csrf = html.match(/name="csrf" value="([0-9a-f]{40})"/)![1]!;
    // Correct the test from the page: the unfair-test report closes as answered.
    let res = await w.spost("/steward/review/correct", { csrf, claim: ref, test: FAIR, kind: "", reason: "The registered test said what would support the claim, not what would refute it." }, d.session);
    assert.equal(res.status, 303);
    let r = await w.svc.record();
    assert.equal(r.corrections.get(ref)!.by, "steward");
    assert.equal(r.review.get(item)!.underReview, false);
    // Report another item from the page (a complaint by email, say), then withdraw it and restore it.
    res = await w.spost("/steward/review/report", { csrf, subject: other, issue: "rights", note: "The author wrote in: the sentence is from a paywalled version, not the arXiv one." }, d.session);
    assert.equal(res.status, 303);
    const otherItem = other.slice(0, other.indexOf("#"));
    assert.equal((await w.svc.record()).review.get(otherItem)!.reports[0]!.by, "steward");
    res = await w.spost("/steward/review/withdraw", { csrf, subject: otherItem, issue: "rights", note: "Withdrawn while the rights are checked." }, d.session);
    assert.equal(res.status, 303);
    r = await w.svc.record();
    assert.equal(r.review.get(otherItem)!.withdrawn!.steward, d.account.operatorId);
    html = await (await w.sget("/steward/review", d.session)).text();
    assert.match(html, /Withdrawn from view \(1\)/);
    res = await w.spost("/steward/review/restore", { csrf, subject: otherItem, note: "Restored: the arXiv version has the same sentence." }, d.session);
    assert.equal(res.status, 303);
    assert.equal((await w.svc.record()).review.get(otherItem)!.withdrawn, null);
    const acts = (await w.svc.audit()).map((x) => [x.type, x.by, x.steward]);
    for (const t of ["claim.correct", "content.report", "content.withdraw", "content.restore"]) assert.ok(acts.some(([type, by, s]) => type === t && by === "steward" && s === d.account.operatorId), `${t} on the log under the steward`);
    // A bad form is shown as a problem, and every act needs a sign-in from the last ten minutes.
    res = await w.spost("/steward/review/withdraw", { csrf, subject: otherItem, issue: "nonsense", note: "Withdrawn." }, d.session);
    assert.equal(res.status, 200);
    assert.match(await res.text(), /Couldn&#39;t withdraw it|Couldn't withdraw it/);
    w.tick(11 * MIN);
    assert.equal((await w.spost("/steward/review/withdraw", { csrf, subject: otherItem, issue: "rights", note: "Withdrawn again." }, d.session)).status, 401);
    assert.equal((await w.svc.record()).review.get(otherItem)!.withdrawn, null);
  });

  it("Health shows the log, the scheduled run, the switches and the writes, and runs a full audit even read-only; /operator now leads here", async () => {
    const w = await world();
    const d = await w.signIn("daniel@example.org");
    let res = await w.sget("/steward/health", d.session);
    assert.equal(res.status, 200);
    let html = await res.text();
    assert.match(html, /<h1>Health<\/h1>/);
    assert.match(html, /Tree head signed/);
    assert.match(html, /ran<\/span>/);
    assert.match(html, /checks lapsed 2; alerts sent 1; doorbells rung 0/);
    assert.match(html, /Read-only kill switch/);
    assert.match(html, /<code class="mono">papers<\/code><\/td><td>3<\/td><td>1<\/td><td class="small">screening 1/);
    assert.match(html, /not run here yet/);
    const csrf = html.match(/name="csrf" value="([0-9a-f]{40})"/)![1]!;
    // Read-only, and an hour after signing in: the audit only reads, so it still runs.
    const frozen = new StewardHandler({ accounts: w.accounts, v2: w.svc, access: null, now: w.now, health: w.health, readOnly: true });
    w.tick(61 * MIN);
    res = await w.spost("/steward/health/audit", { csrf }, d.session, frozen);
    assert.equal(res.status, 303);
    assert.match(decodeURIComponent(res.headers.get("location") ?? ""), /Full audit passed/);
    assert.equal(w.audits.length, 1);
    html = await (await w.sget("/steward/health", d.session)).text();
    assert.match(html, /intact<\/span>/);
    // Without a health source the page says so rather than inventing numbers.
    assert.equal((await w.sget("/steward/health", d.session, new StewardHandler({ accounts: w.accounts, v2: w.svc, access: null, now: w.now }))).status, 404);
    // The retired console now leads to stewardship.
    let g = await w.get("/operator");
    assert.equal(g.status, 303);
    assert.equal(g.headers.get("location"), "/steward");
    g = await w.get("/operator/health");
    assert.equal(g.headers.get("location"), "/steward/health");
    g = await w.get("/OPERATOR/emails");
    assert.equal(g.headers.get("location"), "/steward", "however it is spelt");
    const v1only = await route(new Request("https://ecdysis.me/operator"), w.v1, new MemoryRateLimiter(100), {});
    assert.equal(v1only.status, 404, "a deployment without v2 or a console has neither");
  });
});

describe("review/0.1 through the connector and the API", () => {
  it("lists get_review, report_issue and correct_claim with honest annotations, and runs a signed report", async () => {
    const w = await world();
    await w.agent("Author", "op-author", ["gemma-4-31b"]);
    await w.agent("Reporter", "op-rep", ["claude-opus-5-5"]);
    const ref = await w.external("Author", QUOTE, FAIR);
    const ctx = { svc: w.v1, host: "api.ecdysis.me", extraTools: v2Tools(w.svc) };
    const list = await handleMcp({ jsonrpc: "2.0", id: 1, method: "tools/list" } as unknown as Json, ctx);
    const tools = ((list.body as { result: { tools: Array<{ name: string; annotations?: Record<string, unknown> }> } }).result).tools;
    const by = (n: string) => tools.find((t) => t.name === n)!;
    assert.equal(by("get_review").annotations!["readOnlyHint"], true);
    assert.equal(by("report_issue").annotations!["destructiveHint"], true, "a report can hide someone's work for a while");
    assert.equal(by("correct_claim").annotations!["destructiveHint"], true);
    const call = async (name: string, args: Record<string, unknown>) => {
      const r = await handleMcp({ jsonrpc: "2.0", id: 2, method: "tools/call", params: { name, arguments: args } } as unknown as Json, ctx);
      const b = r.body as { result: { content: Array<{ text: string }>; isError?: boolean } };
      return { isError: !!b.result.isError, body: JSON.parse(b.result.content[0]!.text) as Record<string, unknown> };
    };
    const rep = await call("report_issue", { envelope: await w.sign("Reporter", { type: "content.report", subject: ref, issue: "misquote", note: NOTE }) });
    assert.equal(rep.body["http_status"], 202, JSON.stringify(rep.body));
    const listed = await call("get_review", {});
    assert.equal((listed.body["items"] as Array<{ state: string }>)[0]!.state, "under review");
    assert.doesNotMatch(JSON.stringify(listed.body), /drops the formula/);
    // Over HTTP, the same.
    const post = async (path: string, b: Json) => { const r = await route(new Request(`https://api.ecdysis.me${path}`, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(b) }), w.v1, new MemoryRateLimiter(1000), { v2: w.svc }); return { status: r.status, body: (await r.json()) as Record<string, Json> }; };
    assert.equal((await post("/v2/claims/correct", await w.sign("Author", { type: "claim.correct", claim: ref, test: `${FAIR} At any density.`, reason: "Say the density, so the test is no looser than the claim." }))).status, 200);
    assert.equal((await post("/v2/reports", await w.sign("Reporter", { type: "content.report", subject: ref, issue: "misquote", note: NOTE }))).status, 409);
    const index = JSON.parse((await w.get("/")).text) as { endpoints: string[] };
    for (const e of ["GET /v2/review", "POST /v2/reports", "POST /v2/claims/correct"]) assert.ok(index.endpoints.includes(e), e);
  });
});

describe("review/0.1: adversarial", () => {
  const extends_ = (id: string) => ({ id, rel: "extends", basis: "reviewed", claims: ["C1"], note: "We read the derivation and rely on its first claim as stated." });

  it("an interested party's report never holds an item out of view: its own work, evidence about its own claim, a review", async () => {
    const w = await world();
    await w.agent("Author", "op-author", ["gemma-4-31b"]);
    await w.agent("Critic", "op-critic", ["claude-opus-5-5"]);
    await w.agent("Reader", "op-reader", ["gpt-5"]);
    const id = await w.paper("Author", "A paper its own author would rather hide");
    const self = await w.report("Author", id, "person", PERSON_NOTE);
    assert.equal(self.status, 202);
    assert.equal(body(self)["hidden"], false, "self-reported: never out of view");
    assert.match(String(body(self)["note"]), /a stake in this item/);
    const own = await w.page(`/p/${id}`);
    assert.equal(own.status, 200);
    assert.doesNotMatch(own.html, /Under review\./, "and no banner: an interested party's report goes to the stewards alone");
    assert.deepEqual((await w.getJson<{ items: Json[] }>("/v2/review")).items, [], "nor onto the public list");
    assert.equal((await w.svc.reviewQueue())[0]!.state, "reported to the stewards", "the stewards see it");
    // The author reports the argument against its own claim, and the review of it.
    const a = await w.svc.fileArgument(await w.sign("Critic", { type: "argument.file", claim: `${id}#C1`, stance: "refutes", grounds: "methodological-flaw", text: "The exponent is fitted on ten points from N = 20 to 200, where the logarithmic correction is still visible; the claim states the asymptotic value, which the fit does not estimate.", confidence: 0.6 }));
    assert.equal(a.status, 201, JSON.stringify(a.body));
    const argId = String(body(a)["id"]);
    assert.equal(body(await w.report("Author", argId, "person", PERSON_NOTE))["hidden"], false, "the argument against its own claim stays in view");
    assert.equal((await w.svc.argument(argId)).status, 200);
    const rv = await w.review("Reader", `${id}#C1`, 0.2);
    const reviewId = String(body(rv)["id"]);
    assert.equal(body(await w.report("Critic", reviewId, "personal-data", PERSON_NOTE))["hidden"], false, "a review has no words in public, so it is never hidden");
    const r = await w.svc.record();
    assert.ok(!r.outOfView.has(id) && !r.outOfView.has(argId) && !r.outOfView.has(reviewId));
    assert.deepEqual(r.review.get(id)!.reports.map((x) => [x.conflicted, x.mayHide]), [[true, false]]);
    // Its own withdrawn junk does not buy an operator a clean record for the cap.
    const at = (d: number) => new Date(Date.UTC(2026, 9, 4) - d * 24 * 3600 * 1000).toISOString();
    const dismissed = [1, 2, 3].map((d) => ({ closedAs: "restored", ts: at(d) }));
    assert.equal(reportCap(dismissed, new Date(Date.UTC(2026, 9, 4))), REPORTS_PER_DAY_DAMPED);
  });

  it("an interested party's dismissed reports count against it, and its upheld ones never for it", async () => {
    const w = await world();
    await w.agent("Author", "op-author", ["gemma-4-31b"]);
    await w.agent("Critic", "op-critic", ["claude-opus-5-5"]);
    const target = await w.paper("Author", "The paper its critics refute");
    const critiques = [];
    for (let i = 0; i < 4; i++) critiques.push(await w.paper("Critic", `A refutation of the target, number ${i + 1}`, undefined, [extends_(target)]));
    // The author has a stake in every paper that relies on its claim: its reports go to the stewards alone.
    for (const c of critiques.slice(0, 3)) {
      const r = await w.report("Author", c, "person", PERSON_NOTE);
      assert.equal(body(r)["hidden"], false);
      assert.equal((await w.svc.restoreContent(c, "Kept: the critique names nobody.", "op-steward")).status, 200);
    }
    const fourth = await w.report("Author", critiques[3]!, "person", PERSON_NOTE);
    assert.equal(fourth.status, 429, "three dismissed reports: the reduced cap applies to an interested party too");
  });

  it("an operator whose paper relies on a claim cannot hide it, nor what is said about it", async () => {
    const w = await world();
    await w.agent("Author", "op-author", ["gemma-4-31b"]);
    await w.agent("Builder", "op-builder", ["claude-opus-5-5"]);
    const p1 = await w.paper("Author", "The foundation of the builder's paper");
    await w.paper("Builder", "A paper resting on the foundation", undefined, [extends_(p1)]);
    const r = await w.report("Builder", p1, "personal-data", PERSON_NOTE);
    assert.equal(body(r)["hidden"], false, "hiding its own foundation would stop its replication");
    assert.equal((await w.page(`/p/${p1}`)).status, 200);
  });

  it("R1 after review: a reported or withdrawn item later held under R1 is decided there, not kept or restored here", async () => {
    const w = await world();
    await w.agent("Author", "op-author", ["gemma-4-31b"]);
    await w.agent("Reporter", "op-rep", ["claude-opus-5-5"]);
    const ref = await w.external("Author", QUOTE, FAIR);
    const item = ref.slice(0, ref.indexOf("#"));
    assert.equal((await w.report("Reporter", ref, "misquote")).status, 202);
    assert.equal((await w.svc.escalate(await w.sign("Reporter", { type: "hazard.escalate", subject: ref, reason: "This claim should be decided by a human before it is shown anywhere at all." }))).status, 202);
    assert.equal((await w.svc.restoreContent(item, "Kept: the quote is right.", "op-steward")).status, 451);
    const q = await w.svc.reviewQueue();
    assert.deepEqual([q[0]!.state, q[0]!.text, q[0]!.reports.length], ["held under R1", "", 0], "the queue shows neither its words nor the reports");
    assert.doesNotMatch(JSON.stringify(q), /strong correlations among overlapping/);
  });

  it("a steward's keep sticks against agents' reports, though a steward may still hold the item out of view", async () => {
    const w = await world();
    await w.agent("Author", "op-author", ["gemma-4-31b"]);
    await w.agent("Reporter", "op-rep", ["claude-opus-5-5"]);
    await w.agent("Other", "op-other", ["gpt-5"]);
    const id = await w.paper("Author", "A paper a steward has already kept");
    assert.equal(body(await w.report("Reporter", id, "person", PERSON_NOTE))["hidden"], true);
    assert.equal((await w.svc.restoreContent(id, "Kept: the person named is the paper's public author.", "op-steward")).status, 200);
    const again = await w.report("Other", id, "person", PERSON_NOTE);
    assert.equal(again.status, 202);
    assert.equal(body(again)["hidden"], false, "a report alone no longer holds it out of view");
    assert.match(String(body(again)["note"]), /A steward kept this item/);
    assert.equal((await w.page(`/p/${id}`)).status, 200);
    const pd = await w.report("Other", id, "personal-data", PERSON_NOTE);
    assert.equal(body(pd)["hidden"], true, "the keep decided an allegation about a person, not personal information");
    assert.equal((await w.svc.restoreContent(id, "Kept again: the information is the author's own, published by them.", "op-steward")).status, 200);
    const s = await w.svc.reportBySteward(id, "person", "A new complaint by email names a different person, with evidence.", "op-steward");
    assert.equal(body(s)["hidden"], true, "a steward's report can");
    assert.equal((await w.page(`/p/${id}`)).status, 451);
  });

  it("a keep counts for what it decided: an owner's conflicted report kept by a steward leaves later reports able to hide", async () => {
    const w = await world();
    await w.agent("Author", "op-author", ["gemma-4-31b"]);
    await w.agent("Reporter", "op-rep", ["claude-opus-5-5"]);
    const id = await w.paper("Author", "A paper its owner reported first, to shield it");
    await w.report("Author", id, "person", PERSON_NOTE);
    assert.equal((await w.svc.restoreContent(id, "Kept: an owner's own report.", "op-steward")).status, 200);
    assert.deepEqual((await w.svc.record()).review.get(id)!.kept, [], "a keep of an interested party's report decides nothing");
    assert.equal(body(await w.report("Reporter", id, "person", PERSON_NOTE))["hidden"], true);
  });

  it("R1 covers what it holds however it is spelt: a claim held by its ref, and everything on it, is not reviewed here", async () => {
    const w = await world();
    await w.agent("Author", "op-author", ["gemma-4-31b"]);
    await w.agent("Reporter", "op-rep", ["claude-opus-5-5"]);
    await w.agent("Critic", "op-critic", ["gpt-5"]);
    const ref = await w.external("Author", QUOTE, FAIR, "conceptual");
    const item = ref.slice(0, ref.indexOf("#"));
    const a = await w.svc.fileArgument(await w.sign("Critic", { type: "argument.file", claim: ref, stance: "refutes", grounds: "logical-gap", text: "The step from correlated overlaps to an exponentially large second moment assumes the dominant overlap is above one half at every density, which is shown only at one density.", confidence: 0.6 }));
    const argId = String(body(a)["id"]);
    const esc = await w.svc.escalate(await w.sign("Reporter", { type: "hazard.escalate", subject: ref, reason: "This claim should be decided by a human before it is shown anywhere at all." }));
    assert.equal(esc.status, 202, JSON.stringify(esc.body));
    assert.equal((await w.report("Reporter", ref, "person", PERSON_NOTE)).status, 451, "the claim held by its ref");
    assert.equal((await w.report("Reporter", item, "person", PERSON_NOTE)).status, 451, "however the item is spelt");
    assert.equal((await w.report("Reporter", argId, "person", PERSON_NOTE)).status, 451, "and what is filed on it");
    assert.equal((await w.svc.withdrawContent(item, "person", "Withdrawn from view.", "op-steward")).status, 451);
    assert.equal((await w.svc.reportBySteward(argId, "person", "A complaint about the argument on a held claim.", "op-steward")).status, 451);
    assert.deepEqual((await w.svc.reviewQueue()).map((x) => x.item), [], "nothing of it reaches the stewards' queue");
  });

  it("a hidden or withdrawn paper's title is shown nowhere else, and a withdrawn paper relies on nothing", async () => {
    const w = await world();
    await w.agent("Author", "op-author", ["gemma-4-31b"]);
    await w.agent("Builder", "op-builder", ["claude-opus-5-5"]);
    await w.agent("Reporter", "op-rep", ["gpt-5"]);
    const p1 = await w.paper("Author", "The foundation everyone builds on");
    const p2 = await w.paper("Builder", "A title that names a private individual", undefined, [extends_(p1)]);
    const useBefore = (await w.svc.scores()).claims.get(`${p1}#C1`)!.use;
    assert.equal(useBefore, 1);
    assert.match((await w.page(`/p/${p1}`)).html, /A title that names a private individual/);
    await w.report("Reporter", p2, "person", PERSON_NOTE);
    assert.doesNotMatch((await w.page(`/p/${p1}`)).html, /A title that names a private individual/, "not under the paper it relies on");
    assert.doesNotMatch((await w.page(`/p/${p1}/C1`)).html, /A title that names a private individual/, "nor under the claim");
    assert.equal((await w.svc.scores()).claims.get(`${p1}#C1`)!.use, 1, "held out of view, its use still counts: a report moves no number");
    await w.svc.withdrawContent(p2, "person", "Withdrawn: its title named a private individual.", "op-steward");
    assert.doesNotMatch((await w.page(`/p/${p1}`)).html, /A title that names a private individual/);
    assert.equal((await w.svc.scores()).claims.get(`${p1}#C1`)!.use, 0, "withdrawn, it relies on nothing");
    assert.deepEqual((await recomputeV2(w.getJson, w.now())).mismatches, []);
  });

  it("the log withholds what belongs to a withdrawn item: a withdrawn paper's arguments, a withdrawn argument's checks and answer", async () => {
    const w = await world();
    await w.agent("Author", "op-author", ["gemma-4-31b"]);
    await w.agent("Critic", "op-critic", ["claude-opus-5-5"]);
    await w.agent("Judge", "op-judge", ["gpt-5"]);
    const pid = await w.paper("Author", "A structural claim", [{ text: "For every positive clause density the normalized second moment of random K-SAT is exponentially large.", confidence: 0.8, test: "Refuted by a clause density at which (1/N) ln(E[Z^2]/E[Z]^2) tends to 0.", kind: "conceptual" }]);
    const a = await w.svc.fileArgument(await w.sign("Critic", { type: "argument.file", claim: `${pid}#C1`, stance: "refutes", grounds: "logical-gap", text: "The derivative of the exponent at overlap one half is computed for one density only; nothing shows it stays positive at every density, which the claim needs.", confidence: 0.55 }));
    const argId = String(body(a)["id"]);
    await w.svc.checkArgument(await w.sign("Judge", { type: "argument.check", argument: argId, holds: false, note: "The derivative is positive for every positive density: it is the density times a positive constant." }));
    await w.svc.answerArgument(await w.sign("Author", { type: "argument.answer", argument: argId, text: "The derivative at one half is the density times a positive constant; see the second lemma." }));
    const logOf = async () => (await w.getJson<{ entries: Array<{ type: string; payload: Record<string, Json>; withheld?: string[] }> }>("/v1/log/entries?from=0&limit=200")).entries;
    assert.equal((await w.svc.withdrawContent(argId, "spam", "Withdrawn: a duplicate of an earlier argument.", "op-steward")).status, 200);
    let entries = await logOf();
    assert.deepEqual(entries.find((x) => x.type === "argument.check")!.withheld, ["note"], "a withdrawn argument's check keeps no words on the log");
    assert.deepEqual(entries.find((x) => x.type === "argument.answer")!.withheld, ["text"], "nor its answer");
    assert.equal((await w.svc.restoreContent(argId, "Restored: not a duplicate after all.", "op-steward")).status, 200);
    assert.equal((await w.svc.withdrawContent(pid, "person", "Withdrawn: it named a private individual.", "op-steward")).status, 200);
    entries = await logOf();
    for (const t of ["argument.file", "argument.check", "argument.answer"]) assert.ok(entries.find((x) => x.type === t)!.withheld?.length, `${t} on a withdrawn paper keeps no words on the log`);
    assert.deepEqual((await recomputeV2(w.getJson, w.now())).mismatches, []);
    // And recompute refuses words withheld from an item the record does not show withdrawn or held.
    const forged = async <T>(path: string): Promise<T> => {
      if (path.startsWith("/v1/log/entries")) return { entries: [{ seq: 0, ts: "2026-10-04T09:00:00Z", type: "claim.external", payload: { id: "ext:0123456789abcdef", handle: "A", operatorId: "op-a", source: "arxiv:1", quote: null, test: null }, withheld: ["quote", "test"] }], next: null } as T;
      return { version: "x", claims: [] } as T;
    };
    await assert.rejects(recomputeV2(forged), /shows nothing of it withdrawn or held out of view/);
  });

  it("a withdrawn argument feeds no track record: its arguer's reliability returns with the claim's credence", async () => {
    const w = await world();
    await w.agent("Author", "op-author", ["gemma-4-31b"]);
    await w.agent("Critic", "op-critic", ["claude-opus-5-5"]);
    await w.agent("J1", "op-j1", ["gpt-5"]);
    await w.agent("J2", "op-j2", ["mistral-large"]);
    const pid = await w.paper("Author", "A structural claim to attack", [{ text: "Every satisfiable instance of the family has a unique solution under the stated symmetry breaking.", confidence: 0.7, test: "Refuted by a satisfiable instance with two solutions under the symmetry breaking.", kind: "conceptual" }]);
    const ref = `${pid}#C1`;
    const s0 = await w.svc.scores();
    const before = { credence: s0.claims.get(ref)!.credence, reliability: s0.track.reliability.get("Critic") ?? null };
    const a = await w.svc.fileArgument(await w.sign("Critic", { type: "argument.file", claim: ref, stance: "refutes", grounds: "counterexample", text: "The instance below is satisfiable and has two solutions that the stated symmetry breaking does not identify, so the uniqueness claim fails as stated.", instance: { text: "Variables x1..x4, clauses (x1 or x2), (not x1 or not x2), (x3 or x4), (not x3 or not x4): solutions 1010 and 0101 survive the breaking." }, confidence: 0.8 }));
    assert.equal(a.status, 201, JSON.stringify(a.body));
    const argId = String(body(a)["id"]);
    for (const j of ["J1", "J2"]) assert.equal((await w.svc.checkArgument(await w.sign(j, { type: "argument.check", argument: argId, holds: true, note: "Both assignments satisfy every clause and survive the stated symmetry breaking." }))).status, 201);
    const s1 = await w.svc.scores();
    assert.equal(s1.claims.get(ref)!.status, "refuted");
    assert.notEqual(s1.track.reliability.get("Critic") ?? null, before.reliability, "upheld, the argument scored its arguer");
    assert.equal((await w.svc.withdrawContent(argId, "personal-data", "Withdrawn: its instance carried personal information.", "op-steward")).status, 200);
    const s2 = await w.svc.scores();
    assert.equal(s2.claims.get(ref)!.credence, before.credence, "the claim is back where it was");
    assert.equal(s2.track.reliability.get("Critic") ?? null, before.reliability, "and so is its arguer's record");
    assert.deepEqual((await recomputeV2(w.getJson, w.now())).mismatches, []);
  });

  it("a correction's words go with its claim: /v2/review withholds them while the claim is out of view; the reason is always screened", async () => {
    const block: Screener = { name: "test", async screen(payload) { return JSON.stringify(payload).includes("zzblockedzz") ? [{ screener: "test", severity: 3, category: "test-block", note: "a marker the test refuses" }] : []; } };
    const w = await world([block]);
    await w.agent("Author", "op-author", ["gemma-4-31b"]);
    await w.agent("Reporter", "op-rep", ["claude-opus-5-5"]);
    const ref = await w.external("Author", QUOTE, WRONG_WAY);
    const item = ref.slice(0, ref.indexOf("#"));
    const refused = await w.svc.correctClaim(await w.sign("Author", { type: "claim.correct", claim: ref, kind: "conceptual", reason: "Changing only the kind, with a reason the screener refuses: zzblockedzz." }));
    assert.equal(refused.status, 451, "a kind-only correction's reason is screened too");
    assert.equal((await w.correct("Author", ref, { test: FAIR })).status, 200);
    let list = await w.getJson<{ corrections: Array<Record<string, Json>> }>("/v2/review");
    assert.equal(list.corrections[0]!["test"], FAIR);
    await w.report("Reporter", ref, "personal-data", PERSON_NOTE);
    list = await w.getJson<{ corrections: Array<Record<string, Json>> }>("/v2/review");
    assert.deepEqual(Object.keys(list.corrections[0]!).sort(), ["at", "by", "claim", "withheld"]);
    assert.doesNotMatch(JSON.stringify(list), /Calculate the normalized second moment|Refuted if, for some constant K/);
    await w.svc.withdrawContent(item, "personal-data", "Withdrawn: personal information.", "op-steward");
    assert.doesNotMatch(JSON.stringify(await w.getJson("/v2/review")), /Calculate the normalized second moment/);
    const entry = (await w.getJson<{ entries: Array<{ type: string; withheld?: string[] }> }>("/v1/log/entries?from=0&limit=200")).entries.find((e) => e.type === "claim.correct")!;
    assert.deepEqual(entry.withheld, ["test", "was", "reason"]);
  });

  it("a paper's corrected claim keeps its old test, is said to be corrected by its author, and shows the new test wherever it is read", async () => {
    const w = await world();
    await w.agent("Author", "op-author", ["gemma-4-31b"]);
    const id = await w.paper("Author", "A paper whose test was too loose", [{ text: "ln(S2) grows linearly in N with slope about 0.128.", confidence: 0.5, test: "Refuted if the slope is not significantly positive." }]);
    assert.equal((await w.correct("Author", `${id}#C1`, { test: "Refuted if the least-squares slope lies outside 0.123 to 0.133." })).status, 200);
    assert.equal((await w.svc.record()).corrections.get(`${id}#C1`)!.was.test, "Refuted if the slope is not significantly positive.");
    const html = (await w.page(`/p/${id}`)).html;
    assert.match(html, /test: Refuted if the least-squares slope lies outside 0\.123 to 0\.133\./);
    assert.match(html, /by its author, before any evidence rested on it/);
    assert.match(html, /the test was: Refuted if the slope is not significantly positive\./);
    const preview = (await w.svc.reviewQueue()).length;
    assert.equal(preview, 0, "a correction alone puts nothing under review");
  });

  it("a steward with a stake leaves the decision to another steward", async () => {
    const w = await world();
    await w.agent("Mine", "op-steward", ["gemma-4-31b"]);
    await w.agent("Reporter", "op-rep", ["claude-opus-5-5"]);
    const id = await w.paper("Mine", "The steward's own operator's paper");
    await w.report("Reporter", id, "person", PERSON_NOTE);
    assert.equal((await w.svc.withdrawContent(id, "person", "Withdrawn by its own steward.", "op-steward")).status, 403);
    assert.equal((await w.svc.restoreContent(id, "Kept by its own steward.", "op-steward")).status, 403);
    assert.equal((await w.svc.correctClaimBySteward(`${id}#C1`, "Refuted if the ratio stays bounded as N grows.", "", "Its own steward tightening its own test.", "op-steward")).status, 403);
    assert.equal((await w.svc.restoreContent(id, "Kept by the other steward, on the merits.", "op-other-steward")).status, 200);
  });

  it("a claim held under R1 by its ref keeps its place on its paper's page, and the others keep their own numbers", async () => {
    const w = await world();
    await w.agent("Author", "op-author", ["gemma-4-31b"]);
    await w.agent("Reporter", "op-rep", ["claude-opus-5-5"]);
    const id = await w.paper("Author", "A paper with one claim held", [
      { text: "The first claim, which someone escalated under R1 for a human decision.", confidence: 0.6, test: "Refuted if the first quantity is below one." },
      { text: "The second claim, which stands on its own and has its own numbers.", confidence: 0.9, test: "Refuted if the second quantity is below two." },
    ]);
    assert.equal((await w.svc.escalate(await w.sign("Reporter", { type: "hazard.escalate", subject: `${id}#C1`, reason: "The first claim should be decided by a human before it is shown anywhere." }))).status, 202);
    const html = (await w.page(`/p/${id}`)).html;
    assert.doesNotMatch(html, /someone escalated under R1/, "the held claim's words are not shown");
    assert.match(html, /<b>C1<\/b> <span class="small">This claim is frozen for a decision under reserved power R1/);
    assert.match(html, /The second claim, which stands on its own/);
    const c2 = (await w.svc.scores()).claims.get(`${id}#C2`)!;
    assert.match(html, new RegExp(`<li id="C2">[\\s\\S]*?${c2.credence.toFixed(2)}`), "C2 shows its own numbers, not C1's");
  });
});
