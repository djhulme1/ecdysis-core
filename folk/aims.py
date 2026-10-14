"""The AIMS survey's abstract sentence, recounted from the released data by the authors' own analysis rules.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:ef92c8539d44adcb) is from Anthis, Pauketat,
Ladak and Manoli, "Perceptions of Sentient AI and Other Digital Minds: Evidence from the AI, Morality, and Sentience
(AIMS) Survey", CHI '25 (arXiv:2407.08867v3): "Mind perception and moral concern for AI welfare were surprisingly high
and significantly increased: in 2023, one in five U.S. adults believed some AI systems are currently sentient, and 38%
supported legal rights for sentient AI."

Its registered test: refuted if, on the released Main 2021 and Main 2023 data with their raking weights, the 2023
weighted share answering Yes (of Yes, No, Not sure) to whether any existing robots/AIs are sentient is outside 17.5%
to 22.5% (one in five); or 2023 weighted agreement with granting legal rights to sentient robots/AIs (codes 5 to 7 of
1 to 3 and 5 to 7; 4 is no opinion) is outside 37% to 39%; or the mind perception index (mean of MP1 to MP4) or the
moral concern index (mean of MCE21 to MCE31) is not higher in 2023 at two-sided p < 0.05 by the authors' weighted
t-test.

The input is the paper's arXiv e-print (version 3, the CHI '25 text, a gzipped tar), checked against its SHA-256 and
read in memory as data: its supplemental_materials/main_2021_data.csv, main_2023_data.csv, main_codebook.csv and, for
values beside the test, supplement_2023_data.csv, parsed with pandas.read_csv as the authors' analysis.py reads them.
Nothing in the archive is run, and nothing is written from it to disk. analysis.py, in the same archive, is the method
followed; it is not run (it is the authors' code, and needs weightedstats and a notebook's display), and each rule below
names the cell of it that it reimplements, by the same pandas and statsmodels calls. Every rule was fixed before any
statistic was computed. The seed draws only the bootstrap beside the test.

1. The files. Each main wave's file must have the columns F1, F2, weight, PMC1 to PMC12, MCE1 to MCE9, MCE21 to
   MCE31, MP1 to MP4 and Anth1 to Anth4. What the test reads is checked: F1 must be Yes, No or Not sure in every row,
   PMC9 an integer from 1 to 7 or empty, MP1 to MP4 from 0 to 100 and MCE21 to MCE31 from 1 to 5, or empty, and every
   weight positive; the other columns are read as numbers, anything else in them as missing. The codebook must word
   F1, PMC9 and MP1 to MP4 as below and call MCE21 to MCE31 "Moral concern: ... (scale 1-5)". Anything else is
   refused. The supplement's file is read only for its F1 shares, by the same rule, and if it cannot be read the
   reason is reported in their place.
2. The first condition, by the "Extra main stats" cell's Yes, No, Not sure rule on Main 2023: the weight answering
   Yes over the weight answering any of the three. It holds if the share is from 0.175 to 0.225.
3. The second, by the same cell's agreement rule on PMC9 ("I support granting legal rights to sentient robots/AIs.")
   in Main 2023: the weight on codes 5, 6 and 7 over the weight on 1, 2, 3, 5, 6 and 7 (4, no opinion, left out); the
   cell's round(..., 4) is not applied. It holds if the agreement is from 0.37 to 0.39.
4. The third, by the first cell (the 2021 to 2023 comparison): the two waves concatenated, F1 and the other
   Yes, No, Not sure columns made True where Yes, and the indices built as it builds them, Mind Perception
   d[['MP1', 'MP2', 'MP3', 'MP4']].mean(axis=1) and AI Moral Concern d[['MCE21', ..., 'MCE31']].mean(axis=1) (pandas
   skips a missing item; a respondent with none is missing and left out). For each index, the weighted means of the
   respondents with a value in each wave (np.average with their weights) and
   statsmodels.stats.weightstats.ttest_ind(x2021, x2023, weights=(w2021, w2023)), pooled variance and two-sided, as
   the cell calls it. The condition holds if, for both indices, the 2023 mean is the higher and p < 0.05.
   test_passed is 1 if all three conditions hold.
5. Beside the test, other numbers the paper prints from the two main waves, each recomputed by the rule of the cell
   that computes it and compared at the precision printed (Main 2023 unless a year is given): the two Ns; F1's three
   shares, and that it did not change significantly between the waves (the first cell's test on F1 as True or
   False); F2's shares saying sentient AI already exists (F2 = 0) and never will (F2 = -1 or empty) over all the
   weight, as the timeline cell computes them, and the two changes' z tests there (statsmodels proportions_ztest on
   the weighted counts); agreement with PMC9 in 2021; the sentient-AI column of Table 2 (MCE5, MCE1, PMC10, MCE3,
   PMC8, PMC11, MCE2, MCE4, PMC12); the bans (PMC4, PMC3, PMC1, and PMC1 in 2021 with the first cell's p for its
   change); four more proposals (PMC7, PMC2, PMC6, PMC5) and that none changed significantly; the four mental
   faculties' weighted means in each wave and their p values (MP3, MP4, MP1, MP2); the four anthropomorphism items'
   2023 means and that none changed significantly; the eleven moral concern items' 2023 means, the index's p and
   which items changed significantly (all but AI video game characters, MCE28, the paper says); and that none of the
   nine general moral concern items (MCE1 to MCE9) changed significantly. Significance is p < 0.05, the paper's
   cutoff. Also beside the test: F1's shares in Main 2021 and in Supplement 2023, and 95% intervals for the three
   tested quantities and the two indices' changes from 2,000 resamples of each wave's respondents, weights carried
   with them, drawn from ECDYSIS_SEED.
6. Controls, known answers: statsmodels' weighted t-test is the pooled formula with the weights as frequencies
   (n the sum of the weights, n1 + n2 - 2 degrees of freedom); with integer weights it equals scipy's
   equal-variance t-test on rows repeated by their weights; the share and agreement rules give exact ratios on a
   frame built here; and the index rule skips a missing item and leaves out a respondent with none.
7. The period: the released files carry no interview dates, so period_from and period_to are the first day of Main
   2021's fieldwork and the last of Main 2023's as the paper states them ("collected from November to December 2021";
   "From April to May 2023"), for the two files read.

What it cannot check: the survey itself (who took it, how they read the questions), the raking (the weights are taken
as released), and whether the samples stand for U.S. adults; "surprisingly high" is a judgement no number settles.

Writes results/outputs.json (the values a receipt carries) and results/detail.json (every value computed).
Run with: python3 folk/aims.py
"""

