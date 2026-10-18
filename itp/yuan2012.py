"""Later sexual maturation goes with longer life among inbred mouse strains of normal lifespan, and lower IGF1 with
later maturation: Yuan, Meng, Nautiyal, Flurkey, Tsaih, Krier, Parker, Harrison & Paigen (2012), checked on the
per-mouse data its authors deposited in the Mouse Phenome Database.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:8dcf7c6a224abf35) is from Yuan et al.,
"Genetic coregulation of age of female sexual maturation and lifespan through circulating IGF1 among inbred mouse
strains", Proc. Natl Acad. Sci. USA 109(21), 8224-8229 (2012), its abstract: "Here we report that strains with lower
IGF1 have significantly delayed age of female sexual maturation, measured by vaginal patency (VP). Among strains with
normal lifespans (mean lifespan >600 d), delayed age of VP associated with greater longevity ( P = 0.015), suggesting
a genetically regulated tradeoff at least partly mediated by IGF1."

The paper, read in PMC (PMC3361401): the Jackson Aging Center's lifespan study of 32 inbred strains, now with
"lifespan data for all 1,945 mice"; "Survival data from mice that died abnormally are treated as censored data";
survival curves by Kaplan-Meier, statistics in JMP 7.0. Age of VP in 31 of the strains ("We dropped NZO/H1LtJ (NZO)
because no NZO breeders were available, and measured 31 strains"), "24.9 +/- 0.4 to 42.9 +/- 0.6 d, mean +/- SEM",
four of the five latest wild-derived (PWD, WSB, CAST, MOLF), D2 "the only domesticated strain with an age of VP within
the range of the wild-derived strains". A post hoc analysis "removed short-lived strains, using 500, 600, and 700 d as
cutoffs ... removed 2, 8, and 15 strains. With these cutoffs, regressions of lifespan on age of VP are R^2 = 0.03
(P = 0.38), R^2 = 0.33 (P = 0.015), and R^2 = 0.35 (P = 0.046)"; Fig. 1's caption gives the second as "R2 = 0.33,
P = 0.005"; over all strains R^2 = 0.04, P = 0.27. "Strains with lower IGF1 level have a delayed age of VP (R^2 = 0.19,
P = 0.013)", and at the three cutoffs R^2 = 0.25 (P = 0.015), 0.18 (P = 0.021) and 0.15 (P = 0.12). D2 and CAST are
short-lived ("female mean lifespan = 580 d" and "578 d").

The deposits. MPD project Yuan2, whose page names this paper: "MPD accessed only those rows in the raw data set where
censor=0. Animals judged to have died from unnatural causes are indicated as censor=1 and are present only in the raw
data set. Strain AKR/J was omitted." It is read here in its raw data set (strain, sex, id, censor, lifespandays), the
1,945 mice less AKR/J's 64. Yuan4: ages of vaginal opening (strain, sex, animal_id, age_VO), females of 33 strains, two
of them (JF1/MsJ and Pohn/Deh) outside the lifespan study. Yuan1: IGF1 at 6, 12 and 18 months (the assay of Yuan et
al. 2009, Aging Cell 8, 277-287), 33 strains, Pohn/Deh among them. AKR/J's females died young (Yuan et al. 2009, Table
2, a completed strain: mean 275 days, SEM 17), below every cutoff the paper uses, so its absence from Yuan2 changes no
analysis at a cutoff; only the regression over all strains runs over 30 strains here, not the paper's 31.

Rules, committed before any lifespan, age of VP or IGF1 value in the files was summarised (their structure was read:
Yuan2.csv 1,881 rows, 1,778 with censor 0 and 103 with censor 1, 31 strains, no AKR/J, BTBR spelled "BTBR T+ tf/J"
where the other two files spell it "BTBR T<+> Itpr3<tf>/J"; Yuan4 1,242 rows, all female, 33 strains, no NZO/HlLtJ;
Yuan1 744 rows, 33 strains, IGF1_M06 filled in 491):

1. Reading: each file's header must be exactly the committed one; a sex is f or m (Yuan4's only f); a lifespan or an
   age of VP is a whole number of days and a censor 0 or 1; an IGF1 value is a decimal or empty. Yuan2.csv's strain
   names are mapped by NAME_MAP to the other files' spelling. Anything else is refused.
2. The panel: the lifespan study's 32 strains, Yuan2.csv's 31 and AKR/J. Its strains with VP: those in Yuan4 (31,
   all but NZO/HlLtJ). JF1/MsJ and Pohn/Deh enter one beside value only.
3. A strain's female mean lifespan: the area under the Kaplan-Meier survival curve of its females in Yuan2.csv, a row
   with censor 0 a death at its lifespandays and a row with censor 1 censored there (deaths before censorings at a
   tie, censored mice at risk at their own time), from 0 to the largest time observed, the curve flat after its last
   drop.
4. A strain's mean age of VP: the mean of age_VO over its rows in Yuan4.
5. A strain's mean female IGF1 at 6 months: the mean of IGF1_M06 over its female rows in Yuan1 that hold a value, as
   deposited.
6. Condition (i): over the strains with female lifespans and VP (30: the panel less AKR/J, which has no lifespans, and
   NZO/HlLtJ, which has no VP), keep those whose female mean lifespan exceeds 600 days; the ordinary least-squares
   regression of female mean lifespan on mean age of VP must have a slope above 0 with two-sided P < 0.05 (Student's
   t, n - 2 degrees of freedom).
7. Condition (ii): over the panel's strains with VP and female IGF1 at 6 months (31), the Pearson correlation of mean
   female IGF1 at 6 months with mean age of VP must be below 0 with two-sided P < 0.05.
8. The test passes when both conditions hold.

Beside the test, not counted:
 (a) Rule 6's regression at the cutoffs 500, 600 and 700 days (strains kept and removed, slope, R^2, P) against the
     printed R^2 0.03, 0.33, 0.35 and P 0.38, 0.015 (0.005 in Fig. 1's caption), 0.046, and 2, 8 and 15 strains removed
     of 31 (AKR/J among them); and over all 30 strains (printed R^2 0.04, P 0.27 over 31).
 (b) Rule 7's correlation over the strains kept at each cutoff (printed R^2 0.25, 0.18, 0.15; P 0.015, 0.021, 0.12).
 (c) Other readings of the mean lifespan (rule 3's is "km"): the area to the last death, rule 3's curve stopped at its
     last drop ("km_death"); the plain mean of the deaths with censor 0, as MPD's animal data matrix holds them
     ("deaths"); every row a death ("all_rows"); and both sexes in one curve ("pooled"). Each with rule 6's regression
     at 600 days and with D2's and CAST's female means (printed 580 and 578).
 (d) Other readings of IGF1: both sexes, the mean of a strain's female and male means ("both"); males ("males");
     female values with |z| > 2 within their strain left out, Yuan et al. 2009's rule, z from the group's mean and
     sample SD ("z2_out"); and the 32 strains with VP and female IGF1, Pohn/Deh added ("with_Pohn").
 (e) VP: the panel's lowest and highest strain means with their SEMs (printed 24.9 +/- 0.4 and 42.9 +/- 0.6 d), its
     five latest strains (printed: four wild-derived, PWD, WSB, CAST and MOLF), and whether D2 is the only domesticated
     strain at or above the earliest wild-derived strain's mean (wild-derived: CAST/EiJ, MOLF/EiJ, PWD/PhJ, WSB/EiJ).
 (f) Yuan et al. 2009's correlation, which the paper's first sentence recalls ("strains with lower circulating ... IGF1
     level at 6 mo have significantly extended longevity"), on the completed deposit: the Pearson correlation of
     strain-by-sex Kaplan-Meier median lifespans (the earliest death time where the curve is at or below 1/2, censor 1
     censored) with mean IGF1 at 6 months over the groups that paper used, less AKR/J: females of the 30 strains other
     than MOLF/EiJ (which entered the study late), males of Yuan2.csv's 28 strains with males; and over those groups
     whose median is at least 600 days. Printed: R = -0.33, P = 0.01, over 60 groups with AKR/J's two; R = -0.53,
     P < 0.01.

Controls (controls_passed of controls_total):
 (a) A plain least-squares regression and Pearson correlation (the P from the regularised incomplete beta function)
     against scipy's linregress and pearsonr on every one computed and on made-up sets: slope and r within 1e-9, P
     within 1e-7 (relative) or 1e-12 (absolute, for P near 0).
 (b) The Kaplan-Meier area by two exact forms (the step sum of S over each interval and the jump form, the sum of each
     drop times its time plus the last S times the end) within 1e-9 on every curve computed; each curve's S at every
     death time, its median and its area against scipy.stats.ecdf on the same censored data within 1e-9.
 (c) The files as read: Yuan2.csv 1,881 rows (1,778 deaths, 103 censored) of 31 strains; Yuan4 1,242 rows of 33;
     Yuan1 744 of 33; every Yuan2 strain, as mapped, in Yuan1, and all but NZO/HlLtJ in Yuan4; the panel 32, with VP 31,
     with VP and female IGF1 31, with VP and lifespans 30.
 (d) Planted panels: a made-up panel whose lifespans rise with VP meets condition (i) and one whose lifespans fall
     with it does not; one whose IGF1 falls with VP meets condition (ii) and one whose IGF1 rises with it does not.
 (e) The deposit as the paper read it: under at least one reading of rule 3 or beside (c), D2's and CAST's female mean
     lifespans are within 1 day of the printed 580 and 578.
 (f) The deposit's VP as the paper read it: the panel's lowest and highest strain means round to the printed 24.9 and
     42.9 days.

Changed after the first trial (seed sha256("imago trial yuan2012 18 October"), whose outputs were seen): the
Kaplan-Meier curve is now computed in exact fractions. In floating point NOD.B10's females, whose curve is exactly 1/2
after 662 days, came out at 0.5000000000000001 there, so their median was given as 669 days, the next death; scipy's
ecdf gave 662 and control (b) failed on it. Scipy's side of control (b) now takes S at or below 1/2 + 1e-12 for its
median. Only beside (f) uses a median; no condition does, and the areas move only in their last bits.

Writes results/outputs.json (the values a receipt carries) and results/detail.json (every value computed).
Run with: python3 itp/yuan2012.py (the pinned scipy-notebook image).
"""

