#!/usr/bin/env python3
"""Heule's 529-vertex unit-distance graph with chromatic number 5, checked exactly, for an Ecdysis receipt.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:908399b77ca88eb3) is from Heule, "Trimming
Graphs Using Clausal Proof Optimization" (CP 2019, LNCS 11802; arXiv:1907.00929): "We applied this method to reduce
the smallest known unit-distance graph with chromatic number 5 from 553 vertices and 2720 edges to 529 vertices and
2670 edges." Its registered test: refuted if the graph released with the paper (vtx/529.vtx and edge/529.edge in
marijnheule/CNP-SAT at efe60fb) is not 529 distinct points and 2,670 distinct listed edges, lists an edge whose ends
are not at distance exactly 1 (exact arithmetic over Q(sqrt3, sqrt5, sqrt11), where its coordinates lie), has a proper
4-colouring, or has no proper 5-colouring; or if a unit-distance graph with chromatic number 5 on fewer than 529
vertices was public before 1 July 2019, the paper's date.

This is udg/check.py's check of the 553-vertex graph (its exact arithmetic, parsers, formulas, RUP checker and controls
are imported from it, and through it hexagon/check.py's CaDiCaL and cake_lpr), applied to the 529-vertex release, with
three differences the release makes necessary: no symmetry-broken formula is released for it, so rule 3's symmetry
break is written here; the released proof's premises are found by checking it, and the triangle the paper's text
names is reported beside them; and the graph is checked to be vertex-critical, as a trimmed graph should be.

The inputs, each checked against its SHA-256 and size before anything else runs (INPUTS): the claim's four files of
record from marijnheule/CNP-SAT at efe60fb (the vertices, the edges, the 4-colouring formula and the DRAT proof Heule
released), and CaDiCaL 2.1.3's source as Debian archived it and the two files of the CakeML-verified LRAT checker
cake_lpr. No input is executed: the solver and the checker are compiled from source into results/build by this run, in
the pinned image, with no network. Every rule below was fixed before any seed existed; the seed is not used, as nothing
here is random.

1. The points, as udg/check.py's rule 1 reads them: "{x, y}" lines, each coordinate evaluated exactly in
   Q(sqrt3, sqrt5, sqrt11). There must be 529 lines and 529 distinct points; how many need sqrt5 is reported (the
   paper's two parts: 393 points in Q(sqrt3, sqrt11) and a small part sharing the origin).
2. The edges, as udg/check.py's rule 2: the header "p edge 529 2670" and 2,670 distinct "e u v" lines, each edge's
   squared length computed exactly; unit_edges counts those exactly 1. The unit pairs the file does not list are
   reported beside it.
3. No 4-colouring. The 4-colouring formula of the edges (variable 4(v - 1) + c) must equal heule529-4.cnf as a set of
   clauses. It is solved by CaDiCaL with an LRAT proof streamed into cake_lpr: no_4_colouring is 1 when CaDiCaL
   reports UNSATISFIABLE and cake_lpr reports "s VERIFIED UNSAT" on it. The symmetry break the released proof was
   written for is SBP_UNITS, vertex 1 coloured 1, vertex 2 coloured 2 and vertex 6 coloured 3; sbp_triangle is 1 if
   those three vertices are pairwise adjacent (a sound break: any proper colouring can be renamed to meet it).
4. Five colours. The same encoding with five colours is solved by CaDiCaL; its model gives each vertex its first true
   colour, and five_colouring is 1 if every vertex has one and every edge's ends differ.
5. The released proof (reported only). heule529-4-sbp.drat is checked lemma by lemma, by udg/check.py's forward RUP
   checker, against the formula of rule 3 with SBP_UNITS: released_proof_rup is 1 if the lemmas reach a conflict at
   level 0, each RUP before it. Against the paper's text's triangle, TEXT_UNITS (vertex 7 for vertex 6), the position
   of the first lemma that is not RUP is reported as text_units_fail_at (0 if the proof goes through with them too).
6. Vertex-critical (reported only). For every vertex v, the 4-colouring formula of the graph without v is solved by
   CaDiCaL and its model checked against every clause: vertex_critical counts the vertices whose removal leaves the
   graph 4-colourable. A graph trimmed until no vertex can go has all 529.
7. Controls (controls_passed counts those that behave as stated), as udg/check.py's rule 6: vertex 2 moved by 10^-9 in
   x must make one of its edges not unit; rule 4's colouring with one endpoint of the first edge given the other's
   colour must fail; the graph without rule 4's smallest colour class must be 4-colourable, the model checked; and
   hexagon/check.py's three pigeonhole proof controls (an LRAT proof accepted, and rejected without its last step and
   without a lemma its last step cites).

test_passed is 1 if there are 529 distinct points and 2,670 edges, every edge is exactly unit, no_4_colouring is 1 and
five_colouring is 1; else 0. Rules 5 to 7 are reported beside it.

What it cannot check:
- the test's last clause: whether a smaller 5-chromatic unit-distance graph was public before 1 July 2019 is a
  question of the literature (the registration's search found none; Parts' 525 followed on 16 July 2019);
- the paper's method of finding the graph, and the 553 graph's "2720 edges" (that paper's average over its graphs);
- the tools beyond themselves: cake_lpr is verified in CakeML down to its assembly, but the C wrapper, the compiler,
  the kernel and this script (its exact arithmetic among it) are trusted.

Writes results/outputs.json (the values a receipt carries) and results/detail.json. Run with: python3 udg/trim529.py
"""