import csv
import hashlib
import io
import json
import math
import os
import re
import sys
import tarfile

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.proportion import proportions_ztest
from statsmodels.stats.weightstats import ttest_ind

INPUT = ("arXiv-2407.08867v3-source.tar.gz", "cb22b236a73bf6fd99e719569913ac2fa8895a1fc085f95b2de06448a018e364")
MEMBERS = {"2021": "supplemental_materials/main_2021_data.csv", "2023": "supplemental_materials/main_2023_data.csv",
           "codebook": "supplemental_materials/main_codebook.csv",
           "supplement": "supplemental_materials/supplement_2023_data.csv"}
FIELDWORK = {"2021": (20211101, 20211231), "2023": (20230401, 20230531)}
PMC = [f"PMC{i}" for i in range(1, 13)]
MCE_GENERAL = [f"MCE{i}" for i in range(1, 10)]
MCE_TARGET = [f"MCE{i}" for i in range(21, 32)]
MP = ["MP1", "MP2", "MP3", "MP4"]
ANTH = ["Anth1", "Anth2", "Anth3", "Anth4"]
COLUMNS = ["F1", "F2", "weight"] + PMC + MCE_GENERAL + MCE_TARGET + MP + ANTH
WORDING = {
    "F1": ("Do you think any robots/AIs that currently exist (i.e., those that exist in 2021) are sentient? "
           "(Yes, No, Not sure)"),
    "PMC9": "I support granting legal rights to sentient robots/AIs.",
    "MP1": "experiencing emotions (scale 0-100)", "MP2": "having feelings (scale 0-100)",
    "MP3": "thinking analytically (scale 0-100)", "MP4": "being rational (scale 0-100)",
}
ANSWERS = ("Yes", "No", "Not sure")
AGREE, OPINION = (5, 6, 7), (1, 2, 3, 5, 6, 7)
ONE_IN_FIVE = (0.175, 0.225)
RIGHTS = (0.37, 0.39)
ALPHA = 0.05
BOOTSTRAP = 2000
OUTPUTS = ("sample", "sentient_now_2023", "sentient_now", "legal_rights_2023", "legal_rights", "mind_perception_p",
           "mind_perception", "moral_concern_p", "moral_concern", "timelines", "printed_values", "bootstrap_95ci",
           "conditions_met", "conditions_total", "test_passed", "controls_passed", "controls_total", "period_from",
           "period_to")
