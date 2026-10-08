#!/usr/bin/env python3
"""The googol-th binary digit of Stoneham's constant alpha_{2,3}, by exact integer arithmetic.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:ded670e8b5a597f3) is from Bailey and
Crandall, "Random generators and normal numbers", Experimental Mathematics 11(4) (2002): "For example, we find that the
googol-th (i.e., 10100 -th) binary bit of alpha2,3 is 0." Its index drops the superscript: the position is 10^100.

Its registered test: refuted if the binary digit of alpha_{2,3} = sum_{k>=1} 1/(3^k 2^(3^k)) at position 10^100, the
coefficient of 2^(-10^100) in its binary expansion, is 1.

Standard library only. Every rule below was fixed before any seed existed; the seed (ECDYSIS_SEED) draws rule 3's
positions and nothing else.

1. Extraction. The digits from position n (the n-th digit being the coefficient of 2^-n) are the binary digits of
   frac(2^(n-1) alpha). With d = n - 1, the terms with 3^k <= d contribute (2^(d - 3^k) mod 3^k) / 3^k each, summed
   exactly as one fraction over 3^K (K the largest such k); the terms with d < 3^k <= d + 128 are added exactly as
   1 / (3^k 2^(3^k - d)); the rest of the series is positive and below 2^-128. The 40 digits from position n are
   floor(2^40 V) for the exact sum V, and they are certain unless the 88 digits after them are all ones, in which
   case the run stops rather than guess.
2. The googol. Rule 1 at n = 10^100: the googol-th digit, the 40 digits from there in hexadecimal, the number of
   terms summed and the exponent below which the rest of the series lies (3^(K+1) - d, over 5 x 10^99).
3. A second route. The first 2^20 + 48 digits of alpha by direct summation, floor(2^(N+64) / (3^k 2^(3^k))) over
   every k with 3^k <= N + 64, the 64 guard digits checked for a carry; rule 1 must give the same 40 digits at 16
   positions drawn by the seed in [1, 2^20] and at 12 fixed ones (1, 2, 3, 4, 8, 9, 10, 26, 27, 28, 80, 728), where
   terms enter and leave the head.
4. The paper. The ten hexadecimal digits from position 10^100 are compared with those section 4 prints, 2205896E7B.
5. Controls. (a) The digits from 10^100 + 1 must be the googol's digits shifted by one, and their hexadecimal is
   not the printed string: the count matters. (b) The series without its first term must give other digits at
   10^100. (c) A corrupted head (the residue of k = 10 increased by one, a change of 1/3^10 that the 40 digits
   can show) must give other digits at 10^100.

test_passed is 1 if the googol-th digit is 0; else 0.

What it cannot check: the paper's own run (2.8 seconds on a workstation of 2002); anything about the normality of
alpha_{2,3}, which the paper proves by other means.

Writes results/outputs.json (10 values) and results/detail.json. Run with: python3 pi/alpha23.py
"""

import hashlib
import json
import os
import re
import sys
from fractions import Fraction

GOOGOL = 10 ** 100
PRINTED = "2205896E7B"
WIDTH, GUARD = 40, 88                       # digits reported; guard digits that must not all be ones
LOW_MAX, LOW_DRAWN = 2 ** 20, 16
FIXED = (1, 2, 3, 4, 8, 9, 10, 26, 27, 28, 80, 728)


class Uncertain(Exception):
    """The digits after the window are all ones: the rest of the series might carry into it."""


def head_terms(d):
    """[(k, 3^k)] for every k >= 1 with 3^k <= d."""
    out, k, p = [], 1, 3
    while p <= d:
        out.append((k, p))
        k, p = k + 1, p * 3
    return out


