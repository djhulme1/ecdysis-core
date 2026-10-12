#!/usr/bin/env python3
"""NDGA and aspirin in the ITP's first cohort (2004), recomputed from the per-mouse data with the paper's own test.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:6c6aee7d6ede468c) is from Strong et al.,
"Nordihydroguaiaretic acid and aspirin increase lifespan of genetically heterogeneous male mice", Aging Cell 7(5),
641-650 (2008): "Pooling data from all three sites, a log-rank test showed that both NDGA (p = 0.0006) and aspirin
(p = 0.01) led to increased lifespan of male mice."

Its registered test: refuted if, in the cohort's deposited per-mouse lifespans (the ITP's 2004 cohort of UM-HET3 males
at its three sites: controls, NDGA at 2,500 ppm from 9 months, aspirin at 21 ppm from 4 months), the two-tailed
log-rank test stratified by site with removed mice censored at removal, as the paper tests it, gives p of 0.05 or more
for NDGA or for aspirin against the controls, or if either drug's males show more deaths than the test expects of them
(observed above expected).

The input is the program's deposited dataset for the cohort (the Mouse Phenome Database, project ITP1):
ITP_C2004_Lifespan.xlsx (file id 834), the claim's data of record, checked against its SHA-256 and read with the
standard library by itp/rapa.py's reader (its XML parsed as data; nothing in it is run). The two-group statistics are
itp/cana.py's. Every rule below was fixed before any seed existed; the seed is not used, as nothing here is random.

1. The mice. Every row must be of population UM-HET3 and cohort C2004, at site TJL, UM or UT, of sex f or m, with a
   whole number of days as its age, and either dead (status "dead", dead 1) or removed (status "removed", dead 0); its
   group must be one of the cohort's five, carrying its design in the workbook's own columns (DESIGN below: the dose
   in ppm and the starting age in months, empty for the controls), as the paper's Methods give them.
2. The paper's test (its Methods: "the two-tailed log-rank test at p < 0.05, stratified by test site, with censored
   mice included up until their date of removal"): itp/cana.py's stratified log-rank test, each drug's males against
   the cohort's control males. Its direction is the treated males' observed deaths less those the test expects of
   them, summed over the sites' death times.
3. The test's four conditions: for NDGA and for aspirin, p below 0.05, and observed deaths not above expected.
   test_passed is 1 if all four hold.
4. Beside the test, each against what the paper prints:
   - the two p values, to the printed number's decimals (0.0006 and 0.01);
   - each site's p (Results: NDGA 0.003 at UT, 0.09 at TJL and no significant effect at UM; aspirin 0.04 at UT,
     0.051 at TJL and not at UM), "no significant effect" read as p of 0.05 or more;
   - the null results: no drug significant in females, and neither NFP nor 4-OH-PBN in males (six tests);
   - the male medians of the dead, by two rules, the three sites pooled and the mean of the three site medians, with
     the printed 786, 881 and 849 days (the pooled rule's count is reported);
   - the Wang-Allison test as itp/cana.py takes it (each site's cut at R's default 90th percentile of both groups'
     dead, the tables summed, Fisher's exact test), with the paper's counts (30 of 350 controls and 22 of 168 treated
     above the cut for NDGA, p = 0.12; 8.9% and 13.1% for aspirin, p = 0.16);
   - the difference among the three sites in the controls' survival (the paper: p = 0.0001 in males, none in
     females), by the log-rank test for three groups (two degrees of freedom);
   - Table 1, the control mice's median age at death and number of dead at each site and in each sex (12 numbers).

What it cannot check: the cohort beyond the workbook (ages are as the ITP recorded them; why a mouse was removed is not
in it); and the data as the paper analysed them in 2008, from which the deposit differs in places (Table 1's female
count at UM, one NDGA male among the dead), which the check reports and does not explain.

Writes results/outputs.json (the 19 values a receipt carries) and results/detail.json (every value computed).
"""

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
    spec.loader.exec_module(module)
    return module


rapa = _load("itp_rapa", "rapa.py")
cana = _load("itp_cana", "cana.py")

