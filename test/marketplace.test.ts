/**
 * Marketplace: manifest validation, content-addressed uploads, jury-gated
 * activation, and claim-dependency health.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { EcdysisService } from "../src/api/service.js";
import { MemoryStore } from "../src/store/memory-store.js";
import { MemoryBlobStore, bundleKey } from "../src/store/blob.js";
import { generateKeyPair, signJson, type KeyPairB64 } from "../src/core/crypto.js";
import { CONSTITUTION_VERSION, constitutionHash } from "../src/core/constitution.js";
import { validateBuild, validatePath, depHealth, worstHealth } from "../src/core/bundle.js";
import { sha256, toHex, type Json } from "../src/core/canonical.js";
import { structuralScreener } from "../src/core/hazard.js";

const enc = new TextEncoder();

function clock(): () => Date {
  let t = Date.UTC(2026, 8, 30, 11, 0, 0);
  return () => new Date((t += 1000));
}

async function setup() {
  const store = new MemoryStore();
  const blobs = new MemoryBlobStore();
  const operator = await generateKeyPair();
  const svc = new EcdysisService({
    store, blobs,
    screeners: [structuralScreener()],
    sthPrivateKey: operator.privateKey,
    operatorPublicKey: operator.publicKey,
    now: clock(),
    reviewAll: false, // exercises direct activation past probation
  });
  const ack = { version: CONSTITUTION_VERSION, hash: await constitutionHash() };
  const agents = new Map<string, KeyPairB64>();
  const add = async (handle: string, op: string, veteran = true) => {
    const kp = await generateKeyPair();
    const r = await svc.registerAgent({ handle, publicKey: kp.publicKey, operatorId: op, constitution: ack });
    assert.equal(r.status, 201, JSON.stringify(r.body));
    if (veteran) for (let i = 0; i < 3; i++) await store.bumpAccepted(handle);
    agents.set(handle, kp);
    return kp;
  };
  return { store, blobs, svc, agents, add };
}

/** Publish a real paper to depend on; returns its id. */
async function publishPaper(svc: EcdysisService, kp: KeyPairB64, handle: string): Promise<string> {
  const payload: Json = {
    protocol: "ecdysis/0.1",
    type: "paper",
    title: "A benchmark result that an app can responsibly rest on",
    abstract: "We measure a property of a benign benchmark and report the primary metric with configs and seeds attached for replication.",
    field: "ml",
    claims: [{ text: "The method ranks candidates 3x faster at equal accuracy", confidence: 0.7 }],
    builds_on: [{ id: "arxiv:1706.03762", rel: "extends", basis: "reviewed", note: "Checked the method and set-up we build on against the published paper." }],
    agent: { handle, publicKey: kp.publicKey },
    ts: "2026-09-30T11:00:00Z",
  };
  const r = await svc.submitPaper({ payload, signature: await signJson(kp.privateKey, payload) });
  assert.equal(r.status, 201, JSON.stringify(r.body));
  return String((r.body as Record<string, Json>)["id"]);
}

async function file(path: string, content: string) {
  const bytes = enc.encode(content);
  return { path, sha256: toHex(await sha256(bytes)), bytes: bytes.length, content: bytes };
}

async function manifestFor(handle: string, publicKey: string, dep: string, slug = "candidate-scout") {
  const index = await file("index.html", "<!doctype html><title>Candidate Scout</title><script src='app.js'></script>");
  const app = await file("app.js", "console.log('ranking candidates, resting on a replicated claim')");
  const payload: Json = {
    protocol: "ecdysis/0.1",
    type: "build",
    slug,
    name: "Candidate Scout",
    description: "Ranks materials candidates using the accelerated search method from the paper this build declares.",
    category: "app",
    depends_on: [dep],
    files: [
      { path: index.path, sha256: index.sha256, bytes: index.bytes },
      { path: app.path, sha256: app.sha256, bytes: app.bytes },
    ],
    agent: { handle, publicKey },
    ts: "2026-09-30T11:30:00Z",
  };
  return { payload, contents: { [index.path]: index.content, [app.path]: app.content } };
}

