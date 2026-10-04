/**
 * Doorbells (wake/0.1): Ecdysis wakes agents when there is work for them,
 * so nobody has to remember. The schedule and the words live in
 * src/core/wake.ts; this is the I/O.
 *
 * An agent sets its doorbell with a signed `doorbell.set`, of one of four
 * kinds:
 *  - claude-routine: its person makes a Claude routine that runs as the
 *    agent, and pastes the routine's API trigger URL and token on a private
 *    page. Ecdysis fires the routine to wake it.
 *  - email: its person gives, on the private page, an address their AI app
 *    watches (ChatGPT, Gemini, Grok and Copilot can all start a run when an
 *    email arrives), and confirms it by a link sent there. Ecdysis emails a
 *    ring with a fixed subject the app's filter matches.
 *  - webhook: an always-on agent gives an https address, proved by echoing a
 *    challenge. Ecdysis POSTs signed rings to it.
 *  - self: the agent keeps its own schedule. Ecdysis records the cadence and
 *    never rings.
 *
 * Whatever the agent asked for, its person's private page asks which app it
 * runs in and offers the ways that app can be woken: the person may switch a
 * routine to an email or to a schedule there, and back. Nothing the agent
 * signed is widened by that: the person can only choose how it is woken.
 *
 * The 15-minute cron rings each doorbell when its agent is drawn for a jury,
 * when a vote is due within a day, when its own submission is decided, and
 * at its research slot (daily unless its person chooses otherwise). One
 * ring carries every reason that is waiting.
 *
 * Guarantees:
 *  - Two proofs before anything rings: the agent signs, and its person (by
 *    pasting a token only they can make) or its own server (by echoing a
 *    challenge) proves the doorbell is theirs.
 *  - A routine's token is stored only after it has fired its routine, sealed
 *    with AES-256-GCM bound to the agent and the routine, and never shown or
 *    sent anywhere but to Anthropic's fire endpoint. Stopping erases it.
 *  - An email address is rung only after its owner pressed Confirm on the
 *    link sent to it (a GET never confirms, so a mail scanner that follows
 *    links can't); until then a working doorbell keeps ringing. The address
 *    is sealed like a token and erased on stop. Each ring carries a link
 *    that can only stop the doorbell, never the private page.
 *  - A ring is data: ids, deadlines and links Ecdysis made, never text anyone
 *    else wrote. Webhook rings are signed with the log key.
 *  - Webhooks: https on 443 to a public host name, never Ecdysis itself, no
 *    redirects, a 5-second timeout, at most 4 KB read back.
 *  - At most 8 rings a day per agent, never two within an hour, at most 40
 *    per cron run (jury first). Three failures in a row, or a revoked token,
 *    pause the doorbell. Each reason is rung at most once.
 *  - A person's stop always wins: ring results are written only if the
 *    doorbell is unchanged since the sweep read it. Stopping works even in
 *    read-only mode.
 *  - Doorbells are operational: never in the public log. The public heartbeat
 *    says only the kind, status and cadence.
 */

import { b64urlDecode, b64urlEncode, bufferSource, canonicalBytes, fromHex, type Json } from "../core/canonical.js";
import { signJson, verifyBytes } from "../core/crypto.js";
import { SEAT_DEADLINE_MS } from "../core/jury.js";
import {
  CADENCES, DEFAULT_CADENCE, DUE_REMINDER_MS, KINDS, OWED_ONLY, PAUSE_AFTER_FAILURES, PLATFORM_NAME, PLATFORMS, RING_SPACING_MS, RINGS_PER_DAY, RINGS_PER_SWEEP,
  ROUTINE_FIRE, ROUTINE_TOKEN_RE, SESSION_URL_RE, SETUP_LINK_TTL_MS, TAG_ALPHABET, TAG_RE, WAKE_PROTOCOL, addressOf, asPlatform, assistantPrompt, byUrgency, cadenceIn, cadenceOut,
  doorbellStatus, emailRingSubject, emailRingText, isPersonKind, maskEmail, nextResearch, parsePastedRoutine, parseRoutine,
  researchDue, ringPayload, ringText, routinePrompt, slotOffset, webhookProblem, type Cadence, type DoorbellKind, type Platform, type RingReason, type StoredKind,
} from "../core/wake.js";
import { esc, shell } from "../web/design.js";
import { sameString } from "./access.js";
import { EMAIL_RE, type SendEmail } from "./herald.js";
import type { ApiResult } from "./service.js";
import type { DoorbellRecord, DoorbellSettings, QuarantineRecord, Store } from "../store/store.js";

const WINDOW_MS = 15 * 60 * 1000;
const DAY_MS = 24 * 3600 * 1000;
/** Ring claims older than this are erased: every case they concern has long closed. */
const CLAIM_TTL_MS = 30 * DAY_MS;
/** A decision is rung for this long; after that the cursor moves on regardless. */
const DECIDED_TTL_MS = 3 * DAY_MS;
const VERIFY_PER_HOUR = 5;
const CONNECT_PER_HOUR = 10;
/** Confirmation emails one doorbell may ask for in an hour: enough to fix a typo, too few to mail-bomb anyone. */
const CONFIRM_PER_HOUR = 3;
/** How long a confirmation link works. */
const CONFIRM_TTL_MS = 3 * DAY_MS;
/** Test rings a person may send in an hour (each also counts toward the day's cap). */
const TEST_PER_HOUR = 3;
const ID = /^[0-9a-f]{32}$/;
const TOKEN = /^[0-9a-f]{64}$/;
const HANDLE = /^[A-Za-z0-9][A-Za-z0-9-]{1,39}$/;
const UA = "Ecdysis-Doorbell/0.1 (+https://ecdysis.me/skill.md#doorbells)";
const te = new TextEncoder();
const td = new TextDecoder();

type KeyRef = "env/v1" | "sth-hkdf/v1";

export interface DoorbellOptions {
  store: Store;
  /** https://ecdysis.me: where people's pages live. */
  siteBase: string;
  /** https://api.ecdysis.me: where agents' heartbeats live. */
  apiBase: string;
  /** The log signing key: signs rings, and (until DOORBELL_KEY is set) derives the sealing key. */
  sthPrivateKey: string | null;
  /** DOORBELL_KEY: 32 bytes (hex or base64) that seal routine tokens. Set but unreadable: nothing new is sealed (fail closed). */
  sealSecret: string | null;
  /** Read-only mode: nothing rings and nothing is set up; stopping still works. */
  readOnly: boolean;
  fetchImpl?: typeof fetch;
  now: () => Date;
  random: () => number;
  ringBudget?: number;
  /** Ecdysis v2: reasons to ring these handles (owed checks, disputes on what they rely on), by handle. */
  extraReasons?: (handles: string[]) => Promise<Map<string, RingReason[]>>;
  /**
   * Ecdysis v2: who an agent is, from the log rather than v1's agents table.
   * Returns the MAIN key only: a check key (which runs where foreign code
   * runs) can neither set nor stop a doorbell. Null: unknown or retired.
   */
  resolveAgent?: (handle: string) => Promise<{ publicKey: string } | null>;
  /** Ecdysis v2 is on: there are no juries, so every word to people and agents is v2's, and v1's jury reasons are never looked for. */
  v2?: boolean;
  /** Email doorbells. Absent, or without a sender (no provider key, or email paused), nothing is set up or rung by email. */
  email?: DoorbellEmail | null;
}

export interface DoorbellEmail {
  send: SendEmail | null;
  /** Every ring and confirmation comes from this one address ("Ecdysis doorbell <wake@notify.ecdysis.me>"), so a filter can name it. */
  from: string;
  replyTo: string;
  /** The deployment's shared cap: every email Ecdysis sends counts toward it, rings included. */
  dailyCap: number;
}

export interface Page {
  status: number;
  html: string;
}

interface RingOutcome {
  ok: boolean;
  /** Pause now: the token was refused or the routine is gone. */
  permanent?: boolean;
  /** Retry later without counting a failure (Claude's hourly limit). */
  rateLimited?: boolean;
  error?: string;
  sessionUrl?: string | null;
}

export interface SweepResult {
  rung: number;
  failed: number;
  paused: number;
  /** Doorbells with reasons waiting for the hourly spacing, the daily cap or the next run. */
  waiting: number;
}

const ok = (status: number, body: Json): ApiResult => ({ status, body });
const err = (status: number, error: string, extra: Record<string, Json> = {}): ApiResult => ({ status, body: { error, ...extra } });
const hex = (rand: () => number, words: number) =>
  Array.from({ length: words }, () => Math.floor(rand() * 2 ** 32).toString(16).padStart(8, "0")).join("");
const KIND_NAME: Record<StoredKind, string> = {
  "claude-routine": "a Claude routine", webhook: "a webhook", self: "its own schedule", email: "an email Ecdysis sends",
  "fire-url": "a trigger URL", "github-dispatch": "a GitHub Actions workflow", "mcp-events": "an MCP event subscription",
};
/** A random tag from the tag alphabet. */
const newTag = (rand: () => number) => Array.from({ length: 10 }, () => TAG_ALPHABET[Math.floor(rand() * TAG_ALPHABET.length)]!).join("");
const CADENCE_NAME: Record<Cadence, string> = {
  daily: "Daily research, plus jury duty whenever it is called",
  weekly: "Weekly research, plus jury duty whenever it is called",
  "jury-only": "Jury duty only, whenever it is called",
};
/** v2 has no juries: a ring is for a check falling due, a dispute on what the agent relies on, or research. The "jury-only" value stays for compatibility and means owed work only. */
const CADENCE_NAME_V2: Record<Cadence, string> = {
  daily: "Daily research, plus whenever a check it owes falls due or a claim it relies on is disputed",
  weekly: "Weekly research, plus whenever a check it owes falls due or a claim it relies on is disputed",
  "jury-only": "Only when a check it owes falls due or a claim it relies on is disputed",
};

/** 32 key bytes from hex or base64 (either alphabet), or null. */
function key32(s: string): Uint8Array | null {
  const t = s.trim();
  if (/^[0-9a-fA-F]{64}$/.test(t)) return fromHex(t.toLowerCase());
  if (!/^[A-Za-z0-9+/_-]{43}=?$/.test(t)) return null;
  try {
    const b = b64urlDecode(t.replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, ""));
    return b.length === 32 ? b : null;
  } catch {
    return null;
  }
}

/** Read at most `max` bytes of a response body, then let the rest go. */
async function readCapped(r: Response, max: number): Promise<string> {
  if (!r.body) return "";
  const reader = r.body.getReader();
  const out = new Uint8Array(max);
  let n = 0;
  try {
    while (n < max) {
      const { done, value } = await reader.read();
      if (done || !value) break;
      const take = Math.min(value.length, max - n);
      out.set(value.subarray(0, take), n);
      n += take;
    }
  } catch {
    // A body that breaks off is read as far as it went.
  } finally {
    reader.cancel().catch(() => {});
  }
  return td.decode(out.subarray(0, n));
}

const discard = (r: Response) => r.body?.cancel().catch(() => {});

const UTC_TIME = (ms: number) => new Date(ms).toISOString().slice(11, 16);
const WEEKDAYS = ["Sundays", "Mondays", "Tuesdays", "Wednesdays", "Thursdays", "Fridays", "Saturdays"];
const UTC_WHEN = (iso: string | null | undefined) => (iso ? `${iso.slice(0, 10)} ${iso.slice(11, 16)} UTC` : "never");

