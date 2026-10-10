/**
 * The redesign of 9 October 2026 (Lucy Griffiths): the claims for people, under the paper each comes from, and the story
 * of a claim's checks in plain words. The tests show the story following the record and never saying more than the
 * counted checks do (no agent called independent, no paper where there is none), the list grouping, filtering, sorting
 * and paging from the address bar with anything it does not offer ignored, a paper the scout could not match listed last
 * and said so, fields merged where two indexes name one field twice, the claim page reading the same record, and hostile
 * text from an index or an agent escaped wherever it lands.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { MemoryStore } from "../src/store/memory-store.js";
import { TransparencyLog } from "../src/core/log.js";
import { generateKeyPair, signJson, type KeyPairB64 } from "../src/core/crypto.js";
import { MemoryV2Store, V2Service } from "../src/api/v2/service.js";
import { featuredFinding, OffLogMemo, PagesHandler } from "../src/api/v2/pages.js";
import { MemoryContextStore } from "../src/api/v2/context.js";
import { MemoryQuoteCheckStore, type QuoteStatus } from "../src/api/v2/quotes.js";
import { checkStory, CONTEXT_VERSION, fieldName, surnames, type PaperRecord, type StoryInput } from "../src/core/v2/context.js";
import { claimsListPageV2, credenceMeter, longPost, peopleQuery, type PeopleClaimV2 } from "../src/web/v2/pages.js";
import type { Bundle } from "../src/core/v2/receipts.js";
import type { Json } from "../src/core/canonical.js";
import { CONSTITUTION_VERSION, constitutionHash } from "../src/core/constitution.js";
import { declared } from "./kinds-kit.js";
import { signedClaim } from "./claims-kit.js";
const ACK = { version: CONSTITUTION_VERSION, hash: await constitutionHash() };

const BASE: StoryInput = {
  kind: "empirical", status: "unchecked", credence: 0.55, prior: 0.55, external: true, operators: { confirming: 0, failing: 0 }, checks: [],
  arguments: { upheld: 0, dismissed: 0, open: 0 }, blockers: [], by: { handle: "Ant", at: "2026-10-07T09:00:00Z" }, declared: [], period: null,
};
type Who = "other" | "own" | "unverified" | "unaudited" | "ignored";
const confirmed = (agent: string, tests = "verification", who: Who = "other") => ({ agent, tests, counted: true, outcome: "confirmed", who });
const failed = (agent: string, tests = "verification", who: Who = "other") => ({ agent, tests, counted: true, outcome: "failed", who });
const inconclusive = (agent: string) => ({ agent, tests: "verification", counted: true, outcome: "inconclusive" });

describe("the story of a claim's checks", () => {
  it("says nobody has checked it, who registered it and when, and that a verification of the paper's own data comes first", () => {
    const s = checkStory(BASE);
    assert.deepEqual(s.lede, ["Nobody has checked this claim on Ecdysis yet."]);
    assert.deepEqual(s.checked, ["Ant registered the claim on 7 October 2026, with a test written from the paper.", "No check has been filed yet."]);
    assert.deepEqual([s.shows, s.notYet, s.showsTone], [null, null, null], "nothing to show until a check has a result");
    assert.equal(s.next, "a verification: re-running the authors' analysis on their own data, where they have published it.");
    assert.equal(s.checkedBy, "Nobody yet");
    assert.match(checkStory({ ...BASE, period: "October 2017 to May 2019" }).next, /on their own data, which covers October 2017 to May 2019, where they have published it\.$/);
    assert.deepEqual(checkStory(BASE), s, "the same record tells the same story");
  });

  it("tells a verification as what it shows and what it does not, and asks next for a reproduction of the claim's period", () => {
    const s = checkStory({ ...BASE, status: "supported", credence: 0.72, operators: { confirming: 1, failing: 0 }, checks: [confirmed("Imago")], period: "October 2017 to May 2019" });
    assert.deepEqual(s.lede, ["Imago re-ran the authors' analysis on the paper's own data and got the paper's result."]);
    assert.equal(s.checked[1], "Imago re-ran the authors' analysis on the paper's own data, and got the paper's result.");
    assert.equal(s.showsTone, "show");
    assert.deepEqual(s.shows, ["The published numbers are what the authors' own data and analysis produce: the analysis was reported correctly."]);
    assert.deepEqual(s.notYet, ["That the finding holds with new data, from new participants, at other times or in other places. That needs a reproduction, not a re-run. Until one confirms it, it cannot be established, and each verification counts half."]);
    // credence/0.6: an object defined by its construction is checked by checking the object, and reproduced by running it afresh.
    const object = checkStory({ ...BASE, world: false, status: "supported", checks: [confirmed("Imago")] });
    assert.deepEqual(object.shows, ["The published numbers are what the authors' own data and analysis produce: for an object defined by its construction, checking the object itself is the test."]);
    assert.deepEqual(object.notYet, ["Whether the construction gives the same when it is run afresh: a reproduction runs it again."]);
    assert.equal(object.next, "a reproduction: the construction run afresh.");
    assert.doesNotMatch(JSON.stringify(object), /counts half|new participants/);
    assert.equal(s.next, "a reproduction, meaning the same study with new data from the same population and period, October 2017 to May 2019.");
    assert.equal(s.checkedBy, "1 agent, confirming");
    const two = checkStory({ ...BASE, status: "supported", operators: { confirming: 2, failing: 0 }, checks: [confirmed("Imago"), confirmed("Moth")] });
    assert.deepEqual(two.lede, ["Two agents each re-ran the authors' analysis on the paper's own data and got the paper's results."]);
    assert.equal(two.checked[1], "Imago and Moth each re-ran the authors' analysis on the paper's own data, and both got the paper's results.");
    assert.equal(two.checkedBy, "2 agents, both confirm");
  });

  it("tells a reproduction as a test of the finding, leaves the design to robustness tests and arguments, and asks for what the record still needs", () => {
    const s = checkStory({ ...BASE, status: "supported", operators: { confirming: 2, failing: 0 }, checks: [confirmed("Imago"), confirmed("Moth", "reproduction"), { agent: "Lark", tests: "extension", counted: false, outcome: "failed" }], period: "2009 to 2012" });
    assert.deepEqual(s.lede, ["Two agents checked it, and both got the paper's result: Imago re-ran the authors' analysis on the paper's own data, and Moth repeated the method on new data."], "never 'every check', when a robustness test failed");
    assert.ok(s.checked.includes("Moth repeated the authors' method on new data from the same population and period (2009 to 2012), and got the paper's result."));
    assert.deepEqual(s.shows, ["The finding held when the authors' method was repeated on new data from the same population and period."]);
    assert.match(s.notYet![0]!, /^Whether the method measures what the claim says/);
    assert.equal(s.next, "a reproduction run with a different family of AI model: established needs confirming replication tests from two verified operators and two families of model, and the credence its use calls for.");
    const one = checkStory({ ...BASE, status: "supported", operators: { confirming: 1, failing: 0 }, checks: [confirmed("Moth", "reproduction")] });
    assert.equal(one.next, "a reproduction by a second verified operator other than the registrant's, ideally working with a different family of AI model: confirming replication tests from two verified operators, run with two families of model, can establish a claim.");
    const self = checkStory({ ...BASE, checks: [confirmed("Ant", "verification", "own"), confirmed("Ant", "reproduction", "own")] });
    assert.deepEqual(self.lede.slice(0, 1), ["Ant (an agent of the registrant's operator) re-ran the authors' analysis on the paper's own data and repeated the method on new data, and got the paper's result both times."]);
  });

  it("tells a failure, and a disagreement, without a verdict the record has not given", () => {
    const f = checkStory({ ...BASE, status: "contested", credence: 0.3, operators: { confirming: 0, failing: 1 }, checks: [failed("Imago")] });
    assert.deepEqual(f.lede, ["Imago re-ran the authors' analysis on the paper's own data and did not get the paper's result."]);
    assert.equal(f.showsTone, "fail");
    assert.deepEqual(f.shows, ["The published results could not be obtained from the authors' own data and analysis."]);
    assert.deepEqual(f.notYet, ["Whether the fault is in the analysis, in its report or in the check itself: more checks by verified operators will show which."]);
    assert.equal(f.next, "a replication test by a second verified operator other than the registrant's: two failing ones can refute the claim, and a confirming one leaves it contested.");
    assert.equal(f.checkedBy, "1 agent, failing");
    const both = checkStory({ ...BASE, status: "contested", operators: { confirming: 0, failing: 2 }, checks: [failed("Imago"), failed("Moth", "reproduction")] });
    assert.deepEqual(both.lede, ["Two agents checked it, and none got the paper's result: Imago re-ran the authors' analysis on the paper's own data, and Moth repeated the method on new data."]);
    assert.deepEqual(both.shows, ["The published results could not be obtained from the authors' own data and analysis.", "The finding did not hold when the authors' method was repeated on new data from the same population and period."]);
    const m = checkStory({ ...BASE, status: "contested", operators: { confirming: 1, failing: 1 }, checks: [confirmed("Imago"), failed("Moth")] });
    assert.deepEqual(m.lede, ["The verifications disagree: Imago got the paper's result, and Moth did not."]);
    assert.equal(m.showsTone, "mixed");
    assert.deepEqual(checkStory({ ...BASE, checks: [confirmed("Imago", "reproduction"), failed("Moth", "reproduction"), confirmed("Lark"), failed("Gnat")] }).lede, ["The checks disagree: of the verifications, Lark got the paper's result, and Gnat did not; of the reproductions, Imago got the paper's result, and Moth did not."]);
    // A verification that holds and a reproduction that fails answer two questions, and both can be so: no disagreement.
    const split = checkStory({ ...BASE, status: "contested", operators: { confirming: 1, failing: 1 }, checks: [confirmed("Imago"), failed("Imago", "reproduction")], period: "2009 to 2012" });
    assert.deepEqual(split.lede, ["Imago re-ran the authors' analysis on the paper's own data and got the paper's result, but did not get it when it repeated the method on new data."]);
    assert.equal(split.showsTone, "split");
    assert.deepEqual(split.shows, ["The published numbers are what the authors' own data and analysis produce: the analysis was reported correctly.", "But the finding did not hold when the authors' method was repeated on new data from the same population and period."]);
    assert.match(split.notYet![0]!, /^Whether the first new data were unusual or the finding does not hold beyond the paper's own data/);
    assert.equal(split.next, "a reproduction by a second verified operator other than the registrant's: whether the finding holds on new data from the same population and period, 2009 to 2012, is what is in question.");
    assert.doesNotMatch(JSON.stringify(split), /disagree/);
    assert.deepEqual(checkStory({ ...BASE, checks: [confirmed("Imago"), failed("Moth", "reproduction")] }).lede, ["Imago re-ran the authors' analysis on the paper's own data and got the paper's result, but Moth repeated the method on new data and did not."]);
    assert.equal(m.next, "more replication tests by verified operators, and re-runs of the disagreeing checks' receipts, which show whether each check's own code gives what it reported.");
    assert.equal(m.checkedBy, "2 agents: 1 confirms, 1 fails");
    for (const story of [f, both, m, split]) assert.doesNotMatch(JSON.stringify(story), /\b(refuted|debunked|wrong|false)\b|settles (it|which)/i, "no verdict before the record gives one");
    const settled = checkStory({ ...BASE, status: "refuted", credence: 0.12, checks: [failed("Imago"), failed("Moth", "reproduction")] });
    assert.equal(settled.next, "a robustness test: the same question asked of other data or by another method, to say where the finding holds. The claim itself is refuted.");
  });

  it("counts neither a robustness test nor a disowned check, tells an inconclusive one as filed, and says what stopped the checks", () => {
    const robust = checkStory({ ...BASE, checks: [{ agent: "Lark", tests: "extension", counted: false, outcome: "failed" }] });
    assert.deepEqual(robust.lede, ["It has been tested only under changed conditions so far, which shows where a finding holds but does not count for or against it."]);
    assert.ok(robust.checked.includes("One test changed the data or the method (robustness tests): it says where the finding holds, and does not count for or against it."));
    assert.equal(robust.checkedBy, "No replication test yet");
    assert.equal(robust.shows, null);
    const unclear = checkStory({ ...BASE, checks: [{ ...confirmed("Gnat"), disowned: true }, inconclusive("Moth")] });
    assert.deepEqual(unclear.lede, ["One check has been filed, and it was inconclusive."]);
    assert.doesNotMatch(JSON.stringify(unclear), /Gnat/, "a disowned check is not told");
    assert.deepEqual(unclear.checked.slice(1), ["One check was inconclusive."], "and never that no check has been filed");
    assert.equal(unclear.checkedBy, "1 agent, inconclusive");
    assert.equal(checkStory({ ...BASE, checks: [confirmed("Imago"), inconclusive("Moth")] }).checkedBy, "2 agents: 1 confirms, 1 inconclusive");
    assert.ok(checkStory({ ...BASE, checks: [confirmed("Imago"), inconclusive("Moth")] }).checked.includes("One more check was inconclusive."));
    const stopped = checkStory({ ...BASE, blockers: [{ blocker: "compute", meaning: "it needs more compute than the agents who tried have" }] });
    assert.deepEqual(stopped.lede, ["Nobody has checked this claim on Ecdysis yet.", "An attempt to check it stopped: it needs more compute than the agents who tried have."]);
    assert.match(stopped.next, /^clearing what stopped the last attempt \(it needs more compute than the agents who tried have\), then a verification/);
    const held = checkStory({ ...BASE, declared: [{ label: "data not available", meaning: "the data are not published" }] });
    assert.equal(held.lede[1], "Part of its test has not been run: data not available, as its registrant declared.");
  });

  it("names every check that cannot settle the claim as one, tells what it found as its own, and never lets it settle the claim", () => {
    const own = checkStory({ ...BASE, status: "supported", credence: 0.66, checks: [confirmed("Moth", "reproduction", "own")] });
    assert.deepEqual(own.lede, [
      "Moth (an agent of the registrant's operator) repeated the authors' method on new data from the same population and period and got the paper's result.",
      "That check cannot settle the claim: a check by the operator that registered a claim counts towards its credence, but never towards the two verified operators that settle it.",
    ]);
    assert.equal(own.showsTone, "uncounted");
    assert.deepEqual(own.shows, ["It found that the finding held when the authors' method was repeated on new data from the same population and period."], "what the check found is told as its own, never as what the record shows");
    assert.equal(own.notYet![0], "That a check that can settle it, by a verified operator other than the registrant's, gets the same result.");
    assert.equal(own.next, "a reproduction by a verified operator other than the registrant's, ideally working with a different family of AI model: confirming replication tests from two verified operators, run with two families of model, can establish a claim.", "a first operator, not a second: the record counts none yet");
    const verified = checkStory({ ...BASE, checks: [confirmed("Moth", "verification", "own")] });
    assert.deepEqual(verified.shows, ["It found that the published numbers are what the authors' own data and analysis produce."], "and draws no conclusion from it");
    const pair = checkStory({ ...BASE, status: "supported", operators: { confirming: 1, failing: 0 }, checks: [confirmed("Imago"), confirmed("Moth", "verification", "own")] });
    assert.equal(pair.checked[1], "Imago and Moth (an agent of the registrant's operator) each re-ran the authors' analysis on the paper's own data, and both got the paper's results.");
    assert.equal(pair.lede.length, 1, "a check that can settle it is there: no caveat in the lede");
    assert.equal(pair.showsTone, "show");
    const crowd = checkStory({ ...BASE, checks: [failed("Gnat", "verification", "unverified")] });
    assert.deepEqual(crowd.lede, ["Gnat (whose operator is not yet verified) re-ran the authors' analysis on the paper's own data and did not get the paper's result.", "That check cannot settle the claim: a check by an operator not yet verified is shown, but never settles a claim."]);
    assert.equal(crowd.next, "a replication test by a verified operator other than the registrant's: the checks so far cannot settle it.");
    assert.deepEqual(crowd.shows, ["It found that the published results could not be obtained from the authors' own data and analysis."]);
    const held = checkStory({ ...BASE, checks: [confirmed("Kite", "verification", "unaudited"), confirmed("Wren", "verification", "ignored")] });
    assert.equal(held.lede[1], "None of those checks can settle the claim: a check on data held privately counts as an unverified operator's until a verified operator re-runs it. A receipt whose outputs ignored the archive's seed adds nothing.");
    assert.match(held.checked[1]!, /^Kite \(on data held privately, not yet re-run by a verified operator\) and Wren \(whose outputs ignored the archive's seed\) each re-ran/);
    // A disagreement among checks that cannot settle it: told as one, and what is missing has a referent.
    const muddle = checkStory({ ...BASE, checks: [confirmed("Moth", "verification", "own"), failed("Gnat", "verification", "unverified")] });
    assert.equal(muddle.showsTone, "mixed");
    assert.equal(muddle.notYet![0], "What a verified operator other than the registrant's would find: none of the checks so far can settle it.");
    const author = checkStory({ ...BASE, external: false, checks: [confirmed("Imago"), failed("Ant", "verification", "own")], operators: { confirming: 1, failing: 0 } });
    assert.deepEqual(author.lede, ["The verifications disagree: Imago got the claimed result, and Ant (an agent of its author's operator) did not."]);
    assert.match(checkStory({ ...BASE, external: false, checks: [confirmed("Ant", "verification", "own")] }).lede[1]!, /^That check cannot settle the claim: a check by a claim's own author's operator carries no weight: only others' checks count\.$/);
  });

  it("speaks of a claim published here as its author's, never a paper's, and of a conceptual claim's arguments", () => {
    const here = checkStory({ ...BASE, external: false, status: "supported", checks: [confirmed("Imago")], by: { handle: "Moth", at: "2026-10-05T09:00:00Z" } });
    assert.deepEqual(here.lede, ["Imago re-ran its author's analysis on the claim's own data and got the claimed result."]);
    assert.equal(here.checked[0], "Moth published it on 5 October 2026.");
    assert.deepEqual(here.shows, ["The reported numbers are what its author's own data and analysis produce: the analysis was reported correctly."]);
    assert.doesNotMatch(JSON.stringify([here, checkStory({ ...BASE, external: false }), checkStory({ ...BASE, external: false, checks: [failed("Imago")] }), checkStory({ ...BASE, external: false, checks: [failed("Imago", "verification", "own")] })]), /paper|the authors'|registrant/i);
    const c = checkStory({ ...BASE, kind: "conceptual" });
    assert.match(c.lede[0]!, /^No argument about this claim has been settled yet\. It is a conceptual claim, so it is tested by argument/);
    assert.equal(c.checkedBy, "No arguments yet");
    assert.match(c.next, /^an argument: a counterexample, a contradiction with a claim on the record/);
    const dismissed = checkStory({ ...BASE, kind: "conceptual", arguments: { upheld: 0, dismissed: 2, open: 1 } });
    assert.deepEqual(dismissed.lede, ["Two attacks on it were dismissed by independent checkers, and none upheld."]);
    assert.deepEqual([dismissed.showsTone, dismissed.shows], ["show", ["The arguments filed against it so far have not held up: two dismissed by independent checkers."]]);
    const upheld = checkStory({ ...BASE, kind: "conceptual", arguments: { upheld: 1, dismissed: 0, open: 0 } });
    assert.deepEqual(upheld.lede, ["One argument against it was upheld by independent checkers."]);
    assert.deepEqual([upheld.showsTone, upheld.shows], ["fail", ["One argument against it was upheld by independent checkers."]]);
    const mixed = checkStory({ ...BASE, kind: "conceptual", arguments: { upheld: 1, dismissed: 2, open: 0 } });
    assert.deepEqual(mixed.lede, ["Two attacks on it were dismissed by independent checkers, and one was upheld."]);
    assert.equal(mixed.showsTone, "mixed");
    assert.doesNotMatch(JSON.stringify(mixed), /not held up/, "never 'not held up' when one has");
  });

  it("never calls the agents that checked an empirical claim independent: the archive counts operators and cannot see their ties", () => {
    const stories = [BASE, { ...BASE, checks: [confirmed("A")] }, { ...BASE, checks: [confirmed("A"), confirmed("B", "reproduction")] }, { ...BASE, checks: [failed("A")] }, { ...BASE, checks: [confirmed("A"), failed("B")] }, { ...BASE, checks: [confirmed("A", "verification", "own")] }].map(checkStory);
    for (const s of stories) assert.doesNotMatch(JSON.stringify(s), /independent/i);
  });
});

describe("names, fields, the meter and the longer post", () => {
  it("names a paper's authors as lists do, each once, with their particles", () => {
    assert.equal(surnames(["Gordon Pennycook", "Ziv Epstein"]), "Pennycook and Epstein");
    assert.equal(surnames(["Ludwig van Beethoven", "Gordon Pennycook", "Ziv Epstein"]), "van Beethoven, Pennycook and Epstein");
    assert.equal(surnames(["Gordon Pennycook", "Gordon Pennycook", "Ziv Epstein"]), "Pennycook and Epstein", "an index that lists one person twice");
    assert.equal(surnames(["A One", "B Two", "C Three", "D Four", "E Five", "F Six", "G Seven"]), "One, Two, Three et al.");
    assert.equal(surnames(["A One"], 12), "One et al.", "the count the index gives, when it lists fewer");
    assert.equal(surnames([]), "");
  });

  it("folds the fields two indexes spell differently into one place to browse", () => {
    assert.equal(fieldName("Physics"), "Physics and Astronomy");
    assert.equal(fieldName("Physics and Astronomy"), "Physics and Astronomy");
    assert.equal(fieldName(" Computer Science "), "Computer Science");
    assert.equal(fieldName("Biology"), "Biochemistry, Genetics and Molecular Biology");
    assert.equal(fieldName(""), null);
    assert.equal(fieldName(null), null);
  });

  it("draws the meter from the status thresholds, marks where credence started only when it moved, and says it all in words", () => {
    const still = credenceMeter({ credence: 0.55, prior: 0.55, bar: 0.9 });
    assert.doesNotMatch(still, /cm-ring/);
    assert.match(still, /aria-label="Credence 55%\. Refuted, below 35%; Unsettled; Supported, from 60%; Established, from 90%\."/);
    const widths = [...still.matchAll(/style="width:([\d.]+)%"/g)].map((m) => Number(m[1]));
    assert.equal(widths.length, 4);
    assert.ok(Math.abs(widths.reduce((a, b) => a + b, 0) - 100) < 0.2, "the bands fill the track");
    const moved = credenceMeter({ credence: 0.78, prior: 0.55, bar: 0.95 });
    assert.match(moved, /<i class="cm-ring" style="left:55\.0%" title="Where it started: 55%"><\/i><i class="cm-now" style="left:78\.0%"/);
    assert.match(moved, /Credence 78%, from 55% where it started\./);
    assert.match(moved, /Established, from 95%/, "the bar for established is the claim's own, which rises with its use");
    assert.equal([...credenceMeter({ credence: 0.5, prior: 0.5, bar: 0.9, conceptual: true }).matchAll(/class="s-/g)].length, 3, "a conceptual claim is never established");
    assert.match(credenceMeter({ credence: 1.4, prior: -2, bar: 0.9 }), /left:100\.0%/, "drawn inside the track whatever it is given");
  });

  it("writes the longer post from the record: the paper's words first, the machine's headline marked, what is checked and what is not, and never more", () => {
    const paper: PaperRecord = { provider: "openalex", work: "W1", title: "Shifting attention to accuracy", authors: ["Gordon Pennycook", "Ziv Epstein"], authorCount: 6, venue: "Nature", year: 2021, type: "article", citedBy: 1126, keywords: [], topic: null, readAt: "2026-10-09T08:00:00Z" };
    const url = "https://ecdysis.me/c/ext:0123456789abcdef";
    const unchecked = longPost({ url, headline: "Prompting people to think about accuracy improves what they share.", quote: "subtly shifting attention to accuracy increases the quality of news", paper, source: "doi:10.1/x", status: "unchecked", credence: 0.55, story: checkStory(BASE), external: true });
    assert.deepEqual(unchecked.split("\n\n").slice(0, 3), [
      "\"subtly shifting attention to accuracy increases the quality of news\"\n(Pennycook et al., Nature, 2021)",
      "In plain words (machine-written from the paper's abstract): Prompting people to think about accuracy improves what they share.",
      "On Ecdysis, an open record where AI agents check published research, it is unchecked (credence 55%). Nobody has checked this claim on Ecdysis yet.",
    ], "the authors are credited with their own words, never with a machine's paraphrase");
    assert.match(unchecked, /The most useful next check: a verification/);
    assert.match(longPost({ url, headline: "A headline.", quote: "q", paper, source: "doi:10.1/x", status: "unchecked", credence: 0.55, story: checkStory(BASE), external: true, headlineFrom: "title" }), /In plain words \(machine-written from the quote and the paper's title\): A headline\./, "and says what the machine wrote it from");
    assert.ok(unchecked.endsWith(url));
    const checked = longPost({ url, headline: null, quote: "subtly shifting attention", paper: null, source: "doi:10.1/x", status: "supported", credence: 0.72, story: checkStory({ ...BASE, status: "supported", checks: [confirmed("Imago")] }), external: true });
    assert.match(checked, /^"subtly shifting attention"\n\(doi:10\.1\/x\)\n\nOn Ecdysis/, "with no headline, the paper's words alone");
    assert.match(checked, /it is supported \(credence 72%\)\. Imago re-ran the authors' analysis/);
    assert.match(checked, /What the checks show: the published numbers are what the authors' own data and analysis produce: the analysis was reported correctly\. Not yet shown: that the finding holds with new data/);
    const here = longPost({ url, headline: null, quote: "Grokking appears after weight decay.", paper: null, source: null, status: "unchecked", credence: 0.7, story: checkStory({ ...BASE, external: false }), external: false, author: "Moth" });
    assert.match(here, /^"Grokking appears after weight decay\."\n\(published on Ecdysis by Moth\)/);
    for (const post of [unchecked, checked, here]) assert.doesNotMatch(post, /\bprov(?:e|en|ed)\b|confirmed beyond|independent|debunk/i);
  });
});

/** A record with papers, a claim published here, checks, the scout's findings and the context writer's work. */
async function world() {
  const clock = { t: Date.UTC(2026, 9, 9, 8, 0, 0) };
  const now = () => new Date(clock.t);
  const logStore = new MemoryStore();
  const log = new TransparencyLog(logStore, now);
  const logKey = await generateKeyPair();
  const rows = () => (logStore as unknown as { log: Array<{ entry: { seq: number; ts: string; type: string }; payload: Json }> }).log.map((r) => ({ seq: r.entry.seq, ts: r.entry.ts, type: r.entry.type, payload: r.payload }));
  const context = new MemoryContextStore();
  const svc = new V2Service({ log, store: new MemoryV2Store(rows), logPrivateKey: logKey.privateKey, now, context });
  const quotes = new MemoryQuoteCheckStore();
  const pages = new PagesHandler(svc, { host: "api.ecdysis.me", logPublicKey: logKey.publicKey, quotes, context });
  const keys = new Map<string, KeyPairB64>();
  const ts = () => now().toISOString().replace(/\.\d{3}Z$/, "Z");
  const agent = async (handle: string, op: string, models: string[]) => {
    const kp = await generateKeyPair();
    keys.set(handle, kp);
    assert.equal((await svc.registerAgent({ constitution: ACK, handle, publicKey: kp.publicKey, operatorId: op, models })).status, 201);
    await svc.setTier(op, "verified");
    return kp;
  };
  const sign = async (handle: string, payload: Record<string, Json>) => {
    const kp = keys.get(handle)!;
    const full: Json = declared({ ...payload, agent: { handle, publicKey: kp.publicKey }, ts: ts() });
    return { payload: full, signature: await signJson(kp.privateKey, full) } as Json;
  };
  const register = async (handle: string, source: string, quote: string, check: QuoteStatus = "verified") => {
    clock.t += 60_000;
    const r = await svc.registerExternalClaim(await sign(handle, { protocol: "ecdysis/0.2", type: "claim.external", source, quote, test: "Refuted if the stated effect is absent when the study is run again as the paper describes it." }));
    assert.equal(r.status, 201, `${source}: ${JSON.stringify(r.body)}`);
    const id = String((r.body as Record<string, Json>)["ref"]);
    await quotes.put({ claim: id, status: check, where: check === "verified" ? "crossref-abstract" : null, nearest: null, similarity: check === "verified" ? 1 : null, checkedAt: now().toISOString(), attempts: 1, detail: null });
    return id;
  };
  const bundle = (n: number): Bundle => ({ repo: "https://github.com/example/rep", commit: n.toString(16).padStart(40, "0"), image: "sha256:" + "a".repeat(64), run: "python run.py", outputs: [{ name: "alpha", tolerance: 0.01 }], runtimeMinutes: 5 });
  let bundles = 0;
  /** Each receipt's outputs, so a later check assigned it as a cross-check re-runs it and reports the same (no dispute). */
  const outputsOf = new Map<string, Record<string, number>>();
  const check = async (handle: string, target: string, outcome: "confirmed" | "failed") => {
    clock.t += 60_000;
    const c = await svc.commitCheck(await sign(handle, { protocol: "ecdysis/0.2", type: "check.commit", target, kind: "replication", bundle: bundle(++bundles) as unknown as Json }));
    assert.equal(c.status, 201, JSON.stringify(c.body));
    const id = String((c.body as Record<string, Json>)["id"]);
    const cross = ((c.body as Record<string, Json>)["crossCheck"] as { receipt?: string } | null)?.receipt ?? null;
    clock.t += 60_000;
    const outputs = { alpha: outcome === "confirmed" ? 1 : 0 };
    const r = await svc.fileResult(await sign(handle, { protocol: "ecdysis/0.2", type: "check.result", commit: id, outcome, outputs, crossCheck: cross ? { receipt: cross, outputs: outputsOf.get(cross)! } : null }));
    assert.equal(r.status, 201, JSON.stringify(r.body));
    outputsOf.set(id, outputs);
  };
  const paper = (source: string, over: Partial<PaperRecord>) => context.putSource({
    source: source.toLowerCase(), status: "read", readAt: now().toISOString(), attempts: 1, detail: null,
    record: { provider: "openalex", work: "W1", title: "A paper", authors: ["Gordon Pennycook", "Ziv Epstein"], authorCount: 2, venue: "Nature", year: 2021, type: "article", citedBy: 10, keywords: [], topic: null, readAt: now().toISOString(), ...over },
  });
  const explain = (claim: string, headline: string, gist: string | null = null) => context.putClaim({
    claim, status: "written", version: CONTEXT_VERSION, model: "claude-sonnet-5-5", inputsHash: "a".repeat(64), writtenAt: now().toISOString(), attempts: 1, detail: null,
    explanation: { headline, did: null, gist, meaning: "What the sentence means, in plain words, for a reader who is not a specialist in the field.", findings: [], terms: [], basis: "abstract", abstractFrom: "crossref", model: "claude-sonnet-5-5", writtenAt: now().toISOString(), version: CONTEXT_VERSION },
  });
  const get = async (path: string) => { const r = await pages.handle("GET", path.split("?")[0]!, "text/html", false, path.includes("?") ? `?${path.split("?")[1]}` : ""); assert.ok(r, path); return { status: r!.status, html: await r!.text() }; };
  return { svc, log, context, quotes, pages, agent, sign, register, check, paper, explain, get, now, tick: (ms: number) => { clock.t += ms; }, keys };
}

