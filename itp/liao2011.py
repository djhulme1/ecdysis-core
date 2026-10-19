"""Fat maintenance predicts the lifespan response to dietary restriction: Liao, Rikke, Johnson, Gelfond, Diaz & Nelson
(2011), checked on the per-mouse fat masses and lifespans its authors deposited in the Mouse Phenome Database.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:d8b3233ee52a175a) is from Liao, Rikke,
Johnson, Gelfond, Diaz and Nelson, "Fat maintenance is a predictor of the murine lifespan response to dietary
restriction", Aging Cell 10(4), 629-639 (2011), its abstract: "Across strains, DR life extension correlated inversely
with fat reduction, measured at midlife (males, r= -0.41, P<0.05, n=38 strains; females, r= -0.63, P<0.001, n=33
strains) and later ages."

The paper, read in its author manuscript (PMC3685291): ILSXISS recombinant inbred mice fed ad libitum (AL) or 60% of
their strain's AL intake (DR) from 2-5 months of age; fat and lean mass by quantitative magnetic resonance at 15-17
months ("38 strains for males, 33 for females"); "we defined fat reduction as the difference score between AL fat mass
and DR fat mass and compared this construct to the difference score defining lifespan extension (DR lifespan minus AL
lifespan) across all strains ... Fat reduction correlated inversely with lifespan extension in both males (r = -0.41,
P = 0.01) and females (r = -0.63, P = 0.0001)"; Fig. 4: "fat (or lean) reduction was measured by subtracting fat (or
lean) mass under DR from fat (or lean) mass under AL feeding for each strain. Y-axis: lifespan modulation was measured
by subtracting mean lifespan under AL from mean lifespan under DR (Liao et al., 2010a) ... Pearson correlation
coefficients (r) are all from 2-tailed tests"; "the lifespan data are the same as in Liao, et al., 2010a". The
authors' deposit, MPD project Nelson1 (which names both papers), holds one row per mouse: strain, sex, body weight,
lean mass, fat mass and percent fat at 65-74 weeks and the lifespan in days, each in the column of the mouse's diet.
It is the data of record of Liao et al. 2010 (ext:505a8e3d3548087b) too.

Rules, committed before any fat mass or lifespan in the file was summarised (its structure was read: 790 rows; in
males 41 strains, 38 with fat measured under both diets, 192 AL and 154 DR mice with fat; in females 39, 33, 187 and
135; every mouse with a fat mass has a lifespan, and every one of the 38 and 33 strains has at least 2 lifespans in
each diet):

1. Reading: the CSV's header must be exactly HEADER. A row's diet is AL when lifespan_AL holds a value and DR when
   lifespan_DR does (both or neither refuses the run). Its body composition (bw, lean, fat, pct_fat) may be given only
   in its own diet's columns, all four or none, each a positive decimal; a lifespan is a whole number of days; a sex
   is m or f. Anything else refuses the run as a reading error.
2. Strains: in each sex, those with a fat mass for at least one mouse in each diet. There must be 38 in males and 33
   in females, the paper's counts, or the run is refused as a reading error.
3. Per strain and sex: fat reduction = the mean fat mass of its AL mice with one, minus that of its DR mice;
   lifespan extension = the mean lifespan of all its DR mice, minus that of all its AL mice (Liao et al. 2010's means).
4. The test's conditions: across the strains of rule 2, the Pearson correlation of fat reduction with lifespan
   extension is negative with two-sided P below 0.05 in males, and negative with two-sided P below 0.001 in females
   (the abstract's thresholds). test_passed is 1 if both hold.

Beside the test, not counted: the two correlations against the printed r and P (-0.41 and 0.01; -0.63 and 0.0001);
the same with lifespan means over the mice with a fat mass only; with percent fat, and with the relative reduction
(AL - DR) / AL; lean reduction against lifespan extension ("did not correlate"); Table 1's twelve correlations of
strain mean lifespan with fat, lean mass and body weight (AL over every strain with an AL measure, 41 and 39 as
printed; DR over the 38 and 33) against the printed values and their stars; the overall reductions with strains equally
weighted (fat 38% and 33%, lean 17% and 21%), each both as one minus the ratio of the strains' mean masses and as the
mean of each strain's own reduction; the range of each strain's fat change (from an 80% reduction to a ~60% increase,
the increase in ILSXISS 3 in both sexes); the fold range of strain mean fat (AL 4.8 and 3.9, DR 6.2 and 6.3); the
share of strains whose lean mass fell significantly (74% and 79%) by the single-strain t-test (Student's; Welch's
beside); the correlation of DR with AL strain mean fat ("did not correlate"); the one-way ANOVA of fat on strain
(all P < 0.0001); and, of the strains whose lifespan DR lengthened significantly (Liao et al. 2010's t-tests, Student's
and Welch's), how many show a significant fat reduction ("none").

Controls (controls_passed of controls_total):
 (a) Plain Pearson correlations, t-tests and one-way ANOVAs (itp/liao2010.py's) against scipy's on every one computed,
     within 1e-9 relative (the p-values 1e-7).
 (b) The test's two correlations again in exact rational arithmetic from the file's decimal strings: the same sign and
     r within 1e-12.
 (c) The file as read: 790 rows; 41 and 39 strains; 38 and 33 with fat under both diets; 192, 154, 187 and 135 mice
     with fat.
 (d) Planted signs: every strain's DR fat set so that its fat reduction is minus its lifespan extension over 100 makes
     the conditions hold (r = -1), and plus it makes them fail (r = +1).

What it cannot check: the "later ages" of the abstract (fat at 20-22 months is not in the deposit), the QTL mapping, the
heritabilities, and body weight before 15 months.

Writes results/outputs.json (the values a receipt carries) and results/detail.json (every value computed).
Run with: python3 itp/liao2011.py (the pinned scipy-notebook image).
"""

