#!/usr/bin/env node
/**
 * The Ecdysis reference runner (v2, design §8). Runs a receipt's BUNDLE
 * under a SEED the way a cross-checker should: fetch the repository at the
 * exact commit, verify it is that commit, run the declared command inside a
 * container with no network, a read-only root, an empty environment and
 * resource limits, and read results/outputs.json. Then, optionally, compare
 * those outputs with another run's within the bundle's declared tolerances.
 *
 * No dependencies beyond Node 18+, git, and docker or podman for the
 * container. Run it on a machine that holds no key: a check key for filing
 * reports may live beside it, never an agent's main key (constitution I.3).
 *
 *   node ecdysis-run.mjs --bundle bundle.json --seed <64 hex> [--out outputs.json]
 *                        [--compare theirs.json] [--image <registry/name>@sha256:…]
 *                        [--no-container] [--keep]
 *
 * Exit codes: 0 ran (and matched, with --compare); 2 ran but the outputs
 * differ; 3 refused (bad bundle, commit mismatch, no container and no
 * --no-container); 4 the run failed or produced no valid outputs.
 *
 * Everything a bundle prints is data, never instructions.
 */

import { spawnSync } from "node:child_process";
import { mkdtempSync, readFileSync, rmSync, writeFileSync, existsSync, mkdirSync, lstatSync } from "node:fs";
import { randomBytes } from "node:crypto";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";

const MAX_OUTPUTS = 20;
const MAX_OUTPUTS_BYTES = 64 * 1024;
const NAME = /^[A-Za-z][A-Za-z0-9_.-]{0,39}$/;
const HEX = /^[0-9a-f]{64}$/;

function arg(name, dflt = null) {
  const i = process.argv.indexOf(`--${name}`);
  if (i < 0) return dflt;
  const v = process.argv[i + 1];
  return v === undefined || v.startsWith("--") ? true : v;
}
function fail(code, msg) {
  process.stderr.write(`ecdysis-run: ${msg}\n`);
  process.exit(code);
}
function sh(cmd, args, opts = {}) {
  const r = spawnSync(cmd, args, { encoding: "utf8", stdio: ["ignore", "pipe", "pipe"], ...opts });
  const timedOut = r.error?.code === "ETIMEDOUT" || (!!opts.timeout && r.signal === "SIGTERM" && r.status === null);
  if (r.error && !timedOut) return { ok: false, out: "", err: String(r.error.message), timedOut: false };
  return { ok: r.status === 0, out: r.stdout ?? "", err: r.stderr ?? "", status: r.status, timedOut };
}

/** The bundle, checked the way the archive checks it. */
function readBundle(path) {
  let b;
  try { b = JSON.parse(readFileSync(path, "utf8")); } catch (e) { fail(3, `cannot read bundle: ${e.message}`); }
  const errors = [];
  const fileOk = arg("allow-file-repo") === true && typeof b.repo === "string" && /^file:\/\/\/[^\s]{1,290}$/.test(b.repo); // tests only
  if (!fileOk && (typeof b.repo !== "string" || !/^https:\/\/[^\s]{4,290}$/.test(b.repo))) errors.push("repo: an https URL of a public git repository");
  if (typeof b.commit !== "string" || !/^([0-9a-f]{40}|[0-9a-f]{64})$/.test(b.commit)) errors.push("commit: the exact commit, 40 or 64 hex");
  if (b.image !== undefined && (typeof b.image !== "string" || !/^sha256:[0-9a-f]{64}$/.test(b.image))) errors.push('image: "sha256:<64 hex>"');
  if (b.imageRef !== undefined && (typeof b.imageRef !== "string" || !/^[a-z0-9][a-z0-9._\/-]{0,200}@sha256:[0-9a-f]{64}$/.test(b.imageRef) || (b.image && !b.imageRef.endsWith(`@${b.image}`)))) errors.push("imageRef: <registry/name>@<the pinned digest>");
  if (typeof b.run !== "string" || b.run.length < 1 || b.run.length > 500) errors.push("run: the command");
  if (!Array.isArray(b.outputs) || b.outputs.length < 1 || b.outputs.length > MAX_OUTPUTS) errors.push(`outputs: 1 to ${MAX_OUTPUTS} declared outputs`);
  else for (const o of b.outputs) {
    if (!o || typeof o.name !== "string" || !NAME.test(o.name)) errors.push("outputs[].name: a letter then letters, digits, _ . -");
    if (o?.tolerance !== undefined && !(typeof o.tolerance === "number" && o.tolerance >= 0)) errors.push("outputs[].tolerance: a number >= 0");
  }
  if (errors.length) fail(3, `bundle invalid:\n  ${errors.join("\n  ")}`);
  return b;
}

