#!/usr/bin/env python3
"""Rapamycin's dose and sex effects on lifespan in the ITP's 2009 cohort, recomputed from the per-mouse data.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:db37ab3849d8e4db) is from Miller et al.,
"Rapamycin-mediated lifespan increase in mice is dose and sex dependent and metabolically distinct from dietary
restriction", Aging Cell 13(3) (2014): "Rapamycin increased lifespan more in females than in males at each dose
evaluated, perhaps reflecting sexual dimorphism in blood levels of this drug."

Its registered test: refuted if, at any one of the three doses, the female median's gain over the female controls is
not larger than the male median's gain over the male controls, in the study's own per-mouse lifespans (the ITP's 2009
cohort of UM-HET3 mice fed rapamycin at 4.7, 14 or 42 ppm from 9 months, or the control diet, at its three sites),
with Kaplan-Meier medians of the pooled mice, removed mice censored at removal, as Table 1 gives them.

The input is the workbook the ITP deposited for the cohort, ITP_C2009_Lifespan.xlsx (Mouse Phenome Database, project
ITP1), checked against its SHA-256 and read by itp/rapa.py's reader (its XML parsed as data; nothing in it is run).
Every rule below was fixed before any seed existed; the seed is not used, as nothing here is random.

1. The mice. Every row must be of cohort C2009, at site TJL, UM or UT, of sex f or m, with a whole number of days as
   its age, and either dead (status "dead", dead 1) or removed (status "removed", dead 0); anything else is refused.
   The groups are "Control", "Rapa_lo", "Rapa_mid" and "Rapa_hi", as assigned (the cohort's other arms, 17aE2, ACA
   and MB, are checked and not used); a kept row must also carry its group's design in the workbook's own columns
   (dose 0 and no start for the controls; 4.7, 14 or 42 ppm from 9 months), or the run is refused.
2. Table 1's statistics, for each sex and group, over the mice of the three sites pooled: the Kaplan-Meier median and
   90th percentile (the first age at which survival is at or below 0.5 or 0.1), removed mice censored at removal, as
   itp/rapa.py computes them; the counts are all the mice, dead or removed. This is the rule that reproduces Table 1's
   twelve male numbers; the paper analysed the cohort when under 1% of its mice were alive, and the deposited data are
   its final record. A gain is the rapamycin median over the same sex's control median, less one.
3. Beside the test, the paper's own tests, as itp/cana.py computes them: the two-sided log-rank test stratified by
   site, removed mice censored; and the Wang-Allison test, survivors counted at each site's 90th percentile of the
   joint deaths (R's type 7) and the sites' tables summed for one Fisher exact test (the paper takes each site's age
   of 10% survival in the joint distribution).
4. Table 1's 24 numbers (each sex: the count, median and 90th percentile of the controls and the three doses) are
   compared with the data's. The research for the claim found all twelve male numbers and six of the female ones
   (the counts and two 90th percentiles; the female medians are 1 to 6 days lower in the data, and the female
   controls' 90th percentile, printed 1159, is 1072, as Harrison et al. 2014 print it for the same mice).

test_passed is 1 if at each of the three doses the female median gain is larger than the male median gain; else 0.

What it cannot check: the snapshot of the data the paper analysed, which was not deposited; why the female controls'
90th percentile prints 1159; the drug's blood levels, which the sentence offers as a reason and which are not in
these data.

Writes results/outputs.json (15 values) and results/detail.json.
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

INPUT = ("ITP_C2009_Lifespan.xlsx", "3e542f236b915bc1b312c8698309193abf39497b5c57c5c81eb5d06708ec5d20")
COHORT, SITES, SEXES = "C2009", ("TJL", "UM", "UT"), ("m", "f")
GROUPS = ("Control", "Rapa_lo", "Rapa_mid", "Rapa_hi")
DOSES = ("Rapa_lo", "Rapa_mid", "Rapa_hi")
OTHER = ("17aE2", "ACA", "MB")
# Each group's design as the workbook records it: (dose in ppm, start in months; None for the controls).
DESIGN = {"Control": ("0", None), "Rapa_lo": ("4.7", "9"), "Rapa_mid": ("14", "9"), "Rapa_hi": ("42", "9")}

# Table 1 as printed: sex -> group -> (count, median, 90th percentile), days.
TABLE1 = {"m": {"Control": (300, 807, 1094), "Rapa_lo": (156, 834, 1162), "Rapa_mid": (156, 909, 1180),
                "Rapa_hi": (156, 992, 1185)},
          "f": {"Control": (280, 896, 1159), "Rapa_lo": (136, 1043, 1218), "Rapa_mid": (136, 1086, 1285),
                "Rapa_hi": (136, 1132, 1282)}}
# Table 1's p-values and median increases as printed, for the detail only: sex -> group -> (increase %, log-rank, WA).
PRINTED = {"m": {"Rapa_lo": (3, "0.19", "0.23"), "Rapa_mid": (13, "0.0015", "0.003"), "Rapa_hi": (23, "<0.0001", "0.004")},
           "f": {"Rapa_lo": (16, "<0.0001", "<0.0001"), "Rapa_mid": (21, "<0.0001", "<0.0001"),
                 "Rapa_hi": (26, "<0.0001", "<0.0001")}}


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


def summary(mice):
    """Rule 2: sex -> group -> {mice, dead, median, p90}, the Kaplan-Meier values of the pooled mice."""
    out = {}
    for sex in SEXES:
        out[sex] = {}
        for g in GROUPS:
            every = [m for s in SITES for m in mice[(g, s, sex)]]
            if not any(d for _, d in every):
                raise Refused(f"{g}, {sex}: no deaths")
            median, p90 = rapa.km_quantile(every, 0.5), rapa.km_quantile(every, 0.9)
            if median is None or p90 is None:
                raise Refused(f"{g}, {sex}: survival never reaches the quantile")
            out[sex][g] = {"mice": len(every), "dead": sum(1 for _, d in every if d), "median": median, "p90": p90}
    return out


def gains(s):
    return {f"{sex}_{g}": s[sex][g]["median"] / s[sex]["Control"]["median"] - 1 for sex in SEXES for g in DOSES}


def verdict(gn):
    """The registered test: 1 if the female gain is larger at every dose, else 0; and each comparison."""
    conditions = {g: gn[f"f_{g}"] > gn[f"m_{g}"] for g in DOSES}
    return int(all(conditions.values())), conditions


def table1_check(s):
    rows = []
    for sex in SEXES:
        for g in GROUPS:
            ours = (s[sex][g]["mice"], s[sex][g]["median"], s[sex][g]["p90"])
            rows.append({"sex": sex, "group": g, "printed": list(TABLE1[sex][g]), "data": list(ours),
                         "matched": sum(1 for a, b in zip(TABLE1[sex][g], ours) if a == b)})
    return rows


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
    t1 = table1_check(s)

    def row(key, sex):
        return "/".join(str(s[sex][g][key]) for g in GROUPS)

    def plist(kind):
        return "; ".join(f"{sex} " + "/".join(f"{tests[f'{sex}_{g}'][kind]:.2e}" for g in DOSES) for sex in SEXES)
    out = {
        "median_m": row("median", "m"),
        "median_f": row("median", "f"),
        "p90_m": row("p90", "m"),
        "p90_f": row("p90", "f"),
        "counts": "; ".join(f"{sex} " + "/".join(str(s[sex][g]["mice"]) for g in GROUPS) for sex in SEXES),
        "inc_median_m_lo": round(gn["m_Rapa_lo"], 6),
        "inc_median_m_mid": round(gn["m_Rapa_mid"], 6),
        "inc_median_m_hi": round(gn["m_Rapa_hi"], 6),
        "inc_median_f_lo": round(gn["f_Rapa_lo"], 6),
        "inc_median_f_mid": round(gn["f_Rapa_mid"], 6),
        "inc_median_f_hi": round(gn["f_Rapa_hi"], 6),
        "logrank_p": plist("logrank"),
        "wa_p": plist("wa"),
        "table1_matched": sum(r["matched"] for r in t1),
        "test_passed": passed,
    }
    for k, v in out.items():
        if isinstance(v, str) and len(v) > 200:
            raise AssertionError(f"{k}: longer than 200 characters")
    detail = {"input": {"name": INPUT[0], "sha256": INPUT[1], "rows": len(rows)}, "summary": s, "gains": gn,
              "conditions": conditions, "tests": tests, "printed": PRINTED,
              "table1": {"rows": t1, "matched": out["table1_matched"], "of": 24}}
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
        sys.exit(f"rapadose: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
