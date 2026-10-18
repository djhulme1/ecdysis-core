#!/usr/bin/env python3
"""Nguyen and Fithian's shared monotone spline against the shared-slope logistic, under cross-validation on task
families, on METR's Time Horizon 1.1 task results.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test is from Drew T. Nguyen and William Fithian, "On
the estimation and validity of AI time horizons---a statistical look at the METR plot", arXiv:2610.12466v1 (8 October
2026), its abstract: "Overall, we contribute time-horizon point estimates that perform better under a cross-validated
suite of proper scoring rules, as well as diagnostic plots for assessing time horizons' construct validity." The paper
reanalyses the data behind METR's time horizons (the lab's metr/horizon.py, ext:b88dde9d74fe32f8): on 228 tasks in 79
task families and 26 AIs, its Models 1 and 2 "dominate the baseline at every displayed metric and weighting" of a
suite of 12 (its Figure 2), under 5-fold cross-validation on task families. Model 1 is tested here; Model 2, an
explanatory IRT model fitted by EM with family effects and overdispersion, is not.

The models, as the paper's Section 2.3 states them, for AI j and task i with human time T_i (x_i = log2 T_i, minutes):
  baseline (shared-slope logistic): logit p_j(T) = alpha_j - beta x, beta > 0;
  Model 1 (shared monotone spline, shared slope): logit p_j(T) = alpha_j - beta f(x), beta > 0, f a monotone natural
  cubic I-spline with nonnegative coefficients and 4 interior knots, with f(min x) = min x and f(max x) = max x;
  METR's original (beside the test only): logit p_j(T) = alpha_j - beta_j x, beta_j > 0.
Each is fitted by binary cross entropy with the sqrt-family weights of its Section 2.4.1, w_ij = 1/(sqrt(n_F(i)) n_ij)
for every run of AI j on task i (n_ij runs; n_F the scored tasks of the task's family). The paper does not say where
the knots go, which spline basis it uses, or how its families were dealt into folds: rules 3 and 5 name the readings.

The inputs, each checked against its size and SHA-256 and read as data (YAML by yaml.safe_load, JSON lines by json;
nothing in them is run): the paper's e-print (its TeX read for the strings in PRINTED_TEX); METR's task results for
Time Horizon 1.1 (https://metr.org/assets/task_results_1_1.yaml, the "raw data" of its time-horizons page: per AI, each
task's human minutes, successes, runs and weight, and METR's own fit); and Time Horizon 1.0's runs (METR/eval-
analysis-public at 52cb829), for the three earliest AIs, which the 1.1 results do not hold. Every rule below was fixed
before any quantity it tests was computed; the seed draws the fold assignments. Before the rules, the files' structure
was read (their fields; the 23 AIs, 228 tasks and 79 families of the task results; that each task's family is its
id's prefix, its human minutes agree across AIs and its weight is one over the square root of its family's size;
that the three earliest AIs ran 142 to 152 of the 228 tasks in 1.0, none of the runs cloned; and that the paper's
figure of success curves names exactly these 23 and these three), and the code was run only on data made up for the
tests.

1. The source: with TeX comments removed and whitespace deleted, the TeX must hold every string in PRINTED_TEX (the
   three models, the weights, the scores, the folds, the dataset's counts and the sentence on unanimous runs);
   otherwise the run is refused.
2. The data, two readings of the paper's 26 AIs. Reading A (the test's): the task results' 23 AIs, each cell (AI,
   task) with its runs n and successes k. Reading B (beside): A with the three earliest AIs (GPT-2, davinci-002 and
   gpt-3.5-turbo-instruct) added from Time Horizon 1.0's runs on the 228 tasks' ids, each run's score_binarized its
   outcome (a cloned run, or a run id twice, refuses the run) and the task's human minutes the 1.1 results'. A task's
   family is its id's prefix; n_F counts the family's tasks among the 228.
3. The fits: the weighted cross entropy, sum over cells of w (k log(1 + e^-eta) + (n - k) log(1 + e^eta)), minimised
   by L-BFGS-B with exact gradients (alpha_j in [-60, 60]; beta = e^b with b in [-14, 5]). Model 1's f is
   x_lo + (x_hi - x_lo) sum_m pi_m I_m(x), pi on the simplex (pi = softmax(gamma), gamma in [-30, 30]), I_m the sum
   over l >= m of the cubic B-splines B_0 .. B_7 on the knots (x_lo four times, the interior knots, x_hi four times),
   m = 1 to 7: the cubic I-splines, monotone from 0 at x_lo to 1 at x_hi, so f(x_lo) = x_lo and f(x_hi) = x_hi; beyond
   [x_lo, x_hi] f is continued linearly with its end slopes (the reading of "natural" here; the second derivative at
   the ends is not constrained). x_lo and x_hi are the least and largest x of the training tasks, and the interior
   knots their 0.2, 0.4, 0.6 and 0.8 quantiles over tasks (numpy's default; reading Q; reading E, beside: equally
   spaced). Model 1 starts from the baseline's fit twice, with f the identity (pi from nonnegative least squares on a
   401-point grid) and with pi uniform, and keeps the lower loss. METR's original fits each AI alone (beta_j > 0).
4. The scores, per run, as the paper's Section 2.4 defines them, each held-out cell contributing w times the sum over
   its runs: the marginal log score (-y log p - (1 - y) log(1 - p)), the Brier score ((y - p)^2) and the smoothed
   elementary scores at q = 0.5 and 0.8 (the elementary score q (1 - y) 1{p > q} + (1 - q) y 1{p < q} averaged over
   [q - 0.05, q + 0.05], in closed form); with the equal-task (w = 1/n), equal-family (1/(n_F n)) and sqrt-family
   (1/(sqrt(n_F) n)) weights: 12 metrics, each the weighted sum over all held-out cells divided by its total weight
   (sum of w n), the paper's "weighted per-run score". Probabilities are clipped to [1e-12, 1 - 1e-12] in the log score.
5. The cross-validation: the 79 families, sorted by name, are permuted by a generator seeded from ECDYSIS_SEED and
   split into 5 folds of 16, 16, 16, 16 and 15 (numpy's array_split); each fold's cells are predicted by models
   fitted to the other four's. FOLD_ASSIGNMENTS = 20 assignments are drawn, and each metric's difference, Model 1's
   score minus the baseline's, is averaged over them.
6. The test: on reading A with knots Q, each of the 12 mean differences is negative (Model 1 better), the 12
   conditions; test_passed is 1 if all hold.
7. Beside the test, none of it counted: how many of the 20 assignments have all 12 differences negative, and per
   metric how many are negative; leave-one-family-out cross-validation (79 folds) on reading A; readings B and E (each
   over the same 20 assignments); METR's original against the baseline (the paper: the baseline beats it on 11 of 12,
   all but equal-task q = 0.5); 95% intervals for the 12 differences of the first assignment, with families as
   clusters (the linearised variance of the ratio of the families' sums); Model 1's f fitted to all of reading A, its
   rise from 2 to 30 minutes as a share of the identity's rise there (the abstract: "nearly flat in a region from
   2--30 min") and its average slopes below 2 and above 30 minutes; and the share of cells with two or more runs whose
   runs agree (the paper: 83%) against the share the baseline fitted to all of reading A implies, the mean of
   p^n + (1 - p)^n (the paper: about 60%), both also over all cells.

Controls (controls_passed of controls_total):
 (a) METR's own per-AI fit reproduced from the cells: for each of the 23 AIs, the logistic regression of its runs on x
     with METR's weights (1/(n sqrt(the AI's tasks in the family)), scaled to sum to one) and an L2 penalty of 1e-5/2
     on the slope, by metr/horizon.py's Newton iteration, gives the file's coefficient and intercept (printed to three
     decimals) within 5e-3;
 (b) Model 1 contains the baseline: its fitted loss is at most the baseline's (plus 1e-9) on all of reading A and in
     every fold of the first assignment;
 (c) the score code, on the first assignment's held-out baseline predictions under equal-task weights: twice the
     integral over q of the elementary score by a 40,000-point midpoint rule is the Brier score within 1e-4 (the
     paper's S_BR = 2 int S_q dq), and a 20,000-point midpoint average over [0.45, 0.55] is the closed-form smoothed
     score within 3e-5 (the midpoint rules' worst-case errors are 5e-5 and 2.75e-5);
 (d) the fits recover known success curves, on 12 made-up AIs with 8 runs on each of 300 made-up tasks in up to 90
     families, drawn from a generator seeded apart from the folds: from the baseline (beta 0.8), its fitted slope is
     within 5% of 0.8; from Model 1 (beta 0.8, f the I-spline on the made-up tasks' own knots with pi = PI_TRUE, nearly
     flat in the middle), Model 1's loss is below the baseline's and its fitted probabilities are within 0.03 of the
     true ones in root mean square over the cells, the baseline's not;
 (e) the data: every task's weight in the file is 1/sqrt(the AI's own tasks in the family) within 1e-3 (it is printed
     to three decimals), the count METR's code takes and control (a) uses, and its human minutes agree across AIs
     (rule 2 refuses otherwise);
 (f) a negative control the comparison could fail on: with the human times permuted across tasks (the first
     assignment's folds), the baseline's cross-validated equal-task log score is worse than with the true times by at
     least 0.02.

After the first trial (under a seed of Imago's own, before any was issued; its outcome was seen: Model 1 better on 9
of the 12 metrics, worse on the equal-family log and Brier scores and the sqrt-family log score), two changes, neither
to the test. (1) Control (e) as committed compared each weight with one over the square root of the family's size
among the 228 tasks, and failed: Claude 3.5 Sonnet (New) ran 226 of the 228 tasks, and its four cells in the families
it ran in part are weighted by its own count of their tasks, as METR's code computes weights within each AI (control
(a), which reproduced METR's fits, already used that count; the sentence above on what was read before the rules said
"its family's size" from a reading of some AIs only). The control now takes the AI's own count, and the cells that
differ from the global count are reported beside it. The test's weights stay the paper's, whose n_F does not depend on
the AI. (2) Beside the test, reading N, chosen after the outcome was seen and not counted: rule 3 reads "natural" as
the linear continuation beyond [x_lo, x_hi] only, and its fit to all of reading A has a zero slope at x_lo (pi_1 = 0);
a natural cubic spline in the standard sense also has f'' = 0 at x_lo and x_hi, which on this basis ties pi_2 to pi_1
and pi_6 to pi_7 (the five generators of the cone of nonnegative combinations with f'' = 0 at both ends, each scaled to
end at 1). Reading N runs Model 1 on that basis over the same 20 assignments, on readings A and B.

What it cannot check: Model 2, the paper's figures beyond the values named, and whether METR's tasks and human times
measure what they are meant to (the paper questions exactly that; its diagnostics are not repeated here).

Writes results/outputs.json (the values a receipt carries) and results/detail.json (every value computed).
Run with: python3 metr/nf2026.py (the pinned scipy-notebook image, for numpy, scipy and PyYAML).
"""

