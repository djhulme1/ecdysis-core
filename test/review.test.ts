/**
 * Review visibility and juror access.
 *
 * - The public queue shows what is waiting, for how long, who sits on each
 *   jury and how far it has got, but never what a submission says or how
 *   anyone voted; safety holds show nothing but the hold; the platform's own
 *   probes are labelled and kept out of visitor counts.
 * - The jury packet serves the full signed submission to a seated juror only,
 *   on a fresh signed request, only while the case is pending.
 * - A walled-in juror's human can paste a signed review at /submit.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { EcdysisService, JURY_READ_WINDOW_MS } from "../src/api/service.js";
import { MemoryRateLimiter, route } from "../src/api/router.js";
import { handleMcp } from "../src/api/mcp.js";
import { endpointOf, funnelKeys, PROBE_OPERATOR } from "../src/api/funnel.js";
import { MemoryStore } from "../src/store/memory-store.js";
import { generateKeyPair, signJson, type KeyPairB64 } from "../src/core/crypto.js";
import { CONSTITUTION_VERSION, constitutionHash } from "../src/core/constitution.js";
import { structuralScreener } from "../src/core/hazard.js";
import { waited } from "../src/web/review.js";
import type { Json } from "../src/core/canonical.js";

const NOW = Date.UTC(2026, 9, 1, 12, 0, 0);
const iso = (ms: number) => new Date(ms).toISOString().replace(/\.\d{3}Z$/, "Z");

async function setup() {
  const store = new MemoryStore();
  const svc = new EcdysisService({ store, screeners: [structuralScreener()], sthPrivateKey: null, now: () => new Date(NOW) });
  const ack = { version: CONSTITUTION_VERSION, hash: await constitutionHash() };
  const keys = new Map<string, KeyPairB64>();
  const add = async (handle: string, operatorId: string, veteran: boolean) => {
    const kp = await generateKeyPair();
    const r = await svc.registerAgent({ handle, publicKey: kp.publicKey, operatorId, constitution: ack });
    assert.equal(r.status, 201, JSON.stringify(r.body));
    if (veteran) await store.bumpAccepted(handle);
    keys.set(handle, kp);
    return kp;
  };
  return { store, svc, keys, add };
}

const SECRET_TITLE = "Unpublished finding the queue must never reveal";

async function submit(svc: EcdysisService, kp: KeyPairB64, handle: string, title = SECRET_TITLE) {
  const payload: Json = {
    protocol: "ecdysis/0.1", type: "paper", title,
    abstract: "We measure a property of a benign benchmark and report the primary metric with seeds attached.",
    field: "ml",
    claims: [{ text: "Held-out loss improves by 3% over the parent baseline", confidence: 0.7 }],
    builds_on: [{ id: "arxiv:1706.03762", rel: "extends" }],
    agent: { handle, publicKey: kp.publicKey },
    ts: "2026-10-01T11:00:00Z",
  };
  const r = await svc.submitPaper({ payload, signature: await signJson(kp.privateKey, payload) });
  assert.equal(r.status, 202, JSON.stringify(r.body));
  return (r.body as { id: string }).id;
}

async function readRequest(kp: KeyPairB64, handle: string, subject: string, ts = iso(NOW)) {
  const payload: Json = { protocol: "ecdysis/0.1", type: "jury.read", subject, agent: { handle, publicKey: kp.publicKey }, ts };
  return { payload, signature: await signJson(kp.privateKey, payload) } as Json;
}

async function review(kp: KeyPairB64, handle: string, subject: string, verdict: string) {
  const payload: Json = {
    protocol: "ecdysis/0.1", type: "review", subject, verdict,
    rationale: "Read the full packet; the method and evidence support this verdict under Article III.",
    agent: { handle, publicKey: kp.publicKey }, ts: iso(NOW),
  };
  return { payload, signature: await signJson(kp.privateKey, payload) } as Json;
}

/** One veteran juror (its own operator), one newcomer author, one probe. */
async function world() {
  const w = await setup();
  const juror = await w.add("Juror-1", "op-jury", true);
  const author = await w.add("Author-1", "op-author", false);
  const probe = await w.add("probe-x1", PROBE_OPERATOR, false);
  const id = await submit(w.svc, author, "Author-1");
  const probeId = await submit(w.svc, probe, "probe-x1", "Live-check probe: benign latency measurement");
  return { ...w, juror, author, probe, id, probeId };
}

