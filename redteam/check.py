#!/usr/bin/env python3
"""Ganguli et al. (2022): RLHF models get harder to red team as they scale; the other model types stay flat.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:42826af46a5f52c7) is from Ganguli, Lovitt,
Kernion, Askell et al., "Red Teaming Language Models to Reduce Harms: Methods, Scaling Behaviors, and Lessons Learned"
(arXiv:2209.07858, 2022): "We find that the RLHF models are increasingly difficult to red team as they scale, and we
find a flat trend with scale for the other model types."

Its registered test: refuted if, in the paper's released 38,961 red team attacks (hh-rlhf at c72f5ce), with attack
success measured as its Figure 1 (middle) measures it, the average minimum harmlessness score per model type and size:
the RLHF model's average does not rise from 2.7B to 13B and from 13B to 52B parameters; or, for any of the plain LM,
the prompted LM and rejection sampling, its average at 52B differs from its average at 2.7B by half or more of the RLHF
model's rise between those sizes.

The input is the paper's own release, red-team-attempts/red_team_attempts.jsonl.gz from anthropics/hh-rlhf at
c72f5ce (MIT), checked against its SHA-256 and size and read as data. Only its numeric and categorical fields are
read: no transcript or task description is printed or kept. Every rule below was fixed before any seed existed.

1. The records: one JSON object per line (or one JSON list), each with model_type, num_params,
   min_harmlessness_score_transcript and rating. The paper's prompted LM is the release's "context distillation" (the
   paper prompts its LM to be helpful, honest and harmless by context distillation, after Askell et al.); its plain
   LM, rejection sampling and RLHF are "plain lm", "rejection sampling" and "rlhf".
2. Attack success as Figure 1 (middle) measures it: for each model type and size, the average of the attacks'
   minimum harmlessness scores (higher is less harmful: harder to red team), with its standard error.
3. The test's two conditions: the RLHF average rises from 2.7B to 13B and from 13B to 52B; and for each other type
   the absolute change of its average from 2.7B to 52B is less than half the RLHF average's rise from 2.7B to 52B.
   test_passed is 1 if both hold.
4. Beside the test, none of it counted: the self-reported attack success (rating, 0 to 4) per type and size, which
   the paper finds without clear trends; 95% bootstrap intervals (10,000 resamples of the attacks within each cell,
   drawn from the seed) for the RLHF rise and for each other type's change from 2.7B to 52B.

Controls (controls_passed counts those that behave as stated): the file is the pinned one; it holds 38,961 attacks,
as the paper says; the counts per type and size equal the paper's Table 1 exactly; every record has the four fields,
with a type among the four, a size among the three and a rating among 0 to 4; the same recount from the records in
reverse order gives the same averages.

What it cannot check: the preference model that gave the scores and the red team members' ratings (both are taken as
released), and the paper's mixed-effects analysis (its random intercepts per red team member are not refitted).

Writes results/outputs.json and results/detail.json. Run with: python3 redteam/check.py
"""

import gzip
import hashlib
import json
import math
import os
import random
import re
import statistics
import sys

INPUT = ("red_team_attempts.jsonl.gz", "4c7b0069991460f0064f279fd400b51f3f0095697d14d7793c49b0925f80814f", 15483307)
TYPES = {"plain lm": "plain LM", "context distillation": "prompted LM", "rejection sampling": "rejection sampling",
         "rlhf": "RLHF"}
SIZES = ("2.7B", "13B", "52B")
TABLE1 = {("plain lm", "2.7B"): 1151, ("plain lm", "13B"): 2587, ("plain lm", "52B"): 1414,
          ("context distillation", "2.7B"): 2044, ("context distillation", "13B"): 2174,
          ("context distillation", "52B"): 17739,
          ("rejection sampling", "2.7B"): 1445, ("rejection sampling", "13B"): 1263, ("rejection sampling", "52B"): 1273,
          ("rlhf", "2.7B"): 2498, ("rlhf", "13B"): 2292, ("rlhf", "52B"): 3081}
TOTAL = 38961
RESAMPLES = 10000
LIMIT = 200
OUTPUTS = ("counts_match", "rlhf", "plain", "prompted", "rejection", "rlhf_rise", "largest_other_change", "ratings",
           "bootstrap", "controls_passed", "controls_total", "test_passed")


class Refused(Exception):
    pass


def load(inputs):
    name, sha, size = INPUT
    with open(os.path.join(inputs, name), "rb") as fh:
        raw = fh.read()
    if len(raw) != size or hashlib.sha256(raw).hexdigest() != sha:
        raise Refused(f"{name}: not the pinned file")
    text = gzip.decompress(raw).decode("utf-8")
    if text.lstrip().startswith("["):
        records = json.loads(text)
    else:
        records = [json.loads(line) for line in text.splitlines() if line.strip()]
    out = []
    for r in records:
        out.append((r.get("model_type"), r.get("num_params"), r.get("min_harmlessness_score_transcript"),
                    r.get("rating")))
    return out


def cells(records):
    """Rule 2: {(type, size): [scores]} and {(type, size): [ratings]}."""
    scores, ratings = {}, {}
    for t, s, h, r in records:
        scores.setdefault((t, s), []).append(float(h))
        ratings.setdefault((t, s), []).append(float(r))
    return scores, ratings


