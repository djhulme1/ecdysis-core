"""Dietary restriction shortened lifespan in more mouse strains than it lengthened it: Liao, Rikke, Johnson, Diaz &
Nelson (2010), checked on the per-mouse lifespans its authors deposited in the Mouse Phenome Database.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:505a8e3d3548087b) is from Liao, Rikke,
Johnson, Diaz and Nelson, "Genetic variation in the murine lifespan response to dietary restriction: from life
extension to life shortening", Aging Cell 9(1), 92-95 (2010), its abstract: "Notably, DR shortened lifespan in more
strains than those in which it lengthened life." The paper, read in its author manuscript (PMC3476836): 41 ILSXISS
recombinant inbred strains, mice fed ad libitum (AL) or 60% of their strain's AL intake (DR) from 2-5 months of age,
"typically ... 5 males & 5 females per treatment group"; Figure 1 ranks 41 strains in males and 39 in females, its
asterisks "p < 0.05 ... by t-test (no experiment-wise Bonferroni correction)"; the Results: "Only 5% of the strains for
males and 21% of the strains for females showed statistically significant life extension under DR, using single
strain p values < 0.05. DR shortened lifespan in more strains (27% and 26%; males and females, respectively;
p < 0.05 - 0.001)." The authors' deposit, MPD project Nelson1 (which names this paper), holds one row per mouse with
its strain, sex and age at death in days in the column of its diet (lifespan_AL or lifespan_DR).

Rules, committed before any lifespan in the file was summarised (its structure was read: 790 rows, 44 strains, 402
males and 388 females, every row one lifespan; 41 strains with at least 2 mice in each diet group in males, 39 in
females, the paper's counts):

1. Reading: the CSV's header must be exactly HEADER; a row's diet is AL when lifespan_AL holds a value and DR when
   lifespan_DR does (a row with both or neither is refused, as is a lifespan that is not a whole number of days or a
   sex other than m or f).
2. Strains: in each sex, those with at least 2 lifespans in each diet group.
3. Per strain and sex, the paper's single-strain t-test: Student's two-sample t-test (pooled variance, two-sided;
   scipy.stats.ttest_ind with equal_var=True) of DR against AL lifespans. A strain is lengthened when its DR mean
   exceeds its AL mean with p < 0.05, and shortened when its DR mean is below its AL mean with p < 0.05.
4. The test's conditions, one per sex: more strains shortened than lengthened. The test passes when both hold.

Beside the test, not counted: the same counts with Welch's t-test (the text says only "t-test"); with the sexes pooled
(Supplementary Fig. S2: "doubling sample size by combining the two sexes"); with deaths before 365 days left out
(Supplementary Fig. S3: "exclusion of deaths occurring before 12 months of age"); each count's percentage against the
printed ones (5% and 27% in males, 21% and 26% in females); the ranges of strain mean lifespans against the printed
ones (AL: 504 to 1152 days in males, 407 to 1208 in females; DR: 217 to 1215 and 113 to 1225); the correlations the
text prints between strain means (males against females under AL, r = 0.50, p = 0.002, and DR, r = 0.42, p = 0.012;
DR against AL, Table 1: r = 0.09, p = 0.56 in males, r = -0.03, p = 0.86 in females; maximum against mean lifespan,
r = 0.81, 0.82, 0.92 and 0.94 for AL males, AL females, DR males and DR females); the five longest-lived strains'
average mean lifespan (DR: 1103 +/- 40 and 1108 +/- 32 days in males and females; AL: 1098 +/- 20 and 1088 +/- 31),
with the SEM and the SD of the five; and the one-way ANOVA of lifespan on strain in each sex and diet (printed
p < 1e-6).

Controls (controls_passed of controls_total):
 (a) A plain t-test (Student's and Welch's, the p-value from the regularised incomplete beta function) against scipy's
     on every strain comparison computed and on sets made here, within 1e-9 (relative).
 (b) A plain Pearson correlation and a plain one-way ANOVA against scipy's pearsonr and f_oneway on every one computed.
 (c) The file as read: 790 rows, 44 strains, 402 males and 388 females, every row one diet; 41 and 39 strains in the
     analysis.
 (d) Planted strains: one whose DR mice live 300 days less is counted shortened, one whose DR mice live 300 days more
     lengthened, and one with the same lifespans in both groups neither.

Writes results/outputs.json (the values a receipt carries) and results/detail.json (every value computed).
Run with: python3 itp/liao2010.py (the pinned scipy-notebook image).
"""

