#!/usr/bin/env python3
"""Capcarrere, Sipper & Tomassini's two-state, r = 1 density classifier: rule 184 and the output its theorem specifies.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:7b0e8ed6ac7a5abd) is from Capcarrere,
Sipper and Tomassini, "Two-state, r=1 Cellular Automaton that Classifies Density" (Physical Review Letters 77(24),
4969-4971, 1996): "We show that by changing the output specification, namely, the final pattern toward which the
system should converge, without increasing its computational complexity, a two-state, r = 1 cellular automaton exists
that can perfectly solve the density problem." (the abstract as OpenAlex holds it writes r = 1 in TeX).

Its registered test: refuted if, for some ring of N cells, N from 3 to 28 (periodic boundaries), some configuration
S(0) is left by T = ceil(N/2) steps of rule 184 (s_i(t+1) = s_(i-1)(t) if s_i(t) = 0, else s_(i+1)(t)) in a state that
breaks the paper's theorem: when more than half its cells are 1s, no two adjacent 1s or some two adjacent 0s; when
fewer than half, no two adjacent 0s or some two adjacent 1s; when exactly half, some two adjacent cells alike. Every
one of the 2^N configurations of each N is tried.

The claim is a construction and has no data of record: the paper (read in the authors' copy on Sipper's site before
registering) defines the rule, the step count and the specification, and the runs here are new. The rings are run in
C (ca/cst.c, compiled here with the image's gcc). Every rule below was fixed before any ring was run.

1. The rule. Rule 184 as the paper defines it: a cell in state 0 takes its left neighbour's state, a cell in state 1
   its right neighbour's (ca/cst.c's step184). A control checks that this is Wolfram's rule 184.
2. The test. For every N from 3 to 28 (N >= 3, so that a cell's two neighbours and itself are three cells) and every
   one of the 2^N configurations of the ring of N cells, T = ceil(N/2) steps; the state at T must meet the
   specification of the theorem's cases (1) to (3), the case chosen by the number k of 1s at time 0: two adjacent 1s
   and no two adjacent 0s if 2k > N; two adjacent 0s and no two adjacent 1s if 2k < N; no two adjacent cells alike if
   2k = N. test_passed is 1 if no configuration of any N fails.
3. Beside the test, none of it counted.
   - For each N, the most steps any configuration needed to reach the specification's state, against ceil(N/2), and
     the configurations whose state, once reached, was lost again by T.
   - The paper's remark that at T "the number of cells in state 1 short (respectively, in excess) of floor(0.5N) is
     given by (sum of a_i) - m", m the number of blocks of the majority state and a_i their sizes: for every
     configuration with 2k != N and both states present, that sum (the number of adjacent pairs of the majority state
     at T) against |k - floor(N/2)|, as printed, and against |2k - N|, the difference between the two states' counts.
   - Its footnote 13, that of all 256 two-state, r = 1 rules only 184 and 226 met the specification on 1,000 random
     configurations of 149 cells, rules 57 and 99 "trailing markedly behind at 60%": every rule on every configuration
     of every ring of 3 to 16 cells (the rules that never fail), and every rule on SAMPLE configurations of 149 cells,
     each cell 0 or 1 with equal chance, drawn from ECDYSIS_SEED (SHA-256 in counter mode, labelled "ca/cst/sample"),
     the only randomness used, each run for ceil(149/2) = 75 steps.
   - Its Figure 1(d): on 149 cells, 37 0s, 37 1s, 37 0s and 38 1s, which the caption says ends in "an alternation of
     0s and 1s with a single block of two cells in state 1": the blocks of two or more alike at T = 75.

Controls (controls_passed counts those that behave as stated): the paper's definition of rule 184 is Wolfram's 184;
the C steps (rule 184 as defined, and any rule by its number) equal a cell-by-cell step written here on seed-drawn
configurations of rings of 5, 8, 13 and 28 cells, for rules 30, 90, 110, 184 and 226; rule 226 is rule 184 seen in a
mirror (reflecting the ring, stepping and reflecting back) on the same configurations; the C theorem count equals a
cell-by-cell count written here for rings of 3 to 10 cells, every number of its rows; the C run of rings of any
length equals cell-by-cell steps here on the first 20 sample configurations, for rules 184 and 57; the identity, rule
204, fails the specification on some configuration of every ring of 4 to 12 cells; and Wolfram numbering on tables
built here (rules 30, 90, 110 and 184).

What it cannot check: the theorem for rings above 28 cells (it is proved for every N), the paper's two-dimensional
remarks (there are none in this paper), and the paper's sample of 1,000 configurations itself.

Writes results/outputs.json (the values a receipt carries) and results/detail.json (every value computed).
Run with: python3 ca/cst.py
"""

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

