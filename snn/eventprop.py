#!/usr/bin/env python3
"""EventProp's exact gradients for spiking networks: Wunderlich & Pehle's adjoint network, as their paper prints it,
against central differences of the loss, in leaky integrate-and-fire networks drawn from the seed.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:07ec2c59943734b6) is from Wunderlich and
Pehle, "Event-based backpropagation can compute exact gradients for spiking neural networks", Scientific Reports 11,
12829 (2021; arXiv:2009.08378v3, the same text; CC BY): "This algorithm, EventProp, backpropagates errors at spike times
in order to compute the exact gradient in an event-based, temporally and spatially sparse fashion."

Its registered test is TEST below. There are no inputs: the networks are drawn from ECDYSIS_SEED and simulated exactly.
The paper was read in its arXiv source (v3, 31 May 2021, which the published version follows): Table 1 (the network),
Table 2 (the adjoint network), Eq. 2 (the gradient), Algorithm 1, Fig. 3 (two neurons, the gradients "match the
gradients computed via central differences ... up to a relative deviation of less than 1e-7"), the Methods' derivation
and the table of simulation parameters. The authors released no code. Every rule below was fixed before EventProp was
compared with central differences on any drawn network; the tests use other inputs (single neurons, a chain of two,
closed forms).

1. The network (Table 1): N leaky integrate-and-fire neurons, tau_m dV/dt = -V + I and tau_s dI/dt = -I between spikes,
   V(0) = I(0) = 0; a neuron n spikes when V_n reaches theta from below (dV_n/dt != 0, the paper's transition
   condition), V_n is reset to 0 and the currents jump by W e_n (I_m += W[m][n]); W has a zero diagonal. Fixed input
   spike trains add W_in e_i likewise. tau_m = 20 ms, tau_s = 5 ms and theta = 1, the paper's simulation parameters.
   Between events V and I are exact (V = A e^(-u/tau_m) + B e^(-u/tau_s)); a spike time is the first upward crossing
   of theta, bracketed on the interval's monotone pieces (V has at most one critical point between events) and
   bisected to machine precision, then polished by Newton steps (the paper: "root-bracketing ... using exact
   integration of the membrane potential").
2. EventProp (Table 2, Eq. 2, Algorithm 1). In reverse time from lambda_V(T) = lambda_I(T) = 0, between events
   tau_m lambda_V' = -lambda_V - dl_V/dV and tau_s lambda_I' = -lambda_I + lambda_V (' = -d/dt), solved exactly (for a
   loss c V^2 / 2 the forcing c V(t) is a sum of exponentials and the solution is closed); at the k-th spike, of neuron
   n, (lambda_V^-)_n = (lambda_V^+)_n + [theta (lambda_V^+)_n + (W^T (lambda_V^+ - lambda_I))_n + dl_p/dt_k
   + l_V^- - l_V^+] / (tau_m (dV/dt^-)_n), with tau_m (dV/dt^-)_n = (I^-)_n - theta; and dL/dw_ji = -tau_s times the sum
   of (lambda_I)_j over the spikes from i, inputs included (the Methods: "Fixed Input Spikes"). A loss g V_r(t_m), the
   paper's Dirac case, makes lambda_V of r jump by -g/tau_m at t_m; the maximum of a readout's voltage is that case at
   the time of the maximum (the paper's MNIST loss, "terms containing the distributional derivative of delta are always
   zero").
3. Central differences: the fourth-order central stencil (f(w - 2h) - 8 f(w - h) + 8 f(w + h) - f(w + 2h)) / (12 h),
   h = 1e-5, of the loss recomputed by rule 1's simulation, for every weight the scenario's network has.
4. Scenarios, three networks each, drawn from ECDYSIS_SEED, T = 100 ms (the figure gives no duration):
   A. Fig. 3: an upper neuron receiving 100 independent Poisson trains at 200 Hz through weights uniform on [0, 0.04]
      (the figure: "randomly initialized"), connected to a lower neuron through w uniform on [3, 6]; loss the sum of
      the lower neuron's spike times; the 100 input weights and w.
   B1. Recurrent: 6 neurons, weights uniform on [-0.5, 0.5] off the diagonal, 30 Poisson inputs at 100 Hz to every
      neuron through weights uniform on [0, 0.2]; loss the sum of t_k^2 / T over the spikes of neurons 0 and 1; every
      recurrent and input weight (210).
   B2. The same networks with a voltage loss on the firing neurons, the integral over [0, T] of sum_n V_n^2 / (2 T).
   C1. Feed-forward: 20 Poisson inputs at 100 Hz, 5 hidden neurons (input weights uniform on [0, 0.4]), one non-firing
      readout (hidden-to-readout weights uniform on [0, 1]); loss V_r(25) + V_r(50) + V_r(75) (ms); the 100 input and
      5 readout weights.
   C2. The same draws with loss max_t V_r(t) over [0, T].
   A draw is kept only if it is non-critical, so that no step of the stencil crosses a point where a spike appears,
   vanishes or moves past another event: every spike with (I^-)_n - theta >= 0.02; every local maximum of a firing
   neuron's V that is not a crossing (inside an interval, at an event where V turns down, or at T while rising) at
   least 0.01 below theta; every spike at least 1e-4 ms from every other event and 0.01 ms from T; for C2, the
   readout's maximum inside an interval, at least 1e-4 ms from its ends and above every other local maximum by 0.01;
   the spikes the loss needs present (A: the lower neuron fires; B: neuron 0 or 1 fires; C: a hidden neuron fires);
   and no step of the stencil changing the order of events (spikes, inputs and observations) or, for C2, the
   interval of the maximum. Otherwise it is drawn again, up to 50 times. B1 and B2 draw the same networks; C1 and C2
   draw from the same stream.
5. The test's condition, one per scenario: for every weight of every draw, |g_EventProp - g_FD| <= 1e-5 max(|g_FD|,
   1e-3 G), G the draw's largest |g_FD|. Five conditions; test_passed is 1 if all hold.
6. Beside the test: the largest relative deviation in each scenario (the paper's figure: below 1e-7); the weights, the
   spikes and the redraws; and planted faults, EventProp with one term of the jump changed, each of which must break
   rule 5's bound (in some draw) in every scenario where the term acts: the theta lambda_V^+ term dropped and W in
   place of W^T (the derivation's intermediate line writes w_(n(k)m), its final jump w_(mn)), all five; the
   l_V^- - l_V^+ term dropped (B2).
7. Controls, known answers: a single neuron and one input spike, its spike time and dt/dw from the implicit function
   theorem (the paper's dt/dw = -(dV/dw)/(dV/dt)) against the simulation and EventProp; a readout and one input spike,
   dL/dw = kappa (e^(-D/tau_m) - e^(-D/tau_s)), kappa = tau_s / (tau_m - tau_s), at a fixed time and at the maximum,
   against EventProp; the event-driven simulation against a fine-step integration of the same network (spike times
   within 1e-6 ms); the closed forced adjoint against a fine-step integration of its equations; and the stencil on a
   function whose derivative is known.

What it cannot check: the paper's training results (Yin-Yang 98.1%, MNIST 97.6%), which need its datasets and
hyperparameter searches; and gradients at critical parameters, where the paper says they diverge.

Writes results/outputs.json (the values a receipt carries) and results/detail.json (every value computed).
Standard library only (the pinned python image). Run with: python3 snn/eventprop.py
"""

