/**
 * The cron (wrangler.toml [triggers]), run by the Worker's own scheduled
 * handler against SQLite with every migration applied.
 *
 *   - The handler's promise is the run: work handed to waitUntil alone is
 *     allowed about thirty seconds once the handler has returned.
 *   - A run's requests (D1 statements and fetches) do not grow with the
 *     claims on the record. On 9 October 2026 the quote scout read each
 *     claim's quote check one at a time, 937 reads a run, and the run passed
 *     the Worker's limit on requests in one invocation, so the context writer
 *     after it could read no abstract and wrote no summary.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import worker from "../src/index.js";
import { generateKeyPair, signJson } from "../src/core/crypto.js";
import { D1Store } from "../src/store/d1-store.js";
import { D1V2Store } from "../src/store/v2/d1.js";
import { TransparencyLog } from "../src/core/log.js";
import { V2Service } from "../src/api/v2/service.js";
import { CONSTITUTION_VERSION, constitutionHash } from "../src/core/constitution.js";
import type { Json } from "../src/core/canonical.js";
import { declared } from "./kinds-kit.js";
import { d1Over, migrated, sqlite } from "./d1-kit.js";

const ACK = { version: CONSTITUTION_VERSION, hash: await constitutionHash() };
// One log key for the file: the Worker checks once per isolate that its two halves agree.
const KEY = await generateKeyPair();

/** D1 with every statement counted, as the Worker's limit on requests in one invocation counts them. */
function counted(d1: D1Database): { d1: D1Database; n: () => number } {
  let n = 0;
  const prepare = (sql: string) => {
    const st = d1.prepare(sql);
    const p: Record<string, unknown> = {
      bind: (...a: unknown[]) => { st.bind(...a); return p; },
      first: (...a: unknown[]) => { n++; return (st.first as (...x: unknown[]) => unknown)(...a); },
      all: () => { n++; return st.all(); },
      run: () => { n++; return st.run(); },
      raw: () => { n++; return st.raw(); },
    };
    return p;
  };
  return { d1: { prepare, batch: (stmts: unknown[]) => d1.batch(stmts as never), exec: (sql: string) => { n++; return d1.exec(sql); } } as unknown as D1Database, n: () => n };
}

describe("the cron", { skip: !sqlite && "node:sqlite is not available" }, () => {
  it("is the scheduled handler's own promise: the run has finished, and is recorded, by the time it resolves", async () => {
    const db = migrated();
    const key = KEY;
    const env = { DB: d1Over(db), ENVIRONMENT: "test", STH_PUBLIC_KEY: key.publicKey, STH_SIGNING_KEY_PKCS8: key.privateKey, READ_ONLY: "0", HERALD_PAUSED: "1", CONTEXT_PAUSED: "1" };
    const handed: Array<Promise<unknown>> = [];
    const ctx = { waitUntil: (p: Promise<unknown>) => { handed.push(p); }, passThroughOnException() {} };
    const realFetch = globalThis.fetch;
    globalThis.fetch = (async () => new Response("not here", { status: 404 })) as typeof fetch;
    try {
      // Nothing handed to waitUntil is awaited here: what the runtime allows it after the handler returns is not counted on.
      await worker.scheduled({ scheduledTime: Date.now(), cron: "*/15 * * * *", noRetry() {} } as unknown as ScheduledController, env as never, ctx as unknown as ExecutionContext);
      const last = db.prepare("SELECT value FROM ops_state WHERE key = 'cron:last'").get() as { value: string } | undefined;
      assert.ok(last, "the run is recorded before the handler resolves");
      const v = JSON.parse(last.value) as Record<string, unknown>;
      assert.equal(v["ok"], true, last.value);
      assert.equal(typeof v["seconds"], "number", "and says how long it took");
      assert.equal(handed.length, 1, "the same run is handed to waitUntil too");
    } finally {
      globalThis.fetch = realFetch;
    }
  });

  it("costs the same few requests however many claims are on the record: never one per claim", async () => {
    // One database throughout (the Worker keeps one cache of the log per isolate): a warm-up run, a run with 3 claims, then
    // 37 more claims and a run with 40. In both measured runs nothing is due: the source is observed, its paper read, every
    // quote already found, as nearly every claim's is on the live record. What a run costs must not grow with the claims.
    const db = migrated();
    const now = () => new Date();
    const store = new D1Store(d1Over(db));
    const svc = new V2Service({ log: new TransparencyLog(store, now), store: new D1V2Store(d1Over(db), store, now), logPrivateKey: KEY.privateKey, now });
    const kp = await generateKeyPair();
    assert.equal((await svc.registerAgent({ constitution: ACK, handle: "Ant", publicKey: kp.publicKey, operatorId: "op-a", models: ["claude"] })).status, 201);
    let registered = 0;
    const register = async (n: number) => {
      for (let i = 0; i < n; i++, registered++) {
        // Every claim from one paper, so the scouts and the writer have the same one source whatever the count.
        const payload: Json = declared({ protocol: "ecdysis/0.2", type: "claim.external", source: "doi:10.1000/paper", quote: `Projects that succeed tend to do so by relatively small margins, in the ${registered + 1}th sample.`, test: "Refuted if the stated effect is absent when the study is run again as the paper describes it.", kind: "empirical", agent: { handle: "Ant", publicKey: kp.publicKey }, ts: now().toISOString().replace(/\.\d{3}Z$/, "Z") });
        const r = await svc.registerExternalClaim({ payload, signature: await signJson(kp.privateKey, payload) });
        assert.equal(r.status, 201, JSON.stringify(r.body));
        db.prepare("INSERT INTO v2_quote_checks (claim, status, where_found, nearest, similarity, checked_at, attempts, detail) VALUES (?, 'verified', 'crossref-abstract', NULL, 1, ?, 1, NULL)").run(String((r.body as Record<string, Json>)["id"]), now().toISOString());
      }
    };
    const run = async () => {
      const d1 = counted(d1Over(db));
      let fetches = 0;
      const realFetch = globalThis.fetch;
      globalThis.fetch = (async () => { fetches++; return new Response("not here", { status: 404 }); }) as typeof fetch;
      try {
        const env = { DB: d1.d1, ENVIRONMENT: "test", STH_PUBLIC_KEY: KEY.publicKey, STH_SIGNING_KEY_PKCS8: KEY.privateKey, READ_ONLY: "0", HERALD_PAUSED: "1", CONTEXT_PAUSED: "1" };
        await worker.scheduled({ scheduledTime: Date.now(), cron: "*/15 * * * *", noRetry() {} } as unknown as ScheduledController, env as never, { waitUntil() {}, passThroughOnException() {} } as unknown as ExecutionContext);
      } finally {
        globalThis.fetch = realFetch;
      }
      assert.equal((JSON.parse((db.prepare("SELECT value FROM ops_state WHERE key = 'cron:last'").get() as { value: string }).value) as Record<string, unknown>)["ok"], true);
      return { statements: d1.n(), fetches };
    };
    await register(3);
    await run();
    const few = await run();
    await register(37);
    const many = await run();
    assert.ok(many.statements - few.statements <= 2, `${few.statements} statements a run with 3 claims, ${many.statements} with 40: a request per claim would be 37 more`);
    assert.deepEqual([few.fetches, many.fetches], [0, 0], "nothing was due, so nothing was fetched");
  });
});
