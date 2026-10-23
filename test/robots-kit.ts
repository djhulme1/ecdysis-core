/**
 * A reader of robots.txt as RFC 9309 describes it, for the tests: the group whose user-agent matches the crawler's
 * product token (case-insensitively), else the "*" group; then the rule with the longest pattern that matches the path
 * and query, "*" matching any run of characters and a final "$" the end; an allow beats a disallow of the same length,
 * and a path no rule matches may be read.
 */

interface Rule { allow: boolean; pattern: string }
interface Group { agents: string[]; rules: Rule[] }

function groups(txt: string): Group[] {
  const out: Group[] = [];
  let current: Group | null = null;
  let naming = false;
  for (const raw of txt.split("\n")) {
    const line = raw.replace(/#.*/, "").trim();
    const m = line.match(/^([A-Za-z-]+)\s*:\s*(.*)$/);
    if (!m) continue;
    const key = m[1]!.toLowerCase();
    const value = m[2]!.trim();
    if (key === "user-agent") {
      if (!current || !naming) { current = { agents: [], rules: [] }; out.push(current); }
      current.agents.push(value.toLowerCase());
      naming = true;
      continue;
    }
    naming = false;
    if ((key === "allow" || key === "disallow") && current && value) current.rules.push({ allow: key === "allow", pattern: value });
  }
  return out;
}

function matches(pattern: string, path: string): boolean {
  const anchored = pattern.endsWith("$");
  const body = anchored ? pattern.slice(0, -1) : pattern;
  const re = body.split("*").map((s) => s.replace(/[.+?^${}()|[\]\\]/g, "\\$&")).join(".*");
  return new RegExp(`^${re}${anchored ? "$" : ""}`).test(path);
}

/** Whether a crawler with this product token may read this path (with its query, if any). */
export function mayRead(robots: string, token: string, path: string): boolean {
  const all = groups(robots);
  let chosen = all.filter((g) => g.agents.includes(token.toLowerCase()));
  if (!chosen.length) chosen = all.filter((g) => g.agents.includes("*"));
  const hits = chosen.flatMap((g) => g.rules).filter((r) => matches(r.pattern, path));
  if (!hits.length) return true;
  const longest = Math.max(...hits.map((r) => r.pattern.length));
  return hits.some((r) => r.pattern.length === longest && r.allow);
}

/** The Sitemap lines. */
export function sitemaps(robots: string): string[] {
  return robots.split("\n").map((l) => l.match(/^Sitemap:\s*(\S+)/i)?.[1]).filter((s): s is string => !!s);
}
