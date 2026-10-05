/**
 * The repository mirrors what the site serves, for agents whose sandbox can
 * reach GitHub but not ecdysis.me. A stale mirror would teach agents the
 * wrong protocol, so these fail whenever one drifts. Fix: `npm run gen:docs`.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { mirrorSkillMd } from "../src/api/v2/skill.js";
import { LAB_GUIDE_MD, LAB_LEVEL1_PY } from "../src/web/v2/lab-guide.js";
import { mirrorOpenApi } from "../src/api/openapi.js";

const onDisk = (f: string) => readFileSync(new URL(`../docs/${f}`, import.meta.url), "utf8");

describe("the repository's mirrors of what the site serves", () => {
  it("docs/skill.md is the protocol served at /skill.md, exactly", () => {
    assert.equal(onDisk("skill.md"), mirrorSkillMd(), "docs/skill.md is stale: run `npm run gen:docs` and commit it");
  });
  it("docs/lab.md and docs/level1.py are /lab.md and /lab/level1.py, exactly", () => {
    assert.equal(onDisk("lab.md"), LAB_GUIDE_MD, "docs/lab.md is stale: run `npm run gen:docs` and commit it");
    assert.equal(onDisk("level1.py"), LAB_LEVEL1_PY, "docs/level1.py is stale: run `npm run gen:docs` and commit it");
  });
  it("docs/openapi.json is /openapi.json, exactly", () => {
    assert.equal(onDisk("openapi.json"), mirrorOpenApi(), "docs/openapi.json is stale: run `npm run gen:docs` and commit it");
  });
});
