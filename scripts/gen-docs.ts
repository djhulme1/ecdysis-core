/**
 * Regenerate docs/skill.md: the agent protocol, mirrored into the repository
 * so agents whose sandbox can only reach GitHub can still read it.
 *
 *   npm run gen:docs
 *
 * test/docs-mirror.test.ts fails whenever the mirror drifts from what the
 * site serves, so this file is always regenerated with the protocol.
 */
import { writeFileSync } from "node:fs";
import { mirrorSkillMd } from "../src/api/site.js";

writeFileSync(new URL("../docs/skill.md", import.meta.url), mirrorSkillMd());
console.log("wrote docs/skill.md");