import csv
import hashlib
import importlib.util
import io
import json
import math
import os
import re
import sys
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("itp_liao2010", os.path.join(HERE, "liao2010.py"))
L = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(L)

INPUT = L.INPUT
HEADER = L.HEADER
COMPOSITION = ("bw", "lean", "fat", "pct_fat")
COUNTS = {"m": 38, "f": 33}
ALPHA = {"m": 0.05, "f": 0.001}
ALPHA_STRAIN = 0.05
PRINTED = {
    "r": {"m": (-0.41, 0.01), "f": (-0.63, 0.0001)},
    "table1": {("AL", "m"): (41, 0.47, -0.19, 0.18), ("AL", "f"): (39, 0.46, -0.36, 0.11),
               ("DR", "m"): (38, 0.35, 0.43, 0.42), ("DR", "f"): (33, 0.47, 0.37, 0.51)},
    "fat_reduction_pct": {"m": 38, "f": 33},
    "lean_reduction_pct": {"m": 17, "f": 21},
    "fold_fat": {("AL", "m"): 4.8, ("AL", "f"): 3.9, ("DR", "m"): 6.2, ("DR", "f"): 6.3},
    "lean_significant_pct": {"m": 74, "f": 79},
}
TEST = ("Refuted if, in the authors' Mouse Phenome Database deposit (project Nelson1: per-mouse lifespans and QMR fat "
        "mass at 65-74 weeks under ad libitum feeding and 40% DR), across the strains with fat measured under both "
        "diets (38 male, 33 female), the Pearson correlation of fat reduction (the strain's mean AL fat minus its mean "
        "DR fat) with lifespan extension (its mean DR lifespan minus its mean AL lifespan, all its mice, as in Liao et "
        "al. 2010) is not negative with two-sided P < 0.05 in males and P < 0.001 in females.")
OUTPUTS = ("strains_m", "strains_f", "r_m", "p_m", "r_f", "p_f", "printed_r", "fat_measured_only", "pct_fat",
           "relative_reduction", "lean_reduction", "table1", "table1_match", "overall_reductions", "fat_change_range",
           "fold_range", "lean_significant", "dr_vs_al_fat", "anova", "lengthened_strains", "conditions_met",
           "conditions_total", "test_passed", "controls_passed", "controls_total")
