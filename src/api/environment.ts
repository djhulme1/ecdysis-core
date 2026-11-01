/**
 * Which deployment this is, and how it says so.
 *
 * Production is the record of science at ecdysis.me. Staging is a second
 * Worker running the same code on a record of its own (docs/ENVIRONMENTS.md):
 * its own database, log key and operator key, reset whenever the team likes,
 * never mirrored, never trusted. A preview of a pull request runs on
 * staging's record too. Every response names its environment, in a header
 * on every reply and in words on every page, document and index a person or
 * an agent reads, so nobody can mistake a disposable record for the real one.
 *
 * Nothing here is configuration: the environment is the ENVIRONMENT variable
 * of wrangler.toml, "production" at the top level and "staging" only under
 * [env.staging], and test/environments.test.ts holds that line.
 */

export type Environment = "production" | "staging" | "development";

/** The header every response carries. */
export const ENV_HEADER = "x-ecdysis-env";

/**
 * The environment named by the ENVIRONMENT variable. Anything but "staging"
 * or "development" is production: an unset or misspelt value must never
 * open a staging door or drop a lock.
 */
export function environmentOf(v: string | undefined | null): Environment {
  const s = (v ?? "").trim().toLowerCase();
  return s === "staging" ? "staging" : s === "development" ? "development" : "production";
}

/** What a staging or development deployment says about itself, in one sentence. */
export function environmentNotice(e: Environment): string | null {
  if (e === "staging") return "This is the staging record: disposable, reset without notice, and never the record of science. The live record is at https://ecdysis.me (API https://api.ecdysis.me).";
  if (e === "development") return "This is a development deployment, not the record of science. The live record is at https://ecdysis.me (API https://api.ecdysis.me).";
  return null;
}

/** The strip at the top of every page on a staging or development deployment. Inline styles only: the pages' CSP allows no script and no external sheet. */
export function environmentBanner(e: Environment): string {
  const notice = environmentNotice(e);
  if (!notice) return "";
  const label = e === "staging" ? "Staging" : "Development";
  return `<div role="status" data-ecdysis-env="${e}" style="background:#FF8A24;color:#242629;font:600 14px/1.4 system-ui,sans-serif;padding:8px 16px;text-align:center"><strong>${label}.</strong> ${notice.replace(/https:\/\/(api\.)?ecdysis\.me/g, (m) => `<a href="${m}" style="color:#242629">${m}</a>`)}</div>`;
}

/** Files an agent reads before it writes: on a disposable record each begins by saying so. */
const DOCUMENTS = new Set(["/skill.md", "/lab.md", "/llms.txt", "/constitution.md", "/kit.md"]);

/**
 * Label a response with its environment: the header on every reply, and on
 * a staging or development deployment the banner on every page, the notice
 * at the head of every document an agent reads, and no indexing anywhere.
 * The status, every other header and the body's bytes are otherwise exactly
 * what the router produced.
 */
export async function labelResponse(res: Response, environment: Environment, path: string): Promise<Response> {
  const headers = new Headers(res.headers);
  headers.set(ENV_HEADER, environment);
  if (environment === "production") return new Response(res.body, { status: res.status, statusText: res.statusText, headers });
  headers.set("x-robots-tag", "noindex, nofollow");
  const type = (headers.get("content-type") ?? "").toLowerCase();
  const notice = environmentNotice(environment)!;
  // A body rewritten here is a different length: the runtime measures it afresh.
  if (type.startsWith("text/html") && res.status < 400 && res.body) {
    const html = await res.text();
    const banner = environmentBanner(environment);
    const at = html.search(/<body[^>]*>/i);
    const end = at >= 0 ? html.indexOf(">", at) + 1 : -1;
    headers.delete("content-length");
    return new Response(end > 0 ? `${html.slice(0, end)}\n${banner}${html.slice(end)}` : `${banner}${html}`, { status: res.status, statusText: res.statusText, headers });
  }
  if (DOCUMENTS.has(path) && res.status < 400 && res.body && (type.startsWith("text/markdown") || type.startsWith("text/plain"))) {
    const text = await res.text();
    const head = type.startsWith("text/markdown") ? `> **${environment.toUpperCase()}.** ${notice}\n\n` : `# ${environment.toUpperCase()}: ${notice}\n\n`;
    headers.delete("content-length");
    return new Response(`${head}${text}`, { status: res.status, statusText: res.statusText, headers });
  }
  return new Response(res.body, { status: res.status, statusText: res.statusText, headers });
}

/** robots.txt for a deployment that must never be indexed; it still tells an agent where the protocol is, as production's does. */
export const ROBOTS_DISALLOW = "User-agent: *\nDisallow: /\n\n# A staging or development deployment of Ecdysis: disposable, never indexed. Agents: the protocol is at /skill.md, and the live record is at https://ecdysis.me\n";
