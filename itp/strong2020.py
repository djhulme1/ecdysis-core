#!/usr/bin/env python3
"""Rapamycin from 20 months, continuous, in alternating months or for 3 months, in the ITP's 2015 cohort, recomputed
from the per-mouse data with the paper's own criteria.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:b9d5b47e07b6161a) is from Strong et al.,
"Rapamycin-mediated mouse lifespan extension: Late-life dosage regimes with sex-specific effects", Aging Cell 19(11),
e13269 (2020): "Initiation of Rapa at 42 ppm increased survival significantly in both male and female mice. Exposure to
Rapa for a 3-month period led to significant longevity benefit in males only. Protocols in which each month of Rapa
treatment was followed by a month without Rapa exposure were also effective in both sexes, though this approach was less
effective than continuous exposure in female mice."

Its registered test: refuted if, in the study's deposited per-mouse lifespans (the ITP's 2015 cohort at its three sites:
controls, and rapamycin at 42 ppm from 20 months continuously, in alternating months, or for 3 months), by the two-sided
log-rank test stratified by site (removed mice censored), continuous or alternating rapamycin fails to give p < 0.05
with a higher median than the controls' in either sex; or the 3-month course does so in females or fails to in males; or
alternating months is not below continuous in females (a lower median, p < 0.05 between them).

The input is the cohort's workbook at the Mouse Phenome Database (project ITP2015, whose participants are the paper's
authors): ITP_C2015_Lifespan.xlsx (file id 751), the claim's data of record, checked against its SHA-256 and read with
the standard library by itp/rapa.py's reader (its XML parsed as data; nothing in it is run). MPD keeps a second file
beside it, "ITP_C2015_Lifespan w error.xlsx" (file id 752), which repeats two 17-DMAG males and is not used. The
statistics are itp/cana.py's. Every rule below was fixed before any seed existed; the seed is not used, as nothing here
is random.

1. The mice. Every row must be of population UM-HET3 and cohort C2015, at site TJL, UM or UT, of sex f or m, with a
   whole number of days as its age, and either dead (status "dead", dead 1) or removed (status "removed", dead 0); its
   group must be one of the cohort's eight, and each group must carry one design (dose in ppm, starting age) in the
   workbook's own columns, the four this test uses the designs in DESIGN below. The other four (17-DMAG, minocycline,
   beta-GPA, MitoQ) are counted and tested only beside.
2. The medians. For each sex and group, the median age at death of the dead of the three sites pooled (removed mice
   left out): the middle age, or the mean of the two middle ones. A rise is a group's median over the controls', less
   one.
3. The paper's criterion (its Statistical methods): the two-sided log-rank test for each sex, stratified by site,
   removed mice censored at removal (itp/cana.py's rule 4), at 5%. Two protocols are compared by the same test.
4. The test's seven conditions: continuous and alternating rapamycin, each sex, p < 0.05 against the controls and a
   higher median; the 3-month course, males, p < 0.05 and a higher median; the 3-month course, females, not p < 0.05
   with a higher median (a benefit there refutes; no difference, or a harm, does not); in females, alternating months
   against continuous, a lower median and p < 0.05. test_passed is 1 if all hold.
5. Beside the test.
   - Tables 1 and 2, checked: for each sex and group (pooled) the count of mice, the median and the 90th percentile of
     the dead (the least age by which at least 90% had died), whole days, halves up; and the log-rank and Wang-Allison p
     (each site's joint 90th percentile of the dead by R's default rule, the sites' tables summed, Fisher's exact test),
     the data's p written to the printed number's decimals ("<0.0001" matched by any p below it).
   - The Wang-Allison test for the three protocols; the protocols compared in pairs, each sex (the paper: males
     0.28 < p < 0.61, females 0.0001 to 0.04).
   - The four other agents' log-rank p, each sex: the paper says none changed survival.
   - The paper's own caveat (its Results): the groups differed before rapamycin began at 604 days, perhaps from two
     suppliers' chow. So the log-rank test again on the mice alive at 604 days, each protocol against the controls.

What it cannot check: the cohort beyond the workbook (ages are as the ITP recorded them), the chow, and the paper's
weights.

Writes results/outputs.json (the values a receipt carries) and results/detail.json (every value computed).
Run with: python3 itp/strong2020.py
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

INPUT = ("ITP_C2015_Lifespan.xlsx", "bc0e6f119e950cf35ac67e60cad1df4207cabf7028328840bbe5a54b13e4080a")
POPULATION, COHORT = "UM-HET3", "C2015"
SITES, SEXES = ("TJL", "UM", "UT"), ("f", "m")
CONT, ALT, SHORT = "rapa_hi_continuous", "rapa_hi_cycle", "rapa_hi_start_stop"
OTHERS = ("DMAG", "Min", "bGPA", "MitoQ")
GROUPS = ("Control", CONT, ALT, SHORT) + OTHERS
PROTOCOLS = (CONT, ALT, SHORT)
NAMES = {CONT: "continuous", ALT: "alternating", SHORT: "3 months", "Control": "Control", "DMAG": "17-DMAG",
         "Min": "minocycline", "bGPA": "beta-GPA", "MitoQ": "MitoQ"}
DESIGN = {"Control": ("0", None), CONT: ("42", "20"), ALT: ("42", "20 but every other"), SHORT: ("42", "20 thru 23")}
START = 604                                     # 20 months, in days (the paper's Results)
ALPHA = 0.05
LIMIT = 200

# Tables 1 and 2 as printed, pooled: (group, sex) -> (count, median, P90, log-rank p, Wang-Allison p), in days.
TABLE = {
    ("Control", "m"): (300, 772, 1049, None, None), ("Control", "f"): (280, 905, 1095, None, None),
    (CONT, "m"): (156, 856, 1148, "0.0007", "0.04"), (CONT, "f"): (136, 1040, 1231, "<0.0001", "<0.0001"),
    (ALT, "m"): (159, 841, 1144, "0.002", "0.001"), (ALT, "f"): (136, 977, 1203, "<0.0001", "0.0004"),
    (SHORT, "m"): (153, 854, 1100, "0.024", "0.08"), (SHORT, "f"): (136, 940, 1136, "0.15", "0.12"),
    ("DMAG", "m"): (156, 844, 1090, "0.12", "0.13"), ("DMAG", "f"): (136, 866, 1074, "0.12", "0.29"),
    ("Min", "m"): (156, 807, 1026, "0.99", "0.50"), ("Min", "f"): (136, 878, 1094, "0.38", "0.99"),
    ("bGPA", "m"): (156, 764, 1054, "0.73", "0.86"), ("bGPA", "f"): (136, 893, 1114, "0.91", "0.39"),
    ("MitoQ", "m"): (156, 784, 1066, "0.91", "0.86"), ("MitoQ", "f"): (136, 890, 1105, "0.67", "0.39"),
}
OUTPUTS = ("n", "medians_m", "medians_f", "logrank_m", "logrank_f", "alt_vs_cont_f", "pairwise_m", "pairwise_f",
           "wang_allison", "after_604", "other_agents", "tables_matched", "conditions_met", "conditions_total",
           "test_passed")


class Refused(Exception):
    pass


def mice_from_rows(rows):
    """{(group, site, sex): [(age, died)]} for all eight groups; every row checked against rule 1."""
    out = {(g, s, x): [] for g in GROUPS for s in SITES for x in SEXES}
    designs = {g: set() for g in GROUPS}
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
        design = (r.get("dose"), r.get("age_initiation"))
        if g in DESIGN and design != DESIGN[g]:
            raise Refused(f"row {i}: group {g} carries {design}, not {DESIGN[g]}")
        designs[g].add(design)
        out[(g, r["site"], r["sex"])].append((int(float(age)), state[0] == "dead"))
    for g, ds in designs.items():
        if len(ds) != 1:
            raise Refused(f"group {g} carries {len(ds)} designs, not one: {sorted(ds, key=str)}")
    return out, {g: sorted(ds, key=str)[0] for g, ds in designs.items()}


def pooled(mice, group, sex):
    return [m for s in SITES for m in mice[(group, s, sex)]]


def summary(ms):
    dead = [t for t, d in ms if d]
    return {"count": len(ms), "dead": len(dead), "median": statistics.median(dead), "p90": cana.p90_dead(dead)}


def strata(mice, a, b, sex, sites=SITES, alive_at=None):
    """[(group a's mice, group b's mice)] per site; with alive_at, only the mice alive at that age."""
    keep = (lambda ms: ms) if alive_at is None else (lambda ms: [m for m in ms if m[0] >= alive_at])
    return [(keep(mice[(a, s, sex)]), keep(mice[(b, s, sex)])) for s in sites]


def logrank(mice, a, b, sex, **kw):
    return cana.logrank_strat_p(strata(mice, a, b, sex, **kw))


def conditions(med, lr, alt_cont):
    """Rule 4, by name: med[(group, sex)] the medians, lr[(group, sex)] the log-rank p against the controls, alt_cont
    the females' alternating-against-continuous p."""
    words = {"f": "females", "m": "males"}
    out = {}
    for g in (CONT, ALT):
        for x in SEXES:
            out[f"{NAMES[g]}, {words[x]}: p below 0.05 and a higher median"] = (
                lr[(g, x)] < ALPHA and med[(g, x)] > med[("Control", x)])
    out["3 months, males: p below 0.05 and a higher median"] = lr[(SHORT, "m")] < ALPHA and med[(SHORT, "m")] > med[
        ("Control", "m")]
    out["3 months, females: not p below 0.05 with a higher median"] = not (
        lr[(SHORT, "f")] < ALPHA and med[(SHORT, "f")] > med[("Control", "f")])
    out["females: alternating below continuous, a lower median and p below 0.05"] = (
        med[(ALT, "f")] < med[(CONT, "f")] and alt_cont < ALPHA)
    return out


