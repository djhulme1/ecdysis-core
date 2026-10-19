#!/usr/bin/env python3
"""METR's randomised trial of early-2025 AI tools: allowing AI made experienced open-source developers 19% slower.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test is from Becker, Rush, Barnes and Rein (METR),
"Measuring the Impact of Early-2025 AI on Experienced Open-Source Developer Productivity", arXiv:2507.09089 (v2, July
2025; CC BY 4.0), its abstract: "Surprisingly, we find that allowing AI actually increases completion time by 19%--AI
tooling slowed developers down." Sixteen developers completed 246 issues on their own repositories, each issue
randomised to AI allowed or AI disallowed.

Its registered test is TEST below. Every rule was fixed before any estimate was computed from the released data. A
reading-only pass of the data before the rules (columns, types, blank cells, issue ids; no time, forecast or arm
summarised) found 16 blank post-review times, where the paper counts 27 issues whose post-review time it imputes.

1. Inputs, each checked against its SHA-256 and size and read in memory as data. The data of record, the authors'
   release (METR/Measuring-Early-2025-AI-on-Exp-OSS-Devs at 7ff2d76): data_complete.csv, read by the csv module. Its
   header must be the nine columns of COLUMNS; issue_id must run 1..N once each; dev_id an integer; the two forecasts
   and initial_implementation_time positive numbers (minutes); ai_treatment 0 or 1; post_review_implementation_time a
   number of minutes at least 0, or blank; prior_task_exposure_1_to_5 an integer 1..5 or blank, and
   external_resource_needs_1_to_3 one 1..3 or blank. Anything else refuses the run as a reading error. From the same
   release, regression.py (the authors' code, run once as a control, rule 6) and README.md (whose printed outputs are
   compared beside the test). And the paper's e-print (arXiv:2507.09089v2), a gzipped tar opened in memory and never
   unpacked: its macros.tex holds every number the paper prints as \\newcommand{\\Name}{value}, and those values are
   the printed values compared beside the test.
2. The estimator, the paper's equation (1) and its released code: total implementation time T = initial plus
   post-review time, a blank post-review time imputed as the mean of the observed post-review times of the issue's
   arm; ordinary least squares of ln T on an intercept, AI allowed (0/1) and ln of the developer's forecast without
   AI. The slowdown is S = exp(b) - 1 for the coefficient b of AI allowed, and its 95% interval
   exp(b - z SE) - 1 to exp(b + z SE) - 1, z = the 0.975 normal quantile. Three standard errors: non-robust
   (s^2 (X'X)^-1, s^2 = RSS/(N - 3)), which the released code says the paper uses; HC3, which the paper's appendix
   says it reports by default; and clustered by developer as the released code computes it (statsmodels' default,
   with the factor G/(G - 1) (N - 1)/(N - 3)).
3. The test's conditions: (i) the data are the paper's sample, 246 issues of 16 developers, 136 with AI allowed and
   110 without (its macros' counts); (ii) S rounds to 19% (100 S at least 18.5 and below 19.5); (iii) the 95%
   interval lies above zero with the non-robust and with the HC3 standard error. test_passed is 1 if all three hold.
4. Beside the test, none of it counted, each set against the value the e-print prints (a percentage rounded to the
   integer, compared with 100 x rounded; an interval under both standard errors): the README's printed outputs (to
   their three decimals); the post-review imputation by zero, by the overall mean, by the developer's own mean (the
   overall mean for a developer with none), and with one hour for the blank times of one arm and zero for the other;
   the outcome as initial time alone, and, over the issues whose post-review time is recorded, initial time, total
   time and post-review time (as ln(1 + minutes), its zeros kept); the estimator without a covariate, with the log
   forecast with AI allowed, and with the log forecast without AI and developer fixed effects; the issues with both
   prior task exposure and external resource needs recorded; the ratio of mean times (and of mean forecasts, the
   paper's 24% and its arms' 22% and 25%), with 95% intervals from a pooled bootstrap of the issues (10,000 draws from
   the seed); Pearson's correlation of each arm's forecast with its time (as minutes and as logarithms, with total and
   with initial time); the post-review times' means, medians and shares of zero by arm; the counts of issues with and
   without a post-review time; a two-stage bootstrap of the regression's slowdown (developers, then issues within
   them; 2,000 draws); and a randomisation p value from 10,000 permutations of the arms within each developer.
5. Not in the release, and so not checked: the issues randomised other than by coin flip, the screen recordings, the
   exit surveys (the developers' post-hoc 20%), the expert forecasts (39% and 38%) and the dates.
6. Controls (controls_passed counts those that behave as stated): (1) the authors' regression.py, run from the input
   in memory under the image's Python, prints the slowdown and the three intervals this module computes, to its three
   decimals; (2) this module's least squares equals statsmodels' (the image's) in b and in all three standard errors
   (relative difference below 1e-9), and b equals the exact rational solution of the normal equations on the same
   floating-point inputs (below 1e-12); (3) the arms swapped give exactly -b, and ln 1.5 added to every AI-allowed
   log time gives exactly b + ln 1.5 (below 1e-12); (4) the mean of the permuted coefficients lies within four of
   its standard errors of zero.

What it cannot check: the trial itself (the recruitment, the randomisation, the self-reported times and the issues'
validity are as METR recorded them), and whether the effect generalises beyond these developers and early-2025 tools.

Writes results/outputs.json (the values a receipt carries) and results/detail.json (every value computed).
Run with: python3 metr/becker2025.py
"""

