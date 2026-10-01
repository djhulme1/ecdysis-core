"""Generate random 3-SAT instances and decide each with MiniSat 2.2 (python-sat).
Entry point: python3 run.py   -> results/counts.csv (resumable; skips finished (N, alpha) points).
Seeds: SHA-256 of "ks94|N|alpha_index|sample"."""
import csv, hashlib, os, random, sys, time
from multiprocessing import Pool
from pysat.solvers import Solver

GRID = {}
for n in (12, 20, 24, 40, 50, 100):
    GRID[n] = ([round(3.0 + 0.1 * i, 2) for i in range(31)], 400)
for n in (150, 200):
    GRID[n] = ([round(3.8 + 0.05 * i, 2) for i in range(21)], 200)

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results", "counts.csv")

def seed(n, ai, s):
    return int.from_bytes(hashlib.sha256(f"ks94|{n}|{ai}|{s}".encode()).digest()[:8], "big")

def instance(n, m, rng):
    cls = []
    for _ in range(m):
        vs = rng.sample(range(1, n + 1), 3)
        cls.append([v if rng.random() < 0.5 else -v for v in vs])
    return cls

def solve(args):
    n, ai, alpha, s = args
    rng = random.Random(seed(n, ai, s))
    with Solver(name="minisat22", bootstrap_with=instance(n, round(alpha * n), rng)) as sol:
        return not sol.solve()  # True = unsatisfiable

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
