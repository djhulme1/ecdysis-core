#!/usr/bin/env python3
"""Jiang et al. 2024: five ITP compounds the Gehan test finds and the log-rank test missed, recomputed from the
program's deposited per-mouse lifespans with the paper's two tests.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:7b9f52a065c49b0c) is from N. Jiang, J.
Gelfond, Q. Liu, R. Strong and J. F. Nelson, "The Gehan test identifies life-extending compounds overlooked by the
log-rank test in the NIA Interventions Testing Program: ...", GeroScience 46, 4533-4541 (2024): "The Gehan test
identified 5 additional compounds, metformin, enalapril, 17-dimethylaminoethylamino-17-demethoxygeldanamycin
hydrochloride (17-DMAG), caffeic acid phenethyl ester (CAPE), and green tea extract (GTE), which significantly
increased survival but were previously missed by the log-rank test."

The test, as registered: see TEST below. The inputs are the claim's data of record, the program's workbooks at the
Mouse Phenome Database (project ITP1), each checked against its SHA-256 and read with the standard library by
itp/rapa.py's reader (its XML parsed as data; nothing in it is run): the 2005 cohort (CAPE at 300 ppm and enalapril at
120 ppm from 4 months), 2007 (GTE at 2,000 ppm from 4 months), 2011 (metformin at 1,000 ppm from 9 months), 2015
(17-DMAG at 30 ppm from 6 months) and 2017 (1,3-butanediol at 100,000 ppm from 6 months, beside the test). Every rule
below was fixed before any age or status in the workbooks was read (only their headers and design columns were looked
at: the groups, doses, starting ages, sites and sexes).

The paper's Methods: "The differences in right censored survival were tested using the log-rank and
Gehan-Breslow-Wilcoxon test with the Peto modification [23]. For each gender, the ITP data was pooled from three sites
with stratification by site. The log-rank test was performed in the same way as in the original publications by the
Interventions Testing Program." It used R's survival package, whose survdiff with rho = 1 is "the Peto & Peto
modification of the Gehan-Wilcoxon test".

1. The mice. Every row must be of population UM-HET3 and its workbook's cohort, at site TJL, UM or UT, of sex f or m,
   with a whole number of days as its age, and either dead (status "dead", dead 1) or removed (status "removed", dead
   0); each cohort's groups must be the ones its workbook holds (GROUPS below), and the rows of the groups the check
   uses must carry the design the workbook gives them (DESIGN: dose in ppm, starting age in months; the controls' age
   is an empty cell). Removed mice are censored at their age at removal, as the program's tests censor them.
2. The tests, each for one agent and sex against the same cohort's controls of that sex, the three sites as strata,
   two-sided: the log-rank test (itp/cana.py's, the program's own), and the G-rho test of Harrington and Fleming with
   rho = 1, as R's survdiff computes it: within each site, at each age at which a mouse of either group died, the
   weight w is the Kaplan-Meier estimate of the two groups together just before that age; the agent's observed less
   expected deaths, each weighted by w, and their variance, each term weighted by w^2 (the hypergeometric variance), are
   summed over ages and sites, and p = P(chi-square with one degree of freedom > (O - E)^2 / V). The direction is the
   sign of O - E: below zero, the agent's mice died fewer than expected, so lived longer.
3. The test's five conditions, one per compound (metformin, enalapril and 17-DMAG in males; CAPE and GTE in females):
   its Gehan p below 0.05, its O - E below zero, and its log-rank p at least 0.05. test_passed is 1 if all five hold.
4. Beside the test, none of it counted.
   - 1,3-butanediol: the males' Gehan and log-rank p (the paper: 0.0248 and 0.1097), and the females' (the paper: the
     Gehan p 0.1632; its original report, a significant log-rank test).
   - Table 1 as printed, for its six rows: the log-rank and Gehan p (matched when the computed p rounds to the printed
     four decimals) and the median lifespan change (matched when the change of the medians of the pooled dead, removed
     mice left out, rounds to the printed whole percent).
   - Figure 1's group sizes (CAPE 147 and 289 controls; GTE 129 and 275; metformin 148 and 294; enalapril 170 and 357;
     17-DMAG 152 and 264; 1,3-butanediol 145 and 285) against the mice in the data, all and dead only.
   - The Results' p for each compound against Table 1's Gehan p: the text gives enalapril's as 0.0343, Table 1 its
     Gehan p as 0.0460 and its Z-test p as 0.0343.
   - Two other weightings of the same test: Gehan and Breslow's (w the number at risk) and Peto and Prentice's (w the
     product of 1 - d/(n + 1) over earlier ages), for the six rows.
   - What it cannot recompute: the Methods' adjustment of the p values to a 5% false discovery rate over 132 trials,
     which needs the other 126 trials (the paper's Tables S1 and S2, in a Word file), and the Z-tests of proportional
     hazards.

Controls (controls_passed counts those that behave as stated; the run stops if any fails): every file is the pinned
one and holds the expected number of rows, each as rule 1 requires; on seed-drawn censored samples in three strata,
the module's G-rho test with rho = 0 gives itp/cana.py's log-rank p, and with rho = 0, rho = 1 and Gehan and
Breslow's weights it gives statsmodels 0.14's survdiff p (weight_type None, "fh" with fh_p = 1, and "gb") to 1e-9; for
each compound, swapping the two groups gives the same p and the opposite O - E, and reading the rows in reverse order
gives the same p; and the 2011 cohort's control males against themselves give p = 1 in both tests.

What it cannot check: the data as the paper analysed them, from which the deposit may differ (Figure 1's group sizes
are compared beside); and the causes of death.

Writes results/outputs.json (the values a receipt carries) and results/detail.json (every value computed).
Run with: python3 itp/gehan2024.py
"""

