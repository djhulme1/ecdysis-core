#!/usr/bin/env python3
"""METR's 50% time horizons and their doubling time, recomputed from the released runs by the paper's own estimator.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:b88dde9d74fe32f8) is from Kwa, West, Becker
et al., "Measuring AI Ability to Complete Long Software Tasks", arXiv:2503.14499 (v4, July 2026): "On these tasks,
current frontier AI models such as Claude 3.7 Sonnet have a 50% time horizon of around 50 minutes. Furthermore,
frontier AI time horizon has been doubling approximately every seven months since 2019, though the trend may have
accelerated in 2024."

Its registered test: refuted if, by the paper's method on its released runs (METR/eval-analysis-public,
time-horizon-1-0 runs.jsonl: per model, logistic regression of binarized success on log2 human minutes, runs weighted
1/(runs in task x sqrt(tasks in family)), L2 penalty 1e-5; the 50% horizon where it crosses one half), the 12 frontier
models from GPT-2 (2019) to o3 (2025), by OLS of log horizon on release date, double outside 5 to 9 months (152 to
274 days), or Claude 3.7 Sonnet's 50% horizon lies outside 25 to 100 minutes.

The inputs are the repository's own files at commit 52cb829, each checked against its SHA-256 and read as data (JSON
lines parsed, the dates file read by a parser that accepts only its "date:" table; none of the repository's code is
run): reports/time-horizon-1-0/data/raw/runs.jsonl and data/external/release_dates.yaml. Every rule below was fixed
before any horizon was computed. The seed draws only the bootstrap beside the test.

1. The runs. Every run of the models named below must carry an alias, a task id and family, a run id (no run twice),
   a binarized score of 0 or 1 and a positive number of human minutes; anything else is refused. The test's models
   are FRONTIER, the paper's 12 frontier models (its section 3.2), the set its repository's headline fit keeps up to
   o3. LATER, the five models the repository's current headline adds after them (Claude 4.1 Opus, Grok 4, GPT-5,
   GPT-5.1-Codex-Max and Claude Opus 4.5), are run beside the test only.
2. The weights, as the paper's section 4 and the repository's compute_task_weights state them: within each model a
   run weighs 1/(runs of that model on the task x sqrt(tasks of the model in the task's family)), the weights then
   scaled to sum to 1.
3. The fit, as the repository's logistic_regression: for each model, the weighted logistic regression of the score
   on x = log2(human minutes), p = 1/(1 + exp(-(a x + b))), minimising sum w (log(1 + e^z) - y z) + (1e-5/2) a^2 (scikit-
   learn's LogisticRegression with C = 1/1e-5 and weights summing to 1: the intercept is not penalised), by Newton's
   method with step halving from a = 0 and b the logit of the weighted mean score, until the gradient is below
   1e-11. The 50% horizon is 2^(-b/a) minutes, the 80% horizon 2^((ln 4 - b)/a).
4. The trend, as the paper's section 4.2: ordinary least squares of the natural logarithm of each model's 50% horizon
   on its release date in days (release_dates.yaml); the doubling time is ln 2 over the slope, in days.
5. The test's two conditions: the 12 frontier models' doubling time is between 152 and 274 days inclusive; and Claude
   3.7 Sonnet's 50% horizon is between 25 and 100 minutes inclusive. test_passed is 1 if both hold.
6. Beside the test: every model's 50% horizon; the doubling time over the 11 models up to Claude 3.7 Sonnet (the
   abstract's frontier, February 2025), over those released from 2024 (the trend that "may have accelerated"), and of
   the 80% horizon (the paper: 204 days); the repository's current headline, the 12 with LATER (17 models); and a
   95% interval for the 12 models' doubling time by the paper's hierarchical bootstrap (task families, then tasks
   within them, then each model's runs on each task, all with replacement; the original weights kept, as the
   repository's bootstrap does; 1,000 samples drawn from ECDYSIS_SEED; a sample in which a model has no success or
   no finite horizon is left out and counted), with the share of samples inside 152 to 274 days. The paper prints
   207 days, 95% CI 166 to 240.
7. Controls: the weights of rule 2 equal the file's own invsqrt_task_weight column; every fit converges with a
   negative slope; the fit recovers a known logistic curve (a = -0.7, b = 3 on a grid of task lengths, its outcomes
   given as weights); and the trend recovers a known doubling time of 200 days from exact points.

What it cannot check: the runs themselves (the agents, scaffolds, scoring and human baselines are as METR recorded
them), and whether the tasks stand for real work.

Writes results/outputs.json (the values a receipt carries) and results/detail.json (every value computed).
Run with: python3 metr/horizon.py
"""

