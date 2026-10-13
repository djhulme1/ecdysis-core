#!/usr/bin/env python3
"""Exoo and Ismailescu's 6-chromatic {1,2}-graph, rebuilt exactly from their paper and refuted by a verified proof.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:c3433d7a12cf0983) is from Exoo and
Ismailescu, "A 6-chromatic two-distance graph in the plane" (Geombinatorics 29(3), 97-103, 2020; arXiv:1909.13177):
"We prove that if one colors each point of the Euclidean plane with one of five colors, then there exist two points of
the same color that are either distance 1 or distance 2 apart." Its registered test: refuted if K, the {1,2}-graph
the paper builds (the 23 points S it prints in its [a,b,c,d] coordinates, their reflections in the axes and rotations
by multiples of pi/3, nine further points including A and B, and a copy of the whole rotated about A by
arccos(49/50)), with an edge wherever two of its points are exactly 1 or 2 apart, has a proper 5-colouring.

The input is the claim's data of record, the paper's e-print (arXiv-1909.13177v1.tar.gz), checked against its SHA-256
and size; its TeX is read as text (nothing in it is run). As in udg/check.py, CaDiCaL 2.1.3 and the CakeML-verified
LRAT checker cake_lpr are compiled from their pinned sources by this run (hexagon/check.py's build_tools), in the
pinned image, with no network. Every rule below was fixed before any seed existed; nothing is random, so the seed is
not used.

1. The paper's data. g2_version_2.tex must print the notation [a,b,c,d] = (a sqrt3/12 + b sqrt11/12,
   c/12 + d sqrt33/12), the rotation by pi/3 as [(a-c)/2, (b-3d)/2, (3a+c)/2, (b+d)/2], the angle arccos(49/50) and the
   counts it claims
   (205, 966, 423; 214, 1004, 446; 426, 2009, 892); S is the 23 bracketed points after "S:=\\{" and the further points
   the 9 after "A:=&", the first two being A and B. A point is held as its four rationals (a, b, c, d); since 1, sqrt3,
   sqrt11 and sqrt33 are linearly independent over Q, two points are equal exactly when their four rationals are.
2. The construction, as Section 2 states it. T is S with its reflections in the x-axis ([a,b,-c,-d]) and in the y-axis
   ([-a,-b,c,d]); V is the union of T's images under the printed rotation applied 0 to 5 times (every coordinate must
   stay an integer); G has the points of V, H those of V and the nine. The rotation about A by theta, cos theta = 49/50
   and sin theta = 3 sqrt11/50, sends A + (a, b, c, d) to A + ((49a - 33d)/50, (49b - 3c)/50, (33b + 49c)/50,
   (3a + 49d)/50): with x = (a sqrt3 + b sqrt11)/12 and y = (c + d sqrt33)/12, x cos - y sin and x sin + y cos written
   out, sqrt363 being 11 sqrt3. H' is H's image and K has the points of H and H'. Beside it, the same with -theta.
3. The edges, exactly. For points p and q with difference (a, b, c, d), 144 |p - q|^2 = (3a^2 + 11b^2 + c^2 + 33d^2)
   + 2(ab + cd) sqrt33, so p and q are 1 apart when ab + cd = 0 and the rational part is 144, and 2 apart when it is
   576. Every pair of points is tested. The counts must be the paper's, |AB| = 5, and B' (B's image) must be 1 from B.
4. The colouring argument. The 5-colouring formula of H (variable 5v + c + 1 for vertex v, colour c: one clause "some
   colour" per vertex, one "not both c" per edge and colour), with A and B made to differ (one clause "not both c" per
   colour) and the colours of a triangle of H fixed (its three vertices given colours 1, 2 and 3, a sound break of the
   colours' symmetry, as any proper colouring has three colours on a triangle and can be renamed), is solved by CaDiCaL
   with its LRAT proof streamed into cake_lpr. If cake_lpr reports "s VERIFIED UNSAT", every proper 5-colouring of H
   gives A and B one colour. The rotation of rule 2 is an isometry (checked: it sends every edge of H to a pair of
   K's points the same distance apart) fixing A and sending B to B', so every proper 5-colouring of K, restricted to
   H', gives A and B' one colour too; then B and B' would share a colour, though rule 3 finds them adjacent. So K has
   no proper 5-colouring. The triangle is the first in vertex order (points sorted by their four rationals).
5. Controls (controls_passed counts those that behave as stated): the formula of rule 4 without the clauses that make
   A and B differ must be satisfiable, and CaDiCaL's model must be a proper colouring of H that gives A and B one
   colour, checked here edge by edge; rotated about A by twice the paper's angle (cos 1151/1250, sin 147 sqrt11/1250),
   B's image must not be 1 from B; and hexagon/check.py's three pigeonhole proof controls (an LRAT proof accepted,
   and rejected without its last step and without a lemma its last step cites).

test_passed is 1 if the counts of rule 3 are the paper's, B and B' are adjacent, the rotation is an isometry on H, and
cake_lpr verifies rule 4's refutation; else 0.

What it cannot check:
- the paper's counts of colourings (exactly 18 for G and 35 for H), which need an enumeration the receipt does not run;
- the tools beyond themselves: cake_lpr is verified in CakeML down to its assembly, but the C wrapper, the compiler,
  the kernel and this script (its exact arithmetic and rule 4's argument from H to K among it) are trusted.

Writes results/outputs.json (the values a receipt carries) and results/detail.json. Run with:
python3 udg/two_distance.py
"""

