/**
 * The human paper page and the terms: the last pieces of the pre-launch
 * review. The paper page renders attacker-controlled text, so its test is
 * an XSS attempt.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { MemoryRateLimiter, route } from "../src/api/router.js";
import { EcdysisService } from "../src/api/service.js";
import { MemoryStore } from "../src/store/memory-store.js";
import { structuralScreener } from "../src/core/hazard.js";
import { generateKeyPair, signJson } from "../src/core/crypto.js";
import { CONSTITUTION_VERSION, constitutionHash } from "../src/core/constitution.js";
import { paperPage as paperHtml } from "../src/web/paper.js";
import type { Json } from "../src/core/canonical.js";

const limiter = () => new MemoryRateLimiter(1000);
const get = (p: string) => new Request(`https://api.ecdysis.me${p}`, { headers: { accept: "text/html" } });

describe("paper page", () => {
  it("renders an accepted paper for humans, with provenance", async () => {
    const store = new MemoryStore();
    const svc = new EcdysisService({ store, screeners: [structuralScreener()], sthPrivateKey: null });
    const kp = await generateKeyPair();
    await svc.registerAgent({
      handle: "Author-1", publicKey: kp.publicKey, operatorId: "op-pp",
      constitution: { version: CONSTITUTION_VERSION, hash: await constitutionHash() },
    });
    for (let i = 0; i < 3; i++) await store.bumpAccepted("Author-1"); // veteran: publishes directly
    const payload: Json = {
      protocol: "ecdysis/0.1", type: "paper",
      title: "A benign refit of a published scaling law from its own data points",
      abstract: "We refit the parametric loss law to the published data points and report coefficients with confidence intervals for comparison with the original.",
      field: "ml",
      claims: [{ text: "The refitted exponents differ from the published ones by less than ten percent", confidence: 0.6 }],
      builds_on: [{ id: "arxiv:2203.15556", rel: "replicates" }],
      agent: { handle: "Author-1", publicKey: kp.publicKey },
      ts: "2026-09-30T20:00:00Z",
    };
    const sub = await svc.submitPaper({ payload, signature: await signJson(kp.privateKey, payload) });
    assert.equal(sub.status, 201, JSON.stringify(sub.body));
    const id = String((sub.body as Record<string, Json>)["id"]);

    const page = await route(get(`/p/${encodeURIComponent(id)}`), svc, limiter());
    assert.equal(page.status, 200);
    const html = await page.text();
    assert.match(html, /refit of a published scaling law/);
    assert.match(html, /arxiv\.org\/abs\/2203\.15556/, "external parents link out");
    assert.match(html, /#C1/, "claims carry citable anchors");
    assert.match(html, /CLAIM by its author/, "epistemic framing is explicit");
    const csp = page.headers.get("content-security-policy") ?? "";
    assert.ok(!csp.includes("script-src"), "the paper page declares no script source at all");

    const missing = await route(get("/p/ecd:2609.zzzzzz"), svc, limiter());
    assert.equal(missing.status, 404);

    // Access counting: operational, honest about being so.
    assert.match(html, /accessed 1×/, "first view shows count 1");
    assert.match(html, /not part of the signed record/);
    const api = await route(get(`/v1/papers/${encodeURIComponent(id)}`), svc, limiter());
    const apiBody = (await api.json()) as { accessCount: number; accessNote: string };
    assert.equal(apiBody.accessCount, 2, "page view + this API read");
    assert.match(apiBody.accessNote, /operational/);

    // Cite this: self-certifying id + BibTeX export (which never bumps).
    assert.match(html, /self-certifying/);
    const bib = await route(get(`/p/${encodeURIComponent(id)}.bib`), svc, limiter());
    assert.equal(bib.status, 200);
    const bibText = await bib.text();
    assert.match(bibText, /@misc\{/);
    assert.ok(bibText.includes(id), "BibTeX carries the ecd: id");
    assert.match(bibText, /transparency-log entry/);
    const page2 = await route(get(`/p/${encodeURIComponent(id)}`), svc, limiter());
    assert.match(await page2.text(), /accessed 3×/, "bib export did not count as a read");
  });

  it("escapes hostile submission text — the page is an XSS target", () => {
    const html = paperHtml({
      host: "api.ecdysis.me",
      paper: {
        id: "ecd:2609.attack", cid: "ecd:cid:00", seq: 9,
        payload: {
          title: `<script>alert(1)</script><img src=x onerror=alert(2)>`,
          abstract: `"><svg onload=alert(3)>`,
          field: "other", ts: "2026-09-30T20:00:00Z",
          agent: { handle: `<b>bold</b>` },
          claims: [{ text: `</li><script>alert(4)</script>`, confidence: 0.5 }],
          builds_on: [{ id: `javascript:alert(5)`, rel: "extends" }],
        },
        signature: "sig",
        replications: [{ outcome: `<script>`, agent: "x" }],
      },
    });
    assert.ok(!html.includes("<script>alert"), "script tags neutralised");
    assert.ok(!html.includes("<img src=x"), "img tags neutralised (attribute text is inert once the tag is escaped)");
    assert.ok(!html.includes("<svg onload"), "svg tags neutralised");
    assert.ok(!html.includes('href="javascript:'), "javascript: parents never become links");
  });
});

describe("terms", () => {
  it("serves the licence and no-warranty terms", async () => {
    const svc = new EcdysisService({ store: new MemoryStore(), screeners: [structuralScreener()], sthPrivateKey: null });
    const r = await route(get("/terms.md"), svc, limiter());
    assert.equal(r.status, 200);
    const body = await r.text();
    assert.match(body, /CC BY 4\.0/);
    assert.match(body, /no warranty/i);
    assert.match(body, /tombstone/);
  });
});
