#!/usr/bin/env python3
"""Masquelier, Guyonneau & Thorpe (2008): STDP finds the start of a repeating pattern in continuous spike trains.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:6c301e23f4249a33) is from Masquelier,
Guyonneau and Thorpe, "Spike Timing Dependent Plasticity Finds the Start of Repeating Patterns in Continuous Spike
Trains", PLoS ONE 3(1), e1377 (2008): "As such, STDP is able to solve a very difficult computational problem: to
localize a repeating spatio-temporal spike pattern embedded in equally dense 'distractor' spike trains."

Its registered test: refuted if, simulating the paper's model as its Methods state (2,000 afferents firing 0 to 90 Hz
with a spike forced after 50 ms of silence, plus 10 Hz; a 50 ms pattern of the first 1,000 pasted into a quarter of the
50 ms sections with 1 ms jitter; an SRM neuron with threshold 500 and initial weights 0.475; nearest-spike STDP;
450 s), fewer than 50 of 100 runs end selective: over the last 150 s, discharging in at least 90% of the pattern's
presentations at a mean latency under 10 ms, and at most 15 times outside them.

The model is the paper's Materials and Methods, simulated in C (stdp/pattern.c, compiled here with the image's gcc);
the paper's equations are printed as images, and where this module reads one from the text it says so. No code or data
is read. Every rule below was fixed before any seed existed.

1. The afferents (Methods, Poisson spike trains): 2,000 afferents on a 1 ms grid over a 150 s train. Each fires in a
   step with probability r dt, its rate r in [0, 90] Hz moving by s dt each step, and s, the rate's speed, moving by a
   uniform random step of at most a fifth of its bound, kept within +-1,800 Hz/s (the speed that takes 0 to 90 Hz in
   50 ms; the step's size, printed only in an image, is this module's reading); r and s start uniform in their ranges.
   An afferent silent for more than 50 ms fires. The first 1,000 afferents' spikes in one 50 ms section, drawn
   uniformly, are the pattern; a quarter of the 3,000 sections, drawn uniformly among the sets with no two
   consecutive, have those afferents' spikes replaced by the pattern's, each spike jittered by a Gaussian of 1 ms
   standard deviation. Then 10 Hz of spontaneous spikes on every afferent (Bernoulli on the same grid). The 150 s train
   is pasted three times: 450 s.
2. The neuron (Methods, LIF as Gerstner's SRM): each input adds w K (exp(-t/10 ms) - exp(-t/2.5 ms)), K making its peak
   1; after its own spike at t_i the neuron adds T (2 exp(-(t - t_i)/10 ms) - 4 (exp(-(t - t_i)/10 ms) -
   exp(-(t - t_i)/2.5 ms))), the pulse and the negative afterpotential (K1 = 2, K2 = 4; the form, an image, read from
   the text's description of its two terms); both kernels zero beyond 70 ms (7 tau_m); threshold T = 500; a spike
   flushes every EPSP; a refractory period of 1 ms. The potential is checked at every input (about every 8
   microseconds), and a spike is emitted at the first input at which it reaches the threshold.
3. STDP (Methods): at a post-synaptic spike, each afferent's last spike before it, if no other post-synaptic spike
   came between them and it is at most 7 tau+ earlier, adds a+ exp(-dt/tau+); each afferent's first spike after a
   post-synaptic spike, at most 7 tau- later, subtracts a- exp(-dt/tau-) (the nearest-spike approximation); tau+ =
   16.8 ms, tau- = 33.7 ms, a+ = 0.03125, a- = 0.85 a+; weights clipped to [0, 1]; all start at 0.475.
4. Scoring each run over its last 150 s (the paper's window): the pattern's 750 presentations there; a hit is a
   presentation with a discharge in its 50 ms, its latency that of the first; a false alarm is a discharge in no
   presentation. Selective (the test's reading of "localize"): hits in at least 90% of presentations, a mean latency
   under 10 ms, at most 15 false alarms (0.1 Hz). Successful by the paper's own criteria, beside the test: a mean
   latency under 10 ms, hits in more than 98%, no false alarm. Stopped: fewer than 10 discharges in the window.
5. 100 runs, run i under the seed SHA-256(receipt seed, i); test_passed is 1 if at least 50 end selective.

Controls (controls_passed counts those that behave as stated): the afferents' mean rate is the paper's 54 Hz before
spontaneous activity and 64 Hz after (each within 2 Hz, over the 100 runs); every run pastes 750 sections, none
consecutive; with the weights held at 0.475 and at 0.325 the neuron fires at the paper's initial 63 and 38 Hz (each
within 5 Hz, over four 5 s trains); the C simulation agrees with a reference in Python, spike for spike and weight for
weight, on a 3 s train of 1,000 afferents with STDP; a run repeated under the same seed gives the same record.

What it cannot check: the authors' own code (available from them on request, never released), so the readings in
rules 1 and 2; and the event-driven prediction of threshold crossings between inputs, here checked at each input.

Writes results/outputs.json and results/detail.json. Run with: python3 stdp/pattern.py
"""

