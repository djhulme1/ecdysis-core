"""Ahmed, Kullmann & Snevily's certificates (vdw/aks.py): the paper's word notation and its refusals; the progression
check against a direct loop; palindromes expanded from the half the paper prints (its own example among them);
exhaustive van der Waerden numbers w(2;3,3) = 9 and w(2;3,4) = 18; the planted progression; the reading of
certificates, tables and the palindromic table from synthetic TeX, including a table whose caption carries digits; the
conjecture's checks and the Ansatz; and, with the e-print at inputs/ (or AKS_INPUTS), the whole run, which must not
depend on the seed beyond the controls' detail.

Run with: python3 -m unittest tests.test_aks
"""

import gzip
import importlib.util
import os
import random
import shutil
import sys
import tempfile
import unittest
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("vdw_aks", os.path.join(HERE, "..", "vdw", "aks.py"))
M = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = M
_spec.loader.exec_module(M)

INPUTS = os.environ.get("AKS_INPUTS") or os.path.join(HERE, "..", "inputs")
HAVE = os.path.isfile(os.path.join(INPUTS, M.EPRINT[0]))
SEED = "0" * 63 + "1"


class Notation(unittest.TestCase):
    def test_powers_layout_and_full_stop(self):
        self.assertEqual(M.word("$1^{3}01$"), "11101")
        self.assertEqual(M.word("$$0^{2}1^{10}$$"), "00" + "1" * 10)
        self.assertEqual(M.word("\\begin{gather*}01\\\\\n 1^{2}0.\\end{gather*}"), "01110")

    def test_refusals(self):
        for bad in ("", "$$", "1^{3}2", "0^3", "01x", "\\textbf{01}"):
            with self.subTest(bad=bad), self.assertRaises(M.Refused):
                M.word(bad)


class Progressions(unittest.TestCase):
    def test_small_sets(self):
        self.assertTrue(M.has_progression([1, 3, 5], 3, 5))
        self.assertFalse(M.has_progression([1, 2, 4], 3, 4))
        self.assertTrue(M.has_progression([2, 5, 8, 11], 4, 11))
        self.assertFalse(M.has_progression([2, 5, 8, 12], 4, 12))

    def test_fast_check_agrees_with_a_direct_loop(self):
        rng = random.Random(7)
        for _ in range(400):
            n, t = rng.randint(1, 40), rng.randint(3, 6)
            w = "".join(rng.choice("0111") for _ in range(n))
            with self.subTest(w=w, t=t):
                self.assertEqual(M.is_good(w, t), M.is_good_naive(w, t))

    def test_exhaustive_known_values(self):
        self.assertEqual(M.vdw_exhaustive(3), 9)
        self.assertEqual(M.vdw_exhaustive(4), 18)

    def test_planted_progression_is_caught(self):
        good = "11001100"                       # good w.r.t. (3, 3): the 1s 1, 2, 5, 6 and the 0s 3, 4, 7, 8
        self.assertTrue(M.is_good(good, 3))
        bad, at = M.plant_three_ap(good, M.Stream(SEED, "test"))
        self.assertEqual(good[at - 1], "1")
        self.assertEqual(bad[at - 1], "0")
        self.assertFalse(M.is_good(bad, 3))


class Palindromes(unittest.TestCase):
    def test_the_papers_own_example(self):
        # "the good palindromic partition 01^2001^20 for t=3 and n=8 is compressed to 01^20"
        full = M.palindrome_full(M.word("01^{2}0"), 8)
        self.assertEqual(full, M.word("01^{2}001^{2}0"))
        self.assertTrue(M.is_good(full, 3))

    def test_odd_and_wrong_lengths(self):
        self.assertEqual(M.palindrome_full("110", 5), "11011")
        self.assertIsNone(M.palindrome_full("110", 8))
        self.assertIsNone(M.palindrome_full("1100", 5))


DOC = r"""
\subsection{Conjectured precise lower bounds}
\label{sec:Certificates3tp}
\paragraph{$\vdw(2; 3, 4)\geq 18$}
{\scriptsize
$$1^{3}0^{2}1^{3}0$$
$$1^{3}0^{2}1^{3}.$$
}
\normalsize
\paragraph{$\vdw(2; 3, 5) \geq 22$}
$$01^{4}0.$$
\subsection{Further lower bounds}
\label{sec:Certificates3tf}
\paragraph{$\vdw(2; 3, 6) > 30$}
\begin{gather*}
1^{5}0\\
1^{5}0.
\end{gather*}
\subsection{Good palindromic partitions}
"""

TABLES = r"""
\begin{table}[H]
  \begin{tabular}{c|*{3}{c}}
    $t$ & 3 & 4 & \textbf{5}\\
    \hline
    $\vdw(2;3,t)$ & 9 & 18 & \textbf{22}
  \end{tabular}
  \caption{Known values for $\vdw(2;3,t)$ with 2;3 in it}
  \label{tab:a}
\end{table}
\begin{table}[H]
  \begin{tabular}{c|*{2}{c}}
    $t$ & 6 & 7\\
    \hline
    $\vdw(2;3,t) \geq$ & 32 & 4x6
  \end{tabular}
  \label{tab:b}
\end{table}
"""

