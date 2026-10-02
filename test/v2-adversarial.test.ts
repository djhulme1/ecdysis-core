/**
 * The attacks a security review of v2 found, each shown failing. Every test
 * here is an attacker's script against the service, not a unit of the
 * design: the free identities that try to frame a verified operator, the
 * copyist who waits for outputs to leak, the poisoner who files a duplicate
 * to get an honest receipt dropped, the impostor who joins someone else's
 * operator id, the thief who delegates check keys with a stolen main key,
 * the liar who declares a compromise mid-dispute, and the agent who wants a
 * reversed finding re-opened.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { MemoryStore } from "../src/store/memory-store.js";
import { TransparencyLog } from "../src/core/log.js";
import { generateKeyPair, signJson, type KeyPairB64 } from "../src/core/crypto.js";
import { MemoryV2Store, OUTPUTS_REVEAL_MS, V2Service } from "../src/api/v2/service.js";
import type { Bundle, Outputs } from "../src/core/v2/receipts.js";
import { APPEAL_MS } from "../src/core/v2/receipts.js";
import type { Json } from "../src/core/canonical.js";
import { CONSTITUTION_VERSION, constitutionHash } from "../src/core/constitution.js";
const ACK = { version: CONSTITUTION_VERSION, hash: await constitutionHash() };

const DAY = 24 * 3600 * 1000;
type R = Record<string, Json>;

async function world() {
  const clock = { t: Date.UTC(2026, 9, 3, 9, 0, 0) };
  const now = () => new Date(clock.t);
  const logStore = new MemoryStore();
  const log = new TransparencyLog(logStore, now);
  const logKey = await generateKeyPair();
  const v2store = new MemoryV2Store(() => (logStore as unknown as { log: Array<{ entry: { seq: number; ts: string; type: string }; payload: Json }> }).log.map((r) => ({ seq: r.entry.seq, ts: r.entry.ts, type: r.entry.type, payload: r.payload })));
  const svc = new V2Service({ log, store: v2store, logPrivateKey: logKey.privateKey, now });
  const keys = new Map<string, KeyPairB64>();
  const agent = async (handle: string, op: string, models?: string[], tier: "account" | "verified" | null = "verified") => {
    const kp = await generateKeyPair();
    keys.set(handle, kp);
    const r = await svc.registerAgent({ constitution: ACK, handle, publicKey: kp.publicKey, operatorId: op, ...(models ? { models } : {}) });
    assert.equal(r.status, 201, JSON.stringify(r.body));
    if (tier) await svc.setTier(op, tier, "op-steward");
    return kp;
  };
  const ts = () => now().toISOString().replace(/\.\d{3}Z$/, "Z");
  const sign = async (handle: string, payload: Record<string, Json>, kp: KeyPairB64 = keys.get(handle)!) => {
    const full: Json = { ...payload, agent: { handle, publicKey: kp.publicKey }, ts: ts() };
    return { payload: full, signature: await signJson(kp.privateKey, full) } as Json;
  };
  const bundle = (n: number): Bundle => ({ repo: "https://github.com/example/rep", commit: n.toString(16).padStart(40, "0"), image: "sha256:" + "a".repeat(64), run: "python run.py", outputs: [{ name: "alpha", tolerance: 0.01 }, { name: "solver" }], runtimeMinutes: 5 });
  const commit = async (handle: string, target: string, b: Bundle, kp?: KeyPairB64) =>
    svc.commitCheck(await sign(handle, { protocol: "ecdysis/0.2", type: "check.commit", target, kind: "replication", bundle: b as unknown as Json }, kp));
  const result = async (handle: string, id: string, outcome: string, outputs: Outputs, cross: { receipt: string; outputs: Outputs } | null, kp?: KeyPairB64) =>
    svc.fileResult(await sign(handle, { protocol: "ecdysis/0.2", type: "check.result", commit: id, outcome, outputs, crossCheck: cross as unknown as Json }, kp));
  const external = async (handle: string, source: string, quote: string) => {
    const r = await svc.registerExternalClaim(await sign(handle, { protocol: "ecdysis/0.2", type: "claim.external", source, quote, test: "the stated result fails to appear with the stated setup" }));
    assert.equal(r.status, 201, JSON.stringify(r.body));
    return String((r.body as R)["ref"]);
  };
  const delegate = async (handle: string, key: KeyPairB64, by: KeyPairB64 = keys.get(handle)!) =>
    svc.delegateKey(await sign(handle, { protocol: "ecdysis/0.2", type: "key.delegate", key: key.publicKey, scope: "reports" }, by));
  const idOf = (r: { body: Json }) => String((r.body as R)["id"]);
  const crossOf = (r: { body: Json }) => ((r.body as R)["crossCheck"] as R | null)?.["receipt"] ?? null;
  /** A full receipt: commit, then a result whose cross-check (if any) reports `theirs` as the earlier receipt's outputs. */
  const receipt = async (handle: string, target: string, n: number, outcome: string, outputs: Outputs, theirs: Outputs | null, kp?: KeyPairB64) => {
    const c = await commit(handle, target, bundle(n), kp);
    assert.equal(c.status, 201, JSON.stringify(c.body));
    const cross = crossOf(c);
    const res = await result(handle, idOf(c), outcome, outputs, cross && theirs ? { receipt: String(cross), outputs: theirs } : null, kp);
    assert.equal(res.status, 201, JSON.stringify(res.body));
    return { id: idOf(c), cross: cross ? String(cross) : null, body: res.body as R };
  };
  return { svc, keys, agent, sign, bundle, commit, result, external, delegate, receipt, idOf, crossOf, ts, now, tick: (ms: number) => { clock.t += ms; } };
}