LIMIT = 200


class Refused(Exception):
    pass


def read_input(inputs):
    path = os.path.join(inputs, INPUT[0])
    with open(path, "rb") as fh:
        raw = fh.read()
    got = hashlib.sha256(raw).hexdigest()
    if got != INPUT[1]:
        raise Refused(f"{INPUT[0]}: sha256 {got}, not the registered {INPUT[1]}")
    return raw


def members(raw):
    """The four files, as bytes, from the e-print in memory."""
    try:
        tar = tarfile.open(fileobj=io.BytesIO(raw), mode="r:*")
    except tarfile.TarError as e:
        raise Refused(f"the e-print is not a tar: {e}")
    out = {}
    with tar:
        names = {m.name: m for m in tar.getmembers() if m.isfile()}
        for k, name in MEMBERS.items():
            if name not in names:
                raise Refused(f"the e-print has no {name}")
            out[k] = tar.extractfile(names[name]).read()
    return out


def frame(raw, what, columns=COLUMNS):
    """Rule 1: a wave's file, its tested columns checked."""
    d = pd.read_csv(io.BytesIO(raw))
    missing = [c for c in columns if c not in d.columns]
    if missing:
        raise Refused(f"{what}: no column {', '.join(missing)}")
    if len(d) == 0:
        raise Refused(f"{what}: no rows")
    w = pd.to_numeric(d["weight"], errors="coerce")
    if w.isna().any() or not (w > 0).all() or not np.isfinite(w).all():
        raise Refused(f"{what}: a weight that is not a positive number")
    if columns is not COLUMNS:
        return d
    bad = sorted(set(str(v) for v in d["F1"]) - set(ANSWERS))
    if bad:
        raise Refused(f"{what}: F1 holds {bad[:3]}")
    for cols, lo, hi, integer in ((["PMC9"], 1, 7, True), (MP, 0, 100, False), (MCE_TARGET, 1, 5, False)):
        for c in cols:
            x = pd.to_numeric(d[c], errors="coerce")
            if (x.isna() & d[c].notna()).any():
                raise Refused(f"{what}: {c} holds a value that is not a number")
            v = x.dropna()
            if ((v < lo) | (v > hi)).any() or (integer and (v != np.round(v)).any()):
                raise Refused(f"{what}: {c} outside {lo} to {hi}")
    for c in COLUMNS:
        if c not in ("F1", "weight"):
            d[c] = pd.to_numeric(d[c], errors="coerce")
    return d


def codebook(raw):
    rows = list(csv.reader(io.StringIO(raw.decode("utf-8-sig"))))
    desc = {r[0]: r[1] for r in rows if len(r) >= 2}
    for k, v in WORDING.items():
        if desc.get(k) != v:
            raise Refused(f"the codebook words {k} as {desc.get(k)!r}")
    for c in MCE_TARGET:
        if not (desc.get(c, "").startswith("Moral concern: ") and desc[c].endswith("(scale 1-5)")):
            raise Refused(f"the codebook words {c} as {desc.get(c)!r}")
    return desc


