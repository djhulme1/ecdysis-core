#!/usr/bin/env python3
"""Acarbose from 16 months in the ITP's 2012 cohort, recomputed from the per-mouse data with the paper's own tests.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:c0d2736e7a9c02b3) is from Strong et al.,
"Longer lifespan in male mice treated with a weakly estrogenic agonist, an antioxidant, an alpha-glucosidase inhibitor
or a Nrf2-inducer", Aging Cell 15(5) (2016): "The alpha-glucosidase inhibitor, acarbose, at a concentration previously
tested (1000 ppm), significantly increased median longevity in males and 90th percentile lifespan in both sexes, even
when treatment was started at 16 months."

Its registered test: refuted if, in the cohort's per-mouse lifespans (the ITP's 2012 cohort of UM-HET3 mice fed
acarbose at 1000 ppm from 16 months, or the control diet, at its three sites; removed mice censored), the male median
does not rise with a site-stratified log-rank P below 0.05, or in either sex the age at 90th percentile survival does
not rise with a Wang-Allison P below 0.05, that test as the paper's Methods state it: Fisher's exact test on the sum of
the sites' 2x2 tables of mice alive past, and dead by, each site's joint 90th percentile age.

The input is the workbook the ITP deposited for the cohort, ITP_C2012_Lifespan.xlsx (Mouse Phenome Database, project
ITP1, file id 768), the claim's data of record; it is checked against its SHA-256 and read by itp/rapa.py's reader
(its XML parsed as data; nothing in it is run). Every rule below was fixed before any seed existed; the seed is not
used, as nothing here is random.

What was read before registering (programme doc, line 8): by the method the Methods state, the female Wang-Allison P
is 0.050 to 0.058 over the readings of "the joint 90th percentile", where Table 2 prints 0.010; one threshold pooled
across sites gives 0.007 to 0.015. The test was registered as the paper states it, so this check audits that clause.

1. The mice. Every row must be of population UM-HET3 and cohort C2012, at site TJL, UM or UT, of sex f or m, with a
   whole number of days as its age, and either dead (status "dead", dead 1) or removed (status "removed", dead 0); its
   group must be one of the cohort's four, carrying that group's design in the workbook's own dose and start columns
   (DESIGN below, as the workbook spells them; HBX and I767d belong to other papers and are only checked and counted).
2. Medians and 90th percentiles of the dead, per site, sex and group, as itp/cana.py's rule 2 computes them (removed
   mice left out). Pooled two ways, both reported: the mean of the three site values (the rule of the paper's Table 1
   for the 2011 cohort) and the dead of the three sites together. A rise is the acarbose value above the control
   value, and the test asks for it under both rules.
3. The paper's tests. The log-rank test stratified by site, removed mice censored (itp/cana.py's rule 4). The
   Wang-Allison test as the Methods state it, by itp/cana.py's rule 4: at each site the joint 90th percentile is the
   90th percentile of the dead of both groups together by R's default rule (type 7); a mouse counts as alive past it
   if it lived beyond it, dead or removed later, and as dead by it if it died at or before it (a mouse removed at or
   before it is left out); the three sites' tables are summed; Fisher's exact test, two-sided, in exact integers.
4. Beside the test, the other readings of that test, all on the same summed site tables unless said: the joint 90th
   percentile as the least age by which 90% of the joint dead had died, and as the Kaplan-Meier age at 10% survival
   (removed mice censored), each counted strictly past or at-or-past; and, not what the Methods state, one threshold
   pooled across the three sites (R's type 7 on all the joint dead), one table.
5. Table 2, checked: its twelve C2012 numbers (each sex, control and acarbose: the number of deaths, the median and the
   90th percentile, in days), each compared with the data's value rounded to whole days, halves up, under each pooling
   rule; table2_matched_pooled and table2_matched_sitemean count those that agree.

test_passed is 1 if the male median rises under both pooling rules with a log-rank P below 0.05, and in each sex the
90th percentile rises under both rules with a Wang-Allison P (rule 3) below 0.05; else 0.

What it cannot check:
- the cohort beyond the workbook: ages are as the ITP recorded them; the workbook holds one more death in each of the
  four Table 2 groups than Table 2 counts;
- how Table 2's P values were computed, beyond what the Methods say: rule 4 reports the readings that come near them.

Writes results/outputs.json (17 values) and results/detail.json.
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

INPUT = ("ITP_C2012_Lifespan.xlsx", "87a805da0eb9da9d9bea6ecc3e83a689d422e145abeecbfda5d37f99326a3ef4")
POPULATION, COHORT, SITES, SEXES = "UM-HET3", "C2012", ("TJL", "UM", "UT"), ("m", "f")
# Each group's design as the workbook spells it: (dose, start in months).
DESIGN = {"Control": ("0", None), "ACA": ("1000", "16"), "HBX": ("1", "15"), "I767d": ("180", "10")}
GROUPS = tuple(DESIGN)
ALPHA = 0.05

# Table 2's C2012 rows as printed: (group, sex) -> (deaths, median, 90th percentile), days.
TABLE2 = {
    ("Control", "m"): (283, 823, 1055), ("ACA", "m"): (147, 875, 1183),
    ("Control", "f"): (278, 881, 1100), ("ACA", "f"): (135, 902, 1166),
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
            raise cana.Refused(f"row {i}: group {g!r} is not one of the cohort's four")
        dose, start = DESIGN[g]
        if r.get("dose") != dose or (r.get("age_initiation") or None) != start:
            raise cana.Refused(f"row {i}: group {g} with dose {r.get('dose')!r} and start {r.get('age_initiation')!r}, "
                               f"not {dose!r} and {start!r}")
        out[(g, r["site"], r["sex"])].append((int(float(age)), state[0] == "dead"))
    return out


def summarise(mice, sex, groups=("Control", "ACA")):
    """Per group: each site's count, deaths, median and 90th percentile of the dead, and both pooled values (rule 2)."""
    out = {}
    for g in groups:
        per = {}
        for s in SITES:
            dead = [t for t, d in mice[(g, s, sex)] if d]
            if not dead:
                raise cana.Refused(f"{g}, {sex}, at {s}: no deaths")
            per[s] = {"count": len(mice[(g, s, sex)]), "dead": len(dead), "median": cana.median_dead(dead),
                      "p90": cana.p90_dead(dead)}
        everyone = [t for s in SITES for t, d in mice[(g, s, sex)] if d]
        per["SiteMean"] = {"dead": sum(per[s]["dead"] for s in SITES), "median": sum(per[s]["median"] for s in SITES) / 3,
                           "p90": sum(per[s]["p90"] for s in SITES) / 3}
        per["Pooled"] = {"dead": len(everyone), "median": cana.median_dead(everyone), "p90": cana.p90_dead(everyone)}
        out[g] = per
    return out


