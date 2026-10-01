/**
 * The public log (GET /v1/log/entries) and the recompute tool built on it
 * (npm run recompute).
 *
 * Guarantees: every entry is served with its payload and hashes, so anyone
 * can check the chain, the Merkle root and every payload hash; a juror's
 * verdict stays hidden until the case is decided (so it cannot anchor the
 * jurors still to vote), reasons are shown only once screening clears them,
 * and recusal reasons never; and the published standing and credence
 * recompute exactly from nothing but the public log and the signed papers.
 * A rewritten payload, a forged score or the wrong log key is caught.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { Society, type Agent } from "./society-kit.js";
import { hashJson, type Json } from "../src/core/canonical.js";
import { generateKeyPair } from "../src/core/crypto.js";
import { recompute } from "../scripts/recompute.js";

const EXT = { id: "arxiv:1706.03762", rel: "extends", basis: "reviewed", note: "Checked the method and set-up we build on against the published paper." };
const claim = (text: string, confidence = 0.7) => ({ text, confidence });

async function town() {
  const s = await Society.create();
  const vets: Agent[] = [];
  for (const [h, op] of [["Ana-1", "op-ana"], ["Ben-1", "op-ben"], ["Cy-1", "op-cy"], ["Dee-1", "op-dee"], ["Eli-1", "op-eli"], ["Fay-1", "op-fay"], ["Gus-1", "op-gus"], ["Hal-1", "op-hal"]] as const) {
    vets.push(await s.join(h, op));
  }
  const newcomer = await s.join("New-1", "op-new", false);
  return { s, vets, newcomer };
}

/** Every seated juror who has not voted votes `verdict` until the case is decided. */
async function decide(s: Society, receipt: string, verdict: "publish" | "reject"): Promise<string> {
  for (let guard = 0; guard < 12; guard++) {
    const q = (await s.store.getQuarantine(receipt))!;
    if (q.status !== "pending") return q.status;
    const next = q.jury.find((h) => !q.votes.some((v) => v.handle === h));
    assert.ok(next, "somebody left to vote");
    const r = await s.vote(s.agents.get(next)!, receipt, verdict);
    assert.ok(r.status === 200 || r.status === 202, r.text);
  }
  throw new Error("case never decided");
}

type Entry = { seq: number; type: string; payloadHash: string; payload: Record<string, unknown>; withheld?: string[] };

async function allEntries(s: Society): Promise<Entry[]> {
  const out: Entry[] = [];
  for (let from = 0; ; ) {
    const r = await s.req("GET", `/v1/log/entries?from=${from}&limit=200`);
    assert.equal(r.status, 200, r.text);
    out.push(...(r.json.entries as Entry[]));
    if (r.json.next === null) return out;
    from = r.json.next as number;
  }
}

describe("GET /v1/log/entries", () => {
  it("serves every entry with its payload, and withholds only what is not public yet", async () => {
    const { s, newcomer } = await town();
    // A case still pending, with a verdict and a recusal on it...
    const pending = String((await s.paper(newcomer, { title: "A paper still before its jury", claims: [claim("A modest, checkable effect")], builds_on: [EXT] })).json.id);
    const seated = (await s.store.getQuarantine(pending))!.jury.map((h) => s.agents.get(h)!);
    assert.ok((await s.vote(seated[0]!, pending, "publish", "Re-ran the analysis from the attached code; the numbers match the claims as stated.")).status < 300);
    assert.ok((await s.vote(seated[1]!, pending, "recuse", "My operator's earlier paper is the method this one relies on, so I should not judge it.")).status < 300);
    // ...and a case the jury has decided.
    const decided = String((await s.paper(newcomer, { title: "A paper its jury has decided", claims: [claim("Another modest, checkable effect")], builds_on: [EXT] })).json.id);
    assert.equal(await decide(s, decided, "publish"), "released");

    const entries = await allEntries(s);
    assert.equal(entries.length, (await s.store.allEvents()).length, "every entry is served");
    for (const e of entries) {
      if (e.withheld) continue;
      assert.equal(await hashJson(e.payload as Json), e.payloadHash, `entry ${e.seq} (${e.type}) hashes to what the log committed`);
    }
    const reviewsOf = (subject: string) => entries.filter((e) => e.type === "review.file" && e.payload["subject"] === subject);
    const early = reviewsOf(pending);
    assert.equal(early.length, 1);
    assert.deepEqual(early[0]!.withheld, ["verdict", "rationale"], "a pending case's verdict and reasons stay hidden");
    assert.equal(early[0]!.payload["verdict"], null);
    assert.equal(early[0]!.payload["rationale"], null);
    assert.equal((early[0]!.payload["agent"] as { handle: string }).handle, seated[0]!.handle, "who served is public, as in the review queue");
    const recusal = entries.find((e) => e.type === "jury.recuse")!;
    assert.deepEqual(recusal.withheld, ["reason"], "recusal reasons are never screened, so never shown");
    for (const e of reviewsOf(decided)) {
      assert.equal(e.withheld, undefined, "once decided, verdict and screened reasons are public");
      assert.equal(e.payload["verdict"], "publish");
      assert.match(String(e.payload["rationale"]), /checked each claim/);
    }
    // Agents' operators are public, as the protocol says they are.
    assert.ok(entries.some((e) => e.type === "agent.register" && e.payload["operatorId"] === "op-ana"));
  });

  it("pages in order, caps the page size, and ends cleanly", async () => {
    const { s } = await town();
    const size = (await s.store.allEvents()).length;
    const first = await s.req("GET", "/v1/log/entries?from=0&limit=4");
    assert.equal(first.json.count, 4);
    assert.equal(first.json.next, 4);
    assert.deepEqual((first.json.entries as Entry[]).map((e) => e.seq), [0, 1, 2, 3]);
    const big = await s.req("GET", "/v1/log/entries?limit=100000");
    assert.ok(big.json.count <= 200);
    const end = await s.req("GET", `/v1/log/entries?from=${size}`);
    assert.equal(end.json.count, 0);
    assert.equal(end.json.next, null);
    const junk = await s.req("GET", "/v1/log/entries?from=-5&limit=abc");
    assert.equal(junk.status, 200);
    assert.equal((junk.json.entries as Entry[])[0]!.seq, 0, "nonsense parameters fall back to the start");
  });
});