import csv
import hashlib
import io
import json
import math
import os
import re
import sys

INPUT = ("Nelson1_animaldata.csv", "a3d57bfd20502b51e7a95c1839c0881e18b8e02e23450459430cda4dadc53da3", 42453)
HEADER = ["strain", "sex", "animal_id", "bw_AL", "bw_DR", "lean_AL", "lean_DR", "fat_AL", "fat_DR", "pct_fat_AL",
          "pct_fat_DR", "lifespan_AL", "lifespan_DR"]
ALPHA = 0.05
MIN_PER_GROUP = 2
EARLY_DAYS = 365
PRINTED = {
    "pct": {"m": (5, 27), "f": (21, 26)},                            # (lengthened, shortened), percent of strains
    "range_AL": {"m": (504, 1152), "f": (407, 1208)},
    "range_DR": {"m": (217, 1215), "f": (113, 1225)},
    "r_sexes": {"AL": (0.50, 0.002), "DR": (0.42, 0.012)},
    "r_al_dr": {"m": (0.09, 0.56), "f": (-0.03, 0.86)},
    "r_max_mean": {("AL", "m"): 0.81, ("AL", "f"): 0.82, ("DR", "m"): 0.92, ("DR", "f"): 0.94},
    "top5": {("DR", "m"): (1103, 40), ("DR", "f"): (1108, 32), ("AL", "m"): (1098, 20), ("AL", "f"): (1088, 31)},
}
TEST = ("Refuted if, in the authors' per-mouse lifespans (MPD project Nelson1), comparing DR with AL strain by strain "
        "with the paper's single-strain t-test (Student's, two-sided, p < 0.05) among strains with at least 2 mice in "
        "each diet group (41 in males, 39 in females), the strains in which DR significantly shortened mean lifespan "
        "are not more than those in which it significantly lengthened it, in males or in females.")
OUTPUTS = ("strains_m", "strains_f", "m_lengthened", "m_shortened", "f_lengthened", "f_shortened", "printed_pct",
           "welch", "sexes_pooled", "early_deaths_out", "ranges", "r_sexes", "r_al_dr", "r_max_mean", "top5",
           "anova", "conditions_met", "conditions_total", "test_passed", "controls_passed", "controls_total")


class Refused(Exception):
    pass


# ---------------------------------------------------------------- rule 1: reading

def read_mice(data):
    """Rows as (strain, sex, diet, lifespan in days)."""
    text = data.decode("utf-8")
    reader = csv.reader(io.StringIO(text))
    header = next(reader)
    if header != HEADER:
        raise Refused(f"the header is not the committed one: {header}")
    mice = []
    for row in reader:
        if not row:
            continue
        rec = dict(zip(HEADER, row))
        if rec["sex"] not in ("m", "f"):
            raise Refused(f"a sex other than m or f: {rec['sex']!r}")
        al, dr = rec["lifespan_AL"].strip(), rec["lifespan_DR"].strip()
        if bool(al) == bool(dr):
            raise Refused(f"mouse {rec['animal_id']}: lifespans in both diets or in neither")
        value = al or dr
        if not re.fullmatch(r"\d+", value):
            raise Refused(f"mouse {rec['animal_id']}: a lifespan that is not whole days: {value!r}")
        mice.append((rec["strain"], rec["sex"], "AL" if al else "DR", int(value)))
    return mice


def groups(mice, min_days=0):
    """{(strain, sex): {"AL": [...], "DR": [...]}} with lifespans of at least min_days."""
    g = {}
    for strain, sex, diet, days in mice:
        if days >= min_days:
            g.setdefault((strain, sex), {"AL": [], "DR": []})[diet].append(days)
    return g


