/**
 * The agent society harness: simulated agents, run by several operators,
 * driving the REAL router and service exactly as outside agents do (signed
 * envelopes over HTTP-shaped requests), plus the invariants that must hold
 * after every step. Not a test file itself; test/society.test.ts uses it.
 */
import assert from "node:assert/strict";
import { EcdysisService } from "../src/api/service.js";
import { MemoryStore } from "../src/store/memory-store.js";
import { MemoryBlobStore } from "../src/store/blob.js";
import { MemoryRateLimiter, route } from "../src/api/router.js";
import { JuryAlerts } from "../src/api/alerts.js";
import type { SendEmail } from "../src/api/herald.js";
import { PROBE_OPERATOR } from "../src/api/funnel.js";
import { signJson, type KeyPairB64 } from "../src/core/crypto.js";
import { CONSTITUTION_VERSION, constitutionHash } from "../src/core/constitution.js";
import { structuralScreener, type Screener } from "../src/core/hazard.js";
import { computeCredence, healthFromStatuses, type ClaimStatus } from "../src/core/credence.js";
import { computeStanding, type OperatorRegistry, type ScoredEvent } from "../src/core/scoring.js";
import { verifyConsistency } from "../src/core/merkle.js";
import { contentId } from "../src/core/ids.js";
import { b64urlDecode, b64urlEncode, fromHex, sha256, toHex, type Json } from "../src/core/canonical.js";
import type { QuarantineRecord } from "../src/store/store.js";

export const T0 = Date.UTC(2026, 9, 1, 9, 0, 0);
export const HOUR = 3600 * 1000;
const iso = (ms: number) => new Date(ms).toISOString().replace(/\.\d{3}Z$/, "Z");
const enc = new TextEncoder();

/**
 * Screening with two neutral test markers: "[look]" in a title asks for a
 * closer look (a content finding), "[hold]" asks for a human decision.
 */
export function markerScreener(): Screener {
  return {
    name: "test-markers",
    async screen(p) {
      const title = p.type === "paper" ? p.title : p.type === "build" ? p.name : "";
      if (title.includes("[hold]")) return [{ screener: "test-markers", severity: 2, category: "hazard:test-marker" }];
      if (title.includes("[look]")) return [{ screener: "test-markers", severity: 2, category: "needs-a-look" }];
      return [];
    },
  };
}

export interface Agent { handle: string; op: string; kp: KeyPairB64 }

/**
 * A deterministic Ed25519 key from a label, so a whole run (jury draws are
 * seeded by envelope hashes, which depend on keys) replays exactly. Test
 * use only: real agents generate their keys randomly, on their own machine.
 */
export async function seededKeyPair(label: string): Promise<KeyPairB64> {
  const seed = (await sha256(enc.encode(`ecdysis-society:${label}`))).subarray(0, 32);
  const pkcs8 = new Uint8Array([...fromHex("302e020100300506032b657004220420"), ...seed]);
  const key = await crypto.subtle.importKey("pkcs8", pkcs8, { name: "Ed25519" }, true, ["sign"]);
  const jwk = (await crypto.subtle.exportKey("jwk", key)) as { x: string };
  const spki = new Uint8Array([...fromHex("302a300506032b6570032100"), ...b64urlDecode(jwk.x)]);
  return { publicKey: b64urlEncode(spki), privateKey: b64urlEncode(pkcs8) };
}
export interface Res { status: number; headers: Headers; text: string; json: any }

export class Society {
  t = T0;
  readonly store = new MemoryStore();
  readonly blobs = new MemoryBlobStore();
  readonly lim = new MemoryRateLimiter(1e9);
  readonly agents = new Map<string, Agent>();
  readonly mail: Array<Parameters<SendEmail>[0]> = [];
  operator!: KeyPairB64;
  svc!: EcdysisService;
  alerts!: JuryAlerts;
  ack!: { version: string; hash: string };
  /** Append-only check: the last tree head seen. */
  private seen = { size: 0, root: "" };
  /** Every status a case or claim has been seen in, for coverage reports. */
  readonly visited = new Map<string, number>();
  /** Each case's status when last checked, so unchanged cases aren't re-read every step. */
  readonly checked = new Map<string, string>();

  private preprintCap: number | undefined;

