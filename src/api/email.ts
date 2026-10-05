/**
 * Email: the one way Ecdysis sends mail (sign-in links, alerts people asked
 * for, digests, doorbell rings and confirmations, complaint notices to the
 * stewards). Plain text through a transactional provider's HTTP API
 * (Resend), from a subdomain whose reputation is separate from ecdysis.me.
 * The provider key is a Worker secret the deploy installs; it appears
 * nowhere else. Every kind of email shares one daily cap (the provider
 * plan's quota), and the pause switch or the kill switch stops all of it.
 */

export const EMAIL_RE = /^[A-Za-z0-9._%+-]{1,64}@[A-Za-z0-9.-]{1,190}\.[A-Za-z]{2,24}$/;

/** The provider quota every kind of email shares, unless configured otherwise (EMAIL_DAILY_CAP). */
export const EMAIL_DAILY_CAP_DEFAULT = 100;

export type SendEmail = (msg: {
  from: string; to: string; replyTo: string; subject: string; text: string; headers: Record<string, string>;
}) => Promise<{ ok: true; id: string } | { ok: false; error: string }>;

/** Resend's HTTP API. The fetch is called as a plain function, never as a method (Cloudflare's runtime refuses a foreign `this`). */
export function resendSender(apiKey: string, fetchImpl: typeof fetch = (input, init) => fetch(input, init)): SendEmail {
  return async (m) => {
    let r: Response;
    try {
      // Ten seconds at most: a provider that hangs must never hold up a cron run (doorbells, lapses, alerts all share it).
      r = await fetchImpl("https://api.resend.com/emails", {
        method: "POST",
        headers: { authorization: `Bearer ${apiKey}`, "content-type": "application/json" },
        body: JSON.stringify({ from: m.from, to: [m.to], reply_to: m.replyTo, subject: m.subject, text: m.text, headers: m.headers }),
        signal: AbortSignal.timeout(10_000),
      });
    } catch {
      return { ok: false, error: "provider timeout: no answer within 10 seconds" };
    }
    const body = (await r.json().catch(() => ({}))) as { id?: string; message?: string; name?: string };
    if (r.ok && typeof body.id === "string") return { ok: true, id: body.id };
    return { ok: false, error: `provider ${r.status}: ${String(body.message ?? body.name ?? "error").slice(0, 200)}` };
  };
}
