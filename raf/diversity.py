#!/usr/bin/env python3
"""The molecular diversity that autocatalytic sets need, in seeded instances of two models, for an Ecdysis receipt.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:2d06a5cef5b5b249) is from Hordijk, Steel &
Kauffman, "Molecular Diversity Required for the Formation of Autocatalytic Sets", Life 9(1), 23 (2019): "We investigate
the issue of the required molecular diversity for autocatalytic sets to exist in random polymer libraries. Given a fixed
probability that an arbitrary polymer catalyzes the formation of other polymers, we calculate this required molecular
diversity theoretically for two particular models of chemical reaction systems, and then verify these calculations by
computer simulations." Its registered test: refuted if, in the binary polymer model (bit strings up to length n, food of
length <= 2, each ligation with its cleavage one reaction, catalysed by each molecule with probability p), for any p in
Table 1 (1e-6, 5e-6, 1e-5, 5e-5, 1e-4, 5e-4), half or more of 200 instances have an RAF at the least n with
n + log2(n-2) > log2(1/p) - 2, or fewer than half at the next n (Table 1's); or if, in the Jain-Krishna model (N types,
each catalysing each type's formation, itself too, with probability p), half or more of 1,000 instances have one at
N = ceil((1-e^-1/2)/p) - 1, or fewer than half at N = floor(ln 2/p).

The models, the exact Bernoulli draws, the seeding and the maxRAF reduction are raf/check.py's (Kauffman's claim,
receipt d61f0e30), imported unchanged; so is its validation on CatReNet's three examples, which are this run's only
inputs. Every rule below was fixed before any seed existed.

1. The binary polymer model (the paper's section 3.1): raf/check.py's polymer_system(n), molecules the bit strings of
   length 1 to n, food those of length 1 and 2, ligation j and its cleavage n_lig + j. Catalysis: each of the
   n_lig |X| (ligation, molecule) pairs independently with probability p, drawn exactly (raf/check.py's
   catalysis_pairs), and a molecule that catalyses a ligation catalyses its cleavage too: each ligation with its
   cleavage is one reaction, as the paper counts |R| = (n - 2) 2^(n+1).
2. n* for each p: the least n >= 3 with (n - 2) 2^(n+1) > 1/(2p), which is inequality (2) of the paper written in
   integers (inequality (1): p (n - 2) 2^(n+1) > 1/2). For Table 1's p this is 15, 13, 12, 10, 9 and 7; Table 1's
   diversities (131,070 to 510) are those of n* + 1.
3. The Jain-Krishna model (section 3.2): N molecule types, molecule N the food; reaction j makes type j from the food;
   each type catalyses each reaction, its own included, independently with probability p (catalysis_pairs over the
   N x N pairs); the food catalyses nothing. N_low = ceil((1 - e^(-1/2))/p) - 1 and N_high = floor(ln 2/p), from
   Theorem 1's bounds (equation (5)), in 50-digit decimal arithmetic.
4. RAF: raf/check.py's max_raf (Hordijk and Steel's reduction); an instance has an RAF when the maxRAF is not empty.
   In the Jain-Krishna model an RAF is a directed cycle of catalysis, a self-loop included, so each instance is also
   decided by an independent rule: remove every type that catalyses no remaining type, until none is removed; a cycle
   exists exactly when something remains. jkm_agree is 1 if the two agree on every instance.
5. Randomness only from ECDYSIS_SEED, through raf/check.py's generator: instance i of a setting labelled s is drawn from
   PCG64 seeded with SHA-256(seed || "|" || s || "|" || i). Labels: "diversity/bpm/p<k>/n<n>", "diversity/jkm/p<k>/
   N<N>" and "diversity/oneway/p<k>/n<n>", k the index of p in Table 1.
6. What runs: 200 polymer-model instances at n* and at n* + 1 for each of Table 1's six p; 1,000 Jain-Krishna instances
   at N_low and N_high for each; and, beside the test, 100 instances at n* and n* + 1 for p = 1e-5 and 1e-4 with each
   direction of each reaction catalysed independently (the reading raf/check.py uses for Kauffman's model), to show
   the verdict does not hang on that choice. Two worker processes, results gathered in a fixed order.

test_passed is 1 if, for every p, fewer than 100 of the 200 polymer-model instances have an RAF at n* and at least 100
at n* + 1, and fewer than 500 of the 1,000 Jain-Krishna instances at N_low and at least 500 at N_high; else 0.

Reported beside the test, not part of it: closure_mean_p1e5, the mean number of molecule types (the six food types
included) made from the food by the maxRAF, over the polymer-model instances with an RAF at p = 1e-5 and n = 13, for
the paper's "autocatalytic (RAF) sets for these parameter values containing on average 14,000 polymer types".

Controls (controls_passed counts those that behave as stated): CatReNet's three examples give the sizes CatReNet's
README states (raf/check.py's validation); with no catalysis there is no RAF, in the polymer model at n = 8 and in the
Jain-Krishna model at N = 1,000; with one ligation of two food molecules catalysed by a food molecule there is one; with
one self-catalysing type there is one; and jkm_agree.

What it cannot check: the paper's theory beyond these points (its Theorem 1 itself, the heuristic's justification, which
the authors themselves call a mis-application of the Erdos-Renyi result); larger n than Table 1's; chemistry.

Writes results/outputs.json and results/detail.json. Run with: python3 raf/diversity.py
"""

