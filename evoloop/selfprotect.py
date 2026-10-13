#!/usr/bin/env python3
"""Sayama's self-protecting evoloops: does protecting a loop from attack keep the population's sizes diverse?

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:10b8167c671aaa9f) is from Sayama,
"Self-Protection and Diversity in Self-Replicating Cellular Automata", Artificial Life 10(1), 83-98 (2004):
"Simulation results imply a positive effect of those mechanisms on diversity maintenance, especially when the
self-protection is moderate so that it conserves both the attacker and the attacked."

Its registered test: refuted if, under the paper's own rules (Appendix A: Tables 2 to 6 and their steps), from the
size-13 ancestor (genome 774477777777777) alone in a 400 x 400 periodic space for 1,000,000 updates, loops counted by
size and the trait-distribution entropy sampled every 40 updates from 200,000 to 1,000,000: the mean entropy of any of
the shielded, deflecting and poisoning SP evoloops is not above the original evoloop's; or, from the ancestor
777777777777744, the deflecting one's is not above the original's, or the poisoning one's is above the deflecting
one's.

The paper prints its models in full. Tables 3 to 7 below are transcribed from the author's copy (bingweb.binghamton.
edu/~sayama/papers/ALIFE10-1-83.pdf, SHA-256 43b09426...29d0d), as three PDF readers (poppler, pdfminer and pypdf)
extract them alike, and hashed; Table 2 is evoloop/check.py's, whose hash the same extraction gives. The evoloop is
deterministic, so nothing here is random but the choice of the census control's grids, which the seed draws.

1. The rules, each model's table over ten states (0 to 9) and von Neumann neighbours, built as Appendix A says.
   Every CTRBL->I of a table defines the site's image when it is in state C with T, R, B and L above, right of,
   below and left of it, and so do its rotations (TRBL turned round together); a situation given two images is
   refused. The original (A.1): Table 2; then 8 -> 0 with no condition; then, for situations still undefined with a
   state 8 among the four neighbours, 0 and 1 -> 8 if a state 2 to 7 is among them, else unchanged, 2, 3, 5 -> 0 and
   4, 6, 7 -> 1; then every other undefined situation 0 -> 0 and 1 to 7 -> 8 (state 9 does not occur in it: its
   situations with a 9 at the centre are given 0 and never met). Shielded and deflecting (A.2.1): Tables 2 and 3,
   then Table 4 (shielded) or Table 5 (deflecting); then 8 -> 0; then, undefined with an 8 among the neighbours,
   0 and 1 -> 8 if a 2 to 7 is among them, else unchanged, 2, 3, 5, 9 -> 0 and 4, 6, 7 -> 1; then 0 -> 0 and 1 to 7
   and 9 -> 8. Poisoning (A.2.2): Tables 2, 3 and 6; then 8 -> 0; then 9 -> 0 wherever the centre is 9; then,
   undefined with a 9 among the neighbours, 0 -> 0 and 1 to 8 -> 9; then, still undefined with an 8 among them, as
   A.1's step 3; then 0 -> 0 and 1 to 7 -> 8. Table 7 (the paper's variation of the rules) is transcribed but not
   run.
2. The ancestors: A, Golly's rle of the evoloop's ancestor (as evoloop/check.py reads it: size 13, genome
   774477777777777); B, the same loop built in that layout (evoloop/check.py's build) with the genome
   777777777777744, the paper's other ancestor, which is A's cycle of genes read from its fifth gene. Each is placed
   alone with its top-left corner at ((400 - 17) // 2, (400 - 17) // 2) in a 400 x 400 torus.
3. The runs: the four models from each ancestor, 1,000,000 updates each, in C (evoloop/sp.c, compiled here with the
   image's gcc; integer arithmetic only), two at a time.
4. The census, every 1,000 updates and every 40 after update 200,000: evoloop/check.py's, in C. A loop is counted by
   its hole, a 4-connected region of state 0 on the torus of at most 400 sites that fills a rectangle whose
   surrounding ring, corners included, is all sheath (states 2 and 3). A square hole of side h is a loop of size
   h + 2; other rectangles are variants and not counted as loops.
5. The entropy at each census: H = log N - (1/N) sum_i n_i log n_i over the sizes i, with n_i loops of size i and N
   their total (natural logarithms; H = 0 when N is 0); its mean over the 20,000 censuses at updates 200,040 to
   1,000,000.
6. The test's three conditions: from A, each SP model's mean H strictly above the original's; from B, the deflecting
   one's strictly above the original's; from B, the poisoning one's not above the deflecting one's. test_passed is 1
   if all three hold.
7. Beside the test, none of it counted: the shielded model from B; the same means with the attack detector also
   counted as sheath (9 for shielded and deflecting, 8 for poisoning); the means over each half of the window; the
   share of the 20,000 censuses at which each SP model's H exceeds the original's; the census at the end; the first
   update at which each SP model departs from the original from A.

Controls (controls_passed counts those that behave as stated): each table's transcription is the one this module was
written with (else it refuses); the original's table, on states 0 to 8, equals evoloop/check.py's Sayama rules
exactly; every SP table gives every situation that Table 2 and its rotations define the original's image (the paper:
"the transition rules explicitly defined in the original evoloop are all inherited as is"); every table leaves the
quiescent state alone; the C update equals a numpy update site for site, for all four models from both ancestors in
tori of 60 and 100 sites a side over 2,000 updates; the C census equals evoloop/check.py's census, loops and variants,
on two seed-drawn grids and the last of every run, with both sheath sets; ancestor A built equals the rle site for
site, and B reads back as 777777777777744; B alone (in a torus of 170 sites a side, under the original's rules) gives
its first offspring, a loop of size 13, with nothing else counted before it; the SP models leave A's development
unchanged through its first offspring (no departure from the original before update 400); every run's window holds
20,000 censuses.

What it cannot check: the paper's own runs (the evoloop is deterministic, so under the same rules from the same
ancestor a run is the same trajectory, but the paper prints only its figures); the paper's own census, which it takes
"using the method proposed in [11]" (Sayama 1999), here evoloop/check.py's; the two other variations of Figure 8
(Table 7's rules, with either ancestor); and why any difference arises: the receipt measures the entropy, not the
mechanism.

Writes results/outputs.json (the values a receipt carries) and results/detail.json (every 1,000-update census of every
run, and the controls). Run with: python3 evoloop/selfprotect.py
"""

