"""Shifted STDP stabilises synaptic strengths: Babadi & Abbott (2010), simulated as the paper specifies.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:e5149bd6f1025244) is from Babadi and Abbott,
"Intrinsic stability of temporally shifted spike-timing dependent plasticity", PLoS Computational Biology 6(11),
e1000961 (2010; CC BY), its abstract: "Through simulations and analytic calculations, we show that a small temporal shift
in the STDP window that causes synchronous, or nearly synchronous, pre- and postsynaptic action potentials to induce
long-term depression can stabilize synaptic strengths." Its Results: "With conventional, unshifted STDP (d = 0),
synaptic strengths grow or shrink indefinitely unless limits are imposed ... if we introduce a d = 2 ms shift into the
STDP window, the steady-state distribution of synaptic strengths is unimodal and stable even when no limits are
imposed (figure 1B)."

The model, as the paper's Methods and Table 1 give it (read in the PLoS PDF and the Europe PMC XML, whose formulas are
images): an integrate-and-fire neuron, tau_m dV/dt = (V_r - V) + I_ex - I_in, tau_m = 20 ms, V_r = -60 mV, reset to
V_r on reaching V_th = -40 mV; 1000 excitatory and 250 inhibitory synapses receiving independent Poisson spike trains
at 10 Hz each; each presynaptic spike makes its input jump by the synapse's strength (in mV) and the input decays with
tau_s = 5 ms; inhibitory strengths fixed at 4 mV; excitatory strengths changed by pair-based STDP,
F(dt) = -A_- exp((dt - d)/tau_-) for dt <= d and A_+ exp(-(dt - d)/tau_+) for dt > d, dt = t_post - t_pre,
A_+ = 0.006 mV, A_- = 0.005 mV, tau_+ = tau_- = 20 ms, d = 2 ms; only nearest neighbours pair ("each postsynaptic
action potential can only potentiate a synapses on the basis of the interval to the presynaptic spike immediately
preceding it, and each presynaptic action potential can only depress a synapses on the basis of the timing interval to
the immediately preceding postsynaptic spike"); initial strengths uniform on 1-5 mV; negative strengths not allowed;
no upper limit for shifted STDP. The paper ran each regime for 10^5 s and called it steady when the first three
moments of the strengths and the firing rate stayed constant.

Rules, committed before any run of the paper's model at its parameters (the program was timed and the controls tried
on other rates and sizes only):

1. Integration (snn/babadi.c; the paper names no scheme): steps of 0.1 ms; in each, the step's presynaptic spikes at
   time t (excitatory ones adding their strength to I_ex and, with plasticity, applying F(t_lastpost - t) to their
   synapse once the neuron has fired), then the exact solution of the linear membrane and input equations over the
   step, then a postsynaptic spike at t + 0.1 ms if V >= V_th, which resets V and applies F(t_spike - t_lastpre) to
   every synapse that has received a presynaptic spike since the previous postsynaptic spike; a presynaptic spike
   applies F(t_lastpost - t) only if the neuron has fired since that synapse's previous presynaptic spike. Pairs are
   thus only between spikes adjacent in the order of events (no postsynaptic spike between a pre-post pair, no
   presynaptic spike at that synapse between a post-pre pair), the reading under which the paper's nearest-neighbour intervals have the density it uses,
   r exp(-r t) with r the sum of the pre- and postsynaptic rates (its equation 12); a timing run at other inputs (12 Hz,
   d = 3 ms) with each postsynaptic spike pairing with the last presynaptic spike whatever came between showed
   strengths growing without bound, every presynaptic spike paired again with every new postsynaptic one, and the rules
   were set to the adjacent reading before any run at the paper's parameters (the same timing run then settled near
   1.4 mV at about 32 Hz). The pairing at a postsynaptic spike uses
   F as written, so a presynaptic spike less than d before it depresses (the paper's shift), and strengths are clipped
   at 0 after each change. Spike times are whole steps and intervals are counted in steps, so an interval of exactly d
   (which the 0.1 ms grid makes common) depresses, as F's dt <= d says, at every time of a run. A trial under a seed of
   Imago's own found the strengths and rates of every run stepping up together near 16,800 s: with times held in
   milliseconds as floating-point numbers, about 40% of intervals of exactly d rounded above d, and so potentiated, once
   the times passed 2^24 ms (none between 2^22 and 2^24 ms, about a fifth before); the times were made whole steps
   before the sealed run. Inputs:
   in each step a Poisson number of excitatory spikes with mean N_ex r_ex dt, each at a synapse drawn uniformly, and a
   Poisson number of inhibitory spikes with mean N_in r_in dt (the superposition of independent Poisson trains), from
   xoshiro256** seeded from the archive's seed.
2. Runs, each T = 20,000 s with checkpoints every 100 s (the strengths' mean, standard deviation, third central
   moment, share at 0 and maximum, and the postsynaptic spikes in the last 100 s): S1, d = 2 ms from strengths uniform on
   1-5 mV (the paper's); S2, d = 2 ms from strengths uniform on 5-9 mV (another start); U, d = 0 from 1-5 mV, no upper
   limit (conventional STDP, the paper's contrast). A run stops early, as a runaway, if a checkpoint's rate exceeds
   1,000 Hz or its mean strength 30 mV (from 5-9 mV the paper's equation 13 puts the
   neuron near 700 Hz at the start). Beside the test: d = 1 ms and d = 4 ms from 1-5 mV.
3. Settled: a run is settled when it did not run away and, between the windows 10,000-15,000 s and 15,000-20,000 s
   (the means of their 50 checkpoints), the mean strength, the standard deviation of the strengths and the firing rate
   each change by at most 5% (relative).
4. The test's conditions: C1, S1 is settled; C2, S2 is settled and its last window's mean strength is within 5% of
   S1's and its standard deviation within 10%; C3, U is not settled (it runs away or drifts), as the paper says of
   unshifted STDP without limits. The test passes when all three hold.

Beside the test, not counted: the last window's statistics of each run (mean, standard deviation, skewness, share at
0, firing rate, CV not computed), the means of d = 1, 2 and 4 ms (the paper: larger delays give lower means and
sharper distributions), and the paper's estimate of the steady rate, its equation 13, r_post = (N_ex r_ex tau_s <w> -
N_in r_in tau_s w_in - 0.5 (V_th - V_r)) / ((V_th - V_r) tau_m), against S1's.

Controls (controls_passed of controls_total):
 (a) The C program against a plain Python implementation of rule 1 on the same replayed inputs (50 excitatory and 20
     inhibitory synapses at 40 Hz, 2 s, with plasticity, d = 2 ms and d = 0): the same postsynaptic spike steps and
     final strengths within 1e-9 mV.
 (b) The free membrane: with firing and plasticity off and all strengths 2 mV for 1,000 s, the mean of V is
     V_r + tau_s (N_ex r_ex 2 mV - N_in r_in w_in) within 2% (about five standard errors).
 (c) The inputs: in S1, the excitatory and inhibitory input rates per synapse within 1% of 10 Hz.
 (d) The window: F at hand-chosen intervals (-5, 0, 1, 2, 2.1 and 10 ms) against the formula, and the strengths stay at
     or above 0 in every run.
"""

