"""The BBP check against known digits of pi, against itself, and against a wrong identity.

Run with: python3 -m unittest discover -s tests
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "pi"))
import bbp  # noqa: E402

# pi in hexadecimal, the first 48 digits after the point (any reference table).
PI_HEX = "243f6a8885a308d313198a2e03707344a4093822299f31d0"


def square_and_multiply_count(e):
    """Multiplications done by left-to-right binary exponentiation, counted by running it."""
    if e == 0:
        return 0
    count, acc = 0, 16
    for bit in bin(e)[3:]:
        acc = acc * acc
        count += 1
        if bit == "1":
            acc = acc * 16
            count += 1
    return count


class Digits(unittest.TestCase):
    def test_the_independent_pi_matches_the_known_expansion(self):
        bits = 4 * 48 + 64
        pi = bbp.chudnovsky_fixed(bits)
        self.assertEqual(pi >> bits, 3)
        self.assertEqual(bbp.exact_digits(pi, bits, 0, 48), PI_HEX)

    def test_the_paper_algorithm_gives_the_known_digits(self):
        for d in (0, 1, 7, 20, 40):
            self.assertEqual(bbp.bbp_digits(d), PI_HEX[d:d + bbp.DIGITS], d)

    def test_the_algorithm_agrees_with_the_independent_pi_far_out(self):
        bits = 4 * (5000 + bbp.DIGITS) + 64
        pi = bbp.chudnovsky_fixed(bits)
        for d in (999, 2024, 4999):
            self.assertEqual(bbp.bbp_digits(d), bbp.exact_digits(pi, bits, d), d)

    def test_a_wrong_identity_is_caught(self):
        wrong = [bbp.bbp_digits(d, wrong=True) for d in (0, 100, 1000)]
        right = [PI_HEX[0:6], None, None]
        self.assertNotEqual(wrong[0], right[0])
        bits = 4 * (1000 + bbp.DIGITS) + 64
        pi = bbp.chudnovsky_fixed(bits)
        self.assertNotEqual(wrong[2], bbp.exact_digits(pi, bits, 1000))

    def test_the_cost_formula_counts_what_square_and_multiply_does(self):
        for d in (1, 2, 3, 17, 64, 1000):
            counted = 4 * sum(square_and_multiply_count(e) for e in range(1, d + 1))
            self.assertEqual(bbp.multiplications(d), counted, d)

    def test_positions_come_from_the_seed(self):
        a = bbp.Stream("0" * 64, "bbp/positions")
        b = bbp.Stream("0" * 64, "bbp/positions")
        c = bbp.Stream("f" * 64, "bbp/positions")
        xs = [a.below(1000) for _ in range(5)]
        self.assertEqual(xs, [b.below(1000) for _ in range(5)])
        self.assertNotEqual(xs, [c.below(1000) for _ in range(5)])


if __name__ == "__main__":
    unittest.main()
