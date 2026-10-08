#!/usr/bin/env python3
"""Salamin's AGM iteration for pi: the correct digits of its first 17 approximations, and whether each step doubles
them.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:3ae15a09dd283917) is from Salamin,
"Computation of pi using arithmetic-geometric mean", Mathematics of Computation 30(135) (1976): "The error analysis
shows that its rapid convergence doubles the number of significant digits after each step."

Its registered test: refuted if, for some n from 1 to 16, pi_{n+1} has fewer than twice as many correct decimal digits
as pi_n, where pi_n = a_{n+1}^2/s_n from the AGM iteration as Brent states Salamin's formula (a_0 = 1,
b_0 = 1/sqrt(2), s_0 = 1/4; a_{n+1} = (a_n + b_n)/2, b_{n+1} = sqrt(a_n b_n), s_{n+1} = s_n - 2^n (a_n - a_{n+1})^2),
computed with enough guard digits, and the correct digits of x are floor(-log10(pi - x)).

Standard library only: Python's decimal module (libmpdec), every operation correctly rounded to the context's
precision. Nothing is read in. Every rule below was fixed before any seed existed; the seed is not used, as nothing
here is random.

1. Precision. The last approximation the test needs, pi_17, has about 357,700 correct digits, so the iteration runs
   at P = 360,000 significant digits plus 50 guard digits (and again with 100, rule 5).
2. The reference pi. Chudnovsky's series (about 14.18 digits a term) and, independently, Ramanujan's of 1914
   (1103 + 26390k, about 7.98 digits a term), each summed by binary splitting in exact integer arithmetic (any
   rounding there stops the run) and divided out at P + 120 digits. The two must differ by less than 10^-(P + 110)
   and begin with the 50 decimals everyone knows (3.14159...37510); Chudnovsky's is the reference.
3. The iteration. Brent's Algorithm GL (arXiv:1802.07558, section 4) exactly as the test states it, for n from 0 to
   17: pi_n = a_{n+1}^2/s_n.
4. Correct digits. d_n = floor(-log10 |pi - pi_n|), read exactly from the decimal exponent of pi - pi_n and whether
   its digits are a bare power of ten. That is the registered formula: the absolute value only defines it for the
   controls, as Brent's lower bound makes pi - pi_n positive (whether it is, is reported). A difference that is zero,
   or below 10^-(prec - 1000) where the working precision's rounding could reach it, is refused rather than read.
5. Guard digits. Rules 3 and 4 run with 100 guard digits instead of 50 must give the same d_n for every n; if not,
   the run is refused as not computed with enough guard digits.

test_passed is 1 if d_{n+1} >= 2 d_n for every n from 1 to 16; else 0. The excess d_{n+1} - 2 d_n is reported, its
smallest value and the first n where it falls.

Controls, at 3,000 digits, each reported:
(a) the references: rule 2's agreement and first 50 decimals;
(b) Brent's Table 1: the lower and upper values a_{n+1}^2/s_n and a_n^2/s_n for n = 0 to 4, as printed to 24
    decimals (10 numbers);
(c) Brent's Table 2: a_n^2/s_n - pi and pi - a_{n+1}^2/s_n to three significant figures, and their ratios to his
    bounds U(n) = 8 pi q^(2^n) and L(n) = (2^(n+4) pi^2 - 8 pi) q^(2^(n+1)), q = e^-pi, to nine decimals, for n = 0
    to 8 (36 numbers). For both tables, each of ours must lie within one unit of the printed number's last digit, and
    how many match exactly when rounded as printed is reported: before registering, one did not (Table 2's n = 1
    lower ratio, printed 0.999656206, recomputed 0.99965620542);
(d) Brent's bounds: 0 < pi - a_{n+1}^2/s_n < L(n) and 0 < a_n^2/s_n - pi < U(n) for n = 0 to 8;
(e) the test can fail: with b_0 raised by 10^-30 the iteration converges elsewhere, and d_{n+1} >= 2 d_n must fail
    for some n from 1 to 8;
(f) and with a sequence that converges only linearly, the semi-perimeters of the regular polygons of 12, 24, ...,
    3,072 sides inscribed in the unit circle (Archimedes' doubling), it must fail too.

What it cannot check: Salamin's own paper, whose text is not reachable here (the iteration is Brent's statement of
it, which he gives as Salamin's; his two tables are matched as controls); steps beyond n = 17; the error analysis
itself, which this run observes and does not prove.

Writes results/outputs.json (18 values) and results/detail.json. Run with: python3 pi/agm.py
"""

