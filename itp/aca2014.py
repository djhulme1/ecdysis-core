#!/usr/bin/env python3
"""Acarbose's sex-dependent effect on lifespan in the ITP's 2009 cohort, recomputed from the per-mouse data.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:68f89b65e7b328e2) is from Harrison et al.,
"Acarbose, 17-alpha-estradiol, and nordihydroguaiaretic acid extend mouse lifespan preferentially in males", Aging Cell
13(2) (2014): "Acarbose increased male median lifespan by 22% (P < 0.0001), but increased female median lifespan by
only 5% (P = 0.01)."

Its registered test: refuted if, in the study's own per-mouse lifespans (the ITP's 2009 cohort of UM-HET3 mice fed
acarbose at 1,000 ppm from 4 months, or the control diet, at its three sites), with Kaplan-Meier medians of the pooled
mice, removed mice censored at removal, as Table 1 gives them, the male median's gain over the male controls is below
11% (half the 22% reported), or the female median's gain over the female controls is below 2.5% (half the 5% reported)
or not smaller than the male gain.

The input is the workbook the ITP deposited for the cohort, ITP_C2009_Lifespan.xlsx (Mouse Phenome Database, project
ITP1), checked against its SHA-256 and read by itp/rapa.py's reader (its XML parsed as data; nothing in it is run). It
is the same file itp/rapadose.py reads for Miller et al. (2014), the cohort's rapamycin arms. Every rule below was fixed
before any seed existed; the seed is not used, as nothing here is random.

1. The mice. Every row must be of cohort C2009, at site TJL, UM or UT, of sex f or m, with a whole number of days as
   its age, and either dead (status "dead", dead 1) or removed (status "removed", dead 0); anything else is refused.
   The groups kept are "Control", "ACA", "17aE2" and "MB", as assigned (the cohort's rapamycin arms are checked and
   not used); a kept row must also carry its group's design in the workbook's own columns (dose 0 and no start for
   the controls; acarbose 1,000 ppm from 4 months; 17-alpha-estradiol 4.8 ppm from 10 months; methylene blue 28 ppm
   from 4 months), or the run is refused.
2. Table 1's statistics, for each sex and group, over the mice of the three sites pooled and at each site: the
   Kaplan-Meier median and 90th percentile (the first age at which survival is at or below 0.5 or 0.1), removed mice
   censored at removal, as itp/rapa.py computes them; the counts are all the mice, dead or removed. A gain is the
   acarbose median (or 90th percentile) of the pooled mice over the same sex's control value, less one.
3. Beside the test, the paper's tests, as itp/cana.py computes them: the two-sided log-rank test, removed mice
   censored, stratified by site for the pooled mice and within each site for the sites; and the Wang-Allison test,
   survivors counted above the 90th percentile of the joint deaths (R's type 7), Fisher's exact test, the sites'
   tables summed for the pooled mice.
4. Table 1's 96 numbers (for each drug, sex and row, the pooled mice and the three sites: the control and treated
   medians and 90th percentiles, the controls repeated for each drug as the table prints them) are compared with the
   data's, and the 32 of acarbose on their own.

test_passed is 1 if the male gain is at least 11%, the female gain at least 2.5% and the female gain below the male
one, compared as exact fractions of days; else 0.

What it cannot check: the snapshot of the data the paper analysed (its Table 1 says all the mice had died, yet the
deposit, the cohort's final record, differs in some female numbers); the weights the abstract also discusses; NDGA,
tested in another cohort; and why acarbose acts more in males.

Writes results/outputs.json (16 values) and results/detail.json.
"""

import importlib.util
import json
import os
import re
import sys
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("itp_cana", os.path.join(HERE, "cana.py"))
cana = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cana)
rapa = cana.rapa

