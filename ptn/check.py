#!/usr/bin/env python3
"""The boolean Pythagorean triples: the authors' formulas checked against the encoding, a seeded sample of their
million cubes re-solved with proofs a verified checker accepts, the cubes' cover checked whole, and a partition of
{1, ..., 7824} checked, for an Ecdysis receipt.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:ac93008aa381022b) is from Heule, Kullmann and
Marek, "Solving and Verifying the boolean Pythagorean Triples problem via Cube-and-Conquer" (SAT 2016, LNCS 9710;
arXiv:1605.00723): "Due to the general interest in this mathematical problem, our result requires a formal proof.
Exploiting recent progress in unsatisfiability proofs of SAT solvers, we produced and verified a proof in the DRAT
format, which is almost 200 terabytes in size." Its registered test: Theorem 1, {1, ..., 7824} splits into two parts
with no Pythagorean triple (a^2 + b^2 = c^2) inside either, and {1, ..., 7825} does not. Refuted by such a split of
{1, ..., 7825}; by none existing for {1, ..., 7824}; or by the proof failing: the cube-split formula (the encoding after
blocked clause elimination, with one symmetry-breaking unit) not following from the encoding, one of its 10^6 cubes
satisfiable with that formula or its refutation rejected by a verified checker, or the cubes not covering the search
space.

The inputs, each checked against its SHA-256 and size before anything else runs (see INPUTS), come from the page the
paper names for its validation files (https://www.cs.utexas.edu/~marijn/ptn/): plain7825.cnf (the encoding),
transformed.cnf (the formula the cubes split), million.cubes (the first-level cubes), backbone7824.cnf (the encoding
for 7824 with its backbone) and bce7824.cnf (for a control); and the solver and the checker of hexagon/check.py, whose
code this module imports: CaDiCaL 2.1.3's source as Debian archived it and the two files of the CakeML-verified LRAT
checker cake_lpr, compiled from source by the run, in the pinned image, with no network. Every rule below was fixed
before any seed existed.

1. The encoding, written here: for n, every triple a <= b <= c <= n with a^2 + b^2 = c^2 (exact integers), and for
   each the clauses (a b c) and (-a -b -c): no triple all in one part, x_i true putting i in the first part. Its
   sizes must be those the paper prints in section 4: 6,492 occurring variables and 18,930 clauses for n = 7824,
   6,494 and 18,944 for n = 7825.
2. The formulas of record. plain7825.cnf (one header, every literal within it, the header's clause count) must equal
   rule 1's formula for 7825 as a multiset of clauses (each a set of literals). transformed.cnf must be one positive
   unit clause and otherwise clauses of plain7825.cnf (a sub-multiset of it), as the paper's blocked clause
   elimination and symmetry breaking make it; the kept clauses' sizes must be the paper's after elimination, 14,672
   clauses on 3,745 variables. The encoding must be closed under negating every variable (each clause's negation is
   a clause). Together: removing clauses only weakens a formula, and a model of the encoding, negated if need be, is
   a model with the unit true, so if transformed.cnf is unsatisfiable, so is the encoding (transformed_sound).
3. The proof, sampled. The cubes must be 10^6 lines "a <literals> 0", each a set of literals on the formula's
   variables with no variable twice. CUBES cubes are drawn without replacement, uniformly, by the seed (numbered by
   their line, from 1). For each, transformed.cnf with the cube's literals added as unit clauses is solved by CaDiCaL
   with its LRAT proof streamed through a pipe into cake_lpr as it is written (hexagon/check.py's solve), two at a
   time; a check that runs out of cake_lpr's heap or stack is repeated alone with a larger one. A cube counts as UNSAT
   when CaDiCaL reports UNSATISFIABLE and as verified when cake_lpr then reports "s VERIFIED UNSAT". A cube found
   satisfiable has its model checked against every clause and the cube; one that passed would refute the claim.
4. The cover, twice. (a) As the paper describes it, a binary tree with the cubes as leaves: sibling cubes (the same
   literals but the last, whose signs differ) are merged into their common part, round after round, each merge a
   resolution step; the cubes cover every assignment when this ends in the empty cube (cover_merges counts the
   merges). (b) The negations of all 10^6 cubes, one clause each, refuted with a proof verified as in rule 3, alone
   and with cake_lpr's larger heap. cover_verified needs both.
5. The partition of {1, ..., 7824}. backbone7824.cnf must hold every clause of rule 1's formula for 7824 and nothing
   else but unit clauses. CaDiCaL solves it; its model, read as a colouring (i in the first part when x_i is true;
   numbers in no triple, 7821 to 7824 among them, in the second), is checked against every triple of rule 1 for
   7824: witness_ok when none is monochromatic.
6. Controls, each of which must behave as stated (controls_passed counts those that do): rule 1's sizes as printed;
   transformed.cnf's sizes as printed; the comparison of rule 2 finds one clause missing when one clause is taken out
   of plain7825.cnf; the tree of rule 4 without one cube (drawn by the seed) does not end in the empty cube; the
   cube the authors' log marks SATISFIABLE for n = 7824 (number 343864) gives a model of bce7824.cnf with the unit
   2520 and the cube, checked against every clause; the witness with the number of its first backbone unit (other
   than 2520) moved to the other part has a monochromatic triple, as a backbone variable must; and hexagon's three
   pigeonhole proof controls.
7. Randomness, only from ECDYSIS_SEED, as in hexagon/check.py: the cubes from the label "ptn/cubes", the cube left out
   of the tree in control 6 from "ptn/drop". Timings and each cube's conflicts go to results/detail.json.

test_passed is 1 if plain7825.cnf is the encoding, transformed_sound holds, every sampled cube is UNSAT with a
verified proof, cover_verified is 1 and witness_ok is 1; else 0. The controls are reported beside it.

What it cannot check:
- the whole proof: only CUBES of the 10^6 cubes are re-solved (each in about two to four minutes here, against about
  two minutes of splitting and solving in the authors' runs). A sample this size would catch a defect shared by many
  cubes, not one bad cube;
- the authors' own proof: their DRAT proofs (almost 200 TB) were checked as they were made and not kept, and their
  68 GB certificate (the second-level cubes) is not used; this re-solves each sampled cube with a later solver;
- the tools beyond themselves: cake_lpr is verified in CakeML down to its assembly, but its C wrapper, the compiler,
  the kernel and this script are trusted.

Writes results/outputs.json (the 19 values a receipt carries) and results/detail.json. Run with: python3 ptn/check.py
"""