import decimal
import json
import math
import os
import re
import sys
from decimal import Decimal as D

PRECISION = 360_000                 # rule 1: P, significant digits
GUARDS = (50, 100)                  # rules 1 and 5
N_MAX = 17                          # pi_0 to pi_17
FIRST = 1                           # the test compares d_{n+1} with 2 d_n for n from FIRST to N_MAX - 1
REF_EXTRA, AGREE_EXTRA = 120, 110   # rule 2
FLOOR = 1000                        # rule 4
CHUD_DIGITS, RAM_DIGITS = 14.18, 7.98
CONTROL_PREC, CONTROL_N, CONTROL_SIDES = 3000, 9, 9
PERTURB = D("1e-30")                # control (e)
PI50 = "3.14159265358979323846264338327950288419716939937510"

# Brent, "The Borwein brothers, pi and the AGM" (arXiv:1802.07558), Table 1: n -> (a_{n+1}^2/s_n, a_n^2/s_n).
TABLE1 = {
    0: ("2.914213562373095048801689", "4.000000000000000000000000"),
    1: ("3.140579250522168248311331", "3.187672642712108627201930"),
    2: ("3.141592646213542282149344", "3.141680293297653293918070"),
    3: ("3.141592653589793238279513", "3.141592653895446496002915"),
    4: ("3.141592653589793238462643", "3.141592653589793238466361"),
}
# Table 2: n -> (a_n^2/s_n - pi, pi - a_{n+1}^2/s_n, the first over U(n), the second over L(n)).
TABLE2 = {
    0: ("8.58e-1", "2.27e-1", "0.790369040", "0.916996189"),
    1: ("4.61e-2", "1.01e-3", "0.981804947", "0.999656206"),
    2: ("8.76e-5", "7.38e-9", "0.999922813", "0.999999998"),
    3: ("3.06e-10", "1.83e-19", "0.999999999", "1.000000000"),
    4: ("3.72e-21", "5.47e-41", "1.000000000", "1.000000000"),
    5: ("5.50e-43", "2.41e-84", "1.000000000", "1.000000000"),
    6: ("1.20e-86", "2.31e-171", "1.000000000", "1.000000000"),
    7: ("5.76e-174", "1.06e-345", "1.000000000", "1.000000000"),
    8: ("1.32e-348", "1.11e-694", "1.000000000", "1.000000000"),
}


class Refused(Exception):
    """The run cannot read the digits it was asked for (rules 2, 4 and 5)."""


def context(prec):
    """Rounded arithmetic at prec significant digits, half to even, with room for any exponent."""
    return decimal.localcontext(decimal.Context(
        prec=prec, rounding=decimal.ROUND_HALF_EVEN, Emax=decimal.MAX_EMAX, Emin=decimal.MIN_EMIN,
        traps=[decimal.InvalidOperation, decimal.DivisionByZero, decimal.Overflow]))


def exact():
    """Exact integer arithmetic: any rounding raises."""
    return decimal.localcontext(decimal.Context(
        prec=decimal.MAX_PREC, Emax=decimal.MAX_EMAX, Emin=decimal.MIN_EMIN,
        traps=[decimal.InvalidOperation, decimal.DivisionByZero, decimal.Overflow, decimal.Inexact,
               decimal.Rounded]))


def split(leaf, a, b):
    """Binary splitting: (P, Q, T) over the terms a to b - 1, from leaf(k) = (p_k, q_k, t_k)."""
    if b - a == 1:
        return leaf(a)
    m = (a + b) // 2
    p1, q1, t1 = split(leaf, a, m)
    p2, q2, t2 = split(leaf, m, b)
    return p1 * p2, q1 * q2, q2 * t1 + p1 * t2


