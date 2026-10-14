"""Folk attributions of consciousness to ChatGPT, recomputed from the released survey by the authors' own analyses.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:adb1673906083222) is from Colombatto and
Fleming, "Folk psychological attributions of consciousness to large language models", Neuroscience of Consciousness
2024(1), niae013: "We surveyed a sample of US residents (n = 300) and found that a majority of participants were
willing to attribute some possibility of phenomenal consciousness to large language models. These attributions were
robust, as they predicted attributions of mental states typically associated with phenomenality--but also flexible,
as they were sensitive to individual differences such as usage frequency."

Its registered test: refuted if, on the released data (OSF 49w7m Data.csv: 300 US adults rating ChatGPT from 1,
clearly not an experiencer, to 100), 150 or fewer rate it above 1; or the least-squares slope of the rating on ChatGPT
use, coded 1 (never) to 6 (more than once a day) as the authors' code codes it, is not positive at two-sided p < 0.05;
or the rating's correlation with participants' scores on the first principal component of the 65 standardised
mental-state ratings (the paper's experience dimension, most states loading positively) is not positive at two-sided
p < 0.05.

The input is the authors' Data.csv from their OSF project (49w7m), checked against its SHA-256 and read as data (the
csv module; nothing in it is run). Their Analysis.Rmd, beside it on OSF, is the method followed; it is not run either
(no R here), and each step below names the line of it that it reimplements. Every rule was fixed before any statistic
was computed. The seed draws only the bootstrap beside the test.

1. The file. 300 rows and 76 columns: sub_n, pheno (the rating, an integer from 1 to 100), pheno_rt, pheno_conf and
   pheno_pred (integers from 1 to 100), know_yn (Yes or No), use_yn (Yes, No or empty), use_often (one of the survey's
   five frequencies, or empty), use_purpose, age (a number or NA), gender, then the 65 mental-state ratings that the
   authors' code takes as df[, 12:76] (numbers from 1 to 100, or NA). sub_n must be 1 to 300 in order, since the
   code's merge of the PCA's coordinates (pca$ind$coord, named by row) onto df is by sub_n. Anything else is refused.
2. The first condition: the number of participants whose rating is above 1 (the code's "Low ratings" counts
   pheno == 1); more than 150 of the 300.
3. Usage, as the code recodes it: "Never" when use_yn is not "Yes", otherwise use_often, the levels Never, about once
   a month, about once every two weeks, about once a week, about once a day and more than once a day numbered 1 to 6
   (as.numeric of the factor). A "Yes" with no frequency would be NA and left out of the regression, as lm leaves it;
   their number is reported. The second condition: the ordinary least-squares slope of the rating on that number
   (lm(pheno ~ as.numeric(use_often_rec))) is positive with a two-sided p below 0.05 by its t statistic.
4. The mental states, as FactoMineR's PCA(df[, 12:76], scale.unit = TRUE) computes them: a missing rating replaced by
   that state's mean over the participants who gave one (FactoMineR's rule for missing values), every state centred
   and divided by its standard deviation with weights 1/n, the components the eigenvectors of the resulting
   correlation matrix in decreasing order of eigenvalue, a state's loading its correlation with a component
   (pca$var$coord) and a participant's score the projection of their standardised ratings (pca$ind$coord). A
   component's sign is arbitrary in any implementation; the first is oriented so that most of the 65 states load
   positively on it (the paper's experience dimension, its Dim.1). The third condition: the Pearson correlation of
   the rating with the scores on that component (cor.test(df$pheno, df$Dim.1)) is positive with a two-sided p below
   0.05 (t = r sqrt((n - 2)/(1 - r^2)) on n - 2 degrees of freedom). test_passed is 1 if all three hold.
5. Beside the test, every other number the paper prints from these data, each recomputed as its line of the code
   computes it and compared at the precision printed: the sample (N, gender counts, mean age); the share rating 1 and
   the rating's mean, median, standard deviation and range; the quadratic regression of the rating on confidence
   (lm(pheno ~ poly(pheno_conf, 2)), R's orthogonal polynomials, and the anova F against the linear fit); the shares
   who knew of and had used ChatGPT, and the Welch t test of users against non-users; the usage regression's
   coefficient, standard error, t and interval; the share of variance in the first two components; the correlation
   across the 65 states between their loadings and their mean attribution; the correlations of the rating with the
   two components' scores; and the predictions of others' ratings (mean, median, standard deviation, their
   correlation with the rating, and the paired t test). The second component's sign is arbitrary and the paper does
   not fix it, so its two correlations are compared in absolute value. Also beside it: 95% intervals for the three
   tested quantities from 2,000 resamples of the participants drawn from ECDYSIS_SEED (the PCA, its imputation and
   its orientation redone in each).
6. Controls, known answers: the least-squares fit recovers an exact line and its p value function gives 0.05 at
   t = 2.228 on 10 degrees of freedom; the PCA recovers the first component of two correlated variables (eigenvalue
   1 + rho, equal loadings); R's poly basis is orthonormal, orthogonal to the constant and leads positively; and the
   Welch test gives the textbook value for two samples of three.

After the trial (under a seed of Imago's own, before any was issued), one change beside the test, to how a printed
value that differs is reported: each is now marked when it differs only in its sign. The trial reproduced 35 of the 38
printed values; the other three, the quadratic term's coefficient, t and interval, came out as the authors' own
knitted output (Analysis.html on OSF) has them, -178.25, -7.297 and -226.33 to -130.18, where the paper prints them
without the minus sign. The test's conditions, its data and its rules did not change.

What it cannot check: the survey itself (who took it, how they understood the questions), and whether its 300
participants stand for US residents, which the paper does not claim beyond its quota sampling.

Writes results/outputs.json (the values a receipt carries) and results/detail.json (every value computed).
Run with: python3 folk/colombatto.py
"""