import argparse
import collections
import hashlib
import importlib.util
import json
import math
import os
import platform
import re
import shutil
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("ptn_hexagon", os.path.join(HERE, "..", "hexagon", "check.py"))
H = importlib.util.module_from_spec(_spec)
sys.modules["ptn_hexagon"] = H
_spec.loader.exec_module(H)

PAGE = "https://www.cs.utexas.edu/~marijn/ptn/"
INPUTS = (
    ("plain7825.cnf", "49735fb2d9dcce1ea5a610297d0128a60876ec82b29f6824f20e01e89e7223a7", 339081,
     PAGE + "plain7825.cnf"),
    ("transformed.cnf", "7d28ad60ec99d7c83c8b0633acbd3661f9cb18846563207536360d3f306e98de", 262146,
     PAGE + "transformed.cnf"),
    ("million.cubes", "04a4e0dec40bfb88cb8b75efa014d7fb526fe036106f9987e7c82335065d3f35", 129691814,
     PAGE + "million.cubes"),
    ("backbone7824.cnf", "9226d9d30c34fbc1338b5c3d2d36acb3781759a2204d85b089579fdc3f5f5955", 355670,
     PAGE + "backbone7824.cnf"),
    ("bce7824.cnf", "62644a56ba7f81062454dc806103c9c9ae1769c4b8b54baf6cb67b816971da97", 261775, PAGE + "bce7824.cnf"),
) + tuple(i for i in H.INPUTS if i[0] in ("cadical_2.1.3.orig.tar.gz", "cake_lpr.S", "basis_ffi.c"))

