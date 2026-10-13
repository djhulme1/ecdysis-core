#!/usr/bin/env python3
"""Rapamycin with acarbose against rapamycin alone, across three ITP cohorts, from the per-mouse data.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:ff7b4dd0265b29b1) is from Strong et al.,
"Lifespan benefits for the combination of rapamycin plus acarbose and for captopril in genetically heterogeneous mice",
Aging Cell 21(12), e13724 (2022): "In male mice, the combination of Rapa and Aca started at 9 months and led to a longer
lifespan than in either of the two prior cohorts of mice treated with Rapa only, suggesting that this drug combination
was more potent than either of its components used alone."

Its registered test: refuted if, in the three cohorts' deposited per-mouse lifespans, the C2017 males given rapamycin
(14.7 ppm) with acarbose (1000 ppm) from 9 months do not have a higher median age at death, as the paper takes it (the
mean of the three site medians of the dead), than both the C2006 and the C2009 males given rapamycin alone (14 ppm) from
9 months, or if the site-stratified log-rank test of the combination's males against either earlier cohort's, removed
mice censored, gives p of 0.05 or more.

The inputs are the program's three deposited workbooks (the Mouse Phenome Database, project ITP1), the claim's data of
record, each checked against its SHA-256 and read with the standard library by itp/rapa.py's reader (their XML parsed
as data; nothing in them is run). The statistics are itp/cana.py's. Every rule below was fixed before any seed existed;
the seed is not used, as nothing here is random.

1. The mice. Every row of each workbook must be of population UM-HET3 and of that workbook's cohort, at site TJL, UM or
   UT, of sex f or m, with a whole number of days as its age, and either dead (status "dead", dead 1) or removed (status
   "removed", dead 0). The groups compared must carry their design in the workbooks' own columns (DESIGN below): C2017's
   RaAc_9 (rapamycin 14.7 ppm and acarbose 1000 ppm from 9 months) and Control, C2006's Rapa (14 ppm from 9 months)
   and Control, C2009's Rapa_mid (14 ppm from 9 months) and Control. Otherwise the run is refused.
2. The median, as the paper's Table 5 takes it: for each site, the median age at death of the dead (removed mice left
   out), the middle age or the mean of the two middle ones; then the mean of the three site medians.
3. The log-rank test, as the paper's Discussion does it: the two-tailed log-rank test stratified by site, the treated
   mice of one cohort against those of another (no controls), removed mice censored at removal (itp/cana.py's rule 4).
4. The test's four conditions, for males: the RaAc9 median above the C2006 Rapa median, and above the C2009 Rapa
   median; the log-rank p against each below 0.05. test_passed is 1 if all four hold.
5. Beside the test, against what the paper prints: the three medians (949, 887 and 852 days) and the p values (below
   0.006 and below 0.0006); the same comparisons for females (1083, 1030 and 1052; p 0.07 and 0.39); the eighteen site
   medians of Table 5, each rounded half up, read as rule 2 reads them and, as a second reading, as the Kaplan-Meier
   median (removed mice censored; the first age of death at which the product-limit survival falls to one half or
   below, or, where it is exactly one half, the mean of that age and the next age of death); each Rapa group's gain over
   its own cohort's controls as the mean of the three site gains (the paper: 10% in C2006 and 5% in C2009 for males, 18%
   in each for females) and RaAc9's (29% for males with all three sites); and the log-rank p of each comparison with
   removed mice left out instead of censored.

What it cannot check: the cohorts beyond the workbooks; and the data as the paper read them, from which the deposits
may differ (the comparisons of rule 5 say where).

Writes results/outputs.json (the 20 values a receipt carries) and results/detail.json (every value computed).
"""

import importlib.util
import json
import os
import re
import statistics
import sys
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))


def _load(name, file):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, file))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


rapa = _load("itp_rapa", "rapa.py")
cana = _load("itp_cana", "cana.py")

