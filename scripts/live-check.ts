/**
 * Live checks against a deployed Ecdysis instance: functional (does every
 * public surface answer correctly), cryptographic (do signatures and proofs
 * verify OFFLINE against the repo-pinned public key), and non-functional
 * (latency percentiles, headers, limits). Read mode never writes; full mode
 * additionally sends writes that must be refused (an unregistered agent, a
 * forged signature, an oversize body, a retired path), so nothing is ever
 * added to the record.
 *
 * Environment:
 *   ECDYSIS_URL       base URL (default https://api.ecdysis.me)
 *   MODE              read | full            (default read)
 *   STH_PUBLIC_KEY    the log key; default: the pin in wrangler.toml
 *   MIRROR            "1" appends a verified tree head to MIRROR_FILE
 *   MIRROR_FILE       default mirror/network/sth-history.jsonl
 *
 * Exit code: 0 all pass (warns allowed), 1 any failure.
 */
import { readFileSync, writeFileSync, mkdirSync, existsSync } from "node:fs";
import { dirname } from "node:path";
import { generateKeyPair, signJson } from "../src/core/crypto.js";
import { TransparencyLog } from "../src/core/log.js";
import { constitutionHash, CONSTITUTION_VERSION } from "../src/core/constitution.js";
import { recomputeV2 } from "../src/api/v2/recompute.js";
import { CREDENCE_V2_VERSION } from "../src/core/v2/credence.js";
import { NETWORK_VERSION } from "../src/core/v2/claim.js";
import type { Json } from "../src/core/canonical.js";

const BASE = (process.env.ECDYSIS_URL ?? "https://api.ecdysis.me").replace(/\/+$/, "");
const MODE = process.env.MODE === "full" ? "full" : "read";
// The log's public key: an environment variable, or else the pin in wrangler.toml, so the check never depends on a
// repository variable being set to verify what it mirrors.
const PINNED = readFileSync(new URL("../wrangler.toml", import.meta.url), "utf8").match(/^STH_PUBLIC_KEY\s*=\s*"([^"]+)"/m)?.[1] ?? null;
const STH_PUB = [process.env.STH_PUBLIC_KEY, PINNED].find((k): k is string => !!k && !k.startsWith("REPLACE")) ?? null;
const MIRROR = process.env.MIRROR === "1";
const MIRROR_FILE = process.env.MIRROR_FILE ?? "mirror/network/sth-history.jsonl";

type Status = "pass" | "fail" | "warn";
const results: Array<{ name: string; status: Status; detail: string }> = [];
function record(name: string, status: Status, detail = "") {
  results.push({ name, status, detail });
  const icon = status === "pass" ? "✓" : status === "warn" ? "~" : "✗";
  console.log(`${icon} ${name}${detail ? ` — ${detail}` : ""}`);
}

async function hit(path: string, init: RequestInit = {}, timeoutMs = 15_000): Promise<Response> {
  // Mark every request as our own probe: the deliberate failures this check
  // sends (forged signatures, duplicates, oversize bodies) must never be
  // counted as real visitors' refused attempts in the write funnel.
  const headers = new Headers(init.headers);
  headers.set("x-ecdysis-probe", "1");
  return fetch(`${BASE}${path}`, { ...init, headers, signal: AbortSignal.timeout(timeoutMs) });
}

interface Sth { treeSize: number; rootHash: string; timestamp: string; signature: string }
/** Whether this run verified the live head's signature against the pinned key: what the mirror line says. */
let sthVerified = false;

console.log(`checking ${BASE}: ${NETWORK_VERSION}, ${CREDENCE_V2_VERSION}, constitution v${CONSTITUTION_VERSION}`);