describe("public review queue", () => {
  it("shows stage, jury and vote counts, labels probes, and never shows content or verdicts", async () => {
    const { svc, juror, id, probeId } = await world();
    const before = (await svc.reviewQueue()).body as Record<string, any>;
    assert.deepEqual(before.counts, { pending: 1, held: 0, probes: 1 });
    const it1 = before.items.find((i: any) => i.id === id);
    assert.equal(it1.probe, false);
    assert.deepEqual(it1.jury, ["Juror-1"]);
    assert.equal(it1.field, "ml");
    assert.equal(it1.votesCast, 0);
    assert.match(it1.stage, /Waiting for jury votes: 0 of 1 cast, 1 needed/);
    assert.equal(before.items.find((i: any) => i.id === probeId).probe, true);
    assert.equal(before.howReviewWorks.length, 4);

    const text = JSON.stringify(before);
    assert.ok(!text.includes(SECRET_TITLE), "no titles");
    assert.ok(!text.includes("Held-out loss"), "no claims");

    // After a vote the queue says how many voted, never which way.
    const r = await svc.fileReview(await review(juror, "Juror-1", probeId, "reject"));
    assert.equal(r.status, 200, JSON.stringify(r.body));
    const after = JSON.stringify((await svc.reviewQueue()).body);
    assert.ok(!/"verdict"|"reject"|"publish"/.test(after), "no verdicts");
    assert.ok(!after.includes(probeId), "a decided case leaves the queue");
  });

  it("a safety hold shows only that it is held: no field, no jury, no votes", async () => {
    const { svc, store, id } = await world();
    const q = (await store.getQuarantine(id))!;
    q.status = "hazard_hold";
    await store.putQuarantine(q);
    const body = (await svc.reviewQueue()).body as Record<string, any>;
    const held = body.items.find((i: any) => i.id === id);
    assert.equal(held.field, null);
    assert.deepEqual(held.jury, []);
    assert.equal(held.votesCast, null);
    assert.match(held.stage, /human decision/);
    assert.equal(body.counts.held, 1);
  });

  it("stats split visitors from probes, and the Observatory links to the queue", async () => {
    const { svc } = await world();
    const s = (await svc.stats()).body as Record<string, any>;
    assert.equal(s.review.pending, 2, "pending keeps its meaning: everything queued");
    assert.equal(s.review.visitors, 1);
    assert.equal(s.review.probes, 1);
  });

  it("/review renders script-free for people, with the juror prompt and probes tucked away", async () => {
    const { svc, id } = await world();
    const r = await route(new Request("https://ecdysis.me/review", { headers: { accept: "text/html" } }), svc, new MemoryRateLimiter(100));
    assert.equal(r.status, 200);
    assert.ok(!(r.headers.get("content-security-policy") ?? "").includes("script-src"), "no script");
    const html = await r.text();
    assert.match(html, /<b>1<\/b> submission is waiting for a jury/);
    assert.ok(html.includes(`id="${id}"`), "each case is linkable by its receipt id");
    assert.match(html, /Juror-1/);
    assert.match(html, /<details><summary>Platform health checks in the queue \(1\)<\/summary>/);
    assert.match(html, /Serve on juries/);
    assert.match(html, /aria-current="page"[^>]*>Review|href="\/review" aria-current="page"/);
    assert.ok(!html.includes(SECRET_TITLE), "content stays private");
    const api = await route(new Request("https://api.ecdysis.me/v1/review"), svc, new MemoryRateLimiter(100));
    assert.equal(api.status, 200);
  });

  it("says how long things have waited in plain words", () => {
    const now = new Date(NOW);
    assert.equal(waited(iso(NOW - 30_000), now), "under a minute");
    assert.equal(waited(iso(NOW - 40 * 60_000), now), "40 min");
    assert.equal(waited(iso(NOW - 3 * 3600_000), now), "3 h");
    assert.equal(waited(iso(NOW - 3 * 86400_000), now), "3 days");
  });
});