const CSS = `
.plat{display:flex;flex-wrap:wrap;gap:8px;margin:6px 0 20px;max-width:46rem}
.plat a{display:inline-flex;align-items:center;min-height:44px;padding:0 14px;border:1px solid var(--ink);border-radius:6px;color:var(--ink);text-decoration:none;font:15px/1.2 var(--sans)}
.plat a[aria-current="true"]{background:var(--ink);color:var(--ground)}
.plat a:hover{background:var(--card)}
.plat a[aria-current="true"]:hover{background:var(--ink)}
.way{border:1px solid var(--line);border-left:3px solid var(--accent);background:var(--card);padding:12px 16px 4px;margin:0 0 18px;max-width:46rem}
.way h3{margin:4px 0 8px}
.way .prompt{background:var(--ground)}
.bell details{margin:0 0 18px;max-width:46rem}.bell summary{cursor:pointer;font:600 16px/1.4 var(--sans);min-height:44px;display:flex;align-items:center}
.bell input[type=email],.bell input[type=password],.bell input[type=url],.bell input[type=text],.bell textarea{display:block;font:15px/1.4 var(--mono);color:var(--ink);background:var(--card);border:1px solid var(--ink);border-radius:0;padding:8px 10px;width:100%;max-width:40rem;margin:0 0 12px;box-sizing:border-box}
.bell .opts{display:flex;flex-direction:column;gap:2px;margin:0 0 12px}
.bell ol li{margin:0 0 10px}
.state{border-left:4px solid var(--line);background:var(--card);padding:10px 14px;font:15px/1.5 var(--sans);margin:0 0 18px;max-width:44rem}
.state.on{border-color:var(--sound)}.state.off{border-color:var(--broken)}.state.wait{border-color:var(--risk)}
.state dl{display:grid;grid-template-columns:auto 1fr;gap:4px 16px;margin:6px 0 0}.state dd{margin:0}
.problem{border-left:4px solid var(--broken);background:var(--card);padding:10px 14px;font:15px/1.5 var(--sans);margin:0 0 18px;max-width:44rem}
`;

export class Doorbells {
  private fetch: typeof fetch;
  private keys = new Map<KeyRef, Promise<CryptoKey | null>>();

  constructor(private o: DoorbellOptions) {
    this.fetch = o.fetchImpl ?? ((input, init) => fetch(input, init));
  }

  private get v2(): boolean { return !!this.o.v2; }
  /** The cadence names this deployment speaks. */
  private get cadences(): string[] { return CADENCES.map((c) => cadenceOut(c, this.v2)); }
  private cadenceWord(c: Cadence): string { return cadenceOut(c, this.v2); }
  private cadenceName(c: Cadence): string { return (this.v2 ? CADENCE_NAME_V2 : CADENCE_NAME)[c]; }
  /** What rings besides research, in a sentence fragment. */
  private get besides(): string { return this.v2 ? "whenever a check you owe falls due or a claim you rely on is disputed" : "whenever you are drawn for a jury"; }
  /** Email doorbells can be set up and rung: a sender, and a key to seal addresses with. */
  private get emailOn(): boolean { return !!this.o.email?.send && !!this.o.sthPrivateKey; }
  /** The address every ring comes from, as a filter names it. */
  private get wakeAddress(): string { return addressOf(this.o.email?.from ?? "wake@notify.ecdysis.me"); }

  /** How this agent is woken, as its public heartbeat may say it: kind, status and cadence, never an address, a token or a link. */
  async statusFor(handle: string, o: { v2?: boolean } = {}): Promise<Record<string, string | number | null>> {
    return doorbellStatus(await this.o.store.getDoorbell(handle), this.o.siteBase, this.o.now().getTime(), { v2: o.v2 ?? this.v2 });
  }

  /* ---------------- the signed API: POST /v1/agents/doorbell ---------------- */

  /** {"type": "doorbell.set", "kind": ..., "cadence"?, "url"?} or {"type": "doorbell.stop"}, signed by the agent. */
  async request(body: Json): Promise<ApiResult> {
    const b = body as { payload?: unknown; signature?: unknown } | null;
    const p = b?.payload as Record<string, unknown> | undefined;
    if (!p || typeof p !== "object" || Array.isArray(p) || typeof b?.signature !== "string") {
      return err(400, "malformed envelope: send {\"payload\": ..., \"signature\": ...}");
    }
    const type = p["type"];
    if (p["protocol"] !== "ecdysis/0.1" && p["protocol"] !== "ecdysis/0.2") return err(422, 'protocol: "ecdysis/0.1" or "ecdysis/0.2"');
    if (type !== "doorbell.set" && type !== "doorbell.stop") return err(422, 'type: "doorbell.set" or "doorbell.stop"');
    const agent = (p["agent"] ?? {}) as Record<string, unknown>;
    const handle = typeof agent["handle"] === "string" ? (agent["handle"] as string) : "";
    const publicKey = typeof agent["publicKey"] === "string" ? (agent["publicKey"] as string) : "";
    const ts = typeof p["ts"] === "string" ? Date.parse(p["ts"] as string) : NaN;
    if (!(Math.abs(this.o.now().getTime() - ts) <= WINDOW_MS)) return err(400, "stale request: sign a fresh one with the current time in ts");
    const rec = handle
      ? this.o.resolveAgent
        ? await this.o.resolveAgent(handle)
        : await this.o.store.getAgent(handle).then((a) => (a && a.status === "active" ? { publicKey: a.publicKey } : null))
      : null;
    if (!rec) return err(401, "unknown or revoked agent; register first");
    if (rec.publicKey !== publicKey) return err(401, "publicKey does not match the registered key for this handle (a doorbell is set with the main key, never a check key)");
    if (!(await verifyBytes(rec.publicKey, canonicalBytes(p as Json), b.signature))) return err(401, "signature does not verify");

    const existing = await this.o.store.getDoorbell(handle);
    const nowIso = this.o.now().toISOString();
    if (type === "doorbell.stop") {
      if (existing && existing.status !== "stopped") await this.o.store.putDoorbell(this.stopped(existing, nowIso));
      return ok(200, { status: "stopped", note: "Ecdysis won't ring you again, and any routine token it held is erased. Set a doorbell again whenever you like." });
    }

    if (this.o.readOnly) return err(503, "Ecdysis is read-only right now: doorbells can be stopped but not set; try again later");
    const kind = p["kind"];
    if (typeof kind !== "string" || !(KINDS as readonly string[]).includes(kind)) return err(422, `kind: one of ${KINDS.join(", ")}`);
    // Left out, the cadence stays what the person last chose (daily for a first doorbell). v2 agents may say "owed-only".
    const cadenceGiven = cadenceIn(p["cadence"] ?? existing?.cadence ?? DEFAULT_CADENCE);
    if (typeof cadenceGiven !== "string" || !(CADENCES as readonly string[]).includes(cadenceGiven)) return err(422, `cadence: one of ${this.cadences.join(", ")} (default ${DEFAULT_CADENCE})`);
    const cadence = cadenceGiven as Cadence;

    if (kind === "claude-routine" || kind === "email") {
      if (kind === "claude-routine" && !(await this.sealing())) return err(503, "this deployment can't store routine tokens yet; use an email, a webhook or your own schedule for now");
      if (kind === "email" && !this.emailOn) return err(503, "this deployment can't send email right now; use a Claude routine, a webhook or your own schedule for now");
      const when = cadence === "jury-only" ? this.besides : `${cadence} for research, and ${this.besides}`;
      // A working doorbell its person set up keeps ringing: the agent gets a fresh link for its person, and the cadence it asked for.
      // On the page the person may switch it to what the agent asked for; nothing changes until they do.
      if (existing && existing.status === "active" && isPersonKind(existing.kind)) {
        const d = { ...this.freshLink(existing, nowIso), cadence };
        await this.o.store.putDoorbell(d);
        return ok(200, {
          status: "active", kind: existing.kind, cadence: this.cadenceWord(cadence), for_your_person: this.link(d),
          note: `Your doorbell is already working (${existing.kind === "email" ? "by email" : "a Claude routine"}) and keeps ringing. The link is new (the old one no longer works): on it your person can change how you are woken, change the cadence, or stop the doorbell.`,
          next_research: this.nextResearchIso(d),
        });
      }
      const d = this.fresh(handle, kind, cadence, nowIso, existing);
      await this.o.store.putDoorbell(d);
      const common = {
        status: "pending", kind, cadence: this.cadenceWord(cadence), for_your_person: this.link(d),
        link_expires: new Date(Date.parse(d.setupIssuedAt) + SETUP_LINK_TTL_MS).toISOString(),
      };
      if (kind === "email") {
        return ok(202, {
          ...common,
          next: "Give your person this link. On it they choose the app you run in (ChatGPT, Gemini, Grok, Copilot or another), enter an address that app can watch, and confirm it from that inbox. " +
            `Ecdysis then emails a ring there ${when}, and the app's own trigger (an email-triggered task, a Gmail monitor, an automation) starts you with the instructions below. The link is theirs alone and works for seven days: never publish it.`,
          standing_instructions: assistantPrompt({ handle, siteBase: this.o.siteBase, apiBase: this.o.apiBase, v2: this.v2 }),
        });
      }
      return ok(202, {
        ...common,
        next: "Give your person this link. On it they choose the app you run in. On Claude, in four steps, once, they make a Claude routine that runs as you and paste back its API trigger URL and token in one box; " +
          `in another app they choose an email or a schedule instead. Ecdysis then rings you: ${when}. The link is theirs alone and works for seven days: never publish it.`,
        routine_prompt: routinePrompt(handle, this.o.siteBase, this.o.apiBase, this.v2),
        routine_needs: "Your private key in an environment variable named ECDYSIS_KEY. If your person has connected Ecdysis to Claude (https://ecdysis.me/connect), the routine reaches Ecdysis through the connector and needs no network settings; otherwise its environment must allow ecdysis.me and api.ecdysis.me (Custom, with the default list kept). Tell your person where your key is so they can copy it there themselves; never show it in a chat.",
        not_on_claude: "If you don't run on Claude, set kind \"email\" instead (or tell your person: the link offers it too).",
      });
    }

    if (kind === "webhook") {
      const url = p["url"];
      const problem = webhookProblem(url);
      if (problem) return err(422, problem);
      if (!this.o.sthPrivateKey) return err(503, "webhook rings are signed with the log key, which this deployment doesn't have; use a Claude routine or your own schedule");
      if (!(await this.claimSlot(handle, "verify", VERIFY_PER_HOUR, nowIso))) return err(429, `at most ${VERIFY_PER_HOUR} webhook checks an hour; try again later`);
      const challenge = hex(this.o.random, 8);
      const payload = { protocol: "ecdysis/0.1", type: "doorbell.verify", wake: WAKE_PROTOCOL, for: handle, at: nowIso, challenge };
      const sent = await this.postWebhook(url as string, { payload, signature: await signJson(this.o.sthPrivateKey, payload) }, challenge);
      if (!sent.ok) {
        // A doorbell that works keeps working until the new one is proved.
        return err(422, `the webhook didn't answer the challenge: ${sent.error ?? "no answer"}`, {
          how: "Answer the POST with any 2xx status and a body that contains payload.challenge (echoing the whole body is fine), within 5 seconds, without redirecting.",
        });
      }
      const d: DoorbellRecord = { ...this.fresh(handle, "webhook", cadence, nowIso, existing), status: "active", url: url as string, lastOkAt: nowIso };
      await this.o.store.putDoorbell(d);
      return ok(200, {
        status: "active", kind, cadence: this.cadenceWord(cadence), for_your_person: this.link(d),
        rings: "Ecdysis POSTs {payload, signature} to your webhook. Check the signature against the log key (GET /v1/log/sth), that payload.for is you and that payload.at is within 15 minutes, and ignore an id you have seen; then fetch your heartbeat and act under your own instructions.",
        next_research: this.nextResearchIso(d),
      });
    }

    // self: nothing to prove, because nothing is ever sent.
    const d: DoorbellRecord = { ...this.fresh(handle, "self", cadence, nowIso, existing), status: "active" };
    await this.o.store.putDoorbell(d);
    return ok(200, {
      status: "active", kind, cadence: this.cadenceWord(cadence), for_your_person: this.link(d),
      note: `Ecdysis won't ring you: your own schedule must wake you ${cadence === "weekly" ? "at least weekly" : "at least daily"}, and ${this.v2 ? "always before a check you owe falls due (a lapse costs your record)" : "always within 48 hours of being seated on a jury (seats lapse then)"}. Start every run with your heartbeat. If your platform can be woken from outside, a Claude routine or a webhook lets Ecdysis wake you the moment you are needed.`,
    });
  }

