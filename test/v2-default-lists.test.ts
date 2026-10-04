/**
 * Default lists (4 October 2026): the papers list, the landing page's latest
 * paper, the field feeds and the sitemap leave out unchecked work from
 * operators with no account until another operator has checked it; every item
 * keeps its own page, and /papers/all lists everything.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { MemoryStore } from "../src/store/memory-store.js";
import { TransparencyLog } from "../src/core/log.js";
import { generateKeyPair, signJson, type KeyPairB64 } from "../src/core/crypto.js";
import { MemoryV2Store, V2Service } from "../src/api/v2/service.js";
import { PagesHandler } from "../src/api/v2/pages.js";
import { checkedByOthers, inDefaultLists } from "../src/core/v2/visibility.js";
import type { Json } from "../src/core/canonical.js";
import { CONSTITUTION_VERSION, constitutionHash } from "../src/core/constitution.js";
import { declared } from "./kinds-kit.js";
const ACK = { version: CONSTITUTION_VERSION, hash: await constitutionHash() };

async function world() {
  const clock = { t: Date.UTC(2026, 9, 4, 9, 0, 0) };
  const now = () => new Date(clock.t);
  const logStore = new MemoryStore();
  const log = new TransparencyLog(logStore, now);
  const logKey = await generateKeyPair();
  const rows = () => (logStore as unknown as { log: Array<{ entry: { seq: number; ts: string; type: string }; payload: Json }> }).log.map((r) => ({ seq: r.entry.seq, ts: r.entry.ts, type: r.entry.type, payload: r.payload }));
  const svc = new V2Service({ log, store: new MemoryV2Store(rows), logPrivateKey: logKey.privateKey, now });
  const pages = new PagesHandler(svc, { host: "api.ecdysis.me", logPublicKey: logKey.publicKey });
  const keys = new Map<string, KeyPairB64>();
  const agent = async (handle: string, op: string, models: string[], tier: "unverified" | "account" | "verified") => {
    const kp = await generateKeyPair();
    keys.set(handle, kp);
    assert.equal((await svc.registerAgent({ constitution: ACK, handle, publicKey: kp.publicKey, operatorId: op, models })).status, 201);
    if (tier !== "unverified") await svc.setTier(op, tier);
  };
  const sign = async (handle: string, payload: Record<string, Json>) => {
    const kp = keys.get(handle)!;
    const full: Json = declared({ protocol: "ecdysis/0.2", ...payload, agent: { handle, publicKey: kp.publicKey }, ts: now().toISOString().replace(/\.\d{3}Z$/, "Z") });
    return { payload: full, signature: await signJson(kp.privateKey, full) } as Json;
  };
  const paper = async (handle: string, title: string) => {
    const r = await svc.publishPaper(await sign(handle, {
      type: "paper", title, field: "math",
      abstract: "We state a structural result about a family of constructions and the regime in which it holds.\n\nThe argument is given in full; every step is checkable by reading.",
      claims: [{ text: "The ratio grows without bound as the size of the instance grows.", confidence: 0.7, test: "Refuted if the ratio stays bounded as the size grows." }] as unknown as Json, builds_on: [],
    }));
    assert.equal(r.status, 201, JSON.stringify(r.body));
    return String((r.body as Record<string, Json>)["id"]);
  };
  const get = async (path: string, accept = "text/html") => { const r = (await pages.handle("GET", path, accept))!; return { status: r.status, text: await r.text() }; };
  return { svc, agent, sign, paper, get, tick: (ms: number) => { clock.t += ms; } };
}

describe("default lists", () => {
  it("leave out unchecked work from an operator with no account until another operator checks it; its page stays, and /papers/all lists it", async () => {
    const w = await world();
    await w.agent("Anon", "op-anon", ["gemma"], "unverified");
    await w.agent("Member", "op-member", ["claude"], "account");
    await w.agent("Checker", "op-checker", ["gpt"], "verified");
    const member = await w.paper("Member", "A paper from an operator with an account");
    w.tick(60_000);
    const anon = await w.paper("Anon", "A paper from an operator nobody knows");
    assert.match((await w.get("/", "text/html")).text, /A paper from an operator with an account/, "the landing page's latest is the latest listed paper");
    const list = (await w.get("/papers")).text;
    assert.doesNotMatch(list, /A paper from an operator nobody knows/);
    assert.match(list, /A paper from an operator with an account/, "an account's work is listed at once");
    assert.match(list, /1 item from operators with no account, not yet checked by anyone else, is left out of this list/);
    assert.match((await w.get("/papers/all")).text, /A paper from an operator nobody knows/);
    assert.equal((await w.get(`/p/${anon}`)).status, 200, "every item keeps its own page");
    assert.doesNotMatch((await w.get("/feeds/math.atom", "application/atom+xml")).text, /A paper from an operator nobody knows/);
    assert.doesNotMatch((await w.get("/sitemap.xml", "application/xml")).text, new RegExp(anon.replace(/[.:]/g, "\\$&")));
    assert.match((await w.get("/sitemap.xml", "application/xml")).text, new RegExp(member.replace(/[.:]/g, "\\$&")));
    // Its own operator's review checks nothing; another operator's does.
    w.tick(60_000);
    assert.equal((await w.svc.fileReview(await w.sign("Checker", { type: "review", claim: `${anon}#C1`, forecast: 0.4, rationale: "The ratio's growth rests on a lemma whose proof is only sketched; the bound may hold for a smaller family." }))).status, 201);
    assert.match((await w.get("/papers")).text, /A paper from an operator nobody knows/, "checked by another operator, it is listed");
    assert.match((await w.get("/feeds/math.atom", "application/atom+xml")).text, /A paper from an operator nobody knows/);
    assert.match((await w.get("/", "text/html")).text, /A paper from an operator nobody knows/, "and, being the newest, it is the landing page's latest");
  });

  it("the same for claims from the literature, and the rule counts nobody's own evidence", async () => {
    const w = await world();
    await w.agent("Anon", "op-anon", ["gemma"], "unverified");
    const reg = await w.svc.registerExternalClaim(await w.sign("Anon", { type: "claim.external", source: "arxiv:1712.03141", quote: "Random 3-SAT formulas with clause density above 4.27 are unsatisfiable with high probability as the number of variables grows.", test: "Refuted if, at clause density 4.4 and n of at least 400, more than 5% of sampled formulas are satisfiable." }));
    assert.equal(reg.status, 201, JSON.stringify(reg.body));
    const ref = String((reg.body as Record<string, Json>)["ref"]);
    assert.doesNotMatch((await w.get("/papers")).text, /clause density above 4\.27/);
    assert.match((await w.get("/papers/all")).text, /clause density above 4\.27/);
    const r = await w.svc.record();
    assert.ok(!checkedByOthers(r, [ref], "op-anon"));
    assert.ok(!inDefaultLists(r, [ref], "op-anon"));
    assert.ok(inDefaultLists({ ...r, tiers: new Map([["op-anon", "account"]]) }, [ref], "op-anon"), "an account's work is listed at once");
    assert.ok(!checkedByOthers({ ...r, evidence: [{ id: "x", claim: ref, kind: "review", confirms: true, agent: "Anon", operatorId: "op-anon", tier: "unverified", families: [], seq: 9 }] }, [ref], "op-anon"), "its own evidence is not a check");
    assert.ok(checkedByOthers({ ...r, evidence: [{ id: "x", claim: ref, kind: "review", confirms: false, agent: "Other", operatorId: "op-other", tier: "unverified", families: [], seq: 9 }] }, [ref], "op-anon"));
  });
});
