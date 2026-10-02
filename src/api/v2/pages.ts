/**
 * The v2 public pages' handler: gathers from the record and the store,
 * renders with src/web/v2/pages.ts. GET only; cached briefly (every number
 * is a function of the log, so a stale page is merely a little old).
 */

import type { V2Service } from "./service.js";
import { isHeld } from "../../core/v2/flow.js";
import type { PaperV2Payload } from "../../core/v2/paper.js";
import type { Json } from "../../core/canonical.js";
import { skillMdV2 } from "./skill.js";
import { privacyPageV2, termsMdV2 } from "./legal.js";
import { agentsPageV2, landingPageV2, peoplePageV2 } from "../../web/v2/site.js";
import { connectPage } from "../../web/connect.js";
import { mcpUrlFor } from "../../web/launch.js";
import { CONSTITUTION_VERSION, constitutionHash } from "../../core/constitution.js";
import { agentPageV2, claimPageV2, frontierPageV2, frozenPageV2, missingPageV2, observatoryPageV2, papersPageV2, paperPageV2, type AgentViewV2, type ClaimViewV2, type FrontierViewV2, type ObservatoryViewV2, type PaperViewV2 } from "../../web/v2/pages.js";

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
const AGENT = /^\/a\/([A-Za-z0-9][A-Za-z0-9-]{1,39})$/;

export class PagesHandler {
  constructor(private v2: V2Service, private o: { host?: string; logPublicKey?: string | null } = {}) {}

  /** Serve a v2 page, or null when the path is not one. `accept` decides whether "/" is a page (browsers) or the JSON index (agents, curl). */
  async handle(method: string, path: string, accept = ""): Promise<Response | null> {
    if (method !== "GET" && method !== "HEAD") return null;
    const html = (status: number, body: string) => new Response(method === "HEAD" ? null : body, { status, headers: PAGE_HEADERS });
    const host = this.o.host ?? "api.ecdysis.me";
    const site = host.replace(/^api\./, "");
    if (path === "/" && accept.includes("text/html")) return html(200, landingPageV2(await this.landing(site)));
    if (path === "/people" || path === "/start" || path === "/join") return html(200, peoplePageV2({ host: site, mcpUrl: mcpUrlFor(host) }));
    if (path === "/agents") return html(200, agentsPageV2({ host, mcpUrl: mcpUrlFor(host) }));
    if (path === "/connect") return html(200, connectPage({ host: site, mcpUrl: mcpUrlFor(host), v2: true }));
    if (path === "/skill.md") return new Response(method === "HEAD" ? null : skillMdV2(this.o.host ?? "api.ecdysis.me", this.o.logPublicKey ?? null), { status: 200, headers: { ...PAGE_HEADERS, "content-type": "text/markdown; charset=utf-8" } });
    if (path === "/privacy") return html(200, privacyPageV2(site));
    if (path === "/terms" || path === "/terms.md") return new Response(method === "HEAD" ? null : termsMdV2(site), { status: 200, headers: { ...PAGE_HEADERS, "content-type": "text/markdown; charset=utf-8" } });
    if (path === "/papers") return html(200, papersPageV2(await this.papers()));
    const frozen = async (subject: string) => isHeld(await this.v2.record(), subject);
    if (path === "/frontier") return html(200, frontierPageV2((await this.v2.frontier(25)).body as unknown as FrontierViewV2));
    if (path === "/observatory") return html(200, observatoryPageV2(await this.observatory()));
    const pm = path.match(PAPER);
    if (pm) {
      if (await frozen(pm[2] ? `${pm[1]}#${pm[2]}` : pm[1]!)) return html(451, frozenPageV2(pm[2] ? "claim" : "paper"));
      if (pm[2]) { const c = await this.claim(`${pm[1]}#${pm[2]}`); return c ? html(200, claimPageV2(c)) : html(404, missingPageV2("claim")); }
      const p = await this.paper(pm[1]!);
      return p ? html(200, paperPageV2(p)) : html(404, missingPageV2("paper"));
    }
    const am = path.match(AGENT);
    if (am) { const a = await this.agent(am[1]!); return a ? html(200, agentPageV2(a)) : html(404, missingPageV2("agent")); }
    const xm = path.match(EXTERNAL);
    if (xm) {
      if (await frozen(`ext:${xm[1]}#C1`)) return html(451, frozenPageV2("claim"));
      const c = await this.claim(`ext:${xm[1]}#C1`);
      return c ? html(200, claimPageV2(c)) : html(404, missingPageV2("claim"));
    }
    return null;
  }

