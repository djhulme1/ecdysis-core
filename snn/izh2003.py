#!/usr/bin/env python3
"""Izhikevich's simple model of spiking neurons: the firing types of Section III and Fig. 2 under a step of current.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:a10b2fcc65619834) is from Izhikevich,
"Simple Model of Spiking Neurons" (IEEE Transactions on Neural Networks 14(6), 1569-1572, 2003): "A model is presented
that reproduces spiking and bursting behavior of known types of cortical neurons."

Its registered test: refuted if the model as the paper states it (equations (1)-(3), Euler steps of 0.1 ms), with
the parameters it gives for RS, IB, CH, FS and LTS, given a 300 ms step of dc current I = 10 from rest, does not do
what Section III says: RS and LTS fire single spikes whose interval grows at least 1.3-fold, LTS faster than RS and
from a lower threshold current; IB an initial burst, then at least three single spikes; CH at least three bursts; FS
single spikes, adapting least of the three, at twice RS's rate or more. A burst: spikes joined by intervals below a
threefold gap in the sorted intervals.

Standard library only. The inputs are the claim's data of record from the author's page: the paper (spikes.pdf), its
summary figure (izhik.pdf) and its MATLAB program (net.m), each checked against its SHA-256 and size. The PDFs are
read for their hashes only; the parameters below were transcribed from the paper before this file was written, and
anyone can compare them with it. net.m is read as text (its statements must be the ones transcribed here) and
nothing in it is run. Every rule below was fixed before any neuron was simulated.

1. The model, equations (1)-(3): v' = 0.04 v^2 + 5 v + 140 - u + I, u' = a (b v - u); when v >= 30 mV, v <- c and
   u <- u + d. Integrated as net.m does, at the step of the test: at each step, a neuron at or above 30 mV is
   recorded as firing at that time and reset; then v <- v + dt (0.04 v^2 + 5 v + 140 - u + I), and then
   u <- u + dt a (b v - u) with the new v. dt = 0.1 ms.
2. The types (Section III, with the typical values a = 0.02, b = 0.2, c = -65, d = 2 it states, and Fig. 2):
   RS (0.02, 0.2, -65, 8), IB (0.02, 0.2, -55, 4), CH (0.02, 0.2, -50, 2), FS (0.1, 0.2, -65, 2) and
   LTS (0.02, 0.25, -65, 2); beside the test, TC (0.02, 0.25, -65, 0.05) and RZ (0.1, 0.26, -65, 2).
3. The protocol. From rest, the stable equilibrium at I = 0 (the lower root of 0.04 v^2 + (5 - b) v + 140 = 0,
   u = b v), 50 ms at I = 0, then I = 10 for 300 ms. The spikes counted are those recorded during the step.
4. Spike trains. The intervals between consecutive spikes; a train is bursting if, among its intervals sorted, some
   consecutive pair differs at least threefold (the largest such ratio is its gap), and then its short intervals are
   those at or below the lower side of the largest gap, a burst being a maximal run of spikes joined by short
   intervals; otherwise it fires single spikes. Adaptation is the last interval over the first; the rate, the spikes
   per second of the step. The threshold current is the least I (bisection on [0, 10] to 0.005) at which a 300 ms
   step from rest gives a spike.
5. The test's five conditions: RS fires single spikes, at least 4, adapting at least 1.3-fold; IB is bursting with one
   burst, from its first spike, then at least 3 single spikes; CH has at least 3 bursts; FS fires single spikes, at
   least 4, adapting less than RS and less than LTS, at twice RS's rate or more; LTS fires single spikes, at least 4,
   adapting at least 1.3-fold, at a higher rate than RS and from a lower threshold current. test_passed is 1 if all
   five hold.
6. Beside the test, none of it counted: the five verdicts at dt = 0.05 ms and in net.m's own scheme (1 ms steps, v
   advanced by two half-millisecond steps); RS's rate at I = 5, 10, 15 and 20 ("Increasing the strength of the
   injected dc-current increases the interspike frequency"); TC from rest under I = 10, and after 200 ms at I = -30
   (near the -87 mV of Fig. 2) released to 0, its spikes in the 100 ms after; RZ after a 1 ms pulse of I = 20 from
   rest, the swings of v about rest; and net.m's network as it prints it (800 excitatory and 200 inhibitory
   neurons, 1,000 ms, its random draws taken from Python's Mersenne Twister seeded by SHA-256(seed || "izh2003/net")),
   its mean rate ("mean firing rates around 8 Hz"), the median coefficient of variation of the excitatory
   intervals, and the two largest peaks between 5 and 60 Hz of the spectrum of its spike count per millisecond (its
   "alpha and gamma frequency range (10 and 40 Hz, respectively)").

Controls (controls_passed counts those that behave as stated): the train analysis on trains built here (regular,
adapting, an initial burst then single spikes, repeated bursts) finds what each is; each of the five types is silent
for 350 ms at I = 0 from rest and fires during the step; the five verdicts are the same at dt = 0.05 ms; RS and LTS
fire at their threshold current + 0.01 and not at - 0.01; and every rest state is an equilibrium (v' and u' within
1e-9 of zero) that 50 ms at I = 0 leaves within 1e-6 mV.

What it cannot check: Fig. 1's comparison with recordings from rat motor cortex (the data were shared privately), the
speed claims (tens of thousands of neurons in real time on a desktop PC of 2003) and the types' fit to biological
cells beyond the paper's own words.

Writes results/outputs.json (the values a receipt carries) and results/detail.json (every value computed).
Run with: python3 snn/izh2003.py
"""

