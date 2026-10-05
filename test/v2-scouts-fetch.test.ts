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

describe("the OpenAlex key", () => {
  it("goes to OpenAlex alone, as a bearer header, never in a URL; without one nothing is sent", async () => {
    const seen: Array<{ url: string; auth: string | null }> = [];
    const capture: typeof fetch = async (input, init) => {
      const url = String(input);
      const h = new Headers(init?.headers);
      seen.push({ url, auth: h.get("authorization") });
      if (url.startsWith("https://api.openalex.org/works/doi:")) return new Response(JSON.stringify({ id: "https://openalex.org/W1", cited_by_count: 5, publication_year: 2010, primary_topic: { field: { id: "https://openalex.org/fields/17", display_name: "Computer Science" } } }), { status: 200 });
      if (url.startsWith("https://api.openalex.org/fields/")) return new Response(JSON.stringify({ display_name: "Computer Science", works_count: 1000, cited_by_count: 50000 }), { status: 200 });
      return new Response("{}", { status: 404 });
    };
    const secret = "oa-test-key-0123456789";
    const withKey = new StakesScout({ v2: {} as never, log: {} as never, pause: async () => {}, fetchImpl: capture, apiKey: secret }) as unknown as { observe(s: string): Promise<{ status: string }>; observeField(id: string): Promise<unknown> };
    assert.equal((await withKey.observe("doi:10.1000/xyz")).status, "observed");
    assert.ok(await withKey.observeField("17"));
    assert.ok(seen.length >= 2 && seen.every((r) => r.auth === `Bearer ${secret}`), JSON.stringify(seen));
    assert.ok(seen.every((r) => !r.url.includes(secret)), "never in a URL");
    seen.length = 0;
    const without = new StakesScout({ v2: {} as never, log: {} as never, pause: async () => {}, fetchImpl: capture }) as unknown as { observe(s: string): Promise<{ status: string }> };
    assert.equal((await without.observe("doi:10.1000/xyz")).status, "observed");
    assert.ok(seen.every((r) => r.auth === null));
    // Semantic Scholar, the fallback, never sees it.
    seen.length = 0;
    const fallback: typeof fetch = async (input, init) => {
      const url = String(input);
      seen.push({ url, auth: new Headers(init?.headers).get("authorization") });
      if (url.startsWith("https://api.openalex.org/")) return new Response("{}", { status: 404 });
      return new Response(JSON.stringify({ paperId: "p1", citationCount: 3, year: 2020, s2FieldsOfStudy: [{ category: "Computer Science" }] }), { status: 200 });
    };
    const viaS2 = new StakesScout({ v2: {} as never, log: {} as never, pause: async () => {}, fetchImpl: fallback, apiKey: secret }) as unknown as { observe(s: string): Promise<{ status: string }> };
    await viaS2.observe("arxiv:2203.15556");
    const s2 = seen.filter((r) => r.url.startsWith("https://api.semanticscholar.org/"));
    assert.ok(s2.length >= 1 && s2.every((r) => r.auth === null), JSON.stringify(seen));
  });
});

describe("the quote scout after the fetch fix", () => {
  it("starts again on claims whose attempts the bug spent, and only on those", async () => {
    const store = new MemoryQuoteCheckStore();
    const at = "2026-10-05T11:00:00.000Z";
    await store.put({ claim: "ext:aaaaaaaaaaaaaaaa", status: "error", where: null, nearest: null, similarity: null, detail: "Illegal invocation: function called with incorrect `this` reference.", checkedAt: at, attempts: 4 });
    await store.put({ claim: "ext:bbbbbbbbbbbbbbbb", status: "error", where: null, nearest: null, similarity: null, detail: "arXiv 503", checkedAt: at, attempts: 4 });
    const external = new Map([
      ["ext:aaaaaaaaaaaaaaaa", { source: "arxiv:2203.15556", quote: QUOTE }],
      ["ext:bbbbbbbbbbbbbbbb", { source: "arxiv:2203.15556", quote: QUOTE }],
    ]);
    const calls: string[] = [];
    const scout = new QuoteScout({ store, v2: { record: async () => ({ external, held: new Set<string>() }) } as never, pause: async () => {}, now: () => new Date("2026-10-05T11:30:00Z"), fetchImpl: (input, init) => (workerdFetch(calls) as typeof fetch)(input, init) });
    const out = await scout.run(6);
    assert.equal(out.checked, 1, "the row the bug spent is checked again; a real failure past its four attempts is left alone");
    const again = await store.get("ext:aaaaaaaaaaaaaaaa");
    assert.equal(again?.status, "verified");
    assert.equal(again?.attempts, 1, "counted afresh");
    assert.equal((await store.get("ext:bbbbbbbbbbbbbbbb"))?.attempts, 4);
  });
});