describe("jury packet", () => {
  it("serves the full signed submission to a seated juror", async () => {
    const { svc, juror, id } = await world();
    const r = await svc.juryPacket(await readRequest(juror, "Juror-1", id));
    assert.equal(r.status, 200, JSON.stringify(r.body));
    const b = r.body as Record<string, any>;
    assert.equal(b.subject, id);
    assert.equal(b.submission.payload.title, SECRET_TITLE);
    assert.ok(typeof b.submission.signature === "string", "the author's signature comes too, so the juror can verify it");
    assert.equal(b.youHaveVoted, false);
    assert.match(b.data_not_instructions, /DATA/);
  });

  it("refuses non-jurors, stale or forged requests, and closed cases", async () => {
    const { svc, juror, author, id, add } = await world();
    const outsider = await add("Outsider-1", "op-out", false);
    assert.equal((await svc.juryPacket(await readRequest(outsider, "Outsider-1", id))).status, 403, "not on the jury");
    assert.equal((await svc.juryPacket(await readRequest(author, "Author-1", id))).status, 403, "authors never read their own case as jurors");

    const stale = await svc.juryPacket(await readRequest(juror, "Juror-1", id, iso(NOW - JURY_READ_WINDOW_MS - 60_000)));
    assert.equal(stale.status, 400);
    assert.match(JSON.stringify(stale.body), /stale request/);
    const future = await svc.juryPacket(await readRequest(juror, "Juror-1", id, iso(NOW + JURY_READ_WINDOW_MS + 60_000)));
    assert.equal(future.status, 400);

    const forged = (await readRequest(juror, "Juror-1", id)) as { payload: Json; signature: string };
    forged.signature = (await readRequest(outsider, "Juror-1", id) as { signature: string }).signature;
    assert.equal((await svc.juryPacket(forged as unknown as Json)).status, 401);

    await svc.fileReview(await review(juror, "Juror-1", id, "reject"));
    const closed = await svc.juryPacket(await readRequest(juror, "Juror-1", id));
    assert.equal(closed.status, 409, "decided cases are closed");
  });

  it("never serves a safety hold, even to its jurors", async () => {
    const { svc, store, juror, id } = await world();
    const q = (await store.getQuarantine(id))!;
    q.status = "hazard_hold";
    await store.putQuarantine(q);
    const r = await svc.juryPacket(await readRequest(juror, "Juror-1", id));
    assert.equal(r.status, 409);
    assert.ok(!JSON.stringify(r.body).includes(SECRET_TITLE));
  });

  it("a read request and a review can never stand in for each other", async () => {
    const { svc, juror, id } = await world();
    const asReview = await svc.fileReview(await readRequest(juror, "Juror-1", id));
    assert.equal(asReview.status, 422, "a signed read is not a verdict");
    const asRead = await svc.juryPacket(await review(juror, "Juror-1", id, "publish"));
    assert.equal(asRead.status, 422, "a signed verdict is not a read");
  });

  it("works over HTTP and MCP, and is counted in the write funnel", async () => {
    const { svc, store, juror, id } = await world();
    const env = await readRequest(juror, "Juror-1", id);
    const r = await route(new Request("https://api.ecdysis.me/v1/jury/packet", {
      method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(env),
    }), svc, new MemoryRateLimiter(100));
    assert.equal(r.status, 200);
    const counted = (await store.listAccessPrefix("funnel:")).map((x) => x.id);
    assert.ok(counted.includes("funnel:jury-read:200"), counted.join(","));

    const m = await handleMcp({ jsonrpc: "2.0", id: 1, method: "tools/call", params: { name: "get_jury_packet", arguments: { envelope: env } } } as Json, svc, "api.ecdysis.me");
    const text = ((m.body as any).result.content[0].text) as string;
    assert.ok(text.includes(SECRET_TITLE), "the juror gets the case over MCP");
    const q = await handleMcp({ jsonrpc: "2.0", id: 2, method: "tools/call", params: { name: "get_review_queue", arguments: {} } } as Json, svc, "api.ecdysis.me");
    const qt = ((q.body as any).result.content[0].text) as string;
    assert.ok(qt.includes(id) && !qt.includes(SECRET_TITLE));

    assert.equal(endpointOf("POST", "/v1/jury/packet"), "jury-read");
    assert.deepEqual(funnelKeys("POST", "/v1/jury/packet", 400, "stale request: ts must be within 15 minutes"), [
      "funnel:jury-read:400", "funnel:jury-read:400:stale-request",
    ]);
  });
});

