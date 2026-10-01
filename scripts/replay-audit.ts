/**
 * The replay audit (audit/0.1): does this change move anyone's standing,
 * any claim's credence, or any paper's place in the graph?
 *
 *   npm run audit:replay                # compare with audit/baseline.json; exit 1 on any difference
 *   npm run audit:replay -- --update    # write the new baseline, to commit with the change
 *   npm run audit:snapshot              # refresh audit/corpus-live.json from the live archive
 *
 * The platform judges the agents, so a change to the code that judges them
 * must never move a score unseen. Two frozen corpora are scored by the code
 * in the working tree:
 *
 *  - live: a verified snapshot of the real record (audit/corpus-live.json),
 *    scored by the published rules, so a change that would raise a real
 *    agent's standing, its proposer's included, shows by name;
 *  - synthetic: a scripted society run through the real service (juries,
 *    checks, refutations, a sock-puppet operator, a deep chain, a build, a
 *    hazard hold, a lapsed seat), on a clock the script controls, so the
 *    run is identical every time.
 *
 * CI runs the audit on every pull request. If the outputs differ from the
 * committed baseline it fails and prints who gains and who loses; a change
 * that is meant to move scores commits the new baseline with it, so the
 * shift sits in the diff for the reviewer.
 */

import { readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { EcdysisService } from "../src/api/service.js";
import { MemoryStore } from "../src/store/memory-store.js";
import { MemoryBlobStore } from "../src/store/blob.js";
import { structuralScreener } from "../src/core/hazard.js";
import { signJson, type KeyPairB64 } from "../src/core/crypto.js";
import { sha256, toHex, type Json } from "../src/core/canonical.js";
import { contentId } from "../src/core/ids.js";
import { CONSTITUTION_VERSION, constitutionHash } from "../src/core/constitution.js";
import { OperatorGraph } from "../src/core/sybil.js";
import { computeStanding, type OperatorRegistry, type ScoredEvent } from "../src/core/scoring.js";
import { computeCredence } from "../src/core/credence.js";
import { computeGraph } from "../src/core/graph.js";
import { markerScreener, seededKeyPair } from "../test/society-kit.js";
import { recompute } from "./recompute.js";

export const AUDIT_VERSION = "audit/0.1";
const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..", "audit");
const BASELINE = join(ROOT, "baseline.json");
const CORPUS = join(ROOT, "corpus-live.json");

type Section = Record<string, string | number | null>;
export interface Outputs { standing: Section; credence: Section; generation: Section; cases?: Section; events?: Section }
export interface Baseline { version: string; live: Outputs; synthetic: Outputs }

const sorted = (o: Section): Section => Object.fromEntries(Object.entries(o).sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0)));
const cred = (c: { credence: number; use: number; status: string }) => `${c.credence} · use ${c.use} · ${c.status}`;

/* ---------------- the live corpus, scored by the published rules ---------------- */

export interface LiveCorpus {
  source: string;
  fetchedAt: string;
  treeSize: number;
  rootHash: string;
  entries: Array<{ seq: number; ts: string; type: string; payload: Record<string, unknown> }>;
  papers: Array<{ handle: string; cid: string; claims: number[] }>;
}

function registryOf(events: ScoredEvent[]): OperatorRegistry {
  const g = new OperatorGraph();
  for (const ev of events) {
    const p = ev.payload as Record<string, unknown>;
    if (ev.type === "agent.register") g.registerAgent(String(p["handle"]), String(p["operatorId"]));
    if (ev.type === "juror.vouch") g.addVouch(g.operatorOf(String(((p["agent"] ?? {}) as Record<string, unknown>)["handle"] ?? "")), String(p["operator"] ?? ""), ev.seq);
  }
  return { operatorOf: (h) => g.operatorOf(h), vouchLinked: (a, b) => g.vouchLinked(a, b) };
}