import csv
import hashlib
import io
import json
import math
import os
import re
import subprocess
import sys
import tarfile
from fractions import Fraction

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_CORETYPE", "Prescott")

import numpy as np  # noqa: E402

TEST = ("Refuted if the paper's estimator on its released data does not give a slowdown that rounds to 19% with a 95% "
        "interval above zero, or the data are not its 246 issues of 16 developers (136 with AI allowed): OLS of the "
        "log of total implementation time (initial plus post-review time, a missing post-review time imputed as its "
        "arm's mean) on AI allowed and the log of the developer's forecast without AI; slowdown exp(b) - 1, interval "
        "exp(b +/- 1.96 SE) - 1, with the non-robust standard error the released code names and the HC3 the appendix "
        "names.")

REPO = "METR/Measuring-Early-2025-AI-on-Exp-OSS-Devs"
DATA = ("data_complete.csv", "1493fc46dc379b15d2c39273fa7a7ee98767ff0d90dea113f300d7338f165746", 8819)
CODE = ("regression.py", "41307fa0b2f617eb815fdaaf41ee18c04fb7332eab118e86c1556154f496afd6", 5310)
README = ("README.md", "8d9ce0ac356c12606299a7f2f3a5ccad4b0ce2e344759e837bc65d4542541dd4", 2781)
EPRINT = ("arXiv-2507.09089v2.tar.gz", "1671577c51037bd3b9e396c115c1a4152a42a4b5898d996a564622f71ea84170", 5730251)
MACROS = "macros.tex"
COLUMNS = ("dev_id", "issue_id", "predicted_time_no_ai", "predicted_time_ai_allowed", "prior_task_exposure_1_to_5",
           "external_resource_needs_1_to_3", "ai_treatment", "initial_implementation_time",
           "post_review_implementation_time")
SAMPLE = {"issues": "NumIssuesAllInitialImplementationFinishedValid",
          "ai": "NumIssuesAIAllowedAllInitialImplementationFinishedValid",
          "noai": "NumIssuesNoAIAllInitialImplementationFinishedValid",
          "developers": "NumUniqueDevelopersAllInitialImplementationFinishedValid"}
CLAIMED = 19
Z = 1.959963984540054
RATIO_DRAWS = 10000
TWO_STAGE_DRAWS = 2000
PERMUTATIONS = 10000
OUTPUTS = ("sample", "beta", "slowdown", "slowdown_pct", "se_nonrobust", "se_hc3", "se_cluster", "ci_nonrobust",
           "ci_hc3", "ci_cluster", "readme", "imputation", "outcomes", "estimators", "exposure_subset", "ratio",
           "forecasts", "correlations", "review_times", "counts", "two_stage", "randomisation_p", "printed",
           "printed_matched", "printed_total", "authors_code", "conditions_met", "conditions_total", "test_passed",
           "controls_passed", "controls_total")
LIMIT = 200


class Refused(Exception):
    pass


# ---------------------------------------------------------------- inputs

def read_input(inputs, spec):
    name, sha, size = spec
    with open(os.path.join(inputs, name), "rb") as fh:
        data = fh.read()
    got = hashlib.sha256(data).hexdigest()
    if got != sha or len(data) != size:
        raise Refused(f"{name}: sha256 {got} ({len(data)} bytes), not the registered {sha} ({size})")
    return data


def number(text, what, positive=False, nonnegative=False, blank=False):
    if text == "":
        if blank:
            return None
        raise Refused(f"{what}: blank")
    try:
        v = float(text)
    except ValueError:
        raise Refused(f"{what}: {text!r} is not a number")
    if not math.isfinite(v) or (positive and v <= 0) or (nonnegative and v < 0):
        raise Refused(f"{what}: {text!r} out of range")
    return v


def whole(text, what, low=None, high=None, blank=False):
    v = number(text, what, blank=blank)
    if v is None:
        return None
    if v != int(v) or (low is not None and v < low) or (high is not None and v > high):
        raise Refused(f"{what}: {text!r} is not an integer in range")
    return int(v)