def chudnovsky(prec):
    """(pi to prec digits by the Chudnovskys' series, terms summed)."""
    terms = math.ceil(prec / CHUD_DIGITS) + 2
    with exact():
        c3 = D(640320 ** 3 // 24)

        def leaf(k):
            if k == 0:
                p = q = D(1)
            else:
                p = D((6 * k - 5) * (2 * k - 1) * (6 * k - 1))
                q = D(k) ** 3 * c3
            t = p * (13591409 + 545140134 * k)
            return p, q, (-t if k & 1 else t)

        _, q, t = split(leaf, 0, terms)
    with context(prec):
        return D(426880) * D(10005).sqrt() * q / t, terms


def ramanujan(prec):
    """(pi to prec digits by Ramanujan's series of 1914, terms summed): 1/pi = (2 sqrt 2/9801) sum (4k)! (1103 +
    26390k) / ((k!)^4 396^(4k))."""
    terms = math.ceil(prec / RAM_DIGITS) + 2
    with exact():
        r4 = D(396) ** 4

        def leaf(k):
            if k == 0:
                p = q = D(1)
            else:
                p = D((4 * k - 3) * (4 * k - 2) * (4 * k - 1) * (4 * k))
                q = D(k) ** 4 * r4
            return p, q, p * (1103 + 26390 * k)

        _, q, t = split(leaf, 0, terms)
    with context(prec):
        return D(9801) * q / (D(8).sqrt() * t), terms


def references(prec):
    """Rule 2: Chudnovsky's pi at prec digits, after checking it against Ramanujan's and the known 50 decimals."""
    pc, nc = chudnovsky(prec)
    pr, nr = ramanujan(prec)
    with context(prec):
        gap = abs(pc - pr)
    agree = gap == 0 or gap.adjusted() < -(prec - REF_EXTRA + AGREE_EXTRA)
    first = str(pc)[:len(PI50)] == PI50
    return pc, {"chudnovsky_terms": nc, "ramanujan_terms": nr, "gap": "0" if gap == 0 else f"{gap:.3e}",
                "agree": agree, "first50": first}


def gl(prec, n_max, b0_shift=0, upper=False):
    """Brent's Algorithm GL at prec digits: [a_{n+1}^2/s_n for n = 0..n_max] and, if asked, [a_n^2/s_n]."""
    lows, ups = [], []
    with context(prec):
        a, b, s = D(1), D("0.5").sqrt() + b0_shift, D(1) / 4
        for n in range(n_max + 1):
            a1 = (a + b) / 2
            c1 = a - a1
            lows.append(a1 * a1 / s)
            if upper:
                ups.append(a * a / s)
            if n < n_max:
                b = (a * b).sqrt()
                s = s - 2 ** n * c1 * c1
            a = a1
    return lows, ups


def correct_digits(diff):
    """floor(-log10 |diff|), exactly: from the decimal exponent, less one unless the digits are a bare power of ten."""
    x = abs(diff)
    if x == 0:
        raise Refused("the approximation equals pi to the working precision")
    e = x.adjusted()
    return -e if x == D((0, (1,), e)) else -e - 1


def digits_of(values, pi, prec, floor=True):
    """Rule 4: [(d_n, pi - x_n > 0, the leading digits of pi - x_n)] for the values x_n, at prec digits."""
    out = []
    with context(prec):
        for n, x in enumerate(values):
            diff = pi - x
            if floor and (diff == 0 or diff.adjusted() < -(prec - FLOOR)):
                raise Refused(f"n = {n}: pi - pi_n is within reach of the working precision's rounding")
            out.append((correct_digits(diff), diff > 0, f"{diff:.11e}"))
    return out


def excesses(ds, first=FIRST):
    """[(n, d_{n+1} - 2 d_n)] for n from first to the last but one; ds[n] is d_n."""
    return [(n, ds[n + 1] - 2 * ds[n]) for n in range(first, len(ds) - 1)]


def doubles(ds, first=FIRST):
    return all(e >= 0 for _, e in excesses(ds, first))


def archimedes(prec, steps):
    """Semi-perimeters of the regular polygons of 6, 12, ..., 6 * 2^steps sides inscribed in the unit circle."""
    out = []
    with context(prec):
        m, side = 6, D(1)
        out.append(D(3))
        for _ in range(steps):
            side = side / (2 + (4 - side * side).sqrt()).sqrt()
            m *= 2
            out.append(m * side / 2)
    return out


def compare(value, printed, shown):
    """A printed number against ours: matched when ours, rounded as printed, is the same number; within when ours lies
    within one unit of the printed number's last digit."""
    p = D(printed)
    unit = D((0, (1,), p.as_tuple().exponent))
    return {"printed": printed, "ours": shown, "matched": D(shown) == p, "within": abs(value - p) <= unit}


def brent(prec=CONTROL_PREC):
    """Controls (b) to (d): Brent's two tables and his bounds, at prec digits."""
    pi, _ = chudnovsky(prec + 20)
    lows, ups = gl(prec, 8, upper=True)
    t1, t2, bounds = [], [], []
    with context(prec):
        pi = +pi
        q = [(-pi).exp()]
        for _ in range(10):
            q.append(q[-1] * q[-1])                         # q[k] = q^(2^k)
        for n, printed in TABLE1.items():
            for which, value, p in (("lower", lows[n], printed[0]), ("upper", ups[n], printed[1])):
                t1.append(dict(compare(value, p, str(value.quantize(D("1e-24")))), n=n, value=which))
        for n, printed in TABLE2.items():
            up_err, low_err = ups[n] - pi, pi - lows[n]
            u = 8 * pi * q[n]
            l_ = (2 ** (n + 4) * pi * pi - 8 * pi) * q[n + 1]
            values = (up_err, low_err, up_err / u, low_err / l_)
            shown = (f"{up_err:.2e}", f"{low_err:.2e}", f"{values[2]:.9f}", f"{values[3]:.9f}")
            for col, p, v, o in zip(("upper error", "lower error", "upper ratio", "lower ratio"), printed, values,
                                    shown):
                t2.append(dict(compare(v, p, o), n=n, column=col))
            bounds.append({"n": n, "lower": bool(0 < low_err < l_), "upper": bool(0 < up_err < u)})
    return t1, t2, bounds


def controls():
    """Controls (a) to (f) at CONTROL_PREC digits."""
    pi, ref = references(CONTROL_PREC + REF_EXTRA)
    t1, t2, bounds = brent()
    lows, _ = gl(CONTROL_PREC, CONTROL_N, b0_shift=PERTURB)
    perturbed = [d for d, _, _ in digits_of(lows, pi, CONTROL_PREC, floor=False)]
    linear = [d for d, _, _ in digits_of(archimedes(CONTROL_PREC, CONTROL_SIDES), pi, CONTROL_PREC, floor=False)]
    checks = {
        "references": ref["agree"] and ref["first50"],
        "table1": all(r["within"] for r in t1),
        "table2": all(r["within"] for r in t2),
        "bounds": all(b["lower"] and b["upper"] for b in bounds),
        "perturbed_fails": not doubles(perturbed),
        "linear_fails": not doubles(linear),
    }
    return checks, {"references": ref, "table1": t1, "table2": t2, "bounds": bounds,
                    "perturbed_digits": perturbed, "linear_digits": linear}


def run(precision=PRECISION, n_max=N_MAX, guards=GUARDS, results="results", progress=None):
    say = progress or (lambda *_: None)
    pi, ref = references(precision + REF_EXTRA)
    if not (ref["agree"] and ref["first50"]):
        raise Refused(f"rule 2: the two references disagree or do not begin as pi does: {ref}")
    say("references", ref)
    per_guard = {}
    for g in guards:
        lows, _ = gl(precision + g, n_max)
        per_guard[g] = digits_of(lows, pi, precision + g)
        say("guard", g, [d for d, _, _ in per_guard[g]])
    lists = {g: [d for d, _, _ in rows] for g, rows in per_guard.items()}
    if len({tuple(v) for v in lists.values()}) != 1:
        raise Refused(f"rule 5: the correct digits differ with the guard digits: {lists}")
    rows = per_guard[guards[0]]
    ds = lists[guards[0]]
    exc = excesses(ds)
    worst = min(e for _, e in exc)
    checks, cdetail = controls()
    say("controls", checks)
    out = {
        "precision": precision,
        "digits": ",".join(str(d) for d in ds[1:]),
        "d_last": ds[-1],
        "min_excess": worst,
        "min_excess_at": next(n for n, e in exc if e == worst),
        "all_below": int(all(below for _, below, _ in rows)),
        "guards_agree": 1,
        "refs_agree": int(ref["agree"] and ref["first50"]),
        "table1_matched": sum(r["matched"] for r in cdetail["table1"]),
        "table1_total": len(cdetail["table1"]),
        "table2_matched": sum(r["matched"] for r in cdetail["table2"]),
        "table2_total": len(cdetail["table2"]),
        "bounds_held": int(checks["bounds"]),
        "perturbed_fails": int(checks["perturbed_fails"]),
        "linear_fails": int(checks["linear_fails"]),
        "controls_passed": sum(checks.values()),
        "controls_total": len(checks),
        "test_passed": int(doubles(ds)),
    }
    detail = {
        "rules": {"precision": precision, "guards": list(guards), "n_max": n_max, "first": FIRST, "floor": FLOOR},
        "references": ref,
        "approximations": [{"n": n, "d": d, "pi_minus_pi_n": lead, "positive": below}
                           for n, (d, below, lead) in enumerate(rows)],
        "excesses": [{"n": n, "excess": e} for n, e in exc],
        "guards": {str(g): v for g, v in lists.items()},
        "controls": checks,
        "control_detail": cdetail,
    }
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
        out, _ = run(progress=lambda *a: print("agm:", *a, file=sys.stderr, flush=True))
    except Refused as e:
        sys.exit(f"agm: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
