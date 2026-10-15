#!/usr/bin/env python3
"""Beside Kauers & Wood's receipt, not part of it: the denominators a released rational scheme really needs.

Imago's laboratory (https://ecdysis.me/a/Imago). mm/mfg.py's receipt (54eebe7d..., 15 October 2026) reports, beside its
test, the primes of the rational schemes' divisors as the release writes them, a product (A)*(B)*(C)/d. A divisor can
cancel against the factors: a term u (x) v (x) w / d with integer u, v and w needs the prime q only when the power of q
in d exceeds the sum of its powers in the contents (the gcds) of u, v and w, because the entries of a tensor product
of primitive vectors have gcd 1. When no prime remains in any term, moving each term's integer scalar into its first
factor gives the same scheme with integer coefficients, which this module checks exact over Z with mm/check.py.

This was written after the receipt's run, on the release's other files as well as the receipt's; nothing in the
receipt depends on it. Run with: python3 mm/mfg_reduce.py DIR [FORMAT ...], DIR holding the release's format
directories (github.com/mkauers/matrix-multiplication at 6487519, the paper's day); by default the seven formats the
paper calls rational, each file without .mod2 in its name that has a divisor. Nothing in the files is run; they are
read as text. Standard library only.
"""

import importlib.util
import json
import os
import sys
from fractions import Fraction
from functools import reduce
from math import gcd

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("mm_mfg", os.path.join(HERE, "mfg.py"))
MFG = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(MFG)
CHECK = MFG.CHECK

RATIONAL = ("257", "258", "268", "277", "348", "357", "377")


def valuation(x, q):
    x, k = abs(x), 0
    while x and x % q == 0:
        x //= q
        k += 1
    return k


def terms(text, fmt):
    """Each product of a .exp text as (sign, u, v, w, d) with integer u, v and w, read as mm/mfg.py reads it."""
    n, m, p = fmt
    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        d, sign = 1, 1
        t = MFG.TAIL.match(s)
        if t:
            s, d = t.group(1).strip(), int(t.group(2))
        if s.startswith("-(") and CHECK.closing(s, 1) == len(s) - 1:
            s, sign = s[2:-1], -1
        parts = CHECK.split_product(s)
        if len(parts) != 3:
            raise MFG.Refused(f"not a product of three factors: {line[:60]!r}")
        yield (sign, MFG.factor(parts[0], "a", n, m), MFG.factor(parts[1], "b", m, p), MFG.factor(parts[2], "c", p, n),
               d)


def needed_primes(u, v, w, d):
    """The primes left in the denominators of u (x) v (x) w / d, and those of d as written."""
    contents = [reduce(gcd, (abs(x) for x in f.values())) for f in (u, v, w)]
    written = MFG.primes_of(d)
    return {q for q in written if valuation(d, q) > sum(valuation(c, q) for c in contents)}, written


def integral(scheme_terms):
    """The scheme with each term's scalar moved into its first factor, or None if some term keeps a denominator."""
    out = []
    for sign, u, v, w, d in scheme_terms:
        cu, cv, cw = (reduce(gcd, (abs(x) for x in f.values())) for f in (u, v, w))
        c = Fraction(sign * cu * cv * cw, d)
        if c.denominator != 1:
            return None
        out.append(({k: int(c) * (x // cu) for k, x in u.items()}, {k: x // cv for k, x in v.items()},
                    {k: x // cw for k, x in w.items()}))
    return out


def examine(text, fmt):
    n, m, p = fmt
    ts = list(terms(text, fmt))
    kept, written = set(), set()
    for _, u, v, w, d in ts:
        k, wr = needed_primes(u, v, w, d)
        kept |= k
        written |= wr
    row = {"products": len(ts), "written": sorted(written), "needed": sorted(kept)}
    if not kept:
        scheme, _ = MFG.read_scheme(text.encode("ascii"), fmt, "Q")
        ints = integral(ts)
        row["wrong_over_Q_as_written"] = CHECK.wrong_entries(scheme, n, m, p, "Q")
        row["wrong_over_Z_rescaled"] = CHECK.wrong_entries(ints, n, m, p, "Z")
        row["largest_integer"] = max(abs(x) for t in ints for f in t for x in f.values())
    return row


def main(argv):
    root, formats = argv[0], argv[1:] or RATIONAL
    for code in formats:
        d = os.path.join(root, code)
        for name in sorted(os.listdir(d)):
            if not name.endswith(".exp") or ".mod2" in name:
                continue
            with open(os.path.join(d, name), "rb") as fh:
                text = fh.read().decode("ascii")
            if "/" not in text:
                continue
            print(json.dumps({"format": code, "file": name, **examine(text, MFG.fmt_of(code))}))


if __name__ == "__main__":
    main(sys.argv[1:])
