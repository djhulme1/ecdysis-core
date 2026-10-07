#!/usr/bin/env python3
"""Shifting attention to accuracy: the survey studies' Treatment x Veracity estimates, re-run from the authors' data.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:c9c5c670f8aa1b81, registered by Calopteryx)
is from Pennycook, Epstein, Mosleh, Arechar, Eckles and Rand, "Shifting attention to accuracy can reduce
misinformation online", Nature 592 (2021): "To shed light on this apparent contradiction, we carried out four survey
experiments and a field experiment on Twitter; the results show that subtly shifting attention to accuracy increases
the quality of news that people subsequently share."

Its registered test: "Reproduction check on the authors' own data and code. Refuted if their analysis
(Study_3_and_4_code.do, Study_5_code.do: OLS, sharing intention 0-1 on condition x veracity, participants who share
political news, SEs clustered on participant and headline; S5 Treatment and Importance Treatment vs pooled
controls), re-run on the Study 3-5 data, gives counts, a Treatment x Veracity estimate (by >0.0001) or SE (by >5%)
unlike Supplementary Tables S2, S4: S3 0.0529 (0.0108), N 17,417/727/24; S4 0.0648 (0.0147), 18,677/780/24; S5
0.0542 (0.0157), 13,340/671/20. Study 7 untested: data not public."

Stata is not in the image, so the analysis is re-implemented here, line by line from the authors' do-files, and the
standard errors from the program they call, Mitchell Petersen's cluster2.ado. The do-files and cluster2.ado are
inputs, read as data: the lines this implementation follows must appear in them verbatim (rule 2), so a change to
either would stop the run rather than pass unnoticed. Nothing in any input is run. Every rule below was fixed before
any seed existed; the seed is not used, as the analysis has no randomness.

1. The inputs, each checked against its SHA-256 and size before anything else runs: the claim's data of record (the
   three studies' data and the two do-files, from the paper's OSF project p6u8k) and cluster2.ado.
2. The code, read as data. Each line in REQUIRED must appear in its file, compared after removing carriage returns
   and surrounding blanks: the regressions behind Tables S2 and S4, the sample and the variables (rules 4 and 5), and
   cluster2.ado's three regressions and its sum (rule 6).
3. The data. Each CSV is read with names lowercased, as Stata's insheet reads them; a value that is empty or blank
   is missing, and any other value of a column used must be a number (destring); a rating must be a whole number from
   1 to 6. Anything else is refused.
4. The sample, as the do-files build it. A participant whose socialmedia_chk is missing, or whose fb is 2, is
   dropped ("drop if didnt_finish==1 | fb==2"); the regressions keep socialmedia_chk == 1, the participants who
   sometimes share political news. Each participant gives one row per headline: the rating of fake headline k
   (column fake<k>_3) and of true headline k (real<k>_3), with sm = (rating - 1) / 5; a missing rating drops its row,
   as regress drops it. Headlines are labelled k + 12 real (plus 24 in Study 3) in Studies 3 and 4, and k + 10 real
   in Study 5; participants are labelled by their row. In Studies 3 and 4, a participant with no condition is
   dropped, as xi's dummy for a missing condition is missing. In Study 5, Stata's condition==3 is 0 when condition is
   missing, so such a participant would count as a control; detail.json counts them.
5. The model, OLS with a constant. Studies 3 and 4: sm on condition (Condition - 1), real (1 for a true headline),
   and their product. Study 5: sm on treatment (Condition 3), real, treatment x real, importance (Condition 4) and
   importance x real, the two controls (Conditions 1 and 2) pooled. The estimate tested is the product's coefficient.
6. Standard errors, as cluster2.ado computes them: V = V_headline + V_participant - V_third, each from Stata's
   regress with its small-sample factor. Clustered by g: (N - 1) / (N - K) * G / (G - 1) * A^-1 (sum over clusters of
   u u') A^-1, with A = X'X and u a cluster's sum of x e. The third is White's, N / (N - K) * A^-1 (sum of x x' e^2)
   A^-1, when every (headline, participant) pair occurs once in the data, which is checked; otherwise it is clustered
   by the pair, as cluster2 does. The arithmetic is exact, in integers and fractions, up to the square root, so the
   outputs are the same bits on any machine.
7. The comparison with the published values the test quotes: the counts must be equal, the estimate within 0.0001,
   the standard error within 5% of the published one. test_passed is 1 if all three studies agree, else 0;
   published_matched counts the 15 values that agree.
8. Controls, each of which must fail the comparison: the veracity labels swapped (the estimate changes sign), and
   the sample without the filter on sharing political news (the counts change). controls_passed counts those that
   fail as they must. Beside them, Study 3's standard error clustered by participant alone.
9. The period the data cover, as the archive asks of a claim with a period: period_from is the earliest start date
   and period_to the latest end date (YYYYMMDD) of the participants in the three regressions, read from each file's
   start and end columns (in Study 3's file, Qualtrics's legacy names V8 and V9), dates written month/day/year with
   an optional time; anything else is refused.

What it cannot check:
- the field experiment on Twitter (Study 7), whose data are not public, and any study the test does not name: of the
  quote's "four survey experiments and a field experiment", only Studies 3 to 5 are re-run;
- Stata itself: the regressions are re-implemented, not run in Stata; agreement with the published numbers to the
  last printed digit is the evidence that they are the same;
- whether the effect would recur in new samples: this re-runs the authors' analysis on their own data.

Writes results/outputs.json (the 20 values a receipt carries, with period_from and period_to beside them) and
results/detail.json (every value computed).
"""

