#!/usr/bin/env python3
"""Heule's 553-vertex unit-distance graph with chromatic number 5, checked exactly, for an Ecdysis receipt.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:33129411bee32407) is from Heule,
"Computing Small Unit-Distance Graphs with Chromatic Number 5" (Geombinatorics 28(1), 2018; arXiv:1805.12181): "Our
method, which is based on clausal proof minimization, allowed us to compute several 553-vertex unit-distance graphs
with chromatic number 5, while the smallest published unit-distance graph with chromatic number 5 has 1581
vertices." Its registered test: refuted if the 553-vertex graph released with the paper (vtx/553.vtx and
edge/553.edge in marijnheule/CNP-SAT at a238bb0) is not 553 distinct points in the plane, or lists an edge whose
endpoints are not at distance exactly 1 (in exact arithmetic over Q(sqrt3, sqrt5, sqrt11), where its coordinates
lie), or has a proper colouring with 4 colours, or has none with 5.

The inputs, each checked against its SHA-256 and size before anything else runs (INPUTS): the claim's five files of
record from marijnheule/CNP-SAT at a238bb0 (the vertices, the edges, the 4-colouring formula without and with
symmetry breaking, and the DRAT proof Heule released), and, as in hexagon/check.py, whose code this module imports,
CaDiCaL 2.1.3's source as Debian archived it and the two files of the CakeML-verified LRAT checker cake_lpr. No
input is executed: the solver and the checker are compiled from source into results/build by this run, in the pinned
image, with no network. Every rule below was fixed before any seed existed; the seed is not used, as nothing here is
random.

1. The points. Each line of heule553.vtx must be "{x, y}", x and y built from integers, + - * /, parentheses and
   Sqrt[r] with r a positive rational, and nothing else. Each is evaluated exactly as an element of Q(sqrt3, sqrt5,
   sqrt11): a sum of rational multiples of sqrt m for m in 1, 3, 5, 11, 15, 33, 55, 165, a quotient being formed by
   multiplying through by conjugates; a radical outside the field, or a Sqrt of anything but a positive rational, is
   refused. There must be 553 lines and 553 distinct points.
2. The edges. heule553.edge must be the header "p edge 553 E" and E lines "e u v" with 1 <= u < v <= 553, no edge
   twice. Each edge's squared length (x_u - x_v)^2 + (y_u - y_v)^2 is computed exactly; unit_edges counts those that
   are exactly 1. Beside it (reported only, as a unit-distance graph need not hold every unit pair): the pairs of
   points at distance exactly 1 that the file does not list, found by testing exactly every pair whose distance in
   floating point is within 10^-6 of 1.
3. No 4-colouring. The 4-colouring formula of the edges is written here: variable 4(v - 1) + c for vertex v and
   colour c, one clause "some colour" per vertex and one "not both c" per edge and colour. It must equal
   heule553-4.cnf clause for clause, as sets of clauses (order aside); heule553-4-sbp.cnf must be those clauses and
   three units that give three pairwise adjacent vertices three different colours (a sound symmetry break). The
   formula written here is solved by CaDiCaL with an LRAT proof streamed into cake_lpr, as hexagon/check.py does:
   no_4_colouring is 1 when CaDiCaL reports UNSATISFIABLE and cake_lpr reports "s VERIFIED UNSAT" on it.
4. Five colours. The same encoding with five colours is solved by CaDiCaL; its model gives each vertex its first true
   colour, and five_colouring is 1 if every vertex has one and every edge's ends differ.
5. The released proof (reported only). heule553-4-sbp.drat must be lines of literals ending in 0 (deletions begin
   "d"); each added lemma, in order, is checked to be RUP (reverse unit propagation) against heule553-4-sbp.cnf and
   the lemmas before it, by a forward checker of Imago's own that keeps deleted clauses (a clause kept is still
   implied, so this accepts no lemma that is not implied), until the lemmas added leave a conflict at level 0:
   released_proof_rup is 1 if that point is reached with every lemma before it RUP. Not a verified checker: rule 3's
   is the verified check of the claim.
6. Controls (controls_passed counts those that behave as stated): vertex 2 moved by 10^-9 in x must make one of its
   edges not unit; rule 4's colouring with one endpoint of the first edge given the other's colour must fail the
   colouring check; the 4-colouring formula of the graph left when rule 4's smallest colour class is removed must be
   satisfiable (rule 4's colouring restricted to it is a proper 4-colouring), with CaDiCaL's model checked against
   every clause; and hexagon/check.py's three pigeonhole proof controls (an LRAT proof accepted, and rejected without
   its last step and without a lemma its last step cites).

test_passed is 1 if there are 553 distinct points, every listed edge is exactly unit, no_4_colouring is 1 and
five_colouring is 1; else 0. Rule 3's match with the released formulas, rule 5 and rule 6 are reported beside it.

What it cannot check:
- the paper's other 553-vertex graphs (it computed several and released one) and its method of finding them;
- the tools beyond themselves: cake_lpr is verified in CakeML down to its assembly, but the C wrapper, the compiler,
  the kernel and this script (its exact arithmetic among it) are trusted;
- the released proof formally: rule 5's checker is Imago's own, and the verified proof is the one CaDiCaL writes here.

Writes results/outputs.json (the values a receipt carries) and results/detail.json. Run with: python3 udg/check.py
"""

