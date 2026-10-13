#!/usr/bin/env python3
"""The primordial particle system: does a life-like population of cells emerge, grow and persist?

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:8b04844b0315a05d) is from Schmickl, Stefanec &
Crailsheim, "How a life-like system emerges from a simple particle motion law", Scientific Reports 6, 37969 (2016): "We
discovered a simple motion law for moving and interacting self-propelled particles leading to a self-structuring,
self-reproducing and self-sustaining life-like system."

Its registered test: refuted if, in 16 runs of the paper's default system (r = 5, alpha = 180 degrees, beta = 17 degrees,
v = 0.67; 5,000 particles at random positions and headings in a 250 x 250 torus; each step every particle, in a fresh
random order, counts its neighbours within r on its left and right, turns by alpha + beta N sign(R - L) and moves v
forward), fewer than 8 grow from under 1 estimated cell at the start to at least 25 at step 100,000, or those runs' mean
final estimate is not within a quarter of the paper's 50.54 (cells estimated as the paper does: particles with over 15
neighbours within 5, over 48).

The paper releases no code and no data; its Method and Figure 1 (pseudo-code) define the system, and pps/pps.c (C,
compiled here into results/) runs it. This module draws the seeds, runs the controls and the 16 runs, and judges them.
Every rule below was fixed before any seed existed.

1. The system, as the Method and Figure 1 state it: 5,000 particles, each placed uniformly at random in [0, 250)^2 with
   a heading uniform in [0, 2 pi), on a torus. Each step, a fresh uniformly random order of all particles (Fisher-Yates);
   each particle in turn, seeing the others where they are at that moment, counts the others at a distance of at most
   r = 5 (on the torus) on its right (R: the side towards which a positive turn rotates its heading, where the cross
   product of heading and offset is positive) and on its left (L: where it is negative; a particle exactly ahead or
   behind is in neither), turns by alpha + beta (L + R) sign(R - L) with alpha = 180 and beta = 17 degrees, keeps its
   heading modulo 2 pi, and moves 0.67 forward, wrapped onto the torus. All in 64-bit floating point, compiled without
   contraction of multiply-adds, so that a run repeats bit for bit.
2. Randomness: run k (1 to 16) and each control draw from xoshiro256** seeded by splitmix64 from the first 8 bytes (big-
   endian) of SHA-256(the seed's 32 bytes || "|pps/" || label); uniform reals from the top 53 bits; the order's draws by
   rejection.
3. The census: at step 0 and every 2,500 steps, after all particles have moved, each particle's neighbours within 5
   (N5) and within 1.3 (N1.3) are counted. The paper's colour rule, as printed: blue 15 < N5 <= 35, else yellow N5 > 35,
   else brown 13 <= N5 <= 15, else magenta N1.3 > 15, else green. The estimated cells are the blue and yellow particles
   over 48 (the paper's particles per cell).
4. The test: a run grows if its estimate is below 1 at step 0 and at least 25 at step 100,000. test_passed is 1 if at
   least 8 of the 16 runs grow and the mean of their final estimates lies within a quarter of 50.54 (37.905 to 63.175).
5. Beside the test: the mean estimate over the runs at steps 2,500, 5,000, 10,000, 25,000, 50,000 and 100,000; the runs
   that died out (final estimate below 1); the printed rule's magenta count (no particle can be magenta under it, since
   N1.3 > 15 implies N5 > 15); and the counts read with magenta first (magenta if N1.3 > 15, then blue and yellow among
   the rest), cells over 48 and spores over 18, against the paper's 50.54 cells and 19.14 spores at step 100,000.
6. Controls, which must all pass or the run stops: the compiled program agrees bit for bit with a reference written here
   in Python (all pairs, no grid) on 60 particles in a 25 x 25 torus for 200 steps; a lone particle is back where it
   started after 2 steps and 0.67 away after 1 (alpha = 180 degrees: "isolated particles hold position within 2 time
   steps"); no census of any run finds a magenta particle under the printed rule; and the rule misread with the turn
   mirrored (alpha - beta N sign(R - L)) yields no particle with more than 35 neighbours and an estimate below 25 at step
   10,000 (pilots: about 12).

What it cannot check: the paper's own runs, which were not released, and its life cycle, replication of seeded cells and
parameter scans, which the test does not take up.

Writes results/outputs.json (the values a receipt carries) and results/detail.json (every census of every run).
"""