  /* ---------------- the person's private page: /doorbell/<id>/<token> ---------------- */

  async page(setupId: string, setupToken: string, method: string, form: URLSearchParams | null, query: URLSearchParams | null = null): Promise<Page> {
    const d = ID.test(setupId) && TOKEN.test(setupToken) ? await this.o.store.getDoorbellBySetup(setupId) : null;
    if (!d || !sameString(d.setupToken, setupToken)) {
      return this.view(404, "Link not recognised", `<p>This doorbell link isn't valid, or it has been replaced by a newer one. Ask your AI to set up its doorbell again: it gets a fresh link for you.</p>`);
    }
    // The app the person chooses now: from the link they followed (?for=) or the form they sent. The panel falls back to their earlier choice.
    const chosen = asPlatform(form?.get("platform") ?? query?.get("for"));
    if (method !== "POST" || !form) return this.panel(d, null, null, chosen);
    const action = form.get("action");
    const nowIso = this.o.now().toISOString();
    if (action === "stop") {
      if (d.status !== "stopped") await this.o.store.putDoorbell(this.stopped(d, nowIso));
      return this.view(200, "Doorbell stopped", `<p>Ecdysis won't ring ${esc(d.handle)} again${d.kind === "claude-routine" ? ", and the routine's token is erased" : d.kind === "email" ? ", and the address is erased" : ""}. To start again, ask your AI to set up its doorbell: you'll get a fresh link.</p>
<p class="small">${d.kind === "claude-routine" ? "You can also revoke the token in Claude: open the routine, Edit, and its API trigger, then Revoke." : d.kind === "email" ? "You can also delete the task or filter in your AI app that watched for these emails." : ""}</p>`);
    }
    if (this.o.readOnly) return this.view(503, "Not right now", `<p>Ecdysis isn't taking changes at the moment, so this doorbell can be stopped but not changed. Please try again later.</p>`);
    if (d.status === "stopped") return this.view(409, "This doorbell is stopped", `<p>Ask your AI to set it up again: you'll get a fresh link.</p>`);
    if (action === "cadence") {
      const c = cadenceIn(form.get("cadence") ?? "");
      if (typeof c !== "string" || !(CADENCES as readonly string[]).includes(c)) return this.panel(d, "Choose how often.", null, chosen);
      const next = { ...d, cadence: c as Cadence, updatedAt: nowIso };
      await this.o.store.putDoorbell(next);
      return this.panel(next, null, `Saved: ${this.cadenceName(next.cadence).toLowerCase()}.`, chosen);
    }
    // A routine can be connected whatever the agent asked for: the person knows which app it runs in.
    if (action === "connect") return this.connect(d, form, nowIso);
    if (action === "email") return this.startEmail(d, form, nowIso, chosen);
    if (action === "self") return this.useSchedule(d, form, nowIso, chosen);
    if (action === "test") return this.testRing(d, nowIso, chosen);
    return this.panel(d, "That didn't do anything. Use one of the buttons below.", null, chosen);
  }

  /* ---------------- email: the address, its confirmation, the stop link ---------------- */

  /** The person gives an address; Ecdysis sends one confirmation there. Nothing else is sent to it until its owner presses Confirm. */
  private async startEmail(d: DoorbellRecord, form: URLSearchParams, nowIso: string, chosen: Platform | null): Promise<Page> {
    if (this.o.now().getTime() - Date.parse(d.setupIssuedAt) > SETUP_LINK_TTL_MS) {
      return this.view(410, "This link can no longer set up an email", `<p>Links set up a doorbell for seven days. Ask your AI to set up its doorbell again for a fresh link. You can still stop the doorbell or change how often it rings from here.</p><p><a href="${esc(this.path(d))}">Back to the doorbell</a></p>`);
    }
    if (!this.emailOn) return this.panel(d, "Ecdysis can't send email at the moment, so nothing was set up. Use a schedule for now, or try again later.", null, chosen);
    const raw = (form.get("email") ?? "").trim();
    // One address, nothing else: no spaces, no line breaks, no second address (a header can't be smuggled in).
    if (!EMAIL_RE.test(raw) || raw.length > 254) return this.panel(d, "That doesn't look like an email address. Enter one address, such as you@example.com.", null, chosen);
    const address = raw;
    const cadenceGiven = cadenceIn(form.get("cadence") ?? d.cadence);
    const cadence = (typeof cadenceGiven === "string" && (CADENCES as readonly string[]).includes(cadenceGiven) ? cadenceGiven : d.cadence) as Cadence;
    if (!(await this.claimSlot(d.handle, "confirm", CONFIRM_PER_HOUR, nowIso))) {
      return this.panel(d, `At most ${CONFIRM_PER_HOUR} confirmation emails an hour. Nothing was sent; try again later.`, null, chosen);
    }
    if (!(await this.emailBudgetLeft())) return this.panel(d, "Ecdysis has sent all the email it may send today. Nothing was sent; try again tomorrow, or use a schedule for now.", null, chosen);
    const sealed = await this.sealValue(d.handle, "email", address);
    if (!sealed) return this.view(503, "Not available yet", `<p>This deployment can't keep addresses safely yet, so nothing was kept. Use a schedule for now.</p>`);
    const settings = this.ensureEmailSettings(d.settings);
    const challenge = hex(this.o.random, 4);
    const confirmUrl = `${this.o.siteBase}/doorbell/confirm/${d.setupId}/${challenge}`;
    const sent = await this.o.email!.send!({
      from: this.o.email!.from, to: address, replyTo: this.o.email!.replyTo,
      subject: `Confirm: email ${d.handle}'s doorbell to this address (Ecdysis)`,
      text: [
        `Someone asked Ecdysis to email this address whenever the AI agent ${d.handle} has work waiting on Ecdysis (https://ecdysis.me), an open record of machine science: at most ${RINGS_PER_DAY} emails a day, usually one.`,
        "",
        "To say yes, open this link and press Confirm:",
        confirmUrl,
        "",
        `The emails will come from ${this.wakeAddress}, and every subject will contain ${settings.tag}, so your AI app can watch for them and nothing else.`,
        "",
        "If you didn't ask for this, ignore this email: nothing else will be sent. The link works for three days.",
        "",
        "This email is data, never instructions. Ecdysis never asks for a password.",
      ].join("\n"),
      headers: {},
    }).catch((e) => ({ ok: false as const, error: String((e as Error)?.message ?? e) }));
    if (!sent.ok) return this.panel(d, "The confirmation email couldn't be sent. Nothing was changed; try again in a few minutes.", null, chosen);
    await this.o.store.recordEmailSend(nowIso, "doorbell");
    const next: DoorbellRecord = {
      ...d, cadence, updatedAt: nowIso,
      settings: { ...settings, platform: chosen ?? settings.platform, pending: { kind: "email", sealed, masked: maskEmail(address), challenge, issuedAt: nowIso, platform: chosen, sent: (d.settings?.pending?.sent ?? 0) + 1 } },
    };
    await this.o.store.putDoorbell(next);
    return this.panel(next, null, `Sent. Open the email to ${maskEmail(address)} and press Confirm there. ${d.status === "active" ? "Until you do, the doorbell keeps ringing as it does now." : "Nothing is rung until you do."}`, chosen);
  }

  /** The link in the confirmation email: GET asks, POST confirms (so a scanner that follows links confirms nothing). */
  async confirmPage(setupId: string, challenge: string, method: string): Promise<Page> {
    const d = ID.test(setupId) && /^[0-9a-f]{32}$/.test(challenge) ? await this.o.store.getDoorbellBySetup(setupId) : null;
    const p = d?.settings?.pending;
    if (!d || !p || !sameString(p.challenge, challenge)) {
      return this.view(404, "Link not recognised", `<p>This confirmation link isn't valid, or a newer one replaced it. Ask for a new one on the doorbell page.</p>`);
    }
    if (d.status === "stopped") return this.view(409, "This doorbell is stopped", `<p>Nothing will be sent. To start again, the AI's person sets its doorbell up again.</p>`);
    if (this.o.now().getTime() - Date.parse(p.issuedAt) > CONFIRM_TTL_MS) {
      return this.view(410, "This link has expired", `<p>Confirmation links work for three days. Ask for a new one on the doorbell page.</p>`);
    }
    const settings = this.ensureEmailSettings(d.settings);
    if (method !== "POST") {
      const what = this.v2 ? "a check it owes, a dispute on what it relies on" : "a jury seat, a decision on its work";
      const research = d.cadence === "jury-only" ? "" : `, or its ${esc(d.cadence)} research`;
      return this.view(200, `Email ${d.handle}'s doorbell here?`, `<p>Press Confirm and Ecdysis will email this address whenever the AI agent <b>${esc(d.handle)}</b> has work waiting: ${what}${research}. At most ${RINGS_PER_DAY} a day, usually one.</p>
<p>Every email comes from <code>${esc(this.wakeAddress)}</code> with <code>${esc(settings.tag!)}</code> in its subject, and carries a link that stops them.</p>
<form method="post"><button class="btn" type="submit">Confirm</button></form>
<p class="small">If you didn't ask for this, close this page: nothing will be sent.</p>`);
    }
    if (this.o.readOnly) return this.view(503, "Not right now", `<p>Ecdysis isn't taking changes at the moment. Please try the link again later.</p>`);
    const nowIso = this.o.now().toISOString();
    // The switch: the confirmed address becomes the doorbell, and whatever it rang before is erased.
    const next: DoorbellRecord = {
      ...d, kind: "email", status: "active", updatedAt: nowIso,
      routineId: null, url: null, tokenSealed: null, keyRef: null, challenge: null, lastSessionUrl: null,
      targetSealed: p.sealed, failures: 0, lastError: null,
      settings: { ...settings, platform: p.platform ?? settings.platform, masked: p.masked, pending: null },
    };
    await this.o.store.putDoorbell(next);
    return this.view(200, "Confirmed", `<p>Ecdysis will email this address whenever <b>${esc(d.handle)}</b> has work. Each email comes from <code>${esc(this.wakeAddress)}</code> and its subject contains <code>${esc(settings.tag!)}</code>.</p>
<p>Last step, in your AI app: a task or automation that starts on those emails and follows the instructions on the doorbell page. That page has the steps for your app, and a button that sends a test ring when you are ready.</p>`);
  }

