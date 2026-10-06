"""The RAF check on made-up cases: the polymer model's numbering and reaction counts, ligation and cleavage as
inverses, the builder against the general form built from strings, closure, maxRAF and maxCAF on hand-made systems
with known answers and against every subset of small random systems, a reduction without its catalyst check caught,
the exact sampler, instances fixed by the seed, the CRS reader and its refusals, other bytes refused, pooled and
serial runs alike, and a whole run with made-up inputs. With CatReNet's three examples (put them at inputs/ or name
their directory in RAF_EXAMPLES), also the sizes its README states.

Run with: python3 -m unittest discover -s tests
"""

import os

for _var in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
    os.environ.setdefault(_var, "1")   # as raf/check.py does: no BLAS threads in a process that forks

import contextlib  # noqa: E402
import hashlib  # noqa: E402
import importlib.util  # noqa: E402
import itertools  # noqa: E402
import json  # noqa: E402
import sys  # noqa: E402
import tempfile  # noqa: E402
import unittest  # noqa: E402
from fractions import Fraction  # noqa: E402

import numpy as np  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
# Loaded under its own name, since other tests import other labs' check.py; registered in sys.modules so that the
# worker pool can name its functions.
_spec = importlib.util.spec_from_file_location("raf_check", os.path.join(HERE, "..", "raf", "check.py"))
R = importlib.util.module_from_spec(_spec)
sys.modules["raf_check"] = R
_spec.loader.exec_module(R)

SEED = "0" * 64
OTHER = "f" * 64


def write(path, data):
    with open(path, "wb") as f:
        f.write(data)


def examples_dir():
    d = os.environ.get("RAF_EXAMPLES") or os.path.join(HERE, "..", "inputs")
    return d if all(os.path.isfile(os.path.join(d, name)) for name, *_ in R.INPUTS) else None


# ---------------------------------------------------------------- independent references, by definition

def as_sets(S, catalysis):
    """A general-form system as Python sets: (food, [(reactants, products, catalysts)])."""
    def rows(entries):
        out = [set() for _ in range(S.reactions)]
        for r, m in zip(*entries):
            out[int(r)].add(int(m))
        return out
    return (set(np.flatnonzero(S.food).tolist()),
            list(zip(rows(S.reactants), rows(S.products), rows(catalysis))))


def ref_closure(food, reactions, subset):
    W, grew = set(food), True
    while grew:
        grew = False
        for k in subset:
            reac, prod, _ = reactions[k]
            if reac <= W and not prod <= W:
                W |= prod
                grew = True
    return W


def is_raf(food, reactions, subset):
    """Hordijk and Steel's definition: non-empty, and every reaction's reactants and one of its catalysts lie in the
    closure of the food under the subset."""
    W = ref_closure(food, reactions, subset)
    return bool(subset) and all(reactions[k][0] <= W and reactions[k][2] & W for k in subset)


def is_caf(food, reactions, subset):
    """Constructively autocatalytic: the subset's reactions can run one after another from the food, each with its
    reactants and a catalyst already present (availability only grows, so taking any ready reaction first works)."""
    W, left = set(food), set(subset)
    while left:
        ready = {k for k in left if reactions[k][0] <= W and reactions[k][2] & W}
        if not ready:
            return False
        for k in ready:
            W |= reactions[k][1]
        left -= ready
    return bool(subset)


def union_of_all(food, reactions, test):
    """The union of every subset that passes test: the maxRAF (or maxCAF), since unions of RAFs (CAFs) are RAFs (CAFs)."""
    out = set()
    for size in range(1, len(reactions) + 1):
        for subset in itertools.combinations(range(len(reactions)), size):
            if not set(subset) <= out and test(food, reactions, set(subset)):
                out |= set(subset)
    return out


def ref_max_raf(food, reactions):
    """The reduction again, in plain Python sets."""
    alive = set(range(len(reactions)))
    while True:
        W = ref_closure(food, reactions, alive)
        keep = {k for k in alive if reactions[k][0] <= W and reactions[k][2] & W}
        if keep == alive:
            return alive
        alive = keep