import datetime
import hashlib
import json
import math
import os
import re
import sys

import numpy as np

INPUTS = {
    "runs": ("runs.jsonl", "f489d11728909937dad99ba1ed2d7c40efe12a766891e67dbc7c2486a3311236"),
    "dates": ("release_dates.yaml", "317b92915df5bf935908567a857116bcf6f0c7686ef8b0840897ed04a29232bc"),
}
FRONTIER = ("GPT-2", "davinci-002 (GPT-3)", "gpt-3.5-turbo-instruct", "GPT-4 0314", "GPT-4 1106", "GPT-4o",
            "Claude 3.5 Sonnet (Old)", "o1-preview", "Claude 3.5 Sonnet (New)", "o1", "Claude 3.7 Sonnet", "o3")
TO_CLAUDE37 = FRONTIER[:11]
LATER = ("Claude 4.1 Opus", "Grok 4", "GPT-5", "GPT-5.1-Codex-Max", "Claude Opus 4.5")
CLAUDE37 = "Claude 3.7 Sonnet"
SINCE = datetime.date(2024, 1, 1)
LAMBDA = 1e-5
DOUBLING = (152.0, 274.0)
CLAUDE37_MINUTES = (25.0, 100.0)
BOOTSTRAP = 1000
SHORT = {"davinci-002 (GPT-3)": "davinci-002", "gpt-3.5-turbo-instruct": "gpt-3.5-instruct",
         "Claude 3.5 Sonnet (Old)": "Sonnet 3.5 old", "Claude 3.5 Sonnet (New)": "Sonnet 3.5 new",
         "Claude 3.7 Sonnet": "Sonnet 3.7", "Claude 4.1 Opus": "Opus 4.1", "Claude Opus 4.5": "Opus 4.5",
         "GPT-5.1-Codex-Max": "GPT-5.1-Codex-Max"}
OUTPUTS = ("runs", "horizons_early", "horizons_late", "horizons_later", "claude37_p50_minutes", "doubling_days",
           "r_squared", "doubling_to_claude37_days", "doubling_since_2024_days", "doubling_p80_days",
           "bootstrap_95ci", "headline_17_doubling_days", "controls_passed", "controls_total", "conditions_met",
           "conditions_total", "test_passed")
LIMIT = 200


class Refused(Exception):
    pass


def read_bytes(path, sha256):
    with open(path, "rb") as fh:
        data = fh.read()
    got = hashlib.sha256(data).hexdigest()
    if got != sha256:
        raise Refused(f"{path}: sha256 {got}, not the registered {sha256}")
    return data


def release_dates(text):
    """The 'date:' table of release_dates.yaml: {model: date}. Nothing else is accepted."""
    lines = [l for l in text.splitlines() if l.strip() and not l.lstrip().startswith("#")]
    if not lines or lines[0].strip() != "date:":
        raise Refused("release_dates.yaml does not begin with its 'date:' table")
    out = {}
    for line in lines[1:]:
        m = re.fullmatch(r"  (\S.*?): (\d{4})-(\d{2})-(\d{2})\s*", line)
        if not m:
            raise Refused(f"release_dates.yaml line {line!r} is not 'name: YYYY-MM-DD'")
        name = m.group(1)
        if name in out:
            raise Refused(f"release_dates.yaml names {name!r} twice")
        out[name] = datetime.date(int(m.group(2)), int(m.group(3)), int(m.group(4)))
    return out