N_UNSAT, N_SAT = 7825, 7824
PRINTED = {7824: (6492, 18930), 7825: (6494, 18944)}      # occurring variables, clauses (section 4)
PRINTED_BCE = (3745, 14672)                              # transformed.cnf without its unit: variables, clauses
CUBES_TOTAL = 1000000
CUBES = 20                                               # cubes re-solved and re-checked, drawn by the seed
SAT_CUBE, SAT_UNIT = 343864, 2520                        # the authors' log: the one satisfiable cube for n = 7824
WORKERS = 2
HEAP_MB, STACK_MB = 1024, 512
BIG_HEAP_MB, BIG_STACK_MB = 2560, 768                    # alone, for the cover formula (10^6 clauses)
LIMIT = 200

OUTPUTS = (
    "encoding_equal", "encoding_clauses", "transformed_unit", "transformed_kept", "transformed_sound",
    "cubes_total", "cubes_sampled", "cubes_ids", "cubes_unsat", "cubes_verified", "cubes_conflicts",
    "cover_merges", "cover_verified", "witness_ok", "witness_triples",
    "controls_passed", "controls_total", "tools", "test_passed",
)


class Refused(Exception):
    """An input that is not what the rules say it must be."""


def load(directory, name):
    spec = next(i for i in INPUTS if i[0] == name)
    with open(os.path.join(directory, name), "rb") as f:
        data = f.read()
    got = hashlib.sha256(data).hexdigest()
    if got != spec[1] or len(data) != spec[2]:
        raise Refused(f"{name}: sha256 {got} and {len(data)} bytes, not the committed {spec[1]} and {spec[2]}")
    return data


# ---------------------------------------------------------------- rule 1: the encoding

def triples(n):
    """Every (a, b, c) with a <= b <= c <= n and a^2 + b^2 = c^2, in exact integers."""
    out = []
    for a in range(1, n + 1):
        b = a
        while a * a + b * b <= n * n:
            s = a * a + b * b
            c = math.isqrt(s)
            if c * c == s:
                out.append((a, b, c))
            b += 1
    return out


def encode(n):
    """Rule 1: (the triples, the clauses)."""
    ts = triples(n)
    clauses = []
    for a, b, c in ts:
        clauses += [(a, b, c), (-a, -b, -c)]
    return ts, clauses


def occurring(clauses):
    return len({abs(lit) for c in clauses for lit in c})


def multiset(clauses):
    return collections.Counter(frozenset(c) for c in clauses)


# ---------------------------------------------------------------- rule 2: the formulas of record

def check_formulas(inputs):
    """Rules 1, 2 and 5's structure, and two controls, in a child process: a summary, nothing big."""
    out = {}
    sizes = {}
    for n in PRINTED:
        ts, cl = encode(n)
        sizes[n] = (occurring(cl), len(cl))
    out["sizes"] = {str(n): list(v) for n, v in sizes.items()}
    out["sizes_ok"] = all(sizes[n] == PRINTED[n] for n in PRINTED)
    ts, enc = encode(N_UNSAT)
    nv, plain, header, _ = H.parse_cnf(load(inputs, "plain7825.cnf"), "plain7825.cnf")
    want, have = multiset(enc), multiset(plain)
    out["plain_header"] = header.decode()
    out["encoding_equal"] = want == have
    out["encoding_clauses"] = len(plain)
    cut = plain[:-1]                                        # control: one clause taken out
    missing_cut = sum((want - multiset(cut)).values())
    out["missing_when_cut"] = missing_cut
    out["negation_closed"] = all(have[frozenset(-lit for lit in c)] > 0 for c in plain)
    _, transformed, _, _ = H.parse_cnf(load(inputs, "transformed.cnf"), "transformed.cnf")
    units = [c for c in transformed if len(c) == 1]
    kept = [c for c in transformed if len(c) != 1]
    out["transformed_units"] = [u[0] for u in units]
    out["transformed_kept"] = len(kept)
    out["transformed_kept_variables"] = occurring(kept)
    out["kept_in_plain"] = not (multiset(kept) - have)
    out["transformed_sound"] = (len(units) == 1 and units[0][0] > 0 and out["kept_in_plain"] and out["negation_closed"]
                                and out["encoding_equal"])
    out["transformed_sizes_ok"] = (out["transformed_kept_variables"], len(kept)) == PRINTED_BCE
    _, backbone, _, _ = H.parse_cnf(load(inputs, "backbone7824.cnf"), "backbone7824.cnf")
    ts24, enc24 = encode(N_SAT)
    extra = multiset(backbone) - multiset(enc24)
    out["backbone_has_encoding"] = not (multiset(enc24) - multiset(backbone))
    out["backbone_extra_units_only"] = all(len(c) == 1 for c in extra.elements())
    out["backbone_units"] = sorted(next(iter(c)) for c in extra.elements())
    return out