import argparse
import hashlib
import importlib.util
import json
import math
import os
import platform
import re
import sys
import tempfile
import time
from fractions import Fraction
from math import gcd

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("udg_hexagon", os.path.join(HERE, "..", "hexagon", "check.py"))
H = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(H)
Refused = H.Refused

CNP = "marijnheule/CNP-SAT@a238bb0"
INPUTS = (
    ("heule553.vtx", "7e43a0250f4e54f362ffec98dcc0d364edd06d3d0963931b1ec7c32cc846d4fb", 28611, f"{CNP} vtx/553.vtx"),
    ("heule553.edge", "b339b6a75575152d8bf2efc9ca1a178d2df15a2f9590b752de4f8ebc4a63e466", 25710,
     f"{CNP} edge/553.edge"),
    ("heule553-4.cnf", "ca66ff9c9aa2ff32954265dd5a56b1c4255924e3655b79a3096abaa71bd5bd81", 149821,
     f"{CNP} cnf/553-4.cnf"),
    ("heule553-4-sbp.cnf", "cc5e23a4f5ce073ec3b95ba8a109cb663dcdd49a50524eb5379f2315631d9361", 149834,
     f"{CNP} cnf/553-4-sbp.cnf"),
    ("heule553-4-sbp.drat", "d71180c6d30f85ec95c91a54aee09f60b728588257198116157c92e99dd17d50", 4143373,
     f"{CNP} proof/553-4-sbp.drat"),
) + tuple(i for i in H.INPUTS if i[0] in ("cadical_2.1.3.orig.tar.gz", "cake_lpr.S", "basis_ffi.c"))

VERTICES = 553
PRIMES = (3, 5, 11)                          # the field Q(sqrt3, sqrt5, sqrt11)
BASIS = (1, 3, 5, 11, 15, 33, 55, 165)       # its squarefree radicands
NEAR = 1e-6                                  # rule 2's floating-point screen for unlisted unit pairs
NUDGE = Fraction(1, 10 ** 9)                 # rule 6's moved vertex
LIMIT = 200

OUTPUTS = (
    "points", "points_distinct", "radicands", "edges", "unit_edges", "unlisted_unit_pairs", "degrees",
    "formula_matches", "sbp_triangle", "no_4_colouring", "five_colouring",
    "released_lemmas", "released_proof_rup", "controls_passed", "controls_total",
    "solver", "checker", "test_passed",
)


# ---------------------------------------------------------------- exact arithmetic in Q(sqrt3, sqrt5, sqrt11)

