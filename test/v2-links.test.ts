/**
 * literature/0.1, adversarially: identified links between claims from human
 * literature (links.ts; claude/ecdysis-literature-network-design.md). An
 * agent reading the citing paper says which earlier claim it rests on, with
 * the paper's own sentence as evidence; the link is attributable, one per
 * operator, corroborated by others, withdrawn but never edited, and keeps
 * the links a DAG. It moves no credence: it feeds RELIANCE, which enters
 * stakes (stakes/0.2) and so ranks what is worth checking. Every attack on
 * that is shown failing here: a link to a claim published here, unknown or
 * out of view; a self-link and a cycle; a repeat that would count twice; a
 * free identity filing links by the thousand to steer the queues; another
 * operator withdrawing a link; a withdrawn, disowned, voided or withheld
 * link still steering; evidence screening refuses; a check key signing one.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { MemoryStore } from "../src/store/memory-store.js";
import { TransparencyLog } from "../src/core/log.js";
import { generateKeyPair, signJson, type KeyPairB64 } from "../src/core/crypto.js";
import { structuralScreener } from "../src/core/hazard.js";
import { MemoryV2Store, V2Service } from "../src/api/v2/service.js";
import { route, MemoryRateLimiter } from "../src/api/router.js";
import { generations, PagesHandler } from "../src/api/v2/pages.js";
import { LogApi } from "../src/api/v2/log-api.js";
import { MANAGED_SIGNS } from "../src/api/v2/oauth.js";
import { IssueRegistry, MemoryIssueStore, normaliseSubject } from "../src/api/v2/issues.js";
import { deriveV2, type V2Entry } from "../src/core/v2/flow.js";
import { resolveV2 } from "../src/core/v2/resolve.js";
import { closesCycle, linkEdgesOf, relianceOf, RELIANCE_PARAMS, validateLinkV2, validateUnlinkV2, type LinkEdge, type LinkState } from "../src/core/v2/links.js";
import { stakesOf, STAKES_VERSION } from "../src/core/v2/stakes.js";
import { scriptedLog } from "../scripts/v2-replay-audit.js";
import type { Json } from "../src/core/canonical.js";
import { CONSTITUTION_VERSION, constitutionHash } from "../src/core/constitution.js";
import { declared, GENERAL, REPORTED } from "./kinds-kit.js";
import { signedClaim } from "./claims-kit.js";

const ACK = { version: CONSTITUTION_VERSION, hash: await constitutionHash() };
const body = (r: { body: Json }) => r.body as Record<string, Json>;
/** A claim from human literature's id, from one hex digit: ext:aaaaaaaaaaaaaaaa. */
const X = (c: string) => `ext:${c.repeat(16)}`;
const A = X("a"), B = X("b"), C = X("c"), D = X("d"), T = X("e");
const edge = (from: string, to: string, o: { rel?: LinkEdge["rel"]; weight?: number; verified?: boolean } = {}): LinkEdge => ({
  from, to, rel: o.rel ?? "extends", basis: "identified", by: [], weight: o.weight ?? 1, verified: o.verified ?? (o.weight ?? 1) === 1, seq: 0,
});
const QUOTE = "We build directly on the threshold the earlier study measured, and take its value as given throughout.";

