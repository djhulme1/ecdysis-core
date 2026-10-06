"""The Lenia check on made-up cases: the decoder, the kernel and growth functions, the convolution against a
direct sum, the order of the product in the potential, the count on a small made-up catalogue, the seeded
sample, the refusal of other bytes, failures caught on purpose-built cases, pooled and serial runs bit for
bit, and a whole run on a made-up catalogue. With the real catalogue (put it at
inputs/lenia_animals_2020.json or name it in LENIA_CATALOGUE), also the counts and Orbium unicaudatus.

Run with: python3 -m unittest discover -s tests
"""

import os

for _var in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
    os.environ.setdefault(_var, "1")   # as lenia/check.py does: no BLAS threads in a process that forks

import contextlib  # noqa: E402
import hashlib  # noqa: E402
import importlib.util  # noqa: E402
import json  # noqa: E402
import sys  # noqa: E402
import tempfile  # noqa: E402
import unittest  # noqa: E402
import warnings  # noqa: E402

import numpy as np  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
# Loaded under its own name, since tests/test_check.py has already imported mm/check.py as "check"; registered
# in sys.modules so that the worker pool can name its functions.
_spec = importlib.util.spec_from_file_location("lenia_check", os.path.join(HERE, "..", "lenia", "check.py"))
L = importlib.util.module_from_spec(_spec)
sys.modules["lenia_check"] = L
_spec.loader.exec_module(L)


def write(path, data):
    with open(path, "wb") as f:
        f.write(data)

SEED = "0" * 64
OTHER = "f" * 64


def catalogue_path():
    path = os.environ.get("LENIA_CATALOGUE") or os.path.join(HERE, "..", "inputs", L.INPUT[0])
    return path if os.path.isfile(path) else None


def header(level, name):
    return {"code": f">{level}", "name": name, "cname": ""}


def pattern(code, name, cells="2o$2o!", **params):
    p = {"R": 3, "T": 4, "b": "1", "m": 0.15, "s": 0.015, "kn": 1, "gn": 1}
    p.update(params)
    return {"code": code, "name": name, "cname": "", "params": p, "cells": cells}


class Decoder(unittest.TestCase):
    def test_counts_values_rows_and_padding(self):
        A = L.decode("3.2o$A2pAyO$.b!")
        self.assertEqual(A.shape, (3, 5))
        np.testing.assert_array_equal(A, np.array([[0, 0, 0, 255, 255], [1, 25, 25, 255, 0], [0, 0, 0, 0, 0]]) / 255)

    def test_two_character_values(self):
        self.assertEqual(L.ch2val("pA"), 25)
        self.assertEqual(L.ch2val("pX"), 48)
        self.assertEqual(L.ch2val("qA"), 49)
        self.assertEqual(L.ch2val("yO"), 255)
        self.assertEqual(L.ch2val("o"), 255)
        self.assertEqual(L.ch2val("X"), 24)

    def test_a_count_before_a_dollar_adds_empty_rows(self):
        A = L.decode("o3$2o!")
        np.testing.assert_array_equal(A, [[1, 0], [0, 0], [0, 0], [1, 1]])

    def test_a_trailing_dollar_adds_a_zero_row_as_leniand_does(self):
        self.assertEqual(L.decode("o$o$!").shape, (3, 1))
        self.assertEqual(L.decode("o$o!").shape, (2, 1))

    def test_other_dimensions_strange_tokens_and_no_mass_are_refused(self):
        for bad in ("2o%2o!", "o#o!", "o@Ao!", "o!o!", "pq!", "p$o!", "Y!", "3.$b!", "$!", 7):
            with self.assertRaises(ValueError, msg=bad):
                L.decode(bad)