import csv
import hashlib
import io
import json
import math
import os
import re
import sys

import numpy as np
from scipy import stats

INPUTS = {"data": ("Data.csv", "6124c4ccdd24078153740298b887136b8a0eb4ff2a10cba9fda8e22f3713c5df")}
HEAD = ("sub_n", "pheno", "pheno_rt", "pheno_conf", "pheno_pred", "know_yn", "use_yn", "use_often", "use_purpose",
        "age", "gender")
TRAITS = 65
N = 300
FREQ = {"About once a month": 2, "About once every two weeks": 3, "About once a week": 4, "About once a day": 5,
        "More than once a day": 6}
NEVER = 1
MAJORITY = 150
ALPHA = 0.05
BOOTSTRAP = 2000
OUTPUTS = ("sample", "above_1", "share_above_1", "usage", "usage_slope", "usage_p", "r_experience", "p_experience",
           "intelligence", "pca", "predictions", "users", "printed_values", "bootstrap_95ci", "conditions_met",
           "conditions_total", "test_passed", "controls_passed", "controls_total")
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


def _int(v, what, lo=1, hi=100):
    if not re.fullmatch(r"[0-9]+", v):
        raise Refused(f"{what}: {v!r} is not an integer")
    k = int(v)
    if not lo <= k <= hi:
        raise Refused(f"{what}: {k} outside {lo} to {hi}")
    return k


def _num(v, what, lo=1.0, hi=100.0):
    if v == "NA":
        return math.nan
    if not re.fullmatch(r"[0-9]+(\.[0-9]+)?", v):
        raise Refused(f"{what}: {v!r} is not a number or NA")
    x = float(v)
    if not lo <= x <= hi:
        raise Refused(f"{what}: {x} outside {lo} to {hi}")
    return x


