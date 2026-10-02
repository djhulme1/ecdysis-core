"""Kirkpatrick & Selman (1994) random 3-SAT finite-size scaling, re-measured: the v2 receipt bundle.

Entry point:  python3 run.py
Reads one seed from the environment variable ECDYSIS_SEED (64 hex characters). ALL randomness (every instance
and every bootstrap resample) derives from it through SHA-256; the clock is never read. With no ECDYSIS_SEED
the fixed default below is used and the run says so.

What it does, exactly as pre-registered in PLAN.md (grid, instance model, solver, analyses A1-A5), for two
instance models ("dup": clauses drawn independently, duplicates possible, the pre-registered model; "nodup":
no clause repeated within a formula, the arm added at review because the parent does not state its model):
  1. generate 82,800 random 3-CNF formulas per arm and decide each with MiniSat 2.2 (python-sat)
     -> results/counts_dup.csv, results/counts_nodup.csv (resumable for the same seed);
  2. fit A1 (per-N logistic), A2/A3 (finite-size-scaling collapses), A4 (width exponent), A5 (50% law)
     -> results/analysis.json (everything) and results/outputs.json (the at most 20 outputs a cross-check compares).
"""
import csv, hashlib, itertools, json, os, random, re, sys
from multiprocessing import Pool

import numpy as np
from pysat.solvers import Solver
from scipy.optimize import minimize
from scipy.special import expit

DEFAULT_SEED = "00" * 32
SEED = os.environ.get("ECDYSIS_SEED", "").strip().lower()
SEED_FROM_ENV = bool(SEED)
if not SEED:
    SEED = DEFAULT_SEED
if not re.fullmatch(r"[0-9a-f]{64}", SEED):
    sys.exit("ECDYSIS_SEED must be 64 hexadecimal characters")

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "results")
ARMS = ("dup", "nodup")
SMALL = [12, 20, 24, 40, 50, 100]      # Kirkpatrick & Selman's own sizes
LARGE = [50, 100, 150, 200]
GRID = {}
for _n in SMALL:
    GRID[_n] = ([round(3.0 + 0.1 * i, 2) for i in range(31)], 400)
for _n in (150, 200):
    GRID[_n] = ([round(3.8 + 0.05 * i, 2) for i in range(21)], 200)
B_A1 = 300        # bootstrap resamples for per-N fits and the width exponent
B_COLLAPSE = 100  # bootstrap resamples for each collapse fit


def derive(*parts):
    """A 64-bit integer derived from the run seed and a label."""
    return int.from_bytes(hashlib.sha256("|".join([SEED] + [str(p) for p in parts]).encode()).digest()[:8], "big")


# ---------------------------------------------------------------- data
def instance(n, m, rng, nodup):
    cls, seen = [], set()
    while len(cls) < m:
        vs = rng.sample(range(1, n + 1), 3)
        c = [v if rng.random() < 0.5 else -v for v in vs]
        if nodup:
            key = frozenset(c)
            if key in seen:
                continue
            seen.add(key)
        cls.append(c)
    return cls


def solve(args):
    arm, n, ai, alpha, s = args
    rng = random.Random(derive("instance", arm, n, ai, s))
    with Solver(name="minisat22", bootstrap_with=instance(n, round(alpha * n), rng, arm == "nodup")) as sol:
        return not sol.solve()  # True = unsatisfiable (MiniSat is complete: every instance is decided)


def generate(arm, pool):
    path = os.path.join(RES, "counts_%s.csv" % arm)
    head = "# seed=%s" % SEED
    done = set()
    if os.path.exists(path):
        with open(path) as f:
            lines = f.read().splitlines()
        if lines and lines[0] == head:
            for r in csv.DictReader(lines[1:]):
                done.add((int(r["N"]), int(r["alpha_index"])))
    if not done:
        with open(path, "w", newline="") as f:
            f.write(head + "\n")
            csv.writer(f, lineterminator="\n").writerow(["N", "alpha_index", "alpha", "M", "samples", "unsat"])
    for n, (alphas, k) in GRID.items():
        for ai, a in enumerate(alphas):
            if (n, ai) in done:
                continue
            res = pool.map(solve, [(arm, n, ai, a, s) for s in range(k)], chunksize=8)
            with open(path, "a", newline="") as f:
                csv.writer(f, lineterminator="\n").writerow([n, ai, a, round(a * n), k, sum(res)])
        print(arm, "N =", n, "done", flush=True)