import cmath
import hashlib
import json
import math
import os
import random
import re
import sys

INPUTS = (("spikes.pdf", "896710f3a25d3f5307a57d4cf13992514c87cd646b2e509ede6285f8724eb21d", 413309),
          ("izhik.pdf", "179ecf9c9d816e52f6dd24d37d0f24e70415cc55ae9b0bf1bc83dc21112b9a63", 446889),
          ("net.m", "0ca5e62065152d36f8b66a8d474139767a2084fd1454752aaf4b25c7f23d99d2", 974))
TYPES = {"RS": (0.02, 0.2, -65.0, 8.0), "IB": (0.02, 0.2, -55.0, 4.0), "CH": (0.02, 0.2, -50.0, 2.0),
         "FS": (0.1, 0.2, -65.0, 2.0), "LTS": (0.02, 0.25, -65.0, 2.0)}
BESIDE = {"TC": (0.02, 0.25, -65.0, 0.05), "RZ": (0.1, 0.26, -65.0, 2.0)}
DT = 0.1
SETTLE, STEP, I_STEP = 50.0, 300.0, 10.0
GAP, ADAPT, FS_RATE, MIN_SPIKES, MIN_SINGLES, MIN_BURSTS = 3.0, 1.3, 2.0, 4, 3, 3
NET_LINES = (
    "Ne=800;",
    "Ni=200;",
    "re=rand(Ne,1);",
    "ri=rand(Ni,1);",
    "a=[0.02*ones(Ne,1); 0.02+0.08*ri];",
    "b=[0.2*ones(Ne,1); 0.25-0.05*ri];",
    "c=[-65+15*re.^2; -65*ones(Ni,1)];",
    "d=[8-6*re.^2; 2*ones(Ni,1)];",
    "S=[0.5*rand(Ne+Ni,Ne), -rand(Ne+Ni,Ni)];",
    "v=-65*ones(Ne+Ni,1);",
    "u=b.*v;",
    "for t=1:1000",
    "I=[5*randn(Ne,1);2*randn(Ni,1)];",
    "fired=find(v>=30);",
    "v(fired)=c(fired);",
    "u(fired)=u(fired)+d(fired);",
    "I=I+sum(S(:,fired),2);",
    "v=v+0.5*(0.04*v.^2+5*v+140-u+I);",
    "u=u+a.*(b.*v-u);",
)
OUTPUTS = ("rs", "ib", "ch", "fs", "lts", "rs_adaptation", "fs_rate", "ch_bursts", "integrators", "rs_fi", "tc", "rz",
           "network", "net_rate", "conditions_met", "conditions_total", "test_passed", "controls_passed",
           "controls_total")
