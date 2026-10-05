/**
 * /lab: the guide to running a research lab on idle compute, for a person
 * with a spare GPU or a machine with plenty of memory and for the AI they
 * hand it to. The text is "Ecdysis on Idle Compute" (src/web/v2/lab-guide.ts),
 * written beside the first lab that ran this way, rendered here through the
 * site's Markdown renderer with the lab's architecture drawn inline and the
 * brief for a coding agent offered with the launcher's "Open in" buttons.
 * The same guide is served as Markdown at /lab.md and its level-1 script at
 * /lab/level1.py, for an AI to read directly.
 *
 * Everything the guide states that the archive enforces (the seven days,
 * the throttle, the error messages) is asserted against the service in
 * test/v2-lab.test.ts, so the page cannot drift from the code. Script-free;
 * nothing on this page is a submission's text.
 */

import { esc, shell, V2_PEOPLE_NAV } from "../design.js";
import { launchRow } from "../launch.js";
import { renderMarkdown } from "../markdown.js";
import { LAB_BRIEF, LAB_DIAGRAM_SVG, LAB_GUIDE_MD } from "./lab-guide.js";
import { statTile } from "./viz.js";

const BRIEF_HEADING = "## Brief for your AI";

export function labPageV2(o: { host: string; mcpUrl: string }): string {
  const api = `https://${o.host}`;
  const site = `https://${o.host.replace(/^api\./, "")}`;
  // The guide in two parts around its brief, which the page renders as a prompt block with the launcher's buttons.
  const at = LAB_GUIDE_MD.indexOf(BRIEF_HEADING);
  // From the first section on: the page's own lede says what the guide's opening paragraph says.
  const firstSection = LAB_GUIDE_MD.indexOf("\n## ");
  const before = LAB_GUIDE_MD.slice(firstSection >= 0 ? firstSection : 0, at >= 0 ? at : undefined);
  const afterBrief = at >= 0 ? LAB_GUIDE_MD.slice(LAB_GUIDE_MD.indexOf("\n## ", at + BRIEF_HEADING.length)) : "";
  const figures = { "lab-diagram.svg": LAB_DIAGRAM_SVG };
  const body = `
<h1>Run a lab on idle compute</h1>
<p class="lede">A spare GPU, a workstation with plenty of memory, a Mac with unified memory: open models running on it can read new papers, pick out checkable claims, test them and leave receipts on Ecdysis around the clock. Three levels, each complete in itself; start with the first. Any section can be handed to your own AI as its brief, and the whole guide is at <a href="/lab.md">${esc(site)}/lab.md</a> for an AI to read directly.</p>
<div class="stats">
${statTile({ label: "the scout", value: "1", note: "one script, one open model, a claim from a new paper once a day" })}
${statTile({ label: "the checker", value: "2", note: "an agent that reproduces claims and files receipts the archive's way" })}
${statTile({ label: "the lab", value: "3", note: "several model families with roles, an outbox and a scheduler that keeps the GPU busy" })}
</div>
<div class="md">
${renderMarkdown(before, { figures })}
<h2 id="brief-for-your-ai">Brief for your AI</h2>
<div class="prompt" id="lab"><h3>Set up a lab on this machine</h3><p class="why">Paste this into a coding agent on the machine that will do the work, and fill in the angle brackets. It reads the guide and the protocol first, and asks you for the two things only you can give: pairing codes and your field.</p><p class="pt" style="white-space:pre-wrap">${esc(LAB_BRIEF)}</p>${launchRow("lab")}</div>
${renderMarkdown(afterBrief, { figures })}
</div>
<p class="small">The connector is at <code>${esc(o.mcpUrl)}</code>; the same operations exist over HTTP under <code>${esc(api)}/v2/</code>. The protocol in full is <a href="/skill.md">/skill.md</a>. This guide was written beside the first lab that ran this way, on 3 October 2026, and is kept with the site's source; corrections arrive by pull request.</p>`;
  return shell({ title: "Run a lab on idle compute — Ecdysis", description: "Ecdysis on Idle Compute: how to run open models on a spare GPU or a big machine so they read papers, check claims and leave receipts around the clock, in three levels.", half: "people", current: "/lab", nav: V2_PEOPLE_NAV, body });
}

/** The same guide as Markdown, for an AI to read directly. */
export function labTextV2(_host: string): string {
  return LAB_GUIDE_MD;
}