def read_data(data):
    """Rule 1: the rows of data_complete.csv as dicts."""
    try:
        rows = list(csv.reader(io.StringIO(data.decode("utf-8"), newline="")))
    except (UnicodeDecodeError, csv.Error) as e:
        raise Refused(f"{DATA[0]}: {e}")
    if not rows or tuple(rows[0]) != COLUMNS:
        raise Refused(f"{DATA[0]}: header {rows[0] if rows else None!r}")
    out = []
    for k, r in enumerate(rows[1:], 2):
        if len(r) != len(COLUMNS):
            raise Refused(f"{DATA[0]} line {k}: {len(r)} cells")
        c = dict(zip(COLUMNS, r))
        out.append({
            "dev": whole(c["dev_id"], f"line {k} dev_id"),
            "issue": whole(c["issue_id"], f"line {k} issue_id", 1),
            "f_noai": number(c["predicted_time_no_ai"], f"line {k} predicted_time_no_ai", positive=True),
            "f_ai": number(c["predicted_time_ai_allowed"], f"line {k} predicted_time_ai_allowed", positive=True),
            "exposure": whole(c["prior_task_exposure_1_to_5"], f"line {k} prior_task_exposure", 1, 5, blank=True),
            "resources": whole(c["external_resource_needs_1_to_3"], f"line {k} external_resource_needs", 1, 3,
                               blank=True),
            "ai": whole(c["ai_treatment"], f"line {k} ai_treatment", 0, 1),
            "initial": number(c["initial_implementation_time"], f"line {k} initial time", positive=True),
            "post": number(c["post_review_implementation_time"], f"line {k} post-review time", nonnegative=True,
                           blank=True),
        })
    if sorted(r["issue"] for r in out) != list(range(1, len(out) + 1)):
        raise Refused(f"{DATA[0]}: issue_id does not run 1..{len(out)} once each")
    return out


def read_macros(eprint):
    """Rule 1: \\newcommand{\\Name}{value} from the e-print's macros.tex, read in memory."""
    try:
        with tarfile.open(fileobj=io.BytesIO(eprint), mode="r:gz") as tf:
            member = tf.getmember(MACROS)
            if not member.isfile():
                raise Refused(f"{MACROS} is not a file in the e-print")
            tex = tf.extractfile(member).read().decode("utf-8")
    except (tarfile.TarError, KeyError, UnicodeDecodeError, OSError) as e:
        raise Refused(f"the e-print: {e}")
    return parse_macros(tex)


def parse_macros(tex):
    out = {}
    for m in re.finditer(r"\\newcommand\{\\([A-Za-z]+)\}\{([^{}]*)\}", tex):
        out[m.group(1)] = m.group(2)
    return out


def macro_number(macros, name):
    if name not in macros:
        raise Refused(f"the e-print defines no \\{name}")
    try:
        return float(macros[name].replace(",", ""))
    except ValueError:
        raise Refused(f"\\{name} is {macros[name]!r}, not a number")


README_LINES = (
    ("speedup", re.compile(r"Regression calculated speedup of:\s+(-?[\d.]+)")),
    ("Homoskedastic", re.compile(r"stderr=Homoskedastic:\s*\((-?[\d.]+),\s*(-?[\d.]+)\)")),
    ("Robust (HC3)", re.compile(r"stderr=Robust \(HC3\):\s*\((-?[\d.]+),\s*(-?[\d.]+)\)")),
    ("Clustered By Dev", re.compile(r"stderr=Clustered By Dev:\s*\((-?[\d.]+),\s*(-?[\d.]+)\)")),
)


def parse_printed_run(text):
    """The four printed lines of the README or of the authors' code: {name: value or (low, high)}."""
    out = {}
    for name, rx in README_LINES:
        m = rx.search(text)
        if m is None:
            out[name] = None
        elif name == "speedup":
            out[name] = float(m.group(1))
        else:
            out[name] = (float(m.group(1)), float(m.group(2)))
    return out


# ---------------------------------------------------------------- the estimator

def impute(rows, how="arm"):
    """Rule 2 (arm) and rule 4's variants: the post-review time of every row, blanks filled."""
    seen = [r for r in rows if r["post"] is not None]
    arm = {a: np.mean([r["post"] for r in seen if r["ai"] == a]) for a in (0, 1)}
    overall = np.mean([r["post"] for r in seen])
    dev = {}
    for r in seen:
        dev.setdefault(r["dev"], []).append(r["post"])
    out = []
    for r in rows:
        if r["post"] is not None:
            out.append(r["post"])
        elif how == "arm":
            out.append(float(arm[r["ai"]]))
        elif how == "zero":
            out.append(0.0)
        elif how == "overall":
            out.append(float(overall))
        elif how == "developer":
            out.append(float(np.mean(dev[r["dev"]])) if r["dev"] in dev else float(overall))
        elif how == "hour_ai":
            out.append(60.0 if r["ai"] == 1 else 0.0)
        elif how == "hour_noai":
            out.append(60.0 if r["ai"] == 0 else 0.0)
        else:
            raise ValueError(how)
    return np.asarray(out, dtype=np.float64)


def ols(y, X, groups=None):
    """Least squares with the three standard errors of rule 2. Returns b (vector) and {name: SE vector}."""
    y = np.asarray(y, dtype=np.float64)
    X = np.asarray(X, dtype=np.float64)
    n, k = X.shape
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    e = y - X @ b
    xtx_inv = np.linalg.inv(X.T @ X)
    s2 = float(e @ e) / (n - k)
    se = {"nonrobust": np.sqrt(np.diag(xtx_inv) * s2)}
    h = np.einsum("ij,jk,ik->i", X, xtx_inv, X)
    w = (e / (1.0 - h)) ** 2
    meat = X.T @ (X * w[:, None])
    se["hc3"] = np.sqrt(np.diag(xtx_inv @ meat @ xtx_inv))
    if groups is not None:
        groups = np.asarray(groups)
        labels = sorted(set(groups.tolist()))
        g = len(labels)
        meat = np.zeros((k, k))
        for lab in labels:
            sel = groups == lab
            s = X[sel].T @ e[sel]
            meat += np.outer(s, s)
        c = g / (g - 1) * (n - 1) / (n - k)
        se["cluster"] = np.sqrt(np.diag(xtx_inv @ meat @ xtx_inv) * c)
    return b, se


