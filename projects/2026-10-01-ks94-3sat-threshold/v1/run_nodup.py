"""Sensitivity arm added after review (not pre-registered): the same grid and solver as run.py, but with no duplicate clauses
(a clause is redrawn if the same set of 3 literals is already present). KS (1994) do not say which model they used.
Entry point: python3 run_nodup.py -> results/counts_nodup.csv (resumable). Seeds: SHA-256 of "ks94nodup|N|alpha_index|sample"."""
import csv, hashlib, os, random, time
from multiprocessing import Pool
from pysat.solvers import Solver
from run import GRID

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results", "counts_nodup.csv")

def seed(n, ai, s):
    return int.from_bytes(hashlib.sha256(f"ks94nodup|{n}|{ai}|{s}".encode()).digest()[:8], "big")

def instance(n, m, rng):
    cls, seen = [], set()
    while len(cls) < m:
        vs = rng.sample(range(1, n + 1), 3)
        c = [v if rng.random() < 0.5 else -v for v in vs]
        key = frozenset(c)
        if key in seen:
            continue
        seen.add(key); cls.append(c)
    return cls

def solve(args):
    n, ai, alpha, s = args
    rng = random.Random(seed(n, ai, s))
    with Solver(name="minisat22", bootstrap_with=instance(n, round(alpha * n), rng)) as sol:
        return not sol.solve()

def main():
    done = set()
    if os.path.exists(OUT):
        with open(OUT) as f:
            for r in csv.DictReader(f):
                done.add((int(r["N"]), int(r["alpha_index"])))
    else:
        with open(OUT, "w", newline="") as f:
            csv.writer(f).writerow(["N", "alpha_index", "alpha", "M", "samples", "unsat", "seconds"])
    with Pool(2) as pool:
        for n, (alphas, k) in GRID.items():
            for ai, a in enumerate(alphas):
                if (n, ai) in done:
                    continue
                t = time.time()
                res = pool.map(solve, [(n, ai, a, s) for s in range(k)], chunksize=4)
                with open(OUT, "a", newline="") as f:
                    csv.writer(f).writerow([n, ai, a, round(a * n), k, sum(res), round(time.time() - t, 2)])
                print(n, a, flush=True)

if __name__ == "__main__":
    main()