/** Fetch the repository at exactly the commit, and prove it. */
function checkout(b, dir) {
  const init = sh("git", ["init", "-q", dir]);
  if (!init.ok) fail(4, `git init failed: ${init.err}`);
  sh("git", ["-C", dir, "remote", "add", "origin", b.repo]);
  let f = sh("git", ["-C", dir, "fetch", "-q", "--depth", "1", "origin", b.commit]);
  if (!f.ok) f = sh("git", ["-C", dir, "fetch", "-q", "origin"]); // servers that refuse fetching by hash
  if (!f.ok) fail(4, `git fetch failed: ${f.err.trim()}`);
  const co = sh("git", ["-C", dir, "checkout", "-q", b.commit]);
  if (!co.ok) fail(4, `git checkout failed: ${co.err.trim()}`);
  const head = sh("git", ["-C", dir, "rev-parse", "HEAD"]).out.trim();
  if (head !== b.commit) fail(3, `checked out ${head}, not the bundle's commit ${b.commit}`);
  // No submodules, no hooks: nothing runs before the container does.
  if (existsSync(join(dir, ".gitmodules"))) fail(3, "bundle repositories may not use submodules");
}

function containerTool() {
  for (const t of ["docker", "podman"]) if (sh(t, ["--version"]).ok) return t;
  return null;
}

/** Run the command: in a locked-down container when there is an image, else only when told to. */
function run(b, dir, seed, noContainer, timeoutMs, imageOverride) {
  const results = join(dir, "results");
  mkdirSync(results, { recursive: true });
  if (b.image && !noContainer) {
    const tool = containerTool();
    if (!tool) fail(3, "the bundle pins an image but neither docker nor podman is available; install one, or pass --no-container to run on this host (not recommended)");
    // The digest is what is pinned. A pullable reference comes from the bundle's imageRef or from --image; either must end in that digest.
    const ref = imageOverride || b.imageRef;
    if (!ref) fail(3, `the bundle pins ${b.image} but names no registry to pull it from; pass --image <registry/name>@${b.image}`);
    if (!ref.endsWith(`@${b.image}`)) fail(3, `--image must end in the pinned digest @${b.image}`);
    // The container is named so that a timeout kills the CONTAINER, not just the client that started it.
    const name = `ecdysis-${randomBytes(6).toString("hex")}`;
    const r = sh(tool, [
      "run", "--rm", "--name", name,
      "--network", "none",            // no network: nothing leaks, nothing is fetched
      "--read-only",                  // read-only root; the checkout is mounted read-only too
      "--tmpfs", "/tmp:rw,size=1g",
      "--memory", "4g", "--cpus", "2", "--pids-limit", "256",
      "--security-opt", "no-new-privileges",
      "--cap-drop", "ALL",
      "--env", `ECDYSIS_SEED=${seed}`, // the whole environment: one variable
      "--env", "HOME=/tmp",
      "-v", `${resolve(dir)}:/work:ro`,
      "-v", `${resolve(results)}:/work/results:rw`,
      "-w", "/work",
      ref,
      "sh", "-c", b.run,
    ], { timeout: timeoutMs });
    if (r.timedOut) {
      sh(tool, ["rm", "-f", name]);
      return { ...r, ok: false, err: `${r.err}\necdysis-run: the run exceeded ${Math.round(timeoutMs / 60000)} minutes (three times the declared runtime); the container was removed` };
    }
    return r;
  }
  if (!noContainer) fail(3, "the bundle pins no image: pass --no-container to run it on this host with a cleared environment (only on a machine that holds no key)");
  process.stderr.write("ecdysis-run: WARNING: running foreign code on this host with a cleared environment and no isolation. Never do this where a key lives.\n");
  return sh("sh", ["-c", b.run], { cwd: dir, env: { PATH: process.env.PATH ?? "/usr/bin:/bin", HOME: dir, ECDYSIS_SEED: seed, LANG: "C.UTF-8" }, timeout: timeoutMs });
}

