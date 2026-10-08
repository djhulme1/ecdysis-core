#!/usr/bin/env python3
"""Acarbose at three doses and lifespan in the ITP's 2013 cohort, recomputed from the per-mouse data.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:e6c402de6e773a31) is from Harrison et al.,
"Acarbose improves health and lifespan in aging HET3 mice", Aging Cell 18(2) (2019): "The two higher doses produced
16% or 17% increases in median longevity of males, but only 4% or 5% increases in females. Age at the 90th
percentile was increased significantly (8%-11%) in males at each dose, but was significantly increased (3%) in
females only at 1,000 ppm."

Its registered test: refuted if, in the study's own per-mouse lifespans (the ITP's 2013 cohort of UM-HET3 mice fed
acarbose at 400, 1,000 or 2,500 ppm from 8 months, or the control diet, at its three sites), with medians and 90th
percentiles of the pooled deaths, removed mice left out, as Table 1 gives them: the male median rises by less than
8.5% at 1,000 ppm or 8% at 2,500 ppm; the male age at 90th percentile survival by less than 5.5%, 5.5% or 4% at 400,
1,000 or 2,500 ppm (half each reported gain); or the female median gain at 1,000 or 2,500 ppm is not below the male
gain at that dose.

The input is the workbook the ITP deposited for the cohort, ITP_C2013_Lifespan.xlsx (Mouse Phenome Database, project
ITP1), checked against its SHA-256 and read by itp/rapa.py's reader (its XML parsed as data; nothing in it is run).
Every rule below was fixed before any seed existed; the seed is not used, as nothing here is random.

1. The mice. Every row must be of cohort C2013, at site TJL, UM or UT, of sex f or m, with a whole number of days as
   its age, and either dead (status "dead", dead 1) or removed (status "removed", dead 0); anything else is refused.
   The groups are "Control", "ACA_lo", "ACA_mid" and "ACA_hi", as assigned (the cohort's ursolic acid group is
   checked and not used); a kept row must also carry its group's design in the workbook's own columns (dose 0 and no
   start for the controls; 400, 1000 or 2500 ppm from 8 months), or the run is refused.
2. Table 1's statistics, for each sex and group: the median of the pooled deaths of the three sites (the mean of the
   two middle ages when their count is even) and the 90th percentile, the least age by which at least 90% of the
   pooled dead had died; removed mice are left out of both. This is the rule that reproduces Table 1, whose counts
   are the deaths (its male controls, 273, are the cohort's dead male controls; 39 more were removed). A gain is the
   acarbose value over the control value, less one.
3. Beside the test, the paper's own tests, as its Table 1 note and methods describe them and as itp/cana.py computes
   them: the two-sided log-rank test on the pooled data stratified by site, removed mice censored at removal; and
   the Wang-Allison test, survivors counted at each site's 90th percentile of the joint deaths (R's type 7) and the
   three sites' tables summed for one Fisher exact test.
4. The paper's tables, checked: Table 1's 24 numbers (each sex: the count, median and 90th percentile of the controls
   and the three doses) and Table 2's 24 site medians, each compared after rounding the data's value to whole days,
   halves up. The research for the claim found 23 of Table 1's (the female median at 1,000 ppm is 932 in the data
   and 933 in print) and all of Table 2's.

test_passed is 1 if the male median gains reach 8.5% (1,000 ppm) and 8% (2,500 ppm), the male 90th-percentile gains
5.5%, 5.5% and 4% (400, 1,000 and 2,500 ppm), and the female median gain is below the male one at 1,000 and at 2,500
ppm; else 0.

What it cannot check: why the female median at 1,000 ppm prints a day higher than the data give; the significance
statements, which the test leaves to the tests beside it (rule 3); the cohort's other arms and the 2012 cohort's
controls (Table 1's Cont_12), which this claim does not concern.

Writes results/outputs.json (17 values) and results/detail.json.
"""

import importlib.util
import json
import os
import re
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("itp_cana", os.path.join(HERE, "cana.py"))
cana = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cana)
rapa = cana.rapa