class Rule(unittest.TestCase):
    def test_the_exponential_core_is_0_at_0_and_1_at_one_half_without_warnings(self):
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            with np.errstate(all="raise", under="ignore"):
                v = L.core_exponential(np.array([0.0, 0.5, 1.0, 1e-300, 0.25]))
        self.assertEqual(v[0], 0.0)
        self.assertEqual(v[1], 1.0)
        self.assertEqual(v[2], 0.0)
        self.assertEqual(v[3], 0.0)
        self.assertAlmostEqual(v[4], np.exp(4 - 1 / 0.1875), places=15)
        self.assertFalse(np.isnan(v).any())

    def test_every_growth_is_1_at_mu_and_minus_1_far_away(self):
        for name, g in L.GROWTHS.items():
            self.assertEqual(float(g(np.array([0.3]), 0.3, 0.02)[0]), 1.0, name)
            self.assertEqual(float(g(np.array([0.9]), 0.3, 0.02)[0]), -1.0, name)

    def test_each_kernel_sums_to_1_and_has_the_rings_beta_implies(self):
        N, R, beta = 64, 12, [1.0, 0.5, 0.25]
        c = N // 2
        for core in L.CORES:
            K = L.kernel(N, R, beta, core)
            self.assertAlmostEqual(K.sum(), 1.0, places=12, msg=core)
            self.assertTrue((K >= 0).all())
            np.testing.assert_array_equal(K, K.T)
            # The rings' middles (D = 1/6, 1/2, 5/6: 2, 6, 10 cells out) stand in the ratios of beta.
            mids = [K[c, c + d] for d in (2, 6, 10)]
            self.assertAlmostEqual(mids[1] / mids[0], 0.5, places=9, msg=core)
            self.assertAlmostEqual(mids[2] / mids[0], 0.25, places=9, msg=core)
            # Nothing at or beyond D = 1.
            yy, xx = np.mgrid[0:N, 0:N]
            self.assertEqual(K[(yy - c) ** 2 + (xx - c) ** 2 >= R * R].max(), 0.0)
        K = L.kernel(N, R, beta, "exponential")
        self.assertLess(max(K[c, c + d] for d in (0, 4, 8)), 1e-12 * K.max())   # the rings' edges

    def test_the_fft_convolution_equals_a_direct_periodic_sum(self):
        N, R = 32, 5
        A = np.random.default_rng(1).random((N, N))
        K = L.kernel(N, R, [1.0, 1 / 3], "exponential")
        U = L.potential(L.kernel_fft(N, R, [1.0, 1 / 3], "exponential"), A)
        direct = np.zeros((N, N))
        c = N // 2
        for a in range(-R, R + 1):
            for b in range(-R, R + 1):
                direct += K[c + a, c + b] * np.roll(A, (a, b), axis=(0, 1))   # A[x - a, y - b]
        self.assertLess(np.abs(U - direct).max(), 1e-12)

    def test_the_product_is_taken_kernel_first_whatever_the_interpreter_elides(self):
        # numpy's complex multiply fuses one of its products, so K F and F K can differ in the last bit of the
        # imaginary part; and numpy's temporary elision rewrites `Khat * np.fft.fft2(A)` as `F *= Khat` for
        # arrays of 256 KiB or more under some interpreters (Python 3.12, as in the pinned image). The potential
        # must be K F from a named F, as LeniaND's calc_once computes it, on every interpreter.
        rng = np.random.default_rng(2)
        for N in (128, 256):
            A = rng.random((N, N))
            Khat = L.kernel_fft(N, 13, [1.0, 0.5], "exponential")
            F = np.fft.fft2(A)
            np.testing.assert_array_equal(L.potential(Khat, A), np.real(np.fft.ifft2(np.multiply(Khat, F))))

    def test_the_potential_does_not_depend_on_where_the_world_sits_in_memory(self):
        N = 128
        A = np.random.default_rng(3).random((N, N))
        Khat = L.kernel_fft(N, 13, [1.0], "polynomial")
        want = L.potential(Khat, A)
        for offset in (8, 16, 24, 32, 40, 48, 56):
            buf = np.zeros(A.nbytes + 128, dtype=np.uint8)
            start = (-buf.ctypes.data) % 64 + offset
            B = buf[start:start + A.nbytes].view(np.float64).reshape(N, N)
            B[...] = A
            self.assertEqual(B.ctypes.data % 64, offset)
            np.testing.assert_array_equal(L.potential(Khat, B), want, err_msg=f"offset {offset}")

    def test_the_variants_map_kn_and_gn_as_leniand_does(self):
        self.assertEqual(L.functions(1, 1, 0.15, "code"), ("polynomial", "polynomial", 0.15))
        self.assertEqual(L.functions(2, 2, 0.15, "code"), ("exponential", "exponential", 0.15))
        self.assertEqual(L.functions(3, 3, 0.15, "code"), ("step", "step", 0.15))
        self.assertEqual(L.functions(4, 3, 0.15, "code"), ("staircase", "step", 0.15))
        self.assertEqual(L.functions(3, 1, 0.15, "paper"), ("exponential", "exponential", 0.15))
        self.assertEqual(L.functions(1, 1, 0.15, "control"), ("exponential", "exponential", 0.3))

    def test_the_world_is_a_power_of_two_large_enough(self):
        self.assertEqual(L.world_size(20, 20, 13), 128)
        self.assertEqual(L.world_size(43, 10, 13), 256)
        self.assertEqual(L.world_size(10, 10, 22), 256)
        self.assertEqual(L.world_size(227, 230, 13), 1024)


