#!/usr/bin/env python3
"""Izhikevich's polychronous groups: the paper's released program, run in eight seeded draws.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:df6778c0e0f48316) is from Izhikevich,
"Polychronization: Computation with Spikes", Neural Computation 18(2), 245-282 (2006): "To our surprise, the number of
coexisting polychronous groups far exceeds the number of neurons in the network, resulting in an unprecedented memory
capacity of the system."

Its registered test: refuted if the network of the paper's released C++ program (poly_spnet.cpp at the author's page:
800 excitatory and 200 inhibitory neurons, 100 synapses each, delays of 1 to 20 ms, STDP, one random neuron driven each
millisecond), run as released for 18,000 s of model time in each of 8 seeded draws, gives a median below 2,500
polychronous groups (half the over 5,000 the paper reports) by the program's own default algorithm: anchor triplets
with synapses above 95% of the maximum, groups whose longest path has 7 layers or more.

The input is the program itself (inputs/poly_spnet.cpp, from https://www.izhikevich.org/publications/poly_spnet.cpp),
checked against its SHA-256. It is third-party code, so it runs only in the sealed container. Every rule below was fixed
before any seed existed.

1. The program: the released file, changed in three places and nowhere else, each matched exactly once. Its header
   <iostream.h> becomes <iostream> with the std namespace, and void main() becomes int main(argc, argv), which a
   current compiler requires; and srand(0) takes the draw's seed from its first argument (0 when there is none). It is
   compiled with the image's g++ at -O2. Its model, its 18,000 s, its plasticity and its search for groups are not
   touched.
2. The draws: eight seeds from the archive's seed (the first 31 bits of SHA-256 of "<seed>:<i>", i = 1 to 8), each run
   in its own directory, two at a time. After its 18,000 s the program prints its count of groups ("N_polychronous=")
   and then shuffles the synapses and counts again. A draw is stopped once its first count is printed (its output is
   line-buffered, so the count is read as printed), since the test asks only that.
3. The released draw: the program's own seed (srand 0), run to its end. Its count is reported beside the test (and in
   a control, below). The program then means to shuffle the excitatory synapses and count again, but first closes its
   group file a second time (main's fclose after all_polychronous's own), which a current C library stops as a double
   free; how the run ends (its exit status and last line, or the shuffled count if it gets there) is reported as found.
4. The test: the median of the eight counts (the mean of the middle two) at 2,500 or more. test_passed is 1 if it holds.
5. Beside, also not counted: each draw's count, the least and greatest, how many reach 2,500; the last second's
   excitatory and inhibitory firing rates and share of strong excitatory-to-excitatory synapses, as the program prints
   them ("exc. frate", "inh. frate", "exc->exc str": the percentage of excitatory synapses that are excitatory-to-
   excitatory and above 90% of the maximum weight).

Controls (controls_passed counts those that behave as stated): the file is the pinned one; the changed program differs
from the released one by the three changes only; the eight seeds are distinct and none is 0; every run printed its
18,000 seconds and a count; and the released draw's count is the 4,305 groups Pauli, Weidel, Kunkel & Morrison report
for the program (Frontiers in Neuroinformatics 12:46, 2018, section 3.1), which a run on the same C library's random
numbers repeats only if the program runs here as it ran there.

What it cannot check: the paper's own run, on another compiler's random numbers and over 24 hours, and the counts
during it; and whether the groups the program finds are ever activated, which the paper measured from spiking activity.

Writes results/outputs.json and results/detail.json. Run with: python3 poly/izh2006.py
"""

import concurrent.futures as cf
import hashlib
import json
import os
import re
import shutil
import statistics
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))

INPUT = ("poly_spnet.cpp", "37f71268e1f66fa244cea2cafdf63fccdfe6db4f2d19105a3eb6d3b20e20a7dc", 23829)
CHANGES = (
    ("#include <iostream.h>", "#include <iostream>\nusing namespace std;"),
    ("void main()", "int main(int argc, char **argv)"),
    ("srand(0);", "srand(argc > 1 ? (unsigned) strtoul(argv[1], 0, 10) : 0);"),
)
NEURONS = 1000
SECONDS = 18000
DRAWS = 8
THRESHOLD = 2500
PAULI = 4305
LIMIT = 200
OUTPUTS = ("median_groups", "groups", "least_groups", "most_groups", "draws_at_least_2500", "released_groups",
           "released_end", "last_second", "controls_passed", "controls_total", "test_passed")