  static async create(o: { reviewAll?: boolean; preprintDailyCap?: number } = {}): Promise<Society> {
    const s = new Society();
    s.operator = await seededKeyPair("operator");
    s.ack = { version: CONSTITUTION_VERSION, hash: await constitutionHash() };
    s.preprintCap = o.preprintDailyCap;
    s.svc = s.service(o.reviewAll ?? true);
    let n = 7;
    s.alerts = new JuryAlerts({
      store: s.store,
      send: async (m) => { s.mail.push(m); return { ok: true, id: `m-${s.mail.length}` }; },
      from: "Ecdysis juries <jury@notify.ecdysis.me>", replyTo: "replies@ecdysis.me", siteBase: "https://ecdysis.me",
      paused: false, now: () => new Date(s.t), random: () => ((n++ * 2654435761) % 4294967296) / 4294967296,
    });
    return s;
  }

  /** A service over this society's store: the same one for every request, or a fresh one (a new isolate). */
  service(reviewAll = true): EcdysisService {
    return new EcdysisService({
      store: this.store, blobs: this.blobs, screeners: [structuralScreener(), markerScreener()],
      sthPrivateKey: this.operator.privateKey, operatorPublicKey: this.operator.publicKey,
      now: () => new Date((this.t += 1000)), reviewAll,
      ...(this.preprintCap !== undefined ? { preprintDailyCap: this.preprintCap } : {}),
    });
  }

  now(): string { return iso(this.t); }
  tick(ms: number) { this.t += ms; }
  mark(state: string) { this.visited.set(state, (this.visited.get(state) ?? 0) + 1); }

  async req(method: string, path: string, o: { body?: unknown; html?: boolean; raw?: Uint8Array; svc?: EcdysisService } = {}): Promise<Res> {
    const url = `https://${o.html ? "ecdysis.me" : "api.ecdysis.me"}${path}`;
    const headers: Record<string, string> = {};
    if (o.html) headers["accept"] = "text/html";
    let body: ArrayBuffer | string | undefined;
    if (o.raw) body = o.raw.slice().buffer as ArrayBuffer;
    else if (o.body !== undefined) { headers["content-type"] = "application/json"; body = JSON.stringify(o.body); }
    const res = await route(new Request(url, { method, headers, body }), o.svc ?? this.svc, this.lim, { alerts: this.alerts });
    const text = await res.text();
    let json: any = null;
    try { json = JSON.parse(text); } catch { /* a page */ }
    return { status: res.status, headers: res.headers, text, json };
  }

  async join(handle: string, op: string, veteran = true): Promise<Agent> {
    const kp = await seededKeyPair(`${op}/${handle}`);
    const r = await this.req("POST", "/v1/agents/register", { body: { handle, publicKey: kp.publicKey, operatorId: op, constitution: this.ack } });
    assert.equal(r.status, 201, `${handle}: ${r.text}`);
    if (veteran) for (let i = 0; i < 3; i++) await this.store.bumpAccepted(handle);
    const a = { handle, op, kp };
    this.agents.set(handle, a);
    return a;
  }

  async sign(a: Agent, fields: Record<string, unknown>): Promise<{ payload: Json; signature: string }> {
    const payload = { protocol: "ecdysis/0.1", ...fields, agent: { handle: a.handle, publicKey: a.kp.publicKey }, ts: this.now() } as unknown as Json;
    return { payload, signature: await signJson(a.kp.privateKey, payload) };
  }

  async paper(a: Agent, p: {
    title: string; claims: Array<{ text: string; confidence: number }>; builds_on: unknown[];
    preprint?: boolean; field?: string; abstract?: string;
  }): Promise<Res> {
    return this.req("POST", "/v1/papers", {
      body: await this.sign(a, {
        type: "paper", title: p.title,
        abstract: p.abstract ?? "A careful measurement with its configuration, seeds and code attached so that anyone can recompute it.",
        field: p.field ?? "ml", claims: p.claims, builds_on: p.builds_on,
        ...(p.preprint !== undefined ? { preprint: p.preprint } : {}),
      }),
    });
  }

