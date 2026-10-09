/**
 * The Ecdysis design system: one shell, one stylesheet, every human page.
 *
 * Identity, from the brand kit of 3 October 2026 (Lucy Griffiths): the
 * layered orange dragonfly and a lowercase serif wordmark, supplied as SVG
 * and never redrawn (src/web/brand.ts). Soft white #F7F8FA and ink #242629
 * swap between light and dark; signal orange #FF8A24 is a deliberate accent
 * (buttons, the mark of attention), never body text, never a background
 * wash; the two paler orange tints belong to the emblem alone. Pages stay
 * overwhelmingly monochrome. Serif headings (Georgia and its cousins, the
 * kit's system fallback), a plain sans for reading and interface, monospace
 * only where it does a job (hashes and ecd: ids). The reference quality is
 * a well-designed scholarly book cover: decisive shapes, refined serif
 * headings, careful negative space, no unnecessary boxes.
 *
 * The record behaves like a natural-history collection: each claim is a
 * catalogued specimen, and the signature element is the specimen label, a
 * white card with a thin ink rule carrying the catalogue data. Status is
 * never carried by colour alone: each status mark is a glyph and a word,
 * with fill, outline and the one accent as the second signal (established
 * filled ink, supported outlined, unchecked dashed, contested orange,
 * refuted crossed), so it reads the same to every eye and in print.
 *
 * Accessibility, as the kit asks: 44px interactive targets, visible
 * keyboard focus, a skip link, every image with the right alt, reduced
 * motion respected, body text 55–75 characters a line, contrast checked
 * (ink on orange 7.3:1; muted text 6.4:1 on soft white).
 *
 * The site is split in two halves, people and agents, with the person's own
 * page beside them in the top bar.
 */

import { brandLockup, LOGO_SYMBOL } from "./brand.js";

export type Half = "people" | "agents" | "me" | "none";

/** Escape text for HTML element and attribute contexts. */
export function esc(s: string): string {
  return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]!);
}

/** The emblem inline, for places that cannot load an image (the legacy console, error pages); the kit's symbol, unchanged, sized by CSS. */
export const MARK = LOGO_SYMBOL.replace("<svg ", '<svg class="mark" aria-hidden="true" focusable="false" ').replace(/ role="img" aria-label="Ecdysis"/, "").replace("<title>Ecdysis</title>", "");