import hashlib
import json
import math
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SOURCE = os.path.join(HERE, "babadi.c")

BASE = {"nex": 1000, "nin": 250, "rex": 10.0, "rin": 10.0, "tau_m": 20.0, "vth": -40.0, "vr": -60.0, "tau_s": 5.0,
        "win": 4.0, "ap": 0.006, "am": 0.005, "tp": 20.0, "tn": 20.0, "d": 2.0, "wmax": 0.0, "dt": 0.1,
        "plastic": 1, "fire": 1, "cp": 100.0, "stop_rate": 1000.0, "stop_mean": 30.0}
T_RUN = 20000.0
WINDOWS = ((10000.0, 15000.0), (15000.0, 20000.0))
SETTLE = 0.05
START_MEAN, START_SD = 0.05, 0.10
RUNS = {  # name: (d, low, high)
    "S1": (2.0, 1.0, 5.0),
    "S2": (2.0, 5.0, 9.0),
    "U": (0.0, 1.0, 5.0),
    "d1": (1.0, 1.0, 5.0),
    "d4": (4.0, 1.0, 5.0),
}
TEST = ("Refuted if, in the paper's model (Methods and Table 1: integrate-and-fire neuron, 1000 excitatory synapses under "
        "nearest-neighbour pair STDP with A+ 0.006 and A- 0.005 mV, tau 20 ms, shift d = 2 ms, 250 inhibitory of 4 mV, "
        "Poisson inputs at 10 Hz, strengths only kept at or above 0), simulated 20,000 s from strengths uniform on 1-5 "
        "mV, the mean or SD of the strengths or the firing rate changes by over 5% between the last two 5,000 s; or a "
        "start on 5-9 mV fails that or ends over 5% from the first run's mean or 10% from its SD; or d = 0 settles "
        "likewise.")


class Refused(Exception):
    pass


