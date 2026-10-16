#!/usr/bin/env python3
"""Pauli, Weidel, Kunkel & Morrison's sensitivity of the polychronization model: the released program, its background
noise made Poisson, and its group search's threshold moved.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test is from Pauli, Weidel, Kunkel & Morrison,
"Reproducing Polychronization: A Guide to Maximizing the Reproducibility of Spiking Network Models", Frontiers in
Neuroinformatics 12:46 (2018; doi:10.3389/fninf.2018.00046; CC BY 4.0): "Further examination of the correctly
reproduced model reveals that it is highly sensitive to implementation choices such as the realization of background
noise, the integration timestep, and the thresholding parameter of the analysis algorithm."

The model is Izhikevich's (Neural Computation 18(2), 2006), as his released C++ program builds it (poly_spnet.cpp at
the author's page, pinned by hash: 800 excitatory and 200 inhibitory neurons, 100 synapses each, delays of 1 to 20 ms,
additive STDP, one randomly chosen neuron driven with 20 each millisecond, 18,000 s of model time, then a search for
polychronous groups). Pauli et al. reproduced it bit for bit in NEST (their section 3.2), so the released program is the
"correctly reproduced model". The input is the program itself, checked against its SHA-256; it is third-party code and
runs only in the sealed container. Every rule below was fixed before any seed existed, and before any count of groups
was computed under either change. The program's own count, 4,305 groups for its own seed, was known (the printed value
of Pauli et al.'s section 3.1, which receipt ee91ebb3 on Izhikevich's claim repeated here); no count at 5 or 10 layers,
and none under the Poisson background, had been computed.

Read before fixing the rules (the paper, its section numbers as printed; its repository, INM-6/reproducing-
polychronization at 169f022, read as data and not run):
  - The background noise (3.4.1): "each neuron receives an independent Poissonian spike train with synaptic weight of
    10mV and rate of 40Hz", in place of the one random neuron each millisecond; its experiment file
    (poisson_stimulus.yaml) sets rate 40 and weight 10 on its qualitative NEST model, one Poisson generator connected to
    every neuron (independent trains), and the result was counted by the program's own search: "the number of found
    groups are reduced by around 90% to a median of 291 with an IQR of 24" over ten realizations (its Figure 8A, where
    the bitwise reproduction of the program is the reference).
  - The threshold (3.5): "Reducing it to five increases the number of groups found in the original model from 4,305
    to 27,116, whereas increasing it to ten decreases the number to 608", the parameter min_group_path of the program's
    search, a group counted when its longest path L_max is at least that many layers (the code's L_max >= 7; the text
    of 2.3.2 says "larger than seven", 3.5 "greater than, or equal to seven", and the code decides).
  - The integration timestep (3.4.4) was tested by integrating the neuron in ten 0.1 ms substeps with spikes held to
    the 1 ms grid (4,300 groups to 13,000 by their Python search) and at 0.1 ms throughout (151), both needing their own
    search or ten times the search's work; it is not tested here (below).
  - Spike weights enter the neuron as a current for the 1 ms step they arrive in, I += w, as the program's synapses
    and its driven neuron do, and as the NEST fork's izhikevich model adds spike weights for the bitwise reproduction;
    a 10 mV Poisson spike is half the program's 20, which alone does not fire a neuron at rest.
  - A pilot here, outside any receipt, ran O and P for 600 s of model time under a test seed (12345), simulating only,
    with no search, to time them: 13.6 s and 27.7 s (P then drew exp(-0.04) for every neuron, which rule 1 now draws
    once a millisecond, the same number), excitatory rates 3.6 and 4.2 Hz in the last second.

1. The programs: the released file, with izh2006's three changes (its header, its main, srand from the first argument)
   and four that count groups at 5 and 10 layers in the same pass as the program's own count at 7: two counters
   declared beside N_polychronous, set to zero where it is, raised in polychronous() for every candidate the program
   does not discard (discard == 0) with L_max >= 5 and L_max >= 10, just before its own test (discard == 0) &
   (L_max >= min_group_path), and printed on one line ("N_layers5=..., N_layers10=...") just before its own
   "N_polychronous=" line. min_group_path is used nowhere else in the default search, so the counts are those the
   program gives with min_group_path set to 5 or 10, from one run. That is program O. Program P is O with the one line
   that drives a random neuron each millisecond (I[int(floor(N*rand01))]=20;) replaced by a Poisson background: each
   millisecond, for each neuron in turn, k is drawn from a Poisson law of mean 0.04 (40 Hz in 1 ms steps) by inverting
   its distribution with one rand01, and I[i] += 10 k. Nothing else is touched: the model, the plasticity, the 18,000 s
   and the search. Both are compiled with the image's g++ at -O2.
2. The draws: four seeds from the archive's seed (the first 31 bits of SHA-256 of "<seed>:<i>", i = 1 to 4, as
   izh2006's), each run once as O and once as P (the same seed builds the same network and initial state, which the
   program draws before its first millisecond), each in its own directory, two at a time; and the released draw, O
   under the program's own seed (srand 0), the run Pauli et al. counted. Each run is stopped once its count is printed.
3. The test, five conditions, each a change by at least half the paper's on a log scale (the square root of the
   paper's ratio):
   (1) the median count of the four P draws at most sqrt(1/10) = 0.316 times the median of the four O draws (the
       paper: a fall of about 90%);
   (2) in the released draw, the count at 5 layers at least sqrt(27,116/4,305) = 2.51 times the count at 7, and
   (3) the count at 10 layers at most sqrt(608/4,305) = 0.376 times it;
   (4) and (5) the same two in the median, over the four O draws, of each draw's count at 5 (and at 10) over its count
       at 7.
   test_passed is 1 if all five hold. A median of zero at 7 layers makes a ratio undefined, and its condition fails.
4. Beside, not counted: every count; whether the released draw gives the paper's 27,116 and 608 exactly; each draw's
   firing rates (the program's own printed rates, excitatory and inhibitory, the mean of its last 10 s) and share of
   strong excitatory-to-excitatory synapses; the ratio of the medians at 5 and 10 layers in the P draws.

Controls (controls_passed counts those that behave as stated): the file is the pinned one; each program differs from
the released one by its stated changes only; the four seeds are distinct and none is 0; every run printed its 18,000
seconds and both its count lines; the released draw's count at 7 layers is Pauli et al.'s 4,305, which a run on the
same C library's random numbers repeats only if the program runs here as it ran there (the method could fail it); and
every P draw's excitatory rate over its last 10 s lies between 2 and 8 Hz, the range Pauli et al. kept every changed
model in (3.4: "between 2 and 8Hz (compared with 2-5Hz of the original)"), so that the two backgrounds are compared at
like rates.

What it cannot check: the integration timestep, the third choice the sentence names, whose test needs the network and
its search at 0.1 ms (or a search ten times as long); the changes on Pauli et al.'s qualitative NEST model, where they
made the Poisson change (it differs from the program in its numerics and, they report, in how often each of two gamma
states is reached); and their Python search, which finds about twice the program's groups.

POLY_SMOKE_SECONDS (a smoke trial only; the bundle never sets it) shortens the 18,000 s, by one more change to the
loop's bound, and the controls then say so.

Writes results/outputs.json and results/detail.json. Run with: python3 poly/pauli2018.py
"""