class Q3:
    """An element of Q(sqrt3, sqrt5, sqrt11): {m: c} meaning the sum of c sqrt(m), m in BASIS, no zero c."""

    __slots__ = ("t",)

    def __init__(self, terms=None):
        self.t = {m: Fraction(c) for m, c in (terms or {}).items() if c != 0}
        if any(m not in BASIS for m in self.t):
            raise Refused(f"a radical outside Q(sqrt3, sqrt5, sqrt11): {sorted(self.t)}")

    @staticmethod
    def rational(q):
        return Q3({1: Fraction(q)})

    @staticmethod
    def sqrt(r):
        """sqrt of a positive rational r = p/q: sqrt(pq)/q = (f/q) sqrt(s), pq = f^2 s with s squarefree."""
        r = Fraction(r)
        if r <= 0:
            raise Refused(f"Sqrt of {r}, not a positive rational")
        n, f, s, d = r.numerator * r.denominator, 1, 1, 2
        while d * d <= n:
            while n % (d * d) == 0:
                n //= d * d
                f *= d
            if n % d == 0:
                n //= d
                s *= d
            d += 1
        s *= n
        return Q3({s: Fraction(f, r.denominator)})

    def __add__(self, o):
        out = dict(self.t)
        for m, c in o.t.items():
            out[m] = out.get(m, 0) + c
        return Q3(out)

    def __neg__(self):
        return Q3({m: -c for m, c in self.t.items()})

    def __sub__(self, o):
        return self + (-o)

    def __mul__(self, o):
        out = {}
        for m1, c1 in self.t.items():
            for m2, c2 in o.t.items():
                g = gcd(m1, m2)                   # sqrt m1 sqrt m2 = g sqrt(m1 m2 / g^2), squarefree again
                m = m1 * m2 // (g * g)
                out[m] = out.get(m, 0) + c1 * c2 * g
        return Q3(out)

    def conjugate(self, p):
        """sqrt p -> -sqrt p."""
        return Q3({m: (-c if m % p == 0 else c) for m, c in self.t.items()})

    def inverse(self):
        """1/self: multiply by the conjugates in sqrt3, sqrt5 and sqrt11 in turn until the denominator is rational."""
        if not self.t:
            raise Refused("division by zero")
        num, den = Q3.rational(1), self
        for p in PRIMES:
            c = den.conjugate(p)
            num, den = num * c, den * c
        if set(den.t) - {1}:
            raise AssertionError("the denominator did not become rational")
        return num * Q3.rational(1 / den.t[1])

    def __truediv__(self, o):
        return self * o.inverse()

    def __eq__(self, o):
        return isinstance(o, Q3) and self.t == o.t

    def __hash__(self):
        return hash(self.key())

    def key(self):
        return tuple(sorted(self.t.items()))

    def rational_value(self):
        """The rational this is, or None."""
        return self.t.get(1, Fraction(0)) if set(self.t) <= {1} else None

    def __float__(self):
        return float(sum(float(c) * math.sqrt(m) for m, c in self.t.items()))


TOKEN = re.compile(r"\s*(?:(\d+)|(Sqrt)|([-+*/()\[\],{}]))")


def tokens(s):
    out, pos = [], 0
    s = s.strip()
    while pos < len(s):
        m = TOKEN.match(s, pos)
        if not m or m.end() == pos:
            raise Refused(f"cannot read {s[pos:pos + 30]!r}")
        out.append(m.group(1) or m.group(2) or m.group(3))
        pos = m.end()
    return out


def parse_point(line):
    """(x, y) as Q3 from one line "{x, y}" of Mathematica input: integers, + - * /, parentheses and Sqrt[...]."""
    toks, i = tokens(line), 0

    def peek():
        return toks[i] if i < len(toks) else None

    def eat(t):
        nonlocal i
        if peek() != t:
            raise Refused(f"expected {t!r} in {line.strip()!r}")
        i += 1

    def expr():
        v = term()
        while peek() in ("+", "-"):
            op = peek()
            eat(op)
            w = term()
            v = v + w if op == "+" else v - w
        return v

    def term():
        v = factor()
        while peek() in ("*", "/"):
            op = peek()
            eat(op)
            w = factor()
            v = v * w if op == "*" else v / w
        return v

    def factor():
        nonlocal i
        t = peek()
        if t == "-":
            eat("-")
            return -factor()
        if t == "(":
            eat("(")
            v = expr()
            eat(")")
            return v
        if t == "Sqrt":
            eat("Sqrt")
            eat("[")
            v = expr()
            eat("]")
            r = v.rational_value()
            if r is None:
                raise Refused(f"Sqrt of an irrational in {line.strip()!r}")
            return Q3.sqrt(r)
        if t is not None and t.isdigit():
            i += 1
            return Q3.rational(int(t))
        raise Refused(f"unexpected {t!r} in {line.strip()!r}")

    eat("{")
    x = expr()
    eat(",")
    y = expr()
    eat("}")
    if i != len(toks):
        raise Refused(f"more after the point in {line.strip()!r}")
    return x, y


