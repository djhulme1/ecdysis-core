#!/usr/bin/env python3
"""Hexadecimal digits of pi by Bailey-Borwein-Plouffe digit extraction, for an Ecdysis receipt.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test is from Bailey, Borwein and
Plouffe, "On the rapid computation of various polylogarithmic constants", Mathematics of
Computation 66 (1997): the digit-extraction algorithms "can be easily implemented (multiple
precision arithmetic is not needed), require virtually no memory, and feature run times that scale
nearly linearly with the order of the digit desired".

What runs, standard library only:

1. The paper's algorithm for pi in base 16, from its identity
       pi = sum_k 16^-k (4/(8k+1) - 2/(8k+4) - 1/(8k+5) - 1/(8k+6)).
   For a position d, each series S_j = sum_k 16^(d-k)/(8k+j) is taken modulo 1: the terms with
   k <= d as (16^(d-k) mod (8k+j)) / (8k+j), by modular exponentiation on integers below 2^26, and
   the tail k > d directly; every fraction is an ordinary double. Then frac(4 S1 - 2 S4 - S5 - S6)
   holds the hexadecimal digits of pi from position d+1 on (position 1 is the first after the point).
2. An independent computation: floor(pi * 2^B) by the Chudnovsky series with binary splitting in
   exact integer arithmetic, from which the same digits are read off.
3. The comparison, at positions drawn from ECDYSIS_SEED, and at position 0.
4. A control: the same algorithm on a wrong identity (1/(8k+7) for 1/(8k+6)) must disagree.
5. The cost: the number of modular multiplications that square-and-multiply exponentiation performs
   for position d, (bit length of e) - 1 squarings plus (ones in e) - 1 multiplications for each
   exponent e = d - k of each of the four series, divided by d log2 d, at d = 2^12, 2^16 and 2^20.
   If the cost grew faster than d log d this ratio would grow with d.

Writes results/outputs.json. All randomness comes from ECDYSIS_SEED through SHA-256 in counter mode,
as in mm/check.py; nothing reads the clock.
"""

import hashlib
import json
import math
import os
import re
import sys

MAX_POSITION = 1 << 17   # positions drawn below this; pi is computed independently to past it
DIGITS = 6               # hexadecimal digits compared at each position (double precision gives ~9)
POSITIONS = 8            # positions drawn from the seed


# ---------------------------------------------------------------- the seed (as mm/check.py)

class Stream:
    def __init__(self, seed_hex, label):
        self.seed = bytes.fromhex(seed_hex)
        self.label = label.encode("ascii")
        self.counter = 0
        self.buf = b""

    def u64(self):
        if len(self.buf) < 8:
            self.buf += hashlib.sha256(self.seed + b"|" + self.label + b"|" + str(self.counter).encode("ascii")).digest()
            self.counter += 1
        x, self.buf = int.from_bytes(self.buf[:8], "big"), self.buf[8:]
        return x

    def below(self, n):
        limit = (1 << 64) - ((1 << 64) % n)
        while True:
            x = self.u64()
            if x < limit:
                return x % n


# ---------------------------------------------------------------- the paper's algorithm

def series(j, d, last=6):
    """frac(sum_{k>=0} 16^(d-k) / (8k + j)) in double precision; `last` replaces 6 in the control."""
    s = 0.0
    for k in range(d + 1):
        a = 8 * k + j
        if a >= 1 << 26:
            raise ValueError("a modulus at or above 2^26: the products would leave 52-bit integers")
        s += pow(16, d - k, a) / a
        s -= math.floor(s)
    k = d + 1
    while True:
        a = 8 * k + j
        t = 16.0 ** (d - k) / a
        if t < 1e-17:
            break
        s += t
        s -= math.floor(s)
        k += 1
    return s


def bbp_digits(d, n=DIGITS, wrong=False):
    """Hexadecimal digits of pi at positions d+1 .. d+n by the paper's algorithm (or the control's)."""
    s6 = series(7, d) if wrong else series(6, d)
    x = 4 * series(1, d) - 2 * series(4, d) - series(5, d) - s6
    x -= math.floor(x)
    out = ""
    for _ in range(n):
        x *= 16
        digit = int(x)
        out += "0123456789abcdef"[digit]
        x -= digit
    return out