import gzip
import hashlib
import io
import json
import math
import os
import re
import sys
import tarfile
import time
from collections import Counter, defaultdict

import numpy as np
import yaml
from scipy.interpolate import BSpline
from scipy.optimize import minimize, nnls

INPUTS = {
    "eprint": ("arXiv-2610.12466v1.tar.gz", "83e596b347cf28e5f1cc209b94bb40adc548ff2d4a8fe014d80bb74d9e96c067", 338265),
    "results": ("task_results_1_1.yaml", "4f85fbf03cbf8b43af102ff17db6bbb4963b3c98784e90f81fb71a146cf26b07", 686419),
    "th10": ("runs.jsonl", "f489d11728909937dad99ba1ed2d7c40efe12a766891e67dbc7c2486a3311236", 24022538),
}
EARLIEST = ("GPT-2", "davinci-002 (GPT-3)", "gpt-3.5-turbo-instruct")
FOLDS = 5
FOLD_ASSIGNMENTS = 20
QUANTILES = (0.2, 0.4, 0.6, 0.8)
ALPHA_BOUND = 60.0
LOGBETA_BOUNDS = (-14.0, 5.0)
GAMMA_BOUND = 30.0
METR_L2 = 1e-5
METR_TOL = 5e-3
CLIP = 1e-12
QS = (0.5, 0.8)
WIDTH = 0.05
WEIGHTINGS = ("equal-task", "equal-family", "sqrt-family")
SCORES = ("log", "brier", "q0.5", "q0.8")
METRICS = tuple(f"{s} {w}" for s in SCORES for w in WEIGHTINGS)
LIMIT = 200
OPTIONS = {"maxiter": 20000, "ftol": 1e-15, "gtol": 1e-10}
PI_TRUE = (0.22, 0.22, 0.03, 0.03, 0.03, 0.22, 0.25)