import hashlib
import json
import math
import os
import random
import re
import sys

TEST = (
    "Refuted if EventProp as the paper prints it (Table 1's LIF network; Table 2's adjoint dynamics and jumps; Eq. 2's "
    "gradient) differs from 4th-order central differences of the loss by over 1e-5 relative (floor 1e-3 of the "
    "draw's largest) for any weight, in networks drawn from the seed with every spike non-critical: Fig. 3's pair (100 "
    "Poisson inputs at 200 Hz; loss the sum of the lower neuron's spike times); recurrent networks with a spike-time "
    "loss and with a voltage loss on firing neurons; and a readout's voltage at fixed times and at its maximum."
)
TAU_M, TAU_S, THETA, T_END = 20.0, 5.0, 1.0, 100.0
ALPHA, BETA = 1.0 / TAU_M, 1.0 / TAU_S
KAPPA = TAU_S / (TAU_M - TAU_S)
H_FD = 1e-5
TOL, FLOOR = 1e-5, 1e-3
DRAWS, MAX_ATTEMPTS = 3, 50
MARGIN_DV, MARGIN_V, MARGIN_EVENT, MARGIN_END = 0.02, 0.01, 1e-4, 0.01
SCENARIOS = ("A", "B1", "B2", "C1", "C2")
FAMILY = {"A": "A", "B1": "B", "B2": "B", "C1": "C", "C2": "C"}
FAULTS = {"no_theta": SCENARIOS, "transposed": SCENARIOS, "no_lv_jump": ("B2",)}
VARIANTS = ("paper",) + tuple(FAULTS)
OUTPUTS = ("params", "A_max_rel_dev", "B1_max_rel_dev", "B2_max_rel_dev", "C1_max_rel_dev", "C2_max_rel_dev",
           "A_summary", "B1_summary", "B2_summary", "C1_summary", "C2_summary", "faults", "faults_caught",
           "faults_total", "conditions_met", "conditions_total", "test_passed", "controls_passed", "controls_total")
LIMIT = 200


class Refused(Exception):
    pass


# ---------------------------------------------------------------- the network

class Net:
    """N neurons (W[m][k]: from neuron k to neuron m, zero diagonal), inputs (W_in[m][i]: from input i to neuron m),
    input spikes as a sorted list of (time, input), firing[m] False for a non-firing readout."""

    def __init__(self, W, W_in, inputs, firing=None):
        self.n = len(W)
        self.W = [list(row) for row in W]
        self.W_in = [list(row) for row in W_in]
        self.inputs = sorted(inputs)
        self.firing = list(firing) if firing is not None else [True] * self.n
        if len(self.W_in) != self.n or len(self.firing) != self.n or any(len(r) != self.n for r in self.W):
            raise Refused("the network's shapes disagree")
        if any(self.W[m][m] != 0 for m in range(self.n)):
            raise Refused("a self-connection")
        n_in = len(self.W_in[0]) if self.n else 0
        if any(len(r) != n_in for r in self.W_in) or any(not 0 <= i < n_in for _, i in self.inputs):
            raise Refused("an input out of range")