# ---------------------------------------------------------------- statistics: scipy and plain

def betacf(a, b, x):
    """Continued fraction for the incomplete beta function (Lentz's method)."""
    tiny, eps = 1e-300, 1e-16
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c, d = 1.0, 1.0 - qab * x / qap
    d = 1.0 / (d if abs(d) > tiny else tiny)
    h = d
    for m in range(1, 10000):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        d = 1.0 / (d if abs(d) > tiny else tiny)
        c = 1.0 + aa / c
        c = c if abs(c) > tiny else tiny
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        d = 1.0 / (d if abs(d) > tiny else tiny)
        c = 1.0 + aa / c
        c = c if abs(c) > tiny else tiny
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < eps:
            return h
    raise ArithmeticError("betacf did not converge")


def betainc(a, b, x):
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    lbt = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log1p(-x)
    if x < (a + 1) / (a + b + 2):
        return math.exp(lbt) * betacf(a, b, x) / a
    return 1.0 - math.exp(lbt) * betacf(b, a, 1 - x) / b


def t_two_sided(t, df):
    return betainc(df / 2, 0.5, df / (df + t * t)) if df > 0 else float("nan")


def mean(x):
    return sum(x) / len(x)


def var(x):
    m = mean(x)
    return sum((v - m) ** 2 for v in x) / (len(x) - 1)


def plain_ttest(a, b, equal_var=True):
    """t and two-sided p of mean(a) - mean(b)."""
    na, nb = len(a), len(b)
    va, vb = var(a), var(b)
    if equal_var:
        df = na + nb - 2
        sp = ((na - 1) * va + (nb - 1) * vb) / df
        se = math.sqrt(sp * (1 / na + 1 / nb))
    else:
        se = math.sqrt(va / na + vb / nb)
        df = (va / na + vb / nb) ** 2 / ((va / na) ** 2 / (na - 1) + (vb / nb) ** 2 / (nb - 1))
    if se == 0:
        return (0.0, 1.0) if mean(a) == mean(b) else (math.copysign(math.inf, mean(a) - mean(b)), 0.0)
    t = (mean(a) - mean(b)) / se
    return t, t_two_sided(t, df)


def scipy_ttest(a, b, equal_var=True):
    from scipy.stats import ttest_ind
    r = ttest_ind(a, b, equal_var=equal_var)
    return float(r.statistic), float(r.pvalue)


def plain_pearson(x, y):
    mx, my = mean(x), mean(y)
    sxx = sum((v - mx) ** 2 for v in x)
    syy = sum((v - my) ** 2 for v in y)
    sxy = sum((u - mx) * (v - my) for u, v in zip(x, y))
    r = sxy / math.sqrt(sxx * syy)
    df = len(x) - 2
    t2 = r * r * df / max(1e-300, (1 - r) * (1 + r))
    return r, betainc(df / 2, 0.5, df / (df + t2))


def scipy_pearson(x, y):
    from scipy.stats import pearsonr
    r = pearsonr(x, y)
    return float(r.statistic), float(r.pvalue)


def plain_anova(samples):
    allv = [v for s in samples for v in s]
    gm = mean(allv)
    ssb = sum(len(s) * (mean(s) - gm) ** 2 for s in samples)
    ssw = sum(sum((v - mean(s)) ** 2 for v in s) for s in samples)
    d1, d2 = len(samples) - 1, len(allv) - len(samples)
    f = (ssb / d1) / (ssw / d2)
    return f, betainc(d2 / 2, d1 / 2, d2 / (d2 + d1 * f))


def scipy_anova(samples):
    from scipy.stats import f_oneway
    r = f_oneway(*samples)
    return float(r.statistic), float(r.pvalue)


def close(a, b, rel=1e-9):
    if math.isinf(a) or math.isinf(b):
        return a == b
    return abs(a - b) <= rel * max(abs(a), abs(b), 1e-300)


# ---------------------------------------------------------------- rules 2 and 3: the counts

