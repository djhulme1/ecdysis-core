#!/usr/bin/env python3
"""Canagliflozin from 6 months in the ITP's 2020 cohort, recomputed from the per-mouse data with the ITP's own test.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:7f61a9e620a3e016) is from Miller et al.,
"Lifespan effects in male UM-HET3 mice treated with sodium thiosulfate, 16-hydroxyestriol, and late-start
canagliflozin", GeroScience 46(5), 4657-4670 (2024): "Cana given to mice at 6 months led, as in our previous study, to
an increase in male lifespan without any change in female lifespan, suggesting that this agent may lead to
female-specific late-life harm." The previous study is Miller et al. 2020 (JCI Insight 5(21); ext:292a830531948ff3,
which this claim replicates: lnk:5465237a8125ae91).

Its registered test: refuted if, in the study's deposited per-mouse lifespans (the ITP's 2020 cohort of UM-HET3 mice;
canagliflozin at 180 ppm from 6 months, given at the Jackson Laboratory only), against that site's control mice, all
mice as assigned: the males' median age at death (the dead) is not above the controls', or their two-tailed log-rank
test (removed mice censored) gives p of 0.05 or more; or the females' log-rank test gives p below 0.05.

The input, and every check of its rows, are itp/cana2020.py's: the cohort's workbook at the Mouse Phenome Database,
ITP_C2020_Lifespan.xlsx (file id 710), the claim's data of record, checked against its SHA-256 and read as data with
the standard library. The statistics are that module's and itp/cana.py's. The paper's full text could not be read
here, so the comparison is the registered test's, stated before any seed existed; nothing is random, and the seed is
not used.

1. The mice: rule 1 of itp/cana2020.py (population, cohort, site, sex, whole days, status, group, and each group's
   dose and starting age in the workbook's own columns), which also refuses canagliflozin from 6 months anywhere but
   at the Jackson Laboratory (TJL). Its controls are the TJL controls. Mice that died or were removed before the start
   stay in their group, as assigned.
2. The medians: for each sex, the median age at death of the dead (removed mice left out), canagliflozin from 6 months
   and the TJL controls; a change is the canagliflozin median over the control median, less one.
3. The ITP's primary test: the two-tailed log-rank test for each sex, removed mice censored at removal (itp/cana.py's
   logrank_strat_p, one stratum: the one site).
4. The test's three conditions: the males' change above zero; the males' p below 0.05; the females' p at 0.05 or more.
   test_passed is 1 if all three hold.
5. Beside the test, none of it counted:
   - Kaplan-Meier medians, removed mice censored;
   - the 90th percentile of the dead, as the previous study reports it, and the Wang-Allison test at the 90th
     percentile (itp/cana.py's wang_allison: Fisher's exact p);
   - only the mice alive at 6 months (183 days, 6 x 30.44): each sex's change and p;
   - against all three sites' controls, a reading that ignores where the drug was given: each sex's change and the
     unstratified p;
   - the cohort's group sizes.

What it cannot check: the paper's own pooling and tests (its full text was not read), and the sentence's inference
of female-specific late-life harm, which the 16-month arm of the same cohort bears on (ext:48bb5699582dabc1).

Writes results/outputs.json (the 17 values a receipt carries) and results/detail.json (every value computed).
"""

import importlib.util
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def _load(name, file):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, file))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


c20 = _load("itp_cana2020", "cana2020.py")
cana, rapa, Refused = c20.cana, c20.rapa, c20.Refused

INPUT = c20.INPUT
GROUP, SITE = "Cana_6", "TJL"
ALPHA = 0.05
START_DAYS = 183           # 6 months of 30.44 days
LIMIT = 200
OUTPUTS = ("n", "median_m_control", "median_m_cana", "median_f_control", "median_f_cana", "change_m", "change_f",
           "logrank_p_m", "logrank_p_f", "km_medians", "p90_wang_allison", "from_6_months", "all_controls", "groups",
           "conditions_met", "conditions_total", "test_passed")


def conditions(changes, ps):
    """Rule 4."""
    return {"males: median above the controls'": changes["m"] > 0,
            "males: log-rank p below 0.05": ps["m"] < ALPHA,
            "females: log-rank p 0.05 or more": ps["f"] >= ALPHA}


def p90(ms):
    return cana.p90_dead([t for t, d in ms if d])


