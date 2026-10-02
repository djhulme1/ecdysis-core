/**
 * The v2 public pages' handler: gathers from the record and the store,
 * renders with src/web/v2/pages.ts. GET only; cached briefly (every number
 * is a function of the log, so a stale page is merely a little old).
 */

import type { V2Service } from "./service.js";
import type { PaperV2Payload } from "../../core/v2/paper.js";
import type { Json } from "../../core/canonical.js";
import { claimPageV2, frontierPageV2, missingPageV2, observatoryPageV2, papersPageV2, paperPageV2, type ClaimViewV2, type FrontierViewV2, type ObservatoryViewV2, type PaperViewV2 } from "../../web/v2/pages.js";

export const PAGE_HEADERS: Record<string, string> = {
  "content-type": "text/html; charset=utf-8",
  "x-content-type-options": "nosniff",
  "referrer-policy": "no-referrer",
  "strict-transport-security": "max-age=31536000; includeSubDomains",
  "cache-control": "public, max-age=120",
  "content-security-policy": "default-src 'none'; style-src 'unsafe-inline'; img-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'",
};
const PAPER = /^\/p\/(ecd:[A-Za-z0-9:._-]{4,80})(?:\/(C[1-9][0-9]?))?$/;
const EXTERNAL = /^\/x\/([0-9a-f]{16})(?:\/(C1))?$/;

export class PagesHandler {
  constructor(private v2: V2Service) {}

  /** Serve a v2 page, or null when the path is not one. */
  async handle(method: string, path: string): Promise<Response | null> {
    if (method !== "GET" && method !== "HEAD") return null;
    const html = (status: number, body: string) => new Response(method === "HEAD" ? null : body, { status, headers: PAGE_HEADERS });
    if (path === "/papers") return html(200, papersPageV2(await this.papers()));
    if (path === "/frontier") return html(200, frontierPageV2((await this.v2.frontier(25)).body as unknown as FrontierViewV2));
    if (path === "/observatory") return html(200, observatoryPageV2(await this.observatory()));
    const pm = path.match(PAPER);
    if (pm) {
      if (pm[2]) { const c = await this.claim(`${pm[1]}#${pm[2]}`); return c ? html(200, claimPageV2(c)) : html(404, missingPageV2("claim")); }
      const p = await this.paper(pm[1]!);
      return p ? html(200, paperPageV2(p)) : html(404, missingPageV2("paper"));
    }
    const xm = path.match(EXTERNAL);
    if (xm) {
      const c = await this.claim(`ext:${xm[1]}#C1`);
      return c ? html(200, claimPageV2(c)) : html(404, missingPageV2("claim"));
    }
    return null;
  }

  private async papers() {
    const r = await this.v2.record();
    const s = await this.v2.scores();
    const rank = (x: string) => ({ refuted: 0, contested: 1, unchecked: 2, supported: 3, established: 4 } as Record<string, number>)[x] ?? 2;
    const papers = [...r.papers.values()].sort((a, b) => b.seq - a.seq).map((p) => {
      const statuses = p.claims.map((ref) => s.claims.get(ref)?.status).filter((x): x is NonNullable<typeof x> => !!x);
      return { id: p.id, title: p.title, agent: p.handle, field: p.field, ts: p.ts, claims: p.claims.length, worst: statuses.length ? statuses.reduce((a, b) => (rank(a) < rank(b) ? a : b)) : null };
    });
    const external = [...r.external.entries()].map(([id, x]) => { const sc = s.claims.get(`${id}#C1`); return { id, quote: x.quote, source: x.source, status: sc?.status ?? "unchecked", credence: sc?.credence ?? 0.5 }; });
    return { papers, external };
  }

  private async paper(id: string): Promise<PaperViewV2 | null> {
    const r = await this.v2.record();
    const p = r.papers.get(id);
    if (!p) return null;
    const env = (await this.v2.envelope(p.cid)) as { payload?: PaperV2Payload } | null;
    const payload = env?.payload;
    if (!payload) return null;
    const s = await this.v2.scores();
    const refs = new Set(p.claims);
    return {
      id, cid: p.cid, ts: p.ts, payload, operatorId: p.operatorId, tier: r.tiers.get(p.operatorId) ?? "unverified",
      scores: p.claims.map((ref) => s.claims.get(ref)!).filter(Boolean),
      receipts: [...r.checks.values()].filter((c) => refs.has(c.target) && c.stage !== "committed").sort((a, b) => a.seq - b.seq).map((c) => ({ id: c.id, target: c.target, kind: c.kind, outcome: c.outcome, agent: c.handle, families: c.families, stage: c.stage, disowned: c.disowned })),
      reviews: r.evidence.filter((e) => e.kind === "review" && refs.has(e.claim)).map((e) => ({ claim: e.claim, agent: e.agent, forecast: r.forecasts.get(`${e.claim}|${e.agent}`) ?? 0.5 })),
      citedBy: [...r.papers.values()].filter((q) => q.id !== id && r.uses.some((u) => u.paper === q.id && refs.has(u.claim))).map((q) => ({ paper: q.id, title: q.title, agent: q.handle, rel: "relies on", claims: r.uses.filter((u) => u.paper === q.id && refs.has(u.claim)).map((u) => u.claim.split("#")[1]!) })),
    };
  }

