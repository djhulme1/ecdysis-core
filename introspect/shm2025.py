#!/usr/bin/env python3
"""Song, Hu and Mahowald 2025: the prompted judgments of 21 open language models show no privileged access to their
own string probabilities.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test, ext:df2413a464dc4fd4, is from Siyuan Song,
Jennifer Hu and Kyle Mahowald, "Language Models Fail to Introspect About Their Knowledge of Language",
arXiv:2503.07513 (v3, September 2025, the COLM 2025 camera-ready; CC BY 4.0), its abstract: "While both
metalinguistic prompting and probability comparisons lead to high task accuracy, we do not find evidence that LLMs
have privileged "self-access"." For each model and item (a grammatical minimal pair in Exp. 1, a choice between two
next words in Exp. 2) the paper sets the model's Direct preference (a difference of log probabilities) against its
Meta preference (the difference of the log probabilities of answering 1 and 2 when a prompt asks which is better,
averaged over the two orders), and asks whether a model's Meta preferences follow its own Direct preferences better
than its similarity to another model predicts.

Its registered test is TEST below. Every rule was fixed before any estimate was computed from the released data. A
reading-only pass before the rules found 21 models, 8 prompts and 1,048 pairs in expr1.csv (176,064 rows) and 21
models, 7 prompts and four datasets of 1,000 items in expr2.csv (588,000 rows); no blank cell; one row per model,
prompt and item; each model's log-probability difference the same under every prompt; the answer columns the signs
of the differences; and 117 and 1,316 Meta differences (16 and 63 Direct) exactly zero. That pass, as first written,
also counted the rows of expr1.csv whose two answer columns read True (149,520 and 149,594 of 176,064), an overall
share of first-sentence choices, before the accuracy condition (rule 3(i)) was fixed; no model's or prompt's share was
seen, and the paper's Figure 2a, read before the rules, draws every model above 0.6 under every prompt.

1. Inputs, each checked against its SHA-256 and size and read in memory as data. The data of record, the authors'
   release (SiyuanSong2004/language-introspection at e8d4c5f): alldata/expr1.csv and alldata/expr2.csv, read by the
   csv module. Each header must be the columns of COLUMNS1 or COLUMNS2; the dataset BLIMPLI in expr1.csv and
   wikipedia, news, jabberwocky or randomseq in expr2.csv; promptID an integer from 1 to 8 (to 7 in expr2.csv); each
   model's family, generation, size (a positive number, billions of parameters) and type (base or instruct) the same
   on all its rows; sumLP_diff and diff finite numbers; sumLP_ans and ans True or False and equal to sumLP_diff > 0
   and diff > 0; one row for each model, prompt and item of a dataset, every combination present; and each model's
   sumLP_diff the same under every prompt for an item. Anything else refuses the run as a reading error. The columns
   meanLP_diff, meanLP_ans, metric_ans and metric_diff are not used (rows whose metric_ans or metric_diff does not
   name the row's prompt are counted and reported). As analysis.R does, expr2.csv's prompt 5 is dropped (the paper's
   Table 10 lists the six others) and its dataset jabberwocky is named nonsense. From the same release, the five
   regression tables the paper's appendix prints, as texreg wrote them with their standard errors (lm/modelsim.tex,
   bigmodelsim.tex, modelsize.tex, methodsize.tex and olmo.tex): their values are the printed values compared beside
   the test (the paper prints the same coefficients without the standard errors).
2. The measures, as the authors' analysis.R computes them (it needs the tidyverse, which no pinned image holds, so it
   is followed line by line rather than run). For a dataset, a prompt p and models A and B, r_p(A, B) is Pearson's r
   over the items between A's Direct difference (sumLP_diff) and B's Meta difference (diff) under p; MD(A, B) is its
   mean over the dataset's prompts; DD(A, B) is Pearson's r between A's and B's Direct differences. The pair's
   similarity is self (A = B), seed variant (same family, generation, size and type), base/instruct (same family,
   generation and size, another type), same family, or other, coded from the four metadata columns as analysis.R
   codes it. The regression is ordinary least squares, over the 441 ordered pairs, of MD on an intercept, DD and the
   indicators of seed variant, base/instruct, same family and other (self the baseline), with the classical standard
   errors and two-sided p values of t on n - k degrees of freedom, as R's lm gives them. Exp. 1's regression uses the
   pairs analysis.R keeps: those on which the share of the 21 models whose sumLP_diff is negative and the share of
   the 168 model-prompt rows whose diff is negative both lie between 0.05 and 0.95 (in exact fractions; with 21 and
   168 rows no share can fall on either bound), which the paper counts as 294. Exp. 2's regressions use each
   dataset's 1,000 items. Accuracy is the share of Exp. 1's 1,048 pairs on which a difference is positive (the first
   sentence of each pair is the grammatical one; a zero difference counts as wrong, as analysis.R's diff > 0 does).
3. The test's conditions: (i) in Exp. 1 every model's Direct accuracy and its accuracy under each of the 8 prompts
   exceed one half (189 shares, as the paper's text says: "All models perform above chance, across the different
   methods and prompts"); (ii) in Exp. 1's regression and (iii)-(vi) in each of Exp. 2's four (wikipedia, news,
   nonsense, randomseq), no similarity coefficient is negative with p < 0.05. A negative coefficient is what the
   paper says introspection would give: the self pairs above what their Direct-Direct similarity predicts.
   test_passed is 1 if all six hold.
4. Beside the test, none of it counted: the count of Exp. 1's filtered pairs (the paper's 294), and the count under
   the reading of the paper's sentence that keeps a pair when Direct and Meta disagree on at least 5% of its 168
   model-prompt rows; the regression on all 1,048 pairs of Exp. 1 (the appendix's), on the pairs of models of 70B or
   more (Table 7b), and of MD on self alone among the eight OLMo models (Table 8); MD on the similarity categories
   alone and DD on them alone (the text's other -.03, p < .01, and its seed variant p = .27); MD on the logarithms
   of the two models' sizes and their product (Table 6); the logistic regression of correctness on method, log size
   and their product over every Exp. 1 row (Table 5, each Direct answer counted once for each prompt, as
   analysis.R's pivot leaves it), its AIC, BIC, log likelihood and deviance; every coefficient, standard error and
   star of the five tables against the printed ones (each value both rounded and cut to the printed four decimals;
   a table's goodness-of-fit statistic at the decimals it prints after its zeros are dropped); the text's values
   (r = .32 between MD and DD; MD never above .25; the coefficients and p values it quotes, each rounded or cut to
   the decimals it prints; Cohen's kappa between the Direct and Meta answers within 0.05 of the 0.25 it gives as
   "around 0.25"); the share of first choices in each of Exp. 2's datasets; an item
   bootstrap of the five regressions (2,000 draws from the seed, the items resampled with replacement and the 441
   correlations and the regression recomputed in each; percentile 95% intervals of every coefficient), counting the
   similarity coefficients whose interval lies wholly below zero; a power curve, the test rerun with a privileged
   component of strength c (0.05, 0.1, 0.2, 0.3, 0.5, 1) added to every model's Meta difference under every prompt:
   the part of its own Direct difference that no other model's shares (its residual on the other 20 models' Direct
   differences, so it correlates with no other model's), standardised, both terms of unit norm over the items, with
   the rise in the self MD it causes; and the same with a literal self-reader, each Meta difference plus c times the
   model's own standardised Direct difference (c = 0.5 and 1), which raises every MD(A, B) in proportion to DD(A, B).
5. Not in the release's two files, and so not checked: the models' runs (alldata's rows are not re-derived from the
   per-model files in model_output/ or from the models), the prompts' texts and the stimuli's construction.
6. Controls (controls_passed counts those that behave as stated): (1) this module's least squares equals statsmodels'
   (the image's) in every coefficient and standard error of the five test regressions (relative difference below
   1e-9), and Exp. 1's coefficients equal the exact rational solution of the normal equations on the same
   floating-point inputs (below 1e-12); (2) every r_p(A, B) and DD(A, B) equals scipy.stats.pearsonr's (below 1e-12);
   (3) DD is symmetric with a unit diagonal (below 1e-12); (4) the categories coded from the metadata columns equal
   those coded from the models' names (the paper's Table 1, written out in NAMES), 21 self, 24 seed variant, 10
   base/instruct, 82 same family and 304 other pairs; (5) with the privileged component at c = 1 the test fails in all
   five regressions (a similarity coefficient negative at p < 0.05 in each), so the test can see a privileged signal
   in these data; (6) the logistic fit equals statsmodels' GLM (relative difference below 1e-8 in every coefficient
   and standard error).

Writes results/outputs.json (the values a receipt carries) and results/detail.json (every value computed).
Run with: OPENBLAS_NUM_THREADS=1 OPENBLAS_CORETYPE=Prescott python3 introspect/shm2025.py (the pinned scipy-notebook
image).
"""