def design(rows, outcome, covariate="f_noai", fixed_effects=False):
    """ln outcome on [1, AI, ln covariate (+ developer dummies)]."""
    y = np.log(np.asarray(outcome, dtype=np.float64))
    cols = [np.ones(len(rows)), np.asarray([r["ai"] for r in rows], dtype=np.float64)]
    if covariate is not None:
        cols.append(np.log(np.asarray([r[covariate] for r in rows], dtype=np.float64)))
    if fixed_effects:
        devs = sorted({r["dev"] for r in rows})
        for d in devs[1:]:
            cols.append(np.asarray([1.0 if r["dev"] == d else 0.0 for r in rows]))
    return y, np.column_stack(cols)


def effect(rows, outcome, covariate="f_noai", fixed_effects=False):
    y, X = design(rows, outcome, covariate, fixed_effects)
    b, se = ols(y, X, groups=[r["dev"] for r in rows])
    beta = float(b[1])
    out = {"beta": beta, "s": math.exp(beta) - 1, "n": len(rows)}
    for name, v in se.items():
        s = float(v[1])
        out[f"se_{name}"] = s
        out[f"ci_{name}"] = (math.exp(beta - Z * s) - 1, math.exp(beta + Z * s) - 1)
    return out


def total_time(rows, how="arm"):
    return np.asarray([r["initial"] for r in rows]) + impute(rows, how)


def exact_beta(y, X):
    """The normal equations solved in exact rational arithmetic on the floating-point inputs."""
    Xf = [[Fraction(float(v)) for v in row] for row in X]
    yf = [Fraction(float(v)) for v in y]
    k = len(Xf[0])
    A = [[sum(r[i] * r[j] for r in Xf) for j in range(k)] for i in range(k)]
    c = [sum(r[i] * t for r, t in zip(Xf, yf)) for i in range(k)]
    for i in range(k):
        p = next(j for j in range(i, k) if A[j][i] != 0)
        A[i], A[p], c[i], c[p] = A[p], A[i], c[p], c[i]
        for j in range(k):
            if j != i and A[j][i] != 0:
                f = A[j][i] / A[i][i]
                A[j] = [a - f * bb for a, bb in zip(A[j], A[i])]
                c[j] -= f * c[i]
    return [c[i] / A[i][i] for i in range(k)]


# ---------------------------------------------------------------- the seeded draws

class Stream:
    """Integers from the seed: SHA-256 of seed, label and a counter (as schur/fs.py's)."""

    def __init__(self, seed, label):
        self.seed, self.label, self.n = seed, label, 0

    def rng(self):
        self.n += 1
        h = hashlib.sha256(f"{self.seed}/{self.label}/{self.n}".encode()).digest()
        return np.random.Generator(np.random.PCG64(int.from_bytes(h[:16], "big")))


def ratio_of_means(x, ai):
    return float(np.mean(x[ai == 1]) / np.mean(x[ai == 0]) - 1)


def pooled_bootstrap(x, ai, draws, rng):
    n = len(x)
    out = np.empty(draws)
    for d in range(draws):
        idx = rng.integers(0, n, n)
        xi, ai_i = x[idx], ai[idx]
        if not (ai_i == 1).any() or not (ai_i == 0).any():
            out[d] = np.nan
            continue
        out[d] = ratio_of_means(xi, ai_i)
    out = out[np.isfinite(out)]
    return float(np.quantile(out, 0.025)), float(np.quantile(out, 0.975))


def two_stage(rows, total, draws, rng):
    devs = sorted({r["dev"] for r in rows})
    by_dev = {d: [i for i, r in enumerate(rows) if r["dev"] == d] for d in devs}
    out = []
    for _ in range(draws):
        idx = []
        for d in rng.choice(devs, len(devs), replace=True):
            members = by_dev[int(d)]
            idx.extend(rng.choice(members, len(members), replace=True).tolist())
        sub = [rows[i] for i in idx]
        ai = np.asarray([r["ai"] for r in sub])
        if ai.min() == ai.max():
            continue
        y, X = design(sub, total[idx])
        b, *_ = np.linalg.lstsq(X, y, rcond=None)
        out.append(math.exp(float(b[1])) - 1)
    out = np.asarray(out)
    return float(np.quantile(out, 0.025)), float(np.quantile(out, 0.975)), len(out)


def permutation_betas(rows, total, draws, rng):
    y, X = design(rows, total)
    devs = np.asarray([r["dev"] for r in rows])
    ai = X[:, 1].copy()
    blocks = [np.flatnonzero(devs == d) for d in sorted(set(devs.tolist()))]
    out = np.empty(draws)
    Xp = X.copy()
    for d in range(draws):
        perm = ai.copy()
        for blk in blocks:
            perm[blk] = ai[rng.permutation(blk)]
        Xp[:, 1] = perm
        b, *_ = np.linalg.lstsq(Xp, y, rcond=None)
        out[d] = b[1]
    return out


# ---------------------------------------------------------------- comparison with the printed values

