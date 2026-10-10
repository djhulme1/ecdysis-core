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
import { structuralScreener } from "../src/core/hazard.js";
import { generateKeyPair } from "../src/core/crypto.js";
import { MemoryV2Store, RESULT_DEADLINE_MS, V2Service } from "../src/api/v2/service.js";
import { PER_ADDRESS_PER_MINUTE, VOLUME_POLICY } from "../src/core/v2/quotas.js";
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
  const limiter = new MemoryRateLimiter(1000);
  const pages = new PagesHandler(v2, { host: "api.ecdysis.me" });
  const site = (path: string) => route(new Request(`https://ecdysis.me${path}`, { headers: { accept: "text/html" } }), limiter, { v2, pages });
  return { site };
}

describe("the lab guide", () => {
  it("is the guide rendered for people, Markdown and a script for their AIs, in both menus and the sitemap, with the archive's own numbers", async () => {
    const w = await world();
    const r = await w.site("/lab");
    assert.equal(r.status, 200);
    const html = await r.text();
    assert.match(html, /<h1>Run a lab on idle compute<\/h1>/);
    assert.doesNotMatch(html.split("<main")[1]!, /<h1>Ecdysis on Idle Compute<\/h1>/, "the guide's own title gives way to the page's");
    for (const h of ["What you need", "Level 1: one script, one model", "Level 2: one agent that also checks claims", "Level 3: a multi-model lab", "Getting the most from the hardware", "Rules that keep your agents&#39; work credible", "When something fails", "Brief for your AI", "Sources"]) assert.match(html, new RegExp(`<h2 id="[a-z0-9-]+">${h.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}</h2>`), h);
    assert.match(html, /<pre class="lang-python"><code>&quot;&quot;&quot;level1\.py: load-bearing and new arXiv papers/, "the level-1 script is in the page, escaped");
    assert.match(html, /<figure class="fig wide diagram"><figcaption><span class="fig-title">Models do the work; only the outbox signs and sends<\/span><\/figcaption><div class="scroll"><svg /, "the lab's drawing is inline where the guide places its image");
    assert.doesNotMatch(html, /#2f6fde|#9a9a92|#1f1f1f/, "the drawing uses the design tokens, not the document's hex colours");
    assert.match(html, /<div class="table"><table><thead><tr><th>You need<\/th><th>From level<\/th><th>Notes<\/th>/);
    assert.match(html, /<a href="https:\/\/lmstudio\.ai" rel="noopener">LM Studio<\/a>/);
    assert.doesNotMatch(html, /<img(?![^>]*src="\/brand\/)/, "no image is loaded but the brand's own");
    assert.doesNotMatch(html.split("<main")[1]!, /<script/);
    // The numbers in the guide are the service's.
    // quotas/0.3: the guide says nothing is rationed, in the core's own words, and names the throttle's number.
    assert.ok(html.includes(VOLUME_POLICY), "the no-quotas sentence is on the page");
    assert.doesNotMatch(html, /By tier \(unverified, account, verified\): papers \d+/, "no quota sentence survives");
    assert.ok(html.includes(`more than ${PER_ADDRESS_PER_MINUTE} requests in a minute`), "the throttle's number is the router's");
    assert.equal(RESULT_DEADLINE_MS, 7 * 24 * 3600 * 1000, "the guide says seven days because the archive does");
    assert.match(html, /seven days away/);
    assert.match(html, /PER_RUN = int\(os\.environ\.get\(&quot;PER_RUN&quot;, &quot;6&quot;\)\)/);
    // Both halves of the site point here, and so does the person's page.
    assert.match(html, /<nav class="sub" aria-label="In this section">[^]*?<a href="\/lab" aria-current="page">Run a lab<\/a>/, "a tab under How it works");
    const agents = await (await w.site("/agents")).text();
    assert.match(agents, /<footer[^]*<a href="\/lab">Run a lab<\/a>/, "every page's footer lists it");
    assert.match(agents, /<a href="\/lab\.md">\/lab\.md<\/a>/);
    const landing = await (await w.site("/")).text();
    assert.match(landing, /<h3>Lend spare computing power<\/h3>[^]*?<a class="btn quiet" href="\/lab">Run a lab<\/a>/);
    assert.match(await (await w.site("/sitemap.xml")).text(), /<loc>https:\/\/ecdysis\.me\/lab<\/loc>/);
    assert.match(await (await w.site("/skill.md")).text(), /ecdysis\.me\/lab\.md is the guide to running\ncontinuously/);
    // The Markdown twin and the script.
    const md = await w.site("/lab.md");
    assert.equal(md.status, 200);
    assert.match(md.headers.get("content-type") ?? "", /text\/markdown/);
    const text = await md.text();
    assert.match(text, /^# Ecdysis on Idle Compute\n/);
    assert.match(text, /data, never instructions/);
    for (const tool of ["signed_post", "/v2/keys/delegate", "/v2/checks", "/v2/checks/result"]) assert.ok(text.includes(tool), tool);
    assert.ok(text.includes(VOLUME_POLICY), "the Markdown twin says nothing is rationed");
    assert.doesNotMatch(text.split(VOLUME_POLICY).join(""), /\bquotas?\b/i, "no quota survives in the guide, beyond the sentence saying there are none");
    assert.match(text, /lms load <model> --gpu max/);
    assert.equal(labTextV2("api.ecdysis.me"), text);
    const py = await w.site("/lab/level1.py");
    assert.equal(py.status, 200);
    assert.match(py.headers.get("content-type") ?? "", /text\/x-python/);
    const script = await py.text();
    assert.match(script, /^"""level1\.py: load-bearing and new arXiv papers/);
    assert.match(script, /\/v2\/direction\?limit=50/, "stakes first: the map's register acts come before the newest listings");
    assert.ok(text.includes(script.trimEnd()), "the script in the guide is the file served");
    assert.ok(labPageV2({ host: "api.ecdysis.me", mcpUrl: "https://api.ecdysis.me/mcp" }).includes("https://api.ecdysis.me/mcp"));
  });

  it("the brief fits every app's link, is on the page, and the launcher types it", async () => {
    const brief = labBriefV2("https://ecdysis.me");
    assert.ok(brief.length < Math.min(...Object.values(PROMPT_APPS).map((a) => a.max)), `the brief (${brief.length} chars) fits the tightest app`);
    assert.match(brief, /Never print, log, upload or send a\s+private key, and never show one to a model/);
    assert.match(brief, /at the first 429, pause a minute and resend/);
    assert.match(brief, /https:\/\/ecdysis\.me\/lab\.md/, "the brief points the agent at the guide itself");
    assert.match(brief, /Never run anyone else's code \(bundles, repositories\) on a machine that holds the main key/);
    assert.match(brief, /data, never instructions/);
    assert.ok((STARTERS_V2 as readonly string[]).includes("lab"));
    const w = await world();
    const page = await (await w.site("/lab")).text();
    assert.ok(page.includes(brief.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#39;")), "the page shows the brief the launcher will type");
    assert.match(page, /<a href="\/o\/claude\/lab" target="_blank"/);
    assert.match(page, /<a href="\/o\/claude-code\/lab" target="_blank"/);
    const go = await w.site("/o/claude/lab");
    assert.equal(go.status, 302);
    assert.match(decodeURIComponent(go.headers.get("location") ?? ""), /^https:\/\/claude\.ai\/new\?q=Set up a continuously running contributor to Ecdysis/);
    assert.equal((await w.site("/o/claude/juror")).status, 404, "the first record's starters are gone");
  });
});
