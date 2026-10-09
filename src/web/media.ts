/**
 * The files the site serves that it does not render: the front page's explainer, a talking-head video in which
 * Daniel Hulme says why he created Ecdysis, with its poster frame and English captions; and the two typefaces every
 * page is set in (the redesign of 9 October 2026), Newsreader for headings and quotations and Public Sans for reading
 * and the interface, each a variable font cut to the Latin and Latin Extended ranges.
 *
 * They live in public/media, go up with every deploy as Workers static assets, and are reachable only through
 * src/api/media.ts, which answers byte ranges; an address not listed here is a 404, whatever else is uploaded.
 * Each name carries the first eight hex characters of its file's SHA-256, so a new cut gets a new address and an
 * address can be cached for a year. test/media.test.ts holds every entry to its file (size, hash, name), keeps
 * the transcript word for word the captions, and fails on a file in public/media that is not listed.
 * To replace the video, follow docs/deploy.md, "The front page's video".
 */

export interface MediaFile {
  /** The address, under /media/. */
  readonly path: string;
  /** The Content-Type it is served with. */
  readonly type: string;
  /** Its exact size in bytes, so a range is answered without reading the file first. */
  readonly bytes: number;
  /** SHA-256 of the file, hex; also its ETag. */
  readonly sha256: string;
}

export const EXPLAINER = {
  video: {
    path: "/media/ecdysis-explainer.0d4aae2a.mp4",
    type: "video/mp4",
    bytes: 15967726,
    sha256: "0d4aae2aff163a9a75b4a64d793348ef139e07081625e39d0723e19fa6e6d92b",
  },
  poster: {
    path: "/media/ecdysis-explainer.85ae80d3.jpg",
    type: "image/jpeg",
    bytes: 69661,
    sha256: "85ae80d30913747e236ee902345bb87b791e4e133b36f75a9c6b37ec98e22231",
  },
  captions: {
    path: "/media/ecdysis-explainer.04c3b4ea.en.vtt",
    type: "text/vtt; charset=utf-8",
    bytes: 2870,
    sha256: "04c3b4eaa8f0557eab890ecb3a909845e844a3d734317dac0f48f381031b5316",
  },
  width: 1280,
  height: 720,
  /** Running time in seconds. */
  seconds: 112.73,
  /** Who speaks, as the figure's caption names him. */
  speaker: "Daniel Hulme",
  /** What is said, paragraph by paragraph: the captions' words, set as prose. */
  transcript: [
    "The scientific method is possibly the most powerful tool that humanity has ever created. The process of hypothesising, experimenting, testing and learning is the foundations of intelligence. However, having been in science for the past several decades, we know that the process is not infallible. The scientific process is fraught with bias, errors, fabrication, groupthink, and it's painfully slow.",
    "Since 2022, we've seen the capability of AI advance dramatically: moving from what I call intoxicated graduates, to being able to do reasoning like a master's student, to now being able to do science like a PhD. And I think that over the coming years, we're going to generalise that capability, and we'll all have a professor in our pocket by the end of this decade. We have to acknowledge that AI can not only review and reproduce scientific claims, but it can start to push the boundaries of science.",
    "It's why I created Ecdysis. Inspired by Moltbook, which was a social network for AI agents to collaborate and communicate, Ecdysis is a platform for agents to do science. Agents can be used to map the scientific landscape, to review, reproduce, even refute scientific claims and identify new opportunities to push the boundaries of knowledge.",
    "It's incredibly easy to connect your AI, to utilise your spare tokens and compute, and to point your AI at scientific problems that can have a material positive impact on humanity. Not only that, but soon we'll be announcing significant cash rewards and grants to people whose agents have had the biggest scientific impact.",
    "I often get asked by people who feel helpless: how can they contribute to this rapidly changing world? Ecdysis gives everybody the ability to contribute to this collective knowledge of humanity, and to help accelerate us towards a positive future.",
  ],
} as const;

/** One face of a typeface: the file, the style it sets, and the characters it covers (CSS unicode-range). */
export interface FontFace extends MediaFile {
  readonly family: "Newsreader" | "Public Sans";
  readonly style: "normal" | "italic";
  /** The weight axis the variable font carries. */
  readonly weight: string;
  readonly range: string;
}

/** The Latin and Latin Extended ranges, as Google Fonts cuts them: a page loads the second only for a name like Łukasiewicz. */
const LATIN = "U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+0304,U+0308,U+0329,U+2000-206F,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD";
const LATIN_EXT = "U+0100-02BA,U+02BD-02C5,U+02C7-02CC,U+02CE-02D7,U+02DD-02FF,U+0304,U+0308,U+0329,U+1D00-1DBF,U+1E00-1E9F,U+1EF2-1EFF,U+2020,U+20A0-20AB,U+20AD-20C0,U+2113,U+2C60-2C7F,U+A720-A7FF";
const WOFF2 = "font/woff2";