import concurrent.futures as cf
import hashlib
import importlib.util
import json
import math
import os
import random
import re
import shutil
import subprocess
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("evoloop_check", os.path.join(HERE, "check.py"))
E = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = E
_spec.loader.exec_module(E)
Refused = E.Refused

Q = 10
L = 400
UPDATES = 1_000_000
WINDOW_FROM = 200_000
SAMPLE = 40
EVERY = 1000
WINDOW_N = (UPDATES - WINDOW_FROM) // SAMPLE
NBINS = 20                                   # sizes 3 to 22, as evoloop/sp.c counts them
MIN_SIZE = 3
GENOME_A = "774477777777777"
GENOME_B = "777777777777744"
MODELS = ("original", "shielded", "deflecting", "poisoning")
SP = MODELS[1:]
PATCH = {"shielded": 4, "deflecting": 5, "poisoning": 6}
DETECTOR = {"original": -1, "shielded": 9, "deflecting": 9, "poisoning": 8}
SMALL = ((60, 2000), (100, 2000))
DIVERGE_LIMIT = 1500
OFFSPRING_BY = 400
LIMIT = 200
OUTPUTS = ("rules", "variant_alone", "H_original_A", "H_shielded_A", "H_deflecting_A", "H_poisoning_A",
           "H_original_B", "H_shielded_B", "H_deflecting_B", "H_poisoning_B", "above_original_A",
           "deflecting_above_B", "poisoning_not_above_B", "end_A", "end_B", "beside", "controls_passed",
           "controls_total", "test_passed")

