#!/usr/bin/env python3
"""Mitchell, Hraber & Crutchfield (1993): evolved cellular automata for the density task cluster at lambda = 1/2,
not at the "edge of chaos".

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:b5219a067681072d) is from Mitchell, Hraber
and Crutchfield, "Revisiting the Edge of Chaos: Evolving Cellular Automata to Perform Computations" (Complex Systems 7,
89-130, 1993; arXiv:adap-org/9303003): "Our experiment produced very different results, and we suggest that the
interpretation of the original results is not correct." The original results are Packard's (1988): rules a genetic
algorithm evolved for the rho_c = 1/2 task clustered near the critical lambda values, in the bins centred about 0.24 and
0.83; the paper's runs put no rules there, but close about lambda = 1/2.

Its registered test: refuted if, in 30 new runs of the paper's GA as it specifies it (Section 7.1), the final
generations' rules, merged, are not clustered about lambda = 1/2: more than 1% of them in Packard's peak bins, lambda in
[0.2, 0.267) or [0.8, 0.867), or fewer than 95% between 0.267 and 0.733.

Standard library and the image's gcc: the GA is simulated in C (alife/eoc.c, compiled here). No data are read: the
runs are generated under the seed. Every rule below was fixed before any seed existed.

1. The task and the rules (Sections 2, 6 and 7.1): one-dimensional binary CA of radius 3 on a ring of 149 cells. A rule
   is its 128 output bits, bit k the next state of the neighbourhood k read as a 7-bit number, cell i - 3 the most
   significant (the paper: bit 0 for 0000000, bit 1 for 0000001). lambda is the fraction of 1s among the 128.
2. Fitness, "proportional fitness" (7.1): each generation, 300 new initial configurations, uniformly distributed over
   density, exactly half below 1/2 and half above (the number of 1s uniform on 0..74 for 150, on 75..149 for 150, and
   uniformly placed). Each rule runs on every one for M steps, M drawn for the rule from a Poisson distribution of mean
   320; its score on one is the fraction of cells in the correct state at the last step (all 1s for density above 1/2,
   all 0s below), its fitness the mean score. A run that reaches a fixed point stops there, which changes no score.
3. The GA (7.1): population 100; the initial rules uniform in lambda (their number of 1s uniform on 0..128, then
   uniformly placed). Each generation all rules are tested; the top half, the elite, passes on unchanged (ties in order
   of index); the other half are offspring of parents drawn at random with replacement from the whole population, one
   crossover point uniform on the 127 places, two offspring a pair, each given a number of random bit flips drawn from
   a Poisson distribution of mean 3.8. The paper says fifty pairs, two offspring each, for the fifty places: here 25
   pairs give the fifty. 100 generations; the final generation is the population at generation 100, all of it, as the
   paper's Figure 6(b) merges it.
4. The histogram (Figure 6): 15 bins of width 1/15 over lambda, lambda = 1 in the rightmost. Packard's peaks are the
   bins [0.2, 0.267) and [0.8, 0.867); the seven central bins span [0.267, 0.733).
5. The test's two conditions, on the 3,000 final rules of the 30 runs merged: at most 1% in Packard's two peak bins; at
   least 95% in the seven central bins. test_passed is 1 if both hold.
6. Beside the test, none of it counted: the merged final histogram and that of the elite alone (the top 50 of each run at
   generation 100, Figure 7); how many bins are occupied (six, in the paper); whether the central bin holds fewer rules
   than both its neighbours, the paper's dip at 1/2, and the two highest bins against it (three times as high, in the
   paper); on which side of 1/2 each run's final rules lie (14 below and 16 above, in the paper); the best fitness of a
   final rule (0.93 to 0.95, in the paper); and 30 runs with selection turned off (7.3, Figure 9: the elite chosen at
   random), whose rules drift to lambda = 1/2 by generation 10 without any fitness.

Controls (controls_passed counts those that behave as stated): the C simulation agrees cell for cell with a plain one
written here, on 20 seed-drawn rules and configurations over 60 steps; the GKL rule, built from the paper's definition
(Section 6), has lambda exactly 1/2 and a proportional fitness within 0.01 of the paper's 0.98, over ten fresh sets of
300 configurations; the rule that maps everything to 0 scores exactly 1/2 on every set, and the identity rule within
0.01 of 112/149, its expectation under these densities; and the initial populations cover lambda from 0 to 1, every bin
holding at least 3% of the 3,000 generation-0 rules.

What it cannot check: Packard's own runs, whose data are not published, and the paper's second experiment with
performance fitness (Section 8).

Writes results/outputs.json (the values a receipt carries) and results/detail.json (every value computed).
Run with: python3 alife/eoc.py
"""

