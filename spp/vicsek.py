"""Self-driven particles: Vicsek, Czirok, Ben-Jacob, Cohen & Shochet (1995), the exponent of the ordering transition.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:8fcb3415efefaef9) is the abstract's last
sentence of Vicsek et al., "Novel type of phase transition in a system of self-driven particles", Physical Review
Letters 75(6), 1226-1229 (1995; arXiv:cond-mat/0611743): "The transition is continuous since |v_a| is found to scale
as (eta_c - eta)^beta with beta ~ 0.45." The paper (the e-print's TeX, read as data) gives the model and the method:
N particles in a square of side L with periodic boundaries; r = 1, dt = 1, v = 0.03; random positions and directions at
t = 0; at each step each particle takes the average direction of the particles within r of it, itself included,
arctg(<sin theta>/<cos theta>), plus a noise uniform on [-eta/2, eta/2], and moves by its old velocity (its equations
1 and 2); v_a = |sum of the velocities| / (N v) (its equation 3). Its Figure 2a plots v_a against eta for N = 40, 100,
400, 4000 and 10000 (L = 3.1, 5, 10, 31.6 and 50, so a density of 4); errors near the transition, for 4000 and 10000,
"estimated from 5 runs with different initial conditions are in the range of 5%". beta came from plotting log v_a
against log[(eta_c(L) - eta)/eta_c(L)] (its Figure 3a), with eta_c(L) "such values ... for which the plots in Fig. 3
were the straightest in the relevant region", as the slope of the lines fitted: beta = 0.45 +- 0.07. Read from the
figure's PostScript (as data): its axis runs from 0.01 to 1 and the fitted line, of slope 0.46, from 0.02 to 0.50.
The text gives Figure 3a's density as 0.4, and eta_c(infinity) = 2.9 +- 0.05 "for rho = 0.4", while its sizes give 4.

Rules, committed before any run of the model at the test's size (the engine was timed, and the controls tried, on
other sizes and noises only):

1. The model (spp/vicsek.c): as the paper states it; neighbours at distance at most r = 1 by the nearest image; the
   average direction as atan2 of the summed sines and cosines; the noise (u - 1/2) eta from xoshiro256** seeded from
   the archive's seed; all directions updated from the state at time t, then each position moved by v times its old
   direction. v_a(t) is measured on the directions at the start of each step.
2. Runs: the test's size is the paper's N = 4000, L = 31.6 (density 4.006, as its Figure 2a's sizes give it; the text's
   0.4 is not run). Noises: 0.5, then 1.4 to 3.4 in steps of 0.1, then 4.5 (23 values). For each noise, 4 runs from
   independent random starts (the paper's "simplest initial conditions"), each 3,000 steps discarded and the next
   6,000 averaged; the noise's v_a is the mean of the 4 runs' averages. Beside the test, the same at N = 400, L = 10.
3. The exponent, as the paper found it: for each trial eta_c from the largest noise whose v_a is at least 0.2 to the
   smallest whose v_a is at most 0.05, in steps of 0.001, a least-squares line of ln v_a against
   ln[(eta_c - eta)/eta_c] through the noises with (eta_c - eta)/eta_c from 0.02 to 0.50 (the span of the paper's fitted
   line), at least 8 of them; eta_c(L) is the trial value whose line is straightest (the least residual variance), and
   beta the slope of that line.
4. The test's conditions, at N = 4000: C1, beta within 0.45 +- 0.07 (0.38 to 0.52); C2, the line is straight (R^2 at
   least 0.98), as a power law needs; C3, the transition is there: v_a at least 0.9 at noise 0.5 and at most 0.1 at
   4.5. The test passes when all three hold.

Beside the test, not counted: eta_c(L) and beta at N = 400; the v_a curve; the scatter between runs; and, as a check on
the averaging, v_a over the first and second halves of each measured window.

Controls (controls_passed of controls_total):
 (a) The C program against a plain Python implementation of rule 1 (40 particles in a square of 3.2, where the program
     searches by brute force, and 60 in 4.5, by cells; 200 steps at noise 0.7 and 2.6): the same positions and
     directions within 1e-9.
 (b) Cells against brute force in the C program (1000 particles in 15.8, 300 steps, noise 1.9): the same numbers, bit
     for bit.
 (c) Independent directions: at noise 2 pi (N = 400, L = 10, 2,000 steps) the mean v_a is within 3% of
     sqrt(pi / (4N)), the mean length of a sum of N random unit vectors over N.
 (d) Perfect order: at noise 0 from aligned directions (N = 400, L = 10, 500 steps) v_a stays at 1 within 1e-12.
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

HERE = os.path.dirname(os.path.abspath(__file__))
SOURCE = os.path.join(HERE, "vicsek.c")

V = 0.03
SIZES = {"test": (4000, 31.6), "beside": (400, 10.0)}
NOISES = [0.5] + [round(1.4 + 0.1 * k, 1) for k in range(21)] + [4.5]
RUNS, BURN, MEASURE, BLOCK = 4, 3000, 6000, 1000
WINDOW = (0.02, 0.50)
MIN_POINTS = 8
ETAC_STEP = 0.001
BETA, BETA_TOL = 0.45, 0.07
R2_MIN = 0.98
WORKERS = 2
TEST = ("Refuted if, in the paper's model (N particles, r = 1, v = 0.03, each taking its neighbours' mean direction plus "
        "noise uniform on [-eta/2, eta/2]) at its size N = 4000, L = 31.6, v_a averaged over 4 runs (3,000 steps "
        "discarded, 6,000 averaged) at noises 1.4 to 3.4 does not follow (eta_c - eta)^beta with beta in 0.45 +- 0.07 "
        "on a straight log-log line (R^2 >= 0.98) through (eta_c - eta)/eta_c = 0.02 to 0.5, eta_c chosen as the "
        "straightest as the paper did; or v_a is not >= 0.9 at noise 0.5 and <= 0.1 at 4.5.")


class Refused(Exception):
    pass


def seed64(seed, label):
    return int.from_bytes(hashlib.sha256(f"{seed}/{label}/rng".encode()).digest()[:8], "big")


# ---------------------------------------------------------------- the C program

def build(work):
    exe = os.path.join(work, "vicsek")
    subprocess.run(["gcc", "-O2", "-std=c99", "-o", exe, SOURCE, "-lm"], check=True)
    return exe


def c_run(exe, work, params, mode="run", tag="p"):
    path = os.path.join(work, f"params-{tag}.txt")
    with open(path, "w") as fh:
        for k, v in params.items():
            fh.write(f"{k} {v}\n")
    out = subprocess.run([exe, mode, path], check=True, capture_output=True, text=True).stdout
    res = {"blocks": [], "particles": []}
    for line in out.splitlines():
        f = line.split()
        if f[0] == "va":
            res["va"], res["va2"], res["va4"], res["n"] = float(f[1]), float(f[2]), float(f[3]), int(f[4])
        elif f[0] == "block":
            res["blocks"].append(float(f[2]))
        elif f[0] == "end":
            res["end"] = [float(f[1]), float(f[2]), float(f[3])]
        elif f[0] == "p":
            res["particles"].append((float(f[2]), float(f[3]), float(f[4])))
    os.remove(path)
    return res


# ---------------------------------------------------------------- the plain implementation (control a)

class Xoshiro:
    M = (1 << 64) - 1

    def __init__(self, x):
        self.s = []
        for _ in range(4):
            x = (x + 0x9E3779B97F4A7C15) & self.M
            z = x
            z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & self.M
            z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & self.M
            self.s.append(z ^ (z >> 31))

    @staticmethod
    def rotl(x, k):
        return ((x << k) | (x >> (64 - k))) & Xoshiro.M

    def next(self):
        s = self.s
        res = (self.rotl((s[1] * 5) & self.M, 7) * 9) & self.M
        t = (s[1] << 17) & self.M
        s[2] ^= s[0]; s[3] ^= s[1]; s[1] ^= s[2]; s[0] ^= s[3]; s[2] ^= t; s[3] = self.rotl(s[3], 45)
        return res

    def uni(self):
        return (self.next() >> 11) * 2.0 ** -53


def py_run(N, L, eta, steps, seed, v=V, r=1.0, align=0):
    """Rule 1 written plainly (neighbours by brute force); returns the final (x, y, theta) of every particle."""
    rng = Xoshiro(seed)
    x, y, th = [], [], []
    for _ in range(N):
        x.append(L * rng.uni())
        y.append(L * rng.uni())
        a = math.pi * (2 * rng.uni() - 1)
        th.append(0.0 if align else a)
    half, r2 = L / 2, r * r
    for _ in range(steps):
        sn = [math.sin(a) for a in th]
        cs = [math.cos(a) for a in th]
        new = []
        for i in range(N):
            ss = cc = 0.0
            for j in range(N):
                dx, dy = x[j] - x[i], y[j] - y[i]
                if dx > half:
                    dx -= L
                elif dx < -half:
                    dx += L
                if dy > half:
                    dy -= L
                elif dy < -half:
                    dy += L
                if dx * dx + dy * dy <= r2:
                    ss += sn[j]
                    cc += cs[j]
            new.append(math.atan2(ss, cc) + (rng.uni() - 0.5) * eta)
        for i in range(N):
            x[i] += v * cs[i]
            y[i] += v * sn[i]
            if x[i] >= L:
                x[i] -= L
            elif x[i] < 0:
                x[i] += L
            if y[i] >= L:
                y[i] -= L
            elif y[i] < 0:
                y[i] += L
            th[i] = new[i]
    return list(zip(x, y, th))


# ---------------------------------------------------------------- the exponent (rule 3)

def line(xs, ys):
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((a - mx) ** 2 for a in xs)
    sxy = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
    slope = sxy / sxx
    icpt = my - slope * mx
    rss = sum((b - icpt - slope * a) ** 2 for a, b in zip(xs, ys))
    syy = sum((b - my) ** 2 for b in ys)
    return slope, icpt, rss, (1 - rss / syy) if syy > 0 else 0.0


def exponent(curve):
    """curve: {eta: v_a}. Returns the straightest fit of rule 3, or None."""
    etas = sorted(curve)
    hi = [e for e in etas if curve[e] >= 0.2]
    lo = [e for e in etas if curve[e] <= 0.05]
    if not hi or not lo:
        return None
    a, b = max(hi), min(lo)
    if b <= a:
        return None
    best = None
    k = 0
    while True:
        ec = round(a + k * ETAC_STEP, 6)
        if ec > b + 1e-12:
            break
        k += 1
        pts = [(math.log((ec - e) / ec), math.log(curve[e])) for e in etas
               if e < ec and WINDOW[0] <= (ec - e) / ec <= WINDOW[1] and curve[e] > 0]
        if len(pts) < MIN_POINTS:
            continue
        slope, icpt, rss, r2 = line([p[0] for p in pts], [p[1] for p in pts])
        var = rss / (len(pts) - 2)
        if best is None or var < best["var"] - 1e-15:
            best = {"etac": ec, "beta": slope, "icpt": icpt, "var": var, "r2": r2, "points": len(pts)}
    return best


# ---------------------------------------------------------------- the assessment

def sweep(exe, work, seed, N, L, pool):
    jobs = {}
    for eta in NOISES:
        for k in range(RUNS):
            p = {"N": N, "L": L, "v": V, "r": 1.0, "eta": eta, "steps": MEASURE, "burn": BURN, "block": BLOCK,
                 "seed": seed64(seed, f"{N}/{eta:.2f}/{k}"), "mode": 0, "align": 0}
            jobs[(eta, k)] = pool.submit(c_run, exe, work, p, "run", f"{N}-{eta:.2f}-{k}")
    runs = {key: f.result() for key, f in jobs.items()}
    curve, spread, halves = {}, {}, {}
    for eta in NOISES:
        vals = [runs[(eta, k)]["va"] for k in range(RUNS)]
        m = sum(vals) / RUNS
        curve[eta] = m
        spread[eta] = (sum((x - m) ** 2 for x in vals) / (RUNS - 1)) ** 0.5
        h = MEASURE // BLOCK // 2
        first = sum(sum(runs[(eta, k)]["blocks"][:h]) / h for k in range(RUNS)) / RUNS
        second = sum(sum(runs[(eta, k)]["blocks"][h:]) / h for k in range(RUNS)) / RUNS
        halves[eta] = (first, second)
    return curve, spread, halves


def controls(exe, work, seed):
    ctl, info = {}, {}
    ok = True
    gaps = []
    for N, L, eta, label in ((40, 3.2, 0.7, "a1"), (60, 4.5, 2.6, "a2"), (40, 3.2, 2.6, "a3"), (60, 4.5, 0.7, "a4")):
        sd = seed64(seed, f"control/{label}")
        pc = c_run(exe, work, {"N": N, "L": L, "v": V, "r": 1.0, "eta": eta, "steps": 200, "burn": 0, "block": 200,
                               "seed": sd, "mode": 0, "align": 0}, "trace", label)["particles"]
        pp = py_run(N, L, eta, 200, sd)
        gap = max(max(abs(a - b) for a, b in zip(u, w)) for u, w in zip(pc, pp))
        gaps.append(gap)
        ok &= len(pc) == N and gap < 1e-9
    ctl["(a) C against Python"] = ok
    info["a_gaps"] = gaps
    base = {"N": 1000, "L": 15.8, "v": V, "r": 1.0, "eta": 1.9, "steps": 300, "burn": 0, "block": 100,
            "seed": seed64(seed, "control/b"), "align": 0}
    rc = c_run(exe, work, dict(base, mode=0), "trace", "b0")
    rb = c_run(exe, work, dict(base, mode=1), "trace", "b1")
    ctl["(b) cells against brute force"] = rc["particles"] == rb["particles"] and rc["va"] == rb["va"]
    rr = c_run(exe, work, {"N": 400, "L": 10.0, "v": V, "r": 1.0, "eta": 2 * math.pi, "steps": 2000, "burn": 0,
                           "block": 1000, "seed": seed64(seed, "control/c"), "mode": 0, "align": 0}, "run", "c")
    want = math.sqrt(math.pi / (4 * 400))
    ctl["(c) independent directions"] = abs(rr["va"] - want) <= 0.03 * want
    info["c"] = [rr["va"], want]
    ra = c_run(exe, work, {"N": 400, "L": 10.0, "v": V, "r": 1.0, "eta": 0.0, "steps": 500, "burn": 0, "block": 500,
                           "seed": seed64(seed, "control/d"), "mode": 0, "align": 1}, "run", "d")
    ctl["(d) perfect order"] = abs(ra["va"] - 1) <= 1e-12 and abs(ra["va2"] - 1) <= 1e-12
    info["d"] = ra["va"]
    return ctl, info


def assess(seed, work):
    exe = build(work)
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as pool:
        ctl, cinfo = controls(exe, work, seed)
        res = {name: sweep(exe, work, seed, N, L, pool) for name, (N, L) in SIZES.items()}
    curve, spread, halves = res["test"]
    fit = exponent(curve)
    fit_b = exponent(res["beside"][0])
    c1 = fit is not None and abs(fit["beta"] - BETA) <= BETA_TOL
    c2 = fit is not None and fit["r2"] >= R2_MIN
    c3 = curve[0.5] >= 0.9 and curve[4.5] <= 0.1
    cond = {"C1 beta in 0.45 +- 0.07": c1, "C2 a straight log-log line": c2, "C3 ordered at 0.5, disordered at 4.5": c3}
    met = sum(cond.values())

    def fmt(f):
        return "no fit" if f is None else (f"beta {f['beta']:.4f}, eta_c(L) {f['etac']:.3f}, {f['points']} points, "
                                           f"R^2 {f['r2']:.4f}")
    out = {
        "fit_4000": fmt(fit),
        "fit_400": fmt(fit_b),
        "beta_4000": round(fit["beta"], 4) if fit else -1,
        "etac_4000": round(fit["etac"], 3) if fit else -1,
        "curve_4000": "v_a at " + ", ".join(f"{e}: {curve[e]:.3f}" for e in (0.5, 1.5, 2.0, 2.5, 2.8, 3.0, 3.2, 3.4, 4.5)),
        "va_low_noise": round(curve[0.5], 4), "va_high_noise": round(curve[4.5], 4),
        "conditions_met": met, "conditions_total": len(cond), "test_passed": int(met == len(cond)),
        "controls_passed": sum(ctl.values()), "controls_total": len(ctl),
    }
    for k, v in out.items():
        if isinstance(v, str) and len(v) > 200:
            raise AssertionError(f"{k}: longer than 200 characters: {v}")
    detail = {"test": TEST, "conditions": cond, "controls": ctl, "control_info": cinfo, "fit": fit, "fit_400": fit_b,
              "curves": {name: {str(e): {"va": r[0][e], "sd_runs": r[1][e], "halves": r[2][e]} for e in NOISES}
                         for name, r in res.items()}}
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
        sys.exit(f"vicsek: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