TEST = ("Refuted if, on METR's public Time Horizon 1.1 task results (its 23 AIs' runs on the 228 tasks), the paper's "
        "Model 1 (logit p = α_j − β f(log₂ T), f a shared monotone cubic I-spline with 4 interior knots at the tasks' "
        "quintiles, sqrt-family-weighted cross entropy) scores no better than its shared-slope logistic baseline, "
        "averaged over 20 seed-drawn 5-fold splits of the 79 task families, on any of the 12 metrics: the marginal "
        "log, Brier and smoothed elementary (q = 0.5, 0.8) scores, each under equal-task, equal-family and "
        "sqrt-family weights.")

PRINTED_TEX = [
    r"\log\left( \frac{p_j(t)}{1-p_j(t)} \right) = \alpha_j - \beta \log_2(t)",
    r"\log\left( \frac{p_j(t)}{1-p_j(t)} \right) = \alpha_j - \beta\, f(\log_2 t), \qquad \beta > 0.",
    r"a monotone natural cubic I-spline with nonnegative coefficients with 4 interior knots",
    r"$f(\min \log_2 T_i) = \min \log_2 T_i$ and $f(\max \log_2 T_i) = \max \log_2 T_i$",
    r"\log\left( \frac{p_j(t)}{1-p_j(t)} \right) = \alpha_j - \beta_j \log_2(t)",
    r"w_{ij} = 1/n_{ij} \ \ (\text{equal-task}), \qquad 1/(n_{F(i)}\, n_{ij}) \ \ (\text{equal-family}), \qquad "
    r"1/(\sqrt{n_{F(i)}}\, n_{ij}) \ \ (\text{sqrt-family}).",
    r"q (1 - Y_{ijr}) 1\{\hat p_{ij} > q\} + (1 - q) Y_{ijr} 1\{\hat p_{ij} < q\}",
    r"\tilde S_q((\mathbf{T}, \mathbf{Y}), \mathcal{M}) := \frac{1}{0.1}\int_{-0.05}^{0.05} S_{q + \varepsilon}"
    r"((\mathbf{T}, \mathbf{Y}), \mathcal{M})\,  d\varepsilon",
    r"we split the 79 task families into 5 approximately equally sized folds",
    r"evaluate marginal log score, Brier score, and the smoothed elementary binary score at $q = 0.5$ and $q = 0.8$",
    r"Crossing these four scores with the three weighting schemes gives 12 proper scoring rule metrics.",
    r"Point estimates for both of our models dominate the baseline at every displayed metric and weighting.",
    r"we would predict that $\sim 60\%$ of vectors $Y_{ij} = (Y_{ij1}, \dots, Y_{ijn_{ij}})$ were unanimous. "
    r"However, it is actually 83\% of them.",
    r"On 228 tasks and 26 AIs",
    r"the sqrt-family weighting described in Section \ref{sec:weights} on the cross-entropy loss",
    r"Our chosen baseline itself dominates the original logistic regression specification on all metrics except "
    r"one, namely equal-task $\tilde S_{q = 0.5}$",
]


class Refused(Exception):
    pass


# ---------------------------------------------------------------- inputs (rules 1 and 2)

def read_bytes(path, sha, size):
    with open(path, "rb") as fh:
        data = fh.read()
    if len(data) != size or hashlib.sha256(data).hexdigest() != sha:
        raise Refused(f"{os.path.basename(path)} does not match its pinned size and SHA-256")
    return data


def flatten_tex(tex):
    lines = [re.sub(r"(?<!\\)%.*$", "", line) for line in tex.split("\n")]
    return re.sub(r"\s+", "", "\n".join(lines))


def check_tex(blob):
    tf = tarfile.open(fileobj=io.BytesIO(gzip.decompress(blob)))
    names = {m.name: m for m in tf.getmembers() if m.isfile()}
    if "main.tex" not in names:
        raise Refused("the e-print lacks main.tex")
    flat = flatten_tex(tf.extractfile(names["main.tex"]).read().decode("utf-8"))
    missing = [s for s in PRINTED_TEX if re.sub(r"\s+", "", s) not in flat]
    if missing:
        raise Refused(f"the TeX does not print: {missing[:2]}")


def family(task_id):
    return task_id.split("/")[0]


def read_results(blob):
    d = yaml.safe_load(blob.decode("utf-8"))
    if not isinstance(d, dict) or not isinstance(d.get("agents"), dict):
        raise Refused("the task results hold no agents")
    agents = {}
    for name, a in d["agents"].items():
        cells, seen = [], set()
        for t in a["tasks"]:
            n, k, hm = int(t["n_runs"]), int(t["n_successes"]), float(t["human_minutes"])
            if n < 1 or not 0 <= k <= n or not hm > 0 or not math.isfinite(hm) or t["task_id"] in seen:
                raise Refused(f"a cell of {name} is not valid: {t}")
            seen.add(t["task_id"])
            cells.append({"task": str(t["task_id"]), "n": n, "k": k, "minutes": hm, "weight": float(t["task_weight"])})
        agents[str(name)] = {"cells": cells, "coefficient": float(a["coefficient"]), "intercept": float(a["intercept"]),
                             "release_date": str(a["release_date"])}
    return agents


def read_th10(blob, minutes):
    """The three earliest AIs' runs on the 1.1 tasks' ids, as cells with the 1.1 human minutes."""
    counts = defaultdict(lambda: [0, 0])
    seen = set()
    for line in blob.decode("utf-8").split("\n"):
        if not line.strip():
            continue
        r = json.loads(line)
        if not isinstance(r, dict) or r.get("alias") not in EARLIEST or r.get("task_id") not in minutes:
            continue
        if r.get("run_id") is None or r["run_id"] in seen:
            raise Refused("a run of the earliest AIs has no id or appears twice")
        seen.add(r["run_id"])
        if r.get("cloned") not in (None, 0, 0.0, False):
            raise Refused("a run of the earliest AIs is cloned")
        y = r.get("score_binarized")
        if isinstance(y, bool) or y not in (0, 1):
            raise Refused("a run's binarized score is not 0 or 1")
        c = counts[(r["alias"], r["task_id"])]
        c[0] += 1
        c[1] += int(y)
    out = {a: [] for a in EARLIEST}
    for (a, t), (n, k) in sorted(counts.items()):
        out[a].append({"task": t, "n": n, "k": k, "minutes": minutes[t], "weight": None})
    return out