import hashlib
import importlib.util
import json
import math
import os
import re
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def _load(name, file):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, file))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


rapa = _load("itp_rapa", "rapa.py")
cana = _load("itp_cana", "cana.py")

INPUTS = {
    "C2005": ("itp_c2005_lifespan.xlsx", "0b17afe4bf172d1fb08dbe382f8f6abdddd2b6172ae5d1cf4b5678415cc1c019", 1974),
    "C2007": ("ITP_C2007_Lifespan.xlsx", "7f58576df8966197c49f61aedd8c812305e5a632dfe5416d1ac93275153f6f4d", 2008),
    "C2011": ("ITP_C2011_Lifespan.xlsx", "509a0c1a30f92ba6f590ec7d669df9b88c44f47692164a7f24e8c83efa4e47e1", 2082),
    "C2015": ("ITP_C2015_Lifespan.xlsx", "bc0e6f119e950cf35ac67e60cad1df4207cabf7028328840bbe5a54b13e4080a", 2624),
    "C2017": ("ITP_C2017_Lifespan.xlsx", "1f1ab41e6497c92bc926ee9ba63f617a239549745ecd2ceede7932fdbf36dc1f", 2916),
}
POPULATION = "UM-HET3"
SITES, SEXES = ("TJL", "UM", "UT"), ("m", "f")
GROUPS = {
    "C2005": {"Control", "CAPE_lo", "CAPE_hi", "Enal", "Rapa"},
    "C2007": {"Control", "Cur", "GTE", "MCTO", "OAA", "Res"},
    "C2011": {"Control", "17aE2", "Met", "MetRapa", "Prot", "UDCA"},
    "C2015": {"Control", "DMAG", "Min", "MitoQ", "bGPA", "rapa_hi_continuous", "rapa_hi_cycle", "rapa_hi_start_stop"},
    "C2017": {"Control", "BD", "Capt", "Leu", "PB125", "RaAc_16", "RaAc_9", "Sul", "Syr"},
}
DESIGN = {"Control": ("0", None), "CAPE_hi": ("300", "4"), "Enal": ("120", "4"), "GTE": ("2000", "4"),
          "Met": ("1000", "9"), "DMAG": ("30", "6"), "BD": ("100000", "6")}
CASES = (("metformin", "C2011", "Met", "m"), ("enalapril", "C2005", "Enal", "m"), ("17-DMAG", "C2015", "DMAG", "m"),
         ("CAPE", "C2005", "CAPE_hi", "f"), ("GTE", "C2007", "GTE", "f"))
BESIDE = (("1,3-butanediol", "C2017", "BD", "m"), ("1,3-butanediol females", "C2017", "BD", "f"))
ALPHA = 0.05
# Table 1 as printed: (log-rank p, Gehan p, median change in %); Figure 1's (treated, control) sizes; the Results' p.
TABLE1 = {"GTE": (0.3686, 0.0344, 7), "metformin": (0.3477, 0.0495, 8), "enalapril": (0.2200, 0.0460, 7),
          "CAPE": (0.0665, 0.0481, 5), "17-DMAG": (0.1173, 0.0321, 7), "1,3-butanediol": (0.1097, 0.0248, 9)}
