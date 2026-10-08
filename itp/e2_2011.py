#!/usr/bin/env python3
"""17-alpha-estradiol at 14.4 ppm from 10 months in the ITP's 2011 cohort, recomputed from the per-mouse data.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:adfc5cd7134d2356) is from Strong et al.,
"Longer lifespan in male mice treated with a weakly estrogenic agonist, an antioxidant, an alpha-glucosidase inhibitor
or a Nrf2-inducer", Aging Cell 15(5) (2016): "17-alpha-estradiol at a threefold higher dose robustly extended both
median and maximal lifespan, but still only in males."

Its registered test: refuted if, in the study's own per-mouse lifespans (the ITP's 2011 cohort of UM-HET3 mice fed
17-alpha-estradiol at 14.4 ppm from 10 months, or the control diet, at its three sites), with medians and 90th
percentiles of the deaths, removed mice left out, each the mean of the three site values as Table 1 pools them: the
male median rises by less than 9.5% or the male age at 90th percentile survival by less than 6% (half the reported 19%
and 12%); or the female median rises by 9.5% or more, or the female 90th percentile by 6% or more.

The input is the workbook the ITP deposited for the cohort, ITP_C2011_Lifespan.xlsx (Mouse Phenome Database, project
ITP1, file id 787), the claim's data of record; it is checked against its SHA-256 and read by itp/rapa.py's reader
(its XML parsed as data; nothing in it is run). Every rule below was fixed before any seed existed; the seed is not
used, as nothing here is random.

1. The mice. Every row must be of population UM-HET3 and cohort C2011, at site TJL, UM or UT, of sex f or m, with a
   whole number of days as its age, and either dead (status "dead", dead 1) or removed (status "removed", dead 0); its
   group must be one of the cohort's six, carrying that group's design in the workbook's own dose and start columns
   (DESIGN below, as the workbook spells them). Anything else is refused.
2. Medians and 90th percentiles of the dead, per site, sex and group, as itp/cana.py's rule 2 computes them (removed
   mice left out); pooled as the mean of the three site values, as itp/cana.py's rule 3 does: the rule that gives all
   12 of Table 1's printed medians. A gain is the 17aE2 value over the control value, less one.
3. Beside the test, the paper's own tests, as itp/cana.py's rule 4 runs them, for each sex: the log-rank test
   stratified by site (removed mice censored) and the Wang-Allison test as Fisher's exact test on the sites' summed
   tables.
4. Table 1, checked: its 36 numbers (each sex, each of the six groups: the number of deaths, the median and the 90th
   percentile, in days), each compared after rounding the data's value to whole days, halves up. table1_matched
   counts those that agree; three 90th percentiles were seen to differ before registering (17aE2 males, Protandim
   males, metformin with rapamycin females) and are reported as found.

test_passed is 1 if the male median gain is at least 0.095 and the male 90th-percentile gain at least 0.06, and the
female median gain is below 0.095 and the female 90th-percentile gain below 0.06; else 0.

What it cannot check:
- the cohort beyond the workbook: ages are as the ITP recorded them; how a mouse was judged moribund, or why one was
  removed, is not in the data;
- the pooling rule's source: the site-mean rule is read from Table 1, which it reproduces in its medians and counts;
  the paper's methods do not state it, and three of Table 1's 90th percentiles follow some other rule;
- the paper's other cohorts (2010 and 2012: NDGA, fish oil, acarbose from 16 months), in other workbooks.

Writes results/outputs.json (18 values) and results/detail.json.
"""

import importlib.util
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("itp_cana", os.path.join(HERE, "cana.py"))
cana = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cana)
rapa = cana.rapa

INPUT = ("ITP_C2011_Lifespan.xlsx", "509a0c1a30f92ba6f590ec7d669df9b88c44f47692164a7f24e8c83efa4e47e1")
POPULATION, COHORT, SITES, SEXES = "UM-HET3", "C2011", ("TJL", "UM", "UT"), ("m", "f")
# Each group's design as the workbook spells it: (dose, start in months).
DESIGN = {
    "Control": ("0", None),
    "17aE2": ("14.4", "10"),
    "Prot": ("600, then 1200", "10, then 17 "),
    "Met": ("1000", "9"),
    "MetRapa": ("Met: 1000, Rapa: 14", "9"),
    "UDCA": ("5000", "5"),
}
GROUPS = tuple(DESIGN)
MEDIAN_GAIN, P90_GAIN = 0.095, 0.06      # half the reported male 19% and 12%; ceilings for the females

# Table 1 as printed: (group, sex) -> (deaths, median, 90th percentile), days.
TABLE1 = {
    ("Control", "m"): (294, 780, 1064), ("17aE2", "m"): (144, 925, 1193), ("Prot", "m"): (155, 834, 1130),
    ("Met", "m"): (148, 835, 1046), ("MetRapa", "m"): (158, 959, 1175), ("UDCA", "m"): (149, 832, 1063),
    ("Control", "f"): (281, 874, 1092), ("17aE2", "f"): (135, 883, 1091), ("Prot", "f"): (134, 896, 1154),
    ("Met", "f"): (140, 872, 1094), ("MetRapa", "f"): (142, 1078, 1278), ("UDCA", "f"): (133, 865, 1105),
}


