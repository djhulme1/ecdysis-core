#!/usr/bin/env python3
"""Richardson et al. 2021: dietary restriction of the branched-chain amino acids and survival in two progeroid mouse
models and in wild-type mice fed for life, recomputed from the authors' per-mouse lifespans with the paper's own tests.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:1be155e1b24e78fd) is from N. E. Richardson,
E. N. Konon, H. S. Schuster, A. T. Mitchell, C. Boyle, A. C. Rodgers, M. Finke, L. R. Haider, D. Yu, V. Flores,
H. H. Pak, S. Ahmad, S. Ahmed, A. Radcliff, J. Wu, E. M. Williams, L. Abdi, D. S. Sherman, T. Hacker and D. W. Lamming,
"Lifelong restriction of dietary branched-chain amino acids has sex-specific benefits for frailty and life span in
mice", Nature Aging 1, 73-86 (2021): "Here, we demonstrate that restricting dietary BCAAs increases the survival of two
different progeroid mouse models, delays frailty and promotes the metabolic health of wild-type C57BL/6J mice when
started in midlife, and leads to a 30% increase in lifespan and a reduction in frailty in male, but not female,
wild-type mice when fed lifelong."

The test, as registered: see TEST below. The input is the claim's data of record, the paper's Supplementary Tables
workbook (Nature Aging's file 43587_2020_6_MOESM2_ESM.xlsx, read here as inputs/SupplementaryTables_MOESM2.xlsx),
checked against its SHA-256 and size and read with the standard library (its XML parsed as data; nothing in it is
run). Every rule below was fixed before any lifespan
statistic was computed from it: only its layout (sheet names, headers, captions and the first row of each table) and
the paper's printed statistics (Supplementary Table 3, the text and the figure legends) were read beforehand.

1. The mice. Supplementary Tables 2 (Lmna-/-, Figure 1A-B), 5 (LmnaG609G/G609G, Figure 1D), 8 (C57BL/6J.Nia mice
   switched at 16 months, Figure 4A-B) and 10 (wild-type mice fed from weaning, Figure 5D and 5H) are Prism survival
   tables: a column headed "Lifespan" (days) and one column per diet; each mouse is a row with 1 (died, the event) or 0
   (censored) in its diet's column and nothing in the others. Tables 2, 8 and 10 hold females on the left and males on
   the right, each half with its own Lifespan column; Table 5 holds one group of both sexes. The run is refused unless
   every row of a half has a non-negative whole number of days and exactly one diet cell, 0 or 1, the half's rows are
   contiguous, and each diet holds the number of mice its caption gives (CAPTION_N).
2. The statistics, each diet against its table's Control of the same half, two-sided, as GraphPad Prism 8 (the paper's
   software) computes them:
   - Kaplan-Meier survival, in exact fractions. The median as Prism takes it (its FAQ 44, after Machin): the first age
     at which the staircase falls below one half; where it is exactly one half over an interval, the average of the
     age at which it reaches one half and the age at which it falls below; undefined if it never falls below one half.
   - The log-rank (Mantel-Haenszel) test: at each age at which a mouse of either group died, the diet group's observed
     deaths less those expected, d n_diet / n, summed, and the hypergeometric variance
     d (n_diet / n)(1 - n_diet / n)(n - d) / (n - 1), summed (exact fractions); p = P(chi-square with 1 df >
     (O - E)^2 / V). The direction is the sign of O - E: below zero, the diet's mice died fewer than expected.
   - The Gehan-Breslow-Wilcoxon test (Prism's name): the same sums with each age's terms weighted by n, the number of
     mice of both groups at risk (n^2 in the variance).
   - The change in the median, 100 (m_diet / m_Control - 1).
3. The test's four conditions, each Low BCAA against Control:
   (a) Lmna-/- females (Table 2): Gehan-Breslow-Wilcoxon p below 0.05, O - E below zero and the median longer (the
       paper's test where these curves cross; its log-rank p is reported beside);
   (b) LmnaG609G/G609G mice (Table 5): log-rank p below 0.05, O - E below zero and the median longer;
   (c) wild-type males fed from weaning (Table 10): log-rank p below 0.05, O - E below zero and the median at least
       1.25 times Control's ("a 30% increase", a figure rounded to one significant digit: 25% or more);
   (d) wild-type females fed from weaning (Table 10): the median less than 1.25 times Control's, and no longer
       survival at log-rank p below 0.05 (not both p below 0.05 and O - E below zero).
   test_passed is 1 if all four hold.
4. Beside the test, none of it counted.
   - Supplementary Table 3 as printed: each median and its change, each log-rank and Wilcoxon p, each "Max (75%)
     Survival" and its change, and each Wang-Allison p, set against its recomputation (a p matches when the computed p
     rounds to the printed digits, a median or maximum when it is the printed whole number of days, a change when it
     rounds to the printed two decimals). The medians also by the standard rule (the first age at which survival is at
     or below one half). The maxima under each reading the paper's words allow: each group's age at 75% mortality by its
     Kaplan-Meier staircase (Prism's rule at one quarter), or the 75th percentile of its deaths, or of all its mice, by
     nearest rank. The Wang-Allison p (the Methods: "a cutoff of the top 25% longest lived animals in each cohort,
     coupled with Boschloo's test"; Table 3: "longest lived quartile across all cohorts") under each reading: the
     cutoff the age of 75% mortality (by the same three rules) of the two groups compared or of every group of the
     table's half; censored mice dropped or counted by their ages; mice beyond the cutoff against the rest, by
     Boschloo's exact test (scipy's, two-sided) or Fisher's.
   - The Low AA groups against Control, and the midlife cohort (Table 8; the paper: no extension, p 0.959 and 0.608).
   - The text's counts: 26% of the midlife Low BCAA females dead before 717 days against 8% of Control's (as shares of
     each group, and by Kaplan-Meier); the longest-lived lifelong Low BCAA male, 1,456 days; the changes the text prints
     (86% and 59% in Lmna-/- females, 38% in Lmna-/- males on Low AA, 7% and 15% in LmnaG609G/G609G, 31.8% and 34.9% in
     lifelong males, a 22% reduction in lifelong Low AA females).
   - Frailty, which the deposit gives only as each index item's mean by age and diet (Supplementary Tables 6, 7, 9 and
     11): the mean of the items' means at each age, by diet, and the ages at which Low BCAA's is below Control's, beside
     the text (lower in Low BCAA mice of both sexes switched in midlife; lower in lifelong Low BCAA males after 25
     months; no difference in lifelong females).
   - What it cannot recompute: the mixed-effects models for frailty (no per-mouse scores are deposited) and the
     metabolic measures (not deposited), the delays of frailty and the metabolic health the claim also states.

Controls (controls_passed counts those that behave as stated; the run stops if any fails):
   - the workbook is the pinned one, every table holds its captions' counts and Table 3 as read gives the printed
     values the rules were written from (PRINTED);
   - on seed-drawn censored samples with ties, and on each of the test's four comparisons, the module's log-rank and
     Gehan-Breslow-Wilcoxon p equal statsmodels 0.14's survdiff (weights None and "gb") to 1e-9, the log-rank p equals
     scipy 1.11's logrank to 1e-9, and the exact Kaplan-Meier curve equals scipy's ecdf in floating point to 1e-12;
   - Prism's FAQ example of a curve at one half from 9 to 17 (median 13), a curve that stays above one half (no
     median), and a curve that falls through one half (its first age below it);
   - swapping the two groups leaves each p and reverses O - E; reading the rows in reverse order leaves every value;
     each Control against itself gives p = 1;
   - planted faults each condition must catch, whatever the data hold: the Lmna-/- females' Control mice standing for
     their Low BCAA mice make (a) fail; the lifelong Control males' ages multiplied by 1.2 standing for Low BCAA's (a
     gain under 25%) make (c) fail; the lifelong Control females' ages multiplied by 1.4 standing for Low BCAA's make
     (d) fail.

Changed after the first trial (under a trial seed; the test, its conditions and their computations unchanged, every
change beside the test, made after its outputs were seen):
   - the frailty tables write each item as text, "mean ± SEM" to two decimals, which the first reader took for no
     number at all, so every frailty mean was empty: the reader now takes the mean before "±" (exactly, as written)
     and refuses a cell it cannot read or a table with no score;
   - the text's "26% dying prior to 717 days (the lifespan of the last mouse in the Low BCAA group prior to the curves
     crossing)" counts that mouse: the deaths by 717 days are now reported, by Kaplan-Meier and as shares, beside those
     before it;
   - Table 3 prints its medians in whole days (Prism's 68.5 and 52.5 as 69 and 53) and its changes from the rounded
     medians: a median now matches when it rounds half up to the printed day and a change when the change of the
     rounded medians rounds to it (the unrounded matches are counted too), and a printed log-rank p that is the
     Gehan-Breslow-Wilcoxon p is counted as such.

What it cannot check: whether the tables are the data the paper analysed (Table 3's values are compared beside), and
the mice's causes of death.

Writes results/outputs.json (the values a receipt carries) and results/detail.json (every value computed).
Run with: python3 dr/richardson2021.py
"""