describe("literature/0.1: the core", () => {
  it("takes a well-formed link, and refuses by name everything else: a mention, another basis, a self-link, evidence that is not a sentence", () => {
    const good = { protocol: "ecdysis/0.2", type: "claim.link", from: B, to: A, rel: "extends", basis: "identified", evidence: { quote: QUOTE, where: "Section 2" }, models: ["gemma-4-31b-qat", "gpt-oss-120b"], agent: { handle: "Exuvia", publicKey: "MCowBQYDK2VwAyEA" + "x".repeat(43) }, ts: "2026-10-06T09:00:00Z" };
    assert.equal(validateLinkV2(good).ok, true);
    assert.equal(validateLinkV2({ ...good, evidence: { quote: QUOTE } }).ok, true, "where is optional");
    const refused = (over: Record<string, unknown>, pattern: RegExp) => {
      const r = validateLinkV2({ ...good, ...over });
      assert.equal(r.ok, false, JSON.stringify(over));
      assert.match((r as { errors: string[] }).errors.join("; "), pattern);
    };
    refused({ rel: "background" }, /rel: extends, method, replicates, refutes .*a mention is not a link/);
    refused({ basis: "reviewed" }, /basis: "identified"/);
    refused({ basis: undefined }, /basis: "identified"/);
    refused({ to: B }, /to: a claim cannot rest on itself/);
    refused({ from: "arxiv:1706.03762" }, /from: the claim that rests on the other/);
    refused({ to: "ext:0123" }, /to: the claim it rests on/);
    refused({ evidence: { quote: "too short" } }, /evidence\.quote: 20 to 600 characters/);
    refused({ evidence: { quote: "x".repeat(601) } }, /evidence\.quote: 20 to 600 characters/);
    refused({ evidence: { quote: `We build directly on the​ threshold the earlier study measured.` } }, /evidence\.quote: no control, zero-width or bidirectional characters/);
    refused({ evidence: { quote: `We build directly on the‮ threshold the earlier study measured.` } }, /no control, zero-width or bidirectional/);
    refused({ evidence: { quote: QUOTE, page: 3 } }, /evidence\.page: not a field of the evidence/);
    refused({ evidence: "We build on it." }, /evidence: \{quote/);
    refused({ weight: 5 }, /weight: not a field of a link/);
    refused({ ts: "yesterday" }, /ts: ISO-8601 UTC/);
    refused({ agent: { handle: "Exuvia" } }, /agent: \{handle, publicKey\}/);
    const unlink = { protocol: "ecdysis/0.2", type: "claim.unlink", link: "lnk:0123456789abcdef", reason: "The citing sentence was about another paper.", agent: good.agent, ts: good.ts };
    assert.equal(validateUnlinkV2(unlink).ok, true);
    assert.equal(validateUnlinkV2({ ...unlink, link: "lnk:0123" }).ok, false);
    assert.equal(validateUnlinkV2({ ...unlink, reason: "wrong" }).ok, false, "a reason of ten characters at least goes on the log");
  });

  it("counts reliance through every path, halved for each step away, and only through dependencies", () => {
    const chain = relianceOf([edge(B, A), edge(C, B)]);
    assert.equal(chain.get(B), 1, "C rests on B");
    assert.equal(chain.get(A), 1.5, "B rests on A, and C half a step further");
    assert.equal(chain.has(C), false, "nothing rests on C");
    const diamond = relianceOf([edge(B, A), edge(C, A), edge(D, B), edge(D, C)]);
    assert.equal(diamond.get(A), 3, "B and C count 1 each; D reaches A by two paths and counts ½ on each");
    const relations = relianceOf([edge(B, A), edge(B, A, { rel: "method" }), edge(C, A, { rel: "replicates" }), edge(D, A, { rel: "refutes" })]);
    assert.equal(relations.get(A), 1, "two relations between one pair count once; replicates and refutes are evidence, not reliance");
    assert.equal(relianceOf([edge(A, A)]).size, 0, "a self-link (never on the log) counts for nothing");
    const cycle = relianceOf([edge(A, B), edge(B, A)]);
    assert.equal(cycle.get(A), 1.875, "a cycle (which the service refuses) neither loops nor blows up: each walk round it counts for at most four steps");
    assert.equal(cycle.get(B), 1.875);
    const ten = Array.from({ length: 10 }, (_, i) => edge(`ext:${(i + 1).toString(16).padStart(16, "0")}`, `ext:${i.toString(16).padStart(16, "0")}`));
    assert.equal(relianceOf(ten).get(`ext:${"0".repeat(16)}`), 1 + 1 / 2 + 1 / 4 + 1 / 8, "a chain counts four steps: a fifth would add at most a sixteenth a path");
    assert.equal(RELIANCE_PARAMS.depth, 4);
    assert.equal(STAKES_VERSION, "stakes/0.2");
    assert.equal(stakesOf(2, 1023, 3), 2 + 10 + 2, "S = U + log2(1 + R) + log2(1 + N)");
    assert.equal(stakesOf(2, 1023), 12, "and with no reliance, stakes/0.1's number exactly");
  });

  it("weighs each dependency by who identified it, and lets what no verified operator identified add at most three", () => {
    const from = (i: number) => `ext:${i.toString(16).padStart(16, "0")}`;
    const accounts = Array.from({ length: 10 }, (_, i) => edge(from(i), T, { weight: 0.5, verified: false }));
    assert.equal(relianceOf(accounts.slice(0, 2)).get(T), 1, "an account's dependency weighs ½");
    assert.equal(relianceOf(accounts).get(T), RELIANCE_PARAMS.otherCap, "ten of them would be 5: what no verified operator identified adds at most 3");
    assert.equal(relianceOf([...accounts, edge(B, T), edge(C, T)]).get(T), 2 + RELIANCE_PARAMS.otherCap, "verified dependencies count in full, beside the capped rest");
    assert.equal(relianceOf([edge(B, T, { weight: 0.5, verified: false }), edge(B, T)]).get(T), 1, "corroborated by a verified operator: the pair weighs 1, once");
  });

  it("bounds what a dense tangle of links can make of a claim, finitely, however many paths it has", () => {
    // Twenty layers four wide, each claim resting on all four below it: 1,048,576 paths from the top to the root.
    const layer = (k: number, i: number) => `ext:${(k * 16 + i).toString(16).padStart(16, "0")}`;
    const dense: LinkEdge[] = [];
    for (let k = 1; k < 20; k++) for (let i = 0; i < 4; i++) for (let j = 0; j < 4; j++) dense.push(edge(layer(k, i), layer(k - 1, j)));
    const n = relianceOf(dense);
    const root = n.get(layer(0, 0))!;
    assert.equal(root, 4 + 16 / 2 + 64 / 4 + 256 / 8, "four steps of paths at most: 4 + 8 + 16 + 32");
    assert.ok([...n.values()].every((x) => Number.isFinite(x) && x <= 60));
    assert.ok(stakesOf(0, 0, root) < Math.log2(1 + 1_000_000), "less than a million citations would add");
  });

  it("the queue attack fails: a free identity filing a thousand links moves a claim's stakes by at most two, and a verified line outranks it", () => {
    const from = (i: number) => `ext:${i.toString(16).padStart(16, "0")}`;
    const attack = Array.from({ length: 1000 }, (_, i) => edge(from(i), T, { weight: 0.25, verified: false }));
    const n = relianceOf(attack).get(T)!;
    assert.equal(n, RELIANCE_PARAMS.otherCap, "a thousand links at ¼ would be 250");
    assert.equal(stakesOf(0, 0, n), 2, "two units of stakes, however many links");
    const line = Array.from({ length: 10 }, (_, i) => edge(from(5000 + i), A));
    assert.ok(stakesOf(0, 0, relianceOf(line).get(A)!) > stakesOf(0, 0, n) + 1, "ten dependencies a verified operator identified outrank the thousand");
  });

  it("finds a cycle before it closes, without recursion however long the chain", () => {
    const g = new Map<string, string[]>([[B, [A]], [C, [B]]]);
    const next = (x: string) => g.get(x) ?? [];
    assert.equal(closesCycle(next, A, C), true, "A cannot rest on C, which rests on A through B");
    assert.equal(closesCycle(next, C, A), false, "C may rest on A directly as well");
    assert.equal(closesCycle(next, A, A), true);
    const chain = new Map<string, string[]>(Array.from({ length: 100_000 }, (_, i) => [`n${i + 1}`, [`n${i}`]] as [string, string[]]));
    assert.equal(closesCycle((x) => chain.get(x) ?? [], "n0", "n100000"), true);
  });

  it("counts only the links in force and in view: withdrawn, disowned, by a voided operator, withheld, or touching a claim out of view, none counts", () => {
    const state = (id: string, from: string, to: string, over: Partial<LinkState> = {}): LinkState => ({ id, from, to, rel: "extends", quote: QUOTE, where: null, handle: "Ant", operatorId: "op-v", families: [], seq: Number.parseInt(id.slice(-2), 16), ts: "2026-10-05T18:00:00Z", key: "k", tier: "verified", disowned: false, withdrawn: null, ...over });
    const links = [
      state("lnk:00000000000000a1", B, A),
      state("lnk:00000000000000a2", C, A, { withdrawn: { seq: 9, ts: "2026-10-05T18:09:00Z", reason: "a misreading", handle: "Ant" } }),
      state("lnk:00000000000000a3", D, A, { disowned: true }),
      state("lnk:00000000000000a4", T, A, { operatorId: "op-void" }),
      state("lnk:00000000000000a5", C, B, { tier: "account" }),
      state("lnk:00000000000000a6", D, B, { id: "lnk:00000000000000a6" }),
      state("lnk:00000000000000a7", T, B),
    ];
    const held = new Set(["lnk:00000000000000a6", T]);
    const edges = linkEdgesOf(links, { held: (s) => held.has(s), voided: (op) => op === "op-void" });
    assert.deepEqual(edges.map((e) => `${e.from.slice(4, 5)}>${e.to.slice(4, 5)}:${e.weight}`), ["b>a:1", "c>b:0.5"], "only the first and the account's link count");
    assert.equal(edges[1]!.verified, false);
    assert.deepEqual(edges[0]!.by.map((b) => b.id), ["lnk:00000000000000a1"]);
  });
});

/* -------------------------------------------------------------------------- */
/* The fold: what the log may hold, and what it does                           */

function log() {
  const out: V2Entry[] = [];
  let seq = 0;
  const t0 = Date.UTC(2026, 9, 5, 18, 0, 0);
  const push = (type: V2Entry["type"], payload: Record<string, unknown>) => { out.push({ seq, ts: new Date(t0 + seq * 60_000).toISOString(), type, payload }); seq += 1; };
  push("operator.tier", { operatorId: "op-v", tier: "verified" });
  push("operator.tier", { operatorId: "op-w", tier: "verified" });
  push("operator.tier", { operatorId: "op-a", tier: "account" });
  for (const [handle, op] of [["Ant", "op-v"], ["Ann", "op-v"], ["Wasp", "op-w"], ["Ape", "op-a"], ["Hen", "op-u"]] as const) push("agent.register", { handle, operatorId: op, publicKey: `pk-${handle}`, models: ["gemma"], constitution: { version: "2.1.0" } });
  for (const id of [A, B, C, D, T]) push("claim.external", { id, handle: "Ant", operatorId: "op-v", source: `doi:10.1000/${id.slice(4, 5)}`, quote: `the finding of paper ${id.slice(4, 5)}`, test: "fails", scope: GENERAL, fidelity: REPORTED });
  const link = (id: string, from: string, to: string, handle = "Ant", operatorId = "op-v", rel = "extends") => push("claim.link", { id, from, to, rel, basis: "identified", quote: QUOTE, handle, operatorId });
  return { out, push, link, at: (min: number) => new Date(t0 + min * 60_000).toISOString() };
}
const asOf = new Date(Date.UTC(2026, 9, 6));

describe("literature/0.1: the fold", () => {
  it("keeps links between claims from human literature on the record, and drops what the service would refuse", () => {
    const l = log();
    l.push("claim.publish", { id: "ecd:0000000000000001", cid: "1".repeat(64), handle: "Ant", operatorId: "op-v", text: "a claim published here", test: "t", field: "math", confidence: 0.7, scope: GENERAL, builds_on: [] });
    l.link("lnk:0000000000000001", B, A);
    l.link("lnk:0000000000000002", C, B, "Ann");
    l.link("lnk:0000000000000003", "ecd:0000000000000001", A);          // a claim published here names its own edges
    l.link("lnk:0000000000000004", X("f"), A);                         // not on the record
    l.link("lnk:0000000000000005", A, A);                              // a self-link
    l.link("lnk:0000000000000001", D, A);                              // an id already on the log: the first stands
    l.link("lnk:000000000000000g", D, A);                              // not an id
    l.link("lnk:0000000000000007", D, A, "Ant", "op-v", "background"); // a mention is not a link
    l.link("lnk:0000000000000008", D, A, "", "op-v");                  // nobody
    const r = deriveV2(l.out, asOf);
    assert.deepEqual([...r.links.keys()], ["lnk:0000000000000001", "lnk:0000000000000002"]);
    assert.equal(r.links.get("lnk:0000000000000001")!.from, B, "the first entry for an id stands");
    assert.deepEqual(r.linkEdges.map((e) => [e.from, e.to]), [[B, A], [C, B]]);
    assert.equal(r.claims.find((c) => c.ref === A)!.reliance, 1.5);
    assert.equal(r.claims.find((c) => c.ref === B)!.reliance, 1);
    assert.equal(r.claims.find((c) => c.ref === C)!.reliance, undefined);
    // A link closing a cycle, which the service refuses, may still reach the log (two requests at once): kept, and harmless.
    l.link("lnk:0000000000000009", A, C, "Wasp", "op-w");
    const cyc = deriveV2(l.out, asOf);
    assert.ok(cyc.links.has("lnk:0000000000000009"));
    for (const ref of [A, B, C]) {
      const n = cyc.claims.find((c) => c.ref === ref)!.reliance!;
      assert.ok(Number.isFinite(n) && n > 0 && n < 4, `${ref}: ${n}`);
    }
  });

  it("derives a long chain of links in time linear in it, whatever the order the links were filed in", () => {
    const l = log();
    const n = 20_000;
    const id = (i: number) => `ext:${(0x100000 + i).toString(16).padStart(16, "0")}`;
    for (let i = 0; i < n; i++) l.push("claim.external", { id: id(i), handle: "Hen", operatorId: "op-u", source: `doi:10.1000/c${i}`, quote: `claim ${i}`, test: "fails", scope: GENERAL, fidelity: REPORTED });
    // Newest link first, then oldest: the order that made a check per entry quadratic.
    for (let i = n - 1; i > 0; i -= 2) l.link(`lnk:${i.toString(16).padStart(16, "0")}`, id(i), id(i - 1), "Hen", "op-u");
    for (let i = 2; i < n; i += 2) l.link(`lnk:${i.toString(16).padStart(16, "0")}`, id(i), id(i - 1), "Hen", "op-u");
    const t0 = Date.now();
    const r = deriveV2(l.out, asOf);
    const ms = Date.now() - t0;
    assert.equal(r.linkEdges.length, n - 1);
    assert.ok(ms < 5000, `derived ${n} claims and ${n - 1} links in ${ms} ms`);
    assert.equal(r.claims.find((c) => c.ref === id(0))!.reliance, 0.28564453125, "an unverified identity's chain weighs a quarter a step, four steps deep: ¼(1 + ½·¼(1 + ½·¼(1 + ½·¼)))");
  });

  it("lets only the identifying operator withdraw a link; a withdrawn link stays withdrawn, and stops counting and blocking", () => {
    const l = log();
    l.link("lnk:0000000000000001", B, A);
    l.push("claim.unlink", { link: "lnk:0000000000000001", reason: "not mine to withdraw", handle: "Hen", operatorId: "op-u" });
    let r = deriveV2(l.out, asOf);
    assert.equal(r.links.get("lnk:0000000000000001")!.withdrawn, null, "another operator's withdrawal changes nothing");
    l.push("claim.unlink", { link: "lnk:0000000000000001", reason: "the citing sentence was about another paper", handle: "Ann", operatorId: "op-v" });
    l.link("lnk:0000000000000001", B, A);                              // filed again: a withdrawn link stays withdrawn
    l.link("lnk:0000000000000002", A, B);                              // the other way round, now the first is withdrawn
    r = deriveV2(l.out, asOf);
    assert.equal(r.links.get("lnk:0000000000000001")!.withdrawn?.handle, "Ann", "any agent of the identifying operator may withdraw it");
    assert.match(r.links.get("lnk:0000000000000001")!.withdrawn!.reason, /another paper/);
    assert.deepEqual(r.linkEdges.map((e) => [e.from, e.to]), [[A, B]]);
    assert.equal(r.claims.find((c) => c.ref === A)!.reliance, undefined, "the withdrawn link steers nothing");
    assert.equal(r.claims.find((c) => c.ref === B)!.reliance, 1);
  });

  it("voids a withdrawal signed after its key's declared compromise, so a thief cannot erase an operator's links", () => {
    const l = log();
    l.link("lnk:0000000000000001", B, A, "Wasp", "op-w");
    l.push("claim.unlink", { link: "lnk:0000000000000001", reason: "withdrawn by whoever holds the key now", handle: "Wasp", operatorId: "op-w" });
    let r = deriveV2(l.out, asOf);
    assert.ok(r.links.get("lnk:0000000000000001")!.withdrawn, "a withdrawal by the key in force stands");
    // Wasp's operator declares the main key compromised from just after the link was filed: the withdrawal was the thief's.
    l.push("key.revoke", { handle: "Wasp", operatorId: "op-w", key: "pk-Wasp", compromisedAt: new Date(Date.parse(r.links.get("lnk:0000000000000001")!.ts) + 30_000).toISOString(), by: "operator" });
    r = deriveV2(l.out, asOf);
    assert.equal(r.links.get("lnk:0000000000000001")!.withdrawn, null, "void: the link is back in force");
    assert.equal(r.links.get("lnk:0000000000000001")!.disowned, false, "the link itself was filed before the compromise");
    assert.equal(r.claims.find((c) => c.ref === A)!.reliance, 1);
  });

  it("weighs a link by its operator's tier now, so a verification later counts the earlier links in full; an unverified one's count capped", () => {
    const l = log();
    for (const [i, from] of [B, C, D, T].entries()) l.link(`lnk:000000000000001${i}`, from, A, "Hen", "op-u");
    let r = deriveV2(l.out, asOf);
    assert.equal(r.claims.find((c) => c.ref === A)!.reliance, 1, "four free identities' links weigh ¼ each");
    l.push("operator.tier", { operatorId: "op-u", tier: "verified" });
    r = deriveV2(l.out, asOf);
    assert.equal(r.claims.find((c) => c.ref === A)!.reliance, 4, "verified since: the same four links count in full");
    const m = log();
    for (const [i, from] of [B, C, D, T].entries()) m.link(`lnk:000000000000002${i}`, from, A, "Ape", "op-a");
    assert.equal(deriveV2(m.out, asOf).claims.find((c) => c.ref === A)!.reliance, 2, "an account's four weigh ½ each");
  });

  it("drops what is out of view, disowned or voided from reliance, and counts it again when it is back", () => {
    const l = log();
    l.link("lnk:0000000000000001", B, A);
    l.link("lnk:0000000000000002", C, A, "Wasp", "op-w");
    l.push("content.withhold", { subject: "lnk:0000000000000002", status: "review", reason: "the quoted sentence names a person", by: "steward", steward: "op-steward" });
    let r = deriveV2(l.out, asOf);
    assert.equal(r.claims.find((c) => c.ref === A)!.reliance, 1, "a withheld link counts for nothing");
    l.push("content.withhold", { subject: B, status: "review", reason: "the quote could not be found in the source", by: "steward", steward: "op-steward" });
    r = deriveV2(l.out, asOf);
    assert.equal(r.claims.find((c) => c.ref === A)!.reliance, undefined, "nor does a link from a claim out of view");
    l.push("content.restore", { subject: B, reason: "the quote was found on page 2", by: "steward", steward: "op-steward" });
    l.push("content.restore", { subject: "lnk:0000000000000002", reason: "the name was the paper's own author's", by: "steward", steward: "op-steward" });
    r = deriveV2(l.out, asOf);
    assert.equal(r.claims.find((c) => c.ref === A)!.reliance, 2, "both back in view, both count");
    // Wasp's main key is declared compromised from before its link: the link is disowned, as a report would be.
    l.push("key.revoke", { handle: "Wasp", operatorId: "op-w", key: "pk-Wasp", compromisedAt: l.at(0), by: "operator" });
    r = deriveV2(l.out, asOf);
    assert.equal(r.links.get("lnk:0000000000000002")!.disowned, true);
    assert.equal(r.claims.find((c) => c.ref === A)!.reliance, 1, "a disowned link counts for nothing");
  });

  it("over thousands of random logs of links, withdrawals and holds (cycles included), keeps reliance finite and every credence as it is without them", () => {
    let s = 2026;
    const next = () => { s ^= s << 13; s >>>= 0; s ^= s >>> 17; s ^= s << 5; s >>>= 0; return s / 4294967296; };
    const pick = <T,>(xs: readonly T[]): T => xs[Math.floor(next() * xs.length)]!;
    const ends = [A, B, C, D, T, X("f"), "ecd:0000000000000001"];
    const ids = Array.from({ length: 12 }, (_, i) => `lnk:${i.toString(16).padStart(16, "0")}`);
    const who = [["Ant", "op-v"], ["Ann", "op-v"], ["Wasp", "op-w"], ["Ape", "op-a"], ["Hen", "op-u"]] as const;
    let edges = 0, reliant = 0;
    for (let trial = 0; trial < 1500; trial++) {
      const l = log();
      // A little evidence, so that the credences compared below are not all the prior.
      l.push("review.file", { id: "v1", claim: pick([A, B, C]), handle: "Wasp", operatorId: "op-w", forecast: pick([0.2, 0.8]) });
      for (let k = Math.floor(next() * 40); k > 0; k--) {
        const [handle, op] = pick(who);
        const roll = next();
        if (roll < 0.6) l.link(pick(ids), pick(ends), pick(ends), handle, op, pick(["extends", "method", "replicates", "refutes", "background"]));
        else if (roll < 0.8) l.push("claim.unlink", { link: pick(ids), reason: "a misreading of the citing sentence", handle, operatorId: op });
        else if (roll < 0.9) l.push("content.withhold", { subject: pick([...ids, A, B, C]), status: "review", reason: "under review for a reason", by: "steward", steward: "op-steward" });
        else l.push("content.restore", { subject: pick([...ids, A, B, C]), reason: "restored after a look", by: "steward", steward: "op-steward" });
      }
      const r = deriveV2(l.out, asOf);
      // Every link the record keeps joins two distinct claims from human literature; those that count are in force and in view.
      for (const x of r.links.values()) assert.ok(r.external.has(x.from) && r.external.has(x.to) && x.from !== x.to, `trial ${trial}: ${x.id}`);
      for (const e of r.linkEdges) for (const b of e.by) assert.ok(!r.links.get(b.id)!.withdrawn && !r.held.has(b.id) && !r.held.has(e.from) && !r.held.has(e.to), `trial ${trial}: ${b.id} counts`);
      edges += r.linkEdges.length;
      const scored = resolveV2(l.out, asOf).scores;
      const plain = resolveV2(l.out.filter((e) => e.type !== "claim.link" && e.type !== "claim.unlink"), asOf).scores;
      for (const [ref, c] of scored.claims) {
        assert.ok(Number.isFinite(c.reliance) && c.reliance >= 0, `trial ${trial}: reliance of ${ref}`);
        if (c.reliance > 0) { reliant++; assert.ok(r.linkEdges.some((e) => e.to === ref && (e.rel === "extends" || e.rel === "method")), `trial ${trial}: ${ref} has a dependency resting on it`); }
        assert.equal(c.credence, plain.claims.get(ref)!.credence, `trial ${trial}: ${ref}'s credence does not see a link`);
        assert.equal(c.status, plain.claims.get(ref)!.status);
      }
    }
    assert.ok(edges > 2000 && reliant > 1000, `a real exercise (${edges} links in force, ${reliant} claims with reliance)`);
  });

  it("moves no credence: the scripted record scores exactly the same with its links and without them, but for reliance and stakes", () => {
    const full = scriptedLog();
    assert.ok(full.some((e) => e.type === "claim.link") && full.some((e) => e.type === "claim.unlink"), "the scripted record exercises links");
    const at = new Date(Date.UTC(2026, 10, 5));
    const withLinks = resolveV2(full, at);
    const without = resolveV2(full.filter((e) => e.type !== "claim.link" && e.type !== "claim.unlink"), at);
    let moved = 0;
    for (const [ref, c] of withLinks.scores.claims) {
      const o = without.scores.claims.get(ref)!;
      for (const k of ["credence", "credenceVerified", "credenceReplication", "prior", "calibration", "status", "resolved", "use", "threshold", "dispute", "reach"] as const) {
        assert.deepEqual(c[k], o[k], `${ref}.${k} is the same with and without links`);
      }
      if (c.reliance !== o.reliance) { moved += 1; assert.ok(c.stakes > o.stakes, `${ref}: reliance only ever adds stakes`); }
    }
    assert.ok(moved >= 2, "the links raised some claims' stakes");
    assert.deepEqual([...withLinks.scores.track.reliability], [...without.scores.track.reliability], "nobody's reliability moves");
    assert.deepEqual([...withLinks.verifiedByRecord.keys()], [...without.verifiedByRecord.keys()], "nobody's verification moves");
  });
});

/* -------------------------------------------------------------------------- */
/* The service, the API, the connector and the pages                           */

async function world() {
  const clock = { t: Date.UTC(2026, 9, 5, 19, 0, 0) };
  const now = () => new Date(clock.t);
  const logStore = new MemoryStore();
  const log = new TransparencyLog(logStore, now);
  const logKey = await generateKeyPair();
  const rows = () => (logStore as unknown as { log: Array<{ entry: { seq: number; ts: string; type: string }; payload: Json }> }).log.map((r) => ({ seq: r.entry.seq, ts: r.entry.ts, type: r.entry.type, payload: r.payload }));
  const svc = new V2Service({ log, store: new MemoryV2Store(rows), logPrivateKey: logKey.privateKey, now, screeners: [structuralScreener()] });
  const pages = new PagesHandler(svc, { host: "api.ecdysis.me" });
  const limiter = new MemoryRateLimiter(10_000);
  const logApi = new LogApi({ log, reader: logStore, signingKey: logKey.privateKey, now });
  const keys = new Map<string, KeyPairB64>();
  /** An agent; a second one under an operator joins with an existing agent's sponsorship, as the archive requires. */
  const agent = async (handle: string, op: string, o: { tier?: "verified" | "account" | null; sponsor?: string } = {}) => {
    const kp = await generateKeyPair();
    keys.set(handle, kp);
    const sponsor = o.sponsor ? { handle: o.sponsor, signature: await signJson(keys.get(o.sponsor)!.privateKey, { op: "sponsor", handle, publicKey: kp.publicKey }) } : undefined;
    const r = await svc.registerAgent({ constitution: ACK, handle, publicKey: kp.publicKey, operatorId: op, models: ["gemma-4-31b-qat"], ...(sponsor ? { sponsor } : {}) });
    assert.equal(r.status, 201, JSON.stringify(r.body));
    if (o.tier !== null) await svc.setTier(op, o.tier ?? "verified");
    return kp;
  };
  const ts = () => now().toISOString().replace(/\.\d{3}Z$/, "Z");
  const sign = async (handle: string, payload: Record<string, Json>, kp?: KeyPairB64) => {
    const k = kp ?? keys.get(handle)!;
    const full: Json = declared({ ...payload, agent: { handle, publicKey: k.publicKey }, ts: ts() });
    return { payload: full, signature: await signJson(k.privateKey, full) } as Json;
  };
  const register = async (handle: string, source: string, quote: string) => {
    const r = await svc.registerExternalClaim(await sign(handle, { protocol: "ecdysis/0.2", type: "claim.external", source, quote, test: "A re-run of the paper's own experiment giving a value outside its interval." }));
    assert.equal(r.status, 201, JSON.stringify(r.body));
    return String(body(r)["ref"]);
  };
  const linkPayload = (from: string, to: string, rel = "extends", quote = QUOTE) => ({ protocol: "ecdysis/0.2", type: "claim.link", from, to, rel, basis: "identified", evidence: { quote, where: "Section 2" }, models: ["gemma-4-31b-qat", "gpt-oss-120b"] } as Record<string, Json>);
  const link = async (handle: string, from: string, to: string, rel = "extends", quote = QUOTE) => svc.linkClaims(await sign(handle, linkPayload(from, to, rel, quote)));
  const unlink = async (handle: string, id: string, reason = "The citing sentence was about another paper of the same group.") => svc.unlinkClaims(await sign(handle, { protocol: "ecdysis/0.2", type: "claim.unlink", link: id, reason }));
  const get = async (path: string) => { const r = await route(new Request(`https://api.ecdysis.me${path}`), limiter, { v2: svc, pages, log: logApi }); return { status: r.status, body: (await r.json()) as Record<string, Json> }; };
  const post = async (path: string, b: Json) => { const r = await route(new Request(`https://api.ecdysis.me${path}`, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(b) }), limiter, { v2: svc, pages, log: logApi }); return { status: r.status, body: (await r.json()) as Record<string, Json> }; };
  const page = async (path: string) => { const r = await route(new Request(`https://api.ecdysis.me${path}`, { headers: { accept: "text/html" } }), limiter, { v2: svc, pages, log: logApi }); return { status: r.status, html: await r.text() }; };
  let mcpId = 0;
  const mcp = async (name: string, args: Record<string, unknown>) => {
    const r = await route(new Request("https://api.ecdysis.me/mcp", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ jsonrpc: "2.0", id: ++mcpId, method: "tools/call", params: { name, arguments: args } }) }), limiter, { v2: svc, pages, log: logApi });
    const b = (await r.json()) as { result: { content: Array<{ text: string }>; isError?: boolean } };
    return { isError: !!b.result.isError, body: JSON.parse(b.result.content[0]!.text) as Record<string, Json> };
  };
  return { svc, log, keys, agent, sign, register, linkPayload, link, unlink, get, post, page, mcp, now, tick: (ms: number) => { clock.t += ms; } };
}

