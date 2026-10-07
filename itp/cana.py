#!/usr/bin/env python3
"""Canagliflozin and male lifespan in the ITP's 2016 cohort, recomputed from the per-mouse data.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:292a830531948ff3) is from Miller et al.,
"Canagliflozin extends life span in genetically heterogeneous male but not female mice", JCI Insight 5(21) (2020):
"Cana extended median survival of male mice by 14%. Cana also increased by 9% the age for 90th percentile survival,
with parallel effects seen at each of 3 test sites."

Its registered test: refuted if, in the study's own per-mouse lifespans (the ITP's 2016 cohort of UM-HET3 males fed
canagliflozin or the control diet at its three sites; removed mice left out, as the paper does), canagliflozin raises
the median age at death by less than 7% or the age at 90th percentile survival by less than 4.5% (half the reported
14% and 9%), each taken as the mean of the three site values, as the paper's Table 1 pools them; or if either is not
higher than the controls' at each of the three sites.

The input is the workbook the paper names as its data's home (the Mouse Phenome Database, project ITP1):
ITP_C2016_Lifespan.xlsx, checked against its SHA-256 and read with the standard library by itp/rapa.py's reader (its
XML parsed as data; nothing in it is run). Every rule below was fixed before any seed existed.

1. The mice. Every row must be of cohort C2016, at site TJL, UM or UT, of sex f or m, with a whole number of days as
   its age, and either dead (status "dead", dead 1) or removed (status "removed", dead 0); anything else is refused.
   The groups are "Control" and "Cana" (canagliflozin at 180 ppm from 7 months), as assigned. Counts include removed
   mice, as Table 1's do.
2. Median and 90th percentile, for each site, sex and group, among the dead only, as the paper says: removed mice
   "are included in the Kaplan-Meier survival calculations but not in calculations of median or 90th percentile
   survival". The median is the middle age at death (the mean of the two middle ones when the count is even). The
   90th percentile is the least age by which at least 90% of the dead had died.
3. Pooling. A pooled value is the mean of the three site values, as Table 1's "Pool" rows are (its male control
   median, 787, is the mean of 749, 814 and 799). A gain is the canagliflozin value over the control value, less one.
4. The paper's own tests, beside the test. The log-rank test stratified by site, for each sex, with removed mice
   censored at removal (the paper's prespecified primary outcome). The Wang-Allison test in its Fisher exact form: at
   each site the cut-off is the 90th percentile of the dead of both groups together by R's default rule (type 7); a
   mouse counts above it if it lived beyond it (dead or removed later) and below it if it died at or before it (a
   mouse removed at or before it is left out); the three sites' tables are summed; the two-sided p is R's, the total
   probability of the tables no more probable than the observed one (relative tolerance 1e-7), in exact integers.
5. Table 1, checked. The paper prints 16 rows (each sex: control and canagliflozin, pooled and at each site), each
   with a count, a median and a 90th percentile. table1_matched counts the 48 printed numbers that the data give
   when rounded to whole days, halves up.
6. A bootstrap of the two male gains under the site-mean rule: within each site, the dead control males and the
   dead canagliflozin males are each resampled with replacement, BOOTSTRAP times, with draws from ECDYSIS_SEED
   (SHA-256 in counter mode, itp/rapa.py's Stream, labelled "itp/cana/bootstrap"), the only randomness used. The
   2.5th percentile of each gain is reported.

test_passed is 1 if the male median gain is at least 0.07 and the male 90th-percentile gain at least 0.045, both by
the site-mean rule, and at each of the three sites the canagliflozin males' median and 90th percentile both exceed
the controls'; else 0.

What it cannot check:
- the cohort beyond the workbook: ages are as the ITP recorded them; how a mouse was judged moribund, or why one was
  removed, is not in the data;
- the pooling rule's source: the site-mean rule is read from Table 1, which it reproduces to the day; the paper's
  methods do not state it;
- other cohorts: the ITP's 2020 cohort, which started canagliflozin at 6 and at 16 months, would be another receipt.

Writes results/outputs.json (the 20 values a receipt carries) and results/detail.json (every value computed).
"""

import importlib.util
import json
import math
import os
import re
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("itp_rapa", os.path.join(HERE, "rapa.py"))
rapa = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rapa)

INPUT = ("ITP_C2016_Lifespan.xlsx", "8c23eb208a1c4dd46b6ce9cee788796a25a2844cbee62e72a7693198cda330df")
COHORT, SITES, SEXES, GROUPS = "C2016", ("TJL", "UM", "UT"), ("m", "f"), ("Control", "Cana")
BOOTSTRAP = 1000
MEDIAN_GAIN, P90_GAIN = 0.07, 0.045      # half the reported 14% and 9%