def rises(summary, key):
    """{rule: acarbose value over control value, less one} for a key ("median" or "p90"), under both pooling rules."""
    return {rule: summary["ACA"][rule][key] / summary["Control"][rule][key] - 1 for rule in ("SiteMean", "Pooled")}


def km_q90(mice):
    """The Kaplan-Meier age at which survival first falls to 10% or below (removed mice censored), in exact fractions."""
    s = Fraction(1)
    for t in sorted({t for t, d in mice if d}):
        at_risk = sum(1 for x, _ in mice if x >= t)
        deaths = sum(1 for x, d in mice if x == t and d)
        s *= 1 - Fraction(deaths, at_risk)
        if s <= Fraction(1, 10):
            return t
    return max(t for t, _ in mice)


def wa_table(strata, cut_of, strict=True):
    """Summed per-site table (rows: control, treated; columns: alive past, dead by) for a cut-off rule."""
    table = [[0, 0], [0, 0]]
    for ctl, trt in strata:
        cut = cut_of(ctl + trt)
        for row, mice in ((0, ctl), (1, trt)):
            table[row][0] += sum(1 for t, _ in mice if (t > cut if strict else t >= cut))
            table[row][1] += sum(1 for t, d in mice if d and (t <= cut if strict else t < cut))
    return table


READINGS = {
    "p90 of the joint dead, past": (lambda m: cana.p90_dead([t for t, d in m if d]), True),
    "p90 of the joint dead, at or past": (lambda m: cana.p90_dead([t for t, d in m if d]), False),
    "Kaplan-Meier 10% survival, past": (km_q90, True),
    "Kaplan-Meier 10% survival, at or past": (km_q90, False),
}


def wang_allison_readings(mice, sex):
    """Rule 4: the other readings of the joint 90th percentile, on summed site tables, and one pooled threshold."""
    strata = [(mice[("Control", s, sex)], mice[("ACA", s, sex)]) for s in SITES]
    out = {}
    for name, (cut_of, strict) in READINGS.items():
        table = wa_table(strata, cut_of, strict)
        out[name] = {"table": table, "p": cana.fisher_two_sided(table)}
    ctl = [x for s in SITES for x in mice[("Control", s, sex)]]
    trt = [x for s in SITES for x in mice[("ACA", s, sex)]]
    table, p = cana.wang_allison([(ctl, trt)])
    out["one threshold pooled across sites (not the Methods)"] = {"table": table, "p": p}
    return out