PAL = r"""
\label{tab-pal}\\
  \hline \hline
 $t$ & $\vdwpd(2;3,t)-1$ &{\tt Good palindromic partitions}\\
  \hline
\endhead
\endlastfoot
$3$ & $(5,8)$ & $1^{2}0, \ 10^{2}1$\\
\hline
$4$ & $\geq 15$ & $1^{2}01$\\[-2ex]
&& $0^{2}1^{2}$\\
\hline
\end{longtable}
"""


class Reading(unittest.TestCase):
    def test_certificates(self):
        c = M.certificates(DOC)
        self.assertEqual(sorted(c), [4, 5, 6])
        self.assertEqual(c[4], (18, False, "11100111" + "0" + "11100111"))
        self.assertEqual(c[5], (22, False, "011110"))
        self.assertEqual(c[6], (30, True, "111110111110"))

    def test_a_strict_heading_among_the_exact_refuses(self):
        with self.assertRaises(M.Refused):
            M.certificates(DOC.replace("5) \\geq 22", "5) > 22"))

    def test_tables_stop_at_the_end_of_the_tabular(self):
        self.assertEqual(M.table_bounds(TABLES, "tab:a"), {3: 9, 4: 18, 5: 22})
        with self.assertRaises(M.Refused):
            M.table_bounds(TABLES, "tab:b")            # "4x6" is not a number
        with self.assertRaises(M.Refused):
            M.table_bounds(TABLES + "\\label{tab:a}", "tab:a")

    def test_palindromic_table_with_a_continuation(self):
        self.assertEqual(M.palindromic(PAL), [(3, 5, "110"), (3, 8, "1001"), (4, 15, "1101" + "0011")])


class Conjecture(unittest.TestCase):
    def test_ansatz_and_its_printed_closed_form(self):
        d = Fraction(77, 23)
        rows = {r["t"]: r for r in M.ansatz(d)}
        self.assertEqual(rows[3]["w_t"], 9)
        self.assertEqual(rows[4]["w_t"], 9 + 3 * d)
        self.assertEqual(rows[4]["closed"], 9)          # the printed form is the sum to t - 2
        self.assertTrue(all(r["gap"] == d * (t - 1) and r["below"] for t, r in rows.items()))

    def test_d_and_the_bound(self):
        known = {t: 9 + 3 * (t - 3) for t in range(3, 20)}
        exact = {t: 60 + 3 * (t - 20) for t in range(20, 31)}
        further = {t: 100 + 3 * (t - 31) for t in range(31, 40)}
        exact[24] += 40                                 # the largest step, at t = 24
        r = M.conjecture(known, exact, further)
        self.assertEqual((r["within"], r["total"]), (37, 37))
        self.assertEqual(r["d_at"], [24])
        self.assertEqual(r["d"], Fraction(exact[24] - exact[23], 23))
        with self.assertRaises(M.Refused):
            M.conjecture(known, {}, further)


class Run(unittest.TestCase):
    def test_refuses_a_bad_seed(self):
        with self.assertRaises(M.Refused):
            M.run("xyz", inputs=HERE, results=os.path.join(HERE, "_never"))


@unittest.skipUnless(HAVE, "the e-print is not at inputs/")
class EPrint(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_the_whole_run(self):
        out, detail = M.run(SEED, inputs=INPUTS, results=os.path.join(self.tmp, "r1"))
        self.assertEqual(out["test_passed"], 1)
        self.assertEqual(out["margins"], "16 30 50 40 42 26 2")
        self.assertEqual((out["lengths_match"], out["good"], out["refuting"]), (20, 20, 7))
        self.assertEqual(out["tables_match"], "11 of 11; 9 of 9")
        self.assertEqual(out["palindromic_good"], 74)
        self.assertEqual(out["d"], "77/23 at t = 24")
        self.assertEqual(out["controls_passed"], out["controls_total"])
        other, _ = M.run("f" * 64, inputs=INPUTS, results=os.path.join(self.tmp, "r2"))
        self.assertEqual(out, other)

    def test_a_changed_eprint_refuses(self):
        with open(os.path.join(INPUTS, M.EPRINT[0]), "rb") as fh:
            data = bytearray(fh.read())
        data[-1] ^= 1
        os.makedirs(os.path.join(self.tmp, "in"))
        with open(os.path.join(self.tmp, "in", M.EPRINT[0]), "wb") as fh:
            fh.write(bytes(data))
        with self.assertRaises(M.Refused):
            M.run(SEED, inputs=os.path.join(self.tmp, "in"), results=os.path.join(self.tmp, "r"))

    def test_the_text_is_one_tex_file(self):
        tex = M.load(INPUTS)
        self.assertIn("\\label{sec:Certificates3tp}", tex)
        with open(os.path.join(INPUTS, M.EPRINT[0]), "rb") as fh:
            self.assertEqual(gzip.decompress(fh.read()).decode("utf-8"), tex)


if __name__ == "__main__":
    unittest.main()