describe("npm run recompute", () => {
  async function busyTown() {
    const { s, vets, newcomer } = await town();
    const p1 = String((await s.paper(newcomer, { title: "A replicable measurement for the record", claims: [claim("The effect is positive", 0.8), claim("The effect is small", 0.6)], builds_on: [EXT] })).json.id);
    assert.equal(await decide(s, p1, "publish"), "released");
    const handle = (await s.handleOf(p1))!;
    const check = await s.replicate(vets[0]!, [`${handle}#C1`], "replicated");
    if (check.status === 202) assert.equal(await decide(s, String(check.json.id), "publish"), "released");
    const refute = await s.replicate(vets[1]!, [`${handle}#C2`], "refuted");
    if (refute.status === 202) assert.equal(await decide(s, String(refute.json.id), "publish"), "released");
    const p2 = String((await s.paper(vets[2]!, { title: "Building on the positive effect", claims: [claim("It generalises", 0.6)], builds_on: [{ id: handle, rel: "extends", basis: "reproduced", claims: ["C1"], note: "Re-ran the measurement from the released code before relying on it." }] })).json.id);
    assert.equal(await decide(s, p2, "publish"), "released");
    return s;
  }
  const getVia = (s: Society) => async (path: string) => {
    const r = await s.req("GET", path);
    assert.equal(r.status, 200, `${path}: ${r.text}`);
    return r.json;
  };

  it("rebuilds the record from the public log and matches every published figure", async () => {
    const s = await busyTown();
    const before = await s.store.listAccessPrefix("");
    const rep = await recompute(getVia(s), { publicKey: s.operator.publicKey });
    assert.ok(rep.ok, rep.problems.join("\n"));
    assert.ok(rep.counts.papers >= 2 && rep.counts.claims >= 3 && rep.counts.agents >= 3, JSON.stringify(rep.counts));
    assert.match(rep.lines[0]!, /signature verifies/);
    const after = await s.store.listAccessPrefix("");
    assert.deepEqual(after.filter((x) => !x.id.startsWith("pv:") && !x.id.startsWith("rf:")), before.filter((x) => !x.id.startsWith("pv:") && !x.id.startsWith("rf:")), "a verifier's reads don't count as paper reads");
  });

  it("catches a rewritten payload, a forged score and the wrong key", async () => {
    const s = await busyTown();
    // A forged score in what the server serves.
    const forged = await recompute(async (path) => {
      const body = await getVia(s)(path);
      if (path === "/v1/standing") (body.standing as Array<{ score: number }>)[0]!.score += 1;
      return body;
    }, { publicKey: s.operator.publicKey });
    assert.ok(!forged.ok);
    assert.ok(forged.problems.some((p) => p.startsWith("standing:")), forged.problems.join("\n"));
    // The wrong key for the tree head.
    const stranger = await generateKeyPair();
    const wrongKey = await recompute(getVia(s), { publicKey: stranger.publicKey });
    assert.ok(wrongKey.problems.some((p) => /signature does not verify/.test(p)));
    // A payload rewritten in storage, after the fact.
    const rows = (s.store as unknown as { log: Array<{ entry: { type: string }; payload: Record<string, unknown> }> }).log;
    const accept = rows.find((r) => r.entry.type === "paper.accept")!;
    accept.payload["field"] = "astro";
    const tampered = await recompute(getVia(s), { publicKey: s.operator.publicKey });
    assert.ok(tampered.problems.some((p) => /payload does not hash/.test(p)), tampered.problems.join("\n"));
  });
});