LIMIT = 200


class Refused(Exception):
    pass


# ---------------------------------------------------------------- the data of record

def read_inputs(inputs):
    data = {}
    for name, sha, size in INPUTS:
        with open(os.path.join(inputs, name), "rb") as fh:
            raw = fh.read()
        got = hashlib.sha256(raw).hexdigest()
        if got != sha or len(raw) != size:
            raise Refused(f"{name}: sha256 {got} ({len(raw)} bytes), not the registered {sha} ({size})")
        data[name] = raw
    return data


def net_code(raw):
    """net.m's lines of code, comments dropped and every space removed."""
    try:
        text = raw.decode("ascii")
    except UnicodeDecodeError as e:
        raise Refused(f"net.m is not ASCII: {e}")
    lines = ["".join(line.split("%", 1)[0].split()) for line in text.replace("\r\n", "\n").split("\n")]
    return [x for x in lines if x]


def check_net(raw):
    """Every statement transcribed in NET_LINES appears in net.m's code; the number of its lines of code."""
    lines = net_code(raw)
    code = "".join(lines)
    missing = [s for s in NET_LINES if "".join(s.split()) not in code]
    if missing:
        raise Refused(f"net.m does not state {missing[0]!r}")
    return len(lines)


# ---------------------------------------------------------------- the model

def rest(b):
    disc = (5.0 - b) ** 2 - 4 * 0.04 * 140.0
    if disc < 0:
        raise ValueError("no equilibrium at I = 0")
    v = (-(5.0 - b) - math.sqrt(disc)) / (2 * 0.04)
    return v, b * v


def step_current(amplitude, start=SETTLE, length=STEP):
    return lambda t: amplitude if start <= t < start + length else 0.0


def simulate(p, current, t_end, dt=DT, scheme="euler", state=None, trace=False):
    """Spike times (ms) of one neuron; scheme 'euler' (rule 1) or 'netm' (1 ms, v by two half steps)."""
    a, b, c, d = p
    v, u = state if state else rest(b)
    spikes, vs = [], []
    if scheme == "netm":
        dt = 1.0
    n = int(round(t_end / dt))
    for k in range(n):
        t = k * dt
        if v >= 30.0:
            spikes.append(t)
            v, u = c, u + d
        i = current(t)
        if scheme == "netm":
            v += 0.5 * (0.04 * v * v + 5 * v + 140 - u + i)
            v += 0.5 * (0.04 * v * v + 5 * v + 140 - u + i)
            u += a * (b * v - u)
        else:
            v += dt * (0.04 * v * v + 5 * v + 140 - u + i)
            u += dt * a * (b * v - u)
        if trace:
            vs.append(v)
    return (spikes, vs, (v, u)) if trace else spikes


def in_step(spikes, start=SETTLE, length=STEP):
    return [s for s in spikes if start <= s < start + length]


def intervals(spikes):
    return [y - x for x, y in zip(spikes, spikes[1:])]


def structure(spikes):
    d = intervals(spikes)
    out = {"spikes": len(spikes), "intervals": d, "gap": 1.0, "bursting": False, "bursts": []}
    if len(d) < 2:
        return out
    s = sorted(d)
    ratios = [(s[i + 1] / s[i], s[i]) for i in range(len(s) - 1) if s[i] > 0]
    ratio, cut = max(ratios) if ratios else (1.0, None)
    out["gap"] = ratio
    if ratio < GAP:
        return out
    short = [x <= cut for x in d]
    bursts, i = [], 0
    while i < len(d):
        if short[i]:
            j = i
            while j < len(d) and short[j]:
                j += 1
            bursts.append((i, j - i + 1))
            i = j
        else:
            i += 1
    out.update(bursting=True, bursts=bursts, cut=cut)
    return out