import os

for _var in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
    os.environ.setdefault(_var, "1")

import decimal  # noqa: E402
import importlib.util  # noqa: E402
import json  # noqa: E402
import multiprocessing  # noqa: E402
import re  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
from fractions import Fraction  # noqa: E402

import numpy as np  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("raf_check", os.path.join(HERE, "check.py"))
R = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(R)

TABLE1 = (Fraction(1, 10 ** 6), Fraction(5, 10 ** 6), Fraction(1, 10 ** 5), Fraction(5, 10 ** 5), Fraction(1, 10 ** 4),
          Fraction(5, 10 ** 4))
NSTAR = (15, 13, 12, 10, 9, 7)                 # rule 2, checked
BPM_INSTANCES, JKM_INSTANCES, ONEWAY_INSTANCES = 200, 1000, 100
ONEWAY = (2, 4)                                # indices of p = 1e-5 and 1e-4
WORKERS = 2
LIMIT = 200

OUTPUTS = (
    "nstar", "bpm_at_nstar", "bpm_at_next", "jkm_low_n", "jkm_high_n", "jkm_at_low", "jkm_at_high", "jkm_agree",
    "closure_mean_p1e5", "oneway_at_nstar", "oneway_at_next", "validation_ok", "validation_sizes", "instances",
    "controls_passed", "controls_total", "test_passed",
)


def nstar(p):
    """Rule 2: the least n >= 3 with (n - 2) 2^(n+1) > 1/(2p), in exact arithmetic."""
    n = 3
    while not (n - 2) * (1 << (n + 1)) > Fraction(1, 2) / p:
        n += 1
    return n


def jkm_points(p):
    """Rule 3: (N_low, N_high) in 50-digit decimal arithmetic."""
    with decimal.localcontext() as ctx:
        ctx.prec = 50
        q = decimal.Decimal(p.numerator) / decimal.Decimal(p.denominator)
        low = ((1 - (decimal.Decimal(-1) / 2).exp()) / q).to_integral_value(rounding=decimal.ROUND_CEILING) - 1
        high = (decimal.Decimal(2).ln() / q).to_integral_value(rounding=decimal.ROUND_FLOOR)
    return int(low), int(high)


def two_way(rng, n, p):
    """Rule 1: the catalysis of polymer_system(n) with each ligation and its cleavage sharing their catalysts."""
    S = R.polymer_system(n)
    nl = R.ligation_count(n)
    r, m = R.catalysis_pairs(rng, nl, S.molecules, p)
    return S, (np.concatenate([r, r + nl]), np.concatenate([m, m]))


def elementary(N):
    """Rule 3's system: types 0 .. N - 1, molecule N the food, reaction j: food -> j."""
    food = np.zeros(N + 1, dtype=bool)
    food[N] = True
    j = np.arange(N, dtype=np.int64)
    return R.System(N + 1, N, food, (j, np.full(N, N, dtype=np.int64)), (j, j))


def has_cycle(N, rxn, cat):
    """Rule 4's independent rule: prune the types that catalyse no remaining type until stable; True if any remain."""
    alive = np.ones(N, dtype=bool)
    while True:
        keep = alive[cat] & alive[rxn]
        out = np.bincount(cat[keep], minlength=N) > 0
        new = alive & out
        if np.array_equal(new, alive):
            return bool(new.any())
        alive = new


def verdict(at_n, at_next, at_low, at_high, bpm_instances=BPM_INSTANCES, jkm_instances=JKM_INSTANCES):
    """The registered test on the counts of instances with an RAF, one count per p in each list: True unless half or
    more of the polymer-model instances have one at n* or fewer than half at n* + 1, or half or more of the
    Jain-Krishna instances at N_low or fewer than half at N_high."""
    hb, hj = Fraction(bpm_instances, 2), Fraction(jkm_instances, 2)
    return (all(x < hb for x in at_n) and all(x >= hb for x in at_next)
            and all(x < hj for x in at_low) and all(x >= hj for x in at_high))