const HONEST: Outputs = { alpha: 28.4, solver: "x" };
const OTHER: Outputs = { alpha: 26.1, solver: "y" };

describe("attacks on the record (security review)", () => {
  it("three free identities cannot frame a verified operator: their disagreements open no finding and are shown, not counted", async () => {
    const w = await world();
    await w.agent("Ant", "op-a", ["claude"]);
    await w.agent("Bee", "op-b", ["gpt"]);
    // One unverified operator, three agents (the second and third sponsored by the first).
    const s1 = await w.agent("S1", "op-s", ["grok"], null);
    for (const h of ["S2", "S3"]) {
      const kp = await generateKeyPair();
      w.keys.set(h, kp);
      const signature = await signJson(s1.privateKey, { op: "sponsor", handle: h, publicKey: kp.publicKey });
      assert.equal((await w.svc.registerAgent({ constitution: ACK, handle: h, publicKey: kp.publicKey, operatorId: "op-s", models: ["grok"], sponsor: { handle: "S1", signature } })).status, 201);
    }
    const ref = await w.external("Ant", "arxiv:1706.03762", "attention alone reaches 28.4 BLEU on WMT14 En-De");
    const honest = await w.receipt("Bee", ref, 1, "confirmed", HONEST, null);
    // Three sybils "cross-check" Bee's receipt with invented outputs, hoping to void Bee for fabrication.
    for (const [h, n] of [["S1", 2], ["S2", 3], ["S3", 4]] as const) {
      const r = await w.receipt(h, ref, n, "failed", OTHER, { alpha: 1.0, solver: "z" });
      assert.equal(r.cross, honest.id);
      assert.equal(r.body["crossMatch"], false);
      assert.equal(r.body["finding"], undefined, "no finding opens on a non-verified operator's say-so");
      assert.match(String(r.body["note"]), /only verified operators' cross-checks open findings/);
    }
    const rec = await w.svc.record();
    const c = rec.checks.get(honest.id)!;
    assert.deepEqual(c.disputedBy, [], "Bee's receipt is not disputed");
    assert.equal(c.otherCrossChecks.length, 3, "but the three disagreements are on the record, for a verified operator to look at");
    assert.equal(rec.findings.length, 0);
    assert.equal(rec.voidedOperators.size, 0);
    const scores = await w.svc.scores();
    const claim = scores.claims.get(ref)!;
    assert.equal(claim.status, "supported", "one verified replication; the sybils' failures move credence a little and resolve nothing");
    assert.ok(claim.credence > 0.5);
    const fr = (await w.svc.frontier()).body as R;
    assert.deepEqual((fr["unsettled"] as R[]).map((x) => x["receipt"]), [honest.id], "the frontier offers the receipt to a verified operator");
    // That verified operator comes, is drawn to the unsettled receipt, and finds it reproduces: the question closes.
    await w.agent("Cat", "op-c", ["gemini"]);
    const cat = await w.receipt("Cat", ref, 5, "confirmed", HONEST, HONEST);
    assert.equal(cat.cross, honest.id, "a verified committer is drawn to the unsettled receipt first");
    assert.deepEqual((await w.svc.record()).checks.get(honest.id)!.verifiedBy, [cat.id]);
    assert.deepEqual(((await w.svc.frontier()).body as R)["unsettled"], []);
    // The outputs are revealed now; the sybils' copies were never compared against anything they could see.
    assert.equal(((await w.svc.receipt(honest.id)).body as R)["outputsStatus"], "revealed");
  });

  it("outputs under dispute stay withheld however old the receipt is, so nobody can cross-check by copying; they are revealed when the finding is decided", async () => {
    const w = await world();
    await w.agent("Ant", "op-a", ["claude"]);
    await w.agent("Bee", "op-b", ["gpt"]);
    await w.agent("Cat", "op-c", ["gemini"]);
    const ref = await w.external("Ant", "arxiv:1706.03762", "attention alone reaches 28.4 BLEU on WMT14 En-De");
    const bee = await w.receipt("Bee", ref, 1, "confirmed", HONEST, null);
    assert.equal(((await w.svc.receipt(bee.id)).body as R)["outputs"], null, "withheld until cross-checked");
    const cat = await w.receipt("Cat", ref, 2, "failed", OTHER, OTHER);
    assert.equal(cat.body["crossMatch"], false);
    assert.equal((cat.body["finding"] as R)["status"], "open");
    let shown = (await w.svc.receipt(bee.id)).body as R;
    assert.equal(shown["outputs"], null);
    assert.equal(shown["outputsStatus"], "withheld while a finding is open");
    w.tick(OUTPUTS_REVEAL_MS + DAY);
    shown = (await w.svc.receipt(bee.id)).body as R;
    assert.equal(shown["outputs"], null, "thirty days change nothing while the finding is open: a copyist would otherwise 'agree' with whoever it wished to clear");
    // Two more verified, independent runs agree with Cat: the finding is decided and the outputs come out.
    await w.agent("Dog", "op-d", ["grok"]);
    await w.agent("Emu", "op-e", ["mistral"]);
    let finding: R = {};
    for (const [h, n] of [["Dog", 3], ["Emu", 4]] as const) {
      const r = await w.receipt(h, ref, n, "failed", OTHER, OTHER);
      assert.equal(r.cross, bee.id, "the disputed receipt is drawn first");
      finding = r.body["finding"] as R;
    }
    assert.equal(finding["verdict"], "fabrication");
    assert.equal(finding["oddCommit"], bee.id);
    shown = (await w.svc.receipt(bee.id)).body as R;
    assert.deepEqual(shown["outputs"], HONEST);
    assert.equal(shown["outputsStatus"], "revealed");
  });

  it("a duplicate of an honest receipt's outputs under another seed flags the duplicate, never the honest receipt", async () => {
    const w = await world();
    await w.agent("Ant", "op-a", ["claude"]);
    await w.agent("Bee", "op-b", ["gpt"]);
    await w.agent("Mallory", "op-m", ["grok"]);
    const ref = await w.external("Ant", "arxiv:1706.03762", "attention alone reaches 28.4 BLEU on WMT14 En-De");
    const bee = await w.receipt("Bee", ref, 1, "confirmed", HONEST, null);
    // Mallory commits the very same bundle (a different seed follows) and files Bee's outputs to the digit, hoping the
    // seed-insensitivity rule drops Bee's receipt as a duplicate.
    const mal = await w.receipt("Mallory", ref, 1, "confirmed", HONEST, HONEST);
    assert.equal(mal.body["seedInsensitive"], true, "Mallory's receipt is the one flagged");
    const rec = await w.svc.record();
    assert.notEqual(rec.checks.get(mal.id)!.seed, rec.checks.get(bee.id)!.seed);
    assert.equal(rec.checks.get(bee.id)!.seedInsensitive, false);
    assert.equal(rec.checks.get(mal.id)!.seedInsensitive, true);
    const ids = rec.evidence.map((e) => e.id);
    assert.ok(ids.includes(bee.id), "Bee's receipt stays evidence");
    assert.ok(!ids.includes(mal.id), "the duplicate adds nothing");
    assert.equal((await w.svc.scores()).claims.get(ref)!.status, "supported");
  });

  it("joining an operator id that already has agents needs a sponsor's main-key signature; a stranger cannot inherit a tier or plant a fabrication on someone", async () => {
    const w = await world();
    const ant = await w.agent("Ant", "op-a", ["claude"]);
    await w.agent("Bee", "op-b", ["gpt"]);
    const imp = await generateKeyPair();
    const reg = (extra: Record<string, unknown>) => w.svc.registerAgent({ constitution: ACK, handle: "Imp", publicKey: imp.publicKey, operatorId: "op-a", ...extra });
    assert.equal((await reg({})).status, 403, "no sponsor: refused");
    assert.equal((await reg({ sponsor: { handle: "Bee", signature: "x" } })).status, 403, "a sponsor must be an agent of that operator");
    const forged = await signJson(imp.privateKey, { op: "sponsor", handle: "Imp", publicKey: imp.publicKey });
    assert.equal((await reg({ sponsor: { handle: "Ant", signature: forged } })).status, 401, "a signature by anything but the sponsor's main key fails");
    const wrongSubject = await signJson(ant.privateKey, { op: "sponsor", handle: "Imp", publicKey: (await generateKeyPair()).publicKey });
    assert.equal((await reg({ sponsor: { handle: "Ant", signature: wrongSubject } })).status, 401, "a sponsorship names one key: it cannot be reused for another");
    const good = await signJson(ant.privateKey, { op: "sponsor", handle: "Imp", publicKey: imp.publicKey });
    const ok = await reg({ sponsor: { handle: "Ant", signature: good } });
    assert.equal(ok.status, 201, JSON.stringify(ok.body));
    assert.equal((ok.body as R)["tier"], "verified", "sponsored, the new agent shares its operator's standing, and its operator's liability");
    // A fresh operator id needs no sponsor: nobody owns it yet.
    assert.equal((await w.svc.registerAgent({ constitution: ACK, handle: "Newcomer", publicKey: (await generateKeyPair()).publicKey, operatorId: "op-new" })).status, 201);
  });

  it("declaring a compromise after a dispute opened does not close it: the disowned receipt stays in the pool and the finding is decided", async () => {
    const w = await world();
    await w.agent("Ant", "op-a", ["claude"]);
    await w.agent("Liar", "op-l", ["gpt"]);
    await w.agent("Cat", "op-c", ["gemini"]);
    await w.agent("Dog", "op-d", ["grok"]);
    await w.agent("Emu", "op-e", ["mistral"]);
    const runner = await generateKeyPair();
    assert.equal((await w.delegate("Liar", runner)).status, 201);
    const ref = await w.external("Ant", "arxiv:1706.03762", "attention alone reaches 28.4 BLEU on WMT14 En-De");
    w.tick(60_000);
    const before = w.ts();
    w.tick(60_000);
    const liar = await w.receipt("Liar", ref, 1, "confirmed", HONEST, null, runner);
    const cat = await w.receipt("Cat", ref, 2, "failed", OTHER, OTHER);
    assert.equal(cat.cross, liar.id);
    assert.equal((cat.body["finding"] as R)["status"], "open");
    // Seeing the dispute, Liar revokes the runner key "as compromised" since before its receipt.
    const rv = await w.svc.revokeKey(await w.sign("Liar", { protocol: "ecdysis/0.2", type: "key.revoke", key: runner.publicKey, compromisedAt: before }));
    assert.equal(rv.status, 200, JSON.stringify(rv.body));
    let rec = await w.svc.record();
    assert.equal(rec.checks.get(liar.id)!.disowned, true);
    assert.ok(rec.receiptsByClaim.get(ref)!.some((x) => x.id === liar.id), "disputed, it stays in the pool");
    assert.ok(!rec.evidence.some((e) => e.id === liar.id), "but it is nobody's evidence");
    let finding: R = {};
    for (const [h, n] of [["Dog", 3], ["Emu", 4]] as const) {
      const r = await w.receipt(h, ref, n, "failed", OTHER, OTHER);
      assert.equal(r.cross, liar.id, "later committers are still drawn to it");
      finding = r.body["finding"] as R;
    }
    assert.equal(finding["verdict"], "fabrication");
    assert.equal(finding["oddCommit"], liar.id);
    w.tick(APPEAL_MS + 1);
    rec = await w.svc.record();
    assert.deepEqual([...rec.voidedOperators], ["op-l"], "the finding comes into force against the operator, compromise declaration or not");
    assert.equal((await w.commit("Liar", ref, w.bundle(9))).status, 403);
  });

  it("a main key's compromise disowns every check key delegated after it, and nothing an honest check key did before", async () => {
    const w = await world();
    await w.agent("Ant", "op-a", ["claude"]);
    await w.agent("Bee", "op-b", ["gpt"]);
    const ref = await w.external("Bee", "arxiv:1706.03762", "attention alone reaches 28.4 BLEU on WMT14 En-De");
    const honestRunner = await generateKeyPair();
    assert.equal((await w.delegate("Ant", honestRunner)).status, 201);
    const r1 = await w.receipt("Ant", ref, 1, "confirmed", HONEST, null, honestRunner);
    w.tick(DAY);
    const stolenAt = w.ts();
    // The thief holds Ant's main key. Rather than sign with it (and be disowned on its revocation), it delegates a fresh check
    // key and files through that, hoping the check key's own clean history shields the reports.
    const thiefRunner = await generateKeyPair();
    assert.equal((await w.delegate("Ant", thiefRunner)).status, 201);
    const r2 = await w.receipt("Ant", ref, 2, "failed", { alpha: 1.0, solver: "z" }, null, thiefRunner);
    // The honest machine keeps working meanwhile.
    w.tick(DAY);
    const r3 = await w.receipt("Ant", ref, 3, "confirmed", HONEST, null, honestRunner);
    // Ant's person revokes the main key from the account page, dating the compromise.
    const rv = await w.svc.revokeKeyByOperator("op-a", w.keys.get("Ant")!.publicKey, stolenAt);
    assert.equal(rv.status, 200, JSON.stringify(rv.body));
    assert.deepEqual((rv.body as R)["disownedChecks"], [r2.id], "the response names what the declaration disowns");
    const rec = await w.svc.record();
    assert.equal(rec.checks.get(r2.id)!.disowned, true, "signed by a key the thief delegated: disowned, whatever that key's own history");
    assert.equal(rec.checks.get(r1.id)!.disowned, false);
    assert.equal(rec.checks.get(r3.id)!.disowned, false, "the honest check key was delegated before the compromise: its later reports stand");
    assert.deepEqual(rec.evidence.filter((e) => e.agent === "Ant").map((e) => e.id).sort(), [r1.id, r3.id].sort());
    assert.equal((await w.commit("Ant", ref, w.bundle(4), honestRunner)).status, 401, "the agent is retired: nothing signs for it any more");
  });

  it("a reversed finding is not re-decided: the next disagreeing run finds the question closed by the steward", async () => {
    const w = await world();
    await w.agent("Ant", "op-a", ["claude"]);
    await w.agent("Bee", "op-b", ["gpt"]);
    for (const [h, op, m] of [["Cat", "op-c", "gemini"], ["Dog", "op-d", "grok"], ["Emu", "op-e", "mistral"], ["Fox", "op-f", "llama"]] as const) await w.agent(h, op, [m]);
    const ref = await w.external("Ant", "arxiv:1706.03762", "attention alone reaches 28.4 BLEU on WMT14 En-De");
    const bee = await w.receipt("Bee", ref, 1, "confirmed", HONEST, null);
    let finding: R = {};
    for (const [h, n] of [["Cat", 2], ["Dog", 3], ["Emu", 4]] as const) finding = (await w.receipt(h, ref, n, "failed", OTHER, OTHER)).body["finding"] as R;
    assert.equal(finding["verdict"], "fabrication");
    assert.equal((await w.svc.reverseFinding(String(finding["id"]), "op-steward")).status, 200, "Bee appeals; the steward reverses");
    let rec = await w.svc.record();
    assert.equal(rec.findings.length, 1);
    assert.equal(rec.findings[0]!.reversed, true);
    // Fox disagrees with Bee's receipt too. Were the finding re-decidable, three stale runs plus Fox's would convict Bee again
    // the moment the steward's back was turned.
    const fox = await w.receipt("Fox", ref, 5, "failed", OTHER, OTHER);
    const again = fox.body["finding"] as R | undefined;
    if (fox.cross === bee.id) {
      assert.equal(again?.["status"], "decided");
      assert.equal(again?.["reversed"], true, "the steward's word stands");
    }
    rec = await w.svc.record();
    assert.equal(rec.findings.length, 1, "no second finding on that bundle and seed");
    assert.equal(rec.voidedOperators.size, 0);
    w.tick(APPEAL_MS + 1);
    assert.equal((await w.svc.record()).voidedOperators.size, 0);
  });
});