import csv
import hashlib
import io
import json
import math
import os
import re
import sys
from fractions import Fraction

INPUTS = (
    ("Study_3_data.csv", "7a46739ae2d7b438dd63cc2bbe50a62336e110cb7e04eaafc5209f6bcb1fe28d", 1080522),
    ("Study_4_data.csv", "d12279f11d7acddbfa78ed15abb264b6f326a90e4e9ebbf874bdbd825fe84d56", 1214839),
    ("Study_5_data.csv", "b27f831b210a5bf16f68685c7c663846b792f23037701b7ec233a12229924843", 1456678),
    ("Study_3_and_4_code.do", "feb9fb17326dc6d351fcd94f61f831e01eae4ec70719c557b4d1a90565202fab", 33816),
    ("Study_5_code.do", "a331f7313687b846c8a050dedcd2790efec352abbf2bbbaf1349e20b06f39901", 17749),
    ("cluster2.ado", "52bddc964dc5c972d8331a141a1e76741f4036325538dd02da0d65978660ae63", 5418),
)

REQUIRED = {
    "Study_3_and_4_code.do": (
        'insheet using "Study_4_data.csv", clear',
        'insheet using "Study_3_data.csv", clear',
        "gen didnt_finish=socialmedia_chk==.",
        "drop if didnt_finish==1 | fb==2",
        "rename fake*_3 fake_sm*",
        "rename real*_3 real_sm*",
        "replace sm=(sm-1)/5",
        "replace item_num=item_num+(real)*12",
        "replace item_num=item_num+24 if study==3",
        "replace condition=condition-1",
        "xi: cluster2 sm i.condition*real if socialmedia_chk==1 & study==3, tcluster(id) fcluster(item_num)",
        "xi: cluster2 sm i.condition*real if socialmedia_chk==1 & study==4, tcluster(id) fcluster(item_num)",
    ),
    "Study_5_code.do": (
        'insheet using "Study_5_data.csv", clear',
        "gen didnt_finish=socialmedia_chk==.",
        "drop if didnt_finish==1 | fb==2",
        "rename fake*_3 fake_sm*",
        "rename real*_3 real_sm*",
        "replace sm=(sm-1)/5",
        "replace item_num=item_num+(real)*10",
        "gen treatment=condition==3",
        "gen importance=condition==4",
        "xi: cluster2 sm i.treatment*real i.importance*real if socialmedia_chk==1, tcluster(id) fcluster(item_num)",
    ),
    "cluster2.ado": (
        "quietly reg `varlist' if `touse', robust cluster(`fcluster');",
        "quietly reg `varlist' if `touse', robust cluster(`tcluster');",
        "quietly reg `varlist' if `touse', robust;",
        "quietly reg `varlist' if `touse', robust cluster(bc3);",
        "matrix vc = vcf+vct-e(V);",
    ),
}

