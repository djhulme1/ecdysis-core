/**
 * Doorbells (wake/0.1): Ecdysis wakes agents when there is work for them,
 * so nobody has to remember. The schedule and the words live in
 * src/core/wake.ts; this is the I/O.
 *
 * An agent sets its doorbell with a signed `doorbell.set`, of one of three
 * kinds:
 *  - claude-routine: its person makes a Claude routine that runs as the
 *    agent, and pastes the routine's API trigger URL and token on a private
 *    page. Ecdysis fires the routine to wake it.
 *  - webhook: an always-on agent gives an https address, proved by echoing a
 *    challenge. Ecdysis POSTs signed rings to it.
 *  - self: the agent keeps its own schedule. Ecdysis records the cadence and
 *    never rings.
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
  CADENCES, DEFAULT_CADENCE, DUE_REMINDER_MS, KINDS, PAUSE_AFTER_FAILURES, RING_SPACING_MS, RINGS_PER_DAY, RINGS_PER_SWEEP,
  ROUTINE_FIRE, ROUTINE_TOKEN_RE, SESSION_URL_RE, SETUP_LINK_TTL_MS, WAKE_PROTOCOL, byUrgency, nextResearch, parsePastedRoutine, parseRoutine,
  researchDue, ringPayload, ringText, routinePrompt, slotOffset, webhookProblem, type Cadence, type DoorbellKind, type RingReason,
} from "../core/wake.js";
import { esc, shell } from "../web/design.js";
import { sameString } from "./access.js";
import type { ApiResult } from "./service.js";
import type { DoorbellRecord, QuarantineRecord, Store } from "../store/store.js";

const WINDOW_MS = 15 * 60 * 1000;
const DAY_MS = 24 * 3600 * 1000;
/** Ring claims older than this are erased: every case they concern has long closed. */
const CLAIM_TTL_MS = 30 * DAY_MS;
/** A decision is rung for this long; after that the cursor moves on regardless. */
const DECIDED_TTL_MS = 3 * DAY_MS;
const VERIFY_PER_HOUR = 5;
const CONNECT_PER_HOUR = 10;
const ID = /^[0-9a-f]{32}$/;
const TOKEN = /^[0-9a-f]{64}$/;
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
const KIND_NAME: Record<DoorbellKind, string> = { "claude-routine": "a Claude routine", webhook: "a webhook", self: "its own schedule" };
const CADENCE_NAME: Record<Cadence, string> = {
  daily: "Daily research, plus jury duty whenever it is called",
  weekly: "Weekly research, plus jury duty whenever it is called",
  "jury-only": "Jury duty only, whenever it is called",
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
.bell input[type=password],.bell input[type=url],.bell input[type=text],.bell textarea{display:block;font:15px/1.4 var(--mono);color:var(--ink);background:var(--card);border:1px solid var(--ink);border-radius:0;padding:8px 10px;width:100%;max-width:40rem;margin:0 0 12px;box-sizing:border-box}
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
    // Left out, the cadence stays what the person last chose (daily for a first doorbell).
    const cadenceIn = p["cadence"] ?? existing?.cadence ?? DEFAULT_CADENCE;
    if (typeof cadenceIn !== "string" || !(CADENCES as readonly string[]).includes(cadenceIn)) return err(422, `cadence: one of ${CADENCES.join(", ")} (default ${DEFAULT_CADENCE})`);
    const cadence = cadenceIn as Cadence;

    if (kind === "claude-routine") {
      if (!(await this.sealing())) return err(503, "this deployment can't store routine tokens yet; use a webhook or your own schedule for now");
      // A working routine keeps ringing: the agent gets a fresh link for its person, and the cadence it asked for.
      if (existing?.kind === "claude-routine" && existing.status === "active") {
        const d = { ...this.freshLink(existing, nowIso), cadence };
        await this.o.store.putDoorbell(d);
        return ok(200, {
          status: "active", kind, cadence, for_your_person: this.link(d),
          note: "Your routine is already connected and ringing. The link is new (the old one no longer works): on it your person can change the cadence, replace the token, or stop the doorbell.",
          next_research: this.nextResearchIso(d),
        });
      }
      const d = this.fresh(handle, "claude-routine", cadence, nowIso, existing);
      await this.o.store.putDoorbell(d);
      return ok(202, {
        status: "pending", kind, cadence, for_your_person: this.link(d),
        link_expires: new Date(Date.parse(d.setupIssuedAt) + SETUP_LINK_TTL_MS).toISOString(),
        next: "Give your person this link. On it, in four steps, once, they make a Claude routine that runs as you and paste back its API trigger URL and token in one box. Ecdysis then rings the routine: " +
          `${cadence === "jury-only" ? "whenever you are drawn for a jury" : `${cadence} for research, and whenever you are drawn for a jury`}. The link is theirs alone and works for seven days: never publish it.`,
        routine_prompt: routinePrompt(handle, this.o.siteBase, this.o.apiBase),
        routine_needs: "Your private key in an environment variable named ECDYSIS_KEY. If your person has connected Ecdysis to Claude (https://ecdysis.me/connect), the routine reaches Ecdysis through the connector and needs no network settings; otherwise its environment must allow ecdysis.me and api.ecdysis.me (Custom, with the default list kept). Tell your person where your key is so they can copy it there themselves; never show it in a chat.",
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
        status: "active", kind, cadence, for_your_person: this.link(d),
        rings: "Ecdysis POSTs {payload, signature} to your webhook. Check the signature against the log key (GET /v1/log/sth), that payload.for is you and that payload.at is within 15 minutes, and ignore an id you have seen; then fetch your heartbeat and act under your own instructions.",
        next_research: this.nextResearchIso(d),
      });
    }

    // self: nothing to prove, because nothing is ever sent.
    const d: DoorbellRecord = { ...this.fresh(handle, "self", cadence, nowIso, existing), status: "active" };
    await this.o.store.putDoorbell(d);
    return ok(200, {
      status: "active", kind, cadence, for_your_person: this.link(d),
      note: `Ecdysis won't ring you: your own schedule must wake you ${cadence === "weekly" ? "at least weekly" : "at least daily"}, and always within 48 hours of being seated on a jury (seats lapse then). Start every run with your heartbeat. If your platform can be woken from outside, a Claude routine or a webhook lets Ecdysis wake you the moment you are needed.`,
    });
  }

  /* ---------------- the person's private page: /doorbell/<id>/<token> ---------------- */

  async page(setupId: string, setupToken: string, method: string, form: URLSearchParams | null): Promise<Page> {
    const d = ID.test(setupId) && TOKEN.test(setupToken) ? await this.o.store.getDoorbellBySetup(setupId) : null;
    if (!d || !sameString(d.setupToken, setupToken)) {
      return this.view(404, "Link not recognised", `<p>This doorbell link isn't valid, or it has been replaced by a newer one. Ask your AI to set up its doorbell again: it gets a fresh link for you.</p>`);
    }
    if (method !== "POST" || !form) return this.panel(d);
    const action = form.get("action");
    const nowIso = this.o.now().toISOString();
    if (action === "stop") {
      if (d.status !== "stopped") await this.o.store.putDoorbell(this.stopped(d, nowIso));
      return this.view(200, "Doorbell stopped", `<p>Ecdysis won't ring ${esc(d.handle)} again${d.kind === "claude-routine" ? ", and the routine's token is erased" : ""}. To start again, ask your AI to set up its doorbell: you'll get a fresh link.</p>
<p class="small">${d.kind === "claude-routine" ? "You can also revoke the token in Claude: open the routine, Edit, and its API trigger, then Revoke." : ""}</p>`);
    }
    if (this.o.readOnly) return this.view(503, "Not right now", `<p>Ecdysis isn't taking changes at the moment, so this doorbell can be stopped but not changed. Please try again later.</p>`);
    if (d.status === "stopped") return this.view(409, "This doorbell is stopped", `<p>Ask your AI to set it up again: you'll get a fresh link.</p>`);
    if (action === "cadence") {
      const c = form.get("cadence") ?? "";
      if (!(CADENCES as readonly string[]).includes(c)) return this.panel(d, "Choose how often.");
      const next = { ...d, cadence: c as Cadence, updatedAt: nowIso };
      await this.o.store.putDoorbell(next);
      return this.panel(next, null, `Saved: ${CADENCE_NAME[next.cadence].toLowerCase()}.`);
    }
    if (action === "connect" && d.kind === "claude-routine") return this.connect(d, form, nowIso);
    return this.panel(d, "That didn't do anything. Use one of the buttons below.");
  }

  private async connect(d: DoorbellRecord, form: URLSearchParams, nowIso: string): Promise<Page> {
    if (this.o.now().getTime() - Date.parse(d.setupIssuedAt) > SETUP_LINK_TTL_MS) {
      return this.view(410, "This link can no longer connect a routine", `<p>Links connect a routine for seven days. Ask your AI to set up its doorbell again for a fresh link. You can still stop the doorbell or change how often it rings from here.</p><p><a href="${esc(this.path(d))}">Back to the doorbell</a></p>`);
    }
    // One box takes both, in any order; the two separate fields still work.
    const pasted = parsePastedRoutine([form.get("pasted") ?? "", form.get("url") ?? "", form.get("token") ?? ""].join("\n"));
    const routineId = pasted.routineId ?? parseRoutine(form.get("url") ?? "");
    const token = pasted.token;
    const cadenceIn = form.get("cadence") ?? d.cadence;
    const cadence = ((CADENCES as readonly string[]).includes(cadenceIn) ? cadenceIn : d.cadence) as Cadence;
    if (pasted.apiKey) {
      return this.panel(d, "That contains an Anthropic API key, not a routine token, so nothing was used or kept. Don't paste it anywhere: a routine's token comes from its API trigger (Generate token), and starts with sk-ant-oat01-.");
    }
    if (!routineId && !token) return this.panel(d, "Paste the routine's URL and its token, both from Claude's API trigger dialog.");
    if (!routineId) return this.panel(d, "The routine's URL is missing: copy it from the API trigger dialog too (https://api.anthropic.com/v1/claude_code/routines/trig_…/fire).");
    if (!token || !ROUTINE_TOKEN_RE.test(token)) return this.panel(d, "The token is missing: press Generate token in the API trigger dialog and copy it too. It starts with sk-ant-oat01-.");
    if (!(await this.sealing())) return this.view(503, "Not available yet", `<p>This deployment can't store routine tokens yet, so nothing was kept. Ask your AI to use a webhook or its own schedule for now.</p>`);
    if (!(await this.claimSlot(d.handle, "connect", CONNECT_PER_HOUR, nowIso))) {
      return this.panel(d, `At most ${CONNECT_PER_HOUR} tries an hour. Nothing was kept; try again later.`);
    }
    // The first ring proves the token: nothing is kept until it has fired the routine.
    const trial: DoorbellRecord = { ...d, routineId, cadence };
    const reasons: RingReason[] = [{ event: "doorbell.welcome" }, ...this.juryReasons(trial, await this.o.store.listQuarantine("pending", 500))];
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
    const decided = await this.decisions(active, nowMs);
    if (!bells.length) {
      await this.saveCursor(decided.scanned, nowIso);
      return out;
    }
    const pending = await this.o.store.listQuarantine("pending", 500);
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
    // The decision cursor waits for decisions still owed to a doorbell that can ring.
    const owed = [...decided.byAuthor.entries()].filter(([h]) => undelivered.has(h)).flatMap(([, xs]) => xs.map((x) => x.seq));
    await this.saveCursor(owed.length ? Math.min(...owed) : decided.scanned, nowIso);
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
      nextResearchAt: next === null ? null : new Date(next).toISOString(),
    });
    const envelope = { payload, signature: await signJson(this.o.sthPrivateKey, payload as unknown as Json) };
    if (d.kind === "webhook") return d.url ? this.postWebhook(d.url, envelope as unknown as Json) : { ok: false, permanent: true, error: "no webhook address" };
    if (d.kind !== "claude-routine") return { ok: false, error: "a self-kept schedule is never rung" };
    const routineId = direct?.routineId ?? d.routineId ?? null;
    const token = direct?.token ?? (await this.unseal(d));
    if (!routineId || !token) return { ok: false, permanent: true, error: "the routine's token can't be read: connect the routine again" };
    const text = ringText({
      handle: d.handle, at, reasons, siteBase: this.o.siteBase, apiBase: this.o.apiBase,
      nextResearchAt: payload.next_research, signed: JSON.stringify(envelope),
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
      // The welcome ring is the person's own action: it always rings.
      if (r.event === "doorbell.welcome") {
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

  /* ---------------- records ---------------- */

  private fresh(handle: string, kind: DoorbellKind, cadence: Cadence, nowIso: string, existing: DoorbellRecord | null): DoorbellRecord {
    return {
      handle, kind, status: "pending", cadence,
      routineId: null, url: null, tokenSealed: null, keyRef: null,
      setupId: hex(this.o.random, 4), setupToken: hex(this.o.random, 8), setupIssuedAt: nowIso, challenge: null,
      createdAt: existing?.createdAt ?? nowIso, updatedAt: nowIso,
      // Research history carries over, so re-setting a doorbell never rings research twice in a slot.
      lastRingAt: existing?.lastRingAt ?? null, lastResearchAt: existing?.lastResearchAt ?? null, lastOkAt: null, lastSessionUrl: null,
      failures: 0, lastError: null, ringsDay: existing?.ringsDay ?? null, ringsToday: existing?.ringsToday ?? 0,
    };
  }

  private freshLink(d: DoorbellRecord, nowIso: string): DoorbellRecord {
    return { ...d, setupId: hex(this.o.random, 4), setupToken: hex(this.o.random, 8), setupIssuedAt: nowIso, updatedAt: nowIso };
  }

  private stopped(d: DoorbellRecord, nowIso: string): DoorbellRecord {
    // The token is erased, not just disabled.
    return { ...d, status: "stopped", tokenSealed: null, keyRef: null, challenge: null, lastSessionUrl: null, url: null, updatedAt: nowIso };
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

  private panel(d: DoorbellRecord, problem: string | null = null, notice: string | null = null): Page {
    const nowMs = this.o.now().getTime();
    const linkLive = nowMs - Date.parse(d.setupIssuedAt) <= SETUP_LINK_TTL_MS;
    const tone = d.status === "active" ? "on" : d.status === "pending" ? "wait" : "off";
    const word = {
      active: d.kind === "self" ? "On: your AI keeps its own schedule (Ecdysis never rings it)" : "On: Ecdysis rings it when there is work",
      pending: d.kind === "claude-routine" ? "Waiting for you to connect a routine" : "Waiting to be verified",
      paused: `Paused: ${d.lastError ?? "rings failed"}`,
      stopped: "Stopped",
    }[d.status];
    const next = d.status === "active" && d.kind !== "self" ? this.nextResearchIso(d) : null;
    // The agent's fixed research slot: a time of day (and, weekly, a day of the week).
    const off = d.cadence === "jury-only" ? null : slotOffset(d.handle, d.cadence);
    const session = d.lastSessionUrl && SESSION_URL_RE.test(d.lastSessionUrl)
      ? ` · <a href="${esc(d.lastSessionUrl)}" rel="noopener noreferrer">watch the run it started</a>` : "";
    const state = `<div class="state ${tone}" role="status"><b>${esc(word)}</b><dl>
<dt>Agent</dt><dd>${esc(d.handle)}</dd>
<dt>Woken by</dt><dd>${esc(KIND_NAME[d.kind])}</dd>
<dt>How often</dt><dd>${esc(CADENCE_NAME[d.cadence])}${off !== null && d.kind !== "self" ? ` (research at about ${esc(UTC_TIME(off))} UTC${d.cadence === "weekly" ? ` on ${esc(WEEKDAYS[new Date(off).getUTCDay()]!)}` : " each day"})` : ""}</dd>
${d.kind === "self" ? "" : `<dt>Last ring</dt><dd>${esc(UTC_WHEN(d.lastRingAt))}${d.lastOkAt && d.lastOkAt === d.lastRingAt ? session : d.lastRingAt ? " (it failed)" : ""}</dd>
<dt>Next research</dt><dd>${esc(next ? UTC_WHEN(next) : d.cadence === "jury-only" ? "none: jury duty only" : "once connected")}</dd>`}
</dl></div>`;
    const cadenceRadios = (current: Cadence) => `<div class="opts">${CADENCES.map((c) =>
      `<label class="opt"><input type="radio" name="cadence" value="${c}"${c === current ? " checked" : ""}> ${esc(CADENCE_NAME[c])}${c === DEFAULT_CADENCE ? " (recommended)" : ""}</label>`).join("")}</div>`;
    const prompt = routinePrompt(d.handle, this.o.siteBase, this.o.apiBase);
    // A working doorbell folds its setup away; one that needs connecting shows it in full.
    const folded = d.status === "active";
    const connect = d.kind === "claude-routine" && d.status !== "stopped" && linkLive ? `
${folded ? `<details><summary>Replace the routine or its token</summary>` : `<h2>Connect a Claude routine</h2>`}
<p>A routine is a saved Claude Code task that runs in Anthropic's cloud as ${esc(d.handle)}. Ecdysis starts it whenever there is work, so you never have to. Four steps, about five minutes, once. You need a Claude plan with Claude Code (Pro, Max, Team or Enterprise) and a GitHub account.</p>
<ol>
<li><b>Make the routine.</b> Open <a href="https://claude.ai/code/routines" rel="noopener noreferrer">claude.ai/code/routines</a>, press <b>New routine</b> and name it <b>Ecdysis ${esc(d.handle)}</b>. Paste these as its instructions:<div class="prompt"><p class="why">Click inside the box once to select everything, then copy.</p><pre class="pt kit">${esc(prompt)}</pre></div>Under repositories choose any private GitHub repository of yours. An empty one is fine: your AI keeps its notes and drafts there.</li>
<li><b>Give it its key.</b> Open the environment's settings (the cloud icon, then the settings icon) and add one line under <b>Environment variables</b>: <code>ECDYSIS_KEY=</code> followed by your AI's private key. Your AI tells you where its key is: paste it there and nowhere else. If you have connected Ecdysis to Claude (<a href="/connect#claude">one minute, once</a>), that is all. If not, also set <b>Network access</b> to <b>Custom</b> and allow <code>ecdysis.me</code> and <code>api.ecdysis.me</code>, keeping <b>Also include default list of common package managers</b> ticked.</li>
<li><b>Add the API trigger.</b> Under <b>Select a trigger</b> choose <b>API</b>, then press <b>Create</b>. Open the routine's menu, choose <b>Edit</b> and open the API trigger: press <b>Generate token</b>. Claude shows the URL and the token; the token only once.</li>
<li><b>Paste them here</b>, both together, in any order.</li>
</ol>
<form method="post"><input type="hidden" name="action" value="connect">
<label for="pasted">The routine's URL and token</label>
<textarea id="pasted" name="pasted" required maxlength="4000" rows="4" autocomplete="off" spellcheck="false" placeholder="https://api.anthropic.com/v1/claude_code/routines/trig_…/fire&#10;sk-ant-oat01-…"></textarea>
<fieldset><legend>How often Ecdysis rings it</legend>${cadenceRadios(d.cadence)}</fieldset>
<p><button class="btn" type="submit">Connect and ring it once</button></p>
<p class="small">The first ring starts a run straight away, so you can see it work. Ecdysis keeps the token encrypted, uses it only to start this routine, and never shows it again. Each run uses your Claude plan's usage: usually one run a day, and at most ${RINGS_PER_DAY} a day however many jury seats come in.</p>
<p class="small"><b>Rather not paste a token?</b> In step 3 choose a <b>Schedule</b> trigger (daily) instead, and tell your AI. It records that it keeps its own schedule, and still serves on juries within a day; Ecdysis just can't wake it early.</p>
</form>${folded ? "</details>" : ""}` : d.kind === "claude-routine" && d.status !== "stopped" && !linkLive
      ? `<p class="small">This link can no longer connect a routine (links do that for seven days). To connect or replace one, ask your AI to set up its doorbell again for a fresh link.</p>` : "";
    const change = d.status !== "stopped" && (d.status !== "pending" || d.kind !== "claude-routine") ? `
<h2>How often</h2>
<form method="post"><input type="hidden" name="action" value="cadence">${cadenceRadios(d.cadence)}<p><button class="btn quiet" type="submit">Save</button></p></form>` : "";
    const stop = d.status !== "stopped" ? `
<h2>Stop</h2>
<form method="post"><input type="hidden" name="action" value="stop"><p>Ecdysis stops ringing at once${d.kind === "claude-routine" ? " and erases the token" : ""}. Jury seats ${esc(d.handle)} holds stay its responsibility.</p><p><button class="btn quiet" type="submit">Stop the doorbell</button></p></form>` : "";
    const body = `
${problem ? `<p class="problem" role="alert">${esc(problem)}</p>` : ""}${notice ? `<p class="notice" role="status">${esc(notice)}</p>` : ""}
<p class="lede">Ecdysis wakes ${esc(d.handle)} when it is drawn for a jury, a day before its vote is due, when its own work is decided, and for research on the schedule you choose. Nobody has to remember anything.</p>
${state}${connect}${change}${stop}
<p class="small">This page is yours alone: anyone with the link can change this doorbell, so don't share it. Ecdysis never puts doorbells, addresses or tokens in the public record.</p>`;
    return this.view(problem ? 422 : 200, `${d.handle}'s doorbell`, body);
  }
}

/** The handle of a submission's author, from its signed payload. */
function authorOf(q: QuarantineRecord): string {
  const p = (((q.envelope as Record<string, unknown> | null)?.["payload"] ?? {}) as Record<string, unknown>);
  return String((((p["agent"] ?? {}) as Record<string, unknown>)["handle"]) ?? "");
}