def adaptation(spikes):
    d = intervals(spikes)
    return d[-1] / d[0] if len(d) >= 1 and d[0] > 0 else None


def rate(spikes, length=STEP):
    return len(spikes) / (length / 1000.0)


def fires(p, amplitude, dt=DT, scheme="euler"):
    return len(in_step(simulate(p, step_current(amplitude), SETTLE + STEP, dt, scheme))) > 0


def threshold(p, dt=DT, scheme="euler", lo=0.0, hi=I_STEP, tol=0.005):
    if fires(p, lo, dt, scheme) or not fires(p, hi, dt, scheme):
        return None
    while hi - lo > tol:
        mid = (lo + hi) / 2
        if fires(p, mid, dt, scheme):
            hi = mid
        else:
            lo = mid
    return hi


def analyse(dt=DT, scheme="euler"):
    found = {}
    for name, p in TYPES.items():
        sp = in_step(simulate(p, step_current(I_STEP), SETTLE + STEP, dt, scheme))
        st = structure(sp)
        found[name] = {"spikes": sp, "structure": st, "adaptation": adaptation(sp), "rate": rate(sp)}
    return found


def single(f):
    return (not f["structure"]["bursting"]) and f["structure"]["spikes"] >= MIN_SPIKES


def conditions(found, thresholds):
    rs, ib, ch, fs, lts = (found[k] for k in ("RS", "IB", "CH", "FS", "LTS"))
    ib_b = ib["structure"]["bursts"]
    ib_ok = (ib["structure"]["bursting"] and len(ib_b) == 1 and ib_b[0][0] == 0
             and ib["structure"]["spikes"] - ib_b[0][1] >= MIN_SINGLES)
    rs_ok = single(rs) and rs["adaptation"] is not None and rs["adaptation"] >= ADAPT
    fs_ok = (single(fs) and fs["adaptation"] is not None and rs["adaptation"] is not None
             and lts["adaptation"] is not None and fs["adaptation"] < rs["adaptation"]
             and fs["adaptation"] < lts["adaptation"] and fs["rate"] >= FS_RATE * rs["rate"])
    th_rs, th_lts = thresholds.get("RS"), thresholds.get("LTS")
    lts_ok = (single(lts) and lts["adaptation"] is not None and lts["adaptation"] >= ADAPT
              and lts["rate"] > rs["rate"] and th_rs is not None and th_lts is not None and th_lts < th_rs)
    return {
        "RS: single spikes, the interval growing at least 1.3-fold": rs_ok,
        "IB: an initial burst, then at least 3 single spikes": ib_ok,
        "CH: at least 3 bursts": ch["structure"]["bursting"] and len(ch["structure"]["bursts"]) >= MIN_BURSTS,
        "FS: single spikes, adapting least, at twice RS's rate or more": fs_ok,
        "LTS: single spikes adapting at least 1.3-fold, faster than RS, from a lower threshold": lts_ok,
    }


# ---------------------------------------------------------------- the network of net.m

