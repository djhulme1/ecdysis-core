"""The order check (iit4/orders.py): the verdict at and either side of each of its clauses, values grouped to 1e-6,
relabelling that keeps the dynamics and a relabelling of rows alone caught, PyPhi's recorded rows read for all 24
orders, the refusal of another state; and, with the claim's three files at inputs/ (or IIT4_INPUTS), PQRS in 0101 under
all 24 orders against the stated values and PyPhi's own output. With IIT4_SLOW set, a whole run with every state.

Run with: python3 -m unittest discover -s tests
"""

import itertools
import os
import shutil
import sys
import tempfile
import unittest
import warnings

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))

from iit4 import engine as E  # noqa: E402
from iit4 import orders as O  # noqa: E402

warnings.simplefilter("ignore", RuntimeWarning)

INPUTS = os.environ.get("IIT4_INPUTS") or os.path.join(HERE, "..", "inputs")
HAVE = all(os.path.isfile(os.path.join(INPUTS, name)) for name in O.INPUTS)
SLOW = bool(os.environ.get("IIT4_SLOW"))
SEED = "0" * 64


def fabricated(values=O.STATED, thirteen=15):
    """24 rows meeting the test: the nine stated values, 13 distinctions in the first `thirteen` rows."""
    phis = list(values) + [values[0]] * (24 - len(values))
    return [{"big_phi": p, "distinctions": 13 if i < thirteen else 12} for i, p in enumerate(phis)]


class Verdict(unittest.TestCase):
    def test_the_stated_values_pass(self):
        self.assertTrue(O.verdict(fabricated()))

    def test_one_value_everywhere_fails(self):
        self.assertFalse(O.verdict(fabricated(values=(391.2472,) * 9)))

    def test_a_value_off_by_more_than_1e4_fails(self):
        moved = list(O.STATED)
        moved[3] += 2e-4
        self.assertFalse(O.verdict(fabricated(values=tuple(moved))))
        moved[3] = O.STATED[3] + 5e-5
        self.assertTrue(O.verdict(fabricated(values=tuple(moved))))

    def test_a_missing_value_fails(self):
        self.assertFalse(O.verdict(fabricated(values=O.STATED[:-1] + (O.STATED[0],))))

    def test_other_counts_of_distinctions_fail(self):
        self.assertFalse(O.verdict(fabricated(thirteen=14)))
        self.assertFalse(O.verdict(fabricated(thirteen=16)))

    def test_distinct_groups_to_1e6(self):
        self.assertEqual(O.distinct([1.0, 1.0 + 5e-7, 2.0, 2.0000001, 3.0]), [1.0, 2.0, 3.0])


class Relabelling(unittest.TestCase):
    def tpm(self):
        return [[s[(i + 1) % 4] ^ s[i] for i in range(4)] for s in E.all_states(4)]

    def test_relabelling_keeps_the_dynamics(self):
        tpm = self.tpm()
        for order in itertools.permutations(range(4)):
            network, _ = O.K.permuted(tpm, (0, 1, 0, 1), order, O.LABELS)
            self.assertTrue(O.keeps_dynamics(tpm, network, order))

    def test_rows_alone_are_caught(self):
        tpm = self.tpm()
        self.assertFalse(O.keeps_dynamics(tpm, O.rows_only_permuted(tpm, (1, 2, 3, 0)), (1, 2, 3, 0)))

    def test_pyphis_rows_cover_every_order(self):
        ref = O.reference_rows()
        self.assertEqual(sorted(ref), sorted("".join(p) for p in itertools.permutations(O.LABELS)))
        self.assertAlmostEqual(ref["PQRS"]["big_phi"], O.AUTHORS[0], places=6)
        self.assertEqual(len({round(r["big_phi"], 6) for r in ref.values()}), 9)


@unittest.skipUnless(HAVE, "the claim's three files are not at inputs/ (or IIT4_INPUTS)")
class TheClaim(unittest.TestCase):
    def test_refuses_other_bytes_and_another_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            for name in O.INPUTS:
                shutil.copy(os.path.join(INPUTS, name), tmp)
            with open(os.path.join(tmp, "uv.lock"), "ab") as f:
                f.write(b"\n")
            with self.assertRaises(O.Refused):
                O.read_inputs(tmp)
        tpm, state = O.read_inputs(INPUTS)
        self.assertEqual(state, (0, 1, 0, 1))

    def test_pqrs_in_0101_under_every_order(self):
        tpm, state = O.read_inputs(INPUTS)
        rows = O.all_orders(tpm, state)
        self.assertTrue(O.verdict(rows))
        self.assertEqual(O.matches_pyphi(rows, O.reference_rows()), 24)


@unittest.skipUnless(SLOW and HAVE, "IIT4_SLOW not set, or no inputs")
class WholeRun(unittest.TestCase):
    def test_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            out, _ = O.run(SEED, results=tmp, inputs=INPUTS, log=lambda s: None)
        self.assertEqual(tuple(out), O.OUTPUTS)
        self.assertEqual(out["test_passed"], 1)
        self.assertEqual((out["controls_passed"], out["controls_total"]), (5, 5))
        self.assertEqual(out["distinct_phi"], 9)
        self.assertEqual(out["pyphi_match"], "24 of 24")


if __name__ == "__main__":
    unittest.main()