class Fates(unittest.TestCase):
    def test_evaporation_is_caught_and_stops_the_run(self):
        # mu far above any potential: growth is -1 everywhere and each step removes 1/4 of a cell's value.
        fate, steps, t, mass, low, high, N, m0 = L.simulate("3o$3o$3o!", {"R": 3, "T": 4, "b": "1", "m": 0.9, "s": 0.01, "kn": 2, "gn": 2}, "paper")
        self.assertEqual((fate, steps, t, mass, N, m0), ("evaporated", 4, 1.0, 0.0, 128, 9.0))

    def test_explosion_is_caught_and_stops_the_run(self):
        # The step growth with |u - mu| <= s everywhere grows every cell by 1/4 a step: half full after 2.
        fate, steps, t, mass, low, high, N, m0 = L.simulate("3o$3o$3o!", {"R": 3, "T": 4, "b": "1", "m": 0.5, "s": 1.0, "kn": 3, "gn": 3}, "code")
        self.assertEqual((fate, steps, t, N), ("exploded", 2, 0.5, 128))
        self.assertAlmostEqual(mass * m0, 0.5 * (128 * 128 - 9) + 9, places=9)

    def test_a_pattern_that_neither_dies_nor_fills_persists_to_t_30(self):
        # R = 1 and the staircase core leave only the centre in the kernel (U = A); the step growth around
        # mu = 1 then keeps every 1 at 1 and every 0 at 0.
        fate, steps, t, mass, low, high, N, m0 = L.simulate("o!", {"R": 1, "T": 1, "b": "1", "m": 1.0, "s": 0.5, "kn": 4, "gn": 3}, "code")
        self.assertEqual((fate, steps, t, mass, low, high, m0), ("persists", L.HORIZON, float(L.HORIZON), 1.0, 1.0, 1.0, 1.0))


def random_cells(rng, h, w):
    """A made-up pattern in LeniaND's run-length code: h rows of w values, a third of them empty."""
    tokens = ["."] * 12 + list(L.LETTERS) + ["pA", "qK", "tX", "yO", "o"]
    return "$".join("".join(tokens[k] for k in rng.integers(0, len(tokens), w)) for _ in range(h)) + "!"


class Repeatability(unittest.TestCase):
    def test_pooled_and_serial_runs_give_the_same_bits_in_any_order(self):
        # Made-up patterns that change shape, under every variant and all four cores; the pool hands them to two
        # processes in an order of its own, and the serial runs go backwards, in this process.
        rng = np.random.default_rng(4)
        jobs = []
        for k, (kn, gn) in enumerate(((1, 1), (2, 2), (3, 3), (4, 1))):
            params = {"R": 10, "T": 10, "b": "1,1/2" if k % 2 else "1", "m": 0.15 + 0.05 * k, "s": 0.02 + 0.01 * k,
                      "kn": kn, "gn": gn}
            cells = random_cells(rng, 20, 24)
            jobs += [(cells, params, v) for v in L.VARIANTS]
        saved = L.HORIZON
        L.HORIZON = 3
        try:
            with open(os.devnull, "w") as quiet, contextlib.redirect_stderr(quiet):
                pooled = L.run_all(jobs)
            serial = [L.run_one(j) for j in reversed(jobs)][::-1]
            again = [L.run_one(j) for j in jobs]
        finally:
            L.HORIZON = saved
        self.assertEqual([repr(r) for r in pooled], [repr(r) for r in serial])
        self.assertEqual([repr(r) for r in serial], [repr(r) for r in again])
        self.assertGreater(len({r[3] for r in pooled}), 6)   # the runs differ from each other