import csv
from fractions import Fraction
import hashlib
import io
import json
import math
import os
import re
import sys

INPUTS = (
    ("Yuan2.csv", "980683707414f662d3b9324d23c94a65bd8b77d7f7e1ba86b73c66d421a451dd", 47582),
    ("Yuan4_animaldata.csv", "ba41899385beb87bb5d5f46c424ccc50cfed32937519ca92684112cff3c30482", 34451),
    ("Yuan1_animaldata.csv", "17aa9c635582a72fee1752cad579eefc2c8fa755321c5362fc7a7365468d68ac", 29914),
)
HEADER_LIFE = ["strain", "sex", "id", "censor", "lifespandays"]
HEADER_VP = ["strain", "sex", "animal_id", "age_VO"]
HEADER_IGF1 = ["strain", "sex", "animal_id", "IGF1_M06", "IGF1_M12", "IGF1_M18", "bw_M06", "bw_M12", "bw_M18"]
NAME_MAP = {"BTBR T+ tf/J": "BTBR T<+> Itpr3<tf>/J"}
AKR, NZO, MOLF = "AKR/J", "NZO/HlLtJ", "MOLF/EiJ"
D2, CAST = "DBA/2J", "CAST/EiJ"
WILD = ("CAST/EiJ", "MOLF/EiJ", "PWD/PhJ", "WSB/EiJ")
OUTSIDE = ("JF1/MsJ", "Pohn/Deh")
CUTOFF = 600
CUTOFFS = (500, 600, 700)
ALPHA = 0.05
YUAN2009_CUT = 600
PRINTED = {
    "vp_life": {500: (0.03, 0.38, 2), 600: (0.33, 0.015, 8), 700: (0.35, 0.046, 15), "all": (0.04, 0.27, 31)},
    "caption_600_p": 0.005,
    "igf1_vp": {500: (0.25, 0.015), 600: (0.18, 0.021), 700: (0.15, 0.12), "all": (0.19, 0.013)},
    "female_mean": {D2: 580, CAST: 578},
    "vp_range": ((24.9, 0.4), (42.9, 0.6)),
    "latest_wild": ("PWD/PhJ", "WSB/EiJ", "CAST/EiJ", "MOLF/EiJ"),
    "yuan2009": {"all": (-0.33, 0.01, 60), "long": (-0.53, 0.01)},
}
EXPECT = {"life_rows": 1881, "deaths": 1778, "censored": 103, "life_strains": 31, "vp_rows": 1242, "vp_strains": 33,
          "igf1_rows": 744, "igf1_strains": 33, "panel": 32, "panel_vp": 31, "panel_vp_igf1": 31, "vp_life": 30}
