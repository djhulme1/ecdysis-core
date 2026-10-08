#!/usr/bin/env python3
"""Seventeen points always contain a convex hexagon: Szekeres and Peters's model refuted again by SAT, with the proof
checked by a verified checker, for an Ecdysis receipt.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:141c76dc2a47364f) is from Szekeres and
Peters, "Computer solution to the 17-point Erdős-Szekeres problem", The ANZIAM Journal 48(2) (2006): "We describe a
computer proof of the 17-point version of a conjecture originally made by Klein-Szekeres in 1932 (now commonly known
as the "Happy End Problem") that a planar configuration of 17 points, no 3 points collinear, always contains a convex
6-subset." Its registered test: refuted if 17 points in the plane, no three collinear, can be placed with no six in
convex position; or if the paper's Theorem 2 fails: if a signature function on 17 points satisfying (2.1) or (2.2) on
every four points (an orientation for each triple of the ordered points, changing sign at most once along the four
triples of any four points) has no convex 6-subset, the union of a cup and a cap with common ends.

The inputs, each checked against its SHA-256 and size before anything else runs, are the solver and the checker of
hexagon/check.py, whose code this module imports: CaDiCaL 2.1.3's source as Debian archived it and the two files of
the CakeML-verified LRAT checker cake_lpr, compiled from source into results/build by the run, in the pinned image,
with no network. The paper itself is not an input: the model is defined below, from its section 2. Every rule below
was fixed before any seed existed.

1. The formula es(n, k), in the variables o(a, b, c) for the triples a < b < c of the points 0 .. n-1 (true for +):
   a. the paper's conditions (2.1) or (2.2) on every four points a < b < c < d, that is, no pattern + - + or - + -
      along o(abc), o(abd), o(acd), o(bcd) (eight clauses for each four points);
   b. the first point a vertex of the convex hull and the rest sorted around it: o(0, b, c) true for every b < c
      (rule 5 says why this loses nothing);
   c. chains, as the paper defines them: c(s, l, a, y, z) is implied whenever a, ..., y, z is a chain of l points from
      a whose consecutive triples all have sign s (s = + a cup, s = - a cap), by o(a, y, z) for l = 3 and by
      c(s, l - 1, a, x, y) and o(x, y, z) for l > 3; and e(s, l, a, z) by any c(s, l, a, y, z);
   d. no convex k-subset: for every a < f and every cup of i points and cap of j points from a to f with
      i + j - 2 = k (i, j >= 2; a chain of 2 points is the pair itself), the clause that they do not both exist.
   A model is an admissible signature function with no convex k-subset; the chain variables only ever appear negated
   in (d), so the formula has a model exactly when such a function exists.
2. The proof. es(17, 6) is renamed and shuffled by the seed (rule 6): its variables by a permutation, the order of its
   clauses and the order of the literals in each. CaDiCaL solves it with its LRAT proof streamed down a pipe into
   cake_lpr, as in hexagon/check.py; a check that runs out of cake_lpr's heap or stack is repeated with a larger one.
   unsat_verified is 1 when CaDiCaL reports UNSATISFIABLE and cake_lpr reports "s VERIFIED UNSAT" on that formula. A
   model, if one were found, would be renamed back and checked against every clause: it would refute Theorem 2.
3. Controls, each of which must behave as stated (controls_passed counts those that do):
   a. the known thresholds below six: es(4, 4) has a model and es(5, 4) is refuted (Klein: five points); es(8, 5) has
      a model and es(9, 5) is refuted (Makai and Turán: nine points, the paper's Theorem 1 in this model); each
      refutation's proof verified by cake_lpr, each model checked against every clause;
   b. es(16, 6) has a model, checked against every clause: sixteen points are not enough, as Erdős and Szekeres's
      construction shows, so the formula is not refuted for a reason that has nothing to do with seventeen points;
   c. geometry: GEO_SETS sets of GEO_POINTS points with integer coordinates drawn by the seed, in general position and
      with distinct x coordinates (sets that are not are redrawn): with the leftmost point first and the rest sorted
      by the slope from it, every o(0, b, c) is true, every four points satisfy (2.1) or (2.2), and every 6-subset is
      the union of a cup and a cap exactly when its six points are the vertices of their convex hull;
   d. hexagon's three pigeonhole proof controls: an LRAT proof accepted, and rejected without its last step or
      without a lemma that step cites.
4. test_passed is 1 if unsat_verified is 1; else 0. The controls are reported beside it.
5. Why rule 1b loses nothing: relabelling the points of an admissible signature function changes neither which of its
   subsets are convex nor its being a chirotope; choosing as the first point a vertex of the hull and sorting the
   others around it gives an admissible function whose triples through the first point are all positive (Heule and
   Scheucher prove this for point sets, in Lean, in their empty hexagon work; control (c) checks it on point sets).
6. Randomness, only from ECDYSIS_SEED, as in hexagon/check.py: the shuffle from SHA-256(seed || "|" || "es/shuffle" ||
   "|" || counter), Fisher-Yates from the top, the variables first, then the clauses, then each clause's literals;
   control (c)'s coordinates from the label "es/points". cnf_sha256 (of the shuffled formula's DIMACS text) lets
   another run under the same seed show it solved the same formula. Timings go to results/detail.json.

What it cannot check: the paper's own search (its program was not released; this proves the result again in the
paper's model rather than re-running theirs); rule 5 for signature functions that no point set realises, which is
argued rather than checked here; and the tools beyond themselves: cake_lpr is verified in CakeML down to its assembly,
but its C wrapper, the compiler, the kernel and this script (the encoder and the shuffle) are trusted.

Writes results/outputs.json (17 values) and results/detail.json (timings among them). Run with: python3 es/check.py
"""