class Catalogue(unittest.TestCase):
    def test_the_count_keeps_families_only_and_counts_names_once(self):
        entries = [
            header(1, "class: A"), header(2, "order: X"), header(3, "family: F One"), header(4, "subfamily: s"),
            pattern("a1", "Alpha unus"), pattern("a2", "Alpha unus"), pattern("b", "Beta duo tres"),
            header(4, "(step function only)"), pattern("b2", "Beta duo quattuor"),
            header(3, "(compilation)"), pattern("c", "Compilatum"),
            header(3, "family: G Two"), pattern("d", "Delta"),
            header(2, "order: Y"), pattern("e", "Orphanum"),
            header(1, "SmoothLife"), pattern("s", "Bug"),
            header(1, "class: B"), header(2, "order: Z"), header(3, "family: F One"), pattern("a1", "Alpha unus"),
        ]
        counts, species = L.census(entries)
        self.assertEqual(counts, {"catalogue_entries": 21, "families": 2, "family_entries": 6, "species": 4,
                                  "species_codes": 5, "species_binomials": 3})
        self.assertEqual(species, [4, 6, 8, 12])

    def test_a_header_with_another_code_is_refused(self):
        with self.assertRaises(ValueError):
            L.census([{"code": ">5", "name": "x"}])

    def test_the_sample_is_fixed_by_the_seed_distinct_and_differs_between_seeds(self):
        a, b, c = L.draw(433, SEED), L.draw(433, SEED), L.draw(433, OTHER)
        self.assertEqual(a, b)
        self.assertEqual(len(set(a)), 40)
        self.assertEqual(a, sorted(a))
        self.assertTrue(all(0 <= x < 433 for x in a))
        self.assertNotEqual(a, c)
        self.assertEqual(L.draw(40, SEED), list(range(40)))

    def test_other_bytes_are_refused(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "c.json")
            data = json.dumps([header(1, "class: A")]).encode("utf-8")
            write(p, data)
            self.assertEqual(L.load(p, hashlib.sha256(data).hexdigest())[0]["code"], ">1")
            with self.assertRaises(SystemExit):
                L.load(p, "0" * 64)

    def test_long_lists_are_cut_to_whole_items(self):
        items = [f"code{i}:evaporated@1.{i % 10}" for i in range(40)]
        text = L.bounded(items)
        self.assertLessEqual(len(text), 200)
        self.assertTrue(text.endswith(" more"))
        kept = text.split(";")[:-1]
        self.assertEqual(kept, items[:len(kept)])
        self.assertEqual(text.split(";")[-1], f"+{40 - len(kept)} more")
        self.assertEqual(L.bounded(items[:3]), ";".join(items[:3]))
        self.assertEqual(L.bounded([]), "")