LIMIT = 200


class Refused(Exception):
    pass


# ---------------------------------------------------------------- rule 1: reading

DECIMAL = re.compile(r"\d+(?:\.\d+)?")


def read_mice(data):
    """Rows as dicts: strain, sex, diet, lifespan (int), and comp {measure: (Fraction, float)} or None."""
    reader = csv.reader(io.StringIO(data.decode("utf-8")))
    header = next(reader)
    if header != HEADER:
        raise Refused(f"the header is not the committed one: {header}")
    mice = []
    for row in reader:
        if not row:
            continue
        rec = dict(zip(HEADER, row))
        if len(row) != len(HEADER):
            raise Refused(f"a row of {len(row)} fields: {row[:3]}")
        if rec["sex"] not in ("m", "f"):
            raise Refused(f"a sex other than m or f: {rec['sex']!r}")
        al, dr = rec["lifespan_AL"].strip(), rec["lifespan_DR"].strip()
        if bool(al) == bool(dr):
            raise Refused(f"mouse {rec['animal_id']}: lifespans in both diets or in neither")
        diet, other = ("AL", "DR") if al else ("DR", "AL")
        days = al or dr
        if not re.fullmatch(r"\d+", days):
            raise Refused(f"mouse {rec['animal_id']}: a lifespan that is not whole days: {days!r}")
        if any(rec[f"{m}_{other}"].strip() for m in COMPOSITION):
            raise Refused(f"mouse {rec['animal_id']}: body composition in the other diet's columns")
        vals = {m: rec[f"{m}_{diet}"].strip() for m in COMPOSITION}
        filled = [m for m in COMPOSITION if vals[m]]
        if filled and len(filled) != len(COMPOSITION):
            raise Refused(f"mouse {rec['animal_id']}: body composition partly given ({filled})")
        comp = None
        if filled:
            comp = {}
            for m in COMPOSITION:
                if not DECIMAL.fullmatch(vals[m]) or Fraction(vals[m]) <= 0:
                    raise Refused(f"mouse {rec['animal_id']}: {m} is not a positive decimal: {vals[m]!r}")
                comp[m] = (Fraction(vals[m]), float(vals[m]))
        mice.append({"strain": rec["strain"], "sex": rec["sex"], "diet": diet, "days": int(days), "comp": comp})
    return mice


def cells(mice):
    """{(strain, sex, diet): {"days": [...], measure: [(Fraction, float), ...]}}."""
    out = {}
    for m in mice:
        c = out.setdefault((m["strain"], m["sex"], m["diet"]), {"days": [], **{k: [] for k in COMPOSITION},
                                                                "days_measured": []})
        c["days"].append(m["days"])
        if m["comp"] is not None:
            for k in COMPOSITION:
                c[k].append(m["comp"][k])
            c["days_measured"].append(m["days"])
    return out


def strains_of(c, sex, need=("AL", "DR"), measure="fat"):
    """Rule 2: strains of a sex with the measure for at least one mouse in each diet named."""
    names = sorted({s for (s, x, d) in c if x == sex})
    return [s for s in names if all(len(c.get((s, sex, d), {}).get(measure, [])) >= 1 for d in need)]


# ---------------------------------------------------------------- rule 3: strain means and difference scores

def fmean(values):
    return sum(v[1] for v in values) / len(values)


def qmean(values):
    return sum((v[0] for v in values), Fraction(0)) / len(values)


def scores(c, sex, strains, measure="fat", relative=False, days_key="days"):
    """(reduction, extension) per strain, floats; reduction = mean AL - mean DR of the measure."""
    red, ext = [], []
    for s in strains:
        a, d = fmean(c[(s, sex, "AL")][measure]), fmean(c[(s, sex, "DR")][measure])
        red.append((a - d) / a if relative else a - d)
        ext.append(L.mean(c[(s, sex, "DR")][days_key]) - L.mean(c[(s, sex, "AL")][days_key]))
    return red, ext