def share_yes(d, col="F1"):
    """The Yes, No, Not sure rule: the weight on each answer over the weight on any of the three."""
    w = d["weight"]
    tot = w[d[col].isin(list(ANSWERS))].sum()
    return {a: float(w[d[col].isin([a])].sum() / tot) for a in ANSWERS}


def agreement(d, col):
    """The agreement rule: the weight on codes 5 to 7 over the weight on 1 to 3 and 5 to 7."""
    w = d["weight"]
    return float(w[d[col].isin(list(AGREE))].sum() / w[d[col].isin(list(OPINION))].sum())


def combined(d21, d23):
    """The first cell's frame: the waves concatenated, Yes, No, Not sure columns as True where Yes, the indices."""
    a, b = d21.copy(), d23.copy()
    a["year"], b["year"] = "2021", "2023"
    d = pd.concat([a, b], ignore_index=True)
    d["F1"] = d["F1"] == "Yes"
    d["AI Moral Concern"] = d[MCE_TARGET].mean(axis=1)
    d["Mind Perception"] = d[MP].mean(axis=1)
    d["AS Treatment"] = d[["MCE1", "MCE2", "MCE3", "MCE4", "MCE5", "MCE6"]].mean(axis=1)
    d["Anthropomorphism"] = d[ANTH].mean(axis=1)
    return d


def compare(d, c):
    """The first cell's test of a column: weighted means of the values present in each wave and the weighted t-test."""
    x, w, y = d[c], d["weight"], d["year"]
    ok = ~pd.isna(x)
    x21, x23 = x[ok & (y == "2021")].astype(float), x[ok & (y == "2023")].astype(float)
    w21, w23 = w[ok & (y == "2021")], w[ok & (y == "2023")]
    t, p, df = ttest_ind(x21, x23, weights=(w21, w23))
    return {"m2021": float(np.average(x21, weights=w21)), "m2023": float(np.average(x23, weights=w23)),
            "t": float(t), "p": float(p), "df": float(df), "n2021": int(len(x21)), "n2023": int(len(x23))}


def timelines(d21, d23):
    """The timeline cell, F2: already (0), never (-1 or empty), shares of all the weight, and the two z tests."""
    def wave(d, year):
        f = pd.to_numeric(d["F2"], errors="coerce").astype(float).reset_index(drop=True)
        if year == "2023":
            f = f.apply(lambda x: x - 2023 if (x < 2100) & (x >= 2023) else x)
        f[f == -1] = np.nan
        if year == "2021":
            f = f.apply(lambda x: x - 2023 if (x < 2100) & (x >= 2023) else x)
        never = f.isna()
        w = d["weight"].reset_index(drop=True)
        return {"already_w": float(w[f == 0].sum()), "never_w": float(w[never].sum()), "w": float(w.sum())}
    a, b = wave(d21, "2021"), wave(d23, "2023")
    _, p_already = proportions_ztest([a["already_w"], b["already_w"]], [a["w"], b["w"]])
    _, p_never = proportions_ztest([a["never_w"], b["never_w"]], [a["w"], b["w"]])
    return {"2021": {"already": a["already_w"] / a["w"], "never": a["never_w"] / a["w"]},
            "2023": {"already": b["already_w"] / b["w"], "never": b["never_w"] / b["w"]},
            "p_already": float(p_already), "p_never": float(p_never)}


def generator(seed, label):
    return np.random.Generator(np.random.PCG64(int.from_bytes(
        hashlib.sha256(bytes.fromhex(seed) + b"|" + label.encode("ascii")).digest(), "big")))