import concurrent.futures as cf
import hashlib
import importlib.util
import json
import math
import os
import re
import shutil
import statistics
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("poly_izh2006_for_pauli", os.path.join(HERE, "izh2006.py"))
izh = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(izh)

INPUT = izh.INPUT
Refused = izh.Refused
BASE = izh.CHANGES
COUNTING = (
    ("int\t\t\tN_polychronous;", "int\t\t\tN_polychronous;\r\nint\t\t\tN_layers5, N_layers10;"),
    ("if ((discard == 0) & (L_max >= min_group_path))",
     "if (discard == 0) { if (L_max >= 5) N_layers5++; if (L_max >= 10) N_layers10++; }\r\n"
     "\t\t\tif ((discard == 0) & (L_max >= min_group_path))"),
    ("N_polychronous=0;", "N_polychronous=0; N_layers5=0; N_layers10=0;"),
    ('cout << "\\nN_polychronous=" << N_polychronous << "\\n";',
     'cout << "\\nN_layers5=" << N_layers5 << ", N_layers10=" << N_layers10;\r\n'
     '\tcout << "\\nN_polychronous=" << N_polychronous << "\\n";'),
)
RATE_HZ = 40.0
WEIGHT = 10.0
POISSON = ("I[int(floor(N*rand01))]=20;",
           "{ const double p0_ = exp(-0.04); for (i=0;i<N;i++) { double x_ = rand01, p_ = p0_, c_ = p0_; int k_ = 0; "
           "while (x_ > c_) { k_++; p_ *= 0.04/k_; c_ += p_; } I[i] += 10.0*k_; } }")