import bisect
import concurrent.futures as cf
import hashlib
import json
import math
import os
import re
import shutil
import statistics
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RUNS = 100
N, NP, BASE, REPEATS, W0 = 2000, 1000, 150, 3, 0.475
SECTION = 50.0
SELECTIVE_HIT, SELECTIVE_LATENCY, SELECTIVE_FA = 0.90, 10.0, 15
STRICT_HIT, STRICT_LATENCY = 0.98, 10.0
STOPPED_BELOW = 10
LIMIT = 200
OUTPUTS = ("selective", "strict", "stopped", "latency", "hit_rate", "false_alarms", "potentiated", "afferent_rates",
           "initial_rates", "controls_passed", "controls_total", "test_passed")
# the model's constants, as pattern.c holds them (for the reference)
TAU_M, TAU_S, THRESHOLD, K1, K2, CUT, REFRACTORY = 10.0, 2.5, 500.0, 2.0, 4.0, 70.0, 1.0
TAU_PLUS, TAU_MINUS, A_PLUS = 16.8, 33.7, 0.03125
A_MINUS = 0.85 * A_PLUS


def compile_c(work):
    exe = os.path.join(work, "pattern")
    subprocess.run(["gcc", "-O2", "-o", exe, os.path.join(HERE, "pattern.c"), "-lm"], check=True)
    return exe


def run_c(exe, work, seed, n=N, npat=NP, base=BASE, repeats=REPEATS, w0=W0, stdp=1, dump="-"):
    out = os.path.join(work, f"run_{seed}_{n}_{base}_{repeats}_{w0}_{stdp}.txt")
    subprocess.run([exe, str(seed), str(n), str(npat), str(base), str(repeats), repr(w0), str(stdp), dump, out],
                   check=True)
    rec = {}
    with open(out) as fh:
        for line in fh:
            parts = line.split()
            rec[parts[0]] = parts[1:]
    os.remove(out)
    return rec


def seed_of(seed, i):
    return int(hashlib.sha256(f"{seed}:{i}".encode()).hexdigest()[:16], 16)


def score(rec, base=BASE, repeats=REPEATS):
    """Rule 4."""
    post = [float(x) for x in rec["post"]]
    sections = [int(x) for x in rec["sections"]]
    w = [float(x) for x in rec["weights"]]
    off = (repeats - 1) * base * 1000.0
    starts = [s * SECTION + off for s in sections]
    window = [t for t in post if t >= off]
    first, fa = {}, 0
    for t in window:
        i = bisect.bisect_right(starts, t) - 1
        if i >= 0 and t - starts[i] < SECTION:
            first.setdefault(i, t - starts[i])
        else:
            fa += 1
    hit = len(first) / len(starts)
    lat = statistics.fmean(first.values()) if first else math.inf
    pat = w[:NP]
    rest = w[NP:]
    return {"discharges": len(window), "false_alarms": fa, "hit_rate": round(hit, 4),
            "latency": round(lat, 3) if math.isfinite(lat) else None,
            "selective": hit >= SELECTIVE_HIT and lat < SELECTIVE_LATENCY and fa <= SELECTIVE_FA,
            "strict": hit > STRICT_HIT and lat < STRICT_LATENCY and fa == 0,
            "stopped": len(window) < STOPPED_BELOW,
            "potentiated_pattern": sum(1 for x in pat if x >= 0.9), "potentiated_other": sum(1 for x in rest if x >= 0.9),
            "depressed_other": sum(1 for x in rest if x < 0.1),
            "posts": int(rec["posts"][0]), "pasted": int(rec["pasted"][0]), "consecutive": int(rec["consecutive"][0]),
            "rate_original": float(rec["afferent_rate_original"][0]), "rate_forced": float(rec["afferent_rate_forced"][0]),
            "rate_total": float(rec["afferent_rate_total"][0])}


