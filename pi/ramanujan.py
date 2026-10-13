#!/usr/bin/env python3
"""Two continued fractions from the Ramanujan Machine, against 24/pi^2 and 8/(7 zeta(3)) to 10,000 digits.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:362eb6b475d3e8dd) is from Raayoni, Gottlieb,
Pisha, Harris, Manor, Mendlovic, Haviv, Hadad & Kaminer, "The Ramanujan Machine: Automatically Generated Conjectures on
Fundamental Constants" (arXiv:1907.00205; Nature 590, 67-73, 2021): "Two example conjectures found by our algorithm and
so far unproven are:" 24/pi^2 = 2 + 7.0.1 + 8.1^4/(2 + 7.1.2 + 8.2^4/(2 + 7.2.3 + ...)) and
8/(7 zeta(3)) = 1.1 - 1^6/(3.7 - 2^6/(5.19 - 3^6/(7.37 - ...))).

Its registered test: refuted if either continued fraction, as the quote prints it (24/pi^2: partial denominators
2 + 7n(n + 1) from n = 0 and numerators 8n^4; 8/(7 zeta(3)): denominators (2n + 1)(3n^2 + 3n + 1) and numerators -n^6),
differs from its constant by more than 10^-10000 at its 12,000th convergent (the first) or its 7,000th (the second),
with pi and zeta(3) each computed afresh to 11,000 digits by two independent series that agree.

Python's standard library only (integers, exactly); no input, as the claim is a construction. Every rule below was
fixed before any seed existed; the seed is not used, as nothing here is random.

1. The continued fractions: b_0 + a_1/(b_1 + a_2/(b_2 + ...)), with b_n and a_n as the test reads them from the quote;
   the n-th convergent P_n/Q_n by the three-term recurrence P_n = b_n P_{n-1} + a_n P_{n-2} (P_{-1} = 1, P_0 = b_0;
   Q_{-1} = 0, Q_0 = 1), in exact integers.
2. The constants, each to D = 11,000 decimal digits as an integer scaled by 10^D, each by two series that share no
   arithmetic:
   - pi by Machin's formula (16 arctan(1/5) - 4 arctan(1/239), each arctan by its Taylor series in fixed point) and
     by the Chudnovskys' series (binary splitting, then an integer square root);
   - zeta(3) by Apery's series (5/2) sum (-1)^(k-1) / (k^3 C(2k, k)) in fixed point and by Amdeberhan and
     Zeilberger's (1/64) sum (-1)^k (205k^2 + 250k + 77) (k!)^10 / ((2k + 1)!)^5, by binary splitting.
   Each pair must agree within 10^-(D - 20) (control); the first is used.
3. The test: for each fraction, |P_N/Q_N - c| < 10^-10000, with N = 12,000 for 24/pi^2 and 7,000 for 8/(7 zeta(3)),
   computed as |P_N 10^D - c Q_N| < Q_N 10^(D - 10000) with c to D digits. The constants' error, 10^-(D - 20), is far
   below the threshold and below what the convergents reach, so the agreement beside the test is measured, not capped.
   test_passed is 1 if both hold.
4. Beside the test: the digits of agreement, -log10 |P_n/Q_n - c|, at the quarter points of each run (n = N/4, N/2,
   3N/4, N) and the digits gained over the last step, against the rates the recurrences predict (log10 8 = 0.9031 for
   the first, whose characteristic roots are 8 and -1; log10 (1 + sqrt 2)^4 = 1.5311 for the second, roots
   (1 +- sqrt 2)^4).
5. Controls, which must all pass or the run stops: the two series for each constant agree (rule 2); the first 50
   digits of each are the published ones (OEIS A000796 and A002117); and the first ten convergents of each fraction are
   those of the recurrence written out as fractions (Python's fractions module, by the nested form of the quote).

Writes results/outputs.json (the values a receipt carries) and results/detail.json (every value computed).
"""

