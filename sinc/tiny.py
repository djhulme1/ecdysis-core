#!/usr/bin/env python3
"""Bäsel & Baillie's tiny numbers: the tenth sinc integral, its 68,100,152 factors and its t.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:d8c1563cc47642eb) is from Bäsel & Baillie,
"Sinc integrals and tiny numbers", Elemente der Mathematik 71(1), 7-20 (2016; arXiv:1510.03200): "For example, the
integrand of the tenth integral in the sequence is the product of 68100152 sinc functions. The corresponding t is
approximately 9.6492736004286844634795531209398105309232 x 10^-554381308."

Its registered test: refuted if, with a_0 = 10 and a_k = 1/(2k-1), the first n at which a_1 + ... + a_n exceeds a_0 is
not 68,100,151 (an integrand of n + 1 = 68,100,152 sinc functions), or if t_n = (a_1 + ... + a_n - a_0)^n /
(2^(n-1) n! a_1 a_2 ... a_n), the paper's formula from the Borweins' Corollary 1, computed to at least 50 significant
digits, differs from 9.6492736004286844634795531209398105309232 x 10^-554381308 by more than one unit in its 41st
significant digit.

The input is the paper's e-print (inputs/arXiv-1510.03200v1.tar.gz, checked against its SHA-256), from which only the
TeX of its Table 1 is read, as data, to compare every row; nothing in it is run. The computation does not use the
paper's Euler-Maclaurin sums: it uses closed forms, in mpmath at 120 digits. Every rule below was fixed before any seed
existed; the seed is not used, as nothing here is random.

1. The sum. s(n) = 1 + 1/3 + ... + 1/(2n-1) = H(2n) - H(n)/2 = psi(2n+1) - psi(n+1)/2 + gamma/2, with psi the digamma
   function and gamma Euler's constant.
2. The index. For a_0 = 1 to 10, n0(a_0) is the least n with s(n) > a_0, found by bisection on n (s increases with n).
3. The number. Since a_1 a_2 ... a_n = 1/(2n-1)!! and (2n-1)!! = (2n)!/(2^n n!), t_n = 2 (s(n) - a_0)^n C(2n, n) / 4^n,
   taken through its logarithm: ln t = ln 2 + n ln(s(n) - a_0) + lnGamma(2n+1) - 2 lnGamma(n+1) - 2n ln 2, and written
   as a mantissa with 40 decimals (41 significant digits, the paper's rounding) and a power of ten.
4. The test's conditions: n0(10) = 68,100,151; and the mantissa within one unit in its 41st significant digit of the
   printed 9.6492736004286844634795531209398105309232, with the exponent -554381308. test_passed is 1 if both hold.
5. Beside, not counted: every row of the paper's Table 1 (a_0 = 1 to 10), its n and its t compared in the same way;
   and the margin s(n0) - a_0 at a_0 = 10.

Controls (controls_passed counts those that behave as stated): the e-print is the pinned file; its Table 1 is read whole
(ten rows, a_0 = 1 to 10); the closed form of rule 1 equals the exact rational sum at n = 1,000 to 100 digits; t at
a_0 = 1 and a_0 = 2, computed exactly in rationals, equals rule 3's value to 100 digits, and the a_0 = 2 value is the
fraction the paper prints in its text (3377940044732998170721 / 168579263752214678679209808915000000); and a direct
summation of the 68,100,151 terms in double precision (math.fsum over chunks) puts s(n0 - 1) at or below 10 and s(n0)
above it, by margins far larger than its error.

What it cannot check: the integrals themselves, which the Borweins' theorem evaluates; the check takes their formula as
proved, as the paper does.

Writes results/outputs.json and results/detail.json. Run with: python3 sinc/tiny.py
"""

import hashlib
import io
import json
import math
import os
import re
import sys
import tarfile
from fractions import Fraction

import mpmath

INPUT = ("arXiv-1510.03200v1.tar.gz", "3f3f920bc6e61349a00ab35c3d46e71bc432b1dd15c0c144ccc744ab6bb2c31e", 159477)
TEX = "Sinc-Baillie-Basel.tex"
DPS = 120
A0 = 10
N0 = 68100151
MANTISSA = "9.6492736004286844634795531209398105309232"
EXPONENT = -554381308
A2_FRACTION = Fraction(3377940044732998170721, 168579263752214678679209808915000000)
LIMIT = 200
OUTPUTS = ("n0", "factors", "t_mantissa", "t_exponent", "t_differs_by_units", "rows_matched", "margin",
           "controls_passed", "controls_total", "test_passed")


class Refused(Exception):
    pass


def read_table(inputs):
    path = os.path.join(inputs, INPUT[0])
    with open(path, "rb") as fh:
        data = fh.read()
    if hashlib.sha256(data).hexdigest() != INPUT[1] or len(data) != INPUT[2]:
        raise Refused(f"{INPUT[0]} is not the pinned file")
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
        member = tar.getmember(TEX)
        tex = tar.extractfile(member).read().decode("utf-8")
    rows = {}
    for m in re.finditer(r"^\s*(\d+)\s*&\s*\$(\d+)\$\s*&\s*\$([0-9.]+)\s*\\cdot\s*10\^\{(-?\d+)\}\$\s*\\\\", tex, re.M):
        rows[int(m.group(1))] = (int(m.group(2)), m.group(3), int(m.group(4)))
    return rows


def s_closed(n):
    """Rule 1, at the working precision."""
    n = mpmath.mpf(n)
    return mpmath.digamma(2 * n + 1) - mpmath.digamma(n + 1) / 2 + mpmath.euler / 2