def mean_se(xs):
    return statistics.fmean(xs), statistics.stdev(xs) / math.sqrt(len(xs))


def conditions(means):
    """Rule 3."""
    r = [means[("rlhf", s)] for s in SIZES]
    rise = r[2] - r[0]
    others = {t: abs(means[(t, "52B")] - means[(t, "2.7B")]) for t in TYPES if t != "rlhf"}
    return {"the RLHF average rises from 2.7B to 13B and from 13B to 52B": r[0] < r[1] < r[2],
            "each other type changes from 2.7B to 52B by less than half the RLHF rise":
            rise > 0 and all(v < 0.5 * rise for v in others.values())}


def bootstrap(scores, rng, resamples=RESAMPLES):
    """Rule 4: 95% intervals for the change from 2.7B to 52B of each type's average."""
    out = {}
    for t in TYPES:
        a, b = scores[(t, "2.7B")], scores[(t, "52B")]
        diffs = []
        for _ in range(resamples):
            ma = sum(rng.choices(a, k=len(a))) / len(a)
            mb = sum(rng.choices(b, k=len(b))) / len(b)
            diffs.append(mb - ma)
        diffs.sort()
        out[t] = (diffs[int(0.025 * resamples)], diffs[int(0.975 * resamples) - 1])
    return out


def run(seed, inputs="inputs", results="results", resamples=RESAMPLES):
    records = load(inputs)
    rng = random.Random(int(seed, 16))
    ctl = {"the file is the pinned one": True}
    ctl["it holds 38,961 attacks"] = len(records) == TOTAL
    ok_fields = all(t in TYPES and s in SIZES and isinstance(h, (int, float)) and r in (0, 1, 2, 3, 4)
                    for t, s, h, r in records)
    ctl["every record has a type, a size, a score and a rating 0 to 4"] = ok_fields
    if not ok_fields:
        raise Refused("a record without the four fields")
    scores, ratings = cells(records)
    counts = {k: len(v) for k, v in scores.items()}
    ctl["the counts per type and size equal the paper's Table 1"] = counts == TABLE1
    means = {k: mean_se(v)[0] for k, v in scores.items()}
    rev_scores, _ = cells(list(reversed(records)))
    ctl["the recount in reverse order gives the same averages"] = all(
        abs(mean_se(rev_scores[k])[0] - means[k]) <= 1e-12 for k in means)
    cond = conditions(means)
    rise = means[("rlhf", "52B")] - means[("rlhf", "2.7B")]
    changes = {t: means[(t, "52B")] - means[(t, "2.7B")] for t in TYPES if t != "rlhf"}
    largest = max(changes, key=lambda t: abs(changes[t]))
    boot = bootstrap(scores, rng, resamples)

    def row(t):
        return ", ".join(f"{s} {mean_se(scores[(t, s)])[0]:.3f} (se {mean_se(scores[(t, s)])[1]:.3f})" for s in SIZES)

    values = {
        "counts_match": int(ctl["the counts per type and size equal the paper's Table 1"]),
        "rlhf": row("rlhf"), "plain": row("plain lm"), "prompted": row("context distillation"),
        "rejection": row("rejection sampling"),
        "rlhf_rise": round(rise, 6),
        "largest_other_change": f"{TYPES[largest]} {changes[largest]:+.3f} ({abs(changes[largest]) / rise:.2f} of the RLHF rise)",
        "ratings": "; ".join(f"{TYPES[t]} " + ", ".join(f"{statistics.fmean(ratings[(t, s)]):.2f}" for s in SIZES)
                             for t in TYPES),
        "bootstrap": "; ".join(f"{TYPES[t]} {boot[t][0]:+.3f} to {boot[t][1]:+.3f}" for t in TYPES),
        "controls_passed": sum(bool(v) for v in ctl.values()), "controls_total": len(ctl),
        "test_passed": int(all(cond.values())),
    }
    out = {k: values[k] for k in OUTPUTS}
    for k, v in out.items():
        if isinstance(v, str) and len(v) > LIMIT:
            raise AssertionError(f"{k}: longer than {LIMIT} characters: {v}")
    detail = {"conditions": cond, "controls": ctl, "counts": {f"{t}|{s}": n for (t, s), n in sorted(counts.items())},
              "means": {f"{t}|{s}": {"mean": mean_se(v)[0], "se": mean_se(v)[1], "n": len(v)}
                        for (t, s), v in sorted(scores.items())},
              "ratings": {f"{t}|{s}": statistics.fmean(v) for (t, s), v in sorted(ratings.items())},
              "bootstrap_change_2.7B_to_52B": {t: list(v) for t, v in boot.items()}}
    os.makedirs(results, exist_ok=True)
    with open(os.path.join(results, "outputs.json"), "w", encoding="ascii") as fh:
        json.dump(out, fh, indent=2, sort_keys=True)
        fh.write("\n")
    with open(os.path.join(results, "detail.json"), "w", encoding="ascii") as fh:
        json.dump(detail, fh, indent=1, sort_keys=True)
        fh.write("\n")
    return out, detail


def main():
    seed = os.environ.get("ECDYSIS_SEED", "")
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        sys.exit("ECDYSIS_SEED must be the 64-hex seed the archive issued")
    try:
        out, _ = run(seed)
    except Refused as e:
        sys.exit(f"redteam: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
