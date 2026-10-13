#!/usr/bin/env python3
"""Rapamycin from 9 months in the ITP's 2006 cohort: longer life, and longer maximum life, at each of three sites.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:01247e22c31f6c76) is from Miller et al.,
"Rapamycin, But Not Resveratrol or Simvastatin, Extends Life Span of Genetically Heterogeneous Mice", J. Gerontol. A
66A(2), 191-201 (2011): "Rapamycin was administered in food to genetically heterogeneous mice from the age of 9 months
and produced significant increases in life span, including maximum life span, at each of three test sites. Median
survival was extended by an average of 10% in males and 18% in females."

Its registered test: refuted if, in the cohort's deposited per-mouse lifespans (the ITP's 2006 cohort of UM-HET3 mice at
its three sites: controls and rapamycin at 14 ppm from 9 months), for either sex at any site the log-rank test of
rapamycin against the controls (removed mice censored at removal) or the Wang-Allison test (Fisher's exact test on each
group's mice alive past the 90th percentile age of both groups' dead) gives p of 0.05 or more, or the mean of the three
site medians of the dead rises by less than 5% in males or 9% in females (half the 10% and 18% printed).

The input is the program's deposited dataset for the cohort (the Mouse Phenome Database, project ITP1):
ITP_C2006_Lifespan.xlsx (file 827, also served as 823), the claim's data of record, checked against its SHA-256 and read
with the standard library by itp/rapa.py's reader (its XML parsed as data; nothing in it is run). The statistics are
itp/cana.py's and itp/strong2008.py's. Every rule below was fixed before any seed existed; the seed is not used, as
nothing here is random.

1. The mice. Every row must be of population UM-HET3 and cohort C2006, at site TJL, UM or UT, of sex f or m, with a
   whole number of days as its age, and either dead (status "dead", dead 1) or removed (status "removed", dead 0); its
   group must be one of the cohort's six, carrying its design in the workbook's own columns (DESIGN below: the dose in
   ppm and the starting age in months, empty for the controls), as the paper's Table 1 gives them.
2. The tests, as the paper's Methods and Results state them. For each site and sex: the log-rank test of the rapamycin
   mice against that site's controls of the same sex (itp/cana.py's, two-sided, removed mice censored at their removal),
   and the Wang-Allison test (itp/cana.py's: the 90th percentile age of both groups' dead, R's default quantile; each
   group's mice alive past it, removed mice among them, against its dead at or below it; Fisher's exact test, two-sided).
   The medians: for each site, sex and group, the median age of the dead (removed mice left out, as the paper leaves
   them out); for each sex the mean of the three site medians of each group, and the rise of rapamycin's over the
   controls', (rapamycin - control) / control.
3. The test's conditions: all six log-rank p values below 0.05; all six Wang-Allison p values below 0.05; the rise at 5%
   or more in males and 9% or more in females. test_passed is 1 if all hold.
4. Beside the test, none of it counted: each site's direction (the rapamycin mice's observed deaths less those the test
   expects of them); the rise as the mean of the three site rises; the pooled tests of the paper's Figure 1 (the
   log-rank test stratified by site) and of its pooled Wang-Allison statement (each site's table summed); and the
   abstract's next sentence, resveratrol (300 and 1,200 ppm from 12 months) and simvastatin (12 and 120 ppm from 10
   months) against the controls of each sex by the site-stratified log-rank test, the smallest of their eight p values.

Controls (controls_passed counts those that behave as stated): the file is the pinned one; it holds 2,172 mice, every
row as rule 1 requires; the log-rank test of one site gives the same p as itp/strong2008.py's log-rank test of two
groups; it gives the same p with the two groups swapped; every result is the same when the rows are read in reverse
order; and each Fisher p equals a sum over the hypergeometric tables computed here independently.

What it cannot check: the data as the paper analysed them in 2010, from which the deposit may differ (the paper says
99.8% of the mice had died); and the paper's own quantile rule for the 90th percentile, which it does not state.

Writes results/outputs.json and results/detail.json. Run with: python3 itp/miller2011.py
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
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


rapa = _load("itp_rapa", "rapa.py")
cana = _load("itp_cana", "cana.py")
s08 = _load("itp_strong2008", "strong2008.py")

INPUT = ("ITP_C2006_Lifespan.xlsx", "1cac070f8d8c1ad92602bb929ab2f91f75a247fafc76c42067c660306836cd07")
POPULATION, COHORT = "UM-HET3", "C2006"
SITES, SEXES = ("TJL", "UM", "UT"), ("m", "f")
GROUPS = ("Control", "Rapa", "Res_lo", "Res_hi", "Sim_lo", "Sim_hi")
DESIGN = {"Control": ("0", None), "Rapa": ("14", "9"), "Res_lo": ("300", "12"), "Res_hi": ("1200", "12"),
          "Sim_lo": ("12", "10"), "Sim_hi": ("120", "10")}
OTHERS = ("Res_lo", "Res_hi", "Sim_lo", "Sim_hi")
ROWS = 2172
ALPHA = 0.05
RISE = {"m": 0.05, "f": 0.09}
LIMIT = 200
OUTPUTS = tuple(f"p_lr_{s.lower()}_{x}" for s in SITES for x in SEXES) + tuple(
    f"p_wa_{s.lower()}_{x}" for s in SITES for x in SEXES) + (
    "rise_m", "rise_f", "largest_p", "beside", "controls_passed", "controls_total", "test_passed")


class Refused(Exception):
    pass


def mice_from_rows(rows):
    """{(group, site, sex): [(age, died)]}; every row checked against rule 1."""
    out = {(g, s, x): [] for g in GROUPS for s in SITES for x in SEXES}
    for i, r in enumerate(rows, start=2):
        if r.get("population") != POPULATION or r.get("cohort") != COHORT:
            raise Refused(f"row {i}: population or cohort not as expected")
        if r.get("site") not in SITES or r.get("sex") not in SEXES:
            raise Refused(f"row {i}: site or sex not as expected")
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


def pair(mice, group, site, sex):
    return (mice[("Control", site, sex)], mice[(group, site, sex)])


def dead(ages):
    return [t for t, d in ages if d]


def fisher_by_enumeration(table):
    """An independent two-sided Fisher p: the probabilities of all tables with the same margins, in floating point,
    those no more likely than the observed one summed (with R's relative tolerance)."""
    (a, b), (c, d) = table
    r1, r2, c1, n = a + b, c + d, a + c, a + b + c + d
    probs = {}
    for x in range(max(0, c1 - r2), min(r1, c1) + 1):
        probs[x] = math.exp(math.lgamma(r1 + 1) - math.lgamma(x + 1) - math.lgamma(r1 - x + 1)
                            + math.lgamma(r2 + 1) - math.lgamma(c1 - x + 1) - math.lgamma(r2 - c1 + x + 1)
                            - math.lgamma(n + 1) + math.lgamma(c1 + 1) + math.lgamma(n - c1 + 1))
    obs = probs[a]
    return sum(p for p in probs.values() if p <= obs * (1 + 1e-7))


def analyse(mice):
    lr = {(s, x): cana.logrank_strat_p([pair(mice, "Rapa", s, x)]) for s in SITES for x in SEXES}
    oe = {(s, x): s08.observed_minus_expected([pair(mice, "Rapa", s, x)]) for s in SITES for x in SEXES}
    wa = {(s, x): cana.wang_allison([pair(mice, "Rapa", s, x)]) for s in SITES for x in SEXES}
    med = {(g, s, x): cana.median_dead(dead(mice[(g, s, x)])) for g in ("Control", "Rapa") for s in SITES for x in SEXES}
    rise, rise_sites = {}, {}
    for x in SEXES:
        c = statistics.mean(med[("Control", s, x)] for s in SITES)
        r = statistics.mean(med[("Rapa", s, x)] for s in SITES)
        rise[x] = (r - c) / c
        rise_sites[x] = statistics.mean((med[("Rapa", s, x)] - med[("Control", s, x)]) / med[("Control", s, x)]
                                        for s in SITES)
    pooled_lr = {x: cana.logrank_strat_p([pair(mice, "Rapa", s, x) for s in SITES]) for x in SEXES}
    pooled_wa = {x: cana.wang_allison([pair(mice, "Rapa", s, x) for s in SITES]) for x in SEXES}
    others = {(g, x): cana.logrank_strat_p([pair(mice, g, s, x) for s in SITES]) for g in OTHERS for x in SEXES}
    others_oe = {(g, x): s08.observed_minus_expected([pair(mice, g, s, x) for s in SITES]) for g in OTHERS for x in SEXES}
    return {"lr": lr, "oe": oe, "wa": wa, "med": med, "rise": rise, "rise_sites": rise_sites, "pooled_lr": pooled_lr,
            "pooled_wa": pooled_wa, "others": others, "others_oe": others_oe}


def conditions(lr, wa, rise):
    """Rule 3."""
    return {"all six site log-rank p values below 0.05": all(p < ALPHA for p in lr.values()),
            "all six site Wang-Allison p values below 0.05": all(p < ALPHA for _, p in wa.values()),
            "the rise of the mean site median at least 5% in males and 9% in females":
                all(rise[x] >= RISE[x] for x in SEXES)}


def sig(p):
    return float(f"{p:.4g}")


def run(seed, inputs="inputs", results="results"):
    rows = rapa.read_rows(os.path.join(inputs, INPUT[0]), INPUT[1])
    mice = mice_from_rows(rows)
    a = analyse(mice)
    cond = conditions(a["lr"], a["wa"], a["rise"])

    ctl = {"the file is the pinned one": True,
           "it holds 2,172 mice, every row as rule 1 requires": len(rows) == ROWS}
    one = pair(mice, "Rapa", "UT", "m")
    ctl["one site's test gives the same p as strong2008.py's two-group test"] = abs(
        a["lr"][("UT", "m")] - s08.logrank_k_p([one[0], one[1]])) <= 1e-12
    swapped = (pair(mice, "Rapa", "UM", "f")[1], pair(mice, "Rapa", "UM", "f")[0])
    ctl["the test gives the same p with the groups swapped"] = abs(
        cana.logrank_strat_p([swapped]) - a["lr"][("UM", "f")]) <= 1e-12
    b = analyse(mice_from_rows(list(reversed(rows))))
    ctl["every result is the same with the rows read in reverse"] = (
        b["lr"] == a["lr"] and b["wa"] == a["wa"] and b["rise"] == a["rise"] and b["others"] == a["others"])
    ctl["each Fisher p equals the enumeration computed here"] = all(
        abs(fisher_by_enumeration(t) - p) <= 1e-9 * max(1.0, p) + 1e-15 for t, p in
        list(a["wa"].values()) + list(a["pooled_wa"].values()))

    largest = max(list(a["lr"].items()) + [(k, p) for k, (_, p) in a["wa"].items()], key=lambda kv: kv[1])
    which = "log-rank" if largest in a["lr"].items() else "Wang-Allison"
    smallest_other = min(a["others"], key=a["others"].get)
    values = {f"p_lr_{s.lower()}_{x}": sig(a["lr"][(s, x)]) for s in SITES for x in SEXES}
    values.update({f"p_wa_{s.lower()}_{x}": sig(a["wa"][(s, x)][1]) for s in SITES for x in SEXES})
    values.update({
        "rise_m": round(a["rise"]["m"], 4), "rise_f": round(a["rise"]["f"], 4),
        "largest_p": f"{which} {largest[0][0]} {largest[0][1]}: p {sig(largest[1])}",
        "beside": (f"pooled log-rank p m {sig(a['pooled_lr']['m'])}, f {sig(a['pooled_lr']['f'])}; resveratrol and "
                   f"simvastatin: smallest p {sig(a['others'][smallest_other])} ({smallest_other[0]} "
                   f"{smallest_other[1]}) of 8"),
        "controls_passed": sum(bool(v) for v in ctl.values()), "controls_total": len(ctl),
        "test_passed": int(all(cond.values())),
    })
    out = {k: values[k] for k in OUTPUTS}
    for k, v in out.items():
        if isinstance(v, str) and len(v) > LIMIT:
            raise AssertionError(f"{k}: longer than {LIMIT} characters: {v}")
    detail = {
        "input": {"name": INPUT[0], "sha256": INPUT[1], "rows": len(rows)},
        "counts": {f"{g} {s} {x}": [len(mice[(g, s, x)]), sum(1 for _, d in mice[(g, s, x)] if d)]
                   for g in GROUPS for s in SITES for x in SEXES},
        "conditions": cond, "controls": ctl,
        "logrank": {f"{s} {x}": a["lr"][(s, x)] for s, x in a["lr"]},
        "observed_minus_expected": {f"{s} {x}": a["oe"][(s, x)] for s, x in a["oe"]},
        "wang_allison": {f"{s} {x}": {"table": t, "p": p} for (s, x), (t, p) in a["wa"].items()},
        "medians_dead": {f"{g} {s} {x}": m for (g, s, x), m in a["med"].items()},
        "rise_of_mean_site_median": a["rise"], "mean_of_site_rises": a["rise_sites"],
        "pooled_logrank": a["pooled_lr"],
        "pooled_wang_allison": {x: {"table": t, "p": p} for x, (t, p) in a["pooled_wa"].items()},
        "others_logrank": {f"{g} {x}": p for (g, x), p in a["others"].items()},
        "others_observed_minus_expected": {f"{g} {x}": v for (g, x), v in a["others_oe"].items()},
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
        sys.exit(f"miller2011: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