def ref_max_caf(food, reactions):
    W, taken = set(food), set()
    while True:
        ready = {k for k, (reac, _, cats) in enumerate(reactions) if reac <= W and cats & W}
        if ready == taken:
            return taken
        taken = ready
        for k in taken:
            W |= reactions[k][1]


def string_model(M):
    """Kauffman's model built naively from strings, in the same numbering, as the general form."""
    strings = [format(v, f"0{L}b") for L in range(1, M + 1) for v in range(1 << L)]
    number = {s: k for k, s in enumerate(strings)}
    ligs = [(x[:k], x[k:], x) for L in range(2, M + 1) for k in range(1, L)
            for x in (format(v, f"0{L}b") for v in range(1 << L))]
    reactions = ([([number[a], number[b]], [number[x]]) for a, b, x in ligs]
                 + [([number[x]], [number[a], number[b]]) for a, b, x in ligs])
    return R.system(len(strings), [number[s] for s in strings if len(s) <= 2], reactions), strings, ligs


def random_system(rng, molecules=7, reactions=8):
    """A small random system: food {0, 1}; each reaction one or two reactants and products, zero to two catalysts."""
    lists, cats = [], []
    for _ in range(reactions):
        lists.append((rng.choice(molecules, rng.integers(1, 3), replace=False).tolist(),
                      rng.choice(molecules, rng.integers(1, 3), replace=False).tolist()))
        cats.append(rng.choice(molecules, rng.integers(0, 3), replace=False).tolist())
    return R.system(molecules, [0, 1], lists), R.pairs(cats)


# Hand-made systems with known answers: (CRS text, maxRAF, maxCAF).
HAND = {
    # r1 is catalysed by food; r2's only catalyst z is never made, so it goes, and with it d, r3's catalyst.
    "dropped": ("Food: a b\nr1 : a + b [a] => c\nr2 : c [z] => d\nr3 : c + a [d] => e\nr4 : q [a] => w\n",
                {"r1"}, {"r1"}),
    # c catalyses its own making: an RAF, but nothing starts it from the food, so no CAF.
    "raf, no caf": ("Food: a, b\nr1 : a + b [c] => c\n", {"r1"}, set()),
    # A cycle: r2 makes e, r1's catalyst, from c, which r1 makes; r3 and r4 hang from it. Only r4 is catalysed by
    # the food, and its reactant f needs r3, so there is no CAF.
    "cycle": ("# a comment\nFood: a b\nr1 : a + b [e] -> c\nr2 : c + a [b] -> d + e\nr3 : b [d] -> f\n"
              "r4 : f + a [a] -> g\n", {"r1", "r2", "r3", "r4"}, set()),
    # Two-way: r1 runs backwards from food; r2 is catalysed by what r1 makes from its products.
    "two-way": ("Food: x y\nr1 : p + q [y] <=> x\nr2 : p + y [q] => s\nr3 : s [t] <-> u\n", {"r1", "r2"},
                {"r1", "r2"}),
}


def hand_results(module=R):
    """{name: (maxRAF, maxCAF)} of the hand-made systems, as module computes them."""
    out = {}
    for name, (text, _, _) in HAND.items():
        food, reactions = module.parse_crs(text)
        S, catalysis, owner, _ = module.crs_system(food, reactions)
        out[name] = (set(module.counted(module.max_raf(S, catalysis)[0], owner)),
                     set(module.counted(module.max_caf(S, catalysis)[0], owner)))
    return out


# ---------------------------------------------------------------- the polymer model