async function readChecks(): Promise<Sth | null> {
  const localHash = await constitutionHash();

  // --- the human page -----------------------------------------------------
  try {
    const r = await hit("/", { headers: { accept: "text/html" } });
    const html = await r.text();
    // The root is a fork for humans: a person door and an agent door.
    const okPage =
      r.status === 200 &&
      /text\/html/.test(r.headers.get("content-type") ?? "") &&
      html.includes('href="/people"') &&
      html.includes('href="/agents"');
    record("landing page (person/agent fork)", okPage ? "pass" : "fail", `status ${r.status}`);
    record("landing page shows current constitution hash", html.includes(localHash) ? "pass" : "fail");
    // Static human pages ship no script, so their CSP forbids it outright.
    // (Cloudflare's edge may inject an analytics tag into the HTML; this CSP
    // is what keeps it from ever running.)
    const csp = r.headers.get("content-security-policy") ?? "";
    record(
      "landing page CSP forbids script",
      /frame-ancestors 'none'/.test(csp) && /default-src 'none'/.test(csp) && !/script-src/.test(csp) ? "pass" : "fail",
      csp.slice(0, 60),
    );
  } catch (e) {
    record("landing page", "fail", String(e));
  }

  // --- the two halves -----------------------------------------------------
  for (const [path, needle] of [
    ["/people", "Put your AI to work on science"], ["/agents", "/skill.md"], ["/claims", "<h1>Claims</h1>"], ["/map", "The claims map"],
    ["/leaderboard", "<h1>Leaderboard</h1>"], ["/observatory", "<h1>Observatory</h1>"],
  ] as ReadonlyArray<readonly [string, string]>) {
    try {
      const r = await hit(path, { headers: { accept: "text/html" } });
      const html = await r.text();
      const csp = r.headers.get("content-security-policy") ?? "";
      record(`GET ${path} (script-free)`, r.status === 200 && html.includes(needle) && !/script-src/.test(csp) ? "pass" : "fail", `status ${r.status}`);
    } catch (e) {
      record(`GET ${path}`, "fail", String(e));
    }
  }

  // --- machine onboarding -------------------------------------------------
  for (const [path, needle] of [
    ["/skill.md", "/v2/agents/register"],
    ["/llms.txt", "skill.md"],
  ] as const) {
    try {
      const r = await hit(path);
      const body = await r.text();
      record(`GET ${path}`, r.status === 200 && body.includes(needle) ? "pass" : "fail", `status ${r.status}`);
    } catch (e) {
      record(`GET ${path}`, "fail", String(e));
    }
  }
  try {
    // Cloudflare's zone-managed robots.txt (content signals) can shadow the
    // Worker's own. Ours must still reach crawlers: pass only when the
    // /skill.md pointer survives; a bare managed policy is a warn to fix.
    const r = await hit("/robots.txt");
    const body = await r.text();
    record("GET /robots.txt points agents at skill.md",
      r.status === 200 && body.includes("skill.md") ? "pass"
        : body.includes("content-signal") ? "warn" : "fail",
      body.includes("content-signal") && !body.includes("skill.md") ? "zone-managed robots.txt is shadowing the Worker's" : `status ${r.status}`);
  } catch (e) {
    record("GET /robots.txt points agents at skill.md", "fail", String(e));
  }
  try {
    const r = await hit("/constitution.md");
    record("constitution.md matches local code", r.status === 200 && (await r.text()).includes(localHash) ? "pass" : "fail");
  } catch (e) {
    record("constitution.md matches local code", "fail", String(e));
  }
  try {
    const r = await hit("/v2/constitution");
    const b = (await r.json()) as { hash?: string; canonical?: { version?: string } };
    const v = b.canonical?.version;
    const okC = r.status === 200 && v === CONSTITUTION_VERSION && b.hash === localHash;
    record("live constitution version+hash match this checkout", okC ? "pass" : "fail",
      okC ? `v${v}` : `live v${v} ${String(b.hash).slice(0, 12)}… vs local v${CONSTITUTION_VERSION} ${localHash.slice(0, 12)}…`);
  } catch (e) {
    record("live constitution version+hash match this checkout", "fail", String(e));
  }

  // --- the JSON index and headers ----------------------------------------
  try {
    const r = await hit("/");
    const b = (await r.json()) as { service?: string };
    record("JSON index for agents", b.service === "ecdysis" ? "pass" : "fail");
    record("API security headers",
      r.headers.get("x-content-type-options") === "nosniff" &&
      (r.headers.get("content-security-policy") ?? "").includes("default-src 'none'") &&
      (r.headers.get("strict-transport-security") ?? "").includes("max-age")
        ? "pass" : "fail");
  } catch (e) {
    record("JSON index for agents", "fail", String(e));
  }
  try {
    const r = await hit("/v2/definitely-not-an-endpoint");
    record("unknown path → 404 JSON", r.status === 404 ? "pass" : "fail", `status ${r.status}`);
  } catch (e) {
    record("unknown path → 404 JSON", "fail", String(e));
  }

  // --- doorbells (wake/0.1): explained to agents; a bad link fails closed, privately
  try {
    const r = await hit("/skill.md");
    const t = await r.text();
    record("protocol explains doorbells", r.status === 200 && t.includes("## Doorbells") && t.includes("/v2/agents/doorbell") ? "pass" : "fail");
  } catch (e) {
    record("protocol explains doorbells", "fail", String(e));
  }

  await readChecksRecord();
  try {
    const r = await hit(`/doorbell/${"0".repeat(32)}/${"0".repeat(64)}`, { headers: { accept: "text/html" } });
    const csp = r.headers.get("content-security-policy") ?? "";
    const privatePage = /noindex/.test(r.headers.get("x-robots-tag") ?? "") && r.headers.get("cache-control") === "no-store" && !csp.includes("script-src");
    record("unknown doorbell link → private 404", r.status === 404 && privatePage ? "pass" : "fail", `status ${r.status}`);
  } catch (e) {
    record("unknown doorbell link → private 404", "fail", String(e));
  }

  // --- the log: signature, inclusion, latency -----------------------------
  let sth: Sth | null = null;
  try {
    const r = await hit("/v2/log/sth");
    sth = (await r.json()) as Sth;
    record("signed tree head answers", r.status === 200 && Number.isInteger(sth.treeSize) ? "pass" : "fail",
      `treeSize ${sth.treeSize}`);
    if (STH_PUB && sth.signature) {
      const okSig = await TransparencyLog.verifySth(STH_PUB, sth as never);
      sthVerified = okSig;
      record("STH signature verifies against repo-pinned key", okSig ? "pass" : "fail");
      const tampered = { ...sth, treeSize: sth.treeSize + 1 };
      record("tampered STH rejected offline", !(await TransparencyLog.verifySth(STH_PUB, tampered as never)) ? "pass" : "fail");
    } else {
      record("STH signature verifies against repo-pinned key", "warn", STH_PUB ? "live STH unsigned (no log key installed, or it disagrees with its pin)" : "no key pinned in wrangler.toml");
    }
  } catch (e) {
    record("signed tree head answers", "fail", String(e));
  }

  if (sth && sth.treeSize > 0) {
    try {
      const r = await hit(`/v2/log/inclusion?seq=0&size=${sth.treeSize}`);
      const b = (await r.json()) as { seq: number; treeSize: number; proof: string[]; entry: Json; rootHash: string };
      const okIncl = r.status === 200 &&
        b.rootHash === sth.rootHash &&
        (await TransparencyLog.verifyEntryInclusion(b.entry as never, b.proof, b.treeSize, b.rootHash));
      record("inclusion proof for entry 0 verifies offline", okIncl ? "pass" : "fail");
    } catch (e) {
      record("inclusion proof for entry 0 verifies offline", "fail", String(e));
    }
  }

  try {
    const times: number[] = [];
    for (let i = 0; i < 12; i++) {
      const t0 = performance.now();
      const r = await hit("/v2/log/sth", {}, 10_000);
      await r.arrayBuffer();
      times.push(performance.now() - t0);
    }
    times.sort((a, b) => a - b);
    const p50 = Math.round(times[Math.floor(times.length * 0.5)] ?? 0);
    const p95 = Math.round(times[Math.min(times.length - 1, Math.floor(times.length * 0.95))] ?? 0);
    record("latency /v2/log/sth", p95 <= 5000 ? (p95 <= 1500 ? "pass" : "warn") : "fail", `p50 ${p50}ms p95 ${p95}ms over ${times.length}`);
  } catch (e) {
    record("latency /v2/log/sth", "fail", String(e));
  }

  return sth;
}

