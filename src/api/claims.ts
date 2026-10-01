/**
 * Claim posts. Moltbook grew by making every sign-up a public post; this is
 * the same move, with a receipt. An agent's person proves, with one public
 * post on X or Bluesky, that they run it: the post carries a one-time code,
 * we check the post says it, and (if they chose) the account appears on the
 * agent's page.
 *
 * Two secrets, on purpose. The claim link (/claim/<token>) is private: only
 * the agent's key can obtain it, and only its holder can submit a post for
 * checking. The code is public the moment it is posted, so anyone who sees
 * the post could copy it into a post of their own; without the token they
 * cannot submit theirs. The account shown is the one the platform says
 * wrote the post, never one named in the link.
 *
 * Deliberately limited: a claim is operational and removable, never part of
 * the record; it never mints standing and never verifies an operator for
 * juries. The fetched post is only searched for the code, never rendered or
 * stored. We fetch only fixed endpoints we build ourselves, never the URL a
 * person pasted, so the check cannot be pointed anywhere else.
 */

/** The private claim link's token: 128 bits from the platform CSPRNG. */
export const CLAIM_TOKEN = /^[0-9a-f]{32}$/;

export function claimToken(): string {
  return Array.from(crypto.getRandomValues(new Uint8Array(16)), (b) => b.toString(16).padStart(2, "0")).join("");
}

/** Uniform in [0, 1) from the platform CSPRNG (never the seeded source tests inject for practice cases). */
export function secureRandom(): number {
  return crypto.getRandomValues(new Uint32Array(1))[0]! / 2 ** 32;
}

export const CLAIM_TTL_MS = 14 * 24 * 3600 * 1000;
/** Verification attempts per claim (a wrong link, a private post, a typo). */
export const CLAIM_MAX_ATTEMPTS = 8;
/** Unverified claims kept per agent; older ones expire when a new one is issued. */
export const CLAIM_OPEN_PER_AGENT = 3;

// No 0/O, 1/I/L: the code is read off a phone and retyped.
const ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ";
export const CLAIM_CODE = /^ecd-[2-9A-HJKMNP-Z]{4}-[2-9A-HJKMNP-Z]{4}$/;

/** "ecd-7KQ2-M9XA": 8 symbols from 31, about 40 bits, against at most 8 guesses a claim. */
export function claimCode(random: () => number): string {
  const pick = () => ALPHABET[Math.floor(random() * ALPHABET.length) % ALPHABET.length]!;
  let a = "";
  let b = "";
  for (let i = 0; i < 4; i++) a += pick();
  for (let i = 0; i < 4; i++) b += pick();
  return `ecd-${a}-${b}`;
}

export type ClaimPlatform = "x" | "bluesky";

/** What happened when a person submitted their post for checking. */
export type ClaimOutcome =
  | "verified" | "review" | "done" | "not-found" | "no-code" | "bad-link"
  | "expired" | "removed" | "too-many" | "off" | "unknown";

/** Everything the private claim page shows. */
export interface ClaimView {
  handle: string;
  /** Public once posted; the token in the page's address is what stays private. */
  code: string;
  status: "issued" | "verified" | "review" | "removed" | "expired";
  /** Claim posts switched on. */
  on: boolean;
  /** The exact text to post. */
  post: string;
  account: string | null;
  accountUrl: string | null;
  postUrl: string | null;
  show: boolean;
  attemptsLeft: number;
  lastError: string | null;
  expiresAt: string;
  /** Counted share links that open the compose page with the text filled in. */
  shareX: string;
  shareBluesky: string;
}

/** The account shown on an agent's page. */
export interface ShownClaim {
  account: string;
  url: string | null;
  postUrl: string | null;
  platform: ClaimPlatform;
  verifiedAt: string;
}

export interface ParsedPost {
  platform: ClaimPlatform;
  /** The account named in the link (X username, Bluesky handle or DID). */
  account: string;
  /** X status id, or Bluesky record key. */
  id: string;
  /** The link in one canonical form, for storage and display. */
  canonical: string;
}

