#!/usr/bin/env python3
"""Brunel's model A at the four points of his Figure 8, simulated afresh from the seed, for an Ecdysis receipt.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:e36ea87957330dd0) is from Brunel, "Dynamics
of Sparsely Connected Networks of Excitatory and Inhibitory Spiking Neurons" (Journal of Computational Neuroscience
8(3), 2000): "The analysis reveals a rich repertoire of states, including synchronous states in which neurons fire
regularly; asynchronous states with stationary global activity and very irregular individual cell activity; and states
in which the global activity oscillates but individual cells fire irregularly, typically at rates lower than the global
oscillation frequency. The network can switch between these states, provided the external frequency, or the balance
between excitation and inhibition, is varied."

Its registered test: refuted if the paper's model A (N_E = 10,000, N_I = 2,500, connection probability 0.1,
J = 0.1 mV, D = 1.5 ms, tau = 20 ms, theta = 20 mV, V_r = 10 mV, 2 ms refractory, Poisson external input) simulated at
its Figure 8 points does not give: at g = 3, nu_ext/nu_thr = 2, regular firing (ISI CV < 0.1); at (6, 4), (5, 2) and
(4.5, 0.9), irregular firing (CV > 0.3) at rates, and for (6, 4) and (4.5, 0.9) global frequencies, within 25% of the
span of Table 1's simulation and theory values; and at (5, 2) a population spectral peak under a tenth of (6, 4)'s.

numpy only. Every rule below was fixed before any seed existed; the seed draws each network and its inputs.

1. The model, as the paper's section 2 defines model A. Each neuron receives exactly C_E = 1,000 excitatory and
   C_I = 250 inhibitory connections, drawn without replacement from the other neurons of each population (no neuron
   connects to itself), of efficacy J = 0.1 mV and -gJ, delivered after D = 1.5 ms; and C_ext = C_E external
   excitatory synapses of efficacy J, each an independent Poisson process at nu_ext = eta nu_thr, with
   nu_thr = theta / (J C_E tau) = 10 Hz. The membrane potential decays exactly between steps of dt = 0.1 ms
   (V <- V e^(-dt/tau) + the inputs arriving in the step); a neuron at or above theta = 20 mV fires, is reset to
   V_r = 10 mV and ignores all input for 20 steps (2 ms). Potentials start uniform in [0, theta).
2. The runs. The four points of Figure 8, (g, eta) = A (3, 2), B (6, 4), C (5, 2), D (4.5, 0.9), each simulated for
   0.2 s of transient and 2.0 s of analysis, every random draw from numpy's PCG64 seeded by SHA-256(seed || "|" ||
   "brunel/" || the point's letter). Two points run at a time.
3. The measures, over the 2.0 s of analysis. The rate: spikes per neuron per second. The ISI CV: for every neuron with
   at least three interspike intervals, the standard deviation of its intervals (population form) over their mean;
   then the mean over those neurons. The global activity: the spikes in each 0.1 ms step over N dt (Hz), whose power
   spectrum is taken by Welch's method (segments of 0.25 s, a Hann window, half overlapping, each segment's mean
   removed, density scaling); the global frequency is the frequency of its largest power at 5 Hz or above, and the
   peak power that power.
4. The test's ten conditions. A: CV < 0.1. B, C and D: CV > 0.3. Rates within 25% of the span of Table 1's simulation
   and theory values, 0.75 times the smaller to 1.25 times the larger: B in [41.85, 75.875] Hz (60.7 and 55.8),
   C in [28.275, 47.5] Hz (37.7 and 38.0), D in [4.125, 8.125] Hz (5.5 and 6.5). Global frequencies the same way:
   B in [135, 237.5] Hz (180 and 190), D in [16.5, 36.25] Hz (22 and 29). C's peak power under a tenth of B's.
   test_passed is 1 if all ten hold; else 0.
5. Controls of the measures, on 2 s of synthetic spikes from 1,000 neurons drawn from the seed (controls_passed
   counts those that behave as stated): independent Poisson neurons at 30 Hz must give a CV within 0.1 of 1;
   neurons each firing every 10 ms at its own phase, a CV under 0.01; neurons firing together every 10 ms with a
   1 ms (standard deviation) jitter, a global frequency within 4 Hz of 100 Hz; and the Poisson neurons, a peak power
   under a tenth of the synchronous neurons'.

What it cannot check: the paper's own runs (their seeds and durations are not given; Figure 8 shows 50 ms windows);
the theory's predictions themselves, which Table 1 gives and the test uses only as the span; other points of the
phase diagram.

Writes results/outputs.json and results/detail.json. Run with: python3 snn/brunel.py
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

NE, NI = 10_000, 2_500
CE, CI = 1_000, 250
J, DELAY_MS, TAU_MS, THETA, VR, REF_STEPS = 0.1, 1.5, 20.0, 20.0, 10.0, 20
DT_MS = 0.1
TRANSIENT_S, ANALYSIS_S = 0.2, 2.0
POINTS = {"A": (3.0, 2.0), "B": (6.0, 4.0), "C": (5.0, 2.0), "D": (4.5, 0.9)}
SEGMENT_S, FMIN = 0.25, 5.0
RATE_SPAN = {"B": (60.7, 55.8), "C": (37.7, 38.0), "D": (5.5, 6.5)}
FREQ_SPAN = {"B": (180.0, 190.0), "D": (22.0, 29.0)}
MARGIN = 0.25
REGULAR, IRREGULAR, PEAK_FRACTION = 0.1, 0.3, 0.1
WORKERS = 2


def nu_thr():
    """theta / (J C_E tau), in Hz."""
    return THETA / (J * CE * TAU_MS * 1e-3)


def rng_for(seed_hex, label):
    digest = hashlib.sha256(bytes.fromhex(seed_hex) + b"|" + b"brunel/" + label.encode("ascii")).digest()
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


def network(rng):
    """(targets, weights per J, starts): for each presynaptic neuron j, its postsynaptic targets
    targets[starts[j]:starts[j+1]] and signed unit weights (+1 excitatory, -1 inhibitory, times g later)."""
    n = NE + NI
    pre = np.empty((n, CE + CI), dtype=np.int32)
    for i in range(n):
        pre[i, :CE] = presynaptic(rng, NE, CE, i, 0, i < NE)
        pre[i, CE:] = presynaptic(rng, NI, CI, i, NE, i >= NE)
    flat = pre.ravel()
    post = np.repeat(np.arange(n, dtype=np.int32), CE + CI)
    order = np.argsort(flat, kind="stable")
    targets = post[order]
    excit = flat[order] < NE
    starts = np.searchsorted(flat[order], np.arange(n + 1))
    return targets, excit, starts


def simulate(seed_hex, label):
    """One point: (spike step and neuron arrays within the analysis window, the population counts per step)."""
    g, eta = POINTS[label]
    rng = rng_for(seed_hex, label)
    n = NE + NI
    targets, excit, starts = network(rng)
    weights = np.where(excit, J, -g * J)
    delay = int(round(DELAY_MS / DT_MS))
    ring = np.zeros((delay + 1, n))
    v = rng.uniform(0.0, THETA, n)
    ref = np.zeros(n, dtype=np.int32)
    decay = math.exp(-DT_MS / TAU_MS)
    lam = CE * eta * nu_thr() * DT_MS * 1e-3
    first = int(round(TRANSIENT_S * 1e3 / DT_MS))
    steps = first + int(round(ANALYSIS_S * 1e3 / DT_MS))
    pop = np.zeros(steps - first, dtype=np.int64)
    sp_t, sp_i = [], []
    for k in range(steps):
        slot = k % (delay + 1)
        ext = rng.poisson(lam, n) * J
        active = ref == 0
        v = np.where(active, v * decay + ring[slot] + ext, v)
        np.maximum(ref - 1, 0, out=ref)
        ring[slot] = 0.0
        fired = np.flatnonzero(v >= THETA)
        if fired.size:
            v[fired] = VR
            ref[fired] = REF_STEPS
            idx = np.concatenate([np.arange(starts[f], starts[f + 1]) for f in fired])
            ring[(k + delay) % (delay + 1)] += np.bincount(targets[idx], weights=weights[idx], minlength=n)
            if k >= first:
                pop[k - first] = fired.size
                sp_t.append(np.full(fired.size, k - first, dtype=np.int64))
                sp_i.append(fired.astype(np.int64))
    st = np.concatenate(sp_t) if sp_t else np.zeros(0, np.int64)
    si = np.concatenate(sp_i) if sp_i else np.zeros(0, np.int64)
    return st, si, pop


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


def welch(pop, n):
    """(frequencies, power density) of the global activity pop / (n dt), by Welch's method (rule 3)."""
    fs = 1e3 / DT_MS
    x = pop / (n * DT_MS * 1e-3)
    seg = int(round(SEGMENT_S * fs))
    step = seg // 2
    w = np.hanning(seg)
    scale = 1.0 / (fs * np.sum(w * w))
    acc, count = np.zeros(seg // 2 + 1), 0
    for start in range(0, x.size - seg + 1, step):
        part = x[start:start + seg]
        spec = np.fft.rfft(w * (part - part.mean()))
        acc += scale * np.abs(spec) ** 2
        count += 1
    psd = acc / count
    psd[1:-1] *= 2
    return np.fft.rfftfreq(seg, 1.0 / fs), psd


def peak(freqs, psd):
    band = freqs >= FMIN
    k = int(np.argmax(psd[band]))
    return float(freqs[band][k]), float(psd[band][k])


def measures(st, si, pop, n, seconds):
    rate = st.size / (n * seconds)
    cv, used = cv_of(st, si)
    f, p = peak(*welch(pop, n))
    return {"rate": rate, "cv": cv, "cv_neurons": used, "frequency": f, "peak_power": p}


def within(value, span):
    lo, hi = min(span), max(span)
    return (1 - MARGIN) * lo <= value <= (1 + MARGIN) * hi


def conditions(m):
    """The test's ten conditions (rule 4), by name."""
    return {
        "A regular": m["A"]["cv"] < REGULAR,
        "B irregular": m["B"]["cv"] > IRREGULAR,
        "C irregular": m["C"]["cv"] > IRREGULAR,
        "D irregular": m["D"]["cv"] > IRREGULAR,
        "B rate": within(m["B"]["rate"], RATE_SPAN["B"]),
        "C rate": within(m["C"]["rate"], RATE_SPAN["C"]),
        "D rate": within(m["D"]["rate"], RATE_SPAN["D"]),
        "B frequency": within(m["B"]["frequency"], FREQ_SPAN["B"]),
        "D frequency": within(m["D"]["frequency"], FREQ_SPAN["D"]),
        "C peak under a tenth of B's": m["C"]["peak_power"] < PEAK_FRACTION * m["B"]["peak_power"],
    }


def controls(seed_hex):
    """Rule 5: the measures on 1,000 independent Poisson neurons at 30 Hz, on 1,000 neurons firing every 10 ms each at
    its own phase, and on 1,000 neurons firing together every 10 ms with a jitter of 1 ms (standard deviation)."""
    rng = rng_for(seed_hex, "controls")
    n, steps = 1000, int(round(ANALYSIS_S * 1e3 / DT_MS))
    period = int(round(10.0 / DT_MS))

    def counts(st):
        return np.bincount(st, minlength=steps)

    spikes = rng.random((steps, n)) < 30.0 * DT_MS * 1e-3
    pt, pi = np.nonzero(spikes)
    poisson = measures(pt, pi, counts(pt), n, ANALYSIS_S)
    phase = rng.integers(0, period, n)
    beats = np.arange(0, steps, period)
    rt = (beats[:, None] + phase[None, :]).ravel()
    ri = np.tile(np.arange(n), beats.size)
    keep = rt < steps
    regular = measures(rt[keep], ri[keep], counts(rt[keep]), n, ANALYSIS_S)
    jt = (beats[:, None] + np.rint(rng.normal(0.0, 1.0 / DT_MS, (beats.size, n)))).astype(np.int64).ravel()
    ji = np.tile(np.arange(n), beats.size)
    keep = (jt >= 0) & (jt < steps)
    jittered = measures(jt[keep], ji[keep], counts(jt[keep]), n, ANALYSIS_S)
    return [
        {"control": "Poisson neurons at 30 Hz: CV within 0.1 of 1", "passed": abs(poisson["cv"] - 1) < 0.1,
         "value": poisson["cv"]},
        {"control": "neurons each firing every 10 ms at its own phase: CV under 0.01", "passed": regular["cv"] < 0.01,
         "value": regular["cv"]},
        {"control": "neurons firing together every 10 ms, 1 ms jitter: global frequency within 4 Hz of 100 Hz",
         "passed": abs(jittered["frequency"] - 100.0) <= 4.0, "value": jittered["frequency"]},
        {"control": "the Poisson neurons' peak power under a tenth of the synchronous neurons'",
         "passed": poisson["peak_power"] < PEAK_FRACTION * jittered["peak_power"],
         "value": poisson["peak_power"] / jittered["peak_power"]},
    ]


def one(args):
    seed_hex, label = args
    t = time.monotonic()
    st, si, pop = simulate(seed_hex, label)
    m = measures(st, si, pop, NE + NI, ANALYSIS_S)
    m["seconds"] = round(time.monotonic() - t, 1)
    return label, m


def run(seed_hex, results="results", labels=tuple(POINTS), log=print):
    with ProcessPoolExecutor(WORKERS) as pool:
        found = dict(pool.map(one, [(seed_hex, label) for label in labels]))
    for label in labels:
        m = found[label]
        log(f"brunel: {label} {POINTS[label]}: rate {m['rate']:.2f} Hz, CV {m['cv']:.3f} over {m['cv_neurons']} neurons, "
            f"peak {m['frequency']:.0f} Hz (power {m['peak_power']:.4g}), {m['seconds']} s")
    cond = conditions(found)
    rows = controls(seed_hex)
    r = lambda x, d: float(round(x, d))  # noqa: E731
    out = {
        "cv_a": r(found["A"]["cv"], 4), "cv_b": r(found["B"]["cv"], 4), "cv_c": r(found["C"]["cv"], 4),
        "cv_d": r(found["D"]["cv"], 4),
        "rate_a": r(found["A"]["rate"], 2), "rate_b": r(found["B"]["rate"], 2), "rate_c": r(found["C"]["rate"], 2),
        "rate_d": r(found["D"]["rate"], 2),
        "freq_b": r(found["B"]["frequency"], 1), "freq_d": r(found["D"]["frequency"], 1),
        "peak_ratio_c_b": r(found["C"]["peak_power"] / found["B"]["peak_power"], 5),
        "conditions_met": sum(cond.values()), "conditions_total": len(cond),
        "controls_passed": sum(1 for x in rows if x["passed"]), "controls_total": len(rows),
        "test_passed": int(all(cond.values())),
    }
    detail = {"points": {k: dict(v, g=POINTS[k][0], eta=POINTS[k][1]) for k, v in found.items()},
              "conditions": cond, "controls": rows,
              "rules": {"dt_ms": DT_MS, "transient_s": TRANSIENT_S, "analysis_s": ANALYSIS_S, "segment_s": SEGMENT_S,
                        "fmin": FMIN, "margin": MARGIN}}
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