import argparse
import hashlib
import importlib.util
import itertools
import json
import os
import re
import sys
import tempfile
import time
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("es_hexagon", os.path.join(HERE, "..", "hexagon", "check.py"))
H = importlib.util.module_from_spec(_spec)
sys.modules["es_hexagon"] = H
_spec.loader.exec_module(H)

INPUTS = tuple(i for i in H.INPUTS if i[0] in ("cadical_2.1.3.orig.tar.gz", "cake_lpr.S", "basis_ffi.c"))
N_PROOF, K = 17, 6
SMALL = ((4, 4, "sat"), (5, 4, "unsat"), (8, 5, "sat"), (9, 5, "unsat"), (16, 6, "sat"))
GEO_SETS, GEO_POINTS, GEO_RANGE = 24, 12, 10 ** 6
HEAP_MB, STACK_MB = 1024, 512
RETRY_HEAP_MB, RETRY_STACK_MB = 2560, 768

OUTPUTS = (
    "cnf_vars", "cnf_clauses", "cnf_sha256", "unsat_answer", "unsat_verified", "proof_conflicts",
    "small_cases", "geo_sets", "geo_subsets", "geo_mismatches", "geo_axiom_violations", "geo_first_not_fixed",
    "controls_passed", "controls_total", "solver", "checker", "test_passed",
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


# ---------------------------------------------------------------- rule 1: the formula

def encode(n, k):
    """es(n, k): (number of variables, clauses, {name: variable})."""
    names = {}

    def var(name):
        v = names.get(name)
        if v is None:
            v = names[name] = len(names) + 1
        return v

    o = {t: var(("o",) + t) for t in itertools.combinations(range(n), 3)}
    clauses = []
    for a, b, c, d in itertools.combinations(range(n), 4):                       # (a)
        T = (o[(a, b, c)], o[(a, b, d)], o[(a, c, d)], o[(b, c, d)])
        for i, j, l in itertools.combinations(range(4), 3):
            clauses.append([-T[i], T[j], -T[l]])
            clauses.append([T[i], -T[j], T[l]])
    for b, c in itertools.combinations(range(1, n), 2):                         # (b)
        clauses.append([o[(0, b, c)]])
    ends = {}
    for s in (1, -1):                                                            # (c)
        for l in range(3, k + 1):
            for a in range(n):
                for y in range(a + 1, n):
                    for z in range(y + 1, n):
                        if z - a < l - 1:
                            continue
                        cur = var(("c", s, l, a, y, z))
                        if l == 3:
                            clauses.append([-s * o[(a, y, z)], cur])
                        else:
                            for x in range(a + 1, y):
                                prev = names.get(("c", s, l - 1, a, x, y))
                                if prev is not None:
                                    clauses.append([-prev, -s * o[(x, y, z)], cur])
                        e = ends.get((s, l, a, z))
                        if e is None:
                            e = ends[(s, l, a, z)] = var(("e", s, l, a, z))
                        clauses.append([-cur, e])
    for a, f in itertools.combinations(range(n), 2):                            # (d)
        for i in range(2, k + 1):
            j = k + 2 - i
            if j < 2:
                continue
            lits, possible = [], True
            for s, size in ((1, i), (-1, j)):
                if size > 2:
                    e = ends.get((s, size, a, f))
                    if e is None:
                        possible = False
                        break
                    lits.append(-e)
            if possible:
                clauses.append(lits)
    return len(names), clauses, names


def shuffled(items, stream):
    items = list(items)
    for i in range(len(items) - 1, 0, -1):
        j = stream.below(i + 1)
        items[i], items[j] = items[j], items[i]
    return items


def renamed(nv, clauses, seed):
    """Rule 6: (the shuffled clauses, the permutation old -> new)."""
    stream = H.Stream(seed, "es/shuffle")
    perm = shuffled(range(1, nv + 1), stream)
    new = {old: i + 1 for i, old in enumerate(perm)}
    out = [[(1 if lit > 0 else -1) * new[abs(lit)] for lit in c] for c in shuffled(clauses, stream)]
    return [shuffled(c, stream) for c in out], new


def dimacs(nv, clauses):
    return b"p cnf %d %d\n" % (nv, len(clauses)) + H.clause_lines(clauses)


# ---------------------------------------------------------------- rule 3c: geometry

def orient(p, q, r):
    return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])


