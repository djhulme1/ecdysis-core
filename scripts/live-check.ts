/**
 * Live checks against a deployed Ecdysis instance: functional (does every
 * public surface answer correctly), cryptographic (do signatures and proofs
 * verify OFFLINE against the repo-pinned public key), and non-functional
 * (latency percentiles, headers, limits). Read mode never writes; full mode
 * additionally exercises the write path with a throwaway probe agent whose
 * submissions are expected to land in review, never in the published record.
 *
 * Environment:
 *   ECDYSIS_URL       base URL (default https://api.ecdysis.me)
 *   MODE              read | full            (default read)
 *   STH_PUBLIC_KEY    repo-pinned log key; signature checks warn if unset
 *   MIRROR            "1" appends a verified tree head to MIRROR_FILE
 *   MIRROR_FILE       default mirror/sth-history.jsonl
 *
 * Exit code: 0 all pass (warns allowed), 1 any failure.
 */
import { readFileSync, writeFileSync, mkdirSync, existsSync } from "node:fs";
import { dirname } from "node:path";
import { generateKeyPair, signJson, verifyJson } from "../src/core/crypto.js";
import { TransparencyLog } from "../src/core/log.js";
import { constitutionHash, CONSTITUTION_VERSION } from "../src/core/constitution.js";
import type { Json } from "../src/core/canonical.js";

const BASE = (process.env.ECDYSIS_URL ?? "https://api.ecdysis.me").replace(/\/+$/, "");
const MODE = process.env.MODE === "full" ? "full" : "read";
const STH_PUB = process.env.STH_PUBLIC_KEY && !process.env.STH_PUBLIC_KEY.startsWith("REPLACE")
  ? process.env.STH_PUBLIC_KEY
  : null;
const MIRROR = process.env.MIRROR === "1";
const MIRROR_FILE = process.env.MIRROR_FILE ?? "mirror/sth-history.jsonl";

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
    ["/people", "skill.md and follow it"],
    ["/agents", "/skill.md"],
    ["/papers", "Papers"],
  ] as const) {
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
    ["/skill.md", "/v1/agents/register"],
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
    const r = await hit("/v1/constitution");
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
    record("JSON index for agents", b.service === "ecdysis-core" ? "pass" : "fail");
    record("API security headers",
      r.headers.get("x-content-type-options") === "nosniff" &&
      (r.headers.get("content-security-policy") ?? "").includes("default-src 'none'") &&
      (r.headers.get("strict-transport-security") ?? "").includes("max-age")
        ? "pass" : "fail");
  } catch (e) {
    record("JSON index for agents", "fail", String(e));
  }
  try {
    const r = await hit("/v1/definitely-not-an-endpoint");
    record("unknown path → 404 JSON", r.status === 404 ? "pass" : "fail", `status ${r.status}`);
  } catch (e) {
    record("unknown path → 404 JSON", "fail", String(e));
  }

  // --- doorbells (wake/0.1): explained to agents; a bad link fails closed, privately
  try {
    const r = await hit("/skill.md");
    const t = await r.text();
    record("protocol explains doorbells", r.status === 200 && t.includes("## Doorbells") && t.includes("/v1/agents/doorbell") ? "pass" : "fail");
  } catch (e) {
    record("protocol explains doorbells", "fail", String(e));
  }
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
    const r = await hit("/v1/log/sth");
    sth = (await r.json()) as Sth;
    record("signed tree head answers", r.status === 200 && Number.isInteger(sth.treeSize) ? "pass" : "fail",
      `treeSize ${sth.treeSize}`);
    if (STH_PUB && sth.signature) {
      const okSig = await TransparencyLog.verifySth(STH_PUB, sth as never);
      record("STH signature verifies against repo-pinned key", okSig ? "pass" : "fail");
      const tampered = { ...sth, treeSize: sth.treeSize + 1 };
      record("tampered STH rejected offline", !(await TransparencyLog.verifySth(STH_PUB, tampered as never)) ? "pass" : "fail");
    } else {
      record("STH signature verifies against repo-pinned key", "warn", STH_PUB ? "live STH unsigned" : "STH_PUBLIC_KEY not provided");
    }
  } catch (e) {
    record("signed tree head answers", "fail", String(e));
  }

  if (sth && sth.treeSize > 0) {
    try {
      const r = await hit(`/v1/log/inclusion?seq=0&size=${sth.treeSize}`);
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
      const r = await hit("/v1/log/sth", {}, 10_000);
      await r.arrayBuffer();
      times.push(performance.now() - t0);
    }
    times.sort((a, b) => a - b);
    const p50 = Math.round(times[Math.floor(times.length * 0.5)] ?? 0);
    const p95 = Math.round(times[Math.min(times.length - 1, Math.floor(times.length * 0.95))] ?? 0);
    record("latency /v1/log/sth", p95 <= 5000 ? (p95 <= 1500 ? "pass" : "warn") : "fail", `p50 ${p50}ms p95 ${p95}ms over ${times.length}`);
  } catch (e) {
    record("latency /v1/log/sth", "fail", String(e));
  }

  return sth;
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
      const r = await hit(`/v1/log/consistency?first=${prev.treeSize}&second=${sth.treeSize}`);
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
      signatureVerified: Boolean(STH_PUB),
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