# Table 1 as printed: (group, site or "Pool", sex) -> (count, median, 90th percentile), in days.
TABLE1 = {
    ("Control", "Pool", "m"): (303, 787, 1047), ("Cana", "Pool", "m"): (156, 897, 1143),
    ("Control", "TJL", "m"): (102, 749, 1005), ("Cana", "TJL", "m"): (54, 880, 1159),
    ("Control", "UM", "m"): (102, 814, 1071), ("Cana", "UM", "m"): (51, 946, 1170),
    ("Control", "UT", "m"): (99, 799, 1064), ("Cana", "UT", "m"): (51, 866, 1099),
    ("Control", "Pool", "f"): (304, 874, 1050), ("Cana", "Pool", "f"): (136, 886, 1059),
    ("Control", "TJL", "f"): (96, 883, 1057), ("Cana", "TJL", "f"): (48, 912, 1097),
    ("Control", "UM", "f"): (92, 858, 1034), ("Cana", "UM", "f"): (44, 897, 1076),
    ("Control", "UT", "f"): (116, 882, 1058), ("Cana", "UT", "f"): (44, 849, 1003),
}


class Refused(Exception):
    pass


def mice_from_rows(rows):
    """{(group, site, sex): [(age, died)]} for the two groups, every row checked against rule 1."""
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
        if r.get("group") in GROUPS:
            out[(r["group"], r["site"], r["sex"])].append((int(float(age)), state[0] == "dead"))
    return out


def median_dead(ages):
    return statistics.median(ages)


def p90_dead(ages):
    """The least age by which at least 90% of the dead had died."""
    a = sorted(ages)
    return a[math.ceil(0.9 * len(a)) - 1]


def quantile7(ages, q):
    """R's default quantile (type 7): linear between order statistics at position (n - 1) q."""
    a = sorted(ages)
    h = (len(a) - 1) * q
    lo = math.floor(h)
    hi = min(lo + 1, len(a) - 1)
    return a[lo] + (h - lo) * (a[hi] - a[lo])


def logrank_strat_p(strata):
    """Two-sided log-rank p, stratified: strata is a list of (a, b), each a list of (age, died)."""
    o_minus_e = var = 0.0
    for a, b in strata:
        for t in sorted({t for t, d in a + b if d}):
            na = sum(1 for x, _ in a if x >= t)
            nb = sum(1 for x, _ in b if x >= t)
            da = sum(1 for x, d in a if x == t and d)
            db = sum(1 for x, d in b if x == t and d)
            n, d = na + nb, da + db
            if n < 2:
                continue
            o_minus_e += da - d * na / n
            var += d * (na / n) * (1 - na / n) * (n - d) / (n - 1)
    return math.erfc(math.sqrt(o_minus_e * o_minus_e / var / 2))


def fisher_two_sided(table):
    """R's fisher.test two-sided p for [[a, b], [c, d]], in exact integers."""
    (a, b), (c, d) = table
    r1, r2, c1 = a + b, c + d, a + c
    lo, hi = max(0, c1 - r2), min(r1, c1)
    weights = {x: math.comb(r1, x) * math.comb(r2, c1 - x) for x in range(lo, hi + 1)}
    observed = weights[a]
    kept = sum(w for w in weights.values() if w * 10 ** 7 <= observed * (10 ** 7 + 1))
    return kept / math.comb(r1 + r2, c1)


def wang_allison(strata):
    """Summed per-site Wang-Allison table (rows: control, treated; columns: above, below) and its Fisher p."""
    table = [[0, 0], [0, 0]]
    for ctl, trt in strata:
        cut = quantile7([t for t, d in ctl + trt if d], 0.9)
        for row, mice in ((0, ctl), (1, trt)):
            table[row][0] += sum(1 for t, _ in mice if t > cut)
            table[row][1] += sum(1 for t, d in mice if d and t <= cut)
    return table, fisher_two_sided(table)


def summarise(mice, sex):
    """Per site and pooled (site-mean) medians and 90th percentiles of the dead, for both groups."""
    out = {}
    for g in GROUPS:
        per = {}
        for s in SITES:
            dead = [t for t, d in mice[(g, s, sex)] if d]
            per[s] = {"count": len(mice[(g, s, sex)]), "dead": len(dead), "median": median_dead(dead),
                      "p90": p90_dead(dead)}
        per["Pool"] = {"count": sum(per[s]["count"] for s in SITES), "dead": sum(per[s]["dead"] for s in SITES),
                       "median": sum(per[s]["median"] for s in SITES) / 3,
                       "p90": sum(per[s]["p90"] for s in SITES) / 3}
        out[g] = per
    return out


def half_up(x):
    return math.floor(x + 0.5)


def table1_check(summaries):
    """How many of Table 1's 48 printed numbers the data give, and every comparison."""
    matched, rows = 0, []
    for (g, site, sex), printed in TABLE1.items():
        got = summaries[sex][g][site]
        ours = (got["count"], half_up(got["median"]), half_up(got["p90"]))
        matched += sum(1 for p, o in zip(printed, ours) if p == o)
        rows.append({"group": g, "site": site, "sex": sex, "printed": list(printed), "data": list(ours)})
    return matched, rows


def gains(summary):
    c, t = summary["Control"]["Pool"], summary["Cana"]["Pool"]
    return t["median"] / c["median"] - 1, t["p90"] / c["p90"] - 1