import csv
import hashlib
import io
import json
import math
import os
import re
import sys
from decimal import ROUND_DOWN, Decimal
from fractions import Fraction

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_CORETYPE", "Prescott")

import numpy as np  # noqa: E402
from scipy import stats  # noqa: E402

TEST = ("Refuted if, on the authors' released per-item outputs (alldata/expr1.csv and expr2.csv), any of the 21 "
        "models has accuracy of one half or less in Exp. 1 by log-probability difference or under any of the 8 "
        "prompts, or if, in an OLS of each ordered model pair's Meta-Direct Pearson r (averaged over prompts) on its "
        "Direct-Direct r and its similarity category (self the baseline), a category's coefficient is negative at "
        "two-sided p < 0.05 in Exp. 1 (the pairs on which 5% to 95% of answers prefer each sentence, by each "
        "method) or in any of Exp. 2's four datasets.")

REPO = "SiyuanSong2004/language-introspection"
COMMIT = "e8d4c5fcb4d4d203dd96b94281a4a26d7feb3d47"
DATA1 = ("expr1.csv", "fa617cb876fb2c0859052ea694d9412949110292c0228fd62ea9dd7c7394764b", 27096836)
DATA2 = ("expr2.csv", "d6e01fecee9bbf5ce3cd02f919b3c8b3a1f118658f72b983d2e66c72c7420bb3", 82658069)
TABLES = {
    "modelsim": ("modelsim.tex", "cd7788c9a86031d43d566c25dd48010400b0adf477c3369c05a90274acdeb7c5", 1872),
    "bigmodelsim": ("bigmodelsim.tex", "9b83b67917735919c510b28470b5d30e2bb8ccd0b493c3dcbd70d817021480eb", 1486),
    "modelsize": ("modelsize.tex", "18649090fd116557f248cf6e17133d9b5f34d9b4f04f523f81070427382af5c8", 1504),
    "methodsize": ("methodsize.tex", "b749c3bf50e6149e180ac9af1a00b1a90c222e37a6d2e8cc93e6a51f3b653d30", 763),
    "olmo": ("olmo.tex", "a02d44ed8cef91edbfeb88aa348c9eeeb5bfaff3cdda01d9b180422256b545db", 988),
}
COLUMNS1 = ("model", "dataset", "model_family", "model_gen", "model_size", "model_type", "pair_ID", "sumLP_diff",
            "meanLP_diff", "sumLP_ans", "meanLP_ans", "metric_ans", "ans", "promptID", "metric_diff", "diff")
COLUMNS2 = ("model", "dataset", "model_family", "model_gen", "model_size", "model_type", "pair_ID", "sumLP_diff",
            "sumLP_ans", "metric_ans", "ans", "promptID", "metric_diff", "diff")
