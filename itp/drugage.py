"""Weight loss and lifespan extension across mouse drug studies: Belikov, Talay & de Magalhaes (2025), its own table.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:44dfcde04ae07f80) is from Belikov, Talay
and de Magalhaes, "Sex-specific insights into drug-induced lifespan extension and weight loss in mice", npj Aging 11,
40 (2025; CC BY), its abstract: "Our analysis revealed significant correlations between weight loss and lifespan
extension in male mice, particularly in studies conducted by the Interventions Testing Program, highlighting the
importance of considering weight changes in lifespan studies." The paper, read in Europe PMC's full text: DrugAge
Build 5 re-recorded every mouse experiment from its source (one experiment a dose, treatment scheme, sex and strain),
with the change in average/median and maximum lifespan and in body weight, each as a percentage of control, and
marked the Interventions Testing Program's; "The linear regression and the corresponding statistics were produced
using the linregress function from the scipy.stats library in Python"; "The dataset used to generate the figures in
this article is available as a Supplementary Table" (the claim's data of record, by hash). Its results: over all
data, "correlations between weight change and median or maximum lifespan change are significant ... for males alone
but not for females alone"; with ITP data only, "In males there is a strong correlation between the increase in
lifespan and decrease in weight, both for median (slope: -0.76, R2: 0.52, p-value: 3.09 x 10^-11, Fig. 2C) and for
maximum (slope: -0.97, R2: 0.35, p-value: 3.73 x 10^-7, Fig. 2D) lifespan."

Rules, committed before any regression was computed on the table (its structure was read: two sheets, the first,
"DrugAge Mice - all instances", with 17 named columns and 367 rows; its column ITP? holds "ITP" or "No", its column
Sex "M", "F", "M+F" or "?"):

1. Rows: the first sheet's, keyed by its header row. A row is an ITP experiment when ITP? is "ITP", and in males when
   Sex is "M" ("M+F" and "?" rows are in neither sex). x is "Weight change (% of control)"; y is "Avg_lifespan_change
   (% of control)" (the paper's median panel) or "Max_lifespan_change (% of control)" (its maximum panel). A row
   enters a regression only when both its x and y cells are numbers; an empty cell or text ("not available") is
   missing.
2. Each regression is scipy.stats.linregress(x, y), as the paper's, in the pinned scipy-notebook image: slope, R^2
   and the two-sided p-value of the slope.
3. The test's conditions: C1, ITP experiments in males, median: slope below 0 and p below 0.05; C2, the same for the
   maximum; C3, all male experiments (ITP or not), median: slope below 0 and p below 0.05 (the abstract's "in male
   mice"). The test passes when all three hold.

Beside the test, not counted: the paper's printed numbers against those computed (slopes and R^2 to two decimals, p to
three significant figures); the same regressions in females and in both sexes.

Controls (controls_passed of controls_total):
 (a) A plain implementation (least squares in closed form, the p-value from the regularised incomplete beta function)
     against linregress on every regression computed and on sets made here: slope, R^2 and p within 1e-9 (relative).
 (b) The table as read: 367 rows under the 17 named columns, 164 marked ITP, 192 in males.
 (c) The selection: a row with Sex "M+F" or "?" enters no sex's regression, and a row with a text cell enters none.
"""

import hashlib
import io
import json
import math
import os
import re
import sys
import xml.etree.ElementTree as ET
import zipfile

INPUT = ("drugage-belikov2025-supp.xlsx", "d04ab25b810b585195e6f2c50aaa8aec114608fd40b2f4d65ca8a639997feb61")
NS = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
X = "Weight change (% of control)"
Y = {"median": "Avg_lifespan_change (% of control)", "max": "Max_lifespan_change (% of control)"}
HEADER = ["Compound_name", "Pubchem_id", "ITP?", "Sex", "Avg_lifespan_change (% of control)",
          "Avg_lifespan_significance", "Max_lifespan_change (% of control)", "Max_lifespan_significance",
          "Weight change (% of control)", "Weight change significance", "Pubmed_id", "Author year", "Dosage",
          "Treat_start_month", "Treat_duration", "Strain", "Comments/Questions"]