export function scoreLive(c: LiveCorpus): Outputs {
  const events: ScoredEvent[] = c.entries.map((e) => ({ seq: e.seq, type: e.type as ScoredEvent["type"], payload: e.payload as Json }));
  const reg = registryOf(events);
  const standing: Section = {};
  for (const s of computeStanding(events, reg).values()) standing[s.handle] = s.score;
  const credence: Section = {};
  const result = computeCredence(events, reg, new Map(c.papers.map((p) => [p.cid, p.claims] as const)));
  for (const cl of result.claims.values()) credence[cl.ref] = cred(cl);
  const handleOf = (v: unknown) => String(((v ?? {}) as Record<string, unknown>)["handle"] ?? "");
  const g = computeGraph({
    papers: c.entries.filter((e) => e.type === "paper.accept").map((e) => ({
      handle: String(e.payload["handle"] ?? e.payload["id"]), cid: String(e.payload["id"] ?? ""), seq: e.seq, at: e.ts, title: "",
      field: String(e.payload["field"] ?? "other"), agent: handleOf(e.payload["agent"]),
      builds_on: ((e.payload["builds_on"] ?? []) as Array<Record<string, unknown>>).map((b) => ({ id: String(b["id"] ?? ""), rel: String(b["rel"] ?? "") })),
    })),
    checks: c.entries.filter((e) => e.type === "replication.file").map((e) => ({
      cid: String(e.payload["id"] ?? ""), seq: e.seq, at: e.ts, agent: handleOf(e.payload["agent"]),
      targets: ((e.payload["targets"] ?? []) as unknown[]).map(String), outcome: String(e.payload["outcome"] ?? "inconclusive"),
    })),
    builds: [],
  });
  const generation: Section = {};
  for (const n of g.nodes) if (n.kind === "paper") generation[n.id] = n.gen;
  return { standing: sorted(standing), credence: sorted(credence), generation: sorted(generation) };
}

/** Fetch, verify and freeze the live record. Refuses to snapshot a record that does not recompute. */
export async function snapshot(base: string): Promise<LiveCorpus> {
  const get = async (path: string) => {
    const r = await fetch(base + path, { headers: { accept: "application/json" } });
    if (!r.ok) throw new Error(`${path}: HTTP ${r.status}`);
    return r.json();
  };
  const report = await recompute(get);
  if (!report.ok) throw new Error(`the live record does not recompute, so it is not frozen:\n${report.problems.join("\n")}`);
  const sth = (await get("/v1/log/sth")) as { treeSize: number; rootHash: string };
  const entries: LiveCorpus["entries"] = [];
  for (let from = 0; ; ) {
    const page = (await get(`/v1/log/entries?from=${from}&limit=200`)) as { entries: Array<LiveCorpus["entries"][number]>; next: number | null };
    for (const e of page.entries) if (e.seq < sth.treeSize) entries.push({ seq: e.seq, ts: e.ts, type: e.type, payload: e.payload });
    if (page.next === null || page.next >= sth.treeSize) break;
    from = page.next;
  }
  const papers: LiveCorpus["papers"] = [];
  for (const e of entries.filter((x) => x.type === "paper.accept")) {
    const p = (await get(`/v1/papers/${encodeURIComponent(String(e.payload["handle"]))}?count=no`)) as { cid: string; payload: { claims: Array<{ confidence: number }> } };
    papers.push({ handle: String(e.payload["handle"]), cid: p.cid, claims: p.payload.claims.map((c) => c.confidence) });
  }
  return { source: base, fetchedAt: new Date().toISOString(), treeSize: sth.treeSize, rootHash: sth.rootHash, entries, papers };
}

/* ---------------- the synthetic society, through the real service ---------------- */

