/**
 * The canary registry (people-and-stewardship §7; v2 design: canaries are
 * external claims whose outcome was known before they were planted). The
 * registry is the steward's private list, OFF the log: which live claims
 * are canaries, what the known outcome is, where it comes from, and when the
 * steward means to reveal each. Nothing here is an input to any number; the
 * reveal itself is the log entry (`canary.reveal`, written by the service),
 * and the registry only remembers that it happened.
 *
 * What the table holds is designed so that a copy of it names no canary:
 * each row is keyed by a KEYED HASH of the claim ref (under the accounts
 * token key), and the ref itself, the known outcome, the label and the
 * source are SEALED together (AES-GCM under a key of its own, bound to the
 * row key, so a blob moved to another row does not open). Without the
 * accounts key the table is a list of random-looking rows with dates.
 * Revealing from the registry uses the sealed outcome, so a steward cannot
 * mistype the truth that will score every report on the claim.
 */

import type { Accounts } from "./accounts.js";
import type { V2Service } from "./service.js";

export const CANARY_REF = /^ext:[0-9a-f]{16}$/;
const ISO_DAY = /^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}(:\d{2})?Z)?$/;
const PURPOSE = "canary";

export interface CanaryRow {
  /** A keyed hash of the claim ref: the row's key. */
  key: string;
  /** {claim, outcome, label, source} as JSON, sealed and bound to `key`. */
  sealed: string;
  /** When the steward intends to reveal it (ISO), or null for "by hand, when ready". */
  revealAfter: string | null;
  registeredAt: string;
  /** The steward's operator id. */
  registeredBy: string;
  revealedAt: string | null;
}

export interface CanaryStore {
  list(): Promise<CanaryRow[]>;
  get(key: string): Promise<CanaryRow | null>;
  put(row: CanaryRow): Promise<void>;
  delete(key: string): Promise<void>;
}

export class MemoryCanaryStore implements CanaryStore {
  rows = new Map<string, CanaryRow>();
  async list() { return [...this.rows.values()].sort((a, b) => (a.registeredAt < b.registeredAt ? -1 : 1)); }
  async get(key: string) { return this.rows.get(key) ?? null; }
  async put(row: CanaryRow) { this.rows.set(row.key, { ...row }); }
  async delete(key: string) { this.rows.delete(key); }
}

export interface CanarySecret { claim: string; outcome: "confirmed" | "refuted"; label: string; source: string }

/** A registry row as the steward sees it: opened, with what the record says about the claim so far. */
export interface CanaryView {
  key: string;
  /** Null when the row cannot be opened (the accounts key changed): shown as such, never as an outcome. */
  secret: CanarySecret | null;
  revealAfter: string | null;
  registeredAt: string;
  registeredBy: string;
  revealedAt: string | null;
  /** On the record: reports (receipts and reviews) filed on it so far, and whether the log carries its reveal. */
  reports: number;
  onRecord: boolean;
  revealedOnLog: boolean;
  /** Due: the intended reveal time has passed and it is not yet revealed. */
  due: boolean;
}

export interface CanaryRegistryOptions {
  store: CanaryStore;
  accounts: Accounts;
  v2: V2Service;
  now?: () => Date;
}

export class CanaryRegistry {
  private now: () => Date;
  constructor(private o: CanaryRegistryOptions) { this.now = o.now ?? (() => new Date()); }

  /** The row key for a claim: a keyed hash, so the table's keys name nothing without the accounts key. */
  private async keyOf(claim: string): Promise<string> {
    return (await this.o.accounts.token_(PURPOSE, claim)).slice(0, 40);
  }

