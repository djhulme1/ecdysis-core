/**
 * Two things a reader of a claim page asked for (a steward's report, 4
 * October 2026): the page says which log entry its figures were derived to,
 * so a view left open in a tab can be told from the record as it stands;
 * and a re-run by an operator not yet verified is shown on the receipt it
 * re-ran, marked as counting for nothing, rather than leaving the row at
 * "0 verified, 0 disputed" as if nobody had re-run it.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { MemoryStore } from "../src/store/memory-store.js";
import { TransparencyLog } from "../src/core/log.js";
import { generateKeyPair, signJson, type KeyPairB64 } from "../src/core/crypto.js";
import { MemoryV2Store, V2Service } from "../src/api/v2/service.js";
import { PagesHandler } from "../src/api/v2/pages.js";
import { deriveV2, type V2Entry } from "../src/core/v2/flow.js";
import type { Bundle, Outputs } from "../src/core/v2/receipts.js";
import type { Json } from "../src/core/canonical.js";
import { CONSTITUTION_VERSION, constitutionHash } from "../src/core/constitution.js";
import { declared } from "./kinds-kit.js";
const ACK = { version: CONSTITUTION_VERSION, hash: await constitutionHash() };

async function world() {
  const store = new MemoryStore();
  const clock = { t: Date.UTC(2026, 9, 4, 11, 0, 0) };
  const now = () => new Date(clock.t);
  const log = new TransparencyLog(store, now);
  const logKey = await generateKeyPair();
  const rows = () => (store as unknown as { log: Array<{ entry: { seq: number; ts: string; type: string }; payload: Json }> }).log.map((r) => ({ seq: r.entry.seq, ts: r.entry.ts, type: r.entry.type, payload: r.payload }));
  const svc = new V2Service({ log, store: new MemoryV2Store(rows), logPrivateKey: logKey.privateKey, now });
  const pages = new PagesHandler(svc, { host: "api.ecdysis.me", logPublicKey: logKey.publicKey });
  const keys = new Map<string, KeyPairB64>();
  const agent = async (handle: string, op: string, models: string[], tier: "account" | "verified" = "verified") => {
    const kp = await generateKeyPair();
    keys.set(handle, kp);
    assert.equal((await svc.registerAgent({ constitution: ACK, handle, publicKey: kp.publicKey, operatorId: op, models })).status, 201);
    await svc.setTier(op, tier);
  };
  const ts = () => now().toISOString().replace(/\.\d{3}Z$/, "Z");
  const sign = async (handle: string, payload: Record<string, Json>) => {
    const full: Json = declared({ ...payload, agent: { handle, publicKey: keys.get(handle)!.publicKey }, ts: ts() });
    return { payload: full, signature: await signJson(keys.get(handle)!.privateKey, full) } as Json;
  };
  const bundle = (n: number): Bundle => ({ repo: "https://github.com/example/rep", commit: n.toString(16).padStart(40, "0"), image: "sha256:" + "a".repeat(64), run: "python run.py", outputs: [{ name: "effect", tolerance: 0.01 }, { name: "n" }], runtimeMinutes: 5 });
  const commit = async (handle: string, target: string, n: number) => svc.commitCheck(await sign(handle, { protocol: "ecdysis/0.2", type: "check.commit", target, kind: "replication", bundle: bundle(n) as unknown as Json }));
  const result = async (handle: string, id: string, outcome: string, outputs: Outputs, cross: { receipt: string; outputs: Outputs } | null) =>
    svc.fileResult(await sign(handle, { protocol: "ecdysis/0.2", type: "check.result", commit: id, outcome, outputs, crossCheck: cross as unknown as Json }));
  const b = (r: { body: Json }) => r.body as Record<string, Json>;
  const page = async (path: string) => { const res = await pages.handle("GET", path, "text/html"); assert.ok(res, `a page at ${path}`); return { status: res.status, text: await res.text() }; };
  return { svc, agent, sign, commit, result, b, page, rows, tick: (ms: number) => { clock.t += ms; } };
}

describe("the record names the entry it was derived to", () => {
  it("head is the last entry's seq and time; null for an empty log", () => {
    const t0 = Date.UTC(2026, 9, 4);
    const e = (seq: number, type: V2Entry["type"], payload: Record<string, unknown>): V2Entry => ({ seq, ts: new Date(t0 + seq * 60_000).toISOString(), type, payload });
    assert.equal(deriveV2([], new Date(t0)).head, null);
    const r = deriveV2([e(3, "operator.tier", { operatorId: "op-a", tier: "verified" }), e(1, "operator.tier", { operatorId: "op-b", tier: "account" })], new Date(t0 + 3_600_000));
    assert.deepEqual(r.head, { seq: 3, ts: new Date(t0 + 3 * 60_000).toISOString() }, "the greatest seq, whatever order the entries came in");
  });
});

describe("the claim page", () => {
  it("says which entry it was computed from, and shows a not-yet-verified operator's re-run without counting it", async () => {
    const w = await world();
    await w.agent("Ant", "op-a", ["claude"]);
    await w.agent("Bee", "op-b", ["gpt"], "account");
    await w.agent("Dog", "op-d", ["mistral"]);
    const reg = await w.svc.registerExternalClaim(await w.sign("Dog", { protocol: "ecdysis/0.2", type: "claim.external", source: "doi:10.1016/j.jbusvent.2013.06.005", quote: "Projects that succeed tend to do so by relatively small margins.", test: "On a complete crawl, the 25th percentile of pledged/goal exceeds 1.06." }));
    assert.equal(reg.status, 201, JSON.stringify(reg.body));
    const ref = String(w.b(reg)["ref"]);
    const path = `/x/${ref.slice(4, ref.indexOf("#"))}/C1`;
    // Ant's receipt fails the claim.
    const c1 = await w.commit("Ant", ref, 1);
    assert.equal(c1.status, 201, JSON.stringify(c1.body));
    const id1 = String(w.b(c1)["id"]);
    assert.equal((await w.result("Ant", id1, "failed", { effect: 0.42, n: 48526 }, null)).status, 201);
    let p = await w.page(path);
    assert.match(p.text, /not yet by a verified operator/);
    assert.doesNotMatch(p.text, /not yet verified/, "nobody has re-run it");
    // Bee, at the account tier, is handed Ant's receipt as its cross-check and matches it: shown on Ant's row, counted nowhere.
    w.tick(60_000);
    const c2 = await w.commit("Bee", ref, 2);
    assert.equal(c2.status, 201, JSON.stringify(c2.body));
    assert.equal((w.b(c2)["crossCheck"] as Record<string, Json>)["receipt"], id1);
    const r2 = await w.result("Bee", String(w.b(c2)["id"]), "inconclusive", { effect: 0.4, n: 1 }, { receipt: id1, outputs: { effect: 0.42, n: 48526 } });
    assert.equal(r2.status, 201, JSON.stringify(r2.body));
    assert.equal(w.b(r2)["crossMatch"], true);
    const rec = await w.svc.record();
    assert.deepEqual(rec.checks.get(id1)!.verifiedBy, [], "an account-tier cross-check verifies nothing");
    assert.equal(rec.checks.get(id1)!.otherCrossChecks.length, 1);
    p = await w.page(path);
    assert.match(p.text, /not yet by a verified operator · <span class="small"[^>]*>1 more by operators not yet verified \(1 matched, 0 disagreed\), shown, not counted<\/span>/);
    assert.match(p.text, /inconclusive/, "Bee's own receipt is listed too");
    // The footer names the log head the figures came from: the last entry, Bee's result.
    const last = w.rows().at(-1)!;
    assert.equal(last.type, "check.result");
    assert.match(p.text, new RegExp(`computed from the public log at entry #${last.seq} \\(4 Oct 2026, ${last.ts.slice(11, 16)} UTC\\)`));
    // Once a steward verifies Bee's operator, the same re-run verifies the receipt, and the "not counted" clause goes.
    w.tick(60_000);
    assert.equal((await w.svc.setTier("op-b", "verified", "op-steward")).status, 200);
    p = await w.page(path);
    assert.match(p.text, /once by one verified operator/, "re-runs are counted in operators as well as runs");
    assert.doesNotMatch(p.text, /not yet verified/);
    const head = w.rows().at(-1)!;
    assert.equal(head.type, "operator.tier");
    assert.match(p.text, new RegExp(`computed from the public log at entry #${head.seq} `), "the head moves with the log");
    // The agent page carries the same line.
    const a = await w.page("/a/Ant");
    assert.equal(a.status, 200);
    assert.match(a.text, new RegExp(`computed from the public log at entry #${head.seq} `));
  });
});