def v_at(A, B, u):
    return A * math.exp(-ALPHA * u) + B * math.exp(-BETA * u)


def dv_at(A, B, u):
    return -ALPHA * A * math.exp(-ALPHA * u) - BETA * B * math.exp(-BETA * u)


def coeffs(V0, I0):
    """V(u) = A e^(-alpha u) + B e^(-beta u) from V(0) = V0 and I(0) = I0."""
    return V0 + KAPPA * I0, -KAPPA * I0


def critical(A, B):
    """The one u where dV/du = 0, if any (None otherwise)."""
    if A == 0 or B == 0:
        return None
    r = -BETA * B / (ALPHA * A)
    if r <= 0:
        return None
    return math.log(r) / (BETA - ALPHA)


def first_crossing(A, B, D):
    """The first u in (0, D] where V crosses theta upward, by bracketing on V's monotone pieces and bisection."""
    us = critical(A, B)
    pieces = [(0.0, us), (us, D)] if us is not None and 0.0 < us < D else [(0.0, D)]
    for a, b in pieces:
        va, vb = v_at(A, B, a), v_at(A, B, b)
        if va < THETA <= vb:
            lo, hi = a, b
            for _ in range(200):
                mid = 0.5 * (lo + hi)
                if mid <= lo or mid >= hi:
                    break
                if v_at(A, B, mid) < THETA:
                    lo = mid
                else:
                    hi = mid
            u = hi
            for _ in range(3):
                d = dv_at(A, B, u)
                if d <= 0:
                    break
                nu = u - (v_at(A, B, u) - THETA) / d
                if not a <= nu <= b:
                    break
                u = nu
            return u
    return None


def simulate(net, T=T_END, observe=(), track_readout=None, check=True):
    """Rule 1. Returns a record: segments [(t0, t1, A[], B[], spiker at t1 or None)], events in time order
    [(t, kind, index, extra, the segment the event begins)], spikes [(t, neuron, I^-)], and with check the margins;
    with track_readout the readout's local maxima and its maximum."""
    n = net.n
    V, I = [0.0] * n, [0.0] * n
    t = 0.0
    events, segments, spikes = [], [], []
    obs = sorted(o for o in observe if 0.0 < o[0] < T)
    inputs = [(ti, i) for ti, i in net.inputs if ti < T]
    p = q = 0
    while True:
        t_in = inputs[p][0] if p < len(inputs) else math.inf
        t_ob = obs[q][0] if q < len(obs) else math.inf
        t_next = min(t_in, t_ob, T)
        D = max(0.0, t_next - t)
        AB = [coeffs(V[m], I[m]) for m in range(n)]
        best = None
        if D > 0.0:
            for m in range(n):
                if net.firing[m]:
                    u = first_crossing(AB[m][0], AB[m][1], D)
                    if u is not None and (best is None or u < best[0]):
                        best = (u, m)
        if best is not None:
            u, nb = best
            t1 = min(t + u, t_next)
        else:
            u, nb, t1 = D, None, t_next
        segments.append((t, t1, [a for a, _ in AB], [b for _, b in AB], nb))
        decay = math.exp(-BETA * u)
        for m in range(n):
            V[m] = v_at(AB[m][0], AB[m][1], u)
            I[m] *= decay
        t = t1
        seg = len(segments)
        if nb is not None:
            spikes.append((t, nb, I[nb]))
            events.append((t, "spike", nb, I[nb], seg))
            V[nb] = 0.0
            for m in range(n):
                I[m] += net.W[m][nb]
            continue
        if t_next >= T:
            break
        if t_ob <= t_in:
            _, r, g = obs[q]
            events.append((t, "observe", r, (g, V[r]), seg))
            q += 1
        else:
            _, i = inputs[p]
            events.append((t, "input", i, None, seg))
            for m in range(n):
                I[m] += net.W_in[m][i]
            p += 1
    rec = {"segments": segments, "events": events, "spikes": spikes, "V_end": V[:], "I_end": I[:], "T": T}
    if track_readout is not None:
        loc = sorted(local_maxima(rec, track_readout), key=lambda x: -x[0])
        rec["rlocal"] = loc
        rec["rmax"] = loc[0] if loc else None
    if check:
        rec["margins"] = margins_of(net, rec)
    return rec


def local_maxima(rec, m):
    """The local maxima of neuron m's V that are not threshold crossings: (value, time, kind, segment, offset)."""
    segs = rec["segments"]
    out = []
    for k, (t0, t1, As, Bs, nb) in enumerate(segs):
        A, B = As[m], Bs[m]
        D = t1 - t0
        us = critical(A, B)
        if us is not None and 0.0 < us < D and dv_at(A, B, 0.0) > 0.0:
            out.append((v_at(A, B, us), t0 + us, "interior", k, us))
        if nb == m or dv_at(A, B, D) <= 0.0:
            continue
        if k + 1 < len(segs):
            if dv_at(segs[k + 1][2][m], segs[k + 1][3][m], 0.0) <= 0.0:
                out.append((v_at(A, B, D), t1, "corner", k, D))
        else:
            out.append((v_at(A, B, D), t1, "end", k, D))
    return out