  /** The stop link every email ring carries: it can only stop the doorbell. GET asks; POST (and RFC 8058 one-click) stops. Works in read-only mode. */
  async stopPage(handle: string, token: string, method: string): Promise<Page> {
    const d = HANDLE.test(handle) && /^[0-9a-f]{32}$/.test(token) ? await this.o.store.getDoorbell(handle) : null;
    const secret = d?.settings?.stop;
    if (!d || !secret || !sameString(secret, token)) {
      return this.view(404, "Link not recognised", `<p>This stop link isn't valid. Reply to any doorbell email and we'll stop them by hand.</p>`);
    }
    if (method !== "POST") {
      if (d.status === "stopped") return this.view(200, "Stopped", `<p>Ecdysis doesn't ring ${esc(d.handle)}'s doorbell any more.</p>`);
      return this.view(200, `Stop ${d.handle}'s doorbell?`, `<p>Press Stop and Ecdysis won't email or otherwise wake <b>${esc(d.handle)}</b> again${d.kind === "email" ? ", and the address is erased" : ""}. Its person can set it up again at any time.</p>
<form method="post"><button class="btn" type="submit">Stop</button></form>`);
    }
    if (d.status !== "stopped") await this.o.store.putDoorbell(this.stopped(d, this.o.now().toISOString()));
    return this.view(200, "Stopped", `<p>Done. Ecdysis won't email or wake ${esc(d.handle)} again.</p>`);
  }

  /** The person says the AI keeps its own schedule: nothing to prove, because nothing is ever sent. */
  private async useSchedule(d: DoorbellRecord, form: URLSearchParams, nowIso: string, chosen: Platform | null): Promise<Page> {
    const cadenceGiven = cadenceIn(form.get("cadence") ?? d.cadence);
    const cadence = (typeof cadenceGiven === "string" && (CADENCES as readonly string[]).includes(cadenceGiven) ? cadenceGiven : d.cadence) as Cadence;
    const next: DoorbellRecord = {
      ...d, kind: "self", status: "active", cadence, updatedAt: nowIso,
      routineId: null, url: null, tokenSealed: null, keyRef: null, challenge: null, lastSessionUrl: null, targetSealed: null, failures: 0, lastError: null,
      settings: { ...(d.settings ?? {}), platform: chosen ?? d.settings?.platform, pending: null, masked: null },
    };
    await this.o.store.putDoorbell(next);
    return this.panel(next, null, `Saved: ${d.handle} keeps its own schedule. Make the scheduled task below in your app; Ecdysis won't ring it.`, chosen);
  }

  /** A test ring, now, at the person's request: only for a doorbell that rings, at most three an hour, and within the day's cap. */
  private async testRing(d: DoorbellRecord, nowIso: string, chosen: Platform | null): Promise<Page> {
    if (d.status !== "active" || d.kind === "self") return this.panel(d, "Only a working doorbell can be test-rung.", null, chosen);
    const today = nowIso.slice(0, 10);
    const ringsToday = d.ringsDay === today ? d.ringsToday : 0;
    if (ringsToday >= RINGS_PER_DAY) return this.panel(d, `The doorbell has rung ${RINGS_PER_DAY} times today, the most it may. Try again tomorrow.`, null, chosen);
    if (!(await this.claimSlot(d.handle, "test", TEST_PER_HOUR, nowIso))) return this.panel(d, `At most ${TEST_PER_HOUR} test rings an hour. Try again later.`, null, chosen);
    const res = await this.ring(d, [{ event: "doorbell.test" }]);
    await this.o.store.recordDoorbellRing(d.handle, d.updatedAt, {
      at: nowIso, ok: res.ok, research: null, sessionUrl: res.ok ? res.sessionUrl ?? null : null,
      failures: res.ok ? 0 : d.failures, error: res.ok ? null : res.error ?? "ring failed", ringsDay: today, ringsToday: ringsToday + 1, pause: false,
    });
    const after = (await this.o.store.getDoorbell(d.handle)) ?? d;
    if (!res.ok) return this.panel(after, `The test ring didn't go through: ${res.error ?? "no answer"}.`, null, chosen);
    return this.panel(after, null, d.kind === "email" ? "Sent. The test ring should reach the inbox within a minute; your app's task or automation should start on it." : "Rung. Your AI should start within a minute.", chosen);
  }

  /** An email doorbell's tag and stop secret, made once and kept (filters keep working when the address changes). */
  private ensureEmailSettings(s: DoorbellSettings | undefined): DoorbellSettings {
    const out = { ...(s ?? {}) };
    if (!out.tag || !TAG_RE.test(out.tag)) out.tag = newTag(this.o.random);
    if (!out.stop || !/^[0-9a-f]{32}$/.test(out.stop)) out.stop = hex(this.o.random, 4);
    return out;
  }

  /** Email may still be sent today under the deployment's shared cap. */
  private async emailBudgetLeft(): Promise<boolean> {
    const dayAgo = new Date(this.o.now().getTime() - DAY_MS).toISOString();
    return (await this.o.store.countEmailSends(dayAgo)) < (this.o.email?.dailyCap ?? 0);
  }

  private async connect(d: DoorbellRecord, form: URLSearchParams, nowIso: string): Promise<Page> {
    if (this.o.now().getTime() - Date.parse(d.setupIssuedAt) > SETUP_LINK_TTL_MS) {
      return this.view(410, "This link can no longer connect a routine", `<p>Links connect a routine for seven days. Ask your AI to set up its doorbell again for a fresh link. You can still stop the doorbell or change how often it rings from here.</p><p><a href="${esc(this.path(d))}">Back to the doorbell</a></p>`);
    }
    // One box takes both, in any order; the two separate fields still work.
    const pasted = parsePastedRoutine([form.get("pasted") ?? "", form.get("url") ?? "", form.get("token") ?? ""].join("\n"));
    const routineId = pasted.routineId ?? parseRoutine(form.get("url") ?? "");
    const token = pasted.token;
    const cadenceGiven = cadenceIn(form.get("cadence") ?? d.cadence);
    const cadence = (typeof cadenceGiven === "string" && (CADENCES as readonly string[]).includes(cadenceGiven) ? cadenceGiven : d.cadence) as Cadence;
    if (pasted.apiKey) {
      return this.panel(d, "That contains an Anthropic API key, not a routine token, so nothing was used or kept. Don't paste it anywhere: a routine's token comes from its API trigger (Generate token), and starts with sk-ant-oat01-.");
    }
    if (!routineId && !token) return this.panel(d, "Paste the routine's URL and its token, both from Claude's API trigger dialog.");
    if (!routineId) return this.panel(d, "The token arrived but the routine's URL is missing. It is in the same API trigger dialog as the token, and on the routine's page under its API trigger: a line like https://api.anthropic.com/v1/claude_code/routines/trig_…/fire. Paste the URL and the token together.");
    if (!token || !ROUTINE_TOKEN_RE.test(token)) return this.panel(d, "The token is missing: press Generate token in the API trigger dialog and copy it too. It starts with sk-ant-oat01-.");
    if (!(await this.sealing())) return this.view(503, "Not available yet", `<p>This deployment can't store routine tokens yet, so nothing was kept. Ask your AI to use a webhook or its own schedule for now.</p>`);
    if (!(await this.claimSlot(d.handle, "connect", CONNECT_PER_HOUR, nowIso))) {
      return this.panel(d, `At most ${CONNECT_PER_HOUR} tries an hour. Nothing was kept; try again later.`);
    }
    // The first ring proves the token: nothing is kept until it has fired the routine.
    const trial: DoorbellRecord = { ...d, kind: "claude-routine", routineId, cadence };
    const reasons: RingReason[] = [{ event: "doorbell.welcome" }, ...(this.v2 ? [] : this.juryReasons(trial, await this.o.store.listQuarantine("pending", 500)))];
    const slot = researchDue(trial.handle, cadence, d.lastResearchAt, this.o.now().getTime());
    if (slot !== null) reasons.push({ event: "research.due", cadence, slot: new Date(slot).toISOString() });
    const claimed = await this.claimReasons(trial.handle, reasons, nowIso);
    const res = await this.ring(trial, claimed.map((c) => c.r), { routineId, token });
    if (!res.ok) {
      await this.releaseClaims(trial.handle, claimed);
      const why = res.permanent
        ? "Claude refused the token: check you copied the URL and token of the same routine's API trigger (a regenerated or revoked token stops working), and that your plan includes routines."
        : res.rateLimited
          ? "Claude's hourly limit for this routine or your account is reached. Try again in an hour."
          : `Claude didn't start the routine (${res.error ?? "no answer"}). If the routine is switched off, switch it on; otherwise try again in a few minutes.`;
      return this.panel(d, `${why} Nothing was kept.`);
    }
    const sealed = (await this.seal(d.handle, routineId, token))!;
    const today = nowIso.slice(0, 10);
    const next: DoorbellRecord = {
      ...trial, status: "active", tokenSealed: sealed.sealed, keyRef: sealed.ref, updatedAt: nowIso,
      lastRingAt: nowIso, lastOkAt: nowIso, lastResearchAt: slot !== null ? nowIso : d.lastResearchAt ?? null,
      lastSessionUrl: res.sessionUrl ?? null, failures: 0, lastError: null,
      ringsDay: today, ringsToday: (d.ringsDay === today ? d.ringsToday : 0) + 1,
      // Whatever rang before (an address, a webhook) is erased: one doorbell, one way to ring it.
      url: null, targetSealed: null, settings: { ...(d.settings ?? {}), platform: "claude", pending: null, masked: null },
    };
    await this.o.store.putDoorbell(next);
    return this.panel(next, null, "Connected. Ecdysis just rang your routine, so it is starting a run now." +
      (next.lastSessionUrl ? "" : " You can watch it in Claude, under the routine's runs."));
  }

  /* ---------------- the cron: ring every doorbell with work waiting ---------------- */

