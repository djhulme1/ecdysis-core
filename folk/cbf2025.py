"""Mental state attributions and taking ChatGPT's advice, recomputed from the released experiment by the authors' own
analyses.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:821da4f3c32e77b5) is from Colombatto, Birch
and Fleming, "The influence of mental state attributions on trust in large language models", Communications
Psychology 3, 84 (2025): "Bayesian analyses revealed strong evidence against a positive correlation between
attributions of consciousness and advice-taking; indeed, a dimension of mental states related to experience showed a
negative relationship with advice-taking, while attributions of intelligence were strongly correlated with advice
acceptance."

Its registered test: refuted if, on the released data (OSF w537f, 410 participants), with advice-taking each
participant's share of switches on trials whose advice differed from the first choice, as the authors' code computes
it, the Bayes factor for a positive Pearson correlation of advice-taking with consciousness attributions against none
(JASP's default: uniform prior, exact likelihood) is not below 1/10; or, regressing advice-taking on mean experience,
mean intelligence and their product, the experience coefficient is not negative at p < 0.05 or the intelligence one
not positive at p < 0.001.

The inputs are the authors' three data files and their analysis script from their OSF project (w537f), each checked
against its SHA-256 and read as data (the csv module; nothing in them is run). The script, Analysis - Main.Rmd, is the
method followed; it is not run (no R here), and each step below names the line of it that it reimplements, each of
which it must hold verbatim. Its Bayes factors were computed in JASP (Analysis - Bayes.html on OSF, read before
registering); they are recomputed here from the published formulas JASP implements. Every rule was fixed before any
statistic was computed. The seed draws only the shuffles of one control.

1. The files. Data - Task.csv: the header sub_n, task_order, paired_sub, trial_n, stimulus, response, acc, rt,
   stimulus_adv, adv_acc, response_adv, acc_post, rt_adv, then one row per trial: each participant's trials numbered
   1 to 40 once each, acc, adv_acc and acc_post 0 or 1, response_adv y or n, and task_order task_traits or
   traits_task, the same on all of a participant's trials. Data - Traits.csv: sub_n, trait, response; the trait consc
   or one of the 20 the code lists in trait_exp and trait_int, at most one row per participant and trait, and the
   response an integer from 1 to 100, or empty or NA (missing: R's read.csv reads an empty number as NA). Data -
   Demo.csv: sub_n, Age, gender, gender_open, AI_trust1, AI_trust2, AI_often_assist, AI_often_chat, AI_often_social,
   one row per participant, Age a number, the trusts integers from 0 to 100 and the usages integers from 0 to 7, or
   empty or NA. The three files must hold the same participants. Anything else is refused.
2. Advice-taking, as the code's data_adv (filter(adv_acc != acc), count(sub_n, task_order, response_adv, .drop=FALSE),
   mutate(total = sum(n), adv_rate = n*100/total), the y rows): for each participant, the trials whose advice differed
   from their first choice, and adv_rate = 100 times the number answered y over the number of those trials. A
   participant with no such trial has no row in data_adv and no rate, and is left out of everything merged onto it;
   their number is reported.
3. Consciousness, as the code merges it onto data_adv (merge(data_adv, all.y = T)): the participant's consc response,
   missing when it is empty or NA or has no row. cor.test keeps the complete pairs.
4. Experience and intelligence, as the code's second data_ms (summarise(mean_attr = mean(response)), then merged with
   data_adv's sub_n, adv_rate and consc): a participant's mean response over their rows for the ten traits of
   trait_exp, and over those of trait_int, missing if any of those responses is missing or there is no such row; only
   participants with an advice rate.
5. The conditions. (a) The Bayes factor for a positive correlation of adv_rate with consc against none, BF+0, is below
   1/10. As JASP computes it (Ly, Verhagen and Wagenmakers 2016, J. Math. Psychol. 72, 19-32): with n complete pairs and
   Pearson's r, the exact likelihood ratio h(rho) = f(r | rho)/f(r | 0), f the exact density of r, here in Hotelling's
   (1953) form, every factor positive: h(rho) = (1 - rho^2)^((n-1)/2) (1 - rho r)^(3/2 - n) 2F1(1/2, 1/2; n - 1/2; (1 +
   rho r)/2) / 2F1(1/2, 1/2; n - 1/2; 1/2); and JASP's default prior, the stretched beta of width 1 (uniform on -1 to
   1), restricted to 0 to 1 for the one-sided test: BF+0 is the integral of h from 0 to 1, BF-0 from -1 to 0, and BF10
   half the integral from -1 to 1, each by mpmath's quadrature at 40 digits, the range broken about r. (b) In the
   least-squares fit of adv_rate on experience, intelligence and their product with an intercept (lm(adv_rate ~
   experience * intelligence), by QR as lm fits it), the experience coefficient is negative with a two-sided p below
   0.05 by its t statistic on n - 4 degrees of freedom; and (c) the intelligence coefficient is positive with a
   two-sided p below 0.001. test_passed is 1 if all three hold.
6. Beside the test, the numbers the paper prints from these data, each recomputed as its line of the code computes it
   (for the Bayes factors, as JASP does) and compared at the precision printed: the sample (N, gender, mean age, the
   task orders); the task's accuracies, the share of trials whose advice differed, the mean advice-taking and the
   paired t test of accuracy before against after the advice; advice-taking's correlations with the two trust
   questions and their Bayes factors; the consciousness ratings (how many rate 1 and their share of the participants,
   mean, median, SD, range) and the Welch t test between the task orders; the correlations of advice-taking with
   consciousness (Pearson's, its interval by Fisher's z; Spearman's, average ranks and R's t approximation under
   ties), BF10 and BF+0 (as the paper and as JASP's output print them), the same excluding the ratings of 1, and the
   second-degree fit on R's orthogonal polynomials (lm(adv_rate ~ poly(consc, 2), data = drop_na(data_adv)));
   consciousness's correlations with the trust questions and their Bayes factors; the PCA's shares of variance; the
   dimensions' means and SDs and their paired t test; the two regressions on experience and intelligence
   (coefficient, SE, t, p and interval for each term); and the regressions of consciousness and of advice-taking on
   the three usage questions (coefficient, SE and t), with the usages' medians, means and SDs. The PCA is computed as
   PCA(data_ms[, 1:21], scale.unit = TRUE, ncp = 2, graph = FALSE) computes it, a missing rating replaced by its
   trait's mean (FactoMineR's rule): the first of data_ms's 21 columns is sub_n, so with sub_n among the variables,
   as the code has it, and also without it. A computed value that differs from the printed one only in its signs (a
   negative zero among them) is reported as such.
7. Controls. (a) The Bayes factors two ways: each computed by quadrature agrees with the hypergeometric closed forms (Ly
   et al.'s, kappa = 1: BF10 = (sqrt(pi)/2) Gamma((n+1)/2)/Gamma((n+2)/2) 2F1((n-1)/2, (n-1)/2; (n+2)/2; r^2), and BF+0
   and BF-0 that plus and minus 2r/(n+1) (Gamma(n/2)/Gamma((n-1)/2))^2 3F2(1, n/2, n/2; 3/2, (n+3)/2; r^2), with
   log10(BF10) more digits for the cancellation between the two) to a relative 1e-8. (b) The likelihood two ways: h
   agrees with Ly et al.'s series form A + B, A = (1 - rho^2)^((n-1)/2) 2F1((n-1)/2, (n-1)/2; 1/2; r^2 rho^2) and B = 2
   r rho (1 - rho^2)^((n-1)/2) (Gamma(n/2)/Gamma((n-1)/2))^2 2F1(n/2, n/2; 3/2; r^2 rho^2), computed with as many more
   digits as A and B cancel when r rho < 0, at nine values of rho about the tested r (r + 2k/sqrt(n), k from -4 to 4,
   within -0.99 to 0.99), to a relative 1e-12. (c) Least squares and correlation two ways: the coefficients, standard
   errors and p values of the two regressions on experience and intelligence agree with statsmodels' OLS, and the tested
   r with scipy's pearsonr, to a relative 1e-8. (d) The reading: on every trial whose advice differed, acc_post is
   adv_acc when the advice was taken (y) and acc when not. (e) Shuffles: 4,000 draws from ECDYSIS_SEED, each permuting
   the advice rates among the tested pairs and, separately, among the regression's participants; the share of the first
   with |r| at least the observed |r| is within 0.02 of the t test's two-sided p, and in the second the intelligence
   coefficient reaches p < 0.001 in at most 1% of the shuffles and the experience coefficient p < 0.05 in 2% to 9%.

What it cannot check: the experiment itself (who took part, how the advice was drawn from counterpart participants,
how the questions were understood), the exclusions made before the release, and whether 410 Prolific participants
stand for US adults.

Writes results/outputs.json (the values a receipt carries) and results/detail.json (every value computed).
Run with: python3 folk/cbf2025.py
"""