def mice_from_rows(rows):
    """{(group, site, sex): [(age, died)]} for every group, each row checked against rule 1."""
    out = {(g, s, x): [] for g in GROUPS for s in SITES for x in SEXES}
    for i, r in enumerate(rows, start=2):
        if (r.get("population") != POPULATION or r.get("cohort") != COHORT or r.get("site") not in SITES
                or r.get("sex") not in SEXES):
            raise cana.Refused(f"row {i}: population, cohort, site or sex not as expected: {r}")
        age = r.get("age") or ""
        if not re.fullmatch(r"[0-9]+(\.0+)?", age):
            raise cana.Refused(f"row {i}: age {age!r} is not a whole number of days")
        state = (r.get("status"), r.get("dead"))
        if state not in (("dead", "1"), ("removed", "0")):
            raise cana.Refused(f"row {i}: status and dead disagree: {state}")
        g = r.get("group")
        if g not in DESIGN:
            raise cana.Refused(f"row {i}: group {g!r} is not one of the cohort's six")
        dose, start = DESIGN[g]
        if r.get("dose") != dose or (r.get("age_initiation") or None) != start:
            raise cana.Refused(f"row {i}: group {g} with dose {r.get('dose')!r} and start {r.get('age_initiation')!r}, "
                               f"not {dose!r} and {start!r}")
        out[(g, r["site"], r["sex"])].append((int(float(age)), state[0] == "dead"))
    return out


def summarise(mice, sex):
    """Per group: each site's count, deaths, median and 90th percentile of the dead, and the Pool (site means)."""
    out = {}
    for g in GROUPS:
        per = {}
        for s in SITES:
            dead = [t for t, d in mice[(g, s, sex)] if d]
            if not dead:
                raise cana.Refused(f"{g}, {sex}, at {s}: no deaths")
            per[s] = {"count": len(mice[(g, s, sex)]), "dead": len(dead), "median": cana.median_dead(dead),
                      "p90": cana.p90_dead(dead)}
        per["Pool"] = {"count": sum(per[s]["count"] for s in SITES), "dead": sum(per[s]["dead"] for s in SITES),
                       "median": sum(per[s]["median"] for s in SITES) / 3,
                       "p90": sum(per[s]["p90"] for s in SITES) / 3}
        out[g] = per
    return out


def gains(summary):
    """(median gain, 90th-percentile gain) of 17aE2 over the controls, by the site-mean rule."""
    c, t = summary["Control"]["Pool"], summary["17aE2"]["Pool"]
    return t["median"] / c["median"] - 1, t["p90"] / c["p90"] - 1


def verdict(male, female):
    """The registered test: male gains at least the thresholds, female gains below them."""
    return int(male[0] >= MEDIAN_GAIN and male[1] >= P90_GAIN and female[0] < MEDIAN_GAIN and female[1] < P90_GAIN)


def table1_check(summaries):
    matched, rows = 0, []
    for (g, sex), printed in TABLE1.items():
        got = summaries[sex][g]["Pool"]
        ours = (got["dead"], cana.half_up(got["median"]), cana.half_up(got["p90"]))
        matched += sum(1 for p, o in zip(printed, ours) if p == o)
        rows.append({"group": g, "sex": sex, "printed": list(printed), "data": list(ours)})
    return matched, rows


def run(inputs="inputs", results="results"):
    rows = rapa.read_rows(os.path.join(inputs, INPUT[0]), INPUT[1])
    mice = mice_from_rows(rows)
    summ = {sex: summarise(mice, sex) for sex in SEXES}
    male, female = gains(summ["m"]), gains(summ["f"])
    tests = {}
    for sex in SEXES:
        strata = [(mice[("Control", s, sex)], mice[("17aE2", s, sex)]) for s in SITES]
        tests[sex] = {"logrank": cana.logrank_strat_p(strata), "wa": cana.wang_allison(strata)}
    matched, t1rows = table1_check(summ)
    cm, tm = summ["m"]["Control"], summ["m"]["17aE2"]
    out = {
        "n_m_control": cm["Pool"]["dead"],
        "n_m_e2": tm["Pool"]["dead"],
        "median_m_control": round(cm["Pool"]["median"], 4),
        "median_m_e2": round(tm["Pool"]["median"], 4),
        "p90_m_control": round(cm["Pool"]["p90"], 4),
        "p90_m_e2": round(tm["Pool"]["p90"], 4),
        "inc_median_m": round(male[0], 6),
        "inc_p90_m": round(male[1], 6),
        "inc_median_f": round(female[0], 6),
        "inc_p90_f": round(female[1], 6),
        "logrank_p_m": float(f"{tests['m']['logrank']:.3e}"),
        "logrank_p_f": float(f"{tests['f']['logrank']:.3e}"),
        "wa_p_m": float(f"{tests['m']['wa'][1]:.3e}"),
        "wa_p_f": float(f"{tests['f']['wa'][1]:.3e}"),
        "table1_matched": matched,
        "table1_total": 3 * len(TABLE1),
        "sites_m": "; ".join(f"{s} {cana.fmt(cm[s]['median'])}/{cana.fmt(tm[s]['median'])}" for s in SITES),
        "test_passed": verdict(male, female),
    }
    detail = {"input": {"name": INPUT[0], "sha256": INPUT[1], "rows": len(rows)}, "summary": summ,
              "gains": {"m": male, "f": female}, "thresholds": {"median": MEDIAN_GAIN, "p90": P90_GAIN},
              "tests": {k: {"logrank": v["logrank"], "wa_table": v["wa"][0], "wa_p": v["wa"][1]}
                        for k, v in tests.items()},
              "table1": {"matched": matched, "of": 3 * len(TABLE1), "rows": t1rows}}
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
        out, _ = run()
    except cana.Refused as e:
        sys.exit(f"e2_2011: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