def margins_of(net, rec):
    T, ev = rec["T"], rec["events"]
    mg = {"dv": math.inf, "v": math.inf, "event": math.inf, "end": math.inf}
    for t, _, i_minus in rec["spikes"]:
        mg["dv"] = min(mg["dv"], i_minus - THETA)
        mg["end"] = min(mg["end"], T - t)
    for m in range(net.n):
        if net.firing[m]:
            for val, *_ in local_maxima(rec, m):
                mg["v"] = min(mg["v"], THETA - val)
    for j, e in enumerate(ev):
        if e[1] == "spike":
            if j > 0:
                mg["event"] = min(mg["event"], e[0] - ev[j - 1][0])
            if j + 1 < len(ev):
                mg["event"] = min(mg["event"], ev[j + 1][0] - e[0])
    if "rmax" in rec:
        top, loc = rec["rmax"], rec["rlocal"]
        mg["readout"] = (top[0] - loc[1][0]) if len(loc) > 1 else (math.inf if top else -math.inf)
        if top and top[2] == "interior":
            t0, t1 = rec["segments"][top[3]][:2]
            mg["readout_event"] = min(top[1] - t0, t1 - top[1])
        else:
            mg["readout_event"] = -math.inf
    return mg


def non_critical(rec, need=None, readout=False):
    m = rec["margins"]
    ok = (m["dv"] >= MARGIN_DV and m["v"] >= MARGIN_V and m["event"] >= MARGIN_EVENT and m["end"] >= MARGIN_END)
    if need is not None:
        ok = ok and any(s[1] in need for s in rec["spikes"])
    if readout:
        ok = (ok and rec.get("rmax") is not None and rec["rmax"][2] == "interior" and m["readout"] >= MARGIN_V
              and m["readout_event"] >= MARGIN_EVENT)
    return ok


def structure(rec):
    """What the stencil must not change: the order of events (spikes, inputs, observations) and the interval of a
    readout's maximum."""
    s = tuple((e[1], e[2]) for e in rec["events"])
    if "rmax" in rec:
        top = rec["rmax"]
        s += (("max", top[3], top[2]) if top else ("max", None, None),)
    return s


# ---------------------------------------------------------------- losses

def seg_v2_integral(A, B, D):
    """The integral over [0, D] of V^2, V = A e^(-alpha u) + B e^(-beta u)."""
    a, b = ALPHA, BETA
    return (A * A / (2 * a) * (1 - math.exp(-2 * a * D)) + 2 * A * B / (a + b) * (1 - math.exp(-(a + b) * D))
            + B * B / (2 * b) * (1 - math.exp(-2 * b * D)))


class Loss:
    """A loss: spike-time terms (sum_t: t; sum_t2: t^2 / T) on given neurons, a voltage integral sum_n c_n V_n^2 / 2
    (v2), readout voltages at fixed times (observe: sum of g V_r(t_m)), or the readout's maximum (max)."""

    def __init__(self, kind, neurons=(), c=None, observe=(), readout=None):
        if kind not in ("sum_t", "sum_t2", "v2", "observe", "max"):
            raise Refused(f"no loss {kind}")
        self.kind, self.neurons, self.c, self.observe, self.readout = kind, set(neurons), c, tuple(observe), readout

    def value(self, rec):
        if self.kind == "sum_t":
            return sum(t for t, n, _ in rec["spikes"] if n in self.neurons)
        if self.kind == "sum_t2":
            return sum(t * t / rec["T"] for t, n, _ in rec["spikes"] if n in self.neurons)
        if self.kind == "v2":
            L = 0.0
            for t0, t1, As, Bs, _ in rec["segments"]:
                for m, cm in enumerate(self.c):
                    if cm:
                        L += 0.5 * cm * seg_v2_integral(As[m], Bs[m], t1 - t0)
            return L
        if self.kind == "observe":
            return sum(e[3][0] * e[3][1] for e in rec["events"] if e[1] == "observe")
        top = rec.get("rmax")
        return top[0] if top else 0.0

    def dlp(self, t, n, T):
        if self.kind == "sum_t" and n in self.neurons:
            return 1.0
        if self.kind == "sum_t2" and n in self.neurons:
            return 2.0 * t / T
        return 0.0

    def lv_jump(self, n):
        """l_V^- - l_V^+ at a spike of neuron n (its V from theta to 0)."""
        if self.kind == "v2" and self.c[n]:
            return 0.5 * self.c[n] * THETA * THETA
        return 0.0


# ---------------------------------------------------------------- EventProp