class Polymers(unittest.TestCase):
    def test_molecule_numbers_and_names(self):
        strings = [format(v, f"0{L}b") for L in range(1, 8) for v in range(1 << L)]
        self.assertEqual([R.molecule_name(i) for i in range(len(strings))], strings)
        self.assertEqual([R.molecule_id(len(s), int(s, 2)) for s in strings], list(range(len(strings))))
        self.assertEqual([R.molecule_name(i) for i in range(6)], ["0", "1", "00", "01", "10", "11"])
        S = R.polymer_system(5)
        self.assertEqual(np.flatnonzero(S.food).tolist(), [0, 1, 2, 3, 4, 5])

    def test_reaction_and_molecule_counts(self):
        for M in range(2, 11):
            S = R.polymer_system(M)
            self.assertEqual(S.molecules, sum(1 << L for L in range(1, M + 1)))
            self.assertEqual(S.molecules, 2 ** (M + 1) - 2)
            n = sum((L - 1) * (1 << L) for L in range(2, M + 1))
            self.assertEqual(n, (M - 2) * 2 ** (M + 1) + 4)
            self.assertEqual(S.reactions, 2 * n)
            self.assertEqual(S.reactants[0].size, 3 * n)   # two reactants for a ligation, one for a cleavage
            self.assertEqual(S.products[0].size, 3 * n)
        self.assertEqual(R.polymer_system(15).reactions, 1703944)

    def test_each_ligation_joins_its_reactants_in_the_stated_order(self):
        M = 6
        left, right, product = R.ligations(M)
        got = [(R.molecule_name(a), R.molecule_name(b), R.molecule_name(x)) for a, b, x in zip(left, right, product)]
        want = [(x[:k], x[k:], x) for L in range(2, M + 1) for k in range(1, L)
                for x in (format(v, f"0{L}b") for v in range(1 << L))]
        self.assertEqual(got, want)

    def test_ligation_and_cleavage_are_inverse(self):
        M = 6
        S = R.polymer_system(M)
        left, right, product = R.ligations(M)
        n = S.reactions // 2

        def by_reaction(entries):   # each reaction's molecules, with repeats (0 + 0 -> 00 has 0 twice)
            out = [[] for _ in range(S.reactions)]
            for r, m in zip(entries[0].tolist(), entries[1].tolist()):
                out[r].append(m)
            return [sorted(x) for x in out]

        rx, px = by_reaction(S.reactants), by_reaction(S.products)
        for j in range(n):
            self.assertEqual(rx[j], sorted([int(left[j]), int(right[j])]))
            self.assertEqual(px[j], [int(product[j])])
            self.assertEqual((rx[n + j], px[n + j]), (px[j], rx[j]))
        self.assertEqual(rx[0], [0, 0])   # the first ligation: 0 + 0 -> 00
        self.assertEqual(px[n], [0, 0])   # and its cleavage

    def test_the_builder_equals_the_general_form_built_from_strings(self):
        # As sets of (reaction, molecule) entries: the general form keeps a repeated reactant once, the builder twice,
        # which changes nothing (a reaction needs every entry present).
        for M in range(2, 8):
            S = R.polymer_system(M)
            T, _, _ = string_model(M)
            self.assertEqual((S.molecules, S.reactions), (T.molecules, T.reactions))
            np.testing.assert_array_equal(S.food, T.food)
            for a, b in ((S.reactants, T.reactants), (S.products, T.products)):
                self.assertEqual(set(zip(a[0].tolist(), a[1].tolist())), set(zip(b[0].tolist(), b[1].tolist())))

    def test_the_registered_m_is_the_least_with_p_n_at_least_4m(self):
        self.assertEqual({k: R.least_m(P) for k, P in R.PROBABILITIES}, R.REGISTERED)
        for k, P in R.PROBABILITIES:
            M = R.REGISTERED[k]
            self.assertGreaterEqual(P * ((M - 2) * 2 ** (M + 1) + 4), 4 * M)
            self.assertLess(P * ((M - 3) * 2 ** M + 4), 4 * (M - 1))
        plan = R.settings()
        self.assertEqual([s[3] for s in plan if s[0] == "test"], [9, 12, 15])
        self.assertEqual([(s[1], s[3]) for s in plan if s[0] == "curve"],
                         [("p2", M) for M in range(3, 9)] + [("p3", M) for M in range(3, 12)]
                         + [("p4", M) for M in range(3, 15)])
        self.assertEqual([(s[2], s[3]) for s in plan if s[0] == "control"],
                         [(Fraction(1, 2 * 2 * R.ligation_count(M)), M) for M in (9, 12, 15)])