def parse_points(text):
    lines = [line for line in text.split("\n") if line.strip()]
    return [parse_point(line) for line in lines]


def parse_edges(text, n):
    """The edges of a DIMACS graph "p edge n E" then "e u v" lines, 1 <= u < v <= n, none twice."""
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    m = re.fullmatch(r"p edge (\d+) (\d+)", lines[0]) if lines else None
    if not m or int(m.group(1)) != n:
        raise Refused(f"the edge file's header is not \"p edge {n} E\"")
    edges = []
    for line in lines[1:]:
        e = re.fullmatch(r"e (\d+) (\d+)", line)
        if not e:
            raise Refused(f"not an edge line: {line!r}")
        u, v = int(e.group(1)), int(e.group(2))
        if not 1 <= u < v <= n:
            raise Refused(f"an edge out of order or range: {line!r}")
        edges.append((u, v))
    if len(edges) != int(m.group(2)) or len(set(edges)) != len(edges):
        raise Refused("the edge count is not the header's, or an edge is listed twice")
    return edges


def squared(p, q):
    dx, dy = p[0] - q[0], p[1] - q[1]
    return dx * dx + dy * dy


ONE = Q3.rational(1)


def unit_edges(points, edges):
    return sum(1 for u, v in edges if squared(points[u - 1], points[v - 1]) == ONE)


def unlisted_unit_pairs(points, edges):
    """Pairs at distance exactly 1 that edges does not list: every pair within NEAR of 1 in floating point, tested
    exactly."""
    fl = [(float(x), float(y)) for x, y in points]
    listed, found = set(edges), []
    for a in range(len(points)):
        for b in range(a + 1, len(points)):
            d2 = (fl[a][0] - fl[b][0]) ** 2 + (fl[a][1] - fl[b][1]) ** 2
            if abs(d2 - 1) < NEAR and (a + 1, b + 1) not in listed and squared(points[a], points[b]) == ONE:
                found.append((a + 1, b + 1))
    return found


# ---------------------------------------------------------------- colourings

def colouring_clauses(n, edges, k, vertices=None):
    """The k-colouring formula: variable k(v - 1) + c; "some colour" for each vertex (of vertices, if given) and "not
    both c" for each edge between them and each colour."""
    keep = set(range(1, n + 1)) if vertices is None else set(vertices)
    out = [tuple(k * (v - 1) + c for c in range(1, k + 1)) for v in sorted(keep)]
    out += [(-(k * (u - 1) + c), -(k * (v - 1) + c)) for u, v in edges if u in keep and v in keep
            for c in range(1, k + 1)]
    return out


def canonical(clauses):
    return sorted(tuple(sorted(c)) for c in clauses)


def triangle_units(units, edges, k):
    """Whether unit literals give pairwise adjacent vertices distinct colours (variable k(v - 1) + c)."""
    if len(units) != 3 or any(lit <= 0 for lit in units):
        return False
    vc = [divmod(lit - 1, k) for lit in units]
    vs, cs = [v + 1 for v, _ in vc], [c + 1 for _, c in vc]
    adjacent = set(edges)
    pairs = [(min(a, b), max(a, b)) for i, a in enumerate(vs) for b in vs[i + 1:]]
    return len(set(vs)) == 3 and len(set(cs)) == 3 and all(p in adjacent for p in pairs)


def colours_from_model(assignment, n, k):
    """Each vertex's first true colour, or None."""
    return [next((c for c in range(1, k + 1) if k * (v - 1) + c in assignment), None) for v in range(1, n + 1)]