N_MIN, N_MAX = 3, 28
SWEEP = (3, 16)
SAMPLE, SAMPLE_N = 1000, 149
FIG1D = ((0, 37), (1, 37), (0, 37), (1, 38))
CONTROL_RINGS = (5, 8, 13, 28)
CONTROL_RULES = (30, 90, 110, 184, 226)
OUTPUTS = ("theorem", "configurations", "failures", "first_failure", "steps_needed", "persistence", "remark",
           "sweep", "sample", "fig1d", "conditions_met", "conditions_total", "test_passed", "controls_passed",
           "controls_total")
LIMIT = 200
HERE = os.path.dirname(os.path.abspath(__file__))


class Refused(Exception):
    pass


def steps(N):
    return (N + 1) // 2


# ---------------------------------------------------------------- cell by cell, for the controls and the figure

def bits_of(x, N):
    return [(x >> i) & 1 for i in range(N)]


def word_of(bits):
    return sum(b << i for i, b in enumerate(bits))


def step_cells(bits, rule):
    N = len(bits)
    return [(rule >> (4 * bits[(i - 1) % N] + 2 * bits[i] + bits[(i + 1) % N])) & 1 for i in range(N)]


def step184_cells(bits):
    """The paper's definition: a 0 takes its left neighbour's state, a 1 its right neighbour's."""
    N = len(bits)
    return [bits[(i - 1) % N] if bits[i] == 0 else bits[(i + 1) % N] for i in range(N)]


def meets_cells(bits, twice_ones):
    N = len(bits)
    has11 = any(bits[i] and bits[(i + 1) % N] for i in range(N))
    has00 = any(not bits[i] and not bits[(i + 1) % N] for i in range(N))
    if twice_ones > N:
        return has11 and not has00
    if twice_ones < N:
        return has00 and not has11
    return not has00 and not has11


def theorem_cells(N):
    """The C theorem row for one N, computed cell by cell."""
    T, half = steps(N), N // 2
    fails = lost = r_total = r_paper = r_count = 0
    first, most, never = -1, 0, False
    for s in range(1 << N):
        b = bits_of(s, N)
        k = sum(b)
        need, was_lost = -1, False
        for t in range(T + 1):
            if t:
                b = step184_cells(b)
            ok = meets_cells(b, 2 * k)
            if ok and need < 0:
                need = t
            if not ok and need >= 0:
                was_lost = True
        if not meets_cells(b, 2 * k):
            fails += 1
            if first < 0:
                first = s
        if need < 0:
            never = True
        else:
            most = max(most, need)
        lost += was_lost
        if 2 * k != N and 0 < k < N:
            state = 1 if 2 * k > N else 0
            pairs = sum(1 for i in range(N) if b[i] == state and b[(i + 1) % N] == state)
            r_total += 1
            r_paper += pairs == abs(k - half)
            r_count += pairs == abs(2 * k - N)
    return {"N": N, "configurations": 1 << N, "failures": fails, "first": first, "most": -1 if never else most,
            "lost": lost, "remark_total": r_total, "remark_paper": r_paper, "remark_count": r_count}


def wolfram(table):
    return sum(v << int(nb, 2) for nb, v in table.items())


def table_of_184_definition():
    return {f"{a}{b}{c}": (a if b == 0 else c) for a in (0, 1) for b in (0, 1) for c in (0, 1)}


def blocks(bits):
    """The maximal runs of two or more alike on the ring, as (state, length), from the first cell that starts one."""
    N = len(bits)
    if all(b == bits[0] for b in bits):
        return [(bits[0], N)]
    start = next(i for i in range(N) if bits[i] != bits[i - 1])
    runs, i = [], 0
    while i < N:
        j = i
        while j + 1 < N and bits[(start + j + 1) % N] == bits[(start + i) % N]:
            j += 1
        runs.append((bits[(start + i) % N], j - i + 1))
        i = j + 1
    return [r for r in runs if r[1] >= 2]


# ---------------------------------------------------------------- the seed

