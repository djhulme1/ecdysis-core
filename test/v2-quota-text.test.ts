/**
 * No quota survives in the text agents read (quotas/0.3, 5 October 2026: the owner removed every cap on what an agent
 * files). This file used to pin each quota sentence to the constants after #40 raised them a hundredfold, because agents
 * plan their day by those words; now it pins the opposite: the skill, every tool description, the lab guide and the API
 * description say nothing is rationed, in the core's own words, and no figure of a daily allowance is left anywhere an
 * agent would read it.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { MemoryStore } from "../src/store/memory-store.js";
import { TransparencyLog } from "../src/core/log.js";
import { structuralScreener } from "../src/core/hazard.js";
import { generateKeyPair } from "../src/core/crypto.js";
import { MemoryV2Store, V2Service } from "../src/api/v2/service.js";
import { v2Tools } from "../src/api/v2/tools.js";
import { skillMdV2 } from "../src/api/v2/skill.js";
import { LAB_GUIDE_MD } from "../src/web/v2/lab-guide.js";
import { MCP_PER_ADDRESS_PER_MINUTE, PER_ADDRESS_PER_MINUTE, VOLUME_POLICY, VOLUME_SHORT } from "../src/core/v2/quotas.js";
import { BUCKET_LIMITS } from "../src/api/router.js";
import { openApiDocument } from "../src/api/openapi.js";
import type { Json } from "../src/core/canonical.js";
import { readFileSync } from "node:fs";

/**
 * Any figure of a daily allowance, in the shapes the text used to carry ("100 papers a day", "100/300/500", "1, 3 or 5 a
 * day", "ten a day", "Quotas:"). The doorbell's "at most 8 a day" is not one: it limits what Ecdysis sends a person, not
 * what an agent files.
 */
const RATIONED = /\b\d+ (?:papers?|claims?|reviews?|arguments?|attempts?|checks?|flags?|escalations?|vouch(?:es)?) a day\b|\b\d+\/\d+\/\d+\b|\b\d+, \d+ or \d+ a day\b|\bten (?:flags )?a day\b|\bthree (?:times )?a day\b|(?<!No )\bquotas?:|daily allowance|quota by tier|a day by tier/i;

async function tools() {
  const store = new MemoryStore();
  const log = new TransparencyLog(store);
  const logKey = await generateKeyPair();
  const v2 = new MemoryV2Store(() => (store as unknown as { log: Array<{ entry: { seq: number; ts: string; type: string }; payload: Json }> }).log.map((r) => ({ seq: r.entry.seq, ts: r.entry.ts, type: r.entry.type, payload: r.payload })));
  const svc = new V2Service({ log, store: v2, logPrivateKey: logKey.privateKey, screeners: [structuralScreener()] });
  return v2Tools(svc);
}

describe("no quotas in the text agents read (quotas/0.3)", () => {
  it("the skill says nothing is rationed, attempts are always open, and the throttle's numbers are the router's", () => {
    const md = skillMdV2("api.ecdysis.me");
    assert.ok(md.includes(VOLUME_POLICY), "the core's sentence");
    assert.match(md, /Attempts in particular are never refused for volume, never\npaused and never refused for missing evidence/);
    assert.match(md, new RegExp(`more than ${PER_ADDRESS_PER_MINUTE} requests in a minute \\(${MCP_PER_ADDRESS_PER_MINUTE.toLocaleString("en-GB")} through\\nthe connector\\)`));
    assert.doesNotMatch(md, RATIONED);
  });

  it("every tool description says it is not rationed where it once stated a quota, and none carries a figure", async () => {
    const defs = await tools();
    const desc = (name: string) => {
      const t = defs.find((d) => d.name === name);
      assert.ok(t, `tool ${name}`);
      return t.description;
    };
    for (const name of ["publish_claims", "file_attempt", "file_argument", "check_argument"]) assert.ok(desc(name).endsWith(VOLUME_SHORT), name);
    assert.match(desc("file_attempt"), /You can always file one: never rationed, never paused, never refused for missing evidence/);
    assert.match(desc("escalate"), /Not rationed; false escalations cost your record\./);
    for (const t of defs) assert.doesNotMatch(t.description, RATIONED, `${t.name} carries a quota`);
  });

  it("the lab guide and the API description carry no quota either", () => {
    assert.ok(LAB_GUIDE_MD.includes(VOLUME_POLICY));
    assert.doesNotMatch(LAB_GUIDE_MD, RATIONED);
    const api = JSON.stringify(openApiDocument({ api: "https://api.ecdysis.me", site: "https://ecdysis.me" }));
    assert.doesNotMatch(api, /quota|a day per operator/i);
  });

  it("the throttle in wrangler.toml is the core's, and there is no per-agent ceiling any more", () => {
    assert.deepEqual(BUCKET_LIMITS, { mcp: MCP_PER_ADDRESS_PER_MINUTE });
    const toml = readFileSync(new URL("../wrangler.toml", import.meta.url), "utf8");
    assert.match(toml, new RegExp(`name = "RL_KEY"\\nnamespace_id = "1001"\\nsimple = \\{ limit = ${PER_ADDRESS_PER_MINUTE}, period = 60 \\}`));
    assert.match(toml, new RegExp(`name = "RL_MCP"\\nnamespace_id = "1002"\\nsimple = \\{ limit = ${MCP_PER_ADDRESS_PER_MINUTE}, period = 60 \\}`));
    assert.doesNotMatch(toml, /RL_AGENT/);
  });
});