def run(seed, inputs="inputs", results="results"):
    rows = rapa.read_rows(os.path.join(inputs, INPUT[0]), INPUT[1])
    mice, counts = c20.mice_from_rows(rows)
    here = (SITE,)
    med, ch, ps = {}, {}, {}
    for x in c20.SEXES:
        c, t, r = c20.change(mice, GROUP, x, here)
        med[x], ch[x], ps[x] = (c, t), r, c20.logrank(mice, GROUP, x, here)
    cond = conditions(ch, ps)
    ctl = {x: c20.pooled(mice, "Control", x, here) for x in c20.SEXES}
    trt = {x: c20.pooled(mice, GROUP, x, here) for x in c20.SEXES}
    km = {x: (c20.km_median(ctl[x]), c20.km_median(trt[x])) for x in c20.SEXES}
    nineties = {x: (p90(ctl[x]), p90(trt[x])) for x in c20.SEXES}
    wa = {x: cana.wang_allison([(ctl[x], trt[x])]) for x in c20.SEXES}
    older = c20.alive_at(mice, START_DAYS)
    from6 = {x: (c20.change(older, GROUP, x, here)[2], c20.logrank(older, GROUP, x, here)) for x in c20.SEXES}
    allc = {x: c20.change(mice, GROUP, x, here, c20.SITES) for x in c20.SEXES}
    allp = {x: cana.logrank_strat_p([(c20.pooled(mice, "Control", x, c20.SITES), trt[x])]) for x in c20.SEXES}
    fmt, pct, sig = c20.fmt, c20.pct, c20.sig

    def dead(ms):
        return sum(1 for _, d in ms if d)

    values = {
        "n": "; ".join(f"{x} Control {len(ctl[x])} ({dead(ctl[x])} dead), {GROUP} {len(trt[x])} ({dead(trt[x])} dead)"
                       for x in ("m", "f")) + f" ({SITE})",
        "median_m_control": float(med["m"][0]), "median_m_cana": float(med["m"][1]),
        "median_f_control": float(med["f"][0]), "median_f_cana": float(med["f"][1]),
        "change_m": round(ch["m"], 6), "change_f": round(ch["f"], 6),
        "logrank_p_m": sig(ps["m"]), "logrank_p_f": sig(ps["f"]),
        "km_medians": "; ".join(f"{x} {km[x][0]} to {km[x][1]} ({pct(km[x][1] / km[x][0] - 1)})" for x in ("m", "f")),
        "p90_wang_allison": "; ".join(f"{x} 90th percentile {nineties[x][0]} to {nineties[x][1]} "
                                      f"({pct(nineties[x][1] / nineties[x][0] - 1)}), Wang-Allison p {sig(wa[x][1])}"
                                      for x in ("m", "f")),
        "from_6_months": "; ".join(f"{x} {pct(from6[x][0])} (p {sig(from6[x][1])})" for x in ("m", "f"))
                         + f" among the mice alive at {START_DAYS} days",
        "all_controls": "; ".join(f"{x} {fmt(allc[x][0])} to {fmt(allc[x][1])} ({pct(allc[x][2])}, unstratified p "
                                  f"{sig(allp[x])})" for x in ("m", "f")) + " against all three sites' controls",
        "groups": f"{len(rows)} mice; " + ", ".join(f"{g} {counts[g]}" for g in c20.GROUPS),
        "conditions_met": sum(cond.values()), "conditions_total": len(cond), "test_passed": int(all(cond.values())),
    }
    out = {k: values[k] for k in OUTPUTS}
    for k, v in out.items():
        if isinstance(v, str) and len(v) > LIMIT:
            raise AssertionError(f"{k}: longer than {LIMIT} characters: {v}")
    detail = {
        "input": {"name": INPUT[0], "sha256": INPUT[1], "rows": len(rows), "groups": counts},
        "conditions": cond, "medians": med, "changes": ch, "logrank": ps, "km_medians": km,
        "p90": nineties, "wang_allison": {x: {"table": wa[x][0], "p": wa[x][1]} for x in c20.SEXES},
        "from_6_months": from6,
        "all_controls": {x: {"medians": allc[x][:2], "change": allc[x][2], "p_unstratified": allp[x]}
                         for x in c20.SEXES},
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
        sys.exit(f"cana2020_6: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
