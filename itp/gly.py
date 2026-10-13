#!/usr/bin/env python3
"""Glycine in the ITP's 2014 cohort, recomputed from the per-mouse data with the paper's own criteria.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:f62aa4592440bbed) is from Miller et al.,
"Glycine supplementation extends lifespan of male and female mice", Aging Cell 18(3), e12953 (2019): "Elevated glycine
led to a small (4%-6%) but statistically significant lifespan increase, as well as an increase in maximum lifespan, in
both males (p = 0.002) and females (p < 0.001)."

Its registered test: refuted if, in the study's deposited per-mouse lifespans (the ITP's 2014 cohort of UM-HET3 mice at
its three sites, fed 8% glycine from 9 months or the control diet), for either sex the median age at death (the dead of
the three sites pooled) rises by less than 2% (half the 4% printed), or the log-rank test stratified by site (removed
mice censored) gives p of 0.05 or more, or the Wang-Allison test the paper uses for maximum lifespan (survivors past each
site's joint 90th percentile, tables summed, Fisher's exact test) gives p of 0.05 or more.

The input is the cohort's workbook at the Mouse Phenome Database (project ITP2014, whose participants are the paper's
authors): ITP_C2014_Lifespan.xlsx (file id 836), the claim's data of record, checked against its SHA-256 and read with
the standard library by itp/rapa.py's reader (its XML parsed as data; nothing in it is run). The statistics are
itp/cana.py's. Every rule below was fixed before any seed existed; the seed is not used, as nothing here is random.

1. The mice. Every row must be of population UM-HET3 and cohort C2014, at site TJL, UM or UT, of sex f or m, with a
   whole number of days as its age, and either dead (status "dead", dead 1) or removed (status "removed", dead 0); its
   group must be one of the cohort's six, and a row of the two this test uses must carry its group's design in the
   workbook's own columns (DESIGN below: the dose in ppm, 80,000 being 8% of the diet, and the starting age in months).
   The other four groups (aspirin at two doses, inulin, TM5441) are only checked and counted.
2. The medians. For each sex and group, the median age at death of the dead of the three sites pooled (removed mice
   left out, as the paper's Methods leave them out): the middle age, or the mean of the two middle ones. A rise is the
   glycine median over the control median, less one.
3. The paper's principal criterion: the two-tailed log-rank test for each sex, stratified by site, removed mice censored
   at removal (itp/cana.py's rule 4); for both sexes together, stratified by site and sex.
4. The paper's criterion for maximum lifespan, as its Methods and Table 1 state it: at each site (and each sex, for both
   sexes together) the joint 90th percentile of the dead of both groups by R's default rule; the mice alive past it and
   the dead at or before it, in each group; the sites' tables summed; Fisher's exact test, two-sided.
5. The test's six conditions: for each sex, the rise at least 0.02, the log-rank p below 0.05, the Wang-Allison p below
   0.05. test_passed is 1 if all six hold.
6. Beside the test.
   - Table 1, checked: for each sex, group and site (and pooled) the count of mice, the median and the 90th percentile
     (the least age by which at least 90% of the dead had died), rounded to whole days, halves up; and the glycine rows'
     log-rank and Wang-Allison p, the data's p written to the printed number's decimals. tables_matched counts each.
   - The abstract's p-values beside Table 1's and the data's.
   - The Wang-Allison test under three other readings of "the age at which 90% have died" (the least age by which 90%
     of the dead had died; the Kaplan-Meier estimate with removed mice censored; one cut for the three sites pooled),
     so that the maximum-lifespan verdict can be seen not to rest on the choice of quantile.
   - Each site's log-rank p, by sex and for both sexes.

What it cannot check: the cohort beyond the workbook (ages are as the ITP recorded them); whether mice still alive when
the paper was written (its Methods say some were) account for the differences between its Table 1 and the final data,
which the check reports and does not explain.

Writes results/outputs.json (the 20 values a receipt carries) and results/detail.json (every value computed).
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

INPUT = ("ITP_C2014_Lifespan.xlsx", "baaf03bfee266d3fbffc21ae7cb38510ebed8e73042b3d88719d7b424ed42d05")
POPULATION, COHORT = "UM-HET3", "C2014"
SITES, SEXES = ("TJL", "UM", "UT"), ("f", "m")
GROUPS = ("Control", "Gly", "Asp_60", "Asp_200", "Inu", "TM")
TESTED = ("Control", "Gly")
DESIGN = {"Control": ("0", None), "Gly": ("80000", "9")}
RISE, ALPHA = 0.02, 0.05
LIMIT = 200

# Table 1 as printed: (group, site or "Pool", sex) -> (count, median, P90), in days.
TABLE = {
    ("Control", "Pool", "f"): (280, 897, 1109), ("Gly", "Pool", "f"): (136, 929, 1129),
    ("Control", "Pool", "m"): (300, 832, 1059), ("Gly", "Pool", "m"): (156, 884, 1107),
    ("Control", "TJL", "f"): (96, 904, 1099), ("Gly", "TJL", "f"): (48, 959, 1190),
    ("Control", "TJL", "m"): (102, 873, 1068), ("Gly", "TJL", "m"): (54, 864, 1107),
    ("Control", "UM", "f"): (92, 884, 1139), ("Gly", "UM", "f"): (44, 925, 1129),
    ("Control", "UM", "m"): (99, 894, 1084), ("Gly", "UM", "m"): (51, 901, 1138),
    ("Control", "UT", "f"): (92, 882, 1109), ("Gly", "UT", "f"): (44, 872, 1106),
    ("Control", "UT", "m"): (99, 743, 977), ("Gly", "UT", "m"): (51, 810, 1073),
}
# Table 1's glycine rows: (site or "Pool", sex or "both") -> (log-rank p, Wang-Allison p), as printed.
TABLE_P = {
    ("Pool", "f"): ("0.006", "0.7"), ("Pool", "m"): ("0.002", "0.0005"), ("Pool", "both"): ("0.00004", "0.006"),
    ("TJL", "f"): ("0.01", "0.04"), ("TJL", "m"): ("0.3", "0.27"), ("TJL", "both"): ("0.013", "0.02"),
    ("UM", "f"): ("0.2", "0.77"), ("UM", "m"): ("0.1", "0.13"), ("UM", "both"): ("0.053", "0.52"),
    ("UT", "f"): ("0.8", "1.00"), ("UT", "m"): ("0.006", "0.04"), ("UT", "both"): ("0.026", "0.83"),
}
ABSTRACT_P = {"m": "0.002", "f": "< 0.001"}
OUTPUTS = ("n", "median_f_control", "median_f_gly", "median_m_control", "median_m_gly", "rise_f", "rise_m",
           "logrank_p_f", "logrank_p_m", "wa_p_f", "wa_p_m", "wa_readings", "p90", "logrank_p_both", "sites_logrank",
           "abstract_p", "tables_matched", "conditions_met", "conditions_total", "test_passed")


class Refused(Exception):
    pass


def mice_from_rows(rows):
    """{(group, site, sex): [(age, died)]} for the two groups tested; every row checked against rule 1."""
    out = {(g, s, x): [] for g in TESTED for s in SITES for x in SEXES}
    counts = {g: 0 for g in GROUPS}
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
        counts[g] += 1
        if g in TESTED:
            design = (r.get("dose"), r.get("age_initiation"))
            if design != DESIGN[g]:
                raise Refused(f"row {i}: group {g} carries {design}, not {DESIGN[g]}")
            out[(g, r["site"], r["sex"])].append((int(float(age)), state[0] == "dead"))
    return out, counts


def pooled(mice, group, sex):
    return [m for s in SITES for m in mice[(group, s, sex)]]


def summary(ms):
    dead = [t for t, d in ms if d]
    return {"count": len(ms), "dead": len(dead), "median": statistics.median(dead), "p90": cana.p90_dead(dead)}


def strata(mice, sex, sites=SITES):
    sexes = SEXES if sex == "both" else (sex,)
    return [(mice[("Control", s, x)], mice[("Gly", s, x)]) for s in sites for x in sexes]


def km_cut(ms, q=0.9):
    """The least age at which the Kaplan-Meier survival of the mice (removed censored) falls to 1 - q or below."""
    s, ages = 1.0, sorted({t for t, d in ms if d})
    for t in ages:
        n = sum(1 for x, _ in ms if x >= t)
        d = sum(1 for x, dd in ms if x == t and dd)
        s *= 1 - d / n
        if s <= 1 - q + 1e-12:
            return t
    return ages[-1]


def wang_allison_by(pairs, cut_of):
    """Rule 4's table with any rule for the cut, applied to each (control, glycine) pair; the summed table and its p."""
    table = [[0, 0], [0, 0]]
    for ctl, trt in pairs:
        cut = cut_of(ctl + trt)
        for row, ms in ((0, ctl), (1, trt)):
            table[row][0] += sum(1 for t, _ in ms if t > cut)
            table[row][1] += sum(1 for t, d in ms if d and t <= cut)
    return table, cana.fisher_two_sided(table)


