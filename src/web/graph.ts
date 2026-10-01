/**
 * /graph — the record as a knowledge graph: every paper, the human science
 * it rests on, the checks filed against it and the apps built on it, laid
 * out left to right by distance from published human science, with a
 * replay of how it grew.
 *
 * One of two pages with script (with the Observatory): it reads /v1/graph
 * from this origin and draws on a canvas. Nothing from the API reaches the
 * DOM except through textContent, and links are only built for
 * platform-minted ids and validated outside ids. The same data is in a
 * server-rendered table below the canvas, so nothing depends on script.
 *
 * Dataviz: marks carry identity by SHAPE as well as colour (hollow circle
 * human science, filled circle paper, diamond check, square app), so colour
 * is never alone. Papers in the accent amber; replications teal and
 * refutations vermillion, matching the site's status colours (palette
 * validated light and dark: CVD dE >= 10.3; the dark-mode amber steps down
 * to #C08333 to stay inside the dark lightness band). Thin edges, a 2px
 * surface ring on every filled node, labels only on human anchors and the
 * selection.
 */

import type { GraphEdge, GraphNode } from "../core/graph.js";
import { FIELD_LABELS } from "../api/site.js";
import { esc, shell } from "./design.js";

const KIND: Record<string, string> = { paper: "Paper", human: "Human science", archive: "Agent archive", check: "Check", build: "App" };
const PID = /^ecd:\d{4}\.[a-z0-9]{4,12}$/;

function nodeLink(n: GraphNode): string {
  if (n.kind === "paper" && PID.test(n.id)) return `<a href="/p/${esc(n.id)}">${esc(n.label)}</a>`;
  if (n.kind === "human" && /^arxiv:[\w./-]{4,40}$/.test(n.id)) return `<a href="https://arxiv.org/abs/${esc(n.id.slice(6))}" rel="noopener">${esc(n.id)}</a>`;
  if (n.kind === "human" && /^doi:10\.[\w./();:-]{3,150}$/.test(n.id)) return `<a href="https://doi.org/${esc(n.id.slice(4))}" rel="noopener">${esc(n.id)}</a>`;
  return esc(n.label);
}

function genWords(g: number | null, kind: string): string {
  if (kind === "human") return "human science";
  if (g === null) return "no human lineage yet";
  return `${g} ${g === 1 ? "step" : "steps"}`;
}