LOOP = "for (sec=0; sec<60*60*5; sec++)"

SECONDS = 18000
DRAWS = 4
LAYERS = (5, 7, 10)
PAULI = {5: 27116, 7: 4305, 10: 608}
NOISE_BOUND = math.sqrt(1 / 10)                       # 0.316
UP5 = math.sqrt(PAULI[5] / PAULI[7])                  # 2.51
DOWN10 = math.sqrt(PAULI[10] / PAULI[7])              # 0.376
RATE_RANGE = (2.0, 8.0)
LAST = 10
LIMIT = 200
OUTPUTS = ("median_original", "median_poisson", "noise_ratio", "groups_original", "groups_poisson",
           "released_groups", "released_layers5", "released_layers10", "released_ratio5", "released_ratio10",
           "draws_ratio5", "draws_ratio10", "paper_counts", "rates", "conditions_met", "conditions_total",
           "controls_passed", "controls_total", "test_passed")

SEC = izh.SEC
COUNT = izh.COUNT
LAYERLINE = re.compile(r"^N_layers5=(\d+), N_layers10=(\d+)$")


def apply(source, changes):
    """Each anchor present exactly once when its turn comes; the rest of the text untouched."""
    out = source
    for old, new in changes:
        if out.count(old) != 1:
            raise Refused(f"{old[:60]!r} occurs {out.count(old)} times, not once")
        out = out.replace(old, new)
    return out


def undone(original, new, changes):
    """Control: undoing the changes, last first, gives back the released text exactly."""
    back = new
    for old, rep in reversed(changes):
        if back.count(rep) != 1:
            return False
        back = back.replace(rep, old)
    return back == original


def changes_of(kind, seconds=SECONDS):
    ch = list(BASE) + list(COUNTING)
    if kind == "P":
        ch.append(POISSON)
    elif kind != "O":
        raise ValueError(kind)
    if seconds != SECONDS:
        ch.append((LOOP, f"for (sec=0; sec<{int(seconds)}; sec++)"))
    return tuple(ch)


def seeds_of(seed, n=DRAWS):
    return izh.seeds_of(seed, n)


def parse(lines):
    """The printed seconds, the count at 7 layers, and the counts at 5 and 10."""
    secs, counts, _ = izh.parse(lines)
    layers = []
    for line in lines:
        m = LAYERLINE.match(line.strip())
        if m:
            layers.append((int(m.group(1)), int(m.group(2))))
    return secs, counts, layers


def run_program(exe, work, name, seed, seconds):
    """One run in its own directory (the program writes ../*.dat), stopped once its count is printed."""
    home = os.path.join(work, name)
    run_dir = os.path.join(home, "run")
    os.makedirs(run_dir)
    t0 = time.time()
    lines, killed = [], False
    with open(os.path.join(home, "stdout.txt"), "w", encoding="latin-1") as fh:
        p = subprocess.Popen(["stdbuf", "-oL", exe, str(seed)], cwd=run_dir, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, text=True, encoding="latin-1")
        for line in p.stdout:
            fh.write(line)
            if line.startswith("i= "):
                continue
            lines.append(line)
            if COUNT.match(line.strip()):
                p.kill()
                killed = True
                break
        p.stdout.close()
        p.wait()
    secs, counts, layers = parse(lines)
    complete = (len(secs) == seconds and [s[0] for s in secs] == list(range(seconds)) and len(counts) == 1
                and len(layers) == 1)
    tail = [x.strip() for x in lines if x.strip() and not SEC.match(x.rstrip("\r\n"))][-3:]
    return {"name": name, "seed": seed, "secs": secs, "counts": counts, "layers": layers, "complete": complete,
            "exit": "stopped after its count" if killed else p.returncode, "tail": tail,
            "wall_s": round(time.time() - t0, 1)}


