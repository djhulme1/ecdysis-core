#!/usr/bin/env python3
"""Curcumin, green tea extract, MCT oil, oxaloacetic acid and resveratrol in the ITP's 2007 cohort: no effect on life span.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:8f5f3e190b0dff91) is from Strong et al.,
"Evaluation of Resveratrol, Green Tea Extract, Curcumin, Oxaloacetic Acid, and Medium-Chain Triglyceride Oil on Life
Span of Genetically Heterogeneous Mice", J. Gerontol. A 68(1), 6-16 (2013): "None of these five agents had a
statistically significant effect on life span of male or female mice, by log-rank test, at the concentrations tested,
although a secondary analysis suggested that GTE might diminish the risk of midlife deaths in females only."

Its registered test: refuted if, in the deposited per-mouse lifespans of the ITP's 2007 cohort (ITP_C2007_Lifespan.xlsx:
controls; curcumin and green tea extract at 2,000 ppm, medium-chain triglyceride oil at 60,000 ppm, oxaloacetic acid at
2,200 ppm and resveratrol at 300 ppm, each from 4 months), the two-tailed log-rank test stratified by site, removed mice
censored at removal, gives p below 0.05 for any of the five agents against the controls of the same sex, in males or in
females (ten tests).

The input is the program's deposited dataset for the cohort (the Mouse Phenome Database, project ITP1):
ITP_C2007_Lifespan.xlsx (file id 804), the claim's data of record, checked against its SHA-256 and read with the
standard library by itp/rapa.py's reader (its XML parsed as data; nothing in it is run). The statistics are
itp/cana.py's and itp/strong2008.py's. Every rule below was fixed before any seed existed; the seed is not used, as
nothing here is random.

1. The mice. Every row must be of population UM-HET3 and cohort C2007, at site TJL, UM or UT, of sex f or m, with a
   whole number of days as its age, and either dead (status "dead", dead 1) or removed (status "removed", dead 0); its
   group must be one of the cohort's six, carrying its design in the workbook's own columns (DESIGN below: the dose in
   ppm and the starting age in months, empty for the controls), as the abstract gives them (all from 4 months).
2. The test (the ITP's, as its papers state it: two-tailed log-rank at p < 0.05, stratified by site, removed mice
   censored at their removal): itp/cana.py's stratified log-rank test, each agent's mice of a sex against that sex's
   controls; its direction, the agent's observed deaths less those the test expects of them (itp/strong2008.py's).
3. The test's condition: all ten p values at 0.05 or more. test_passed is 1 if it holds.
4. Beside the test, none of it counted: the median age at death of the dead, the three sites pooled, per group and
   sex, and each agent's change from the controls; each site's p; the Wang-Allison test as itp/cana.py takes it (each
   site's cut at the 90th percentile of both groups' dead, the tables summed, Fisher's exact test); the abstract's
   secondary analysis (green tea extract and midlife deaths in females) is not repeated, its method unread.

Controls (controls_passed counts those that behave as stated): the file is the pinned one; it holds 2,008 mice, every
row as rule 1 requires; the stratified test with a single stratum gives the same p as itp/strong2008.py's log-rank test
of two groups; it gives the same p with the two groups swapped; and each agent's p is the same when its rows are read
in reverse order.

What it cannot check: the paper's own Methods, which were not read (Europe PMC holds no open full text), so its test
is taken from the program's practice; and the data as the paper analysed them in 2012, from which the deposit may differ.

Writes results/outputs.json and results/detail.json. Run with: python3 itp/strong2013.py
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

INPUT = ("ITP_C2007_Lifespan.xlsx", "7f58576df8966197c49f61aedd8c812305e5a632dfe5416d1ac93275153f6f4d")
POPULATION, COHORT = "UM-HET3", "C2007"
SITES, SEXES = ("TJL", "UM", "UT"), ("m", "f")
AGENTS = ("Cur", "GTE", "MCTO", "OAA", "Res")
NAMES = {"Cur": "curcumin", "GTE": "green tea extract", "MCTO": "MCT oil", "OAA": "oxaloacetic acid",
         "Res": "resveratrol"}
GROUPS = ("Control",) + AGENTS
DESIGN = {"Control": ("0", None), "Cur": ("2000", "4"), "GTE": ("2000", "4"), "MCTO": ("60,000", "4"),
          "OAA": ("2200", "4"), "Res": ("300", "4")}
ROWS = 2008
ALPHA = 0.05
LIMIT = 200
OUTPUTS = tuple(f"p_{a.lower()}_{x}" for a in AGENTS for x in SEXES) + (
    "smallest_p", "medians", "sites_p", "wang_allison", "controls_passed", "controls_total", "test_passed")


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


def strata(mice, group, sex, sites=SITES):
    return [(mice[("Control", s, sex)], mice[(group, s, sex)]) for s in sites]


def conditions(ps):
    """Rule 3."""
    return {"all ten log-rank p values at 0.05 or more": all(p >= ALPHA for p in ps.values())}


def sig(p):
    return float(f"{p:.4g}")


def run(seed, inputs="inputs", results="results"):
    rows = rapa.read_rows(os.path.join(inputs, INPUT[0]), INPUT[1])
    mice = mice_from_rows(rows)
    ps = {(a, x): cana.logrank_strat_p(strata(mice, a, x)) for a in AGENTS for x in SEXES}
    oes = {(a, x): s08.observed_minus_expected(strata(mice, a, x)) for a in AGENTS for x in SEXES}
    cond = conditions(ps)
    site_ps = {(a, x, s): cana.logrank_strat_p(strata(mice, a, x, (s,))) for a in AGENTS for x in SEXES for s in SITES}

    def dead(g, x):
        return [t for s in SITES for t, d in mice[(g, s, x)] if d]

    meds = {(g, x): statistics.median(dead(g, x)) for g in GROUPS for x in SEXES}
    wa = {(a, x): cana.wang_allison(strata(mice, a, x)) for a in AGENTS for x in SEXES}

    ctl = {"the file is the pinned one": True, "it holds 2,008 mice, every row as rule 1 requires": len(rows) == ROWS}
    one = [(sum((mice[("Control", s, "m")] for s in SITES), []), sum((mice[("GTE", s, "m")] for s in SITES), []))]
    ctl["one stratum gives the same p as strong2008.py's two-group test"] = abs(
        cana.logrank_strat_p(one) - s08.logrank_k_p([one[0][0], one[0][1]])) <= 1e-12
    swapped = [(b, a) for a, b in strata(mice, "Res", "f")]
    ctl["the test gives the same p with the groups swapped"] = abs(
        cana.logrank_strat_p(swapped) - ps[("Res", "f")]) <= 1e-12
    rev = mice_from_rows(list(reversed(rows)))
    ctl["each p is the same with the rows read in reverse"] = all(
        abs(cana.logrank_strat_p(strata(rev, a, x)) - ps[(a, x)]) <= 1e-12 for a in AGENTS for x in SEXES)

    smallest = min(ps, key=ps.get)
    values = {f"p_{a.lower()}_{x}": sig(ps[(a, x)]) for a in AGENTS for x in SEXES}
    values.update({
        "smallest_p": f"{NAMES[smallest[0]]} {smallest[1]}: p {sig(ps[smallest])}, observed less expected deaths "
                      f"{oes[smallest]:+.1f}",
        "medians": "; ".join(f"{x}: control {meds[('Control', x)]:g}, " + ", ".join(
            f"{a} {100 * (meds[(a, x)] - meds[('Control', x)]) / meds[('Control', x)]:+.1f}%" for a in AGENTS)
            for x in SEXES),
        "sites_p": "below 0.05: " + (", ".join(f"{a} {x} {s} {sig(p)}" for (a, x, s), p in sorted(site_ps.items())
                                              if p < ALPHA) or "none") + f" (of {len(site_ps)})",
        "wang_allison": "; ".join(f"{a} {x} {sig(wa[(a, x)][1])}" for a in AGENTS for x in SEXES),
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
        "sites": {f"{a} {x} {s}": p for (a, x, s), p in site_ps.items()},
        "medians_dead_pooled": {f"{g} {x}": m for (g, x), m in meds.items()},
        "wang_allison": {f"{a} {x}": {"table": wa[(a, x)][0], "p": wa[(a, x)][1]} for a, x in wa},
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
        sys.exit(f"strong2013: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