# ---------------------------------------------------------------- the reference, in Python (a control)

def reference(events, n, w0):
    """Rules 2 and 3 replayed in Python over the C program's dumped inputs: the post-synaptic spikes and the weight of
    each input's afferent after it."""
    tp = math.log(TAU_M / TAU_S) * TAU_M * TAU_S / (TAU_M - TAU_S)
    K = 1.0 / (math.exp(-tp / TAU_M) - math.exp(-tp / TAU_S))
    w = [w0] * n
    last_pre = [-1e18] * n
    since_post = [False] * n
    queue = []
    qh = 0
    A = B = tA = 0.0
    t_post = -1e18
    posts, weights = [], []
    for t, a in events:
        dA, dB = math.exp(-(t - tA) / TAU_M), math.exp(-(t - tA) / TAU_S)
        A *= dA
        B *= dB
        tA = t
        while qh < len(queue) and t - queue[qh][0] > CUT:
            age = t - queue[qh][0]
            A -= queue[qh][1] * math.exp(-age / TAU_M)
            B -= queue[qh][1] * math.exp(-age / TAU_S)
            qh += 1
        since = t - t_post
        eta = 0.0
        if 0 <= since < CUT:
            eta = THRESHOLD * (K1 * math.exp(-since / TAU_M) - K2 * (math.exp(-since / TAU_M) - math.exp(-since / TAU_S)))
        V = K * (A - B) + eta
        if V >= THRESHOLD and since >= REFRACTORY:
            for j in range(n):
                d = t - last_pre[j]
                if last_pre[j] > t_post and 0 <= d <= 7.0 * TAU_PLUS:
                    w[j] = min(1.0, w[j] + A_PLUS * math.exp(-d / TAU_PLUS))
            since_post = [False] * n
            A = B = 0.0
            queue, qh = [], 0
            t_post = t
            posts.append(t)
        if not since_post[a]:
            d = t - t_post
            if 0 <= d <= 7.0 * TAU_MINUS:
                w[a] = max(0.0, w[a] - A_MINUS * math.exp(-d / TAU_MINUS))
        since_post[a] = True
        last_pre[a] = t
        A += w[a]
        B += w[a]
        queue.append((t, w[a]))
        weights.append(w[a])
    return posts, weights


def reference_control(exe, work, seed):
    dump = os.path.join(work, "dump.txt")
    run_c(exe, work, seed, n=1000, npat=500, base=3, repeats=1, w0=0.9, stdp=1, dump=dump)
    events, c_w, c_posts = [], [], []
    with open(dump) as fh:
        for line in fh:
            p = line.split()
            if p[0] == "in":
                events.append((float(p[1]), int(p[2])))
                c_w.append(float(p[3]))
            else:
                c_posts.append(float(p[1]))
    os.remove(dump)
    posts, weights = reference(events, 1000, 0.9)
    same_posts = len(posts) == len(c_posts) and all(abs(a - b) <= 1e-5 for a, b in zip(posts, c_posts))
    same_w = len(weights) == len(c_w) and all(abs(a - b) <= 1e-8 for a, b in zip(weights, c_w))
    return same_posts and same_w and len(posts) > 0, {"events": len(events), "posts_c": len(c_posts),
                                                     "posts_python": len(posts)}


# ---------------------------------------------------------------- the verdict

def summary(values, digits=2):
    v = sorted(values)
    if not v:
        return "none"
    return f"median {statistics.median(v):.{digits}f} (range {v[0]:.{digits}f} to {v[-1]:.{digits}f})"