# ---------------------------------------------------------------- closure, maxRAF and maxCAF

class Algorithms(unittest.TestCase):
    def test_closure_on_a_hand_made_system(self):
        # food a, b; r0 a + b -> c; r1 c -> d + e; r2 x -> y (x is never made); r3 d + e -> f
        S = R.system(8, [0, 1], [([0, 1], [2]), ([2], [3, 4]), ([5], [6]), ([3, 4], [7])])
        names = "abcdexyf"
        def cl(alive):
            return {names[k] for k in np.flatnonzero(R.closure(S, np.array(alive)))}
        self.assertEqual(cl([True] * 4), set("abcdef"))
        self.assertEqual(cl([True, False, True, True]), set("abc"))
        self.assertEqual(cl([False] * 4), set("ab"))
        self.assertEqual(cl([False, True, True, True]), set("ab"))

    def test_hand_made_systems_have_their_known_answers(self):
        got = hand_results()
        for name, (_, raf, caf) in HAND.items():
            self.assertEqual(got[name], (raf, caf), name)

    def test_a_reaction_catalysed_only_outside_the_closure_is_dropped(self):
        food, reactions = R.parse_crs(HAND["dropped"][0])
        S, catalysis, owner, molecules = R.crs_system(food, reactions)
        raf, W = R.max_raf(S, catalysis)
        self.assertEqual(R.counted(raf, owner), ["r1"])
        self.assertEqual({molecules[k] for k in np.flatnonzero(W)}, {"a", "b", "c"})
        everything = R.closure(S, np.ones(S.reactions, dtype=bool))
        self.assertTrue(everything[molecules.index("d")])   # d is made if r2 is allowed to run uncatalysed

    def test_a_reduction_without_its_catalyst_check_is_caught(self):
        saved = R.catalysed
        R.catalysed = lambda catalysis, W, reactions: np.ones(reactions, dtype=bool)
        try:
            broken = hand_results()
        finally:
            R.catalysed = saved
        wrong = [name for name, (_, raf, caf) in HAND.items() if broken[name] != (raf, caf)]
        self.assertIn("dropped", wrong)
        self.assertEqual(broken["dropped"][0], {"r1", "r2", "r3"})
        self.assertEqual(hand_results(), {name: (raf, caf) for name, (_, raf, caf) in HAND.items()})

    def test_against_every_subset_of_small_random_systems(self):
        rng = np.random.default_rng(7)
        nonempty_raf = nonempty_caf = differ = 0
        for _ in range(150):
            S, catalysis = random_system(rng)
            food, reactions = as_sets(S, catalysis)
            raf = set(np.flatnonzero(R.max_raf(S, catalysis)[0]).tolist())
            caf = set(np.flatnonzero(R.max_caf(S, catalysis)[0]).tolist())
            self.assertEqual(raf, union_of_all(food, reactions, is_raf))
            self.assertEqual(caf, union_of_all(food, reactions, is_caf))
            self.assertTrue(caf <= raf)
            nonempty_raf += bool(raf)
            nonempty_caf += bool(caf)
            differ += raf != caf
        self.assertGreater(nonempty_raf, 30)   # the cases are not all empty, nor all alike
        self.assertGreater(nonempty_caf, 15)
        self.assertGreater(differ, 15)

    def test_the_polymer_model_against_the_reference_in_plain_python(self):
        # Probabilities near each M's transition, so that the maxRAF is sometimes empty, sometimes partial, sometimes
        # everything; the instances are drawn as the run draws them.
        seen = set()
        for M, p in ((3, 0.01), (3, 0.08), (4, 0.03), (4, 0.3), (5, 0.012), (6, 0.004)):
            S = R.polymer_system(M)
            T, _, _ = string_model(M)
            for i in range(12):
                catalysis = R.catalysis_pairs(R.generator(SEED, "test/reference", i), S.reactions, S.molecules, p)
                food, reactions = as_sets(T, catalysis)
                raf, caf = R.max_raf(S, catalysis)[0], R.max_caf(S, catalysis)[0]
                np.testing.assert_array_equal(raf, R.max_raf(T, catalysis)[0])
                self.assertEqual(set(np.flatnonzero(raf).tolist()), ref_max_raf(food, reactions))
                self.assertEqual(set(np.flatnonzero(caf).tolist()), ref_max_caf(food, reactions))
                seen.add("empty" if not raf.any() else "all" if raf.all() else "partial")
        self.assertEqual(seen, {"empty", "partial", "all"})