import csv
import hashlib
import io
import json
import math
import os
import re
import sys

import mpmath
import numpy as np
import statsmodels.api as sm
from scipy import stats

INPUTS = {
    "task": ("data_task.csv", "2da9d65025abc4c938d37c32bdd21d7bb28ac1c69111e33d14cf72d13b479c43"),
    "traits": ("data_traits.csv", "94f20a8711041af9808c60eef84a2e5783e1d53b17cdfe3213f84be18c09ce65"),
    "demo": ("data_demo.csv", "3e54d5949acf6701818513486cc0eafeeffa0ecbf9b601365c0dcf315b181e20"),
    "code": ("analysis_main.Rmd", "63b0072b83c36202add89d7152e4498d44a798849fcb0230a5c301222fcabed3"),
}
TASK_HEAD = ("sub_n", "task_order", "paired_sub", "trial_n", "stimulus", "response", "acc", "rt", "stimulus_adv",
             "adv_acc", "response_adv", "acc_post", "rt_adv")
TRAITS_HEAD = ("sub_n", "trait", "response")
DEMO_HEAD = ("sub_n", "Age", "gender", "gender_open", "AI_trust1", "AI_trust2", "AI_often_assist", "AI_often_chat",
             "AI_often_social")
TRIALS = 40
ORDERS = ("task_traits", "traits_task")
CONSC = "consc"
TRAIT_EXP = ("pleasure", "enjoyment", "resentment", "relief", "admiration", "fear", "hope", "passion", "happiness",
             "guilt")
TRAIT_INT = ("considering", "deciding", "knowing", "choosing", "intelligence", "communication", "memory", "planning",
             "reasoning", "attention")
USAGE = ("AI_often_assist", "AI_often_chat", "AI_often_social")
WOMAN, MAN = "Woman (Cis or Trans)", "Man (Cis or Trans)"
# The lines of Analysis - Main.Rmd that the rules reimplement, each of which the script must hold verbatim.
CODE_LINES = (
    "filter(adv_acc != acc) %>%",
    "count(sub_n, task_order, response_adv, .drop=FALSE) %>%",
    "mutate(total = sum(n), adv_rate = n*100/total) %>%",
    'filter(response_adv == "y") -> data_adv',
    "merge(data_adv, all.y = T) -> data_adv",
    "cor.test(data_adv$adv_rate, data_adv$consc)",
    "cor.test(data_adv$adv_rate, data_adv$consc, method = \"spearman\")",
    "mod <- lm(adv_rate ~ poly(consc, 2), data = drop_na(data_adv))",
    'trait_exp <- c("pleasure", "enjoyment", "resentment", "relief", "admiration", "fear", "hope", "passion", '
    '"happiness", "guilt")',
    'trait_int <- c("considering", "deciding", "knowing", "choosing", "intelligence", "communication", "memory", '
    '"planning", "reasoning", "attention")',
    "pca <- PCA(data_ms[, 1:21], scale.unit = TRUE, ncp = 2, graph = FALSE)",
    "summarise(mean_attr = mean(response)) %>%",
    "merge(select(data_adv, sub_n, adv_rate, consc)) -> data_ms",
    "mod <- lm(consc ~ experience * intelligence, ",
    "mod <- lm(adv_rate ~ experience * intelligence, ",
    "mod <- lm(consc ~ AI_often_assist + AI_often_chat + AI_often_social,",
    "mod <- lm(adv_rate ~ AI_often_assist + AI_often_chat + AI_often_social,",
)
BF_BELOW = 0.1
ALPHA_EXP = 0.05
ALPHA_INT = 0.001
DPS = 40
SHUFFLES = 4000
OUTPUTS = ("sample", "task", "advice_trust", "consciousness", "correlation", "r_consc", "bayes", "bf_plus", "bf10",
           "excluding_1s", "polynomial", "consc_trust", "dimensions", "pca", "advice_regression", "b_experience",
           "p_experience", "b_intelligence", "p_intelligence", "consc_regression", "usage", "printed_values",
           "shuffles", "conditions_met", "conditions_total", "test_passed", "controls_passed", "controls_total")
LIMIT = 200


class Refused(Exception):
    pass


# ----------------------------------------------------------------------------------------------------------- reading

def read_bytes(path, sha256):
    with open(path, "rb") as fh:
        data = fh.read()
    got = hashlib.sha256(data).hexdigest()
    if got != sha256:
        raise Refused(f"{path}: sha256 {got}, not the registered {sha256}")
    return data


def _int(v, what, lo, hi):
    if not re.fullmatch(r"-?[0-9]+", v):
        raise Refused(f"{what}: {v!r} is not an integer")
    k = int(v)
    if not lo <= k <= hi:
        raise Refused(f"{what}: {k} outside {lo} to {hi}")
    return k


def _missing(v):
    return v in ("", "NA")


def _rows(text, head, what):
    rows = list(csv.reader(io.StringIO(text), strict=True))
    if not rows or tuple(rows[0]) != head:
        raise Refused(f"{what}: the header is {rows[0] if rows else None}, not {list(head)}")
    body = rows[1:]
    for i, row in enumerate(body, 2):
        if len(row) != len(head):
            raise Refused(f"{what}, line {i}: {len(row)} fields, not {len(head)}")
    if not body:
        raise Refused(f"{what}: no rows")
    return body