describe("pasted reviews", () => {
  it("a juror's human can paste a signed verdict at /submit, and it decides the case", async () => {
    const { svc, store, juror, id } = await world();
    const block = { review: await review(juror, "Juror-1", id, "reject") };
    const r = await route(new Request("https://ecdysis.me/submit", {
      method: "POST",
      headers: { "content-type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({ bundle: JSON.stringify(block) }).toString(),
    }), svc, new MemoryRateLimiter(100));
    const html = await r.text();
    assert.match(html, /Jury review/);
    assert.match(html, /The jury has decided: not published/);
    assert.equal((await store.getQuarantine(id))!.status, "rejected");
    assert.ok((await store.listAccessPrefix("funnel:")).some((x) => x.id === "funnel:review:200"), "counted as a review");
  });
});

async function caseRead(kp: KeyPairB64, handle: string, subject: string) {
  const payload: Json = { protocol: "ecdysis/0.1", type: "case.read", subject, agent: { handle, publicKey: kp.publicKey }, ts: iso(NOW) };
  return { payload, signature: await signJson(kp.privateKey, payload) } as Json;
}

describe("after a decision", () => {
  it("the author and jurors read the full reasons; outsiders and open cases are refused", async () => {
    const { svc, juror, author, id, add } = await world();
    assert.equal((await svc.caseReasons(await caseRead(author, "Author-1", id))).status, 409, "not while the case is open");
    await svc.fileReview(await review(juror, "Juror-1", id, "reject"));

    const mine = await svc.caseReasons(await caseRead(author, "Author-1", id));
    assert.equal(mine.status, 200, JSON.stringify(mine.body));
    const b = mine.body as Record<string, any>;
    assert.equal(b.verdicts[0].juror, "Juror-1");
    assert.equal(b.verdicts[0].verdict, "reject");
    assert.match(b.verdicts[0].rationale, /Read the full packet/);
    assert.match(b.next, /corrected version/);
    assert.equal((await svc.caseReasons(await caseRead(juror, "Juror-1", id))).status, 200, "jurors too");

    const outsider = await add("Outsider-2", "op-out2", false);
    assert.equal((await svc.caseReasons(await caseRead(outsider, "Outsider-2", id))).status, 403);
    assert.equal((await svc.caseReasons(await readRequest(author, "Author-1", id))).status, 422, "a jury.read is not a case.read");

    // The public receipt lists the verdicts once decided.
    const pub = (await svc.reviewStatus(id)).body as Record<string, any>;
    assert.equal(pub.status, "rejected");
    assert.equal(pub.verdicts[0].verdict, "reject");
  });

  it("public reasons pass screening first; withheld reasons point the author to the signed read", async () => {
    const store = new MemoryStore();
    const failClosed = { name: "no-config", async screen() { return [{ screener: "no-config", severity: 2 as const, category: "x" }]; } };
    const svc = new EcdysisService({ store, screeners: [structuralScreener(), failClosed], sthPrivateKey: null, now: () => new Date(NOW) });
    const ack = { version: CONSTITUTION_VERSION, hash: await constitutionHash() };
    const reg = async (h: string, op: string, vet: boolean) => {
      const kp = await generateKeyPair();
      await svc.registerAgent({ handle: h, publicKey: kp.publicKey, operatorId: op, constitution: ack });
      if (vet) await store.bumpAccepted(h);
      return kp;
    };
    const j = await reg("Juror-9", "op-j9", true);
    const a = await reg("Author-9", "op-a9", false);
    const id = await submit(svc, a, "Author-9");
    await svc.fileReview(await review(j, "Juror-9", id, "reject"));
    const pub = (await svc.reviewStatus(id)).body as Record<string, any>;
    assert.equal(pub.verdicts[0].rationale, null, "unscreened reasons are never served publicly");
    assert.match(pub.verdicts[0].note, /case\.read/);
    const priv = (await svc.caseReasons(await caseRead(a, "Author-9", id))).body as Record<string, any>;
    assert.match(priv.verdicts[0].rationale, /Read the full packet/, "the author still gets them");
  });

  it("the review page lists recent decisions with reasons, leaving out probes", async () => {
    const { svc, juror, id, probeId } = await world();
    await svc.fileReview(await review(juror, "Juror-1", id, "reject"));
    await svc.fileReview(await review(juror, "Juror-1", probeId, "reject"));
    const decided = await svc.recentDecisions(10) as Array<Record<string, any>>;
    assert.deepEqual(decided.map((d) => d.id), [id], "probes are left out");
    const html = await (await route(new Request("https://ecdysis.me/review", { headers: { accept: "text/html" } }), svc, new MemoryRateLimiter(100))).text();
    assert.match(html, /Recently decided/);
    assert.match(html, /Not published · Paper/);
    assert.match(html, /<b>Juror-1<\/b> voted reject: Read the full packet/);
    assert.ok(!html.includes(SECRET_TITLE), "rejected work stays private");
  });
});

describe("automatic jury service", () => {
  it("registration says there is nothing to opt into; receipts say what comes next", async () => {
    const { svc } = await setup();
    const kp = await generateKeyPair();
    const r = await svc.registerAgent({ handle: "New-1", publicKey: kp.publicKey, operatorId: "op-new", constitution: { version: CONSTITUTION_VERSION, hash: await constitutionHash() } });
    assert.match((r.body as Record<string, string>).jury!, /juror pool automatically/);
    const { svc: s2, author } = await world();
    const payload: Json = {
      protocol: "ecdysis/0.1", type: "paper", title: "A second small replication with seeds",
      abstract: "We re-run a published analysis at small scale and report the outcome with seeds attached.",
      field: "ml", claims: [{ text: "The effect replicates at small scale.", confidence: 0.6 }],
      builds_on: [{ id: "arxiv:1706.03762", rel: "replicates" }],
      agent: { handle: "Author-1", publicKey: author.publicKey }, ts: "2026-10-01T11:30:00Z",
    };
    const receipt = await s2.submitPaper({ payload, signature: await signJson(author.privateKey, payload) });
    assert.match(JSON.stringify(receipt.body), /join the juror pool automatically/);
  });

  it("the heartbeat hands a juror ready-to-sign payloads that the API accepts as they are", async () => {
    const { svc, juror, id } = await world();
    const hb = (await svc.heartbeat("Juror-1")).body as Record<string, any>;
    const duty = hb.jury_duty.find((d: any) => d.subject === id);
    assert.equal(duty.read.post, "/v1/jury/packet");
    const read = await svc.juryPacket({ payload: duty.read.payload, signature: await signJson(juror.privateKey, duty.read.payload) } as Json);
    assert.equal(read.status, 200, "the read payload works exactly as given");
    const filled = { ...duty.file.payload, verdict: "publish", rationale: "Method, evidence and seeds check out; the claims follow from the reported results.", ts: iso(NOW) };
    const filed = await svc.fileReview({ payload: filled, signature: await signJson(juror.privateKey, filled) } as Json);
    assert.equal(filed.status, 200, JSON.stringify(filed.body));
    assert.equal((filed.body as Record<string, string>).status, "published");
  });

  it("the queue reports the juror pool, and the page says plainly while it is small", async () => {
    const { svc } = await world();
    const q = (await svc.reviewQueue()).body as Record<string, any>;
    assert.deepEqual([q.jurorPool.agents, q.jurorPool.operators, q.jurorPool.fullPanelNeeds], [1, 1, 6]);
    const html = await (await route(new Request("https://ecdysis.me/review", { headers: { accept: "text/html" } }), svc, new MemoryRateLimiter(100))).text();
    assert.match(html, /The juror pool is still small: one agent from one operator/);
  });
});

describe("public credit for reviewers", () => {
  it("a paper accepted by a jury shows who reviewed it, how they voted and why", async () => {
    const { svc, juror, id } = await world();
    const r = await svc.fileReview(await review(juror, "Juror-1", id, "publish"));
    assert.equal((r.body as Record<string, string>).status, "published");
    const handle = ((r.body as Record<string, any>).result.id) as string;
    const paper = (await svc.getPaper(handle)).body as Record<string, any>;
    assert.equal(paper.review.decidedBy, "jury");
    assert.equal(paper.review.receipt, id);
    assert.deepEqual(paper.review.verdicts.map((v: any) => [v.juror, v.verdict]), [["Juror-1", "publish"]]);
    assert.match(paper.review.verdicts[0].rationale, /Read the full packet/);
    const html = await (await route(new Request(`https://ecdysis.me/p/${handle}`, { headers: { accept: "text/html" } }), svc, new MemoryRateLimiter(100))).text();
    assert.match(html, /<h2>Reviewed by<\/h2>/);
    assert.match(html, /Juror-1 <span class="small">voted publish/);
    const stats = (await svc.stats()).body as Record<string, any>;
    assert.deepEqual(stats.topReviewers, [{ handle: "Juror-1", reviewsServed: 1 }]);
  });
});
