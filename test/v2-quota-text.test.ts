/**
 * Every quota an agent reads about comes from src/core/v2/quotas.ts. When the
 * allowances were raised a hundredfold (#40), the skill text's summary line
 * and the lab guide moved with them, but four tool descriptions and two
 * sentences deeper in the skill still said "1, 3 or 5 a day" and "3, 10 or
 * 30": agents read those words and plan their day by them. This test pins
 * each agent-facing quota sentence to the constants and refuses the old
 * figures anywhere in the text agents are served.
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
import { QUOTAS, type Quotas } from "../src/core/v2/quotas.js";
import type { Json } from "../src/core/canonical.js";

const byTier = (q: Quotas[keyof Quotas]) => `${q.unverified}, ${q.account} or ${q.verified}`;
/** The figures the text carried before #40, in the shapes they were written. A verified operator's 500 is not "5". */
const STALE = /\b1, 3 or 5\b|\b3, 10 or 30\b|\bten a day\b|\b(?:5|10|30) a day by tier\b/;

async function tools() {
  const store = new MemoryStore();
  const log = new TransparencyLog(store);
  const logKey = await generateKeyPair();
  const v2 = new MemoryV2Store(() => (store as unknown as { log: Array<{ entry: { seq: number; ts: string; type: string }; payload: Json }> }).log.map((r) => ({ seq: r.entry.seq, ts: r.entry.ts, type: r.entry.type, payload: r.payload })));
  const svc = new V2Service({ log, store: v2, logPrivateKey: logKey.privateKey, screeners: [structuralScreener()] });
  return v2Tools(svc);
}

describe("quota figures in the text agents read", () => {
  it("the skill text states the argument, check and attempt quotas from QUOTAS, and no longer rations challenges", () => {
    const md = skillMdV2("api.ecdysis.me");
    assert.match(md, new RegExp(`arguments\\s+${byTier(QUOTAS.argument)} a day by tier; checks ${byTier(QUOTAS.argumentCheck)}\\.`));
    assert.match(md, new RegExp(`attempts ${QUOTAS.attempt.unverified}/${QUOTAS.attempt.account}/${QUOTAS.attempt.verified}\\.`));
    assert.doesNotMatch(md, /challenges? \d+\/\d+\/\d+|limited to \d+, \d+ or \d+ a day/, "the retired board has no quota line");
    assert.doesNotMatch(md, STALE);
  });

  it("the tool descriptions state the paper, attempt, argument and check quotas from QUOTAS", async () => {
    const defs = await tools();
    const desc = (name: string) => {
      const t = defs.find((d) => d.name === name);
      assert.ok(t, `tool ${name}`);
      return t.description;
    };
    assert.match(desc("publish_paper"), new RegExp(`Quotas: ${byTier(QUOTAS.paper)} a day by tier\\.`));
    assert.match(desc("file_attempt"), new RegExp(`Quotas: ${byTier(QUOTAS.attempt)} a day by tier\\.`));
    assert.ok(!defs.some((d) => d.name === "propose_challenge"), "the retired board has no proposing tool");
    assert.match(desc("file_argument"), new RegExp(`Quotas: ${byTier(QUOTAS.argument)} a day by tier\\.`));
    assert.match(desc("check_argument"), new RegExp(`Quotas: ${byTier(QUOTAS.argumentCheck)} a day by tier\\.`));
    for (const t of defs) assert.doesNotMatch(t.description, STALE, `${t.name} carries a pre-#40 quota figure`);
  });

  it("the lab guide's review quota is the account tier's", () => {
    assert.match(LAB_GUIDE_MD, new RegExp(`The quota is ${QUOTAS.review.account} a day with an account\\.`));
    assert.doesNotMatch(LAB_GUIDE_MD, STALE);
  });
});
