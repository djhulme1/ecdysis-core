/**
 * The OAuth and managed-key store on D1 (migration 0015). Off the log.
 */
import type { ClientRow, CodeRow, ManagedKeyRow, OAuthStore, TokenRow } from "../../api/v2/oauth.js";

export class D1OAuthStore implements OAuthStore {
  constructor(private db: D1Database, private now: () => Date = () => new Date()) {}

  async putClient(c: ClientRow) {
    await this.db.prepare("INSERT OR REPLACE INTO oauth_clients (id, name, redirect_uris_json, created_at) VALUES (?1, ?2, ?3, ?4)").bind(c.id, c.name, JSON.stringify(c.redirectUris), c.createdAt).run();
  }
  async getClient(id: string) {
    const r = await this.db.prepare("SELECT * FROM oauth_clients WHERE id = ?1").bind(id).first<Record<string, unknown>>();
    return r ? { id: String(r["id"]), name: String(r["name"]), redirectUris: JSON.parse(String(r["redirect_uris_json"])) as string[], createdAt: String(r["created_at"]) } : null;
  }
  async countClients(sinceIso: string, ipHash: string) {
    const r = await this.db.prepare("SELECT COUNT(*) AS n FROM oauth_registrations WHERE ip_hash = ?1 AND at >= ?2").bind(ipHash, sinceIso).first<{ n: number }>();
    return Number(r?.n ?? 0);
  }
  async recordClient(ipHash: string, atIso: string) {
    await this.db.prepare("INSERT INTO oauth_registrations (ip_hash, at) VALUES (?1, ?2)").bind(ipHash, atIso).run();
    // Registrations older than a day say nothing any more.
    await this.db.prepare("DELETE FROM oauth_registrations WHERE at < ?1").bind(new Date(this.now().getTime() - 24 * 3600 * 1000).toISOString()).run();
  }

  async putCode(c: CodeRow) {
    await this.db.prepare("INSERT OR REPLACE INTO oauth_codes (hash, grant_id, client_id, account_id, redirect_uri, code_challenge, scope, resource, created_at, expires_at, used_at) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11)")
      .bind(c.hash, c.grantId, c.clientId, c.accountId, c.redirectUri, c.codeChallenge, c.scope, c.resource, c.createdAt, c.expiresAt, c.usedAt).run();
    await this.db.prepare("DELETE FROM oauth_codes WHERE expires_at < ?1").bind(new Date(this.now().getTime() - 24 * 3600 * 1000).toISOString()).run();
  }
  async getCode(hash: string) {
    const r = await this.db.prepare("SELECT * FROM oauth_codes WHERE hash = ?1").bind(hash).first<Record<string, unknown>>();
    return r ? { hash: String(r["hash"]), grantId: String(r["grant_id"]), clientId: String(r["client_id"]), accountId: String(r["account_id"]), redirectUri: String(r["redirect_uri"]), codeChallenge: String(r["code_challenge"]), scope: String(r["scope"]), resource: String(r["resource"]), createdAt: String(r["created_at"]), expiresAt: String(r["expires_at"]), usedAt: r["used_at"] ? String(r["used_at"]) : null } : null;
  }
  async useCode(hash: string, usedAt: string) {
    const r = await this.db.prepare("UPDATE oauth_codes SET used_at = ?2 WHERE hash = ?1 AND used_at IS NULL").bind(hash, usedAt).run();
    return (r.meta?.changes ?? 0) > 0;
  }

  async putToken(t: TokenRow) {
    await this.db.prepare("INSERT OR REPLACE INTO oauth_tokens (hash, grant_id, kind, account_id, client_id, scope, resource, created_at, expires_at, revoked_at) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10)")
      .bind(t.hash, t.grantId, t.kind, t.accountId, t.clientId, t.scope, t.resource, t.createdAt, t.expiresAt, t.revokedAt).run();
    await this.db.prepare("DELETE FROM oauth_tokens WHERE expires_at < ?1").bind(new Date(this.now().getTime() - 7 * 24 * 3600 * 1000).toISOString()).run();
  }
  async getToken(hash: string) {
    const r = await this.db.prepare("SELECT * FROM oauth_tokens WHERE hash = ?1").bind(hash).first<Record<string, unknown>>();
    return r ? { hash: String(r["hash"]), grantId: String(r["grant_id"]), kind: r["kind"] === "refresh" ? "refresh" as const : "access" as const, accountId: String(r["account_id"]), clientId: String(r["client_id"]), scope: String(r["scope"]), resource: String(r["resource"]), createdAt: String(r["created_at"]), expiresAt: String(r["expires_at"]), revokedAt: r["revoked_at"] ? String(r["revoked_at"]) : null } : null;
  }
  async revokeToken(hash: string, atIso: string) {
    const r = await this.db.prepare("UPDATE oauth_tokens SET revoked_at = ?2 WHERE hash = ?1 AND revoked_at IS NULL").bind(hash, atIso).run();
    return (r.meta?.changes ?? 0) > 0;
  }
  async revokeGrant(grantId: string, atIso: string) {
    await this.db.prepare("UPDATE oauth_tokens SET revoked_at = ?2 WHERE grant_id = ?1 AND revoked_at IS NULL").bind(grantId, atIso).run();
  }
  async revokeTokensFor(accountId: string, atIso: string) {
    await this.db.prepare("UPDATE oauth_tokens SET revoked_at = ?2 WHERE account_id = ?1 AND revoked_at IS NULL").bind(accountId, atIso).run();
  }

  async putManagedKey(k: ManagedKeyRow) {
    await this.db.prepare("INSERT OR REPLACE INTO managed_keys (handle, account_id, public_key, private_sealed, created_at, destroyed_at) VALUES (?1, ?2, ?3, ?4, ?5, ?6)")
      .bind(k.handle, k.accountId, k.publicKey, k.privateSealed, k.createdAt, k.destroyedAt).run();
  }
  private rowToKey(r: Record<string, unknown>): ManagedKeyRow {
    return { handle: String(r["handle"]), accountId: String(r["account_id"]), publicKey: String(r["public_key"]), privateSealed: String(r["private_sealed"]), createdAt: String(r["created_at"]), destroyedAt: r["destroyed_at"] ? String(r["destroyed_at"]) : null };
  }
  async getManagedKey(handle: string) {
    const r = await this.db.prepare("SELECT * FROM managed_keys WHERE handle = ?1").bind(handle).first<Record<string, unknown>>();
    return r ? this.rowToKey(r) : null;
  }
  async listManagedKeys(accountId: string) {
    const rs = await this.db.prepare("SELECT * FROM managed_keys WHERE account_id = ?1 ORDER BY created_at").bind(accountId).all<Record<string, unknown>>();
    return (rs.results ?? []).map((r) => this.rowToKey(r));
  }
  async destroyManagedKey(handle: string, atIso: string) {
    await this.db.prepare("UPDATE managed_keys SET private_sealed = '', destroyed_at = ?2 WHERE handle = ?1").bind(handle, atIso).run();
  }
}
