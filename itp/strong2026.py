#!/usr/bin/env python3
"""Epicatechin, halofuginone and mitoglitazone in the ITP's 2021 cohort, recomputed from the per-mouse data with the
paper's own test.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:cea402e411ca1625) is from Strong et al.,
"Extension of lifespan by epicatechin, halofuginone and mitoglitazone in male but not female genetically heterogeneous
mice", GeroScience 48(3), 4139-4156 (2026; online 19 September 2025): "In male mice, EPI increased median lifespan by
~ 5%, and HAL and MIT each increased median lifespan by ~ 9%."

Its registered test: refuted if, in the study's own per-mouse lifespans (the ITP's 2021 cohort of UM-HET3 mice at its
three sites, fed epicatechin, halofuginone or mitoglitazone from 7 months, or the control diet), the median age at
death of the three sites' males pooled, removed mice left out, rises by less than 2.5% with epicatechin or by less
than 4.5% with halofuginone or with mitoglitazone (half the reported 5%, 9% and 9%), or if any of the three rises has a
two-tailed log-rank p of 0.05 or more, stratified by site with removed mice censored, as the paper tests it.

The input is the workbook the paper names as its data's home (the Mouse Phenome Database, project ITP1):
ITP_C2021_Lifespan.xlsx (file id 772), the claim's data of record, checked against its SHA-256 and read with the
standard library by itp/rapa.py's reader (its XML parsed as data; nothing in it is run). The statistics are
itp/cana.py's and itp/strong2008.py's. Every rule below was fixed before any seed existed and before any age or status
in the workbook was read (only its header, its design columns and the form of its values were looked at); the seed is
not used, as nothing here is random.

1. The mice. Every row must be of population UM-HET3 and cohort C2021, at site TJL, UM or UT, of sex f or m, with a
   whole number of days as its age ("age"), and either dead (status "dead", dead 1) or removed (status "removed", dead
   0); its group must be one of the cohort's seven, and it must carry its group's design in the workbook's own columns
   ("dose" in ppm and "age_initiation" in months, spelt as the workbook spells them: DESIGN below; the controls'
   starting age is an empty cell). The workbook records epicatechin's dose as 60 ppm, where the paper's Table S2 gives
   its target as 600 ppm; "Epi" is the cohort's only epicatechin group, and the test takes it as the paper's EPI.
2. The medians. For each sex and group, the median age at death of the dead of the three sites pooled (removed mice
   left out, as Table 1's footnote says): the middle age, or the mean of the two middle ones. A rise is the treated
   median over the control median, less one, as the paper's Methods compute its percentage.
3. The paper's test. The two-tailed log-rank test stratified by site, removed mice censored at removal (Table 1's
   footnote: "Log-rank test includes all mice entered into the study"), for each sex and agent against the cohort's
   controls of the same sex (itp/cana.py's rule 4). Its direction, beside, is the agent's observed deaths less those
   the test expects of it (itp/strong2008.py's): below zero, the agent's mice lived longer.
4. The test's six conditions: the male epicatechin rise at least 0.025; the male halofuginone and mitoglitazone rises
   each at least 0.045; and each of the three with a log-rank p below 0.05. test_passed is 1 if all six hold.
5. Beside the test, none of it counted.
   - The paper's Table 1 and Tables S1a and S1b (its supplement), checked: for each sex and group, pooled and at each
     site, the count of the dead, the median as rule 2 takes it and the 90th percentile as the least age by which at
     least 90% of the dead had died (itp/cana.py's rule 2), each rounded to whole days, halves up; and each printed
     log-rank and Wang-Allison p, as printed (to its printed decimals). tables_matched counts them.
   - The Wang-Allison test as the Methods state it (itp/cana.py's rule 4): at each site the 90th percentile of the dead
     of both groups together by R's default rule, the sites' tables summed, Fisher's exact test, two-sided. The
     abstract's next sentence says epicatechin and halofuginone, but not mitoglitazone, increased 90% survival.
   - The females' rises and log-rank p for the three agents, and the males' for the other three (2BAct,
     dichloroacetate and forskolin, whose male median the paper says rose about 8% without a significant test).
   - Each site's male medians, log-rank p and direction for the three agents. (The Results say halofuginone's male
     gain reached significance only at UM; Table S1a prints p = 0.15 at UM and 0.04 at UT.)

Controls (controls_passed counts those that behave as stated): the file is the pinned one; it holds 2,388 mice, every
row as rule 1 requires; the stratified test with a single stratum gives the same p as itp/strong2008.py's log-rank test
of two groups; it gives the same p with the two groups swapped; each p is the same when the rows are read in reverse
order; and the control males against themselves give a log-rank p and a Wang-Allison p of 1.

What it cannot check: the data as the paper analysed them, from which the deposit may differ; the drugs in the food
(Table S2 measured about a third to a half of each target in the lifespan food: epicatechin 35%, halofuginone 36%,
mitoglitazone 46%); and the causes of death.

Writes results/outputs.json (the 19 values a receipt carries) and results/detail.json (every value computed).
Run with: python3 itp/strong2026.py
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

INPUT = ("ITP_C2021_Lifespan.xlsx", "c7b446f23129ff8e14410fb1e5bd626d40171ce4debccbe613a04ebf1b758169")
ROWS = 2388
POPULATION, COHORT = "UM-HET3", "C2021"
SITES, SEXES = ("TJL", "UM", "UT"), ("m", "f")
DESIGN = {"Control": ("0", None), "2BA": ("30", "7"), "DCA": ("30", "7"), "Epi": ("60", "7"), "For": ("5", "7"),
          "Hal": ("0.6", "7"), "M160": ("300", "7")}
GROUPS = tuple(DESIGN)
AGENTS = tuple(g for g in GROUPS if g != "Control")
TESTED = ("Epi", "Hal", "M160")
OTHERS = ("2BA", "DCA", "For")
NAMES = {"Epi": "epicatechin", "Hal": "halofuginone", "M160": "mitoglitazone"}
SHORT = {"Epi": "epi", "Hal": "hal", "M160": "mit"}
RISE = {"Epi": 0.025, "Hal": 0.045, "M160": 0.045}     # half the reported 5%, 9% and 9%
ALPHA = 0.05
LIMIT = 200

# The paper's Table 1 ("Pool") and Tables S1a and S1b (each site) as printed: (group, site, sex) -> (n, median, 90th
# percentile), n being the dead (removed mice left out), in days. The paper's names: Cont_21, 2BA, DCA, EPI, FSK (FOR
# in the supplement), HAL and MIT; the workbook's are DESIGN's.
TABLES = {
    ("Control", "Pool", "m"): (298, 794, 1069),
    ("2BA", "Pool", "m"): (153, 767, 1024),
    ("DCA", "Pool", "m"): (152, 814, 1105),
    ("Epi", "Pool", "m"): (141, 836, 1135),
    ("For", "Pool", "m"): (150, 860, 1117),
    ("Hal", "Pool", "m"): (154, 864, 1143),
    ("M160", "Pool", "m"): (149, 863, 1100),
    ("Control", "Pool", "f"): (286, 870, 1079),
    ("2BA", "Pool", "f"): (143, 857, 1070),
    ("DCA", "Pool", "f"): (142, 866, 1099),
    ("Epi", "Pool", "f"): (143, 851, 1081),
    ("For", "Pool", "f"): (143, 877, 1084),
    ("Hal", "Pool", "f"): (143, 872, 1076),
    ("M160", "Pool", "f"): (144, 850, 1037),
    ("Control", "TJL", "m"): (97, 715, 1048),
    ("2BA", "TJL", "m"): (51, 749, 959),
    ("DCA", "TJL", "m"): (48, 780, 1069),
    ("Epi", "TJL", "m"): (42, 800, 1109),
    ("For", "TJL", "m"): (50, 758, 1138),
    ("Hal", "TJL", "m"): (51, 779, 1094),
    ("M160", "TJL", "m"): (51, 860, 1133),
    ("Control", "UM", "m"): (99, 874, 1123),
    ("2BA", "UM", "m"): (51, 826, 1024),
    ("DCA", "UM", "m"): (53, 845, 1161),
    ("Epi", "UM", "m"): (48, 880, 1173),
    ("For", "UM", "m"): (49, 887, 1079),
    ("Hal", "UM", "m"): (54, 926, 1137),
    ("M160", "UM", "m"): (50, 912, 1120),
    ("Control", "UT", "m"): (102, 783, 1039),
    ("2BA", "UT", "m"): (51, 709, 1047),
    ("DCA", "UT", "m"): (51, 784, 1080),
    ("Epi", "UT", "m"): (51, 805, 1135),
    ("For", "UT", "m"): (51, 809, 1117),
    ("Hal", "UT", "m"): (49, 864, 1215),
    ("M160", "UT", "m"): (48, 863, 1080),
    ("Control", "TJL", "f"): (96, 892, 1079),
    ("2BA", "TJL", "f"): (47, 883, 1114),
    ("DCA", "TJL", "f"): (47, 900, 1040),
    ("Epi", "TJL", "f"): (48, 876, 1061),
    ("For", "TJL", "f"): (47, 869, 1079),
    ("Hal", "TJL", "f"): (48, 914, 1080),
    ("M160", "TJL", "f"): (48, 883, 1114),
    ("Control", "UM", "f"): (94, 882, 1103),
    ("2BA", "UM", "f"): (48, 838, 1040),
    ("DCA", "UM", "f"): (47, 816, 1105),
    ("Epi", "UM", "f"): (47, 894, 1127),
    ("For", "UM", "f"): (48, 877, 1062),
    ("Hal", "UM", "f"): (47, 867, 1074),
    ("M160", "UM", "f"): (48, 830, 1026),
    ("Control", "UT", "f"): (96, 848, 1050),
    ("2BA", "UT", "f"): (48, 838, 1064),
    ("DCA", "UT", "f"): (48, 856, 1114),
    ("Epi", "UT", "f"): (48, 835, 1071),
    ("For", "UT", "f"): (48, 895, 1100),
    ("Hal", "UT", "f"): (48, 832, 1079),
    ("M160", "UT", "f"): (48, 848, 1034),
}
# The same tables' log-rank and Wang-Allison p, as printed: (group, site, sex) -> (log-rank, Wang-Allison).
PRINTED_P = {
    ("2BA", "Pool", "m"): ("0.09", "0.42"),
    ("DCA", "Pool", "m"): ("0.28", "0.25"),
    ("Epi", "Pool", "m"): ("0.037", "0.01"),
    ("For", "Pool", "m"): ("0.17", "0.32"),
    ("Hal", "Pool", "m"): ("0.002", "0.01"),
    ("M160", "Pool", "m"): ("0.015", "0.19"),
    ("2BA", "Pool", "f"): ("0.41", "0.50"),
    ("DCA", "Pool", "f"): ("0.88", "0.86"),
    ("Epi", "Pool", "f"): ("0.6", "0.87"),
    ("For", "Pool", "f"): ("0.99", "0.87"),
    ("Hal", "Pool", "f"): ("0.75", "1.00"),
    ("M160", "Pool", "f"): ("0.07", "0.19"),
    ("2BA", "TJL", "m"): ("0.88", "0.58"),
    ("DCA", "TJL", "m"): ("0.38", "0.57"),
    ("Epi", "TJL", "m"): ("0.06", "0.36"),
    ("For", "TJL", "m"): ("0.09", "0.15"),
    ("Hal", "TJL", "m"): ("0.06", "0.39"),
    ("M160", "TJL", "m"): ("0.005", "0.39"),
    ("2BA", "UM", "m"): ("0.1", "0.77"),
    ("DCA", "UM", "m"): ("0.41", "0.42"),
    ("Epi", "UM", "m"): ("0.32", "1.00"),
    ("For", "UM", "m"): ("0.96", "0.39"),
    ("Hal", "UM", "m"): ("0.15", "0.58"),
    ("M160", "UM", "m"): ("0.65", "1.00"),
    ("2BA", "UT", "m"): ("0.24", "0.78"),
    ("DCA", "UT", "m"): ("0.87", "0.40"),
    ("Epi", "UT", "m"): ("0.43", "0.40"),
    ("For", "UT", "m"): ("0.54", "0.16"),
    ("Hal", "UT", "m"): ("0.04", "0.01"),
    ("M160", "UT", "m"): ("0.39", "0.56"),
    ("2BA", "TJL", "f"): ("0.33", "0.40"),
    ("DCA", "TJL", "f"): ("0.64", "0.77"),
    ("Epi", "TJL", "f"): ("0.42", "0.39"),
    ("For", "TJL", "f"): ("0.83", "1.00"),
    ("Hal", "TJL", "f"): ("0.97", "1.00"),
    ("M160", "TJL", "f"): ("0.9", "0.57"),
    ("2BA", "UM", "f"): ("0.01", "0.26"),
    ("DCA", "UM", "f"): ("0.85", "0.57"),
    ("Epi", "UM", "f"): ("0.51", "1.00"),
    ("For", "UM", "f"): ("0.3", "0.77"),
    ("Hal", "UM", "f"): ("0.45", "0.77"),
    ("M160", "UM", "f"): ("0.01", "0.09"),
    ("2BA", "UT", "f"): ("0.87", "0.40"),
    ("DCA", "UT", "f"): ("0.7", "1.00"),
    ("Epi", "UT", "f"): ("0.43", "1.00"),
    ("For", "UT", "f"): ("0.24", "0.26"),
    ("Hal", "UT", "f"): ("0.88", "0.26"),
    ("M160", "UT", "f"): ("0.41", "0.58"),
}
OUTPUTS = ("n_m", "median_m_control", "median_m_epi", "median_m_hal", "median_m_mit", "rise_epi", "rise_hal",
           "rise_mit", "logrank_p_epi", "logrank_p_hal", "logrank_p_mit", "wa_p_m", "females", "others_m",
           "tables_matched", "conditions_met", "test_passed", "controls_passed", "controls_total")


class Refused(Exception):
    pass


def mice_from_rows(rows):
    """{(group, site, sex): [(age, died)]} for the cohort's seven groups; every row checked against rule 1."""
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
        if g not in DESIGN:
            raise Refused(f"row {i}: group {g!r} is not one of the cohort's")
        design = (r.get("dose"), r.get("age_initiation"))
        if design != DESIGN[g]:
            raise Refused(f"row {i}: group {g} carries {design}, not {DESIGN[g]}")
        out[(g, r["site"], r["sex"])].append((int(float(age)), state[0] == "dead"))
    return out


