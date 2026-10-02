"""Entry point. python3 run.py [--recheck]  -> results/*.csv

Part A: constructed instances satisfying Turner et al. Prop. 6.9's copy condition.
Part B: random deterministic MDPs (n=20, out-degree U{1,2,3}).
Master seed 20261002; every instance and every reward sample is regenerated from seeds.
"""
import csv
import os
import sys
import time

import numpy as np

from mdp import start_stats

SEED = 20261002
GAMMAS = [0.1, 0.5, 0.9, 0.99, 0.999]
M = 4000
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")


def random_out(rng, pool, lo=1, hi=3):
    d = int(rng.integers(lo, hi + 1))
    d = min(d, len(pool))
    return [int(x) for x in rng.choice(pool, size=d, replace=False)]


def build_A(i):
    """Start 0 -> a' : region G' (states 1..k), a : copy of G' (k+1..2k) plus extras.
    Returns succ, the copy map phi (G' state -> copy state)."""
    rng = np.random.default_rng([SEED, 1, i])
    k = int(rng.integers(3, 9))
    m = int(rng.integers(1, 9))
    G = list(range(1, k + 1))
    C = list(range(k + 1, 2 * k + 1))
    X = list(range(2 * k + 1, 2 * k + 1 + m))
    phi = {g: c for g, c in zip(G, C)}
    succ = [None] * (1 + 2 * k + m)
    for g in G:
        succ[g] = random_out(rng, G)
    for g in G:  # copy keeps G's edges, then gains extra options
        succ[phi[g]] = [phi[t] for t in succ[g]]
        if rng.random() < 0.5:
            succ[phi[g]].append(int(rng.choice(X)))
    if X[0] not in succ[C[0]] and not any(x in succ[C[0]] for x in X):
        succ[C[0]].append(X[0])  # guarantee the copy's entry gains at least one option
    for x in X:
        succ[x] = random_out(rng, C + X)
    succ[0] = [C[0], G[0]]  # action a (index 0) -> copy entry; a' -> G' entry
    for u in range(1, len(succ)):
        succ[u] = list(dict.fromkeys(succ[u]))
    return succ, phi


def check_copy(succ, phi):
    """Prop 6.9 condition (sufficient check): no return to 0; regions disjoint;
    every copied state's successors contain the image of the original's successors."""
    ok = all(0 not in succ[u] for u in range(1, len(succ)))
    G = set(phi)
    for g in G:
        if not set(succ[g]) <= G:
            ok = False
        if not {phi[t] for t in succ[g]} <= set(succ[phi[g]]):
            ok = False
    return ok


def build_B(i, n=20):
    rng = np.random.default_rng([SEED, 2, i])
    pool = np.arange(n)
    succ = [random_out(rng, pool) for _ in range(n)]
    # state 0: exactly two distinct successors, neither 0 (equivalent to resampling until so)
    succ[0] = [int(x) for x in rng.choice(np.arange(1, n), size=2, replace=False)]
    return succ


def rewards(part, i, n, m, salt=0):
    rng = np.random.default_rng([SEED, 10 + part, i, salt])
    return rng.random((m, n))


def main():
    os.makedirs(OUT, exist_ok=True)
    t0 = time.time()
    # Part A
    rows = []
    for i in range(200):
        succ, phi = build_A(i)
        assert check_copy(succ, phi), i
        R = rewards(1, i, len(succ), M)
        for g in GAMMAS:
            st = start_stats(succ, g, R)
            rows.append(dict(part="A", inst=i, n=len(succ), gamma=g, **st))
    write(rows, "partA.csv")
    print("Part A done", round(time.time() - t0, 1), "s", flush=True)
    rows = []
    for i in range(1000):
        succ = build_B(i)
        R = rewards(2, i, len(succ), M)
        for g in GAMMAS:
            st = start_stats(succ, g, R)
            rows.append(dict(part="B", inst=i, n=len(succ), gamma=g, **st))
        if i % 100 == 0:
            print("B", i, round(time.time() - t0, 1), "s", flush=True)
    write(rows, "partB.csv")
    print("Part B done", round(time.time() - t0, 1), "s")


def write(rows, name):
    with open(os.path.join(OUT, name), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    main()
