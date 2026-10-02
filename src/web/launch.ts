/**
 * One click from a prompt to an AI app, and from Ecdysis's MCP server into
 * an AI tool.
 *
 * Prompt buttons open an app with the prompt typed in and NOT sent: the
 * person reads it and presses send. Claude (claude.ai/new?q=) and Claude
 * Code (claude-cli://open?q=) document exactly this; ChatGPT's ?q= is long
 * standing, and since July 2025 it does not send by itself when the link
 * comes from another site; Grok's ?q= asks the person to confirm before it
 * sends. Gemini and Microsoft Copilot have no working link (Copilot's broke
 * in November 2025), so they get the words to copy, and /connect says how
 * to connect each of them.
 *
 * MCP buttons use the official "Add to …" links of Cursor, VS Code and LM
 * Studio, each of which asks the person to confirm. Claude's own apps add a
 * connector by hand (four steps); Claude Code takes one command.
 *
 * Every button goes through /o/<app>/<what>: the click is counted by app
 * and prompt only (never who), then the browser goes on to a target built
 * here from fixed parts and a prompt this site wrote, so the route can never
 * be an open redirect. Web apps get a 302; apps opened by their own URL
 * scheme get a short page that opens them and says what to do if nothing
 * happens.
 */

import { esc, shell } from "./design.js";

export interface PromptAppDef {
  label: string;
  /** A web address (302) or an app's own scheme (a page that opens it). */
  web: boolean;
  /** The longest prompt the app takes in a link, in characters. */
  max: number;
  target: (prompt: string) => string;
  /** What has to be true for the link to work, for the fallback page. */
  needs: string;
}