class Stream:
    """Bits from ECDYSIS_SEED: SHA-256 of seed/label/counter, 256 bits a block."""

    def __init__(self, seed, label):
        self.seed, self.label, self.n, self.buf = seed, label, 0, []

    def bit(self):
        if not self.buf:
            self.n += 1
            h = hashlib.sha256(f"{self.seed}/{self.label}/{self.n}".encode()).digest()
            self.buf = [(byte >> j) & 1 for byte in h for j in range(8)]
        return self.buf.pop(0)

    def below(self, m):
        x = 0
        for _ in range(64):
            x = (x << 1) | self.bit()
        return x % m


# ---------------------------------------------------------------- the C program

def build(work):
    exe = os.path.join(work, "cst")
    subprocess.run(["gcc", "-O2", "-std=gnu11", "-o", exe, os.path.join(HERE, "cst.c")], check=True)
    return exe


def c_lines(exe, *args):
    out = subprocess.run([exe] + [str(a) for a in args], check=True, capture_output=True, text=True).stdout
    return [list(map(int, line.split())) for line in out.strip().split("\n") if line.strip()]


def c_theorem(exe, a, b):
    keys = ("N", "configurations", "failures", "first", "most", "lost", "remark_total", "remark_paper",
            "remark_count")
    return [dict(zip(keys, row)) for row in c_lines(exe, "theorem", a, b)]


def c_step(exe, rule, N, x, t=1):
    return c_lines(exe, "step", rule, N, x, t)[0][0]


def c_step184(exe, N, x, t=1):
    return c_lines(exe, "step184", N, x, t)[0][0]


def write_configs(path, configs):
    with open(path, "w", encoding="ascii") as fh:
        for b in configs:
            fh.write("".join(map(str, b)) + "\n")


def c_final(exe, path, rule, T):
    out = subprocess.run([exe, "final", path, str(rule), str(T)], check=True, capture_output=True,
                         text=True).stdout.split()
    return [[int(ch) for ch in line] for line in out]


# ---------------------------------------------------------------- the run

def conditions(rows):
    """Rule 2: no configuration of any ring of 3 to 28 cells fails."""
    covered = [r["N"] for r in rows] == list(range(N_MIN, N_MAX + 1))
    return {f"rule 184 meets the theorem's specification at ceil(N/2) on every configuration of every ring of "
            f"{N_MIN} to {N_MAX} cells": covered and all(r["failures"] == 0 for r in rows)}