INPUTS = {
    "C2017": ("ITP_C2017_Lifespan.xlsx", "1f1ab41e6497c92bc926ee9ba63f617a239549745ecd2ceede7932fdbf36dc1f"),
    "C2006": ("ITP_C2006_Lifespan.xlsx", "1cac070f8d8c1ad92602bb929ab2f91f75a247fafc76c42067c660306836cd07"),
    "C2009": ("ITP_C2009_Lifespan.xlsx", "3e542f236b915bc1b312c8698309193abf39497b5c57c5c81eb5d06708ec5d20"),
}
POPULATION, SITES, SEXES = "UM-HET3", ("TJL", "UM", "UT"), ("m", "f")
DESIGN = {  # (cohort, group): (dose as the workbook writes it, starting age in months)
    ("C2017", "RaAc_9"): ("Rapa: 14.7 and ACA: 1000", "9"), ("C2017", "Control"): ("0", None),
    ("C2006", "Rapa"): ("14", "9"), ("C2006", "Control"): ("0", None),
    ("C2009", "Rapa_mid"): ("14", "9"), ("C2009", "Control"): ("0", None),
}
COMBINATION = ("C2017", "RaAc_9")
PRIOR = {"C2006": ("C2006", "Rapa"), "C2009": ("C2009", "Rapa_mid")}
ALPHA = 0.05
PRINTED = {("m", "RaAc9"): 949, ("m", "C2006"): 887, ("m", "C2009"): 852,
           ("f", "RaAc9"): 1083, ("f", "C2006"): 1030, ("f", "C2009"): 1052}
PRINTED_P = {("m", "C2006"): "< 0.006", ("m", "C2009"): "< 0.0006", ("f", "C2006"): "0.07", ("f", "C2009"): "0.39"}
PRINTED_SITES = {  # Table 5's site medians, TJL, UM, UT
    ("m", "RaAc9"): (847, 987, 1014), ("m", "C2006"): (841, 932, 888), ("m", "C2009"): (728, 974, 855),
    ("f", "RaAc9"): (1147, 972, 1130), ("f", "C2006"): (1077, 1008, 1006), ("f", "C2009"): (1002, 1065, 1089),
}
LIMIT = 200
OUTPUTS = ("n_m", "median_m_raac9", "median_m_c2006", "median_m_c2009", "logrank_p_c2006", "logrank_p_c2009",
           "medians_as_printed", "p_as_printed", "median_f_raac9", "median_f_c2006", "median_f_c2009",
           "logrank_p_f_c2006", "logrank_p_f_c2009", "gains_m", "gains_f", "p_removed_left_out", "conditions_met",
           "conditions_total", "rows", "test_passed")


class Refused(Exception):
    pass


def mice_from_rows(rows, cohort):
    """{(group, site, sex): [(age, died)]} for every group of the cohort; every row checked against rule 1."""
    out = {}
    for i, r in enumerate(rows, start=2):
        if r.get("population") != POPULATION or r.get("cohort") != cohort:
            raise Refused(f"{cohort} row {i}: population or cohort not as expected: {r}")
        if r.get("site") not in SITES or r.get("sex") not in SEXES:
            raise Refused(f"{cohort} row {i}: site or sex not as expected: {r}")
        age = r.get("age") or ""
        if not re.fullmatch(r"[0-9]+(\.0+)?", age):
            raise Refused(f"{cohort} row {i}: age {age!r} is not a whole number of days")
        state = (r.get("status"), r.get("dead"))
        if state not in (("dead", "1"), ("removed", "0")):
            raise Refused(f"{cohort} row {i}: status and dead disagree: {state}")
        g = r.get("group")
        if (cohort, g) in DESIGN:
            design = (r.get("dose"), r.get("age_initiation") or None)
            if design != DESIGN[(cohort, g)]:
                raise Refused(f"{cohort} row {i}: group {g} carries {design}, not {DESIGN[(cohort, g)]}")
        out.setdefault((g, r["site"], r["sex"]), []).append((int(float(age)), state[0] == "dead"))
    for (c, g) in DESIGN:
        if c == cohort and not any(k[0] == g for k in out):
            raise Refused(f"{cohort}: no mice in group {g}")
    return out


