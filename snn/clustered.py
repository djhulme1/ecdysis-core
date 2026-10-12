#!/usr/bin/env python3
"""Litwin-Kumar & Doiron's clustered balanced network, simulated afresh from its Online Methods, for an Ecdysis receipt.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:621d0751f2c1b161) is from Litwin-Kumar & Doiron, "Slow
dynamics and high variability in balanced cortical networks with clustered connections", Nature Neuroscience 15(11),
1498-1505 (2012): "Even modest clustering substantially changed the behavior of these networks, introducing slow dynamics
during which clusters of neurons transiently increased or decreased their firing rate. Consequently, neurons exhibited
both fast spiking variability and slow firing rate fluctuations."

Its registered test: refuted if, in the paper's network as its Online Methods state it (4,000 excitatory and 1,000
inhibitory LIF neurons, Euler steps of 0.1 ms; clustered: 50 clusters of 80 excitatory neurons, R_EE = 2.5, in-cluster
weights x1.9; uniform: p_EE = 0.2), the excitatory neurons' mean Fano factor of 100 ms spike counts from 1.5 to 3 s,
over 9 trials of each of 12 networks from random initial voltages, is 1 or less with clustering, or exceeds the uniform
networks' by less than 0.31 (half the gap the paper reports: 1.4 against 0.78).

No input: the network is the paper's (its Online Methods and the Results' clustering rule), and nothing the authors
released is read. numpy, in the pinned pytorch image. Every rule below was fixed before any seed existed.

1. The network (Online Methods). 4,000 excitatory (E) and 1,000 inhibitory (I) leaky integrate-and-fire neurons,
   dV/dt = (mu - V)/tau + I_syn, threshold 1, reset 0, absolute refractory period 5 ms (V held), tau 15 ms (E) and
   10 ms (I); mu uniform in [1.1, 1.2] (E) and [1, 1.05] (I), drawn once per network. Synapses are differences of
   exponentials of unit area, (exp(-t/tau2) - exp(-t/tau1))/(tau2 - tau1), tau1 = 1 ms, tau2 = 3 ms from E and 2 ms
   from I; a spike adds J to the target's two filter variables at the next step. Connections are drawn independently,
   no neuron to itself: p_EI = p_IE = p_II = 0.5 with J_EI = -0.045, J_IE = 0.014, J_II = -0.057; E to E with
   J_EE = 0.024. Uniform networks: p_EE = 0.2. Clustered networks (Results): the E neurons in 50 clusters of 80 (in
   index order), p_in = R p_out with R = 2.5 and p_out = 800/(80 (R - 1) + 4000), so that each E neuron receives 800
   E connections on average, and in-cluster connections 1.9 times as strong. The weights are held as integers in units
   of 0.0001 (240, 456, -450, 140, -570), so that every synaptic sum is exact and a run repeats bit for bit anywhere.
2. The simulation: Euler steps of 0.1 ms, each step updating the filter variables, then the voltages of the neurons
   out of their refractory period, then emitting the spikes of those above threshold; 3 s from initial voltages uniform
   in [0, 1) and filters at 0. Each network (its connections and mu) and each trial's initial voltages are drawn from
   ECDYSIS_SEED (SHA-256 of the seed and a label, into numpy's default generator).
3. The statistic (Online Methods: Fano factors over 100 ms windows, across repeated trials of the same network from
   random initial conditions, for excitatory neurons, the spontaneous state from 1.5 s): for each E neuron and each of
   the 15 windows from 1.5 to 3 s, the variance of its spike count over the 9 trials (denominator 8) over its mean, where
   the mean is above 0; a neuron's Fano factor is the mean over those windows; the networks' Fano factor is the mean
   over all such neurons of the 12 networks of a kind (Fig. 2 used 12 networks of each kind and 9 trials of each).
4. The test's two conditions: the clustered networks' Fano factor above 1, and above the uniform networks' by at least
   0.31. test_passed is 1 if both hold.
5. Beside the test, against the paper's numbers: each Fano factor's s.d. across neurons (paper 0.7 clustered, 0.09
   uniform) and with denominator 9 instead of 8; Fano factors over 300 ms windows (Fig. 2g: rising with the window in
   clustered networks only); the E neurons' rates (paper 3.3 +- 4.1 and 2.0 +- 1.8 Hz); and the spike count
   correlation of pairs in the same cluster over 50 ms windows (paper 0.13 +- 0.18; for uniform networks, the same
   index blocks as a control).
6. Controls of the estimator, on counts drawn from the seed: Poisson counts at a fixed rate must give a Fano factor
   within 0.05 of 1, and counts whose rate switches between trials (doubly stochastic) one above 1.3.

What it cannot check: the authors' own code (not released with the paper), and details its text does not fix (the
order of updates within a step, how a mean of zero or the variance's denominator was handled), which rules 2 and 3 fix
here and rule 5 reports both ways where they matter.

Writes results/outputs.json and results/detail.json. Run with: python3 snn/clustered.py
"""

