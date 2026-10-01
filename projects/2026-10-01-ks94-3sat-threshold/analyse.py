"""Pre-registered analyses A1-A5 on results/counts.csv -> results/analysis.json. Bootstrap seed 20261001."""
import csv, json, os
import numpy as np
from scipy.optimize import minimize
from scipy.special import expit

HERE = os.path.dirname(os.path.abspath(__file__))
rows = list(csv.DictReader(open(os.path.join(HERE, "results", "counts.csv"))))
D = {}
for r in rows:
    D.setdefault(int(r["N"]), []).append((float(r["alpha"]), int(r["samples"]), int(r["unsat"])))
D = {n: np.array(sorted(v)) for n, v in D.items()}
rng = np.random.default_rng(20261001)
B = 1000

def nll(p, k, n):
    p = np.clip(p, 1e-12, 1 - 1e-12)
    return -np.sum(k * np.log(p) + (n - k) * np.log(1 - p))

def fit_logistic(a, n, k):  # P = expit((a - m)/s)
    f = lambda th: nll(expit((a - th[0]) / abs(th[1])), k, n)
    r = minimize(f, [4.3, 0.1], method="Nelder-Mead", options={"xatol": 1e-7, "fatol": 1e-9, "maxiter": 4000})
    m, s = r.x[0], abs(r.x[1])
    return m, 2 * np.log(9) * s  # midpoint, 10-90% width

def collapse(datasets, starts=([4.2, 1.5, 0.7, 0.5], [4.27, 2.0, 0.5, 0.5], [4.15, 1.2, 1.0, 0.5])):  # params: ac, nu, y50, s
    def f(th):
        ac, nu, y50, s = th
        if nu <= 0.2 or s <= 0: return 1e18
        tot = 0.0
        for N, a, n, k in datasets:
            y = N ** (1 / nu) * (a - ac) / ac
            tot += nll(expit((y - y50) / s), k, n)
        return tot
    best = None
    for start in starts:
        r = minimize(f, start, method="Nelder-Mead", options={"xatol": 1e-7, "fatol": 1e-9, "maxiter": 20000})
        if best is None or r.fun < best.fun: best = r
    return best.x

def resample(n_list):
    return {N: np.column_stack([D[N][:, 0], D[N][:, 1], rng.binomial(D[N][:, 1].astype(int), D[N][:, 2] / D[N][:, 1])]) for N in n_list}

def ci(x): return [float(np.percentile(x, 2.5)), float(np.percentile(x, 97.5))]

Ns = sorted(D)
out = {"A1": {}, "notes": "logistic MLE; 95 percent intervals: parametric bootstrap (binomial resampling at observed fractions), %d resamples" % B}
boot_w = {N: [] for N in Ns}; boot_m = {N: [] for N in Ns}
for N in Ns:
    m, w = fit_logistic(D[N][:, 0], D[N][:, 1], D[N][:, 2])
    out["A1"][N] = {"alpha50": m, "width10_90": w}
for b in range(B):
    R = resample(Ns)
    for N in Ns:
        m, w = fit_logistic(R[N][:, 0], R[N][:, 1], R[N][:, 2]); boot_m[N].append(m); boot_w[N].append(w)
for N in Ns:
    out["A1"][N]["alpha50_ci"] = ci(boot_m[N]); out["A1"][N]["width_ci"] = ci(boot_w[N])

def ds(n_list, src):
    return [(N, src[N][:, 0], src[N][:, 1], src[N][:, 2]) for N in n_list]
small = [12, 20, 24, 40, 50, 100]; large = [50, 100, 150, 200]
for key, nl in (("A2", small), ("A3", large)):
    th = collapse(ds(nl, D)); bs = []
    for b in range(200):
        bs.append(collapse(ds(nl, resample(nl)), starts=(list(th),)))
    bs = np.array(bs)
    out[key] = {"N": nl, "alpha_c": th[0], "nu": th[1], "y50": th[2], "s": th[3],
                "alpha_c_ci": ci(bs[:, 0]), "nu_ci": ci(bs[:, 1]), "bootstrap_resamples": 200}

lx = np.log(large)
sl = lambda ws: np.polyfit(lx, np.log(ws), 1)[0]
s0 = sl([out["A1"][N]["width10_90"] for N in large])
sb = [sl([boot_w[N][b] for N in large]) for b in range(B)]
nub = [-1 / x for x in sb]
out["A4"] = {"N": large, "slope_logw_logN": s0, "nu_eff": -1 / s0, "nu_eff_ci": ci(nub)}

out["A5"] = {}
for N in (150, 200):
    ks = 4.17 + 3.1 * N ** (-2 / 3); ca = 4.24 + 6 / N
    out["A5"][N] = {"observed": out["A1"][N]["alpha50"], "ci": out["A1"][N]["alpha50_ci"], "KS_formula": ks, "CA_formula": ca,
                    "obs_minus_KS": out["A1"][N]["alpha50"] - ks, "obs_minus_CA": out["A1"][N]["alpha50"] - ca}
# also residuals of KS formula across all N
out["A5_all"] = {N: {"obs": out["A1"][N]["alpha50"], "KS": 4.17 + 3.1 * N ** (-2 / 3), "CA": 4.24 + 6 / N} for N in Ns}
json.dump(out, open(os.path.join(HERE, "results", "analysis.json"), "w"), indent=1, default=float)
print(json.dumps(out, indent=1, default=float))
