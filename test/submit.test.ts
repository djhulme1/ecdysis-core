/**
 * The paste route (/submit): a person submits what their walled-in AI
 * prepared. It must register and submit through the same service as the
 * API, tolerate how people really paste (code fences, bare forms), refuse
 * anything that looks like a private key without echoing it, and count
 * each inner step in the write funnel.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { MemoryRateLimiter, route } from "../src/api/router.js";
import { EcdysisService } from "../src/api/service.js";
import { MemoryStore } from "../src/store/memory-store.js";
import { structuralScreener } from "../src/core/hazard.js";
import { constitutionHash, CONSTITUTION_VERSION } from "../src/core/constitution.js";
import { generateKeyPair, signJson } from "../src/core/crypto.js";
import { looksLikePrivateKey, parseBundle } from "../src/web/submit.js";
import { PROTOCOL } from "../src/core/schema.js";
import type { Json } from "../src/core/canonical.js";

const limiter = () => new MemoryRateLimiter(1000);
function setup() {
  const store = new MemoryStore();
  return { store, svc: new EcdysisService({ store, screeners: [structuralScreener()], sthPrivateKey: null }) };
}
function paste(bundle: string, extra: HeadersInit = {}) {
  return new Request("https://ecdysis.me/submit", {
    method: "POST",
    headers: { "content-type": "application/x-www-form-urlencoded", ...extra },
    body: new URLSearchParams({ bundle }).toString(),
  });
}

async function preparedBlock(handle: string) {
  const kp = await generateKeyPair();
  const payload = {
    protocol: PROTOCOL,
    type: "paper",
    title: "A pasted test paper on a small replication",
    abstract: "We re-ran a small published analysis and report what we found, with seeds and code.",
    field: "ml",
    claims: [{ text: "The headline effect replicates at the reported scale.", confidence: 0.7 }],
    builds_on: [{ id: "arxiv:2203.15556", rel: "replicates" }],
    agent: { handle, publicKey: kp.publicKey },
    ts: "2026-10-01T10:00:00Z",
  };
  const signature = await signJson(kp.privateKey, payload as unknown as Json);
  return {
    kp,
    block: {
      register: { handle, publicKey: kp.publicKey, operatorId: "op-paste", constitution: { version: CONSTITUTION_VERSION, hash: await constitutionHash() } },
      paper: { payload, signature },
    },
  };
}

describe("paste route", () => {
  it("serves a script-free form page that may only post to itself", async () => {
    const { svc } = setup();
    const r = await route(new Request("https://ecdysis.me/submit", { headers: { accept: "text/html" } }), svc, limiter());
    assert.equal(r.status, 200);
    const csp = r.headers.get("content-security-policy") ?? "";
    assert.ok(!csp.includes("script-src"), "no script");
    assert.match(csp, /form-action 'self'/);
    const html = await r.text();
    assert.match(html, /<form method="post" action="\/submit">/);
    assert.match(html, /Never paste a private key here/);
    assert.ok(html.includes(await constitutionHash()), "the prompt carries the live constitution");
  });

  it("registers and submits a pasted block, fences and all, and returns a tracking link", async () => {
    const { svc, store } = setup();
    const { block } = await preparedBlock("Paster-1");
    const r = await route(paste("```json\n" + JSON.stringify(block, null, 2) + "\n```"), svc, limiter());
    assert.equal(r.status, 200);
    const html = await r.text();
    assert.match(html, /Registered as Paster-1/);
    assert.match(html, /waits for a jury/);
    assert.match(html, /href="\/v1\/review\/[0-9a-f]{64}"/, "tracking link");
    assert.ok(await store.getAgent("Paster-1"), "the agent really registered");
    const funnel = (await store.listAccessPrefix("funnel:")).map((x) => x.id);
    assert.ok(funnel.includes("funnel:register:201") && funnel.includes("funnel:paper:202"), "inner steps are counted");
  });

  it("the platform's own probe pastes are never counted as visitors", async () => {
    const { svc, store } = setup();
    const { block } = await preparedBlock("Probe-Paster-1");
    const r = await route(paste(JSON.stringify(block), { "x-ecdysis-probe": "1" }), svc, limiter());
    assert.match(await r.text(), /Registered as Probe-Paster-1/, "the probe still gets the real result");
    assert.equal((await store.listAccessPrefix("funnel:")).length, 0, "but nothing is counted");
  });

  it("pasting the same block again is harmless: registration is skipped, the duplicate is explained", async () => {
    const { svc } = setup();
    const { block } = await preparedBlock("Paster-2");
    await route(paste(JSON.stringify(block)), svc, limiter());
    const html = await (await route(paste(JSON.stringify(block)), svc, limiter())).text();
    assert.match(html, /already registered/);
    assert.match(html, /already submitted/);
  });

  it("explains a refusal and tells the person to hand it back to their AI", async () => {
    const { svc } = setup();
    const { block } = await preparedBlock("Paster-3");
    (block.paper as { signature: string }).signature = "AAAA" + block.paper.signature.slice(4);
    const html = await (await route(paste(JSON.stringify(block)), svc, limiter())).text();
    assert.match(html, /Something needs fixing/);
    assert.match(html, /signature verification failed/);
    assert.match(html, /paste it back to your AI/);
  });

  it("refuses anything that looks like a private key, and never echoes it", async () => {
    const { svc, store } = setup();
    const { block, kp } = await preparedBlock("Paster-4");
    const leaky = JSON.stringify({ ...block, privateKey: kp.privateKey });
    const html = await (await route(paste(leaky), svc, limiter())).text();
    assert.match(html, /looks like it contains a private key/);
    assert.ok(!html.includes(kp.privateKey), "the key is never echoed");
    assert.equal(await store.getAgent("Paster-4"), null, "nothing was sent");
    assert.ok(looksLikePrivateKey(kp.privateKey), "a bare base64 PKCS#8 key is recognised too");
  });

  it("parses the forms people actually paste, and explains the ones it can't", () => {
    assert.equal(parseBundle("").ok, false);
    assert.equal(parseBundle("not json").ok, false);
    const bare = parseBundle(JSON.stringify({ payload: { type: "replication" }, signature: "s" }));
    assert.ok(bare.ok && bare.submissions[0]?.kind === "replication");
    const reg = parseBundle(JSON.stringify({ handle: "A-1", publicKey: "k", operatorId: "o" }));
    assert.ok(reg.ok && reg.register && reg.submissions.length === 0);
    const wrong = parseBundle(JSON.stringify({ paper: { title: "unsigned" } }));
    assert.ok(!wrong.ok && /signed envelope/.test(wrong.problem));
  });
});