import concurrent.futures as cf
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
L = 149
POP = 100
ELITE = 50
RUNS = 30
GENS = 100
BINS = 15
CENTRE = 7                                      # the bin [7/15, 8/15), lambda = 1/2
PACKARD = (3, 12)                               # [0.2, 0.267) and [0.8, 0.867)
CENTRAL = range(4, 11)                          # [0.267, 0.733)
LIMIT = 200
OUTPUTS = ("runs", "final_rules", "in_packard_bins", "central_share", "histogram", "elite_histogram",
           "occupied_bins", "dip", "peaks", "sides", "best_fitness", "gkl_fitness", "drift", "conditions_met",
           "conditions_total", "controls_passed", "controls_total", "test_passed")


class Refused(Exception):
    pass


# ---------------------------------------------------------------- rules, bins and a plain simulation

def lam_bin(n_ones):
    """The paper's bin of a rule with n_ones 1s among its 128 bits: floor(15 lambda), lambda = 1 in the last."""
    return min(BINS * n_ones // 128, BINS - 1)


def histogram(ns):
    h = [0] * BINS
    for n in ns:
        h[lam_bin(n)] += 1
    return h


def neighbourhood(cells, i):
    """The 7-bit number of cell i's neighbourhood, cell i - 3 the most significant bit."""
    n = len(cells)
    return sum(cells[(i + d) % n] << (3 - d) for d in range(-3, 4))


def plain_step(rule, cells):
    return [rule[neighbourhood(cells, i)] for i in range(len(cells))]


def gkl():
    """The Gacs-Kurdyumov-Levin rule as the paper defines it (Section 6)."""
    out = []
    for nb in range(128):
        s = {d: (nb >> (3 - d)) & 1 for d in range(-3, 4)}
        votes = (s[0], s[-1], s[-3]) if s[0] == 0 else (s[0], s[1], s[3])
        out.append(int(sum(votes) >= 2))
    return out


def rule_hex(bits):
    return format(sum(b << k for k, b in enumerate(bits)), "032x")


def hex_rule(h):
    v = int(h, 16)
    return [(v >> k) & 1 for k in range(128)]


# ---------------------------------------------------------------- seeds

class Stream:
    """Integers from the seed: SHA-256 of seed, label and a counter."""

    def __init__(self, seed, label):
        self.seed, self.label, self.n = seed, label, 0

    def below(self, m):
        self.n += 1
        h = hashlib.sha256(f"{self.seed}/{self.label}/{self.n}".encode()).digest()
        return int.from_bytes(h[:8], "big") % m


def words(seed, label):
    """Four 64-bit words for the C generator (xoshiro256**), from SHA-256 of seed and label."""
    h = hashlib.sha256(f"{seed}/{label}".encode()).digest()
    w = [h[i:i + 8].hex() for i in range(0, 32, 8)]
    if all(int(x, 16) == 0 for x in w):
        raise Refused("an all-zero generator state")
    return w


# ---------------------------------------------------------------- the C program

def build(work):
    exe = os.path.join(work, "eoc")
    subprocess.run(["gcc", "-O2", "-std=gnu11", "-o", exe, os.path.join(HERE, "eoc.c"), "-lm"], check=True)
    return exe


def ga_run(exe, seed, label, select, work):
    out = os.path.join(work, label.replace("/", "_") + ".txt")
    subprocess.run([exe, "ga", *words(seed, label), str(GENS), str(int(select)), out], check=True)
    gens, final = {}, []
    with open(out, encoding="ascii") as fh:
        for line in fh:
            parts = line.split()
            if parts[0] == "gen":
                gens[int(parts[1])] = [int(x) for x in parts[2:]]
            elif parts[0] == "final":
                final.append({"rank": int(parts[1]), "rule": parts[2], "ones": int(parts[3]),
                              "fitness": float(parts[4]), "elite": parts[5] == "1"})
    if sorted(gens) != list(range(GENS + 1)) or len(final) != POP:
        raise Refused(f"{label}: an incomplete run")
    return {"gens": gens, "final": final}


def fit_sets(exe, seed, label, bits, sets, work):
    out = os.path.join(work, label.replace("/", "_") + ".fit")
    subprocess.run([exe, "fit", *words(seed, label), rule_hex(bits), str(sets), out], check=True)
    with open(out, encoding="ascii") as fh:
        return [float(x) for x in fh.read().split()]


def trace(exe, bits, cells, steps):
    r = subprocess.run([exe, "trace", rule_hex(bits), "".join(map(str, cells)), str(steps)], check=True,
                       capture_output=True, text=True)
    return [int(c) for c in r.stdout.strip()]


# ---------------------------------------------------------------- the run

def summary_bins(h):
    return " ".join(str(x) for x in h)


def run(seed, results="results", workers=None):
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        raise Refused("the seed must be 64 hex characters")
    if shutil.which("gcc") is None:
        raise Refused("no gcc in this image")
    work = tempfile.mkdtemp(prefix="eoc-")
    try:
        exe = build(work)
        workers = workers or max(1, os.cpu_count() or 1)
        jobs = [(f"eoc/ga/{k}", True) for k in range(1, RUNS + 1)] + \
               [(f"eoc/drift/{k}", False) for k in range(1, RUNS + 1)]
        with cf.ThreadPoolExecutor(workers) as pool:
            futs = {lab: pool.submit(ga_run, exe, seed, lab, sel, work) for lab, sel in jobs}
            runs = {lab: f.result() for lab, f in futs.items()}

        ga = [runs[f"eoc/ga/{k}"] for k in range(1, RUNS + 1)]
        drift = [runs[f"eoc/drift/{k}"] for k in range(1, RUNS + 1)]
        final_ones = [r["ones"] for run_ in ga for r in run_["final"]]
        elite_ones = [r["ones"] for run_ in ga for r in run_["final"] if r["elite"]]
        hist, ehist = histogram(final_ones), histogram(elite_ones)
        n_final = len(final_ones)
        in_packard = sum(hist[b] for b in PACKARD)
        central = sum(hist[b] for b in CENTRAL)
        cond = {
            "at most 1% of the final rules in Packard's peak bins, [0.2, 0.267) and [0.8, 0.867)":
                in_packard * 100 <= n_final,
            "at least 95% of them between lambda = 0.267 and 0.733": central * 100 >= 95 * n_final,
        }
        sides = [0, 0]
        for run_ in ga:
            below = sum(1 for r in run_["final"] if r["ones"] < 64)
            above = sum(1 for r in run_["final"] if r["ones"] > 64)
            sides[0 if below > above else 1] += 1
        best = max(r["fitness"] for run_ in ga for r in run_["final"])
        order = sorted(range(BINS), key=lambda b: (-hist[b], b))
        peaks = (f"highest bins {order[0]}/15 to {order[0] + 1}/15 ({hist[order[0]]}) and {order[1]}/15 to "
                 f"{order[1] + 1}/15 ({hist[order[1]]}); central bin {hist[CENTRE]}")

        def share(gen, runs_):
            ns = [n for r in runs_ for n in r["gens"][gen]]
            return sum(1 for n in ns if lam_bin(n) in (CENTRE - 1, CENTRE, CENTRE + 1)) / len(ns)
        g10 = min(10, GENS)
        drift_text = (f"central three bins: {100 * share(0, drift):.1f}% at generation 0, "
                      f"{100 * share(g10, drift):.1f}% at {g10}, {100 * share(GENS, drift):.1f}% at {GENS}")

        # controls
        ctl, ctl_detail = {}, {}
        stream = Stream(seed, "eoc/controls")
        agree = True
        for _ in range(20):
            n1 = stream.below(129)
            pos = list(range(128))
            for i in range(127, 0, -1):
                j = stream.below(i + 1)
                pos[i], pos[j] = pos[j], pos[i]
            bits = [0] * 128
            for k in pos[:n1]:
                bits[k] = 1
            cells = [stream.below(2) for _ in range(L)]
            steps = 1 + stream.below(60)
            ref = cells
            for _ in range(steps):
                ref = plain_step(bits, ref)
            agree = agree and trace(exe, bits, cells, steps) == ref
        ctl["the C simulation agrees with a plain one on 20 seed-drawn rules and configurations"] = agree
        g = gkl()
        gfit = fit_sets(exe, seed, "eoc/gkl", g, 10, work)
        gmean = sum(gfit) / len(gfit)
        ctl["the GKL rule has lambda 1/2 and fitness within 0.01 of 0.98"] = sum(g) == 64 and abs(gmean - 0.98) <= 0.01
        zero = fit_sets(exe, seed, "eoc/zero", [0] * 128, 10, work)
        ident = fit_sets(exe, seed, "eoc/identity", [(nb >> 3) & 1 for nb in range(128)], 10, work)
        imean = sum(ident) / len(ident)
        ctl["the all-0 rule scores exactly 1/2 and the identity rule within 0.01 of 112/149"] = (
            all(abs(z - 0.5) < 1e-9 for z in zero) and abs(imean - 112 / 149) <= 0.01)
        h0 = histogram([n for run_ in ga for n in run_["gens"][0]])
        ctl["the initial populations cover lambda: every bin holds at least 3% of the generation-0 rules"] = (
            min(h0) * 100 >= 3 * sum(h0))
        ctl_detail.update({"gkl_sets": gfit, "zero_sets": zero, "identity_sets": ident, "generation0_histogram": h0})

        values = {
            "runs": f"{RUNS} GA runs of {GENS} generations, population {POP}; {RUNS} without selection",
            "final_rules": n_final,
            "in_packard_bins": in_packard,
            "central_share": round(central / n_final, 4),
            "histogram": summary_bins(hist),
            "elite_histogram": summary_bins(ehist),
            "occupied_bins": sum(1 for x in hist if x),
            "dip": int(hist[CENTRE] < hist[CENTRE - 1] and hist[CENTRE] < hist[CENTRE + 1]),
            "peaks": peaks,
            "sides": f"{sides[0]} runs below 1/2, {sides[1]} above",
            "best_fitness": round(best, 4),
            "gkl_fitness": round(gmean, 4),
            "drift": drift_text,
            "conditions_met": sum(cond.values()), "conditions_total": len(cond),
            "controls_passed": sum(ctl.values()), "controls_total": len(ctl),
            "test_passed": int(all(cond.values())),
        }
        out = {k: values[k] for k in OUTPUTS}
        for key, v in out.items():
            if isinstance(v, str) and len(v) > LIMIT:
                raise AssertionError(f"{key}: longer than {LIMIT} characters: {v}")
        per_run = []
        for k, run_ in enumerate(ga, 1):
            per_run.append({"run": k, "final_histogram": histogram([r["ones"] for r in run_["final"]]),
                            "best": max(r["fitness"] for r in run_["final"]),
                            "best_rule": run_["final"][0]["rule"],
                            "mosaic": {str(gn): histogram(run_["gens"][gn]) for gn in range(0, GENS + 1, 5)}})
        detail = {"conditions": cond, "controls": ctl, "control_detail": ctl_detail,
                  "final_histogram": hist, "elite_histogram": ehist, "runs": per_run,
                  "drift_mosaic": {str(gn): histogram([n for r in drift for n in r["gens"][gn]])
                                   for gn in range(0, GENS + 1, 5)},
                  "bins": [str(Fraction(b, BINS)) for b in range(BINS + 1)]}
        os.makedirs(results, exist_ok=True)
        with open(os.path.join(results, "outputs.json"), "w", encoding="ascii") as fh:
            json.dump(out, fh, indent=2, sort_keys=True)
            fh.write("\n")
        with open(os.path.join(results, "detail.json"), "w", encoding="ascii") as fh:
            json.dump(detail, fh, indent=1, sort_keys=True)
            fh.write("\n")
        return out, detail
    finally:
        shutil.rmtree(work, ignore_errors=True)


def main():
    seed = os.environ.get("ECDYSIS_SEED", "")
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        sys.exit("ECDYSIS_SEED must be the 64-hex seed the archive issued")
    try:
        out, _ = run(seed)
    except Refused as e:
        sys.exit(f"eoc: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