def read_runs(text, models):
    """{model: [runs]} for the named models, every run checked against rule 1."""
    out = {m: [] for m in models}
    seen = set()
    for i, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        r = json.loads(line)
        if not isinstance(r, dict):
            raise Refused(f"runs.jsonl line {i} is not an object")
        alias = r.get("alias")
        if alias not in out:
            continue
        task, family, run, y, minutes = (r.get("task_id"), r.get("task_family"), r.get("run_id"),
                                         r.get("score_binarized"), r.get("human_minutes"))
        if not (isinstance(task, str) and task and isinstance(family, str) and family and isinstance(run, str) and run):
            raise Refused(f"runs.jsonl line {i}: task, family or run id missing")
        if run in seen:
            raise Refused(f"runs.jsonl line {i}: run {run} appears twice")
        seen.add(run)
        if y not in (0, 1) or isinstance(y, bool):
            raise Refused(f"runs.jsonl line {i}: binarized score {y!r} is not 0 or 1")
        if isinstance(minutes, bool) or not isinstance(minutes, (int, float)) or not minutes > 0 or \
                not math.isfinite(minutes):
            raise Refused(f"runs.jsonl line {i}: human minutes {minutes!r} is not a positive number")
        out[alias].append({"task": task, "family": family, "run": run, "y": int(y), "minutes": float(minutes),
                           "file_weight": r.get("invsqrt_task_weight")})
    for m, rs in out.items():
        if not rs:
            raise Refused(f"no runs for {m}")
    return out


def weights(runs):
    """Rule 2: 1/(runs in task x sqrt(tasks in family)) within the model, scaled to sum to 1."""
    per_task, tasks_in_family = {}, {}
    for r in runs:
        per_task[r["task"]] = per_task.get(r["task"], 0) + 1
        tasks_in_family.setdefault(r["family"], set()).add(r["task"])
    w = np.array([1.0 / (per_task[r["task"]] * math.sqrt(len(tasks_in_family[r["family"]]))) for r in runs])
    return w / w.sum()


def fit(x, y, w, lam=LAMBDA, tol=1e-11, steps=200):
    """Rule 3: (a, b, gradient norm) minimising sum w (log(1 + e^z) - y z) + lam a^2 / 2, z = a x + b."""
    def loss(a, b):
        z = a * x + b
        return float(np.sum(w * (np.logaddexp(0.0, z) - y * z)) + 0.5 * lam * a * a)

    def gradient(a, b):
        p = 0.5 * (1.0 + np.tanh(0.5 * (a * x + b)))  # the logistic function, stable at both ends
        r = w * (p - y)
        return float(np.sum(r * x) + lam * a), float(np.sum(r)), p

    mean = float(np.sum(w * y) / np.sum(w))
    mean = min(max(mean, 1e-9), 1 - 1e-9)
    a, b = 0.0, math.log(mean / (1 - mean))
    current = loss(a, b)
    for _ in range(steps):
        ga, gb, p = gradient(a, b)
        if math.hypot(ga, gb) < tol:
            break
        s = w * p * (1 - p)
        haa, hab, hbb = float(np.sum(s * x * x) + lam), float(np.sum(s * x)), float(np.sum(s))
        det = haa * hbb - hab * hab
        if not det > 0:
            raise Refused("a fit's Hessian is not positive definite")
        da, db = (hbb * ga - hab * gb) / det, (haa * gb - hab * ga) / det
        t = 1.0
        while True:
            na, nb = a - t * da, b - t * db
            new = loss(na, nb)
            if new <= current or t < 1e-12:
                break
            t /= 2
        a, b, current = na, nb, new
    ga, gb, _ = gradient(a, b)
    return a, b, math.hypot(ga, gb)


def horizon(a, b, q=0.5):
    """The task length, in minutes, at which the fitted success rate is q (infinite if it overflows)."""
    try:
        return 2.0 ** ((math.log(q / (1 - q)) - b) / a)
    except OverflowError:
        return math.inf


def days(d):
    return float((d - datetime.date(1970, 1, 1)).days)


def trend(points):
    """Rule 4: OLS of ln(horizon) on release day; (doubling days, R^2)."""
    xs = np.array([days(d) for d, _ in points])
    ys = np.array([math.log(h) for _, h in points])
    xm, ym = xs.mean(), ys.mean()
    slope = float(np.sum((xs - xm) * (ys - ym)) / np.sum((xs - xm) ** 2))
    resid = ys - (ym + slope * (xs - xm))
    r2 = 1.0 - float(np.sum(resid ** 2) / np.sum((ys - ym) ** 2))
    return math.log(2) / slope, r2


def arrays(runs):
    x = np.array([math.log2(r["minutes"]) for r in runs])
    y = np.array([float(r["y"]) for r in runs])
    return x, y


def generator(seed, label):
    return np.random.Generator(np.random.PCG64(int.from_bytes(
        hashlib.sha256(bytes.fromhex(seed) + b"|" + label.encode("ascii")).digest(), "big")))


