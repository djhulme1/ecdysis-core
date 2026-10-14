#!/usr/bin/env python3
"""Captopril and female lifespan in the ITP's 2017 cohort, with and without its short-lived UT controls.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:049e04f7d49b7db1) is from Strong et al.,
"Lifespan benefits for the combination of rapamycin plus acarbose and for captopril in genetically heterogeneous mice",
Aging Cell 21(12), e13724 (2022): "Capt led to a significant, though small (4% or 5%), increase in female lifespan."
The paper's Discussion gives the two numbers' sources: "Captopril led to small (4% or 5%) but significant increases in
female lifespan regardless of whether UT mice were included", the 5% from all three sites (Table 1) and the 4% from its
ad hoc analysis of TJL and UM alone, made because the cohort's UT controls were unusually short-lived.

Its registered test: refuted if, in the C2017 cohort's deposited per-mouse lifespans (MPD file 737), the females fed
captopril (180 ppm from 5 months) against the cohort's control females, pooled over its three sites or over TJL and UM
alone (the paper's analysis without UT's short-lived controls), have a median age at death (the dead pooled, removed
mice left out) less than 2% above the controls', or a site-stratified log-rank p (removed mice censored) of 0.05 or
more.

The input is the cohort's workbook at the Mouse Phenome Database (project ITP1), ITP_C2017_Lifespan.xlsx, the claim's
data of record, checked against its SHA-256 and read with the standard library by itp/rapa.py's reader (its XML parsed
as data; nothing in it is run). The statistics are itp/cana.py's. Every rule below was fixed before any lifespan was
computed; the seed is not used, as nothing here is random.

1. The mice. Every row must be of population UM-HET3 and cohort C2017, at site TJL, UM or UT, of sex f or m, with a
   whole number of days as its age, and either dead (status "dead", dead 1) or removed (status "removed", dead 0). The
   groups compared must carry their design in the workbook's own columns: Capt (dose 180, from 5 months) and Control
   (dose 0, no start). Otherwise the run is refused.
2. The median, as Table 1 takes it for pooled data: the median age at death of the dead of the sites considered taken
   together (removed mice left out, as Table 1's note says), the middle age or the mean of the two middle ones. The
   gain is the captopril median over the control median, less one.
3. The log-rank test, as the paper's statistical methods state it: two-sided, stratified by site over the sites
   considered, captopril against control, removed mice censored at their removal (treated as alive until then, as
   section 4.3 says).
4. The test's four conditions, for females: over the three sites, the gain at least 2% and the log-rank p below 0.05;
   over TJL and UM alone, the same two. test_passed is 1 if all four hold.
5. Beside the test, against what the paper prints: Table 1's pooled rows for captopril and the controls in each sex
   (counts of the dead, medians, gains, log-rank p, 90th percentiles and their gains, Wang-Allison p), Tables 2 and 3's
   site rows, and the ad hoc two-site results its text gives (females 4%, p 0.04, Wang-Allison 0.06; males 6%,
   p < 0.26). Medians, percentiles and gains are compared rounded half up to the precision printed; a p value at the
   decimals printed. The 90th percentile is read two ways, itp/cana.py's (the least age by which 90% of the dead had
   died) and R's default quantile, and the one that reproduces more of the printed values is reported. The
   Wang-Allison test is itp/cana.py's (per site, the cut at the 90th percentile of the dead of both groups, R's
   quantile; the tables summed; Fisher's exact test). Also: each condition's statistic with removed mice left out of
   the log-rank test, and the median taken as the mean of site medians.
6. Controls, known answers: the stratified log-rank test of two groups of two (deaths at 1 and 2 against 3 and 4) gives
   chi-square 49/17, and a group against itself gives p 1; Fisher's exact test gives 17/35 for [[3, 1], [1, 3]]; the
   median of the dead and the 90th percentile give their hand values on a small list.

What it cannot check: the cohort beyond the workbook, and the data as the paper read them, from which the deposit may
differ (rule 5 says where).

Writes results/outputs.json (the values a receipt carries) and results/detail.json (every value computed).
Run with: python3 itp/capt2017.py
"""

import importlib.util
import json
import math
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