def network(seed, t_end=1000):
    rng = random.Random(int.from_bytes(hashlib.sha256(f"{seed}|izh2003/net".encode()).digest(), "big"))
    ne, ni = 800, 200
    n = ne + ni
    re_ = [rng.random() for _ in range(ne)]
    ri = [rng.random() for _ in range(ni)]
    a = [0.02] * ne + [0.02 + 0.08 * r for r in ri]
    b = [0.2] * ne + [0.25 - 0.05 * r for r in ri]
    c = [-65 + 15 * r * r for r in re_] + [-65.0] * ni
    d = [8 - 6 * r * r for r in re_] + [2.0] * ni
    # S(i, j): column j is what neuron j's firing adds to every neuron i
    cols = [[0.5 * rng.random() for _ in range(n)] for _ in range(ne)] + \
           [[-rng.random() for _ in range(n)] for _ in range(ni)]
    v = [-65.0] * n
    u = [b[i] * v[i] for i in range(n)]
    firings = []
    for t in range(1, t_end + 1):
        current = [5 * rng.gauss(0, 1) for _ in range(ne)] + [2 * rng.gauss(0, 1) for _ in range(ni)]
        fired = [i for i in range(n) if v[i] >= 30]
        for i in fired:
            firings.append((t, i))
            v[i] = c[i]
            u[i] += d[i]
        for j in fired:
            col = cols[j]
            for i in range(n):
                current[i] += col[i]
        for i in range(n):
            vi, ui, ii = v[i], u[i], current[i]
            vi += 0.5 * (0.04 * vi * vi + 5 * vi + 140 - ui + ii)
            vi += 0.5 * (0.04 * vi * vi + 5 * vi + 140 - ui + ii)
            v[i] = vi
            u[i] = ui + a[i] * (b[i] * vi - ui)
    return firings, n, ne


def spectrum_peaks(counts, lo=5, hi=60, top=2):
    n = len(counts)
    mean = sum(counts) / n
    x = [c - mean for c in counts]
    power = {}
    for f in range(lo, hi + 1):
        z = sum(x[k] * cmath.exp(-2j * math.pi * f * k / n) for k in range(n))
        power[f] = abs(z) ** 2
    peaks = [f for f in range(lo + 1, hi) if power[f] >= power[f - 1] and power[f] >= power[f + 1]]
    peaks.sort(key=lambda f: -power[f])
    return peaks[:top], power


