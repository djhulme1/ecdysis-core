r"""Collective memory in the zones model: Couzin, Krause, James, Ruxton & Franks (2002).

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test is the abstract's third sentence of Couzin et
al., "Collective memory and spatial sorting in animal groups", Journal of Theoretical Biology 218(1), 1-11 (2002;
doi:10.1006/jtbi.2002.3065): "Further, we present the first evidence for collective memory in such animal groups
(where the previous history of group structure influences the collective behaviour exhibited as individual
interactions change) during the transition of a group from one type of collective behaviour to another."

The paper (read as data, from a copy of the journal's PDF) gives the model. N individuals with positions c_i and unit
directions v_i move in unbounded three-dimensional space in steps of tau = 0.1 s. Each step, an individual with
neighbours in its zone of repulsion (a sphere of radius r_r, all round) takes d_r = -sum r_ij/|r_ij| over them
(its eq. 1, highest priority). Otherwise it responds to neighbours it can detect, outside a blind cone behind it of
interior angle 360 - alpha degrees: in the zone of orientation (r_r <= |c_j - c_i| < r_o), d_o = sum v_j/|v_j|
(eq. 2, summed "j = 1 to n_o", where eqs. 1 and 3 sum over "j != i"); in the zone of attraction (r_o <= |c_j - c_i|
<= r_a), d_a = sum r_ij/|r_ij| (eq. 3). With neighbours only in one zone it takes that zone's vector, with both
d_i = (d_o + d_a)/2, and with none, or a zero vector, its own direction. d_i is then rotated "by an angle taken at
random from a spherically wrapped Gaussian distribution with standard deviation sigma", and each individual turns
towards it by at most theta*tau, taking it when the angle is less. Speed s is constant. p_group = |sum v_i|/N
(eq. 4) and m_group = |sum r_ic x v_i|/N (eq. 5, r_ic from the group's centre c_group to c_i; the paper bounds m_group
by 0 and 1, so r_ic is taken as a unit vector). Start: random orientations, random positions "within a sphere in which
each can detect at least one individual". Fragmentation: equivalence classes under detection within the field of
perception; "analysis is only performed on non-fragmented groups". Figure 3's caption: N = 100, r_r = 1,
alpha = 270, theta = 40 (degrees a second), s = 3, sigma = 0.05 (radians, Table 1). Figure 4, the collective memory:
r_a = 14 fixed, r_o raised and then lowered; "Two thousand time steps were run under each value of r_o before it was
incremented or decremented. Fifteen replicates were performed". Read from the figure (a 300-dpi render): r_o from 1
to 4 in steps of 0.25 both ways; rising, a torus from 1.5 to 2.5 (m_group 0.87 to 0.95, p_group 0.22 to 0.27) and
a polarized group from 3.25 (p_group 0.86 to 0.91); falling, the polarized group kept down to 1.5 (p_group 0.89 to
0.93, m_group 0.07 to 0.20), and below that the swarm. The text: "As r_o increases towards 1.5, the group ... enters
the torus phase ... Beyond 2.5 ... a polarized configuration ... if the group moves back ... decreasing r_o ... the
group does not adopt the torus conformation. As r_o decreases below 1.5, however, the polarization rapidly
disappears and the group readopts the swarm configuration."

Rules, committed before any run of the model at the test's parameters (the engine was timed there with its outputs
discarded, and nothing else was run there):

1. The model (spp/couzin.c), in plain arithmetic so that any IEEE machine gives the same numbers: xoshiro256** seeded
   from the archive's seed; normal deviates by Marsaglia's polar method; sines, cosines and the logarithm by series
   written in the program; only sqrt, frexp and fabs from the library; built with -ffp-contract=off. Updates are
   synchronous: every desired direction from the state at t, then every turn, then every move by s*tau along the
   new direction. The blind cone is the set of neighbours at more than alpha/2 from v_i; the zone of repulsion has
   none. The details the text leaves open are run under every reading it allows, eight model readings:
   (i) d_o without the focal individual (eq. 2's zone holds neighbours) or with it (its "j = 1"), added when n_o > 0;
   (ii) d_o and d_a summed as eqs. 2 and 3 print them, or each made a unit vector before they are averaged (the 1/2
   of the average suggests directions); (iii) the noise as an angle drawn from N(0, sigma^2) about an axis uniform
   in the plane perpendicular to d_i, or as a Gaussian of s.d. sigma in that plane wrapped onto the sphere (the
   angle then Rayleigh). The literal reading is the first of each: without, summed, an angle.
2. The protocol (Figure 4): N = 100, r_r = 1, r_a = 14, alpha = 270, theta = 40, s = 3, sigma = 0.05, tau = 0.1.
   Each replicate starts at r_o = 1 from random directions and positions uniform in a ball of radius 5 (every pair
   within r_a; drawn again until each individual detects another), runs 2,000 steps at each of r_o = 1, 1.25, ...,
   4, and then, continuing, 2,000 steps at each of 3.75, 3.5, ..., 1 (the value at 4 is shared). 15 replicates, the
   same 15 seeds under every reading. A replicate's value at an r_o is read two ways (both counted as readings):
   at the last of its 2,000 steps, or as the mean over its last 1,000. It counts only if the group is one
   equivalence class at that last step (two individuals joined when within r_a and either is within the other's
   field of perception, or within the other's zone of repulsion).
3. The conditions, on the means over the counted replicates, for each of the 16 readings (8 model readings, 2 ways
   of reading a value): at r_o = 1.75, 2 and 2.25, the rising sweep's m_group >= 0.6 and p_group <= 0.4 (a torus)
   and the falling sweep's p_group >= 0.7 and m_group <= 0.3 (a polarized group, no torus): 12 conditions; and
   p_group <= 0.4 at r_o = 1 on the rising sweep (its start) and on the falling (its end), and >= 0.7 at r_o = 4:
   3 more, 15 in all. A value with fewer than 8 counted replicates fails its conditions. The test passes when all
   15 hold under at least one reading (as with Rabung & Lotts's turnings, the paper's model is one of the readings
   its text allows); every reading's count is reported, and the literal reading's.

Beside the test, not counted: every reading's curves at all 25 values, and the literal reading's mean absolute gap to
the figure's values read by eye; the state reached from random starts at r_o = 1.75, 2 and 2.25 (15 each, 5,000
steps, the paper's time to a stable state, literal reading); the same sweep with alpha = 360, where the text says the torus's range is "diminished to a
very small range"; a coarse grid of Figure 3 (Delta r_o = r_o - r_r in 0, 1, 2, 4, 8, 13; Delta r_a = r_a - r_o in
1, 4, 8, 13; 10 random starts each, 5,000 steps); and the sorting of Figure 5 at its largest variations (speed with
s.d. 0.2, r_r with s.d. 0.3; r_o = 6, r_a = 14; 30 replicates, 5,000 steps, a deviate that would make the parameter
non-positive, or r_r not below r_o, drawn again), as Spearman's rho of the parameter against frontness (the signed
distance from the plane through c_group perpendicular to the mean direction) and centrality (minus the distance from
c_group), set against the figure's 0.76 and -0.22 (speed) and -0.44 and -0.57 (r_r).

Controls (controls_passed of controls_total):
 (a) The C program against a plain Python implementation of rule 1 (12 individuals, r_a = 6, r_o = 2, a ball of 3,
     150 steps; all eight readings, the two variations, and alpha = 360): the same positions, directions, p_group,
     m_group and classes, bit for bit.
 (b) The series against the library over 2,000 arguments each: sin and cos within 8 x 2^-52 absolutely on [-4, 4),
     log within 4 units in the last place on (0, 4]; and the program's values equal to this module's.
 (c) Free flight: five aligned individuals a million units apart, sigma = 0, 1,000 steps: directions unchanged,
     p_group 1, and the positions this module computes.
 (d) The noise: one free individual, 200,000 steps under each noise reading: the mean sine and 1 - cosine of the
     angle turned within 5 standard errors of their exact values for min(angle, theta*tau).
 (e) The measures: a ring of 100 moving tangentially has m_group 1 and p_group 0, a file moving along itself
     p_group 1 and m_group 0 (within 1e-12).
 (f) The classes: two clusters 100 apart are two, one cluster one.
 (g) The decision on the figure's own values (read by eye): all 15 conditions hold.
 (h) A planted fault: the decision on a history with no memory (the falling sweep a copy of the rising) fails all
     six of the falling sweep's conditions at r_o = 1.75, 2 and 2.25, and so the test.
"""