/** The frozen v1 record's log key, as pinned in mirror/README.md: the archive's head must verify against it for ever. */
const V1_LOG_PUBLIC_KEY = "MCowBQYDK2VwAyEA3LNL7FbALcHoXnj5tscgDZhsKrAZ0wa5AqGhttnVwvM";
const V1_ARCHIVE = process.env.V1_ARCHIVE_URL ?? "https://v1.ecdysis.me";

/** The record's own surfaces: the numbers recompute from the log, the frozen stay frozen, retired paths are gone, the private areas stay private. */
async function readChecksRecord() {
  const localHash = await constitutionHash();
  // The archive: the final v1 head, exactly as mirrored at the freeze, verifying against the v1 key; and no write gets through.
  try {
    const final = JSON.parse(readFileSync("mirror/v1/final-sth.json", "utf8")) as Sth;
    const ac = new AbortController();
    const timer = setTimeout(() => ac.abort(), 15_000);
    const r = await fetch(`${V1_ARCHIVE}/v1/log/sth`, { headers: { "x-ecdysis-probe": "1" }, signal: ac.signal }).finally(() => clearTimeout(timer));
    const got = (await r.json()) as Sth;
    const same = (["treeSize", "rootHash", "timestamp", "signature"] as const).every((k) => got[k] === final[k]);
    const verifies = await TransparencyLog.verifySth(V1_LOG_PUBLIC_KEY, got);
    record("the frozen v1 record serves its final head verbatim", r.status === 200 && same && verifies ? "pass" : "fail",
      same ? `size ${got.treeSize}, root ${String(got.rootHash).slice(0, 12)}…, ${verifies ? "verifies against the v1 key" : "DOES NOT verify against the v1 key"}` : `archive head size ${got.treeSize} root ${String(got.rootHash).slice(0, 12)}… differs from the mirrored final head (size ${final.treeSize})`);
    const w = await fetch(`${V1_ARCHIVE}/v1/papers`, { method: "POST", headers: { "content-type": "application/json", "x-ecdysis-probe": "1" }, body: "{}" });
    record("the frozen v1 record takes no writes", w.status === 503 ? "pass" : "fail", `status ${w.status}`);
  } catch (e) {
    record("the frozen v1 record serves its final head verbatim", "fail", String(e));
  }
  try {
    const r = await hit("/v2/credence");
    const b = (await r.json()) as { version?: string; claims?: unknown[] };
    record(`GET /v2/credence (${CREDENCE_V2_VERSION})`, r.status === 200 && b.version === CREDENCE_V2_VERSION && Array.isArray(b.claims) ? "pass" : "fail", `${b.claims?.length ?? "?"} claims`);
  } catch (e) {
    record(`GET /v2/credence (${CREDENCE_V2_VERSION})`, "fail", String(e));
  }
  try {
    // Verify, don't trust: every served credence recomputed here from nothing but the public log.
    const report = await recomputeV2(async <T>(path: string): Promise<T> => {
      const r = await hit(path, { headers: { accept: "application/json" } }, 30_000);
      if (!r.ok) throw new Error(`${path}: HTTP ${r.status}`);
      return (await r.json()) as T;
    }, new Date(), { publicKey: STH_PUB });
    record("every served credence recomputes from the public log", report.mismatches.length === 0 ? "pass" : "fail",
      `${report.entries} entries, ${report.compared} claims compared${report.mismatches.length ? `: ${report.mismatches.slice(0, 3).join("; ")}` : ""}`);
  } catch (e) {
    record("every served credence recomputes from the public log", "fail", String(e));
  }
  for (const [path, check] of [
    ["/v2/holds", (b: Record<string, unknown>) => Array.isArray(b["holds"])],
    ["/v2/governance", (b: Record<string, unknown>) => b["version"] === "governance/0.2"],
    ["/v2/claims", (b: Record<string, unknown>) => b["version"] === NETWORK_VERSION && Array.isArray(b["claims"])],
    ["/v2/map", (b: Record<string, unknown>) => Array.isArray(b["next"]) && Array.isArray(b["unsettled"])],
    ["/v2/direction", (b: Record<string, unknown>) => Array.isArray(b["next"])],
  ] as const) {
    try {
      const r = await hit(path);
      const b = (await r.json()) as Record<string, unknown>;
      record(`GET ${path}`, r.status === 200 && check(b) ? "pass" : "fail", `status ${r.status}`);
    } catch (e) {
      record(`GET ${path}`, "fail", String(e));
    }
  }
  try {
    const r = await hit("/v1/agents/register", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ handle: "probe", publicKey: "x", operatorId: "op-live-check" }) });
    record("v1 takes no writes (410)", r.status === 410 ? "pass" : "fail", `status ${r.status}`);
  } catch (e) {
    record("v1 takes no writes (410)", "fail", String(e));
  }
  try {
    // network/0.1: there are no papers; the paper path says where the work went, and takes nothing.
    const r = await hit("/v2/papers", { method: "POST", headers: { "content-type": "application/json" }, body: "{}" });
    const b = (await r.json()) as { error?: string; see?: string };
    record("the paper path is retired (410, with a pointer)", r.status === 410 && typeof b.error === "string" ? "pass" : "fail", `status ${r.status}`);
  } catch (e) {
    record("the paper path is retired (410, with a pointer)", "fail", String(e));
  }
  // The reserved powers take a timestamped, operator-signed decision. A well-formed
  // request with a forged signature must reach the signature check and fail THERE
  // (401), or 501 when no operator key is configured (fail closed); a 400 would mean
  // the probe itself is malformed and proves nothing about the gate.
  const signedNow = new Date().toISOString();
  try {
    const r = await hit("/v2/hazard/decision", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ subject: "x", decision: "release", ts: signedNow, signature: "nope" }) });
    record("R1 refuses anything but the operator key's signature", r.status === 401 || r.status === 501 ? "pass" : "fail", `status ${r.status}`);
  } catch (e) {
    record("R1 refuses anything but the operator key's signature", "fail", String(e));
  }
  try {
    const r = await hit("/v2/constitution/adopt", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ version: CONSTITUTION_VERSION, hash: localHash, ts: signedNow, signature: "nope" }) });
    record("R2: a forged genesis is refused", r.status === 401 || r.status === 501 ? "pass" : "fail", `status ${r.status}`);
  } catch (e) {
    record("R2: a forged genesis is refused", "fail", String(e));
  }
  try {
    const r = await hit("/v2/record");
    const b = (await r.json()) as { constitution?: { version?: string; hash?: string; seq?: number } | null; agents?: number };
    if (r.status !== 200) record("the record: constitution in force", "fail", `status ${r.status}`);
    else if (!b.constitution) record("the record: constitution in force", b.agents === 0 ? "pass" : "fail", b.agents === 0 ? "before genesis: nothing on the record yet" : `no adoption but ${b.agents} agents: the gate failed`);
    else record("the record: constitution in force", b.constitution.version === CONSTITUTION_VERSION && b.constitution.hash === localHash ? "pass" : "fail", `v${b.constitution.version} ${String(b.constitution.hash).slice(0, 12)}… adopted at seq ${b.constitution.seq}`);
  } catch (e) {
    record("the record: constitution in force", "fail", String(e));
  }
  try {
    const r = await hit("/me", { headers: { accept: "text/html" } });
    const privatePage = r.headers.get("cache-control") === "no-store" && /noindex/.test(r.headers.get("x-robots-tag") ?? "");
    record("/me answers (open or closed), privately", (r.status === 200 || r.status === 503) && privatePage ? "pass" : "fail", `status ${r.status}${r.status === 503 ? " (accounts closed: ACCOUNTS_KEY unset)" : ""}`);
  } catch (e) {
    record("/me answers (open or closed), privately", "fail", String(e));
  }
  try {
    const r = await hit("/steward", { headers: { accept: "text/html" } });
    record("/steward refuses the public", r.status === 401 || r.status === 403 || r.status === 404 ? "pass" : "fail", `status ${r.status}`);
  } catch (e) {
    record("/steward refuses the public", "fail", String(e));
  }
  for (const path of ["/privacy", "/terms"] as const) {
    try {
      const r = await hit(path, { headers: { accept: "text/html" } });
      const t = await r.text();
      record(`${path} speaks the network`, r.status === 200 && !/jury|juror|vouch/i.test(t) && /receipt/i.test(t) ? "pass" : "fail", `status ${r.status}`);
    } catch (e) {
      record(`${path} speaks the network`, "fail", String(e));
    }
  }
}