# ---------------------------------------------------------------- the draws

class Draws(unittest.TestCase):
    def test_pairs_are_distinct_ordered_and_in_range(self):
        for i in range(20):
            rxn, mol = R.catalysis_pairs(R.generator(SEED, "test/range", i), 40, 14, 0.3)
            numbers = rxn * 14 + mol
            self.assertTrue((np.diff(numbers) > 0).all())
            self.assertTrue(((0 <= rxn) & (rxn < 40) & (0 <= mol) & (mol < 14)).all())
        rxn, mol = R.catalysis_pairs(R.generator(SEED, "test/one", 0), 5, 3, 1.0)
        self.assertEqual(list(zip(rxn.tolist(), mol.tolist())), [(r, m) for r in range(5) for m in range(3)])

    def test_the_count_and_each_pair_have_the_right_law(self):
        # 6 x 4 pairs at p = 0.3, 20000 draws: each pair's frequency, the joint frequency of neighbouring pairs and of
        # the first and last, and the mean count, each within five standard errors of the exact value.
        p, n, draws = 0.3, 24, 20000
        hits = np.zeros((draws, n), dtype=bool)
        for i in range(draws):
            rxn, mol = R.catalysis_pairs(R.generator(SEED, "test/law", i), 6, 4, p)
            hits[i, rxn * 4 + mol] = True
        tol = 5 * np.sqrt(p * (1 - p) / draws)
        self.assertLess(np.abs(hits.mean(axis=0) - p).max(), tol)
        joint = (hits[:, :-1] & hits[:, 1:]).mean(axis=0)
        self.assertLess(np.abs(joint - p * p).max(), 5 * np.sqrt(p * p * (1 - p * p) / draws))
        self.assertLess(abs((hits[:, 0] & hits[:, -1]).mean() - p * p), 5 * np.sqrt(p * p * (1 - p * p) / draws))
        counts = hits.sum(axis=1)
        self.assertLess(abs(counts.mean() - n * p), 5 * np.sqrt(n * p * (1 - p) / draws))
        self.assertLess(abs(counts.var() - n * p * (1 - p)), 0.15 * n * p * (1 - p))

    def test_the_mean_count_at_a_small_probability(self):
        reactions, molecules, p, draws = 1032, 126, 0.001, 400   # M = 6
        counts = [R.catalysis_pairs(R.generator(SEED, "test/mean", i), reactions, molecules, p)[0].size
                  for i in range(draws)]
        mu = p * reactions * molecules
        self.assertLess(abs(np.mean(counts) - mu), 5 * np.sqrt(mu * (1 - p) / draws))

    def test_the_draw_does_not_depend_on_the_chunk(self):
        # numpy draws geometric variates one after another, so an array of n is the same as n drawn in two parts;
        # the pairs are then the same whatever the chunk size.
        a = R.generator(SEED, "test/chunk", 0).geometric(0.001, size=1000)
        g = R.generator(SEED, "test/chunk", 0)
        b = np.concatenate([g.geometric(0.001, size=300), g.geometric(0.001, size=700)])
        np.testing.assert_array_equal(a, b)
        rxn, mol = R.catalysis_pairs(R.generator(SEED, "test/chunk", 1), 300, 50, 0.002)
        gaps = R.generator(SEED, "test/chunk", 1).geometric(0.002, size=1000)
        numbers = np.cumsum(gaps) - 1
        np.testing.assert_array_equal(rxn * 50 + mol, numbers[numbers < 300 * 50])

    def test_a_zero_gap_is_read_as_one_and_a_long_one_ends_the_draw(self):
        class Fake:
            def __init__(self, gaps):
                self.gaps = list(gaps)

            def geometric(self, p, size):
                out, self.gaps = self.gaps[:size], self.gaps[size:]
                return np.array(out + [1] * (size - len(out)), dtype=np.int64)

        rxn, mol = R.catalysis_pairs(Fake([0, 0, 3, 2 ** 62, 5]), 10, 10, 0.01)
        self.assertEqual((rxn * 10 + mol).tolist(), [0, 1, 4])
        # Gaps of 1 throughout: the first chunk (71 draws) falls short of the 100 pairs and the second completes them.
        rxn, mol = R.catalysis_pairs(Fake([]), 10, 10, 0.01)
        self.assertEqual((rxn * 10 + mol).tolist(), list(range(100)))

    def test_an_instance_is_fixed_by_the_seed_its_label_and_its_number(self):
        def draw(seed, label, i):
            rxn, mol = R.catalysis_pairs(R.generator(seed, label, i), 392, 62, 0.01)
            return (rxn * 62 + mol).tolist()
        a = draw(SEED, "raf/test/p2/m5", 3)
        self.assertEqual(a, draw(SEED, "raf/test/p2/m5", 3))
        self.assertNotEqual(a, draw(OTHER, "raf/test/p2/m5", 3))
        self.assertNotEqual(a, draw(SEED, "raf/curve/p2/m5", 3))
        self.assertNotEqual(a, draw(SEED, "raf/test/p2/m5", 4))
        digest = hashlib.sha256(bytes.fromhex(SEED) + b"|raf/test/p2/m5|3").digest()
        g = np.random.Generator(np.random.PCG64(int.from_bytes(digest, "big")))
        self.assertEqual(R.generator(SEED, "raf/test/p2/m5", 3).integers(0, 2 ** 62, size=4).tolist(),
                         g.integers(0, 2 ** 62, size=4).tolist())

    def test_pooled_and_serial_runs_give_the_same_results(self):
        jobs = [(SEED, "curve", "p2", 0.01, M, i) for M in (5, 6, 7) for i in range(6)]
        jobs += [(OTHER, "control", "half", 0.5 / (2 * R.ligation_count(6)), 6, i) for i in range(4)]
        with open(os.devnull, "w") as quiet, contextlib.redirect_stderr(quiet):
            pooled = R.run_all(jobs)
        serial = [R.run_instance(j) for j in reversed(jobs)][::-1]
        self.assertEqual(pooled, serial)
        self.assertGreater(len(set(pooled)), 10)