FIG1 = {"CAPE": (147, 289), "GTE": (129, 275), "metformin": (148, 294), "enalapril": (170, 357), "17-DMAG": (152, 264),
        "1,3-butanediol": (145, 285)}
TEXT_P = {"CAPE": 0.0481, "GTE": 0.0344, "metformin": 0.0495, "enalapril": 0.0343, "17-DMAG": 0.0321,
          "1,3-butanediol": 0.0248}
BD_FEMALE_GEHAN = 0.1632
LIMIT = 200
TEST = ("Refuted if, in the program's deposited per-mouse lifespans (Mouse Phenome Database: cohorts C2005, C2007, "
        "C2011 and C2015), any of metformin, enalapril or 17-DMAG in males, or CAPE or GTE in females, at the dose and "
        "starting age of the paper's Table 1, against its cohort's controls of that sex, stratified by site with removed "
        "mice censored, has a two-sided Gehan–Breslow–Wilcoxon p with Peto's modification (R's survdiff, rho = 1) of "
        "0.05 or more, or no fewer deaths than expected, or a log-rank p below 0.05.")
OUTPUTS = ("mice", "gehan_met", "gehan_enal", "gehan_dmag", "gehan_cape", "gehan_gte", "logrank_met", "logrank_enal",
           "logrank_dmag", "logrank_cape", "logrank_gte", "directions", "butanediol", "table1", "medians", "fig1",
           "text_p", "weightings", "conditions_met", "conditions_total", "test_passed", "controls_passed",
           "controls_total")
SHORT = {"metformin": "met", "enalapril": "enal", "17-DMAG": "dmag", "CAPE": "cape", "GTE": "gte",
         "1,3-butanediol": "bd"}


class Refused(Exception):
    pass


# ---------------------------------------------------------------- the mice (rule 1)

def mice_from_rows(rows, cohort):
    """{(group, site, sex): [(age, died)]} for one cohort, every row checked against rule 1."""
    out = {(g, s, x): [] for g in GROUPS[cohort] for s in SITES for x in SEXES}
    for i, r in enumerate(rows, start=2):
        if r.get("population") != POPULATION or r.get("cohort") != cohort:
            raise Refused(f"{cohort} row {i}: population or cohort not as expected")
        if r.get("site") not in SITES or r.get("sex") not in SEXES:
            raise Refused(f"{cohort} row {i}: site or sex not as expected")
        age = r.get("age") or ""
        if not re.fullmatch(r"[0-9]+(\.0+)?", age):
            raise Refused(f"{cohort} row {i}: age {age!r} is not a whole number of days")
        state = (r.get("status"), r.get("dead"))
        if state not in (("dead", "1"), ("removed", "0")):
            raise Refused(f"{cohort} row {i}: status and dead disagree: {state}")
        g = r.get("group")
        if g not in GROUPS[cohort]:
            raise Refused(f"{cohort} row {i}: group {g!r} is not one of the cohort's")
        if g in DESIGN and (r.get("dose"), r.get("age_initiation")) != DESIGN[g]:
            raise Refused(f"{cohort} row {i}: group {g} carries {(r.get('dose'), r.get('age_initiation'))}")
        out[(g, r["site"], r["sex"])].append((int(float(age)), state[0] == "dead"))
    return out


def strata_of(mice, group, sex):
    return [(mice[("Control", s, sex)], mice[(group, s, sex)]) for s in SITES]


# ---------------------------------------------------------------- the tests (rule 2)

def weighted_test(strata, weighting):
    """Two-sided p and O - E of the second group of each (a, b) stratum pair, the weights by name: "logrank" (1),
    "fh1" (the pooled left-continuous Kaplan-Meier estimate, R's survdiff rho = 1), "gb" (the number at risk) or "pp"
    (Peto and Prentice's product of 1 - d/(n + 1) over earlier ages)."""
    o_minus_e = var = 0.0
    for a, b in strata:
        both = a + b
        times = sorted({t for t, _ in both})
        km = pp = 1.0
        for t in times:
            n = sum(1 for x, _ in both if x >= t)
            d = sum(1 for x, died in both if x == t and died)
            if d == 0:
                continue
            nb = sum(1 for x, _ in b if x >= t)
            db = sum(1 for x, died in b if x == t and died)
            w = {"logrank": 1.0, "fh1": km, "gb": float(n), "pp": pp}[weighting]
            o_minus_e += w * (db - d * nb / n)
            if n > 1:
                var += w * w * d * (nb / n) * (1 - nb / n) * (n - d) / (n - 1)
            km *= (n - d) / n
            pp *= 1 - d / (n + 1)
    if var <= 0:
        return 1.0, o_minus_e
    return math.erfc(math.sqrt(o_minus_e * o_minus_e / var / 2)), o_minus_e


