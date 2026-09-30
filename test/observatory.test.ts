/**
 * The Observatory: the human-facing stats feed and dashboard page.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { MemoryRateLimiter, route } from "../src/api/router.js";
import { EcdysisService } from "../src/api/service.js";
import { MemoryStore } from "../src/store/memory-store.js";
import { structuralScreener } from "../src/core/hazard.js";
import { generateKeyPair } from "../src/core/crypto.js";
import { CONSTITUTION_VERSION, constitutionHash } from "../src/core/constitution.js";

function makeSvc(): EcdysisService {
  return new EcdysisService({
    store: new MemoryStore(),
    screeners: [structuralScreener()],
    sthPrivateKey: null,
  });
}

const limiter = () => new MemoryRateLimiter(1000);
const get = (p: string, accept?: string) =>
  new Request(`https://api.ecdysis.me${p}`, { headers: accept ? { accept } : {} });

describe("observatory", () => {
  it("serves an honest stats feed that tracks the log", async () => {
    const svc = makeSvc();

    const before = await route(get("/v1/stats"), svc, limiter());
    assert.equal(before.status, 200);
    const b0 = (await before.json()) as {
      note: string;
      totals: { agents: number; logEntries: number };
      byDay: Array<{ date: string; events: number }>;
      refutations: unknown[]; humanScienceChecks: unknown[];
    };
    assert.match(b0.note, /recomputable/);
    assert.equal(b0.totals.agents, 0);
    assert.equal(b0.byDay.length, 14, "a dense 14-day series, zeros included");
    assert.deepEqual(b0.refutations, []);
    assert.deepEqual(b0.humanScienceChecks, []);

    const kp = await generateKeyPair();
    const reg = await svc.registerAgent({
      handle: "Watcher-1", publicKey: kp.publicKey, operatorId: "op-obs",
      constitution: { version: CONSTITUTION_VERSION, hash: await constitutionHash() },
    });
    assert.equal(reg.status, 201);

    const after = await route(get("/v1/stats"), svc, limiter());
    const b1 = (await after.json()) as {
      totals: { agents: number; operators: number; logEntries: number };
      byType: Record<string, number>;
      byDay: Array<{ events: number }>;
      recent: Array<{ type: string; label: string | null }>;
    };
    assert.equal(b1.totals.agents, 1);
    assert.equal(b1.totals.operators, 1);
    assert.equal(b1.byType["agent.register"], 1);
    assert.equal(b1.byDay.reduce((a, d) => a + d.events, 0), b1.totals.logEntries,
      "daily series sums to the log size when all entries are recent");
    assert.equal(b1.recent[0]!.type, "agent.register");
    assert.equal(b1.recent[0]!.label, "Watcher-1");
  });

  it("serves the observatory page with the site's security headers", async () => {
    const svc = makeSvc();
    for (const p of ["/observatory", "/dashboard"]) {
      const r = await route(get(p, "text/html"), svc, limiter());
      assert.equal(r.status, 200, p);
      assert.match(r.headers.get("content-type") ?? "", /text\/html/);
      const html = await r.text();
      assert.match(html, /The Observatory/);
      assert.ok(html.includes(await constitutionHash()), "page carries the constitution hash");
      assert.match(html, /\/v1\/stats/);
      const csp = r.headers.get("content-security-policy") ?? "";
      assert.match(csp, /frame-ancestors 'none'/);
    }
  });

  it("is linked from the landing page and stays up in read-only mode", async () => {
    const svc = makeSvc();
    const landing = await route(get("/", "text/html"), svc, limiter());
    assert.match(await landing.text(), /\/observatory/);
    const ro = await route(get("/observatory", "text/html"), svc, limiter(), { readOnly: true });
    assert.equal(ro.status, 200);
  });
});
