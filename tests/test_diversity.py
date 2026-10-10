"""Hordijk, Steel & Kauffman's diversity check: n* and the Jain-Krishna points from the rules' formulas, against the
registered test's own form in floating point and Table 1's diversities; each ligation sharing its catalysts with its
cleavage; the Jain-Krishna system and both of its rules against the definition of an RAF on every subset of small random
systems, with a cycle rule that forgets the pruned types caught; instances fixed by the seed and the label; the polymer
model far below and far above n*; the verdict at and either side of half; controls that fail when the reduction is
broken; other bytes refused. With CatReNet's three examples (at inputs/ or in RAF_EXAMPLES) and DIVERSITY_SLOW set,
also whole runs at a hundredth of the instances, pooled and in one worker alike.

raf/check.py's own parts (the polymer model, the sampler, max_raf, the CRS reader) are tested in test_raf.py.

Run with: python3 -m unittest discover -s tests
"""

import os

for _var in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
    os.environ.setdefault(_var, "1")   # as raf/diversity.py does: no BLAS threads in a process that forks

import importlib.util  # noqa: E402
import itertools  # noqa: E402
import json  # noqa: E402
import math  # noqa: E402
import sys  # noqa: E402
import tempfile  # noqa: E402
import unittest  # noqa: E402
from unittest import mock  # noqa: E402

import numpy as np  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
# Registered in sys.modules under its own name, so that the worker pool can name run_job.
_spec = importlib.util.spec_from_file_location("raf_diversity", os.path.join(HERE, "..", "raf", "diversity.py"))
D = importlib.util.module_from_spec(_spec)
sys.modules["raf_diversity"] = D
_spec.loader.exec_module(D)
R = D.R

SEED = "0" * 64
OTHER = "f" * 64
EXAMPLES = os.environ.get("RAF_EXAMPLES") or os.path.join(HERE, "..", "inputs")
HAVE = all(os.path.isfile(os.path.join(EXAMPLES, name)) for name, *_ in R.INPUTS)
# Type 0 catalyses the formation of type 1, 1 that of 2, 2 that of 3: (reactions, catalysts).
CHAIN = (np.array([1, 2, 3], dtype=np.int64), np.array([0, 1, 2], dtype=np.int64))


def raf_by_definition(N, rxn, cat):
    """Whether some non-empty set of types has every member's formation catalysed by a member: every subset tried."""
    made_by = [set() for _ in range(N)]
    for r, m in zip(rxn.tolist(), cat.tolist()):
        made_by[r].add(m)
    return any(all(made_by[j] & set(s) for j in s)
               for size in range(1, N + 1) for s in itertools.combinations(range(N), size))


def forgetful_cycle(N, rxn, cat):
    """A broken cycle rule: a catalysis into a type already pruned still counts."""
    alive = np.ones(N, dtype=bool)
    while True:
        new = alive & (np.bincount(cat[alive[cat]], minlength=N) > 0)
        if np.array_equal(new, alive):
            return bool(new.any())
        alive = new


class Rules(unittest.TestCase):
    def test_n_star_is_the_registered_least_n(self):
        for p, n in zip(D.TABLE1, D.NSTAR):
            with self.subTest(p=p):
                self.assertEqual(D.nstar(p), n)

                def holds(m):
                    return m + math.log2(m - 2) > math.log2(1 / float(p)) - 2
                self.assertTrue(holds(n))
                self.assertFalse(any(holds(m) for m in range(3, n)))

    def test_table_1_s_diversities_are_those_of_the_next_n(self):
        # Table 1, row BPM: 131,070, 32,766, 16,382, 4094, 2046, 510; row JKM: 1/(2p), between the two points.
        self.assertEqual([R.molecule_count(n + 1) for n in D.NSTAR], [131070, 32766, 16382, 4094, 2046, 510])
        for p in D.TABLE1:
            low, high = D.jkm_points(p)
            self.assertTrue(low < 1 / (2 * p) <= high)

    def test_the_jain_krishna_points(self):
        self.assertEqual(D.jkm_points(D.TABLE1[0]), (393469, 693147))
        for p in D.TABLE1:
            with self.subTest(p=p):
                low, high = D.jkm_points(p)
                self.assertTrue(low < (1 - math.exp(-0.5)) / float(p) <= low + 1)
                self.assertTrue(high <= math.log(2) / float(p) < high + 1)