/** encodeURIComponent, plus the five characters it leaves alone (RFC 3986 reserves them), so no app's link parser trips on an apostrophe. */
const enc = (s: string) => encodeURIComponent(s).replace(/[!'()*]/g, (c) => `%${c.charCodeAt(0).toString(16).toUpperCase()}`);

export const PROMPT_APPS = {
  claude: {
    label: "Claude", web: true, max: 14000,
    target: (q: string) => `https://claude.ai/new?q=${enc(q)}`,
    needs: "a Claude account; signing in first is fine",
  },
  chatgpt: {
    label: "ChatGPT", web: true, max: 6000,
    target: (q: string) => `https://chatgpt.com/?q=${enc(q)}`,
    needs: "a ChatGPT account; signing in first is fine",
  },
  grok: {
    label: "Grok", web: true, max: 6000,
    target: (q: string) => `https://grok.com/?q=${enc(q)}`,
    needs: "a Grok account; Grok asks you to confirm before it sends the prompt",
  },
  "claude-code": {
    label: "Claude Code", web: false, max: 5000,
    target: (q: string) => `claude-cli://open?q=${enc(q)}`,
    needs: "Claude Code installed on this computer, and run once: send it any prompt, and from then on links can open it",
  },
} as const satisfies Record<string, PromptAppDef>;
export type PromptApp = keyof typeof PROMPT_APPS;

export interface McpAppDef {
  label: string;
  target: (mcpUrl: string) => string;
  /** The same server, written into the app's settings by hand: what to do, and what to enter. */
  manual: (mcpUrl: string) => { how: string; code: string };
}

const b64 = (s: string) => btoa(s);

export const MCP_APPS = {
  cursor: {
    label: "Cursor",
    target: (url: string) => `cursor://anysphere.cursor-deeplink/mcp/install?name=ecdysis&config=${encodeURIComponent(b64(JSON.stringify({ url })))}`,
    manual: (url: string) => ({ how: "add this to ~/.cursor/mcp.json:", code: `{"mcpServers": {"ecdysis": {"url": "${url}"}}}` }),
  },
  vscode: {
    label: "VS Code",
    target: (url: string) => `vscode:mcp/install?${encodeURIComponent(JSON.stringify({ name: "ecdysis", type: "http", url }))}`,
    manual: (url: string) => ({ how: "run MCP: Add Server from the command palette, choose HTTP, and enter", code: url }),
  },
  lmstudio: {
    label: "LM Studio",
    target: (url: string) => `lmstudio://add_mcp?name=ecdysis&config=${encodeURIComponent(b64(JSON.stringify({ url })))}`,
    manual: (url: string) => ({ how: "add this to LM Studio's mcp.json (Program, then Install, then Edit mcp.json):", code: `{"mcpServers": {"ecdysis": {"url": "${url}"}}}` }),
  },
} as const satisfies Record<string, McpAppDef>;
export type McpApp = keyof typeof MCP_APPS;

/** Where MCP clients connect: the API host in production, the serving host anywhere else. */
export function mcpUrlFor(host: string): string {
  return host === "ecdysis.me" || host === "api.ecdysis.me" ? "https://api.ecdysis.me/mcp" : `https://${host}/mcp`;
}

/** The apps each prompt may open in. Prompts written for a walled-in chat AI skip Claude Code, which is never walled in. */
export function appsFor(id: string): PromptApp[] {
  return id === "paste" || id === "handoff" ? ["claude", "chatgpt", "grok"] : ["claude", "chatgpt", "grok", "claude-code"];
}

/** The "Open in" buttons under a prompt. */
export function launchRow(id: string): string {
  return `<p class="openin"><span>Open in</span>${appsFor(id).map((a) =>
    `<a href="/o/${a}/${esc(id)}" target="_blank" rel="noopener" aria-label="Open this prompt in ${esc(PROMPT_APPS[a].label)}, typed in but not sent">${esc(PROMPT_APPS[a].label)}</a>`).join("")}</p>`;
}

/** "Add to …" buttons for the MCP server, plus the two apps that take it by hand. */
export function mcpConnect(mcpUrl: string): string {
  return `<div class="mcpin">${(Object.keys(MCP_APPS) as McpApp[]).map((a) =>
    `<a class="btn quiet" href="/o/${a}/mcp" target="_blank" rel="noopener">Add to ${esc(MCP_APPS[a].label)}</a>`).join("")}</div>
<ul class="rows">
<li><span class="t">Claude (web, desktop and mobile)</span><span class="d">No link can add a connector, so it takes four steps: Customize, then Connectors, then Add custom connector, then paste <code>${esc(mcpUrl)}</code>. No sign-in is needed. Then switch it on in a chat with the + button.</span></li>
<li><span class="t">Claude Code</span><span class="d">One command: <code>claude mcp add --transport http ecdysis ${esc(mcpUrl)}</code></span></li>
<li><span class="t">Anything else that speaks MCP</span><span class="d"><code>{"mcpServers": {"ecdysis": {"url": "${esc(mcpUrl)}"}}}</code></span></li>
</ul>`;
}

/**
 * The page an app scheme link lands on: it asks the browser to open the
 * app at once, keeps a button for the browsers that want a click, and says
 * what to do if nothing happens. Script-free.
 */
export function launchPage(o: { label: string; target: string; needs: string; prompt?: string; mcp?: { url: string; manual: { how: string; code: string } } }): string {
  const what = o.mcp ? `Adding Ecdysis to ${o.label}` : `Opening ${o.label}`;
  const body = `
<h1>${esc(what)}…</h1>
<p class="lede">${o.mcp
    ? `Your browser should ask to open ${esc(o.label)}, which then asks you to confirm adding Ecdysis's MCP server: read tools, no key or account needed.`
    : `Your browser should ask to open ${esc(o.label)}, with the prompt typed in and not sent. Read it, then press Enter.`}</p>
<p><a class="btn" href="${esc(o.target)}">Open ${esc(o.label)}</a></p>
<h2>If nothing happens</h2>
<p>This needs ${esc(o.needs)}.</p>
${o.prompt ? `<div class="prompt"><h3>Or copy the prompt</h3><p class="why">Click inside the box once to select everything, then copy.</p><p class="pt">${esc(o.prompt)}</p></div>` : ""}
${o.mcp ? `<p>Or add it by hand: ${esc(o.mcp.manual.how)}</p><pre><code>${esc(o.mcp.manual.code)}</code></pre>` : ""}
<p class="small"><a href="/people">Back to the start page</a></p>`;
  return shell({
    title: `${what} — Ecdysis`,
    description: `${what}.`,
    half: "people",
    body,
    head: `<meta http-equiv="refresh" content="0;url=${esc(o.target)}"><meta name="robots" content="noindex">`,
  });
}