INPUT = ("ITP_C2004_Lifespan.xlsx", "4e8d309f146a59c2c6bc03d68b8bf08e01ee789130047aff24b153aaa1bab948")
POPULATION, COHORT = "UM-HET3", "C2004"
SITES, SEXES = ("TJL", "UM", "UT"), ("m", "f")
GROUPS = ("Control", "NDGA", "Aspirin", "NFP", "4-OH-PBN")
DRUGS = ("NDGA", "Aspirin")
DESIGN = {"Control": ("0", None), "NDGA": ("2500", "9"), "Aspirin": ("21", "4"), "NFP": ("200", "4"),
          "4-OH-PBN": ("350", "4")}
ALPHA = 0.05
LIMIT = 200

PRINTED_P = {"NDGA": "0.0006", "Aspirin": "0.01"}
PRINTED_SITE_P = {("NDGA", "UT"): "0.003", ("NDGA", "TJL"): "0.09", ("NDGA", "UM"): "ns",
                  ("Aspirin", "UT"): "0.04", ("Aspirin", "TJL"): "0.051", ("Aspirin", "UM"): "ns"}
NULLS = (("NDGA", "f"), ("Aspirin", "f"), ("NFP", "f"), ("4-OH-PBN", "f"), ("NFP", "m"), ("4-OH-PBN", "m"))
PRINTED_MEDIANS = {"Control": 786, "NDGA": 881, "Aspirin": 849}
PRINTED_WA = {"NDGA": "30 of 350 controls, 22 of 168 treated; p = 0.12",
              "Aspirin": "8.9% of controls, 13.1% of treated; p = 0.16"}
# Table 1 as printed: (site, sex) -> (median, N) of the control mice, in days.
TABLE1 = {("TJL", "f"): (858, 93), ("UM", "f"): (909, 86), ("UT", "f"): (876, 96),
          ("TJL", "m"): (781, 125), ("UM", "m"): (876, 106), ("UT", "m"): (739, 119)}
OUTPUTS = ("n_m", "logrank_p_ndga", "logrank_p_aspirin", "oe_ndga", "oe_aspirin", "p_as_printed", "sites_p",
           "sites_as_printed", "nulls_p", "nulls_as_printed", "medians_m", "medians_as_printed", "wa_ndga",
           "wa_aspirin", "sites_ctl_p_m", "sites_ctl_p_f", "table1_matched", "conditions_met", "test_passed")


class Refused(Exception):
    pass


def mice_from_rows(rows):
    """{(group, site, sex): [(age, died)]} for every group; every row checked against rule 1."""
    out = {(g, s, x): [] for g in GROUPS for s in SITES for x in SEXES}
    for i, r in enumerate(rows, start=2):
        if r.get("population") != POPULATION or r.get("cohort") != COHORT:
            raise Refused(f"row {i}: population or cohort not as expected: {r}")
        if r.get("site") not in SITES or r.get("sex") not in SEXES:
            raise Refused(f"row {i}: site or sex not as expected: {r}")
        age = r.get("age") or ""
        if not re.fullmatch(r"[0-9]+(\.0+)?", age):
            raise Refused(f"row {i}: age {age!r} is not a whole number of days")
        state = (r.get("status"), r.get("dead"))
        if state not in (("dead", "1"), ("removed", "0")):
            raise Refused(f"row {i}: status and dead disagree: {state}")
        g = r.get("group")
        if g not in GROUPS:
            raise Refused(f"row {i}: group {g!r} is not one of the cohort's")
        design = (r.get("dose"), r.get("age_initiation") or None)
        if design != DESIGN[g]:
            raise Refused(f"row {i}: group {g} carries {design}, not {DESIGN[g]}")
        out[(g, r["site"], r["sex"])].append((int(float(age)), state[0] == "dead"))
    return out


def strata(mice, group, sex, sites=SITES):
    return [(mice[("Control", s, sex)], mice[(group, s, sex)]) for s in sites]


