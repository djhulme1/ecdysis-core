/**
 * The D1 store's real SQL, run against SQLite (what D1 is built on) with
 * every migration applied in order. The in-memory store can't catch a
 * misspelt column, a binding of undefined, an upsert that clobbers a column,
 * or a migration that doesn't apply: this does, before a deploy does.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { D1Store } from "../src/store/d1-store.js";
import { EcdysisService } from "../src/api/service.js";
import { structuralScreener } from "../src/core/hazard.js";
import { signJson } from "../src/core/crypto.js";
import { CONSTITUTION_VERSION, constitutionHash } from "../src/core/constitution.js";
const ACK = { version: CONSTITUTION_VERSION, hash: await constitutionHash() };
import type { Json } from "../src/core/canonical.js";
import { seededKeyPair } from "./society-kit.js";

type Sqlite = typeof import("node:sqlite");
let sqlite: Sqlite | null = null;
try {
  sqlite = await import("node:sqlite");
} catch {
  sqlite = null; // older Node: skipped, never silently passed
}

/** The slice of D1's binding the store uses, over node:sqlite. Refuses undefined, as D1 does. */
function d1Over(db: InstanceType<Sqlite["DatabaseSync"]>): D1Database {
  const check = (args: unknown[]) => {
    for (const a of args) if (a === undefined) throw new Error("D1_TYPE_ERROR: Type 'undefined' not supported");
    return args as Array<string | number | null>;
  };
  const prepare = (sql: string) => {
    let args: unknown[] = [];
    const stmt = {
      bind(...a: unknown[]) {
        args = a;
        return stmt;
      },
      async first<T>() {
        return (db.prepare(sql).get(...check(args)) ?? null) as T | null;
      },
      async all<T>() {
        return { results: db.prepare(sql).all(...check(args)) as T[], success: true, meta: {} };
      },
      async run() {
        const r = db.prepare(sql).run(...check(args));
        return { success: true, meta: { changes: Number(r.changes) } };
      },
    };
    return stmt;
  };
  return {
    prepare,
    async batch(stmts: Array<{ run: () => Promise<unknown> }>) {
      db.exec("BEGIN");
      try {
        const out = [];
        for (const s of stmts) out.push(await s.run());
        db.exec("COMMIT");
        return out;
      } catch (e) {
        db.exec("ROLLBACK");
        throw e;
      }
    },
    async exec(sql: string) {
      db.exec(sql);
      return { count: 0, duration: 0 };
    },
  } as unknown as D1Database;
}

function migrated(): InstanceType<Sqlite["DatabaseSync"]> {
  const db = new sqlite!.DatabaseSync(":memory:");
  const dir = join(import.meta.dirname, "..", "migrations");
  for (const f of readdirSync(dir).filter((x) => x.endsWith(".sql")).sort()) db.exec(readFileSync(join(dir, f), "utf8"));
  return db;
}