def bootstrap(seed, d, n=BOOTSTRAP):
    """Rule 5: each wave's respondents resampled with replacement, weights carried with them."""
    g = generator(seed, "aims/bootstrap")
    y = d["year"].to_numpy()
    w = d["weight"].to_numpy(float)
    yes = d["F1"].to_numpy(bool)
    pmc9 = d["PMC9"].to_numpy(float)
    agree, opinion = np.isin(pmc9, AGREE), np.isin(pmc9, OPINION)
    mp, mc = d["Mind Perception"].to_numpy(float), d["AI Moral Concern"].to_numpy(float)
    i21, i23 = np.flatnonzero(y == "2021"), np.flatnonzero(y == "2023")

    def wmean(v, ww):
        ok = ~np.isnan(v)
        return float(np.sum(v[ok] * ww[ok]) / np.sum(ww[ok]))
    share, rights, dmp, dmc = [], [], [], []
    for _ in range(n):
        a = i21[g.integers(0, len(i21), len(i21))]
        b = i23[g.integers(0, len(i23), len(i23))]
        share.append(float(np.sum(w[b] * yes[b]) / np.sum(w[b])))
        rights.append(float(np.sum(w[b] * agree[b]) / np.sum(w[b] * opinion[b])))
        dmp.append(wmean(mp[b], w[b]) - wmean(mp[a], w[a]))
        dmc.append(wmean(mc[b], w[b]) - wmean(mc[a], w[a]))

    def ci(v):
        return float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))
    return {"share": ci(share), "rights": ci(rights), "mp_change": ci(dmp), "mc_change": ci(dmc), "n": n}


def controls_known():
    """Rule 6."""
    x1, x2 = np.array([1.0, 2, 4, 7]), np.array([3.0, 5, 6, 9, 10])
    w1, w2 = np.array([0.5, 1.5, 1, 2]), np.array([1.0, 0.25, 2, 1.75, 1])
    t, p, df = ttest_ind(x1, x2, weights=(w1, w2))
    W1, W2 = w1.sum(), w2.sum()
    m1, m2 = np.sum(w1 * x1) / W1, np.sum(w2 * x2) / W2
    ss = np.sum(w1 * (x1 - m1) ** 2) + np.sum(w2 * (x2 - m2) ** 2)
    th = (m1 - m2) / math.sqrt(ss / (W1 + W2 - 2) * (1 / W1 + 1 / W2))
    formula_ok = (abs(t - th) < 1e-12 and abs(df - (W1 + W2 - 2)) < 1e-12
                  and abs(p - 2 * stats.t.sf(abs(th), W1 + W2 - 2)) < 1e-12)
    k1, k2 = np.array([1, 3, 2, 2]), np.array([2, 1, 1, 3, 2])
    t2, p2, _ = ttest_ind(x1, x2, weights=(k1.astype(float), k2.astype(float)))
    ref = stats.ttest_ind(np.repeat(x1, k1), np.repeat(x2, k2), equal_var=True)
    repeat_ok = abs(t2 - ref.statistic) < 1e-10 and abs(p2 - ref.pvalue) < 1e-10
    f = pd.DataFrame({"F1": ["Yes", "No", "Not sure", "Yes"], "PMC9": [5, 4, 1, 7], "weight": [1.0, 2.0, 3.0, 4.0]})
    rules_ok = (abs(share_yes(f)["Yes"] - 0.5) < 1e-15 and abs(agreement(f, "PMC9") - 5 / 8) < 1e-15)
    g = pd.DataFrame({"a": [1.0, np.nan, np.nan], "b": [3.0, 4.0, np.nan]})
    m = g[["a", "b"]].mean(axis=1)
    index_ok = m.iloc[0] == 2.0 and m.iloc[1] == 4.0 and pd.isna(m.iloc[2])
    return {"the weighted t-test is the pooled formula with frequency weights": bool(formula_ok),
            "integer weights equal repeated rows in scipy's t-test": bool(repeat_ok),
            "the share and agreement rules give exact ratios": bool(rules_ok),
            "the index skips a missing item and leaves out a respondent with none": bool(index_ok)}


def pct(x):
    return f"{100 * x:.1f}"


def pfmt(p, printed):
    if printed.startswith("<"):
        return "< 0.001" if p < 0.001 else f"{p:.3f}"
    return f"{p:.3f}"


def ns(results, names):
    """'n.s.' when none of the named columns changed at p < 0.05, else the ones that did."""
    sig = [c for c in names if results[c]["p"] < ALPHA]
    return "n.s." if not sig else "significant: " + ", ".join(sig)