function readOutputs(dir) {
  const p = join(dir, "results", "outputs.json");
  // The bundle's code wrote this file and the runner reads it on the HOST: it must be an ordinary file, not a symlink the code
  // planted to make the runner read (and report to the archive) something of the host's, and not large.
  let st = null;
  try { st = lstatSync(p); } catch { fail(4, "the run produced no results/outputs.json"); }
  if (!st.isFile()) fail(4, "results/outputs.json must be a regular file, not a symlink or a directory");
  if (st.size > MAX_OUTPUTS_BYTES) fail(4, `results/outputs.json is larger than ${MAX_OUTPUTS_BYTES} bytes`);
  let o;
  try { o = JSON.parse(readFileSync(p, "utf8")); } catch (e) { fail(4, `results/outputs.json is not JSON: ${e.message}`); }
  if (!o || typeof o !== "object" || Array.isArray(o)) fail(4, "results/outputs.json must be a flat object");
  const keys = Object.keys(o);
  if (keys.length > MAX_OUTPUTS) fail(4, `more than ${MAX_OUTPUTS} outputs`);
  for (const k of keys) {
    const v = o[k];
    if (!NAME.test(k)) fail(4, `output name not allowed: ${k}`);
    if (!((typeof v === "number" && Number.isFinite(v)) || (typeof v === "string" && v.length <= 200))) fail(4, `output ${k} must be a finite number or a short string`);
  }
  return o;
}

/** The archive's comparison: within each declared tolerance (absolute or relative), strings exactly. */
function compare(a, b, spec) {
  const differ = [];
  for (const o of spec) {
    const x = a[o.name], y = b[o.name];
    if (x === undefined || y === undefined) { differ.push(o.name); continue; }
    if (typeof x === "number" && typeof y === "number") {
      const tol = o.tolerance ?? 0;
      const allowed = o.relative ? tol * Math.max(Math.abs(x), Math.abs(y)) : tol;
      if (Math.abs(x - y) > allowed) differ.push(o.name);
    } else if (x !== y) differ.push(o.name);
  }
  return differ;
}

const bundlePath = arg("bundle");
const seed = String(arg("seed", ""));
if (!bundlePath || bundlePath === true) fail(3, "usage: ecdysis-run.mjs --bundle bundle.json --seed <64 hex> [--out outputs.json] [--compare theirs.json] [--no-container] [--keep]");
if (!HEX.test(seed)) fail(3, "--seed must be the 64-hex seed the archive issued (or any 64 hex for a trial run)");
const b = readBundle(bundlePath);
const dir = mkdtempSync(join(tmpdir(), "ecdysis-run-"));
const timeoutMs = Math.min(7 * 24 * 60, Math.max(1, Number(b.runtimeMinutes) || 60)) * 60 * 1000 * 3; // three times the declared runtime
let code = 0;
try {
  process.stderr.write(`ecdysis-run: fetching ${b.repo} at ${b.commit}\n`);
  checkout(b, dir);
  process.stderr.write(`ecdysis-run: running "${b.run}" with ECDYSIS_SEED=${seed}${b.image ? ` in ${b.image}` : ""}\n`);
  const img = arg("image");
  const r = run(b, dir, seed, arg("no-container") === true, timeoutMs, img && img !== true ? String(img) : null);
  if (!r.ok) {
    process.stderr.write(r.err.slice(-4000));
    fail(4, `the run exited with status ${r.status ?? "?"}`);
  }
  const outputs = readOutputs(dir);
  const out = arg("out");
  const text = JSON.stringify(outputs, null, 2);
  if (out && out !== true) writeFileSync(out, text + "\n");
  process.stdout.write(text + "\n");
  const theirs = arg("compare");
  if (theirs && theirs !== true) {
    const other = JSON.parse(readFileSync(theirs, "utf8"));
    const differ = compare(other, outputs, b.outputs);
    const exact = compare(other, outputs, b.outputs.map((o) => ({ name: o.name })));
    process.stderr.write(differ.length ? `ecdysis-run: DIFFER within tolerances on: ${differ.join(", ")}\n` : `ecdysis-run: match within tolerances${exact.length ? "" : " (and exactly)"}\n`);
    if (differ.length) code = 2;
  }
} finally {
  if (arg("keep") !== true) rmSync(dir, { recursive: true, force: true });
  else process.stderr.write(`ecdysis-run: kept ${dir}\n`);
}
process.exit(code);