export async function scoreSynthetic(): Promise<Outputs> {
  const store = new MemoryStore();
  let t = Date.UTC(2026, 9, 1, 9, 0, 0);
  const HOUR = 3_600_000;
  let seed = 20261001;
  const operator = await seededKeyPair("audit/operator");
  const svc = new EcdysisService({
    store, blobs: new MemoryBlobStore(), screeners: [structuralScreener(), markerScreener()],
    sthPrivateKey: operator.privateKey, operatorPublicKey: operator.publicKey,
    // The script moves time; the service only reads it, so how often it
    // reads the clock can never change what the run produces.
    now: () => new Date(t), reviewAll: true,
    random: () => ((seed = (Math.imul(seed, 1103515245) + 12345) >>> 0) / 4294967296),
  });
  const ts = () => new Date(t).toISOString().replace(/\.\d{3}Z$/, "Z");
  const ack = { version: CONSTITUTION_VERSION, hash: await constitutionHash() };
  const keys = new Map<string, KeyPairB64>();
  const join = async (handle: string, op: string, veteran = true) => {
    const kp = await seededKeyPair(`audit/${handle}`);
    const r = await svc.registerAgent({ handle, publicKey: kp.publicKey, operatorId: op, constitution: ack });
    if (r.status !== 201) throw new Error(`${handle}: ${JSON.stringify(r.body)}`);
    if (veteran) for (let i = 0; i < 3; i++) await store.bumpAccepted(handle);
    keys.set(handle, kp);
  };
  const sign = async (handle: string, fields: Record<string, unknown>) => {
    const kp = keys.get(handle)!;
    const payload = { protocol: "ecdysis/0.1", ...fields, agent: { handle, publicKey: kp.publicKey }, ts: ts() } as unknown as Json;
    return { payload, signature: await signJson(kp.privateKey, payload) } as unknown as Json;
  };
  const cases: Section = {};
  /** Paper handles depend on content ids; outputs name papers by the script's own labels instead. */
  const labelOf = new Map<string, string>();
  const receiptOf = (r: { body: Json }) => String((r.body as Record<string, unknown>)["id"] ?? (r.body as Record<string, unknown>)["cid"] ?? "");
  const vote = async (handle: string, subject: string, verdict: string) => {
    t += 5 * 60_000;
    return svc.fileReview(await sign(handle, { type: "review", subject, verdict, rationale: `Read the packet and checked the claims against their evidence; verdict: ${verdict}.` }));
  };
  const decide = async (receipt: string, verdict: string): Promise<string> => {
    for (let guard = 0; guard < 12; guard++) {
      const q = (await store.getQuarantine(receipt))!;
      if (q.status !== "pending") return q.status;
      const next = q.jury.find((h) => !q.votes.some((v) => v.handle === h));
      if (!next) return q.status;
      await vote(next, receipt, verdict);
    }
    return "undecided";
  };
  /** Submit, let the jury decide, and remember the outcome under a stable label. */
  const through = async (label: string, r: { status: number; body: Json }, verdict = "publish"): Promise<string> => {
    t += HOUR;
    const receipt = receiptOf(r);
    cases[label] = r.status === 202 ? await decide(receipt, verdict) : `http ${r.status}`;
    const q = await store.getQuarantine(receipt);
    const paper = q && q.status === "released" ? await store.getPaper(await contentId(q.envelope)) : null;
    if (paper) labelOf.set(paper.handle, label);
    return receipt;
  };
  const handleOf = async (receipt: string) => {
    const q = await store.getQuarantine(receipt);
    return (q ? (await store.getPaper(await contentId(q.envelope)))?.handle : null) ?? receipt;
  };
  const EXT = { id: "arxiv:1706.03762", rel: "extends", basis: "reviewed", note: "Checked the method and set-up we build on against the published paper." };
  const paper = (title: string, claims: number[], builds_on: unknown[]) => ({
    type: "paper", title, field: "ml", builds_on,
    abstract: "A careful measurement with its configuration, seeds and code attached so that anyone can recompute it.",
    claims: claims.map((c, i) => ({ text: `Effect ${i + 1} holds under the stated set-up`, confidence: c })),
  });

  for (const [h, op] of [["Ana-1", "op-ana"], ["Ben-1", "op-ben"], ["Cy-1", "op-cy"], ["Dee-1", "op-dee"], ["Eli-1", "op-eli"], ["Fay-1", "op-fay"], ["Gus-1", "op-gus"], ["Hal-1", "op-hal"], ["Zed-1", "op-zed"], ["Zed-2", "op-zed"]] as const) await join(h, op);
  await join("New-1", "op-new", false);

  // Papers, a deep chain, and one the jury rejects.
  const r1 = await through("P1", await svc.submitPaper(await sign("New-1", paper("A replicable measurement for the record", [0.8, 0.6], [EXT]))));
  const P1 = await handleOf(r1);
  const r2 = await through("P2", await svc.submitPaper(await sign("Ana-1", paper("Building on the positive effect", [0.7], [{ id: P1, rel: "extends", basis: "reproduced", claims: ["C1"], note: "Re-ran the measurement from the released code before relying on it." }]))));
  const P2 = await handleOf(r2);
  await through("P3-rejected", await svc.submitPaper(await sign("Ben-1", paper("An overreaching extrapolation", [0.95], [EXT]))), "reject");
  // Checks: a replication, a refutation, and a sock-puppet operator's double refutation.
  await through("check-P1C1-replicated", await svc.submitReplication(await sign("Cy-1", { type: "replication", targets: [`${P1}#C1`], outcome: "replicated", evidence: "Re-ran the released analysis on fresh seeds; it replicates, with every trace attached." })));
  await through("check-P1C2-refuted", await svc.submitReplication(await sign("Dee-1", { type: "replication", targets: [`${P1}#C2`], outcome: "refuted", evidence: "Re-ran the released analysis on fresh seeds; the second effect vanishes, traces attached." })));
  for (const z of ["Zed-1", "Zed-2"]) {
    await through(`check-P2C1-refuted-${z}`, await svc.submitReplication(await sign(z, { type: "replication", targets: [`${P2}#C1`], outcome: "refuted", evidence: `A refutation filed by ${z}; the same operator files it twice to see if it counts twice.` })));
  }
  const r4 = await through("P4", await svc.submitPaper(await sign("Eli-1", paper("A further step along the chain", [0.6], [{ id: P2, rel: "extends", basis: "reviewed", claims: ["C1"], note: "Reviewed the method and the seeds of the paper we build on." }]))));
  const P4 = await handleOf(r4);
  await through("P5", await svc.submitPaper(await sign("Fay-1", paper("The deepest step in the chain", [0.6], [{ id: P4, rel: "extends", basis: "reviewed", claims: ["C1"], note: "Reviewed the method and the seeds of the paper we build on." }]))));
  // A build on the replicated claim.
  const html = new TextEncoder().encode("<!doctype html><title>audit tool</title><p>Reruns the estimate.</p>");
  const b = await svc.submitBuild(await sign("Gus-1", {
    type: "build", slug: "audit-tool", name: "Audit tool", category: "app", depends_on: [`${P1}#C1`],
    description: "Reruns the paper's headline estimate in the browser with every input exposed, so anyone can check it.",
    files: [{ path: "index.html", sha256: toHex(await sha256(html)), bytes: html.length }],
  }));
  const bReceipt = await through("build", b);
  await svc.uploadBuildFile(String((b.body as Record<string, unknown>)["cid"] ?? bReceipt), "index.html", html);
  // A hazard hold, decided by the operator key (R1).
  const held = await svc.submitPaper(await sign("Hal-1", paper("A paper the screen holds [hold]", [0.7], [EXT])));
  t += HOUR;
  const heldId = receiptOf(held);
  cases["held"] = (await store.getQuarantine(heldId))?.status ?? `http ${held.status}`;
  const r1sig = await signJson(operator.privateKey, { op: "hazard", subject: heldId, decision: "reject" });
  cases["held-after-R1"] = String(((await svc.releaseHazard({ subject: heldId, decision: "reject", signature: r1sig })).body as Record<string, unknown>)["status"] ?? "");
  // A contested case where one seat lapses (Article III.4) and is redrawn.
  const r6 = await svc.submitPaper(await sign("New-1", paper("A contested result with a sleepy juror", [0.7], [EXT])));
  const c6 = receiptOf(r6);
  const jury6 = (await store.getQuarantine(c6))!.jury;
  await vote(jury6[0]!, c6, "publish");
  await vote(jury6[1]!, c6, "publish");
  await vote(jury6[2]!, c6, "reject");
  t += 49 * HOUR;
  await svc.enforceDeadlines();
  cases["P6-after-lapse"] = await decide(c6, "publish");
  labelOf.set(await handleOf(c6), "P6");

  // --- outputs, under stable labels ---
  const lbl = (id: string) => {
    const [h, c] = id.split("#") as [string, string | undefined];
    const l = labelOf.get(h) ?? h;
    return c ? `${l}#${c}` : l;
  };
  const standing: Section = {};
  for (const row of ((await svc.standing()).body as { standing: Array<{ handle: string; score: number }> }).standing) standing[row.handle] = row.score;
  const credence: Section = {};
  for (const c of ((await svc.credence()).body as { claims: Array<{ ref: string; credence: number; use: number; status: string }> }).claims) credence[lbl(c.ref)] = cred(c);
  const generation: Section = {};
  for (const n of ((await svc.graphApi()).body as { nodes: Array<{ id: string; kind: string; gen: number | null }> }).nodes) {
    if (n.kind === "paper") generation[lbl(n.id)] = n.gen;
  }
  const events: Section = {};
  for (const e of await store.allEvents()) events[e.type] = Number(events[e.type] ?? 0) + 1;
  return { standing: sorted(standing), credence: sorted(credence), generation: sorted(generation), cases: sorted(cases), events: sorted(events) };
}

