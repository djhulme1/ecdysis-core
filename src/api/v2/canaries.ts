/**
 * The canary registry (people-and-stewardship §7; v2 design: canaries are
 * external claims whose outcome was known before they were planted). The
 * registry is the steward's private list, OFF the log: which live claims
 * are canaries, what the known outcome is, where it comes from, and when the
 * steward means to reveal each. Nothing here is an input to any number; the
 * reveal itself is the log entry (`canary.reveal`, written by the service),
 * and the registry only remembers that it happened.
 *
 * The known outcome, the label and the source are kept SEALED (AES-GCM under
 * the accounts key), so a copy of the database alone names no canary: a live
 * canary that could be told apart from any other external claim would be
 * worthless. Revealing from the registry uses the sealed outcome, so a
 * steward cannot mistype the truth that will score every report on it.
 */

import type { Accounts } from "./accounts.js";
import type { V2Service } from "./service.js";

export const CANARY_REF = /^ext:[0-9a-f]{16}#C1$/;
const ISO_DAY = /^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}(:\d{2})?Z)?$/;

export interface CanaryRow {
  claim: string;
  /** {outcome, label, source} as JSON, sealed. */
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
  get(claim: string): Promise<CanaryRow | null>;
  put(row: CanaryRow): Promise<void>;
  delete(claim: string): Promise<void>;
}

export class MemoryCanaryStore implements CanaryStore {
  rows = new Map<string, CanaryRow>();
  async list() { return [...this.rows.values()].sort((a, b) => (a.registeredAt < b.registeredAt ? -1 : 1)); }
  async get(claim: string) { return this.rows.get(claim) ?? null; }
  async put(row: CanaryRow) { this.rows.set(row.claim, { ...row }); }
  async delete(claim: string) { this.rows.delete(claim); }
}

export interface CanarySecret { outcome: "confirmed" | "refuted"; label: string; source: string }

/** A registry row as the steward sees it: opened, with what the record says about the claim so far. */
export interface CanaryView extends CanarySecret {
  claim: string;
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

  /**
   * Register a live external claim as a canary. The claim must be on the
   * record and not yet revealed; the outcome is what the steward knows from
   * the human literature. Nothing is written to the log.
   */
  async register(input: { claim: string; outcome: string; label: string; source: string; revealAfter: string | null }, steward: string): Promise<{ ok: true } | { ok: false; status: number; error: string }> {
    const claim = input.claim.trim();
    if (!CANARY_REF.test(claim)) return { ok: false, status: 400, error: "a canary is an external claim: ext:<16 hex>#C1" };
    if (input.outcome !== "confirmed" && input.outcome !== "refuted") return { ok: false, status: 400, error: "outcome: confirmed (known to hold) or refuted (known to fail)" };
    const label = input.label.trim().slice(0, 80);
    const source = input.source.trim().slice(0, 300);
    if (!label) return { ok: false, status: 400, error: "label: a short name for your own eyes (never shown publicly)" };
    const revealAfter = input.revealAfter?.trim() || null;
    if (revealAfter !== null && (!ISO_DAY.test(revealAfter) || Number.isNaN(Date.parse(revealAfter)))) return { ok: false, status: 400, error: "reveal after: a date like 2026-12-01, or blank to reveal by hand" };
    const r = await this.o.v2.record();
    if (!r.claims.some((c) => c.ref === claim)) return { ok: false, status: 404, error: "no such claim on the record: register the external claim first (register_claim), then list it here" };
    if (r.anchors.has(claim)) return { ok: false, status: 409, error: "that claim is already revealed on the log" };
    if (await this.o.store.get(claim)) return { ok: false, status: 409, error: "already in the registry" };
    const secret: CanarySecret = { outcome: input.outcome, label, source };
    await this.o.store.put({ claim, sealed: await this.o.accounts.seal(JSON.stringify(secret)), revealAfter: revealAfter ? new Date(revealAfter).toISOString() : null, registeredAt: this.now().toISOString(), registeredBy: steward, revealedAt: null });
    return { ok: true };
  }

  /** Reveal a registered canary with its SEALED outcome: the one the steward wrote down when they planted it. */
  async reveal(claim: string, steward: string): Promise<{ ok: true; note: string } | { ok: false; status: number; error: string }> {
    const row = await this.o.store.get(claim.trim());
    if (!row) return { ok: false, status: 404, error: "not in the registry" };
    if (row.revealedAt) return { ok: false, status: 409, error: "already revealed" };
    const secret = await this.open(row);
    if (!secret) return { ok: false, status: 500, error: "the registry entry cannot be opened (was the accounts key changed?); reveal by hand from the Evidence page if you still know the outcome" };
    const r = await this.o.v2.revealCanary(row.claim, secret.outcome, steward);
    if (r.status !== 200) return { ok: false, status: r.status, error: String((r.body as Record<string, unknown>)["error"] ?? "refused") };
    await this.o.store.put({ ...row, revealedAt: this.now().toISOString() });
    return { ok: true, note: String((r.body as Record<string, unknown>)["note"] ?? "Revealed.") };
  }

  /** Forget a registry row. The log is untouched: a reveal already written stays written. */
  async remove(claim: string): Promise<boolean> {
    const row = await this.o.store.get(claim.trim());
    if (!row) return false;
    await this.o.store.delete(row.claim);
    return true;
  }

  private async open(row: CanaryRow): Promise<CanarySecret | null> {
    const text = await this.o.accounts.unseal(row.sealed);
    if (!text) return null;
    try {
      const s = JSON.parse(text) as Partial<CanarySecret>;
      if ((s.outcome !== "confirmed" && s.outcome !== "refuted") || typeof s.label !== "string") return null;
      return { outcome: s.outcome, label: s.label, source: typeof s.source === "string" ? s.source : "" };
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
      const secret = (await this.open(row)) ?? { outcome: "confirmed" as const, label: "(cannot be opened)", source: "" };
      const revealedOnLog = r.anchors.has(row.claim);
      out.push({
        ...secret, claim: row.claim, revealAfter: row.revealAfter, registeredAt: row.registeredAt, registeredBy: row.registeredBy, revealedAt: row.revealedAt,
        reports: r.evidence.filter((e) => e.claim === row.claim).length, onRecord: r.claims.some((c) => c.ref === row.claim), revealedOnLog,
        due: !row.revealedAt && !revealedOnLog && row.revealAfter !== null && Date.parse(row.revealAfter) <= nowMs,
      });
    }
    return out;
  }

  /** How many registered canaries are due for reveal (for the overview). */
  async due(): Promise<number> {
    return (await this.list()).filter((c) => c.due).length;
  }
}