class Data:
    """Cells as arrays: AI index, task index, runs, successes; tasks' x = log2 minutes and family index."""

    def __init__(self, agents):
        self.ais = list(agents)
        tasks = sorted({c["task"] for a in agents.values() for c in a})
        self.tasks = tasks
        tix = {t: i for i, t in enumerate(tasks)}
        fams = sorted({family(t) for t in tasks})
        self.families = fams
        fix = {f: i for i, f in enumerate(fams)}
        self.task_family = np.array([fix[family(t)] for t in tasks])
        size = Counter(self.task_family.tolist())
        self.nF_task = np.array([size[f] for f in self.task_family], dtype=float)
        minutes = {}
        rows = []
        for j, a in enumerate(self.ais):
            for c in agents[a]:
                minutes.setdefault(c["task"], c["minutes"])
                if abs(minutes[c["task"]] - c["minutes"]) > 1e-9:
                    raise Refused(f"task {c['task']} has two human times")
                rows.append((j, tix[c["task"]], c["n"], c["k"]))
        self.x_task = np.array([math.log2(minutes[t]) for t in tasks])
        arr = np.array(rows, dtype=np.int64)
        self.j, self.i, self.n, self.k = arr[:, 0], arr[:, 1], arr[:, 2].astype(float), arr[:, 3].astype(float)
        self.fam = self.task_family[self.i]
        self.nF = self.nF_task[self.i]
        self.x = self.x_task[self.i]

    def subset(self, mask):
        s = object.__new__(Data)
        s.ais, s.tasks, s.families = self.ais, self.tasks, self.families
        s.task_family, s.nF_task, s.x_task = self.task_family, self.nF_task, self.x_task
        for name in ("j", "i", "n", "k", "fam", "nF", "x"):
            setattr(s, name, getattr(self, name)[mask])
        return s

    def with_x(self, x_task):
        s = self.subset(np.ones(len(self.j), dtype=bool))
        s.x_task = np.asarray(x_task, dtype=float)
        s.x = s.x_task[s.i]
        return s


# ---------------------------------------------------------------- the spline (rule 3)

class ISpline:
    def __init__(self, x_train_tasks, knots="Q"):
        xs = np.asarray(x_train_tasks, dtype=float)
        self.lo, self.hi = float(xs.min()), float(xs.max())
        if not self.hi > self.lo:
            raise Refused("the training tasks span no range of human times")
        if knots == "Q":
            inner = [float(np.quantile(xs, q)) for q in QUANTILES]
        else:
            inner = [self.lo + (self.hi - self.lo) * q for q in QUANTILES]
        self.inner = inner
        self.t = np.array([self.lo] * 4 + inner + [self.hi] * 4)
        nb = len(self.t) - 4
        self.splines = []
        for m in range(1, nb):
            c = np.array([0.0] * m + [1.0] * (nb - m))
            s = BSpline(self.t, c, 3, extrapolate=False)
            ds = s.derivative()
            self.splines.append((s, float(ds(self.lo)), float(ds(self.hi))))
        self.K = len(self.splines)

    def basis(self, x):
        x = np.asarray(x, dtype=float)
        B = np.empty((len(x), len(self.splines)))
        inside = (x >= self.lo) & (x <= self.hi)
        below, above = x < self.lo, x > self.hi
        for m, (s, d_lo, d_hi) in enumerate(self.splines):
            col = np.zeros(len(x))
            if inside.any():
                col[inside] = s(x[inside])
            col[below] = d_lo * (x[below] - self.lo)
            col[above] = 1.0 + d_hi * (x[above] - self.hi)
            B[:, m] = col
        return B

    def identity_pi(self):
        grid = np.linspace(self.lo, self.hi, 401)
        pi, _ = nnls(self.basis(grid), (grid - self.lo) / (self.hi - self.lo))
        pi = np.maximum(pi, 1e-9)
        return pi / pi.sum()


class NaturalISpline(ISpline):
    """Reading N (beside the test, chosen after the first trial): nonnegative combinations of the cubic I-splines with
    f'' = 0 at x_lo and x_hi. At x_lo only I_1'' (negative) and I_2'' (positive) are nonzero, and at x_hi only I_6''
    (negative) and I_7'' (positive), so the cone is spanned by five generators: I_1 and I_2 in the ratio that cancels
    f''(x_lo), I_3, I_4, I_5, and I_6 and I_7 in the ratio that cancels f''(x_hi), each scaled to end at 1."""

    def __init__(self, x_train_tasks, knots="Q"):
        super().__init__(x_train_tasks, knots)
        a = np.array([float(s.derivative(2)(self.lo)) for s, _, _ in self.splines])
        b = np.array([float(s.derivative(2)(self.hi)) for s, _, _ in self.splines])
        tiny = 1e-9 * max(1.0, float(np.max(np.abs(a))), float(np.max(np.abs(b))))
        if [i for i in range(7) if abs(a[i]) > tiny] != [0, 1] or [i for i in range(7) if abs(b[i]) > tiny] != [5, 6] \
                or not (a[0] < 0 < a[1] and b[5] < 0 < b[6]):
            raise Refused("the I-splines' second derivatives at the ends are not as expected")
        G = np.zeros((7, 5))
        G[0, 0], G[1, 0] = a[1], -a[0]
        G[2, 1] = G[3, 2] = G[4, 3] = 1.0
        G[5, 4], G[6, 4] = b[6], -b[5]
        self.G = G / G.sum(axis=0)
        self.K = 5

    def basis(self, x):
        return ISpline.basis(self, x) @ self.G


def softmax(g):
    e = np.exp(g - g.max())
    return e / e.sum()


# ---------------------------------------------------------------- fits (rule 3)

def bce_terms(eta, n, k):
    """k log(1 + e^-eta) + (n - k) log(1 + e^eta), and its derivative in eta, n sigmoid(eta) - k."""
    lp = np.logaddexp(0.0, -eta)
    lq = np.logaddexp(0.0, eta)
    return k * lp + (n - k) * lq, n * np.exp(-lp) - k


def train_weights(d):
    return 1.0 / (np.sqrt(d.nF) * d.n)