def classify(g, sexes=("m", "f"), equal_var=True, pooled=False, log=None):
    """Per sex (or pooled): strains in the analysis, lengthened and shortened, and each comparison."""
    out = {}
    keys = ("both",) if pooled else sexes
    for key in keys:
        strains = sorted({s for (s, x) in g})
        rows = []
        for s in strains:
            if pooled:
                al = g.get((s, "m"), {"AL": []})["AL"] + g.get((s, "f"), {"AL": []})["AL"]
                dr = g.get((s, "m"), {"DR": []})["DR"] + g.get((s, "f"), {"DR": []})["DR"]
            else:
                if (s, key) not in g:
                    continue
                al, dr = g[(s, key)]["AL"], g[(s, key)]["DR"]
            if len(al) < MIN_PER_GROUP or len(dr) < MIN_PER_GROUP:
                continue
            t, p = scipy_ttest(dr, al, equal_var)
            if log is not None:
                log.append((dr, al, equal_var, t, p))
            diff = mean(dr) - mean(al)
            verdict = "lengthened" if (diff > 0 and p < ALPHA) else ("shortened" if (diff < 0 and p < ALPHA) else "")
            rows.append({"strain": s, "n_AL": len(al), "n_DR": len(dr), "mean_AL": mean(al), "mean_DR": mean(dr),
                         "t": t, "p": p, "verdict": verdict})
        out[key] = {"strains": len(rows), "lengthened": sum(r["verdict"] == "lengthened" for r in rows),
                    "shortened": sum(r["verdict"] == "shortened" for r in rows), "rows": rows}
    return out


def analysed_strains(g, sex):
    return sorted(s for (s, x), v in g.items() if x == sex and len(v["AL"]) >= MIN_PER_GROUP
                  and len(v["DR"]) >= MIN_PER_GROUP)


# ---------------------------------------------------------------- the run