def table2_check(summaries):
    """Rule 5: matches of Table 2's twelve numbers under each pooling rule."""
    matched = {"SiteMean": 0, "Pooled": 0}
    rows = []
    for (g, sex), printed in TABLE2.items():
        entry = {"group": g, "sex": sex, "printed": list(printed)}
        for rule in matched:
            got = summaries[sex][g][rule]
            ours = (got["dead"], cana.half_up(got["median"]), cana.half_up(got["p90"]))
            matched[rule] += sum(1 for p, o in zip(printed, ours) if p == o)
            entry[rule] = list(ours)
        rows.append(entry)
    return matched, rows


def verdict(median_m, p90, logrank_m, wa):
    """The registered test (rule 3 and the verdict): every clause, by name."""
    return {
        "male median rises (both rules)": all(v > 0 for v in median_m.values()),
        "male log-rank P below 0.05": logrank_m < ALPHA,
        "male 90th percentile rises (both rules)": all(v > 0 for v in p90["m"].values()),
        "male Wang-Allison P below 0.05": wa["m"] < ALPHA,
        "female 90th percentile rises (both rules)": all(v > 0 for v in p90["f"].values()),
        "female Wang-Allison P below 0.05": wa["f"] < ALPHA,
    }


def run(inputs="inputs", results="results"):
    rows = rapa.read_rows(os.path.join(inputs, INPUT[0]), INPUT[1])
    mice = mice_from_rows(rows)
    summ = {sex: summarise(mice, sex) for sex in SEXES}
    median_m = rises(summ["m"], "median")
    p90 = {sex: rises(summ[sex], "p90") for sex in SEXES}
    tests = {}
    for sex in SEXES:
        strata = [(mice[("Control", s, sex)], mice[("ACA", s, sex)]) for s in SITES]
        table, p = cana.wang_allison(strata)
        tests[sex] = {"logrank": cana.logrank_strat_p(strata), "wa_table": table, "wa": p,
                      "readings": wang_allison_readings(mice, sex)}
    clauses = verdict(median_m, p90, tests["m"]["logrank"], {sex: tests[sex]["wa"] for sex in SEXES})
    matched, t2rows = table2_check(summ)
    stated_f = [tests["f"]["wa"]] + [v["p"] for k, v in tests["f"]["readings"].items() if "pooled" not in k]
    sig = lambda x: float(f"{x:.4e}")  # noqa: E731
    out = {
        "median_gain_m_sitemean": round(median_m["SiteMean"], 6),
        "median_gain_m_pooled": round(median_m["Pooled"], 6),
        "p90_gain_m_sitemean": round(p90["m"]["SiteMean"], 6),
        "p90_gain_m_pooled": round(p90["m"]["Pooled"], 6),
        "p90_gain_f_sitemean": round(p90["f"]["SiteMean"], 6),
        "p90_gain_f_pooled": round(p90["f"]["Pooled"], 6),
        "logrank_p_m": sig(tests["m"]["logrank"]),
        "logrank_p_f": sig(tests["f"]["logrank"]),
        "wa_p_m": sig(tests["m"]["wa"]),
        "wa_p_f": sig(tests["f"]["wa"]),
        "wa_p_f_stated_low": sig(min(stated_f)),
        "wa_p_f_stated_high": sig(max(stated_f)),
        "wa_p_f_pooled_threshold": sig(tests["f"]["readings"]["one threshold pooled across sites (not the Methods)"]["p"]),
        "table2_matched_pooled": matched["Pooled"],
        "table2_matched_sitemean": matched["SiteMean"],
        "table2_total": 3 * len(TABLE2),
        "test_passed": int(all(clauses.values())),
    }
    counts = {g: sum(len(mice[(g, s, x)]) for s in SITES for x in SEXES) for g in GROUPS}
    detail = {"input": {"name": INPUT[0], "sha256": INPUT[1], "rows": len(rows), "per_group": counts},
              "summary": summ, "rises": {"median_m": median_m, "p90": p90}, "clauses": clauses,
              "tests": tests, "table2": {"matched": matched, "of": 3 * len(TABLE2), "rows": t2rows}}
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
        sys.exit(f"aca2012: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