def back_segment(lv, li, A, B, D, c):
    """Rule 2: lambda_V and lambda_I at the start of a segment of length D from their values at its end, with the
    forcing c V(t), V(u) = A e^(-alpha u) + B e^(-beta u), closed form."""
    a, b = ALPHA, BETA
    P = -c * A / 2.0
    Q = -a * c * B / (a + b)
    K = lv * math.exp(-a * D) - P * math.exp(-2 * a * D) - Q * math.exp(-(a + b) * D)
    lv0 = K + P + Q
    R = b * K / (b - a)
    S = b * P / (a + b)
    U = Q / 2.0
    M = li * math.exp(-b * D) - R * math.exp((a - b) * D) - S * math.exp(-(a + b) * D) - U * math.exp(-2 * b * D)
    li0 = M + R + S + U
    return lv0, li0


def eventprop(net, rec, loss, variant="paper"):
    """Rule 2: the gradient of the loss with respect to W and W_in, by the paper's adjoint network (or a planted
    fault, rule 6)."""
    if variant not in VARIANTS:
        raise Refused(f"no variant {variant}")
    n = net.n
    n_in = len(net.W_in[0]) if n else 0
    lv, li = [0.0] * n, [0.0] * n
    gW = [[0.0] * n for _ in range(n)]
    gin = [[0.0] * n_in for _ in range(n)]
    c = list(loss.c) if loss.kind == "v2" else [0.0] * n
    segs = rec["segments"]
    starts = {}
    for e in rec["events"]:
        starts.setdefault(e[4], []).append(e)
    top = rec.get("rmax") if loss.kind == "max" else None
    for k in range(len(segs) - 1, -1, -1):
        t0, t1, As, Bs, _ = segs[k]
        if top is not None and top[3] == k:
            us = top[4]
            ea, eb = math.exp(-ALPHA * us), math.exp(-BETA * us)
            for m in range(n):
                lv[m], li[m] = back_segment(lv[m], li[m], As[m] * ea, Bs[m] * eb, (t1 - t0) - us, c[m])
            lv[loss.readout] -= 1.0 / TAU_M
            for m in range(n):
                lv[m], li[m] = back_segment(lv[m], li[m], As[m], Bs[m], us, c[m])
        else:
            for m in range(n):
                lv[m], li[m] = back_segment(lv[m], li[m], As[m], Bs[m], t1 - t0, c[m])
        for t, kind, idx, extra, _ in reversed(starts.get(k, [])):
            if kind == "input":
                for j in range(n):
                    gin[j][idx] -= TAU_S * li[j]
            elif kind == "observe":
                lv[idx] -= extra[0] / TAU_M
            else:
                nn, i_minus = idx, extra
                for j in range(n):
                    gW[j][nn] -= TAU_S * li[j]
                if variant == "transposed":
                    coupling = sum(net.W[nn][m] * (lv[m] - li[m]) for m in range(n))
                else:
                    coupling = sum(net.W[m][nn] * (lv[m] - li[m]) for m in range(n))
                theta_term = 0.0 if variant == "no_theta" else THETA * lv[nn]
                lvj = 0.0 if variant == "no_lv_jump" else loss.lv_jump(nn)
                lv[nn] += (theta_term + coupling + loss.dlp(t, nn, rec["T"]) + lvj) / (i_minus - THETA)
    return gW, gin


def pick(gW, gin, weights):
    return [gW[a][b] if kind == "W" else gin[a][b] for kind, a, b in weights]


# ---------------------------------------------------------------- central differences

def stencil(f, x, h):
    return (f(x - 2 * h) - 8 * f(x - h) + 8 * f(x + h) - f(x + 2 * h)) / (12 * h)


def fd_all(net, loss, weights, base, observe=(), track=None, h=H_FD):
    """Rule 3 for every weight, and how many stencil steps changed the base record's structure."""
    sig = structure(base)
    out, changed = [], 0
    for kind, a, b in weights:
        mat = net.W if kind == "W" else net.W_in
        w0 = mat[a][b]

        def f(w):
            nonlocal changed
            mat[a][b] = w
            rec = simulate(net, observe=observe, track_readout=track, check=False)
            if structure(rec) != sig:
                changed += 1
            return loss.value(rec)
        try:
            out.append(stencil(f, w0, h))
        finally:
            mat[a][b] = w0
    return out, changed


def finite(d):
    """A margins record for JSON: infinities as None."""
    return {k: (v if math.isfinite(v) else None) for k, v in d.items()}


def deviations(ep, fd):
    G = max((abs(x) for x in fd), default=0.0)
    return [abs(e - f) / max(abs(f), FLOOR * G, 1e-300) for e, f in zip(ep, fd)], G


# ---------------------------------------------------------------- draws

def rng_for(seed, label):
    return random.Random(int.from_bytes(hashlib.sha256(bytes.fromhex(seed) + label.encode()).digest(), "big"))


def poisson(rng, n_trains, rate_hz, T=T_END):
    out = []
    lam = rate_hz / 1000.0
    for i in range(n_trains):
        t = rng.expovariate(lam)
        while t < T:
            out.append((t, i))
            t += rng.expovariate(lam)
    return sorted(out)