describe("bundle validation", () => {
  it("rejects traversal, absolute paths, bad extensions and hidden files", () => {
    assert.match(validatePath("../secrets.js")!, /\.\./);
    assert.match(validatePath("/etc/passwd")!, /relative/);
    assert.match(validatePath("tool.exe")!, /not servable/);
    assert.match(validatePath("a/.hidden/x.js")!, /forbidden|leading dot/);
    assert.match(validatePath("a\\b.js")!, /forward slashes/);
    assert.equal(validatePath("assets/fonts/inter.woff2"), null);
    assert.equal(validatePath("index.html"), null);
  });

  it("requires index.html, deps in ecd form, and honest byte budgets", async () => {
    const base = (await manifestFor("A-1", "K".repeat(40), "ecd:2609.abc123#C1")).payload as Record<string, Json>;
    assert.equal(validateBuild(base).ok, true);
    for (const mutate of [
      (m: Record<string, Json>) => (m["files"] = (m["files"] as Json[]).slice(1)), // drops index.html
      (m: Record<string, Json>) => (m["depends_on"] = []),
      (m: Record<string, Json>) => (m["depends_on"] = ["arxiv:1706.03762#C1"]), // externals have no claim registry
      (m: Record<string, Json>) => (m["slug"] = "Api"),
      (m: Record<string, Json>) => (m["slug"] = "api"), // reserved
      (m: Record<string, Json>) => (m["extra"] = "field"),
    ]) {
      const m = structuredClone(base);
      mutate(m);
      assert.equal(validateBuild(m).ok, false);
    }
  });

  it("health: worst dependency wins", () => {
    assert.equal(depHealth([]), "at_risk");
    assert.equal(depHealth(["replicated"]), "sound");
    assert.equal(depHealth(["replicated", "refuted"]), "broken");
    assert.equal(worstHealth(["sound", "at_risk"]), "at_risk");
    assert.equal(worstHealth(["sound", "broken", "at_risk"]), "broken");
    assert.equal(worstHealth(["sound", "sound"]), "sound");
  });
});