# Tables 3 to 7 of Sayama (2004), CTRBL->I, sorted; each hash is of its tokens joined by single spaces.
TABLES = {
    3: ("""
01243->1 01273->1 01443->1 01773->1 10031->1 10034->4 10312->1 10342->4 11113->1 11134->4
11137->7 11342->4 11372->7 20132->2 20231->2 20234->2 20237->2 20432->2 20732->2 30202->3
40113->0 40213->0 70113->0 70213->0
""", "f10323172b552556e4dd9a863ae0d539b0a5751c1f96b4881a1ac4f59c900a02", 24),
    4: ("""
00208->0 01249->1 01279->1 01292->1 01449->1 01779->1 01792->1 01922->1 10029->7 10037->9
10091->1 10094->4 10097->7 10229->7 10292->7 10372->9 10912->1 10942->4 10972->7 11119->1
11194->4 11197->7 11219->1 11942->4 11972->7 20029->2 20092->2 20192->2 20229->2 20291->2
20292->2 20294->2 20297->2 20492->2 20792->2 20922->2 21229->2 21922->2 22249->2 22279->2
22294->2 22297->2 30292->9 31292->9 32429->9 32729->9 40119->0 40219->0 70119->0 70219->0
90113->0 90202->9 90212->9 90213->0 90242->9 90272->9 90282->2 91212->9 91242->9 91272->9
91282->2 92424->9 92427->9 92428->2 92727->9 92728->2
""", "09916dde11275cb6229a2bfc9797e2e4a0c671de1f828d35728c84bdd23afc67", 66),
    5: ("""
01246->1 01276->1 01292->1 01446->1 01776->1 01792->1 01922->1 10029->7 10037->9 10061->1
10064->4 10067->7 10229->7 10292->7 10372->9 10612->1 10642->4 10672->7 11116->1 11164->4
11167->7 11216->1 11642->4 11672->7 20162->2 20226->2 20261->2 20264->2 20267->2 20292->2
20462->2 20762->2 20922->2 21229->2 21262->2 22246->2 22264->2 22267->2 22276->2 30292->6
31292->6 32429->6 32729->6 40116->0 40216->0 70116->0 70216->0 90113->0 90213->0
""", "c41595e0c8ab1e0e18c76804356fe819312353e3ca925b038245197197eb0960", 49),
    6: ("""
01279->1 01282->1 01292->9 01779->1 01782->1 01822->1 10028->7 10037->8 10228->7 10282->7
10372->8 20192->2 20282->2 20292->0 20297->2 20822->2 21228->2 21292->2 21922->2 22297->2
30282->9 31282->9 32428->9 32728->9 90202->2 90212->2 90242->2 90272->2
""", "ed14be104f7dc63d1431530fb174dbfb40dbad325961534fcabce17cf059c096", 28),
    7: ("""
00233->3 20033->2 20133->2 20204->3 20332->2 20433->2 20733->2 21332->2 22433->2 22733->2
30213->2 30312->2
""", "be3b0342baf3b8f3e3c5500af0fe6f8f649e8bcb3bd3ad82e2d8af2e960e9fa1", 12),
}


# ---------------------------------------------------------------- the rules (rule 1)

def table_rules(k):
    text, sha, count = TABLES[k]
    toks = text.split()
    if len(toks) != count or hashlib.sha256(" ".join(toks).encode()).hexdigest() != sha:
        raise Refused(f"Table {k}: not the transcription this module was written with")
    out = []
    for tok in toks:
        m = re.fullmatch(r"([0-9])([0-9])([0-9])([0-9])([0-9])->([0-9])", tok)
        if not m:
            raise Refused(f"Table {k}: {tok}")
        out.append(tuple(int(x) for x in m.groups()))
    return out


def define(t, rules, what):
    for c, n, e, s, w, out in rules:
        for nb in E.turns(n, e, s, w):
            key = (c,) + nb
            if t[key] >= 0 and t[key] != out:
                raise Refused(f"{what}: two images for {c}{''.join(map(str, nb))}")
            t[key] = out


def table2_mask():
    """The situations Table 2 and its rotations define."""
    m = np.zeros((Q,) * 5, dtype=bool)
    for c, n, e, s, w, _ in E.table2_rules():
        for nb in E.turns(n, e, s, w):
            m[(c,) + nb] = True
    return m


