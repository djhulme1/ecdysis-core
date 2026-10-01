/**
 * The digest: double opt-in, the same answer for everyone, link scanners
 * can't act for anyone, one-click unsubscribe honoured even in read-only
 * mode, batches that resume and never send anyone an issue twice, and one
 * shared daily cap.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { CONFIRM_DAILY_CAP, Newsletter } from "../src/api/newsletter.js";
import type { SendBatch, SendEmail } from "../src/api/herald.js";
import { MemoryStore } from "../src/store/memory-store.js";
import { EcdysisService } from "../src/api/service.js";
import { MemoryRateLimiter, route } from "../src/api/router.js";
import { structuralScreener } from "../src/core/hazard.js";

const T0 = Date.UTC(2026, 9, 1, 13, 0, 0);

function seq() {
  let i = 1;
  return () => ((i++ * 2654435761) % 4294967296) / 4294967296;
}

function world(o: { cap?: number; provider?: boolean; paused?: boolean; batchFails?: boolean } = {}) {
  const store = new MemoryStore();
  let now = T0;
  const single: Array<Parameters<SendEmail>[0]> = [];
  const batches: Array<{ key: string; msgs: Array<Parameters<SendEmail>[0]> }> = [];
  let failBatch = !!o.batchFails;
  const send: SendEmail = async (m) => { single.push(m); return { ok: true, id: `c-${single.length}` }; };
  const sendBatch: SendBatch = async (msgs, key) => {
    if (failBatch) return { ok: false, error: "provider 500: boom" };
    batches.push({ key, msgs });
    return { ok: true, ids: msgs.map((_, i) => `b-${batches.length}-${i}`) };
  };
  const nl = new Newsletter({
    store, send: o.provider === false ? null : send, sendBatch: o.provider === false ? null : sendBatch,
    from: "Ecdysis digest <digest@notify.ecdysis.me>", replyTo: "replies@ecdysis.me", siteBase: "https://ecdysis.me",
    paused: !!o.paused, emailDailyCap: o.cap ?? 100, now: () => new Date(now), random: seq(),
  });
  const svc = new EcdysisService({ store, screeners: [structuralScreener()], sthPrivateKey: null, now: () => new Date(now) });
  return {
    store, nl, single, batches, svc,
    tick(ms: number) { now += ms; },
    failBatches(v: boolean) { failBatch = v; },
  };
}

const form = (email: string, ...fields: string[]) => {
  const f = new URLSearchParams({ email });
  for (const x of fields) f.append("field", x);
  return f;
};

const linkIn = (text: string, kind: "confirm" | "unsub") => {
  const re = kind === "confirm" ? /https:\/\/ecdysis\.me\/subscribe\/confirm\/([0-9a-f]{32})\/([0-9a-f]{32})/ : /https:\/\/ecdysis\.me\/u\/n\/([0-9a-f]{32})\/([0-9a-f]{32})/;
  const m = text.match(re)!;
  return { id: m[1]!, token: m[2]! };
};

describe("the digest: signing up", () => {
  it("double opt-in: one confirmation email, nothing more until a POST confirms", async () => {
    const w = world();
    const r = await w.nl.subscribe(form("Reader@Example.org", "econ", "math"));
    assert.equal(r.status, 200);
    assert.match(r.html, /Check your inbox/);
    assert.equal(w.single.length, 1);
    assert.equal(w.single[0]!.to, "reader@example.org");
    assert.match(w.single[0]!.text, /economics and mathematics|mathematics and economics/);
    const s = (await w.store.getSubscriberByEmail("reader@example.org"))!;
    assert.equal(s.status, "pending");
    assert.deepEqual(s.fields, ["econ", "math"]);

    const { id, token } = linkIn(w.single[0]!.text, "confirm");
    const get = await w.nl.confirm(id, token, "GET");
    assert.match(get.html, /<form method="post">/, "a GET shows a button, so mail scanners can't confirm anyone");
    assert.equal((await w.store.getSubscriber(id))!.status, "pending");
    const post = await w.nl.confirm(id, token, "POST");
    assert.match(post.html, /Subscribed/);
    const after = (await w.store.getSubscriber(id))!;
    assert.equal(after.status, "confirmed");
    assert.match(after.consent!, /digest-consent\/1/);
    assert.equal((await w.nl.confirm(id, "f".repeat(32), "POST")).status, 404, "a wrong token is refused");
  });

  it("answers the same for everyone, and never reveals who is subscribed", async () => {
    const w = world();
    const first = await w.nl.subscribe(form("a@example.org"));
    const { id, token } = linkIn(w.single[0]!.text, "confirm");
    await w.nl.confirm(id, token, "POST");
    const again = await w.nl.subscribe(form("a@example.org"));
    const stranger = await w.nl.subscribe(form("b@example.org"));
    assert.equal(again.html.replace(/\s+/g, " "), stranger.html.replace(/\s+/g, " "));
    assert.equal(first.html, stranger.html);
    assert.equal(w.single.length, 2, "an already-confirmed address with the same fields gets nothing new");
  });

  it("ignores bots, honours 'never email me', refuses bad addresses and resends at most every 12 hours", async () => {
    const w = world();
    const bot = form("bot@example.org");
    bot.set("website", "http://spam.example");
    assert.match((await w.nl.subscribe(bot)).html, /Check your inbox/);
    assert.equal(w.single.length, 0);
    assert.equal(await w.store.getSubscriberByEmail("bot@example.org"), null);

    await w.store.suppress("never@example.org", new Date(T0).toISOString());
    assert.match((await w.nl.subscribe(form("never@example.org"))).html, /Check your inbox/);
    assert.equal(w.single.length, 0, "a suppressed address is never emailed, and the page doesn't say so");

    assert.equal((await w.nl.subscribe(form("not an address"))).status, 422);

    await w.nl.subscribe(form("c@example.org"));
    await w.nl.subscribe(form("c@example.org"));
    assert.equal(w.single.length, 1, "no second confirmation within 12 hours");
    w.tick(13 * 3600 * 1000);
    await w.nl.subscribe(form("c@example.org"));
    assert.equal(w.single.length, 2);
  });

  it("caps confirmation emails per day, and stays closed without a provider", async () => {
    const w = world();
    for (let i = 0; i < CONFIRM_DAILY_CAP; i++) await w.nl.subscribe(form(`p${i}@example.org`));
    const over = await w.nl.subscribe(form("late@example.org"));
    assert.equal(over.status, 429);
    assert.equal(w.single.length, CONFIRM_DAILY_CAP);
    const closed = world({ provider: false });
    assert.equal((await closed.nl.subscribe(form("x@example.org"))).status, 503);
    assert.equal(closed.nl.open, false);
  });

  it("expires confirmation links after seven days and erases stale signups after thirty", async () => {
    const w = world();
    await w.nl.subscribe(form("slow@example.org"));
    const { id, token } = linkIn(w.single[0]!.text, "confirm");
    w.tick(8 * 24 * 3600 * 1000);
    assert.equal((await w.nl.confirm(id, token, "POST")).status, 410);
    w.tick(23 * 24 * 3600 * 1000);
    assert.equal(await w.nl.purgeStale(), 1);
    assert.equal(await w.store.getSubscriber(id), null, "erased");
  });
});

describe("the digest: sending issues", () => {
  async function confirmed(w: ReturnType<typeof world>, email: string, ...fields: string[]) {
    const before = w.single.length;
    await w.nl.subscribe(form(email, ...fields));
    const { id, token } = linkIn(w.single[before]!.text, "confirm");
    await w.nl.confirm(id, token, "POST");
    return id;
  }

  it("reaches exactly the confirmed audience, each with their own unsubscribe link", async () => {
    const w = world();
    await confirmed(w, "econ@example.org", "econ");
    await confirmed(w, "all@example.org");
    await confirmed(w, "math@example.org", "math");
    await w.nl.subscribe(form("pending@example.org", "econ")); // never confirms
    const blocked = await confirmed(w, "blocked@example.org", "econ");
    await w.store.suppress("blocked@example.org", new Date(T0).toISOString());

    const issue = await w.nl.createIssue({ audience: "econ", subject: "The Ecdysis digest: economics", body: "Two new papers and one replication this week. ".repeat(3) });
    assert.ok(issue.ok);
    const r = await w.nl.sendIssue(issue.ok ? issue.id : "");
    assert.ok(r.ok && r.status === "sent", JSON.stringify(r));
    const to = w.batches.flatMap((b) => b.msgs.map((m) => m.to)).sort();
    assert.deepEqual(to, ["all@example.org", "econ@example.org"], "field followers and everything-followers; never pending, other fields or suppressed");
    assert.ok(!to.includes("blocked@example.org"));
    void blocked;
    for (const m of w.batches[0]!.msgs) {
      assert.match(m.headers["List-Unsubscribe"]!, /^<https:\/\/ecdysis\.me\/u\/n\/[0-9a-f]{32}\/[0-9a-f]{32}>$/);
      assert.equal(m.headers["List-Unsubscribe-Post"], "List-Unsubscribe=One-Click");
      assert.ok(m.text.includes(m.headers["List-Unsubscribe"]!.slice(1, -1)), "the footer link is the person's own");
    }
    assert.equal((await w.nl.sendIssue(issue.ok ? issue.id : "")).ok, false, "a sent issue can't be sent again");
  });

  it("respects the shared daily cap, resumes the next day, and never sends anyone twice", async () => {
    const w = world({ cap: 4 });
    for (let i = 0; i < 4; i++) await confirmed(w, `r${i}@example.org`); // 4 confirmations use the cap
    const issue = await w.nl.createIssue({ audience: "everyone", subject: "Launch week on Ecdysis", body: "Here is what happened in the record this week, and what to watch next.".repeat(2) });
    const id = issue.ok ? issue.id : "";
    const first = await w.nl.sendIssue(id);
    assert.ok(first.ok && first.status === "partial" && first.remaining === 4 && /cap/.test(first.note ?? ""), JSON.stringify(first));
    assert.equal(w.batches.length, 0);
    w.tick(25 * 3600 * 1000);
    const second = await w.nl.sendIssue(id);
    assert.ok(second.ok && second.status === "sent" && second.delivered === 4, JSON.stringify(second));
    assert.equal(new Set(w.batches.flatMap((b) => b.msgs.map((m) => m.to))).size, 4);
    assert.equal((await w.store.getIssue(id))!.status, "sent");
  });

  it("survives a provider failure: failures are recorded, Continue retries with the same idempotency key", async () => {
    const w = world();
    await confirmed(w, "one@example.org");
    await confirmed(w, "two@example.org");
    const issue = await w.nl.createIssue({ audience: "everyone", subject: "A short note from Ecdysis", body: "Something worth knowing about the record, written by a person, in plain text." });
    const id = issue.ok ? issue.id : "";
    w.failBatches(true);
    const bad = await w.nl.sendIssue(id);
    assert.equal(bad.ok, false);
    assert.equal((await w.store.getIssue(id))!.status, "sending", "stays part-sent");
    assert.equal((await w.store.listDeliveries(id)).filter((d) => d.status === "failed").length, 2);
    w.failBatches(false);
    const good = await w.nl.sendIssue(id);
    assert.ok(good.ok && good.status === "sent");
    assert.match(w.batches[0]!.key, /^issue-[0-9a-f]{32}-[0-9a-f]{32}$/);
  });

  it("refuses HTML bodies, unknown audiences and empty audiences", async () => {
    const w = world();
    assert.equal((await w.nl.createIssue({ audience: "everyone", subject: "Hello there", body: "<a href='x'>click</a> ".repeat(10) })).ok, false);
    assert.equal((await w.nl.createIssue({ audience: "astrology", subject: "Hello there", body: "x".repeat(80) })).ok, false);
    const ok = await w.nl.createIssue({ audience: "astro", subject: "Hello there", body: "y".repeat(80) });
    const r = await w.nl.sendIssue(ok.ok ? ok.id : "");
    assert.ok(!r.ok && /Nobody has confirmed/.test(r.error));
    assert.equal((await w.store.getIssue(ok.ok ? ok.id : ""))!.status, "draft", "nothing claimed, nothing sent");
  });
});

describe("the digest on the site", () => {
  it("signs up through the form, unsubscribes in one click even in read-only mode", async () => {
    const w = world();
    const lim = new MemoryRateLimiter(1000);
    const page = await route(new Request("https://ecdysis.me/subscribe", { headers: { accept: "text/html" } }), w.svc, lim, { newsletter: w.nl });
    const html = await page.text();
    assert.match(html, /<form class="digest" method="post" action="\/subscribe">/);
    assert.match(page.headers.get("content-security-policy")!, /form-action 'self'/);
    assert.doesNotMatch(page.headers.get("content-security-policy")!, /script-src/);

    const post = await route(new Request("https://ecdysis.me/subscribe", {
      method: "POST", headers: { "content-type": "application/x-www-form-urlencoded" }, body: "email=site%40example.org&field=clim",
    }), w.svc, lim, { newsletter: w.nl });
    assert.equal(post.status, 200);
    assert.match(await post.text(), /Check your inbox/);
    const { id, token } = linkIn(w.single[0]!.text, "confirm");
    const confirm = await route(new Request(`https://ecdysis.me/subscribe/confirm/${id}/${token}`, { method: "POST" }), w.svc, lim, { newsletter: w.nl });
    assert.equal(confirm.status, 200);
    assert.equal((await w.store.getSubscriber(id))!.status, "confirmed");

    const issue = await w.nl.createIssue({ audience: "clim", subject: "Climate on Ecdysis", body: "A plain-text digest with links to the record, nothing else in it at all." });
    await w.nl.sendIssue(issue.ok ? issue.id : "");
    const u = linkIn(w.batches[0]!.msgs[0]!.text, "unsub");
    const one = await route(new Request(`https://ecdysis.me/u/n/${u.id}/${u.token}`, { method: "POST", body: "List-Unsubscribe=One-Click" }), w.svc, lim, { newsletter: w.nl, readOnly: true });
    assert.equal(one.status, 200, "honoured in read-only mode");
    assert.equal((await w.store.getSubscriber(u.id))!.status, "unsubscribed");

    const ro = await route(new Request("https://ecdysis.me/subscribe", { method: "POST", body: "email=late%40example.org" }), w.svc, lim, { newsletter: w.nl, readOnly: true });
    assert.equal(ro.status, 503, "but signups wait while the platform is read-only");
    assert.match(await ro.text(), /Not right now/);
  });

  it("shows the form on the Observatory only when email is open", async () => {
    const open = world();
    const lim = new MemoryRateLimiter(1000);
    const o = await route(new Request("https://ecdysis.me/observatory", { headers: { accept: "text/html" } }), open.svc, lim, { newsletter: open.nl });
    assert.match(await o.text(), /action="\/subscribe"/);
    assert.match(o.headers.get("content-security-policy")!, /form-action 'self'/);
    const closed = world({ provider: false });
    const c = await route(new Request("https://ecdysis.me/observatory", { headers: { accept: "text/html" } }), closed.svc, lim, { newsletter: closed.nl });
    assert.match(await c.text(), /Email digests open soon/);
  });

  it("keeps signup counts out of public statistics", async () => {
    const w = world();
    const lim = new MemoryRateLimiter(1000);
    await route(new Request("https://ecdysis.me/subscribe", { method: "POST", body: "email=quiet%40example.org" }), w.svc, lim, { newsletter: w.nl });
    const stats = (await (await route(new Request("https://api.ecdysis.me/v1/stats"), w.svc, lim)).json()) as { operational: { writes: Record<string, unknown> } };
    assert.ok(!("subscribe" in stats.operational.writes));
    assert.ok((await w.store.listAccessPrefix("funnel:subscribe")).length > 0, "counted privately");
    assert.ok(!JSON.stringify(await w.store.listAccessPrefix("")).includes("quiet@example.org"), "never the address");
  });
});
