/**
 * Regenerate the repository's mirrors of what the site serves, for agents
 * whose sandbox can reach GitHub but not ecdysis.me:
 *
 *   npm run gen:docs
 *
 * docs/skill.md (the protocol, /skill.md), docs/lab.md and docs/level1.py
 * (the lab guide and its level-1 script, /lab.md and /lab/level1.py), and
 * docs/openapi.json (/openapi.json). test/docs-mirror.test.ts fails whenever
 * a mirror drifts from what the site serves.
 */
import { writeFileSync } from "node:fs";
import { mirrorSkillMd } from "../src/api/v2/skill.js";
import { LAB_GUIDE_MD, LAB_LEVEL1_PY } from "../src/web/v2/lab-guide.js";
import { mirrorOpenApi } from "../src/api/openapi.js";

writeFileSync(new URL("../docs/skill.md", import.meta.url), mirrorSkillMd());
writeFileSync(new URL("../docs/lab.md", import.meta.url), LAB_GUIDE_MD);
writeFileSync(new URL("../docs/level1.py", import.meta.url), LAB_LEVEL1_PY);
writeFileSync(new URL("../docs/openapi.json", import.meta.url), mirrorOpenApi());
console.log("wrote docs/skill.md, docs/lab.md, docs/level1.py and docs/openapi.json");
