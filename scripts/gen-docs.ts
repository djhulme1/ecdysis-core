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
import { mirrorSkillMdV2 } from "../src/api/v2/skill.js";

writeFileSync(new URL("../docs/skill.md", import.meta.url), mirrorSkillMd());
writeFileSync(new URL("../docs/v2/skill.md", import.meta.url), mirrorSkillMdV2());
console.log("wrote docs/skill.md and docs/v2/skill.md");
