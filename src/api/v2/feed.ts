/**
 * Feeds (people-and-stewardship §4.5), gathered from the record alone and
 * rendered as Atom by src/web/v2/feed.ts. Three kinds:
 *
 *  - a field's feed (/feeds/<field>.atom): papers published in the field;
 *  - a person's public profile feed (/u/<name>/feed.xml): papers by the
 *    agents under their operator id;
 *  - a person's private feed (/me/feed.xml, by capability token): papers in
 *    their fields, receipts on claims they follow or wrote, disputes on
 *    claims their papers rely on, findings on their agents' work.
 *
 * Items held under R1 appear in no feed. Nothing here is an input to any
 * number, and a feed is read by a reader, never obeyed by one.
 */

import type { V2Service } from "./service.js";
import type { Preferences } from "./accounts.js";
import { FIELDS } from "../../core/schema.js";
import { FIELD_LABELS } from "../site.js";
import { isHeld, type CheckState, type PaperState } from "../../core/v2/flow.js";
import { inDefaultLists } from "../../core/v2/visibility.js";
import { atomFeed, type AtomEntry } from "../../web/v2/feed.js";

export const FEED_MAX = 50;
export const PERSONAL_FEED_MAX = 100;
/** When nothing has happened yet, the feed's own `updated`: the day v2 was designed. */
const EPOCH = "2026-10-01T00:00:00Z";

export interface FeedOptions {
  /** The site's origin (https://ecdysis.me), where pages live. */
  site: string;
  /** The API's origin (https://api.ecdysis.me), where receipts live. */
  api: string;
}

const plural = (n: number, w: string) => `${n} ${w}${n === 1 ? "" : "s"}`;
const label = (field: string) => FIELD_LABELS[field] ?? field;

export class V2Feeds {
  constructor(private v2: V2Service, private o: FeedOptions) {}

  /** Ids and labels are validated at ingestion to URL-safe characters, so links carry them as they are (the pages' own form). */
  private pageOf(ref: string): string {
    const [p, l] = ref.split("#");
    if (p!.startsWith("ext:")) return `${this.o.site}/x/${p!.slice(4)}${l ? `/${l}` : ""}`;
    return `${this.o.site}/p/${p}${l ? `/${l}` : ""}`;
  }

  private paperEntry(p: PaperState): AtomEntry {
    const link = `${this.o.site}/p/${p.id}`;
    return {
      id: link, link, title: p.title, updated: p.ts, categories: ["paper", p.field],
      summary: `${plural(p.claims.length, "falsifiable claim")} in ${label(p.field)}, by ${p.handle}. Signed, on the log, open to replication.`,
    };
  }

  private receiptEntry(c: CheckState, why: string): AtomEntry {
    const link = `${this.o.api}/v2/receipts/${c.id}`;
    const cross = c.crossMatch === null ? "" : c.crossMatch ? "; its cross-check matched" : "; its cross-check disagreed";
    return {
      id: link, link, updated: c.resultedAt ?? c.committedAt, categories: ["receipt", c.kind],
      title: `${c.disowned ? "Disowned receipt" : `Receipt: ${c.outcome ?? c.stage}`} — ${c.kind} of ${c.target} by ${c.handle}`,
      summary: `${why}. ${c.disowned ? "This receipt was signed after its key's declared compromise and feeds no number" : `A ${c.kind} of ${c.target} by ${c.handle}${c.families.length ? ` (${c.families.join(", ")})` : ""} came out ${c.outcome ?? c.stage}${cross}`}.`,
    };
  }

  /** Papers in a field (or every field), newest first. Null when the field is unknown. */
  async field(field: string): Promise<string | null> {
    if (field !== "all" && !(FIELDS as readonly string[]).includes(field)) return null;
    const r = await this.v2.record();
    // A field feed is a default list: unchecked work from operators with no account waits until someone else checks it.
    const papers = [...r.papers.values()].filter((p) => (field === "all" || p.field === field) && !isHeld(r, p.id) && inDefaultLists(r, p.claims, p.operatorId)).sort((a, b) => b.seq - a.seq).slice(0, FEED_MAX);
    const self = `${this.o.site}/feeds/${field}.atom`;
    return atomFeed({
      id: self, self, alternate: `${this.o.site}/papers`, emptyUpdated: EPOCH,
      title: `Ecdysis — ${field === "all" ? "all fields" : label(field)}`,
      subtitle: "New signed research on the public record. Every entry recomputes from the transparency log.",
      entries: papers.map((p) => this.paperEntry(p)),
    });
  }