def load(arm):
    D = {}
    with open(os.path.join(RES, "counts_%s.csv" % arm)) as f:
        for r in csv.DictReader(f.read().splitlines()[1:]):
            D.setdefault(int(r["N"]), []).append((float(r["alpha"]), int(r["samples"]), int(r["unsat"])))
    return {n: np.array(sorted(v)) for n, v in D.items()}


# ---------------------------------------------------------------- fits
OPT = {"xatol": 1e-6, "fatol": 1e-7, "maxiter": 20000}


def nll(p, k, n):
    p = np.clip(p, 1e-12, 1 - 1e-12)
    return -np.sum(k * np.log(p) + (n - k) * np.log(1 - p))


def fit_logistic(a, n, k):
    """A1: P_unsat = logistic((alpha - m)/s) by maximum likelihood -> (alpha_50, 10-90% width)."""
    r = minimize(lambda th: nll(expit((a - th[0]) / abs(th[1])), k, n), [4.3, 0.1], method="Nelder-Mead", options=OPT)
    return r.x[0], 2 * np.log(9) * abs(r.x[1])


def stack(D, nl):
    return (np.concatenate([np.full(len(D[N]), float(N)) for N in nl]),) + tuple(
        np.concatenate([D[N][:, j] for N in nl]) for j in (0, 1, 2))


def collapse_nll(th, S):
    ac, nu, y50, s = th
    if nu <= 0.2 or s <= 0 or ac <= 0:
        return 1e18
    Ns, a, n, k = S
    return nll(expit((Ns ** (1 / nu) * (a - ac) / ac - y50) / s), k, n)


STARTS = list(itertools.product([4.0, 4.17, 4.27], [1.2, 1.5, 2.0], [0.4, 1.0], [0.6]))


def collapse(S, starts=STARTS):
    """A2/A3: P_unsat = logistic((y - y50)/s), y = N^(1/nu) (alpha - alpha_c)/alpha_c, by maximum likelihood."""
    return min((minimize(collapse_nll, st, args=(S,), method="Nelder-Mead", options=OPT) for st in starts),
               key=lambda r: r.fun)


def sd(x):
    return float(np.std(np.asarray(x, dtype=float), ddof=1))


def ci(x):
    return [float(np.percentile(x, 2.5)), float(np.percentile(x, 97.5))]


def analyse(arm):
    D = load(arm)
    rng = np.random.default_rng(derive("bootstrap", arm))
    resample = lambda N: rng.binomial(D[N][:, 1].astype(int), D[N][:, 2] / D[N][:, 1])  # fresh formulas at the observed fractions
    o = {"A1": {}}
    bm, bw = {}, {}
    for N in sorted(D):
        a, n, k = D[N][:, 0], D[N][:, 1], D[N][:, 2]
        m, w = fit_logistic(a, n, k)
        fb = [fit_logistic(a, n, resample(N)) for _ in range(B_A1)]
        bm[N] = [x[0] for x in fb]
        bw[N] = [x[1] for x in fb]
        ks = 4.17 + 3.1 * N ** (-2 / 3)
        ca = 4.24 + 6 / N
        o["A1"][str(N)] = {"alpha50": m, "alpha50_se": sd(bm[N]), "alpha50_ci": ci(bm[N]), "width10_90": w,
                           "width_ci": ci(bw[N]), "KS_law": ks, "obs_minus_KS_law": m - ks,
                           "CA_law": ca, "obs_minus_CA_law": m - ca}
    for key, nl in (("A2", SMALL), ("A3", LARGE)):
        S = stack(D, nl)
        r = collapse(S)
        sat = sum(nll(D[N][:, 2] / D[N][:, 1], D[N][:, 2], D[N][:, 1]) for N in nl)
        df = len(S[0]) - 4
        phi = 2 * (r.fun - sat) / df
        at417 = min((minimize(lambda t: collapse_nll([4.17, t[0], t[1], t[2]], S), st, method="Nelder-Mead", options=OPT)
                     for st in (list(r.x[1:]), [1.5, 0.74, 0.6])), key=lambda q: q.fun)
        triple = minimize(lambda t: collapse_nll([4.17, 1.5, 0.74, t[0]], S), [0.5], method="Nelder-Mead", options=OPT)
        bs = []
        for _ in range(B_COLLAPSE):
            Sb = S[:3] + (np.concatenate([resample(N) for N in nl]).astype(float),)
            bs.append(collapse(Sb, starts=[list(r.x)]).x)
        bs = np.array(bs)
        o[key] = {"N": nl, "alpha_c": r.x[0], "nu": r.x[1], "y50": r.x[2], "s": r.x[3],
                  "alpha_c_se": sd(bs[:, 0]), "nu_se": sd(bs[:, 1]), "alpha_c_ci": ci(bs[:, 0]), "nu_ci": ci(bs[:, 1]),
                  "residual_deviance": 2 * (r.fun - sat), "df": df, "phi": phi,
                  "deviance_at_alpha_c_4.17": 2 * (at417.fun - r.fun), "deviance_over_phi_at_4.17": 2 * (at417.fun - r.fun) / phi,
                  "KS_triple_deviance": 2 * (triple.fun - r.fun), "KS_triple_deviance_over_phi": 2 * (triple.fun - r.fun) / phi}
    lx = np.log(LARGE)
    slope = lambda ws: np.polyfit(lx, np.log(ws), 1)[0]
    s0 = slope([o["A1"][str(N)]["width10_90"] for N in LARGE])
    nb = [-1 / slope([bw[N][b] for N in LARGE]) for b in range(B_A1)]
    o["A4"] = {"N": LARGE, "slope_logw_logN": s0, "nu_eff": -1 / s0, "nu_eff_se": sd(nb), "nu_eff_ci": ci(nb)}
    o["instances"] = int(sum(D[N][:, 1].sum() for N in D))
    return o