import argparse
import hashlib
import importlib.util
import io
import json
import os
import platform
import re
import sys
import tarfile
import tempfile
import time
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("udg_hexagon", os.path.join(HERE, "..", "hexagon", "check.py"))
H = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(H)
Refused = H.Refused

EPRINT = ("arXiv-1909.13177v1.tar.gz", "ec93ab51a21cbe1ff047968b7720029fa69e5955a39330145097339f7ac6bec8", 43112,
          "https://arxiv.org/src/1909.13177v1")
TEX = "g2_version_2.tex"
INPUTS = (EPRINT,) + tuple(i for i in H.INPUTS if i[0] in ("cadical_2.1.3.orig.tar.gz", "cake_lpr.S", "basis_ffi.c"))
PRINTED = (  # each must appear in the TeX, runs of whitespace read as one space
    r"[a,b,c,d]:=\left(\frac{a\sqrt{3}}{12}+\frac{b\sqrt{11}}{12}, \frac{c}{12}+\frac{d\sqrt{33}}{12}\right).",
    r"is $[(a-c)/2, (b-3d)/2,(3a+c)/2,(b+d)/2]$.",
    r"The graph $G$ has $205$ vertices, $966$ edges of length $1$, $423$ edges of length $2$",
    r"The graph $H$ defined above has $214$ vertices, $1004$ edges of length $1$, $446$ edges of length $2$",
    r"Rotating the vertices of $H$ about vertex $A$ by an angle $\arccos(49/50)=\arcsin(3\sqrt{11}/50)$",
    r"It can be checked that $K$ has $426$ vertices, $2009$ edges of length $1$, and $892$ edges of length $2$.",
)
COUNTS = {"T": 57, "G": (205, 966, 423), "H": (214, 1004, 446), "K": (426, 2009, 892)}
COLOURS = 5
LIMIT = 200

OUTPUTS = (
    "printed", "S_points", "extra_points", "T_points", "G", "H", "K", "K_other_turn", "AB_squared", "BBprime_squared",
    "isometry_on_H", "triangle", "refutation", "proof_verified", "solver_seconds", "controls_passed", "controls_total",
    "solver", "checker", "test_passed",
)


def load(directory, name):
    spec = next(i for i in INPUTS if i[0] == name)
    with open(os.path.join(directory, name), "rb") as f:
        data = f.read()
    got = hashlib.sha256(data).hexdigest()
    if got != spec[1] or len(data) != spec[2]:
        raise Refused(f"{name}: sha256 {got} and {len(data)} bytes, not the committed {spec[1]} and {spec[2]}")
    return data


