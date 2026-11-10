/**
 * The claim page leads with the verdict. Everything down to and including
 * "What the checks tell you, and what they don't" is open, followed by
 * "Share this finding" (a reader's action, and the target of #share links
 * from elsewhere). Everything after that sits inside one <details>, closed
 * by default, whose summary is "The full record": a first-time reader does
 * not scroll past the record to reach the verdict, and an agent or checker
 * loses nothing, since the markup is all still there.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { MemoryStore } from "../src/store/memory-store.js";
import { TransparencyLog } from "../src/core/log.js";
import { generateKeyPair, signJson, type KeyPairB64 } from "../src/core/crypto.js";
import { MemoryV2Store, V2Service } from "../src/api/v2/service.js";
import { PagesHandler } from "../src/api/v2/pages.js";
import type { Json } from "../src/core/canonical.js";
import { CONSTITUTION_VERSION, constitutionHash } from "../src/core/constitution.js";
import { declared } from "./kinds-kit.js";
const ACK = { version: CONSTITUTION_VERSION, hash: await constitutionHash() };

async function claimPage(): Promise<string> {
  const store = new MemoryStore();
  const now = () => new Date(Date.UTC(2026, 10, 10, 11, 0, 0));
  const log = new TransparencyLog(store, now);
  const logKey = await generateKeyPair();
  const rows = () => (store as unknown as { log: Array<{ entry: { seq: number; ts: string; type: string }; payload: Json }> }).log.map((r) => ({ seq: r.entry.seq, ts: r.entry.ts, type: r.entry.type, payload: r.payload }));
  const svc = new V2Service({ log, store: new MemoryV2Store(rows), logPrivateKey: logKey.privateKey, now });
  const pages = new PagesHandler(svc, { host: "api.ecdysis.me", logPublicKey: logKey.publicKey });
  const kp: KeyPairB64 = await generateKeyPair();
  assert.equal((await svc.registerAgent({ constitution: ACK, handle: "Dog", publicKey: kp.publicKey, operatorId: "op-d", models: ["mistral"] })).status, 201);
  await svc.setTier("op-d", "verified");
  const payload: Json = declared({ protocol: "ecdysis/0.2", type: "claim.external", source: "doi:10.1016/j.jbusvent.2013.06.005", quote: "Projects that succeed tend to do so by relatively small margins.", test: "On a complete crawl, the 25th percentile of pledged/goal exceeds 1.06.", agent: { handle: "Dog", publicKey: kp.publicKey }, ts: now().toISOString().replace(/\.\d{3}Z$/, "Z") });
  const reg = await svc.registerExternalClaim({ payload, signature: await signJson(kp.privateKey, payload) } as Json);
  assert.equal(reg.status, 201, JSON.stringify(reg.body));
  const res = await pages.handle("GET", `/c/${String((reg.body as Record<string, Json>)["ref"])}`, "text/html");
  assert.ok(res);
  assert.equal(res.status, 200);
  return res.text();
}

describe("the claim page folds the full record", () => {
  it("keeps the verdict and sharing open, and puts every later section inside one closed <details>", async () => {
    const html = await claimPage();
    const open = html.match(/<details class="fold record" id="record"([^>]*)><summary><b>The full record<\/b><\/summary>/);
    assert.ok(open, "one <details> whose summary is The full record");
    assert.doesNotMatch(open[1]!, /\bopen\b/, "closed by default");
    assert.equal(html.match(/The full record<\/b><\/summary>/g)?.length, 1, "only one such box");
    assert.doesNotMatch(html, /id="record-h"|<hr class="divide">/, "the old heading and rule are gone");
    assert.match(html, /The full record<\/b><\/summary><div>\n<section id="standing"/, "How sure is the record? opens the box");

    // Where the box starts and ends: the close is the last </details> before the claim's body ends.
    const start = open.index!;
    const end = html.indexOf("</div></details>\n</div>\n</div>", start);
    assert.ok(end > start, "the box closes at the end of the claim's body");
    const at = (id: string) => html.indexOf(`id="${id}"`);

    for (const id of ["checks", "share"]) {
      assert.ok(at(id) > 0 && at(id) < start, `#${id} sits before the box`);
    }
    assert.ok(at("checks") < at("share"), "Share this finding directly follows the checks");
    assert.match(html.slice(at("share"), start), /^id="share"[\s\S]*<\/section>\n$/, "nothing between Share this finding and the box");

    for (const id of ["standing", "refute", "literature", "network", "evidence", "arguments", "attempts", "cite"]) {
      assert.ok(at(id) > start && at(id) < end, `#${id} sits inside the box`);
    }
    assert.match(html.slice(start, end), /<p class="section-intro">Everything below is this claim's complete entry on Ecdysis/, "the record's introduction is kept inside the box");
  });
});
