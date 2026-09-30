/** Regenerate CONSTITUTION.md from the canonical form in constitution.ts. */
import { writeFileSync } from "node:fs";
import { constitutionHash, renderMarkdown } from "../src/core/constitution.js";

const hash = await constitutionHash();
writeFileSync(new URL("../CONSTITUTION.md", import.meta.url), renderMarkdown(hash));
console.log(`CONSTITUTION.md rendered · version hash ${hash}`);