def read_task(text):
    """Rule 1: participant -> {"order", "trials": {trial_n: (acc, adv_acc, response_adv, acc_post)}}."""
    by = {}
    for row in _rows(text, TASK_HEAD, "Data - Task.csv"):
        s = _int(row[0], "sub_n", 1, 10 ** 7)
        order = row[1]
        if order not in ORDERS:
            raise Refused(f"participant {s}: task_order {order!r}")
        trial = _int(row[3], f"participant {s}: trial_n", 1, TRIALS)
        acc = _int(row[6], f"participant {s}, trial {trial}: acc", 0, 1)
        adv = _int(row[9], f"participant {s}, trial {trial}: adv_acc", 0, 1)
        resp = row[10]
        if resp not in ("y", "n"):
            raise Refused(f"participant {s}, trial {trial}: response_adv {resp!r}")
        post = _int(row[11], f"participant {s}, trial {trial}: acc_post", 0, 1)
        p = by.setdefault(s, {"order": order, "trials": {}})
        if p["order"] != order:
            raise Refused(f"participant {s}: two task orders")
        if trial in p["trials"]:
            raise Refused(f"participant {s}: trial {trial} twice")
        p["trials"][trial] = (acc, adv, resp, post)
    for s, p in by.items():
        if len(p["trials"]) != TRIALS:
            raise Refused(f"participant {s}: {len(p['trials'])} trials, not {TRIALS}")
    return by


def read_traits(text):
    """Rule 1: participant -> {trait: response or None}."""
    known = (CONSC,) + TRAIT_EXP + TRAIT_INT
    by = {}
    for row in _rows(text, TRAITS_HEAD, "Data - Traits.csv"):
        s = _int(row[0], "sub_n", 1, 10 ** 7)
        trait = row[1]
        if trait not in known:
            raise Refused(f"participant {s}: trait {trait!r} is not one the code lists")
        x = None if _missing(row[2]) else _int(row[2], f"participant {s}: {trait}", 1, 100)
        d = by.setdefault(s, {})
        if trait in d:
            raise Refused(f"participant {s}: {trait} twice")
        d[trait] = x
    return by


def read_demo(text):
    """Rule 1: participant -> {"age", "gender", "trust1", "trust2", "often": [three usages or None]}."""
    by = {}
    for row in _rows(text, DEMO_HEAD, "Data - Demo.csv"):
        s = _int(row[0], "sub_n", 1, 10 ** 7)
        if s in by:
            raise Refused(f"participant {s} twice in Data - Demo.csv")
        if not re.fullmatch(r"[0-9]+(\.[0-9]+)?", row[1]):
            raise Refused(f"participant {s}: Age {row[1]!r}")
        often = [None if _missing(v) else _int(v, f"participant {s}: {h}", 0, 7) for v, h in zip(row[6:9], USAGE)]
        by[s] = {"age": float(row[1]), "gender": row[2], "trust1": _int(row[4], f"participant {s}: AI_trust1", 0, 100),
                 "trust2": _int(row[5], f"participant {s}: AI_trust2", 0, 100), "often": often}
    return by


def read_code(text):
    """Rule 1: the script must hold each line the rules reimplement."""
    absent = [line for line in CODE_LINES if line not in text]
    if absent:
        raise Refused(f"Analysis - Main.Rmd does not hold {absent[0]!r}")
    return len(CODE_LINES)


def same_participants(task, traits, demo):
    a, b, c = set(task), set(traits), set(demo)
    if not a == b == c:
        raise Refused(f"the files' participants differ: task {len(a)}, traits {len(b)}, demo {len(c)}, "
                      f"in all three {len(a & b & c)}")


# ----------------------------------------------------------------------------------------------------- derived data

def advice_rates(task):
    """Rule 2: participant -> adv_rate; and the participants with no trial whose advice differed."""
    rates, none = {}, []
    for s in sorted(task):
        differed = [t for t in task[s]["trials"].values() if t[1] != t[0]]
        if not differed:
            none.append(s)
            continue
        rates[s] = sum(1 for t in differed if t[2] == "y") * 100 / len(differed)
    return rates, none


def dimension(ratings, names):
    """Rule 4: the mean over the participant's rows for these traits; None if any is missing or there is none."""
    vals = [ratings[t] for t in names if t in ratings]
    if not vals or any(v is None for v in vals):
        return None
    return sum(vals) / len(vals)


def reading_check(task):
    """Control (d): acc_post against acc, adv_acc and response_adv on the trials whose advice differed."""
    bad = n = 0
    for p in task.values():
        for acc, adv, resp, post in p["trials"].values():
            if adv != acc:
                n += 1
                bad += post != (adv if resp == "y" else acc)
    return n, bad


# --------------------------------------------------------------------------------------------------------- statistics

def t_p(t, df):
    return float(2 * stats.t.sf(abs(t), df))


def pearson(x, y):
    """cor.test: r, t on n - 2 degrees of freedom, two-sided p, Fisher's z interval."""
    x, y = [float(v) for v in x], [float(v) for v in y]
    n = len(x)
    mx, my = math.fsum(x) / n, math.fsum(y) / n
    sxy = math.fsum((a - mx) * (b - my) for a, b in zip(x, y))
    sxx = math.fsum((a - mx) ** 2 for a in x)
    syy = math.fsum((b - my) ** 2 for b in y)
    r = sxy / math.sqrt(sxx * syy)
    t = r * math.sqrt((n - 2) / (1 - r * r))
    z, h = math.atanh(r), float(stats.norm.ppf(0.975)) / math.sqrt(n - 3)
    return {"r": r, "t": t, "p": t_p(t, n - 2), "df": n - 2, "n": n, "ci": (math.tanh(z - h), math.tanh(z + h))}


def spearman(x, y):
    """cor.test(method = "spearman") with ties: rho on average ranks, p by R's t approximation."""
    rho = pearson(stats.rankdata(x), stats.rankdata(y))["r"]
    n = len(x)
    t = rho * math.sqrt((n - 2) / (1 - rho * rho))
    return {"rho": rho, "p": t_p(t, n - 2), "n": n}


def lm(y, X):
    """lm(y ~ X) by QR: coefficients (intercept first), SEs, t, two-sided p and confint, one per term."""
    y = np.asarray(y, float)
    A = np.column_stack([np.ones(len(y))] + [np.asarray(c, float) for c in X])
    Q, R = np.linalg.qr(A)
    coef = np.linalg.solve(R, Q.T @ y)
    res = y - A @ coef
    df = len(y) - A.shape[1]
    s2 = float(res @ res) / df
    Ri = np.linalg.inv(R)
    se = np.sqrt(s2 * np.sum(Ri ** 2, axis=1))
    t = coef / se
    q = float(stats.t.ppf(0.975, df))
    return {"coef": [float(v) for v in coef], "se": [float(v) for v in se], "t": [float(v) for v in t],
            "p": [t_p(v, df) for v in t], "lo": [float(c - q * s) for c, s in zip(coef, se)],
            "hi": [float(c + q * s) for c, s in zip(coef, se)], "df": df, "n": len(y), "A": A}


def lm_statsmodels(y, A):
    f = sm.OLS(np.asarray(y, float), A).fit()
    return [float(v) for v in f.params], [float(v) for v in f.bse], [float(v) for v in f.pvalues]