def read_data(text):
    """Rule 1."""
    rows = list(csv.reader(io.StringIO(text)))
    if not rows:
        raise Refused("empty file")
    head, body = rows[0], [r for r in rows[1:] if r != []]
    if len(head) != len(HEAD) + TRAITS or tuple(head[:len(HEAD)]) != HEAD:
        raise Refused(f"the header is not the expected {len(HEAD) + TRAITS} columns")
    traits = head[len(HEAD):]
    if len(set(traits)) != TRAITS or any(not t for t in traits):
        raise Refused("the 65 mental states must have distinct names")
    if len(body) != N:
        raise Refused(f"{len(body)} rows, not {N}")
    d = {k: [] for k in ("sub", "pheno", "conf", "pred", "know", "use", "often", "age", "gender")}
    X = np.empty((N, TRAITS))
    for i, r in enumerate(body):
        if len(r) != len(head):
            raise Refused(f"row {i + 1}: {len(r)} fields")
        sub = _int(r[0], f"row {i + 1} sub_n", 1, N)
        if sub != i + 1:
            raise Refused(f"row {i + 1}: sub_n {sub}, not its row number")
        d["sub"].append(sub)
        d["pheno"].append(_int(r[1], f"row {i + 1} pheno"))
        d["conf"].append(_int(r[3], f"row {i + 1} pheno_conf"))
        d["pred"].append(_int(r[4], f"row {i + 1} pheno_pred"))
        if r[5] not in ("Yes", "No"):
            raise Refused(f"row {i + 1}: know_yn {r[5]!r}")
        if r[6] not in ("Yes", "No", ""):
            raise Refused(f"row {i + 1}: use_yn {r[6]!r}")
        if r[7] not in FREQ and r[7] != "":
            raise Refused(f"row {i + 1}: use_often {r[7]!r}")
        d["know"].append(r[5])
        d["use"].append(r[6])
        d["often"].append(r[7])
        d["age"].append(_num(r[9], f"row {i + 1} age", 0, 150) if r[9] not in ("", "NA") else math.nan)
        d["gender"].append(r[10])
        for j in range(TRAITS):
            X[i, j] = _num(r[len(HEAD) + j], f"row {i + 1} {traits[j]}")
    out = {k: np.array(v, dtype=float) if k in ("pheno", "conf", "pred", "age") else v for k, v in d.items()}
    out["X"] = X
    out["traits"] = traits
    return out


def usage_codes(use, often):
    """Rule 3: the code's use_often_rec as numbers; None where R would have NA."""
    codes = []
    for u, o in zip(use, often):
        if u != "Yes":
            codes.append(NEVER)
        else:
            codes.append(FREQ.get(o))
    return codes


def t_p(t, df):
    return float(2 * stats.t.sf(abs(t), df))


def ols(x, y):
    """Simple least squares with R's summary.lm and confint numbers for the slope."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    n = len(x)
    xm, ym = x.mean(), y.mean()
    sxx = float(np.sum((x - xm) ** 2))
    b = float(np.sum((x - xm) * (y - ym)) / sxx)
    a = float(ym - b * xm)
    res = y - (a + b * x)
    df = n - 2
    s2 = float(np.sum(res ** 2) / df)
    se = math.sqrt(s2 / sxx)
    t = b / se if se > 0 else math.inf
    q = float(stats.t.ppf(0.975, df))
    return {"b": b, "a": a, "se": se, "t": t, "p": t_p(t, df) if se > 0 else 0.0, "df": df, "n": n,
            "ci": (b - q * se, b + q * se)}


def pearson(x, y):
    """cor.test: r, t on n - 2 degrees of freedom, two-sided p, Fisher's z interval."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    n = len(x)
    r = float(np.corrcoef(x, y)[0, 1])
    t = r * math.sqrt((n - 2) / (1 - r * r))
    z = math.atanh(r)
    h = float(stats.norm.ppf(0.975)) / math.sqrt(n - 3)
    return {"r": r, "t": t, "p": t_p(t, n - 2), "df": n - 2, "ci": (math.tanh(z - h), math.tanh(z + h)), "n": n}