def colouring(model, n):
    """Rule 5: the parts of 1 .. n read from a model (true: the first part); numbers the model leaves out: second."""
    return {i: (i in model) for i in range(1, n + 1)}


def monochromatic(colour, ts):
    return sum(1 for a, b, c in ts if colour[a] == colour[b] == colour[c])


# ---------------------------------------------------------------- rule 4: the cover as a tree

def parse_cubes(path, variables):
    """The cubes, as tuples, read line by line: "a <literals> 0", literals within range, no variable twice. Each
    literal is one shared int object (a million cubes of separate ints would take most of the sandbox's memory)."""
    known = {b"%d" % v: v for v in range(-variables, variables + 1) if v}
    cubes = []
    with open(path, "rb") as f:
        for line in f:
            toks = line.split()
            if not toks:
                continue
            if toks[0] != b"a" or toks[-1] != b"0" or len(toks) < 3:
                raise Refused("million.cubes: a line that is not \"a <literals> 0\"")
            try:
                cube = tuple(known[t] for t in toks[1:-1])
            except KeyError:
                raise Refused("million.cubes: a literal that is not an integer within range") from None
            if len({abs(lit) for lit in cube}) != len(cube):
                raise Refused("million.cubes: a variable twice in one cube")
            cubes.append(cube)
    return cubes


def tree_cover(cubes):
    """Rule 4a: merge sibling cubes into their common part until nothing changes; (merges, rounds, pieces left)."""
    current, merges, rounds = set(cubes), 0, 0
    while True:
        by = collections.defaultdict(set)
        for c in current:
            if c:
                by[c[:-1]].add(c[-1])
        new = {c for c in current if not c}
        changed = False
        for prefix, lasts in by.items():
            for lit in lasts:
                if -lit in lasts:
                    if lit > 0:
                        new.add(prefix)
                        merges += 1
                        changed = True
                else:
                    new.add(prefix + (lit,))
        rounds += 1
        current = new
        if not changed:
            return merges, rounds, current


def prepare_cubes(inputs, results, chosen, drop):
    """Rule 4a, its control and the cover formula for 4b, in a child process: the chosen cubes and the counts."""
    path = os.path.join(inputs, "million.cubes")
    load(inputs, "million.cubes")
    cubes = parse_cubes(path, N_UNSAT)
    if len(cubes) != CUBES_TOTAL:
        raise Refused(f"million.cubes: {len(cubes)} cubes, not {CUBES_TOTAL}")
    merges, rounds, left = tree_cover(cubes)
    d_merges, _, d_left = tree_cover(cubes[:drop] + cubes[drop + 1:])
    cover = os.path.join(results, "cover.cnf")             # on the results disk, not in /tmp (memory)
    with open(cover, "wb") as f:
        f.write(b"p cnf %d %d\n" % (N_UNSAT, len(cubes)))
        for c in cubes:
            f.write(b" ".join(b"%d" % -lit for lit in c) + b" 0\n")
    return {"cubes": len(cubes), "merges": merges, "rounds": rounds, "left": len(left), "empty": left == {()},
            "drop_left": len(d_left), "drop_merges": d_merges, "chosen": [cubes[i] for i in chosen],
            "sat_cube": cubes[SAT_CUBE - 1], "cover": cover,
            "lengths": dict(sorted(collections.Counter(len(c) for c in cubes).items()))}