TEST = ("Refuted if, in the authors' Mouse Phenome Database deposits (Yuan2's raw lifespans, abnormal deaths censored; "
        "Yuan4's ages of vaginal opening; Yuan1's IGF1), among the strains with both whose female Kaplan–Meier mean "
        "lifespan exceeds 600 d, the least-squares regression of that mean on the strain's mean age of VP has slope "
        "≤ 0 or two-sided P ≥ 0.05; or if, over the paper's 31 strains with VP, mean female IGF1 at 6 months is "
        "not negatively correlated with mean age of VP at two-sided P < 0.05.")
OUTPUTS = ("strains_vp_lifespan", "kept_600", "slope_600", "r2_600", "p_600", "r_igf1_vp", "p_igf1_vp", "n_igf1_vp",
           "cutoffs", "igf1_cutoffs", "readings", "d2_cast", "igf1_readings", "vp", "yuan2009",
           "conditions_met", "conditions_total", "test_passed", "controls_passed", "controls_total")


class Refused(Exception):
    pass


# ---------------------------------------------------------------- rule 1: reading

def _rows(data, header, name):
    reader = csv.reader(io.StringIO(data.decode("utf-8")))
    got = next(reader)
    if got != header:
        raise Refused(f"{name}: the header is not the committed one: {got}")
    out = []
    for row in reader:
        if not row:
            continue
        if len(row) != len(header):
            raise Refused(f"{name}: a row of {len(row)} fields: {row}")
        out.append(dict(zip(header, row)))
    return out