import os

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_CORETYPE", "Prescott")

import hashlib  # noqa: E402
import io  # noqa: E402
import json  # noqa: E402
import math  # noqa: E402
import re  # noqa: E402
import sys  # noqa: E402
import xml.etree.ElementTree as ET  # noqa: E402
import zipfile  # noqa: E402
from fractions import Fraction  # noqa: E402

WORKBOOK = ("SupplementaryTables_MOESM2.xlsx", "9ade808b2337832331529cfa0da3348672c93844c841a4caf15acc443a0b04c9",
            215229)

CAPTION_N = {
    "Table S2": {"f": {"Control": 9, "Low BCAA": 18, "Low AA": 13}, "m": {"Control": 20, "Low BCAA": 14, "Low AA": 10}},
    "Table S5": {"all": {"Control": 15, "Low BCAA": 12, "Low AA": 8}},
    "Table S8": {"f": {"Control": 34, "Low BCAA": 34}, "m": {"Control": 35, "Low BCAA": 35}},
    "Table S10": {"f": {"Control": 60, "Low BCAA": 29, "Low AA": 9},
                  "m": {"Control": 54, "Low BCAA": 30, "Low AA": 21}},
}
HALF_LABEL = {"Table S2": ("Lmna-/- Females", "Lmna-/- Males"), "Table S5": ("LmnaG609G/G609G",),
              "Table S8": ("Females", "Males"), "Table S10": ("Females", "Males")}
PANELS = {"lmna_f": ("Table S2", "f"), "lmna_m": ("Table S2", "m"), "g609g": ("Table S5", "all"),
          "mid_f": ("Table S8", "f"), "mid_m": ("Table S8", "m"), "wt_f": ("Table S10", "f"),
          "wt_m": ("Table S10", "m")}
FRAILTY = {"Table S6": ("mid_f", "Female frailty scores (midlife intervention)"),
           "Table S7": ("mid_m", "Male frailty scores (midlife intervention)"),
           "Table S9": ("wt_f", "Female frailty scores (lifelong intervention)"),
           "Table S11": ("wt_m", "Male frailty scores (lifelong intervention)")}

