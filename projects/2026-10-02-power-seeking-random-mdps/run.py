"""The v2 receipt bundle's single entry point.

    python3 run.py        -> results/partA.csv, partB.csv, recheck.csv, summary.json, outputs.json

Part A: constructed deterministic MDPs satisfying the copy condition of Turner et al., Proposition 6.9.
Part B: random deterministic MDPs (n = 20, out-degree uniform on {1, 2, 3}).
Then the pre-registered analysis (PLAN.md), the 10^5-sample re-checks of every Part A falsifier hit and
every Part B reversal, and the cross-check of policy iteration against plain value iteration.

ALL randomness comes from the environment variable ECDYSIS_SEED (64 hex characters): the master integer
seed is int(seed[:16], 16), and every instance and every reward sample is drawn from numpy generators
seeded by [master, stream, instance, salt]. With no ECDYSIS_SEED set, the fixed default below is used; its
master seed is 20261002, the seed of the v1-era run, so the default run regenerates the v1 instances.
The clock is never read.
"""
import csv
import json
import math
import os
import re
import sys

import numpy as np
from scipy.stats import binomtest

from mdp import optimal_values, pad_succ, start_stats

DEFAULT_SEED = "000000000135288a" + "0" * 48
GAMMAS = [0.1, 0.5, 0.9, 0.99, 0.999]
M = 4000            # reward samples per instance and discount rate
N_A = 200           # Part A instances
N_B = 1000          # Part B instances
MB = 100_000        # reward samples for a re-check
CH = 20_000         # re-check chunk size (salts 1..5)
VI_SWEEPS = 40_000
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")


def master_seed():
    s = os.environ.get("ECDYSIS_SEED")
    if s is None:
        print("ECDYSIS_SEED is not set: using the fixed default seed", DEFAULT_SEED)
        s = DEFAULT_SEED
    s = s.strip().lower()
    if not re.fullmatch(r"[0-9a-f]{64}", s):
        sys.exit("ECDYSIS_SEED must be 64 hexadecimal characters")
    return s, int(s[:16], 16)


# ---------------------------------------------------------------- instances

def random_out(rng, pool, lo=1, hi=3):
    d = int(rng.integers(lo, hi + 1))
    d = min(d, len(pool))
    return [int(x) for x in rng.choice(pool, size=d, replace=False)]


def build_A(seed, i):
    """Start 0 -> a' : region G' (states 1..k); a : a copy of G' (k+1..2k) plus extra states.
    Returns the successor lists and the copy map phi (G' state -> copy state)."""
    rng = np.random.default_rng([seed, 1, i])
    k = int(rng.integers(3, 9))
    m = int(rng.integers(1, 9))
    G = list(range(1, k + 1))
    C = list(range(k + 1, 2 * k + 1))
    X = list(range(2 * k + 1, 2 * k + 1 + m))
    phi = {g: c for g, c in zip(G, C)}
    succ = [None] * (1 + 2 * k + m)
    for g in G:
        succ[g] = random_out(rng, G)
    for g in G:  # the copy keeps G's edges, then may gain extra options
        succ[phi[g]] = [phi[t] for t in succ[g]]
        if rng.random() < 0.5:
            succ[phi[g]].append(int(rng.choice(X)))
    if X[0] not in succ[C[0]] and not any(x in succ[C[0]] for x in X):
        succ[C[0]].append(X[0])  # the copy's entry state gains at least one option
    for x in X:
        succ[x] = random_out(rng, C + X)
    succ[0] = [C[0], G[0]]  # action a (index 0) -> copy entry; a' -> G' entry
    for u in range(1, len(succ)):
        succ[u] = list(dict.fromkeys(succ[u]))
    return succ, phi


def check_copy(succ, phi):
    """Sufficient check of Prop. 6.9's conditions: no return to 0; G' closed; every copied state's
    successors contain the image of the original's successors."""
    ok = all(0 not in succ[u] for u in range(1, len(succ)))
    G = set(phi)
    for g in G:
        if not set(succ[g]) <= G:
            ok = False
        if not {phi[t] for t in succ[g]} <= set(succ[phi[g]]):
            ok = False
    return ok


def build_B(seed, i, n=20):
    rng = np.random.default_rng([seed, 2, i])
    pool = np.arange(n)
    succ = [random_out(rng, pool) for _ in range(n)]
    # state 0: exactly two distinct successors, neither 0 (equivalent to resampling until so)
    succ[0] = [int(x) for x in rng.choice(np.arange(1, n), size=2, replace=False)]
    return succ


def rewards(seed, part, i, n, m, salt=0):
    rng = np.random.default_rng([seed, 10 + part, i, salt])
    return rng.random((m, n))


# ---------------------------------------------------------------- statistics

def wilson(k, n, z=1.96):
    if n == 0:
        return [None, None]
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [c - h, c + h]


def zscore(p, m):
    return (p - 0.5) / math.sqrt(0.25 / m)


