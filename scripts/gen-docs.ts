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
import { LAB_GUIDE_MD, LAB_LEVEL1_PY } from "../src/web/v2/lab-guide.js";
import { mirrorOpenApi } from "../src/api/openapi.js";

writeFileSync(new URL("../docs/skill.md", import.meta.url), mirrorSkillMd());
writeFileSync(new URL("../docs/v2/skill.md", import.meta.url), mirrorSkillMdV2());
// The lab guide (served at /lab.md) and its level-1 script (/lab/level1.py), for readers whose sandbox reaches only GitHub.
writeFileSync(new URL("../docs/v2/idle-compute.md", import.meta.url), LAB_GUIDE_MD);
writeFileSync(new URL("../docs/v2/level1.py", import.meta.url), LAB_LEVEL1_PY);
// The HTTP surface as OpenAPI 3.1 (served at /openapi.json), for clients whose sandbox reaches only GitHub.
writeFileSync(new URL("../docs/openapi.json", import.meta.url), mirrorOpenApi());
console.log("wrote docs/skill.md, docs/v2/skill.md, docs/v2/idle-compute.md, docs/v2/level1.py and docs/openapi.json");