describe("the D1 store against SQLite, every migration applied", { skip: !sqlite && "node:sqlite is not available" }, () => {
  it("applies every migration in order, from an empty database", () => {
    const db = migrated();
    const cols = (db.prepare("PRAGMA table_info(quarantine)").all() as Array<{ name: string }>).map((c) => c.name);
    assert.ok(cols.includes("preprint_withdrawn_at"));
    const tables = (db.prepare("SELECT name FROM sqlite_master WHERE type = 'table'").all() as Array<{ name: string }>).map((t) => t.name);
    for (const t of ["settings", "claims", "quarantine", "agents", "juror_operators"]) assert.ok(tables.includes(t), t);
  });

  it("stores settings and claims, and lists claims newest first by handle and status", async () => {
    const store = new D1Store(d1Over(migrated()));
    await store.putSetting({ key: "submissions", value: "paused", updatedAt: "2026-10-01T10:00:00.000Z", updatedBy: "daniel@hulme.ai" });
    await store.putSetting({ key: "submissions", value: "open", updatedAt: "2026-10-01T11:00:00.000Z", updatedBy: "daniel@hulme.ai" });
    assert.deepEqual(await store.listSettings(), [{ key: "submissions", value: "open", updatedAt: "2026-10-01T11:00:00.000Z", updatedBy: "daniel@hulme.ai" }]);
    const base = {
      handle: "Moth-1", operatorId: "op-moth", status: "issued" as const, expiresAt: "2026-10-15T10:00:00.000Z",
      platform: null, account: null, postUrl: null, show: true, verifiedAt: null, verifiedBy: null, attempts: 0, lastError: null,
    };
    await store.putClaim({ ...base, id: "a".repeat(32), code: "ecd-2222-3333", createdAt: "2026-10-01T10:00:00.000Z" });
    await store.putClaim({ ...base, id: "b".repeat(32), code: "ecd-4444-5555", createdAt: "2026-10-01T11:00:00.000Z" });
    await store.putClaim({ ...base, id: "c".repeat(32), code: "ecd-6666-7777", createdAt: "2026-10-01T12:00:00.000Z", handle: "Wasp-1" });
    await store.putClaim({
      ...base, id: "a".repeat(32), code: "ecd-2222-3333", createdAt: "2026-10-01T10:00:00.000Z",
      status: "verified", platform: "x", account: "alice", postUrl: "https://x.com/alice/status/1840000000000000001", show: false,
      verifiedAt: "2026-10-01T10:05:00.000Z", verifiedBy: "auto", attempts: 1,
    });
    const a = (await store.getClaim("a".repeat(32)))!;
    assert.equal(a.status, "verified");
    assert.equal(a.show, false);
    assert.equal(a.account, "alice");
    assert.equal((await store.getClaimByCode("ecd-4444-5555"))?.id, "b".repeat(32));
    assert.deepEqual((await store.listClaims({ handle: "Moth-1", limit: 10 })).map((c) => c.id), ["b".repeat(32), "a".repeat(32)]);
    assert.deepEqual((await store.listClaims({ status: "issued", limit: 10 })).map((c) => c.id), ["c".repeat(32), "b".repeat(32)]);
    assert.deepEqual((await store.listClaims({ handle: "Moth-1", status: "verified", limit: 10 })).map((c) => c.id), ["a".repeat(32)]);
    assert.equal((await store.listClaims({ limit: 2 })).length, 2);
    // The code is unique: a second claim can't reuse one.
    await assert.rejects(store.putClaim({ ...base, id: "d".repeat(32), code: "ecd-2222-3333", createdAt: "2026-10-01T13:00:00.000Z" }));
  });

  it("stores doorbells: an upsert keeps the creation time, the setup id is unique, and every column round-trips", async () => {
    const store = new D1Store(d1Over(migrated()));
    const bell = {
      handle: "Moth-1", kind: "claude-routine" as const, status: "pending" as const, cadence: "daily" as const,
      routineId: null, url: null, tokenSealed: null, keyRef: null,
      setupId: "s".repeat(32), setupToken: "t".repeat(64), setupIssuedAt: "2026-10-02T09:00:00.000Z", challenge: null,
      createdAt: "2026-10-02T09:00:00.000Z", updatedAt: "2026-10-02T09:00:00.000Z",
      lastRingAt: null, lastResearchAt: null, lastOkAt: null, lastSessionUrl: null, failures: 0, lastError: null, ringsDay: null, ringsToday: 0,
      targetSealed: null, settings: {},
    };
    await store.putDoorbell(bell);
    const active = {
      ...bell, status: "active" as const, routineId: "trig_01ABCDEFGHJKMNPQRSTVWXYZ0", tokenSealed: "v1.abc.def", keyRef: "hkdf-sth/v1",
      createdAt: "2026-10-02T10:00:00.000Z", updatedAt: "2026-10-02T10:00:00.000Z", lastRingAt: "2026-10-02T10:00:01.000Z",
      lastResearchAt: "2026-10-02T10:00:01.000Z", lastOkAt: "2026-10-02T10:00:01.000Z", lastSessionUrl: "https://claude.ai/code/session_01X",
      failures: 1, lastError: "timeout", ringsDay: "2026-10-02", ringsToday: 1,
      settings: { platform: "claude", tag: "abcdefghjk", stop: "5".repeat(32) },
    };
    await store.putDoorbell(active);
    const got = (await store.getDoorbell("Moth-1"))!;
    assert.deepEqual(got, { ...active, createdAt: bell.createdAt }, "every column round-trips, and the first creation time stands");
    assert.equal((await store.getDoorbellBySetup("s".repeat(32)))?.handle, "Moth-1");
    assert.equal(await store.getDoorbellBySetup("x".repeat(32)), null);
    await store.putDoorbell({ ...bell, handle: "Wasp-1", kind: "webhook", url: "https://hooks.example.org/ring", setupId: "w".repeat(32) });
    assert.deepEqual((await store.listDoorbells(10)).map((d) => d.handle), ["Moth-1", "Wasp-1"]);
    assert.equal((await store.listDoorbells(1)).length, 1);
    // One setup page per doorbell: another agent can't take a setup id.
    await assert.rejects(store.putDoorbell({ ...bell, handle: "Gnat-1", setupId: "s".repeat(32) }));
    // The kind is checked by the schema, not only by the code.
    await assert.rejects(store.putDoorbell({ ...bell, handle: "Gnat-1", setupId: "g".repeat(32), kind: "smtp" as never }));
    // An email doorbell: the sealed address and the settings (an address waiting for its click included) round-trip.
    const email = {
      ...bell, handle: "Bee-1", kind: "email" as const, status: "active" as const, setupId: "b".repeat(32), targetSealed: "v2.hkdf.iv.ct",
      settings: { platform: "gemini", tag: "k7f3q9w2mx", stop: "a".repeat(32), masked: "d•••@example.org", pending: { kind: "email" as const, sealed: "v2.env.iv2.ct2", masked: "x•••@example.com", challenge: "c".repeat(32), issuedAt: "2026-10-02T11:00:00.000Z", platform: "gemini", sent: 1 } },
    };
    await store.putDoorbell(email);
    assert.deepEqual(await store.getDoorbell("Bee-1"), email);
  });

  it("migration 0021 rebuilds the doorbells table without losing a row or a column", async () => {
    const db = new sqlite!.DatabaseSync(":memory:");
    const dir = join(import.meta.dirname, "..", "migrations");
    const files = readdirSync(dir).filter((x) => x.endsWith(".sql")).sort();
    const at = files.indexOf("0021_doorbells_everywhere.sql");
    assert.ok(at > 0, "the migration exists");
    for (const f of files.slice(0, at)) db.exec(readFileSync(join(dir, f), "utf8"));
    // A doorbell as the live table holds it before the change: a connected routine with a token, a failure and a ring.
    db.exec(`INSERT INTO doorbells (handle, kind, status, cadence, routine_id, url, token_sealed, key_ref, setup_id, setup_token, setup_issued_at,
      challenge, created_at, updated_at, last_ring_at, last_research_at, last_ok_at, last_session_url, failures, last_error, rings_day, rings_today)
      VALUES ('Chrysalis-1','claude-routine','active','daily','trig_01ABCDEFGHJK',NULL,'v1.iv.ct','sth-hkdf/v1','${"s".repeat(32)}','${"t".repeat(64)}',
      '2026-10-02T09:00:00.000Z',NULL,'2026-10-02T09:00:00.000Z','2026-10-04T08:00:00.000Z','2026-10-04T08:00:00.000Z','2026-10-04T06:51:00.000Z',
      '2026-10-04T08:00:00.000Z','https://claude.ai/code/session_01X',0,NULL,'2026-10-04',2)`);
    for (const f of files.slice(at)) db.exec(readFileSync(join(dir, f), "utf8"));
    const got = (await new D1Store(d1Over(db)).getDoorbell("Chrysalis-1"))!;
    assert.equal(got.kind, "claude-routine");
    assert.equal(got.status, "active");
    assert.equal(got.tokenSealed, "v1.iv.ct", "the sealed token survives");
    assert.equal(got.keyRef, "sth-hkdf/v1");
    assert.equal(got.routineId, "trig_01ABCDEFGHJK");
    assert.equal(got.lastResearchAt, "2026-10-04T06:51:00.000Z");
    assert.equal(got.ringsToday, 2);
    assert.equal(got.targetSealed, null);
    assert.deepEqual(got.settings, {});
    // The constraint and the unique setup id still hold on the rebuilt table, and the index is back.
    assert.throws(() => db.exec(`INSERT INTO doorbells (handle, kind, status, cadence, setup_id, setup_token, setup_issued_at, created_at, updated_at)
      VALUES ('X','smtp','active','daily','${"x".repeat(32)}','t','a','a','a')`));
    assert.throws(() => db.exec(`INSERT INTO doorbells (handle, kind, status, cadence, setup_id, setup_token, setup_issued_at, created_at, updated_at)
      VALUES ('Y','email','active','daily','${"s".repeat(32)}','t','a','a','a')`));
    assert.ok(db.prepare("SELECT name FROM sqlite_master WHERE type='index' AND name='doorbells_status'").get(), "the status index is rebuilt");
  });

  it("runs registration, a preprint, a switch, a withdrawal and an uninvite through the real SQL", async () => {
    const store = new D1Store(d1Over(migrated()));
    let t = Date.UTC(2026, 9, 1, 9, 0, 0);
    const svc = new EcdysisService({ store, screeners: [structuralScreener()], sthPrivateKey: null, now: () => new Date((t += 1000)) });
    const ack = { version: CONSTITUTION_VERSION, hash: await constitutionHash() };
    const kp = await seededKeyPair("d1/Moth-1");
    const reg = await svc.registerAgent({ handle: "Moth-1", publicKey: kp.publicKey, operatorId: "op-moth", constitution: ack });
    assert.equal(reg.status, 201, JSON.stringify(reg.body));
    const claimUrl = String(((reg.body as Record<string, Json>)["claim"] as Record<string, Json>)["url"]);
    assert.match(claimUrl, /\/claim\/[0-9a-f]{32}$/);
    assert.equal((await store.listClaims({ handle: "Moth-1", limit: 5 })).length, 1);

    const payload = {
      protocol: "ecdysis/0.1", type: "paper", title: "A preprint stored through the real SQL",
      abstract: "A careful measurement with its configuration, seeds and code attached so that anyone can recompute it.",
      field: "ml", claims: [{ text: "The effect holds under the stated set-up", confidence: 0.7 }],
      builds_on: [{ id: "arxiv:2203.15556", rel: "replicates" }], preprint: true,
      agent: { handle: "Moth-1", publicKey: kp.publicKey }, ts: new Date(t).toISOString().replace(/\.\d{3}Z$/, "Z"),
    } as unknown as Json;
    const sub = await svc.submitPaper({ payload, signature: await signJson(kp.privateKey, payload) });
    assert.equal(sub.status, 202, JSON.stringify(sub.body));
    const receipt = String((sub.body as Record<string, Json>)["id"]);
    const before = (await store.getQuarantine(receipt))!;
    assert.equal(((await svc.preprints()).body as { preprints: unknown[] }).preprints.length, 1);

    // Withdraw: one column, one way; a full-row write from a stale read can't undo it.
    assert.equal((await svc.withdrawPreprint(receipt)).status, 200);
    await store.putQuarantine(before);
    assert.ok((await store.getQuarantine(receipt))!.preprintWithdrawnAt, "COALESCE keeps the withdrawal");
    assert.equal(((await svc.preprints()).body as { preprints: unknown[] }).preprints.length, 0);

    // A switch: stored, logged, read back by a fresh instance (a new request).
    assert.equal((await svc.setSetting("submissions", "paused", "daniel@hulme.ai")).status, 200);
    const next = new EcdysisService({ store, screeners: [structuralScreener()], sthPrivateKey: null, now: () => new Date((t += 1000)) });
    assert.equal(await next.setting("submissions"), "paused");
    assert.equal((await next.registerAgent({ handle: "Late-1", publicKey: (await seededKeyPair("d1/late")).publicKey, operatorId: "op-late", constitution: ack })).status, 503);

    // Invite, then withdraw the invitation.
    assert.equal((await next.inviteJurorOperator("op-moth")).status, 201);
    assert.equal((await next.uninviteJurorOperator("op-moth")).status, 200);
    assert.equal(await store.getJurorOperator("op-moth"), null);

    // The log took every change and is intact.
    const audit = await next.audit();
    assert.equal((audit.body as { intact: boolean }).intact, true);
    const types = (await store.listLog(0, 100)).map((e) => e.type);
    for (const ty of ["agent.register", "moderation.remove", "operator.setting", "juror.invite", "juror.uninvite"]) assert.ok(types.includes(ty as never), ty);
  });
});

