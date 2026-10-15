#!/usr/bin/env python3
"""Horton's sets with no empty convex 7-gon (1983): the paper's sets S_k, built as its page 482 defines them, have no
three collinear points and no empty convex 7-gon, checked exactly for k = 1 to 11 (2 to 2,048 points).

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:43277d513fc8f74d) is from J. D. Horton,
"Sets with No Empty Convex 7-Gons", Canadian Mathematical Bulletin 26(4), 482-484 (1983; doi:10.4153/cmb-1983-077-8;
free to read at Cambridge Core), its abstract as Crossref prints it: "Arbitrarily large sets containing no empty convex
7-gon are constructed, showing that g(n) does not exist for n≥l." (the paper prints n ≥ 7). The test, as registered:
see TEST below. No data of record: the sets are defined by construction, so the receipt is a reproduction.

The paper's construction, read from its PDF (sha256 ab7a2454..., 243,638 bytes) before this module was written: for
any k, let a_1 a_2 ... a_k be the binary expansion of the integer i, 0 <= i < 2^k, leading 0s kept; let c = 2^k + 1
and d(i) = the sum of a_j c^(j-1) over j = 1..k; p_i = (i, d(i)); S_k = {p_i : i = 0, ..., 2^k - 1}. a_1 is the
leading digit, as the paper's observation (e) requires: halving the first coordinate while multiplying the second by
c takes the even-indexed points B onto the left half L only when the last digit carries the largest weight. The paper
calls an n-gon empty when no point of the set lies in its interior; g(n) is defined for sets with no three collinear.

Rules, fixed before this module computed anything about any S_k beyond the hand-worked S_2 of its tests:
1. S_k for k = 1 to 11, in Python's exact integers. The search runs in holes/horton.c, compiled here with the image's
   gcc, whose orientation tests are exact in signed 128-bit integers; it refuses a set whose coordinates could
   overflow them (S_11 has x < 2^11 and y < 2^111). k = 12 would not fit.
2. Three points are collinear when their orientation is 0. An empty convex m-gon is m points in convex position whose
   convex hull holds no other point of the set; with no three collinear, its interior and its closed hull hold the
   same points. Each is counted once, by its lowest vertex p (least y, then least x): around p, the points above it in
   counterclockwise order; a fan triangle (p, q_i, q_j) is empty exactly when q_j is counterclockwise of every q_l
   between them as seen from q_i; a polygon is a chain of empty fan triangles turning left at every vertex. Polygons
   of 7 or more vertices are counted together (an empty convex m-gon, m > 7, holds empty convex 7-gons).
3. The test's two conditions, each over k = 1 to 11: (1) no three points of S_k collinear; (2) no empty convex 7-gon
   (or larger) in S_k. test_passed is 1 if both hold.
4. Beside, none of it counted: for each k the counts of empty triangles, quadrilaterals, pentagons and hexagons, and
   the largest empty convex polygon; the least k whose S_k has an empty pentagon and an empty hexagon (Harborth's
   g(5) = 10 says S_4 must have the first; Heule and Scheucher's g(6) = 30, on the record as ext:4c4750ac793ed187,
   says S_5 must have the second); the paper's observation (g), every point of T above every line through two points
   of B and every point of B below every line through two points of T, for c = 2^k + 1, k = 1 to 11; and, for k = 3
   to 8, two other readings: the digits weighted the other way (a_1 the heaviest) and c = 2.

Controls (controls_passed counts those that behave as stated; the run stops if any fails): the paper's observations
(a) to (f) on every S_k (R the translate of L by (2^(k-1), 1); T the translate of B by (1, c^(k-1)); halving x and
multiplying y by c takes B onto L; the half-turn about ((2^k - 1)/2, (c^0 + ... + c^(k-1))/2) takes T onto B); a
brute-force count (every subset tested for convex position and emptiness) against the C program on 60 seed-drawn sets
of 9 to 12 points, 20 of them holding seven points in convex position with the rest kept outside their hull; a Python
transcription of rule 2, in big integers, against the C program on S_1 to S_8 and on 20 seed-drawn sets of 40
points; and the other digit order failing observation (e) for every k from 2 to 11.

What it cannot check: every k (the paper's proof covers them all; the test runs k = 1 to 11, beyond which 128-bit
arithmetic does not hold S_k's coordinates); the paper's observation (h) is not tested.

Writes results/outputs.json and results/detail.json. Run with: python3 holes/horton.py
"""