# Supplementary Table 3 as printed (read with the paper before the rules): per panel and diet, the median (days), its
# change (%), the log-rank p, the Wilcoxon p (Table 2 only), the "Max (75%) Survival" (days) and its change (%); and
# the Wang-Allison p of each diet against Control.
PRINTED = {
    "lmna_f": {"Control": (37, None, None, None, 67, None), "Low BCAA": (69, 86.49, 0.0794, 0.0098, 79, 17.91),
               "Low AA": (59, 59.46, 0.366, 0.0355, 74, 10.45)},
    "lmna_m": {"Control": (48, None, None, None, 74, None), "Low BCAA": (53, 10.42, 0.5527, 0.5689, 57, -22.97),
               "Low AA": (66, 37.5, 0.2045, 0.0714, 74, 0.0)},
    "g609g": {"Control": (167, None, None, None, 175, None), "Low BCAA": (178, 6.59, 0.0274, None, 393, 124.57),
              "Low AA": (192, 14.97, 0.0144, None, 295, 68.57)},
    "mid_f": {"Control": (839, None, None, None, None, None), "Low BCAA": (882, 5.13, 0.959, None, None, None)},
    "mid_m": {"Control": (924, None, None, None, None, None), "Low BCAA": (952, 3.03, 0.608, None, None, None)},
    "wt_f": {"Control": (697, None, None, None, 879, None), "Low BCAA": (700, 0.43, 0.684, None, 751, -14.6),
             "Low AA": (543, -22.09, 0.218, None, 784, -10.81)},
    "wt_m": {"Control": (754, None, None, None, 911, None), "Low BCAA": (994, 31.83, 0.037, None, 1023, 12.29),
             "Low AA": (1017, 34.88, 0.033, None, 1077, 18.22)},
}
PRINTED_WA = {("lmna_f", "Low BCAA"): 0.1487, ("lmna_f", "Low AA"): 0.6416, ("lmna_m", "Low BCAA"): 0.9666,
              ("lmna_m", "Low AA"): 0.1478, ("g609g", "Low BCAA"): 0.0098, ("g609g", "Low AA"): 0.0119,
              ("mid_f", "Low BCAA"): 0.1176, ("mid_m", "Low BCAA"): 0.3925, ("wt_f", "Low BCAA"): 0.6905,
              ("wt_f", "Low AA"): 0.4459, ("wt_m", "Low BCAA"): 0.0251, ("wt_m", "Low AA"): 0.0066}
# The text's figures: the midlife females dead before 717 days (26% of Low BCAA's, 8% of Control's), the longest-lived
# lifelong Low BCAA male (1,456 days), and the changes in median lifespan it prints (%).
TEXT = {"early": (717, 26, 8), "longest": 1456,
        "changes": {("lmna_f", "Low BCAA"): 86, ("lmna_f", "Low AA"): 59, ("lmna_m", "Low AA"): 38,
                    ("g609g", "Low BCAA"): 7, ("g609g", "Low AA"): 15, ("wt_m", "Low BCAA"): 31.8,
                    ("wt_m", "Low AA"): 34.9, ("wt_f", "Low AA"): -22}}
ALPHA = Fraction(1, 20)
GAIN = Fraction(5, 4)
LIMIT = 200
TEST = ("Refuted if, in the authors' Supplementary Tables 2, 5 and 10 (per-mouse lifespans in days, 0 = censored), "
        "Low BCAA against Control (two-sided; Kaplan-Meier medians as Prism takes them) does not give longer survival "
        "at P < 0.05 with a longer median in Lmna-/- females (Gehan-Breslow-Wilcoxon, the paper's test where their "
        "curves cross) and in LmnaG609G/G609G mice (log-rank); or lifelong-fed wild-type males' median is not 25% or "
        "more above Control's with log-rank P < 0.05; or lifelong-fed wild-type females' median is 25% or more above "
        "Control's, or their survival is longer at log-rank P < 0.05.")
OUTPUTS = ("mice", "lmna_f_gbw_p", "lmna_f", "g609g_logrank_p", "g609g", "wt_m_logrank_p", "wt_m_gain",
           "wt_f_logrank_p", "wt_f_gain", "table_s3", "maxima", "wang_allison", "text_values", "frailty", "beside",
           "conditions_met", "conditions_total", "test_passed", "controls_passed", "controls_total")

NS = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
      "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"}


class Refused(Exception):
    pass


# ---------------------------------------------------------------- the workbook (rule 1)

def col_index(ref):
    n = 0
    for ch in re.match(r"[A-Z]+", ref).group(0):
        n = n * 26 + ord(ch) - 64
    return n - 1


def read_workbook(path, sha256, size):
    """{sheet name: [row as a list of cell texts or None]}, every sheet, from the pinned file."""
    with open(path, "rb") as f:
        data = f.read()
    if len(data) != size or hashlib.sha256(data).hexdigest() != sha256:
        raise Refused(f"{path}: not the pinned workbook ({len(data)} bytes)")
    sheets = {}
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        shared = []
        if "xl/sharedStrings.xml" in z.namelist():
            for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall("x:si", NS):
                shared.append("".join(t.text or "" for t in si.iter("{%s}t" % NS["x"])))
        wb = ET.fromstring(z.read("xl/workbook.xml"))
        rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
        target = {r.get("Id"): r.get("Target") for r in rels}
        for s in wb.find("x:sheets", NS):
            t = target[s.get("{%s}id" % NS["r"])].lstrip("/")
            t = t if t.startswith("xl/") else "xl/" + t
            rows = []
            for row in ET.fromstring(z.read(t)).iter("{%s}row" % NS["x"]):
                vals = {}
                for c in row.findall("x:c", NS):
                    kind, v = c.get("t"), c.find("x:v", NS)
                    if kind == "s" and v is not None:
                        val = shared[int(v.text)]
                    elif kind == "inlineStr":
                        val = "".join(x.text or "" for x in c.iter("{%s}t" % NS["x"]))
                    else:
                        val = v.text if v is not None else None
                    vals[col_index(c.get("r"))] = val
                rows.append([vals.get(i) for i in range(max(vals) + 1)] if vals else [])
            sheets[s.get("name")] = rows
    return sheets