def assess(mice):
    g = groups(mice)
    tlog = []
    main = classify(g, log=tlog)
    welch = classify(g, equal_var=False, log=tlog)
    pooled = classify(g, pooled=True, log=tlog)["both"]
    early = classify(groups(mice, min_days=EARLY_DAYS), log=tlog)
    cond = {f"{sex}: more strains shortened than lengthened": main[sex]["shortened"] > main[sex]["lengthened"]
            for sex in ("m", "f")}

    # beside: ranges, correlations, top five, ANOVA (over each sex's analysed strains)
    plog, alog = [], []
    detail_b = {}
    ranges, r_al_dr, r_max, top5, anova = {}, {}, {}, {}, {}
    for sex in ("m", "f"):
        st = analysed_strains(g, sex)
        for diet in ("AL", "DR"):
            means = [mean(g[(s, sex)][diet]) for s in st]
            maxes = [max(g[(s, sex)][diet]) for s in st]
            ranges[(diet, sex)] = (min(means), max(means))
            r = scipy_pearson(maxes, means)
            plog.append((maxes, means, r))
            r_max[(diet, sex)] = r
            best = sorted(means, reverse=True)[:5]
            m5 = mean(best)
            sd5 = math.sqrt(var(best))
            top5[(diet, sex)] = (m5, sd5 / math.sqrt(5), sd5)
            samples = [g[(s, sex)][diet] for s in st]
            fa = scipy_anova(samples)
            alog.append((samples, fa))
            anova[(diet, sex)] = fa
        al = [mean(g[(s, sex)]["AL"]) for s in st]
        dr = [mean(g[(s, sex)]["DR"]) for s in st]
        r = scipy_pearson(dr, al)
        plog.append((dr, al, r))
        r_al_dr[sex] = r
    r_sexes = {}
    for diet in ("AL", "DR"):
        both = sorted(set(analysed_strains(g, "m")) & set(analysed_strains(g, "f")))
        xm = [mean(g[(s, "m")][diet]) for s in both]
        xf = [mean(g[(s, "f")][diet]) for s in both]
        r = scipy_pearson(xm, xf)
        plog.append((xm, xf, r))
        r_sexes[diet] = (r[0], r[1], len(both))

    # controls
    ctl = {}
    ok = True
    for dr, al, eq, t, p in tlog:
        pt, pp = plain_ttest(dr, al, eq)
        ok = ok and close(pt, t) and close(pp, p)
    for a, b in (([1, 2, 3, 4], [2, 3, 5, 9]), ([10.5, 11, 9, 12, 13], [3, 4]), ([500, 610, 720], [400, 300, 350, 999])):
        for eq in (True, False):
            pt, pp = plain_ttest(a, b, eq)
            st, sp = scipy_ttest(a, b, eq)
            ok = ok and close(pt, st) and close(pp, sp)
    ctl["plain t-tests (Student's and Welch's) against scipy's on every comparison and three made-up pairs"] = ok
    ok = True
    for x, y, r in plog:
        pr = plain_pearson(x, y)
        ok = ok and close(pr[0], r[0]) and close(pr[1], r[1], 1e-7)
    for samples, fa in alog:
        pf = plain_anova(samples)
        ok = ok and close(pf[0], fa[0]) and (close(pf[1], fa[1], 1e-7) or (pf[1] < 1e-300 and fa[1] < 1e-300))
    ctl["plain Pearson correlations and one-way ANOVAs against scipy's on every one computed"] = ok
    nstr = len({m[0] for m in mice})
    ctl["the file as read: 790 rows, 44 strains, 402 males and 388 females; 41 and 39 strains analysed"] = (
        len(mice) == 790 and nstr == 44 and sum(m[1] == "m" for m in mice) == 402
        and sum(m[1] == "f" for m in mice) == 388 and main["m"]["strains"] == 41 and main["f"]["strains"] == 39)
    planted = [("P-short", "m", "AL", d) for d in (900, 950, 1000, 1050, 980)] + \
              [("P-short", "m", "DR", d - 300) for d in (900, 950, 1000, 1050, 980)] + \
              [("P-long", "m", "AL", d) for d in (600, 650, 700, 640, 690)] + \
              [("P-long", "m", "DR", d + 300) for d in (600, 650, 700, 640, 690)] + \
              [("P-same", "m", "AL", d) for d in (800, 820, 860)] + [("P-same", "m", "DR", d) for d in (800, 820, 860)]
    pc = classify(groups(planted), sexes=("m",))["m"]
    verdicts = {r["strain"]: r["verdict"] for r in pc["rows"]}
    ctl["planted strains: 300 days less counted shortened, 300 more lengthened, the same neither"] = (
        verdicts == {"P-short": "shortened", "P-long": "lengthened", "P-same": ""})

    def pct(k, n):
        return round(100 * k / n) if n else -1

    pr = PRINTED
    values = {
        "strains_m": main["m"]["strains"], "strains_f": main["f"]["strains"],
        "m_lengthened": main["m"]["lengthened"], "m_shortened": main["m"]["shortened"],
        "f_lengthened": main["f"]["lengthened"], "f_shortened": main["f"]["shortened"],
        "printed_pct": (f"males lengthened {pct(main['m']['lengthened'], main['m']['strains'])}% (printed "
                        f"{pr['pct']['m'][0]}%), shortened {pct(main['m']['shortened'], main['m']['strains'])}% "
                        f"({pr['pct']['m'][1]}%); females {pct(main['f']['lengthened'], main['f']['strains'])}% "
                        f"({pr['pct']['f'][0]}%), {pct(main['f']['shortened'], main['f']['strains'])}% "
                        f"({pr['pct']['f'][1]}%)"),
        "welch": (f"Welch: males {welch['m']['lengthened']} lengthened, {welch['m']['shortened']} shortened of "
                  f"{welch['m']['strains']}; females {welch['f']['lengthened']}, {welch['f']['shortened']} of "
                  f"{welch['f']['strains']}"),
        "sexes_pooled": (f"sexes pooled: {pooled['lengthened']} lengthened, {pooled['shortened']} shortened of "
                         f"{pooled['strains']} strains"),
        "early_deaths_out": (f"deaths before {EARLY_DAYS} days left out: males {early['m']['lengthened']} lengthened, "
                             f"{early['m']['shortened']} shortened of {early['m']['strains']}; females "
                             f"{early['f']['lengthened']}, {early['f']['shortened']} of {early['f']['strains']}"),
        "ranges": "; ".join(f"{d} {s} {ranges[(d, s)][0]:.0f}-{ranges[(d, s)][1]:.0f} (printed "
                            f"{pr['range_' + d][s][0]}-{pr['range_' + d][s][1]})"
                            for d in ("AL", "DR") for s in ("m", "f")),
        "r_sexes": "; ".join(f"{d} r {r_sexes[d][0]:.2f} p {r_sexes[d][1]:.2g} over {r_sexes[d][2]} (printed "
                             f"{pr['r_sexes'][d][0]:.2f}, {pr['r_sexes'][d][1]:g})" for d in ("AL", "DR")),
        "r_al_dr": "; ".join(f"{s} r {r_al_dr[s][0]:.2f} p {r_al_dr[s][1]:.2f} (printed {pr['r_al_dr'][s][0]:.2f}, "
                             f"{pr['r_al_dr'][s][1]:.2f})" for s in ("m", "f")),
        "r_max_mean": "; ".join(f"{d} {s} {r_max[(d, s)][0]:.2f} ({pr['r_max_mean'][(d, s)]:.2f})"
                                for d in ("AL", "DR") for s in ("m", "f")),
        "top5": "; ".join(f"{d} {s} {top5[(d, s)][0]:.0f} sem {top5[(d, s)][1]:.0f} sd {top5[(d, s)][2]:.0f} "
                          f"({pr['top5'][(d, s)][0]} +/- {pr['top5'][(d, s)][1]})"
                          for d in ("DR", "AL") for s in ("m", "f")),
        "anova": "; ".join(f"{d} {s} p {anova[(d, s)][1]:.1e}" for d in ("AL", "DR") for s in ("m", "f")),
        "conditions_met": sum(cond.values()), "conditions_total": len(cond),
        "test_passed": int(all(cond.values())), "controls_passed": sum(ctl.values()), "controls_total": len(ctl),
    }
    out = {k: values[k] for k in OUTPUTS}
    for k, v in out.items():
        if isinstance(v, str) and len(v) > 200:
            raise AssertionError(f"{k}: longer than 200 characters: {v}")
    detail = {"test": TEST, "conditions": cond, "controls": ctl,
              "student": {k: v for k, v in main.items()}, "welch": welch, "pooled": pooled, "early_out": early,
              "ranges": {f"{d}_{s}": v for (d, s), v in ranges.items()},
              "r_sexes": r_sexes, "r_al_dr": r_al_dr, "r_max_mean": {f"{d}_{s}": v for (d, s), v in r_max.items()},
              "top5": {f"{d}_{s}": v for (d, s), v in top5.items()},
              "anova": {f"{d}_{s}": v for (d, s), v in anova.items()},
              "printed": {k: {("_".join(kk) if isinstance(kk, tuple) else kk): vv for kk, vv in val.items()}
                          for k, val in PRINTED.items()}}
    return out, detail


def run(seed, inputs="inputs", results="results"):
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        raise Refused("the seed must be 64 hex characters")
    path = os.path.join(inputs, INPUT[0])
    with open(path, "rb") as fh:
        data = fh.read()
    if hashlib.sha256(data).hexdigest() != INPUT[1] or len(data) != INPUT[2]:
        raise Refused(f"{INPUT[0]} is not the committed file")
    out, detail = assess(read_mice(data))
    os.makedirs(results, exist_ok=True)
    with open(os.path.join(results, "outputs.json"), "w", encoding="ascii") as fh:
        json.dump(out, fh, indent=2, sort_keys=True)
        fh.write("\n")
    with open(os.path.join(results, "detail.json"), "w", encoding="utf-8") as fh:
        json.dump(detail, fh, indent=1, sort_keys=True, default=str)
        fh.write("\n")
    return out, detail


def main():
    seed = os.environ.get("ECDYSIS_SEED", "")
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        sys.exit("ECDYSIS_SEED must be the 64-hex seed the archive issued")
    try:
        out, _ = run(seed)
    except Refused as e:
        sys.exit(f"liao2010: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