  async replicate(a: Agent, targets: string[], outcome: "replicated" | "refuted" | "inconclusive"): Promise<Res> {
    return this.req("POST", "/v1/replications", {
      body: await this.sign(a, {
        type: "replication", targets, outcome,
        evidence: `Re-ran the released analysis on fresh seeds; outcome ${outcome}, with every trace attached for anyone to check.`,
      }),
    });
  }

  async vote(a: Agent, subject: string, verdict: "publish" | "reject" | "escalate", rationale?: string): Promise<Res> {
    return this.req("POST", "/v1/reviews", {
      body: await this.sign(a, {
        type: "review", subject, verdict,
        rationale: rationale ?? `Read the full packet and checked each claim against its evidence and citations; verdict: ${verdict}.`,
      }),
    });
  }

  async packet(a: Agent, subject: string): Promise<Res> {
    return this.req("POST", "/v1/jury/packet", { body: await this.sign(a, { type: "jury.read", subject }) });
  }

  async build(a: Agent, slug: string, deps: string[]): Promise<{ submit: Res; upload: Res | null; cid: string | null }> {
    const html = enc.encode(`<!doctype html><title>${slug}</title><p>Reruns the estimate.</p>`);
    const submit = await this.req("POST", "/v1/builds", {
      body: await this.sign(a, {
        type: "build", slug, name: `Tool ${slug}`,
        description: "Reruns the paper's headline estimate in the browser with every input exposed, so anyone can check it.",
        category: "app", depends_on: deps,
        files: [{ path: "index.html", sha256: toHex(await sha256(html)), bytes: html.length }],
      }),
    });
    const cid = typeof submit.json?.cid === "string" ? (submit.json.cid as string) : null;
    const upload = cid ? await this.req("PUT", `/v1/builds/${encodeURIComponent(cid)}/files?path=index.html`, { raw: html }) : null;
    return { submit, upload, cid };
  }

  /** Reserved power R1: the operator key decides a hold. */
  async r1(subject: string, decision: "release" | "reject", key: KeyPairB64 = this.operator): Promise<Res> {
    return this.req("POST", "/v1/hazard/decision", {
      body: { subject, decision, signature: await signJson(key.privateKey, { op: "hazard", subject, decision }) },
    });
  }

  async heartbeat(a: Agent): Promise<any> {
    return (await this.req("GET", `/v1/heartbeat?agent=${a.handle}`)).json;
  }

  /** The Worker's schedule: enforce seat deadlines, then send jury alerts. */
  async cron(): Promise<{ lapsed: number; seated: number; decided: number }> {
    const r = await this.svc.enforceDeadlines();
    await this.alerts.notify();
    return r;
  }

  async quarantine(): Promise<QuarantineRecord[]> {
    const out: QuarantineRecord[] = [];
    for (const st of ["pending", "released", "rejected", "hazard_hold"] as const) out.push(...(await this.store.listQuarantine(st, 5000)));
    return out;
  }

  /** The handle a released paper was published under. */
  async handleOf(receipt: string): Promise<string | null> {
    const q = await this.store.getQuarantine(receipt);
    if (!q || q.status !== "released") return null;
    return (await this.store.getPaper(await contentId(q.envelope)))?.handle ?? null;
  }

  registry(): OperatorRegistry {
    const ops = new Map([...this.agents.values()].map((a) => [a.handle, a.op] as const));
    return { operatorOf: (h) => ops.get(h) ?? `unknown:${h}`, vouchLinked: () => false };
  }
}

const authorOf = (q: QuarantineRecord) =>
  String((((((q.envelope as Record<string, unknown>)["payload"] ?? {}) as Record<string, unknown>)["agent"] ?? {}) as Record<string, unknown>)["handle"] ?? "");

/**
 * Everything that must hold after every step, checked from the outside
 * where possible (the public API and pages), and against an independent
 * recomputation from the log where the claim is about recomputability.
 */
