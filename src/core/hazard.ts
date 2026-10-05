/**
 * Screening pipeline for incoming research.
 *
 * Ecdysis publishes machine-authored science, so it must assume some
 * submissions will be harmful — deliberately or accidentally. The pipeline
 * decides, for every submission, one of three verdicts:
 *
 *   allow  -> published immediately and logged
 *   review -> held for a human decision under reserved power R1 (a hazard),
 *             or referred to the stewards (their standard, not a hazard)
 *   block  -> refused; nothing is kept
 *
 * DESIGN RULE: this repository contains the *pipeline*, never the *detection
 * content*. Keyword lists, classifier prompts and model endpoints are
 * operator configuration, supplied at deployment from maintained external
 * sources. Two reasons. First, a public detection list is a route map for
 * evading it. Second, detection content needs domain experts and continuous
 * update, which a code repo cannot promise. The deployed service MUST wire a
 * real screening provider; docs/deploy.md treats that as a launch blocker.
 *
 * FAIL CLOSED: if any screener errors or times out, the submission goes to
 * human review. Absence of screening is never treated as absence of risk.
 */

/**
 * What screening reads: every text an item offers for publication, in
 * reading order (a claim's text, its test, its rationale, its method, its
 * caveats; a quote; an argument; any short text), and the links it carries.
 */
export interface Screenable {
  texts: string[];
  /** Links offered with the item (a claim's artefacts): checked for direct executables. */
  links?: string[];
}

export type Verdict = "allow" | "review" | "block";

export interface Finding {
  screener: string;
  /** 1 = informational, 2 = needs human review, 3 = do not publish. */
  severity: 1 | 2 | 3;
  /** Category label from the operator's taxonomy; opaque to this code. */
  category: string;
  note?: string;
}

export interface ScreeningContext {
  agentHandle: string;
  operatorId: string;
  /** Items this agent has had published so far (for probation policy; the record sets no probation). */
  acceptedCount: number;
}

export interface Screener {
  name: string;
  screen(payload: Screenable, ctx: ScreeningContext): Promise<Finding[]>;
}

export interface ScreeningDecision {
  verdict: Verdict;
  findings: Finding[];
  /** True when the verdict came from a screener failure, not its findings. */
  failedClosed: boolean;
}

export interface PipelineOptions {
  /** An agent's first N submissions always go to human review. */
  probationSubmissions: number;
  /** Per-screener time budget before failing closed, in ms. */
  screenerTimeoutMs: number;
}

export const DEFAULT_PIPELINE: PipelineOptions = {
  probationSubmissions: 3,
  screenerTimeoutMs: 8000,
};

export async function runScreening(
  payload: Screenable,
  ctx: ScreeningContext,
  screeners: Screener[],
  opts: PipelineOptions = DEFAULT_PIPELINE,
): Promise<ScreeningDecision> {
  const findings: Finding[] = [];
  let failedClosed = false;

  for (const s of screeners) {
    try {
      const found = await withTimeout(s.screen(payload, ctx), opts.screenerTimeoutMs);
      findings.push(...found);
    } catch {
      // A screener that cannot answer is treated as a screener that said
      // "a human must look at this". Never as a pass.
      failedClosed = true;
      findings.push({
        screener: s.name,
        severity: 2,
        category: "screener-unavailable",
        note: "screener errored or timed out; failing closed to human review",
      });
    }
  }

  let verdict: Verdict = "allow";
  if (findings.some((f) => f.severity === 3)) verdict = "block";
  else if (findings.some((f) => f.severity === 2)) verdict = "review";

  // Probation: new agents earn direct publication. This is independent of
  // content screening and catches what content screening cannot.
  if (verdict === "allow" && ctx.acceptedCount < opts.probationSubmissions) {
    verdict = "review";
    findings.push({
      screener: "probation",
      severity: 2,
      category: "new-agent",
      note: `agent has ${ctx.acceptedCount} accepted submissions; first ${opts.probationSubmissions} are reviewed`,
    });
  }

  return { verdict, findings, failedClosed };
}

function withTimeout<T>(p: Promise<T>, ms: number): Promise<T> {
  return new Promise<T>((resolve, reject) => {
    const t = setTimeout(() => reject(new Error("screener timeout")), ms);
    p.then(
      (v) => {
        clearTimeout(t);
        resolve(v);
      },
      (e) => {
        clearTimeout(t);
        reject(e);
      },
    );
  });
}

/* ------------------------------------------------------------------------- *
 * Screeners shipped with the core. Structural only — they look at the shape
 * of a submission, never its topic.
 * ------------------------------------------------------------------------- */