import concurrent.futures
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
SOURCE = os.path.join(HERE, "couzin.c")

N, RR, RA, ALPHA, THETA, SPEED, SIGMA, TAU, R0 = 100, 1.0, 14.0, 270.0, 40.0, 3.0, 0.05, 0.1, 5.0
RO_LO, RO_STEP, N_UP, STEPS_PER, WINDOW = 1.0, 0.25, 13, 2000, 1000
REPLICATES, MIN_COUNTED = 15, 8
CORE = (1.75, 2.0, 2.25)
TORUS_M, TORUS_P, PAR_P, PAR_M, LOW_P, HIGH_P = 0.6, 0.4, 0.7, 0.3, 0.4, 0.7
READINGS = [(s, u, z) for s in (0, 1) for u in (0, 1) for z in (1, 2)]  # (self in d_o, unit vectors, noise)
LITERAL = (0, 0, 1)
MEASURES = ("end", "win")
GRID_DRO, GRID_DRA, GRID_REPS, GRID_STEPS = (0, 1, 2, 4, 8, 13), (1, 4, 8, 13), 10, 5000
SORT_RO, SORT_REPS, SORT_STEPS = 6.0, 30, 5000
SORTS = {"speed": (1, 0.2, (0.76, -0.22)), "rr": (2, 0.3, (-0.44, -0.57))}
WORKERS = 2

# Figure 4 read by eye from a 300-dpi render (to about 0.02): r_o = 1, 1.25, ..., 4 rising; 1, ..., 3.75 falling
FIG4 = {
    "p_up": [0.165, 0.23, 0.225, 0.22, 0.255, 0.245, 0.27, 0.42, 0.685, 0.86, 0.905, 0.905, 0.91],
    "m_up": [0.25, 0.485, 0.87, 0.93, 0.945, 0.945, 0.90, 0.68, 0.375, 0.165, 0.065, 0.09, 0.085],
    "p_down": [0.17, 0.21, 0.89, 0.915, 0.915, 0.92, 0.925, 0.92, 0.91, 0.905, 0.915, 0.90],
    "m_down": [0.25, 0.48, 0.20, 0.12, 0.105, 0.10, 0.09, 0.09, 0.075, 0.07, 0.065, 0.085],
}

TEST = ("Refuted if, in the paper's model (N = 100, r_r = 1, r_a = 14, alpha = 270, theta = 40 deg/s, s = 3, sigma = "
        "0.05 rad, tau = 0.1 s), r_o raised from 1 to 4 and lowered back in steps of 0.25, 2,000 steps at each, 15 "
        "replicates of unfragmented groups, under none of the readings its open details allow do the rising sweep's "
        "means show a torus (m_group >= 0.6, p_group <= 0.4) and the falling sweep's a polarized group (p_group >= "
        "0.7, m_group <= 0.3) at r_o = 1.75, 2 and 2.25, with p_group <= 0.4 at r_o = 1 on both and >= 0.7 at 4.")


class Refused(Exception):
    pass