# ---------------------------------------------------------------- CatReNet's format, and the inputs

class Inputs(unittest.TestCase):
    def test_the_format_the_examples_use(self):
        food, reactions = R.parse_crs("# made up\nFoods: a, b  c\n\nx1 : a+b [c, d|e] -> f\n"
                                      "x2 : 0 + 10 [01100] => 100\nx3:f [a]<=>g + h\nx4 : g [b] <-> a\n")
        self.assertEqual(food, ["a", "b", "c"])
        self.assertEqual(reactions, [("x1", ["a", "b"], ["c", "d", "e"], ["f"], False),
                                     ("x2", ["0", "10"], ["01100"], ["100"], False),
                                     ("x3", ["f"], ["a"], ["g", "h"], True),
                                     ("x4", ["g"], ["b"], ["a"], True)])
        S, catalysis, owner, molecules = R.crs_system(food, reactions)
        self.assertEqual(owner, ["x1", "x2", "x3", "x3", "x4", "x4"])
        self.assertEqual(S.reactions, 6)
        _, rows = as_sets(S, catalysis)
        name = lambda ks: {molecules[k] for k in ks}   # noqa: E731
        self.assertEqual([(name(a), name(b)) for a, b, _ in rows[2:4]], [({"f"}, {"g", "h"}), ({"g", "h"}, {"f"})])
        self.assertEqual(name(rows[0][2]), {"c", "d", "e"})

    def test_what_the_check_does_not_read_is_refused(self):
        bad = {
            "inhibitor": "Food: a\nr1 : a [a] {b} => c\n",
            "and": "Food: a b\nr1 : a [a&b] => c\n",
            "star": "Food: a b\nr1 : a [a*b] => c\n",
            "reverse": "Food: a\nr1 : a [a] <= c\n",
            "reverse2": "Food: a\nr1 : a [a] <- c\n",
            "coefficient": "Food: a\nr1 : 2 a [a] => c\n",
            "no catalysts": "Food: a\nr1 : a => c\n",
            "empty catalysts": "Food: a\nr1 : a [] => c\n",
            "repeated name": "Food: a\nr1 : a [a] => c\nr1 : c [a] => d\n",
            "no food": "r1 : a [a] => c\n",
            "no reactions": "Food: a\n",
            "other line": "Food: a\nr1 : a [a] => c\nb c\n",
            "no products": "Food: a\nr1 : a [a] =>\n",
        }
        for what, text in bad.items():
            with self.assertRaises(ValueError, msg=what):
                R.parse_crs(text)

    def test_both_halves_of_a_two_way_reaction_must_agree(self):
        self.assertEqual(R.counted(np.array([True, True, False]), ["r1", "r1", "r2"]), ["r1"])
        with self.assertRaises(AssertionError):
            R.counted(np.array([True, False]), ["r1", "r1"])

    def test_other_bytes_are_refused(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "x.crs")
            data = b"Food: a\nr1 : a [a] => b\n"
            write(p, data)
            self.assertEqual(R.load(p, hashlib.sha256(data).hexdigest()), data.decode())
            with self.assertRaises(SystemExit):
                R.load(p, "0" * 64)
            with self.assertRaises(SystemExit):
                R.load(p, R.INPUTS[0][1])

    @unittest.skipUnless(examples_dir(), "CatReNet's examples are not at inputs/ and RAF_EXAMPLES is not set")
    def test_catrenet_examples_have_the_sizes_its_readme_states(self):
        ok, sizes, rows = R.validate(examples_dir())
        self.assertTrue(ok, sizes)
        self.assertEqual(sizes, "example-00:reactions=6,food=3,maxraf=3,maxcaf=0;"
                                "example-02:reactions=5,food=6,maxraf=5,maxcaf=3;"
                                "example-08:reactions=17,food=4,maxraf=17,maxcaf=17")
        self.assertEqual([r["maxraf"] for r in rows[:2]], [["r1", "r2", "r3"], ["r1", "r2", "r3", "r4", "r5"]])
        self.assertEqual(rows[1]["maxcaf"], ["r3", "r4", "r5"])
        self.assertEqual(rows[2]["two_way"], 17)


