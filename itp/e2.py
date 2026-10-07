#!/usr/bin/env python3
"""17-alpha-estradiol late in life and male lifespan in the ITP's 2016 cohort, recomputed from the per-mouse data.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test is from Harrison et al., "17-a-estradiol late in
life extends lifespan in aging UM-HET3 male mice; nicotinamide riboside and three other drugs do not affect lifespan in
either sex", Aging Cell 20(5) (2021): 17aE2 "extended median male lifespan by 19% (p < 0.0001, log-rank test) and 11%
(p = 0.007) when fed at 14.4 ppm starting at 16 and 20 months, respectively. 90th percentile lifespans were extended 7%
(p = 0.004, Wang-Allison test) and 5% (p = 0.17)."

Its registered test: refuted if, in the study's own per-mouse lifespans (the ITP's 2016 cohort of UM-HET3 males given
17aE2 at 14.4 ppm from 16 or from 20 months, and the cohort's control males, at its three sites; removed mice left
out of medians and 90th percentiles), the median age at death rises by less than 9.5% (from 16 months) or 5.5% (from
20 months), or the age at 90th percentile survival by less than 3.5% or 2.5%, half the reported gains, each taken as
the mean of the three site values, as the paper's Table 1 pools them.

The input is the workbook the ITP deposited for the cohort, ITP_C2016_Lifespan.xlsx (Mouse Phenome Database, project
ITP1), the same file itp/cana.py reads; it is checked against its SHA-256 and read by itp/rapa.py's reader. Every rule
below was fixed before any seed existed; the seed is not used, as nothing here is random.

1. The mice: every row is checked by itp/cana.py's rule 1 (cohort C2016, three sites, whole-day ages, dead or
   removed; anything else refused). The groups are "Control" and the two late starts, "17aE2_16m" and "17aE2_20m",
   males only, as assigned; a kept row must also carry its group's design in the workbook's own columns (dose 0 for
   the controls; dose 14.4 ppm and a start at 16 or at 20 months for the late starts), or the run is refused. Counts
   include removed mice, as Table 1's do, and mice that died or were removed before their start stay in their group.
2. Medians and 90th percentiles of the dead, per site, and pooled as the mean of the three site values, as in
   itp/cana.py (rules 2 and 3 there): the rule that reproduces the paper's Table 1, which prints the pooled values.
   A group with no deaths at a site is refused.
3. Beside the test, the paper's own tests, as in itp/cana.py (rule 4 there): the log-rank test stratified by site
   (removed mice censored) and the Wang-Allison test as Fisher's exact test on the sites' summed tables.
4. The paper's tables, checked: Table 1's nine male numbers (count, median and 90th percentile of the controls and of
   the two late starts) and Table 2's nine male site medians, each compared after rounding the data's value to whole
   days, halves up. Table 1 is expected to agree in full; Table 2 is reported as found (its site medians do not all
   agree with Table 1's pooled ones: its controls, 752, 826 and 799, average 792, where Table 1 prints 787).

test_passed is 1 if the four gains, by the site-mean rule, reach 9.5% and 5.5% (medians, from 16 and from 20 months)
and 3.5% and 2.5% (90th percentiles); else 0.

What it cannot check: why Table 2 differs from the data in places, or why the log-rank p from 20 months comes out
near 0.0064 where Table 1 prints 0.007 (the paper does not say); the cohort the paper compares with (17aE2 from 10
months, Strong et al. 2016), whose data are another workbook.

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

INPUT = cana.INPUT
SITES = cana.SITES
GROUPS = ("Control", "17aE2_16m", "17aE2_20m")
# Each group's design as the workbook records it: (dose in ppm, start in months; None for the controls).
DESIGN = {"Control": ("0", None), "17aE2_16m": ("14.4", "16"), "17aE2_20m": ("14.4", "20")}
THRESHOLDS = {"median_16": 0.095, "median_20": 0.055, "p90_16": 0.035, "p90_20": 0.025}

# Table 1, males: group -> (count, median, 90th percentile), days.
TABLE1 = {"Control": (303, 787, 1047), "17aE2_16m": (156, 933, 1120), "17aE2_20m": (159, 871, 1103)}
# Table 2, males: group -> site medians (TJL, UM, UT), days.
TABLE2 = {"Control": (752, 826, 799), "17aE2_16m": (906, 943, 955), "17aE2_20m": (896, 900, 840)}


def males(rows):
    """{group: {site: [(age, died)]}} for the three male groups, every row checked by itp/cana.py's rule 1."""
    out = {g: {s: [] for s in SITES} for g in GROUPS}
    for i, r in enumerate(rows, start=2):
        cana.mice_from_rows([r])              # refuses a malformed row (it keeps nothing here)
        if r.get("sex") == "m" and r.get("group") in GROUPS:
            dose, start = DESIGN[r["group"]]
            if r.get("dose") != dose or (r.get("age_initiation") or None) != start:
                raise cana.Refused(f"row {i}: group {r['group']} with dose {r.get('dose')!r} and start "
                                   f"{r.get('age_initiation')!r}, not {dose!r} and {start!r}")
            out[r["group"]][r["site"]].append((int(float(r["age"])), r["status"] == "dead"))
    return out


