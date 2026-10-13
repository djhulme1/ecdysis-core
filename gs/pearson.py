#!/usr/bin/env python3
"""Pearson's spots in the Gray-Scott model, tracked: do they grow to a critical size and divide in two? For an
Ecdysis receipt.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:8f6f57b2c21b2a97) is from J. E. Pearson,
"Complex Patterns in a Simple System", Science 261(5118):189-192, 1993 (arXiv:patt-sol/9304003), whose abstract
says of the model's patterns: "Others consist of spots which grow until they reach a critical size at which time
they divide in two." Its registered test is rule 7 below, at every point of rule 3.

Nothing is read: the model and its start are the paper's, as its methods state them, and the points are read from
its Figure 3 (fig3.ps in the arXiv source, a PostScript file that places each label at its (k, F)). Every choice
below was fixed before any seed existed.

1. The model, the paper's equation 1: dU/dt = Du lap U - U V^2 + F (1 - U), dV/dt = Dv lap V + U V^2 - (F + k) V,
   with Du = 2e-5 and Dv = 1e-5 on a 2.5 x 2.5 square with periodic boundaries, a 256 x 256 mesh (h = 2.5/256),
   the five-point Laplacian and forward Euler with a time step of 1, for 200,000 steps, in double precision. Each
   step is the same fixed sequence of whole-array additions and multiplications (step below), each rounded once,
   so the bits are the same on any machine with IEEE doubles.
2. The start, the paper's: U = 1, V = 0 everywhere; the 20 x 20 mesh points about the centre (rows and columns
   118 to 137) at U = 1/2, V = 1/4; then every value of U and of V multiplied by 1 + 0.01 (2u - 1), u uniform on
   [0, 1) drawn from ECDYSIS_SEED by SHA-256 in counter mode (the Stream of lenia/check.py) under the label
   "gs/<point>", U's 65,536 draws then V's, in row order, u being a draw's top 53 bits over 2^53. "Perturbed with
   +-1% random noise" is read as relative noise, so V stays 0 outside the square.
3. The points: every point Figure 3 marks epsilon, zeta or lambda, the three patterns that, in the paper's words,
   "consist of blue spots": epsilon at (k, F) = (0.05, 0.01), (0.055, 0.015), (0.055, 0.02), (0.059, 0.02) (the
   point the text gives for pattern epsilon), (0.0625, 0.025) and (0.0625, 0.03); zeta at (0.06, 0.025); lambda
   at (0.065, 0.035) and (0.065, 0.04). The figure's tick labels give k = 0.03 + (x - 750)/90200 and
   F = (y - 500)/52800 for a label at (x, y); 0.059 and 0.0625 are 0.05899 and 0.06249 rounded.
4. Spots: every 100 steps, the mesh points with U < 0.5 (the paper colours U: blue near 0.2, red at 1, yellow
   between), joined by edge adjacency, across the periodic boundaries too; a spot's area is its number of mesh
   points.
5. Tracking, from each snapshot to the next: an earlier spot and a later one are linked when they share a mesh
   point. A split is an earlier spot linked to two or more later ones; a division in two is a split into exactly
   two, each linked to it alone. A spot linked one to one continues. Births (a later spot with no link), deaths
   (an earlier spot with none) and merges (a later spot linked to two or more) are counted.
6. Lineages: a spot born in a division in two that continues until it divides in two itself is a complete
   lineage. Its growth is its area at its last snapshot over its area at its first; its reproduction time is the
   steps from its first snapshot to its daughters' first.
7. The verdict at a point needs all six: (a) at least 50 divisions in two; (b) divisions in two at least 90% of
   splits; (c) at least 20 complete lineages, with median growth at least 1.5; (d) the dividing spots' areas,
   each at its last snapshot, with a coefficient of variation (population standard deviation over mean) at most
   0.25; (e) at most 1% of all spot sightings (a spot at a snapshot) larger than 1.5 times the median dividing
   area; (f) at least 20 spots at step 200,000. test_passed is 1 when all nine points pass, else 0.
8. Beside the test: a control, kappa at (0.0625, 0.05), whose stripes the paper says grow "radially outward"; if
   it passed all six, the conditions could not tell dividing spots from growing stripes, and control_ok is 1 only
   when it fails at least one. And robustness: the verdict at every point again with spots at U < 0.4 and U < 0.6
   (the same runs, three trackers).
9. What runs: ten simulations (the nine points and the control), each depending on its point and the seed alone,
   on two worker processes, gathered in a fixed order; nothing reads the clock.

What it cannot check:
- the paper's own code or colour scale: the spot threshold is a reading of its colours, and the robustness
  thresholds show how much it matters;
- the paper's figure 4 setting (a 0.5 x 0.5 square, time step 0.01), which is not run;
- other meshes or time steps (the paper reports spot checks to 1024 x 1024 and 0.01 with no qualitative change);
- the paper's sentence on over-crowding, which follows the claim in the abstract: deaths are counted, not tested.

Writes results/outputs.json, the 20 outputs the archive accepts for one receipt (strings of at most 200
characters), and results/detail.json: every count, each tracker's statistics at every point, the spot counts
every 10,000 steps, and the first divisions. The lab's README, section gs/, says what each holds and the
runtime.
"""

