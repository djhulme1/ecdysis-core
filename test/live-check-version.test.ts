/**
 * The live check must expect the credence version the code serves, never one
 * written into the script by hand. On 4 October 2026 the core moved to
 * credence/0.4 while scripts/live-check.ts still asked production for
 * "credence/0.3", so a healthy deployment read as a failed probe.
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

test("the live check reads the credence version from the core, not from a literal", () => {
  const src = readFileSync(new URL("../scripts/live-check.ts", import.meta.url), "utf8");
  assert.match(src, /import \{ CREDENCE_V2_VERSION \} from "\.\.\/src\/core\/v2\/credence\.js";/);
  assert.match(src, /b\.version === CREDENCE_V2_VERSION/);
  // A full version literal (credence/0.<digit>) anywhere in the script would go stale at the next version.
  assert.deepEqual(src.match(/credence\/0\.\d/g) ?? [], []);
});
