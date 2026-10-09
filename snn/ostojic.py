#!/usr/bin/env python3
"""Ostojic's network at weak and strong coupling, simulated afresh from the seed, for an Ecdysis receipt.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:83abea862f6cd7e8) is from Ostojic, "Two
types of asynchronous activity in networks of excitatory and inhibitory spiking neurons" (Nature Neuroscience 17(4),
2014): "For strong couplings, we find that the network at rest displays rich internal dynamics, in which the firing
rates of individual neurons fluctuate strongly in time and across neurons."

Its registered test: refuted if the paper's network (8,000 excitatory and 2,000 inhibitory LIF neurons, each
receiving 800 excitatory and 200 inhibitory inputs of J and -5J mV after 0.55 ms; constant input 24 mV, threshold
20 mV, reset 10 mV, tau 20 ms, 0.5 ms refractory), simulated exactly or in steps of at most 0.01 ms for 10 s after a
1 s transient, does not give at J = 0.8 mV a mean Fano factor of 100 ms spike counts above 2 and a time-averaged SD
across neurons of rates filtered by a Gaussian of s.d. 50 ms at least twice that at J = 0.2 mV, where the Fano factor
must be below 1.2.

The paper's text is closed to this laboratory. The network is the one every open source states: the reanalysis code of
Engelken, Farkhooi, Hansel, van Vreeswijk & Wolf (F1000Research 5:2043, 2016; Zenodo 59624), Mastrogiuseppe & Ostojic
(2017), Pena et al. (2018) and Ullner et al. (2020).

numpy only. Every rule below was fixed before any seed existed; the seed draws the network and the starting potentials.

1. The model. N_E = 8,000 excitatory and N_I = 2,000 inhibitory leaky integrate-and-fire neurons. Each receives exactly
   C_E = 800 excitatory and C_I = 200 inhibitory connections, drawn without replacement from the other neurons of each
   population (no neuron connects to itself), of efficacy J and -gJ with g = 5, each a jump of the membrane potential
   delivered D = 0.55 ms after the presynaptic spike. Between inputs the potential relaxes towards the constant
   external input mu_0 = 24 mV with tau = 20 ms, integrated exactly in steps of dt = 0.01 ms:
   V <- mu_0 + (V - mu_0) e^(-dt/tau) + the inputs arriving in the step. A neuron at or above theta = 20 mV fires, is
   reset to V_r = 10 mV and ignores all input for 50 steps (0.5 ms): input that arrives meanwhile is lost, as the
   paper's model has it. Potentials start uniform in [V_r, theta).
2. The runs. J = 0.2 mV and J = 0.8 mV (the ends of the paper's Figure 3), each simulated for 1 s of transient and
   10 s of analysis. One network serves both, drawn from numpy's PCG64 seeded by SHA-256(seed || "|" ||
   "ostojic/network"); each run's starting potentials from "ostojic/J0.2" or "ostojic/J0.8". The two runs go at once.
3. The measures, over the 10 s of analysis.
   - The Fano factor: each neuron's spike counts in the 100 consecutive windows of 100 ms, their variance (population
     form) over their mean; then the mean over the neurons that fired.
   - The spread: each neuron's spikes counted in 1 ms bins and convolved with a Gaussian of standard deviation 50 ms
     (truncated at 4 standard deviations, summing to one), times 1,000, for a rate in Hz at every millisecond from
     200 ms after the window opens to 200 ms before it closes, where the kernel sees only the window; at each such
     millisecond the standard deviation (population form) of the rates across all 10,000 neurons; then their mean.
   - Beside the test: the rate (spikes per neuron per second), the ISI CV (for every neuron with at least three
     intervals, the standard deviation of its intervals, population form, over their mean; then the mean), and the
     white-noise mean-field rate of the network (Brunel 2000 and Ricciardi's first-passage time, with the refractory
     period), as the reanalysis compares them.
4. The test's three conditions: at J = 0.8 mV a Fano factor above 2; a spread at J = 0.8 mV at least twice the spread
   at J = 0.2 mV; at J = 0.2 mV a Fano factor below 1.2. test_passed is 1 if all three hold and every control does.
5. Controls (controls_passed counts those that behave as stated), on synthetic spikes drawn from the seed
   ("ostojic/controls") and on the simulator itself:
   - 1,000 independent Poisson neurons at 20 Hz for 10 s: a Fano factor within 0.1 of 1, and a spread within 3% of
     the theory for independent Poisson trains, sqrt(rate / (2 sqrt(pi) sigma)) = 10.62 Hz;
   - 1,000 neurons each firing every 50 ms at its own phase: a Fano factor below 0.05;
   - the simulator at J = 0 (500 neurons for 1 s, the same code): every neuron fires regularly, every interval exactly
     2,556 steps (0.5 ms refractory and then 2,506 steps of 0.01 ms to climb from 10 to 20 mV towards 24 mV, the first
     step at or past tau ln(14/4) = 25.055 ms), so 39.12 Hz.

What it cannot check: the paper's own runs and figure values (the text is closed here); the computational claims of the
abstract's other sentences; whether there is a sharp transition between the two regimes, which the reanalysis disputes
and this test does not ask.

Writes results/outputs.json and results/detail.json. Run with: python3 snn/ostojic.py
"""