class Stream:
    def __init__(self, seed, label):
        self.seed, self.label, self.n = seed, label, 0

    def below(self, m):
        self.n += 1
        h = hashlib.sha256(f"{self.seed}/{self.label}/{self.n}".encode()).digest()
        return int.from_bytes(h[:8], "big") % m

    def uniform(self, lo, hi):
        return lo + (hi - lo) * self.below(2 ** 53) / 2 ** 53


def seed64(seed, label):
    return int.from_bytes(hashlib.sha256(f"{seed}/{label}/rng".encode()).digest()[:8], "big")


def F(dt, p):
    """The paper's window (rule 1); dt in ms, an interval of exactly d (to a billionth of a step) depressing."""
    if dt <= p["d"] + 1e-9 * p["dt"]:
        return -p["am"] * math.exp((dt - p["d"]) / p["tn"])
    return p["ap"] * math.exp(-(dt - p["d"]) / p["tp"])


# ---------------------------------------------------------------- the C program

def build(work):
    exe = os.path.join(work, "babadi")
    subprocess.run(["gcc", "-O2", "-std=c99", "-o", exe, SOURCE, "-lm"], check=True)
    return exe


def c_run(exe, work, params, winit, mode="run", spikes=None):
    pfile = os.path.join(work, "params.txt")
    wfile = os.path.join(work, "winit.txt")
    ofile = os.path.join(work, "wout.txt")
    with open(wfile, "w") as fh:
        fh.write("".join(f"{x:.17g}\n" for x in winit))
    p = dict(params, winit=wfile, wout=ofile)
    with open(pfile, "w") as fh:
        for k, v in p.items():
            fh.write(f"{k} {v}\n")
    args = [exe, mode, pfile]
    if spikes is not None:
        sfile = os.path.join(work, "spikes.txt")
        with open(sfile, "w") as fh:
            fh.write("".join(f"{k} {ty} {ix}\n" for k, ty, ix in spikes))
        args.append(sfile)
    out = subprocess.run(args, check=True, capture_output=True, text=True).stdout
    res = {"cp": [], "runaway": None, "spikes": [], "end": None}
    for line in out.splitlines():
        f = line.split()
        if f[0] == "cp":
            res["cp"].append({"t": float(f[1]), "mean": float(f[2]), "sd": float(f[3]), "m3": float(f[4]),
                              "zero": float(f[5]), "max": float(f[6]), "spikes": int(f[7])})
        elif f[0] == "runaway":
            res["runaway"] = float(f[1])
        elif f[0] == "spike":
            res["spikes"].append(int(f[1]))
        elif f[0] == "end":
            res["end"] = {"t": float(f[1]), "spikes": int(f[2]), "in_ex": int(f[3]), "in_in": int(f[4]),
                          "meanV": float(f[5])}
    with open(ofile) as fh:
        res["w"] = [float(x) for x in fh.read().split()]
    return res


# ---------------------------------------------------------------- the plain implementation (control a)

def py_replay(params, winit, spikes, steps):
    """Rule 1 written plainly: returns the postsynaptic spikes (each as the step at whose start it falls) and the final
    strengths."""
    p = params
    w = list(winit)
    lastpre = [None] * p["nex"]
    postidx = [0] * p["nex"]
    pending = []
    npost = 0
    lastpost = None
    Iex = Iin = 0.0
    V = p["vr"]
    dt = p["dt"]
    em, es = math.exp(-dt / p["tau_m"]), math.exp(-dt / p["tau_s"])
    C = p["tau_s"] / (p["tau_s"] - p["tau_m"])
    by_step = {}
    for k, ty, ix in spikes:
        by_step.setdefault(k, []).append((ty, ix))
    out = []
    for k in range(steps):
        for ty, ix in by_step.get(k, []):
            if ty == 0:
                Iex += w[ix]
                if p["plastic"] and npost > postidx[ix]:
                    w[ix] = max(0.0, w[ix] + F((lastpost - k) * dt, p))
                lastpre[ix] = k
                postidx[ix] = npost
                if ix not in pending:
                    pending.append(ix)
            else:
                Iin += p["win"]
        J = Iex - Iin
        V = p["vr"] + (V - p["vr"]) * em + J * C * (es - em)
        Iex *= es
        Iin *= es
        if p["fire"] and V >= p["vth"]:
            kp = k + 1
            V = p["vr"]
            out.append(kp)
            if p["plastic"]:
                for i in pending:
                    w[i] = max(0.0, w[i] + F((kp - lastpre[i]) * dt, p))
            pending = []
            lastpost = kp
            npost += 1
    return out, w