def pooled(mice, group, sex, sites=SITES):
    return [m for s in sites for m in mice[(group, s, sex)]]


def dead_of(ms):
    return [t for t, d in ms if d]


def summary(ms):
    """Rule 2 and rule 5's numbers for a list of (age, died): count, dead, median and 90th percentile of the dead."""
    dead = dead_of(ms)
    return {"count": len(ms), "dead": len(dead), "median": statistics.median(dead), "p90": cana.p90_dead(dead)}


def strata(mice, group, sex, sites=SITES):
    """The (controls, agent) pairs of the given sites, for one sex: the log-rank and Wang-Allison tests' strata."""
    return [(mice[("Control", s, sex)], mice[(group, s, sex)]) for s in sites]


def conditions(rises, ps):
    """Rule 4, by name, from the male rises and log-rank p of the three agents."""
    out = {f"{NAMES[g]}: male median at least {RISE[g]:.1%} above the controls'": rises[g] >= RISE[g] for g in TESTED}
    out.update({f"{NAMES[g]}: log-rank p below 0.05": ps[g] < ALPHA for g in TESTED})
    return out


def tables_check(mice):
    """How many of the printed numbers of Table 1 and Tables S1a and S1b the data give, and every comparison."""
    numbers = {"Pool": [0, 0], "Site": [0, 0]}      # [matched, printed]
    pvalues = {"Pool": [0, 0], "Site": [0, 0]}
    rows = []
    for (g, site, sex), printed in TABLES.items():
        part = "Pool" if site == "Pool" else "Site"
        sites = SITES if site == "Pool" else (site,)
        got = summary(pooled(mice, g, sex, sites))
        ours = (got["dead"], cana.half_up(got["median"]), cana.half_up(got["p90"]))
        numbers[part][0] += sum(1 for p, o in zip(printed, ours) if p == o)
        numbers[part][1] += len(printed)
        row = {"group": g, "site": site, "sex": sex, "printed": list(printed), "data": list(ours)}
        if g != "Control":
            lr = cana.logrank_strat_p(strata(mice, g, sex, sites))
            wa = cana.wang_allison(strata(mice, g, sex, sites))[1]
            p_lr, p_wa = PRINTED_P[(g, site, sex)]
            hits = [s08.as_printed(lr, p_lr), s08.as_printed(wa, p_wa)]
            pvalues[part][0] += sum(hits)
            pvalues[part][1] += len(hits)
            row.update({"logrank_p": {"printed": p_lr, "data": lr, "as_printed": hits[0]},
                        "wang_allison_p": {"printed": p_wa, "data": wa, "as_printed": hits[1]}})
        rows.append(row)
    text = (f"Table 1: {numbers['Pool'][0]} of {numbers['Pool'][1]}, p {pvalues['Pool'][0]} of {pvalues['Pool'][1]}; "
            f"Tables S1a and S1b: {numbers['Site'][0]} of {numbers['Site'][1]}, p {pvalues['Site'][0]} of "
            f"{pvalues['Site'][1]}")
    return text, rows


