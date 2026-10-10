/**
 * The Ecdysis design system: one shell, one stylesheet, every human page.
 *
 * Identity, from the brand kit of 3 October 2026 (Lucy Griffiths): the
 * layered orange dragonfly and a lowercase serif wordmark, supplied as SVG
 * and never redrawn (src/web/brand.ts). The look, from her redesign of
 * 9 October 2026 (the claim page and the claims list, with their design
 * notes): a warm paper ground (#F5F4EF) with white cards on it, each with a
 * hairline border and soft corners; near-black ink (#1D1E22); links in a
 * burnt orange (#9A4410) that is the brand's signal orange made fit for
 * text, which stays for the emblem; black buttons for the one thing to do
 * next, white ones for the rest. Status has its own small palette, used as
 * washes behind words and as fills in the drawings: green for supported and
 * established, amber for contested, rose for refuted, a dashed grey outline
 * for unchecked. Headings and quotations are set in Newsreader, reading and
 * the interface in Public Sans, both served from this site (src/web/media.ts)
 * with Georgia and the system sans behind them; monospace only where it does
 * a job (hashes and ids).
 *
 * The pages lead with meaning and keep the record: a reader meets what a
 * claim says, what the paper is and what has been checked, in plain words,
 * before the full record, which is kept whole, folded, for checkers and
 * agents. Status is never carried by colour alone: every status mark is a
 * glyph and a word (established ●, supported ✓, unchecked ○, contested ◆,
 * refuted ✕), so it reads the same to every eye and in print.
 *
 * Accessibility, as the kit asks: 44px targets for buttons, form controls
 * and the top bar (chips, pills, footer links, the glance's links and table
 * headings at least 32px; links within text take the line's height, as
 * WCAG 2.2 allows),
 * visible keyboard focus, a skip link, every image with the right alt,
 * reduced motion respected, body text 55–75 characters a line, text
 * contrast of at least 4.5:1 and form borders of at least 3:1 in both
 * themes (test/web.test.ts checks the pairs).
 *
 * The top bar carries the five places a person goes (Claims, Map, How it
 * works, FAQ, Your Ecdysis); the pages within a place carry their own row
 * of tabs (the map, the leaderboard and the observatory; how it works,
 * connecting an AI and running a lab; the agents' references).
 */

import { brandLockup, LOGO_SYMBOL } from "./brand.js";
import { fontFaceCss, PRELOAD_FONTS } from "./media.js";

export type Half = "people" | "agents" | "me" | "none";

/** Escape text for HTML element and attribute contexts. */
export function esc(s: string): string {
  return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]!);
}

/** The emblem inline, for places that cannot load an image (the legacy console, error pages); the kit's symbol, unchanged, sized by CSS. */
export const MARK = LOGO_SYMBOL.replace("<svg ", '<svg class="mark" aria-hidden="true" focusable="false" ').replace(/ role="img" aria-label="Ecdysis"/, "").replace("<title>Ecdysis</title>", "");

/**
 * The colours, by role, in both themes. Text pairs are held to 4.5:1 or better on the ground and on a card (the test
 * computes them); the washes carry only their own ink.
 */
export const TOKENS = {
  light: {
    ground: "#F5F4EF", card: "#FFFFFF", sunk: "#F1EFE9", ink: "#1D1E22", ink2: "#2B2D31", muted: "#4F5156", faint: "#64666B", rule: "#8A8983", line: "#DCDAD3", line2: "#E9E7E1",
    link: "#9A4410", link2: "#7A3409", onInk: "#FFFFFF",
    green: "#1F6C5C", greenInk: "#12513F", greenWash: "#E4F0EC", onGreen: "#FFFFFF",
    amber: "#B7791F", amberInk: "#6B4600", amberWash: "#FCF1DD",
    rose: "#B04E3B", roseInk: "#8A2E1E", roseWash: "#F7E3DE",
    mRef: "#EAC9C0", mUns: "#E7E3D7", mSup: "#BFDDD5", mEst: "#7EBBAB",
    stEst: "#1F6C5C", stSup: "#529A85", stUnc: "#8A8983", stCon: "#C2851F", stRef: "#B04E3B",
  },
  dark: {
    ground: "#141518", card: "#1D1F23", sunk: "#18191C", ink: "#ECEBE6", ink2: "#DCDBD5", muted: "#B2B1AB", faint: "#A2A19B", rule: "#7C7B76", line: "#34363B", line2: "#2A2C30",
    link: "#F2A56B", link2: "#FFC38F", onInk: "#141518",
    green: "#5DB39C", greenInk: "#93D4C0", greenWash: "#1B332D", onGreen: "#0E1E19",
    amber: "#E2A84B", amberInk: "#F3CB8B", amberWash: "#382D18",
    rose: "#E0806B", roseInk: "#F4AE9F", roseWash: "#3B231F",
    mRef: "#5A3832", mUns: "#38372F", mSup: "#29483F", mEst: "#4C8B79",
    stEst: "#6CC3AA", stSup: "#3F8C78", stUnc: "#7C7B76", stCon: "#E2A84B", stRef: "#E0806B",
  },
} as const;

type Palette = { readonly [K in keyof typeof TOKENS.light]: string };
const vars = (p: Palette) =>
  `--ground:${p.ground};--card:${p.card};--sunk:${p.sunk};--ink:${p.ink};--ink-2:${p.ink2};--muted:${p.muted};--faint:${p.faint};--rule:${p.rule};--line:${p.line};--line-2:${p.line2};` +
  `--link:${p.link};--link-2:${p.link2};--on-ink:${p.onInk};` +
  `--green:${p.green};--green-ink:${p.greenInk};--green-wash:${p.greenWash};--on-green:${p.onGreen};` +
  `--amber:${p.amber};--amber-ink:${p.amberInk};--amber-wash:${p.amberWash};--rose:${p.rose};--rose-ink:${p.roseInk};--rose-wash:${p.roseWash};` +
  `--m-ref:${p.mRef};--m-uns:${p.mUns};--m-sup:${p.mSup};--m-est:${p.mEst};` +
  `--st-est:${p.stEst};--st-sup:${p.stSup};--st-unc:${p.stUnc};--st-con:${p.stCon};--st-ref:${p.stRef}`;

