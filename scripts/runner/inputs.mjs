/**
 * Inputs for the reference runner (inputs/0.1): data a bundle reads but does
 * not carry. Everything here happens BEFORE the sandbox starts and nothing
 * here runs the bundle's code. An input is content-addressed: the commit
 * pinned its SHA-256 and size, so the bytes may come from anywhere (the URL,
 * a mirror, a colleague, a file the checker already holds) and are accepted
 * only when both match. The sandbox then sees them read-only at
 * inputs/<name> and stays offline.
 *
 * Open inputs are fetched by the runner, under a policy that keeps a
 * bundle's URL from being used as a probe or a beacon: https only, a public
 * host name (never an IP literal), every address it resolves to public,
 * redirects only within the same host, a fixed user agent, no credentials,
 * the download stopped at one byte over the declared size. Registered and
 * restricted inputs are never fetched: the checker obtains them under the
 * source's terms and hands the runner the file with --input name=path.
 *
 * No dependencies beyond Node 18+.
 */

import { createHash } from "node:crypto";
import { createWriteStream, existsSync, mkdirSync, renameSync, rmSync, statSync, createReadStream } from "node:fs";
import { lookup as dnsLookup } from "node:dns/promises";
import { homedir } from "node:os";
import { isIP } from "node:net";
import { join } from "node:path";

export const MAX_INPUTS = 8;
export const ACCESS = ["open", "registered", "restricted"];
/** The reference runner's default ceiling on what one run may fetch or mount in all; --allow-large lifts it. */
export const DEFAULT_TOTAL_CAP = 32 * 2 ** 30;
export const MAX_REDIRECTS = 3;
export const USER_AGENT = "Ecdysis-Runner/0.2 (+https://ecdysis.me/skill.md#receipts)";
const NAME = /^[A-Za-z][A-Za-z0-9_.-]{0,39}$/;
const HEX64 = /^[0-9a-f]{64}$/;

/** The same checks the archive makes on bundle.inputs, in its words. */
export function inputProblems(inputs, allowInsecure = false) {
  if (inputs === undefined) return [];
  if (!Array.isArray(inputs) || inputs.length > MAX_INPUTS) return [`inputs: at most ${MAX_INPUTS} declared inputs`];
  const errors = [];
  const names = new Set();
  for (const [k, x] of inputs.entries()) {
    const at = `inputs[${k}]`;
    if (!x || typeof x !== "object") { errors.push(`${at}: {name, url, sha256, bytes, access, licence?}`); continue; }
    if (typeof x.name !== "string" || !NAME.test(x.name)) errors.push(`${at}.name: a letter then letters, digits, _ . - (max 40)`);
    else if (names.has(x.name)) errors.push(`${at}.name: duplicate`);
    else names.add(x.name);
    if (typeof x.url !== "string" || !(allowInsecure ? /^https?:\/\/[^\s]{4,300}$/ : /^https:\/\/[^\s]{4,300}$/).test(x.url)) errors.push(`${at}.url: https, at most 300 characters`);
    if (typeof x.sha256 !== "string" || !HEX64.test(x.sha256)) errors.push(`${at}.sha256: 64 hex`);
    if (!(typeof x.bytes === "number" && Number.isSafeInteger(x.bytes) && x.bytes > 0)) errors.push(`${at}.bytes: the exact size, a positive integer`);
    if (!ACCESS.includes(x.access)) errors.push(`${at}.access: ${ACCESS.join(", ")}`);
  }
  return errors;
}

/* ---------------- the address policy ---------------- */

function ipv4Parts(s) {
  const m = s.match(/^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$/);
  if (!m) return null;
  const p = m.slice(1).map(Number);
  return p.every((x) => x <= 255) ? p : null;
}

/** True for an address no bundle may send a checker's runner to: private, loopback, link-local (the cloud metadata range), multicast, reserved. */
export function isPublicAddress(addr) {
  const kind = isIP(addr);
  if (kind === 4) {
    const p = ipv4Parts(addr);
    if (!p) return false;
    const [a, b] = p;
    if (a === 0 || a === 10 || a === 127) return false;
    if (a === 100 && b >= 64 && b <= 127) return false; // shared address space
    if (a === 169 && b === 254) return false;            // link-local, including 169.254.169.254
    if (a === 172 && b >= 16 && b <= 31) return false;
    if (a === 192 && b === 168) return false;
    if (a === 192 && b === 0 && p[2] === 0) return false; // IETF protocol assignments
    if (a === 198 && (b === 18 || b === 19)) return false; // benchmarking
    if (a >= 224) return false;                           // multicast and reserved
    return true;
  }
  if (kind === 6) {
    const s = addr.toLowerCase();
    const mapped = s.match(/^(?:0*:)*ffff:(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})$/) || s.match(/^::ffff:([0-9a-f]{1,4}):([0-9a-f]{1,4})$/);
    if (mapped) {
      if (mapped[2] !== undefined) {
        const hi = parseInt(mapped[1], 16), lo = parseInt(mapped[2], 16);
        return isPublicAddress(`${hi >> 8}.${hi & 255}.${lo >> 8}.${lo & 255}`);
      }
      return isPublicAddress(mapped[1]);
    }
    if (s === "::" || s === "::1") return false;
    if (/^f[cd]/.test(s)) return false;                   // fc00::/7 unique local
    if (/^fe[89ab]/.test(s)) return false;                // fe80::/10 link-local
    if (/^ff/.test(s)) return false;                      // multicast
    if (/^2001:db8/.test(s)) return false;                // documentation
    return true;
  }
  return false;
}