def seed64(seed, label):
    return int.from_bytes(hashlib.sha256(f"{seed}/{label}/rng".encode()).digest()[:8], "big")


def code(reading):
    s, u, z = reading
    return f"{'s' if s else 'n'}{'u' if u else 'r'}{z}"


def ro_value(k):
    return RO_LO + RO_STEP * k


# ---------------------------------------------------------------- the C program

def build(work):
    exe = os.path.join(work, "couzin")
    subprocess.run(["gcc", "-O2", "-std=c99", "-ffp-contract=off", "-o", exe, SOURCE, "-lm"], check=True)
    return exe


def c_run(exe, work, params, mode, tag):
    path = os.path.join(work, f"params-{tag}.txt")
    with open(path, "w") as fh:
        for k, v in params.items():
            fh.write(f"{k} {v}\n")
    out = subprocess.run([exe, mode, path], check=True, capture_output=True, text=True).stdout
    os.remove(path)
    res = {"up": {}, "down": {}, "grid": None, "t0": [], "t1": [], "ind": [], "m": []}
    for line in out.splitlines():
        f = line.split()
        if f[0] in ("up", "down", "grid"):
            rec = {"ro": float(f[2]), "p": float(f[3]), "m": float(f[4]), "pw": float(f[5]), "mw": float(f[6]),
                   "classes": int(f[7])}
            if f[0] == "grid":
                res["grid"] = rec
            else:
                res[f[0]][int(f[1])] = rec
        elif f[0] in ("t0", "t1"):
            res[f[0]].append(tuple(float(x) for x in f[2:8]))
        elif f[0] == "pm":
            res["pm"] = (float(f[1]), float(f[2]), int(f[3]))
        elif f[0] == "state":
            res["state"] = (float(f[1]), float(f[2]), int(f[3]))
        elif f[0] == "ind":
            res["ind"].append(tuple(float(x) for x in f[2:10]))
        elif f[0] == "noise":
            res["noise"] = (float(f[1]), float(f[2]), int(f[3]))
        elif f[0] == "m":
            res["m"].append(tuple(float(x) for x in f[1:6]))
    return res


def base_params(reading, seed, **kw):
    s, u, z = reading
    p = {"N": N, "rr": RR, "ro": RO_LO, "ra": RA, "alpha": ALPHA, "theta": THETA, "speed": SPEED, "sigma": SIGMA,
         "tau": TAU, "r0": R0, "self": s, "normed": u, "noise": z, "seed": seed}
    p.update(kw)
    return p


# ---------------------------------------------------------------- the plain implementation (controls, tests)

MASK = (1 << 64) - 1
LN2 = 0.6931471805599453
PI = 3.141592653589793


class Rng:
    def __init__(self, seed):
        self.s = []
        x = seed
        for _ in range(4):
            x = (x + 0x9E3779B97F4A7C15) & MASK
            z = x
            z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & MASK
            z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & MASK
            self.s.append(z ^ (z >> 31))
        self.have = False
        self.spare = 0.0

    @staticmethod
    def rotl(x, k):
        return ((x << k) | (x >> (64 - k))) & MASK

    def next(self):
        s = self.s
        res = (self.rotl((s[1] * 5) & MASK, 7) * 9) & MASK
        t = (s[1] << 17) & MASK
        s[2] ^= s[0]
        s[3] ^= s[1]
        s[1] ^= s[2]
        s[0] ^= s[3]
        s[2] ^= t
        s[3] = self.rotl(s[3], 45)
        return res

    def uni(self):
        return (self.next() >> 11) * (1.0 / 9007199254740992.0)

    def gauss(self):
        if self.have:
            self.have = False
            return self.spare
        while True:
            u = 2.0 * self.uni() - 1.0
            v = 2.0 * self.uni() - 1.0
            s = u * u + v * v
            if not (s >= 1.0 or s == 0.0):
                break
        f = math.sqrt(-2.0 * dlog(s) / s)
        self.spare = v * f
        self.have = True
        return u * f


def dlog(x):
    m, e = math.frexp(x)
    if m < 0.7071067811865476:
        m = m * 2.0
        e = e - 1
    z = (m - 1.0) / (m + 1.0)
    z2 = z * z
    s = 1.0 / 29.0
    for k in range(27, 0, -2):
        s = s * z2 + 1.0 / float(k)
    return 2.0 * z * s + float(e) * LN2


def dsincos(x):
    if abs(x) > 1.0:
        s2, c2 = dsincos(0.5 * x)
        return 2.0 * s2 * c2, 1.0 - 2.0 * s2 * s2
    x2 = x * x
    ps = 1.0
    for k in range(24, 1, -2):
        ps = 1.0 - x2 / (float(k) * float(k + 1)) * ps
    pc = 1.0
    for k in range(23, 0, -2):
        pc = 1.0 - x2 / (float(k) * float(k + 1)) * pc
    return x * ps, pc


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def vnorm(a):
    return math.sqrt(a[0] * a[0] + a[1] * a[1] + a[2] * a[2])


def unit(a):
    n = vnorm(a)
    return [a[0] / n, a[1] / n, a[2] / n]


def cross(a, b):
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]


def basis(d):
    a0, a1, a2 = abs(d[0]), abs(d[1]), abs(d[2])
    ax = [0.0, 0.0, 0.0]
    if a0 <= a1 and a0 <= a2:
        ax[0] = 1.0
    elif a1 <= a2:
        ax[1] = 1.0
    else:
        ax[2] = 1.0
    e1 = unit(cross(ax, d))
    e2 = unit(cross(d, e1))
    return e1, e2


