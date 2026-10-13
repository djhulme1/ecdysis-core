#!/usr/bin/env python3
"""Fisetin and four other agents in the ITP's 2018 and 2019 cohorts: no significant increase in life span.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:2d43fe76960ee6a9) is from Harrison et al.,
"Astaxanthin and meclizine extend lifespan in UM-HET3 male mice; fisetin, SG1002 (hydrogen sulfide donor), dimethyl
fumarate, mycophenolic acid, and 4-phenylbutyrate do not significantly affect lifespan in either sex at the doses and
schedules used", GeroScience 46(1), 795-816 (2024): "Five other new agents were also tested as follows: fisetin, SG1002
(hydrogen sulfide donor), dimethyl fumarate, mycophenolic acid, and 4-phenylbutyrate. None of these increased lifespan
significantly at the dose and method of administration tested in either sex."

Its registered test: refuted if, in the deposited per-mouse lifespans of the ITP's 2018 and 2019 cohorts (fisetin at
600 ppm from 20 months, continuous or 3 days in 14, and SG1002 at 240 ppm from 18 months, in 2018; SG1002 from 6
months, dimethyl fumarate at 120 ppm from 9 or 16 months, mycophenolic acid at 6.7 ppm and 4-phenylbutyrate at 1,000
ppm from 9 months, in 2019), the two-tailed log-rank test stratified by site, removed mice censored, gives p below 0.05
for any group against its cohort's controls of the same sex, with the group dying less than expected.

The inputs are the program's deposited datasets for the two cohorts (the Mouse Phenome Database, project ITP1):
ITP_C2018_Lifespan.xlsx (file 558) and ITP_C2019_Lifespan.xlsx (file 573), the claim's data of record, checked against
their SHA-256 and read with the standard library by itp/rapa.py's reader (their XML parsed as data; nothing in them is
run). The statistics are itp/cana.py's and itp/strong2008.py's. Every rule below was fixed before any seed existed; the
seed is not used, as nothing here is random.

1. The mice. Every row must be of population UM-HET3 and of its file's cohort, at site TJL, UM or UT, of sex f or m,
   with a whole number of days as its age ("age(days)"), and either dead (status "dead", dead 1) or removed (status
   "removed", dead 0); its group must be one of its cohort's, carrying its design in the workbook's own columns
   ("Rx(ppm)" and "age_initiation(mo)", spelt as the workbook spells them: DESIGN below).
2. The test, the paper's as its Methods state it (two-tailed log-rank at p < 0.05, stratified by site, removed mice
   censored, males and females separately, each cohort's groups against that cohort's controls): itp/cana.py's
   stratified log-rank test; its direction, the group's observed deaths less those the test expects of it
   (itp/strong2008.py's): below zero, the group lived longer.
3. The test's condition: no group of the five agents (TESTED below, eight groups) in either sex with p below 0.05 and its
   mice dying less than expected. test_passed is 1 if it holds.
4. Beside the test, none of it counted: any significant decrease (the paper reports one, 4-phenylbutyrate in females,
   p = 0.01); the median age at death of the dead, the three sites pooled, per group and sex, and each group's change
   from its controls; each site's p and direction; the Wang-Allison test as itp/cana.py takes it; and, as a positive
   control of the same test on the 2019 file, astaxanthin and meclizine in males (printed p = 0.003 and 0.03).

Controls (controls_passed counts those that behave as stated): the files are the pinned ones; they hold 1,509 and 2,635
mice, every row as rule 1 requires; the stratified test with a single stratum gives the same p as itp/strong2008.py's
log-rank test of two groups; it gives the same p with the two groups swapped; each group's p is the same when its rows
are read in reverse order; and the same test finds astaxanthin's male gain below 0.05.

What it cannot check: the data as the paper analysed them, from which the deposits may differ; and the diets' actual
contents, which the paper assayed (dimethyl fumarate at 35% of its target; SG1002 not measurable).

Writes results/outputs.json and results/detail.json. Run with: python3 itp/fis2024.py
"""

import importlib.util
import json
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

INPUTS = {"C2018": ("ITP_C2018_Lifespan.xlsx", "7f57e5430efea9067f1782a4b8cbdcb752243e3f314f09d8596a7df044314a2d", 1509),
          "C2019": ("ITP_C2019_Lifespan.xlsx", "c3047b7c545460e7e3c98213770c42e7d0ade1ed16f492cc9c7405a7b4d1b798", 2635)}