def proper(colours, edges):
    return all(c is not None for c in colours) and all(colours[u - 1] != colours[v - 1] for u, v in edges)


# ---------------------------------------------------------------- rule 5: a forward RUP checker

def parse_drat(data, variables):
    """The steps of a text DRAT proof: [(deleted, literals)], every literal within 1..variables."""
    steps = []
    for line in data.split(b"\n"):
        toks = line.split()
        if not toks:
            continue
        deleted = toks[0] == b"d"
        if deleted:
            toks = toks[1:]
        if not toks or toks[-1] != b"0":
            raise Refused("proof: a line that does not end in 0")
        try:
            lits = tuple(int(t) for t in toks[:-1])
        except ValueError:
            raise Refused("proof: a literal that is not an integer") from None
        if any(lit == 0 or abs(lit) > variables for lit in lits):
            raise Refused(f"proof: a literal outside 1..{variables}")
        steps.append((deleted, lits))
    return steps


class RUP:
    """Unit propagation over binary implications and watched longer clauses, at level 0 with a trail that each check
    extends and then undoes. Clauses are never deleted."""

    def __init__(self, variables):
        self.n = variables
        size = 2 * variables + 2
        self.val = [0] * size            # by literal index: 1 true, -1 false, 0 unassigned
        self.binary = [[] for _ in range(size)]    # the literals implied when the indexed literal becomes false
        self.watches = [[] for _ in range(size)]   # clauses watching the indexed literal
        self.clauses = []
        self.trail = []

    def i(self, lit):
        return lit if lit > 0 else self.n - lit

    def assign(self, lit):
        self.val[self.i(lit)], self.val[self.i(-lit)] = 1, -1
        self.trail.append(lit)

    def propagate(self, start):
        """False on a conflict."""
        val, i, k = self.val, self.i, start
        while k < len(self.trail):
            false = -self.trail[k]
            k += 1
            for m in self.binary[i(false)]:
                if val[i(m)] == -1:
                    return False
                if val[i(m)] == 0:
                    self.assign(m)
            ws, keep, j = self.watches[i(false)], [], 0
            while j < len(ws):
                cid = ws[j]
                j += 1
                c = self.clauses[cid]
                if c[0] == false:
                    c[0], c[1] = c[1], c[0]
                if val[i(c[0])] == 1:
                    keep.append(cid)
                    continue
                for q in range(2, len(c)):
                    if val[i(c[q])] != -1:
                        c[1], c[q] = c[q], c[1]
                        self.watches[i(c[1])].append(cid)
                        break
                else:
                    keep.append(cid)
                    if val[i(c[0])] == -1:
                        keep.extend(ws[j:])
                        self.watches[i(false)] = keep
                        return False
                    if val[i(c[0])] == 0:
                        self.assign(c[0])
            self.watches[i(false)] = keep
        return True

    def add(self, clause):
        """Add a clause at level 0; False if that gives a conflict."""
        c = list(dict.fromkeys(clause))
        if any(-lit in c for lit in c):
            return True
        val, i = self.val, self.i
        free = [lit for lit in c if val[i(lit)] != -1]
        if any(val[i(lit)] == 1 for lit in c):
            pass                                   # satisfied at level 0: stored, it can never propagate
        elif not free:
            return False
        if len(c) == 1:
            if val[i(c[0])] == 0:
                start = len(self.trail)
                self.assign(c[0])
                return self.propagate(start)
            return val[i(c[0])] == 1
        if len(c) == 2:
            a, b = c
            self.binary[i(a)].append(b)
            self.binary[i(b)].append(a)
        else:
            c.sort(key=lambda lit: 0 if val[i(lit)] != -1 else 1)
            self.clauses.append(c)
            self.watches[i(c[0])].append(len(self.clauses) - 1)
            self.watches[i(c[1])].append(len(self.clauses) - 1)
        if len(free) == 1 and val[i(free[0])] == 0:
            start = len(self.trail)
            self.assign(free[0])
            return self.propagate(start)
        return True

    def implied(self, lemma):
        """Whether the lemma is RUP: its negation, propagated, gives a conflict. The trail is restored."""
        base, conflict = len(self.trail), False
        for lit in lemma:
            v = self.val[self.i(lit)]
            if v == 1:
                conflict = True
                break
            if v == 0:
                self.assign(-lit)
        if not conflict:
            conflict = not self.propagate(base)
        for lit in self.trail[base:]:
            self.val[self.i(lit)] = self.val[self.i(-lit)] = 0
        del self.trail[base:]
        return conflict