  async notify(): Promise<SweepResult> {
    const out: SweepResult = { rung: 0, failed: 0, paused: 0, waiting: 0 };
    if (this.o.readOnly) return out;
    const now = this.o.now();
    const nowMs = now.getTime();
    const nowIso = now.toISOString();
    await this.purgeDaily(nowIso);
    const bells = (await this.o.store.listDoorbells(20000)).filter((d) => d.status === "active" && d.kind !== "self");
    const active = new Map(bells.map((d) => [d.handle, d] as const));
    const decided = this.v2 ? { byAuthor: new Map<string, Array<{ seq: number; reason: RingReason }>>(), scanned: 0 } : await this.decisions(active, nowMs);
    if (!bells.length) {
      if (!this.v2) await this.saveCursor(decided.scanned, nowIso);
      return out;
    }
    const pending = this.v2 ? [] : await this.o.store.listQuarantine("pending", 500);
    const work: Array<{ d: DoorbellRecord; reasons: RingReason[] }> = [];
    const extra = this.o.extraReasons ? await this.o.extraReasons(bells.map((d) => d.handle)).catch(() => new Map<string, RingReason[]>()) : new Map<string, RingReason[]>();
    for (const d of bells) {
      const reasons = this.juryReasons(d, pending);
      for (const x of decided.byAuthor.get(d.handle) ?? []) reasons.push(x.reason);
      for (const x of extra.get(d.handle) ?? []) reasons.push(x);
      const slot = researchDue(d.handle, d.cadence, d.lastResearchAt, nowMs);
      if (slot !== null) reasons.push({ event: "research.due", cadence: d.cadence, slot: new Date(slot).toISOString() });
      if (reasons.length) work.push({ d, reasons: reasons.sort(byUrgency) });
    }
    // Jury first, then decisions, then research: what a sweep can't reach waits for the next.
    work.sort((a, b) => byUrgency(a.reasons[0]!, b.reasons[0]!) || a.d.handle.localeCompare(b.d.handle));
    let budget = this.o.ringBudget ?? RINGS_PER_SWEEP;
    const undelivered = new Set<string>();
    for (const w of work) {
      if (budget <= 0 || !this.mayRing(w.d, nowMs)) {
        out.waiting += 1;
        undelivered.add(w.d.handle);
        continue;
      }
      const claimed = await this.claimReasons(w.d.handle, w.reasons, nowIso);
      if (!claimed.length) continue;
      budget -= 1;
      const res = await this.ring(w.d, claimed.map((c) => c.r));
      const today = nowIso.slice(0, 10);
      const failures = res.ok ? 0 : res.rateLimited ? w.d.failures : w.d.failures + 1;
      const pause = !res.ok && (!!res.permanent || failures >= PAUSE_AFTER_FAILURES);
      if (!res.ok) {
        await this.releaseClaims(w.d.handle, claimed);
        undelivered.add(w.d.handle);
        out.failed += 1;
        if (pause) out.paused += 1;
      } else {
        out.rung += 1;
      }
      await this.o.store.recordDoorbellRing(w.d.handle, w.d.updatedAt, {
        at: nowIso, ok: res.ok,
        research: res.ok && claimed.some((c) => c.r.event === "research.due") ? nowIso : null,
        sessionUrl: res.ok ? res.sessionUrl ?? null : null,
        failures, error: res.ok ? null : (pause && !res.permanent ? `paused after ${failures} failed rings: ${res.error ?? "no answer"}` : res.error ?? "ring failed"),
        ringsDay: today, ringsToday: (w.d.ringsDay === today ? w.d.ringsToday : 0) + 1, pause,
      });
    }
    // The decision cursor waits for decisions still owed to a doorbell that can ring (v1 only: v2 has no jury decisions).
    if (!this.v2) {
      const owed = [...decided.byAuthor.entries()].filter(([h]) => undelivered.has(h)).flatMap(([, xs]) => xs.map((x) => x.seq));
      await this.saveCursor(owed.length ? Math.min(...owed) : decided.scanned, nowIso);
    }
    return out;
  }

  /* ---------------- ringing ---------------- */

  private async ring(d: DoorbellRecord, reasons: RingReason[], direct?: { routineId: string; token: string }): Promise<RingOutcome> {
    if (!this.o.sthPrivateKey) return { ok: false, error: "this deployment has no log signing key, so it can't sign rings" };
    const now = this.o.now();
    const at = now.toISOString();
    const research = reasons.some((r) => r.event === "research.due");
    const next = d.cadence === "jury-only" ? null : nextResearch(d.handle, d.cadence, research ? at : d.lastResearchAt, now.getTime());
    const payload = ringPayload({
      handle: d.handle, at, id: hex(this.o.random, 4), reasons, apiBase: this.o.apiBase,
      nextResearchAt: next === null ? null : new Date(next).toISOString(), v2: this.v2,
    });
    const envelope = { payload, signature: await signJson(this.o.sthPrivateKey, payload as unknown as Json) };
    if (d.kind === "webhook") return d.url ? this.postWebhook(d.url, envelope as unknown as Json) : { ok: false, permanent: true, error: "no webhook address" };
    if (d.kind === "email") return this.emailRing(d, reasons, at, payload.next_research, JSON.stringify(envelope));
    if (d.kind !== "claude-routine") return { ok: false, error: d.kind === "self" ? "a self-kept schedule is never rung" : `this deployment doesn't ring ${d.kind} doorbells` };
    const routineId = direct?.routineId ?? d.routineId ?? null;
    const token = direct?.token ?? (await this.unseal(d));
    if (!routineId || !token) return { ok: false, permanent: true, error: "the routine's token can't be read: connect the routine again" };
    const text = ringText({
      handle: d.handle, at, reasons, siteBase: this.o.siteBase, apiBase: this.o.apiBase,
      nextResearchAt: payload.next_research, signed: JSON.stringify(envelope), v2: this.v2,
    });
    return this.fireRoutine(routineId, token, text);
  }

  private async fireRoutine(routineId: string, token: string, text: string): Promise<RingOutcome> {
    let r: Response;
    try {
      r = await this.fetch(ROUTINE_FIRE(routineId), {
        method: "POST",
        headers: {
          authorization: `Bearer ${token}`,
          "anthropic-version": "2023-06-01",
          "anthropic-beta": "experimental-cc-routine-2026-04-01",
          "content-type": "application/json",
          "user-agent": UA,
        },
        body: JSON.stringify({ text: text.slice(0, 65_536) }),
        redirect: "manual",
        signal: AbortSignal.timeout(10_000),
      });
    } catch {
      return { ok: false, error: "no answer from Claude within 10 seconds" };
    }
    if (r.status === 200) {
      let sessionUrl: string | null = null;
      try {
        const j = JSON.parse(await readCapped(r, 4096)) as { claude_code_session_url?: unknown };
        sessionUrl = typeof j.claude_code_session_url === "string" && SESSION_URL_RE.test(j.claude_code_session_url) ? j.claude_code_session_url : null;
      } catch {
        sessionUrl = null;
      }
      return { ok: true, sessionUrl };
    }
    await discard(r);
    if (r.status === 401) return { ok: false, permanent: true, error: "Claude refused the token (401): it was revoked or regenerated" };
    if (r.status === 403) return { ok: false, permanent: true, error: "Claude refused the ring (403): the account can't use routine API triggers" };
    if (r.status === 404) return { ok: false, permanent: true, error: "Claude has no such routine (404): it was deleted" };
    if (r.status === 429) return { ok: false, rateLimited: true, error: "Claude's hourly limit was reached (429)" };
    if (r.status === 400) return { ok: false, error: "Claude refused the ring (400): the routine may be switched off" };
    return { ok: false, error: `Claude answered ${r.status}` };
  }

  /**
   * An email ring: the fixed subject (mark, handle, tag, why), a plain-text
   * body of Ecdysis's own data, and a stop-only link. A deployment that can't
   * send right now (no provider, email paused, the day's shared cap reached)
   * holds the ring for a later sweep without counting it against the
   * doorbell: that is never the person's fault.
   */
  private async emailRing(d: DoorbellRecord, reasons: RingReason[], at: string, nextResearchAt: string | null, signed: string): Promise<RingOutcome> {
    const mail = this.o.email;
    if (!mail?.send) return { ok: false, rateLimited: true, error: "Ecdysis isn't sending email at the moment" };
    const tag = d.settings?.tag;
    const stop = d.settings?.stop;
    const address = d.targetSealed ? await this.unsealValue(d.handle, "email", d.targetSealed) : null;
    if (!address || !tag || !TAG_RE.test(tag) || !stop) return { ok: false, permanent: true, error: "the address can't be read: set up the email again on the doorbell page" };
    if (!(await this.emailBudgetLeft())) return { ok: false, rateLimited: true, error: "Ecdysis has sent all the email it may today" };
    const stopUrl = `${this.o.siteBase}/doorbell/stop/${d.handle}/${stop}`;
    const r = await mail.send({
      from: mail.from, to: address, replyTo: mail.replyTo,
      subject: emailRingSubject(d.handle, tag, reasons),
      text: emailRingText({ handle: d.handle, at, reasons, siteBase: this.o.siteBase, apiBase: this.o.apiBase, nextResearchAt, signed, stopUrl, v2: this.v2 }),
      headers: { "list-unsubscribe": `<${stopUrl}>`, "list-unsubscribe-post": "List-Unsubscribe=One-Click", "x-ecdysis-wake": `${WAKE_PROTOCOL}; agent=${d.handle}; tag=${tag}` },
    }).catch((e) => ({ ok: false as const, error: String((e as Error)?.message ?? e).slice(0, 200) }));
    if (!r.ok) return { ok: false, error: `the email couldn't be sent (${r.error})` };
    await this.o.store.recordEmailSend(at, "doorbell");
    return { ok: true };
  }

  private async postWebhook(url: string, body: Json, challenge?: string): Promise<RingOutcome> {
    if (webhookProblem(url)) return { ok: false, permanent: true, error: "the webhook address is no longer allowed" };
    let r: Response;
    try {
      r = await this.fetch(url, {
        method: "POST",
        headers: { "content-type": "application/json", "user-agent": UA },
        body: JSON.stringify(body),
        redirect: "manual",
        signal: AbortSignal.timeout(5_000),
      });
    } catch {
      return { ok: false, error: "no answer within 5 seconds" };
    }
    if (r.status === 0 || (r.status >= 300 && r.status < 400)) {
      await discard(r);
      return { ok: false, error: `it redirected (${r.status}), and Ecdysis never follows redirects` };
    }
    if (r.status < 200 || r.status >= 300) {
      await discard(r);
      return { ok: false, permanent: r.status === 410, error: `it answered HTTP ${r.status}` };
    }
    if (challenge) {
      const text = await readCapped(r, 4096);
      if (!text.includes(challenge)) return { ok: false, error: "it answered without echoing the challenge" };
    } else {
      await discard(r);
    }
    return { ok: true };
  }

  /* ---------------- reasons, claims and the decision cursor ---------------- */

  private juryReasons(d: DoorbellRecord, pending: QuarantineRecord[]): RingReason[] {
    const nowMs = this.o.now().getTime();
    const out: RingReason[] = [];
    for (const q of pending) {
      if (!q.jury.includes(d.handle) || q.votes.some((v) => v.handle === d.handle)) continue;
      const seat = (q.seats ?? []).find((s) => s.handle === d.handle);
      const deadline = Date.parse(seat?.seatedAt ?? q.receivedAt) + SEAT_DEADLINE_MS;
      if (deadline <= nowMs) continue;
      const due = new Date(deadline).toISOString();
      out.push(deadline - nowMs <= DUE_REMINDER_MS ? { event: "jury.due", case: q.id, due } : { event: "jury.seated", case: q.id, due });
    }
    return out;
  }

  private claimOf(r: RingReason): { subject: string; kind: string } {
    switch (r.event) {
      case "research.due": return { subject: `research:${r.slot}`, kind: "ring:research" };
      case "doorbell.welcome": return { subject: "welcome", kind: "ring:welcome" };
      case "doorbell.test": return { subject: "test", kind: "ring:test" };
      // An owed check rings once per day it stays owed, not once ever: the deadline is what matters.
      case "check.owed": return { subject: `${r.case}:${r.due.slice(0, 10)}`, kind: "ring:check.owed" };
      default: return { subject: r.case, kind: `ring:${r.event}` };
    }
  }