def hull_size(pts):
    pts = sorted(pts)

    def half(ps):
        h = []
        for p in ps:
            while len(h) >= 2 and orient(h[-2], h[-1], p) <= 0:
                h.pop()
            h.append(p)
        return h
    return len(half(pts)) + len(half(pts[::-1])) - 2


def normalised(pts):
    """The leftmost point first, then the others by the slope from it, increasing."""
    p0 = min(pts)
    return [p0] + sorted((p for p in pts if p != p0), key=lambda p: Fraction(p[1] - p0[1], p[0] - p0[0]))


def signature(pts):
    return {t: orient(*(pts[i] for i in t)) > 0 for t in itertools.combinations(range(len(pts)), 3)}


def is_chain(sig, seq, sign):
    return all(sig[(seq[i], seq[i + 1], seq[i + 2])] == sign for i in range(len(seq) - 2))


def cup_cap(sig, subset):
    """The paper's definition: the subset (in order) is the union of a cup and a cap with common ends."""
    a, f, mid = subset[0], subset[-1], subset[1:-1]
    for r in range(len(mid) + 1):
        for low in itertools.combinations(mid, r):
            if is_chain(sig, [a, *low, f], True) and is_chain(sig, [a, *(x for x in mid if x not in low), f], False):
                return True
    return False


def point_sets(seed, sets=GEO_SETS, n=GEO_POINTS):
    stream, out = H.Stream(seed, "es/points"), []
    while len(out) < sets:
        pts = [(stream.below(2 * GEO_RANGE + 1) - GEO_RANGE, stream.below(2 * GEO_RANGE + 1) - GEO_RANGE)
               for _ in range(n)]
        if len({p[0] for p in pts}) < n or any(orient(*t) == 0 for t in itertools.combinations(pts, 3)):
            continue
        out.append(pts)
    return out


def geometry(seed, sets=GEO_SETS, n=GEO_POINTS, k=K):
    fixed = axioms = mismatches = subsets = 0
    for pts in point_sets(seed, sets, n):
        P = normalised(pts)
        sig = signature(P)
        fixed += sum(1 for b, c in itertools.combinations(range(1, n), 2) if not sig[(0, b, c)])
        for a, b, c, d in itertools.combinations(range(n), 4):
            seq = (sig[(a, b, c)], sig[(a, b, d)], sig[(a, c, d)], sig[(b, c, d)])
            axioms += sum(seq[i] != seq[i + 1] for i in range(3)) > 1
        for S in itertools.combinations(range(n), k):
            subsets += 1
            mismatches += cup_cap(sig, S) != (hull_size([P[i] for i in S]) == k)
    return {"geo_sets": sets, "geo_subsets": subsets, "geo_mismatches": mismatches, "geo_axiom_violations": axioms,
            "geo_first_not_fixed": fixed}


