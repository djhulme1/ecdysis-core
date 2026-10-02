"""Drafting-stage checks (not pre-registered; exploratory): (1) convergence of the A2/A3 collapse fits from many starts;
(2) profile likelihood of alpha_c (nu, y50, s re-optimised) to see how strongly the data disfavour KS's 4.17. -> results/check_fit.json"""
import csv, json, os, itertools
import numpy as np
from scipy.optimize import minimize
from scipy.special import expit
HERE = os.path.dirname(os.path.abspath(__file__))
rows = list(csv.DictReader(open(os.path.join(HERE, "results", "counts.csv"))))
D = {}
for r in rows:
    D.setdefault(int(r["N"]), []).append((float(r["alpha"]), int(r["samples"]), int(r["unsat"])))
D = {n: np.array(sorted(v)) for n, v in D.items()}
def nll(p, k, n):
    p = np.clip(p, 1e-12, 1 - 1e-12); return -np.sum(k * np.log(p) + (n - k) * np.log(1 - p))
def F(th, nl, ac=None):
    if ac is None: ac, nu, y50, s = th
    else: nu, y50, s = th
    if nu <= 0.2 or s <= 0: return 1e18
    return sum(nll(expit((N ** (1 / nu) * (D[N][:, 0] - ac) / ac - y50) / s), D[N][:, 2], D[N][:, 1]) for N in nl)
opt = {"xatol": 1e-8, "fatol": 1e-10, "maxiter": 40000}
out = {}
for key, nl in (("A2", [12, 20, 24, 40, 50, 100]), ("A3", [50, 100, 150, 200])):
    starts = list(itertools.product([4.0, 4.17, 4.27], [1.2, 1.5, 2.0, 2.6], [0.3, 0.7, 1.2], [0.3, 0.7]))
    res = [minimize(F, list(s), args=(nl,), method="Nelder-Mead", options=opt) for s in starts]
    funs = np.array([r.fun for r in res]); best = res[int(funs.argmin())]
    good = [r.x.tolist() for r in res if r.fun < best.fun + 1e-3]
    prof = {}
    for ac in np.round(np.arange(4.00, 4.3001, 0.005), 3):
        rr = min((minimize(F, s, args=(nl, ac), method="Nelder-Mead", options=opt) for s in ([1.5, 0.7, 0.5], [2.0, 0.5, 0.5], [1.2, 1.2, 0.7])), key=lambda r: r.fun)
        prof[float(ac)] = {"dev": 2 * (rr.fun - best.fun), "nu": rr.x[0], "y50": rr.x[1]}
    # goodness of fit: residual deviance against the saturated (per-point) model
    sat = sum(nll(np.clip(D[N][:, 2] / D[N][:, 1], 1e-12, 1 - 1e-12), D[N][:, 2], D[N][:, 1]) for N in nl)
    npts = sum(len(D[N]) for N in nl)
    # KS's published parameters (alpha_c 4.17, nu 1.5, y50 0.74) with only the scale s fitted
    ks = minimize(lambda t: F([1.5, 0.74, t[0]], nl, 4.17), [0.5], method="Nelder-Mead", options=opt)
    out[key + "_fit"] = {"residual_deviance": 2 * (best.fun - sat), "points": npts, "df": npts - 4,
                         "KS_params_dev_vs_best": 2 * (ks.fun - best.fun), "KS_params_s": ks.x[0]}
    out[key] = {"starts": len(starts), "best_nll": best.fun, "best": best.x.tolist(),
                "n_starts_within_1e-3": len(good), "spread_of_converged_alpha_c": [min(g[0] for g in good), max(g[0] for g in good)],
                "profile_deviance": prof}
# quasi-likelihood 95% profile interval for alpha_c: deviance / phi <= 3.84, phi = residual deviance / df (grid step 0.005)
for key in ("A2", "A3"):
    phi = out[key + "_fit"]["residual_deviance"] / out[key + "_fit"]["df"]
    inside = [ac for ac, p in out[key]["profile_deviance"].items() if p["dev"] / phi <= 3.84]
    out[key + "_fit"].update({"phi": phi, "quasi_profile_ci_alpha_c": [min(inside), max(inside)],
                              "dev_over_phi_at_4.17": out[key]["profile_deviance"][4.17]["dev"] / phi})
json.dump(out, open(os.path.join(HERE, "results", "check_fit.json"), "w"), indent=1, default=float)
for k in ("A2", "A3"):
    o = out[k]; print(k, o["best"], o["n_starts_within_1e-3"], "/", o["starts"], o["spread_of_converged_alpha_c"])
    for ac in (4.07, 4.12, 4.17, 4.2, 4.22, 4.27): 
        p = o["profile_deviance"][ac]; print("  ac=%.3f dev=%.1f nu=%.3f y50=%.3f" % (ac, p["dev"], p["nu"], p["y50"]))
    print(" ", out[k + "_fit"])
