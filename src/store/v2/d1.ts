/**
 * The v2 store on D1: envelopes, bundles and withheld outputs (migration
 * 0013). The log rows come from the existing D1Store, which backs the
 * transparency log. Nothing here is an input to any number.
 */
import type { Json } from "../../core/canonical.js";
import type { V2Store } from "../../api/v2/service.js";
import type { Bundle, Outputs } from "../../core/v2/receipts.js";
import type { D1Store } from "../d1-store.js";

export class D1V2Store implements V2Store {
  constructor(private db: D1Database, private log: D1Store, private now: () => Date = () => new Date()) {}

  async putEnvelope(id: string, envelope: Json): Promise<void> {
    await this.db.prepare("INSERT OR IGNORE INTO v2_envelopes (id, envelope_json, created_at) VALUES (?1, ?2, ?3)").bind(id, JSON.stringify(envelope), this.now().toISOString()).run();
  }
  async getEnvelope(id: string): Promise<Json | null> {
    const r = await this.db.prepare("SELECT envelope_json FROM v2_envelopes WHERE id = ?1").bind(id).first<{ envelope_json: string }>();
    return r ? (JSON.parse(r.envelope_json) as Json) : null;
  }
  async putOutputs(key: string, outputs: Outputs): Promise<void> {
    await this.db.prepare("INSERT OR REPLACE INTO v2_outputs (key, outputs_json, created_at) VALUES (?1, ?2, ?3)").bind(key, JSON.stringify(outputs), this.now().toISOString()).run();
  }
  async getOutputs(key: string): Promise<Outputs | null> {
    const r = await this.db.prepare("SELECT outputs_json FROM v2_outputs WHERE key = ?1").bind(key).first<{ outputs_json: string }>();
    return r ? (JSON.parse(r.outputs_json) as Outputs) : null;
  }
  async putBundle(commitId: string, bundle: Bundle): Promise<void> {
    await this.db.prepare("INSERT OR IGNORE INTO v2_bundles (commit_id, bundle_json) VALUES (?1, ?2)").bind(commitId, JSON.stringify(bundle)).run();
  }
  async getBundle(commitId: string): Promise<Bundle | null> {
    const r = await this.db.prepare("SELECT bundle_json FROM v2_bundles WHERE commit_id = ?1").bind(commitId).first<{ bundle_json: string }>();
    return r ? (JSON.parse(r.bundle_json) as Bundle) : null;
  }
  async listLog(fromSeq: number, limit: number): Promise<Array<{ seq: number; ts: string; type: string; payload: Json }>> {
    return this.log.listLog(fromSeq, limit);
  }
}