def rup_check(variables, clauses, steps):
    """(lemmas, checked, refuted): the proof's added lemmas (the empty clause among them); how many were checked RUP,
    in order, before the formula was refuted or the first that is not RUP; and whether it was refuted, that is,
    whether adding the lemmas checked left a conflict at level 0. The lemmas after that point are not needed."""
    lemmas = [lits for deleted, lits in steps if not deleted]
    db = RUP(variables)
    for c in clauses:
        if not db.add(c):
            return len(lemmas), 0, True           # refuted by unit propagation alone
    for k, lemma in enumerate(lemmas):
        if not db.implied(lemma):
            return len(lemmas), k, False
        if not db.add(lemma):
            return len(lemmas), k + 1, True
    return len(lemmas), len(lemmas), False


# ---------------------------------------------------------------- the run

def load(directory, name):
    spec = next(i for i in INPUTS if i[0] == name)
    with open(os.path.join(directory, name), "rb") as f:
        data = f.read()
    got = hashlib.sha256(data).hexdigest()
    if got != spec[1] or len(data) != spec[2]:
        raise Refused(f"{name}: sha256 {got} and {len(data)} bytes, not the committed {spec[1]} and {spec[2]}")
    return data


def write_cnf(path, variables, clauses):
    with open(path, "wb") as f:
        f.write(b"p cnf %d %d\n" % (variables, len(clauses)) + H.clause_lines(clauses))


def summarise(values):
    out = {k: values[k] for k in OUTPUTS}
    for k, v in out.items():
        if isinstance(v, str) and len(v) > LIMIT:
            raise AssertionError(f"{k}: longer than {LIMIT} characters")
    return out


