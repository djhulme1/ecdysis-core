/**
 * The account store on D1 (migration 0014). Off the log; deletable.
 */
import type { AccountRow, AccountStore, MagicLinkRow, PairingRow, Preferences, SessionRow } from "../../api/v2/accounts.js";

const DAY_MS = 24 * 3600 * 1000;

export class D1AccountStore implements AccountStore {
  constructor(private db: D1Database, private now: () => Date = () => new Date()) {}

  private rowToAccount(r: Record<string, unknown>): AccountRow {
    return { id: String(r["id"]), emailHash: String(r["email_hash"]), emailSealed: String(r["email_sealed"]), operatorId: String(r["operator_id"]), role: r["role"] === "steward" ? "steward" : "member", createdAt: String(r["created_at"]) };
  }
  async getAccount(id: string) {
    const r = await this.db.prepare("SELECT * FROM accounts WHERE id = ?1").bind(id).first<Record<string, unknown>>();
    return r ? this.rowToAccount(r) : null;
  }
  async getAccountByEmailHash(h: string) {
    const r = await this.db.prepare("SELECT * FROM accounts WHERE email_hash = ?1").bind(h).first<Record<string, unknown>>();
    return r ? this.rowToAccount(r) : null;
  }
  async getAccountByOperator(op: string) {
    const r = await this.db.prepare("SELECT * FROM accounts WHERE operator_id = ?1").bind(op).first<Record<string, unknown>>();
    return r ? this.rowToAccount(r) : null;
  }
  /** Upsert on the id only: a row whose email hash or operator id is another account's is refused, never replaced (REPLACE would delete that other account). */
  async putAccount(a: AccountRow) {
    await this.db.prepare("INSERT INTO accounts (id, email_hash, email_sealed, operator_id, role, created_at) VALUES (?1, ?2, ?3, ?4, ?5, ?6) ON CONFLICT(id) DO UPDATE SET email_hash = excluded.email_hash, email_sealed = excluded.email_sealed, operator_id = excluded.operator_id, role = excluded.role, created_at = excluded.created_at")
      .bind(a.id, a.emailHash, a.emailSealed, a.operatorId, a.role, a.createdAt).run();
  }
  async createAccount(a: AccountRow) {
    const r = await this.db.prepare("INSERT OR IGNORE INTO accounts (id, email_hash, email_sealed, operator_id, role, created_at) VALUES (?1, ?2, ?3, ?4, ?5, ?6)")
      .bind(a.id, a.emailHash, a.emailSealed, a.operatorId, a.role, a.createdAt).run();
    return (r.meta?.changes ?? 0) > 0;
  }
  async deleteAccount(id: string, emailHash: string) {
    await this.db.batch([
      this.db.prepare("DELETE FROM account_sessions WHERE account_id = ?1").bind(id),
      this.db.prepare("DELETE FROM account_pairings WHERE account_id = ?1").bind(id),
      this.db.prepare("DELETE FROM account_preferences WHERE account_id = ?1").bind(id),
      this.db.prepare("DELETE FROM account_alerts WHERE account_id = ?1").bind(id),
      this.db.prepare("DELETE FROM account_links WHERE email_hash = ?1").bind(emailHash),
      this.db.prepare("DELETE FROM account_events WHERE bucket = ?1").bind(`link:e:${emailHash}`),
      this.db.prepare("DELETE FROM accounts WHERE id = ?1").bind(id),
    ]);
  }