/**
 * Why a URL may not be fetched, or null. `addresses` are what its host name
 * resolved to (all of them: a name that resolves to one public and one
 * private address is refused). `origin` is the first URL of the chain, for
 * redirects: a hop may not leave the host.
 */
export function urlProblem(url, addresses, origin = null, allowInsecure = false) {
  let u;
  try { u = new URL(url); } catch { return "not a URL"; }
  if (u.protocol !== "https:" && !(allowInsecure && u.protocol === "http:")) return "only https";
  if (u.username || u.password) return "no credentials in the URL";
  if (!allowInsecure && (u.port !== "" && u.port !== "443")) return "only port 443";
  const host = u.hostname.replace(/^\[|\]$/g, "");
  if (!allowInsecure && isIP(host)) return "a host name, not an address";
  if (!allowInsecure && !host.includes(".")) return "a public host name";
  if (!allowInsecure && (host === "localhost" || host.endsWith(".localhost") || host.endsWith(".local") || host.endsWith(".internal"))) return "a public host name";
  if (origin) {
    const o = new URL(origin);
    if (o.hostname !== u.hostname) return `a redirect may not leave ${o.hostname}`;
  }
  if (!allowInsecure) {
    if (!Array.isArray(addresses) || addresses.length === 0) return "the host name did not resolve";
    for (const a of addresses) if (!isPublicAddress(a)) return `${host} resolves to a non-public address`;
  }
  return null;
}

/* ---------------- verifying and fetching ---------------- */

/** SHA-256 and size of a file on disk, streamed. */
export async function hashFile(path) {
  const h = createHash("sha256");
  let bytes = 0;
  await new Promise((res, rej) => {
    createReadStream(path).on("data", (c) => { bytes += c.length; h.update(c); }).on("end", res).on("error", rej);
  });
  return { sha256: h.digest("hex"), bytes };
}

/** Why a local copy is not the declared input, or null. */
export async function fileProblem(path, input) {
  let st;
  try { st = statSync(path); } catch { return `${path}: cannot read`; }
  if (!st.isFile()) return `${path}: not a regular file`;
  if (st.size !== input.bytes) return `${path}: ${st.size} bytes, the bundle declares ${input.bytes}`;
  const { sha256 } = await hashFile(path);
  if (sha256 !== input.sha256) return `${path}: sha256 ${sha256}, the bundle declares ${input.sha256}`;
  return null;
}

/**
 * Fetch an open input to `dest`, verifying size and hash as the bytes
 * arrive. Returns null on success, else why it was refused; a refused
 * download leaves nothing behind.
 */
