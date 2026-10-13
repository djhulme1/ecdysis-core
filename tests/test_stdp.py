"""Diehl & Cook's released network (stdp/check.py and stdp/dcnet.c): the streams; reading idx and .npy files and each
refusal; the generator's weights and the script's delays; classes and accuracy, ties included; the verdict at and
beside each threshold; the shuffled labels; the draws (rule 4); the C program against the Python reference, byte for
byte, on small jobs (learning and not, and one that runs away); and, with the claim's eight inputs at inputs/ (or
STDP_INPUTS), a short run and the first receipt's runaway, stopped at its digit.

Needs gcc for the C program. Run with: python3 -m unittest discover -s tests
"""

import array
import gzip
import importlib.util
import os
import shutil
import struct
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("stdp_check", os.path.join(HERE, "..", "stdp", "check.py"))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)

INPUTS = os.environ.get("STDP_INPUTS") or os.path.join(HERE, "..", "inputs")
HAVE = all(os.path.isfile(os.path.join(INPUTS, name)) for name, _ in M.INPUTS.values())
HAVE_GCC = shutil.which("gcc") is not None
SEED = "0" * 64


def npy(shape, values, descr="<f8"):
    head = "{'descr': '%s', 'fortran_order': False, 'shape': (%s), }" % (descr, ", ".join(str(s) for s in shape) +
                                                                          ("," if len(shape) == 1 else ""))
    head += " " * (118 - len(head)) + "\n"
    return b"\x93NUMPY\x01\x00" + len(head).to_bytes(2, "little") + head.encode("latin1") + struct.pack(
        f"<{len(values)}d", *values)


def digits(n, seed=1):
    rng = M.Xoshiro(seed)
    return bytes(int(rng.unif() * 256) if rng.unif() < 0.2 else 0 for _ in range(n * M.NIN))


class Streams(unittest.TestCase):
    def test_labels_and_seeds(self):
        self.assertNotEqual(M.seed_of(SEED, "a"), M.seed_of(SEED, "b"))
        self.assertNotEqual(M.seed_of(SEED, "a"), M.seed_of("1" * 64, "a"))
        a, b = M.Xoshiro(5), M.Xoshiro(5)
        self.assertEqual([a.next() for _ in range(4)], [b.next() for _ in range(4)])
        self.assertTrue(all(0.0 <= a.unif() < 1.0 for _ in range(1000)))


class Files(unittest.TestCase):
    def test_idx(self):
        imgs = gzip.compress((2051).to_bytes(4, "big") + (2).to_bytes(4, "big") + (28).to_bytes(4, "big") +
                             (28).to_bytes(4, "big") + bytes(2 * 784))
        self.assertEqual(len(M.read_idx(imgs)), 2 * 784)
        labels = gzip.compress((2049).to_bytes(4, "big") + (3).to_bytes(4, "big") + bytes([1, 9, 0]))
        self.assertEqual(list(M.read_idx(labels)), [1, 9, 0])
        for bad in (gzip.compress((2049).to_bytes(4, "big") + (2).to_bytes(4, "big") + bytes([1, 10])),
                    gzip.compress((2051).to_bytes(4, "big") + (1).to_bytes(4, "big") + (27).to_bytes(4, "big") +
                                  (28).to_bytes(4, "big") + bytes(27 * 28)),
                    gzip.compress((7).to_bytes(4, "big"))):
            with self.subTest(bad=bad[:12]), self.assertRaises(M.Refused):
                M.read_idx(bad)

    def test_npy(self):
        self.assertEqual(M.read_npy(npy((2, 3), [1.0, 2.0, 3.0, 4.0, 5.0, 6.0])), ((2, 3), (1.0, 2.0, 3.0, 4.0, 5.0, 6.0)))
        self.assertEqual(M.read_npy(npy((2,), [0.5, 0.25]))[0], (2,))
        for bad in (npy((2,), [1.0, 2.0], descr="|O"), npy((3,), [1.0, 2.0]), b"PK\x03\x04" + bytes(20)):
            with self.subTest(bad=bad[:12]), self.assertRaises(M.Refused):
                M.read_npy(bad)