INPUT = ("ITP_C2013_Lifespan.xlsx", "e998a849596e53c895c00ca2fb3c85968250767529f1ab23ac56360551da0d57")
COHORT, SITES, SEXES = "C2013", ("TJL", "UM", "UT"), ("m", "f")
GROUPS = ("Control", "ACA_lo", "ACA_mid", "ACA_hi")
DOSES = ("ACA_lo", "ACA_mid", "ACA_hi")
OTHER = ("UA",)
# Each group's design as the workbook records it: (dose in ppm, start in months; None for the controls).
DESIGN = {"Control": ("0", None), "ACA_lo": ("400", "8"), "ACA_mid": ("1000", "8"), "ACA_hi": ("2500", "8")}
MEDIAN_GAIN = {"ACA_mid": 0.085, "ACA_hi": 0.08}                      # half the reported 17% and 16%
P90_GAIN = {"ACA_lo": 0.055, "ACA_mid": 0.055, "ACA_hi": 0.04}        # half the reported 11%, 11% and 8%

# Table 1 as printed: sex -> group -> (count, median, 90th percentile), days.
TABLE1 = {"f": {"Control": (287, 889, 1097), "ACA_lo": (139, 887, 1123), "ACA_mid": (142, 933, 1125),
                "ACA_hi": (152, 922, 1125)},
          "m": {"Control": (273, 830, 1089), "ACA_lo": (147, 918, 1211), "ACA_mid": (161, 975, 1210),
                "ACA_hi": (163, 964, 1181)}}
# Table 2 as printed: sex -> group -> site medians (TJL, UM, UT), days.
TABLE2 = {"f": {"Control": (890, 870, 897), "ACA_lo": (887, 871, 923), "ACA_mid": (934, 890, 950),
                "ACA_hi": (938, 931, 917)},
          "m": {"Control": (803, 912, 807), "ACA_lo": (880, 924, 919), "ACA_mid": (967, 1033, 914),
                "ACA_hi": (960, 975, 957)}}
# Table 1's p-values as printed, for the detail only: sex -> group -> (log-rank, Wang-Allison).
PRINTED_P = {"f": {"ACA_lo": ("0.03", "0.37"), "ACA_mid": ("0.003", "0.007"), "ACA_hi": ("0.006", "0.10")},
             "m": {"ACA_lo": ("<0.0001", "0.0004"), "ACA_mid": ("<0.0001", "0.0004"), "ACA_hi": ("<0.0001", "0.0001")}}


class Refused(Exception):
    """An input that is not what the rules say it must be."""


def mice_from_rows(rows):
    """Rule 1: {(group, site, sex): [(age, died)]} for the four groups, every row checked."""
    out = {(g, s, x): [] for g in GROUPS for s in SITES for x in SEXES}
    for i, r in enumerate(rows, start=2):
        if r.get("cohort") != COHORT or r.get("site") not in SITES or r.get("sex") not in SEXES:
            raise Refused(f"row {i}: cohort, site or sex not as expected: {r}")
        age = r.get("age") or ""
        if not re.fullmatch(r"[0-9]+(\.0+)?", age):
            raise Refused(f"row {i}: age {age!r} is not a whole number of days")
        state = (r.get("status"), r.get("dead"))
        if state not in (("dead", "1"), ("removed", "0")):
            raise Refused(f"row {i}: status and dead disagree: {state}")
        g = r.get("group")
        if g in GROUPS:
            dose, start = DESIGN[g]
            if r.get("dose") != dose or (r.get("age_initiation") or None) != start:
                raise Refused(f"row {i}: group {g} with dose {r.get('dose')!r} and start {r.get('age_initiation')!r},"
                              f" not {dose!r} and {start!r}")
            out[(g, r["site"], r["sex"])].append((int(float(age)), state[0] == "dead"))
        elif g not in OTHER:
            raise Refused(f"row {i}: an unexpected group {g!r}")
    return out


def p90_dead(ages):
    return cana.p90_dead(ages)


def summary(mice):
    """Rule 2 and Table 2's site medians: sex -> group -> {count, dead, removed, median, p90, sites}."""
    out = {}
    for sex in SEXES:
        out[sex] = {}
        for g in GROUPS:
            every = [m for s in SITES for m in mice[(g, s, sex)]]
            dead = [t for t, d in every if d]
            sites = {}
            for s in SITES:
                ds = [t for t, d in mice[(g, s, sex)] if d]
                if not ds:
                    raise Refused(f"{g}, {sex}, {s}: no deaths")
                sites[s] = statistics.median(ds)
            out[sex][g] = {"mice": len(every), "dead": len(dead), "removed": len(every) - len(dead),
                           "median": statistics.median(dead), "p90": p90_dead(dead), "sites": sites}
    return out