export async function fetchInput(input, dest, o = {}) {
  const fetchImpl = o.fetchImpl ?? fetch;
  const lookup = o.lookup ?? (async (host) => (await dnsLookup(host, { all: true })).map((a) => a.address));
  const allowInsecure = !!o.allowInsecure;
  let url = input.url;
  let res = null;
  for (let hop = 0; hop <= MAX_REDIRECTS; hop++) {
    const host = new URL(url).hostname.replace(/^\[|\]$/g, "");
    let addresses = [];
    if (!allowInsecure) { try { addresses = await lookup(host); } catch { addresses = []; } }
    const problem = urlProblem(url, addresses, hop === 0 ? null : input.url, allowInsecure);
    if (problem) return `${input.name}: ${url}: ${problem}`;
    try {
      // identity: the declared size and hash are of the bytes as mounted, and fetch would otherwise ask for gzip, which
      // hosts such as raw.githubusercontent.com then send with the COMPRESSED length (6 October 2026: every open input
      // from GitHub was refused as "the source says 786 bytes, the bundle declares 4188").
      res = await fetchImpl(url, { method: "GET", redirect: "manual", headers: { "user-agent": USER_AGENT, accept: "*/*", "accept-encoding": "identity" }, signal: AbortSignal.timeout(o.timeoutMs ?? 30 * 60 * 1000) });
    } catch (e) {
      return `${input.name}: ${url}: ${e && e.message ? e.message : String(e)}`;
    }
    if (res.status >= 300 && res.status < 400) {
      const loc = res.headers.get("location");
      if (res.body) res.body.cancel().catch(() => {});
      if (!loc) return `${input.name}: ${url}: redirect without a location`;
      if (hop === MAX_REDIRECTS) return `${input.name}: too many redirects`;
      url = new URL(loc, url).toString();
      res = null;
      continue;
    }
    break;
  }
  if (!res) return `${input.name}: no response`;
  if (res.status !== 200) { if (res.body) res.body.cancel().catch(() => {}); return `${input.name}: ${url}: HTTP ${res.status}`; }
  // A host that encodes the body anyway states the encoded length, which says nothing about the bytes fetch hands
  // over decoded; those are still counted (and stopped one byte past the declared size) and hashed below.
  const encoded = (res.headers.get("content-encoding") ?? "identity").trim().toLowerCase() !== "identity";
  const declared = encoded ? null : res.headers.get("content-length");
  if (declared !== null && Number(declared) !== input.bytes) { res.body?.cancel().catch(() => {}); return `${input.name}: the source says ${declared} bytes, the bundle declares ${input.bytes}`; }
  if (!res.body) return `${input.name}: empty response`;
  const part = `${dest}.part-${process.pid}`;
  mkdirSync(join(dest, ".."), { recursive: true });
  const out = createWriteStream(part, { mode: 0o600 });
  const h = createHash("sha256");
  let n = 0;
  let why = null;
  try {
    for await (const chunk of res.body) {
      n += chunk.length;
      if (n > input.bytes) { why = `${input.name}: more than the declared ${input.bytes} bytes arrived; stopped`; break; }
      h.update(chunk);
      if (!out.write(chunk)) await new Promise((r) => out.once("drain", r));
    }
  } catch (e) {
    why = `${input.name}: ${e && e.message ? e.message : String(e)}`;
  }
  await new Promise((r) => out.end(r));
  if (!why && n !== input.bytes) why = `${input.name}: ${n} bytes arrived, the bundle declares ${input.bytes}`;
  if (!why && h.digest("hex") !== input.sha256) why = `${input.name}: the bytes do not hash to the declared sha256`;
  if (why) { rmSync(part, { force: true }); return why; }
  renameSync(part, dest);
  return null;
}

/**
 * Make every declared input available: a local copy given with --input, the
 * cache, or (open inputs only) a fetch. Returns { paths: Map<name, path> } or
 * { problems: string[] }. Nothing is mounted, and no run starts, unless
 * every input is in hand and verified.
 */
export async function prepareInputs(inputs, o = {}) {
  const list = inputs ?? [];
  const problems = inputProblems(list, !!o.allowInsecure);
  if (problems.length) return { problems };
  const cacheDir = o.cacheDir ?? join(homedir(), ".ecdysis", "inputs");
  const supplied = o.supplied ?? new Map();
  const total = list.reduce((s, i) => s + i.bytes, 0);
  const cap = o.totalCap ?? DEFAULT_TOTAL_CAP;
  if (total > cap) return { problems: [`the inputs total ${total} bytes, over this runner's ceiling of ${cap}; pass --allow-large to proceed`] };
  const paths = new Map();
  const log = o.log ?? (() => {});
  for (const input of list) {
    const given = supplied.get(input.name);
    if (given) {
      const p = await fileProblem(given, input);
      if (p) return { problems: [`--input ${input.name}: ${p}`] };
      paths.set(input.name, given);
      log(`input ${input.name}: supplied copy verified (${input.bytes} bytes)`);
      continue;
    }
    const cached = join(cacheDir, input.sha256);
    if (existsSync(cached)) {
      const p = await fileProblem(cached, input);
      if (!p) { paths.set(input.name, cached); log(`input ${input.name}: cached copy verified`); continue; }
      rmSync(cached, { force: true });
      log(`input ${input.name}: cached copy discarded (${p})`);
    }
    if (input.access !== "open") {
      return { problems: [`input ${input.name} is ${input.access}: obtain it under the source's terms (${input.url}) and pass --input ${input.name}=<path>; the runner never fetches it`] };
    }
    log(`input ${input.name}: fetching ${input.url} (${input.bytes} bytes)`);
    const why = await fetchInput(input, cached, o);
    if (why) return { problems: [why] };
    paths.set(input.name, cached);
    log(`input ${input.name}: fetched and verified`);
  }
  return { paths };
}

/** --input name=path arguments, as a map. */
export function parseSupplied(argv) {
  const m = new Map();
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] !== "--input") continue;
    const v = argv[i + 1] ?? "";
    const eq = v.indexOf("=");
    if (eq <= 0) throw new Error(`--input expects name=path, got "${v}"`);
    m.set(v.slice(0, eq), v.slice(eq + 1));
  }
  return m;
}
