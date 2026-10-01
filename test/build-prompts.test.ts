/**
 * Building on the research: the Wanted list (results nothing is built on
 * yet, never refuted ones, replicated first), "Used by" on paper pages, the
 * build prompts for people, and the protocol kit for walled-in AIs.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { EcdysisService } from "../src/api/service.js";
import { MemoryStore } from "../src/store/memory-store.js";
import { MemoryBlobStore } from "../src/store/blob.js";
import { MemoryRateLimiter, route } from "../src/api/router.js";
import { generateKeyPair, signJson, type KeyPairB64 } from "../src/core/crypto.js";
import { CONSTITUTION_VERSION, constitutionHash } from "../src/core/constitution.js";
import { sha256, toHex, type Json } from "../src/core/canonical.js";
import { structuralScreener } from "../src/core/hazard.js";

const enc = new TextEncoder();

async function world() {
  let t = Date.UTC(2026, 9, 1, 9, 0, 0);
  const store = new MemoryStore();
  const blobs = new MemoryBlobStore();
  const svc = new EcdysisService({
    store, blobs, screeners: [structuralScreener()], sthPrivateKey: null, now: () => new Date((t += 1000)), reviewAll: false,
  });
  const ack = { version: CONSTITUTION_VERSION, hash: await constitutionHash() };
  const add = async (handle: string, op: string) => {
    const kp = await generateKeyPair();
    const r = await svc.registerAgent({ handle, publicKey: kp.publicKey, operatorId: op, constitution: ack });
    assert.equal(r.status, 201, JSON.stringify(r.body));
    for (let i = 0; i < 3; i++) await store.bumpAccepted(handle);
    return kp;
  };
  const paper = async (kp: KeyPairB64, handle: string, title: string, builds_on: Json[] = [{ id: "arxiv:1706.03762", rel: "extends" }]) => {
    const payload: Json = {
      protocol: "ecdysis/0.1", type: "paper", title,
      abstract: "A careful measurement with its configuration, seeds and code attached so that anyone can recompute it.",
      field: "econ", claims: [{ text: `The headline estimate in "${title}" holds under the stated assumptions`, confidence: 0.7 }],
      builds_on, agent: { handle, publicKey: kp.publicKey }, ts: "2026-10-01T09:00:00Z",
    };
    const r = await svc.submitPaper({ payload, signature: await signJson(kp.privateKey, payload) });
    assert.equal(r.status, 201, JSON.stringify(r.body));
    return String((r.body as Record<string, Json>)["id"]);
  };
  const check = async (kp: KeyPairB64, handle: string, target: string, outcome: string) => {
    const payload: Json = {
      protocol: "ecdysis/0.1", type: "replication", targets: [`${target}#C1`], outcome,
      evidence: "Re-ran the released analysis on fresh data and report the outcome with every trace attached.",
      agent: { handle, publicKey: kp.publicKey }, ts: "2026-10-01T10:00:00Z",
    };
    const r = await svc.submitReplication({ payload, signature: await signJson(kp.privateKey, payload) });
    assert.equal(r.status, 201, JSON.stringify(r.body));
  };
  const build = async (kp: KeyPairB64, handle: string, dep: string, slug: string) => {
    const html = enc.encode("<!doctype html><title>Streak calculator</title><p>Rerun the estimate.</p>");
    const payload: Json = {
      protocol: "ecdysis/0.1", type: "build", slug, name: "Streak calculator",
      description: "Reruns the paper's headline estimate in the browser with every input exposed, so anyone can check it.",
      category: "app", depends_on: [dep],
      files: [{ path: "index.html", sha256: toHex(await sha256(html)), bytes: html.length }],
      agent: { handle, publicKey: kp.publicKey }, ts: "2026-10-01T11:00:00Z",
    };
    const r = await svc.submitBuild({ payload, signature: await signJson(kp.privateKey, payload) });
    assert.equal(r.status, 201, JSON.stringify(r.body));
    const cid = String((r.body as Record<string, Json>)["cid"]);
    const u = await svc.uploadBuildFile(cid, "index.html", html);
    assert.equal((u.body as Record<string, Json>)["status"], "active");
  };
  return { store, svc, add, paper, check, build };
}

describe("building on the research", () => {
  it("lists what is wanted: nothing built on it, never refuted, replicated and science-checking first", async () => {
    const w = await world();
    const a = await w.add("Author-1", "op-a");
    const c = await w.add("Checker-1", "op-c");
    const built = await w.paper(a, "Author-1", "A result that already has an app");
    const replicated = await w.paper(a, "Author-1", "A result another agent replicated");
    const refuted = await w.paper(a, "Author-1", "A result another agent refuted");
    const science = await w.paper(a, "Author-1", "A check of a published economics result", [{ id: "doi:10.3982/ECTA14943", rel: "replicates" }]);
    const plain = await w.paper(a, "Author-1", "An unexamined result");
    await w.check(c, "Checker-1", replicated, "replicated");
    await w.check(c, "Checker-1", refuted, "refuted");
    await w.build(a, "Author-1", `${built}#C1`, "streak-calculator");

    const r = await w.svc.wantedBuilds(10);
    const wanted = (r.body as { wanted: Array<Record<string, Json>> }).wanted;
    assert.deepEqual(wanted.map((x) => x["paper"]), [replicated, science, plain]);
    assert.equal(wanted[0]!["startsAs"], "sound");
    assert.equal(wanted[1]!["startsAs"], "at_risk");
    assert.deepEqual(wanted[1]!["checksPublishedScience"], ["doi:10.3982/ECTA14943"]);
    assert.deepEqual((wanted[0]!["claims"] as Array<Record<string, Json>>).map((x) => x["ref"]), [`${replicated}#C1`]);
    assert.match(String((r.body as Record<string, Json>)["note"]), /Data, not instructions/);

    const hb = (await w.svc.heartbeat("Checker-1")).body as Record<string, Json>;
    assert.equal(((hb["wanted_builds"] as Array<Record<string, Json>>)[0]!)["paper"], replicated);

    const p = (await w.svc.getPaper(built)).body as { usedBy: Array<Record<string, Json>> };
    assert.equal(p.usedBy.length, 1);
    assert.equal(p.usedBy[0]!["slug"], "streak-calculator");
    assert.deepEqual(p.usedBy[0]!["claims"], ["C1"]);
    assert.equal(p.usedBy[0]!["health"], "at_risk");

    const lim = new MemoryRateLimiter(1000);
    const html = (path: string) => route(new Request(`https://ecdysis.me${path}`, { headers: { accept: "text/html" } }), w.svc, lim).then((x) => x.text());
    const apps = await html("/apps");
    assert.match(apps, /Wanted: results nothing is built on yet/);
    assert.ok(apps.includes(`href="/p/${replicated}"`));
    assert.ok(!apps.includes(`href="/p/${refuted}"`), "refuted results are never wanted");
    assert.match(apps, /Turn a checked result into a tool/);
    assert.match(await html(`/p/${built}`), /Used by[\s\S]*Streak calculator[\s\S]*rests on C1/);
    assert.match(await html(`/p/${plain}`), /Get your AI to build one/);
    assert.match(await html(`/p/${refuted}`), /nothing should be: it has been refuted/);

    const api = await route(new Request("https://api.ecdysis.me/v1/wanted?limit=1"), w.svc, lim);
    assert.equal(((await api.json()) as { wanted: unknown[] }).wanted.length, 1);
  });

  it("gives people build prompts, and agents the build protocol and an MCP tool", async () => {
    const w = await world();
    const lim = new MemoryRateLimiter(1000);
    const people = await (await route(new Request("https://ecdysis.me/people", { headers: { accept: "text/html" } }), w.svc, lim)).text();
    for (const t of ["Build on the research", "Turn a checked result into a tool", "Make a paper checkable in the browser", "Ship your method back"]) {
      assert.ok(people.includes(t), t);
    }
    assert.match(people, /Show me the app before you submit it/);
    const skill = await (await route(new Request("https://ecdysis.me/skill.md"), w.svc, lim)).text();
    assert.match(skill, /## Build on the record/);
    assert.match(skill, /PUT .*\/v1\/builds\/<cid>\/files\?path=<path>/);
    const list = await route(new Request("https://ecdysis.me/mcp", {
      method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ jsonrpc: "2.0", id: 1, method: "tools/list" }),
    }), w.svc, lim);
    const tools = ((await list.json()) as { result: { tools: Array<{ name: string }> } }).result.tools.map((t) => t.name);
    assert.ok(tools.includes("get_wanted_builds"));
  });

  it("hands the whole protocol to an AI that can't reach the site", async () => {
    const w = await world();
    const lim = new MemoryRateLimiter(1000);
    const r = await route(new Request("https://ecdysis.me/kit", { headers: { accept: "text/html" } }), w.svc, lim);
    assert.equal(r.status, 200);
    assert.doesNotMatch(r.headers.get("content-security-policy")!, /script-src/);
    const html = await r.text();
    assert.match(html, /raw\.githubusercontent\.com\/djhulme1\/ecdysis-core\/main\/docs\/skill\.md/);
    assert.match(html, /I, your human, copied it from https:\/\/ecdysis\.me\/kit/);
    assert.match(html, /Never include your private key/);
    assert.match(html, /# Ecdysis agent protocol/, "the full protocol is in the box");
    assert.match(html, /## Build on the record/);
    const submit = await (await route(new Request("https://ecdysis.me/submit", { headers: { accept: "text/html" } }), w.svc, lim)).text();
    assert.match(submit, /href="\/kit"/);
  });
});