def recheck_stats(seed, part, succ, g, i):
    """P_opt of the first action and the POWER difference on 10^5 fresh reward samples (salts 1..5)."""
    S = pad_succ(succ)
    s1, s2 = succ[0]
    diffs, pd = [], []
    k = (1 - g) / g
    for c in range(MB // CH):
        R = rewards(seed, part, i, len(succ), CH, salt=1 + c)
        V = optimal_values(S, R, g)
        diffs.append(V[:, s1] - V[:, s2])
        pd.append(k * ((V[:, s1] - R[:, s1]) - (V[:, s2] - R[:, s2])))
    d = np.concatenate(diffs)
    p = np.concatenate(pd)
    p1 = float(np.mean(d > 0))
    return p1, float(p.mean()), float(p.std(ddof=1) / math.sqrt(MB))


def a_falsifier(p_opt, m, power_diff, se):
    """The pre-registered Part A falsifier on one instance-gamma pair."""
    pv = binomtest(round(p_opt * m), m, 0.5, alternative="less").pvalue
    return pv < 1e-4 or power_diff < -4 * se, pv


def write_csv(rows, name, fields=None):
    with open(os.path.join(OUT, name), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields or list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def r6(x):
    return round(float(x), 6)


# ---------------------------------------------------------------- main

def main():
    seed_hex, seed = master_seed()
    os.makedirs(OUT, exist_ok=True)

    # ---- Part A
    A, copy_fail = [], 0
    for i in range(N_A):
        succ, phi = build_A(seed, i)
        if not check_copy(succ, phi):
            copy_fail += 1
        R = rewards(seed, 1, i, len(succ), M)
        for g in GAMMAS:
            A.append(dict(part="A", inst=i, n=len(succ), gamma=g, **start_stats(succ, g, R)))
    write_csv(A, "partA.csv")
    print("Part A done", flush=True)

    # ---- Part B
    B = []
    for i in range(N_B):
        succ = build_B(seed, i)
        R = rewards(seed, 2, i, len(succ), M)
        for g in GAMMAS:
            B.append(dict(part="B", inst=i, n=len(succ), gamma=g, **start_stats(succ, g, R)))
        if i % 100 == 99:
            print("Part B", i + 1, flush=True)
    write_csv(B, "partB.csv")

    # ---- analysis, Part A
    summary = {"seed": seed_hex, "master_seed": seed}
    hits = []
    for r in A:
        bad, pv = a_falsifier(r["p_opt_a1"], M, r["power_diff"], r["power_diff_se"])
        if bad:
            hits.append(dict(inst=r["inst"], gamma=r["gamma"], p_opt=r["p_opt_a1"], p=pv,
                             power_diff=r["power_diff"], se=r["power_diff_se"]))
    recheck_rows, survivors = [], 0
    for h in hits:
        succ, _ = build_A(seed, h["inst"])
        p1, pdm, se = recheck_stats(seed, 1, succ, h["gamma"], h["inst"])
        bad, pv = a_falsifier(p1, MB, pdm, se)
        survivors += int(bad)
        recheck_rows.append(dict(part="A", inst=h["inst"], gamma=h["gamma"], p_opt_a1_4000=h["p_opt"],
                                 p_opt_a1=p1, z=round(zscore(p1, MB), 2), power_diff=pdm,
                                 power_diff_se=se, confirmed=int(bad)))
    byg = {}
    for r in A:
        byg.setdefault(r["gamma"], []).append(r)
    summary["A"] = dict(
        n_pairs=len(A), copy_check_failures=copy_fail, falsifier_hits=hits, falsifier_survivors=survivors,
        ties=int(sum(r["ties"] for r in A)),
        by_gamma={str(g): dict(
            min_p_opt=min(r["p_opt_a1"] for r in rs),
            mean_p_opt=r6(sum(r["p_opt_a1"] for r in rs) / len(rs)),
            n_below_half=sum(r["p_opt_a1"] < 0.5 for r in rs),
            min_power_diff_z=round(min(r["power_diff"] / r["power_diff_se"] if r["power_diff_se"] > 0 else 0
                                       for r in rs), 2),
        ) for g, rs in sorted(byg.items())},
    )

    # ---- analysis, Part B
    byg = {}
    for r in B:
        byg.setdefault(r["gamma"], []).append(r)
    summary["B"] = {}
    reversals = []
    for g, rs in sorted(byg.items()):
        dec = [r for r in rs if abs(zscore(r["p_opt_a1"], M)) > 3]
        pw = [r for r in dec if abs(r["power_diff"]) > 3 * r["power_diff_se"]]
        agree = [r for r in pw if (r["power_diff"] > 0) == (r["p_opt_a1"] > 0.5)]
        for r in pw:
            if (r["power_diff"] > 0) != (r["p_opt_a1"] > 0.5):
                reversals.append(dict(inst=r["inst"], gamma=g, p_opt_a1=r["p_opt_a1"],
                                      power_diff=r["power_diff"], se=r["power_diff_se"]))
        rc = [r for r in dec if r["reach1"] != r["reach2"]]
        ragree = [r for r in rc if (r["reach1"] > r["reach2"]) == (r["p_opt_a1"] > 0.5)]
        both = [r for r in pw if r["reach1"] != r["reach2"]]
        summary["B"][str(g)] = dict(
            n=len(rs), decided=len(dec), decided_frac=len(dec) / len(rs), decided_ci=wilson(len(dec), len(rs)),
            power_untied=len(pw), power_agree=len(agree),
            A_power=len(agree) / len(pw) if pw else None, A_power_ci=wilson(len(agree), len(pw)),
            reach_untied=len(rc), reach_equal=len(dec) - len(rc), reach_agree=len(ragree),
            A_reach=len(ragree) / len(rc) if rc else None, A_reach_ci=wilson(len(ragree), len(rc)),
            both_untied=len(both),
            ties=int(sum(r["ties"] for r in rs)),
        )

    # ---- re-check every Part B reversal on 10^5 fresh samples
    confirmed, min_z, min_gap = 0, None, None
    for n_done, r in enumerate(reversals):
        i, g = r["inst"], r["gamma"]
        p1, pdm, se = recheck_stats(seed, 2, build_B(seed, i), g, i)
        z = zscore(p1, MB)
        conf = abs(z) > 3 and abs(pdm) > 3 * se and ((pdm > 0) != (p1 > 0.5))
        if conf:
            confirmed += 1
            min_z = abs(z) if min_z is None else min(min_z, abs(z))
            gap = abs(pdm) / se
            min_gap = gap if min_gap is None else min(min_gap, gap)
        recheck_rows.append(dict(part="B", inst=i, gamma=g, p_opt_a1_4000=r["p_opt_a1"], p_opt_a1=p1,
                                 z=round(z, 2), power_diff=pdm, power_diff_se=se, confirmed=int(conf)))
        if n_done % 20 == 19:
            print("re-check", n_done + 1, "of", len(reversals), flush=True)
    write_csv(recheck_rows, "recheck.csv",
              fields=["part", "inst", "gamma", "p_opt_a1_4000", "p_opt_a1", "z", "power_diff",
                      "power_diff_se", "confirmed"])
    summary["B_reversals"] = dict(
        found=len(reversals), distinct_instances=len({r["inst"] for r in reversals}), confirmed=confirmed,
        by_gamma={str(g): sum(r["gamma"] == g for r in reversals) for g in GAMMAS},
        min_confirmed_abs_z=None if min_z is None else round(min_z, 2),
        min_confirmed_power_gap_se=None if min_gap is None else round(min_gap, 2),
    )

    # ---- policy iteration against plain value iteration (Part B instances 0-3, 200 samples)
    vi = {}
    for g in GAMMAS:
        worst = 0.0
        for i in range(4):
            succ = build_B(seed, i)
            S = pad_succ(succ)
            R = rewards(seed, 2, i, len(succ), M)[:200]
            V_pi = optimal_values(S, R, g)
            V = R.copy()
            for _ in range(VI_SWEEPS):
                V = R + g * V[:, S].max(axis=2)
            worst = max(worst, float(np.abs(V - V_pi).max()))
        vi[str(g)] = worst
    summary["vi_check"] = dict(sweeps=VI_SWEEPS, instances="B 0-3", samples=200, max_abs_diff=vi)

    with open(os.path.join(OUT, "summary.json"), "w") as f:
        json.dump(summary, f, indent=1)
        f.write("\n")

    # ---- the named outputs a cross-check compares (at most 20)
    b = summary["B"]
    g90, g99 = b["0.9"], b["0.99"]
    out = {
        "a_copy_check_failures": copy_fail,
        "a_falsifier_hits_m4000": len(hits),
        "a_falsifier_survivors": survivors,
        "a_min_p_opt": r6(min(r["p_opt_a1"] for r in A)),
        "b_decided_frac_g0.1": r6(b["0.1"]["decided_frac"]),
        "b_decided_frac_g0.5": r6(b["0.5"]["decided_frac"]),
        "b_decided_frac_g0.9": r6(g90["decided_frac"]),
        "b_decided_frac_g0.99": r6(g99["decided_frac"]),
        "b_A_power_g0.9": r6(g90["A_power"]),
        "b_A_power_lo_g0.9": r6(g90["A_power_ci"][0]),
        "b_A_power_g0.99": r6(g99["A_power"]),
        "b_A_power_lo_g0.99": r6(g99["A_power_ci"][0]),
        "b_reversals_found": len(reversals),
        "b_reversals_confirmed_frac": r6(confirmed / len(reversals)) if reversals else 0.0,
        "b_A_reach_g0.99": r6(g99["A_reach"]),
        "b_A_reach_lo_g0.99": r6(g99["A_reach_ci"][0]),
        "b_A_reach_hi_g0.99": r6(g99["A_reach_ci"][1]),
        "b_reach_equal_frac_g0.99": r6(g99["reach_equal"] / g99["decided"]),
        "exact_ties": summary["A"]["ties"] + sum(v["ties"] for v in b.values()),
        "vi_max_abs_diff": float(f"{max(vi.values()):.3e}"),
    }
    assert len(out) <= 20 and all(math.isfinite(v) for v in out.values())
    with open(os.path.join(OUT, "outputs.json"), "w") as f:
        json.dump(out, f, indent=1)
        f.write("\n")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