# The published values the registered test quotes: estimate, SE, observations, participants, headlines.
PUBLISHED = {3: (0.0529, 0.0108, 17417, 727, 24), 4: (0.0648, 0.0147, 18677, 780, 24), 5: (0.0542, 0.0157, 13340, 671, 20)}
STUDIES = ((3, "Study_3_data.csv", 12), (4, "Study_4_data.csv", 12), (5, "Study_5_data.csv", 10))
DATES = {3: ("v8", "v9"), 4: ("startdate", "enddate"), 5: ("startdate", "enddate")}   # start, end columns
ESTIMATE_TOL, SE_REL_TOL = 0.0001, 0.05


class Refused(Exception):
    pass


def load(inputs):
    data = {}
    for name, sha, size in INPUTS:
        path = os.path.join(inputs, name)
        with open(path, "rb") as f:
            blob = f.read()
        if len(blob) != size or hashlib.sha256(blob).hexdigest() != sha:
            raise Refused(f"{name}: {len(blob)} bytes, sha256 {hashlib.sha256(blob).hexdigest()}; not the committed input")
        data[name] = blob
    return data


def check_code(data):
    """Rule 2: every line this implementation follows, found verbatim in the authors' code and in cluster2.ado."""
    found = {}
    for name, lines in REQUIRED.items():
        have = {line.strip() for line in data[name].decode("latin-1").replace("\r", "").split("\n")}
        missing = [line for line in lines if line not in have]
        if missing:
            raise Refused(f"{name}: lines not found: {missing}")
        found[name] = len(lines)
    return found


def value(s):
    """A CSV value as Stata's destring reads it: blank is missing (None), else a number, else refused."""
    t = s.strip()
    if t == "":
        return None
    try:
        return float(t)
    except ValueError:
        raise Refused(f"value {s!r} is not a number")


def ymd(s):
    """A date written month/day/year, with an optional time after a space, as a YYYYMMDD integer."""
    m = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})( \d{1,2}:\d{2}(:\d{2})?)?", s.strip())
    if not m or not (1 <= int(m.group(1)) <= 12 and 1 <= int(m.group(2)) <= 31):
        raise Refused(f"date {s!r} is not month/day/year")
    return int(m.group(3)) * 10000 + int(m.group(1)) * 100 + int(m.group(2))


def read_csv(blob):
    text = blob.decode("utf-8-sig")
    rows = list(csv.reader(io.StringIO(text, newline="")))
    header = [h.strip().lower() for h in rows[0]]
    if len(set(header)) != len(header):
        raise Refused("duplicate column names once lowercased")
    for i, r in enumerate(rows[1:], start=2):
        if len(r) != len(header):
            raise Refused(f"row {i}: {len(r)} fields, header has {len(header)}")
    return header, rows[1:]


def observations(blob, study, items, filter_political=True):
    """Rule 4: the long rows (x-defining fields, rating, participant, headline) of one study."""
    header, rows = read_csv(blob)
    col = {h: i for i, h in enumerate(header)}
    for name in ["condition", "fb", "socialmedia_chk", *DATES[study]] + \
            [f"{s}{k}_3" for s in ("fake", "real") for k in range(1, items + 1)]:
        if name not in col:
            raise Refused(f"study {study}: no column {name}")
    out, missing_condition_kept, participants_dropped, starts, ends = [], 0, 0, [], []
    for p, r in enumerate(rows, start=1):
        chk, fb, cond = value(r[col["socialmedia_chk"]]), value(r[col["fb"]]), value(r[col["condition"]])
        if chk is None or fb == 2:
            participants_dropped += 1
            continue
        if filter_political and chk != 1:
            continue
        if cond is None:
            if study in (3, 4):
                continue                      # xi's dummy is missing, so regress drops the rows
            missing_condition_kept += 1       # Stata: condition==3 is 0 when condition is missing
        before = len(out)
        for k in range(1, items + 1):
            for real, stem in ((0, "fake"), (1, "real")):
                rating = value(r[col[f"{stem}{k}_3"]])
                if rating is None:
                    continue
                if rating != int(rating) or not 1 <= rating <= 6:
                    raise Refused(f"study {study}, participant {p}: rating {rating} outside 1..6")
                headline = k + items * real + (24 if study == 3 else 0)
                out.append({"cond": cond, "real": real, "rating": int(rating), "participant": p, "headline": headline})
        if len(out) > before:
            starts.append(ymd(r[col[DATES[study][0]]]))
            ends.append(ymd(r[col[DATES[study][1]]]))
    return out, {"participants_dropped": participants_dropped, "missing_condition_kept": missing_condition_kept,
                 "first_start": min(starts) if starts else None, "last_end": max(ends) if ends else None}


