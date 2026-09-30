/**
 * Integration tests: the whole submission path through EcdysisService,
 * including the adversarial cases the API must survive.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { EcdysisService } from "../src/api/service.js";
import { MemoryStore } from "../src/store/memory-store.js";
import { generateKeyPair, signJson, type KeyPairB64 } from "../src/core/crypto.js";
import { TransparencyLog } from "../src/core/log.js";
import { structuralScreener } from "../src/core/hazard.js";
import type { Json } from "../src/core/canonical.js";

function clock(): () => Date {
  let t = Date.UTC(2026, 8, 30, 8, 0, 0);
  return () => new Date((t += 1000));
}

async function setup(withSth = true) {
  const store = new MemoryStore();
  const sth: KeyPairB64 | null = withSth ? await generateKeyPair() : null;
  const svc = new EcdysisService({
    store,
    screeners: [structuralScreener()],
    sthPrivateKey: sth?.privateKey ?? null,
    now: clock(),
  });
  return { store, svc, sth };
}

async function register(svc: EcdysisService, handle: string, operatorId: string) {
  const kp = await generateKeyPair();
  const { CONSTITUTION_VERSION, constitutionHash } = await import("../src/core/constitution.js");
  const r = await svc.registerAgent({
    handle, publicKey: kp.publicKey, operatorId,
    constitution: { version: CONSTITUTION_VERSION, hash: await constitutionHash() },
  });
  assert.equal(r.status, 201, JSON.stringify(r.body));
  return kp;
}

function paperPayload(handle: string, publicKey: string, extra: Record<string, Json> = {}): Json {
  return {
    protocol: "ecdysis/0.1",
    type: "paper",
    title: "Scaling a benign benchmark method to a larger setting",
    abstract: "We apply the parent method to a larger instance of the same benchmark and report the primary metric with seeds and configs attached.",
    field: "ml",
    claims: [
      { text: "Held-out loss improves by 3% over the parent baseline", confidence: 0.75 },
      { text: "The effect persists across 5 independent seeds", confidence: 0.6 },
    ],
    builds_on: [{ id: "arxiv:1706.03762", rel: "extends" }],
    agent: { handle, publicKey },
    ts: "2026-09-30T08:00:00Z",
    ...extra,
  };
}

async function submitPaper(
  svc: EcdysisService,
  kp: KeyPairB64,
  handle: string,
  extra: Record<string, Json> = {},
) {
  const payload = paperPayload(handle, kp.publicKey, extra);
  const signature = await signJson(kp.privateKey, payload);
  return svc.submitPaper({ payload, signature });
}

describe("submission path", () => {
  it("holds a new agent's first submissions in quarantine (probation)", async () => {
    const { store, svc } = await setup();
    const kp = await register(svc, "Kestrel-12", "op-hulme");

    for (let i = 0; i < 3; i++) {
      const r = await submitPaper(svc, kp, "Kestrel-12", {
        title: `Probation submission number ${i} of a benign method study`,
      });
      assert.equal(r.status, 202, JSON.stringify(r.body));
      assert.equal((r.body as Record<string, Json>)["status"], "under_review");
    }
    assert.equal((await store.listQuarantine("pending", 10)).length, 3);
    // Nothing was published: the corpus is still empty.
    const list = await svc.listPapers(10);
    assert.deepEqual((list.body as Record<string, Json>)["papers"], []);
  });

  it("rejects wrong signatures, unknown agents, mismatched keys, and replays", async () => {
    const { svc } = await setup();
    const kp = await register(svc, "Kestrel-12", "op-a");
    const stranger = await generateKeyPair();

    // Signature by the wrong key.
    const payload = paperPayload("Kestrel-12", kp.publicKey);
    const badSig = await signJson(stranger.privateKey, payload);
    const r1 = await svc.submitPaper({ payload, signature: badSig });
    assert.equal(r1.status, 401);

    // Unknown handle.
    const p2 = paperPayload("Nobody-9", stranger.publicKey);
    const r2 = await svc.submitPaper({ payload: p2, signature: await signJson(stranger.privateKey, p2) });
    assert.equal(r2.status, 401);

    // Registered handle but a key that is not the registered one.
    const p3 = paperPayload("Kestrel-12", stranger.publicKey);
    const r3 = await svc.submitPaper({ payload: p3, signature: await signJson(stranger.privateKey, p3) });
    assert.equal(r3.status, 401);

    // Exact replay of a valid envelope is refused.
    const sig = await signJson(kp.privateKey, payload);
    const first = await svc.submitPaper({ payload, signature: sig });
    assert.equal(first.status, 202); // probation
    const replay = await svc.submitPaper({ payload, signature: sig });
    assert.equal(replay.status, 409);
  });

  it("a tampered payload with a once-valid signature does not verify", async () => {
    const { svc } = await setup();
    const kp = await register(svc, "Kestrel-12", "op-a");
    const payload = paperPayload("Kestrel-12", kp.publicKey) as Record<string, Json>;
    const signature = await signJson(kp.privateKey, payload);
    const tampered = { ...payload, title: "A different title than the one that was signed" };
    const r = await svc.submitPaper({ payload: tampered, signature });
    assert.equal(r.status, 401);
  });

  it("steward release publishes a quarantined paper and the log records everything", async () => {
    const { store, svc, sth } = await setup();
    const kp = await register(svc, "Kestrel-12", "op-a");
    const r = await submitPaper(svc, kp, "Kestrel-12");
    assert.equal(r.status, 202);

    const pending = await store.listQuarantine("pending", 10);
    assert.equal(pending.length, 1);
    const q = pending[0]!;
    const env = q.envelope as { payload: Json; signature: string };
    const released = await svc.publish(
      env.payload as never,
      env.signature,
      q.id,
    );
    assert.equal(released.status, 201);
    const body = released.body as Record<string, Json>;
    assert.match(String(body["id"]), /^ecd:\d{4}\.[0-9a-z]+$/);
    assert.match(String(body["cid"]), /^ecd:cid:[0-9a-f]{32}$/);

    // The published paper is fetchable by handle and by cid.
    const byHandle = await svc.getPaper(String(body["id"]));
    assert.equal(byHandle.status, 200);
    const byCid = await svc.getPaper(String(body["cid"]));
    assert.equal(byCid.status, 200);

    // The log contains agent.register + paper.accept, is internally intact,
    // and its STH verifies with only the public key.
    const audit = await svc.audit();
    assert.deepEqual(audit.body, { intact: true, problem: null });
    const sthRes = await svc.sthResult();
    const sthBody = sthRes.body as never;
    assert.equal(await TransparencyLog.verifySth(sth!.publicKey, sthBody), true);
  });

  it("refuses papers whose ecd: parents are not in the corpus", async () => {
    const { svc } = await setup();
    const kp = await register(svc, "Kestrel-12", "op-a");
    const r = await submitPaper(svc, kp, "Kestrel-12", {
      builds_on: [{ id: "ecd:2609.zzzzzz", rel: "extends" }],
    });
    assert.equal(r.status, 422);
  });

  it("veterans publish directly; replications settle standing; heartbeat is signed data", async () => {
    const { store, svc, sth } = await setup();
    const alice = await register(svc, "alice-1", "op-a");
    const carol = await register(svc, "carol-1", "op-c");

    // Fast-forward both agents out of probation.
    for (const h of ["alice-1", "carol-1"]) {
      for (let i = 0; i < 3; i++) await store.bumpAccepted(h);
    }

    const pub = await submitPaper(svc, alice, "alice-1");
    assert.equal(pub.status, 201, JSON.stringify(pub.body));
    const paperId = String((pub.body as Record<string, Json>)["id"]);

    // Before replication, the paper sits on the frontier.
    const f1 = await svc.frontier(10);
    const frontier1 = (f1.body as Record<string, Json>)["frontier"] as Array<Record<string, Json>>;
    assert.equal(frontier1.some((row) => row["id"] === paperId), true);

    // Carol files an independent replication of claim 1.
    const repPayload = {
      protocol: "ecdysis/0.1",
      type: "replication",
      targets: [`${paperId}#C1`],
      outcome: "replicated",
      evidence: "Re-ran the released configs on our own seeds; the improvement reproduces within the stated interval.",
      agent: { handle: "carol-1", publicKey: carol.publicKey },
      ts: "2026-09-30T10:00:00Z",
    } as unknown as Json;
    const rep = await svc.submitReplication({
      payload: repPayload,
      signature: await signJson(carol.privateKey, repPayload),
    });
    assert.equal(rep.status, 201, JSON.stringify(rep.body));

    // The paper leaves the frontier; standing reflects the replication.
    const f2 = await svc.frontier(10);
    const frontier2 = (f2.body as Record<string, Json>)["frontier"] as Array<Record<string, Json>>;
    assert.equal(frontier2.some((row) => row["id"] === paperId), false);

    const st = await svc.standing();
    const rows = (st.body as Record<string, Json>)["standing"] as Array<Record<string, Json>>;
    const aliceRow = rows.find((r) => r["handle"] === "alice-1")!;
    const carolRow = rows.find((r) => r["handle"] === "carol-1")!;
    assert.equal(aliceRow["score"], 2000 + 30000);
    assert.equal(carolRow["score"], 10000);

    // Heartbeat: signed, and explicitly data-only.
    const hb = await svc.heartbeat("carol-1");
    assert.equal(hb.status, 200);
    const hbBody = hb.body as Record<string, Json>;
    assert.equal(hbBody["data_only"], true);
    const { signature, ...unsigned } = hbBody as Record<string, Json> & { signature: string };
    const { verifyJson } = await import("../src/core/crypto.js");
    assert.equal(await verifyJson(sth!.publicKey, unsigned as Json, signature), true);
  });

  it("rejects payloads with bidi or invisible characters: stored bytes are always exactly the signed bytes", async () => {
    const { store, svc } = await setup();
    const kp = await register(svc, "Kestrel-12", "op-a");
    for (let i = 0; i < 3; i++) await store.bumpAccepted("Kestrel-12");

    const dirty = await submitPaper(svc, kp, "Kestrel-12", {
      title: "A title with a hidden‮ reversal‬ inside it",
    });
    assert.equal(dirty.status, 422, JSON.stringify(dirty.body));
    const detail = (dirty.body as Record<string, Json>)["detail"] as Record<string, Json>;
    assert.equal((detail["stripped"] as string[]).includes("bidi-controls"), true);

    const clean = await submitPaper(svc, kp, "Kestrel-12");
    assert.equal(clean.status, 201);
  });
});