def gains(s):
    out = {}
    for sex in SEXES:
        c = s[sex]["Control"]
        for g in DOSES:
            out[f"median_{sex}_{g}"] = s[sex][g]["median"] / c["median"] - 1
            out[f"p90_{sex}_{g}"] = s[sex][g]["p90"] / c["p90"] - 1
    return out


def verdict(gn):
    """The registered test: 1 if every condition holds, else 0; and each condition."""
    conditions = {}
    for g, v in MEDIAN_GAIN.items():
        conditions[f"male median gain at {g} >= {v}"] = gn[f"median_m_{g}"] >= v
    for g, v in P90_GAIN.items():
        conditions[f"male p90 gain at {g} >= {v}"] = gn[f"p90_m_{g}"] >= v
    for g in ("ACA_mid", "ACA_hi"):
        conditions[f"female median gain below the male at {g}"] = gn[f"median_f_{g}"] < gn[f"median_m_{g}"]
    return int(all(conditions.values())), conditions


def tables_check(s):
    t1, t2 = [], []
    for sex in SEXES:
        for g in GROUPS:
            ours = (s[sex][g]["dead"], cana.half_up(s[sex][g]["median"]), cana.half_up(s[sex][g]["p90"]))
            t1.append({"sex": sex, "group": g, "printed": list(TABLE1[sex][g]), "data": list(ours),
                       "matched": sum(1 for a, b in zip(TABLE1[sex][g], ours) if a == b)})
            site = tuple(cana.half_up(s[sex][g]["sites"][x]) for x in SITES)
            t2.append({"sex": sex, "group": g, "printed": list(TABLE2[sex][g]), "data": list(site),
                       "matched": sum(1 for a, b in zip(TABLE2[sex][g], site) if a == b)})
    return t1, t2


def pct(x):
    return round(x, 6)


def p3(x):
    return f"{x:.2e}"


def run(inputs="inputs", results="results"):
    rows = rapa.read_rows(os.path.join(inputs, INPUT[0]), INPUT[1])
    mice = mice_from_rows(rows)
    s = summary(mice)
    gn = gains(s)
    passed, conditions = verdict(gn)
    tests = {}
    for sex in SEXES:
        for g in DOSES:
            strata = [(mice[("Control", site, sex)], mice[(g, site, sex)]) for site in SITES]
            table, wa = cana.wang_allison(strata)
            tests[f"{sex}_{g}"] = {"logrank": cana.logrank_strat_p(strata), "wa": wa, "wa_table": table}
    t1, t2 = tables_check(s)

    def row(key, sex):
        return "/".join(cana.fmt(s[sex][g][key]) for g in GROUPS)

    def plist(kind):
        return "; ".join(f"{sex} " + "/".join(p3(tests[f"{sex}_{g}"][kind]) for g in DOSES) for sex in SEXES)
    out = {
        "median_m": row("median", "m"),
        "p90_m": row("p90", "m"),
        "median_f": row("median", "f"),
        "p90_f": row("p90", "f"),
        "inc_median_m_mid": pct(gn["median_m_ACA_mid"]),
        "inc_median_m_hi": pct(gn["median_m_ACA_hi"]),
        "inc_p90_m_lo": pct(gn["p90_m_ACA_lo"]),
        "inc_p90_m_mid": pct(gn["p90_m_ACA_mid"]),
        "inc_p90_m_hi": pct(gn["p90_m_ACA_hi"]),
        "inc_median_f_mid": pct(gn["median_f_ACA_mid"]),
        "inc_median_f_hi": pct(gn["median_f_ACA_hi"]),
        "deaths": "; ".join(f"{sex} " + "/".join(str(s[sex][g]["dead"]) for g in GROUPS) for sex in SEXES),
        "logrank_p": plist("logrank"),
        "wa_p": plist("wa"),
        "table1_matched": sum(r["matched"] for r in t1),
        "table2_matched": sum(r["matched"] for r in t2),
        "test_passed": passed,
    }
    for k, v in out.items():
        if isinstance(v, str) and len(v) > 200:
            raise AssertionError(f"{k}: longer than 200 characters")
    detail = {"input": {"name": INPUT[0], "sha256": INPUT[1], "rows": len(rows)}, "summary": s, "gains": gn,
              "conditions": conditions, "thresholds": {"median": MEDIAN_GAIN, "p90": P90_GAIN},
              "tests": tests, "printed_p": PRINTED_P,
              "table1": {"rows": t1, "matched": out["table1_matched"], "of": 24},
              "table2": {"rows": t2, "matched": out["table2_matched"], "of": 24}}
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
    except Refused as e:
        sys.exit(f"aca: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