def sig(p):
    return float(f"{p:.4g}")


def fmt(x):
    return str(int(x)) if float(x).is_integer() else f"{x:.1f}"


def analyse(mice):
    """Rules 2 to 5 on the mice of rule 1: the values a receipt carries (but the controls) and the detail."""
    s = {(g, x): summary(pooled(mice, g, x)) for g in GROUPS for x in SEXES}
    rises = {(g, x): s[(g, x)]["median"] / s[("Control", x)]["median"] - 1 for g in AGENTS for x in SEXES}
    ps = {(g, x): cana.logrank_strat_p(strata(mice, g, x)) for g in AGENTS for x in SEXES}
    oes = {(g, x): s08.observed_minus_expected(strata(mice, g, x)) for g in AGENTS for x in SEXES}
    wa = {(g, x): cana.wang_allison(strata(mice, g, x)) for g in AGENTS for x in SEXES}
    cond = conditions({g: rises[(g, "m")] for g in TESTED}, {g: ps[(g, "m")] for g in TESTED})
    matched, table_rows = tables_check(mice)
    site = {}
    for g in ("Control",) + TESTED:
        for st in SITES:
            entry = dict(summary(mice[(g, st, "m")]))
            if g != "Control":
                one = strata(mice, g, "m", (st,))
                entry.update({"logrank_p": cana.logrank_strat_p(one),
                              "observed_minus_expected": s08.observed_minus_expected(one)})
            site[f"{g} {st}"] = entry
    values = {
        "n_m": "; ".join(f"{g} {s[(g, 'm')]['count']} ({s[(g, 'm')]['dead']} dead)" for g in ("Control",) + TESTED),
        "median_m_control": float(s[("Control", "m")]["median"]),
        "tables_matched": matched,
        "wa_p_m": "; ".join(f"{g} {sig(wa[(g, 'm')][1])}" for g in TESTED),
        "females": ("rises " + ", ".join(f"{g} {rises[(g, 'f')]:+.4f}" for g in TESTED) + "; log-rank p "
                    + ", ".join(f"{g} {sig(ps[(g, 'f')])}" for g in TESTED)),
        "others_m": "; ".join(f"{g} rise {rises[(g, 'm')]:+.4f} p {sig(ps[(g, 'm')])}" for g in OTHERS),
        "conditions_met": sum(cond.values()),
        "test_passed": int(all(cond.values())),
    }
    for g in TESTED:
        values[f"median_m_{SHORT[g]}"] = float(s[(g, "m")]["median"])
        values[f"rise_{SHORT[g]}"] = round(rises[(g, "m")], 6)
        values[f"logrank_p_{SHORT[g]}"] = sig(ps[(g, "m")])
    detail = {
        "summaries": {f"{g} {x}": s[(g, x)] for g, x in s},
        "rises": {f"{g} {x}": v for (g, x), v in rises.items()},
        "logrank": {f"{g} {x}": {"p": ps[(g, x)], "observed_minus_expected": oes[(g, x)]} for g, x in ps},
        "wang_allison": {f"{g} {x}": {"table": wa[(g, x)][0], "p": wa[(g, x)][1]} for g, x in wa},
        "sites_m": site,
        "sites_m_text": "; ".join(f"{st} " + "/".join(fmt(site[f'{g} {st}']['median']) for g in ("Control",) + TESTED)
                                  for st in SITES) + " (Control/Epi/Hal/M160 medians)",
        "conditions": cond,
        "tables": {"matched": matched, "rows": table_rows},
    }
    return values, detail, ps