class Models(unittest.TestCase):
    def test_each_ligation_shares_its_catalysts_with_its_cleavage(self):
        S, (rxn, mol) = D.two_way(R.generator(SEED, "test/two-way", 0), 6, 0.01)
        nl = R.ligation_count(6)
        pairs = set(zip(rxn.tolist(), mol.tolist()))
        self.assertEqual((S.reactions, len(pairs)), (2 * nl, rxn.size))
        ligation = {(r, m) for r, m in pairs if r < nl}
        self.assertGreater(len(ligation), 100)
        self.assertEqual(ligation, {(r - nl, m) for r, m in pairs if r >= nl})

    def test_the_one_way_reading_draws_each_direction_on_its_own(self):
        S = R.polymer_system(6)
        rxn, mol = R.catalysis_pairs(R.generator(SEED, "test/one-way", 0), S.reactions, S.molecules, 0.01)
        nl = R.ligation_count(6)
        pairs = set(zip(rxn.tolist(), mol.tolist()))
        self.assertNotEqual({(r, m) for r, m in pairs if r < nl}, {(r - nl, m) for r, m in pairs if r >= nl})

    def test_the_jain_krishna_system(self):
        S = D.elementary(5)
        self.assertEqual((S.molecules, S.reactions, np.flatnonzero(S.food).tolist()), (6, 5, [5]))
        self.assertEqual(sorted(zip(*(a.tolist() for a in S.reactants))), [(j, 5) for j in range(5)])
        self.assertEqual(sorted(zip(*(a.tolist() for a in S.products))), [(j, j) for j in range(5)])

    def test_a_chain_has_no_raf_and_a_cycle_has_one(self):
        S = D.elementary(4)
        self.assertFalse(R.max_raf(S, CHAIN)[0].any())
        self.assertFalse(D.has_cycle(4, *CHAIN))
        loop = (np.append(CHAIN[0], 1), np.append(CHAIN[1], 3))     # and 3 catalyses 1's formation
        self.assertEqual(np.flatnonzero(R.max_raf(S, loop)[0]).tolist(), [1, 2, 3])
        self.assertTrue(D.has_cycle(4, *loop))

    def test_both_rules_agree_with_the_definition(self):
        seen, forgetful_wrong = set(), 0
        for i in range(300):
            rng = R.generator(SEED, "test/jkm-small", i)
            N = int(rng.integers(1, 10))
            rxn, cat = R.catalysis_pairs(rng, N, N, float(rng.choice([0.05, 0.1, 0.2, 0.3])))
            expected = raf_by_definition(N, rxn, cat)
            seen.add(expected)
            with self.subTest(i=i):
                self.assertEqual(bool(R.max_raf(D.elementary(N), (rxn, cat))[0].any()), expected)
                self.assertEqual(D.has_cycle(N, rxn, cat), expected)
            forgetful_wrong += forgetful_cycle(N, rxn, cat) != expected
        self.assertEqual(seen, {False, True})
        self.assertGreater(forgetful_wrong, 0)
        self.assertTrue(forgetful_cycle(4, *CHAIN))


class Draws(unittest.TestCase):
    def test_an_instance_is_its_label_s_draw(self):
        S, catalysis = D.two_way(R.generator(SEED, "diversity/bpm/p4/n10", 3), 10, float(D.TABLE1[4]))
        alive, made = R.max_raf(S, catalysis)
        self.assertEqual(D.run_job((SEED, "bpm", 4, 10, 3)),
                         (bool(alive.any()), int(alive.sum()), int(made.sum()), None))
        S = R.polymer_system(10)
        catalysis = R.catalysis_pairs(R.generator(SEED, "diversity/oneway/p4/n10", 3), S.reactions, S.molecules, 1e-4)
        alive, made = R.max_raf(S, catalysis)
        self.assertEqual(D.run_job((SEED, "oneway", 4, 10, 3)),
                         (bool(alive.any()), int(alive.sum()), int(made.sum()), None))
        rxn, cat = R.catalysis_pairs(R.generator(SEED, "diversity/jkm/p5/N1386", 2), 1386, 1386, float(D.TABLE1[5]))
        alive, made = R.max_raf(D.elementary(1386), (rxn, cat))
        self.assertEqual(D.run_job((SEED, "jkm", 5, 1386, 2)),
                         (bool(alive.any()), int(alive.sum()), int(made.sum()), D.has_cycle(1386, rxn, cat)))

    def test_other_seeds_and_instances_draw_otherwise(self):
        sizes = {D.run_job((seed, "bpm", 4, 10, i))[1] for seed in (SEED, OTHER) for i in range(4)}
        self.assertGreater(len(sizes), 4)


class Threshold(unittest.TestCase):
    def test_far_below_and_far_above_n_star(self):
        # p = 1e-4, n* = 9: three below it no instance of 20 has an RAF; two above it, every one.
        self.assertEqual(sum(D.run_job((SEED, "bpm", 4, 6, i))[0] for i in range(20)), 0)
        self.assertEqual(sum(D.run_job((SEED, "bpm", 4, 11, i))[0] for i in range(20)), 20)
        # The Jain-Krishna model at p = 5e-4: at a tenth of N_low (N p = 0.04) about one instance in 25 has a cycle;
        # at three times N_high (N p = 2.1), every one.
        self.assertLessEqual(sum(D.run_job((SEED, "jkm", 5, 78, i))[0] for i in range(20)), 2)
        self.assertEqual(sum(D.run_job((SEED, "jkm", 5, 4158, i))[0] for i in range(20)), 20)