INPUTS = {"C2017": ("ITP_C2017_Lifespan.xlsx", "1f1ab41e6497c92bc926ee9ba63f617a239549745ecd2ceede7932fdbf36dc1f")}
COHORT, POPULATION, SITES, SEXES = "C2017", "UM-HET3", ("TJL", "UM", "UT"), ("f", "m")
TWO = ("TJL", "UM")
DESIGN = {"Capt": ("180", "5"), "Control": ("0", None)}
GAIN, ALPHA = 0.02, 0.05
TABLE1 = {  # sex: (control count, median, p90), (capt count, median, % median, log-rank p, p90, % p90, Wang-Allison p)
    "f": ((276, 868, 1060), (132, 915, 5, "0.002", 1144, 8, "0.02")),
    "m": ((285, 718, 1029), (150, 821, 14, "0.001", 1097, 7, "0.01")),
}
SITE_TABLES = {  # (sex, site): (control count, median, p90), (capt count, median, % median, log-rank p, p90, % p90, W-A p)
    ("f", "TJL"): ((96, 871, 1068), (48, 960, 10, "0.0032", 1245, 17, "0.007")),
    ("f", "UM"): ((90, 902, 1094), (44, 890, -1, "0.93", 1086, -1, "0.99")),
    ("f", "UT"): ((90, 824, 979), (40, 872, 6, "0.02", 1053, 8, "0.11")),
    ("m", "TJL"): ((102, 748, 1079), (54, 827, 11, "0.24", 1081, 0, "0.79")),
    ("m", "UM"): ((88, 790, 1019), (45, 744, -6, "0.70", 1099, 8, "0.23")),
    ("m", "UT"): ((95, 676, 963), (51, 866, 28, "0.001", 1125, 17, "0.01")),
}
TWO_SITE = {"f": (4, "0.04", "0.06"), "m": (6, "< 0.26", None)}  # % median, log-rank p, Wang-Allison p
LIMIT = 200
OUTPUTS = ("rows", "females_3_sites", "gain_f3", "p_f3", "females_2_sites", "gain_f2", "p_f2", "males",
           "sites_f", "sites_m", "wang_allison", "p90_reading", "printed_values", "beside", "conditions_met",
           "conditions_total", "test_passed", "controls_passed", "controls_total")


class Refused(Exception):
    pass


def mice_from_rows(rows):
    """{(group, site, sex): [(age, died)]} for every group; every row checked against rule 1."""
    out = {}
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
        if g in DESIGN:
            design = (r.get("dose"), r.get("age_initiation") or None)
            if design != DESIGN[g]:
                raise Refused(f"row {i}: group {g} carries {design}, not {DESIGN[g]}")
        out.setdefault((g, r["site"], r["sex"]), []).append((int(float(age)), state[0] == "dead"))
    for g in DESIGN:
        for s in SITES:
            for x in SEXES:
                if (g, s, x) not in out:
                    raise Refused(f"no mice in group {g} at {s} of sex {x}")
    return out


def pooled(mice, group, sex, sites):
    return [m for s in sites for m in mice[(group, s, sex)]]


def dead(ms):
    return [t for t, d in ms if d]


def median_of_dead(ms):
    return statistics.median(dead(ms))


def logrank(mice, sex, sites, removed="censored"):
    def keep(ms):
        return ms if removed == "censored" else [m for m in ms if m[1]]
    return cana.logrank_strat_p([(keep(mice[("Control", s, sex)]), keep(mice[("Capt", s, sex)])) for s in sites])


def p90(ms, reading):
    a = dead(ms)
    return cana.p90_dead(a) if reading == "cana" else cana.quantile7(a, 0.9)


def wang_allison_p(mice, sex, sites):
    _, p = cana.wang_allison([(mice[("Control", s, sex)], mice[("Capt", s, sex)]) for s in sites])
    return p


def summary(mice, sex, sites, reading):
    c, t = pooled(mice, "Control", sex, sites), pooled(mice, "Capt", sex, sites)
    mc, mt = median_of_dead(c), median_of_dead(t)
    pc, pt = p90(c, reading), p90(t, reading)
    return {"n_control": len(dead(c)), "n_capt": len(dead(t)), "median_control": mc, "median_capt": mt,
            "gain": mt / mc - 1, "p": logrank(mice, sex, sites), "p90_control": pc, "p90_capt": pt,
            "p90_gain": pt / pc - 1, "wang_allison": wang_allison_p(mice, sex, sites),
            "p_removed_left_out": logrank(mice, sex, sites, removed="left out"),
            "mean_of_site_medians_gain": (sum(median_of_dead(mice[("Capt", s, sex)]) for s in sites)
                                          / sum(median_of_dead(mice[("Control", s, sex)]) for s in sites) - 1)}


def conditions(f3, f2):
    return {
        "three sites: females' median at least 2% above the controls'": f3["gain"] >= GAIN,
        "three sites: site-stratified log-rank p below 0.05": f3["p"] < ALPHA,
        "TJL and UM: females' median at least 2% above the controls'": f2["gain"] >= GAIN,
        "TJL and UM: site-stratified log-rank p below 0.05": f2["p"] < ALPHA,
    }