import functools
import hashlib
import itertools
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
K_MAX = 11
K_PY = 8
OTHER_READINGS = range(3, 9)
LIMIT = 200
TEST = ("Refuted if, for some k from 1 to 11, the set S_k the paper defines (the points (i, d(i)) for 0 <= i < 2^k, "
        "with d(i) the sum of a_j c^(j-1) over j = 1..k, a_1...a_k the binary expansion of i with leading 0s kept, "
        "and c = 2^k + 1) has three collinear points, or contains the vertex set of a convex 7-gon with no point of "
        "S_k in its interior, computed exactly in integer arithmetic.")
OUTPUTS = ("sets", "collinear", "empty7", "largest", "pentagons", "hexagons", "counts_11", "first", "observation_g",
           "other_order", "c_two", "conditions_met", "conditions_total", "test_passed", "controls_passed",
           "controls_total")


class Refused(Exception):
    pass


# ---------------------------------------------------------------- randomness (controls only)

class Stream:
    def __init__(self, seed, label):
        self.seed, self.label, self.n = seed, label, 0

    def below(self, m):
        self.n += 1
        h = hashlib.sha256(f"{self.seed}/{self.label}/{self.n}".encode()).digest()
        return int.from_bytes(h[:8], "big") % m


# ---------------------------------------------------------------- the paper's sets (page 482)

def digits(i, k):
    """a_1 ... a_k, the binary expansion of i with leading 0s kept (a_1 the leading digit)."""
    return [(i >> (k - j)) & 1 for j in range(1, k + 1)]


def horton(k, c=None, heavy_first=False):
    """S_k as the paper defines it; c and the digit weighting can be changed for the other readings."""
    c = 2 ** k + 1 if c is None else c
    pts = []
    for i in range(2 ** k):
        a = digits(i, k)
        if heavy_first:
            d = sum(a[j - 1] * c ** (k - j) for j in range(1, k + 1))
        else:
            d = sum(a[j - 1] * c ** (j - 1) for j in range(1, k + 1))
        pts.append((i, d))
    return pts