class Verdict(unittest.TestCase):
    PILOT = ([0, 0, 1, 2, 2, 29], [185, 190, 195, 198, 199, 200], [400] * 6, [700] * 6)

    def changed(self, which, index, value):
        counts = [list(x) for x in self.PILOT]
        counts[which][index] = value
        return counts

    def test_counts_like_the_pilot_s_pass(self):
        self.assertTrue(D.verdict(*self.PILOT))

    def test_half_is_on_the_failing_side_at_n_star_and_n_low(self):
        for which, index, failing, passing in ((0, 5, 100, 99), (1, 0, 99, 100), (2, 3, 500, 499), (3, 2, 499, 500)):
            with self.subTest(which=which):
                self.assertFalse(D.verdict(*self.changed(which, index, failing)))
                self.assertTrue(D.verdict(*self.changed(which, index, passing)))

    def test_odd_counts_halve_exactly(self):
        self.assertTrue(D.verdict([1], [2], [2], [3], 3, 5))
        self.assertFalse(D.verdict([2], [2], [2], [3], 3, 5))
        self.assertFalse(D.verdict([1], [1], [2], [3], 3, 5))
        self.assertFalse(D.verdict([1], [2], [3], [3], 3, 5))
        self.assertFalse(D.verdict([1], [2], [2], [2], 3, 5))


class Controls(unittest.TestCase):
    def test_the_controls_pass(self):
        rows = D.controls(SEED)
        self.assertEqual(len(rows), 4)
        self.assertTrue(all(r["passed"] for r in rows), rows)

    def test_a_reduction_without_its_catalyst_check_fails_them_all(self):
        def uncatalysed(S, catalysis):
            alive = np.ones(S.reactions, dtype=bool)
            while True:
                W = R.closure(S, alive)
                keep = alive & R.present(S.reactants, W, S.reactions)
                if np.array_equal(keep, alive):
                    return alive, W
                alive = keep
        with mock.patch.object(R, "max_raf", uncatalysed):
            rows = D.controls(SEED)
        self.assertEqual([r["passed"] for r in rows], [False, False, False, False])

    def test_a_reduction_that_keeps_nothing_fails_the_others(self):
        with mock.patch.object(R, "max_raf", lambda S, c: (np.zeros(S.reactions, dtype=bool), S.food.copy())):
            rows = D.controls(SEED)
        self.assertEqual([r["passed"] for r in rows], [True, True, False, False])


class Inputs(unittest.TestCase):
    def test_other_bytes_are_refused_before_anything_runs(self):
        with tempfile.TemporaryDirectory() as d:
            for name, *_ in R.INPUTS:
                with open(os.path.join(d, name), "w", encoding="ascii") as f:
                    f.write("food: a\nr1 : a -> b\n")
            with mock.patch.object(D, "run_all") as run_all, self.assertRaises(SystemExit):
                D.run(SEED, os.path.join(d, "results"), inputs=d, workers=1, scale=100, log=lambda *_: None)
            run_all.assert_not_called()
            self.assertFalse(os.path.exists(os.path.join(d, "results")))


@unittest.skipUnless(HAVE and os.environ.get("DIVERSITY_SLOW"), "set DIVERSITY_SLOW, with CatReNet's examples")
class Run(unittest.TestCase):
    def test_runs_at_a_hundredth(self):
        with tempfile.TemporaryDirectory() as d:
            pooled, _ = D.run(SEED, os.path.join(d, "a"), inputs=EXAMPLES, workers=2, scale=100, log=lambda *_: None)
            single, _ = D.run(SEED, os.path.join(d, "b"), inputs=EXAMPLES, workers=1, scale=100, log=lambda *_: None)
            with open(os.path.join(d, "a", "outputs.json"), encoding="ascii") as f:
                self.assertEqual(json.load(f), pooled)
        self.assertEqual(pooled, single)
        self.assertEqual(set(pooled), set(D.OUTPUTS))
        self.assertEqual((pooled["nstar"], pooled["jkm_low_n"], pooled["jkm_high_n"]),
                         ("15,13,12,10,9,7", "393469,78693,39346,7869,3934,786", "693147,138629,69314,13862,6931,1386"))
        self.assertEqual((pooled["instances"], pooled["validation_ok"], pooled["jkm_agree"]),
                         (12 * 2 + 12 * 10 + 4, 1, 1))
        self.assertEqual((pooled["controls_passed"], pooled["controls_total"]), (6, 6))


if __name__ == "__main__":
    unittest.main()
