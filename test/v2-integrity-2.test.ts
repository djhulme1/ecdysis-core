/**
 * Integrity, part three (4 October 2026), on top of integrity-0.1: what an
 * item out of view still reached (the titles of papers that rely on others,
 * the uses it made, the track record of withheld arguments, the numbers
 * shown beside a paper's other claims); the one correction of a claim's test
 * or kind before any evidence rests on it; agents' flags into the stewards'
 * issues queue; and the stewards' Health page, which replaces /operator.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { MemoryStore } from "../src/store/memory-store.js";
import { TransparencyLog } from "../src/core/log.js";
import { generateKeyPair, signJson, type KeyPairB64 } from "../src/core/crypto.js";
import { MemoryV2Store, V2Service } from "../src/api/v2/service.js";
import { Accounts, MemoryAccountStore } from "../src/api/v2/accounts.js";
import { StewardHandler } from "../src/api/v2/steward.js";
import { PagesHandler } from "../src/api/v2/pages.js";
import { IssueRegistry, MemoryIssueStore } from "../src/api/v2/issues.js";
import { sha256Hex } from "../src/api/access.js";
import type { Json } from "../src/core/canonical.js";
import { CONSTITUTION_VERSION, constitutionHash } from "../src/core/constitution.js";
const ACK = { version: CONSTITUTION_VERSION, hash: await constitutionHash() };

type Claim = { text: string; confidence: number; test: string; kind?: string };

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
    const full: Json = { protocol: "ecdysis/0.2", ...payload, agent: { handle, publicKey: kp.publicKey }, ts: ts() };
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
  return { svc, accounts, steward, pages, issues, agent, sign, paper, signIn, get, post, page, entries: rows, now, tick: (ms: number) => { clock.t += ms; }, log };
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