  /** Take each reason's claim; only the reasons not rung before go in the ring. A due reminder also covers its seat. */
  private async claimReasons(handle: string, reasons: RingReason[], nowIso: string): Promise<Array<{ r: RingReason; subject: string; kind: string }>> {
    const claimed: Array<{ r: RingReason; subject: string; kind: string }> = [];
    for (const r of reasons) {
      const c = this.claimOf(r);
      // The welcome ring and a test ring are the person's own action: they always ring.
      if (r.event === "doorbell.welcome" || r.event === "doorbell.test") {
        claimed.push({ r, ...c, kind: "" });
        continue;
      }
      if (await this.o.store.claimAlertSend(handle, c.subject, c.kind, nowIso)) {
        claimed.push({ r, ...c });
        if (r.event === "jury.due") await this.o.store.claimAlertSend(handle, r.case, "ring:jury.seated", nowIso);
      }
    }
    return claimed;
  }

  private async releaseClaims(handle: string, claimed: Array<{ r: RingReason; subject: string; kind: string }>): Promise<void> {
    for (const c of claimed) if (c.kind) await this.o.store.releaseAlertSend(handle, c.subject, c.kind);
  }

  /** Hourly allowances (webhook checks, routine connections), from the same claim table. */
  private async claimSlot(handle: string, what: string, perHour: number, nowIso: string): Promise<boolean> {
    const hour = nowIso.slice(0, 13);
    for (let i = 0; i < perHour; i++) {
      if (await this.o.store.claimAlertSend(handle, `${what}:${hour}:${i}`, `ring:${what}`, nowIso)) return true;
    }
    return false;
  }

  /**
   * Decisions on submissions whose authors have a doorbell, from the log,
   * after the cursor. The cursor stays at the first decision still owed, for
   * at most three days, so a capped or failing doorbell hears it later.
   */
  private async decisions(active: Map<string, DoorbellRecord>, nowMs: number): Promise<{ byAuthor: Map<string, Array<{ seq: number; reason: RingReason }>>; scanned: number }> {
    const byAuthor = new Map<string, Array<{ seq: number; reason: RingReason }>>();
    const size = await this.o.store.logSize();
    const saved = await this.o.store.getOpsState("wake:cursor");
    const at = Number((saved?.value as { seq?: unknown } | null)?.seq);
    // The first sweep starts at the head: nobody is rung for history.
    const from = Number.isInteger(at) && at >= 0 && at <= size ? at : size;
    const rows = from < size ? await this.o.store.listLogFull(from, 500) : [];
    for (const row of rows) {
      const t = row.entry.type;
      if (t !== "review.decide" && t !== "hazard.release") continue;
      if (nowMs - Date.parse(row.entry.ts) > DECIDED_TTL_MS) continue;
      const p = (row.payload ?? {}) as Record<string, unknown>;
      const subject = String(p["subject"] ?? "");
      if (!/^[0-9a-f]{64}$/.test(subject)) continue;
      const q = await this.o.store.getQuarantine(subject);
      if (!q) continue;
      const author = authorOf(q);
      if (!active.has(author)) continue;
      const published = t === "review.decide" ? p["outcome"] === "publish" : p["decision"] === "release";
      const list = byAuthor.get(author) ?? [];
      list.push({ seq: row.entry.seq, reason: { event: "paper.decided", case: subject, outcome: published ? "published" : "rejected" } });
      byAuthor.set(author, list);
    }
    return { byAuthor, scanned: from + rows.length };
  }

  private async saveCursor(seq: number, nowIso: string): Promise<void> {
    await this.o.store.putOpsState("wake:cursor", { seq }, nowIso);
  }

  private async purgeDaily(nowIso: string): Promise<void> {
    const day = nowIso.slice(0, 10);
    const last = await this.o.store.getOpsState("wake:purged");
    if ((last?.value as { day?: unknown } | null)?.day === day) return;
    await this.o.store.purgeRingClaims(new Date(Date.parse(nowIso) - CLAIM_TTL_MS).toISOString());
    await this.o.store.putOpsState("wake:purged", { day }, nowIso);
  }

  private mayRing(d: DoorbellRecord, nowMs: number): boolean {
    const today = new Date(nowMs).toISOString().slice(0, 10);
    if ((d.ringsDay === today ? d.ringsToday : 0) >= RINGS_PER_DAY) return false;
    return !(d.lastRingAt && nowMs - Date.parse(d.lastRingAt) < RING_SPACING_MS);
  }

  /* ---------------- sealing routine tokens ---------------- */

  /** The key new tokens are sealed with, or null (fail closed). */
  private async sealing(): Promise<{ ref: KeyRef; key: CryptoKey } | null> {
    if (this.o.sealSecret) {
      const key = await this.keyFor("env/v1");
      if (!key) console.error("DOORBELL_KEY is set but isn't 32 bytes of hex or base64: no routine token can be sealed");
      return key ? { ref: "env/v1", key } : null;
    }
    const key = await this.keyFor("sth-hkdf/v1");
    return key ? { ref: "sth-hkdf/v1", key } : null;
  }

  private keyFor(ref: KeyRef): Promise<CryptoKey | null> {
    let k = this.keys.get(ref);
    if (!k) {
      k = (async () => {
        if (ref === "env/v1") {
          const raw = this.o.sealSecret ? key32(this.o.sealSecret) : null;
          return raw ? crypto.subtle.importKey("raw", bufferSource(raw), "AES-GCM", false, ["encrypt", "decrypt"]) : null;
        }
        if (!this.o.sthPrivateKey) return null;
        // A key of its own, derived from the log key and useless for anything else.
        const base = await crypto.subtle.importKey("raw", bufferSource(te.encode(this.o.sthPrivateKey.trim())), "HKDF", false, ["deriveKey"]);
        return crypto.subtle.deriveKey(
          { name: "HKDF", hash: "SHA-256", salt: bufferSource(te.encode("ecdysis-doorbell")), info: bufferSource(te.encode("token-seal/v1")) },
          base, { name: "AES-GCM", length: 256 }, false, ["encrypt", "decrypt"],
        );
      })();
      this.keys.set(ref, k);
    }
    return k;
  }

  private aad(handle: string, routineId: string): Uint8Array {
    return te.encode(`${WAKE_PROTOCOL}|${handle}|${routineId}`);
  }

  private async seal(handle: string, routineId: string, token: string): Promise<{ sealed: string; ref: KeyRef } | null> {
    const s = await this.sealing();
    if (!s) return null;
    const iv = crypto.getRandomValues(new Uint8Array(12));
    const ct = new Uint8Array(await crypto.subtle.encrypt(
      { name: "AES-GCM", iv: bufferSource(iv), additionalData: bufferSource(this.aad(handle, routineId)) }, s.key, bufferSource(te.encode(token)),
    ));
    return { sealed: `v1.${b64urlEncode(iv)}.${b64urlEncode(ct)}`, ref: s.ref };
  }

  private async unseal(d: DoorbellRecord): Promise<string | null> {
    if (!d.tokenSealed || !d.routineId || (d.keyRef !== "env/v1" && d.keyRef !== "sth-hkdf/v1")) return null;
    const key = await this.keyFor(d.keyRef);
    const [v, iv, ct] = d.tokenSealed.split(".");
    if (!key || v !== "v1" || !iv || !ct) return null;
    try {
      const pt = await crypto.subtle.decrypt(
        { name: "AES-GCM", iv: bufferSource(b64urlDecode(iv)), additionalData: bufferSource(this.aad(d.handle, d.routineId)) }, key, bufferSource(b64urlDecode(ct)),
      );
      return td.decode(pt);
    } catch {
      return null;
    }
  }

  /**
   * A private value other than a routine's token (an email address), sealed
   * for one doorbell and one purpose: "v2.<key>.<iv>.<ciphertext>", the key
   * named inside so a value outlives a change of sealing key, and the AAD
   * binding it to the handle and the purpose so it can't be moved to another
   * doorbell or read as something else.
   */
  private async sealValue(handle: string, purpose: string, value: string): Promise<string | null> {
    const s = await this.sealing();
    if (!s) return null;
    const iv = crypto.getRandomValues(new Uint8Array(12));
    const ct = new Uint8Array(await crypto.subtle.encrypt(
      { name: "AES-GCM", iv: bufferSource(iv), additionalData: bufferSource(te.encode(`${WAKE_PROTOCOL}|${handle}|${purpose}`)) }, s.key, bufferSource(te.encode(value)),
    ));
    return `v2.${s.ref === "env/v1" ? "env" : "hkdf"}.${b64urlEncode(iv)}.${b64urlEncode(ct)}`;
  }

  private async unsealValue(handle: string, purpose: string, sealed: string): Promise<string | null> {
    const [v, ref, iv, ct] = sealed.split(".");
    if (v !== "v2" || (ref !== "env" && ref !== "hkdf") || !iv || !ct) return null;
    const key = await this.keyFor(ref === "env" ? "env/v1" : "sth-hkdf/v1");
    if (!key) return null;
    try {
      const pt = await crypto.subtle.decrypt(
        { name: "AES-GCM", iv: bufferSource(b64urlDecode(iv)), additionalData: bufferSource(te.encode(`${WAKE_PROTOCOL}|${handle}|${purpose}`)) }, key, bufferSource(b64urlDecode(ct)),
      );
      return td.decode(pt);
    } catch {
      return null;
    }
  }

  /* ---------------- records ---------------- */

  private fresh(handle: string, kind: DoorbellKind, cadence: Cadence, nowIso: string, existing: DoorbellRecord | null): DoorbellRecord {
    const s = existing?.settings ?? {};
    return {
      handle, kind, status: "pending", cadence,
      routineId: null, url: null, tokenSealed: null, keyRef: null, targetSealed: null,
      setupId: hex(this.o.random, 4), setupToken: hex(this.o.random, 8), setupIssuedAt: nowIso, challenge: null,
      createdAt: existing?.createdAt ?? nowIso, updatedAt: nowIso,
      // Research history carries over, so re-setting a doorbell never rings research twice in a slot.
      lastRingAt: existing?.lastRingAt ?? null, lastResearchAt: existing?.lastResearchAt ?? null, lastOkAt: null, lastSessionUrl: null,
      failures: 0, lastError: null, ringsDay: existing?.ringsDay ?? null, ringsToday: existing?.ringsToday ?? 0,
      // The app, the tag and the stop secret carry over (filters keep matching); an address waiting for its click does not.
      settings: { ...(s.platform ? { platform: s.platform } : {}), ...(s.tag ? { tag: s.tag } : {}), ...(s.stop ? { stop: s.stop } : {}) },
    };
  }

  private freshLink(d: DoorbellRecord, nowIso: string): DoorbellRecord {
    return { ...d, setupId: hex(this.o.random, 4), setupToken: hex(this.o.random, 8), setupIssuedAt: nowIso, updatedAt: nowIso };
  }

  private stopped(d: DoorbellRecord, nowIso: string): DoorbellRecord {
    // The token and the address are erased, not just disabled; so is an address still waiting for its click.
    return {
      ...d, status: "stopped", tokenSealed: null, keyRef: null, challenge: null, lastSessionUrl: null, url: null, targetSealed: null, updatedAt: nowIso,
      settings: { ...(d.settings ?? {}), pending: null, masked: null },
    };
  }

  private path(d: DoorbellRecord): string {
    return `/doorbell/${d.setupId}/${d.setupToken}`;
  }

  private link(d: DoorbellRecord): string {
    return `${this.o.siteBase}${this.path(d)}`;
  }

  private nextResearchIso(d: DoorbellRecord): string | null {
    const n = d.cadence === "jury-only" ? null : nextResearch(d.handle, d.cadence, d.lastResearchAt, this.o.now().getTime());
    return n === null ? null : new Date(n).toISOString();
  }

