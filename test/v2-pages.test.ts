/**
 * v2's public pages: a paper, its claims, an external claim, the frontier
 * and the observatory, rendered from the record; hostile text escaped.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { MemoryStore } from "../src/store/memory-store.js";
import { TransparencyLog } from "../src/core/log.js";
import { generateKeyPair, signJson, type KeyPairB64 } from "../src/core/crypto.js";
import { MemoryV2Store, V2Service } from "../src/api/v2/service.js";
import { PagesHandler } from "../src/api/v2/pages.js";
import type { Bundle, Outputs } from "../src/core/v2/receipts.js";
import type { Json } from "../src/core/canonical.js";
import { CONSTITUTION_VERSION, constitutionHash } from "../src/core/constitution.js";
const ACK = { version: CONSTITUTION_VERSION, hash: await constitutionHash() };

async function world() {
  const clock = { t: Date.UTC(2026, 9, 3, 9, 0, 0) };
  const now = () => new Date(clock.t);
  const logStore = new MemoryStore();
  const log = new TransparencyLog(logStore, now);
  const logKey = await generateKeyPair();
  const v2store = new MemoryV2Store(() => (logStore as unknown as { log: Array<{ entry: { seq: number; ts: string; type: string }; payload: Json }> }).log.map((r) => ({ seq: r.entry.seq, ts: r.entry.ts, type: r.entry.type, payload: r.payload })));
  const svc = new V2Service({ log, store: v2store, logPrivateKey: logKey.privateKey, now });
  const pages = new PagesHandler(svc);
  const keys = new Map<string, KeyPairB64>();
  const agent = async (handle: string, op: string, models?: string[], tier: "account" | "verified" | null = "verified") => {
    const kp = await generateKeyPair();
    keys.set(handle, kp);
    assert.equal((await svc.registerAgent({ constitution: ACK, handle, publicKey: kp.publicKey, operatorId: op, ...(models ? { models } : {}) })).status, 201);
    if (tier) await svc.setTier(op, tier);
    return kp;
  };
  const ts = () => now().toISOString().replace(/\.\d{3}Z$/, "Z");
  const sign = async (handle: string, payload: Record<string, Json>) => {
    const kp = keys.get(handle)!;
    const full: Json = { ...payload, agent: { handle, publicKey: kp.publicKey }, ts: ts() };
    return { payload: full, signature: await signJson(kp.privateKey, full) } as Json;
  };
  const bundle = (n: number): Bundle => ({ repo: "https://github.com/example/rep", commit: n.toString(16).padStart(40, "0"), image: "sha256:" + "a".repeat(64), run: "python run.py", outputs: [{ name: "alpha", tolerance: 0.01 }], runtimeMinutes: 5 });
  const commit = async (handle: string, target: string, b: Bundle) => svc.commitCheck(await sign(handle, { protocol: "ecdysis/0.2", type: "check.commit", target, kind: "replication", bundle: b as unknown as Json }));
  const result = async (handle: string, id: string, outcome: string, outputs: Outputs, cross: { receipt: string; outputs: Outputs } | null) =>
    svc.fileResult(await sign(handle, { protocol: "ecdysis/0.2", type: "check.result", commit: id, outcome, outputs, crossCheck: cross as unknown as Json }));
  const get = async (path: string) => { const r = await pages.handle("GET", path); return r ? { status: r.status, html: await r.text(), headers: r.headers } : null; };
  const idOf = (r: { body: Json }) => String((r.body as Record<string, Json>)["id"]);
  return { svc, pages, agent, sign, commit, result, bundle, get, idOf, tick: (ms: number) => { clock.t += ms; } };
}

describe("v2 pages", () => {
  it("renders a paper, its claims, an external claim, the frontier and the observatory from the record, escaping hostile text", async () => {
    const w = await world();
    await w.agent("Ant", "op-a", ["claude"]);
    await w.agent("Bee", "op-b", ["gpt"]);
    await w.agent("Cat", "op-c", ["gemini"]);
    const hostile = `<script>alert(1)</script> & "quotes" <img src=x onerror=alert(2)>`;
    const pub = await w.svc.publishPaper(await w.sign("Ant", {
      protocol: "ecdysis/0.2", type: "paper", title: `A title with ${hostile}`,
      abstract: `An abstract long enough to pass the structural screen, with ${hostile} inside it, describing what was measured and how.\n\nA second paragraph.`,
      field: "math", models: ["claude-fable-5-1"], methods: "Pre-registered; one seeded entry point.",
      claims: [{ text: `Claim one says ${hostile} holds in the stated regime.`, confidence: 0.7, test: "The quantity lies outside the interval in a fresh run." }, { text: "Claim two is a second atomic claim with its own test.", confidence: 0.6, test: "A second refuting result." }],
      builds_on: [{ id: "arxiv:1706.03762", rel: "background" }], artefacts: ["https://github.com/example/rep/tree/abc"],
    }));
    assert.equal(pub.status, 201, JSON.stringify(pub.body));
    const paperId = w.idOf(pub);
    const claim1 = `${paperId}#C1`;
    const ext = await w.svc.registerExternalClaim(await w.sign("Bee", { protocol: "ecdysis/0.2", type: "claim.external", source: "arxiv:1706.03762", quote: `attention alone reaches 28.4 BLEU ${hostile}`, test: "BLEU below 27 with the stated setup" }));
    const extRef = String((ext.body as Record<string, Json>)["ref"]);
    const c1 = await w.commit("Bee", claim1, w.bundle(1));
    await w.result("Bee", w.idOf(c1), "confirmed", { alpha: 1 }, null);
    const c2 = await w.commit("Cat", extRef, w.bundle(2));
    await w.result("Cat", w.idOf(c2), "failed", { alpha: 0 }, null);
    await w.svc.fileReview(await w.sign("Cat", { protocol: "ecdysis/0.2", type: "review", claim: claim1, forecast: 0.8, rationale: "The method is standard and the number is widely reproduced; the interval is conservative." }));

    // Papers list.
    let r = (await w.get("/papers"))!;
    assert.equal(r.status, 200);
    assert.match(r.html, /A title with &lt;script&gt;/);
    assert.doesNotMatch(r.html, /<script>alert/);
    assert.match(r.html, /attention alone reaches/);
    assert.equal(r.headers.get("content-security-policy")?.includes("script-src"), false, "no script allowed at all");
    // The paper.
    r = (await w.get(`/p/${paperId}`))!;
    assert.equal(r.status, 200);
    assert.match(r.html, /Claim one says &lt;script&gt;/);
    assert.match(r.html, /Stated 70%/);
    assert.match(r.html, /supported/, "Bee's verified replication confirms C1");
    assert.match(r.html, /models: claude-fable-5-1/);
    assert.match(r.html, /Cat<\/a> forecasts 80%/);
    assert.match(r.html, /A second paragraph/);
    assert.doesNotMatch(r.html, /<img src=x onerror=/, "the image tag is escaped, never live");
    // A claim page.
    r = (await w.get(`/p/${paperId}/C1`))!;
    assert.equal(r.status, 200);
    assert.match(r.html, /What would raise it most/);
    assert.match(r.html, /confirms<\/td><td><a href="\/a\/Bee"/);
    assert.match(r.html, /Confirming model families: gpt/);
    r = (await w.get(`/p/${paperId}/C9`))!;
    assert.equal(r.status, 404);
    // The external claim.
    r = (await w.get(`/x/${extRef.slice(4, 20)}/C1`))!;
    assert.equal(r.status, 200);
    assert.match(r.html, /From human literature/);
    assert.match(r.html, /arxiv:1706.03762/);
    assert.match(r.html, /refuted|contested|unchecked/);
    assert.doesNotMatch(r.html, /<script>alert/);
    assert.equal((await w.get("/x/0000000000000000/C1"))!.status, 404);
    // The frontier and the observatory.
    r = (await w.get("/frontier"))!;
    assert.equal(r.status, 200);
    assert.match(r.html, /Most worth checking/);
    assert.match(r.html, new RegExp(paperId.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")));
    r = (await w.get("/observatory"))!;
    assert.equal(r.status, 200);
    assert.match(r.html, /1 papers, 3 claims/);
    assert.match(r.html, /receipts per paper/);
    assert.match(r.html, /<td>gpt<\/td>/);
    assert.match(r.html, /Calibration/);
    // An agent page.
    r = (await w.get("/a/Bee"))!;
    assert.equal(r.status, 200);
    assert.match(r.html, /Tier verified/);
    assert.match(r.html, /models gpt/);
    assert.match(r.html, /confirmed<\/td>/);
    assert.equal((await w.get("/a/Nobody"))!.status, 404);
    // The front pages: v2 wording, v2 navigation, no juries anywhere.
    for (const path of ["/people", "/agents", "/connect"]) {
      const page = (await w.get(path))!;
      assert.equal(page.status, 200, path);
      assert.doesNotMatch(page.html, /jury|juror/i, `${path} speaks v2`);
      if (path !== "/agents") assert.match(page.html, /href="\/me"/, `${path} links to Your Ecdysis`);
      assert.doesNotMatch(page.html, /href="\/review"|href="\/apps"/, `${path} has the v2 navigation`);
    }
    const landing = await w.pages.handle("GET", "/", "text/html,application/xhtml+xml");
    assert.ok(landing);
    const lhtml = await landing!.text();
    assert.match(lhtml, /An open record of machine science/);
    assert.match(lhtml, /1 papers · 3 claims · 2 receipts · 3 agents/);
    assert.match(lhtml, /A title with &lt;script&gt;/, "the latest paper, escaped");
    assert.equal(await w.pages.handle("GET", "/", "application/json"), null, "agents and curl keep the JSON index");
    // Privacy and terms in v2 terms: accounts, check keys, receipts and holds; no juries, apps or claim posts.
    const privacy = (await w.get("/privacy"))!;
    assert.equal(privacy.status, 200);
    assert.match(privacy.html, /keyed hash/);
    assert.match(privacy.html, /Receipts' outputs/);
    assert.doesNotMatch(privacy.html, /jury|juror|claim post|marketplace/i);
    assert.doesNotMatch(privacy.html, /href="\/review"|href="\/apps"/, "v2 navigation");
    const terms = await w.pages.handle("GET", "/terms");
    assert.equal(terms!.status, 200);
    assert.match(terms!.headers.get("content-type") ?? "", /text\/markdown/);
    const ttext = await terms!.text();
    assert.match(ttext, /## Receipts and other people's code/);
    assert.match(ttext, /## Holds \(reserved power R1\)/);
    assert.match(ttext, /## Accounts/);
    assert.doesNotMatch(ttext, /jury|juror|Marketplace apps|Claim posts/i);
    // Not a v2 page: the handler declines, so v1 (or a 404) answers.
    assert.equal(await w.get("/kit"), null);
    assert.equal(await w.pages.handle("POST", "/papers"), null);
  });
});
