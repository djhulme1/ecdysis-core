/**
 * The reference runner, end to end on a local repository: it fetches the
 * exact commit and refuses any other, runs the command with ECDYSIS_SEED as
 * the whole environment, reads results/outputs.json, and compares outputs
 * within the bundle's tolerances. Container isolation itself is not
 * exercised here (no docker in CI); the --no-container path is.
 */
import { describe, it, after } from "node:test";
import assert from "node:assert/strict";
import { spawn, spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import { mkdtempSync, writeFileSync, mkdirSync, rmSync, existsSync, readdirSync, readFileSync } from "node:fs";
import { createServer } from "node:http";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fetchInput, isPublicAddress, prepareInputs, urlProblem, type RunnerInput } from "../scripts/runner/inputs.mjs";

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
/** The runner as a child that this process keeps serving while it runs (a test server lives here; spawnSync would deadlock). */
function runnerAsync(args: string[]): Promise<{ status: number | null; out: string; err: string }> {
  return new Promise((resolve) => {
    const child = spawn("node", [RUNNER, ...args], { stdio: ["ignore", "pipe", "pipe"] });
    let out = "", err = "";
    child.stdout.on("data", (d) => { out += d; });
    child.stderr.on("data", (d) => { err += d; });
    child.on("close", (status) => resolve({ status, out, err }));
  });
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

/* ---------------- inputs/0.1 ---------------- */

const sha = (b: Buffer) => createHash("sha256").update(b).digest("hex");

describe("the reference runner's container", { skip: (!hasGit && "git is not available") || (typeof process.getuid !== "function" && "no POSIX user ids here") }, () => {
  // CI has no docker, so a stand-in records the arguments it is given and plays the container: it writes outputs.json into the
  // results mount, as a run would. 4 October 2026: run as the image's own USER, the container could neither read the checkout (a
  // private temporary directory) nor write results/, and every run of the Bombus lab's bundles on GitHub Actions failed.
  it("runs the container as the user running the runner, locked down as before", () => {
    const { url, commit, dir } = repo();
    const work = mkdtempSync(join(tmpdir(), "ecdysis-runner-"));
    try {
      const bin = join(work, "bin");
      mkdirSync(bin);
      const log = join(work, "docker-args.txt");
      writeFileSync(join(bin, "docker"), `#!/bin/sh
if [ "$1" = "--version" ]; then echo "Docker version 0 (stand-in)"; exit 0; fi
if [ "$1" = "rm" ]; then exit 0; fi
printf '%s\n' "$@" > "${log}"
prev=""
for a in "$@"; do
  if [ "$prev" = "-v" ]; then case "$a" in *:/work/results:rw) printf '{"alpha": 1.5}' > "\${a%%:/work/results:rw}/outputs.json";; esac; fi
  prev="$a"
done
exit 0
`, { mode: 0o755 });
      const digest = "sha256:" + "c".repeat(64);
      const bpath = join(work, "bundle.json");
      writeFileSync(bpath, JSON.stringify({ repo: url, commit, run: "sh run.sh", image: digest, imageRef: `ghcr.io/example/env@${digest}`, outputs: [{ name: "alpha", tolerance: 0.1 }], runtimeMinutes: 1 }));
      const r = spawnSync("node", [RUNNER, "--bundle", bpath, "--seed", "a".repeat(64), "--allow-file-repo"], { encoding: "utf8", env: { ...process.env, PATH: `${bin}:${process.env.PATH ?? ""}` } });
      assert.equal(r.status, 0, r.stderr);
      assert.equal((JSON.parse(r.stdout) as Record<string, number>)["alpha"], 1.5, "the outputs the container wrote were read");
      const args = readFileSync(log, "utf8").trim().split("\n");
      const at = args.indexOf("--user");
      assert.ok(at > 0, `the container runs as a named user: ${args.join(" ")}`);
      assert.equal(args[at + 1], `${process.getuid!()}:${process.getgid!()}`, "the user running the runner, who owns the checkout and results/");
      for (const flag of ["--network", "--read-only", "--cap-drop", "--security-opt", "--pids-limit"]) assert.ok(args.includes(flag), `still ${flag}`);
      assert.equal(args[args.indexOf("--network") + 1], "none");
      assert.equal(args[args.indexOf("--cap-drop") + 1], "ALL");
      assert.ok(args.some((a) => a.endsWith(":/work:ro")), "the checkout is read-only");
      assert.equal(args.filter((a) => a.startsWith("ECDYSIS_SEED=")).length, 1);
    } finally {
      rmSync(work, { recursive: true, force: true });
      rmSync(dir, { recursive: true, force: true });
    }
  });
});

describe("the runner's input policy", () => {
  it("knows which addresses a bundle may never send a checker to, and refuses URLs that are not plain public https", () => {
    for (const a of ["127.0.0.1", "10.1.2.3", "172.16.0.1", "172.31.255.255", "192.168.1.1", "169.254.169.254", "100.64.0.1", "0.0.0.0", "224.0.0.1", "::1", "::", "fd00::1", "fe80::1", "::ffff:127.0.0.1", "::ffff:7f00:1", "2001:db8::1"]) assert.equal(isPublicAddress(a), false, a);
    for (const a of ["8.8.8.8", "151.101.1.69", "172.32.0.1", "2606:4700::1111", "::ffff:8.8.8.8"]) assert.equal(isPublicAddress(a), true, a);
    assert.equal(urlProblem("https://data.example.org/x.csv", ["93.184.216.34"]), null);
    assert.equal(urlProblem("http://data.example.org/x.csv", ["93.184.216.34"]), "only https");
    assert.equal(urlProblem("https://169.254.169.254/latest/meta-data", ["169.254.169.254"]), "a host name, not an address");
    assert.equal(urlProblem("https://[::1]/x", ["::1"]), "a host name, not an address");
    assert.equal(urlProblem("https://data.example.org:8443/x", ["93.184.216.34"]), "only port 443");
    assert.equal(urlProblem("https://user:pw@data.example.org/x", ["93.184.216.34"]), "no credentials in the URL");
    assert.equal(urlProblem("https://intranet/x", ["93.184.216.34"]), "a public host name");
    assert.equal(urlProblem("https://nas.local/x", ["93.184.216.34"]), "a public host name");
    assert.match(String(urlProblem("https://data.example.org/x", ["93.184.216.34", "10.0.0.5"])), /non-public address/);
    assert.equal(urlProblem("https://data.example.org/x", []), "the host name did not resolve");
    assert.match(String(urlProblem("https://mirror.example.net/x", ["93.184.216.34"], "https://data.example.org/x")), /may not leave data\.example\.org/);
  });
});

describe("the runner's inputs", { skip: !hasGit && "git is not available" }, () => {
  const payload = Buffer.from("campaign,goal,pledged\n1,100,99\n2,100,250\n".repeat(50));
  const hits: string[] = [];
  const server = createServer((req, res) => {
    hits.push(req.url ?? "");
    if (req.url === "/data") { res.writeHead(200, { "content-length": String(payload.length), "content-type": "text/csv" }); res.end(payload); return; }
    if (req.url === "/long") { res.writeHead(200, { "content-type": "text/csv" }); res.write(payload); res.write(Buffer.from("and more than was declared\n")); res.end(); return; }
    if (req.url === "/away") { res.writeHead(302, { location: `http://127.0.0.2:${port}/data` }); res.end(); return; }
    if (req.url === "/here") { res.writeHead(302, { location: "/data" }); res.end(); return; }
    res.writeHead(404); res.end();
  });
  let port = 0;
  const ready = new Promise<void>((r) => server.listen(0, "127.0.0.1", () => { port = (server.address() as { port: number }).port; r(); }));
  after(() => { server.closeAllConnections(); server.close(); });
  const input = (over: Partial<RunnerInput> = {}): RunnerInput => ({ name: "campaigns", url: `http://127.0.0.1:${port}/data`, sha256: sha(payload), bytes: payload.length, access: "open", licence: "CC0", ...over });

  it("fetches an open input under the policy, verifies it as the bytes arrive, keeps a verified copy, and refuses what does not match", async () => {
    await ready;
    const cache = mkdtempSync(join(tmpdir(), "ecdysis-inputs-"));
    try {
      const o = { cacheDir: cache, allowInsecure: true };
      const ok = await prepareInputs([input()], o);
      assert.ok(ok.paths && ok.paths.get("campaigns") === join(cache, sha(payload)), JSON.stringify(ok));
      assert.equal(hits.filter((h) => h === "/data").length, 1);
      // Again: the cache serves it; nothing is fetched.
      const again = await prepareInputs([input()], o);
      assert.ok(again.paths);
      assert.equal(hits.filter((h) => h === "/data").length, 1, "no second fetch");
      // A wrong hash is refused and leaves nothing behind.
      const wrong = await prepareInputs([input({ sha256: "f".repeat(64), name: "other" })], o);
      assert.match(String(wrong.problems?.[0]), /do not hash to the declared sha256/);
      assert.ok(!existsSync(join(cache, "f".repeat(64))));
      assert.deepEqual(readdirSync(cache).filter((f) => f.includes(".part")), [], "no partial file is kept");
      // A source that sends more than declared is stopped at one byte over, and a declared size that disagrees is refused before any byte.
      const long = await fetchInput(input({ url: `http://127.0.0.1:${port}/long`, name: "long" }), join(cache, "x"), o);
      assert.match(String(long), /more than the declared/);
      const sized = await fetchInput(input({ bytes: payload.length + 1, name: "sized" }), join(cache, "y"), o);
      assert.match(String(sized), /the source says/);
      // A redirect within the host is followed; one to another host is refused.
      assert.equal(await fetchInput(input({ url: `http://127.0.0.1:${port}/here`, name: "here" }), join(cache, "z"), o), null);
      assert.match(String(await fetchInput(input({ url: `http://127.0.0.1:${port}/away`, name: "away" }), join(cache, "w"), o)), /may not leave 127\.0\.0\.1/);
      // Registered and restricted inputs are never fetched: the checker supplies the file, and it must be the declared one.
      const restricted = await prepareInputs([input({ access: "restricted", url: "https://archive.example.org/study/1" })], { cacheDir: mkdtempSync(join(tmpdir(), "ecdysis-inputs-")), allowInsecure: true });
      assert.match(String(restricted.problems?.[0]), /is restricted: obtain it under the source's terms .* --input campaigns=<path>/);
      const copy = join(cache, "copy.csv");
      writeFileSync(copy, payload);
      const held = input({ access: "restricted", url: "https://archive.example.org/study/1" });
      const supplied = await prepareInputs([held], { cacheDir: cache, supplied: new Map([["campaigns", copy]]) });
      assert.equal(supplied.paths?.get("campaigns"), copy, JSON.stringify(supplied));
      writeFileSync(copy, Buffer.concat([payload, Buffer.from("x")]));
      const tampered = await prepareInputs([held], { cacheDir: cache, supplied: new Map([["campaigns", copy]]) });
      assert.match(String(tampered.problems?.[0]), /bytes, the bundle declares/);
      // The ceiling on the total.
      const big = await prepareInputs([input({ bytes: 2 ** 36, sha256: "e".repeat(64), name: "big" })], { ...o, totalCap: 2 ** 35 });
      assert.match(String(big.problems?.[0]), /over this runner's ceiling/);
    } finally {
      rmSync(cache, { recursive: true, force: true });
    }
  });

  it("runs a bundle with its inputs at inputs/<name>, from a supplied copy, and refuses to run without them", async () => {
    await ready;
    const dir = mkdtempSync(join(tmpdir(), "ecdysis-bundle-"));
    const work = mkdtempSync(join(tmpdir(), "ecdysis-runner-"));
    try {
      writeFileSync(join(dir, "run.sh"), `#!/bin/sh
set -e
mkdir -p results
rows=$(wc -l < inputs/campaigns | tr -d ' ')
bytes=$(wc -c < inputs/campaigns | tr -d ' ')
printf '{"rows": %s, "bytes": %s}\n' "$rows" "$bytes" > results/outputs.json
`);
      sh("git", ["init", "-q", "-b", "main"], dir);
      sh("git", ["add", "."], dir);
      sh("git", ["commit", "-q", "-m", "bundle"], dir);
      const commit = sh("git", ["rev-parse", "HEAD"], dir).stdout.trim();
      const bundle = { repo: `file://${dir}`, commit, run: "sh run.sh", outputs: [{ name: "rows" }, { name: "bytes" }], runtimeMinutes: 1, inputs: [input({ access: "registered", url: "https://archive.example.org/study/1" })] };
      const bpath = join(work, "bundle.json");
      writeFileSync(bpath, JSON.stringify(bundle));
      const cache = join(work, "cache");
      // Without the file: refused before the repository is fetched, with the way to supply it.
      const missing = runner(["--bundle", bpath, "--seed", "a".repeat(64), "--no-container", "--allow-file-repo", "--inputs-cache", cache]);
      assert.equal(missing.status, 3, missing.err);
      assert.match(missing.err, /--input campaigns=<path>/);
      // With it: the run sees the verified bytes at inputs/campaigns.
      const copy = join(work, "campaigns.csv");
      writeFileSync(copy, payload);
      const ran = runner(["--bundle", bpath, "--seed", "a".repeat(64), "--no-container", "--allow-file-repo", "--inputs-cache", cache, "--input", `campaigns=${copy}`]);
      assert.equal(ran.status, 0, ran.err);
      const out = JSON.parse(ran.out) as Record<string, number>;
      assert.equal(out["bytes"], payload.length);
      assert.equal(out["rows"], 150);
      // An open input is fetched by the runner itself (the test server; --allow-insecure-inputs is for tests only).
      const open = { ...bundle, inputs: [input()] };
      writeFileSync(join(work, "open.json"), JSON.stringify(open));
      const fetched = await runnerAsync(["--bundle", join(work, "open.json"), "--seed", "a".repeat(64), "--no-container", "--allow-file-repo", "--inputs-cache", cache, "--allow-insecure-inputs"]);
      assert.equal(fetched.status, 0, fetched.err);
      assert.match(fetched.err, /fetched and verified/);
      assert.ok(existsSync(join(cache, sha(payload))), "the verified copy is cached");
      // Without the tests-only flag the same http URL is refused by the policy, and nothing runs.
      const refused = runner(["--bundle", join(work, "open.json"), "--seed", "a".repeat(64), "--no-container", "--allow-file-repo", "--inputs-cache", join(work, "cache2")]);
      assert.equal(refused.status, 3);
      assert.match(refused.err, /url: https/);
    } finally {
      rmSync(work, { recursive: true, force: true });
      rmSync(dir, { recursive: true, force: true });
    }
  });
});
