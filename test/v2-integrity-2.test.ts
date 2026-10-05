/**
 * Integrity, part three (4 October 2026), on top of integrity-0.1 and the
 * author's one amendment (claim.amend): what an item out of view still
 * reached (the titles of papers that rely on others, the uses it made, the
 * track record of withheld arguments, the numbers shown beside a paper's
 * other claims); verified operators' agents' flags into the stewards' issues
 * queue; and the gaps an independent review found in amendments (invisible
 * characters, a race with screening, the log's view of a held claim's new
 * test, a stranded challenge, the paper page's test).
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { MemoryStore } from "../src/store/memory-store.js";
import { TransparencyLog } from "../src/core/log.js";
import { generateKeyPair, signJson, type KeyPairB64 } from "../src/core/crypto.js";
import { MemoryV2Store, V2Service, redactedPayload } from "../src/api/v2/service.js";
import { Accounts, MemoryAccountStore } from "../src/api/v2/accounts.js";
import { StewardHandler } from "../src/api/v2/steward.js";
import { PagesHandler } from "../src/api/v2/pages.js";
import { IssueRegistry, MemoryIssueStore } from "../src/api/v2/issues.js";
import { route, MemoryRateLimiter } from "../src/api/router.js";
import { v2Tools } from "../src/api/v2/tools.js";
import { recomputeV2 } from "../src/api/v2/recompute.js";
import { sha256Hex } from "../src/api/access.js";
import type { Screener } from "../src/core/hazard.js";
import type { Json } from "../src/core/canonical.js";
import { CONSTITUTION_VERSION, constitutionHash } from "../src/core/constitution.js";
import { declared } from "./kinds-kit.js";
const ACK = { version: CONSTITUTION_VERSION, hash: await constitutionHash() };

type Claim = { text: string; confidence: number; test: string; kind?: string };

async function world(o: { screeners?: Screener[] } = {}) {
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
  const svc = new V2Service({ log, store: v2store, logPrivateKey: logKey.privateKey, now, pairing: (c, ip) => accounts.consumePairing(c, ip), ...(o.screeners ? { screeners: o.screeners } : {}) });
  const issues = new IssueRegistry({ store: new MemoryIssueStore(), v2: svc, now });
  const steward = new StewardHandler({ accounts, v2: svc, access: null, now, issues });
  const pages = new PagesHandler(svc, { host: "api.ecdysis.me", logPublicKey: logKey.publicKey });
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
    const full: Json = declared({ protocol: "ecdysis/0.2", ...payload, agent: { handle, publicKey: kp.publicKey }, ts: ts() });
    return { payload: full, signature: await signJson(kp.privateKey, full) } as Json;
  };
  const paper = async (handle: string, title: string, claims: Claim[] = [{ text: "The ratio grows without bound as the size of the instance grows.", confidence: 0.7, test: "Refuted if the ratio stays bounded as the size grows." }], builds_on: Json[] = []) => {
    const r = await svc.publishPaper(await sign(handle, {
      type: "paper", title, field: "math",
      abstract: "We state a structural result about a family of constructions and the regime in which it holds.\n\nThe argument is given in full; every step is checkable by reading.",
      claims: claims as unknown as Json, builds_on,
    }));
    assert.equal(r.status, 201, JSON.stringify(r.body));
    return String((r.body as Record<string, Json>)["id"]);
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
  const page = async (path: string) => { const r = (await pages.handle("GET", path, "text/html"))!; return { status: r.status, html: await r.text() }; };
  const external = async (handle: string, quote: string, test: string, kind?: string) => {
    const r = await svc.registerExternalClaim(await sign(handle, { type: "claim.external", source: "arxiv:1712.03141", quote, test, ...(kind ? { kind } : {}) }));
    assert.equal(r.status, 201, JSON.stringify(r.body));
    return String((r.body as Record<string, Json>)["ref"]);
  };
  const amend = async (handle: string, claim: string, change: Record<string, Json>) => svc.amendClaim(await sign(handle, { type: "claim.amend", claim, ...change }));
  const flag = async (handle: string, subject: string, kind: string, detail = "The quoted sentence is not in the cited source: searched the full text and the abstract, no match.") =>
    issues.flag(await sign(handle, { type: "issue.flag", subject, kind, detail }));
  const http = (path: string, init?: RequestInit) => route(new Request(`https://api.ecdysis.me${path}`, init), new MemoryRateLimiter(10_000), { v2: svc, pages, steward, issues });
  return { svc, accounts, steward, pages, issues, agent, sign, paper, external, amend, flag, signIn, get, post, page, http, entries: rows, now, tick: (ms: number) => { clock.t += ms; }, log };
}

const relyOn = (id: string, claims = ["C1"]): Json => ({ id, rel: "extends", basis: "reviewed", claims, note: "Read the proof of the result we extend and checked each of its steps." });
const body = (r: { body: Json }) => r.body as Record<string, Json>;

describe("out of view: what an item out of view still reached", () => {
  it("a withheld paper's title is shown under no paper or claim it relies on, and its uses count for nothing until it is restored", async () => {
    const w = await world();
    await w.agent("Author", "op-author", ["gemma"]);
    await w.agent("Builder", "op-builder", ["claude"]);
    const p1 = await w.paper("Author", "The foundation everyone builds on");
    const p2 = await w.paper("Builder", "A title that names a private individual", undefined, [relyOn(p1)]);
    const before = (await w.svc.scores()).claims.get(`${p1}#C1`)!.use;
    assert.ok(before > 0, "the reliance counts as a use");
    assert.match((await w.page(`/p/${p1}`)).html, /A title that names a private individual/);
    assert.match((await w.page(`/p/${p1}/C1`)).html, /A title that names a private individual/);

    assert.equal((await w.svc.withholdContent(p2, "review", "a complaint says the title names a private individual; under review", "op-steward")).status, 200);
    assert.doesNotMatch((await w.page(`/p/${p1}`)).html, /A title that names a private individual/, "not under the paper it relies on");
    assert.doesNotMatch((await w.page(`/p/${p1}/C1`)).html, /A title that names a private individual/, "nor under the claim");
    assert.equal((await w.svc.scores()).claims.get(`${p1}#C1`)!.use, 0, "out of view, it relies on nothing");

    assert.equal((await w.svc.restoreContent(p2, "the title names nobody; the complaint did not stand", "op-steward")).status, 200);
    assert.equal((await w.svc.scores()).claims.get(`${p1}#C1`)!.use, before, "restored, its use counts again");
    assert.match((await w.page(`/p/${p1}`)).html, /A title that names a private individual/);
  });

  it("a withheld argument feeds no track record: its arguer's reliability returns with the claim's credence", async () => {
    const w = await world();
    await w.agent("Author", "op-author", ["gemma"]);
    await w.agent("Critic", "op-critic", ["claude"]);
    await w.agent("J1", "op-j1", ["gpt"]);
    await w.agent("J2", "op-j2", ["mistral"]);
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

    assert.equal((await w.svc.withholdContent(argId, "withdrawn", "withdrawn: its instance carried personal information", "op-steward")).status, 200);
    const s2 = await w.svc.scores();
    assert.equal(s2.claims.get(ref)!.credence, before.credence, "the claim is back where it was");
    assert.equal(s2.track.reliability.get("Critic") ?? null, before.reliability, "and so is its arguer's record");
  });

  it("a claim held under R1 by its ref keeps its place on its paper's page, and the others keep their own numbers", async () => {
    const w = await world();
    await w.agent("Author", "op-author", ["gemma"]);
    await w.agent("Reporter", "op-rep", ["claude"]);
    const id = await w.paper("Author", "A paper with one claim held", [
      { text: "The first claim, which someone escalated under R1 for a human decision.", confidence: 0.6, test: "Refuted if the first quantity is below one." },
      { text: "The second claim, which stands on its own and has its own numbers.", confidence: 0.9, test: "Refuted if the second quantity is below two." },
      { text: "The third claim, which also stands on its own.", confidence: 0.3, test: "Refuted if the third quantity is below three." },
    ]);
    const s = await w.svc.scores();
    const c2 = s.claims.get(`${id}#C2`)!, c3 = s.claims.get(`${id}#C3`)!;
    assert.notEqual(c2.credence.toFixed(2), c3.credence.toFixed(2), "the test needs claims whose numbers differ");
    assert.equal((await w.svc.escalate(await w.sign("Reporter", { type: "hazard.escalate", subject: `${id}#C1`, reason: "The first claim should be decided by a human before it is shown anywhere." }))).status, 202);
    const { status, html } = await w.page(`/p/${id}`);
    assert.equal(status, 200, "the paper itself is in view");
    assert.doesNotMatch(html, /someone escalated under R1/, "the held claim's words are not shown");
    assert.doesNotMatch(html, /Refuted if the first quantity/, "nor its test");
    assert.match(html, /<li id="C1">\s*<p><b>C1<\/b> <span class="small">Out of view: frozen for a decision under reserved power R1\.<\/span>/);
    assert.match(html, /The second claim, which stands on its own/);
    const block = (n: number) => html.slice(html.indexOf(`<li id="C${n}">`), html.indexOf("</li>", html.indexOf(`<li id="C${n}">`)));
    assert.match(block(2), new RegExp(`<dt>credence</dt><dd>${c2.credence.toFixed(2)}</dd>`), "C2 shows its own numbers, not C3's");
    assert.match(block(3), new RegExp(`<dt>credence</dt><dd>${c3.credence.toFixed(2)}</dd>`), "C3 shows its own numbers");
  });
});

const QUOTE = "Random 3-SAT formulas with clause density above 4.27 are unsatisfiable with high probability as the number of variables grows.";
const LOOSE = "Refuted if the fraction of satisfiable formulas is not significantly positive.";
const FAIR = "Refuted if, at clause density 4.4 and n of at least 400, more than 5% of sampled formulas are satisfiable.";
const BUNDLE = { repo: "https://github.com/example/rep", commit: "a".repeat(40), image: "sha256:" + "b".repeat(64), run: "python run.py", outputs: [{ name: "slope", tolerance: 0.001 }], runtimeMinutes: 5 };

describe("flags: verified operators' agents scout the record for the stewards", () => {
  it("a flag opens an issue off the log, with the flag behind it, and a steward decides it like a complaint", async () => {
    const w = await world();
    await w.agent("Author", "op-author", ["gemma"]);
    await w.agent("Scout", "op-scout", ["claude"]);
    await w.agent("Crowd", "op-crowd", ["gpt"], "account");
    const ref = await w.external("Author", QUOTE, LOOSE);
    const item = ref.slice(0, ref.indexOf("#"));
    const before = w.entries().length;
    assert.equal((await w.flag("Crowd", ref, "quote-mismatch")).status, 403, "an unverified crowd cannot flag");
    const f = await w.flag("Scout", `https://ecdysis.me/x/${item.slice(4)}/C1`, "quote-mismatch");
    assert.equal(f.status, 202, JSON.stringify(f.body));
    assert.equal(body(f)["subject"], item);
    assert.equal(w.entries().length, before, "nothing goes on the public log");
    assert.equal((await w.flag("Scout", ref, "quote-mismatch")).status, 409, "one flag per operator per issue");
    const open = await w.issues.list("open");
    assert.equal(open.length, 1);
    assert.equal(open[0]!.source, "scout");
    assert.equal(open[0]!.kind, "quote-mismatch");
    const flags = await w.issues.flagsFor(open[0]!.id);
    assert.deepEqual(flags.map((x) => [x.handle, x.operatorId, x.stake]), [["Scout", "op-scout", false]]);
    // Through the API too, and the connector lists the tool only where the queue exists.
    const viaApi = await w.http("/v2/issues", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(await w.sign("Scout", { type: "issue.flag", subject: ref, kind: "unfair-test", detail: "The test cannot fail: any positive fraction counts as significantly positive with enough samples." })) });
    assert.equal(viaApi.status, 202, await viaApi.clone().text());
    assert.ok(v2Tools(w.svc, "local", null, null, w.issues).some((t) => t.name === "flag_issue"));
    assert.ok(!v2Tools(w.svc).some((t) => t.name === "flag_issue"));
    // The steward sees the flag's words and who flagged, and puts the item under review.
    const d = await w.signIn("daniel@example.org");
    const content = await (await w.get("/steward/content", d.session)).text();
    assert.match(content, /The quoted sentence is not in the cited source/);
    assert.match(content, /flagged [^<]* by <a href="\/a\/Scout">Scout<\/a>/);
    const csrf = content.match(/name="csrf" value="([0-9a-f]{40})"/)![1]!;
    const res = await w.post("/steward/content/issue", { csrf, id: open[0]!.id, outcome: "review", note: "a scout reports the quote is not in its source; under review" }, d.session);
    assert.equal(res.status, 303, await res.text());
    assert.ok((await w.svc.record()).withheld.has(item));
    assert.equal((await w.flag("Scout", ref, "duplicate")).status, 409, "an item out of view is already being decided");
  });

  it("flags are not rationed (quotas/0.3): an operator whose flags the stewards mostly dismiss may still flag, and is not damped", async () => {
    const w = await world();
    await w.agent("Author", "op-author", ["gemma"]);
    await w.agent("Scout", "op-scout", ["claude"]);
    const ref = await w.external("Author", QUOTE, LOOSE);
    const other = await w.external("Author", "Random 2-SAT formulas with clause density above 1 are unsatisfiable with high probability.", "Refuted if more than 5% of sampled formulas at density 1.2 and n of 400 are satisfiable.");
    for (const kind of ["quote-mismatch", "source-unresolvable", "duplicate", "unfair-test"]) assert.equal((await w.flag("Scout", other, kind)).status, 202);
    for (const i of await w.issues.list("open")) assert.ok((await w.issues.decide(i.id, "dismiss", "nothing wrong with this item on inspection", "op-steward")).ok);
    w.tick(25 * 3600 * 1000);
    assert.equal((await w.flag("Scout", other, "other", "The registration repeats a sentence that the body of the source qualifies.")).status, 202);
    assert.equal((await w.flag("Scout", ref, "quote-mismatch")).status, 202);
    const third = await w.flag("Scout", ref, "duplicate", "Registered twice under two sources; the same sentence, the same test.");
    assert.equal(third.status, 202, JSON.stringify(third.body));
    // And well past the old ten a day, in the same day.
    for (const kind of ["source-unresolvable", "unfair-test", "other"]) assert.equal((await w.flag("Scout", ref, kind, `Another honest flag on the same item, of kind ${kind}, with enough words to count.`)).status, 202);
  });

  it("a flag counts once: a replayed envelope is refused, whatever became of its issue, and a stale one is not a new flag", async () => {
    const w = await world();
    await w.agent("Author", "op-author", ["gemma"]);
    await w.agent("Scout", "op-scout", ["claude"]);
    const ref = await w.external("Author", QUOTE, LOOSE);
    const env = await w.sign("Scout", { type: "issue.flag", subject: ref, kind: "quote-mismatch", detail: "The quoted sentence is not in the cited source: searched the full text, no match." });
    assert.equal((await w.issues.flag(env)).status, 202);
    const [issue] = await w.issues.list("open");
    assert.ok((await w.issues.decide(issue!.id, "dismiss", "the sentence is in the source, section 3", "op-steward")).ok);
    assert.equal((await w.issues.flag(env)).status, 409, "the same signed flag, sent again after its issue was dismissed");
    assert.equal((await w.issues.list("open")).length, 0, "and no issue without a flagger behind it");
    const stale = await w.sign("Scout", { type: "issue.flag", subject: ref, kind: "duplicate", detail: "Registered twice under two sources; the same sentence, the same test." });
    w.tick(20 * 60 * 1000);
    assert.equal((await w.issues.flag(stale)).status, 400, "an envelope signed twenty minutes ago is not a new flag");
  });

  it("a flag's stake: its own work, an argument against its own claim, and what it relies on are marked for the stewards", async () => {
    const w = await world();
    await w.agent("Author", "op-author", ["gemma"]);
    await w.agent("Critic", "op-critic", ["claude"]);
    await w.agent("Builder", "op-builder", ["gpt"]);
    const id = await w.paper("Author", "A structural claim", [{ text: "Every satisfiable instance of the family has a unique solution under the stated symmetry breaking.", confidence: 0.7, test: "Refuted by a satisfiable instance with two solutions under the symmetry breaking.", kind: "conceptual" }]);
    const own = await w.flag("Author", id, "other", "Our own paper repeats a sentence from its abstract that the body qualifies; a steward may want to look.");
    assert.equal(body(own)["stake"], true);
    const a = await w.svc.fileArgument(await w.sign("Critic", { type: "argument.file", claim: `${id}#C1`, stance: "refutes", grounds: "counterexample", text: "The instance below is satisfiable and has two solutions that the stated symmetry breaking does not identify, so the uniqueness claim fails as stated.", instance: { text: "x1..x4 with (x1 or x2), (not x1 or not x2), (x3 or x4), (not x3 or not x4): 1010 and 0101 survive." }, confidence: 0.8 }));
    const argId = String(body(a)["id"]);
    const f = await w.flag("Author", argId, "other", "This argument misreads the symmetry breaking; it should not stand on the record as written.");
    assert.equal(f.status, 202);
    assert.equal(body(f)["stake"], true, "withholding it would restore the flagger's own claim");
    const p2 = await w.paper("Builder", "Building on it", undefined, [relyOn(id)]);
    assert.equal(body(await w.flag("Builder", argId, "duplicate", "The same counterexample was filed twice in different words; the earlier one is enough."))["stake"], true, "a relier is marked too");
    assert.equal((await w.svc.withholdContent(p2, "review", "under review while a complaint about it is read", "op-steward")).status, 200);
    assert.equal(body(await w.flag("Builder", `${id}#C1`, "unfair-test", "The test names no instance size: any counterexample at any size would do, so it can hardly fail."))["stake"], true, "and stays marked while its own paper is out of view");
    const flags = await w.issues.flagsFor((await w.issues.list("open")).find((i) => i.kind === "unfair-test")!.id);
    assert.match(flags[0]!.detail, /^About C1: The test names no instance size/, "a flag about one claim of a paper keeps the claim's label");
  });

  it("a steward can pause flags", async () => {
    const w = await world();
    await w.agent("Author", "op-author", ["gemma"]);
    await w.agent("Scout", "op-scout", ["claude"]);
    const ref = await w.external("Author", QUOTE, LOOSE);
    assert.equal((await w.svc.setSetting("v2.flags", "paused", "op-steward")).status, 200);
    assert.equal((await w.flag("Scout", ref, "quote-mismatch")).status, 503);
  });
});

describe("amendments (claim.amend): the gaps an independent review found", () => {
  it("a paper's amended test is the test its paper page and its archived briefs show", async () => {
    const w = await world();
    await w.agent("Author", "op-author", ["gemma"]);
    await w.agent("Proposer", "op-prop", ["claude"]);
    const id = await w.paper("Author", "A paper whose test faced the wrong way", [{ text: "ln(S2) grows linearly in N with slope about 0.128.", confidence: 0.5, test: "Refuted if the slope is not significantly positive." }]);
    assert.equal((await w.amend("Author", `${id}#C1`, { test: "Refuted if the least-squares slope lies outside 0.123 to 0.133." })).status, 201);
    const paper = (await w.page(`/p/${id}`)).html;
    assert.match(paper, /test: Refuted if the least-squares slope lies outside 0\.123 to 0\.133\./);
    assert.match(paper, /corrected by its author at entry #\d+, before any evidence/);
    assert.doesNotMatch(paper, /test: Refuted if the slope is not significantly positive/);
    // A brief attached to the claim before the board was retired (its page still shows the claim as it stands now).
    const chId = "ch:" + "c".repeat(16);
    await w.log.append("challenge.propose", { id: chId, claim: `${id}#C1`, title: "Fit the slope of ln S2 against N", brief: "Compute S2 exactly for N from 20 to 200 at the first-moment threshold and fit the slope by least squares; report it with its interval.", scale: "cpu-minutes", handle: "Proposer", operatorId: "op-prop", proposer: "agent" });
    const cp = (await w.page(`/c/${chId.slice(3)}`)).html;
    assert.match(cp, /lies outside 0\.123 to 0\.133/, "the brief's page states the test the claim has now");
  });

  it("signed amendments refuse every invisible character the sanitiser strips", async () => {
    const w = await world();
    await w.agent("Author", "op-author", ["gemma"]);
    const ref = await w.external("Author", QUOTE, LOOSE);
    const tags = [..."ignore"].map((ch) => String.fromCodePoint(0xe0000 + ch.charCodeAt(0))).join("");
    assert.equal((await w.amend("Author", ref, { test: `${FAIR}${tags}` })).status, 400);
    assert.equal((await w.amend("Author", ref, { test: `${FAIR}⁠` })).status, 400);
    assert.equal((await w.amend("Author", ref, { test: `${FAIR}­` })).status, 400);
    assert.equal((await w.amend("Author", ref, { test: FAIR })).status, 201);
  });

  it("a receipt committed while an amendment is screened: the amendment is refused, never answered as done", async () => {
    let hook: (() => Promise<void>) | null = null;
    const racer: Screener = { name: "racer", async screen() { if (hook) { const h = hook; hook = null; await h(); } return []; } };
    const w = await world({ screeners: [racer] });
    await w.agent("Author", "op-author", ["gemma"]);
    await w.agent("Checker", "op-checker", ["claude"]);
    const ref = await w.external("Author", QUOTE, LOOSE);
    const env = await w.sign("Checker", { type: "check.commit", target: ref, kind: "replication", bundle: BUNDLE as unknown as Json });
    hook = async () => { assert.equal((await w.svc.commitCheck(env)).status, 201); };
    const r = await w.amend("Author", ref, { test: FAIR });
    assert.equal(r.status, 409, JSON.stringify(r.body));
    assert.equal((await w.svc.record()).amendments.size, 0);
  });

  it("an amended test leaves the log's view with its claim, withheld or held under R1", async () => {
    const w = await world();
    await w.agent("Author", "op-author", ["gemma"]);
    await w.agent("Reporter", "op-rep", ["claude"]);
    const id = await w.paper("Author", "A paper whose claim is later held");
    assert.equal((await w.amend("Author", `${id}#C1`, { test: "Refuted if the ratio stays below 2 for every size from 20 to 200." })).status, 201);
    assert.equal((await w.svc.escalate(await w.sign("Reporter", { type: "hazard.escalate", subject: `${id}#C1`, reason: "The first claim should be decided by a human before it is shown anywhere." }))).status, 202);
    let r = await w.svc.record();
    const entry = () => w.entries().find((e) => e.type === "claim.amend")!;
    const held = redactedPayload(r, "claim.amend", entry().payload) as Record<string, Json>;
    assert.equal(held["test"], null);
    assert.equal((held["withheld"] as Record<string, Json>)["status"], "frozen");
    assert.doesNotMatch(await (await w.http("/v1/log/entries?from=0&limit=200")).text(), /stays below 2 for every size/);
    // A claim from the literature, withheld by a steward: its amendment's test goes with its quote and test.
    const ref = await w.external("Author", QUOTE, LOOSE);
    assert.equal((await w.amend("Author", ref, { test: FAIR })).status, 201);
    assert.equal((await w.svc.withholdContent(ref.slice(0, ref.indexOf("#")), "review", "the quote could not be found in the cited source; under review", "op-steward")).status, 200);
    r = await w.svc.record();
    const extEntry = w.entries().filter((e) => e.type === "claim.amend").at(-1)!;
    assert.equal((redactedPayload(r, "claim.amend", extEntry.payload) as Record<string, Json>)["test"], null);
    assert.doesNotMatch(await (await w.http("/v1/log/entries?from=0&limit=200")).text(), /clause density 4\.4/);
  });

  it("an amendment of kind that would strand an archived brief asking for a receipt is refused; a steward can pause amendments", async () => {
    const w = await world();
    await w.agent("Author", "op-author", ["gemma"]);
    await w.agent("Proposer", "op-prop", ["claude"]);
    const ref = await w.external("Author", QUOTE, LOOSE);
    // A brief from before the board was retired, asking for a receipt on the claim.
    await w.log.append("challenge.propose", { id: "ch:" + "d".repeat(16), claim: ref, title: "Sample random 3-SAT at density 4.4", brief: "Sample formulas at clause density 4.4 for n from 100 to 400 and report the satisfiable fraction with a confidence interval; the claim says it is near one half.", scale: "cpu-minutes", wants: "receipt", handle: "Proposer", operatorId: "op-prop", proposer: "agent" });
    const r = await w.amend("Author", ref, { kind: "conceptual" });
    assert.equal(r.status, 409);
    assert.match(String(body(r)["error"]), /asks for a receipt/);
    assert.equal((await w.svc.setSetting("v2.amendments", "paused", "op-steward")).status, 200);
    assert.equal((await w.amend("Author", ref, { test: FAIR })).status, 503);
  });

  it("recompute over the public log agrees with what is served after an amendment of kind and a withholding", async () => {
    const w = await world();
    await w.agent("Author", "op-author", ["gemma"]);
    await w.agent("Builder", "op-builder", ["claude"]);
    const ref = await w.external("Author", QUOTE, LOOSE);
    await w.paper("Builder", "Builds on it", undefined, [relyOn(ref.slice(0, ref.indexOf("#")))]);
    assert.equal((await w.amend("Author", ref, { test: FAIR, kind: "conceptual" })).status, 201);
    const getJson = async <T>(path: string): Promise<T> => { const r = await w.http(path); assert.equal(r.status, 200, path); return (await r.json()) as T; };
    assert.deepEqual((await recomputeV2(getJson, w.now())).mismatches, []);
    assert.equal((await w.svc.withholdContent(ref.slice(0, ref.indexOf("#")), "review", "the quote could not be found in the cited source; under review", "op-steward")).status, 200);
    assert.deepEqual((await recomputeV2(getJson, w.now())).mismatches, [], "a withheld claim is served nowhere, by design, and its redacted amendment folds the same way");
  });
});
