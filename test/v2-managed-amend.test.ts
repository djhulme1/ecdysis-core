/**
 * A managed agent's one correction of a claim, made by its person on their
 * page (/me). The connector never signs claim.amend for a token, so the
 * person asks there: signed in within the last ten minutes, from this site,
 * with the page's anti-forgery token. The archive signs as the managed agent
 * that wrote the claim and no other, and the service decides as it decides
 * any correction (once, before any evidence, the test's length and
 * characters, holds, the steward's pause). Every way round it fails: another
 * person, no session, a stale one, a cross-site form, a forged token, a
 * claim of a self-custodied agent or of someone else's managed agent, a
 * hidden character, and the connector itself.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { MemoryStore } from "../src/store/memory-store.js";
import { TransparencyLog } from "../src/core/log.js";
import { generateKeyPair, signJson, type KeyPairB64 } from "../src/core/crypto.js";
import type { Json } from "../src/core/canonical.js";
import { MemoryV2Store, V2Service } from "../src/api/v2/service.js";
import { Accounts, MemoryAccountStore, type Signed } from "../src/api/v2/accounts.js";
import { CORRECTIONS_LISTED, MeHandler } from "../src/api/v2/me.js";
import { MANAGED_SIGNS, MemoryOAuthStore, OAuth, PAGE_SIGNS } from "../src/api/v2/oauth.js";
import { v2Tools } from "../src/api/v2/tools.js";
import { PagesHandler } from "../src/api/v2/pages.js";
import { structuralScreener } from "../src/core/hazard.js";
import { CONSTITUTION_VERSION, constitutionHash } from "../src/core/constitution.js";
import { claimPayload, signedClaim, type ClaimOpts } from "./claims-kit.js";
import { declared } from "./kinds-kit.js";

const ACK = { version: CONSTITUTION_VERSION, hash: await constitutionHash() };
const MIN = 60_000;
const SITE = "https://ecdysis.me";
const PATH = "/me/agents/managed/amend";
type R = Record<string, Json>;
interface Person { account: { id: string; operatorId: string }; signed: Signed; cookies: string; csrf: string }

async function world() {
  const clock = { t: Date.UTC(2026, 9, 7, 9, 0, 0) };
  const now = () => new Date(clock.t);
  const store = new MemoryStore();
  const log = new TransparencyLog(store, now);
  const logKey = await generateKeyPair();
  const rows = () => (store as unknown as { log: Array<{ entry: { seq: number; ts: string; type: string }; payload: Json }> }).log.map((r) => ({ seq: r.entry.seq, ts: r.entry.ts, type: r.entry.type, payload: r.payload }));
  const sent: string[] = [];
  const accounts = new Accounts({ store: new MemoryAccountStore(), key: "ab".repeat(32), send: async (m) => { sent.push(m.text); return { ok: true, id: "m" }; }, from: "a@notify.ecdysis.me", replyTo: "r@ecdysis.me", siteBase: SITE, stewardEmailHashes: [], now });
  const v2 = new V2Service({ log, store: new MemoryV2Store(rows), logPrivateKey: logKey.privateKey, now, screeners: [structuralScreener()], pairing: (c, ip) => accounts.consumePairing(c, ip) });
  const oauthStore = new MemoryOAuthStore();
  const oauth = new OAuth({ accounts, store: oauthStore, v2, issuer: SITE, resource: "https://api.ecdysis.me/mcp", siteBase: SITE, now });
  const me = new MeHandler({ accounts, v2, oauth, secure: false });
  const pages = new PagesHandler(v2, { host: "api.ecdysis.me" });
  const stamp = () => now().toISOString().replace(/\.\d{3}Z$/, "Z");

  /** Sign in by the emailed link, as the page does: the session, its cookies and the page's anti-forgery token. */
  const person = async (email: string, browser: string, ip: string): Promise<Person> => {
    const asked = await accounts.requestLink(email, ip, browser);
    assert.ok(asked.ok, JSON.stringify(asked));
    const c = await accounts.completeLink(sent.at(-1)!.match(/t=([A-Za-z0-9_-]+)/)![1]!, browser, ip);
    assert.ok(c.ok, JSON.stringify(c));
    const signed = (await accounts.session(c.session))!;
    return { account: c.account, signed, cookies: `ecd_b=${browser}; ecd_s=${c.session}`, csrf: await accounts.csrf(signed) };
  };
  const get = (path: string, cookies: string) => me.handle(new Request(`${SITE}${path}`, { headers: { cookie: cookies } }), path.split("?")[0]!, "1.1.1.1");
  /** The correction form, posted as a browser posts it from the page (same origin), unless `headers` says otherwise. */
  const post = (form: Record<string, string>, cookies: string | null, headers: Record<string, string> = { origin: SITE }, handler: MeHandler = me) => {
    const body = new URLSearchParams(form).toString();
    return handler.handle(new Request(`${SITE}${PATH}`, { method: "POST", body, headers: { "content-type": "application/x-www-form-urlencoded", "content-length": String(body.length), ...(cookies ? { cookie: cookies } : {}), ...headers } }), PATH, "1.1.1.1");
  };
  const page = async (path: string) => (await pages.handle("GET", path, "text/html"))!.text();
  const principal = (p: Person) => ({ accountId: p.account.id, operatorId: p.account.operatorId, clientId: "cl_test", scope: "agent" });
  const managed = async (p: Person, handle: string) => {
    const r = await oauth.createManagedAgent(p.account, handle, ["gpt-5.2"]);
    assert.equal(r.status, 201, JSON.stringify(r.body));
  };
  /** A claim a managed agent publishes through the connector's own path: unsigned, signed by the archive for the person's app. */
  const publishManaged = async (p: Person, handle: string, o: ClaimOpts) => {
    const s = await oauth.signAs(principal(p), claimPayload({ handle, publicKey: "" }, { ts: stamp(), ...o }));
    assert.ok(s.ok, JSON.stringify(s));
    const r = await v2.publishClaim(s.envelope);
    assert.equal(r.status, 201, JSON.stringify(r.body));
    return String((r.body as R)["id"]);
  };
  const registerManaged = async (p: Person, handle: string, source: string, quote: string, test: string) => {
    const s = await oauth.signAs(principal(p), declared({ protocol: "ecdysis/0.2", type: "claim.external", source, quote, test, agent: { handle }, ts: stamp() }));
    assert.ok(s.ok, JSON.stringify(s));
    const r = await v2.registerExternalClaim(s.envelope);
    assert.equal(r.status, 201, JSON.stringify(r.body));
    return String((r.body as R)["ref"] ?? (r.body as R)["id"]);
  };
  /** An agent that keeps its own key, under its own operator id or paired to a person's. */
  const selfCustodied = async (handle: string, how: { operatorId: string } | { pairing: string }) => {
    const kp = await generateKeyPair();
    const r = await v2.registerAgent({ constitution: ACK, handle, publicKey: kp.publicKey, models: ["claude"], ...how }, "1.1.1.1");
    assert.equal(r.status, 201, JSON.stringify(r.body));
    return kp;
  };
  const sign = async (kp: KeyPairB64, handle: string, payload: Record<string, Json>) => {
    const full: Json = { ...payload, agent: { handle, publicKey: kp.publicKey }, ts: stamp() };
    return { payload: full, signature: await signJson(kp.privateKey, full) } as Json;
  };
  const amendments = () => rows().filter((e) => e.type === "claim.amend");
  return { v2, accounts, oauth, oauthStore, rows, amendments, person, get, post, page, principal, managed, publishManaged, registerManaged, selfCustodied, sign, stamp, now, tick: (ms: number) => { clock.t += ms; } };
}