PRINTED = {"median": (-0.76, 0.52, 3.09e-11), "max": (-0.97, 0.35, 3.73e-7)}
ALPHA = 0.05
TEST = ("Refuted if, in the paper's supplementary table (DrugAge Build 5's mouse experiments), among ITP experiments in "
        "male mice with both values recorded, scipy's linregress of average/median lifespan change (% of control) on "
        "weight change (% of control) gives a slope that is not negative or p >= 0.05; or likewise for maximum "
        "lifespan change; or, over all male experiments, the median regression's slope is not negative or p >= 0.05.")


class Refused(Exception):
    pass


def read_rows(data):
    """The first sheet as a list of dicts keyed by its header row; numbers as text, as the file holds them."""
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        shared = []
        if "xl/sharedStrings.xml" in z.namelist():
            for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall("x:si", NS):
                shared.append("".join(t.text or "" for t in si.iter("{%s}t" % NS["x"])))
        sheet = ET.fromstring(z.read("xl/worksheets/sheet1.xml"))
    rows = []
    for row in sheet.find("x:sheetData", NS).findall("x:row", NS):
        cells = {}
        for c in row.findall("x:c", NS):
            col = re.match(r"[A-Z]+", c.get("r")).group(0)
            kind = c.get("t")
            if kind == "inlineStr":
                value = "".join(t.text or "" for t in c.iter("{%s}t" % NS["x"]))
            elif kind == "s":
                value = shared[int(c.find("x:v", NS).text)]
            else:
                v = c.find("x:v", NS)
                value = v.text if v is not None else None
            cells[col] = value
        rows.append(cells)
    header = rows[0]
    keys = sorted(header, key=lambda k: (len(k), k))
    return [header[k] for k in keys], [{header[k]: r.get(k) for k in keys} for r in rows[1:]]


def number(v):
    if v is None:
        return None
    try:
        x = float(v)
    except ValueError:
        return None
    return x if math.isfinite(x) else None


def select(rows, itp, sex, ycol):
    out = []
    for r in rows:
        if itp is not None and (r.get("ITP?") == "ITP") != itp:
            continue
        if sex is not None and r.get("Sex") != sex:
            continue
        x, y = number(r.get(X)), number(r.get(ycol))
        if x is None or y is None:
            continue
        out.append((x, y))
    return out


# ---------------------------------------------------------------- the plain regression (control a)

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


def plain_regression(pts):
    n = len(pts)
    mx = sum(p[0] for p in pts) / n
    my = sum(p[1] for p in pts) / n
    sxx = sum((p[0] - mx) ** 2 for p in pts)
    syy = sum((p[1] - my) ** 2 for p in pts)
    sxy = sum((p[0] - mx) * (p[1] - my) for p in pts)
    slope = sxy / sxx
    r = sxy / math.sqrt(sxx * syy)
    df = n - 2
    t2 = r * r * df / max(1e-300, (1 - r) * (1 + r))
    p = betainc(df / 2, 0.5, df / (df + t2))
    return {"n": n, "slope": slope, "r2": r * r, "p": p}


def regression(pts):
    from scipy.stats import linregress
    res = linregress([p[0] for p in pts], [p[1] for p in pts])
    return {"n": len(pts), "slope": float(res.slope), "r2": float(res.rvalue) ** 2, "p": float(res.pvalue)}


def close(a, b, rel=1e-9):
    return abs(a - b) <= rel * max(abs(a), abs(b), 1e-300)


# ---------------------------------------------------------------- the assessment

