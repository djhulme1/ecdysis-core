/**
 * docs/skill.md mirrors the agent protocol on GitHub, where blocked
 * sandboxes can still read it. A stale mirror would teach agents the wrong
 * protocol, so this fails whenever it drifts. Fix: `npm run gen:docs`.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { mirrorSkillMd } from "../src/api/site.js";

describe("protocol mirror", () => {
  it("docs/skill.md matches the served protocol exactly", () => {
    const onDisk = readFileSync(new URL("../docs/skill.md", import.meta.url), "utf8");
    assert.equal(onDisk, mirrorSkillMd(), "docs/skill.md is stale: run `npm run gen:docs` and commit it");
  });
});

describe("v2 protocol mirror", () => {
  it("docs/v2/skill.md matches the served v2 protocol exactly", async () => {
    const { mirrorSkillMdV2 } = await import("../src/api/v2/skill.js");
    const onDisk = readFileSync(new URL("../docs/v2/skill.md", import.meta.url), "utf8");
    assert.equal(onDisk, mirrorSkillMdV2(), "docs/v2/skill.md is stale: run `npm run gen:docs` and commit it");
  });
});

describe("the lab guide's mirror", () => {
  it("docs/v2/idle-compute.md and docs/v2/level1.py match what the site serves at /lab.md and /lab/level1.py", async () => {
    const { LAB_GUIDE_MD, LAB_LEVEL1_PY } = await import("../src/web/v2/lab-guide.js");
    assert.equal(readFileSync(new URL("../docs/v2/idle-compute.md", import.meta.url), "utf8"), LAB_GUIDE_MD, "docs/v2/idle-compute.md is stale: run `npm run gen:docs` and commit it");
    assert.equal(readFileSync(new URL("../docs/v2/level1.py", import.meta.url), "utf8"), LAB_LEVEL1_PY, "docs/v2/level1.py is stale: run `npm run gen:docs` and commit it");
  });
});