def observed_minus_expected(pairs):
    """The second group's observed deaths less those the log-rank test expects of it, over the strata's death times."""
    total = 0.0
    for a, b in pairs:
        for t in sorted({t for t, d in a + b if d}):
            na = sum(1 for x, _ in a if x >= t)
            nb = sum(1 for x, _ in b if x >= t)
            db = sum(1 for x, d in b if x == t and d)
            d = sum(1 for x, dd in a if x == t and dd) + db
            n = na + nb
            if n < 2:
                continue
            total += db - d * nb / n
    return total


def logrank_k_p(groups):
    """The log-rank test of k groups (lists of (age, died)), chi-square on k - 1 degrees of freedom; p for k = 2 or 3."""
    k = len(groups)
    u = [0.0] * k
    v = [[0.0] * k for _ in range(k)]
    for t in sorted({t for g in groups for t, d in g if d}):
        n_j = [sum(1 for x, _ in g if x >= t) for g in groups]
        d_j = [sum(1 for x, d in g if x == t and d) for g in groups]
        n, d = sum(n_j), sum(d_j)
        if n < 2:
            continue
        for j in range(k):
            u[j] += d_j[j] - d * n_j[j] / n
            for m in range(k):
                v[j][m] += d * (n - d) / (n - 1) * (n_j[j] / n) * ((j == m) - n_j[m] / n)
    if k == 2:
        return math.erfc(math.sqrt(u[0] * u[0] / v[0][0] / 2))
    if k == 3:
        a, b, c, e = v[0][0], v[0][1], v[1][0], v[1][1]
        det = a * e - b * c
        chi2 = (u[0] * (e * u[0] - b * u[1]) + u[1] * (a * u[1] - c * u[0])) / det
        return math.exp(-chi2 / 2)
    raise ValueError("k must be 2 or 3")


def as_printed(p, printed):
    """Whether p is what the paper prints: to the printed number's decimals, or p >= 0.05 for "ns"."""
    if printed == "ns":
        return p >= ALPHA
    decimals = len(printed.split(".")[1])
    return f"{p:.{decimals}f}" == printed


def dead_of(ms):
    return [t for t, d in ms if d]


def pooled(mice, group, sex):
    return [m for s in SITES for m in mice[(group, s, sex)]]


def medians(mice, group, sex):
    """(the median of the three sites' dead pooled, the mean of the three site medians)."""
    pool = statistics.median(dead_of(pooled(mice, group, sex)))
    sites = sum(statistics.median(dead_of(mice[(group, s, sex)])) for s in SITES) / 3
    return pool, sites


def conditions(ps, oes):
    """Rule 3, by name, from the male log-rank p and observed-minus-expected deaths of NDGA and aspirin."""
    return {
        "NDGA: log-rank p below 0.05": ps["NDGA"] < ALPHA,
        "NDGA: observed deaths not above expected": oes["NDGA"] <= 0,
        "aspirin: log-rank p below 0.05": ps["Aspirin"] < ALPHA,
        "aspirin: observed deaths not above expected": oes["Aspirin"] <= 0,
    }


def fmt(x):
    return str(int(x)) if float(x).is_integer() else f"{x:.1f}"


def sig(p):
    return float(f"{p:.4g}")