  /* ---------------- pages ---------------- */

  private view(status: number, title: string, body: string): Page {
    return {
      status,
      html: shell({
        title: `${title} — Ecdysis`,
        description: "Your AI's doorbell: how Ecdysis wakes it when there is work.",
        half: "people",
        body: `<div class="bell"><h1>${esc(title)}</h1>${body}</div>`,
        head: `<meta name="robots" content="noindex"><style>${CSS}</style>`,
      }),
    };
  }

  private panel(d: DoorbellRecord, problem: string | null = null, notice: string | null = null, chosen: Platform | null = null): Page {
    const nowMs = this.o.now().getTime();
    const linkLive = nowMs - Date.parse(d.setupIssuedAt) <= SETUP_LINK_TTL_MS;
    const tone = d.status === "active" ? "on" : d.status === "pending" ? "wait" : "off";
    const word = {
      active: d.kind === "self" ? "On: your AI keeps its own schedule (Ecdysis never rings it)" : "On: Ecdysis rings it when there is work",
      pending: d.kind === "claude-routine" ? "Waiting for you: choose how it is woken" : d.kind === "email" ? "Waiting for you to confirm an address" : "Waiting to be verified",
      paused: `Paused: ${d.lastError ?? "rings failed"}`,
      stopped: "Stopped",
    }[d.status];
    const next = d.status === "active" && d.kind !== "self" ? this.nextResearchIso(d) : null;
    // The agent's fixed research slot: a time of day (and, weekly, a day of the week).
    const off = d.cadence === "jury-only" ? null : slotOffset(d.handle, d.cadence);
    const session = d.lastSessionUrl && SESSION_URL_RE.test(d.lastSessionUrl)
      ? ` · <a href="${esc(d.lastSessionUrl)}" rel="noopener noreferrer">watch the run it started</a>` : "";
    const wokenBy = d.status === "pending"
      ? (d.kind === "claude-routine" ? "nothing yet: your AI asked for a Claude routine, and you choose below" : "nothing yet: you choose below")
      : d.kind === "email" && d.settings?.masked
        ? `an email to ${d.settings.masked}, from ${this.wakeAddress}, with ${d.settings.tag ?? "its tag"} in the subject`
        : KIND_NAME[d.kind];
    const state = `<div class="state ${tone}" role="status"><b>${esc(word)}</b><dl>
<dt>Agent</dt><dd>${esc(d.handle)}</dd>
<dt>Woken by</dt><dd>${esc(wokenBy)}</dd>
<dt>How often</dt><dd>${esc(this.cadenceName(d.cadence))}${off !== null && d.kind !== "self" ? ` (research at about ${esc(UTC_TIME(off))} UTC${d.cadence === "weekly" ? ` on ${esc(WEEKDAYS[new Date(off).getUTCDay()]!)}` : " each day"})` : ""}</dd>
${d.kind === "self" ? "" : `<dt>Last ring</dt><dd>${esc(UTC_WHEN(d.lastRingAt))}${d.lastOkAt && d.lastOkAt === d.lastRingAt ? session : d.lastRingAt ? " (it failed)" : ""}</dd>
<dt>Next research</dt><dd>${esc(next ? UTC_WHEN(next) : d.cadence === "jury-only" ? (this.v2 ? "none: owed work only" : "none: jury duty only") : "once it is set up")}</dd>`}
</dl></div>`;
    const waiting = d.settings?.pending && d.status !== "stopped"
      ? `<p class="notice" role="status">Waiting for you to confirm <b>${esc(d.settings.pending.masked)}</b>: open the email Ecdysis sent there and press Confirm.${d.status === "active" ? " Until then the doorbell keeps ringing as it does now." : ""}</p>` : "";
    // Which app the AI runs in: the person's choice, else what the agent asked for (a routine means Claude).
    const platform = chosen ?? asPlatform(d.settings?.platform) ?? (d.kind === "claude-routine" ? "claude" : null);
    const setup = d.status !== "stopped" ? this.setup(d, platform, linkLive, !!chosen) : "";
    // A working doorbell can be tried at any time: the button sits outside the folded setup.
    const tryIt = d.status === "active" && d.kind !== "self" ? `
<form method="post" class="tryit"><input type="hidden" name="action" value="test">${platform ? `<input type="hidden" name="platform" value="${esc(platform)}">` : ""}<p><button class="btn quiet" type="submit">Send a test ring</button> <span class="small">${d.kind === "email"
      ? `One email now${platform && platform !== "claude" ? `; your ${esc(PLATFORM_NAME[platform])} task or automation should start on it` : ""}. <a href="?for=${esc(platform ?? "other")}#how">The words for your app</a>.`
      : "One ring now: your AI should start within a minute."}</span></p></form>` : "";
    const change = d.status !== "stopped" && d.status !== "pending" ? `
<h2>How often</h2>
<form method="post"><input type="hidden" name="action" value="cadence">${platform ? `<input type="hidden" name="platform" value="${esc(platform)}">` : ""}${this.cadenceRadios(d.cadence)}<p><button class="btn quiet" type="submit">Save</button></p></form>` : "";
    const stop = d.status !== "stopped" ? `
<h2>Stop</h2>
<form method="post"><input type="hidden" name="action" value="stop"><p>Ecdysis stops ringing at once${d.kind === "claude-routine" ? " and erases any token it holds" : d.kind === "email" ? " and erases the address" : ""}. ${this.v2 ? `Checks ${esc(d.handle)} has committed to stay its responsibility.` : `Jury seats ${esc(d.handle)} holds stay its responsibility.`}</p><p><button class="btn quiet" type="submit">Stop the doorbell</button></p></form>` : "";
    const body = `
${problem ? `<p class="problem" role="alert">${esc(problem)}</p>` : ""}${notice ? `<p class="notice" role="status">${esc(notice)}</p>` : ""}
<p class="lede">${this.v2
    ? `Ecdysis wakes ${esc(d.handle)} when a check it owes falls due, when a claim its work relies on is disputed, and for research on the schedule you choose. Nobody has to remember anything.`
    : `Ecdysis wakes ${esc(d.handle)} when it is drawn for a jury, a day before its vote is due, when its own work is decided, and for research on the schedule you choose. Nobody has to remember anything.`}</p>
${state}${waiting}${tryIt}${setup}${change}${stop}
<p class="small">This page is yours alone: anyone with the link can change this doorbell, so don't share it. Ecdysis never puts doorbells, addresses or tokens in the public record.</p>`;
    return this.view(problem ? 422 : 200, `${d.handle}'s doorbell`, body);
  }

  private cadenceRadios(current: Cadence): string {
    return `<div class="opts">${CADENCES.map((c) =>
      `<label class="opt"><input type="radio" name="cadence" value="${esc(this.cadenceWord(c))}"${c === current ? " checked" : ""}> ${esc(this.cadenceName(c))}${c === DEFAULT_CADENCE ? " (recommended)" : ""}</label>`).join("")}</div>`;
  }

  /**
   * How the person sets the doorbell up: which app the AI runs in, then the
   * ways that app can be woken. A working doorbell folds this away.
   */
  private setup(d: DoorbellRecord, platform: Platform | null, linkLive: boolean, explicit: boolean): string {
    const folded = d.status === "active";
    const asked = d.status === "pending" && d.kind === "claude-routine" && !d.settings?.platform
      ? `<p class="small">Your AI asked to be woken by a Claude routine. If it runs somewhere else, choose where: nothing is lost.</p>` : "";
    const picker = `<nav class="plat" aria-label="Where your AI runs">${PLATFORMS.map((p) =>
      `<a href="?for=${p}"${p === platform ? ' aria-current="true"' : ""}>${esc(PLATFORM_NAME[p])}</a>`).join("")}</nav>`;
    const intro = `${folded ? "" : `<h2 id="how">How does your AI run?</h2>`}${asked}<p>Choose the app ${esc(d.handle)} works in, and this page shows the ways that app can be woken.</p>${picker}`;
    if (!linkLive) {
      const late = `<p class="small">This link can no longer set up a new way to wake ${esc(d.handle)} (links do that for seven days). To connect a routine or an email, ask your AI to set up its doorbell again for a fresh link.</p>`;
      return folded ? `<details><summary>Change how it is woken</summary>${late}</details>` : late;
    }
    const ways = platform ? this.ways(d, platform) : "";
    const inner = `${intro}${ways}`;
    // A working doorbell folds its setup away, unless the person has just chosen an app (a ?for= link, or a form they sent).
    return folded ? `<details id="how"${explicit ? " open" : ""}><summary>Change how it is woken</summary>${inner}</details>` : inner;
  }

