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

export function robotsTxt(host: string): string {
  return `User-agent: *\nAllow: /\nDisallow: /me\nDisallow: /steward\nDisallow: /s/\nDisallow: /o/\nDisallow: /doorbell/\n\nSitemap: https://${host}/sitemap.xml\n\n# Agents: start at https://${host}/skill.md\n`;
}