# ---------------------------------------------------------------- a whole run

class WholeRun(unittest.TestCase):
    def test_a_run_with_made_up_inputs_and_two_instances_a_setting(self):
        texts = [b"Food: a b\nr1 : a + b [c] => c\n",                     # an RAF, no CAF
                 b"Food: a b\nr1 : a + b [a] => c\nr2 : c [z] => d\n",    # RAF = CAF = {r1}
                 b"Food: a\nr1 : a [a] <=> b\n"]                          # one two-way reaction, both
        expected = [(1, 2, 1, 0), (2, 2, 1, 1), (1, 1, 1, 1)]
        saved = (R.INPUTS, R.INSTANCES, R.REQUIRED, os.environ.get("ECDYSIS_SEED"))
        here = os.getcwd()
        with tempfile.TemporaryDirectory() as d:
            os.mkdir(os.path.join(d, "inputs"))
            inputs = []
            for (name, _, _, words), data, want in zip(R.INPUTS, texts, expected):
                write(os.path.join(d, "inputs", name), data)
                inputs.append((name, hashlib.sha256(data).hexdigest(), want, words))
            R.INPUTS, R.INSTANCES, R.REQUIRED = tuple(inputs), 2, 2
            os.chdir(d)
            os.environ["ECDYSIS_SEED"] = "a" * 64
            try:
                with open(os.devnull, "w") as quiet, contextlib.redirect_stdout(quiet), contextlib.redirect_stderr(quiet):
                    R.main()
                with open(os.path.join("results", "outputs.json"), encoding="ascii") as f:
                    raw = f.read()
                with open(os.path.join("results", "detail.json"), encoding="ascii") as f:
                    full = json.load(f)
                again = R.run_instance(("a" * 64, "test", "p2", 0.01, 9, 1))
            finally:
                os.chdir(here)
                R.INPUTS, R.INSTANCES, R.REQUIRED = saved[:3]
                if saved[3] is None:
                    os.environ.pop("ECDYSIS_SEED", None)
                else:
                    os.environ["ECDYSIS_SEED"] = saved[3]
        out = json.loads(raw)
        self.assertTrue(raw.endswith("}\n"))
        self.assertEqual(list(out), sorted(out))
        self.assertEqual(set(out), set(R.OUTPUTS))
        self.assertEqual(len(out), 20)
        self.assertTrue(all(isinstance(v, (int, float)) or (isinstance(v, str) and len(v) <= 200) for v in out.values()))
        self.assertEqual((out["instances"], out["reactions_m15"], out["validation_ok"]), (2, 1703944, 1))
        self.assertEqual(out["validation_sizes"], "example-00:reactions=1,food=2,maxraf=1,maxcaf=0;"
                                                  "example-02:reactions=2,food=2,maxraf=1,maxcaf=1;"
                                                  "example-08:reactions=1,food=1,maxraf=1,maxcaf=1")
        settings = full["settings"]
        self.assertEqual(len(settings), 3 + 27 + 3)
        self.assertTrue(all(len(s["maxraf"]) == 2 and len(s["pairs"]) == 2 for s in settings))
        test = {s["p_label"]: s for s in settings if s["kind"] == "test"}
        self.assertEqual([out[f"raf_{k}_m{s['M']}"] for k, s in test.items()], [s["with_raf"] for s in test.values()])
        self.assertEqual(out["test_passed"], int(all(s["with_raf"] >= 2 for s in test.values())))
        control = [s for s in settings if s["kind"] == "control"]
        self.assertEqual([s["label"] for s in control], ["raf/control/half/m9", "raf/control/half/m12",
                                                          "raf/control/half/m15"])
        self.assertEqual(out["control_ok"], int(all(s["with_raf"] < 2 for s in control)))
        self.assertEqual(out["curve_p4"], ",".join(f"{s['M']}:{s['with_raf']}" for s in settings
                                                   if s["kind"] == "curve" and s["p_label"] == "p4"))
        self.assertEqual(out["curve_p4"].count(","), 11)
        p2 = test["p2"]
        self.assertEqual((p2["pairs"][1], p2["maxraf"][1], p2["maxraf_molecules"][1], p2["maxcaf"][1]), again)
        self.assertEqual(out["catalysts_mean_p4_m15"], round(sum(test["p4"]["pairs"]) / (2 * 1703944), 6))
        self.assertTrue(5 < out["catalysts_mean_p4_m15"] < 8)   # P |X| = 6.5534
        self.assertEqual(full["validation"][2]["two_way"], 1)
        self.assertEqual(full["targets"]["p4"], {"P": "1/10000", "M": 15, "P_n": "212993/2500",
                                                 "P_n_below": "19661/500"})


if __name__ == "__main__":
    unittest.main()
