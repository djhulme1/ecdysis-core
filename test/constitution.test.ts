/**
 * The constitution as data. Version 2.1.0 is the text for the network of
 * claims (network/0.1), adopted at the record's genesis once the owner has
 * approved it; 2.0.0 is the text the first v2 record adopted on 3 October
 * 2026; 1.0.0 is the text the v1 record's agents acknowledged. Every hash is
 * pinned, so no edit to any text can pass unnoticed, and 2.1.0 is checked
 * against 2.0.0 article by article, so it can differ only where the network
 * needs it to.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import {
  ARTICLES, ARTICLES_2_0, ARTICLES_V1, CONSTITUTION_2_0_HASH, CONSTITUTION_2_0_VERSION, CONSTITUTION_HASH, CONSTITUTION_V1_HASH,
  CONSTITUTION_V1_VERSION, CONSTITUTION_VERSION, constitutionCanonical, constitutionHash, hashFor, renderMarkdown,
} from "../src/core/constitution.js";
import { V2_ARTICLES } from "../src/api/v2/governance.js";

const clauses = (articles: ReadonlyArray<{ text: string }>) => new Map(articles.flatMap((a) => a.text.split("\n")).map((t) => [t.split(" ")[0]!, t] as const));

describe("constitution v2.1.0, the network of claims", () => {
  it("is the version in force, and its hash is the one pinned for genesis", async () => {
    assert.equal(CONSTITUTION_VERSION, "2.1.0");
    assert.equal(await constitutionHash(), CONSTITUTION_HASH);
    assert.equal(await hashFor("2.1.0", ARTICLES), CONSTITUTION_HASH);
    assert.match(CONSTITUTION_HASH, /^[0-9a-f]{64}$/);
  });

  it("differs from 2.0.0 only in II.1, II.2, II.4 and IV.3; Article 0 is untouched", () => {
    const now = clauses(ARTICLES);
    const before = clauses(ARTICLES_2_0);
    assert.deepEqual([...now.keys()], [...before.keys()], "the same clauses, in the same order");
    const changed = [...now.keys()].filter((k) => now.get(k) !== before.get(k));
    assert.deepEqual(changed, ["II.1", "II.2", "II.4", "IV.3"]);
    assert.deepEqual(ARTICLES.map((a) => `${a.id}:${a.title}:${a.entrenched}`), ARTICLES_2_0.map((a) => `${a.id}:${a.title}:${a.entrenched}`));
    assert.equal(ARTICLES.find((a) => a.id === "0")!.text, ARTICLES_2_0.find((a) => a.id === "0")!.text, "the entrenched core is word for word the same");
  });

  it("says claims are the unit, with no papers and no vouching, and keeps no citation on faith", () => {
    const text = ARTICLES.map((a) => a.text).join("\n");
    assert.ok(text.includes("II.1 Claims are the unit of the record. Each is atomic and falsifiable, with a stated confidence and a stated test: the result that would refute it. Each carries its own rationale, method, data and caveats. There are no papers: a line of work is the claims that build on one another."));
    assert.ok(text.includes("II.2 Every claim declares the claims it extends, replicates, refutes or takes method from. No citation on faith: relying on a claim means reproducing or reviewing it, and saying which."));
    assert.ok(text.includes("IV.3 Independence weights every reward: same operator zero, operators that confirm each other's work half, independent full."));
    assert.ok(!/\bpapers?\b(?! here)/i.test(text.replace("There are no papers", "")), "no paper anywhere but where the text says there are none");
    assert.ok(!/vouch/i.test(text), "no vouching");
    assert.ok(!/jur(y|or)/i.test(text), "no juries");
    assert.ok(!/to confirm|\[edit|DRAFT/i.test(text));
  });

  it("Article V needs R2 by 0.6, which the governance module honours whatever the text's own flag says", () => {
    assert.deepEqual(ARTICLES.filter((a) => a.entrenched).map((a) => a.id), ["0"], "the text marks Article 0 alone as entrenched");
    assert.deepEqual(V2_ARTICLES.filter((a) => a.entrenched).map((a) => a.id), ["0", "V"]);
    assert.deepEqual(V2_ARTICLES.map((a) => a.id), ARTICLES.map((a) => a.id));
  });

  it("the canonical form names the version, and the rendering says how each version came to be", async () => {
    const c = constitutionCanonical() as { version: string; articles: unknown[] };
    assert.equal(c.version, "2.1.0");
    assert.equal(c.articles.length, 7);
    const md = renderMarkdown(await constitutionHash());
    assert.match(md, /Version 2\.1\.0 · canonical hash `9ecee158/);
    assert.match(md, /adopted at the genesis of the record under reserved power R2/);
    assert.match(md, new RegExp(`Version 2\\.0\\.0 \\(canonical hash\\n\`${CONSTITUTION_2_0_HASH}\``));
    assert.ok(md.includes(CONSTITUTION_V1_HASH));
  });
});

describe("earlier texts, kept as history", () => {
  it("2.0.0 hashes to what the first v2 record adopted at its genesis", async () => {
    assert.equal(CONSTITUTION_2_0_VERSION, "2.0.0");
    assert.equal(await hashFor(CONSTITUTION_2_0_VERSION, ARTICLES_2_0), CONSTITUTION_2_0_HASH);
    assert.equal(CONSTITUTION_2_0_HASH, "b8079a55f0039e38b6a6241a3172a54f8ac52c61141477e3017f08a8f76ab17f", "entry 0 of mirror/v2/entries.jsonl");
  });

  it("1.0.0 hashes to what the v1 record's agents acknowledged, and is a different text: juries in, receipts out", async () => {
    assert.equal(CONSTITUTION_V1_VERSION, "1.0.0");
    assert.equal(await hashFor(CONSTITUTION_V1_VERSION, ARTICLES_V1), CONSTITUTION_V1_HASH);
    assert.equal(CONSTITUTION_V1_HASH, "01bd924dffe698de91a6a342d04e5e010afbdd224cbe07f9314fec676521e81c");
    const v1 = ARTICLES_V1.map((a) => a.text).join("\n");
    assert.match(v1, /jury of agents/);
    assert.ok(!/receipt/.test(v1));
  });
});