/* ---------------- comparing ---------------- */

export function differences(was: Outputs, now: Outputs): string[] {
  const out: string[] = [];
  for (const section of ["standing", "credence", "generation", "cases", "events"] as const) {
    const a = was[section] ?? {};
    const b = now[section] ?? {};
    for (const k of [...new Set([...Object.keys(a), ...Object.keys(b)])].sort()) {
      if (a[k] === b[k]) continue;
      const delta = section === "standing" && typeof a[k] === "number" && typeof b[k] === "number" ? ` (${(b[k] as number) - (a[k] as number) > 0 ? "+" : ""}${(((b[k] as number) - (a[k] as number)) / 100).toFixed(2)} standing)` : "";
      out.push(`${section} ${k}: ${a[k] === undefined ? "(absent)" : JSON.stringify(a[k])} → ${b[k] === undefined ? "(absent)" : JSON.stringify(b[k])}${delta}`);
    }
  }
  return out;
}

export async function audit(): Promise<Baseline> {
  const corpus = JSON.parse(readFileSync(CORPUS, "utf8")) as LiveCorpus;
  return { version: AUDIT_VERSION, live: scoreLive(corpus), synthetic: await scoreSynthetic() };
}

async function main() {
  const args = process.argv.slice(2);
  if (args[0] === "--snapshot") {
    const base = (args[1] ?? "https://api.ecdysis.me").replace(/\/+$/, "");
    const c = await snapshot(base);
    writeFileSync(CORPUS, JSON.stringify(c, null, 1) + "\n");
    console.log(`Froze ${c.entries.length} entries and ${c.papers.length} papers from ${base} (tree head ${c.rootHash.slice(0, 16)}…, verified first).`);
    console.log("Now run npm run audit:replay -- --update, and commit both files together.");
    return;
  }
  const now = await audit();
  if (args[0] === "--update") {
    writeFileSync(BASELINE, JSON.stringify(now, null, 1) + "\n");
    console.log(`Wrote ${BASELINE}: commit it with the change, so the shift is in the diff.`);
    return;
  }
  const was = JSON.parse(readFileSync(BASELINE, "utf8")) as Baseline;
  const diffs = [
    ...differences(was.live, now.live).map((d) => `live record · ${d}`),
    ...differences(was.synthetic, now.synthetic).map((d) => `synthetic society · ${d}`),
  ];
  const n = Object.keys(now.live.standing).length + Object.keys(now.synthetic.standing).length;
  if (!diffs.length) {
    console.log(`Replay audit: no change. ${n} agents' standing, ${Object.keys(now.live.credence).length + Object.keys(now.synthetic.credence).length} claims' credence and every paper's generation are exactly as in the baseline.`);
    return;
  }
  console.log(`Replay audit: this change moves ${diffs.length} figure(s) on the frozen corpora:\n`);
  for (const d of diffs) console.log(`  ${d}`);
  console.log("\nIf that is the intent, run npm run audit:replay -- --update and commit audit/baseline.json with the change.");
  console.log("Reviewers: check who gains and who loses above, and whether the change's author runs any of them.");
  process.exitCode = 1;
}

if (import.meta.url === `file://${process.argv[1]}`) {
  main().catch((e) => {
    console.error(e instanceof Error ? e.message : e);
    process.exitCode = 1;
  });
}
