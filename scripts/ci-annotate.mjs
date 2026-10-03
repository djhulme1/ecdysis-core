// Turns a failed test run's TAP output into GitHub check annotations, so a
// failure can be read from the pull request (and through the API) without
// opening the raw log. Nothing else: no summary, no retries, no network.
//
// Usage, in CI, after `npm test` has written TAP to a file:
//   node scripts/ci-annotate.mjs test.tap
//
// For each failing test, the test's name becomes the annotation's title and
// its YAML diagnostic block (the assertion message with the diff, expected
// and actual, the operator, the location) becomes the message; the stack
// and the timing are left out. A suite that fails only because a child did
// is not annotated again.
import { readFileSync } from "node:fs";

const file = process.argv[2];
if (!file) {
  console.error("usage: node scripts/ci-annotate.mjs <tap file>");
  process.exit(2);
}
const lines = readFileSync(file, "utf8").split(/\r?\n/);
const encode = (s) => s.replace(/%/g, "%25").replace(/\r/g, "%0D").replace(/\n/g, "%0A");
const DROP = new Set(["duration_ms", "type", "stack"]);
let failures = 0;
for (let i = 0; i < lines.length; i++) {
  const m = lines[i].match(/^\s*not ok \d+ - (.*)$/);
  if (!m) continue;
  const name = m[1].replace(/\s*#.*$/, "");
  const open = lines[i + 1] ?? "";
  if (!/^\s*---\s*$/.test(open)) { failures++; console.log(`::error title=${encode(`Test failed: ${name}`)}::(no diagnostics)`); continue; }
  const base = open.match(/^\s*/)[0].length;
  const kept = [];
  let subtestsOnly = false;
  let dropping = false;
  for (let j = i + 2; j < lines.length && !/^\s*\.\.\.\s*$/.test(lines[j]); j++) {
    const l = lines[j].slice(base);
    const key = l.match(/^([A-Za-z_]+):/);
    if (key) {
      dropping = DROP.has(key[1]);
      if (key[1] === "failureType" && /subtestsFailed/.test(l)) subtestsOnly = true;
    }
    if (!dropping) kept.push(l);
  }
  if (subtestsOnly) continue;
  failures++;
  const message = kept.join("\n").trim().slice(0, 3800) || "(no diagnostics)";
  console.log(`::error title=${encode(`Test failed: ${name}`)}::${encode(message)}`);
}
console.log(failures ? `${failures} failing test(s) annotated` : "no failing tests found in the TAP output");