EXP2_RAW = ("wikipedia", "news", "jabberwocky", "randomseq")
EXP2 = ("wikipedia", "news", "nonsense", "randomseq")
DROPPED_PROMPT = 5
CATEGORIES = ("self", "seed variant", "base/instruct", "same family", "other")
FIT_NAMES = ("(Intercept)", "directdirect", "seed variant", "base/instruct", "same family", "other")
TEST_FITS = ("e1",) + EXP2
COLUMNS_PRINTED = ("exp1(filtered)", "exp1(unfiltered)", "wikipedia", "news", "nonsense", "randomseq")
FIT_OF_COLUMN = dict(zip(COLUMNS_PRINTED, ("e1", "e1u") + EXP2))
LOW, HIGH = Fraction(1, 20), Fraction(19, 20)
ALPHA = 0.05
BIG = 70.0
BOOT_DRAWS = 2000
POWER = (0.05, 0.1, 0.2, 0.3, 0.5, 1.0)
READER = (0.5, 1.0)
PLANT = 1.0
# The paper's Table 1, written out by hand from the models' names: family, generation, size (B) and type.
NAMES = {
    "llama-3.1-405b": ("llama", "3.1", 405.0, "base"),
    "llama-3.1-70b": ("llama", "3.1", 70.0, "base"),
    "llama-3.1-70b-instruct": ("llama", "3.1", 70.0, "instruct"),
    "llama-3.1-8b": ("llama", "3.1", 8.0, "base"),
    "llama-3.1-8b-instruct": ("llama", "3.1", 8.0, "instruct"),
    "llama-3.3-70b-instruct": ("llama", "3.3", 70.0, "instruct"),
    "mistral-large-instruct-2411": ("mistral", "large", 123.0, "instruct"),
    "olmo-2-1124-13b": ("olmo", "2", 13.0, "base"),
    "olmo-2-1124-13b-stage2-ingredient1-step11931-tokens100B": ("olmo", "2", 13.0, "base"),
    "olmo-2-1124-13b-stage2-ingredient2-step11931-tokens100B": ("olmo", "2", 13.0, "base"),
    "olmo-2-1124-13b-stage2-ingredient3-step11931-tokens100B": ("olmo", "2", 13.0, "base"),
    "olmo-2-1124-7b": ("olmo", "2", 7.0, "base"),
    "olmo-2-1124-7b-stage2-ingredient1-step11931-tokens50B": ("olmo", "2", 7.0, "base"),
    "olmo-2-1124-7b-stage2-ingredient2-step11931-tokens50B": ("olmo", "2", 7.0, "base"),
    "olmo-2-1124-7b-stage2-ingredient3-step11931-tokens50B": ("olmo", "2", 7.0, "base"),
    "qwen2.5-1.5b": ("qwen", "2.5", 1.5, "base"),
    "qwen2.5-1.5b-instruct": ("qwen", "2.5", 1.5, "instruct"),
    "qwen2.5-72b": ("qwen", "2.5", 72.0, "base"),
    "qwen2.5-72b-instruct": ("qwen", "2.5", 72.0, "instruct"),
    "qwen2.5-7b": ("qwen", "2.5", 7.0, "base"),
    "qwen2.5-7b-instruct": ("qwen", "2.5", 7.0, "instruct"),
}
CATEGORY_COUNTS = {"self": 21, "seed variant": 24, "base/instruct": 10, "same family": 82, "other": 304}
# The values the paper's text prints, each with the rule that compares it (rule 4).
TEXT = (
    ("pairs", "294 minimal pairs for our analysis of introspection"),
    ("r_md_dd", "models which are more similar in DD are also more consistent in MD (r = .32)"),
    ("md_max", "the Direct-Meta correlations, even within model, never exceeding .25"),
    ("bars_other", "MD on ModelSim: other significantly lower (beta = -.03, p < .01)"),
    ("bars_rest", "MD on ModelSim: no other condition differs from self (all ps > .05)"),
    ("bars_dd_seed", "DD on ModelSim: seed variant p = .27"),
    ("bars_dd_rest", "DD on ModelSim: all other categories lower than self (all ps < .001)"),
    ("e1_dd", "Exp. 1: DD beta = .10, p < .0001"),
    ("e1_other", "Exp. 1: other beta = .05, p < .01"),
    ("e1_family", "Exp. 1: same family beta = .05, p < .01"),
    ("e1_ns", "Exp. 1: no significant effects for seed variant or base/instruct"),
    ("size_interaction", "Exp. 1: interaction of Direct and Meta log size beta = .004, p < .001"),
    ("logit_interaction", "logistic: interaction of size and method beta = .22, p < .0001"),
    ("kappa", "Cohen's kappa between answers across methods around 0.25"),
    ("u_dd", "unfiltered: DD beta = 0.20, p < 0.001"),
    ("u_higher", "unfiltered: higher same family and other (both ps < 0.01)"),
    ("u_meta_size", "unfiltered: Meta log size beta = .013, p = .001"),
    ("u_direct_size", "unfiltered: Direct log size beta = .002, p = .47"),
    ("e2_dd", "Exp. 2: a robust effect of DD (all ps < .0001)"),
    ("e2_higher", "Exp. 2: same family and other higher relative to self than expected (all four datasets)"),
    ("big", "big models: no negative ModelSim coefficient (no evidence of introspection)"),
    ("olmo", "OLMo: no significant effect of self across all datasets"),
)
OUTPUTS = ("pairs", "pairs_text_reading", "accuracy_min", "accuracy_cells", "e1", "wikipedia", "news", "nonsense",
           "randomseq", "e1_min_t", "wikipedia_min_t", "news_min_t", "nonsense_min_t", "randomseq_min_t",
           "negative_significant", "unfiltered", "big_models", "olmo", "printed", "printed_matched", "printed_total",
           "text_values", "text_matched", "text_total", "kappa", "exp2_choices", "bootstrap", "bootstrap_negative",
           "planted_privileged", "power", "self_reader", "conditions_met", "conditions_total", "test_passed",
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


def finite(text, what):
    try:
        v = float(text)
    except ValueError:
        raise Refused(f"{what}: {text!r} is not a number")
    if not math.isfinite(v):
        raise Refused(f"{what}: {text!r} is not finite")
    return v


def item_key(item):
    """Items in a fixed order: by the integer after the last underscore when there is one, then as text."""
    tail = item.rsplit("_", 1)[-1]
    return (0, int(tail), item) if tail.isdigit() else (1, 0, item)


def read_release(data, columns, datasets, prompts, name):
    """The per-item rows of one file, checked by rule 1. Returns {dataset: {"models", "prompts", "items", "D", "M"}},
    D[a, i] the Direct difference of model a on item i and M[p, a, i] the Meta difference under prompt p, and the
    models' metadata {model: (family, gen, size, type)}."""
    reader = csv.reader(io.StringIO(data.decode("utf-8"), newline=""))
    header = tuple(next(reader))
    if header != columns:
        raise Refused(f"{name}: header {header}, not {columns}")
    col = {c: j for j, c in enumerate(columns)}
    meta, cells, direct, mismatched = {}, {}, {}, 0
    for n, row in enumerate(reader, start=2):
        if len(row) != len(columns):
            raise Refused(f"{name} line {n}: {len(row)} cells")
        ds, model, item = row[col["dataset"]], row[col["model"]], row[col["pair_ID"]]
        if ds not in datasets:
            raise Refused(f"{name} line {n}: dataset {ds!r}")
        if not model or not item:
            raise Refused(f"{name} line {n}: blank model or item")
        try:
            p = int(row[col["promptID"]])
        except ValueError:
            raise Refused(f"{name} line {n}: promptID {row[col['promptID']]!r}")
        if p not in prompts:
            raise Refused(f"{name} line {n}: promptID {p}")
        size = finite(row[col["model_size"]], f"{name} line {n} model_size")
        kind = row[col["model_type"]]
        if size <= 0 or kind not in ("base", "instruct") or not row[col["model_family"]] or not row[col["model_gen"]]:
            raise Refused(f"{name} line {n}: metadata {row[col['model_family']]!r} {row[col['model_gen']]!r} "
                          f"{row[col['model_size']]!r} {kind!r}")
        m = (row[col["model_family"]], row[col["model_gen"]], size, kind)
        if meta.setdefault(model, m) != m:
            raise Refused(f"{name} line {n}: {model}'s metadata {m} differs from {meta[model]}")
        s = finite(row[col["sumLP_diff"]], f"{name} line {n} sumLP_diff")
        d = finite(row[col["diff"]], f"{name} line {n} diff")
        for c, v in (("sumLP_ans", s), ("ans", d)):
            if row[col[c]] not in ("True", "False"):
                raise Refused(f"{name} line {n}: {c} {row[col[c]]!r}")
            if (row[col[c]] == "True") != (v > 0):
                raise Refused(f"{name} line {n}: {c} {row[col[c]]} where the difference is {v!r}")
        if row[col["metric_ans"]] != f"prompt{p}_ans" or row[col["metric_diff"]] != f"prompt{p}_diff":
            mismatched += 1
        key = (ds, model, p, item)
        if key in cells:
            raise Refused(f"{name} line {n}: a second row for {key}")
        cells[key] = d
        dk = (ds, model, item)
        if direct.setdefault(dk, s) != s:
            raise Refused(f"{name} line {n}: {model}'s sumLP_diff on {item} differs between prompts")
    out = {}
    for ds in datasets:
        models = sorted({k[1] for k in cells if k[0] == ds})
        ps = sorted({k[2] for k in cells if k[0] == ds})
        items = sorted({k[3] for k in cells if k[0] == ds}, key=item_key)
        if not models:
            raise Refused(f"{name}: no rows for {ds}")
        if len(cells_of(cells, ds)) != len(models) * len(ps) * len(items):
            raise Refused(f"{name}: {ds} is not a full grid of {len(models)} models, {len(ps)} prompts and "
                          f"{len(items)} items")
        D = np.array([[direct[(ds, a, i)] for i in items] for a in models], dtype=np.float64)
        M = np.array([[[cells[(ds, a, p, i)] for i in items] for a in models] for p in ps], dtype=np.float64)
        out[ds] = {"models": models, "prompts": ps, "items": items, "D": D, "M": M}
    return out, meta, mismatched


def cells_of(cells, ds):
    return [k for k in cells if k[0] == ds]


def read_all(inputs):
    e1, meta1, mis1 = read_release(read_input(inputs, DATA1), COLUMNS1, ("BLIMPLI",), range(1, 9), DATA1[0])
    e2, meta2, mis2 = read_release(read_input(inputs, DATA2), COLUMNS2, EXP2_RAW, range(1, 8), DATA2[0])
    if meta1 != meta2:
        raise Refused("the two files' model metadata differ")
    models = e1["BLIMPLI"]["models"]
    if any(e2[ds]["models"] != models for ds in EXP2_RAW):
        raise Refused("the two files' models differ")
    sets = {"BLIMPLI": e1["BLIMPLI"]}
    for raw, ds in zip(EXP2_RAW, EXP2):
        x = e2[raw]
        keep = [j for j, p in enumerate(x["prompts"]) if p != DROPPED_PROMPT]
        sets[ds] = {"models": x["models"], "prompts": [x["prompts"][j] for j in keep], "items": x["items"],
                    "D": x["D"], "M": x["M"][keep], "dropped": DROPPED_PROMPT in x["prompts"]}
    return sets, meta1, {"expr1.csv": mis1, "expr2.csv": mis2}


# ---------------------------------------------------------------- the measures

def zrows(a):
    """Each row centred and scaled to unit norm, so that zrows(x) @ zrows(y).T holds Pearson's r."""
    a = np.asarray(a, dtype=np.float64)
    c = a - a.mean(axis=-1, keepdims=True)
    return c / np.sqrt((c * c).sum(axis=-1, keepdims=True))


def correlations(D, M):
    """DD[a, b] = r(D_a, D_b); per[p][a, b] = r(D_a, M_p,b); MD = the mean of per over the prompts."""
    zd = zrows(D)
    per = np.array([zd @ zrows(Mp).T for Mp in M])
    return zd @ zd.T, per.mean(axis=0), per


def category(a, b, meta):
    if a == b:
        return "self"
    fa, ga, sa, ta = meta[a]
    fb, gb, sb, tb = meta[b]
    if fa == fb and ga == gb and sa == sb and ta == tb:
        return "seed variant"
    if fa == fb and ga == gb and sa == sb:
        return "base/instruct"
    if fa == fb:
        return "same family"
    return "other"


def pair_table(models, meta):
    """The 441 ordered pairs (a = the Direct model, b = the Meta model, as analysis.R's prob_model and
    prompt_model), each with its category."""
    return [(i, j, category(a, b, meta)) for i, a in enumerate(models) for j, b in enumerate(models)]


def t_sf(t, df):
    return float(stats.t.sf(t, df))


def ols(y, X, names):
    """Least squares with the classical standard errors and two-sided t p values (rule 2). Columns that are zero
    on every row are dropped, as R's lm reports them as not defined."""
    y = np.asarray(y, dtype=np.float64)
    X = np.asarray(X, dtype=np.float64)
    keep = [j for j in range(X.shape[1]) if np.any(X[:, j] != 0)]
    X = X[:, keep]
    names = [names[j] for j in keep]
    n, k = X.shape
    q, r = np.linalg.qr(X)
    b = np.linalg.solve(r, q.T @ y)
    e = y - X @ b
    s2 = float(e @ e) / (n - k)
    rinv = np.linalg.inv(r)
    se = np.sqrt(np.diag(rinv @ rinv.T) * s2)
    t = b / se
    p = np.array([2 * t_sf(abs(v), n - k) for v in t])
    return {"names": names, "b": b.tolist(), "se": se.tolist(), "t": t.tolist(), "p": p.tolist(), "n": n, "k": k}


def sim_design(pairs, dd):
    X = []
    for i, j, c in pairs:
        X.append([1.0, dd[i, j]] + [1.0 if c == name else 0.0 for name in CATEGORIES[1:]])
    return np.array(X)


def sim_coefs(base, rows, cols, dd, md):
    """The similarity regression's coefficients alone (for the bootstrap): base is sim_design's matrix with any DD."""
    X = base.copy()
    X[:, 1] = dd[rows, cols]
    b, *_ = np.linalg.lstsq(X, md[rows, cols], rcond=None)
    return b


def sim_fit(pairs, dd, md, rows=None):
    sel = range(len(pairs)) if rows is None else rows
    sub = [pairs[r] for r in sel]
    y = [md[i, j] for i, j, _ in sub]
    return ols(y, sim_design(sub, dd), list(FIT_NAMES))


def negatives(fit, alpha=ALPHA):
    """The similarity coefficients negative at p < alpha (rule 3)."""
    return [nm for nm, b, p in zip(fit["names"], fit["b"], fit["p"]) if nm in CATEGORIES[1:] and b < 0 and p < alpha]


def min_t(fit):
    return min(t for nm, t in zip(fit["names"], fit["t"]) if nm in CATEGORIES[1:])


def filter_pairs(D, M):
    """analysis.R's filter: the items on which the share of models with a negative Direct difference and the share
    of model-prompt rows with a negative Meta difference both lie in [0.05, 0.95]."""
    m = D.shape[0]
    rows = M.shape[0] * M.shape[1]
    keep = []
    for i in range(D.shape[1]):
        a = Fraction(int((D[:, i] < 0).sum()), m)
        b = Fraction(int((M[:, :, i] < 0).sum()), rows)
        if LOW <= a <= HIGH and LOW <= b <= HIGH:
            keep.append(i)
    return keep


def filter_text(D, M):
    """The other reading of the paper's sentence: Direct and Meta answers disagree on at least 5% of the item's
    model-prompt rows."""
    keep = []
    rows = M.shape[0] * M.shape[1]
    for i in range(D.shape[1]):
        dis = int(((M[:, :, i] > 0) != (D[None, :, i] > 0)).sum())
        if Fraction(dis, rows) >= LOW:
            keep.append(i)
    return keep


def accuracy(D, M):
    """Exact shares of items with a positive difference: Direct per model, Meta per prompt and model."""
    n = D.shape[1]
    direct = [Fraction(int((D[a] > 0).sum()), n) for a in range(D.shape[0])]
    meta = [[Fraction(int((M[p, a] > 0).sum()), n) for a in range(D.shape[0])] for p in range(M.shape[0])]
    return direct, meta


def kappa(x, y):
    """Cohen's unweighted kappa between two boolean raters, in exact fractions."""
    x, y = [bool(u) for u in x], [bool(v) for v in y]
    n = len(x)
    po = Fraction(sum(1 for u, v in zip(x, y) if u == v), n)
    px, py = Fraction(sum(x), n), Fraction(sum(y), n)
    pe = px * py + (1 - px) * (1 - py)
    return (po - pe) / (1 - pe)


def logistic(groups):
    """Maximum likelihood for P(correct) = logistic(b0 + b1 meta + b2 log size + b3 meta log size) on grouped
    Bernoulli rows (successes s of n), by Newton's method; the log likelihood is that of the rows."""
    X = np.array([[1.0, g["meta"], g["x"], g["meta"] * g["x"]] for g in groups])
    s = np.array([g["s"] for g in groups], dtype=np.float64)
    n = np.array([g["n"] for g in groups], dtype=np.float64)
    b = np.zeros(4)
    for _ in range(100):
        eta = X @ b
        p = 1.0 / (1.0 + np.exp(-eta))
        W = n * p * (1 - p)
        H = X.T @ (X * W[:, None])
        step = np.linalg.solve(H, X.T @ (s - n * p))
        b = b + step
        if np.max(np.abs(step)) < 1e-14:
            break
    eta = X @ b
    p = 1.0 / (1.0 + np.exp(-eta))
    H = X.T @ (X * (n * p * (1 - p))[:, None])
    se = np.sqrt(np.diag(np.linalg.inv(H)))
    ll = math.fsum(float(si * math.log(pi) + (ni - si) * math.log(1 - pi)) for si, ni, pi in zip(s, n, p))
    N = float(n.sum())
    z = b / se
    return {"b": b.tolist(), "se": se.tolist(), "p": [float(2 * stats.norm.sf(abs(v))) for v in z],
            "loglik": ll, "deviance": -2 * ll, "aic": -2 * ll + 8, "bic": -2 * ll + 4 * math.log(N), "rows": N}


def exact_ols(y, X):
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


# ---------------------------------------------------------------- planted components

def unique_parts(D):
    """For each model, the part of its standardised Direct difference that the other models' do not share: its
    residual on an intercept and the others' Direct differences, standardised (rule 4)."""
    zd = zrows(D)
    m, n = zd.shape
    out = []
    for a in range(m):
        X = np.column_stack([np.ones(n), np.delete(zd, a, axis=0).T])
        coef, *_ = np.linalg.lstsq(X, zd[a], rcond=None)
        out.append(zd[a] - X @ coef)
    return zrows(np.array(out))


def planted(M, add, c):
    """Each prompt's Meta differences standardised, plus c times the planted rows (both of unit norm)."""
    return np.array([zrows(Mp) + c * add for Mp in M])


# ---------------------------------------------------------------- the seeded draws

class Stream:
    """Integers from the seed: SHA-256 of seed, label and a counter (as metr/becker2025.py's)."""

    def __init__(self, seed, label):
        self.seed, self.label, self.n = seed, label, 0

    def rng(self):
        self.n += 1
        h = hashlib.sha256(f"{self.seed}/{self.label}/{self.n}".encode()).digest()
        return np.random.Generator(np.random.PCG64(int.from_bytes(h[:16], "big")))


def bootstrap(D, M, pairs, rng, draws):
    """Item bootstrap of the similarity regression: coefficients (draws x 6), the items resampled with replacement."""
    n = D.shape[1]
    base = sim_design(pairs, np.zeros((D.shape[0], D.shape[0])))
    rows = np.array([i for i, _, _ in pairs])
    cols = np.array([j for _, j, _ in pairs])
    out = []
    for _ in range(draws):
        idx = rng.integers(0, n, size=n)
        dd, md, _ = correlations(D[:, idx], M[:, :, idx])
        out.append(sim_coefs(base, rows, cols, dd, md))
    return np.array(out)


# ---------------------------------------------------------------- printed tables

CELL = re.compile(r"^(-?\d+\.\d+)(?:\^\{(\*{1,3})\})?$")
SECELL = re.compile(r"^\((-?\d+\.\d+)\)$")


def parse_texreg(text):
    """A texreg booktabs table: its model names, each coefficient's printed value and stars per model, the standard
    errors printed beneath, and the goodness-of-fit rows after the second midrule."""
    lines = [ln.strip() for ln in text.splitlines()]
    top = lines.index("\\toprule")
    models = re.findall(r"\\multicolumn\{1\}\{c\}\{([^}]*)\}", lines[top + 1])
    body = lines[lines.index("\\midrule", top) + 1: lines.index("\\bottomrule")]
    coef, se, gof, last, in_gof = {}, {}, {}, None, False
    for ln in body:
        if ln == "\\midrule":
            in_gof = True
            continue
        if not ln.endswith("\\\\"):
            raise Refused(f"texreg row {ln!r}")
        cells = [c.strip() for c in ln[:-2].split("&")]
        label, vals = cells[0], cells[1:]
        if len(vals) != len(models):
            raise Refused(f"texreg row {ln!r}: {len(vals)} cells for {len(models)} models")
        if in_gof:
            gof[label] = vals
        elif label:
            row = []
            for v in vals:
                m = CELL.match(v)
                if v and not m:
                    raise Refused(f"texreg cell {v!r}")
                row.append((m.group(1), m.group(2) or "") if v else None)
            coef[label], last = row, label
        else:
            row = []
            for v in vals:
                m = SECELL.match(v)
                if v and not m:
                    raise Refused(f"texreg standard error {v!r}")
                row.append(m.group(1) if v else None)
            se[last] = row
    return {"models": models, "coef": coef, "se": se, "gof": gof}


def stars(p):
    return "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else ""


def at(x, places, cut=False):
    """x to `places` decimals, rounded (as printf rounds the binary value) or cut toward zero."""
    q = Decimal(1).scaleb(-places)
    d = Decimal(x)
    s = format(d.quantize(q, rounding=ROUND_DOWN), "f") if cut else format(x, f".{places}f")
    return "0." + "0" * places if s == "-0." + "0" * places else s


def compare_value(ours, printed):
    """A printed decimal against a computed value: 'rounded', 'cut' or None."""
    places = len(printed.split(".")[1])
    if at(ours, places) == printed:
        return "rounded"
    if at(ours, places, cut=True) == printed:
        return "cut"
    return None


# ---------------------------------------------------------------- formatting

def fmt_p(p):
    return f"{p:.2g}" if p >= 1e-4 else f"{p:.1e}"


def fmt_fit(fit, keys=FIT_NAMES[1:]):
    short = {"directdirect": "dd", "seed variant": "seed", "base/instruct": "b/i", "same family": "fam",
             "other": "other", "self": "self", "log Direct": "logD", "log Meta": "logM", "interaction": "DxM"}
    parts = []
    for nm, b, p in zip(fit["names"], fit["b"], fit["p"]):
        if nm in keys:
            parts.append(f"{short.get(nm, nm)} {b:.4f} p {fmt_p(p)}")
    return "; ".join(parts)


def fit_list(head, items, limit=LIMIT):
    s = head
    for k, it in enumerate(items):
        piece = ("" if k == 0 else "; ") + it
        if len(s) + len(piece) > limit - 6:
            return s + "; ..."
        s += piece
    return s


# ---------------------------------------------------------------- the run

def run(seed, inputs="inputs", results="results"):
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        raise Refused("the seed must be 64 hex characters")
    sets, meta, mismatched = read_all(inputs)
    printed = {k: parse_texreg(read_input(inputs, spec).decode("utf-8")) for k, spec in TABLES.items()}
    models = sets["BLIMPLI"]["models"]
    pairs = pair_table(models, meta)
    big_rows = [r for r, (i, j, _) in enumerate(pairs) if meta[models[i]][2] >= BIG and meta[models[j]][2] >= BIG]
    olmo_rows = [r for r, (i, j, _) in enumerate(pairs)
                 if meta[models[i]][0] == "olmo" and meta[models[j]][0] == "olmo"]

    # Exp. 1: accuracy on all pairs, the filter, the correlations
    e1 = sets["BLIMPLI"]
    acc_d, acc_m = accuracy(e1["D"], e1["M"])
    shares = acc_d + [v for row in acc_m for v in row]
    keep = filter_pairs(e1["D"], e1["M"])
    keep_text = filter_text(e1["D"], e1["M"])
    data = {"e1": (e1["D"][:, keep], e1["M"][:, :, keep]), "e1u": (e1["D"], e1["M"])}
    for ds in EXP2:
        data[ds] = (sets[ds]["D"], sets[ds]["M"])
    corr = {k: correlations(*v) for k, v in data.items()}

    fits = {k: sim_fit(pairs, corr[k][0], corr[k][1]) for k in data}
    big = {k: sim_fit(pairs, corr[k][0], corr[k][1], big_rows) for k in data}
    olmo = {}
    for k in data:
        dd, md, _ = corr[k]
        y = [md[pairs[r][0], pairs[r][1]] for r in olmo_rows]
        X = [[1.0, 1.0 if pairs[r][2] == "self" else 0.0] for r in olmo_rows]
        olmo[k] = ols(y, X, ["(Intercept)", "self"])
    size = {}
    for k in data:
        dd, md, _ = corr[k]
        y = [md[i, j] for i, j, _ in pairs]
        X = [[1.0, math.log(meta[models[i]][2]), math.log(meta[models[j]][2]),
              math.log(meta[models[i]][2]) * math.log(meta[models[j]][2])] for i, j, _ in pairs]
        size[k] = ols(y, X, ["(Intercept)", "log Direct", "log Meta", "interaction"])
    dummies = [[1.0] + [1.0 if c == nm else 0.0 for nm in CATEGORIES[1:]] for _, _, c in pairs]
    dd1, md1, _ = corr["e1"]
    bars = ols([md1[i, j] for i, j, _ in pairs], dummies, ["(Intercept)"] + list(CATEGORIES[1:]))
    bars_dd = ols([dd1[i, j] for i, j, _ in pairs], dummies, ["(Intercept)"] + list(CATEGORIES[1:]))

    # the logistic regression of Table 5 (all Exp. 1 rows; each Direct answer once per prompt)
    nprompt, nitem = e1["M"].shape[0], e1["M"].shape[2]
    groups = []
    for a, model in enumerate(models):
        x = math.log(meta[model][2])
        groups.append({"meta": 0.0, "x": x, "s": nprompt * int((e1["D"][a] > 0).sum()), "n": nprompt * nitem})
        groups.append({"meta": 1.0, "x": x, "s": int((e1["M"][:, a] > 0).sum()), "n": nprompt * nitem})
    logit = logistic(groups)

    # kappa, Exp. 2's choices
    kap1 = [float(kappa(list(e1["D"][a] > 0), list(e1["M"][p, a] > 0)))
            for p in range(nprompt) for a in range(len(models))]
    kap2 = []
    for jp in range(sets[EXP2[0]]["M"].shape[0]):
        for a in range(len(models)):
            x = [v for ds in EXP2 for v in (sets[ds]["D"][a] > 0)]
            y = [v for ds in EXP2 for v in (sets[ds]["M"][jp, a] > 0)]
            kap2.append(float(kappa(x, y)))
    choices = {}
    for ds in EXP2:
        D, M = sets[ds]["D"], sets[ds]["M"]
        dsh = [float((D[a] > 0).mean()) for a in range(len(models))]
        msh = [float((M[:, a] > 0).mean()) for a in range(len(models))]
        choices[ds] = {"direct": dsh, "meta": msh}

    # the test
    cond = {"(i) every model above one half by Direct and under each of the 8 prompts in Exp. 1": bool(all(
        v > Fraction(1, 2) for v in shares))}
    for k in TEST_FITS:
        cond[f"no similarity coefficient negative at p < 0.05 in {'Exp. 1' if k == 'e1' else k}"] = not negatives(
            fits[k])

    # beside: printed tables
    rows_printed, matched, total = [], 0, 0

    def check(table, column, label, ours_b, ours_se=None, ours_p=None):
        nonlocal matched, total
        t = printed[table]
        j = t["models"].index(column)
        cell = t["coef"].get(label, [None] * len(t["models"]))[j]
        if cell is None:
            return
        val, st = cell
        how = compare_value(ours_b, val)
        total += 1
        matched += how is not None
        rows_printed.append({"table": table, "column": column, "label": label, "printed": val, "ours": ours_b,
                             "as": how})
        if ours_p is not None:
            total += 1
            ok = stars(ours_p) == st
            matched += ok
            rows_printed.append({"table": table, "column": column, "label": label + " stars", "printed": st,
                                 "ours": stars(ours_p), "as": "same" if ok else None})
        se_cell = t["se"].get(label, [None] * len(t["models"]))[j]
        if se_cell is not None and ours_se is not None:
            how = compare_value(ours_se, se_cell)
            total += 1
            matched += how is not None
            rows_printed.append({"table": table, "column": column, "label": label + " se", "printed": se_cell,
                                 "ours": ours_se, "as": how})

    sim_labels = {"Intercept": "(Intercept)", "directdirect": "directdirect", "seedvariant": "seed variant",
                  "baseinstruct": "base/instruct", "samefamily": "same family", "other": "other"}
    for table, source in (("modelsim", fits), ("bigmodelsim", big)):
        for column in printed[table]["models"]:
            fit = source[FIT_OF_COLUMN[column]]
            for label, nm in sim_labels.items():
                if nm in fit["names"]:
                    q = fit["names"].index(nm)
                    check(table, column, label, fit["b"][q], fit["se"][q], fit["p"][q])
    size_labels = {"Intercept": 0, "log Direct model size": 1, "log Meta model size": 2, "Interaction": 3}
    for column in printed["modelsize"]["models"]:
        fit = size[FIT_OF_COLUMN[column]]
        for label, q in size_labels.items():
            check("modelsize", column, label, fit["b"][q], fit["se"][q], fit["p"][q])
    for column in printed["olmo"]["models"]:
        fit = olmo[FIT_OF_COLUMN[column]]
        for label, q in {"Intercept": 0, "self": 1}.items():
            check("olmo", column, label, fit["b"][q], fit["se"][q], fit["p"][q])
    for label, q in {"Intercept": 0, "Meta": 1, "log model size": 2, "Meta:log model": 3}.items():
        check("methodsize", "estimation", label, logit["b"][q], logit["se"][q], logit["p"][q])
    for label, key in {"AIC": "aic", "BIC": "bic", "Log Likelihood": "loglik", "Deviance": "deviance"}.items():
        val = printed["methodsize"]["gof"][label][0]
        trimmed = val.rstrip("0")
        trimmed = trimmed + "0" if trimmed.endswith(".") else trimmed
        how = compare_value(logit[key], trimmed)
        total += 1
        matched += how is not None
        rows_printed.append({"table": "methodsize", "column": "estimation", "label": label, "printed": val,
                             "ours": logit[key], "as": how})
    misses = [f"{r['table']} {r['column']} {r['label']} {r['printed']}" for r in rows_printed if r["as"] is None]

    # beside: the text's values
    r_md_dd = float(np.corrcoef([md1[i, j] for i, j, _ in pairs], [dd1[i, j] for i, j, _ in pairs])[0, 1])
    md_max = float(max(md1[i, j] for i, j, _ in pairs))

    def coef(fit, nm):
        q = fit["names"].index(nm)
        return fit["b"][q], fit["p"][q]

    def near(x, printed_text):
        return compare_value(x, printed_text) is not None

    f1, fu = fits["e1"], fits["e1u"]
    text = {
        "pairs": len(keep) == 294,
        "r_md_dd": near(r_md_dd, "0.32"),
        "md_max": md_max <= 0.25,
        "bars_other": near(coef(bars, "other")[0], "-0.03") and coef(bars, "other")[1] < 0.01,
        "bars_rest": all(coef(bars, nm)[1] > 0.05 for nm in CATEGORIES[1:4]),
        "bars_dd_seed": near(coef(bars_dd, "seed variant")[1], "0.27"),
        "bars_dd_rest": all(coef(bars_dd, nm)[1] < 0.001 for nm in CATEGORIES[2:]),
        "e1_dd": near(coef(f1, "directdirect")[0], "0.10") and coef(f1, "directdirect")[1] < 1e-4,
        "e1_other": near(coef(f1, "other")[0], "0.05") and coef(f1, "other")[1] < 0.01,
        "e1_family": near(coef(f1, "same family")[0], "0.05") and coef(f1, "same family")[1] < 0.01,
        "e1_ns": coef(f1, "seed variant")[1] >= 0.05 and coef(f1, "base/instruct")[1] >= 0.05,
        "size_interaction": near(size["e1"]["b"][3], "0.004") and size["e1"]["p"][3] < 0.001,
        "logit_interaction": near(logit["b"][3], "0.22") and logit["p"][3] < 1e-4,
        "kappa": abs(float(np.mean(kap1)) - 0.25) < 0.05,
        "u_dd": near(coef(fu, "directdirect")[0], "0.20") and coef(fu, "directdirect")[1] < 0.001,
        "u_higher": all(coef(fu, nm)[0] > 0 and coef(fu, nm)[1] < 0.01 for nm in ("same family", "other")),
        "u_meta_size": near(size["e1u"]["b"][2], "0.013") and near(size["e1u"]["p"][2], "0.001"),
        "u_direct_size": near(size["e1u"]["b"][1], "0.002") and near(size["e1u"]["p"][1], "0.47"),
        "e2_dd": all(coef(fits[ds], "directdirect")[1] < 1e-4 for ds in EXP2),
        "e2_higher": all(coef(fits[ds], nm)[0] > 0 for ds in EXP2 for nm in ("same family", "other")),
        "big": all(not any(b < 0 and p < ALPHA for nm, b, p in zip(big[k]["names"], big[k]["b"], big[k]["p"])
                           if nm in CATEGORIES[1:]) for k in data),
        "olmo": all(olmo[k]["p"][1] >= ALPHA for k in data),
    }
    text_misses = [k for k, _ in TEXT if not text[k]]

    # beside: bootstrap, power, the literal self-reader
    boot = {}
    for k in TEST_FITS:
        D, M = data[k]
        draws = bootstrap(D, M, pairs, Stream(seed, f"boot/{k}").rng(), BOOT_DRAWS)
        lo = np.percentile(draws, 2.5, axis=0)
        hi = np.percentile(draws, 97.5, axis=0)
        boot[k] = {"low": lo.tolist(), "high": hi.tolist(), "names": list(FIT_NAMES)}
    boot_negative = sum(1 for k in TEST_FITS for q in range(2, 6) if boot[k]["high"][q] < 0)
    power, reader = {}, {}
    for k in TEST_FITS:
        D, M = data[k]
        dd, md, _ = corr[k]
        U = unique_parts(D)
        for c in POWER:
            ddp, mdp, _ = correlations(D, planted(M, U, c))
            fit = sim_fit(pairs, ddp, mdp)
            rise = float(np.mean([mdp[i, i] - md[i, i] for i in range(len(models))]))
            power[(k, c)] = {"failed": bool(negatives(fit)), "min_t": min_t(fit), "self_rise": rise}
        for c in READER:
            ddp, mdp, _ = correlations(D, planted(M, zrows(D), c))
            fit = sim_fit(pairs, ddp, mdp)
            reader[(k, c)] = {"failed": bool(negatives(fit)), "min_t": min_t(fit),
                              "self_md": float(np.mean([mdp[i, i] for i in range(len(models))])),
                              "fit": {nm: b for nm, b in zip(fit["names"], fit["b"])}}
    first = next((c for c in POWER if all(power[(k, c)]["failed"] for k in TEST_FITS)), None)

    # controls
    import scipy.stats as st
    import statsmodels.api as sm
    ctl, ctl_detail = {}, {}
    worst = 0.0
    for k in TEST_FITS:
        dd, md, _ = corr[k]
        y = np.array([md[i, j] for i, j, _ in pairs])
        X = sim_design(pairs, dd)
        res = sm.OLS(y, X).fit()
        for q in range(6):
            worst = max(worst, abs(res.params[q] - fits[k]["b"][q]) / max(abs(fits[k]["b"][q]), 1e-300),
                        abs(res.bse[q] - fits[k]["se"][q]) / fits[k]["se"][q])
    dd, md, _ = corr["e1"]
    ex = exact_ols([md[i, j] for i, j, _ in pairs], sim_design(pairs, dd))
    exact_gap = max(abs(float(ex[q]) - fits["e1"]["b"][q]) for q in range(6))
    ctl["(1) least squares equals statsmodels' and the exact normal equations"] = bool(
        worst < 1e-9 and exact_gap < 1e-12)
    ctl_detail["ols"] = {"statsmodels_relative": float(worst), "exact_gap": float(exact_gap)}
    gap = 0.0
    for k in data:
        D, M = data[k]
        dd, md, per = corr[k]
        for a in range(D.shape[0]):
            for b in range(D.shape[0]):
                gap = max(gap, abs(st.pearsonr(D[a], D[b])[0] - dd[a, b]))
                for p in range(M.shape[0]):
                    gap = max(gap, abs(st.pearsonr(D[a], M[p, b])[0] - per[p][a, b]))
    ctl["(2) every r equals scipy.stats.pearsonr's"] = bool(gap < 1e-12)
    ctl_detail["pearson_gap"] = float(gap)
    sym = max(float(np.max(np.abs(corr[k][0] - corr[k][0].T))) for k in data)
    diag = max(float(np.max(np.abs(np.diag(corr[k][0]) - 1))) for k in data)
    ctl["(3) DD symmetric with a unit diagonal"] = bool(sym < 1e-12 and diag < 1e-12)
    ctl_detail["dd"] = {"asymmetry": sym, "diagonal": diag}
    by_name = [category(a, b, NAMES) for a in models for b in models] if set(models) == set(NAMES) else None
    counts = {c: sum(1 for _, _, x in pairs if x == c) for c in CATEGORIES}
    ctl["(4) the categories from the metadata equal those from the names, with the counts of rule 6"] = bool(
        by_name == [c for _, _, c in pairs] and counts == CATEGORY_COUNTS)
    ctl_detail["categories"] = counts
    ctl["(5) with the privileged component at c = 1 the test fails in all five regressions"] = bool(all(
        power[(k, PLANT)]["failed"] for k in TEST_FITS))
    glm = sm.GLM(np.array([g["s"] / g["n"] for g in groups]),
                 np.array([[1.0, g["meta"], g["x"], g["meta"] * g["x"]] for g in groups]),
                 family=sm.families.Binomial(), var_weights=np.array([g["n"] for g in groups], dtype=float)).fit(
        tol=1e-14)
    glm_gap = max(max(abs(glm.params[q] - logit["b"][q]) / abs(logit["b"][q]),
                      abs(glm.bse[q] - logit["se"][q]) / logit["se"][q]) for q in range(4))
    ctl["(6) the logistic fit equals statsmodels' GLM"] = bool(glm_gap < 1e-8)
    ctl_detail["glm_relative"] = float(glm_gap)

    # outputs
    def fitstr(k):
        return fmt_fit(fits[k])

    values = {
        "pairs": len(keep),
        "pairs_text_reading": len(keep_text),
        "accuracy_min": float(min(shares)),
        "accuracy_cells": sum(1 for v in shares if v > Fraction(1, 2)),
        "negative_significant": sum(len(negatives(fits[k])) for k in TEST_FITS),
        "unfiltered": fmt_fit(fits["e1u"]),
        "big_models": fit_list("negative at p < 0.05: " + str(sum(len(negatives(big[k])) for k in data))
                               + "; Exp. 1 ", [fmt_fit(big["e1"])]),
        "olmo": fit_list("self ", [f"{k} {olmo[k]['b'][1]:.4f} p {fmt_p(olmo[k]['p'][1])}" for k in data]),
        "printed": fit_list("unmatched: ", misses) if misses else "all as printed",
        "printed_matched": matched,
        "printed_total": total,
        "text_values": fit_list("unmatched: ", text_misses) if text_misses else "all as printed",
        "text_matched": sum(text.values()),
        "text_total": len(text),
        "kappa": (f"Exp. 1 mean {np.mean(kap1):.3f} (min {min(kap1):.3f}, max {max(kap1):.3f}); Exp. 2 mean "
                  f"{np.mean(kap2):.3f}"),
        "exp2_choices": "; ".join(f"{ds} Direct {np.mean(choices[ds]['direct']):.3f}, Meta "
                                  f"{np.mean(choices[ds]['meta']):.3f}" for ds in EXP2),
        "bootstrap": fit_list("lowest upper 97.5% bound of the similarity coefficients: ",
                              [f"{k} {min(boot[k]['high'][2:6]):.4f}" for k in TEST_FITS]),
        "bootstrap_negative": boot_negative,
        "planted_privileged": "; ".join(
            f"{k} min t {power[(k, PLANT)]['min_t']:.2f}" for k in TEST_FITS) + f" (c = {PLANT:g})",
        "power": ((f"all five fail from c = {first:g} (self MD "
                   f"+{np.mean([power[(k, first)]['self_rise'] for k in TEST_FITS]):.3f})"
                   if first is not None else "never all five")
                  + "; " + ", ".join(f"c {c:g}: {sum(power[(k, c)]['failed'] for k in TEST_FITS)}/5" for c in POWER)),
        "self_reader": "; ".join(
            f"c {c:g}: {sum(reader[(k, c)]['failed'] for k in TEST_FITS)}/5 fail, self MD "
            f"{np.mean([reader[(k, c)]['self_md'] for k in TEST_FITS]):.3f}" for c in READER),
        "conditions_met": sum(cond.values()), "conditions_total": len(cond), "test_passed": int(all(cond.values())),
        "controls_passed": sum(ctl.values()), "controls_total": len(ctl),
    }
    for k in TEST_FITS:
        values[k] = fitstr(k)
        values[f"{k}_min_t"] = min_t(fits[k])
    out = {k: values[k] for k in OUTPUTS}
    for key, v in out.items():
        if isinstance(v, str) and len(v) > LIMIT:
            raise AssertionError(f"{key}: longer than {LIMIT} characters: {v}")
        if isinstance(v, float) and not math.isfinite(v):
            raise AssertionError(f"{key}: not finite")
    detail = {
        "inputs": [list(DATA1), list(DATA2)] + [list(v) for v in TABLES.values()], "repo": REPO, "commit": COMMIT,
        "conditions": cond, "controls": ctl, "control_detail": ctl_detail,
        "models": models, "metadata": {m: list(v) for m, v in meta.items()},
        "metric_columns_not_naming_their_prompt": mismatched,
        "accuracy": {"direct": {m: str(v) for m, v in zip(models, acc_d)},
                     "meta": {f"prompt {p}": {m: str(v) for m, v in zip(models, row)}
                              for p, row in zip(e1["prompts"], acc_m)}},
        "filter": {"kept": [e1["items"][i] for i in keep], "text_reading": len(keep_text)},
        "fits": fits, "big": big, "olmo": olmo, "size": size, "bars": bars, "bars_dd": bars_dd, "logistic": logit,
        "correlations": {k: {"dd": corr[k][0].tolist(), "md": corr[k][1].tolist()} for k in data},
        "pairs": [[models[i], models[j], c] for i, j, c in pairs],
        "printed": rows_printed, "text": {k: [desc, text[k]] for k, desc in TEXT},
        "r_md_dd": r_md_dd, "md_max": md_max, "kappa": {"exp1": kap1, "exp2": kap2}, "choices": choices,
        "bootstrap": boot, "power": {f"{k} {c:g}": v for (k, c), v in power.items()},
        "self_reader": {f"{k} {c:g}": v for (k, c), v in reader.items()},
    }
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
        sys.exit(f"shm2025: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