import hashlib
import json
import math
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SOURCE = os.path.join(HERE, "pps.c")

PARTICLES, SIDE, STEPS, EVERY, RUNS = 5000, 250.0, 100_000, 2_500, 16
RADIUS, ALPHA, BETA, SPEED = 5.0, math.pi, 17.0 * math.pi / 180.0, 0.67
CELL, SPORE = 48, 18
PAPER_CELLS, PAPER_SPORES = 50.54, 19.14
MIN_RUNS, MIN_FINAL, START_BELOW, BAND = 8, 25.0, 1.0, 0.25
CURVE = (2_500, 5_000, 10_000, 25_000, 50_000, 100_000)
FIELDS = ("t", "over15", "blue", "yellow", "brown", "magenta_printed", "magenta_first", "blue_mf", "yellow_mf")
PARALLEL = 2
LIMIT = 200
OUTPUTS = ("runs", "growing", "mean_final", "final_range", "start_max", "died_out", "mean_curve", "magenta_first",
           "printed_magenta", "band", "controls", "reference_match", "lone_particle", "mirror", "census_digest",
           "conditions_met", "conditions_total", "test_passed")


class Refused(Exception):
    pass


# ---------------------------------------------------------------- seeds and the generator (rule 2)

M64 = (1 << 64) - 1


def seed_of(seed_hex, label):
    return int.from_bytes(hashlib.sha256(bytes.fromhex(seed_hex) + b"|pps/" + label.encode("ascii")).digest()[:8], "big")


class Xoshiro:
    """xoshiro256** seeded by splitmix64, as pps.c."""

    def __init__(self, seed):
        self.s = []
        z = seed
        for _ in range(4):
            z = (z + 0x9E3779B97F4A7C15) & M64
            w = z
            w = ((w ^ (w >> 30)) * 0xBF58476D1CE4E5B9) & M64
            w = ((w ^ (w >> 27)) * 0x94D049BB133111EB) & M64
            self.s.append(w ^ (w >> 31))

    def next(self):
        s = self.s
        result = (((((s[1] * 5) & M64) << 7 | ((s[1] * 5) & M64) >> 57) & M64) * 9) & M64
        t = (s[1] << 17) & M64
        s[2] ^= s[0]
        s[3] ^= s[1]
        s[1] ^= s[2]
        s[0] ^= s[3]
        s[2] ^= t
        s[3] = ((s[3] << 45) | (s[3] >> 19)) & M64
        return result

    def unif(self):
        return (self.next() >> 11) * (1.0 / 9007199254740992.0)

    def below(self, n):
        lim = M64 - (M64 % n)
        while True:
            x = self.next()
            if x < lim:
                return x % n


# ---------------------------------------------------------------- the reference (rule 6): all pairs, no grid

def reference(seed, n, side, steps):
    """[(x, y, heading)] after the given steps, by rule 1, in Python."""
    rng = Xoshiro(seed)
    xs, ys, ph = [], [], []
    for _ in range(n):
        xs.append(rng.unif() * side)
        ys.append(rng.unif() * side)
        ph.append(rng.unif() * 2 * math.pi)

    def wrap(d):
        if d > side / 2:
            d -= side
        elif d < -side / 2:
            d += side
        return d

    for _ in range(steps):
        order = list(range(n))
        for i in range(n - 1, 0, -1):
            j = rng.below(i + 1)
            order[i], order[j] = order[j], order[i]
        for i in order:
            hx, hy = math.cos(ph[i]), math.sin(ph[i])
            left = right = 0
            for j in range(n):
                if j == i:
                    continue
                dx, dy = wrap(xs[j] - xs[i]), wrap(ys[j] - ys[i])
                if dx * dx + dy * dy > RADIUS * RADIUS:
                    continue
                cr = hx * dy - hy * dx
                if cr > 0:
                    right += 1
                elif cr < 0:
                    left += 1
            total, sg = left + right, (right > left) - (right < left)
            ph[i] = math.fmod(ph[i] + ALPHA + BETA * total * sg, 2 * math.pi)
            nx, ny = xs[i] + math.cos(ph[i]) * SPEED, ys[i] + math.sin(ph[i]) * SPEED
            nx, ny = math.fmod(nx + side, side), math.fmod(ny + side, side)
            if nx >= side:
                nx -= side
            if ny >= side:
                ny -= side
            xs[i], ys[i] = nx, ny
    return list(zip(xs, ys, ph))


