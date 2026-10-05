/**
 * The scouts call fetch the way Cloudflare's runtime allows. workerd throws "Illegal invocation" when the global `fetch` is
 * called as a method of another object (`this.fetchImpl(url)` after `this.fetchImpl = fetch`); Node does not. Both scouts
 * stored it that way, so on the deployment every request failed while every test passed: from 4 and 5 October no source's
 * reach was ever observed (stakes 0 everywhere, so the map of pressure was empty) and no quote was ever checked. These tests
 * run the scouts against a fetch that refuses a foreign `this`, as workerd does, and show the old way failing.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { StakesScout } from "../src/api/v2/stakes-scout.js";
import { MemoryQuoteCheckStore, QuoteScout } from "../src/api/v2/quotes.js";

const QUOTE = "the compute-optimal token count scales linearly with parameters";

/** A fetch that behaves like workerd's about `this`, and answers OpenAlex and arXiv with just enough to parse. */
function workerdFetch(calls: string[]) {
  return function (this: unknown, input: RequestInfo | URL): Promise<Response> {
    if (this !== undefined && this !== globalThis) throw new TypeError("Illegal invocation: function called with incorrect `this` reference");
    const url = String(input);
    calls.push(url);
    if (url.startsWith("https://export.arxiv.org/")) {
      return Promise.resolve(new Response(`<feed><entry><title>Training compute-optimal models</title><summary>We find that ${QUOTE}.</summary></entry></feed>`, { status: 200 }));
    }
    return Promise.resolve(new Response(JSON.stringify({ id: "https://openalex.org/W4225591000", cited_by_count: 662, publication_year: 2022, primary_topic: { field: { id: "https://openalex.org/fields/17", display_name: "Computer Science" } } }), { status: 200, headers: { "content-type": "application/json" } }));
  };
}

async function withFetch<T>(f: typeof fetch, run: () => Promise<T>): Promise<T> {
  const real = globalThis.fetch;
  globalThis.fetch = f;
  try { return await run(); } finally { globalThis.fetch = real; }
}

describe("the scouts on a runtime that refuses a foreign `this` for fetch", () => {
  it("the stakes scout's own fetch reaches the citation graph", async () => {
    const calls: string[] = [];
    const got = await withFetch(workerdFetch(calls) as typeof fetch, () => new StakesScout({ v2: {} as never, log: {} as never, pause: async () => {} }).observe("arxiv:2203.15556"));
    assert.equal(got.status, "observed", JSON.stringify(got));
    assert.ok(calls.some((u) => u.startsWith("https://api.openalex.org/works/doi:")));
  });

  it("the quote scout's own fetch reaches arXiv and verifies the quote", async () => {
    const calls: string[] = [];
    const row = await withFetch(workerdFetch(calls) as typeof fetch, () => new QuoteScout({ store: new MemoryQuoteCheckStore(), v2: {} as never, pause: async () => {} }).check("ext:0123456789abcdef", "arxiv:2203.15556", QUOTE));
    assert.equal(row.status, "verified", JSON.stringify(row));
    assert.equal(calls.length, 1);
  });

  it("the old way, fetch kept bare as a property and called as a method, fails exactly as it did on the deployment", async () => {
    const calls: string[] = [];
    const bare = workerdFetch(calls) as typeof fetch;
    const stakes = await new StakesScout({ v2: {} as never, log: {} as never, pause: async () => {}, fetchImpl: bare }).observe("arxiv:2203.15556");
    assert.equal(stakes.status, "error");
    assert.match((stakes as { detail: string }).detail, /Illegal invocation/);
    const quote = await new QuoteScout({ store: new MemoryQuoteCheckStore(), v2: {} as never, pause: async () => {}, fetchImpl: bare }).check("ext:0123456789abcdef", "arxiv:2203.15556", QUOTE);
    assert.equal(quote.status, "error");
    assert.match(quote.detail ?? "", /Illegal invocation/);
    assert.equal(calls.length, 0, "nothing ever left the Worker");
  });
});

describe("the registration candidates on the deployment", () => {
  it("are kept in ops state, so the stakes scout's monthly read reaches the direction list's register acts", async () => {
    const { candidatesFrom } = await import("../src/index.js");
    const rows = new Map<string, { value: unknown; at: string }>();
    const store = {
      getOpsState: async (key: string) => (rows.get(key) as { value: never; at: string } | undefined) ?? null,
      putOpsState: async (key: string, value: unknown, at: string) => { rows.set(key, { value, at }); },
    };
    const c = candidatesFrom(store as never);
    assert.equal(await c.get(), null, "nothing read yet");
    const set = { fields: { "17": { field: "Computer Science", observedAt: "2026-10-05T12:00:00Z", works: [{ work: "https://openalex.org/W1", source: "arxiv:2203.15556", title: "A work", citedBy: 662, year: 2022, field: "Computer Science", observedAt: "2026-10-05T12:00:00Z" }] } } };
    await c.put(set);
    assert.deepEqual(await c.get(), set);
    assert.ok(rows.has("direction:candidates"), "under the key the reference names");
  });
});
