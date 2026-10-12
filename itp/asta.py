#!/usr/bin/env python3
"""Astaxanthin and meclizine in the ITP's 2019 cohort, recomputed from the per-mouse data with the paper's own test.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:b5ad2f9a9f04a0b5) is from Harrison et al.,
"Astaxanthin and meclizine extend lifespan in UM-HET3 male mice; fisetin, SG1002 (hydrogen sulfide donor), dimethyl
fumarate, mycophenolic acid, and 4-phenylbutyrate do not significantly affect lifespan in either sex at the doses and
schedules used", GeroScience 46(1), 795-816 (2024): "In genetically heterogeneous (UM-HET3) mice produced by the
CByB6F1 x C3D2F1 cross, the Nrf2 activator astaxanthin (Asta) extended the median male lifespan by 12% (p = 0.003,
log-rank test), while meclizine (Mec), an mTORC1 inhibitor, extended the male lifespan by 8% (p = 0.03)."

Its registered test: refuted if, in the study's own per-mouse lifespans (the ITP's 2019 cohort of UM-HET3 mice at its
three sites, fed astaxanthin at 4,000 ppm or meclizine at 800 ppm from 12 months, or the control diet), the median age
at death of the three sites' males pooled, removed mice left out, rises by less than 6% with astaxanthin or by less
than 4% with meclizine (half the reported 12% and 8%), or if either rise has a two-tailed log-rank p of 0.05 or more,
stratified by site with removed mice censored, as the paper tests it.

The input is the workbook the paper names as its data's home (the Mouse Phenome Database, project ITP1):
ITP_C2019_Lifespan.xlsx (file id 573), the claim's data of record, checked against its SHA-256 and read with the
standard library by itp/rapa.py's reader (its XML parsed as data; nothing in it is run). The statistics are
itp/cana.py's. Every rule below was fixed before any seed existed; the seed is not used, as nothing here is random.

1. The mice. Every row must be of population UM-HET3 and cohort C2019, at site TJL, UM or UT, of sex f or m, with a
   whole number of days as its age, and either dead (status "dead", dead 1) or removed (status "removed", dead 0); its
   group must be one of the cohort's eight, and a row of the three this test uses must carry its group's design in the
   workbook's own columns (DESIGN below: the dose in ppm and the starting age in months, as the workbook spells them).
   The other five groups belong to the paper's null results and are only checked and counted.
2. The medians. For each sex and group, the median age at death of the dead of the three sites pooled (removed mice
   left out): the middle age, or the mean of the two middle ones. A rise is the treated median over the control
   median, less one.
3. The paper's test. The two-tailed log-rank test stratified by site, removed mice censored at removal, for each sex
   and agent against the cohort's controls (itp/cana.py's rule 4).
4. The test's four conditions: the male astaxanthin rise at least 0.06; the male meclizine rise at least 0.04; each
   with a log-rank p below 0.05. test_passed is 1 if all four hold.
5. Beside the test.
   - The paper's Tables 1 to 4, checked: for each sex and for the controls, astaxanthin and meclizine, the count, the
     median and the 90th percentile, pooled (Table 1) and at each site (Tables 2 to 4). The count is the number of
     dead, the median as rule 2 takes it and the 90th percentile the least age by which at least 90% of the dead had
     died (itp/cana.py's rule 2), each rounded to whole days, halves up; tables_matched counts the printed numbers the
     data give.
   - The females' rises and log-rank p.
   - The Wang-Allison test as the Methods state it (itp/cana.py's rule 4): at each site the joint 90th percentile of
     the dead of both groups by R's default rule, the sites' tables summed, Fisher's exact test, two-sided.
   - The males' 90th percentiles pooled, and each site's male medians.

What it cannot check: the cohort beyond the workbook (ages are as the ITP recorded them); the drugs' doses in the food
(the paper measured 46% of the astaxanthin target and 68% of the meclizine target); and why the deposited data differ
from Table 3 for the Michigan males, which the check reports and does not explain.

Writes results/outputs.json (the 19 values a receipt carries) and results/detail.json (every value computed).
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
    spec.loader.exec_module(module)
    return module


rapa = _load("itp_rapa", "rapa.py")
cana = _load("itp_cana", "cana.py")

INPUT = ("ITP_C2019_Lifespan.xlsx", "c3047b7c545460e7e3c98213770c42e7d0ade1ed16f492cc9c7405a7b4d1b798")
POPULATION, COHORT = "UM-HET3", "C2019"
SITES, SEXES = ("TJL", "UM", "UT"), ("m", "f")
GROUPS = ("Control", "Asta", "DMF_16", "MPA", "DMF_9", "Mec", "PBA", "SG1002")
TESTED = ("Control", "Asta", "Mec")
DESIGN = {"Control": ("0", "NA"), "Asta": ("4000", "12"), "Mec": ("800", "12")}
RISE = {"Asta": 0.06, "Mec": 0.04}     # half the reported 12% and 8%
ALPHA = 0.05
LIMIT = 200

# The paper's Tables 1 to 4 as printed: (group, site or "Pool", sex) -> (n, median, 90th percentile), in days.
TABLES = {
    ("Control", "Pool", "m"): (298, 817, 1092), ("Asta", "Pool", "m"): (156, 911, 1159),
    ("Mec", "Pool", "m"): (149, 885, 1156),
    ("Control", "Pool", "f"): (282, 893, 1098), ("Asta", "Pool", "f"): (132, 924, 1088),
    ("Mec", "Pool", "f"): (136, 917, 1106),
    ("Control", "TJL", "m"): (105, 790, 1068), ("Asta", "TJL", "m"): (54, 875, 1067),
    ("Mec", "TJL", "m"): (51, 911, 1104),
    ("Control", "TJL", "f"): (100, 939, 1144), ("Asta", "TJL", "f"): (48, 994, 1116),
    ("Mec", "TJL", "f"): (48, 940, 1137),
    ("Control", "UM", "m"): (94, 861, 1178), ("Asta", "UM", "m"): (51, 983, 1193),
    ("Mec", "UM", "m"): (47, 960, 1191),
    ("Control", "UM", "f"): (90, 896, 1068), ("Asta", "UM", "f"): (44, 892, 1088),
    ("Mec", "UM", "f"): (44, 901, 1106),
    ("Control", "UT", "m"): (99, 814, 1090), ("Asta", "UT", "m"): (51, 905, 1159),
    ("Mec", "UT", "m"): (51, 815, 1053),
    ("Control", "UT", "f"): (92, 878, 1076), ("Asta", "UT", "f"): (40, 916, 1042),
    ("Mec", "UT", "f"): (44, 926, 1081),
}
OUTPUTS = ("n_m", "median_m_control", "median_m_asta", "median_m_mec", "rise_asta", "rise_mec", "logrank_p_asta",
           "logrank_p_mec", "rise_f_asta", "rise_f_mec", "logrank_p_f_asta", "logrank_p_f_mec", "wa_p_asta",
           "wa_p_mec", "p90_m", "sites_m", "tables_matched", "conditions_met", "test_passed")


class Refused(Exception):
    pass


def mice_from_rows(rows):
    """{(group, site, sex): [(age, died)]} for the three groups tested; every row checked against rule 1."""
    out = {(g, s, x): [] for g in TESTED for s in SITES for x in SEXES}
    counts = {g: 0 for g in GROUPS}
    for i, r in enumerate(rows, start=2):
        if r.get("population") != POPULATION or r.get("cohort") != COHORT:
            raise Refused(f"row {i}: population or cohort not as expected: {r}")
        if r.get("site") not in SITES or r.get("sex") not in SEXES:
            raise Refused(f"row {i}: site or sex not as expected: {r}")
        age = r.get("age(days)") or ""
        if not re.fullmatch(r"[0-9]+(\.0+)?", age):
            raise Refused(f"row {i}: age {age!r} is not a whole number of days")
        state = (r.get("status"), r.get("dead"))
        if state not in (("dead", "1"), ("removed", "0")):
            raise Refused(f"row {i}: status and dead disagree: {state}")
        g = r.get("group")
        if g not in GROUPS:
            raise Refused(f"row {i}: group {g!r} is not one of the cohort's")
        counts[g] += 1
        if g in TESTED:
            design = (r.get("Rx(ppm)"), r.get("age_initiation(mo)"))
            if design != DESIGN[g]:
                raise Refused(f"row {i}: group {g} carries {design}, not {DESIGN[g]}")
            out[(g, r["site"], r["sex"])].append((int(float(age)), state[0] == "dead"))
    return out, counts


def pooled(mice, group, sex):
    return [m for s in SITES for m in mice[(group, s, sex)]]


def dead_of(ms):
    return [t for t, d in ms if d]


def summary(ms):
    dead = dead_of(ms)
    return {"count": len(ms), "dead": len(dead), "median": statistics.median(dead), "p90": cana.p90_dead(dead)}


def rise(mice, group, sex):
    return summary(pooled(mice, group, sex))["median"] / summary(pooled(mice, "Control", sex))["median"] - 1


def logrank(mice, group, sex):
    return cana.logrank_strat_p([(mice[("Control", s, sex)], mice[(group, s, sex)]) for s in SITES])


def wang_allison(mice, group, sex):
    return cana.wang_allison([(mice[("Control", s, sex)], mice[(group, s, sex)]) for s in SITES])


def conditions(rises, ps):
    """Rule 4, by name, from the male rises and log-rank p of astaxanthin and meclizine."""
    return {
        "astaxanthin: male median at least 6% above the controls'": rises["Asta"] >= RISE["Asta"],
        "meclizine: male median at least 4% above the controls'": rises["Mec"] >= RISE["Mec"],
        "astaxanthin: log-rank p below 0.05": ps["Asta"] < ALPHA,
        "meclizine: log-rank p below 0.05": ps["Mec"] < ALPHA,
    }


def tables_check(mice):
    """How many of the printed numbers of Tables 1 to 4 the data give, by table, and every comparison."""
    rows, pooled_hits, site_hits = [], 0, 0
    for (g, site, sex), printed in TABLES.items():
        ms = pooled(mice, g, sex) if site == "Pool" else mice[(g, site, sex)]
        got = summary(ms)
        ours = (got["dead"], cana.half_up(got["median"]), cana.half_up(got["p90"]))
        hits = sum(1 for p, o in zip(printed, ours) if p == o)
        if site == "Pool":
            pooled_hits += hits
        else:
            site_hits += hits
        rows.append({"group": g, "site": site, "sex": sex, "printed": list(printed), "data": list(ours)})
    n_pool = 3 * sum(1 for k in TABLES if k[1] == "Pool")
    n_site = 3 * len(TABLES) - n_pool
    return f"Table 1: {pooled_hits} of {n_pool}; Tables 2 to 4: {site_hits} of {n_site}", rows


def fmt(x):
    return str(int(x)) if float(x).is_integer() else f"{x:.1f}"


def sig(p):
    return float(f"{p:.4g}")


def run(seed, inputs="inputs", results="results"):
    rows = rapa.read_rows(os.path.join(inputs, INPUT[0]), INPUT[1])
    mice, counts = mice_from_rows(rows)
    s = {(g, sex): summary(pooled(mice, g, sex)) for g in TESTED for sex in SEXES}
    rises = {g: rise(mice, g, "m") for g in ("Asta", "Mec")}
    ps = {g: logrank(mice, g, "m") for g in ("Asta", "Mec")}
    rises_f = {g: rise(mice, g, "f") for g in ("Asta", "Mec")}
    ps_f = {g: logrank(mice, g, "f") for g in ("Asta", "Mec")}
    wa = {(g, sex): wang_allison(mice, g, sex) for g in ("Asta", "Mec") for sex in SEXES}
    cond = conditions(rises, ps)
    matched, table_rows = tables_check(mice)
    sites = {(g, site): summary(mice[(g, site, "m")]) for g in TESTED for site in SITES}
    values = {
        "n_m": "; ".join(f"{g} {s[(g, 'm')]['count']} ({s[(g, 'm')]['dead']} dead)" for g in TESTED),
        "median_m_control": float(s[("Control", "m")]["median"]),
        "median_m_asta": float(s[("Asta", "m")]["median"]),
        "median_m_mec": float(s[("Mec", "m")]["median"]),
        "rise_asta": round(rises["Asta"], 6), "rise_mec": round(rises["Mec"], 6),
        "logrank_p_asta": sig(ps["Asta"]), "logrank_p_mec": sig(ps["Mec"]),
        "rise_f_asta": round(rises_f["Asta"], 6), "rise_f_mec": round(rises_f["Mec"], 6),
        "logrank_p_f_asta": sig(ps_f["Asta"]), "logrank_p_f_mec": sig(ps_f["Mec"]),
        "wa_p_asta": sig(wa[("Asta", "m")][1]), "wa_p_mec": sig(wa[("Mec", "m")][1]),
        "p90_m": "; ".join(f"{g} {fmt(s[(g, 'm')]['p90'])}" for g in TESTED),
        "sites_m": "; ".join(f"{site} " + "/".join(fmt(sites[(g, site)]["median"]) for g in TESTED) for site in SITES)
                   + " (Control/Asta/Mec medians)",
        "tables_matched": matched,
        "conditions_met": sum(cond.values()),
        "test_passed": int(all(cond.values())),
    }
    out = {k: values[k] for k in OUTPUTS}
    for k, v in out.items():
        if isinstance(v, str) and len(v) > LIMIT:
            raise AssertionError(f"{k}: longer than {LIMIT} characters")
    detail = {
        "input": {"name": INPUT[0], "sha256": INPUT[1], "rows": len(rows), "groups": counts},
        "summaries": {f"{g} {sex}": s[(g, sex)] for g in TESTED for sex in SEXES},
        "sites_m": {f"{g} {site}": sites[(g, site)] for g in TESTED for site in SITES},
        "conditions": cond,
        "rises": {"m": rises, "f": rises_f}, "logrank": {"m": ps, "f": ps_f},
        "wang_allison": {f"{g} {sex}": {"table": wa[(g, sex)][0], "p": wa[(g, sex)][1]} for g, sex in wa},
        "tables": {"matched": matched, "rows": table_rows},
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
        sys.exit(f"asta: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
