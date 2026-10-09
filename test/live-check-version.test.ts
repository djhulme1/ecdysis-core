/**
 * The live check must expect the credence version the code serves, never one
 * written into the script by hand. On 4 October 2026 the core moved to
 * credence/0.4 while scripts/live-check.ts still asked production for
 * "credence/0.3", so a healthy deployment read as a failed probe.
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { MemoryRateLimiter, route } from "../src/api/router.js";
import { MemoryStore } from "../src/store/memory-store.js";
import { TransparencyLog } from "../src/core/log.js";
import { generateKeyPair } from "../src/core/crypto.js";
import { MemoryV2Store, V2Service } from "../src/api/v2/service.js";
import { PagesHandler } from "../src/api/v2/pages.js";
import type { Json } from "../src/core/canonical.js";
import { LIVE_PAGE_NEEDLES } from "../scripts/live-check-pages.js";

test("the live check reads the credence version from the core, not from a literal", () => {
  const src = readFileSync(new URL("../scripts/live-check.ts", import.meta.url), "utf8");
  assert.match(src, /import \{ CREDENCE_V2_VERSION \} from "\.\.\/src\/core\/v2\/credence\.js";/);
  assert.match(src, /b\.version === CREDENCE_V2_VERSION/);
  // A full version literal (credence/0.<digit>) anywhere in the script would go stale at the next version.
  assert.deepEqual(src.match(/credence\/0\.\d/g) ?? [], []);
});

test("the live check asks each page for what the page carries, so a redesign cannot leave its probe behind", async () => {
  const now = () => new Date(Date.UTC(2026, 9, 9, 12, 0, 0));
  const store = new MemoryStore();
  const log = new TransparencyLog(store, now);
  const logKey = await generateKeyPair();
  const v2 = new V2Service({ log, store: new MemoryV2Store(() => (store as unknown as { log: Array<{ entry: { seq: number; ts: string; type: string }; payload: Json }> }).log.map((r) => ({ seq: r.entry.seq, ts: r.entry.ts, type: r.entry.type, payload: r.payload }))), logPrivateKey: logKey.privateKey, now });
  const opts = { v2, pages: new PagesHandler(v2, { host: "ecdysis.me", logPublicKey: logKey.publicKey }), sthPublicKey: logKey.publicKey };
  const src = readFileSync(new URL("../scripts/live-check.ts", import.meta.url), "utf8");
  assert.match(src, /for \(const \[path, needle\] of LIVE_PAGE_NEEDLES\)/, "the script probes the pages listed here, and no others written into it by hand");
  assert.ok(LIVE_PAGE_NEEDLES.some(([p]) => p === "/claims") && LIVE_PAGE_NEEDLES.some(([p]) => p === "/claims/table"));
  for (const [path, needle] of LIVE_PAGE_NEEDLES) {
    const r = await route(new Request(`https://ecdysis.me${path}`, { headers: { accept: "text/html" } }), new MemoryRateLimiter(1000), opts);
    assert.equal(r.status, 200, path);
    assert.ok((await r.text()).includes(needle), `${path} carries "${needle}"`);
  }
});