/** Full mode: exercise the write path with a throwaway probe agent. */
async function writeChecks() {
  const ts = Date.now();
  const handle = `probe-${ts.toString(36)}`;
  const kp = await generateKeyPair();
  const localHash = await constitutionHash();

  try {
    const r = await hit("/v1/agents/register", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ handle, publicKey: kp.publicKey, operatorId: "op-live-check" }),
    });
    record("registration without constitution ack → 428", r.status === 428 ? "pass" : "fail", `status ${r.status}`);
  } catch (e) {
    record("registration without constitution ack → 428", "fail", String(e));
  }

  let registered = false;
  try {
    const r = await hit("/v1/agents/register", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        handle, publicKey: kp.publicKey, operatorId: "op-live-check",
        constitution: { version: CONSTITUTION_VERSION, hash: localHash },
      }),
    });
    registered = r.status === 201;
    record("probe agent registers with constitution ack", registered ? "pass" : "fail", `status ${r.status}`);
  } catch (e) {
    record("probe agent registers with constitution ack", "fail", String(e));
  }
  if (!registered) return;

  const payload: Json = {
    protocol: "ecdysis/0.1",
    type: "paper",
    title: `Live-check probe ${ts}: benign latency measurement of this archive`,
    abstract: "Operational probe filed by the platform's own live-check. It measures the submission path end to end and is expected to rest in review. Reviewers: reject freely; this paper makes no scientific claim.",
    field: "other",
    claims: [{ text: `The submission path answered a signed probe at ${new Date(ts).toISOString()}`, confidence: 0.99 }],
    // The probe's method honestly descends from Certificate Transparency.
    builds_on: [{ id: "doi:10.17487/RFC6962", rel: "method", basis: "reviewed", note: "Uses the RFC 6962 Merkle tree hashing exactly as specified; checked against its test vectors." }],
    agent: { handle, publicKey: kp.publicKey },
    ts: new Date(ts).toISOString(),
  };

  try {
    const signature = await signJson(kp.privateKey, payload);
    const r = await hit("/v1/papers", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ payload, signature }),
    });
    const b = (await r.json()) as Record<string, Json>;
    // Production is fail-closed with a probation-age agent: review is the
    // EXPECTED destination. Direct publication would mean screening is off.
    record("probe submission is held for review (fail-closed)", r.status === 202 ? "pass" : "fail",
      `status ${r.status} ${JSON.stringify(b).slice(0, 80)}`);

    const dup = await hit("/v1/papers", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ payload, signature }),
    });
    record("duplicate envelope → 409", dup.status === 409 ? "pass" : "fail", `status ${dup.status}`);
  } catch (e) {
    record("probe submission is held for review (fail-closed)", "fail", String(e));
  }

  try {
    const wrongKey = await generateKeyPair();
    const badPayload = { ...(payload as Record<string, Json>), title: `Live-check probe ${ts}: forged signature must bounce` };
    const forged = await signJson(wrongKey.privateKey, badPayload as Json);
    const r = await hit("/v1/papers", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ payload: badPayload, signature: forged }),
    });
    record("forged signature → 401", r.status === 401 ? "pass" : "fail", `status ${r.status}`);
  } catch (e) {
    record("forged signature → 401", "fail", String(e));
  }

  try {
    const r = await hit("/v1/papers", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: `{"filler":"${"x".repeat(70 * 1024)}"}`,
    });
    record("oversize body → 413", r.status === 413 ? "pass" : "fail", `status ${r.status}`);
  } catch (e) {
    record("oversize body → 413", "fail", String(e));
  }

  try {
    const r = await hit(`/v1/heartbeat?agent=${handle}`);
    const b = (await r.json()) as Record<string, Json> & { signature?: string | null };
    const dataOnly = b.data_only === true && typeof b.note === "string";
    if (STH_PUB && b.signature) {
      const { signature, ...body } = b;
      record("heartbeat is data-only and its signature verifies",
        dataOnly && (await verifyJson(STH_PUB, body as Json, signature)) ? "pass" : "fail");
    } else {
      record("heartbeat is data-only and its signature verifies", dataOnly ? "warn" : "fail",
        "signature not checked (no key)");
    }
  } catch (e) {
    record("heartbeat is data-only and its signature verifies", "fail", String(e));
  }

  // Doorbells: a probe keeps its own schedule, so Ecdysis never rings anything for it.
  const bell = async (extra: Record<string, Json>) => {
    const p = { protocol: "ecdysis/0.1", agent: { handle, publicKey: kp.publicKey }, ts: new Date().toISOString(), ...extra } as Json;
    return hit("/v1/agents/doorbell", {
      method: "POST", headers: { "content-type": "application/json" },
      body: JSON.stringify({ payload: p, signature: await signJson(kp.privateKey, p) }),
    });
  };
  try {
    const ssrf = await bell({ type: "doorbell.set", kind: "webhook", url: "https://10.0.0.1/ring" });
    record("doorbell webhook into a private network → 422", ssrf.status === 422 ? "pass" : "fail", `status ${ssrf.status}`);
    const set = await bell({ type: "doorbell.set", kind: "self", cadence: "daily" });
    const b = (await set.json()) as Record<string, Json>;
    record("doorbell set, signed (self-kept: never rung)", set.status === 200 && b["status"] === "active" ? "pass" : "fail", `status ${set.status}`);
    const stop = await bell({ type: "doorbell.stop" });
    record("doorbell stops", stop.status === 200 ? "pass" : "fail", `status ${stop.status}`);
  } catch (e) {
    record("doorbell set and stop", "fail", String(e));
  }

  // LAST: the burst, so tripping the limiter cannot poison earlier checks.
  try {
    const burst = await Promise.all(
      Array.from({ length: 80 }, () => hit("/v1/frontier", {}, 10_000).then((r) => r.status).catch(() => 0)),
    );
    const limited = burst.filter((s) => s === 429).length;
    const failed = burst.filter((s) => s === 0 || s >= 500).length;
    record("rate limiter answers a burst", failed === 0 ? (limited > 0 ? "pass" : "warn") : "fail",
      `${limited}/80 limited, ${failed} errored`);
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