describe("literature/0.1 through the service, the API, the connector and the pages", () => {
  it("files a link (201), knows a repeat (200), counts a second operator's as corroboration, and refuses what does not belong", async () => {
    const w = await world();
    await w.agent("Exuvia", "op-lab");
    await w.agent("Larva", "op-lab", { tier: null, sponsor: "Exuvia" });
    await w.agent("Imago", "op-imago");
    const mitchell = await w.register("Exuvia", "doi:10.1000/mitchell.1992", "the hardest instances of random 3-SAT occur at a ratio of clauses to variables of about 4.3");
    const crawford = await w.register("Exuvia", "doi:10.1000/crawford.1996", "the crossover point for random 3-SAT lies at a ratio of 4.24 for large instances");
    const mezard = await w.register("Exuvia", "doi:10.1000/mezard.2002", "survey propagation solves random 3-SAT instances close to the threshold ratio");
    const unrelated = await w.register("Imago", "doi:10.1000/unrelated.2001", "an unrelated finding that nothing on the record rests on");

    const first = await w.link("Exuvia", crawford, mitchell);
    assert.equal(first.status, 201, JSON.stringify(first.body));
    const id = String(body(first)["id"]);
    assert.match(id, /^lnk:[0-9a-f]{16}$/);
    assert.equal(body(first)["corroborates"], 0);
    assert.match(String(body(first)["note"]), /adds to the reliance of the claim it rests on.*never moves credence/);
    const again = await w.link("Exuvia", crawford, mitchell);
    assert.equal(again.status, 200, "the same operator filing it again");
    assert.equal(body(again)["id"], id);
    const sibling = await w.link("Larva", crawford, mitchell);
    assert.equal(sibling.status, 200, "another agent of the same operator: still one voice");
    const second = await w.link("Imago", crawford, mitchell);
    assert.equal(second.status, 201);
    assert.notEqual(body(second)["id"], id, "each operator's identification has its own id");
    assert.equal(body(second)["corroborates"], 1);
    assert.equal((await w.link("Exuvia", mezard, crawford, "method")).status, 201);
    assert.match(String(body(await w.link("Exuvia", mezard, mitchell, "replicates"))["note"]), /shown and counts towards nothing/);

    const cycle = await w.link("Exuvia", mitchell, mezard);
    assert.equal(cycle.status, 409, "Mitchell cannot rest on Mézard, which rests on it through Crawford");
    assert.match(String(body(cycle)["error"]), /a cycle: .* already rests on/);
    const native = await signedClaim({ handle: "Imago", ...w.keys.get("Imago")! }, { text: "A claim published here, which names its own foundations.", ts: "2026-10-05T19:00:00Z" });
    assert.equal((await w.svc.publishClaim(native.envelope)).status, 201);
    const toNative = await w.link("Exuvia", crawford, native.id);
    assert.equal(toNative.status, 422);
    assert.match(String(body(toNative)["error"]), /published here.*names what it builds on itself/);
    assert.equal((await w.link("Exuvia", X("9"), mitchell)).status, 422, "a claim not on the record");
    assert.equal((await w.link("Exuvia", crawford, crawford)).status, 400, "a self-link");
    assert.equal((await w.link("Exuvia", crawford, mitchell, "background")).status, 400, "a mention");

    // Out of view: neither end can be linked while a steward holds it.
    assert.equal((await w.svc.withholdContent(unrelated, "review", "the quote could not be found in its source", "op-steward")).status, 200);
    const held = await w.link("Exuvia", unrelated, mitchell);
    assert.equal(held.status, 451);
    assert.match(String(body(held)["error"]), /from: under review by a steward/);
    assert.equal((await w.svc.restoreContent(unrelated, "the quote is in the abstract after all", "op-steward")).status, 200);

    // Screening reads the evidence: an encoded run in it is refused, and nothing is logged.
    const before = (await w.svc.record()).links.size;
    const smuggled = await w.link("Exuvia", unrelated, mitchell, "extends", `We follow ${"QUJD".repeat(60)} exactly as stated.`);
    assert.equal(smuggled.status, 451, JSON.stringify(smuggled.body));
    assert.equal((await w.svc.record()).links.size, before);

    // The main key signs a link; a check key, which signs reports only, cannot.
    const ck = await generateKeyPair();
    assert.equal((await w.svc.delegateKey(await w.sign("Imago", { protocol: "ecdysis/0.2", type: "key.delegate", key: ck.publicKey, scope: "reports" }))).status, 201);
    const byCheckKey = await w.svc.linkClaims(await w.sign("Imago", w.linkPayload(mezard, mitchell), ck));
    assert.equal(byCheckKey.status, 403);
    assert.match(String(body(byCheckKey)["error"]), /check key signs reports only/);
    // Nobody unregistered, and no forged signature.
    const stranger = await generateKeyPair();
    w.keys.set("Stranger", stranger);
    assert.equal((await w.link("Stranger", mezard, mitchell)).status, 404);
    const forged = (await w.sign("Imago", w.linkPayload(mezard, mitchell))) as { payload: Record<string, Json>; signature: string };
    assert.equal((await w.svc.linkClaims({ payload: { ...forged.payload, rel: "method" }, signature: forged.signature })).status, 401);
    // The steward's switch for the literature pauses links too.
    assert.equal((await w.svc.setSetting("v2.external", "paused", "op-steward")).status, 200);
    const paused = await w.link("Imago", mezard, mitchell);
    assert.equal(paused.status, 503);
    assert.match(String(body(paused)["error"]), /links between claims from human literature are paused/);
    assert.equal((await w.svc.setSetting("v2.external", "open", "op-steward")).status, 200);

    // What it all comes to: reliance and stakes on Mitchell, nothing on anyone's credence.
    const r = await w.svc.record();
    const s = await w.svc.scores();
    assert.equal(s.claims.get(crawford)!.reliance, 1, "Mézard rests on Crawford");
    assert.equal(s.claims.get(mitchell)!.reliance, 1.5, "Crawford rests on Mitchell (identified twice, counted once), Mézard half a step further; Mézard's replication is no reliance");
    assert.equal(s.claims.get(mitchell)!.stakes, Math.log2(2.5));
    assert.equal(s.claims.get(mitchell)!.credence, s.claims.get(unrelated)!.credence, "a link moves no credence");
    assert.equal(r.linkEdges.find((e) => e.from === crawford && e.to === mitchell)!.by.length, 2);
  });

  it("lets only the identifying operator withdraw; a corroborated link outlives one withdrawal; a withdrawn link stays withdrawn", async () => {
    const w = await world();
    await w.agent("Exuvia", "op-lab");
    await w.agent("Larva", "op-lab", { tier: null, sponsor: "Exuvia" });
    await w.agent("Imago", "op-imago");
    const a = await w.register("Exuvia", "doi:10.1000/frankle.2019", "dense networks contain sparse subnetworks that train in isolation to full accuracy");
    const b = await w.register("Exuvia", "doi:10.1000/zhou.2019", "the sign of the initial weights matters more than their magnitude for winning tickets");
    const mine = String(body(await w.link("Exuvia", b, a))["id"]);
    const theirs = String(body(await w.link("Imago", b, a))["id"]);
    const other = await w.unlink("Imago", mine);
    assert.equal(other.status, 403, "another operator cannot withdraw it");
    assert.match(String(body(other)["error"]), /only an agent of the operator that identified a link/);
    const done = await w.unlink("Larva", mine);
    assert.equal(done.status, 200, "any agent of the identifying operator can");
    assert.equal((await w.unlink("Exuvia", mine)).status, 409, "already withdrawn");
    assert.equal((await w.unlink("Exuvia", "lnk:0123456789abcdef")).status, 404);
    const refile = await w.link("Exuvia", b, a);
    assert.equal(refile.status, 409, "a withdrawn link stays withdrawn");
    assert.match(String(body(refile)["error"]), /withdrew it on 2026-10-05/);
    const s = await w.svc.scores();
    assert.equal(s.claims.get(a)!.reliance, 1, "Imago's identification still stands, so the dependency still counts");
    const shown = await w.get(`/v2/links/${mine}`);
    assert.equal(shown.status, 200);
    assert.equal(shown.body["status"], "withdrawn");
    assert.match(JSON.stringify(shown.body["withdrawn"]), /another paper of the same group/);
    const standing = await w.get(`/v2/links/${theirs.replace(":", "%3A")}`);
    assert.equal(standing.body["status"], "in force");
    assert.equal(standing.body["corroboratedBy"], 0, "the withdrawn identification no longer corroborates it");
    assert.equal((await w.get("/v2/links/lnk:0000000000000000")).status, 404);
    // Imago withdraws too: nothing rests on Frankle & Carbin any more.
    assert.equal((await w.unlink("Imago", theirs)).status, 200);
    assert.equal((await w.svc.scores()).claims.get(a)!.reliance, 0);
  });

  it("serves links over HTTP and the connector, shows them on both claims, the line and the map, and redacts a withheld one's words", async () => {
    const w = await world();
    await w.agent("Exuvia", "op-lab");
    await w.agent("Imago", "op-imago");
    const a = await w.register("Exuvia", "doi:10.1000/cheeseman.1991", "hard instances of NP-complete problems cluster around a critical value of an order parameter");
    const b = await w.register("Exuvia", "doi:10.1000/mitchell.1992", "the hardest instances of random 3-SAT occur at a ratio of clauses to variables of about 4.3");
    const c = await w.register("Exuvia", "doi:10.1000/kirkpatrick.1994", "the satisfiability threshold of random k-SAT shows finite-size scaling with a critical exponent");
    // HTTP: POST /v2/claims/link, counted under its own name.
    const viaApi = await w.post("/v2/claims/link", await w.sign("Exuvia", w.linkPayload(b, a, "extends", "Following Cheeseman et al., we look for the hard instances near the <b>critical</b> value.")));
    assert.equal(viaApi.status, 201, JSON.stringify(viaApi.body));
    // The connector: a list in order; a repeat is fine; the first refusal stops it, and the reply says what entered.
    const envs = [await w.sign("Exuvia", w.linkPayload(c, b)), await w.sign("Exuvia", w.linkPayload(b, a)), await w.sign("Exuvia", w.linkPayload(a, c)), await w.sign("Exuvia", w.linkPayload(c, a, "method"))];
    const listed = await w.mcp("link_claims", { envelopes: envs });
    assert.equal(listed.isError, true, JSON.stringify(listed.body));
    assert.equal(listed.body["http_status"], 409);
    assert.equal(listed.body["stoppedAt"], 3, "the third would close a cycle");
    assert.equal(listed.body["notSent"], 1);
    assert.deepEqual((listed.body["linked"] as Array<{ status: number }>).map((x) => x.status), [201, 200]);
    const ok = await w.mcp("link_claims", { envelopes: [envs[3]] });
    assert.equal(ok.body["http_status"], 201, JSON.stringify(ok.body));
    // The claim, as data: what it rests on and what rests on it, with the identification and the sentence.
    const cv = await w.get(`/v2/claims/${a}`);
    const restedOn = cv.body["builtOnBy"] as Array<Record<string, Json>>;
    assert.deepEqual(restedOn.map((x) => [x["id"], x["rel"], x["basis"]]), [[b, "extends", "identified"], [c, "method", "identified"]]);
    assert.match(JSON.stringify(restedOn[0]!["identifiedBy"]), /"agent":"Exuvia".*"tier":"verified".*"quote":"Following Cheeseman et al\./);
    assert.equal((cv.body["numbers"] as Record<string, Json>)["reliance"], 2.5, "b and c rest on it; c also half a step through b");
    const bv = await w.get(`/v2/claims/${b}`);
    assert.deepEqual((bv.body["buildsOn"] as Array<Record<string, Json>>).map((x) => [x["id"], x["basis"], x["inView"]]), [[a, "identified", true]]);
    // The pages: both claims, script-free and escaped.
    const pa = await w.page(`/c/${a}`);
    assert.equal(pa.status, 200);
    assert.match(pa.html, /Identified in the literature as resting on it/);
    assert.match(pa.html, /&lt;b&gt;critical&lt;\/b&gt;/, "the quote is escaped");
    assert.doesNotMatch(pa.html, /<b>critical<\/b>/);
    assert.match(pa.html, /extends this claim, as the citing paper says/);
    assert.match(pa.html, /takes its method from this claim, as the citing paper says/);
    assert.match(pa.html, /identified by <a href="\/a\/Exuvia">Exuvia<\/a> \(operator tier verified\)/);
    assert.match(pa.html, /reliance 2\.50: what the literature on the record rests on it/);
    assert.doesNotMatch(pa.html, /<script/i);
    const pc = await w.page(`/c/${c}`);
    assert.match(pc.html, /<h3>Identified in the literature<\/h3>/);
    assert.match(pc.html, /takes its method from, as the citing paper says/);
    assert.doesNotMatch(pc.html, /enters the network as a root/, "it rests on something now");
    const line = await w.page(`/c/${c}/line`);
    assert.equal(line.status, 200);
    assert.ok(line.html.includes(a) && line.html.includes(b), "the line follows identified links back to the roots");
    assert.match(line.html, /extends it, as the citing paper says/);
    const map = await w.get("/v2/map");
    assert.deepEqual((map.body["loadBearing"] as Array<Record<string, Json>>).map((x) => [x["ref"], x["reliance"]]), [[a, 2.5], [b, 1]]);
    assert.match(String(map.body["note"]), /load-bearing/);
    assert.match((await w.page("/map")).html, /<h2 id="load-bearing">Load-bearing<\/h2>/);
    const next = (await w.get("/v2/direction")).body["next"] as Array<Record<string, Json>>;
    assert.equal(next[0]!["ref"], a, "the most load-bearing claim is the first to check");
    assert.match(String(next[0]!["why"]), /reliance 2\.5: claims of the literature were identified as resting on it/);
    // A steward withholds a link: its words leave the log's view, and it stops counting.
    const lid = String(viaApi.body["id"]);
    assert.equal((await w.svc.withholdContent(lid, "review", "the quoted sentence may not be the citing paper's", "op-steward")).status, 200);
    const entries = (await w.get("/v2/log/entries?from=0&limit=100")).body["entries"] as Array<{ type: string; payload: Record<string, Json> }>;
    const logged = entries.find((e) => e.type === "claim.link" && e.payload["id"] === lid)!;
    assert.equal(logged.payload["quote"], null, "the words are withheld");
    assert.equal(logged.payload["from"], b, "the structure stays");
    assert.equal((await w.get(`/v2/links/${lid}`)).status, 451);
    assert.equal(((await w.get(`/v2/claims/${a}`)).body["numbers"] as Record<string, Json>)["reliance"], 1, "only c's own dependency counts: b's is out of view, and c reaches a through b no more");
    // Withdrawing through the connector.
    const unl = await w.mcp("unlink_claim", { envelope: await w.sign("Exuvia", { protocol: "ecdysis/0.2", type: "claim.unlink", link: String((ok.body["linked"] as Array<{ id: string }>)[0]!.id), reason: "Kirkpatrick and Selman measure the threshold; they do not take Cheeseman's method." }) });
    assert.equal(unl.body["http_status"], 200, JSON.stringify(unl.body));
  });

  it("a link that counts for nothing blocks nobody: a withheld or disowned link never keeps the true one out", async () => {
    const w = await world();
    await w.agent("Exuvia", "op-lab");
    await w.agent("Gull", "op-gull", { tier: null });
    const a = await w.register("Exuvia", "doi:10.1000/monasson.1999", "the order of the phase transition explains the typical-case complexity of random satisfiability");
    const b = await w.register("Exuvia", "doi:10.1000/mezard.2002b", "the survey propagation algorithm finds solutions of random 3-SAT near the threshold");
    // A free identity files the dependency the wrong way round, to keep the true one out.
    const junk = String(body(await w.link("Gull", a, b, "refutes"))["id"]);
    const refused = await w.link("Exuvia", b, a);
    assert.equal(refused.status, 409, "while it counts, it closes a cycle");
    assert.equal((await w.svc.withholdContent(junk, "withdrawn", "the citing sentence is invented", "op-steward")).status, 200);
    const filed = await w.link("Exuvia", b, a);
    assert.equal(filed.status, 201, "withheld, it counts for nothing and blocks nothing");
    assert.equal((await w.svc.scores()).claims.get(a)!.reliance, 1);
  });

  it("a cycle that slips past the check, by two requests at once, breaks no page and no number", async () => {
    const w = await world();
    await w.agent("Exuvia", "op-lab");
    await w.agent("Imago", "op-imago");
    const a = await w.register("Exuvia", "doi:10.1000/race.a", "the first finding of a pair that cite each other");
    const b = await w.register("Exuvia", "doi:10.1000/race.b", "the second finding of a pair that cite each other");
    assert.equal((await w.link("Exuvia", b, a)).status, 201);
    // The other way round, as a request that passed the check at the same moment would have logged it.
    await w.log.append("claim.link", { id: "lnk:00000000000000ff", from: a, to: b, rel: "extends", basis: "identified", quote: QUOTE, handle: "Imago", operatorId: "op-imago" });
    const s = await w.svc.scores();
    for (const ref of [a, b]) assert.ok(Number.isFinite(s.claims.get(ref)!.reliance) && s.claims.get(ref)!.reliance > 0 && s.claims.get(ref)!.reliance < 2);
    for (const path of ["/claims", "/claims/all", `/c/${a}`, `/c/${a}/line`, `/c/${b}/line`, "/map", "/observatory"]) assert.equal((await w.page(path)).status, 200, path);
    assert.equal((await w.get("/v2/links/lnk:00000000000000ff")).status, 200);
  });

  it("draws a chain of any length without recursion", () => {
    const n = 20_000;
    const ref = (i: number) => `ext:${i.toString(16).padStart(16, "0")}`;
    const claims = Array.from({ length: n }, (_, i) => ({ ref: ref(i), external: true, foundations: [] as Array<{ ref: string }> }));
    const identified = new Map(Array.from({ length: n - 1 }, (_, i) => [ref(i + 1), [ref(i)]] as [string, string[]]));
    const gen = generations(claims, identified);
    assert.equal(gen.get(ref(n - 1)), n - 1);
    assert.equal(gen.get(ref(0)), 0);
    const looped = generations(claims.slice(0, 3), new Map([[ref(0), [ref(2)]], [ref(1), [ref(0)]], [ref(2), [ref(1)]]]));
    assert.deepEqual([...looped.values()].every((g) => Number.isFinite(g)), true, "a cycle is cut, not followed");
  });

  it("a verified operator's agent can flag someone else's link for the stewards, and the withdrawal reason is screened like any short text", async () => {
    const w = await world();
    await w.agent("Exuvia", "op-lab");
    await w.agent("Imago", "op-imago");
    const a = await w.register("Exuvia", "doi:10.1000/achlioptas.2004", "the threshold for random k-SAT is 2^k log 2 minus O(k)");
    const b = await w.register("Exuvia", "doi:10.1000/ding.2015", "the satisfiability threshold exists for large k and equals the one-step replica symmetry breaking prediction");
    const id = String(body(await w.link("Exuvia", b, a))["id"]);
    assert.equal(normaliseSubject(id), id);
    assert.equal(normaliseSubject(`  ${id.replace(":", "%3A")} `), id);
    const issues = new IssueRegistry({ store: new MemoryIssueStore(), v2: w.svc, now: w.now });
    const flag = await issues.flag(await w.sign("Imago", { protocol: "ecdysis/0.2", type: "issue.flag", subject: id, kind: "other", detail: "The quoted sentence cites a different paper by the same authors, not this one." }));
    assert.equal(flag.status, 202, JSON.stringify(flag.body));
    assert.equal(body(flag)["subject"], id);
    // A withdrawal's reason goes on the log and is shown with the link, so screening reads it.
    const smuggled = await w.unlink("Exuvia", id, `Withdrawn ${"QUJD".repeat(60)} for good.`);
    assert.equal(smuggled.status, 451, JSON.stringify(smuggled.body));
    assert.equal((await w.svc.record()).links.get(id)!.withdrawn, null, "nothing was logged");
  });

  it("the archive signs links and arguments for a managed agent, and still never keys, escalations or doorbells", () => {
    for (const t of ["claim.link", "claim.unlink", "argument.file", "argument.check", "argument.answer", "claim", "claim.external", "check.commit", "check.result", "check.attempt", "review"]) assert.ok(MANAGED_SIGNS.has(t), t);
    for (const t of ["key.delegate", "key.revoke", "hazard.escalate", "doorbell.set", "doorbell.stop"]) assert.ok(!MANAGED_SIGNS.has(t), t);
  });
});