def readings(mice, sex):
    """The Wang-Allison p under rule 4 and under the three other readings of rule 6."""
    pairs = strata(mice, sex)
    dead = lambda ms: [t for t, d in ms if d]  # noqa: E731
    out = {"R's default quantile of the dead, per site (rule 4)": cana.wang_allison(pairs)[1],
           "least age by which 90% of the dead had died, per site": wang_allison_by(pairs, lambda ms: cana.p90_dead(dead(ms)))[1],
           "Kaplan-Meier, removed censored, per site": wang_allison_by(pairs, km_cut)[1]}
    joint = [m for c, t in pairs for m in c + t]
    cut = cana.quantile7(dead(joint), 0.9)
    out["one cut for the three sites pooled"] = wang_allison_by(
        [([m for c, _ in pairs for m in c], [m for _, t in pairs for m in t])], lambda ms: cut)[1]
    return out


def conditions(rises, logrank, wa):
    """Rule 5, by name, from each sex's rise, log-rank p and Wang-Allison p."""
    words = {"f": "females", "m": "males"}
    out = {}
    for x in SEXES:
        out[f"{words[x]}: median at least 2% above the controls'"] = rises[x] >= RISE
        out[f"{words[x]}: log-rank p below 0.05"] = logrank[x] < ALPHA
        out[f"{words[x]}: Wang-Allison p below 0.05"] = wa[x] < ALPHA
    return out