def baseline_objective(d, J):
    """The baseline's weighted cross entropy and its gradient in (alpha_1 .. alpha_J, log beta)."""
    w = train_weights(d)

    def fun(theta):
        a, beta = theta[:J], math.exp(theta[J])
        val, g = bce_terms(a[d.j] - beta * d.x, d.n, d.k)
        g = w * g
        grad = np.zeros_like(theta)
        np.add.at(grad, d.j, g)
        grad[J] = -beta * float(np.sum(g * d.x))
        return float(np.sum(w * val)), grad
    return fun


def model1_objective(d, J, spl):
    """Model 1's weighted cross entropy and its gradient in (alpha_1 .. alpha_J, log beta, gamma_1 .. gamma_K)."""
    w = train_weights(d)
    B = spl.basis(d.x)
    span = spl.hi - spl.lo

    def fun(theta):
        a, beta, pi = theta[:J], math.exp(theta[J]), softmax(theta[J + 1:])
        f = spl.lo + span * (B @ pi)
        val, g = bce_terms(a[d.j] - beta * f, d.n, d.k)
        g = w * g
        grad = np.zeros_like(theta)
        np.add.at(grad, d.j, g)
        grad[J] = -beta * float(np.sum(g * f))
        h = span * (B.T @ (-beta * g))                      # the gradient in pi
        grad[J + 1:] = pi * (h - float(np.dot(pi, h)))      # through the softmax
        return float(np.sum(w * val)), grad
    return fun


def fit_baseline(d, J):
    fun = baseline_objective(d, J)
    theta0 = np.zeros(J + 1)
    theta0[J] = math.log(0.5)
    r = minimize(fun, theta0, jac=True, method="L-BFGS-B", bounds=[(-ALPHA_BOUND, ALPHA_BOUND)] * J + [LOGBETA_BOUNDS],
                 options=OPTIONS)
    return {"alpha": r.x[:J], "beta": math.exp(r.x[J]), "loss": float(r.fun), "ok": bool(r.success)}


def fit_model1(d, J, spl, base):
    fun = model1_objective(d, J, spl)
    bounds = [(-ALPHA_BOUND, ALPHA_BOUND)] * J + [LOGBETA_BOUNDS] + [(-GAMMA_BOUND, GAMMA_BOUND)] * spl.K
    best = None
    for pi0 in (spl.identity_pi(), np.full(spl.K, 1.0 / spl.K)):
        theta0 = np.concatenate([base["alpha"], [math.log(base["beta"])], np.log(pi0)])
        r = minimize(fun, theta0, jac=True, method="L-BFGS-B", bounds=bounds, options=OPTIONS)
        if best is None or r.fun < best.fun:
            best = r
    th = best.x
    return {"alpha": th[:J], "beta": math.exp(th[J]), "pi": softmax(th[J + 1:]), "spline": spl, "loss": float(best.fun),
            "ok": bool(best.success)}


def fit_separate(d, J):
    """METR's original specification, each AI alone (beta_j > 0), with the paper's training weights."""
    w = train_weights(d)
    out = np.zeros((J, 2))
    for j in range(J):
        m = d.j == j
        xj, nj, kj, wj = d.x[m], d.n[m], d.k[m], w[m]

        def fun(th):
            beta = math.exp(th[1])
            val, g = bce_terms(th[0] - beta * xj, nj, kj)
            g = wj * g
            return float(np.sum(wj * val)), np.array([float(np.sum(g)), -beta * float(np.sum(g * xj))])
        r = minimize(fun, np.array([0.0, math.log(0.5)]), jac=True, method="L-BFGS-B",
                     bounds=[(-ALPHA_BOUND, ALPHA_BOUND), LOGBETA_BOUNDS], options=OPTIONS)
        out[j] = (r.x[0], math.exp(r.x[1]))
    return out


def f_of(model, x):
    spl = model["spline"]
    return spl.lo + (spl.hi - spl.lo) * (spl.basis(np.atleast_1d(np.asarray(x, dtype=float))) @ model["pi"])


def predict(model, kind, d):
    if kind == "baseline":
        eta = model["alpha"][d.j] - model["beta"] * d.x
    elif kind == "model1":
        eta = model["alpha"][d.j] - model["beta"] * f_of(model, d.x)
    else:
        eta = model[d.j, 0] - model[d.j, 1] * d.x
    return 0.5 * (1.0 + np.tanh(0.5 * eta))


# ---------------------------------------------------------------- scores (rule 4)

def smoothed_elementary(p, q):
    """Per-run smoothed elementary scores at level q, for y = 1 and for y = 0 (closed form)."""
    lo, hi = q - WIDTH, q + WIDTH
    a = np.clip(p, lo, hi)
    s1 = ((hi - hi * hi / 2) - (a - a * a / 2)) / (2 * WIDTH)     # mean over [lo, hi] of (1 - u) 1{p < u}
    s0 = (a * a / 2 - lo * lo / 2) / (2 * WIDTH)                  # mean over [lo, hi] of u 1{p > u}
    return s1, s0


def cell_scores(p, n, k):
    pc = np.clip(p, CLIP, 1 - CLIP)
    out = {"log": -(k * np.log(pc) + (n - k) * np.log(1 - pc)), "brier": k * (1 - p) ** 2 + (n - k) * p ** 2}
    for q in QS:
        s1, s0 = smoothed_elementary(p, q)
        out[f"q{q}"] = k * s1 + (n - k) * s0
    return out


def eval_weights(d):
    return {"equal-task": 1.0 / d.n, "equal-family": 1.0 / (d.nF * d.n), "sqrt-family": 1.0 / (np.sqrt(d.nF) * d.n)}


def pooled(cs, d):
    """The 12 metrics from per-cell scores: weighted sums over the total weight."""
    ws = eval_weights(d)
    return {f"{s} {w}": float(np.sum(ws[w] * cs[s]) / np.sum(ws[w] * d.n)) for s in SCORES for w in WEIGHTINGS}


# ---------------------------------------------------------------- cross-validation (rule 5)

def fold_assignment(seed, r, nfam):
    h = hashlib.sha256(bytes.fromhex(seed) + f"|folds|{r}".encode("ascii")).digest()
    rng = np.random.Generator(np.random.PCG64(int.from_bytes(h[:16], "big")))
    return [set(int(v) for v in part) for part in np.array_split(rng.permutation(nfam), FOLDS)]