POPULATION = "UM-HET3"
SITES, SEXES = ("TJL", "UM", "UT"), ("m", "f")
DESIGN = {
    "C2018": {"Control": ("0", "NA"), "Fis_On": ("600", "20 (continuous)"),
              "Fis_Cyc": ("600", "20 (3 days on/11 days off"), "SG1002": ("240", "18")},
    "C2019": {"Control": ("0", "NA"), "Asta": ("4000", "12"), "Mec": ("800", "12"), "DMF_9": ("120", "9"),
              "DMF_16": ("120", "16"), "MPA": ("6.7", "9"), "PBA": ("1000", "9"), "SG1002": ("240", "6")},
}
TESTED = (("C2018", "Fis_On"), ("C2018", "Fis_Cyc"), ("C2018", "SG1002"), ("C2019", "SG1002"), ("C2019", "DMF_9"),
          ("C2019", "DMF_16"), ("C2019", "MPA"), ("C2019", "PBA"))
POSITIVE = (("C2019", "Asta"), ("C2019", "Mec"))
ALPHA = 0.05
LIMIT = 200


def key(cohort, group, sex):
    return f"p_{cohort[-2:]}_{group.lower()}_{sex}"


OUTPUTS = tuple(key(c, g, x) for c, g in TESTED for x in SEXES) + (
    "beside", "controls_passed", "controls_total", "test_passed")


class Refused(Exception):
    pass


def mice_from_rows(rows, cohort):
    """{(group, site, sex): [(age, died)]} for one cohort; every row checked against rule 1."""
    design = DESIGN[cohort]
    out = {(g, s, x): [] for g in design for s in SITES for x in SEXES}
    for i, r in enumerate(rows, start=2):
        if r.get("population") != POPULATION or r.get("cohort") != cohort:
            raise Refused(f"{cohort} row {i}: population or cohort not as expected")
        if r.get("site") not in SITES or r.get("sex") not in SEXES:
            raise Refused(f"{cohort} row {i}: site or sex not as expected")
        age = r.get("age(days)") or ""
        if not re.fullmatch(r"[0-9]+(\.0+)?", age):
            raise Refused(f"{cohort} row {i}: age {age!r} is not a whole number of days")
        state = (r.get("status"), r.get("dead"))
        if state not in (("dead", "1"), ("removed", "0")):
            raise Refused(f"{cohort} row {i}: status and dead disagree: {state}")
        g = r.get("group")
        if g not in design:
            raise Refused(f"{cohort} row {i}: group {g!r} is not one of the cohort's")
        d = (r.get("Rx(ppm)"), r.get("age_initiation(mo)"))
        if d != design[g]:
            raise Refused(f"{cohort} row {i}: group {g} carries {d}, not {design[g]}")
        out[(g, r["site"], r["sex"])].append((int(float(age)), state[0] == "dead"))
    return out


def strata(mice, group, sex, sites=SITES):
    return [(mice[("Control", s, sex)], mice[(group, s, sex)]) for s in sites]


def analyse(cohorts, groups):
    ps = {(c, g, x): cana.logrank_strat_p(strata(cohorts[c], g, x)) for c, g in groups for x in SEXES}
    oes = {(c, g, x): s08.observed_minus_expected(strata(cohorts[c], g, x)) for c, g in groups for x in SEXES}
    return ps, oes


def conditions(ps, oes):
    """Rule 3."""
    return {"no group of the five agents, in either sex, lives significantly longer (p < 0.05, fewer deaths than "
            "expected)": not any(ps[k] < ALPHA and oes[k] < 0 for k in ps)}


def sig(p):
    return float(f"{p:.4g}")