class Network(unittest.TestCase):
    def test_initial_weights_and_delays(self):
        w, d = M.initial(SEED, 10, "t")
        self.assertEqual((len(w), len(d)), (7840, 7840))
        self.assertTrue(all(0.003 <= x < 0.303 for x in w))
        self.assertEqual((min(d), max(d)), (0, 19))
        self.assertNotEqual(M.initial(SEED, 10, "u")[0], w)


class Classes(unittest.TestCase):
    def test_assignments_and_accuracy(self):
        ne = 3
        counts = array.array("i", [5, 0, 0,  4, 1, 0,  0, 3, 0,  0, 0, 0])   # 4 digits x 3 neurons
        labels = [1, 1, 2, 2]
        a = M.assignments(counts, labels, ne)
        self.assertEqual(a, [1, 2, -1])                    # neuron 2 never fires: no class
        self.assertEqual(M.accuracy(counts, labels, a, ne), 75.0)   # the silent digit goes to the highest tie, 9
        self.assertEqual(M.accuracy(array.array("i", [1, 1, 0]), [2], [1, 2, -1], ne), 100.0)   # tie 1 and 2: 2

    def test_shuffled_is_a_permutation(self):
        labels = [k % 10 for k in range(100)]
        sh = M.shuffled(SEED, labels)
        self.assertEqual(sorted(sh), sorted(labels))
        self.assertNotEqual(sh, labels)


class Draws(unittest.TestCase):
    def test_the_first_draw_that_counts(self):
        self.assertEqual(M.pick({1: "clean", 2: "clean"}), (1, 2))
        self.assertEqual(M.pick({1: "ran away", 2: "clean"}), (2, None))
        self.assertEqual(M.pick({1: "clean", 2: "ran away"}), (1, None))
        self.assertEqual(M.pick({1: "ran away", 2: "ran away", 3: "clean"}), (3, None))
        self.assertEqual(M.pick({1: "ran away", 2: "ran away", 3: "ran away"}), (None, None))

    def test_a_third_draw_only_when_both_ran_away(self):
        self.assertEqual(M.needs_another({1: "ran away", 2: "ran away"}), 3)
        self.assertIsNone(M.needs_another({1: "ran away", 2: "training"}))
        self.assertIsNone(M.needs_another({1: "ran away", 2: "clean"}))
        self.assertIsNone(M.needs_another({1: "ran away", 2: "ran away", 3: "ran away"}))
        self.assertEqual(M.needs_another({1: "ran away"}), 2)            # the released network's delays

    def test_words(self):
        n = {"400": 60_000, "100": 40_000}
        r = {"run": "train", "digit": 65_469, "spikes": 38_796}
        self.assertEqual(M.runaway_words([("400", 1, r)], n), "400 draw 1: training, pass 2 digit 5,469 (38,796 spikes)")
        self.assertEqual(M.runaway_words([], n), "none")
        many = [("400", k, dict(r, run="assign")) for k in range(1, 4)] * 3
        self.assertLessEqual(len(M.runaway_words(many, n)), M.LIMIT)
        status = {"400": {1: "ran away", 2: "clean"}, "100": {1: "clean", 2: "clean"}, "released": {1: "clean"}}
        self.assertEqual(M.draws_words(status, {"400": 2, "100": 1, "released": 1}),
                         "400: 1 ran away, 2 used; 100: 1 used, 2 clean; released: 1 used")


class Verdict(unittest.TestCase):
    def test_at_and_beside_each_threshold(self):
        self.assertEqual(sum(M.conditions(85.0, 83.0).values()), 2)
        self.assertEqual(sum(M.conditions(84.99, 82.99).values()), 1)
        self.assertEqual(sum(M.conditions(85.0, 83.01).values()), 1)
        self.assertEqual(sum(M.conditions(80.0, 79.0).values()), 0)