  async putMagicLink(l: MagicLinkRow) {
    await this.db.prepare("INSERT OR REPLACE INTO account_links (hash, email_hash, email_sealed, browser_hash, created_at, expires_at, used_at) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7)")
      .bind(l.hash, l.emailHash, l.emailSealed, l.browserHash, l.createdAt, l.expiresAt, l.usedAt).run();
    // Links expire in minutes; forget them after a day.
    await this.db.prepare("DELETE FROM account_links WHERE expires_at < ?1").bind(new Date(this.now().getTime() - DAY_MS).toISOString()).run();
  }
  async getMagicLink(hash: string) {
    const r = await this.db.prepare("SELECT * FROM account_links WHERE hash = ?1").bind(hash).first<Record<string, unknown>>();
    return r ? { hash: String(r["hash"]), emailHash: String(r["email_hash"]), emailSealed: String(r["email_sealed"]), browserHash: String(r["browser_hash"]), createdAt: String(r["created_at"]), expiresAt: String(r["expires_at"]), usedAt: r["used_at"] ? String(r["used_at"]) : null } : null;
  }
  /** Spends the link; false when it was already spent (two requests racing for one link: exactly one wins). */
  async useMagicLink(hash: string, usedAt: string) {
    const r = await this.db.prepare("UPDATE account_links SET used_at = ?2 WHERE hash = ?1 AND used_at IS NULL").bind(hash, usedAt).run();
    return (r.meta?.changes ?? 0) > 0;
  }

  async putSession(s: SessionRow) {
    await this.db.prepare("INSERT OR REPLACE INTO account_sessions (hash, account_id, created_at, expires_at, signed_in_at) VALUES (?1, ?2, ?3, ?4, ?5)")
      .bind(s.hash, s.accountId, s.createdAt, s.expiresAt, s.signedInAt).run();
  }
  async getSession(hash: string) {
    const r = await this.db.prepare("SELECT * FROM account_sessions WHERE hash = ?1").bind(hash).first<Record<string, unknown>>();
    return r ? { hash: String(r["hash"]), accountId: String(r["account_id"]), createdAt: String(r["created_at"]), expiresAt: String(r["expires_at"]), signedInAt: String(r["signed_in_at"]) } : null;
  }
  async deleteSession(hash: string) { await this.db.prepare("DELETE FROM account_sessions WHERE hash = ?1").bind(hash).run(); }
  async deleteSessionsFor(accountId: string) { await this.db.prepare("DELETE FROM account_sessions WHERE account_id = ?1").bind(accountId).run(); }

  async putPairing(p: PairingRow) {
    await this.db.prepare("INSERT OR REPLACE INTO account_pairings (hash, account_id, created_at, expires_at, used_at) VALUES (?1, ?2, ?3, ?4, ?5)")
      .bind(p.hash, p.accountId, p.createdAt, p.expiresAt, p.usedAt).run();
    await this.db.prepare("DELETE FROM account_pairings WHERE expires_at < ?1").bind(new Date(this.now().getTime() - 7 * DAY_MS).toISOString()).run();
  }
  async getPairing(hash: string) {
    const r = await this.db.prepare("SELECT * FROM account_pairings WHERE hash = ?1").bind(hash).first<Record<string, unknown>>();
    return r ? { hash: String(r["hash"]), accountId: String(r["account_id"]), createdAt: String(r["created_at"]), expiresAt: String(r["expires_at"]), usedAt: r["used_at"] ? String(r["used_at"]) : null } : null;
  }
  async usePairing(hash: string, usedAt: string) {
    const r = await this.db.prepare("UPDATE account_pairings SET used_at = ?2 WHERE hash = ?1 AND used_at IS NULL").bind(hash, usedAt).run();
    return (r.meta?.changes ?? 0) > 0;
  }

