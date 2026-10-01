"""Post-review sensitivity analysis (not pre-registered): the A1 50% points, A2/A3 collapses and A4 effective exponent under both
instance models (duplicates allowed: counts.csv; no duplicate clauses: counts_nodup.csv), with overdispersion-corrected
(quasi-likelihood) profile intervals for alpha_c and nu. -> results/sensitivity.json. Bootstrap seed 20261002."""
import csv, json, os, itertools
import numpy as np
from scipy.optimize import minimize
from scipy.special import expit
HERE = os.path.dirname(os.path.abspath(__file__))
opt = {"xatol": 1e-8, "fatol": 1e-10, "maxiter": 40000}
def load(name):
    D = {}
    for r in csv.DictReader(open(os.path.join(HERE, "results", name))):
        D.setdefault(int(r["N"]), []).append((float(r["alpha"]), int(r["samples"]), int(r["unsat"])))
    return {n: np.array(sorted(v)) for n, v in D.items()}
def nll(p, k, n):
    p = np.clip(p, 1e-12, 1 - 1e-12); return -np.sum(k * np.log(p) + (n - k) * np.log(1 - p))
def fit_logistic(a, n, k):
    r = minimize(lambda th: nll(expit((a - th[0]) / abs(th[1])), k, n), [4.3, 0.1], method="Nelder-Mead", options=opt)
    return r.x[0], 2 * np.log(9) * abs(r.x[1])
def F(th, D, nl, fix=None):
    th = list(th)
    if fix:
        i, v = fix; th.insert(i, v)
    ac, nu, y50, s = th
    if nu <= 0.2 or s <= 0: return 1e18
    return sum(nll(expit((N ** (1 / nu) * (D[N][:, 0] - ac) / ac - y50) / s), D[N][:, 2], D[N][:, 1]) for N in nl)
def best(D, nl, fix=None, x0=None):
    if fix and x0 is not None:  # profile point: start from the free optimum and two perturbations
        b = [x for j, x in enumerate(x0) if j != fix[0]]
        starts = [b, [x * 1.15 for x in b], [x * 0.85 for x in b]]
        return min((minimize(F, s, args=(D, nl, fix), method="Nelder-Mead", options=opt) for s in starts), key=lambda r: r.fun)
    full = list(itertools.product([4.0, 4.17, 4.27], [1.2, 1.5, 2.0], [0.4, 1.0], [0.4, 0.8]))
    starts = [[x for j, x in enumerate(s) if j != fix[0]] for s in full] if fix else full
    return min((minimize(F, s, args=(D, nl, fix), method="Nelder-Mead", options=opt) for s in starts), key=lambda r: r.fun)
def analyse(D, rng):
    o = {"A1": {}}
    for N in sorted(D):
        m, w = fit_logistic(D[N][:, 0], D[N][:, 1], D[N][:, 2]); bm = []
        for b in range(300):
            k = rng.binomial(D[N][:, 1].astype(int), D[N][:, 2] / D[N][:, 1]); bm.append(fit_logistic(D[N][:, 0], D[N][:, 1], k)[0])
        o["A1"][N] = {"alpha50": m, "alpha50_ci": [float(np.percentile(bm, 2.5)), float(np.percentile(bm, 97.5))], "width10_90": w}
    for key, nl in (("A2", [12, 20, 24, 40, 50, 100]), ("A3", [50, 100, 150, 200])):
        r = best(D, nl)
        sat = sum(nll(np.clip(D[N][:, 2] / D[N][:, 1], 1e-12, 1 - 1e-12), D[N][:, 2], D[N][:, 1]) for N in nl)
        df = sum(len(D[N]) for N in nl) - 4; phi = 2 * (r.fun - sat) / df
        prof_ac = {round(float(a), 3): 2 * (best(D, nl, (0, a), r.x).fun - r.fun) for a in np.arange(4.00, 4.3001, 0.005)}
        prof_nu = {round(float(v), 3): 2 * (best(D, nl, (1, v), r.x).fun - r.fun) for v in np.arange(1.20, 1.9001, 0.01)}
        ks = minimize(lambda t: F([4.17, 1.5, 0.74, t[0]], D, nl), [0.5], method="Nelder-Mead", options=opt)
        inside = lambda pr: [min(k for k, d in pr.items() if d / phi <= 3.84), max(k for k, d in pr.items() if d / phi <= 3.84)]
        o[key] = {"N": nl, "alpha_c": r.x[0], "nu": r.x[1], "y50": r.x[2], "s": r.x[3], "residual_deviance": 2 * (r.fun - sat), "df": df, "phi": phi,
                  "alpha_c_quasi_ci": inside(prof_ac), "nu_quasi_ci": inside(prof_nu),
                  "dev_at_4.17": prof_ac[4.17], "dev_over_phi_at_4.17": prof_ac[4.17] / phi,
                  "KS_triple_dev": 2 * (ks.fun - r.fun), "KS_triple_dev_over_phi": 2 * (ks.fun - r.fun) / phi}
    L = [50, 100, 150, 200]
    sl = np.polyfit(np.log(L), np.log([o["A1"][N]["width10_90"] for N in L]), 1)[0]
    o["A4"] = {"slope": sl, "nu_eff": -1 / sl}
    o["A5"] = {N: {"obs": o["A1"][N]["alpha50"], "obs_minus_KS": o["A1"][N]["alpha50"] - (4.17 + 3.1 * N ** (-2 / 3))} for N in (150, 200)}
    return o
rng = np.random.default_rng(20261002)
out = {"with_duplicates": analyse(load("counts.csv"), rng), "no_duplicates": analyse(load("counts_nodup.csv"), rng)}
json.dump(out, open(os.path.join(HERE, "results", "sensitivity.json"), "w"), indent=1, default=float)
for m, o in out.items():
    print(m)
    for N, a in o["A1"].items(): print("  N=%d a50=%.3f [%.3f, %.3f] w=%.3f" % (N, a["alpha50"], *a["alpha50_ci"], a["width10_90"]))
    for k in ("A2", "A3"):
        q = o[k]; print("  %s ac=%.3f %s nu=%.3f %s y50=%.2f phi=%.2f dev/phi@4.17=%.1f KS=%.1f (%.1f)" % (k, q["alpha_c"], q["alpha_c_quasi_ci"], q["nu"], q["nu_quasi_ci"], q["y50"], q["phi"], q["dev_over_phi_at_4.17"], q["KS_triple_dev"], q["KS_triple_dev_over_phi"]))
    print("  A4 nu_eff=%.3f" % o["A4"]["nu_eff"], " A5", {N: round(v["obs_minus_KS"], 4) for N, v in o["A5"].items()})