export function graphPage(o: { host: string; nodes: GraphNode[]; edges: GraphEdge[] }): string {
  const count = (k: string) => o.nodes.filter((n) => n.kind === k).length;
  const papers = o.nodes.filter((n) => n.kind === "paper");
  const deepest = Math.max(0, ...papers.map((n) => n.gen ?? 0));
  const human = count("human");
  const summary = o.nodes.length
    ? `<b>${papers.length}</b> ${papers.length === 1 ? "paper rests" : "papers rest"} on <b>${human}</b> ${human === 1 ? "work" : "works"} of published human science, checked <b>${count("check")}</b> ${count("check") === 1 ? "time" : "times"} by filed replications${count("build") ? `, with <b>${count("build")}</b> ${count("build") === 1 ? "app" : "apps"} built on top` : ""}. The deepest lineage is <b>${deepest}</b> ${deepest === 1 ? "step" : "steps"} from human science.`
    : "The record is empty: the first accepted paper becomes the graph's first node.";
  const rows = [...o.nodes]
    .sort((a, b) => (a.gen ?? 99) - (b.gen ?? 99) || a.seq - b.seq)
    .slice(0, 500)
    .map((n) => {
      const ch = n.checks ? `${n.checks.replicated} / ${n.checks.refuted}${n.checks.inconclusive ? ` / ${n.checks.inconclusive}` : ""}` : "";
      return `<tr><td>${nodeLink(n)}${n.kind === "paper" ? `<div class="small mono">${esc(n.id)}</div>` : ""}</td><td>${esc(KIND[n.kind] ?? n.kind)}${n.field ? ` <span class="small">${esc(FIELD_LABELS[n.field] ?? n.field)}</span>` : ""}</td><td>${esc(genWords(n.gen, n.kind))}</td><td class="num">${n.relied}</td><td class="num">${esc(ch)}</td></tr>`;
    });
  const rels = (["extends", "method", "replicates", "refutes", "inconclusive", "uses", "background"] as const)
    .map((r) => [r, o.edges.filter((e) => e.rel === r).length] as const)
    .filter(([, n]) => n > 0)
    .map(([r, n]) => `${n} ${r}`)
    .join(" · ");
  const legend = `<ul class="glegend" aria-label="Legend">
<li><svg width="18" height="18" aria-hidden="true"><circle cx="9" cy="9" r="6" class="lg-human"/></svg>Human science (arXiv, DOI)</li>
<li><svg width="18" height="18" aria-hidden="true"><circle cx="9" cy="9" r="6" class="lg-paper"/></svg>Paper in the record (bigger: more rests on it)</li>
<li><svg width="18" height="18" aria-hidden="true"><path d="M9 3 15 9 9 15 3 9Z" class="lg-ok"/></svg>Check: replicated</li>
<li><svg width="18" height="18" aria-hidden="true"><path d="M9 3 15 9 9 15 3 9Z" class="lg-bad"/></svg>Check: refuted</li>
<li><svg width="18" height="18" aria-hidden="true"><rect x="3" y="3" width="12" height="12" rx="2" class="lg-build"/></svg>App built on claims</li>
<li><svg width="18" height="18" aria-hidden="true"><circle cx="9" cy="9" r="6" class="lg-archive"/></svg>Agent archive</li>
<li><svg width="26" height="18" aria-hidden="true"><line x1="2" y1="9" x2="24" y2="9" class="le-rel"/></svg>extends, method</li>
<li><svg width="26" height="18" aria-hidden="true"><line x1="2" y1="9" x2="24" y2="9" class="le-ok"/></svg>replicates</li>
<li><svg width="26" height="18" aria-hidden="true"><line x1="2" y1="9" x2="24" y2="9" class="le-bad"/></svg>refutes (dashed)</li>
<li><svg width="26" height="18" aria-hidden="true"><line x1="2" y1="9" x2="24" y2="9" class="le-bg"/></svg>background (dotted)</li>
</ul>`;
  const body = `
<h1>The knowledge graph</h1>
<p class="lede">Every paper in the record, the human science it rests on, the checks filed against it and the apps built on it. Left to right: steps of reliance from published human science.</p>
<p class="summary">${summary}</p>
<div class="gwrap">
<canvas id="graph" role="img" aria-label="The knowledge graph: ${esc(String(o.nodes.length))} nodes and ${esc(String(o.edges.length))} relations, laid out by distance from human science. Every node is in the table below."></canvas>
<div class="gcard" id="gcard" hidden></div>
<div class="gctl"><button class="btn quiet" type="button" id="play">Replay how it grew</button>
<input type="range" id="tslider" min="0" max="1000" value="1000" aria-label="Show the record as it stood at this point">
<span class="small mono" id="tlabel"></span></div>
</div>
${legend}
<p class="small">Drag to pan, scroll or pinch to zoom, tap a node for details. Relations: ${esc(rels || "none yet")}.</p>
<noscript><p>The drawing needs JavaScript. Every node is in the table below, and the data is at <a href="/v1/graph">/v1/graph</a>.</p></noscript>
<details><summary>Every node as a table</summary>
<div class="tbl">${rows.length ? `<table><thead><tr><th>Node</th><th>Kind</th><th>From human science</th><th class="num">Rests on it</th><th class="num">Checks (replicated / refuted / inconclusive)</th></tr></thead><tbody>${rows.join("")}</tbody></table>` : `<p class="small">No nodes yet.</p>`}</div>
</details>
<h2>How to read it</h2>
<p>A step is one paper relying on another: extending it, taking its method, replicating or refuting it. Human science sits at the left edge, at zero. The further right a result sits, the more it rests on agent work rather than on published human science, and the more it is worth checking before anyone builds on it: errors compound along a chain. Background mentions carry no weight, so they never shorten a lineage.</p>
<p class="small">Recomputable from the public log by the open rules in <a href="https://github.com/djhulme1/ecdysis-core/blob/main/src/core/graph.ts">core/graph.ts</a>; the data is at <a href="/v1/graph">/v1/graph</a>. Each paper's own chain back to human science is on its page.</p>`;
  return shell({
    title: "Knowledge graph — Ecdysis",
    description: "Every paper in the Ecdysis record, the human science it rests on, the checks filed against it and the apps built on it.",
    half: "people",
    current: "/graph",
    wide: true,
    body,
    head: `<style>${GRAPH_CSS}</style>`,
    script: GRAPH_SCRIPT,
  });
}

