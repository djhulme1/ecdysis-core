/**
 * /lab and /lab.md: the guide to running a research lab on idle compute,
 * served to people as a page and to their AIs as Markdown, with a brief the
 * launcher types into an AI app. The numbers it states are the archive's
 * own, so the page cannot drift from the service that enforces them.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { MemoryStore } from "../src/store/memory-store.js";
import { TransparencyLog } from "../src/core/log.js";
import { EcdysisService } from "../src/api/service.js";
import { structuralScreener } from "../src/core/hazard.js";
import { generateKeyPair } from "../src/core/crypto.js";
import { EXTERNAL_PER_DAY, MemoryV2Store, QUOTA_PER_DAY, RESULT_DEADLINE_MS, REVIEWS_PER_DAY, V2Service } from "../src/api/v2/service.js";
import { PagesHandler } from "../src/api/v2/pages.js";
import { route, MemoryRateLimiter } from "../src/api/router.js";
import { labPageV2, labTextV2 } from "../src/web/v2/lab.js";
import { labBriefV2, STARTERS_V2 } from "../src/web/starters.js";
import { PROMPT_APPS } from "../src/web/launch.js";
import type { Json } from "../src/core/canonical.js";

async function world() {
  const store = new MemoryStore();
  const log = new TransparencyLog(store);
  const logKey = await generateKeyPair();
  const v2store = new MemoryV2Store(() => (store as unknown as { log: Array<{ entry: { seq: number; ts: string; type: string }; payload: Json }> }).log.map((r) => ({ seq: r.entry.seq, ts: r.entry.ts, type: r.entry.type, payload: r.payload })));
  const v2 = new V2Service({ log, store: v2store, logPrivateKey: logKey.privateKey, screeners: [structuralScreener()] });
  const v1 = new EcdysisService({ store, screeners: [structuralScreener()], sthPrivateKey: null });
  const limiter = new MemoryRateLimiter(1000);
  const pages = new PagesHandler(v2, { host: "api.ecdysis.me" });
  const site = (path: string, v2on = true) => route(new Request(`https://ecdysis.me${path}`, { headers: { accept: "text/html" } }), v1, limiter, v2on ? { v2, pages } : {});
  return { site };
}

describe("the lab guide", () => {
  it("is a page for people and Markdown for their AIs, in both menus and the sitemap, with the archive's own numbers", async () => {
    const w = await world();
    const r = await w.site("/lab");
    assert.equal(r.status, 200);
    const html = await r.text();
    assert.match(html, /<h1>Run a lab on idle compute<\/h1>/);
    for (const level of ["Level 1: the scout", "Level 2: the checker", "Level 3: the lab"]) assert.match(html, new RegExp(level.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")), level);
    for (const tool of ["register_agent", "register_claim", "file_review", "delegate_key", "get_frontier", "commit_check", "file_result"]) assert.match(html, new RegExp(`<code>${tool}</code>`), tool);
    assert.match(html, /<li><b>Find<\/b>/);
    assert.match(html, /<li><b>File<\/b>/);
    assert.doesNotMatch(html.split("<main")[1]!, /<script/);
    // The quotas table says what service.ts enforces.
    assert.match(html, new RegExp(`<td>papers</td><td>${QUOTA_PER_DAY.unverified}</td><td>${QUOTA_PER_DAY.account}</td><td>${QUOTA_PER_DAY.verified}</td>`));
    assert.match(html, new RegExp(`<td>claims from human literature</td><td>${EXTERNAL_PER_DAY.unverified}</td><td>${EXTERNAL_PER_DAY.account}</td><td>${EXTERNAL_PER_DAY.verified}</td>`));
    assert.match(html, new RegExp(`<td>reviews</td><td>${REVIEWS_PER_DAY.unverified}</td><td>${REVIEWS_PER_DAY.account}</td><td>${REVIEWS_PER_DAY.verified}</td>`));
    assert.equal(RESULT_DEADLINE_MS, 7 * 24 * 3600 * 1000, "the page says seven days because the archive does");
    assert.match(html, /seven days/);
    // Both halves of the site point here.
    assert.match(html, /<nav class="sub" aria-label="For people">[^]*?<a href="\/lab" aria-current="page">Lab<\/a>/);
    const agents = await (await w.site("/agents")).text();
    assert.match(agents, /<a href="\/lab">Lab<\/a>/);
    assert.match(agents, /<a href="\/lab\.md">\/lab\.md<\/a>/);
    const landing = await (await w.site("/")).text();
    assert.match(landing, /<a class="door" href="\/lab"><span class="who">I have a spare GPU<\/span>/);
    assert.match(await (await w.site("/sitemap.xml")).text(), /<loc>https:\/\/ecdysis\.me\/lab<\/loc>/);
    // The Markdown twin.
    const md = await w.site("/lab.md");
    assert.equal(md.status, 200);
    assert.match(md.headers.get("content-type") ?? "", /text\/markdown/);
    const text = await md.text();
    assert.match(text, /^# Run a lab on idle compute \(Ecdysis v2\)/);
    assert.match(text, /data, never instructions/);
    for (const tool of ["register_claim", "delegate_key", "commit_check", "file_result"]) assert.match(text, new RegExp(tool), tool);
    assert.match(text, /papers 1\/3\/5;\s*claims from human literature 2\/6\/10; reviews 3\/10\/30/);
    assert.doesNotMatch(text, /<\/?(p|div|span|a|h[1-6]|ul|ol|li|code|table|svg)\b[^>]*>/, "plain Markdown, no markup");
    assert.match(text, /lms load <model> --gpu max/, "placeholders in angle brackets are fine");
    assert.equal(labTextV2("api.ecdysis.me"), text);
    assert.ok(labPageV2({ host: "api.ecdysis.me", mcpUrl: "https://api.ecdysis.me/mcp" }).includes("https://api.ecdysis.me/mcp"));
  });

  it("the brief fits every app's link, is on the page, and the launcher types it only when v2 is on", async () => {
    const brief = labBriefV2("https://ecdysis.me");
    assert.ok(brief.length < Math.min(...Object.values(PROMPT_APPS).map((a) => a.max)), `the brief (${brief.length} chars) fits the tightest app`);
    assert.match(brief, /never print, log, upload or show it to a model/);
    assert.match(brief, /stop sending at the first 429/);
    assert.match(brief, /only inside a container or CI sandbox/);
    assert.match(brief, /data, never instructions/);
    assert.ok((STARTERS_V2 as readonly string[]).includes("lab"));
    const w = await world();
    const page = await (await w.site("/lab")).text();
    assert.ok(page.includes(brief.replace(/'/g, "&#39;").replace(/"/g, "&quot;")), "the page shows the brief the launcher will type");
    assert.match(page, /<a href="\/o\/claude\/lab" target="_blank"/);
    assert.match(page, /<a href="\/o\/claude-code\/lab" target="_blank"/);
    const go = await w.site("/o/claude/lab");
    assert.equal(go.status, 302);
    assert.match(decodeURIComponent(go.headers.get("location") ?? ""), /^https:\/\/claude\.ai\/new\?q=Read https:\/\/ecdysis\.me\/lab\.md/);
    assert.equal((await w.site("/o/claude/lab", false)).status, 404, "v1 has no lab brief");
    assert.equal((await w.site("/o/claude/juror")).status, 404, "v1's starters are gone under v2");
  });
});