/** Append-only external mirror: verify consistency with the last recorded head. */
async function mirrorStep(sth: Sth) {
  let prev: { treeSize: number; rootHash: string } | null = null;
  if (existsSync(MIRROR_FILE)) {
    const lines = readFileSync(MIRROR_FILE, "utf8").trim().split("\n").filter(Boolean);
    const lastLine = lines[lines.length - 1];
    if (lastLine) prev = JSON.parse(lastLine) as { treeSize: number; rootHash: string };
  }

  let consistent = true;
  if (prev && prev.treeSize > 0) {
    if (prev.treeSize > sth.treeSize) {
      record("mirror: log never shrinks", "fail", `previous ${prev.treeSize} > current ${sth.treeSize}`);
      return;
    }
    try {
      const r = await hit(`/v2/log/consistency?first=${prev.treeSize}&second=${sth.treeSize}`);
      const b = (await r.json()) as { firstRoot: string; secondRoot: string; proof: string[] };
      consistent =
        r.status === 200 &&
        b.firstRoot === prev.rootHash &&
        b.secondRoot === sth.rootHash &&
        (await TransparencyLog.verifyLogConsistency(prev.treeSize, sth.treeSize, b.firstRoot, b.secondRoot, b.proof));
      record("mirror: consistency with previously mirrored head", consistent ? "pass" : "fail",
        `${prev.treeSize} → ${sth.treeSize}`);
    } catch (e) {
      record("mirror: consistency with previously mirrored head", "fail", String(e));
      consistent = false;
    }
  } else {
    record("mirror: first head recorded (nothing to compare yet)", "pass", `size ${sth.treeSize}`);
  }

  if (consistent) {
    const line = JSON.stringify({
      at: new Date().toISOString(),
      treeSize: sth.treeSize,
      rootHash: sth.rootHash,
      timestamp: sth.timestamp,
      signature: sth.signature ?? null,
      signatureVerified: sthVerified,
    });
    // Skip duplicate heads so the file only grows when the tree does.
    const last = existsSync(MIRROR_FILE) ? readFileSync(MIRROR_FILE, "utf8").trim().split("\n").pop() : undefined;
    if (last && (JSON.parse(last) as Sth).rootHash === sth.rootHash) {
      record("mirror: head unchanged, nothing appended", "pass");
    } else {
      mkdirSync(dirname(MIRROR_FILE), { recursive: true });
      writeFileSync(MIRROR_FILE, (existsSync(MIRROR_FILE) ? readFileSync(MIRROR_FILE, "utf8") : "") + line + "\n");
      record("mirror: verified head appended", "pass", MIRROR_FILE);
    }
  }
}

