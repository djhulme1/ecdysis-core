/**
 * /scoring.md: the leaderboard's scoring method as a versioned document.
 * The document names the commit of the code that is the rule and the
 * SHA-256 of each scoring module at that commit; this test fails when the
 * modules on disk no longer match the hashes the document publishes, so a
 * change to the rule cannot ship without a new version of the document
 * (an effective date, a log sequence number, who gains and who loses).
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { MemoryStore } from "../src/store/memory-store.js";
import { TransparencyLog } from "../src/core/log.js";
import { structuralScreener } from "../src/core/hazard.js";
import { generateKeyPair } from "../src/core/crypto.js";
import { MemoryV2Store, V2Service } from "../src/api/v2/service.js";
import { PagesHandler } from "../src/api/v2/pages.js";
import { route, MemoryRateLimiter } from "../src/api/router.js";
import { SCORING_METHOD_MD, SCORING_METHOD_VERSION, SCORING_RULE_COMMIT, mirrorScoringMd } from "../src/web/v2/scoring-method.js";
import { LEADERBOARD_VERSION } from "../src/core/v2/leaderboard.js";
import { CREDENCE_V2_VERSION, SETTLEMENT } from "../src/core/v2/credence.js";
import { TRACK_VERSION } from "../src/core/v2/scoring.js";
import type { Json } from "../src/core/canonical.js";

const sha256 = (path: string) => createHash("sha256").update(readFileSync(new URL(`../${path}`, import.meta.url))).digest("hex");

async function world() {
  const store = new MemoryStore();
  const log = new TransparencyLog(store);
  const logKey = await generateKeyPair();
  const v2store = new MemoryV2Store(() => (store as unknown as { log: Array<{ entry: { seq: number; ts: string; type: string }; payload: Json }> }).log.map((r) => ({ seq: r.entry.seq, ts: r.entry.ts, type: r.entry.type, payload: r.payload })));
  const v2 = new V2Service({ log, store: v2store, logPrivateKey: logKey.privateKey, screeners: [structuralScreener()] });
  const limiter = new MemoryRateLimiter(1000);
  const pages = new PagesHandler(v2, { host: "api.ecdysis.me" });
  const site = (path: string) => route(new Request(`https://ecdysis.me${path}`, { headers: { accept: "text/html" } }), limiter, { v2, pages });
  return { site };
}

describe("the scoring method", () => {
  it("is served at /scoring.md, mirrored, linked from the leaderboard and the protocol, and names its version and commit", async () => {
    const w = await world();
    const r = await w.site("/scoring.md");
    assert.equal(r.status, 200);
    assert.match(r.headers.get("content-type") ?? "", /text\/markdown/);
    const text = await r.text();
    assert.equal(text, SCORING_METHOD_MD);
    assert.equal(mirrorScoringMd(), text);
    assert.match(text, /^# The Ecdysis leaderboard: scoring method\n/);
    assert.ok(text.includes(`Version ${SCORING_METHOD_VERSION} of this document`));
    assert.ok(text.includes(SCORING_RULE_COMMIT), "the document names the commit that is the rule");
    for (const v of [LEADERBOARD_VERSION, TRACK_VERSION, CREDENCE_V2_VERSION]) assert.ok(text.includes(`(${v})`), `${v} is named`);
    assert.equal(SETTLEMENT, "resolution", "the document says settlement is by resolution because the code does");
    assert.match(text, /Settlement is by resolution/);
    assert.match(text, /never retrospective/);
    assert.match(await (await w.site("/leaderboard")).text(), /<a href="\/scoring\.md">\/scoring\.md<\/a>/);
    assert.match(await (await w.site("/skill.md")).text(), /ecdysis\.me\/scoring\.md/);
    assert.match(await (await w.site("/sitemap.xml")).text(), /<loc>https:\/\/ecdysis\.me\/scoring\.md<\/loc>/);
  });

  it("publishes the hash of every scoring module, and the modules on disk still match: the rule cannot change without a new version", () => {
    const rows = [...SCORING_METHOD_MD.matchAll(/\| `(src\/core\/v2\/[a-z-]+\.ts)`[^|]*\|[^|]*\| `([0-9a-f]{64})` \|/g)];
    assert.equal(rows.length, 7, "seven modules are named with a hash");
    for (const [, path, hash] of rows) assert.equal(sha256(path!), hash, `${path} has changed since the scoring method was published: publish a new version (section 6) before shipping it`);
  });
});