def site_median(ms):
    return statistics.median([t for t, d in ms if d])


def km_median(ms):
    """The Kaplan-Meier median of [(age, died)], removed mice censored (at risk at their own age): the first age of
    death at which the product-limit survival falls to one half or below; at exactly one half, the mean of that age and
    the next age of death. None if it never falls that far."""
    deaths = sorted({t for t, d in ms if d})
    s = Fraction(1)
    for i, t in enumerate(deaths):
        n = sum(1 for x, _ in ms if x >= t)
        d = sum(1 for x, died in ms if x == t and died)
        s *= Fraction(n - d, n)
        if s == Fraction(1, 2) and i + 1 < len(deaths):
            return (t + deaths[i + 1]) / 2
        if s <= Fraction(1, 2):
            return t
    return None


def mean_of_site_medians(mice, group, sex):
    return sum(site_median(mice[(group, s, sex)]) for s in SITES) / len(SITES)


def compare(a_mice, a_group, b_mice, b_group, sex, removed="censored"):
    """Site-stratified two-tailed log-rank p of group a against group b (each from its own cohort)."""
    def keep(ms):
        return ms if removed == "censored" else [m for m in ms if m[1]]
    return cana.logrank_strat_p([(keep(b_mice[(b_group, s, sex)]), keep(a_mice[(a_group, s, sex)])) for s in SITES])


def gain(mice, group, sex):
    """The mean over the three sites of the group's median over its cohort's control median, less one."""
    return sum(site_median(mice[(group, s, sex)]) / site_median(mice[("Control", s, sex)]) - 1 for s in SITES) / 3


def conditions(medians, ps):
    return {
        "RaAc9 males: median above C2006's rapamycin males": medians["RaAc9"] > medians["C2006"],
        "RaAc9 males: median above C2009's rapamycin males": medians["RaAc9"] > medians["C2009"],
        "against C2006: log-rank p below 0.05": ps["C2006"] < ALPHA,
        "against C2009: log-rank p below 0.05": ps["C2009"] < ALPHA,
    }


def p_text(p):
    return f"{p:.3g}"


def as_printed_p(p, printed):
    if printed.startswith("<"):
        return p < float(printed[1:])
    decimals = len(printed.split(".")[1])
    return f"{p:.{decimals}f}" == printed


def half_up(x):
    return cana.half_up(x)