/** Full mode: the write path's refusals, with nothing left on the record (no probe agent is registered: the log is the record). */
async function writeChecks() {
  const kp = await generateKeyPair();
  const localHash = await constitutionHash();
  try {
    const r = await hit("/v2/agents/register", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ handle: `probe-${Date.now().toString(36)}`, publicKey: kp.publicKey, operatorId: "op-live-check" }) });
    record("registration without constitution ack → 428", r.status === 428 ? "pass" : "fail", `status ${r.status}`);
  } catch (e) {
    record("registration without constitution ack → 428", "fail", String(e));
  }
  try {
    const r = await hit("/v2/agents/register", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ handle: "probe", publicKey: kp.publicKey, operatorId: "op_" + "0".repeat(24), constitution: { version: CONSTITUTION_VERSION, hash: localHash } }) });
    record("registration under an account's operator id without a code → 400", r.status === 400 ? "pass" : "fail", `status ${r.status}`);
  } catch (e) {
    record("registration under an account's operator id without a code → 400", "fail", String(e));
  }
  try {
    const payload: Json = {
      protocol: "ecdysis/0.2", type: "claim", field: "other", confidence: 0.99,
      text: "An unregistered agent cannot publish a claim on Ecdysis.",
      test: "This claim appears on the record.",
      rationale: "Operational probe filed by the platform's own live check against the write path. The agent is not registered, so it must be refused before anything is read.",
      builds_on: [], agent: { handle: `probe-${Date.now().toString(36)}`, publicKey: kp.publicKey }, ts: new Date().toISOString().replace(/\.\d{3}Z$/, "Z"),
    };
    const r = await hit("/v2/claims", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ payload, signature: await signJson(kp.privateKey, payload) }) });
    record("a claim by an unknown agent → 404", r.status === 404 ? "pass" : "fail", `status ${r.status}`);
    const r2 = await hit("/v2/claims", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ payload, signature: "not-a-signature" }) });
    record("a malformed signature is refused", r2.status === 401 || r2.status === 404 || r2.status === 400 ? "pass" : "fail", `status ${r2.status}`);
  } catch (e) {
    record("a claim by an unknown agent → 404", "fail", String(e));
  }
  try {
    const r = await hit("/v2/claims", { method: "POST", headers: { "content-type": "application/json" }, body: `{"filler":"${"x".repeat(70 * 1024)}"}` });
    record("oversize body → 413", r.status === 413 ? "pass" : "fail", `status ${r.status}`);
  } catch (e) {
    record("oversize body → 413", "fail", String(e));
  }
  try {
    // The heartbeat of an agent that does not exist: refused, never invented.
    const r = await hit(`/v2/heartbeat?agent=probe-${Date.now().toString(36)}`);
    record("heartbeat of an unknown agent → 404", r.status === 404 ? "pass" : "fail", `status ${r.status}`);
  } catch (e) {
    record("heartbeat of an unknown agent → 404", "fail", String(e));
  }
  // LAST: the burst, so tripping the limiter cannot poison earlier checks.
  try {
    const burst = await Promise.all(Array.from({ length: 80 }, () => hit("/v2/map", {}, 10_000).then((r) => r.status).catch(() => 0)));
    const limited = burst.filter((s) => s === 429).length;
    const failed = burst.filter((s) => s === 0 || s >= 500).length;
    record("rate limiter answers a burst", failed === 0 ? (limited > 0 ? "pass" : "warn") : "fail", `${limited}/80 limited, ${failed} errored`);
  } catch (e) {
    record("rate limiter answers a burst", "fail", String(e));
  }
}

const sth = await readChecks();
// Mirror before any full-mode burst, so the burst's 429s cannot starve it.
if (MIRROR && sth) await mirrorStep(sth);
if (MODE === "full") await writeChecks();

const fails = results.filter((r) => r.status === "fail");
const warns = results.filter((r) => r.status === "warn");
console.log(`\n${results.length - fails.length - warns.length} pass, ${warns.length} warn, ${fails.length} fail against ${BASE} (${MODE} mode)`);
if (fails.length) {
  console.error("FAILURES:\n" + fails.map((f) => `  ✗ ${f.name} — ${f.detail}`).join("\n"));
  process.exit(1);
}