def crossval(d, folds, knots="Q", kinds=("baseline", "model1"), spline=ISpline):
    J = len(d.ais)
    preds = {kind: np.full(len(d.j), np.nan) for kind in kinds}
    losses = []
    for fold in folds:
        test = np.isin(d.fam, sorted(fold))
        tr, te = d.subset(~test), d.subset(test)
        base = fit_baseline(tr, J)
        if "baseline" in kinds:
            preds["baseline"][test] = predict(base, "baseline", te)
        if "model1" in kinds:
            m1 = fit_model1(tr, J, spline(d.x_task[np.unique(tr.i)], knots), base)
            preds["model1"][test] = predict(m1, "model1", te)
            losses.append((base["loss"], m1["loss"]))
        if "separate" in kinds:
            preds["separate"][test] = predict(fit_separate(tr, J), "separate", te)
    for kind in kinds:
        if not np.all(np.isfinite(preds[kind])):
            raise AssertionError(f"a cell was not predicted by {kind}")
    scores = {kind: pooled(cell_scores(preds[kind], d.n, d.k), d) for kind in kinds}
    return scores, preds, losses


def differences(sc, a="model1", b="baseline"):
    return {m: sc[a][m] - sc[b][m] for m in METRICS}


def cluster_ci(p1, p0, d):
    """95% intervals for each metric's difference, with families as clusters."""
    c1, c0 = cell_scores(p1, d.n, d.k), cell_scores(p0, d.n, d.k)
    ws = eval_weights(d)
    out = {}
    G = len(d.families)
    for s in SCORES:
        for wn in WEIGHTINGS:
            num = np.bincount(d.fam, weights=ws[wn] * (c1[s] - c0[s]), minlength=G)
            den = np.bincount(d.fam, weights=ws[wn] * d.n, minlength=G)
            keep = den > 0
            num, den = num[keep], den[keep]
            D = num.sum() / den.sum()
            g = len(num)
            se = math.sqrt(g / (g - 1) * float(np.sum((num - D * den) ** 2))) / den.sum()
            out[f"{s} {wn}"] = (D - 1.96 * se, D + 1.96 * se)
    return out


# ---------------------------------------------------------------- controls

def metr_fit(x, y, w, lam=METR_L2, tol=1e-11, steps=200):
    """metr/horizon.py's fit: (a, b) minimising sum w (log(1 + e^z) - y z) + lam a^2 / 2, z = a x + b."""
    def loss(a, b):
        z = a * x + b
        return float(np.sum(w * (np.logaddexp(0.0, z) - y * z)) + 0.5 * lam * a * a)

    def gradient(a, b):
        p = 0.5 * (1.0 + np.tanh(0.5 * (a * x + b)))
        r = w * (p - y)
        return float(np.sum(r * x) + lam * a), float(np.sum(r)), p
    mean = min(max(float(np.sum(w * y) / np.sum(w)), 1e-9), 1 - 1e-9)
    a, b = 0.0, math.log(mean / (1 - mean))
    current = loss(a, b)
    for _ in range(steps):
        ga, gb, p = gradient(a, b)
        if math.hypot(ga, gb) < tol:
            break
        s = w * p * (1 - p)
        haa, hab, hbb = float(np.sum(s * x * x) + lam), float(np.sum(s * x)), float(np.sum(s))
        det = haa * hbb - hab * hab
        da, db = (hbb * ga - hab * gb) / det, (haa * gb - hab * ga) / det
        if math.hypot(ga, gb) < 1e-6:
            a, b = a - da, b - db
            current = loss(a, b)
            continue
        t = 1.0
        while True:
            na, nb = a - t * da, b - t * db
            new = loss(na, nb)
            if new <= current or t < 1e-12:
                break
            t /= 2
        a, b, current = na, nb, new
    return a, b


def control_metr(agents):
    """The largest difference from the file's own fits, over the AIs, and the worst AI."""
    worst, who = 0.0, None
    for name, a in agents.items():
        fams = Counter(family(c["task"]) for c in a["cells"])
        xs, ys, ws = [], [], []
        for c in a["cells"]:
            base = 1.0 / (c["n"] * math.sqrt(fams[family(c["task"])]))
            for y, cnt in ((1, c["k"]), (0, c["n"] - c["k"])):
                if cnt:
                    xs.append(math.log2(c["minutes"]))
                    ys.append(float(y))
                    ws.append(base * cnt)
        w = np.array(ws)
        coef, icpt = metr_fit(np.array(xs), np.array(ys), w / w.sum())
        diff = max(abs(coef - a["coefficient"]), abs(icpt - a["intercept"]))
        if diff > worst:
            worst, who = diff, name
    return worst, who


def simulate(seed, kind):
    """Made-up cells from the baseline or from Model 1 (kind "spline"): the data, the true slope and the true
    probability of each cell."""
    h = hashlib.sha256(bytes.fromhex(seed) + f"|simulate|{kind}".encode("ascii")).digest()
    rng = np.random.Generator(np.random.PCG64(int.from_bytes(h[:16], "big")))
    I, J, beta = 300, 12, 0.8
    x = rng.uniform(-2, 10, I)
    fams = rng.integers(0, 90, I)
    alpha = np.linspace(-1, 6, J)
    if kind == "spline":
        spl = ISpline(x, "Q")
        fx = spl.lo + (spl.hi - spl.lo) * (spl.basis(x) @ np.array(PI_TRUE))
    else:
        fx = x
    agents, truth = {}, {}
    for j in range(J):
        name = f"ai{j:02d}"
        p = 1 / (1 + np.exp(-(alpha[j] - beta * fx)))
        ks = rng.binomial(8, p)
        agents[name] = [{"task": f"fam{fams[i]:03d}/t{i:03d}", "n": 8, "k": int(ks[i]), "minutes": 2.0 ** x[i],
                         "weight": None} for i in range(I)]
        truth.update({(name, f"fam{fams[i]:03d}/t{i:03d}"): float(p[i]) for i in range(I)})
    d = Data(agents)
    return d, beta, np.array([truth[(d.ais[a], d.tasks[t])] for a, t in zip(d.j, d.i)])


def rms(a, b):
    return math.sqrt(float(np.mean((a - b) ** 2)))


