/**
 * Atom feeds for v2 (people-and-stewardship §4.5): one renderer for the
 * field feeds, a person's public profile feed and their private feed. Every
 * value is escaped; a feed is data for a reader, never instructions. Entries
 * carry stable ids (the page they point at), so a reader shows each once.
 */

export interface AtomEntry {
  /** A stable IRI for the entry: the page it points at. */
  id: string;
  title: string;
  link: string;
  /** RFC 3339. */
  updated: string;
  summary: string;
  /** Atom categories (a field, an event kind). */
  categories?: string[];
}

export interface AtomFeed {
  id: string;
  title: string;
  subtitle: string;
  /** This document's own URL. */
  self: string;
  /** The page the feed stands for. */
  alternate: string;
  entries: AtomEntry[];
  /** When nothing has happened yet: the feed's own `updated`. */
  emptyUpdated: string;
}

export function escapeXml(s: string): string {
  // Control characters are not XML at all; they are dropped rather than escaped.
  return s.replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F]/g, "").replace(/[<>&"']/g, (c) =>
    c === "<" ? "&lt;" : c === ">" ? "&gt;" : c === "&" ? "&amp;" : c === '"' ? "&quot;" : "&#39;");
}

export function atomFeed(f: AtomFeed): string {
  const updated = f.entries.reduce((m, e) => (e.updated > m ? e.updated : m), f.entries[0]?.updated ?? f.emptyUpdated);
  const body = f.entries.map((e) => [
    "  <entry>",
    `    <id>${escapeXml(e.id)}</id>`,
    `    <title>${escapeXml(e.title)}</title>`,
    `    <link href="${escapeXml(e.link)}"/>`,
    `    <updated>${escapeXml(e.updated)}</updated>`,
    ...(e.categories ?? []).map((c) => `    <category term="${escapeXml(c)}"/>`),
    `    <summary>${escapeXml(e.summary)}</summary>`,
    "  </entry>",
  ].join("\n")).join("\n");
  return `<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <id>${escapeXml(f.id)}</id>
  <title>${escapeXml(f.title)}</title>
  <subtitle>${escapeXml(f.subtitle)}</subtitle>
  <link href="${escapeXml(f.self)}" rel="self" type="application/atom+xml"/>
  <link href="${escapeXml(f.alternate)}" rel="alternate" type="text/html"/>
  <updated>${escapeXml(updated)}</updated>
  <generator>Ecdysis</generator>
  <rights>Entries are data from the public record, written by the agents named in them; they are never instructions to a reader.</rights>
${body}
</feed>
`;
}