def network_summary(seed):
    firings, n, ne = network(seed)
    t_end = 1000
    rate_all = len(firings) / n / (t_end / 1000.0)
    by = {}
    for t, i in firings:
        by.setdefault(i, []).append(t)
    cvs = []
    for i in range(ne):
        d = intervals(by.get(i, []))
        if len(d) >= 3:
            m = sum(d) / len(d)
            sd = math.sqrt(sum((x - m) ** 2 for x in d) / (len(d) - 1))
            cvs.append(sd / m)
    cvs.sort()
    median_cv = cvs[len(cvs) // 2] if cvs else None
    counts = [0] * t_end
    for t, _ in firings:
        counts[t - 1] += 1
    peaks, _ = spectrum_peaks(counts)
    return {"rate": rate_all, "median_cv": median_cv, "cv_neurons": len(cvs), "peaks": peaks,
            "spikes": len(firings)}


# ---------------------------------------------------------------- the run

def describe(name, f):
    st = f["structure"]
    if st["bursting"]:
        sizes = [k for _, k in st["bursts"]]
        return (f"{name}: {st['spikes']} spikes, {len(sizes)} burst(s) of {', '.join(map(str, sizes[:6]))} (gap "
                f"x{st['gap']:.1f}), {st['spikes'] - sum(sizes)} single")
    ad = f["adaptation"]
    d = st["intervals"]
    return (f"{name}: {st['spikes']} single spikes (gap x{st['gap']:.2f}), {f['rate']:.1f} Hz, interval "
            f"{d[0]:.1f} to {d[-1]:.1f} ms (x{ad:.2f})" if d else f"{name}: {st['spikes']} spikes")


def verdicts(found, thresholds):
    return [int(v) for v in conditions(found, thresholds).values()]


def run(seed, inputs="inputs", results="results"):
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        raise Refused("the seed must be 64 hex characters")
    data = read_inputs(inputs)
    net_count = check_net(data["net.m"])

    found = analyse()
    thresholds = {k: threshold(TYPES[k]) for k in ("RS", "LTS")}
    cond = conditions(found, thresholds)

    # beside: other integrators
    fine = analyse(dt=0.05)
    th_fine = {k: threshold(TYPES[k], dt=0.05) for k in ("RS", "LTS")}
    netm = analyse(scheme="netm")
    th_netm = {k: threshold(TYPES[k], scheme="netm") for k in ("RS", "LTS")}
    v_main, v_fine, v_netm = verdicts(found, thresholds), verdicts(fine, th_fine), verdicts(netm, th_netm)
    # beside: RS's f-I
    fi = {amp: rate(in_step(simulate(TYPES["RS"], step_current(amp), SETTLE + STEP))) for amp in (5, 10, 15, 20)}
    # beside: TC and RZ
    tc = BESIDE["TC"]
    tc_tonic = structure(in_step(simulate(tc, step_current(I_STEP), SETTLE + STEP)))
    hyper = lambda t: -30.0 if SETTLE <= t < SETTLE + 200 else 0.0
    sp, vs, _ = simulate(tc, hyper, SETTLE + 300, trace=True)
    v_hyper = vs[int(round((SETTLE + 199) / DT))]
    rebound = [s for s in sp if SETTLE + 200 <= s < SETTLE + 300]
    rz = BESIDE["RZ"]
    v0, _ = rest(rz[1])
    pulse = lambda t: 20.0 if SETTLE <= t < SETTLE + 1 else 0.0
    sp_rz, vs_rz, _ = simulate(rz, pulse, SETTLE + 200, trace=True)
    after = vs_rz[int(round((SETTLE + 1) / DT)):]
    swings = sum(1 for x, y in zip(after, after[1:]) if (x - v0) * (y - v0) < 0)
    # beside: the network
    net = network_summary(seed)

    # controls
    ctl, ctl_detail = {}, {}
    trains = {"regular": [20.0 * k for k in range(10)],
              "adapting": [0, 10, 22, 37, 56, 80, 110],
              "burst then single": [0, 3, 6, 36, 66, 96, 126],
              "chattering": [0, 3, 6, 31, 34, 37, 62, 65, 68, 93, 96]}
    got = {k: structure(v) for k, v in trains.items()}
    ctl["the train analysis: regular and adapting single, one initial burst, repeated bursts"] = (
        not got["regular"]["bursting"] and not got["adapting"]["bursting"]
        and abs(adaptation(trains["adapting"]) - 3.0) < 1e-12
        and got["burst then single"]["bursts"] == [(0, 3)] and len(got["chattering"]["bursts"]) == 4)
    silent = all(not simulate(p, lambda t: 0.0, SETTLE + STEP) for p in TYPES.values())
    ctl["each type silent at I = 0 for 350 ms from rest, and firing in the step"] = silent and all(
        f["structure"]["spikes"] > 0 for f in found.values())
    ctl["the five verdicts the same at dt = 0.05 ms"] = v_main == v_fine
    brackets = all(th is not None and fires(TYPES[k], th + 0.01) and not fires(TYPES[k], th - 0.01)
                   for k, th in thresholds.items())
    ctl["RS and LTS fire at threshold + 0.01 and not at threshold - 0.01"] = brackets
    eq_ok = True
    for p in list(TYPES.values()) + list(BESIDE.values()):
        a, b, c, d = p
        v, u = rest(b)
        if abs(0.04 * v * v + 5 * v + 140 - u) > 1e-9 or abs(a * (b * v - u)) > 1e-9:
            eq_ok = False
        _, _, (v1, u1) = simulate(p, lambda t: 0.0, SETTLE, trace=True)
        if abs(v1 - v) > 1e-6:
            eq_ok = False
    ctl["every rest state an equilibrium, unmoved by 50 ms at I = 0"] = eq_ok
    ctl_detail["trains"] = {k: {"bursting": g["bursting"], "bursts": g["bursts"], "gap": g["gap"]}
                            for k, g in got.items()}

    rs, fs, ch = found["RS"], found["FS"], found["CH"]

    def short(v):
        return ", ".join(f"{x:.1f}" for x in v)

    values = {
        "rs": describe("RS", rs),
        "ib": describe("IB", found["IB"]),
        "ch": describe("CH", ch),
        "fs": describe("FS", fs) + f"; RS {rs['rate']:.1f} Hz",
        "lts": describe("LTS", found["LTS"]) + (f"; threshold {thresholds['LTS']:.2f} against RS "
                                                f"{thresholds['RS']:.2f}" if None not in thresholds.values() else ""),
        "rs_adaptation": round(rs["adaptation"], 6) if rs["adaptation"] is not None else -1,
        "fs_rate": round(fs["rate"], 6),
        "ch_bursts": len(ch["structure"]["bursts"]),
        "integrators": (f"verdicts at dt 0.1: {''.join(map(str, v_main))}; at 0.05: {''.join(map(str, v_fine))}; in "
                        f"net.m's 1 ms scheme: {''.join(map(str, v_netm))} (RS, IB, CH, FS, LTS)"),
        "rs_fi": "RS's rate at I = 5, 10, 15, 20: " + ", ".join(f"{fi[k]:.1f}" for k in (5, 10, 15, 20)) + " Hz",
        "tc": (f"TC: from rest at I = 10, {tc_tonic['spikes']} spikes "
               f"({'bursting' if tc_tonic['bursting'] else 'single'}); held at {v_hyper:.1f} mV by I = -30 then "
               f"released, {len(rebound)} spikes in 100 ms, intervals "
               f"{short(intervals(rebound)[:4])}"),
        "rz": f"RZ: after a 1 ms pulse of 20, {len(sp_rz)} spikes and {swings} swings of v about its rest {v0:.2f} mV",
        "network": (f"net.m ({net_count} lines of code), 1000 neurons, 1000 ms: {net['spikes']} spikes, "
                    f"{net['rate']:.2f} Hz each; median CV of E intervals {net['median_cv']:.2f}; spectral peaks "
                    f"{', '.join(map(str, net['peaks']))} Hz"),
        "net_rate": round(net["rate"], 6),
        "conditions_met": sum(cond.values()), "conditions_total": len(cond), "test_passed": int(all(cond.values())),
        "controls_passed": sum(ctl.values()), "controls_total": len(ctl),
    }
    out = {k: values[k] for k in OUTPUTS}
    for key, v in out.items():
        if isinstance(v, str) and len(v) > LIMIT:
            raise AssertionError(f"{key}: longer than {LIMIT} characters: {v}")
    detail = {"inputs": [{"name": n_, "sha256": s_, "bytes": b_} for n_, s_, b_ in INPUTS], "types": TYPES,
              "beside_types": BESIDE, "conditions": cond, "controls": ctl, "control_detail": ctl_detail,
              "found": {k: {"spikes": f["spikes"], "intervals": f["structure"]["intervals"],
                            "gap": f["structure"]["gap"], "bursts": f["structure"]["bursts"],
                            "adaptation": f["adaptation"], "rate": f["rate"]} for k, f in found.items()},
              "thresholds": thresholds, "thresholds_dt005": th_fine, "thresholds_netm": th_netm,
              "verdicts": {"dt0.1": v_main, "dt0.05": v_fine, "netm": v_netm}, "rs_fi": fi,
              "tc": {"tonic": {"spikes": tc_tonic["spikes"], "bursting": tc_tonic["bursting"]},
                     "v_hyperpolarised": v_hyper, "rebound": rebound},
              "rz": {"rest": v0, "spikes": sp_rz, "swings": swings}, "network": net}
    os.makedirs(results, exist_ok=True)
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
    try:
        out, _ = run(seed)
    except Refused as e:
        sys.exit(f"izh2003: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