import hashlib
import json
import math
import os
import re
import sys
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np

NE, NI = 8_000, 2_000
CE, CI = 800, 200
G, MU0, TAU_MS, THETA, VR = 5.0, 24.0, 20.0, 20.0, 10.0
DT_MS, DELAY_MS, REF_MS = 0.01, 0.55, 0.5
TRANSIENT_S, ANALYSIS_S = 1.0, 10.0
COUPLINGS = {"J0.2": 0.2, "J0.8": 0.8}
WINDOW_MS, KERNEL_SD_MS, KERNEL_SDS = 100, 50, 4
FANO_STRONG, FANO_WEAK, SPREAD_RATIO = 2.0, 1.2, 2.0
WORKERS = 2


def steps_of(ms):
    return int(round(ms / DT_MS))


def rng_for(seed_hex, label):
    digest = hashlib.sha256(bytes.fromhex(seed_hex) + b"|" + b"ostojic/" + label.encode("ascii")).digest()
    return np.random.default_rng(int.from_bytes(digest, "big"))


def presynaptic(rng, n_pre, k, post, offset, same):
    """k distinct presynaptic indices (offset + 0 .. n_pre - 1) for neuron post, excluding post itself when it belongs to
    the same population."""
    if same:
        own = post - offset
        draw = rng.choice(n_pre - 1, k, replace=False)
        draw = draw + (draw >= own)
    else:
        draw = rng.choice(n_pre, k, replace=False)
    return draw + offset


def network(rng, ne=NE, ni=NI, ce=CE, ci=CI):
    """(targets, excit, starts): for each presynaptic neuron j its postsynaptic targets targets[starts[j]:starts[j+1]],
    and whether each connection is excitatory."""
    n = ne + ni
    pre = np.empty((n, ce + ci), dtype=np.int32)
    for i in range(n):
        pre[i, :ce] = presynaptic(rng, ne, ce, i, 0, i < ne)
        pre[i, ce:] = presynaptic(rng, ni, ci, i, ne, i >= ne)
    flat = pre.ravel()
    post = np.repeat(np.arange(n, dtype=np.int32), ce + ci)
    order = np.argsort(flat, kind="stable")
    targets = post[order]
    excit = flat[order] < ne
    starts = np.searchsorted(flat[order], np.arange(n + 1))
    return targets, excit, starts


