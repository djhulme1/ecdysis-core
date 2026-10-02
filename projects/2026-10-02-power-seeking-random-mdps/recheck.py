"""python3 recheck.py -> results/recheck.csv
Re-checks every Part B reversal found at M=4000 with 10^5 fresh reward samples (salt=1),
as pre-registered for prediction B2. A reversal is confirmed when, on the fresh samples,
|z| of P_opt - 0.5 exceeds 3, the POWER difference exceeds 3 SE, and their signs still disagree."""
import csv, json, math, os
import numpy as np
from mdp import pad_succ, optimal_values, reach_count
from run import build_B, rewards

HERE = os.path.dirname(os.path.abspath(__file__))
MB = 100_000
CH = 20_000

def stats(succ, g, i):
    S = pad_succ(succ); s1, s2 = succ[0]
    diffs, pd = [], []
    for c in range(MB // CH):
        R = rewards(2, i, len(succ), CH, salt=1 + c)
        V = optimal_values(S, R, g)
        diffs.append(V[:, s1] - V[:, s2])
        k = (1 - g) / g
        pd.append(k * ((V[:, s1] - R[:, s1]) - (V[:, s2] - R[:, s2])))
    d = np.concatenate(diffs); p = np.concatenate(pd)
    p1 = float(np.mean(d > 0))
    return p1, (p1 - 0.5) / math.sqrt(0.25 / MB), float(p.mean()), float(p.std(ddof=1) / math.sqrt(MB))

rev = json.load(open(os.path.join(HERE, "results", "summary.json")))["B_reversals_M4000"]
rows = []
for r in rev:
    i, g = r["inst"], r["gamma"]
    p1, z, pdm, se = stats(build_B(i), g, i)
    conf = abs(z) > 3 and abs(pdm) > 3 * se and ((pdm > 0) != (p1 > 0.5))
    rows.append(dict(inst=i, gamma=g, p_opt_a1_4000=r["p_opt_a1"], p_opt_a1=p1, z=round(z, 2),
                     power_diff=pdm, power_diff_se=se, confirmed=int(conf)))
    print(rows[-1], flush=True)
with open(os.path.join(HERE, "results", "recheck.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
print("confirmed", sum(r["confirmed"] for r in rows), "of", len(rows))