  async getPreferences(accountId: string) {
    const r = await this.db.prepare("SELECT prefs_json FROM account_preferences WHERE account_id = ?1").bind(accountId).first<{ prefs_json: string }>();
    return r ? (JSON.parse(r.prefs_json) as Preferences) : null;
  }
  /**
   * Throws (a UNIQUE constraint, migration 0016) when the profile name is another account's, so names stay unique under
   * concurrent claims. An upsert on the account id, deliberately not INSERT OR REPLACE: REPLACE resolves ANY unique
   * violation by deleting the offending row, which would let a second claimant erase the first holder's preferences.
   */
  async putPreferences(accountId: string, prefs: Preferences) {
    await this.db.prepare("INSERT INTO account_preferences (account_id, prefs_json, updated_at) VALUES (?1, ?2, ?3) ON CONFLICT(account_id) DO UPDATE SET prefs_json = excluded.prefs_json, updated_at = excluded.updated_at")
      .bind(accountId, JSON.stringify(prefs), this.now().toISOString()).run();
  }
  async getPreferencesJson(accountId: string) {
    const r = await this.db.prepare("SELECT prefs_json FROM account_preferences WHERE account_id = ?1").bind(accountId).first<{ prefs_json: string }>();
    return r ? r.prefs_json : null;
  }
  /** Compare-and-set on the stored text: the UPDATE matches only the row as the caller saw it; a first write is an INSERT that yields to any row already there. */
  async putPreferencesIf(accountId: string, prefs: Preferences, expectedJson: string | null) {
    const at = this.now().toISOString();
    if (expectedJson === null) {
      const r = await this.db.prepare("INSERT OR IGNORE INTO account_preferences (account_id, prefs_json, updated_at) VALUES (?1, ?2, ?3)").bind(accountId, JSON.stringify(prefs), at).run();
      if ((r.meta?.changes ?? 0) > 0) return true;
      // Ignored: either a row appeared meanwhile (the caller re-reads) or the profile name is another account's (a refusal).
      if ((await this.getPreferencesJson(accountId)) === null) throw new Error("UNIQUE constraint failed: account_preferences_profile");
      return false;
    }
    const r = await this.db.prepare("UPDATE account_preferences SET prefs_json = ?2, updated_at = ?3 WHERE account_id = ?1 AND prefs_json = ?4").bind(accountId, JSON.stringify(prefs), at, expectedJson).run();
    return (r.meta?.changes ?? 0) > 0;
  }
  async getAccountByProfile(name: string) {
    const r = await this.db.prepare("SELECT a.* FROM account_preferences p JOIN accounts a ON a.id = p.account_id WHERE json_extract(p.prefs_json, '$.profile') = ?1").bind(name).first<Record<string, unknown>>();
    return r ? this.rowToAccount(r) : null;
  }

  async listAlertAccounts() {
    const rs = await this.db.prepare("SELECT a.*, p.prefs_json FROM account_preferences p JOIN accounts a ON a.id = p.account_id WHERE json_array_length(json_extract(p.prefs_json, '$.notifications.alerts')) > 0 LIMIT 5000").all<Record<string, unknown>>();
    return (rs.results ?? []).map((r) => ({ account: this.rowToAccount(r), alerts: ((JSON.parse(String(r["prefs_json"])) as Preferences).notifications.alerts) }));
  }
  async listDigestAccounts() {
    const rs = await this.db.prepare("SELECT a.*, p.prefs_json FROM account_preferences p JOIN accounts a ON a.id = p.account_id WHERE json_extract(p.prefs_json, '$.notifications.digest') IN ('daily', 'weekly') LIMIT 5000").all<Record<string, unknown>>();
    return (rs.results ?? []).map((r) => ({ account: this.rowToAccount(r), prefs: JSON.parse(String(r["prefs_json"])) as Preferences }));
  }
  async wasSent(accountId: string, key: string) {
    const r = await this.db.prepare("SELECT 1 AS one FROM account_alerts WHERE account_id = ?1 AND key = ?2").bind(accountId, key).first<{ one: number }>();
    return !!r;
  }
  async markSent(accountId: string, key: string, atIso: string) {
    await this.db.prepare("INSERT OR IGNORE INTO account_alerts (account_id, key, at) VALUES (?1, ?2, ?3)").bind(accountId, key, atIso).run();
  }

  async countEvents(bucket: string, sinceIso: string) {
    const r = await this.db.prepare("SELECT COUNT(*) AS n FROM account_events WHERE bucket = ?1 AND at >= ?2").bind(bucket, sinceIso).first<{ n: number }>();
    return Number(r?.n ?? 0);
  }
  async recordEvent(bucket: string, atIso: string) {
    await this.db.prepare("INSERT INTO account_events (bucket, at) VALUES (?1, ?2)").bind(bucket, atIso).run();
    await this.db.prepare("DELETE FROM account_events WHERE at < ?1").bind(new Date(this.now().getTime() - DAY_MS).toISOString()).run();
  }
}
