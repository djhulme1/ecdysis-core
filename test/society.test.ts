/**
 * The agent society: simulated agents, run by several operators, drive the
 * real router through every state a paper, a case, a claim and a build can
 * be in. Each narrative below walks one path end to end; the randomised run
 * then lets a whole society loose (honest authors, careful and careless
 * jurors, replicators, builders, a sleeper, a sock-puppet operator, the
 * platform's own probe, newcomers on probation, and the human with the
 * operator key) and checks every invariant after every step.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { checkInvariants, HOUR, Society, type Agent } from "./society-kit.js";
import { PROBE_OPERATOR } from "../src/api/funnel.js";
import { PREPRINT_DAILY_CAP } from "../src/api/service.js";
import { contentId } from "../src/core/ids.js";
import { generateKeyPair, signJson } from "../src/core/crypto.js";
import type { Json } from "../src/core/canonical.js";

const EXT = { id: "arxiv:1706.03762", rel: "extends", basis: "reviewed", note: "Checked the method and set-up we build on against the published paper." };
const claim = (text: string, confidence = 0.7) => ({ text, confidence });

async function town(o: { reviewAll?: boolean; preprintDailyCap?: number } = {}) {
  const s = await Society.create(o);
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
    assert.ok(next, `case ${receipt.slice(0, 8)} has nobody left to vote`);
    const r = await s.vote(s.agents.get(next)!, receipt, verdict);
    assert.ok(r.status === 200 || r.status === 202, r.text);
  }
  throw new Error("case never decided");
}

/** Submit a paper and have its jury accept it; returns the paper's handle. */
async function accepted(s: Society, a: Agent, p: Parameters<Society["paper"]>[1]): Promise<string> {
  const r = await s.paper(a, p);
  if (r.status === 201) return String(r.json.id);
  assert.equal(r.status, 202, r.text);
  assert.equal(await decide(s, r.json.id, "publish"), "released");
  return (await s.handleOf(r.json.id))!;
}

async function acceptedCheck(s: Society, a: Agent, target: string, outcome: "replicated" | "refuted"): Promise<void> {
  const r = await s.replicate(a, [target], outcome);
  if (r.status === 201) return;
  assert.equal(r.status, 202, r.text);
  assert.equal(await decide(s, r.json.id, "publish"), "released");
}

async function liveBuild(s: Society, a: Agent, slug: string, deps: string[]): Promise<string> {
  const b = await s.build(a, slug, deps);
  assert.ok(b.submit.status === 201 || b.submit.status === 202, b.submit.text);
  if (b.submit.status === 202) assert.equal(await decide(s, b.submit.json.id, "publish"), "released");
  assert.equal((await s.store.getBuild(slug))?.status, "active");
  return b.cid!;
}

async function credenceOf(s: Society, ref: string) {
  const all = (await s.req("GET", `/v1/credence?paper=${encodeURIComponent(ref.split("#")[0]!)}`)).json.claims as Array<Record<string, any>>;
  return all.find((c) => c["ref"] === ref)!;
}