def as_printed(p, printed):
    """Whether the data's p reads as the printed one: to its decimals, or below a printed '<' bound."""
    if printed.startswith("<"):
        return p < float(printed[1:])
    decimals = len(printed.split(".")[1]) if "." in printed else 0
    return f"{p:.{decimals}f}" == printed


def tables_check(mice):
    """How many of Tables 1 and 2's numbers the data give, by kind, and every comparison."""
    hits = {"counts": 0, "medians": 0, "P90": 0, "log-rank p": 0, "Wang-Allison p": 0}
    n = {"counts": 0, "medians": 0, "P90": 0, "log-rank p": 0, "Wang-Allison p": 0}
    rows = []
    for (g, x), (count, median, p90, lr, wa) in TABLE.items():
        got = summary(pooled(mice, g, x))
        ours = (got["count"], cana.half_up(got["median"]), cana.half_up(got["p90"]))
        for kind, p, o in zip(("counts", "medians", "P90"), (count, median, p90), ours):
            hits[kind] += int(p == o)
            n[kind] += 1
        row = {"group": g, "sex": x, "printed": [count, median, p90, lr, wa], "data": list(ours)}
        if lr is not None:
            p_lr = logrank(mice, "Control", g, x)
            p_wa = cana.wang_allison(strata(mice, "Control", g, x))[1]
            hits["log-rank p"] += int(as_printed(p_lr, lr))
            hits["Wang-Allison p"] += int(as_printed(p_wa, wa))
            n["log-rank p"] += 1
            n["Wang-Allison p"] += 1
            row["data"] += [p_lr, p_wa]
        rows.append(row)
    return "; ".join(f"{k} {hits[k]} of {n[k]}" for k in hits), rows


