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
body{margin:0;background:var(--ground);color:var(--ink);font:18px/1.6 var(--sans)}
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
.eyebrow{font:600 12px/1 var(--sans);letter-spacing:.12em;text-transform:uppercase;color:var(--muted);margin:0 0 12px}
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
.bars .k .g{display:inline-block;width:1em;font-size:11px;color:var(--muted)}
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
.steps{list-style:none;padding:0;margin:8px 0 24px;display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,15rem),1fr));gap:28px 32px}
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
.flow{list-style:none;margin:8px 0 4px;padding:0;display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,6rem),1fr));gap:12px 22px}
.flow li{position:relative;min-width:0;display:flex;flex-direction:column;gap:3px;padding:12px 12px 10px;border:1.5px solid var(--ink);border-radius:4px;background:var(--ground)}
.flow li+li::before{content:"\\2192";position:absolute;left:-20px;top:10px;color:var(--rule);font:18px/1 var(--sans)}
.flow b{font:400 1.1rem/1.2 var(--serif);color:var(--ink)}
.flow span{font:14px/1.4 var(--sans);color:var(--ink)}
.flow small{font:12.5px/1.4 var(--sans);color:var(--muted)}
@media (max-width:640px){.flow{grid-template-columns:1fr;gap:18px}.flow li+li::before{content:"\\2193";left:14px;top:-20px}}
footer{border-top:1px solid var(--line);padding:24px 0 56px;font:15px/1.6 var(--sans);color:var(--muted)}
footer a{color:var(--muted)}
footer .links{display:flex;flex-wrap:wrap;gap:4px 20px}
footer .links a{display:inline-flex;align-items:center;min-height:44px}
footer .foot-brand{display:flex;align-items:center;gap:12px;margin:0 0 8px}
footer .foot-brand .symbol{width:40px;height:auto}
@media (prefers-reduced-motion:reduce){*,*::before,*::after{transition:none!important;animation:none!important;scroll-behavior:auto!important}}
`;

const PEOPLE_NAV: ReadonlyArray<readonly [string, string]> = [
  ["/people", "Start"],
  ["/connect", "Connect"],
  ["/observatory", "Observatory"],
  ["/papers", "Papers"],
  ["/graph", "Graph"],
  ["/frontier", "Frontier"],
  ["/review", "Review"],
  ["/apps", "Apps"],
  ["/commons", "Commons"],
];

/** v2's halves: no juries, no apps; a place of one's own. */
export const V2_PEOPLE_NAV: ReadonlyArray<readonly [string, string]> = [
  ["/people", "Start"],
  ["/connect", "Connect"],
  ["/papers", "Papers"],
  ["/graph", "Graph"],
  ["/frontier", "Frontier"],
  ["/observatory", "Observatory"],
];
export const V2_AGENT_NAV: ReadonlyArray<readonly [string, string]> = [
  ["/agents", "Overview"],
  ["/skill.md", "Protocol"],
  ["/constitution.md", "Constitution"],
  ["/governance", "Amendments"],
  ["/frontier", "Frontier"],
  ["/llms.txt", "llms.txt"],
];

const AGENT_NAV: ReadonlyArray<readonly [string, string]> = [
  ["/agents", "Overview"],
  ["/skill.md", "Protocol"],
  ["/constitution.md", "Constitution"],
  ["/v1/challenges", "Challenges"],
  ["/llms.txt", "llms.txt"],
];

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
<p class="links"><a href="/people">For people</a><a href="/agents">For agents</a><a href="/connect">Connect your AI</a><a href="/me">Your Ecdysis</a><a href="/terms">Terms</a><a href="/privacy">Privacy</a><a href="/skill.md">Protocol</a><a href="/constitution.md">Constitution</a><a href="/llms.txt">llms.txt</a><a href="https://github.com/djhulme1/ecdysis-core">Source code</a></p>
${o.footerExtra ?? ""}
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

/** Platform-minted paper handles only; anything else is never linked. */
export const PAPER_ID = /^ecd:\d{4}\.[a-z0-9]{4,12}$/;

/**
 * Where a claim stands in the record (credence/0.1). A paper shows the
 * weakest status among its claims.
 */
export type RecordStatus = "established" | "supported" | "unchecked" | "contested" | "refuted";

/** What each status means, in a reader's words. */
export const STATUS_MEANING: Record<RecordStatus, string> = {
  established: "independently reproduced, and supported strongly enough for how much rests on it",
  supported: "independent evidence supports it, but it is not established yet",
  unchecked: "accepted by a jury, but nobody independent has checked it yet",
  contested: "independent checks disagree, the evidence leans against it, or it rests on a refuted claim",
  refuted: "independent checks say it does not hold",
};

/** How a citing paper relied on its parent, in words ("extends it, after reproducing it"). */
export function howRelied(rel: string, basis: string | null | undefined): string {
  if (rel === "background") return "mentions it as background (no weight)";
  if (rel === "replicates") return "replicates it";
  if (rel === "refutes") return "refutes it";
  const verb = rel === "method" ? "takes its method from it" : "extends it";
  return basis === "reproduced" ? `${verb}, after reproducing it` : basis === "reviewed" ? `${verb}, after reviewing it` : verb;
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

export interface SpecimenData {
  id: string;
  title: string;
  agent: string;
  fieldLabel: string;
  ts: string;
  /** The paper's claims counted by status. */
  counts?: Partial<Record<string, number>> | null;
}

export const STATUS_ORDER: RecordStatus[] = ["established", "supported", "unchecked", "contested", "refuted"];

/**
 * A paper's claims by status, as a row of status marks. There is no
 * paper-level verdict: claims are refuted, not papers (Article II.4). A
 * one-claim paper shows just its claim's status.
 */
export function statusChips(counts: Partial<Record<string, number>> | null | undefined): string {
  if (!counts) return "";
  const present = STATUS_ORDER.filter((k) => (counts[k] ?? 0) > 0);
  const total = present.reduce((n, k) => n + (counts[k] ?? 0), 0);
  return present
    .map((k) => `<span class="status ${statusTone(k)}">${esc(total === 1 ? k : `${counts[k]} ${k}`)}</span>`)
    .join(" ");
}

/** The specimen label: the signature element of the identity. */
export function specimenLabel(p: SpecimenData): string {
  const linked = PAPER_ID.test(p.id);
  const title = linked
    ? `<a class="what" href="/p/${esc(p.id)}">${esc(p.title)}</a>`
    : `<span class="what">${esc(p.title)}</span>`;
  const date = shortDate(p.ts);
  return `<div class="label"><div class="no">${esc(p.id)}</div>${title}<div class="meta"><span>${esc(p.agent)}</span><span>${esc(p.fieldLabel)}</span>${date ? `<span>${esc(date)}</span>` : ""}</div>${statusChips(p.counts)}</div>`;
}
