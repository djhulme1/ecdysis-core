"""python3 analyse.py -> results/summary.json (pre-registered quantities from PLAN.md)."""
import csv
import json
import math
import os

from scipy.stats import binomtest

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "results")
M = 4000


def load(name):
    with open(os.path.join(RES, name)) as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        for k in r:
            if k != "part":
                r[k] = float(r[k])
    return rows


def wilson(k, n, z=1.96):
    if n == 0:
        return [None, None]
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(c - h, 4), round(c + h, 4)]


def zscore(p):
    return (p - 0.5) / math.sqrt(0.25 / M)


def main():
    out = {}
    A = load("partA.csv")
    viol = []
    for r in A:
        k = round(r["p_opt_a1"] * M)
        pv = binomtest(k, M, 0.5, alternative="less").pvalue
        pw_bad = r["power_diff"] < -4 * r["power_diff_se"]
        if pv < 1e-4 or pw_bad:
            viol.append(dict(inst=int(r["inst"]), gamma=r["gamma"], p_opt=r["p_opt_a1"], p=pv,
                             power_diff=r["power_diff"], se=r["power_diff_se"]))
    byg = {}
    for r in A:
        g = r["gamma"]
        byg.setdefault(g, []).append(r)
    out["A"] = dict(
        violations=viol,
        n_pairs=len(A),
        ties=int(sum(r["ties"] for r in A)),
        by_gamma={str(g): dict(
            min_p_opt=round(min(r["p_opt_a1"] for r in rs), 4),
            mean_p_opt=round(sum(r["p_opt_a1"] for r in rs) / len(rs), 4),
            n_below_half=sum(r["p_opt_a1"] < 0.5 for r in rs),
            min_power_diff_z=round(min(r["power_diff"] / r["power_diff_se"] if r["power_diff_se"] > 0 else 0 for r in rs), 2),
        ) for g, rs in sorted(byg.items())},
    )
    B = load("partB.csv")
    byg = {}
    for r in B:
        byg.setdefault(r["gamma"], []).append(r)
    out["B"] = {}
    reversals = []
    for g, rs in sorted(byg.items()):
        dec = [r for r in rs if abs(zscore(r["p_opt_a1"])) > 3]
        pw = [r for r in dec if abs(r["power_diff"]) > 3 * r["power_diff_se"]]
        agree = [r for r in pw if (r["power_diff"] > 0) == (r["p_opt_a1"] > 0.5)]
        for r in pw:
            if (r["power_diff"] > 0) != (r["p_opt_a1"] > 0.5):
                reversals.append(dict(inst=int(r["inst"]), gamma=g, p_opt_a1=r["p_opt_a1"],
                                      power_diff=r["power_diff"], se=r["power_diff_se"]))
        rc = [r for r in dec if r["reach1"] != r["reach2"]]
        ragree = [r for r in rc if (r["reach1"] > r["reach2"]) == (r["p_opt_a1"] > 0.5)]
        out["B"][str(g)] = dict(
            n=len(rs), decided=len(dec), decided_frac=round(len(dec) / len(rs), 4),
            decided_ci=wilson(len(dec), len(rs)),
            power_untied=len(pw), A_power=round(len(agree) / len(pw), 4) if pw else None,
            A_power_ci=wilson(len(agree), len(pw)),
            reach_untied=len(rc), reach_equal=len(dec) - len(rc),
            A_reach=round(len(ragree) / len(rc), 4) if rc else None,
            A_reach_ci=wilson(len(ragree), len(rc)),
            ties=int(sum(r["ties"] for r in rs)),
        )
    out["B_reversals_M4000"] = reversals
    with open(os.path.join(RES, "summary.json"), "w") as f:
        json.dump(out, f, indent=1)
    print(json.dumps({k: v for k, v in out.items() if k != "B_reversals_M4000"}, indent=1))
    print("reversals:", len(reversals))


if __name__ == "__main__":
    main()
