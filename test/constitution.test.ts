/**
 * The constitution as data: version 2.0.0 is the text the owner approved on
 * 3 October 2026 and is adopted at v2's genesis; version 1.0.0 is the text
 * the live v1 record's agents acknowledged. Both hashes are pinned, so no
 * edit to either text can pass unnoticed.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import {
  ARTICLES, ARTICLES_V1, CONSTITUTION_V1_HASH, CONSTITUTION_V1_VERSION, CONSTITUTION_V2_HASH, CONSTITUTION_VERSION,
  constitutionCanonical, constitutionHash, hashFor, renderMarkdown,
} from "../src/core/constitution.js";
import { V2_ARTICLES } from "../src/api/v2/governance.js";

describe("constitution v2.0.0", () => {
  it("is the version in force, and its hash is the one pinned for genesis", async () => {
    assert.equal(CONSTITUTION_VERSION, "2.0.0");
    assert.equal(await constitutionHash(), CONSTITUTION_V2_HASH);
    assert.equal(await hashFor("2.0.0", ARTICLES), CONSTITUTION_V2_HASH);
    assert.match(CONSTITUTION_V2_HASH, /^[0-9a-f]{64}$/);
  });

  it("carries the three approved edits verbatim, and nothing left to confirm", () => {
    const text = ARTICLES.map((a) => a.text).join("\n");
    assert.ok(text.includes("I.4 A key the archive holds on a person's behalf is marked as such on every entry it signs, and the person may destroy it at any time."));
    assert.ok(text.includes("III.3 Every reproduction also re-runs an earlier reproduction of the same claim, chosen at random by the archive. A disagreement opens a finding, decided by further independent runs; a finding of fabrication stands only against a bundle shown to be deterministic, after an appeal period, and voids every contribution of the operator responsible until a later finding reverses it."));
    assert.ok(text.includes("VI.3 Whatever declares reliance on a claim is flagged when that claim is refuted."));
    assert.ok(!/to confirm|\[edit|DRAFT/i.test(text));
    // No juries anywhere in the text that governs v2.
    assert.ok(!/jur(y|or)/i.test(text), "v2 has no juries");
    assert.deepEqual(ARTICLES.map((a) => `${a.id}:${a.title}`), ["0:Entrenched core", "I:Identity and assent", "II:Claims and evidence", "III:Evidence", "IV:Standing", "V:Amendment", "VI:Safety"]);
    assert.deepEqual(ARTICLES.filter((a) => a.entrenched).map((a) => a.id), ["0"], "the approved text marks Article 0 alone as entrenched");
  });

  it("Article V needs R2 by 0.6, which the governance module honours whatever the text's own flag says", () => {
    assert.deepEqual(V2_ARTICLES.filter((a) => a.entrenched).map((a) => a.id), ["0", "V"]);
    assert.deepEqual(V2_ARTICLES.map((a) => a.id), ARTICLES.map((a) => a.id));
  });

  it("the canonical form names the version, and the rendering says how each version came to be", async () => {
    const c = constitutionCanonical() as { version: string; articles: unknown[] };
    assert.equal(c.version, "2.0.0");
    assert.equal(c.articles.length, 7);
    const md = renderMarkdown(await constitutionHash());
    assert.match(md, /Version 2\.0\.0 · canonical hash `b8079a55/);
    assert.match(md, /adopted at the genesis of the v2 record under reserved power R2/);
    assert.match(md, new RegExp(`Version 1\\.0\\.0 \\(canonical hash\\n\`${CONSTITUTION_V1_HASH}\``));
  });
});

describe("constitution v1.0.0, kept as history", () => {
  it("hashes to what the live v1 record's agents acknowledged", async () => {
    assert.equal(CONSTITUTION_V1_VERSION, "1.0.0");
    assert.equal(await hashFor(CONSTITUTION_V1_VERSION, ARTICLES_V1), CONSTITUTION_V1_HASH);
    assert.equal(CONSTITUTION_V1_HASH, "01bd924dffe698de91a6a342d04e5e010afbdd224cbe07f9314fec676521e81c");
  });

  it("is a different text: juries in, receipts out", () => {
    const v1 = ARTICLES_V1.map((a) => a.text).join("\n");
    assert.match(v1, /jury of agents/);
    assert.ok(!/receipt/.test(v1));
    assert.notEqual(ARTICLES_V1.find((a) => a.id === "III")!.title, ARTICLES.find((a) => a.id === "III")!.title);
  });
});
