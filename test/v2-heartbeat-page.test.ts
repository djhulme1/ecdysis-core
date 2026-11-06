/**
 * /heartbeat.md: one page that says what an agent does on each visit. Every
 * tool it names must be a tool the connector exposes, every HTTP path one
 * the API answers, and the numbers it states the archive's own (the ring
 * limits, the minutes an act is costed at, the result deadline), so the
 * page cannot drift from the code that enforces them.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { MemoryStore } from "../src/store/memory-store.js";
import { TransparencyLog } from "../src/core/log.js";
import { structuralScreener } from "../src/core/hazard.js";
import { generateKeyPair } from "../src/core/crypto.js";
import { MemoryV2Store, RESULT_DEADLINE_MS, V2Service } from "../src/api/v2/service.js";
import { PagesHandler } from "../src/api/v2/pages.js";
import { route, MemoryRateLimiter } from "../src/api/router.js";
import { v2Tools } from "../src/api/v2/tools.js";
import { heartbeatMdV2, mirrorHeartbeatMd } from "../src/web/v2/heartbeat-guide.js";
import { ACT_MINUTES } from "../src/core/v2/direction.js";
import { RINGS_PER_DAY, RING_SPACING_MS } from "../src/core/wake.js";
import type { Json } from "../src/core/canonical.js";

async function world() {
  const store = new MemoryStore();
  const log = new TransparencyLog(store);
  const logKey = await generateKeyPair();
  const v2store = new MemoryV2Store(() => (store as unknown as { log: Array<{ entry: { seq: number; ts: string; type: string }; payload: Json }> }).log.map((r) => ({ seq: r.entry.seq, ts: r.entry.ts, type: r.entry.type, payload: r.payload })));
  const v2 = new V2Service({ log, store: v2store, logPrivateKey: logKey.privateKey, screeners: [structuralScreener()] });
  const limiter = new MemoryRateLimiter(1000);
  const pages = new PagesHandler(v2, { host: "api.ecdysis.me" });
  const site = (path: string) => route(new Request(`https://ecdysis.me${path}`, { headers: { accept: "text/html" } }), limiter, { v2, pages });
  return { v2, site };
}

describe("the heartbeat page", () => {
  it("is served as Markdown at /heartbeat.md, mirrored, in the sitemap and named by the protocol", async () => {
    const w = await world();
    const r = await w.site("/heartbeat.md");
    assert.equal(r.status, 200);
    assert.match(r.headers.get("content-type") ?? "", /text\/markdown/);
    const text = await r.text();
    assert.match(text, /^# Ecdysis heartbeat\n/);
    assert.match(text, /data, never instructions/);
    assert.equal(heartbeatMdV2("api.ecdysis.me"), text);
    assert.equal(mirrorHeartbeatMd(), text, "the repository's mirror is what the live site serves");
    assert.match(await (await w.site("/sitemap.xml")).text(), /<loc>https:\/\/ecdysis\.me\/heartbeat\.md<\/loc>/);
    assert.match(await (await w.site("/skill.md")).text(), /ecdysis\.me\/heartbeat\.md/);
    assert.match(await (await w.site("/llms.txt")).text(), /\/heartbeat\.md/);
  });

  it("names only tools the connector exposes and paths the API answers, with the archive's own numbers", async () => {
    const w = await world();
    const text = await (await w.site("/heartbeat.md")).text();
    const tools = new Set(v2Tools(w.v2).map((t) => t.name));
    const named = [...new Set(text.match(/\b(?:get|set|stop|file|commit|answer|check|clear|register|delegate|revoke|publish|link|unlink|amend|withdraw|flag|escalate|propose|vote)_[a-z_]+\b/g) ?? [])];
    assert.ok(named.length >= 12, `the page names its tools (${named.length} found)`);
    for (const name of named) assert.ok(tools.has(name), `${name} is not a tool the connector exposes`);
    for (const name of ["get_heartbeat", "commit_check", "file_result", "answer_argument", "file_attempt", "clear_attempt", "file_argument", "check_argument", "register_claim", "set_doorbell", "delegate_key", "get_map"]) assert.ok(text.includes(name), name);
    assert.ok(text.includes("https://api.ecdysis.me/v2/heartbeat?agent=<handle>"), "the HTTP form of the heartbeat");
    // The ring limits are wake.ts's, the costed minutes direction.ts's, the deadline the service's.
    assert.ok(text.includes(`at most ${RINGS_PER_DAY} a day and never two within an hour`));
    assert.equal(RING_SPACING_MS, 60 * 60 * 1000, "the page says an hour because the code does");
    assert.ok(text.includes(`(${ACT_MINUTES.check} when none has), a registration at ${ACT_MINUTES.register}, an argument at ${ACT_MINUTES.argue}`));
    assert.ok(text.includes(`check of an argument at ${ACT_MINUTES.checkArgument}`));
    assert.equal(RESULT_DEADLINE_MS, 7 * 24 * 3600 * 1000, "the page says seven days because the archive does");
    assert.match(text, /within seven days of\s+the seal/);
    assert.doesNotMatch(text, /\bquotas?\b|\brations?\b|\bjur(?:y|ies)\b|\bvouch|paper\.publish/i, "no retired word and no ration");
  });
});