def summary(mice):
    """Per group: each site's count, median and 90th percentile of the dead, and the Pool (the mean of the sites)."""
    s = {}
    for g in GROUPS:
        per = {}
        for site in SITES:
            dead = [t for t, d in mice[g][site] if d]
            if not dead:
                raise cana.Refused(f"{g} at {site}: no deaths")
            per[site] = {"count": len(mice[g][site]), "dead": len(dead),
                         "median": cana.median_dead(dead), "p90": cana.p90_dead(dead)}
        per["Pool"] = {"count": sum(per[x]["count"] for x in SITES),
                       "median": sum(per[x]["median"] for x in SITES) / 3,
                       "p90": sum(per[x]["p90"] for x in SITES) / 3}
        s[g] = per
    return s


def gains(s):
    """The four gains over the controls, by the site-mean rule."""
    c = s["Control"]["Pool"]
    out = {}
    for g, tag in (("17aE2_16m", "16"), ("17aE2_20m", "20")):
        t = s[g]["Pool"]
        out[f"median_{tag}"] = t["median"] / c["median"] - 1
        out[f"p90_{tag}"] = t["p90"] / c["p90"] - 1
    return out


def verdict(g):
    return int(all(g[k] >= v for k, v in THRESHOLDS.items()))


def run(inputs="inputs", results="results"):
    rows = rapa.read_rows(os.path.join(inputs, INPUT[0]), INPUT[1])
    mice = males(rows)
    s = summary(mice)
    gn = gains(s)
    tests = {}
    for g, tag in (("17aE2_16m", "16"), ("17aE2_20m", "20")):
        strata = [(mice["Control"][site], mice[g][site]) for site in SITES]
        tests[tag] = {"logrank": cana.logrank_strat_p(strata), "wa": cana.wang_allison(strata)}
    t1 = {g: (s[g]["Pool"]["count"], cana.half_up(s[g]["Pool"]["median"]), cana.half_up(s[g]["Pool"]["p90"]))
          for g in GROUPS}
    t1_matched = sum(1 for g in GROUPS for a, b in zip(TABLE1[g], t1[g]) if a == b)
    t2 = {g: tuple(cana.half_up(s[g][site]["median"]) for site in SITES) for g in GROUPS}
    t2_matched = sum(1 for g in GROUPS for a, b in zip(TABLE2[g], t2[g]) if a == b)
    c = s["Control"]["Pool"]
    out = {
        "n_m_control": c["count"],
        "n_m_e2_16": s["17aE2_16m"]["Pool"]["count"],
        "n_m_e2_20": s["17aE2_20m"]["Pool"]["count"],
        "median_m_control": round(c["median"], 4),
        "median_m_e2_16": round(s["17aE2_16m"]["Pool"]["median"], 4),
        "median_m_e2_20": round(s["17aE2_20m"]["Pool"]["median"], 4),
        "inc_median_16": round(gn["median_16"], 6),
        "inc_median_20": round(gn["median_20"], 6),
        "inc_p90_16": round(gn["p90_16"], 6),
        "inc_p90_20": round(gn["p90_20"], 6),
        "logrank_p_16": float(f"{tests['16']['logrank']:.3e}"),
        "logrank_p_20": float(f"{tests['20']['logrank']:.3e}"),
        "wa_p_16": float(f"{tests['16']['wa'][1]:.3e}"),
        "wa_p_20": float(f"{tests['20']['wa'][1]:.3e}"),
        "table1_matched": t1_matched,
        "table2_matched": t2_matched,
        "sites_m": "; ".join(f"{site} {cana.fmt(s['Control'][site]['median'])}/{cana.fmt(s['17aE2_16m'][site]['median'])}/"
                             f"{cana.fmt(s['17aE2_20m'][site]['median'])}" for site in SITES),
        "test_passed": verdict(gn),
    }
    detail = {"input": {"name": INPUT[0], "sha256": INPUT[1], "rows": len(rows)}, "summary": s, "gains": gn,
              "thresholds": THRESHOLDS,
              "tests": {k: {"logrank": v["logrank"], "wa_table": v["wa"][0], "wa_p": v["wa"][1]} for k, v in tests.items()},
              "table1": {"printed": TABLE1, "data": t1, "matched": t1_matched, "of": 9},
              "table2": {"printed": TABLE2, "data": t2, "matched": t2_matched, "of": 9}}
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
        sys.exit(f"e2: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