def run(seed, inputs="inputs", results="results"):
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        raise Refused("the seed must be 64 hex characters")
    if shutil.which("gcc") is None:
        raise Refused("no gcc in this image")
    os.makedirs(results, exist_ok=True)
    work = tempfile.mkdtemp(prefix="work-", dir=results)
    try:
        exe = build(work)
        rows = c_theorem(exe, N_MIN, N_MAX)
        sweep = {r[0]: (r[1], r[2]) for r in c_lines(exe, "sweep", *SWEEP)}
        st = Stream(seed, "ca/cst/sample")
        sample = [[st.bit() for _ in range(SAMPLE_N)] for _ in range(SAMPLE)]
        sample_path = os.path.join(work, "sample.txt")
        write_configs(sample_path, sample)
        counts = c_lines(exe, "sample", sample_path, steps(SAMPLE_N))[0]
        fig = [s for s, n in FIG1D for _ in range(n)]
        b = list(fig)
        for _ in range(steps(len(fig))):
            b = step184_cells(b)
        fig_blocks = blocks(b)

        # controls
        ctl, ctl_detail = {}, {}
        ctl["the paper's definition of rule 184 is Wolfram's rule 184"] = wolfram(table_of_184_definition()) == 184
        cs = Stream(seed, "ca/cst/controls")
        same, mirror = True, True
        for N in CONTROL_RINGS:
            for _ in range(20):
                x = cs.below(1 << N)
                bx = bits_of(x, N)
                if c_step184(exe, N, x) != word_of(step184_cells(bx)):
                    same = False
                for rule in CONTROL_RULES:
                    if c_step(exe, rule, N, x) != word_of(step_cells(bx, rule)):
                        same = False
                if step_cells(bx, 226) != step_cells(bx[::-1], 184)[::-1]:
                    mirror = False
        ctl["the C steps equal a cell-by-cell step on seed-drawn rings of 5, 8, 13 and 28 cells"] = same
        ctl["rule 226 is rule 184 in a mirror on the same configurations"] = mirror
        small = c_theorem(exe, 3, 10)
        ctl["the C theorem rows for rings of 3 to 10 cells equal a cell-by-cell count"] = all(
            row == theorem_cells(row["N"]) for row in small) and len(small) == 8
        firsts = sample[:20]
        part = os.path.join(work, "first20.txt")
        write_configs(part, firsts)
        agree = True
        for rule in (184, 57):
            got = c_final(exe, part, rule, steps(SAMPLE_N))
            for b0, g in zip(firsts, got):
                y = list(b0)
                for _ in range(steps(SAMPLE_N)):
                    y = step_cells(y, rule)
                if y != g:
                    agree = False
        ctl["the C run of long rings equals cell-by-cell steps on the first 20 sample configurations, rules 184 "
            "and 57"] = agree
        ident = {N: c_lines(exe, "count", 204, N)[0][0] for N in range(4, 13)}
        ctl_detail["identity_failures"] = ident
        ctl["the identity, rule 204, fails some configuration of every ring of 4 to 12 cells"] = all(
            v > 0 for v in ident.values())
        built = {30: "00011110", 90: "01011010", 110: "01101110", 184: "10111000"}
        ctl["Wolfram numbering on tables built here (30, 90, 110, 184)"] = all(
            wolfram({format(k, "03b"): int(bits[7 - k]) for k in range(8)}) == num for num, bits in built.items())
    finally:
        shutil.rmtree(work, ignore_errors=True)

    cond = conditions(rows)
    total = sum(r["configurations"] for r in rows)
    fails = sum(r["failures"] for r in rows)
    first = next((r for r in rows if r["failures"]), None)
    passing = [rule for rule, (n, _) in sorted(sweep.items()) if n == 0]
    ranked = sorted(range(256), key=lambda r: (-counts[r], r))
    perfect = [r for r in ranked if counts[r] == SAMPLE]
    below = [r for r in ranked if counts[r] < SAMPLE][:4]
    r_total = sum(r["remark_total"] for r in rows)
    r_paper = sum(r["remark_paper"] for r in rows)
    r_count = sum(r["remark_count"] for r in rows)
    lost = sum(r["lost"] for r in rows)

    def ints(v):
        return ", ".join(map(str, v)) if v else "none"

    values = {
        "theorem": (f"rings of {N_MIN} to {N_MAX} cells, every configuration ({total:,} in all): {fails} fail the "
                    f"specification at ceil(N/2)"),
        "configurations": total,
        "failures": fails,
        "first_failure": f"N = {first['N']}, S(0) = {first['first']}" if first else "none",
        "steps_needed": (f"most steps needed, N = {N_MIN} to {N_MAX}: " + " ".join(str(r["most"]) for r in rows)),
        "persistence": f"configurations whose state, once reached, was lost by ceil(N/2): {lost:,}",
        "remark": (f"at T the majority's adjacent pairs equal |k - floor(N/2)| (the remark) in {r_paper:,} and "
                   f"|2k - N| in {r_count:,} of {r_total:,} configurations"),
        "sweep": (f"rules never failing on rings of {SWEEP[0]} to {SWEEP[1]} cells: {ints(passing)}"),
        "sample": (f"{SAMPLE:,} seed-drawn rings of {SAMPLE_N}: every one for rules {ints(perfect)}; then "
                   + ", ".join(f"{r} {100 * counts[r] / SAMPLE:.1f}%" for r in below)),
        "fig1d": ("Figure 1(d) at T = 75: blocks of two or more alike " +
                  (", ".join(f"{n} of {s}s" for s, n in fig_blocks) if fig_blocks else "none")),
        "conditions_met": sum(cond.values()), "conditions_total": len(cond), "test_passed": int(all(cond.values())),
        "controls_passed": sum(bool(v) for v in ctl.values()), "controls_total": len(ctl),
    }
    out = {k: values[k] for k in OUTPUTS}
    for key, v in out.items():
        if isinstance(v, str) and len(v) > LIMIT:
            raise AssertionError(f"{key}: longer than {LIMIT} characters: {v}")
    detail = {"rings": rows, "sweep_first_failures": {str(k): v for k, v in sweep.items()},
              "sample_counts": counts, "fig1d_blocks": fig_blocks, "conditions": cond, "controls": ctl,
              "control_detail": ctl_detail}
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
        sys.exit(f"cst: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