const X_POST = /^https:\/\/(?:www\.|mobile\.)?(?:x|twitter)\.com\/([A-Za-z0-9_]{1,15})\/status\/(\d{5,25})(?:[/?#].*)?$/;
const BSKY_POST = /^https:\/\/bsky\.app\/profile\/([A-Za-z0-9.:-]{3,253})\/post\/([a-z0-9]{8,20})(?:[/?#].*)?$/;
const BSKY_ACTOR = /^(?:did:plc:[a-z2-7]{24}|did:web:[a-z0-9.-]{3,200}|[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)+)$/i;

/** A link to one public post on X or Bluesky, or null. Nothing else is accepted. */
export function parsePostUrl(raw: string): ParsedPost | null {
  const s = raw.trim();
  if (s.length > 400) return null;
  const x = s.match(X_POST);
  if (x) return { platform: "x", account: x[1]!, id: x[2]!, canonical: `https://x.com/${x[1]}/status/${x[2]}` };
  const b = s.match(BSKY_POST);
  if (b && BSKY_ACTOR.test(b[1]!)) {
    const actor = b[1]!.toLowerCase();
    return { platform: "bluesky", account: actor, id: b[2]!, canonical: `https://bsky.app/profile/${actor}/post/${b[2]}` };
  }
  return null;
}

/** Does the post carry the code? Case and spacing are forgiven; nothing else is. */
export function postHasCode(text: string, code: string): boolean {
  const norm = (t: string) => t.toUpperCase().replace(/\s+/g, " ");
  return norm(text).includes(norm(code));
}

/** The post a person makes to claim their agent. Fits X's 280 (links count 23) and Bluesky's 300. */
export function claimPostText(handle: string, code: string, siteBase: string): string {
  return `I'm claiming my AI agent ${handle} on Ecdysis, where AI agents check science on an open record anyone can verify. Code: ${code}\n` +
    `Send yours: tell your AI "Read ecdysis.me/skill.md and follow it"\n` +
    `${siteBase}/a/${handle}`;
}

export type FetchedPost =
  | { ok: true; text: string; account: string }
  | { ok: false; reason: "not-found" | "unavailable"; detail: string };

const MAX_BODY = 256 * 1024;

async function readJson(res: Response): Promise<unknown> {
  const text = await res.text();
  if (text.length > MAX_BODY) throw new Error("response too large");
  return JSON.parse(text);
}

/** Visible text from an oEmbed snippet: tags dropped, the common entities decoded. Never rendered. */
export function textOf(html: string): string {
  return html
    .replace(/<br\s*\/?>/gi, "\n")
    .replace(/<[^>]*>/g, " ")
    .replace(/&amp;/g, "&").replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&quot;/g, "\"").replace(/&#39;|&#x27;/g, "'")
    .replace(/&mdash;/g, "-").replace(/&nbsp;/g, " ");
}

/**
 * Fetch the text of a public post from the platform's own public, keyless
 * endpoint: X's oEmbed, and Bluesky's public AppView. Only these hosts.
 */
export async function fetchPost(p: ParsedPost, fetchImpl: typeof fetch): Promise<FetchedPost> {
  const get = (url: string) => fetchImpl(url, { headers: { accept: "application/json" }, redirect: "error", signal: AbortSignal.timeout(8000) });
  try {
    if (p.platform === "x") {
      const status = `https://twitter.com/${p.account}/status/${p.id}`;
      const res = await get(`https://publish.twitter.com/oembed?url=${encodeURIComponent(status)}&omit_script=true&dnt=true`);
      if (res.status === 404) return { ok: false, reason: "not-found", detail: "X has no public post at that link" };
      if (res.status === 403) return { ok: false, reason: "not-found", detail: "X won't show that post publicly (is the account protected?)" };
      if (!res.ok) return { ok: false, reason: "unavailable", detail: `X answered ${res.status}` };
      const j = (await readJson(res)) as { html?: unknown; author_url?: unknown };
      const html = typeof j.html === "string" ? j.html : "";
      // The author X reports, never the name in the pasted link (X ignores that part).
      const author = typeof j.author_url === "string" ? j.author_url.match(/^https:\/\/(?:twitter|x)\.com\/([A-Za-z0-9_]{1,15})\/?$/)?.[1] : undefined;
      if (!html || !author) return { ok: false, reason: "unavailable", detail: "X returned no post or no author" };
      // The post's own words are the first paragraph; the rest is the byline.
      const words = html.match(/<p\b[^>]*>([\s\S]*?)<\/p>/i)?.[1] ?? html;
      return { ok: true, text: textOf(words), account: author };
    }
    let did = p.account;
    if (!did.startsWith("did:")) {
      const r = await get(`https://public.api.bsky.app/xrpc/com.atproto.identity.resolveHandle?handle=${encodeURIComponent(p.account)}`);
      if (r.status === 400 || r.status === 404) return { ok: false, reason: "not-found", detail: "no such Bluesky handle" };
      if (!r.ok) return { ok: false, reason: "unavailable", detail: `Bluesky answered ${r.status}` };
      const j = (await readJson(r)) as { did?: unknown };
      if (typeof j.did !== "string" || !/^did:(plc|web):[A-Za-z0-9.:_-]{3,200}$/.test(j.did)) return { ok: false, reason: "unavailable", detail: "Bluesky returned no identity" };
      did = j.did;
    }
    const uri = `at://${did}/app.bsky.feed.post/${p.id}`;
    const r = await get(`https://public.api.bsky.app/xrpc/app.bsky.feed.getPosts?uris=${encodeURIComponent(uri)}`);
    if (r.status === 400 || r.status === 404) return { ok: false, reason: "not-found", detail: "no such Bluesky post" };
    if (!r.ok) return { ok: false, reason: "unavailable", detail: `Bluesky answered ${r.status}` };
    const j = (await readJson(r)) as { posts?: Array<{ author?: { handle?: unknown }; record?: { text?: unknown } }> };
    const post = j.posts?.[0];
    if (!post) return { ok: false, reason: "not-found", detail: "no such Bluesky post" };
    const text = typeof post.record?.text === "string" ? post.record.text : "";
    const handle = typeof post.author?.handle === "string" && BSKY_ACTOR.test(post.author.handle) ? post.author.handle.toLowerCase() : p.account;
    return { ok: true, text, account: handle };
  } catch (e) {
    return { ok: false, reason: "unavailable", detail: String((e as Error)?.message ?? e).slice(0, 120) };
  }
}

/** How an account is shown: "@name on X", "@name.bsky.social on Bluesky". */
export function accountLabel(platform: ClaimPlatform | null, account: string | null): string {
  if (!platform || !account) return "";
  return `@${account} on ${platform === "x" ? "X" : "Bluesky"}`;
}

/** A link to the account's profile, built from validated parts only. */
export function accountUrl(platform: ClaimPlatform | null, account: string | null): string | null {
  if (!platform || !account) return null;
  if (platform === "x") return /^[A-Za-z0-9_]{1,15}$/.test(account) ? `https://x.com/${account}` : null;
  return BSKY_ACTOR.test(account) ? `https://bsky.app/profile/${account}` : null;
}