def bootstrap(seed, data, dates, n=BOOTSTRAP):
    """Rule 6: the hierarchical bootstrap of the 12 models' doubling time; families, tasks within them, and each
    model's runs on each task, with replacement, shared across models, the original weights kept."""
    rng = generator(seed, "metr/bootstrap")
    families = {}
    for m in FRONTIER:
        for k, r in enumerate(data[m]["runs"]):
            families.setdefault(r["family"], {}).setdefault(r["task"], {}).setdefault(m, []).append(k)
    fam_names = sorted(families)
    out = []
    for _ in range(n):
        picks = {m: [] for m in FRONTIER}
        for f in rng.integers(0, len(fam_names), len(fam_names)):
            tasks = families[fam_names[f]]
            task_names = sorted(tasks)
            for t in rng.integers(0, len(task_names), len(task_names)):
                for m, ks in sorted(tasks[task_names[t]].items()):
                    picks[m].extend(ks[j] for j in rng.integers(0, len(ks), len(ks)))
        pts = []
        for m in FRONTIER:
            idx = np.array(picks[m], dtype=np.int64)
            if idx.size == 0 or not np.any(data[m]["y"][idx] > 0):
                pts = None
                break
            a, b, _ = fit(data[m]["x"][idx], data[m]["y"][idx], data[m]["w"][idx])
            h = horizon(a, b)
            if not (a < 0 and 0 < h < math.inf):
                pts = None                                   # a sample without a finite horizon is left out
                break
            pts.append((dates[m], h))
        out.append(trend(pts)[0] if pts else float("nan"))
    vals = np.array([v for v in out if math.isfinite(v)])
    lo, hi = np.quantile(vals, [0.025, 0.975])
    inside = int(np.sum((vals >= DOUBLING[0]) & (vals <= DOUBLING[1])))
    return float(lo), float(hi), inside, len(vals), out


def controls_known():
    """Rule 7's two known answers."""
    grid = np.log2(np.geomspace(1.0, 1000.0, 31))
    a0, b0 = -0.7, 3.0
    p = 1 / (1 + np.exp(-(a0 * grid + b0)))
    x = np.concatenate([grid, grid])
    y = np.concatenate([np.ones_like(grid), np.zeros_like(grid)])
    w = np.concatenate([p, 1 - p])
    w = w / w.sum()
    a, b, g = fit(x, y, w)
    logistic_ok = abs(horizon(a, b) / horizon(a0, b0) - 1) < 1e-3 and g < 1e-10
    start = datetime.date(2019, 2, 14)
    pts = [(start + datetime.timedelta(days=k), 0.05 * 2 ** (k / 200.0)) for k in (0, 300, 700, 1100, 1500, 2200)]
    trend_ok = abs(trend(pts)[0] - 200.0) < 1e-6
    return logistic_ok, trend_ok


def sig(v, n=3):
    return float(f"{v:.{n}g}")


