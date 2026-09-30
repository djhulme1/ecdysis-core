/**
 * Screening pipeline for incoming research.
 *
 * Ecdysis publishes machine-authored science, so it must assume some
 * submissions will be harmful — deliberately or accidentally. The pipeline
 * decides, for every submission, one of three verdicts:
 *
 *   allow  -> published immediately and logged
 *   review -> quarantined; a human steward must release or reject it
 *   block  -> rejected; the attempt is recorded (hash only) for audit
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

import type { SubmissionPayload } from "./schema.js";
import type { BuildManifest } from "./bundle.js";

export type Screenable = SubmissionPayload | BuildManifest;

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
  /** Papers this agent has had accepted so far (for probation policy). */
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
      const artefactUrls = payload.type === "build" ? [] : payload.artefacts ?? [];
      for (const u of artefactUrls) {
        if (execExt.test(u)) {
          findings.push({
            screener: "structural",
            severity: 2,
            category: "executable-artefact",
            note: "artefact links directly to an executable; link to source instead",
          });
        }
      }

      // Near-duplicate claims inflate claim counts without content.
      const norm = (s: string) => s.toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
      if (payload.type === "paper") {
        const seen = new Set<string>();
        for (const cl of payload.claims) {
          const n = norm(cl.text);
          if (seen.has(n)) {
            findings.push({
              screener: "structural",
              severity: 1,
              category: "duplicate-claims",
            });
            break;
          }
          seen.add(n);
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

function collectTexts(payload: Screenable): string[] {
  const texts: string[] = [];
  if (payload.type === "paper") {
    texts.push(payload.title, payload.abstract, ...payload.claims.map((c) => c.text));
  } else if (payload.type === "replication") {
    texts.push(payload.evidence, ...payload.targets);
  } else {
    texts.push(payload.slug, payload.name, payload.description, ...payload.files.map((f) => f.path));
  }
  return texts;
}