SEC = re.compile(r"^sec=(\d+), exc\. frate=(\S+),\s+exc->exc str=(\S+),\s+inh\. frate=(\S+?)\.$")
COUNT = re.compile(r"^N_polychronous=(\d+)$")
RATIO = re.compile(r"ratio \(true/shuffled\) = (\S+)")


class Refused(Exception):
    pass


def read_input(inputs):
    path = os.path.join(inputs, INPUT[0])
    with open(path, "rb") as fh:
        data = fh.read()
    if hashlib.sha256(data).hexdigest() != INPUT[1] or len(data) != INPUT[2]:
        raise Refused(f"{INPUT[0]} is not the pinned file")
    return data.decode("ascii")


def changed(source):
    """Rule 1: the three changes, each anchor present exactly once; the rest of the text untouched."""
    out = source
    for old, new in CHANGES:
        if out.count(old) != 1:
            raise Refused(f"{old!r} occurs {out.count(old)} times, not once")
        out = out.replace(old, new)
    return out


def only_the_changes(original, new):
    """Control: undoing the three changes gives back the released text exactly."""
    back = new
    for old, rep in reversed(CHANGES):
        if back.count(rep) != 1:
            return False
        back = back.replace(rep, old)
    return back == original


def seeds_of(seed, n=DRAWS):
    return [int(hashlib.sha256(f"{seed}:{i}".encode()).hexdigest()[:8], 16) & 0x7FFFFFFF for i in range(1, n + 1)]


def parse(lines):
    """The program's printed seconds, counts and ratio."""
    secs, counts, ratio = [], [], None
    for line in lines:
        line = line.rstrip("\r\n")
        m = SEC.match(line)
        if m:
            secs.append((int(m.group(1)), float(m.group(2)), float(m.group(3)), float(m.group(4))))
            continue
        m = COUNT.match(line.strip())
        if m:
            counts.append(int(m.group(1)))
            continue
        m = RATIO.search(line)
        if m:
            ratio = float(m.group(1))
    return secs, counts, ratio


def compile_program(source, work):
    src = os.path.join(work, "poly_spnet.cpp")
    with open(src, "w", encoding="ascii", newline="") as fh:
        fh.write(source)
    exe = os.path.abspath(os.path.join(work, "poly_spnet"))
    subprocess.run(["g++", "-O2", "-w", "-o", exe, src], check=True)
    return exe


def run_program(exe, work, name, seed, stop_after_first):
    """One run in its own directory (the program writes ../*.dat); returns its parsed output and wall time."""
    home = os.path.join(work, name)
    run_dir = os.path.join(home, "run")
    os.makedirs(run_dir)
    log = os.path.join(home, "stdout.txt")
    t0 = time.time()
    lines = []
    killed = False
    with open(log, "w", encoding="latin-1") as fh:
        p = subprocess.Popen(["stdbuf", "-oL", exe, str(seed)], cwd=run_dir, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, text=True, encoding="latin-1")
        for line in p.stdout:
            fh.write(line)
            if line.startswith("i= "):
                continue
            lines.append(line)
            if stop_after_first and COUNT.match(line.strip()):
                p.kill()
                killed = True
                break
        p.stdout.close()
        p.wait()
    secs, counts, ratio = parse(lines)
    tail = [x.strip() for x in lines if x.strip() and not SEC.match(x.rstrip("\r\n"))][-3:]
    return {"name": name, "seed": seed, "secs": secs, "counts": counts, "ratio": ratio,
            "exit": "stopped after its count" if killed else p.returncode, "tail": tail,
            "wall_s": round(time.time() - t0, 1), "complete": len(secs) == SECONDS and
            [s[0] for s in secs] == list(range(SECONDS)) and len(counts) >= 1}