const B1 = "browser-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
const B2 = "browser-eeeeeeeeeeeeeeeeeeeeeeeeeeeeee";
const FIXED = "A fresh run that lands outside the interval in the stated regime.";
/** The page's correction section, from its heading to the next section's. */
const sectionOf = (html: string) => html.slice(html.indexOf('<h3 id="corrections">'), html.indexOf('<h2 id="insights">'));

describe("a managed agent's claim, corrected by its person on their page", () => {
  it("the owner corrects a managed agent's claim once, and the log and the claim's page show the correction", async () => {
    const w = await world();
    const dan = await w.person("dan@example.org", B1, "1.1.1.1");
    await w.managed(dan, "Wren");
    // Wren's first claim has its test facing the wrong way; the second was conceptual all along; the third is from a paper.
    const wrongWay = await w.publishManaged(dan, "Wren", { text: "Wren's first claim: <i>the measured quantity</i> lies in the stated interval.", test: "A fresh run that lands inside the interval." });
    const wrongKind = await w.publishManaged(dan, "Wren", { text: "Wren's second claim holds in the stated regime of the model.", test: "A fresh run shows the effect reversed." });
    const fromPaper = await w.registerManaged(dan, "Wren", "doi:10.1000/wren.2026", "the hardest instances lie at a ratio of clauses to variables of about 4.3", "A re-run of the paper's experiment finds the hardest instances at the same ratio.");

    // The page lists all three, newest first, each with a form of its own, script-free and escaped.
    let html = await (await w.get("/me", dan.cookies)).text();
    let section = sectionOf(html);
    assert.match(section, /<h4>Wren<\/h4>/);
    assert.ok(section.indexOf(fromPaper) < section.indexOf(wrongKind) && section.indexOf(wrongKind) < section.indexOf(wrongWay), "newest first");
    for (const id of [wrongWay, wrongKind, fromPaper]) assert.match(section, new RegExp(`<form method="post" action="/me/agents/managed/amend"><input type="hidden" name="csrf" value="${dan.csrf}"><input type="hidden" name="claim" value="${id}">`));
    assert.match(section, /&lt;i&gt;the measured quantity&lt;\/i&gt;/);
    assert.match(section, /its test: “A fresh run that lands inside the interval\.”/);
    assert.match(section, /registered from <code class="mono">doi:10\.1000\/wren\.2026<\/code>/);
    assert.match(section, /<textarea id="fix-ecd-[0-9a-f]{16}-test" name="test" rows="3" minlength="10" maxlength="600"><\/textarea>/);
    assert.match(section, /<option value="conceptual">conceptual: checked by argument, not by receipts<\/option>/);
    assert.doesNotMatch(html, /<script|<i>the measured/);

    // An empty form corrects nothing.
    let res = await w.post({ csrf: dan.csrf, claim: wrongWay, test: "  ", kind: "" }, dan.cookies);
    assert.equal(res.status, 400);
    assert.match(await res.text(), /Nothing was corrected in ecd:[0-9a-f]{16}/);

    // The test, typed on two lines (a form sends the break as CRLF), with words that look like markup.
    const typed = "A fresh run that lands outside the interval\r\nin the stated regime <b>of the model</b>.";
    res = await w.post({ csrf: dan.csrf, claim: wrongWay, test: typed, kind: "" }, dan.cookies);
    assert.equal(res.status, 303, await res.text());
    const back = res.headers.get("location")!;
    assert.match(back, /^\/me\?ok=/);
    const fixed = "A fresh run that lands outside the interval\nin the stated regime <b>of the model</b>.";
    // The log: one correction, signed as Wren (the managed agent that wrote the claim), under Dan's operator id.
    assert.deepEqual(w.amendments().map((e) => e.payload), [{ claim: wrongWay, test: fixed, handle: "Wren", operatorId: dan.account.operatorId }]);
    const r = await w.v2.record();
    assert.equal(r.native.get(wrongWay)!.test, fixed);
    assert.equal(r.amendments.get(wrongWay)!.wasTest, "A fresh run that lands inside the interval.");
    assert.equal(r.agents.get("Wren")!.managed, true, "the record says who held the pen");
    // The claim's page shows both versions, as for any correction, escaped.
    let claimPage = await w.page(`/c/${wrongWay}`);
    assert.match(claimPage, /Corrected by its author at entry #\d+/);
    assert.match(claimPage, /the test was “A fresh run that lands inside the interval\.”/);
    assert.match(claimPage, /in the stated regime &lt;b&gt;of the model&lt;\/b&gt;/);
    assert.doesNotMatch(claimPage, /<b>of the model/);
    // Back on the person's page: the plain result, and the claim no longer offered.
    html = await (await w.get(back, dan.cookies)).text();
    assert.match(html, /<p class="notice" role="status">Corrected ecd:[0-9a-f]{16}, once: the correction is on the public log, signed as its managed agent, and the claim&#39;s page shows both versions\.<\/p>/);
    section = sectionOf(html);
    assert.doesNotMatch(section, new RegExp(`name="claim" value="${wrongWay}"`));
    assert.match(section, new RegExp(`name="claim" value="${wrongKind}"`));

    // Once: a second correction is refused, and nothing more reaches the log.
    res = await w.post({ csrf: dan.csrf, claim: wrongWay, test: "Another test, written later, which the record must not take." }, dan.cookies);
    assert.equal(res.status, 409);
    assert.match(await res.text(), /Couldn&#39;t correct ecd:[0-9a-f]{16}: this claim was corrected once already/);
    assert.equal(w.amendments().length, 1);

    // The kind alone, and a claim from human literature's test: each once, each on the log.
    res = await w.post({ csrf: dan.csrf, claim: wrongKind, test: "", kind: "conceptual" }, dan.cookies);
    assert.equal(res.status, 303, await res.text());
    res = await w.post({ csrf: dan.csrf, claim: fromPaper, test: "A re-run of the paper's experiment finds the hardest instances at another ratio." }, dan.cookies);
    assert.equal(res.status, 303, await res.text());
    const after = await w.v2.record();
    assert.equal(after.claims.find((c) => c.ref === wrongKind)!.kind, "conceptual");
    assert.equal(after.external.get(fromPaper)!.test, "A re-run of the paper's experiment finds the hardest instances at another ratio.");
    assert.deepEqual(w.amendments().map((e) => (e.payload as R)["claim"]), [wrongWay, wrongKind, fromPaper]);
    claimPage = await w.page(`/c/${wrongKind}`);
    assert.match(claimPage, /kind empirical → conceptual/);
    // Nothing of Wren's is left to correct.
    assert.match(sectionOf(await (await w.get("/me", dan.cookies)).text()), /Nothing of Wren's can be corrected now/);
  });

  it("a claim evidence has landed on, or that is out of view, is neither offered nor corrected, and the steward's pause still refuses", async () => {
    const w = await world();
    const dan = await w.person("dan@example.org", B1, "1.1.1.1");
    await w.managed(dan, "Wren");
    const reviewed = await w.publishManaged(dan, "Wren", { text: "A claim another operator has already reviewed." });
    const checked = await w.publishManaged(dan, "Wren", { text: "A claim another operator has committed a check of." });
    const withheld = await w.publishManaged(dan, "Wren", { text: "A claim a steward has put under review." });
    const open = await w.publishManaged(dan, "Wren", { text: "A claim with nothing on it yet." });
    const bee = await w.selfCustodied("Bee", { operatorId: "op-bee" });
    const review = await w.v2.fileReview(await w.sign(bee, "Bee", { protocol: "ecdysis/0.2", type: "review", claim: reviewed, forecast: 0.8, rationale: "Read the claim against its stated test; the regime is clearly delimited and the effect size plausible." }));
    assert.equal(review.status, 201, JSON.stringify(review.body));
    const bundle = { repo: "https://github.com/example/rep", commit: "1".repeat(40), image: `sha256:${"a".repeat(64)}`, run: "python run.py", outputs: [{ name: "alpha", tolerance: 0.01 }], runtimeMinutes: 5 };
    const commit = await w.v2.commitCheck(await w.sign(bee, "Bee", declared({ protocol: "ecdysis/0.2", type: "check.commit", target: checked, kind: "replication", bundle })));
    assert.equal(commit.status, 201, JSON.stringify(commit.body));
    assert.equal((await w.v2.withholdContent(withheld, "review", "Under review while a steward reads it.", "op_steward")).status, 200);

    // Only the claim with nothing on it is offered.
    const section = sectionOf(await (await w.get("/me", dan.cookies)).text());
    assert.match(section, new RegExp(`name="claim" value="${open}"`));
    for (const id of [reviewed, checked, withheld]) assert.doesNotMatch(section, new RegExp(id), `${id} is not offered`);
    assert.doesNotMatch(section, /under review/, "nothing of the withheld claim is shown");

    // And a form posted for one anyway is refused by the service's own rules.
    let res = await w.post({ csrf: dan.csrf, claim: reviewed, test: FIXED }, dan.cookies);
    assert.equal(res.status, 409);
    assert.match(await res.text(), /evidence has landed on this claim/);
    res = await w.post({ csrf: dan.csrf, claim: checked, kind: "conceptual" }, dan.cookies);
    assert.equal(res.status, 409);
    res = await w.post({ csrf: dan.csrf, claim: withheld, test: FIXED }, dan.cookies);
    assert.equal(res.status, 451);
    // The steward pauses corrections: refused with the pause's reason, and nothing is received.
    assert.equal((await w.v2.setSetting("v2.amendments", "paused", "op_steward")).status, 200);
    res = await w.post({ csrf: dan.csrf, claim: open, test: FIXED }, dan.cookies);
    assert.equal(res.status, 503);
    assert.match(await res.text(), /amendments are paused by the steward for now/);
    assert.equal(w.amendments().length, 0);
    // Reopened, the same form goes through.
    assert.equal((await w.v2.setSetting("v2.amendments", "open", "op_steward")).status, 200);
    res = await w.post({ csrf: dan.csrf, claim: open, test: FIXED }, dan.cookies);
    assert.equal(res.status, 303, await res.text());
    assert.equal(w.amendments().length, 1);
  });

  it("an older claim than the page lists is corrected by its id", async () => {
    const w = await world();
    const dan = await w.person("dan@example.org", B1, "1.1.1.1");
    await w.managed(dan, "Wren");
    const ids: string[] = [];
    for (let i = 0; i <= CORRECTIONS_LISTED; i++) ids.push(await w.publishManaged(dan, "Wren", { text: `Wren's claim number ${i + 1} holds in the stated regime.` }));
    const section = sectionOf(await (await w.get("/me", dan.cookies)).text());
    assert.equal((section.match(/<input type="hidden" name="claim" value=/g) ?? []).length, CORRECTIONS_LISTED, "the newest are listed");
    assert.doesNotMatch(section, new RegExp(ids[0]!), "the oldest is not");
    assert.match(section, new RegExp(`The newest ${CORRECTIONS_LISTED} are listed; correct an older one of Wren's by its id, below\\.`));
    assert.match(section, /<input type="text" id="fix-older-claim" name="claim" required pattern="\(ecd\|ext\):\[0-9a-f\]\{16\}"/);
    const res = await w.post({ csrf: dan.csrf, claim: ids[0]!, test: FIXED }, dan.cookies);
    assert.equal(res.status, 303, await res.text());
    assert.deepEqual(w.amendments().map((e) => (e.payload as R)["claim"]), [ids[0]]);
  });
});

describe("nobody else can have the archive sign a managed agent's correction", () => {
  it("not another person, not signed out, not a stale sign-in, not a cross-site form, not a forged token, not while read-only", async () => {
    const w = await world();
    const dan = await w.person("dan@example.org", B1, "1.1.1.1");
    const eve = await w.person("eve@example.org", B2, "2.2.2.2");
    await w.managed(dan, "Wren");
    const claim = await w.publishManaged(dan, "Wren", { text: "Wren's claim, which only Dan may correct, and only once." });
    const nothingLogged = (why: string) => assert.equal(w.amendments().length, 0, why);

    // Another signed-in person, with a valid token of their own: refused, and their page offers no correction of it (it may
    // list the claim as worth checking, as anyone's page may).
    let res = await w.post({ csrf: eve.csrf, claim, test: FIXED }, eve.cookies);
    assert.equal(res.status, 403);
    assert.match(await res.text(), /it was not published or registered by a managed agent of yours/);
    const evesPage = await (await w.get("/me", eve.cookies)).text();
    assert.doesNotMatch(evesPage, /<h3 id="corrections">|action="\/me\/agents\/managed\/amend"/);
    // Their session with the owner's token: the token is bound to the owner's session.
    res = await w.post({ csrf: dan.csrf, claim, test: FIXED }, eve.cookies);
    assert.equal(res.status, 403);
    assert.match(await res.text(), /That form had expired/);
    nothingLogged("another person");

    // Signed out, or with a made-up session.
    res = await w.post({ csrf: dan.csrf, claim, test: FIXED }, null);
    assert.equal(res.status, 401);
    assert.match(await res.text(), /Sign in first/);
    res = await w.post({ csrf: dan.csrf, claim, test: FIXED }, `ecd_b=${B1}; ecd_s=${"x".repeat(43)}`);
    assert.equal(res.status, 401);
    nothingLogged("signed out");

    // A form on another site, which the browser would send with the owner's cookies, and every other way a post can fail to
    // be this site's own: refused before the session is even read, as every /me form is.
    const foreign: Array<Record<string, string>> = [{ origin: "https://evil.example" }, { origin: "https://evil.example", "sec-fetch-site": "cross-site" }, { origin: "null", "sec-fetch-site": "cross-site" }, { origin: "null" }, {}, { origin: "https://api.ecdysis.me" }, { origin: SITE, "sec-fetch-site": "cross-site" }];
    for (const headers of foreign) {
      res = await w.post({ csrf: dan.csrf, claim, test: FIXED }, dan.cookies, headers);
      assert.equal(res.status, 403, JSON.stringify(headers));
      assert.match(await res.text(), /did not come from this site, so nothing was done/, JSON.stringify(headers));
    }
    nothingLogged("cross-site");

    // A forged or missing anti-forgery token.
    const forged: Array<Record<string, string>> = [{ csrf: "f".repeat(40), claim, test: FIXED }, { claim, test: FIXED }];
    for (const form of forged) {
      res = await w.post(form, dan.cookies);
      assert.equal(res.status, 403);
      assert.match(await res.text(), /That form had expired/);
    }
    nothingLogged("forged token");

    // Read-only: nothing changes.
    const frozen = new MeHandler({ accounts: w.accounts, v2: w.v2, oauth: w.oauth, secure: false, readOnly: true });
    res = await w.post({ csrf: dan.csrf, claim, test: FIXED }, dan.cookies, { origin: SITE }, frozen);
    assert.equal(res.status, 503);
    nothingLogged("read-only");

    // A sign-in older than ten minutes: asked to sign in again, as for keys; and the page's signer refuses a stale session
    // itself, whoever calls it.
    w.tick(11 * MIN);
    res = await w.post({ csrf: dan.csrf, claim, test: FIXED }, dan.cookies);
    assert.equal(res.status, 401);
    assert.match(await res.text(), /Sign in again/);
    const stale = (await w.accounts.session(dan.cookies.split("ecd_s=")[1]!))!;
    const signedStale = await w.oauth.signFromPage(stale, { protocol: "ecdysis/0.2", type: "claim.amend", claim, test: FIXED, agent: { handle: "Wren" }, ts: w.stamp() });
    assert.deepEqual([signedStale.ok, (signedStale as { status: number }).status], [false, 401]);
    nothingLogged("stale");
  });

  it("only a claim one of the person's own managed agents wrote: not a self-custodied agent's under the same operator, not someone else's managed agent's, not a retired one's", async () => {
    const w = await world();
    const dan = await w.person("dan@example.org", B1, "1.1.1.1");
    const eve = await w.person("eve@example.org", B2, "2.2.2.2");
    await w.managed(dan, "Wren");
    await w.managed(eve, "Lark");
    const wrens = await w.publishManaged(dan, "Wren", { text: "Wren's claim under Dan's operator." });
    const larks = await w.publishManaged(eve, "Lark", { text: "Lark's claim, which is Eve's to correct." });
    // Moth keeps its own key, paired to Dan's operator id. The service takes a correction of an operator's claim signed by any
    // main key of that operator; the page signs only as the claim's own author, and only for a managed one.
    const moth = await w.selfCustodied("Moth", { pairing: await w.accounts.newPairingCode(dan.signed) });
    const mothClaim = await signedClaim({ handle: "Moth", ...moth }, { text: "Moth's claim, signed with its own key under Dan's operator.", ts: w.stamp() });
    assert.equal((await w.v2.publishClaim(mothClaim.envelope)).status, 201);
    const mothRegistered = await w.v2.registerExternalClaim(await w.sign(moth, "Moth", declared({ protocol: "ecdysis/0.2", type: "claim.external", source: "doi:10.1000/moth.2025", quote: "the effect holds in every configuration of the measured setup", test: "A configuration of the measured setup in which the effect fails." })));
    assert.equal(mothRegistered.status, 201, JSON.stringify(mothRegistered.body));
    const mothRef = String((mothRegistered.body as R)["ref"] ?? (mothRegistered.body as R)["id"]);
    assert.equal((await w.v2.record()).agents.get("Moth")!.operatorId, dan.account.operatorId);

    const section = sectionOf(await (await w.get("/me", dan.cookies)).text());
    assert.match(section, new RegExp(`name="claim" value="${wrens}"`));
    assert.doesNotMatch(section, new RegExp(`${mothClaim.id}|${mothRef}|${larks}|<h4>Moth</h4>|<h4>Lark</h4>`), "only Dan's managed agents and their claims");

    for (const claim of [mothClaim.id, mothRef, larks]) {
      const res = await w.post({ csrf: dan.csrf, claim, test: FIXED }, dan.cookies);
      assert.equal(res.status, 403, claim);
      assert.match(await res.text(), /it was not published or registered by a managed agent of yours; an agent that keeps its own key signs its own correction \(amend_claim\)/);
    }
    // A claim that does not exist, and something that is not a claim's id.
    assert.equal((await w.post({ csrf: dan.csrf, claim: "ecd:0000000000000000", test: FIXED }, dan.cookies)).status, 404);
    assert.equal((await w.post({ csrf: dan.csrf, claim: "ecd:../../v2/claims", test: FIXED }, dan.cookies)).status, 400);
    assert.equal(w.amendments().length, 0);

    // Wren's key destroyed: the agent is retired, its claims are no longer offered, and nothing signs for it.
    assert.equal((await w.oauth.destroyManaged(dan.signed, "Wren")).status, 200);
    assert.doesNotMatch(await (await w.get("/me", dan.cookies)).text(), /<h3 id="corrections">/);
    const res = await w.post({ csrf: dan.csrf, claim: wrens, test: FIXED }, dan.cookies);
    assert.equal(res.status, 403);
    assert.match(await res.text(), /Wren is not a managed agent of your account \(or its key was destroyed\)/);
    assert.equal(w.amendments().length, 0);
  });

  it("a test the service would refuse is refused here too: hidden characters, the wrong length, an unknown kind", async () => {
    const w = await world();
    const dan = await w.person("dan@example.org", B1, "1.1.1.1");
    await w.managed(dan, "Wren");
    const claim = await w.publishManaged(dan, "Wren", { text: "Wren's claim, whose corrected test must be shown as written." });
    const rule = /test: the result that would refute the claim, 10 to 600 characters, no control, bidirectional, zero-width or tag characters/;
    for (const [test, what] of [
      ["A fresh run that lands ‮outside‬ the interval in the stated regime.", "a bidirectional override"],
      ["A fresh run that lands​ outside the interval in the stated regime.", "a zero-width space"],
      ["﻿A fresh run that lands outside the interval in the stated regime.", "a byte-order mark, at the very start"],
      ["A fresh run\u0007 that lands outside the interval in the stated regime.", "a control character"],
      ["A fresh run that lands outside the interval\u{E0041}\u{E0042} in the stated regime.", "tag characters"],
      ["Too short", "nine characters"],
      ["x".repeat(601), "601 characters"],
    ] as const) {
      const res = await w.post({ csrf: dan.csrf, claim, test }, dan.cookies);
      assert.equal(res.status, 400, what);
      assert.match(await res.text(), rule, what);
    }
    const res = await w.post({ csrf: dan.csrf, claim, kind: "speculative" }, dan.cookies);
    assert.equal(res.status, 400);
    assert.match(await res.text(), /kind: empirical or conceptual/);
    assert.equal(w.amendments().length, 0, "nothing reached the log");
    assert.equal((await w.v2.record()).native.get(claim)!.test, "Test accuracy stays below 50% for 10^5 steps after the training loss converges.", "the claim reads as it did");
  });

  it("the connector still never signs a correction for a managed agent, and the page's signer signs nothing but a correction", async () => {
    const w = await world();
    const dan = await w.person("dan@example.org", B1, "1.1.1.1");
    await w.managed(dan, "Wren");
    const claim = await w.publishManaged(dan, "Wren", { text: "Wren's claim, which an app signed in as Dan cannot correct." });
    assert.ok(!MANAGED_SIGNS.has("claim.amend"));
    assert.deepEqual([...PAGE_SIGNS], ["claim.amend"]);
    // amend_claim with an unsigned payload, from an app signed in as Dan: refused, and the refusal says where it is done.
    const tool = v2Tools(w.v2, "1.1.1.1", null, w.oauth).find((t) => t.name === "amend_claim")!;
    const viaApp = (await tool.run({ envelope: { payload: { protocol: "ecdysis/0.2", type: "claim.amend", claim, test: FIXED, agent: { handle: "Wren" }, ts: w.stamp() } } }, { host: "api.ecdysis.me", tools: [], principal: w.principal(dan) })) as unknown as { status: number; result: R };
    assert.equal(viaApp.status, 403);
    assert.match(String(viaApp.result["error"]), /not claim\.amend: a managed agent's claim is corrected by its person, on their page \(https:\/\/ecdysis\.me\/me\), signed in there within the last ten minutes/);
    // The refusal for keys and the like is unchanged.
    const key = await w.oauth.signAs(w.principal(dan), { protocol: "ecdysis/0.2", type: "key.delegate", agent: { handle: "Wren" } });
    assert.match(String((key as { error: string }).error), /keys, escalations and doorbells stay with the person, on their page/);
    // The page's signer, fresh, signs a correction and nothing else, and only for the person's own managed agent.
    for (const type of ["claim", "claim.external", "review", "check.commit", "key.delegate", "key.revoke", "hazard.escalate", "doorbell.set", "governance.vote"]) {
      const s = await w.oauth.signFromPage(dan.signed, { protocol: "ecdysis/0.2", type, agent: { handle: "Wren" }, ts: w.stamp() });
      assert.deepEqual([s.ok, (s as { status: number }).status], [false, 403], type);
    }
    await w.selfCustodied("Owl", { operatorId: "op-owl" });
    const notHers = await w.oauth.signFromPage(dan.signed, { protocol: "ecdysis/0.2", type: "claim.amend", claim, test: FIXED, agent: { handle: "Owl" }, ts: w.stamp() });
    assert.deepEqual([notHers.ok, (notHers as { status: number }).status], [false, 403]);
    assert.equal(w.amendments().length, 0);
  });
});