def read_lifespans(data):
    """Yuan2.csv as (strain, sex, days, dead) with the strain names mapped."""
    mice = []
    for r in _rows(data, HEADER_LIFE, "Yuan2.csv"):
        if r["sex"] not in ("f", "m"):
            raise Refused(f"Yuan2.csv: a sex other than f or m: {r['sex']!r}")
        if r["censor"] not in ("0", "1"):
            raise Refused(f"Yuan2.csv: a censor other than 0 or 1: {r['censor']!r}")
        if not re.fullmatch(r"\d+", r["lifespandays"]):
            raise Refused(f"Yuan2.csv: a lifespan that is not whole days: {r['lifespandays']!r}")
        mice.append((NAME_MAP.get(r["strain"], r["strain"]), r["sex"], int(r["lifespandays"]), r["censor"] == "0"))
    return mice


def read_vp(data):
    """Yuan4 as (strain, days)."""
    out = []
    for r in _rows(data, HEADER_VP, "Yuan4_animaldata.csv"):
        if r["sex"] != "f":
            raise Refused(f"Yuan4: a sex other than f: {r['sex']!r}")
        if not re.fullmatch(r"\d+", r["age_VO"]):
            raise Refused(f"Yuan4: an age of VP that is not whole days: {r['age_VO']!r}")
        out.append((r["strain"], int(r["age_VO"])))
    return out


def read_igf1(data):
    """Yuan1 as (strain, sex, IGF1 at 6 months or None)."""
    out = []
    for r in _rows(data, HEADER_IGF1, "Yuan1_animaldata.csv"):
        if r["sex"] not in ("f", "m"):
            raise Refused(f"Yuan1: a sex other than f or m: {r['sex']!r}")
        for k in HEADER_IGF1[3:]:
            v = r[k].strip()
            if v and not re.fullmatch(r"\d+(\.\d+)?", v):
                raise Refused(f"Yuan1: {k} is not a decimal: {v!r}")
        v = r["IGF1_M06"].strip()
        out.append((r["strain"], r["sex"], float(v) if v else None))
    return out


# ---------------------------------------------------------------- rule 3: Kaplan-Meier

def km_steps(obs):
    """obs: [(time, dead)]. Returns [(t, deaths, censored, at_risk, S after t)] over the distinct times, ascending,
    S an exact fraction."""
    by_t = {}
    for t, dead in obs:
        c = by_t.setdefault(t, [0, 0])
        c[0 if dead else 1] += 1
    at_risk, s, steps = len(obs), Fraction(1), []
    for t in sorted(by_t):
        d, c = by_t[t]
        if d:
            s *= Fraction(at_risk - d, at_risk)
        steps.append((t, d, c, at_risk, s))
        at_risk -= d + c
    return steps


def km_area(obs, end="observed"):
    """Area under the curve from 0: to the largest time observed (end="observed") or to the last death ("death")."""
    steps = km_steps(obs)
    deaths = [st for st in steps if st[1]]
    if not deaths:
        raise ArithmeticError("a curve with no death")
    stop = steps[-1][0] if end == "observed" else deaths[-1][0]
    area, prev_t, prev_s = Fraction(0), 0, Fraction(1)
    for t, d, c, n, s in steps:
        if t > stop:
            break
        area += prev_s * (t - prev_t)
        prev_t, prev_s = t, s
    return float(area)


def km_area_jumps(obs, end="observed"):
    """The same area by the jump form: sum over deaths of the drop times its time, plus the last S times the end."""
    steps = km_steps(obs)
    deaths = [st for st in steps if st[1]]
    stop = steps[-1][0] if end == "observed" else deaths[-1][0]
    total, prev_s = Fraction(0), Fraction(1)
    for t, d, c, n, s in deaths:
        total += (prev_s - s) * t
        prev_s = s
    return float(total + prev_s * stop)


def km_median(obs):
    for t, d, c, n, s in km_steps(obs):
        if d and s <= Fraction(1, 2):
            return t
    return None