def by_layer(run):
    """{5: n5, 7: n7, 10: n10}, or None if the run printed no counts."""
    if not run["counts"] or not run["layers"]:
        return None
    return {5: run["layers"][0][0], 7: run["counts"][0], 10: run["layers"][0][1]}


def last_rates(run, last=LAST):
    """The mean of the program's printed excitatory and inhibitory rates, and its last strong share."""
    s = run["secs"][-last:]
    if not s:
        return None
    return (sum(x[1] for x in s) / len(s), sum(x[3] for x in s) / len(s), s[-1][2])


def ratio(a, b):
    return a / b if b else None


def conditions(o7, p7, released, r5, r10):
    """Rule 3. o7 and p7: the O and P draws' counts at 7 layers; released: {5, 7, 10}; r5, r10: the O draws' own
    ratios of the counts at 5 and 10 layers to the count at 7 (None where the count at 7 is zero)."""
    mo, mp = statistics.median(o7), statistics.median(p7)
    noise = ratio(mp, mo)
    rel5, rel10 = ratio(released[5], released[7]), ratio(released[10], released[7])
    d5 = statistics.median(r5) if all(x is not None for x in r5) else None
    d10 = statistics.median(r10) if all(x is not None for x in r10) else None
    return {
        "Poisson background: median at most 0.316 of the original's": noise is not None and noise <= NOISE_BOUND,
        "released draw: 5 layers at least 2.51 times 7": rel5 is not None and rel5 >= UP5,
        "released draw: 10 layers at most 0.376 times 7": rel10 is not None and rel10 <= DOWN10,
        "O draws: median of 5 over 7 at least 2.51": d5 is not None and d5 >= UP5,
        "O draws: median of 10 over 7 at most 0.376": d10 is not None and d10 <= DOWN10,
    }


def fmt(x, nd=4):
    return "n/a" if x is None else f"{x:.{nd}g}"