def control_scores(p, d):
    ws = eval_weights(d)["equal-task"]
    total = float(np.sum(ws * d.n))
    acc = np.zeros(len(p))
    N = 40000
    for q in (np.arange(N) + 0.5) / N:
        acc += d.k * (1 - q) * (p < q) + (d.n - d.k) * q * (p > q)
    brier_int = float(np.sum(ws * 2 * acc / N)) / total
    acc = np.zeros(len(p))
    N = 20000
    for q in 0.5 - WIDTH + 2 * WIDTH * (np.arange(N) + 0.5) / N:
        acc += d.k * (1 - q) * (p < q) + (d.n - d.k) * q * (p > q)
    smooth_num = float(np.sum(ws * acc / N)) / total
    return brier_int, smooth_num


# ---------------------------------------------------------------- the run

def mean_of(rows):
    return {m: float(np.mean([r[m] for r in rows])) for m in METRICS}


def run(seed, inputs="inputs", results="results"):
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        raise Refused("the seed must be 64 hex characters")
    raw = {}
    for key, (name, sha, size) in INPUTS.items():
        path = os.path.join(inputs, name)
        if not os.path.exists(path):
            raise Refused(f"missing input {name}")
        raw[key] = read_bytes(path, sha, size)
    check_tex(raw["eprint"])
    t0 = time.time()
    agents = read_results(raw["results"])
    cellsA = {a: v["cells"] for a, v in agents.items()}
    dataA = Data(cellsA)
    minutes = {c["task"]: c["minutes"] for v in cellsA.values() for c in v}
    early = read_th10(raw["th10"], minutes)
    cellsB = dict(cellsA)
    for a in EARLIEST:
        if not early[a]:
            raise Refused(f"no 1.0 runs of {a} on the 1.1 tasks")
        cellsB[a] = early[a]
    dataB = Data(cellsB)
    nfam = len(dataA.families)
    if len(dataB.families) != nfam:
        raise AssertionError("reading B has other families")
    timing = {}

    # the test (rule 6)
    diffs, per_metric_neg, first, fold_losses_ok = [], Counter(), None, True
    for r in range(FOLD_ASSIGNMENTS):
        folds = fold_assignment(seed, r, nfam)
        sc, preds, losses = crossval(dataA, folds)
        dd = differences(sc)
        diffs.append(dd)
        for m, v in dd.items():
            per_metric_neg[m] += int(v < 0)
        if r == 0:
            first = (folds, sc, preds)
            fold_losses_ok = all(m1 <= b0 + 1e-9 for b0, m1 in losses)
    all_better = sum(1 for dd in diffs if all(v < 0 for v in dd.values()))
    mean_diff = mean_of(diffs)
    cond = {f"Model 1 better on {m} (mean over {FOLD_ASSIGNMENTS} assignments)": mean_diff[m] < 0 for m in METRICS}
    timing["test"] = round(time.time() - t0, 1)

    # beside the test (rule 7)
    t1 = time.time()
    sc_lofo, _, _ = crossval(dataA, [{f} for f in range(nfam)])
    lofo_d = differences(sc_lofo)
    meanB = mean_of([differences(crossval(dataB, fold_assignment(seed, r, nfam))[0])
                     for r in range(FOLD_ASSIGNMENTS)])
    meanE = mean_of([differences(crossval(dataA, fold_assignment(seed, r, nfam), knots="E")[0])
                     for r in range(FOLD_ASSIGNMENTS)])
    meanS = mean_of([differences(crossval(dataA, fold_assignment(seed, r, nfam), kinds=("baseline", "separate"))[0],
                                 "baseline", "separate") for r in range(FOLD_ASSIGNMENTS)])
    natural = {}
    for label, data in (("A", dataA), ("B", dataB)):
        rows = [differences(crossval(data, fold_assignment(seed, r, nfam), spline=NaturalISpline)[0])
                for r in range(FOLD_ASSIGNMENTS)]
        natural[label] = {"mean_differences": mean_of(rows),
                          "per_metric_negative": {m: sum(1 for row in rows if row[m] < 0) for m in METRICS}}
    folds0, sc0, preds0 = first
    ci = cluster_ci(preds0["model1"], preds0["baseline"], dataA)
    J = len(dataA.ais)
    base_all = fit_baseline(dataA, J)
    m1_all = fit_model1(dataA, J, ISpline(dataA.x_task, "Q"), base_all)
    in_sample_ok = m1_all["loss"] <= base_all["loss"] + 1e-9
    spl = m1_all["spline"]
    x2, x30 = math.log2(2.0), math.log2(30.0)
    f2, f30, flo, fhi = (float(f_of(m1_all, v)[0]) for v in (x2, x30, spl.lo, spl.hi))
    rise = (f30 - f2) / (x30 - x2)
    slope_low = (f2 - flo) / (x2 - spl.lo)
    slope_high = (fhi - f30) / (spl.hi - x30)
    multi = dataA.n >= 2
    agree = (dataA.k == 0) | (dataA.k == dataA.n)
    p_all = predict(base_all, "baseline", dataA)
    implied = p_all ** dataA.n + (1 - p_all) ** dataA.n
    unanimous, expected = float(np.mean(agree[multi])), float(np.mean(implied[multi]))
    timing["beside"] = round(time.time() - t1, 1)

    # controls
    t2 = time.time()
    ctl = {}
    metr_worst, metr_who = control_metr(agents)
    ctl["(a) METR's per-AI coefficient and intercept reproduced within 5e-3"] = metr_worst < METR_TOL
    ctl["(b) Model 1's loss at most the baseline's, on all of reading A and in every fold of the first assignment"] = \
        bool(in_sample_ok and fold_losses_ok)
    brier_int, smooth_num = control_scores(preds0["baseline"], dataA)
    brier, smooth = sc0["baseline"]["brier equal-task"], sc0["baseline"]["q0.5 equal-task"]
    ctl["(c) Brier = 2 int S_q dq within 1e-4, and the smoothed score's closed form within 3e-5"] = bool(
        abs(brier_int - brier) < 1e-4 and abs(smooth_num - smooth) < 3e-5)
    simb, beta_b, _ = simulate(seed, "baseline")
    fb = fit_baseline(simb, len(simb.ais))
    sim1, _, p_true = simulate(seed, "spline")
    b1 = fit_baseline(sim1, len(sim1.ais))
    f1 = fit_model1(sim1, len(sim1.ais), ISpline(sim1.x_task, "Q"), b1)
    rms1, rmsb = rms(predict(f1, "model1", sim1), p_true), rms(predict(b1, "baseline", sim1), p_true)
    ctl["(d) the fits recover known curves (the baseline's slope within 5%; Model 1's probabilities within 0.03)"] = \
        bool(abs(fb["beta"] - beta_b) / beta_b < 0.05 and f1["loss"] < b1["loss"] and rms1 < 0.03 <= rmsb)
    wt_ok, off_global = True, Counter()
    for name, v in cellsA.items():
        own = Counter(family(c["task"]) for c in v)
        for c in v:
            wt_ok &= abs(c["weight"] - 1 / math.sqrt(own[family(c["task"])])) < 1e-3
            if abs(c["weight"] - 1 / math.sqrt(dataA.nF_task[dataA.tasks.index(c["task"])])) >= 1e-3:
                off_global[name] += 1
    ctl["(e) every task's weight is 1/sqrt(the AI's tasks in the family) within 1e-3; human minutes agree across AIs"] = \
        bool(wt_ok)
    h = hashlib.sha256(bytes.fromhex(seed) + b"|permute").digest()
    rng = np.random.Generator(np.random.PCG64(int.from_bytes(h[:16], "big")))
    scp, _, _ = crossval(dataA.with_x(dataA.x_task[rng.permutation(len(dataA.x_task))]), folds0, kinds=("baseline",))
    permuted = scp["baseline"]["log equal-task"]
    ctl["(f) with human times permuted, the baseline's equal-task log score worsens by at least 0.02"] = bool(
        permuted - sc0["baseline"]["log equal-task"] >= 0.02)
    timing["controls"] = round(time.time() - t2, 1)

    def g4(v):
        return float(f"{v:.4g}")
    short = {m: m.replace(" ", "_").replace("-", "_").replace(".", "") for m in METRICS}
    out = {"ais": len(dataA.ais), "tasks": len(dataA.tasks), "families": nfam, "cells": int(len(dataA.j)),
           "runs": int(dataA.n.sum())}
    for m in METRICS:
        out[f"d_{short[m]}"] = g4(mean_diff[m])
    out.update({
        "assignments_all_better": all_better,
        "lofo_better": sum(1 for v in lofo_d.values() if v < 0),
        "reading_b_better": sum(1 for v in meanB.values() if v < 0),
        "knots_equal_better": sum(1 for v in meanE.values() if v < 0),
        "baseline_over_metr_better": sum(1 for v in meanS.values() if v < 0),
        "natural_a_better": sum(1 for v in natural["A"]["mean_differences"].values() if v < 0),
        "natural_b_better": sum(1 for v in natural["B"]["mean_differences"].values() if v < 0),
        "weights_off_global_count": sum(off_global.values()),
        "f_rise_2_30": g4(rise), "f_slope_below_2": g4(slope_low), "f_slope_above_30": g4(slope_high),
        "unanimous_share": g4(unanimous), "unanimous_expected": g4(expected),
        "conditions_met": sum(cond.values()), "conditions_total": len(cond),
        "test_passed": int(all(cond.values())),
        "controls_passed": sum(ctl.values()), "controls_total": len(ctl),
    })
    for k, v in out.items():
        if isinstance(v, float) and not math.isfinite(v):
            raise AssertionError(f"{k}: not finite")
        if isinstance(v, str) and len(v) > LIMIT:
            raise AssertionError(f"{k}: longer than {LIMIT} characters")
    detail = {
        "test": TEST, "conditions": cond, "controls": ctl, "timing": timing,
        "mean_differences": mean_diff, "per_assignment": diffs, "per_metric_negative": dict(per_metric_neg),
        "lofo": lofo_d,
        "reading_b": {"ais": len(dataB.ais), "cells": int(len(dataB.j)), "runs": int(dataB.n.sum()),
                      "earliest_cells": {a: len(early[a]) for a in EARLIEST}, "mean_differences": meanB},
        "knots_equal": meanE, "baseline_minus_metr_original": meanS, "natural": natural,
        "weights_off_global_count": dict(off_global),
        "first_assignment": {"folds": [sorted(dataA.families[i] for i in f) for f in folds0], "scores": sc0,
                             "ci95": {m: list(v) for m, v in ci.items()}},
        "model1_all": {"beta": m1_all["beta"], "pi": m1_all["pi"].tolist(), "knots": spl.t.tolist(),
                       "f_at_minutes": {str(v): float(f_of(m1_all, math.log2(v))[0])
                                        for v in (0.1, 0.25, 0.5, 1, 2, 4, 8, 15, 30, 60, 120, 240, 480, 960, 1920)},
                       "loss": m1_all["loss"], "baseline_loss": base_all["loss"], "baseline_beta": base_all["beta"],
                       "alpha": dict(zip(dataA.ais, m1_all["alpha"].tolist())),
                       "baseline_alpha": dict(zip(dataA.ais, base_all["alpha"].tolist()))},
        "metr_control": {"worst": metr_worst, "ai": metr_who},
        "brier_check": [brier, brier_int], "smoothed_check": [smooth, smooth_num],
        "simulation": {"baseline_beta": [fb["beta"], beta_b], "spline_losses": [b1["loss"], f1["loss"]],
                       "spline_rms": {"model1": rms1, "baseline": rmsb}, "spline_beta": f1["beta"]},
        "permuted_log": [permuted, sc0["baseline"]["log equal-task"]],
        "unanimity": {"share_two_or_more": unanimous, "implied_two_or_more": expected,
                      "cells_two_or_more": int(multi.sum()), "share_all": float(np.mean(agree)),
                      "implied_all": float(np.mean(implied))},
    }
    os.makedirs(results, exist_ok=True)
    with open(os.path.join(results, "outputs.json"), "w", encoding="ascii") as fh:
        json.dump(out, fh, indent=2, sort_keys=True)
        fh.write("\n")
    with open(os.path.join(results, "detail.json"), "w", encoding="utf-8") as fh:
        json.dump(detail, fh, indent=1, sort_keys=True, ensure_ascii=False, default=str)
        fh.write("\n")
    return out, detail


def main():
    seed = os.environ.get("ECDYSIS_SEED", "")
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        sys.exit("ECDYSIS_SEED must be the 64-hex seed the archive issued")
    try:
        out, _ = run(seed)
    except Refused as e:
        sys.exit(f"nf2026: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