def simulate(net, j_mv, v0, total_steps, first_step):
    """Rule 1 for total_steps steps from the potentials v0. Returns the spike steps (from first_step, counted from it) and
    neurons, in the order they fired."""
    targets, excit, starts = net
    n = v0.size
    weights = np.where(excit, j_mv, -G * j_mv)
    delay, refractory = steps_of(DELAY_MS), steps_of(REF_MS)
    ring = np.zeros((delay + 1, n))
    v = v0.astype(float).copy()
    ref = np.zeros(n, dtype=np.int32)
    decay = math.exp(-DT_MS / TAU_MS)
    sp_t, sp_i = [], []
    for k in range(total_steps):
        slot = k % (delay + 1)
        active = ref == 0
        v = np.where(active, MU0 + (v - MU0) * decay + ring[slot], v)
        np.maximum(ref - 1, 0, out=ref)
        ring[slot] = 0.0
        fired = np.flatnonzero(v >= THETA)
        if fired.size:
            v[fired] = VR
            ref[fired] = refractory
            if j_mv != 0.0:
                idx = np.concatenate([np.arange(starts[f], starts[f + 1]) for f in fired])
                ring[(k + delay) % (delay + 1)] += np.bincount(targets[idx], weights=weights[idx], minlength=n)
            if k >= first_step:
                sp_t.append(np.full(fired.size, k - first_step, dtype=np.int64))
                sp_i.append(fired.astype(np.int64))
    st = np.concatenate(sp_t) if sp_t else np.zeros(0, np.int64)
    si = np.concatenate(sp_i) if sp_i else np.zeros(0, np.int64)
    return st, si