def replay_spikes(rng, nex, nin, rate, steps, dt):
    """Independent Bernoulli spikes per synapse and step (a control's inputs, not the model's); rng a random.Random."""
    pr = rate * dt / 1000.0
    out = []
    for k in range(steps):
        for i in range(nex):
            if rng.random() < pr:
                out.append((k, 0, i))
        for i in range(nin):
            if rng.random() < pr:
                out.append((k, 1, i))
    return out


# ---------------------------------------------------------------- the assessment

def window_stats(res, lo, hi):
    pts = [c for c in res["cp"] if lo < c["t"] <= hi + 1e-9]
    if len(pts) != int(round((hi - lo) / BASE["cp"])):
        return None
    n = len(pts)
    mean = sum(c["mean"] for c in pts) / n
    sd = sum(c["sd"] for c in pts) / n
    m3 = sum(c["m3"] for c in pts) / n
    rate = sum(c["spikes"] for c in pts) / (hi - lo)
    zero = sum(c["zero"] for c in pts) / n
    return {"mean": mean, "sd": sd, "skew": m3 / sd ** 3 if sd > 0 else 0.0, "rate": rate, "zero": zero}


def settled(res):
    if res["runaway"] is not None:
        return False, None
    a, b = (window_stats(res, lo, hi) for lo, hi in WINDOWS)
    if a is None or b is None:
        return False, None
    rel = {k: abs(b[k] - a[k]) / abs(a[k]) if a[k] else float("inf") for k in ("mean", "sd", "rate")}
    return all(v <= SETTLE for v in rel.values()), {"first": a, "last": b, "change": rel}


def conditions(runs):
    """Rule 4 on the runs S1, S2 and U: the conditions, and the settling statistics of each."""
    s1_ok, s1 = settled(runs["S1"])
    s2_ok, s2 = settled(runs["S2"])
    u_ok, u = settled(runs["U"])
    c1 = s1_ok
    c2 = (s2_ok and s1 is not None
          and abs(s2["last"]["mean"] - s1["last"]["mean"]) / s1["last"]["mean"] <= START_MEAN
          and abs(s2["last"]["sd"] - s1["last"]["sd"]) / s1["last"]["sd"] <= START_SD)
    c3 = not u_ok
    cond = {"C1 S1 settled": c1, "C2 S2 settled at S1's distribution": c2, "C3 d = 0 does not settle": c3}
    return cond, s1, s2, u


