"""Cross-check: exact policy iteration (mdp.optimal_values) against plain value iteration.
python3 vi_check.py -> results/vi_check.json
Part B instances 0-3, the first 200 reward samples of each, 40,000 value-iteration sweeps."""
import json
import os

import numpy as np

from mdp import optimal_values, pad_succ
from run import GAMMAS, OUT, build_B, rewards

SWEEPS = 40000
out = {}
for g in GAMMAS:
    worst = 0.0
    for i in range(4):
        succ = build_B(i)
        S = pad_succ(succ)
        R = rewards(2, i, len(succ), 4000)[:200]
        V_pi = optimal_values(S, R, g)
        V = R.copy()
        for _ in range(SWEEPS):
            V = R + g * V[:, S].max(axis=2)
        worst = max(worst, float(np.abs(V - V_pi).max()))
    out[str(g)] = worst
    print(g, worst)
with open(os.path.join(OUT, "vi_check.json"), "w") as f:
    json.dump({"sweeps": SWEEPS, "instances": "B 0-3", "samples": 200, "max_abs_diff": out}, f, indent=1)