def cell(row, j):
    v = row[j] if j < len(row) else None
    return None if v is None or str(v).strip() == "" else str(v).strip()


def number(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def halves(sheet, name):
    """{half: {diet: [(days, died)]}} from one Prism survival table, every row checked as rule 1 requires."""
    rows = [r for r in sheet if any(cell(r, j) is not None for j in range(len(r)))]
    hi = [i for i, r in enumerate(rows) if any(cell(r, j) == "Lifespan" for j in range(len(r)))]
    if len(hi) != 1:
        raise Refused(f"{name}: {len(hi)} header rows")
    h = hi[0]
    header = rows[h]
    starts = [j for j in range(len(header)) if cell(header, j) == "Lifespan"]
    keys = list(CAPTION_N[name])
    labels = HALF_LABEL[name]
    if len(starts) != len(keys):
        raise Refused(f"{name}: {len(starts)} Lifespan columns")
    out = {}
    for k, j0, label in zip(keys, starts, labels):
        if cell(rows[h - 1], j0) != label:
            raise Refused(f"{name}: half {k} is labelled {cell(rows[h - 1], j0)!r}")
        diets = []
        j = j0 + 1
        while cell(header, j) is not None and cell(header, j) != "Lifespan":
            diets.append((j, " ".join(cell(header, j).split())))
            j += 1
        if sorted(d for _, d in diets) != sorted(CAPTION_N[name][k]):
            raise Refused(f"{name}: half {k} has diets {[d for _, d in diets]}")
        mice = {d: [] for _, d in diets}
        ended = False
        for i in range(h + 1, len(rows)):
            r = rows[i]
            x = cell(r, j0)
            flags = [(d, cell(r, jj)) for jj, d in diets if cell(r, jj) is not None]
            if x is None or number(x) is None:
                if flags:
                    raise Refused(f"{name} row {i + 1}: a diet cell without a lifespan")
                if mice and any(mice.values()):
                    ended = True
                continue
            if ended:
                raise Refused(f"{name} row {i + 1}: half {k}'s rows are not contiguous")
            t = number(x)
            if t < 0 or t != int(t):
                raise Refused(f"{name} row {i + 1}: {x!r} is not a whole number of days")
            if len(flags) != 1 or flags[0][1] not in ("0", "1"):
                raise Refused(f"{name} row {i + 1}: diet cells {flags}")
            mice[flags[0][0]].append((int(t), flags[0][1] == "1"))
        for d, n in CAPTION_N[name][k].items():
            if len(mice[d]) != n:
                raise Refused(f"{name}: half {k}, {d} holds {len(mice[d])} mice, its caption {n}")
        out[k] = mice
    return out


def read_printed(sheet):
    """Supplementary Table 3's numbers as read, in the order PRINTED lists them, for the control."""
    vals = []
    for r in sheet:
        for x in r:
            v = number(x)
            if v is not None:
                vals.append(v)
    return vals


# ---------------------------------------------------------------- the statistics (rule 2)

def km(ms):
    """[(age, S(age))] at each age at which a mouse died, S exact."""
    data = sorted(ms)
    n, s, out, i = len(data), Fraction(1), [], 0
    while i < len(data):
        t, d, c = data[i][0], 0, 0
        while i < len(data) and data[i][0] == t:
            if data[i][1]:
                d += 1
            else:
                c += 1
            i += 1
        if d:
            s *= Fraction(n - d, n)
            out.append((t, s))
        n -= d + c
    return out


def prism_quantile(ms, level):
    """Prism's rule: the first age at which the staircase falls below level; on a plateau exactly at level, the
    average of the age it reaches level and the age it falls below; None if it never falls below."""
    curve = km(ms)
    for k, (t, s) in enumerate(curve):
        if s < level:
            return Fraction(t)
        if s == level:
            for t2, s2 in curve[k + 1:]:
                if s2 < level:
                    return Fraction(t + t2, 2)
            return None
    return None


def standard_quantile(ms, level):
    """The first age at which survival is at or below level (R's survfit and the usual definition)."""
    for t, s in km(ms):
        if s <= level:
            return Fraction(t)
    return None


def weighted(control, diet, weighting):
    """Two-sided p and O - E of the diet group: "logrank" (weights 1) or "gbw" (the number at risk), exact sums."""
    both = control + diet
    o_e, var = Fraction(0), Fraction(0)
    for t in sorted({x for x, died in both if died}):
        n = sum(1 for x, _ in both if x >= t)
        d = sum(1 for x, died in both if x == t and died)
        nb = sum(1 for x, _ in diet if x >= t)
        db = sum(1 for x, died in diet if x == t and died)
        w = 1 if weighting == "logrank" else n
        o_e += w * (db - Fraction(d * nb, n))
        if n > 1:
            var += w * w * Fraction(d * nb * (n - nb) * (n - d), n * n * (n - 1))
    if var == 0:
        return 1.0, o_e
    chi2 = o_e * o_e / var
    return math.erfc(math.sqrt(float(chi2) / 2)), o_e


def change(m_diet, m_control):
    if m_diet is None or m_control is None:
        return None
    return 100 * (Fraction(m_diet) / Fraction(m_control) - 1)


def compare(control, diet):
    lp, loe = weighted(control, diet, "logrank")
    gp, goe = weighted(control, diet, "gbw")
    mc, md = prism_quantile(control, Fraction(1, 2)), prism_quantile(diet, Fraction(1, 2))
    return {"logrank_p": lp, "logrank_oe": loe, "gbw_p": gp, "gbw_oe": goe, "median": (md, mc),
            "change": change(md, mc), "std_median": (standard_quantile(diet, Fraction(1, 2)),
                                                     standard_quantile(control, Fraction(1, 2)))}


# ---------------------------------------------------------------- the conditions (rule 3)

def conditions(r):
    a, b, c, d = r["lmna_f/Low BCAA"], r["g609g/Low BCAA"], r["wt_m/Low BCAA"], r["wt_f/Low BCAA"]

    def longer(x):
        return x["median"][0] is not None and x["median"][1] is not None and x["median"][0] > x["median"][1]

    def ratio(x):
        md, mc = x["median"]
        if mc is None:
            return None
        if md is None:
            return math.inf
        return Fraction(md) / Fraction(mc)

    rc, rd = ratio(c), ratio(d)
    return {
        "(a) Lmna-/- females: Gehan-Breslow-Wilcoxon p below 0.05, fewer deaths than expected, median longer":
            a["gbw_p"] < ALPHA and a["gbw_oe"] < 0 and longer(a),
        "(b) LmnaG609G/G609G: log-rank p below 0.05, fewer deaths than expected, median longer":
            b["logrank_p"] < ALPHA and b["logrank_oe"] < 0 and longer(b),
        "(c) lifelong males: log-rank p below 0.05, fewer deaths than expected, median at least 1.25 times Control's":
            c["logrank_p"] < ALPHA and c["logrank_oe"] < 0 and rc is not None and rc >= GAIN,
        "(d) lifelong females: median below 1.25 times Control's and no longer survival at log-rank p below 0.05":
            rd is not None and rd < GAIN and not (d["logrank_p"] < ALPHA and d["logrank_oe"] < 0),
    }


# ---------------------------------------------------------------- beside (rule 4)

def nearest_rank(values, q):
    v = sorted(values)
    if not v:
        return None
    return Fraction(v[max(0, math.ceil(q * len(v)) - 1)])


def max75(ms, reading):
    if reading == "km":
        return prism_quantile(ms, Fraction(1, 4))
    if reading == "deaths":
        return nearest_rank([t for t, died in ms if died], Fraction(3, 4))
    return nearest_rank([t for t, _ in ms], Fraction(3, 4))


def wang_allison(control, diet, pool, cut_reading, censored, test):
    """p of mice beyond the age of 75% mortality of pool, against the rest, in diet and Control."""
    cut = max75(pool, cut_reading)
    if cut is None:
        return None, None
    table = []
    for g in (diet, control):
        kept = [(t, died) for t, died in g if died or censored == "ages"]
        beyond = sum(1 for t, _ in kept if t > cut)
        table.append([beyond, len(kept) - beyond])
    from scipy import stats
    if test == "boschloo":
        p = float(stats.boschloo_exact(table, alternative="two-sided").pvalue)
    else:
        p = float(stats.fisher_exact(table, alternative="two-sided")[1])
    return p, table


def rounds_to(x, printed):
    """True if x rounds to the printed value at the printed value's digits (scientific forms included)."""
    if x is None or printed is None:
        return False
    s = repr(printed)
    if "e" in s:
        mant, ex = s.split("e")
        places = len(mant.split(".")[1]) if "." in mant else 0
        places -= int(ex)
    else:
        places = len(s.split(".")[1]) if "." in s else 0
    return abs(round(float(x), places) - printed) < 10 ** (-places) / 2 + 1e-15


def frailty_score(v):
    """A frailty cell as the deposit writes it, "mean ± SEM" (or a bare number): its mean, exact; None if empty."""
    if v is None:
        return None
    m = re.fullmatch(r"\s*(-?[0-9]+(?:\.[0-9]+)?)\s*(?:±\s*[0-9]+(?:\.[0-9]+)?)?\s*", v)
    if not m:
        raise Refused(f"frailty cell {v!r} is not a mean with its SEM")
    return Fraction(m.group(1))


def frailty_means(sheet, name):
    rows = [r for r in sheet if any(cell(r, j) is not None for j in range(len(r)))]
    ages = rows[0]
    diets = rows[1]
    if cell(ages, 0) != "Age" or cell(diets, 0) != "Category":
        raise Refused(f"{name}: not a frailty table")
    caption = " ".join(cell(r, 0) or "" for r in rows[-3:])
    if FRAILTY[name][1] not in caption:
        raise Refused(f"{name}: caption not as expected")
    cols = []
    age = None
    for j in range(1, len(diets)):
        if cell(ages, j) is not None:
            age = cell(ages, j)
        if cell(diets, j) is not None:
            cols.append((j, age, cell(diets, j)))
    sums = {(a, d): [] for _, a, d in cols}
    for r in rows[2:]:
        vals = [(a, d, frailty_score(cell(r, j))) for j, a, d in cols]
        for a, d, v in vals:
            if v is not None:
                sums[(a, d)].append(v)
    if not any(sums.values()):
        raise Refused(f"{name}: no frailty scores read")
    means = {k: (sum(v) / len(v) if v else None) for k, v in sums.items()}
    order = []
    for _, a, _ in cols:
        if a not in order:
            order.append(a)
    return order, means


# ---------------------------------------------------------------- controls

class Stream:
    def __init__(self, seed, label):
        self.seed, self.label, self.n = seed, label, 0

    def ints(self, k, lo, hi):
        out = []
        while len(out) < k:
            h = hashlib.sha256(f"{self.seed}/{self.label}/{self.n}".encode()).digest()
            self.n += 1
            for i in range(0, 32, 4):
                out.append(lo + int.from_bytes(h[i:i + 4], "big") % (hi - lo + 1))
        return out[:k]


def synthetic(seed, k):
    """Two seed-drawn censored groups with tied ages, about one mouse in five censored."""
    st = Stream(seed, f"richardson2021/synthetic/{k}")
    pair = []
    for g in range(2):
        size = 15 + st.ints(1, 0, 45)[0]
        ages = st.ints(size, 300, 1200)
        if g == 1:
            ages = [a + st.ints(1, 0, 120)[0] for a in ages]
        flags = st.ints(size, 0, 4)
        pair.append([(a // 7 * 7, f != 0) for a, f in zip(ages, flags)])
    return pair[0], pair[1]


def statsmodels_p(control, diet, weight_type):
    import numpy as np
    from statsmodels.duration.survfunc import survdiff
    time = [t for t, _ in control + diet]
    status = [1 if d else 0 for _, d in control + diet]
    group = [0] * len(control) + [1] * len(diet)
    _, p = survdiff(np.array(time, float), np.array(status, float), np.array(group), weight_type=weight_type)
    return float(p)


def scipy_logrank_p(control, diet):
    from scipy import stats

    def cd(ms):
        return stats.CensoredData(uncensored=[t for t, d in ms if d], right=[t for t, d in ms if not d])
    return float(stats.logrank(cd(control), cd(diet), alternative="two-sided").pvalue)


def scipy_km_agrees(ms):
    """scipy's ecdf reports the curve at every distinct age, censored ones included: the exact curve must give its
    values there, and every age of a death must be among them."""
    from scipy import stats
    res = stats.ecdf(stats.CensoredData(uncensored=[t for t, d in ms if d], right=[t for t, d in ms if not d]))
    mine = km(ms)
    q = [float(x) for x in res.sf.quantiles]
    p = [float(x) for x in res.sf.probabilities]

    def at(age):
        s = Fraction(1)
        for t, v in mine:
            if t > age:
                break
            s = v
        return s
    if not {float(t) for t, _ in mine} <= set(q):
        return False
    return all(abs(float(at(x)) - y) < 1e-12 for x, y in zip(q, p))


def controls_run(seed, panels, printed_numbers, results):
    ctl = {}
    ctl["the workbook pinned, every table with its captions' counts"] = True     # read_workbook and halves refuse
    flat = []
    for key in PANELS:
        for diet, vals in PRINTED[key].items():
            flat.extend(v for v in vals if v is not None)
    ctl["Supplementary Table 3 as read holds the printed values the rules were written from"] = all(
        any(abs(v - x) < 1e-9 for x in printed_numbers) for v in flat + list(PRINTED_WA.values()))
    agree = True
    for k in range(6):
        a, b = synthetic(seed, k)
        for w, sm in (("logrank", None), ("gbw", "gb")):
            agree &= abs(weighted(a, b, w)[0] - statsmodels_p(a, b, sm)) < 1e-9
        agree &= abs(weighted(a, b, "logrank")[0] - scipy_logrank_p(a, b)) < 1e-9
        agree &= scipy_km_agrees(a) and scipy_km_agrees(b)
    for key, diet in (("lmna_f", "Low BCAA"), ("g609g", "Low BCAA"), ("wt_m", "Low BCAA"), ("wt_f", "Low BCAA")):
        c, d = panels[key]["Control"], panels[key][diet]
        for w, sm in (("logrank", None), ("gbw", "gb")):
            agree &= abs(weighted(c, d, w)[0] - statsmodels_p(c, d, sm)) < 1e-9
        agree &= abs(weighted(c, d, "logrank")[0] - scipy_logrank_p(c, d)) < 1e-9
        agree &= scipy_km_agrees(c) and scipy_km_agrees(d)
    ctl["log-rank and Gehan-Breslow-Wilcoxon p as statsmodels and scipy give them; the exact curve as scipy's"] = agree
    faq = [(5, True), (9, True), (17, True), (20, True)]
    ctl["Prism's medians: a plateau at one half from 9 to 17 gives 13; above one half, none; through it, its age"] = (
        prism_quantile(faq, Fraction(1, 2)) == 13 and standard_quantile(faq, Fraction(1, 2)) == 9
        and prism_quantile([(5, True), (9, False), (17, False)], Fraction(1, 2)) is None
        and prism_quantile([(5, True), (6, True), (9, True)], Fraction(1, 2)) == 6)
    sym = True
    for key in PANELS:
        for diet in PRINTED[key]:
            if diet == "Control":
                continue
            c, d = panels[key]["Control"], panels[key][diet]
            for w in ("logrank", "gbw"):
                p, oe = weighted(c, d, w)
                p2, oe2 = weighted(d, c, w)
                p3, oe3 = weighted(list(reversed(c)), list(reversed(d)), w)
                sym &= abs(p - p2) < 1e-12 and oe == -oe2 and p == p3 and oe == oe3
            sym &= weighted(c, list(c), "logrank")[0] == 1.0 and weighted(c, list(c), "gbw")[0] == 1.0
    ctl["swapping the groups and reversing the rows leave each p; each Control against itself gives p = 1"] = sym
    r = dict(results)
    keys = list(conditions(r))
    copy_a = dict(r)
    copy_a["lmna_f/Low BCAA"] = compare(panels["lmna_f"]["Control"], list(panels["lmna_f"]["Control"]))
    gain_c = dict(r)
    gain_c["wt_m/Low BCAA"] = compare(panels["wt_m"]["Control"],
                                      [(Fraction(t) * Fraction(6, 5), died) for t, died in panels["wt_m"]["Control"]])
    gain_d = dict(r)
    gain_d["wt_f/Low BCAA"] = compare(panels["wt_f"]["Control"],
                                      [(Fraction(t) * Fraction(7, 5), died) for t, died in panels["wt_f"]["Control"]])
    ctl["planted faults: (a) fails with Control's mice as Low BCAA's, (c) with Control's ages x 1.2, (d) x 1.4"] = (
        not conditions(copy_a)[keys[0]] and not conditions(gain_c)[keys[2]] and not conditions(gain_d)[keys[3]])
    return ctl


# ---------------------------------------------------------------- run

def fmt(x, places=4):
    if x is None:
        return "none"
    return f"{float(x):.{places}f}"


def days(x):
    if x is None:
        return "none"
    x = Fraction(x)
    return str(int(x)) if x.denominator == 1 else f"{float(x):.1f}"


def run(seed, inputs="inputs", results="results"):
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        raise Refused("the seed must be 64 hex characters")
    book = read_workbook(os.path.join(inputs, WORKBOOK[0]), WORKBOOK[1], WORKBOOK[2])
    tables = {name: halves(book[name], name) for name in CAPTION_N}
    panels = {key: tables[t][h] for key, (t, h) in PANELS.items()}
    printed_numbers = read_printed(book["Table S3"])

    res = {}
    for key in PANELS:
        for diet in panels[key]:
            if diet != "Control":
                res[f"{key}/{diet}"] = compare(panels[key]["Control"], panels[key][diet])
    ctl = controls_run(seed, panels, printed_numbers, res)
    if not all(ctl.values()):
        raise AssertionError(f"a control failed: {[k for k, v in ctl.items() if not v]}")
    cond = conditions(res)

    # beside: Table 3 as printed
    def half_up(x):
        return None if x is None else math.floor(Fraction(x) + Fraction(1, 2))

    matched, total, misses, exact = 0, 0, [], 0
    lr_as_gbw = []
    for key in PANELS:
        for diet, (med, ch, lp, wp, mx, mch) in PRINTED[key].items():
            group = panels[key][diet]
            mine_med = prism_quantile(group, Fraction(1, 2))
            checks = [("median", half_up(mine_med) == med, mine_med is not None and mine_med == med)]
            if diet != "Control":
                r = res[f"{key}/{diet}"]
                rounded = change(half_up(r["median"][0]), half_up(r["median"][1]))
                checks.append(("change", rounded is not None and rounds_to(rounded, ch),
                               r["change"] is not None and rounds_to(r["change"], ch)))
                ok_lr = rounds_to(r["logrank_p"], lp)
                checks.append(("log-rank p", ok_lr, ok_lr))
                if not ok_lr and rounds_to(r["gbw_p"], lp):
                    lr_as_gbw.append(f"{key} {diet}")
                if wp is not None:
                    ok_w = rounds_to(r["gbw_p"], wp)
                    checks.append(("Wilcoxon p", ok_w, ok_w))
            for name, ok, ok_exact in checks:
                total += 1
                matched += ok
                exact += ok_exact
                if not ok:
                    misses.append(f"{key} {diet} {name}")
    maxima = {}
    for reading in ("km", "deaths", "all"):
        hits, n = 0, 0
        for key in PANELS:
            for diet, vals in PRINTED[key].items():
                if vals[4] is None:
                    continue
                v = max75(panels[key][diet], reading)
                n += 1
                hits += v is not None and v == vals[4]
        maxima[reading] = (hits, n)
    wa = {}
    for pool_kind in ("pair", "panel"):
        for cut_reading in ("km", "deaths", "all"):
            for censored in ("drop", "ages"):
                for test in ("boschloo", "fisher"):
                    hits, n, vals = 0, 0, {}
                    for (key, diet), printed in PRINTED_WA.items():
                        c, d = panels[key]["Control"], panels[key][diet]
                        pool = c + d if pool_kind == "pair" else [m for g in panels[key].values() for m in g]
                        p, table = wang_allison(c, d, pool, cut_reading, censored, test)
                        vals[f"{key}/{diet}"] = (p, table)
                        n += 1
                        hits += p is not None and rounds_to(p, printed)
                    wa[(pool_kind, cut_reading, censored, test)] = {"hits": hits, "n": n, "values": vals}
    best = max(wa, key=lambda k: wa[k]["hits"])

    # beside: the text's values
    early_cut, early_bcaa, early_ctl = TEXT["early"]
    mf = panels["mid_f"]
    share = {d: Fraction(sum(1 for t, died in mf[d] if died and t < early_cut), len(mf[d])) for d in mf}
    share_at = {d: Fraction(sum(1 for t, died in mf[d] if died and t <= early_cut), len(mf[d])) for d in mf}
    km_early, km_at = {}, {}
    for d in mf:
        s = s_at = Fraction(1)
        for t, sv in km(mf[d]):
            if t < early_cut:
                s = sv
            if t <= early_cut:
                s_at = sv
        km_early[d], km_at[d] = 1 - s, 1 - s_at
    longest = max(t for t, died in panels["wt_m"]["Low BCAA"] if died)
    text_changes = {f"{k}/{d}": res[f"{k}/{d}"]["change"] for (k, d) in TEXT["changes"]}

    # beside: frailty
    fr = {}
    for name, (key, _) in FRAILTY.items():
        order, means = frailty_means(book[name], name)
        lower = [a for a in order if means.get((a, "Low BCAA")) is not None and means.get((a, "Control")) is not None
                 and means[(a, "Low BCAA")] < means[(a, "Control")]]
        fr[key] = {"ages": order, "lower": lower,
                   "means": {f"{a} {d}": (float(v) if v is not None else None) for (a, d), v in means.items()}}

    a, b, c, d = (res[k] for k in ("lmna_f/Low BCAA", "g609g/Low BCAA", "wt_m/Low BCAA", "wt_f/Low BCAA"))
    short = {"Control": "C", "Low BCAA": "B", "Low AA": "A"}
    counts = "; ".join(f"{t.split()[-1]} " + " / ".join(
        f"{h} " + " ".join(f"{short[dd]}{len(v)}" for dd, v in tables[t][h].items()) for h in tables[t])
        for t in CAPTION_N)
    low_aa = ", ".join(f"{k} {fmt(res[k + '/Low AA']['change'], 1)}% p {fmt(res[k + '/Low AA']['logrank_p'], 3)}"
                       for k in ("lmna_f", "lmna_m", "g609g", "wt_f", "wt_m"))
    values = {
        "mice": f"as the captions give them: {counts}",
        "lmna_f_gbw_p": a["gbw_p"],
        "lmna_f": (f"medians {days(a['median'][0])} and {days(a['median'][1])} d (printed 69, 37); log-rank p "
                   f"{fmt(a['logrank_p'])} (printed 0.0794); O - E {fmt(a['gbw_oe'], 2)}"),
        "g609g_logrank_p": b["logrank_p"],
        "g609g": (f"medians {days(b['median'][0])} and {days(b['median'][1])} d (printed 178, 167); Wilcoxon p "
                  f"{fmt(b['gbw_p'])}; O - E {fmt(b['logrank_oe'], 2)}"),
        "wt_m_logrank_p": c["logrank_p"],
        "wt_m_gain": float(c["change"]) if c["change"] is not None else -1.0,
        "wt_f_logrank_p": d["logrank_p"],
        "wt_f_gain": float(d["change"]) if d["change"] is not None else -1.0,
        "table_s3": (f"{matched} of {total} printed medians (whole days), changes and p as computed ({exact} "
                     f"unrounded); log-rank p printed that are the Wilcoxon's: {len(lr_as_gbw)}; not: "
                     + (", ".join(misses[:2]) + (f" and {len(misses) - 2} more" if len(misses) > 2 else "")
                        if misses else "none")),
        "maxima": "Max (75%) as printed: " + ", ".join(f"{k} {h} of {n}" for k, (h, n) in maxima.items()),
        "wang_allison": (f"best reading {'/'.join(best)}: {wa[best]['hits']} of {wa[best]['n']} printed p; wt_m Low "
                         f"BCAA p {fmt(wa[best]['values']['wt_m/Low BCAA'][0])} (printed 0.0251)"),
        "text_values": (f"midlife females dead by 717 d, Kaplan-Meier (shares): Low BCAA "
                        f"{fmt(100 * km_at['Low BCAA'], 1)}% ({fmt(100 * share_at['Low BCAA'], 1)}), Control "
                        f"{fmt(100 * km_at['Control'], 1)}% "
                        f"({fmt(100 * share_at['Control'], 1)}); printed 26, 8; longest lifelong Low BCAA male "
                        f"{longest} d (printed 1456)"),
        "frailty": "Low BCAA mean item score below Control's at " + "; ".join(
            f"{k} {len(v['lower'])} of {len(v['ages'])} ages" for k, v in fr.items()),
        "beside": f"Low AA vs Control: {low_aa}",
        "conditions_met": sum(cond.values()), "conditions_total": len(cond), "test_passed": int(all(cond.values())),
        "controls_passed": sum(ctl.values()), "controls_total": len(ctl),
    }
    out = {k: values[k] for k in OUTPUTS}
    for k, v in out.items():
        if isinstance(v, str) and len(v) > LIMIT:
            raise AssertionError(f"{k}: longer than {LIMIT} characters: {v}")
        if isinstance(v, float) and not math.isfinite(v):
            raise AssertionError(f"{k}: not finite")

    def js(x):
        if isinstance(x, Fraction):
            return float(x)
        if isinstance(x, dict):
            return {str(k): js(v) for k, v in x.items()}
        if isinstance(x, (list, tuple)):
            return [js(v) for v in x]
        return x

    detail = {"input": {"name": WORKBOOK[0], "sha256": WORKBOOK[1], "bytes": WORKBOOK[2]},
              "counts": {t: {h: {dd: len(v) for dd, v in tables[t][h].items()} for h in tables[t]} for t in tables},
              "conditions": cond, "controls": ctl, "results": js(res), "table_s3_misses": misses,
              "table_s3_logrank_as_wilcoxon": lr_as_gbw,
              "maxima": {k: list(v) for k, v in maxima.items()},
              "max75_values": {f"{key}/{diet}/{reading}": js(max75(panels[key][diet], reading))
                               for key in PANELS for diet in panels[key] for reading in ("km", "deaths", "all")},
              "wang_allison": {"/".join(k): js(v) for k, v in wa.items()}, "best_reading": list(best),
              "early_deaths": {"before 717: share": js(share), "before 717: km": js(km_early),
                               "by 717: share": js(share_at), "by 717: km": js(km_at)}, "longest": longest,
              "text_changes": js(text_changes), "frailty": fr, "test": TEST}
    os.makedirs(results, exist_ok=True)
    with open(os.path.join(results, "outputs.json"), "w", encoding="ascii") as fh:
        json.dump(out, fh, indent=2, sort_keys=True)
        fh.write("\n")
    with open(os.path.join(results, "detail.json"), "w", encoding="utf-8") as fh:
        json.dump(detail, fh, indent=1, sort_keys=True, ensure_ascii=False)
        fh.write("\n")
    return out, detail


def main():
    seed = os.environ.get("ECDYSIS_SEED", "")
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        sys.exit("ECDYSIS_SEED must be the 64-hex seed the archive issued")
    try:
        out, _ = run(seed)
    except Refused as e:
        sys.exit(f"richardson2021: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
