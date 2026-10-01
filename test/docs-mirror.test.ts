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