def run_job(job):
    """One instance: (has an RAF, the maxRAF's reactions, its closure's molecules, the independent rule's verdict)."""
    seed, kind, k, size, i = job
    p = float(TABLE1[k])
    rng = R.generator(seed, f"diversity/{kind}/p{k}/{'N' if kind == 'jkm' else 'n'}{size}", i)
    if kind == "bpm":
        S, catalysis = two_way(rng, size, p)
    elif kind == "oneway":
        S = R.polymer_system(size)
        catalysis = R.catalysis_pairs(rng, S.reactions, S.molecules, p)
    else:
        S = elementary(size)
        catalysis = R.catalysis_pairs(rng, size, size, p)
    alive, made = R.max_raf(S, catalysis)
    raf = bool(alive.any())
    cycle = has_cycle(size, catalysis[0], catalysis[1]) if kind == "jkm" else None
    return raf, int(alive.sum()), int(made.sum()), cycle


def cost(job):
    _, kind, k, size, _ = job
    if kind == "jkm":
        return size / 50.0
    return float(TABLE1[k]) * R.ligation_count(size) * R.molecule_count(size) + 2 * R.ligation_count(size)


def run_all(jobs, workers=WORKERS):
    order = sorted(range(len(jobs)), key=lambda q: (-cost(jobs[q]), q))
    queue = [jobs[q] for q in order]
    results = [None] * len(jobs)
    pool = None
    try:
        pool = multiprocessing.get_context("fork").Pool(workers)
        done = pool.imap(run_job, queue, chunksize=1)
    except (OSError, ValueError, ImportError) as e:
        print(f"raf/diversity.py: no worker pool ({e}); running serially", file=sys.stderr)
        done = map(run_job, queue)
    try:
        for count, (q, r) in enumerate(zip(order, done), start=1):
            results[q] = r
            if count % 1000 == 0 or count == len(jobs):
                print(f"raf/diversity.py: {count} of {len(jobs)} instances", file=sys.stderr, flush=True)
    finally:
        if pool is not None:
            pool.terminate()
            pool.join()
    return results


def controls(seed):
    """The controls that need no draws beyond these fixed systems: (rows, all passed)."""
    rows = []
    S = R.polymer_system(8)
    empty = (np.zeros(0, dtype=np.int64), np.zeros(0, dtype=np.int64))
    rows.append({"control": "no catalysis, polymer model n = 8: no RAF", "passed": not R.max_raf(S, empty)[0].any()})
    rows.append({"control": "no catalysis, Jain-Krishna N = 1000: no RAF",
                 "passed": not R.max_raf(elementary(1000), empty)[0].any()})
    # The first ligation of two food molecules into a polymer that is not food ("0" + "00" -> "000"), catalysed by
    # molecule 0 (the food "0"); nothing else catalysed, its cleavage included.
    left, right, product = R.ligations(8)
    food = S.food
    j = int(np.flatnonzero(food[left] & food[right] & ~food[product])[0])
    one = (np.array([j], dtype=np.int64), np.array([0], dtype=np.int64))
    alive, _ = R.max_raf(S, one)
    rows.append({"control": f"ligation {j} of two food molecules catalysed by food: an RAF",
                 "passed": bool(alive.any()) and int(alive.sum()) == 1})
    self_loop = (np.array([7], dtype=np.int64), np.array([7], dtype=np.int64))
    alive, _ = R.max_raf(elementary(1000), self_loop)
    rows.append({"control": "one self-catalysing type, Jain-Krishna N = 1000: an RAF of one",
                 "passed": bool(alive.any()) and int(alive.sum()) == 1 and has_cycle(1000, *self_loop)})
    return rows