def pct(x):
    return int(math.floor(100 * x + 0.5))


def half_up(x, decimals):
    f = 10 ** decimals
    return math.floor(x * f + 0.5) / f


def decimals_of(text):
    t = text.strip().replace(",", "")
    return len(t.split(".")[1]) if "." in t else 0


class Printed:
    def __init__(self, macros):
        self.macros, self.rows = macros, []

    def value(self, name, computed, scale=100):
        """A printed value against the computed one rounded half up to the printed number of decimals (a
        percentage when scale is 100)."""
        printed = macro_number(self.macros, name)
        got = computed * scale
        ok = half_up(got, decimals_of(self.macros[name])) == printed
        self.rows.append({"name": name, "printed": printed, "computed": got, "match": bool(ok)})
        return ok

    def interval(self, base, est):
        pt = self.value(base, est["s"])
        lo_name, hi_name = base + "LowerCI", base + "UpperCI"
        res = {}
        for se in ("hc3", "nonrobust"):
            lo, hi = est[f"ci_{se}"]
            res[se] = (pct(lo) == int(round(macro_number(self.macros, lo_name))) and
                       pct(hi) == int(round(macro_number(self.macros, hi_name))))
        self.rows.append({"name": base + " interval", "printed": (macro_number(self.macros, lo_name),
                                                                   macro_number(self.macros, hi_name)),
                          "computed": {se: [100 * v for v in est[f"ci_{se}"]] for se in ("hc3", "nonrobust")},
                          "match": bool(res["hc3"] or res["nonrobust"]), "by_se": res})
        return pt, res

    def matched(self):
        return sum(r["match"] for r in self.rows), len(self.rows)

    def misses(self):
        return [r["name"] for r in self.rows if not r["match"]]


def fmt_ci(ci):
    return f"({100 * ci[0]:.1f}, {100 * ci[1]:.1f})"


def short(est, se="hc3"):
    return f"{100 * est['s']:.1f}% {fmt_ci(est['ci_' + se])}"


# ---------------------------------------------------------------- the run