def run(seed, inputs="inputs", results="results"):
    rows = {c: rapa.read_rows(os.path.join(inputs, name), sha) for c, (name, sha, _) in INPUTS.items()}
    cohorts = {c: mice_from_rows(rows[c], c) for c in INPUTS}
    ps, oes = analyse(cohorts, TESTED)
    cond = conditions(ps, oes)
    pos_ps, pos_oes = analyse(cohorts, POSITIVE)
    site = {(c, g, x, s): (cana.logrank_strat_p(strata(cohorts[c], g, x, (s,))),
                           s08.observed_minus_expected(strata(cohorts[c], g, x, (s,))))
            for c, g in TESTED for x in SEXES for s in SITES}

    def dead(c, g, x):
        return [t for s in SITES for t, d in cohorts[c][(g, s, x)] if d]

    meds = {(c, g, x): statistics.median(dead(c, g, x)) for c in INPUTS for g in DESIGN[c] for x in SEXES}
    wa = {(c, g, x): cana.wang_allison(strata(cohorts[c], g, x)) for c, g in TESTED for x in SEXES}
    gains = {k: v for k, v in ps.items() if oes[k] < 0}
    decreases = sorted(k for k in ps if ps[k] < ALPHA and oes[k] > 0)

    ctl = {"the files are the pinned ones": True,
           "they hold 1,509 and 2,635 mice, every row as rule 1 requires":
               all(len(rows[c]) == INPUTS[c][2] for c in INPUTS)}
    one = cohorts["C2019"]
    pooled = [(sum((one[("Control", s, "f")] for s in SITES), []), sum((one[("PBA", s, "f")] for s in SITES), []))]
    ctl["one stratum gives the same p as strong2008.py's two-group test"] = abs(
        cana.logrank_strat_p(pooled) - s08.logrank_k_p([pooled[0][0], pooled[0][1]])) <= 1e-12
    swapped = [(b, a) for a, b in strata(cohorts["C2018"], "Fis_On", "m")]
    ctl["the test gives the same p with the groups swapped"] = abs(
        cana.logrank_strat_p(swapped) - ps[("C2018", "Fis_On", "m")]) <= 1e-12
    rev = {c: mice_from_rows(list(reversed(rows[c])), c) for c in INPUTS}
    rps, _ = analyse(rev, TESTED)
    ctl["each p is the same with the rows read in reverse"] = all(abs(rps[k] - ps[k]) <= 1e-12 for k in ps)
    ctl["the same test finds astaxanthin's male gain below 0.05"] = (
        pos_ps[("C2019", "Asta", "m")] < ALPHA and pos_oes[("C2019", "Asta", "m")] < 0)

    best = min(gains, key=gains.get) if gains else None
    smallest_down = min(decreases, key=lambda k: ps[k]) if decreases else None
    values = {key(c, g, x): sig(ps[(c, g, x)]) for c, g in TESTED for x in SEXES}
    values.update({
        "beside": ("best gain " + (f"{best[1]} {best[2]} p {sig(ps[best])}" if best else "none") + "; significant "
                   f"decreases {len(decreases)}" + (f" ({smallest_down[1]} {smallest_down[2]} p "
                                                     f"{sig(ps[smallest_down])})" if smallest_down else "")
                   + "; positive control " + ", ".join(f"{g} m p {sig(pos_ps[(c, g, 'm')])}" for c, g in POSITIVE)),
        "controls_passed": sum(bool(v) for v in ctl.values()), "controls_total": len(ctl),
        "test_passed": int(all(cond.values())),
    })
    out = {k: values[k] for k in OUTPUTS}
    for k, v in out.items():
        if isinstance(v, str) and len(v) > LIMIT:
            raise AssertionError(f"{k}: longer than {LIMIT} characters: {v}")
    detail = {
        "inputs": {c: {"name": n, "sha256": h, "rows": len(rows[c])} for c, (n, h, _) in INPUTS.items()},
        "counts": {f"{c} {g} {s} {x}": [len(cohorts[c][(g, s, x)]), sum(1 for _, d in cohorts[c][(g, s, x)] if d)]
                   for c in INPUTS for g in DESIGN[c] for s in SITES for x in SEXES},
        "conditions": cond, "controls": ctl,
        "logrank": {f"{c} {g} {x}": {"p": ps[(c, g, x)], "observed_minus_expected": oes[(c, g, x)]}
                    for c, g, x in ps},
        "sites": {f"{c} {g} {x} {s}": {"p": p, "observed_minus_expected": oe} for (c, g, x, s), (p, oe) in site.items()},
        "sites_below_0.05": [f"{c} {g} {x} {s}: p {sig(p)} ({'longer' if oe < 0 else 'shorter'})"
                             for (c, g, x, s), (p, oe) in sorted(site.items()) if p < ALPHA],
        "medians_dead_pooled": {f"{c} {g} {x}": m for (c, g, x), m in meds.items()},
        "wang_allison": {f"{c} {g} {x}": {"table": t, "p": p} for (c, g, x), (t, p) in wa.items()},
        "positive_control": {f"{c} {g} {x}": {"p": pos_ps[(c, g, x)], "observed_minus_expected": pos_oes[(c, g, x)]}
                             for c, g, x in pos_ps},
        "decreases": [{"group": f"{c} {g} {x}", "p": ps[(c, g, x)], "observed_minus_expected": oes[(c, g, x)],
                       "median_change": (meds[(c, g, x)] - meds[(c, "Control", x)]) / meds[(c, "Control", x)]}
                      for c, g, x in decreases],
        "largest_gain": ({"group": f"{best[0]} {best[1]} {best[2]}", "p": ps[best],
                          "observed_minus_expected": oes[best]} if best else None),
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
        sys.exit(f"fis2024: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
