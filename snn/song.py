#!/usr/bin/env python3
"""Song, Miller & Abbott (2000): STDP balances a neuron's excitation, making its firing irregular and more sensitive to
presynaptic spike timing.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:4c6c4e22f5e782dd) is from Song, Miller and
Abbott, "Competitive Hebbian learning through spike-timing-dependent synaptic plasticity" (Nature Neuroscience 3(9),
919-926, 2000; pmid:10966623): "In modeling studies, we find that this form of synaptic modification can automatically
balance synaptic strengths to make postsynaptic firing irregular but more sensitive to presynaptic spike timing."

Its registered test: refuted if, in the paper's model (Methods: an integrate-and-fire neuron, 1000 excitatory synapses
under additive STDP with A-/A+ = 1.05 and gmax = 0.015, all starting at gmax, 200 fixed inhibitory ones at 10 Hz), over
200 s after 1000 s of independent Poisson input at 10, 20, 30 and 40 Hz: the inhibitory-to-excitatory current ratio at
threshold is outside 1.0-1.3, or the output CV is below 0.7, at any rate; or the output rate rises by 12 Hz or more
from 10 to 40 Hz; or, at 10 Hz, the excess of presynaptic spikes in the 20 ms before a postsynaptic spike is under twice
that at the start.

Standard library and the image's gcc: the neuron is simulated in C (snn/song.c, compiled here). No data are read: the
inputs are generated under the seed. Every rule below was fixed before any run of the model.

1. The model, as the paper's Methods give it (read from the authors' copy of the paper): tau_m dV/dt = V_rest - V +
   g_ex (E_ex - V) + g_in (E_in - V), tau_m = 20 ms, V_rest = -70 mV, E_ex = 0, E_in = -70 mV; a spike at -54 mV, reset
   to -60 mV; conductances in units of the leak, each presynaptic spike adding its synapse's peak conductance, both
   decaying with 5 ms; 200 inhibitory synapses of peak 0.05, Poisson at 10 Hz, fixed; 1000 excitatory synapses, Poisson
   at the input rate, their peaks between 0 and gmax = 0.015 and all at gmax at the start (Results). STDP as the Methods
   implement it: a trace M decaying with tau- = 20 ms and lowered by A- at each postsynaptic spike, a trace P_a for
   each synapse decaying with tau+ = 20 ms and raised by A+ = 0.005 at each of its presynaptic spikes; a presynaptic
   spike changes its peak by M gmax (clipped at 0) after adding it to g_ex, a postsynaptic spike every peak by P_a gmax
   (clipped at gmax); A- = 1.05 A+.
2. The numerics, which the paper does not give: steps of 0.1 ms; in each, the inhibitory and the excitatory arrivals
   (a Poisson count for each population, each excitatory spike given to a synapse drawn uniformly, which is the
   superposition of independent Poisson trains), then the membrane by exponential Euler with the step's conductances,
   then the spike if V >= -54 mV, then one step of decay; no refractory period (none is given). The generator is
   xoshiro256**, seeded from SHA-256 of the seed and the run's label.
3. Runs: at each input rate of 10, 20, 30 and 40 Hz, 1000 s from all peaks at gmax and then 200 s of measurement, STDP
   on throughout (the Methods: "all presented data were collected only after 1000 seconds of simulated time"). The
   start: 20 s at 10 Hz with every peak held at gmax, measured from the first step.
4. What is measured: the output rate; the CV of the interspike intervals; the time-averaged conductances, from which
   the ratio of inhibitory to excitatory current at threshold, the leak counted as inhibitory (Figure 2d's legend):
   (V_th - V_rest + <g_in> (V_th - E_in)) / (<g_ex> (E_ex - V_th)) = 16 (1 + <g_in>) / (54 <g_ex>); and the correlogram
   of excitatory presynaptic spikes around each postsynaptic spike, 1 ms bins from -50 to +50 ms, divided by its value
   by chance (postsynaptic spikes times the presynaptic spikes per ms), so that 1 means chance (Figure 3). A
   presynaptic spike in the step of the postsynaptic one arrived before it and counts as before. The excess before is
   the mean, over the 20 bins before the spike, of the correlation less 1.
5. The test's ten conditions: at each rate, the ratio within 1.0 to 1.3 (four) and the CV at least 0.7 (four); the
   output rate at 40 Hz less than 12 Hz above that at 10 Hz; and the excess before at 10 Hz, after 1000 s, at least
   twice the start's. test_passed is 1 if all ten hold.
6. Beside the test, none of it counted: the output rates and CVs against Figure 2c (about 9 to 15 Hz, CV about 0.9);
   the ratios against Figure 2d (about 1.15); the share of strong synapses (peak at least 0.8 gmax) at each rate,
   against the text's "roughly half" at 10 Hz and 10% at 40 Hz; the shares in the bottom and top twentieths of
   [0, gmax] at 10 and 40 Hz against Figure 2a and 2b; the rise in output rate when the inputs go from 10 to 15 Hz with
   the peaks held at their 10 Hz equilibrium (50 s each), against the text's "over 100 Hz"; the start's rate and CV;
   and the output rate in 10 s windows of the 10 Hz run (detail only), against the Methods' convergence in about
   100 s.

Controls (controls_passed counts those that behave as stated; the run stops if any fails): the C program matches a
plain implementation written here, bit for bit, over 0.5 s at 10 Hz from all peaks at gmax with STDP on (spikes,
conductances, correlogram, intervals and every final peak); one pre and one post spike 10 ms apart change a synapse by
A+ e^(-1/2) gmax and -A- e^(-1/2) gmax within 1e-12; in the start run, the excitatory and inhibitory arrivals are
within four standard errors of 200,000 and 40,000, and the mean conductances within 2% of 1000 x 10 Hz x 5 ms x gmax
= 0.75 and 200 x 10 Hz x 5 ms x 0.05 = 0.5; and the correlogram's 50 bins after the spike, where independent Poisson
inputs cannot depend on it, average 1 within 0.02 in the start run and in the 10 Hz run.

What it cannot check: the paper's own simulations, which were not released; its figures beyond what they show by eye;
the latency and correlation results of its Figures 4 and 5, which the quoted sentence does not state.

Writes results/outputs.json (the values a receipt carries) and results/detail.json (every value computed).
Run with: python3 snn/song.py
"""