def tex_of(eprint):
    """The paper's TeX from the e-print, as text (a regular file of that name, read and never run)."""
    with tarfile.open(fileobj=io.BytesIO(eprint), mode="r:gz") as tar:
        member = tar.getmember(TEX)
        if not member.isfile():
            raise Refused(f"{TEX} is not a regular file in the e-print")
        return tar.extractfile(member).read().decode("utf-8")


def squash(s):
    return " ".join(s.split())


POINT = re.compile(r"\[\s*(-?\d+)\s*,\s*(-?\d+)\s*,\s*(-?\d+)\s*,\s*(-?\d+)\s*\]")


def points_after(tex, marker):
    """The bracketed points [a,b,c,d] from marker to the end of its align* block."""
    i = tex.find(marker)
    if i < 0:
        raise Refused(f"the TeX has no {marker!r}")
    j = tex.find("\\end{align*}", i)
    if j < 0:
        raise Refused(f"no end of the block after {marker!r}")
    return [tuple(Fraction(int(x)) for x in m) for m in POINT.findall(tex[i:j])]


def read_paper(tex):
    """Rule 1: the printed statements must be there; S (23 points) and the nine further points, A and B first."""
    flat = squash(tex)
    missing = [i for i, s in enumerate(PRINTED) if squash(s) not in flat]
    S = points_after(tex, "S:=\\{")
    extra = points_after(tex, "A:=&")
    if len(S) != 23 or len(extra) != 9 or len(set(S)) != 23 or len(set(extra)) != 9:
        raise Refused(f"{len(S)} points in S and {len(extra)} further points, not 23 and 9 distinct")
    return S, extra, missing


def reflect_x(p):
    return (p[0], p[1], -p[2], -p[3])


def reflect_y(p):
    return (-p[0], -p[1], p[2], p[3])


def rotate60(p):
    """The paper's rotation by pi/3 about the origin."""
    a, b, c, d = p
    return ((a - c) / 2, (b - 3 * d) / 2, (3 * a + c) / 2, (b + d) / 2)


def rotation_about(centre, cos, sin11):
    """The rotation about centre by the angle with cosine cos and sine sin11 * sqrt11 (rule 2's formula)."""
    def f(p):
        a, b, c, d = (p[k] - centre[k] for k in range(4))
        r = (cos * a - 11 * sin11 * d, cos * b - sin11 * c, 11 * sin11 * b + cos * c, sin11 * a + cos * d)
        return tuple(centre[k] + r[k] for k in range(4))
    return f


THETA = (Fraction(49, 50), Fraction(3, 50))         # cos theta, and sin theta over sqrt11
MINUS_THETA = (Fraction(49, 50), Fraction(-3, 50))
CONTROL_ANGLE = (Fraction(1151, 1250), Fraction(147, 1250))   # rule 5: twice theta, a rotation the paper does not use


def construct(S, extra, turn=THETA):
    """Rule 2: T, V (= G's points), H's points, the rotation, H' and K's points."""
    T = set(S) | {reflect_x(p) for p in S} | {reflect_y(p) for p in S}
    V = set()
    for p in T:
        q = p
        for _ in range(6):
            V.add(q)
            q = rotate60(q)
    if any(x.denominator != 1 for p in V for x in p):
        raise Refused("a rotated point left the integers")
    Hs = V | set(extra)
    A = extra[0]
    R = rotation_about(A, *turn)
    Hp = {R(p) for p in Hs}
    return T, V, Hs, R, Hp, Hs | Hp


def sq144(p, q):
    """144 |p - q|^2 as (rational part, the coefficient of 2 sqrt33)."""
    a, b, c, d = (p[k] - q[k] for k in range(4))
    return 3 * a * a + 11 * b * b + c * c + 33 * d * d, a * b + c * d


def edges(points):
    """Rule 3: the sorted points, and the pairs (i, j), i < j, exactly 1 apart and exactly 2 apart."""
    P = sorted(points)
    one, two = [], []
    for i in range(len(P)):
        for j in range(i + 1, len(P)):
            r, s = sq144(P[i], P[j])
            if s == 0 and r == 144:
                one.append((i, j))
            elif s == 0 and r == 576:
                two.append((i, j))
    return P, one, two