# ---------------------------------------------------------------- the run

def solve(tools, nv, clauses, work, tag, proof=True):
    cnf = os.path.join(work, f"{tag}.cnf")
    with open(cnf, "wb") as f:
        f.write(dimacs(nv, clauses))
    r = H.solve(tools, cnf, work, tag, heap=HEAP_MB, stack=STACK_MB, proof=proof)
    if r["answer"] == "unsat" and not r["verified"] and r["resources"]:
        r = H.solve(tools, cnf, work, tag, heap=RETRY_HEAP_MB, stack=RETRY_STACK_MB, proof=proof)
    if r["answer"] == "sat":
        r["model_unsatisfied"] = H.satisfies(H.model(r["model"]), clauses)
        r["model"] = None
    os.unlink(cnf)
    return r


def run(seed, inputs="inputs", results="results", tools=None, log=print):
    started = time.monotonic()
    for name, *_ in INPUTS:
        load(inputs, name)
    os.makedirs(results, exist_ok=True)
    if tools is None:
        tools = H.build_tools(os.path.abspath(inputs), os.path.abspath(os.path.join(results, "build")))
        log(f"es: built CaDiCaL {tools['cadical_version']} and cake_lpr")
    work = tempfile.mkdtemp(prefix="es-", dir=results)
    controls, small = [], []
    for n, k, want in SMALL:                                                      # 3a, 3b
        nv, cl, _ = encode(n, k)
        r = solve(tools, nv, cl, work, f"es{n}_{k}")
        ok = (r["answer"] == "unsat" and r["verified"]) if want == "unsat" else \
             (r["answer"] == "sat" and r["model_unsatisfied"] == 0)
        controls.append({"control": f"es({n}, {k}) {want}", "passed": ok, "answer": r["answer"],
                         "verified": r["verified"], "seconds": r["seconds"]})
        small.append(f"{n}:{k} {r['answer']}{'*' if r['verified'] else ''}")
        log(f"es: es({n}, {k}): {r['answer']}{' (verified)' if r['verified'] else ''}, {r['seconds']} s")
    geo = geometry(seed)                                                          # 3c
    geo_ok = geo["geo_mismatches"] == 0 and geo["geo_axiom_violations"] == 0 and geo["geo_first_not_fixed"] == 0
    controls.append({"control": "geometry", "passed": geo_ok, **geo})
    log(f"es: geometry: {geo}")
    rows, ok = H.proof_controls(tools, work)                                     # 3d
    controls += rows
    nv, clauses, names = encode(N_PROOF, K)                                       # 2
    shuffled_clauses, new = renamed(nv, clauses, seed)
    text = dimacs(nv, shuffled_clauses)
    r = solve(tools, nv, shuffled_clauses, work, "es17")
    log(f"es: es(17, 6): {r['answer']}{' (verified)' if r['verified'] else ''}, {r['seconds']} s, "
        f"{r['conflicts']} conflicts")
    if r["answer"] == "sat":
        log("es: a model of es(17, 6): Theorem 2 would be refuted")
    passed = sum(1 for c in controls if c["passed"])
    values = {
        "cnf_vars": nv, "cnf_clauses": len(clauses), "cnf_sha256": hashlib.sha256(text).hexdigest(),
        "unsat_answer": r["answer"], "unsat_verified": int(r["answer"] == "unsat" and r["verified"]),
        "solve_seconds": r["seconds"], "proof_conflicts": r["conflicts"],
        "small_cases": "; ".join(small), **geo,
        "controls_passed": passed, "controls_total": len(controls),
        "solver": f"CaDiCaL {tools['cadical_version']}", "checker": H.CHECKER,
    }
    values["test_passed"] = values["unsat_verified"]
    out = {k: values[k] for k in OUTPUTS}
    for k, v in out.items():
        if isinstance(v, str) and len(v) > 200:
            raise AssertionError(f"{k}: longer than 200 characters")
    detail = {"values": values, "controls": controls, "proof": {k: v for k, v in r.items() if k != "model"},
              "seconds": round(time.monotonic() - started, 1)}
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
    argparse.ArgumentParser(description=__doc__.splitlines()[0]).parse_args()
    try:
        out, _ = run(seed, log=lambda m: print(m, file=sys.stderr, flush=True))
    except Refused as e:
        sys.exit(f"es: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