class Model:
    """Rule 1 written plainly: every pair visited from both sides, in index order."""

    def __init__(self, n, seed, ro=RO_LO, ra=RA, alpha=ALPHA, theta=THETA, speed=SPEED, sigma=SIGMA, tau=TAU, r0=R0,
                 rr=RR, reading=LITERAL, vary=0, vary_sd=0.0, aligned=0, spread=0.0):
        self.n, self.ro, self.ra, self.sigma, self.tau = n, ro, ra, sigma, tau
        self.self_in, self.normed, self.noise = reading
        self.cos_half = dsincos(alpha / 2.0 * PI / 180.0)[1]
        if alpha >= 360.0:
            self.cos_half = -2.0
        self.sinT, self.cosT = dsincos(theta * tau * PI / 180.0)
        self.rng = Rng(seed)
        self.rr = [rr] * n
        self.sp = [speed] * n
        while True:
            self.c, self.v = [], []
            for i in range(n):
                if aligned:
                    self.c.append([0.0, spread * float(i), 0.0])
                    self.v.append([1.0, 0.0, 0.0])
                    continue
                while True:
                    x = 2.0 * self.rng.uni() - 1.0
                    y = 2.0 * self.rng.uni() - 1.0
                    z = 2.0 * self.rng.uni() - 1.0
                    if not (x * x + y * y + z * z > 1.0):
                        break
                self.c.append([r0 * x, r0 * y, r0 * z])
                while True:
                    g = [self.rng.gauss(), self.rng.gauss(), self.rng.gauss()]
                    ng = vnorm(g)
                    if ng != 0.0:
                        break
                self.v.append([g[0] / ng, g[1] / ng, g[2] / ng])
            if aligned or all(self.detects_one(i) for i in range(n)):
                break
        if vary:
            for i in range(n):
                while True:
                    x = (speed if vary == 1 else rr) + vary_sd * self.rng.gauss()
                    if not (x <= 0.0 or (vary == 2 and x >= ro)):
                        break
                if vary == 1:
                    self.sp[i] = x
                else:
                    self.rr[i] = x

    def detects_one(self, i):
        ra2 = self.ra * self.ra
        for j in range(self.n):
            if j == i:
                continue
            r = [self.c[j][k] - self.c[i][k] for k in range(3)]
            d2 = dot(r, r)
            if d2 > ra2:
                continue
            dist = math.sqrt(d2)
            u = [r[0] / dist, r[1] / dist, r[2] / dist]
            if dist < self.rr[i] or dot(self.v[i], u) >= self.cos_half:
                return True
        return False

    def noisy(self, dd):
        if self.sigma == 0.0:
            return dd
        e1, e2 = basis(dd)
        if self.noise == 1:
            phi = self.sigma * self.rng.gauss()
            while True:
                g1, g2 = self.rng.gauss(), self.rng.gauss()
                w = [g1 * e1[k] + g2 * e2[k] for k in range(3)]
                nw = vnorm(w)
                if nw != 0.0:
                    break
            w = [w[k] / nw for k in range(3)]
            sn, cs = dsincos(phi)
        else:
            g1, g2 = self.rng.gauss(), self.rng.gauss()
            w = [self.sigma * g1 * e1[k] + self.sigma * g2 * e2[k] for k in range(3)]
            a = vnorm(w)
            if a == 0.0:
                return dd
            w = [w[k] / a for k in range(3)]
            sn, cs = dsincos(a)
        return unit([cs * dd[k] + sn * w[k] for k in range(3)])

    def desired(self, i):
        ra2 = self.ra * self.ra
        nr = no = na = 0
        dr, do, da = [0.0, 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]
        for j in range(self.n):
            if j == i:
                continue
            r = [self.c[j][0] - self.c[i][0], self.c[j][1] - self.c[i][1], self.c[j][2] - self.c[i][2]]
            d2 = r[0] * r[0] + r[1] * r[1] + r[2] * r[2]
            if d2 > ra2:
                continue
            dist = math.sqrt(d2)
            u = [r[0] / dist, r[1] / dist, r[2] / dist]
            if dist < self.rr[i]:
                nr += 1
                dr = [dr[k] - u[k] for k in range(3)]
            elif dot(self.v[i], u) >= self.cos_half:
                if dist < self.ro:
                    no += 1
                    do = [do[k] + self.v[j][k] for k in range(3)]
                else:
                    na += 1
                    da = [da[k] + u[k] for k in range(3)]
        if nr > 0:
            dd = dr
        else:
            o, a = do[:], da[:]
            if no > 0 and self.self_in:
                o = [o[k] + self.v[i][k] for k in range(3)]
            if self.normed:
                n_o, n_a = vnorm(o), vnorm(a)
                if no > 0 and n_o > 0.0:
                    o = [o[k] / n_o for k in range(3)]
                if na > 0 and n_a > 0.0:
                    a = [a[k] / n_a for k in range(3)]
            if no > 0 and na > 0:
                dd = [0.5 * (o[k] + a[k]) for k in range(3)]
            elif no > 0:
                dd = o
            elif na > 0:
                dd = a
            else:
                dd = self.v[i][:]
        if dd[0] == 0.0 and dd[1] == 0.0 and dd[2] == 0.0:
            dd = self.v[i][:]
        return self.noisy(unit(dd))

    def step(self):
        ds = [self.desired(i) for i in range(self.n)]
        for i in range(self.n):
            v, dd = self.v[i], ds[i]
            c = dot(v, dd)
            if c > self.cosT:
                nv = dd[:]
            else:
                w = [dd[k] - c * v[k] for k in range(3)]
                nw = vnorm(w)
                if nw == 0.0:
                    w = basis(v)[0]
                else:
                    w = [w[k] / nw for k in range(3)]
                nv = unit([self.cosT * v[k] + self.sinT * w[k] for k in range(3)])
            self.v[i] = nv
            ln = self.sp[i] * self.tau
            self.c[i] = [self.c[i][k] + ln * nv[k] for k in range(3)]

    def measures(self):
        return measures(self.c, self.v)

    def classes(self):
        return classes(self.c, self.v, self.rr, self.ra, self.cos_half)


