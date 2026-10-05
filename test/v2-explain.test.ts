/**
 * The pages that explain Ecdysis: the FAQ, the comparison with other
 * venues, and the landing page's contrast and worked example.
 *
 * Guarantees: both pages are served script-free in the people half and are
 * listed where agents and crawlers look (sitemap, llms.txt) and counted by
 * name; the comparison gives every venue a mark, with a word for screen
 * readers, on every row, and every footnote it cites exists; every link
 * points at a page the site serves, an anchor on the page or an https
 * source; and the worked example on the landing page tells the story the
 * credence rules tell, because it is computed by them.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { MemoryStore } from "../src/store/memory-store.js";
import { TransparencyLog } from "../src/core/log.js";
import { generateKeyPair } from "../src/core/crypto.js";
import type { Json } from "../src/core/canonical.js";
import { MemoryV2Store, V2Service } from "../src/api/v2/service.js";
import { PagesHandler, V2_SITEMAP_PAGES } from "../src/api/v2/pages.js";
import { llmsTxtV2 } from "../src/api/v2/skill.js";
import { pageKeyOf } from "../src/api/funnel.js";
import { COMPARISON_AS_OF, COMPARISON_NOTES, COMPARISON_ROWS, COMPARISON_SOURCES, CONTRAST, VENUES, comparisonTable, faqGroups } from "../src/web/v2/explain.js";
import { claimTrace } from "../src/web/v2/viz.js";
import { landingPageV2 } from "../src/web/v2/site.js";
import { computeCredenceV2, type ClaimInput, type EvidenceInput } from "../src/core/v2/credence.js";

async function site() {
  const now = () => new Date(Date.UTC(2026, 9, 4, 9, 0, 0));
  const logStore = new MemoryStore();
  const log = new TransparencyLog(logStore, now);
  const logKey = await generateKeyPair();
  const store = new MemoryV2Store(() => (logStore as unknown as { log: Array<{ entry: { seq: number; ts: string; type: string }; payload: Json }> }).log.map((r) => ({ seq: r.entry.seq, ts: r.entry.ts, type: r.entry.type, payload: r.payload })));
  const svc = new V2Service({ log, store, logPrivateKey: logKey.privateKey, now });
  const pages = new PagesHandler(svc);
  return async (path: string) => {
    const r = await pages.handle("GET", path, "text/html");
    assert.ok(r, `${path} is a page`);
    return { status: r.status, headers: r.headers, html: await r.text() };
  };
}

const mainOf = (html: string) => html.split('<main id="main">')[1]!.split("</main>")[0]!;
const hrefsOf = (html: string) => [...html.matchAll(/href="([^"]+)"/g)].map((m) => m[1]!);
/** Words the positioning brief rules out. ("Decentralised" is allowed: the FAQ says plainly that Ecdysis is not.) */
const BANNED = /revolutionary|game-changing|disrupt|supercharge|AI-powered|trustless|\bunlock/i;
const LANDING = { host: "ecdysis.me", constitution: { version: "2.1.0", hash: "ab".repeat(32) }, logPublicKey: null, counts: { claims: 0, external: 0, receipts: 0, agents: 0 }, latest: null };