def initial(seed, n, side):
    rng = Xoshiro(seed)
    return [(rng.unif() * side, rng.unif() * side, rng.unif() * 2 * math.pi) for _ in range(n)]


# ---------------------------------------------------------------- the compiled program

def build(results):
    os.makedirs(results, exist_ok=True)
    exe = os.path.join(results, "pps")
    cmd = ["gcc", "-O2", "-ffp-contract=off", "-std=gnu11", "-o", exe, SOURCE, "-lm"]
    subprocess.run(cmd, check=True)
    return exe


def trace(exe, seed, n, side, steps):
    out = subprocess.run([exe, "trace", str(seed), str(n), repr(side), str(steps)], check=True, capture_output=True,
                         text=True).stdout
    return [tuple(float.fromhex(v) for v in line.split()) for line in out.splitlines()]


def parse_census(text):
    rows = []
    for line in text.splitlines():
        parts = line.split()
        if len(parts) != len(FIELDS) or not all(re.fullmatch(r"\d+", p) for p in parts):
            raise Refused(f"census line not understood: {line!r}")
        rows.append(dict(zip(FIELDS, map(int, parts))))
    return rows


def start(exe, seed, steps, every, mirror=False, n=PARTICLES, side=SIDE):
    return subprocess.Popen([exe, "run", str(seed), str(n), repr(side), str(steps), str(every), "1" if mirror else "0"],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


def finish(proc):
    out, err = proc.communicate()
    if proc.returncode != 0:
        raise Refused(f"the simulation failed: {err.strip()}")
    return parse_census(out)


def run_all(exe, seed_hex, runs=RUNS, steps=STEPS, every=EVERY, parallel=PARALLEL):
    """{k: [census rows]} for runs 1..runs, `parallel` at a time."""
    results, pending, k = {}, [], 1
    while k <= runs or pending:
        while k <= runs and len(pending) < parallel:
            pending.append((k, start(exe, seed_of(seed_hex, f"run/{k}"), steps, every)))
            k += 1
        kk, proc = pending.pop(0)
        results[kk] = finish(proc)
    return results


# ---------------------------------------------------------------- the judgement

def estimate(row):
    return (row["blue"] + row["yellow"]) / CELL


def at(rows, t):
    for r in rows:
        if r["t"] == t:
            return r
    raise Refused(f"no census at step {t}")


def judge(series, steps=STEPS):
    """The test (rule 4) and what stands beside it (rule 5)."""
    per = {}
    for k, rows in series.items():
        first, last = estimate(at(rows, 0)), estimate(at(rows, steps))
        per[k] = {"start": first, "final": last, "grows": first < START_BELOW and last >= MIN_FINAL}
    growing = [k for k, v in per.items() if v["grows"]]
    mean_final = sum(per[k]["final"] for k in growing) / len(growing) if growing else float("nan")
    lo, hi = PAPER_CELLS * (1 - BAND), PAPER_CELLS * (1 + BAND)
    cond = {
        "at least 8 of 16 runs grow from under 1 estimated cell to at least 25": len(growing) >= MIN_RUNS,
        "their mean final estimate within a quarter of 50.54": bool(growing) and lo <= mean_final <= hi,
    }
    return per, growing, mean_final, (lo, hi), cond


def magenta_first(rows):
    return (rows["blue_mf"] + rows["yellow_mf"]) / CELL, rows["magenta_first"] / SPORE


# ---------------------------------------------------------------- the run

def controls(exe, seed_hex, series):
    out = {}
    s = seed_of(seed_hex, "control/reference")
    c, py = trace(exe, s, 60, 25.0, 200), reference(s, 60, 25.0, 200)
    same = sum(1 for a, b in zip(c, py) for u, v in zip(a, b) if u == v)
    out["reference"] = (f"{same} of {3 * len(py)}", len(c) == len(py) == 60 and same == 3 * len(py))
    s = seed_of(seed_hex, "control/lone")
    (x0, y0, _), = initial(s, 1, 25.0)
    (x1, y1, _), = trace(exe, s, 1, 25.0, 1)
    (x2, y2, _), = trace(exe, s, 1, 25.0, 2)

    def dist(ax, ay, bx, by):
        dx, dy = abs(ax - bx), abs(ay - by)
        dx, dy = min(dx, 25.0 - dx), min(dy, 25.0 - dy)
        return math.hypot(dx, dy)
    d1, d2 = dist(x0, y0, x1, y1), dist(x0, y0, x2, y2)
    out["lone particle"] = (f"{d1:.12f} after 1 step, {d2:.1e} after 2", abs(d1 - SPEED) < 1e-12 and d2 < 1e-9)
    printed = sum(r["magenta_printed"] for rows in series.values() for r in rows)
    out["printed magenta"] = (printed, printed == 0)
    mirror = finish(start(exe, seed_of(seed_hex, "control/mirror"), 10_000, 10_000, mirror=True))
    m = at(mirror, 10_000)
    out["mirror"] = (f"yellow {m['yellow']}, estimate {estimate(m):.2f} at step 10,000",
                     m["yellow"] == 0 and estimate(m) < MIN_FINAL)
    return out


def run(seed_hex, results="results", runs=RUNS, steps=STEPS, every=EVERY):
    exe = build(results)
    series = run_all(exe, seed_hex, runs, steps, every)
    ctl = controls(exe, seed_hex, series)
    failed = [k for k, (_, ok) in ctl.items() if not ok]
    if failed:
        raise Refused(f"the checker is not to be trusted: controls failed {failed}: {ctl}")
    per, growing, mean_final, (lo, hi), cond = judge(series, steps)
    finals = [v["final"] for v in per.values()]
    curve = [t for t in CURVE if t <= steps]
    mf = [magenta_first(at(series[k], steps)) for k in growing]
    lines = [f"{k}:" + ";".join(",".join(str(r[f]) for f in FIELDS) for r in series[k]) for k in sorted(series)]
    values = {
        "runs": len(series), "growing": len(growing),
        "mean_final": round(mean_final, 2) if growing else None,
        "final_range": f"{min(finals):.2f} to {max(finals):.2f}",
        "start_max": round(max(v["start"] for v in per.values()), 3),
        "died_out": sum(1 for v in finals if v < 1),
        "mean_curve": "; ".join(f"{t} {sum(estimate(at(series[k], t)) for k in series) / len(series):.1f}" for t in curve),
        "magenta_first": (f"cells {sum(c for c, _ in mf) / len(mf):.2f}, spores {sum(s for _, s in mf) / len(mf):.2f} "
                          f"(paper {PAPER_CELLS} and {PAPER_SPORES})") if mf else "no growing run",
        "printed_magenta": ctl["printed magenta"][0],
        "band": f"{lo:.3f} to {hi:.3f}",
        "controls": f"{len(ctl) - len(failed)} of {len(ctl)}",
        "reference_match": ctl["reference"][0],
        "lone_particle": ctl["lone particle"][0],
        "mirror": ctl["mirror"][0],
        "census_digest": hashlib.sha256("\n".join(lines).encode("ascii")).hexdigest()[:16],
        "conditions_met": sum(cond.values()), "conditions_total": len(cond),
        "test_passed": int(all(cond.values())),
    }
    out = {k: values[k] for k in OUTPUTS}
    for k, v in out.items():
        if isinstance(v, str) and len(v) > LIMIT:
            raise AssertionError(f"{k}: longer than {LIMIT} characters: {v}")
    detail = {"values": values, "conditions": cond, "per_run": {str(k): v for k, v in per.items()},
              "controls": {k: [str(v[0]), v[1]] for k, v in ctl.items()},
              "census": {str(k): rows for k, rows in series.items()},
              "magenta_first_per_growing_run": {str(k): magenta_first(at(series[k], steps)) for k in growing}}
    with open(os.path.join(results, "outputs.json"), "w", encoding="ascii") as fh:
        json.dump(out, fh, indent=2, sort_keys=True)
        fh.write("\n")
    with open(os.path.join(results, "detail.json"), "w", encoding="ascii") as fh:
        json.dump(detail, fh, indent=1, sort_keys=True)
        fh.write("\n")
    os.remove(os.path.join(results, "pps"))
    return out, detail


def main():
    seed = os.environ.get("ECDYSIS_SEED", "")
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        sys.exit("ECDYSIS_SEED must be the 64-hex seed the archive issued")
    try:
        out, _ = run(seed)
    except Refused as e:
        sys.exit(f"pps: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