def frac_head(d, skip_first=False, corrupt=False):
    """Rule 1: frac(2^d alpha) up to the terms with 3^k <= d + 128, exactly; and the exponent bounding the rest."""
    terms = head_terms(d)
    if skip_first:
        terms = [t for t in terms if t[0] != 1]
    V = Fraction(0)
    if terms:
        P = terms[-1][1]
        num = 0
        for k, p in terms:
            r = pow(2, d - p, p)
            if corrupt and k == 10:                    # a term whose 1/3^k shows in the 40 digits
                r = (r + 1) % p
            num += r * (P // p)
        V = Fraction(num % P, P)
    k = len(head_terms(d)) + 1
    p = 3 ** k
    while p <= d + 128:
        if not (skip_first and k == 1):
            V += Fraction(1, p * 2 ** (p - d))
        k, p = k + 1, p * 3
    V -= V.numerator // V.denominator                 # modulo 1
    return V, p - d, len(terms)


def digits_from(n, width=WIDTH, **kw):
    """The `width` binary digits of alpha from position n, as an integer; Uncertain if a carry cannot be ruled out."""
    if n < 1:
        raise ValueError("positions start at 1")
    V, _, _ = frac_head(n - 1, **kw)
    scaled = V * 2 ** (width + GUARD)
    window = scaled.numerator // scaled.denominator
    if window % 2 ** GUARD == 2 ** GUARD - 1:
        raise Uncertain(f"position {n}: the {GUARD} digits after the window are all ones")
    return window >> GUARD


def prefix(N):
    """Rule 3: the first N digits of alpha by direct summation, as an integer; Uncertain if the guard could carry."""
    G = 64
    total, k, p = 0, 1, 3
    while p <= N + G:
        total += 2 ** (N + G - p) // p
        k, p = k + 1, p * 3
    if total % 2 ** G >= 2 ** G - k:                 # each floor lost under one unit; k - 1 terms
        raise Uncertain("the guard digits of the direct sum could carry")
    return total >> G


def window_of(pre, N, n, width=WIDTH):
    """Digits n .. n + width - 1 of the N-digit prefix."""
    return (pre >> (N - (n + width - 1))) & (2 ** width - 1)


def positions(seed):
    """Rule 3's 16 positions in [1, 2^20], drawn from the seed by SHA-256 in counter mode, without repeats."""
    out, i = [], 0
    while len(out) < LOW_DRAWN:
        h = hashlib.sha256(f"{seed}|alpha23|{i}".encode("ascii")).digest()
        x = int.from_bytes(h[:8], "big") % LOW_MAX + 1
        if x not in out:
            out.append(x)
        i += 1
    return sorted(out)


def hexd(x, width=WIDTH):
    return format(x, f"0{width // 4}X")


def run(seed, results="results"):
    g = digits_from(GOOGOL)
    _, tail_exp, terms = frac_head(GOOGOL - 1)
    bit = g >> (WIDTH - 1)
    # rule 3
    N = LOW_MAX + WIDTH + 8
    pre = prefix(N)
    drawn = positions(seed)
    checks = [(n, hexd(digits_from(n)), hexd(window_of(pre, N, n))) for n in list(FIXED) + drawn]
    agree = sum(1 for _, a, b in checks if a == b)
    # rule 5
    g1 = digits_from(GOOGOL + 1)
    nxt = digits_from(GOOGOL + WIDTH, width=1)
    shifted_ok = g1 == ((g << 1) & (2 ** WIDTH - 1)) | nxt
    controls = {
        "shifted_by_one": shifted_ok and hexd(g1) != PRINTED,
        "without_first_term": digits_from(GOOGOL, skip_first=True) != g,
        "corrupted_head": digits_from(GOOGOL, corrupt=True) != g,
    }
    out = {
        "googol_bit": bit,
        "hex10": hexd(g),
        "printed_match": int(hexd(g) == PRINTED),
        "terms": terms,
        "tail_exponent": f"{tail_exp:.6e}",
        "next_hex10": hexd(g1),
        "low_positions": ",".join(str(n) for n in drawn),
        "low_agree": f"{agree}/{len(checks)}",
        "controls": f"{sum(controls.values())}/{len(controls)}",
        "test_passed": int(bit == 0),
    }
    for k, v in out.items():
        if isinstance(v, str) and len(v) > 200:
            raise AssertionError(f"{k}: longer than 200 characters")
    detail = {"googol": {"position": "10^100", "digits": format(g, "040b"), "hex": hexd(g), "terms": terms,
                         "tail_below": f"2^-{tail_exp}"},
              "low": [{"position": n, "extraction": a, "direct": b} for n, a, b in checks], "prefix_digits": N,
              "controls": controls, "printed": PRINTED}
    os.makedirs(results, exist_ok=True)
    with open(os.path.join(results, "outputs.json"), "w", encoding="ascii") as fh:
        json.dump(out, fh, indent=2, sort_keys=True)
        fh.write("\n")
    with open(os.path.join(results, "detail.json"), "w", encoding="ascii") as fh:
        json.dump(detail, fh, indent=1, sort_keys=True)
        fh.write("\n")
    return out, detail


def main():
    seed = os.environ.get("ECDYSIS_SEED", "")
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        sys.exit("ECDYSIS_SEED must be the 64-hex seed the archive issued")
    try:
        out, _ = run(seed)
    except Uncertain as e:
        sys.exit(f"alpha23: uncertain: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