def run(seed, results="results", inputs="inputs", workers=WORKERS, scale=1, log=print):
    """scale divides the instance counts, for tests only (the receipt runs scale 1)."""
    started = time.monotonic()
    got = tuple(nstar(p) for p in TABLE1)
    if got != NSTAR:
        raise AssertionError(f"n* is {got}, not {NSTAR}")
    points = [jkm_points(p) for p in TABLE1]
    validation_ok, validation_sizes, validation = R.validate(inputs)
    for n in sorted({n for n in NSTAR} | {n + 1 for n in NSTAR}):
        R.polymer_system(n)                         # built before the workers fork, so they share it
    bpm_k, jkm_k, one_k = BPM_INSTANCES // scale, JKM_INSTANCES // scale, ONEWAY_INSTANCES // scale
    plan = [("bpm", k, n) for k, n0 in enumerate(NSTAR) for n in (n0, n0 + 1)]
    plan += [("jkm", k, N) for k, pts in enumerate(points) for N in pts]
    plan += [("oneway", k, n) for k in ONEWAY for n in (NSTAR[k], NSTAR[k] + 1)]
    counts = {"bpm": bpm_k, "jkm": jkm_k, "oneway": one_k}
    jobs = [(seed, kind, k, size, i) for kind, k, size in plan for i in range(counts[kind])]
    out_rows = run_all(jobs, workers)
    summary, at = [], 0
    for kind, k, size in plan:
        rows = out_rows[at:at + counts[kind]]
        at += counts[kind]
        with_raf = sum(1 for r in rows if r[0])
        entry = {"kind": kind, "p": str(TABLE1[k]), "size": size, "instances": len(rows), "with_raf": with_raf,
                 "maxraf_mean": round(sum(r[1] for r in rows) / len(rows), 3),
                 "closure_mean_given_raf": round(sum(r[2] for r in rows if r[0]) / with_raf, 3) if with_raf else None}
        if kind == "jkm":
            entry["agree"] = all(r[0] == r[3] for r in rows)
        summary.append(entry)
        log(f"diversity: {kind} p = {TABLE1[k]} size {size}: {with_raf} of {len(rows)} with an RAF")

    def pick(kind, k, size):
        return next(s for s in summary if s["kind"] == kind and s["p"] == str(TABLE1[k]) and s["size"] == size)

    at_n = [pick("bpm", k, n)["with_raf"] for k, n in enumerate(NSTAR)]
    at_next = [pick("bpm", k, n + 1)["with_raf"] for k, n in enumerate(NSTAR)]
    at_low = [pick("jkm", k, pts[0])["with_raf"] for k, pts in enumerate(points)]
    at_high = [pick("jkm", k, pts[1])["with_raf"] for k, pts in enumerate(points)]
    agree = all(s.get("agree", True) for s in summary)
    rows = controls(seed)
    rows.insert(0, {"control": "CatReNet's three examples", "passed": bool(validation_ok)})
    rows.append({"control": "the Jain-Krishna verdicts agree with the independent rule", "passed": agree})
    test = verdict(at_n, at_next, at_low, at_high, bpm_k, jkm_k)
    values = {
        "nstar": ",".join(map(str, NSTAR)),
        "bpm_at_nstar": ",".join(map(str, at_n)),
        "bpm_at_next": ",".join(map(str, at_next)),
        "jkm_low_n": ",".join(str(pts[0]) for pts in points),
        "jkm_high_n": ",".join(str(pts[1]) for pts in points),
        "jkm_at_low": ",".join(map(str, at_low)),
        "jkm_at_high": ",".join(map(str, at_high)),
        "jkm_agree": int(agree),
        "closure_mean_p1e5": pick("bpm", 2, NSTAR[2] + 1)["closure_mean_given_raf"],
        "oneway_at_nstar": ",".join(str(pick("oneway", k, NSTAR[k])["with_raf"]) for k in ONEWAY),
        "oneway_at_next": ",".join(str(pick("oneway", k, NSTAR[k] + 1)["with_raf"]) for k in ONEWAY),
        "validation_ok": int(bool(validation_ok)),
        "validation_sizes": validation_sizes,
        "instances": len(jobs),
        "controls_passed": sum(1 for r in rows if r["passed"]),
        "controls_total": len(rows),
        "test_passed": int(test),
    }
    out = {k: values[k] for k in OUTPUTS}
    for k, v in out.items():
        if isinstance(v, str) and len(v) > LIMIT:
            raise AssertionError(f"{k}: longer than {LIMIT} characters")
    os.makedirs(results, exist_ok=True)
    with open(os.path.join(results, "outputs.json"), "w", encoding="ascii") as f:
        json.dump(out, f, indent=2, sort_keys=True)
        f.write("\n")
    with open(os.path.join(results, "detail.json"), "w", encoding="ascii") as f:
        json.dump({"values": values, "settings": summary, "controls": rows, "validation": validation,
                   "jkm_points": points, "seconds": round(time.monotonic() - started, 1)}, f, indent=1, sort_keys=True)
        f.write("\n")
    return out, summary


def main():
    seed = os.environ.get("ECDYSIS_SEED", "")
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        sys.exit("ECDYSIS_SEED must be the 64-hex seed the archive issued")
    out, _ = run(seed, log=lambda s: print(s, file=sys.stderr, flush=True))
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