def assess(rows, header):
    fits = {}
    for itp_name, itp in (("itp", True), ("all", None)):
        for sex_name, sex in (("m", "M"), ("f", "F"), ("both", None)):
            for panel, ycol in Y.items():
                pts = select(rows, itp, sex, ycol)
                fits[f"{itp_name}_{sex_name}_{panel}"] = regression(pts) if len(pts) >= 3 else None
    a, b, c = fits["itp_m_median"], fits["itp_m_max"], fits["all_m_median"]
    c1 = a is not None and a["slope"] < 0 and a["p"] < ALPHA
    c2 = b is not None and b["slope"] < 0 and b["p"] < ALPHA
    c3 = c is not None and c["slope"] < 0 and c["p"] < ALPHA
    cond = {"C1 ITP males, median": c1, "C2 ITP males, maximum": c2, "C3 all males, median": c3}

    ctl = {}
    ok = True
    gaps = []
    for k, f in fits.items():
        if f is None:
            continue
        itp_name, sex_name, panel = k.split("_")
        pts = select(rows, True if itp_name == "itp" else None, {"m": "M", "f": "F", "both": None}[sex_name], Y[panel])
        q = plain_regression(pts)
        ok &= close(q["slope"], f["slope"]) and close(q["r2"], f["r2"]) and close(q["p"], f["p"], 1e-7)
        gaps.append((k, abs(q["p"] - f["p"]) / max(f["p"], 1e-300)))
    for made in ([(0, 1.0), (1, 2.9), (2, 5.2), (3, 6.8), (4, 9.5)], [(1, 4), (2, 1), (3, 5), (4, 2), (5, 6), (6, 3)]):
        q, f = plain_regression(made), regression(made)
        ok &= close(q["slope"], f["slope"]) and close(q["p"], f["p"], 1e-7)
    ctl["(a) plain regression against linregress"] = ok
    ctl["(b) the table as read"] = (header == HEADER and len(rows) == 367
                                    and sum(1 for r in rows if r.get("ITP?") == "ITP") == 164
                                    and sum(1 for r in rows if r.get("Sex") == "M") == 192)
    planted = [{"ITP?": "ITP", "Sex": "M+F", X: "-10", Y["median"]: "5"},
               {"ITP?": "ITP", "Sex": "?", X: "-10", Y["median"]: "5"},
               {"ITP?": "ITP", "Sex": "M", X: "not available", Y["median"]: "5"},
               {"ITP?": "ITP", "Sex": "M", X: "-3", Y["median"]: ""}]
    ctl["(c) the selection"] = all(select([r], True, s, Y["median"]) == [] for r in planted for s in ("M", "F")) and \
        select([{"ITP?": "ITP", "Sex": "M", X: "-3", Y["median"]: "4.5"}], True, "M", Y["median"]) == [(-3.0, 4.5)]

    def short(f):
        return "n/a" if f is None else f"n {f['n']}, slope {f['slope']:.3f}, R^2 {f['r2']:.3f}, p {f['p']:.3g}"
    match = []
    for panel, key in (("median", "itp_m_median"), ("max", "itp_m_max")):
        f = fits[key]
        s, r2, p = PRINTED[panel]
        match.append(f is not None and round(f["slope"], 2) == s and round(f["r2"], 2) == r2
                     and float(f"{f['p']:.3g}") == p)
    met = sum(cond.values())
    out = {
        "itp_m_median": short(a), "itp_m_max": short(b), "all_m_median": short(c),
        "itp_f_median": short(fits["itp_f_median"]), "itp_f_max": short(fits["itp_f_max"]),
        "all_f_median": short(fits["all_f_median"]), "all_m_max": short(fits["all_m_max"]),
        "slope_itp_m_median": round(a["slope"], 6) if a else 0, "p_itp_m_median": float(f"{a['p']:.6g}") if a else 1,
        "printed_matched": sum(match), "printed_total": len(match),
        "conditions_met": met, "conditions_total": len(cond), "test_passed": int(met == len(cond)),
        "controls_passed": sum(ctl.values()), "controls_total": len(ctl),
    }
    for k, v in out.items():
        if isinstance(v, str) and len(v) > 200:
            raise AssertionError(f"{k}: longer than 200 characters")
    detail = {"test": TEST, "conditions": cond, "controls": ctl, "fits": fits, "printed": PRINTED,
              "printed_match": match, "p_gaps": gaps}
    return out, detail


def run(seed, inputs="inputs", results="results"):
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        raise Refused("the seed must be 64 hex characters")
    path = os.path.join(inputs, INPUT[0])
    with open(path, "rb") as fh:
        data = fh.read()
    if hashlib.sha256(data).hexdigest() != INPUT[1]:
        raise Refused(f"{INPUT[0]} is not the committed file")
    header, rows = read_rows(data)
    out, detail = assess(rows, header)
    os.makedirs(results, exist_ok=True)
    with open(os.path.join(results, "outputs.json"), "w", encoding="ascii") as fh:
        json.dump(out, fh, indent=2, sort_keys=True)
        fh.write("\n")
    with open(os.path.join(results, "detail.json"), "w", encoding="utf-8") as fh:
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
        sys.exit(f"drugage: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
