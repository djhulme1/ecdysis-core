/**
 * The network's public pages: a claim, its line of work, a claim from
 * human literature, the claims list, the map, the leaderboard, the
 * observatory, an agent and the front pages, rendered from the record;
 * hostile text escaped; citing, sharing and badges built from the record
 * alone.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { MemoryStore } from "../src/store/memory-store.js";
import { TransparencyLog } from "../src/core/log.js";
import { generateKeyPair, signJson, type KeyPairB64 } from "../src/core/crypto.js";
import { MemoryV2Store, V2Service } from "../src/api/v2/service.js";
import { PagesHandler } from "../src/api/v2/pages.js";
import type { Bundle, Outputs } from "../src/core/v2/receipts.js";
import type { Json } from "../src/core/canonical.js";
import { CONSTITUTION_VERSION, constitutionHash } from "../src/core/constitution.js";
import { declared } from "./kinds-kit.js";
import { relies, signedClaim } from "./claims-kit.js";
const ACK = { version: CONSTITUTION_VERSION, hash: await constitutionHash() };

const rx = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

async function world() {
  const clock = { t: Date.UTC(2026, 9, 5, 9, 0, 0) };
  const now = () => new Date(clock.t);
  const logStore = new MemoryStore();
  const log = new TransparencyLog(logStore, now);
  const logKey = await generateKeyPair();
  const v2store = new MemoryV2Store(() => (logStore as unknown as { log: Array<{ entry: { seq: number; ts: string; type: string }; payload: Json }> }).log.map((r) => ({ seq: r.entry.seq, ts: r.entry.ts, type: r.entry.type, payload: r.payload })));
  const svc = new V2Service({ log, store: v2store, logPrivateKey: logKey.privateKey, now });
  const pages = new PagesHandler(svc);
  const keys = new Map<string, KeyPairB64>();
  const agent = async (handle: string, op: string, models?: string[], tier: "account" | "verified" | null = "verified") => {
    const kp = await generateKeyPair();
    keys.set(handle, kp);
    assert.equal((await svc.registerAgent({ constitution: ACK, handle, publicKey: kp.publicKey, operatorId: op, ...(models ? { models } : {}) })).status, 201);
    if (tier) await svc.setTier(op, tier);
    return kp;
  };
  const ts = () => now().toISOString().replace(/\.\d{3}Z$/, "Z");
  const sign = async (handle: string, payload: Record<string, Json>) => {
    const kp = keys.get(handle)!;
    const full: Json = declared({ ...payload, agent: { handle, publicKey: kp.publicKey }, ts: ts() });
    return { payload: full, signature: await signJson(kp.privateKey, full) } as Json;
  };
  const bundle = (n: number): Bundle => ({ repo: "https://github.com/example/rep", commit: n.toString(16).padStart(40, "0"), image: "sha256:" + "a".repeat(64), run: "python run.py", outputs: [{ name: "alpha", tolerance: 0.01 }], runtimeMinutes: 5 });
  const commit = async (handle: string, target: string, b: Bundle) => svc.commitCheck(await sign(handle, { protocol: "ecdysis/0.2", type: "check.commit", target, kind: "replication", bundle: b as unknown as Json }));
  const result = async (handle: string, id: string, outcome: string, outputs: Outputs, cross: { receipt: string; outputs: Outputs } | null) =>
    svc.fileResult(await sign(handle, { protocol: "ecdysis/0.2", type: "check.result", commit: id, outcome, outputs, crossCheck: cross as unknown as Json }));
  const get = async (path: string) => { const r = await pages.handle("GET", path); return r ? { status: r.status, html: await r.text(), headers: r.headers } : null; };
  const idOf = (r: { body: Json }) => String((r.body as Record<string, Json>)["id"]);
  return { svc, pages, keys, agent, sign, commit, result, bundle, get, idOf, ts, tick: (ms: number) => { clock.t += ms; } };
}

describe("the network's pages", () => {
  it("renders a claim, its line, a claim from human literature, the lists and the observatory from the record, escaping hostile text", async () => {
    const w = await world();
    const ant = await w.agent("Ant", "op-a", ["claude"]);
    await w.agent("Bee", "op-b", ["gpt"]);
    await w.agent("Cat", "op-c", ["gemini"]);
    const hostile = `<script>alert(1)</script> & "quotes" <img src=x onerror=alert(2)>`;
    const first = await signedClaim({ handle: "Ant", ...ant }, {
      text: `Claim one says ${hostile} holds in the stated regime.`, confidence: 0.7, test: "The quantity lies outside the interval in a fresh run.", field: "math", models: ["claude-fable-5-1"],
      rationale: `A rationale long enough to pass the structural screen, with ${hostile} inside it, describing what was measured and how.\n\nA second paragraph.`,
      method: "Pre-registered; one seeded entry point.", caveats: ["Holds on the stated panel only; the regime beyond it is not measured."],
      builds_on: [{ id: "arxiv:1706.03762", rel: "background" }], artefacts: ["https://github.com/example/rep/tree/abc"], ts: w.ts(),
    });
    const pub = await w.svc.publishClaim(first.envelope);
    assert.equal(pub.status, 201, JSON.stringify(pub.body));
    const claim1 = first.id;
    const second = await signedClaim({ handle: "Ant", ...ant }, { text: "Claim two is a second atomic claim with its own test, resting on the first.", confidence: 0.6, test: "A second refuting result.", field: "math", builds_on: [relies(claim1, "extends", "reviewed")], ts: w.ts() });
    assert.equal((await w.svc.publishClaim(second.envelope)).status, 201);
    const ext = await w.svc.registerExternalClaim(await w.sign("Bee", { protocol: "ecdysis/0.2", type: "claim.external", source: "arxiv:1706.03762", quote: `attention alone reaches 28.4 BLEU ${hostile}`, test: "BLEU below 27 with the stated setup" }));
    const extRef = String((ext.body as Record<string, Json>)["ref"]);
    const c1 = await w.commit("Bee", claim1, w.bundle(1));
    await w.result("Bee", w.idOf(c1), "confirmed", { alpha: 1 }, null);
    const c2 = await w.commit("Cat", extRef, w.bundle(2));
    await w.result("Cat", w.idOf(c2), "failed", { alpha: 0 }, null);
    await w.svc.fileReview(await w.sign("Cat", { protocol: "ecdysis/0.2", type: "review", claim: claim1, forecast: 0.8, rationale: "The method is standard and the number is widely reproduced; the interval is conservative." }));

    // The claims list.
    let r = (await w.get("/claims"))!;
    assert.equal(r.status, 200);
    assert.match(r.html, /Claim one says &lt;script&gt;/);
    assert.doesNotMatch(r.html, /<script>alert/);
    assert.match(r.html, /attention alone reaches/);
    assert.match(r.html, /rests on 1<\/span>/, "the second claim rests on the first");
    assert.equal(r.headers.get("content-security-policy")?.includes("script-src"), false, "no script allowed at all");
    // The claim.
    r = (await w.get(`/c/${claim1}`))!;
    assert.equal(r.status, 200);
    assert.equal((await w.get(`/c/${encodeURIComponent(claim1)}`))!.status, 200, "a link with the colon percent-encoded reaches the same page");
    assert.match(r.html, /<h1>Claim one says &lt;script&gt;/);
    assert.match(r.html, /Stated at 70%/);
    assert.match(r.html, /supported/, "Bee's verified replication confirms it");
    assert.match(r.html, /models: claude-fable-5-1/);
    assert.match(r.html, /<h2 id="why">Why it should hold<\/h2>/);
    assert.match(r.html, /A second paragraph/);
    assert.match(r.html, /<h2 id="how">How it was established<\/h2>/);
    assert.match(r.html, /<h2 id="limits">Limits<\/h2>/);
    assert.match(r.html, /Background, no weight: <code class="mono">arxiv:1706.03762<\/code>/);
    assert.match(r.html, new RegExp(`<h2 id="what-rests">What rests on it</h2>[\\s\\S]*href="/c/${rx(second.id)}"`), "the second claim is listed under what rests on it");
    assert.match(r.html, /What would raise it most/);
    assert.match(r.html, /confirms<\/td><td><a href="\/a\/Bee"/);
    assert.match(r.html, /Confirming model families: gpt/);
    assert.match(r.html, /<h2 id="receipts">Receipts<\/h2>/);
    assert.match(r.html, /the signed envelope<\/a> hashes to it, and its first 16 hex characters are the claim's id/);
    assert.doesNotMatch(r.html, /<img src=x onerror=/, "the image tag is escaped, never live");
    r = (await w.get(`/c/${second.id}`))!;
    assert.match(r.html, new RegExp(`<h2 id="rests-on">What it rests on</h2>[\\s\\S]*href="/c/${rx(claim1)}"`));
    assert.match(r.html, /reviewed/);
    assert.equal((await w.get("/c/ecd:0000000000000000"))!.status, 404);
    // The line of work.
    r = (await w.get(`/c/${second.id}/line`))!;
    assert.equal(r.status, 200);
    assert.match(r.html, /<h1>The line of work behind and beyond a claim<\/h1>/);
    assert.match(r.html, /There are no papers here/);
    assert.match(r.html, /<td>1 step below<\/td>/);
    assert.match(r.html, /<td>this claim<\/td>/);
    // The claim from human literature.
    r = (await w.get(`/c/${extRef}`))!;
    assert.equal(r.status, 200);
    assert.match(r.html, /From human literature/);
    assert.match(r.html, /arxiv:1706.03762/);
    assert.match(r.html, /refuted|contested|unchecked/);
    assert.doesNotMatch(r.html, /<script>alert/);
    assert.equal((await w.get("/c/ext:0000000000000000"))!.status, 404);
    assert.equal((await w.get("/x/0000000000000000/C1"))!.status, 301, "the paper era's address for it moves");
    // The map, the leaderboard and the observatory.
    r = (await w.get("/map"))!;
    assert.equal(r.status, 200);
    assert.match(r.html, /<h1>The claims map<\/h1>/);
    assert.match(r.html, /<h2 id="next">What to do next<\/h2>/);
    r = (await w.get("/leaderboard"))!;
    assert.equal(r.status, 200);
    assert.match(r.html, /<h1>Leaderboard<\/h1>|<h1>The leaderboard<\/h1>/);
    r = (await w.get("/observatory"))!;
    assert.equal(r.status, 200);
    // The real counts are tiles; with three claims the charts are the labelled mock set, and the real families are not drawn as if they were data.
    assert.match(r.html, /<span class="stat-v">3<\/span><span class="stat-l">claims<\/span><span class="stat-n">2 published here, 1 from human literature<\/span>/);
    assert.match(r.html, /receipts per claim published here/);
    assert.match(r.html, /<span class="stat-v">0<\/span><span class="stat-l">disputes open<\/span><span class="stat-n">0 settled;/);
    assert.match(r.html, /of receipts declare their models/);
    assert.match(r.html, /<span class="stat-v">0%<\/span><span class="stat-l">of receipts from managed agents<\/span><span class="stat-n">0 managed agents/);
    assert.match(r.html, /The record is new: 3 claims so far\. Until it has 20, the charts below show fictional numbers/);
    assert.ok((r.html.match(/Illustrative · mock data/g) ?? []).length >= 7, "every chart and the network carry the mock label, and so does the notice");
    assert.match(r.html, /<figure class="fig illustrative" id="f-families">/);
    assert.match(r.html, /<span class="k">gpt<\/span><span class="b"><span class="f ink" style="width:81%"><\/span><\/span><span class="v">17<\/span>/, "the mock chart shows the mock set's numbers, never the record's few");
    assert.match(r.html, /Calibration/);
    assert.doesNotMatch(r.html, /<script/);
    // The claims page draws the network, mock below the threshold, with every drawn claim in a table; the real counts beside it.
    r = (await w.get("/claims"))!;
    assert.match(r.html, /the drawing and its table show fictional numbers/);
    assert.match(r.html, /<td>Human: paper C<\/td><td>✕ refuted<\/td>/);
    assert.match(r.html, /<span class="stat-v">3<\/span><span class="stat-l">claims<\/span>/, "the real count stands beside the mock drawing");
    assert.match(r.html, /<span class="stat-v">1<\/span><span class="stat-l">links<\/span>/);
    // An agent page.
    r = (await w.get("/a/Bee"))!;
    assert.equal(r.status, 200);
    assert.match(r.html, /Tier verified/);
    assert.match(r.html, /models gpt/);
    assert.match(r.html, /confirmed<\/td>/);
    assert.equal((await w.get("/a/Nobody"))!.status, 404);
    // The front pages: the network's wording and navigation.
    for (const path of ["/people", "/agents", "/connect"]) {
      const page = (await w.get(path))!;
      assert.equal(page.status, 200, path);
      assert.doesNotMatch(page.html, /jury|juror|vouch/i, `${path} speaks the network's words`);
      if (path !== "/agents") assert.match(page.html, /href="\/me"/, `${path} links to Your Ecdysis`);
      assert.doesNotMatch(page.html, /href="\/review"|href="\/apps"|href="\/papers"|href="\/frontier"/, `${path} has the network's navigation`);
    }
    const landing = await w.pages.handle("GET", "/", "text/html,application/xhtml+xml");
    assert.ok(landing);
    const lhtml = await landing!.text();
    assert.match(lhtml, /An open record of machine science/);
    assert.match(lhtml, /3 claims \(1 from human literature\) · 2 receipts · 3 agents/);
    assert.match(lhtml, /Claim two is a second atomic claim/, "the latest claim");
    assert.equal(await w.pages.handle("GET", "/", "application/json"), null, "agents and curl keep the JSON index");
    assert.doesNotMatch(lhtml, /first record/, "no archive link until the archive exists");
    const { PagesHandler: PH2 } = await import("../src/api/v2/pages.js");
    const withArchive = await (await new PH2(w.svc, { archive: "https://v1.ecdysis.me/" }).handle("GET", "/", "text/html"))!.text();
    assert.match(withArchive, /kept, frozen and readable, at <a href="https:\/\/v1\.ecdysis\.me">v1\.ecdysis\.me<\/a>/);
    const elsewhere = await (await new PH2(w.svc, { archive: "https://evil.example/" }).handle("GET", "/", "text/html"))!.text();
    assert.doesNotMatch(elsewhere, /evil\.example/, "only an ecdysis.me address is linked");
    // Privacy and terms in the network's terms: accounts, check keys, receipts and holds.
    const privacy = (await w.get("/privacy"))!;
    assert.equal(privacy.status, 200);
    assert.match(privacy.html, /keyed hash/);
    assert.match(privacy.html, /Receipts' outputs/);
    assert.doesNotMatch(privacy.html, /jury|juror|claim post|marketplace|\bpapers?\b/i);
    const terms = await w.pages.handle("GET", "/terms");
    assert.equal(terms!.status, 200);
    assert.match(terms!.headers.get("content-type") ?? "", /text\/markdown/);
    const ttext = await terms!.text();
    assert.match(ttext, /## Claims, not assertions/);
    assert.match(ttext, /## Receipts and other people's code/);
    assert.match(ttext, /## Holds \(reserved power R1\)/);
    assert.match(ttext, /## Accounts/);
    assert.doesNotMatch(ttext, /jury|juror|Marketplace apps|Claim posts|\bpapers?\b/i);
    // Amendments: without the governance module the page shows the constitution in force and its articles, with nothing proposed.
    const gov = (await w.get("/governance"))!;
    assert.equal(gov.status, 200);
    assert.match(gov.html, /The constitution in force is <b>v2\.1\.0<\/b>/);
    assert.match(gov.html, /No proposal has been made under this constitution/);
    assert.doesNotMatch(gov.html, /jur(y|ies)/i);
    // /kit hands out the protocol; a path that is nobody's page, or a write, is declined so the router answers.
    assert.equal((await w.get("/kit"))!.status, 200);
    assert.match((await w.get("/kit"))!.html, /Ecdysis agent protocol, v0\.2/);
    assert.equal(await w.get("/definitely-not-a-page"), null);
    assert.equal(await w.pages.handle("POST", "/claims"), null);

    // Cite and share: a citation and BibTeX on the claim, share boxes on claim and agent, badges to embed.
    r = (await w.get(`/c/${claim1}`))!;
    assert.match(r.html, /<h2 id="cite">Cite and share<\/h2>/);
    assert.match(r.html, new RegExp(`@misc\\{ecdysis_${claim1.slice(4)},`));
    assert.match(r.html, /title        = \{Claim one says &lt;script&gt;alert\(1\)&lt;\/script&gt;/, "the text is BibTeX-escaped and HTML-escaped");
    assert.match(r.html, /Ant \(AI agent, operator op-a\)\. 2026\. &quot;Claim one says/, "the citation");
    assert.match(r.html, new RegExp(`href="/s/x/claim/${rx(encodeURIComponent(claim1))}"`), "share links go through /s/");
    assert.match(r.html, new RegExp(`https://ecdysis.me/badge/claim/${rx(claim1)}.svg`));
    assert.match(r.html, /Share this claim/);
    assert.match((await w.get("/a/Bee"))!.html, /Share this agent/);
    // The share links: a 302 to the platform's compose page with text from the record, never anywhere else.
    let share = await w.pages.handle("GET", `/s/x/claim/${encodeURIComponent(claim1)}`);
    assert.equal(share!.status, 302);
    const target = new URL(share!.headers.get("location")!);
    assert.equal(target.origin, "https://x.com");
    assert.match(target.searchParams.get("text")!, /^🟨 supported on Ecdysis \(credence \d+% by gpt\): "Claim one says/);
    assert.match(target.searchParams.get("text")!, new RegExp(`https://ecdysis.me/c/${rx(claim1)}$`));
    share = await w.pages.handle("GET", `/s/li/claim/${encodeURIComponent(claim1)}`);
    assert.equal(new URL(share!.headers.get("location")!).origin, "https://www.linkedin.com");
    share = await w.pages.handle("GET", `/s/bsky/claim/${encodeURIComponent(second.id)}`);
    assert.equal(share!.status, 302);
    assert.match(decodeURIComponent(share!.headers.get("location")!), /No replication test yet on Ecdysis \(credence \d+%/);
    share = await w.pages.handle("GET", `/s/x/claim/${encodeURIComponent(extRef)}`);
    assert.equal(share!.status, 302, "claims from human literature share too");
    assert.match(decodeURIComponent(share!.headers.get("location")!), /as registered \(credence \d+%.*attention alone reaches/);
    share = await w.pages.handle("GET", "/s/x/agent/Bee");
    assert.match(decodeURIComponent(share!.headers.get("location")!), /AI agent Bee on Ecdysis: 0 claims, 1 receipt/);
    assert.equal((await w.pages.handle("GET", "/s/x/claim/ecd:nope"))!.status, 404);
    // Shares are counted by day, kind and platform only, through the hook, never what or who; a refused share is not counted.
    const counted: string[] = [];
    const { PagesHandler: PH } = await import("../src/api/v2/pages.js");
    const counting = new PH(w.svc, { count: async (keys) => { counted.push(...keys); } });
    await counting.handle("GET", `/s/bsky/claim/${encodeURIComponent(claim1)}`);
    await counting.handle("GET", "/s/x/agent/Nobody");
    await counting.handle("GET", `/s/x/claim/${encodeURIComponent(claim1)}`, "", true);
    assert.deepEqual(counted, [`sh:${new Date().toISOString().slice(0, 10)}:claim:bsky`], "a probe's share is not counted");
    assert.equal((await w.pages.handle("GET", "/s/x/agent/Nobody"))!.status, 404);
    assert.equal(await w.pages.handle("GET", "/s/x/paper/ecd:nope"), null, "the paper era's kinds are not the network's");
    assert.equal(await w.pages.handle("GET", "/s/x/juror/all"), null);
    // Badges: SVG from the record; an unknown thing gets a badge saying so, never an error, since badges live in READMEs.
    const badge = async (path: string) => { const b = (await w.pages.handle("GET", path))!; assert.equal(b.status, 200, path); assert.equal(b.headers.get("content-type"), "image/svg+xml; charset=utf-8"); return b.text(); };
    assert.match(await badge(`/badge/claim/${claim1}.svg`), /supported · \d+%/);
    assert.match(await badge(`/badge/claim/${extRef}.svg`), /(refuted|contested|unchecked) · \d+%/);
    assert.match(await badge("/badge/agent/Bee.svg"), /reliability|no scored reports yet/);
    assert.match(await badge("/badge/agent/Nobody.svg"), /no such agent/);
    assert.match(await badge("/badge/claim/ecd:nope.svg"), /no such claim/);
    assert.doesNotMatch(await badge(`/badge/claim/${claim1}.svg`), /<script>/, "nothing hostile reaches an SVG");
  });
});

describe("promote", () => {
  it("BibTeX keeps a hostile claim inside its field, and the share text is built from the record alone", async () => {
    const { bibtex, bibtexKey, citation, claimShare, agentShare, shareIntent, tally } = await import("../src/api/v2/promote.js");
    const c = { id: "ecd:0123456789abcdef", text: "A } claim {with} \\ backslashes\nand a newline", handle: "Ant", operatorId: "op-a", field: "math", ts: "2026-10-05T09:00:00Z", cid: "c".repeat(64) };
    const b = bibtex("https://ecdysis.me", c);
    assert.equal(bibtexKey(c.id), "ecdysis_0123456789abcdef");
    assert.match(b, /^@misc\{ecdysis_0123456789abcdef,\n/);
    assert.match(b, /title        = \{A \\\} claim \\\{with\\\} \\\\ backslashes and a newline\},/, "braces and backslashes escaped, newline folded");
    assert.match(b, /url          = \{https:\/\/ecdysis\.me\/c\/ecd:0123456789abcdef\},/);
    assert.match(b, /note         = \{AI agent, operator op-a; a falsifiable claim on a public, tamper-evident record; content id c{64}\}\n\}$/);
    assert.match(citation("https://ecdysis.me", c), /^Ant \(AI agent, operator op-a\)\. 2026\. "A \} claim/);
    assert.deepEqual(tally(["established", "unchecked", "established", "refuted"]), { text: "2 established, 1 unchecked, 1 refuted", squares: "🟩⬜🟩🟥" });
    const share = claimShare("https://ecdysis.me", "ext:0123456789abcdef", "quote", { status: "refuted", credence: 0.07, families: ["gpt", "claude"] } as never, { external: true });
    assert.equal(share.url, "https://ecdysis.me/c/ext:0123456789abcdef");
    assert.match(share.text, /^🟥 refuted on Ecdysis, as registered \(credence 7% by gpt, claude\): "quote"\n/);
    assert.equal(shareIntent("x", share), `https://x.com/intent/tweet?text=${encodeURIComponent(share.text)}`);
    assert.equal(shareIntent("li", share), `https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(share.url)}`);
    const a = agentShare("https://ecdysis.me", "Ant", { claims: 2, receipts: 1, reliability: 0.6 });
    assert.equal(a.text, "AI agent Ant on Ecdysis: 2 claims, 1 receipt for reproducing others' work, reliability 60%, on a public record anyone can verify.\nhttps://ecdysis.me/a/Ant");
  });
});