def run(seed, inputs="inputs", results="results"):
    rows = rapa.read_rows(os.path.join(inputs, INPUT[0]), INPUT[1])
    mice = mice_from_rows(rows)
    ps = {g: cana.logrank_strat_p(strata(mice, g, "m")) for g in DRUGS}
    oes = {g: observed_minus_expected(strata(mice, g, "m")) for g in DRUGS}
    cond = conditions(ps, oes)
    site_ps = {(g, s): cana.logrank_strat_p(strata(mice, g, "m", (s,))) for g in DRUGS for s in SITES}
    null_ps = {(g, x): cana.logrank_strat_p(strata(mice, g, x)) for g, x in NULLS}
    meds = {g: medians(mice, g, "m") for g in ("Control",) + DRUGS}
    wa = {g: cana.wang_allison(strata(mice, g, "m")) for g in DRUGS}
    site_ctl = {x: logrank_k_p([mice[("Control", s, x)] for s in SITES]) for x in SEXES}
    t1 = {}
    for (s, x), (med, n) in TABLE1.items():
        dead = dead_of(mice[("Control", s, x)])
        t1[f"{s} {x}"] = {"printed": [med, n], "data": [statistics.median(dead), len(dead)]}
    t1_hits = sum((cana.half_up(v["data"][0]) == v["printed"][0]) + (v["data"][1] == v["printed"][1])
                  for v in t1.values())
    counts = {g: (len(pooled(mice, g, "m")), len(dead_of(pooled(mice, g, "m")))) for g in ("Control",) + DRUGS}

    def wa_text(g):
        (ca, cb), (ta, tb) = wa[g][0]
        return f"controls {ca} of {ca + cb} above, {g} {ta} of {ta + tb}; p {sig(wa[g][1])} (printed: {PRINTED_WA[g]})"

    values = {
        "n_m": "; ".join(f"{g} {counts[g][0]} ({counts[g][1]} dead)" for g in counts),
        "logrank_p_ndga": sig(ps["NDGA"]), "logrank_p_aspirin": sig(ps["Aspirin"]),
        "oe_ndga": round(oes["NDGA"], 2), "oe_aspirin": round(oes["Aspirin"], 2),
        "p_as_printed": sum(as_printed(ps[g], PRINTED_P[g]) for g in DRUGS),
        "sites_p": "; ".join(f"{g} " + ", ".join(f"{s} {sig(site_ps[(g, s)])}" for s in SITES) for g in DRUGS),
        "sites_as_printed": sum(as_printed(site_ps[k], v) for k, v in PRINTED_SITE_P.items()),
        "nulls_p": "; ".join(f"{g} {x} {sig(null_ps[(g, x)])}" for g, x in NULLS),
        "nulls_as_printed": sum(1 for v in null_ps.values() if v >= ALPHA),
        "medians_m": ", ".join(f"{g} {fmt(meds[g][0])}" for g in meds) + " (dead pooled); "
                     + ", ".join(f"{g} {meds[g][1]:.1f}" for g in meds) + " (site means)",
        "medians_as_printed": sum(1 for g in meds if cana.half_up(meds[g][0]) == PRINTED_MEDIANS[g]),
        "wa_ndga": wa_text("NDGA"), "wa_aspirin": wa_text("Aspirin"),
        "sites_ctl_p_m": sig(site_ctl["m"]), "sites_ctl_p_f": sig(site_ctl["f"]),
        "table1_matched": f"{t1_hits} of {2 * len(TABLE1)}",
        "conditions_met": sum(cond.values()),
        "test_passed": int(all(cond.values())),
    }
    out = {k: values[k] for k in OUTPUTS}
    for k, v in out.items():
        if isinstance(v, str) and len(v) > LIMIT:
            raise AssertionError(f"{k}: longer than {LIMIT} characters")
    detail = {
        "input": {"name": INPUT[0], "sha256": INPUT[1], "rows": len(rows)},
        "counts": {f"{g} {s} {x}": [len(mice[(g, s, x)]), len(dead_of(mice[(g, s, x)]))]
                   for g in GROUPS for s in SITES for x in SEXES},
        "conditions": cond, "logrank": ps, "observed_minus_expected": oes,
        "sites": {f"{g} {s}": {"p": site_ps[(g, s)], "printed": PRINTED_SITE_P[(g, s)]} for g, s in site_ps},
        "nulls": {f"{g} {x}": null_ps[(g, x)] for g, x in NULLS},
        "medians": {g: {"dead_pooled": meds[g][0], "site_means": meds[g][1], "printed": PRINTED_MEDIANS[g]}
                    for g in meds},
        "wang_allison": {g: {"table": wa[g][0], "p": wa[g][1], "printed": PRINTED_WA[g]} for g in DRUGS},
        "sites_controls": site_ctl, "table1": t1,
    }
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
        sys.exit(f"strong2008: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
