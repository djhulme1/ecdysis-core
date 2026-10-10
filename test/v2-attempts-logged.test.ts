/**
 * "Make it explicit everywhere, including the front page, that even attempts are logged, and even attempts can help build a
 * map of pressure" (Daniel, 5 October 2026). Every page, guide and tool a person or an agent starts from says so, in the
 * words of one constant (attempts.ts, ATTEMPTS_LOGGED), so they cannot drift apart.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { ATTEMPTS_LOGGED, ATTEMPTS_LOGGED_SHORT } from "../src/core/v2/attempts.js";
import { agentsPageV2, landingPageV2, peoplePageV2 } from "../src/web/v2/site.js";
import { comparePageV2, faqPageV2 } from "../src/web/v2/explain.js";
import { llmsTxtV2, skillMdV2 } from "../src/api/v2/skill.js";
import { LAB_BRIEF, LAB_GUIDE_MD } from "../src/web/v2/lab-guide.js";
import { mapPageV2 } from "../src/web/v2/map.js";
import { buildMap } from "../src/core/v2/map.js";
import { attemptsSection, claimsPageV2 } from "../src/web/v2/pages.js";
import { peoplePromptsV2 } from "../src/web/starters.js";
import { openApiDocument } from "../src/api/openapi.js";
import { v2Tools } from "../src/api/v2/tools.js";
import type { V2Service } from "../src/api/v2/service.js";

const LOGGED = /even an attempt is logged/i;
const PRESSURE = /map of pressure/i;
/** The page's text with tags removed and entities for quotes and apostrophes restored: what a reader sees. */
const text = (html: string) => html.replace(/<[^>]+>/g, " ").replace(/&#39;|&#x27;/g, "'").replace(/&quot;/g, '"').replace(/&amp;/g, "&").replace(/\s+/g, " ");

describe("even an attempt is logged, and attempts build the map of pressure: said everywhere", () => {
  it("the sentence itself is true to the rules: logged, never refused, and building the map", () => {
    assert.match(ATTEMPTS_LOGGED, LOGGED);
    assert.match(ATTEMPTS_LOGGED, PRESSURE);
    assert.match(ATTEMPTS_LOGGED_SHORT, LOGGED);
    assert.match(ATTEMPTS_LOGGED_SHORT, PRESSURE);
    assert.match(ATTEMPTS_LOGGED, /authors/, "it says whom the pressure falls on");
  });

  it("on the front page, in how a finding is checked, and in its own section on How it works", () => {
    const html = landingPageV2({ host: "ecdysis.me", constitution: { version: "2.1.0", hash: "0".repeat(64) }, logPublicKey: null, counts: { claims: 0, external: 0, receipts: 0, agents: 0 } });
    const t = text(html);
    assert.match(t, LOGGED);
    assert.match(t, PRESSURE);
    assert.match(html, /href="\/leaderboard"/, "and the leaderboard is linked from the front page");
    const people = peoplePageV2({ host: "ecdysis.me", mcpUrl: "https://api.ecdysis.me/mcp" });
    assert.ok(text(people).includes(ATTEMPTS_LOGGED), "the whole sentence, in its own section");
    assert.match(people, /<h2 id="attempts">Nothing tried is wasted<\/h2>/);
  });

  it("on the people and agents pages, the FAQ and the comparison", () => {
    for (const [name, html] of [
      ["people", peoplePageV2({ host: "ecdysis.me", mcpUrl: "https://api.ecdysis.me/mcp" })],
      ["agents", agentsPageV2({ host: "api.ecdysis.me", mcpUrl: "https://api.ecdysis.me/mcp" })],
      ["faq", faqPageV2({ host: "api.ecdysis.me" })],
      ["compare", comparePageV2({ host: "api.ecdysis.me" })],
    ] as const) {
      assert.match(text(html), LOGGED, name);
      assert.match(text(html), PRESSURE, name);
    }
  });

  it("on the map, the claims page and every claim's attempts section", () => {
    const map = mapPageV2(buildMap([], [], new Map(), new Map(), 10));
    assert.match(text(map), LOGGED);
    const claims = claimsPageV2({ claims: [], all: false, unlisted: 0, graph: { nodes: [], edges: [], omitted: 0 }, totals: { claims: 0, external: 0, edges: 0, maxGen: 0, deepUnchecked: 0 } });
    assert.match(text(claims), /The map/);
    assert.match(text(attemptsSection("ext:0123456789abcdef", "empirical", null, [])), LOGGED);
  });

  it("in the protocol, llms.txt, the lab guide and brief, and the prompts people hand their AI", () => {
    const skill = skillMdV2("api.ecdysis.me");
    assert.match(skill, LOGGED);
    assert.match(skill, PRESSURE);
    assert.ok(skill.indexOf(ATTEMPTS_LOGGED) < skill.indexOf("## Reading needs no keys"), "it is said in the opening section, not only in the attempts section");
    assert.match(llmsTxtV2("api.ecdysis.me"), LOGGED);
    assert.match(LAB_GUIDE_MD, LOGGED);
    assert.match(LAB_BRIEF, LOGGED);
    assert.ok(LAB_BRIEF.length < 5000, "the brief still fits every app's link");
    const prompts = new Map(peoplePromptsV2("https://ecdysis.me").map((p) => [p.id, p.text] as const));
    assert.match(prompts.get("famous")!, LOGGED);
    assert.match(prompts.get("famous")!, PRESSURE);
    assert.match(prompts.get("field")!, LOGGED);
  });

  it("in the connector's tools and the API description", () => {
    const tools = new Map(v2Tools({} as unknown as V2Service).map((t) => [t.name, t.description] as const));
    assert.match(tools.get("file_attempt")!, LOGGED);
    assert.match(tools.get("get_map")!, LOGGED);
    assert.match(tools.get("get_map")!, PRESSURE);
    const doc = openApiDocument({ api: "https://api.ecdysis.me", site: "https://ecdysis.me" }) as { paths: Record<string, Record<string, { description?: string }>> };
    assert.match(doc.paths["/v2/attempts"]!["post"]!.description ?? "", LOGGED);
  });

  it("in the repository's README, the quickstart and the mirrored protocol", () => {
    for (const f of ["README.md", "docs/QUICKSTART.md", "docs/skill.md"]) {
      const s = readFileSync(new URL(`../${f}`, import.meta.url), "utf8").replace(/\s+/g, " ").replace(/^> /gm, "");
      assert.match(s.replace(/ > /g, " "), LOGGED, f);
    }
  });
});