def assess(seed, work):
    exe = build(work)
    runs = {}
    for name, (d, lo, hi) in RUNS.items():
        st = Stream(seed, f"init/{name}")
        winit = [st.uniform(lo, hi) for _ in range(BASE["nex"])]
        p = dict(BASE, d=d, T=T_RUN, seed=seed64(seed, name))
        runs[name] = c_run(exe, work, p, winit)
    cond, s1, s2, u = conditions(runs)

    ctl = {}
    # (a) C against Python on replayed inputs
    agree = True
    detail_a = []
    for d in (2.0, 0.0):
        p = dict(BASE, nex=50, nin=20, rex=40.0, rin=40.0, d=d, T=2.0, cp=2.0, stop_rate=0, stop_mean=0, seed=1)
        rng = random.Random(seed64(seed, f"replay/{d}"))
        winit = [4 * (1.0 + 4.0 * rng.random()) for _ in range(50)]
        steps = int(round(p["T"] * 1000 / p["dt"]))
        spikes = replay_spikes(rng, 50, 20, 40.0, steps, p["dt"])
        rc = c_run(exe, work, p, winit, mode="replay", spikes=spikes)
        ps, pw = py_replay(p, winit, spikes, steps)
        same_t = ps == rc["spikes"]
        gap = max(abs(a - b) for a, b in zip(pw, rc["w"]))
        agree &= same_t and gap < 1e-9 and len(ps) > 0
        detail_a.append({"d": d, "spikes_c": len(rc["spikes"]), "spikes_py": len(ps), "largest_gap": gap})
    ctl["(a) C against Python on replayed inputs"] = agree
    # (b) the free membrane
    p = dict(BASE, plastic=0, fire=0, T=1000.0, cp=1000.0, stop_rate=0, stop_mean=0, seed=seed64(seed, "free"))
    rf = c_run(exe, work, p, [2.0] * BASE["nex"])
    want = BASE["vr"] + BASE["tau_s"] / 1000.0 * (BASE["nex"] * BASE["rex"] * 2.0 - BASE["nin"] * BASE["rin"] * BASE["win"])
    ctl["(b) free membrane mean"] = abs(rf["end"]["meanV"] - want) <= 0.02 * abs(want)
    # (c) input rates in S1
    e = runs["S1"]["end"]
    rate_ex = e["in_ex"] / (BASE["nex"] * e["t"])
    rate_in = e["in_in"] / (BASE["nin"] * e["t"])
    ctl["(c) input rates within 1% of 10 Hz"] = abs(rate_ex - 10) <= 0.1 and abs(rate_in - 10) <= 0.1
    # (d) the window and the lower bound
    q = dict(BASE)
    want_F = {-5.0: -0.005 * math.exp(-7 / 20), 0.0: -0.005 * math.exp(-2 / 20), 1.0: -0.005 * math.exp(-1 / 20),
              2.0: -0.005, 2.1: 0.006 * math.exp(-0.1 / 20), 10.0: 0.006 * math.exp(-8 / 20)}
    ok_d = all(abs(F(x, q) - v) < 1e-15 for x, v in want_F.items())
    ok_d &= all(min(r["w"]) >= 0 and all(c["mean"] >= 0 for c in r["cp"]) for r in runs.values())
    ctl["(d) the window's values and the lower bound"] = ok_d

    def show(st):
        if st is None:
            return "no full windows (runaway)"
        L = st["last"]
        return (f"mean {L['mean']:.3f} mV, SD {L['sd']:.3f}, skew {L['skew']:.2f}, at 0 {100 * L['zero']:.1f}%, "
                f"rate {L['rate']:.2f} Hz; change {100 * st['change']['mean']:.2f}/{100 * st['change']['sd']:.2f}/"
                f"{100 * st['change']['rate']:.2f}%")

    ru = runs["U"]
    if ru["runaway"] is not None:
        u_text = f"runaway at {ru['runaway']:.0f} s (last mean {ru['cp'][-1]['mean']:.2f} mV, max {ru['cp'][-1]['max']:.1f})"
    else:
        u_text = "no runaway: " + show(u)
    ds = {}
    for name in ("d1", "S1", "d4"):
        ok, st = settled(runs[name])
        ds[name] = st["last"] if st else None
    met = sum(cond.values())
    s1L = s1["last"] if s1 else None
    r13 = None
    if s1L:
        r13 = (BASE["nex"] * BASE["rex"] * BASE["tau_s"] / 1000 * s1L["mean"]
               - BASE["nin"] * BASE["rin"] * BASE["tau_s"] / 1000 * BASE["win"]
               - 0.5 * (BASE["vth"] - BASE["vr"])) / ((BASE["vth"] - BASE["vr"]) * BASE["tau_m"] / 1000)
    out = {
        "s1": show(s1),
        "s2": show(s2),
        "unshifted": u_text,
        "delays": "d = 1, 2, 4 ms: " + "; ".join(
            (f"mean {v['mean']:.3f} SD {v['sd']:.3f}" if v else "not settled") for v in ds.values()),
        "rate_eq13": f"S1 rate {s1L['rate']:.2f} Hz against the paper's equation 13, {r13:.2f} Hz" if s1L else "n/a",
        "conditions_met": met, "conditions_total": len(cond), "test_passed": int(met == len(cond)),
        "controls_passed": sum(ctl.values()), "controls_total": len(ctl),
    }
    for k, v in out.items():
        if isinstance(v, str) and len(v) > 200:
            raise AssertionError(f"{k}: longer than 200 characters: {v}")
    detail = {"test": TEST, "conditions": cond, "controls": ctl, "replay": detail_a, "free_meanV": rf["end"]["meanV"],
              "free_meanV_expected": want, "input_rates": [rate_ex, rate_in],
              "runs": {k: {"end": r["end"], "runaway": r["runaway"], "cp": r["cp"]} for k, r in runs.items()},
              "settle": {"S1": s1, "S2": s2, "U": u}}
    return out, detail


def run(seed, results="results"):
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        raise Refused("the seed must be 64 hex characters")
    if shutil.which("gcc") is None:
        raise Refused("no gcc in this image")
    os.makedirs(results, exist_ok=True)
    # the program is built and run inside the results directory: the sandbox's /tmp may not allow execution
    work = tempfile.mkdtemp(prefix="work-", dir=results)
    try:
        out, detail = assess(seed, work)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    with open(os.path.join(results, "outputs.json"), "w", encoding="ascii") as fh:
        json.dump(out, fh, indent=2, sort_keys=True)
        fh.write("\n")
    with open(os.path.join(results, "detail.json"), "w", encoding="utf-8") as fh:
        json.dump(detail, fh, indent=1, sort_keys=True)
        fh.write("\n")
    return out, detail


def main():
    seed = os.environ.get("ECDYSIS_SEED", "")
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        sys.exit("ECDYSIS_SEED must be the 64-hex seed the archive issued")
    try:
        out, _ = run(seed)
    except Refused as e:
        sys.exit(f"babadi: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