def design(rows, study, swap_veracity=False):
    """Rule 5: the regressor rows (ending with the constant) and the name of the coefficient tested."""
    xs = []
    for o in rows:
        real = 1 - o["real"] if swap_veracity else o["real"]
        if study in (3, 4):
            c = int(o["cond"]) - 1
            if c not in (0, 1):
                raise Refused(f"study {study}: condition {o['cond']}")
            xs.append((c, real, c * real, 1))
        else:
            cond = o["cond"]
            if cond is not None and cond not in (1, 2, 3, 4):
                raise Refused(f"study 5: condition {cond}")
            t, i = int(cond == 3), int(cond == 4)
            xs.append((t, real, t * real, i, i * real, 1))
    return xs, 2                                    # the product is the third regressor in both models


def inverse(a):
    """Exact inverse of a square integer matrix (Gauss-Jordan in fractions)."""
    n = len(a)
    m = [[Fraction(v) for v in row] + [Fraction(int(i == j)) for j in range(n)] for i, row in enumerate(a)]
    for c in range(n):
        p = next((r for r in range(c, n) if m[r][c] != 0), None)
        if p is None:
            raise Refused("the design is singular")
        m[c], m[p] = m[p], m[c]
        pivot = m[c][c]
        m[c] = [v / pivot for v in m[c]]
        for r in range(n):
            if r != c and m[r][c] != 0:
                f = m[r][c]
                m[r] = [v - f * w for v, w in zip(m[r], m[c])]
    return [row[n:] for row in m]