INPUT = ("ITP_C2009_Lifespan.xlsx", "3e542f236b915bc1b312c8698309193abf39497b5c57c5c81eb5d06708ec5d20")
COHORT, SITES, SEXES = "C2009", ("TJL", "UM", "UT"), ("m", "f")
DRUGS = ("ACA", "17aE2", "MB")
GROUPS = ("Control",) + DRUGS
OTHER = ("Rapa_lo", "Rapa_mid", "Rapa_hi")
ROWS = ("Pooled",) + SITES
# Each group's design as the workbook records it: (dose in ppm, start in months; None for the controls).
DESIGN = {"Control": ("0", None), "ACA": ("1000", "4"), "17aE2": ("4.8", "10"), "MB": ("28", "4")}
MALE_GAIN, FEMALE_GAIN = Fraction(11, 100), Fraction(25, 1000)

# Table 1 as printed: drug -> sex -> row -> (control median, treated median, control p90, treated p90), days.
TABLE1 = {
    "ACA": {"m": {"Pooled": (807, 984, 1094, 1215), "TJL": (807, 974, 1061, 1212), "UM": (925, 999, 1051, 1219),
                  "UT": (704, 981, 1013, 1204)},
            "f": {"Pooled": (896, 939, 1072, 1167), "TJL": (918, 911, 1084, 1148), "UM": (887, 949, 1089, 1152),
                  "UT": (864, 942, 1062, 1167)}},
    "17aE2": {"m": {"Pooled": (807, 900, 1094, 1148), "TJL": (807, 828, 1061, 1117), "UM": (925, 949, 1151, 1187),
                    "UT": (704, 900, 1013, 1110)},
              "f": {"Pooled": (896, 893, 1072, 1068), "TJL": (918, 867, 1084, 1107), "UM": (887, 910, 1089, 1006),
                    "UT": (864, 903, 1062, 1079)}},
    "MB": {"m": {"Pooled": (807, 790, 1094, 1037), "TJL": (807, 701, 1061, 1009), "UM": (925, 905, 1151, 1157),
                 "UT": (704, 699, 1013, 980)},
           "f": {"Pooled": (896, 902, 1072, 1138), "TJL": (918, 862, 1084, 1121), "UM": (887, 993, 1089, 1159),
                 "UT": (864, 880, 1062, 1075)}}}
# Table 1's acarbose rows as printed, for the detail only: sex -> row -> (difference %, log-rank P, Wang-Allison P).
PRINTED = {"m": {"Pooled": (22, "<0.0001", "<0.001"), "TJL": (21, "0.0003", "0.09"), "UM": (8, "0.054", "0.04"),
                 "UT": (39, "<0.0001", "<0.001")},
           "f": {"Pooled": (5, "0.0101", "0.001"), "TJL": (-1, "0.4", "0.01"), "UM": (7, "0.13", "0.14"),
                 "UT": (9, "0.04", "0.11")}}


class Refused(Exception):
    """An input that is not what the rules say it must be."""


def mice_from_rows(rows):
    """Rule 1: {(group, site, sex): [(age, died)]} for the four groups kept, every row checked."""
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


def stats(mice):
    """Rule 2 for one set of mice: {mice, dead, median, p90}."""
    if not any(d for _, d in mice):
        raise Refused("a set of mice with no deaths")
    median, p90 = rapa.km_quantile(mice, 0.5), rapa.km_quantile(mice, 0.9)
    if median is None or p90 is None:
        raise Refused("survival never reaches the quantile")
    return {"mice": len(mice), "dead": sum(1 for _, d in mice if d), "median": median, "p90": p90}


def summary(mice):
    """Rule 2: sex -> group -> row -> stats, the rows being the pooled mice and each site."""
    out = {}
    for sex in SEXES:
        out[sex] = {}
        for g in GROUPS:
            out[sex][g] = {"Pooled": stats([m for s in SITES for m in mice[(g, s, sex)]])}
            for s in SITES:
                out[sex][g][s] = stats(mice[(g, s, sex)])
    return out


def gains(s):
    """Fractions: sex -> (median gain, 90th percentile gain) of acarbose over the controls, pooled."""
    out = {}
    for sex in SEXES:
        c, t = s[sex]["Control"]["Pooled"], s[sex]["ACA"]["Pooled"]
        out[sex] = (Fraction(t["median"], c["median"]) - 1, Fraction(t["p90"], c["p90"]) - 1)
    return out


