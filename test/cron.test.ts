/**
 * The cron (wrangler.toml [triggers]), run by the Worker's own scheduled
 * handler against SQLite with every migration applied. The handler's promise
 * is the run: work handed to waitUntil alone is allowed about thirty seconds
 * once the handler has returned, which on 9 October 2026 cut the context
 * writer off after its first paper or two, every run.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import worker from "../src/index.js";
import { generateKeyPair } from "../src/core/crypto.js";
import { d1Over, migrated, sqlite } from "./d1-kit.js";

describe("the cron", { skip: !sqlite && "node:sqlite is not available" }, () => {
  it("is the scheduled handler's own promise: the run has finished, and is recorded, by the time it resolves", async () => {
    const db = migrated();
    const key = await generateKeyPair();
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
});