def run(seed, inputs="inputs", results="results"):
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        raise Refused("the seed must be 64 hex characters")
    raw = {k: read_bytes(os.path.join(inputs, name), sha) for k, (name, sha) in INPUTS.items()}
    dates = release_dates(raw["dates"].decode("utf-8"))
    models = FRONTIER + LATER
    for m in models:
        if m not in dates:
            raise Refused(f"release_dates.yaml has no date for {m}")
    runs = read_runs(raw["runs"].decode("utf-8"), models)

    data, fits, worst_weight = {}, {}, 0.0
    for m in models:
        rs = runs[m]
        x, y = arrays(rs)
        w = weights(rs)
        fw = np.array([float(r["file_weight"]) if isinstance(r["file_weight"], (int, float)) else math.nan
                       for r in rs])
        worst_weight = max(worst_weight, float(np.nanmax(np.abs(w - fw) / w)) if np.all(np.isfinite(fw)) else math.inf)
        a, b, g = fit(x, y, w)
        data[m] = {"runs": rs, "x": x, "y": y, "w": w}
        fits[m] = {"a": a, "b": b, "gradient": g, "p50": horizon(a, b), "p80": horizon(a, b, 0.8),
                   "runs": len(rs), "tasks": len({r["task"] for r in rs}), "families": len({r["family"] for r in rs}),
                   "release": dates[m].isoformat()}

    def doubling(names, key="p50"):
        return trend([(dates[m], fits[m][key]) for m in names])

    d12, r2 = doubling(FRONTIER)
    d11, _ = doubling(TO_CLAUDE37)
    since = [m for m in FRONTIER if dates[m] >= SINCE]
    d24, _ = doubling(since)
    d80, _ = doubling(FRONTIER, "p80")
    d17, _ = doubling(FRONTIER + LATER)
    c37 = fits[CLAUDE37]["p50"]
    lo, hi, inside, valid, samples = bootstrap(seed, data, dates)

    cond = {
        f"the 12 frontier models double in {DOUBLING[0]:g} to {DOUBLING[1]:g} days": DOUBLING[0] <= d12 <= DOUBLING[1],
        f"Claude 3.7 Sonnet's 50% horizon is {CLAUDE37_MINUTES[0]:g} to {CLAUDE37_MINUTES[1]:g} minutes":
            CLAUDE37_MINUTES[0] <= c37 <= CLAUDE37_MINUTES[1],
    }
    logistic_ok, trend_ok = controls_known()
    controls = {
        "rule 2's weights equal the file's invsqrt_task_weight": worst_weight < 1e-6,
        "every fit converges with a negative slope": all(f["gradient"] < 1e-10 and f["a"] < 0 for f in fits.values()),
        "the fit recovers a known logistic curve": logistic_ok,
        "the trend recovers a known doubling time": trend_ok,
    }

    def listing(names):
        return ", ".join(f"{SHORT.get(m, m)} {sig(fits[m]['p50'])}" for m in names)

    tasks = {r["task"] for m in FRONTIER for r in runs[m]}
    fams = {r["family"] for m in FRONTIER for r in runs[m]}
    values = {
        "runs": (f"12 frontier models, {sum(fits[m]['runs'] for m in FRONTIER)} runs on {len(tasks)} tasks in "
                 f"{len(fams)} families; 5 later models, {sum(fits[m]['runs'] for m in LATER)} runs"),
        "horizons_early": "50% horizons, minutes: " + listing(FRONTIER[:6]),
        "horizons_late": listing(FRONTIER[6:]),
        "horizons_later": listing(LATER),
        "claude37_p50_minutes": round(c37, 2),
        "doubling_days": round(d12, 2),
        "r_squared": round(r2, 4),
        "doubling_to_claude37_days": round(d11, 2),
        "doubling_since_2024_days": round(d24, 2),
        "doubling_p80_days": round(d80, 2),
        "bootstrap_95ci": (f"{lo:.0f} to {hi:.0f} days; {inside} of {valid} samples within {DOUBLING[0]:g} to "
                           f"{DOUBLING[1]:g}"),
        "headline_17_doubling_days": round(d17, 2),
        "controls_passed": sum(controls.values()), "controls_total": len(controls),
        "conditions_met": sum(cond.values()), "conditions_total": len(cond), "test_passed": int(all(cond.values())),
    }
    out = {k: values[k] for k in OUTPUTS}
    for k, v in out.items():
        if isinstance(v, str) and len(v) > LIMIT:
            raise AssertionError(f"{k}: longer than {LIMIT} characters: {v}")
    detail = {
        "inputs": {k: {"name": n, "sha256": s} for k, (n, s) in INPUTS.items()},
        "fits": fits, "conditions": cond, "controls": controls, "worst_weight_difference": worst_weight,
        "since_2024_models": since,
        "doubling": {"frontier_12": d12, "r2": r2, "to_claude37_11": d11, "since_2024": d24, "p80": d80,
                     "headline_17": d17},
        "bootstrap": {"low": lo, "high": hi, "inside": inside, "valid": valid, "samples": samples},
    }
    os.makedirs(results, exist_ok=True)
    with open(os.path.join(results, "outputs.json"), "w", encoding="ascii") as fh:
        json.dump(out, fh, indent=2, sort_keys=True)
        fh.write("\n")
    with open(os.path.join(results, "detail.json"), "w", encoding="ascii") as fh:
        json.dump(detail, fh, indent=1, sort_keys=True, default=float)
        fh.write("\n")
    return out, detail


def main():
    seed = os.environ.get("ECDYSIS_SEED", "")
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        sys.exit("ECDYSIS_SEED must be the 64-hex seed the archive issued")
    try:
        out, _ = run(seed)
    except Refused as e:
        sys.exit(f"horizon: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