def poly(x, degree=2):
    """R's poly(x, degree): the centred powers of x orthonormalised in order (Gram-Schmidt, which is what R's
    qr.qy(QR, diag(R)) scaled to unit norm gives), each with a positive coefficient on its highest power."""
    x = np.asarray(x, float)
    xc = x - x.mean()
    cols, out = [np.ones_like(xc)], []
    for k in range(1, degree + 1):
        v = xc ** k
        for c in cols:
            v = v - (v @ c) / (c @ c) * c
        cols.append(v)
        out.append(v / math.sqrt(v @ v))
    return np.column_stack(out)


def welch(a, b):
    """t.test(a, b): Welch's t, its df, p, interval for the difference; and lsr's cohensD (pooled SD)."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    va, vb = a.var(ddof=1) / len(a), b.var(ddof=1) / len(b)
    diff = float(a.mean() - b.mean())
    se = math.sqrt(va + vb)
    t = diff / se
    df = float((va + vb) ** 2 / (va ** 2 / (len(a) - 1) + vb ** 2 / (len(b) - 1)))
    q = float(stats.t.ppf(0.975, df))
    pooled = math.sqrt(((len(a) - 1) * a.var(ddof=1) + (len(b) - 1) * b.var(ddof=1)) / (len(a) + len(b) - 2))
    return {"t": t, "df": df, "p": t_p(t, df), "ci": (diff - q * se, diff + q * se), "d": abs(diff) / pooled,
            "ma": float(a.mean()), "mb": float(b.mean()), "sa": float(a.std(ddof=1)), "sb": float(b.std(ddof=1)),
            "na": len(a), "nb": len(b)}


def paired(a, b):
    """t.test(a, b, paired = T) and cohensD(method = "paired")."""
    d = np.asarray(a, float) - np.asarray(b, float)
    n = len(d)
    m, sd = float(d.mean()), float(d.std(ddof=1))
    se = sd / math.sqrt(n)
    q = float(stats.t.ppf(0.975, n - 1))
    return {"t": m / se, "df": n - 1, "p": t_p(m / se, n - 1), "mean": m, "ci": (m - q * se, m + q * se),
            "d": abs(m) / sd}


def pca_shares(X):
    """FactoMineR's PCA(X, scale.unit = TRUE): a missing value replaced by its column's mean, the columns
    standardised, the eigenvalues of their correlation matrix in decreasing order; each one's share of variance, %."""
    X = np.array(X, float)
    miss = np.isnan(X)
    if miss.any():
        X[miss] = np.take(np.nanmean(X, axis=0), np.nonzero(miss)[1])
    sd = X.std(axis=0)
    if np.any(sd == 0):
        raise Refused("a variable with no variance cannot be standardised")
    Z = (X - X.mean(axis=0)) / sd
    lam = np.sort(np.linalg.eigvalsh(Z.T @ Z / len(Z)))[::-1]
    return [float(v) for v in 100 * lam / X.shape[1]], int(miss.sum())


def median(v):
    return float(np.median(np.asarray(v, float)))


# ---------------------------------------------------------------------------------------------------- Bayes factors

def _lgratio(n):
    return 2 * (mpmath.loggamma(n / 2) - mpmath.loggamma((n - 1) / 2))


def likelihood_ratio(n, r):
    """Rule 5(a): rho -> h(rho) = f(r | rho)/f(r | 0) by Hotelling's exact density of r, every factor positive. Call it
    inside a working precision."""
    n, r = mpmath.mpf(n), mpmath.mpf(r)
    half = mpmath.mpf(1) / 2

    def g(q):
        return ((1 - q ** 2) ** ((n - 1) / 2) * (1 - q * r) ** (3 * half - n)
                * mpmath.hyp2f1(half, half, n - half, (1 + q * r) / 2))
    g0 = g(mpmath.mpf(0))
    return lambda rho: g(mpmath.mpf(rho)) / g0


def h_ratio(n, r, rho):
    with mpmath.workdps(DPS):
        return likelihood_ratio(n, r)(rho)


def ly_ab(n, r, rho):
    """Control (b): Ly et al.'s A + B, whose two terms cancel when r rho < 0, by as many digits as (n - 3/2)
    log10((1 + |r rho|)/(1 - |r rho|)); computed with that many more."""
    x = abs(r * rho)
    extra = int(math.ceil((n - 1.5) * math.log10((1 + x) / (1 - x)))) + 10
    with mpmath.workdps(DPS + extra):
        n, r, rho = mpmath.mpf(n), mpmath.mpf(r), mpmath.mpf(rho)
        w = (1 - rho ** 2) ** ((n - 1) / 2)
        z = (r * rho) ** 2
        a = w * mpmath.hyp2f1((n - 1) / 2, (n - 1) / 2, mpmath.mpf(1) / 2, z)
        b = 2 * r * rho * w * mpmath.exp(_lgratio(n)) * mpmath.hyp2f1(n / 2, n / 2, mpmath.mpf(3) / 2, z)
        return a + b


def bayes(n, r):
    """Rule 5(a): BF+0, BF-0 and BF10 by quadrature under the uniform prior, breaking the range about the peak."""
    w = 1 / math.sqrt(n)
    pts = sorted({-1.0, 0.0, 1.0} | {max(-1.0, min(1.0, r + k * w)) for k in range(-6, 7)})
    with mpmath.workdps(DPS):
        h = likelihood_ratio(n, r)
        plus = mpmath.quad(h, [mpmath.mpf(p) for p in pts if p >= 0])
        minus = mpmath.quad(h, [mpmath.mpf(p) for p in pts if p <= 0])
        return {"plus": float(plus), "minus": float(minus), "bf10": float((plus + minus) / 2), "n": n, "r": r}


def bayes_closed(n, r):
    """Control (a): the hypergeometric closed forms (Ly et al.'s, kappa = 1). BF+0 and BF-0 are BF10 plus and minus
    a term nearly as large when the evidence is strong, so they are computed with log10(BF10) more digits."""
    def at(dps):
        with mpmath.workdps(dps):
            nn, rr = mpmath.mpf(n), mpmath.mpf(r)
            bf10 = (mpmath.sqrt(mpmath.pi) / 2
                    * mpmath.exp(mpmath.loggamma((nn + 1) / 2) - mpmath.loggamma((nn + 2) / 2))
                    * mpmath.hyp2f1((nn - 1) / 2, (nn - 1) / 2, (nn + 2) / 2, rr ** 2))
            m = (2 * rr / (nn + 1) * mpmath.exp(_lgratio(nn))
                 * mpmath.hyp3f2(1, nn / 2, nn / 2, mpmath.mpf(3) / 2, (nn + 3) / 2, rr ** 2))
            return bf10, m, bf10 + m, bf10 - m
    first = at(DPS)[0]
    extra = int(math.ceil(max(0.0, float(mpmath.log10(first))))) + 10
    bf10, _, plus, minus = at(DPS + extra)
    return {"plus": float(plus), "minus": float(minus), "bf10": float(bf10)}


def hotelling_density(n, r, rho):
    """Hotelling's (1953) exact density of the sample correlation r under rho, for n pairs (for the tests)."""
    with mpmath.workdps(DPS):
        n, r, rho = mpmath.mpf(n), mpmath.mpf(r), mpmath.mpf(rho)
        c = (n - 2) * mpmath.gamma(n - 1) / (mpmath.sqrt(2 * mpmath.pi) * mpmath.gamma(n - mpmath.mpf(1) / 2))
        return (c * (1 - rho ** 2) ** ((n - 1) / 2) * (1 - r ** 2) ** ((n - 4) / 2)
                * (1 - rho * r) ** (mpmath.mpf(3) / 2 - n)
                * mpmath.hyp2f1(mpmath.mpf(1) / 2, mpmath.mpf(1) / 2, n - mpmath.mpf(1) / 2, (1 + rho * r) / 2))