def logrank(strata):
    return cana.logrank_strat_p(strata)


# ---------------------------------------------------------------- beside (rule 4)

def dead_median(ms):
    return statistics.median([t for t, d in ms if d])


def pooled(mice, group, sex):
    return [m for s in SITES for m in mice[(group, s, sex)]]


def rounds_to(x, printed, places):
    return abs(round(x, places) - printed) < 10 ** (-places) / 2


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
    """Seed-drawn censored samples: three strata, two groups, ages with ties, about one in five censored."""
    st = Stream(seed, f"gehan/synthetic/{k}")
    strata = []
    for s in range(3):
        pair = []
        for g in range(2):
            size = 20 + st.ints(1, 0, 30)[0]
            ages = st.ints(size, 300, 1200)
            if g == 1:
                ages = [a + st.ints(1, 0, 80)[0] for a in ages]
            flags = st.ints(size, 0, 4)
            pair.append([(a // 7 * 7, f != 0) for a, f in zip(ages, flags)])
        strata.append(tuple(pair))
    return strata


def statsmodels_p(strata, weight_type, **kw):
    import numpy as np
    from statsmodels.duration.survfunc import survdiff
    time, status, group, stratum = [], [], [], []
    for s, (a, b) in enumerate(strata):
        for g, ms in ((0, a), (1, b)):
            for t, d in ms:
                time.append(t)
                status.append(1 if d else 0)
                group.append(g)
                stratum.append(s)
    chi2, p = survdiff(np.array(time, float), np.array(status, float), np.array(group), weight_type=weight_type,
                       strata=np.array(stratum), **kw)
    return float(p)


def controls_run(seed, cohorts, raw_rows, statsmodels_ok=True):
    ctl = {}
    ctl["every file pinned, with its expected rows, each as rule 1 requires"] = all(
        len(raw_rows[c]) == INPUTS[c][2] for c in INPUTS)
    agree_lr = agree_sm = True
    for k in range(5):
        strata = synthetic(seed, k)
        p0, _ = weighted_test(strata, "logrank")
        agree_lr &= abs(p0 - logrank(strata)) < 1e-12
        if statsmodels_ok:
            agree_sm &= abs(p0 - statsmodels_p(strata, None)) < 1e-9
            agree_sm &= abs(weighted_test(strata, "fh1")[0] - statsmodels_p(strata, "fh", fh_p=1)) < 1e-9
            agree_sm &= abs(weighted_test(strata, "gb")[0] - statsmodels_p(strata, "gb")) < 1e-9
    ctl["the G-rho test with rho = 0 gives the program's log-rank p"] = agree_lr
    ctl["rho = 0, rho = 1 and Gehan-Breslow weights give statsmodels' survdiff p"] = agree_sm
    sym = True
    for name, cohort, group, sex in CASES:
        mice = cohorts[cohort]
        s = strata_of(mice, group, sex)
        swapped = [(b, a) for a, b in s]
        rev = [(list(reversed(a)), list(reversed(b))) for a, b in s]
        for w in ("logrank", "fh1"):
            p, oe = weighted_test(s, w)
            p2, oe2 = weighted_test(swapped, w)
            p3, _ = weighted_test(rev, w)
            sym &= abs(p - p2) < 1e-12 and abs(oe + oe2) < 1e-9 and abs(p - p3) < 1e-12
    ctl["swapping the groups and reversing the rows leave each p"] = sym
    same = strata_of(cohorts["C2011"], "Control", "m")
    ctl["the 2011 control males against themselves give p = 1"] = (
        weighted_test(same, "fh1")[0] == 1.0 and abs(logrank(same) - 1.0) < 1e-12)
    return ctl


# ---------------------------------------------------------------- run

def run(seed, inputs="inputs", results="results"):
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        raise Refused("the seed must be 64 hex characters")
    raw_rows, cohorts = {}, {}
    for c, (name, sha, _) in INPUTS.items():
        raw_rows[c] = rapa.read_rows(os.path.join(inputs, name), sha)
        cohorts[c] = mice_from_rows(raw_rows[c], c)

    ctl = controls_run(seed, cohorts, raw_rows)
    if not all(ctl.values()):
        raise AssertionError(f"a control failed: {[k for k, v in ctl.items() if not v]}")

    res = {}
    for name, cohort, group, sex in CASES + BESIDE:
        mice = cohorts[cohort]
        s = strata_of(mice, group, sex)
        g_p, g_oe = weighted_test(s, "fh1")
        l_p = logrank(s)
        _, l_oe = weighted_test(s, "logrank")
        trt, con = pooled(mice, group, sex), pooled(mice, "Control", sex)
        res[name] = {"gehan_p": g_p, "gehan_oe": g_oe, "logrank_p": l_p, "logrank_oe": l_oe,
                     "gb_p": weighted_test(s, "gb")[0], "pp_p": weighted_test(s, "pp")[0],
                     "n": (len(trt), len(con)), "dead": (sum(1 for _, d in trt if d), sum(1 for _, d in con if d)),
                     "median": (dead_median(trt), dead_median(con))}
    cond = {f"{name}: Gehan p below 0.05, fewer deaths than expected, log-rank p at least 0.05":
            res[name]["gehan_p"] < ALPHA and res[name]["gehan_oe"] < 0 and res[name]["logrank_p"] >= ALPHA
            for name, _, _, _ in CASES}

    rows6 = [n for n, _, _, _ in CASES] + ["1,3-butanediol"]
    t_lr = sum(rounds_to(res[n]["logrank_p"], TABLE1[n][0], 4) for n in rows6)
    t_g = sum(rounds_to(res[n]["gehan_p"], TABLE1[n][1], 4) for n in rows6)
    changes = {n: 100 * (res[n]["median"][0] / res[n]["median"][1] - 1) for n in rows6}
    t_m = sum(round(changes[n]) == TABLE1[n][2] for n in rows6)
    fig_all = sum(res[n]["n"] == FIG1[n] for n in rows6)
    fig_dead = sum(res[n]["dead"] == FIG1[n] for n in rows6)

    def p4(x):
        return f"{x:.4f}"

    bd, bdf = res["1,3-butanediol"], res["1,3-butanediol females"]
    values = {
        "mice": ", ".join(f"{c} {len(raw_rows[c])}" for c in INPUTS) + " mice, every row as rule 1 requires",
        "conditions_met": sum(cond.values()), "conditions_total": len(cond), "test_passed": int(all(cond.values())),
        "directions": "Gehan O - E: " + ", ".join(f"{SHORT[n]} {res[n]['gehan_oe']:.2f}" for n, _, _, _ in CASES),
        "butanediol": (f"males: Gehan {p4(bd['gehan_p'])}, log-rank {p4(bd['logrank_p'])} (printed 0.0248, 0.1097); "
                       f"females: Gehan {p4(bdf['gehan_p'])} (printed 0.1632), log-rank {p4(bdf['logrank_p'])}"),
        "table1": f"of six rows: log-rank p as printed {t_lr}, Gehan p {t_g}, median change {t_m}",
        "medians": "median change, pooled dead: " + ", ".join(f"{SHORT[n]} {changes[n]:+.1f}%" for n in rows6),
        "fig1": (f"Figure 1's sizes: as all mice {fig_all} of 6, as the dead {fig_dead} of 6; data, all: "
                 + ", ".join(f"{SHORT[n]} {res[n]['n'][0]}/{res[n]['n'][1]}" for n in rows6)),
        "text_p": "Results' p vs Gehan p: " + ", ".join(
            f"{SHORT[n]} {TEXT_P[n]} vs {p4(res[n]['gehan_p'])}" for n in rows6),
        "weightings": "Gehan-Breslow, Peto-Prentice p: " + ", ".join(
            f"{SHORT[n]} {p4(res[n]['gb_p'])}, {p4(res[n]['pp_p'])}" for n in rows6),
        "controls_passed": sum(ctl.values()), "controls_total": len(ctl),
    }
    for n, _, _, _ in CASES:
        values[f"gehan_{SHORT[n]}"] = res[n]["gehan_p"]
        values[f"logrank_{SHORT[n]}"] = res[n]["logrank_p"]
    out = {k: values[k] for k in OUTPUTS}
    for k, v in out.items():
        if isinstance(v, str) and len(v) > LIMIT:
            raise AssertionError(f"{k}: longer than {LIMIT} characters: {v}")
    detail = {"inputs": {c: {"name": INPUTS[c][0], "sha256": INPUTS[c][1], "rows": len(raw_rows[c])} for c in INPUTS},
              "conditions": cond, "controls": ctl, "results": res, "test": TEST}
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
        sys.exit(f"gehan2024: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