def run(seed, inputs="inputs", results="results", workers=2, seconds=SECONDS):
    original = izh.read_input(inputs)
    sources = {k: apply(original, changes_of(k, seconds)) for k in ("O", "P")}
    seeds = seeds_of(seed)
    os.makedirs(results, exist_ok=True)
    # The sandbox's /tmp cannot run programs; results/ can, by an absolute path (each run starts in its own directory).
    work = os.path.abspath(os.path.join(results, "work"))
    shutil.rmtree(work, ignore_errors=True)
    os.makedirs(work)
    exes = {}
    for k, src in sources.items():
        d = os.path.join(work, f"build{k}")
        os.makedirs(d)
        exes[k] = izh.compile_program(src, d)
    jobs = [("released", 0, "O")]
    for i, s in enumerate(seeds, start=1):
        jobs += [(f"O{i}", s, "O"), (f"P{i}", s, "P")]
    with cf.ThreadPoolExecutor(workers) as pool:
        done = list(pool.map(lambda j: run_program(exes[j[2]], work, j[0], j[1], seconds), jobs))
    for d in done:
        if by_layer(d) is None:
            raise RuntimeError(f"{d['name']} printed no counts; its last lines: {d['tail']} (kept in {work})")
    shutil.rmtree(work, ignore_errors=True)        # kept above when a run fails, for the reason to be read
    runs = {d["name"]: d for d in done}
    released = by_layer(runs["released"])
    O = [by_layer(runs[f"O{i}"]) for i in range(1, DRAWS + 1)]
    P = [by_layer(runs[f"P{i}"]) for i in range(1, DRAWS + 1)]
    o7, p7 = [x[7] for x in O], [x[7] for x in P]
    r5, r10 = [ratio(x[5], x[7]) for x in O], [ratio(x[10], x[7]) for x in O]
    cond = conditions(o7, p7, released, r5, r10)
    mo, mp = statistics.median(o7), statistics.median(p7)
    noise = ratio(mp, mo)
    rates = {d["name"]: last_rates(d) for d in done}

    ctl = {
        "the file is the pinned one": True,
        "each program differs from the released one by its stated changes only":
            all(undone(original, sources[k], changes_of(k, seconds)) for k in ("O", "P")),
        "the four seeds are distinct and none is 0": len(set(seeds)) == DRAWS and 0 not in seeds,
        f"every run printed its {SECONDS:,} seconds and both count lines":
            seconds == SECONDS and all(d["complete"] for d in done),
        "the released draw's count at 7 layers is Pauli et al.'s 4,305": released[7] == PAULI[7],
        "every P draw's excitatory rate over its last 10 s lies between 2 and 8 Hz":
            all(rates[f"P{i}"] is not None and RATE_RANGE[0] <= rates[f"P{i}"][0] <= RATE_RANGE[1]
                for i in range(1, DRAWS + 1)),
    }
    p5 = [ratio(x[5], x[7]) for x in P]
    p10 = [ratio(x[10], x[7]) for x in P]

    def span(names, j, nd=3):
        v = [rates[n][j] for n in names if rates[n] is not None]
        return f"{min(v):.{nd}g}-{max(v):.{nd}g}" if v else "n/a"

    on = [f"O{i}" for i in range(1, DRAWS + 1)]
    pn = [f"P{i}" for i in range(1, DRAWS + 1)]
    values = {
        "median_original": mo, "median_poisson": mp, "noise_ratio": -1 if noise is None else round(noise, 6),
        "groups_original": ", ".join(f"{x[7]} ({x[5]}/{x[10]})" for x in O) + " at 7 (5/10) layers, draws 1-4",
        "groups_poisson": ", ".join(f"{x[7]} ({x[5]}/{x[10]})" for x in P) + " at 7 (5/10) layers, draws 1-4",
        "released_groups": released[7], "released_layers5": released[5], "released_layers10": released[10],
        "released_ratio5": round(released[5] / released[7], 6) if released[7] else -1,
        "released_ratio10": round(released[10] / released[7], 6) if released[7] else -1,
        "draws_ratio5": -1 if any(x is None for x in r5) else round(statistics.median(r5), 6),
        "draws_ratio10": -1 if any(x is None for x in r10) else round(statistics.median(r10), 6),
        "paper_counts": (f"released draw: 4,305 at 7 {'yes' if released[7] == PAULI[7] else 'no'}, 27,116 at 5 "
                         f"{'yes' if released[5] == PAULI[5] else 'no'}, 608 at 10 "
                         f"{'yes' if released[10] == PAULI[10] else 'no'}"),
        "rates": (f"last 10 s, exc/inh Hz: O {span(on, 0)}/{span(on, 1)}, P {span(pn, 0)}/{span(pn, 1)}; strong E-E % "
                  f"O {span(on, 2)}, P {span(pn, 2)}"),
        "conditions_met": sum(bool(v) for v in cond.values()), "conditions_total": len(cond),
        "controls_passed": sum(bool(v) for v in ctl.values()), "controls_total": len(ctl),
        "test_passed": int(all(cond.values())),
    }
    out = {k: values[k] for k in OUTPUTS}
    for k, v in out.items():
        if isinstance(v, str) and len(v) > LIMIT:
            raise AssertionError(f"{k}: longer than {LIMIT} characters: {v}")
        if isinstance(v, float) and not math.isfinite(v):
            raise AssertionError(f"{k}: not finite")
    detail = {
        "input": {"name": INPUT[0], "sha256": INPUT[1], "bytes": INPUT[2]},
        "changes": {k: [{"from": a, "to": b} for a, b in changes_of(k, seconds)] for k in ("O", "P")},
        "seconds": seconds, "seeds": seeds,
        "thresholds": {"noise": NOISE_BOUND, "up5": UP5, "down10": DOWN10},
        "conditions": cond, "controls": ctl,
        "runs": [{"name": d["name"], "seed": d["seed"], "counts": by_layer(d), "rates_last_10s": rates[d["name"]],
                  "exit": d["exit"], "tail": d["tail"], "seconds": len(d["secs"]), "last_seconds": d["secs"][-3:],
                  "wall_s": d["wall_s"]} for d in done],
        "poisson_ratios": {"median_5_over_7": statistics.median(p5) if all(x is not None for x in p5) else None,
                           "median_10_over_7": statistics.median(p10) if all(x is not None for x in p10) else None},
        "strong_ee_every_1000s": {d["name"]: [s[2] for s in d["secs"] if s[0] % 1000 == 999] for d in done},
    }
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
    smoke = os.environ.get("POLY_SMOKE_SECONDS")
    seconds = int(smoke) if smoke else SECONDS
    try:
        out, _ = run(seed, seconds=seconds)
    except Refused as e:
        sys.exit(f"pauli2018: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