def run(seed, inputs="inputs", results="results"):
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        raise Refused("the seed must be 64 hex characters")
    files = members(read_input(inputs))
    d21, d23 = frame(files["2021"], "Main 2021"), frame(files["2023"], "Main 2023")
    codebook(files["codebook"])
    try:
        sup = frame(files["supplement"], "Supplement 2023", columns=["F1", "weight"])
        f1_sup, sup_rows = share_yes(sup), len(sup)
    except (Refused, ValueError, KeyError, ZeroDivisionError) as e:
        f1_sup, sup_rows = f"unreadable: {e}"[:60], 0

    f1_23, f1_21 = share_yes(d23), share_yes(d21)
    rights23, rights21 = agreement(d23, "PMC9"), agreement(d21, "PMC9")
    d = combined(d21, d23)
    cmp = {c: compare(d, c) for c in ["Mind Perception", "AI Moral Concern", "AS Treatment", "Anthropomorphism", "F1"]
           + MP + MCE_TARGET + MCE_GENERAL + PMC + ANTH}
    mpi, mci = cmp["Mind Perception"], cmp["AI Moral Concern"]
    cond = {
        "the 2023 share saying some existing AI is sentient is from 17.5% to 22.5%":
            ONE_IN_FIVE[0] <= f1_23["Yes"] <= ONE_IN_FIVE[1],
        "2023 agreement with legal rights for sentient AI is from 37% to 39%": RIGHTS[0] <= rights23 <= RIGHTS[1],
        "both indices are higher in 2023 at p < 0.05":
            all(r["m2023"] > r["m2021"] and r["p"] < ALPHA for r in (mpi, mci)),
    }
    tl = timelines(d21, d23)

    def ag(c, d_=d23):
        return pct(agreement(d_, c))
    target_ns = [c for c in MCE_TARGET if cmp[c]["p"] >= ALPHA]
    printed = [  # (what, computed, printed) at the precision the paper prints
        ("Main 2021 N", f"{len(d21):,}", "1,232"),
        ("Main 2023 N", f"{len(d23):,}", "1,169"),
        ("F1 yes, %", pct(f1_23["Yes"]), "18.8"),
        ("F1 no, %", pct(f1_23["No"]), "42.2"),
        ("F1 not sure, %", pct(f1_23["Not sure"]), "39.0"),
        ("F1, change 2021 to 2023", ns(cmp, ["F1"]), "n.s."),
        ("F2 already, %", pct(tl["2023"]["already"]), "20.0"),
        ("F2 never, %", pct(tl["2023"]["never"]), "10.0"),
        ("F2 already, change p", "< 0.001" if tl["p_already"] < 0.001 else f"{tl['p_already']:.3f}", "< 0.001"),
        ("F2 never, change p", "< 0.001" if tl["p_never"] < 0.001 else f"{tl['p_never']:.3f}", "< 0.001"),
        ("PMC9 legal rights, %", pct(rights23), "37.7"),
        ("PMC9 legal rights 2021, %", pct(rights21), "37.2"),
        ("MCE5 torture wrong, %", ag("MCE5"), "76.4"),
        ("MCE1 respect, %", ag("MCE1"), "71.1"),
        ("PMC10 campaigns, %", ag("PMC10"), "55.8"),
        ("MCE3 physical damage wrong, %", ag("MCE3"), "65.1"),
        ("PMC8 welfare standards, %", ag("PMC8"), "57.5"),
        ("PMC11 fund research, %", ag("PMC11"), "52.0"),
        ("MCE2 moral circle, %", ag("MCE2"), "44.6"),
        ("MCE4 reprogramming wrong, %", ag("MCE4"), "45.2"),
        ("PMC12 demonstration, %", ag("PMC12"), "35.6"),
        ("PMC4 ban robot-human hybrids, %", ag("PMC4"), "67.8"),
        ("PMC3 ban AI-enhanced humans, %", ag("PMC3"), "65.8"),
        ("PMC1 ban sentience in AI, %", ag("PMC1"), "61.5"),
        ("PMC1 2021, %", ag("PMC1", d21), "57.7"),
        ("PMC1 change p", pfmt(cmp["PMC1"]["p"], "0.046"), "0.046"),
        ("PMC7 research safeguards, %", ag("PMC7"), "65.2"),
        ("PMC2 ban welfare-risking applications, %", ag("PMC2"), "56.0"),
        ("PMC6 ban medical experiments, %", ag("PMC6"), "49.2"),
        ("PMC5 ban labour, %", ag("PMC5"), "47.9"),
        ("PMC7, PMC2, PMC6, PMC5 change", ns(cmp, ["PMC7", "PMC2", "PMC6", "PMC5"]), "n.s."),
        ("MP3 analytical 2021", f"{cmp['MP3']['m2021']:.1f}", "62.7"),
        ("MP4 rational 2021", f"{cmp['MP4']['m2021']:.1f}", "51.4"),
        ("MP1 emotions 2021", f"{cmp['MP1']['m2021']:.1f}", "34.3"),
        ("MP2 feelings 2021", f"{cmp['MP2']['m2021']:.1f}", "33.7"),
        ("MP3 analytical", f"{cmp['MP3']['m2023']:.1f}", "67.1"),
        ("MP4 rational", f"{cmp['MP4']['m2023']:.1f}", "53.8"),
        ("MP1 emotions", f"{cmp['MP1']['m2023']:.1f}", "36.8"),
        ("MP2 feelings", f"{cmp['MP2']['m2023']:.1f}", "36.5"),
        ("MP3 change p", pfmt(cmp["MP3"]["p"], "<"), "< 0.001"),
        ("MP4 change p", pfmt(cmp["MP4"]["p"], "0.012"), "0.012"),
        ("MP1 change p", pfmt(cmp["MP1"]["p"], "<"), "< 0.001"),
        ("MP2 change p", pfmt(cmp["MP2"]["p"], "<"), "< 0.001"),
        ("Anth4 simulation emotions", f"{cmp['Anth4']['m2023']:.2f}", "3.22"),
        ("Anth1 robot consciousness", f"{cmp['Anth1']['m2023']:.2f}", "3.23"),
        ("Anth2 computer mind", f"{cmp['Anth2']['m2023']:.2f}", "3.71"),
        ("Anth3 AI intentions", f"{cmp['Anth3']['m2023']:.2f}", "4.04"),
        ("Anth1 to Anth4 change", ns(cmp, ANTH), "n.s."),
        ("MCE30 brain copies", f"{cmp['MCE30']['m2023']:.2f}", "3.43"),
        ("MCE21 human-like companions", f"{cmp['MCE21']['m2023']:.2f}", "3.34"),
        ("MCE23 human-like retail", f"{cmp['MCE23']['m2023']:.2f}", "3.11"),
        ("MCE22 animal-like companions", f"{cmp['MCE22']['m2023']:.2f}", "3.10"),
        ("MCE31 animal copies", f"{cmp['MCE31']['m2023']:.2f}", "3.07"),
        ("MCE29 personal assistants", f"{cmp['MCE29']['m2023']:.2f}", "3.02"),
        ("MCE27 language algorithms", f"{cmp['MCE27']['m2023']:.2f}", "2.90"),
        ("MCE25 factory robots", f"{cmp['MCE25']['m2023']:.2f}", "2.78"),
        ("MCE24 cleaning robots", f"{cmp['MCE24']['m2023']:.2f}", "2.66"),
        ("MCE26 virtual avatars", f"{cmp['MCE26']['m2023']:.2f}", "2.63"),
        ("MCE28 game characters", f"{cmp['MCE28']['m2023']:.2f}", "2.46"),
        ("moral concern index change p", pfmt(mci["p"], "<"), "< 0.001"),
        ("moral concern items not changed", ", ".join(target_ns) or "none", "MCE28"),
        ("MCE1 to MCE9 change", ns(cmp, MCE_GENERAL), "n.s."),
    ]
    matched = [w for w, c, p in printed if c == p]
    differs = [{"what": w, "computed": c, "printed": p} for w, c, p in printed if c != p]

    boot = bootstrap(seed, d)
    controls = controls_known()

    def idx(r):
        return (f"2021 {r['m2021']:.3f} (n {r['n2021']}), 2023 {r['m2023']:.3f} (n {r['n2023']}); t {r['t']:.3f}, "
                f"df {r['df']:.1f}, p {r['p']:.3g}")
    values = {
        "sample": (f"Main 2021 {len(d21)} rows, Main 2023 {len(d23)}, weights summing to {d21['weight'].sum():.3f} "
                   f"and {d23['weight'].sum():.3f}; Supplement 2023 {sup_rows} rows"),
        "sentient_now_2023": round(f1_23["Yes"], 6),
        "sentient_now": ("F1 yes/no/not sure: Main 2023 " + "/".join(pct(f1_23[a]) for a in ANSWERS)
                         + "%, Main 2021 " + "/".join(pct(f1_21[a]) for a in ANSWERS)
                         + "%, Supplement 2023 " + ("/".join(pct(f1_sup[a]) for a in ANSWERS) + "%"
                                                    if isinstance(f1_sup, dict) else f1_sup)
                         + f"; change 2021 to 2023 p {cmp['F1']['p']:.3g}"),
        "legal_rights_2023": round(rights23, 6),
        "legal_rights": (f"PMC9 agreement of those with an opinion: Main 2023 {pct(rights23)}%, Main 2021 "
                         f"{pct(rights21)}%; mean code change p {cmp['PMC9']['p']:.3g}"),
        "mind_perception_p": float(f"{mpi['p']:.4g}"),
        "mind_perception": "index " + idx(mpi),
        "moral_concern_p": float(f"{mci['p']:.4g}"),
        "moral_concern": "index " + idx(mci),
        "timelines": (f"F2 already {pct(tl['2023']['already'])}% (2021 {pct(tl['2021']['already'])}%), never "
                      f"{pct(tl['2023']['never'])}% (2021 {pct(tl['2021']['never'])}%); z test p {tl['p_already']:.3g}"
                      f" and {tl['p_never']:.3g}"),
        "printed_values": (f"{len(matched)} of {len(printed)} as printed"
                           + ("; not: " + ", ".join(x["what"] for x in differs) if differs else ""))[:LIMIT],
        "bootstrap_95ci": (f"share yes {boot['share'][0]:.4f} to {boot['share'][1]:.4f}; legal rights "
                           f"{boot['rights'][0]:.4f} to {boot['rights'][1]:.4f}; index changes MP "
                           f"{boot['mp_change'][0]:.2f} to {boot['mp_change'][1]:.2f}, MC {boot['mc_change'][0]:.3f} "
                           f"to {boot['mc_change'][1]:.3f} ({boot['n']} resamples)"),
        "conditions_met": sum(cond.values()), "conditions_total": len(cond), "test_passed": int(all(cond.values())),
        "controls_passed": sum(controls.values()), "controls_total": len(controls),
        "period_from": min(FIELDWORK[k][0] for k in ("2021", "2023")),
        "period_to": max(FIELDWORK[k][1] for k in ("2021", "2023")),
    }
    out = {k: values[k] for k in OUTPUTS}
    for k, v in out.items():
        if isinstance(v, str) and len(v) > LIMIT:
            raise AssertionError(f"{k}: longer than {LIMIT} characters: {v}")
    detail = {
        "input": {"name": INPUT[0], "sha256": INPUT[1], "members": MEMBERS},
        "conditions": cond, "controls": controls,
        "f1": {"2023": f1_23, "2021": f1_21, "supplement_2023": f1_sup},
        "legal_rights": {"2023": rights23, "2021": rights21},
        "comparisons": cmp, "timelines": tl,
        "agreement_2023": {c: agreement(d23, c) for c in PMC + MCE_GENERAL},
        "agreement_2021": {c: agreement(d21, c) for c in PMC + MCE_GENERAL},
        "printed": [{"what": w, "computed": c, "printed": p} for w, c, p in printed], "differs": differs,
        "bootstrap": boot,
        "versions": {"pandas": pd.__version__, "numpy": np.__version__},
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
        sys.exit(f"aims: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