import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
RATES = (10, 20, 30, 40)
WARM, MEAS, START, FROZEN = 1000.0, 200.0, 20.0, 50.0
FROZEN_UP = 15
RATIO = (1.0, 1.3)
CV_MIN = 0.7
RISE_MAX = 12.0
EXCESS_FACTOR = 2.0
STRONG = 0.8
LIMIT = 200

NE, NI = 1000, 200
DT = 0.1
TAU_M, V_REST, E_EX, E_IN, V_TH, V_RESET = 20.0, -70.0, 0.0, -70.0, -54.0, -60.0
TAU_EX = TAU_IN = 5.0
GIN_PEAK, GMAX = 0.05, 0.015
TAU_P = TAU_MS = 20.0
A_PLUS = 0.005
A_MINUS = 1.05 * 0.005
RATE_IN = 10.0
WIN, NBIN = 500, 100

OUTPUTS = ("ratios", "cvs", "rates", "rate_rise", "ratio_min", "ratio_max", "cv_min", "excess_start",
           "excess_equilibrium", "strong_shares", "extremes", "frozen_rise", "start", "conditions_met",
           "conditions_total", "test_passed", "controls_passed", "controls_total")


class Refused(Exception):
    pass


# ---------------------------------------------------------------- seeds and the generator

def words(seed, label):
    """Four 64-bit words for xoshiro256**, from SHA-256 of seed and label (never all zero)."""
    h = hashlib.sha256(f"{seed}/{label}".encode()).digest()
    w = [int.from_bytes(h[8 * i:8 * i + 8], "big") for i in range(4)]
    if not any(w):
        w[0] = 1
    return [f"{x:016x}" for x in w]