export const CSS = `
:root{--ground:#F7F8FA;--card:#FFFFFF;--ink:#242629;--muted:#5B5F64;--rule:#73767A;--line:#D9DBDF;--accent:#FF8A24;--on-accent:#242629;--amber:#B85C00;--on-amber:#FFFFFF;--sound:#242629;--risk:#FF8A24;--broken:#242629;
--serif:Georgia,"Times New Roman","Iowan Old Style",Charter,serif;
--sans:Arial,Helvetica,"Helvetica Neue",system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
--mono:ui-monospace,"SF Mono",Menlo,Consolas,monospace;
--s1:4px;--s2:8px;--s3:12px;--s4:16px;--s5:24px;--s6:32px;--s7:48px;--s8:64px;--s9:96px;--s10:128px;color-scheme:light}
@media (prefers-color-scheme:dark){:root{--ground:#242629;--card:#2C2F33;--ink:#F7F8FA;--muted:#B4B8BD;--rule:#8A8E93;--line:#41454A;--accent:#FF8A24;--on-accent:#242629;--amber:#FFB36B;--on-amber:#242629;--sound:#F7F8FA;--broken:#F7F8FA;color-scheme:dark}}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--ground);color:var(--ink);font:18px/1.6 var(--sans);overflow-wrap:break-word}
a{color:var(--ink);text-decoration:underline;text-decoration-color:var(--rule);text-underline-offset:.2em}
a:hover{text-decoration-color:var(--accent);text-decoration-thickness:2px}
:focus-visible{outline:2px solid var(--ink);outline-offset:4px}
.skip{position:absolute;left:-9999px}
.skip:focus{left:16px;top:10px;background:var(--card);padding:10px 14px;border:1px solid var(--ink);z-index:20}
.wrap{max-width:42rem;margin:0 auto;padding:0 clamp(24px,5vw,48px)}
.wrap.wide{max-width:75rem}
.frame{max-width:75rem;margin:0 auto;padding:0 clamp(24px,5vw,48px)}
.top{display:flex;align-items:center;justify-content:space-between;gap:12px 24px;flex-wrap:wrap;padding:24px 0 12px}
.brand{display:inline-flex;align-items:center;color:var(--ink);text-decoration:none;min-height:44px}
.brand .lockup{display:block;width:240px;max-width:100%;height:auto}
.brand .symbol{display:none;width:48px;height:auto}
@media (max-width:420px){.brand .lockup{width:190px}}
@media (max-width:300px){.brand .lockup{display:none}.brand .symbol{display:block}}
.mark{width:28px;height:auto;vertical-align:middle}
.halves{display:inline-flex;align-items:center;gap:12px;font:16px/1 var(--sans);flex-wrap:wrap}
.halves .seg{display:inline-flex;border:1px solid var(--ink);border-radius:6px;overflow:hidden}
.halves .seg a{display:inline-flex;align-items:center;min-height:44px;padding:0 16px;color:var(--ink);text-decoration:none}
.halves .seg a+a{border-left:1px solid var(--ink)}
.halves .seg a[aria-current="true"]{background:var(--ink);color:var(--ground)}
.halves .me{display:inline-flex;align-items:center;gap:8px;min-height:44px;padding:0 16px;border:1px solid var(--rule);border-radius:6px;color:var(--ink);text-decoration:none}
.halves .me::before{content:"";width:8px;height:8px;border-radius:50%;background:var(--accent)}
.halves .me:hover,.halves .seg a:hover{background:var(--card)}
.halves .seg a[aria-current="true"]:hover{background:var(--ink)}
.halves .me[aria-current="true"]{border-color:var(--ink);background:var(--card);font-weight:700}
.tag{font:600 11px/1 var(--sans);letter-spacing:.12em;text-transform:uppercase;color:var(--on-accent);background:var(--accent);padding:5px 7px;border-radius:3px;margin-left:12px;vertical-align:middle}
.top .who{font:14px/1.4 var(--sans);color:var(--muted);flex:1 1 12rem}
.top .who a{color:var(--muted)}
.sub{display:flex;flex-wrap:wrap;gap:0 8px;font:16px/1 var(--sans);border-bottom:1px solid var(--line);padding:4px 0 0;margin:0 0 8px}
.sub a{display:inline-flex;align-items:center;min-height:44px;padding:0 8px;color:var(--muted);text-decoration:none;border-bottom:2px solid transparent;margin-bottom:-1px}
.sub a:hover{color:var(--ink)}
.sub a[aria-current="page"]{color:var(--ink);border-bottom-color:var(--accent)}
main{padding:clamp(32px,5vw,56px) 0 clamp(48px,7vw,96px)}
h1{font:400 clamp(2.25rem,5vw,3.5rem)/1.08 var(--serif);letter-spacing:-.025em;margin:0 0 24px;text-wrap:balance;max-width:22ch}
h2{font:400 clamp(1.5rem,2.6vw,1.85rem)/1.2 var(--serif);letter-spacing:-.015em;margin:48px 0 16px;text-wrap:balance}
h3{font:400 1.2rem/1.3 var(--serif);margin:0 0 6px}
p{margin:0 0 16px}
ul,ol{padding-left:1.25em}
.lede{font-size:1.2rem;line-height:1.5;color:var(--muted);max-width:40rem;margin-bottom:32px}
.small{font:15px/1.55 var(--sans);color:var(--muted)}
.eyebrow{font:15px/1.4 var(--sans);color:var(--muted);margin:0 0 14px}
.mono{font-family:var(--mono);font-size:.86em;overflow-wrap:anywhere}
.label{background:var(--card);border:1px solid var(--ink);padding:14px 16px;font:15px/1.45 var(--sans);color:var(--ink);max-width:38rem}
.label .no{font:13px/1.3 var(--mono);color:var(--muted);overflow-wrap:anywhere}
.label .what{display:block;font:1.15rem/1.3 var(--serif);color:var(--ink);margin:4px 0 8px;text-decoration:none}
.label a.what:hover{text-decoration:underline;text-decoration-color:var(--accent)}
.label .meta{display:flex;flex-wrap:wrap;gap:2px 14px;color:var(--muted)}
.status{display:inline-flex;align-items:center;gap:6px;margin-top:8px;font:600 12.5px/1 var(--sans);padding:5px 8px;border:1px solid var(--ink);border-radius:3px;color:var(--ink);background:var(--card)}
.status::before{font-size:10px;line-height:1}
.status.sound{background:var(--ink);color:var(--ground)}.status.sound::before{content:"\\25CF"}
.status.part::before{content:"\\25D0"}
.status.open{border-style:dashed;color:var(--muted)}.status.open::before{content:"\\25CB"}
.status.risk{background:var(--accent);color:var(--on-accent);border-color:var(--accent)}.status.risk::before{content:"\\25C6"}
.status.broken::before{content:"\\2715";font-weight:700}
dl.kv{display:inline-flex;flex-wrap:wrap;align-items:baseline;gap:4px;margin:0 0 0 10px;font:14px/1.4 var(--sans);color:var(--muted);vertical-align:middle}
dl.kv dt{margin-left:14px}dl.kv dt:first-child{margin-left:0}dl.kv dd{margin:0;color:var(--ink);font-weight:600;font-variant-numeric:tabular-nums}
.labels{list-style:none;padding:0;margin:0;display:grid;gap:12px}
.label+p{margin-top:10px}
.notice{background:var(--card);border:1px solid var(--line);border-left:4px solid var(--accent);padding:12px 16px;font:15px/1.5 var(--sans);margin:0 0 24px;max-width:44rem}
.doors{display:grid;grid-template-columns:repeat(auto-fit,minmax(16rem,1fr));gap:24px;margin:8px 0}
.door{display:flex;flex-direction:column;background:var(--card);border:1px solid var(--line);border-top:3px solid var(--ink);padding:24px 24px 22px;color:var(--ink);text-decoration:none;min-height:44px}
.door:hover{border-color:var(--ink)}
.door .who{display:block;flex:0 0 auto;font:400 1.75rem/1.15 var(--serif);letter-spacing:-.02em;margin:0 0 8px}
.door .what{display:block;font:16px/1.5 var(--sans);color:var(--muted);margin:0 0 20px;flex:1}
.btn{display:inline-flex;align-items:center;justify-content:center;min-height:44px;background:var(--accent);color:var(--on-accent);font:600 16px/1 var(--sans);padding:0 20px;border-radius:6px;text-decoration:none;border:1px solid var(--accent);cursor:pointer}
.btn:hover{background:#FF9B45;border-color:#FF9B45}
form label{display:block;margin:0 0 6px}
input[type=email],input[type=text],input[type=number],select{display:block;font:16px/1.4 var(--sans);color:var(--ink);background:var(--card);border:1px solid var(--ink);border-radius:4px;padding:10px 12px;min-height:44px;width:100%;max-width:32rem;margin:0 0 12px}
fieldset{border:1px solid var(--line);padding:8px 16px 12px;margin:0 0 16px;max-width:44rem}
legend{font:15px/1.3 var(--sans);color:var(--muted);padding:0 4px}
form label.opt{display:inline-flex;align-items:center;gap:8px;min-height:44px;margin:0 18px 0 0;font:16px/1.4 var(--sans)}
.hp,.sr{position:absolute;left:-9999px;width:1px;height:1px;overflow:hidden}
.btn.quiet{background:transparent;color:var(--ink);border:1px solid var(--ink)}
.btn.quiet:hover{background:var(--card)}
.btn.danger{background:transparent;color:var(--ink);border:1px solid var(--ink);text-decoration:underline;text-decoration-color:var(--accent)}
textarea{display:block;width:100%;font:14px/1.5 var(--mono);color:var(--ink);background:var(--card);border:1px solid var(--ink);border-radius:4px;padding:10px 12px;margin:0 0 8px;resize:vertical}
textarea::placeholder{color:var(--muted)}
.prompt{background:var(--card);border:1px solid var(--line);border-left:3px solid var(--ink);margin:12px 0 24px}
.prompt h3{padding:16px 16px 0}
.prompt .why{padding:0 16px;font:15px/1.45 var(--sans);color:var(--muted);margin:2px 0 0}
.prompt .pt{font:15px/1.55 var(--sans);background:var(--ground);padding:12px 14px;margin:10px 16px 16px;border-radius:4px;-webkit-user-select:all;user-select:all;cursor:text;overflow-wrap:anywhere}
.prompt.habit{border-left-color:var(--line)}
.prompt pre.kit{white-space:pre-wrap;font:12.5px/1.5 var(--mono);max-height:26rem;overflow:auto;border:0}
.prompt.habit .pt{margin-top:8px}
.rows{list-style:none;padding:0;margin:0;border-top:1px solid var(--line)}
.rows li{padding:16px 0;border-bottom:1px solid var(--line)}
.rows .t{display:block;font:400 1.15rem/1.35 var(--serif)}
.rows .d{display:block;font:16px/1.5 var(--sans);color:var(--muted);margin-top:4px}
code{font-family:var(--mono);font-size:.86em;background:var(--card);border:1px solid var(--line);padding:1px 5px;border-radius:3px;overflow-wrap:anywhere}
pre{font:13.5px/1.5 var(--mono);background:var(--card);border:1px solid var(--line);padding:12px 14px;overflow-x:auto;margin:0 0 16px}
pre code{border:0;padding:0;background:none}
.claims{padding-left:1.4em}
.claims li{margin:0 0 16px}
.claims li p{margin:0 0 4px}
.summary{font:1.15rem/1.6 var(--serif);max-width:44rem}
.summary b{font-weight:700}
.chart{background:var(--card);border:1px solid var(--line);padding:16px 16px 12px}
.chart svg{display:block;width:100%;height:auto;margin:6px 0 4px}
.tip{position:fixed;pointer-events:none;background:var(--ink);color:var(--ground);font:13px/1.3 var(--sans);padding:5px 8px;border-radius:4px;display:none;z-index:10}
details summary{cursor:pointer;font:15px/1.4 var(--sans);color:var(--muted);margin-top:6px;min-height:44px;display:flex;align-items:center}
table{border-collapse:collapse;font:15px/1.45 var(--sans);width:100%;margin:4px 0 8px}
.scroll{overflow-x:auto;max-width:100%}
@media (max-width:680px){main table:not(.vs):not(.cmp):not(.ledger){display:block;overflow-x:auto;max-width:100%}}
th,td{text-align:left;padding:8px 10px 8px 0;border-bottom:1px solid var(--line);vertical-align:top}
th{font-weight:600;color:var(--muted)}
td{font-variant-numeric:tabular-nums}
.grid2{display:grid;grid-template-columns:repeat(auto-fit,minmax(22rem,1fr));gap:24px 48px}
.grid2 section{min-width:0}
.hbar{display:grid;grid-template-columns:7rem 1fr 2.5rem;align-items:center;gap:10px;font:14px/1.4 var(--sans);margin:6px 0}
.hbar .bar{display:block;height:10px;border-radius:0 4px 4px 0}
.check{padding:10px 0;border-bottom:1px solid var(--line);font:15px/1.45 var(--sans)}
.check .small{margin-top:3px}
.feeds{display:flex;flex-wrap:wrap;gap:6px 16px;font:15px/1.5 var(--sans)}
.pfilter{background:var(--card);border:1px solid var(--line);padding:12px 16px 4px;margin:0 0 16px;max-width:44rem}
.pfilter label{font:14px/1.4 var(--sans);color:var(--muted)}
.pfrow{display:flex;flex-wrap:wrap;gap:8px 14px;align-items:flex-end}
.pfrow label{display:flex;flex-direction:column;gap:4px}
.pfrow select{width:auto;margin:0 0 10px}
.pfrow .btn{margin:0 0 10px}
.fun{margin:0 0 12px}
.fun-h{display:flex;justify-content:space-between;gap:10px;font:14px/1.4 var(--sans);margin:0 0 4px}
.meter{display:block;height:8px;border-radius:4px;background:var(--line);overflow:hidden}
.meter>span{display:block;height:100%;background:var(--accent);border-radius:4px}
.lineage{list-style:none;padding:0;margin:8px 0 14px;max-width:44rem}
.lineage li{position:relative;padding:0 0 12px 26px;font:15px/1.45 var(--sans)}
.lineage li::before{content:"";position:absolute;left:7px;top:0;bottom:0;width:2px;background:var(--line)}
.lineage li:last-child::before{bottom:auto;height:10px}
.lineage li::after{content:"";position:absolute;left:2px;top:5px;width:12px;height:12px;border-radius:50%;background:var(--accent);border:2px solid var(--ground)}
.lineage li.human::after{background:var(--card);border:2px solid var(--ink)}
.lineage .g{display:block;font:13px/1.4 var(--sans);color:var(--muted)}
.openin{display:flex;flex-wrap:wrap;align-items:center;gap:6px 8px;padding:0 16px 14px;margin:-4px 0 0;font:13px/1.2 var(--sans);color:var(--muted)}
.openin a{display:inline-flex;align-items:center;min-height:36px;font:600 13px/1 var(--sans);padding:0 12px;border:1px solid var(--line);border-radius:5px;color:var(--ink);text-decoration:none;background:var(--card)}
.openin a:hover{border-color:var(--ink)}
.mcpin{display:flex;flex-wrap:wrap;gap:8px;margin:8px 0 12px}
.figs{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,21rem),1fr));gap:24px;margin:16px 0 8px}
@media (min-width:1100px){.figs.three-two{grid-template-columns:repeat(6,minmax(0,1fr))}.figs.three-two>.fig{grid-column:span 2}.figs.three-two>.fig:nth-child(n+4){grid-column:span 3}}
.fig{margin:0 0 24px;background:var(--card);border:1px solid var(--line);padding:16px 18px 12px;min-width:0}
.figs .fig{margin:0}
.fig.illustrative{border:1px dashed var(--rule)}
.fig.wide{grid-column:1/-1}
.fig figcaption{display:flex;flex-wrap:wrap;align-items:center;gap:6px 12px;margin:0 0 14px}
.fig-title{font:400 1.2rem/1.3 var(--serif);color:var(--ink)}
.fig-caption{flex-basis:100%;font:14px/1.5 var(--sans);color:var(--muted)}
.mock{display:inline-block;font:600 11px/1 var(--sans);letter-spacing:.08em;text-transform:uppercase;color:var(--on-accent);background:var(--accent);padding:5px 7px;border-radius:3px;white-space:nowrap}
.notice .mock{margin-right:8px;vertical-align:middle}
.bars{list-style:none;padding:0;margin:4px 0 8px;display:grid;gap:8px;font:14px/1.3 var(--sans)}
.bars li{display:grid;grid-template-columns:minmax(5.5rem,8.5rem) minmax(0,1fr) 3rem;align-items:center;gap:10px;min-width:0}
.bars .k{text-align:right;overflow-wrap:anywhere;color:var(--ink)}
.bars .k a{text-decoration-color:var(--line)}
.bars .k .g{display:inline-block;width:1.1em;font-size:.95em;color:var(--ink)}
.bars .b{display:block;height:14px;background:var(--ground);border-radius:3px;overflow:hidden}
.bars .f{display:block;height:100%;border-radius:3px;box-sizing:border-box}
.bars .v{font-variant-numeric:tabular-nums;color:var(--ink)}
.f.ink,.f.sound,.c.ink,.c.sound{background:var(--ink)}
.f.mid,.f.part,.c.mid,.c.part{background:var(--rule)}
.f.pale,.c.pale{background:var(--line)}
.f.open,.c.open{background:var(--card);border:1px dashed var(--rule)}
.f.accent,.f.risk,.c.accent,.c.risk{background:var(--accent)}
.f.broken,.c.broken{background:var(--card);border:2px solid var(--ink)}
.hist{list-style:none;margin:8px 0 38px;padding:0;display:grid;grid-template-columns:repeat(var(--n),minmax(0,1fr));gap:4px;height:200px;border-bottom:1px solid var(--rule)}
.hist li{position:relative;min-width:0;height:100%}
.hist .c{position:absolute;left:0;right:0;bottom:0;height:var(--h);border-radius:3px 3px 0 0;box-sizing:border-box}
.hist .v{position:absolute;left:0;right:0;bottom:calc(var(--h) + 4px);text-align:center;font:12px/1 var(--sans);color:var(--ink);font-variant-numeric:tabular-nums}
.hist .x{position:absolute;left:0;right:0;top:calc(100% + 6px);text-align:center;font:11px/1.2 var(--sans);color:var(--muted);overflow-wrap:anywhere}
@media (max-width:480px){.hist .x{font-size:10px}.hist .v{font-size:11px}}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,9.5rem),1fr));gap:16px;margin:8px 0 24px}
.stat{display:flex;flex-direction:column;gap:4px;background:var(--card);border:1px solid var(--line);border-top:3px solid var(--ink);padding:14px 16px 12px;min-width:0}
.stat.warn{border-top-color:var(--accent)}
.stat-v{font:400 2rem/1.1 var(--serif);letter-spacing:-.02em;font-variant-numeric:tabular-nums;color:var(--ink);overflow-wrap:anywhere}
.stat-l{font:600 13px/1.3 var(--sans);color:var(--ink)}
.stat-n{font:13px/1.4 var(--sans);color:var(--muted)}
.stat.warn .stat-n::before{content:"\\25C6  ";color:var(--accent)}
.steps{list-style:none;padding:0;margin:8px 0 24px;display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,11.5rem),1fr));gap:28px 28px}
.step{min-width:0}
.step-n{display:inline-flex;align-items:center;justify-content:center;width:28px;height:28px;border-radius:50%;background:var(--accent);color:var(--on-accent);font:600 14px/1 var(--sans);margin:0 10px 12px 0;vertical-align:middle}
.step-icon{display:inline-block;width:44px;height:44px;vertical-align:middle;margin:0 0 12px}
.step h3{margin:0 0 6px}
.step p{font-size:16px;line-height:1.55;color:var(--muted);margin:0}
.fig svg{display:block;width:100%;height:auto}
.fig .scroll{overflow-x:auto;margin:0 -2px}
.fig .scroll svg{min-width:640px}
.fig .scroll-hint{display:none;margin:6px 0 0}
@media (max-width:680px){.fig .scroll-hint{display:block}}
.fig svg text{font-family:var(--sans)}
.fig svg .lbl{font-size:13px;fill:var(--ink);paint-order:stroke;stroke:var(--card);stroke-width:4px;stroke-linejoin:round}
.fig svg .lbl.muted{fill:var(--muted);font-size:12px}
.fig svg .lbl.x{font-size:11px;font-weight:700;stroke:none}
.fig details summary{margin-top:8px}
.fig table{font-size:14px}
.md ul,.md ol{padding-left:1.4em;margin:0 0 16px}
.md li{margin:0 0 10px}
.md li>p{margin:0}
.md h2,.md h3{text-wrap:balance}
.md .table{overflow-x:auto;margin:0 0 16px}
.md table{font-size:15px;min-width:36rem}
.md pre{font-size:13px;line-height:1.5;max-height:40rem;overflow:auto}
.md img{display:none}
.fig.diagram .scroll svg{min-width:680px}
.fig.diagram svg .lbl{stroke:none}
.wrap:not(.wide) .fig.diagram{width:min(800px,calc(100vw - 48px));margin-left:calc(50% - min(400px,(100vw - 48px) / 2))}
.fig svg .lbl.b{font-weight:700}
.flow{list-style:none;margin:8px 0 4px;padding:0;display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,6rem),1fr));gap:12px 22px}
.flow li{position:relative;min-width:0;display:flex;flex-direction:column;gap:3px;padding:12px 12px 10px;border:1.5px solid var(--ink);border-radius:4px;background:var(--ground)}
.flow li+li::before{content:"\\2192";position:absolute;left:-20px;top:10px;color:var(--rule);font:18px/1 var(--sans)}
.flow b{font:400 1.1rem/1.2 var(--serif);color:var(--ink)}
.flow span{font:14px/1.4 var(--sans);color:var(--ink)}
.flow small{font:12.5px/1.4 var(--sans);color:var(--muted)}
.wrap:not(.wide) .flow{grid-template-columns:1fr;gap:18px}
.wrap:not(.wide) .flow li+li::before{content:"\\2193";left:14px;top:-20px}
@media (max-width:640px){.flow{grid-template-columns:1fr;gap:18px}.flow li+li::before{content:"\\2193";left:14px;top:-20px}}
.cmp-cap{margin:8px 0 4px}
.cmp-key{display:flex;flex-wrap:wrap;gap:2px 18px;margin:0 0 8px}
.cmp-wrap{overflow-x:auto;margin:0 0 8px;border-top:1px solid var(--ink);border-bottom:1px solid var(--ink)}
.wrap:not(.wide) .cmp-wrap{width:min(960px,calc(100vw - 48px));margin-left:calc(50% - min(480px,(100vw - 48px) / 2))}
.cmp{border-collapse:separate;border-spacing:0;width:100%;min-width:46rem;margin:0;font:15px/1.4 var(--sans)}
.cmp th,.cmp td{padding:12px 8px;border-bottom:1px solid var(--line);text-align:center;vertical-align:middle}
.cmp tbody tr:last-child th,.cmp tbody tr:last-child td{border-bottom:0}
.cmp thead th{font:600 14px/1.2 var(--sans);color:var(--ink);white-space:nowrap;padding:14px 8px 10px;border-bottom:1px solid var(--ink)}
.cmp th[scope=row]{position:sticky;left:0;z-index:1;text-align:left;background:var(--ground);min-width:14rem;max-width:18rem;padding:12px 14px 12px 0}
.cmp thead th:first-child{position:sticky;left:0;z-index:2;background:var(--ground)}
.cmp th[scope=row] .t{display:block;font:400 1.05rem/1.3 var(--serif);color:var(--ink)}
.cmp th[scope=row] .d{display:block;font:13.5px/1.4 var(--sans);color:var(--muted);margin-top:3px}
.cmp .us{background:var(--card)}
.cmp thead th.us{box-shadow:inset 0 3px 0 var(--accent)}
.dot{display:inline-block;box-sizing:border-box;width:13px;height:13px;border-radius:50%;border:2px solid var(--ink);overflow:hidden;vertical-align:middle}
.dot.yes{background:var(--ink)}
.dot.part::before{content:"";display:block;width:50%;height:100%;background:var(--ink)}
.cmp-key .dot{margin-right:4px;vertical-align:-1px}
.cmp-key .g{color:var(--rule);margin-right:2px}
.cmp td .g{font-size:16px;line-height:1;color:var(--rule)}
.cmp td sup{font-size:11px;margin-left:2px;color:var(--muted)}
.cmp-hint{display:none}
@media (max-width:760px){.cmp-hint{display:block}}
@media (max-width:520px){.cmp{font-size:14px;min-width:36rem}.cmp th[scope=row]{min-width:9.5rem;max-width:11rem;padding-right:10px}.cmp th[scope=row] .t{font-size:.95rem}.cmp th[scope=row] .d{font-size:12px}.cmp th,.cmp td{padding:10px 6px}}
.notes{font:14px/1.5 var(--sans);color:var(--muted);padding-left:1.4em;margin:12px 0 24px;max-width:44rem}
.notes li{margin:0 0 6px}
.sources{font:15px/1.5 var(--sans);padding-left:1.2em;margin:0 0 16px;max-width:44rem}
.sources li{margin:0 0 8px}
.actions{display:flex;flex-wrap:wrap;gap:12px;margin:8px 0 16px}
.verb{display:inline-block;font:700 12px/1 var(--mono);letter-spacing:.04em;padding:4px 7px;border-radius:3px;border:1px solid var(--ink);color:var(--ink);background:var(--card);vertical-align:middle}
.verb.post{background:var(--ink);color:var(--ground)}
.req{font:600 12px/1 var(--sans);color:var(--accent);letter-spacing:.02em}
.op{border-top:1px solid var(--line);padding:16px 0 8px;margin:0 0 8px}
.op h3{margin:0 0 8px;overflow-wrap:anywhere}.op h4{font:600 14px/1.3 var(--sans);color:var(--muted);text-transform:uppercase;letter-spacing:.04em;margin:16px 0 6px}
dl.schema{margin:0 0 8px;padding-left:0;border-left:2px solid var(--line)}
dl.schema dt{margin:8px 0 0 12px;font:15px/1.4 var(--sans)}dl.schema dd{margin:2px 0 0 12px;font:15px/1.5 var(--sans);color:var(--ink);max-width:48rem}
dl.schema dl.schema{margin:6px 0 0 0}
.rows .d .verb{font-size:11px;padding:3px 5px}
.vs{width:100%;max-width:44rem;border-collapse:collapse;margin:8px 0 12px;font:16px/1.45 var(--sans)}
.vs th{font:600 14px/1.2 var(--sans);color:var(--muted);text-align:left;padding:0 16px 10px 0;border-bottom:1px solid var(--ink)}
.vs th.us{color:var(--ink);box-shadow:inset 0 -3px 0 var(--accent)}
.vs td{width:50%;padding:12px 16px 12px 0;border-bottom:1px solid var(--line);vertical-align:top}
.vs td:first-child{color:var(--muted)}
.vs td:last-child{color:var(--ink);font-weight:600}
@media (max-width:520px){.vs{font-size:15px}}
.jump{display:flex;flex-wrap:wrap;gap:0 20px;font:15px/1.4 var(--sans);margin:0 0 8px}
.jump a{display:inline-flex;align-items:center;min-height:44px;color:var(--muted)}
.faq{border-top:1px solid var(--line);margin:0 0 8px;max-width:44rem}
.faq details{border-bottom:1px solid var(--line)}
.faq summary{display:flex;align-items:center;gap:16px;min-height:44px;margin:0;padding:14px 0;list-style:none;font:400 1.15rem/1.35 var(--serif);color:var(--ink)}
.faq summary::-webkit-details-marker{display:none}
.faq summary::after{content:"+";flex:0 0 auto;margin-left:auto;font:400 1.5rem/1 var(--sans);color:var(--muted)}
.faq details[open] summary::after{content:"\\2212"}
.faq summary:hover{text-decoration:underline;text-decoration-color:var(--accent);text-underline-offset:.2em}
.faq .a{padding:0 0 18px;max-width:40rem}
.faq .a p{margin:0 0 10px}
.faq .a p:last-child{margin:0}
.trace-fig{max-width:56rem}
.trace{list-style:none;padding:0;margin:0}
.trace li{display:grid;grid-template-columns:minmax(0,1fr) minmax(12rem,20rem);gap:8px 24px;align-items:center;padding:14px 0;border-bottom:1px solid var(--line)}
.trace li:last-child{border-bottom:0}
.trace .tx b{display:block;font:400 1.08rem/1.3 var(--serif);color:var(--ink)}
.trace .tx span{display:block;font:14px/1.45 var(--sans);color:var(--muted);margin-top:2px}
.trace .tm{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:8px 12px;align-items:center}
.trace .gauge{position:relative;display:block;height:10px;border-radius:5px;background:var(--line)}
.trace .gauge .fill{position:absolute;left:0;top:0;bottom:0;border-radius:5px;background:var(--ink)}
.trace .gauge .bar{position:absolute;top:-6px;bottom:-6px;width:3px;margin-left:-1.5px;border-radius:2px;background:var(--accent)}
.trace .tv{font:600 15px/1 var(--sans);font-variant-numeric:tabular-nums;color:var(--ink)}
.trace .status{grid-column:1/-1;justify-self:start;margin-top:0}
@media (max-width:600px){.trace li{grid-template-columns:1fr}}
.trace-key{display:flex;flex-wrap:wrap;gap:4px 20px;font:14px/1.4 var(--sans);color:var(--muted);margin:10px 0 0}
.trace-key i{display:inline-block;vertical-align:middle;margin-right:8px}
.trace-key .k-fill{width:20px;height:8px;border-radius:4px;background:var(--ink)}
.trace-key .k-bar{width:3px;height:16px;border-radius:2px;background:var(--accent)}
footer{border-top:1px solid var(--line);padding:24px 0 56px;font:15px/1.6 var(--sans);color:var(--muted)}
footer a{color:var(--muted)}
footer .links{display:flex;flex-wrap:wrap;gap:4px 20px}
footer .links a{display:inline-flex;align-items:center;min-height:44px}
footer .foot-brand{display:flex;align-items:center;gap:12px;margin:0 0 8px}
footer .foot-brand .symbol{width:40px;height:auto}
.catalogue{margin:8px 0 32px}
.tq{display:flex;flex-wrap:wrap;gap:10px 12px;align-items:flex-end;margin:0 0 14px;padding:14px 16px;background:var(--card);border:1px solid var(--line);border-radius:6px}
.tq label{display:flex;flex-direction:column;gap:5px;margin:0;font:600 13px/1.2 var(--sans);color:var(--muted)}
.tq .q{flex:1 1 16rem;min-width:0}
.tq input[type=search],.tq select{display:block;margin:0;width:100%;max-width:none;min-height:44px;padding:8px 12px;font:15px/1.3 var(--sans);color:var(--ink);background:var(--ground);border:1px solid var(--rule);border-radius:4px}
.tq select{width:auto;min-width:8.5rem}
.tq input[type=search]:focus,.tq select:focus{border-color:var(--ink)}
.tq .btn{min-height:44px}
.tq .reset{align-self:center;font:15px/1.3 var(--sans);color:var(--muted);min-height:44px;display:inline-flex;align-items:center}
.pills{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:0 0 10px}
.pill{display:inline-flex;align-items:center;gap:8px;min-height:36px;padding:0 12px;border:1px solid var(--rule);border-radius:18px;background:var(--card);color:var(--ink);text-decoration:none;font:14px/1 var(--sans)}
.pill:hover{border-color:var(--ink)}
.pill .x{font-size:16px;color:var(--muted)}
.pill.on{border-color:var(--ink);background:var(--ink);color:var(--ground)}.pill.on .x{color:var(--ground)}
.count{font:14px/1.4 var(--sans);color:var(--muted);margin:0 0 4px}
.ledger-scroll{overflow-x:auto}
table.ledger{width:100%;border-collapse:collapse;font:15px/1.45 var(--sans);margin:0}
.ledger thead th{font:600 13px/1.25 var(--sans);color:var(--muted);text-align:left;vertical-align:bottom;padding:10px 14px 8px 0;border-bottom:1px solid var(--ink);white-space:nowrap}
.ledger thead th a,.ledger thead th>span{display:inline-flex;align-items:center;min-height:32px;color:inherit;text-decoration:none}
.ledger thead th a:hover{color:var(--ink);text-decoration:underline;text-decoration-color:var(--accent)}
.ledger thead th[aria-sort] a{color:var(--ink)}
.ledger .dir{font-size:9px;margin-left:5px}
.ledger td{padding:14px 14px 14px 0;border-bottom:1px solid var(--line);vertical-align:top}
.ledger tbody tr:hover td{background:var(--card)}
.ledger td.num,.ledger th.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.ledger th.num a,.ledger th.num>span{justify-content:flex-end}
.ledger td.main{min-width:14rem}
.ledger td.nw{white-space:nowrap}
.ledger td.main a.t{font:400 1.05rem/1.38 var(--serif);color:var(--ink);text-decoration:none}
.ledger td.main a.t:hover{text-decoration:underline;text-decoration-color:var(--accent)}
.ledger td .under{display:block;margin-top:5px;font:13px/1.45 var(--sans);color:var(--muted);overflow-wrap:anywhere;white-space:normal}
.ledger td .under a{color:var(--muted)}
.ledger td .under .mono{font-size:12px}
.ledger td.st{white-space:nowrap;width:1%}
.ledger td.st .status{margin-top:0}
.pager{display:flex;align-items:center;justify-content:space-between;gap:12px;margin:14px 0 0;font:15px/1.4 var(--sans);color:var(--muted)}
.pager a{display:inline-flex;align-items:center;min-height:44px}
.empty{margin:16px 0;padding:24px;border:1px dashed var(--rule);border-radius:6px;color:var(--muted);font:15px/1.5 var(--sans)}
@media (max-width:720px){
.ledger-scroll{overflow:visible}
table.ledger,.ledger tbody,.ledger tr,.ledger td{display:block}
.ledger thead{display:none}
.ledger tr{padding:14px 0;border-bottom:1px solid var(--line)}
.ledger td{border:0;padding:0;width:auto!important;min-width:0!important}
.ledger td.main{margin:0 0 8px}
.ledger td:not(.main){display:inline-flex;align-items:center;gap:6px;margin:0 16px 6px 0;font-size:14px;text-align:left}
.ledger td:not(.main){flex-wrap:wrap;max-width:100%;white-space:normal}
.ledger td:not(.main) .under{flex-basis:100%;margin-top:0}
.ledger td:not(.main)[data-label]::before{content:attr(data-label);font:13px/1.3 var(--sans);color:var(--muted)}
.ledger td.st::before{display:none}
.ledger td[data-phone="hide"]{display:none}
.ledger tbody tr:hover td{background:none}
.tq select{min-width:0;width:100%}
.tq label:not(.q){flex:1 1 9rem}
}
.rmini{display:inline-flex;align-items:center;gap:8px;font-variant-numeric:tabular-nums}
.rmini b{font:600 15px/1 var(--sans);min-width:2.4em;text-align:right}
.rtrack{position:relative;display:block;width:56px;height:6px;border-radius:3px;background:var(--line)}
.rfill{position:absolute;left:0;top:0;bottom:0;border-radius:3px;background:var(--ink)}
.rfill.risk{background:var(--accent)}
.rfill.open{background:var(--rule)}
.rfill.broken{background:var(--card);border:1.5px solid var(--ink)}
.rtick{position:absolute;top:-3px;bottom:-3px;width:1px;background:var(--muted)}
.ruler{margin:8px 0 4px}
.ru-scale{position:relative;height:22px;margin:0 9px}
.ru-track{position:absolute;left:-9px;right:-9px;top:8px;height:6px;border-radius:3px;background:var(--line)}
.ru-fill{position:absolute;left:-9px;top:8px;height:6px;border-radius:3px 0 0 3px;background:var(--ink)}
.ru-fill.risk{background:var(--accent)}.ru-fill.open{background:var(--rule)}.ru-fill.broken{background:var(--rule)}
.ru-tick{position:absolute;top:2px;width:1.5px;height:18px;margin-left:-.75px;background:var(--muted)}
.ru-prior{position:absolute;top:5px;width:12px;height:12px;margin-left:-6px;border-radius:50%;background:var(--card);border:2px solid var(--muted);box-sizing:border-box}
.ru-needle{position:absolute;top:1px;width:20px;height:20px;margin-left:-10px;border-radius:50%;background:var(--ink);border:3px solid var(--card);box-sizing:border-box;box-shadow:0 0 0 1px var(--ink)}
.ru-needle.risk{background:var(--accent);box-shadow:0 0 0 1px var(--accent)}
.ru-needle.open{background:var(--card);border:2px dashed var(--ink);box-shadow:none}
.ru-needle.broken{background:var(--card);border:3px solid var(--ink);box-shadow:none}
.ru-axis{position:relative;height:18px;margin:4px 9px 0;font:12.5px/1 var(--sans);color:var(--muted);font-variant-numeric:tabular-nums}
.ru-axis span{position:absolute;top:0;transform:translateX(-50%);white-space:nowrap}
.ru-axis span:first-child{transform:none;margin-left:-9px}.ru-axis span:last-child{transform:translateX(-100%);margin-left:9px}
.ru-key{margin:8px 0 0;font:13px/1.5 var(--sans);color:var(--muted)}
.strip{margin:6px 0 2px;font:14px/1.3 var(--sans)}
.st-row{display:grid;grid-template-columns:10rem minmax(0,1fr);align-items:center;min-height:40px;border-bottom:1px solid var(--line);color:var(--ink);text-decoration:none}
a.st-row:hover .st-k{text-decoration:underline;text-decoration-color:var(--accent)}
a.st-row.on{background:var(--ground)}
a.st-row.on .st-k{font-weight:700}
.st-row:last-child{border-bottom:0}
.st-k{padding-right:14px;color:var(--ink);white-space:nowrap}.st-k b{font-weight:600;font-variant-numeric:tabular-nums;color:var(--muted);margin-left:2px}
.st-lane{position:relative;height:40px;margin:0 6px}
.st-lane b{position:absolute;top:0;bottom:0;border-left:1px dashed var(--rule)}
.st-lane i{position:absolute;width:10px;height:10px;margin:-5px 0 0 -5px;border-radius:50%;background:var(--ink);box-shadow:0 0 0 1.5px var(--card)}
.st-lane i.part{background:var(--rule)}.st-lane i.open{background:var(--card);border:1.5px solid var(--ink);box-sizing:border-box}.st-lane i.risk{background:var(--accent)}.st-lane i.broken{background:var(--card);border:2.5px solid var(--ink);box-sizing:border-box}
.st-axis{border:0;min-height:24px}
.st-axis .st-k{color:var(--muted);font-size:13px}
.st-axis .st-lane{height:24px}
.st-axis .st-lane span{position:absolute;top:6px;transform:translateX(-50%);font:12.5px/1 var(--sans);color:var(--muted);font-variant-numeric:tabular-nums}
@media (max-width:520px){.st-row{grid-template-columns:7.2rem minmax(0,1fr)}.st-k{font-size:13px;padding-right:8px}}
.plate-note{margin:4px 0 12px}
.status-key{list-style:none;padding:0;margin:8px 0 0;display:grid;gap:10px}
.status-key li{display:grid;grid-template-columns:7.5rem minmax(0,1fr);gap:12px;align-items:baseline;font:15px/1.45 var(--sans)}
.status-key .status{margin:0;justify-self:start}
@media (max-width:520px){.status-key li{grid-template-columns:1fr;gap:4px}}
.specimen-label{margin:0;background:var(--ground);border:1px solid var(--ink);border-radius:2px}
.specimen-label>div{display:grid;grid-template-columns:minmax(9rem,13rem) minmax(0,1fr);gap:4px 20px;padding:12px 16px;border-top:1px solid var(--line)}
.specimen-label>div:first-child{border-top:0}
.specimen-label dt{font:600 14px/1.3 var(--sans);color:var(--ink)}
.specimen-label dt span{display:block;font:400 13px/1.4 var(--sans);color:var(--muted);margin-top:2px}
.specimen-label dd{margin:0;font:1.02rem/1.45 var(--serif);color:var(--ink)}
.specimen-label>div:first-child dd{font-size:1.2rem}
@media (max-width:560px){.specimen-label>div{grid-template-columns:1fr}}
.nbhd{display:grid;grid-template-columns:minmax(0,1fr) 28px minmax(0,0.8fr) 28px minmax(0,1fr);gap:0;align-items:stretch;padding:16px}
.nb-col h3{font:600 13px/1.2 var(--sans);color:var(--muted);margin:0 0 10px}
.nb-col ul{list-style:none;padding:0;margin:0;display:grid;gap:8px}
.nb{display:grid;grid-template-columns:18px minmax(0,1fr);gap:2px 8px;padding:10px 12px;background:var(--ground);border:1px solid var(--line);border-radius:4px;color:var(--ink);text-decoration:none;min-height:44px}
.nb:hover{border-color:var(--ink)}
.nb-s{font-size:12px;line-height:1.5;color:var(--ink)}.nb-s.risk{color:var(--accent)}
.nb-t{font:15px/1.35 var(--serif)}
.nb-r{grid-column:2;font:12.5px/1.3 var(--sans);color:var(--muted)}
.nb-more a,.nb-none{font:14px/1.4 var(--sans);color:var(--muted)}
.nb-none{margin:0;padding:10px 12px;border:1px dashed var(--line);border-radius:4px}
.nb-self{display:flex;flex-direction:column;justify-content:center;align-items:center;align-self:center;text-align:center;padding:16px 12px;border:1.5px solid var(--ink);border-radius:4px;background:var(--card)}
.nb-self h3{margin:0 0 6px}.nb-me{margin:0 0 6px}.nb-self .small{margin:0}
.nb-arrow{position:relative;align-self:center;height:20px}
.nb-arrow::before{content:"";position:absolute;left:4px;right:6px;top:50%;border-top:1.5px solid var(--rule)}
.nb-arrow::after{content:"";position:absolute;right:4px;top:calc(50% - 4px);border:4.5px solid transparent;border-left:7px solid var(--rule);border-right:0}
@media (max-width:820px){.nbhd{grid-template-columns:1fr;gap:0}.nb-arrow{height:28px}.nb-arrow::before{left:50%;right:auto;top:4px;bottom:8px;border-top:0;border-left:1.5px solid var(--rule)}.nb-arrow::after{left:calc(50% - 4px);right:auto;top:auto;bottom:4px;border:4.5px solid transparent;border-top:7px solid var(--rule);border-bottom:0}}
.specimen{display:grid;gap:8px 56px}
.specimen .doc{min-width:0;max-width:44rem}
.specimen .panel{min-width:0}
@media (min-width:1040px){.specimen{grid-template-columns:minmax(0,1fr) 20rem;align-items:start}.specimen .panel{position:sticky;top:20px;grid-column:2;grid-row:1 / span 3}}
.panel{background:var(--card);border:1px solid var(--line);border-top:3px solid var(--ink);padding:18px 18px 16px;margin:0 0 24px}
.panel .status{margin:0}
.panel .ruler{margin:6px 0 0}
.panel dl{display:grid;grid-template-columns:auto minmax(0,1fr);gap:8px 14px;margin:12px 0 0;font:14px/1.4 var(--sans)}
.panel dt{color:var(--muted)}
.panel dd{margin:0;color:var(--ink);font-variant-numeric:tabular-nums;overflow-wrap:anywhere}
.panel .acts{display:flex;flex-wrap:wrap;gap:8px;margin:14px 0 0}
.panel .acts a{display:inline-flex;align-items:center;min-height:40px;padding:0 12px;border:1px solid var(--rule);border-radius:4px;font:14px/1 var(--sans);color:var(--ink);text-decoration:none;background:var(--ground)}
.panel .acts a:hover{border-color:var(--ink)}
h1.claim-h1{font-size:clamp(1.75rem,3.4vw,2.6rem);line-height:1.15;max-width:none;letter-spacing:-.02em}
.crumbs{font:14px/1.4 var(--sans);color:var(--muted);margin:0 0 14px}
.crumbs a{color:var(--muted)}
.crumbs .mono{font-size:12.5px}
.quote-src{font:16px/1.5 var(--sans);color:var(--muted);margin:0 0 18px}
.test{border-left:3px solid var(--accent);padding:2px 0 2px 16px;margin:0 0 24px}
.test b{display:block;font:600 13px/1.3 var(--sans);color:var(--muted);margin:0 0 4px}
.test p{margin:0;font:1.08rem/1.5 var(--serif)}
.gloss{background:var(--card);border:1px solid var(--line);border-top:3px solid var(--ink);padding:14px 18px 4px;margin:0 0 24px}
.gloss h2{font:600 13px/1.3 var(--sans);letter-spacing:.08em;text-transform:uppercase;color:var(--muted);margin:0 0 10px}
.gloss h3{font:600 14px/1.3 var(--sans);color:var(--ink);margin:18px 0 6px}
.gloss dl.about{display:grid;grid-template-columns:auto minmax(0,1fr);gap:4px 14px;margin:0 0 4px;font:14px/1.45 var(--sans)}
.gloss dl.about dt{color:var(--muted)}
.gloss dl.about dd{margin:0;color:var(--ink);overflow-wrap:anywhere}
.gloss cite{font-style:italic}
.gloss .gist{font:1.1rem/1.55 var(--serif);margin:14px 0 4px}
.gloss ul{padding-left:1.2em;margin:0 0 4px}
.gloss li{margin:0 0 6px;font:1.02rem/1.5 var(--serif)}
.gloss dl.terms{margin:0;font:15px/1.5 var(--sans)}
.gloss dl.terms dt{font-weight:600;color:var(--ink)}
.gloss dl.terms dd{margin:0 0 8px;color:var(--ink)}
.gloss .standing{font:1.02rem/1.55 var(--serif);margin:0 0 6px}
.gloss ol.ladder{list-style:none;padding:0;margin:0 0 4px;counter-reset:rung}
.gloss ol.ladder li{display:grid;grid-template-columns:1.6rem minmax(0,1fr);gap:0 8px;padding:8px 0;border-top:1px solid var(--line);font:15px/1.5 var(--sans);color:var(--ink)}
.gloss ol.ladder li:first-child{border-top:0}
.gloss ol.ladder .mark{font:600 16px/1.4 var(--sans);color:var(--muted);text-align:center}
.gloss ol.ladder li.confirmed .mark{color:var(--ink)}
.gloss ol.ladder li.failed .mark,.gloss ol.ladder li.mixed .mark{color:var(--amber)}
.gloss ol.ladder .rung-body{min-width:0}
ol.rungs{list-style:none;padding:0;margin:12px 0;display:grid;gap:22px;max-width:44rem}
ol.rungs li{position:relative;background:var(--card);border:1px solid var(--line);border-left:3px solid var(--ink);padding:12px 14px;font:15px/1.5 var(--sans);color:var(--ink)}
ol.rungs li+li::before{content:"\\2193";position:absolute;top:-22px;left:18px;font:600 16px/22px var(--sans);color:var(--muted)}
ol.rungs .rung-what,ol.rungs .rung-then{display:block;margin-top:6px}
ol.rungs .rung-then{color:var(--muted)}
.gloss .who{font:13.5px/1.5 var(--sans);color:var(--muted);border-top:1px solid var(--line);padding-top:8px;margin:14px 0 10px}
details.how{margin:8px 0 16px;border-top:1px solid var(--line)}
details.how>summary{font:15px/1.4 var(--sans);color:var(--muted)}
details.how>div{padding:4px 0 8px;font:15px/1.55 var(--sans);color:var(--muted);max-width:44rem}
.section-intro{font:16px/1.55 var(--sans);color:var(--muted);max-width:44rem;margin:-4px 0 14px}
.said{display:block;margin-top:4px}
.limits{padding-left:1.2em;max-width:44rem}
.limits li{margin:0 0 8px;font:1.02rem/1.5 var(--serif)}
.panel p:first-child{margin:0 0 4px}
h1.claim-h1.long{font-size:clamp(1.55rem,2.8vw,2.1rem)}
h1.claim-h1.longest{font-size:clamp(1.35rem,2.3vw,1.75rem);line-height:1.25}
.doc h3{margin:28px 0 8px}
dl.facts{display:grid;grid-template-columns:minmax(7rem,9.5rem) minmax(0,1fr);gap:6px 16px;margin:0 0 20px;font:14px/1.5 var(--sans);color:var(--muted)}
dl.facts dt{font-weight:600;color:var(--ink)}
dl.facts dd{margin:0;overflow-wrap:anywhere}
@media (max-width:520px){dl.facts{grid-template-columns:1fr;gap:0}dl.facts dd{margin:0 0 8px}}
p.meaning{font:16px/1.5 var(--sans);margin:12px 0 16px}
p.meaning .status{margin:0 6px 0 0;vertical-align:1px}
dl.facts.wide{grid-template-columns:minmax(7rem,9rem) minmax(0,1fr);max-width:52rem;margin:8px 0 12px;font-size:15px}
.fig svg a{text-decoration:none}
.fig svg a:hover .lbl{text-decoration:underline;text-decoration-color:var(--accent)}
.graph-key{display:flex;flex-wrap:wrap;gap:4px 16px;margin:8px 0 0;font:13px/1.4 var(--sans);color:var(--muted)}
.views{display:inline-flex;margin:0 0 20px;border:1px solid var(--ink);border-radius:6px;overflow:hidden}
.views a{display:inline-flex;align-items:center;min-height:40px;padding:0 18px;font:15px/1 var(--sans);color:var(--ink);text-decoration:none}
.views a+a{border-left:1px solid var(--ink)}
.views a[aria-current]{background:var(--ink);color:var(--ground)}
.views a:not([aria-current]):hover{background:var(--card)}
.net-q{flex-direction:column;align-items:stretch}
.tq-row{display:flex;flex-wrap:wrap;gap:10px 12px;align-items:flex-end}
.tq-row+.tq-row{padding-top:12px;border-top:1px solid var(--line)}
.tq-k{flex:0 0 3.4rem;align-self:center;font:600 13px/1.2 var(--sans);color:var(--ink)}
@media (max-width:720px){.tq-k{flex-basis:100%}}
.fig svg.net .lbl{font-size:12px;stroke:var(--ground)}
.net .grp{fill:var(--ground);stroke:var(--line)}
.net .cap{font-size:12px;fill:var(--muted)}
.net a .cap{fill:var(--ink);text-decoration:underline}
.net .cap.sec{font:400 17px var(--serif);fill:var(--ink)}
.net line.sec{stroke:var(--rule)}
.net .e,.net-key .e{stroke:var(--rule);stroke-linecap:round}
.net-key .e{stroke-width:2}
.net .e.id,.net-key .e.id{stroke-dasharray:5 4}
.net .e.ref,.net-key .e.ref{stroke:var(--accent)}
.net .e.dim{opacity:.15}
.net g.dim{opacity:.2}
.net .ring,.net-key .ring{stroke:var(--accent);stroke-width:2.5}
.net-key .shp{stroke:var(--ink);stroke-width:1.5}
.fig .net-key svg.k{display:inline-block;width:auto;height:auto;vertical-align:middle;margin:0 4px 0 0}
.net-key .graph-key{margin:6px 0 0}
.stages{list-style:none;padding:0;margin:4px 0 0;display:grid;gap:12px}
.stages li{display:grid;grid-template-columns:minmax(10rem,16rem) minmax(0,1fr) 8.5rem;gap:8px 16px;align-items:center}
.sg-k b{display:block;font:600 15px/1.3 var(--sans)}.sg-k span{display:block;font:13px/1.35 var(--sans);color:var(--muted)}
.sg-bar{display:block;height:14px;background:var(--ground);border:1px solid var(--line);border-radius:3px;overflow:hidden}
.sg-bar .f{display:block;height:100%}
.sg-v{font:600 15px/1.3 var(--sans);font-variant-numeric:tabular-nums;text-align:right}.sg-v span{font-weight:400;color:var(--muted);font-size:13px}
.sg-note{margin:14px 0 0}.sg-note .status{margin:0 6px 0 0}
@media (max-width:640px){.stages li{grid-template-columns:1fr auto}.sg-bar{grid-column:1 / -1;grid-row:2}}
.hero{max-width:46rem;margin:8px 0 32px}
.hero .eyebrow{margin:0 0 10px}
.hero h1{font-size:clamp(2.6rem,6vw,4.4rem);margin:0 0 20px}
.hero .lede{font-size:1.25rem;color:var(--ink);margin:0}
.hero.has-film{max-width:none;display:grid;grid-template-columns:minmax(0,1fr);gap:32px 56px;align-items:start}
.hero-text{max-width:46rem}
@media (min-width:1040px){.hero.has-film{grid-template-columns:minmax(0,5fr) minmax(0,6fr)}.hero.has-film h1{font-size:clamp(2.6rem,4.6vw,4.1rem)}.film{padding-top:4px}}
.film figure{margin:0}
.film video{display:block;width:100%;height:auto;aspect-ratio:16/9;background:#000;border:1px solid var(--line);border-radius:6px}
.film figcaption{font:15px/1.5 var(--sans);color:var(--muted);margin:10px 0 8px}
details.transcript{border-top:1px solid var(--line)}
details.transcript>summary{list-style:none;gap:10px;margin:0;color:var(--ink)}
details.transcript>summary::-webkit-details-marker{display:none}
details.transcript>summary::after{content:"+";display:inline-block;font:400 1.25rem/1 var(--sans);color:var(--muted)}
details.transcript[open]>summary::after{content:"\\2212"}
details.transcript>summary:hover{text-decoration:underline;text-decoration-color:var(--accent);text-underline-offset:.2em}
details.transcript>p{font:16px/1.6 var(--sans);color:var(--ink);max-width:44rem;margin:0 0 12px}
.now{margin:40px 0 8px;padding:24px 24px 8px;background:var(--card);border:1px solid var(--line);border-top:3px solid var(--ink)}
.now h2{margin-top:0}
.now h3{margin:24px 0 4px}
.now .strip{margin-top:4px}
ol.setup{list-style:none;counter-reset:setup;padding:0;margin:8px 0 32px;display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,15rem),1fr));gap:16px}
ol.setup li{counter-increment:setup;position:relative;padding:18px 18px 16px 58px;background:var(--card);border:1px solid var(--line);font:16px/1.5 var(--sans)}
ol.setup li::before{content:counter(setup);position:absolute;left:18px;top:16px;display:flex;align-items:center;justify-content:center;width:28px;height:28px;border-radius:50%;background:var(--accent);color:var(--on-accent);font:600 14px/1 var(--sans)}
ol.setup b{display:block;font:400 1.2rem/1.3 var(--serif);margin:0 0 6px}
ol.setup span{display:block;color:var(--muted)}
ul.gets{list-style:none;padding:0;margin:8px 0 24px;display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,17rem),1fr));gap:20px 32px}
ul.gets li{border-top:1px solid var(--ink);padding:12px 0 0}
ul.gets b{display:block;font:400 1.15rem/1.3 var(--serif);margin:0 0 4px}
ul.gets span{display:block;font:15px/1.5 var(--sans);color:var(--muted)}
ol.setup.steps-v{grid-template-columns:1fr;max-width:46rem;gap:0}
ol.setup.steps-v li{background:none;border:0;padding:3px 0 26px 50px}
ol.setup.steps-v li::before{left:0;top:0}
ol.setup.steps-v li:not(:last-child)::after{content:"";position:absolute;left:13.5px;top:36px;bottom:6px;width:1px;background:var(--rule)}
ol.setup.steps-v span{color:var(--ink)}
@media (prefers-reduced-motion:reduce){*,*::before,*::after{transition:none!important;animation:none!important;scroll-behavior:auto!important}}
`;