def build_rules(model):
    """Rule 1: a model's table, (10,)*5 of uint8, and the situations its tables define."""
    t = -np.ones((Q,) * 5, dtype=np.int16)
    define(t, E.table2_rules(), "Table 2")
    if model != "original":
        define(t, table_rules(3), "Table 3")
        define(t, table_rules(PATCH[model]), f"Table {PATCH[model]}")
    defined = t >= 0
    c, n, e, s, w = np.indices((Q,) * 5)

    def among(states):
        m = np.zeros(t.shape, dtype=bool)
        for x in (n, e, s, w):
            m |= np.isin(x, states)
        return m

    live = among(range(2, 8))

    def dissolve_step(to_zero):                      # A.1 step 3, A.2.1 step 4, A.2.2 step 5
        und = (t < 0) & among([8])
        t[und & (c <= 1) & live] = 8
        keep = und & (c <= 1) & ~live
        t[keep] = c[keep]
        t[und & np.isin(c, to_zero)] = 0
        t[und & np.isin(c, (4, 6, 7))] = 1

    t[(t < 0) & (c == 8)] = 0                        # 8 -> 0 with no condition
    if model == "poisoning":
        t[(t < 0) & (c == 9)] = 0                    # A.2.2 step 3
        und = (t < 0) & among([9])                   # A.2.2 step 4
        t[und & (c == 0)] = 0
        t[und & (c >= 1) & (c <= 8)] = 9
        dissolve_step((2, 3, 5))
        rest = t < 0
        t[rest & (c == 0)] = 0
        t[rest & (c >= 1) & (c <= 7)] = 8
    elif model == "original":
        dissolve_step((2, 3, 5))
        rest = t < 0
        t[rest & (c == 0)] = 0
        t[rest & (c >= 1) & (c <= 7)] = 8
        t[(t < 0) & (c == 9)] = 0                    # no state 9 in the original: never met
    else:
        dissolve_step((2, 3, 5, 9))
        rest = t < 0
        t[rest & (c == 0)] = 0
        t[rest & (((c >= 1) & (c <= 7)) | (c == 9))] = 8
    if (t < 0).any() or (t >= Q).any():
        raise Refused(f"{model}: a situation without one image")
    return t.astype(np.uint8), defined


def step(g, flat):
    """One update under a ten-state table (flat: the table raveled); north is the row above."""
    idx = g.astype(np.int32) * Q + np.roll(g, 1, 0)
    idx = idx * Q + np.roll(g, -1, 1)
    idx = idx * Q + np.roll(g, -1, 0)
    idx = idx * Q + np.roll(g, 1, 1)
    return flat[idx]


# ---------------------------------------------------------------- the runs, in C (rule 3)

RECORD = np.dtype([("t", "<i4"), ("live", "<i4"), ("c1", "<u2", (NBINS + 1,)), ("c2", "<u2", (NBINS + 1,))])


def compile_sp(work):
    exe = os.path.join(work, "sp")
    subprocess.run(["gcc", "-O2", "-o", exe, os.path.join(HERE, "sp.c")], check=True)
    return exe


def run_c(exe, work, name, table, grid, updates, detector, snaps=(), window_from=WINDOW_FROM):
    tab = os.path.join(work, f"{name}.table")
    gp = os.path.join(work, f"{name}.grid")
    out = os.path.join(work, f"{name}.rec")
    table.astype(np.uint8).ravel().tofile(tab)
    grid.astype(np.uint8).tofile(gp)
    subprocess.run([exe, tab, gp, str(grid.shape[0]), str(updates), str(window_from), str(detector), out]
                   + [str(s) for s in snaps], check=True)
    rec = np.fromfile(out, dtype=RECORD)
    shots = {}
    for s in snaps:
        shots[s] = np.fromfile(f"{out}.{s}", dtype=np.uint8).reshape(grid.shape)
        os.remove(f"{out}.{s}")
    for p in (tab, gp, out):
        os.remove(p)
    return rec, shots


def entropy(counts):
    """Rule 5, for one census: counts of sizes 3 to 22."""
    n = counts[:NBINS].astype(np.float64)
    N = n.sum()
    if N <= 0:
        return 0.0
    nz = n[n > 0]
    return math.log(N) - float((nz * np.log(nz)).sum()) / N


def loops_of(counts):
    return {MIN_SIZE + i: int(v) for i, v in enumerate(counts[:NBINS]) if v}