import hashlib
import json
import os
import re
import sys
import time
from multiprocessing import get_context

import numpy as np

NE, NI, C = 4000, 1000, 80
N = NE + NI
CLUSTERS = NE // C
R_EE, IN_FACTOR, K_EE = 2.5, 1.9, 800
UNIT = 1e-4                                  # weights as integers in units of 0.0001
J_EE, J_EI, J_IE, J_II = 240, -450, 140, -570
J_EE_IN = 456                                # 1.9 x 240
P_EE, P_X = 0.2, 0.5
TAU_E, TAU_I = 15.0, 10.0
MU_E, MU_I = (1.1, 1.2), (1.0, 1.05)
T1, T2E, T2I = 1.0, 3.0, 2.0
DT, REF, T_END = 0.1, 5.0, 3000.0
START, WINDOW, LONG_WINDOW, CORR_WINDOW = 1500.0, 100.0, 300.0, 50.0
NETWORKS, TRIALS = 12, 9
FF_ABOVE, GAP = 1.0, 0.31
KINDS = ("uniform", "clustered")
OUTPUTS = ("ff_clustered", "ff_uniform", "ff_gap", "ff_sd_clustered", "ff_sd_uniform", "ff_n9_clustered",
           "ff_n9_uniform", "ff300_clustered", "ff300_uniform", "rate_clustered", "rate_uniform", "corr_in_clustered",
           "corr_in_uniform", "neurons", "controls_passed", "controls_total", "conditions_met", "test_passed")


def rng_for(seed_hex, label):
    digest = hashlib.sha256(bytes.fromhex(seed_hex) + b"|" + b"clustered/" + label.encode("ascii")).digest()
    return np.random.default_rng(int.from_bytes(digest, "big"))


# ---------------------------------------------------------------- the network (rules 1 and 2)

def p_out_in(r=R_EE):
    p_out = K_EE / (C * (r - 1.0) + NE)
    return p_out, r * p_out


def network(rng, clustered):
    """(WT, mu): WT[j] is presynaptic neuron j's row of integer weights onto every neuron; mu each neuron's bias."""
    W = np.zeros((N, N), dtype=np.int16)                       # W[post, pre]
    if clustered:
        p_out, p_in = p_out_in()
        W[:NE, :NE] = J_EE * (rng.random((NE, NE)) < p_out)
        for c in range(CLUSTERS):
            s = slice(c * C, (c + 1) * C)
            W[s, s] = J_EE_IN * (rng.random((C, C)) < p_in)
    else:
        W[:NE, :NE] = J_EE * (rng.random((NE, NE)) < P_EE)
    W[:NE, NE:] = J_EI * (rng.random((NE, NI)) < P_X)
    W[NE:, :NE] = J_IE * (rng.random((NI, NE)) < P_X)
    W[NE:, NE:] = J_II * (rng.random((NI, NI)) < P_X)
    np.fill_diagonal(W, 0)
    mu = np.concatenate([rng.uniform(*MU_E, NE), rng.uniform(*MU_I, NI)])
    return np.ascontiguousarray(W.T), mu