def verdict(summary_m):
    """(test_passed, every site higher) for the males' summary, by the registered test."""
    median_gain, p90_gain = gains(summary_m)
    c, t = summary_m["Control"], summary_m["Cana"]
    every_site = all(t[s]["median"] > c[s]["median"] and t[s]["p90"] > c[s]["p90"] for s in SITES)
    return (1 if median_gain >= MEDIAN_GAIN and p90_gain >= P90_GAIN and every_site else 0), every_site


def bootstrap(mice, seed):
    """2.5th percentiles of the male median and 90th-percentile gains (site-mean rule), resampled within sites."""
    stream = rapa.Stream(seed, "itp/cana/bootstrap")
    dead = {(g, s): [t for t, d in mice[(g, s, "m")] if d] for g in GROUPS for s in SITES}
    med, p90 = [], []
    for _ in range(BOOTSTRAP):
        values = {}
        for g in GROUPS:
            for s in SITES:
                pool = dead[(g, s)]
                values[(g, s)] = [pool[stream.below(len(pool))] for _ in pool]
        mc = sum(median_dead(values[("Control", s)]) for s in SITES)
        mt = sum(median_dead(values[("Cana", s)]) for s in SITES)
        pc = sum(p90_dead(values[("Control", s)]) for s in SITES)
        pt = sum(p90_dead(values[("Cana", s)]) for s in SITES)
        med.append(mt / mc - 1)
        p90.append(pt / pc - 1)
    med.sort()
    p90.sort()
    k = int(0.025 * BOOTSTRAP)
    return med[k], p90[k]


def fmt(x):
    return str(int(x)) if float(x).is_integer() else f"{x:.1f}"


def run(seed, inputs="inputs", results="results"):
    rows = rapa.read_rows(os.path.join(inputs, INPUT[0]), INPUT[1])
    mice = mice_from_rows(rows)
    summaries = {sex: summarise(mice, sex) for sex in SEXES}
    matched, table1 = table1_check(summaries)
    m, f = summaries["m"], summaries["f"]
    inc_med_m, inc_p90_m = gains(m)
    inc_med_f, inc_p90_f = gains(f)
    strata = {sex: [(mice[("Control", s, sex)], mice[("Cana", s, sex)]) for s in SITES] for sex in SEXES}
    lr = {sex: logrank_strat_p(strata[sex]) for sex in SEXES}
    wa = {sex: wang_allison(strata[sex]) for sex in SEXES}
    wa_sites = {sex: {s: wang_allison([pair])[1] for s, pair in zip(SITES, strata[sex])} for sex in SEXES}
    lr_sites = {sex: {s: logrank_strat_p([pair]) for s, pair in zip(SITES, strata[sex])} for sex in SEXES}
    boot_med, boot_p90 = bootstrap(mice, seed)
    passed, every_site = verdict(m)
    removed_m = sum(1 for g in GROUPS for s in SITES for _, d in mice[(g, s, "m")] if not d)
    out = {
        "n_m_control": m["Control"]["Pool"]["count"],
        "n_m_cana": m["Cana"]["Pool"]["count"],
        "removed_m": removed_m,
        "median_m_control": round(m["Control"]["Pool"]["median"], 4),
        "median_m_cana": round(m["Cana"]["Pool"]["median"], 4),
        "inc_median_m": round(inc_med_m, 6),
        "p90_m_control": round(m["Control"]["Pool"]["p90"], 4),
        "p90_m_cana": round(m["Cana"]["Pool"]["p90"], 4),
        "inc_p90_m": round(inc_p90_m, 6),
        "sites_m": "; ".join(f"{s} median {fmt(m['Control'][s]['median'])}->{fmt(m['Cana'][s]['median'])}, "
                             f"p90 {fmt(m['Control'][s]['p90'])}->{fmt(m['Cana'][s]['p90'])}" for s in SITES),
        "inc_median_f": round(inc_med_f, 6),
        "inc_p90_f": round(inc_p90_f, 6),
        "logrank_p_m": float(f"{lr['m']:.3e}"),
        "logrank_p_f": float(f"{lr['f']:.3e}"),
        "wa_p_m": float(f"{wa['m'][1]:.3e}"),
        "wa_p_f": float(f"{wa['f'][1]:.3e}"),
        "boot_inc_median_m_low": round(boot_med, 6),
        "boot_inc_p90_m_low": round(boot_p90, 6),
        "table1_matched": matched,
    }
    out["test_passed"] = passed
    detail = {
        "input": {"name": INPUT[0], "sha256": INPUT[1], "rows": len(rows)},
        "summaries": summaries,
        "table1": {"matched": matched, "of": 3 * len(TABLE1), "rows": table1},
        "gains": {"m": {"median": inc_med_m, "p90": inc_p90_m}, "f": {"median": inc_med_f, "p90": inc_p90_f}},
        "every_site_higher_m": every_site,
        "logrank": {"stratified": lr, "per_site": lr_sites},
        "wang_allison": {"summed": {sex: {"table": wa[sex][0], "p": wa[sex][1]} for sex in SEXES},
                         "per_site": wa_sites},
        "bootstrap": {"resamples": BOOTSTRAP, "median_low": boot_med, "p90_low": boot_p90},
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
        sys.exit(f"cana: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
