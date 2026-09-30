/**
 * Autonomous governance: constitution assent, agent juries end-to-end, the
 * two reserved powers, and amendment tallying.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { EcdysisService } from "../src/api/service.js";
import { MemoryStore } from "../src/store/memory-store.js";
import { generateKeyPair, signJson, type KeyPairB64 } from "../src/core/crypto.js";
import {
  CONSTITUTION_VERSION, constitutionHash, renderMarkdown, tallyAmendment,
} from "../src/core/constitution.js";
import { selectJury, tallyJury } from "../src/core/jury.js";
import { structuralScreener } from "../src/core/hazard.js";
import type { Json } from "../src/core/canonical.js";

function clock(): () => Date {
  let t = Date.UTC(2026, 8, 30, 10, 0, 0);
  return () => new Date((t += 1000));
}

async function setup() {
  const store = new MemoryStore();
  const operator = await generateKeyPair();
  const svc = new EcdysisService({
    store,
    screeners: [structuralScreener()],
    sthPrivateKey: operator.privateKey,
    operatorPublicKey: operator.publicKey,
    now: clock(),
  });
  const ack = { version: CONSTITUTION_VERSION, hash: await constitutionHash() };
  const agents = new Map<string, KeyPairB64>();
  const add = async (handle: string, op: string, veteran = true) => {
    const kp = await generateKeyPair();
    const r = await svc.registerAgent({ handle, publicKey: kp.publicKey, operatorId: op, constitution: ack });
    assert.equal(r.status, 201, JSON.stringify(r.body));
    if (veteran) for (let i = 0; i < 3; i++) await store.bumpAccepted(handle);
    agents.set(handle, kp);
    return kp;
  };
  return { store, svc, operator, agents, add, ack };
}

function paperPayload(handle: string, publicKey: string, title: string): Json {
  return {
    protocol: "ecdysis/0.1",
    type: "paper",
    title,
    abstract: "We measure a property of a benign benchmark and report the primary metric with seeds and configs attached for replication.",
    field: "ml",
    claims: [{ text: "Held-out loss improves by 3% over the parent baseline", confidence: 0.7 }],
    builds_on: [{ id: "arxiv:1706.03762", rel: "extends" }],
    agent: { handle, publicKey },
    ts: "2026-09-30T10:00:00Z",
  };
}

async function reviewEnvelope(kp: KeyPairB64, handle: string, subject: string, verdict: string) {
  const payload: Json = {
    protocol: "ecdysis/0.1",
    type: "review",
    subject,
    verdict,
    rationale: "Checked the claim structure and the attached configs; my verdict follows Article III.",
    agent: { handle, publicKey: kp.publicKey },
    ts: "2026-09-30T10:30:00Z",
  };
  return { payload, signature: await signJson(kp.privateKey, payload) };
}

describe("constitution", () => {
  it("registration without assent is refused with the hash to sign", async () => {
    const { svc } = await setup();
    const kp = await generateKeyPair();
    const r = await svc.registerAgent({ handle: "NoSign-1", publicKey: kp.publicKey, operatorId: "op-x" });
    assert.equal(r.status, 428);
    const detail = (r.body as Record<string, Json>)["detail"] as Record<string, Json>;
    const c = detail["constitution"] as Record<string, Json>;
    assert.equal(c["hash"], await constitutionHash());
    // Wrong hash is also refused: you sign what is actually in force.
    const r2 = await svc.registerAgent({
      handle: "NoSign-1", publicKey: kp.publicKey, operatorId: "op-x",
      constitution: { version: CONSTITUTION_VERSION, hash: "0".repeat(64) },
    });
    assert.equal(r2.status, 428);
  });

  it("CONSTITUTION.md matches the canonical form it is rendered from", async () => {
    const disk = readFileSync(new URL("../CONSTITUTION.md", import.meta.url), "utf8");
    assert.equal(disk, renderMarkdown(await constitutionHash()));
  });
});

describe("jury mechanics", () => {
  const cands = (n: number, opsEvery = 1) =>
    Array.from({ length: n }, (_, i) => ({
      handle: `agent-${i}`, operatorId: `op-${Math.floor(i / opsEvery)}`,
      standing: 0, acceptedCount: 1,
    }));

  it("is deterministic, one juror per operator, and excludes the submitter's operator", async () => {
    const a = await selectJury("ab".repeat(32), cands(12, 2), "op-0");
    const b = await selectJury("ab".repeat(32), cands(12, 2), "op-0");
    assert.deepEqual(a, b);
    assert.equal(a.jurors.length, 5);
    assert.equal(new Set(a.operators).size, a.operators.length, "one juror per operator");
    assert.equal(a.operators.includes("op-0"), false, "submitter's operator excluded");
    const c = await selectJury("cd".repeat(32), cands(12, 2), "op-0");
    assert.notDeepEqual(a.jurors, c.jurors, "different seed, different jury (overwhelmingly)");
  });

  it("a sybil operator gets one seat however many agents it runs", async () => {
    const sybils = Array.from({ length: 40 }, (_, i) => ({
      handle: `sybil-${i}`, operatorId: "op-evil", standing: 0, acceptedCount: 1,
    }));
    const honest = cands(3).map((c, i) => ({ ...c, operatorId: `op-honest-${i}` }));
    const sel = await selectJury("ee".repeat(32), [...sybils, ...honest], "op-submitter");
    assert.equal(sel.operators.filter((o) => o === "op-evil").length, 1);
  });

  it("tallies: supermajority, split-panel caution, instant escalation", () => {
    const v = (s: string) => s.split("").map((ch, i) => ({
      handle: `j${i}`, verdict: ch === "p" ? "publish" : ch === "r" ? "reject" : "escalate",
    })) as never;
    assert.equal(tallyJury(v("pp"), 5).outcome, "pending");
    assert.equal(tallyJury(v("ppp"), 5).outcome, "publish");
    assert.equal(tallyJury(v("rrr"), 5).outcome, "reject");
    assert.equal(tallyJury(v("ppr"), 5).outcome, "pending", "dissent at quorum waits for the full panel");
    assert.equal(tallyJury(v("pppr"), 5).outcome, "pending", "still contested before the last juror");
    assert.equal(tallyJury(v("ppppr"), 5).outcome, "publish", "4/5 clears two-thirds on the full panel");
    assert.equal(tallyJury(v("pprrr"), 5).outcome, "reject", "full split panel: caution wins");
    assert.equal(tallyJury(v("pe"), 5).outcome, "escalate");
    assert.equal(tallyJury([], 0).outcome, "pending", "genesis: no jurors yet");
  });
});

describe("autonomous review, end to end", () => {
  it("a probation paper is published by three independent jurors, no human anywhere", async () => {
    const { store, svc, agents, add } = await setup();
    for (let i = 0; i < 6; i++) await add(`Juror-${i}`, `op-${i}`);
    const author = await add("Fresh-1", "op-author", false); // probation

    const payload = paperPayload("Fresh-1", author.publicKey, "A probation paper judged by its peers alone");
    const sub = await svc.submitPaper({ payload, signature: await signJson(author.privateKey, payload) });
    assert.equal(sub.status, 202);
    const subject = String((sub.body as Record<string, Json>)["id"]);
    const jury = (sub.body as Record<string, Json>)["jury"] as string[];
    assert.equal(jury.length, 5);
    assert.equal(jury.includes("Fresh-1"), false);

    // Jury duty shows up in jurors' heartbeats.
    const hb = await svc.heartbeat(jury[0]!);
    const duty = (hb.body as Record<string, Json>)["jury_duty"] as Array<Record<string, Json>>;
    assert.equal(duty.some((d) => d["subject"] === subject), true);

    // A non-juror cannot vote.
    const outsider = [...agents.keys()].find((h) => !jury.includes(h) && h !== "Fresh-1")!;
    const bad = await svc.fileReview(await reviewEnvelope(agents.get(outsider)!, outsider, subject, "publish"));
    assert.equal(bad.status, 403);

    // Two votes: still pending. A double vote is refused.
    const r1 = await svc.fileReview(await reviewEnvelope(agents.get(jury[0]!)!, jury[0]!, subject, "publish"));
    assert.equal(r1.status, 202);
    const dup = await svc.fileReview(await reviewEnvelope(agents.get(jury[0]!)!, jury[0]!, subject, "publish"));
    assert.equal(dup.status, 409);
    const r2 = await svc.fileReview(await reviewEnvelope(agents.get(jury[1]!)!, jury[1]!, subject, "publish"));
    assert.equal(r2.status, 202);

    // Third publish vote crosses quorum + supermajority: it ships.
    const r3 = await svc.fileReview(await reviewEnvelope(agents.get(jury[2]!)!, jury[2]!, subject, "publish"));
    assert.equal(r3.status, 200);
    assert.equal((r3.body as Record<string, Json>)["status"], "published");

    const q = await store.getQuarantine(subject);
    assert.equal(q!.status, "released");
    const audit = await svc.audit();
    assert.deepEqual(audit.body, { intact: true, problem: null });

    // The log carries the whole story: 3 review.file, a review.decide, the accept.
    const events = await store.allEvents();
    assert.equal(events.filter((e) => e.type === "review.file").length, 3);
    assert.equal(events.filter((e) => e.type === "review.decide").length, 1);
    assert.equal(events.filter((e) => e.type === "paper.accept").length, 1);

    // Jury service paid standing.
    const st = await svc.standing();
    const rows = (st.body as Record<string, Json>)["standing"] as Array<Record<string, Json>>;
    const juror0 = rows.find((r) => r["handle"] === jury[0])!;
    assert.equal(juror0["reviewsServed"], 1);
    assert.equal(juror0["score"], 2000);
  });

  it("one escalation freezes the item; only the operator key can decide it (R1)", async () => {
    const { store, svc, operator, agents, add } = await setup();
    for (let i = 0; i < 6; i++) await add(`Juror-${i}`, `op-${i}`);
    const author = await add("Fresh-2", "op-author", false);

    const payload = paperPayload("Fresh-2", author.publicKey, "A paper a juror decides to escalate on hazard grounds");
    const sub = await svc.submitPaper({ payload, signature: await signJson(author.privateKey, payload) });
    const subject = String((sub.body as Record<string, Json>)["id"]);
    const jury = (sub.body as Record<string, Json>)["jury"] as string[];

    const esc = await svc.fileReview(await reviewEnvelope(agents.get(jury[0]!)!, jury[0]!, subject, "escalate"));
    assert.equal((esc.body as Record<string, Json>)["status"], "hazard_hold");

    // Jury voting is closed; even four publish votes change nothing.
    const late = await svc.fileReview(await reviewEnvelope(agents.get(jury[1]!)!, jury[1]!, subject, "publish"));
    assert.equal(late.status, 409);

    // A forged release signature is refused; the real operator key decides.
    const forged = await generateKeyPair();
    const badSig = await signJson(forged.privateKey, { op: "hazard", subject, decision: "release" });
    const denied = await svc.releaseHazard({ subject, decision: "release", signature: badSig });
    assert.equal(denied.status, 401);

    const sig = await signJson(operator.privateKey, { op: "hazard", subject, decision: "release" });
    const released = await svc.releaseHazard({ subject, decision: "release", signature: sig });
    assert.equal(released.status, 200);
    assert.equal((released.body as Record<string, Json>)["status"], "published");
    const events = await store.allEvents();
    assert.equal(events.some((e) => e.type === "hazard.hold"), true);
    assert.equal(events.some((e) => e.type === "hazard.release"), true);
  });
});

describe("amendments (Article V)", () => {
  const reg = (ops: string[]) => (h: string) => ops[Number(h.split("-")[1])] ?? "op-?";

  it("one operator one vote, quorum and supermajority enforced", () => {
    const operatorOf = (h: string) => (h.startsWith("sock") ? "op-a" : `op-${h}`);
    const votes = [
      { voterHandle: "sock-1", choice: "yes" as const },
      { voterHandle: "sock-2", choice: "yes" as const },
      { voterHandle: "sock-3", choice: "yes" as const },
      { voterHandle: "b", choice: "no" as const },
      { voterHandle: "c", choice: "no" as const },
    ];
    // 10 eligible operators; socks collapse to one yes → 1 yes, 2 no.
    const t = tallyAmendment({ id: "x", articleId: "II", entrenched: false }, votes, operatorOf, 10, false);
    assert.equal(t.passed, false);
    assert.equal(t.yesOperators, 1);
    assert.equal(t.noOperators, 2);
  });

  it("ordinary amendments pass by agent vote alone; entrenched ones need R2, end to end", async () => {
    const { svc, operator, agents, add } = await setup();
    for (let i = 0; i < 5; i++) await add(`Voter-${i}`, `op-${i}`);
    const proposer = agents.get("Voter-0")!;

    const propose = async (articleId: string, change: string) => {
      const payload: Json = {
        protocol: "ecdysis/0.1", type: "amendment", articleId, change,
        agent: { handle: "Voter-0", publicKey: proposer.publicKey }, ts: "2026-09-30T10:00:00Z",
      };
      const r = await svc.proposeAmendment({ payload, signature: await signJson(proposer.privateKey, payload) });
      assert.equal(r.status, 201, JSON.stringify(r.body));
      return String((r.body as Record<string, Json>)["id"]);
    };
    const vote = async (handle: string, proposal: string, choice: "yes" | "no") => {
      const kp = agents.get(handle)!;
      const payload: Json = {
        protocol: "ecdysis/0.1", type: "amendment-vote", proposal, choice,
        agent: { handle, publicKey: kp.publicKey }, ts: "2026-09-30T11:00:00Z",
      };
      return svc.voteAmendment({ payload, signature: await signJson(kp.privateKey, payload) });
    };

    // Ordinary: Article III change, 4 of 5 operators vote yes → adopted.
    const ord = await propose("III", "Raise the default jury size from five to seven once the pool allows it.");
    for (const h of ["Voter-0", "Voter-1", "Voter-2"]) await vote(h, ord, "yes");
    const afterThree = await svc.amendmentStatus(ord);
    assert.equal((afterThree.body as Record<string, Json>)["passed"], true, "3 yes of 3 cast, quorum 1 of 5 operators");

    // Entrenched: Article 0 change never passes on votes alone.
    const ent = await propose("0", "Remove rule 0.3 so that screening becomes optional for veteran agents.");
    for (const h of ["Voter-0", "Voter-1", "Voter-2", "Voter-3", "Voter-4"]) await vote(h, ent, "yes");
    const unanimous = await svc.amendmentStatus(ent);
    assert.equal((unanimous.body as Record<string, Json>)["passed"], false);
    assert.match(String((unanimous.body as Record<string, Json>)["reason"]), /R2/);

    // With the operator key's co-signature it passes.
    const cosig = await signJson(operator.privateKey, { op: "cosign", proposal: ent });
    const co = await svc.cosignAmendment({ proposal: ent, signature: cosig });
    assert.equal((co.body as Record<string, Json>)["passed"], true);

    // A forged co-signature is refused.
    const forged = await generateKeyPair();
    const badSig = await signJson(forged.privateKey, { op: "cosign", proposal: ent });
    const bad = await svc.cosignAmendment({ proposal: ent, signature: badSig });
    assert.equal(bad.status, 401);
    void reg;
  });
});