def measures(c, v):
    n = len(c)
    sv, cg, sm = [0.0, 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]
    for i in range(n):
        for k in range(3):
            sv[k] = sv[k] + v[i][k]
            cg[k] = cg[k] + c[i][k]
    cg = [cg[k] / float(n) for k in range(3)]
    for i in range(n):
        r = [c[i][0] - cg[0], c[i][1] - cg[1], c[i][2] - cg[2]]
        nr = vnorm(r)
        if nr == 0.0:
            continue
        r = [r[k] / nr for k in range(3)]
        x = cross(r, v[i])
        sm = [sm[k] + x[k] for k in range(3)]
    return vnorm(sv) / float(n), vnorm(sm) / float(n)


def classes(c, v, rr, ra, cos_half):
    n = len(c)
    parent = list(range(n))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    count = n
    ra2 = ra * ra
    for i in range(n):
        for j in range(i + 1, n):
            r = [c[j][k] - c[i][k] for k in range(3)]
            d2 = dot(r, r)
            if d2 > ra2:
                continue
            dist = math.sqrt(d2)
            u = [r[0] / dist, r[1] / dist, r[2] / dist]
            w = [-u[0], -u[1], -u[2]]
            if dist < rr[i] or dist < rr[j] or dot(v[i], u) >= cos_half or dot(v[j], w) >= cos_half:
                a, b = find(i), find(j)
                if a != b:
                    parent[a] = b
                    count -= 1
    return count


# ---------------------------------------------------------------- statistics and the decision

def mean_se(xs):
    n = len(xs)
    if n == 0:
        return None, None
    m = math.fsum(xs) / n
    if n < 2:
        return m, 0.0
    var = math.fsum((x - m) ** 2 for x in xs) / (n - 1)
    return m, math.sqrt(var / n)


def curves(runs, measure):
    """runs: list of C sweep results (one per replicate). Returns {dir: {k: (p, m, counted, p_se, m_se)}}."""
    out = {"up": {}, "down": {}}
    for d in ("up", "down"):
        ks = sorted(runs[0][d])
        for k in ks:
            recs = [r[d][k] for r in runs if r[d][k]["classes"] == 1]
            ps = [x["p"] if measure == "end" else x["pw"] for x in recs]
            ms = [x["m"] if measure == "end" else x["mw"] for x in recs]
            pm, pse = mean_se(ps)
            mm, mse = mean_se(ms)
            out[d][k] = (pm, mm, len(recs), pse, mse)
    return out


def k_of(ro):
    k = round((ro - RO_LO) / RO_STEP)
    if abs(ro_value(k) - ro) > 1e-12:
        raise ValueError(ro)
    return k


def decide(cv):
    """cv: {"up": {k: (p, m, counted, ...)}, "down": {k: ...}} with the top value under "up" only.
    Returns (conditions met, {name: bool})."""
    cond = {}

    def ok(d, k):
        rec = cv[d].get(k)
        return rec is not None and rec[2] >= MIN_COUNTED and rec[0] is not None

    top = N_UP - 1
    for ro in CORE:
        k = k_of(ro)
        up, dn = cv["up"].get(k), cv["down"].get(k)
        cond[f"rising m >= {TORUS_M} at {ro}"] = ok("up", k) and up[1] >= TORUS_M
        cond[f"rising p <= {TORUS_P} at {ro}"] = ok("up", k) and up[0] <= TORUS_P
        cond[f"falling p >= {PAR_P} at {ro}"] = ok("down", k) and dn[0] >= PAR_P
        cond[f"falling m <= {PAR_M} at {ro}"] = ok("down", k) and dn[1] <= PAR_M
    cond[f"rising p <= {LOW_P} at 1"] = ok("up", 0) and cv["up"][0][0] <= LOW_P
    cond[f"falling p <= {LOW_P} at 1"] = ok("down", 0) and cv["down"][0][0] <= LOW_P
    cond[f"p >= {HIGH_P} at 4"] = ok("up", top) and cv["up"][top][0] >= HIGH_P
    return sum(cond.values()), cond


def figure_curves():
    up = {k: (FIG4["p_up"][k], FIG4["m_up"][k], REPLICATES) for k in range(N_UP)}
    down = {k: (FIG4["p_down"][k], FIG4["m_down"][k], REPLICATES) for k in range(N_UP - 1)}
    return {"up": up, "down": down}


def ranks(xs):
    order = sorted(range(len(xs)), key=lambda i: (xs[i], i))
    r = [Fraction(0)] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        avg = Fraction(i + j + 2, 2)
        for t in range(i, j + 1):
            r[order[t]] = avg
        i = j + 1
    return r


def spearman(xs, ys):
    rx, ry = ranks(xs), ranks(ys)
    n = len(xs)
    mx, my = sum(rx) / n, sum(ry) / n
    sxy = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    sxx = sum((a - mx) ** 2 for a in rx)
    syy = sum((b - my) ** 2 for b in ry)
    return float(sxy) / math.sqrt(float(sxx) * float(syy))


def sorting_rho(inds, which):
    """inds: (speed, rr, cx, cy, cz, vx, vy, vz) per individual. Spearman of the varied parameter against frontness
    and centrality."""
    n = len(inds)
    cg = [math.fsum(x[2 + k] for x in inds) / n for k in range(3)]
    dg = unit([math.fsum(x[5 + k] for x in inds) / n for k in range(3)])
    par = [x[0] if which == "speed" else x[1] for x in inds]
    front = [dot([x[2] - cg[0], x[3] - cg[1], x[4] - cg[2]], dg) for x in inds]
    centre = [-vnorm([x[2] - cg[0], x[3] - cg[1], x[4] - cg[2]]) for x in inds]
    return spearman(par, front), spearman(par, centre)