def scipy_km(obs):
    """S after each death time, the median and the area to the largest time, from scipy.stats.ecdf."""
    from scipy import stats
    dead = [t for t, x in obs if x]
    cens = [t for t, x in obs if not x]
    sample = stats.CensoredData(uncensored=dead, right=cens) if cens else dead
    sf = stats.ecdf(sample).sf
    times = sorted({t for t, _ in obs})
    s_at = {t: float(sf.evaluate(t)) for t in times}
    area, prev_t, prev_s = 0.0, 0, 1.0
    for t in times:
        area += prev_s * (t - prev_t)
        prev_t, prev_s = t, s_at[t]
    med = next((t for t in sorted(set(dead)) if s_at[t] <= 0.5 + 1e-12), None)
    return {t: s_at[t] for t in sorted(set(dead))}, med, area


# ---------------------------------------------------------------- statistics: plain and scipy

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


def mean(x):
    return sum(x) / len(x)


def sd(x):
    m = mean(x)
    return math.sqrt(sum((v - m) ** 2 for v in x) / (len(x) - 1))


def plain_regress(x, y):
    """Least squares of y on x: slope, intercept, r, two-sided P of the slope (Student's t, n - 2 df), R^2."""
    n = len(x)
    mx, my = mean(x), mean(y)
    sxx = sum((u - mx) ** 2 for u in x)
    syy = sum((v - my) ** 2 for v in y)
    sxy = sum((u - mx) * (v - my) for u, v in zip(x, y))
    slope = sxy / sxx
    r = sxy / math.sqrt(sxx * syy)
    df = n - 2
    t2 = r * r * df / max(1e-300, (1 - r) * (1 + r))
    p = betainc(df / 2, 0.5, df / (df + t2))
    return {"n": n, "slope": slope, "intercept": my - slope * mx, "r": r, "p": p, "r2": r * r}


def scipy_regress(x, y):
    from scipy.stats import linregress, pearsonr
    lr = linregress(x, y)
    pr = pearsonr(x, y)
    return {"slope": float(lr.slope), "r": float(lr.rvalue), "p": float(lr.pvalue), "pearson_r": float(pr.statistic),
            "pearson_p": float(pr.pvalue)}


def close(a, b, rel=1e-9):
    if a is None or b is None:
        return a is b
    return abs(a - b) <= rel * max(abs(a), abs(b), 1e-300)


# ---------------------------------------------------------------- rules 2 to 8

def groups_life(mice):
    g = {}
    for strain, sex, days, dead in mice:
        g.setdefault((strain, sex), []).append((days, dead))
    return g


def strain_means(pairs):
    g = {}
    for strain, v in pairs:
        g.setdefault(strain, []).append(v)
    return {s: mean(v) for s, v in g.items()}, g


def igf1_means(igf1, sex, z_out=False):
    g = {}
    for strain, x, v in igf1:
        if x == sex and v is not None:
            g.setdefault(strain, []).append(v)
    if z_out:
        for s, v in list(g.items()):
            if len(v) >= 3:
                m, d = mean(v), sd(v)
                g[s] = [u for u in v if d == 0 or abs(u - m) / d <= 2]
    return {s: mean(v) for s, v in g.items() if v}


def condition_i(life_mean, vp_mean, strains, cutoff=CUTOFF, log=None):
    kept = sorted(s for s in strains if life_mean[s] > cutoff)
    x = [vp_mean[s] for s in kept]
    y = [life_mean[s] for s in kept]
    reg = plain_regress(x, y)
    if log is not None:
        log.append((x, y, reg))
    reg["kept"], reg["removed"] = len(kept), len(strains) - len(kept)
    reg["strains"] = kept
    reg["holds"] = reg["slope"] > 0 and reg["p"] < ALPHA
    return reg


def condition_ii(igf1_mean, vp_mean, strains, log=None):
    use = sorted(s for s in strains if s in igf1_mean and s in vp_mean)
    x = [igf1_mean[s] for s in use]
    y = [vp_mean[s] for s in use]
    reg = plain_regress(x, y)
    if log is not None:
        log.append((x, y, reg))
    reg["holds"] = reg["r"] < 0 and reg["p"] < ALPHA
    reg["strains"] = use
    return reg


def life_readings(g, strains):
    """Female (or pooled) mean lifespans per strain under each named reading."""
    out = {"km": {}, "km_death": {}, "deaths": {}, "all_rows": {}, "pooled": {}}
    for s in strains:
        f = g.get((s, "f"), [])
        out["km"][s] = km_area(f, "observed")
        out["km_death"][s] = km_area(f, "death")
        out["deaths"][s] = mean([t for t, dead in f if dead])
        out["all_rows"][s] = mean([t for t, _ in f])
        out["pooled"][s] = km_area(f + g.get((s, "m"), []), "observed")
    return out


