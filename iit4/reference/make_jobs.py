"""The networks PyPhi was run on for pyphi-c1a7f4e.json: PQRS in its 16 states in the authors' order and reversed, PQRS
in 0101 under the other 22 orders of its units, and seven random networks from a fixed seed (deterministic, noisy, one
with a MAXENT unit; three to five units; states drawn from those PyPhi can reach).

Run with: python3 iit4/reference/make_jobs.py inputs jobs.json (inputs: the claim's data of record)
"""

import itertools
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from iit4 import check, engine as E  # noqa: E402


def idx(s):
    return sum(v << i for i, v in enumerate(s))


def permuted(tpm, state, perm, labels):
    n = len(perm)
    rows = []
    for s in E.all_states(n):
        original = [0] * n
        for j in range(n):
            original[perm[j]] = s[j]
        nxt = tpm[idx(original)]
        rows.append([float(nxt[perm[j]]) for j in range(n)])
    return rows, [state[perm[j]] for j in range(n)], "".join(labels[perm[j]] for j in range(n))


def reachable(tpm, n):
    tpm = np.array(tpm)
    return [list(s) for s in E.all_states(n)
            if np.any(np.logical_and(-1 < tpm - np.array(s), tpm - np.array(s) < 1).all(-1))]


def jobs(inputs):
    tpm, state = check.read_inputs(inputs)["pqrs"]
    tpm = [list(map(float, r)) for r in np.array(tpm)]
    out = [{"name": "PQRS", "tpm": tpm, "cm": None, "labels": "PQRS", "states": [list(s) for s in E.all_states(4)],
            "nodes": None}]
    rev, _, lab = permuted(tpm, state, [3, 2, 1, 0], "PQRS")
    out.append({"name": "SRQP", "tpm": rev, "cm": None, "labels": lab,
                "states": [[s[3], s[2], s[1], s[0]] for s in E.all_states(4)], "nodes": None})
    for perm in itertools.permutations(range(4)):
        if perm in ((0, 1, 2, 3), (3, 2, 1, 0)):
            continue
        t, st, lab = permuted(tpm, state, perm, "PQRS")
        out.append({"name": "perm-" + lab, "tpm": t, "cm": None, "labels": lab, "states": [st], "nodes": None})
    rng = np.random.default_rng(20261012)

    def random_net(name, n, kind, nstates, density=0.6, maxent=()):
        cm = (rng.random((n, n)) < density).astype(int)
        for j in range(n):
            if not cm[:, j].any():
                cm[rng.integers(n), j] = 1
        for j in maxent:
            cm[:, j] = 0
            cm[j, j] = 1
        tables = []
        for j in range(n):
            k = int(cm[:, j].sum())
            if j in maxent:
                tables.append(np.full(2 ** k, 0.5))
            elif kind == "det":
                tables.append(rng.integers(0, 2, 2 ** k).astype(float))
            else:
                tables.append(rng.choice([0.0, 0.2, 0.5, 0.8, 1.0], 2 ** k))
        rows = [[float(tables[j][idx([s[i] for i in range(n) if cm[i, j]])]) for j in range(n)]
                for s in E.all_states(n)]
        states = reachable(rows, n)
        pick = [states[i] for i in sorted(rng.choice(len(states), min(nstates, len(states)), replace=False))]
        return {"name": name, "tpm": rows, "cm": cm.tolist(), "labels": "ABCDE"[:n], "states": pick, "nodes": None}

    out += [random_net("R3-det", 3, "det", 3), random_net("R3-prob", 3, "prob", 3, density=1.0),
            random_net("R4-det", 4, "det", 3), random_net("R4-maxent", 4, "det", 2, maxent=(2,)),
            random_net("R4-prob", 4, "prob", 2), random_net("R4-det-b", 4, "det", 3, density=0.5),
            random_net("R5-det", 5, "det", 1, density=0.45)]
    return out


if __name__ == "__main__":
    with open(sys.argv[2], "w") as f:
        json.dump(jobs(sys.argv[1]), f)