def pct(x):
    return cana.half_up(100 * x)


def p_as_printed(p, printed):
    if printed.startswith("<"):
        return p < float(printed[1:])
    decimals = len(printed.split(".")[1])
    return f"{p:.{decimals}f}" == printed or (float(printed) == 0.001 and p < 0.001)


def printed_rows(s, ctl_printed, capt_printed):
    """The printed numbers of one table row pair against a summary; [(what, ours, printed, equal)]."""
    nc, mc, pc = ctl_printed
    nt, mt, gm, pp, p9, g9, wa = capt_printed
    return [
        ("control dead", s["n_control"], nc, s["n_control"] == nc),
        ("control median", cana.half_up(s["median_control"]), mc, cana.half_up(s["median_control"]) == mc),
        ("control p90", cana.half_up(s["p90_control"]), pc, cana.half_up(s["p90_control"]) == pc),
        ("captopril dead", s["n_capt"], nt, s["n_capt"] == nt),
        ("captopril median", cana.half_up(s["median_capt"]), mt, cana.half_up(s["median_capt"]) == mt),
        ("% median", pct(s["gain"]), gm, pct(s["gain"]) == gm),
        ("log-rank p", f"{s['p']:.4f}", pp, p_as_printed(s["p"], pp)),
        ("captopril p90", cana.half_up(s["p90_capt"]), p9, cana.half_up(s["p90_capt"]) == p9),
        ("% p90", pct(s["p90_gain"]), g9, pct(s["p90_gain"]) == g9),
        ("Wang-Allison p", f"{s['wang_allison']:.4f}", wa, p_as_printed(s["wang_allison"], wa)),
    ]


def controls_known():
    a = [(1, True), (2, True)]
    b = [(3, True), (4, True)]
    lr = abs(cana.logrank_strat_p([(a, b)]) - math.erfc(math.sqrt(49 / 17 / 2))) < 1e-12
    same = abs(cana.logrank_strat_p([(a + b, a + b)]) - 1.0) < 1e-12
    fisher = abs(cana.fisher_two_sided([[3, 1], [1, 3]]) - 17 / 35) < 1e-12
    ages = [(t, True) for t in (5, 1, 4, 2, 3, 10, 6, 9, 8, 7)] + [(11, False)]
    hand = median_of_dead(ages) == 5.5 and cana.p90_dead(dead(ages)) == 9 and abs(
        cana.quantile7(dead(ages), 0.9) - 9.1) < 1e-12
    return {"the stratified log-rank test gives its hand answers": lr and same,
            "Fisher's exact test gives 17/35 for [[3, 1], [1, 3]]": fisher,
            "the median of the dead and the 90th percentile give their hand values": hand}


def p_text(p):
    return f"{p:.2g}" if p < 0.001 else f"{p:.4f}"


def line(s):
    return (f"{s['n_capt']} captopril against {s['n_control']} control dead: median {s['median_capt']:g} against "
            f"{s['median_control']:g} days ({100 * s['gain']:+.1f}%), log-rank p {p_text(s['p'])}")