def run(inputs="inputs", results="results", tools=None, log=print):
    started = time.monotonic()
    data = {name: load(inputs, name) for name, *_ in INPUTS}
    detail = {"inputs": [{"name": n, "sha256": h, "bytes": b, "source": s} for n, h, b, s in INPUTS]}
    v = {}

    # Rules 1 and 2: the points and the edges, exactly.
    points = parse_points(data["heule553.vtx"].decode("ascii"))
    if len(points) != VERTICES:
        raise Refused(f"{len(points)} points, not {VERTICES}")
    edges = parse_edges(data["heule553.edge"].decode("ascii"), VERTICES)
    radicands = sorted({m for p in points for coord in p for m in coord.t})
    unit = unit_edges(points, edges)
    unlisted = unlisted_unit_pairs(points, edges)
    degree = [0] * VERTICES
    for a, b in edges:
        degree[a - 1] += 1
        degree[b - 1] += 1
    v.update({"points": len(points), "points_distinct": len({(x.key(), y.key()) for x, y in points}),
              "radicands": ",".join(map(str, radicands)), "edges": len(edges), "unit_edges": unit,
              "unlisted_unit_pairs": len(unlisted), "degrees": f"{min(degree)}..{max(degree)}"})
    detail["unlisted_unit_pairs"] = unlisted
    log(f"udg: {v['points_distinct']} distinct points over sqrt {v['radicands']}; {unit} of {len(edges)} edges unit; "
        f"{len(unlisted)} unit pairs unlisted; degrees {v['degrees']}; {time.monotonic() - started:.1f} s")

    # Rule 3's formulas, against the released ones.
    four = colouring_clauses(VERTICES, edges, 4)
    nv, released, _, _ = H.parse_cnf(data["heule553-4.cnf"], "heule553-4.cnf")
    nv_s, released_sbp, _, _ = H.parse_cnf(data["heule553-4-sbp.cnf"], "heule553-4-sbp.cnf")
    matches = nv == 4 * VERTICES and canonical(released) == canonical(four)
    units = [c[0] for c in released_sbp if len(c) == 1]
    rest = [c for c in released_sbp if len(c) != 1]
    sbp = nv_s == nv and canonical(rest) == canonical(four) and triangle_units(units, edges, 4)
    v.update({"formula_matches": int(matches), "sbp_triangle": int(sbp)})
    detail["sbp_units"] = units

    # Rule 5: the released proof, by Imago's RUP checker.
    steps = parse_drat(data["heule553-4-sbp.drat"], nv_s)
    t = time.monotonic()
    lemmas, rup_ok, refuted = rup_check(nv_s, released_sbp, steps)
    v.update({"released_lemmas": lemmas, "released_proof_rup": int(refuted)})
    detail["released_proof"] = {"steps": len(steps), "lemmas": lemmas, "rup": rup_ok, "refuted": refuted,
                                "seconds": round(time.monotonic() - t, 1)}
    log(f"udg: released proof: {rup_ok} of {lemmas} lemmas RUP, refuted {refuted}, "
        f"{detail['released_proof']['seconds']} s")

    # The tools.
    os.makedirs(results, exist_ok=True)
    if tools is None:
        if platform.machine() not in ("x86_64", "AMD64"):
            raise SystemExit("udg/check.py: cake_lpr.S is x86-64 assembly; run this on an x86-64 machine")
        tools = H.build_tools(os.path.abspath(inputs), os.path.abspath(os.path.join(results, "build")))
        log(f"udg: built CaDiCaL {tools['cadical_version']} and cake_lpr, gcc {tools['gcc']}, "
            f"at {time.monotonic() - started:.0f} s")
    work = tempfile.mkdtemp(prefix="udg-")

    # Rule 3: no 4-colouring, verified.
    path4 = os.path.join(work, "four.cnf")
    write_cnf(path4, 4 * VERTICES, four)
    r4 = H.solve(tools, path4, work, "four")
    v["no_4_colouring"] = int(r4["answer"] == "unsat" and r4["verified"])
    detail["four"] = {k: r4[k] for k in ("answer", "verified", "conflicts", "seconds", "checker_said")}
    log(f"udg: 4 colours: {r4['answer']}, verified {r4['verified']}, {r4['seconds']} s")

    # Rule 4: five colours.
    path5 = os.path.join(work, "five.cnf")
    write_cnf(path5, 5 * VERTICES, colouring_clauses(VERTICES, edges, 5))
    r5 = H.solve(tools, path5, work, "five", proof=False)
    colours = colours_from_model(H.model(r5["model"]), VERTICES, 5) if r5["answer"] == "sat" else None
    v["five_colouring"] = int(colours is not None and proper(colours, edges))
    if colours:
        detail["five_classes"] = [colours.count(c) for c in range(1, 6)]
    log(f"udg: 5 colours: {r5['answer']}, proper {bool(v['five_colouring'])}")

    # Rule 6: controls.
    controls = []
    moved = list(points)
    moved[1] = (points[1][0] + Q3.rational(NUDGE), points[1][1])
    controls.append({"control": "vertex 2 moved by 10^-9 in x: an edge not unit",
                     "passed": unit_edges(moved, edges) < len(edges)})
    if colours:
        bad = list(colours)
        u, w = edges[0]
        bad[u - 1] = bad[w - 1]
        controls.append({"control": "the 5-colouring with an edge's ends given one colour: fails",
                         "passed": not proper(bad, edges)})
        smallest = min((c for c in range(1, 6) if c in colours), key=lambda c: (colours.count(c), c))
        left = [x for x in range(1, VERTICES + 1) if colours[x - 1] != smallest]
        weak = colouring_clauses(VERTICES, edges, 4, left)
        pathw = os.path.join(work, "weak.cnf")
        write_cnf(pathw, 4 * VERTICES, weak)
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
                   f"gcc {tools['gcc']}")
    v["checker"] = H.CHECKER
    v["test_passed"] = int(v["points"] == VERTICES and v["points_distinct"] == VERTICES and unit == len(edges)
                           and v["no_4_colouring"] == 1 and v["five_colouring"] == 1)
    out = summarise(v)
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
        sys.exit(f"udg/check.py: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
