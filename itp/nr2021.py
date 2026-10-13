#!/usr/bin/env python3
"""Nicotinamide riboside and three other agents in the ITP's 2016 cohort: no significant increase in life span.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:4e441e04e162d792) is from Harrison et al.,
"17-a-estradiol late in life extends lifespan in aging UM-HET3 male mice; nicotinamide riboside and three other drugs do
not affect lifespan in either sex", Aging Cell 20(5), e13328 (2021): "Four other interventions were tested in males and
females: nicotinamide riboside, candesartan cilexetil, geranylgeranylacetone, and MIF098. Despite some data suggesting
that nicotinamide riboside would be effective, neither it nor the other three increased lifespans significantly at the
doses tested."

Its registered test: refuted if, in the cohort's deposited per-mouse lifespans (the ITP's 2016 cohort of UM-HET3 mice at
its three sites: controls; nicotinamide riboside at 1,000 ppm and candesartan cilexetil at 30 ppm from 8 months,
geranylgeranylacetone at 600 ppm from 9 months, MIF098 at 240 ppm from 8 months), the two-tailed log-rank test
stratified by site, removed mice censored at removal, gives p below 0.05 for any of the four agents against the controls
of the same sex, in males or in females, with the agent's mice dying fewer than the test expects (eight tests).

The input is the program's deposited dataset for the cohort (the Mouse Phenome Database, project ITP1):
ITP_C2016_Lifespan.xlsx (file 754), the claim's data of record, checked against its SHA-256 and read with the standard
library by itp/rapa.py's reader (its XML parsed as data; nothing in it is run). The statistics are itp/cana.py's and
itp/strong2008.py's. Every rule below was fixed before any seed existed; the seed is not used, as nothing here is random.

1. The mice. Every row must be of population UM-HET3 and cohort C2016, at site TJL, UM or UT, of sex f or m, with a
   whole number of days as its age, and either dead (status "dead", dead 1) or removed (status "removed", dead 0); its
   group must be one of the cohort's eight, carrying its design in the workbook's own columns (DESIGN below: the dose in
   ppm and the starting age in months, empty for the controls), as the paper's Methods give the four agents' (the
   cohort also holds canagliflozin, Miller et al. 2020's, and 17-alpha-estradiol from 16 and 20 months, males only).
2. The test, the paper's as its Methods state it (two-tailed log-rank at p < 0.05, stratified by site, removed mice
   censored, males and females separately): itp/cana.py's stratified log-rank test, each agent's mice of a sex against
   that sex's controls; its direction, the agent's observed deaths less those the test expects of them
   (itp/strong2008.py's): below zero, the agent's mice lived longer.
3. The test's condition: no agent in either sex with p below 0.05 and its mice dying fewer than expected. test_passed
   is 1 if it holds.
4. Beside the test, none of it counted: any significant decrease; the median age at death of the dead, the three sites
   pooled, per group and sex, and each agent's change from the controls; each site's p and direction (the paper's
   Table 2 reports marginal site effects of NR in both directions); the Wang-Allison test as itp/cana.py takes it (each
   site's cut at the 90th percentile of both groups' dead, the tables summed, Fisher's exact test), as the paper's
   Methods describe for its pooled data; and, as a positive control of the same test on the same file, 17-alpha-
   estradiol in males from 16 and from 20 months (printed p < 0.0001 and p = 0.007).

Controls (controls_passed counts those that behave as stated): the file is the pinned one; it holds 2,382 mice, every
row as rule 1 requires; the stratified test with a single stratum gives the same p as itp/strong2008.py's log-rank test
of two groups; it gives the same p with the two groups swapped; each agent's p is the same when its rows are read in
reverse order; and the same test finds 17-alpha-estradiol's male gains, from 16 and from 20 months, below 0.05.

What it cannot check: the data as the paper analysed them in 2020, from which the deposit may differ; and the diets'
actual contents, which the paper assayed (NR plus nicotinamide at 67% to 89% of the target in four batches).

Writes results/outputs.json and results/detail.json. Run with: python3 itp/nr2021.py
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

INPUT = ("ITP_C2016_Lifespan.xlsx", "8c23eb208a1c4dd46b6ce9cee788796a25a2844cbee62e72a7693198cda330df")
POPULATION, COHORT = "UM-HET3", "C2016"
SITES, SEXES = ("TJL", "UM", "UT"), ("m", "f")
AGENTS = ("NR", "CC", "GGA", "MIF098")
NAMES = {"NR": "nicotinamide riboside", "CC": "candesartan cilexetil", "GGA": "geranylgeranylacetone",
         "MIF098": "MIF098"}
DESIGN = {"Control": ("0", None), "NR": ("1000", "8"), "CC": ("30", "8"), "GGA": ("600", "9"), "MIF098": ("240", "8"),
          "Cana": ("180", "7"), "17aE2_16m": ("14.4", "16"), "17aE2_20m": ("14.4", "20")}
GROUPS = tuple(DESIGN)
MALES_ONLY = ("17aE2_16m", "17aE2_20m")
ROWS = 2382
ALPHA = 0.05
LIMIT = 200
OUTPUTS = tuple(f"p_{a.lower()}_{x}" for a in AGENTS for x in SEXES) + (
    "smallest_p", "medians", "sites_p", "wang_allison", "positive_control", "controls_passed", "controls_total",
    "test_passed")


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
        if g in MALES_ONLY and r["sex"] != "m":
            raise Refused(f"row {i}: group {g} holds males only")
        out[(g, r["site"], r["sex"])].append((int(float(age)), state[0] == "dead"))
    return out


def strata(mice, group, sex, sites=SITES):
    return [(mice[("Control", s, sex)], mice[(group, s, sex)]) for s in sites]


def increased(p, oe):
    return p < ALPHA and oe < 0


def conditions(ps, oes):
    """Rule 3."""
    return {"no agent's mice, in either sex, live significantly longer (p < 0.05, fewer deaths than expected)":
            not any(increased(ps[k], oes[k]) for k in ps)}


def sig(p):
    return float(f"{p:.4g}")


def analyse(mice):
    ps = {(a, x): cana.logrank_strat_p(strata(mice, a, x)) for a in AGENTS for x in SEXES}
    oes = {(a, x): s08.observed_minus_expected(strata(mice, a, x)) for a in AGENTS for x in SEXES}
    return ps, oes


def run(seed, inputs="inputs", results="results"):
    rows = rapa.read_rows(os.path.join(inputs, INPUT[0]), INPUT[1])
    mice = mice_from_rows(rows)
    ps, oes = analyse(mice)
    cond = conditions(ps, oes)
    site_ps = {(a, x, s): cana.logrank_strat_p(strata(mice, a, x, (s,))) for a in AGENTS for x in SEXES for s in SITES}
    site_oes = {(a, x, s): s08.observed_minus_expected(strata(mice, a, x, (s,)))
                for a in AGENTS for x in SEXES for s in SITES}

    def dead(g, x):
        return [t for s in SITES for t, d in mice[(g, s, x)] if d]

    meds = {(g, x): statistics.median(dead(g, x)) for g in ("Control",) + AGENTS for x in SEXES}
    wa = {(a, x): cana.wang_allison(strata(mice, a, x)) for a in AGENTS for x in SEXES}
    e2 = {g: (cana.logrank_strat_p(strata(mice, g, "m")), s08.observed_minus_expected(strata(mice, g, "m")))
          for g in MALES_ONLY}
    decreases = [k for k in ps if ps[k] < ALPHA and oes[k] > 0]

    ctl = {"the file is the pinned one": True, "it holds 2,382 mice, every row as rule 1 requires": len(rows) == ROWS}
    one = [(sum((mice[("Control", s, "f")] for s in SITES), []), sum((mice[("NR", s, "f")] for s in SITES), []))]
    ctl["one stratum gives the same p as strong2008.py's two-group test"] = abs(
        cana.logrank_strat_p(one) - s08.logrank_k_p([one[0][0], one[0][1]])) <= 1e-12
    swapped = [(b, a) for a, b in strata(mice, "CC", "m")]
    ctl["the test gives the same p with the groups swapped"] = abs(
        cana.logrank_strat_p(swapped) - ps[("CC", "m")]) <= 1e-12
    rps, _ = analyse(mice_from_rows(list(reversed(rows))))
    ctl["each p is the same with the rows read in reverse"] = all(abs(rps[k] - ps[k]) <= 1e-12 for k in ps)
    ctl["the same test finds 17-alpha-estradiol's male gains below 0.05"] = all(
        p < ALPHA and oe < 0 for p, oe in e2.values())

    smallest = min(ps, key=ps.get)
    values = {f"p_{a.lower()}_{x}": sig(ps[(a, x)]) for a in AGENTS for x in SEXES}
    values.update({
        "smallest_p": f"{NAMES[smallest[0]]} {smallest[1]}: p {sig(ps[smallest])}, observed less expected deaths "
                      f"{oes[smallest]:+.1f}" + (f"; significant decreases: {len(decreases)}" if decreases else ""),
        "medians": "; ".join(f"{x}: control {meds[('Control', x)]:g}, " + ", ".join(
            f"{a} {100 * (meds[(a, x)] - meds[('Control', x)]) / meds[('Control', x)]:+.1f}%" for a in AGENTS)
            for x in SEXES),
        "sites_p": "below 0.05: " + (", ".join(
            f"{a} {x} {s} {sig(p)} ({'longer' if site_oes[(a, x, s)] < 0 else 'shorter'})"
            for (a, x, s), p in sorted(site_ps.items()) if p < ALPHA) or "none") + f" (of {len(site_ps)})",
        "wang_allison": "; ".join(f"{a} {x} {sig(wa[(a, x)][1])}" for a in AGENTS for x in SEXES),
        "positive_control": "17aE2 males: " + ", ".join(
            f"from {g.split('_')[1][:-1]} months p {sig(p)} ({oe:+.1f} deaths)" for g, (p, oe) in e2.items()),
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
        "logrank": {f"{a} {x}": ps[(a, x)] for a, x in ps},
        "observed_minus_expected": {f"{a} {x}": oes[(a, x)] for a, x in oes},
        "significant_decreases": [f"{a} {x}" for a, x in decreases],
        "sites": {f"{a} {x} {s}": {"p": p, "observed_minus_expected": site_oes[(a, x, s)]}
                  for (a, x, s), p in site_ps.items()},
        "medians_dead_pooled": {f"{g} {x}": m for (g, x), m in meds.items()},
        "wang_allison": {f"{a} {x}": {"table": wa[(a, x)][0], "p": wa[(a, x)][1]} for a, x in wa},
        "positive_control_17aE2_males": {g: {"p": p, "observed_minus_expected": oe} for g, (p, oe) in e2.items()},
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
        sys.exit(f"nr2021: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