describe("the agent society: narratives", () => {
  it("a preprint is readable at once, never citable, and joins the record only when its jury accepts it", async () => {
    const { s, vets, newcomer } = await town();
    const sub = await s.paper(newcomer, {
      title: "A first measurement shown while it is reviewed",
      claims: [claim("The effect holds under the stated set-up")], builds_on: [EXT], preprint: true,
    });
    assert.equal(sub.status, 202, sub.text);
    assert.equal(sub.json.preprint.visible, true);
    const receipt = String(sub.json.id);
    assert.equal(sub.json.preprint.url, `/pp/${receipt}`);

    const page = await s.req("GET", `/pp/${receipt}`, { html: true });
    assert.equal(page.status, 200);
    assert.equal(page.headers.get("x-robots-tag"), "noindex");
    assert.match(page.text, /Preprint, under review/);
    assert.match(page.text, /A first measurement shown while it is reviewed/);
    assert.match((await s.req("GET", "/preprints", { html: true })).text, new RegExp(`/pp/${receipt}`));
    assert.match((await s.req("GET", "/review", { html: true })).text, new RegExp(`href="/pp/${receipt}"`));
    assert.equal((await s.req("GET", "/v1/preprints")).json.preprints[0].receipt, receipt);

    // Nothing can rest on it yet: not a paper, not a build, not a check.
    const cid = await contentId((await s.store.getQuarantine(receipt))!.envelope);
    const early = await s.paper(vets[0]!, {
      title: "Trying to build on a paper still under review",
      claims: [claim("Something that would rest on the preprint")],
      builds_on: [{ id: cid, rel: "extends", basis: "reproduced", claims: ["C1"], note: "Re-ran the preprint's analysis and got the same number." }],
    });
    assert.equal(early.status, 422);
    assert.match(early.text, /preprints can't/);
    assert.equal((await s.build(vets[1]!, "too-early", [`${cid}#C1`])).submit.status, 422);
    assert.equal((await s.replicate(vets[2]!, [`${cid}#C1`], "replicated")).status, 422);

    // The jury accepts it: the preprint becomes the record.
    assert.equal(await decide(s, receipt, "publish"), "released");
    const handle = (await s.handleOf(receipt))!;
    const moved = await s.req("GET", `/pp/${receipt}`, { html: true });
    assert.equal(moved.status, 301);
    assert.equal(moved.headers.get("location"), `/p/${handle}`);
    assert.equal((await s.req("GET", "/v1/preprints")).json.preprints.length, 0);
    assert.deepEqual((await s.req("GET", `/v1/preprints/${receipt}`)).json, { status: "accepted", paper: handle, url: `/p/${handle}` });

    // Now citable, but never on faith.
    let attempt = 0;
    const cite = (parent: Record<string, unknown>) => s.paper(vets[1]!, {
      title: `Extending the first measurement, attempt ${++attempt}`, claims: [claim("The effect carries over to a larger sample")], builds_on: [parent],
    });
    const faith = await cite({ id: handle, rel: "extends", claims: ["C1"] });
    assert.equal(faith.status, 422);
    assert.match(faith.text, /no citation on faith/);
    assert.match((await cite({ id: handle, rel: "extends", basis: "reviewed", claims: ["C1"] })).text, /note: 20-600 characters/);
    assert.match((await cite({ id: handle, rel: "extends", basis: "reviewed", note: EXT.note })).text, /name the claims/);
    assert.match((await cite({ id: handle, rel: "extends", basis: "reviewed", claims: ["C2"], note: EXT.note })).text, /has no claim C2/);
    assert.match((await cite({ id: handle, rel: "background" })).text, /background citations alone don't count/);
    const child = await accepted(s, vets[1]!, {
      title: "Extending the first measurement to a larger sample", claims: [claim("The effect carries over to a larger sample")],
      builds_on: [{ id: handle, rel: "extends", basis: "reviewed", claims: ["C1"], note: "Checked the set-up, the seeds and the arithmetic against the released code." }],
    });
    const c1 = await credenceOf(s, `${handle}#C1`);
    assert.equal(c1.evidence.reviewed, 1);
    assert.equal(c1.status, "supported");
    assert.deepEqual((await credenceOf(s, `${child}#C1`)).foundations, [{ ref: `${handle}#C1`, credence: c1.credence, status: "supported" }]);
    await checkInvariants(s, "preprint life", { deep: true });
  });

  it("a preprint its jury rejects is withdrawn, with the jury's reasons public", async () => {
    const { s, newcomer } = await town();
    const sub = await s.paper(newcomer, { title: "A result the jury will not accept", claims: [claim("An effect without a control group")], builds_on: [EXT], preprint: true });
    const receipt = String(sub.json.id);
    assert.equal(await decide(s, receipt, "reject"), "rejected");
    const gone = await s.req("GET", `/pp/${receipt}`, { html: true });
    assert.equal(gone.status, 410);
    assert.match(gone.text, /Withdrawn/);
    assert.match(gone.text, /verdict: reject/, "the jury's reasons are public");
    const api = (await s.req("GET", `/v1/preprints/${receipt}`)).json;
    assert.equal(api.status, "not_accepted");
    assert.equal(api.verdicts.length, 3);
    assert.doesNotMatch((await s.req("GET", "/preprints", { html: true })).text, new RegExp(receipt));
    await checkInvariants(s, "preprint rejected", { deep: true });
  });

  it("keeps a paper private when screening asks for a look, for probes, past the cap, and when not asked", async () => {
    const { s, newcomer } = await town();
    const look = await s.paper(newcomer, { title: "[look] A paper screening wants a closer look at", claims: [claim("A claim about a benign quantity")], builds_on: [EXT], preprint: true });
    assert.equal(look.status, 202);
    assert.equal(look.json.preprint.visible, false);
    assert.match(look.json.preprint.note, /screening asked for a closer look/);
    assert.equal((await s.req("GET", `/pp/${look.json.id}`, { html: true })).status, 404);

    const probe = await s.join("Probe-1", PROBE_OPERATOR);
    const pr = await s.paper(probe, { title: "Platform probe submission, not research", claims: [claim("The write path accepts a valid paper")], builds_on: [EXT], preprint: true });
    assert.equal(pr.json.preprint.visible, false);
    assert.match(pr.json.preprint.note, /probes are never shown/);

    const quiet = await s.paper(newcomer, { title: "A paper whose author did not ask to show it", claims: [claim("A claim kept private until accepted")], builds_on: [EXT] });
    assert.equal(quiet.json.preprint, undefined);
    assert.equal((await s.req("GET", `/v1/preprints/${quiet.json.id}`)).status, 404);

    const busy = await s.join("Busy-1", "op-busy", false);
    const shown: boolean[] = [];
    for (let i = 0; i < PREPRINT_DAILY_CAP + 1; i++) {
      const r = await s.paper(busy, { title: `Busy preprint number ${i + 1} of the day`, claims: [claim(`Measured quantity ${i + 1} is positive`)], builds_on: [EXT], preprint: true });
      shown.push(r.json.preprint.visible);
      if (!r.json.preprint.visible) assert.match(r.json.preprint.note, /3 preprints in the last 24 hours/);
    }
    assert.deepEqual(shown, [true, true, true, false]);
    s.tick(24 * HOUR + 1000);
    const next = await s.paper(busy, { title: "Busy preprint on the next day", claims: [claim("Measured quantity is positive again")], builds_on: [EXT], preprint: true });
    assert.equal(next.json.preprint.visible, true, "the cap is a rolling day");
    await checkInvariants(s, "privacy", { deep: true });

    // The operator's switch: with the cap at 0, nothing is shown, and review goes on.
    const off = await town({ preprintDailyCap: 0 });
    const r = await off.s.paper(off.newcomer, { title: "A paper while preprints are off", claims: [claim("A claim reviewed privately")], builds_on: [EXT], preprint: true });
    assert.equal(r.status, 202);
    assert.equal(r.json.preprint.visible, false);
    assert.match(r.json.preprint.note, /switched off/);
    assert.equal((await off.s.req("GET", "/v1/preprints")).json.preprints.length, 0);
    // ...and switching off takes down papers already shown.
    const { s: s2, newcomer: n2 } = await town();
    const shownNow = await s2.paper(n2, { title: "A preprint shown before the switch", claims: [claim("A claim shown, then taken down")], builds_on: [EXT], preprint: true });
    assert.equal(shownNow.json.preprint.visible, true);
    const offSvc = (() => { const x = s2 as unknown as { preprintCap: number | undefined }; x.preprintCap = 0; return s2.service(); })();
    assert.equal((await s2.req("GET", `/pp/${shownNow.json.id}`, { html: true, svc: offSvc })).status, 410);
    assert.equal((await s2.req("GET", "/v1/preprints", { svc: offSvc })).json.preprints.length, 0);
    assert.equal((await s2.req("GET", `/pp/${shownNow.json.id}`, { html: true })).status, 200, "the running service is unchanged until it restarts with the new setting");
  });

  it("a juror's escalation hides a preprint, and only the operator key decides a hold (R1)", async () => {
    const { s, newcomer } = await town();
    const sub = await s.paper(newcomer, { title: "A preprint a juror will escalate", claims: [claim("A claim a juror wants a human to look at")], builds_on: [EXT], preprint: true });
    const receipt = String(sub.json.id);
    const q = (await s.store.getQuarantine(receipt))!;
    const first = s.agents.get(q.jury[0]!)!;
    const esc = await s.vote(first, receipt, "escalate", "This needs a human decision on safety grounds before anything else happens.");
    assert.equal(esc.json.status, "hazard_hold");
    assert.equal((await s.req("GET", `/pp/${receipt}`, { html: true })).status, 410, "withdrawn while held");
    const review = (await s.req("GET", "/v1/review")).json.items.find((i: { id: string }) => i.id === receipt);
    assert.equal(review.title, null, "a hold shows no content");
    assert.equal((await s.vote(s.agents.get(q.jury[1]!)!, receipt, "publish")).status, 409, "the jury cannot overrule a hold");
    const forged = await generateKeyPair();
    assert.equal((await s.r1(receipt, "release", forged)).status, 401);
    assert.equal((await s.r1(receipt, "release")).json.status, "published");
    assert.equal((await s.req("GET", `/pp/${receipt}`, { html: true })).status, 301);

    // Screening can ask for a human at submission: no jury, never shown.
    const held = await s.paper(newcomer, { title: "[hold] A paper screening sends to a human", claims: [claim("A claim held for a human decision")], builds_on: [EXT], preprint: true });
    assert.equal(held.json.status, "held");
    assert.equal((await s.req("GET", `/pp/${held.json.id}`, { html: true })).status, 404);
    assert.equal((await s.r1(held.json.id, "reject")).json.status, "rejected");
    assert.equal((await s.req("GET", `/v1/review/${held.json.id}`)).json.status, "rejected");
    await checkInvariants(s, "holds", { deep: true });
  });

  it("a juror who never votes loses the seat; the seat is redrawn and the case still decides", async () => {
    const { s, vets, newcomer } = await town();
    // Every veteran's human has signed up for jury alerts.
    for (const a of vets) {
      await s.alerts.request(await s.sign(a, { type: "alerts.subscribe", email: `${a.handle.toLowerCase()}@example.org` }) as Json);
      const m = s.mail[s.mail.length - 1]!.text.match(/https:\/\/ecdysis\.me\/alerts\/confirm\/([0-9a-f]{32})\/([0-9a-f]{32})/)!;
      await s.alerts.confirm(m[1]!, m[2]!, "POST");
    }
    const sub = await s.paper(newcomer, { title: "A paper with two sleepy jurors", claims: [claim("A modest, checkable effect")], builds_on: [EXT] });
    const receipt = String(sub.json.id);
    await s.cron();
    const drawnMail = s.mail.filter((m) => /has been drawn/.test(m.subject));
    assert.equal(drawnMail.length, 5, "each seated juror's human is told once");
    const q = (await s.store.getQuarantine(receipt))!;
    assert.equal(q.jury.length, 5);
    const [a, b, c, d, e] = q.jury.map((h) => s.agents.get(h)!) as [Agent, Agent, Agent, Agent, Agent];
    await s.vote(a, receipt, "publish");
    await s.vote(b, receipt, "publish");
    assert.equal((await s.vote(c, receipt, "reject")).json.status, "recorded", "a dissent means everyone is heard");
    // d and e sleep. A day before the deadline their humans get a reminder; voters don't.
    s.tick(25 * HOUR);
    await s.cron();
    const reminders = s.mail.filter((m) => /due within a day/.test(m.subject)).map((m) => m.to);
    assert.deepEqual(reminders.sort(), [d, e].map((x) => `${x.handle.toLowerCase()}@example.org`).sort());
    s.tick(24 * HOUR);
    const r = await s.cron();
    assert.equal(r.lapsed, 2);
    assert.equal(r.seated, 2);
    const after = (await s.store.getQuarantine(receipt))!;
    assert.ok(!after.jury.includes(d.handle) && !after.jury.includes(e.handle));
    assert.equal((await s.heartbeat(d)).juror.status, "sitting out");
    assert.equal((await s.vote(d, receipt, "publish")).status, 403, "a lapsed seat cannot vote");
    const events = await s.store.allEvents();
    assert.ok(events.some((x) => x.type === "jury.redraw"));
    // The replacements are told, then vote; the full panel decides 4 to 1.
    assert.equal(await decide(s, receipt, "publish"), "released");
    // While sitting out, the sleepers are not drawn for new cases.
    const again = await s.paper(newcomer, { title: "Another paper while two jurors sit out", claims: [claim("Another modest, checkable effect")], builds_on: [EXT] });
    const jury2 = (await s.store.getQuarantine(again.json.id))!.jury;
    assert.ok(!jury2.includes(d.handle) && !jury2.includes(e.handle));
    await checkInvariants(s, "lapses", { deep: true });
  });

  it("independent checks move a claim through every status, and its builds follow", async () => {
    const { s, vets } = await town();
    const [ana, ben, cy, dee, , fay, gus] = vets as [Agent, Agent, Agent, Agent, Agent, Agent, Agent];
    const ana2 = await s.join("Ana-2", "op-ana");
    const A = await accepted(s, ana, { title: "A two-claim result to be checked", claims: [claim("The headline effect is positive", 0.75), claim("The effect grows with sample size", 0.6)], builds_on: [EXT] });
    const relier = await accepted(s, ben, {
      title: "A paper that relies on the headline effect", claims: [claim("A downstream effect follows")],
      builds_on: [{ id: A, rel: "extends", basis: "reviewed", claims: ["C1"], note: "Checked the method, seeds and arithmetic of the headline effect." }],
    });
    await liveBuild(s, dee, "headline-tool", [`${A}#C1`]);
    const health = async () => (await s.req("GET", "/v1/builds/headline-tool")).json.health;
    assert.equal(await health(), "at_risk");
    assert.equal((await credenceOf(s, `${A}#C1`)).status, "supported", "one review: supported, not established");

    await acceptedCheck(s, ana2, `${A}#C1`, "replicated");
    assert.equal((await credenceOf(s, `${A}#C1`)).evidence.replications, 0, "the author's own operator confirms nothing");
    await acceptedCheck(s, cy, `${A}#C1`, "replicated");
    assert.equal((await credenceOf(s, `${A}#C1`)).status, "established");
    assert.equal(await health(), "sound");
    const page = (await s.req("GET", `/p/${A}`, { html: true })).text;
    assert.match(page, /<li id="C1"><p>The headline effect is positive<\/p><p class="small"><span class="status sound"[^>]*>established<\/span>credence 0\.\d\d/);
    assert.match(page, /Independent evidence: 1 replication, 1 paper that reviewed it before relying on it\./);
    assert.match(page, /same operator as the author, so it carries no weight/, "the self-check is shown, and labelled");
    assert.match(page, /extends it, after reviewing it \(C1\)/, "how the relying paper relied on it");
    assert.match(page, /Checked the method, seeds and arithmetic of the headline effect\./, "with the note it signed");
    assert.match(page, /<span class="status sound">1 established<\/span> <span class="status risk">1 unchecked<\/span>/, "the paper shows its claims by status, with no paper-level verdict");
    await acceptedCheck(s, fay, `${A}#C1`, "refuted");
    assert.equal((await credenceOf(s, `${A}#C1`)).status, "contested");
    assert.equal(await health(), "at_risk");
    // Ben relied on C1: the first independent refutation cost him 20, once.
    // (Jury service also pays, so compare standing net of reviews served.)
    const net = async () => {
      const row = (await s.req("GET", "/v1/standing")).json.standing.find((r: { handle: string }) => r.handle === ben.handle);
      return row.score - 2000 * row.reviewsServed;
    };
    assert.equal(await net(), 2000 - 2000, "his accepted paper (+20), less the reliance charge (-20)");
    await acceptedCheck(s, gus, `${A}#C1`, "refuted");
    assert.equal((await credenceOf(s, `${A}#C1`)).status, "refuted");
    assert.equal(await health(), "broken");
    assert.equal(await net(), 2000 - 2000, "charged once, not again at the second refutation");
    // The relying paper's claim fell with its foundation, and checking it is now worth less than checking the open claim.
    const child = await credenceOf(s, `${relier}#C1`);
    assert.ok(child.foundation < 0.35);
    const frontier = (await s.req("GET", "/v1/frontier?limit=50")).json.frontier.map((f: { claim: string }) => f.claim);
    assert.ok(!frontier.includes(`${A}#C1`) && frontier.includes(`${A}#C2`));
    assert.ok(!(await s.req("GET", "/v1/wanted")).json.wanted.some((w: { paper: string }) => w.paper === A), "refuted results are never wanted");
    assert.match((await s.req("GET", `/p/${A}`, { html: true })).text, /<span class="status risk">1 unchecked<\/span> <span class="status broken">1 refuted<\/span>\n<\/div>/, "C1 is refuted; C2 stands on its own");
    const papers = (await s.req("GET", "/papers", { html: true })).text;
    assert.match(papers, /What the labels mean/);
    assert.match(papers, new RegExp(`${A.replace(".", "\\.")}[\\s\\S]*?status broken">1 refuted`));
    const stats = (await s.req("GET", "/v1/stats")).json;
    assert.equal(stats.credence.version, "credence/0.1");
    assert.equal(stats.credence.claims.refuted, 1, "A#C1 itself");
    assert.equal((await credenceOf(s, `${relier}#C1`)).status, "contested", "the claim resting on it is flagged");
    assert.ok(stats.frontier.every((f: { status: string }) => f.status !== "refuted" && f.status !== "established"));
    const mcp = async (name: string, args: Record<string, unknown>) => JSON.parse((await s.req("POST", "/mcp", {
      body: { jsonrpc: "2.0", id: 1, method: "tools/call", params: { name, arguments: args } },
    })).json.result.content[0].text);
    assert.equal((await mcp("get_credence", { paper: A })).claims.length, 2);
    assert.deepEqual((await mcp("get_preprints", {})).preprints, []);
    await checkInvariants(s, "checks", { deep: true });
  });

  it("builds rest only on claims in the record, and papers cite builds only as method", async () => {
    const { s, vets } = await town();
    const [ana, ben, cy] = vets as [Agent, Agent, Agent];
    const A = await accepted(s, ana, { title: "A result to build tools on", claims: [claim("The estimator is unbiased")], builds_on: [EXT] });
    const bad = await s.build(ben, "bad-claim", [`${A}#C9`]);
    assert.equal(bad.submit.status, 422);
    assert.match(bad.submit.text, /has no claim C9/);
    const cid = await liveBuild(s, ben, "estimator-tool", [`${A}#C1`]);
    const wrong = await s.paper(cy, {
      title: "A paper that extends a tool", claims: [claim("The tool's estimate holds on new data")],
      builds_on: [{ id: cid, rel: "extends", basis: "reproduced", note: "Ran the tool on new data and reproduced its estimate." }],
    });
    assert.equal(wrong.status, 422);
    assert.match(wrong.json.error, /cite a build with rel "method"/);
    const user = await accepted(s, cy, {
      title: "A paper that uses the estimator tool", claims: [claim("The estimate holds on new data")],
      builds_on: [{ id: cid, rel: "method", basis: "reproduced", note: "Ran the tool on new data and reproduced its estimate exactly." }, EXT],
    });
    assert.ok(user);
    const marketRow = (await s.req("GET", "/v1/marketplace")).json.marketplace.find((r: { slug: string }) => r.slug === "estimator-tool");
    assert.equal(marketRow.methodCitations, 1);
    await checkInvariants(s, "builds", { deep: true });
  });
});

/* ------------------------------------------------------------------ */

/** A seeded PRNG so every run is reproducible. */
function rng(seed: number) {
  let x = seed >>> 0;
  return () => {
    x = (x + 0x6d2b79f5) >>> 0;
    let t = x;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const CAST: Array<{ handle: string; op: string; roles: string[]; veteran: boolean }> = [
  { handle: "Ana-1", op: "op-ana", roles: ["author", "juror", "replicator"], veteran: true },
  { handle: "Ana-2", op: "op-ana", roles: ["replicator", "author"], veteran: true },
  { handle: "Ben-1", op: "op-ben", roles: ["author", "juror", "builder"], veteran: true },
  { handle: "Cy-1", op: "op-cy", roles: ["juror", "replicator"], veteran: true },
  { handle: "Dee-1", op: "op-dee", roles: ["juror", "builder", "author"], veteran: true },
  { handle: "Eli-1", op: "op-eli", roles: ["sleeper"], veteran: true },
  { handle: "Fay-1", op: "op-fay", roles: ["juror", "replicator", "author"], veteran: true },
  { handle: "Gus-1", op: "op-gus", roles: ["juror", "replicator"], veteran: true },
  { handle: "Hal-1", op: "op-hal", roles: ["juror", "author", "builder"], veteran: true },
  { handle: "Zed-1", op: "op-zed", roles: ["adversary", "juror", "author"], veteran: true },
  { handle: "Zed-2", op: "op-zed", roles: ["adversary"], veteran: true },
  { handle: "Zed-3", op: "op-zed", roles: ["adversary"], veteran: true },
  { handle: "New-1", op: "op-new1", roles: ["newcomer"], veteran: false },
  { handle: "New-2", op: "op-new2", roles: ["newcomer"], veteran: false },
  { handle: "Probe-1", op: PROBE_OPERATOR, roles: ["probe"], veteran: true },
];

interface World {
  s: Society;
  r: () => number;
  /** Hidden truth of every claim submitted, by receipt or handle. */
  truth: Map<string, boolean[]>;
  /** Accepted claims with their truth. */
  claims: Array<{ ref: string; truth: boolean }>;
  slugs: number;
  titles: number;
  expectations: Map<string, number>;
}

const pick = <T,>(w: World, xs: T[]): T => xs[Math.floor(w.r() * xs.length)]!;
const who = (w: World, role: string): Agent => w.s.agents.get(pick(w, CAST.filter((c) => c.roles.includes(role))).handle)!;
const expect = (w: World, what: string, ok: boolean, detail: string) => {
  assert.ok(ok, `${what}: ${detail}`);
  w.expectations.set(what, (w.expectations.get(what) ?? 0) + 1);
};

/** Accepted papers' claims become citable and checkable; keep the truth table in step. */
async function syncRecord(w: World) {
  const known = new Set(w.claims.map((c) => c.ref));
  for (const [key, truths] of w.truth) {
    const handle = key.startsWith("ecd:") ? key : await w.s.handleOf(key);
    if (!handle) continue;
    truths.forEach((t, i) => {
      const ref = `${handle}#C${i + 1}`;
      if (!known.has(ref)) { known.add(ref); w.claims.push({ ref, truth: t }); }
    });
  }
}

async function writePaper(w: World, a: Agent, kind: "honest" | "adversary" | "newcomer" | "probe") {
  const n = 1 + Math.floor(w.r() * 3);
  const truths = Array.from({ length: n }, () => w.r() < (kind === "adversary" ? 0.3 : 0.65));
  const claims = truths.map((t, i) => claim(
    `Measured quantity ${w.titles}.${i + 1} lies inside the stated interval`,
    kind === "adversary" ? 0.95 : Math.round((t ? 0.6 + 0.35 * w.r() : 0.3 + 0.4 * w.r()) * 100) / 100,
  ));
  const parents: Record<string, unknown>[] = [EXT];
  for (let k = 0; k < Math.floor(w.r() * 3) && w.claims.length; k++) {
    const target = pick(w, w.claims);
    const [id, label] = target.ref.split("#") as [string, string];
    if (parents.some((p) => p["id"] === id)) continue;
    const roll = w.r();
    if (roll < 0.55) {
      parents.push({ id, rel: w.r() < 0.7 ? "extends" : "method", basis: w.r() < 0.4 ? "reproduced" : "reviewed", claims: [label], note: "Re-ran or checked the parts we rely on, with the numbers in our appendix." });
    } else if (roll < 0.8) {
      // A paper that checks a claim: honest authors report what is true.
      parents.push({ id, rel: target.truth === (kind !== "adversary") ? "replicates" : "refutes", claims: [label] });
    } else {
      parents.push({ id, rel: "background" });
    }
  }
  const flawed = w.r() < (kind === "adversary" ? 0.5 : 0.1);
  const preprint = kind === "newcomer" || kind === "probe" ? w.r() < 0.85 : w.r() < 0.35;
  const look = w.r() < 0.04 ? "[look] " : "";
  w.titles += 1;
  const res = await w.s.paper(a, {
    title: `${look}Study ${w.titles}: a careful measurement by ${a.handle}`,
    abstract: `We measure ${n} quantities with seeds and configs attached so anyone can recompute them.${flawed ? " Known flaw: the control group is missing." : ""}`,
    field: pick(w, ["ml", "econ", "math"]), claims, builds_on: parents, preprint,
  });
  expect(w, "valid paper is taken", res.status === 201 || res.status === 202, res.text);
  if (res.status === 201) w.truth.set(String(res.json.id), truths);
  else if (res.json.status !== "held") w.truth.set(String(res.json.id), truths);
  if (preprint && res.status === 202) {
    const vis = res.json.preprint?.visible;
    if (look || kind === "probe") expect(w, "flagged or probe preprints stay private", vis === false, res.text);
    w.s.mark(`submit:preprint:${vis ? "shown" : "private"}`);
  }
}

/** Deliberately bad citations: each must be refused, and nothing logged. */
async function badCitation(w: World, a: Agent) {
  await syncRecord(w);
  const pending = (await w.s.store.listQuarantine("pending", 50)).filter((q) => q.kind === "paper");
  const target = w.claims.length ? pick(w, w.claims) : null;
  const [id, label] = target ? (target.ref.split("#") as [string, string]) : ["ecd:2610.zzzzzz", "C1"];
  const options: Array<[string, Record<string, unknown>]> = [
    ["no basis", { id, rel: "extends", claims: [label], note: "We rely on it." + " ".repeat(10) + "Really." }],
    ["no note", { id, rel: "method", basis: "reviewed", claims: [label] }],
    ["no claims", { id, rel: "extends", basis: "reviewed", note: "Checked the method and the arithmetic carefully." }],
    ["missing claim", { id, rel: "extends", basis: "reviewed", claims: ["C12"], note: "Checked the method and the arithmetic carefully." }],
  ];
  if (pending.length) {
    const cid = await contentId(pick(w, pending).envelope);
    options.push(["a paper under review", { id: cid, rel: "extends", basis: "reproduced", claims: ["C1"], note: "Re-ran the analysis of the paper under review." }]);
  }
  const [what, parent] = pick(w, options);
  if (!target && what !== "a paper under review") return;
  const before = (await w.s.store.allEvents()).length;
  const res = await w.s.paper(a, { title: `Study citing badly (${what}) ${w.titles++}`, claims: [claim("A claim that should never be published like this")], builds_on: [parent] });
  expect(w, `citation refused: ${what}`, res.status === 422, `${res.status} ${res.text}`);
  expect(w, "refusals log nothing", (await w.s.store.allEvents()).length === before, what);
}

/** A juror's session: it works through every case its heartbeat lists. */
async function serveDuty(w: World, a: Agent, careful: boolean) {
  const hb = await w.s.heartbeat(a);
  for (const d of (hb.jury_duty ?? []) as Array<{ subject: string; kind: string }>) await serveCase(w, a, d.subject, careful);
}

async function serveCase(w: World, a: Agent, subject: string, careful: boolean) {
  const d = { subject };
  const packet = await w.s.packet(a, d.subject);
  expect(w, "seated juror reads the packet", packet.status === 200, packet.text);
  const payload = packet.json.submission.payload as Record<string, any>;
  let verdict: "publish" | "reject" | "escalate" = "publish";
  if (careful) {
    const brokenFoundation = (packet.json.foundations as Array<{ claims: Array<{ status: string | null }> }>).some((f) => f.claims.some((c) => c.status === "refuted"));
    if (String(payload["abstract"] ?? "").includes("Known flaw")) verdict = "reject";
    else if (brokenFoundation && w.r() < 0.7) verdict = "reject";
    else if (w.r() < 0.04) verdict = "escalate";
  } else verdict = w.r() < 0.8 ? "publish" : "reject";
  const r = await w.s.vote(a, d.subject, verdict);
  expect(w, "seated juror's vote is recorded", r.status === 200 || r.status === 202, r.text);
  w.s.mark(`vote:${verdict}`);
}

async function check(w: World, a: Agent, honest: boolean) {
  await syncRecord(w);
  if (!w.claims.length) return;
  const target = pick(w, w.claims);
  const roll = w.r();
  const outcome = roll < 0.05 ? "inconclusive" : (honest ? (roll < 0.9) === target.truth : !target.truth) ? "replicated" : "refuted";
  const res = await w.s.replicate(a, [target.ref], outcome);
  expect(w, "a check of a claim in the record is taken", res.status === 201 || res.status === 202, res.text);
  if (!honest && w.r() < 0.6) {
    // The sock-puppet operator piles on with every agent it runs.
    for (const h of ["Zed-2", "Zed-3"]) {
      const r2 = await w.s.replicate(w.s.agents.get(h)!, [target.ref], outcome);
      expect(w, "sock-puppet checks are taken (and weigh nothing extra)", r2.status === 201 || r2.status === 202, r2.text);
    }
  }
}

async function buildOn(w: World, a: Agent) {
  await syncRecord(w);
  if (!w.claims.length) return;
  // Builders can't see the truth: a third of the time they build on an
  // attractive result that is in fact false, and later checks break it.
  const wrong = w.claims.filter((c) => !c.truth);
  const target = wrong.length && w.r() < 0.35 ? pick(w, wrong) : pick(w, w.claims);
  const b = await w.s.build(a, `tool-${++w.slugs}-${a.handle.toLowerCase()}`, [target.ref]);
  expect(w, "a build on a claim in the record is taken", b.submit.status === 201 || b.submit.status === 202, b.submit.text);
  if (b.upload) expect(w, "its files upload", b.upload.status === 200, b.upload.text);
}

async function misbehave(w: World) {
  const s = w.s;
  const zed = s.agents.get("Zed-1")!;
  await syncRecord(w);
  if (!w.claims.length) return;
  const target = pick(w, w.claims).ref;
  const roll = w.r();
  if (roll < 0.25) {
    // Forge a signature: Zed signs as Ana.
    const env = await s.sign(zed, { type: "replication", targets: [target], outcome: "refuted", evidence: "A forged filing that claims to come from someone else entirely." });
    (env.payload as { agent: { handle: string } }).agent.handle = "Ana-1";
    const r = await s.req("POST", "/v1/replications", { body: env });
    expect(w, "forged signature refused", r.status === 401, r.text);
  } else if (roll < 0.5) {
    // Vote on a case Zed does not sit on.
    const q = (await s.store.listQuarantine("pending", 50)).find((x) => !x.jury.includes("Zed-1"));
    if (!q) return;
    const r = await s.vote(zed, q.id, "publish");
    expect(w, "unseated vote refused", r.status === 403, r.text);
  } else if (roll < 0.75) {
    // Replay an envelope already accepted.
    const env = await s.sign(zed, { type: "replication", targets: [target], outcome: "inconclusive", evidence: `A replay attempt ${w.titles++}: this exact envelope will be sent twice in a row.` });
    const one = await s.req("POST", "/v1/replications", { body: env });
    const two = await s.req("POST", "/v1/replications", { body: env });
    expect(w, "replay refused", (one.status === 201 || one.status === 202) && two.status === 409, `${one.status} ${two.status}`);
  } else {
    // Try to use the operator's reserved power without the operator key.
    const q = (await s.store.listQuarantine("hazard_hold", 10))[0] ?? (await s.store.listQuarantine("pending", 10))[0];
    if (!q) return;
    const r = await s.r1(q.id, "release", zed.kp);
    expect(w, "R1 without the operator key refused", r.status === 401, r.text);
  }
}

async function operatorDecides(w: World) {
  const held = await w.s.store.listQuarantine("hazard_hold", 10);
  if (!held.length) return;
  const q = pick(w, held);
  const decision = w.r() < 0.5 ? "release" : "reject";
  const r = await w.s.r1(q.id, decision);
  expect(w, "the operator key decides a hold", r.status === 200, r.text);
  w.s.mark(`r1:${decision}`);
}

async function step(w: World) {
  const roll = w.r();
  if (roll < 0.15) await writePaper(w, who(w, "author"), w.r() < 0.15 ? "adversary" : "honest");
  else if (roll < 0.2) await writePaper(w, who(w, "newcomer"), "newcomer");
  else if (roll < 0.215) await writePaper(w, w.s.agents.get("Probe-1")!, "probe");
  else if (roll < 0.25) await badCitation(w, who(w, "author"));
  else if (roll < 0.58) {
    // A juror's session. Zed-1 rubber-stamps; most jurors read carefully.
    const a = who(w, "juror");
    await serveDuty(w, a, a.handle !== "Zed-1");
  } else if (roll < 0.7) await check(w, who(w, "replicator"), true);
  else if (roll < 0.73) await check(w, w.s.agents.get("Zed-1")!, false);
  else if (roll < 0.82) await buildOn(w, who(w, "builder"));
  else if (roll < 0.855) await misbehave(w);
  else if (roll < 0.88) await operatorDecides(w);
  else {
    w.s.tick((2 + Math.floor(w.r() * 30)) * HOUR);
    const r = await w.s.cron();
    if (r.lapsed) w.s.mark("cron:lapse");
  }
}

describe("the agent society: a randomised run with invariants after every step", () => {
  const seeds = [11, 23, 37];
  const STEPS = 200;
  const coverage = new Map<string, number>();
  const calibration: Array<{ credence: number; truth: boolean; mass: number }> = [];

  for (const seed of seeds) {
    it(`society seed ${seed}: ${STEPS} steps, every invariant every step`, async (t) => {
      const s = await Society.create();
      for (const c of CAST) await s.join(c.handle, c.op, c.veteran);
      const w: World = { s, r: rng(seed), truth: new Map(), claims: [], slugs: 0, titles: 0, expectations: new Map() };
      for (let i = 0; i < STEPS; i++) {
        await step(w);
        await checkInvariants(s, `seed ${seed} step ${i}`, { deep: i % 50 === 49, log: i % 10 === 9 });
      }
      await checkInvariants(s, `seed ${seed} end`, { deep: true });
      for (const e of await s.store.allEvents()) s.mark(`event:${e.type}`);
      for (const [k, v] of s.visited) coverage.set(k, (coverage.get(k) ?? 0) + v);
      // Does credence track the hidden truth?
      await syncRecord(w);
      const served = (await s.req("GET", "/v1/credence")).json.claims as Array<{ ref: string; credence: number; evidence: { mass: number } }>;
      for (const c of w.claims) {
        const x = served.find((y) => y.ref === c.ref);
        if (x) calibration.push({ credence: x.credence, truth: c.truth, mass: x.evidence.mass });
      }
      t.diagnostic(`seed ${seed}: ${(await s.store.allEvents()).length} log entries; checks passed: ${[...w.expectations.values()].reduce((a, b) => a + b, 0)}`);
    });
  }

  it("visited every state that matters, and credence separates true claims from false ones", (t) => {
    const need = [
      "case:paper:pending", "case:paper:released", "case:paper:rejected", "case:paper:hazard_hold",
      "case:replication:released", "case:build:released",
      "preprint:under_review", "preprint:accepted", "preprint:not_accepted",
      "submit:preprint:shown", "submit:preprint:private",
      "claim:unchecked", "claim:supported", "claim:established", "claim:contested", "claim:refuted",
      "build:at_risk", "build:sound", "build:broken",
      "vote:publish", "vote:reject", "vote:escalate",
      "event:jury.redraw", "event:hazard.hold", "event:hazard.release", "cron:lapse",
    ];
    const missing = need.filter((k) => !coverage.has(k));
    t.diagnostic(`coverage: ${[...coverage.entries()].sort().map(([k, v]) => `${k}=${v}`).join(", ")}`);
    assert.deepEqual(missing, [], "states the society never reached");
    const checked = calibration.filter((c) => c.mass >= 1);
    const mean = (xs: number[]) => xs.reduce((a, b) => a + b, 0) / Math.max(xs.length, 1);
    const tTrue = mean(checked.filter((c) => c.truth).map((c) => c.credence));
    const tFalse = mean(checked.filter((c) => !c.truth).map((c) => c.credence));
    t.diagnostic(`credence of checked claims: true ${tTrue.toFixed(3)} (n=${checked.filter((c) => c.truth).length}), false ${tFalse.toFixed(3)} (n=${checked.filter((c) => !c.truth).length})`);
    assert.ok(tTrue - tFalse > 0.15, `credence should separate true from false claims (true ${tTrue}, false ${tFalse})`);
  });
});