def as_printed(p, printed):
    """The data's p written to the printed number's decimals."""
    decimals = len(printed.split(".")[1]) if "." in printed else 0
    return f"{p:.{decimals}f}"


def tables_check(mice):
    """How many of Table 1's numbers the data give, by kind, and every comparison."""
    rows, hits = [], {"counts": 0, "medians": 0, "P90": 0, "log-rank p": 0, "Wang-Allison p": 0}
    for (g, site, sex), printed in TABLE.items():
        ms = pooled(mice, g, sex) if site == "Pool" else mice[(g, site, sex)]
        got = summary(ms)
        ours = (got["count"], cana.half_up(got["median"]), cana.half_up(got["p90"]))
        for kind, p, o in zip(("counts", "medians", "P90"), printed, ours):
            hits[kind] += int(p == o)
        rows.append({"group": g, "site": site, "sex": sex, "printed": list(printed), "data": list(ours)})
    for (site, sex), (lr, wa) in TABLE_P.items():
        pairs = strata(mice, sex, SITES if site == "Pool" else (site,))
        ours = (as_printed(cana.logrank_strat_p(pairs), lr), as_printed(cana.wang_allison(pairs)[1], wa))
        hits["log-rank p"] += int(ours[0] == lr)
        hits["Wang-Allison p"] += int(ours[1] == wa)
        rows.append({"site": site, "sex": sex, "printed": [lr, wa], "data": list(ours)})
    n = {"counts": len(TABLE), "medians": len(TABLE), "P90": len(TABLE), "log-rank p": len(TABLE_P),
         "Wang-Allison p": len(TABLE_P)}
    return "; ".join(f"{k} {hits[k]} of {n[k]}" for k in hits), rows