def simulate(WT, mu, v0, t_end=T_END):
    """Spike times (ms) and neuron indices of one trial from initial voltages v0."""
    steps = int(round(t_end / DT))
    tau = np.concatenate([np.full(NE, TAU_E), np.full(NI, TAU_I)])
    dtau, a1, a2e, a2i = DT / tau, DT / T1, DT / T2E, DT / T2I
    de, di = 1.0 / (T2E - T1), 1.0 / (T2I - T1)
    v = v0.copy()
    xer, xed, xir, xid = (np.zeros(N) for _ in range(4))
    in_e, in_i = np.zeros(N), np.zeros(N)
    last = np.full(N, -1e9)
    times, cells = [], []
    for k in range(steps):
        t = k * DT
        xer += in_e - a1 * xer
        xed += in_e - a2e * xed
        xir += in_i - a1 * xir
        xid += in_i - a2i * xid
        syn = (xed - xer) * de + (xid - xir) * di
        free = t > last + REF
        v = np.where(free, v + dtau * (mu - v) + DT * syn, v)
        fired = np.flatnonzero(v > 1.0)
        if fired.size:
            v[fired] = 0.0
            last[fired] = t
            times.append(np.full(fired.size, t))
            cells.append(fired)
            e, i = fired[fired < NE], fired[fired >= NE]
            in_e = WT[e].sum(axis=0, dtype=np.int64) * UNIT if e.size else np.zeros(N)
            in_i = WT[i].sum(axis=0, dtype=np.int64) * UNIT if i.size else np.zeros(N)
        else:
            in_e, in_i = np.zeros(N), np.zeros(N)
    if not times:
        return np.zeros(0), np.zeros(0, dtype=np.int64)
    return np.concatenate(times), np.concatenate(cells)


# ---------------------------------------------------------------- the statistics (rules 3 and 5)