def fano(st, si, n, steps):
    """Rule 3: the mean over neurons that fired of var/mean of their counts in consecutive 100 ms windows."""
    per = steps_of(WINDOW_MS)
    windows = steps // per
    keep = st < windows * per
    counts = np.zeros((n, windows))
    np.add.at(counts, (si[keep], st[keep] // per), 1.0)
    mean = counts.mean(axis=1)
    fired = mean > 0
    var = counts[fired].var(axis=1)
    return float((var / mean[fired]).mean()), int(fired.sum())


def spread(st, si, n, steps, chunk=1000):
    """Rule 3: the time-averaged standard deviation across neurons of rates filtered by a Gaussian of s.d. 50 ms."""
    per_ms = steps_of(1.0)
    bins = steps // per_ms
    half = KERNEL_SDS * KERNEL_SD_MS
    m = np.arange(-half, half + 1)
    kernel = np.exp(-0.5 * (m / KERNEL_SD_MS) ** 2)
    kernel /= kernel.sum()
    size = bins + kernel.size - 1
    fk = np.fft.rfft(kernel, n=size)
    s1 = np.zeros(bins - 2 * half)
    s2 = np.zeros(bins - 2 * half)
    b = st // per_ms
    order = np.argsort(si, kind="stable")
    si_o, b_o = si[order], b[order]
    bounds = np.searchsorted(si_o, np.arange(0, n + chunk, chunk))
    for c in range(0, n, chunk):
        lo, hi = bounds[c // chunk], bounds[min(c // chunk + 1, bounds.size - 1)]
        rows = min(chunk, n - c)
        counts = np.zeros((rows, bins))
        np.add.at(counts, (si_o[lo:hi] - c, np.minimum(b_o[lo:hi], bins - 1)), 1.0)
        full = np.fft.irfft(np.fft.rfft(counts, n=size, axis=1) * fk, n=size, axis=1)
        # full[:, t + half] is the kernel centred on bin t; keep the centres the window's spikes alone determine.
        rates = full[:, 2 * half:bins] * 1000.0
        s1 += rates.sum(axis=0)
        s2 += (rates * rates).sum(axis=0)
    mean = s1 / n
    var = np.maximum(s2 / n - mean * mean, 0.0)
    return float(np.sqrt(var).mean())


def cv_of(st, si):
    """(mean ISI CV over neurons with at least three intervals, how many such neurons)."""
    order = np.lexsort((st, si))
    st, si = st[order], si[order]
    same = si[1:] == si[:-1]
    isi = (st[1:] - st[:-1])[same].astype(float)
    owner = si[1:][same]
    if owner.size == 0:
        return float("nan"), 0
    counts = np.bincount(owner)
    sums = np.bincount(owner, weights=isi)
    sq = np.bincount(owner, weights=isi * isi)
    keep = counts >= 3
    mean = sums[keep] / counts[keep]
    var = np.maximum(sq[keep] / counts[keep] - mean * mean, 0.0)
    cvs = np.sqrt(var) / mean
    return float(cvs.mean()) if cvs.size else float("nan"), int(cvs.size)


def mean_field_rate(j_mv):
    """The white-noise mean-field rate (Hz) of the network: nu = 1 / (tau_ref + tau sqrt(pi) integral from
    (V_r - mu)/sigma to (theta - mu)/sigma of e^(u^2) (1 + erf u) du), with mu = mu_0 + tau nu J (C_E - g C_I) and
    sigma^2 = tau nu J^2 (C_E + g^2 C_I), solved for nu by bisection; Simpson's rule on 4,000 intervals."""
    tau, tref = TAU_MS * 1e-3, REF_MS * 1e-3

    def integral(a, b, n=4000):
        h = (b - a) / n
        def f(u):  # e^(u^2) (1 + erf u), with its asymptotic form far below zero, where e^(u^2) would overflow
            if u < -25.0:
                return (1.0 - 1.0 / (2 * u * u)) / (-u * math.sqrt(math.pi))
            return math.exp(u * u) * math.erfc(-u)
        s = f(a) + f(b) + sum((4 if i % 2 else 2) * f(a + i * h) for i in range(1, n))
        return s * h / 3

    def transfer(nu):
        mu = MU0 + tau * nu * j_mv * (CE - G * CI)
        sigma = math.sqrt(tau * nu * j_mv * j_mv * (CE + G * G * CI))
        return 1.0 / (tref + tau * math.sqrt(math.pi) * integral((VR - mu) / sigma, (THETA - mu) / sigma))

    lo, hi = 0.1, 1.0 / tref - 1.0
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if transfer(mid) > mid:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def measures(st, si, n, steps):
    f, fired = fano(st, si, n, steps)
    cv, used = cv_of(st, si)
    return {"rate": st.size / (n * steps * DT_MS * 1e-3), "fano": f, "fano_neurons": fired, "spread": spread(st, si, n, steps),
            "cv": cv, "cv_neurons": used}


def conditions(m):
    """The test's three conditions (rule 4), by name."""
    return {
        "J = 0.8 mV: Fano factor above 2": m["J0.8"]["fano"] > FANO_STRONG,
        "spread at 0.8 mV at least twice that at 0.2 mV": m["J0.8"]["spread"] >= SPREAD_RATIO * m["J0.2"]["spread"],
        "J = 0.2 mV: Fano factor below 1.2": m["J0.2"]["fano"] < FANO_WEAK,
    }


def controls(seed_hex):
    """Rule 5."""
    rng = rng_for(seed_hex, "controls")
    n, steps = 1000, steps_of(ANALYSIS_S * 1e3)
    per_ms = steps_of(1.0)
    # Poisson neurons at 20 Hz, drawn per millisecond and placed at a uniform step within it.
    ms = steps // per_ms
    hits = rng.random((ms, n)) < 20.0 * 1e-3
    pt_ms, pi = np.nonzero(hits)
    pt = pt_ms * per_ms + rng.integers(0, per_ms, pt_ms.size)
    poisson_fano, _ = fano(pt, pi, n, steps)
    poisson_spread = spread(pt, pi, n, steps)
    theory = math.sqrt(20.0 / (2 * math.sqrt(math.pi) * KERNEL_SD_MS * 1e-3))
    period = steps_of(50.0)
    phase = rng.integers(0, period, n)
    beats = np.arange(0, steps, period)
    rt = (beats[:, None] + phase[None, :]).ravel()
    ri = np.tile(np.arange(n), beats.size)
    keep = rt < steps
    regular_fano, _ = fano(rt[keep], ri[keep], n, steps)
    # The simulator at J = 0: 500 neurons (any connectivity; none is used) for 1 s.
    small = 500
    net = (np.zeros(0, np.int32), np.zeros(0, bool), np.zeros(small + 1, np.int64))
    v0 = rng.uniform(VR, THETA, small)
    zt, zi = simulate(net, 0.0, v0, steps_of(1000.0), 0)
    order = np.lexsort((zt, zi))
    zt, zi = zt[order], zi[order]
    same = zi[1:] == zi[:-1]
    intervals = np.unique((zt[1:] - zt[:-1])[same])
    return [
        {"control": "Poisson neurons at 20 Hz: Fano factor within 0.1 of 1", "passed": abs(poisson_fano - 1) < 0.1,
         "value": poisson_fano},
        {"control": "Poisson neurons at 20 Hz: spread within 3% of sqrt(rate / (2 sqrt(pi) sigma)) = 10.62 Hz",
         "passed": abs(poisson_spread / theory - 1) < 0.03, "value": poisson_spread},
        {"control": "neurons each firing every 50 ms at its own phase: Fano factor below 0.05",
         "passed": regular_fano < 0.05, "value": regular_fano},
        {"control": "the simulator at J = 0: every interval exactly 2,556 steps (39.12 Hz)",
         "passed": intervals.tolist() == [2556], "value": intervals.tolist()},
    ]


def one(args):
    seed_hex, label = args
    t = time.monotonic()
    net = network(rng_for(seed_hex, "network"))
    v0 = rng_for(seed_hex, label).uniform(VR, THETA, NE + NI)
    first = steps_of(TRANSIENT_S * 1e3)
    total = first + steps_of(ANALYSIS_S * 1e3)
    st, si = simulate(net, COUPLINGS[label], v0, total, first)
    m = measures(st, si, NE + NI, total - first)
    m["mean_field_rate"] = mean_field_rate(COUPLINGS[label])
    m["seconds"] = round(time.monotonic() - t, 1)
    return label, m


def run(seed_hex, results="results", log=print):
    with ProcessPoolExecutor(WORKERS) as pool:
        found = dict(pool.map(one, [(seed_hex, label) for label in COUPLINGS]))
    for label in COUPLINGS:
        m = found[label]
        log(f"ostojic: {label}: rate {m['rate']:.2f} Hz (mean field {m['mean_field_rate']:.2f}), Fano {m['fano']:.3f} over "
            f"{m['fano_neurons']} neurons, spread {m['spread']:.3f} Hz, ISI CV {m['cv']:.3f}, {m['seconds']} s")
    cond = conditions(found)
    rows = controls(seed_hex)
    r = lambda x, d: float(round(x, d))  # noqa: E731
    ok_controls = sum(1 for x in rows if x["passed"])
    out = {
        "fano_02": r(found["J0.2"]["fano"], 4), "fano_08": r(found["J0.8"]["fano"], 4),
        "spread_02": r(found["J0.2"]["spread"], 4), "spread_08": r(found["J0.8"]["spread"], 4),
        "spread_ratio": r(found["J0.8"]["spread"] / found["J0.2"]["spread"], 4),
        "rate_02": r(found["J0.2"]["rate"], 3), "rate_08": r(found["J0.8"]["rate"], 3),
        "cv_02": r(found["J0.2"]["cv"], 4), "cv_08": r(found["J0.8"]["cv"], 4),
        "mean_field_02": r(found["J0.2"]["mean_field_rate"], 3), "mean_field_08": r(found["J0.8"]["mean_field_rate"], 3),
        "conditions_met": sum(cond.values()), "conditions_total": len(cond),
        "controls_passed": ok_controls, "controls_total": len(rows),
        "test_passed": int(all(cond.values()) and ok_controls == len(rows)),
    }
    detail = {"couplings": {k: dict(v, j_mv=COUPLINGS[k]) for k, v in found.items()}, "conditions": cond, "controls": rows,
              "rules": {"dt_ms": DT_MS, "delay_ms": DELAY_MS, "refractory_ms": REF_MS, "transient_s": TRANSIENT_S,
                        "analysis_s": ANALYSIS_S, "window_ms": WINDOW_MS, "kernel_sd_ms": KERNEL_SD_MS}}
    os.makedirs(results, exist_ok=True)
    with open(os.path.join(results, "outputs.json"), "w", encoding="ascii") as f:
        json.dump(out, f, indent=2, sort_keys=True)
        f.write("\n")
    with open(os.path.join(results, "detail.json"), "w", encoding="ascii") as f:
        json.dump(detail, f, indent=1, sort_keys=True, default=float)
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