def fmt(x):
    return str(int(x)) if float(x).is_integer() else f"{x:.1f}"


def sig(p):
    return float(f"{p:.4g}")


def run(seed, inputs="inputs", results="results"):
    rows = rapa.read_rows(os.path.join(inputs, INPUT[0]), INPUT[1])
    mice, counts = mice_from_rows(rows)
    s = {(g, x): summary(pooled(mice, g, x)) for g in TESTED for x in SEXES}
    rises = {x: s[("Gly", x)]["median"] / s[("Control", x)]["median"] - 1 for x in SEXES}
    logrank = {x: cana.logrank_strat_p(strata(mice, x)) for x in SEXES + ("both",)}
    wa_tables = {x: cana.wang_allison(strata(mice, x)) for x in SEXES + ("both",)}
    wa = {x: wa_tables[x][1] for x in wa_tables}
    alt = {x: readings(mice, x) for x in SEXES}
    cond = conditions(rises, logrank, wa)
    matched, table_rows = tables_check(mice)
    site_lr = {(site, x): cana.logrank_strat_p(strata(mice, x, (site,))) for site in SITES for x in SEXES + ("both",)}
    values = {
        "n": "; ".join(f"{x} " + ", ".join(f"{g} {s[(g, x)]['count']} ({s[(g, x)]['dead']} dead)" for g in TESTED)
                       for x in SEXES),
        "median_f_control": float(s[("Control", "f")]["median"]), "median_f_gly": float(s[("Gly", "f")]["median"]),
        "median_m_control": float(s[("Control", "m")]["median"]), "median_m_gly": float(s[("Gly", "m")]["median"]),
        "rise_f": round(rises["f"], 6), "rise_m": round(rises["m"], 6),
        "logrank_p_f": sig(logrank["f"]), "logrank_p_m": sig(logrank["m"]),
        "wa_p_f": sig(wa["f"]), "wa_p_m": sig(wa["m"]),
        "wa_readings": "; ".join(f"{x} {sig(min(alt[x].values()))} to {sig(max(alt[x].values()))}" for x in SEXES)
                       + f" over {len(alt['f'])} readings",
        "p90": "; ".join(f"{x} " + ", ".join(f"{g} {fmt(s[(g, x)]['p90'])}" for g in TESTED) for x in SEXES),
        "logrank_p_both": sig(logrank["both"]),
        "sites_logrank": "; ".join(f"{site} " + "/".join(f"{sig(site_lr[(site, x)])}" for x in SEXES + ("both",))
                                   for site in SITES) + " (f/m/both)",
        "abstract_p": (f"abstract m {ABSTRACT_P['m']}, f {ABSTRACT_P['f']}; Table 1 m {TABLE_P[('Pool', 'm')][0]}, "
                       f"f {TABLE_P[('Pool', 'f')][0]}; data m {sig(logrank['m'])}, f {sig(logrank['f'])}"),
        "tables_matched": matched,
        "conditions_met": sum(cond.values()), "conditions_total": len(cond), "test_passed": int(all(cond.values())),
    }
    out = {k: values[k] for k in OUTPUTS}
    for k, v in out.items():
        if isinstance(v, str) and len(v) > LIMIT:
            raise AssertionError(f"{k}: longer than {LIMIT} characters: {v}")
    detail = {
        "input": {"name": INPUT[0], "sha256": INPUT[1], "rows": len(rows), "groups": counts},
        "summaries": {f"{g} {x}": s[(g, x)] for g in TESTED for x in SEXES},
        "sites": {f"{g} {site} {x}": summary(mice[(g, site, x)]) for g in TESTED for site in SITES for x in SEXES},
        "conditions": cond, "rises": rises, "logrank": logrank,
        "wang_allison": {x: {"table": wa_tables[x][0], "p": wa_tables[x][1]} for x in wa_tables},
        "wang_allison_readings": alt, "sites_logrank": {f"{k[0]} {k[1]}": v for k, v in site_lr.items()},
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
        sys.exit(f"gly: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