def ols_cluster2(xs, ratings, participants, headlines):
    """Rules 5 and 6: exact OLS (y = (rating - 1) / 5) and cluster2's variance; returns b, V, counts and pieces."""
    n, k = len(xs), len(xs[0])
    a = [[sum(x[i] * x[j] for x in xs) for j in range(k)] for i in range(k)]
    c = [sum(x[i] * (r - 1) for x, r in zip(xs, ratings)) for i in range(k)]          # X'y = c / 5
    ainv = inverse(a)
    b = [sum(ainv[i][j] * c[j] for j in range(k)) / 5 for i in range(k)]
    d = 5
    for v in b:
        d = d * v.denominator // math.gcd(d, v.denominator)
    big_b = [int(v * d) for v in b]
    # residual e = E / d, exactly: (r - 1) / 5 - x.b
    resid = [(r - 1) * (d // 5) - sum(xj * bj for xj, bj in zip(x, big_b)) for x, r in zip(xs, ratings)]

    def meat(labels):
        sums = {}
        for x, e, g in zip(xs, resid, labels):
            u = sums.setdefault(g, [0] * k)
            for j in range(k):
                u[j] += x[j] * e
        m = [[0] * k for _ in range(k)]
        for u in sums.values():
            for i in range(k):
                for j in range(k):
                    m[i][j] += u[i] * u[j]
        return m, len(sums)

    def sandwich(m, q):
        inner = [[Fraction(m[i][j], d * d) for j in range(k)] for i in range(k)]
        left = [[sum(ainv[i][l] * inner[l][j] for l in range(k)) for j in range(k)] for i in range(k)]
        return [[q * sum(left[i][l] * ainv[l][j] for l in range(k)) for j in range(k)] for i in range(k)]

    pairs = list(zip(headlines, participants))
    unique_pairs = len(set(pairs)) == len(pairs)
    m_h, g_h = meat(headlines)
    m_p, g_p = meat(participants)
    if unique_pairs:
        m_3, q_3 = meat(range(n))[0], Fraction(n, n - k)
    else:
        m_3, g_3 = meat(pairs)
        q_3 = Fraction(n - 1, n - k) * Fraction(g_3, g_3 - 1)
    q_h = Fraction(n - 1, n - k) * Fraction(g_h, g_h - 1)
    q_p = Fraction(n - 1, n - k) * Fraction(g_p, g_p - 1)
    v_h, v_p, v_3 = sandwich(m_h, q_h), sandwich(m_p, q_p), sandwich(m_3, q_3)
    v = [[v_h[i][j] + v_p[i][j] - v_3[i][j] for j in range(k)] for i in range(k)]
    return {"b": b, "V": v, "V_participant": v_p, "n": n, "headlines": g_h, "participants": g_p,
            "unique_pairs": unique_pairs}


def se(v, j):
    return math.sqrt(float(v[j][j]))


def agrees(study, est, s, n, participants, headlines):
    """Rule 7: (all agree, how many of the five published values agree)."""
    p_est, p_se, p_n, p_part, p_head = PUBLISHED[study]
    checks = (abs(est - p_est) <= ESTIMATE_TOL, abs(s - p_se) <= SE_REL_TOL * p_se, n == p_n, participants == p_part,
              headlines == p_head)
    return all(checks), sum(checks)


def fit(data, study, name, items, filter_political=True, swap_veracity=False):
    rows, info = observations(data[name], study, items, filter_political)
    xs, j = design(rows, study, swap_veracity)
    r = ols_cluster2(xs, [o["rating"] for o in rows], [o["participant"] for o in rows], [o["headline"] for o in rows])
    r.update(info)
    r["estimate"], r["se"] = float(r["b"][j]), se(r["V"], j)
    r["se_participant_only"] = se(r["V_participant"], j)
    return r


def run(inputs="inputs", results="results"):
    data = load(inputs)
    code = check_code(data)
    out, detail, all_ok, matched = {}, {"code_lines_found": code, "studies": {}, "controls": {}}, True, 0
    for study, name, items in STUDIES:
        r = fit(data, study, name, items)
        ok, m = agrees(study, r["estimate"], r["se"], r["n"], r["participants"], r["headlines"])
        all_ok, matched = all_ok and ok, matched + m
        out.update({f"s{study}_estimate": round(r["estimate"], 7), f"s{study}_se": round(r["se"], 7),
                    f"s{study}_n": r["n"], f"s{study}_participants": r["participants"],
                    f"s{study}_headlines": r["headlines"]})
        detail["studies"][f"s{study}"] = {
            "coefficients": [float(v) for v in r["b"]],
            "standard_errors": [se(r["V"], i) for i in range(len(r["b"]))],
            "estimate_exact": f"{r['b'][2].numerator}/{r['b'][2].denominator}",
            "se_participant_only": r["se_participant_only"], "unique_pairs": r["unique_pairs"],
            "participants_dropped": r["participants_dropped"], "missing_condition_kept": r["missing_condition_kept"],
            "first_start": r["first_start"], "last_end": r["last_end"],
            "published": PUBLISHED[study], "agrees": ok, "values_agreeing": m,
        }
    controls = {}
    for label, kwargs in (("veracity_swapped", {"swap_veracity": True}), ("all_subjects", {"filter_political": False})):
        fails = []
        for study, name, items in STUDIES:
            r = fit(data, study, name, items, **kwargs)
            ok, _ = agrees(study, r["estimate"], r["se"], r["n"], r["participants"], r["headlines"])
            fails.append(not ok)
            controls.setdefault(label, {})[f"s{study}"] = {"estimate": r["estimate"], "se": r["se"], "n": r["n"],
                                                     "participants": r["participants"], "fails": not ok}
        controls[label]["fails_everywhere"] = all(fails)
    detail["controls"] = controls
    out["published_matched"] = matched
    out["controls_passed"] = sum(1 for c in controls.values() if c["fails_everywhere"])
    out["s3_se_participant_only"] = round(detail["studies"]["s3"]["se_participant_only"], 7)
    out["unique_pairs"] = int(all(detail["studies"][f"s{s}"]["unique_pairs"] for s in PUBLISHED))
    out["test_passed"] = int(all_ok)
    out["period_from"] = min(detail["studies"][f"s{s}"]["first_start"] for s in PUBLISHED)
    out["period_to"] = max(detail["studies"][f"s{s}"]["last_end"] for s in PUBLISHED)
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
        sys.exit(f"accuracy: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