def observations(k, pts):
    """The paper's (a)-(f) on S_k: a dict of booleans."""
    c = 2 ** k + 1
    half = 2 ** (k - 1)
    L = set(pts[:half]) if k >= 1 else set()
    R = set(pts[half:])
    B = set(pts[0::2])
    T = set(pts[1::2])
    big = sum(c ** j for j in range(k))
    return {
        "(b) R is L moved by (2^(k-1), 1)": R == {(x + half, y + 1) for x, y in L},
        "(d) T is B moved by (1, c^(k-1))": T == {(x + 1, y + c ** (k - 1)) for x, y in B},
        "(e) halving x and multiplying y by c takes B onto L": all(x % 2 == 0 for x, _ in B)
        and {(x // 2, y * c) for x, y in B} == L,
        "(f) the half-turn about ((2^k-1)/2, sum c^j/2) takes T onto B": {(2 ** k - 1 - x, big - y) for x, y in T} == B,
    }


# ---------------------------------------------------------------- rule 2 in Python (a control on the C program)

def orient(a, b, c):
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def above(p, q):
    return q[1] > p[1] or (q[1] == p[1] and q[0] > p[0])


def count_py(points):
    """(collinear, [c3, c4, c5, c6, c7plus]) by rule 2."""
    collinear, total = 0, [0] * 5
    for p in points:
        qs = [q for q in points if q != p and above(p, q)]
        qs.sort(key=functools.cmp_to_key(lambda a, b: -1 if orient(p, a, b) > 0 else (1 if orient(p, a, b) < 0 else 0)))
        for t in range(len(qs) - 1):
            if orient(p, qs[t], qs[t + 1]) == 0:
                collinear += 1
        m = len(qs)
        out, inn = [[] for _ in range(m)], [[] for _ in range(m)]
        for i in range(m):
            best = None
            for j in range(i + 1, m):
                if best is None or orient(qs[i], qs[best], qs[j]) > 0:
                    out[i].append(j)
                    inn[j].append(i)
                    best = j
        cnt = {}
        for i in range(m):
            for j in out[i]:
                c = [1, 0, 0, 0, 0]
                for h in inn[i]:
                    if orient(qs[h], qs[i], qs[j]) > 0:
                        f = cnt[(h, i)]
                        c[1] += f[0]
                        c[2] += f[1]
                        c[3] += f[2]
                        c[4] += f[3] + f[4]
                cnt[(i, j)] = c
                for L in range(5):
                    total[L] += c[L]
    return collinear, total


# ---------------------------------------------------------------- brute force (a control)

def hull(pts):
    """Strict convex hull, counterclockwise (Andrew's monotone chain)."""
    pts = sorted(pts)
    if len(pts) < 3:
        return pts
    lower, upper = [], []
    for p in pts:
        while len(lower) >= 2 and orient(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    for p in reversed(pts):
        while len(upper) >= 2 and orient(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


def brute(points):
    """[c3, c4, c5, c6, c7plus] by testing every subset."""
    total = [0] * 5
    n = len(points)
    for r in range(3, n + 1):
        for sub in itertools.combinations(points, r):
            h = hull(sub)
            if len(h) != r:
                continue
            rest = [q for q in points if q not in sub]
            if any(all(orient(h[t], h[(t + 1) % r], q) > 0 for t in range(r)) for q in rest):
                continue
            total[min(r, 7) - 3] += 1
    return total


def general(points):
    return all(orient(a, b, c) != 0 for a, b, c in itertools.combinations(points, 3))


def random_set(stream, n, convex7=False):
    while True:
        pts = set()
        if convex7:
            ts = set()
            while len(ts) < 7:
                ts.add(stream.below(2001) - 1000)
            pts = {(t, t * t) for t in ts}
            top = max(y for _, y in pts)
            while len(pts) < n:
                pts.add((stream.below(4001) - 2000, top + 1 + stream.below(1 << 20)))
        else:
            while len(pts) < n:
                pts.add((stream.below(1 << 20), stream.below(1 << 20)))
        pts = sorted(pts)
        if general(pts):
            return pts


# ---------------------------------------------------------------- the C program

def build(work):
    exe = os.path.join(work, "horton")
    subprocess.run(["gcc", "-O2", "-std=gnu11", "-o", exe, os.path.join(HERE, "horton.c")], check=True)
    return exe


def c_run(exe, work, mode, points):
    path = os.path.join(work, "points.txt")
    with open(path, "w", encoding="ascii") as fh:
        fh.write(f"{len(points)}\n")
        for x, y in points:
            fh.write(f"{x} {y}\n")
    out = subprocess.run([exe, mode, path], check=True, capture_output=True, text=True).stdout.split("\n")
    vals = {}
    for line in out:
        if line.strip():
            key, *rest = line.split()
            vals[key] = [int(v) for v in rest]
    return vals


def count_c(exe, work, points):
    v = c_run(exe, work, "count", points)
    return v["collinear"][0], v["counts"], v["work"][0]


# ---------------------------------------------------------------- the run

def run(seed, results="results"):
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        raise Refused("the seed must be 64 hex characters")
    if shutil.which("gcc") is None:
        raise Refused("no gcc in this image")
    os.makedirs(results, exist_ok=True)
    work = tempfile.mkdtemp(prefix="work-", dir=results)
    try:
        exe = build(work)
        return _run(seed, results, exe, work)
    finally:
        shutil.rmtree(work, ignore_errors=True)


def _run(seed, results, exe, work):
    ctl = {}
    sets = {k: horton(k) for k in range(1, K_MAX + 1)}
    obs = {k: observations(k, sets[k]) for k in range(1, K_MAX + 1)}
    ctl["the paper's observations (b), (d), (e) and (f) hold on S_1 to S_11"] = all(
        all(v.values()) for v in obs.values())
    ctl["the other digit order fails observation (e) for every k from 2 to 11"] = all(
        not observations(k, horton(k, heavy_first=True))["(e) halving x and multiplying y by c takes B onto L"]
        for k in range(2, K_MAX + 1))

    stream = Stream(seed, "horton/small")
    small = [random_set(stream, 9 + stream.below(4), convex7=(t % 3 == 0)) for t in range(60)]
    agree, planted7 = True, 0
    for t, pts in enumerate(small):
        b = brute(pts)
        col, cnt, _ = count_c(exe, work, pts)
        _, cpy = count_py(pts)
        agree = agree and col == 0 and cnt == b and cpy == b
        if t % 3 == 0:
            planted7 += b[4] > 0
    ctl["brute force, the C program and the Python counting agree on 60 seed-drawn sets of 9 to 12 points, and all "
        "20 with seven points placed in convex position have an empty 7-gon"] = agree and planted7 == 20

    stream = Stream(seed, "horton/forty")
    forty = [random_set(stream, 40) for _ in range(20)]
    agree_mid = all(count_c(exe, work, pts)[:2] == count_py(pts) for pts in forty)
    agree_s = {}
    for k in range(1, K_PY + 1):
        agree_s[k] = count_c(exe, work, sets[k])[:2] == count_py(sets[k])
    ctl["the Python counting equals the C program's on S_1 to S_8 and on 20 seed-drawn sets of 40 points"] = (
        agree_mid and all(agree_s.values()))

    if not all(ctl.values()):
        raise AssertionError(f"a control failed: {[k for k, v in ctl.items() if not v]}")

    rows = {}
    for k in range(1, K_MAX + 1):
        col, cnt, w = count_c(exe, work, sets[k])
        g = c_run(exe, work, "above", sets[k])["above"] if k >= 2 else [0, 0]
        largest = max([L + 3 for L in range(5) if cnt[L] > 0], default=len(sets[k]) if len(sets[k]) < 3 else 0)
        rows[k] = {"points": len(sets[k]), "collinear": col, "counts": cnt, "largest": largest, "g": g, "work": w}
    other = {}
    for k in OTHER_READINGS:
        col1, cnt1, _ = count_c(exe, work, horton(k, heavy_first=True))
        col2, cnt2, _ = count_c(exe, work, horton(k, c=2))
        other[k] = {"heavy_first": [col1, cnt1[4]], "c2": [col2, cnt2[4]]}

    cond = {
        "no three points of S_k collinear, k = 1 to 11": all(r["collinear"] == 0 for r in rows.values()),
        "no empty convex 7-gon or larger in S_k, k = 1 to 11": all(r["counts"][4] == 0 for r in rows.values()),
    }
    ks = range(1, K_MAX + 1)
    first5 = next((k for k in ks if rows[k]["counts"][2] > 0), None)
    first6 = next((k for k in ks if rows[k]["counts"][3] > 0), None)
    g_bad = [k for k in ks if rows[k]["g"] != [0, 0]]
    lab = lambda xs: ", ".join(str(x) for x in xs)
    r11 = rows[K_MAX]["counts"]
    values_out = {
        "sets": (f"S_1 to S_{K_MAX}: {lab(rows[k]['points'] for k in ks)} points; largest y in S_{K_MAX} has "
                 f"{len(str(max(y for _, y in sets[K_MAX])))} digits"),
        "collinear": ("collinear triples: " + ("none in S_1 to S_11" if cond[
            "no three points of S_k collinear, k = 1 to 11"] else
            "in " + lab(f"S_{k}" for k in ks if rows[k]["collinear"]))),
        "empty7": "empty convex 7-gons or larger, S_1 to S_11: " + lab(rows[k]["counts"][4] for k in ks),
        "largest": "largest empty convex polygon, S_1 to S_11: " + lab(rows[k]["largest"] for k in ks),
        "pentagons": "empty pentagons, S_1 to S_11: " + lab(rows[k]["counts"][2] for k in ks),
        "hexagons": "empty hexagons, S_1 to S_11: " + lab(rows[k]["counts"][3] for k in ks),
        "counts_11": (f"S_{K_MAX}: empty triangles {r11[0]}, quadrilaterals {r11[1]}, pentagons {r11[2]}, hexagons "
                      f"{r11[3]}"),
        "first": (f"least k with an empty pentagon: {first5}; with an empty hexagon: {first6} "
                  f"(g(5) = 10 and g(6) = 30 require 4 and 5 at most)"),
        "observation_g": ("(g) with c = 2^k + 1: " + ("holds for k = 1 to 11" if not g_bad else
                          "fails for k = " + lab(g_bad))),
        "other_order": ("a_1 heaviest, k = 3 to 8: collinear " + lab(other[k]["heavy_first"][0] for k in OTHER_READINGS)
                        + "; empty 7-gons or larger " + lab(other[k]["heavy_first"][1] for k in OTHER_READINGS)),
        "c_two": ("c = 2, k = 3 to 8: collinear " + lab(other[k]["c2"][0] for k in OTHER_READINGS)
                  + "; empty 7-gons or larger " + lab(other[k]["c2"][1] for k in OTHER_READINGS)),
        "conditions_met": sum(cond.values()), "conditions_total": len(cond), "test_passed": int(all(cond.values())),
        "controls_passed": sum(ctl.values()), "controls_total": len(ctl),
    }
    out = {k: values_out[k] for k in OUTPUTS}
    for k, v in out.items():
        if isinstance(v, str) and len(v) > LIMIT:
            raise AssertionError(f"{k}: longer than {LIMIT} characters: {v}")
    detail = {"test": TEST, "conditions": cond, "controls": ctl, "rows": {str(k): rows[k] for k in ks},
              "observations": {str(k): obs[k] for k in ks}, "other_readings": {str(k): other[k] for k in other},
              "python_agrees_on_S_k": {str(k): v for k, v in agree_s.items()}}
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
        sys.exit(f"horton: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