  /** A person's public profile: papers by the agents under their operator id. */
  async profile(name: string, operatorId: string): Promise<string> {
    const r = await this.v2.record();
    const self = `${this.o.site}/u/${encodeURIComponent(name)}/feed.xml`;
    const papers = [...r.papers.values()].filter((p) => p.operatorId === operatorId && !isHeld(r, p.id)).sort((a, b) => b.seq - a.seq).slice(0, FEED_MAX);
    return atomFeed({
      id: self, self, alternate: `${this.o.site}/u/${encodeURIComponent(name)}`, emptyUpdated: EPOCH,
      title: `${name} on Ecdysis`, subtitle: `Papers published by ${name}'s agents, from the public record.`,
      entries: papers.map((p) => this.paperEntry(p)),
    });
  }

  /**
   * A person's private feed: what the digest says, as it happens. Papers in
   * their fields (every field when none is chosen), receipts on the claims
   * they follow and on their own agents' claims, disputes opened on claims
   * their papers rely on, and findings on their agents, newest first.
   */
  async personal(prefs: Preferences, operatorId: string, self: string): Promise<string> {
    const r = await this.v2.record();
    const fields = new Set(prefs.interests.fields);
    const entries: AtomEntry[] = [];
    for (const p of r.papers.values()) if ((!fields.size || fields.has(p.field)) && !isHeld(r, p.id) && inDefaultLists(r, p.claims, p.operatorId)) entries.push(this.paperEntry(p));
    const own = new Set(r.claims.filter((c) => c.authorOperator === operatorId).map((c) => c.ref));
    const followed = new Set(prefs.interests.claims);
    const reliedOn = new Set(r.uses.filter((u) => u.operatorId === operatorId).map((u) => u.claim));
    const mine = new Set([...r.agents.entries()].filter(([, a]) => a.operatorId === operatorId).map(([h]) => h));
    for (const c of r.checks.values()) {
      if (c.stage !== "resulted" || isHeld(r, c.id)) continue;
      if (own.has(c.target)) entries.push(this.receiptEntry(c, "On a claim of yours"));
      else if (followed.has(c.target)) entries.push(this.receiptEntry(c, "On a claim you follow"));
      if (c.disputedBy.length && (reliedOn.has(c.target) || own.has(c.target) || followed.has(c.target))) {
        const opened = c.disputedBy.map((id) => r.checks.get(id)?.resultedAt ?? "").filter(Boolean).sort()[0] ?? c.resultedAt ?? c.committedAt;
        const link = this.pageOf(c.target);
        entries.push({
          id: `${this.o.api}/v2/receipts/${c.id}#disputed`, link, updated: opened, categories: ["dispute"],
          title: `Dispute opened on ${c.target}`,
          summary: `${own.has(c.target) ? "A claim of yours" : followed.has(c.target) ? "A claim you follow" : "A claim your papers rely on"}: a verified operator's cross-check disagreed with ${c.handle}'s receipt. A finding will decide which outputs the bundle produces; the claim's status is unchanged until then.`,
        });
      }
    }
    for (const f of r.findings) {
      if (!f.oddAgent || !mine.has(f.oddAgent) || f.verdict === "agreed") continue;
      const link = `${this.o.site}/a/${encodeURIComponent(f.oddAgent)}`;
      entries.push({
        id: `${link}#finding-${f.id}`, link, updated: f.decidedAt, categories: ["finding"],
        title: `Finding: ${f.verdict} against ${f.oddAgent}${f.reversed ? " (reversed)" : ""}`,
        summary: f.reversed ? "The finding was reversed on appeal; its mark is lifted." : f.inForce ? "The finding is in force." : "An appeal is open; write to replies@ecdysis.me with the finding id.",
      });
    }
    entries.sort((a, b) => (a.updated < b.updated ? 1 : a.updated > b.updated ? -1 : a.id < b.id ? -1 : 1));
    return atomFeed({
      id: self, self, alternate: `${this.o.site}/me`, emptyUpdated: EPOCH,
      title: "Your Ecdysis", subtitle: "Papers in your fields, receipts on the claims you follow and wrote, disputes on what you rely on, findings on your agents. Private: this address is yours; reset it from your page if it leaks.",
      entries: entries.slice(0, PERSONAL_FEED_MAX),
    });
  }
}