def summarise(rec, window_from=WINDOW_FROM, updates=UPDATES):
    H1 = np.array([entropy(r) for r in rec["c1"]])
    H2 = np.array([entropy(r) for r in rec["c2"]])
    t = rec["t"]
    win = (t > window_from) & (t % SAMPLE == 0)
    first = win & (t <= (window_from + updates) // 2)
    second = win & (t > (window_from + updates) // 2)
    N = rec["c1"][:, :NBINS].sum(axis=1)
    sizes = np.arange(MIN_SIZE, MIN_SIZE + NBINS)
    with np.errstate(invalid="ignore", divide="ignore"):
        mean_size = (rec["c1"][:, :NBINS] * sizes).sum(axis=1) / N
    series = [{"t": int(t[i]), "live": int(rec["live"][i]), "loops": {str(k): v for k, v in loops_of(rec["c1"][i]).items()},
               "variants": int(rec["c1"][i][NBINS]), "H": round(float(H1[i]), 6)}
              for i in range(len(t)) if t[i] % EVERY == 0]
    return {"window_censuses": int(win.sum()), "mean_H": float(H1[win].mean()) if win.any() else None,
            "mean_H_detector": float(H2[win].mean()) if win.any() else None,
            "mean_H_first_half": float(H1[first].mean()) if first.any() else None,
            "mean_H_second_half": float(H1[second].mean()) if second.any() else None,
            "mean_N": float(N[win].mean()) if win.any() else None,
            "mean_size": float(np.nanmean(mean_size[win])) if win.any() else None,
            "H_window": H1[win], "end": {"t": int(t[-1]), "loops": loops_of(rec["c1"][-1]),
                                         "variants": int(rec["c1"][-1][NBINS])},
            "series": series}


def census_record(rec, t):
    i = int(np.nonzero(rec["t"] == t)[0][0])
    return ({"loops": loops_of(rec["c1"][i]), "variants": int(rec["c1"][i][NBINS])},
            {"loops": loops_of(rec["c2"][i]), "variants": int(rec["c2"][i][NBINS])})


def py_census(grid, sheath):
    old = E.SHEATH
    try:
        E.SHEATH = sheath
        loops, variants = E.census(grid)
    finally:
        E.SHEATH = old
    return {"loops": {int(k): int(v) for k, v in loops.items()}, "variants": int(variants)}


# ---------------------------------------------------------------- controls

def alone_pattern(pattern, n, flat9, limit=E.ALONE_LIMIT):
    """evoloop/check.py's alone(), for a given loop: the update of its first offspring, and anything else counted."""
    g = E.place(pattern, 10 * (n + 4))
    seen, births, other = 1, [], []
    for t in range(1, limit + 1):
        g = E.step(g, flat9)
        loops, variants = E.census(g)
        if variants or any(s != n for s in loops):
            other.append({"t": t, "loops": {str(k): v for k, v in loops.items()}, "variants": variants})
        k = loops.get(n, 0)
        if k > seen:
            births.extend([t] * (k - seen))
            seen = k
        if seen >= 2:
            break
    first = births[0] if births else None
    faithful = first is not None and not any(o["t"] <= first for o in other)
    return {"first": first, "faithful": faithful, "other": other[:5]}


def first_divergence(a0, tables, limit=DIVERGE_LIMIT):
    """The first update at which each SP model's grid departs from the original's, from the same start."""
    grids = {m: a0.copy() for m in MODELS}
    flats = {m: tables[m].ravel() for m in MODELS}
    out = {m: None for m in SP}
    for t in range(1, limit + 1):
        for m in MODELS:
            if m == "original" or out[m] is None:
                grids[m] = step(grids[m], flats[m])
        for m in SP:
            if out[m] is None and not np.array_equal(grids[m], grids["original"]):
                out[m] = t
        if all(v is not None for v in out.values()):
            break
    return out


# ---------------------------------------------------------------- the verdict

def conditions(H):
    return {"from 774477777777777, each SP evoloop's mean entropy above the original's":
            all(H[(m, "A")] > H[("original", "A")] for m in SP),
            "from 777777777777744, the deflecting one's above the original's":
            H[("deflecting", "B")] > H[("original", "B")],
            "from 777777777777744, the poisoning one's not above the deflecting one's":
            H[("poisoning", "B")] <= H[("deflecting", "B")]}


def describe(end):
    loops = end["loops"]
    total = sum(loops.values())
    ranked = sorted(loops.items(), key=lambda x: (-x[1], x[0]))
    parts = ", ".join(f"{s}: {v}" for s, v in ranked[:3])
    return f"{total} ({parts or 'none'})"


def run(seed, inputs="inputs", results="results", updates=UPDATES, window_from=WINDOW_FROM, workers=2, small=SMALL):
    t_start = time.time()
    rle_text = E.load(inputs, "Evoloop.rle")
    ancestor_a = E.read_rle(rle_text)
    ancestor_b = E.build(E.ANCESTOR, GENOME_B)
    tables, defined = {}, {}
    for m in MODELS:
        tables[m], defined[m] = build_rules(m)
    sayama9, _ = E.sayama_rules()
    t2 = table2_mask()
    rng = random.Random(int(seed, 16))

    ctl = {}
    ctl["each table's transcription is the one this module was written with"] = all(
        len(table_rules(k)) == TABLES[k][2] for k in TABLES) and len(E.table2_rules()) == E.TABLE2_COUNT
    ctl["the original's table on states 0 to 8 equals evoloop/check.py's Sayama rules"] = bool(
        np.array_equal(tables["original"][:9, :9, :9, :9, :9], sayama9))
    ctl["every SP table keeps the original's image wherever Table 2 defines one"] = all(
        np.array_equal(tables[m][t2], tables["original"][t2]) for m in SP)
    ctl["every table leaves the quiescent state alone"] = all(int(tables[m][0, 0, 0, 0, 0]) == 0 for m in MODELS)
    ctl["ancestor A built equals the rle, site for site"] = bool(np.array_equal(E.build(E.ANCESTOR), ancestor_a))
    ctl["ancestor A reads 774477777777777 and B 777777777777744"] = (
        E.genome_of(ancestor_a, E.ANCESTOR) == GENOME_A and E.genome_of(ancestor_b, E.ANCESTOR) == GENOME_B)

    os.makedirs(results, exist_ok=True)
    work = os.path.join(results, "work")
    shutil.rmtree(work, ignore_errors=True)
    os.makedirs(work)
    exe = compile_sp(work)

    # the C update against numpy, in small tori
    agree, compared = 0, []
    for m in MODELS:
        for an, pat in (("A", ancestor_a), ("B", ancestor_b)):
            for size, steps in small:
                g0 = E.place(pat, size)
                _, shots = run_c(exe, work, f"small_{m}_{an}_{size}", tables[m], g0, steps, DETECTOR[m], (steps,))
                g = g0
                flat = tables[m].ravel()
                for _ in range(steps):
                    g = step(g, flat)
                same = bool(np.array_equal(g, shots[steps]))
                agree += same
                compared.append({"model": m, "ancestor": an, "L": size, "updates": steps, "equal": same,
                                 "live": int(np.count_nonzero(g))})
    ctl["the C update equals numpy's, site for site, in every small torus"] = agree == len(compared)

    # the eight runs
    window_times = list(range(window_from + SAMPLE, updates + 1, SAMPLE))
    jobs = []
    for an, pat in (("A", ancestor_a), ("B", ancestor_b)):
        for m in MODELS:
            drawn = sorted(rng.sample(window_times, 2)) if len(window_times) >= 2 else []
            jobs.append((m, an, pat, drawn))

    def one(job):
        m, an, pat, drawn = job
        t0 = time.time()
        rec, shots = run_c(exe, work, f"run_{m}_{an}", tables[m], E.place(pat, L), updates, DETECTOR[m],
                           tuple(drawn) + (updates,), window_from)
        return (m, an), rec, shots, round(time.time() - t0, 1)

    with cf.ThreadPoolExecutor(workers) as pool:
        done = list(pool.map(one, jobs))

    runs, census_checks = {}, []
    for key, rec, shots, secs in done:
        m, an = key
        s = summarise(rec, window_from, updates)
        s["seconds"] = secs
        runs[key] = s
        for t, grid in sorted(shots.items()):
            c1, c2 = census_record(rec, t)
            p1 = py_census(grid, (2, 3))
            p2 = py_census(grid, (2, 3) + ((DETECTOR[m],) if DETECTOR[m] >= 0 else ()))
            census_checks.append({"model": m, "ancestor": an, "t": t, "equal": c1 == p1 and c2 == p2,
                                  "c": c1, "check_py": p1})
    ctl["the C census equals evoloop/check.py's on the drawn grids and the last, with both sheath sets"] = all(
        c["equal"] for c in census_checks) and len(census_checks) == 3 * len(jobs)
    ctl["every run's window holds 20,000 censuses"] = all(
        runs[k]["window_censuses"] == len(window_times) for k in runs) and (
        len(window_times) == WINDOW_N or (updates, window_from) != (UPDATES, WINDOW_FROM))
    shutil.rmtree(work, ignore_errors=True)

    # alone, and the departure from the original
    flat9 = sayama9.ravel()
    lone_b = alone_pattern(ancestor_b, E.ANCESTOR, flat9)
    lone_a = alone_pattern(ancestor_a, E.ANCESTOR, flat9)
    ctl["B alone gives its first offspring, a loop of size 13, with nothing else counted before it"] = bool(
        lone_b["faithful"])
    diverge = first_divergence(E.place(ancestor_a, L), tables)
    ctl["the SP models leave A's development unchanged through its first offspring"] = all(
        v is None or v > OFFSPRING_BY for v in diverge.values()) and lone_a["first"] is not None and \
        lone_a["first"] < OFFSPRING_BY

    H = {k: runs[k]["mean_H"] for k in runs}
    cond = conditions(H)
    paired = {}
    for an in "AB":
        base = runs[("original", an)]["H_window"]
        for m in SP:
            paired[f"{m}_{an}"] = round(float((runs[(m, an)]["H_window"] > base).mean()), 4)

    def r6(x):
        return round(x, 6) if x is not None else None

    values = {
        "rules": ("Tables 2 to 6: 258, 24, 66, 49, 28 rules; situations defined with rotations: "
                  + ", ".join(f"{m} {int(defined[m].sum())}" for m in MODELS)),
        "variant_alone": (f"777777777777744 alone: first offspring at {lone_b['first']} updates"
                          f"{', faithful' if lone_b['faithful'] else ', not faithful'}; 774477777777777 at "
                          f"{lone_a['first']}"),
        "above_original_A": sum(1 for m in SP if H[(m, "A")] > H[("original", "A")]),
        "deflecting_above_B": int(H[("deflecting", "B")] > H[("original", "B")]),
        "poisoning_not_above_B": int(H[("poisoning", "B")] <= H[("deflecting", "B")]),
        "end_A": "; ".join(f"{m[:4]} {describe(runs[(m, 'A')]['end'])}" for m in MODELS),
        "end_B": "; ".join(f"{m[:4]} {describe(runs[(m, 'B')]['end'])}" for m in MODELS),
        "beside": ("detector as sheath, A: " + ", ".join(f"{m[:4]} {runs[(m, 'A')]['mean_H_detector']:.4f}"
                                                         for m in MODELS)
                   + "; B: " + ", ".join(f"{m[:4]} {runs[(m, 'B')]['mean_H_detector']:.4f}" for m in MODELS)
                   + "; first departure from A: " + ", ".join(f"{m[:4]} {diverge[m]}" for m in SP)),
        "controls_passed": sum(bool(v) for v in ctl.values()), "controls_total": len(ctl),
        "test_passed": int(all(cond.values())),
    }
    for m in MODELS:
        for an in "AB":
            values[f"H_{m}_{an}"] = r6(H[(m, an)])
    out = {k: values[k] for k in OUTPUTS}
    for k, v in out.items():
        if isinstance(v, str) and len(v) > LIMIT:
            raise AssertionError(f"{k}: longer than {LIMIT} characters: {v}")
    detail = {
        "conditions": cond, "controls": ctl, "small_tori": compared, "census_checks": census_checks,
        "alone": {"B": lone_b, "A": lone_a}, "first_departure_from_A": diverge, "paired_share_above_original": paired,
        "rules": {m: {"defined": int(defined[m].sum())} for m in MODELS},
        "runs": [{"model": k[0], "ancestor": k[1], **{x: y for x, y in v.items() if x != "H_window"}}
                 for k, v in sorted(runs.items(), key=lambda kv: ("AB".index(kv[0][1]), MODELS.index(kv[0][0])))],
        "updates": updates, "window": [window_from + SAMPLE, updates, SAMPLE], "L": L,
        "seconds": round(time.time() - t_start, 1),
    }
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
        sys.exit(f"selfprotect: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