def assess(mice, vp_rows, igf1):
    g = groups_life(mice)
    life_strains = sorted({m[0] for m in mice})
    panel = sorted(set(life_strains) | {AKR})
    vp_mean, vp_g = strain_means(vp_rows)
    panel_vp = [s for s in panel if s in vp_mean]
    vp_life = [s for s in panel_vp if (s, "f") in g]
    f_igf1 = igf1_means(igf1, "f")
    m_igf1 = igf1_means(igf1, "m")
    panel_vp_igf1 = [s for s in panel_vp if s in f_igf1]

    rlog, kmlog = [], []
    readings = life_readings(g, vp_life)
    life = readings["km"]
    c1 = condition_i(life, vp_mean, vp_life, log=rlog)
    c2 = condition_ii(f_igf1, vp_mean, panel_vp_igf1, log=rlog)
    cond = {"(i) female mean lifespan rises with mean age of VP among strains above 600 days, P < 0.05": c1["holds"],
            "(ii) mean female IGF1 at 6 months falls with mean age of VP over the panel's strains, P < 0.05": c2["holds"]}
    for s in vp_life:
        kmlog.append(g[(s, "f")])
        kmlog.append(g[(s, "f")] + g.get((s, "m"), []))

    # beside (a) and (b): the cutoffs
    cut = {}
    for c in CUTOFFS:
        a = condition_i(life, vp_mean, vp_life, cutoff=c, log=rlog)
        b = condition_ii(f_igf1, vp_mean, [s for s in a["strains"] if s in f_igf1], log=rlog)
        cut[c] = {"vp_life": a, "igf1_vp": b}
    x_all = [vp_mean[s] for s in vp_life]
    y_all = [life[s] for s in vp_life]
    allreg = plain_regress(x_all, y_all)
    rlog.append((x_all, y_all, allreg))

    # beside (c): readings of the mean lifespan
    rd = {}
    for k, vals in readings.items():
        reg = condition_i(vals, vp_mean, vp_life, log=rlog)
        rd[k] = {"kept": reg["kept"], "slope": reg["slope"], "r2": reg["r2"], "p": reg["p"], "holds": reg["holds"],
                 "D2": vals.get(D2), "CAST": vals.get(CAST)}

    # beside (d): readings of IGF1
    both = {s: (f_igf1[s] + m_igf1[s]) / 2 if (s in f_igf1 and s in m_igf1) else f_igf1.get(s, m_igf1.get(s))
            for s in set(f_igf1) | set(m_igf1)}
    ir = {"both": condition_ii(both, vp_mean, panel_vp, log=rlog),
          "males": condition_ii(m_igf1, vp_mean, panel_vp, log=rlog),
          "z2_out": condition_ii(igf1_means(igf1, "f", z_out=True), vp_mean, panel_vp, log=rlog),
          "with_Pohn": condition_ii(f_igf1, vp_mean, sorted(set(panel_vp) | {"Pohn/Deh"}), log=rlog)}

    # beside (e): VP
    sem = {s: sd(v) / math.sqrt(len(v)) for s, v in vp_g.items() if len(v) > 1}
    order = sorted(panel_vp, key=lambda s: vp_mean[s])
    lo, hi = order[0], order[-1]
    latest5 = order[-5:][::-1]
    earliest_wild = min((vp_mean[s] for s in WILD if s in vp_mean), default=math.inf)
    dom_late = [s for s in panel_vp if s not in WILD and vp_mean[s] >= earliest_wild]

    # beside (f): Yuan et al. 2009's correlation on the completed deposit
    pts = []
    for (s, sex), obs in sorted(g.items()):
        if sex == "f" and s == MOLF:
            continue
        means = f_igf1 if sex == "f" else m_igf1
        if s in means:
            pts.append((s, sex, km_median(obs), means[s]))
            kmlog.append(obs)
    y9 = plain_regress([p[3] for p in pts], [p[2] for p in pts])
    rlog.append(([p[3] for p in pts], [p[2] for p in pts], y9))
    long_pts = [p for p in pts if p[2] >= YUAN2009_CUT]
    y9l = plain_regress([p[3] for p in long_pts], [p[2] for p in long_pts])
    rlog.append(([p[3] for p in long_pts], [p[2] for p in long_pts], y9l))

    # controls
    ctl = {}
    ok = True
    made = (([1, 2, 3, 4, 5], [2.1, 3.9, 6.2, 7.8, 10.1]), ([25, 30, 31, 40, 28, 35], [700, 650, 800, 820, 610, 790]),
            ([300.5, 250, 410, 380, 290], [40, 33, 30, 27, 36]))
    for x, y, reg in rlog + [(x, y, plain_regress(x, y)) for x, y in made]:
        sc = scipy_regress(x, y)
        ok = ok and close(reg["slope"], sc["slope"]) and close(reg["r"], sc["r"]) and close(reg["r"], sc["pearson_r"])
        ok = ok and all(close(reg["p"], q, 1e-7) or abs(reg["p"] - q) < 1e-12 for q in (sc["p"], sc["pearson_p"]))
    ctl["plain regressions and correlations against scipy's linregress and pearsonr on every one and three made-up"] = ok
    ok = True
    for obs in kmlog:
        for end in ("observed", "death"):
            ok = ok and close(km_area(obs, end), km_area_jumps(obs, end))
        s_sc, med_sc, area_sc = scipy_km(obs)
        s_me = {t: float(s) for t, d, c, n, s in km_steps(obs) if d}
        ok = ok and set(s_sc) == set(s_me) and all(close(s_sc[t], s_me[t]) for t in s_me)
        ok = ok and med_sc == km_median(obs) and close(area_sc, km_area(obs, "observed"))
    ctl["Kaplan-Meier areas by two exact forms, and S, medians and areas against scipy.stats.ecdf, on every curve"] = ok
    n_dead = sum(1 for m in mice if m[3])
    ctl["the files as read: 1,881 lifespans (1,778 deaths, 103 censored) of 31 strains, 1,242 VP of 33, 744 IGF1 of "
        "33; names matched; panel 32, with VP 31, with VP and IGF1 31, with VP and lifespans 30"] = (
        len(mice) == EXPECT["life_rows"] and n_dead == EXPECT["deaths"] and len(mice) - n_dead == EXPECT["censored"]
        and len(life_strains) == EXPECT["life_strains"] and len(vp_rows) == EXPECT["vp_rows"]
        and len(vp_mean) == EXPECT["vp_strains"] and len(igf1) == EXPECT["igf1_rows"]
        and len({r[0] for r in igf1}) == EXPECT["igf1_strains"]
        and all(s in {r[0] for r in igf1} for s in life_strains)
        and sorted(s for s in life_strains if s not in vp_mean) == [NZO]
        and len(panel) == EXPECT["panel"] and len(panel_vp) == EXPECT["panel_vp"]
        and len(panel_vp_igf1) == EXPECT["panel_vp_igf1"] and len(vp_life) == EXPECT["vp_life"])
    ctl["planted panels: lifespans rising with VP meet (i), falling do not; IGF1 falling with VP meets (ii), rising "
        "does not"] = planted_ok()
    near = [k for k, v in rd.items() if v["D2"] is not None and v["CAST"] is not None
            and abs(v["D2"] - PRINTED["female_mean"][D2]) <= 1 and abs(v["CAST"] - PRINTED["female_mean"][CAST]) <= 1]
    ctl["the deposit as the paper read it: D2's and CAST's female means within 1 day of 580 and 578 under a named "
        "reading"] = bool(near)
    ctl["the deposit's VP as the paper read it: the panel's lowest and highest strain means round to 24.9 and 42.9"] = (
        round(vp_mean[lo], 1) == PRINTED["vp_range"][0][0] and round(vp_mean[hi], 1) == PRINTED["vp_range"][1][0])

    def rp(reg):
        return f"R2 {reg['r2']:.3f} P {reg['p']:.2g}"

    def short(s):
        return s.split("/")[0].split(" ")[0][:10]

    def f1(v):
        return f"{v:.1f}" if v is not None else "na"

    pv = PRINTED["vp_life"]
    pi = PRINTED["igf1_vp"]
    values = {
        "strains_vp_lifespan": len(vp_life), "kept_600": c1["kept"], "slope_600": c1["slope"], "r2_600": c1["r2"],
        "p_600": c1["p"], "r_igf1_vp": c2["r"], "p_igf1_vp": c2["p"], "n_igf1_vp": c2["n"],
        "cutoffs": "; ".join(f"{c} out {cut[c]['vp_life']['removed']}/{len(vp_life)} {rp(cut[c]['vp_life'])} "
                             f"[{pv[c][0]} {pv[c][1]} {pv[c][2]}/31]" for c in CUTOFFS)
        + f"; all {rp(allreg)} [{pv['all'][0]} {pv['all'][1]}]",
        "igf1_cutoffs": "; ".join(f"{c} n {cut[c]['igf1_vp']['n']} r {cut[c]['igf1_vp']['r']:.3f} "
                                  f"{rp(cut[c]['igf1_vp'])} [{pi[c][0]} {pi[c][1]}]" for c in CUTOFFS)
        + f"; all [{pi['all'][0]} {pi['all'][1]}]",
        "readings": "; ".join(f"{k} {v['kept']} kept R2 {v['r2']:.3f} P {v['p']:.2g}" for k, v in rd.items()),
        "d2_cast": "; ".join(f"{k} {f1(v['D2'])} {f1(v['CAST'])}" for k, v in rd.items()) + " [580 578]",
        "igf1_readings": "; ".join(f"{k} n {v['n']} r {v['r']:.3f} P {v['p']:.2g}" for k, v in ir.items()),
        "vp": (f"low {short(lo)} {vp_mean[lo]:.2f} sem {sem.get(lo, float('nan')):.2f}; high {short(hi)} "
               f"{vp_mean[hi]:.2f} sem {sem.get(hi, float('nan')):.2f}; latest {','.join(short(s) for s in latest5)}; "
               f"tame at wild {','.join(short(s) for s in dom_late) or 'none'}"),
        "yuan2009": (f"median~IGF1 6 mo {y9['n']} groups r {y9['r']:.3f} P {y9['p']:.2g}; median >= 600 {y9l['n']} "
                     f"r {y9l['r']:.3f} P {y9l['p']:.2g} [-0.33 P 0.01 over 60; -0.53 P < 0.01]"),
        "conditions_met": sum(cond.values()), "conditions_total": len(cond), "test_passed": int(all(cond.values())),
        "controls_passed": sum(ctl.values()), "controls_total": len(ctl),
    }
    out = {k: values[k] for k in OUTPUTS}
    for k, v in out.items():
        if isinstance(v, str) and len(v) > 200:
            raise AssertionError(f"{k}: longer than 200 characters ({len(v)}): {v}")
        if isinstance(v, float) and not math.isfinite(v):
            raise AssertionError(f"{k}: not finite")

    def strip(reg):
        return {k: v for k, v in reg.items()}

    detail = {
        "test": TEST, "conditions": cond, "controls": ctl, "printed": {k: (v if not isinstance(v, dict) else
                                                                           {str(kk): vv for kk, vv in v.items()})
                                                                       for k, v in PRINTED.items()},
        "condition_i": strip(c1), "condition_ii": strip(c2),
        "cutoffs": {str(c): {"vp_life": strip(cut[c]["vp_life"]), "igf1_vp": strip(cut[c]["igf1_vp"])} for c in CUTOFFS},
        "all_strains": strip(allreg), "readings": rd, "igf1_readings": {k: strip(v) for k, v in ir.items()},
        "female_mean_lifespan": {k: {s: v for s, v in vals.items()} for k, vals in readings.items()},
        "vp_mean": vp_mean, "vp_n": {s: len(v) for s, v in vp_g.items()}, "vp_sem": sem,
        "igf1_female": f_igf1, "igf1_male": m_igf1, "near_printed_d2_cast": near,
        "yuan2009_points": [{"strain": p[0], "sex": p[1], "median": p[2], "igf1": p[3]} for p in pts],
        "yuan2009": {"all": strip(y9), "long": strip(y9l)},
        "panel": panel, "panel_vp": panel_vp, "vp_life": vp_life,
    }
    return out, detail