def run(seed, inputs="inputs", results="results"):
    mice, rows = {}, {}
    for cohort, (name, sha) in INPUTS.items():
        r = rapa.read_rows(os.path.join(inputs, name), sha)
        rows[cohort] = len(r)
        mice[cohort] = mice_from_rows(r, cohort)
    combo = mice[COMBINATION[0]]
    med, ps, ps_left = {}, {}, {}
    for sex in SEXES:
        med[(sex, "RaAc9")] = mean_of_site_medians(combo, COMBINATION[1], sex)
        for key, (cohort, group) in PRIOR.items():
            med[(sex, key)] = mean_of_site_medians(mice[cohort], group, sex)
            ps[(sex, key)] = compare(combo, COMBINATION[1], mice[cohort], group, sex)
            ps_left[(sex, key)] = compare(combo, COMBINATION[1], mice[cohort], group, sex, removed="left out")
    cond = conditions({k: med[("m", k)] for k in ("RaAc9", "C2006", "C2009")},
                      {k: ps[("m", k)] for k in ("C2006", "C2009")})
    gains = {(sex, key): gain(mice[cohort], group, sex) for sex in SEXES
             for key, (cohort, group) in list(PRIOR.items()) + [("RaAc9", COMBINATION)]}
    counts = {key: sum(len(mice[c][(g, s, "m")]) for s in SITES)
              for key, (c, g) in [("RaAc9", COMBINATION)] + list(PRIOR.items())}
    medians_as_printed = sum(1 for k, v in PRINTED.items() if half_up(med[k]) == v)
    groups = {"RaAc9": COMBINATION, **PRIOR}
    sites = {(sex, key, s): (site_median(mice[c][(g, s, sex)]), km_median(mice[c][(g, s, sex)]))
             for sex in SEXES for key, (c, g) in groups.items() for s in SITES}

    def sites_as_printed(key, reading):
        return sum(1 for sex in SEXES for s, v in zip(SITES, PRINTED_SITES[(sex, key)])
                   if sites[(sex, key, s)][reading] is not None and half_up(sites[(sex, key, s)][reading]) == v)
    p_as_printed = sum(1 for k, v in PRINTED_P.items() if as_printed_p(ps[k], v))

    def fmt(x):
        return float(f"{x:.1f}")

    values = {
        "n_m": "; ".join(f"{k} {counts[k]}" for k in counts),
        "median_m_raac9": fmt(med[("m", "RaAc9")]), "median_m_c2006": fmt(med[("m", "C2006")]),
        "median_m_c2009": fmt(med[("m", "C2009")]),
        "logrank_p_c2006": float(p_text(ps[("m", "C2006")])), "logrank_p_c2009": float(p_text(ps[("m", "C2009")])),
        "medians_as_printed": (f"means {medians_as_printed} of {len(PRINTED)}; site medians "
                               + ", ".join(f"{k} {sites_as_printed(k, 0)}" for k in groups)
                               + " of 6; as Kaplan-Meier medians "
                               + ", ".join(f"{k} {sites_as_printed(k, 1)}" for k in groups) + " of 6"),
        "p_as_printed": f"{p_as_printed} of {len(PRINTED_P)}",
        "median_f_raac9": fmt(med[("f", "RaAc9")]), "median_f_c2006": fmt(med[("f", "C2006")]),
        "median_f_c2009": fmt(med[("f", "C2009")]),
        "logrank_p_f_c2006": float(p_text(ps[("f", "C2006")])), "logrank_p_f_c2009": float(p_text(ps[("f", "C2009")])),
        "gains_m": "; ".join(f"{k} {100 * gains[('m', k)]:.1f}%" for k in ("C2006", "C2009", "RaAc9")),
        "gains_f": "; ".join(f"{k} {100 * gains[('f', k)]:.1f}%" for k in ("C2006", "C2009", "RaAc9")),
        "p_removed_left_out": "; ".join(f"{sex} {k} {p_text(ps_left[(sex, k)])}" for sex in SEXES for k in ("C2006", "C2009")),
        "conditions_met": sum(cond.values()), "conditions_total": len(cond),
        "rows": "; ".join(f"{c} {n}" for c, n in rows.items()),
        "test_passed": int(all(cond.values())),
    }
    out = {k: values[k] for k in OUTPUTS}
    for k, v in out.items():
        if isinstance(v, str) and len(v) > LIMIT:
            raise AssertionError(f"{k}: longer than {LIMIT} characters")
    detail = {"values": values, "conditions": cond,
              "medians": {f"{s} {k}": v for (s, k), v in med.items()},
              "printed_medians": {f"{s} {k}": v for (s, k), v in PRINTED.items()},
              "logrank": {f"{s} {k}": v for (s, k), v in ps.items()},
              "printed_p": {f"{s} {k}": v for (s, k), v in PRINTED_P.items()},
              "logrank_removed_left_out": {f"{s} {k}": v for (s, k), v in ps_left.items()},
              "gains": {f"{s} {k}": v for (s, k), v in gains.items()},
              "site_medians": {f"{key} {sex} {s}": {"dead": v[0], "kaplan_meier": v[1],
                                                    "printed": PRINTED_SITES[(sex, key)][SITES.index(s)]}
                               for (sex, key, s), v in sites.items()}}
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
        sys.exit(f"raac: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