describe("the v2 store against SQLite, every migration applied", { skip: !sqlite && "node:sqlite is not available" }, () => {
  it("runs registration, an external claim, two receipts with a cross-check and the scores through the real SQL", async () => {
    const { D1V2Store } = await import("../src/store/v2/d1.js");
    const { V2Service } = await import("../src/api/v2/service.js");
    const { TransparencyLog } = await import("../src/core/log.js");
    const { generateKeyPair, signJson } = await import("../src/core/crypto.js");
    const db = migrated();
    const tables = (db.prepare("SELECT name FROM sqlite_master WHERE type = 'table'").all() as Array<{ name: string }>).map((t) => t.name);
    for (const t of ["v2_envelopes", "v2_bundles", "v2_outputs"]) assert.ok(tables.includes(t), t);
    const store = new D1Store(d1Over(db));
    let t = Date.UTC(2026, 9, 3, 9, 0, 0);
    const now = () => new Date((t += 1000));
    const log = new TransparencyLog(store, now);
    const logKey = await generateKeyPair();
    const svc = new V2Service({ log, store: new D1V2Store(d1Over(db), store, now), logPrivateKey: logKey.privateKey, now });
    const a = await generateKeyPair();
    const b = await generateKeyPair();
    assert.equal((await svc.registerAgent({ constitution: ACK, handle: "Ant", publicKey: a.publicKey, operatorId: "op-a", models: ["claude"] })).status, 201);
    assert.equal((await svc.registerAgent({ constitution: ACK, handle: "Bee", publicKey: b.publicKey, operatorId: "op-b", models: ["gpt"] })).status, 201);
    await svc.setTier("op-a", "verified");
    await svc.setTier("op-b", "verified");
    const sign = async (kp: { privateKey: string }, payload: Json) => ({ payload, signature: await signJson(kp.privateKey, payload) }) as Json;
    const ext = await svc.registerExternalClaim(await sign(a, { protocol: "ecdysis/0.2", type: "claim.external", source: "arxiv:1706.03762", quote: "attention alone reaches 28.4 BLEU on WMT14 En-De", test: "BLEU below 27 with the stated setup", agent: { handle: "Ant", publicKey: a.publicKey }, ts: "2026-10-03T09:00:00Z" }));
    assert.equal(ext.status, 201);
    const ref = String((ext.body as Record<string, Json>)["ref"]);
    const bundle = (n: number) => ({ repo: "https://github.com/example/rep", commit: n.toString(16).padStart(40, "0"), image: "sha256:" + "a".repeat(64), run: "python run.py", outputs: [{ name: "alpha", tolerance: 0.01 }], runtimeMinutes: 5 });
    const c1 = await svc.commitCheck(await sign(a, { protocol: "ecdysis/0.2", type: "check.commit", target: ref, kind: "replication", bundle: bundle(1) as unknown as Json, agent: { handle: "Ant", publicKey: a.publicKey }, ts: "2026-10-03T09:00:00Z" }));
    assert.equal(c1.status, 201, JSON.stringify(c1.body));
    const id1 = String((c1.body as Record<string, Json>)["id"]);
    assert.equal((await svc.fileResult(await sign(a, { protocol: "ecdysis/0.2", type: "check.result", commit: id1, outcome: "confirmed", outputs: { alpha: 28.4 }, crossCheck: null, agent: { handle: "Ant", publicKey: a.publicKey }, ts: "2026-10-03T09:01:00Z" }))).status, 201);
    const c2 = await svc.commitCheck(await sign(b, { protocol: "ecdysis/0.2", type: "check.commit", target: ref, kind: "replication", bundle: bundle(2) as unknown as Json, agent: { handle: "Bee", publicKey: b.publicKey }, ts: "2026-10-03T09:02:00Z" }));
    const b2 = c2.body as Record<string, Json>;
    assert.equal((b2["crossCheck"] as Record<string, Json>)["receipt"], id1);
    const r2 = await svc.fileResult(await sign(b, { protocol: "ecdysis/0.2", type: "check.result", commit: String(b2["id"]), outcome: "confirmed", outputs: { alpha: 28.3 }, crossCheck: { receipt: id1, outputs: { alpha: 28.405 } }, agent: { handle: "Bee", publicKey: b.publicKey }, ts: "2026-10-03T09:03:00Z" }));
    assert.equal(r2.status, 201, JSON.stringify(r2.body));
    assert.equal((r2.body as Record<string, Json>)["crossMatch"], true);
    const scores = await svc.scores();
    const claim = scores.claims.get(ref)!;
    assert.equal(claim.status, "supported");
    assert.deepEqual(claim.families, ["claude", "gpt"]);
    // The withheld outputs and the bundle round-trip through SQL; the log is intact.
    const v2store = new D1V2Store(d1Over(db), store, now);
    assert.deepEqual(await v2store.getOutputs(id1), { alpha: 28.4 });
    assert.equal((await v2store.getBundle(id1))!.run, "python run.py");
    const types = (await store.listLog(0, 100)).map((e) => e.type);
    for (const ty of ["agent.register", "operator.tier", "claim.external", "check.commit", "check.seal", "check.result"]) assert.ok(types.includes(ty), ty);
    const audit = await new (await import("../src/api/service.js")).EcdysisService({ store, screeners: [structuralScreener()], sthPrivateKey: null }).audit();
    assert.equal((audit.body as { intact: boolean }).intact, true);
  });

  it("keeps a verification request in the issues table through the real SQL: open, newest by subject, decided", async () => {
    const { D1V2Store } = await import("../src/store/v2/d1.js");
    const { D1IssueStore } = await import("../src/store/v2/issues-d1.js");
    const { IssueRegistry } = await import("../src/api/v2/issues.js");
    const { V2Service } = await import("../src/api/v2/service.js");
    const { TransparencyLog } = await import("../src/core/log.js");
    const db = migrated();
    const store = new D1Store(d1Over(db));
    let t = Date.UTC(2026, 9, 4, 14, 0, 0);
    const now = () => new Date((t += 1000));
    const svc = new V2Service({ log: new TransparencyLog(store, now), store: new D1V2Store(d1Over(db), store, now), logPrivateKey: null, now });
    const issues = new IssueRegistry({ store: new D1IssueStore(d1Over(db)), v2: svc, now });
    const text = "Dr A. Member, University of Example (https://example.edu/people/a-member); reach me at a.member@example.edu; agents run claude.";
    const first = await issues.requestVerification("op_1234567890abcdef12345678", text);
    assert.ok(first.ok, JSON.stringify(first));
    assert.equal((await issues.requestVerification("op_1234567890abcdef12345678", text)).ok, false, "one open request per operator");
    assert.equal((await issues.verificationOf("op_1234567890abcdef12345678"))!.status, "open");
    const declined = await issues.decideVerification(first.ok ? first.id : "", "decline", "Send a page that lists you.", "op_steward");
    assert.ok(declined.ok, JSON.stringify(declined));
    const second = await issues.requestVerification("op_1234567890abcdef12345678", `${text} Now listed.`);
    assert.ok(second.ok);
    const latest = (await issues.verificationOf("op_1234567890abcdef12345678"))!;
    assert.equal(latest.id, second.ok ? second.id : "", "the newest request, not the declined one");
    assert.equal(latest.status, "open");
    const verified = await issues.decideVerification(latest.id, "verify", "", "op_steward");
    assert.ok(verified.ok, JSON.stringify(verified));
    assert.equal((await svc.record()).tiers.get("op_1234567890abcdef12345678"), "verified", "the tier reached the log");
    assert.equal((await issues.verificationOf("op_1234567890abcdef12345678"))!.note, "verify: verified");
    assert.equal((db.prepare("SELECT COUNT(*) AS n FROM v2_issues WHERE kind = 'verification'").get() as { n: number }).n, 2);
  });
});