def run(seed, inputs="inputs", results="results"):
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        raise Refused("the seed must be 64 hex characters")
    name, sha = INPUTS["C2017"]
    rows = rapa.read_rows(os.path.join(inputs, name), sha)
    mice = mice_from_rows(rows)

    # the 90th percentile reading that reproduces more of the printed pooled and site values
    def count_p90(reading):
        n = 0
        for sex in SEXES:
            s = summary(mice, sex, SITES, reading)
            n += (cana.half_up(s["p90_control"]) == TABLE1[sex][0][2]) + (cana.half_up(s["p90_capt"]) == TABLE1[sex][1][4])
            for site in SITES:
                t = summary(mice, sex, (site,), reading)
                n += (cana.half_up(t["p90_control"]) == SITE_TABLES[(sex, site)][0][2])
                n += (cana.half_up(t["p90_capt"]) == SITE_TABLES[(sex, site)][1][4])
        return n
    counts = {r: count_p90(r) for r in ("cana", "quantile7")}
    reading = "cana" if counts["cana"] >= counts["quantile7"] else "quantile7"

    S = {(sex, k): summary(mice, sex, sites, reading) for sex in SEXES
         for k, sites in (("3", SITES), ("2", TWO), ("TJL", ("TJL",)), ("UM", ("UM",)), ("UT", ("UT",)))}
    f3, f2 = S[("f", "3")], S[("f", "2")]
    cond = conditions(f3, f2)

    printed = []
    for sex in SEXES:
        for w, o, p, e in printed_rows(S[(sex, "3")], *TABLE1[sex]):
            printed.append({"what": f"{sex} three sites, {w}", "ours": o, "printed": p, "equal": bool(e)})
        for site in SITES:
            for w, o, p, e in printed_rows(S[(sex, site)], *SITE_TABLES[(sex, site)]):
                printed.append({"what": f"{sex} {site}, {w}", "ours": o, "printed": p, "equal": bool(e)})
        g, lp, wa = TWO_SITE[sex]
        s2 = S[(sex, "2")]
        printed.append({"what": f"{sex} TJL and UM, % median", "ours": pct(s2["gain"]), "printed": g,
                        "equal": pct(s2["gain"]) == g})
        printed.append({"what": f"{sex} TJL and UM, log-rank p", "ours": f"{s2['p']:.4f}", "printed": lp,
                        "equal": p_as_printed(s2["p"], lp)})
        if wa:
            printed.append({"what": f"{sex} TJL and UM, Wang-Allison p", "ours": f"{s2['wang_allison']:.4f}",
                            "printed": wa, "equal": p_as_printed(s2["wang_allison"], wa)})
    equal = sum(1 for x in printed if x["equal"])
    differs = [x for x in printed if not x["equal"]]
    controls = controls_known()

    def sites_line(sex):
        return "; ".join(f"{site} {S[(sex, site)]['median_capt']:g}/{S[(sex, site)]['median_control']:g} "
                         f"({100 * S[(sex, site)]['gain']:+.1f}%, p {p_text(S[(sex, site)]['p'])})" for site in SITES)

    m3, m2 = S[("m", "3")], S[("m", "2")]
    values = {
        "rows": f"{len(rows)} mice in the workbook; {sum(len(v) for k, v in mice.items() if k[0] in DESIGN)} captopril "
                f"or control",
        "females_3_sites": line(f3),
        "gain_f3": round(f3["gain"], 5), "p_f3": float(f"{f3['p']:.4g}"),
        "females_2_sites": line(f2),
        "gain_f2": round(f2["gain"], 5), "p_f2": float(f"{f2['p']:.4g}"),
        "males": (f"three sites {m3['median_capt']:g}/{m3['median_control']:g} ({100 * m3['gain']:+.1f}%, p "
                  f"{p_text(m3['p'])}); TJL and UM {m2['median_capt']:g}/{m2['median_control']:g} "
                  f"({100 * m2['gain']:+.1f}%, p {p_text(m2['p'])})"),
        "sites_f": sites_line("f"),
        "sites_m": sites_line("m"),
        "wang_allison": (f"females {p_text(f3['wang_allison'])} (three sites), {p_text(f2['wang_allison'])} (TJL and "
                         f"UM); males {p_text(m3['wang_allison'])}, {p_text(m2['wang_allison'])}"),
        "p90_reading": (f"{reading} ({counts['cana']} of 16 printed 90th percentiles by cana's, "
                        f"{counts['quantile7']} by R's quantile); female p90 gain {100 * f3['p90_gain']:+.1f}%"),
        "printed_values": (f"{equal} of {len(printed)} as printed"
                           + ("; not: " + ", ".join(x["what"] for x in differs) if differs else ""))[:LIMIT],
        "beside": (f"removed left out, females p {p_text(f3['p_removed_left_out'])} and "
                   f"{p_text(f2['p_removed_left_out'])}; mean of site medians, gains {100 * f3['mean_of_site_medians_gain']:+.1f}% "
                   f"and {100 * f2['mean_of_site_medians_gain']:+.1f}%"),
        "conditions_met": sum(cond.values()), "conditions_total": len(cond), "test_passed": int(all(cond.values())),
        "controls_passed": sum(controls.values()), "controls_total": len(controls),
    }
    out = {k: values[k] for k in OUTPUTS}
    for k, v in out.items():
        if isinstance(v, str) and len(v) > LIMIT:
            raise AssertionError(f"{k}: longer than {LIMIT} characters: {v}")
    detail = {"inputs": {k: {"name": n, "sha256": s} for k, (n, s) in INPUTS.items()}, "conditions": cond,
              "controls": controls, "p90_counts": counts, "reading": reading,
              "summaries": {f"{sex} {k}": v for (sex, k), v in S.items()}, "printed": printed}
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
    except (Refused, getattr(rapa, "Refused", Refused)) as e:
        sys.exit(f"capt2017: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