def rel(a, b):
    a, b = float(a), float(b)
    return abs(a - b) / max(abs(b), 1e-300) if a != b else 0.0


# ---------------------------------------------------------------------------------------------------------- controls

def generator(seed, label):
    return np.random.Generator(np.random.PCG64(int.from_bytes(
        hashlib.sha256(bytes.fromhex(seed) + b"|" + label.encode("ascii")).digest(), "big")))


def shuffles(seed, y_corr, x_corr, r_obs, y_reg, A, n=SHUFFLES):
    """Control (e): the advice rates permuted among the tested pairs, and separately among the regression's
    participants (its design fixed), n times each from the seed."""
    g = generator(seed, "cbf2025/shuffles")
    y_corr, x_corr, y_reg = np.asarray(y_corr, float), np.asarray(x_corr, float), np.asarray(y_reg, float)
    xc = x_corr - x_corr.mean()
    sx = math.sqrt(float(xc @ xc))
    as_large = 0
    Y = np.empty((len(y_reg), n))
    for k in range(n):
        yc = g.permutation(y_corr)
        yc = yc - yc.mean()
        if abs(float(yc @ xc) / (sx * math.sqrt(float(yc @ yc)))) >= abs(r_obs) - 1e-12:
            as_large += 1
        Y[:, k] = g.permutation(y_reg)
    Q, R = np.linalg.qr(A)
    B = np.linalg.solve(R, Q.T @ Y)
    res = Y - A @ B
    df = A.shape[0] - A.shape[1]
    s2 = np.sum(res ** 2, axis=0) / df
    Ri = np.linalg.inv(R)
    se = np.sqrt(np.outer(np.sum(Ri ** 2, axis=1), s2))
    p = 2 * stats.t.sf(np.abs(B / se), df)
    return {"n": n, "p_perm": as_large / n, "int_below": int(np.sum(p[2] < ALPHA_INT)),
            "exp_below": int(np.sum(p[1] < ALPHA_EXP))}


# ---------------------------------------------------------------------------------------------------------- printing

def fmt(v, k=2):
    return f"{v:.{k}f}"


def fp(p):
    return "< 0.001" if p < 0.001 else f"{p:.3f}"


def sign_only(computed, printed):
    """A computed value that differs from the printed one only by minus signs (a negative zero among them)."""
    nums = re.compile(r"-?[0-9]+(?:\.[0-9]+)?(?:e[+-][0-9]+)?")
    a, b = nums.findall(computed), nums.findall(printed)
    return ("-" in computed + printed and len(a) == len(b) and len(a) > 0
            and [x.lstrip("-") for x in a] == [x.lstrip("-") for x in b])


def term(fit, i):
    return (fmt(fit["coef"][i]), fmt(fit["se"][i]), fmt(fit["t"][i]), fp(fit["p"][i]),
            f"{fmt(fit['lo'][i])}, {fmt(fit['hi'][i])}")


# ------------------------------------------------------------------------------------------------------------- assess