def build(seed, scenario, d, attempt):
    """Rule 4: one candidate network of a scenario: (net, loss, weights, observe, track, need, readout)."""
    fam = FAMILY[scenario]
    rng = rng_for(seed, f"|eventprop/{fam}/{d}/{attempt}")
    if fam == "A":
        W = [[0.0, 0.0], [rng.uniform(3.0, 6.0), 0.0]]
        W_in = [[rng.uniform(0.0, 0.04) for _ in range(100)], [0.0] * 100]
        net = Net(W, W_in, poisson(rng, 100, 200.0))
        weights = [("in", 0, i) for i in range(100)] + [("W", 1, 0)]
        return net, Loss("sum_t", neurons=(1,)), weights, (), None, {1}, False
    if fam == "B":
        n = 6
        W = [[0.0 if m == k else rng.uniform(-0.5, 0.5) for k in range(n)] for m in range(n)]
        W_in = [[rng.uniform(0.0, 0.2) for _ in range(30)] for _ in range(n)]
        net = Net(W, W_in, poisson(rng, 30, 100.0))
        loss = Loss("sum_t2", neurons=(0, 1)) if scenario == "B1" else Loss("v2", c=[1.0 / T_END] * n)
        weights = [("W", m, k) for m in range(n) for k in range(n) if m != k] + \
                  [("in", m, i) for m in range(n) for i in range(30)]
        return net, loss, weights, (), None, {0, 1}, False
    n, r = 6, 5
    W = [[0.0] * n for _ in range(n)]
    for h in range(5):
        W[r][h] = rng.uniform(0.0, 1.0)
    W_in = [[rng.uniform(0.0, 0.4) for _ in range(20)] for _ in range(5)] + [[0.0] * 20]
    net = Net(W, W_in, poisson(rng, 20, 100.0), firing=[True] * 5 + [False])
    weights = [("in", m, i) for m in range(5) for i in range(20)] + [("W", r, h) for h in range(5)]
    if scenario == "C1":
        observe = ((25.0, r, 1.0), (50.0, r, 1.0), (75.0, r, 1.0))
        return net, Loss("observe", observe=observe), weights, observe, None, set(range(5)), False
    return net, Loss("max", readout=r), weights, (), r, set(range(5)), True


def accept(seed, scenario, d):
    """Rule 4: the first non-critical candidate, with its central differences, and why earlier ones were drawn
    again."""
    why = {"critical": 0, "stencil": 0}
    for attempt in range(MAX_ATTEMPTS):
        net, loss, weights, observe, track, need, readout = build(seed, scenario, d, attempt)
        rec = simulate(net, observe=observe, track_readout=track)
        if not non_critical(rec, need=need, readout=readout):
            why["critical"] += 1
            continue
        fd, changed = fd_all(net, loss, weights, rec, observe, track)
        if changed:
            why["stencil"] += 1
            continue
        return net, loss, weights, rec, fd, attempt, why
    raise Refused(f"no non-critical draw for {scenario} {d} in {MAX_ATTEMPTS} attempts")


# ---------------------------------------------------------------- controls

def _rk4_step(V, I, h):
    def f(V, I):
        return [(-v + i) / TAU_M for v, i in zip(V, I)], [-i / TAU_S for i in I]
    k1v, k1i = f(V, I)
    k2v, k2i = f([v + 0.5 * h * k for v, k in zip(V, k1v)], [i + 0.5 * h * k for i, k in zip(I, k1i)])
    k3v, k3i = f([v + 0.5 * h * k for v, k in zip(V, k2v)], [i + 0.5 * h * k for i, k in zip(I, k2i)])
    k4v, k4i = f([v + h * k for v, k in zip(V, k3v)], [i + h * k for i, k in zip(I, k3i)])
    return ([v + h / 6 * (a + 2 * b + 2 * c + d) for v, a, b, c, d in zip(V, k1v, k2v, k3v, k4v)],
            [i + h / 6 * (a + 2 * b + 2 * c + d) for i, a, b, c, d in zip(I, k1i, k2i, k3i, k4i)])


def rk4_network(net, T, dt):
    """A fine-step integration of rule 1's network: RK4 on V and I, a spike located inside its step by bisection on
    the cubic Hermite interpolant and the state carried to it by one RK4 step. Returns [(t, neuron)]."""
    n = net.n
    V, I = [0.0] * n, [0.0] * n
    spikes, inputs, p, t = [], [x for x in net.inputs if x[0] < T], 0, 0.0
    while t < T - 1e-12:
        while p < len(inputs) and inputs[p][0] <= t:
            for k in range(n):
                I[k] += net.W_in[k][inputs[p][1]]
            p += 1
        step = min(dt, T - t)
        if p < len(inputs) and inputs[p][0] < t + step:
            step = inputs[p][0] - t
        if step <= 0:
            continue
        Vn, In = _rk4_step(V, I, step)
        cands = []
        for m in range(n):
            if net.firing[m] and V[m] < THETA <= Vn[m]:
                d0, d1 = (-V[m] + I[m]) / TAU_M, (-Vn[m] + In[m]) / TAU_M
                lo, hi = 0.0, step
                for _ in range(80):
                    s = 0.5 * (lo + hi)
                    x = s / step
                    v = ((2 * x ** 3 - 3 * x ** 2 + 1) * V[m] + (x ** 3 - 2 * x ** 2 + x) * step * d0
                         + (-2 * x ** 3 + 3 * x ** 2) * Vn[m] + (x ** 3 - x ** 2) * step * d1)
                    if v < THETA:
                        lo = s
                    else:
                        hi = s
                cands.append((hi, m))
        if cands:
            s, m = min(cands)
            V, I = _rk4_step(V, I, s)
            spikes.append((t + s, m))
            V[m] = 0.0
            for k in range(n):
                I[k] += net.W[k][m]
            t += s
            continue
        V, I = Vn, In
        t += step
    return spikes