import json
import math
import os
import re
import sys
import time
from fractions import Fraction

if hasattr(sys, "set_int_max_str_digits"):
    sys.set_int_max_str_digits(0)          # the constants are written out to 10,100 digits

D = 11_000
THRESHOLD = 10_000
N_PI, N_ZETA = 12_000, 7_000
PI50 = "3.1415926535897932384626433832795028841971693993751"
ZETA50 = "1.2020569031595942853997381615114499907649862923404"
RATE_PI, RATE_ZETA = math.log10(8), 2 * math.log10((1 + math.sqrt(2)) ** 2)
LIMIT = 200
OUTPUTS = ("digits_pi_cf", "digits_zeta_cf", "checkpoints_pi", "checkpoints_zeta", "rate_pi", "rate_zeta",
           "last_step_pi", "last_step_zeta", "pi_methods", "zeta_methods", "controls", "conditions_met",
           "conditions_total", "test_passed")


class Refused(Exception):
    pass


# ---------------------------------------------------------------- the continued fractions (rule 1)

def b_pi(n):
    return 2 + 7 * n * (n + 1)


def a_pi(n):
    return 8 * n ** 4


def b_zeta(n):
    return (2 * n + 1) * (3 * n * n + 3 * n + 1)


def a_zeta(n):
    return -n ** 6


def convergents(b, a, n_max, keep=()):
    """P_n, Q_n for n = 0 .. n_max; returns the pairs at the indices in keep, and the last two."""
    p_prev, q_prev = 1, 0
    p, q = b(0), 1
    kept = {0: (p, q)} if 0 in keep else {}
    for n in range(1, n_max + 1):
        p, p_prev = b(n) * p + a(n) * p_prev, p
        q, q_prev = b(n) * q + a(n) * q_prev, q
        if n in keep:
            kept[n] = (p, q)
    return kept, (p_prev, q_prev), (p, q)


def nested(b, a, n):
    """The n-th convergent written out as the quote's nested fraction, in exact rationals."""
    value = Fraction(b(n))
    for k in range(n, 0, -1):
        value = b(k - 1) + Fraction(a(k)) / value
    return value


# ---------------------------------------------------------------- the constants (rule 2)

