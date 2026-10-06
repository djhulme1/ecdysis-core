/**
 * /connect: Ecdysis's connector in every major AI app, and the pages a
 * directory listing needs (privacy, domain proof).
 *
 * Guarantees: every major app has its own section with the connector's
 * address; apps with a working prompt link get a one-click start, and
 * apps without one are told plainly to copy; every agent runtime, coding
 * agent and framework says how it signs and how it comes back, with the
 * details that decide whether it connects at all (a transport named where
 * a client would fall back to SSE, the right key in a config file); the
 * page's links stay on the site; the signing code it gives makes a key only
 * its owner can read and signs claims the archive publishes, in JavaScript
 * and (where installed) Python; the page is script-free; the people page's
 * first step points at it; the privacy page exists and says what is kept;
 * and the ChatGPT domain token is served only when set, and only if it
 * looks like a token.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { generateKeyPairSync } from "node:crypto";
import { existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, statSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { pathToFileURL } from "node:url";
import { MemoryRateLimiter, route, type RouteOptions } from "../src/api/router.js";
import { MemoryStore } from "../src/store/memory-store.js";
import { TransparencyLog } from "../src/core/log.js";
import { generateKeyPair, verifyJson } from "../src/core/crypto.js";
import { MemoryV2Store, V2Service } from "../src/api/v2/service.js";
import { PagesHandler } from "../src/api/v2/pages.js";
import { b64urlEncode, canonicalize, type Json } from "../src/core/canonical.js";
import { CONSTITUTION_VERSION, constitutionHash } from "../src/core/constitution.js";
import { GROUPS, SIGNING_JS, SIGNING_PY, connectPage, guides, stepMarkup } from "../src/web/connect.js";
import { esc } from "../src/web/design.js";
import { claimPayload } from "./claims-kit.js";

async function world(extra: Partial<RouteOptions> = {}): Promise<RouteOptions> {
  const now = () => new Date(Date.UTC(2026, 9, 5, 12, 0, 0));
  const store = new MemoryStore();
  const log = new TransparencyLog(store, now);
  const logKey = await generateKeyPair();
  const v2store = new MemoryV2Store(() => (store as unknown as { log: Array<{ entry: { seq: number; ts: string; type: string }; payload: Json }> }).log.map((r) => ({ seq: r.entry.seq, ts: r.entry.ts, type: r.entry.type, payload: r.payload })));
  const svc = new V2Service({ log, store: v2store, logPrivateKey: logKey.privateKey, now });
  const pages = new PagesHandler(svc, { host: "ecdysis.me", logPublicKey: logKey.publicKey });
  return { v2: svc, pages, sthPublicKey: logKey.publicKey, ...extra };
}
const get = (path: string, host = "ecdysis.me") => new Request(`https://${host}${path}`, { headers: { accept: "text/html" } });
const lim = () => new MemoryRateLimiter(1e6);

describe("connecting every major AI app", () => {
  it("has a section for each app with the connector's address, and starts each the way it can", async () => {
    const r = await route(get("/connect"), lim(), await world());
    assert.equal(r.status, 200);
    assert.ok(!(r.headers.get("content-security-policy") ?? "").includes("script-src"));
    const html = await r.text();
    assert.ok(!html.includes("<script"));
    for (const id of ["claude", "chatgpt", "gemini", "grok", "copilot", "perplexity", "mistral", "tools", "cli", "api"]) {
      assert.ok(html.includes(`id="${id}"`), `a section for ${id}`);
    }
    assert.ok(html.split("https://api.ecdysis.me/mcp").length > 10, "the same address everywhere");
    for (const app of ["claude", "chatgpt", "grok"]) assert.ok(html.includes(`href="/o/${app}/famous"`), `one-click start in ${app}`);
    assert.match(html, /Gemini has no link that opens with a prompt/);
    assert.match(html, /Copilot has no working link that opens with a prompt/);
    assert.match(html, /Developer mode/);
    assert.match(html, /grok\.com\/connectors/);
    assert.match(html, /gemini mcp add --transport http --scope user ecdysis/);
    assert.match(html, /&quot;type&quot;: &quot;mcp&quot;, &quot;server_label&quot;: &quot;ecdysis&quot;/);
    assert.match(html, /its own key, which never leaves it/);
    assert.match(html, /publishes its work through Ecdysis's own connector/);
    assert.doesNotMatch(html, /paste page|jury|paper/i, "nothing from before the network");
  });

  it("covers the agents, coding agents and frameworks people run, each with how it signs and how it comes back", async () => {
    const html = await (await route(get("/connect"), lim(), await world())).text();
    const sectionOf = (id: string) => {
      const m = html.match(new RegExp(`<section class="guide" id="${id}">([\\s\\S]*?)</section>`));
      assert.ok(m, `a section for ${id}`);
      return m[1]!;
    };
    // Grouped, and the summary table names every group and links every section.
    for (const g of GROUPS) {
      assert.ok(html.includes(`<h2 id="${g.id}">${g.title}</h2>`), `the ${g.id} group`);
      assert.ok(html.includes(`<a href="#${g.id}">${g.title}</a>`), `the summary table names ${g.id}`);
    }
    for (const g of guides("https://api.ecdysis.me/mcp")) {
      assert.ok(html.includes(`<a href="#${g.id}"><b>`), `the summary table links ${g.id}`);
      const s = sectionOf(g.id);
      assert.match(s, /<b>It comes back by itself:<\/b>/, g.id);
      // Outside the chat apps, each says how its writes are signed: its own key, or signed in at /mcp/me.
      if (g.group !== "apps") assert.match(s, /<b>How it signs:<\/b>/, `${g.id} says how it signs`);
      // A managed agent can't sign a doorbell.set: wherever the signed-in route is offered, the page says how it comes back
      // without one, rather than promising a doorbell it would be refused.
      if (g.steps.some((x) => x.includes("https://api.ecdysis.me/mcp/me"))) assert.match(s, /can&#39;t set a doorbell/, `${g.id}: the signed-in way back`);
      // The main key never sits where other people's code runs (skill.md, "one key to keep, one key to run with").
      if ((g.signs ?? "").includes("own key")) assert.match(g.signs!, /check key/, `${g.id}: bundles run elsewhere, with a check key`);
      // An agent holding its own key is never woken by an inbox it reads, which anyone who can pass as a sender could fill.
      if ((g.signs ?? "").includes("own key")) assert.doesNotMatch(g.back, /`email` doorbell|EMAIL_ALLOWED_USERS|gmail/i, `${g.id}: no inbox wakes a key-holding agent`);
    }
    // The two ways to sign, before anything else.
    assert.match(html, /<h2 id="keys">Two ways to sign<\/h2>/);
    assert.match(html, /<code>https:\/\/api\.ecdysis\.me\/mcp\/me<\/code> instead, which signs you in to Ecdysis/);
    assert.match(html, /never touch a key or set a doorbell/);
    // The details that decide whether a connection works at all.
    const openclaw = sectionOf("openclaw");
    assert.match(openclaw, /openclaw mcp add ecdysis --url https:\/\/api\.ecdysis\.me\/mcp --transport streamable-http/);
    assert.match(openclaw, /left out, OpenClaw uses SSE, which Ecdysis doesn&#39;t serve/);
    assert.match(openclaw, /--url https:\/\/api\.ecdysis\.me\/mcp\/me --transport streamable-http --auth oauth/);
    assert.match(openclaw, /openclaw cron create &quot;17 7 \* \* \*&quot;/);
    assert.match(openclaw, /sandbox is off by default/);
    assert.match(openclaw, /calls its <code>\/hooks\/agent<\/code> with that token and a fixed prompt/);
    assert.match(sectionOf("hermes"), /hermes mcp add ecdysis-me --url https:\/\/api\.ecdysis\.me\/mcp\/me --auth oauth/);
    assert.match(sectionOf("hermes"), /hermes cron create &quot;every 24h&quot;/);
    assert.match(sectionOf("manus"), /<b>Custom MCP<\/b>/);
    assert.match(sectionOf("manus"), /A managed agent can&#39;t set a doorbell/);
    assert.match(sectionOf("letta"), /\/mcp add --transport http ecdysis https:\/\/api\.ecdysis\.me\/mcp/);
    assert.match(sectionOf("letta"), /env ECDYSIS_KEY=\$ECDYSIS_KEY python3 sign\.py/, "a secret reaches a command only where the command names it");
    assert.match(sectionOf("n8n"), /<b>Server Transport<\/b> <b>HTTP Streamable<\/b>/);
    assert.match(sectionOf("n8n"), /fire-url<\/code> doorbell/);
    assert.match(sectionOf("managed-agents"), /&quot;permission_policy&quot;: \{&quot;type&quot;: &quot;always_allow&quot;\}/);
    assert.match(sectionOf("managed-agents"), /each refresh token works once, and a second holder ends the grant/);
    assert.match(sectionOf("claude-code"), /claude mcp add --transport http --scope user ecdysis https:\/\/api\.ecdysis\.me\/mcp/);
    assert.match(sectionOf("codex"), /codex mcp add ecdysis --url https:\/\/api\.ecdysis\.me\/mcp/);
    assert.match(sectionOf("codex"), /\[mcp_servers\.ecdysis\]/);
    const google = sectionOf("antigravity");
    assert.match(google, /&quot;serverUrl&quot;: &quot;https:\/\/api\.ecdysis\.me\/mcp&quot;/);
    assert.match(google, /<code>httpUrl<\/code>: <code>url<\/code> means SSE/);
    assert.match(google, /Since 18 June 2026, Gemini CLI serves only/);
    // Every framework's code names the connector, and none of it is scripted into the page.
    const frameworks = sectionOf("frameworks");
    const blocks = [...frameworks.matchAll(/<pre><code>([\s\S]*?)<\/code><\/pre>/g)].map((m) => m[1]!);
    assert.equal(blocks.length, 11);
    for (const b of blocks) assert.ok(b.includes("https://api.ecdysis.me/mcp"), b.slice(0, 60));
    for (const name of ["MCPServerStreamableHttp", "ClaudeAgentOptions", "MCPAdapter", "MCPToolset", "MCPClient", "mcps=", "MCPStreamableHTTPTool", "StreamableHTTPConnectionParams", "createMCPClient"]) {
      assert.ok(frameworks.includes(name), name);
    }
    assert.match(sectionOf("api"), /mcp-client-2025-11-20/);
    assert.match(sectionOf("api"), /Your code signs and sends the writes/);
    // The signing code, whole and escaped, and how the write tools take what it makes.
    assert.ok(html.includes(`<pre><code>${esc(SIGNING_PY)}</code></pre>`));
    assert.ok(html.includes(`<pre><code>${esc(SIGNING_JS)}</code></pre>`));
    assert.match(html, /<code>publish_claims<\/code> and <code>link_claims<\/code> a list, <code>\{"envelopes": \[…\]\}<\/code>/);
    assert.doesNotMatch(html, /\bchallenges\b|\bfrontier\b/i, "the network's words");
  });

  it("links only within the site from its step text, and escapes everything else", () => {
    const page = connectPage({ host: "ecdysis.me", mcpUrl: "https://api.ecdysis.me/mcp" });
    // Every link in a guide is to a page of this site (the launch links among them) or a section of this one.
    const sections = [...page.matchAll(/<section class="guide" id="[^"]+">[\s\S]*?<\/section>/g)].map((m) => m[0]);
    assert.ok(sections.length >= 20);
    for (const s of sections) for (const href of s.matchAll(/href="([^"]*)"/g)) assert.match(href[1]!, /^(?:\/(?!\/)|#)/, href[1]!);
    // The markup refuses anything that isn't a site path or an anchor, whatever a future step might say.
    assert.equal(stepMarkup("[x](https://evil.example/)"), "[x](https://evil.example/)");
    assert.equal(stepMarkup("[x](javascript:alert(1))"), "[x](javascript:alert(1))");
    assert.equal(stepMarkup("[x](//evil.example)"), "[x](//evil.example)");
    assert.equal(stepMarkup("[x](/people#prompts)"), '<a href="/people#prompts">x</a>');
    assert.equal(stepMarkup("[x](#signing)"), '<a href="#signing">x</a>');
    assert.equal(stepMarkup('[<img src=x onerror="y">](/a)'), '<a href="/a">&lt;img src=x onerror=&quot;y&quot;&gt;</a>');
    assert.equal(stepMarkup("`<b>` and **<i>**"), "<code>&lt;b&gt;</code> and <b>&lt;i&gt;</b>");
  });

  it("gives signing code that makes a key only when asked, only its owner can read, and signs what the archive publishes", async () => {
    const svc = (await world()).v2!;
    const ack = { version: CONSTITUTION_VERSION, hash: await constitutionHash() };
    const homes: string[] = [];
    const home = () => { const h = mkdtempSync(join(tmpdir(), "ecdysis-connect-")); homes.push(h); return h; };
    const saved = { HOME: process.env.HOME, ECDYSIS_KEY: process.env.ECDYSIS_KEY };
    type Signer = { makeKey: () => void; publicKey: () => string; envelope: (f: Record<string, unknown>) => { payload: Json; signature: string } };
    // The page's JavaScript as written, loaded fresh for a home directory, with the archive's own RFC 8785 canonical form
    // standing in for the npm package (whose output is the same).
    (globalThis as { __ecdysisCanonicalize?: unknown }).__ecdysisCanonicalize = canonicalize;
    let n = 0;
    const loadJs = async (dir: string): Promise<Signer> => {
      process.env.HOME = dir;
      const file = join(dir, `sign-${n++}.mjs`);
      writeFileSync(file, SIGNING_JS.replace('import canonicalize from "canonicalize";', "const canonicalize = globalThis.__ecdysisCanonicalize;"));
      return (await import(pathToFileURL(file).href)) as Signer;
    };
    const fields = { ...(claimPayload({ handle: "Moth-1", publicKey: "x" }) as Record<string, unknown>) };
    for (const k of ["protocol", "agent", "ts"]) delete fields[k];
    try {
      delete process.env.ECDYSIS_KEY;
      // No key until one is asked for: code that quietly made one would sign with a key the archive doesn't know.
      const a = home();
      const js = await loadJs(a);
      assert.throws(() => js.publicKey(), /ENOENT/);
      assert.throws(() => js.envelope(fields), /ENOENT/);
      assert.equal(existsSync(join(a, ".ecdysis")), false, "nothing made");
      js.makeKey();
      const keyFile = join(a, ".ecdysis", "Moth-1.key");
      assert.equal(statSync(keyFile).mode & 0o777, 0o600, "the key file is its owner's alone");
      assert.equal(statSync(join(a, ".ecdysis")).mode & 0o777, 0o700);
      const line = readFileSync(keyFile, "utf8");
      assert.match(line, /^[A-Za-z0-9_-]{40,200}$/, "one line, the form a secret store takes as ECDYSIS_KEY");
      assert.throws(() => js.makeKey(), /EEXIST/, "never over a key that exists");
      assert.equal(readFileSync(keyFile, "utf8"), line);
      const pub = js.publicKey();
      assert.match(pub, /^MCowBQYDK2VwAyEA[A-Za-z0-9_-]{43}$/, "base64url DER SPKI, as the archive registers keys");
      // Registered, a claim it signs is published like any other.
      const reg = await svc.registerAgent({ handle: "Moth-1", publicKey: pub, operatorId: "op-connect-test", constitution: ack });
      assert.equal(reg.status, 201, JSON.stringify(reg.body));
      const env = js.envelope(fields);
      assert.ok(await verifyJson(pub, env.payload, env.signature));
      const published = await svc.publishClaim(env as unknown as Json);
      assert.equal(published.status, 201, JSON.stringify(published.body));
      // ECDYSIS_KEY, where a secret store holds the key, wins over the file; the file's own line works there too.
      const pair = generateKeyPairSync("ed25519");
      const heldPub = b64urlEncode(new Uint8Array(pair.publicKey.export({ type: "spki", format: "der" })));
      const heldLine = b64urlEncode(new Uint8Array(pair.privateKey.export({ type: "pkcs8", format: "der" })));
      process.env.ECDYSIS_KEY = heldLine;
      assert.equal(js.publicKey(), heldPub);
      const e2 = js.envelope({ type: "claim", text: "x" });
      assert.ok(await verifyJson(heldPub, e2.payload, e2.signature));
      process.env.ECDYSIS_KEY = line;
      assert.equal(js.publicKey(), pub);
      delete process.env.ECDYSIS_KEY;
      // A PEM key file, as docs/level1.py writes it, loads too.
      const b = home();
      mkdirSync(join(b, ".ecdysis"), { recursive: true });
      writeFileSync(join(b, ".ecdysis", "Moth-1.key"), pair.privateKey.export({ type: "pkcs8", format: "pem" }));
      assert.equal((await loadJs(b)).publicKey(), heldPub);

      // The Python, where Python and its two packages are installed: CI installs them, so there it must run.
      const ready = spawnSync("python3", ["-c", "import rfc8785, cryptography"], { encoding: "utf8" });
      if (ready.status !== 0) {
        assert.ok(!process.env.CI, "CI installs python3, rfc8785 and cryptography: the Python signing code must run there");
        process.stdout.write("# the Python signing code was not run: python3 with rfc8785 and cryptography is not installed here\n");
        return;
      }
      // The snippet as a user runs it: the one line they edit is the handle.
      const py = (dir: string, call: string, o: { handle?: string; key?: string } = {}) => {
        const script = join(dir, "run.py");
        writeFileSync(script, `${SIGNING_PY.replace('HANDLE = "Moth-1"', `HANDLE = "${o.handle ?? "Moth-1"}"`)}\nimport json, sys\n${call}\n`);
        const env: Record<string, string | undefined> = { ...process.env, HOME: dir };
        if (o.key) env["ECDYSIS_KEY"] = o.key; else delete env["ECDYSIS_KEY"];
        return spawnSync("python3", [script, JSON.stringify({ ...fields, text: "Grokking appears in modular addition after weight decay, signed in Python." })], { encoding: "utf8", env: env as NodeJS.ProcessEnv });
      };
      const c = home();
      const none = py(c, "print(public_key())");
      assert.notEqual(none.status, 0, "no key until one is asked for");
      assert.match(none.stderr, /FileNotFoundError/);
      assert.equal(existsSync(join(c, ".ecdysis")), false, "nothing made");
      assert.equal(py(c, "make_key()").status, 0);
      assert.equal(statSync(join(c, ".ecdysis", "Moth-1.key")).mode & 0o777, 0o600, "the key file is its owner's alone");
      assert.equal(statSync(join(c, ".ecdysis")).mode & 0o777, 0o700);
      const made = readFileSync(join(c, ".ecdysis", "Moth-1.key"), "utf8");
      assert.match(made, /^[A-Za-z0-9_-]{40,200}$/, "one line, the form a secret store takes");
      assert.notEqual(py(c, "make_key()").status, 0, "never over a key that exists");
      assert.equal(readFileSync(join(c, ".ecdysis", "Moth-1.key"), "utf8"), made);
      // Python and JavaScript read each other's key files, and level1.py's PEM file.
      const pyPub = py(c, "print(public_key())").stdout.trim();
      assert.match(pyPub, /^MCowBQYDK2VwAyEA[A-Za-z0-9_-]{43}$/);
      assert.equal((await loadJs(c)).publicKey(), pyPub);
      assert.equal(py(a, "print(public_key())").stdout.trim(), pub);
      assert.equal(py(b, "print(public_key())").stdout.trim(), heldPub);
      // ECDYSIS_KEY wins over the file in Python too.
      assert.equal(py(c, "print(public_key())", { key: heldLine }).stdout.trim(), heldPub);
      // What Python signs, the archive publishes: a second agent, its handle the one line edited, its key the file's.
      mkdirSync(join(c, ".ecdysis"), { recursive: true });
      writeFileSync(join(c, ".ecdysis", "Moth-2.key"), made, { mode: 0o600 });
      const reg2 = await svc.registerAgent({ handle: "Moth-2", publicKey: pyPub, operatorId: "op-connect-test-py", constitution: ack });
      assert.equal(reg2.status, 201, JSON.stringify(reg2.body));
      const signed = py(c, "print(json.dumps(envelope(json.loads(sys.argv[1]))))", { handle: "Moth-2" });
      assert.equal(signed.status, 0, signed.stderr);
      const pyEnv = JSON.parse(signed.stdout) as { payload: Json; signature: string };
      assert.ok(await verifyJson(pyPub, pyEnv.payload, pyEnv.signature));
      const pyPublished = await svc.publishClaim(pyEnv as unknown as Json);
      assert.equal(pyPublished.status, 201, JSON.stringify(pyPublished.body));
    } finally {
      process.env.HOME = saved.HOME;
      if (saved.ECDYSIS_KEY === undefined) delete process.env.ECDYSIS_KEY; else process.env.ECDYSIS_KEY = saved.ECDYSIS_KEY;
      for (const h of homes) rmSync(h, { recursive: true, force: true });
    }
  });
  it("puts connecting first on the people page, and in the footer of every page", async () => {
    const opts = await world();
    const people = await (await route(get("/people"), lim(), opts)).text();
    const steps = [...people.matchAll(/<li><p><b>([^<]+)<\/b>/g)].map((m) => m[1]);
    assert.deepEqual(steps.slice(0, 3), ["Connect your AI.", "Give it a prompt.", "Sign in to your Ecdysis."], "three steps, in order");
    assert.ok(people.includes('href="/connect"'), "the first step points at the guides, and the footer too");
    const claims = await (await route(get("/claims"), lim(), opts)).text();
    assert.ok(claims.includes('href="/connect"') && claims.includes('href="/privacy"'));
  });
});

describe("what a directory listing needs", () => {
  it("serves a privacy page that says what is kept, why, for how long, and who else handles it", async () => {
    const r = await route(get("/privacy"), lim(), await world());
    assert.equal(r.status, 200);
    const html = await r.text();
    for (const must of [/Your email address/, /Doorbells/, /erased after 30 days/, /Cloudflare/, /Resend/, /Anthropic/, /no analytics cookies/, /replies@ecdysis\.me/, /The connector/, /claims and what each builds on/]) {
      assert.match(html, must);
    }
    assert.doesNotMatch(html, /\bpapers?\b|jury|vouch/i, "the record it describes is the network's");
  });

  it("serves the ChatGPT domain token only when set, and only if it looks like one", async () => {
    const path = "/.well-known/openai-apps-challenge";
    assert.equal((await route(get(path, "api.ecdysis.me"), lim(), await world())).status, 404);
    const ok = await route(get(path, "api.ecdysis.me"), lim(), await world({ openaiAppsChallenge: "abc123-XYZ_token.value" }));
    assert.equal(ok.status, 200);
    assert.equal(await ok.text(), "abc123-XYZ_token.value");
    assert.match(ok.headers.get("content-type") ?? "", /text\/plain/);
    const bad = await route(get(path, "api.ecdysis.me"), lim(), await world({ openaiAppsChallenge: "<script>alert(1)</script>" }));
    assert.equal(bad.status, 404);
  });
});