describe("the account store against SQLite, every migration applied", { skip: !sqlite && "node:sqlite is not available" }, () => {
  it("signs a person in, pairs an agent, keeps preferences, counts rate-limit events and deletes everything but the log", async () => {
    const { D1AccountStore } = await import("../src/store/v2/accounts-d1.js");
    const { Accounts } = await import("../src/api/v2/accounts.js");
    const { D1V2Store } = await import("../src/store/v2/d1.js");
    const { V2Service } = await import("../src/api/v2/service.js");
    const { TransparencyLog } = await import("../src/core/log.js");
    const { generateKeyPair } = await import("../src/core/crypto.js");
    const db = migrated();
    const tables = (db.prepare("SELECT name FROM sqlite_master WHERE type = 'table'").all() as Array<{ name: string }>).map((t) => t.name);
    for (const t of ["accounts", "account_sessions", "account_links", "account_pairings", "account_preferences", "account_events"]) assert.ok(tables.includes(t), t);
    let t = Date.UTC(2026, 9, 3, 9, 0, 0);
    const now = () => new Date((t += 1000));
    const sent: string[] = [];
    const accounts = new Accounts({
      store: new D1AccountStore(d1Over(db), now), key: "ef".repeat(32),
      send: async (m) => { sent.push(m.text); return { ok: true, id: "m" }; },
      from: "Ecdysis <accounts@notify.ecdysis.me>", replyTo: "replies@ecdysis.me", siteBase: "https://ecdysis.me", stewardEmailHashes: [], now,
    });
    const store = new D1Store(d1Over(db));
    const log = new TransparencyLog(store, now);
    const svc = new V2Service({ log, store: new D1V2Store(d1Over(db), store, now), logPrivateKey: null, now, pairing: (c, ip) => accounts.consumePairing(c, ip) });
    const r = await accounts.requestLink("dan@example.org", "1.1.1.1", null);
    assert.ok(r.ok);
    const token = sent[0]!.match(/t=([A-Za-z0-9_-]+)/)![1]!;
    const c = await accounts.completeLink(token, r.browser, "1.1.1.1");
    assert.ok(c.ok && c.created);
    assert.equal((await accounts.completeLink(token, r.browser, "1.1.1.1")).ok, false, "single use, through SQL");
    const s = (await accounts.session(c.session))!;
    assert.equal(s.account.id, c.account.id);
    const code = await accounts.newPairingCode(s);
    const kp = await generateKeyPair();
    const reg = await svc.registerAgent({ constitution: ACK, handle: "Moth", publicKey: kp.publicKey, pairing: code }, "1.1.1.1");
    assert.equal(reg.status, 201, JSON.stringify(reg.body));
    assert.equal((reg.body as Record<string, Json>)["operatorId"], c.account.operatorId);
    await accounts.savePreferences(s, { interests: { fields: ["math"], topics: ["sat"], claims: [], agents: [] }, notifications: { digest: "weekly", alerts: ["check.owed"] }, profile: null, feed: { epoch: 0 } });
    assert.deepEqual((await accounts.preferences(s)).interests.fields, ["math"]);
    const row = db.prepare("SELECT email_hash, email_sealed FROM accounts").get() as { email_hash: string; email_sealed: string };
    assert.ok(!row.email_sealed.includes("example") && !row.email_hash.includes("example"), "no readable address in the database");
    assert.equal(await accounts.emailOf(s.account), "dan@example.org");
    assert.equal((db.prepare("SELECT COUNT(*) AS n FROM account_events").get() as { n: number }).n >= 2, true);
    // OAuth and a managed agent, through the real SQL: a client, a code spent once, tokens, a sealed key that is opened and then erased.
    const { D1OAuthStore } = await import("../src/store/v2/oauth-d1.js");
    const { OAuth } = await import("../src/api/v2/oauth.js");
    const oauth = new OAuth({ accounts, store: new D1OAuthStore(d1Over(db), now), v2: svc, issuer: "https://ecdysis.me", resource: "https://api.ecdysis.me/mcp", siteBase: "https://ecdysis.me", now });
    const client = await oauth.register({ redirect_uris: ["https://app.example/cb"], client_name: "An app" }, "1.1.1.1");
    assert.equal(client.status, 201, JSON.stringify(client.body));
    const clientId = String((client.body as Record<string, Json>)["client_id"]);
    const verifier = "v".repeat(43);
    const challenge = (await import("../src/core/canonical.js")).b64urlEncode(new Uint8Array(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(verifier))));
    const q = new URLSearchParams({ response_type: "code", client_id: clientId, redirect_uri: "https://app.example/cb", code_challenge: challenge, code_challenge_method: "S256", state: "xyz" });
    const g = await oauth.grant(s, q);
    assert.ok(g.ok, JSON.stringify(g));
    const authCode = new URL(g.redirect).searchParams.get("code")!;
    const tok = await oauth.tokenRequest(new URLSearchParams({ grant_type: "authorization_code", code: authCode, client_id: clientId, redirect_uri: "https://app.example/cb", code_verifier: verifier }));
    assert.equal(tok.status, 200, JSON.stringify(tok.body));
    const access = String((tok.body as Record<string, Json>)["access_token"]);
    const principal = (await oauth.resolve(`Bearer ${access}`))!;
    assert.equal(principal.accountId, c.account.id);
    assert.equal((await oauth.tokenRequest(new URLSearchParams({ grant_type: "authorization_code", code: authCode, client_id: clientId, redirect_uri: "https://app.example/cb", code_verifier: verifier }))).status, 400, "a code is spent once, in SQL");
    assert.equal(await oauth.resolve(`Bearer ${access}`), null, "and the replay revoked the grant's tokens, in SQL");
    const created = await oauth.createManagedAgent(c.account, "Wren", ["gpt-5.2"]);
    assert.equal(created.status, 201, JSON.stringify(created.body));
    const keyRow = db.prepare("SELECT private_sealed FROM managed_keys WHERE handle = 'Wren'").get() as { private_sealed: string };
    assert.ok(keyRow.private_sealed.length > 40 && !keyRow.private_sealed.startsWith("MC4C"), "the private key is sealed, never stored plain");
    const signed = await oauth.signAs(principal, { protocol: "ecdysis/0.2", type: "review", claim: "ecd:x#C1", forecast: 0.5, rationale: "r".repeat(40), agent: { handle: "Wren" }, ts: now().toISOString() });
    assert.ok(signed.ok);
    assert.ok((await svc.record()).agents.get("Wren")!.managed, "the log says the archive held the pen");
    // Public profile names are unique in SQL (migration 0016): the index decides a race, and deletion frees the name.
    const p1 = await accounts.setProfile(s, "Dan-Hulme");
    assert.deepEqual(p1, { ok: true, name: "dan-hulme" });
    assert.equal((await accounts.accountByProfile("DAN-hulme"))?.id, c.account.id, "found by name, whatever the case");
    const r2 = await accounts.requestLink("eve@example.org", "2.2.2.2", null);
    assert.ok(r2.ok);
    const c2 = await accounts.completeLink(sent.at(-1)!.match(/t=([A-Za-z0-9_-]+)/)![1]!, r2.browser, "2.2.2.2");
    assert.ok(c2.ok);
    const s2 = (await accounts.session(c2.session))!;
    assert.deepEqual(await accounts.setProfile(s2, "dan-hulme"), { ok: false, status: 409, error: "that name is taken" });
    const d1 = new D1AccountStore(d1Over(db), now);
    await assert.rejects(d1.putPreferences(s2.account.id, { ...(await accounts.preferences(s2)), profile: "dan-hulme" }), /UNIQUE|constraint/i, "the index itself refuses a second holder");
    assert.equal((await accounts.preferences(s2)).profile, null, "and nothing of the loser's was written");
    assert.deepEqual(await accounts.setProfile(s2, "eve"), { ok: true, name: "eve" });
    assert.equal((await accounts.setProfile(s2, "eve")).ok, true, "re-saving one's own name is fine");
    await assert.rejects(d1.putAccount({ ...s2.account, emailHash: s.account.emailHash }), /UNIQUE|constraint/i, "an account row cannot take another's address or operator id; REPLACE would have deleted the other account");
    assert.equal((await d1.getAccount(s.account.id))?.operatorId, s.account.operatorId, "the first account is untouched");
    // The canary registry, through SQL: a row with a sealed outcome, listed, updated on reveal, deleted.
    const { D1CanaryStore } = await import("../src/store/v2/canaries-d1.js");
    const { CanaryRegistry } = await import("../src/api/v2/canaries.js");
    const cs = new D1CanaryStore(d1Over(db));
    const registry = new CanaryRegistry({ store: cs, accounts, v2: svc, now });
    const { signJson } = await import("../src/core/crypto.js");
    const extPayload = { protocol: "ecdysis/0.2", type: "claim.external", source: "doi:10.1000/known", quote: "a known result from the human literature", test: "a fresh run disagrees", agent: { handle: "Moth", publicKey: kp.publicKey }, ts: now().toISOString().replace(/\.\d{3}Z$/, "Z") } as unknown as Json;
    const ext = await svc.registerExternalClaim({ payload: extPayload, signature: await signJson(kp.privateKey, extPayload) });
    assert.equal(ext.status, 201, JSON.stringify(ext.body));
    const ref = String((ext.body as Record<string, Json>)["ref"]);
    assert.deepEqual(await registry.register({ claim: ref, outcome: "refuted", label: "the-first-canary", source: "a paper", revealAfter: null }, s.account.operatorId), { ok: true });
    const stored = db.prepare("SELECT * FROM steward_canaries").all() as Array<Record<string, unknown>>;
    assert.equal(stored.length, 1);
    // The label is long on purpose: a two-letter one ("A1") turned up by chance inside the base64url ciphertext once in CI.
    assert.doesNotMatch(JSON.stringify(stored[0]), new RegExp(`refuted|the-first-canary|paper|${ref.slice(4, 20)}`), "nothing readable in the table, not even the claim");
    assert.match(String(stored[0]!["key"]), /^[0-9a-f]{40}$/);
    assert.equal(stored[0]!["reveal_after"], null);
    const listed = await registry.list();
    assert.equal(listed[0]!.secret!.label, "the-first-canary");
    assert.equal(listed[0]!.secret!.outcome, "refuted");
    assert.equal(listed[0]!.secret!.claim, ref);
    const revealed = await registry.reveal(listed[0]!.key, s.account.operatorId);
    assert.ok(revealed.ok, JSON.stringify(revealed));
    assert.ok((db.prepare("SELECT revealed_at FROM steward_canaries").get() as { revealed_at: string | null }).revealed_at);
    assert.equal((await svc.record()).anchors.get(ref), false, "the sealed outcome, refuted, reached the log");
    assert.equal(await registry.remove(listed[0]!.key), true);
    assert.equal((db.prepare("SELECT COUNT(*) AS n FROM steward_canaries").get() as { n: number }).n, 0);
    await accounts.deleteAccount(s);
    assert.equal(await accounts.accountByProfile("dan-hulme"), null, "deletion frees the name");
    assert.deepEqual(await accounts.setProfile(s2, "dan-hulme"), { ok: true, name: "dan-hulme" });
    await accounts.deleteAccount(s2);
    assert.equal((db.prepare("SELECT COUNT(*) AS n FROM accounts").get() as { n: number }).n, 0);
    assert.equal((db.prepare("SELECT COUNT(*) AS n FROM account_sessions").get() as { n: number }).n, 0);
    assert.equal((db.prepare("SELECT COUNT(*) AS n FROM account_preferences").get() as { n: number }).n, 0);
    assert.equal((db.prepare("SELECT COUNT(*) AS n FROM account_links").get() as { n: number }).n, 0, "the links carrying the sealed address go too");
    const rec = await svc.record();
    assert.equal(rec.agents.get("Moth")!.operatorId, c.account.operatorId, "the log keeps the operator id and the agent");
  });
});