def verdict(gm, gf):
    """The registered test on the median gains, as fractions: 1 if it stands, else 0; and each condition."""
    conditions = {"male_at_least_11pct": gm >= MALE_GAIN, "female_at_least_2.5pct": gf >= FEMALE_GAIN,
                  "female_below_male": gf < gm}
    return int(all(conditions.values())), conditions


def tests(mice):
    """Rule 3: sex -> row -> {logrank, wa, wa_table} for acarbose against the controls."""
    out = {}
    for sex in SEXES:
        out[sex] = {}
        strata = [(mice[("Control", site, sex)], mice[("ACA", site, sex)]) for site in SITES]
        table, wa = cana.wang_allison(strata)
        out[sex]["Pooled"] = {"logrank": cana.logrank_strat_p(strata), "wa": wa, "wa_table": table}
        for site, stratum in zip(SITES, strata):
            table, wa = cana.wang_allison([stratum])
            out[sex][site] = {"logrank": cana.logrank_strat_p([stratum]), "wa": wa, "wa_table": table}
    return out


def table1_check(s):
    rows = []
    for drug in DRUGS:
        for sex in SEXES:
            for row in ROWS:
                c, t = s[sex]["Control"][row], s[sex][drug][row]
                ours = (c["median"], t["median"], c["p90"], t["p90"])
                rows.append({"drug": drug, "sex": sex, "row": row, "printed": list(TABLE1[drug][sex][row]),
                             "data": list(ours), "matched": sum(1 for a, b in zip(TABLE1[drug][sex][row], ours) if a == b)})
    return rows


def run(inputs="inputs", results="results"):
    rows = rapa.read_rows(os.path.join(inputs, INPUT[0]), INPUT[1])
    mice = mice_from_rows(rows)
    s = summary(mice)
    g = gains(s)
    passed, conditions = verdict(g["m"][0], g["f"][0])
    t = tests(mice)
    t1 = table1_check(s)

    def pair(sex, key, row="Pooled"):
        return f"{s[sex]['Control'][row][key]}/{s[sex]['ACA'][row][key]}"
    out = {
        "median_m": pair("m", "median"),
        "median_f": pair("f", "median"),
        "p90_m": pair("m", "p90"),
        "p90_f": pair("f", "p90"),
        "counts": "; ".join(f"{sex} {s[sex]['Control']['Pooled']['mice']}/{s[sex]['ACA']['Pooled']['mice']}"
                            for sex in SEXES),
        "sites_median_m": "; ".join(pair("m", "median", site) for site in SITES),
        "sites_median_f": "; ".join(pair("f", "median", site) for site in SITES),
        "inc_median_m": round(float(g["m"][0]), 6),
        "inc_median_f": round(float(g["f"][0]), 6),
        "inc_p90_m": round(float(g["m"][1]), 6),
        "inc_p90_f": round(float(g["f"][1]), 6),
        "logrank_p": "; ".join(f"{sex} {t[sex]['Pooled']['logrank']:.2e}" for sex in SEXES),
        "wa_p": "; ".join(f"{sex} {t[sex]['Pooled']['wa']:.2e}" for sex in SEXES),
        "table1_aca": sum(r["matched"] for r in t1 if r["drug"] == "ACA"),
        "table1_all": sum(r["matched"] for r in t1),
        "test_passed": passed,
    }
    for k, v in out.items():
        if isinstance(v, str) and len(v) > 200:
            raise AssertionError(f"{k}: longer than 200 characters")
    detail = {"input": {"name": INPUT[0], "sha256": INPUT[1], "rows": len(rows)}, "summary": s,
              "gains": {sex: [str(x) for x in g[sex]] for sex in SEXES}, "conditions": conditions, "tests": t,
              "printed_aca": PRINTED,
              "table1": {"rows": t1, "aca_matched": out["table1_aca"], "aca_of": 32, "matched": out["table1_all"],
                         "of": 96}}
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
        sys.exit(f"aca2014: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