def main():
    os.makedirs(RES, exist_ok=True)
    print("seed:", SEED, "(from ECDYSIS_SEED)" if SEED_FROM_ENV else "(ECDYSIS_SEED not set: fixed default)", flush=True)
    with Pool(os.cpu_count() or 1) as pool:  # worker count does not affect any result: every instance has its own seed
        for arm in ARMS:
            generate(arm, pool)
    A = {arm: analyse(arm) for arm in ARMS}
    full = {"seed": SEED, "seed_from_environment": SEED_FROM_ENV, "solver": "MiniSat 2.2 (python-sat)",
            "bootstrap_resamples": {"A1_A4": B_A1, "A2_A3": B_COLLAPSE}, "arms": A}
    with open(os.path.join(RES, "analysis.json"), "w") as f:
        json.dump(full, f, indent=1, sort_keys=True, default=float)
        f.write("\n")
    r4 = lambda x: round(float(x), 4)
    out = {"instances_per_arm": A["dup"]["instances"]}
    assert A["dup"]["instances"] == A["nodup"]["instances"]
    for arm in ARMS:
        a = A[arm]
        out["alpha_c_small_" + arm] = r4(a["A2"]["alpha_c"])          # collapse, N = 12-100
        out["nu_small_" + arm] = r4(a["A2"]["nu"])
        out["phi_small_" + arm] = r4(a["A2"]["phi"])                  # residual deviance / df of that collapse
        out["alpha_c_large_" + arm] = r4(a["A3"]["alpha_c"])          # collapse, N = 50-200
        out["nu_eff_" + arm] = r4(a["A4"]["nu_eff"])                  # width exponent, N = 50-200
        out["ks_law_miss_150_" + arm] = r4(a["A1"]["150"]["obs_minus_KS_law"])
        out["ks_law_miss_200_" + arm] = r4(a["A1"]["200"]["obs_minus_KS_law"])
    mx = lambda f: r4(max(f(A[arm]) for arm in ARMS))                 # bootstrap standard errors, the larger arm
    out["se_alpha_c_small"] = mx(lambda a: a["A2"]["alpha_c_se"])
    out["se_nu_small"] = mx(lambda a: a["A2"]["nu_se"])
    out["se_alpha_c_large"] = mx(lambda a: a["A3"]["alpha_c_se"])
    out["se_nu_eff"] = mx(lambda a: a["A4"]["nu_eff_se"])
    out["se_alpha50_large"] = mx(lambda a: max(a["A1"]["150"]["alpha50_se"], a["A1"]["200"]["alpha50_se"]))
    assert len(out) <= 20
    with open(os.path.join(RES, "outputs.json"), "w") as f:
        json.dump(out, f, indent=1)
        f.write("\n")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