def welch(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    va, vb = a.var(ddof=1) / len(a), b.var(ddof=1) / len(b)
    t = float((a.mean() - b.mean()) / math.sqrt(va + vb))
    df = float((va + vb) ** 2 / (va ** 2 / (len(a) - 1) + vb ** 2 / (len(b) - 1)))
    return {"t": t, "df": df, "p": t_p(t, df), "ma": float(a.mean()), "mb": float(b.mean())}


def paired(a, b):
    d = np.asarray(a, float) - np.asarray(b, float)
    n = len(d)
    t = float(d.mean() / (d.std(ddof=1) / math.sqrt(n)))
    return {"t": t, "df": n - 1, "p": t_p(t, n - 1)}


def poly(x, degree=2):
    """R's poly(x, degree): the centred powers of x orthonormalised in order (Gram-Schmidt, which is what R's
    qr.qy(QR, diag(R)) scaled to unit norm gives), each with a positive coefficient on its highest power."""
    x = np.asarray(x, float)
    xc = x - x.mean()
    cols = [np.ones_like(xc)]
    out = []
    for k in range(1, degree + 1):
        v = xc ** k
        for c in cols:
            v = v - (v @ c) / (c @ c) * c
        cols.append(v)
        out.append(v / math.sqrt(v @ v))
    return np.column_stack(out)


def lm(y, Z):
    """lm(y ~ Z): coefficients (intercept first), standard errors, residual sum of squares, residual df."""
    y = np.asarray(y, float)
    A = np.column_stack([np.ones(len(y)), Z])
    coef, *_ = np.linalg.lstsq(A, y, rcond=None)
    res = y - A @ coef
    df = len(y) - A.shape[1]
    rss = float(res @ res)
    cov = rss / df * np.linalg.inv(A.T @ A)
    return coef, np.sqrt(np.diag(cov)), rss, df


def quadratic(y, x):
    """lm(pheno ~ poly(pheno_conf, 2)), its confint for the quadratic term, and anova against the linear model."""
    Z = poly(x, 2)
    c2, se2, rss2, df2 = lm(y, Z)
    _, _, rss1, _ = lm(y, Z[:, :1])
    t = float(c2[2] / se2[2])
    q = float(stats.t.ppf(0.975, df2))
    F = (rss1 - rss2) / (rss2 / df2)
    return {"b": float(c2[2]), "se": float(se2[2]), "t": t, "p": t_p(t, df2), "df": df2,
            "ci": (float(c2[2] - q * se2[2]), float(c2[2] + q * se2[2])), "F": float(F),
            "F_p": float(stats.f.sf(F, 1, df2))}


def pca(X):
    """Rule 4: FactoMineR's PCA with scale.unit = TRUE and mean imputation; the first component oriented so that most
    states load positively; the second as the eigenvector comes."""
    X = np.array(X, float)
    means = np.nanmean(X, axis=0)
    miss = np.isnan(X)
    X[miss] = np.take(means, np.nonzero(miss)[1])
    mu = X.mean(axis=0)
    sd = np.sqrt(((X - mu) ** 2).mean(axis=0))
    if np.any(sd == 0):
        raise Refused("a mental state with no variance cannot be standardised")
    Z = (X - mu) / sd
    R = Z.T @ Z / len(Z)
    lam, V = np.linalg.eigh(R)
    order = np.argsort(lam)[::-1]
    lam, V = lam[order], V[:, order]
    load = V * np.sqrt(np.maximum(lam, 0))
    if np.sum(load[:, 0] > 0) < np.sum(load[:, 0] < 0):
        V[:, 0], load[:, 0] = -V[:, 0], -load[:, 0]
    scores = Z @ V[:, :2]
    return {"eig": lam, "load": load[:, :2], "scores": scores, "missing": int(miss.sum())}


def tests(d, P=None):
    """The three conditions' quantities (rules 2 to 4)."""
    above = int(np.sum(d["pheno"] > 1))
    codes = usage_codes(d["use"], d["often"])
    keep = [i for i, c in enumerate(codes) if c is not None]
    use = ols([codes[i] for i in keep], d["pheno"][keep])
    use["dropped"] = len(codes) - len(keep)
    P = P if P is not None else pca(d["X"])
    exp = pearson(d["pheno"], P["scores"][:, 0])
    return above, use, exp, P


def generator(seed, label):
    return np.random.Generator(np.random.PCG64(int.from_bytes(
        hashlib.sha256(bytes.fromhex(seed) + b"|" + label.encode("ascii")).digest(), "big")))


def bootstrap(seed, d, n=BOOTSTRAP):
    """Rule 5: participants resampled with replacement; the three tested quantities recomputed in each."""
    g = generator(seed, "colombatto/bootstrap")
    share, slope, r = [], [], []
    for _ in range(n):
        idx = g.integers(0, N, N)
        dd = {"pheno": d["pheno"][idx], "use": [d["use"][i] for i in idx], "often": [d["often"][i] for i in idx],
              "X": d["X"][idx]}
        above, use, exp, _ = tests(dd)
        share.append(above / N)
        slope.append(use["b"])
        r.append(exp["r"])

    def ci(v):
        return float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))
    return {"share": ci(share), "slope": ci(slope), "r": ci(r), "n": n}


