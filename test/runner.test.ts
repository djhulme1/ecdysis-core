/**
 * The reference runner, end to end on a local repository: it fetches the
 * exact commit and refuses any other, runs the command with ECDYSIS_SEED as
 * the whole environment, reads results/outputs.json, and compares outputs
 * within the bundle's tolerances. Container isolation itself is not
 * exercised here (no docker in CI); the --no-container path is.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { mkdtempSync, writeFileSync, mkdirSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const RUNNER = join(process.cwd(), "scripts", "runner", "ecdysis-run.mjs");
const sh = (cmd: string, args: string[], cwd?: string) => spawnSync(cmd, args, { encoding: "utf8", cwd, env: { ...process.env, GIT_AUTHOR_NAME: "t", GIT_AUTHOR_EMAIL: "t@example.org", GIT_COMMITTER_NAME: "t", GIT_COMMITTER_EMAIL: "t@example.org" } });
const hasGit = sh("git", ["--version"]).status === 0;

function repo(): { url: string; commit: string; dir: string } {
  const dir = mkdtempSync(join(tmpdir(), "ecdysis-bundle-"));
  writeFileSync(join(dir, "run.sh"), `#!/bin/sh
set -e
mkdir -p results
head=$(printf %s "$ECDYSIS_SEED" | cut -c1-4)
# The environment is the seed and nothing else: prove it by counting variables other than the expected ones.
extra=$(env | grep -v -E '^(ECDYSIS_SEED|PATH|HOME|LANG|PWD|SHLVL|_|OLDPWD)=' | wc -l | tr -d ' ')
printf '{"alpha": 1.5, "seedhead": "%s", "extra_env": %s}\\n' "$head" "$extra" > results/outputs.json
`);
  sh("git", ["init", "-q", "-b", "main"], dir);
  sh("git", ["add", "."], dir);
  sh("git", ["commit", "-q", "-m", "bundle"], dir);
  const commit = sh("git", ["rev-parse", "HEAD"], dir).stdout.trim();
  return { url: `file://${dir}`, commit, dir };
}

function runner(args: string[]) {
  const r = spawnSync("node", [RUNNER, ...args], { encoding: "utf8" });
  return { status: r.status, out: r.stdout, err: r.stderr };
}

describe("the reference runner", { skip: !hasGit && "git is not available" }, () => {
  it("runs a bundle at its exact commit with the seed as the whole environment, and compares outputs within tolerances", () => {
    const { url, commit, dir } = repo();
    const work = mkdtempSync(join(tmpdir(), "ecdysis-runner-"));
    try {
      const bundle = { repo: url, commit, run: "sh run.sh", outputs: [{ name: "alpha", tolerance: 0.1 }, { name: "seedhead" }, { name: "extra_env" }], runtimeMinutes: 1 };
      const bpath = join(work, "bundle.json");
      writeFileSync(bpath, JSON.stringify(bundle));
      const seedA = "a".repeat(64);
      const seedB = "b".repeat(64);
      const first = runner(["--bundle", bpath, "--seed", seedA, "--no-container", "--allow-file-repo", "--out", join(work, "a.json")]);
      assert.equal(first.status, 0, first.err);
      const a = JSON.parse(first.out) as Record<string, unknown>;
      assert.equal(a["seedhead"], "aaaa", "the seed reached the run");
      assert.equal(a["extra_env"], 0, "nothing else did");
      // The same seed again: identical; compared, a match.
      const again = runner(["--bundle", bpath, "--seed", seedA, "--no-container", "--allow-file-repo", "--compare", join(work, "a.json")]);
      assert.equal(again.status, 0, again.err);
      assert.match(again.err, /match within tolerances/);
      // A different seed changes seedhead (exact output): the comparison differs, exit 2.
      const other = runner(["--bundle", bpath, "--seed", seedB, "--no-container", "--allow-file-repo", "--compare", join(work, "a.json")]);
      assert.equal(other.status, 2, other.err);
      assert.match(other.err, /DIFFER within tolerances on: seedhead/);
      // Refusals: a wrong commit, a bad seed, no image and no --no-container.
      const wrong = { ...bundle, commit: "0".repeat(40) };
      writeFileSync(join(work, "wrong.json"), JSON.stringify(wrong));
      const w = runner(["--bundle", join(work, "wrong.json"), "--seed", seedA, "--no-container", "--allow-file-repo"]);
      assert.notEqual(w.status, 0);
      assert.equal(runner(["--bundle", bpath, "--seed", "nothex", "--no-container", "--allow-file-repo"]).status, 3);
      const host = runner(["--bundle", bpath, "--seed", seedA, "--allow-file-repo"]);
      assert.equal(host.status, 3, "foreign code never runs on the host unless told to");
      assert.match(host.err, /--no-container/);
      // Without --allow-file-repo a file: repository is refused: real bundles are https.
      assert.equal(runner(["--bundle", bpath, "--seed", seedA, "--no-container"]).status, 3);
    } finally {
      rmSync(work, { recursive: true, force: true });
      rmSync(dir, { recursive: true, force: true });
    }
  });

  it("refuses an outputs file that is not an ordinary file: a bundle cannot make the runner read the host's files", () => {
    // The bundle plants results/outputs.json as a symlink to a file on the host. Read, it would be reported to the archive as the
    // run's outputs; the runner reads results on the host, so it checks the file itself, not its contents, first.
    const dir = mkdtempSync(join(tmpdir(), "ecdysis-bundle-"));
    const work = mkdtempSync(join(tmpdir(), "ecdysis-runner-"));
    try {
      const secret = join(work, "secret.json");
      writeFileSync(secret, JSON.stringify({ alpha: 1.5, token: "the host's secret" }));
      writeFileSync(join(dir, "run.sh"), `#!/bin/sh\nset -e\nmkdir -p results\nln -s ${secret} results/outputs.json\n`);
      sh("git", ["init", "-q", "-b", "main"], dir);
      sh("git", ["add", "."], dir);
      sh("git", ["commit", "-q", "-m", "bundle"], dir);
      const commit = sh("git", ["rev-parse", "HEAD"], dir).stdout.trim();
      const bpath = join(work, "bundle.json");
      writeFileSync(bpath, JSON.stringify({ repo: `file://${dir}`, commit, run: "sh run.sh", outputs: [{ name: "alpha" }], runtimeMinutes: 1 }));
      const r = runner(["--bundle", bpath, "--seed", "a".repeat(64), "--no-container", "--allow-file-repo"]);
      assert.equal(r.status, 4, r.err);
      assert.match(r.err, /regular file/);
      assert.ok(!r.out.includes("secret"), "nothing of the host's is printed");
    } finally {
      rmSync(work, { recursive: true, force: true });
      rmSync(dir, { recursive: true, force: true });
    }
  });
});