MASK = (1 << 64) - 1


def _rotl(v, k):
    return ((v << k) | (v >> (64 - k))) & MASK


class Xoshiro:
    def __init__(self, w):
        self.s = [int(x, 16) for x in w]

    def next64(self):
        s = self.s
        r = (_rotl((s[1] * 5) & MASK, 7) * 9) & MASK
        t = (s[1] << 17) & MASK
        s[2] ^= s[0]
        s[3] ^= s[1]
        s[1] ^= s[2]
        s[0] ^= s[3]
        s[2] ^= t
        s[3] = _rotl(s[3], 45)
        return r

    def unif(self):
        return (self.next64() >> 11) * 2.0 ** -53

    def below(self, m):
        return int(self.unif() * m)

    def poisson(self, lam, emlam):
        u, p = self.unif(), emlam
        c, k = p, 0
        while u >= c and k < 1000:
            k += 1
            p *= lam / k
            c += p
        return k


# ---------------------------------------------------------------- the plain implementation (control)

def plain_run(w, rate, warm, meas, plastic, weights=None):
    """The C program's "run", step for step in Python's floats (the same operations in the same order)."""
    rng = Xoshiro(w)
    g = [GMAX] * NE if weights is None else [x * GMAX for x in weights]
    P, last = [0.0] * NE, [0] * NE
    warm_steps, meas_steps = round(warm / (DT * 1e-3)), round(meas / (DT * 1e-3))
    lam_in = NI * RATE_IN * DT * 1e-3
    em_in = math.exp(-lam_in)
    lam_ex = NE * rate * DT * 1e-3
    em_ex = math.exp(-lam_ex)
    dec_ex, dec_in, dec_m = math.exp(-DT / TAU_EX), math.exp(-DT / TAU_IN), math.exp(-DT / TAU_MS)
    v, gex, gin, M = V_REST, 0.0, 0.0, 0.0
    post_n = isi_n = pre_n = inh_n = 0
    last_post = -1
    isi_s = isi_ss = gex_sum = gin_sum = 0.0
    corr = [0] * NBIN
    pre_ring, post_ring = [], []
    for n in range(warm_steps + meas_steps):
        measuring = n >= warm_steps
        ki = rng.poisson(lam_in, em_in)
        gin += ki * GIN_PEAK
        ke = rng.poisson(lam_ex, em_ex)
        for _ in range(ke):
            a = rng.below(NE)
            gex += g[a]
            if plastic:
                g[a] += M * GMAX
                if g[a] < 0.0:
                    g[a] = 0.0
                P[a] = P[a] * math.exp(-(n - last[a]) * DT / TAU_P) + A_PLUS
                last[a] = n
            if measuring:
                pre_n += 1
                pre_ring.append(n)
                for q in post_ring:
                    d = n - q
                    if 1 <= d <= WIN:
                        corr[50 + (d - 1) // 10] += 1
        if measuring:
            inh_n += ki
        G = 1.0 + gex + gin
        vinf = (V_REST + gex * E_EX + gin * E_IN) / G
        v = vinf + (v - vinf) * math.exp(-DT * G / TAU_M)
        if measuring:
            gex_sum += gex
            gin_sum += gin
        if v >= V_TH:
            v = V_RESET
            if plastic:
                M -= A_MINUS
                for a in range(NE):
                    p = P[a] * math.exp(-(n - last[a]) * DT / TAU_P)
                    P[a] = p
                    last[a] = n
                    g[a] += p * GMAX
                    if g[a] > GMAX:
                        g[a] = GMAX
            if measuring:
                post_n += 1
                if last_post >= 0:
                    isi = (n - last_post) * DT
                    isi_s += isi
                    isi_ss += isi * isi
                    isi_n += 1
                last_post = n
                pre_ring = [x for x in pre_ring if n - x <= WIN - 1]
                for x in pre_ring:
                    corr[49 - (n - x) // 10] += 1
                post_ring.append(n)
        if measuring:
            post_ring = [q for q in post_ring if n - q < WIN]
            pre_ring = [x for x in pre_ring if n - x <= WIN - 1]
        gex *= dec_ex
        gin *= dec_in
        M *= dec_m
    T = meas_steps * DT * 1e-3
    mean_isi = isi_s / isi_n if isi_n else 0.0
    var = (isi_ss - isi_n * mean_isi * mean_isi) / (isi_n - 1) if isi_n > 1 else 0.0
    cv = math.sqrt(var if var > 0 else 0) / mean_isi if (isi_n > 1 and mean_isi > 0) else 0.0
    return {"post_spikes": post_n, "rate": post_n / T, "cv": cv, "gex_mean": gex_sum / meas_steps,
            "gin_mean": gin_sum / meas_steps, "pre_spikes": pre_n, "inh_spikes": inh_n, "corr": corr,
            "weights": [x / GMAX for x in g]}


# ---------------------------------------------------------------- the C program

def build(work):
    exe = os.path.join(work, "song")
    subprocess.run(["gcc", "-O2", "-ffp-contract=off", "-std=gnu11", "-o", exe, os.path.join(HERE, "song.c"), "-lm"],
                   check=True)
    return exe


def c_run(exe, w, rate, warm, meas, plastic, win="-", wout="-"):
    out = subprocess.run([exe, "run", *w, repr(float(rate)), repr(float(warm)), repr(float(meas)), str(int(plastic)),
                          win, wout], check=True, capture_output=True, text=True).stdout
    got = {}
    for line in out.splitlines():
        k, _, v = line.partition("=")
        got[k] = v
    res = {"post_spikes": int(got["post_spikes"]), "rate": float(got["rate"]), "cv": float(got["cv"]),
           "gex_mean": float(got["gex_mean"]), "gin_mean": float(got["gin_mean"]),
           "pre_spikes": int(got["pre_spikes"]), "inh_spikes": int(got["inh_spikes"]),
           "corr": [int(x) for x in got["corr"].split(",")],
           "rates_10s": [float(x) for x in got["rates_10s"].split(",")] if got.get("rates_10s") else []}
    if wout != "-":
        with open(wout) as fh:
            res["weights"] = [float(x) for x in fh.read().split()]
    return res


def c_pair(exe, dt_ms):
    out = subprocess.run([exe, "pair", repr(float(dt_ms))], check=True, capture_output=True, text=True).stdout
    return float(out.strip().split("=")[1])


# ---------------------------------------------------------------- measures (rule 4)

def ratio(gex_mean, gin_mean):
    return ((V_TH - V_REST) + gin_mean * (V_TH - E_IN)) / (gex_mean * (E_EX - V_TH))


def correlation(res, meas):
    """The correlogram divided by chance: postsynaptic spikes times presynaptic spikes per ms."""
    chance = res["post_spikes"] * (res["pre_spikes"] / (meas * 1000.0))
    if chance <= 0:
        return [float("nan")] * NBIN
    return [c / chance for c in res["corr"]]


def excess_before(corr):
    return sum(c - 1.0 for c in corr[30:50]) / 20.0


def after_mean(corr):
    return sum(corr[50:]) / 50.0


def shares(weights):
    n = len(weights)
    return {"strong": sum(1 for x in weights if x >= STRONG) / n,
            "bottom": sum(1 for x in weights if x < 0.05) / n,
            "top": sum(1 for x in weights if x >= 0.95) / n,
            "mean": sum(weights) / n}


def conditions(eq, rise, ex_start, ex_eq):
    cond = {}
    for r in RATES:
        cond[f"{r} Hz: ratio within {RATIO[0]}-{RATIO[1]}"] = RATIO[0] <= eq[r]["ratio"] <= RATIO[1]
    for r in RATES:
        cond[f"{r} Hz: CV at least {CV_MIN}"] = eq[r]["cv"] >= CV_MIN
    cond[f"output rate rises less than {RISE_MAX:g} Hz from 10 to 40 Hz"] = rise < RISE_MAX
    cond[f"excess before at 10 Hz at least {EXCESS_FACTOR:g} times the start's"] = ex_eq >= EXCESS_FACTOR * ex_start
    return cond


def controls(exe, seed, start, eq10, work):
    w = words(seed, "song/control/plain")
    wout = os.path.join(work, "plain.txt")
    c = c_run(exe, w, 10, 0.0, 0.5, 1, "-", wout)
    p = plain_run(w, 10, 0.0, 0.5, 1)
    same = all(c[k] == p[k] for k in ("post_spikes", "rate", "cv", "gex_mean", "gin_mean", "pre_spikes",
                                       "inh_spikes", "corr", "weights"))
    plus, minus = c_pair(exe, -10.0), c_pair(exe, 10.0)
    pair_ok = abs(plus - A_PLUS * math.exp(-0.5)) < 1e-12 and abs(minus + A_MINUS * math.exp(-0.5)) < 1e-12
    ne, ni = NE * 10 * START, NI * RATE_IN * START
    counts_ok = abs(start["pre_spikes"] - ne) < 4 * math.sqrt(ne) and abs(start["inh_spikes"] - ni) < 4 * math.sqrt(ni)
    gex0, gin0 = NE * 10 * TAU_EX * 1e-3 * GMAX, NI * RATE_IN * TAU_IN * 1e-3 * GIN_PEAK
    means_ok = abs(start["gex_mean"] / gex0 - 1) < 0.02 and abs(start["gin_mean"] / gin0 - 1) < 0.02
    after_ok = (abs(after_mean(correlation(start, START)) - 1) < 0.02
                and abs(after_mean(correlation(eq10, MEAS)) - 1) < 0.02)
    return {"the C program matches the plain implementation bit for bit over 0.5 s": bool(same),
            "one pre and one post spike 10 ms apart change a synapse by A+ e^(-1/2) and -A- e^(-1/2)": pair_ok,
            "the start run's arrivals within four standard errors of 200,000 and 40,000": counts_ok,
            "the start run's mean conductances within 2% of 0.75 and 0.5": means_ok,
            "the correlogram after the spike averages 1 within 0.02 (start and 10 Hz runs)": after_ok}


def fmt(x, nd=2):
    return f"{x:.{nd}f}"


def run(seed, results="results", log=sys.stderr):
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        raise Refused("the seed must be 64 hex characters")
    if shutil.which("gcc") is None:
        raise Refused("no gcc in this image")
    os.makedirs(results, exist_ok=True)
    work = tempfile.mkdtemp(prefix="work-", dir=results)   # the sandbox's /tmp cannot run what is built in it
    exe = build(work)

    eq = {}
    for r in RATES:
        wout = os.path.join(work, f"weights-{r}.txt")
        res = c_run(exe, words(seed, f"song/run/{r}"), r, WARM, MEAS, 1, "-", wout)
        res["ratio"] = ratio(res["gex_mean"], res["gin_mean"])
        res["shares"] = shares(res["weights"])
        res["correlation"] = correlation(res, MEAS)
        eq[r] = res
        print(f"{r} Hz: rate {res['rate']:.2f}, CV {res['cv']:.3f}, ratio {res['ratio']:.3f}, "
              f"strong {res['shares']['strong']:.3f}", file=log)
    start = c_run(exe, words(seed, "song/start"), 10, 0.0, START, 0, "-", "-")
    start["correlation"] = correlation(start, START)
    ex_start = excess_before(start["correlation"])
    ex_eq = excess_before(eq[10]["correlation"])
    w10 = os.path.join(work, "weights-10.txt")
    held10 = c_run(exe, words(seed, "song/held/10"), 10, 0.0, FROZEN, 0, w10, "-")
    held15 = c_run(exe, words(seed, f"song/held/{FROZEN_UP}"), FROZEN_UP, 0.0, FROZEN, 0, w10, "-")
    frozen_rise = held15["rate"] - held10["rate"]
    rise = eq[40]["rate"] - eq[10]["rate"]
    print(f"start: rate {start['rate']:.1f}, CV {start['cv']:.3f}; excess {ex_start:.4f} -> {ex_eq:.4f}; "
          f"held peaks 10 -> 15 Hz: {held10['rate']:.1f} -> {held15['rate']:.1f}", file=log)

    ctl = controls(exe, seed, start, eq[10], work)
    print(f"controls: {sum(ctl.values())} of {len(ctl)}", file=log)
    if not all(ctl.values()):
        raise AssertionError(f"a control failed: {[c for c, ok in ctl.items() if not ok]}")
    cond = conditions(eq, rise, ex_start, ex_eq)

    def each(key, nd=2):
        return ", ".join(f"{r} Hz {fmt(eq[r][key], nd)}" for r in RATES)
    values = {
        "ratios": "inhibitory/excitatory at threshold: " + each("ratio"),
        "cvs": "output CV: " + each("cv"),
        "rates": "output Hz: " + each("rate"),
        "rate_rise": round(rise, 3),
        "ratio_min": round(min(eq[r]["ratio"] for r in RATES), 4),
        "ratio_max": round(max(eq[r]["ratio"] for r in RATES), 4),
        "cv_min": round(min(eq[r]["cv"] for r in RATES), 4),
        "excess_start": round(ex_start, 5),
        "excess_equilibrium": round(ex_eq, 5),
        "strong_shares": "peaks >= 0.8 gmax: " + ", ".join(f"{r} Hz {eq[r]['shares']['strong']:.3f}" for r in RATES),
        "extremes": ("bottom/top twentieth: " + "; ".join(
            f"{r} Hz {eq[r]['shares']['bottom']:.3f}/{eq[r]['shares']['top']:.3f}" for r in (10, 40))),
        "frozen_rise": round(frozen_rise, 2),
        "start": f"all at gmax, 10 Hz: output {start['rate']:.1f} Hz, CV {start['cv']:.3f}",
        "conditions_met": sum(cond.values()),
        "conditions_total": len(cond),
        "test_passed": int(all(cond.values())),
        "controls_passed": sum(ctl.values()),
        "controls_total": len(ctl),
    }
    out = {k: values[k] for k in OUTPUTS}
    for k, v in out.items():
        if isinstance(v, str) and len(v) > LIMIT:
            raise AssertionError(f"{k}: longer than {LIMIT} characters: {v}")
    detail = {"conditions": cond, "controls": ctl,
              "equilibrium": {str(r): {k: eq[r][k] for k in ("rate", "cv", "ratio", "gex_mean", "gin_mean",
                                                            "post_spikes", "pre_spikes", "inh_spikes", "shares",
                                                            "correlation", "rates_10s")} for r in RATES},
              "histograms": {str(r): [sum(1 for x in eq[r]["weights"] if b / 20 <= x < (b + 1) / 20 or
                                          (b == 19 and x >= 1.0)) for b in range(20)] for r in RATES},
              "start": {k: start[k] for k in ("rate", "cv", "gex_mean", "gin_mean", "post_spikes", "pre_spikes",
                                              "inh_spikes", "correlation")},
              "held_peaks": {"10": held10["rate"], str(FROZEN_UP): held15["rate"]},
              "excess": {"start": ex_start, "equilibrium_10": ex_eq}}
    with open(os.path.join(results, "outputs.json"), "w", encoding="ascii") as fh:
        json.dump(out, fh, indent=2, sort_keys=True)
        fh.write("\n")
    with open(os.path.join(results, "detail.json"), "w", encoding="ascii") as fh:
        json.dump(detail, fh, indent=1, sort_keys=True)
        fh.write("\n")
    shutil.rmtree(work, ignore_errors=True)
    return out, detail


def main():
    seed = os.environ.get("ECDYSIS_SEED", "")
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        sys.exit("ECDYSIS_SEED must be the 64-hex seed the archive issued")
    try:
        out, _ = run(seed)
    except Refused as e:
        sys.exit(f"song: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