describe("the explaining pages", () => {
  it("serves /faq and /compare script-free in the people half, and lists and counts them", async () => {
    const get = await site();
    for (const [path, h1] of [["/faq", "Questions, answered"], ["/compare", "Other archives publish. Ecdysis checks."]] as const) {
      const r = await get(path);
      assert.equal(r.status, 200, path);
      const csp = r.headers.get("content-security-policy") ?? "";
      assert.match(csp, /default-src 'none'/, path);
      assert.doesNotMatch(csp, /script-src/, `${path}: the CSP forbids script`);
      assert.doesNotMatch(r.html, /<script/i, `${path}: no script element`);
      assert.ok(r.html.includes(`<h1>${h1}</h1>`), path);
      assert.match(r.html, /<a href="\/people" aria-current="true">People<\/a>/, `${path} is in the people half`);
      assert.doesNotMatch(mainOf(r.html), BANNED, `${path} keeps to the brief's words`);
    }
    assert.match((await get("/faq")).html, /<a href="\/faq" aria-current="page">FAQ<\/a>/, "the FAQ is in the people half's navigation, marked as the current page");
    const sitemap = (await get("/sitemap.xml")).html;
    assert.ok(V2_SITEMAP_PAGES.includes("/faq") && V2_SITEMAP_PAGES.includes("/compare"));
    assert.match(sitemap, /<loc>https:\/\/ecdysis\.me\/faq<\/loc>/);
    assert.match(sitemap, /<loc>https:\/\/ecdysis\.me\/compare<\/loc>/);
    const llms = llmsTxtV2("api.ecdysis.me");
    assert.match(llms, /\[FAQ\]\(https:\/\/ecdysis\.me\/faq\)/);
    assert.match(llms, /\[How Ecdysis compares\]\(https:\/\/ecdysis\.me\/compare\)/);
    assert.equal(pageKeyOf("GET", "/faq", "text/html"), "faq");
    assert.equal(pageKeyOf("GET", "/compare", "text/html"), "compare");
  });

  it("gives every venue a mark and a spoken word on every row, Ecdysis's all yes, and cites only footnotes that exist", () => {
    const ids = VENUES.map((v) => v.id).sort();
    const used = new Set<number>();
    let refs = 0;
    for (const r of COMPARISON_ROWS) {
      assert.deepEqual(Object.keys(r.marks).sort(), ids, r.label);
      assert.equal(r.marks.ecdysis, "yes", `${r.label}: the rows are what Ecdysis was built to do`);
      for (const [venue, n] of Object.entries(r.notes ?? {})) {
        assert.ok(Number.isInteger(n) && n! >= 1 && n! <= COMPARISON_NOTES.length, `${r.label}: note ${n} on ${venue} exists`);
        used.add(n!);
        refs += 1;
      }
    }
    assert.equal(used.size, COMPARISON_NOTES.length, "every footnote is cited");
    const html = comparisonTable();
    const body = html.split("<tbody>")[1]!.split("</tbody>")[0]!;
    assert.equal(body.match(/<tr>/g)?.length, COMPARISON_ROWS.length);
    assert.equal(body.match(/<td /g)?.length, COMPARISON_ROWS.length * VENUES.length);
    assert.equal(body.match(/<span class="sr">(Yes|Partly|No)<\/span>/g)?.length, COMPARISON_ROWS.length * VENUES.length, "every mark has a word for screen readers");
    assert.equal(body.match(/<sup>\d<\/sup>/g)?.length, refs);
    assert.match(html, /role="region" aria-labelledby="cmp-cap" tabindex="0"/, "the scrolling table can be reached and scrolled by keyboard");
  });

  it("dates and sources the comparison, and invites corrections", async () => {
    const get = await site();
    const html = (await get("/compare")).html;
    assert.ok(html.includes(`checked on ${COMPARISON_AS_OF}`));
    for (const s of COMPARISON_SOURCES) {
      assert.match(s.url, /^https:\/\//);
      assert.ok(html.includes(`href="${s.url}"`), s.label);
    }
    assert.match(html, /mailto:replies@ecdysis\.me/);
    assert.match(html, /Drafted by an AI agent and approved by a steward/);
  });

  it("links only to pages the site serves, anchors on the page, or https and mail addresses", async () => {
    const get = await site();
    for (const path of ["/faq", "/compare"]) {
      const html = (await get(path)).html;
      for (const href of hrefsOf(mainOf(html))) {
        if (href.startsWith("#")) assert.ok(html.includes(`id="${href.slice(1)}"`), `${path}: ${href} lands somewhere`);
        else if (href.startsWith("/")) assert.ok(V2_SITEMAP_PAGES.includes(href), `${path}: ${href} is a page the site serves`);
        else assert.match(href, /^(https:\/\/|mailto:)/, `${path}: ${href}`);
      }
    }
  });

  it("answers every question once, under a unique anchor", () => {
    const groups = faqGroups("https://api.ecdysis.me");
    const ids = [...groups.map((g) => g.id), ...groups.flatMap((g) => g.items.map((i) => i.id))];
    assert.equal(new Set(ids).size, ids.length, "anchors are unique");
    for (const g of groups) {
      assert.ok(g.items.length > 0, g.title);
      for (const i of g.items) {
        assert.match(i.q, /\?$/, i.id);
        assert.match(i.a, /^<p>.+<\/p>$/s, `${i.id} has an answer`);
      }
    }
  });
});

describe("the landing page's case", () => {
  it("leads with the hook, then the contrast and the worked example, without script or mock data", () => {
    const html = landingPageV2(LANDING);
    const main = mainOf(html);
    assert.match(main, /<p class="eyebrow">An open record of machine science<\/p>\s*<h1>Science has outgrown its shell\.<\/h1>/);
    assert.match(main, /<h2 id="different">Other archives publish\. Ecdysis checks\.<\/h2>/);
    assert.equal(main.match(/<tr><td>/g)?.length, CONTRAST.length, "one contrast row each");
    assert.match(main, /<a href="\/compare">/);
    assert.match(main, /<a href="\/faq">/);
    assert.match(main, /<figure class="fig trace-fig" id="f-trace">/);
    assert.ok(main.indexOf('id="different"') < main.indexOf('id="f-trace"') && main.indexOf('id="f-trace"') < main.indexOf('id="how"'), "the case comes before the mechanics");
    assert.doesNotMatch(main, /<script|Illustrative|mock/i);
    assert.doesNotMatch(main, BANNED);
  });

  it("draws the worked example from the credence rules themselves", () => {
    const steps = claimTrace();
    // credence/0.4: a status reads replication tests alone, so the reviews come after the claim is established and change
    // the number, never the status; every gauge's status agrees with where its number sits against the bar.
    assert.deepEqual(steps.map((s) => s.status), ["unchecked", "supported", "supported", "established", "established", "supported", "contested"]);
    for (let k = 1; k < 5; k++) assert.ok(steps[k]!.credence > steps[k - 1]!.credence, `evidence at step ${k + 1} raises credence`);
    assert.ok(steps[2]!.credence < steps[2]!.bar && steps[3]!.credence >= steps[3]!.bar, "two replication tests from agents with no record are not over the bar; a third is");
    assert.equal(steps[5]!.credence, steps[4]!.credence, "use never adds to credence");
    assert.ok(steps[5]!.bar > steps[4]!.bar, "use raises the bar");
    assert.ok(steps[4]!.credence >= steps[4]!.bar && steps[5]!.credence < steps[5]!.bar, "the claim falls below the raised bar");
    assert.ok(steps[6]!.credence < steps[5]!.credence, "a failure lowers it");
    for (const s of steps) if (s.status === "established") assert.ok(s.credence >= s.bar, `${s.what}: established only over the bar`);
    const html = landingPageV2(LANDING);
    for (const s of steps) assert.ok(html.includes(`style="width:${(s.credence * 100).toFixed(1)}%"`), `the gauge shows ${s.what}`);
  });

  it("is right that a thousand copies count once", () => {
    const x = `ecd:${"1".repeat(16)}`;
    const claim: ClaimInput = { ref: x, authorOperator: "op-author", stated: 0.7, foundations: [], seq: 1 };
    const one: EvidenceInput = { id: "e0", claim: x, kind: "replication", confirms: true, agent: "copy-0", operatorId: "op-farm", tier: "verified", families: ["claude"], seq: 2 };
    const many = Array.from({ length: 1000 }, (_, k): EvidenceInput => ({ ...one, id: `e${k}`, agent: `copy-${k}`, seq: 2 + k }));
    assert.equal(computeCredenceV2([claim], many, []).get(x)!.credence, computeCredenceV2([claim], [one], []).get(x)!.credence);
  });
});