def run(seed, inputs="inputs", results="results"):
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        raise Refused("the seed must be 64 hex characters")
    rows = read_data(read_input(inputs, DATA))
    code = read_input(inputs, CODE)
    readme = parse_printed_run(read_input(inputs, README).decode("utf-8"))
    macros = read_macros(read_input(inputs, EPRINT))
    pr = Printed(macros)

    ai = np.asarray([r["ai"] for r in rows])
    n_ai, n_noai = int((ai == 1).sum()), int((ai == 0).sum())
    devs = sorted({r["dev"] for r in rows})
    blanks = [r for r in rows if r["post"] is None]
    total = total_time(rows)

    # the test
    main = effect(rows, total)
    sample_ok = (len(rows) == macro_number(macros, SAMPLE["issues"]) == 246 and
                 len(devs) == macro_number(macros, SAMPLE["developers"]) == 16 and
                 n_ai == macro_number(macros, SAMPLE["ai"]) == 136 and
                 n_noai == macro_number(macros, SAMPLE["noai"]) == 110)
    cond = {
        "the data are the paper's 246 issues of 16 developers, 136 with AI allowed and 110 without": sample_ok,
        "the slowdown rounds to 19%": 18.5 <= 100 * main["s"] < 19.5,
        "its 95% interval lies above zero with the non-robust and with the HC3 standard error": (
            main["ci_nonrobust"][0] > 0 and main["ci_hc3"][0] > 0),
    }

    # beside: the README's printed run and the paper's printed values
    ours_printed = {"speedup": round(main["s"], 3), "Homoskedastic": tuple(round(v, 3) for v in main["ci_nonrobust"]),
                    "Robust (HC3)": tuple(round(v, 3) for v in main["ci_hc3"]),
                    "Clustered By Dev": tuple(round(v, 3) for v in main["ci_cluster"])}
    readme_match = {k: readme.get(k) is not None and tuple(np.atleast_1d(readme[k])) ==
                    tuple(np.atleast_1d(ours_printed[k])) for k in ours_printed}
    pr.interval("PctSpeedupBaseline", main)
    variants = {}
    for how, name in (("zero", "PctSpeedupBaselineImputationZero"),
                      ("overall", "PctSpeedupBaselineImputationOverallMean"),
                      ("developer", "PctSpeedupBaselineImputationPerDeveloperMean"),
                      ("hour_noai", "PctSpeedupBaselineImputationAddOneHourAIDisallowedIssues"),
                      ("hour_ai", "PctSpeedupBaselineImputationAddOneHourAIAllowedIssues")):
        variants[how] = effect(rows, total_time(rows, how))
        pr.interval(name, variants[how])
    initial = np.asarray([r["initial"] for r in rows])
    outcomes = {"initial": effect(rows, initial)}
    pr.interval("PctSpeedupInitialImplementationFinishedIssuesInitialImplementationTime", outcomes["initial"])
    done = [r for r in rows if r["post"] is not None]
    outcomes["complete_initial"] = effect(done, [r["initial"] for r in done])
    outcomes["complete_total"] = effect(done, [r["initial"] + r["post"] for r in done])
    outcomes["complete_post"] = effect(done, [1.0 + r["post"] for r in done])
    pr.interval("PctSpeedupFinishedCompleteIssuesInitialImplementationTime", outcomes["complete_initial"])
    pr.interval("PctSpeedupFinishedCompleteIssuesTotalImplementationTime", outcomes["complete_total"])
    pr.interval("PctSpeedupFinishedCompleteIssuesPostReviewTime", outcomes["complete_post"])
    estimators = {"none": effect(rows, total, covariate=None), "f_ai": effect(rows, total, covariate="f_ai"),
                  "fixed": effect(rows, total, fixed_effects=True)}
    pr.interval("PctSpeedupRegressionWithoutLogForecastNoAI", estimators["none"])
    pr.interval("PctSpeedupRegressionWithLogForecastAIAllowed", estimators["f_ai"])
    pr.interval("PctSpeedupRegressionWithLogForecastNoAIAndFixedEffects", estimators["fixed"])
    exp_rows = [i for i, r in enumerate(rows) if r["exposure"] is not None and r["resources"] is not None]
    exposure = effect([rows[i] for i in exp_rows], total[exp_rows])
    pr.interval("PctSpeedupBaselinePriorTaskExposureAndExternalResourceNeedsDefined", exposure)
    st = Stream(seed, "becker2025/ratio")
    ratio = {"s": ratio_of_means(total, ai)}
    ratio["ci"] = pooled_bootstrap(total, ai, RATIO_DRAWS, st.rng())
    pr.value("PctSpeedupRatioEstimator", ratio["s"])
    ratio_ci_ok = (pct(ratio["ci"][0]) == int(macro_number(macros, "PctSpeedupRatioEstimatorLowerCI")) and
                   pct(ratio["ci"][1]) == int(macro_number(macros, "PctSpeedupRatioEstimatorUpperCI")))
    f_ai = np.asarray([r["f_ai"] for r in rows])
    f_noai = np.asarray([r["f_noai"] for r in rows])
    forecast = {"all": float(f_ai.mean() / f_noai.mean() - 1),
                "noai": float(f_ai[ai == 0].mean() / f_noai[ai == 0].mean() - 1),
                "ai": float(f_ai[ai == 1].mean() / f_noai[ai == 1].mean() - 1)}
    st = Stream(seed, "becker2025/forecast")
    rng = st.rng()
    fb = np.empty(RATIO_DRAWS)
    for d in range(RATIO_DRAWS):
        idx = rng.integers(0, len(rows), len(rows))
        fb[d] = f_ai[idx].mean() / f_noai[idx].mean() - 1
    forecast["ci"] = (float(np.quantile(fb, 0.025)), float(np.quantile(fb, 0.975)))
    pr.value("PctSpeedupForecast", forecast["all"])
    pr.value("PctSpeedupForecastNoAI", forecast["noai"])
    pr.value("PctSpeedupForecastAIAllowed", forecast["ai"])
    forecast_ci_ok = (pct(forecast["ci"][0]) == int(macro_number(macros, "PctSpeedupForecastLowerCI")) and
                      pct(forecast["ci"][1]) == int(macro_number(macros, "PctSpeedupForecastUpperCI")))
    corr = {}
    for arm, fc, name in ((1, f_ai, "CorrForecastAndImplementationTimeAIAllowed"),
                          (0, f_noai, "CorrForecastAndImplementationTimeNoAI")):
        sel = ai == arm
        readings = {"minutes, total": float(np.corrcoef(fc[sel], total[sel])[0, 1]),
                    "logs, total": float(np.corrcoef(np.log(fc[sel]), np.log(total[sel]))[0, 1]),
                    "minutes, initial": float(np.corrcoef(fc[sel], initial[sel])[0, 1]),
                    "logs, initial": float(np.corrcoef(np.log(fc[sel]), np.log(initial[sel]))[0, 1])}
        printed = macro_number(macros, name)
        corr[name] = {"printed": printed, "readings": readings,
                      "matching": [k for k, v in readings.items() if round(v, 2) == printed]}
        pr.rows.append({"name": name, "printed": printed, "computed": readings,
                        "match": bool(corr[name]["matching"])})
    review = {}
    for arm, tag in ((1, "AIAllowed"), (0, "NoAI")):
        vals = np.asarray([r["post"] for r in done if r["ai"] == arm])
        review[tag] = {"mean": float(vals.mean()), "median": float(np.median(vals)),
                       "zero_share": float((vals == 0).mean()), "n": int(vals.size)}
        pr.value(f"MeanReviewTimeMinutes{tag}", review[tag]["mean"], scale=1)
        pr.value(f"MedianReviewTimeMinutes{tag}", review[tag]["median"], scale=1)
        pr.value(f"PercentileZeroReviewTime{tag}", review[tag]["zero_share"])
    overall_median = float(np.median([r["post"] for r in done]))
    pr.value("MedianReviewTimeMinutesOverall", overall_median, scale=1)
    counts = {"blank post-review": len(blanks), "blank, AI allowed": sum(r["ai"] for r in blanks),
              "blank, AI disallowed": sum(1 - r["ai"] for r in blanks), "recorded": len(done),
              "recorded, AI allowed": sum(r["ai"] for r in done), "recorded, AI disallowed": sum(1 - r["ai"] for r in done)}
    for key, name in (("blank post-review", "NumIssuesInitialImplementationStartedButNotFinished"),
                      ("blank, AI allowed", "NumIssuesInitialImplementationStartedButNotFinishedInAIAllowed"),
                      ("blank, AI disallowed", "NumIssuesInitialImplementationStartedButNotFinishedNoAIAllowed"),
                      ("recorded", "NumIssuesAllFinishedCompleteValid"),
                      ("recorded, AI allowed", "NumIssuesAIAllowedAllFinishedCompleteValid"),
                      ("recorded, AI disallowed", "NumIssuesNoAIAllFinishedCompleteValid")):
        pr.value(name, counts[key], scale=1)
    st = Stream(seed, "becker2025/two-stage")
    ts = two_stage(rows, total, TWO_STAGE_DRAWS, st.rng())
    st = Stream(seed, "becker2025/permutation")
    perm = permutation_betas(rows, total, PERMUTATIONS, st.rng())
    p_one = float((1 + np.sum(perm >= main["beta"])) / (1 + PERMUTATIONS))
    p_two = float((1 + np.sum(np.abs(perm) >= abs(main["beta"]))) / (1 + PERMUTATIONS))

    # controls
    ctl, ctl_detail = {}, {}
    proc = subprocess.run([sys.executable, "-I", "-", "--input-data", os.path.join(inputs, DATA[0])], input=code,
                          capture_output=True, timeout=600)
    authors = parse_printed_run(proc.stdout.decode("utf-8", "replace"))
    authors_match = {k: authors.get(k) is not None and tuple(np.atleast_1d(authors[k])) ==
                     tuple(np.atleast_1d(ours_printed[k])) for k in ours_printed}
    ctl["the authors' regression.py prints this module's slowdown and three intervals to its three decimals"] = (
        proc.returncode == 0 and all(authors_match.values()))
    ctl_detail["authors_code"] = {"returncode": proc.returncode, "stdout": proc.stdout.decode("utf-8", "replace"),
                                  "stderr": proc.stderr.decode("utf-8", "replace")[-2000:], "parsed": authors,
                                  "match": authors_match}
    import statsmodels.api as sm
    y, X = design(rows, total)
    sm_res = {name: sm.OLS(y, X).fit(**kw) for name, kw in (
        ("nonrobust", {}), ("hc3", {"cov_type": "HC3"}),
        ("cluster", {"cov_type": "cluster", "cov_kwds": {"groups": np.asarray([r["dev"] for r in rows])}}))}
    rel = {name: abs(float(res.bse[1]) - main[f"se_{name}"]) / main[f"se_{name}"] for name, res in sm_res.items()}
    beta_rel = abs(float(sm_res["nonrobust"].params[1]) - main["beta"]) / abs(main["beta"])
    exact = exact_beta(y, X)
    exact_diff = abs(float(exact[1]) - main["beta"])
    ctl["least squares equals statsmodels' in b and three standard errors, and the exact normal equations in b"] = (
        beta_rel < 1e-9 and max(rel.values()) < 1e-9 and exact_diff < 1e-12)
    ctl_detail["statsmodels"] = {"beta_rel": beta_rel, "se_rel": rel, "exact_beta_diff": exact_diff}
    Xs = X.copy()
    Xs[:, 1] = 1 - Xs[:, 1]
    b_swap, *_ = np.linalg.lstsq(Xs, y, rcond=None)
    y_shift = y + math.log(1.5) * X[:, 1]
    b_shift, *_ = np.linalg.lstsq(X, y_shift, rcond=None)
    swap_diff = abs(float(b_swap[1]) + main["beta"])
    shift_diff = abs(float(b_shift[1]) - (main["beta"] + math.log(1.5)))
    ctl["the arms swapped give exactly -b, and ln 1.5 added to the AI-allowed log times b + ln 1.5"] = (
        swap_diff < 1e-12 and shift_diff < 1e-12)
    ctl_detail["swap_shift"] = {"swap": swap_diff, "shift": shift_diff}
    perm_sd = float(np.std(perm, ddof=1))
    perm_mean = float(np.mean(perm))
    ctl["the permuted coefficients centre on zero (within four standard errors of their mean)"] = (
        abs(perm_mean) < 4 * perm_sd / math.sqrt(PERMUTATIONS))
    ctl_detail["permutation"] = {"mean": perm_mean, "sd": perm_sd, "p_one_sided": p_one, "p_two_sided": p_two}

    matched, total_printed = pr.matched()
    misses = pr.misses()
    values = {
        "sample": (f"{len(rows)} issues of {len(devs)} developers, {n_ai} with AI allowed, {n_noai} without; "
                   f"{len(blanks)} post-review times blank ({counts['blank, AI allowed']} with AI, "
                   f"{counts['blank, AI disallowed']} without), imputed by arm means"),
        "beta": round(main["beta"], 6),
        "slowdown": round(main["s"], 6),
        "slowdown_pct": pct(main["s"]),
        "se_nonrobust": round(main["se_nonrobust"], 6),
        "se_hc3": round(main["se_hc3"], 6),
        "se_cluster": round(main["se_cluster"], 6),
        "ci_nonrobust": f"{100 * main['ci_nonrobust'][0]:.2f}% to {100 * main['ci_nonrobust'][1]:.2f}%",
        "ci_hc3": f"{100 * main['ci_hc3'][0]:.2f}% to {100 * main['ci_hc3'][1]:.2f}%",
        "ci_cluster": f"{100 * main['ci_cluster'][0]:.2f}% to {100 * main['ci_cluster'][1]:.2f}%",
        "readme": (f"README's printed run: {sum(readme_match.values())} of 4 lines match to 3 decimals"
                   + ("" if all(readme_match.values()) else
                      " (not: " + ", ".join(k for k, v in readme_match.items() if not v) + ")")),
        "imputation": "; ".join(f"{k} {short(v)}" for k, v in variants.items()),
        "outcomes": (f"initial {short(outcomes['initial'])}; recorded {len(done)}: initial "
                     f"{short(outcomes['complete_initial'])}, total {short(outcomes['complete_total'])}, "
                     f"post-review {short(outcomes['complete_post'])}"),
        "estimators": (f"no covariate {short(estimators['none'])}; AI-allowed forecast {short(estimators['f_ai'])}; "
                       f"fixed effects {short(estimators['fixed'])}"),
        "exposure_subset": f"{len(exp_rows)} issues with both recorded: {short(exposure)}",
        "ratio": (f"ratio of mean times {100 * ratio['s']:.1f}%, pooled bootstrap {fmt_ci(ratio['ci'])}"
                  f"{' as printed' if ratio_ci_ok else ' (printed 5 to 70)'}"),
        "forecasts": (f"forecast ratio {100 * forecast['all']:.1f}% {fmt_ci(forecast['ci'])}"
                      f"{'' if forecast_ci_ok else ' (interval not as printed)'}; arms: without AI "
                      f"{100 * forecast['noai']:.1f}%, with {100 * forecast['ai']:.1f}%"),
        "correlations": "; ".join(f"{'AI allowed' if 'AIAllowed' in k else 'AI disallowed'} {v['printed']}: "
                                  + (", ".join(v["matching"]) or "no reading") for k, v in corr.items()),
        "review_times": "; ".join(f"{k}: mean {v['mean']:.1f}, median {v['median']:.1f}, zero {100 * v['zero_share']:.0f}%"
                                  for k, v in review.items()) + f"; median overall {overall_median:.1f}",
        "counts": (f"post-review recorded {counts['recorded']} ({counts['recorded, AI allowed']} with AI), blank "
                   f"{counts['blank post-review']}; the paper: 219 (122) and 27"),
        "two_stage": f"two-stage bootstrap {fmt_ci(ts[:2])} from {ts[2]} draws",
        "randomisation_p": round(p_one, 6),
        "printed": ("not as printed: " + ", ".join(m.replace("PctSpeedup", "").replace("NumIssues", "N")[:40]
                                                   for m in misses))[:LIMIT] if misses else "all as printed",
        "printed_matched": matched,
        "printed_total": total_printed,
        "authors_code": ("prints " + ", ".join(f"{k} {authors[k]}" for k in ("speedup",) if authors.get(k) is not None)
                         + f"; {sum(authors_match.values())} of 4 lines match"),
        "conditions_met": sum(cond.values()), "conditions_total": len(cond), "test_passed": int(all(cond.values())),
        "controls_passed": sum(ctl.values()), "controls_total": len(ctl),
    }
    out = {k: values[k] for k in OUTPUTS}
    for key, v in out.items():
        if isinstance(v, str) and len(v) > LIMIT:
            raise AssertionError(f"{key}: longer than {LIMIT} characters: {v}")
        if isinstance(v, float) and not math.isfinite(v):
            raise AssertionError(f"{key}: not finite")
    detail = {"inputs": [list(DATA), list(CODE), list(README), list(EPRINT)], "repo": REPO, "conditions": cond,
              "controls": ctl, "control_detail": ctl_detail, "main": main, "variants": variants,
              "outcomes": outcomes, "estimators": estimators, "exposure": exposure, "ratio": ratio,
              "ratio_ci_as_printed": ratio_ci_ok, "forecast": forecast, "forecast_ci_as_printed": forecast_ci_ok,
              "correlations": corr, "review": review, "overall_median_review": overall_median, "counts": counts,
              "two_stage": ts, "permutation": {"p_one_sided": p_one, "p_two_sided": p_two},
              "readme": {"printed": readme, "ours": ours_printed, "match": readme_match}, "printed": pr.rows,
              "blank_issue_ids": [r["issue"] for r in blanks]}
    os.makedirs(results, exist_ok=True)
    with open(os.path.join(results, "outputs.json"), "w", encoding="ascii") as fh:
        json.dump(out, fh, indent=2, sort_keys=True)
        fh.write("\n")
    with open(os.path.join(results, "detail.json"), "w", encoding="ascii") as fh:
        json.dump(detail, fh, indent=1, sort_keys=True, default=str)
        fh.write("\n")
    return out, detail


def main():
    seed = os.environ.get("ECDYSIS_SEED", "")
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        sys.exit("ECDYSIS_SEED must be the 64-hex seed the archive issued")
    try:
        out, _ = run(seed)
    except Refused as e:
        sys.exit(f"becker2025: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