def controls_known():
    """Rule 6."""
    x = np.arange(10.0)
    f = ols(x, 2 + 3 * x)
    line_ok = abs(f["b"] - 3) < 1e-12 and abs(f["a"] - 2) < 1e-12 and abs(t_p(2.228138851986, 10) - 0.05) < 1e-9
    rho = 0.6
    L = np.linalg.cholesky(np.array([[1, rho], [rho, 1]]))
    g = np.random.Generator(np.random.PCG64(7))
    Y = g.standard_normal((20000, 2)) @ L.T
    P = pca(Y)
    pca_ok = (abs(P["eig"][0] - (1 + np.corrcoef(Y.T)[0, 1])) < 1e-9
              and abs(P["load"][0, 0] - P["load"][1, 0]) < 1e-9 and P["load"][0, 0] > 0
              and abs(P["eig"][0] - 1.6) < 0.03)
    xs = np.array([1.0, 2, 2, 5, 7, 9, 10])
    Zp = poly(xs, 2)
    poly_ok = (np.allclose(Zp.T @ Zp, np.eye(2)) and np.allclose(Zp.sum(axis=0), 0)
               and np.polyfit(xs, Zp[:, 1], 2)[0] > 0 and np.polyfit(xs, Zp[:, 0], 1)[0] > 0)
    w = welch([1, 2, 3], [4, 5, 6])
    welch_ok = abs(w["t"] + 3 / math.sqrt(2 / 3)) < 1e-12 and abs(w["df"] - 4) < 1e-12 and abs(
        w["p"] - 2 * stats.t.sf(3 / math.sqrt(2 / 3), 4)) < 1e-15
    return {"least squares and its p values give known answers": bool(line_ok),
            "the PCA recovers two correlated variables' first component": bool(pca_ok),
            "R's poly basis is orthonormal, centred and leads positively": bool(poly_ok),
            "the Welch test gives the textbook answer": bool(welch_ok)}


def fmt(v, k=2):
    return f"{v:.{k}f}"


