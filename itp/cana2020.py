#!/usr/bin/env python3
"""Canagliflozin from 16 months in the ITP's 2020 cohort, recomputed from the per-mouse data with the ITP's own test.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:48bb5699582dabc1) is from Miller et al.,
"Lifespan effects in male UM-HET3 mice treated with sodium thiosulfate, 16-hydroxyestriol, and late-start
canagliflozin", GeroScience 46(5), 4657-4670 (2024; two corrections, to its author list and Figure 3 and to the name
of 16-hydroxyestradiol, neither to a number): "Cana, started at 16 months, also led to a significant increase (14%,
p = 0.004) in males and a significant decline (6%, p = 0.03) in females."

Its registered test: refuted if, in the study's deposited per-mouse lifespans (the ITP's 2020 cohort of UM-HET3 mice;
canagliflozin at 180 ppm from 16 months, given at Michigan and Texas), against those two sites' control mice, all mice
as assigned, the males' median age at death (the dead pooled) rises by less than 7% (half the 14% printed) or the
log-rank test stratified by site (removed mice censored) gives p of 0.05 or more; or the females' median falls by less
than 3% (half the 6% printed) or that test gives p of 0.05 or more.

The input is the cohort's workbook at the Mouse Phenome Database (project ITP2020, whose investigators are the paper's
authors): ITP_C2020_Lifespan.xlsx (file id 710), the claim's data of record, checked against its SHA-256 and read with
the standard library by itp/rapa.py's reader (its XML parsed as data; nothing in it is run). MPD keeps an earlier file
beside it, marked deprecated (id 709), which differs in one mouse of another group. The statistics are itp/cana.py's.
The paper's full text could not be read here, so the comparison is the registered test's, stated before any seed
existed; the seed is not used, as nothing here is random.

1. The mice. Every row must be of population UM-HET3 and cohort C2020, at site TJL, UM or UT, of sex f or m, with a
   whole number of days as its age, and either dead (status "dead", dead 1) or removed (status "removed", dead 0); its
   group must be one of the cohort's ten; a row of the three groups used here must carry its group's design in the
   workbook's own columns (DESIGN below: the dose in ppm and the starting age in months), and canagliflozin from 16
   months must be at Michigan or Texas, from 6 months at the Jackson Laboratory, as the cohort gave them. Mice that
   died or were removed before their start stay in their group, as assigned.
2. The medians. For each sex, the median age at death of the dead of Michigan and Texas pooled (removed mice left
   out), for canagliflozin from 16 months and for the two sites' controls: the middle age, or the mean of the two
   middle ones. A change is the canagliflozin median over the control median, less one.
3. The ITP's primary test: the two-tailed log-rank test for each sex, stratified by site (Michigan and Texas), removed
   mice censored at removal (itp/cana.py's rule 4).
4. The test's four conditions: the males' change at least 0.07 and their p below 0.05; the females' change at most
   -0.03 and their p below 0.05. test_passed is 1 if all four hold.
5. Beside the test.
   - The same comparison against all three sites' controls, as a reading of "against the cohort's controls" that
     ignores where the drug was given: the change in pooled medians and the unstratified log-rank p.
   - Kaplan-Meier medians (removed mice censored) of the site-matched groups.
   - Only the mice alive at 16 months (487 days, 16 x 30.44): the changes and the stratified p.
   - Each site's medians and log-rank p.
   - Canagliflozin from 6 months at the Jackson Laboratory against that site's controls, the abstract's next sentence
     ("Cana given to mice at 6 months led, as in our previous study, to an increase in male lifespan without any change
     in female lifespan"): each sex's change and log-rank p.
   - The abstract's numbers beside the data's.

What it cannot check: the paper's own pooling and tests (its full text was not read), so the printed 14% and p values
are compared, not explained.

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

INPUT = ("ITP_C2020_Lifespan.xlsx", "7b97cd4cd238e8feb18a996ba80f7112fb7e574c3db4204216efcae469e15603")
POPULATION, COHORT = "UM-HET3", "C2020"
SITES, SEXES = ("TJL", "UM", "UT"), ("f", "m")
GROUPS = ("Control", "Cana_16", "Cana_6", "AKG_18", "DNP", "HYD_16", "HYD_6", "NEBI", "OH-EST", "THIO")
USED = ("Control", "Cana_16", "Cana_6")
DESIGN = {"Control": ("0", "NA"), "Cana_16": ("180", "16"), "Cana_6": ("180", "6")}
WHERE = {"Cana_16": ("UM", "UT"), "Cana_6": ("TJL",)}
RISE_M, FALL_F, ALPHA = 0.07, -0.03, 0.05
START_DAYS = 487
PRINTED = {"m": ("+14%", "0.004"), "f": ("-6%", "0.03")}
LIMIT = 200
OUTPUTS = ("n", "median_m_control", "median_m_cana", "median_f_control", "median_f_cana", "change_m", "change_f",
           "logrank_p_m", "logrank_p_f", "all_controls", "km_medians", "from_16_months", "sites", "cana_6",
           "printed", "groups", "conditions_met", "conditions_total", "test_passed")


class Refused(Exception):
    pass


def mice_from_rows(rows):
    """{(group, site, sex): [(age, died)]} for the three groups used; every row checked against rule 1."""
    out = {(g, s, x): [] for g in USED for s in SITES for x in SEXES}
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
        if g in USED:
            design = (r.get("Rx(ppm)"), r.get("age_initiation(mo)"))
            if design != DESIGN[g]:
                raise Refused(f"row {i}: group {g} carries {design}, not {DESIGN[g]}")
            if g in WHERE and r["site"] not in WHERE[g]:
                raise Refused(f"row {i}: group {g} at {r['site']}, where the cohort did not give it")
            out[(g, r["site"], r["sex"])].append((int(float(age)), state[0] == "dead"))
    return out, counts


def pooled(mice, group, sex, sites):
    return [m for s in sites for m in mice[(group, s, sex)]]


def median_of_dead(ms):
    dead = [t for t, d in ms if d]
    if not dead:
        raise Refused("a group with no deaths")
    return statistics.median(dead)


def change(mice, group, sex, sites, ctl_sites=None):
    """Rule 2: the group's median over the controls' (of ctl_sites, by default the same sites), less one."""
    c = median_of_dead(pooled(mice, "Control", sex, ctl_sites or sites))
    t = median_of_dead(pooled(mice, group, sex, sites))
    return c, t, t / c - 1


def logrank(mice, group, sex, sites):
    """Rule 3: the log-rank p stratified by the given sites."""
    return cana.logrank_strat_p([(mice[("Control", s, sex)], mice[(group, s, sex)]) for s in sites])


def km_median(ms):
    """The least age at which the Kaplan-Meier survival (removed mice censored) falls to one half or below."""
    s = 1.0
    for t in sorted({t for t, d in ms if d}):
        n = sum(1 for x, _ in ms if x >= t)
        d = sum(1 for x, dd in ms if x == t and dd)
        s *= 1 - d / n
        if s <= 0.5 + 1e-12:
            return t
    raise Refused("a Kaplan-Meier curve that never reaches one half")


def alive_at(mice, days):
    return {k: [m for m in v if m[0] >= days] for k, v in mice.items()}


def conditions(changes, ps):
    return {"males: median at least 7% above the controls'": changes["m"] >= RISE_M,
            "males: log-rank p below 0.05": ps["m"] < ALPHA,
            "females: median at least 3% below the controls'": changes["f"] <= FALL_F,
            "females: log-rank p below 0.05": ps["f"] < ALPHA}


def pct(x):
    return f"{100 * x:+.1f}%"


def sig(p):
    return float(f"{p:.4g}")


def fmt(x):
    return str(int(x)) if float(x).is_integer() else f"{x:.1f}"


def run(seed, inputs="inputs", results="results"):
    rows = rapa.read_rows(os.path.join(inputs, INPUT[0]), INPUT[1])
    mice, counts = mice_from_rows(rows)
    late = WHERE["Cana_16"]
    med, ch, ps = {}, {}, {}
    for x in SEXES:
        c, t, r = change(mice, "Cana_16", x, late)
        med[x], ch[x], ps[x] = (c, t), r, logrank(mice, "Cana_16", x, late)
    cond = conditions(ch, ps)
    allc = {x: change(mice, "Cana_16", x, late, SITES) for x in SEXES}
    allp = {x: cana.logrank_strat_p([(pooled(mice, "Control", x, SITES), pooled(mice, "Cana_16", x, late))]) for x in SEXES}
    km = {x: (km_median(pooled(mice, "Control", x, late)), km_median(pooled(mice, "Cana_16", x, late))) for x in SEXES}
    older = alive_at(mice, START_DAYS)
    from16 = {x: (change(older, "Cana_16", x, late)[2], logrank(older, "Cana_16", x, late)) for x in SEXES}
    per_site = {(s, x): (change(mice, "Cana_16", x, (s,))[:2], logrank(mice, "Cana_16", x, (s,))) for s in late for x in SEXES}
    six = {x: (change(mice, "Cana_6", x, WHERE["Cana_6"]), logrank(mice, "Cana_6", x, WHERE["Cana_6"])) for x in SEXES}
    n = {(g, x): pooled(mice, g, x, late) for g in ("Control", "Cana_16") for x in SEXES}
    values = {
        "n": "; ".join(f"{x} " + ", ".join(f"{g} {len(n[(g, x)])} ({sum(1 for _, d in n[(g, x)] if d)} dead)"
                                         for g in ("Control", "Cana_16")) for x in ("m", "f")) + " (UM and UT)",
        "median_m_control": float(med["m"][0]), "median_m_cana": float(med["m"][1]),
        "median_f_control": float(med["f"][0]), "median_f_cana": float(med["f"][1]),
        "change_m": round(ch["m"], 6), "change_f": round(ch["f"], 6),
        "logrank_p_m": sig(ps["m"]), "logrank_p_f": sig(ps["f"]),
        "all_controls": "; ".join(f"{x} {fmt(allc[x][0])} to {fmt(allc[x][1])} ({pct(allc[x][2])}, unstratified p "
                                  f"{sig(allp[x])})" for x in ("m", "f")) + " against all three sites' controls",
        "km_medians": "; ".join(f"{x} {km[x][0]} to {km[x][1]} ({pct(km[x][1] / km[x][0] - 1)})" for x in ("m", "f")),
        "from_16_months": "; ".join(f"{x} {pct(from16[x][0])} (p {sig(from16[x][1])})" for x in ("m", "f"))
                          + f" among the mice alive at {START_DAYS} days",
        "sites": "; ".join(f"{s} {x} {fmt(per_site[(s, x)][0][0])} to {fmt(per_site[(s, x)][0][1])} (p "
                           f"{sig(per_site[(s, x)][1])})" for s in late for x in ("m", "f")),
        "cana_6": "; ".join(f"{x} {fmt(six[x][0][0])} to {fmt(six[x][0][1])} ({pct(six[x][0][2])}, p {sig(six[x][1])})"
                            for x in ("m", "f")) + " (from 6 months, TJL)",
        "printed": "; ".join(f"{x} printed {PRINTED[x][0]} (p {PRINTED[x][1]}), data {pct(ch[x])} (p {sig(ps[x])})"
                             for x in ("m", "f")),
        "groups": f"{len(rows)} mice; " + ", ".join(f"{g} {counts[g]}" for g in GROUPS),
        "conditions_met": sum(cond.values()), "conditions_total": len(cond), "test_passed": int(all(cond.values())),
    }
    out = {k: values[k] for k in OUTPUTS}
    for k, v in out.items():
        if isinstance(v, str) and len(v) > LIMIT:
            raise AssertionError(f"{k}: longer than {LIMIT} characters: {v}")
    detail = {
        "input": {"name": INPUT[0], "sha256": INPUT[1], "rows": len(rows), "groups": counts},
        "conditions": cond, "medians": {x: med[x] for x in SEXES}, "changes": ch, "logrank": ps,
        "all_controls": {x: {"medians": allc[x][:2], "change": allc[x][2], "p_unstratified": allp[x]} for x in SEXES},
        "km_medians": km, "from_16_months": from16,
        "sites": {f"{s} {x}": {"medians": v[0], "p": v[1]} for (s, x), v in per_site.items()},
        "cana_6": {x: {"medians": six[x][0][:2], "change": six[x][0][2], "p": six[x][1]} for x in SEXES},
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
        sys.exit(f"cana2020: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