def rk4_adjoint(lv, li, A, B, D, c, steps):
    """The adjoint's equations integrated backward over a segment by RK4 (the control for back_segment)."""
    h = D / steps

    def f(u, x):
        return (ALPHA * (x[0] + c * v_at(A, B, u)), BETA * (x[1] - x[0]))
    u, x = D, (lv, li)
    for _ in range(steps):
        k1 = f(u, x)
        k2 = f(u - h / 2, (x[0] - h / 2 * k1[0], x[1] - h / 2 * k1[1]))
        k3 = f(u - h / 2, (x[0] - h / 2 * k2[0], x[1] - h / 2 * k2[1]))
        k4 = f(u - h, (x[0] - h * k3[0], x[1] - h * k3[1]))
        x = (x[0] - h / 6 * (k1[0] + 2 * k2[0] + 2 * k3[0] + k4[0]), x[1] - h / 6 * (k1[1] + 2 * k2[1] + 2 * k3[1] + k4[1]))
        u -= h
    return x


def g_psp(u):
    return math.exp(-ALPHA * u) - math.exp(-BETA * u)


def controls_known(seed):
    c = {}
    # a single neuron, one input spike at 2 ms with weight w
    w = 8.0
    net = Net([[0.0]], [[w]], [(2.0, 0)])
    rec = simulate(net)
    ok = len(rec["spikes"]) == 1
    if ok:
        u = rec["spikes"][0][0] - 2.0
        dvdt = (-THETA + w * math.exp(-BETA * u)) / TAU_M
        dtdw = -KAPPA * g_psp(u) / dvdt
        _, gin = eventprop(net, rec, Loss("sum_t", neurons=(0,)))
        ok = abs(w * KAPPA * g_psp(u) - THETA) < 1e-12 and abs(gin[0][0] - dtdw) < 1e-10 * abs(dtdw)
    c["one neuron, one input: the spike time and EventProp's dt/dw as the implicit function theorem gives them"] = ok
    # a readout and one input spike: L = V_r(t_m), and L = max_t V_r(t)
    net = Net([[0.0]], [[0.7]], [(10.0, 0)], firing=[False])
    obs = ((40.0, 0, 1.0),)
    _, gin = eventprop(net, simulate(net, observe=obs), Loss("observe", observe=obs))
    want = KAPPA * g_psp(30.0)
    c["a readout at a fixed time: dL/dw = kappa (e^(-D/tau_m) - e^(-D/tau_s))"] = abs(gin[0][0] - want) < 1e-12
    rec = simulate(net, track_readout=0)
    u_star = math.log(BETA / ALPHA) / (BETA - ALPHA)
    _, gin = eventprop(net, rec, Loss("max", readout=0))
    ok = rec["rmax"] is not None and abs(rec["rmax"][1] - 10.0 - u_star) < 1e-9
    c["a readout's maximum: dL/dw = kappa (e^(-u*/tau_m) - e^(-u*/tau_s)) at its time u*"] = (
        ok and abs(gin[0][0] - KAPPA * g_psp(u_star)) < 1e-12)
    # the event-driven simulation against a fine-step integration
    rng = rng_for(seed, "|eventprop/control/sim")
    n = 3
    W = [[0.0 if m == k else rng.uniform(-0.3, 0.6) for k in range(n)] for m in range(n)]
    W_in = [[rng.uniform(0.0, 0.5) for _ in range(10)] for _ in range(n)]
    net = Net(W, W_in, poisson(rng, 10, 100.0, 60.0))
    ev = [(t, m) for t, m, _ in simulate(net, T=60.0)["spikes"]]
    fine = rk4_network(net, 60.0, 0.002)
    c["the event-driven simulation against RK4 at 0.002 ms: the same spikes within 1e-6 ms"] = (
        len(ev) > 0 and len(fine) == len(ev) and all(m1 == m2 and abs(t1 - t2) < 1e-6
                                                     for (t1, m1), (t2, m2) in zip(ev, fine)))
    # the forced adjoint against RK4
    ok = True
    for (lv, li, A, B, D, cc) in ((0.3, -0.2, 0.8, -0.5, 7.0, 0.04), (0.0, 0.0, 1.2, -0.9, 30.0, 1.0),
                                  (-1.1, 0.4, -0.3, 0.2, 3.0, 0.0)):
        x = back_segment(lv, li, A, B, D, cc)
        y = rk4_adjoint(lv, li, A, B, D, cc, 4000)
        ok = ok and abs(x[0] - y[0]) < 1e-10 and abs(x[1] - y[1]) < 1e-10
    c["the closed forced adjoint against RK4 on three segments, within 1e-10"] = ok
    # the stencil on a known function
    want = math.exp(0.3) * (math.sin(0.3) + math.cos(0.3))
    c["the fourth-order stencil on e^x sin x at 0.3 within 1e-9"] = (
        abs(stencil(lambda x: math.exp(x) * math.sin(x), 0.3, 1e-3) - want) < 1e-9)
    return c