describe("the issues store against SQLite, every migration applied", { skip: !sqlite && "node:sqlite is not available" }, () => {
  it("keeps flags with their issues: once per envelope, counted per operator and day, with the outcomes of decided issues newest first", async () => {
    const { D1IssueStore } = await import("../src/store/v2/issues-d1.js");
    const db = migrated();
    const tables = (db.prepare("SELECT name FROM sqlite_master WHERE type = 'table'").all() as Array<{ name: string }>).map((t) => t.name);
    assert.ok(tables.includes("v2_flags"));
    const store = new D1IssueStore(d1Over(db));
    const issue = (id: string, status: "open" | "dismissed" | "acted", at: string) => store.putIssue({ id, kind: "quote-mismatch", subject: "ext:0123456789abcdef", severity: 1, detail: "Flagged by an agent.", source: "scout", status, openedAt: at, decidedAt: status === "open" ? null : at, decidedBy: status === "open" ? null : "op-s", note: null });
    const flag = (id: string, issueId: string, at: string, operatorId = "op-scout") => store.putFlag({ id, issueId, subject: "ext:0123456789abcdef", kind: "quote-mismatch", operatorId, handle: "Scout", stake: id === "f1", detail: "The quote is not in the source.", at });
    await issue("i1", "dismissed", "2026-10-03T09:00:00Z");
    await issue("i2", "acted", "2026-10-03T10:00:00Z");
    await issue("i3", "open", "2026-10-04T09:00:00Z");
    await flag("f1", "i1", "2026-10-03T09:00:00Z");
    await flag("f2", "i2", "2026-10-03T10:00:00Z");
    await flag("f3", "i3", "2026-10-04T09:00:00Z");
    await flag("f3", "i3", "2026-10-04T09:30:00Z"); // the same envelope again: ignored
    await flag("g1", "i3", "2026-10-04T09:10:00Z", "op-other");
    assert.ok(await store.hasFlag("f3"));
    assert.ok(!(await store.hasFlag("f4")));
    assert.deepEqual((await store.flagsFor("i3")).map((f) => [f.id, f.operatorId, f.stake, f.at]), [["f3", "op-scout", false, "2026-10-04T09:00:00Z"], ["g1", "op-other", false, "2026-10-04T09:10:00Z"]]);
    assert.equal((await store.flagsFor("i1"))[0]!.stake, true);
    assert.equal(await store.flagsSince("op-scout", "2026-10-04T00:00:00Z"), 1);
    assert.equal(await store.flagsSince("op-scout", "2026-10-01T00:00:00Z"), 3);
    assert.equal((await store.flagOn("i3", "op-other"))!.id, "g1");
    assert.equal(await store.flagOn("i1", "op-other"), null);
    assert.deepEqual(await store.flagOutcomes("op-scout", 10), ["acted", "dismissed"], "decided issues only, newest flag first");
  });
});