export async function checkInvariants(s: Society, label: string, o: { deep?: boolean; log?: boolean } = {}): Promise<void> {
  const at = (m: string) => `[${label}] ${m}`;

  // 1. The log is intact and only ever grows: the whole chain re-verifies,
  //    and the tree head proves consistent with the last one checked (so
  //    every state in between was an append-only extension). Hashing the
  //    whole log is the costly part, so a run may do it every few steps.
  if (o.log !== false || o.deep) {
    const audit = await s.req("GET", "/v1/log/audit");
    assert.equal(audit.json?.intact, true, at(`log audit: ${audit.text}`));
    const sth = (await s.req("GET", "/v1/log/sth")).json;
    const size = Number(sth.treeSize);
    assert.ok(size >= s["seen"].size, at("the log shrank"));
    if (s["seen"].size > 0 && size > s["seen"].size) {
      const c = (await s.req("GET", `/v1/log/consistency?first=${s["seen"].size}&second=${size}`)).json;
      assert.equal(c.firstRoot, s["seen"].root, at("an earlier tree head changed"));
      const okc = await verifyConsistency(s["seen"].size, size, fromHex(c.firstRoot), fromHex(c.secondRoot), (c.proof as string[]).map(fromHex));
      assert.ok(okc, at("consistency proof failed: the log was rewritten"));
    }
    s["seen"] = { size, root: String(sth.rootHash) };
  }

  const cases = await s.quarantine();
  const byId = new Map(cases.map((q) => [q.id, q] as const));
  for (const q of cases) s.mark(`case:${q.kind}:${q.status}`);

  // 2. Nothing unscreened is shown: every listed preprint was asked for,
  //    screened clean, is still under review, and is not a platform probe.
  const listed = ((await s.req("GET", "/v1/preprints?limit=100")).json?.preprints ?? []) as Array<Record<string, unknown>>;
  for (const p of listed) {
    const q = byId.get(String(p["receipt"]));
    assert.ok(q, at("a listed preprint has no case"));
    assert.equal(q.status, "pending", at("a decided or held paper is still listed as a preprint"));
    assert.equal(q.kind, "paper");
    assert.ok(q.preprintAt, at("listed without preprintAt"));
    const payload = (q.envelope as { payload: Record<string, unknown> }).payload;
    assert.equal(payload["preprint"], true, at("shown without the author's signed choice"));
    assert.deepEqual(q.findings.filter((f) => f.screener !== "probation"), [], at("shown despite a content finding"));
    assert.notEqual(s.agents.get(authorOf(q))?.op, PROBE_OPERATOR, at("a platform probe was shown"));
  }
  // ...and every case answers /v1/preprints/<receipt> consistently with its
  // state (re-read whenever a case is new or has changed, and on deep checks).
  for (const q of cases) {
    if (!o.deep && s.checked.get(q.id) === q.status) continue;
    s.checked.set(q.id, q.status);
    const r = await s.req("GET", `/v1/preprints/${q.id}`);
    if (q.kind !== "paper" || !q.preprintAt) {
      assert.equal(r.status, 404, at(`not a preprint, yet /v1/preprints answered ${r.status}`));
      continue;
    }
    const expected = { pending: "under_review", released: "accepted", rejected: "not_accepted", hazard_hold: "withdrawn" }[q.status];
    assert.equal(r.json?.status, expected, at(`preprint ${q.id.slice(0, 8)} is ${q.status} but reads ${r.json?.status}`));
    s.mark(`preprint:${expected}`);
    if (q.status === "released") assert.equal(r.json.url, `/p/${await s.handleOf(q.id)}`, at("accepted preprint points elsewhere"));
    if (q.status === "pending") assert.equal(r.json.citable, false);
  }

  // 3. At most PREPRINT_DAILY_CAP preprints per operator in any 24 hours.
  const shownBy = new Map<string, number[]>();
  for (const q of cases) {
    if (!q.preprintAt) continue;
    const op = s.agents.get(authorOf(q))?.op ?? "?";
    (shownBy.get(op) ?? shownBy.set(op, []).get(op)!).push(Date.parse(q.preprintAt));
  }
  for (const [op, times] of shownBy) {
    times.sort((a, b) => a - b);
    for (let i = 0; i + 3 < times.length; i++) assert.ok(times[i + 3]! - times[i]! >= 24 * HOUR, at(`${op} showed more than 3 preprints in 24 hours`));
  }

  // 4. Nothing unaccepted is citable: every accepted paper's record parents
  //    were in the record before it, cited with the right shape.
  const events = (await s.store.allEvents()) as ScoredEvent[];
  const acceptSeq = new Map<string, number>();
  const buildSeq = new Map<string, number>();
  for (const e of events) {
    const p = e.payload as Record<string, unknown>;
    if (e.type === "paper.accept") { acceptSeq.set(String(p["id"]), e.seq); acceptSeq.set(String(p["handle"]), e.seq); }
    if (e.type === "build.activate") buildSeq.set(String(p["cid"]), e.seq);
  }
  const papers = await s.store.listPapers(5000);
  for (const paper of papers) {
    for (const par of paper.payload.builds_on) {
      if (!par.id.startsWith("ecd:")) continue;
      const parent = await s.store.getPaper(par.id);
      if (parent) {
        assert.ok(parent.seq < paper.seq, at(`${paper.handle} cites ${par.id}, which was not in the record first`));
        if (par.rel !== "background") assert.ok(par.claims?.length, at(`${paper.handle} relies on ${par.id} without naming claims`));
        for (const l of par.claims ?? []) assert.ok(Number(l.slice(1)) <= parent.payload.claims.length, at(`${paper.handle} cites a missing claim`));
      } else {
        const b = buildSeq.get(par.id);
        assert.ok(b !== undefined && b < paper.seq, at(`${paper.handle} cites ${par.id}, which is neither an accepted paper nor a live build`));
        assert.ok(par.rel === "method" || par.rel === "background", at("a build cited as something other than method or background"));
      }
      if (par.rel === "extends" || par.rel === "method") {
        assert.ok(par.basis === "reproduced" || par.basis === "reviewed", at(`${paper.handle}: reliance without a basis`));
        assert.ok((par.note ?? "").trim().length >= 20, at(`${paper.handle}: reliance without a note`));
      }
    }
  }
  //    ...and every live build rests on claims in the record.
  const live = await s.store.listBuilds("active", 5000);
  for (const b of live) {
    for (const dep of b.manifest.depends_on) {
      const [pid, label] = dep.split("#") as [string, string];
      const parent = await s.store.getPaper(pid);
      assert.ok(parent && Number(label.slice(1)) <= parent.payload.claims.length, at(`build ${b.slug} rests on ${dep}, not in the record`));
    }
  }

  // 5. Every accepted paper came through its jury or the operator key (R1),
  //    or was published directly by a veteran when every-paper review is off.
  for (const q of cases) {
    if (q.status !== "released") continue;
    const decided = events.some((e) => {
      const p = e.payload as Record<string, unknown>;
      return (e.type === "review.decide" && p["subject"] === q.id && p["outcome"] === "publish")
        || (e.type === "hazard.release" && p["subject"] === q.id && p["decision"] === "release");
    });
    assert.ok(decided, at(`case ${q.id.slice(0, 8)} was released without a jury decision or R1`));
  }

  // 6. Juries are independent: never the author's operator, one seat per
  //    operator, one vote per juror, and only seated jurors vote.
  for (const q of cases) {
    const authorOp = s.agents.get(authorOf(q))?.op;
    const ops = q.jury.map((h) => s.agents.get(h)?.op);
    assert.ok(!ops.includes(authorOp), at(`case ${q.id.slice(0, 8)} seats its author's operator`));
    assert.equal(new Set(ops).size, ops.length, at(`case ${q.id.slice(0, 8)} seats one operator twice`));
    const voters = q.votes.map((v) => v.handle);
    assert.equal(new Set(voters).size, voters.length, at("a juror voted twice"));
    const everSeated = new Set([...q.jury, ...(q.seats ?? []).map((x) => x.handle)]);
    for (const v of voters) assert.ok(everSeated.has(v), at(`${v} voted without a seat`));
  }

  // 7. Credence: what the API serves is an independent recomputation from
  //    the log and the published papers; and an operator's own filings on
  //    its own claims change nothing.
  const confidences = new Map(papers.map((p) => [p.cid, p.payload.claims.map((c) => c.confidence)] as const));
  const reg = s.registry();
  const mine = computeCredence(events, reg, confidences);
  const served = ((await s.req("GET", "/v1/credence")).json?.claims ?? []) as Array<Record<string, unknown>>;
  assert.equal(served.length, mine.claims.size, at("credence covers a different set of claims"));
  for (const c of served) {
    assert.deepEqual(c, JSON.parse(JSON.stringify(mine.claims.get(String(c["ref"])))), at(`credence for ${c["ref"]} does not recompute`));
    s.mark(`claim:${c["status"]}`);
  }
  const withoutSelf = events.filter((e) => {
    if (e.type !== "replication.file") return true;
    const p = e.payload as { agent: { handle: string }; targets: string[] };
    return !p.targets.every((t) => {
      const parent = papers.find((x) => x.handle === t.split("#")[0] || x.cid === t.split("#")[0]);
      return parent && reg.operatorOf(parent.payload.agent.handle) === reg.operatorOf(p.agent.handle);
    });
  });
  const stripped = computeCredence(withoutSelf, reg, confidences);
  for (const [ref, c] of mine.claims) {
    const d = stripped.claims.get(ref)!;
    assert.equal(c.credence, d.credence, at(`same-operator filings moved ${ref}`));
    assert.deepEqual(c.evidence, d.evidence, at(`same-operator filings counted as evidence on ${ref}`));
  }

  // 8. A build's health is the worst status among the claims it rests on.
  for (const b of live) {
    const r = (await s.req("GET", `/v1/builds/${b.slug}`)).json;
    const statuses = (b.manifest.depends_on as string[]).map((dep) => {
      const [pid, label] = dep.split("#") as [string, string];
      const handle = papers.find((x) => x.handle === pid || x.cid === pid)!.handle;
      return mine.claims.get(`${handle}#${label}`)!.status as ClaimStatus;
    });
    assert.equal(r.health, healthFromStatuses(statuses), at(`build ${b.slug} health disagrees with credence`));
    s.mark(`build:${r.health}`);
  }

  // 9. Standing is the published rule applied to the public log.
  const st = ((await s.req("GET", "/v1/standing")).json?.standing ?? []) as Array<{ handle: string; score: number }>;
  const replay = computeStanding(events, reg);
  for (const row of st) assert.equal(row.score, replay.get(row.handle)?.score ?? 0, at(`standing for ${row.handle} does not recompute`));

  // 10. Deep: a fresh isolate (cold caches, cold operator graph) serves the
  //     same figures, and the human pages render without script.
  if (o.deep) {
    const fresh = s.service();
    for (const path of ["/v1/credence", "/v1/standing", "/v1/frontier?limit=50", "/v1/marketplace?limit=100", "/v1/preprints?limit=100"]) {
      const a = await s.req("GET", path);
      const b = await s.req("GET", path, { svc: fresh });
      assert.equal(b.text, a.text, at(`${path} differs between isolates`));
    }
    for (const path of ["/papers", "/preprints", "/review", "/apps", ...papers.slice(0, 3).map((p) => `/p/${p.handle}`)]) {
      const r = await s.req("GET", path, { html: true });
      assert.equal(r.status, 200, at(`${path} → ${r.status}`));
      assert.doesNotMatch(r.text, /<script/i, at(`${path} carries script`));
      assert.doesNotMatch(r.text, /undefined|NaN|\[object Object\]/, at(`${path} renders a broken value`));
    }
    for (const q of cases.filter((x) => x.preprintAt).slice(-4)) {
      const r = await s.req("GET", `/pp/${q.id}`, { html: true });
      const want = { pending: 200, released: 301, rejected: 410, hazard_hold: 410 }[q.status];
      assert.equal(r.status, want, at(`/pp/ for a ${q.status} preprint → ${r.status}`));
      assert.equal(r.headers.get("x-robots-tag"), "noindex", at("a preprint page is indexable"));
    }
    // Preprints stay out of the sitemap and feeds: only the record goes there.
    const sitemap = (await s.req("GET", "/sitemap.xml", { html: true })).text;
    const feed = (await s.req("GET", "/feeds/all.atom", { html: true })).text;
    for (const text of [sitemap, feed]) assert.doesNotMatch(text, /\/pp\/|\/preprints/, at("a preprint reached the sitemap or a feed"));
    const titles = new Set(cases.filter((q) => q.status !== "released" && q.kind === "paper").map((q) => String((q.envelope as { payload: Record<string, unknown> }).payload["title"])));
    for (const t of titles) assert.ok(!feed.includes(t.replace(/&/g, "&amp;")), at(`an unaccepted paper's title is in the feed: ${t}`));
  }
}
