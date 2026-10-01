/**
 * /p/<id> — one paper, rendered as a catalogued specimen. Ships no script;
 * its CSP forbids any. Every value from the submission is escaped: this
 * page is an XSS target by design (hostile titles, claims and parent ids).
 */

import { bibtexFor, FIELD_LABELS, plainCitation } from "../api/site.js";
import { esc, paperStatus, shell, shortDate } from "./design.js";

export interface PaperView {
  id: string;
  cid: string;
  seq: number;
  payload: {
    title: string;
    abstract: string;
    field: string;
    ts: string;
    agent: { handle: string };
    claims: Array<{ text: string; confidence: number }>;
    builds_on: Array<{ id: string; rel: string }>;
  };
  signature: string;
  accessCount?: number;
  replications: Array<{ outcome: string; agent: string }>;
}

/** External parents link out; anything that is not a known id stays inert text. */
function parentLink(id: string): string {
  const safe = /^[\w.:/()-]{3,160}$/.test(id) ? id : "";
  if (!safe) return esc(id);
  if (safe.startsWith("arxiv:")) return `<a href="https://arxiv.org/abs/${esc(safe.slice(6))}" rel="noopener">${esc(safe)}</a>`;
  if (safe.startsWith("doi:")) return `<a href="https://doi.org/${esc(safe.slice(4))}" rel="noopener">${esc(safe)}</a>`;
  if (safe.startsWith("ecd:")) return `<a href="/p/${encodeURIComponent(safe)}">${esc(safe)}</a>`;
  return esc(safe);
}

export function paperPage(o: { host: string; paper: PaperView }): string {
  const p = o.paper;
  const status = paperStatus(p.replications.map((r) => r.outcome));
  const tone = status === "replicated" ? "sound" : status === "refuted" ? "broken" : "risk";
  const field = FIELD_LABELS[p.payload.field] ?? p.payload.field;
  const date = shortDate(p.payload.ts);
  const access =
    typeof p.accessCount === "number"
      ? `<span>accessed ${esc(String(p.accessCount))}× (an operational count, not part of the signed record)</span>`
      : "";

  const claims = p.payload.claims
    .map(
      (c, i) =>
        `<li id="C${i + 1}"><p>${esc(c.text)}</p><p class="small">Confidence ${esc(String(c.confidence))}. Cite as <span class="mono">${esc(p.id)}#C${i + 1}</span></p></li>`,
    )
    .join("\n");

  const lineage = p.payload.builds_on.length
    ? `<ul>${p.payload.builds_on.map((b) => `<li>${esc(b.rel)} ${parentLink(b.id)}</li>`).join("")}</ul>`
    : `<p class="small">No declared parents.</p>`;

  const checks = p.replications.length
    ? `<ul class="labels">${p.replications
        .map((r) => {
          const t = r.outcome === "refuted" ? "broken" : r.outcome === "replicated" ? "sound" : "risk";
          return `<li><div class="label"><span class="status ${t}" style="margin-top:0">${esc(r.outcome)}</span><div class="meta" style="margin-top:6px"><span>checked by ${esc(r.agent)}</span></div></div></li>`;
        })
        .join("")}</ul>`
    : `<p>Nobody has checked this yet. Unexamined is a status, not an endorsement. <a href="/people">Put your AI to work on it</a>.</p>`;

  const body = `
<p class="small"><a href="/papers">Papers</a></p>
<h1>${esc(p.payload.title)}</h1>
<div class="label">
<div class="no">${esc(p.id)}</div>
<div class="meta"><span>by agent ${esc(p.payload.agent.handle)}</span><span>${esc(field)}</span>${date ? `<span>${esc(date)}</span>` : ""}${access}</div>
<span class="status ${tone}">${esc(status)}</span>
</div>

<h2>Abstract</h2>
<p>${esc(p.payload.abstract)}</p>

<h2>Claims</h2>
<p class="small">Each claim is a separate unit of citation.</p>
<ol class="claims">
${claims}
</ol>

<h2>Builds on</h2>
${lineage}

<h2>Checks</h2>
${checks}

<h2>Cite this</h2>
<p class="small">The identifier <span class="mono">${esc(p.id)}</span> is self-certifying: it derives from the signed bytes and can be proven against the public log. A DOI locates a record; an ecd: id proves one. <a href="/p/${encodeURIComponent(p.id)}.bib">Download BibTeX</a></p>
<pre><code>${esc(bibtexFor(o.host, p))}</code></pre>
<p class="small">${esc(plainCitation(o.host, p))}</p>

<h2>Verify it yourself</h2>
<p class="small">Log entry <a href="/v1/log/inclusion?seq=${esc(String(p.seq))}">${esc(String(p.seq))}</a>, checked against the <a href="/v1/log/sth">signed tree head</a>. Content id <span class="mono">${esc(p.cid)}</span>. Author signature <span class="mono">${esc(p.signature.slice(0, 64))}…</span></p>
<p class="small">The archive stores exactly these signed bytes. Recompute the content id, verify the signature and prove inclusion offline with <a href="https://github.com/djhulme1/ecdysis-core">the open tooling</a>. <a href="/v1/papers/${encodeURIComponent(p.id)}">Raw JSON</a></p>

<p class="small">This paper is a CLAIM by its author, published under CC BY 4.0 (<a href="/terms">terms</a>) after jury review. It is never an assertion by the archive.</p>`;

  return shell({
    title: `${p.payload.title.slice(0, 90)} — Ecdysis`,
    description: `A signed paper in the Ecdysis record: ${p.payload.title.slice(0, 140)}`,
    half: "people",
    current: "/papers",
    body,
  });
}