/** The papers on the list, in order, by their titles. */
const titles = (html: string) => [...html.matchAll(/<li class="work" id="[^"]*"><div class="row"><div>\s*(?:<p class="path">[^<]*<\/p>\s*)?<h3 class="title">(?:<a [^>]*>)?([^<]*)/g)].map((m) => m[1]!);

describe("the claims for people, under their papers", () => {
  async function seeded() {
    const w = await world();
    await w.agent("Ant", "op-a", ["claude"]);
    await w.agent("Bee", "op-b", ["gpt"]);
    const misinfo = { topic: "Misinformation and Its Impacts", subfield: "Sociology and Political Science", field: "Social Sciences", domain: "Social Sciences" };
    const a1 = await w.register("Ant", "doi:10.1000/p1", "subtly shifting attention to accuracy increases the quality of news that people subsequently share");
    const a2 = await w.register("Ant", "doi:10.1000/p1", "the veracity of headlines had little effect on sharing intentions");
    await w.paper("doi:10.1000/p1", { title: "Shifting attention to accuracy can reduce misinformation online", keywords: ["misinformation", "Twitter"], topic: misinfo, citedBy: 1126 });
    await w.explain(a1, "Prompting people to think about accuracy improves the news they share.", "People share false news because their attention is elsewhere, not because they believe it.");
    const b = await w.register("Bee", "doi:10.1000/p2", "the halo's mass profile is consistent with cold dark matter at the 2 sigma level");
    await w.paper("doi:10.1000/p2", { title: "A dark matter halo, weighed", authors: ["Vera Rubin"], authorCount: 1, venue: "ApJ", year: 1980, keywords: ["dark matter"], topic: { topic: "Galaxies: Formation, Evolution, Phenomena", subfield: "Astronomy and Astrophysics", field: "Physics and Astronomy", domain: "Physical Sciences" } });
    const c = await w.register("Bee", "arxiv:2001.00001", "the measured lensing signal exceeds the baryonic prediction by a factor of five");
    // Semantic Scholar's word for the field of a paper OpenAlex has not read: the same place to browse.
    await w.log.append("source.observed", { source: "arxiv:2001.00001", provider: "semanticscholar", work: "abc", citedBy: 3, year: 2020, field: "Physics" });
    const wrong = await w.register("Ant", "doi:10.1000/p4", "a sentence the scout found in a different paper altogether", "wrong-work");
    const ant = w.keys.get("Ant")!;
    const native = await signedClaim({ handle: "Ant", ...ant }, { text: "Grokking appears in modular addition after weight decay, within 10^5 steps of convergence.", field: "ml", ts: w.now().toISOString().replace(/\.\d{3}Z$/, "Z") });
    assert.equal((await w.svc.publishClaim(native.envelope)).status, 201);
    await w.check("Bee", a1, "confirmed");
    await w.check("Ant", b, "failed");
    return { w, a1, a2, b, c, wrong, native: native.id };
  }

  it("groups the claims under their papers, says where the record stands, what was checked last and where to browse", async () => {
    const { w, a1, a2, b, wrong, native } = await seeded();
    const scores = (await w.svc.scores()).claims;
    const page = await w.get("/claims");
    assert.equal(page.status, 200);
    assert.doesNotMatch(page.html, /<script/);
    assert.match(page.html, /<h1>Findings from published research, checked in the open<\/h1>\s*<p class="lede">Each claim is a single finding: most are taken word for word from a published paper, and some are published here by AI agents\./);
    assert.match(page.html, /<p class="standing-line"><b>6 claims<\/b> are on the record: <b>5<\/b> from <b>4 papers<\/b>, and <b>1<\/b> published here by agents\. <b>2<\/b> have been checked so far; the other 4 have no check with a result yet\.<\/p>/);
    // The status tiles count the claims, and each filters the list to its status.
    const supported = [...scores.values()].filter((x) => x.status === "supported").length;
    assert.match(page.html, new RegExp(`<a class="stat t-[a-z]+" href="/claims\\?status=supported"><span class="stat-v">${supported}</span><span class="stat-l">Supported</span>`));
    // Recently checked: the claims with results, newest first, each with the story's first line.
    const recent = page.html.slice(page.html.indexOf('<div class="checked">'), page.html.indexOf('<h2 id="topics">'));
    assert.ok(recent.indexOf(`/c/${b}"`) < recent.indexOf(`/c/${a1}"`) && recent.indexOf(`/c/${a1}"`) > 0, "the latest result first");
    assert.match(recent, /Bee repeated the authors&#39; method on new data from the same population and period and got the paper&#39;s result\./);
    assert.match(recent, /Prompting people to think about accuracy improves the news they share\./, "the headline where one is written");
    // Topics: the fields on the record, Physics and Physics and Astronomy as one.
    const tiles = page.html.slice(page.html.indexOf('<div class="tiles">'), page.html.indexOf("</div>", page.html.indexOf('<div class="tiles">')));
    assert.match(tiles, /<a class="tile" href="\/claims\?field=Physics%20and%20Astronomy"><b>Physics and Astronomy<\/b><span>Astronomy and Astrophysics<\/span><span class="n">2 claims · 1 checked<\/span><\/a>/);
    assert.match(tiles, /<a class="tile" href="\/claims\?field=Social%20Sciences"><b>Social Sciences<\/b><span>Sociology and Political Science<\/span><span class="n">2 claims · 1 checked<\/span><\/a>/);
    assert.doesNotMatch(tiles, /<b>Physics<\/b>/);
    // The papers: one card per paper, its claims inside, in the paper's words beneath a plain headline.
    const order = titles(page.html);
    assert.equal(order.length, 5, "four papers and the claim published here");
    assert.equal(order.at(-1), "DOI 10.1000/p4", "a paper whose every quote the scout could not match is listed last");
    assert.match(page.html, /<h3 class="title">Shifting attention to accuracy can reduce misinformation online<\/h3>\s*<p class="who">Pennycook and Epstein · <cite>Nature<\/cite> · 2021<\/p>\s*<p class="gist">People share false news because their attention is elsewhere, not because they believe it\.<\/p>/);
    assert.match(page.html, /Headlines in plain words, and the lines on papers, are machine-written from each paper&#39;s abstract|Headlines in plain words, and the lines on papers, are machine-written from each paper's abstract/, "the list says which of its words a machine wrote");
    assert.match(page.html, /<summary>Show 2 claims<\/summary>/);
    assert.match(page.html, new RegExp(`<span class="plain"><a href="/c/${a1}">Prompting people to think about accuracy improves the news they share\\.</a></span><span class="q">“subtly shifting attention to accuracy`));
    assert.match(page.html, new RegExp(`<span class="plain"><a href="/c/${a2}">“the veracity of headlines had little effect on sharing intentions”</a></span>`), "with no headline yet, the paper's words, quoted");
    assert.match(page.html, /<span class="flag">The cited source names a different paper; the stewards have been told\.<\/span>/);
    assert.match(page.html, new RegExp(`<a href="/c/${wrong}">`));
    assert.match(page.html, /<p class="who">Published on Ecdysis by <a href="\/a\/Ant">Ant<\/a><\/p>/);
    assert.match(page.html, new RegExp(`<a href="/c/${native}">Grokking appears in modular addition`));
    // For checkers and agents: the full table and the network.
    assert.match(page.html, /<a class="btn" href="\/claims\/table">The full table<\/a><a class="btn quiet" href="\/network">The network<\/a>/);
  });

  it("filters by status, field, subfield, topic and keyword, searches papers and authors, and shows only checked papers or the rest", async () => {
    const { w, a1, b, c } = await seeded();
    const has = (html: string, id: string) => html.includes(`/c/${id}"`);
    const physics = (await w.get("/claims?field=Physics%20and%20Astronomy")).html;
    assert.deepEqual(titles(physics).sort(), ["A dark matter halo, weighed", "arXiv 2001.00001"]);
    assert.match(physics, /<a class="pill" href="\/claims" aria-label="Remove Field: Physics and Astronomy">Field: Physics and Astronomy <span class="x" aria-hidden="true">×<\/span><\/a>/);
    assert.match(physics, /<p class="count" role="status">2 claims from 2 papers<\/p>/);
    assert.match((await w.get("/claims?q=grokking")).html, /<p class="count" role="status">1 claim published here<\/p>/, "a claim published here is not counted as a paper");
    assert.doesNotMatch(physics, /<h2 id="topics">|<h2 id="checked">/, "a filtered list is the list alone");
    assert.deepEqual(titles((await w.get("/claims?subfield=Astronomy%20and%20Astrophysics")).html), ["A dark matter halo, weighed"]);
    assert.deepEqual(titles((await w.get("/claims?topic=Misinformation%20and%20Its%20Impacts")).html), ["Shifting attention to accuracy can reduce misinformation online"]);
    assert.deepEqual(titles((await w.get("/claims?keyword=TWITTER")).html), ["Shifting attention to accuracy can reduce misinformation online"], "keywords match whatever their case");
    assert.deepEqual(titles((await w.get("/claims?q=rubin")).html), ["A dark matter halo, weighed"], "the search reads the paper's authors");
    assert.deepEqual(titles((await w.get("/claims?q=lensing%20baryonic")).html), ["arXiv 2001.00001"], "every word, in the claim's own words");
    const status = (await w.svc.scores()).claims.get(a1)!.status;
    const byStatus = (await w.get(`/claims?status=${status}`)).html;
    assert.ok(has(byStatus, a1) && !has(byStatus, c), "a status filters claim by claim");
    const checked = (await w.get("/claims?show=checked")).html;
    assert.ok(has(checked, a1) && has(checked, b) && !has(checked, c));
    const rest = (await w.get("/claims?show=unchecked")).html;
    assert.ok(!has(rest, a1) && has(rest, c));
    // What the list does not offer is no filter: an unknown field, a status of another vocabulary, a hostile word.
    const hostile = (await w.get(`/claims?field=Astrology&status=${encodeURIComponent('" onmouseover="x')}&sort=%3Cb%3E&show=all&keyword=nothing&page=-4&q=${encodeURIComponent("<script>alert(1)</script>")}`)).html;
    assert.doesNotMatch(hostile, /<script>alert|onmouseover="x/);
    assert.match(hostile, /<option value="relied" selected>Most relied on<\/option>/, "an unknown sort is the default");
    assert.doesNotMatch(hostile, /Field: Astrology|Keyword: nothing|Status: /);
    assert.match(hostile, /value="&lt;script&gt;alert\(1\)&lt;\/script&gt;"/);
    assert.match(hostile, /No claims match\. Remove a filter or search for something else\./);
  });

  it("sorts by what is most relied on, most recently checked, newest and most contested, and pages by twenty papers with canonical addresses", () => {
    const claim = (i: number, over: Partial<PeopleClaimV2> = {}): PeopleClaimV2 => ({
      id: `ext:${i.toString(16).padStart(16, "0")}`, text: `Claim ${i} in the paper's words.`, headline: null, external: true, kind: "empirical", status: "unchecked", credence: 0.55, stakes: i % 7,
      seq: i, checkedAt: null, source: `doi:10.1000/${i}`, agent: "Ant", paper: `doi:10.1000/${i}`, field: "Computer Science", subfield: null, topic: null, keywords: [], flag: null, ...over,
    });
    const claims = Array.from({ length: 45 }, (_, i) => claim(i + 1, i === 44 ? { status: "contested", checkedAt: "2026-10-01T00:00:00Z" } : i === 3 ? { status: "supported", checkedAt: "2026-10-08T00:00:00Z" } : {}));
    const page = (qs: string) => claimsListPageV2({ claims, papers: new Map(), recent: [], unlisted: 0, params: new URLSearchParams(qs) });
    const order = (qs: string) => titles(page(qs)).map((t) => Number(t.replace("DOI 10.1000/", "")));
    const relied = order("");
    assert.equal(relied.length, 20, "twenty papers a page");
    assert.deepEqual(relied.slice(0, 3), [41, 34, 27], "the most relied on first, the newest of equals first");
    assert.deepEqual(order("sort=checked").slice(0, 2), [4, 45], "the most recently checked first");
    assert.deepEqual(order("sort=newest").slice(0, 3), [45, 44, 43]);
    assert.equal(order("sort=contested")[0], 45);
    const p1 = page("");
    assert.match(p1, /<nav class="pager" aria-label="Pages of the list"><span>Page 1 of 3<\/span><a href="\/claims\?page=2" rel="next">Next page<\/a><\/nav>/);
    assert.match(page("sort=newest&page=3"), /<a href="\/claims\?sort=newest&amp;page=2" rel="prev">Previous page<\/a><span>Page 3 of 3<\/span><\/nav>/);
    assert.equal(order("page=99").length, 5, "past the end is the last page");
    assert.deepEqual(peopleQuery(new URLSearchParams("sort=nonsense&show=nonsense&page=abc"), claims), { q: "", status: null, field: null, subfield: null, topic: null, keyword: null, show: "all", sort: "relied", page: 1 });
    assert.match(p1, /<form class="sorts" method="get" action="\/claims" aria-label="Sort and show the papers"><label>Sort by <select name="sort"><option value="relied" selected>Most relied on<\/option><option value="checked">Recently checked<\/option><option value="newest">Newest<\/option><option value="contested">Contested first<\/option><\/select><\/label><label>Show <select name="show"><option value="all" selected>All claims<\/option><option value="checked">Checked claims<\/option><option value="unchecked">Claims with no check yet<\/option><\/select><\/label>/);
    assert.match(page("show=checked"), /<p class="count" role="status">2 claims from 2 papers<\/p>/, "a claim is checked once a check of it has a result");
  });

  it("escapes what an index or an agent wrote, wherever the list or the claim page shows it", async () => {
    const w = await world();
    await w.agent("Ant", "op-a", ["claude"]);
    const id = await w.register("Ant", "doi:10.1000/evil", "a perfectly ordinary sentence quoted from the paper's abstract");
    const evil = `<img src=x onerror=alert(1)>"'`;
    await w.paper("doi:10.1000/evil", { title: `Title ${evil}`, authors: [`Mallory ${evil}`], venue: `Venue ${evil}`, keywords: [`kw ${evil}`], topic: { topic: `Topic ${evil}`, subfield: `Sub ${evil}`, field: `Field ${evil}`, domain: "x" } });
    for (const html of [(await w.get("/claims")).html, (await w.get(`/c/${id}`)).html]) {
      assert.doesNotMatch(html, /<img src=x/, "no markup from the index is ever live");
      assert.match(html, /Title &lt;img src=x onerror=alert\(1\)&gt;&quot;&#39;/);
    }
    const claimPage = (await w.get(`/c/${id}`)).html;
    assert.match(claimPage, /<a class="chip" href="\/claims\?keyword=kw%20%3Cimg%20src%3Dx%20onerror%3Dalert\(1\)%3E%22&#39;">kw &lt;img src=x onerror=alert\(1\)&gt;&quot;&#39;<\/a>/, "a keyword's link is encoded and its words escaped");
    assert.match(claimPage, /<a href="\/claims\?topic=Topic%20%3Cimg/);
    // The front page shows the same claim (the only one) beside its headline, and the field among its tiles.
    const home = (await w.get("/")).html;
    assert.ok(home.includes(`/c/${id}"`));
    assert.doesNotMatch(home, /<img src=x/, "nor on the front page");
    assert.match(home, /<cite>Venue &lt;img src=x onerror=alert\(1\)&gt;&quot;&#39;<\/cite>/);
    assert.match(home, /<span>Topic &lt;img src=x onerror=alert\(1\)&gt;&quot;&#39;<\/span>/);
    assert.match(home, /<a class="tile" href="\/claims\?field=Field%20%3Cimg%20src%3Dx%20onerror%3Dalert%281%29%3E%22%27"><b>Field &lt;img src=x onerror=alert\(1\)&gt;&quot;&#39;<\/b><span>Sub &lt;img src=x onerror=alert\(1\)&gt;&quot;&#39;<\/span><\/a>/, "a tile's link is encoded and its words escaped");
  });

  it("sends an address made for the table on to the table, with its filters, instead of dropping them", async () => {
    const { w } = await seeded();
    for (const qs of ["?stage=attempted&q=x", "?origin=here", "?kind=empirical", "?sort=stakes&order=asc", "?sort=credence", "?field=ml"]) {
      const r = await w.pages.handle("GET", "/claims", "text/html", false, qs);
      assert.equal(r!.status, 302, qs);
      assert.equal(r!.headers.get("location"), `/claims/table${qs}`, qs);
    }
    for (const qs of ["?q=x&status=supported&field=Social%20Sciences", "?sort=newest", "?sort=relied&show=checked&page=2"]) assert.equal((await w.pages.handle("GET", "/claims", "text/html", false, qs))!.status, 200, `${qs} is the list's own`);
  });

  it("tells on the claim page how far the record is from settling the claim, and when its credence sits in a band its status has not reached", async () => {
    const { w, a1, c } = await seeded();
    const checked = (await w.get(`/c/${a1}`)).html;
    const ops = (await w.svc.scores()).claims.get(a1)!.operators;
    assert.equal(ops.confirming, 1, "Bee's verified reproduction counts");
    assert.match(checked, /<dt>Verified operators, not the registrant&#39;s<\/dt><dd>1 confirming: two, with two families of model, can establish it<\/dd>/);
    assert.match(checked, /<dt>Checked by<\/dt><dd>1 agent, confirming<\/dd>/);
    const none = (await w.get(`/c/${c}`)).html;
    assert.match(none, /<dt>Verified operators, not the registrant&#39;s<\/dt><dd>None yet: two agreeing can settle it<\/dd>/);
    assert.match(none, /<span class="status big open" title="[^"]*">Unchecked<\/span>/, "the protocol's word for the status");
    assert.match(none, /credence alone never sets one: supported also needs a confirming replication test by a verified operator/);
    // A claim published here at high confidence starts high, in a band its status has not reached: the key says so.
    const ant = w.keys.get("Ant")!;
    const sure = await signedClaim({ handle: "Ant", ...ant }, { text: "A claim its author is very sure of, published here with no check at all yet.", confidence: 0.95, field: "math", ts: w.now().toISOString().replace(/\.\d{3}Z$/, "Z") });
    assert.equal((await w.svc.publishClaim(sure.envelope)).status, 201);
    const sc = (await w.svc.scores()).claims.get(sure.id)!;
    const page = (await w.get(`/c/${sure.id}`)).html;
    if (sc.credence >= 0.6) assert.match(page, new RegExp(`Its credence is in the (supported|established) band; its status is ${sc.status}\\.`));
    assert.doesNotMatch(page, /besides its registrant|registrant&#39;s</, "a claim published here has no registrant");
    assert.match(page, /<dt>Verified operators, not its author&#39;s<\/dt><dd>None yet: two agreeing can settle it<\/dd>/);
  });

  it("labels every machine-written line on the claim page, and keeps the claim's own words in its title", async () => {
    const { w, a1 } = await seeded();
    await w.context.putClaim({ ...(await w.context.getClaim(a1))!, explanation: { ...(await w.context.getClaim(a1))!.explanation!, did: "The authors asked people to rate the accuracy of one headline before choosing what to share.", findings: ["Sharing improved after the prompt."] } });
    const html = (await w.get(`/c/${a1}`)).html;
    assert.match(html, /<title>“subtly shifting attention to accuracy increases the quality of news that…<\/title>/, "the title is the paper's words, never the machine's paraphrase");
    assert.match(html, /<meta name="description" content="A claim on Ecdysis, from Pennycook and Epstein \(2021\): “subtly shifting/);
    assert.match(html, /<h3>What the authors did<\/h3><p>The authors asked people to rate[^<]*<\/p><p class="from">Machine-written from the paper&#39;s abstract, as noted under <a href="#matters">Why it matters<\/a>\.<\/p>|<h3>What the authors did<\/h3><p>The authors asked people to rate[^<]*<\/p><p class="from">Machine-written from the paper's abstract, as noted under <a href="#matters">Why it matters<\/a>\.<\/p>/);
    assert.match(html, /<h3>What they found<\/h3><p>Sharing improved after the prompt\.<\/p><p class="from">Machine-written from the paper/);
    assert.match(html, /In plain words \(machine-written from the paper&#39;s abstract\): Prompting people/, "and the longer post marks the headline too");
  });

  it("gives the claim page the other claims from the same paper, with their plain headlines", async () => {
    const { w, a1, a2 } = await seeded();
    const html = (await w.get(`/c/${a2}`)).html;
    assert.match(html, /<h3>Other claims from the same paper<\/h3><ul class="lit"><li><span class="status [a-z]+"[^>]*>[^<]*<\/span><a class="t" href="\/c\/[^"]+">Prompting people to think about accuracy improves the news they share\.<\/a><span class="d">“subtly shifting attention/);
    assert.ok(html.includes(`href="/c/${a1}"`));
    assert.match(html, /<a href="\/claims\?field=Social%20Sciences">Social Sciences<\/a>/, "the breadcrumb opens the field on the list");
    assert.match(html, /Headlines are machine-written from the paper(&#39;|')s abstract, or from the quote and the paper(&#39;|')s title where no abstract is open; each claim(&#39;|')s own words are quoted beneath its headline\./);
    // An operator with no standing registers a quote from the same paper: it is not listed beside the others, as the lists leave it out.
    await w.agent("Nobody", "op-n", ["claude"]);
    await w.svc.setTier("op-n", "unverified");
    const junk = await w.register("Nobody", "doi:10.1000/p1", "a quote an operator with no standing registered from the same paper");
    assert.ok(!(await w.get(`/c/${a2}`)).html.includes(`href="/c/${junk}"`), "unchecked work from an operator with no standing is not shown beside the paper's other claims");
    assert.ok(!(await w.get("/claims")).html.includes(`/c/${junk}"`), "nor in the list");
  });
});

describe("the front page reads the same record (Lucy Griffiths' home page, 10 October 2026)", () => {
  it("counts the default list, shows the surest checked finding with its paper and its checks' story, and offers the record's fields", async () => {
    const w = await world();
    await w.agent("Ant", "op-a", ["claude"]);
    await w.agent("Bee", "op-b", ["gpt"]);
    const misinfo = { topic: "Misinformation and Its Impacts", subfield: "Sociology and Political Science", field: "Social Sciences", domain: "Social Sciences" };
    const a1 = await w.register("Ant", "doi:10.1000/p1", "subtly shifting attention to accuracy increases the quality of news that people subsequently share");
    const a2 = await w.register("Ant", "doi:10.1000/p1", "the veracity of headlines had little effect on sharing intentions");
    await w.paper("doi:10.1000/p1", { title: "Shifting attention to accuracy can reduce misinformation online", topic: misinfo });
    await w.explain(a1, "Prompting people to think about accuracy improves the news they share.");
    const b = await w.register("Bee", "doi:10.1000/p2", "the halo's mass profile is consistent with cold dark matter at the 2 sigma level");
    await w.paper("doi:10.1000/p2", { title: "A dark matter halo, weighed", authors: ["Vera Rubin"], authorCount: 1, venue: "ApJ", year: 1980, topic: { topic: "Galaxies", subfield: "Astronomy and Astrophysics", field: "Physics and Astronomy", domain: "Physical Sciences" } });
    await w.explain(b, "A galaxy's dark matter halo weighs what cold dark matter predicts.");
    const wrong = await w.register("Bee", "doi:10.1000/p4", "a sentence the scout found in a different paper altogether", "wrong-work");
    await w.paper("doi:10.1000/p4", { title: "Another paper", authorCount: 7, authors: ["Ada Lovelace", "Charles Babbage", "Mary Somerville"], topic: misinfo });
    await w.explain(wrong, "A headline for a quote the scout could not find in its paper.");

    // Before any check: the unchecked finding most relied on, said so, with no percentage; never the flagged one.
    let html = (await w.get("/")).html;
    let card = html.slice(html.indexOf('<aside class="find-card"'), html.indexOf("</aside>"));
    assert.ok(card.length > 0 && !card.includes(`/c/${wrong}"`), "a quote the scout could not match is never the finding shown");
    assert.match(card, /<span class="status [^"]*"[^>]*>[^<]*Unchecked<\/span>/);
    assert.doesNotMatch(card, /\d+%/, "an unchecked claim shows no percentage beside its status");
    assert.match(card, /<b>So far:<\/b> nobody has checked it on Ecdysis yet\./);
    assert.match(card, /<b>Still to come:<\/b> a verification: re-running the authors(&#39;|') analysis on their own data, where they have published it\.<\/li>/, "a short next step keeps the words that say what it is");

    await w.check("Bee", a1, "confirmed");
    await w.check("Ant", b, "failed");
    const scores = (await w.svc.scores()).claims;
    assert.equal(scores.get(a1)!.status, "supported");
    assert.notEqual(scores.get(b)!.status, "supported", "b's check failed");
    html = (await w.get("/")).html;
    assert.doesNotMatch(html, /<script/);
    // The record now, counted as the claims page counts it.
    assert.match(html, /<div class="fig-n"><span class="v">4<\/span><span class="l">findings on the record<\/span><\/div><div class="fig-n"><span class="v">2<\/span><span class="l">checked so far<\/span><\/div><div class="fig-n t-sound"><span class="v">1<\/span><span class="l">supported by their checks<\/span><\/div>/);
    assert.match(html, /<div class="fig-n t-risk"><span class="v">1<\/span><span class="l">contested<\/span><\/div>/, "b's one failed check makes it contested");
    assert.match(html, /2 checks have a result so far, from 2 agents\. Counted live from the public log/);
    // The finding: the supported one, never the one whose check failed.
    card = html.slice(html.indexOf('<aside class="find-card"'), html.indexOf("</aside>"));
    assert.match(card, new RegExp(`<p class="ft"><a href="/c/${a1}">Prompting people to think about accuracy improves the news they share\\.</a></p>`));
    assert.ok(!card.includes(`/c/${b}"`) && !card.includes(`/c/${a2}"`) && !card.includes(`/c/${wrong}"`));
    assert.match(card, />Supported · \d+%<\/span><span>Misinformation and Its Impacts<\/span>/);
    assert.match(card, /<p class="from">Pennycook and Epstein, <cite>Nature<\/cite>, 2021<\/p>/, "two authors by both names");
    assert.match(card, /<b>Registered<\/b> word for word from the paper, with the test that would prove it wrong/, "the scout found the quote in the paper");
    assert.match(card, /<b>Checked:<\/b> Bee repeated the authors(&#39;|') method on new data from the same population and period and got the paper(&#39;|')s result\./);
    assert.match(card, /<b>Still to come:<\/b> a reproduction by a second verified operator other than the registrant(&#39;|')s, ideally working with a different family of AI model\.<\/li>/, "what the record still needs, in its first clause");
    assert.match(card, /The headline is machine-written from the paper/);
    // The fields to enter by: busiest first, each with its commonest subfields, each opening the list at that field.
    const tiles = html.slice(html.indexOf('<h2 id="topics">'), html.indexOf('<section class="why-grid"'));
    assert.match(tiles, /<a class="tile" href="\/claims\?field=Social%20Sciences"><b>Social Sciences<\/b><span>Sociology and Political Science<\/span><\/a><a class="tile" href="\/claims\?field=Physics%20and%20Astronomy"><b>Physics and Astronomy<\/b><span>Astronomy and Astrophysics<\/span><\/a>/);
  });

  it("names an author as lists do: one by name, two by both names, three or more as the first and et al.", async () => {
    const w = await world();
    await w.agent("Ant", "op-a", ["claude"]);
    const id = await w.register("Ant", "doi:10.1000/p9", "a single quoted sentence from the paper's abstract, registered with its test");
    const from = async (authors: string[], authorCount: number) => {
      await w.paper("doi:10.1000/p9", { authors, authorCount, venue: "Science", year: 2015 });
      const html = (await w.get("/")).html;
      assert.ok(html.includes(`/c/${id}"`));
      return /<p class="from">([^]*?)<\/p>/.exec(html.slice(html.indexOf('<aside class="find-card"')))![1];
    };
    assert.equal(await from(["Brian Nosek"], 1), "Nosek, <cite>Science</cite>, 2015");
    assert.equal(await from(["Brian Nosek", "Jeffrey Spies"], 2), "Nosek and Spies, <cite>Science</cite>, 2015");
    assert.equal(await from(["Brian Nosek", "Jeffrey Spies"], 270), "Nosek et al., <cite>Science</cite>, 2015", "an index that lists only some of many authors");
  });

  it("never shows a disagreement, a failed check, a quote the scout did not find in its paper or a conceptual claim, whatever its status", async () => {
    const w = await world();
    await w.agent("Ant", "op-a", ["claude"]);
    await w.agent("Bee", "op-b", ["gpt"]);
    await w.agent("Cat", "op-c", ["gemini"]);
    await w.svc.setTier("op-c", "account"); // Cat's operator has an account, not verification: its checks cannot settle a claim
    const misinfo = { topic: "Misinformation and Its Impacts", subfield: "Sociology and Political Science", field: "Social Sciences", domain: "Social Sciences" };
    // Each of these would come first on its headline and paper, were it not for what the card would have to say.
    const whole = async (id: string, source: string, headline: string) => { await w.paper(source, { title: `The paper of ${headline}`, topic: misinfo }); await w.explain(id, headline); };
    const a1 = await w.register("Ant", "doi:10.1000/s1", "subtly shifting attention to accuracy increases the quality of news that people subsequently share");
    await whole(a1, "doi:10.1000/s1", "A finding its checks will disagree about.");
    const lost = await w.register("Ant", "doi:10.1000/s2", "the sentence the scout could not find anywhere it looked for the paper", "unresolvable");
    await whole(lost, "doi:10.1000/s2", "A finding whose source the scout could not resolve.");
    const reg = await w.svc.registerExternalClaim(await w.sign("Ant", { protocol: "ecdysis/0.2", type: "claim.external", source: "doi:10.1000/s3", quote: "A widely held position stated here as its authors state it, at length enough to screen.", test: "A counterexample of the stated form, or an established claim on the record entailing its negation.", kind: "conceptual" }));
    assert.equal(reg.status, 201, JSON.stringify(reg.body));
    const idea = String((reg.body as Record<string, Json>)["ref"]);
    await w.quotes.put({ claim: idea, status: "verified", where: "crossref-abstract", nearest: null, similarity: 1, checkedAt: w.now().toISOString(), attempts: 1, detail: null });
    await whole(idea, "doi:10.1000/s3", "A position argued rather than measured.");
    const plain = await w.register("Bee", "doi:10.1000/s4", "the measured lensing signal exceeds the baryonic prediction by a factor of five");
    const card = async () => { const html = (await w.get("/")).html; const i = html.indexOf('<aside class="find-card"'); return i < 0 ? "" : html.slice(i, html.indexOf("</aside>", i)); };

    // Confirmed by a verified operator, then failed by one with an account only: still supported, but a disagreement.
    await w.check("Bee", a1, "confirmed");
    await w.check("Cat", a1, "failed");
    assert.equal((await w.svc.scores()).claims.get(a1)!.status, "supported", "Cat's failure cannot settle anything");
    let c = await card();
    assert.ok(c.includes(`/c/${plain}"`), "the plain unchecked finding is shown instead");
    for (const id of [a1, lost, idea]) assert.ok(!c.includes(`/c/${id}"`), id);
    assert.doesNotMatch(c, /disagree|did not get/);

    // A failed check, even one that cannot settle the claim, takes an unchecked claim off the front page.
    await w.check("Cat", plain, "failed");
    assert.equal((await w.svc.scores()).claims.get(plain)!.status, "unchecked");
    c = await card();
    assert.equal(c, "", "nothing left that the card could tell without a failure: no card at all");
  });

  it("chooses by the words the card prints: whole and surest first, never a disputed receipt", () => {
    const base: PeopleClaimV2 = {
      id: "ext:0000000000000001", text: "t", headline: "h", external: true, kind: "empirical", status: "supported", credence: 0.7, stakes: 0, seq: 1,
      checkedAt: "2026-10-09T10:00:00Z", source: "doi:10.1/x", agent: "Ant", paper: "doi:10.1/x", field: null, subfield: null, topic: null, keywords: [], flag: null, quote: "verified",
    };
    const c = (id: number, over: Partial<PeopleClaimV2>): PeopleClaimV2 => ({ ...base, id: `ext:${String(id).padStart(16, "0")}`, seq: id, ...over });
    const pick = (claims: PeopleClaimV2[], o: Partial<Parameters<typeof featuredFinding>[1]> = {}) =>
      featuredFinding(claims, { full: () => 0, tone: () => "show", disputed: () => false, ...o })?.id ?? null;
    const sure = c(2, { credence: 0.8 });
    assert.equal(pick([c(1, {}), sure]), sure.id, "the surest");
    assert.equal(pick([sure, c(3, { status: "established", credence: 0.91 })]), c(3, {}).id, "established before supported");
    assert.equal(pick([sure, c(4, {})], { full: (x) => (x.id === sure.id ? 1 : 0) }), c(4, {}).id, "a whole card before a surer one without its headline or paper");
    assert.equal(pick([c(5, { checkedAt: "2026-10-01T00:00:00Z" }), c(6, { checkedAt: "2026-10-09T00:00:00Z" })]), c(6, {}).id, "then the most recently checked");
    assert.equal(pick([sure, c(7, {})], { disputed: (x) => x.id === sure.id }), c(7, {}).id, "a receipt another re-ran and could not match keeps its claim off");
    for (const tone of ["mixed", "split", "fail", "uncounted", null] as const) assert.equal(pick([sure], { tone: () => tone }), null, `a story told as ${tone}`);
    for (const over of [{ status: "contested" }, { status: "refuted" }, { quote: "mismatch", flag: "mismatch" as const }, { quote: null }, { quote: "unresolvable" }, { kind: "conceptual" }, { external: false }])
      assert.equal(pick([c(8, over)]), null, JSON.stringify(over));
    // With nothing supported, a claim no check has reached a result on, the most relied on; never one with a result of any kind.
    const fresh = (id: number, over: Partial<PeopleClaimV2>) => c(id, { status: "unchecked", credence: 0.55, checkedAt: null, ...over });
    assert.equal(pick([fresh(9, { stakes: 1 }), fresh(10, { stakes: 3 })], { tone: () => null }), c(10, {}).id);
    assert.equal(pick([fresh(11, { checkedAt: "2026-10-09T00:00:00Z" })], { tone: () => null }), null, "an unchecked claim that a check failed is not shown as untouched");
  });
});

describe("the off-log reads, kept a minute per isolate", () => {
  it("reads the papers, headlines and quote verdicts once a minute for the front page and the claims list, and never keeps a failed read", async () => {
    const w = await world();
    await w.agent("Ant", "op-a", ["claude"]);
    const id = await w.register("Ant", "doi:10.1000/m1", "subtly shifting attention to accuracy increases the quality of news that people subsequently share");
    await w.paper("doi:10.1000/m1", { title: "Shifting attention to accuracy can reduce misinformation online" });
    await w.explain(id, "Prompting people to think about accuracy improves the news they share.");
    let reads = 0, failNext = false;
    const context = {
      getSource: (s: string) => w.context.getSource(s), getClaim: (c: string) => w.context.getClaim(c), sourceIndex: () => w.context.sourceIndex(), headlines: () => w.context.headlines(),
      papers: async () => { reads++; if (failNext) { failNext = false; throw new Error("D1 is down"); } return w.context.papers(); },
    };
    const memo = new OffLogMemo(60_000);
    const pages = new PagesHandler(w.svc, { host: "api.ecdysis.me", quotes: w.quotes, context, memo });
    const get = async (path: string) => (await (await pages.handle("GET", path, "text/html"))!.text());
    const [home, list] = await Promise.all([get("/"), get("/claims")]);
    assert.equal(reads, 1, "two requests at once share one read");
    assert.match(home, /Prompting people to think about accuracy/);
    assert.match(list, /Prompting people to think about accuracy/);
    await get("/");
    await get("/claims");
    assert.equal(reads, 1, "and it serves both pages for the minute");
    await w.explain(id, "A newer headline, written after the read.");
    assert.doesNotMatch(await get("/"), /A newer headline/, "within the minute, the kept read");
    w.tick(61_000);
    assert.match(await get("/"), /A newer headline/, "after it, a fresh read");
    assert.equal(reads, 2);
    w.tick(61_000);
    failNext = true;
    assert.match(await get("/"), /A newer headline/, "a failed table leaves the page standing on what it could read");
    await get("/");
    assert.equal(reads, 4, "and the failed read was not kept");
    const unmemoised = new PagesHandler(w.svc, { host: "api.ecdysis.me", quotes: w.quotes, context });
    await unmemoised.handle("GET", "/", "text/html");
    await unmemoised.handle("GET", "/", "text/html");
    assert.equal(reads, 6, "without a memo, every request reads");
  });
});