import argparse
import hashlib
import importlib.util
import json
import os
import platform
import re
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("udg_check", os.path.join(HERE, "check.py"))
U = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(U)
H = U.H
Refused = U.Refused

CNP = "marijnheule/CNP-SAT@efe60fb"
INPUTS = (
    ("heule529.vtx", "ce0cf260e431972c1222521f1b552bc94e7c42040ddf4b4110cee0eaab518dbb", 26780, f"{CNP} vtx/529.vtx"),
    ("heule529.edge", "4c7e01105d880e2ca84804f73318dabaaffd61b8f826923c30de5c06fdcdf1c5", 25472,
     f"{CNP} edge/529.edge"),
    ("heule529-4.cnf", "30206704425272db3150d3d88e3008f0500bb30ae1432eaed3815e7c4e5c9924", 146987,
     f"{CNP} cnf/529-4.cnf"),
    ("heule529-4-sbp.drat", "fc2edf1fb573de69f5f2c786d62c50b7da13e7b2b8bc1b1bb5859bea58ee4cb6", 2704564,
     f"{CNP} proof/529-4-sbp.drat"),
) + tuple(i for i in H.INPUTS if i[0] in ("cadical_2.1.3.orig.tar.gz", "cake_lpr.S", "basis_ffi.c"))

VERTICES, EDGES = 529, 2670
SBP_UNITS = (1, 6, 23)       # 4(v - 1) + c: vertex 1 colour 1, vertex 2 colour 2, vertex 6 colour 3
TEXT_UNITS = (1, 6, 27)      # the paper's text: vertex 7, (1/2, sqrt3/2), in place of vertex 6
SQRT5 = {5, 15, 55, 165}     # the radicands that need sqrt5

OUTPUTS = (
    "points", "points_distinct", "points_with_sqrt5", "radicands", "edges", "unit_edges", "unlisted_unit_pairs",
    "formula_matches", "sbp_triangle", "no_4_colouring", "five_colouring", "released_lemmas", "released_proof_rup",
    "text_units_fail_at", "vertex_critical", "controls_passed", "controls_total", "solver", "test_passed",
)


def load(directory, name):
    spec = next(i for i in INPUTS if i[0] == name)
    with open(os.path.join(directory, name), "rb") as f:
        data = f.read()
    got = hashlib.sha256(data).hexdigest()
    if got != spec[1] or len(data) != spec[2]:
        raise Refused(f"{name}: sha256 {got} and {len(data)} bytes, not the committed {spec[1]} and {spec[2]}")
    return data


def first_not_rup(variables, clauses, steps):
    """The position, counting from 1, of the first lemma that is not RUP against clauses and the lemmas before it; 0
    if the proof reaches a refutation with every lemma RUP (or the clauses refute themselves by propagation)."""
    lemmas, checked, refuted = U.rup_check(variables, clauses, steps)
    return 0 if refuted else checked + 1


def critical(tools, work, edges, n, log, solve=None):
    """Rule 6: [vertices whose removal leaves the graph 4-colourable, each model checked against every clause]."""
    solve = solve or H.solve
    out = []
    for v in range(1, n + 1):
        left = [x for x in range(1, n + 1) if x != v]
        clauses = U.colouring_clauses(n, edges, 4, left)
        path = os.path.join(work, "critical.cnf")
        U.write_cnf(path, 4 * n, clauses)
        r = solve(tools, path, work, "critical", proof=False)
        if r["answer"] == "sat" and H.satisfies(H.model(r["model"]), clauses) == 0:
            out.append(v)
        if v % 100 == 0:
            log(f"trim529: vertex-critical {len(out)} of {v}")
    return out