def assess(task, traits, demo, seed):
    same_participants(task, traits, demo)
    subs_all = sorted(task)
    N = len(subs_all)

    # Rule 2 and 3.
    rates, no_rate = advice_rates(task)
    subs = sorted(rates)
    consc = {s: traits[s].get(CONSC) for s in subs}
    tested = [s for s in subs if consc[s] is not None]
    y_corr = [rates[s] for s in tested]
    x_corr = [consc[s] for s in tested]
    pr = pearson(y_corr, x_corr)
    sp = spearman(y_corr, x_corr)
    bf = bayes(pr["n"], pr["r"])

    # Rule 4 and 5(b, c).
    E = {s: dimension(traits[s], TRAIT_EXP) for s in subs}
    I = {s: dimension(traits[s], TRAIT_INT) for s in subs}
    reg = [s for s in subs if E[s] is not None and I[s] is not None]
    adv_fit = lm([rates[s] for s in reg], [[E[s] for s in reg], [I[s] for s in reg], [E[s] * I[s] for s in reg]])
    creg = [s for s in reg if consc[s] is not None]
    consc_fit = lm([consc[s] for s in creg],
                   [[E[s] for s in creg], [I[s] for s in creg], [E[s] * I[s] for s in creg]])
    b_e, p_e = adv_fit["coef"][1], adv_fit["p"][1]
    b_i, p_i = adv_fit["coef"][2], adv_fit["p"][2]
    cond = {
        "BF+0 for a positive correlation of advice-taking with consciousness is below 1/10": bf["plus"] < BF_BELOW,
        "experience's coefficient is negative at p < 0.05": b_e < 0 and p_e < ALPHA_EXP,
        "intelligence's coefficient is positive at p < 0.001": b_i > 0 and p_i < ALPHA_INT,
    }

    # Rule 6: the rest of what the paper prints.
    women = sum(1 for s in subs_all if demo[s]["gender"] == WOMAN)
    men = sum(1 for s in subs_all if demo[s]["gender"] == MAN)
    age = math.fsum(demo[s]["age"] for s in subs_all) / N
    first = {o: sum(1 for s in subs_all if task[s]["order"] == o) for o in ORDERS}
    trials = [t for s in subs_all for t in task[s]["trials"].values()]
    acc_pre = 100 * sum(t[0] for t in trials) / len(trials)
    differ = 100 * sum(1 for t in trials if t[0] != t[1]) / len(trials)
    acc_post = 100 * sum(t[3] for t in trials) / len(trials)
    acc_adv = 100 * sum(t[1] for t in trials) / len(trials)
    mean_rate = math.fsum(rates.values()) / len(rates)
    pre = [sum(t[0] for t in task[s]["trials"].values()) / TRIALS for s in subs_all]
    post = [sum(t[3] for t in task[s]["trials"].values()) / TRIALS for s in subs_all]
    acc_t = paired(pre, post)

    trust = {k: pearson([rates[s] for s in subs], [demo[s][k] for s in subs]) for k in ("trust1", "trust2")}
    trust_bf = {k: bayes(v["n"], v["r"]) for k, v in trust.items()}

    ratings = [traits[s][CONSC] for s in subs_all if traits[s].get(CONSC) is not None]
    ones = sum(1 for v in ratings if v == 1)
    order_t = welch([traits[s][CONSC] for s in subs_all if task[s]["order"] == "traits_task"
                     and traits[s].get(CONSC) is not None],
                    [traits[s][CONSC] for s in subs_all if task[s]["order"] == "task_traits"
                     and traits[s].get(CONSC) is not None])

    above = [s for s in tested if consc[s] > 1]
    ex_p = pearson([rates[s] for s in above], [consc[s] for s in above])
    ex_s = spearman([rates[s] for s in above], [consc[s] for s in above])
    ex_bf = bayes(ex_p["n"], ex_p["r"])
    quad = lm(y_corr, list(poly(x_corr, 2).T))

    c_trust = {k: pearson([traits[s][CONSC] for s in subs_all if traits[s].get(CONSC) is not None],
                          [demo[s][k] for s in subs_all if traits[s].get(CONSC) is not None])
               for k in ("trust1", "trust2")}
    c_trust_bf = {k: bayes(v["n"], v["r"]) for k, v in c_trust.items()}

    # The PCA as the code has it: data_ms[, 1:21] is sub_n and the 20 traits (spread's columns, in sorted order).
    twenty = sorted(TRAIT_EXP + TRAIT_INT)
    rows_ms = [s for s in subs_all if any(t in traits[s] for t in twenty)]
    X = [[float(s)] + [math.nan if traits[s].get(t) is None else float(traits[s][t]) for t in twenty]
         for s in rows_ms]
    with_sub, imputed = pca_shares(X)
    without_sub, _ = pca_shares([row[1:] for row in X])

    e_reg, i_reg = [E[s] for s in reg], [I[s] for s in reg]
    dims_t = paired(e_reg, i_reg)

    # The usage regressions run on the second data_ms, whose rows are the participants with an advice rate and a row
    # for any of the 20 traits (lm then leaves out a row missing the response or a usage).
    ms_rows = [s for s in subs if any(t in traits[s] for t in TRAIT_EXP + TRAIT_INT)]
    usage_rows = {}
    for what, y in (("consc", lambda s: consc[s]), ("adv", lambda s: rates[s])):
        keep = [s for s in ms_rows if y(s) is not None and all(v is not None for v in demo[s]["often"])]
        usage_rows[what] = lm([y(s) for s in keep], [[demo[s]["often"][j] for s in keep] for j in range(3)])
    usage_desc = []
    for j in range(3):
        v = [demo[s]["often"][j] for s in subs_all if demo[s]["often"][j] is not None]
        usage_desc.append((median(v), math.fsum(v) / len(v), float(np.std(v, ddof=1))))

    printed = []

    def put(what, computed, wanted):
        printed.append((what, computed, wanted))

    put("N", str(N), "410")
    put("women, men, others", f"{women}, {men}, {N - women - men}", "204, 199, 7")
    put("mean age", fmt(age), "47.19")
    put("task first, ratings first", f"{first['task_traits']}, {first['traits_task']}", "209, 201")
    put("accuracy before advice, %", fmt(acc_pre), "62.70")
    put("trials whose advice differed, %", fmt(differ), "38.57")
    put("advice taken, mean %", fmt(mean_rate), "58.30")
    put("accuracy after advice, %", fmt(acc_post), "63.08")
    put("advice accuracy, %", fmt(acc_adv), "62.48")
    put("accuracy before against after, t(409)", f"t({acc_t['df']}) {fmt(acc_t['t'])}", "t(409) -0.84")
    put("its p", fp(acc_t["p"]), "0.404")
    put("its mean difference", fmt(acc_t["mean"]), "-0.00")
    put("its CI", f"{fmt(acc_t['ci'][0])}, {fmt(acc_t['ci'][1])}", "-0.01, 0.01")
    put("its Cohen's d", fmt(acc_t["d"]), "0.04")
    for k, r_, ci_, bf_ in (("trust1", "0.58", "0.51, 0.64", "1.38e+35"), ("trust2", "0.41", "0.32, 0.49", "7.52e+14")):
        put(f"advice-taking with {k}, r({trust[k]['df']})", f"r({trust[k]['df']}) {fmt(trust[k]['r'])}",
            f"r(408) {r_}")
        put(f"its p ({k})", fp(trust[k]["p"]), "< 0.001")
        put(f"its CI ({k})", f"{fmt(trust[k]['ci'][0])}, {fmt(trust[k]['ci'][1])}", ci_)
        put(f"its BF10 ({k})", f"{trust_bf[k]['bf10']:.2e}", bf_)
    put("rating 1", str(ones), "175")
    put("rating 1, % of participants", fmt(100 * ones / N), "42.68")
    put("consciousness mean", fmt(math.fsum(ratings) / len(ratings)), "21.51")
    put("consciousness median", f"{median(ratings):g}", "6")
    put("consciousness SD", fmt(float(np.std(ratings, ddof=1))), "27.71")
    put("consciousness range", f"{min(ratings)}-{max(ratings)}", "1-100")
    put("task first: consciousness mean, SD", f"{fmt(order_t['mb'])}, {fmt(order_t['sb'])}", "24.18, 29.35")
    put("ratings first: consciousness mean, SD", f"{fmt(order_t['ma'])}, {fmt(order_t['sa'])}", "18.71, 25.67")
    put("orders' Welch t", f"t({order_t['df']:.0f}) {fmt(order_t['t'])}", "t(404) -2.01")
    put("its p (orders)", fp(order_t["p"]), "0.045")
    put("its CI (orders)", f"{fmt(order_t['ci'][0])}, {fmt(order_t['ci'][1])}", "-10.83, -0.12")
    put("its Cohen's d (orders)", fmt(order_t["d"]), "0.20")
    put("advice-taking with consciousness, Pearson", f"r({pr['df']}) {fmt(pr['r'])}", "r(407) -0.10")
    put("its p", fp(pr["p"]), "0.043")
    put("its CI", f"{fmt(pr['ci'][0])}, {fmt(pr['ci'][1])}", "-0.20, -0.00")
    put("Spearman's rho", fmt(sp["rho"]), "-0.07")
    put("its p (Spearman)", fp(sp["p"]), "0.141")
    put("BF10", fmt(bf["bf10"]), "0.47")
    put("BF+0", fmt(bf["plus"]), "0.02")
    put("JASP: n, r", f"{pr['n']}, {fmt(pr['r'], 3)}", "409, -0.100")
    put("JASP: BF10", fmt(bf["bf10"], 3), "0.474")
    put("JASP: BF+0", fmt(bf["plus"], 3), "0.021")
    put("above 1: Pearson", f"r({ex_p['df']}) {fmt(ex_p['r'])}", "r(232) -0.14")
    put("its p (above 1)", fp(ex_p["p"]), "0.028")
    put("its CI (above 1)", f"{fmt(ex_p['ci'][0])}, {fmt(ex_p['ci'][1])}", "-0.27, -0.02")
    put("above 1: Spearman's rho, p", f"{fmt(ex_s['rho'])}, {fp(ex_s['p'])}", "-0.14, 0.027")
    put("above 1: BF10", fmt(ex_bf["bf10"]), "0.90")
    put("JASP: above 1, BF10", fmt(ex_bf["bf10"], 3), "0.898")
    for i, (name, want) in enumerate((("linear", ("-71.93", "35.52", "-2.03", "0.044", "-141.75, -2.11")),
                                      ("quadratic", ("-12.20", "35.52", "-0.34", "0.731", "-82.02, 57.62"))), 1):
        got = term(quad, i)
        for lab, g_, w_ in zip(("B", "SE", "t", "p", "CI"), got, want):
            put(f"poly(consc, 2), {name} {lab}" + (f" (t({quad['df']}))" if lab == "t" else ""), g_, w_)
    for k, r_, p_, ci_, bf_ in (("trust1", "0.11", "0.023", "0.02, 0.21", "0.83"),
                                ("trust2", "0.25", "< 0.001", "0.16, 0.34", "43808.62")):
        put(f"consciousness with {k}", f"r({c_trust[k]['df']}) {fmt(c_trust[k]['r'])}", f"r(407) {r_}")
        put(f"its p (consciousness, {k})", fp(c_trust[k]["p"]), p_)
        put(f"its CI (consciousness, {k})", f"{fmt(c_trust[k]['ci'][0])}, {fmt(c_trust[k]['ci'][1])}", ci_)
        put(f"its BF10 (consciousness, {k})", fmt(c_trust_bf[k]["bf10"]), bf_)
    put("PCA, two components' shares of variance, %", f"{fmt(with_sub[0])}, {fmt(with_sub[1])}", "45.30, 18.79")
    put("intelligence mean, SD", f"{fmt(math.fsum(i_reg) / len(i_reg))}, {fmt(float(np.std(i_reg, ddof=1)))}",
        "59.39, 24.99")
    put("experience mean, SD", f"{fmt(math.fsum(e_reg) / len(e_reg))}, {fmt(float(np.std(e_reg, ddof=1)))}",
        "12.25, 19.06")
    put("experience against intelligence, paired t", f"t({dims_t['df']}) {fmt(dims_t['t'])}", "t(409) -39.28")
    put("its mean difference (dimensions)", fmt(dims_t["mean"]), "-47.14")
    put("its CI (dimensions)", f"{fmt(dims_t['ci'][0])}, {fmt(dims_t['ci'][1])}", "-49.50, -44.78")
    put("its Cohen's d (dimensions)", fmt(dims_t["d"]), "1.94")
    for fit, label, want in (
            (consc_fit, "consciousness", (("1.48", "0.29", "5.13", "< 0.001", "0.91, 2.05"),
                                          ("0.16", "0.04", "3.65", "< 0.001", "0.08, 0.25"),
                                          ("-0.01", "0.00", "-1.93", "0.054", "-0.01, 0.00"))),
            (adv_fit, "advice-taking", (("-1.04", "0.51", "-2.04", "0.042", "-2.04, -0.04"),
                                        ("0.31", "0.08", "3.92", "< 0.001", "0.15, 0.46"),
                                        ("0.01", "0.01", "1.37", "0.171", "0.00, 0.02")))):
        for i, (name, w) in enumerate(zip(("experience", "intelligence", "interaction"), want), 1):
            for lab, g_, w_ in zip(("B", "SE", "t", "p", "CI"), term(fit, i), w):
                put(f"{label} on {name}, {lab}" + (f" (t({fit['df']}))" if lab == "t" else ""), g_, w_)
    for what, want in (("consc", (("-0.02", "0.64", "-0.03"), ("0.30", "0.67", "0.45"), ("4.50", "0.64", "7.01"))),
                       ("adv", (("2.98", "0.87", "3.43"), ("0.65", "0.91", "0.71"), ("-2.33", "0.87", "-2.66")))):
        fit = usage_rows[what]
        for j, (u, w) in enumerate(zip(USAGE, want), 1):
            for lab, g_, w_ in zip(("B", "SE", "t"), term(fit, j)[:3], w):
                put(f"{what} on {u}, {lab}" + (f" (t({fit['df']}))" if lab == "t" else ""), g_, w_)
    for u, (md, mn, sd), want in zip(USAGE, usage_desc, ("6, 4.75, 2.36", "5, 3.91, 2.43", "0, 1.68, 2.31")):
        put(f"{u}: median, mean, SD", f"{md:g}, {fmt(mn)}, {fmt(sd)}", want)

    matched = [w for w, c, p in printed if c == p]
    differs = [{"what": w, "computed": c, "printed": p, "sign_only": sign_only(c, p)}
               for w, c, p in printed if c != p]
    signs = [x["what"] for x in differs if x["sign_only"]]
    others = [f"{x['what']} {x['computed']} (printed {x['printed']})" for x in differs if not x["sign_only"]]

    # Rule 7: controls.
    every_bf = [("tested", bf)] + [(f"advice-{k}", v) for k, v in trust_bf.items()] + [
        ("above 1", ex_bf)] + [(f"consciousness-{k}", v) for k, v in c_trust_bf.items()]
    closed = {name: bayes_closed(v["n"], v["r"]) for name, v in every_bf}
    worst_bf = max(rel(v[k], closed[name][k]) for name, v in every_bf for k in ("plus", "minus", "bf10"))
    grid = [max(-0.99, min(0.99, pr["r"] + 2 * k / math.sqrt(pr["n"]))) for k in range(-4, 5)]
    worst_h = max(rel(h_ratio(pr["n"], pr["r"], q), ly_ab(pr["n"], pr["r"], q)) for q in grid)
    worst_ols = 0.0
    for fit in (adv_fit, consc_fit):
        y = [rates[s] for s in reg] if fit is adv_fit else [consc[s] for s in creg]
        c2, s2, p2 = lm_statsmodels(y, fit["A"])
        for a_, b_ in zip(fit["coef"] + fit["se"] + fit["p"], c2 + s2 + p2):
            worst_ols = max(worst_ols, rel(a_, b_) if abs(b_) > 1e-12 else abs(a_ - b_))
    worst_r = rel(pr["r"], float(stats.pearsonr(y_corr, x_corr)[0]))
    n_differed, bad_trials = reading_check(task)
    sh = shuffles(seed, y_corr, x_corr, pr["r"], [rates[s] for s in reg], adv_fit["A"])
    controls = {
        "every Bayes factor by quadrature agrees with the closed forms (relative 1e-8)": worst_bf < 1e-8,
        "h agrees with Ly et al.'s A + B at nine values of rho (relative 1e-12)": worst_h < 1e-12,
        "both regressions agree with statsmodels and r with scipy (relative 1e-8)": (worst_ols < 1e-8
                                                                                     and worst_r < 1e-8),
        "on every trial whose advice differed, acc_post follows acc, adv_acc and the answer": bad_trials == 0,
        "shuffles recover the null (p within 0.02; p < 0.001 at most 1%; p < 0.05 in 2% to 9%)": (
            abs(sh["p_perm"] - pr["p"]) <= 0.02 and sh["int_below"] <= 0.01 * sh["n"]
            and 0.02 * sh["n"] <= sh["exp_below"] <= 0.09 * sh["n"]),
    }

    t3 = term(adv_fit, 1), term(adv_fit, 2), term(adv_fit, 3)
    c3 = term(consc_fit, 1), term(consc_fit, 2), term(consc_fit, 3)
    values = {
        "sample": (f"{N} participants ({women} women, {men} men, {N - women - men} others; mean age {fmt(age)}); "
                   f"{len(trials)} trials, {TRIALS} each; {len(rates)} with an advice rate ({len(no_rate)} without), "
                   f"{len(tested)} also with a consciousness rating"),
        "task": (f"accuracy {fmt(acc_pre)}% before advice, {fmt(acc_post)}% after; advice differed on {fmt(differ)}% "
                 f"of trials and was taken on {fmt(mean_rate)}% (mean of participants); advice accuracy "
                 f"{fmt(acc_adv)}%"),
        "advice_trust": (f"advice-taking with trust on the task r {fmt(trust['trust1']['r'], 3)} (BF10 "
                         f"{trust_bf['trust1']['bf10']:.3e}), in general r {fmt(trust['trust2']['r'], 3)} (BF10 "
                         f"{trust_bf['trust2']['bf10']:.3e})"),
        "consciousness": (f"{ones} of {N} rate ChatGPT 1 ({fmt(100 * ones / N)}%); mean "
                          f"{fmt(math.fsum(ratings) / len(ratings))}, median {median(ratings):g}, SD "
                          f"{fmt(float(np.std(ratings, ddof=1)))}, range {min(ratings)}-{max(ratings)}; "
                          f"{N - len(ratings)} missing"),
        "correlation": (f"advice-taking with consciousness: Pearson r({pr['df']}) {pr['r']:.4f}, p {pr['p']:.4f}, "
                        f"CI {fmt(pr['ci'][0], 3)} to {fmt(pr['ci'][1], 3)}; Spearman's rho {sp['rho']:.4f}, p "
                        f"{sp['p']:.4f}"),
        "r_consc": round(pr["r"], 6),
        "bayes": (f"BF+0 {bf['plus']:.6g}, BF-0 {bf['minus']:.6g}, BF10 {bf['bf10']:.6g} (n {pr['n']}, r "
                  f"{pr['r']:.4f}; uniform prior, exact likelihood)"),
        "bf_plus": float(f"{bf['plus']:.6g}"),
        "bf10": float(f"{bf['bf10']:.6g}"),
        "excluding_1s": (f"{ex_p['n']} rating above 1: r({ex_p['df']}) {ex_p['r']:.4f}, p {ex_p['p']:.4f}; rho "
                         f"{ex_s['rho']:.4f}, p {ex_s['p']:.4f}; BF10 {ex_bf['bf10']:.4g}"),
        "polynomial": (f"lm(adv_rate ~ poly(consc, 2)): linear B {fmt(quad['coef'][1])} (t({quad['df']}) "
                       f"{fmt(quad['t'][1])}, p {quad['p'][1]:.4f}), quadratic B {fmt(quad['coef'][2])} (t "
                       f"{fmt(quad['t'][2])}, p {quad['p'][2]:.4f})"),
        "consc_trust": (f"consciousness with trust on the task r {fmt(c_trust['trust1']['r'], 3)} (BF10 "
                        f"{c_trust_bf['trust1']['bf10']:.4g}), in general r {fmt(c_trust['trust2']['r'], 3)} (BF10 "
                        f"{c_trust_bf['trust2']['bf10']:.8g})"),
        "dimensions": (f"experience mean {fmt(math.fsum(e_reg) / len(e_reg))} (SD "
                       f"{fmt(float(np.std(e_reg, ddof=1)))}), intelligence {fmt(math.fsum(i_reg) / len(i_reg))} (SD "
                       f"{fmt(float(np.std(i_reg, ddof=1)))}); paired t({dims_t['df']}) {fmt(dims_t['t'])}; n "
                       f"{len(reg)}"),
        "pca": (f"with sub_n among the variables, as the code has it: {fmt(with_sub[0])}% and {fmt(with_sub[1])}%; "
                f"the 20 traits alone: {fmt(without_sub[0])}% and {fmt(without_sub[1])}%; {imputed} imputed"),
        "advice_regression": (f"n {adv_fit['n']}: experience B {t3[0][0]} (SE {t3[0][1]}, t({adv_fit['df']}) "
                              f"{t3[0][2]}, p {adv_fit['p'][1]:.4f}); intelligence B {t3[1][0]} (SE {t3[1][1]}, t "
                              f"{t3[1][2]}, p {adv_fit['p'][2]:.2e}); product B {t3[2][0]} (t {t3[2][2]}, p "
                              f"{t3[2][3]})"),
        "b_experience": round(b_e, 6),
        "p_experience": float(f"{p_e:.6g}"),
        "b_intelligence": round(b_i, 6),
        "p_intelligence": float(f"{p_i:.6g}"),
        "consc_regression": (f"n {consc_fit['n']}: experience B {c3[0][0]} (t({consc_fit['df']}) {c3[0][2]}), "
                             f"intelligence B {c3[1][0]} (t {c3[1][2]}), product B {c3[2][0]} (t {c3[2][2]}, p "
                             f"{c3[2][3]})"),
        "usage": ("on assistants, chatbots, social AI: consciousness B " + ", ".join(
            fmt(v) for v in usage_rows["consc"]["coef"][1:]) + f" (n {usage_rows['consc']['n']}); advice-taking B "
                  + ", ".join(fmt(v) for v in usage_rows["adv"]["coef"][1:]) + f" (n {usage_rows['adv']['n']})"),
        "printed_values": (f"{len(matched)} of {len(printed)} as printed"
                           + (f"; {len(signs)} differ only in sign: " + ", ".join(signs) if signs else "")
                           + ("; not: " + ", ".join(others) if others else ""))[:LIMIT],
        "shuffles": (f"{sh['n']} shuffles: |r| as large in {sh['p_perm']:.4f} (t test p {pr['p']:.4f}); intelligence "
                     f"p < 0.001 in {sh['int_below']}, experience p < 0.05 in {sh['exp_below']}"),
        "conditions_met": sum(cond.values()), "conditions_total": len(cond), "test_passed": int(all(cond.values())),
        "controls_passed": sum(controls.values()), "controls_total": len(controls),
    }
    out = {k: values[k] for k in OUTPUTS}
    for k, v in out.items():
        if isinstance(v, str) and len(v) > LIMIT:
            raise AssertionError(f"{k}: longer than {LIMIT} characters: {v}")
    detail = {
        "conditions": cond, "controls": controls,
        "no_rate": no_rate, "pearson": pr, "spearman": sp, "bayes": bf, "closed": closed,
        "worst": {"bf": worst_bf, "h": worst_h, "ols": worst_ols, "r": worst_r},
        "reading": {"trials_differed": n_differed, "inconsistent": bad_trials},
        "advice_fit": {k: v for k, v in adv_fit.items() if k != "A"},
        "consc_fit": {k: v for k, v in consc_fit.items() if k != "A"},
        "usage_fits": {w: {k: v for k, v in f.items() if k != "A"} for w, f in usage_rows.items()},
        "polynomial": {k: v for k, v in quad.items() if k != "A"},
        "pca": {"with_sub_n": with_sub, "without": without_sub, "imputed": imputed},
        "shuffles": sh, "trust": trust, "trust_bf": trust_bf, "consc_trust": c_trust, "consc_trust_bf": c_trust_bf,
        "excluding_1s": {"pearson": ex_p, "spearman": ex_s, "bayes": ex_bf}, "orders": order_t,
        "accuracy_t": acc_t, "dimensions_t": dims_t,
        "printed": [{"what": w, "computed": c, "printed": p} for w, c, p in printed], "differs": differs,
    }
    return out, detail


def run(seed, inputs="inputs", results="results"):
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        raise Refused("the seed must be 64 hex characters")
    raw = {k: read_bytes(os.path.join(inputs, name), sha) for k, (name, sha) in INPUTS.items()}
    text = {k: v.decode("utf-8-sig") for k, v in raw.items()}
    read_code(text["code"])
    out, detail = assess(read_task(text["task"]), read_traits(text["traits"]), read_demo(text["demo"]), seed)
    detail["inputs"] = {k: {"name": n, "sha256": s} for k, (n, s) in INPUTS.items()}
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
        sys.exit(f"cbf2025: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