@unittest.skipUnless(HAVE_GCC, "needs gcc")
class Compiled(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dir = tempfile.mkdtemp()
        cls.exe = M.build(cls.dir)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.dir)

    def test_reference_byte_for_byte(self):
        self.assertEqual(M.reference_agrees(self.exe, self.dir, digits(3), SEED), 3)

    def test_a_runaway_is_stopped_and_reported(self):
        img = bytes(200 if 300 <= i < 500 else 0 for i in range(M.NIN))       # 200 bright pixels
        out = M.finish(M.start(self.exe, M.runaway_job(img, SEED), self.dir, "runaway"), self.dir, "runaway", 0)
        self.assertEqual((out["runaway"]["ne"], out["runaway"]["digit"], out["runaway"]["repeat"]), (200, 0, 0))
        self.assertGreater(out["runaway"]["spikes"], 10 * 200)

    def test_round_trip_and_repeats(self):
        w, d = M.initial(SEED, 4, "rt")
        job = M.job_bytes(4, bytes(2 * M.NIN), 0, 1, 0.0, 9, w, [20.0] * 4, d)     # blank digits never reach 5 spikes
        h = M.start(self.exe, job, self.dir, "blank")
        h[0].wait()
        self.assertNotEqual(h[0].returncode, 0)                                     # a thousand repeats, then it stops
        img = digits(2, seed=3)
        job = M.job_bytes(4, img, 1, 2, 0.05, 9, w, [20.0] * 4, d)
        out = M.finish(M.start(self.exe, job, self.dir, "rt"), self.dir, "rt", 1)
        self.assertEqual((out["ne"], out["nex"], len(out["counts"]), len(out["repeats"])), (4, 2, 0, 4))
        self.assertAlmostEqual(sum(out["w"][0::4]), 78.0, delta=2.0)                  # normalised before each digit

    def test_a_job_with_a_bad_delay_is_refused(self):
        w, d = M.initial(SEED, 4, "bad")
        d = bytes([25]) + d[1:]
        h = M.start(self.exe, M.job_bytes(4, digits(1), 0, 1, 0.0, 1, w, [20.0] * 4, d), self.dir, "bad")
        h[0].wait()
        self.assertEqual(h[0].returncode, 2)


@unittest.skipUnless(HAVE and HAVE_GCC, "needs gcc and the claim's eight inputs at inputs/ or STDP_INPUTS")
class Run(unittest.TestCase):
    def test_a_short_run(self):
        with tempfile.TemporaryDirectory() as d:
            out, detail = M.run(SEED, inputs=INPUTS, results=d, short=(300, 600, 300), log=None)
            self.assertEqual(sorted(os.listdir(d)), ["detail.json", "outputs.json"])
        self.assertEqual(tuple(out), M.OUTPUTS)
        self.assertEqual(out["script_facts"], "59 of 59")
        self.assertEqual(out["controls"], "3 of 3")
        self.assertIn("reference: 3 of 3 small jobs byte for byte", out["control_detail"])
        self.assertTrue(0.0 <= out["acc_100"] <= 100.0 and 0.0 <= out["acc_400"] <= 100.0)
        self.assertTrue(out["draws"].startswith("400: 1 ") and "released: 1 used" in out["draws"])
        self.assertGreater(out["acc_released"], 80.0)

    def test_the_first_receipts_runaway(self):
        """The first receipt's 400-neuron training (6d2aeda8..., its seed and its labels) runs away at digit 5,469."""
        seed = "7f73ddc114ce2faaccee24371d4e252c08c733e8b04c491d8323b3e21c139c44"
        xtr = M.read_idx(M.input_bytes(INPUTS, "train_x"))
        w, d = M.initial(seed, 400, "400")
        job = M.job_bytes(400, xtr[:5_500 * M.NIN], 1, 1, M.THETA_PLUS, M.seed_of(seed, "in/train/400"), w,
                          [M.THETA_START] * 400, d)
        with tempfile.TemporaryDirectory() as tmp:
            exe = M.build(tmp)
            out = M.finish(M.start(exe, job, tmp, "first"), tmp, "first", 1)
        self.assertEqual((out["runaway"]["digit"], out["runaway"]["repeat"]), (5469, 0))


if __name__ == "__main__":
    unittest.main()