def run(seed, inputs="inputs", results="results"):
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        raise Refused("the seed must be 64 hex characters")
    raw = {k: read_bytes(os.path.join(inputs, name), sha) for k, (name, sha) in INPUTS.items()}
    d = read_data(raw["data"].decode("utf-8-sig"))

    above, use, exp, P = tests(d)
    cond = {
        f"more than {MAJORITY} of the {N} rate ChatGPT above 1": above > MAJORITY,
        "the rating rises with usage (slope > 0, p < 0.05)": use["b"] > 0 and use["p"] < ALPHA,
        "the rating correlates with the experience component (r > 0, p < 0.05)": exp["r"] > 0 and exp["p"] < ALPHA,
    }

    pheno, pred = d["pheno"], d["pred"]
    gender = {g: d["gender"].count(g) for g in sorted(set(d["gender"]))}
    age = float(np.nanmean(d["age"]))
    quad = quadratic(pheno, d["conf"])
    users = welch(pheno[[i for i, u in enumerate(d["use"]) if u == "Yes"]],
                  pheno[[i for i, u in enumerate(d["use"]) if u == "No"]])
    intel = pearson(pheno, P["scores"][:, 1])
    item_means = np.nanmean(d["X"], axis=0)
    load_exp = pearson(P["load"][:, 0], item_means)
    load_int = pearson(P["load"][:, 1], item_means)
    preds = pearson(pheno, pred)
    pt = paired(pheno, pred)
    two = float(100 * (P["eig"][0] + P["eig"][1]) / TRAITS)
    know = 100 * d["know"].count("Yes") / N
    used = 100 * d["use"].count("Yes") / N

    printed = [  # (what, computed, printed) at the precision the paper prints
        ("N", str(N), "300"),
        ("female, male, non-binary, not saying", ", ".join(str(gender.get(k, 0)) for k in (
            "Female", "Male", "Non-binary / third gender", "Prefer not to say")), "152, 142, 2, 4"),
        ("mean age", fmt(age), "46.13"),
        ("share rating 1, %", f"{int(round(float(100 * np.sum(pheno == 1) / N)))}", "33"),
        ("share above 1, %", f"{int(round(100 * above / N))}", "67"),
        ("rating mean", fmt(pheno.mean()), "25.56"),
        ("rating median", fmt(float(np.median(pheno))), "16.00"),
        ("rating SD", fmt(pheno.std(ddof=1)), "27.36"),
        ("rating range", f"{pheno.min():.0f}-{pheno.max():.0f}", "1-100"),
        ("quadratic B", fmt(quad["b"]), "178.25"),
        ("quadratic SE", fmt(quad["se"]), "24.43"),
        ("quadratic t", fmt(quad["t"]), "7.30"),
        ("quadratic CI", f"{fmt(quad['ci'][0])}, {fmt(quad['ci'][1])}", "130.18, 226.33"),
        ("quadratic against linear, F(1, 297)", fmt(quad["F"]), "53.24"),
        ("heard of ChatGPT, %", f"{int(round(know))}", "97"),
        ("used ChatGPT, %", f"{int(round(used))}", "57"),
        ("users' mean", fmt(users["ma"]), "29.59"),
        ("non-users' mean", fmt(users["mb"]), "19.37"),
        ("users against non-users, t", fmt(users["t"]), "3.33"),
        ("users against non-users, df", f"{int(users['df'])}", "287"),
        ("usage B", fmt(use["b"]), "4.94"),
        ("usage SE", fmt(use["se"]), "0.99"),
        ("usage t", fmt(use["t"]), "4.99"),
        ("usage CI", f"{fmt(use['ci'][0])}, {fmt(use['ci'][1])}", "2.99, 6.88"),
        ("two components' share of variance, %", f"{int(round(two))}", "58"),
        ("loadings on experience against mean attribution, r", fmt(load_exp["r"]), "-0.94"),
        ("its CI", f"{fmt(load_exp['ci'][0])}, {fmt(load_exp['ci'][1])}", "-0.96, -0.91"),
        ("loadings on intelligence against mean attribution, |r|", fmt(abs(load_int["r"])), "0.95"),
        ("rating against experience scores, r", fmt(exp["r"]), "0.65"),
        ("its CI", f"{fmt(exp['ci'][0])}, {fmt(exp['ci'][1])}", "0.58, 0.71"),
        ("rating against intelligence scores, |r|", fmt(abs(intel["r"])), "0.03"),
        ("its p", f"{intel['p']:.3f}", "0.596"),
        ("predictions' mean", fmt(pred.mean()), "41.11"),
        ("predictions' median", fmt(float(np.median(pred))), "39.50"),
        ("predictions' SD", fmt(pred.std(ddof=1)), "25.28"),
        ("rating against predictions, r", fmt(preds["r"]), "0.56"),
        ("its CI", f"{fmt(preds['ci'][0])}, {fmt(preds['ci'][1])}", "0.48, 0.63"),
        ("rating against predictions, paired t(299)", fmt(abs(pt["t"])), "10.90"),
    ]
    matched = [w for w, c, p in printed if c == p]
    differs = [{"what": w, "computed": c, "printed": p, "sign_only": c.replace("-", "") == p.replace("-", "")}
               for w, c, p in printed if c != p]
    signs = [x["what"] for x in differs if x["sign_only"]]
    others = [x["what"] for x in differs if not x["sign_only"]]

    boot = bootstrap(seed, d)
    controls = controls_known()

    values = {
        "sample": (f"{N} participants; " + ", ".join(f"{v} {k}" for k, v in gender.items())
                   + f"; mean age {fmt(age)}"),
        "above_1": (f"{above} of {N} rate ChatGPT above 1; mean {fmt(pheno.mean())}, median {np.median(pheno):g}, "
                    f"SD {fmt(pheno.std(ddof=1))}"),
        "share_above_1": round(above / N, 4),
        "usage": (f"B {fmt(use['b'])}, SE {fmt(use['se'])}, t {fmt(use['t'])}, CI {fmt(use['ci'][0])} to "
                  f"{fmt(use['ci'][1])}, n {use['n']} ({use['dropped']} left out)"),
        "usage_slope": round(use["b"], 4),
        "usage_p": float(f"{use['p']:.3g}"),
        "r_experience": round(exp["r"], 4),
        "p_experience": float(f"{exp['p']:.3g}"),
        "intelligence": (f"rating against the second component: |r| {abs(intel['r']):.4f}, p {intel['p']:.3f}; "
                         f"loadings against mean attribution: experience r {load_exp['r']:.3f}, intelligence "
                         f"|r| {abs(load_int['r']):.3f}"),
        "pca": (f"two components {two:.1f}% of variance (first {100 * P['eig'][0] / TRAITS:.1f}%); "
                f"{int(np.sum(P['load'][:, 0] > 0))} of {TRAITS} states load positively on the first; "
                f"{P['missing']} missing ratings imputed"),
        "predictions": (f"mean {fmt(pred.mean())}, median {np.median(pred):g}, SD {fmt(pred.std(ddof=1))}; r with "
                        f"the rating {fmt(preds['r'])}; paired t({pt['df']}) {fmt(abs(pt['t']))}"),
        "users": (f"heard of it {know:.1f}%, used it {used:.1f}%; users {fmt(users['ma'])} against non-users "
                  f"{fmt(users['mb'])}, Welch t({users['df']:.1f}) {fmt(users['t'])}"),
        "printed_values": (f"{len(matched)} of {len(printed)} as printed"
                           + (f"; {len(signs)} differ only in sign: " + ", ".join(signs) if signs else "")
                           + ("; not: " + ", ".join(others) if others else ""))[:LIMIT],
        "bootstrap_95ci": (f"share above 1 {boot['share'][0]:.3f} to {boot['share'][1]:.3f}; usage slope "
                           f"{boot['slope'][0]:.2f} to {boot['slope'][1]:.2f}; r {boot['r'][0]:.3f} to "
                           f"{boot['r'][1]:.3f} ({boot['n']} resamples)"),
        "conditions_met": sum(cond.values()), "conditions_total": len(cond), "test_passed": int(all(cond.values())),
        "controls_passed": sum(controls.values()), "controls_total": len(controls),
    }
    out = {k: values[k] for k in OUTPUTS}
    for k, v in out.items():
        if isinstance(v, str) and len(v) > LIMIT:
            raise AssertionError(f"{k}: longer than {LIMIT} characters: {v}")
    detail = {
        "inputs": {k: {"name": n, "sha256": s} for k, (n, s) in INPUTS.items()},
        "conditions": cond, "controls": controls,
        "above_1": above, "usage": use, "experience": exp, "intelligence": intel,
        "loadings": {t: [float(P["load"][j, 0]), float(P["load"][j, 1])] for j, t in enumerate(d["traits"])},
        "item_means": {t: float(item_means[j]) for j, t in enumerate(d["traits"])},
        "eigenvalues": [float(v) for v in P["eig"]],
        "quadratic": quad, "users_vs_never": users, "predictions": preds, "paired": pt,
        "printed": [{"what": w, "computed": c, "printed": p} for w, c, p in printed], "differs": differs,
        "bootstrap": boot,
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
        sys.exit(f"colombatto: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
