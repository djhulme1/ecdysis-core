/**
 * Live badges: Shields-style SVGs served by the Worker itself, for READMEs
 * and bios. Every embedded badge is a live, verifiable backlink into the
 * record. Every value is escaped.
 */

export function escapeXml(s: string): string {
  return s.replace(/[<>&"']/g, (c) =>
    c === "<" ? "&lt;" : c === ">" ? "&gt;" : c === "&" ? "&amp;" : c === '"' ? "&quot;" : "&#39;");
}

export function badgeSvg(label: string, value: string, color = "#0B6E78"): string {
  const l = escapeXml(label);
  const v = escapeXml(value);
  const lw = Math.round(label.length * 6.3 + 20);
  const vw = Math.round(value.length * 6.3 + 20);
  const w = lw + vw;
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="20" role="img" aria-label="${l}: ${v}">
<linearGradient id="s" x2="0" y2="100%"><stop offset="0" stop-color="#fff" stop-opacity=".1"/><stop offset="1" stop-opacity=".1"/></linearGradient>
<clipPath id="r"><rect width="${w}" height="20" rx="3" fill="#fff"/></clipPath>
<g clip-path="url(#r)">
<rect width="${lw}" height="20" fill="#3a4441"/>
<rect x="${lw}" width="${vw}" height="20" fill="${color}"/>
<rect width="${w}" height="20" fill="url(#s)"/>
</g>
<g fill="#fff" text-anchor="middle" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" font-size="11">
<text x="${lw / 2}" y="14" fill="#010101" fill-opacity=".3">${l}</text><text x="${lw / 2}" y="13">${l}</text>
<text x="${lw + vw / 2}" y="14" fill="#010101" fill-opacity=".3">${v}</text><text x="${lw + vw / 2}" y="13">${v}</text>
</g>
</svg>`;
}

/** Pages that are a person's own or a steward's: no crawler and no agent reads them. `/me$` and `/me/` rather than `/me`, which matched /media/ too. */
const PRIVATE_PATHS = ["/me$", "/me/", "/steward", "/s/", "/o/", "/doorbell/"];

/**
 * The lists' filtered, sorted and paged views, and the network around each claim. Each is built from the whole record
 * on every request, so they are the archive's dearest pages, and crawlers walking every combination of them knocked the
 * site over (21 to 22 October 2026). They hold nothing the sitemap's claim pages do not.
 */
export const CRAWLER_HEAVY_VIEWS = ["/claims?", "/claims/table?", "/network?"] as const;

/** Agents fetching a page because a person asked them to, not crawling: they may read everything that is not private. */
export const FOR_A_PERSON = ["Claude-User", "ChatGPT-User", "Perplexity-User"] as const;

/** What a crawler may read on the API host: the agents' guides and the descriptions of the API. */
const API_FILES = ["/skill.md", "/llms.txt", "/lab.md", "/openapi.json", "/.well-known/"];

/**
 * robots.txt (RFC 9309) for the host it is asked on. On the website, crawlers may read every page but the private ones
 * and the heavy views. The API host serves the website's pages too, so a crawler there would read everything twice: it
 * reads only the guides and is pointed at the website's sitemap. On both, an agent fetching for a person keeps the
 * whole site but the private pages.
 */
export function robotsTxt(site: string, api = false): string {
  const lines = (rules: string[]) => rules.map((r) => `${r}\n`).join("");
  const crawlers = api
    ? `# api.${site} is the archive's API. The website is https://${site}, and its sitemap lists every claim.\nUser-agent: *\n${lines(API_FILES.map((p) => `Allow: ${p}`))}Disallow: /\n`
    : `User-agent: *\nAllow: /\n${lines([...PRIVATE_PATHS, ...CRAWLER_HEAVY_VIEWS].map((p) => `Disallow: ${p}`))}`;
  const people = `${lines(FOR_A_PERSON.map((a) => `User-agent: ${a}`))}Allow: /\n${lines(PRIVATE_PATHS.map((p) => `Disallow: ${p}`))}`;
  return `${crawlers}\n# Agents fetching a page because a person asked them to.\n${people}\nSitemap: https://${site}/sitemap.xml\n\n# Agents: start at https://${site}/skill.md\n`;
}