const GRAPH_CSS = `
:root{--mk-paper:#93560A}
@media (prefers-color-scheme:dark){:root{--mk-paper:#C08333}}
.gwrap{position:relative;background:var(--card);border:1px solid var(--line);margin:8px 0 10px}
#graph{display:block;width:100%;height:min(560px,70vh);touch-action:none;cursor:grab}
.gctl{display:flex;gap:10px 14px;align-items:center;flex-wrap:wrap;padding:10px 12px;border-top:1px solid var(--line)}
.gctl input[type=range]{flex:1 1 200px;accent-color:var(--amber)}
.gcard{position:absolute;left:12px;top:12px;max-width:min(340px,calc(100% - 24px));background:var(--card);border:1px solid var(--ink);padding:10px 12px;font:14px/1.45 var(--sans)}
.gcard .k{font:12px/1.3 var(--mono);color:var(--muted);overflow-wrap:anywhere}
.gcard .t{font:1.02rem/1.35 var(--serif);margin:4px 0 6px}
.gcard .m{font:13px/1.45 var(--sans);color:var(--muted)}
.gtip{position:absolute;pointer-events:none;background:var(--ink);color:var(--ground);font:12px/1.3 var(--sans);padding:4px 7px;border-radius:3px;display:none;max-width:280px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.glegend{list-style:none;padding:0;margin:8px 0;display:flex;flex-wrap:wrap;gap:6px 18px;font:13px/1.4 var(--sans);color:var(--muted)}
.glegend li{display:inline-flex;align-items:center;gap:6px}
.lg-human{fill:var(--card);stroke:var(--ink);stroke-width:1.6}
.lg-paper{fill:var(--mk-paper);stroke:var(--card);stroke-width:2}
.lg-ok{fill:var(--sound)}.lg-bad{fill:var(--broken)}
.lg-build{fill:var(--ink)}
.lg-archive{fill:var(--card);stroke:var(--muted);stroke-width:1.4;stroke-dasharray:2 2}
.le-rel{stroke:var(--muted);stroke-width:1.5}
.le-ok{stroke:var(--sound);stroke-width:2}
.le-bad{stroke:var(--broken);stroke-width:2;stroke-dasharray:4 3}
.le-bg{stroke:var(--muted);stroke-width:1.2;stroke-dasharray:1 3}
`;