def planted_ok():
    strains = [f"P{i:02d}" for i in range(20)]
    vp = {s: 25.0 + i * 0.9 for i, s in enumerate(strains)}
    wob = [((i * 37) % 11 - 5) * 3.0 for i in range(20)]
    rise = {s: 640 + 12 * (vp[s] - 25) + wob[i] for i, s in enumerate(strains)}
    fall = {s: 900 - 12 * (vp[s] - 25) + wob[i] for i, s in enumerate(strains)}
    i_fall = {s: 420 - 6 * (vp[s] - 25) + wob[i] for i, s in enumerate(strains)}
    i_rise = {s: 250 + 6 * (vp[s] - 25) + wob[i] for i, s in enumerate(strains)}
    return (condition_i(rise, vp, strains)["holds"] and not condition_i(fall, vp, strains)["holds"]
            and condition_ii(i_fall, vp, strains)["holds"] and not condition_ii(i_rise, vp, strains)["holds"])


# ---------------------------------------------------------------- the run

def run(seed, inputs="inputs", results="results"):
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        raise Refused("the seed must be 64 hex characters")
    data = []
    for name, sha, size in INPUTS:
        with open(os.path.join(inputs, name), "rb") as fh:
            b = fh.read()
        if hashlib.sha256(b).hexdigest() != sha or len(b) != size:
            raise Refused(f"{name} is not the committed file")
        data.append(b)
    out, detail = assess(read_lifespans(data[0]), read_vp(data[1]), read_igf1(data[2]))
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
        sys.exit(f"yuan2012: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