class WholeRun(unittest.TestCase):
    def test_a_run_on_a_made_up_catalogue(self):
        # 42 species in 18 families, each a 3 x 3 block: a third with mu = 0.9, which no potential reaches, so
        # that they evaporate at the fourth step (t = 1); the rest with mu = 0.3, which keeps 95% of the mass to
        # t = 1. The control's doubled mu leaves at most 3%. The run is cut to t = 1 so that it is quick, and goes
        # through the worker pool.
        entries, doomed = [header(1, "class: A"), header(2, "order: X")], set()
        for f in range(18):
            entries.append(header(3, f"family: F{f}"))
            for k in range(3 if f < 6 else 2):
                m = 0.9 if (f + k) % 3 == 0 else 0.3
                if m == 0.9:
                    doomed.add(len(entries))
                entries.append(pattern(f"{f}x{k}", f"Genus{f} species{k}", "3o$3o$3o!", m=m, s=0.05, kn=2, gn=2))
        data = json.dumps(entries).encode("utf-8")
        _, species = L.census(entries)
        sampled = [species[j] for j in L.draw(42, "a" * 64)]
        saved = (L.INPUT, L.HORIZON, os.environ.get("ECDYSIS_SEED"))
        here = os.getcwd()
        with tempfile.TemporaryDirectory() as d:
            os.mkdir(os.path.join(d, "inputs"))
            write(os.path.join(d, "inputs", L.INPUT[0]), data)
            L.INPUT, L.HORIZON = (L.INPUT[0], hashlib.sha256(data).hexdigest()), 1
            os.chdir(d)
            os.environ["ECDYSIS_SEED"] = "a" * 64
            try:
                with open(os.devnull, "w") as quiet, contextlib.redirect_stdout(quiet), contextlib.redirect_stderr(quiet):
                    L.main()
                survivor = next(i for i in species if i not in doomed)
                expected = L.simulate(entries[survivor]["cells"], entries[survivor]["params"], "paper")
                with open(os.path.join("results", "outputs.json"), encoding="ascii") as f:
                    raw = f.read()
                with open(os.path.join("results", "census.json"), encoding="ascii") as f:
                    full = json.load(f)
            finally:
                os.chdir(here)
                L.INPUT, L.HORIZON = saved[:2]
                if saved[2] is None:
                    os.environ.pop("ECDYSIS_SEED", None)
                else:
                    os.environ["ECDYSIS_SEED"] = saved[2]
        out = json.loads(raw)
        self.assertTrue(raw.endswith("}\n"))
        self.assertEqual(list(out), sorted(out))
        self.assertEqual(set(out), set(L.OUTPUTS))
        self.assertEqual(len(out), 20)
        self.assertTrue(all(isinstance(v, int) or (isinstance(v, str) and len(v) <= 200) for v in out.values()))
        self.assertEqual((out["families"], out["species"], out["sample_size"]), (18, 42, 40))
        self.assertEqual(out["sample_indices"], ",".join(str(i) for i in sampled))
        lost = [i for i in sampled if i in doomed]
        self.assertEqual((out["sample_failures"], out["sample_evaporated"], out["sample_exploded"]), (len(lost), len(lost), 0))
        listed = [f"{entries[i]['code']}:evaporated@1.0" for i in lost]
        self.assertGreater(len(";".join(listed)), 200)   # so outputs.json carries it cut, census.json in full
        self.assertEqual(out["sample_failed"], L.bounded(listed))
        self.assertEqual(full["values"]["sample_failed"], ";".join(listed))
        self.assertEqual((out["census_paper_failures"], out["census_code_failures"]), (len(doomed), len(doomed)))
        self.assertEqual((out["control_failures"], out["control_ok"]), (40, 1))
        self.assertEqual(out["steps_simulated"], (42 * 2 + 40) * 4)
        self.assertEqual(out["test_passed"], 0)   # 42 species: not more than 400
        v = full["values"]
        self.assertEqual(v["census_species"], 42)
        self.assertEqual(v["sample_codes"], ",".join(entries[i]["code"] for i in sampled))
        self.assertEqual([(r["index"], r["code"]) for r in full["species"]], [(i, entries[i]["code"]) for i in species])
        self.assertEqual(sum(1 for r in full["species"] if r["sampled"]), 40)
        for r in full["species"]:
            self.assertEqual(set(r["fates"]), {"paper", "code", "control"} if r["sampled"] else {"paper", "code"})
            self.assertEqual(r["fates"]["paper"]["fate"], "evaporated" if r["index"] in doomed else "persists")
            self.assertEqual((r["N"], r["m0"]), (128, 9.0))
            for f in r["fates"].values():
                self.assertEqual((f["steps"], f["t"]), (4, 1.0))
                self.assertTrue(0 <= f["low"] <= f["mass"] <= f["high"])
        # census.json keeps the mass ratios in full: each reads back as the very double the simulation returned.
        row = next(r for r in full["species"] if r["index"] == survivor)
        self.assertEqual([row["fates"]["paper"][k] for k in ("mass", "low", "high")], [float(x) for x in expected[3:6]])
        self.assertNotEqual(round(expected[3], 4), expected[3])


@unittest.skipUnless(catalogue_path(), "the catalogue is not at inputs/ and LENIA_CATALOGUE is not set")
class RealCatalogue(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.entries = L.load(catalogue_path(), L.INPUT[1])

    def test_the_counts(self):
        counts, species = L.census(self.entries)
        self.assertEqual(counts, {"catalogue_entries": 612, "families": 18, "family_entries": 526, "species": 433,
                                  "species_codes": 436, "species_binomials": 361})
        self.assertEqual(len(species), 433)

    def test_orbium_lives_under_its_own_and_the_papers_functions_and_dies_under_the_control(self):
        e = next(e for e in self.entries if e.get("name") == "Orbium unicaudatus")
        self.assertEqual((e["code"], e["params"]["kn"], e["params"]["gn"]), ("O2u", 1, 1))
        for variant in ("paper", "code"):
            fate, steps, t, mass, *_ = L.simulate(e["cells"], e["params"], variant)
            self.assertEqual((fate, steps), ("persists", 300), variant)
            self.assertTrue(0.5 < mass < 2, variant)
        self.assertNotEqual(L.simulate(e["cells"], e["params"], "control")[0], "persists")


if __name__ == "__main__":
    unittest.main()
