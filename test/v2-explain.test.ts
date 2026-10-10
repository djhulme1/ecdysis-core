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
import { claimTrace, homeTrace } from "../src/web/v2/viz.js";
import { landingPageV2, peoplePageV2, type HomeFinding, type LandingData } from "../src/web/v2/site.js";
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
const LANDING: LandingData = { host: "ecdysis.me", constitution: { version: "2.1.0", hash: "ab".repeat(32) }, logPublicKey: null, counts: { claims: 0, external: 0, receipts: 0, agents: 0 } };
/** A finding as the front page shows one, its words written to need escaping. */
const FINDING: HomeFinding = {
  id: "ext:0123456789abcdef", headline: "Prompting people to think about accuracy makes them share <b>better</b> news.", machineHeadline: true,
  status: "supported", credence: 0.78, where: "Misinformation", external: true, source: "doi:10.1038/s41586-021-03344-2", agent: "Imago",
  paper: { provider: "openalex", work: "W1", title: "Shifting attention to accuracy can reduce misinformation online", authors: ["Gordon Pennycook", "Ziv Epstein"], authorCount: 6, venue: "Nature", year: 2021, type: "article", citedBy: 900, keywords: [], topic: null } as unknown as HomeFinding["paper"],
  registered: "word for word from the paper, with the test that would prove it wrong",
  checked: "Two agents each re-ran the authors' analysis on the paper's own data and got the paper's results.",
  next: "a reproduction, meaning the same study with new data from the same population and period.",
};
const HOME: LandingData = {
  ...LANDING,
  figures: { findings: 1035, checked: 39, supported: 38, contested: 1, refuted: 0, checks: 40, checkers: 4 },
  featured: FINDING,
  topics: [{ name: "Psychology", about: "Social Psychology, Experimental and Cognitive Psychology", claims: 120 }, { name: "Computer Science", about: "Artificial Intelligence", claims: 300 }],
};

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
      assert.match(r.html, path === "/faq" ? /<a href="\/faq" aria-current="page">FAQ<\/a>/ : /<a href="\/people" aria-current="true">How it works<\/a>/, `${path} has its place in the top bar`);
      assert.doesNotMatch(mainOf(r.html), BANNED, `${path} keeps to the brief's words`);
    }
    assert.match((await get("/faq")).html, /<a href="\/faq" aria-current="page">FAQ<\/a>/, "the FAQ is in the top bar, marked as the current page");
    assert.match((await get("/compare")).html, /<nav class="sub" aria-label="In this section">[\s\S]*?<a href="\/compare" aria-current="page">How it compares<\/a>/, "the comparison is a tab under How it works, marked as the current page");
    const sitemap = (await get("/sitemap.xml")).html;
    assert.ok(V2_SITEMAP_PAGES.includes("/faq") && V2_SITEMAP_PAGES.includes("/compare"));
    assert.match(sitemap, /<loc>https:\/\/ecdysis\.me\/faq<\/loc>/);
    assert.match(sitemap, /<loc>https:\/\/ecdysis\.me\/compare<\/loc>/);
    const llms = llmsTxtV2("api.ecdysis.me");
    assert.match(llms, /\[FAQ\]\(https:\/\/ecdysis\.me\/faq\)/);
    assert.match(llms, /\[How Ecdysis compares\]\(https:\/\/ecdysis\.me\/compare\)/);
    assert.equal(pageKeyOf("GET", "/faq", "text/html"), "faq");
    assert.equal(pageKeyOf("GET", "/compare", "text/html"), "compare");
    assert.deepEqual(["/claims", "/claims/table", "/claims/all", "/network"].map((p) => pageKeyOf("GET", p, "text/html")), ["claims", "claims-table", "claims-table", "network"], "the list, the table and the network are counted apart");
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

  it("answers the objections to AI doing science in a section of their own, conceding what is right", async () => {
    const groups = faqGroups("https://api.ecdysis.me");
    const objections = groups.find((g) => g.id === "objections");
    assert.ok(objections, "the FAQ has an Objections section");
    assert.ok(groups.findIndex((g) => g.id === "objections") === groups.findIndex((g) => g.id === "trust") + 1, "it follows Trust and integrity");
    const ids = objections.items.map((i) => i.id);
    for (const id of ["slop", "too-fast", "errors", "remix", "fabrication", "accountable", "closed", "loop", "formal", "understanding", "power"]) {
      assert.ok(ids.includes(id), `${id} is answered there`);
    }
    assert.ok(!groups.find((g) => g.id === "trust")!.items.some((i) => i.id === "slop"), "the slop question moved, under the same anchor");
    const answers = objections.items.map((i) => i.a).join("\n");
    // Balanced: the answers say plainly where an objection is right and Ecdysis cannot help.
    for (const concession of [/It is the problem/, /a credence score isn't insight/, /Ecdysis can't change that/, /no archive can answer it alone/, /that's all we say it proves/]) {
      assert.match(answers, concession);
    }
    for (const i of objections.items) assert.ok(i.a.replace(/<[^>]+>/g, "").split(/\s+/).length <= 80, `${i.id} stays short`);
    const html = (await (await site())("/faq")).html;
    assert.match(html, /<nav class="jump" aria-label="On this page">.*<a href="#objections">Objections<\/a>/s, "the jump list reaches it");
    assert.match(html, /<h2 id="objections">Objections<\/h2>\n<div class="prose"><p>AI doing science draws hard questions, and many of them are fair\./);
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

describe("the front page (Lucy Griffiths' home page, 10 October 2026)", () => {
  it("says what Ecdysis is with one primary action, then a real finding, the film, the record now, one worked example, the method, topics, the argument, the ways to take part and the promise, without script or mock data", () => {
    const main = mainOf(landingPageV2(HOME));
    assert.match(main, /<p class="eyebrow">An open record of science, checked in public<\/p>\s*<h1>Science has outgrown its shell\.<\/h1>/);
    assert.match(main, /Ecdysis takes findings from published research and checks them in the open\./);
    assert.match(main, /<p class="actions"><a class="btn" href="\/claims">Explore the findings<\/a><a class="btn quiet" href="\/people">How it works<\/a><\/p>/, "one primary action, for people, and How it works beside it");
    assert.doesNotMatch(main, /class="door"/, "no three equal doors");
    const order = ['class="home-hero"', 'class="find-card"', 'id="film-h"', 'class="figures"', 'id="example"', 'id="how"', 'id="topics"', 'id="why"', 'id="take-part"', 'id="trust-h"'];
    for (let k = 1; k < order.length; k++) assert.ok(main.indexOf(order[k - 1]!) >= 0 && main.indexOf(order[k - 1]!) < main.indexOf(order[k]!), `${order[k - 1]} comes before ${order[k]}`);
    assert.equal(CONTRAST.length, 4, "the argument in four contrasts");
    assert.equal(main.match(/<tr><td>/g)?.length, CONTRAST.length, "one row each");
    assert.match(main, /<th scope="col">Usually<\/th><th scope="col" class="us">On Ecdysis<\/th>/);
    assert.match(main, /<a href="https:\/\/doi\.org\/10\.1126\/science\.aac4716">Open Science Collaboration, <cite>Science<\/cite>, 2015<\/a>/, "the case rests on a cited result");
    for (const href of ["/compare", "/faq#verify", "/constitution.md", "https://github.com/djhulme1/ecdysis-core", "/faq", "/me", "/connect", "/lab"]) assert.ok(main.includes(`href="${href}"`), href);
    assert.match(main, /<h3>Registered<\/h3>[^]*<h3>Checked<\/h3>[^]*<h3>Weighed<\/h3>/, "the method in three steps");
    assert.match(main, /Only independent evidence moves how sure the record is\. Votes, citations and prestige don('|&#39;)t/, "never reputations: an agent's track record does weigh its evidence");
    assert.match(main, /<h2 id="trust-h">Nothing on Ecdysis asks for your trust<\/h2>/);
    // Only what the code makes true (an independent review, 10 October 2026): the log's head is signed, credence and status
    // recompute from it, a person following findings gets a digest, and only the starter prompts make an agent ask first.
    assert.match(main, /Every entry goes into an append-only public log whose signed head would show any rewrite\. Every credence and status recomputes from that log, by rules anyone can read\./);
    assert.match(main, /Follow the findings you care about, and get a daily or weekly digest of where they stand and the new checks on them\./);
    assert.match(main, /Our starter prompts have it show you its work before it files anything, and its record is public and earned\./);
    const people = peoplePageV2({ host: "ecdysis.me", mcpUrl: "https://api.ecdysis.me/mcp" });
    for (const page of [landingPageV2(HOME), people]) {
      assert.doesNotMatch(page, /checks with you before it publishes|approve what it files|every number recomputes|Every number on every page|open record of machine science/i, "no promise the code does not keep");
    }
    assert.match(people, /The three prompts below have it show you its work before it files anything\./);
    assert.match(landingPageV2(HOME), /Ecdysis is an open record of science, checked in public\. Text is licensed CC BY 4\.0, and every credence and status can be recomputed from the public log\./, "the footer says what the front page says");
    assert.doesNotMatch(main, /<script|Illustrative|mock/i);
    assert.doesNotMatch(main, BANNED);
  });

  it("puts the live state of the record up front, and says where the figures come from", () => {
    const main = mainOf(landingPageV2(HOME));
    for (const [v, l] of [["1,035", "findings on the record"], ["39", "checked so far"], ["38", "supported by their checks"], ["1", "contested"]]) {
      assert.match(main, new RegExp(`<span class="v">${v}</span><span class="l">${l}</span>`), l);
    }
    assert.doesNotMatch(main, /refuted by their checks/, "no refuted figure while none is refuted");
    assert.doesNotMatch(main, /where checks disagree/, "contested also means one failed check, or a refuted foundation: the status's own word");
    assert.match(main, /40 checks have a result so far, from 4 agents\. Counted live from the public log, so anyone can recompute these figures\. <a href="\/faq#verify">Verify it yourself<\/a>/);
    assert.match(mainOf(landingPageV2({ ...HOME, figures: { ...HOME.figures!, checks: 1, checkers: 1 } })), /1 check has a result so far, from 1 agent\./);
    const refuted = mainOf(landingPageV2({ ...HOME, figures: { ...HOME.figures!, refuted: 2 } }));
    assert.match(refuted, /<span class="v">2<\/span><span class="l">refuted by their checks<\/span>/);
    const empty = mainOf(landingPageV2(LANDING));
    assert.match(empty, /<span class="v">0<\/span><span class="l">findings on the record<\/span>/);
    assert.match(empty, /No check has a result yet\./);
    assert.doesNotMatch(empty, /class="find-card"/, "no finding to show, no card");
    assert.doesNotMatch(empty, /id="topics"/, "and no topics before there are any");
  });

  it("shows one real finding beside the headline: its words escaped, its paper, its status and the story of its checks", () => {
    const main = mainOf(landingPageV2(HOME));
    const card = main.slice(main.indexOf('<aside class="find-card"'), main.indexOf("</aside>"));
    assert.match(card, /<p class="eyebrow" id="fc-h">A finding on the record<\/p>/);
    assert.match(card, /<span class="status part"[^>]*>Supported · 78%<\/span><span>Misinformation<\/span>/);
    assert.match(card, /<p class="ft"><a href="\/c\/ext:0123456789abcdef">Prompting people to think about accuracy makes them share &lt;b&gt;better&lt;\/b&gt; news\.<\/a><\/p>/);
    assert.match(card, /<p class="from">Pennycook et al\., <cite>Nature<\/cite>, 2021<\/p>/);
    assert.match(card, /<li><b>Registered<\/b> word for word from the paper, with the test that would prove it wrong<\/li>/);
    assert.match(card, /<li><b>Checked:<\/b> Two agents each re-ran the authors&#39; analysis on the paper&#39;s own data and got the paper&#39;s results\.<\/li>/);
    assert.match(card, /<li><b>Still to come:<\/b> a reproduction, meaning the same study with new data/);
    assert.match(card, /<a href="\/c\/ext:0123456789abcdef">Read the full story<\/a>/);
    assert.match(card, /The headline is machine-written from the paper/, "a machine-written headline says so");
    const unchecked = mainOf(landingPageV2({ ...HOME, featured: { ...FINDING, status: "unchecked", credence: 0.5, checked: null, machineHeadline: false, headline: "“A quoted sentence.”" } }));
    assert.match(unchecked, /<span class="status open"[^>]*>Unchecked<\/span>/, "no percentage on an unchecked claim");
    assert.match(unchecked, /<li><b>So far:<\/b> nobody has checked it on Ecdysis yet\.<\/li>/);
    assert.doesNotMatch(unchecked, /machine-written/);
  });

  it("keeps one worked example, scored by the rules, and moves the rest of the machinery to How it works", () => {
    const steps = homeTrace();
    assert.deepEqual(steps.map((s) => s.status), ["unchecked", "supported", "supported", "established", "contested"]);
    for (let k = 1; k < 4; k++) assert.ok(steps[k]!.credence > steps[k - 1]!.credence, `evidence at step ${k + 1} raises credence`);
    assert.ok(steps[2]!.credence < steps[2]!.bar && steps[3]!.credence >= steps[3]!.bar, "two independent checks with no record are not over the bar; a third is");
    assert.ok(steps[4]!.credence < steps[3]!.credence, "a failure lowers it");
    const home = landingPageV2(HOME);
    for (const s of steps) assert.ok(home.includes(`style="width:${(s.credence * 100).toFixed(1)}%"`), `the front page's gauge shows ${s.what}`);
    assert.match(home, /<a href="\/people#worked-example">See the full worked example, and how every number is computed<\/a>/);
    for (const gone of ["The anatomy of a receipt", 'id="claim"', 'id="status"', 'id="receipt"', 'id="attempts"']) assert.ok(!mainOf(home).includes(gone), `${gone} is on How it works now`);
    const people = peoplePageV2({ host: "ecdysis.me", mcpUrl: "https://api.ecdysis.me/mcp" });
    for (const id of ["worked-example", "claim", "status", "receipt", "standing", "attempts"]) assert.match(people, new RegExp(`<h2 id="${id}">`), `How it works has ${id}`);
    for (const s of claimTrace()) assert.ok(people.includes(`style="width:${(s.credence * 100).toFixed(1)}%"`), `the full example's gauge shows ${s.what}`);
  });

  it("draws the full worked example from the credence rules themselves", () => {
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
  });

  it("is right that a thousand copies count once", () => {
    const x = `ecd:${"1".repeat(16)}`;
    const claim: ClaimInput = { ref: x, authorOperator: "op-author", stated: 0.7, foundations: [], seq: 1 };
    const one: EvidenceInput = { id: "e0", claim: x, kind: "replication", confirms: true, agent: "copy-0", operatorId: "op-farm", tier: "verified", families: ["claude"], seq: 2 };
    const many = Array.from({ length: 1000 }, (_, k): EvidenceInput => ({ ...one, id: `e${k}`, agent: `copy-${k}`, seq: 2 + k }));
    assert.equal(computeCredenceV2([claim], many, []).get(x)!.credence, computeCredenceV2([claim], [one], []).get(x)!.credence);
  });
});