def run(seed, results="results", runs=RUNS, workers=2, initial_seconds=5, initial_trains=4):
    os.makedirs(results, exist_ok=True)
    work = os.path.join(results, "work")
    shutil.rmtree(work, ignore_errors=True)
    os.makedirs(work)
    exe = compile_c(work)
    seeds = [seed_of(seed, i) for i in range(runs)]
    with cf.ThreadPoolExecutor(workers) as pool:
        scored = list(pool.map(lambda s: score(run_c(exe, work, s)), seeds))
        init = {}
        for w0 in (0.475, 0.325):
            recs = list(pool.map(lambda s: run_c(exe, work, s, base=initial_seconds, repeats=1, w0=w0, stdp=0),
                                 [seed_of(seed, 1000 + k) for k in range(initial_trains)]))
            init[w0] = statistics.fmean(int(r["posts"][0]) / initial_seconds for r in recs)
    ctl = {}
    rate0 = statistics.fmean(s["rate_original"] for s in scored)
    rate1 = statistics.fmean(s["rate_total"] for s in scored)
    ctl["the afferents fire at the paper's 54 Hz, and 64 Hz with spontaneous activity (within 2 Hz)"] = (
        abs(rate0 - 54) <= 2 and abs(rate1 - 64) <= 2)
    ctl["every run pastes 750 sections, none consecutive"] = all(s["pasted"] == 750 and s["consecutive"] == 0
                                                                 for s in scored)
    ctl["with fixed weights the neuron fires at the paper's 63 Hz (0.475) and 38 Hz (0.325), within 5 Hz"] = (
        abs(init[0.475] - 63) <= 5 and abs(init[0.325] - 38) <= 5)
    ok, ref = reference_control(exe, work, seed_of(seed, 2000))
    ctl["the C simulation agrees with the Python reference, spike for spike and weight for weight"] = ok
    a = run_c(exe, work, seed_of(seed, 3000), base=4, repeats=1)
    b = run_c(exe, work, seed_of(seed, 3000), base=4, repeats=1)
    ctl["a run repeated under the same seed gives the same record"] = a == b
    shutil.rmtree(work, ignore_errors=True)

    selective = sum(s["selective"] for s in scored)
    strict = sum(s["strict"] for s in scored)
    stopped = sum(s["stopped"] for s in scored)
    sel = [s for s in scored if s["selective"]]
    cond = {"at least 50 of 100 runs end selective": selective >= 50}
    fas = sorted(s["false_alarms"] for s in scored if not s["stopped"])
    values = {
        "selective": selective, "strict": strict, "stopped": stopped,
        "latency": "selective runs: " + summary([s["latency"] for s in sel]) + " ms",
        "hit_rate": "selective runs: " + summary([s["hit_rate"] for s in sel], 4),
        "false_alarms": (f"runs still firing: {len(fas)}; with 0 false alarms {sum(1 for x in fas if x == 0)}, "
                         f"1 {sum(1 for x in fas if x == 1)}, 2 to 15 {sum(1 for x in fas if 2 <= x <= 15)}, "
                         f"more {sum(1 for x in fas if x > 15)}"),
        "potentiated": ("selective runs, weights >= 0.9: pattern afferents " + summary([s["potentiated_pattern"] for s in sel], 0)
                        + "; others " + summary([s["potentiated_other"] for s in sel], 0)),
        "afferent_rates": f"{rate0:.2f} Hz before spontaneous activity ({statistics.fmean(s['rate_forced'] for s in scored):.2f} forced), {rate1:.2f} Hz in all",
        "initial_rates": f"weights fixed at 0.475: {init[0.475]:.1f} Hz; at 0.325: {init[0.325]:.1f} Hz",
        "controls_passed": sum(bool(v) for v in ctl.values()), "controls_total": len(ctl),
        "test_passed": int(all(cond.values())),
    }
    out = {k: values[k] for k in OUTPUTS}
    for k, v in out.items():
        if isinstance(v, str) and len(v) > LIMIT:
            raise AssertionError(f"{k}: longer than {LIMIT} characters: {v}")
    detail = {"conditions": cond, "controls": ctl, "reference": ref, "initial_rates": {str(k): v for k, v in init.items()},
              "runs": [{"run": i, "seed": seeds[i], **s} for i, s in enumerate(scored)]}
    with open(os.path.join(results, "outputs.json"), "w", encoding="ascii") as fh:
        json.dump(out, fh, indent=2, sort_keys=True)
        fh.write("\n")
    with open(os.path.join(results, "detail.json"), "w", encoding="ascii") as fh:
        json.dump(detail, fh, indent=1, sort_keys=True)
        fh.write("\n")
    return out, detail


def main():
    seed = os.environ.get("ECDYSIS_SEED", "")
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        sys.exit("ECDYSIS_SEED must be the 64-hex seed the archive issued")
    out, _ = run(seed)
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