def end_of(run):
    """How the released draw ended, as found."""
    if len(run["counts"]) > 1:
        return f"shuffled count {run['counts'][1]}, ratio {run['ratio']}"
    last = run["tail"][-1] if run["tail"] else ""
    return f"exit status {run['exit']} after its count: {last[:120]}"


def conditions(median):
    """Rule 4."""
    return {"the median of the eight counts is 2,500 or more": median >= THRESHOLD}


def fmt(x):
    return f"{x:g}"


def run(seed, inputs="inputs", results="results", workers=2):
    original = read_input(inputs)
    source = changed(original)
    seeds = seeds_of(seed)
    os.makedirs(results, exist_ok=True)
    # The sandbox's /tmp cannot run programs; results/ can. The path is made absolute because each run starts in its
    # own directory, from which a relative path to the program would not resolve.
    work = os.path.abspath(os.path.join(results, "work"))
    shutil.rmtree(work, ignore_errors=True)
    os.makedirs(work)
    exe = compile_program(source, work)
    jobs = [("released", 0, False)] + [(f"draw{i}", s, True) for i, s in enumerate(seeds, start=1)]
    with cf.ThreadPoolExecutor(workers) as pool:
        done = list(pool.map(lambda j: run_program(exe, work, *j), jobs))
    for d in done:
        if not d["secs"] or not d["counts"]:
            raise RuntimeError(f"{d['name']} printed no seconds or no count; its last lines: {d['tail']} "
                               f"(its whole output is kept in {work})")
    shutil.rmtree(work, ignore_errors=True)       # kept above when a run fails, for the reason to be read
    released, draws = done[0], done[1:]
    counts = [d["counts"][0] if d["counts"] else -1 for d in draws]
    median = statistics.median(counts)
    cond = conditions(median)

    ctl = {
        "the file is the pinned one": True,
        "the program differs from the released one by the three changes only": only_the_changes(original, source),
        "the eight seeds are distinct and none is 0": len(set(seeds)) == DRAWS and 0 not in seeds,
        "every run printed its 18,000 seconds and a count": all(d["complete"] for d in done),
        "the released draw's count is Pauli et al.'s 4,305": bool(released["counts"]) and released["counts"][0] == PAULI,
    }

    last = [d["secs"][-1] for d in done if d["secs"]]
    rel_counts = released["counts"]
    values = {
        "median_groups": median,
        "groups": ", ".join(str(c) for c in counts) + f" (draws 1 to {DRAWS}; {NEURONS:,} neurons)",
        "least_groups": min(counts), "most_groups": max(counts),
        "draws_at_least_2500": sum(c >= THRESHOLD for c in counts),
        "released_groups": rel_counts[0] if rel_counts else -1,
        "released_end": end_of(released),
        "last_second": (f"exc {fmt(min(s[1] for s in last))}-{fmt(max(s[1] for s in last))} Hz, inh "
                        f"{fmt(min(s[3] for s in last))}-{fmt(max(s[3] for s in last))} Hz, strong E-E "
                        f"{fmt(min(s[2] for s in last))}-{fmt(max(s[2] for s in last))}%"),
        "controls_passed": sum(bool(v) for v in ctl.values()), "controls_total": len(ctl),
        "test_passed": int(all(cond.values())),
    }
    out = {k: values[k] for k in OUTPUTS}
    for k, v in out.items():
        if isinstance(v, str) and len(v) > LIMIT:
            raise AssertionError(f"{k}: longer than {LIMIT} characters: {v}")
    detail = {
        "input": {"name": INPUT[0], "sha256": INPUT[1], "bytes": INPUT[2]},
        "changes": [{"from": a, "to": b} for a, b in CHANGES],
        "conditions": cond, "controls": ctl,
        "runs": [{"name": d["name"], "seed": d["seed"], "counts": d["counts"], "ratio": d["ratio"], "exit": d["exit"],
                  "tail": d["tail"], "seconds": len(d["secs"]), "last_seconds": d["secs"][-3:], "wall_s": d["wall_s"]}
                 for d in done],
        "strong_ee_every_1000s": {d["name"]: [s[2] for s in d["secs"] if s[0] % 1000 == 999] for d in done},
    }
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
        sys.exit(f"izh2006: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
