"""Heule's 529-vertex graph check: its inputs refused unless they are the committed bytes, the position of the first
lemma a proof fails, vertex-criticality on small graphs with a small solver of the test's own (K5 is critical, a pendant
vertex is not), and the symmetry-breaking triangles; with the released files (at inputs/ or in TRIM_INPUTS), also the
points, the edges, the formula, both triangles and the released proof as found before registering.

udg/check.py's own parts (the field, the parsers, the colouring formulas, the RUP checker) are tested in test_udg.py.

Run with: python3 -m unittest discover -s tests
"""

import importlib.util
import os
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("udg_trim529", os.path.join(HERE, "..", "udg", "trim529.py"))
T = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(T)
U, H = T.U, T.H

INPUTS = os.environ.get("TRIM_INPUTS", os.path.join(HERE, "..", "inputs"))
HAVE = all(os.path.exists(os.path.join(INPUTS, name)) for name, *_ in T.INPUTS[:4])


def dpll(clauses, true=frozenset()):
    """A satisfying set of literals for small formulas, by unit propagation and splitting, or None."""
    true = set(true)
    while True:
        unit = None
        for c in clauses:
            if any(lit in true for lit in c):
                continue
            free = [lit for lit in c if -lit not in true]
            if not free:
                return None
            if len(free) == 1:
                unit = free[0]
                break
        if unit is None:
            break
        true.add(unit)
    for c in clauses:
        if not any(lit in true for lit in c):
            lit = next(x for x in c if -x not in true)
            return dpll(clauses, true | {lit}) or dpll(clauses, true | {-lit})
    return true


def small_solve(tools, cnf, work, tag, proof=False):
    """A stand-in for CaDiCaL on small formulas."""
    with open(cnf, "rb") as f:
        nv, clauses, _, _ = H.parse_cnf(f.read(), tag)
    found = dpll(clauses)
    if found is None:
        return {"answer": "unsat", "model": None}
    lits = [v if v in found else -v for v in range(1, nv + 1)]
    return {"answer": "sat", "model": "v " + " ".join(map(str, lits)) + " 0\n"}


def complete(n):
    return [(a, b) for a in range(1, n + 1) for b in range(a + 1, n + 1)]


class Proofs(unittest.TestCase):
    # x1 or x2, x1 or -x2, -x1 or x2, -x1 or -x2: refuted by the lemmas x1, then the empty clause.
    CLAUSES = [(1, 2), (1, -2), (-1, 2), (-1, -2)]

    def test_a_proof_that_goes_through_reports_0(self):
        self.assertEqual(T.first_not_rup(2, self.CLAUSES, [(False, (1,)), (False, ())]), 0)

    def test_the_first_lemma_not_rup_is_reported_by_position(self):
        self.assertEqual(T.first_not_rup(2, self.CLAUSES[:3], [(False, (1,)), (False, (-2,)), (False, ())]), 2)
        self.assertEqual(T.first_not_rup(2, self.CLAUSES[:2], [(False, (-1,))]), 1)


class Critical(unittest.TestCase):
    def test_k5_is_vertex_critical(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(T.critical(None, d, complete(5), 5, lambda *_: None, solve=small_solve), [1, 2, 3, 4, 5])

    def test_a_pendant_vertex_is_not(self):
        edges = complete(5) + [(5, 6)]
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(T.critical(None, d, edges, 6, lambda *_: None, solve=small_solve), [1, 2, 3, 4, 5])

    def test_a_model_that_breaks_a_clause_is_not_counted(self):
        def lying(tools, cnf, work, tag, proof=False):
            return {"answer": "sat", "model": "v -1 -2 -3 -4 -5 -6 -7 -8 0\n"}
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(T.critical(None, d, complete(3), 3, lambda *_: None, solve=lying), [])


class Inputs(unittest.TestCase):
    def test_an_input_that_is_not_the_committed_bytes_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "heule529.vtx"), "wb") as f:
                f.write(b"{0, 0}\n")
            with self.assertRaises(T.Refused):
                T.load(d, "heule529.vtx")

    def test_the_units_name_the_vertices_they_mean(self):
        self.assertEqual([divmod(u - 1, 4) for u in T.SBP_UNITS], [(0, 0), (1, 1), (5, 2)])
        self.assertEqual([divmod(u - 1, 4) for u in T.TEXT_UNITS], [(0, 0), (1, 1), (6, 2)])

    def test_a_triangle_is_needed(self):
        self.assertTrue(U.triangle_units(list(T.SBP_UNITS), [(1, 2), (1, 6), (2, 6)], 4))
        self.assertFalse(U.triangle_units(list(T.SBP_UNITS), [(1, 2), (1, 6)], 4))


@unittest.skipUnless(HAVE, "the 529 release is not at inputs/ or TRIM_INPUTS")
class Released(unittest.TestCase):
    """What was read before registering, on the files of record."""

    @classmethod
    def setUpClass(cls):
        cls.data = {name: T.load(INPUTS, name) for name, *_ in T.INPUTS[:4]}
        cls.points = U.parse_points(cls.data["heule529.vtx"].decode("ascii"))
        cls.edges = U.parse_edges(cls.data["heule529.edge"].decode("ascii"), T.VERTICES)

    def test_points_and_edges(self):
        self.assertEqual((len(self.points), len({(x.key(), y.key()) for x, y in self.points})), (529, 529))
        self.assertEqual(sum(1 for x, y in self.points if (set(x.t) | set(y.t)) & T.SQRT5), 136)
        self.assertEqual((len(self.edges), U.unit_edges(self.points, self.edges)), (2670, 2670))
        self.assertEqual(U.unlisted_unit_pairs(self.points, self.edges), [])

    def test_the_formula_and_both_triangles(self):
        nv, released, _, _ = H.parse_cnf(self.data["heule529-4.cnf"], "heule529-4.cnf")
        self.assertEqual(nv, 2116)
        self.assertEqual(U.canonical(released), U.canonical(U.colouring_clauses(529, self.edges, 4)))
        self.assertTrue(U.triangle_units(list(T.SBP_UNITS), self.edges, 4))
        self.assertTrue(U.triangle_units(list(T.TEXT_UNITS), self.edges, 4))

    def test_the_released_proof_needs_vertex_6_not_7(self):
        four = U.colouring_clauses(529, self.edges, 4)
        steps = U.parse_drat(self.data["heule529-4-sbp.drat"], 2116)
        self.assertEqual(sum(1 for deleted, _ in steps if not deleted), 30835)
        self.assertEqual(T.first_not_rup(2116, four + [(u,) for u in T.TEXT_UNITS], steps), 62)
        if os.environ.get("TRIM_SLOW"):
            self.assertEqual(T.first_not_rup(2116, four + [(u,) for u in T.SBP_UNITS], steps), 0)


if __name__ == "__main__":
    unittest.main()