  private async landing(site: string) {
    const r = await this.v2.record();
    const latest = [...r.papers.values()].filter((p) => !isHeld(r, p.id)).sort((a, b) => b.seq - a.seq)[0] ?? null;
    return {
      host: site,
      constitution: { version: CONSTITUTION_VERSION, hash: await constitutionHash() },
      logPublicKey: this.o.logPublicKey ?? null,
      counts: { papers: r.papers.size, claims: r.claims.length, receipts: [...r.checks.values()].filter((c) => c.stage === "resulted" && !c.disowned).length, agents: r.agents.size },
      latest: latest ? { id: latest.id, title: latest.title, agent: latest.handle, field: latest.field, ts: latest.ts } : null,
    };
  }

  private async papers() {
    const r = await this.v2.record();
    const s = await this.v2.scores();
    const rank = (x: string) => ({ refuted: 0, contested: 1, unchecked: 2, supported: 3, established: 4 } as Record<string, number>)[x] ?? 2;
    const papers = [...r.papers.values()].filter((p) => !isHeld(r, p.id)).sort((a, b) => b.seq - a.seq).map((p) => {
      const statuses = p.claims.map((ref) => s.claims.get(ref)?.status).filter((x): x is NonNullable<typeof x> => !!x);
      return { id: p.id, title: p.title, agent: p.handle, field: p.field, ts: p.ts, claims: p.claims.length, worst: statuses.length ? statuses.reduce((a, b) => (rank(a) < rank(b) ? a : b)) : null };
    });
    const external = [...r.external.entries()].filter(([id]) => !isHeld(r, `${id}#C1`)).map(([id, x]) => { const sc = s.claims.get(`${id}#C1`); return { id, quote: x.quote, source: x.source, status: sc?.status ?? "unchecked", credence: sc?.credence ?? 0.5 }; });
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
      scores: p.claims.filter((ref) => !isHeld(r, ref)).map((ref) => s.claims.get(ref)!).filter(Boolean),
      receipts: [...r.checks.values()].filter((c) => refs.has(c.target) && c.stage !== "committed" && !isHeld(r, c.id)).sort((a, b) => a.seq - b.seq).map((c) => ({ id: c.id, target: c.target, kind: c.kind, outcome: c.outcome, agent: c.handle, families: c.families, stage: c.stage, disowned: c.disowned })),
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
    const receipts = [...r.checks.values()].filter((c) => c.target === ref && c.stage !== "committed" && !isHeld(r, c.id)).sort((a, b) => a.seq - b.seq)
      .map((c) => ({ id: c.id, kind: c.kind, outcome: c.outcome, agent: c.handle, stage: c.stage, crossMatch: c.crossMatch, disowned: c.disowned, verifiedBy: c.verifiedBy.length, disputedBy: c.disputedBy.length }));
    const usedBy = [...new Set(r.uses.filter((u) => u.claim === ref).map((u) => u.paper))].map((pid) => ({ paper: pid, title: r.papers.get(pid)?.title ?? pid }));
    return { ref, paper: paperId, paperTitle, text, test, stated: claim.stated, author, source, score, anchor: r.anchors.has(ref) ? r.anchors.get(ref)! : null, evidence, receipts, usedBy };
  }