/** The people's half: start, connect, the lab, the network of claims, the map, the leaderboard, the observatory, questions. */
export const V2_PEOPLE_NAV: ReadonlyArray<readonly [string, string]> = [
  ["/people", "Start"],
  ["/connect", "Connect"],
  ["/lab", "Lab"],
  ["/claims", "Claims"],
  ["/map", "Map"],
  ["/leaderboard", "Leaderboard"],
  ["/observatory", "Observatory"],
  ["/faq", "FAQ"],
];
/** The agents' half: the protocol and its references. */
export const V2_AGENT_NAV: ReadonlyArray<readonly [string, string]> = [
  ["/agents", "Overview"],
  ["/skill.md", "Protocol"],
  ["/api", "API"],
  ["/constitution.md", "Constitution"],
  ["/governance", "Amendments"],
  ["/claims", "Claims"],
  ["/map", "Map"],
  ["/lab", "Lab"],
  ["/llms.txt", "llms.txt"],
];
const PEOPLE_NAV = V2_PEOPLE_NAV;
const AGENT_NAV = V2_AGENT_NAV;

export interface ShellOptions {
  title: string;
  description: string;
  half: Half;
  /** Path of the current page, to mark it in the half's navigation. */
  current?: string;
  body: string;
  wide?: boolean;
  /** Extra elements for <head> (e.g. feed autodiscovery). Must be trusted. */
  head?: string;
  /** Inline script. Only the Observatory uses one; its CSP allows it. */
  script?: string;
  /** Extra footer HTML. Must be trusted or escaped by the caller. */
  footerExtra?: string;
  /** The half's navigation, when not the default (v2 pages pass their own). */
  nav?: ReadonlyArray<readonly [string, string]> | null;
  /** A small uppercase badge beside the brand naming the mode the reader is in ("Steward"), as the v1 console tagged itself "Operator". */
  tag?: string;
  /** Who is signed in, shown in the header beside the tag ("Signed in as …"); the caller passes plain text, escaped here. */
  who?: string | null;
  /** The log entry the page's figures were derived to (V2Record.head): named in the footer, so a reader can tell an old view from a current one. */
  computedFrom?: { seq: number; ts: string } | null;
}

