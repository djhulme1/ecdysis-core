/**
 * The site's Markdown renderer (src/web/markdown.ts): used for the lab
 * guide, which is written in the repository and never by a visitor, but
 * still escapes every character of text before adding markup, keeps only
 * safe links, and never loads an image from a URL.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { inline, renderMarkdown, slug } from "../src/web/markdown.js";

describe("the Markdown renderer", () => {
  it("renders headings, paragraphs, lists, tables, fences and inline markup, escaping everything first", () => {
    const md = `# Title <b>bold?</b>

Intro paragraph with \`code <tag>\`, **bold & brave**, a [link](https://example.org/a?b=1&c=2) and a [bad link](javascript:void0).
Second line of the same paragraph.

## Section one

- first item with \`x\`
- second item
  continues here
- third <script>alert(1)</script>

1. step one
2. step two **b**

| Col A | Col B |
| --- | --- |
| a1 <i>x</i> | b1 |
| a2 | b2 \\| escaped |

\`\`\`python
print("<hi>")
\`\`\`

![A drawing](diagram.svg)
![An unknown image](https://evil.example/x.png)

Last paragraph.`;
    const html = renderMarkdown(md, { figures: { "diagram.svg": "<svg><title>d</title></svg>" } });
    assert.match(html, /^<h1 id="title-b-bold-b">Title &lt;b&gt;bold\?&lt;\/b&gt;<\/h1>/);
    assert.match(html, /<p>Intro paragraph with <code>code &lt;tag&gt;<\/code>, <b>bold &amp; brave<\/b>, a <a href="https:\/\/example\.org\/a\?b=1&amp;c=2" rel="noopener">link<\/a> and a bad link\. Second line of the same paragraph\.<\/p>/);
    assert.match(html, /<h2 id="section-one">Section one<\/h2>/);
    assert.match(html, /<ul><li>first item with <code>x<\/code><\/li><li>second item continues here<\/li><li>third &lt;script&gt;alert\(1\)&lt;\/script&gt;<\/li><\/ul>/);
    assert.match(html, /<ol><li>step one<\/li><li>step two <b>b<\/b><\/li><\/ol>/);
    assert.match(html, /<div class="table"><table><thead><tr><th>Col A<\/th><th>Col B<\/th><\/tr><\/thead><tbody><tr><td>a1 &lt;i&gt;x&lt;\/i&gt;<\/td><td>b1<\/td><\/tr><tr><td>a2<\/td><td>b2 \\\| escaped<\/td><\/tr><\/tbody><\/table><\/div>/);
    assert.match(html, /<pre class="lang-python"><code>print\(&quot;&lt;hi&gt;&quot;\)<\/code><\/pre>/);
    assert.match(html, /<figure class="fig wide diagram"><figcaption><span class="fig-title">A drawing<\/span><\/figcaption><div class="scroll"><svg><title>d<\/title><\/svg><\/div><\/figure>/);
    assert.doesNotMatch(html, /evil\.example|<img|javascript:/, "an unknown image is dropped and a bad link is text");
    assert.match(html, /<p>Last paragraph\.<\/p>$/);
    assert.doesNotMatch(html, /<script/);
  });

  it("shifts heading levels, drops the document's title on request, and keeps relative links to this site only", () => {
    const html = renderMarkdown("# Doc\n\n## Part\n\nSee [here](/lab) and [there](//evil.example) and [mail](mailto:a@b.c).", { shift: 1, dropTitle: true });
    assert.doesNotMatch(html, /<h1|<h2/);
    assert.match(html, /<h3 id="part">Part<\/h3>/);
    assert.match(html, /<a href="\/lab">here<\/a> and there and mail\./);
    assert.equal(inline("plain `a<b` **c**"), "plain <code>a&lt;b</code> <b>c</b>");
    assert.equal(slug("Level 1: one script, one model"), "level-1-one-script-one-model");
    assert.equal(slug("`code` only"), "code-only");
  });
});