def expected_noise(reading_noise, sigma=SIGMA, theta=THETA, tau=TAU):
    """Exact E[sin A'], E[1 - cos A'] and their s.d.s, A' = min(A, theta*tau), A the noise angle."""
    cap = theta * tau * math.pi / 180.0

    def dens(a):
        if reading_noise == 1:
            return math.sqrt(2.0 / math.pi) / sigma * math.exp(-a * a / (2 * sigma * sigma))
        return a / (sigma * sigma) * math.exp(-a * a / (2 * sigma * sigma))

    tail = math.erfc(cap / (sigma * math.sqrt(2))) if reading_noise == 1 else math.exp(-cap * cap / (2 * sigma * sigma))
    n = 4000
    h = cap / n
    out = []
    for g in (math.sin, lambda a: 1.0 - math.cos(a)):
        mom = []
        for pw in (1, 2):
            s = dens(0.0) * g(0.0) ** pw + dens(cap) * g(cap) ** pw
            for i in range(1, n):
                a = i * h
                s += (4 if i % 2 else 2) * dens(a) * g(a) ** pw
            mom.append(s * h / 3 + tail * g(cap) ** pw)
        out.append((mom[0], math.sqrt(max(mom[1] - mom[0] ** 2, 0.0))))
    return out


# ---------------------------------------------------------------- controls

def ulps(a, b):
    if a == b:
        return 0
    scale = max(abs(b), 1e-300)
    return abs(a - b) / (math.ulp(scale))


def controls(exe, work, seed):
    ctl, info = {}, {}
    # (a) C against Python
    ok, cases = True, 0
    variants = [dict(reading=r) for r in READINGS]
    variants += [dict(reading=LITERAL, vary=1, vary_sd=0.4), dict(reading=LITERAL, vary=2, vary_sd=0.3),
                 dict(reading=LITERAL, alpha=360.0)]
    for t, var in enumerate(variants):
        sd = seed64(seed, f"control/a/{t}")
        reading = var.get("reading", LITERAL)
        params = base_params(reading, sd, N=12, ra=6.0, ro=2.0, r0=3.0, steps=150, vary=var.get("vary", 0),
                             vary_sd=var.get("vary_sd", 0.0), alpha=var.get("alpha", ALPHA))
        rc = c_run(exe, work, params, "trace", f"a{t}")
        m = Model(12, sd, ro=2.0, ra=6.0, r0=3.0, reading=reading, vary=var.get("vary", 0),
                  vary_sd=var.get("vary_sd", 0.0), alpha=var.get("alpha", ALPHA))
        t0 = [tuple(m.c[i] + m.v[i]) for i in range(12)]
        for _ in range(150):
            m.step()
        t1 = [tuple(m.c[i] + m.v[i]) for i in range(12)]
        p, mm = m.measures()
        same = rc["t0"] == t0 and rc["t1"] == t1 and rc["pm"] == (p, mm, m.classes())
        ok &= same
        cases += 1
    ctl["(a) C against Python, bit for bit"] = ok
    info["a_cases"] = cases
    # (b) the series
    rm = c_run(exe, work, {"seed": 1}, "math", "b")["m"]
    worst_sc, worst_log, same = 0.0, 0.0, True
    for x, sn, cs, y, lg in rm:
        ps, pc = dsincos(x)
        same &= (ps, pc, dlog(y)) == (sn, cs, lg)
        worst_sc = max(worst_sc, abs(sn - math.sin(x)) / 2.0 ** -52, abs(cs - math.cos(x)) / 2.0 ** -52)
        worst_log = max(worst_log, ulps(lg, math.log(y)))
    ctl["(b) the series against the library"] = same and worst_sc <= 8 and worst_log <= 4 and len(rm) == 2000
    info["b_worst"] = [worst_sc, worst_log]
    # (c) free flight
    rf = c_run(exe, work, base_params(LITERAL, 7, N=5, sigma=0.0, aligned=1, spread=1.0e6, steps=1000), "trace", "c")
    x = 0.0
    for _ in range(1000):
        x = x + SPEED * TAU * 1.0
    ctl["(c) free flight"] = (all(t[3:] == (1.0, 0.0, 0.0) for t in rf["t1"]) and all(t[0] == x for t in rf["t1"])
                              and rf["pm"][0] == 1.0 and rf["pm"][2] == 5)
    # (d) the noise
    good = True
    dinfo = {}
    for z in (1, 2):
        rn = c_run(exe, work, base_params((0, 0, z), seed64(seed, f"control/d/{z}"), steps=200000), "noise", f"d{z}")
        msin, mcos, n = rn["noise"]
        (es, ss), (ec, sc) = expected_noise(z)
        zs, zc = (msin - es) / (ss / math.sqrt(n)), (mcos - ec) / (sc / math.sqrt(n))
        dinfo[z] = {"mean_sin": msin, "exact_sin": es, "z_sin": zs, "mean_1mcos": mcos, "exact_1mcos": ec, "z_1mcos": zc}
        good &= abs(zs) <= 5 and abs(zc) <= 5
    ctl["(d) the noise's angles"] = good
    info["d"] = dinfo
    # (e) the measures
    ring_c = [[10.0 * math.cos(2 * math.pi * i / 100), 10.0 * math.sin(2 * math.pi * i / 100), 0.0] for i in range(100)]
    ring_v = [[-math.sin(2 * math.pi * i / 100), math.cos(2 * math.pi * i / 100), 0.0] for i in range(100)]
    pr, mr = measures(ring_c, ring_v)
    file_c = [[float(i), 0.0, 0.0] for i in range(100)]
    file_v = [[1.0, 0.0, 0.0] for _ in range(100)]
    pf, mf = measures(file_c, file_v)
    ctl["(e) the measures"] = abs(mr - 1) <= 1e-12 and pr <= 1e-12 and abs(pf - 1) <= 1e-12 and mf <= 1e-12
    info["e"] = [pr, mr, pf, mf]
    # (f) the classes
    two = [[0.0, 0.0, 0.0], [0.5, 0.0, 0.0], [100.0, 0.0, 0.0], [100.5, 0.0, 0.0]]
    vv = [[1.0, 0.0, 0.0]] * 4
    cos_half = dsincos(ALPHA / 2.0 * PI / 180.0)[1]
    ctl["(f) the classes"] = (classes(two, vv, [RR] * 4, RA, cos_half) == 2
                              and classes(two[:2], vv[:2], [RR] * 2, RA, cos_half) == 1)
    # (g) the figure's own values pass
    gm, gc = decide(figure_curves())
    ctl["(g) the decision on the figure's values: 15 of 15"] = gm == 15
    # (h) a planted fault: no memory
    fc = figure_curves()
    fc["down"] = {k: fc["up"][k] for k in range(N_UP - 1)}
    hm, hc = decide(fc)
    falling_core = [hc[f"falling p >= {PAR_P} at {ro}"] for ro in CORE] + [hc[f"falling m <= {PAR_M} at {ro}"]
                                                                          for ro in CORE]
    ctl["(h) planted: no memory fails the falling sweep's conditions"] = not any(falling_core) and hm < 15
    info["h_met"] = hm
    return ctl, info