def arctan_inv(x, scale):
    """arctan(1/x) * scale, by the Taylor series in fixed point (truncating; a few units of error)."""
    total = term = scale // x
    x2, k, sign = x * x, 1, -1
    while term:
        term //= x2
        total += sign * (term // (2 * k + 1))
        sign, k = -sign, k + 1
    return total


def pi_machin(digits):
    guard = 10
    scale = 10 ** (digits + guard)
    return (16 * arctan_inv(5, scale) - 4 * arctan_inv(239, scale)) // 10 ** guard


def _chud(a, b):
    """Binary splitting of the Chudnovskys' series: P, Q, T over [a, b)."""
    if b - a == 1:
        if a == 0:
            p = q = 1
        else:
            p = (6 * a - 5) * (2 * a - 1) * (6 * a - 1)
            q = a * a * a * 10939058860032000
        t = p * (13591409 + 545140134 * a)
        return p, q, -t if a & 1 else t
    m = (a + b) // 2
    p1, q1, t1 = _chud(a, m)
    p2, q2, t2 = _chud(m, b)
    return p1 * p2, q1 * q2, t1 * q2 + p1 * t2


def pi_chudnovsky(digits):
    guard = 10
    terms = (digits + guard) // 14 + 2
    _, q, t = _chud(0, terms)
    scale = 10 ** (digits + guard)
    sqrt_10005 = math.isqrt(10005 * scale * scale)
    return (426880 * sqrt_10005 * q // t) // 10 ** guard


def zeta3_apery(digits):
    """(5/2) sum_{k>=1} (-1)^(k-1) / (k^3 C(2k, k)), in fixed point; C(2k, k) built up exactly."""
    guard = 12
    scale = 10 ** (digits + guard)
    total, k, c, sign = 0, 1, 2, 1
    while True:
        term = scale // (k * k * k * c)
        if term == 0:
            break
        total += sign * term
        k += 1
        c = c * (2 * k) * (2 * k - 1) // (k * k)
        sign = -sign
    return (5 * total // 2) // 10 ** guard


def _az(a, b):
    """Binary splitting of sum (-1)^k (205k^2 + 250k + 77) (k!)^10 / ((2k+1)!)^5, with term ratio
    r_k = k^10 / ((2k)(2k+1))^5 for k >= 1: P, Q, T over [a, b)."""
    if b - a == 1:
        k = a
        if k == 0:
            p, q = 1, 1
        else:
            p, q = -(k ** 10), ((2 * k) * (2 * k + 1)) ** 5
        return p, q, p * (205 * k * k + 250 * k + 77)
    m = (a + b) // 2
    p1, q1, t1 = _az(a, m)
    p2, q2, t2 = _az(m, b)
    return p1 * p2, q1 * q2, t1 * q2 + p1 * t2


def zeta3_az(digits):
    guard = 12
    terms = (digits + guard) // 3 + 5          # each term about 3.01 digits (ratio 1/1024)
    _, q, t = _az(0, terms)
    scale = 10 ** (digits + guard)
    return (t * scale // (64 * q)) // 10 ** guard


def as_digits(x, digits, n):
    s = str(x).rjust(digits + 1, "0")
    return s[:-digits] + "." + s[-digits:][:n - 1]


# ---------------------------------------------------------------- agreement (rules 3 and 4)

def agreement(p, q, c_scaled, digits):
    """-log10 |p/q - c|, with c = c_scaled / 10^digits (math.log10 takes integers of any size); inf if equal."""
    diff = abs(p * 10 ** digits - c_scaled * q)
    if diff == 0:
        return math.inf
    return digits - math.log10(diff) + math.log10(q)


def within(p, q, c_scaled, digits, threshold):
    """|p/q - c| < 10^-threshold, exactly: |p 10^D - c q| < q 10^(D - threshold)."""
    return abs(p * 10 ** digits - c_scaled * q) < q * 10 ** (digits - threshold)


def conditions(ok_pi, ok_zeta):
    return {"24/pi^2: the 12,000th convergent within 10^-10000": ok_pi,
            "8/(7 zeta(3)): the 7,000th convergent within 10^-10000": ok_zeta}


def run_fraction(b, a, n_max, c_scaled, digits):
    marks = (n_max // 4, n_max // 2, 3 * n_max // 4, n_max - 1, n_max)
    kept, _, last = convergents(b, a, n_max, keep=marks)
    agree = {n: agreement(*kept[n], c_scaled, digits) for n in marks}
    step = agree[n_max] - agree[n_max - 1]
    return kept, last, agree, step


def controls(pi_a, pi_b, z_a, z_b, digits):
    ctl = {}
    ctl["pi"] = ("Machin and Chudnovsky agree within 10^-(D-20)", abs(pi_a - pi_b) < 10 ** 20)
    ctl["zeta3"] = ("Apery and Amdeberhan-Zeilberger agree within 10^-(D-20)", abs(z_a - z_b) < 10 ** 20)
    ctl["published digits"] = ("first 50 digits of pi and zeta(3) as OEIS A000796 and A002117",
                               as_digits(pi_a, digits, 50) == PI50 and as_digits(z_a, digits, 50) == ZETA50)
    ok = True
    for b, a in ((b_pi, a_pi), (b_zeta, a_zeta)):
        kept, _, _ = convergents(b, a, 10, keep=range(11))
        ok &= all(Fraction(*kept[n]) == nested(b, a, n) for n in range(11))
    ctl["convergents"] = ("the first ten convergents of each fraction equal the nested fractions", ok)
    return ctl


def run(seed_hex, results="results", digits=D, n_pi=N_PI, n_zeta=N_ZETA, threshold=THRESHOLD, log=sys.stderr):
    t0 = time.time()

    def say(msg):
        if log:
            print(f"ramanujan: {msg} ({time.time() - t0:.1f} s)", file=log, flush=True)

    pi_a, pi_b = pi_machin(digits), pi_chudnovsky(digits)
    say("pi by two series")
    z_a, z_b = zeta3_apery(digits), zeta3_az(digits)
    say("zeta(3) by two series")
    ctl = controls(pi_a, pi_b, z_a, z_b, digits)
    failed = [k for k, (_, ok) in ctl.items() if not ok]
    if failed:
        raise Refused(f"the checker is not to be trusted: controls failed {failed}: {ctl}")
    scale = 10 ** digits
    c_pi = 24 * scale * scale * scale // (pi_a * pi_a)        # 24/pi^2 to D digits
    c_zeta = 8 * scale * scale // (7 * z_a)                    # 8/(7 zeta(3)) to D digits
    kp, lp, ap, sp = run_fraction(b_pi, a_pi, n_pi, c_pi, digits)
    say(f"24/pi^2 to its {n_pi}th convergent")
    kz, lz, az, sz = run_fraction(b_zeta, a_zeta, n_zeta, c_zeta, digits)
    say(f"8/(7 zeta(3)) to its {n_zeta}th convergent")
    cond = conditions(within(*lp, c_pi, digits, threshold), within(*lz, c_zeta, digits, threshold))

    def marks(agree, n_max):
        return "; ".join(f"n {n}: {agree[n]:.1f}" for n in sorted(agree) if n != n_max - 1)

    values = {
        "digits_pi_cf": round(ap[n_pi], 1), "digits_zeta_cf": round(az[n_zeta], 1),
        "checkpoints_pi": marks(ap, n_pi) + " digits", "checkpoints_zeta": marks(az, n_zeta) + " digits",
        "rate_pi": f"{sp:.4f} digits a term at the last step (predicted {RATE_PI:.4f})",
        "rate_zeta": f"{sz:.4f} digits a term at the last step (predicted {RATE_ZETA:.4f})",
        "last_step_pi": f"convergents {n_pi - 1} and {n_pi}: {ap[n_pi - 1]:.1f} and {ap[n_pi]:.1f} digits",
        "last_step_zeta": f"convergents {n_zeta - 1} and {n_zeta}: {az[n_zeta - 1]:.1f} and {az[n_zeta]:.1f} digits",
        "pi_methods": f"Machin and Chudnovsky agree to within {abs(pi_a - pi_b)} units of 10^-{digits}",
        "zeta_methods": f"Apery and Amdeberhan-Zeilberger agree to within {abs(z_a - z_b)} units of 10^-{digits}",
        "controls": f"{len(ctl) - len(failed)} of {len(ctl)}",
        "conditions_met": sum(cond.values()), "conditions_total": len(cond), "test_passed": int(all(cond.values())),
    }
    out = {k: values[k] for k in OUTPUTS}
    for k, v in out.items():
        if isinstance(v, str) and len(v) > LIMIT:
            raise AssertionError(f"{k}: longer than {LIMIT} characters: {v}")
    detail = {"values": values, "conditions": cond, "controls": {k: [v[0], v[1]] for k, v in ctl.items()},
              "agreement_pi": {str(k): v for k, v in ap.items()}, "agreement_zeta": {str(k): v for k, v in az.items()},
              "pi_first_100": as_digits(pi_a, digits, 100), "zeta3_first_100": as_digits(z_a, digits, 100),
              "digits": digits, "n": {"pi": n_pi, "zeta": n_zeta}, "threshold": threshold,
              "seconds": round(time.time() - t0, 1)}
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
        sys.exit(f"ramanujan: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