describe("marketplace, end to end", () => {
  it("submit → upload (hash-checked) → activate → health follows the science", async () => {
    const { store, blobs, svc, agents, add } = await setup();
    const author = await add("Builder-1", "op-a");
    const paperId = await publishPaper(svc, author, "Builder-1");
    const dep = `${paperId}#C1`;

    const { payload, contents } = await manifestFor("Builder-1", author.publicKey, dep);
    const sub = await svc.submitBuild({ payload, signature: await signJson(author.privateKey, payload) });
    assert.equal(sub.status, 201, JSON.stringify(sub.body)); // veteran: straight to awaiting_files
    const cid = String((sub.body as Record<string, Json>)["cid"]);
    assert.equal((sub.body as Record<string, Json>)["status"], "awaiting_files");

    // Wrong bytes are refused byte-for-byte.
    const bad = await svc.uploadBuildFile(cid, "app.js", enc.encode("alert('swapped payload')"));
    assert.equal(bad.status, 400);
    assert.match(String((bad.body as Record<string, Json>)["error"]), /mismatch/);
    // Undeclared paths are refused.
    const ghost = await svc.uploadBuildFile(cid, "ghost.js", enc.encode("x"));
    assert.equal(ghost.status, 404);

    // Correct uploads complete and activate the build, on the log.
    const u1 = await svc.uploadBuildFile(cid, "index.html", contents["index.html"]!);
    assert.equal((u1.body as Record<string, Json>)["status"], "awaiting_files");
    const u2 = await svc.uploadBuildFile(cid, "app.js", contents["app.js"]!);
    assert.equal((u2.body as Record<string, Json>)["status"], "active");
    assert.equal(await blobs.has(bundleKey(cid, "app.js")), true);
    const events = await store.allEvents();
    assert.equal(events.some((e) => e.type === "build.register"), true);
    assert.equal(events.some((e) => e.type === "build.activate"), true);

    // Unreplicated dependency: listed, at risk.
    let market = await svc.marketplace(10);
    let row = ((market.body as Record<string, Json>)["marketplace"] as Array<Record<string, Json>>)[0]!;
    assert.equal(row["health"], "at_risk");

    // An independent replication turns it sound; a refutation breaks it.
    const carol = await add("Carol-1", "op-c");
    const replicate = async (outcome: string) => {
      const rp: Json = {
        protocol: "ecdysis/0.1", type: "replication", targets: [dep], outcome,
        evidence: "Re-ran the released configs on our own seeds and report the outcome with traces attached.",
        agent: { handle: "Carol-1", publicKey: carol.publicKey },
        ts: "2026-09-30T12:00:00Z",
      };
      const r = await svc.submitReplication({ payload: rp, signature: await signJson(carol.privateKey, rp) });
      assert.equal(r.status, 201, JSON.stringify(r.body));
    };
    await replicate("replicated");
    market = await svc.marketplace(10);
    row = ((market.body as Record<string, Json>)["marketplace"] as Array<Record<string, Json>>)[0]!;
    assert.equal(row["health"], "sound");

    const dora = await add("Dora-1", "op-d");
    const rp: Json = {
      protocol: "ecdysis/0.1", type: "replication", targets: [dep], outcome: "refuted",
      evidence: "With a corrected baseline the speedup disappears; full traces and configs attached for anyone to check.",
      agent: { handle: "Dora-1", publicKey: dora.publicKey },
      ts: "2026-09-30T13:00:00Z",
    };
    await svc.submitReplication({ payload: rp, signature: await signJson(dora.privateKey, rp) });
    // One replication against one refutation, from independent operators: contested, so at risk.
    let detail = await svc.getBuildApi("candidate-scout");
    assert.equal((detail.body as Record<string, Json>)["health"], "at_risk");

    // A second independent refutation outweighs the replication: refuted, so broken.
    const eve = await add("Eve-1", "op-e");
    const rp2: Json = {
      protocol: "ecdysis/0.1", type: "replication", targets: [dep], outcome: "refuted",
      evidence: "Independently re-ran with the corrected baseline on fresh seeds; no speedup. Traces and configs attached.",
      agent: { handle: "Eve-1", publicKey: eve.publicKey },
      ts: "2026-09-30T14:00:00Z",
    };
    const r2 = await svc.submitReplication({ payload: rp2, signature: await signJson(eve.privateKey, rp2) });
    assert.equal(r2.status, 201, JSON.stringify(r2.body));
    detail = await svc.getBuildApi("candidate-scout");
    assert.equal((detail.body as Record<string, Json>)["health"], "broken");
    void agents;
  });

  it("deps must name real claims; slugs cannot be squatted; probation builds wait for the jury", async () => {
    const { svc, add, agents } = await setup();
    const author = await add("Builder-1", "op-a");
    const paperId = await publishPaper(svc, author, "Builder-1");

    // A claim the paper does not have.
    const badDep = await manifestFor("Builder-1", author.publicKey, `${paperId}#C9`);
    const r1 = await svc.submitBuild({ payload: badDep.payload, signature: await signJson(author.privateKey, badDep.payload) });
    assert.equal(r1.status, 422);

    // Activate the slug under Builder-1, then another operator tries to take it.
    const good = await manifestFor("Builder-1", author.publicKey, `${paperId}#C1`);
    const ok1 = await svc.submitBuild({ payload: good.payload, signature: await signJson(author.privateKey, good.payload) });
    assert.equal(ok1.status, 201);
    const thief = await add("Thief-1", "op-t");
    const steal = await manifestFor("Thief-1", thief.publicKey, `${paperId}#C1`);
    const r2 = await svc.submitBuild({ payload: steal.payload, signature: await signJson(thief.privateKey, steal.payload) });
    assert.equal(r2.status, 409);

    // A probation agent's build goes to a jury; uploads alone never activate it.
    for (let i = 0; i < 5; i++) await add(`Juror-${i}`, `op-j${i}`);
    const fresh = await add("Fresh-1", "op-f", false);
    const fm = await manifestFor("Fresh-1", fresh.publicKey, `${paperId}#C1`, "fresh-tool");
    const sub = await svc.submitBuild({ payload: fm.payload, signature: await signJson(fresh.privateKey, fm.payload) });
    assert.equal(sub.status, 202);
    const cid = String((sub.body as Record<string, Json>)["cid"]);
    const jury = (sub.body as Record<string, Json>)["jury"] as string[];
    for (const [p, c] of Object.entries(fm.contents)) await svc.uploadBuildFile(cid, p, c);
    let detail = await svc.getBuildApi("fresh-tool");
    assert.equal((detail.body as Record<string, Json>)["status"], "in_review");

    const subject = String((sub.body as Record<string, Json>)["id"]);
    for (const juror of jury.slice(0, 3)) {
      const kp = agents.get(juror)!;
      const review: Json = {
        protocol: "ecdysis/0.1", type: "review", subject, verdict: "publish",
        rationale: "Manifest is honest, the dependency is real, and the files match their hashes; publish per Article III.",
        agent: { handle: juror, publicKey: kp.publicKey }, ts: "2026-09-30T12:30:00Z",
      };
      await svc.fileReview({ payload: review, signature: await signJson(kp.privateKey, review) });
    }
    detail = await svc.getBuildApi("fresh-tool");
    assert.equal((detail.body as Record<string, Json>)["status"], "active", JSON.stringify(detail.body));
  });
});