import os

for _var in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
    os.environ.setdefault(_var, "1")   # one thread in each of the two worker processes

import hashlib  # noqa: E402
import json  # noqa: E402
import multiprocessing  # noqa: E402
import re  # noqa: E402
import sys  # noqa: E402

import numpy as np  # noqa: E402
from scipy import ndimage  # noqa: E402

N = 256                  # mesh points on a side
SIDE = 2.5               # the square's side
H = SIDE / N             # 2.5/256 = 5/512, exact in binary
DU, DV = 2e-5, 1e-5
CU, CV = DU / (H * H), DV / (H * H)   # dt = 1
STEPS = 200_000
EVERY = 100              # steps between snapshots
SQUARE = (N // 2 - 10, N // 2 + 10)  # rows and columns 118..137
NOISE = 0.01             # +-1%, relative
THRESHOLD = 0.5          # a spot: U < 0.5
ROBUST = (0.4, 0.6)
WORKERS = 2
LIMIT = 200              # the archive's longest string output

# The rule 7 thresholds.
MIN_DIVISIONS = 50
MIN_TWO = 0.9
MIN_LINEAGES = 20
MIN_GROWTH = 1.5
MAX_CV = 0.25
OVERSIZE, MAX_OVERSIZE = 1.5, 0.01
MIN_END = 20

# (name, k, F): the nine points of rule 3, then the control of rule 8.
POINTS = (
    ("epsilon-1", 0.05, 0.01), ("epsilon-2", 0.055, 0.015), ("epsilon-3", 0.055, 0.02),
    ("epsilon-4", 0.059, 0.02), ("epsilon-5", 0.0625, 0.025), ("epsilon-6", 0.0625, 0.03),
    ("zeta", 0.06, 0.025), ("lambda-1", 0.065, 0.035), ("lambda-2", 0.065, 0.04),
)
CONTROL = ("kappa", 0.0625, 0.05)
OUT_NAME = {name: name.replace("-", "_") for name, _, _ in POINTS}
CONDITIONS = ("divisions", "in_two", "growth", "critical", "oversize", "spots_at_end")

# The 20 values results/outputs.json carries (the archive accepts at most 20 per receipt).
OUTPUTS = (
    "epsilon_1", "epsilon_2", "epsilon_3", "epsilon_4", "epsilon_5", "epsilon_6", "zeta", "lambda_1", "lambda_2",
    "points_passed", "divisions_in_two", "fraction_in_two_min", "growth_median_min", "cv_max", "control",
    "control_ok", "robust_u04_u06", "conditions_met", "conditions_total", "test_passed",
)


class Stream:
    """As in lenia/check.py: SHA-256(seed || "|" || label || "|" || counter), 8 bytes at a time."""

    def __init__(self, seed_hex, label):
        self.seed, self.label, self.counter = bytes.fromhex(seed_hex), label.encode("ascii"), 0

    def uniforms(self, n):
        """n draws u in [0, 1): each 8-byte draw, big-endian, shifted right by 11 bits and scaled by 2^-53."""
        blocks = []
        need = -(-8 * n // 32)
        for _ in range(need):
            blocks.append(hashlib.sha256(self.seed + b"|" + self.label + b"|" +
                                         str(self.counter).encode("ascii")).digest())
            self.counter += 1
        x = np.frombuffer(b"".join(blocks)[:8 * n], dtype=">u8").astype(np.uint64)
        return (x >> np.uint64(11)).astype(np.float64) * 2.0 ** -53


# ---------------------------------------------------------------- the model

def start(seed_hex, name):
    """Rule 2: the paper's start, with the seed's +-1% relative noise under the label gs/<name>."""
    U = np.ones((N, N))
    V = np.zeros((N, N))
    a, b = SQUARE
    U[a:b, a:b] = 0.5
    V[a:b, a:b] = 0.25
    u = Stream(seed_hex, f"gs/{name}").uniforms(2 * N * N)
    U *= 1.0 + NOISE * (2.0 * u[:N * N].reshape(N, N) - 1.0)
    V *= 1.0 + NOISE * (2.0 * u[N * N:].reshape(N, N) - 1.0)
    return U, V


def laplacian_into(X, out):
    """The five-point sum, X's four neighbours minus 4 X, with periodic wrap (not yet divided by h^2)."""
    np.multiply(X, -4.0, out=out)
    out[1:] += X[:-1]
    out[:1] += X[-1:]
    out[:-1] += X[1:]
    out[-1:] += X[:1]
    out[:, 1:] += X[:, :-1]
    out[:, :1] += X[:, -1:]
    out[:, :-1] += X[:, 1:]
    out[:, -1:] += X[:, :1]


class Model:
    """U and V and four work arrays; step() advances one forward-Euler step of time 1, in place."""

    def __init__(self, U, V, F, k):
        self.U, self.V, self.F, self.fk = U, V, F, F + k
        self.a, self.b, self.uvv, self.tmp = (np.empty((N, N)) for _ in range(4))

    def step(self, n=1):
        U, V, a, b, uvv, tmp, F, fk = self.U, self.V, self.a, self.b, self.uvv, self.tmp, self.F, self.fk
        for _ in range(n):
            laplacian_into(U, a)
            laplacian_into(V, b)
            np.multiply(U, V, out=uvv)
            uvv *= V                      # U V^2
            a *= CU                       # Du lap U
            a -= uvv
            np.subtract(1.0, U, out=tmp)
            tmp *= F
            a += tmp                      # + F (1 - U)
            b *= CV                       # Dv lap V
            b += uvv
            np.multiply(V, fk, out=tmp)
            b -= tmp                      # - (F + k) V
            U += a
            V += b


# ---------------------------------------------------------------- spots and their tracking

def spots(mask):
    """Rule 4: label the True points of mask by edge adjacency on the torus. Labels 1..n in order of each spot's
    first point in row order; returns (labels, n)."""
    lab, n = ndimage.label(mask)
    parent = list(range(n + 1))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for p, q in ((lab[0, :], lab[-1, :]), (lab[:, 0], lab[:, -1])):
        for x, y in zip(p.tolist(), q.tolist()):
            if x and y:
                rx, ry = find(x), find(y)
                if rx != ry:
                    parent[max(rx, ry)] = min(rx, ry)
    remap = np.zeros(n + 1, dtype=np.int64)
    count = 0
    for i in range(1, n + 1):      # ndimage numbers labels by first point in row order; a root is its set's least
        if find(i) == i:
            count += 1
            remap[i] = count
    for i in range(1, n + 1):
        remap[i] = remap[find(i)]
    return remap[lab], count


class Tracker:
    """Rules 5 and 6 for one threshold: fed each snapshot's labels in turn."""

    def __init__(self):
        self.prev = None                # (labels, n, areas, step)
        self.lineage = {}               # spot -> (born, first area, first step)
        self.counts = {"splits": 0, "divisions": 0, "births": 0, "deaths": 0, "merges": 0}
        self.dividing = []              # each dividing spot's area at its last snapshot
        self.daughters = []
        self.growth = []                # complete lineages: (first area, last area, reproduction time)
        self.sightings = []             # every spot's area at every snapshot
        self.first = []                 # the first divisions: (step, parent area, daughters' areas)
        self.n = []                     # (step, spots)

    def see(self, lab, n, step):
        areas = np.bincount(lab.ravel(), minlength=n + 1)
        self.sightings.extend(areas[1:].tolist())
        self.n.append((step, n))
        lineage = {}
        if self.prev is None:
            for c in range(1, n + 1):
                lineage[c] = ("start", int(areas[c]), step)
        else:
            plab, pn, pareas, pstep = self.prev
            both = (plab > 0) & (lab > 0)
            pairs = np.unique(plab[both].astype(np.int64) * (n + 1) + lab[both])
            kids, pars = {}, {}
            for v in pairs.tolist():
                p, c = divmod(v, n + 1)
                kids.setdefault(p, []).append(c)
                pars.setdefault(c, []).append(p)
            divided = set()
            for p in range(1, pn + 1):
                ks = kids.get(p, [])
                if not ks:
                    self.counts["deaths"] += 1
                elif len(ks) >= 2:
                    self.counts["splits"] += 1
                    if len(ks) == 2 and all(pars[c] == [p] for c in ks):
                        self.counts["divisions"] += 1
                        divided.add(p)
                        self.dividing.append(int(pareas[p]))
                        self.daughters.extend(int(areas[c]) for c in ks)
                        if len(self.first) < 8:
                            self.first.append((step, int(pareas[p]), [int(areas[c]) for c in ks]))
                        born, area0, step0 = self.lineage[p]
                        if born == "division":
                            self.growth.append((area0, int(pareas[p]), step - step0))
            for c in range(1, n + 1):
                ps = pars.get(c, [])
                if not ps:
                    self.counts["births"] += 1
                    lineage[c] = ("birth", int(areas[c]), step)
                elif len(ps) >= 2:
                    self.counts["merges"] += 1
                    lineage[c] = ("other", int(areas[c]), step)
                elif ps[0] in divided:
                    lineage[c] = ("division", int(areas[c]), step)
                elif kids[ps[0]] == [c]:
                    lineage[c] = self.lineage[ps[0]]
                else:
                    lineage[c] = ("other", int(areas[c]), step)
        self.lineage = lineage
        self.prev = (lab, n, areas, step)

    def summary(self):
        d = np.array(self.dividing, dtype=np.float64)
        g = np.array([b / a for a, b, _ in self.growth], dtype=np.float64)
        t = np.array([s for _, _, s in self.growth], dtype=np.float64)
        median_div = float(np.median(d)) if d.size else 0.0
        sightings = np.array(self.sightings, dtype=np.float64)
        over = int(np.count_nonzero(sightings > OVERSIZE * median_div)) if d.size else 0
        return {
            **self.counts,
            "lineages": int(g.size),
            "growth_median": float(np.median(g)) if g.size else 0.0,
            "reproduction_median": float(np.median(t)) if t.size else 0.0,
            "dividing_mean": float(d.mean()) if d.size else 0.0,
            "dividing_median": median_div,
            "dividing_cv": float(d.std() / d.mean()) if d.size else 0.0,
            "daughters_mean": float(np.mean(self.daughters)) if self.daughters else 0.0,
            "sightings": int(sightings.size),
            "oversize": over,
            "oversize_fraction": over / sightings.size if sightings.size else 0.0,
            "largest": int(sightings.max()) if sightings.size else 0,
            "spots_at_end": self.n[-1][1] if self.n else 0,
            "peak": max(m for _, m in self.n) if self.n else 0,
            "first": self.first,
            "counts": [m for s, m in self.n if s % 10_000 == 0],
        }


def conditions(s):
    """Rule 7 on one tracker's summary, keyed as CONDITIONS."""
    return {
        "divisions": s["divisions"] >= MIN_DIVISIONS,
        "in_two": s["splits"] > 0 and s["divisions"] >= MIN_TWO * s["splits"],
        "growth": s["lineages"] >= MIN_LINEAGES and s["growth_median"] >= MIN_GROWTH,
        "critical": s["divisions"] > 0 and s["dividing_cv"] <= MAX_CV,
        "oversize": s["sightings"] > 0 and s["oversize"] <= MAX_OVERSIZE * s["sightings"],
        "spots_at_end": s["spots_at_end"] >= MIN_END,
    }


# ---------------------------------------------------------------- one point

def simulate(job):
    """One point under the seed: the model for STEPS steps, three trackers (U < 0.5, then the two of ROBUST)."""
    seed, name, k, F, steps = job
    U, V = start(seed, name)
    model = Model(U, V, F, k)
    thresholds = (THRESHOLD,) + ROBUST
    trackers = [Tracker() for _ in thresholds]
    for step in range(EVERY, steps + 1, EVERY):
        model.step(EVERY)
        if not (np.isfinite(model.U).all() and np.isfinite(model.V).all()):
            raise FloatingPointError(f"{name}: a non-finite value by step {step}")
        for thr, tr in zip(thresholds, trackers):
            tr.see(*spots(model.U < thr), step)
    return {"name": name, "k": k, "F": F, "steps": steps,
            "trackers": {f"U<{thr}": tr.summary() for thr, tr in zip(thresholds, trackers)}}


def run_all(jobs):
    """Every job's result in the order of jobs, on two workers (or serially if no pool can start)."""
    pool = None
    try:
        pool = multiprocessing.get_context("fork").Pool(WORKERS)
        done = pool.imap(simulate, jobs, chunksize=1)
    except (OSError, ValueError, ImportError) as e:
        print(f"gs/pearson.py: no worker pool ({e}); running serially", file=sys.stderr)
        done = map(simulate, jobs)
    results = []
    try:
        for r in done:
            results.append(r)
            print(f"gs/pearson.py: {r['name']} done ({len(results)} of {len(jobs)})", file=sys.stderr)
    finally:
        if pool is not None:
            pool.terminate()
            pool.join()
    return results


def line(r, key=f"U<{THRESHOLD}"):
    """One point's result in at most 200 characters."""
    s = r["trackers"][key]
    met = conditions(s)
    frac = s["divisions"] / s["splits"] if s["splits"] else 0.0
    text = (f"k {r['k']} F {r['F']}: {s['divisions']} of {s['splits']} splits in two ({frac:.3f}); growth "
            f"{s['growth_median']:.2f} (n {s['lineages']}); dividing {s['dividing_mean']:.1f} cv "
            f"{s['dividing_cv']:.3f}; over 1.5x {s['oversize_fraction']:.4f}; end {s['spots_at_end']}; "
            f"{sum(met.values())} of 6")
    return text[:LIMIT]


def run(seed, results="results", steps=STEPS, points=POINTS, control=CONTROL, log=sys.stderr):
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        sys.exit("ECDYSIS_SEED must be the 64-hex seed the archive issued")
    jobs = [(seed, name, k, F, steps) for name, k, F in tuple(points) + (control,)]
    out_runs = run_all(jobs)
    runs, ctl = out_runs[:-1], out_runs[-1]
    key = f"U<{THRESHOLD}"
    met = [conditions(r["trackers"][key]) for r in runs]
    passed = [all(m.values()) for m in met]
    ctl_met = conditions(ctl["trackers"][key])
    robust = []
    for thr in ROBUST:
        robust.append(sum(all(conditions(r["trackers"][f"U<{thr}"]).values()) for r in runs))
    s = [r["trackers"][key] for r in runs]
    values = {OUT_NAME[r["name"]]: line(r) for r in runs}
    values.update({
        "points_passed": sum(passed),
        "divisions_in_two": sum(x["divisions"] for x in s),
        "fraction_in_two_min": round(min(x["divisions"] / x["splits"] if x["splits"] else 0.0 for x in s), 4),
        "growth_median_min": round(min(x["growth_median"] for x in s), 3),
        "cv_max": round(max(x["dividing_cv"] for x in s), 4),
        "control": line(ctl),
        "control_ok": 0 if all(ctl_met.values()) else 1,
        "robust_u04_u06": f"{robust[0]} and {robust[1]} of {len(runs)} points pass at U < 0.4 and U < 0.6",
        "conditions_met": sum(sum(m.values()) for m in met),
        "conditions_total": len(CONDITIONS) * len(runs),
        "test_passed": 1 if all(passed) else 0,
    })
    out = {k: values.get(k, "not run") for k in OUTPUTS}   # "not run" only when points is a part of POINTS
    detail = {"rules": {"N": N, "side": SIDE, "Du": DU, "Dv": DV, "steps": steps, "every": EVERY,
                        "threshold": THRESHOLD, "robust": list(ROBUST)},
              "points": [{**r, "conditions": {f"U<{thr}": conditions(r["trackers"][f"U<{thr}"])
                                              for thr in (THRESHOLD,) + ROBUST}} for r in out_runs],
              "outputs": out}
    os.makedirs(results, exist_ok=True)
    with open(os.path.join(results, "outputs.json"), "w", encoding="ascii") as f:
        json.dump(out, f, indent=2, sort_keys=True)
        f.write("\n")
    with open(os.path.join(results, "detail.json"), "w", encoding="ascii") as f:
        json.dump(detail, f, indent=1, sort_keys=True)
        f.write("\n")
    if log is not None:
        print(json.dumps(out, indent=2, sort_keys=True), file=log)
    return out, detail



def main():
    run(os.environ.get("ECDYSIS_SEED", ""))


if __name__ == "__main__":
    main()