def sig(p):
    return float(f"{p:.3g}")


def fmt(x):
    return str(int(x)) if float(x).is_integer() else f"{x:.1f}"


def run(seed, inputs="inputs", results="results"):
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        raise Refused("the seed must be 64 hex characters")
    rows = rapa.read_rows(os.path.join(inputs, INPUT[0]), INPUT[1])
    mice, designs = mice_from_rows(rows)
    s = {(g, x): summary(pooled(mice, g, x)) for g in GROUPS for x in SEXES}
    med = {k: v["median"] for k, v in s.items()}
    lr = {(g, x): logrank(mice, "Control", g, x) for g in PROTOCOLS + OTHERS for x in SEXES}
    pairs = {(a, b, x): logrank(mice, a, b, x) for a, b in ((CONT, ALT), (CONT, SHORT), (ALT, SHORT)) for x in SEXES}
    alt_cont = pairs[(CONT, ALT, "f")]
    wa = {(g, x): cana.wang_allison(strata(mice, "Control", g, x)) for g in PROTOCOLS for x in SEXES}
    late = {(g, x): logrank(mice, "Control", g, x, alive_at=START) for g in PROTOCOLS for x in SEXES}
    late_n = {(g, x): (sum(len(c) for c, _ in strata(mice, "Control", g, x, alive_at=START)),
                       sum(len(t) for _, t in strata(mice, "Control", g, x, alive_at=START)))
              for g in PROTOCOLS for x in SEXES}
    cond = conditions(med, lr, alt_cont)
    matched, table_rows = tables_check(mice)

    def by_sex(x, keys, val):
        return ", ".join(f"{NAMES[g]} {val(g, x)}" for g in keys)
    values = {
        "n": "; ".join(f"{x}: " + ", ".join(f"{NAMES[g]} {s[(g, x)]['count']}" for g in ("Control",) + PROTOCOLS)
                       for x in ("m", "f")),
        "medians_m": by_sex("m", ("Control",) + PROTOCOLS, lambda g, x: fmt(med[(g, x)])),
        "medians_f": by_sex("f", ("Control",) + PROTOCOLS, lambda g, x: fmt(med[(g, x)])),
        "logrank_m": by_sex("m", PROTOCOLS, lambda g, x: sig(lr[(g, x)])),
        "logrank_f": by_sex("f", PROTOCOLS, lambda g, x: sig(lr[(g, x)])),
        "alt_vs_cont_f": (f"medians {fmt(med[(ALT, 'f')])} and {fmt(med[(CONT, 'f')])}; log-rank p "
                          f"{sig(alt_cont)}"),
        "pairwise_m": ", ".join(f"{NAMES[a]}-{NAMES[b]} {sig(pairs[(a, b, 'm')])}"
                                for a, b in ((CONT, ALT), (CONT, SHORT), (ALT, SHORT))),
        "pairwise_f": ", ".join(f"{NAMES[a]}-{NAMES[b]} {sig(pairs[(a, b, 'f')])}"
                                for a, b in ((CONT, ALT), (CONT, SHORT), (ALT, SHORT))),
        "wang_allison": "; ".join(f"{x}: " + ", ".join(f"{sig(wa[(g, x)][1])}" for g in PROTOCOLS) for x in ("m", "f"))
                        + " (continuous, alternating, 3 months)",
        "after_604": "; ".join(f"{x}: " + ", ".join(f"{sig(late[(g, x)])}" for g in PROTOCOLS) for x in ("m", "f"))
                     + " (continuous, alternating, 3 months)",
        "other_agents": "; ".join(f"{NAMES[g]} " + "/".join(f"{sig(lr[(g, x)])}" for x in ("m", "f")) for g in OTHERS)
                        + " (m/f)",
        "tables_matched": matched,
        "conditions_met": sum(cond.values()), "conditions_total": len(cond), "test_passed": int(all(cond.values())),
    }
    out = {k: values[k] for k in OUTPUTS}
    for k, v in out.items():
        if isinstance(v, str) and len(v) > LIMIT:
            raise AssertionError(f"{k}: longer than {LIMIT} characters: {v}")
    detail = {
        "input": {"name": INPUT[0], "sha256": INPUT[1], "rows": len(rows),
                  "designs": {g: list(d) for g, d in designs.items()}},
        "summaries": {f"{g} {x}": s[(g, x)] for g in GROUPS for x in SEXES},
        "sites": {f"{g} {site} {x}": summary(mice[(g, site, x)]) for g in ("Control",) + PROTOCOLS
                  for site in SITES for x in SEXES},
        "conditions": cond, "logrank": {f"{g} {x}": p for (g, x), p in lr.items()},
        "pairwise": {f"{a} {b} {x}": p for (a, b, x), p in pairs.items()},
        "wang_allison": {f"{g} {x}": {"table": t, "p": p} for (g, x), (t, p) in wa.items()},
        "after_604": {f"{g} {x}": {"p": late[(g, x)], "control_n": late_n[(g, x)][0], "treated_n": late_n[(g, x)][1]}
                      for g, x in late},
        "sites_logrank": {f"{g} {site} {x}": logrank(mice, "Control", g, x, sites=(site,))
                          for g in PROTOCOLS for site in SITES for x in SEXES},
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
        sys.exit(f"strong2020: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