# ---------------------------------------------------------------- the assessment

def fmt_list(xs):
    return " ".join("-" if x is None else f"{x:.2f}" for x in xs)


def f2(x):
    return "-" if x is None else f"{x:.2f}"


def assess(seed, work):
    exe = build(work)
    jobs = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as pool:
        for reading in READINGS:
            for k in range(REPLICATES):
                p = base_params(reading, seed64(seed, f"sweep/{k}"), ro_lo=RO_LO, ro_step=RO_STEP, n_up=N_UP,
                                steps_per=STEPS_PER, window=WINDOW)
                jobs[("sweep", reading, k)] = pool.submit(c_run, exe, work, p, "sweep", f"s-{code(reading)}-{k}")
        for k in range(REPLICATES):
            p = base_params(LITERAL, seed64(seed, f"sweep/{k}"), alpha=360.0, ro_lo=RO_LO, ro_step=RO_STEP,
                            n_up=N_UP, steps_per=STEPS_PER, window=WINDOW)
            jobs[("a360", LITERAL, k)] = pool.submit(c_run, exe, work, p, "sweep", f"a360-{k}")
        for ro in CORE:
            for k in range(REPLICATES):
                p = base_params(LITERAL, seed64(seed, f"fresh/{ro}/{k}"), ro=ro, steps=GRID_STEPS, window=WINDOW)
                jobs[("fresh", ro, k)] = pool.submit(c_run, exe, work, p, "grid", f"f-{ro}-{k}")
        for dro in GRID_DRO:
            for dra in GRID_DRA:
                for k in range(GRID_REPS):
                    ro = RR + dro
                    p = base_params(LITERAL, seed64(seed, f"grid/{dro}/{dra}/{k}"), ro=ro, ra=ro + dra,
                                    steps=GRID_STEPS, window=WINDOW)
                    jobs[("grid", (dro, dra), k)] = pool.submit(c_run, exe, work, p, "grid", f"g-{dro}-{dra}-{k}")
        for name, (vary, sd, _) in SORTS.items():
            for k in range(SORT_REPS):
                p = base_params(LITERAL, seed64(seed, f"sort/{name}/{k}"), ro=SORT_RO, steps=SORT_STEPS, vary=vary,
                                vary_sd=sd)
                jobs[("sort", name, k)] = pool.submit(c_run, exe, work, p, "sort", f"o-{name}-{k}")
        ctl, cinfo = controls(exe, work, seed)
        res = {key: f.result() for key, f in jobs.items()}

    # the test
    per, curves_all, frag = {}, {}, {}
    for reading in READINGS:
        runs = [res[("sweep", reading, k)] for k in range(REPLICATES)]
        for measure in MEASURES:
            cv = curves(runs, measure)
            met, cond = decide(cv)
            per[(reading, measure)] = (met, cond)
            curves_all[f"{code(reading)}-{measure}"] = {
                d: {f"{ro_value(k):.2f}": {"p": v[0], "m": v[1], "counted": v[2], "p_se": v[3], "m_se": v[4]}
                    for k, v in cv[d].items()} for d in cv}
        frag[code(reading)] = sum(1 for r in runs for d in ("up", "down") for x in r[d].values() if x["classes"] != 1)
    holding = [f"{code(r)}-{m}" for (r, m), (met, _) in per.items() if met == 15]
    best = max(met for met, _ in per.values())
    lit_met, lit_cond = per[(LITERAL, "end")]
    lit = curves([res[("sweep", LITERAL, k)] for k in range(REPLICATES)], "end")

    def series(d, idx):
        return [lit[d][k][idx] for k in sorted(lit[d])]

    gaps = []
    for d, key_p, key_m in (("up", "p_up", "m_up"), ("down", "p_down", "m_down")):
        for k in sorted(lit[d]):
            if lit[d][k][0] is not None:
                gaps.append(abs(lit[d][k][0] - FIG4[key_p][k]))
                gaps.append(abs(lit[d][k][1] - FIG4[key_m][k]))
    figure_gap = math.fsum(gaps) / len(gaps) if gaps else -1.0
    core = [k_of(ro) for ro in CORE]

    # beside: alpha = 360
    a360 = curves([res[("a360", LITERAL, k)] for k in range(REPLICATES)], "end")
    a360_met, a360_cond = decide(a360)
    a360_mmax = max((v[1] for v in a360["up"].values() if v[1] is not None), default=-1.0)
    # beside: fresh starts
    fresh = {}
    for ro in CORE:
        recs = [res[("fresh", ro, k)]["grid"] for k in range(REPLICATES)]
        cnt = [x for x in recs if x["classes"] == 1]
        fresh[ro] = (mean_se([x["p"] for x in cnt])[0], mean_se([x["m"] for x in cnt])[0], len(cnt))
    # beside: the grid
    grid = {}
    for dro in GRID_DRO:
        for dra in GRID_DRA:
            recs = [res[("grid", (dro, dra), k)]["grid"] for k in range(GRID_REPS)]
            cnt = [x for x in recs if x["classes"] == 1]
            pm_, mm_ = mean_se([x["p"] for x in cnt])[0], mean_se([x["m"] for x in cnt])[0]
            if len(cnt) * 2 < GRID_REPS:
                kind = "fragments"
            elif pm_ >= 0.9:
                kind = "highly parallel"
            elif pm_ >= 0.5:
                kind = "dynamic parallel"
            elif mm_ >= 0.5:
                kind = "torus"
            else:
                kind = "swarm"
            grid[f"{dro},{dra}"] = {"p": pm_, "m": mm_, "counted": len(cnt), "kind": kind}
    # beside: sorting
    sorting = {}
    for name, (vary, sd, fig) in SORTS.items():
        fr, ce, n_ok = [], [], 0
        for k in range(SORT_REPS):
            r = res[("sort", name, k)]
            if r["state"][2] != 1:
                continue
            n_ok += 1
            a, b = sorting_rho(r["ind"], name)
            fr.append(a)
            ce.append(b)
        sorting[name] = {"front": mean_se(fr), "centre": mean_se(ce), "counted": n_ok, "figure": fig}

    def g(ro):
        return grid[ro]["kind"]

    out = {
        "test_passed": int(best == 15),
        "conditions_met": best,
        "conditions_total": 15,
        "literal_conditions_met": lit_met,
        "readings_holding": len(holding),
        "readings_total": len(per),
        "readings": "15 of 15 under: " + (", ".join(sorted(holding)) if holding else "none"),
        "readings_counts": "end/win: " + ", ".join(f"{code(r)} {per[(r, 'end')][0]}/{per[(r, 'win')][0]}"
                                                   for r in READINGS),
        "rising_core": (f"literal, r_o 1.75/2/2.25: m {fmt_list([lit['up'][k][1] for k in core])}, "
                        f"p {fmt_list([lit['up'][k][0] for k in core])}"),
        "falling_core": (f"literal, r_o 1.75/2/2.25: p {fmt_list([lit['down'][k][0] for k in core])}, "
                         f"m {fmt_list([lit['down'][k][1] for k in core])}"),
        "ends": (f"literal p: rising at 1 {f2(lit['up'][0][0])}, falling at 1 {f2(lit['down'][0][0])}, "
                 f"at 4 {f2(lit['up'][N_UP - 1][0])}"),
        "rising_m": fmt_list(series("up", 1)),
        "rising_p": fmt_list(series("up", 0)),
        "falling_m": fmt_list(series("down", 1)),
        "falling_p": fmt_list(series("down", 0)),
        "figure_gap": round(figure_gap, 3),
        "fragmented": "fragmented replicate-values of 375: " + ", ".join(f"{k} {v}" for k, v in sorted(frag.items())),
        "fresh_starts": "random starts, 5,000 steps, literal: " + "; ".join(
            f"r_o {ro} m {f2(fresh[ro][1])} p {f2(fresh[ro][0])} ({fresh[ro][2]})" for ro in CORE),
        "alpha360": (f"alpha 360, literal: {a360_met} of 15; rising m at 1.75/2/2.25 "
                     f"{fmt_list([a360['up'][k][1] for k in core])}; largest rising m {f2(a360_mmax)}"),
        "grid": ("Fig. 3 grid (dro,dra): 0,13 " + g("0,13") + "; 1,13 " + g("1,13") + "; 4,13 " + g("4,13")
                 + "; 13,13 " + g("13,13") + "; 0,1 " + g("0,1")),
        "sorting_speed": (f"speed s.d. 0.2: rho front {f2(sorting['speed']['front'][0])}, centre "
                          f"{f2(sorting['speed']['centre'][0])} (figure 0.76, -0.22; {sorting['speed']['counted']} groups)"),
        "sorting_rr": (f"r_r s.d. 0.3: rho front {f2(sorting['rr']['front'][0])}, centre "
                       f"{f2(sorting['rr']['centre'][0])} (figure -0.44, -0.57; {sorting['rr']['counted']} groups)"),
        "controls_passed": sum(ctl.values()),
        "controls_total": len(ctl),
    }
    for k, v in out.items():
        if isinstance(v, str) and len(v) > 200:
            raise AssertionError(f"{k}: longer than 200 characters: {v}")
        if isinstance(v, float) and not math.isfinite(v):
            raise AssertionError(f"{k}: not finite")
    detail = {"test": TEST, "literal_conditions": lit_cond,
              "conditions": {f"{code(r)}-{m}": c for (r, m), (_, c) in per.items()},
              "curves": curves_all, "figure": FIG4, "alpha360": {"conditions": a360_cond, "curves": {
                  d: {f"{ro_value(k):.2f}": v[:3] for k, v in a360[d].items()} for d in a360}},
              "fresh": {str(ro): v for ro, v in fresh.items()}, "grid": grid, "sorting": sorting,
              "controls": ctl, "control_info": cinfo}
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
        sys.exit(f"couzin2002: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