def check_models(inputs, found):
    """For each (cube, model text) a solver called satisfiable: the clauses of transformed.cnf and the cube it fails."""
    _, formula, _, _ = H.parse_cnf(load(inputs, "transformed.cnf"), "transformed.cnf")
    return [H.satisfies(H.model(text), formula) + H.satisfies(H.model(text), [(lit,) for lit in cube])
            for cube, text in found]


def summarise(values):
    out = {k: values[k] for k in OUTPUTS}
    for k, v in out.items():
        if isinstance(v, str) and len(v) > LIMIT:
            raise AssertionError(f"{k}: longer than {LIMIT} characters")
    return out


# ---------------------------------------------------------------- the run

def run(seed, inputs="inputs", results="results", cubes_wanted=CUBES, tools=None, log=print):
    """Every rule, in order; returns (outputs, detail). tools, if given, replaces the build (tests only)."""
    started = time.monotonic()
    for name, *_ in INPUTS:                    # every input checked before anything runs
        load(inputs, name)
    detail = {"inputs": [{"name": n, "sha256": h, "bytes": b, "source": s} for n, h, b, s in INPUTS]}
    values, controls = {}, []
    os.makedirs(results, exist_ok=True)
    if tools is None:
        if platform.machine() not in ("x86_64", "AMD64"):
            raise SystemExit("ptn/check.py: cake_lpr.S is x86-64 assembly; run this on an x86-64 machine")
        tools = H.build_tools(os.path.abspath(inputs), os.path.abspath(os.path.join(results, "build")))
        log(f"ptn: built CaDiCaL {tools['cadical_version']} and cake_lpr, gcc {tools['gcc']}, "
            f"at {time.monotonic() - started:.0f} s")
    work = tempfile.mkdtemp(prefix="ptn-")
    chosen = H.sample(seed, "ptn/cubes", CUBES_TOTAL, cubes_wanted)
    drop = H.sample(seed, "ptn/drop", CUBES_TOTAL, 1)[0]
    try:
        # Rules 1 and 2, and rule 5's structure.
        f = H.in_child(check_formulas, inputs)
        log(f"ptn: encoding {'equal' if f['encoding_equal'] else 'NOT equal'} ({f['encoding_clauses']} clauses); "
            f"transformed.cnf: unit {f['transformed_units']}, {f['transformed_kept']} kept clauses on "
            f"{f['transformed_kept_variables']} variables, in plain7825.cnf {f['kept_in_plain']}; sound "
            f"{f['transformed_sound']}")
        controls.append({"control": "rule 1's sizes are the paper's (section 4)", "passed": f["sizes_ok"],
                         "sizes": f["sizes"]})
        controls.append({"control": "transformed.cnf's sizes are the paper's after elimination",
                         "passed": f["transformed_sizes_ok"]})
        controls.append({"control": "one clause taken out of plain7825.cnf: found missing",
                         "passed": f["missing_when_cut"] == 1, "missing": f["missing_when_cut"]})

        # Rule 5: the partition of 1 .. 7824.
        ts24, _ = encode(N_SAT)
        r = H.solve(tools, os.path.abspath(os.path.join(inputs, "backbone7824.cnf")), work, "witness", proof=False)
        witness_ok, mono, flipped = 0, None, None
        if r["answer"] == "sat" and f["backbone_has_encoding"] and f["backbone_extra_units_only"]:
            m = H.model(r["model"])
            colour = colouring(m, N_SAT)
            mono = monochromatic(colour, ts24)
            witness_ok = 1 if mono == 0 else 0
            v = next((u for u in f["backbone_units"] if abs(u) != SAT_UNIT), None)
            if v is not None:
                damaged = dict(colour)
                damaged[abs(v)] = not damaged[abs(v)]
                flipped = monochromatic(damaged, ts24)
        log(f"ptn: partition of 1..{N_SAT}: {r['answer']}, {mono} monochromatic triples of {len(ts24)}")
        controls.append({"control": "the witness with its first backbone number (not 2520) moved: monochromatic",
                         "passed": bool(flipped), "monochromatic": flipped})
        values.update({"witness_ok": witness_ok, "witness_triples": len(ts24)})

        # Rule 4: the cover, as a tree (in a child) and as a formula refuted alone with the larger heap.
        prep = H.in_child(prepare_cubes, inputs, os.path.abspath(results), chosen, drop)
        log(f"ptn: {prep['cubes']} cubes; the tree ends in {'the empty cube' if prep['empty'] else prep['left']} after "
            f"{prep['merges']} merges in {prep['rounds']} rounds; without cube {drop + 1}, {prep['drop_left']} pieces")
        controls.append({"control": f"the tree without cube {drop + 1}: not a cover", "passed": prep["drop_left"] > 0,
                         "pieces": prep["drop_left"]})
        cover = H.solve(tools, prep["cover"], work, "cover", heap=BIG_HEAP_MB, stack=BIG_STACK_MB)
        os.unlink(prep["cover"])
        log(f"ptn: cover formula {cover['answer']}, verified {cover['verified']}, {cover['seconds']} s")

        # Control: the satisfiable cube of the 7824 run.
        with open(os.path.join(inputs, "bce7824.cnf"), "rb") as fh:
            bce = fh.read()
        nv24, bce_clauses, _, body24 = H.parse_cnf(bce, "bce7824.cnf")
        sat_units = (SAT_UNIT,) + prep["sat_cube"]
        path = os.path.join(work, "sat7824.cnf")
        with open(path, "wb") as fh:
            fh.write(H.with_units(max(nv24, N_UNSAT), len(bce_clauses), body24, sat_units))
        r = H.solve(tools, path, work, "sat7824", proof=False)
        os.unlink(path)
        violated = (H.satisfies(H.model(r["model"]), bce_clauses + [(u,) for u in sat_units])
                    if r["answer"] == "sat" else None)
        controls.append({"control": f"cube {SAT_CUBE} with bce7824.cnf and the unit {SAT_UNIT}: a checked model",
                         "passed": r["answer"] == "sat" and violated == 0, "answer": r["answer"],
                         "violated": violated, "seconds": r["seconds"]})
        log(f"ptn: control, cube {SAT_CUBE} for n = {N_SAT}: {r['answer']}, {violated} clauses violated")

        rows_p, _ = H.proof_controls(tools, work)
        controls += rows_p

        # Rule 3: the sampled cubes, two at a time.
        with open(os.path.join(inputs, "transformed.cnf"), "rb") as fh:
            tv, tclauses, _, body = H.parse_cnf(fh.read(), "transformed.cnf")
        units = dict(zip(chosen, prep["chosen"]))
        del prep["chosen"]

        def job(i, heap=HEAP_MB, stack=STACK_MB):
            p = os.path.join(work, f"cube-{i + 1}.cnf")
            with open(p, "wb") as fh:
                fh.write(H.with_units(tv, len(tclauses), body, units[i]))
            try:
                return H.solve(tools, p, work, f"cube-{i + 1}", heap, stack)
            finally:
                os.unlink(p)

        per_cube = []
        with ThreadPoolExecutor(WORKERS) as pool:
            for i, r in zip(chosen, pool.map(job, chosen)):
                per_cube.append(r)
                log(f"ptn: cube {i + 1}: {r['answer']}, verified {r['verified']}, {r['conflicts']} conflicts, "
                    f"{r['seconds']} s")
        for k, i in enumerate(chosen):          # a check that ran out of room, again, alone, with more
            if per_cube[k]["resources"]:
                log(f"ptn: cube {i + 1}: cake_lpr ran out of room; again with {BIG_HEAP_MB} MB")
                per_cube[k] = dict(job(i, BIG_HEAP_MB, BIG_STACK_MB), retried=True)
        found = [(units[i], r["model"]) for i, r in zip(chosen, per_cube) if r["answer"] == "sat"]
        if found:
            violations = iter(H.in_child(check_models, inputs, found))
            for r in per_cube:
                if r["answer"] == "sat":
                    r["model_violates"] = next(violations)
                    log(f"ptn: a satisfiable cube; its model violates {r['model_violates']} clauses")
        for r in per_cube + [cover]:
            r["model"] = None
    finally:
        shutil.rmtree(work, ignore_errors=True)

    conflicts = [r["conflicts"] for r in per_cube]
    values.update({
        "encoding_equal": 1 if f["encoding_equal"] else 0, "encoding_clauses": f["encoding_clauses"],
        "transformed_unit": f["transformed_units"][0] if len(f["transformed_units"]) == 1 else 0,
        "transformed_kept": f["transformed_kept"], "transformed_sound": 1 if f["transformed_sound"] else 0,
        "cubes_total": prep["cubes"], "cubes_sampled": len(chosen), "cubes_ids": ",".join(str(i + 1) for i in chosen),
        "cubes_unsat": sum(1 for r in per_cube if r["answer"] == "unsat"),
        "cubes_verified": sum(1 for r in per_cube if r["answer"] == "unsat" and r["verified"]),
        "cubes_conflicts": sum(conflicts) if all(c is not None for c in conflicts) else -1,
        "cover_merges": prep["merges"],
        "cover_verified": 1 if prep["empty"] and cover["answer"] == "unsat" and cover["verified"] else 0,
        "controls_passed": sum(1 for c in controls if c["passed"]), "controls_total": len(controls),
        "tools": f"CaDiCaL {tools['cadical_version']} (Debian orig tarball); {H.CHECKER}",
    })
    values["test_passed"] = 1 if (values["encoding_equal"] == 1 and values["transformed_sound"] == 1
                                  and values["cubes_verified"] == len(chosen) == cubes_wanted
                                  and values["cover_verified"] == 1 and values["witness_ok"] == 1) else 0
    detail.update({
        "values": values, "formulas": f, "controls": controls,
        "cover": {"tree": {k: prep[k] for k in ("merges", "rounds", "left", "empty", "drop_left", "drop_merges")},
                  "lengths": prep["lengths"], "dropped_cube": drop + 1,
                  "formula": {k: v for k, v in cover.items() if k != "model"}},
        "cubes": [{"cube": i + 1, "literals": len(units[i]), **{k: v for k, v in r.items() if k != "model"}}
                  for i, r in zip(chosen, per_cube)],
        "tools": {k: v for k, v in tools.items() if k not in ("cadical", "cake_lpr")},
        "seconds": round(time.monotonic() - started, 1)})
    return summarise(values), detail


def main():
    parser = argparse.ArgumentParser(description="The boolean Pythagorean triples: the proof sampled, the cover whole")
    parser.add_argument("--cubes", type=int, default=CUBES, help=f"cubes to re-solve (default {CUBES})")
    args = parser.parse_args()
    seed = os.environ.get("ECDYSIS_SEED", "")
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        sys.exit("ECDYSIS_SEED must be the 64-hex seed the archive issued")
    try:
        out, detail = run(seed, cubes_wanted=args.cubes, log=lambda line: print(line, file=sys.stderr, flush=True))
    except Refused as e:
        sys.exit(f"ptn/check.py: refused: {e}")
    os.makedirs("results", exist_ok=True)
    with open(os.path.join("results", "outputs.json"), "w", encoding="ascii") as fh:
        json.dump(out, fh, indent=2, sort_keys=True)
        fh.write("\n")
    with open(os.path.join("results", "detail.json"), "w", encoding="ascii") as fh:
        json.dump(detail, fh, indent=1, sort_keys=True)
        fh.write("\n")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