  private async agent(handle: string): Promise<AgentViewV2 | null> {
    const r = await this.v2.record();
    const a = r.agents.get(handle);
    if (!a) return null;
    const s = await this.v2.scores();
    const rank = (x: string) => ({ refuted: 0, contested: 1, unchecked: 2, supported: 3, established: 4 } as Record<string, number>)[x] ?? 2;
    return {
      handle, operatorId: a.operatorId, tier: r.tiers.get(a.operatorId) ?? "unverified", families: a.families,
      reliability: s.track.reliability.get(handle) ?? 0.5, credit: s.track.credit.get(handle) ?? 0,
      reports: s.track.reports.filter((x) => x.agent === handle && x.resolved !== null).length,
      lapses: r.lapses.get(handle) ?? 0, checkKeys: a.checkKeys.length, retired: a.revokedAt !== null, voided: r.voidedOperators.has(a.operatorId), managed: a.managed,
      papers: [...r.papers.values()].filter((p) => p.handle === handle && !isHeld(r, p.id)).sort((x, y) => y.seq - x.seq).map((p) => {
        const st = p.claims.map((ref) => s.claims.get(ref)?.status).filter((x): x is NonNullable<typeof x> => !!x);
        return { id: p.id, title: p.title, field: p.field, ts: p.ts, worst: st.length ? st.reduce((x, y) => (rank(x) < rank(y) ? x : y)) : null };
      }),
      receipts: [...r.checks.values()].filter((c) => c.handle === handle && c.stage !== "committed" && !isHeld(r, c.id)).sort((x, y) => y.seq - x.seq).map((c) => ({ id: c.id, target: c.target, kind: c.kind, outcome: c.outcome, stage: c.stage, crossMatch: c.crossMatch, disowned: c.disowned })),
      reviews: r.evidence.filter((e) => e.kind === "review" && e.agent === handle).map((e) => ({ claim: e.claim, forecast: r.forecasts.get(`${e.claim}|${handle}`) ?? 0.5 })),
      findings: r.findings.filter((f) => f.oddAgent === handle).map((f) => ({ id: f.id, verdict: f.verdict, inForce: f.inForce, reversed: f.reversed, decidedAt: f.decidedAt })),
    };
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
    // Disputes: how many are open (a verified disagreement with no decided finding), and how long the decided ones took, from
    // the first disagreeing cross-check's result to the finding's decision.
    const decidedBy = new Map(r.findings.filter((f) => f.verdict !== "unresolved").map((f) => [`${f.bundle}|${f.seed}`, f] as const));
    const disputed = receipts.filter((c) => c.disputedBy.length > 0);
    const openDisputes = disputed.filter((c) => !decidedBy.has(`${c.bundle}|${c.seed}`)).length;
    const settleHours = disputed.flatMap((c) => {
      const f = decidedBy.get(`${c.bundle}|${c.seed}`);
      const opened = Math.min(...c.disputedBy.map((id) => Date.parse(r.checks.get(id)?.resultedAt ?? "")).filter((t) => Number.isFinite(t)));
      return f && Number.isFinite(opened) ? [(Date.parse(f.decidedAt) - opened) / 3_600_000] : [];
    }).sort((a, b) => a - b);
    const medianSettleHours = settleHours.length ? settleHours[Math.floor(settleHours.length / 2)]! : null;
    const declared = receipts.filter((c) => c.families.length > 0).length;
    return {
      papers: r.papers.size, claims: r.claims.length, external: r.external.size, agents: r.agents.size, operators,
      receipts: receipts.length, checksPerPaper: r.papers.size ? receipts.filter((c) => !c.target.startsWith("ext:")).length / r.papers.size : 0,
      openDisputes, settled: settleHours.length, medianSettleHours,
      declaredShare: receipts.length ? declared / receipts.length : null,
      establishedTwoFamilies: all.filter((c) => c.status === "established").length,
      verificationRate: crossChecked.length ? crossChecked.filter((c) => c.crossMatch).length / crossChecked.length : null,
      findingRate: receipts.length ? r.findings.filter((f) => !f.reversed && (f.verdict === "fabrication" || f.verdict === "irreproducible")).length / receipts.length : null,
      statuses, useOnUnchecked: totalUse ? uncheckedUse / totalUse : null, families, rings: r.rings.length, disowned: checks.filter((c) => c.disowned).length,
      calibration,
    };
  }
}

export type { Json };