def controls_of(rows, mice, ps):
    """The controls, by name: True where each behaves as stated."""
    ctl = {"the file is the pinned one": True,
           "it holds 2,388 mice, every row as rule 1 requires": len(rows) == ROWS}
    one = [(pooled(mice, "Control", "f"), pooled(mice, "Hal", "f"))]
    ctl["one stratum gives the same p as strong2008.py's two-group test"] = abs(
        cana.logrank_strat_p(one) - s08.logrank_k_p([one[0][0], one[0][1]])) <= 1e-12
    swapped = [(b, a) for a, b in strata(mice, "Epi", "m")]
    ctl["the test gives the same p with the groups swapped"] = abs(
        cana.logrank_strat_p(swapped) - ps[("Epi", "m")]) <= 1e-12
    rev = mice_from_rows(list(reversed(rows)))
    ctl["each p is the same with the rows read in reverse"] = all(
        abs(cana.logrank_strat_p(strata(rev, g, x)) - ps[(g, x)]) <= 1e-12 for g in AGENTS for x in SEXES)
    same = [(mice[("Control", st, "m")], mice[("Control", st, "m")]) for st in SITES]
    ctl["the control males against themselves give a log-rank p and a Wang-Allison p of 1"] = (
        abs(cana.logrank_strat_p(same) - 1) <= 1e-12 and cana.wang_allison(same)[1] == 1)
    return ctl


def run(seed, inputs="inputs", results="results"):
    rows = rapa.read_rows(os.path.join(inputs, INPUT[0]), INPUT[1])
    mice = mice_from_rows(rows)
    values, detail, ps = analyse(mice)
    ctl = controls_of(rows, mice, ps)
    values.update({"controls_passed": sum(bool(v) for v in ctl.values()), "controls_total": len(ctl)})
    out = {k: values[k] for k in OUTPUTS}
    for k, v in out.items():
        if isinstance(v, str) and len(v) > LIMIT:
            raise AssertionError(f"{k}: longer than {LIMIT} characters: {v}")
    detail = {"input": {"name": INPUT[0], "sha256": INPUT[1], "rows": len(rows)}, "controls": ctl, **detail}
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
        sys.exit(f"strong2026: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