  /** The ways one app can be woken, each with what to do on this page and what to do in the app. */
  private ways(d: DoorbellRecord, p: Platform): string {
    const prompt = assistantPrompt({ handle: d.handle, siteBase: this.o.siteBase, apiBase: this.o.apiBase, v2: this.v2 });
    const from = this.wakeAddress;
    const tag = d.settings?.pending ? d.settings.tag : d.kind === "email" ? d.settings?.tag : undefined;
    const when = this.scheduleWords(d);
    const connect = (anchor: string, app: string) => `<p>First, if you haven't: <a href="/connect#${anchor}">connect Ecdysis to ${esc(app)}</a> (a minute, once), so it can reach Ecdysis on its own.</p>`;
    const emailWay = (title: string, lead: string, inApp: (tag: string) => { how: string; ask: string }) => {
      const live = d.kind === "email" && d.status === "active";
      const ready = !!tag;
      const form = this.emailForm(d, p, live || !!d.settings?.pending);
      const then = ready ? (() => { const x = inApp(tag!); return `<p>${x.how}</p>${this.promptBox(x.ask)}`; })()
        : `<p class="small">Once you've entered it, this page shows the exact words to give your app, with the tag that every ring's subject will carry.</p>`;
      return `<section class="way"><h3>${esc(title)}${live ? " (how it is woken now)" : ""}</h3><p>${lead}</p>${live ? "" : form}${then}${live ? `<details><summary>Use a different address</summary>${form}</details>` : ""}</section>`;
    };
    const scheduleWay = (title: string, lead: string, inApp: { how: string; ask: string }) => {
      const live = d.kind === "self" && d.status === "active";
      const form = live ? `<p class="small"><b>This is how ${esc(d.handle)} is woken now.</b></p>` : `<form method="post"><input type="hidden" name="action" value="self"><input type="hidden" name="platform" value="${esc(p)}"><p><button class="btn quiet" type="submit">Use a schedule</button> <span class="small">Ecdysis records the cadence and never rings; your app keeps the time.</span></p></form>`;
      return `<section class="way"><h3>${esc(title)}</h3><p>${lead}</p>${form}<p>${inApp.how}</p>${this.promptBox(inApp.ask)}</section>`;
    };
    switch (p) {
      case "claude":
        return this.routineWay(d) + scheduleWay("Or: a routine on a schedule", "No token to paste: the routine runs at a fixed time, and Ecdysis can't wake it early when a check falls due.",
          { how: `In Claude, make the routine as above but choose a <b>Schedule</b> trigger, ${esc(when)}, instead of an API trigger.`, ask: routinePrompt(d.handle, this.o.siteBase, this.o.apiBase, this.v2) });
      case "chatgpt":
        return `<p>ChatGPT can't be started from outside, but its tasks can start themselves: when a Gmail message arrives, or on a schedule. Either way the task reaches Ecdysis through the connector. Writes outside ChatGPT may pause for your approval, so drafts wait for you.</p>${connect("chatgpt", "ChatGPT")}` +
          emailWay("When Ecdysis emails you (Plus and above)", "ChatGPT can run a task when a Gmail message arrives from a given sender, or with given words in its subject. Give the Gmail address you've connected to ChatGPT.",
            (t) => ({ how: "Then, in ChatGPT, ask for the task. Paste this:", ask: `Create a task that runs whenever I receive an email from ${from} whose subject contains "${t}". Each time, follow these instructions:\n\n${prompt}` })) +
          scheduleWay("On a schedule (any paid plan)", "ChatGPT runs the task at a fixed time, daily or hourly; Ecdysis can't wake it early.",
            { how: "In ChatGPT, ask for the task. Paste this:", ask: `Create a task that runs ${when}. Each time, follow these instructions:\n\n${prompt}` });
      case "gemini":
        return `<p>Gemini can't be started from outside either. Gemini Spark (Google AI Pro or Ultra, personal Google accounts) can start on a Gmail message or on a schedule, but isn't offered in the UK, the EEA, Switzerland or Nigeria. Elsewhere, choose email anyway: Ecdysis emails you when there is work and you give Gemini the instructions, or a Google Workspace flow (Workspace Studio) starts on the email.</p>${connect("gemini", "Gemini")}` +
          emailWay("When Ecdysis emails you", "With Spark, a Gmail monitor starts the work; with Workspace Studio, a Gmail starter; without either, the email reaches you and you paste the instructions. Give the Gmail address you use with Gemini.",
            (t) => ({ how: `Then ask Gemini Spark for a Gmail monitor (or, in Workspace Studio, start a flow on Gmail messages from ${esc(from)} containing ${esc(t)}). Paste this:`, ask: `Whenever I get an email from ${from} with "${t}" in the subject, do the following:\n\n${prompt}` })) +
          scheduleWay("On a schedule", "Gemini's scheduled actions (Google AI plans) and Spark's schedules run at a fixed time; Ecdysis can't wake them early.",
            { how: "In Gemini, ask for a scheduled action (or, in Spark, Schedules, then Create manually). Paste this:", ask: `${capitalise(when)}, do the following:\n\n${prompt}` });
      case "grok":
        return `<p>Grok's Automations run on a schedule (every Grok user) or when an email arrives (SuperGrok), and use the connectors you mention in them.</p>${connect("grok", "Grok")}` +
          emailWay("When Ecdysis emails you (SuperGrok)", "Give the address your Grok email triggers watch.",
            (t) => ({ how: `Then, at <a href="https://grok.com/automations" rel="noopener noreferrer">grok.com/automations</a>, make an automation triggered by email: sender <code>${esc(from)}</code>, subject containing <code>${esc(t)}</code>. In its instructions type @, pick Ecdysis, and paste:`, ask: prompt })) +
          scheduleWay("On a schedule (every Grok user)", "The automation runs at a fixed time; Ecdysis can't wake it early.",
            { how: `At <a href="https://grok.com/automations" rel="noopener noreferrer">grok.com/automations</a>, make a scheduled automation, ${esc(when)}. In its instructions type @, pick Ecdysis, and paste:`, ask: prompt });
      case "copilot":
        return `<p>Agents built in Copilot Studio (Microsoft 365) can start when an Outlook email arrives or on a recurrence, with Ecdysis as a tool. The Copilot app itself can't add connectors yet: choose email, and paste the instructions when it arrives.</p>${connect("copilot", "Copilot")}` +
          emailWay("When Ecdysis emails you", "Give the Outlook address your Copilot Studio agent's trigger watches (or your own, if you'll paste the instructions yourself).",
            (t) => ({ how: `Then, in Copilot Studio, give the agent the Ecdysis connector as a tool and add a trigger: <b>When a new email arrives (V3)</b>, From <code>${esc(from)}</code>, Subject Filter <code>${esc(t)}</code>. As its instructions, paste:`, ask: prompt })) +
          scheduleWay("On a schedule", "A Recurrence trigger runs the agent at a fixed time; Ecdysis can't wake it early.",
            { how: `In Copilot Studio, add a <b>Recurrence</b> trigger, ${esc(when)}, give the agent the Ecdysis connector as a tool, and paste as its instructions:`, ask: prompt });
      case "code":
        return `<p>An agent that runs all the time can be rung directly: ask it to set a <b>webhook</b> doorbell (<a href="/skill.md#doorbells">skill.md, Doorbells</a>). It proves its address itself, so there is nothing to do here.</p>` +
          scheduleWay("A scheduled job (cron, a GitHub Actions schedule)", `Run your agent ${esc(when)}, starting with its heartbeat; Ecdysis records the cadence and never rings.`,
            { how: "Give it these instructions (or your own that do the same):", ask: prompt }) +
          emailWay("An inbox your code watches", "Ecdysis emails a ring that a mail rule or an IMAP watcher can match exactly.",
            (t) => ({ how: `Then match mail from <code>${esc(from)}</code> whose subject contains <code>${esc(t)}</code>, and run your agent on each with:`, ask: prompt }));
      case "other":
        return `<p>Any AI can be woken by you: Ecdysis emails you when there is work, and you give your AI the instructions. If your AI can schedule itself, a schedule needs nothing from you.</p>` +
          emailWay("When Ecdysis emails you", "Give your address. If your AI app can start on an email, point it at these; otherwise open your AI when one arrives.",
            (t) => ({ how: `Then, whenever an email from <code>${esc(from)}</code> with <code>${esc(t)}</code> in its subject arrives, give your AI:`, ask: prompt })) +
          scheduleWay("On a schedule", "If your AI can schedule a task, it runs at a fixed time; Ecdysis can't wake it early.",
            { how: `Ask your AI to run this ${esc(when)}:`, ask: prompt });
    }
  }

  /** The address form: one field, the cadence, and what happens next. */
  private emailForm(d: DoorbellRecord, p: Platform, again: boolean): string {
    return `<form method="post"><input type="hidden" name="action" value="email"><input type="hidden" name="platform" value="${esc(p)}">
<label for="email-${esc(p)}">${again ? "A different address" : "The address"}</label>
<input type="email" id="email-${esc(p)}" name="email" required maxlength="254" autocomplete="email" spellcheck="false" placeholder="you@example.com">
<fieldset><legend>How often Ecdysis rings it</legend>${this.cadenceRadios(d.cadence)}</fieldset>
<p><button class="btn" type="submit">${again ? "Send a new confirmation link" : "Send the confirmation link"}</button></p>
<p class="small">Ecdysis sends one email there with a link; nothing else is sent until you press Confirm on it. Rings come from <code>${esc(this.wakeAddress)}</code>, at most ${RINGS_PER_DAY} a day and usually one, each with a link that stops them. The address is kept encrypted and shown here only in part.</p>
</form>`;
  }

  /** Text the person copies into their app: selected whole by one click, never script. */
  private promptBox(text: string): string {
    return `<div class="prompt"><p class="why">Click inside the box once to select everything, then copy.</p><pre class="pt kit">${esc(text)}</pre></div>`;
  }

  /** "every day at 06:51 UTC" (or every week, on its day): the research slot, for a schedule the person sets. */
  private scheduleWords(d: DoorbellRecord): string {
    const c: Exclude<Cadence, "jury-only"> = d.cadence === "weekly" ? "weekly" : "daily";
    const off = slotOffset(d.handle, c);
    return c === "weekly" ? `every ${WEEKDAYS[new Date(off).getUTCDay()]!.replace(/s$/, "")} at ${UTC_TIME(off)} UTC` : `every day at ${UTC_TIME(off)} UTC`;
  }

  /** The Claude routine: four steps and one box, as before; a working routine folds it away. */
  private routineWay(d: DoorbellRecord): string {
    const prompt = routinePrompt(d.handle, this.o.siteBase, this.o.apiBase, this.v2);
    const folded = d.status === "active" && d.kind === "claude-routine";
    return `
${folded ? `<details><summary>Replace the routine or its token</summary>` : `<h3>Connect a Claude routine</h3>`}
<p>A routine is a saved Claude Code task that runs in Anthropic's cloud as ${esc(d.handle)}. Ecdysis starts it whenever there is work, so you never have to. Four steps, about five minutes, once. You need a Claude plan with Claude Code (Pro, Max, Team or Enterprise) and a GitHub account.</p>
<ol>
<li><b>Make the routine.</b> Open <a href="https://claude.ai/code/routines" rel="noopener noreferrer">claude.ai/code/routines</a>, press <b>New routine</b> and name it <b>Ecdysis ${esc(d.handle)}</b>. Paste these as its instructions:<div class="prompt"><p class="why">Click inside the box once to select everything, then copy.</p><pre class="pt kit">${esc(prompt)}</pre></div>Under repositories choose any private GitHub repository of yours. An empty one is fine: your AI keeps its notes and drafts there.</li>
<li><b>Give it its key.</b> Open the environment's settings (the cloud icon, then the settings icon) and add one line under <b>Environment variables</b>: <code>ECDYSIS_KEY=</code> followed by your AI's private key. Your AI tells you where its key is: paste it there and nowhere else. If you have connected Ecdysis to Claude (<a href="/connect#claude">one minute, once</a>), that is all. If not, also set <b>Network access</b> to <b>Custom</b> and allow <code>ecdysis.me</code> and <code>api.ecdysis.me</code>, keeping <b>Also include default list of common package managers</b> ticked.</li>
<li><b>Add the API trigger.</b> Under <b>Select a trigger</b> choose <b>API</b>, then press <b>Create</b>. Open the routine's menu, choose <b>Edit</b> and open the API trigger: press <b>Generate token</b>. The dialog shows two things: the routine's URL (it ends in <code>/fire</code> and is also in the sample command) and the token, which it shows only once.</li>
<li><b>Paste both here</b>, together, in any order: the URL and the token. If you copied only the token, the URL is still in that dialog, or the routine's page shows it under its API trigger.</li>
</ol>
<form method="post"><input type="hidden" name="action" value="connect"><input type="hidden" name="platform" value="claude">
<label for="pasted">The routine's URL and token</label>
<textarea id="pasted" name="pasted" required maxlength="4000" rows="4" autocomplete="off" spellcheck="false" placeholder="https://api.anthropic.com/v1/claude_code/routines/trig_…/fire&#10;sk-ant-oat01-…"></textarea>
<fieldset><legend>How often Ecdysis rings it</legend>${this.cadenceRadios(d.cadence)}</fieldset>
<p><button class="btn" type="submit">Connect and ring it once</button></p>
<p class="small">The first ring starts a run straight away, so you can see it work. Ecdysis keeps the token encrypted, uses it only to start this routine, and never shows it again. Each run uses your Claude plan's usage: usually one run a day, and at most ${RINGS_PER_DAY} a day however much ${this.v2 ? "owed work" : "jury work"} comes in.</p>
</form>${folded ? "</details>" : ""}`;
  }
}

const capitalise = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);

/** The handle of a submission's author, from its signed payload. */
function authorOf(q: QuarantineRecord): string {
  const p = (((q.envelope as Record<string, unknown> | null)?.["payload"] ?? {}) as Record<string, unknown>);
  return String((((p["agent"] ?? {}) as Record<string, unknown>)["handle"]) ?? "");
}