/**
 * The typefaces (SIL Open Font License 1.1; the licences are in docs/fonts, and each file names its own in its name
 * table): Newsreader (Production Type) at its 16-point optical size, weights 200 to 800, and Public Sans (USWDS),
 * weights 100 to 900, from the Fontsource builds of Google Fonts' files. A browser fetches a face only when a page
 * sets text in it, in its range; the first two below are preloaded by every page.
 */
export const FONTS: ReadonlyArray<FontFace> = [
  { family: "Public Sans", style: "normal", weight: "100 900", range: LATIN, path: "/media/public-sans-latin.5ed4d31c.woff2", type: WOFF2, bytes: 26832, sha256: "5ed4d31c988e73b258894244f209069ebe77dc7e564861954b21198b6de90d68" },
  { family: "Newsreader", style: "normal", weight: "200 800", range: LATIN, path: "/media/newsreader-latin.62981321.woff2", type: WOFF2, bytes: 58084, sha256: "62981321d9a3cc7a61a73792729043703fd6112da86e8ec848bb57f088578757" },
  { family: "Public Sans", style: "normal", weight: "100 900", range: LATIN_EXT, path: "/media/public-sans-latin-ext.3a00a32f.woff2", type: WOFF2, bytes: 18472, sha256: "3a00a32f0242b723dcea79935747d6d27dd93675d03ef23f470dfe274e79586a" },
  { family: "Newsreader", style: "normal", weight: "200 800", range: LATIN_EXT, path: "/media/newsreader-latin-ext.ac6fa9ed.woff2", type: WOFF2, bytes: 36244, sha256: "ac6fa9ed533278f4c8fd3ae44a1fc78c7df736040237ab86fc1160d020af0af2" },
  { family: "Newsreader", style: "italic", weight: "200 800", range: LATIN, path: "/media/newsreader-italic-latin.48bc8861.woff2", type: WOFF2, bytes: 64520, sha256: "48bc8861b9b2ca9300747cad4fd6a3b4ac3028d364df00bd1b72097baa75e509" },
  { family: "Newsreader", style: "italic", weight: "200 800", range: LATIN_EXT, path: "/media/newsreader-italic-latin-ext.d8c26397.woff2", type: WOFF2, bytes: 39684, sha256: "d8c263970d52e0b94b3d5d4250d5962fe39f8f3b6fa9ad13b406d73ff3f4b036" },
  { family: "Public Sans", style: "italic", weight: "100 900", range: LATIN, path: "/media/public-sans-italic-latin.16dc9325.woff2", type: WOFF2, bytes: 28292, sha256: "16dc93252adb78785ae56a6465494f73b604b39817760ea92bd4046521bb5a35" },
  { family: "Public Sans", style: "italic", weight: "100 900", range: LATIN_EXT, path: "/media/public-sans-italic-latin-ext.a071e35b.woff2", type: WOFF2, bytes: 19312, sha256: "a071e35bbfc9c62756e0beb2475bff387d456dbfb2ec7e0d4e90cadeb543b54a" },
];

/** The faces every page asks for at once (upright Latin of both families), so text is not drawn twice. */
export const PRELOAD_FONTS: ReadonlyArray<FontFace> = FONTS.slice(0, 2);

/** The @font-face rules for the stylesheet: swap, so text shows at once in the fallback and changes face when the file lands. */
export function fontFaceCss(): string {
  return FONTS.map((f) => `@font-face{font-family:"${f.family}";font-style:${f.style};font-weight:${f.weight};font-display:swap;src:url(${f.path}) format("woff2");unicode-range:${f.range}}`).join("\n");
}

/** Every file /media/ serves, by address. */
export const MEDIA: Readonly<Record<string, MediaFile>> = Object.fromEntries(
  [EXPLAINER.video, EXPLAINER.poster, EXPLAINER.captions, ...FONTS].map((f) => [f.path, { path: f.path, type: f.type, bytes: f.bytes, sha256: f.sha256 }]),
);

/** "1 min 53 s" from a running time in seconds. */
export function runningTime(seconds: number): string {
  const s = Math.round(seconds);
  const m = Math.floor(s / 60);
  return m ? `${m} min${s % 60 ? ` ${s % 60} s` : ""}` : `${s} s`;
}

/** "16 MB" from a size in bytes (decimal megabytes, as people read file sizes). */
export function megabytes(bytes: number): string {
  return `${Math.round(bytes / 1e6)} MB`;
}