def run(inputs="inputs", results="results", tools=None, log=print):
    started = time.monotonic()
    data = {name: load(inputs, name) for name, *_ in INPUTS}
    detail = {"inputs": [{"name": n, "sha256": h, "bytes": b, "source": s} for n, h, b, s in INPUTS]}
    v = {}

    # Rules 1 and 2: the points and the edges, exactly.
    points = U.parse_points(data["heule529.vtx"].decode("ascii"))
    if len(points) != VERTICES:
        raise Refused(f"{len(points)} points, not {VERTICES}")
    edges = U.parse_edges(data["heule529.edge"].decode("ascii"), VERTICES)
    radicands = sorted({m for p in points for coord in p for m in coord.t})
    with5 = sum(1 for x, y in points if (set(x.t) | set(y.t)) & SQRT5)
    unit = U.unit_edges(points, edges)
    unlisted = U.unlisted_unit_pairs(points, edges)
    degree = [0] * VERTICES
    for a, b in edges:
        degree[a - 1] += 1
        degree[b - 1] += 1
    v.update({"points": len(points), "points_distinct": len({(x.key(), y.key()) for x, y in points}),
              "points_with_sqrt5": with5, "radicands": ",".join(map(str, radicands)), "edges": len(edges),
              "unit_edges": unit, "unlisted_unit_pairs": len(unlisted)})
    detail["unlisted_unit_pairs"] = unlisted
    detail["degrees"] = f"{min(degree)}..{max(degree)}"
    log(f"trim529: {v['points_distinct']} distinct points over sqrt {v['radicands']} ({with5} need sqrt5); {unit} of "
        f"{len(edges)} edges unit; {len(unlisted)} unit pairs unlisted; {time.monotonic() - started:.1f} s")

    # Rule 3's formula against the released one, and the symmetry break.
    four = U.colouring_clauses(VERTICES, edges, 4)
    nv, released, _, _ = H.parse_cnf(data["heule529-4.cnf"], "heule529-4.cnf")
    v["formula_matches"] = int(nv == 4 * VERTICES and U.canonical(released) == U.canonical(four))
    v["sbp_triangle"] = int(U.triangle_units(list(SBP_UNITS), edges, 4))
    detail["text_triangle"] = int(U.triangle_units(list(TEXT_UNITS), edges, 4))

    # Rule 5: the released proof, against both triangles.
    steps = U.parse_drat(data["heule529-4-sbp.drat"], 4 * VERTICES)
    t = time.monotonic()
    lemmas, rup_ok, refuted = U.rup_check(4 * VERTICES, four + [(u,) for u in SBP_UNITS], steps)
    v.update({"released_lemmas": lemmas, "released_proof_rup": int(refuted)})
    detail["released_proof"] = {"steps": len(steps), "lemmas": lemmas, "rup": rup_ok, "refuted": refuted,
                                "seconds": round(time.monotonic() - t, 1)}
    v["text_units_fail_at"] = first_not_rup(4 * VERTICES, four + [(u,) for u in TEXT_UNITS], steps)
    log(f"trim529: released proof: {rup_ok} of {lemmas} lemmas RUP with units {SBP_UNITS}, refuted {refuted}; with "
        f"the text's units {TEXT_UNITS} the first lemma not RUP is number {v['text_units_fail_at']}; "
        f"{time.monotonic() - t:.1f} s")

    # The tools.
    os.makedirs(results, exist_ok=True)
    if tools is None:
        if platform.machine() not in ("x86_64", "AMD64"):
            raise SystemExit("udg/trim529.py: cake_lpr.S is x86-64 assembly; run this on an x86-64 machine")
        tools = H.build_tools(os.path.abspath(inputs), os.path.abspath(os.path.join(results, "build")))
        log(f"trim529: built CaDiCaL {tools['cadical_version']} and cake_lpr, gcc {tools['gcc']}, "
            f"at {time.monotonic() - started:.0f} s")
    work = tempfile.mkdtemp(prefix="trim529-")

    # Rule 3: no 4-colouring, verified.
    path4 = os.path.join(work, "four.cnf")
    U.write_cnf(path4, 4 * VERTICES, four)
    r4 = H.solve(tools, path4, work, "four")
    v["no_4_colouring"] = int(r4["answer"] == "unsat" and r4["verified"])
    detail["four"] = {k: r4[k] for k in ("answer", "verified", "conflicts", "seconds", "checker_said")}
    log(f"trim529: 4 colours: {r4['answer']}, verified {r4['verified']}, {r4['seconds']} s")

    # Rule 4: five colours.
    path5 = os.path.join(work, "five.cnf")
    U.write_cnf(path5, 5 * VERTICES, U.colouring_clauses(VERTICES, edges, 5))
    r5 = H.solve(tools, path5, work, "five", proof=False)
    colours = U.colours_from_model(H.model(r5["model"]), VERTICES, 5) if r5["answer"] == "sat" else None
    v["five_colouring"] = int(colours is not None and U.proper(colours, edges))
    if colours:
        detail["five_classes"] = [colours.count(c) for c in range(1, 6)]
    log(f"trim529: 5 colours: {r5['answer']}, proper {bool(v['five_colouring'])}")

    # Rule 6: vertex-critical.
    t = time.monotonic()
    crit = critical(tools, work, edges, VERTICES, log)
    v["vertex_critical"] = len(crit)
    detail["not_critical"] = [x for x in range(1, VERTICES + 1) if x not in set(crit)]
    log(f"trim529: vertex-critical {len(crit)} of {VERTICES}, {time.monotonic() - t:.1f} s")

    # Rule 7: controls.
    controls = []
    moved = list(points)
    moved[1] = (points[1][0] + U.Q3.rational(U.NUDGE), points[1][1])
    controls.append({"control": "vertex 2 moved by 10^-9 in x: an edge not unit",
                     "passed": U.unit_edges(moved, edges) < len(edges)})
    if colours:
        bad = list(colours)
        a, b = edges[0]
        bad[a - 1] = bad[b - 1]
        controls.append({"control": "the 5-colouring with an edge's ends given one colour: fails",
                         "passed": not U.proper(bad, edges)})
        smallest = min((c for c in range(1, 6) if c in colours), key=lambda c: (colours.count(c), c))
        left = [x for x in range(1, VERTICES + 1) if colours[x - 1] != smallest]
        weak = U.colouring_clauses(VERTICES, edges, 4, left)
        pathw = os.path.join(work, "weak.cnf")
        U.write_cnf(pathw, 4 * VERTICES, weak)
        rw = H.solve(tools, pathw, work, "weak", proof=False)
        ok = rw["answer"] == "sat" and H.satisfies(H.model(rw["model"]), weak) == 0
        controls.append({"control": f"without colour class {smallest} ({VERTICES - len(left)} vertices): "
                                    "4-colourable, the model checked", "passed": ok})
    else:
        controls += [{"control": "the 5-colouring with an edge's ends given one colour: fails", "passed": False},
                     {"control": "without the smallest colour class: 4-colourable", "passed": False}]
    rows, _ = H.proof_controls(tools, work)
    controls += [{"control": r["control"], "passed": r["passed"]} for r in rows]
    v.update({"controls_passed": sum(1 for c in controls if c["passed"]), "controls_total": len(controls)})
    detail["controls"] = controls
    for name in os.listdir(work):
        os.unlink(os.path.join(work, name))
    os.rmdir(work)

    v["solver"] = (f"CaDiCaL {tools['cadical_version']} (Debian orig tarball; g++ {' '.join(H.CADICAL_FLAGS)}); "
                   f"gcc {tools['gcc']}; {H.CHECKER}")
    v["test_passed"] = int(v["points"] == VERTICES and v["points_distinct"] == VERTICES and v["edges"] == EDGES
                           and unit == len(edges) and v["no_4_colouring"] == 1 and v["five_colouring"] == 1)
    out = {k: v[k] for k in OUTPUTS}
    for k, x in out.items():
        if isinstance(x, str) and len(x) > U.LIMIT:
            raise AssertionError(f"{k}: longer than {U.LIMIT} characters")
    detail["seconds"] = round(time.monotonic() - started, 1)
    with open(os.path.join(results, "outputs.json"), "w", encoding="ascii") as f:
        json.dump(out, f, indent=2, sort_keys=True)
        f.write("\n")
    with open(os.path.join(results, "detail.json"), "w", encoding="ascii") as f:
        json.dump(detail, f, indent=1, sort_keys=True)
        f.write("\n")
    return out, detail


def main():
    argparse.ArgumentParser(description=__doc__.split("\n")[0]).parse_args()
    seed = os.environ.get("ECDYSIS_SEED", "")
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        sys.exit("ECDYSIS_SEED must be the 64-hex seed the archive issued")
    try:
        out, _ = run(log=lambda s: print(s, file=sys.stderr, flush=True))
    except Refused as e:
        sys.exit(f"udg/trim529.py: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