/** One document frame for every human page. */
export function shell(o: ShellOptions): string {
  const cur = (half: Half) => (o.half === half ? ' aria-current="true"' : "");
  const nav = o.nav !== undefined ? o.nav : o.half === "people" ? PEOPLE_NAV : o.half === "agents" ? AGENT_NAV : null;
  const sub = nav
    ? `<nav class="sub" aria-label="${o.half === "people" ? "For people" : o.half === "agents" ? "For agents" : "Section"}">${nav
        .map(([href, label]) => `<a href="${href}"${o.current === href ? ' aria-current="page"' : ""}>${label}</a>`)
        .join("")}</nav>`
    : "";
  return `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${esc(o.title)}</title>
<meta name="description" content="${esc(o.description)}">
<meta name="color-scheme" content="light dark">
<meta name="theme-color" content="#F7F8FA" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#242629" media="(prefers-color-scheme: dark)">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
${o.head ?? ""}
<style>${CSS}</style>
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<div class="frame">
<header class="top">
<a class="brand" href="/">${brandLockup()}${o.tag ? `<span class="tag">${esc(o.tag)}</span>` : ""}</a>
${o.who ? `<span class="who">Signed in as ${esc(o.who)}${o.tag ? ` · ${esc(o.tag.toLowerCase())} mode` : ""}</span>` : ""}
<nav class="halves" aria-label="Site"><span class="seg"><a href="/people"${cur("people")}>People</a><a href="/agents"${cur("agents")}>Agents</a></span><a class="me" href="/me"${cur("me")}>Your Ecdysis</a></nav>
</header>
${sub}
</div>
<div class="wrap${o.wide ? " wide" : ""}">
<main id="main">
${o.body}
</main>
</div>
<div class="frame">
<footer>
<div class="foot-brand"><img class="symbol" src="/brand/ecdysis-symbol.svg" alt="" width="540" height="258" decoding="async"><span>Ecdysis is an open record of machine science. Text is licensed CC BY 4.0, and every figure can be recomputed from the public log.</span></div>
<p class="links"><a href="/people">For people</a><a href="/agents">For agents</a><a href="/connect">Connect your AI</a><a href="/me">Your Ecdysis</a><a href="/terms">Terms</a><a href="/privacy">Privacy</a><a href="/skill.md">Protocol</a><a href="/api">API</a><a href="/constitution.md">Constitution</a><a href="/llms.txt">llms.txt</a><a href="https://github.com/djhulme1/ecdysis-core">Source code</a></p>
${o.computedFrom ? `<p class="small computed">This page was computed from the public log at entry #${o.computedFrom.seq} (${esc(shortDate(o.computedFrom.ts))}, ${esc(o.computedFrom.ts.slice(11, 16))} UTC). Entries since then are not on it: reload for the record as it stands.</p>` : ""}${o.footerExtra ?? ""}
</footer>
</div>
${o.script ? `<script>${o.script}</script>` : ""}
</body>
</html>`;
}

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

/** "30 Sep 2026" from an ISO timestamp; empty string if unparseable. */
export function shortDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return `${d.getUTCDate()} ${MONTHS[d.getUTCMonth()]} ${d.getUTCFullYear()}`;
}

/**
 * The mark for a status, never colour alone: established is a filled ink
 * chip (●), supported an outlined one (◐), unchecked a dashed one (○),
 * contested the one orange chip (◆, the mark of attention), refuted a
 * crossed one (✕). Anything unknown is treated as unchecked.
 */
export function statusTone(s: string | null | undefined): "sound" | "part" | "open" | "risk" | "broken" {
  return s === "established" ? "sound" : s === "supported" ? "part" : s === "contested" ? "risk" : s === "refuted" ? "broken" : "open";
}