def n0_of(a0):
    """Rule 2: the least n with s(n) > a0."""
    lo, hi = 1, 2
    while s_closed(hi) <= a0:
        lo, hi = hi, hi * 2
    while lo < hi:
        mid = (lo + hi) // 2
        if s_closed(mid) > a0:
            hi = mid
        else:
            lo = mid + 1
    return lo


def ln_t(a0, n):
    """Rule 3."""
    s = s_closed(n)
    return (mpmath.log(2) + n * mpmath.log(s - a0) + mpmath.loggamma(2 * n + 1) - 2 * mpmath.loggamma(n + 1)
            - 2 * n * mpmath.log(2))


def scientific(lnt, decimals=40):
    """(mantissa string with the given decimals, exponent), rounding the mantissa half up at the last place."""
    l10 = lnt / mpmath.log(10)
    e = int(mpmath.floor(l10))
    m = mpmath.power(10, l10 - e)
    scaled = int(mpmath.floor(m * mpmath.power(10, decimals) + mpmath.mpf("0.5")))
    if scaled >= 10 ** (decimals + 1):                   # 9.99...95 rounds up to 10
        scaled //= 10
        e += 1
    digits = str(scaled)
    return digits[0] + "." + digits[1:], e


def units_apart(a, b):
    """How many units in the last place two mantissas of equal length differ by."""
    return abs(int(a.replace(".", "")) - int(b.replace(".", "")))


def exact_t(a0):
    """t at small a0 in rationals: the least n with s(n) > a0, then (s - a0)^n (2n-1)!! / (2^(n-1) n!)."""
    s, n = Fraction(0), 0
    while s <= a0:
        n += 1
        s += Fraction(1, 2 * n - 1)
    dfact = math.prod(range(1, 2 * n, 2))
    return n, (s - a0) ** n * dfact / (2 ** (n - 1) * math.factorial(n))


def brute_force_margins(n0, a0, chunk=1_000_000):
    """s(n0 - 1) and s(n0) by direct double-precision summation, exactly rounded within chunks (math.fsum)."""
    partials = []
    for start in range(1, n0, chunk):
        stop = min(start + chunk, n0)                    # terms k = start .. stop - 1
        partials.append(math.fsum(1.0 / (2 * k - 1) for k in range(start, stop)))
    s_before = math.fsum(partials)
    s_at = math.fsum(partials + [1.0 / (2 * n0 - 1)])
    return s_before - a0, s_at - a0


def run(seed, inputs="inputs", results="results"):
    mpmath.mp.dps = DPS
    table = read_table(inputs)
    rows = {}
    for a0 in range(1, A0 + 1):
        n = n0_of(a0)
        mant, exp = scientific(ln_t(a0, n))
        printed = table.get(a0)
        ok = (printed is not None and printed[0] == n and printed[2] == exp
              and len(printed[1]) == len(mant) and units_apart(printed[1], mant) <= 1)
        rows[a0] = {"n": n, "t_mantissa": mant, "t_exponent": exp, "printed": printed, "matches": ok}
    top = rows[A0]
    diff_units = units_apart(MANTISSA, top["t_mantissa"]) if top["t_exponent"] == EXPONENT else None
    cond = {"the first n with s(n) > 10 is 68,100,151": top["n"] == N0,
            "t within one unit in the 41st significant digit, at 10^-554381308":
                diff_units is not None and diff_units <= 1}
    margin = s_closed(top["n"]) - A0

    ctl = {"the e-print is the pinned file": True, "its Table 1 is read whole": sorted(table) == list(range(1, 11))}
    exact_1000 = sum(Fraction(1, 2 * k - 1) for k in range(1, 1001))
    ctl["the closed form equals the exact sum at n = 1,000 to 100 digits"] = abs(
        s_closed(1000) - mpmath.mpf(exact_1000.numerator) / exact_1000.denominator) < mpmath.mpf(10) ** -100
    agree = True
    for a0 in (1, 2):
        n, t = exact_t(a0)
        closed = mpmath.exp(ln_t(a0, n))
        exact = mpmath.mpf(t.numerator) / t.denominator
        agree = agree and n == rows[a0]["n"] and abs(closed / exact - 1) < mpmath.mpf(10) ** -100
        if a0 == 2:
            agree = agree and t == A2_FRACTION
    ctl["t at a_0 = 1 and 2 in rationals equals the closed form, and a_0 = 2 the paper's fraction"] = agree
    before, at = brute_force_margins(top["n"], A0)
    ctl["direct summation puts s(n0 - 1) at or below 10 and s(n0) above it"] = before <= 0 < at and (
        min(abs(before), at) > 1e-12)

    values = {"n0": top["n"], "factors": top["n"] + 1, "t_mantissa": top["t_mantissa"], "t_exponent": top["t_exponent"],
              "t_differs_by_units": -1 if diff_units is None else diff_units,
              "rows_matched": sum(1 for r in rows.values() if r["matches"]),
              "margin": mpmath.nstr(margin, 20),
              "controls_passed": sum(bool(v) for v in ctl.values()), "controls_total": len(ctl),
              "test_passed": int(all(cond.values()))}
    out = {k: values[k] for k in OUTPUTS}
    for k, v in out.items():
        if isinstance(v, str) and len(v) > LIMIT:
            raise AssertionError(f"{k}: longer than {LIMIT} characters: {v}")
    detail = {"input": {"name": INPUT[0], "sha256": INPUT[1], "bytes": INPUT[2]}, "precision_digits": DPS,
              "conditions": cond, "controls": ctl,
              "rows": {str(a0): {**r, "printed": list(r["printed"]) if r["printed"] else None} for a0, r in rows.items()},
              "brute_force": {"s(n0-1) - 10": before, "s(n0) - 10": at},
              "margin_s_n0_minus_10": mpmath.nstr(margin, 40)}
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
    except Refused as e:
        sys.exit(f"tiny: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