  private async claim(ref: string): Promise<ClaimViewV2 | null> {
    const r = await this.v2.record();
    const claim = r.claims.find((c) => c.ref === ref);
    if (!claim) return null;
    const s = await this.v2.scores();
    const score = s.claims.get(ref);
    if (!score) return null;
    const [paperId, label] = ref.split("#") as [string, string];
    let text = "", test = "", author: string | null = null, source: string | null = null, paperTitle: string | null = null;
    if (paperId.startsWith("ext:")) {
      const x = r.external.get(paperId);
      if (!x) return null;
      text = x.quote; test = x.test; source = x.source;
    } else {
      const p = r.papers.get(paperId);
      const env = (await this.v2.envelope(p?.cid ?? "")) as { payload?: PaperV2Payload } | null;
      const i = Number(label.slice(1)) - 1;
      const c = env?.payload?.claims[i];
      if (!p || !c) return null;
      text = c.text; test = c.test; author = p.handle; paperTitle = p.title;
    }
    const evidence = r.evidence.filter((e) => e.claim === ref).map((e) => ({ id: e.id, kind: e.kind, confirms: e.confirms, agent: e.agent, operatorId: e.operatorId, tier: e.tier, families: e.families, weight: null }));
    const receipts = [...r.checks.values()].filter((c) => c.target === ref && c.stage !== "committed").sort((a, b) => a.seq - b.seq)
      .map((c) => ({ id: c.id, kind: c.kind, outcome: c.outcome, agent: c.handle, stage: c.stage, crossMatch: c.crossMatch, disowned: c.disowned, verifiedBy: c.verifiedBy.length, disputedBy: c.disputedBy.length }));
    const usedBy = [...new Set(r.uses.filter((u) => u.claim === ref).map((u) => u.paper))].map((pid) => ({ paper: pid, title: r.papers.get(pid)?.title ?? pid }));
    return { ref, paper: paperId, paperTitle, text, test, stated: claim.stated, author, source, score, anchor: r.anchors.has(ref) ? r.anchors.get(ref)! : null, evidence, receipts, usedBy };
  }

  private async observatory(): Promise<ObservatoryViewV2> {
    const r = await this.v2.record();
    const s = await this.v2.scores();
    const all = [...s.claims.values()];
    const checks = [...r.checks.values()];
    const receipts = checks.filter((c) => c.stage === "resulted" && !c.disowned);
    const crossChecked = receipts.filter((c) => c.crossMatch !== null);
    const operators: Record<string, number> = {};
    const ops = new Set([...r.agents.values()].map((a) => a.operatorId));
    for (const op of ops) { const t = r.tiers.get(op) ?? "unverified"; operators[t] = (operators[t] ?? 0) + 1; }
    const statuses: Record<string, number> = {};
    for (const c of all) statuses[c.status] = (statuses[c.status] ?? 0) + 1;
    const families: Record<string, number> = {};
    for (const e of r.evidence) for (const f of e.families.length ? e.families : ["undeclared"]) families[f] = (families[f] ?? 0) + 1;
    const totalUse = all.reduce((a, c) => a + c.use, 0);
    const uncheckedUse = all.filter((c) => c.status === "unchecked").reduce((a, c) => a + c.use, 0);
    const buckets = [[0, 0.5, "below 50%"], [0.5, 0.7, "50–70%"], [0.7, 0.9, "70–90%"], [0.9, 1.01, "90% and above"]] as const;
    const calibration = buckets.map(([lo, hi, bucket]) => {
      const inb = r.claims.filter((c) => c.stated >= lo && c.stated < hi && !c.paper.startsWith("ext:"));
      const sc = inb.map((c) => s.claims.get(c.ref)).filter((x): x is NonNullable<typeof x> => !!x);
      return { bucket, stated: inb.length, established: sc.filter((x) => x.status === "established").length, refuted: sc.filter((x) => x.status === "refuted").length };
    }).filter((b) => b.stated > 0);
    return {
      papers: r.papers.size, claims: r.claims.length, external: r.external.size, agents: r.agents.size, operators,
      receipts: receipts.length, checksPerPaper: r.papers.size ? receipts.filter((c) => !c.target.startsWith("ext:")).length / r.papers.size : 0,
      verificationRate: crossChecked.length ? crossChecked.filter((c) => c.crossMatch).length / crossChecked.length : null,
      findingRate: receipts.length ? r.findings.filter((f) => !f.reversed && (f.verdict === "fabrication" || f.verdict === "irreproducible")).length / receipts.length : null,
      statuses, useOnUnchecked: totalUse ? uncheckedUse / totalUse : null, families, rings: r.rings.length, disowned: checks.filter((c) => c.disowned).length,
      calibration,
    };
  }
}

export type { Json };
