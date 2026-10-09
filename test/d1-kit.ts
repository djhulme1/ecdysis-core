/**
 * SQLite (what D1 is built on) as the slice of D1's binding the stores use, with every migration applied in order: for the
 * tests that run the D1 stores' real SQL (d1-sqlite.test.ts) and the Worker's own handlers (cron.test.ts).
 */
import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";

export type Sqlite = typeof import("node:sqlite");
export let sqlite: Sqlite | null = null;
try {
  sqlite = await import("node:sqlite");
} catch {
  sqlite = null; // older Node: skipped, never silently passed
}

/** The slice of D1's binding the store uses, over node:sqlite. Refuses undefined, as D1 does. */
export function d1Over(db: InstanceType<Sqlite["DatabaseSync"]>): D1Database {
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

export function migrated(): InstanceType<Sqlite["DatabaseSync"]> {
  const db = new sqlite!.DatabaseSync(":memory:");
  const dir = join(import.meta.dirname, "..", "migrations");
  for (const f of readdirSync(dir).filter((x) => x.endsWith(".sql")).sort()) db.exec(readFileSync(join(dir, f), "utf8"));
  return db;
}