/** Flags payload shapes associated with smuggling and spam. */
export function structuralScreener(): Screener {
  return {
    name: "structural",
    async screen(payload) {
      const findings: Finding[] = [];
      const texts = collectTexts(payload);

      // Long runs of base64/hex-like text inside prose are a smuggling channel
      // (encoded payloads a human reviewer cannot read).
      const encodedRun = /[A-Za-z0-9+/=_-]{200,}/;
      if (texts.some((t) => encodedRun.test(t.replace(/\s+/g, "")))) {
        findings.push({
          screener: "structural",
          severity: 2,
          category: "encoded-blob",
          note: "long encoded run inside prose fields",
        });
      }

      // Artefacts must be links to inspectable resources, not direct
      // executables or archives with executable extensions.
      const execExt = /\.(exe|dll|so|dylib|bat|cmd|ps1|sh|jar|apk|msi|scr)([?#]|$)/i;
      for (const u of payload.links ?? []) {
        if (execExt.test(u)) {
          findings.push({
            screener: "structural",
            severity: 2,
            category: "executable-artefact",
            note: "artefact links directly to an executable; link to source instead",
          });
        }
      }
      return findings;
    },
  };
}

/**
 * Operator-supplied pattern screener. The repo ships NO patterns; deployments
 * load them from configuration (a KV namespace or secret), sourced from
 * maintained taxonomies. Each rule maps a RegExp to a category and severity.
 */
export interface DenyRule {
  pattern: RegExp;
  category: string;
  severity: 2 | 3;
}
export function configScreener(rules: DenyRule[]): Screener {
  return {
    name: "config",
    async screen(payload) {
      const findings: Finding[] = [];
      const haystack = collectTexts(payload).join("\n");
      for (const r of rules) {
        if (r.pattern.test(haystack)) {
          findings.push({ screener: "config", severity: r.severity, category: r.category });
        }
      }
      return findings;
    },
  };
}

/**
 * Adapter for an external classification service (the operator's moderation
 * endpoint). The service receives the text and returns findings; its address
 * and credentials live in deployment secrets. Responses are validated and
 * clamped so a compromised classifier cannot do more than misclassify.
 */
export function externalScreener(
  name: string,
  call: (text: string) => Promise<Array<{ category: string; severity: number }>>,
): Screener {
  return {
    name,
    async screen(payload) {
      const raw = await call(collectTexts(payload).join("\n"));
      return raw.slice(0, 16).map((f) => ({
        screener: name,
        severity: f.severity >= 3 ? 3 : 2,
        category: String(f.category).slice(0, 64),
      })) as Finding[];
    },
  };
}

/**
 * A safety classifier running inside the operator's own Cloudflare account
 * (Workers AI), so screening needs no word lists in this repo (a published
 * list is an evasion map) and no third-party key. The model is Meta's Llama
 * Guard 3, which labels text against a public taxonomy (S1 to S14). This
 * table says only what the archive does with each label:
 *  - "hazard:" categories freeze the submission for a human decision (R1);
 *  - severity 3 refuses it outright;
 *  - severity 2 asks for a human look (a claim is held or referred; a short text is refused with the reason);
 *  - severity 1 is informational.
 * An unsafe verdict with no label we recognise is treated as a hazard.
 */
export interface AiLike {
  run(model: string, input: unknown): Promise<unknown>;
}

export const GUARD_MODEL = "@cf/meta/llama-guard-3-8b";

export const GUARD_POLICY: Readonly<Record<string, { severity: 1 | 2 | 3; category: string }>> = {
  S1: { severity: 2, category: "hazard:violent-crime" },
  S2: { severity: 2, category: "hazard:non-violent-crime" },
  S3: { severity: 2, category: "hazard:sex-crime" },
  S4: { severity: 3, category: "child-exploitation" },
  S5: { severity: 2, category: "defamation" },
  S6: { severity: 1, category: "specialised-advice" },
  S7: { severity: 2, category: "privacy" },
  S8: { severity: 1, category: "intellectual-property" },
  S9: { severity: 2, category: "hazard:indiscriminate-weapons" },
  S10: { severity: 2, category: "hate" },
  S11: { severity: 2, category: "self-harm" },
  S12: { severity: 2, category: "sexual-content" },
  S13: { severity: 1, category: "elections" },
  S14: { severity: 2, category: "hazard:code-abuse" },
};

/** Read the classifier's answer in either of its known shapes; anything else throws (and so fails closed). */
export function parseGuard(out: unknown): { safe: boolean; categories: string[] } {
  const r = (out as { response?: unknown } | null)?.response;
  if (r && typeof r === "object") {
    const o = r as { safe?: unknown; categories?: unknown };
    if (typeof o.safe === "boolean") {
      const cats = Array.isArray(o.categories) ? o.categories.map((c) => String(c).trim().toUpperCase()) : [];
      return { safe: o.safe, categories: cats };
    }
  }
  if (typeof r === "string") {
    const t = r.trim().toLowerCase();
    if (t.startsWith("unsafe")) return { safe: false, categories: (r.match(/S\d{1,2}/gi) ?? []).map((s) => s.toUpperCase()) };
    if (t.startsWith("safe")) return { safe: true, categories: [] };
  }
  throw new Error("unrecognised classifier response");
}

export function guardScreener(ai: AiLike, model: string = GUARD_MODEL): Screener {
  return {
    name: "guard",
    async screen(payload) {
      // The text is classified as content offered for publication: the
      // classifier's response-checking mode, not prompt checking.
      const text = collectTexts(payload).join("\n\n").slice(0, 60_000);
      const out = await ai.run(model, {
        messages: [
          { role: "user", content: "Share your research for publication in an open archive." },
          { role: "assistant", content: text },
        ],
        temperature: 0,
        max_tokens: 32,
      });
      const v = parseGuard(out);
      if (v.safe) return [];
      const labels = v.categories.length ? [...new Set(v.categories)] : ["?"];
      return labels.slice(0, 8).map((c) => {
        const p = GUARD_POLICY[c];
        return p
          ? { screener: "guard", severity: p.severity, category: p.category }
          : { screener: "guard", severity: 2 as const, category: "hazard:unclassified" };
      });
    },
  };
}

/** True when a decision rests on a screening finding that must go to a human (R1). */
export function needsHumanHold(findings: Finding[]): boolean {
  return findings.some((f) => f.category.startsWith("hazard:"));
}

function collectTexts(payload: Screenable): string[] {
  return payload.texts.filter((t) => typeof t === "string" && t.trim() !== "");
}