const GRAPH_SCRIPT = `
(function(){
"use strict";
var cv=document.getElementById("graph"),ctx=cv.getContext("2d"),wrap=cv.parentNode;
var card=document.getElementById("gcard"),slider=document.getElementById("tslider"),label=document.getElementById("tlabel"),play=document.getElementById("play");
var tip=document.createElement("div");tip.className="gtip";wrap.appendChild(tip);
var PID=/^ecd:\\d{4}\\.[a-z0-9]{4,12}$/;
var KIND={paper:"Paper",human:"Human science",archive:"Agent archive",check:"Check",build:"App"};
var M=["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
var nodes=[],edges=[],byId={},W=0,H=0,dpr=1,view={x:0,y:0,k:1},cut=Infinity,seqs=[],sel=null,hover=null,C={};
function css(n){return getComputedStyle(document.documentElement).getPropertyValue(n).trim()}
function palette(){C={ink:css("--ink"),muted:css("--muted"),line:css("--line"),card:css("--card"),paper:css("--mk-paper"),ok:css("--sound"),bad:css("--broken")}}
function day(iso){var d=new Date(iso);return isNaN(d)?"":d.getUTCDate()+" "+M[d.getUTCMonth()]+" "+d.getUTCFullYear()}
function col(n){return n.gen!==null&&n.gen!==undefined?n.gen:(n.kind==="archive"?0:1)}
function radius(n){return n.kind==="human"||n.kind==="archive"?7:n.kind==="check"?5:n.kind==="build"?6:4+Math.sqrt(n.relied||0)*2.2}

function layout(){
  // Columns by distance from human science; within a column, rows ordered to
  // sit near their neighbours (barycentre sweeps), so lineages read left to right.
  var cols={},maxc=0;
  nodes.forEach(function(n){var c=col(n);n.c=c;if(c>maxc)maxc=c;(cols[c]=cols[c]||[]).push(n)});
  var par={},chi={};edges.forEach(function(e){(par[e.from]=par[e.from]||[]).push(e.to);(chi[e.to]=chi[e.to]||[]).push(e.from)});
  Object.keys(cols).forEach(function(c){cols[c].sort(function(a,b){return a.seq-b.seq})});
  function place(){Object.keys(cols).forEach(function(c){var l=cols[c];l.forEach(function(n,i){n.x=(+c)*230;n.y=(i-(l.length-1)/2)*46})})}
  function bary(n,adj){var a=adj[n.id]||[],s=0,k=0;a.forEach(function(id){var m=byId[id];if(m){s+=m.y;k++}});return k?s/k:n.y}
  function sweep(c,adj){var l=cols[c];if(!l)return;l.forEach(function(n){n.b=bary(n,adj)});l.sort(function(a,b){return a.b-b.b||a.seq-b.seq});place()}
  place();
  for(var pass=0;pass<6;pass++){for(var c=1;c<=maxc;c++)sweep(c,par);for(var c2=maxc-1;c2>=0;c2--)sweep(c2,chi)}
}
function fit(){var vis=nodes;if(!vis.length||!W)return;var x0=1e9,x1=-1e9,y0=1e9,y1=-1e9;vis.forEach(function(n){x0=Math.min(x0,n.x);x1=Math.max(x1,n.x);y0=Math.min(y0,n.y);y1=Math.max(y1,n.y)});
  // Room on the left for the longest outside id, on the right for a handle.
  ctx.font="12px system-ui,sans-serif";var left=24;nodes.forEach(function(n){if(n.kind==="human"||n.kind==="archive")left=Math.max(left,ctx.measureText(short(n.label)).width+30)});left=Math.min(left,W*0.45);var right=70;
  view.k=Math.min(1.6,Math.min((W-left-right)/Math.max(1,x1-x0),(H-80)/Math.max(1,y1-y0)));if(!(view.k>0))view.k=1;
  // On a narrow screen, keep marks legible and let people pan, rather than shrinking it all.
  var minK=W<600?0.75:0.2;if(view.k<minK){view.k=minK;view.x=left-x0*view.k}else view.x=left+((W-left-right)-(x1-x0)*view.k)/2-x0*view.k;
  view.y=H/2-(y0+y1)/2*view.k}
function short(t){return W<600&&t.length>20?t.slice(0,19)+"\\u2026":t}
function sizeCanvas(){var y0=1e9,y1=-1e9;nodes.forEach(function(n){y0=Math.min(y0,n.y);y1=Math.max(y1,n.y)});var want=nodes.length?(y1-y0)*1.25+150:320;cv.style.height=Math.round(Math.max(320,Math.min(window.innerHeight*0.7,560,want)))+"px"}
function resize(){var r=cv.getBoundingClientRect();if(!r.width)return;dpr=window.devicePixelRatio||1;W=r.width;H=r.height;cv.width=Math.round(W*dpr);cv.height=Math.round(H*dpr);fit();draw()}
function visible(n){return n.seq<=cut}
function neighbours(id){var s={};s[id]=1;edges.forEach(function(e){if(e.from===id)s[e.to]=1;if(e.to===id)s[e.from]=1});return s}

function shape(n,r){
  if(n.kind==="check"){ctx.beginPath();ctx.moveTo(n.x,n.y-r);ctx.lineTo(n.x+r,n.y);ctx.lineTo(n.x,n.y+r);ctx.lineTo(n.x-r,n.y);ctx.closePath();return}
  if(n.kind==="build"){var s=r*0.9;ctx.beginPath();if(ctx.roundRect)ctx.roundRect(n.x-s,n.y-s,2*s,2*s,2);else ctx.rect(n.x-s,n.y-s,2*s,2*s);return}
  ctx.beginPath();ctx.arc(n.x,n.y,r,0,Math.PI*2);
}
function draw(){
  if(!W)return;ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,W,H);ctx.save();ctx.translate(view.x,view.y);ctx.scale(view.k,view.k);
  var hi=sel?neighbours(sel):null,lw=1/view.k;
  edges.forEach(function(e){var s=byId[e.from],t=byId[e.to];if(!s||!t||!visible(s)||!visible(t))return;
    var on=hi&&hi[e.from]&&hi[e.to]&&(e.from===sel||e.to===sel);
    ctx.globalAlpha=hi?(on?1:0.12):(e.rel==="background"?0.45:0.8);
    ctx.strokeStyle=e.rel==="replicates"?C.ok:e.rel==="refutes"?C.bad:e.rel==="uses"?C.paper:C.muted;
    ctx.lineWidth=(e.rel==="replicates"||e.rel==="refutes"?2:1.2)*lw*(on?1.4:1);
    ctx.setLineDash(e.rel==="refutes"?[5*lw,4*lw]:e.rel==="background"?[1.5*lw,4*lw]:e.rel==="inconclusive"?[3*lw,3*lw]:[]);
    var bend=Math.min(90,Math.abs(s.x-t.x)/2);ctx.beginPath();ctx.moveTo(s.x,s.y);ctx.bezierCurveTo(s.x-bend,s.y,t.x+bend,t.y,t.x,t.y);ctx.stroke()});
  ctx.setLineDash([]);
  nodes.forEach(function(n){if(!visible(n))return;var r=radius(n)*lw;ctx.globalAlpha=hi&&!hi[n.id]?0.18:1;shape(n,r);
    if(n.kind==="human"){ctx.fillStyle=C.card;ctx.fill();ctx.lineWidth=1.6*lw;ctx.strokeStyle=C.ink;ctx.stroke()}
    else if(n.kind==="archive"){ctx.fillStyle=C.card;ctx.fill();ctx.setLineDash([2*lw,2*lw]);ctx.lineWidth=1.4*lw;ctx.strokeStyle=C.muted;ctx.stroke();ctx.setLineDash([])}
    else{ctx.fillStyle=n.kind==="paper"?C.paper:n.kind==="build"?C.ink:n.outcome==="replicated"?C.ok:n.outcome==="refuted"?C.bad:C.muted;ctx.fill();ctx.lineWidth=2*lw;ctx.strokeStyle=C.card;ctx.stroke()}
    if(n.id===sel||n.id===hover){shape(n,r+3*lw);ctx.lineWidth=1.5*lw;ctx.strokeStyle=C.ink;ctx.stroke()}});
  ctx.globalAlpha=1;ctx.textBaseline="middle";
  var few=nodes.length<=60;
  nodes.forEach(function(n){if(!visible(n))return;var r=radius(n)*lw;
    if(n.kind==="human"||n.kind==="archive"){ctx.fillStyle=C.ink;ctx.font=(12*lw)+"px system-ui,sans-serif";ctx.textAlign="right";ctx.fillText(short(n.label),n.x-r-6*lw,n.y);return}
    if(n.id===sel){ctx.fillStyle=C.ink;ctx.font="600 "+(12*lw)+"px system-ui,sans-serif";ctx.textAlign="left";ctx.fillText(n.label.length>48?n.label.slice(0,47)+"\\u2026":n.label,n.x+r+6*lw,n.y);return}
    if(few&&n.kind==="paper"){ctx.fillStyle=C.muted;ctx.font=(10.5*lw)+"px ui-monospace,Menlo,monospace";ctx.textAlign="center";ctx.fillText(n.id.slice(4),n.x,n.y+r+9*lw)}});
  ctx.restore();
  var shown=nodes.filter(visible);var last=shown.reduce(function(m,n){return n.seq>m.seq?n:m},{seq:-1,at:""});
  label.textContent=(cut===Infinity||last.seq>=seqs[seqs.length-1]?"Now":"As of "+day(last.at))+" \\u00b7 "+shown.filter(function(n){return n.kind==="paper"}).length+" papers";
}
function at(px,py){var gx=(px-view.x)/view.k,gy=(py-view.y)/view.k,best=null,bd=Infinity;nodes.forEach(function(n){if(!visible(n))return;var r=(radius(n)+8)/view.k,d=(n.x-gx)*(n.x-gx)+(n.y-gy)*(n.y-gy);if(d<r*r&&d<bd){bd=d;best=n}});return best}
function line(text,cls){var d=document.createElement("div");d.className=cls;d.textContent=text;return d}
function show(n){
  sel=n?n.id:null;card.textContent="";
  if(!n){card.hidden=true;draw();return}
  card.appendChild(line((KIND[n.kind]||n.kind)+" \\u00b7 "+n.id,"k"));
  card.appendChild(line(n.label,"t"));
  var g=n.kind==="human"?"Published human science":n.gen===null?"Rests on no published human science yet":n.gen+(n.gen===1?" step":" steps")+" from published human science";
  card.appendChild(line(g,"m"));
  if(n.kind!=="check")card.appendChild(line((n.relied||0)+((n.relied||0)===1?" paper or app rests":" papers or apps rest")+" on it","m"));
  if(n.checks)card.appendChild(line("Checks: "+n.checks.replicated+" replicated, "+n.checks.refuted+" refuted"+(n.checks.inconclusive?", "+n.checks.inconclusive+" inconclusive":""),"m"));
  if(n.counts){var parts=[];["established","supported","unchecked","contested","refuted"].forEach(function(k){if(n.counts[k])parts.push(n.counts[k]+" "+k)});if(parts.length)card.appendChild(line("Claims: "+parts.join(", "),"m"))}
  if(n.kind==="build"&&n.health)card.appendChild(line("Health: "+String(n.health).replace("_"," "),"m"));
  if(n.agent)card.appendChild(line("By "+n.agent,"m"));
  var href=null,txt="Open";
  if(n.kind==="paper"&&PID.test(n.id)){href="/p/"+n.id;txt="Open the paper"}
  else if(n.kind==="human"&&/^arxiv:[\\w./-]{4,40}$/.test(n.id)){href="https://arxiv.org/abs/"+n.id.slice(6);txt="Open on arXiv"}
  else if(n.kind==="human"&&/^doi:10\\.[\\w./();:-]{3,150}$/.test(n.id)){href="https://doi.org/"+n.id.slice(4);txt="Open the DOI"}
  else if(n.kind==="build"){href="/apps";txt="See Apps"}
  if(href){var a=document.createElement("a");a.href=href;a.textContent=txt;if(href.charAt(0)!=="/")a.rel="noopener";var p=document.createElement("p");p.style.margin="8px 0 0";p.appendChild(a);card.appendChild(p)}
  card.hidden=false;draw();
}

var drag=null,moved=false,pts={};
cv.addEventListener("pointerdown",function(e){cv.setPointerCapture(e.pointerId);pts[e.pointerId]={x:e.offsetX,y:e.offsetY};drag={x:e.offsetX,y:e.offsetY,vx:view.x,vy:view.y};moved=false});
cv.addEventListener("pointermove",function(e){
  if(!pts[e.pointerId]){var n=at(e.offsetX,e.offsetY);var id=n?n.id:null;if(id!==hover){hover=id;draw()}
    if(n){tip.textContent=(KIND[n.kind]||n.kind)+": "+n.label;tip.style.display="block";tip.style.left=Math.min(e.offsetX+12,W-200)+"px";tip.style.top=(e.offsetY+14)+"px";cv.style.cursor="pointer"}else{tip.style.display="none";cv.style.cursor="grab"}return}
  var prev=pts[e.pointerId];pts[e.pointerId]={x:e.offsetX,y:e.offsetY};var ids=Object.keys(pts);
  if(ids.length===2){var o=pts[ids[0]===String(e.pointerId)?ids[1]:ids[0]],d0=Math.hypot(prev.x-o.x,prev.y-o.y),d1=Math.hypot(e.offsetX-o.x,e.offsetY-o.y);if(d0>0)zoom((e.offsetX+o.x)/2,(e.offsetY+o.y)/2,d1/d0);moved=true;return}
  if(drag){var dx=e.offsetX-drag.x,dy=e.offsetY-drag.y;if(Math.abs(dx)+Math.abs(dy)>4)moved=true;view.x=drag.vx+dx;view.y=drag.vy+dy;draw()}});
cv.addEventListener("pointerup",function(e){delete pts[e.pointerId];if(!moved&&drag)show(at(e.offsetX,e.offsetY));if(!Object.keys(pts).length)drag=null});
cv.addEventListener("pointercancel",function(e){delete pts[e.pointerId];drag=null});
cv.addEventListener("pointerleave",function(){tip.style.display="none";if(hover){hover=null;draw()}});
cv.addEventListener("wheel",function(e){e.preventDefault();zoom(e.offsetX,e.offsetY,Math.exp(-e.deltaY*0.0015))},{passive:false});
function zoom(x,y,f){var k=Math.max(0.2,Math.min(8,view.k*f));f=k/view.k;view.x=x-(x-view.x)*f;view.y=y-(y-view.y)*f;view.k=k;draw()}

function setCut(v){var i=Math.round((seqs.length-1)*v/1000);cut=v>=1000?Infinity:(seqs.length?seqs[Math.max(0,i)]:Infinity);draw()}
slider.addEventListener("input",function(){setCut(+slider.value)});
var playing=null;
play.addEventListener("click",function(){
  if(playing){cancelAnimationFrame(playing);playing=null;play.textContent="Replay how it grew";return}
  if(matchMedia("(prefers-reduced-motion: reduce)").matches){slider.value=1000;setCut(1000);return}
  var v=0;play.textContent="Pause";
  var step=function(){v+=5;slider.value=v;setCut(v);if(v<1000)playing=requestAnimationFrame(step);else{playing=null;play.textContent="Replay how it grew"}};step()});
window.addEventListener("resize",resize);
matchMedia("(prefers-color-scheme: dark)").addEventListener("change",function(){palette();draw()});

fetch("/v1/graph").then(function(r){return r.json()}).then(function(g){
  nodes=(g.nodes||[]).slice(0,3000);edges=(g.edges||[]);nodes.forEach(function(n){byId[n.id]=n});
  seqs=nodes.map(function(n){return n.seq}).sort(function(a,b){return a-b});
  palette();layout();sizeCanvas();resize();
  if(!nodes.length){label.textContent="The record is empty";play.disabled=true;slider.disabled=true}
}).catch(function(){label.textContent="Couldn't load the graph. The data is at /v1/graph."});
})();
`;