def exact_r(c, sex, strains):
    """Rule 3's correlation in exact arithmetic: (sign, r squared as a Fraction, r as a float from it)."""
    red, ext = [], []
    for s in strains:
        red.append(qmean(c[(s, sex, "AL")]["fat"]) - qmean(c[(s, sex, "DR")]["fat"]))
        ext.append(Fraction(sum(c[(s, sex, "DR")]["days"]), len(c[(s, sex, "DR")]["days"]))
                   - Fraction(sum(c[(s, sex, "AL")]["days"]), len(c[(s, sex, "AL")]["days"])))
    n = len(red)
    mx, my = sum(red, Fraction(0)) / n, sum(ext, Fraction(0)) / n
    sxy = sum(((x - mx) * (y - my) for x, y in zip(red, ext)), Fraction(0))
    sxx = sum(((x - mx) ** 2 for x in red), Fraction(0))
    syy = sum(((y - my) ** 2 for y in ext), Fraction(0))
    r2 = sxy * sxy / (sxx * syy)
    sign = (sxy > 0) - (sxy < 0)
    return sign, r2, sign * math.sqrt(float(r2))


# ---------------------------------------------------------------- the run

def round_sig(x, d=4):
    if x == 0 or not math.isfinite(x):
        return x
    return float(f"{x:.{d}g}")