  /**
   * Register a live external claim as a canary. The claim must be on the
   * record and not yet revealed; the outcome is what the steward knows from
   * the human literature. Nothing is written to the log.
   */
  async register(input: { claim: string; outcome: string; label: string; source: string; revealAfter: string | null }, steward: string): Promise<{ ok: true } | { ok: false; status: number; error: string }> {
    const claim = input.claim.trim();
    if (!CANARY_REF.test(claim)) return { ok: false, status: 400, error: "a canary is a claim from human literature: ext:<16 hex>" };
    if (input.outcome !== "confirmed" && input.outcome !== "refuted") return { ok: false, status: 400, error: "outcome: confirmed (known to hold) or refuted (known to fail)" };
    const label = input.label.trim().slice(0, 80);
    const source = input.source.trim().slice(0, 300);
    if (!label) return { ok: false, status: 400, error: "label: a short name for your own eyes (never shown publicly)" };
    const revealAfter = input.revealAfter?.trim() || null;
    if (revealAfter !== null && (!ISO_DAY.test(revealAfter) || Number.isNaN(Date.parse(revealAfter)))) return { ok: false, status: 400, error: "reveal after: a date like 2026-12-01, or blank to reveal by hand" };
    const r = await this.o.v2.record();
    if (!r.claims.some((c) => c.ref === claim)) return { ok: false, status: 404, error: "no such claim on the record: register the external claim first (register_claim), then list it here" };
    if (r.anchors.has(claim)) return { ok: false, status: 409, error: "that claim is already revealed on the log" };
    const key = await this.keyOf(claim);
    if (await this.o.store.get(key)) return { ok: false, status: 409, error: "already in the registry" };
    const secret: CanarySecret = { claim, outcome: input.outcome, label, source };
    await this.o.store.put({ key, sealed: await this.o.accounts.sealBound(PURPOSE, key, JSON.stringify(secret)), revealAfter: revealAfter ? new Date(revealAfter).toISOString() : null, registeredAt: this.now().toISOString(), registeredBy: steward, revealedAt: null });
    return { ok: true };
  }

  /** Reveal a registered canary (by its row key) with its SEALED outcome: the one the steward wrote down when they planted it. */
  async reveal(key: string, steward: string): Promise<{ ok: true; note: string } | { ok: false; status: number; error: string }> {
    const row = await this.o.store.get(key.trim());
    if (!row) return { ok: false, status: 404, error: "not in the registry" };
    if (row.revealedAt) return { ok: false, status: 409, error: "already revealed" };
    const secret = await this.open(row);
    if (!secret) return { ok: false, status: 500, error: "the registry entry cannot be opened (was the accounts key changed?); nothing was revealed" };
    const r = await this.o.v2.revealCanary(secret.claim, secret.outcome, steward);
    if (r.status !== 200) return { ok: false, status: r.status, error: String((r.body as Record<string, unknown>)["error"] ?? "refused") };
    await this.o.store.put({ ...row, revealedAt: this.now().toISOString() });
    return { ok: true, note: String((r.body as Record<string, unknown>)["note"] ?? "Revealed.") };
  }

  /** Forget a registry row (by its row key). The log is untouched: a reveal already written stays written. */
  async remove(key: string): Promise<boolean> {
    const row = await this.o.store.get(key.trim());
    if (!row) return false;
    await this.o.store.delete(row.key);
    return true;
  }

  /** Open a row: the seal must be bound to this very row, and the ref inside must hash to the row's key. */
  private async open(row: CanaryRow): Promise<CanarySecret | null> {
    const text = await this.o.accounts.unsealBound(PURPOSE, row.key, row.sealed);
    if (!text) return null;
    try {
      const s = JSON.parse(text) as Partial<CanarySecret>;
      if (typeof s.claim !== "string" || !CANARY_REF.test(s.claim) || (s.outcome !== "confirmed" && s.outcome !== "refuted") || typeof s.label !== "string") return null;
      if ((await this.keyOf(s.claim)) !== row.key) return null;
      return { claim: s.claim, outcome: s.outcome, label: s.label, source: typeof s.source === "string" ? s.source : "" };
    } catch { return null; }
  }

  /** Every registered canary, opened for the steward, with the record's view of it. */
  async list(): Promise<CanaryView[]> {
    const rows = await this.o.store.list();
    if (!rows.length) return [];
    const r = await this.o.v2.record();
    const nowMs = this.now().getTime();
    const out: CanaryView[] = [];
    for (const row of rows) {
      const secret = await this.open(row);
      const revealedOnLog = secret ? r.anchors.has(secret.claim) : false;
      out.push({
        key: row.key, secret, revealAfter: row.revealAfter, registeredAt: row.registeredAt, registeredBy: row.registeredBy, revealedAt: row.revealedAt,
        reports: secret ? r.evidence.filter((e) => e.claim === secret.claim).length : 0,
        onRecord: secret ? r.claims.some((c) => c.ref === secret.claim) : false,
        revealedOnLog,
        due: !!secret && !row.revealedAt && !revealedOnLog && row.revealAfter !== null && Date.parse(row.revealAfter) <= nowMs,
      });
    }
    return out;
  }

  /** How many registered canaries are due for reveal (for the overview). */
  async due(): Promise<number> {
    return (await this.list()).filter((c) => c.due).length;
  }
}
