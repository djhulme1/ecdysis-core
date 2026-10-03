/**
 * A small Markdown renderer for the site's own long texts (the lab guide),
 * which are written in the repository and never by a visitor. It knows
 * exactly what those texts use: headings, paragraphs, bullet and numbered
 * lists, tables, fenced code, inline code, bold, links and one image. Every
 * character of text is escaped before any markup is added, so even a
 * hostile edit to the source could not put a tag or a script on a page;
 * links are kept only to https, mailto-free addresses or to this site's own
 * paths; an image is rendered only when the caller supplies a drawing for
 * its name (inline SVG, themable), never as an <img> to a URL.
 */

import { esc } from "./design.js";

export interface MarkdownOptions {
  /** Inline drawings by image name: `![alt](name)` renders the drawing in a figure, with the alt as its caption. */
  figures?: Record<string, string>;
  /** Shift heading levels down (1 turns ## into h3), for a page that already has its own h1 and h2. */
  shift?: number;
  /** Drop the document's own first h1 (the page provides one). */
  dropTitle?: boolean;
}

/** https anywhere, or a path on this site; never protocol-relative (//host), never another scheme. */
const SAFE_HREF = /^(https:\/\/[^\s"'<>]+|\/(?!\/)[^\s"'<>]*)$/;

/** Inline markup: code first (its contents are literal), then bold, then links. The text is escaped before anything else. */
export function inline(text: string): string {
  const codes: string[] = [];
  let s = text.replace(/`([^`]+)`/g, (_, c: string) => { codes.push(`<code>${esc(c)}</code>`); return `\u0000${codes.length - 1}\u0000`; });
  s = esc(s);
  s = s.replace(/\*\*([^*]+)\*\*/g, "<b>$1</b>");
  s = s.replace(/\[([^\]]+)\]\(([^)\s]+)\)/g, (_, label: string, href: string) => {
    const raw = href.replace(/&amp;/g, "&");
    return SAFE_HREF.test(raw) ? `<a href="${esc(raw)}"${raw.startsWith("https://") ? ' rel="noopener"' : ""}>${label}</a>` : label;
  });
  return s.replace(/\u0000(\d+)\u0000/g, (_, i: string) => codes[Number(i)]!);
}

/** Render a whole document. */
export function renderMarkdown(md: string, o: MarkdownOptions = {}): string {
  const lines = md.replace(/\r\n/g, "\n").split("\n");
  const out: string[] = [];
  const shift = o.shift ?? 0;
  let i = 0;
  let droppedTitle = false;
  const para: string[] = [];
  const flush = () => { if (para.length) { out.push(`<p>${inline(para.join(" "))}</p>`); para.length = 0; } };
  while (i < lines.length) {
    const line = lines[i]!;
    if (/^\s*$/.test(line)) { flush(); i++; continue; }
    // Fenced code: literal until the closing fence.
    const fence = line.match(/^```(\w*)\s*$/);
    if (fence) {
      flush();
      const buf: string[] = [];
      i++;
      while (i < lines.length && !/^```\s*$/.test(lines[i]!)) { buf.push(lines[i]!); i++; }
      i++;
      out.push(`<pre${fence[1] ? ` class="lang-${esc(fence[1])}"` : ""}><code>${esc(buf.join("\n"))}</code></pre>`);
      continue;
    }
    const heading = line.match(/^(#{1,6})\s+(.*)$/);
    if (heading) {
      flush();
      const level = heading[1]!.length;
      if (level === 1 && o.dropTitle && !droppedTitle) { droppedTitle = true; i++; continue; }
      const h = Math.min(6, level + shift);
      const text = heading[2]!.trim();
      out.push(`<h${h} id="${esc(slug(text))}">${inline(text)}</h${h}>`);
      i++;
      continue;
    }
    // An image on a line of its own: a drawing the caller supplied, or nothing.
    const image = line.match(/^!\[([^\]]*)\]\(([^)\s]+)\)\s*$/);
    if (image) {
      flush();
      const drawing = o.figures?.[image[2]!];
      if (drawing) out.push(`<figure class="fig wide diagram"><figcaption><span class="fig-title">${inline(image[1]!)}</span></figcaption><div class="scroll">${drawing}</div></figure>`);
      i++;
      continue;
    }
    // A table: a header row, a separator row, then rows.
    if (/^\|.*\|\s*$/.test(line) && i + 1 < lines.length && /^\|[\s:|-]+\|\s*$/.test(lines[i + 1]!)) {
      flush();
      const cells = (row: string) => row.trim().replace(/^\|/, "").replace(/\|$/, "").split(/(?<!\\)\|/).map((c) => c.trim());
      const head = cells(line);
      i += 2;
      const rows: string[][] = [];
      while (i < lines.length && /^\|.*\|\s*$/.test(lines[i]!)) { rows.push(cells(lines[i]!)); i++; }
      out.push(`<div class="table"><table><thead><tr>${head.map((c) => `<th>${inline(c)}</th>`).join("")}</tr></thead><tbody>${rows.map((r) => `<tr>${head.map((_, k) => `<td>${inline(r[k] ?? "")}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`);
      continue;
    }
    // Lists: consecutive items; a following indented line continues the item.
    const bullet = line.match(/^[-*]\s+(.*)$/);
    const numbered = line.match(/^\d+\.\s+(.*)$/);
    if (bullet || numbered) {
      flush();
      const ordered = !!numbered;
      const items: string[] = [];
      while (i < lines.length) {
        const m = ordered ? lines[i]!.match(/^\d+\.\s+(.*)$/) : lines[i]!.match(/^[-*]\s+(.*)$/);
        if (!m) break;
        let item = m[1]!;
        i++;
        while (i < lines.length && /^\s{2,}\S/.test(lines[i]!)) { item += ` ${lines[i]!.trim()}`; i++; }
        items.push(`<li>${inline(item)}</li>`);
      }
      out.push(ordered ? `<ol>${items.join("")}</ol>` : `<ul>${items.join("")}</ul>`);
      continue;
    }
    para.push(line.trim());
    i++;
  }
  flush();
  return out.join("\n");
}

/** A heading's anchor: lower case, letters, digits and hyphens. */
export function slug(text: string): string {
  return text.toLowerCase().replace(/`/g, "").replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 60) || "section";
}