def counts(times, cells, window, start=START, end=T_END):
    """E neurons' spike counts in consecutive windows from start to end: (NE, windows)."""
    nb = int(round((end - start) / window))
    keep = (times >= start) & (times < end) & (cells < NE)
    b = np.minimum(((times[keep] - start) // window).astype(np.int64), nb - 1)
    out = np.zeros((NE, nb), dtype=np.int64)
    np.add.at(out, (cells[keep], b), 1)
    return out


def fano_per_neuron(stack, ddof=1):
    """stack: trials x neurons x windows of counts. Each neuron's mean over windows of var/mean across trials, where the
    mean is above 0; NaN for a neuron with no such window."""
    stack = stack.astype(np.float64)
    mean = stack.mean(axis=0)
    var = stack.var(axis=0, ddof=ddof)
    ff = np.full(mean.shape, np.nan)
    ok = mean > 0
    ff[ok] = var[ok] / mean[ok]
    defined = ok.sum(axis=1)
    out = np.full(stack.shape[1], np.nan)
    has = defined > 0
    out[has] = np.nansum(ff[has], axis=1) / defined[has]
    return out


def corr_in_blocks(stack):
    """Mean spike count correlation of pairs in the same block of C consecutive E neurons, over CORR_WINDOW windows within
    each trial, averaged across trials (pairs with a neuron silent in a trial skipped in that trial)."""
    sums = np.zeros(CLUSTERS)
    n = np.zeros(CLUSTERS)
    for tr in stack:                                            # neurons x windows
        for c in range(CLUSTERS):
            x = tr[c * C:(c + 1) * C].astype(np.float64)
            sd = x.std(axis=1)
            live = sd > 0
            if live.sum() < 2:
                continue
            r = np.corrcoef(x[live])
            iu = np.triu_indices(r.shape[0], 1)
            sums[c] += r[iu].sum()
            n[c] += iu[0].size
    return float(sums.sum() / n.sum()) if n.sum() else float("nan")


def one_network(task):
    """Everything rule 3 and 5 need from one network of a kind: run in a worker."""
    seed, kind, r = task
    rng = rng_for(seed, f"{kind}/{r}/network")
    WT, mu = network(rng, kind == "clustered")
    c100, c300, c50, rates = [], [], [], []
    for k in range(TRIALS):
        v0 = rng_for(seed, f"{kind}/{r}/trial/{k}").random(N)
        times, cells = simulate(WT, mu, v0)
        c100.append(counts(times, cells, WINDOW))
        c300.append(counts(times, cells, LONG_WINDOW))
        c50.append(counts(times, cells, CORR_WINDOW))
        rates.append(c100[-1].sum(axis=1) / ((T_END - START) / 1000.0))
    s100, s300 = np.stack(c100), np.stack(c300)
    return {"kind": kind, "r": r, "ff": fano_per_neuron(s100), "ff_n9": fano_per_neuron(s100, ddof=0),
            "ff300": fano_per_neuron(s300), "rate": np.mean(rates, axis=0), "corr_in": corr_in_blocks(np.stack(c50))}


# ---------------------------------------------------------------- controls (rule 6)

def controls(seed):
    rng = rng_for(seed, "controls")
    poisson = rng.poisson(0.5, size=(TRIALS, 2000, 15))
    lam = np.where(rng.random((TRIALS, 2000, 1)) < 0.5, 0.1, 1.5) * np.ones((1, 1, 15))
    switching = rng.poisson(lam)
    f_poisson = float(np.nanmean(fano_per_neuron(poisson)))
    f_switch = float(np.nanmean(fano_per_neuron(switching)))
    results = {"poisson": [f_poisson, abs(f_poisson - 1.0) <= 0.05], "switching": [f_switch, f_switch > 1.3]}
    return results


# ---------------------------------------------------------------- the run

def conditions(ff):
    return {"clustered networks' Fano factor above 1": ff["clustered"] > FF_ABOVE,
            "clustered above uniform by at least 0.31": ff["clustered"] - ff["uniform"] >= GAP}


def r4(x):
    return float(f"{x:.4f}")


def run(seed, results="results", workers=2, networks=NETWORKS, log=print):
    started = time.monotonic()
    tasks = [(seed, kind, r) for kind in KINDS for r in range(networks)]
    with get_context("fork").Pool(workers) as pool:
        parts = pool.map(one_network, tasks, chunksize=1)
    log(f"clustered: {len(parts)} networks in {round(time.monotonic() - started)} s")
    by = {kind: [p for p in parts if p["kind"] == kind] for kind in KINDS}
    cat = {kind: {key: np.concatenate([p[key] for p in by[kind]]) for key in ("ff", "ff_n9", "ff300", "rate")}
           for kind in KINDS}
    ff = {kind: float(np.nanmean(cat[kind]["ff"])) for kind in KINDS}
    cond = conditions(ff)
    ctl = controls(seed)
    out = {
        "ff_clustered": r4(ff["clustered"]), "ff_uniform": r4(ff["uniform"]),
        "ff_gap": r4(ff["clustered"] - ff["uniform"]),
        "ff_sd_clustered": r4(np.nanstd(cat["clustered"]["ff"])), "ff_sd_uniform": r4(np.nanstd(cat["uniform"]["ff"])),
        "ff_n9_clustered": r4(np.nanmean(cat["clustered"]["ff_n9"])),
        "ff_n9_uniform": r4(np.nanmean(cat["uniform"]["ff_n9"])),
        "ff300_clustered": r4(np.nanmean(cat["clustered"]["ff300"])),
        "ff300_uniform": r4(np.nanmean(cat["uniform"]["ff300"])),
        "rate_clustered": f"{np.mean(cat['clustered']['rate']):.2f} +- {np.std(cat['clustered']['rate']):.2f} Hz",
        "rate_uniform": f"{np.mean(cat['uniform']['rate']):.2f} +- {np.std(cat['uniform']['rate']):.2f} Hz",
        "corr_in_clustered": r4(np.mean([p["corr_in"] for p in by["clustered"]])),
        "corr_in_uniform": r4(np.mean([p["corr_in"] for p in by["uniform"]])),
        "neurons": f"{int(np.isfinite(cat['clustered']['ff']).sum())} clustered, "
                   f"{int(np.isfinite(cat['uniform']['ff']).sum())} uniform of {networks * NE} each",
        "controls_passed": sum(1 for v in ctl.values() if v[1]), "controls_total": len(ctl),
        "conditions_met": sum(cond.values()),
        "test_passed": int(all(cond.values()) and all(v[1] for v in ctl.values())),
    }
    detail = {"values": out, "conditions": cond, "controls": ctl,
              "per_network": [{"kind": p["kind"], "r": p["r"], "ff": r4(np.nanmean(p["ff"])),
                               "ff300": r4(np.nanmean(p["ff300"])), "rate": r4(np.mean(p["rate"])),
                               "corr_in": r4(p["corr_in"])} for p in parts],
              "p_out_in": p_out_in(), "seconds": round(time.monotonic() - started, 1)}
    os.makedirs(results, exist_ok=True)
    with open(os.path.join(results, "outputs.json"), "w", encoding="ascii") as f:
        json.dump(out, f, indent=2, sort_keys=True)
        f.write("\n")
    with open(os.path.join(results, "detail.json"), "w", encoding="ascii") as f:
        json.dump(detail, f, indent=1, sort_keys=True)
        f.write("\n")
    return out, detail


def main():
    seed = os.environ.get("ECDYSIS_SEED", "")
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        sys.exit("ECDYSIS_SEED must be the 64-hex seed the archive issued")
    out, _ = run(seed, log=lambda s: print(s, file=sys.stderr, flush=True))
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