def colouring_clauses(n, es, k=COLOURS):
    var = lambda v, c: k * v + c + 1  # noqa: E731
    clauses = [tuple(var(v, c) for c in range(k)) for v in range(n)]
    clauses += [(-var(i, c), -var(j, c)) for i, j in es for c in range(k)]
    return clauses


def first_triangle(n, es):
    adj = [set() for _ in range(n)]
    for i, j in es:
        adj[i].add(j)
        adj[j].add(i)
    for i, j in sorted(es):
        common = sorted(adj[i] & adj[j])
        if common:
            return (i, j, common[0])
    raise Refused("H has no triangle")


def colours_from_model(assignment, n, k=COLOURS):
    out = []
    for v in range(n):
        cs = [c for c in range(k) if k * v + c + 1 in assignment]
        out.append(cs[0] if cs else None)
    return out


def write_cnf(path, variables, clauses):
    with open(path, "wb") as f:
        f.write(b"p cnf %d %d\n" % (variables, len(clauses)) + H.clause_lines(clauses))


def run(inputs="inputs", results="results", tools=None, log=print):
    started = time.monotonic()
    data = {name: load(inputs, name) for name, *_ in INPUTS}
    detail = {"inputs": [{"name": n, "sha256": h, "bytes": b, "source": s} for n, h, b, s in INPUTS]}
    v = {}

    # Rules 1 to 3: the paper's points, the construction and the edges, exactly.
    S, extra, missing = read_paper(tex_of(data[EPRINT[0]]))
    A, B = extra[0], extra[1]
    T, V, Hs, R, Hp, K = construct(S, extra)
    G_pts, G1, G2 = edges(V)
    H_pts, H1, H2 = edges(Hs)
    K_pts, K1, K2 = edges(K)
    Bp = R(B)
    *_, K_other = construct(S, extra, MINUS_THETA)
    _, Ko1, Ko2 = edges(K_other)
    index = {p: i for i, p in enumerate(K_pts)}
    unit_K = set(K1)
    BBp = tuple(sorted((index[B], index[Bp])))
    pairs = {(i, j) for i, j in H1 + H2}
    images_ok = all(sq144(R(H_pts[i]), R(H_pts[j])) == sq144(H_pts[i], H_pts[j]) for i, j in pairs)
    images_ok = images_ok and R(A) == A and len(Hp) == len(Hs) and Hp <= K
    v.update({
        "printed": f"{len(PRINTED) - len(missing)} of {len(PRINTED)}",
        "S_points": len(S), "extra_points": len(extra), "T_points": len(T),
        "G": f"{len(G_pts)} vertices, {len(G1)} unit, {len(G2)} length-2 edges",
        "H": f"{len(H_pts)} vertices, {len(H1)} unit, {len(H2)} length-2 edges",
        "K": f"{len(K_pts)} vertices, {len(K1)} unit, {len(K2)} length-2 edges",
        "K_other_turn": f"{len(K_other)} vertices, {len(Ko1)} unit, {len(Ko2)} length-2 edges",
        "AB_squared": str(Fraction(sq144(A, B)[0], 144)) + ("" if sq144(A, B)[1] == 0 else " + sqrt33 part"),
        "BBprime_squared": str(Fraction(sq144(B, Bp)[0], 144)) + ("" if sq144(B, Bp)[1] == 0 else " + sqrt33 part"),
        "isometry_on_H": int(images_ok),
    })
    counts_ok = (len(T) == COUNTS["T"] and (len(G_pts), len(G1), len(G2)) == COUNTS["G"]
                 and (len(H_pts), len(H1), len(H2)) == COUNTS["H"] and (len(K_pts), len(K1), len(K2)) == COUNTS["K"])
    adjacent = BBp in unit_K and sq144(A, B) == (3600, 0)
    log(f"two_distance: printed {v['printed']}; T {len(T)}; G {v['G']}; H {v['H']}; K {v['K']}; "
        f"|AB|^2 {v['AB_squared']}, |BB'|^2 {v['BBprime_squared']}; {time.monotonic() - started:.1f} s")

    # Rule 4: in every proper 5-colouring of H, A and B share a colour; verified.
    os.makedirs(results, exist_ok=True)
    if tools is None:
        if platform.machine() not in ("x86_64", "AMD64"):
            raise SystemExit("udg/two_distance.py: cake_lpr.S is x86-64 assembly; run this on an x86-64 machine")
        tools = H.build_tools(os.path.abspath(inputs), os.path.abspath(os.path.join(results, "build")))
        log(f"two_distance: built CaDiCaL {tools['cadical_version']} and cake_lpr, gcc {tools['gcc']}, "
            f"at {time.monotonic() - started:.0f} s")
    work = tempfile.mkdtemp(prefix="two-distance-")
    n = len(H_pts)
    es = H1 + H2
    iA, iB = H_pts.index(A), H_pts.index(B)
    tri = first_triangle(n, es)
    base = colouring_clauses(n, es)
    differ = [(-(COLOURS * iA + c + 1), -(COLOURS * iB + c + 1)) for c in range(COLOURS)]
    units = [(COLOURS * tri[c] + c + 1,) for c in range(3)]
    path = os.path.join(work, "h-a-b-differ.cnf")
    write_cnf(path, COLOURS * n, base + differ + units)
    r = H.solve(tools, path, work, "differ")
    v.update({"triangle": f"vertices {tri[0]}, {tri[1]}, {tri[2]} of H, colours 1, 2, 3",
              "refutation": r["answer"], "proof_verified": int(r["verified"]), "solver_seconds": r["seconds"]})
    detail["refutation"] = {k: r[k] for k in ("answer", "verified", "conflicts", "seconds", "checker_said",
                                              "solver_said", "solver_rc", "checker_rc", "resources")}
    log(f"two_distance: H with A and B differing: {r['answer']}, verified {r['verified']}, {r['seconds']} s, "
        f"{r['conflicts']} conflicts")

    # Rule 5: controls.
    controls = []
    path_same = os.path.join(work, "h.cnf")
    write_cnf(path_same, COLOURS * n, base + units)
    rs = H.solve(tools, path_same, work, "h", proof=False)
    ok = False
    if rs["answer"] == "sat":
        cols = colours_from_model(H.model(rs["model"]), n)
        ok = (None not in cols and all(cols[i] != cols[j] for i, j in es) and cols[iA] == cols[iB])
    controls.append({"control": "H 5-colourable without the clauses making A and B differ, the model proper and "
                                "giving A and B one colour", "passed": ok})
    Rc = rotation_about(A, *CONTROL_ANGLE)
    controls.append({"control": "rotated about A by twice the paper's angle, B's image is not 1 from B",
                     "passed": sq144(B, Rc(B)) != (144, 0)})
    rows, _ = H.proof_controls(tools, work)
    controls += [{"control": row["control"], "passed": row["passed"]} for row in rows]
    v.update({"controls_passed": sum(1 for c in controls if c["passed"]), "controls_total": len(controls)})
    detail["controls"] = controls
    for name in os.listdir(work):
        os.unlink(os.path.join(work, name))
    os.rmdir(work)

    v["solver"] = (f"CaDiCaL {tools['cadical_version']} (Debian orig tarball; g++ {' '.join(H.CADICAL_FLAGS)}); "
                   f"gcc {tools['gcc']}")
    v["checker"] = H.CHECKER
    v["test_passed"] = int(not missing and counts_ok and adjacent and images_ok and r["answer"] == "unsat"
                           and r["verified"])
    out = {k: v[k] for k in OUTPUTS}
    for k, x in out.items():
        if isinstance(x, str) and len(x) > LIMIT:
            raise AssertionError(f"{k}: longer than {LIMIT} characters")
    detail.update({"missing_printed": missing, "A": [str(x) for x in A], "B": [str(x) for x in B],
                   "B_prime": [str(x) for x in Bp], "seconds": round(time.monotonic() - started, 1)})
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
        sys.exit(f"udg/two_distance.py: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