# ---------------------------------------------------------------- the run

def run(seed, results="results", draws=DRAWS, scenarios=SCENARIOS):
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        raise Refused("the seed must be 64 hex characters")
    if any(s not in SCENARIOS for s in scenarios):
        raise Refused("an unknown scenario")
    if draws < 1:
        raise Refused("at least one draw")
    per = {}
    faults = {f: {} for f in FAULTS}
    for s in scenarios:
        stats = {"weights": 0, "spikes": 0, "redraws": 0, "max_dev": 0.0, "all_ok": True, "draws": []}
        for d in range(draws):
            net, loss, weights, rec, fd, attempt, why = accept(seed, s, d)
            ep = pick(*eventprop(net, rec, loss), weights)
            devs, G = deviations(ep, fd)
            stats["weights"] += len(weights)
            stats["spikes"] += len(rec["spikes"])
            stats["redraws"] += attempt
            stats["max_dev"] = max(stats["max_dev"], max(devs))
            stats["all_ok"] = stats["all_ok"] and all(x <= TOL for x in devs)
            draw_faults = {}
            for f, where in FAULTS.items():
                if s in where:
                    devf, _ = deviations(pick(*eventprop(net, rec, loss, variant=f), weights), fd)
                    faults[f].setdefault(s, []).append(max(devf))
                    draw_faults[f] = max(devf)
            stats["draws"].append({
                "attempt": attempt, "redrawn": why, "spikes": len(rec["spikes"]), "G": G, "max_dev": max(devs),
                "margins": finite(rec["margins"]), "faults": draw_faults,
                "spike_list": [[t, nn] for t, nn, _ in rec["spikes"]],
                "gradients": [[f"{kind}[{a}][{b}]", e, x, dv] for (kind, a, b), e, x, dv in zip(weights, ep, fd, devs)]})
        per[s] = stats
    cond = {f"{s}: EventProp within {TOL:g} of central differences for every weight of {draws} draws": per[s]["all_ok"]
            for s in scenarios}
    caught = {f: {s: max(v) > TOL for s, v in d.items()} for f, d in faults.items()}
    n_caught = sum(sum(v.values()) for v in caught.values())
    n_faults = sum(len(v) for v in caught.values())
    controls = controls_known(seed)

    values = {"params": (f"tau_m {TAU_M:g} ms, tau_s {TAU_S:g} ms, theta {THETA:g}, T {T_END:g} ms; 4th-order central "
                         f"differences, h {H_FD:g}; tolerance {TOL:g}, floor {FLOOR:g} of the draw's largest gradient")}
    for s in SCENARIOS:
        if s in per:
            p = per[s]
            values[f"{s}_max_rel_dev"] = float(f"{p['max_dev']:.2g}")
            values[f"{s}_summary"] = (f"{len(p['draws'])} draws, {p['weights']} weights, {p['spikes']} spikes, "
                                      f"{p['redraws']} redraws; all within tolerance: {'yes' if p['all_ok'] else 'no'}")
        else:
            values[f"{s}_max_rel_dev"] = -1.0
            values[f"{s}_summary"] = "not run"
    values["faults"] = "; ".join(f"{f} caught in {sum(v.values())} of {len(v)}" for f, v in caught.items())
    values.update({"faults_caught": n_caught, "faults_total": n_faults,
                   "conditions_met": sum(cond.values()), "conditions_total": len(cond),
                   "test_passed": int(bool(cond) and all(cond.values())),
                   "controls_passed": sum(controls.values()), "controls_total": len(controls)})
    out = {k: values[k] for k in OUTPUTS}
    for k, v in out.items():
        if isinstance(v, str) and len(v) > LIMIT:
            raise AssertionError(f"{k}: longer than {LIMIT} characters: {v}")
    detail = {"test": TEST, "conditions": cond, "controls": controls, "scenarios": per,
              "faults": faults, "faults_caught": caught}
    os.makedirs(results, exist_ok=True)
    with open(os.path.join(results, "outputs.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, sort_keys=True)
        fh.write("\n")
    with open(os.path.join(results, "detail.json"), "w", encoding="utf-8") as fh:
        json.dump(detail, fh, indent=1, sort_keys=True, default=str)
        fh.write("\n")
    return out, detail


def main():
    seed = os.environ.get("ECDYSIS_SEED", "")
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        sys.exit("ECDYSIS_SEED must be the 64-hex seed the archive issued")
    try:
        out, _ = run(seed)
    except Refused as e:
        sys.exit(f"eventprop: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