def assess(mice, counts=COUNTS):
    c = cells(mice)
    plog, tlog, alog = [], [], []

    def pear(x, y):
        r = L.scipy_pearson(x, y)
        plog.append((list(x), list(y), r))
        return r

    def ttest(a, b, eq=True):
        r = L.scipy_ttest(a, b, eq)
        tlog.append((list(a), list(b), eq, r))
        return r

    st = {sex: strains_of(c, sex) for sex in ("m", "f")}
    for sex in ("m", "f"):
        if counts is not None and len(st[sex]) != counts[sex]:
            raise Refused(f"{sex}: {len(st[sex])} strains with fat under both diets, not the paper's {counts[sex]}")
    main = {}
    for sex in ("m", "f"):
        red, ext = scores(c, sex, st[sex])
        r, p = pear(red, ext)
        main[sex] = {"n": len(red), "r": r, "p": p, "rows": [{"strain": s, "fat_reduction": a, "extension": b}
                                                              for s, a, b in zip(st[sex], red, ext)]}
    cond = {f"{sex}: r < 0 with two-sided P < {ALPHA[sex]}": main[sex]["r"] < 0 and main[sex]["p"] < ALPHA[sex]
            for sex in ("m", "f")}

    beside = {}
    for sex in ("m", "f"):
        red, ext = scores(c, sex, st[sex], days_key="days_measured")
        beside[("measured_only", sex)] = pear(red, ext)
        red, ext = scores(c, sex, st[sex], measure="pct_fat")
        beside[("pct_fat", sex)] = pear(red, ext)
        red, ext = scores(c, sex, st[sex], relative=True)
        beside[("relative", sex)] = pear(red, ext)
        red, ext = scores(c, sex, st[sex], measure="lean")
        beside[("lean", sex)] = pear(red, ext)
    table1 = {}
    for diet in ("AL", "DR"):
        for sex in ("m", "f"):
            sts = strains_of(c, sex, need=(diet,)) if diet == "AL" else st[sex]
            life = [L.mean(c[(s, sex, diet)]["days"]) for s in sts]
            row = [len(sts)]
            for measure in ("fat", "lean", "bw"):
                row.append(pear([fmean(c[(s, sex, diet)][measure]) for s in sts], life))
            table1[(diet, sex)] = row
    matches = 0
    for key, (n, *rs) in PRINTED["table1"].items():
        got = table1[key]
        for (r, p), pr in zip(got[1:], rs):
            matches += int(got[0] == n and round(r, 2) == pr)
    overall, change, fold, lean_sig, dr_al, anova = {}, {}, {}, {}, {}, {}
    for sex in ("m", "f"):
        for measure in ("fat", "lean"):
            al = [fmean(c[(s, sex, "AL")][measure]) for s in st[sex]]
            dr = [fmean(c[(s, sex, "DR")][measure]) for s in st[sex]]
            overall[(measure, sex)] = (100 * (1 - L.mean(dr) / L.mean(al)),
                                       100 * L.mean([(a - d) / a for a, d in zip(al, dr)]))
        al = [fmean(c[(s, sex, "AL")]["fat"]) for s in st[sex]]
        dr = [fmean(c[(s, sex, "DR")]["fat"]) for s in st[sex]]
        ch = [(100 * (d - a) / a, s) for a, d, s in zip(al, dr, st[sex])]
        change[sex] = (min(ch), max(ch))
        al_all = [fmean(c[(s, sex, "AL")]["fat"]) for s in strains_of(c, sex, need=("AL",))]
        fold[("AL", sex)] = (max(al) / min(al), max(al_all) / min(al_all))
        fold[("DR", sex)] = (max(dr) / min(dr), max(dr) / min(dr))
        dr_al[sex] = pear(dr, al)
        sig = {True: 0, False: 0}
        tested = 0
        for s in st[sex]:
            a = [v[1] for v in c[(s, sex, "AL")]["lean"]]
            d = [v[1] for v in c[(s, sex, "DR")]["lean"]]
            if len(a) >= 2 and len(d) >= 2:
                tested += 1
                for eq in (True, False):
                    t, p = ttest(d, a, eq)
                    sig[eq] += int(t < 0 and p < ALPHA_STRAIN)
        lean_sig[sex] = (tested, sig[True], sig[False])
        for diet in ("AL", "DR"):
            sts = strains_of(c, sex, need=(diet,))
            samples = [[v[1] for v in c[(s, sex, diet)]["fat"]] for s in sts if len(c[(s, sex, diet)]["fat"]) >= 1]
            fa = L.scipy_anova(samples)
            alog.append((samples, fa))
            anova[(diet, sex)] = fa
    lengthened = {}
    for eq in (True, False):
        rows = []
        for sex in ("m", "f"):
            names = sorted({s for (s, x, d) in c if x == sex})
            for s in names:
                al, dr = c.get((s, sex, "AL"), {}).get("days", []), c.get((s, sex, "DR"), {}).get("days", [])
                if len(al) < 2 or len(dr) < 2:
                    continue
                t, p = ttest(dr, al, eq)
                if t > 0 and p < ALPHA_STRAIN:
                    fa = [v[1] for v in c[(s, sex, "AL")]["fat"]]
                    fd = [v[1] for v in c[(s, sex, "DR")]["fat"]]
                    if len(fa) >= 2 and len(fd) >= 2:
                        tf, pf = ttest(fd, fa, True)
                        fat_cut = bool(tf < 0 and pf < ALPHA_STRAIN)
                    else:
                        fat_cut = None
                    rows.append({"strain": s, "sex": sex, "fat_cut": fat_cut})
        lengthened["student" if eq else "welch"] = rows

    # controls
    ctl = {}
    ok = True
    for x, y, (r, p) in plog:
        pr = L.plain_pearson(x, y)
        ok = ok and L.close(pr[0], r) and L.close(pr[1], p, 1e-7)
    for a, b, eq, (t, p) in tlog:
        pt, pp = L.plain_ttest(a, b, eq)
        ok = ok and L.close(pt, t) and L.close(pp, p, 1e-7)
    for samples, (f, p) in alog:
        pf = L.plain_anova(samples)
        ok = ok and L.close(pf[0], f) and (L.close(pf[1], p, 1e-7) or (pf[1] < 1e-300 and p < 1e-300))
    ctl["plain Pearson correlations, t-tests and ANOVAs against scipy's on every one computed"] = ok
    ok = True
    exact = {}
    for sex in ("m", "f"):
        sign, r2, r = exact_r(c, sex, st[sex])
        exact[sex] = r
        ok = ok and sign == (1 if main[sex]["r"] > 0 else -1) and abs(r - main[sex]["r"]) <= 1e-12
    ctl["the two correlations in exact rational arithmetic: the same sign and r within 1e-12"] = ok
    nfat = {(sex, d): sum(len(v["fat"]) for (s, x, dd), v in c.items() if x == sex and dd == d)
            for sex in ("m", "f") for d in ("AL", "DR")}
    nstr = {sex: len({s for (s, x, d) in c if x == sex}) for sex in ("m", "f")}
    ctl["the file as read: 790 rows; 41 and 39 strains; 38 and 33 with fat in both diets; 192, 154, 187 and 135 with fat"] = (
        len(mice) == 790 and nstr == {"m": 41, "f": 39} and len(st["m"]) == 38 and len(st["f"]) == 33
        and nfat == {("m", "AL"): 192, ("m", "DR"): 154, ("f", "AL"): 187, ("f", "DR"): 135})
    planted_ok = True
    for direction, want in ((-1, True), (1, False)):
        sub = []
        for m in mice:
            sub.append(dict(m))
        cc = cells(sub)
        held = []
        for sex in ("m", "f"):
            for s in st[sex]:
                ext = L.mean(cc[(s, sex, "DR")]["days"]) - L.mean(cc[(s, sex, "AL")]["days"])
                target = fmean(cc[(s, sex, "AL")]["fat"]) - direction * ext / 100.0
                cc[(s, sex, "DR")]["fat"] = [(Fraction(0), target)]
            red, ext = scores(cc, sex, st[sex])
            r, p = L.scipy_pearson(red, ext)
            held.append(r < 0 and p < ALPHA[sex] and abs(abs(r) - 1) < 1e-9)
        planted_ok = planted_ok and (all(held) == want)
    ctl["planted signs: reduction = -extension/100 holds both conditions, +extension/100 neither"] = planted_ok

    def f2(x):
        return f"{x:.2f}"

    t1 = "; ".join(f"{d} {s} n={table1[(d, s)][0]}: " + ", ".join(f2(r) for r, p in table1[(d, s)][1:])
                   for d in ("AL", "DR") for s in ("m", "f"))
    values = {
        "strains_m": main["m"]["n"], "strains_f": main["f"]["n"],
        "r_m": round_sig(main["m"]["r"]), "p_m": round_sig(main["m"]["p"]),
        "r_f": round_sig(main["f"]["r"]), "p_f": round_sig(main["f"]["p"]),
        "printed_r": (f"printed: males r {PRINTED['r']['m'][0]}, P {PRINTED['r']['m'][1]}; females r "
                      f"{PRINTED['r']['f'][0]}, P {PRINTED['r']['f'][1]}; computed {f2(main['m']['r'])} "
                      f"({main['m']['p']:.2g}) and {f2(main['f']['r'])} ({main['f']['p']:.2g})"),
        "fat_measured_only": ("lifespans of the mice with fat only: males r " + f2(beside[("measured_only", "m")][0])
                              + f" (P {beside[('measured_only', 'm')][1]:.2g}), females "
                              + f2(beside[("measured_only", "f")][0]) + f" (P {beside[('measured_only', 'f')][1]:.2g})"),
        "pct_fat": (f"percent fat: males r {f2(beside[('pct_fat', 'm')][0])} (P {beside[('pct_fat', 'm')][1]:.2g}), "
                    f"females {f2(beside[('pct_fat', 'f')][0])} (P {beside[('pct_fat', 'f')][1]:.2g})"),
        "relative_reduction": (f"(AL - DR)/AL: males r {f2(beside[('relative', 'm')][0])} (P "
                               f"{beside[('relative', 'm')][1]:.2g}), females {f2(beside[('relative', 'f')][0])} (P "
                               f"{beside[('relative', 'f')][1]:.2g})"),
        "lean_reduction": (f"lean reduction: males r {f2(beside[('lean', 'm')][0])} (P {beside[('lean', 'm')][1]:.2g}), "
                           f"females {f2(beside[('lean', 'f')][0])} (P {beside[('lean', 'f')][1]:.2g})"),
        "table1": t1,
        "table1_match": matches,
        "overall_reductions": "; ".join(f"{m} {s} {overall[(m, s)][0]:.1f}% / {overall[(m, s)][1]:.1f}%"
                                        for m in ("fat", "lean") for s in ("m", "f")) + " (printed 38, 33, 17, 21)",
        "fat_change_range": "; ".join(f"{s} {change[s][0][0]:.0f}% ({change[s][0][1]}) to {change[s][1][0]:.0f}% "
                                      f"({change[s][1][1]})" for s in ("m", "f")).replace("/TejJ", ""),
        "fold_range": "; ".join(f"{d} {s} {fold[(d, s)][0]:.1f}" + (f" ({fold[(d, s)][1]:.1f} over all)" if d == "AL"
                                                                     else "") for d in ("AL", "DR") for s in ("m", "f"))
                      + " (printed 4.8, 3.9, 6.2, 6.3)",
        "lean_significant": "; ".join(f"{s} {lean_sig[s][1]} of {lean_sig[s][0]} ({100 * lean_sig[s][1] / lean_sig[s][0]:.0f}%"
                                      f", Welch {lean_sig[s][2]})" for s in ("m", "f")) + " (printed 74%, 79%)",
        "dr_vs_al_fat": (f"DR against AL strain fat: males r {f2(dr_al['m'][0])} (P {dr_al['m'][1]:.2g}), females "
                         f"{f2(dr_al['f'][0])} (P {dr_al['f'][1]:.2g})"),
        "anova": "; ".join(f"{d} {s} P {anova[(d, s)][1]:.1e}" for d in ("AL", "DR") for s in ("m", "f")),
        "lengthened_strains": "; ".join(
            f"{k}: {len(v)} lengthened, {sum(1 for r in v if r['fat_cut'])} with a significant fat cut, "
            f"{sum(1 for r in v if r['fat_cut'] is None)} untestable" for k, v in lengthened.items()),
        "conditions_met": sum(cond.values()), "conditions_total": len(cond), "test_passed": int(all(cond.values())),
        "controls_passed": sum(ctl.values()), "controls_total": len(ctl),
    }
    out = {k: values[k] for k in OUTPUTS}
    for key, v in out.items():
        if isinstance(v, str) and len(v) > LIMIT:
            raise AssertionError(f"{key}: longer than {LIMIT} characters: {v}")
    detail = {"conditions": cond, "controls": ctl, "main": main, "exact_r": exact,
              "beside": {f"{a}/{b}": v for (a, b), v in beside.items()},
              "table1": {f"{d}/{s}": v for (d, s), v in table1.items()},
              "overall": {f"{m}/{s}": v for (m, s), v in overall.items()}, "change": change,
              "fold": {f"{d}/{s}": v for (d, s), v in fold.items()}, "lean_significant": lean_sig,
              "dr_vs_al_fat": dr_al, "anova": {f"{d}/{s}": v for (d, s), v in anova.items()},
              "lengthened": lengthened, "printed": {k: {str(kk): vv for kk, vv in v.items()} for k, v in PRINTED.items()}}
    return out, detail


def read_input(inputs):
    name, sha, size = INPUT
    with open(os.path.join(inputs, name), "rb") as fh:
        data = fh.read()
    got = hashlib.sha256(data).hexdigest()
    if got != sha or len(data) != size:
        raise Refused(f"{name}: sha256 {got} ({len(data)} bytes), not the registered {sha} ({size})")
    return data


def run(inputs="inputs", results="results"):
    mice = read_mice(read_input(inputs))
    out, detail = assess(mice)
    detail["input"] = {"name": INPUT[0], "sha256": INPUT[1], "bytes": INPUT[2]}
    os.makedirs(results, exist_ok=True)
    with open(os.path.join(results, "outputs.json"), "w", encoding="ascii") as fh:
        json.dump(out, fh, indent=2, sort_keys=True)
        fh.write("\n")
    with open(os.path.join(results, "detail.json"), "w", encoding="ascii") as fh:
        json.dump(detail, fh, indent=1, sort_keys=True, default=str)
        fh.write("\n")
    return out, detail


def main():
    try:
        out, _ = run()
    except Refused as e:
        sys.exit(f"liao2011: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