def multiplications(d):
    """Modular multiplications that square-and-multiply makes for position d, over the four series."""
    total = 0
    for e in range(1, d + 1):
        total += (e.bit_length() - 1) + (bin(e).count("1") - 1)
    return 4 * total


# ---------------------------------------------------------------- pi, independently

def chudnovsky_fixed(bits):
    """floor(pi * 2^bits), up to an error in the last few bits, by the Chudnovsky series."""
    C3_24 = 640320 ** 3 // 24

    def split(a, b):
        if b - a == 1:
            if a == 0:
                p = q = 1
            else:
                p = (6 * a - 5) * (2 * a - 1) * (6 * a - 1)
                q = a * a * a * C3_24
            t = p * (13591409 + 545140134 * a)
            return p, q, -t if a & 1 else t
        m = (a + b) // 2
        p1, q1, t1 = split(a, m)
        p2, q2, t2 = split(m, b)
        return p1 * p2, q1 * q2, q2 * t1 + p1 * t2

    terms = int(bits * math.log10(2) / 14.181647462725477) + 2   # each term gives ~14.18 decimal digits
    _, q, t = split(0, terms)
    root = math.isqrt(10005 << (2 * bits))                        # sqrt(10005) * 2^bits
    return (426880 * root * q) // t


def exact_digits(pi_fixed, bits, d, n=DIGITS):
    frac = pi_fixed - (3 << bits)
    shift = bits - 4 * (d + n)
    return format((frac >> shift) & ((1 << (4 * n)) - 1), f"0{n}x")


# ---------------------------------------------------------------- the run

def main():
    seed = os.environ.get("ECDYSIS_SEED", "")
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        sys.exit("ECDYSIS_SEED must be the 64-hex seed the archive issued")
    stream = Stream(seed, "bbp/positions")
    positions = sorted({stream.below(MAX_POSITION - DIGITS) for _ in range(POSITIONS)})
    bits = 4 * (MAX_POSITION + DIGITS) + 64
    pi_fixed = chudnovsky_fixed(bits)
    if exact_digits(pi_fixed, bits, 0, 8) != "243f6a88":
        sys.exit("the independent computation of pi is wrong at its start")

    checked = [0] + positions
    wrong_digits, found = 0, []
    for d in checked:
        got, want = bbp_digits(d), exact_digits(pi_fixed, bits, d)
        wrong_digits += sum(1 for a, b in zip(got, want) if a != b)
        found.append(f"{d}:{got}")
    control_wrong = sum(sum(1 for a, b in zip(bbp_digits(d, wrong=True), exact_digits(pi_fixed, bits, d)) if a != b)
                        for d in checked)

    ratios = {}
    for e in (12, 16, 20):
        d = 1 << e
        ratios[e] = multiplications(d) / (d * e)
    growth = ratios[20] / ratios[12]

    out = {
        "positions_checked": len(checked),
        "digits_per_position": DIGITS,
        "wrong_digits": wrong_digits,
        "control_wrong_digits": control_wrong,
        "max_position": max(checked),
        "digits_found": hashlib.sha256(";".join(found).encode("ascii")).hexdigest()[:16],
        "positions": ",".join(str(d) for d in checked),
        "pi_bits_independent": bits,
        "mults_per_dlogd_2e12": round(ratios[12], 6),
        "mults_per_dlogd_2e16": round(ratios[16], 6),
        "mults_per_dlogd_2e20": round(ratios[20], 6),
        "cost_growth_2e12_to_2e20": round(growth, 6),
        "largest_modulus_bits": (8 * max(checked) + 6).bit_length(),
    }
    out["test_passed"] = 1 if wrong_digits == 0 and control_wrong > 0 and growth <= 1.25 else 0
    os.makedirs("results", exist_ok=True)
    with open(os.path.join("results", "outputs.json"), "w", encoding="ascii") as f:
        json.dump(out, f, indent=2, sort_keys=True)
        f.write("\n")
    print(json.dumps(out, indent=2, sort_keys=True))
    print(";".join(found), file=sys.stderr)


if __name__ == "__main__":
    main()