/** The stylesheet every page carries inline (pages are script-free and fetch no stylesheet), its comments taken out. */
export const CSS = `
${fontFaceCss()}
:root{${vars(TOKENS.light)};--link-inv:${TOKENS.dark.link};--accent:#FF8A24;--on-accent:#1D1E22;--sound:var(--green);--risk:var(--amber);--broken:var(--rose);--on-amber:#1D1E22;
--radius:10px;--radius-s:8px;
--serif:"Newsreader",Georgia,"Iowan Old Style",Charter,"Times New Roman",serif;
--sans:"Public Sans",system-ui,-apple-system,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;
--mono:ui-monospace,"SF Mono",Menlo,Consolas,"Liberation Mono",monospace;
--s1:4px;--s2:8px;--s3:12px;--s4:16px;--s5:24px;--s6:32px;--s7:48px;--s8:64px;--s9:96px;--s10:128px;color-scheme:light}
@media (prefers-color-scheme:dark){:root{${vars(TOKENS.dark)};--link-inv:${TOKENS.light.link};color-scheme:dark}}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%;text-size-adjust:100%}
body{margin:0;background:var(--ground);color:var(--ink);font:17px/1.65 var(--sans);overflow-wrap:break-word;font-kerning:normal;-webkit-font-smoothing:antialiased;-moz-osx-font-smoothing:grayscale}
a{color:var(--link);text-decoration:underline;text-decoration-thickness:1px;text-decoration-color:color-mix(in srgb,var(--link) 45%,transparent);text-underline-offset:.18em}
a:hover{color:var(--link-2);text-decoration-color:currentColor}
:focus-visible{outline:2px solid var(--link);outline-offset:3px;border-radius:2px}
.skip{position:absolute;left:-9999px}
.skip:focus{left:16px;top:10px;background:var(--card);color:var(--ink);padding:10px 14px;border:1px solid var(--ink);border-radius:var(--radius-s);z-index:20}
.wrap{max-width:calc(46rem + 2 * clamp(16px,4vw,40px));margin:0 auto;padding:0 clamp(16px,4vw,40px)}
.wrap.wide,.frame{max-width:calc(75rem + 2 * clamp(16px,4vw,40px));margin:0 auto;padding:0 clamp(16px,4vw,40px)}

/* The top bar: the brand, and the five places a person goes. */
.site{background:var(--card);border-bottom:1px solid var(--line)}
.bar{display:flex;align-items:center;justify-content:space-between;gap:4px 28px;flex-wrap:wrap;min-height:68px;padding-top:6px;padding-bottom:6px}
.brand{display:inline-flex;align-items:center;gap:12px;color:var(--ink);text-decoration:none;min-height:44px}
.brand .lockup{display:block;width:180px;max-width:100%;height:auto}
.brand .symbol{display:none;width:44px;height:auto}
@media (max-width:300px){.brand .lockup{display:none}.brand .symbol{display:block}}
.mark{width:28px;height:auto;vertical-align:middle}
.tag{font:600 11px/1 var(--sans);letter-spacing:.12em;text-transform:uppercase;color:var(--on-accent);background:var(--accent);padding:5px 7px;border-radius:4px}
.bar .who{font:14px/1.4 var(--sans);color:var(--muted);flex:1 1 12rem}
.bar .who a{color:var(--muted)}
.primary{display:flex;align-items:center;gap:0 24px;flex-wrap:wrap;font:500 15.5px/1.2 var(--sans)}
.primary a{display:inline-flex;align-items:center;min-height:44px;color:var(--ink);text-decoration:none;border-bottom:2px solid transparent;padding-top:2px}
.primary a:hover{border-bottom-color:var(--line)}
.primary a[aria-current]{font-weight:650;border-bottom-color:var(--link)}
@media (max-width:760px){.bar{padding-bottom:0}.primary{width:100%;flex-wrap:nowrap;overflow-x:auto;gap:0 20px;scrollbar-width:none}.primary::-webkit-scrollbar{display:none}.primary a{white-space:nowrap}}
@media (max-width:430px){.primary{gap:0 14px;font-size:14.5px}}
.sub{display:flex;flex-wrap:wrap;gap:0 24px;font:15px/1.2 var(--sans);border-bottom:1px solid var(--line)}
.sub a{display:inline-flex;align-items:center;min-height:46px;color:var(--muted);text-decoration:none;border-bottom:2px solid transparent;margin-bottom:-1px}
.sub a:hover{color:var(--ink)}
.sub a[aria-current="page"]{color:var(--ink);font-weight:600;border-bottom-color:var(--link)}
@media (max-width:760px){.sub{flex-wrap:nowrap;overflow-x:auto;scrollbar-width:none}.sub::-webkit-scrollbar{display:none}.sub a{white-space:nowrap}}

/* Type. */
main{padding:clamp(28px,4vw,44px) 0 clamp(48px,7vw,88px)}
h1{font:550 clamp(2.1rem,4.4vw,3rem)/1.1 var(--serif);letter-spacing:-.015em;margin:0 0 20px;text-wrap:balance;max-width:26ch}
h2{font:500 clamp(1.45rem,2.4vw,1.7rem)/1.2 var(--serif);letter-spacing:-.01em;margin:52px 0 14px;text-wrap:balance}
h3{font:600 1.03rem/1.35 var(--sans);margin:0 0 6px}
p{margin:0 0 16px}
ul,ol{padding-left:1.25em}
li::marker{color:var(--muted)}
b,strong{font-weight:650}
.lede{font-size:1.15rem;line-height:1.6;color:var(--ink-2);max-width:42rem;margin-bottom:28px}
.small{font:14px/1.55 var(--sans);color:var(--muted)}
.note{font:13.5px/1.5 var(--sans);color:var(--muted);margin:10px 0 0}
.eyebrow{font:600 12px/1.3 var(--sans);letter-spacing:.09em;text-transform:uppercase;color:var(--muted);margin:0 0 12px}
.mono{font-family:var(--mono);font-size:.86em;overflow-wrap:anywhere}
code{font-family:var(--mono);font-size:.86em;background:var(--sunk);border:1px solid var(--line);padding:1px 5px;border-radius:5px;overflow-wrap:anywhere}
pre{font:13.5px/1.5 var(--mono);background:var(--sunk);border:1px solid var(--line);border-radius:var(--radius-s);padding:12px 14px;overflow-x:auto;margin:0 0 16px}
pre code{border:0;padding:0;background:none}
.summary{font:1.12rem/1.6 var(--serif);max-width:44rem}
.summary b{font-weight:650}
.section-intro{font:16px/1.6 var(--sans);color:var(--muted);max-width:44rem;margin:-4px 0 16px}
cite{font-style:italic}

/* Cards: white, a hairline, soft corners. */
.card{background:var(--card);border:1px solid var(--line);border-radius:var(--radius);padding:18px 20px}
.card>:last-child{margin-bottom:0}
.notice{background:var(--amber-wash);color:var(--ink);border-radius:var(--radius);padding:12px 16px;font:15px/1.55 var(--sans);margin:0 0 24px;max-width:46rem}
.notice .status{margin:0 8px 0 0;vertical-align:1px}
.empty{margin:16px 0;padding:22px 24px;border:1px dashed var(--rule);border-radius:var(--radius);color:var(--muted);font:15px/1.55 var(--sans)}
.placeholder{border:1px dashed var(--rule);border-radius:var(--radius);padding:12px 16px;color:var(--muted);font:14px/1.5 var(--sans)}

/* Status: a word and a glyph, on its own wash. */
.status{display:inline-flex;align-items:center;gap:5px;margin-top:8px;font:600 12.5px/1 var(--sans);padding:5px 10px;border:1px solid transparent;border-radius:999px;color:var(--muted);background:var(--sunk);white-space:nowrap}
.status::before{font-size:11px;line-height:1}
.status.sound{background:var(--green);color:var(--on-green)}.status.sound::before{content:"\\25CF"}
.status.part{background:var(--green-wash);color:var(--green-ink)}.status.part::before{content:"\\2713";font-weight:700}
.status.open{background:transparent;border:1px dashed var(--rule);color:var(--muted)}.status.open::before{content:"\\25CB"}
.status.risk{background:var(--amber-wash);color:var(--amber-ink)}.status.risk::before{content:"\\25C6"}
.status.broken{background:var(--rose-wash);color:var(--rose-ink)}.status.broken::before{content:"\\2715";font-weight:700}
.status.big{font-size:14px;padding:7px 13px 7px 11px;margin:0}
.status.plain::before{content:none}

/* Buttons: black for the one thing to do next, white for the rest. */
.btn{display:inline-flex;align-items:center;justify-content:center;gap:8px;min-height:44px;background:var(--ink);color:var(--on-ink);font:600 15px/1.2 var(--sans);padding:0 18px;border-radius:var(--radius-s);text-decoration:none;border:1px solid var(--ink);cursor:pointer;text-align:center}
.btn:hover{background:var(--ink-2);border-color:var(--ink-2);color:var(--on-ink)}
.btn.quiet{background:var(--card);color:var(--ink);border:1px solid var(--line)}
.btn.quiet:hover{border-color:var(--ink);background:var(--card);color:var(--ink)}
.btn.line{background:transparent;color:var(--link);border:1px solid color-mix(in srgb,var(--link) 55%,transparent)}
.btn.line:hover{border-color:var(--link);color:var(--link-2)}
.btn.danger{background:var(--card);color:var(--rose-ink);border:1px solid var(--rose)}
.btn.block{display:flex;width:100%}
.actions{display:flex;flex-wrap:wrap;gap:10px;margin:8px 0 16px}

/* Forms. */
form label{display:block;margin:0 0 6px}
input[type=email],input[type=text],input[type=number],input[type=search],input[type=url],input[type=password],select{display:block;font:16px/1.4 var(--sans);color:var(--ink);background:var(--card);border:1px solid var(--rule);border-radius:var(--radius-s);padding:10px 12px;min-height:44px;width:100%;max-width:32rem;margin:0 0 12px}
input:focus,select:focus,textarea:focus{border-color:var(--ink)}
fieldset{border:1px solid var(--line);border-radius:var(--radius);padding:8px 16px 12px;margin:0 0 16px;max-width:46rem}
legend{font:15px/1.3 var(--sans);color:var(--muted);padding:0 4px}
form label.opt{display:inline-flex;align-items:center;gap:8px;min-height:44px;margin:0 18px 0 0;font:16px/1.4 var(--sans)}
.hp,.sr{position:absolute;left:-9999px;width:1px;height:1px;overflow:hidden}
textarea{display:block;width:100%;font:14px/1.5 var(--mono);color:var(--ink);background:var(--card);border:1px solid var(--rule);border-radius:var(--radius-s);padding:10px 12px;margin:0 0 8px;resize:vertical}
textarea::placeholder,input::placeholder{color:var(--faint)}

/* Prompts and things to copy: the text selects itself in one click. */
.prompt{background:var(--card);border:1px solid var(--line);border-radius:var(--radius);margin:12px 0 20px}
.prompt h3{padding:16px 18px 0}
.prompt .why{padding:0 18px;font:14.5px/1.5 var(--sans);color:var(--muted);margin:2px 0 0}
.prompt .pt{font:15px/1.6 var(--sans);background:var(--sunk);padding:12px 14px;margin:10px 18px 16px;border-radius:var(--radius-s);-webkit-user-select:all;user-select:all;cursor:text;overflow-wrap:anywhere}
.prompt pre.kit{white-space:pre-wrap;font:12.5px/1.5 var(--mono);max-height:26rem;overflow:auto;border:0}
.prompt.habit .pt{margin-top:8px}
.openin{display:flex;flex-wrap:wrap;align-items:center;gap:6px 8px;padding:0 18px 16px;margin:-4px 0 0;font:13px/1.2 var(--sans);color:var(--muted)}
.openin a{display:inline-flex;align-items:center;min-height:36px;font:600 13px/1 var(--sans);padding:0 12px;border:1px solid var(--line);border-radius:var(--radius-s);color:var(--ink);text-decoration:none;background:var(--card)}
.openin a:hover{border-color:var(--ink)}
.mcpin{display:flex;flex-wrap:wrap;gap:8px;margin:8px 0 12px}

/* Lists of things. */
.rows{list-style:none;padding:0;margin:0;border-top:1px solid var(--line)}
.rows li{padding:14px 0;border-bottom:1px solid var(--line)}
.rows .t{display:block;font:500 1.08rem/1.4 var(--serif)}
.rows .d{display:block;font:15px/1.55 var(--sans);color:var(--muted);margin-top:4px}
.rows .d .verb{font-size:11px;padding:3px 5px}
.claims{padding-left:1.4em}
.claims li{margin:0 0 16px}
.claims li p{margin:0 0 4px}
.check{padding:10px 0;border-bottom:1px solid var(--line);font:15px/1.5 var(--sans)}
.check .small{margin-top:3px}
.feeds{display:flex;flex-wrap:wrap;gap:6px 16px;font:15px/1.5 var(--sans)}
.notes{font:14px/1.5 var(--sans);color:var(--muted);padding-left:1.4em;margin:12px 0 24px;max-width:46rem}
.notes li{margin:0 0 6px}
.sources{font:15px/1.5 var(--sans);padding-left:1.2em;margin:0 0 16px;max-width:46rem}
.sources li{margin:0 0 8px}
.limits{padding-left:1.2em;max-width:46rem}
.limits li{margin:0 0 8px;font:1.02rem/1.55 var(--serif)}
.jump{display:flex;flex-wrap:wrap;gap:0 20px;font:15px/1.4 var(--sans);margin:0 0 8px}
.jump a{display:inline-flex;align-items:center;min-height:44px}
.grid2{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,22rem),1fr));gap:24px 48px}
.grid2 section{min-width:0}

/* The specimen label: a claim as a list shows it. */
.label{background:var(--card);border:1px solid var(--line);border-radius:var(--radius);padding:14px 18px;font:15px/1.5 var(--sans);color:var(--ink);max-width:46rem}
.label .no{font:13px/1.35 var(--mono);color:var(--muted);overflow-wrap:anywhere}
.label .what{display:block;font:500 1.15rem/1.35 var(--serif);color:var(--ink);margin:4px 0 8px;text-decoration:none}
.label a.what:hover{text-decoration:underline;text-decoration-color:var(--rule)}
.label .meta{display:flex;flex-wrap:wrap;gap:2px 14px;color:var(--muted)}
.labels{list-style:none;padding:0;margin:0;display:grid;gap:12px}
.label+p{margin-top:10px}
dl.kv{display:inline-flex;flex-wrap:wrap;align-items:baseline;gap:4px;margin:0 0 0 10px;font:14px/1.4 var(--sans);color:var(--muted);vertical-align:middle}
dl.kv dt{margin-left:14px}dl.kv dt:first-child{margin-left:0}dl.kv dd{margin:0;color:var(--ink);font-weight:600;font-variant-numeric:tabular-nums}

/* Folds: what a checker needs, kept whole and closed until asked for. */
details summary{cursor:pointer;font:15px/1.4 var(--sans);color:var(--muted);margin-top:6px;min-height:44px;display:flex;align-items:center;gap:8px;list-style:none}
details summary::-webkit-details-marker{display:none}
details>summary::before{content:"";flex:0 0 auto;width:0;height:0;border-left:6px solid currentColor;border-top:4.5px solid transparent;border-bottom:4.5px solid transparent;transition:transform .15s}
details[open]>summary::before{transform:rotate(90deg)}
details.fold{background:var(--card);border:1px solid var(--line);border-radius:var(--radius);margin:0 0 10px}
details.fold>summary{margin:0;padding:12px 18px;color:var(--ink);font:15px/1.4 var(--sans)}
details.fold>summary b{font-weight:650}
details.fold>summary .gist{color:var(--muted)}
details.fold>div{padding:2px 18px 16px}
details.fold>div>:last-child{margin-bottom:0}
details.fold h3{margin:18px 0 8px}
details.how{margin:8px 0 16px;border-top:1px solid var(--line)}
details.how>summary{font:15px/1.4 var(--sans);color:var(--muted)}
details.how>div{padding:4px 0 8px;font:15px/1.6 var(--sans);color:var(--muted);max-width:46rem}

/* Tables. */
table{border-collapse:collapse;font:15px/1.45 var(--sans);width:100%;margin:4px 0 8px}
.scroll{overflow-x:auto;max-width:100%}
@media (max-width:680px){main table:not(.vs):not(.cmp):not(.ledger){display:block;overflow-x:auto;max-width:100%}}
th,td{text-align:left;padding:9px 12px 9px 0;border-bottom:1px solid var(--line-2);vertical-align:top}
th{font:600 13px/1.3 var(--sans);color:var(--muted)}
td{font-variant-numeric:tabular-nums}
.vs{width:100%;max-width:46rem;border-collapse:collapse;margin:8px 0 12px;font:16px/1.5 var(--sans)}
.vs th{font:600 13.5px/1.25 var(--sans);color:var(--muted);text-align:left;padding:0 16px 10px 0;border-bottom:1px solid var(--line)}
.vs th.us{color:var(--ink);box-shadow:inset 0 -2px 0 var(--link)}
.vs td{width:50%;padding:12px 16px 12px 0;border-bottom:1px solid var(--line-2);vertical-align:top}
.vs td:first-child{color:var(--muted)}
.vs td:last-child{color:var(--ink);font-weight:600}
@media (max-width:520px){.vs{font-size:15px}}

/* The catalogue: every list on the site, searchable and sortable with no script. */
.catalogue{margin:8px 0 32px}
.tq{display:flex;flex-wrap:wrap;gap:10px 12px;align-items:flex-end;margin:0 0 14px;padding:14px 16px;background:var(--card);border:1px solid var(--line);border-radius:var(--radius)}
.tq label{display:flex;flex-direction:column;gap:5px;margin:0;font:600 13px/1.2 var(--sans);color:var(--muted)}
.tq .q{flex:1 1 16rem;min-width:0}
.tq input[type=search],.tq select{display:block;margin:0;width:100%;max-width:none;min-height:44px;padding:8px 12px;font:15px/1.3 var(--sans);color:var(--ink);background:var(--card);border:1px solid var(--rule);border-radius:var(--radius-s)}
.tq select{width:auto;min-width:8.5rem}
.tq input[type=search]:focus,.tq select:focus{border-color:var(--ink)}
.tq .btn{min-height:44px}
.tq .reset{align-self:center;font:15px/1.3 var(--sans);color:var(--link);min-height:44px;display:inline-flex;align-items:center}
.tq-row{display:flex;flex-wrap:wrap;gap:10px 12px;align-items:flex-end}
.tq-row+.tq-row{padding-top:12px;border-top:1px solid var(--line-2)}
.tq-k{flex:0 0 3.4rem;align-self:center;font:600 13px/1.2 var(--sans);color:var(--ink)}
@media (max-width:720px){.tq-k{flex-basis:100%}}
.net-q{flex-direction:column;align-items:stretch}
.pills{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:0 0 10px}
.pill{display:inline-flex;align-items:center;gap:8px;min-height:36px;padding:0 13px;border:1px solid var(--line);border-radius:999px;background:var(--card);color:var(--ink);text-decoration:none;font:14px/1.2 var(--sans)}
.pill:hover{border-color:var(--ink);color:var(--ink)}
.pill .x{font-size:16px;color:var(--muted)}
.pill.on{border-color:var(--ink);background:var(--ink);color:var(--on-ink)}.pill.on .x{color:var(--on-ink)}
.count{font:14px/1.4 var(--sans);color:var(--muted);margin:0 0 6px}
.ledger-scroll{overflow-x:auto}
.catalogue .ledger-scroll{background:var(--card);border:1px solid var(--line);border-radius:var(--radius);padding:2px 18px}
table.ledger{width:100%;border-collapse:collapse;font:15px/1.45 var(--sans);margin:0}
.ledger thead th{font:600 12.5px/1.25 var(--sans);color:var(--muted);text-align:left;vertical-align:bottom;padding:12px 14px 9px 0;border-bottom:1px solid var(--line);white-space:nowrap}
.ledger thead th a,.ledger thead th>span{display:inline-flex;align-items:center;min-height:32px;color:inherit;text-decoration:none}
.ledger thead th a:hover{color:var(--ink);text-decoration:underline;text-decoration-color:var(--rule)}
.ledger thead th[aria-sort] a{color:var(--ink)}
.ledger .dir{font-size:9px;margin-left:5px}
.ledger td{padding:14px 14px 14px 0;border-bottom:1px solid var(--line-2);vertical-align:top}
.ledger tbody tr:last-child td{border-bottom:0}
.ledger td.num,.ledger th.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.ledger th.num a,.ledger th.num>span{justify-content:flex-end}
.ledger td.main{min-width:14rem}
.ledger td.nw{white-space:nowrap}
.ledger td.main a.t{font:500 1.05rem/1.4 var(--serif);color:var(--ink);text-decoration:none}
.ledger td.main a.t:hover{text-decoration:underline;text-decoration-color:var(--rule)}
.ledger td .under{display:block;margin-top:5px;font:13px/1.45 var(--sans);color:var(--muted);overflow-wrap:anywhere;white-space:normal}
.ledger td .under a{color:var(--muted)}
.ledger td .under .mono{font-size:12px}
.ledger td.st{white-space:nowrap;width:1%}
.ledger td.st .status{margin-top:0}
.pager{display:flex;align-items:center;justify-content:center;gap:16px;margin:18px 0 0;font:15px/1.4 var(--sans);color:var(--muted)}
.pager a{display:inline-flex;align-items:center;min-height:44px;padding:0 16px;background:var(--card);border:1px solid var(--line);border-radius:var(--radius-s);color:var(--ink);text-decoration:none;font-weight:600}
.pager a:hover{border-color:var(--ink)}
@media (max-width:720px){
.ledger-scroll{overflow:visible}
.catalogue .ledger-scroll{padding:0 14px}
table.ledger,.ledger tbody,.ledger tr,.ledger td{display:block}
.ledger thead{display:none}
.ledger tr{padding:14px 0;border-bottom:1px solid var(--line-2)}
.ledger tbody tr:last-child{border-bottom:0}
.ledger td{border:0;padding:0;width:auto!important;min-width:0!important}
.ledger td.main{margin:0 0 8px}
.ledger td:not(.main){display:inline-flex;align-items:center;gap:6px;margin:0 16px 6px 0;font-size:14px;text-align:left}
.ledger td:not(.main){flex-wrap:wrap;max-width:100%;white-space:normal}
.ledger td:not(.main) .under{flex-basis:100%;margin-top:0}
.ledger td:not(.main)[data-label]::before{content:attr(data-label);font:13px/1.3 var(--sans);color:var(--muted)}
.ledger td.st::before{display:none}
.ledger td[data-phone="hide"]{display:none}
.tq select{min-width:0;width:100%}
.tq label:not(.q){flex:1 1 9rem}
}
.views{display:inline-flex;margin:0 0 20px;border:1px solid var(--line);border-radius:var(--radius-s);overflow:hidden;background:var(--card)}
.views a{display:inline-flex;align-items:center;min-height:40px;padding:0 18px;font:15px/1 var(--sans);color:var(--ink);text-decoration:none}
.views a+a{border-left:1px solid var(--line)}
.views a[aria-current]{background:var(--ink);color:var(--on-ink);font-weight:600}
.views a:not([aria-current]):hover{background:var(--sunk)}

/* Figures and charts. */
.chart{background:var(--card);border:1px solid var(--line);border-radius:var(--radius);padding:16px 18px 12px}
.chart svg{display:block;width:100%;height:auto;margin:6px 0 4px}
.tip{position:fixed;pointer-events:none;background:var(--ink);color:var(--on-ink);font:13px/1.3 var(--sans);padding:5px 8px;border-radius:5px;display:none;z-index:10}
.figs{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,21rem),1fr));gap:16px;margin:16px 0 8px}
@media (min-width:1100px){.figs.three-two{grid-template-columns:repeat(6,minmax(0,1fr))}.figs.three-two>.fig{grid-column:span 2}.figs.three-two>.fig:nth-child(n+4){grid-column:span 3}}
.fig{margin:0 0 20px;background:var(--card);border:1px solid var(--line);border-radius:var(--radius);padding:16px 18px 14px;min-width:0}
.figs .fig{margin:0}
.fig.illustrative{border-style:dashed;border-color:var(--rule)}
.fig.wide{grid-column:1/-1}
.fig figcaption{display:flex;flex-wrap:wrap;align-items:center;gap:6px 12px;margin:0 0 14px}
.fig-title{font:550 1.15rem/1.3 var(--serif);color:var(--ink)}
.fig-caption{flex-basis:100%;font:14px/1.5 var(--sans);color:var(--muted)}
.fig svg{display:block;width:100%;height:auto}
.fig .scroll{overflow-x:auto;margin:0 -2px}
.fig .scroll svg{min-width:640px}
.fig .scroll-hint{display:none;margin:6px 0 0}
@media (max-width:680px){.fig .scroll-hint{display:block}}
.fig svg text{font-family:var(--sans)}
.fig svg .lbl{font-size:13px;fill:var(--ink);paint-order:stroke;stroke:var(--card);stroke-width:4px;stroke-linejoin:round}
.fig svg .lbl.muted{fill:var(--muted);font-size:12px}
.fig svg .lbl.x{font-size:11px;font-weight:700;stroke:none}
.fig svg .lbl.b{font-weight:700}
.fig details summary{margin-top:8px}
.fig table{font-size:14px}
.fig.diagram .scroll svg{min-width:680px}
.fig.diagram svg .lbl{stroke:none}
.wrap:not(.wide) .fig.diagram{width:min(800px,calc(100vw - 32px));margin-left:calc(50% - min(400px,(100vw - 32px) / 2))}
.fig svg a{text-decoration:none}
.fig svg a:hover .lbl{text-decoration:underline;text-decoration-color:var(--rule)}
.mock{display:inline-block;font:600 11px/1 var(--sans);letter-spacing:.06em;text-transform:uppercase;color:var(--amber-ink);background:var(--amber-wash);padding:5px 8px;border-radius:999px;white-space:nowrap}
.notice .mock{margin-right:8px;vertical-align:middle}
.hbar{display:grid;grid-template-columns:7rem 1fr 2.5rem;align-items:center;gap:10px;font:14px/1.4 var(--sans);margin:6px 0}
.hbar .bar{display:block;height:10px;border-radius:0 5px 5px 0}
.bars{list-style:none;padding:0;margin:4px 0 8px;display:grid;gap:8px;font:14px/1.3 var(--sans)}
.bars li{display:grid;grid-template-columns:minmax(5.5rem,8.5rem) minmax(0,1fr) 3rem;align-items:center;gap:10px;min-width:0}
.bars .k{text-align:right;overflow-wrap:anywhere;color:var(--ink)}
.bars .k a{text-decoration-color:var(--line)}
.bars .k .g{display:inline-block;width:1.1em;font-size:.95em;color:var(--ink)}
.bars .b{display:block;height:14px;background:var(--sunk);border-radius:4px;overflow:hidden}
.bars .f{display:block;height:100%;border-radius:4px;box-sizing:border-box}
.bars .v{font-variant-numeric:tabular-nums;color:var(--ink)}
.f.ink,.c.ink{background:var(--ink)}
.f.sound,.c.sound{background:var(--st-est)}
.f.part,.c.part{background:var(--st-sup)}
.f.mid,.c.mid{background:var(--rule)}
.f.pale,.c.pale{background:var(--line)}
.f.open,.c.open{background:var(--card);border:1px dashed var(--st-unc)}
.f.accent,.c.accent{background:var(--accent)}
.f.risk,.c.risk{background:var(--st-con)}
.f.broken,.c.broken{background:var(--st-ref)}
.hist{list-style:none;margin:8px 0 38px;padding:0;display:grid;grid-template-columns:repeat(var(--n),minmax(0,1fr));gap:4px;height:200px;border-bottom:1px solid var(--rule)}
.hist li{position:relative;min-width:0;height:100%}
.hist .c{position:absolute;left:0;right:0;bottom:0;height:var(--h);border-radius:4px 4px 0 0;box-sizing:border-box}
.hist .v{position:absolute;left:0;right:0;bottom:calc(var(--h) + 4px);text-align:center;font:12px/1 var(--sans);color:var(--ink);font-variant-numeric:tabular-nums}
.hist .x{position:absolute;left:0;right:0;top:calc(100% + 6px);text-align:center;font:11px/1.2 var(--sans);color:var(--muted);overflow-wrap:anywhere}
@media (max-width:480px){.hist .x{font-size:10px}.hist .v{font-size:11px}}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,9.5rem),1fr));gap:12px;margin:8px 0 24px}
.stat{display:flex;flex-direction:column;gap:3px;background:var(--card);border:1px solid var(--line);border-radius:var(--radius);padding:14px 16px 13px;min-width:0;color:var(--ink);text-decoration:none}
a.stat:hover{border-color:var(--ink)}
.stat.warn{background:var(--amber-wash);border-color:transparent}
.stat-v{font:550 1.9rem/1.1 var(--serif);letter-spacing:-.01em;font-variant-numeric:tabular-nums;color:var(--ink);overflow-wrap:anywhere}
.stat-l{font:650 14px/1.3 var(--sans);color:var(--ink)}
.stat-n{font:13px/1.45 var(--sans);color:var(--muted)}
.stat.warn .stat-n::before{content:"\\25C6  ";color:var(--amber)}
.stat.t-sound .stat-v,.stat.t-part .stat-v{color:var(--green)}
.stat.t-risk .stat-v{color:var(--amber-ink)}
.stat.t-broken .stat-v{color:var(--rose-ink)}
.stat.t-open .stat-v{color:var(--muted)}
.steps{list-style:none;padding:0;margin:8px 0 24px;display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,11.5rem),1fr));gap:16px}
.step{min-width:0;background:var(--card);border:1px solid var(--line);border-radius:var(--radius);padding:18px}
.step-n{display:inline-flex;align-items:center;justify-content:center;width:28px;height:28px;border-radius:50%;background:var(--ink);color:var(--on-ink);font:600 14px/1 var(--sans);margin:0 10px 12px 0;vertical-align:middle}
.step-icon{display:inline-block;width:44px;height:44px;vertical-align:middle;margin:0 0 12px}
.step h3{margin:0 0 6px}
.step p{font-size:15.5px;line-height:1.55;color:var(--muted);margin:0}
.flow{list-style:none;margin:8px 0 4px;padding:0;display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,6rem),1fr));gap:12px 22px}
.flow li{position:relative;min-width:0;display:flex;flex-direction:column;gap:3px;padding:12px 12px 10px;border:1px solid var(--line);border-radius:var(--radius-s);background:var(--card)}
.flow li+li::before{content:"\\2192";position:absolute;left:-19px;top:10px;color:var(--rule);font:18px/1 var(--sans)}
.flow b{font:550 1.05rem/1.2 var(--serif);color:var(--ink)}
.flow span{font:14px/1.4 var(--sans);color:var(--ink)}
.flow small{font:12.5px/1.4 var(--sans);color:var(--muted)}
.wrap:not(.wide) .flow{grid-template-columns:1fr;gap:18px}
.wrap:not(.wide) .flow li+li::before{content:"\\2193";left:14px;top:-20px}
@media (max-width:640px){.flow{grid-template-columns:1fr;gap:18px}.flow li+li::before{content:"\\2193";left:14px;top:-20px}}
.graph-key{display:flex;flex-wrap:wrap;gap:4px 16px;margin:8px 0 0;font:13px/1.4 var(--sans);color:var(--muted)}
.fig svg.net .lbl{font-size:12px;stroke:var(--card)}
.net .grp{fill:var(--sunk);stroke:var(--line)}
.net .cap{font-size:12px;fill:var(--muted)}
.net a .cap{fill:var(--link);text-decoration:underline}
.net .cap.sec{font:500 17px var(--serif);fill:var(--ink)}
.net line.sec{stroke:var(--rule)}
.net .e,.net-key .e{stroke:var(--rule);stroke-linecap:round}
.net-key .e{stroke-width:2}
.net .e.id,.net-key .e.id{stroke-dasharray:5 4}
.net .e.ref,.net-key .e.ref{stroke:var(--st-ref)}
.net .e.dim{opacity:.15}
.net g.dim{opacity:.2}
.net .ring,.net-key .ring{stroke:var(--link);stroke-width:2.5}
.net-key .shp{stroke:var(--ink);stroke-width:1.5}
.fig .net-key svg.k{display:inline-block;width:auto;height:auto;vertical-align:middle;margin:0 4px 0 0}
.net-key .graph-key{margin:6px 0 0}

/* Comparisons. */
.cmp-cap{margin:8px 0 4px}
.cmp-key{display:flex;flex-wrap:wrap;gap:2px 18px;margin:0 0 8px}
.cmp-wrap{overflow-x:auto;margin:0 0 8px;background:var(--card);border:1px solid var(--line);border-radius:var(--radius)}
.wrap:not(.wide) .cmp-wrap{width:min(960px,calc(100vw - 32px));margin-left:calc(50% - min(480px,(100vw - 32px) / 2))}
.cmp{border-collapse:separate;border-spacing:0;width:100%;min-width:46rem;margin:0;font:15px/1.4 var(--sans)}
.cmp th,.cmp td{padding:12px 8px;border-bottom:1px solid var(--line-2);text-align:center;vertical-align:middle}
.cmp tbody tr:last-child th,.cmp tbody tr:last-child td{border-bottom:0}
.cmp thead th{font:600 13.5px/1.2 var(--sans);color:var(--ink);white-space:nowrap;padding:14px 8px 10px;border-bottom:1px solid var(--line)}
.cmp th[scope=row]{position:sticky;left:0;z-index:1;text-align:left;background:var(--card);min-width:14rem;max-width:18rem;padding:12px 14px 12px 16px}
.cmp thead th:first-child{position:sticky;left:0;z-index:2;background:var(--card)}
.cmp th[scope=row] .t{display:block;font:500 1.03rem/1.3 var(--serif);color:var(--ink)}
.cmp th[scope=row] .d{display:block;font:13.5px/1.4 var(--sans);color:var(--muted);margin-top:3px}
.cmp .us{background:var(--green-wash)}
.cmp thead th.us{box-shadow:inset 0 3px 0 var(--green)}
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

/* The API reference. */
.verb{display:inline-block;font:700 12px/1 var(--mono);letter-spacing:.04em;padding:4px 7px;border-radius:5px;border:1px solid var(--line);color:var(--ink);background:var(--card);vertical-align:middle}
.verb.post{background:var(--ink);border-color:var(--ink);color:var(--on-ink)}
.req{font:600 12px/1 var(--sans);color:var(--link);letter-spacing:.02em}
.op{border-top:1px solid var(--line);padding:16px 0 8px;margin:0 0 8px}
.op h3{margin:0 0 8px;overflow-wrap:anywhere}.op h4{font:600 13px/1.3 var(--sans);color:var(--muted);text-transform:uppercase;letter-spacing:.06em;margin:16px 0 6px}
dl.schema{margin:0 0 8px;padding-left:0;border-left:2px solid var(--line)}
dl.schema dt{margin:8px 0 0 12px;font:15px/1.4 var(--sans)}dl.schema dd{margin:2px 0 0 12px;font:15px/1.55 var(--sans);color:var(--ink);max-width:48rem}
dl.schema dl.schema{margin:6px 0 0 0}

/* Questions. */
.faq{margin:0 0 8px;max-width:46rem;background:var(--card);border:1px solid var(--line);border-radius:var(--radius);padding:0 20px}
.faq details{border-bottom:1px solid var(--line-2)}
.faq details:last-child{border-bottom:0}
.faq summary{display:flex;align-items:center;gap:16px;min-height:44px;margin:0;padding:15px 0;list-style:none;font:500 1.1rem/1.35 var(--serif);color:var(--ink)}
.faq summary::before{content:none}
.faq summary::after{content:"+";flex:0 0 auto;margin-left:auto;font:400 1.4rem/1 var(--sans);color:var(--muted)}
.faq details[open] summary::after{content:"\\2212"}
.faq summary:hover{text-decoration:underline;text-decoration-color:var(--rule);text-underline-offset:.2em}
.faq .a{padding:0 0 18px;max-width:42rem}
.faq .a p{margin:0 0 10px}
.faq .a p:last-child{margin:0}

/* A claim earning its standing, step by step (the front page). */
.trace-fig{max-width:56rem}
.trace{list-style:none;padding:0;margin:0}
.trace li{display:grid;grid-template-columns:minmax(0,1fr) minmax(12rem,20rem);gap:8px 24px;align-items:center;padding:14px 0;border-bottom:1px solid var(--line-2)}
.trace li:last-child{border-bottom:0}
.trace .tx b{display:block;font:550 1.05rem/1.3 var(--serif);color:var(--ink)}
.trace .tx span{display:block;font:14px/1.5 var(--sans);color:var(--muted);margin-top:2px}
.trace .tm{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:8px 12px;align-items:center}
.trace .gauge{position:relative;display:block;height:10px;border-radius:5px;background:var(--m-uns)}
.trace .gauge .fill{position:absolute;left:0;top:0;bottom:0;border-radius:5px;background:var(--st-sup)}
.trace .gauge .bar{position:absolute;top:-6px;bottom:-6px;width:3px;margin-left:-1.5px;border-radius:2px;background:var(--ink)}
.trace .tv{font:600 15px/1 var(--sans);font-variant-numeric:tabular-nums;color:var(--ink)}
.trace .status{grid-column:1/-1;justify-self:start;margin-top:0}
@media (max-width:600px){.trace li{grid-template-columns:1fr}}
.trace-key{display:flex;flex-wrap:wrap;gap:4px 20px;font:14px/1.4 var(--sans);color:var(--muted);margin:10px 0 0}
.trace-key i{display:inline-block;vertical-align:middle;margin-right:8px}
.trace-key .k-fill{width:20px;height:8px;border-radius:4px;background:var(--st-sup)}
.trace-key .k-bar{width:3px;height:16px;border-radius:2px;background:var(--ink)}

/* Credence: the ruler, the small bar in tables, the strip of every claim. */
.rmini{display:inline-flex;align-items:center;gap:8px;font-variant-numeric:tabular-nums}
.rmini b{font:600 15px/1 var(--sans);min-width:2.4em;text-align:right}
.rtrack{position:relative;display:block;width:56px;height:6px;border-radius:3px;background:var(--line)}
.rfill{position:absolute;left:0;top:0;bottom:0;border-radius:3px;background:var(--st-unc)}
.rfill.sound{background:var(--st-est)}.rfill.part{background:var(--st-sup)}
.rfill.risk{background:var(--st-con)}
.rfill.open{background:var(--st-unc)}
.rfill.broken{background:var(--st-ref)}
.rtick{position:absolute;top:-3px;bottom:-3px;width:1px;background:var(--muted)}
.ruler{margin:8px 0 4px}
.ru-scale{position:relative;height:22px;margin:0 9px}
.ru-track{position:absolute;left:-9px;right:-9px;top:8px;height:6px;border-radius:3px;background:var(--line)}
.ru-fill{position:absolute;left:-9px;top:8px;height:6px;border-radius:3px 0 0 3px;background:var(--st-unc)}
.ru-fill.sound{background:var(--st-est)}.ru-fill.part{background:var(--st-sup)}.ru-fill.risk{background:var(--st-con)}.ru-fill.open{background:var(--st-unc)}.ru-fill.broken{background:var(--st-ref)}
.ru-tick{position:absolute;top:2px;width:1.5px;height:18px;margin-left:-.75px;background:var(--muted)}
.ru-prior{position:absolute;top:5px;width:12px;height:12px;margin-left:-6px;border-radius:50%;background:var(--card);border:2px solid var(--muted);box-sizing:border-box}
.ru-needle{position:absolute;top:1px;width:20px;height:20px;margin-left:-10px;border-radius:50%;background:var(--ink);border:3px solid var(--card);box-sizing:border-box;box-shadow:0 0 0 1px var(--ink)}
.ru-needle.risk{background:var(--st-con);box-shadow:0 0 0 1px var(--st-con)}
.ru-needle.open{background:var(--card);border:2px dashed var(--ink);box-shadow:none}
.ru-needle.broken{background:var(--st-ref);box-shadow:0 0 0 1px var(--st-ref)}
.ru-axis{position:relative;height:18px;margin:4px 9px 0;font:12.5px/1 var(--sans);color:var(--muted);font-variant-numeric:tabular-nums}
.ru-axis span{position:absolute;top:0;transform:translateX(-50%);white-space:nowrap}
.ru-axis span:first-child{transform:none;margin-left:-9px}.ru-axis span:last-child{transform:translateX(-100%);margin-left:9px}
.ru-key{margin:8px 0 0;font:13px/1.5 var(--sans);color:var(--muted)}
.strip{margin:6px 0 2px;font:14px/1.3 var(--sans)}
.st-row{display:grid;grid-template-columns:10rem minmax(0,1fr);align-items:center;min-height:40px;border-bottom:1px solid var(--line-2);color:var(--ink);text-decoration:none}
a.st-row:hover .st-k{text-decoration:underline;text-decoration-color:var(--rule)}
a.st-row.on{background:var(--sunk)}
a.st-row.on .st-k{font-weight:700}
.st-row:last-child{border-bottom:0}
.st-k{padding-right:14px;color:var(--ink);white-space:nowrap}.st-k b{font-weight:600;font-variant-numeric:tabular-nums;color:var(--muted);margin-left:2px}
.st-lane{position:relative;height:40px;margin:0 6px}
.st-lane b{position:absolute;top:0;bottom:0;border-left:1px dashed var(--rule)}
.st-lane i{position:absolute;width:10px;height:10px;margin:-5px 0 0 -5px;border-radius:50%;background:var(--st-unc);box-shadow:0 0 0 1.5px var(--card)}
.st-lane i.sound{background:var(--st-est)}.st-lane i.part{background:var(--st-sup)}.st-lane i.open{background:var(--card);border:1.5px solid var(--st-unc);box-sizing:border-box}.st-lane i.risk{background:var(--st-con)}.st-lane i.broken{background:var(--st-ref)}
.st-axis{border:0;min-height:24px}
.st-axis .st-k{color:var(--muted);font-size:13px}
.st-axis .st-lane{height:24px}
.st-axis .st-lane span{position:absolute;top:6px;transform:translateX(-50%);font:12.5px/1 var(--sans);color:var(--muted);font-variant-numeric:tabular-nums}
@media (max-width:520px){.st-row{grid-template-columns:7.2rem minmax(0,1fr)}.st-k{font-size:13px;padding-right:8px}}
.plate-note{margin:4px 0 12px}
.status-key{list-style:none;padding:0;margin:8px 0 0;display:grid;gap:10px}
.status-key li{display:grid;grid-template-columns:7.5rem minmax(0,1fr);gap:12px;align-items:baseline;font:15px/1.5 var(--sans)}
.status-key .status{margin:0;justify-self:start}
@media (max-width:520px){.status-key li{grid-template-columns:1fr;gap:4px}}
.specimen-label{margin:0;background:var(--card);border:1px solid var(--line);border-radius:var(--radius)}
.specimen-label>div{display:grid;grid-template-columns:minmax(9rem,13rem) minmax(0,1fr);gap:4px 20px;padding:12px 18px;border-top:1px solid var(--line-2)}
.specimen-label>div:first-child{border-top:0}
.specimen-label dt{font:600 14px/1.35 var(--sans);color:var(--ink)}
.specimen-label dt span{display:block;font:400 13px/1.4 var(--sans);color:var(--muted);margin-top:2px}
.specimen-label dd{margin:0;font:1.02rem/1.5 var(--serif);color:var(--ink)}
.specimen-label>div:first-child dd{font-size:1.15rem}
@media (max-width:560px){.specimen-label>div{grid-template-columns:1fr}}

/* A claim's place in the network: what it rests on, it, what rests on it. */
.nbhd{display:grid;grid-template-columns:minmax(0,1fr) 28px minmax(0,0.8fr) 28px minmax(0,1fr);gap:0;align-items:stretch;padding:4px 0 8px}
.nb-col h3{font:600 13px/1.2 var(--sans);color:var(--muted);margin:0 0 10px}
.nb-col ul{list-style:none;padding:0;margin:0;display:grid;gap:8px}
.nb{display:grid;grid-template-columns:18px minmax(0,1fr);gap:2px 8px;padding:10px 12px;background:var(--card);border:1px solid var(--line);border-radius:var(--radius-s);color:var(--ink);text-decoration:none;min-height:44px}
.nb:hover{border-color:var(--ink)}
.nb-s{font-size:12px;line-height:1.5;color:var(--ink)}.nb-s.risk{color:var(--amber-ink)}
.nb-t{font:15px/1.4 var(--serif)}
.nb-r{grid-column:2;font:12.5px/1.35 var(--sans);color:var(--muted)}
.nb-more a,.nb-none{font:14px/1.4 var(--sans);color:var(--muted)}
.nb-none{margin:0;padding:10px 12px;border:1px dashed var(--line);border-radius:var(--radius-s)}
.nb-self{display:flex;flex-direction:column;justify-content:center;align-items:center;align-self:center;text-align:center;padding:16px 12px;border:1.5px solid var(--ink);border-radius:var(--radius-s);background:var(--card)}
.nb-self h3{margin:0 0 6px}.nb-me{margin:0 0 6px}.nb-self .small{margin:0}
.nb-arrow{position:relative;align-self:center;height:20px}
.nb-arrow::before{content:"";position:absolute;left:4px;right:6px;top:50%;border-top:1.5px solid var(--rule)}
.nb-arrow::after{content:"";position:absolute;right:4px;top:calc(50% - 4px);border:4.5px solid transparent;border-left:7px solid var(--rule);border-right:0}
@media (max-width:820px){.nbhd{grid-template-columns:1fr;gap:0}.nb-arrow{height:28px}.nb-arrow::before{left:50%;right:auto;top:4px;bottom:8px;border-top:0;border-left:1.5px solid var(--rule)}.nb-arrow::after{left:calc(50% - 4px);right:auto;top:auto;bottom:4px;border:4.5px solid transparent;border-top:7px solid var(--rule);border-bottom:0}}
.lineage{list-style:none;padding:0;margin:8px 0 14px;max-width:46rem}
.lineage li{position:relative;padding:0 0 12px 26px;font:15px/1.5 var(--sans)}
.lineage li::before{content:"";position:absolute;left:7px;top:0;bottom:0;width:2px;background:var(--line)}
.lineage li:last-child::before{bottom:auto;height:10px}
.lineage li::after{content:"";position:absolute;left:2px;top:5px;width:12px;height:12px;border-radius:50%;background:var(--link);border:2px solid var(--ground)}
.lineage li.human::after{background:var(--card);border:2px solid var(--ink)}
.lineage .g{display:block;font:13px/1.4 var(--sans);color:var(--muted)}

/* The older claim-page parts some pages still use. */
.panel{background:var(--card);border:1px solid var(--line);border-radius:var(--radius);padding:18px 18px 16px;margin:0 0 24px}
.panel .status{margin:0}
.panel .ruler{margin:6px 0 0}
.panel dl{display:grid;grid-template-columns:auto minmax(0,1fr);gap:8px 14px;margin:12px 0 0;font:14px/1.45 var(--sans)}
.panel dt{color:var(--muted)}
.panel dd{margin:0;color:var(--ink);font-variant-numeric:tabular-nums;overflow-wrap:anywhere}
.panel .acts{display:flex;flex-wrap:wrap;gap:8px;margin:14px 0 0}
.panel .acts a{display:inline-flex;align-items:center;min-height:40px;padding:0 12px;border:1px solid var(--line);border-radius:var(--radius-s);font:14px/1 var(--sans);color:var(--ink);text-decoration:none;background:var(--card)}
.panel .acts a:hover{border-color:var(--ink)}
ol.rungs{list-style:none;padding:0;margin:12px 0;display:grid;gap:22px;max-width:44rem}
ol.rungs li{position:relative;background:var(--card);border:1px solid var(--line);border-left:3px solid var(--ink);border-radius:var(--radius-s);padding:12px 14px;font:15px/1.5 var(--sans);color:var(--ink)}
ol.rungs li+li::before{content:"\\2193";position:absolute;top:-22px;left:18px;font:600 16px/22px var(--sans);color:var(--muted)}
ol.rungs .rung-what,ol.rungs .rung-then{display:block;margin-top:6px}
ol.rungs .rung-then{color:var(--muted)}
ol.ladder{list-style:none;padding:0;margin:0 0 18px;display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}
@media (max-width:760px){ol.ladder{grid-template-columns:1fr}}
ol.ladder>li{display:grid;grid-template-columns:28px minmax(0,1fr);gap:0 10px;align-items:start;background:var(--card);border:1px solid var(--line);border-radius:var(--radius);padding:14px 16px;font:14.5px/1.5 var(--sans);color:var(--ink)}
ol.ladder .mark{display:inline-flex;align-items:center;justify-content:center;width:26px;height:26px;border-radius:50%;font:700 13px/1 var(--sans);border:1.5px dashed var(--rule);color:var(--muted)}
ol.ladder li.confirmed .mark{background:var(--green-wash);border:0;color:var(--green-ink)}
ol.ladder li.failed .mark{background:var(--rose-wash);border:0;color:var(--rose-ink)}
ol.ladder li.mixed .mark{background:var(--amber-wash);border:0;color:var(--amber-ink)}
ol.ladder li.listed .mark{background:var(--sunk);border:1px solid var(--rule);color:var(--ink)}
ol.ladder b{display:block;font-weight:650}
ol.ladder .name{display:block;font-size:13px;color:var(--muted);margin:1px 0 6px}
ol.ladder p{margin:0;color:var(--ink-2)}
.panel p:first-child{margin:0 0 4px}
.crumbs{font:14px/1.5 var(--sans);color:var(--muted);margin:0 0 14px}
.crumbs a{color:var(--link)}
.crumbs a+.sep+a,.crumbs .sep+a{color:var(--muted);text-decoration:none}
.crumbs .sep+a:hover{color:var(--ink);text-decoration:underline}
.crumbs .mono{font-size:12.5px}
.crumbs .sep{margin:0 5px;color:var(--faint)}
.quote-src{font:15px/1.55 var(--sans);color:var(--muted);margin:0 0 18px}
.test{border-left:3px solid var(--line);padding:2px 0 2px 16px;margin:0 0 24px}
.test b{display:block;font:600 13px/1.3 var(--sans);color:var(--muted);margin:0 0 4px}
.test p{margin:0;font:1.05rem/1.55 var(--serif)}
.said{display:block;margin-top:4px}
dl.facts{display:grid;grid-template-columns:minmax(7rem,9.5rem) minmax(0,1fr);gap:8px 16px;margin:0 0 4px;font:14.5px/1.55 var(--sans);color:var(--muted)}
dl.facts dt{font-weight:600;color:var(--ink)}
dl.facts dd{margin:0;overflow-wrap:anywhere}
@media (max-width:520px){dl.facts{grid-template-columns:1fr;gap:0}dl.facts dd{margin:0 0 8px}}
dl.facts.wide{grid-template-columns:minmax(7rem,9rem) minmax(0,1fr);max-width:52rem;margin:8px 0 12px;font-size:15px}
p.meaning{font:16px/1.55 var(--sans);margin:12px 0 16px}
p.meaning .status{margin:0 6px 0 0;vertical-align:1px}
.doc h3{margin:28px 0 8px}
h1.claim-h1{font-size:clamp(1.75rem,3.4vw,2.6rem);line-height:1.15;max-width:none;letter-spacing:-.015em}

/* One claim, as Lucy Griffiths drew it (9 October 2026): the story first, the record after, a glance beside. */
.claim{display:grid;gap:0 44px}
.claim>*{min-width:0}
@media (min-width:1040px){.claim{grid-template-columns:minmax(0,1fr) 19rem;align-items:start}.claim .c-head,.claim .c-body{grid-column:1}.claim .glance-col{grid-column:2;grid-row:1 / span 2;position:sticky;top:20px}}
.c-status{display:flex;flex-wrap:wrap;align-items:center;gap:8px 12px;margin:0 0 14px;font:14px/1.45 var(--sans);color:var(--muted)}
.c-h1{font:550 clamp(1.95rem,3.9vw,2.75rem)/1.12 var(--serif);letter-spacing:-.012em;margin:0 0 18px;max-width:none;text-wrap:balance}
.c-h1.long{font-size:clamp(1.6rem,3vw,2.15rem);line-height:1.2}
.c-h1.longest{font-size:clamp(1.4rem,2.5vw,1.8rem);line-height:1.28}
.c-h1.quoted{font-weight:500}
.c-lede{font:18.5px/1.62 var(--sans);color:var(--ink-2);max-width:44rem;margin:0 0 24px}
.quote-card{background:var(--card);border:1px solid var(--line);border-radius:var(--radius);padding:18px 22px 16px;margin:0 0 18px}
.quote-card blockquote{margin:0 0 12px;font:400 1.22rem/1.58 var(--serif);color:var(--ink)}
.quote-card blockquote p{margin:0}
.quote-card .src{font:13.5px/1.5 var(--sans);color:var(--muted);margin:0}
.quote-card dl{margin:12px 0 0;padding-top:10px;border-top:1px solid var(--line-2);font:14px/1.5 var(--sans)}
.quote-card dt{display:inline;font-weight:650}
.quote-card dd{display:inline;margin:0}
.quote-card dd::after{content:"";display:block;margin-bottom:4px}
.facets{margin:0 0 6px}
.facets p{display:flex;flex-wrap:wrap;align-items:center;gap:6px 6px;margin:0 0 8px;font:14px/1.4 var(--sans)}
.facets .k{font:600 12px/1.3 var(--sans);letter-spacing:.09em;text-transform:uppercase;color:var(--muted);margin-right:8px}
.facets .path a{color:var(--ink);text-decoration:none}
.facets .path a:hover{text-decoration:underline;text-decoration-color:var(--rule)}
.facets .path a:last-child{font-weight:650}
.facets .path .sep{color:var(--faint);margin:0 2px}
.chip{display:inline-flex;align-items:center;min-height:36px;padding:0 12px;background:var(--card);border:1px solid var(--line);border-radius:999px;color:var(--ink);text-decoration:none;font:13.5px/1.2 var(--sans)}
a.chip:hover{border-color:var(--ink);color:var(--ink)}
.c-body>section{margin:0 0 8px}
.c-body h2{margin:44px 0 14px}
.work-card{display:grid;grid-template-columns:minmax(0,1fr) minmax(12rem,15rem);gap:16px 28px;align-items:start}
@media (max-width:640px){.work-card{grid-template-columns:1fr}}
.work-card .title{font:550 1.2rem/1.35 var(--serif);margin:0 0 8px}
.work-card .who{font:14.5px/1.5 var(--sans);color:var(--ink-2);margin:0 0 4px}
.work-card .where{font:14.5px/1.5 var(--sans);color:var(--muted);margin:0}
.work-card .gist{font:15px/1.55 var(--sans);color:var(--ink-2);margin:10px 0 0}
.work-card dl{display:grid;grid-template-columns:auto auto;gap:6px 14px;margin:0 0 14px;font:14px/1.35 var(--sans)}
.work-card dt{color:var(--muted)}
.work-card dd{margin:0;text-align:right;font-weight:650;color:var(--ink)}
.prose{max-width:44rem}
.prose p{font:17px/1.65 var(--sans)}
.story{list-style:none;margin:0;padding:0;display:grid;gap:10px}
.story>li{display:grid;grid-template-columns:30px minmax(0,1fr);gap:4px 16px;background:var(--card);border:1px solid var(--line);border-radius:var(--radius);padding:16px 20px 15px}
.story .n{display:inline-flex;align-items:center;justify-content:center;width:28px;height:28px;border-radius:50%;background:var(--ink);color:var(--on-ink);font:650 14px/1 var(--sans);margin-top:1px}
.story>li.here .n{background:var(--green);color:var(--on-green)}
.story h3{margin:2px 0 4px}
.story p,.story ul{margin:0;font:15.5px/1.6 var(--sans);color:var(--ink-2)}
.story ul{padding-left:1.1em}
.story ul li{margin:0 0 4px}
.story .from{font:13px/1.5 var(--sans);color:var(--muted);margin:6px 0 0}
.tells{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,16rem),1fr));gap:10px;margin:0 0 10px}
.tell{border-radius:var(--radius);padding:16px 18px}
.tell h3{font-size:15px;margin:0 0 6px}
.tell p,.tell ul{margin:0;font:15.5px/1.6 var(--sans);color:var(--ink)}
.tell ul{padding-left:1.1em}
.tell.show{background:var(--green-wash)}.tell.show h3{color:var(--green-ink)}
.tell.dont{background:var(--amber-wash)}.tell.dont h3{color:var(--amber-ink)}
.tell.fail{background:var(--rose-wash)}.tell.fail h3{color:var(--rose-ink)}
.tell.none{background:var(--sunk)}
.next{display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:12px 24px}
.next p{flex:1 1 22rem;margin:0;font:15.5px/1.6 var(--sans)}
.sure .big{display:flex;flex-wrap:wrap;align-items:baseline;gap:4px 12px;margin:0 0 16px;font:15.5px/1.4 var(--sans);color:var(--ink-2)}
.sure .big b{font:500 2.9rem/1 var(--serif);letter-spacing:-.02em;color:var(--ink)}
.cm{margin:0}
.cm-track{position:relative;display:flex;height:12px;border-radius:6px;margin:12px 0 0}
.cm-track>span{display:block;height:100%}
.cm-track>span:first-child{border-radius:6px 0 0 6px}.cm-track>span:last-of-type{border-radius:0 6px 6px 0}
.cm .s-ref{background:var(--m-ref)}.cm .s-uns{background:var(--m-uns)}.cm .s-sup{background:var(--m-sup)}.cm .s-est{background:var(--m-est)}
.cm-ring{position:absolute;top:50%;width:16px;height:16px;margin:-8px 0 0 -8px;border-radius:50%;background:var(--card);border:2px solid var(--muted);box-sizing:border-box}
.cm-now{position:absolute;top:-7px;bottom:-7px;width:4px;margin-left:-2px;border-radius:2px;background:var(--ink);box-shadow:0 0 0 2px var(--card)}
.cm-legend{display:grid;margin:10px 0 0;font:12.5px/1.35 var(--sans);color:var(--muted)}
.cm-legend span{padding-right:6px}
.cm-legend span:last-child{text-align:right;padding-right:0}
.cm-key{margin:10px 0 0;font:13px/1.5 var(--sans);color:var(--muted)}
@media (max-width:560px){.cm-legend{grid-template-columns:1fr 1fr!important;gap:2px 10px}.cm-legend span:last-child{text-align:left}}
.nums{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin:10px 0}
@media (max-width:720px){.nums{grid-template-columns:repeat(2,minmax(0,1fr))}}
.nums .card{padding:14px 16px}
.nums .k{display:block;font:13px/1.3 var(--sans);color:var(--muted)}
.nums .v{display:block;font:550 1.75rem/1.2 var(--serif);font-variant-numeric:tabular-nums;color:var(--ink);margin:2px 0 6px}
.nums p{margin:0;font:13.5px/1.5 var(--sans);color:var(--muted)}
.posts{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,18rem),1fr));gap:10px}
.post{display:flex;flex-direction:column}
.post .hd{display:flex;flex-wrap:wrap;justify-content:space-between;gap:4px 12px;margin:0 0 10px;font:13px/1.4 var(--sans);color:var(--muted)}
.post .hd b{color:var(--ink);font:650 14px/1.4 var(--sans)}
.post .txt{background:var(--sunk);border-radius:var(--radius-s);padding:12px 14px;margin:0 0 14px;font:15px/1.6 var(--sans);white-space:pre-line;-webkit-user-select:all;user-select:all;cursor:text;overflow-wrap:anywhere}
.post .acts{display:flex;flex-wrap:wrap;gap:8px}
.post .acts .btn{min-height:44px;font-size:14px;padding:0 14px}
.refute{font:17px/1.65 var(--sans);max-width:44rem}
.refute+.by,p.by{font:13.5px/1.5 var(--sans);color:var(--muted);max-width:44rem}
.lit{list-style:none;margin:0;padding:0;display:grid;gap:10px}
.lit>li{background:var(--card);border:1px solid var(--line);border-radius:var(--radius);padding:14px 18px}
.lit .t{display:block;font:500 1.05rem/1.4 var(--serif);color:var(--ink);text-decoration:none}
.lit a.t:hover{text-decoration:underline;text-decoration-color:var(--rule)}
.lit .d{display:block;margin-top:5px;font:13.5px/1.5 var(--sans);color:var(--muted)}
.lit .status{margin:0 8px 0 0;vertical-align:1px}
hr.divide{border:0;border-top:1.5px solid var(--ink);margin:52px 0 0}
.c-body .record h2{margin-top:26px}
.glance{padding:18px 20px 20px}
.glance .eyebrow{margin:0 0 12px}
.glance dl{margin:0;display:grid;gap:11px}
.glance dl div{min-width:0}
.glance dt{font:13px/1.35 var(--sans);color:var(--muted)}
.glance dd{margin:1px 0 0;font:650 15px/1.4 var(--sans);color:var(--ink);overflow-wrap:anywhere}
.glance dd.mono{font:500 13px/1.4 var(--mono)}
.glance dd.t-sound,.glance dd.t-part{color:var(--green)}
.glance dd.t-risk{color:var(--amber-ink)}
.glance dd.t-broken{color:var(--rose-ink)}
.glance .acts{display:grid;gap:8px;margin:18px 0 0}
.glance .links{display:flex;flex-wrap:wrap;gap:0 14px;margin:8px 0 0;font:13.5px/1.4 var(--sans)}
.glance .links a{display:inline-flex;align-items:center;min-height:32px}
.newcomer{margin:12px 0 0;padding:16px 20px}
.newcomer p{font:14px/1.55 var(--sans);color:var(--ink-2);margin:0 0 8px}
.newcomer a{font:600 14px/1.4 var(--sans)}
@media (max-width:1039px){.glance-col{margin:4px 0 8px}}

/* The claims list, for people (her second design): each source with its claims. */
.lead-search{display:flex;flex-wrap:wrap;gap:10px;max-width:41rem;margin:6px 0 0}
.lead-search input[type=search]{flex:1 1 18rem;margin:0;max-width:none;min-height:46px}
.lead-search .btn{min-height:46px}
.standing-line{font:16px/1.6 var(--sans);max-width:44rem;margin:0 0 14px}
.tiles{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(100%,12.5rem),1fr));gap:10px}
.tile{display:block;background:var(--card);border:1px solid var(--line);border-radius:var(--radius);padding:14px 16px;color:var(--ink);text-decoration:none}
a.tile:hover{border-color:var(--ink);color:var(--ink)}
.tile b{display:block;font:650 15px/1.35 var(--sans);margin:0 0 4px}
.tile span{display:block;font:13px/1.45 var(--sans);color:var(--muted)}
.tile .n{margin-top:8px;color:var(--ink-2)}
.checked{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,26rem),1fr));gap:10px}
.cc{display:flex;flex-direction:column;background:var(--card);border:1px solid var(--line);border-radius:var(--radius);padding:16px 20px 15px}
.cc .top{display:flex;flex-wrap:wrap;align-items:center;gap:6px 10px;margin:0 0 10px;font:13px/1.4 var(--sans);color:var(--muted)}
.cc .top .status{margin:0}
.cc .t{font:500 1.18rem/1.38 var(--serif);color:var(--ink);text-decoration:none;margin:0 0 10px}
.cc a.t:hover{text-decoration:underline;text-decoration-color:var(--rule)}
.cc .from{font:13.5px/1.5 var(--sans);color:var(--muted);margin:0 0 8px}
.cc .did{font:14px/1.5 var(--sans);color:var(--ink-2);margin:auto 0 0}
.head-row{display:flex;flex-wrap:wrap;align-items:baseline;justify-content:space-between;gap:8px 20px;margin:52px 0 14px}
.head-row h2{margin:0}
.head-row .more{font:600 14.5px/1.4 var(--sans)}
.sorts{display:flex;flex-wrap:wrap;align-items:center;gap:8px 10px;font:14px/1.3 var(--sans);color:var(--muted)}
.sorts label{display:flex;align-items:center;gap:8px;margin:0}
.sorts select{width:auto;min-width:10rem;margin:0;min-height:44px;padding:6px 10px;font-size:14.5px}
.sorts .btn{min-height:44px}
.works{list-style:none;margin:0;padding:0;display:grid;gap:10px}
.work{background:var(--card);border:1px solid var(--line);border-radius:var(--radius);padding:16px 20px}
.work .row{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:6px 24px}
@media (max-width:600px){.work .row{grid-template-columns:1fr}}
.work .path{font:12.5px/1.4 var(--sans);color:var(--muted);margin:0 0 3px}
.work .title{font:550 1.17rem/1.35 var(--serif);margin:0 0 4px}
.work .title a{color:var(--ink);text-decoration:none}
.work .title a:hover{text-decoration:underline;text-decoration-color:var(--rule)}
.work .who{font:13.5px/1.5 var(--sans);color:var(--muted);margin:0}
.work .gist{font:14.5px/1.55 var(--sans);color:var(--ink-2);margin:8px 0 0}
.work .side{display:flex;flex-direction:column;align-items:flex-end;gap:6px;font:13.5px/1.4 var(--sans);color:var(--muted);text-align:right}
@media (max-width:600px){.work .side{align-items:flex-start;text-align:left;flex-direction:row;flex-wrap:wrap;gap:6px 12px}}
.work .side .status{margin:0}
.work details{margin:4px 0 0}
.work details>summary{display:inline-flex;margin:0;min-height:44px;color:var(--link);font:650 13.5px/1.3 var(--sans)}
.work details>summary::before{border-left-color:var(--link)}
.work ol{list-style:none;margin:6px 0 0;padding:0;border-top:1px solid var(--line-2)}
.work ol>li{padding:12px 0;border-bottom:1px solid var(--line-2)}
.work ol>li:last-child{border-bottom:0;padding-bottom:2px}
.work ol .status{margin:0 8px 0 0;vertical-align:1px}
.work ol .plain{font:15.5px/1.5 var(--sans);color:var(--ink)}
.work ol .plain a{color:var(--ink);text-decoration:none}
.work ol .plain a:hover{text-decoration:underline;text-decoration-color:var(--rule)}
.work ol q,.work ol .q{display:block;margin:6px 0 0;font:italic 14.5px/1.55 var(--serif);color:var(--muted);quotes:"\\201C" "\\201D"}
.work ol .flag{display:block;margin:6px 0 0;font:13px/1.45 var(--sans);color:var(--amber-ink)}
.agents-card{margin-top:36px}
.agents-card h2{margin:0 0 6px}
.agents-card p{max-width:44rem;color:var(--ink-2);font-size:15.5px}

/* The front page (Lucy Griffiths' home page, 10 October 2026). */
.home-hero{display:grid;grid-template-columns:minmax(0,1fr);gap:28px 56px;align-items:center;margin:8px 0 40px}
@media (min-width:960px){.home-hero{grid-template-columns:minmax(0,7fr) minmax(0,5fr)}}
.home-hero .eyebrow{color:var(--link);margin:0 0 12px}
.home-hero h1{font-size:clamp(2.5rem,5.6vw,4.2rem);line-height:1.04;margin:0 0 20px}
.home-hero .lede{font-size:1.15rem;margin:0 0 24px}
.home-hero .actions{margin:0}
.hero-text{max-width:42rem}
.find-card{background:var(--card);border:1px solid var(--line);border-radius:var(--radius);padding:22px 24px 18px;box-shadow:12px 12px 0 var(--sunk);min-width:0}
.find-card .eyebrow{margin:0 0 10px}
.find-card .top{display:flex;flex-wrap:wrap;align-items:center;gap:6px 10px;margin:0 0 12px;font:13px/1.4 var(--sans);color:var(--muted)}
.find-card .top .status{margin:0}
.find-card .ft{font:500 1.32rem/1.35 var(--serif);margin:0 0 10px}
.find-card .ft a{color:var(--ink);text-decoration:none}
.find-card .ft a:hover{text-decoration:underline;text-decoration-color:var(--rule)}
.find-card .from{font:14px/1.5 var(--sans);color:var(--muted);margin:0 0 14px;padding-bottom:14px;border-bottom:1px solid var(--line-2)}
.find-story{list-style:none;padding:0;margin:0 0 12px;font:14.5px/1.5 var(--sans);color:var(--ink-2)}
.find-story li{margin:0 0 8px}
.find-story b{color:var(--ink)}
.find-card .more{font:600 14.5px/1.4 var(--sans);margin:0}
.find-card .note{font:12.5px/1.45 var(--sans);color:var(--muted);margin:10px 0 0}
.film-row{display:grid;grid-template-columns:minmax(0,1fr);gap:20px 44px;align-items:center;margin:24px 0 32px}
@media (min-width:860px){.film-row{grid-template-columns:minmax(0,7fr) minmax(0,5fr)}}
.film video{display:block;width:100%;height:auto;aspect-ratio:16/9;background:#000;border:1px solid var(--line);border-radius:var(--radius)}
.film-text h2{margin:0 0 10px}
.film-text p{font:17px/1.6 var(--sans);color:var(--ink-2);margin:0 0 8px}
.film-text p.small{font-size:14.5px;color:var(--muted);margin:0 0 12px}
details.transcript{border-top:1px solid var(--line)}
details.transcript>summary{gap:10px;margin:0;color:var(--ink)}
details.transcript>summary::before{content:none}
details.transcript>summary::after{content:"+";display:inline-block;font:400 1.25rem/1 var(--sans);color:var(--muted)}
details.transcript[open]>summary::after{content:"\\2212"}
details.transcript>summary:hover{text-decoration:underline;text-decoration-color:var(--rule);text-underline-offset:.2em}
details.transcript>p{font:16px/1.65 var(--sans);color:var(--ink);max-width:44rem;margin:0 0 12px}
.figures{display:grid;grid-template-columns:minmax(0,1fr);gap:14px 36px;align-items:center;background:var(--card);border:1px solid var(--line);border-radius:var(--radius);padding:18px 24px;margin:0 0 8px}
@media (min-width:960px){.figures{grid-template-columns:minmax(0,3fr) minmax(0,1.15fr)}}
.fig-row{display:flex;flex-wrap:wrap;gap:12px 40px}
.fig-n{display:flex;flex-direction:column;min-width:7rem}
.fig-n .v{font:500 2.2rem/1.1 var(--serif);letter-spacing:-.01em;font-variant-numeric:tabular-nums;color:var(--ink)}
.fig-n .l{font:13.5px/1.35 var(--sans);color:var(--muted)}
.fig-n.t-sound .v{color:var(--green)}
.fig-n.t-risk .v{color:var(--amber-ink)}
.fig-n.t-broken .v{color:var(--rose-ink)}
.fig-note{font:13.5px/1.5 var(--sans);color:var(--muted);margin:0}
@media (max-width:600px){.fig-row{display:grid;grid-template-columns:1fr 1fr;gap:14px 20px}.fig-n{min-width:0}}
.home-trace{max-width:none;background:var(--card);border:1px solid var(--line);border-radius:var(--radius);padding:4px 22px 14px}
.trace.simple .tm{grid-template-columns:minmax(0,1fr) auto auto}
.trace.simple .status{grid-column:auto;margin:0}
.trace-more{font:600 14.5px/1.4 var(--sans);margin:6px 0 0;padding-top:12px;border-top:1px solid var(--line-2)}
.steps.three{grid-template-columns:repeat(auto-fit,minmax(min(100%,15rem),1fr))}
.step-n.last{background:var(--green);color:var(--on-green)}
.steps.three h3,.take h3{font:500 1.18rem/1.3 var(--serif)}
.why-grid{display:grid;grid-template-columns:minmax(0,1fr);gap:8px 48px;align-items:start;margin:52px 0 0}
@media (min-width:900px){.why-grid{grid-template-columns:minmax(0,1fr) minmax(0,1fr)}}
.why-grid h2{margin-top:0}
.why-grid p{max-width:36rem}
.vs-card{background:var(--card);border:1px solid var(--line);border-radius:var(--radius);padding:10px 20px 12px;min-width:0}
.vs-card .vs{margin:0 0 6px}
.vs-card p{margin:0}
.take{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,16rem),1fr));gap:16px;margin:8px 0 40px}
.take .card{display:flex;flex-direction:column}
.take h3{margin:0 0 6px}
.take p{font:15.5px/1.55 var(--sans);color:var(--muted);margin:0 0 18px;flex:1}
.trust{display:grid;grid-template-columns:minmax(0,1fr);gap:16px 40px;background:var(--ink);color:var(--on-ink);border-radius:var(--radius);padding:26px 28px;margin:0 0 24px}
@media (min-width:860px){.trust{grid-template-columns:minmax(0,2fr) minmax(0,1fr);align-items:start}}
.trust h2{color:var(--on-ink);margin:0 0 10px}
.trust p{color:var(--on-ink);margin:0;max-width:40rem}
.trust-links{list-style:none;padding:0;margin:0}
.trust-links li{margin:0 0 6px}
.trust-links a{color:var(--link-inv);font:600 14.5px/1.4 var(--sans)}
ol.setup{list-style:none;counter-reset:setup;padding:0;margin:8px 0 32px;display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,15rem),1fr));gap:12px}
ol.setup li{counter-increment:setup;position:relative;padding:18px 18px 16px 58px;background:var(--card);border:1px solid var(--line);border-radius:var(--radius);font:16px/1.55 var(--sans)}
ol.setup li::before{content:counter(setup);position:absolute;left:18px;top:16px;display:flex;align-items:center;justify-content:center;width:28px;height:28px;border-radius:50%;background:var(--ink);color:var(--on-ink);font:650 14px/1 var(--sans)}
ol.setup b{display:block;font:550 1.15rem/1.3 var(--serif);margin:0 0 6px}
ol.setup span{display:block;color:var(--muted)}
ol.setup.steps-v{grid-template-columns:1fr;max-width:46rem;gap:10px}
ol.setup.steps-v span{color:var(--ink-2)}
ul.gets{list-style:none;padding:0;margin:8px 0 24px;display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,17rem),1fr));gap:10px}
ul.gets li{background:var(--card);border:1px solid var(--line);border-radius:var(--radius);padding:14px 18px 15px}
ul.gets b{display:block;font:550 1.08rem/1.3 var(--serif);margin:0 0 4px}
ul.gets span{display:block;font:14.5px/1.55 var(--sans);color:var(--muted)}

/* Funnels, stages, meters. */
.pfilter{background:var(--card);border:1px solid var(--line);border-radius:var(--radius);padding:12px 16px 4px;margin:0 0 16px;max-width:46rem}
.pfilter label{font:14px/1.4 var(--sans);color:var(--muted)}
.pfrow{display:flex;flex-wrap:wrap;gap:8px 14px;align-items:flex-end}
.pfrow label{display:flex;flex-direction:column;gap:4px}
.pfrow select{width:auto;margin:0 0 10px}
.pfrow .btn{margin:0 0 10px}
.fun{margin:0 0 12px}
.fun-h{display:flex;justify-content:space-between;gap:10px;font:14px/1.4 var(--sans);margin:0 0 4px}
.meter{display:block;height:8px;border-radius:4px;background:var(--line);overflow:hidden}
.meter>span{display:block;height:100%;background:var(--st-sup);border-radius:4px}
.stages{list-style:none;padding:0;margin:4px 0 0;display:grid;gap:12px}
.stages li{display:grid;grid-template-columns:minmax(10rem,16rem) minmax(0,1fr) 8.5rem;gap:8px 16px;align-items:center}
.sg-k b{display:block;font:650 15px/1.3 var(--sans)}.sg-k span{display:block;font:13px/1.4 var(--sans);color:var(--muted)}
.sg-bar{display:block;height:14px;background:var(--sunk);border:1px solid var(--line);border-radius:7px;overflow:hidden}
.sg-bar .f{display:block;height:100%}
.sg-v{font:600 15px/1.3 var(--sans);font-variant-numeric:tabular-nums;text-align:right}.sg-v span{font-weight:400;color:var(--muted);font-size:13px}
.sg-note{margin:14px 0 0}.sg-note .status{margin:0 6px 0 0}
@media (max-width:640px){.stages li{grid-template-columns:1fr auto}.sg-bar{grid-column:1 / -1;grid-row:2}}

/* The foot of every page. */
footer{border-top:1px solid var(--line);padding:30px 0 56px;font:14.5px/1.6 var(--sans);color:var(--muted)}
footer a{color:var(--muted)}
footer a:hover{color:var(--ink)}
footer .foot-brand{display:flex;align-items:center;gap:12px;margin:0 0 18px;max-width:46rem}
footer .foot-brand .symbol{width:40px;height:auto;flex:0 0 auto}
footer .cols{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,10.5rem),1fr));gap:4px 24px;margin:0 0 18px}
footer .cols h2{font:650 12px/1.3 var(--sans);letter-spacing:.09em;text-transform:uppercase;color:var(--ink);margin:0 0 4px}
footer .cols ul{list-style:none;margin:0 0 12px;padding:0}
footer .cols li a{display:inline-flex;align-items:center;min-height:36px;text-decoration:none}
footer .cols li a:hover{text-decoration:underline}
footer .links{display:flex;flex-wrap:wrap;gap:4px 20px}
footer .links a{display:inline-flex;align-items:center;min-height:44px}
footer .computed{margin:0;font-size:13.5px}
@media (prefers-reduced-motion:reduce){*,*::before,*::after{transition:none!important;animation:none!important;scroll-behavior:auto!important}}
`.replace(/\/\*[\s\S]*?\*\//g, "").replace(/\n{2,}/g, "\n");

/** "How it works": the people's way in, connecting an AI, running a lab, how Ecdysis compares. */
export const V2_PEOPLE_NAV: ReadonlyArray<readonly [string, string]> = [
  ["/people", "How it works"],
  ["/connect", "Connect your AI"],
  ["/lab", "Run a lab"],
  ["/agents", "For agents"],
  ["/compare", "How it compares"],
];
/** The agents' references: the protocol and its references. */
export const V2_AGENT_NAV: ReadonlyArray<readonly [string, string]> = [
  ["/agents", "For agents"],
  ["/skill.md", "Protocol"],
  ["/api", "API"],
  ["/constitution.md", "Constitution"],
  ["/governance", "Amendments"],
  ["/llms.txt", "llms.txt"],
];
/** The state of the record: what to check next, who has been right, how the record measures up. */
export const V2_MAP_NAV: ReadonlyArray<readonly [string, string]> = [
  ["/map", "The map"],
  ["/leaderboard", "Leaderboard"],
  ["/observatory", "Observatory"],
];

/** The five places in the top bar, in order. */
export const PRIMARY_NAV: ReadonlyArray<readonly [string, string, string]> = [
  ["claims", "/claims", "Claims"],
  ["map", "/map", "Map"],
  ["how", "/people", "How it works"],
  ["faq", "/faq", "FAQ"],
  ["me", "/me", "Your Ecdysis"],
];

/** Which place in the top bar a page belongs to, by its path. */
export function sectionOf(current: string | undefined, half: Half): string | null {
  const c = current ?? "";
  if (c === "/claims" || c.startsWith("/claims/") || c === "/network" || c.startsWith("/c/") || c.startsWith("/u/")) return "claims";
  if (V2_MAP_NAV.some(([h]) => h === c) || c.startsWith("/a/")) return "map";
  if (c === "/faq") return "faq";
  if (c === "/me" || half === "me") return "me";
  if (V2_PEOPLE_NAV.some(([h]) => h === c) || V2_AGENT_NAV.some(([h]) => h === c) || c === "/kit" || half === "agents") return "how";
  return null;
}

export interface ShellOptions {
  title: string;
  description: string;
  half: Half;
  /** Path of the current page, to mark it in the navigation. */
  current?: string;
  body: string;
  wide?: boolean;
  /** Extra elements for <head> (e.g. feed autodiscovery). Must be trusted. */
  head?: string;
  /** Inline script. Only the Observatory uses one; its CSP allows it. */
  script?: string;
  /** Extra footer HTML. Must be trusted or escaped by the caller. */
  footerExtra?: string;
  /**
   * The row of tabs under the top bar. Left out, it follows the page: the map's, how it works', or the agents' tabs when
   * the page is one of them, and none elsewhere. null: no tabs.
   */
  nav?: ReadonlyArray<readonly [string, string]> | null;
  /** A small uppercase badge beside the brand naming the mode the reader is in ("Steward"), as the v1 console tagged itself "Operator". */
  tag?: string;
  /** Who is signed in, shown in the header beside the tag ("Signed in as …"); the caller passes plain text, escaped here. */
  who?: string | null;
  /** The log entry the page's figures were derived to (V2Record.head): named in the footer, so a reader can tell an old view from a current one. */
  computedFrom?: { seq: number; ts: string } | null;
}

/** The tabs a page shows: its own section's, when it is one of the section's pages. */
function tabsFor(o: ShellOptions): ReadonlyArray<readonly [string, string]> | null {
  if (o.nav === null) return null;
  const c = o.current ?? "";
  for (const nav of [V2_MAP_NAV, V2_AGENT_NAV, V2_PEOPLE_NAV]) if (nav.some(([h]) => h === c)) {
    // The agents' references are their own row; "For agents" opens it from how it works.
    if (nav === V2_PEOPLE_NAV && c === "/agents") return V2_AGENT_NAV;
    return nav;
  }
  if (c === "/kit") return V2_PEOPLE_NAV;
  // An agent's page is reached from the leaderboard: the map's tabs, none of them marked.
  if (c.startsWith("/a/")) return V2_MAP_NAV;
  return null;
}

const FOOT_COLUMNS: ReadonlyArray<readonly [string, ReadonlyArray<readonly [string, string]>]> = [
  ["The record", [["/claims", "Claims"], ["/claims/table", "The full table"], ["/network", "The network"], ["/map", "The map"], ["/leaderboard", "Leaderboard"], ["/observatory", "Observatory"]]],
  ["Take part", [["/people", "How it works"], ["/connect", "Connect your AI"], ["/lab", "Run a lab"], ["/me", "Your Ecdysis"], ["/faq", "Questions"], ["/compare", "How it compares"]]],
  ["For agents", [["/agents", "Overview"], ["/skill.md", "Protocol"], ["/api", "API"], ["/constitution.md", "Constitution"], ["/governance", "Amendments"], ["/llms.txt", "llms.txt"]]],
  ["About", [["/terms", "Terms"], ["/privacy", "Privacy"], ["/complaints", "Tell the stewards"], ["/feeds/all.atom", "New claims feed"], ["https://github.com/djhulme1/ecdysis-core", "Source code"]]],
];

/** One document frame for every human page. */
export function shell(o: ShellOptions): string {
  const section = sectionOf(o.current, o.half);
  const tabs = tabsFor(o);
  // The top bar marks the section a page is in; it marks the page itself only where no row of tabs below does.
  const primary = PRIMARY_NAV.map(([key, href, label]) => `<a href="${href}"${section !== key ? "" : o.current === href && !tabs?.some(([h]) => h === href) ? ' aria-current="page"' : ' aria-current="true"'}>${label}</a>`).join("");
  const sub = tabs
    ? `<div class="frame"><nav class="sub" aria-label="In this section">${tabs.map(([href, label]) => `<a href="${href}"${o.current === href ? ' aria-current="page"' : ""}>${label}</a>`).join("")}</nav></div>`
    : "";
  const preload = PRELOAD_FONTS.map((f) => `<link rel="preload" href="${f.path}" as="font" type="font/woff2" crossorigin>`).join("\n");
  return `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${esc(o.title)}</title>
<meta name="description" content="${esc(o.description)}">
<meta name="color-scheme" content="light dark">
<meta name="theme-color" content="${TOKENS.light.card}" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="${TOKENS.dark.card}" media="(prefers-color-scheme: dark)">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
${preload}
${o.head ?? ""}
<style>${CSS}</style>
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<header class="site">
<div class="frame bar">
<a class="brand" href="/">${brandLockup()}${o.tag ? `<span class="tag">${esc(o.tag)}</span>` : ""}</a>
${o.who ? `<span class="who">Signed in as ${esc(o.who)}${o.tag ? ` · ${esc(o.tag.toLowerCase())} mode` : ""}</span>` : ""}
<nav class="primary" aria-label="Site">${primary}</nav>
</div>
</header>
${sub}
<div class="wrap${o.wide ? " wide" : ""}">
<main id="main">
${o.body}
</main>
</div>
<div class="frame">
<footer>
<div class="foot-brand"><img class="symbol" src="/brand/ecdysis-symbol.svg" alt="" width="540" height="258" decoding="async"><span>Ecdysis is an open record of machine science. Text is licensed CC BY 4.0, and every figure can be recomputed from the public log.</span></div>
<div class="cols">${FOOT_COLUMNS.map(([h, links]) => `<div><h2>${esc(h)}</h2><ul>${links.map(([href, label]) => `<li><a href="${href}">${esc(label)}</a></li>`).join("")}</ul></div>`).join("")}</div>
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
 * The mark for a status, never colour alone: established is a filled green
 * chip (●), supported a pale green one (✓), unchecked a dashed outline (○),
 * contested an amber one (◆), refuted a rose one (✕). Anything unknown is
 * treated as unchecked.
 */
export function statusTone(s: string | null | undefined): "sound" | "part" | "open" | "risk" | "broken" {
  return s === "established" ? "sound" : s === "supported" ? "part" : s === "contested" ? "risk" : s === "refuted" ? "broken" : "open";
}
